##############################################################################
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

import os
import re
import shutil
import tempfile
import unittest
import zipfile

import pkg_resources

from zope.testing import doctest, renormalizing

import zc.buildout.testing

def test_symbolic_links():
    """
    >>> mkdir('sample')
    >>> sample = join(sample_buildout, 'sample')
    >>> write(sample, 'buildout.cfg',
    ... '''
    ... [buildout]
    ... parts = sample
    ... find-links = %(link_server)s
    ...
    ... [sample]
    ... recipe = zc.recipe.egg
    ... eggs = sample1
    ... ''' % globals())

    >>> os.symlink('./buildout.cfg', join(sample, 'x'))

    >>> print system(join('bin', 'buildout-source-release')
    ...        +' file://'+sample+' buildout.cfg'),
    ... # doctest: +ELLIPSIS
    Creating source release in sample.tgz
    ...
    >>> test = mkdir('test')
    >>> import tarfile
    >>> tf = tarfile.open('sample.tgz', 'r:gz')
    >>> for name in tf.getnames():
    ...   tf.extract(name, 'test')
    >>> tf.close()

    >>> os.readlink(join('test', 'sample', 'x'))
    'buildout.cfg'

    """


def mkdist(dest, name, **kw):
    options = dict(name=name, version='1.0',
                   url='http://www.zope.org',
                   author='bob', author_email='bob@foo.com')
    options.update(kw)
    d = tempfile.mkdtemp('mkdist')
    try:
        open(os.path.join(d, 'README'), 'w').write('')
        open(os.path.join(d, name+'.py'), 'w').write(py_template % name)
        open(os.path.join(d, 'setup.py'), 'w').write(setup_template % dict(
            name = name,
            options = options,
            ))
        zc.buildout.testing.sdist(d, dest)
    finally:
        shutil.rmtree(d)

py_template = """
def main():
    print 'Hello. My name is ', %r

"""

setup_template = """
from setuptools import setup
setup(py_modules=[%(name)r],
      entry_points = {'console_scripts': ['%(name)s=%(name)s:main']},
      **%(options)r)
"""

def copy_egg(src, dest):
    if os.path.isdir(src):
        zip = zipfile.ZipFile(os.path.join(dest, os.path.basename(src)), 'w')
        lprefix = len(src)+1
        for dir, dirs, files in os.walk(src):
            for file in files:
                path = os.path.join(dir, file)
                zip.write(path, path[lprefix:])
        zip.close()
    else:
        shutil.copy(src, dest)

bo = """
[buildout]
parts = script
find-links = %(link_server)s

[script]
recipe = zc.recipe.egg
eggs = zc.sourcerelease
"""

def setUp(test):
    zc.buildout.testing.buildoutSetUp(test)
    sample_eggs = test.globs['tmpdir']('sample_eggs')
    test.globs['sample_eggs'] = sample_eggs
    os.mkdir(os.path.join(sample_eggs, 'index'))
    mkdist(sample_eggs, 'sample1', install_requires=['sample2'])
    mkdist(sample_eggs, 'sample2')
    test.globs['link_server'] = test.globs['start_server'](
        test.globs['sample_eggs'])

    for project in ('zc.recipe.egg', 'zc.buildout', 'setuptools'):
        dist = pkg_resources.working_set.find(
            pkg_resources.Requirement.parse(project))
        copy_egg(dist.location, sample_eggs)
        if dist.precedence == pkg_resources.DEVELOP_DIST:
            zc.buildout.testing.sdist(os.path.dirname(dist.location),
                                      sample_eggs)
        else:
            copy_egg(dist.location, sample_eggs)

    zc.buildout.testing.install_develop('zc.sourcerelease', test)

    # Set up the buildout-source-release script
    test.globs['write']('buildout.cfg', bo % test.globs)
    test.globs['system'](test.globs['buildout'])

    # Install wacky v 99.99 zc.buildout
    env = pkg_resources.Environment([sample_eggs])
    dist = env['zc.buildout'][0]
    eggname, oldver, pyver = egg_parse(
        os.path.basename(dist.location)
        ).groups()
    dest = os.path.join(sample_eggs, "%s-99.99-py%s.egg" % (eggname, pyver))
    shutil.copy(dist.location, dest)
    zip = zipfile.ZipFile(dest, 'a')
    zip.writestr(
        'EGG-INFO/PKG-INFO',
        zip.read('EGG-INFO/PKG-INFO').replace("Version: %s" % oldver,
                                              "Version: 99.99")
        )
    zip.close()

egg_parse = re.compile('([0-9a-zA-Z_.]+)-([0-9a-zA-Z_.]+)-py(\d[.]\d).egg$'
                       ).match

def test_suite():
    return unittest.TestSuite((
        doctest.DocFileSuite(
            'README.txt',
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
                (re.compile(r'distribute(-?(?:\w|[.-])+\.egg)'),
                    r'setuptools\1'),
                zc.buildout.testing.normalize_path,
                zc.buildout.testing.normalize_egg_py,
                (re.compile(r'-\S+-py'), ''),
                ]),
            ),
        doctest.DocTestSuite(
            setUp=setUp, tearDown=zc.buildout.testing.buildoutTearDown,
            checker=renormalizing.RENormalizing([
                (re.compile(r'distribute(-?(?:\w|[.-])+\.egg)'),
                    r'setuptools\1'),
                zc.buildout.testing.normalize_path,
                zc.buildout.testing.normalize_egg_py,
                (re.compile(r'-\S+-py'), ''),
                ]),
            ),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

