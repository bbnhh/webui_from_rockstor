Creating Source Releases from Buildouts
=======================================

The zc.sourcerelease package provides a script,
buildout-source-release, that generates a source release from a
buildout.  The source release, is in the form of a gzipped tar archive
[#zip_in_future]_.  The generated source release can be used as the
basis for higher-level releases, such as RPMs or
configure-make-make-install releases.

The source releases includes data that would normally be installed in
a download cache, such as Python distributions, or downloads performed
by the zc.recipe.cmmi recipe.  If a buildout uses a recipe that
downloads data but does not store the downloaded data in the buildout
download cache, then the data will not be included in the source
release and will have to be downloaded when the source release is
installed.

The source release includes a Python install script.  It is not
executable and must be run with the desired Python, which must be the
same version of Python used when making the release.  The install
script runs the buildout in place.  This means that the source release
will need to be extracted to and the install script run in the final install
location [#separate_install_step]_.  While the install script can be
used directly, it will more commonly be used by system-packaging
(e.g. RPM) build scripts or make files.

Installation
------------

You can install the buildout-source-release script with easy install::

  easy_install zc.sourcerelease

or you can install it into a buildout using zc.buildout.

Usage
-----

To create a source release, simply run the buildout-source-release
script, passing a file URL or a subversion URL
[#other_source_code_control_systems]_ and the name of the
configuration file to use.  File URLs are useful for testing and can
be used with non-subversion source-code control systems.

Let's look at an example.  We have a server with some distributions on
it.

    >>> index_content = get(link_server)
    >>> if 'distribute' in index_content:
    ...     lines = index_content.splitlines()
    ...     distribute_line = lines.pop(1)
    ...     lines.insert(4, distribute_line)
    ...     index_content = '\n'.join(lines)
    >>> print index_content,
    <html><body>
    <a href="index/">index/</a><br>
    <a href="sample1-1.0.zip">sample1-1.0.zip</a><br>
    <a href="sample2-1.0.zip">sample2-1.0.zip</a><br>
    <a href="setuptools-0.6c7-py2.4.egg">setuptools-0.6-py2.4.egg</a><br>
    <a href="zc.buildout-1.0-py2.4.egg">zc.buildout-1.0-py2.4.egg</a><br>
    <a href="zc.buildout-99.99-pyN.N.egg">zc.buildout-99.99-pyN.N.egg</a><br>
    <a href="zc.recipe.egg-1.0-py2.4.egg">zc.recipe.egg-1.0-py2.4.egg</a><br>
    </body></html>

We have the buildout-source-release installed in a local bin
directory.  We'll create another buildout that we'll use for our
source release.

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

We'll run the release script against this sample directory:

    >>> print system(join('bin', 'buildout-source-release')
    ...        +' file://'+sample+' buildout.cfg'),
    ... # doctest: +ELLIPSIS
    Creating source release in sample.tgz
    ...

We end up with a tar file:

    >>> ls('.')
    -  .installed.cfg
    d  bin
    -  buildout.cfg
    d  develop-eggs
    d  eggs
    d  parts
    d  sample
    -  sample.tgz

If we want to give the file a custom name, in this case something other than
sample.tgz, we can use the '-n' or '--name' option to specify one:

    >>> print system(join('bin', 'buildout-source-release')
    ...        +' file://'+sample+' buildout.cfg -n custom_name_one'),
    ... # doctest: +ELLIPSIS
    Creating source release in custom_name_one.tgz
    ...

    >>> print system(join('bin', 'buildout-source-release')
    ...        +' file://'+sample+' buildout.cfg --name custom_name_two'),
    ... # doctest: +ELLIPSIS
    Creating source release in custom_name_two.tgz
    ...

    >>> ls('.')
    -  .installed.cfg
    d  bin
    -  buildout.cfg
    -  custom_name_one.tgz
    -  custom_name_two.tgz
    d  develop-eggs
    d  eggs
    d  parts
    d  sample
    -  sample.tgz

Let's continue with the example using sample.tgz. Extract the tar file to a
temporary directory:

    >>> mkdir('test')
    >>> import tarfile
    >>> tf = tarfile.open('sample.tgz', 'r:gz')
    >>> for name in tf.getnames():
    ...   tf.extract(name, 'test')
    >>> tf.close()

    >>> ls('test')
    d  sample

    >>> ls('test', 'sample')
    -  buildout.cfg
    d  eggs
    -  install.py
    d  release-distributions

The extracted sample directory has eggs for buildout and setuptools:

    >>> ls('test', 'sample', 'eggs')
    -  setuptools-0.6c7-py2.4.egg
    d  zc.buildout-99.99-py2.4.egg

Note that version 99.99 of zc.buildout was used because it was the
most recent version on the link server.  This happens to be different
than the version of buildout used by the source-release script.

It has a release-distributions directory containing distributions
needed to install the buildout:

    >>> ls('test', 'sample', 'release-distributions', 'dist')
    -  sample1-1.0.zip
    -  sample2-1.0.zip
    -  zc.buildout-99.99-pyN.N.egg
    -  zc.recipe.egg-1.0.0b6-py2.4.egg

(There normally aren't distributions for buildout and setuptools, etc.
because these are pre-installed in the eggs directory of the source
release. In this case, we have a release for zc.buildout because it
was downloaded from the link server.  Anything that we downloaded is
included.)

So, now that we've extracted the source release we built, we can try
to install it.  To do this, we'll to run the installer. Before we do,
however, we'll remove the data used by the link server:

    >>> import os
    >>> mkdir('sample_eggs_aside')
    >>> for p in os.listdir(sample_eggs):
    ...     os.rename(join(sample_eggs, p), join('sample_eggs_aside', p))
    >>> print get(link_server),
    <html><body>
    </body></html>

This way, we know that when we run the source release, the
distributions will come from the release, not from the link
server. Now, let's run the installer:

    >>> import sys

    >>> print system(sys.executable+' '+join('test', 'sample', 'install.py')),
    ... # doctest: +ELLIPSIS
    Creating directory ...


Running the installer simply builds out the saved buildout, using the
release-distribution as the source for installable eggs.  In our case,
we get a sample script that we can run:

    >>> print system(join('test', 'sample', 'bin', 'sample1')),
    Hello. My name is  sample1

Note that the sample bin directory doesn't contain a buildout script:

    >>> ls('test', 'sample', 'bin')
    -  sample1

If we want one, we can run the install script again with an argument
of 'bootstrap'.

    >>> print system(sys.executable+
    ...        ' '+join('test', 'sample', 'install.py bootstrap')),
    Generated script '/sample-buildout/test/sample/bin/buildout'.

    >>> ls('test', 'sample', 'bin')
    -  buildout
    -  sample1

Note that the install script is a specialized buildout script, so
other buildout options can be provided, although this shouldn't
normally be necessary.

Often, we'll use file URLs for testing, but store the buildouts to be
released in a source code repository like subversion.  We've created a
simple sample in subversion. Let's try to install it:

    >>> print system(join('bin', 'buildout-source-release')+' '+
    ...     'svn://svn.zope.org/repos/main/zc.sourcerelease/svnsample'+
    ...     ' release.cfg'),
    ... # doctest: +ELLIPSIS
    Creating source release in svnsample.tgz
    ... The referenced section, 'repos', was not defined.

The svnsample config, release.cfg, has::

  find-links = ${repos:svnsample}

Here, the expectation is that the value will be provided by a user's
default.cfg.  We'll provide a value that points to our link
server. First, we'll put the sample eggs back on the link server:

    >>> for p in os.listdir('sample_eggs_aside'):
    ...     os.rename(join('sample_eggs_aside', p), join(sample_eggs, p))
    >>> remove('sample_eggs_aside')

    >>> print system(join('bin', 'buildout-source-release')+' '+
    ...     'svn://svn.zope.org/repos/main/zc.sourcerelease/svnsample'+
    ...     ' release.cfg'+
    ...     ' repos:svnsample='+link_server),
    ... # doctest: +ELLIPSIS
    Creating source release in svnsample.tgz
    ...

    >>> ls('.')
    -  .installed.cfg
    d  bin
    -  buildout.cfg
    -  custom_name_one.tgz
    -  custom_name_two.tgz
    d  develop-eggs
    d  eggs
    d  parts
    d  sample
    -  sample.tgz
    -  svnsample.tgz
    d  test

    >>> mkdir('svntest')
    >>> import tarfile
    >>> tf = tarfile.open('svnsample.tgz', 'r:gz')
    >>> for name in tf.getnames():
    ...   tf.extract(name, 'svntest')
    >>> tf.close()

    >>> print system(sys.executable
    ...              +' '+join('svntest', 'svnsample', 'install.py')),
    ... # doctest: +ELLIPSIS
    Creating directory ...

    >>> print system(join('svntest', 'svnsample', 'bin', 'sample')),
    sample from svn called

You can specify a different configuration file of course.  Let's
create one with an error as it contains an absolute path for the
eggs-directory.

    >>> write(sample, 'wrong.cfg',
    ... '''
    ... [buildout]
    ... parts = sample
    ... find-links = %(link_server)s
    ... eggs-directory = /somewhere/shared-eggs
    ...
    ... [sample]
    ... recipe = zc.recipe.egg
    ... eggs = sample1
    ... ''' % globals())

We'll run the release script against this configuration file:

    >>> print system(join('bin', 'buildout-source-release')
    ...        +' file://'+sample+' wrong.cfg'),
    ... # doctest: +ELLIPSIS
    Creating source release in sample.tgz
    Invalid eggs directory (perhaps not a relative path) /somewhere/shared-eggs

.. [#zip_in_future] It is possible that an option will be added in the
  future to generate zip files rather than tar archives.

.. [#separate_install_step] In the future, it is likely that we'll
  also support a model in which the install script can install to a
  separate location.  Buildouts will have to take this into account,
  providing for copying necessary files, other than just scripts and
  eggs, into the destination directory.

.. [#other_source_code_control_systems] Other source
  code control systems may be supported in the future. In the mean
  time, you can check a project out to a directory and then use a file
  URL to get the buildout-source-release script to use it.
