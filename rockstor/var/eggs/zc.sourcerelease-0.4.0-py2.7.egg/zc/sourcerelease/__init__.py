#############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

import optparse
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urlparse

import pkg_resources

import zc.buildout.buildout

def _system(*args):
    p = subprocess.Popen(args)
    r = p.wait()
    if r:
        raise SystemError("Subprocess failed!")

def _relative(path, to):
    rel = []

    # Remove trailing separators
    while 1:
        d, b = os.path.split(to)
        if b:
            break
        to = d

    while path and path != to and path != '/':
        path, base = os.path.split(path)
        if base:
            rel.insert(0, base)
    if path != to:
        return None
    return os.path.join(*rel)

def source_release(args=None):
    if args is None:
        args = sys.argv[1:]

    # set up command line options
    parser = optparse.OptionParser()
    parser.add_option("-n", "--name", dest="filename",
        help="create custom named files", default="None")

    # retrieve options
    (options, args) = parser.parse_args(args)

    url = args.pop(0)
    config = args.pop(0)

    clopts = []
    for arg in args:
        name, value = arg.split('=', 1)
        section, option = name.split(':')
        clopts.append((section, option, value))

    name = url.split('/')[-1]

    # use optparse to find custom filename
    if options.filename != 'None':
        name = options.filename

    t1 = tempfile.mkdtemp('source-release1')
    t2 = tempfile.mkdtemp('source-release2')
    co1 = os.path.join(t1, name)
    co2 = os.path.join(t2, name)
    here = os.getcwd()
    print 'Creating source release in %s.tgz' % name
    sys.stdout.flush()
    try:

        if url.startswith('file://'):
            shutil.copytree(urlparse.urlparse(url)[2], co1, symlinks=True)
        else:
            _system('svn', 'export', url, co1)
        shutil.copytree(co1, co2, symlinks=True)
        cache = os.path.join(co2, 'release-distributions')
        os.mkdir(cache)
        buildout = zc.buildout.buildout.Buildout(
            os.path.join(co1, config), clopts,
            False, False, 'bootstrap',
            )
        eggs_directory = buildout['buildout']['eggs-directory']
        reggs = _relative(eggs_directory, co1)
        if reggs is None:
            print 'Invalid eggs directory (perhaps not a relative path)', \
                eggs_directory
            sys.exit(0)

        buildout.bootstrap([])

        buildargs = args[:]+[
            '-Uvc', os.path.join(co1, config),
            'buildout:download-cache='+cache
            ]

        _system(os.path.join(co1, 'bin', 'buildout'), *buildargs)

        os.chdir(here)

        env = pkg_resources.Environment([eggs_directory])
        projects = ['zc.buildout']
        if env['setuptools']:
            projects.append('setuptools')
        else:
            projects.append('distribute')
        dists = [env[project][0].location
                 for project in projects]

        eggs = os.path.join(co2, reggs)
        os.mkdir(eggs)
        for dist in dists:
            if os.path.isdir(dist):
                shutil.copytree(dist,
                                os.path.join(eggs, os.path.basename(dist)),
                                symlinks=True)
            else:
                shutil.copy(dist, eggs)


        open(os.path.join(co2, 'install.py'), 'w').write(
            install_template % dict(
                path = [os.path.basename(dist) for dist in dists],
                config = config,
                version = sys.version_info[:2],
                eggs_directory = reggs,
                args = args and repr(args)[1:-1]+',' or '',
            ))


        tar = tarfile.open(name+'.tgz', 'w:gz')
        tar.add(co2, name)
        tar.close()


    finally:
        shutil.rmtree(t1)
        shutil.rmtree(t2)

install_template = """
import os, sys

if sys.version_info[:2] != %(version)r:
    print "Invalid Python version, %%s.%%s." %% sys.version_info[:2]
    print "Python %%s.%%s is required." %% %(version)r
    sys.exit(1)

here = os.path.abspath(os.path.dirname(__file__))

sys.path[0:0] = [
    os.path.join(here, %(eggs_directory)r, dist)
    for dist in %(path)r
    ]
config = os.path.join(here, %(config)r)

import zc.buildout.buildout
zc.buildout.buildout.main([
    %(args)s
    '-Uc', config,
    'buildout:download-cache='+os.path.join(here, 'release-distributions'),
    'buildout:install-from-cache=true',
    ]+sys.argv[1:])
"""
