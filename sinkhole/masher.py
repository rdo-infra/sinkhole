""" masher module
"""

from sinkhole.config import Config

try:
    from sh import createrepo_c as createrepo
except ImportError:
    from sh import createrepo


class RepoMasher(object):
    """ Generate RPM repository metadata
    """
    def __init__(self, destdir, revision=None):
        self.destdir = destdir
        config = Config()
        opts = config.masher_opts
        workers = config.masher_workers
        if revision:
            opts = "%s --revision %s" % (opts, revision)
        self.createrepo = createrepo.bake(*opts.split(), workers=workers)

    def run(self):
        print(self.createrepo)
        res = self.createrepo(self.destdir)
        print(res)
