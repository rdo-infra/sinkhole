""" Bunch of utilities
"""

import os.path
import re
import shutil

import requests


def filter_pkgs(pkgs, patterns):
    """ Filter a list of packages according patterns

    Args:
        pkgs (list): List of packages to filter
        patterns (list): List of patterns

    Returns:
        list: a filtered list of packages
    """
    result = []
    for pattern in patterns:
        regex = re.compile(r"^{}$".format(pattern))
        result = [pkg for pkg in pkgs if regex.match(pkg.source_name)]

    return result


def filter_subpkgs(pkgs, patterns):
    """ Filter a list of subpackages according patterns

    Args:
        pkgs (list): List of subpackages to filter
        patterns (list): List of patterns

    Returns:
        list: a filtered list of packages
    """
    result = []
    for pattern in patterns:
        regex = re.compile(r"^{}$".format(pattern))
        for pkg in pkgs:
            if type(pkg) == dict:
                pkg_name = pkg['name']
            else:
                pkg_name = pkg.name
            if regex.match(pkg_name):
                result.append(pkg)

    return result


def download_packages(url, destdir):
    """ direct packages download utility

    Args:
        url: url of the package to download
        destdir: destination directory

    returns:
        bool: success or failure
    """
    pkg_name = url.split("/")[-1]
    path = os.path.join(destdir, pkg_name)
    if os.path.exists(path):
        print("{} already exists. SKIPPED".format(path))
        return True
    response = requests.get(url, allow_redirects=True, stream=True)
    with open(path, 'wb') as fdst:
        shutil.copyfileobj(response.raw, fdst)
    return True
