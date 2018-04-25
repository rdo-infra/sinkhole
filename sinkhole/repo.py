""" RPM repositories management
"""

from functools import partial
from multiprocessing import Pool
import os
import shutil

import dnf
from dnf.conf.parser import substitute
import six
from six.moves import configparser
import yaml

from sinkhole.config import Config
from sinkhole.util import (download_packages, filter_pkgs, filter_subpkgs)

if six.PY2:
    # ConfigParser.read_string has been added in Python 3.2
    import io
    configparser.ConfigParser.read_string = \
        lambda self, x: configparser.ConfigParser.readfp(self, io.BytesIO(x))


class RepositoryFile(object):
    """ RepositoryFile parses a .repo file
    """
    def __init__(self, conf, repofn):
        self.repofile = repofn
        self.repos = []
        self._parse_repofile(repofn, conf)

    def _parse_repofile(self, repofn, conf):
        config = configparser.ConfigParser()
        if not os.path.isfile(repofn):
            # failover on a string
            try:
                config.read_string(repofn)
            except Exception:
                raise IOError("File {:s} does not exists".format(repofn))
        else:
            config.read(repofn)
        for section in config.sections():
            repo = dnf.repo.Repo(section, conf)
            for key, value in config.items(section):
                if key in ["name", "baseurl", "enabled",
                           "gpgkey", "gpgcheck"]:
                    setattr(repo, key, value)
                elif key == "metalink":
                    setattr(repo, key, substitute(value, conf.substitutions))
            self.repos.append(repo)

    def get_repos(self):
        """ Returns a list of repositories from .repo file

        Returns:
            list: list of repositories
        """
        return self.repos


class Reposync(object):
    """ Reposync allows to sync repositories with packages filtering
    Repositories to sync are specified by feeding this class with your classic
    .repo files.
    """
    def __init__(self, repofns=None,
                 include_pkgs=None,
                 exclude_pkgs=None):
        self.include_pkgs = include_pkgs
        self.exclude_pkgs = exclude_pkgs
        self.repofns = repofns if repofns is not None else []
        self.base = dnf.Base()
        self.conf = self.base.conf
        config = Config()
        self.conf.substitutions['releasever'] = \
            config.default_substitutions["releasever"]
        self.conf.substitutions['basearch'] = \
            config.default_substitutions["basearch"]
        self.conf.cachedir = os.path.join(Config().output_dir, "cache")
        self.repos = self.base.repos

    @property
    def substitutions(self):
        """ Return yum/dnf substitutions dict
        """
        return self.conf.substitutions

    @classmethod
    def build(cls, info):
        """Build an instance of Reposync
        """
        reposync, include_pkgs, exclude_pkgs = None, None, None
        repofile = info["repofile"]
        if "constraints" in info:
            constraints_file = info["constraints"]
            with open(constraints_file, "r") as cfile:
                constraints = yaml.load(cfile, Loader=yaml.Loader)
                include_pkgs = constraints["includes"]
                exclude_pkgs = constraints["excludes"]

        reposync = cls([repofile],
                       include_pkgs=include_pkgs,
                       exclude_pkgs=exclude_pkgs)

        for sub in ["releasever", "basearch"]:
            if sub in info:
                reposync.substitutions[sub] = info[sub]
        return reposync

    def run(self):
        """ Do the repo syncing
        """
        self._setup_repos()
        self.base.fill_sack()
        available_pkgs = self.base.sack.query().available().run()
        download_pkgs = self._filter_download_pkgs(available_pkgs)
        #
        # sinkhole --repofile fedora.repo --destdir tmp2
        # 23.27s user 2.14s system 1% cpu 28:19.24 total
        download_pkgs = [pkg.remote_location() for pkg in download_pkgs]

        config = Config()
        with Pool(config.workers) as pool:
            pool.map(partial(download_packages,
                             destdir=config.output_dir),
                     download_pkgs)
        # 3161
        # sinkhole --repofile fedora.repo --destdir tmp2
        # 699.75s user 195.08s system 14% cpu 1:41:17.52 total
        # self.base.download_packages(download_pkgs,
        #                             MultiFileProgressMeter(fo=sys.stdout))
        self._cleanup_dnf_artefacts()

    def _cleanup_dnf_artefacts(self):
        """ Delete dnf metadata artefacts
        """
        shutil.rmtree(self.conf.cachedir)

    def _setup_repos(self):
        """Parse repository files
        """
        for repofn in self.repofns:
            repofile = RepositoryFile(self.conf, repofn)
            repositories = repofile.get_repos()
            for repository in repositories:
                self.repos.add(repository)

    def _filter_download_pkgs(self, pkgs):
        """ Private method that returns a list of packages to download

        Args:
            pkgs (list): packages to filter

        Returns:
            list: packages to download
        """
        included = set(pkgs) if not self.include_pkgs else \
            filter_pkgs(pkgs, self.include_pkgs)
        excluded = set() if not self.exclude_pkgs else \
            filter_subpkgs(pkgs, self.exclude_pkgs)
        pkgs = list(included - excluded)
        return pkgs
