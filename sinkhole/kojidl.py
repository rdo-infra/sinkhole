""" Koji interaction
"""

import os.path

import koji
import six
import yaml

from sinkhole.config import Config
from sinkhole.util import (download_packages, filter_subpkgs)

# Dict to define RPM arches associated with each basearch.
ARCHES_DICT = {'x86_64': ['noarch', 'i686', 'x86_64']}


def setup_kojiclient(profile):
    """Setup koji client session
    """
    opts = koji.read_config(profile)
    for key, value in six.iteritems(opts):
        opts[key] = os.path.expanduser(value) if isinstance(value, str) \
                    else value
    kojiclient = koji.ClientSession(opts['server'], opts=opts)
    # FIXME: who cares about authentication???
    # Moreover kerberos authentication can be an annoyance
    if opts['authtype'] == "ssl" or \
       (os.path.isfile(opts['cert']) and opts['authtype'] is None):
        kojiclient.ssl_login(opts['cert'], None, opts['serverca'])
    else:
        print('SKIP authentication')
    return kojiclient


class KojiDownloader(object):
    """ Download builds from koji
    """
    def __init__(self, profile, builds=None, exclude=None):
        self.profile = profile
        self.koji = setup_kojiclient(self.profile)
        self._builds = self.builds(builds)
        self._config = Config()
        basearch = self._config.default_substitutions['basearch']
        self._arches = ARCHES_DICT[basearch]
        self._exclude = exclude

    def builds(self, builds_):
        """ Defines builds to be downloaded
        """
        res = []
        for build in builds_:
            nvr = self._retrieve_nvr(build)
            if nvr:
                res.append(nvr)
            else:
                print("Error: {} not Found in {}".format(build). self.profile)
        return res

    def _retrieve_nvr(self, build):
        """ Retrieve NVR from Koji instance
        """
        if "@" not in build:
            return build

        build, tag = build.split("@")
        info = None
        if tag == "latest":
            pkg_id = self.koji.getPackageID(build)
            info = self.koji.listBuilds(pkg_id)
        else:
            info = self.koji.listTagged(tag, package=build)

        nvr = info[0]['nvr'] if info else None
        return nvr

    @classmethod
    def build(cls, info):
        """Build a KojiDownloader instance
        """
        kojid = None
        profile = info["profile"]
        constraints_file = info["constraints"]
        with open(constraints_file, "r") as cfile:
            constraints = yaml.load(cfile, Loader=yaml.Loader)
            builds = constraints["builds"]
            exclude = constraints["exclude"]

        kojid = cls(profile, builds, exclude)
        return kojid

    def run(self):
        """ Execute downloads
        """
        urls = []
        pathinfo = koji.PathInfo(topdir=self.koji.opts['topurl'])
        for build in self._builds:
            try:
                info = self.koji.getBuild(build)
                rpms = self.koji.listRPMs(buildID=info['id'],
                                      arches=self._arches)
                fnames = []
                for rpm in rpms:
                    if not filter_subpkgs([rpm], self._exclude):
                        fnames.append(pathinfo.rpm(rpm))
                urls += [pathinfo.build(info) + '/' + fname
                        for fname in fnames]
            except Exception:
                print('SKIPPED: build {} does not exists'.format(build))
        for url in urls:
            download_packages(url, self._config.output_dir)
