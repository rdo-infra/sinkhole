#! /usr/bin/env python

""" Module containing command-line interface
"""

import argparse
import sys

from sinkhole.config import Config
from sinkhole.kojidl import KojiDownloader
from sinkhole.masher import RepoMasher
from sinkhole.repo import Reposync
from sinkhole.source import SourceBuilder


def main():
    """ Main entrypoint for sinkhole
    """
    # top-level parser
    parser = argparse.ArgumentParser(description="sinkhole")
    parser.add_argument("--revision", action="store")
    subparsers = parser.add_subparsers(dest="subcommand")

    # reposync
    parser_reposync = subparsers.add_parser("reposync",
                                            help="Sync repositories")
    parser_reposync.add_argument("--destdir", action="store", required=True)
    parser_reposync.add_argument("--repofile", action="append", dest="repofns",
                                 required=True)
    parser_reposync.add_argument("--include", action="append", default=None)
    parser_reposync.add_argument("--exclude", action="append", default=None)

    # kojidownload
    parser_koji = subparsers.add_parser("kojidownload",
                                        help="Download builds from Koji")
    parser_koji.add_argument("--profile", action="store", default="koji",
                             help="Koji instance to retrieve builds from")
    parser_koji.add_argument("--arch", action="store", nargs="+",
                             default=None)
    parser_koji.add_argument("--builds", action="store", nargs="+",
                             required=True)
    parser_koji.add_argument("--destdir", action="store", required=True)

    parser_config = subparsers.add_parser("config_file",
                                          help="Use config file")
    parser_config.add_argument("--config", action="store", required=True)

    # argparse in python2 does not support optional subparsers. In order to
    # maintain compatibility in cli for python 2 and 3, i'm implementing a
    # default subcommand to 'config_file'.
    arg1 = sys.argv[1]
    if arg1 not in ['-h', '--help', 'reposync', 'kojidownload', 'config_file']:
        sys.argv.insert(1, 'config_file')

    # Run appropriate command
    args = parser.parse_args()

    config = Config.read_config(args.config) if args.config else Config()

    if args.subcommand == "reposync":
        config.output_dir = args.destdir
        reposync = Reposync(args.repofns, args.include, args.exclude)
        reposync.run()
    elif args.subcommand == "kojidownload":
        config.output_dir = args.destdir
        kojid = KojiDownloader(args.profile, args.builds, args.arch)
        kojid.run()
    else:
        sources = SourceBuilder.build()
        for source in sources:
            source.run()
        rm = RepoMasher(config.output_dir, revision=args.revision)
        rm.run()


if __name__ == '__main__':
    main()
