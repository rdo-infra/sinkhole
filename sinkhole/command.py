#! /usr/bin/env python

""" Module containing command-line interface
"""

import argparse

from sinkhole.config import Config
from sinkhole.kojidl import KojiDownloader
from sinkhole.repo import Reposync
from sinkhole.source import SourceBuilder


def main():
    """ Main entrypoint for sinkhole
    """
    # top-level parser
    parser = argparse.ArgumentParser(description="sinkhole")
    parser.add_argument("--config", action="store")
    subparsers = parser.add_subparsers(dest="subcommand")

    # reposync
    parser_reposync = subparsers.add_parser("reposync", help="Sync repositories")
    parser_reposync.add_argument("--destdir", action="store", required=True)
    parser_reposync.add_argument("--repofile", action="append", dest="repofns",
                                 required=True)
    parser_reposync.add_argument("--include", action="append", default=None)
    parser_reposync.add_argument("--exclude", action="append", default=None)

    # kojidownload
    parser_koji = subparsers.add_parser("kojidownload", help="Download builds from Koji")
    parser_koji.add_argument("--profile", action="store", default="koji")
    parser_koji.add_argument("--builds", action="store", nargs="+", required=True)

    # Run appropriate command
    args = parser.parse_args()

    config = Config.read_config(args.config) if args.config else Config()
        
    if args.subcommand == "reposync":
        config.output_dir = args.destdir
        reposync = Reposync(args.repofns, args.include, args.exclude)
        reposync.run()
    elif args.subcommand == "kojidownload":
        kojid = KojiDownloader(args.profile, args.builds)
        kojid.run()
    else:
        sources = SourceBuilder.build()
        [source.run() for source in sources]

if __name__ == '__main__':
    main()
