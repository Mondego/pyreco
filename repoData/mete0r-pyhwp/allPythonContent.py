__FILENAME__ = bootstrap
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
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.
"""

import os
import shutil
import sys
import tempfile

from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --find-links to point to local resources, you can keep 
this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", help="use a specific zc.buildout version")

parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", "--config-file",
                  help=("Specify the path to the buildout configuration "
                        "file to be used."))
parser.add_option("-f", "--find-links",
                  help=("Specify a URL to search for buildout releases"))


options, args = parser.parse_args()

######################################################################
# load/install setuptools

to_reload = False
try:
    import pkg_resources
    import setuptools
except ImportError:
    ez = {}

    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib2 import urlopen

    # XXX use a more permanent ez_setup.py URL when available.
    exec(urlopen('https://bitbucket.org/pypa/setuptools/raw/0.7.2/ez_setup.py'
                ).read(), ez)
    setup_args = dict(to_dir=tmpeggs, download_delay=0)
    ez['use_setuptools'](**setup_args)

    if to_reload:
        reload(pkg_resources)
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

######################################################################
# Install buildout

ws = pkg_resources.working_set

cmd = [sys.executable, '-c',
       'from setuptools.command.easy_install import main; main()',
       '-mZqNxd', tmpeggs]

find_links = os.environ.get(
    'bootstrap-testing-find-links',
    options.find_links or
    ('http://downloads.buildout.org/'
     if options.accept_buildout_test_releases else None)
    )
if find_links:
    cmd.extend(['-f', find_links])

setuptools_path = ws.find(
    pkg_resources.Requirement.parse('setuptools')).location

requirement = 'zc.buildout'
version = options.version
if version is None and not options.accept_buildout_test_releases:
    # Figure out the most recent final version of zc.buildout.
    import setuptools.package_index
    _final_parts = '*final-', '*final'

    def _final_version(parsed_version):
        for part in parsed_version:
            if (part[:1] == '*') and (part not in _final_parts):
                return False
        return True
    index = setuptools.package_index.PackageIndex(
        search_path=[setuptools_path])
    if find_links:
        index.add_find_links((find_links,))
    req = pkg_resources.Requirement.parse(requirement)
    if index.obtain(req) is not None:
        best = []
        bestv = None
        for dist in index[req.project_name]:
            distv = dist.parsed_version
            if _final_version(distv):
                if bestv is None or distv > bestv:
                    best = [dist]
                    bestv = distv
                elif distv == bestv:
                    best.append(dist)
        if best:
            best.sort()
            version = best[-1].version
if version:
    requirement = '=='.join((requirement, version))
cmd.append(requirement)

import subprocess
if subprocess.call(cmd, env=dict(os.environ, PYTHONPATH=setuptools_path)) != 0:
    raise Exception(
        "Failed to execute command:\n%s",
        repr(cmd)[1:-1])

######################################################################
# Import and run buildout

ws.add_entry(tmpeggs)
ws.require(requirement)
import zc.buildout.buildout

if not [a for a in args if '=' not in a]:
    args.append('bootstrap')

# if -c was provided, we push it back into args for buildout' main function
if options.config_file is not None:
    args[0:0] = ['-c', options.config_file]

zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = bootstrap_me
# -*- coding: utf-8 -*-

import os.path
import sys


def main():
    role = len(sys.argv) > 1 and sys.argv[1] or 'user'

    this_dir = os.path.dirname(__file__)
    dst_path = os.path.join(this_dir, 'buildout.cfg')
    with file(dst_path, 'w') as f:
        f.write('[buildout]\n')
        f.write('extends = buildouts/' + role + '.cfg\n')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# pyhwp documentation build configuration file, created by
# sphinx-quickstart on Sat Mar 10 15:30:24 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
import os.path

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                '..', 'pyhwp')))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['templates']
locale_dirs = ['translated']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'pyhwp'
copyright = u'2012, mete0r'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The full version, including alpha/beta/rc tags.
from hwp5 import __version__ as hwp5_release
release = hwp5_release
if release.endswith('-dirty'):
    release = release[:-len('-dirty')]

# The short X.Y version.
import re
version_match = re.match(r'([0-9]+\.[0-9]+).*', release)
if version_match:
  version = version_match.group(1)
else:
  version = 'develop'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['.build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'pyhwpdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'pyhwp.tex', u'pyhwp Documentation',
   u'mete0r', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'pyhwp', u'pyhwp Documentation',
     [u'mete0r'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'pyhwp', u'pyhwp Documentation',
   u'mete0r', 'pyhwp', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = cleanup-pyc
# -*- coding: utf-8 -*-
import logging
import os.path


logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


def find_files(root):
    import os
    import os.path
    for name in os.listdir(root):
        path = os.path.join(root, name)
        yield path
        if os.path.isdir(path):
            for x in find_files(path):
                yield x


def find_pyc_files(root):
    for path in find_files(root):
        if path.endswith('.pyc') or path.endswith('$py.class'):
            yield path


def main():
    import sys
    import os.path

    logging.basicConfig(level=logging.INFO)

    for root in sys.argv[1:]:
        if os.path.isdir(root):
            for path in find_pyc_files(root):
                if not os.path.isdir(path):
                    logger.info('unlink %s', path)
                    os.unlink(path)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = copylxml
import sys
import os.path
import shutil

def main():
    if sys.platform == 'win32':
        try:
            import lxml
        except ImportError:
            print 'no lxml found'
        else:
            lxml_path = os.path.dirname(lxml.__file__)
            dest_path = os.path.join(sys.argv[1], 'lxml')
            shutil.copytree(lxml_path, dest_path)
        sys.exit(0)
    else:
        sys.exit(os.system('pip install lxml'))


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = fix-coverage
# -*- coding: utf-8 -*-
''' fix pyhwp source paths in coverage.xml
'''
import re
import sys


def main():
    f = file(sys.argv[2], 'w')
    try:
        for line in file(sys.argv[1]):
            line = re.sub('filename="[^"]*/hwp5/', 'filename="pyhwp/hwp5/', line)
            f.write(line)
    finally:
        f.close()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = mkdir
# -*- coding: utf-8 -*-

import sys
import os.path
import shutil

if __name__ == '__main__':
    d = sys.argv[1]
    if os.path.exists(d):
        print('rmtree: %s' % d)
        shutil.rmtree(d)
    print('mkdir: %s' % d)
    os.makedirs(d)

########NEW FILE########
__FILENAME__ = prepare-hwp5-xsl-fixtures
# -*- coding: utf-8 -*-
from __future__ import with_statement
import os.path
import logging
import sys


logger = logging.getLogger('hwp5.xsltests')


def find_hwp5files(dir):
    import glob
    return glob.glob(os.path.join(dir, '*.hwp'))


def main():
    doc = ''' convert fixture hwp5 files into *.xml

    Usage:
        prepare [--fixtures-dir=<dir>] [--out-dir=<dir>]
        prepare --help

    Options:
        -h --help               Show this screen
           --fixtures-dir=<dir> Fixture directory
           --out-dir=<dir>      Output directory
    '''
    from docopt import docopt
    from hwp5.xmlmodel import Hwp5File

    args = docopt(doc, version='0.0')

    logging.getLogger().addHandler(logging.StreamHandler())
    logging.getLogger('hwp5.xsltests').setLevel(logging.INFO)

    if args['--fixtures-dir']:
        fixture_dir = args['--fixtures-dir']
    else:
        import hwp5
        hwp5_pkgdir = os.path.dirname(hwp5.__file__)
        fixture_dir = os.path.join(hwp5_pkgdir, 'tests', 'fixtures')

    out_dir = args['--out-dir']

    for path in find_hwp5files(fixture_dir):
        name = os.path.basename(path)
        rootname = os.path.splitext(name)[0]
        out_path = rootname + '.xml'
        if out_dir is not None:
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            out_path = os.path.join(out_dir, out_path)

        logger.info('%s', out_path)

        opts = {}
        try:
            hwp5file = Hwp5File(path)
            with file(out_path, 'w') as f:
                hwp5file.xmlevents(**opts).dump(f)
        except Exception:
            e = sys.exc_info()[1]
            logger.exception(e)


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = redirect
from __future__ import with_statement
import subprocess
import sys

if __name__ == '__main__':
    with file(sys.argv[1], 'wb') as f:
        p = subprocess.Popen(sys.argv[2:], stdout=f)
        p.wait()
        raise SystemExit(p.returncode)

########NEW FILE########
__FILENAME__ = test-cli
# -*- coding: utf-8 -*-
import os.path
import logging


logger = logging.getLogger('test-cli')


def main():
    logging.basicConfig(level=logging.INFO)

    if not os.path.exists('/bin/sh'):
        logger.warning('/bin/sh: not-found')
        logger.warning('skipping test-cli')
        return 0

    d = 'pyhwp-tests'
    shscript = os.path.join(d, 'hwp5_cli_tests.sh')

    cmd = ['/bin/sh', shscript]
    cmd = ' '.join(cmd)
    logger.info('running: %s', cmd)
    ret = os.system(cmd)
    logger.info('exit with %d', ret)
    if ret != 0:
        raise SystemExit(-1)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test-in-lo
#!/usr/bin/python
# -*- coding: utf-8 -*-

def main():
    import os
    args = ['${buildout:bin-directory}/oxt-test',
            '${buildout:parts-directory}/test']
    os.system(' '.join(args))


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = components
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010,2011,2012 mete0r@sarangbang.or.kr
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import logging
import os


# initialize logging system
logger = logging.getLogger('hwp5')

loglevel = os.environ.get('PYHWP_LOGLEVEL')
if loglevel:
    loglevel = dict(DEBUG=logging.DEBUG,
                    INFO=logging.INFO,
                    WARNING=logging.WARNING,
                    ERROR=logging.ERROR,
                    CRITICAL=logging.CRITICAL).get(loglevel.upper(),
                                                   logging.WARNING)
    logger.setLevel(loglevel)
del loglevel

filename = os.environ.get('PYHWP_LOGFILE')
if filename:
    logger.addHandler(logging.FileHandler(filename))
del filename


import sys
logger.info('sys.executable = %s', sys.executable)
logger.info('sys.version = %s', sys.version)
logger.info('sys.path:')
for path in sys.path:
    logger.info('- %s', path)


try:
    import uno
    import unohelper
    import unokit
    from unokit.util import propseq_to_dict
    from unokit.util import dict_to_propseq
    from unokit.util import xenumeration_list
    from unokit.adapters import InputStreamFromFileLike

    from com.sun.star.lang import XInitialization
    from com.sun.star.document import XFilter, XImporter, XExtendedFilterDetection
    from com.sun.star.task import XJobExecutor

    def log_exception(f):
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception, e:
                logger.exception(e)
                raise
        return wrapper

    g_ImplementationHelper = unohelper.ImplementationHelper()

    def implementation(component_name, *services):
        def decorator(cls):
            g_ImplementationHelper.addImplementation(cls, component_name, services)
            return cls
        return decorator


    @implementation('hwp5.Detector', 'com.sun.star.document.ExtendedTypeDetection')
    class Detector(unokit.Base, XExtendedFilterDetection):

        @log_exception
        @unokit.component_context
        def detect(self, mediadesc):
            from hwp5_uno import typedetect

            logger.info('hwp5.Detector detect()')

            desc = propseq_to_dict(mediadesc)
            for k, v in desc.items():
                logger.debug('\t%s: %s', k, v)

            inputstream = desc['InputStream']

            typename = typedetect(inputstream)

            logger.info('hwp5.Detector: %s detected.', typename)
            return typename, mediadesc


    @implementation('hwp5.Importer', 'com.sun.star.document.ImportFilter')
    class Importer(unokit.Base, XInitialization, XFilter, XImporter):

        @log_exception
        @unokit.component_context
        def initialize(self, args):
            logger.debug('Importer initialize: %s', args)

        @log_exception
        @unokit.component_context
        def setTargetDocument(self, target):
            logger.debug('Importer setTargetDocument: %s', target)
            self.target = target

        @log_exception
        @unokit.component_context
        def filter(self, mediadesc):
            from hwp5.dataio import ParseError
            from hwp5_uno import HwpFileFromInputStream
            from hwp5_uno import load_hwp5file_into_doc

            logger.debug('Importer filter')
            desc = propseq_to_dict(mediadesc)

            logger.debug('mediadesc: %s', str(desc.keys()))
            for k, v in desc.iteritems():
                logger.debug('%s: %s', k, str(v))

            statusindicator = desc.get('StatusIndicator')

            inputstream = desc['InputStream']
            hwpfile = HwpFileFromInputStream(inputstream)
            try:
                load_hwp5file_into_doc(hwpfile, self.target, statusindicator)
            except ParseError, e:
                e.print_to_logger(logger)
                return False
            except Exception, e:
                logger.exception(e)
                return False
            else:
                return True

        @unokit.component_context
        def cancel(self):
            logger.debug('Importer cancel')


    @implementation('hwp5.TestJob')
    class TestJob(unokit.Base, XJobExecutor):

        @unokit.component_context
        def trigger(self, args):
            logger.debug('testjob %s', args)

            wd = args

            import os
            original_wd = os.getcwd()
            try:
                os.chdir(wd)

                from unittest import TextTestRunner
                testrunner = TextTestRunner()

                from unittest import TestSuite
                testrunner.run(TestSuite(self.tests()))
            finally:
                os.chdir(original_wd)

        def tests(self):
            from unittest import defaultTestLoader
            yield defaultTestLoader.loadTestsFromTestCase(DetectorTest)
            yield defaultTestLoader.loadTestsFromTestCase(ImporterTest)
            from hwp5_uno.tests import test_hwp5_uno
            yield defaultTestLoader.loadTestsFromModule(test_hwp5_uno)
            from hwp5.tests import test_suite
            yield test_suite()


    from unittest import TestCase
    class DetectorTest(TestCase):

        def test_detect(self):
            context = uno.getComponentContext()

            from hwp5.tests.fixtures import open_fixture
            f = open_fixture('sample-5017.hwp', 'rb')
            stream = InputStreamFromFileLike(f)
            mediadesc = dict_to_propseq(dict(InputStream=stream))

            svm = context.ServiceManager
            detector = svm.createInstanceWithContext('hwp5.Detector', context)
            typename, mediadesc2 = detector.detect(mediadesc)
            self.assertEquals('hwp5', typename)

    class ImporterTest(TestCase):

        def test_filter(self):
            context = uno.getComponentContext()
            from hwp5.tests.fixtures import open_fixture
            f = open_fixture('sample-5017.hwp', 'rb')
            stream = InputStreamFromFileLike(f)
            mediadesc = dict_to_propseq(dict(InputStream=stream))

            svm = context.ServiceManager
            importer = svm.createInstanceWithContext('hwp5.Importer', context)
            desktop = svm.createInstanceWithContext('com.sun.star.frame.Desktop',
                                                    context)
            doc = desktop.loadComponentFromURL('private:factory/swriter', '_blank',
                                               0, ())

            importer.setTargetDocument(doc)
            importer.filter(mediadesc)

            text = doc.getText()

            paragraphs = text.createEnumeration()
            paragraphs = xenumeration_list(paragraphs)
            for paragraph_ix, paragraph in enumerate(paragraphs):
                logger.info('Paragraph %s', paragraph_ix)
                logger.debug('%s', paragraph)

                services = paragraph.SupportedServiceNames
                if 'com.sun.star.text.Paragraph' in services:
                    portions = xenumeration_list(paragraph.createEnumeration())
                    for portion_ix, portion in enumerate(portions):
                        logger.info('Portion %s: %s', portion_ix,
                                     portion.TextPortionType)
                        if portion.TextPortionType == 'Text':
                            logger.info('- %s', portion.getString())
                        elif portion.TextPortionType == 'Frame':
                            logger.debug('%s', portion)
                            textcontent_name = 'com.sun.star.text.TextContent'
                            en = portion.createContentEnumeration(textcontent_name)
                            contents = xenumeration_list(en)
                            for content in contents:
                                logger.debug('content: %s', content)
                                content_services = content.SupportedServiceNames
                                if ('com.sun.star.drawing.GraphicObjectShape' in
                                    content_services):
                                    logger.info('graphic url: %s',
                                                 content.GraphicURL)
                                    logger.info('graphic stream url: %s',
                                                 content.GraphicStreamURL)
                if 'com.sun.star.text.TextTable' in services:
                    pass
                else:
                    pass

            paragraph_portions = paragraphs[0].createEnumeration()
            paragraph_portions = xenumeration_list(paragraph_portions)
            self.assertEquals(u'한글 ', paragraph_portions[0].getString())

            paragraph_portions = paragraphs[16].createEnumeration()
            paragraph_portions = xenumeration_list(paragraph_portions)
            contents = paragraph_portions[1].createContentEnumeration('com.sun.star.text.TextContent')
            contents = xenumeration_list(contents)
            self.assertEquals('image/x-vclgraphic', contents[0].Bitmap.MimeType)
            #self.assertEquals('vnd.sun.star.Package:bindata/BIN0003.png',
            #                  contents[0].GraphicStreamURL)

            graphics = doc.getGraphicObjects()
            graphics = xenumeration_list(graphics.createEnumeration())
            logger.debug('graphic: %s', graphics)

            frames = doc.getTextFrames()
            frames = xenumeration_list(frames.createEnumeration())
            logger.debug('frames: %s', frames)
except Exception, e:
    logger.exception(e)
    raise

########NEW FILE########
__FILENAME__ = binmodel
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import logging
logger = logging.getLogger(__name__)

from .dataio import (PrimitiveType,
                     CompoundType,
                     ArrayType,
                     StructType, Struct, Flags, Enum, BYTE, WORD, UINT32,
                     UINT16, INT32, INT16, UINT8, INT8, DOUBLE, ARRAY, N_ARRAY,
                     SHWPUNIT, HWPUNIT16, HWPUNIT, BSTR, WCHAR)
from .dataio import HexBytes
from .tagids import (tagnames, HWPTAG_DOCUMENT_PROPERTIES, HWPTAG_ID_MAPPINGS,
                     HWPTAG_BIN_DATA, HWPTAG_FACE_NAME, HWPTAG_BORDER_FILL,
                     HWPTAG_CHAR_SHAPE, HWPTAG_TAB_DEF, HWPTAG_NUMBERING,
                     HWPTAG_BULLET, HWPTAG_PARA_SHAPE, HWPTAG_STYLE,
                     HWPTAG_DOC_DATA, HWPTAG_DISTRIBUTE_DOC_DATA,
                     HWPTAG_COMPATIBLE_DOCUMENT, HWPTAG_LAYOUT_COMPATIBILITY,
                     HWPTAG_PARA_HEADER, HWPTAG_PARA_TEXT,
                     HWPTAG_PARA_CHAR_SHAPE, HWPTAG_PARA_LINE_SEG,
                     HWPTAG_PARA_RANGE_TAG, HWPTAG_CTRL_HEADER,
                     HWPTAG_LIST_HEADER, HWPTAG_PAGE_DEF,
                     HWPTAG_FOOTNOTE_SHAPE, HWPTAG_PAGE_BORDER_FILL,
                     HWPTAG_SHAPE_COMPONENT, HWPTAG_TABLE,
                     HWPTAG_SHAPE_COMPONENT_LINE,
                     HWPTAG_SHAPE_COMPONENT_RECTANGLE,
                     HWPTAG_SHAPE_COMPONENT_ELLIPSE,
                     HWPTAG_SHAPE_COMPONENT_ARC,
                     HWPTAG_SHAPE_COMPONENT_POLYGON,
                     HWPTAG_SHAPE_COMPONENT_CURVE, HWPTAG_SHAPE_COMPONENT_OLE,
                     HWPTAG_SHAPE_COMPONENT_PICTURE,
                     HWPTAG_SHAPE_COMPONENT_CONTAINER, HWPTAG_CTRL_DATA,
                     HWPTAG_CTRL_EQEDIT, HWPTAG_SHAPE_COMPONENT_TEXTART,
                     HWPTAG_FORBIDDEN_CHAR)
from .importhelper import importStringIO
from . import dataio
from hwp5.recordstream import nth


StringIO = importStringIO()


def ref_parent_member(member_name):
    def f(context, values):
        context, model = context['parent']
        return model['content'][member_name]
    f.__doc__ = 'PARENTREC.' + member_name
    return f


tag_models = dict()


class RecordModelType(StructType):

    def __new__(mcs, name, bases, attrs):
        cls = StructType.__new__(mcs, name, bases, attrs)
        if 'tagid' in attrs:
            tagid = attrs['tagid']
            assert tagid not in tag_models
            tag_models[tagid] = cls
        return cls


class RecordModel(object):
    __metaclass__ = RecordModelType


class DocumentProperties(RecordModel):
    tagid = HWPTAG_DOCUMENT_PROPERTIES

    def attributes():
        yield UINT16, 'section_count',
        yield UINT16, 'page_startnum',
        yield UINT16, 'footnote_startnum',
        yield UINT16, 'endnote_startnum',
        yield UINT16, 'picture_startnum',
        yield UINT16, 'table_startnum',
        yield UINT16, 'math_startnum',
        yield UINT32, 'list_id',
        yield UINT32, 'paragraph_id',
        yield UINT32, 'character_unit_loc_in_paragraph',
        #yield UINT32, 'flags',   # DIFFSPEC
    attributes = staticmethod(attributes)


class IdMappings(RecordModel):
    tagid = HWPTAG_ID_MAPPINGS

    def attributes():
        yield UINT32, 'bindata',
        yield UINT32, 'ko_fonts',
        yield UINT32, 'en_fonts',
        yield UINT32, 'cn_fonts',
        yield UINT32, 'jp_fonts',
        yield UINT32, 'other_fonts',
        yield UINT32, 'symbol_fonts',
        yield UINT32, 'user_fonts',
        yield UINT32, 'borderfills',
        yield UINT32, 'charshapes',
        yield UINT32, 'tabdefs',
        yield UINT32, 'numberings',
        yield UINT32, 'bullets',
        yield UINT32, 'parashapes',
        yield UINT32, 'styles',
        # TODO: memoshapes does not exist at least 5.0.1.6
        yield dict(type=UINT32, name='memoshapes', version=(5, 0, 1, 7))
    attributes = staticmethod(attributes)


class BinStorageId(UINT16):
    pass


class BinDataLink(Struct):
    def attributes():
        yield BSTR, 'abspath'
        yield BSTR, 'relpath'
    attributes = staticmethod(attributes)


class BinDataEmbedding(Struct):
    def attributes():
        yield BinStorageId, 'storage_id'
        yield BSTR, 'ext'
    attributes = staticmethod(attributes)


class BinDataStorage(Struct):
    def attributes():
        yield BinStorageId, 'storage_id'
    attributes = staticmethod(attributes)


class BinData(RecordModel):
    tagid = HWPTAG_BIN_DATA
    StorageType = Enum(LINK=0, EMBEDDING=1, STORAGE=2)
    CompressionType = Enum(STORAGE_DEFAULT=0, YES=1, NO=2)
    AccessState = Enum(NEVER=0, OK=1, FAILED=2, FAILED_IGNORED=3)
    Flags = Flags(UINT16,
                  0, 3, StorageType, 'storage',
                  4, 5, CompressionType, 'compression',
                  16, 17, AccessState, 'access')

    def attributes(cls):
        from hwp5.dataio import SelectiveType
        from hwp5.dataio import ref_member_flag
        yield cls.Flags, 'flags'
        yield (SelectiveType(ref_member_flag('flags', 'storage'),
                             {cls.StorageType.LINK: BinDataLink,
                              cls.StorageType.EMBEDDING: BinDataEmbedding,
                              cls.StorageType.STORAGE: BinDataStorage}),
               'bindata')
    attributes = classmethod(attributes)


class AlternateFont(Struct):
    def attributes():
        yield BYTE, 'kind'
        yield BSTR, 'name'
    attributes = staticmethod(attributes)


class Panose1(Struct):

    FamilyType = Enum('any', 'no_fit', 'text_display', 'script', 'decorative',
                      'pictorial')

    SerifStyle = Enum('any', 'no_fit', 'cove', 'obtuse_cove', 'square_cove',
                      'obtuse_square_cove', 'square', 'thin', 'bone',
                      'exaggerated', 'triangle', 'normal_sans', 'obtuse_sans',
                      'perp_sans', 'flared', 'rounded')

    Weight = Enum('any', 'no_fit', 'very_light', 'light', 'thin', 'book',
                  'medium', 'demi', 'bold', 'heavy', 'black', 'nord')

    Proportion = Enum('any', 'no_fit', 'old_style', 'modern', 'even_width',
                      'expanded', 'condensed', 'very_expanded',
                      'very_condensed', 'monospaced')

    Contrast = Enum('any', 'no_fit', 'none', 'very_low', 'low', 'medium_low',
                    'medium', 'medium_high', 'high', 'very_high')

    StrokeVariation = Enum('any', 'no_fit', 'gradual_diag', 'gradual_tran',
                           'gradual_vert', 'gradual_horz', 'rapid_vert',
                           'rapid_horz', 'instant_vert')

    ArmStyle = Enum('any', 'no_fit', 'straight_horz', 'straight_wedge',
                    'straight_vert', 'straight_single_serif',
                    'straight_double_serif', 'bent_horz', 'bent_wedge',
                    'bent_vert', 'bent_single_serif', 'bent_double_serif')

    Letterform = Enum('any', 'no_fit', 'normal_contact', 'normal_weighted',
                      'normal_boxed', 'normal_flattened', 'normal_rounded',
                      'normal_off_center', 'normal_square', 'oblique_contact',
                      'oblique_weighted', 'oblique_boxed', 'oblique_flattened',
                      'oblique_rounded', 'oblique_off_center',
                      'oblique_square')

    Midline = Enum('any', 'no_fit', 'standard_trimmed', 'standard_pointed',
                   'standard_serifed', 'high_trimmed', 'high_pointed',
                   'high_serifed', 'constant_trimmed', 'constant_pointed',
                   'constant_serifed', 'low_trimmed', 'low_pointed',
                   'low_serifed')

    XHeight = Enum('any', 'no_fit', 'constant_small', 'constant_std',
                   'constant_large', 'ducking_small', 'ducking_std',
                   'ducking_large')

    def attributes():
        yield BYTE, 'family_type',
        yield BYTE, 'serif_style',
        yield BYTE, 'weight',
        yield BYTE, 'proportion',
        yield BYTE, 'contrast',
        yield BYTE, 'stroke_variation',
        yield BYTE, 'arm_style',
        yield BYTE, 'letterform',
        yield BYTE, 'midline',
        yield BYTE, 'x_height',
    attributes = staticmethod(attributes)


class FaceName(RecordModel):
    tagid = HWPTAG_FACE_NAME
    FontFileType = Enum(UNKNOWN=0, TTF=1, HFT=2)
    Flags = Flags(BYTE,
                  0, 1, FontFileType, 'font_file_type',
                  5, 'default',
                  6, 'metric',
                  7, 'alternate')

    def attributes(cls):
        yield cls.Flags, 'flags'
        yield BSTR, 'name'

        def has_alternate(context, values):
            ''' flags.alternate == 1 '''
            return values['flags'].alternate

        def has_metric(context, values):
            ''' flags.metric == 1 '''
            return values['flags'].metric

        def has_default(context, values):
            ''' flags.default == 1 '''
            return values['flags'].default

        yield dict(type=AlternateFont, name='alternate_font',
                   condition=has_alternate)
        yield dict(type=Panose1, name='panose1', condition=has_metric)
        yield dict(type=BSTR, name='default_font', condition=has_default)
    attributes = classmethod(attributes)


class COLORREF(int):
    __metaclass__ = PrimitiveType
    binfmt = INT32.binfmt
    never_instantiate = False

    def __getattr__(self, name):
        if name == 'r':
            return self & 0xff
        elif name == 'g':
            return (self & 0xff00) >> 8
        elif name == 'b':
            return (self & 0xff0000) >> 16
        elif name == 'a':
            return int((self & 0xff000000) >> 24)
        elif name == 'rgb':
            return self.r, self.g, self.b

    def __str__(self):
        return '#%02x%02x%02x' % (self.r, self.g, self.b)

    def __repr__(self):
        class_name = self.__class__.__name__
        value = '(0x%02x, 0x%02x, 0x%02x)' % self.rgb
        return class_name + value


class Border(Struct):

    # 표 20 테두리선 종류
    StrokeEnum = Enum('none', 'solid',
                      'dashed', 'dotted', 'dash-dot', 'dash-dot-dot',
                      'long-dash', 'large-dot',
                      'double', 'double-2', 'double-3', 'triple',
                      'wave', 'double-wave',
                      'inset', 'outset', 'groove', 'ridge')
    StrokeType = Flags(UINT8,
                       0, 4, StrokeEnum, 'stroke_type')

    # 표 21 테두리선 굵기
    widths = {'0.1mm': 0,
              '0.12mm': 1,
              '0.15mm': 2,
              '0.2mm': 3,
              '0.25mm': 4,
              '0.3mm': 5,
              '0.4mm': 6,
              '0.5mm': 7,
              '0.6mm': 8,
              '0.7mm': 9,
              '1.0mm': 10,
              '1.5mm': 11,
              '2.0mm': 12,
              '3.0mm': 13,
              '4.0mm': 14,
              '5.0mm': 15}
    WidthEnum = Enum(**widths)
    Width = Flags(UINT8,
                  0, 4, WidthEnum, 'width')

    def attributes(cls):
        yield cls.StrokeType, 'stroke_flags',
        yield cls.Width, 'width_flags',
        yield COLORREF, 'color',
    attributes = classmethod(attributes)


class Fill(Struct):
    pass


class FillNone(Fill):
    def attributes():
        yield UINT32, 'size',  # SPEC is confusing
    attributes = staticmethod(attributes)


class FillColorPattern(Fill):
    ''' 표 23 채우기 정보 '''
    PatternTypeEnum = Enum(NONE=255, HORIZONTAL=0, VERTICAL=1, BACKSLASH=2,
                           SLASH=3, GRID=4, CROSS=5)
    PatternTypeFlags = Flags(UINT32,
                             0, 7, PatternTypeEnum, 'pattern_type')

    def attributes(cls):
        yield COLORREF, 'background_color',
        yield COLORREF, 'pattern_color',
        yield cls.PatternTypeFlags, 'pattern_type_flags',
    attributes = classmethod(attributes)


class FillImage(Fill):
    def attributes():
        yield UINT32, 'flags'
        yield BinStorageId, 'storage_id'
    attributes = staticmethod(attributes)


class Coord32(Struct):
    def attributes():
        yield UINT32, 'x'
        yield UINT32, 'y'
    attributes = staticmethod(attributes)


class FillGradation(Fill):
    def attributes():
        yield BYTE,   'type',
        yield UINT32, 'shear',
        yield Coord32, 'center',
        yield UINT32, 'blur',
        yield N_ARRAY(UINT32, COLORREF), 'colors',
    attributes = staticmethod(attributes)


class BorderFill(RecordModel):
    tagid = HWPTAG_BORDER_FILL

    BorderFlags = Flags(UINT16,
                        0, 'effect_3d',
                        1, 'effect_shadow',
                        2, 4, 'slash',
                        5, 6, 'backslash')

    FillFlags = Flags(UINT32,
                      0, 'colorpattern',
                      1, 'image',
                      2, 'gradation')

    def attributes(cls):
        yield cls.BorderFlags, 'borderflags'
        yield Border, 'left',
        yield Border, 'right',
        yield Border, 'top',
        yield Border, 'bottom',
        yield Border, 'diagonal'
        yield cls.FillFlags, 'fillflags'

        def fill_colorpattern(context, values):
            ''' fillflags.fill_colorpattern '''
            return values['fillflags'].colorpattern

        def fill_image(context, values):
            ''' fillflags.fill_image '''
            return values['fillflags'].image

        def fill_gradation(context, values):
            ''' fillflags.fill_gradation '''
            return values['fillflags'].gradation

        yield dict(type=FillColorPattern, name='fill_colorpattern',
                   condition=fill_colorpattern)
        yield dict(type=FillGradation, name='fill_gradation',
                   condition=fill_gradation)
        yield dict(type=FillImage, name='fill_image',
                   condition=fill_image)
        yield UINT32, 'shape'
        yield dict(type=BYTE, name='blur_center',
                   condition=fill_gradation)
    attributes = classmethod(attributes)


def LanguageStruct(name, basetype):
    def attributes():
        for lang in ('ko', 'en', 'cn', 'jp', 'other', 'symbol', 'user'):
            yield basetype, lang
    attributes = staticmethod(attributes)
    return StructType(name, (Struct,), dict(basetype=basetype,
                                            attributes=attributes))


class ShadowSpace(Struct):
    def attributes():
        yield INT8, 'x'
        yield INT8, 'y'
    attributes = staticmethod(attributes)


class CharShape(RecordModel):
    tagid = HWPTAG_CHAR_SHAPE

    Underline = Enum(NONE=0, UNDERLINE=1, UNKNOWN=2, UPPERLINE=3)
    Flags = Flags(UINT32,
                  0, 'italic',
                  1, 'bold',
                  2, 3, Underline, 'underline',
                  4, 7, 'underline_style',
                  8, 10, 'outline',
                  11, 13, 'shadow')

    def attributes(cls):
        yield LanguageStruct('FontFace', WORD), 'font_face',
        yield (LanguageStruct('LetterWidthExpansion', UINT8),
               'letter_width_expansion')
        yield LanguageStruct('LetterSpacing', INT8), 'letter_spacing'
        yield LanguageStruct('RelativeSize', INT8), 'relative_size'
        yield LanguageStruct('Position', INT8), 'position'
        yield INT32, 'basesize',
        yield cls.Flags, 'charshapeflags',
        yield ShadowSpace, 'shadow_space'
        yield COLORREF, 'text_color',
        yield COLORREF, 'underline_color',
        yield COLORREF, 'shade_color',
        yield COLORREF, 'shadow_color',
        #yield UINT16, 'borderfill_id',        # DIFFSPEC
        #yield COLORREF, 'strikeoutColor',    # DIFFSPEC
    attributes = classmethod(attributes)


class TabDef(RecordModel):
    tagid = HWPTAG_TAB_DEF

    def attributes():
        # SPEC is confusing
        yield dict(type=UINT32, name='unknown1', version=(5, 0, 1, 7))
        yield dict(type=UINT32, name='unknown2', version=(5, 0, 1, 7))
        #yield UINT32, 'attr',
        #yield UINT16, 'count',
        #yield HWPUNIT, 'pos',
        #yield UINT8, 'kind',
        #yield UINT8, 'fillType',
        #yield UINT16, 'reserved',
    attributes = staticmethod(attributes)


class Numbering(RecordModel):
    tagid = HWPTAG_NUMBERING
    Align = Enum(LEFT=0, CENTER=1, RIGHT=2)
    DistanceType = Enum(RATIO=0, VALUE=1)
    Flags = Flags(UINT32,
                  0, 1, Align, 'paragraph_align',
                  2, 'auto_width',
                  3, 'auto_dedent',
                  4, DistanceType, 'distance_to_body_type')

    def attributes(cls):
        yield cls.Flags, 'flags'
        yield HWPUNIT16, 'width_correction'
        yield HWPUNIT16, 'distance_to_body'
        yield UINT32, 'charshape_id'  # SPEC ?????
    attributes = classmethod(attributes)


class Bullet(RecordModel):
    tagid = HWPTAG_BULLET


class ParaShape(RecordModel):
    ''' 4.1.10. 문단 모양 '''
    tagid = HWPTAG_PARA_SHAPE
    LineSpacingType = Enum(RATIO=0, FIXED=1, SPACEONLY=2, MINIMUM=3)
    Align = Enum(BOTH=0, LEFT=1, RIGHT=2, CENTER=3, DISTRIBUTE=4,
                 DISTRIBUTE_SPACE=5)
    VAlign = Enum(FONT=0, TOP=1, CENTER=2, BOTTOM=3)
    LineBreakAlphabet = Enum(WORD=0, HYPHEN=1, CHAR=2)
    LineBreakHangul = Enum(WORD=0, CHAR=1)
    HeadShape = Enum(NONE=0, OUTLINE=1, NUMBER=2, BULLET=3)
    Flags = Flags(UINT32,
                  0, 1, LineSpacingType, 'linespacing_type',
                  2, 4, Align, 'align',
                  5, 6, LineBreakAlphabet, 'linebreak_alphabet',
                  7, LineBreakHangul, 'linebreak_hangul',
                  8, 'use_paper_grid',
                  9, 15, 'minimum_space',  # 공백 최소값
                  16, 'protect_single_line',  # 외톨이줄 보호
                  17, 'with_next_paragraph',  # 다음 문단과 함께
                  18, 'protect',  # 문단 보호
                  19, 'start_new_page',  # 문단 앞에서 항상 쪽 나눔
                  20, 21, VAlign, 'valign',
                  22, 'lineheight_along_fontsize',  # 글꼴에 어울리는 줄 높이
                  23, 24, HeadShape, 'head_shape',  # 문단 머리 모양
                  25, 27, 'level',  # 문단 수준
                  28, 'linked_border',  # 문단 테두리 연결 여부
                  29, 'ignore_margin',  # 문단 여백 무시
                  30, 'tail_shape')  # 문단 꼬리 모양

    Flags2 = dataio.Flags(UINT32,
                          0, 1, 'in_single_line',
                          2, 3, 'reserved',
                          4, 'autospace_alphabet',
                          5, 'autospace_number')

    Flags3 = dataio.Flags(UINT32,
                          0, 4, LineSpacingType, 'linespacing_type3')

    def attributes(cls):
        yield cls.Flags, 'parashapeflags',
        yield INT32,  'doubled_margin_left',   # 1/7200 * 2 # DIFFSPEC
        yield INT32,  'doubled_margin_right',  # 1/7200 * 2
        yield SHWPUNIT,  'indent',
        yield INT32,  'doubled_margin_top',    # 1/7200 * 2
        yield INT32,  'doubled_margin_bottom',  # 1/7200 * 2
        yield SHWPUNIT,  'linespacing',
        yield UINT16, 'tabdef_id',
        yield UINT16, 'numbering_bullet_id',
        yield UINT16, 'borderfill_id',
        yield HWPUNIT16,  'border_left',
        yield HWPUNIT16,  'border_right',
        yield HWPUNIT16,  'border_top',
        yield HWPUNIT16,  'border_bottom',
        yield dict(type=cls.Flags2, name='flags2', version=(5, 0, 1, 7))
        #yield cls.Flags3, 'flags3',   # DIFFSPEC
        #yield UINT32, 'lineSpacing',  # DIFFSPEC
    attributes = classmethod(attributes)


class Style(RecordModel):
    tagid = HWPTAG_STYLE

    Kind = Enum(PARAGRAPH=0, CHAR=1)
    Flags = Flags(BYTE,
                  0, 1, Kind, 'kind')

    def attributes(cls):
        yield BSTR, 'local_name',
        yield BSTR, 'name',
        yield cls.Flags, 'flags',
        yield BYTE, 'next_style_id',
        yield INT16, 'lang_id',
        yield UINT16, 'parashape_id',
        yield UINT16, 'charshape_id',
        yield dict(type=UINT16, name='unknown', version=(5, 0, 0, 5))  # SPEC
    attributes = classmethod(attributes)


class DocData(RecordModel):
    tagid = HWPTAG_DOC_DATA


class DistributeDocData(RecordModel):
    tagid = HWPTAG_DISTRIBUTE_DOC_DATA


class CompatibleDocument(RecordModel):
    tagid = HWPTAG_COMPATIBLE_DOCUMENT
    Target = Enum(DEFAULT=0, HWP2007=1, MSWORD=2)
    Flags = dataio.Flags(UINT32,
                         0, 1, 'target')

    def attributes(cls):
        yield cls.Flags, 'flags'
    attributes = classmethod(attributes)


class LayoutCompatibility(RecordModel):
    tagid = HWPTAG_LAYOUT_COMPATIBILITY

    def attributes():
        yield UINT32, 'char',
        yield UINT32, 'paragraph',
        yield UINT32, 'section',
        yield UINT32, 'object',
        yield UINT32, 'field',
    attributes = staticmethod(attributes)


class CHID(str):
    __metaclass__ = PrimitiveType

    fixed_size = 4

    # Common controls
    GSO = 'gso '
    TBL = 'tbl '
    LINE = '$lin'
    RECT = '$rec'
    ELLI = '$ell'
    ARC = '$arc'
    POLY = '$pol'
    CURV = '$cur'
    EQED = 'eqed'
    PICT = '$pic'
    OLE = '$ole'
    CONTAINER = '$con'

    # Controls
    SECD = 'secd'
    COLD = 'cold'
    HEADER = 'head'
    FOOTER = 'foot'
    FN = 'fn  '
    EN = 'en  '
    ATNO = 'atno'
    NWNO = 'nwno'
    PGHD = 'pghd'
    PGCT = 'pgct'
    PGNP = 'pgnp'
    IDXM = 'idxm'
    BOKM = 'bokm'
    TCPS = 'tcps'
    TDUT = 'tdut'
    TCMT = 'tcmt'

    # Field starts
    UNK = '%unk'
    DTE = '%dte'
    #...
    HLK = '%hlk'

    def decode(bytes, context=None):
        return bytes[3] + bytes[2] + bytes[1] + bytes[0]
    decode = staticmethod(decode)


control_models = dict()


class ControlType(RecordModelType):

    def __new__(mcs, name, bases, attrs):
        cls = RecordModelType.__new__(mcs, name, bases, attrs)
        if 'chid' in attrs:
            chid = attrs['chid']
            assert chid not in control_models
            control_models[chid] = cls
        return cls


class Control(RecordModel):
    __metaclass__ = ControlType
    tagid = HWPTAG_CTRL_HEADER

    def attributes():
        yield CHID, 'chid'
    attributes = staticmethod(attributes)

    extension_types = control_models

    def get_extension_key(cls, context, model):
        ''' chid '''
        return model['content']['chid']
    get_extension_key = classmethod(get_extension_key)


class Margin(Struct):
    def attributes():
        yield HWPUNIT16, 'left'
        yield HWPUNIT16, 'right'
        yield HWPUNIT16, 'top'
        yield HWPUNIT16, 'bottom'
    attributes = staticmethod(attributes)


class CommonControl(Control):
    Flow = Enum(FLOAT=0, BLOCK=1, BACK=2, FRONT=3)
    TextSide = Enum(BOTH=0, LEFT=1, RIGHT=2, LARGER=3)
    VRelTo = Enum(PAPER=0, PAGE=1, PARAGRAPH=2)
    HRelTo = Enum(PAPER=0, PAGE=1, COLUMN=2, PARAGRAPH=3)
    VAlign = Enum(TOP=0, MIDDLE=1, BOTTOM=2)
    HAlign = Enum(LEFT=0, CENTER=1, RIGHT=2, INSIDE=3, OUTSIDE=4)
    WidthRelTo = Enum(PAPER=0, PAGE=1, COLUMN=2, PARAGRAPH=3, ABSOLUTE=4)
    HeightRelTo = Enum(PAPER=0, PAGE=1, ABSOLUTE=2)
    NumberCategory = Enum(NONE=0, FIGURE=1, TABLE=2, EQUATION=3)

    CommonControlFlags = dataio.Flags(UINT32,
                                      0, 'inline',
                                      2, 'affect_line_spacing',
                                      3, 4, VRelTo, 'vrelto',
                                      5, 7, VAlign, 'valign',
                                      8, 9, HRelTo, 'hrelto',
                                      10, 12, HAlign, 'halign',
                                      13, 'restrict_in_page',
                                      14, 'overlap_others',
                                      15, 17, WidthRelTo, 'width_relto',
                                      18, 19, HeightRelTo, 'height_relto',
                                      20, 'protect_size_when_vrelto_paragraph',
                                      21, 23, Flow, 'flow',
                                      24, 25, TextSide, 'text_side',
                                      26, 27, NumberCategory, 'number_category'
                                      )

    MARGIN_LEFT = 0
    MARGIN_RIGHT = 1
    MARGIN_TOP = 2
    MARGIN_BOTTOM = 3

    def attributes(cls):
        yield cls.CommonControlFlags, 'flags',
        yield SHWPUNIT, 'y',    # DIFFSPEC
        yield SHWPUNIT, 'x',    # DIFFSPEC
        yield HWPUNIT, 'width',
        yield HWPUNIT, 'height',
        yield INT16, 'z_order',
        yield INT16, 'unknown1',
        yield Margin, 'margin',
        yield UINT32, 'instance_id',
        yield dict(type=INT16, name='unknown2', version=(5, 0, 0, 5))
        yield dict(type=BSTR, name='description', version=(5, 0, 0, 5))
    attributes = classmethod(attributes)


class TableControl(CommonControl):
    chid = CHID.TBL

    def on_child(cls, attributes, context, child):
        child_context, child_model = child
        if child_model['type'] is TableBody:
            context['table_body'] = True
    on_child = classmethod(on_child)


list_header_models = dict()


class ListHeaderType(RecordModelType):

    def __new__(mcs, name, bases, attrs):
        cls = RecordModelType.__new__(mcs, name, bases, attrs)
        if 'parent_model_type' in attrs:
            parent_model_type = attrs['parent_model_type']
            before_tablebody = attrs.get('before_tablebody', False)
            list_type_key = parent_model_type, before_tablebody
            assert list_type_key not in list_header_models
            list_header_models[list_type_key] = cls
        return cls


class ListHeader(RecordModel):
    __metaclass__ = ListHeaderType
    tagid = HWPTAG_LIST_HEADER

    VAlign = Enum(TOP=0, MIDDLE=1, BOTTOM=2)
    Flags = Flags(UINT32,
                  0, 2, 'textdirection',
                  3, 4, 'linebreak',
                  5, 6, VAlign, 'valign')

    def attributes(cls):
        yield UINT16, 'paragraphs',
        yield UINT16, 'unknown1',
        yield cls.Flags, 'listflags',
    attributes = classmethod(attributes)

    extension_types = list_header_models

    def get_extension_key(context, model):
        ''' (parent model type, after TableBody) '''
        if 'parent' in context:
            context, model = context['parent']
            return model['type'], context.get('table_body', False)
    get_extension_key = staticmethod(get_extension_key)


class PageDef(RecordModel):
    tagid = HWPTAG_PAGE_DEF
    Orientation = Enum(PORTRAIT=0, LANDSCAPE=1)
    BookBinding = Enum(LEFT=0, RIGHT=1, TOP=2, BOTTOM=3)
    Flags = Flags(UINT32,
                  0, Orientation, 'orientation',
                  1, 2, BookBinding, 'bookbinding')

    def attributes(cls):
        yield HWPUNIT, 'width',
        yield HWPUNIT, 'height',
        yield HWPUNIT, 'left_offset',
        yield HWPUNIT, 'right_offset',
        yield HWPUNIT, 'top_offset',
        yield HWPUNIT, 'bottom_offset',
        yield HWPUNIT, 'header_offset',
        yield HWPUNIT, 'footer_offset',
        yield HWPUNIT, 'bookbinding_offset',
        yield cls.Flags, 'attr',
        #yield UINT32, 'attr',
    attributes = classmethod(attributes)

    def getDimension(self):
        width = HWPUNIT(self.paper_width - self.offsetLeft - self.offsetRight)
        height = HWPUNIT(self.paper_height
                         - (self.offsetTop + self.offsetHeader)
                         - (self.offsetBottom + self.offsetFooter))
        if self.attr.landscape:
            return (height, width)
        else:
            return (width, height)
    dimension = property(getDimension)

    def getHeight(self):
        if self.attr.landscape:
            width = HWPUNIT(self.paper_width - self.offsetLeft -
                            self.offsetRight)
            return width
        else:
            height = HWPUNIT(self.paper_height
                             - (self.offsetTop + self.offsetHeader)
                             - (self.offsetBottom + self.offsetFooter))
            return height
    height = property(getHeight)

    def getWidth(self):
        if self.attr.landscape:
            height = HWPUNIT(self.paper_height
                             - (self.offsetTop + self.offsetHeader)
                             - (self.offsetBottom + self.offsetFooter))
            return height
        else:
            width = HWPUNIT(self.paper_width - self.offsetLeft -
                            self.offsetRight)
            return width
    width = property(getWidth)


class FootnoteShape(RecordModel):
    tagid = HWPTAG_FOOTNOTE_SHAPE
    Flags = Flags(UINT32)

    def attributes(cls):
        yield cls.Flags, 'flags'
        yield WCHAR, 'usersymbol'
        yield WCHAR, 'prefix'
        yield WCHAR, 'suffix'
        yield UINT16, 'starting_number'
        yield HWPUNIT16, 'splitter_length'
        yield HWPUNIT16, 'splitter_unknown'
        yield HWPUNIT16, 'splitter_margin_top'
        yield HWPUNIT16, 'splitter_margin_bottom'
        yield HWPUNIT16, 'notes_spacing'
        yield Border.StrokeType, 'splitter_stroke_type'
        yield Border.Width, 'splitter_width'
        yield dict(type=COLORREF, name='splitter_color', version=(5, 0, 0, 6))
    attributes = classmethod(attributes)


class PageBorderFill(RecordModel):
    tagid = HWPTAG_PAGE_BORDER_FILL
    RelativeTo = Enum(BODY=0, PAPER=1)
    FillArea = Enum(PAPER=0, PAGE=1, BORDER=2)
    Flags = Flags(UINT32,
                  0, RelativeTo, 'relative_to',
                  1, 'include_header',
                  2, 'include_footer',
                  3, 4, FillArea, 'fill')

    def attributes(cls):
        yield cls.Flags, 'flags'
        yield Margin, 'margin'
        yield UINT16, 'borderfill_id'
    attributes = classmethod(attributes)


class TableCaption(ListHeader):
    parent_model_type = TableControl
    before_tablebody = False

    Position = Enum(LEFT=0, RIGHT=1, TOP=2, BOTTOM=3)
    Flags = Flags(UINT32,
                  0, 1, Position, 'position',
                  2, 'include_margin')

    def attributes(cls):
        yield cls.Flags, 'flags',
        yield HWPUNIT, 'width',
        yield HWPUNIT16, 'separation',  # 캡션과 틀 사이 간격
        yield HWPUNIT, 'maxsize',
    attributes = classmethod(attributes)


class TableCell(ListHeader):
    parent_model_type = TableControl
    before_tablebody = True

    def attributes():
        yield UINT16, 'col',
        yield UINT16, 'row',
        yield UINT16, 'colspan',
        yield UINT16, 'rowspan',
        yield SHWPUNIT, 'width',
        yield SHWPUNIT, 'height',
        yield Margin, 'padding',
        yield UINT16, 'borderfill_id',
        yield SHWPUNIT, 'unknown_width',
    attributes = staticmethod(attributes)


class ZoneInfo(Struct):
    def attributes():
        yield UINT16, 'starting_column'
        yield UINT16, 'starting_row'
        yield UINT16, 'end_column'
        yield UINT16, 'end_row'
        yield UINT16, 'borderfill_id'
    attributes = staticmethod(attributes)


class TableBody(RecordModel):
    tagid = HWPTAG_TABLE
    Split = Enum(NONE=0, BY_CELL=1, SPLIT=2)
    Flags = Flags(UINT32,
                  0, 1, Split, 'split_page',
                  2, 'repeat_header')

    def attributes(cls):
        from hwp5.dataio import X_ARRAY
        from hwp5.dataio import ref_member
        yield cls.Flags, 'flags'
        yield UINT16, 'rows'
        yield UINT16, 'cols'
        yield HWPUNIT16, 'cellspacing'
        yield Margin, 'padding'
        yield dict(type=X_ARRAY(UINT16, ref_member('rows')),
                   name='rowcols')
        yield UINT16, 'borderfill_id'
        yield dict(type=N_ARRAY(UINT16, ZoneInfo),
                   name='validZones',
                   version=(5, 0, 0, 7))
    attributes = classmethod(attributes)


class Paragraph(RecordModel):
    tagid = HWPTAG_PARA_HEADER

    SplitFlags = Flags(BYTE,
                       0, 'new_section',
                       1, 'new_columnsdef',
                       2, 'new_page',
                       3, 'new_column')
    ControlMask = Flags(UINT32,
                        2, 'unknown1',
                        11, 'control',
                        21, 'new_number')
    Flags = Flags(UINT32,
                  31, 'unknown',
                  0, 30, 'chars')

    def attributes(cls):
        yield cls.Flags, 'text',
        yield cls.ControlMask, 'controlmask',
        yield UINT16, 'parashape_id',
        yield BYTE, 'style_id',
        yield cls.SplitFlags, 'split',
        yield UINT16, 'charshapes',
        yield UINT16, 'rangetags',
        yield UINT16, 'linesegs',
        yield UINT32, 'instance_id',
    attributes = classmethod(attributes)


class ControlChar(object):
    class CHAR(object):
        size = 1

    class INLINE(object):
        size = 8

    class EXTENDED(object):
        size = 8
    chars = {0x00: ('NULL', CHAR),
             0x01: ('CTLCHR01', EXTENDED),
             0x02: ('SECTION_COLUMN_DEF', EXTENDED),
             0x03: ('FIELD_START', EXTENDED),
             0x04: ('FIELD_END', INLINE),
             0x05: ('CTLCHR05', INLINE),
             0x06: ('CTLCHR06', INLINE),
             0x07: ('CTLCHR07', INLINE),
             0x08: ('TITLE_MARK', INLINE),
             0x09: ('TAB', INLINE),
             0x0a: ('LINE_BREAK', CHAR),
             0x0b: ('DRAWING_TABLE_OBJECT', EXTENDED),
             0x0c: ('CTLCHR0C', EXTENDED),
             0x0d: ('PARAGRAPH_BREAK', CHAR),
             0x0e: ('CTLCHR0E', EXTENDED),
             0x0f: ('HIDDEN_EXPLANATION', EXTENDED),
             0x10: ('HEADER_FOOTER', EXTENDED),
             0x11: ('FOOT_END_NOTE', EXTENDED),
             0x12: ('AUTO_NUMBER', EXTENDED),
             0x13: ('CTLCHR13', INLINE),
             0x14: ('CTLCHR14', INLINE),
             0x15: ('PAGE_CTLCHR', EXTENDED),
             0x16: ('BOOKMARK', EXTENDED),
             0x17: ('CTLCHR17', EXTENDED),
             0x18: ('HYPHEN', CHAR),
             0x1e: ('NONBREAK_SPACE', CHAR),
             0x1f: ('FIXWIDTH_SPACE', CHAR)}
    names = dict((unichr(code), name) for code, (name, kind) in chars.items())
    kinds = dict((unichr(code), kind) for code, (name, kind) in chars.items())

    def _populate(cls):
        for ch, name in cls.names.items():
            setattr(cls, name, ch)
    _populate = classmethod(_populate)
    import re
    regex = re.compile('[\x00-\x1f]\x00')

    def find(cls, data, start_idx):
        while True:
            m = cls.regex.search(data, start_idx)
            if m is not None:
                i = m.start()
                if i & 1 == 1:
                    start_idx = i + 1
                    continue
                char = unichr(ord(data[i]))
                size = cls.kinds[char].size
                return i, i + (size * 2)
            data_len = len(data)
            return data_len, data_len
    find = classmethod(find)

    def decode(cls, bytes):
        code = UINT16.decode(bytes[0:2])
        ch = unichr(code)
        if cls.kinds[ch].size == 8:
            bytes = bytes[2:2 + 12]
            if ch == ControlChar.TAB:
                param = dict(width=UINT32.decode(bytes[0:4]),
                             unknown0=UINT8.decode(bytes[4:5]),
                             unknown1=UINT8.decode(bytes[5:6]),
                             unknown2=bytes[6:])
                return dict(code=code, param=param)
            else:
                chid = CHID.decode(bytes[0:4])
                param = bytes[4:12]
                return dict(code=code, chid=chid, param=param)
        else:
            return dict(code=code)
    decode = classmethod(decode)

    def get_kind_by_code(cls, code):
        ch = unichr(code)
        return cls.kinds[ch]
    get_kind_by_code = classmethod(get_kind_by_code)

    def get_name_by_code(cls, code):
        ch = unichr(code)
        return cls.names.get(ch, 'CTLCHR%02x' % code)
    get_name_by_code = classmethod(get_name_by_code)

ControlChar._populate()


class Text(object):
    pass


class ParaTextChunks(list):
    __metaclass__ = CompoundType

    def read(cls, f):
        bytes = f.read()
        return [x for x in cls.parse_chunks(bytes)]
    read = classmethod(read)

    def parse_chunks(bytes):
        from hwp5.dataio import decode_utf16le_with_hypua
        size = len(bytes)
        idx = 0
        while idx < size:
            ctrlpos, ctrlpos_end = ControlChar.find(bytes, idx)
            if idx < ctrlpos:
                text = decode_utf16le_with_hypua(bytes[idx:ctrlpos])
                yield (idx / 2, ctrlpos / 2), text
            if ctrlpos < ctrlpos_end:
                cch = ControlChar.decode(bytes[ctrlpos:ctrlpos_end])
                yield (ctrlpos / 2, ctrlpos_end / 2), cch
            idx = ctrlpos_end
    parse_chunks = staticmethod(parse_chunks)


class ParaText(RecordModel):
    tagid = HWPTAG_PARA_TEXT

    def attributes():
        yield ParaTextChunks, 'chunks'
    attributes = staticmethod(attributes)


class ParaCharShapeList(list):
    __metaclass__ = ArrayType
    itemtype = ARRAY(UINT16, 2)

    def read(cls, f, context):
        bytes = f.read()
        return cls.decode(bytes, context)
    read = classmethod(read)

    def decode(payload, context=None):
        import struct
        fmt = 'II'
        unitsize = struct.calcsize('<' + fmt)
        unitcount = len(payload) / unitsize
        values = struct.unpack('<' + (fmt * unitcount), payload)
        return list(tuple(values[i * 2:i * 2 + 2])
                    for i in range(0, unitcount))
    decode = staticmethod(decode)


class ParaCharShape(RecordModel):
    tagid = HWPTAG_PARA_CHAR_SHAPE

    def attributes():
        from hwp5.dataio import X_ARRAY
        yield dict(name='charshapes',
                   type=X_ARRAY(ARRAY(UINT32, 2),
                                ref_parent_member('charshapes')))
    attributes = staticmethod(attributes)


class LineSeg(Struct):
    Flags = Flags(UINT16,
                  4, 'indented')

    def attributes(cls):
        yield INT32, 'chpos',
        yield SHWPUNIT, 'y',
        yield SHWPUNIT, 'height',
        yield SHWPUNIT, 'height2',
        yield SHWPUNIT, 'height85',
        yield SHWPUNIT, 'space_below',
        yield SHWPUNIT, 'x',
        yield SHWPUNIT, 'width'
        yield UINT16, 'a8'
        yield cls.Flags, 'flags'
    attributes = classmethod(attributes)


class ParaLineSegList(list):
    __metaclass__ = ArrayType
    itemtype = LineSeg

    def read(cls, f, context):
        payload = context['stream'].read()
        return cls.decode(context, payload)
    read = classmethod(read)

    def decode(cls, context, payload):
        from itertools import izip
        import struct
        unitfmt = 'iiiiiiiiHH'
        unitsize = struct.calcsize('<' + unitfmt)
        unitcount = len(payload) / unitsize
        values = struct.unpack('<' + unitfmt * unitcount, payload)
        names = ['chpos', 'y', 'height', 'height2', 'height85', 'space_below',
                 'x', 'width', 'a8', 'flags']
        x = list(dict(izip(names, tuple(values[i * 10:i * 10 + 10])))
                 for i in range(0, unitcount))
        for d in x:
            d['flags'] = LineSeg.Flags(d['flags'])
        return x
    decode = classmethod(decode)


class ParaLineSeg(RecordModel):
    tagid = HWPTAG_PARA_LINE_SEG

    def attributes(cls):
        from hwp5.dataio import X_ARRAY
        yield dict(name='linesegs',
                   type=X_ARRAY(LineSeg, ref_parent_member('linesegs')))
    attributes = classmethod(attributes)


class ParaRangeTag(RecordModel):
    tagid = HWPTAG_PARA_RANGE_TAG

    def attributes():
        yield UINT32, 'start'
        yield UINT32, 'end'
        yield UINT32, 'tag'
        # TODO: SPEC
    attributes = staticmethod(attributes)


class GShapeObjectControl(CommonControl):
    chid = CHID.GSO


class Matrix(Struct):
    ''' 2D Transform Matrix

    [a c e][x]
    [b d f][y]
    [0 0 1][1]
    '''
    def attributes():
        yield DOUBLE, 'a'
        yield DOUBLE, 'c'
        yield DOUBLE, 'e'
        yield DOUBLE, 'b'
        yield DOUBLE, 'd'
        yield DOUBLE, 'f'
    attributes = staticmethod(attributes)


class ScaleRotationMatrix(Struct):
    def attributes():
        yield Matrix, 'scaler',
        yield Matrix, 'rotator',
    attributes = staticmethod(attributes)


class Coord(Struct):
    def attributes():
        yield SHWPUNIT, 'x'
        yield SHWPUNIT, 'y'
    attributes = staticmethod(attributes)


class BorderLine(Struct):
    ''' 표 81. 테두리 선 정보 '''

    LineEnd = Enum('round', 'flat')
    ArrowShape = Enum('none', 'arrow', 'arrow2', 'diamond', 'circle', 'rect',
                      'diamondfilled', 'disc', 'rectfilled')
    ArrowSize = Enum('smallest', 'smaller', 'small', 'abitsmall', 'normal',
                     'abitlarge', 'large', 'larger', 'largest')
    Flags = Flags(UINT32,
                  0, 5, Border.StrokeEnum, 'stroke',
                  6, 9, LineEnd, 'line_end',
                  10, 15, ArrowShape, 'arrow_start',
                  16, 21, ArrowShape, 'arrow_end',
                  22, 25, ArrowSize, 'arrow_start_size',
                  26, 29, ArrowSize, 'arrow_end_size',
                  30, 'arrow_start_fill',
                  31, 'arrow_end_fill')

    def attributes(cls):
        yield COLORREF, 'color'
        yield INT32, 'width'
        yield cls.Flags, 'flags'
    attributes = classmethod(attributes)


class ShapeComponent(RecordModel):
    ''' 4.2.9.2 그리기 개체 '''
    tagid = HWPTAG_SHAPE_COMPONENT
    FillFlags = Flags(UINT16,
                      8, 'fill_colorpattern',
                      9, 'fill_image',
                      10, 'fill_gradation')
    Flags = Flags(UINT32,
                  0, 'flip')

    def attributes(cls):
        from hwp5.dataio import X_ARRAY
        from hwp5.dataio import ref_member

        def parent_must_be_gso(context, values):
            ''' parent record type is GShapeObjectControl '''
            # GSO-child ShapeComponent specific:
            # it may be a GSO model's attribute, e.g. 'child_chid'
            if 'parent' in context:
                parent_context, parent_model = context['parent']
                return parent_model['type'] is GShapeObjectControl

        yield dict(type=CHID, name='chid0', condition=parent_must_be_gso)

        yield CHID, 'chid'
        yield SHWPUNIT, 'x_in_group'
        yield SHWPUNIT, 'y_in_group'
        yield WORD, 'level_in_group'
        yield WORD, 'local_version'
        yield SHWPUNIT, 'initial_width'
        yield SHWPUNIT, 'initial_height'
        yield SHWPUNIT, 'width'
        yield SHWPUNIT, 'height'
        yield cls.Flags, 'flags'
        yield WORD, 'angle'
        yield Coord, 'rotation_center'
        yield WORD, 'scalerotations_count'
        yield Matrix, 'translation'
        yield dict(type=X_ARRAY(ScaleRotationMatrix,
                                ref_member('scalerotations_count')),
                   name='scalerotations')

        def chid_is_container(context, values):
            ''' chid == CHID.CONTAINER '''
            return values['chid'] == CHID.CONTAINER
        yield dict(type=N_ARRAY(WORD, CHID),
                   name='controls',
                   condition=chid_is_container)

        def chid_is_rect(context, values):
            ''' chid == CHID.RECT '''
            return values['chid'] == CHID.RECT

        def chid_is_rect_and_fill_colorpattern(context, values):
            ''' chid == CHID.RECT and fill_flags.fill_colorpattern '''
            return (values['chid'] == CHID.RECT and
                    values['fill_flags'].fill_colorpattern)

        def chid_is_rect_and_fill_image(context, values):
            ''' chid == CHID.RECT and fill_flags.fill_image '''
            return (values['chid'] == CHID.RECT and
                    values['fill_flags'].fill_image)

        def chid_is_rect_and_fill_gradation(context, values):
            ''' chid == CHID.RECT and fill_flags.fill_gradation '''
            return (values['chid'] == CHID.RECT and
                    values['fill_flags'].fill_gradation)

        yield dict(type=BorderLine, name='border', condition=chid_is_rect)
        yield dict(type=cls.FillFlags, name='fill_flags',
                   condition=chid_is_rect)
        yield dict(type=UINT16, name='unknown', condition=chid_is_rect)
        yield dict(type=UINT8, name='unknown1', condition=chid_is_rect)
        yield dict(type=FillColorPattern, name='fill_colorpattern',
                   condition=chid_is_rect_and_fill_colorpattern)
        yield dict(type=FillGradation, name='fill_gradation',
                   condition=chid_is_rect_and_fill_gradation)
        yield dict(type=FillImage, name='fill_image',
                   condition=chid_is_rect_and_fill_image)
        yield dict(type=UINT32, name='fill_shape',
                   condition=chid_is_rect)
        yield dict(type=BYTE, name='fill_blur_center',
                   condition=chid_is_rect_and_fill_gradation)

        # TODO: 아래 두 필드: chid == $rec일 때만인지 확인 필요
        yield dict(type=HexBytes(5), name='unknown2',
                   condition=chid_is_rect, version=(5, 0, 2, 4))
        yield dict(type=HexBytes(16), name='unknown3',
                   condition=chid_is_rect, version=(5, 0, 2, 4))

        def chid_is_line(context, values):
            ''' chid == CHID.LINE '''
            return values['chid'] == CHID.LINE

        yield dict(type=BorderLine, name='line',
                   condition=chid_is_line)
    attributes = classmethod(attributes)


class TextboxParagraphList(ListHeader):
    parent_model_type = ShapeComponent

    def attributes():
        yield Margin, 'padding'
        yield HWPUNIT, 'maxwidth'
    attributes = staticmethod(attributes)


class ShapeLine(RecordModel):
    tagid = HWPTAG_SHAPE_COMPONENT_LINE

    def attributes():
        yield Coord, 'p0'
        yield Coord, 'p1'
        yield UINT16, 'attr'
    attributes = staticmethod(attributes)


class ShapeRectangle(RecordModel):
    tagid = HWPTAG_SHAPE_COMPONENT_RECTANGLE

    def attributes():
        yield BYTE, 'round',
        yield Coord, 'p0'
        yield Coord, 'p1'
        yield Coord, 'p2'
        yield Coord, 'p3'
    attributes = staticmethod(attributes)


class ShapeEllipse(RecordModel):
    tagid = HWPTAG_SHAPE_COMPONENT_ELLIPSE
    Flags = Flags(UINT32)  # TODO

    def attributes(cls):
        yield cls.Flags, 'flags'
        yield Coord, 'center'
        yield Coord, 'axis1'
        yield Coord, 'axis2'
        yield Coord, 'start1'
        yield Coord, 'end1'
        yield Coord, 'start2'
        yield Coord, 'end2'
    attributes = classmethod(attributes)


class ShapeArc(RecordModel):
    tagid = HWPTAG_SHAPE_COMPONENT_ARC

    def attributes(cls):
        #yield ShapeEllipse.Flags, 'flags' # SPEC
        yield Coord, 'center'
        yield Coord, 'axis1'
        yield Coord, 'axis2'
    attributes = classmethod(attributes)


class ShapePolygon(RecordModel):
    tagid = HWPTAG_SHAPE_COMPONENT_POLYGON

    def attributes(cls):
        yield N_ARRAY(UINT16, Coord), 'points'
    attributes = classmethod(attributes)


class ShapeCurve(RecordModel):
    tagid = HWPTAG_SHAPE_COMPONENT_CURVE

    def attributes(cls):
        yield N_ARRAY(UINT16, Coord), 'points'
        # TODO: segment type
    attributes = classmethod(attributes)


class ShapeOLE(RecordModel):
    tagid = HWPTAG_SHAPE_COMPONENT_OLE
    # TODO


class PictureInfo(Struct):
    def attributes():
        yield INT8, 'brightness',
        yield INT8, 'contrast',
        yield BYTE, 'effect',
        yield UINT16, 'bindata_id',
    attributes = staticmethod(attributes)


# HWPML에서의 이름 사용
class ImageRect(Struct):
    ''' 이미지 좌표 정보 '''

    def attributes():
        yield Coord, 'p0'
        yield Coord, 'p1'
        yield Coord, 'p2'
        yield Coord, 'p3'
    attributes = staticmethod(attributes)


# HWPML에서의 이름 사용
class ImageClip(Struct):
    ''' 이미지 자르기 정보 '''

    def attributes():
        yield SHWPUNIT, 'left',
        yield SHWPUNIT, 'top',
        yield SHWPUNIT, 'right',
        yield SHWPUNIT, 'bottom',
    attributes = staticmethod(attributes)


class ShapePicture(RecordModel):
    ''' 4.2.9.4. 그림 개체 '''
    tagid = HWPTAG_SHAPE_COMPONENT_PICTURE

    def attributes():
        yield BorderLine, 'border'
        yield ImageRect, 'rect',
        yield ImageClip, 'clip',
        yield Margin, 'padding',
        yield PictureInfo, 'picture',
        # DIFFSPEC
            # BYTE, 'transparency',
            # UINT32, 'instanceId',
            # PictureEffect, 'effect',
    attributes = staticmethod(attributes)


class ShapeContainer(RecordModel):
    tagid = HWPTAG_SHAPE_COMPONENT_CONTAINER
    # TODO


class ShapeTextArt(RecordModel):
    tagid = HWPTAG_SHAPE_COMPONENT_TEXTART
    # TODO


control_data_models = dict()


class ControlDataType(RecordModelType):

    def __new__(mcs, name, bases, attrs):
        cls = RecordModelType.__new__(mcs, name, bases, attrs)
        if 'parent_model_type' in attrs:
            parent_model_type = attrs['parent_model_type']
            assert parent_model_type not in control_data_models
            control_data_models[parent_model_type] = cls
        return cls


class ControlData(RecordModel):
    __metaclass__ = ControlDataType
    tagid = HWPTAG_CTRL_DATA

    extension_types = control_data_models

    def get_extension_key(cls, context, model):
        ''' parent model type '''
        parent = context.get('parent')
        if parent:
            return parent[1]['type']
    get_extension_key = classmethod(get_extension_key)


class EqEdit(RecordModel):
    tagid = HWPTAG_CTRL_EQEDIT
    # TODO


class ForbiddenChar(RecordModel):
    tagid = HWPTAG_FORBIDDEN_CHAR
    # TODO


class SectionDef(Control):
    ''' 4.2.10.1. 구역 정의 '''
    chid = CHID.SECD

    Flags = Flags(UINT32,
                  0, 'hide_header',
                  1, 'hide_footer',
                  2, 'hide_page',
                  3, 'hide_border',
                  4, 'hide_background',
                  5, 'hide_pagenumber',
                  8, 'show_border_on_first_page_only',
                  9, 'show_background_on_first_page_only',
                  16, 18, 'text_direction',
                  19, 'hide_blank_line',
                  20, 21, 'pagenum_on_split_section',
                  22, 'squared_manuscript_paper')

    def attributes(cls):
        yield cls.Flags, 'flags',
        yield HWPUNIT16, 'columnspacing',
        yield HWPUNIT16, 'grid_vertical',
        yield HWPUNIT16, 'grid_horizontal',
        yield HWPUNIT, 'defaultTabStops',
        yield UINT16, 'numbering_shape_id',
        yield UINT16, 'starting_pagenum',
        yield UINT16, 'starting_picturenum',
        yield UINT16, 'starting_tablenum',
        yield UINT16, 'starting_equationnum',
        yield dict(type=UINT32, name='unknown1', version=(5, 0, 1, 7))
        yield dict(type=UINT32, name='unknown2', version=(5, 0, 1, 7))
    attributes = classmethod(attributes)


class SectionDefData(ControlData):
    parent_model_type = SectionDef

    def attributes():
        yield HexBytes(280), 'unknown'
    attributes = staticmethod(attributes)


class ColumnsDef(Control):
    ''' 4.2.10.2. 단 정의 '''
    chid = CHID.COLD

    Kind = Enum('normal', 'distribute', 'parallel')
    Direction = Enum('l2r', 'r2l', 'both')
    Flags = Flags(UINT16,
                  0, 1, Kind, 'kind',
                  2, 9, 'count',
                  10, 11, Direction, 'direction',
                  12, 'same_widths')

    def attributes(cls):
        from hwp5.dataio import X_ARRAY
        from hwp5.dataio import ref_member_flag
        yield cls.Flags, 'flags'
        yield HWPUNIT16, 'spacing'

        def not_same_widths(context, values):
            ''' flags.same_widths == 0 '''
            return not values['flags'].same_widths

        yield dict(name='widths',
                   type=X_ARRAY(WORD, ref_member_flag('flags', 'count')),
                   condition=not_same_widths)
        yield UINT16, 'attr2'
        yield Border, 'splitter'
    attributes = classmethod(attributes)


class HeaderFooter(Control):
    ''' 4.2.10.3. 머리말/꼬리말 '''
    Places = Enum(BOTH_PAGES=0, EVEN_PAGE=1, ODD_PAGE=2)
    Flags = Flags(UINT32,
                  0, 1, Places, 'places')

    def attributes(cls):
        yield cls.Flags, 'flags'
    attributes = classmethod(attributes)

    class ParagraphList(ListHeader):
        def attributes():
            yield HWPUNIT, 'width'
            yield HWPUNIT, 'height'
            yield BYTE, 'textrefsbitmap'
            yield BYTE, 'numberrefsbitmap'
        attributes = staticmethod(attributes)


class Header(HeaderFooter):
    ''' 머리말 '''
    chid = CHID.HEADER


class HeaderParagraphList(HeaderFooter.ParagraphList):
    parent_model_type = Header


class Footer(HeaderFooter):
    ''' 꼬리말 '''
    chid = CHID.FOOTER


class FooterParagraphList(HeaderFooter.ParagraphList):
    parent_model_type = Footer


class Note(Control):
    ''' 4.2.10.4 미주/각주 '''
    def attributes():
        yield dict(type=UINT32, name='number', version=(5, 0, 0, 6))  # SPEC
    attributes = staticmethod(attributes)


class FootNote(Note):
    ''' 각주 '''
    chid = CHID.FN


class EndNote(Note):
    ''' 미주 '''
    chid = CHID.EN


class NumberingControl(Control):
    Kind = Enum(PAGE=0, FOOTNOTE=1, ENDNOTE=2, PICTURE=3, TABLE=4, EQUATION=5)
    Flags = Flags(UINT32,
                  0, 3, Kind, 'kind',
                  4, 11, 'footnoteshape',
                  12, 'superscript')

    def attributes(cls):
        yield cls.Flags, 'flags',
        yield UINT16, 'number',
    attributes = classmethod(attributes)


class AutoNumbering(NumberingControl):
    ''' 4.2.10.5. 자동 번호 '''
    chid = CHID.ATNO

    def attributes(cls):
        yield WCHAR, 'usersymbol',
        yield WCHAR, 'prefix',
        yield WCHAR, 'suffix',
    attributes = classmethod(attributes)

    def __unicode__(self):
        prefix = u''
        suffix = u''
        if self.flags.kind == self.Kind.FOOTNOTE:
            if self.suffix != u'\x00':
                suffix = self.suffix
        return prefix + unicode(self.number) + suffix


class NewNumbering(NumberingControl):
    ''' 4.2.10.6. 새 번호 지정 '''
    chid = CHID.NWNO


class PageHide(Control):
    ''' 4.2.10.7 감추기 '''
    chid = CHID.PGHD
    Flags = Flags(UINT32,
                  0, 'header',
                  1, 'footer',
                  2, 'basepage',
                  3, 'pageborder',
                  4, 'pagefill',
                  5, 'pagenumber')

    def attributes(cls):
        yield cls.Flags, 'flags'
    attributes = classmethod(attributes)


class PageOddEven(Control):
    ''' 4.2.10.8 홀/짝수 조정 '''
    chid = CHID.PGCT
    OddEven = Enum(BOTH_PAGES=0, EVEN_PAGE=1, ODD_PAGE=2)
    Flags = Flags(UINT32,
                  0, 1, OddEven, 'pages')

    def attributes(cls):
        yield cls.Flags, 'flags'
    attributes = classmethod(attributes)


class PageNumberPosition(Control):
    ''' 4.2.10.9. 쪽 번호 위치 '''
    chid = CHID.PGNP
    Position = Enum(NONE=0,
                    TOP_LEFT=1, TOP_CENTER=2, TOP_RIGHT=3,
                    BOTTOM_LEFT=4, BOTTOM_CENTER=5, BOTTOM_RIGHT=6,
                    OUTSIDE_TOP=7, OUTSIDE_BOTTOM=8,
                    INSIDE_TOP=9, INSIDE_BOTTOM=10)
    Flags = Flags(UINT32,
                  0, 7, 'shape',
                  8, 11, Position, 'position')

    def attributes(cls):
        yield cls.Flags, 'flags'
        yield WCHAR, 'usersymbol'
        yield WCHAR, 'prefix'
        yield WCHAR, 'suffix'
        yield WCHAR, 'dash'
    attributes = classmethod(attributes)


class IndexMarker(Control):
    ''' 4.2.10.10. 찾아보기 표식 '''
    chid = CHID.IDXM

    def attributes():
        yield BSTR, 'keyword1'
        yield BSTR, 'keyword2'
        yield UINT16, 'dummy'
    attributes = staticmethod(attributes)


class BookmarkControl(Control):
    ''' 4.2.10.11. 책갈피 '''
    chid = CHID.BOKM

    def attributes():
        if False:
            yield
    attributes = staticmethod(attributes)


class BookmarkControlData(ControlData):

    parent_model_type = BookmarkControl

    def attributes():
        yield UINT32, 'unknown1'
        yield UINT32, 'unknown2'
        yield UINT16, 'unknown3'
        yield BSTR, 'name'
    attributes = staticmethod(attributes)


class TCPSControl(Control):
    ''' 4.2.10.12. 글자 겹침 '''
    chid = CHID.TCPS

    def attributes():
        yield BSTR, 'textlength'
        #yield UINT8, 'frameType'
        #yield INT8, 'internalCharacterSize'
        #yield UINT8, 'internalCharacterFold'
        #yield N_ARRAY(UINT8, UINT32), 'characterShapeIds'
    attributes = staticmethod(attributes)


class Dutmal(Control):
    ''' 4.2.10.13. 덧말 '''
    chid = CHID.TDUT
    Position = Enum(ABOVE=0, BELOW=1, CENTER=2)
    Align = Enum(BOTH=0, LEFT=1, RIGHT=2, CENTER=3, DISTRIBUTE=4,
                 DISTRIBUTE_SPACE=5)

    def attributes(cls):
        yield BSTR, 'maintext'
        yield BSTR, 'subtext'
        yield Flags(UINT32,
                    0, 31, cls.Position, 'position'), 'position'
        yield UINT32, 'fsizeratio'
        yield UINT32, 'option'
        yield UINT32, 'stylenumber'
        yield Flags(UINT32,
                    0, 31, cls.Align, 'align'), 'align'
    attributes = classmethod(attributes)


class HiddenComment(Control):
    ''' 4.2.10.14 숨은 설명 '''
    chid = CHID.TCMT

    def attributes():
        if False:
            yield
    attributes = staticmethod(attributes)


class Field(Control):
    ''' 4.2.10.15 필드 시작 '''

    Flags = Flags(UINT32,
                  0, 'editableInReadOnly',
                  11, 14, 'visitedType',
                  15, 'modified')

    def attributes(cls):
        yield cls.Flags, 'flags',
        yield BYTE, 'extra_attr',
        yield BSTR, 'command',
        yield UINT32, 'id',
    attributes = classmethod(attributes)


class FieldUnknown(Field):
    chid = '%unk'


class FieldDate(Field):
    chid = CHID.DTE


class FieldDocDate(Field):
    chid = '%ddt'


class FieldPath(Field):
    chid = '%pat'


class FieldBookmark(Field):
    chid = '%bmk'


class FieldMailMerge(Field):
    chid = '%mmg'


class FieldCrossRef(Field):
    chid = '%xrf'


class FieldFormula(Field):
    chid = '%fmu'


class FieldClickHere(Field):
    chid = '%clk'


class FieldClickHereData(ControlData):
    parent_model_type = FieldClickHere


class FieldSummary(Field):
    chid = '%smr'


class FieldUserInfo(Field):
    chid = '%usr'


class FieldHyperLink(Field):
    chid = CHID.HLK

    def geturl(self):
        s = self.command.split(';')
        return s[0].replace('\\:', ':')

# TODO: FieldRevisionXXX


class FieldMemo(Field):
    chid = '%%me'


class FieldPrivateInfoSecurity(Field):
    chid = '%cpr'


def _check_tag_models():
    for tagid, name in tagnames.iteritems():
        assert tagid in tag_models, 'RecordModel for %s is missing!' % name
_check_tag_models()


def init_record_parsing_context(base, record):
    ''' Initialize a context to parse the given record

        the initializations includes followings:
        - context = dict(base)
        - context['record'] = record
        - context['stream'] = record payload stream

        :param base: the base context to be shallow-copied into the new one
        :param record: to be parsed
        :returns: new context
    '''

    return dict(base, record=record, stream=StringIO(record['payload']))


from hwp5.bintype import parse_model


def parse_models_with_parent(context_models):
    from .treeop import prefix_ancestors_from_level
    level_prefixed = ((model['level'], (context, model))
                      for context, model in context_models)
    root_item = (dict(), dict())
    ancestors_prefixed = prefix_ancestors_from_level(level_prefixed, root_item)
    for ancestors, (context, model) in ancestors_prefixed:
        context['parent'] = ancestors[-1]
        parse_model(context, model)
        yield context, model


def parse_models(context, records):
    for context, model in parse_models_intern(context, records):
        yield model


def parse_models_intern(context, records):
    context_models = ((init_record_parsing_context(context, record), record)
                      for record in records)
    context_models = parse_models_with_parent(context_models)
    for context, model in context_models:
        stream = context['stream']
        unparsed = stream.read()
        if unparsed:
            model['unparsed'] = unparsed
        yield context, model


def model_to_json(model, *args, **kwargs):
    ''' convert a model to json '''
    from .dataio import dumpbytes
    from hwp5.importhelper import importjson
    json = importjson()
    model = dict(model)
    model['type'] = model['type'].__name__
    record = model
    record['payload'] = list(dumpbytes(record['payload']))
    if 'unparsed' in model:
        model['unparsed'] = list(dumpbytes(model['unparsed']))
    if 'binevents' in model:
        del model['binevents']
    return json.dumps(model, *args, **kwargs)


def chain_iterables(iterables):
    for iterable in iterables:
        for item in iterable:
            yield item


from . import recordstream


class ModelStream(recordstream.RecordStream):

    def models(self, **kwargs):
        # prepare binmodel parsing context
        kwargs.setdefault('version', self.version)
        try:
            kwargs.setdefault('path', self.path)
        except AttributeError:
            pass
        treegroup = kwargs.get('treegroup', None)
        if treegroup is not None:
            records = self.records_treegroup(treegroup)  # TODO: kwargs
            models = parse_models(kwargs, records)
        else:
            groups = self.models_treegrouped(**kwargs)
            models = chain_iterables(groups)
        return models

    def models_treegrouped(self, **kwargs):
        ''' iterable of iterable of the models, grouped by the top-level tree
        '''
        kwargs.setdefault('version', self.version)
        for group_idx, records in enumerate(self.records_treegrouped()):
            kwargs['treegroup'] = group_idx
            yield parse_models(kwargs, records)

    def model(self, idx):
        return nth(self.models(), idx)

    def models_json(self, **kwargs):
        from .utils import JsonObjects
        models = self.models(**kwargs)
        return JsonObjects(models, model_to_json)

    def other_formats(self):
        d = super(ModelStream, self).other_formats()
        d['.models'] = self.models_json().open
        return d


class DocInfo(ModelStream):

    @property
    def idmappings(self):
        for model in self.models():
            if model['type'] is IdMappings:
                return model

    @property
    def facenames_by_lang(self):
        facenames = list(m for m in self.models()
                         if m['type'] is FaceName)
        languages = 'ko', 'en', 'cn', 'jp', 'other', 'symbol', 'user'
        facenames_by_lang = dict()
        offset = 0
        for lang in languages:
            n_fonts = self.idmappings['content'][lang + '_fonts']
            facenames_by_lang[lang] = facenames[offset:offset + n_fonts]
            offset += n_fonts
        return facenames_by_lang

    @property
    def charshapes(self):
        return (m for m in self.models()
                if m['type'] is CharShape)

    def get_charshape(self, charshape_id):
        return nth(self.charshapes, charshape_id)

    def charshape_lang_facename(self, charshape_id, lang):
        charshape = self.get_charshape(charshape_id)
        lang_facename_offset = charshape['content']['font_face'][lang]
        return self.facenames_by_lang[lang][lang_facename_offset]


class Sections(recordstream.Sections):

    section_class = ModelStream


class Hwp5File(recordstream.Hwp5File):

    docinfo_class = DocInfo
    bodytext_class = Sections


def create_context(file=None, **context):
    if file is not None:
        context['version'] = file.fileheader.version
    assert 'version' in context
    return context

########NEW FILE########
__FILENAME__ = binspec
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''Generate HWPv5 Binary Spec Document

Usage::

    hwp5spec xml [--loglevel=<loglevel>]
    hwp5spec -h | --help
    hwp5spec --version

Options::

    -h --help       Show this screen
    --version       Show version
    --loglevel=<loglevel>   Set log level [default: warning]
'''

import logging
from .importhelper import importStringIO
StringIO = importStringIO()
import xml.etree.ElementTree as ET


logger = logging.getLogger(__name__)


def define_enum_type(enum_type):
    attrs = dict(name=enum_type.__name__)
    if enum_type.scoping_struct:
        attrs['scope'] = enum_type.scoping_struct.__name__
    elem = ET.Element('EnumType', attrs)
    value_names = list((e, e.name) for e in enum_type.instances)
    value_names.sort()
    for value, name in value_names:
        item = ET.Element('item', dict(name=name, value=str(value)))
        elem.append(item)
    return elem


def define_bitfield(bitgroup_name, bitgroup_desc):
    attrs = dict(name=bitgroup_name,
                 lsb=str(bitgroup_desc.lsb),
                 msb=str(bitgroup_desc.msb))
    elem = ET.Element('BitField', attrs)
    elem.append(reference_type(bitgroup_desc.valuetype))
    return elem


def define_flags_type(flags_type):
    elem = ET.Element('FlagsType')
    from hwp5.dataio import BitGroupDescriptor
    base = ET.SubElement(elem, 'base')
    base.append(reference_type(flags_type.basetype))
    bitgroups = flags_type.__dict__.items()
    bitgroups = ((v.lsb, (k, v)) for k, v in bitgroups
                 if isinstance(v, BitGroupDescriptor))
    bitgroups = list(bitgroups)
    bitgroups.sort()
    bitgroups = reversed(bitgroups)
    bitgroups = ((k, v) for lsb, (k, v) in bitgroups)
    bitgroups = (define_bitfield(k, v) for k, v in bitgroups)
    for bitgroup in bitgroups:
        elem.append(bitgroup)
    return elem


def define_fixed_array_type(array_type):
    attrs = dict()
    attrs['size'] = str(array_type.size)
    elem = ET.Element('FixedArrayType', attrs)
    item_type_elem = ET.SubElement(elem, 'item-type')
    item_type_elem.append(reference_type(array_type.itemtype))
    return elem


def define_variable_length_array_type(array_type):
    elem = ET.Element('VariableLengthArrayType')
    count_type_elem = ET.SubElement(elem, 'count-type')
    count_type_elem.append(reference_type(array_type.counttype))
    item_type_elem = ET.SubElement(elem, 'item-type')
    item_type_elem.append(reference_type(array_type.itemtype))
    return elem


def define_x_array_type(t):
    elem = ET.Element('XArrayType', dict(size=t.count_reference.__doc__))
    item_type_elem = ET.SubElement(elem, 'item-type')
    item_type_elem.append(reference_type(t.itemtype))
    return elem


def define_selective_type(t):
    elem = ET.Element('SelectiveType',
                      dict(selector=t.selector_reference.__doc__))
    for k, v in t.selections.items():
        sel = ET.SubElement(elem, 'selection',
                            dict(when=make_condition_value(k)))
        sel.append(reference_type(v))
    return elem


def reference_type(t):
    attrs = dict()
    attrs['name'] = t.__name__
    attrs['meta'] = type(t).__name__
    elem = ET.Element('type-ref', attrs)

    from hwp5.dataio import EnumType
    from hwp5.dataio import FlagsType
    from hwp5.dataio import FixedArrayType
    from hwp5.dataio import X_ARRAY
    from hwp5.dataio import VariableLengthArrayType
    from hwp5.dataio import SelectiveType
    if isinstance(t, EnumType):
        if t.scoping_struct:
            elem.attrib['scope'] = t.scoping_struct.__name__
    elif isinstance(t, FlagsType):
        elem.append(define_flags_type(t))
    elif isinstance(t, FixedArrayType):
        elem.append(define_fixed_array_type(t))
    elif isinstance(t, X_ARRAY):
        elem.append(define_x_array_type(t))
    elif isinstance(t, VariableLengthArrayType):
        elem.append(define_variable_length_array_type(t))
    elif isinstance(t, SelectiveType):
        elem.append(define_selective_type(t))
    return elem


def referenced_types_by_member(member):
    t = member.get('type')
    if t:
        yield t
        for x in direct_referenced_types(t):
            yield x


def define_member(struct_type, member):
    attrs = dict(name=member['name'])

    version = member.get('version')
    if version:
        version = '.'.join(str(x) for x in version)
        attrs['version'] = version

    elem = ET.Element('member', attrs)

    t = member.get('type')
    if t:
        elem.append(reference_type(t))

    condition = member.get('condition')
    if condition:
        condition = condition.__doc__ or condition.__name__ or ''
        condition = condition.strip()
        condition_elem = ET.Element('condition')
        condition_elem.text = condition
        elem.append(condition_elem)

    return elem


def direct_referenced_types(t):
    from hwp5.dataio import FlagsType
    from hwp5.dataio import FixedArrayType
    from hwp5.dataio import X_ARRAY
    from hwp5.dataio import VariableLengthArrayType
    from hwp5.dataio import StructType
    from hwp5.dataio import SelectiveType
    if isinstance(t, FlagsType):
        for k, desc in t.bitfields.items():
            yield desc.valuetype
    elif isinstance(t, FixedArrayType):
        yield t.itemtype
    elif isinstance(t, X_ARRAY):
        yield t.itemtype
    elif isinstance(t, VariableLengthArrayType):
        yield t.counttype
        yield t.itemtype
    elif isinstance(t, StructType):
        if 'members' in t.__dict__:
            for member in t.members:
                for x in referenced_types_by_member(member):
                    yield x
    elif isinstance(t, SelectiveType):
        for selection in t.selections.values():
            yield selection


def referenced_types_by_struct_type(t):
    if 'members' in t.__dict__:
        for member in t.members:
            for x in referenced_types_by_member(member):
                yield x


def extension_sort_key(cls):
    import inspect
    key = inspect.getmro(cls)
    key = list(x.__name__ for x in key)
    key = tuple(reversed(key))
    return key


def sort_extensions(extension_types):
    extension_types = extension_types.items()
    extension_types = list((extension_sort_key(cls), (k, cls))
                           for k, cls in extension_types)
    extension_types.sort()
    extension_types = ((k, cls) for sort_key, (k, cls) in extension_types)
    return extension_types


def extensions_of_tag_model(tag_model):
    extension_types = getattr(tag_model, 'extension_types', None)
    if extension_types:
        extension_types = sort_extensions(extension_types)
        key_condition = getattr(tag_model, 'get_extension_key', None)
        key_condition = key_condition.__doc__.strip()
        for key, extension_type in extension_types:
            yield (key_condition, key), extension_type


def define_struct_type(t):
    elem = ET.Element('StructType',
                      dict(name=t.__name__))
    for extend in get_extends(t):
        elem.append(define_extends(extend))

    if 'members' in t.__dict__:
        for member in t.members:
            elem.append(define_member(t, member))
    return elem


def define_tag_model(tag_id):
    from hwp5.tagids import tagnames
    from hwp5.binmodel import tag_models
    tag_name = tagnames[tag_id]
    tag_model = tag_models[tag_id]
    elem = ET.Element('TagModel',
                      dict(tag_id=str(tag_id),
                           name=tag_name))
    elem.append(define_base_type(tag_model))
    for (name, value), extension_type in extensions_of_tag_model(tag_model):
        elem.append(define_extension(extension_type,
                                     tag_model,
                                     name,
                                     value))
    return elem


def define_base_type(t):
    elem = ET.Element('base', dict(name=t.__name__))
    return elem


def make_condition_value(value):
    from hwp5.dataio import EnumType
    if isinstance(value, tuple):
        value = tuple(make_condition_value(v) for v in value)
        return '('+', '.join(value)+')'
    elif isinstance(type(value), EnumType):
        return repr(value)
    elif isinstance(value, type):
        return value.__name__
    else:
        return str(value)


def define_extension(t, up_to_type, name, value):
    attrs = dict(name=t.__name__)
    elem = ET.Element('extension', attrs)
    condition = ET.Element('condition')
    condition.text = name + ' == ' + make_condition_value(value)
    elem.append(condition)

    for extend in get_extends(t, up_to_type):
        elem.append(define_extends(extend))

    if 'members' in t.__dict__:
        for member in t.members:
            elem.append(define_member(t, member))
    return elem


def get_extends(t, up_to_type=None):
    def take_up_to(up_to_type, mro):
        for t in mro:
            yield t
            if t is up_to_type:
                return
    from itertools import takewhile

    import inspect
    mro = inspect.getmro(t)
    mro = mro[1:]  # exclude self
    #mro = take_up_to(up_to_type, mro)
    mro = takewhile(lambda cls: cls is not up_to_type, mro)
    mro = (t for t in mro if 'members' in t.__dict__)
    mro = list(mro)
    mro = reversed(mro)
    return mro


def define_extends(t):
    attrs = dict(name=t.__name__)
    elem = ET.Element('extends', attrs)
    return elem


def define_primitive_type(t):
    attrs = dict(name=t.__name__)
    fixed_size = getattr(t, 'fixed_size', None)
    if fixed_size:
        attrs['size'] = str(fixed_size)

    elem = ET.Element('PrimitiveType', attrs)

    binfmt = getattr(t, 'binfmt', None)
    if binfmt:
        binfmt_elem = ET.Element('binfmt')
        binfmt_elem.text = binfmt
        elem.append(binfmt_elem)
    return elem


def main():
    from docopt import docopt
    from hwp5 import __version__
    from hwp5.proc import rest_to_docopt

    doc = rest_to_docopt(__doc__)
    args = docopt(doc, version=__version__)

    if '--loglevel' in args:
        loglevel = args['--loglevel'].lower()
        loglevel = dict(error=logging.ERROR,
                        warning=logging.WARNING,
                        info=logging.INFO,
                        debug=logging.DEBUG).get(loglevel, logging.WARNING)
        logger.setLevel(loglevel)
        logger.addHandler(logging.StreamHandler())

    from hwp5 import binmodel
    import sys

    enum_types = set()
    extensions = set()
    struct_types = set()
    primitive_types = set()

    root = ET.Element('binspec', dict(version=__version__))
    for tag_id, tag_model in binmodel.tag_models.items():
        logger.debug('TAG_MODEL: %s', tag_model.__name__)
        root.append(define_tag_model(tag_id))
        struct_types.add(tag_model)

        from hwp5.dataio import EnumType
        from hwp5.dataio import StructType
        from hwp5.dataio import PrimitiveType
        for t in referenced_types_by_struct_type(tag_model):
            if isinstance(t, EnumType):
                enum_types.add(t)
            if isinstance(t, StructType):
                struct_types.add(t)
            if isinstance(t, PrimitiveType):
                logger.debug('- PrimitiveType: %s', t.__name__)
                primitive_types.add(t)

        for _, t in extensions_of_tag_model(tag_model):
            extensions.add(t)

    for t in extensions:
        struct_types.add(t)
        for extends in get_extends(t):
            struct_types.add(extends)

    for struct_type in struct_types:
        for t in referenced_types_by_struct_type(struct_type):
            if isinstance(t, EnumType):
                enum_types.add(t)
            if isinstance(t, PrimitiveType):
                primitive_types.add(t)

    enum_types = list((t.__name__, t) for t in enum_types)
    enum_types.sort()
    enum_types = (t for name, t in enum_types)
    for t in enum_types:
        root.append(define_enum_type(t))

    struct_types = list((t.__name__, t) for t in struct_types)
    struct_types.sort()
    struct_types = (t for name, t in struct_types)
    for t in struct_types:
        root.append(define_struct_type(t))

    primitive_types = list((t.__name__, t) for t in primitive_types)
    primitive_types.sort()
    primitive_types = (t for name, t in primitive_types)
    for t in primitive_types:
        root.append(define_primitive_type(t))

    doc = ET.ElementTree(root)
    doc.write(sys.stdout, 'utf-8')

########NEW FILE########
__FILENAME__ = bintype
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import logging
logger = logging.getLogger(__name__)


def bintype_map_events(bin_item):
    from hwp5.treeop import STARTEVENT, ENDEVENT
    from hwp5.dataio import StructType
    from hwp5.dataio import FixedArrayType
    from hwp5.dataio import VariableLengthArrayType
    from hwp5.dataio import X_ARRAY
    from hwp5.dataio import SelectiveType
    from hwp5.dataio import FlagsType

    bin_type = bin_item['type']
    if isinstance(bin_type, StructType):
        yield STARTEVENT, bin_item
        if hasattr(bin_type, 'members'):
            for member in bin_type.members:
                for x in bintype_map_events(member):
                    yield x
        yield ENDEVENT, bin_item
    elif isinstance(bin_type, FixedArrayType):
        yield STARTEVENT, bin_item
        item = dict(type=bin_type.itemtype)
        for x in bintype_map_events(item):
            yield x
        yield ENDEVENT, bin_item
    elif isinstance(bin_type, VariableLengthArrayType):
        yield STARTEVENT, bin_item
        item = dict(type=bin_type.itemtype)
        for x in bintype_map_events(item):
            yield x
        yield ENDEVENT, bin_item
    elif isinstance(bin_type, X_ARRAY):
        yield STARTEVENT, bin_item
        item = dict(type=bin_type.itemtype)
        for x in bintype_map_events(item):
            yield x
        yield ENDEVENT, bin_item
    elif isinstance(bin_type, SelectiveType):
        yield STARTEVENT, bin_item
        for k, v in bin_type.selections.items():
            item = dict(bin_item, select_when=k, type=v)
            for x in bintype_map_events(item):
                yield x
        yield ENDEVENT, bin_item
    elif isinstance(bin_type, FlagsType):
        yield STARTEVENT, bin_item
        yield None, dict(type=bin_type.basetype)
        yield ENDEVENT, bin_item
    else:
        yield None, bin_item


def filter_with_version(events, version):
    from hwp5.treeop import STARTEVENT
    from hwp5.treeop import iter_subevents
    for ev, item in events:
        required_version = item.get('version')
        if required_version is not None and version < required_version:
            # just consume and skip this tree
            logger.debug('skip following: (required version: %s)',
                         required_version)
            logger.debug('  %s', (ev, item))
            if ev is STARTEVENT:
                for x in iter_subevents(events):
                    pass
            continue
        yield ev, item


def make_items_immutable(events):
    from hwp5.treeop import STARTEVENT, ENDEVENT
    stack = []
    for ev, item in events:
        if ev is None:
            item = tuple(sorted(item.items()))
        elif ev is STARTEVENT:
            item = tuple(sorted(item.items()))
            stack.append(item)
        elif ev is ENDEVENT:
            item = stack.pop()
        yield ev, item


def compile_type_definition(bin_item):
    events = bintype_map_events(bin_item)
    events = make_items_immutable(events)
    return tuple(events)


master_typedefs = dict()


def get_compiled_typedef(type):
    if type not in master_typedefs:
        logger.info('compile typedef of %s', type)
        typedef_events = compile_type_definition(dict(type=type))
        master_typedefs[type] = typedef_events
    return master_typedefs[type]


versioned_typedefs = dict()


def get_compiled_typedef_with_version(type, version):
    if version not in versioned_typedefs:
        versioned_typedefs[version] = typedefs = dict()
    typedefs = versioned_typedefs[version]

    if type not in typedefs:
        logger.info('filter compiled typedef of %s with version %s',
                    type, version)
        typedef_events = get_compiled_typedef(type)
        events = static_to_mutable(typedef_events)
        events = filter_with_version(events, version)
        events = make_items_immutable(events)
        events = tuple(events)
        typedefs[type] = events

    return typedefs[type]


class ERROREVENT(object):
    pass


def static_to_mutable(events):
    from hwp5.treeop import STARTEVENT, ENDEVENT
    stack = []
    for ev, item in events:
        if ev is None:
            item = dict(item)
        elif ev is STARTEVENT:
            item = dict(item)
            stack.append(item)
        elif ev is ENDEVENT:
            item = stack.pop()
        yield ev, item


def pop_subevents(events_deque):
    from hwp5.treeop import STARTEVENT, ENDEVENT
    level = 0
    while len(events_deque) > 0:
        event, item = events_deque.popleft()
        yield event, item
        if event is STARTEVENT:
            level += 1
        elif event is ENDEVENT:
            if level > 0:
                level -= 1
            else:
                return


def resolve_types(typedef_events, context):
    from hwp5.treeop import STARTEVENT, ENDEVENT
    from hwp5.dataio import X_ARRAY
    from hwp5.dataio import VariableLengthArrayType
    from hwp5.dataio import FixedArrayType
    from hwp5.dataio import SelectiveType
    from collections import deque

    array_types = (X_ARRAY, VariableLengthArrayType, FixedArrayType)

    stack = []
    selective_stack = []

    events = static_to_mutable(typedef_events)
    events = deque(events)
    while len(events) > 0:
        ev, item = events.popleft()
        if isinstance(item['type'], SelectiveType):
            if ev is STARTEVENT:
                parent_struct = stack[-1]
                struct_value = parent_struct['value']
                selector_reference = item['type'].selector_reference
                select_key = selector_reference(context, struct_value)
                logger.debug('select_key: %s', select_key)
                item['select_key'] = select_key
                selective_stack.append(item)
            elif ev is ENDEVENT:
                selective_stack.pop()
            else:
                assert False
        elif 'select_when' in item:
            assert ev in (None, STARTEVENT)
            select_key = selective_stack[-1]['select_key']
            select_when = item.pop('select_when')
            if select_when != select_key:
                # just consume and skip this tree
                logger.debug('skip following: (select key %r != %r)',
                             select_key, select_when)
                logger.debug('  %s', (ev, item))
                if ev is STARTEVENT:
                    for x in pop_subevents(events):
                        logger.debug('  %s', x)
                        pass
                continue
            logger.debug('selected for: %r', select_when)
            events.appendleft((ev, item))
        elif 'condition' in item:
            assert ev in (STARTEVENT, None)
            condition = item.pop('condition')
            parent_struct = stack[-1]
            if not condition(context, parent_struct['value']):
                # just consume and skip this tree
                logger.debug('skip following: (not matched condition: %s)',
                             condition)
                logger.debug('  %s', (ev, item))
                if ev is STARTEVENT:
                    for x in pop_subevents(events):
                        logger.debug('  %s', x)
                        pass
                continue
            events.appendleft((ev, item))
        elif isinstance(item['type'], array_types) and 'count' not in item:
            assert ev is STARTEVENT

            if isinstance(item['type'], X_ARRAY):
                parent_struct = stack[-1]
                struct_value = parent_struct['value']

                count_reference = item['type'].count_reference
                count = count_reference(context, struct_value)
            elif isinstance(item['type'], VariableLengthArrayType):
                count = dict(type=item['type'].counttype, dontcollect=True)
                yield None, count
                count = count['value']
            elif isinstance(item['type'], FixedArrayType):
                count = item['type'].size
            item['count'] = count

            subevents = list(pop_subevents(events))
            endevent = subevents[-1]
            subevents = subevents[:-1]

            def clone(events):
                stack = []
                for ev, item in events:
                    if ev in (STARTEVENT, None):
                        item = dict(item)
                        if ev is STARTEVENT:
                            stack.append(item)
                    else:
                        item = stack.pop()
                    yield ev, item

            events.appendleft(endevent)
            for _ in range(0, count):
                cloned = list(clone(subevents))
                events.extendleft(reversed(cloned))
            events.appendleft((ev, item))
        else:
            if ev is STARTEVENT:
                stack.append(item)
            elif ev is ENDEVENT:
                stack.pop()
            yield ev, item


def collect_values(events):
    from hwp5.treeop import STARTEVENT, ENDEVENT
    from hwp5.dataio import StructType
    from hwp5.dataio import X_ARRAY
    from hwp5.dataio import FixedArrayType
    from hwp5.dataio import VariableLengthArrayType
    from hwp5.dataio import FlagsType

    stack = []

    for ev, item in events:
        if ev is STARTEVENT:
            if isinstance(item['type'], StructType):
                item['value'] = dict()
            elif isinstance(item['type'], (X_ARRAY, VariableLengthArrayType,
                                           FixedArrayType)):
                item['value'] = list()
            elif isinstance(item['type'], FlagsType):
                pass
            else:
                assert False
            stack.append(item)
        elif ev in (None, ENDEVENT):
            if ev is ENDEVENT:
                item = stack.pop()
                if isinstance(item['type'], FixedArrayType):
                    item['value'] = tuple(item['value'])

            if len(stack) > 0:
                if not item.get('dontcollect', False):
                    if isinstance(stack[-1]['type'], StructType):
                        # reduce a struct member into struct value
                        stack[-1]['value'][item['name']] = item['value']
                    elif isinstance(stack[-1]['type'],
                                    (X_ARRAY,
                                     VariableLengthArrayType,
                                     FixedArrayType)):
                        stack[-1]['value'].append(item['value'])
                    elif isinstance(stack[-1]['type'], FlagsType):
                        stack[-1]['value'] = stack[-1]['type'](item['value'])
        yield ev, item


def log_events(events, log_fn):
    from hwp5.treeop import STARTEVENT, ENDEVENT
    for ev, item in events:
        if ev in (STARTEVENT, ENDEVENT):
            fmt = ['%s:']
            val = [ev.__name__]
        else:
            fmt = ['  %04x:']
            val = [item['bin_offset']]

        fmt.append('%s')
        val.append(item['type'].__name__)

        if 'name' in item:
            fmt.append('%r')
            val.append(item['name'])

        if 'value' in item and ev is None:
            fmt.append('%r')
            val.append(item['value'])

        if 'exception' in item:
            fmt.append('-- Exception: %r')
            val.append(item['exception'])

        log_fn(' '.join(fmt), *val)
        yield ev, item


def eval_typedef_events(typedef_events, context, resolve_values):
    events = static_to_mutable(typedef_events)
    events = resolve_types(events, context)
    events = resolve_values(events)
    events = collect_values(events)
    events = log_events(events, logger.debug)
    return events


def resolve_values_from_stream(stream):
    def resolve_values(events):
        for ev, item in events:
            if ev is None:
                item['bin_offset'] = stream.tell()
                try:
                    item['value'] = resolve_value_from_stream(item, stream)
                except Exception, e:
                    item['exception'] = e
                    ev = ERROREVENT
            yield ev, item
    return resolve_values


def resolve_value_from_stream(item, stream):
    import struct
    from hwp5.dataio import readn
    from hwp5.dataio import BSTR
    from hwp5.binmodel import ParaTextChunks
    from hwp5.binmodel import CHID
    item_type = item['type']
    if hasattr(item_type, 'binfmt'):
        binfmt = item_type.binfmt
        binsize = struct.calcsize(binfmt)
        bytes = readn(stream, binsize)
        unpacked = struct.unpack(binfmt, bytes)
        return unpacked[0]
    elif item_type is CHID:
        bytes = readn(stream, 4)
        return CHID.decode(bytes)
    elif item_type is BSTR:
        return BSTR.read(stream)
    elif item_type is ParaTextChunks:
        return ParaTextChunks.read(stream)
    elif hasattr(item_type, 'fixed_size'):
        bytes = readn(stream, item_type.fixed_size)
        if hasattr(item_type, 'decode'):
            return item_type.decode(bytes)
        return bytes
    else:
        assert hasattr(item_type, 'read')
        logger.warning('%s: item type relies on its read() to resolve a value',
                       item_type.__name__)
        return item_type.read(stream)


def read_type_events(type, context, stream):
    resolve_values = resolve_values_from_stream(stream)

    # get typedef events: if current version is specified in the context,
    # get version specific typedef
    if 'version' in context:
        version = context['version']
        events = get_compiled_typedef_with_version(type, version)
    else:
        events = get_compiled_typedef(type)

    # evaluate with context/stream
    events = eval_typedef_events(events, context, resolve_values)
    for ev, item in events:
        yield ev, item
        if ev is ERROREVENT:
            from hwp5.dataio import ParseError
            e = item['exception']
            msg = 'can\'t parse %s' % type
            pe = ParseError(msg)
            pe.cause = e
            pe.path = context.get('path')
            pe.treegroup = context.get('treegroup')
            pe.record = context.get('record')
            pe.offset = stream.tell()
            raise pe


def read_type_item(type, context, stream, binevents=None):
    from hwp5.dataio import ParseError
    if binevents is None:
        binevents = []
    try:
        binevents.extend(read_type_events(type, context, stream))
    except ParseError, e:
        e.binevents = binevents
        raise
    return binevents[-1][1]


def read_type(type, context, stream, binevents=None):
    item = read_type_item(type, context, stream, binevents)
    return item['value']


def parse_model(context, model):
    ''' HWPTAG로 모델 결정 후 기본 파싱 '''

    from hwp5.binmodel import tag_models
    from hwp5.binmodel import RecordModel

    stream = context['stream']

    # HWPTAG로 모델 결정
    model['type'] = tag_models.get(model['tagid'], RecordModel)
    model['binevents'] = model_events = list()

    # 1차 파싱
    model['content'] = read_type(model['type'], context, stream, model_events)

    # 키 속성으로 모델 타입 변경 (예: Control.chid에 따라 TableControl 등으로)
    extension_types = getattr(model['type'], 'extension_types', None)
    if extension_types:
        key = model['type'].get_extension_key(context, model)
        extension = extension_types.get(key)
        if extension is not None:
            # 예: Control -> TableControl로 바뀌는 경우,
            # Control의 member들은 이미 읽은 상태이고
            # CommonControl, TableControl에서 각각 정의한
            # 멤버들을 읽어들여야 함
            for cls in get_extension_mro(extension, model['type']):
                content = read_type(cls, context, stream, model_events)
                model['content'].update(content)
            model['type'] = extension

    if 'parent' in context:
        parent = context['parent']
        parent_context, parent_model = parent
        parent_type = parent_model.get('type')
        parent_content = parent_model.get('content')

        on_child = getattr(parent_type, 'on_child', None)
        if on_child:
            on_child(parent_content, parent_context, (context, model))

    logger.debug('model: %s', model['type'].__name__)
    logger.debug('%s', model['content'])


def get_extension_mro(cls, up_to_cls=None):
    import inspect
    from itertools import takewhile
    mro = inspect.getmro(cls)
    mro = takewhile(lambda cls: cls is not up_to_cls, mro)
    mro = list(cls for cls in mro if 'attributes' in cls.__dict__)
    mro = reversed(mro)
    return mro


def dump_events(events):
    def prefix_level(event_prefixed_items):
        from hwp5.treeop import STARTEVENT, ENDEVENT
        level = 0
        for ev, item in event_prefixed_items:
            if ev is STARTEVENT:
                yield level, item
                level += 1
            elif ev is ENDEVENT:
                level -= 1
            else:
                yield level, item

    def item_to_dict(events):
        for ev, item in events:
            yield ev, dict(item)

    def type_to_string(events):
        for ev, item in events:
            item['type'] = item['type'].__name__
            yield ev, item

    def condition_to_string(events):
        for ev, item in events:
            if 'condition' in item:
                item['condition'] = item['condition'].__name__
            yield ev, item

    events = item_to_dict(events)
    events = type_to_string(events)
    events = condition_to_string(events)
    for level, item in prefix_level(events):
        if level > 0:
            if level > 1:
                print '  ' * (level - 2) + ' ',
            print '-',
        print item


def main():
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    import hwp5.binmodel
    import sys
    name = sys.argv[1]
    type = getattr(hwp5.binmodel, name)
    from pprint import pprint
    typedef_events = compile_type_definition(dict(type=type))
    pprint(typedef_events)

    context = {}

    def resolve_values(events):
        from hwp5.dataio import FlagsType
        for ev, item in events:
            if ev is None:
                print
                for k, v in sorted(item.items()):
                    print '-', k, ':', v
                print '>>',
                value = raw_input()
                value = eval(value)
                if isinstance(item['type'], FlagsType):
                    value = item['type'](value)
                item['value'] = value
            yield ev, item
    events = eval_typedef_events(typedef_events, context, resolve_values)
    for ev, item in events:
        print ev, item

########NEW FILE########
__FILENAME__ = dataio
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import sys
import struct
import logging
from .importhelper import importStringIO
StringIO = importStringIO()


logger = logging.getLogger(__name__)


class Eof(Exception):
    def __init__(self, *args):
        self.args = args


class OutOfData(Exception):
    pass


def readn(f, size):
    data = f.read(size)
    datasize = len(data)
    if datasize == 0:
        try:
            pos = f.tell()
        except IOError:
            pos = '<UNKNOWN>'
        raise Eof(pos)
    return data


class PrimitiveType(type):
    def __new__(mcs, name, bases, attrs):
        basetype = bases[0]
        attrs['basetype'] = basetype
        attrs.setdefault('__slots__', [])

        never_instantiate = attrs.pop('never_instantiate', True)
        if never_instantiate and '__new__' not in attrs:
            def __new__(cls, *args, **kwargs):
                return basetype.__new__(basetype, *args, **kwargs)
            attrs['__new__'] = __new__

        if 'binfmt' in attrs:
            binfmt = attrs['binfmt']
            fixed_size = struct.calcsize(binfmt)

            if 'fixed_size' in attrs:
                assert fixed_size == attrs['fixed_size']
            else:
                attrs['fixed_size'] = fixed_size

            if 'decode' not in attrs:
                def decode(cls, s):
                    return struct.unpack(binfmt, s)[0]
                attrs['decode'] = classmethod(decode)

        if 'fixed_size' in attrs and 'read' not in attrs:
            fixed_size = attrs['fixed_size']

            def read(cls, f):
                s = readn(f, fixed_size)
                decode = getattr(cls, 'decode', None)
                if decode:
                    return decode(s)
                return s
            attrs['read'] = classmethod(read)

        return type.__new__(mcs, name, bases, attrs)


def Primitive(name, basetype, binfmt, **attrs):
    attrs['binfmt'] = binfmt
    return PrimitiveType(name, (basetype,), attrs)


UINT32 = Primitive('UINT32', long, '<I')
INT32 = Primitive('INT32', int, '<i')
UINT16 = Primitive('UINT16', int, '<H')
INT16 = Primitive('INT16', int, '<h')
UINT8 = Primitive('UINT8', int, '<B')
INT8 = Primitive('INT8', int, '<b')
WORD = Primitive('WORD', int, '<H')
BYTE = Primitive('BYTE', int, '<B')
DOUBLE = Primitive('DOUBLE', float, '<d')
WCHAR = Primitive('WCHAR', int, '<H')
HWPUNIT = Primitive('HWPUNIT', long, '<I')
SHWPUNIT = Primitive('SHWPUNIT', int, '<i')
HWPUNIT16 = Primitive('HWPUNIT16', int, '<h')

inch2mm = lambda x: float(int(x * 25.4 * 100 + 0.5)) / 100
hwp2inch = lambda x: x / 7200.0
hwp2mm = lambda x: inch2mm(hwp2inch(x))
hwp2pt = lambda x: int((x / 100.0) * 10 + 0.5) / 10.0


class HexBytes(type):
    def __new__(mcs, size):
        from binascii import b2a_hex
        decode = staticmethod(b2a_hex)
        return type.__new__(mcs, 'HexBytes(%d)' % size, (str,),
                            dict(fixed_size=size, decode=decode))


def decode_uint16le_array_default(bytes):
    from array import array
    codes = array('H', bytes)
    if sys.byteorder == 'big':
        codes.byteswap()
    return codes


def decode_uint16le_array_in_jython(bytes):
    from array import array
    codes = array('h', bytes)
    assert codes.itemsize == 2
    assert sys.byteorder == 'big'
    codes.byteswap()
    codes = array('H', codes.tostring())
    assert codes.itemsize == 4
    return codes


in_jython = sys.platform.startswith('java')
if in_jython:
    decode_uint16le_array = decode_uint16le_array_in_jython
else:
    decode_uint16le_array = decode_uint16le_array_default


class BSTR(unicode):
    __metaclass__ = PrimitiveType

    def read(f):
        size = UINT16.read(f)
        if size == 0:
            return u''
        data = readn(f, 2 * size)
        return decode_utf16le_with_hypua(data)
    read = staticmethod(read)


def decode_utf16le_with_hypua(bytes):
    ''' decode utf-16le encoded bytes with Hanyang-PUA codes into a unicode
    string with Hangul Jamo codes

    :param bytes: utf-16le encoded bytes with Hanyang-PUA codes
    :returns: a unicode string with Hangul Jamo codes
    '''
    from hypua2jamo import codes2unicode
    codes = decode_uint16le_array(bytes)
    return codes2unicode(codes.tolist())


class BitGroupDescriptor(object):
    def __init__(self, bitgroup):
        valuetype = int
        if isinstance(bitgroup, tuple):
            if len(bitgroup) > 2:
                lsb, msb, valuetype = bitgroup
            else:
                lsb, msb = bitgroup
        else:
            lsb = msb = bitgroup
        self.lsb = lsb
        self.msb = msb
        self.valuetype = valuetype

    def __get__(self, instance, owner):
        valuetype = self.valuetype
        lsb = self.lsb
        msb = self.msb
        return valuetype(int(instance >> lsb) &
                         int((2 ** (msb + 1 - lsb)) - 1))


class FlagsType(type):
    def __new__(mcs, name, bases, attrs):
        basetype = attrs.pop('basetype')
        bases = (basetype.basetype,)

        bitgroups = dict((k, BitGroupDescriptor(v))
                         for k, v in attrs.iteritems())

        attrs = dict(bitgroups)
        attrs['__name__'] = name
        attrs['__slots__'] = ()

        attrs['basetype'] = basetype
        attrs['bitfields'] = bitgroups

        def dictvalue(self):
            return dict((name, getattr(self, name))
                        for name in bitgroups.keys())
        attrs['dictvalue'] = dictvalue

        return type.__new__(mcs, name, bases, attrs)


def _lex_flags_args(args):
    for idx, arg in enumerate(args):
        while True:
            pushback = (yield idx, arg)
            if pushback is arg:
                yield
                continue
            break


def _parse_flags_args(args):
    args = _lex_flags_args(args)
    try:
        idx = -1
        while True:
            # lsb
            try:
                idx, lsb = args.next()
            except StopIteration:
                break
            assert isinstance(lsb, int), ('#%d arg is expected to be'
                                          'a int: %s' % (idx, repr(lsb)))

            # msb (default: lsb)
            idx, x = args.next()
            if isinstance(x, int):
                msb = x
            elif isinstance(x, (type, basestring)):
                args.send(x)  # pushback
                msb = lsb
            else:
                assert False, '#%d arg is unexpected type: %s' % (idx, repr(x))

            # type (default: int)
            idx, x = args.next()
            assert not isinstance(x, int), ('#%d args is expected to be a type'
                                            'or name: %s' % (idx, repr(x)))
            if isinstance(x, type):
                t = x
            elif isinstance(x, basestring):
                args.send(x)  # pushback
                t = int
            else:
                assert False, '#%d arg is unexpected type: %s' % (idx, repr(x))

            # name
            idx, name = args.next()
            assert isinstance(name, basestring), ('#%d args is expected to be '
                                                  'a name: %s' % (idx,
                                                                  repr(name)))

            yield name, (lsb, msb, t)

    except StopIteration:
        assert False, '#%d arg is expected' % (idx + 1)


def Flags(basetype, *args):
    attrs = dict(_parse_flags_args(args))
    attrs['basetype'] = basetype
    return FlagsType('Flags', (), attrs)


enum_type_instances = set()


class EnumType(type):
    def __new__(mcs, enum_type_name, bases, attrs):
        items = attrs.pop('items')
        moreitems = attrs.pop('moreitems')

        populate_state = [1]

        names_by_instance = dict()
        instances_by_name = dict()
        instances_by_value = dict()

        def __new__(cls, value, name=None):
            if isinstance(value, cls):
                return value

            if name is None:
                if value in instances_by_value:
                    return instances_by_value[value]
                else:
                    logger.warning('undefined %s value: %s',
                                   cls.__name__, value)
                    logger.warning('defined name/values: %s',
                                   str(instances_by_name))
                    return int.__new__(cls, value)

            if len(populate_state) == 0:
                raise TypeError()

            assert name not in instances_by_name

            if value in instances_by_value:
                self = instances_by_value[value]
            else:
                # define new instance of this enum
                self = int.__new__(cls, value)
                instances_by_value[value] = self
                names_by_instance[self] = name

            instances_by_name[name] = self
            return self
        attrs['__new__'] = __new__
        attrs['__slots__'] = []
        attrs['scoping_struct'] = None

        class NameDescriptor(object):
            def __get__(self, instance, owner):
                if instance is None:
                    return owner.__name__
                return names_by_instance.get(instance)

        attrs['name'] = NameDescriptor()

        def __repr__(self):
            enum_name = type(self).__name__
            item_name = self.name
            if item_name is not None:
                return enum_name + '.' + item_name
            else:
                return '%s(%d)' % (enum_name, self)
        attrs['__repr__'] = __repr__

        cls = type.__new__(mcs, enum_type_name, bases, attrs)

        for v, k in enumerate(items):
            setattr(cls, k, cls(v, k))
        for k, v in moreitems.iteritems():
            setattr(cls, k, cls(v, k))

        cls.names = set(instances_by_name.keys())
        cls.instances = set(names_by_instance.keys())

        # no more population
        populate_state.pop()

        enum_type_instances.add(cls)
        return cls

    def __init__(cls, *args, **kwargs):
        pass


def Enum(*items, **moreitems):
    attrs = dict(items=items, moreitems=moreitems)
    return EnumType('Enum', (int,), attrs)


class CompoundType(type):
    pass


class ArrayType(CompoundType):
    def __init__(self, *args, **kwargs):
        pass


class FixedArrayType(ArrayType):

    classes = dict()

    def __new__(mcs, itemtype, size):
        key = itemtype, size

        cls = mcs.classes.get(key)
        if cls is not None:
            return cls

        attrs = dict(itemtype=itemtype, size=size)
        name = 'ARRAY(%s,%s)' % (itemtype.__name__, size)
        cls = ArrayType.__new__(mcs, name, (tuple,), attrs)
        mcs.classes[key] = cls
        return cls


ARRAY = FixedArrayType


class VariableLengthArrayType(ArrayType):

    classes = dict()

    def __new__(mcs, counttype, itemtype):
        key = counttype, itemtype

        cls = mcs.classes.get(key)
        if cls is not None:
            return cls

        attrs = dict(itemtype=itemtype, counttype=counttype)
        name = 'N_ARRAY(%s,%s)' % (counttype.__name__, itemtype.__name__)
        cls = ArrayType.__new__(mcs, name, (list,), attrs)
        mcs.classes[key] = cls
        return cls


N_ARRAY = VariableLengthArrayType


def ref_member(member_name):
    f = lambda context, values: values[member_name]
    f.__doc__ = member_name
    return f


def ref_member_flag(member_name, bitfield_name):
    f = lambda context, values: getattr(values[member_name], bitfield_name)
    f.__doc__ = '%s.%s' % (member_name, bitfield_name)
    return f


class X_ARRAY(object):

    def __init__(self, itemtype, count_reference):
        name = 'ARRAY(%s, \'%s\')' % (itemtype.__name__,
                                      count_reference.__doc__)
        self.__doc__ = self.__name__ = name
        self.itemtype = itemtype
        self.count_reference = count_reference

    def __call__(self, context, values):
        count = self.count_reference(context, values)
        return ARRAY(self.itemtype, count)


class SelectiveType(object):

    def __init__(self, selector_reference, selections):
        self.__name__ = 'SelectiveType'
        self.selections = selections
        self.selector_reference = selector_reference

    def __call__(self, context, values):
        selector = self.selector_reference(context, values)
        return self.selections.get(selector, Struct)  # default: empty struct


class ParseError(Exception):

    treegroup = None

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        self.cause = None
        self.path = None
        self.record = None
        self.binevents = None
        self.parse_stack_traces = []

    def print_to_logger(self, logger):
        e = self
        logger.error('ParseError: %s', e)
        logger.error('Caused by: %s', repr(e.cause))
        logger.error('Path: %s', e.path)
        if e.treegroup is not None:
            logger.error('Treegroup: %s', e.treegroup)
        if e.record:
            logger.error('Record: %s', e.record['seqno'])
            logger.error('Record Payload:')
            for line in dumpbytes(e.record['payload'], True):
                logger.error('  %s', line)
        logger.error('Problem Offset: at %d (=0x%x)', e.offset, e.offset)
        if self.binevents:
            logger.error('Binary Parse Events:')
            from hwp5.bintype import log_events
            for ev, item in log_events(self.binevents, logger.error):
                pass
        logger.error('Model Stack:')
        for level, c in enumerate(reversed(e.parse_stack_traces)):
            model = c['model']
            if isinstance(model, StructType):
                logger.error('  %s', model)
                parsed_members = c['parsed']
                for member in parsed_members:
                    offset = member.get('offset', 0)
                    offset_end = member.get('offset_end', 1)
                    name = member['name']
                    value = member['value']
                    logger.error('    %06x:%06x: %s = %s',
                                 offset, offset_end - 1, name, value)
                logger.error('    %06x:      : %s', c['offset'], c['member'])
                pass
            else:
                logger.error('  %s%s', ' ' * level, c)


def typed_struct_attributes(struct, attributes, context):
    attributes = dict(attributes)

    def popvalue(member):
        name = member['name']
        if name in attributes:
            return attributes.pop(name)
        else:
            return member['type']()

    for member in struct.parse_members_with_inherited(context, popvalue):
        yield member

    # remnants
    for name, value in attributes.iteritems():
        yield dict(name=name, type=type(value), value=value)


class StructType(CompoundType):
    def __init__(cls, name, bases, attrs):
        super(StructType, cls).__init__(name, bases, attrs)
        if 'attributes' in cls.__dict__:
            members = (dict(type=member[0], name=member[1])
                       if isinstance(member, tuple)
                       else member
                       for member in cls.attributes())
            cls.members = list(members)
        for k, v in attrs.iteritems():
            if isinstance(v, EnumType):
                v.__name__ = k
                v.scoping_struct = cls
            elif isinstance(v, FlagsType):
                v.__name__ = k

    def parse_members(cls, context, getvalue):
        if 'attributes' not in cls.__dict__:
            return
        values = dict()
        for member in cls.members:
            member = dict(member)
            if isinstance(member['type'], X_ARRAY):
                member['type'] = member['type'](context, values)
            elif isinstance(member['type'], SelectiveType):
                member['type'] = member['type'](context, values)

            member_version = member.get('version')
            if member_version is None or context['version'] >= member_version:
                condition_func = member.get('condition')
                if condition_func is None or condition_func(context, values):
                    try:
                        value = getvalue(member)
                    except ParseError, e:
                        tracepoint = dict(model=cls, member=member['name'])
                        e.parse_stack_traces.append(tracepoint)
                        raise
                    values[member['name']] = member['value'] = value
                    yield member

    def parse_members_with_inherited(cls, context, getvalue, up_to_cls=None):
        import inspect
        from itertools import takewhile
        mro = inspect.getmro(cls)
        mro = takewhile(lambda cls: cls is not up_to_cls, mro)
        mro = list(cls for cls in mro if 'attributes' in cls.__dict__)
        mro = reversed(mro)
        for cls in mro:
            for member in cls.parse_members(context, getvalue):
                yield member


class Struct(object):
    __metaclass__ = StructType


def dumpbytes(data, crust=False):
    offsbase = 0
    if crust:
        yield '\t 0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F'
    while len(data) > 16:
        if crust:
            line = '%05x0: ' % offsbase
        else:
            line = ''
        line += ' '.join(['%02x' % ord(ch) for ch in data[0:16]])
        yield line
        data = data[16:]
        offsbase += 1

    if crust:
        line = '%05x0: ' % offsbase
    else:
        line = ''
    line += ' '.join(['%02x' % ord(ch) for ch in data])
    yield line


def hexdump(data, crust=False):
    return '\n'.join([line for line in dumpbytes(data, crust)])


class IndentedOutput:
    def __init__(self, base, level):
        self.base = base
        self.level = level

    def write(self, x):
        for line in x.split('\n'):
            if len(line) > 0:
                self.base.write('\t' * self.level)
                self.base.write(line)
                self.base.write('\n')


class Printer:
    def __init__(self, baseout):
        self.baseout = baseout

    def prints(self, *args):
        for x in args:
            self.baseout.write(str(x) + ' ')
        self.baseout.write('\n')

########NEW FILE########
__FILENAME__ = distdoc
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
''' Decode distribute docs.

Based on the algorithm described by Changwoo Ryu
See https://groups.google.com/forum/#!topic/hwp-foss/d2KL2ypR89Q
'''
import logging

from hwp5.recordstream import read_record
from hwp5.tagids import HWPTAG_DISTRIBUTE_DOC_DATA
from hwp5.importhelper import importStringIO
from hwp5.plat import get_aes128ecb_decrypt

StringIO = importStringIO()

logger = logging.getLogger(__name__)


def decode(stream):
    distdoc_data_record = read_record(stream, 0)
    if distdoc_data_record['tagid'] != HWPTAG_DISTRIBUTE_DOC_DATA:
        raise IOError('the first record is not an HWPTAG_DISTRIBUTE_DOC_DATA')
    distdoc_data = distdoc_data_record['payload']
    key = decode_head_to_key(distdoc_data)
    tail = stream.read()
    decrypted = decrypt_tail(key, tail)
    return StringIO(decrypted)


class Random:
    ''' MSVC's srand()/rand() like pseudorandom generator.
    '''

    def __init__(self, seed):
        self.seed = seed

    def rand(self):
        self.seed = (self.seed * 214013 + 2531011) & 0xffffffff
        value = (self.seed >> 16) & 0x7fff
        return value


def decode_head_to_sha1(record_payload):
    ''' Decode HWPTAG_DISTRIBUTE_DOC_DATA.

    It's the sha1 digest of user-supplied password string, i.e.,

        '12345' -> hashlib.sha1('12345').digest()

    '''
    if len(record_payload) != 256:
        raise ValueError('payload size must be 256 bytes')

    data = list(ord(x) for x in record_payload)
    seed = data[3] << 24 | data[2] << 16 | data[1] << 8 | data[0]
    random = Random(seed)

    n = 0
    for i in range(256):
        if n == 0:
            key = random.rand() & 0xff
            n = (random.rand() & 0xf) + 1
        if i >= 4:
            data[i] = data[i] ^ key
        n -= 1

    decoded = ''.join(chr(x) for x in data)
    sha1offset = 4 + (data[0] & 0xf)

    ucs16le = decoded[sha1offset:sha1offset + 80]
    return ucs16le


def decode_head_to_key(record_payload):
    sha1ucs16le = decode_head_to_sha1(record_payload)
    return sha1ucs16le[:16]


def decrypt_tail(key, encrypted_tail):
    decrypt = get_aes128ecb_decrypt()
    return decrypt(key, encrypted_tail)

########NEW FILE########
__FILENAME__ = errors
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


class InvalidOleStorageError(Exception):
    ''' Invalid OLE2 Compound Binary File. '''
    pass


class InvalidHwp5FileError(Exception):
    ''' Invalid HWP Document format v5 File. '''
    pass

########NEW FILE########
__FILENAME__ = filestructure
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import codecs
import zlib
from .utils import cached_property
from .dataio import UINT32, Flags, Struct
from .storage import ItemWrapper
from .storage import StorageWrapper
from .storage import ItemConversionStorage
from .importhelper import importStringIO
import logging


logger = logging.getLogger(__name__)


StringIO = importStringIO()


HWP5_SIGNATURE = 'HWP Document File' + ('\x00' * 15)


class BYTES(type):
    def __new__(mcs, size):
        decode = staticmethod(lambda bytes, *args, **kwargs: bytes)
        return type.__new__(mcs, 'BYTES(%d)' % size, (str,),
                            dict(fixed_size=size, decode=decode))


class VERSION(object):
    fixed_size = 4

    def decode(cls, bytes):
        return (ord(bytes[3]), ord(bytes[2]),
                ord(bytes[1]), ord(bytes[0]))
    decode = classmethod(decode)


class FileHeader(Struct):
    Flags = Flags(UINT32,
                  0, 'compressed',
                  1, 'password',
                  2, 'distributable',
                  3, 'script',
                  4, 'drm',
                  5, 'xmltemplate_storage',
                  6, 'history',
                  7, 'cert_signed',
                  8, 'cert_encrypted',
                  9, 'cert_signature_extra',
                  10, 'cert_drm',
                  11, 'ccl')

    def attributes(cls):
        yield BYTES(32), 'signature'
        yield VERSION, 'version'
        yield cls.Flags, 'flags'
        yield BYTES(216), 'reserved'
    attributes = classmethod(attributes)


def recode(backend_stream, backend_encoding, frontend_encoding,
           errors='strict'):
    import codecs
    enc = codecs.getencoder(frontend_encoding)
    dec = codecs.getdecoder(frontend_encoding)
    rd = codecs.getreader(backend_encoding)
    wr = codecs.getwriter(backend_encoding)
    return codecs.StreamRecoder(backend_stream, enc, dec, rd, wr, errors)


def recoder(backend_encoding, frontend_encoding, errors='strict'):
    def recode(backend_stream):
        import codecs
        enc = codecs.getencoder(frontend_encoding)
        dec = codecs.getdecoder(frontend_encoding)
        rd = codecs.getreader(backend_encoding)
        wr = codecs.getwriter(backend_encoding)
        return codecs.StreamRecoder(backend_stream, enc, dec, rd, wr, errors)
    return recode


def is_hwp5file(filename):
    ''' Test whether it is an HWP format v5 file. '''
    from hwp5.errors import InvalidOleStorageError
    from hwp5.storage.ole import OleStorage
    try:
        olestg = OleStorage(filename)
    except InvalidOleStorageError:
        return False
    return storage_is_hwp5file(olestg)


def storage_is_hwp5file(stg):
    try:
        fileheader = stg['FileHeader']
    except KeyError:
        logger.info('stg has no FileHeader')
        return False
    fileheader = HwpFileHeader(fileheader)
    if fileheader.signature == HWP5_SIGNATURE:
        return True
    else:
        logger.info('fileheader.signature = %r', fileheader.signature)
        return False


class GeneratorReader(object):
    ''' convert a string generator into file-like reader

        def gen():
            yield 'hello'
            yield 'world'

        f = GeneratorReader(gen())
        assert 'hell' == f.read(4)
        assert 'oworld' == f.read()
    '''

    def __init__(self, gen):
        self.gen = gen
        self.buffer = ''

    def read(self, size=None):
        if size is None:
            d, self.buffer = self.buffer, ''
            return d + ''.join(self.gen)

        for data in self.gen:
            self.buffer += data
            bufsize = len(self.buffer)
            if bufsize >= size:
                size = min(bufsize, size)
                d, self.buffer = self.buffer[:size], self.buffer[size:]
                return d

        d, self.buffer = self.buffer, ''
        return d

    def close(self):
        self.gen = self.buffer = None


class ZLibIncrementalDecoder(codecs.IncrementalDecoder):
    def __init__(self, errors='strict', wbits=15):
        assert errors == 'strict'
        self.errors = errors
        self.wbits = wbits
        self.reset()

    def decode(self, input, final=False):
        c = self.decompressobj.decompress(input)
        if final:
            c += self.decompressobj.flush()
        return c

    def reset(self):
        self.decompressobj = zlib.decompressobj(self.wbits)


def uncompress_gen(source, bufsize=4096):
    dec = ZLibIncrementalDecoder(wbits=-15)
    exausted = False
    while not exausted:
        input = source.read(bufsize)
        if len(input) < bufsize:
            exausted = True
        yield dec.decode(input, exausted)


def uncompress_experimental(source, bufsize=4096):
    ''' uncompress inputstream

        stream: a file-like readable
        returns a file-like readable
    '''
    return GeneratorReader(uncompress_gen(source, bufsize))


def uncompress(stream):
    ''' uncompress inputstream

        stream: a file-like readable
        returns a file-like readable
    '''
    return StringIO(zlib.decompress(stream.read(), -15))  # without gzip header


class CompressedStream(ItemWrapper):

    def open(self):
        return uncompress(self.wrapped.open())


class CompressedStorage(StorageWrapper):
    ''' uncompress streams in the underlying storage '''
    def __getitem__(self, name):
        from hwp5.storage import is_stream
        item = self.wrapped[name]
        if is_stream(item):
            return CompressedStream(item)
        else:
            return item


class PasswordProtectedStream(ItemWrapper):

    def open(self):
        # TODO: 현재로선 암호화된 내용을 그냥 반환
        logger.warning('Password-encrypted stream: currently decryption is '
                       'not supported')
        return self.wrapped.open()


class PasswordProtectedStorage(StorageWrapper):
    def __getitem__(self, name):
        from hwp5.storage import is_stream
        item = self.wrapped[name]
        if is_stream(item):
            return PasswordProtectedStream(item)
        else:
            return item


class Hwp5PasswordProtectedDoc(ItemConversionStorage):

    def resolve_conversion_for(self, name):
        if name in ('BinData', 'BodyText', 'Scripts', 'ViewText'):
            return PasswordProtectedStorage
        elif name in ('DocInfo', ):
            return PasswordProtectedStream


class VersionSensitiveItem(ItemWrapper):

    def __init__(self, item, version):
        ItemWrapper.__init__(self, item)
        self.version = version

    def open(self):
        return self.wrapped.open()

    def other_formats(self):
        return dict()


class Hwp5FileBase(ItemConversionStorage):
    ''' Base of an Hwp5File.

    Hwp5FileBase checks basic validity of an HWP format v5 and provides
    `fileheader` property.

    :param stg: an OLE2 structured storage.
    :type stg: an instance of storage, OleFileIO or filename
    :raises InvalidHwp5FileError: `stg` is not a valid HWP format v5 document.
    '''

    def __init__(self, stg):
        from hwp5.errors import InvalidOleStorageError
        from hwp5.errors import InvalidHwp5FileError
        from hwp5.storage import is_storage
        from hwp5.storage.ole import OleStorage
        if not is_storage(stg):
            try:
                stg = OleStorage(stg)
            except InvalidOleStorageError:
                raise InvalidHwp5FileError('Not an OLE2 Compound Binary File.')

        if not storage_is_hwp5file(stg):
            errormsg = 'Not an HWP Document format v5 storage.'
            raise InvalidHwp5FileError(errormsg)

        ItemConversionStorage.__init__(self, stg)

    def resolve_conversion_for(self, name):
        if name == 'FileHeader':
            return HwpFileHeader

    def get_fileheader(self):
        return self['FileHeader']

    fileheader = cached_property(get_fileheader)

    header = fileheader


class Hwp5DistDocStream(VersionSensitiveItem):

    def open(self):
        from hwp5.distdoc import decode
        encodedstream = self.wrapped.open()
        return decode(encodedstream)

    def head_record(self):
        item = self.wrapped.open()
        from .recordstream import read_record
        return read_record(item, 0)

    def head_record_stream(self):
        from .recordstream import record_to_json
        record = self.head_record()
        json = record_to_json(record)
        return GeneratorReader(iter([json]))

    def head(self):
        record = self.head_record()
        return record['payload']

    def head_stream(self):
        return StringIO(self.head())

    def head_sha1(self):
        from hwp5.distdoc import decode_head_to_sha1
        payload = self.head()
        return decode_head_to_sha1(payload)

    def head_key(self):
        from hwp5.distdoc import decode_head_to_key
        payload = self.head()
        return decode_head_to_key(payload)

    def tail(self):
        item = self.wrapped.open()
        from .recordstream import read_record
        read_record(item, 0)
        assert 4 + 256 == item.tell()
        return item.read()

    def tail_decrypted(self):
        from hwp5.distdoc import decrypt_tail
        key = self.head_key()
        tail = self.tail()
        return decrypt_tail(key, tail)

    def tail_stream(self):
        return StringIO(self.tail())


class Hwp5DistDocStorage(ItemConversionStorage):

    def resolve_conversion_for(self, name):
        def conversion(item):
            return Hwp5DistDocStream(self.wrapped[name], None)  # TODO: version
        return conversion


class Hwp5DistDoc(ItemConversionStorage):

    def resolve_conversion_for(self, name):
        if name in ('Scripts', 'ViewText'):
            return Hwp5DistDocStorage


class Hwp5Compression(ItemConversionStorage):
    ''' handle compressed streams in HWPv5 files '''

    def resolve_conversion_for(self, name):
        if name in ('BinData', 'BodyText', 'ViewText'):
            return CompressedStorage
        elif name == 'DocInfo':
            return CompressedStream
        elif name == 'Scripts':
            return CompressedStorage


class PreviewText(object):

    def __init__(self, item):
        self.open = item.open

    def other_formats(self):
        return {'.utf8': self.open_utf8}

    def open_utf8(self):
        recode = recoder('utf-16le', 'utf-8')
        return recode(self.open())

    def get_utf8(self):
        f = self.open_utf8()
        try:
            return f.read()
        finally:
            f.close()

    utf8 = cached_property(get_utf8)

    def __str__(self):
        return self.utf8


class Sections(ItemConversionStorage):

    section_class = VersionSensitiveItem

    def __init__(self, stg, version):
        ItemConversionStorage.__init__(self, stg)
        self.version = version

    def resolve_conversion_for(self, name):
        def conversion(item):
            return self.section_class(self.wrapped[name], self.version)
        return conversion

    def other_formats(self):
        return dict()

    def section(self, idx):
        return self['Section%d' % idx]

    def section_indexes(self):
        def gen():
            for name in self:
                if name.startswith('Section'):
                    idx = name[len('Section'):]
                    try:
                        idx = int(idx)
                    except:
                        pass
                    else:
                        yield idx
        indexes = list(gen())
        indexes.sort()
        return indexes

    @property
    def sections(self):
        return list(self.section(idx)
                    for idx in self.section_indexes())


class HwpFileHeader(object):

    def __init__(self, item):
        self.open = item.open

    def to_dict(self):
        from hwp5.bintype import read_type
        f = self.open()
        try:
            return read_type(FileHeader, dict(), f)
        finally:
            f.close()

    value = cached_property(to_dict)

    def get_version(self):
        return self.value['version']

    version = cached_property(get_version)

    def get_signature(self):
        return self.value['signature']

    signature = cached_property(get_signature)

    def get_flags(self):
        return FileHeader.Flags(self.value['flags'])

    flags = cached_property(get_flags)

    def open_text(self):
        d = FileHeader.Flags.dictvalue(self.value['flags'])
        d['signature'] = self.value['signature']
        d['version'] = '%d.%d.%d.%d' % self.value['version']
        out = StringIO()
        for k, v in sorted(d.items()):
            print >> out, '%s: %s' % (k, v)
        out.seek(0)
        return out

    def other_formats(self):
        return {'.txt': self.open_text}


class HwpSummaryInfo(VersionSensitiveItem):

    def other_formats(self):
        return {'.txt': self.open_text}

    def to_dict(self):
        f = self.open()
        from hwp5.msoleprops import MSOLEPropertySet
        try:
            context = dict(version=self.version)
            summaryinfo = MSOLEPropertySet.read(f, context)
            return summaryinfo
        finally:
            f.close()

    value = cached_property(to_dict)

    def open_text(self):
        out = StringIO()

        def uuid_from_bytes_tuple(t):
            from uuid import UUID
            return UUID(bytes_le=''.join(chr(x) for x in t))

        print >> out, 'byteorder: 0x%x' % self.value['byteorder']
        print >> out, 'clsid: %s' % uuid_from_bytes_tuple(self.value['clsid'])
        print >> out, 'format: %d' % self.value['format']
        print >> out, 'os: %d' % self.value['os']
        print >> out, 'osversion: %d' % self.value['osversion']

        for section in self.value['sections']:
            formatid = uuid_from_bytes_tuple(section['formatid'])
            print >> out, ('-- Section %s --' % formatid)
            for prop in section['properties'].values():
                prop_str = u'%s: %s' % (prop['name'], prop.get('value'))
                print >> out, prop_str.encode('utf-8')

        out.seek(0)
        return out


class Hwp5File(ItemConversionStorage):
    ''' represents HWPv5 File

        Hwp5File(stg)

        stg: an instance of Storage
    '''

    def __init__(self, stg):
        stg = Hwp5FileBase(stg)

        if stg.header.flags.password:
            stg = Hwp5PasswordProtectedDoc(stg)

            # TODO: 현재로선 decryption이 구현되지 않았으므로,
            # 레코드 파싱은 불가능하다. 적어도 encrypted stream에
            # 직접 접근은 가능하도록, 다음 레이어들은 bypass한다.
            ItemConversionStorage.__init__(self, stg)
            return

        if stg.header.flags.distributable:
            stg = Hwp5DistDoc(stg)

        if stg.header.flags.compressed:
            stg = Hwp5Compression(stg)

        ItemConversionStorage.__init__(self, stg)

    def resolve_conversion_for(self, name):
        if name == 'DocInfo':
            return self.with_version(self.docinfo_class)
        if name == 'BodyText':
            return self.with_version(self.bodytext_class)
        if name == 'ViewText':
            return self.with_version(self.bodytext_class)
        if name == 'PrvText':
            return PreviewText
        if name == '\005HwpSummaryInformation':
            return self.with_version(HwpSummaryInfo)

    def with_version(self, f):
        def wrapped(item):
            return f(item, self.header.version)
        return wrapped

    docinfo_class = VersionSensitiveItem
    bodytext_class = Sections

    @cached_property
    def summaryinfo(self):
        return self['\005HwpSummaryInformation']

    @cached_property
    def docinfo(self):
        return self['DocInfo']

    @cached_property
    def preview_text(self):
        return self['PrvText']

    @cached_property
    def bodytext(self):
        return self['BodyText']

    @cached_property
    def viewtext(self):
        return self['ViewText']

    @property
    def text(self):
        if self.header.flags.distributable:
            return self.viewtext
        else:
            return self.bodytext

########NEW FILE########
__FILENAME__ = hwp5html
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''HWPv5 to HTML converter

Usage::

    hwp5html [options] <hwp5file> [<out-directory>]
    hwp5html -h | --help
    hwp5html --version

Options::

    -h --help           Show this screen
    --version           Show version
    --loglevel=<level>  Set log level.
    --logfile=<file>    Set log file.
'''
from __future__ import with_statement
from contextlib import contextmanager
import os.path
import logging
import shutil

from hwp5.importhelper import pkg_resources_filename
from hwp5.hwp5odt import mkstemp_open

logger = logging.getLogger(__name__)


def main():
    import sys
    from hwp5 import __version__ as version
    from hwp5.proc import rest_to_docopt
    from hwp5.proc import init_logger
    from hwp5.errors import InvalidHwp5FileError
    from docopt import docopt
    doc = rest_to_docopt(__doc__)
    args = docopt(doc, version=version)
    init_logger(args)

    filename = args['<hwp5file>']
    from hwp5.dataio import ParseError
    from hwp5.xmlmodel import Hwp5File
    try:
        hwp5file = Hwp5File(filename)
    except ParseError, e:
        e.print_to_logger(logger)
        sys.exit(1)
    except InvalidHwp5FileError, e:
        logger.error('%s', e)
        sys.exit(1)
    else:
        outdir = args['<out-directory>']
        if outdir is None:
            outdir, ext = os.path.splitext(os.path.basename(filename))
        generate_htmldir(hwp5file, outdir)


def generate_htmldir(hwp5file, base_dir):
    if not os.path.exists(base_dir):
        os.mkdir(base_dir)
    generate_htmldir_files(hwp5file, base_dir)


def generate_htmldir_files(hwp5file, base_dir):
    import os
    from tempfile import mkstemp
    from hwp5.plat import get_xslt

    xslt = get_xslt()
    fd, path = mkstemp()
    try:
        xhwp5 = os.fdopen(fd, 'w')
        try:
            hwp5file.xmlevents(embedbin=False).dump(xhwp5)
        finally:
            xhwp5.close()

        html_path = os.path.join(base_dir, 'index.xhtml')
        generate_html_file(xslt, path, html_path)

        css_path = os.path.join(base_dir, 'styles.css')
        generate_css_file(xslt, path, css_path)
    finally:
        os.unlink(path)

    bindata_dir = os.path.join(base_dir, 'bindata')
    extract_bindata_dir(hwp5file, bindata_dir)


def generate_css_file(xslt, xhwp5_path, css_path):
    with hwp5_resources_path('xsl/hwp5css.xsl') as css_xsl:
        xslt(css_xsl, xhwp5_path, css_path)


def generate_html_file(xslt, xhwp5_path, html_path):
    with hwp5_resources_path('xsl/hwp5html.xsl') as html_xsl:
        xslt(html_xsl, xhwp5_path, html_path)


def extract_bindata_dir(hwp5file, bindata_dir):
    if 'BinData' not in hwp5file:
        return
    bindata_stg = hwp5file['BinData']
    if not os.path.exists(bindata_dir):
        os.mkdir(bindata_dir)

    from hwp5.storage import unpack
    unpack(bindata_stg, bindata_dir)


@contextmanager
def hwp5_resources_path(res_path):
    try:
        path = pkg_resources_filename('hwp5', res_path)
    except Exception:
        logger.info('%s: pkg_resources_filename failed; using resource_stream',
                    res_path)
        with mkstemp_open() as (path, g):
            import pkg_resources
            f = pkg_resources.resource_stream('hwp5', res_path)
            try:
                shutil.copyfileobj(f, g)
                g.close()
                yield path
            finally:
                f.close()
    else:
        yield path

########NEW FILE########
__FILENAME__ = hwp5odt
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''HWPv5 to ODT converter

Usage::

    hwp5odt [options] [--embed-image] <hwp5file>
    hwp5odt [options] --styles <hwp5file>
    hwp5odt [options] --content [--embed-image] <hwp5file>
    hwp5odt [options] --document [--no-embed-image] <hwp5file>
    hwp5odt -h | --help
    hwp5odt --version

Options::

    -h --help           Show this screen
    --version           Show version
    --loglevel=<level>  Set log level.
    --logfile=<file>    Set log file.

    --document          Produce single OpenDocument XML file (.fodt)
    --styles            Produce *.styles.xml
    --content           Produce *.content.xml
'''
from __future__ import with_statement
import os
import os.path
import logging
import sys
import tempfile
from contextlib import contextmanager

from docopt import docopt

from hwp5 import plat
from hwp5 import __version__ as version
from hwp5.proc import rest_to_docopt
from hwp5.proc import init_logger
from hwp5.errors import InvalidHwp5FileError
from hwp5.importhelper import pkg_resources_filename


logger = logging.getLogger(__name__)


def main():
    doc = rest_to_docopt(__doc__)
    args = docopt(doc, version=version)
    init_logger(args)

    init_with_environ()

    convert = make_converter(args)

    hwpfilename = args['<hwp5file>']
    root = os.path.basename(hwpfilename)
    if root.lower().endswith('.hwp'):
        root = root[0:-4]
    dest_path = root + '.' + convert.dest_ext

    from hwp5.dataio import ParseError
    try:
        with convert.prepare():
            convert.convert(hwpfilename, dest_path)
    except ParseError, e:
        e.print_to_logger(logger)
    except InvalidHwp5FileError, e:
        logger.error('%s', e)
        sys.exit(1)


def init_with_environ():
    if 'PYHWP_XSLTPROC' in os.environ:
        from hwp5.plat import xsltproc
        xsltproc.executable = os.environ['PYHWP_XSLTPROC']
        xsltproc.enable()

    if 'PYHWP_XMLLINT' in os.environ:
        from hwp5.plat import xmllint
        xmllint.executable = os.environ['PYHWP_XMLLINT']
        xmllint.enable()


def make_converter(args):
    xslt = plat.get_xslt()
    if xslt is None:
        logger.error('no XSLT implementation is available.')
        sys.exit(1)

    rng = plat.get_relaxng()
    if rng is None:
        logger.warning('no RelaxNG implementation is available.')

    if args['--document']:
        return ODTSingleDocumentConverter(xslt, rng,
                                          not args['--no-embed-image'])
    elif args['--styles']:
        return ODTStylesConverter(xslt, rng)
    elif args['--content']:
        return ODTContentConverter(xslt, rng, args['--embed-image'])
    else:
        return ODTPackageConverter(xslt, rng, args['--embed-image'])


class ODTPackage(object):
    def __init__(self, path_or_zipfile):
        self.files = []

        if isinstance(path_or_zipfile, basestring):
            from zipfile import ZipFile
            zipfile = ZipFile(path_or_zipfile, 'w')
        else:
            zipfile = path_or_zipfile
        self.zf = zipfile

    def insert_stream(self, f, path, media_type):
        if isinstance(path, unicode):
            path_bytes = path.encode('utf-8')
            path_unicode = path
        else:
            path_bytes = path
            path_unicode = unicode(path)
        self.zf.writestr(path_bytes, f.read())
        self.files.append(dict(full_path=path_unicode, media_type=media_type))

    def close(self):

        from cStringIO import StringIO
        manifest = StringIO()
        manifest_xml(manifest, self.files)
        manifest.seek(0)
        self.zf.writestr('META-INF/manifest.xml', manifest.getvalue())
        self.zf.writestr('mimetype', 'application/vnd.oasis.opendocument.text')

        self.zf.close()


def hwp5_resources_filename(path):
    ''' get paths of 'hwp5' package resources '''
    return pkg_resources_filename('hwp5', path)


@contextmanager
def hwp5_resources_path(path):
    yield pkg_resources_filename('hwp5', path)


def unlink_or_warning(path):
    try:
        os.unlink(path)
    except Exception, e:
        logger.exception(e)
        logger.warning('%s cannot be deleted', path)


@contextmanager
def mkstemp_open(*args, **kwargs):

    if (kwargs.get('text', False) or (len(args) >= 4 and args[3])):
        text = True
    else:
        text = False

    mode = 'w+' if text else 'wb+'
    fd, path = tempfile.mkstemp(*args, **kwargs)
    try:
        f = os.fdopen(fd, mode)
        try:
            yield path, f
        finally:
            try:
                f.close()
            except Exception:
                pass
    finally:
        unlink_or_warning(path)


class ConverterBase(object):
    def __init__(self, xslt, validator):
        self.xslt = xslt
        self.validator = validator

    @contextmanager
    def make_xhwp5file(self, hwp5file, embedimage):
        with mkstemp_open(prefix='hwp5-', suffix='.xml',
                          text=True) as (path, f):
            hwp5file.xmlevents(embedbin=embedimage).dump(f)
            yield path

    @contextmanager
    def transform(self, xsl_path, xhwp5_path):
        with mkstemp_open(prefix='xslt-') as (path, f):
            f.close()
            self.transform_to(xsl_path, xhwp5_path, path)
            yield path

    def transform_to(self, xsl_path, xhwp5_path, output_path):
        self.xslt(xsl_path, xhwp5_path, output_path)
        if self.validator is not None:
            valid = self.validator(output_path)
            if not valid:
                raise Exception('validation failed')


class ODTConverter(ConverterBase):

    rng_path = 'odf-relaxng/OpenDocument-v1.2-os-schema.rng'

    def __init__(self, xslt, relaxng=None):
        self.relaxng = relaxng
        ConverterBase.__init__(self, xslt, None)

    @contextmanager
    def prepare(self):
        if self.relaxng:
            with hwp5_resources_path(self.rng_path) as rng_path:
                self.validator = lambda path: self.relaxng(rng_path, path)
                yield
                self.validator = None
        else:
            yield

    def convert(self, hwpfilename, dest_path):
        from .xmlmodel import Hwp5File
        hwpfile = Hwp5File(hwpfilename)
        try:
            self.convert_to(hwpfile, dest_path)
        finally:
            hwpfile.close()


class ODTStylesConverter(ODTConverter):

    dest_ext = 'styles.xml'
    styles_xsl_path = 'xsl/odt/styles.xsl'

    @contextmanager
    def prepare(self):
        with ODTConverter.prepare(self):
            with hwp5_resources_path(self.styles_xsl_path) as path:
                self.xsl_styles = path
                yield
                del self.xsl_styles

    def convert_to(self, hwp5file, output_path):
        with self.make_xhwp5file(hwp5file, embedimage=False) as xhwp5_path:
            self.transform_to(self.xsl_styles, xhwp5_path, output_path)


class ODTContentConverter(ODTConverter):

    dest_ext = 'content.xml'
    content_xsl_path = 'xsl/odt/content.xsl'

    def __init__(self, xslt, relaxng=None, embedimage=False):
        ODTConverter.__init__(self, xslt, relaxng)
        self.embedimage = embedimage

    @contextmanager
    def prepare(self):
        with ODTConverter.prepare(self):
            with hwp5_resources_path(self.content_xsl_path) as path:
                self.xsl_content = path
                yield
                del self.xsl_content

    def convert_to(self, hwp5file, output_path):
        with self.make_xhwp5file(hwp5file, self.embedimage) as xhwp5_path:
            self.transform_to(self.xsl_content, xhwp5_path, output_path)


class ODTPackageConverter(ODTConverter):

    dest_ext = 'odt'
    styles_xsl_path = 'xsl/odt/styles.xsl'
    content_xsl_path = 'xsl/odt/content.xsl'

    def __init__(self, xslt, relaxng=None, embedimage=False):
        ODTConverter.__init__(self, xslt, relaxng)
        self.embedimage = embedimage

    @contextmanager
    def prepare(self):
        with ODTConverter.prepare(self):
            with hwp5_resources_path(self.content_xsl_path) as path:
                self.xsl_content = path
                with hwp5_resources_path(self.styles_xsl_path) as path:
                    self.xsl_styles = path
                    yield
                    del self.xsl_styles
                del self.xsl_content

    def convert_to(self, hwp5file, odtpkg_path):
        odtpkg = ODTPackage(odtpkg_path)
        try:
            self.build_odtpkg_streams(hwp5file, odtpkg)
        finally:
            odtpkg.close()

    def build_odtpkg_streams(self, hwp5file, odtpkg):
        with self.make_xhwp5file(hwp5file, self.embedimage) as xhwp5_path:
            with self.make_styles(xhwp5_path) as f:
                odtpkg.insert_stream(f, 'styles.xml', 'text/xml')
            with self.make_content(xhwp5_path) as f:
                odtpkg.insert_stream(f, 'content.xml', 'text/xml')

        from cStringIO import StringIO
        rdf = StringIO()
        manifest_rdf(rdf)
        rdf.seek(0)
        odtpkg.insert_stream(rdf, 'manifest.rdf', 'application/rdf+xml')

        for f, name, mimetype in self.additional_files(hwp5file):
            odtpkg.insert_stream(f, name, mimetype)

    @contextmanager
    def make_styles(self, xhwp5):
        with self.transform(self.xsl_styles, xhwp5) as path:
            with open(path) as f:
                yield f

    @contextmanager
    def make_content(self, xhwp5):
        with self.transform(self.xsl_content, xhwp5) as path:
            with open(path) as f:
                yield f

    def additional_files(self, hwp5file):
        if 'BinData' in hwp5file:
            bindata = hwp5file['BinData']
            for name in bindata:
                f = bindata[name].open()
                yield f, 'bindata/' + name, 'application/octet-stream'


class ODTSingleDocumentConverter(ODTConverter):

    dest_ext = 'fodt'

    def __init__(self, xslt, relaxng=None, embedimage=False):
        ODTConverter.__init__(self, xslt, relaxng)
        self.xsl_document = hwp5_resources_filename('xsl/odt/document.xsl')
        self.embedimage = embedimage

    def convert_to(self, hwp5file, output_path):
        with self.make_xhwp5file(hwp5file, self.embedimage) as xhwp5_path:
            self.transform_to(self.xsl_document, xhwp5_path, output_path)


def manifest_xml(f, files):
    from xml.sax.saxutils import XMLGenerator
    xml = XMLGenerator(f, 'utf-8')
    xml.startDocument()

    uri = 'urn:oasis:names:tc:opendocument:xmlns:manifest:1.0'
    prefix = 'manifest'
    xml.startPrefixMapping(prefix, uri)

    def startElement(name, attrs):
        attrs = dict(((uri, n), v) for n, v in attrs.iteritems())
        xml.startElementNS((uri, name), prefix + ':' + name, attrs)

    def endElement(name):
        xml.endElementNS((uri, name), prefix + ':' + name)

    def file_entry(full_path, media_type, **kwargs):
        attrs = {'media-type': media_type, 'full-path': full_path}
        attrs.update(dict((n.replace('_', '-'), v)
                          for n, v in kwargs.iteritems()))
        startElement('file-entry', attrs)
        endElement('file-entry')

    startElement('manifest', dict(version='1.2'))
    file_entry('/', 'application/vnd.oasis.opendocument.text', version='1.2')
    for e in files:
        e = dict(e)
        full_path = e.pop('full_path')
        media_type = e.pop('media_type', 'application/octet-stream')
        file_entry(full_path, media_type)
    endElement('manifest')

    xml.endPrefixMapping(prefix)
    xml.endDocument()


def manifest_rdf(f):
    f.write('''<?xml version="1.0" encoding="utf-8"?>
<rdf:RDF
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:pkg="http://docs.oasis-open.org/ns/office/1.2/meta/pkg#"
    xmlns:odf="http://docs.oasis-open.org/ns/office/1.2/meta/odf#">
    <pkg:Document rdf:about="">
        <pkg:hasPart rdf:resource="content.xml"/>
        <pkg:hasPart rdf:resource="styles.xml"/>
    </pkg:Document>
    <odf:ContentFile rdf:about="content.xml"/>
    <odf:StylesFile rdf:about="styles.xml"/>
</rdf:RDF>''')


def mimetype(f):
    f.write('application/vnd.oasis.opendocument.text')

########NEW FILE########
__FILENAME__ = hwp5txt
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''HWPv5 to text converter

Usage::

    hwp5txt [options] <hwp5file>
    hwp5txt -h | --help
    hwp5txt --version

Options::

    -h --help           Show this screen
    --version           Show version
    --loglevel=<level>  Set log level.
    --logfile=<file>    Set log file.
'''
import os.path


def main():
    from hwp5 import __version__ as version
    from hwp5.proc import rest_to_docopt
    from hwp5.proc import init_logger
    from docopt import docopt
    doc = rest_to_docopt(__doc__)
    args = docopt(doc, version=version)
    init_logger(args)

    make(args)


def make(args):
    from hwp5.plat import get_xslt
    from hwp5.importhelper import pkg_resources_filename
    from tempfile import mkstemp
    from hwp5.xmlmodel import Hwp5File

    hwp5_filename = args['<hwp5file>']
    rootname = os.path.basename(hwp5_filename)
    if rootname.lower().endswith('.hwp'):
        rootname = rootname[0:-4]
    txt_path = rootname + '.txt'

    xslt = get_xslt()
    plaintext_xsl = pkg_resources_filename('hwp5', 'xsl/plaintext.xsl')

    hwp5file = Hwp5File(hwp5_filename)
    try:
        xhwp5_fd, xhwp5_path = mkstemp()
        try:
            xhwp5_file = os.fdopen(xhwp5_fd, 'w')
            try:
                hwp5file.xmlevents().dump(xhwp5_file)
            finally:
                xhwp5_file.close()

            xslt(plaintext_xsl, xhwp5_path, txt_path)
        finally:
            os.unlink(xhwp5_path)
    finally:
        hwp5file.close()

########NEW FILE########
__FILENAME__ = importhelper
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


def importStringIO():
    ''' from cStringIO/StringIO import StringIO '''
    try:
        from cStringIO import StringIO
        return StringIO
    except:
        from StringIO import StringIO
        return StringIO


def importjson():
    try:
        import json
        return json
    except ImportError:
        import simplejson
        return simplejson


def pkg_resources_filename(pkg_name, path):
    ''' the equivalent of pkg_resources.resource_filename() '''
    try:
        import pkg_resources
    except ImportError:
        return pkg_resources_filename_fallback(pkg_name, path)
    else:
        return pkg_resources.resource_filename(pkg_name, path)


def pkg_resources_filename_fallback(pkg_name, path):
    ''' a fallback implementation of pkg_resources_filename() '''
    pkg_module = __import__(pkg_name)
    pkg_name = pkg_name.split('.')
    import os.path
    for x in pkg_name[1:]:
        pkg_module = getattr(pkg_module, x)
    pkg_dir = os.path.dirname(pkg_module.__file__)
    return os.path.join(pkg_dir, path)

########NEW FILE########
__FILENAME__ = msoleprops
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from datetime import datetime
from datetime import timedelta
import logging

from hwp5.dataio import Struct
from hwp5.dataio import Flags
from hwp5.dataio import N_ARRAY
from hwp5.dataio import ARRAY
from hwp5.dataio import BYTE
from hwp5.dataio import UINT16
from hwp5.dataio import UINT32
from hwp5.dataio import INT32
from hwp5.dataio import BSTR
from hwp5.bintype import read_type


logger = logging.getLogger(__name__)


vt_types = dict()


class VT_Type(type):
    def __new__(mcs, name, bases, attrs):
        t = type.__new__(mcs, name, bases, attrs)
        code = attrs['code']
        vt_types[code] = t
        return t


class VT_I4(object):
    __metaclass__ = VT_Type
    code = 3


class VT_LPWSTR(object):
    __metaclass__ = VT_Type
    code = 31


class VT_FILETIME(object):
    __metaclass__ = VT_Type
    code = 64


class MSOLEPropertySectionDesc(Struct):
    def attributes():
        yield ARRAY(BYTE, 16), 'formatid'
        yield UINT32, 'offset'
    attributes = staticmethod(attributes)


class MSOLEPropertySetHeader(Struct):
    def attributes():
        yield UINT16, 'byteorder'
        yield UINT16, 'format'
        yield UINT16, 'osversion'
        yield UINT16, 'os'
        yield ARRAY(BYTE, 16), 'clsid'
        yield N_ARRAY(UINT32, MSOLEPropertySectionDesc), 'sections'
    attributes = staticmethod(attributes)


class MSOLEPropertyDesc(Struct):
    def attributes():
        yield UINT32, 'id'
        yield UINT32, 'offset'  # offset from section start
    attributes = staticmethod(attributes)


class MSOLEPropertySetSectionHeader(Struct):
    def attributes():
        from hwp5.dataio import N_ARRAY
        yield UINT32, 'bytesize'
        yield N_ARRAY(UINT32, MSOLEPropertyDesc), 'properties'
    attributes = staticmethod(attributes)


class MSOLEPropertyName(Struct):
    def attributes():
        from hwp5.dataio import N_ARRAY
        from hwp5.dataio import BYTE
        yield UINT32, 'id'
        yield N_ARRAY(UINT32, BYTE), 'name'
    attributes = staticmethod(attributes)


class MSOLEPropertyNameDict(Struct):
    def attributes():
        from hwp5.dataio import N_ARRAY
        yield N_ARRAY(UINT32, MSOLEPropertyName), 'names'
    attributes = staticmethod(attributes)


class MSOLEProperty(Struct):
    TypeFlags = Flags(UINT32,
                      0, 16, 'code',
                      17, 'is_vector')

    def attributes(cls):
        yield cls.TypeFlags, 'type'
    attributes = classmethod(attributes)


class MSOLEPropertySet(object):
    def read(f, context):
        propset_header = read_type(MSOLEPropertySetHeader, context, f)
        common_prop_names = {
            0: 'Dictionary',
            1: 'CodePage',
            2: 'Title',
            3: 'Subject',
            4: 'Author',
            5: 'Keywords',
            6: 'Comments',
            7: 'Template',
            8: 'LastSavedBy',
            9: 'RevisionNumber',
            11: 'LastPrinted',
            12: 'CreateTime',
            13: 'LastSavedTime',
            14: 'NumPages',
        }
        for section_desc in propset_header['sections']:
            f.seek(section_desc['offset'])
            section_header = read_type(MSOLEPropertySetSectionHeader,
                                       context, f)
            section_desc['properties'] = section_properties = dict()
            prop_names = dict(common_prop_names)
            for prop_desc in section_header['properties']:
                prop_id = prop_desc['id']
                logger.debug('property id: %d', prop_id)
                f.seek(section_desc['offset'] + prop_desc['offset'])
                if prop_id == 0:
                    namedict = read_type(MSOLEPropertyNameDict, context, f)
                    section_prop_names = dict((name['id'], name['name'])
                                              for name in namedict['names'])
                    #prop_names.update(section_prop_names)
                    section_properties[prop_id] = prop = dict(id=prop_id)
                    prop['name'] = prop_names.get(prop_id, 'property-id-%s' %
                                                  prop_id)
                    prop['value'] = section_prop_names
                elif prop_id == 1:
                    # code page
                    pass
                else:
                    prop = read_type(MSOLEProperty, context, f)
                    prop['id'] = prop_id
                    section_properties[prop_id] = prop
                    if prop_id in prop_names:
                        prop['name'] = prop_names[prop_id]
                    else:
                        prop['name'] = 'property-id-%s' % prop_id
                    logger.debug('name: %s', prop['name'])
                    if not prop['type'].is_vector:
                        vt_code = prop['type'].code
                        vt_type = vt_types[vt_code]
                        logger.debug('type: %s', vt_type)
                        value = read_vt_value(vt_type, context, f)
                        if value is not None:
                            prop['value'] = value

        return propset_header
    read = staticmethod(read)


def read_vt_value(vt_type, context, f):
    if vt_type == VT_I4:
        value = read_type(INT32, context, f)
        logger.debug('value: %s', value)
        return value
    elif vt_type == VT_LPWSTR:
        value = read_type(BSTR, context, f)
        logger.debug('value: %s', value)
        return value
    elif vt_type == VT_FILETIME:
        lword = read_type(UINT32, context, f)
        hword = read_type(UINT32, context, f)
        value = hword << 32 | lword
        value = FILETIME_to_datetime(value)
        logger.debug('value: %s', value)
        return value


def FILETIME_to_datetime(value):
    return datetime(1601, 1, 1, 0, 0, 0) + timedelta(microseconds=value / 10)

########NEW FILE########
__FILENAME__ = javax_transform
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from __future__ import with_statement
import logging


logger = logging.getLogger(__name__)


def is_enabled():
    import sys
    if not sys.platform.startswith('java'):
        logger.info('%s: disabled', __name__)
        return False
    try:
        import javax.xml.transform
        javax
    except ImportError:
        logger.info('%s: disabled', __name__)
        return False
    else:
        logger.info('%s: enabled', __name__)
        return True


def xslt(xsl_path, inp_path, out_path):
    transform = xslt_compile(xsl_path)
    return transform(inp_path, out_path)


def xslt_compile(xsl_path):
    from javax.xml.transform import URIResolver
    from javax.xml.transform import TransformerFactory
    from javax.xml.transform.stream import StreamSource
    from javax.xml.transform.stream import StreamResult
    from java.io import FileInputStream
    from java.io import FileOutputStream
    import os.path

    xsl_path = os.path.abspath(xsl_path)
    xsl_base = os.path.dirname(xsl_path)

    xsl_fis = FileInputStream(xsl_path)

    xsl_source = StreamSource(xsl_fis)

    class BaseURIResolver(URIResolver):

        def __init__(self, base):
            self.base = base

        def resolve(self, href, base):
            path = os.path.join(self.base, href)
            path = os.path.abspath(path)
            fis = FileInputStream(path)
            return StreamSource(fis)

    uri_resolver = BaseURIResolver(xsl_base)

    xslt_factory = TransformerFactory.newInstance()
    xslt_factory.setURIResolver(uri_resolver)

    transformer = xslt_factory.newTransformer(xsl_source)

    def transform(inp_path, out_path):
        inp_path = os.path.abspath(inp_path)
        out_path = os.path.abspath(out_path)
        inp_fis = FileInputStream(inp_path)
        out_fos = FileOutputStream(out_path)
        inp_source = StreamSource(inp_fis)
        out_result = StreamResult(out_fos)
        transformer.transform(inp_source, out_result)
        return dict()
    return transform

########NEW FILE########
__FILENAME__ = jython_poifs
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


def is_enabled():
    try:
        from org.apache.poi.poifs.filesystem import POIFSFileSystem
        POIFSFileSystem  # silencing
        return True
    except ImportError:
        return False


class OleStorage(object):
    ''' Create an OleStorage instance.

    :param olefile: an OLE2 Compound Binary File.
    :raises: `InvalidOleStorageError` when `olefile` is not valid OLE2 format.
    '''

    def __init__(self, olefile):
        from hwp5.errors import InvalidOleStorageError
        from java.io import FileInputStream
        from java.io import IOException
        from org.apache.poi.poifs.filesystem import POIFSFileSystem
        from org.apache.poi.poifs.filesystem import DirectoryEntry

        if isinstance(olefile, basestring):
            import os.path
            path = os.path.abspath(olefile)
            fis = FileInputStream(path)
            try:
                fs = POIFSFileSystem(fis)
            except IOException, e:
                raise InvalidOleStorageError(e.getMessage())
            entry = fs.getRoot()
        elif isinstance(olefile, DirectoryEntry):
            entry = olefile
        else:
            raise ValueError('invalid olefile')

        self.entry = entry

    def __iter__(self):
        return (entry.getName() for entry in self.entry)

    def __getitem__(self, name):
        from java.io import FileNotFoundException
        try:
            entry = self.entry.getEntry(name)
        except FileNotFoundException:
            raise KeyError('%s not found' % name)

        if entry.directoryEntry:
            return OleStorage(entry)
        elif entry.documentEntry:
            return OleStream(entry)
        else:
            raise KeyError('%s is invalid' % name)

    def close(self):
        return


class OleStream(object):

    def __init__(self, entry):
        self.entry = entry

    def open(self):
        from org.apache.poi.poifs.filesystem import DocumentInputStream
        dis = DocumentInputStream(self.entry)
        return FileFromDocumentInputStream(dis)


class FileFromDocumentInputStream(object):

    def __init__(self, dis):
        self.dis = dis
        self.size = dis.available()
        dis.mark(0)

    def read(self, size=None):
        import jarray
        dis = self.dis
        available = dis.available()
        if size is None:
            size = available
        elif size > available:
            size = available
        bytes = jarray.zeros(size, 'b')
        n_read = dis.read(bytes)
        data = bytes.tostring()
        if n_read < size:
            return data[:n_read]
        return data

    def seek(self, offset, whence=0):
        dis = self.dis
        if whence == 0:
            dis.reset()
            dis.skip(offset)
        elif whence == 1:
            dis.skip(offset)
        elif whence == 2:
            dis.reset()
            dis.skip(self.size - offset)
        else:
            raise ValueError('invalid whence: %s', whence)

    def tell(self):
        return self.size - self.dis.available()

    def close(self):
        return self.dis.close()

########NEW FILE########
__FILENAME__ = olefileio
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from hwp5.utils import cached_property


def is_enabled():
    try:
        import OleFileIO_PL
    except Exception:
        return False
    else:
        OleFileIO_PL
        return True


class OleStorageItem(object):

    def __init__(self, olefile, path, parent=None):
        self.olefile = olefile
        self.path = path  # path DOES NOT end with '/'

    def get_name(self):
        if self.path == '':
            return None
        segments = self.path.split('/')
        return segments[-1]

    name = cached_property(get_name)


class OleStream(OleStorageItem):

    def open(self):
        return self.olefile.openstream(self.path)


class OleStorage(OleStorageItem):
    ''' Create an OleStorage instance.

    :param olefile: an OLE2 Compound Binary File.
    :type olefile: an OleFileIO instance or an argument to OleFileIO()
    :param path: internal path in the olefile. Should not end with '/'.
    :raises: `InvalidOleStorageError` when `olefile` is not valid OLE2 format.
    '''

    def __init__(self, olefile, path='', parent=None):
        if not hasattr(olefile, 'openstream'):
            from OleFileIO_PL import isOleFile
            if not isOleFile(olefile):
                from hwp5.errors import InvalidOleStorageError
                errormsg = 'Not an OLE2 Compound Binary File.'
                raise InvalidOleStorageError(errormsg)
            from OleFileIO_PL import OleFileIO
            olefile = OleFileIO(olefile)
        OleStorageItem.__init__(self, olefile, path, parent)

    def __iter__(self):
        return olefile_listdir(self.olefile, self.path)

    def __getitem__(self, name):
        if self.path == '' or self.path == '/':
            path = name
        else:
            path = self.path + '/' + name
        if not self.olefile.exists(path):
            raise KeyError('%s not found' % path)
        t = self.olefile.get_type(path)
        if t == 1:  # Storage
            return OleStorage(self.olefile, path, self)
        elif t == 2:  # Stream
            return OleStream(self.olefile, path, self)
        else:
            raise KeyError('%s is invalid' % path)

    def close(self):
        # if this is root, close underlying olefile
        if self.path == '':
            # old version of OleFileIO has no close()
            if hasattr(self.olefile, 'close'):
                self.olefile.close()


def olefile_listdir(olefile, path):
    if path == '' or path == '/':
        # we use a list instead of a set
        # for python 2.3 compatibility
        yielded = []

        for stream in olefile.listdir():
            top_item = stream[0]
            if top_item in yielded:
                continue
            yielded.append(top_item)
            yield top_item
        return

    if not olefile.exists(path):
        raise IOError('%s not exists' % path)
    if olefile.get_type(path) != 1:
        raise IOError('%s not a storage' % path)
    path_segments = path.split('/')
    for stream in olefile.listdir():
        if len(stream) == len(path_segments) + 1:
            if stream[:-1] == path_segments:
                yield stream[-1]

########NEW FILE########
__FILENAME__ = xmllint
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from __future__ import with_statement
import logging


logger = logging.getLogger(__name__)

executable = 'xmllint'
enabled = None


def xmllint_reachable():
    from subprocess import Popen
    args = [executable, '--version']
    try:
        p = Popen(args)
    except:
        return False
    else:
        p.wait()
        return True


def is_enabled():
    global enabled
    if enabled is None:
        enabled = xmllint_reachable()
    return enabled


def enable():
    global enabled
    enabled = True


def disable():
    global enabled
    enabled = False


def relaxng(rng_path, inp_path):
    from subprocess import Popen
    args = [executable, '--noout', '--relaxng', rng_path, inp_path]
    p = Popen(args)
    p.wait()
    return p.returncode == 0

########NEW FILE########
__FILENAME__ = xsltproc
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from __future__ import with_statement
import logging


logger = logging.getLogger(__name__)

executable = 'xsltproc'
enabled = None


def xslt_reachable():
    from subprocess import Popen
    args = [executable, '--version']
    try:
        p = Popen(args)
    except:
        return False
    else:
        p.wait()
        return True


def is_enabled():
    global enabled
    if enabled is None:
        enabled = xslt_reachable()
    return enabled


def enable():
    global enabled
    enabled = True


def disable():
    global enabled
    enabled = False


def xslt(xsl_path, inp_path, out_path):
    from subprocess import Popen
    args = [executable, '-o', out_path, xsl_path, inp_path]
    p = Popen(args)
    p.wait()
    if p.returncode == 0:
        return dict()
    else:
        return dict(errors=[])

########NEW FILE########
__FILENAME__ = _lxml
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from __future__ import with_statement
import logging


logger = logging.getLogger(__name__)


try:
    from lxml import etree
    etree
except ImportError:
    is_enabled = lambda: False
else:
    is_enabled = lambda: True


def xslt(xsl_path, inp_path, out_path):
    ''' Transform XML with XSL

    :param xsl_path: stylesheet path
    :param inp_path: input path
    :param out_path: output path
    '''
    transform = xslt_compile(xsl_path)
    return transform(inp_path, out_path)


def xslt_compile(xsl_path):
    ''' Compile XSL Transform function.
    :param xsl_path: stylesheet path
    :returns: a transform function
    '''
    from lxml import etree

    with file(xsl_path) as xsl_file:
        xsl_doc = etree.parse(xsl_file)

    xslt = etree.XSLT(xsl_doc)

    def transform(inp_path, out_path):
        ''' Transform XML with %r.

        :param inp_path: input path
        :param out_path: output path
        ''' % xsl_path
        with file(inp_path) as inp_file:
            with file(out_path, 'w') as out_file:
                from os.path import basename
                inp = etree.parse(inp_file)
                logger.info('_lxml.xslt(%s) start', basename(xsl_path))
                out = xslt(inp)
                logger.info('_lxml.xslt(%s) end', basename(xsl_path))
                out_file.write(str(out))
                return dict()
    return transform


def relaxng(rng_path, inp_path):
    validate = relaxng_compile(rng_path)
    return validate(inp_path)


def relaxng_compile(rng_path):
    ''' Compile RelaxNG file

    :param rng_path: RelaxNG path
    :returns: a validation function
    '''

    rng_file = file(rng_path)
    try:
        rng = etree.parse(rng_file)
    finally:
        rng_file.close()

    relaxng = etree.RelaxNG(rng)

    def validate(inp_path):
        ''' Validate XML against %r
        ''' % rng_path
        from os.path import basename
        with file(inp_path) as f:
            inp = etree.parse(f)
        logger.info('_lxml.relaxng(%s) start', basename(rng_path))
        try:
            valid = relaxng.validate(inp)
        except Exception, e:
            logger.exception(e)
            raise
        else:
            if not valid:
                for error in relaxng.error_log:
                    logger.error('%s', error)
            return valid
        finally:
            logger.info('_lxml.relaxng(%s) end', basename(rng_path))
    return validate


def errlog_to_dict(error):
    return dict(message=error.message,
                filename=error.filename,
                line=error.line,
                column=error.column,
                domain=error.domain_name,
                type=error.type_name,
                level=error.level_name)

########NEW FILE########
__FILENAME__ = adapters
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import uno
import unohelper
from com.sun.star.io import XInputStream, XSeekable, XOutputStream


class InputStreamFromFileLike(unohelper.Base, XInputStream, XSeekable):
    ''' Implementation of XInputStream, XSeekable based on a file-like object

    Implements com.sun.star.io.XInputStream and com.sun.star.io.XSeekable

    :param f: a file-like object
    '''
    def __init__(self, f, dontclose=False):
        self.f = f
        self.dontclose = dontclose

    def readBytes(self, aData, nBytesToRead):
        data = self.f.read(nBytesToRead)
        return len(data), uno.ByteSequence(data)

    readSomeBytes = readBytes

    def skipBytes(self, nBytesToSkip):
        self.f.read(nBytesToSkip)

    def available(self):
        return 0

    def closeInput(self):
        if not self.dontclose:
            self.f.close()

    def seek(self, location):
        self.f.seek(location)

    def getPosition(self):
        pos = self.f.tell()
        return pos

    def getLength(self):
        pos = self.f.tell()
        try:
            self.f.seek(0, 2)
            length = self.f.tell()
            return length
        finally:
            self.f.seek(pos)


class OutputStreamToFileLike(unohelper.Base, XOutputStream):
    ''' Implementation of XOutputStream based on a file-like object.

    Implements com.sun.star.io.XOutputStream.

    :param f: a file-like object
    '''
    def __init__(self, f, dontclose=False):
        self.f = f
        self.dontclose = dontclose

    def writeBytes(self, bytesequence):
        self.f.write(bytesequence.value)

    def flush(self):
        self.f.flush()

    def closeOutput(self):
        if not self.dontclose:
            self.f.close()


class FileFromStream(object):
    ''' A file-like object based on XInputStream/XOuputStream/XSeekable

    :param stream: a stream object which implements
    com.sun.star.io.XInputStream, com.sun.star.io.XOutputStream or
    com.sun.star.io.XSeekable
    '''
    def __init__(self, stream):
        self.stream = stream

        if hasattr(stream, 'readBytes'):
            def read(size=None):
                if size is None:
                    data = ''
                    while True:
                        bytes = uno.ByteSequence('')
                        n_read, bytes = stream.readBytes(bytes, 4096)
                        if n_read == 0:
                            return data
                        data += bytes.value
                bytes = uno.ByteSequence('')
                n_read, bytes = stream.readBytes(bytes, size)
                return bytes.value
            self.read = read

        if hasattr(stream, 'seek'):
            self.tell = stream.getPosition

            def seek(offset, whence=0):
                if whence == 0:
                    pass
                elif whence == 1:
                    offset += stream.getPosition()
                elif whence == 2:
                    offset += stream.getLength()
                stream.seek(offset)
            self.seek = seek

        if hasattr(stream, 'writeBytes'):
            def write(s):
                stream.writeBytes(uno.ByteSequence(s))
            self.write = write

            def flush():
                stream.flush()
            self.flush = flush

    def close(self):
        if hasattr(self.stream, 'closeInput'):
            self.stream.closeInput()
        elif hasattr(self.stream, 'closeOutput'):
            self.stream.closeOutput()

########NEW FILE########
__FILENAME__ = services
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


def create_service(context, name, *args):
    sm = context.ServiceManager
    if len(args) > 0:
        return sm.createInstanceWithArgumentsAndContext(name, args, context)
    else:
        return sm.createInstanceWithContext(name, context)


class Namespace(object):
    def __init__(self, dotted_name):
        self.dotted_name = dotted_name

    def __getattr__(self, name):
        return Namespace(self.dotted_name + '.' + name)

    def __call__(self, context, *args):
        return create_service(context, self.dotted_name, *args)

    def bind(self, context):
        return ContextBoundNamespace(self, context)


class ContextBoundNamespace(object):

    def __init__(self, namespace, context):
        self.namespace = namespace
        self.context = context

    def __getattr__(self, name):
        obj = getattr(self.namespace, name, None)
        if isinstance(obj, Namespace):
            return obj.bind(self.context)
        return obj

    def __call__(self, *args):
        return self.namespace(self.context, *args)

    def __iter__(self):
        context = self.context
        sm = context.ServiceManager
        prefix = self.dotted_name + '.'
        for name in sm.AvailableServiceNames:
            if name.startswith(prefix):
                basename = name[len(prefix):]
                if basename.find('.') == -1:
                    yield basename

css = Namespace('com.sun.star')

########NEW FILE########
__FILENAME__ = ucb
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


def open_url(context, url):
    ''' open InputStream from a URL.

    :param url: a URL to open an InputStream.
    :returns: an instance of InputStream
    '''

    # see http://wiki.openoffice.org
    #     /wiki/Documentation/DevGuide/UCB/Using_the_UCB_API

    from hwp5.plat._uno.services import css
    css = css.bind(context)
    ucb = css.ucb.UniversalContentBroker('Local', 'Office')
    content_id = ucb.createContentIdentifier(url)
    content = ucb.queryContent(content_id)

    import unohelper
    from com.sun.star.io import XActiveDataSink

    class DataSink(unohelper.Base, XActiveDataSink):
        def setInputStream(self, stream):
            self.stream = stream

        def getInputStream(self):
            return self.stream

    datasink = DataSink()

    from com.sun.star.ucb import Command, OpenCommandArgument2
    openargs = OpenCommandArgument2()
    openargs.Mode = 2  # OpenMode.DOCUMENT
    openargs.Priority = 32768
    openargs.Sink = datasink

    command = Command()
    command.Name = 'open'
    command.Handle = -1
    command.Argument = openargs

    content.execute(command, 0, None)
    return datasink.stream

########NEW FILE########
__FILENAME__ = cat
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
''' Extract out the specified stream in the <hwp5file> to the standard output.

Usage::

    hwp5proc cat [--loglevel=<loglevel>] [--logfile=<logfile>]
                 [--vstreams | --ole]
                 <hwp5file> <stream>
    hwp5proc cat --help

Options::

    -h --help               Show this screen
       --loglevel=<level>   Set log level.
       --logfile=<file>     Set log file.

       --vstreams           Process with virtual streams (i.e. parsed/converted
                            form of real streams)
       --ole                Treat <hwpfile> as an OLE Compound File. As a
                            result, some streams will be presented as-is. (i.e.
                            not decompressed)

Example::

    $ hwp5proc cat samples/sample-5017.hwp BinData/BIN0002.jpg | file -

    $ hwp5proc cat samples/sample-5017.hwp BinData/BIN0002.jpg > BIN0002.jpg

    $ hwp5proc cat samples/sample-5017.hwp PrvText | iconv -f utf-16le -t utf-8

    $ hwp5proc cat --vstreams samples/sample-5017.hwp PrvText.utf8

    $ hwp5proc cat --vstreams samples/sample-5017.hwp FileHeader.txt

    ccl: 0
    cert_drm: 0
    cert_encrypted: 0
    cert_signature_extra: 0
    cert_signed: 0
    compressed: 1
    distributable: 0
    drm: 0
    history: 0
    password: 0
    script: 0
    signature: HWP Document File
    version: 5.0.1.7
    xmltemplate_storage: 0

'''
from hwp5.proc import entrypoint


@entrypoint(__doc__)
def main(args):
    from hwp5.proc import open_hwpfile
    from hwp5.storage import open_storage_item
    import sys
    hwp5file = open_hwpfile(args)
    stream = open_storage_item(hwp5file, args['<stream>'])
    f = stream.open()
    try:
        while True:
            data = f.read(4096)
            if data:
                sys.stdout.write(data)
            else:
                return
    finally:
        if hasattr(f, 'close'):
            f.close()
        # Without this, last part of the output
        # can be truncated in Jython 2.5.3
        # See #141
        sys.stdout.close()

########NEW FILE########
__FILENAME__ = diststream
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
''' Decode distribute doc stream.

Usage::

    hwp5proc diststream
    hwp5proc diststream sha1 [--raw]
    hwp5proc diststream key [[--raw]
    hwp5proc diststream [--loglevel=<loglevel>] [--logfile=<logfile>]
    hwp5proc diststream --help

Options::

    -h --help               Show this screen
       --loglevel=<level>   Set log level.
       --logfile=<file>     Set log file.

Example::

    $ hwp5proc cat --ole samples/viewtext.hwp ViewText/Section0
      | tee Section0.zraw.aes128ecb | hwp5proc diststream | tee Section0.zraw
      | hwp5proc rawunz > Section0

    $ hwp5proc diststream sha1 < Section0.zraw.aes128ecb
    $ echo -n '12345' | sha1sum

'''
from binascii import b2a_hex
from binascii import a2b_hex
import logging

from hwp5.proc import entrypoint
from hwp5.distdoc import decode
from hwp5.distdoc import decode_head_to_sha1
from hwp5.distdoc import decode_head_to_key
from hwp5.recordstream import read_record


logger = logging.getLogger(__name__)


@entrypoint(__doc__)
def main(args):
    import sys
    import shutil

    if args['sha1']:
        head = read_record(sys.stdin, 0)
        sha1ucs16le = decode_head_to_sha1(head['payload'])
        sha1 = a2b_hex(sha1ucs16le.decode('utf-16le'))
        if not args['--raw']:
            sha1 = b2a_hex(sha1)
        sys.stdout.write(sha1)
    elif args['key']:
        head = read_record(sys.stdin, 0)
        key = decode_head_to_key(head['payload'])
        if not args['--raw']:
            key = b2a_hex(key)
        sys.stdout.write(key)
    else:
        result = decode(sys.stdin)
        shutil.copyfileobj(result, sys.stdout)

########NEW FILE########
__FILENAME__ = find
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
''' Find record models with specified predicates.

Usage::

    hwp5proc find [--model=<model-name> | --tag=<hwptag>]
                  [--incomplete] [--dump]
                  [--loglevel=<loglevel>] [--logfile=<logfile>]
                  <hwp5files>...
    hwp5proc find --help

Options::

    -h --help               Show this screen
       --loglevel=<level>   Set log level.
       --logfile=<file>     Set log file.

       --model=<model-name> filter with record model name
       --tag=<hwptag>       filter with record HWPTAG
       --incomplete         filter with incompletely parsed content
       --dump               dump record

    <hwp5files>...          HWPv5 files (*.hwp)

Example: Find paragraphs::

    $ hwp5proc find --model=Paragraph samples/*.hwp
    $ hwp5proc find --tag=HWPTAG_PARA_TEXT samples/*.hwp
    $ hwp5proc find --tag=66 samples/*.hwp

Example: Find and dump records of ``HWPTAG_LIST_HEADER`` which is parsed
incompletely::

    $ hwp5proc find --tag=HWPTAG_LIST_HEADER --incomplete --dump samples/*.hwp

'''
from hwp5.proc import entrypoint


@entrypoint(__doc__)
def main(args):
    filenames = args['<hwp5files>']
    from hwp5.dataio import ParseError
    from hwp5.binmodel import Hwp5File

    conditions = []
    if args['--model']:
        def with_model_name(model):
            return args['--model'] == model['type'].__name__
        conditions.append(with_model_name)

    if args['--tag']:
        tag = args['--tag']
        try:
            tag = int(tag)
        except ValueError:
            pass
        else:
            from hwp5.tagids import tagnames
            tag = tagnames[tag]

        def with_tag(model):
            return model['tagname'] == tag
        conditions.append(with_tag)

    if args['--incomplete']:
        def with_incomplete(model):
            return 'unparsed' in model
        conditions.append(with_incomplete)

    def flat_models(hwp5file, **kwargs):
        for model in hwp5file.docinfo.models(**kwargs):
            model['stream'] = 'DocInfo'
            yield model

        for section in hwp5file.bodytext:
            for model in hwp5file.bodytext[section].models(**kwargs):
                model['stream'] = 'BodyText/'+section
                yield model

    for filename in filenames:
        try:
            hwp5file = Hwp5File(filename)

            def with_filename(models):
                for model in models:
                    model['filename'] = filename
                    yield model

            models = flat_models(hwp5file)
            models = with_filename(models)

            for model in models:
                if all(condition(model) for condition in conditions):
                    print '%s:%s(%s): %s' % (model['filename'],
                                             model['stream'],
                                             model['seqno'],
                                             model['type'].__name__)
                    if args['--dump']:
                        from hwp5.binmodel import model_to_json
                        print model_to_json(model, sort_keys=True, indent=2)

                        def print_log(fmt, *args):
                            print fmt % args
                        from hwp5.bintype import log_events
                        list(log_events(model['binevents'], print_log))
        except ParseError, e:
            from hwp5.proc import logger
            logger.error('---- On processing %s:', filename)
            e.print_to_logger(logger)

########NEW FILE########
__FILENAME__ = header
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
''' Print HWP file header.

Usage::

    hwp5proc header [options] <hwp5file>
    hwp5proc header -h

Options::

    -h --help              Show this screen
       --loglevel=<level>  Set log level.
       --logfile=<file>    Set log file.

'''
from hwp5.proc import entrypoint


@entrypoint(__doc__)
def main(args):
    from hwp5.filestructure import Hwp5File
    hwp5file = Hwp5File(args['<hwp5file>'])
    f = hwp5file.header.open_text()
    try:
        try:
            for line in f:
                print line,
        finally:
            f.close()
    finally:
        hwp5file.close()

########NEW FILE########
__FILENAME__ = ls
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
''' List streams in the <hwp5file>.

Usage::

    hwp5proc ls [--loglevel=<loglevel>] [--logfile=<logfile>]
                [--vstreams | --ole]
                <hwp5file>
    hwp5proc ls --help

Options::

    -h --help               Show this screen
       --loglevel=<level>   Set log level.
       --logfile=<file>     Set log file.

       --vstreams           Process with virtual streams (i.e. parsed/converted
                            form of real streams)
       --ole                Treat <hwpfile> as an OLE Compound File. As a
                            result, some streams will be presented as-is. (i.e.
                            not decompressed)

Example: List without virtual streams::

    $ hwp5proc ls sample/sample-5017.hwp

    \\x05HwpSummaryInformation
    BinData/BIN0002.jpg
    BinData/BIN0002.png
    BinData/BIN0003.png
    BodyText/Section0
    DocInfo
    DocOptions/_LinkDoc
    FileHeader
    PrvImage
    PrvText
    Scripts/DefaultJScript
    Scripts/JScriptVersion

Example: List virtual streams too::

    $ hwp5proc ls --vstreams sample/sample-5017.hwp

    \\x05HwpSummaryInformation
    \\x05HwpSummaryInformation.txt
    BinData/BIN0002.jpg
    BinData/BIN0002.png
    BinData/BIN0003.png
    BodyText/Section0
    BodyText/Section0.models
    BodyText/Section0.records
    BodyText/Section0.xml
    BodyText.xml
    DocInfo
    DocInfo.models
    DocInfo.records
    DocInfo.xml
    DocOptions/_LinkDoc
    FileHeader
    FileHeader.txt
    PrvImage
    PrvText
    PrvText.utf8
    Scripts/DefaultJScript
    Scripts/JScriptVersion

'''
from hwp5.proc import entrypoint


@entrypoint(__doc__)
def main(args):
    from hwp5.storage import printstorage
    from hwp5.proc import open_hwpfile
    hwpfile = open_hwpfile(args)
    printstorage(hwpfile)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
''' Print parsed binary models in the specified <record-stream>.

Usage::

    hwp5proc models [--simple | --json]
                    [--treegroup=<treegroup>]
                    [--loglevel=<loglevel>] [--logfile=<logfile>]
                    <hwp5file> <record-stream>
    hwp5proc models [--simple | --json]
                    [--treegroup=<treegroup>]
                    [--loglevel=<loglevel>] [--logfile=<logfile>] -V <version>
    hwp5proc models --help

Options::

    -h --help               Show this screen
       --loglevel=<level>   Set log level.
       --logfile=<file>     Set log file.

       --simple             Print records as simple tree
       --json               Print records as json

       --treegroup=<treegroup>
                            Print records in the <treegroup>.
                            <treegroup> specifies the N-th subtree of the
                            record structure.

    -V <version>, --formatversion=<version>
                            Specifies HWPv5 format version

    <hwp5file>              HWPv5 files (*.hwp)
    <record-stream>         Record-structured internal streams.
                            (e.g. DocInfo, BodyText/*)

Example::

    $ hwp5proc models samples/sample-5017.hwp DocInfo
    $ hwp5proc models samples/sample-5017.hwp BodyText/Section0

    $ hwp5proc models samples/sample-5017.hwp docinfo
    $ hwp5proc models samples/sample-5017.hwp bodytext/0

Example::

    $ hwp5proc models --simple samples/sample-5017.hwp bodytext/0

Example::

    $ hwp5proc models --simple --treegroup=1 samples/sample-5017.hwp bodytext/0

If neither <hwp5file> nor <record-stream> is specified, the record stream is
read from the standard input with an assumption that the input is in the format
version specified by -V option.

Example::

    $ hwp5proc cat samples/sample-5017.hwp BodyText/Section0 > Section0.bin
    $ hwp5proc models -V 5.0.1.7 < Section0.bin

'''
from hwp5.proc import entrypoint


@entrypoint(__doc__)
def main(args):
    import sys
    filename = args['<hwp5file>']
    if filename:
        from hwp5.binmodel import Hwp5File
        from hwp5.proc import parse_recordstream_name
        streamname = args['<record-stream>']
        hwpfile = Hwp5File(filename)
        stream = parse_recordstream_name(hwpfile, streamname)
    else:
        version = args['--formatversion'] or '5.0.0.0'
        version = version.split('.')
        version = tuple(int(x) for x in version)

        from hwp5.storage import Open2Stream
        from hwp5.binmodel import ModelStream
        stream = ModelStream(Open2Stream(lambda: sys.stdin), version)

    opts = dict()

    treegroup = args['--treegroup']
    if treegroup is not None:
        opts['treegroup'] = int(treegroup)

    if args['--simple']:
        for model in stream.models(**opts):
            print '%04d' % model['seqno'],
            print ' '*model['level']+model['type'].__name__
    else:
        stream.models_json(**opts).dump(sys.stdout)

########NEW FILE########
__FILENAME__ = rawunz
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
''' Deflate an headerless zlib-compressed stream

Usage::

    hwp5proc rawunz [--loglevel=<loglevel>] [--logfile=<logfile>]
    hwp5proc rawunz --help

Options::

    -h --help               Show this screen
       --loglevel=<level>   Set log level.
       --logfile=<file>     Set log file.
'''
from hwp5.proc import entrypoint


@entrypoint(__doc__)
def main(args):
    import sys
    from hwp5.zlib_raw_codec import StreamReader
    stream = StreamReader(sys.stdin)
    while True:
        buf = stream.read(64)
        if len(buf) == 0:
            break
        sys.stdout.write(buf)

########NEW FILE########
__FILENAME__ = records
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
''' Print the record structure.

Usage::

    hwp5proc records [--simple | --json | --raw | --raw-header | --raw-payload]
                     [--treegroup=<treegroup> | --range=<range>]
                     [--loglevel=<loglevel>] [--logfile=<logfile>]
                     <hwp5file> <record-stream>
    hwp5proc records [--simple | --json | --raw | --raw-header | --raw-payload]
                     [--treegroup=<treegroup> | --range=<range>]
                     [--loglevel=<loglevel>] [--logfile=<logfile>]
    hwp5proc records --help

Options::

    -h --help               Show this screen
       --loglevel=<level>   Set log level.
       --logfile=<file>     Set log file.

       --simple             Print records as simple tree
       --json               Print records as json
       --raw                Print records as is
       --raw-header         Print record headers as is
       --raw-payload        Print record payloads as is

       --range=<range>      Print records specified in the <range>.
       --treegroup=<treegroup>
                            Print records specified in the <treegroup>.

    <hwp5file>              HWPv5 files (*.hwp)
    <record-stream>         Record-structured internal streams.
                            (e.g. DocInfo, BodyText/*)
    <range>                 Specifies the range of the records.
                             N-M means "from the record N to M-1 (excluding M)"
                             N means just the record N
    <treegroup>             Specifies the N-th subtree of the record structure.

Example::

    $ hwp5proc records samples/sample-5017.hwp DocInfo

Example::

    $ hwp5proc records samples/sample-5017.hwp DocInfo --range=0-2

If neither <hwp5file> nor <record-stream> is specified, the record stream is
read from the standard input with an assumption that the input is in the format
version specified by -V option.

Example::

    $ hwp5proc records --raw samples/sample-5017.hwp DocInfo --range=0-2 \
> tmp.rec
    $ hwp5proc records < tmp.rec

'''
from hwp5.proc import entrypoint


@entrypoint(__doc__)
def main(args):
    import sys
    filename = args['<hwp5file>']
    if filename:
        from hwp5.recordstream import Hwp5File
        from hwp5.proc import parse_recordstream_name
        hwpfile = Hwp5File(filename)
        streamname = args['<record-stream>']
        stream = parse_recordstream_name(hwpfile, streamname)
    else:
        from hwp5.storage import Open2Stream
        from hwp5.recordstream import RecordStream
        stream = RecordStream(Open2Stream(lambda: sys.stdin), None)

    opts = dict()
    rng = args['--range']
    if rng:
        rng = rng.split('-', 1)
        rng = tuple(int(x) for x in rng)
        opts['range'] = rng
    treegroup = args['--treegroup']
    if treegroup is not None:
        opts['treegroup'] = int(treegroup)

    if args['--simple']:
        for record in stream.records(**opts):
            print '%04d' % record['seqno'],
            print '  ' * record['level'], record['tagname']
    elif args['--raw']:
        from hwp5.recordstream import dump_record
        for record in stream.records(**opts):
            dump_record(sys.stdout, record)
    elif args['--raw-header']:
        from hwp5.recordstream import encode_record_header
        for record in stream.records(**opts):
            hdr = encode_record_header(record)
            sys.stdout.write(hdr)
    elif args['--raw-payload']:
        for record in stream.records(**opts):
            sys.stdout.write(record['payload'])
    else:
        stream.records_json(**opts).dump(sys.stdout)

########NEW FILE########
__FILENAME__ = summaryinfo
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
''' Print summary information of <hwp5file>.

Usage::

    hwp5proc summaryinfo [options] <hwp5file>
    hwp5proc summaryinfo --help

Options::

    -h --help              Show this screen
       --loglevel=<level>  Set log level.
       --logfile=<file>    Set log file.

'''

from hwp5.proc import entrypoint


@entrypoint(__doc__)
def main(args):
    from hwp5.filestructure import Hwp5File
    hwpfile = Hwp5File(args['<hwp5file>'])
    try:
        f = hwpfile.summaryinfo.open_text()
        try:
            for line in f:
                print line,
        finally:
            f.close()
    finally:
        hwpfile.close()

########NEW FILE########
__FILENAME__ = unpack
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
''' Extract out streams in the specified <hwp5file> to a directory.

Usage::

    hwp5proc unpack [--loglevel=<loglevel>] [--logfile=<logfile>]
                    [--vstreams | --ole]
                    <hwp5file> [<out-directory>]
    hwp5proc unpack --help

Options::

    -h --help               Show this screen
       --loglevel=<level>   Set log level.
       --logfile=<file>     Set log file.

       --vstreams           Process with virtual streams (i.e. parsed/converted
                            form of real streams)
       --ole                Treat <hwpfile> as an OLE Compound File. As a
                            result, some streams will be presented as-is. (i.e.
                            not decompressed)

Example::

    $ hwp5proc unpack samples/sample-5017.hwp
    $ ls sample-5017

Example::

    $ hwp5proc unpack --vstreams samples/sample-5017.hwp
    $ cat sample-5017/PrvText.utf8

'''
from hwp5.proc import entrypoint


@entrypoint(__doc__)
def main(args):
    from hwp5 import storage
    from hwp5.proc import open_hwpfile
    import os.path

    filename = args['<hwp5file>']
    hwp5file = open_hwpfile(args)

    outdir = args['<out-directory>']
    if outdir is None:
        outdir, ext = os.path.splitext(os.path.basename(filename))
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    storage.unpack(hwp5file, outdir)

########NEW FILE########
__FILENAME__ = version
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''Print HWP file format version of <hwp5file>.

Usage::

    hwp5proc version [options] <hwp5file>
    hwp5proc version --help

Options::

    -h --help              Show this screen
       --loglevel=<level>  Set log level.
       --logfile=<file>    Set log file.

'''
from hwp5.proc import entrypoint


@entrypoint(__doc__)
def main(args):
    from hwp5.filestructure import Hwp5File
    hwp5file = Hwp5File(args['<hwp5file>'])
    h = hwp5file.fileheader
    #print h.signature.replace('\x00', ''),
    print '%d.%d.%d.%d' % h.version

########NEW FILE########
__FILENAME__ = xml
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
''' Transform an HWPv5 file into an XML.

.. note::

   This command is experimental. Its output format is subject to change at any
   time.

Usage::

    hwp5proc xml [--embedbin]
                 [--no-xml-decl]
                 [--output=<file>]
                 [--loglevel=<loglevel>] [--logfile=<logfile>]
                 <hwp5file>
    hwp5proc xml --help

Options::

    -h --help               Show this screen
       --loglevel=<level>   Set log level.
       --logfile=<file>     Set log file.

       --embedbin           Embed BinData/* streams in the output XML.
       --no-xml-decl        Don't output <?xml ... ?> XML declaration.
       --output=<file>      Output filename.

    <hwp5file>              HWPv5 files (*.hwp)

Example::

    $ hwp5proc xml samples/sample-5017.hwp > sample-5017.xml
    $ xmllint --format sample-5017.xml

With ``--embedbin`` option, you can embed base64-encoded ``BinData/*`` files in
the output XML.

Example::

    $ hwp5proc xml --embedbin samples/sample-5017.hwp > sample-5017.xml
    $ xmllint --format sample-5017.xml

'''
from __future__ import with_statement
from hwp5.proc import entrypoint


@entrypoint(__doc__)
def main(args):
    ''' Transform <hwp5file> into an XML.
    '''
    import sys
    from hwp5.xmlmodel import Hwp5File

    opts = dict()
    opts['embedbin'] = args['--embedbin']

    if args['--output']:
        output = open(args['--output'], 'w')
    else:
        output = sys.stdout

    if args['--no-xml-decl']:
        xml_declaration = False
    else:
        xml_declaration = True

    with output:
        hwp5file = Hwp5File(args['<hwp5file>'])
        hwp5file.xmlevents(**opts).dump(output,
                                        xml_declaration=xml_declaration)

########NEW FILE########
__FILENAME__ = recordstream
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from .tagids import HWPTAG_BEGIN, tagnames
from .dataio import UINT32, Eof
from . import dataio
from . import filestructure
from .importhelper import importStringIO
from hwp5.importhelper import importjson
StringIO = importStringIO()


def tagname(tagid):
    return tagnames.get(tagid, 'HWPTAG%d' % (tagid - HWPTAG_BEGIN))


def Record(tagid, level, payload, size=None, seqno=None):
    if size is None:
        size = len(payload)
    d = dict(tagid=tagid, tagname=tagname(tagid), level=level,
             size=size, payload=payload)
    if seqno is not None:
        d['seqno'] = seqno
    return d


def decode_record_header(f):
    try:
        # TagID, Level, Size
        rechdr = UINT32.read(f)
        tagid = rechdr & 0x3ff
        level = (rechdr >> 10) & 0x3ff
        size = (rechdr >> 20) & 0xfff
        if size == 0xfff:
            size = UINT32.read(f)
        return (tagid, level, size)
    except Eof:
        return None


def encode_record_header(rec):
    import struct
    size = len(rec['payload'])
    level = rec['level']
    tagid = rec['tagid']
    if size < 0xfff:
        hdr = (size << 20) | (level << 10) | tagid
        return struct.pack('<I', hdr)
    else:
        hdr = (0xfff << 20) | (level << 10) | tagid
        return struct.pack('<II', hdr, size)


def read_record(f, seqno):
    header = decode_record_header(f)
    if header is None:
        return
    tagid, level, size = header
    payload = dataio.readn(f, size)
    return Record(tagid, level, payload, size, seqno)


def dump_record(f, record):
    hdr = encode_record_header(record)
    f.write(hdr)
    f.write(record['payload'])


def read_records(f):
    seqno = 0
    while True:
        record = read_record(f, seqno)
        if record:
            yield record
        else:
            return
        seqno += 1


def link_records(records):
    prev = None
    for rec in records:
        if prev is not None:
            if rec['level'] == prev['level']:
                rec['sister'] = prev
                rec['parent'] = prev.get('parent')
            elif rec['level'] == prev['level'] + 1:
                rec['parent'] = prev
        yield rec
        prev = rec


def record_to_json(record, *args, **kwargs):
    ''' convert a record to json '''
    from .dataio import dumpbytes
    json = importjson()
    record['payload'] = list(dumpbytes(record['payload']))
    return json.dumps(record, *args, **kwargs)


def nth(iterable, n, default=None):
    from itertools import islice
    try:
        return islice(iterable, n, None).next()
    except StopIteration:
        return default


def group_records_by_toplevel(records, group_as_list=True):
    ''' group records by top-level trees and return iterable of the groups
    '''
    context = dict()

    try:
        context['top'] = records.next()
    except StopIteration:
        return

    def records_in_a_tree():
        yield context.pop('top')

        for record in records:
            if record['level'] == 0:
                context['top'] = record
                return
            yield record

    while 'top' in context:
        group = records_in_a_tree()
        if group_as_list:
            group = list(group)
        yield group


class RecordStream(filestructure.VersionSensitiveItem):

    def records(self, **kwargs):
        records = read_records(self.open())
        if 'range' in kwargs:
            from itertools import islice
            range = kwargs['range']
            records = islice(records, range[0], range[1])
        elif 'treegroup' in kwargs:
            groups = group_records_by_toplevel(records, group_as_list=True)
            records = nth(groups, kwargs['treegroup'])
        return records

    def record(self, idx):
        ''' get the record at `idx' '''
        return nth(self.records(), idx)

    def records_json(self, **kwargs):
        from .utils import JsonObjects
        records = self.records(**kwargs)
        return JsonObjects(records, record_to_json)

    def records_treegrouped(self, group_as_list=True):
        ''' group records by top-level trees and return iterable of the groups
        '''
        records = self.records()
        return group_records_by_toplevel(records, group_as_list)

    def records_treegroup(self, n):
        ''' returns list of records in `n'th top-level tree '''
        groups = self.records_treegrouped()
        return nth(groups, n)

    def other_formats(self):
        return {'.records': self.records_json().open}


class Sections(filestructure.Sections):

    section_class = RecordStream


class Hwp5File(filestructure.Hwp5File):
    ''' Hwp5File for 'rec' layer
    '''

    docinfo_class = RecordStream
    bodytext_class = Sections

########NEW FILE########
__FILENAME__ = fs
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


class FileSystemStorage(object):
    ''' Directory-based stroage. '''

    def __init__(self, path):
        self.path = path

    def __iter__(self):
        import os
        return iter(sorted(os.listdir(self.path)))

    def __getitem__(self, name):
        import os.path
        path = os.path.join(self.path, name)
        if os.path.isdir(path):
            return FileSystemStorage(path)
        elif os.path.exists(path):
            return FileSystemStream(path)
        else:
            raise KeyError(name)


class FileSystemStream(object):
    ''' File-based stream. '''

    def __init__(self, path):
        self.path = path

    def open(self):
        return file(self.path, 'rb')

########NEW FILE########
__FILENAME__ = ole
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import logging


logger = logging.getLogger(__name__)


class OleStorage(object):

    def __init__(self, *args, **kwargs):
        from hwp5.plat import get_olestorage_class
        impl_class = get_olestorage_class()
        assert impl_class is not None, 'no OleStorage implementation available'
        self.impl = impl_class(*args, **kwargs)

    def __iter__(self):
        return self.impl.__iter__()

    def __getitem__(self, name):
        return self.impl.__getitem__(name)

    def __getattr__(self, name):
        return getattr(self.impl, name)

########NEW FILE########
__FILENAME__ = tagids
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
HWPTAG_BEGIN = 0x010
tagnames = {
    # DocInfo Records
    HWPTAG_BEGIN + 0: 'HWPTAG_DOCUMENT_PROPERTIES',
    HWPTAG_BEGIN + 1: 'HWPTAG_ID_MAPPINGS',
    HWPTAG_BEGIN + 2: 'HWPTAG_BIN_DATA',
    HWPTAG_BEGIN + 3: 'HWPTAG_FACE_NAME',
    HWPTAG_BEGIN + 4: 'HWPTAG_BORDER_FILL',
    HWPTAG_BEGIN + 5: 'HWPTAG_CHAR_SHAPE',
    HWPTAG_BEGIN + 6: 'HWPTAG_TAB_DEF',
    HWPTAG_BEGIN + 7: 'HWPTAG_NUMBERING',
    HWPTAG_BEGIN + 8: 'HWPTAG_BULLET',
    HWPTAG_BEGIN + 9: 'HWPTAG_PARA_SHAPE',
    HWPTAG_BEGIN + 10: 'HWPTAG_STYLE',
    HWPTAG_BEGIN + 11: 'HWPTAG_DOC_DATA',
    HWPTAG_BEGIN + 12: 'HWPTAG_DISTRIBUTE_DOC_DATA',
    # HWPTAG_BEGIN + 13: RESERVED,
    HWPTAG_BEGIN + 14: 'HWPTAG_COMPATIBLE_DOCUMENT',
    HWPTAG_BEGIN + 15: 'HWPTAG_LAYOUT_COMPATIBILITY',

    # Section Records
    HWPTAG_BEGIN + 50: 'HWPTAG_PARA_HEADER',
    HWPTAG_BEGIN + 51: 'HWPTAG_PARA_TEXT',
    HWPTAG_BEGIN + 52: 'HWPTAG_PARA_CHAR_SHAPE',
    HWPTAG_BEGIN + 53: 'HWPTAG_PARA_LINE_SEG',
    HWPTAG_BEGIN + 54: 'HWPTAG_PARA_RANGE_TAG',
    HWPTAG_BEGIN + 55: 'HWPTAG_CTRL_HEADER',
    HWPTAG_BEGIN + 56: 'HWPTAG_LIST_HEADER',
    HWPTAG_BEGIN + 57: 'HWPTAG_PAGE_DEF',
    HWPTAG_BEGIN + 58: 'HWPTAG_FOOTNOTE_SHAPE',
    HWPTAG_BEGIN + 59: 'HWPTAG_PAGE_BORDER_FILL',
    HWPTAG_BEGIN + 60: 'HWPTAG_SHAPE_COMPONENT',
    HWPTAG_BEGIN + 61: 'HWPTAG_TABLE',
    HWPTAG_BEGIN + 62: 'HWPTAG_SHAPE_COMPONENT_LINE',
    HWPTAG_BEGIN + 63: 'HWPTAG_SHAPE_COMPONENT_RECTANGLE',
    HWPTAG_BEGIN + 64: 'HWPTAG_SHAPE_COMPONENT_ELLIPSE',
    HWPTAG_BEGIN + 65: 'HWPTAG_SHAPE_COMPONENT_ARC',
    HWPTAG_BEGIN + 66: 'HWPTAG_SHAPE_COMPONENT_POLYGON',
    HWPTAG_BEGIN + 67: 'HWPTAG_SHAPE_COMPONENT_CURVE',
    HWPTAG_BEGIN + 68: 'HWPTAG_SHAPE_COMPONENT_OLE',
    HWPTAG_BEGIN + 69: 'HWPTAG_SHAPE_COMPONENT_PICTURE',
    HWPTAG_BEGIN + 70: 'HWPTAG_SHAPE_COMPONENT_CONTAINER',
    HWPTAG_BEGIN + 71: 'HWPTAG_CTRL_DATA',
    HWPTAG_BEGIN + 72: 'HWPTAG_CTRL_EQEDIT',
    # HWPTAG_BEGIN + 73: RESERVED
    HWPTAG_BEGIN + 74: 'HWPTAG_SHAPE_COMPONENT_TEXTART',
    # ...
    HWPTAG_BEGIN + 78: 'HWPTAG_FORBIDDEN_CHAR',
}
for k, v in tagnames.iteritems():
    globals()[v] = k
del k, v

########NEW FILE########
__FILENAME__ = treeop
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


class STARTEVENT:
    pass


class ENDEVENT:
    pass


def prefix_event(level_prefixed_items, root_item=None):
    ''' convert iterable of (level, item) into iterable of (event, item)
    '''
    baselevel = None
    stack = [root_item]
    for level, item in level_prefixed_items:
        if baselevel is None:
            baselevel = level
            level = 0
        else:
            level -= baselevel

        while level + 1 < len(stack):
            yield ENDEVENT, stack.pop()
        while len(stack) < level + 1:
            raise Exception('invalid level: %d, %d, %s' %
                            (level, len(stack) - 1, item))
        assert(len(stack) == level + 1)

        stack.append(item)
        yield STARTEVENT, item

    while 1 < len(stack):
        yield ENDEVENT, stack.pop()


def prefix_ancestors(event_prefixed_items, root_item=None):
    ''' convert iterable of (event, item) into iterable of (ancestors, item)
    '''
    stack = [root_item]
    for event, item in event_prefixed_items:
        if event is STARTEVENT:
            yield stack, item
            stack.append(item)
        elif event is ENDEVENT:
            stack.pop()


def prefix_ancestors_from_level(level_prefixed_items, root_item=None):
    ''' convert iterable of (level, item) into iterable of (ancestors, item)

        @param level_prefixed items: iterable of tuple(level, item)
        @return iterable of tuple(ancestors, item)
    '''
    baselevel = None
    stack = [root_item]
    for level, item in level_prefixed_items:
        if baselevel is None:
            baselevel = level
            level = 0
        else:
            level -= baselevel

        while level + 1 < len(stack):
            stack.pop()
        while len(stack) < level + 1:
            raise Exception('invalid level: %d, %d, %s' %
                            (level, len(stack) - 1, item))
        assert(len(stack) == level + 1)

        yield stack, item
        stack.append(item)


def build_subtree(event_prefixed_items):
    ''' build a tree from (event, item) stream

        Example Scenario::

           ...
           (STARTEVENT, rootitem)          # should be consumed by the caller
           --- call build_subtree() ---
           (STARTEVENT, child1)            # consumed by build_subtree()
           (STARTEVENT, grandchild)        # (same)
           (ENDEVENT, grandchild)          # (same)
           (ENDEVENT, child1)              # (same)
           (STARTEVENT, child2)            # (same)
           (ENDEVENT, child2)              # (same)
           (ENDEVENT, rootitem)            # same, buildsubtree() returns
           --- build_subtree() returns ---
           (STARTEVENT, another_root)
           ...

        result will be (rootitem, [(child1, [(grandchild, [])]),
                                   (child2, [])])

    '''
    childs = []
    for event, item in event_prefixed_items:
        if event == STARTEVENT:
            childs.append(build_subtree(event_prefixed_items))
        elif event == ENDEVENT:
            return item, childs


def iter_subevents(event_prefixed_items):
    level = 0
    for event, item in event_prefixed_items:
        yield event, item
        if event is STARTEVENT:
            level += 1
        elif event is ENDEVENT:
            if level > 0:
                level -= 1
            else:
                return


def tree_events(rootitem, childs):
    ''' generate tuples of (event, item) from a tree
    '''
    yield STARTEVENT, rootitem
    for k in tree_events_multi(childs):
        yield k
    yield ENDEVENT, rootitem


def tree_events_multi(trees):
    ''' generate tuples of (event, item) from trees
    '''
    for rootitem, childs in trees:
        for k in tree_events(rootitem, childs):
            yield k

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


class NIL:
    pass


class cached_property(object):

    def __init__(self, func):
        self.func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, NIL)
        if value is NIL:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value

    def __set__(self, obj, value):
        obj.__dict__[self.__name__] = value


def generate_json_array(tokens):
    ''' generate json array with given tokens '''
    first = True
    for token in tokens:
        if first:
            yield '[\n'
            first = False
        else:
            yield ',\n'
        yield token
    yield '\n]'


class JsonObjects(object):

    def __init__(self, objects, object_to_json):
        self.objects = objects
        self.object_to_json = object_to_json

    def generate(self, **kwargs):
        kwargs.setdefault('sort_keys', True)
        kwargs.setdefault('indent', 2)

        tokens = (self.object_to_json(obj, **kwargs)
                  for obj in self.objects)
        return generate_json_array(tokens)

    def open(self, **kwargs):
        from .filestructure import GeneratorReader
        return GeneratorReader(self.generate(**kwargs))

    def dump(self, outfile, **kwargs):
        for s in self.generate(**kwargs):
            outfile.write(s)

########NEW FILE########
__FILENAME__ = xmlformat
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from itertools import chain
from hwp5.filestructure import VERSION
from hwp5.dataio import typed_struct_attributes
from hwp5.dataio import Struct
from hwp5.dataio import ArrayType
from hwp5.dataio import FlagsType
from hwp5.dataio import EnumType
from hwp5.dataio import WCHAR
from hwp5.dataio import HWPUNIT
from hwp5.dataio import HWPUNIT16
from hwp5.dataio import SHWPUNIT
from hwp5.binmodel import COLORREF
from hwp5.binmodel import BinStorageId
from hwp5.binmodel import Margin
from hwp5.binmodel import Text
from hwp5.treeop import STARTEVENT
from hwp5.treeop import ENDEVENT
import logging
logger = logging.getLogger(__name__)


def xmlattrval(value):
    if isinstance(value, basestring):
        return value
    elif isinstance(type(value), EnumType):
        return type(value)(value).name.lower()
    elif isinstance(value, type):
        return value.__name__
    else:
        return str(value)


def expanded_xmlattribute((name, (t, value))):
    if isinstance(t, FlagsType):
        fmt = '%0'
        fmt += '%d' % (t.basetype.fixed_size * 2)
        fmt += 'X'
        yield name, fmt % int(value)
        for k, v in t.dictvalue(t(value)).iteritems():
            yield k, xmlattrval(v)
    elif t is Margin:
        for pos in ('left', 'right', 'top', 'bottom'):
            yield '-'.join([name, pos]), xmlattrval(value.get(pos))
    elif t is COLORREF:
        yield name, xmlattrval(t(value))
    elif t is VERSION:
        yield name, '.'.join(str(x) for x in value)
    elif t in (HWPUNIT, SHWPUNIT, HWPUNIT16):
        yield name, str(value)
    elif t is WCHAR:
        if value == 0:
            yield name, u''
        else:
            yield name, unichr(value)
    elif t is BinStorageId:
        yield name, 'BIN%04X' % value
    else:
        yield name, xmlattrval(value)


def xmlattr_dashednames(attrs):
    for k, v in attrs:
        yield k.replace('_', '-'), v


def xmlattr_uniqnames(attrs):
    names = set([])
    for k, v in attrs:
        assert not k in names, 'name clashes: %s' % k
        yield k, v
        names.add(k)


def xmlattributes_for_plainvalues(context, plainvalues):
    ntvs = plainvalues.iteritems()
    ntvs = chain(*(expanded_xmlattribute(ntv) for ntv in ntvs))
    return dict(xmlattr_uniqnames(xmlattr_dashednames(ntvs)))


def is_complex_type(type, value):
    if isinstance(value, dict):
        return True
    elif isinstance(type, ArrayType) and issubclass(type.itemtype, Struct):
        return True
    else:
        return False


def separate_plainvalues(typed_attributes):
    d = []
    p = dict()
    for named_item in typed_attributes:
        name, item = named_item
        t, value = item
        try:
            if t is Margin:
                p[name] = item
            elif is_complex_type(t, value):
                d.append(named_item)
            else:
                p[name] = item
        except Exception, e:
            logger.error('%s', (name, t, value))
            logger.error('%s', t.__dict__)
            logger.exception(e)
            raise e
    return d, p


def startelement(context, (model, attributes)):
    from hwp5.dataio import StructType
    if isinstance(model, StructType):
        typed_attributes = ((v['name'], (v['type'], v['value']))
                            for v in typed_struct_attributes(model, attributes,
                                                             context))
    else:
        typed_attributes = ((k, (type(v), v))
                            for k, v in attributes.iteritems())

    typed_attributes, plainvalues = separate_plainvalues(typed_attributes)

    if model is Text:
        text = plainvalues.pop('text')[1]
    elif '<text>' in plainvalues:
        text = plainvalues.pop('<text>')[1]
    else:
        text = None

    yield STARTEVENT, (model.__name__,
                       xmlattributes_for_plainvalues(context, plainvalues))
    if text:
        yield Text, text

    for _name, (_type, _value) in typed_attributes:
        if isinstance(_value, dict):
            assert isinstance(_value, dict)
            _value = dict(_value)
            _value['attribute-name'] = _name
            for x in element(context, (_type, _value)):
                yield x
        else:
            assert isinstance(_value, (tuple, list)), (_value, _type)
            assert issubclass(_type.itemtype, Struct), (_value, _type)
            yield STARTEVENT, ('Array', {'name': _name})
            for _itemvalue in _value:
                for x in element(context, (_type.itemtype, _itemvalue)):
                    yield x
            yield ENDEVENT, 'Array'


def element(context, (model, attributes)):
    for x in startelement(context, (model, attributes)):
        yield x
    yield ENDEVENT, model.__name__


def xmlevents_to_bytechunks(xmlevents, encoding='utf-8'):
    from xml.sax.saxutils import escape
    from xml.sax.saxutils import quoteattr
    entities = {'\r': '&#13;',
                '\n': '&#10;',
                '\t': '&#9;'}
    for event, item in xmlevents:
        if event is STARTEVENT:
            yield '<'
            yield item[0]
            for n, v in item[1].items():
                yield ' '
                yield n
                yield '='
                v = quoteattr(v, entities)
                if isinstance(v, unicode):
                    v = v.encode(encoding)
                yield v
            yield '>'
        elif event is Text:
            text = escape(item)
            if isinstance(text, unicode):
                text = text.encode(encoding)
            yield text
        elif event is ENDEVENT:
            yield '</'
            yield item
            yield '>'

########NEW FILE########
__FILENAME__ = xmlmodel
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from tempfile import TemporaryFile

from .treeop import STARTEVENT, ENDEVENT
from .treeop import build_subtree
from .treeop import tree_events, tree_events_multi
from .binmodel import SectionDef
from .binmodel import ListHeader
from .binmodel import Paragraph
from .binmodel import Text
from .binmodel import TableControl, GShapeObjectControl, ShapeComponent
from .binmodel import TableBody, TableCell
from .dataio import Struct
from .filestructure import VERSION
from . import binmodel

import logging
logger = logging.getLogger(__name__)


def give_elements_unique_id(event_prefixed_mac):
    paragraph_id = 0
    table_id = 0
    gshape_id = 0
    shape_id = 0
    for event, item in event_prefixed_mac:
        (model, attributes, context) = item
        if event == STARTEVENT:
            if model == Paragraph:
                attributes['paragraph_id'] = paragraph_id
                paragraph_id += 1
            elif model == TableControl:
                attributes['table_id'] = table_id
                table_id += 1
            elif model == GShapeObjectControl:
                attributes['gshape_id'] = gshape_id
                gshape_id += 1
            elif model == ShapeComponent:
                attributes['shape_id'] = shape_id
                shape_id += 1
        yield event, item


def make_ranged_shapes(shapes):
    last = None
    for item in shapes:
        if last is not None:
            yield (last[0], item[0]), last[1]
        last = item
    yield (item[0], 0x7fffffff), item[1]


def split_and_shape(chunks, ranged_shapes):
    (chunk_start, chunk_end), chunk_attr, chunk = chunks.next()
    for (shape_start, shape_end), shape in ranged_shapes:
        while True:
            # case 0: chunk has left intersection
            #        vvvv
            #      ----...
            if chunk_start < shape_start:
                assert False

            # case 1: chunk is far right: get next shape
            #         vvvv
            #             ----
            if shape_end <= chunk_start:        # (1)
                break

            assert chunk_start < shape_end      # by (1)
            assert shape_start <= chunk_start
            # case 2: chunk has left intersection
            #         vvvv
            #         ..----
            if shape_end < chunk_end:           # (2)
                prev = ((chunk_start, shape_end),
                        chunk[:shape_end - chunk_start])
                next = ((shape_end, chunk_end),
                        chunk[shape_end - chunk_start:])
                (chunk_start, chunk_end), chunk = prev
            else:
                next = None

            assert chunk_end <= shape_end       # by (2)
            yield (chunk_start, chunk_end), (shape, chunk_attr), chunk

            if next is not None:
                (chunk_start, chunk_end), chunk = next
                continue

            (chunk_start, chunk_end), chunk_attr, chunk = chunks.next()


def line_segmented(chunks, ranged_linesegs):
    prev_lineseg = None
    line = None
    for ((chunk_start, chunk_end),
         (lineseg, chunk_attr),
         chunk) in split_and_shape(chunks, ranged_linesegs):
        if lineseg is not prev_lineseg:
            if line is not None:
                yield prev_lineseg, line
            line = []
        line.append(((chunk_start, chunk_end), chunk_attr, chunk))
        prev_lineseg = lineseg
    if line is not None:
        yield prev_lineseg, line


def make_texts_linesegmented_and_charshaped(event_prefixed_mac):
    ''' lineseg/charshaped text chunks '''
    from .binmodel import ParaText, ParaLineSeg, ParaCharShape

    stack = []  # stack of ancestor Paragraphs
    for event, item in event_prefixed_mac:
        model, attributes, context = item
        if model is Paragraph:
            if event == STARTEVENT:
                stack.append(dict())
                yield STARTEVENT, item
            else:
                paratext = stack[-1].get(ParaText)
                paracharshape = stack[-1].get(ParaCharShape)
                paralineseg = stack[-1].get(ParaLineSeg)
                if paratext is None:
                    paratext = (ParaText,
                                dict(chunks=[((0, 0), '')]),
                                dict(context))
                for x in merge_paragraph_text_charshape_lineseg(paratext,
                                                                paracharshape,
                                                                paralineseg):
                    yield x

                yield ENDEVENT, (model, attributes, context)
                stack.pop()
        #elif model in (ParaText, ParaCharShape):
        elif model in (ParaText, ParaCharShape, ParaLineSeg):
            if event == STARTEVENT:
                stack[-1][model] = model, attributes, context
        else:
            yield event, (model, attributes, context)


def merge_paragraph_text_charshape_lineseg(paratext, paracharshape,
                                           paralineseg):
    from .binmodel import LineSeg

    paratext_model, paratext_attributes, paratext_context = paratext

    chunks = ((range, None, chunk)
              for range, chunk in paratext_attributes['chunks'])
    charshapes = paracharshape[1]['charshapes']
    shaped_chunks = split_and_shape(chunks, make_ranged_shapes(charshapes))

    if paralineseg:
        paralineseg_content = paralineseg[1]
        paralineseg_context = paralineseg[2]
    else:
        # 배포용 문서의 더미 BodyText 에는 LineSeg 정보가 없음
        # (see https://github.com/mete0r/pyhwp/issues/33)
        # 더미 LineSeg를 만들어 준다
        lineseg = dict(chpos=0, y=0, height=0, height2=0, height85=0,
                       space_below=0, x=0, width=0, a8=0, flags=0)
        paralineseg_content = dict(linesegs=[lineseg])
        paralineseg_context = dict()
    linesegs = ((lineseg['chpos'], lineseg)
                for lineseg in paralineseg_content['linesegs'])
    lined_shaped_chunks = line_segmented(shaped_chunks,
                                         make_ranged_shapes(linesegs))
    for lineseg_content, shaped_chunks in lined_shaped_chunks:
        lineseg = (LineSeg, lineseg_content, paralineseg_context)
        chunk_events = range_shaped_textchunk_events(paratext_context,
                                                     shaped_chunks)
        for x in wrap_modelevents(lineseg, chunk_events):
            yield x


def range_shaped_textchunk_events(paratext_context, range_shaped_textchunks):
    from .binmodel import ControlChar
    for (startpos, endpos), (shape, none), chunk in range_shaped_textchunks:
        if isinstance(chunk, basestring):
            textitem = (Text,
                        dict(text=chunk, charshape_id=shape),
                        paratext_context)
            yield STARTEVENT, textitem
            yield ENDEVENT, textitem
        elif isinstance(chunk, dict):
            code = chunk['code']
            uch = unichr(code)
            name = ControlChar.get_name_by_code(code)
            kind = ControlChar.kinds[uch]
            chunk_attributes = dict(name=name,
                                    code=code,
                                    kind=kind,
                                    charshape_id=shape)
            if code in (0x9, 0xa, 0xd):  # http://www.w3.org/TR/xml/#NT-Char
                chunk_attributes['char'] = uch
            ctrlch = (ControlChar, chunk_attributes, paratext_context)
            yield STARTEVENT, ctrlch
            yield ENDEVENT, ctrlch


def wrap_section(event_prefixed_mac, sect_id=None):
    ''' wrap a section with SectionDef '''
    starting_buffer = list()
    started = False
    sectiondef = None
    for event, item in event_prefixed_mac:
        if started:
            yield event, item
        else:
            model, attributes, context = item
            if model is SectionDef and event is STARTEVENT:
                sectiondef, sectdef_child = build_subtree(event_prefixed_mac)
                if sect_id is not None:
                    attributes['section_id'] = sect_id
                yield STARTEVENT, sectiondef
                for k in tree_events_multi(sectdef_child):
                    yield k
                for evented_item in starting_buffer:
                    yield evented_item
                started = True
            else:
                starting_buffer.append((event, item))
    yield ENDEVENT, sectiondef


def make_extended_controls_inline(event_prefixed_mac, stack=None):
    ''' inline extended-controls into paragraph texts '''
    from .binmodel import ControlChar, Control
    if stack is None:
        stack = []  # stack of ancestor Paragraphs
    for event, item in event_prefixed_mac:
        model, attributes, context = item
        if model is Paragraph:
            if event == STARTEVENT:
                stack.append(dict())
                yield STARTEVENT, item
            else:
                yield ENDEVENT, item
                stack.pop()
        elif model is ControlChar:
            if event is STARTEVENT:
                if attributes['kind'] is ControlChar.EXTENDED:
                    control_subtree = stack[-1].get(Control).pop(0)
                    tev = tree_events(*control_subtree)
                    yield tev.next()  # to evade the Control/STARTEVENT trigger
                                      # in parse_models_pass3()
                    for k in make_extended_controls_inline(tev, stack):
                        yield k
                else:
                    yield STARTEVENT, item
                    yield ENDEVENT, item
        elif issubclass(model, Control) and event == STARTEVENT:
            control_subtree = build_subtree(event_prefixed_mac)
            stack[-1].setdefault(Control, []).append(control_subtree)
        else:
            yield event, item


def make_paragraphs_children_of_listheader(event_prefixed_mac,
                                           parentmodel=ListHeader,
                                           childmodel=Paragraph):
    ''' make paragraphs children of the listheader '''
    stack = []
    level = 0
    for event, item in event_prefixed_mac:
        model, attributes, context = item
        if event is STARTEVENT:
            level += 1
        if len(stack) > 0 and ((event is STARTEVENT
                                and stack[-1][0] == level
                                and model is not childmodel) or
                               (event is ENDEVENT
                                and stack[-1][0] - 1 == level)):
            lh_level, lh_item = stack.pop()
            yield ENDEVENT, lh_item

        if issubclass(model, parentmodel):
            if event is STARTEVENT:
                stack.append((level, item))
                yield event, item
            else:
                pass
        else:
            yield event, item

        if event is ENDEVENT:
            level -= 1


def match_field_start_end(event_prefixed_mac):
    from .binmodel import Field, ControlChar
    stack = []
    for event, item in event_prefixed_mac:
        (model, attributes, context) = item
        if issubclass(model, Field):
            if event is STARTEVENT:
                stack.append(item)
                yield event, item
            else:
                pass
        elif model is ControlChar and attributes['name'] == 'FIELD_END':
            if event is ENDEVENT:
                if len(stack) > 0:
                    yield event, stack.pop()
                else:
                    logger.warning('unmatched field end')
        else:
            yield event, item


class TableRow:
    pass


def restructure_tablebody(event_prefixed_mac):
    ROW_OPEN = 1
    ROW_CLOSE = 2

    from collections import deque
    stack = []
    for event, item in event_prefixed_mac:
        (model, attributes, context) = item
        if model is TableBody:
            if event is STARTEVENT:
                rowcols = deque()
                for cols in attributes.pop('rowcols'):
                    if cols == 1:
                        rowcols.append(ROW_OPEN | ROW_CLOSE)
                    else:
                        rowcols.append(ROW_OPEN)
                        for i in range(0, cols - 2):
                            rowcols.append(0)
                        rowcols.append(ROW_CLOSE)
                stack.append((context, rowcols))
                yield event, item
            else:
                yield event, item
                stack.pop()
        elif model is TableCell:
            table_context, rowcols = stack[-1]
            row_context = dict(table_context)
            if event is STARTEVENT:
                how = rowcols[0]
                if how & ROW_OPEN:
                    yield STARTEVENT, (TableRow, dict(), row_context)
            yield event, item
            if event is ENDEVENT:
                how = rowcols.popleft()
                if how & ROW_CLOSE:
                    yield ENDEVENT, (TableRow, dict(), row_context)
        else:
            yield event, item


def embed_bindata(event_prefixed_mac, bindata):
    from hwp5.binmodel import BinData
    import base64
    for event, item in event_prefixed_mac:
        (model, attributes, context) = item
        if event is STARTEVENT and model is BinData:
            if attributes['flags'].storage is BinData.StorageType.EMBEDDING:
                name = ('BIN%04X' % attributes['bindata']['storage_id']
                        + '.'
                        + attributes['bindata']['ext'])
                bin_stream = bindata[name].open()
                try:
                    binary = bin_stream.read()
                finally:
                    bin_stream.close()
                b64 = base64.b64encode(binary)
                attributes['bindata']['<text>'] = b64
                attributes['bindata']['inline'] = 'true'
        yield event, item


def prefix_binmodels_with_event(context, models):
    from .treeop import prefix_event
    level_prefixed = ((model['level'],
                       (model['type'], model['content'], context))
                      for model in models)
    return prefix_event(level_prefixed)


def wrap_modelevents(wrapper_model, modelevents):
    from .treeop import STARTEVENT, ENDEVENT
    yield STARTEVENT, wrapper_model
    for mev in modelevents:
        yield mev
    yield ENDEVENT, wrapper_model


def modelevents_to_xmlevents(modelevents):
    from hwp5.xmlformat import startelement
    for event, (model, attributes, context) in modelevents:
        if event is STARTEVENT:
            for x in startelement(context, (model, attributes)):
                yield x
        elif event is ENDEVENT:
            yield ENDEVENT, model.__name__


class XmlEvents(object):

    def __init__(self, events):
        self.events = events

    def __iter__(self):
        return modelevents_to_xmlevents(self.events)

    def bytechunks(self, xml_declaration=True, **kwargs):
        from hwp5.xmlformat import xmlevents_to_bytechunks
        encoding = kwargs.get('xml_encoding', 'utf-8')
        if xml_declaration:
            yield '<?xml version="1.0" encoding="%s"?>\n' % encoding
        bytechunks = xmlevents_to_bytechunks(self, encoding)
        for chunk in bytechunks:
            yield chunk

    def dump(self, outfile, **kwargs):
        bytechunks = self.bytechunks(**kwargs)
        for chunk in bytechunks:
            outfile.write(chunk)
        if hasattr(outfile, 'flush'):
            outfile.flush()

    def open(self, **kwargs):
        tmpfile = TemporaryFile()
        try:
            self.dump(tmpfile, **kwargs)
        except:
            tmpfile.close()
            raise

        tmpfile.seek(0)
        return tmpfile


class XmlEventsMixin(object):

    def xmlevents(self, **kwargs):
        return XmlEvents(self.events(**kwargs))


class ModelEventStream(binmodel.ModelStream, XmlEventsMixin):

    def modelevents(self, **kwargs):
        models = self.models(**kwargs)

        # prepare modelevents context
        kwargs.setdefault('version', self.version)
        return prefix_binmodels_with_event(kwargs, models)

    def other_formats(self):
        d = super(ModelEventStream, self).other_formats()
        d['.xml'] = self.xmlevents().open
        return d


class DocInfo(ModelEventStream):

    def events(self, **kwargs):
        docinfo = DocInfo, dict(), dict()
        events = self.modelevents(**kwargs)
        if 'embedbin' in kwargs:
            events = embed_bindata(events, kwargs['embedbin'])
        events = wrap_modelevents(docinfo, events)
        return events


class Section(ModelEventStream):

    def events(self, **kwargs):
        events = self.modelevents(**kwargs)

        events = make_texts_linesegmented_and_charshaped(events)
        events = make_extended_controls_inline(events)
        events = match_field_start_end(events)
        events = make_paragraphs_children_of_listheader(events)
        events = make_paragraphs_children_of_listheader(events, TableBody,
                                                        TableCell)
        events = restructure_tablebody(events)

        section_idx = kwargs.get('section_idx')
        events = wrap_section(events, section_idx)

        return events


class Sections(binmodel.Sections, XmlEventsMixin):

    section_class = Section

    def events(self, **kwargs):
        bodytext_events = []
        for idx in self.section_indexes():
            kwargs['section_idx'] = idx
            section = self.section(idx)
            events = section.events(**kwargs)
            bodytext_events.append(events)

        class BodyText(object):
            pass
        from itertools import chain
        bodytext_events = chain(*bodytext_events)
        bodytext = BodyText, dict(), dict()
        return wrap_modelevents(bodytext, bodytext_events)

    def other_formats(self):
        d = super(Sections, self).other_formats()
        d['.xml'] = self.xmlevents().open
        return d


class HwpDoc(Struct):

    def attributes():
        yield VERSION, 'version'
    attributes = staticmethod(attributes)


class Hwp5File(binmodel.Hwp5File, XmlEventsMixin):

    docinfo_class = DocInfo
    bodytext_class = Sections

    def events(self, **kwargs):
        from itertools import chain
        if 'embedbin' in kwargs and kwargs['embedbin'] and 'BinData' in self:
            kwargs['embedbin'] = self['BinData']
        else:
            kwargs.pop('embedbin', None)

        events = chain(self.docinfo.events(**kwargs),
                       self.text.events(**kwargs))

        hwpdoc = HwpDoc, dict(version=self.header.version), dict()
        events = wrap_modelevents(hwpdoc, events)

        # for easy references in styles
        events = give_elements_unique_id(events)

        return events

########NEW FILE########
__FILENAME__ = zlib_raw_codec
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010-2014 mete0r <mete0r@sarangbang.or.kr>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import codecs
import zlib  # this codec needs the optional zlib module !

_wbits = -15


def zlib_raw_encode(input, errors='strict'):
    assert errors == 'strict'
    output = zlib.compress(input)[2:-4]
    return (output, len(input))


def zlib_raw_decode(input, errors='strict'):
    assert errors == 'strict'
    output = zlib.decompress(input, _wbits)
    return (output, len(input))


class Codec(codecs.Codec):

    def encode(self, input, errors='strict'):
        return zlib_raw_encode(input, errors)

    def decode(self, input, errors='strict'):
        return zlib_raw_decode(input, errors)


class IncrementalEncoder(codecs.IncrementalEncoder):
    def __init__(self, errors='strict'):
        assert errors == 'strict'
        self.errors = errors
        self.compressobj = zlib.compressobj()
        self.initial = True

    def encode(self, input, final=False):
        c = self.compressobj.compress(input)
        if self.initial:
            c = c[2:]
            self.initial = False
        if final:
            c += self.compressobj.flush()[:-4]
        return c

    def reset(self):
        self.compressobj = zlib.compressobj()


class IncrementalDecoder(codecs.IncrementalDecoder):
    def __init__(self, errors='strict'):
        assert errors == 'strict'
        self.errors = errors
        self.decompressobj = zlib.decompressobj(_wbits)

    def decode(self, input, final=False):
        if final:
            if len(input) > 0:
                d = self.decompressobj.decompress(input)
            else:
                d = ''
            return d + self.decompressobj.flush()
        else:
            return self.decompressobj.decompress(input)

    def reset(self):
        self.decompressobj = zlib.decompressobj(_wbits)


class StreamWriter(object):
    def __init__(self, stream, errors='strict'):
        assert errors == 'strict'
        self.stream = stream
        self.encoder = IncrementalEncoder(errors)

    def write(self, data):
        raise NotImplementedError


class StreamReader(object):
    def __init__(self, stream, errors='strict'):
        assert errors == 'strict'
        self.stream = stream
        self.decoder = IncrementalDecoder(errors)
        self.buffer = ''
        self.offset = 0

    def read(self, size=-1):
        if size < 0:
            c = self.stream.read()
            d = self.buffer + self.decoder.decode(c, True)
            self.buffer = ''
            self.offset += len(d)
            return d

        final = False
        while True:
            if size <= len(self.buffer):
                d = self.buffer[:size]
                self.buffer = self.buffer[size:]
                self.offset += size
                return d

            if final:
                d = self.buffer
                self.buffer = ''
                self.offset += len(d)
                return d

            c = self.stream.read(8196)
            final = len(c) < 8196 or len(c)
            self.buffer += self.decoder.decode(c, final)

    def tell(self):
        return self.offset


_codecinfo = codecs.CodecInfo(
    name='zlib_raw',
    encode=zlib_raw_encode,
    decode=zlib_raw_decode,
    incrementalencoder=IncrementalEncoder,
    incrementaldecoder=IncrementalDecoder,
    streamreader=StreamReader,
    streamwriter=StreamWriter,
)

########NEW FILE########
__FILENAME__ = mixin_olestg
# -*- coding: utf-8 -*-
import logging


logger = logging.getLogger(__name__)


class OleStorageTestMixin(object):

    hwp5file_name = 'sample-5017.hwp'
    OleStorage = None

    def get_fixture_file(self, filename):
        from fixtures import get_fixture_path
        return get_fixture_path(filename)

    @property
    def hwp5file_path(self):
        return self.get_fixture_file(self.hwp5file_name)

    @property
    def olestg(self):
        return self.OleStorage(self.hwp5file_path)

    def test_OleStorage(self):
        if self.OleStorage is None:
            logger.warning('%s: skipped', self.id())
            return
        OleStorage = self.OleStorage
        from hwp5.errors import InvalidOleStorageError
        from hwp5.storage import is_storage

        olestg = OleStorage(self.hwp5file_path)
        self.assertTrue(is_storage(olestg))
        self.assertTrue(isinstance(olestg, OleStorage))

        nonolefile = self.get_fixture_file('nonole.txt')
        self.assertRaises(InvalidOleStorageError, OleStorage, nonolefile)

    def test_getitem0(self):
        if self.OleStorage is None:
            logger.warning('%s: skipped', self.id())
            return
        from hwp5.storage import is_storage, is_stream
        olestg = self.olestg
        self.assertTrue(is_storage(olestg))
        #self.assertEquals('', olestg.path)

        docinfo = olestg['DocInfo']
        self.assertTrue(is_stream(docinfo))
        #self.assertEquals('DocInfo', docinfo.path)

        bodytext = olestg['BodyText']
        self.assertTrue(is_storage(bodytext))
        #self.assertEquals('BodyText', bodytext.path)

        section = bodytext['Section0']
        self.assertTrue(is_stream(section))
        #self.assertEquals('BodyText/Section0', section.path)

        f = section.open()
        try:
            data = f.read()
            self.assertEquals(1529, len(data))
        finally:
            f.close()

        try:
            bodytext['nonexists']
            self.fail('KeyError expected')
        except KeyError:
            pass

    def test_init_should_receive_string_olefile(self):
        if self.OleStorage is None:
            logger.warning('%s: skipped', self.id())
            return
        OleStorage = self.OleStorage
        path = self.get_fixture_file(self.hwp5file_name)
        olestg = OleStorage(path)
        self.assertTrue(olestg['FileHeader'] is not None)

    def test_iter(self):
        if self.OleStorage is None:
            logger.warning('%s: skipped', self.id())
            return
        olestg = self.olestg
        gen = iter(olestg)
        #import types
        #self.assertTrue(isinstance(gen, types.GeneratorType))
        expected = ['FileHeader', 'BodyText', 'BinData', 'Scripts',
                    'DocOptions', 'DocInfo', 'PrvText', 'PrvImage',
                    '\x05HwpSummaryInformation']
        self.assertEquals(sorted(expected), sorted(gen))

    def test_getitem(self):
        if self.OleStorage is None:
            logger.warning('%s: skipped', self.id())
            return
        from hwp5.storage import is_storage
        #from hwp5.storage.ole import OleStorage
        olestg = self.olestg

        try:
            olestg['non-exists']
            self.fail('KeyError expected')
        except KeyError:
            pass

        fileheader = olestg['FileHeader']
        self.assertTrue(hasattr(fileheader, 'open'))

        bindata = olestg['BinData']
        self.assertTrue(is_storage(bindata))
        #self.assertEquals('BinData', bindata.path)

        self.assertEquals(sorted(['BIN0002.jpg', 'BIN0002.png',
                                  'BIN0003.png']),
                          sorted(iter(bindata)))

        bin0002 = bindata['BIN0002.jpg']
        self.assertTrue(hasattr(bin0002, 'open'))

    def test_iter_storage_leafs(self):
        if self.OleStorage is None:
            logger.warning('%s: skipped', self.id())
            return
        from hwp5.storage import iter_storage_leafs
        result = iter_storage_leafs(self.olestg)
        expected = ['\x05HwpSummaryInformation', 'BinData/BIN0002.jpg',
                    'BinData/BIN0002.png', 'BinData/BIN0003.png',
                    'BodyText/Section0', 'DocInfo', 'DocOptions/_LinkDoc',
                    'FileHeader', 'PrvImage', 'PrvText',
                    'Scripts/DefaultJScript', 'Scripts/JScriptVersion']
        self.assertEquals(sorted(expected), sorted(result))

    def test_unpack(self):
        if self.OleStorage is None:
            logger.warning('%s: skipped', self.id())
            return
        from hwp5.storage import unpack
        import shutil
        import os
        import os.path

        if os.path.exists('5017'):
            shutil.rmtree('5017')
        os.mkdir('5017')
        unpack(self.olestg, '5017')

        self.assertTrue(os.path.exists('5017/_05HwpSummaryInformation'))
        self.assertTrue(os.path.exists('5017/BinData/BIN0002.jpg'))
        self.assertTrue(os.path.exists('5017/BinData/BIN0002.png'))
        self.assertTrue(os.path.exists('5017/BinData/BIN0003.png'))
        self.assertTrue(os.path.exists('5017/BodyText/Section0'))
        self.assertTrue(os.path.exists('5017/DocInfo'))
        self.assertTrue(os.path.exists('5017/DocOptions/_LinkDoc'))
        self.assertTrue(os.path.exists('5017/FileHeader'))
        self.assertTrue(os.path.exists('5017/PrvImage'))
        self.assertTrue(os.path.exists('5017/PrvText'))
        self.assertTrue(os.path.exists('5017/Scripts/DefaultJScript'))
        self.assertTrue(os.path.exists('5017/Scripts/JScriptVersion'))

########NEW FILE########
__FILENAME__ = mixin_relaxng
# -*- coding: utf-8 -*-
from __future__ import with_statement
import logging


logger = logging.getLogger(__name__)


class RelaxNGTestMixin(object):

    rng = '''<?xml version="1.0" encoding="UTF-8"?>
<grammar 
  xmlns="http://relaxng.org/ns/structure/1.0"
  datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
  <define name="doc">
    <element name="doc" >
      <optional>
        <attribute name="attr">
          <data type="string"/>
        </attribute>
      </optional>
    </element>
  </define>
  <start>
    <choice>
      <ref name="doc"/>
    </choice>
  </start>
</grammar>
'''
    def test_relaxng_compile(self):
        if self.relaxng_compile is None:
            logger.warning('%s: skipped', self.id())
            return

        rng = self.rng
        rng_path = self.id() + '.rng'
        with file(rng_path, 'w') as f:
            f.write(rng)

        inp = '<?xml version="1.0" encoding="utf-8"?><doc />'
        inp_path = self.id() + '.inp'
        with file(inp_path, 'w') as f:
            f.write(inp)

        bad = '<?xml version="1.0" encoding="utf-8"?><bad />'
        bad_path = self.id() + '.bad'
        with file(bad_path, 'w') as f:
            f.write(bad)

        validate = self.relaxng_compile(rng_path)
        self.assertTrue(callable(validate))
        self.assertTrue(validate(inp_path))
        self.assertFalse(validate(bad_path))

    def test_relaxng(self):
        if self.relaxng is None:
            logger.warning('%s: skipped', self.id())
            return

        rng = self.rng
        rng_path = self.id() + '.rng'
        with file(rng_path, 'w') as f:
            f.write(rng)

        inp = '<?xml version="1.0" encoding="utf-8"?><doc />'
        inp_path = self.id() + '.inp'
        with file(inp_path, 'w') as f:
            f.write(inp)

        bad = '<?xml version="1.0" encoding="utf-8"?><bad />'
        bad_path = self.id() + '.bad'
        with file(bad_path, 'w') as f:
            f.write(bad)

        self.assertTrue(self.relaxng(rng_path, inp_path))
        self.assertFalse(self.relaxng(rng_path, bad_path))

########NEW FILE########
__FILENAME__ = mixin_xslt
# -*- coding: utf-8 -*-
from __future__ import with_statement
import logging


logger = logging.getLogger(__name__)


class XsltTestMixin(object):

    xsl = '''<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="xml" encoding="utf-8" indent="yes" />
  <xsl:template match="/">
    <xsl:for-each select="inp">
      <xsl:element name="out" />
    </xsl:for-each>
  </xsl:template>
</xsl:stylesheet>'''

    def test_xslt_compile(self):
        if self.xslt_compile is None:
            logger.warning('%s: skipped', self.id())
            return

        xsl = self.xsl
        xsl_path = self.id() + '.xsl'
        with file(xsl_path, 'w') as f:
            f.write(xsl)

        inp = '<?xml version="1.0" encoding="utf-8"?><inp />'
        inp_path = self.id() + '.inp'
        with file(inp_path, 'w') as f:
            f.write(inp)

        out_path = self.id() + '.out'

        transform = self.xslt_compile(xsl_path)
        self.assertTrue(callable(transform))
        transform(inp_path, out_path)

        from xml.etree import ElementTree as etree
        with file(out_path) as f:
            out_doc = etree.parse(f)
        self.assertEquals('out', out_doc.getroot().tag)

    def test_xslt(self):
        if self.xslt is None:
            logger.warning('%s: skipped', self.id())
            return

        xsl = self.xsl
        xsl_path = self.id() + '.xsl'
        with file(xsl_path, 'w') as f:
            f.write(xsl)

        inp = '<?xml version="1.0" encoding="utf-8"?><inp />'
        inp_path = self.id() + '.inp'
        with file(inp_path, 'w') as f:
            f.write(inp)

        out_path = self.id() + '.out'

        result = self.xslt(xsl_path, inp_path, out_path)
        self.assertTrue('errors' not in result)

        from xml.etree import ElementTree as etree
        with file(out_path) as f:
            out_doc = etree.parse(f)
        self.assertEquals('out', out_doc.getroot().tag)

########NEW FILE########
__FILENAME__ = test_binmodel
# -*- coding: utf-8 -*-
from unittest import TestCase
from StringIO import StringIO

import test_recordstream
from hwp5.recordstream import Record, read_records
from hwp5.utils import cached_property
from hwp5.binmodel import RecordModel
from hwp5.importhelper import importjson


def TestContext(**ctx):
    ''' test context '''
    if not 'version' in ctx:
        ctx['version'] = (5, 0, 0, 0)
    return ctx

testcontext = TestContext()


class TestRecordParsing(TestCase):
    def test_init_record_parsing_context(self):
        from hwp5.tagids import HWPTAG_BEGIN
        from hwp5.binmodel import init_record_parsing_context
        record = dict(tagid=HWPTAG_BEGIN, payload='abcd')
        context = init_record_parsing_context(testcontext, record)

        self.assertEquals(record, context['record'])
        self.assertEquals('abcd', context['stream'].read())


class BinEmbeddedTest(TestCase):
    ctx = TestContext()
    stream = StringIO('\x12\x04\xc0\x00\x01\x00\x02\x00\x03\x00'
                      '\x6a\x00\x70\x00\x67\x00')

    def testParse(self):
        from hwp5.binmodel import BinData
        from hwp5.binmodel import init_record_parsing_context
        from hwp5.binmodel import parse_model
        record = read_records(self.stream).next()
        context = init_record_parsing_context(testcontext, record)
        model = record
        parse_model(context, model)

        self.assertTrue(BinData, model['type'])
        self.assertEquals(BinData.StorageType.EMBEDDING,
                          BinData.Flags(model['content']['flags']).storage)
        self.assertEquals(2, model['content']['bindata']['storage_id'])
        self.assertEquals('jpg', model['content']['bindata']['ext'])


class LanguageStructTest(TestCase):
    def test_cls_dict_has_attributes(self):
        from hwp5.binmodel import LanguageStruct
        from hwp5.dataio import WORD
        FontFace = LanguageStruct('FontFace', WORD)
        self.assertTrue('attributes' in FontFace.__dict__)


class TestBase(test_recordstream.TestBase):

    @cached_property
    def hwp5file_bin(self):
        from hwp5.binmodel import Hwp5File
        return Hwp5File(self.olestg)

    hwp5file = hwp5file_bin


class FaceNameTest(TestBase):
    hwp5file_name = 'facename.hwp'

    def test_font_file_type(self):
        from hwp5.binmodel import FaceName

        docinfo = self.hwp5file.docinfo
        facenames = (model for model in docinfo.models()
                     if model['type'] is FaceName)
        facenames = list(facenames)

        facename = facenames[0]['content']
        self.assertEquals(u'굴림', facename['name'])
        self.assertEquals(FaceName.FontFileType.TTF,
                          facename['flags'].font_file_type)

        facename = facenames[3]['content']
        self.assertEquals(u'휴먼명조', facename['name'])
        self.assertEquals(FaceName.FontFileType.HFT,
                          facename['flags'].font_file_type)

        facename = facenames[4]['content']
        self.assertEquals(u'한양신명조', facename['name'])
        self.assertEquals(FaceName.FontFileType.HFT,
                          facename['flags'].font_file_type)


class DocInfoTest(TestBase):
    hwp5file_name = 'facename2.hwp'

    def test_charshape_lang_facename(self):
        from hwp5.binmodel import Style

        docinfo = self.hwp5file.docinfo
        styles = list(m for m in docinfo.models()
                      if m['type'] is Style)

        def style_lang_facename(style, lang):
            charshape_id = style['content']['charshape_id']
            return docinfo.charshape_lang_facename(charshape_id, lang)

        def style_lang_facename_name(style, lang):
            facename = style_lang_facename(style, lang)
            return facename['content']['name']

        self.assertEquals(u'바탕', style_lang_facename_name(styles[0], 'ko'))
        self.assertEquals(u'한컴돋움', style_lang_facename_name(styles[1], 'ko'))
        self.assertEquals(u'Times New Roman',
                          style_lang_facename_name(styles[2], 'en'))
        self.assertEquals(u'Arial', style_lang_facename_name(styles[3], 'en'))
        self.assertEquals(u'해서 약자', style_lang_facename_name(styles[4], 'cn'))
        self.assertEquals(u'해서 간자', style_lang_facename_name(styles[5], 'cn'))
        self.assertEquals(u'명조', style_lang_facename_name(styles[6], 'jp'))
        self.assertEquals(u'고딕', style_lang_facename_name(styles[7], 'jp'))


class BorderFillTest(TestBase):
    hwp5file_name = 'borderfill.hwp'

    def test_parse_borderfill(self):
        from hwp5.binmodel import BorderFill
        from hwp5.binmodel import TableCell

        docinfo = self.hwp5file.docinfo
        borderfills = (model for model in docinfo.models()
                       if model['type'] is BorderFill)
        borderfills = list(borderfills)

        section = self.hwp5file.bodytext.section(0)
        tablecells = list(model for model in section.models()
                          if model['type'] is TableCell)
        for tablecell in tablecells:
            borderfill_id = tablecell['content']['borderfill_id']
            borderfill = borderfills[borderfill_id - 1]['content']
            tablecell['borderfill'] = borderfill

        borderfill = tablecells[0]['borderfill']
        self.assertEquals(0, borderfill['fillflags'])
        self.assertEquals(None, borderfill.get('fill_colorpattern'))
        self.assertEquals(None, borderfill.get('fill_gradation'))
        self.assertEquals(None, borderfill.get('fill_image'))

        borderfill = tablecells[1]['borderfill']
        self.assertEquals(1, borderfill['fillflags'])
        self.assertEquals(dict(background_color=0xff7f3f,
                               pattern_color=0,
                               pattern_type_flags=0xffffffff),
                          borderfill['fill_colorpattern'])
        self.assertEquals(None, borderfill.get('fill_gradation'))
        self.assertEquals(None, borderfill.get('fill_image'))

        borderfill = tablecells[2]['borderfill']
        self.assertEquals(4, borderfill['fillflags'])
        self.assertEquals(None, borderfill.get('fill_colorpattern'))
        self.assertEquals(dict(blur=40, center=dict(x=0, y=0),
                               colors=[0xff7f3f, 0],
                               shear=90, type=1),
                          borderfill['fill_gradation'])
        self.assertEquals(None, borderfill.get('fill_image'))

        borderfill = tablecells[3]['borderfill']
        self.assertEquals(2, borderfill['fillflags'])
        self.assertEquals(None, borderfill.get('fill_colorpattern'))
        self.assertEquals(None, borderfill.get('fill_gradation'))
        self.assertEquals(dict(flags=5, storage_id=1),
                          borderfill.get('fill_image'))

        borderfill = tablecells[4]['borderfill']
        self.assertEquals(3, borderfill['fillflags'])
        self.assertEquals(dict(background_color=0xff7f3f,
                               pattern_color=0,
                               pattern_type_flags=0xffffffff),
                          borderfill['fill_colorpattern'])
        self.assertEquals(None, borderfill.get('fill_gradation'))
        self.assertEquals(dict(flags=5, storage_id=1),
                          borderfill.get('fill_image'))

        borderfill = tablecells[5]['borderfill']
        self.assertEquals(6, borderfill['fillflags'])
        self.assertEquals(None, borderfill.get('fill_colorpattern'))
        self.assertEquals(dict(blur=40, center=dict(x=0, y=0),
                               colors=[0xff7f3f, 0],
                               shear=90, type=1),
                          borderfill['fill_gradation'])
        self.assertEquals(dict(flags=5, storage_id=1),
                          borderfill.get('fill_image'))


class StyleTest(TestBase):
    hwp5file_name = 'charstyle.hwp'

    def test_charstyle(self):
        from hwp5.binmodel import Style

        docinfo = self.hwp5file.docinfo
        styles = (model for model in docinfo.models()
                  if model['type'] is Style)
        styles = list(styles)

        style = styles[0]['content']
        self.assertEquals(dict(name='Normal',
                               unknown=0,
                               parashape_id=0,
                               charshape_id=1,
                               next_style_id=0,
                               lang_id=1042,
                               flags=0,
                               local_name=u'바탕글'),
                          style)
        charstyle = styles[13]['content']
        self.assertEquals(dict(name='',
                               unknown=0,
                               parashape_id=0,
                               charshape_id=1,
                               next_style_id=0,
                               lang_id=1042,
                               flags=1,
                               local_name=u'글자스타일'),
                          charstyle)


class ParaCharShapeTest(TestBase):

    @property
    def paracharshape_record(self):
        return self.bodytext.section(0).record(2)

    def test_read_paracharshape(self):
        from hwp5.binmodel import init_record_parsing_context
        from hwp5.binmodel import parse_model
        parent_context = dict()
        parent_model = dict(content=dict(charshapes=5))

        record = self.paracharshape_record
        context = init_record_parsing_context(dict(), record)
        context['parent'] = parent_context, parent_model
        model = record
        parse_model(context, model)
        self.assertEquals(dict(charshapes=[(0, 7), (19, 8), (23, 7), (24, 9),
                                           (26, 7)]),
                          model['content'])


class TableTest(TestBase):

    @property
    def stream(self):
        return StringIO('G\x04\xc0\x02 lbt\x11#*\x08\x00\x00\x00\x00\x00\x00'
                        '\x00\x00\x06\x9e\x00\x00D\x10\x00\x00\x00\x00\x00\x00'
                        '\x1b\x01\x1b\x01\x1b\x01\x1b\x01\xed\xad\xa2V\x00\x00'
                        '\x00\x00')

    @cached_property
    def tablecontrol_record(self):
        return self.bodytext.section(0).record(30)

    @cached_property
    def tablecaption_record(self):
        return self.bodytext.section(0).record(68)

    @cached_property
    def tablebody_record(self):
        return self.bodytext.section(0).record(31)

    @cached_property
    def tablecell_record(self):
        return self.bodytext.section(0).record(32)

    def testParsePass1(self):
        from hwp5.binmodel import TableControl
        from hwp5.binmodel import init_record_parsing_context
        from hwp5.binmodel import parse_model
        record = read_records(self.stream).next()
        context = init_record_parsing_context(testcontext, record)
        model = record
        parse_model(context, model)

        self.assertTrue(TableControl, model['type'])
        self.assertEquals(1453501933, model['content']['instance_id'])
        self.assertEquals(0x0, model['content']['x'])
        self.assertEquals(0x0, model['content']['y'])
        self.assertEquals(0x1044, model['content']['height'])
        self.assertEquals(0x9e06, model['content']['width'])
        self.assertEquals(0, model['content']['unknown1'])
        self.assertEquals(0x82a2311L, model['content']['flags'])
        self.assertEquals(0, model['content']['z_order'])
        self.assertEquals(dict(left=283, right=283, top=283, bottom=283),
                          model['content']['margin'])
        self.assertEquals('tbl ', model['content']['chid'])

    def test_parse_child_table_body(self):
        from hwp5.binmodel import TableControl, TableBody
        from hwp5.binmodel import init_record_parsing_context
        record = self.tablecontrol_record
        context = init_record_parsing_context(testcontext, record)

        tablebody_record = self.tablebody_record
        child_context = init_record_parsing_context(testcontext,
                                                    tablebody_record)
        child_model = dict(type=TableBody, content=dict())
        child = (child_context, child_model)

        self.assertFalse(context.get('table_body'))
        TableControl.on_child(dict(), context, child)
        # 'table_body' in table record context should have been changed to True
        self.assertTrue(context['table_body'])
        # model and attributes should not have been changed
        self.assertEquals(dict(), child_model['content'])

    def test_parse_child_table_cell(self):
        from hwp5.binmodel import init_record_parsing_context
        from hwp5.binmodel import parse_model
        from hwp5.binmodel import TableCell
        record = self.tablecontrol_record
        context = init_record_parsing_context(testcontext, record)
        model = record
        parse_model(context, model)

        context['table_body'] = True

        child_record = self.tablecell_record
        child_context = init_record_parsing_context(testcontext, child_record)
        child_model = child_record
        child_context['parent'] = context, model
        parse_model(child_context, child_model)
        self.assertEquals(TableCell, child_model['type'])
        self.assertEquals(TableCell, child_model['type'])
        self.assertEquals(dict(padding=dict(top=141, right=141, bottom=141,
                                            left=141),
                               rowspan=1,
                               colspan=1,
                               borderfill_id=1,
                               height=282,
                               listflags=32L,
                               width=20227,
                               unknown1=0,
                               unknown_width=20227,
                               paragraphs=1,
                               col=0,
                               row=0), child_model['content'])
        self.assertEquals('', child_context['stream'].read())

    def test_parse_child_table_caption(self):
        from hwp5.binmodel import init_record_parsing_context
        from hwp5.binmodel import parse_model
        from hwp5.binmodel import TableCaption
        record = self.tablecontrol_record
        context = init_record_parsing_context(testcontext, record)
        model = record
        parse_model(context, model)

        context['table_body'] = False

        child_record = self.tablecaption_record
        child_context = init_record_parsing_context(testcontext, child_record)
        child_context['parent'] = context, model
        child_model = child_record
        parse_model(child_context, child_model)
        self.assertEquals(TableCaption, child_model['type'])
        self.assertEquals(dict(listflags=0,
                               width=8504,
                               maxsize=40454,
                               unknown1=0,
                               flags=3L,
                               separation=850,
                               paragraphs=2), child_model['content'])
        self.assertEquals('', child_context['stream'].read())


class ShapeComponentTest(TestBase):

    hwp5file_name = 'textbox.hwp'

    @cached_property
    def control_gso_record(self):
        return self.bodytext.section(0).record(12)

    @cached_property
    def shapecomponent_record(self):
        return self.bodytext.section(0).record(19)

    @cached_property
    def textbox_paragraph_list_record(self):
        return self.bodytext.section(0).record(20)

    def test_parse_shapecomponent_textbox_paragraph_list(self):
        from hwp5.binmodel import init_record_parsing_context
        from hwp5.binmodel import parse_model
        from hwp5.binmodel import ShapeComponent
        from hwp5.binmodel import TextboxParagraphList
        record = self.shapecomponent_record
        context = init_record_parsing_context(testcontext, record)
        model = record
        model['type'] = ShapeComponent

        child_record = self.textbox_paragraph_list_record
        child_context = init_record_parsing_context(testcontext,
                                                    child_record)
        child_context['parent'] = context, model
        child_model = child_record
        parse_model(child_context, child_model)
        self.assertEquals(TextboxParagraphList, child_model['type'])
        self.assertEquals(dict(listflags=32L,
                               padding=dict(top=283, right=283, bottom=283,
                                            left=283),
                               unknown1=0,
                               maxwidth=11763,
                               paragraphs=1), child_model['content'])
        self.assertEquals('', child_context['stream'].read())

    def test_parse(self):
        from hwp5.binmodel import init_record_parsing_context
        from hwp5.binmodel import parse_model
        from hwp5.binmodel import GShapeObjectControl, ShapeComponent

        #parent_record = self.control_gso_record

        # if parent model is GShapeObjectControl
        parent_model = dict(type=GShapeObjectControl)

        record = self.shapecomponent_record
        context = init_record_parsing_context(testcontext, record)
        context['parent'] = dict(), parent_model
        model = record
        parse_model(context, model)

        self.assertEquals(model['type'], ShapeComponent)
        self.assertTrue('chid0' in model['content'])

        # if parent model is not GShapeObjectControl
        # TODO

    def test_rect_fill(self):
        from hwp5.binmodel import ShapeComponent
        self.hwp5file_name = 'shapecomponent-rect-fill.hwp'

        section = self.hwp5file_bin.bodytext.section(0)
        shapecomps = (model for model in section.models()
                      if model['type'] is ShapeComponent)
        shapecomps = list(shapecomps)

        shapecomp = shapecomps.pop(0)['content']
        self.assertFalse(shapecomp['fill_flags'].fill_colorpattern)
        self.assertFalse(shapecomp['fill_flags'].fill_gradation)
        self.assertFalse(shapecomp['fill_flags'].fill_image)

        shapecomp = shapecomps.pop(0)['content']
        self.assertTrue(shapecomp['fill_flags'].fill_colorpattern)
        self.assertFalse(shapecomp['fill_flags'].fill_gradation)
        self.assertFalse(shapecomp['fill_flags'].fill_image)
        self.assertEquals(dict(background_color=0xff7f3f,
                               pattern_color=0,
                               pattern_type_flags=0xffffffff),
                          shapecomp['fill_colorpattern'])
        self.assertEquals(None, shapecomp.get('fill_gradation'))
        self.assertEquals(None, shapecomp.get('fill_image'))

        shapecomp = shapecomps.pop(0)['content']
        self.assertFalse(shapecomp['fill_flags'].fill_colorpattern)
        self.assertTrue(shapecomp['fill_flags'].fill_gradation)
        self.assertFalse(shapecomp['fill_flags'].fill_image)
        self.assertEquals(None, shapecomp.get('fill_colorpattern'))
        self.assertEquals(dict(type=1, shear=90,
                               center=dict(x=0, y=0),
                               colors=[0xff7f3f, 0],
                               blur=50), shapecomp['fill_gradation'])
        self.assertEquals(None, shapecomp.get('fill_image'))

        shapecomp = shapecomps.pop(0)['content']
        self.assertFalse(shapecomp['fill_flags'].fill_colorpattern)
        self.assertFalse(shapecomp['fill_flags'].fill_gradation)
        self.assertTrue(shapecomp['fill_flags'].fill_image)
        self.assertEquals(None, shapecomp.get('fill_colorpattern'))
        self.assertEquals(None, shapecomp.get('fill_gradation'))
        self.assertEquals(dict(flags=5, storage_id=1),
                          shapecomp['fill_image'])

        shapecomp = shapecomps.pop(0)['content']
        self.assertTrue(shapecomp['fill_flags'].fill_colorpattern)
        self.assertFalse(shapecomp['fill_flags'].fill_gradation)
        self.assertTrue(shapecomp['fill_flags'].fill_image)
        self.assertEquals(dict(background_color=0xff7f3f,
                               pattern_color=0,
                               pattern_type_flags=0xffffffff),
                          shapecomp['fill_colorpattern'])
        self.assertEquals(None, shapecomp.get('fill_gradation'))
        self.assertEquals(dict(flags=5, storage_id=1),
                          shapecomp['fill_image'])

        shapecomp = shapecomps.pop(0)['content']
        self.assertFalse(shapecomp['fill_flags'].fill_colorpattern)
        self.assertTrue(shapecomp['fill_flags'].fill_gradation)
        self.assertTrue(shapecomp['fill_flags'].fill_image)
        self.assertEquals(None, shapecomp.get('fill_colorpattern'))
        self.assertEquals(dict(type=1, shear=90,
                               center=dict(x=0, y=0),
                               colors=[0xff7f3f, 0],
                               blur=50), shapecomp['fill_gradation'])
        self.assertEquals(dict(flags=5, storage_id=1),
                          shapecomp['fill_image'])

    def test_colorpattern_gradation(self):
        import pickle
        from hwp5.binmodel import parse_models
        fixturename = '5005-shapecomponent-with-colorpattern-and-gradation.dat'
        # TODO: regenerate fixture with rb
        f = self.open_fixture(fixturename, 'r')
        try:
            records = pickle.load(f)
        finally:
            f.close()

        context = dict(version=(5, 0, 0, 5))
        models = parse_models(context, records)
        models = list(models)
        self.assertEquals(1280, models[-1]['content']['fill_flags'])
        colorpattern = models[-1]['content']['fill_colorpattern']
        gradation = models[-1]['content']['fill_gradation']
        self.assertEquals(32768, colorpattern['background_color'])
        self.assertEquals(0, colorpattern['pattern_color'])
        self.assertEquals(0xffffffff, colorpattern['pattern_type_flags'])

        self.assertEquals(50, gradation['blur'])
        self.assertEquals(dict(x=0, y=100), gradation['center'])
        self.assertEquals([64512, 13171936], gradation['colors'])
        self.assertEquals(180, gradation['shear'])
        self.assertEquals(1, gradation['type'])
        self.assertEquals(1, models[-1]['content']['fill_shape'])
        self.assertEquals(50, models[-1]['content']['fill_blur_center'])

    def test_colorpattern_gradation_5017(self):
        from hwp5.recordstream import read_records
        from hwp5.binmodel import parse_models
        fixturename = '5017-shapecomponent-with-colorpattern-and-gradation.bin'
        f = self.open_fixture(fixturename, 'rb')
        try:
            records = list(read_records(f))
        finally:
            f.close()

        context = dict(version=(5, 0, 1, 7))
        models = parse_models(context, records)
        models = list(models)
        self.assertEquals(1280, models[-1]['content']['fill_flags'])
        colorpattern = models[-1]['content']['fill_colorpattern']
        gradation = models[-1]['content']['fill_gradation']
        self.assertEquals(32768, colorpattern['background_color'])
        self.assertEquals(0, colorpattern['pattern_color'])
        self.assertEquals(0xffffffff, colorpattern['pattern_type_flags'])

        self.assertEquals(50, gradation['blur'])
        self.assertEquals(dict(x=0, y=100), gradation['center'])
        self.assertEquals([64512, 13171936], gradation['colors'])
        self.assertEquals(180, gradation['shear'])
        self.assertEquals(1, gradation['type'])
        self.assertEquals(1, models[-1]['content']['fill_shape'])
        self.assertEquals(50, models[-1]['content']['fill_blur_center'])


class HeaderFooterTest(TestBase):

    hwp5file_name = 'headerfooter.hwp'

    @cached_property
    def header_record(self):
        return self.bodytext.section(0).record(16)

    @cached_property
    def header_paragraph_list_record(self):
        return self.bodytext.section(0).record(17)

    def test_parse_child(self):
        from hwp5.binmodel import init_record_parsing_context
        from hwp5.binmodel import parse_model
        from hwp5.binmodel import HeaderParagraphList
        record = self.header_record
        context = init_record_parsing_context(testcontext, record)
        model = record
        parse_model(context, model)

        child_record = self.header_paragraph_list_record
        child_context = init_record_parsing_context(testcontext,
                                                    child_record)
        child_context['parent'] = context, model
        child_model = child_record
        parse_model(child_context, child_model)
        self.assertEquals(HeaderParagraphList, child_model['type'])
        self.assertEquals(dict(textrefsbitmap=0,
                               numberrefsbitmap=0,
                               height=4252,
                               listflags=0,
                               width=42520,
                               unknown1=0,
                               paragraphs=1), child_model['content'])
        # TODO
        #self.assertEquals('', child_context['stream'].read())


class ListHeaderTest(TestCase):
    ctx = TestContext()
    record_bytes = ('H\x08`\x02\x01\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00'
                    '\x01\x00\x01\x00\x03O\x00\x00\x1a\x01\x00\x00\x8d\x00'
                    '\x8d\x00\x8d\x00\x8d\x00\x01\x00\x03O\x00\x00')
    stream = StringIO(record_bytes)

    def testParse(self):
        from hwp5.binmodel import ListHeader
        from hwp5.binmodel import init_record_parsing_context
        from hwp5.binmodel import parse_model
        record = read_records(self.stream).next()
        context = init_record_parsing_context(testcontext, record)
        model = record
        parse_model(context, model)

        self.assertEquals(ListHeader, model['type'])
        self.assertEquals(1, model['content']['paragraphs'])
        self.assertEquals(0x20L, model['content']['listflags'])
        self.assertEquals(0, model['content']['unknown1'])
        self.assertEquals(8, context['stream'].tell())


class TableBodyTest(TestCase):
    ctx = TestContext(version=(5, 0, 1, 7))
    stream = StringIO('M\x08\xa0\x01\x06\x00\x00\x04\x02\x00\x02\x00\x00\x00'
                      '\x8d\x00\x8d\x00\x8d\x00\x8d\x00\x02\x00\x02\x00\x01'
                      '\x00\x00\x00')

    def test_parse_model(self):
        from hwp5.binmodel import TableBody
        from hwp5.binmodel import init_record_parsing_context
        from hwp5.binmodel import parse_model
        record = read_records(self.stream).next()
        context = init_record_parsing_context(self.ctx, record)
        model = record

        parse_model(context, model)
        model_type = model['type']
        model_content = model['content']

        self.assertEquals(TableBody, model_type)
        self.assertEquals(dict(left=141, right=141, top=141, bottom=141),
                          model_content['padding'])
        self.assertEquals(0x4000006L, model_content['flags'])
        self.assertEquals(2, model_content['cols'])
        self.assertEquals(2, model_content['rows'])
        self.assertEquals(1, model_content['borderfill_id'])
        self.assertEquals([2, 2], model_content['rowcols'])
        self.assertEquals(0, model_content['cellspacing'])
        self.assertEquals([], model_content['validZones'])


class Pass2Test(TestCase):
    ctx = TestContext()

    def test_pass2_events(self):
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.treeop import prefix_event
        from hwp5.tagids import HWPTAG_BEGIN

        def items():
            yield Record(HWPTAG_BEGIN + 4, 0, ''),
            yield Record(HWPTAG_BEGIN + 3, 1, ''),
            yield Record(HWPTAG_BEGIN + 2, 0, ''),
            yield Record(HWPTAG_BEGIN + 1, 0, ''),
        items = list(item for item in items())
        leveld_items = zip([0, 1, 0, 0], items)

        events = list(prefix_event(leveld_items))

        def expected():
            yield STARTEVENT, items[0]
            yield STARTEVENT, items[1]
            yield ENDEVENT, items[1]
            yield ENDEVENT, items[0]
            yield STARTEVENT, items[2]
            yield ENDEVENT, items[2]
            yield STARTEVENT, items[3]
            yield ENDEVENT, items[3]
        expected = list(expected())
        self.assertEquals(expected, events)


class LineSegTest(TestCase):
    def testDecode(self):
        data = ('00000000481e0000e8030000e80300005203000058020000dc0500003ca00'
                '000000006003300000088240000e8030000e80300005203000058020000dc'
                '0500003ca000000000060067000000c82a0000e8030000e80300005203000'
                '058020000dc0500003ca0000000000600')
        import binascii
        data = binascii.a2b_hex(data)
        from hwp5.binmodel import ParaLineSegList
        lines = list(ParaLineSegList.decode(dict(), data))
        self.assertEquals(0, lines[0]['chpos'])
        self.assertEquals(51, lines[1]['chpos'])
        self.assertEquals(103, lines[2]['chpos'])


class TableCaptionCellTest(TestCase):
    ctx = TestContext(version=(5, 0, 1, 7))
    records_bytes = ('G\x04\xc0\x02 lbt\x10#*(\x00\x00\x00\x00\x00\x00\x00\x00'
                     '\x06\x9e\x00\x00\x04\n\x00\x00\x03\x00\x00\x00\x1b\x01R'
                     '\x037\x02n\x04\n^\xc0V\x00\x00\x00\x00H\x08`\x01\x02\x00'
                     '\x00\x00\x00\x00\x00\x00\x03\x00\x00\x008!\x00\x00R\x03'
                     '\x06\x9e\x00\x00M\x08\xa0\x01\x06\x00\x00\x04\x02\x00'
                     '\x02\x00\x00\x00\x8d\x00\x8d\x00\x8d\x00\x8d\x00\x02\x00'
                     '\x02\x00\x01\x00\x00\x00H\x08`\x02\x01\x00\x00\x00 \x00'
                     '\x00\x00\x00\x00\x00\x00\x01\x00\x01\x00\x03O\x00\x00'
                     '\x1a\x01\x00\x00\x8d\x00\x8d\x00\x8d\x00\x8d\x00\x01\x00'
                     '\x03O\x00\x00')

    def testParsePass1(self):
        from hwp5.binmodel import TableCaption, TableCell
        from hwp5.binmodel import parse_models_intern
        stream = StringIO(self.records_bytes)
        records = list(read_records(stream))
        result = list(parse_models_intern(self.ctx, records))

        tablecaption = result[1]
        context, model = tablecaption
        model_type = model['type']
        model_content = model['content']
        stream = context['stream']

        self.assertEquals(TableCaption, model_type)
        self.assertEquals(22, stream.tell())
        # ListHeader attributes
        self.assertEquals(2, model_content['paragraphs'])
        self.assertEquals(0x0L, model_content['listflags'])
        self.assertEquals(0, model_content['unknown1'])
        # TableCaption model_content
        self.assertEquals(3, model_content['flags'])
        self.assertEquals(8504L, model_content['width'])
        self.assertEquals(850, model_content['separation'])
        self.assertEquals(40454L, model_content['maxsize'])

        tablecell = result[3]
        context, model = tablecell
        model_type = model['type']
        model_content = model['content']
        stream = context['stream']
        self.assertEquals(TableCell, model_type)
        self.assertEquals(38, stream.tell())
        # ListHeader model_content
        self.assertEquals(1, model_content['paragraphs'])
        self.assertEquals(0x20L, model_content['listflags'])
        self.assertEquals(0, model_content['unknown1'])
        # TableCell model_content
        self.assertEquals(0, model_content['col'])
        self.assertEquals(0, model_content['row'])
        self.assertEquals(1, model_content['colspan'])
        self.assertEquals(1, model_content['rowspan'])
        self.assertEquals(0x4f03, model_content['width'])
        self.assertEquals(0x11a, model_content['height'])
        self.assertEquals(dict(left=141, right=141, top=141, bottom=141),
                          model_content['padding'])
        self.assertEquals(1, model_content['borderfill_id'],)
        self.assertEquals(0x4f03, model_content['unknown_width'])


class TestRecordModel(TestCase):
    def test_assign_enum_flags_name(self):
        from hwp5.dataio import Flags, Enum, UINT32

        class FooRecord(RecordModel):
            Bar = Flags(UINT32)
            Baz = Enum()
        self.assertEquals('Bar', FooRecord.Bar.__name__)
        self.assertEquals('Baz', FooRecord.Baz.__name__)


class TestControlType(TestCase):
    def test_ControlType(self):
        from hwp5.binmodel import Control

        class FooControl(Control):
            chid = 'foo!'
        try:
            class Foo2Control(Control):
                chid = 'foo!'
        except Exception:
            pass
        else:
            assert False, 'Exception expected'


class TestControlChar(TestBase):

    def test_decode(self):
        from hwp5.binmodel import ControlChar
        paratext_record = self.hwp5file.bodytext.section(0).record(1)
        payload = paratext_record['payload']
        controlchar = ControlChar.decode(payload[0:16])
        self.assertEquals(dict(code=ord(ControlChar.SECTION_COLUMN_DEF),
                               chid='secd',
                               param='\x00' * 8), controlchar)

    def test_find(self):
        from hwp5.binmodel import ControlChar
        bytes = '\x41\x00'
        self.assertEquals((2, 2), ControlChar.find(bytes, 0))

    def test_tab(self):
        from hwp5.binmodel import ParaText, ControlChar
        self.hwp5file_name = 'tabdef.hwp'
        models = self.hwp5file.bodytext.section(0).models()
        paratexts = list(model for model in models
                         if model['type'] is ParaText)

        def paratext_tabs(paratext):
            for range, chunk in paratext['content']['chunks']:
                if isinstance(chunk, dict):
                    if unichr(chunk['code']) == ControlChar.TAB:
                        yield chunk
        self.assertEquals(set(['code', 'param']),
                          set(paratext_tabs(paratexts[0]).next().keys()))

        def paratext_tab_params(paratext):
            for tab in paratext_tabs(paratext):
                yield tab['param']

        tabs = list(paratext_tab_params(paratexts.pop(0)))
        self.assertEquals([(4000, 1)] * 3,
                          list((tab['width'], tab['unknown1'])
                               for tab in tabs))

        tabs = list(paratext_tab_params(paratexts.pop(0)))
        self.assertEquals([(2000, 1), (1360, 1), (1360, 1)],
                          list((tab['width'], tab['unknown1'])
                               for tab in tabs))

        tabs = list(paratext_tab_params(paratexts.pop(0)))
        self.assertEquals([(2328, 2)] * 3,
                          list((tab['width'], tab['unknown1'])
                               for tab in tabs))

        tabs = list(paratext_tab_params(paratexts.pop(0)))
        self.assertEquals([(2646, 3), (2292, 3), (2292, 3)],
                          list((tab['width'], tab['unknown1'])
                               for tab in tabs))

        tabs = list(paratext_tab_params(paratexts.pop(0)))
        self.assertEquals([(2104, 4)] * 3,
                          list((tab['width'], tab['unknown1'])
                               for tab in tabs))

        tabs = list(paratext_tab_params(paratexts.pop(0)))
        self.assertEquals([(4000, 1), (3360, 1), (3360, 1)],
                          list((tab['width'], tab['unknown1'])
                               for tab in tabs))

        tabs = list(paratext_tab_params(paratexts.pop(0)))
        self.assertEquals([(4000, 1), (3328, 1)],
                          list((tab['width'], tab['unknown1'])
                               for tab in tabs))

        tabs = list(paratext_tab_params(paratexts.pop(0)))
        self.assertEquals([(4000, 1), (3672, 1), (33864, 2)],
                          list((tab['width'], tab['unknown1'])
                               for tab in tabs))


class TestFootnoteShape(TestBase):

    def test_footnote_shape(self):
        import pickle
        f = self.open_fixture('5000-footnote-shape.dat', 'r')
        try:
            records = pickle.load(f)
        finally:
            f.close()

        context = dict(version=(5, 0, 0, 0))
        from hwp5.binmodel import parse_models
        models = parse_models(context, records)
        models = list(models)
        self.assertEquals(850, models[0]['content']['splitter_margin_top'])
        self.assertEquals(567, models[0]['content']['splitter_margin_bottom'])


class TestControlData(TestBase):
    def test_parse(self):
        import pickle
        f = self.open_fixture('5006-controldata.record', 'r')
        try:
            record = pickle.load(f)
        finally:
            f.close()
        from hwp5.binmodel import init_record_parsing_context
        from hwp5.binmodel import parse_model
        from hwp5.binmodel import ControlData
        context = init_record_parsing_context(dict(), record)
        model = record
        parse_model(context, model)
        self.assertEquals(ControlData, model['type'])
        self.assertEquals(dict(), model['content'])


class TestModelJson(TestBase):
    def test_model_to_json(self):
        from hwp5.binmodel import model_to_json
        model = self.hwp5file.docinfo.model(0)
        json = model_to_json(model)

        simplejson = importjson()
        jsonobject = simplejson.loads(json)
        self.assertEquals('DocumentProperties', jsonobject['type'])

    def test_model_to_json_should_not_modify_input(self):
        from hwp5.binmodel import model_to_json
        model = self.hwp5file.docinfo.model(0)
        model_to_json(model, indent=2, sort_keys=True)
        self.assertFalse(isinstance(model['type'], basestring))

    def test_model_to_json_with_controlchar(self):
        from hwp5.binmodel import model_to_json
        model = self.hwp5file.bodytext.section(0).model(1)
        json = model_to_json(model)

        simplejson = importjson()
        jsonobject = simplejson.loads(json)
        self.assertEquals('ParaText', jsonobject['type'])
        self.assertEquals([[0, 8],
                           dict(code=2, param='\x00' * 8, chid='secd')],
                          jsonobject['content']['chunks'][0])

    def test_model_to_json_with_unparsed(self):
        from hwp5.binmodel import model_to_json

        model = dict(type=RecordModel, content=[], payload='\x00\x01\x02\x03',
                     unparsed='\xff\xfe\xfd\xfc')
        json = model_to_json(model)

        simplejson = importjson()
        jsonobject = simplejson.loads(json)
        self.assertEquals(['ff fe fd fc'], jsonobject['unparsed'])

    def test_generate_models_json_array(self):
        models_json = self.hwp5file.bodytext.section(0).models_json()
        gen = models_json.generate()

        simplejson = importjson()
        json_array = simplejson.loads(''.join(gen))
        self.assertEquals(128, len(json_array))


class TestModelStream(TestBase):
    @cached_property
    def docinfo(self):
        from hwp5.binmodel import ModelStream
        return ModelStream(self.hwp5file_rec['DocInfo'],
                           self.hwp5file_rec.header.version)

    def test_models(self):
        self.assertEquals(67, len(list(self.docinfo.models())))

    def test_models_treegrouped(self):
        from hwp5.binmodel import Paragraph
        section = self.bodytext.section(0)
        for idx, paragraph_models in enumerate(section.models_treegrouped()):
            paragraph_models = list(paragraph_models)
            leader = paragraph_models[0]
            # leader should be a Paragraph
            self.assertEquals(Paragraph, leader['type'])
            # leader should be at top-level
            self.assertEquals(0, leader['level'])
            #print idx, leader['record']['seqno'], len(paragraph_models)

    def test_model(self):
        model = self.docinfo.model(0)
        self.assertEquals(0, model['seqno'])

        model = self.docinfo.model(10)
        self.assertEquals(10, model['seqno'])

    def test_models_json_open(self):
        simplejson = importjson()
        f = self.docinfo.models_json().open()
        try:
            self.assertEquals(67, len(simplejson.load(f)))
        finally:
            f.close()

########NEW FILE########
__FILENAME__ = test_bintype
# -*- coding: utf-8 -*-
from unittest import TestCase


class lazy_property(object):

    def __init__(self, f):
        self.f = f

    def __get__(self, object, owner=None):
        name = self.f.__name__
        if name not in object.__dict__:
            object.__dict__[name] = self.f(object)
        return object.__dict__[name]


class TestBinIO(TestCase):

    @lazy_property
    def BasicStruct(self):
        from hwp5.dataio import StructType
        from hwp5.dataio import UINT16
        class BasicStruct(object):
            __metaclass__ = StructType

            @staticmethod
            def attributes():
                yield UINT16, 'a'
                yield UINT16, 'b'
        return BasicStruct

    @lazy_property
    def NestedStruct(self):
        from hwp5.dataio import StructType
        from hwp5.dataio import UINT16
        class NestedStruct(object):
            __metaclass__ = StructType

            @staticmethod
            def attributes():
                yield UINT16, 'a'
                yield self.BasicStruct, 's'
                yield UINT16, 'b'
        return NestedStruct

    def test_map_events(self):
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.dataio import UINT16
        from hwp5.bintype import bintype_map_events

        bin_item = dict(type=self.BasicStruct)
        events = bintype_map_events(bin_item)

        ev, item = events.next()
        self.assertEquals((STARTEVENT, bin_item), (ev, item))

        ev, item = events.next()
        self.assertEquals((None, dict(name='a', type=UINT16)),
                          (ev, item))

        ev, item = events.next()
        self.assertEquals((None, dict(name='b', type=UINT16)),
                          (ev, item))

        ev, item = events.next()
        self.assertEquals((ENDEVENT, bin_item), (ev, item))


    def test_map_events_nested(self):
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.dataio import UINT16
        from hwp5.bintype import bintype_map_events

        bin_item = dict(type=self.NestedStruct)
        events = bintype_map_events(bin_item)

        ev, item = events.next()
        self.assertEquals((STARTEVENT, bin_item), (ev, item))

        ev, item = events.next()
        self.assertEquals((None, dict(name='a', type=UINT16)),
                          (ev, item))

        ev, item = events.next()
        self.assertEquals((STARTEVENT, dict(name='s', type=self.BasicStruct)),
                          (ev, item))

        ev, item = events.next()
        self.assertEquals((None, dict(name='a', type=UINT16)),
                          (ev, item))

        ev, item = events.next()
        self.assertEquals((None, dict(name='b', type=UINT16)),
                          (ev, item))

        ev, item = events.next()
        self.assertEquals((ENDEVENT, dict(name='s', type=self.BasicStruct)),
                          (ev, item))

        ev, item = events.next()
        self.assertEquals((None, dict(name='b', type=UINT16)),
                          (ev, item))

        ev, item = events.next()
        self.assertEquals((ENDEVENT, bin_item), (ev, item))

    def test_map_struct_with_xarray(self):
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.dataio import StructType
        from hwp5.dataio import X_ARRAY
        from hwp5.dataio import ref_member
        from hwp5.dataio import UINT16
        from hwp5.bintype import bintype_map_events

        xarray_type = X_ARRAY(self.BasicStruct, ref_member('count'))
        class StructWithXArray(object):
            __metaclass__ = StructType
            @staticmethod
            def attributes():
                yield UINT16, 'count'
                yield dict(type=xarray_type,
                           name='items')
        bin_item = dict(type=StructWithXArray)
        events = bintype_map_events(bin_item)
        self.assertEquals((STARTEVENT,
                           bin_item),
                          events.next())
        self.assertEquals((None,
                           dict(type=UINT16, name='count')),
                          events.next())
        self.assertEquals((STARTEVENT,
                           dict(type=xarray_type,
                                name='items')),
                          events.next())
        self.assertEquals((STARTEVENT,
                           dict(type=self.BasicStruct)),
                          events.next())
        self.assertEquals((None,
                           dict(type=UINT16, name='a')),
                          events.next())
        self.assertEquals((None,
                           dict(type=UINT16, name='b')),
                          events.next())
        self.assertEquals((ENDEVENT,
                           dict(type=self.BasicStruct)),
                          events.next())
        self.assertEquals((ENDEVENT,
                           dict(type=xarray_type,
                                name='items')),
                          events.next())
        self.assertEquals((ENDEVENT,
                           bin_item),
                          events.next())

    def test_filter_with_version(self):
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.dataio import StructType
        from hwp5.dataio import UINT16
        from hwp5.bintype import bintype_map_events
        from hwp5.bintype import filter_with_version

        class StructWithVersion(object):
            __metaclass__ = StructType

            @classmethod
            def attributes(cls):
                yield UINT16, 'a'
                yield dict(name='b', type=UINT16, version=(5, 0, 2, 4))

        bin_item = dict(type=StructWithVersion)

        events = bintype_map_events(bin_item)
        events = filter_with_version(events, (5, 0, 0, 0))

        self.assertEquals((STARTEVENT, bin_item), events.next())
        self.assertEquals((None, dict(name='a', type=UINT16)), events.next())
        self.assertEquals((ENDEVENT, bin_item), events.next())

        events = bintype_map_events(bin_item)
        events = filter_with_version(events, (5, 0, 2, 4))
        self.assertEquals((STARTEVENT, bin_item), events.next())
        self.assertEquals((None, dict(name='a', type=UINT16)), events.next())
        self.assertEquals((None, dict(name='b', type=UINT16,
                                      version=(5, 0, 2, 4))), events.next())
        self.assertEquals((ENDEVENT, bin_item), events.next())

    def test_resolve_xarray(self):
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.dataio import StructType
        from hwp5.dataio import X_ARRAY
        from hwp5.dataio import UINT16
        from hwp5.dataio import ref_member
        from hwp5.bintype import bintype_map_events
        from hwp5.bintype import static_to_mutable
        from hwp5.bintype import resolve_types

        xarray_type = X_ARRAY(UINT16, ref_member('a'))
        class StructWithXArray(object):
            __metaclass__ = StructType

            @staticmethod
            def attributes():
                yield UINT16, 'a'
                yield dict(name='b',
                           type=xarray_type)

        static_events = bintype_map_events(dict(type=StructWithXArray))
        static_events = list(static_events)

        events = static_to_mutable(iter(static_events))
        events = resolve_types(events, dict())
        ev, struct = events.next()
        self.assertEquals((STARTEVENT, struct), (ev, struct))
        self.assertEquals((None,
                           dict(name='a', type=UINT16)),
                          events.next())
        struct['value'] = dict(a=0)
        self.assertEquals((STARTEVENT,
                           dict(name='b',
                                count=0,
                                type=xarray_type)),
                          events.next())
        self.assertEquals((ENDEVENT,
                           dict(name='b',
                                count=0,
                                type=xarray_type)),
                          events.next())
        self.assertEquals((ENDEVENT, struct),
                          events.next())

        events = static_to_mutable(iter(static_events))
        events = resolve_types(events, dict())
        ev, struct = events.next()
        self.assertEquals((STARTEVENT, struct), (ev, struct))
        self.assertEquals((None,
                           dict(name='a', type=UINT16)),
                          events.next())
        struct['value'] = dict(a=1)
        self.assertEquals((STARTEVENT,
                           dict(name='b',
                                count=1,
                                type=xarray_type)),
                          events.next())
        self.assertEquals((None, dict(type=UINT16)),
                          events.next())
        self.assertEquals((ENDEVENT,
                           dict(name='b',
                                count=1,
                                type=xarray_type)),
                          events.next())
        self.assertEquals((ENDEVENT, struct),
                          events.next())

        events = static_to_mutable(iter(static_events))
        events = resolve_types(events, dict())
        ev, struct = events.next()
        self.assertEquals((STARTEVENT, struct), (ev, struct))
        self.assertEquals((None,
                           dict(name='a', type=UINT16)),
                          events.next())
        struct['value'] = dict(a=2)
        self.assertEquals((STARTEVENT,
                           dict(name='b',
                                count=2,
                                type=xarray_type)),
                          events.next())
        self.assertEquals((None, dict(type=UINT16)),
                          events.next())
        self.assertEquals((None, dict(type=UINT16)),
                          events.next())
        self.assertEquals((ENDEVENT,
                           dict(name='b',
                                count=2,
                                type=xarray_type)),
                          events.next())
        self.assertEquals((ENDEVENT, struct),
                          events.next())

    def test_resolve_xarray_struct(self):
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.dataio import StructType
        from hwp5.dataio import X_ARRAY
        from hwp5.dataio import UINT16
        from hwp5.dataio import ref_member
        from hwp5.bintype import bintype_map_events
        from hwp5.bintype import static_to_mutable
        from hwp5.bintype import resolve_types

        xarray_type = X_ARRAY(self.BasicStruct, ref_member('a'))
        class StructWithXArray(object):
            __metaclass__ = StructType

            @staticmethod
            def attributes():
                yield UINT16, 'a'
                yield dict(name='b',
                           type=xarray_type)

        static_events = bintype_map_events(dict(type=StructWithXArray))
        static_events = list(static_events)

        events = static_to_mutable(iter(static_events))
        events = resolve_types(events, dict())
        ev, struct = events.next()
        self.assertEquals((STARTEVENT, struct), (ev, struct))
        self.assertEquals((None,
                           dict(name='a', type=UINT16)),
                          events.next())
        struct['value'] = dict(a=0)
        self.assertEquals((STARTEVENT,
                           dict(name='b', count=0, type=xarray_type)),
                          events.next())
        self.assertEquals((ENDEVENT,
                           dict(name='b', count=0, type=xarray_type)),
                          events.next())
        self.assertEquals((ENDEVENT, struct),
                          events.next())

        events = static_to_mutable(iter(static_events))
        events = resolve_types(events, dict())
        ev, struct = events.next()
        self.assertEquals((STARTEVENT, struct), (ev, struct))
        self.assertEquals((None,
                           dict(name='a', type=UINT16)),
                          events.next())
        struct['value'] = dict(a=1)
        self.assertEquals((STARTEVENT,
                           dict(name='b', count=1, type=xarray_type)),
                          events.next())
        self.assertEquals((STARTEVENT, dict(type=self.BasicStruct)),
                           events.next())
        self.assertEquals((None, dict(name='a', type=UINT16)),
                          events.next())
        self.assertEquals((None, dict(name='b', type=UINT16)),
                          events.next())
        self.assertEquals((ENDEVENT, dict(type=self.BasicStruct)),
                           events.next())
        self.assertEquals((ENDEVENT,
                           dict(name='b', count=1, type=xarray_type)),
                          events.next())
        self.assertEquals((ENDEVENT, struct),
                          events.next())

        events = static_to_mutable(iter(static_events))
        events = resolve_types(events, dict())
        ev, struct = events.next()
        self.assertEquals((STARTEVENT, struct), (ev, struct))
        self.assertEquals((None,
                           dict(name='a', type=UINT16)),
                          events.next())
        struct['value'] = dict(a=2)
        self.assertEquals((STARTEVENT,
                           dict(name='b', count=2, type=xarray_type)),
                          events.next())
        self.assertEquals((STARTEVENT, dict(type=self.BasicStruct)),
                           events.next())
        self.assertEquals((None, dict(name='a', type=UINT16)),
                          events.next())
        self.assertEquals((None, dict(name='b', type=UINT16)),
                          events.next())
        self.assertEquals((ENDEVENT, dict(type=self.BasicStruct)),
                           events.next())
        self.assertEquals((STARTEVENT, dict(type=self.BasicStruct)),
                           events.next())
        self.assertEquals((None, dict(name='a', type=UINT16)),
                          events.next())
        self.assertEquals((None, dict(name='b', type=UINT16)),
                          events.next())
        self.assertEquals((ENDEVENT, dict(type=self.BasicStruct)),
                           events.next())
        self.assertEquals((ENDEVENT,
                           dict(name='b', count=2, type=xarray_type)),
                          events.next())
        self.assertEquals((ENDEVENT, struct),
                          events.next())

    def test_resolve_conditional_simple(self):
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.dataio import StructType
        from hwp5.dataio import UINT16
        from hwp5.bintype import bintype_map_events
        from hwp5.bintype import static_to_mutable
        from hwp5.bintype import resolve_types

        def if_a_is_1(context, values):
            return values['a'] == 1

        class StructWithCondition(object):
            __metaclass__ = StructType

            @staticmethod
            def attributes():
                yield UINT16, 'a'
                yield dict(name='b', type=UINT16, condition=if_a_is_1)
                yield UINT16, 'c'

        static_events = bintype_map_events(dict(type=StructWithCondition))
        static_events = list(static_events)

        events = static_to_mutable(iter(static_events))
        events = resolve_types(events, dict())
        ev, struct = events.next()
        self.assertEquals(STARTEVENT, ev)
        self.assertEquals(StructWithCondition, struct['type'])
        self.assertEquals((None, dict(name='a', type=UINT16)),
                          events.next())
        struct['value'] = dict(a=0)
        self.assertEquals((None, dict(name='c', type=UINT16)),
                          events.next())
        self.assertEquals((ENDEVENT,
                           dict(struct,
                                value=dict(a=0))),
                          events.next())

        events = static_to_mutable(iter(static_events))
        events = resolve_types(events, dict())
        ev, struct = events.next()
        self.assertEquals(STARTEVENT, ev)
        self.assertEquals(StructWithCondition, struct['type'])
        self.assertEquals((None, dict(name='a', type=UINT16)),
                          events.next())
        struct['value'] = dict(a=1)
        self.assertEquals((None,
                           dict(name='b',
                                type=UINT16)),
                          events.next())
        self.assertEquals((None, dict(name='c', type=UINT16)),
                          events.next())
        self.assertEquals((ENDEVENT,
                           dict(struct,
                                value=dict(a=1))),
                          events.next())

    def test_resolve_conditional_struct(self):
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.dataio import StructType
        from hwp5.dataio import UINT16
        from hwp5.bintype import bintype_map_events
        from hwp5.bintype import static_to_mutable
        from hwp5.bintype import resolve_types

        def if_a_is_1(context, values):
            return values['a'] == 1

        class StructWithCondition(object):
            __metaclass__ = StructType

            @staticmethod
            def attributes():
                yield UINT16, 'a'
                yield dict(name='b', type=self.BasicStruct, condition=if_a_is_1)
                yield UINT16, 'c'

        static_events = bintype_map_events(dict(type=StructWithCondition))
        static_events = list(static_events)

        events = static_to_mutable(iter(static_events))
        events = resolve_types(events, dict())
        ev, struct = events.next()
        self.assertEquals(STARTEVENT, ev)
        self.assertEquals(StructWithCondition, struct['type'])
        self.assertEquals((None, dict(name='a', type=UINT16)),
                          events.next())
        struct['value'] = dict(a=0)
        self.assertEquals((None, dict(name='c', type=UINT16)),
                          events.next())
        self.assertEquals((ENDEVENT,
                           dict(struct,
                                value=dict(a=0))),
                          events.next())

        events = static_to_mutable(iter(static_events))
        events = resolve_types(events, dict())
        ev, struct = events.next()
        self.assertEquals(STARTEVENT, ev)
        self.assertEquals(StructWithCondition, struct['type'])
        self.assertEquals((None, dict(name='a', type=UINT16)),
                          events.next())
        struct['value'] = dict(a=1)
        self.assertEquals((STARTEVENT,
                           dict(name='b',
                                type=self.BasicStruct)),
                          events.next())
        self.assertEquals((None, dict(name='a', type=UINT16)),
                          events.next())
        self.assertEquals((None, dict(name='b', type=UINT16)),
                          events.next())
        self.assertEquals((ENDEVENT,
                           dict(name='b',
                                type=self.BasicStruct)),
                          events.next())
        self.assertEquals((None, dict(name='c', type=UINT16)),
                          events.next())
        self.assertEquals((ENDEVENT,
                           dict(struct,
                                value=dict(a=1))),
                          events.next())

    def test_resolve_selective_type(self):
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.dataio import StructType
        from hwp5.dataio import SelectiveType
        from hwp5.dataio import ref_member
        from hwp5.dataio import UINT16
        from hwp5.bintype import bintype_map_events
        from hwp5.bintype import static_to_mutable
        from hwp5.bintype import resolve_types

        class StructWithSelectiveType(object):
            __metaclass__ = StructType

            @staticmethod
            def attributes():
                yield UINT16, 'a'
                yield dict(name='b',
                           type=SelectiveType(ref_member('a'),
                                              {0: UINT16,
                                               1: self.BasicStruct}))
                yield UINT16, 'c'

        static_events = bintype_map_events(dict(type=StructWithSelectiveType))
        static_events = list(static_events)

        events = static_to_mutable(iter(static_events))
        events = resolve_types(events, dict())
        ev, struct = events.next()
        self.assertEquals(STARTEVENT, ev)
        self.assertEquals(StructWithSelectiveType, struct['type'])
        self.assertEquals((None, dict(name='a', type=UINT16)),
                          events.next())
        struct['value'] = dict(a=0)
        self.assertEquals((None, dict(name='b', type=UINT16)),
                          events.next())
        self.assertEquals((None, dict(name='c', type=UINT16)),
                          events.next())
        self.assertEquals((ENDEVENT,
                           dict(struct,
                                value=dict(a=0))),
                          events.next())

        events = static_to_mutable(iter(static_events))
        events = resolve_types(events, dict())
        ev, struct = events.next()
        self.assertEquals(STARTEVENT, ev)
        self.assertEquals(StructWithSelectiveType, struct['type'])
        self.assertEquals((None, dict(name='a', type=UINT16)),
                          events.next())
        struct['value'] = dict(a=1)
        self.assertEquals((STARTEVENT,
                           dict(name='b',
                                type=self.BasicStruct)),
                          events.next())
        self.assertEquals((None, dict(name='a', type=UINT16)),
                          events.next())
        self.assertEquals((None, dict(name='b', type=UINT16)),
                          events.next())
        self.assertEquals((ENDEVENT,
                           dict(name='b',
                                type=self.BasicStruct)),
                          events.next())
        self.assertEquals((None, dict(name='c', type=UINT16)),
                          events.next())
        self.assertEquals((ENDEVENT,
                           dict(struct,
                                value=dict(a=1))),
                          events.next())

    def test_resolve_values_from_stream(self):
        assertEquals = self.assertEquals
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.dataio import UINT16
        from hwp5.bintype import bintype_map_events
        from hwp5.bintype import resolve_values_from_stream

        from StringIO import StringIO
        stream = StringIO('\x00\x01\x00\x02')
        resolve_values = resolve_values_from_stream(stream)

        bin_item = dict(type=self.BasicStruct)
        events = bintype_map_events(bin_item)
        events = resolve_values(events)

        assertEquals((STARTEVENT, bin_item), events.next())
        assertEquals((None,
                      dict(name='a', type=UINT16, bin_offset=0, value=256)),
                     events.next())
        assertEquals((None,
                      dict(name='b', type=UINT16, bin_offset=2, value=512)),
                     events.next())
        assertEquals((ENDEVENT, bin_item), events.next())

        from hwp5.dataio import StructType
        from hwp5.dataio import BSTR
        class StructWithBSTR(object):
            __metaclass__ = StructType

            @staticmethod
            def attributes():
                yield BSTR, 'name'

        stream = StringIO('\x02\x00\x00\x01\x00\x02')
        resolve_values = resolve_values_from_stream(stream)
        bin_item = dict(type=StructWithBSTR)
        events = bintype_map_events(bin_item)
        events = resolve_values(events)
        assertEquals((STARTEVENT, bin_item), events.next())
        assertEquals((None,
                      dict(name='name', type=BSTR, bin_offset=0,
                           value=u'\u0100\u0200')),
                     events.next())
        assertEquals((ENDEVENT, bin_item), events.next())

        from hwp5.binmodel import ParaTextChunks
        class StructWithParaTextChunks(object):
            __metaclass__ = StructType

            @staticmethod
            def attributes():
                yield ParaTextChunks, 'texts'

        stream = StringIO('\x20\x00\x21\x00\x22\x00')
        resolve_values = resolve_values_from_stream(stream)
        bin_item = dict(type=StructWithParaTextChunks)
        events = bintype_map_events(bin_item)
        events = resolve_values(events)
        assertEquals((STARTEVENT, bin_item), events.next())
        assertEquals((None,
                      dict(name='texts', type=ParaTextChunks,
                           bin_offset=0,
                           value=[((0, 3), u'\u0020\u0021\u0022')])),
                     events.next())
        assertEquals((ENDEVENT, bin_item), events.next())

    def test_collect_values(self):
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.dataio import UINT16
        from hwp5.bintype import bintype_map_events
        from hwp5.bintype import resolve_values_from_stream
        from hwp5.bintype import collect_values
        from StringIO import StringIO

        stream = StringIO('\x01\x00\x01\x01\x02\x01\x02\x00')
        resolve_values = resolve_values_from_stream(stream)

        bin_item = dict(type=self.NestedStruct)
        events = bintype_map_events(bin_item)
        events = resolve_values(events)
        events = collect_values(events)

        a = dict(name='a', type=UINT16, bin_offset=0, value=1)
        s_a = dict(name='a', type=UINT16, bin_offset=2, value=0x101)
        s_b = dict(name='b', type=UINT16, bin_offset=4, value=0x102)
        b = dict(name='b', type=UINT16, bin_offset=6, value=2)
        s = dict(name='s', type=self.BasicStruct,
                 value=dict(a=0x101, b=0x102))
        x = dict(type=self.NestedStruct,
                 value=dict(a=1, s=dict(a=0x101, b=0x102), b=2))
        self.assertEquals((STARTEVENT, bin_item), events.next())
        self.assertEquals((None, a), events.next())
        self.assertEquals((STARTEVENT, dict(name='s', type=self.BasicStruct,
                                            value=dict())),
                           events.next())
        self.assertEquals((None, s_a), events.next())
        self.assertEquals((None, s_b), events.next())
        self.assertEquals((ENDEVENT, s), events.next())
        self.assertEquals((None, b), events.next())
        self.assertEquals((ENDEVENT, x), events.next())


class TestReadEvents(TestCase):
    def test_struct_with_condition(self):
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.dataio import UINT16
        from hwp5.dataio import StructType
        from hwp5.bintype import read_type_events
        from StringIO import StringIO

        def if_a_is_1(context, values):
            return values['a'] == 1

        class StructWithCondition(object):
            __metaclass__ = StructType

            @staticmethod
            def attributes():
                yield UINT16, 'a'
                yield dict(name='b', type=UINT16, condition=if_a_is_1)
                yield UINT16, 'c'

        context = dict()

        # if a = 0
        stream = StringIO('\x00\x00\x02\x00')
        events = read_type_events(StructWithCondition, context, stream)
        a = dict(name='a', type=UINT16, value=0, bin_offset=0)
        c = dict(name='c', type=UINT16, value=2, bin_offset=2)
        self.assertEquals((STARTEVENT, dict(type=StructWithCondition,
                                           value=dict())),
                          events.next())
        self.assertEquals((None, a), events.next())
        self.assertEquals((None, c), events.next())
        self.assertEquals((ENDEVENT, dict(type=StructWithCondition,
                                          value=dict(a=0, c=2))),
                          events.next())
        self.assertEquals('', stream.read())

        # if a = 1
        stream = StringIO('\x01\x00\x0f\x00\x02\x00')
        events = read_type_events(StructWithCondition, context, stream)
        a = dict(name='a', type=UINT16, value=1, bin_offset=0)
        b = dict(name='b', type=UINT16, value=0xf, bin_offset=2)
        c = dict(name='c', type=UINT16, value=2, bin_offset=4)
        x = dict(type=StructWithCondition,
                 value=dict(a=1, b=0xf, c=2))
        self.assertEquals((STARTEVENT, dict(type=StructWithCondition,
                                            value={})),
                          events.next())
        self.assertEquals((None, a), events.next())
        self.assertEquals((None, b), events.next())
        self.assertEquals((None, c), events.next())
        self.assertEquals((ENDEVENT, x), events.next())
        self.assertEquals('', stream.read())

########NEW FILE########
__FILENAME__ = test_dataio
# -*- coding: utf-8 -*-
from unittest import TestCase

from hwp5.dataio import INT32, ARRAY, N_ARRAY, BSTR, Struct
class TestArray(TestCase):
    def test_new(self):
        t1 = ARRAY(INT32, 3)
        t2 = ARRAY(INT32, 3)
        assert t1 is t2

        assert N_ARRAY(INT32, INT32) is N_ARRAY(INT32, INT32)

    def test_BSTR(self):
        assert type(BSTR(u'abc')) is unicode

    def test_hello(self):
        assert INT32.basetype is int

    def test_slots(self):
        a = INT32()
        self.assertRaises(Exception, setattr, a, 'randomattr', 1)

class TestTypedAttributes(TestCase):

    def test_typed_struct_attributes(self):
        from hwp5.dataio import typed_struct_attributes
        class SomeRandomStruct(Struct):
            @staticmethod
            def attributes():
                yield INT32, 'a'
                yield BSTR, 'b'
                yield ARRAY(INT32, 3), 'c'

        attributes = dict(a=1, b=u'abc', c=(4,5,6))
        typed_attributes = typed_struct_attributes(SomeRandomStruct, attributes, dict())
        typed_attributes = list(typed_attributes)
        expected = [dict(name='a', type=INT32, value=1),
                    dict(name='b', type=BSTR, value='abc'),
                    dict(name='c', type=ARRAY(INT32, 3), value=(4,5,6))]
        self.assertEquals(expected, typed_attributes)

    def test_typed_struct_attributes_inherited(self):
        from hwp5.dataio import typed_struct_attributes
        class Hello(Struct):
            @staticmethod
            def attributes():
                yield INT32, 'a'

        class Hoho(Hello):
            @staticmethod
            def attributes():
                yield BSTR, 'b'

        attributes = dict(a=1, b=u'abc', c=(2, 2))
        result = typed_struct_attributes(Hoho, attributes, dict())
        result = list(result)
        expected = [dict(name='a', type=INT32, value=1),
                    dict(name='b', type=BSTR, value='abc'),
                    dict(name='c', type=tuple, value=(2, 2))]
        self.assertEquals(expected, result)


class TestStructType(TestCase):
    def test_assign_enum_flags_name(self):
        from hwp5.dataio import StructType, Enum, Flags, UINT16
        class Foo(object):
            __metaclass__ = StructType
            bar = Enum()
            baz = Flags(UINT16)
        self.assertEquals('bar', Foo.bar.__name__)
        self.assertEquals(Foo, Foo.bar.scoping_struct)
        self.assertEquals('baz', Foo.baz.__name__)

    def test_parse_members(self):
        from hwp5.dataio import StructType
        from hwp5.dataio import UINT8, UINT16, UINT32

        class A(object):
            __metaclass__ = StructType
            @classmethod
            def attributes(cls):
                yield UINT8, 'uint8'
                yield UINT16, 'uint16'
                yield UINT32, 'uint32'

        values = dict(uint8=8, uint16=16, uint32=32)
        def getvalue(member):
            return values[member['name']]
        context = dict()
        result = list(A.parse_members(context, getvalue))
        self.assertEquals([dict(name='uint8', type=UINT8, value=8),
                           dict(name='uint16', type=UINT16, value=16),
                           dict(name='uint32', type=UINT32, value=32)], result)

    def test_parse_members_condition(self):
        from hwp5.dataio import StructType
        from hwp5.dataio import UINT8, UINT16, UINT32

        def uint32_is_32(context, values):
            return values['uint32'] == 32
        class A(object):
            __metaclass__ = StructType
            @classmethod
            def attributes(cls):
                yield UINT8, 'uint8'
                yield UINT16, 'uint16'
                yield UINT32, 'uint32'
                yield dict(type=UINT32, name='extra', condition=uint32_is_32)

        values = dict(uint8=8, uint16=16, uint32=32, extra=666)
        def getvalue(member):
            return values[member['name']]
        context = dict()
        result = list(A.parse_members(context, getvalue))
        self.assertEquals([dict(name='uint8', type=UINT8, value=8),
                           dict(name='uint16', type=UINT16, value=16),
                           dict(name='uint32', type=UINT32, value=32),
                           dict(name='extra', type=UINT32, value=666,
                                condition=uint32_is_32)],
                          result)

    def test_parse_members_empty(self):
        from hwp5.dataio import StructType

        class A(object):
            __metaclass__ = StructType

        value = dict()
        def getvalue(member):
            return value[member['name']]
        context = dict()
        result = list(A.parse_members_with_inherited(context, getvalue))
        self.assertEquals([], result)

    def test_parse_members_inherited(self):
        from hwp5.dataio import StructType
        from hwp5.dataio import UINT8, UINT16, UINT32
        from hwp5.dataio import INT8, INT16, INT32

        class A(object):
            __metaclass__ = StructType
            @classmethod
            def attributes(cls):
                yield UINT8, 'uint8'
                yield UINT16, 'uint16'
                yield UINT32, 'uint32'

        class B(A):
            @classmethod
            def attributes(cls):
                yield INT8, 'int8'
                yield INT16, 'int16'
                yield INT32, 'int32'

        value = dict(uint8=8, uint16=16, uint32=32,
                     int8=-1, int16=-16, int32=-32)
        def getvalue(member):
            return value[member['name']]
        context = dict()
        result = list(B.parse_members_with_inherited(context, getvalue))
        self.assertEquals([dict(name='uint8', type=UINT8, value=8),
                           dict(name='uint16', type=UINT16, value=16),
                           dict(name='uint32', type=UINT32, value=32),
                           dict(name='int8', type=INT8, value=-1),
                           dict(name='int16', type=INT16, value=-16),
                           dict(name='int32', type=INT32, value=-32)],
                          result)


class TestEnumType(TestCase):
    def test_enum(self):
        from hwp5.dataio import EnumType
        from hwp5.dataio import Enum
        Foo = EnumType('Foo', (int,), dict(items=['a', 'b', 'c'], moreitems=dict(d=1, e=4)))

        self.assertRaises(AttributeError, getattr, Foo, 'items')
        self.assertRaises(AttributeError, getattr, Foo, 'moreitems')

        # class members
        self.assertEquals(0, Foo.a)
        self.assertEquals(1, Foo.b)
        self.assertEquals(2, Foo.c)
        self.assertEquals(1, Foo.d)
        self.assertEquals(4, Foo.e)
        self.assertTrue(isinstance(Foo.a, Foo))

        # same instances
        self.assertTrue(Foo(0) is Foo(0))
        self.assertTrue(Foo(0) is Foo.a)

        # not an instance of int
        self.assertTrue(Foo(0) is not 0)

        # instance names
        self.assertEquals('a', Foo.a.name)
        self.assertEquals('b', Foo.b.name)

        # aliases
        self.assertEquals('b', Foo.d.name)
        self.assertTrue(Foo.b is Foo.d)

        # repr
        self.assertEquals('Foo.a', repr(Foo(0)))
        self.assertEquals('Foo.b', repr(Foo(1)))
        self.assertEquals('Foo.e', repr(Foo(4)))

        # frozen attribute set
        self.assertRaises(AttributeError, setattr, Foo(0), 'bar', 0)
        import sys
        if sys.platform.startswith('java'):  # Jython 2.5.3
            self.assertRaises(TypeError, setattr, Foo(0), 'name', 'a')
        else:
            self.assertRaises(AttributeError, setattr, Foo(0), 'name', 'a')

        # undefined value
        #self.assertRaises(ValueError, Foo, 5)

        # undefined value: warning but not error
        undefined = Foo(5)
        self.assertTrue(isinstance(undefined, Foo))
        self.assertEquals(None, undefined.name)
        self.assertEquals('Foo(5)', repr(undefined))

        # can't define anymore
        self.assertRaises(TypeError, Foo, 5, 'f')

        # duplicate names
        self.assertRaises(Exception, Enum, 'a', a=1)


class TestFlags(TestCase):
    def test_parse_args(self):
        from hwp5.dataio import _parse_flags_args
        x = list(_parse_flags_args([0, 1, long, 'bit01']))
        bit01 = ('bit01', (0, 1, long))
        self.assertEquals([bit01], x)

        x = list(_parse_flags_args([2, 3, 'bit23']))
        bit23 = ('bit23', (2, 3, int))
        self.assertEquals([bit23], x)

        x = list(_parse_flags_args([4, long, 'bit4']))
        bit4 = ('bit4', (4, 4, long))
        self.assertEquals([bit4], x)

        x = list(_parse_flags_args([5, 'bit5']))
        bit5 = ('bit5', (5, 5, int))

        x = list(_parse_flags_args([0, 1, long, 'bit01',
                                    2, 3, 'bit23', 
                                    4, long, 'bit4',
                                    5, 'bit5']))
        self.assertEquals([bit01, bit23, bit4, bit5], x)

    def test_basetype(self):
        from hwp5.dataio import UINT32
        from hwp5.dataio import Flags
        MyFlags = Flags(UINT32)
        self.assertEquals(UINT32, MyFlags.basetype)

    def test_bitfields(self):
        from hwp5.dataio import UINT32
        from hwp5.dataio import Flags
        from hwp5.dataio import Enum
        MyEnum = Enum(a=1, b=2)
        MyFlags = Flags(UINT32, 0, 1, 'field0',
                                2, 4, MyEnum, 'field2')
        bitfields = MyFlags.bitfields
        f = bitfields['field0']
        self.assertEquals((0, 1, int),
                          (f.lsb, f.msb, f.valuetype))
        f = bitfields['field2']
        self.assertEquals((2, 4, MyEnum),
                          (f.lsb, f.msb, f.valuetype))

    @property
    def ByteFlags(self):
        from hwp5.dataio import BYTE
        from hwp5.dataio import Flags
        return Flags(BYTE,
                     0, 3, 'low',
                     4, 7, 'high')

    def test_dictvalue(self):
        flags = self.ByteFlags(0xf0)
        self.assertEquals(dict(low=0, high=0xf),
                          flags.dictvalue())


class TestReadStruct(TestCase):

    def test_read_parse_error(self):
        from hwp5.dataio import Struct
        from hwp5.dataio import INT16
        from hwp5.dataio import ParseError

        class Foo(Struct):

            def attributes():
                yield INT16, 'a'
            attributes = staticmethod(attributes)

        from StringIO import StringIO
        stream = StringIO()

        from hwp5.bintype import read_type
        record = dict()
        context = dict(record=record)
        try:
            read_type(Foo, context, stream)
            assert False, 'ParseError expected'
        except ParseError, e:
            self.assertEquals(Foo, e.binevents[0][1]['type'])
            self.assertEquals('a', e.binevents[-1][1]['name'])
            self.assertEquals(0, e.offset)


class TestBSTR(TestCase):

    def test_read(self):
        from hwp5.dataio import BSTR

        from StringIO import StringIO
        f = StringIO('\x03\x00' + u'가나다'.encode('utf-16le'))

        s = BSTR.read(f)
        self.assertEquals(u'가나다', s)

        pua = u'\ub098\ub78f\u302e\ub9d0\u302f\uebd4\ubbf8\u302e'
        pua_utf16le = pua.encode('utf-16le')
        f = StringIO(chr(len(pua)) + '\x00' + pua_utf16le)

        jamo = BSTR.read(f)
        expected = u'\ub098\ub78f\u302e\ub9d0\u302f\u110a\u119e\ubbf8\u302e'
        self.assertEquals(expected, jamo)


class TestDecodeUTF16LEPUA(TestCase):

    def test_decode(self):
        from hwp5.dataio import decode_utf16le_with_hypua

        expected = u'가나다'
        bytes = expected.encode('utf-16le')
        u = decode_utf16le_with_hypua(bytes)
        self.assertEquals(expected, u)

########NEW FILE########
__FILENAME__ = test_distdoc
# -*- coding: utf-8 -*-
from binascii import b2a_hex
from hashlib import sha1
from StringIO import StringIO
import zlib

from hwp5.filestructure import Hwp5DistDoc
from hwp5.distdoc import decode_head_to_sha1
from hwp5.distdoc import decode_head_to_key
from hwp5.distdoc import decrypt_tail
from hwp5.recordstream import read_record
from hwp5.tagids import HWPTAG_PARA_HEADER
import hwp5.distdoc

from hwp5_tests.test_filestructure import TestBase


class TestHwp5DistDocFunctions(TestBase):

    hwp5file_name = 'viewtext.hwp'
    password_sha1 = sha1('12345').digest()

    @property
    def hwp5distdoc(self):
        return Hwp5DistDoc(self.olestg)

    @property
    def section(self):
        return self.hwp5distdoc['ViewText']['Section0']

    def test_distdoc_decode_head_to_sha1(self):
        expected = b2a_hex(self.password_sha1).upper().encode('utf-16le')
        self.assertEquals(expected, decode_head_to_sha1(self.section.head()))

    def test_distdoc_decode_head_to_key(self):
        section = self.section
        expected = b2a_hex(self.password_sha1).upper().encode('utf-16le')[:16]
        self.assertEquals(expected, decode_head_to_key(section.head()))
        self.assertEquals(expected, section.head_key())

    def test_distdoc_decrypt_tail(self):
        section = self.section

        key = section.head_key()
        tail = section.tail()
        try:
            decrypted = decrypt_tail(key, tail)
        except NotImplementedError, e:
            if e.message == 'aes128ecb_decrypt':
                # skip this test
                return
            raise
        uncompressed = zlib.decompress(decrypted, -15)
        record = read_record(StringIO(uncompressed), 0)
        self.assertEquals(0, record['level'])
        self.assertEquals(HWPTAG_PARA_HEADER, record['tagid'])
        self.assertEquals(22, record['size'])

        self.assertEquals(390, len(uncompressed))

    def test_distdoc_decode(self):
        section = self.section

        try:
            stream = hwp5.distdoc.decode(section.wrapped.open())
        except NotImplementedError, e:
            if e.message == 'aes128ecb_decrypt':
                # skip this test
                return
            raise
        stream = hwp5.filestructure.uncompress(stream)
        record = read_record(stream, 0)
        self.assertEquals(0, record['level'])
        self.assertEquals(HWPTAG_PARA_HEADER, record['tagid'])
        self.assertEquals(22, record['size'])

########NEW FILE########
__FILENAME__ = test_filestructure
# -*- coding: utf-8 -*-
from unittest import TestCase
import os.path
import shutil

from hwp5 import filestructure as FS
from hwp5.utils import cached_property
import test_ole


class TestBase(test_ole.TestBase):

    @cached_property
    def hwp5file_base(self):
        return FS.Hwp5FileBase(self.olestg)

    @cached_property
    def hwp5file_fs(self):
        return FS.Hwp5File(self.olestg)

    hwp5file = hwp5file_fs

    @cached_property
    def docinfo(self):
        return self.hwp5file.docinfo

    @cached_property
    def bodytext(self):
        return self.hwp5file.bodytext

    @cached_property
    def viewtext(self):
        return self.hwp5file.viewtext


class TestModuleFunctions(TestBase):

    def test_is_hwp5file(self):
        assert FS.is_hwp5file(self.hwp5file_path)
        nonole_filename = self.get_fixture_file('nonole.txt')
        assert not FS.is_hwp5file(nonole_filename)


class TestHwp5FileBase(TestBase):

    @cached_property
    def hwp5file_base(self):
        from hwp5.filestructure import Hwp5FileBase
        return Hwp5FileBase(self.olestg)

    def test_create_with_filename(self):
        from hwp5.filestructure import Hwp5FileBase
        hwp5file = Hwp5FileBase(self.hwp5file_path)
        self.assertTrue('FileHeader' in hwp5file)

    def test_create_with_nonole(self):
        from hwp5.errors import InvalidHwp5FileError
        from hwp5.filestructure import Hwp5FileBase
        nonole = self.get_fixture_file('nonole.txt')
        self.assertRaises(InvalidHwp5FileError, Hwp5FileBase, nonole)

    def test_create_with_nonhwp5_storage(self):
        from hwp5.errors import InvalidHwp5FileError
        from hwp5.storage.fs import FileSystemStorage
        from hwp5.filestructure import Hwp5FileBase
        stg = FileSystemStorage(self.get_fixture_file('nonhwp5stg'))
        self.assertRaises(InvalidHwp5FileError, Hwp5FileBase, stg)

    def test_item_is_hwpfileheader(self):
        from hwp5.filestructure import HwpFileHeader
        fileheader = self.hwp5file_base['FileHeader']
        self.assertTrue(isinstance(fileheader, HwpFileHeader))

    def test_header(self):
        from hwp5.filestructure import HwpFileHeader
        header = self.hwp5file_base.header
        self.assertTrue(isinstance(header, HwpFileHeader))


class TestHwp5DistDocStream(TestBase):

    hwp5file_name = 'viewtext.hwp'

    @cached_property
    def jscriptversion(self):
        from hwp5.filestructure import Hwp5DistDocStream
        return Hwp5DistDocStream(self.hwp5file_base['Scripts']['JScriptVersion'],
                                 self.hwp5file_base.header.version)

    def test_head_record(self):
        from hwp5.tagids import HWPTAG_DISTRIBUTE_DOC_DATA
        record = self.jscriptversion.head_record()
        self.assertEquals(HWPTAG_DISTRIBUTE_DOC_DATA, record['tagid'])

    def test_head_record_stream(self):
        from hwp5.tagids import HWPTAG_DISTRIBUTE_DOC_DATA
        from hwp5.importhelper import importjson
        simplejson = importjson()
        stream = self.jscriptversion.head_record_stream()
        record = simplejson.load(stream)
        self.assertEquals(HWPTAG_DISTRIBUTE_DOC_DATA, record['tagid'])

        # stream should have been exausted
        self.assertEquals('', stream.read(1))

    def test_head(self):
        head = self.jscriptversion.head()
        self.assertEquals(256, len(head))

    def test_head_stream(self):
        head_stream = self.jscriptversion.head_stream()
        self.assertEquals(256, len(head_stream.read()))

    def test_tail(self):
        tail = self.jscriptversion.tail()
        self.assertEquals(16, len(tail))

    def test_tail_stream(self):
        tail_stream = self.jscriptversion.tail_stream()
        self.assertEquals(16, len(tail_stream.read()))


class TestHwp5DistDicStorage(TestBase):

    hwp5file_name = 'viewtext.hwp'

    @cached_property
    def scripts(self):
        from hwp5.filestructure import Hwp5DistDocStorage
        return Hwp5DistDocStorage(self.olestg['Scripts'])

    def test_scripts_other_formats(self):
        from hwp5.filestructure import Hwp5DistDocStream
        jscriptversion = self.scripts['JScriptVersion']
        self.assertTrue(isinstance(jscriptversion, Hwp5DistDocStream))


class TestHwp5DistDoc(TestBase):

    hwp5file_name = 'viewtext.hwp'

    @cached_property
    def hwp5distdoc(self):
        from hwp5.filestructure import Hwp5DistDoc
        return Hwp5DistDoc(self.olestg)

    def test_conversion_for(self):
        from hwp5.filestructure import Hwp5DistDocStorage
        conversion = self.hwp5distdoc.resolve_conversion_for('Scripts')
        self.assertTrue(conversion is Hwp5DistDocStorage)

    def test_getitem(self):
        from hwp5.filestructure import Hwp5DistDocStorage
        self.assertTrue(isinstance(self.hwp5distdoc['Scripts'],
                                   Hwp5DistDocStorage))
        self.assertTrue(isinstance(self.hwp5distdoc['ViewText'],
                                   Hwp5DistDocStorage))


class TestCompressedStorage(TestBase):
    def test_getitem(self):
        from hwp5.storage import is_storage, is_stream
        stg = FS.CompressedStorage(self.olestg['BinData'])
        self.assertTrue(is_storage(stg))

        item = stg['BIN0002.jpg']
        self.assertTrue(is_stream(item))

        f = item.open()
        try:
            data = f.read()
            self.assertEquals('\xff\xd8\xff\xe0', data[0:4])
            self.assertEquals(15895, len(data))
        finally:
            f.close()


class TestHwp5Compression(TestBase):

    @cached_property
    def hwp5file_compressed(self):
        return FS.Hwp5Compression(self.hwp5file_base)

    @cached_property
    def docinfo(self):
        return self.hwp5file_compressed['DocInfo'].open()

    @cached_property
    def bodytext(self):
        return self.hwp5file_compressed['BodyText']

    @cached_property
    def scripts(self):
        return self.hwp5file_compressed['Scripts']

    def test_docinfo_uncompressed(self):
        from hwp5.recordstream import read_record
        from hwp5.tagids import HWPTAG_DOCUMENT_PROPERTIES
        record = read_record(self.docinfo, 0)
        self.assertEquals(HWPTAG_DOCUMENT_PROPERTIES, record['tagid'])

    def test_bodytext_uncompressed(self):
        from hwp5.recordstream import read_record
        from hwp5.tagids import HWPTAG_PARA_HEADER
        record = read_record(self.bodytext['Section0'].open(), 0)
        self.assertEquals(HWPTAG_PARA_HEADER, record['tagid'])

    def test_scripts_version(self):
        hwp5file = self.hwp5file_compressed
        self.assertFalse(hwp5file.header.flags.distributable)

        JScriptVersion = self.scripts['JScriptVersion'].open().read()
        self.assertEquals(8, len(JScriptVersion))


class TestHwp5File(TestBase):

    def test_init_should_accept_string_path(self):
        from hwp5.filestructure import Hwp5File
        hwp5file = Hwp5File(self.hwp5file_path)
        self.assertTrue(hwp5file['FileHeader'] is not None)

    def test_init_should_accept_olestorage(self):
        from hwp5.filestructure import Hwp5File
        hwp5file = Hwp5File(self.olestg)
        self.assertTrue(hwp5file['FileHeader'] is not None)

    def test_init_should_accept_fs(self):
        from hwp5.filestructure import Hwp5File
        from hwp5.storage import unpack
        from hwp5.storage.fs import FileSystemStorage
        outpath = 'test_init_should_accept_fs'
        if os.path.exists(outpath):
            shutil.rmtree(outpath)
        os.mkdir(outpath)
        unpack(self.olestg, outpath)
        fs = FileSystemStorage(outpath)
        hwp5file = Hwp5File(fs)
        fileheader = hwp5file['FileHeader']
        self.assertTrue(fileheader is not None)
        self.assertEquals((5, 0, 1, 7), fileheader.version)

    def test_fileheader(self):
        fileheader = self.hwp5file.header
        self.assertEquals((5, 0, 1, 7), fileheader.version)
        self.assertTrue(fileheader.flags.compressed)

    def test_getitem_storage_classes(self):
        hwp5file = self.hwp5file
        self.assertTrue(isinstance(hwp5file['BinData'], FS.StorageWrapper))
        self.assertTrue(isinstance(hwp5file['BodyText'], FS.Sections))
        self.assertTrue(isinstance(hwp5file['Scripts'], FS.StorageWrapper))

    def test_prv_text(self):
        prvtext = self.hwp5file['PrvText']
        from hwp5.filestructure import PreviewText
        self.assertTrue(isinstance(prvtext, PreviewText))
        expected = '한글 2005 예제 파일입니다.'
        self.assertEquals(expected, str(prvtext)[0:len(expected)])

    def test_distdoc_layer_inserted(self):
        #from hwp5.storage import ExtraItemStorage
        #self.hwp5file_name = 'viewtext.hwp'
        #self.assertTrue('Section0.tail' in ExtraItemStorage(self.viewtext))
        pass

    def test_unpack(self):
        from hwp5.storage import ExtraItemStorage
        from hwp5.storage import unpack
        outpath = 'test_unpack'
        if os.path.exists(outpath):
            shutil.rmtree(outpath)
        os.mkdir(outpath)
        unpack(ExtraItemStorage(self.hwp5file), outpath)

        self.assertTrue(os.path.exists('test_unpack/_05HwpSummaryInformation'))
        self.assertTrue(os.path.exists('test_unpack/BinData/BIN0002.jpg'))
        self.assertTrue(os.path.exists('test_unpack/BinData/BIN0002.png'))
        self.assertTrue(os.path.exists('test_unpack/BinData/BIN0003.png'))
        self.assertTrue(os.path.exists('test_unpack/BodyText/Section0'))
        self.assertTrue(os.path.exists('test_unpack/DocInfo'))
        self.assertTrue(os.path.exists('test_unpack/DocOptions/_LinkDoc'))
        self.assertTrue(os.path.exists('test_unpack/FileHeader'))
        self.assertTrue(os.path.exists('test_unpack/PrvImage'))
        self.assertTrue(os.path.exists('test_unpack/PrvText'))
        self.assertTrue(os.path.exists('test_unpack/PrvText.utf8'))
        self.assertTrue(os.path.exists('test_unpack/Scripts/DefaultJScript'))
        self.assertTrue(os.path.exists('test_unpack/Scripts/JScriptVersion'))

    def test_if_hwp5file_contains_other_formats(self):
        from hwp5.storage import ExtraItemStorage
        stg = ExtraItemStorage(self.hwp5file)
        self.assertTrue('PrvText.utf8' in list(stg))

    def test_resolve_conversion_for_bodytext(self):
        self.assertTrue(self.hwp5file.resolve_conversion_for('BodyText'))

    def test_docinfo(self):
        hwp5file = self.hwp5file
        self.assertTrue(isinstance(hwp5file.docinfo, FS.VersionSensitiveItem))
        docinfo = hwp5file.docinfo.open()
        try:
            data = docinfo.read()
        finally:
            docinfo.close()

        import zlib
        docinfo = self.olestg['DocInfo']
        self.assertEquals(zlib.decompress(docinfo.open().read(), -15), data)

    def test_bodytext(self):
        bodytext = self.hwp5file.bodytext
        self.assertTrue(isinstance(bodytext, FS.Sections))
        self.assertEquals(['Section0'], list(bodytext))


class TestSections(TestBase):

    @property
    def sections(self):
        from hwp5.filestructure import Sections
        return Sections(self.hwp5file.stg['BodyText'], self.hwp5file.header.version)


class TestGeneratorReader(TestCase):
    def test_generator_reader(self):
        def data():
            yield 'Hello world'
            yield 'my name is'
            yield 'gen'
            yield 'reader'

        from hwp5.filestructure import GeneratorReader

        f = GeneratorReader(data())
        self.assertEquals('Hel', f.read(3))
        self.assertEquals('lo wor', f.read(6))
        self.assertEquals('ldmy ', f.read(5))
        self.assertEquals('name isgenre', f.read(12))
        self.assertEquals('ader', f.read())

        f = GeneratorReader(data())
        self.assertEquals('Hel', f.read(3))
        self.assertEquals('lo wor', f.read(6))
        self.assertEquals('ldmy ', f.read(5))
        self.assertEquals('name isgenreader', f.read())

        f = GeneratorReader(data())
        self.assertEquals('Hel', f.read(3))
        self.assertEquals('lo wor', f.read(6))
        self.assertEquals('ldmy ', f.read(5))
        self.assertEquals('name isgenreader', f.read(1000))


from hwp5.utils import cached_property


class TestUncompress(TestCase):

    @cached_property
    def original_data(self):
        import os
        return os.urandom(16384)

    @cached_property
    def compressed_data(self):
        import zlib
        return zlib.compress(self.original_data)

    def test_incremental_decode(self):
        compressed_data = self.compressed_data

        from hwp5.filestructure import ZLibIncrementalDecoder
        dec = ZLibIncrementalDecoder(wbits=-15)
        data = dec.decode(compressed_data[2:2048])
        data += dec.decode(compressed_data[2048:2048 + 1024])
        data += dec.decode(compressed_data[2048 + 1024:2048 + 1024 + 4096])
        data += dec.decode(compressed_data[2048 + 1024 + 4096:], True)

        self.assertEquals(self.original_data, data)

    def test_uncompress(self):
        from StringIO import StringIO

        from hwp5.filestructure import uncompress_gen
        gen = uncompress_gen(StringIO(self.compressed_data[2:]))
        self.assertEquals(self.original_data, ''.join(gen))

        #print '-----'

        from hwp5.filestructure import uncompress

        f = uncompress(StringIO(self.compressed_data[2:]))
        g = StringIO(self.original_data)

        self.assertEquals(f.read(2048), g.read(2048))
        self.assertEquals(f.read(1024), g.read(1024))
        self.assertEquals(f.read(4096), g.read(4096))
        self.assertEquals(f.read(), g.read())

########NEW FILE########
__FILENAME__ = test_hwp5html
# -*- coding: utf-8 -*-
import os
import os.path
import shutil
import test_xmlmodel


class TestBase(test_xmlmodel.TestBase):

    def make_base_dir(self):
        base_dir = self.id()
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)
        os.mkdir(base_dir)
        return base_dir


class HtmlConvTest(TestBase):

    @property
    def xslt(self):
        from hwp5.plat import get_xslt
        return get_xslt()

    @property
    def xhwp5_path(self):
        return self.id() + '.xhwp5'

    def create_xhwp5(self):
        xhwp5_path = self.xhwp5_path
        xhwp5_file = file(xhwp5_path, 'w')
        try:
            self.hwp5file.xmlevents(embedbin=False).dump(xhwp5_file)
        finally:
            xhwp5_file.close()
        return xhwp5_path

    def test_generate_css_file(self):
        base_dir = self.make_base_dir()
        css_path = os.path.join(base_dir, 'styles.css')

        xhwp5_path = self.create_xhwp5()
        from hwp5.hwp5html import generate_css_file
        generate_css_file(self.xslt, xhwp5_path, css_path)

        self.assertTrue(os.path.exists(css_path))
        #with file(css_path) as f:
        #    print f.read()

    def test_generate_html_file(self):
        base_dir = self.make_base_dir()
        html_path = os.path.join(base_dir, 'index.html')

        xhwp5_path = self.create_xhwp5()
        from hwp5.hwp5html import generate_html_file
        generate_html_file(self.xslt, xhwp5_path, html_path)

        self.assertTrue(os.path.exists(html_path))
        #with file(html_path) as f:
        #    print f.read()

    def test_extract_bindata_dir(self):
        base_dir = self.make_base_dir()
        hwp5file = self.hwp5file

        bindata_dir = os.path.join(base_dir, 'bindata')

        from hwp5.hwp5html import extract_bindata_dir
        extract_bindata_dir(hwp5file, bindata_dir)

        bindata_stg = hwp5file['BinData']

        from hwp5.storage.fs import FileSystemStorage
        self.assertEquals(set(bindata_stg),
                          set(FileSystemStorage(bindata_dir)))

    def test_extract_bindata_dir_without_bindata(self):
        self.hwp5file_name = 'charshape.hwp'
        base_dir = self.make_base_dir()
        hwp5file = self.hwp5file

        bindata_dir = os.path.join(base_dir, 'bindata')

        from hwp5.hwp5html import extract_bindata_dir
        extract_bindata_dir(hwp5file, bindata_dir)
        self.assertFalse(os.path.exists(bindata_dir))

########NEW FILE########
__FILENAME__ = test_hwp5odt
# -*- coding: utf-8 -*-
from unittest import TestCase

class ResourcesTest(TestCase):

    def test_pkg_resources_filename_fallback(self):
        from hwp5.importhelper import pkg_resources_filename_fallback
        fname = pkg_resources_filename_fallback('hwp5', 'xsl/odt/styles.xsl')
        import os.path
        self.assertTrue(os.path.exists(fname))

    def test_hwp5_resources_filename(self):
        from hwp5.hwp5odt import hwp5_resources_filename
        styles_xsl = hwp5_resources_filename('xsl/odt/styles.xsl')
        import os.path
        self.assertTrue(os.path.exists(styles_xsl))

########NEW FILE########
__FILENAME__ = test_odtxsl
# -*- coding: utf-8 -*-
from __future__ import with_statement
from unittest import TestCase


def example(filename):
    from fixtures import get_fixture_path
    from hwp5.xmlmodel import Hwp5File
    path = get_fixture_path(filename)
    return Hwp5File(path)


class TestPrecondition(TestCase):
    def test_example(self):
        assert example('linespacing.hwp') is not None


class TestODTPackageConverter(TestCase):

    @property
    def odt_path(self):
        return self.id() + '.odt'

    @property
    def convert(self):
        from hwp5 import plat
        from hwp5.hwp5odt import ODTPackageConverter

        xslt = plat.get_xslt()
        assert xslt is not None, 'no XSLT implementation is available'
        relaxng = plat.get_relaxng()
        return ODTPackageConverter(xslt, relaxng)

    def test_convert_bindata(self):
        hwp5file = example('sample-5017.hwp')
        try:
            f = hwp5file['BinData']['BIN0002.jpg'].open()
            try:
                data1 = f.read()
            finally:
                f.close()

            convert = self.convert
            with convert.prepare():
                convert.convert_to(hwp5file, self.odt_path)
        finally:
            hwp5file.close()

        from zipfile import ZipFile
        zf = ZipFile(self.odt_path)
        data2 = zf.read('bindata/BIN0002.jpg')

        self.assertEquals(data1, data2)

########NEW FILE########
__FILENAME__ = test_ole
# -*- coding: utf-8 -*-
from unittest import TestCase
from mixin_olestg import OleStorageTestMixin


class TestBase(TestCase):

    hwp5file_name = 'sample-5017.hwp'

    def get_fixture_file(self, filename):
        from fixtures import get_fixture_path
        return get_fixture_path(filename)

    def open_fixture(self, filename, *args, **kwargs):
        from fixtures import open_fixture
        return open_fixture(filename, *args, **kwargs)

    @property
    def hwp5file_path(self):
        return self.get_fixture_file(self.hwp5file_name)

    @property
    def olestg(self):
        from hwp5.storage.ole import OleStorage
        return OleStorage(self.hwp5file_path)


class TestOleStorage(TestCase, OleStorageTestMixin):

    def setUp(self):
        from hwp5.storage.ole import OleStorage
        self.OleStorage = OleStorage

########NEW FILE########
__FILENAME__ = test_plat_javax_transform
# -*- coding: utf-8 -*-
from __future__ import with_statement
import unittest
from mixin_xslt import XsltTestMixin


class TestPlatJavaxTransform(unittest.TestCase, XsltTestMixin):

    def test_is_enabled(self):
        from hwp5.plat import javax_transform
        import sys

        if sys.platform.startswith('java'):
            self.assertTrue(javax_transform.is_enabled())
        else:
            self.assertFalse(javax_transform.is_enabled())

    def setUp(self):
        from hwp5.plat import javax_transform
        if javax_transform.is_enabled():
            self.xslt = javax_transform.xslt
            self.xslt_compile = javax_transform.xslt_compile
        else:
            self.xslt = None
            self.xslt_compile = None

########NEW FILE########
__FILENAME__ = test_plat_jython_poifs
# -*- coding: utf-8 -*-
from unittest import TestCase
from mixin_olestg import OleStorageTestMixin


class TestOleStorageJythonPoiFS(TestCase, OleStorageTestMixin):

    def setUp(self):
        from hwp5.plat import jython_poifs
        if jython_poifs.is_enabled():
            self.OleStorage = jython_poifs.OleStorage

########NEW FILE########
__FILENAME__ = test_plat_lxml
# -*- coding: utf-8 -*-
from __future__ import with_statement
import unittest
from mixin_xslt import XsltTestMixin
from mixin_relaxng import RelaxNGTestMixin


class TestPlatLxml(unittest.TestCase, XsltTestMixin, RelaxNGTestMixin):

    def test_is_enabled(self):
        from hwp5.plat import _lxml

        try:
            import lxml; lxml
        except ImportError:
            self.assertFalse(_lxml.is_enabled())
        else:
            self.assertTrue(_lxml.is_enabled())

    def setUp(self):
        from hwp5.plat import _lxml
        if _lxml.is_enabled():
            self.xslt = _lxml.xslt
            self.xslt_compile = _lxml.xslt_compile
            self.relaxng = _lxml.relaxng
            self.relaxng_compile = _lxml.relaxng_compile
        else:
            self.xslt = None
            self.xslt_compile = None
            self.relaxng = None
            self.relaxng_compile = None

########NEW FILE########
__FILENAME__ = test_plat_olefileio
# -*- coding: utf-8 -*-
from unittest import TestCase
from mixin_olestg import OleStorageTestMixin


class TestOleStorageOleFileIO(TestCase, OleStorageTestMixin):

    def setUp(self):
        from hwp5.plat import olefileio
        if olefileio.is_enabled():
            self.OleStorage = olefileio.OleStorage

########NEW FILE########
__FILENAME__ = test_plat_uno
# -*- coding: utf-8 -*-
from __future__ import with_statement
import unittest
from mixin_xslt import XsltTestMixin
from mixin_olestg import OleStorageTestMixin


class TestPlatUNO(unittest.TestCase, XsltTestMixin, OleStorageTestMixin):

    def setUp(self):
        from hwp5.plat import _uno
        if _uno.is_enabled():
            self.xslt = _uno.xslt
            self.xslt_compile = None
            self.OleStorage = _uno.OleStorage
        else:
            self.xslt = None
            self.xslt_compile = None
            self.OleStorage = None

########NEW FILE########
__FILENAME__ = test_plat_xmllint
# -*- coding: utf-8 -*-
from __future__ import with_statement
import unittest
from mixin_relaxng import RelaxNGTestMixin


class TestPlatXmlLint(unittest.TestCase, RelaxNGTestMixin):

    relaxng = None
    relaxng_compile = None

    def setUp(self):
        from hwp5.plat import xmllint
        if xmllint.is_enabled():
            self.relaxng = xmllint.relaxng

########NEW FILE########
__FILENAME__ = test_plat_xsltproc
# -*- coding: utf-8 -*-
from __future__ import with_statement
import unittest
from mixin_xslt import XsltTestMixin


class TestPlatXsltProc(unittest.TestCase, XsltTestMixin):
    
    xslt = None
    xslt_compile = None

    def setUp(self):
        from hwp5.plat import xsltproc
        if xsltproc.is_enabled():
            self.xslt = xsltproc.xslt

########NEW FILE########
__FILENAME__ = test_recordstream
# -*- coding: utf-8 -*-

import test_filestructure
from hwp5 import recordstream as RS
from hwp5.utils import cached_property
from hwp5.importhelper import importjson

class TestBase(test_filestructure.TestBase):

    @property
    def hwp5file_rec(self):
        return RS.Hwp5File(self.olestg)

    hwp5file = hwp5file_rec


class TestRecord(TestBase):

    def test_read_record(self):
        from hwp5.recordstream import read_record
        from hwp5.tagids import HWPTAG_DOCUMENT_PROPERTIES
        docinfo_stream = self.hwp5file['DocInfo']

        record = read_record(docinfo_stream.open(), 0)
        self.assertEquals(HWPTAG_DOCUMENT_PROPERTIES, record['tagid'])

    def test_dump_record(self):
        from hwp5.recordstream import dump_record
        from hwp5.recordstream import read_record
        docinfo_stream = self.hwp5file['DocInfo']
        record = read_record(docinfo_stream.open(), 0)
        from StringIO import StringIO
        stream = StringIO()
        dump_record(stream, record)
        stream.seek(0)
        record2 = read_record(stream, 0)
        self.assertEquals(record2, record)


class TestRecordStream(TestBase):

    @cached_property
    def docinfo(self):
        from hwp5.recordstream import RecordStream
        return RecordStream(self.hwp5file_fs['DocInfo'],
                            self.hwp5file_fs.header.version)

    def test_records(self):
        self.assertEquals(67, len(list(self.docinfo.records())))

    def test_records_kwargs_treegroup(self):
        from hwp5.tagids import HWPTAG_ID_MAPPINGS
        records = self.docinfo.records(treegroup=1)
        self.assertEquals(66, len(records))
        self.assertEquals(HWPTAG_ID_MAPPINGS, records[0]['tagid'])

        from hwp5.tagids import HWPTAG_DOCUMENT_PROPERTIES
        records = self.docinfo.records(treegroup=0)
        self.assertEquals(1, len(records))
        self.assertEquals(HWPTAG_DOCUMENT_PROPERTIES, records[0]['tagid'])

        records = self.bodytext.section(0).records(treegroup=5)
        self.assertEquals(26, records[0]['seqno'])
        self.assertEquals(37, len(records))

    def test_record(self):
        record = self.docinfo.record(0)
        self.assertEquals(0, record['seqno'])

        record = self.docinfo.record(10)
        self.assertEquals(10, record['seqno'])

    def test_records_treegrouped(self):
        groups = self.docinfo.records_treegrouped()
        document_properties_treerecords = groups.next()
        self.assertEquals(1, len(document_properties_treerecords))
        idmappings_treerecords = groups.next()
        self.assertEquals(66, len(idmappings_treerecords))

        from hwp5.tagids import HWPTAG_PARA_HEADER
        section = self.bodytext.section(0)
        for group_idx, records in enumerate(section.records_treegrouped()):
            #print group_idx, records[0]['seqno'], len(records)
            self.assertEquals(HWPTAG_PARA_HEADER, records[0]['tagid'])

    def test_records_treegrouped_as_iterable(self):
        groups = self.docinfo.records_treegrouped(group_as_list=False)
        group = groups.next()
        self.assertFalse(isinstance(group, list))

    def test_records_treegroped_as_list(self):
        groups = self.docinfo.records_treegrouped()
        group = groups.next()
        self.assertTrue(isinstance(group, list))

    def test_records_treegroup(self):
        from hwp5.tagids import HWPTAG_ID_MAPPINGS
        records = self.docinfo.records_treegroup(1)
        self.assertEquals(66, len(records))
        self.assertEquals(HWPTAG_ID_MAPPINGS, records[0]['tagid'])

        from hwp5.tagids import HWPTAG_DOCUMENT_PROPERTIES
        records = self.docinfo.records_treegroup(0)
        self.assertEquals(1, len(records))
        self.assertEquals(HWPTAG_DOCUMENT_PROPERTIES, records[0]['tagid'])

        records = self.bodytext.section(0).records_treegroup(5)
        self.assertEquals(26, records[0]['seqno'])
        self.assertEquals(37, len(records))


class TestHwp5File(TestBase):

    def test_if_hwp5file_contains_other_formats(self):
        from hwp5.storage import ExtraItemStorage
        stg = ExtraItemStorage(self.hwp5file)
        self.assertTrue('DocInfo.records' in list(stg))

    def test_docinfo(self):
        docinfo = self.hwp5file.docinfo
        self.assertTrue(isinstance(docinfo, RS.RecordStream))
        records = list(docinfo.records())
        self.assertEquals(67, len(records))

    def test_bodytext(self):
        from hwp5.storage import ExtraItemStorage
        bodytext = self.hwp5file.bodytext
        self.assertTrue(isinstance(bodytext, RS.Sections))
        stg = ExtraItemStorage(bodytext)
        self.assertEquals(['Section0', 'Section0.records'], list(stg))


class TestJson(TestBase):
    def test_record_to_json(self):
        from hwp5.recordstream import record_to_json
        simplejson = importjson()
        record = self.hwp5file.docinfo.records().next()
        json = record_to_json(record)
        jsonobject = simplejson.loads(json)
        self.assertEquals(16, jsonobject['tagid'])
        self.assertEquals(0, jsonobject['level'])
        self.assertEquals(26, jsonobject['size'])
        self.assertEquals(['01 00 01 00 01 00 01 00 01 00 01 00 01 00 00 00',
                           '00 00 07 00 00 00 05 00 00 00'],
                          jsonobject['payload'])
        self.assertEquals(0, jsonobject['seqno'])
        self.assertEquals('HWPTAG_DOCUMENT_PROPERTIES', jsonobject['tagname'])

    def test_generate_simplejson_dumps(self):
        simplejson = importjson()
        records_json = self.hwp5file.docinfo.records_json()
        json = ''.join(records_json.generate())

        jsonobject = simplejson.loads(json)
        self.assertEquals(67, len(jsonobject))

########NEW FILE########
__FILENAME__ = test_storage
# -*- coding: utf-8 -*-
from unittest import TestCase
from hwp5.storage import StorageWrapper

class TestStorageWrapper(TestCase):

    @property
    def storage(self):
        from StringIO import StringIO
        return dict(FileHeader=StringIO('fileheader'),
                    BinData={'BIN0001.jpg': StringIO('bin0001.jpg')})

    def test_iter(self):
        stg = StorageWrapper(self.storage)
        expected = ['FileHeader', 'BinData']
        self.assertEquals(sorted(expected), sorted(iter(stg)))

    def test_getitem(self):
        stg = StorageWrapper(self.storage)
        self.assertEquals('fileheader', stg['FileHeader'].read())
        self.assertEquals('bin0001.jpg', stg['BinData']['BIN0001.jpg'].read())

########NEW FILE########
__FILENAME__ = test_treeop
# -*- coding: utf-8 -*-
from unittest import TestCase

class Test_ancestors_from_level(TestCase):

    def test_ancestors_from_level(self):

        from hwp5.treeop import prefix_ancestors_from_level

        level_prefixed = [
            (0, 'a0'),
            (0, 'b0'),   # sibling
            (1, 'b0-a1'), # child
            (2, 'b0-a1-a2'), #child
            (1, 'b0-b1'), # jump to parent level
            (2, 'b0-b1-b2'), # child
            (0, 'c0'), # jump to grand-parent level
        ]

        ancestors_prefixed = prefix_ancestors_from_level(level_prefixed)
        result = list((list(ancestors), item)
                      for ancestors, item in ancestors_prefixed)

        self.assertEquals(result.pop(0), ([None], 'a0'))
        self.assertEquals(result.pop(0), ([None], 'b0'))
        self.assertEquals(result.pop(0), ([None, 'b0'], 'b0-a1'))
        self.assertEquals(result.pop(0), ([None, 'b0', 'b0-a1'], 'b0-a1-a2'))
        self.assertEquals(result.pop(0), ([None, 'b0'], 'b0-b1'))
        self.assertEquals(result.pop(0), ([None, 'b0', 'b0-b1'], 'b0-b1-b2'))
        self.assertEquals(result.pop(0), ([None], 'c0'))

    def test_ancestors_from_level_from_nonzero_baselevel(self):
        from hwp5.treeop import prefix_ancestors_from_level
        level_prefixed = [
            (7, 'a0'), # baselevel 7
            (8, 'a0-a1'),
            (9, 'a0-a1-a2'),
            (7, 'b0'),
        ]
        ancestors_prefixed = prefix_ancestors_from_level(level_prefixed)
        result = list((list(ancestors), item)
                      for ancestors, item in ancestors_prefixed)
        self.assertEquals(result.pop(0), ([None], 'a0'))
        self.assertEquals(result.pop(0), ([None, 'a0'], 'a0-a1'))
        self.assertEquals(result.pop(0), ([None, 'a0', 'a0-a1'], 'a0-a1-a2'))
        self.assertEquals(result.pop(0), ([None], 'b0'))

    def test_ancestors_from_level_fails_at_level_below_baselevel(self):
        from hwp5.treeop import prefix_ancestors_from_level
        level_prefixed = [
            (7, 'a7'), # baselevel 7
            (8, 'a7-a8'),
            (9, 'a7-a8-a9'),
            (6, 'b7'), # level below the base level
        ]
        try:
            list(prefix_ancestors_from_level(level_prefixed))
            # TODO: 현재로서는 스택에 기본으로 root_item을 넣어놓는 구현 방식 때문에
            # base level 바로 아래 level은 에러가 나지 않음
            #self.fail('exception expected')
        except:
            pass

        level_prefixed = [
            (7, 'a7'), # baselevel 7
            (8, 'a7-a8'),
            (9, 'a7-a8-a9'),
            (5, 'b7'), # level below the base level
        ]
        try:
            list(prefix_ancestors_from_level(level_prefixed))
            self.fail('exception expected')
        except:
            pass

    def test_ancestors_from_level_assert_fails_at_invalid_level_jump(self):
        from hwp5.treeop import prefix_ancestors_from_level

        level_prefixed = [
            (0, 'a0'),
            (2, 'a0-a1-a2'), # invalid level jump
        ]
        ancestors_prefixed = prefix_ancestors_from_level(level_prefixed)
        try:
            list(ancestors_prefixed)
            self.fail('assert fails expected')
        except:
            pass


class TestTreeEvents(TestCase):
    def test_tree_events(self):
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.treeop import build_subtree
        from hwp5.treeop import tree_events
        event_prefixed_items = [ (STARTEVENT, 'a'), (ENDEVENT, 'a') ]
        rootitem, childs = build_subtree(iter(event_prefixed_items[1:]))
        self.assertEquals('a', rootitem)
        self.assertEquals(0, len(childs))

        event_prefixed_items = [ (STARTEVENT, 'a'), (STARTEVENT, 'b'), (ENDEVENT, 'b'), (ENDEVENT, 'a') ]
        self.assertEquals( ('a', [('b', [])]), build_subtree(iter(event_prefixed_items[1:])))

        event_prefixed_items = [
            (STARTEVENT, 'a'),
                (STARTEVENT, 'b'),
                    (STARTEVENT, 'c'), (ENDEVENT, 'c'),
                    (STARTEVENT, 'd'), (ENDEVENT, 'd'),
                (ENDEVENT, 'b'),
            (ENDEVENT, 'a')]

        result = build_subtree(iter(event_prefixed_items[1:]))
        self.assertEquals( ('a', [('b', [('c', []), ('d', [])])]), result)

        back = list(tree_events(*result))
        self.assertEquals(event_prefixed_items, back)


class TestSubevents(TestCase):

    def test_iter_subevents(self):
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.treeop import iter_subevents

        events = iter([(STARTEVENT, 'a'), (ENDEVENT, 'a')])
        events.next()
        subevents = iter_subevents(events)
        self.assertEquals([(ENDEVENT, 'a')], list(subevents))

        events = iter([(STARTEVENT, 'a'),
                       (STARTEVENT, 'b'),
                       (None, 'c'),
                       (ENDEVENT, 'b'),
                       (ENDEVENT, 'a')])
        events.next()
        subevents = iter_subevents(events)
        self.assertEquals([(STARTEVENT, 'b'),
                           (None, 'c'),
                           (ENDEVENT, 'b'),
                           (ENDEVENT, 'a')], list(subevents))

        events = iter([(STARTEVENT, 'a'),
                       (None, 'c'),
                       (ENDEVENT, 'a'),
                       (STARTEVENT, 'b'),
                       (None, 'd'),
                       (ENDEVENT, 'b')])
        events.next()
        subevents = iter_subevents(events)
        self.assertEquals([(None, 'c'),
                           (ENDEVENT, 'a')], list(subevents))
        self.assertEquals([(STARTEVENT, 'b'),
                           (None, 'd'),
                           (ENDEVENT, 'b')], list(events))

########NEW FILE########
__FILENAME__ = test_xmlformat
from unittest import TestCase
import logging
from hwp5.dataio import Struct
from hwp5.dataio import INT32, BSTR
from hwp5.xmlformat import element


class TestHello(TestCase):
    def test_hello(self):
        from hwp5.treeop import STARTEVENT
        from hwp5.treeop import ENDEVENT

        context = dict(logging=logging)
        class SomeStruct(Struct):
            @staticmethod
            def attributes():
                yield INT32, 'a'
                yield BSTR, 'b'
        class SomeStruct2(Struct):
            @staticmethod
            def attributes():
                yield SomeStruct, 'somestruct'
        result = element(context, (SomeStruct2, dict(somestruct=dict(a=1, b=u'b'))))
        result = list(result)
        #for x in result: x[0](*x[1:])
        expected = [
                (STARTEVENT, ('SomeStruct2', dict())),
                (STARTEVENT, ('SomeStruct', {'attribute-name': 'somestruct',
                                             'a': '1', 'b': 'b'})),
                (ENDEVENT, 'SomeStruct'),
                (ENDEVENT, 'SomeStruct2'),
                ]
        self.assertEquals(expected, result)

        result = element(context, (SomeStruct, dict(a=1, b=u'b', c=dict(foo=1))))
        result = list(result)
        #for x in result: x[0](*x[1:])
        expected = [
                (STARTEVENT, ('SomeStruct', dict(a='1', b='b'))),
                (STARTEVENT, ('dict', {'attribute-name': 'c', 'foo': '1'})),
                (ENDEVENT, 'dict'),
                (ENDEVENT, 'SomeStruct')
                ]
        self.assertEquals(expected, result)

    def test_xmlattr_uniqnames(self):
        from hwp5.xmlformat import xmlattr_uniqnames
        a = [('a', 1), ('b', 2)]
        self.assertEquals([('a', 1), ('b', 2)], list(xmlattr_uniqnames(a)))

        a = [('a', 1), ('a', 2)]
        result = xmlattr_uniqnames(a)
        self.assertRaises(Exception, list, result)


########NEW FILE########
__FILENAME__ = test_xmlmodel
# -*- coding: utf-8 -*-
from unittest import TestCase
import test_binmodel
from hwp5.utils import cached_property


class TestBase(test_binmodel.TestBase):

    @cached_property
    def hwp5file_xml(self):
        from hwp5.xmlmodel import Hwp5File
        return Hwp5File(self.olestg)

    hwp5file = hwp5file_xml


class TestXmlEvents(TestBase):

    def test_dump_quoteattr_cr(self):
        from hwp5.xmlmodel import XmlEvents
        from hwp5.importhelper import importStringIO
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.binmodel import ControlChar
        StringIO = importStringIO()
        sio = StringIO()

        context = dict()
        attrs = dict(char='\r')
        events = [(STARTEVENT, (ControlChar, attrs, context)),
                  (ENDEVENT, (ControlChar, attrs, context))]
        xmlevents = XmlEvents(iter(events))
        xmlevents.dump(sio)

        data = sio.getvalue()
        self.assertTrue('&#13;' in data)

    def test_bytechunks_quoteattr_cr(self):
        from hwp5.xmlmodel import XmlEvents
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.binmodel import ControlChar

        context = dict()
        attrs = dict(char='\r')
        item = (ControlChar, attrs, context)
        modelevents = [(STARTEVENT, item),
                       (ENDEVENT, item)]
        xmlevents = XmlEvents(iter(modelevents))
        xml = ''.join(xmlevents.bytechunks())

        self.assertTrue('&#13;' in xml)


class TestModelEventStream(TestBase):

    @cached_property
    def docinfo(self):
        from hwp5.xmlmodel import ModelEventStream
        return ModelEventStream(self.hwp5file_bin['DocInfo'],
                                self.hwp5file_bin.header.version)

    def test_modelevents(self):
        self.assertEquals(len(list(self.docinfo.models())) * 2,
                          len(list(self.docinfo.modelevents())))
        #print len(list(self.docinfo.modelevents()))


class TestDocInfo(TestBase):

    @cached_property
    def docinfo(self):
        from hwp5.xmlmodel import DocInfo
        return DocInfo(self.hwp5file_bin['DocInfo'],
                       self.hwp5file_bin.header.version)

    def test_events(self):
        events = list(self.docinfo.events())
        self.assertEquals(136, len(events))
        #print len(events)

        # without embedbin, no <text> is embedded
        self.assertTrue('<text>' not in events[4][1][1]['bindata'])

    def test_events_with_embedbin(self):
        import base64
        bindata = self.hwp5file_bin['BinData']
        events = list(self.docinfo.events(embedbin=bindata))
        self.assertTrue('<text>' in events[4][1][1]['bindata'])
        self.assertEquals(bindata['BIN0002.jpg'].open().read(),
                          base64.b64decode(events[4][1][1]
                                           ['bindata']['<text>']))


class TestSection(TestBase):

    def test_events(self):
        from hwp5.xmlmodel import Section
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.binmodel import SectionDef, PageDef
        section = Section(self.hwp5file_bin['BodyText']['Section0'],
                          self.hwp5file_bin.fileheader.version)
        events = list(section.events())
        ev, (tag, attrs, ctx) = events[0]
        self.assertEquals((STARTEVENT, SectionDef), (ev, tag))
        self.assertFalse('section-id' in attrs)

        ev, (tag, attrs, ctx) = events[1]
        self.assertEquals((STARTEVENT, PageDef), (ev, tag))

        ev, (tag, attrs, ctx) = events[2]
        self.assertEquals((ENDEVENT, PageDef), (ev, tag))

        ev, (tag, attrs, ctx) = events[-1]
        self.assertEquals((ENDEVENT, SectionDef), (ev, tag))


class TestHwp5File(TestBase):

    def test_docinfo_class(self):
        from hwp5.xmlmodel import DocInfo
        self.assertTrue(isinstance(self.hwp5file.docinfo, DocInfo))

    def test_events(self):
        list(self.hwp5file.events())

    def test_events_embedbin_without_bindata(self):
        # see issue 76: https://github.com/mete0r/pyhwp/issues/76
        self.hwp5file_name = 'parashape.hwp'  # an hwp5file without BinData
        hwp5file = self.hwp5file
        self.assertTrue('BinData' not in hwp5file)
        list(hwp5file.events(embedbin=True))

    def test_xmlevents(self):
        from hwp5.treeop import STARTEVENT
        events = iter(self.hwp5file.xmlevents())
        ev = events.next()
        self.assertEquals((STARTEVENT,
                           ('HwpDoc', dict(version='5.0.1.7'))), ev)
        list(events)

    def test_xmlevents_dump(self):
        outfile = file(self.id() + '.xml', 'w+')
        try:
            self.hwp5file.xmlevents().dump(outfile)

            outfile.seek(0)
            from xml.etree import ElementTree
            doc = ElementTree.parse(outfile)
        finally:
            outfile.close()

        self.assertEquals('HwpDoc', doc.getroot().tag)


from hwp5.xmlmodel import make_ranged_shapes, split_and_shape


class TestShapedText(TestCase):
    def test_make_shape_range(self):
        charshapes = [(0, 'A'), (4, 'B'), (6, 'C'), (10, 'D')]
        ranged_shapes = make_ranged_shapes(charshapes)
        self.assertEquals([((0, 4), 'A'), ((4, 6), 'B'), ((6, 10), 'C'),
                           ((10, 0x7fffffff), 'D')], list(ranged_shapes))

    def test_split(self):
        chunks = [((0, 3), None, 'aaa'), ((3, 6), None, 'bbb'),
                  ((6, 9), None, 'ccc'), ((9, 12), None, 'ddd')]
        charshapes = [(0, 'A'), (4, 'B'), (6, 'C'), (10, 'D')]
        shaped_chunks = split_and_shape(iter(chunks),
                                        make_ranged_shapes(charshapes))
        shaped_chunks = list(shaped_chunks)
        self.assertEquals([
            ((0, 3), ('A', None), 'aaa'),
            ((3, 4), ('A', None), 'b'),
            ((4, 6), ('B', None), 'bb'),
            ((6, 9), ('C', None), 'ccc'),
            ((9, 10), ('C', None), 'd'),
            ((10, 12), ('D', None), 'dd')],
            shaped_chunks)

        # split twice
        chunks = [((0, 112), None, 'x' * 112)]
        charshapes = [(0, 'a'), (3, 'b'), (5, 'c')]
        linesegs = [(0, 'A'), (51, 'B'), (103, 'C')]
        shaped = split_and_shape(iter(chunks), make_ranged_shapes(charshapes))
        shaped = list(shaped)
        self.assertEquals([((0, 3), ('a', None), 'xxx'),
                           ((3, 5), ('b', None), 'xx'),
                           ((5, 112), ('c', None), 'x' * 107)], shaped)
        lines = split_and_shape(iter(shaped), make_ranged_shapes(linesegs))
        lines = list(lines)
        self.assertEquals([
            ((0, 3), ('A', ('a', None)), 'xxx'),
            ((3, 5), ('A', ('b', None)), 'xx'),
            ((5, 51), ('A', ('c', None)), 'x' * (51 - 5)),
            ((51, 103), ('B', ('c', None)), 'x' * (103 - 51)),
            ((103, 112), ('C', ('c', None)), 'x' * (112 - 103))], lines)


class TestLineSeg(TestCase):
    def test_line_segmented(self):
        from hwp5.xmlmodel import line_segmented
        chunks = [((0, 3), None, 'aaa'), ((3, 6), None, 'bbb'),
                  ((6, 9), None, 'ccc'), ((9, 12), None, 'ddd')]
        linesegs = [(0, 'A'), (4, 'B'), (6, 'C'), (10, 'D')]
        lines = line_segmented(iter(chunks), make_ranged_shapes(linesegs))
        lines = list(lines)
        self.assertEquals([('A', [((0, 3), None, 'aaa'),
                                  ((3, 4), None, 'b')]),
                           ('B', [((4, 6), None, 'bb')]),
                           ('C', [((6, 9), None, 'ccc'),
                                  ((9, 10), None, 'd')]),
                           ('D', [((10, 12), None, 'dd')])], lines)


class TestDistributionBodyText(TestBase):

    hwp5file_name = 'viewtext.hwp'

    def test_issue33_missing_paralineseg(self):
        from hwp5.tagids import HWPTAG_PARA_LINE_SEG
        from hwp5.binmodel import ParaLineSeg
        section0 = self.hwp5file_bin.bodytext.section(0)
        tagids = set(model['tagid'] for model in section0.models())
        types = set(model['type'] for model in section0.models())
        self.assertTrue(HWPTAG_PARA_LINE_SEG not in tagids)
        self.assertTrue(ParaLineSeg not in types)

        from hwp5.binmodel import ParaText, ParaCharShape
        paratext = self.hwp5file_bin.bodytext.section(0).model(1)
        self.assertEquals(ParaText, paratext['type'])

        paracharshape = self.bodytext.section(0).model(2)
        self.assertEquals(ParaCharShape, paracharshape['type'])

        from hwp5.xmlmodel import merge_paragraph_text_charshape_lineseg as m
        evs = m((paratext['type'], paratext['content'], dict()),
                (paracharshape['type'], paracharshape['content'], dict()),
                None)

        # we can merge events without a problem
        list(evs)


class TestMatchFieldStartEnd(TestCase):

    def test_match_field_start_end(self):
        from hwp5 import binmodel, xmlmodel
        from fixtures import get_fixture_path

        path = get_fixture_path('match-field-start-end.dat')
        import pickle
        f = open(path, 'r')
        try:
            records = pickle.load(f)
        finally:
            f.close()

        models = binmodel.parse_models(dict(), records)
        events = xmlmodel.prefix_binmodels_with_event(dict(), models)
        events = xmlmodel.make_texts_linesegmented_and_charshaped(events)
        events = xmlmodel.make_extended_controls_inline(events)
        events = xmlmodel.match_field_start_end(events)
        events = list(events)


class TestEmbedBinData(TestBase):

    def test_embed_bindata(self):
        from hwp5.treeop import STARTEVENT, ENDEVENT
        from hwp5.binmodel import BinData
        from hwp5.xmlmodel import embed_bindata

        bindata = dict(flags=BinData.Flags(BinData.StorageType.EMBEDDING),
                       bindata=dict(storage_id=2, ext='jpg'))
        events = [(STARTEVENT, (BinData, bindata, dict())),
                  (ENDEVENT, (BinData, bindata, dict()))]
        events = list(embed_bindata(events, self.hwp5file_bin['BinData']))
        self.assertTrue('<text>' in bindata['bindata'])

########NEW FILE########
__FILENAME__ = test_hwp5_uno
# -*- coding: utf-8 -*-
from unittest import TestCase


class TestBase(TestCase):

    def get_fixture_path(self, filename):
        from hwp5_tests.fixtures import get_fixture_path
        return get_fixture_path(filename)

    def open_fixture(self, filename, *args, **kwargs):
        from hwp5_tests.fixtures import open_fixture
        return open_fixture(filename, *args, **kwargs)


class OleStorageAdapterTest(TestBase):

    def get_adapter(self):
        from unokit.services import css
        from hwp5_uno import InputStreamFromFileLike
        from hwp5_uno import OleStorageAdapter
        f = self.open_fixture('sample-5017.hwp', 'rb')
        inputstream = InputStreamFromFileLike(f)
        oless = css.embed.OLESimpleStorage(inputstream)
        return OleStorageAdapter(oless)

    def test_iter(self):
        adapter = self.get_adapter()

        self.assertTrue('FileHeader' in adapter)
        self.assertTrue('DocInfo' in adapter)
        self.assertTrue('BodyText' in adapter)

    def test_getitem(self):
        adapter = self.get_adapter()

        bodytext = adapter['BodyText']
        self.assertTrue('Section0' in bodytext)

        from hwp5.filestructure import HwpFileHeader
        from hwp5.filestructure import HWP5_SIGNATURE

        fileheader = adapter['FileHeader']
        fileheader = HwpFileHeader(fileheader)
        self.assertEquals((5, 0, 1, 7), fileheader.version)
        self.assertEquals(HWP5_SIGNATURE, fileheader.signature)

        # reopen (just being careful)
        fileheader = adapter['FileHeader']
        fileheader = HwpFileHeader(fileheader)
        self.assertEquals((5, 0, 1, 7), fileheader.version)
        self.assertEquals(HWP5_SIGNATURE, fileheader.signature)


class HwpFileFromInputStreamTest(TestBase):

    def test_basic(self):
        from unokit.adapters import InputStreamFromFileLike
        from hwp5_uno import HwpFileFromInputStream
        with self.open_fixture('sample-5017.hwp', 'rb') as f:
            inputstream = InputStreamFromFileLike(f)
            hwpfile = HwpFileFromInputStream(inputstream)
            self.assertEquals((5, 0, 1, 7), hwpfile.fileheader.version)


class StorageFromInputStreamTest(TestBase):

    def test_basic(self):
        import uno
        from unokit.adapters import InputStreamFromFileLike
        from hwp5_uno import StorageFromInputStream
        from hwp5.hwp5odt import ODTPackage

        zipname = self.id()+'.zip'

        pkg = ODTPackage(zipname)
        try:
            from StringIO import StringIO
            data = StringIO('hello')
            pkg.insert_stream(data, 'abc.txt', 'text/plain')
        finally:
            pkg.close()

        with file(zipname, 'rb') as f:
            inputstream = InputStreamFromFileLike(f, dontclose=True)
            storage = StorageFromInputStream(inputstream)
            try:
                self.assertTrue(uno.getTypeByName('com.sun.star.embed.XStorage')
                                in storage.Types)
                self.assertEquals(set(['abc.txt']), set(storage.ElementNames))
            finally:
                storage.dispose()


class TypedetectTest(TestBase):
    def test_basic(self):
        from unokit.adapters import InputStreamFromFileLike
        from hwp5_uno import inputstream_is_hwp5file
        from hwp5_uno import typedetect
        with self.open_fixture('sample-5017.hwp', 'rb') as f:
            inputstream = InputStreamFromFileLike(f, dontclose=True)
            self.assertTrue(inputstream_is_hwp5file(inputstream))
            self.assertEquals('hwp5', typedetect(inputstream))


class LoadHwp5FileTest(TestBase):

    def get_paragraphs(self, text):
        import unokit.util
        return unokit.util.enumerate(text)

    def get_text_portions(self, paragraph):
        import unokit.util
        return unokit.util.enumerate(paragraph)

    def get_text_contents(self, text_portion):
        import unokit.util
        if hasattr(text_portion, 'createContentEnumeration'):
            xenum = text_portion.createContentEnumeration('com.sun.star.text.TextContent')
            for text_content in unokit.util.iterate(xenum):
                yield text_content

    def test_basic(self):
        from unokit.services import css
        import unokit.util
        from hwp5.xmlmodel import Hwp5File
        from hwp5_uno import load_hwp5file_into_doc

        desktop = css.frame.Desktop()
        doc = desktop.loadComponentFromURL('private:factory/swriter', '_blank',
                                           0, tuple())
        hwp5path = self.get_fixture_path('sample-5017.hwp')
        hwp5file = Hwp5File(hwp5path)

        load_hwp5file_into_doc(hwp5file, doc)

        text = doc.getText()

        paragraphs = list(self.get_paragraphs(text))

        p = paragraphs[0]
        text_portions = list(self.get_text_portions(p))
        tp = text_portions[0]
        self.assertEquals('Text', tp.TextPortionType)
        self.assertEquals(u'한글 ', tp.String)

        p = paragraphs[-1]
        tp = list(self.get_text_portions(p))[-1]
        self.assertEquals('Frame', tp.TextPortionType)
        tc = list(self.get_text_contents(tp))[-1]
        self.assertTrue('com.sun.star.drawing.GraphicObjectShape' in
                        tc.SupportedServiceNames)

        table = paragraphs[6]
        self.assertTrue('com.sun.star.text.TextTable' in
                        table.SupportedServiceNames)

        drawpage = doc.getDrawPage()
        shapes = list(unokit.util.enumerate(drawpage))

        self.assertEquals(2, len(shapes))

        self.assertEquals(1, shapes[0].Graphic.GraphicType)
        self.assertEquals('image/jpeg', shapes[0].Graphic.MimeType)
        self.assertEquals(2, shapes[0].Bitmap.GraphicType)
        self.assertEquals('image/x-vclgraphic', shapes[0].Bitmap.MimeType)
        self.assertEquals(28254, len(shapes[0].Bitmap.DIB))
        self.assertTrue(shapes[0].GraphicURL.startswith('vnd.sun.star.GraphicObject:'))
        print shapes[0].GraphicURL
        #self.assertEquals('vnd.sun.star.GraphicObject:10000000000001F40000012C1F9CCF04',
        #                  shapes[0].GraphicURL)
        self.assertEquals(None, shapes[0].GraphicStreamURL)

        self.assertEquals(1, shapes[1].Graphic.GraphicType)
        self.assertEquals('image/png', shapes[1].Graphic.MimeType)
        self.assertEquals(2, shapes[1].Bitmap.GraphicType)
        self.assertEquals('image/x-vclgraphic', shapes[1].Bitmap.MimeType)
        self.assertEquals(374, len(shapes[1].Bitmap.DIB))
        self.assertTrue(shapes[1].GraphicURL.startswith('vnd.sun.star.GraphicObject:'))
        print shapes[1].GraphicURL
        #self.assertEquals('vnd.sun.star.GraphicObject:1000020100000010000000108F049D12',
        #                  shapes[1].GraphicURL)
        self.assertEquals(None, shapes[1].GraphicStreamURL)

########NEW FILE########
__FILENAME__ = pyhwp_dev_constants
# -*- coding: utf-8 -*-
import os
import sys


class Recipe(object):

    def __init__(self, buildout, name, options):
        options['pathsep'] = os.pathsep
        options['sep'] = os.sep
        if sys.platform == 'win32':
            options['script_py_suffix'] = '-script.py'
        else:
            options['script_py_suffix'] = ''

    def install(self):
        return []

    def update(self):
        pass

########NEW FILE########
__FILENAME__ = discover_lo
# -*- coding: utf-8 -*-

import os
import os.path
import sys
import logging
import contextlib
from discover_jre import executable_in_dir
from discover_jre import expose_options


logger = logging.getLogger(__name__)


def wellknown_locations():
    if sys.platform == 'win32':
        program_files = 'c:\\program files'
        if os.path.exists(program_files):
            for name in os.listdir(program_files):
                yield dict(location=os.path.join(program_files, name))
    if sys.platform.startswith('linux'):
        yield dict(location='/usr/lib/libreoffice',
                   uno_python='/usr/bin/python')  # Debian/Ubuntu


def discover_lo(in_wellknown=True, in_path=True):
    if in_wellknown:
        for installation in discover_in_wellknown_locations():
            yield installation

    if in_path:
        for installation in discover_in_path():
            yield installation


def discover_in_wellknown_locations():
    for installation in wellknown_locations():
        found = contains_program(installation['location'])
        if found:
            if 'uno_python' not in found and 'uno_python' in installation:
                uno_python = python_import_uno(installation['uno_python'])
                if uno_python:
                    found.update(resolve_uno_components(uno_python))
            installation.update(found)
            installation['through'] = 'WELLKNOWN_LOCATION'
            yield installation


def discover_in_path():
    if 'PATH' in os.environ:
        path = os.environ['PATH']
        path = path.split(os.pathsep)
        for dir in path:
            libreoffice = contains_libreoffice(dir)
            if libreoffice:
                entry = dict(libreoffice=libreoffice, through='PATH')

                # resolve symlinks
                resolved = os.path.realpath(libreoffice)
                location = os.path.dirname(os.path.dirname(resolved))
                installation = contains_program(location)
                if installation:
                    entry.update(installation)

                # Debian/Ubuntu case
                if 'uno' not in entry:
                    # try System python
                    uno_python = python_import_uno(sys.executable)
                    if uno_python:
                        entry.update(resolve_uno_components(uno_python))

                yield entry


def contains_libreoffice(dir):
    return executable_in_dir('libreoffice', dir)


def contains_program(location):
    program_dir = os.path.join(location, 'program')
    if os.path.isdir(program_dir):
        installation = dict(location=location, program=program_dir)
        soffice = executable_in_dir('soffice', program_dir)
        if soffice:
            installation['soffice'] = soffice
        unopkg = executable_in_dir('unopkg', program_dir)
        if unopkg:
            installation['unopkg'] = unopkg

        program_python = executable_in_dir('python', program_dir)
        if program_python:
            uno_python = python_import_uno(program_python)
            if uno_python:
                installation.update(resolve_uno_components(uno_python))

        basis_link = os.path.join(location, 'basis-link')
        if os.path.islink(basis_link):
            location = os.path.realpath(basis_link)

        ure = find_ure(location)
        if ure:
            installation['ure'] = ure

        return installation


def find_ure(location):
    ure_link = os.path.join(location, 'ure-link')
    if os.path.islink(ure_link):
        ure = os.path.realpath(ure_link)
        if os.path.isdir(ure):
            return ure

    # win32
    ure = os.path.join(location, 'ure')
    if os.path.isdir(ure):
        return ure


def python_import_uno(python):
    import subprocess
    cmd = [python, '-c', 'import uno, unohelper']
    ret = subprocess.call(cmd)
    if ret == 0:
        return python


def resolve_uno_components(uno_python):
    uno_python_core, modules = get_uno_locations(uno_python,
                                            ['uno', 'pyuno',
                                             'unohelper'])

    yield 'uno_python', uno_python
    yield 'uno_python_core', uno_python_core

    uno_pythonpath = set(os.path.dirname(modules[name])
                         for name in ['uno', 'unohelper'])
    uno_pythonpath = os.pathsep.join(list(uno_pythonpath))
    yield 'uno_pythonpath', uno_pythonpath

    for name in modules:
        yield name, modules[name]


def get_uno_locations(python, modules):
    statements = ['print __import__("sys").executable']
    statements.extend('print __import__("%s").__file__' % name
                      for name in modules)
    statements = ';'.join(statements)
    cmd = [python, '-c', statements]
    lines = subprocess_check_output(cmd)
    lines = lines.strip()
    lines = lines.split('\n')
    return lines[0], dict(zip(modules, lines[1:]))


def subprocess_check_output(cmd):
    import tempfile
    fd, name = tempfile.mkstemp()
    f = os.fdopen(fd, 'r+')
    try:
        import subprocess
        ret = subprocess.call(cmd, stdout=f)
        if ret != 0:
            logger.error('%d returned: %s', ret, ' '.join(cmd))
            raise Exception('%s exit with %d' % (cmd[0], ret))
        f.seek(0)
        return f.read()
    finally:
        f.close()
        os.unlink(name)


LO_VARS = ('libreoffice'
           ' location program soffice unopkg'
           ' ure'
           ' uno_python uno_python_core uno_pythonpath uno pyuno unohelper').split(' ')


def log_discovered(installations):
    for installation in installations:
        msg = 'discovered:'
        for name in LO_VARS + ['through']:
            if name in installation:
                msg += ' ' + name + '=' + installation[name]
        logger.info(msg)
        yield installation


@contextlib.contextmanager
def original_pythonpath():
    ''' without buildout-modified environment variables
    '''
    if 'BUILDOUT_ORIGINAL_PYTHONPATH' in os.environ:
        buildout_pythonpath = os.environ['PYTHONPATH']
        os.environ['PYTHONPATH'] = os.environ.pop('BUILDOUT_ORIGINAL_PYTHONPATH')
        yield
        os.environ['BUILDOUT_ORIGINAL_PYTHONPATH'] = os.environ['PYTHONPATH']
        os.environ['PYTHONPATH'] = buildout_pythonpath
    else:
        yield


class Discover(object):
    ''' Discover a LibreOffice installation and provide its location.
    '''

    def __init__(self, buildout, name, options):
        self.__logger = logger = logging.getLogger(name)
        for k, v in options.items():
            logger.info('%s: %r', k, v)

        self.__recipe = options['recipe']
        self.__generate_stub = None

        # special marker
        not_found = options.get('not-found', 'not-found')

        # expose platform-specific path seperator for convinience
        options['pathsep'] = os.pathsep

        if 'location' in options:
            # if location is explicitly specified, it must contains java
            # executable.
            with original_pythonpath():
                discovered = contains_program(options['location'])
            if discovered:
                # LO found, no further operation required.
                expose_options(options, LO_VARS, discovered,
                               not_found=not_found, logger=logger)
                return
            from zc.buildout import UserError
            raise UserError('LO not found at %s' % options['location'])

        in_wellknown = options.get('search-in-wellknown-places',
                                   'true').lower().strip()
        in_wellknown = in_wellknown in ('true', 'yes', '1')
        in_path = options.get('search-in-path', 'true').lower().strip()
        in_path = in_path in ('true', 'yes', '1')

        # location is not specified: try to discover a LO installation
        with original_pythonpath():
            discovered = discover_lo(in_wellknown, in_path)
            discovered = log_discovered(discovered)
            discovered = list(discovered)

        if discovered:
            discovered = discovered[0]
            logger.info('following LO installation will be used:')
            expose_options(options, LO_VARS, discovered, not_found=not_found,
                           logger=logger)
            return

        expose_options(options, LO_VARS, dict(), not_found=not_found,
                       logger=logger)
        return

        # no LO found: stub generation
        parts_dir = buildout['buildout']['parts-directory']
        self.__generate_stub = os.path.join(parts_dir, name)
        options['location'] = self.__generate_stub
        logger.info('LO not found: a dummy LO will be generated')
        logger.info('location = %s (updating)', self.__generate_stub)

    def install(self):
        location = self.__generate_stub
        if location is None:
            return

        if not os.path.exists(location):
            os.makedirs(location)
        yield location
        self.__logger.info('A dummy LO has been generated: %s', location)

    update = install

########NEW FILE########
__FILENAME__ = discover_lxml
# -*- coding: utf-8 -*-
from __future__ import with_statement
import logging
import os
import os.path
import sys
from discover_python import expose_options
from discover_python import log_discovered


logger = logging.getLogger(__name__)


EXPOSE_NAMES = ('location', 'version')


FIND_SOURCE = '''
import os
import os.path
import sys
try:
    from pkg_resources import get_distribution
except ImportError:
    sys.stderr.write('pkg_resources is not found' + os.linesep)
    try:
        import lxml
    except ImportError:
        sys.stderr.write('lxml is not found' + os.linesep)
        raise SystemExit(1)
    else:
        print(os.path.dirname(lxml.__path__[0]))
        print('')
        raise SystemExit(0)

try:
    dist = get_distribution('lxml')
except Exception:
    e = sys.exc_info()[1]
    sys.stderr.write(repr(e))
    sys.stderr.write(os.linesep)
    raise SystemExit(1)
else:
    print(dist.location)
    print(dist.version)
'''


def discover_lxml(executable):
    import tempfile
    fd, path = tempfile.mkstemp()
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(FIND_SOURCE)

        from subprocess import Popen
        from subprocess import PIPE
        args = [executable, path]
        env = dict(os.environ)
        for k in ('PYTHONPATH', 'PYTHONHOME'):
            if k in env:
                del env[k]
        try:
            p = Popen(args, stdout=PIPE, env=env)
        except Exception:
            e = sys.exc_info()[1]
            logger.exception(e)
            return
        else:
            try:
                lines = list(p.stdout)
            finally:
                p.wait()
    finally:
        os.unlink(path)

    if p.returncode == 0:
        location = lines[0].strip()
        version = lines[1].strip()
        yield dict(location=location,
                   version=version)


class DiscoverRecipe(object):
    ''' Discover lxml and provide its location.
    '''

    def __init__(self, buildout, name, options):
        self.__logger = logger = logging.getLogger(name)
        for k, v in options.items():
            logger.info('%s: %r', k, v)

        self.__recipe = options['recipe']

        not_found = options.get('not-found', 'not-found')
        executable = options.get('python', 'python').strip()
        #version = options.get('version', '').strip()

        founds = discover_lxml(executable=executable)
        founds = log_discovered('matching', founds, EXPOSE_NAMES,
                                log=logger.info)
        founds = list(founds)

        # location is not specified: try to discover a Python installation
        if founds:
            found = founds[0]
            logger.info('the first-found one will be used:')
            expose_options(options, EXPOSE_NAMES, found,
                           not_found=not_found, logger=logger)
            return

        # ensure executable publishes not-found marker
        expose_options(options, ['location'], dict(), not_found=not_found,
                       logger=logger)
        logger.warning('lxml not found')
        return

    def install(self):
        return []

    update = install

########NEW FILE########
__FILENAME__ = discover_python
# -*- coding: utf-8 -*-

import logging
import os
import os.path
import sys
import re


logger = logging.getLogger(__name__)


EXPOSE_NAMES = ('executable', 'version', 'prefix', 'exec_prefix', 'through')


def wellknown_locations():
    if sys.platform == 'win32':
        base = 'c:\\'
        for name in os.listdir(base):
            name = name.lower()
            if name.startswith('python'):
                shortversion = name[len('python'):]
                m = re.match('[23][0-9]', shortversion)
                if m:
                    yield base + name
    elif 'PYTHONZ_ROOT' in os.environ:
        pythonz_root = os.environ['PYTHONZ_ROOT']
        pythons = os.path.join(pythonz_root, 'pythons')
        for item in os.listdir(pythons):
            yield os.path.join(pythons, item)


def discover_python(in_wellknown=True, in_path=True):

    if in_wellknown:
        for found in search_in_wellknown_locations():
            yield found

    if in_path:
        for found in search_in_path():
            yield found


def search_in_wellknown_locations():
    for location in wellknown_locations():
        if sys.platform == 'win32':
            founds = contains_python(location)
        else:
            founds = contains_python_in_bin(location)

        for found in founds:
            found['through'] = 'WELLKNOWN_LOCATION'
            yield found


def search_in_path():
    if 'PATH' in os.environ:
        path = os.environ['PATH']
        path = path.split(os.pathsep)
        for dir in path:
            for found in contains_python(dir):
                found['through'] = 'PATH'

                # resolve symlinks
                resolved = os.path.realpath(found['executable'])
                found['executable'] = resolved
                yield found


def contains_python_in_bin(dir):
    bindir = os.path.join(dir, 'bin')
    return contains_python(bindir)


def contains_python(dir):
    vers = {
        2: [3, 4, 5, 6, 7],
        3: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    }
    names = (('python%d.%d' % (major, minor))
             for major in reversed(sorted(vers))
             for minor in reversed(sorted(vers[major])))
    names = list(names) + ['python']
    for name in names:
        executable = executable_in_dir(name, dir)
        if executable:
            found = executable_is_python(executable)
            if found:
                yield found


def executable_in_dir(name, dir):
    assert name == os.path.basename(name)
    if sys.platform == 'win32':
        name += '.exe'
    path = os.path.join(dir, name)
    if not os.path.exists(path):
        return
    return path


def executable_is_python(executable):
    from subprocess import Popen
    from subprocess import PIPE
    cmd = '''
    import os, sys
    print(sys.hexversion)
    print(os.pathsep.join([sys.prefix, sys.exec_prefix]))
    '''.strip().replace('\n', ';')
    args = [executable, '-c', cmd]
    env = dict(os.environ)
    for k in ('PYTHONPATH', 'PYTHONHOME'):
        if k in env:
            del env[k]
    try:
        p = Popen(args, stdout=PIPE, env=env)
        lines = p.stdout.read().split('\n')
        p.wait()
        ver = int(lines[0])
        ver_major = str(ver >> 24 & 0xff)
        ver_minor = str(ver >> 16 & 0xff)
        ver_patch = str(ver >> 8  & 0xff)
        ver = ver_major, ver_minor, ver_patch
        version = '.'.join(ver)
        prefix, exec_prefix = lines[1].split(os.pathsep)
        return dict(executable=executable, version=version,
                    prefix=prefix, exec_prefix=exec_prefix)
    except Exception, e:
        logger.error('popen failed: %s', args)
        logger.exception(e)


def log_discovered(qualify, found, names, log=logger.info):
    for item in found:
        msg = qualify + ':'
        for name in names:
            if name in item:
                msg += ' %s=%s' % (name, item[name])
        log(msg)
        yield item


def expose_options(options, names, found, not_found, logger=logger):
    for name in names:
        if name in found:
            value = found[name]
            if name in options:
                if value != options[name]:
                    logger.info('(updating) %s = %s', name, value)
                    options[name] = value
                else:
                    logger.info('(preserving) %s = %s', name, value)
            else:
                logger.info('(exposing) %s = %s', name, value)
                options[name] = value
        else:
            if name not in options:
                options[name] = value = not_found
                logger.info('(exposing) %s = %s', name, value)


class Discover(object):
    ''' Discover Python and provide its location.
    '''

    def __init__(self, buildout, name, options):
        from zc.buildout import UserError
        self.__logger = logger = logging.getLogger(name)
        for k, v in options.items():
            logger.info('%s: %r', k, v)

        self.__recipe = options['recipe']

        not_found = options.get('not-found', 'not-found')
        version = options.get('version', '').strip()

        if 'location' in options:
            # if location is explicitly specified, it must contains java
            # executable.
            for found in contains_python_in_bin(options['location']):
                if not version or found['version'].startswith(version):
                    # Python found, no further discovery required.
                    options['executable'] = found['executable']
                    return
            raise UserError('Python not found at %s' % options['location'])

        in_wellknown = options.get('search-in-wellknown-places',
                                   'true').lower().strip()
        in_wellknown = in_wellknown in ('true', 'yes', '1') 
        in_path = options.get('search-in-path', 'true').lower().strip()
        in_path = in_path in ('true', 'yes', '1')

        founds = discover_python(in_wellknown=in_wellknown,
                                 in_path=in_path)
        founds = log_discovered('candidates', founds, EXPOSE_NAMES,
                                log=logger.debug)
        if version:
            # filter with version
            founds = (found for found in founds
                      if found['version'].startswith(version))
        founds = log_discovered('matching', founds, EXPOSE_NAMES,
                                log=logger.info)
        founds = list(founds)

        # location is not specified: try to discover a Python installation
        if founds:
            found = founds[0]
            logger.info('the first-matching one will be used:')
            expose_options(options, EXPOSE_NAMES, found,
                           not_found=not_found, logger=logger)
            return

        # ensure executable publishes not-found marker
        expose_options(options, ['executable'], dict(), not_found=not_found,
                       logger=logger)
        logger.warning('Python not found')
        return

    def install(self):
        return []

    update = install

########NEW FILE########
__FILENAME__ = pyhwp_download
# -*- coding: utf-8 -*-
import sys
import urlparse
import os.path
import logging
from binascii import a2b_hex
from binascii import b2a_hex
from hashlib import md5

import requests


logger = logging.getLogger(__name__)


def main():
    logging.basicConfig()
    logger.setLevel(logging.DEBUG)

    url = sys.argv[1]
    dst = sys.argv[2]
    md5_given = a2b_hex(sys.argv[3])
    result = urlparse.urlparse(url)

    filename = os.path.basename(result.path)

    if not os.path.exists(dst):
        destination_path = dst
        logger.debug('%s not exists: destination=%s', dst, destination_path)
    else:
        if os.path.isdir(dst):
            destination_path = os.path.join(dst, filename)
            logger.debug('%s is a directory: destination=%s', dst,
                         destination_path)
        else:
            destination_path = dst

    if os.path.exists(destination_path):
        md5_existing = md5_file(destination_path)
        if md5_given == md5_existing:
            logger.debug('%s exists: skipped', destination_path)
            return

    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(destination_path, 'wb') as f:
        copy_stream(response.raw, f)

    md5_downloaded = md5_file(destination_path)
    if md5_given != md5_downloaded:
        logger.error('md5 not match: %s', b2a_hex(md5_downloaded))
        raise SystemExit(1)


def copy_stream(src, dst):
    while True:
        data = src.read(16384)
        if len(data) == 0:
            break
        dst.write(data)


def md5_file(path):
    with open(path, 'rb') as f:
        m = md5('')
        while True:
            data = f.read(16384)
            if len(data) == 0:
                break
            m.update(data)
    return m.digest()

########NEW FILE########
__FILENAME__ = egg_path
# -*- coding: utf-8 -*-
import logging


class EggPath(object):
    def __init__(self, buildout, name, options):
        self.__name = name
        self.__logger = logging.getLogger(name)

        eggs = options['eggs']
        eggs = eggs.split('\n')
        eggs = list(egg.strip() for egg in eggs)
        for egg in eggs:
            self.__logger.info('egg: %s', egg)

        from zc.recipe.egg.egg import Eggs
        eggs_recipe = Eggs(buildout, name, options)
        req, ws = eggs_recipe.working_set()
        for dist in ws:
            self.__logger.debug('dist: %s %s at %s', dist, dist.key, dist.location)
        dist_locations = dict((dist.key, dist.location) for dist in ws)
        egg_path = list(dist_locations[egg] for egg in eggs)
        for p in egg_path:
            self.__logger.info('egg-path: %s', p)
        options['egg-path'] = ' '.join(egg_path)

    def install(self):
        return []

    update = install

########NEW FILE########
__FILENAME__ = parsers
# -*- coding: utf-8 -*-


from gpl.Pysec import Record
from gpl.Pysec import one_of
from gpl.Pysec import none_of
from gpl.Pysec import between
from gpl.Pysec import digits
from gpl.Pysec import match
from gpl.Pysec import sep_by
from gpl.Pysec import pair
from gpl.Pysec import Parser
from gpl.Pysec import until_one_of
from gpl.Pysec import option
from gpl.Pysec import space
from gpl.Pysec import spaces
from gpl.Pysec import quoted
#from gpl.Pysec import quoted_chars
from gpl.Pysec import char_range
from gpl.Pysec import many_chars
from gpl.Pysec import group_chars
from gpl.Pysec import skip_before
from gpl.Pysec import skip_after
from gpl.Pysec import skip_many
from gpl.Pysec import many
from gpl.Pysec import group
from gpl.Pysec import parser
from gpl.Pysec import ParseFailed

lift = Parser.lift

inline_space  = one_of(" \v\f\t\r")
inline_spaces = skip_many(inline_space)
meaningful_spaces = many_chars(space)

def quoted_chars_inline(start, end):
    return quoted(start, many_chars(none_of(end+'\n')), end)


def until_one_of_inline(chars):
    return until_one_of(chars+'\n')


def skip_tailspace_of_line(parser):
    return skip_after(parser,
                      inline_spaces & option(None, match('\n')))


@parser
def until_not_but(state0, should_not, but):
    state = state0
    values = []
    while True:
        try:
            should_not_value, next_state = should_not(state)
            return values, state
        except ParseFailed:
            value, state = but(state)
            values.append(value)


def py_comment(parser):
    return inline_spaces & match('#') & parser


class Project(Record('name', 'description')):

    @classmethod
    def prepare(cls, name, description=None):
        name = name.strip()
        if description is not None:
            description = description.strip()
        return name, description

    def __str__(self):
        return self.name + (' : ' + self.description
                            if self.description
                            else '')


alphabet = char_range('a', 'z') + char_range('A', 'Z')
PROJECT_NAME = (group_chars([one_of(alphabet),
                             many_chars(one_of(alphabet + char_range('0', '9') + '-_'), 1)])
                >> lift(str.strip))
PROJECT_NAME = skip_after(PROJECT_NAME, option(None, inline_spaces))
PROJECT_DESC = until_one_of('\n') >> lift(str.strip)
PROJECT_LINE = pair(PROJECT_NAME,
                    option(None, match(':') & PROJECT_DESC))
PROJECT_LINE = PROJECT_LINE >> lift(lambda seq: Project(*seq))
PROJECT_LINE = skip_before(inline_spaces, PROJECT_LINE)
PROJECT_LINE = skip_tailspace_of_line(PROJECT_LINE)


COPYRIGHT_SIGN = match('Copyright (C)')

class Span(Record('start', 'end')):

    @classmethod
    def prepare(cls, start, end=None):
        if end is None:
            end = start
        assert start <= end
        return start, end

    def as_set(self):
        return set(range(self.start, self.end + 1))

    @classmethod
    def from_set(cls, valueset):
        span = None
        for value in sorted(valueset):
            if span is None:
                # at first
                span = Span(value, value)
            elif value == span.end + 1:
                # continue current span
                span = span.setEnd(value)
            else:
                # end current and start next span
                yield span
                span = Span(value, value)
        if span is not None:
            yield span

    def __str__(self):
        if self.start == self.end:
            return str(self.start)
        return '%d-%d' % self


YEAR = digits >> lift(int)
TAIL = option(None, match('-') & YEAR)
YEAR_SPAN = (pair(YEAR, TAIL) >> lift(lambda pair: Span(*pair)))
YEARS = (sep_by(YEAR_SPAN, match(','))
         >> lift(lambda spans: reduce(set.union,
                                      (span.as_set() for span in spans))))

class Author(Record('name', 'email')):

    @classmethod
    def prepare(self, name, email=None):
        if not name and not email:
            raise ValueError('either of name and email should not be empty')
        return (name.strip() if name else None,
                email.strip() if email else None)

    def __str__(self):
        name = self.name or ''
        email = ('<' + self.email + '>') if self.email else ''
        if not email:
            return name
        if not name:
            return email
        return name + ' ' + email


AUTHOR_NAME = until_one_of('<,\n') >> lift(str.strip)
AUTHOR_EMAIL = quoted_chars_inline('<', '>')
AUTHOR = (pair(option(None, AUTHOR_NAME), option(None, AUTHOR_EMAIL))
          >> lift(lambda author: Author(*author)))
joiner = between(spaces, match(","), spaces)
AUTHORS = sep_by(AUTHOR, joiner)


class Copyright(Record('years', 'authors')):
    def __str__(self):
        years = ','.join(str(span) for span in Span.from_set(self.years))
        authors = ', '.join(str(author) for author in self.authors)
        return 'Copyright (C) %s %s' % (years, authors)


COPYRIGHT_LINE = (COPYRIGHT_SIGN & inline_spaces &
                  pair(YEARS, inline_spaces & AUTHORS))
COPYRIGHT_LINE = skip_before(inline_spaces, COPYRIGHT_LINE)
COPYRIGHT_LINE = skip_tailspace_of_line(COPYRIGHT_LINE)
COPYRIGHT_LINE = COPYRIGHT_LINE >> lift(lambda seq: Copyright(*seq))

GENERIC_LINE = skip_after(many_chars(none_of('\n')), match('\n'))


class License(Record('prolog', 'project', 'copyright', 'epilog')):

    def __str__(self):
        return '\n'.join(self.prolog +
                         ['#   ' + str(self.project),
                          '#   ' + str(self.copyright)] +
                         self.epilog + [''])


PROLOG = until_not_but(py_comment(PROJECT_LINE), GENERIC_LINE)
EPILOG = many(GENERIC_LINE)
LICENSE = (group([PROLOG,
                  py_comment(PROJECT_LINE),
                  py_comment(COPYRIGHT_LINE),
                  EPILOG])
           >> lift(lambda seq: License(*seq)))


def parse_file(path):
    with file(path) as f:
        text = f.read()
        return LICENSE.parseString(text)

########NEW FILE########
__FILENAME__ = Pysec
# -*- coding: utf-8 -*-
# originally authored by Peter Thatcher, Public Domain
# See http://www.valuedlessons.com/2008/02/pysec-monadic-combinatoric-parsing-in.html

def Record(*props):
    class cls(RecordBase):
        pass

    cls.setProps(props)

    return cls


class RecordBase(tuple):
    PROPS = ()

    def __new__(cls, *values):
        if cls.prepare != RecordBase.prepare:
            values = cls.prepare(*values)
        return cls.fromValues(values)

    @classmethod
    def fromValues(cls, values):
        return tuple.__new__(cls, values)

    def __repr__(self):
        return self.__class__.__name__ + tuple.__repr__(self)

    ## overridable
    @classmethod
    def prepare(cls, *args):
        return args

    ## setting up getters and setters
    @classmethod
    def setProps(cls, props):
        for index, prop in enumerate(props):
            cls.setProp(index, prop)
        cls.PROPS = props

    @classmethod
    def setProp(cls, index, prop):
        getter_name = prop
        setter_name = "set" + prop[0].upper() + prop[1:]

        setattr(cls, getter_name, cls.makeGetter(index, prop))
        setattr(cls, setter_name, cls.makeSetter(index, prop))

    @classmethod
    def makeGetter(cls, index, prop):
        return property(fget = lambda self : self[index])

    @classmethod
    def makeSetter(cls, index, prop):
        def setter(self, value):
            values = (value if current_index == index
                            else current_value
                      for current_index, current_value
                      in enumerate(self))
            return self.fromValues(values)
        return setter


class ByteStream(Record("bytes", "index")):
    @classmethod
    def prepare(cls, bytes, index = 0):
        return (bytes, index)

    def get(self, count):
        start = self.index
        end   = start + count
        bytes = self.bytes[start : end]
        return bytes, (self.setIndex(end) if bytes else self)


def make_decorator(func, *dec_args):
    def decorator(undecorated):
        def decorated(*args, **kargs):
            return func(undecorated, args, kargs, *dec_args) 
        
        decorated.__name__ = undecorated.__name__
        return decorated
    
    decorator.__name__ = func.__name__
    return decorator


decorator = make_decorator


class Monad:
    ## Must be overridden
    def bind(self, func):
        raise NotImplementedError

    @classmethod
    def unit(cls, val):
        raise NotImplementedError

    @classmethod
    def lift(cls, func):
        return (lambda val : cls.unit(func(val)))

    ## useful defaults that should probably NOT be overridden
    def __rshift__(self, bindee):
        return self.bind(bindee)

    def __and__(self, monad):
        return self.shove(monad)
        
    ## could be overridden if useful or if more efficient
    def shove(self, monad):
        return self.bind(lambda _ : monad)


class StateChanger(Record("changer", "bindees"), Monad):
    @classmethod
    def prepare(cls, changer, bindees = ()):
        return (changer, bindees)

    # binding can be slow since it happens at bind time rather than at run time
    def bind(self, bindee):
        return self.setBindees(self.bindees + (bindee,))

    def __call__(self, state):
        return self.run(state)

    def run(self, state0):
        value, state = self.changer(state0) if callable(self.changer) else self.changer
        state        = state0 if state is None else state

        for bindee in self.bindees:
            value, state = bindee(value).run(state)
        return (value, state)

    @classmethod
    def unit(cls, value):
        return cls((value, None))


######## Parser Monad ###########


class ParserState(Record("stream", "position")):
    @classmethod
    def prepare(cls, stream, position = 0):
        return (stream, position)

    def read(self, count):
        collection, stream = self.stream.get(count)
        return collection, self.fromValues((stream, self.position + count))


class Parser(StateChanger):
    def parseString(self, bytes):
        return self.parseStream(ByteStream(bytes))
        
    def parseStream(self, stream):
        state = ParserState(stream)
        value, state = self.run(state)
        return value


class ParseFailed(Exception):
    def __init__(self, message, state):
        self.message = message
        self.state   = state
        Exception.__init__(self, message)


@decorator
def parser(func, func_args, func_kargs):
    def changer(state):
        return func(state, *func_args, **func_kargs)
    changer.__name__ = func.__name__
    return Parser(changer)


##### combinatoric functions #########


@parser
def tokens(state0, count, process):
    tokens, state1 = state0.read(count)

    passed, value = process(tokens)
    if passed:
        return (value, state1)
    else:
        raise ParseFailed(value, state0)
    

def read(count):
    return tokens(count, lambda values : (True, values))


@parser
def skip(state0, parser):
    value, state1 = parser(state0)
    return (None, state1)


@parser
def option(state, default_value, parser):
    try:
        return parser(state)
    except ParseFailed, failure:
        if failure.state == state:
            return (default_value, state)
        else:
            raise
        

@parser
def choice(state, parsers):
    for parser in parsers:
        try:
            return parser(state)
        except ParseFailed, failure:
            if failure.state != state:
                raise failure
    raise ParseFailed("no choices were found", state)


@parser
def match(state0, expected):
    actual, state1 = read(len(expected))(state0)
    if actual == expected:
        return actual, state1
    else:
        raise ParseFailed("expected %r, actual %r" % (expected, actual), state0)


def between(before, inner, after):
    return before & inner >> (lambda value : after & Parser.unit(value))


def quoted(before, inner, after):
    return between(match(before), inner, match(after))


def quoted_collection(start, space, inner, joiner, end):
    return quoted(start, space & sep_end_by(inner, joiner), end)


@parser
def many(state, parser, min_count = 0):
    values = []

    try:
        while True:
            value, state = parser(state)
            values.append(value)
    except ParseFailed:
        if len(values) < min_count:
            raise

    return values, state
    

@parser
def group(state, parsers):
    values = []

    for parser in parsers:
        value, state = parser(state)
        values.append(value)

    return values, state


def pair(parser1, parser2):
    # return group((parser1, parser2))
    return parser1 >> (lambda value1 : parser2 >> (lambda value2 : Parser.unit((value1, value2))))


@parser
def skip_many(state, parser):
    try:
        while True:
            value, state = parser(state)
    except ParseFailed:
        return (None, state)


def skip_before(before, parser):
    return skip(before) & parser


@parser
def skip_after(state0, parser, after):
    value, state1 = parser(state0)
    _,     state2 = after(state1)
    return value, state2


@parser
def option_many(state0, first, repeated, min_count = 0):
    try:
        first_value, state1 = first(state0)
    except ParseFailed:
        if min_count > 0:
            raise
        else:
            return [], state0
    else:
        values, state2 = many(repeated, min_count-1)(state1)
        values.insert(0, first_value)
        return values, state2


# parser separated and ended by sep
def end_by(parser, sep_parser, min_count = 0):
    return many(skip_after(parser, sep_parser), min_count)


# parser separated by sep
def sep_by(parser, sep_parser, min_count = 0):
    return option_many(parser, skip_before(sep_parser, parser), min_count)
    

# parser separated and optionally ended by sep
def sep_end_by(parser, sep_parser, min_count = 0):
    return skip_after(sep_by(parser, sep_parser, min_count), option(None, sep_parser))


##### char-specific parsing ###########


def satisfy(name, passes):
    return tokens(1, lambda char : (True, char) if passes(char) else (False, "not " + name))


def one_of(chars):
    char_set = frozenset(chars)
    return satisfy("one of %r" % chars, lambda char : char in char_set)


def none_of(chars):
    char_set = frozenset(chars)
    return satisfy("not one of %r" % chars, lambda char : char and char not in char_set)


def maybe_match_parser(parser):
    return match(parser) if isinstance(parser, str) else parser


def maybe_match_parsers(parsers):
    return tuple(maybe_match_parser(parser) for parser in parsers)


def many_chars(parser, min_count = 0):
    return join_chars(many(parser, min_count))


def option_chars(parsers):
    return option("", group_chars(parsers))


def group_chars(parsers):
    return join_chars(group(maybe_match_parsers(parsers)))
    #return join_chars(group(parsers))


def join_chars(parser):
    return parser >> Parser.lift("".join)


def while_one_of(chars, min_count = 0):
    return many_chars(one_of(chars), min_count)


def until_one_of(chars, min_count = 0):
    return many_chars(none_of(chars), min_count)


def char_range(begin, end):
    return "".join(chr(num) for num in xrange(ord(begin), ord(end)))


def quoted_chars(start, end):
    assert len(end) == 1, "end string must be exactly 1 character"
    return quoted(start, many_chars(none_of(end)), end)


digit  = one_of(char_range("0", "9"))
digits = many_chars(digit, min_count = 1)
space  = one_of(" \v\f\t\r\n")
spaces = skip_many(space)


############# simplified JSON ########################

#from Pysec import Parser, choice, quoted_chars, group_chars, option_chars, digits, between, pair, spaces, match, quoted_collection, sep_end_by

#HACK: json_choices is used to get around mutual recursion 
#a json is value is one of text, number, mapping, and collection, which we define later 
json_choices = []
json         = choice(json_choices)

#text is any characters between quotes
text         = quoted_chars("'", "'")

#sort of like the regular expression -?[0-9]+(\.[0-9]+)?
#in case you're unfamiliar with monads, "parser >> Parser.lift(func)" means "pass the parsed value into func but give me a new Parser back"
number       = group_chars([option_chars(["-"]), digits, option_chars([".", digits])]) >> Parser.lift(float)

#quoted_collection(start, space, inner, joiner, end) means "a list of inner separated by joiner surrounded by start and end"
#also, we have to put a lot of spaces in there since JSON allows lot of optional whitespace
joiner       = between(spaces, match(","), spaces)
mapping_pair = pair(text, spaces & match(":") & spaces & json)
collection   = quoted_collection("[", spaces, json,         joiner, "]") >> Parser.lift(list)
mapping      = quoted_collection("{", spaces, mapping_pair, joiner, "}") >> Parser.lift(dict)

#HACK: finish the work around mutual recursion
json_choices.extend([text, number, mapping, collection])


############# simplified CSV ########################

def line(cell):
    return sep_end_by(cell, match(","))

def csv(cell):
    return sep_end_by(line(cell), match("\n"))

############# testing ####################

if __name__ == '__main__':
    print json.parseString("{'a' : -1.0, 'b' : 2.0, 'z' : {'c' : [1.0, [2.0, [3.0]]]}}")
    print csv(number).parseString("1,2,3\n4,5,6")
    print csv(json).parseString("{'a' : 'A'},[1, 2, 3],'zzz'\n-1.0,2.0,-3.0")

########NEW FILE########
__FILENAME__ = test_gpl
# -*- coding: utf-8 -*-
from unittest import TestCase


class SpanTest(TestCase):

    def test_from_set(self):
        from gpl.parsers import Span
        self.assertEquals([Span(1)],
                          list(Span.from_set([1])))
        self.assertEquals([Span(1, 2)],
                          list(Span.from_set([1, 2])))
        self.assertEquals([Span(1, 2), Span(4)],
                          list(Span.from_set([1, 2, 4])))
        self.assertEquals([Span(1, 2), Span(4, 6)],
                          list(Span.from_set([1, 2, 4, 5, 6])))

    def test_str(self):
        from gpl.parsers import Span
        self.assertEquals('3', str(Span(3)))
        self.assertEquals('3-4', str(Span(3, 4)))
        self.assertEquals('3-6', str(Span(3, 6)))


project_line = '   pyhwp : hwp file format parser in python'
copyright_line = '    Copyright (C) 2010-2012 mete0r  '
generic_line = '   abc   '
LF = '\n'


class ProjectTest(TestCase):

    def test_project_name(self):
        from gpl.parsers import PROJECT_NAME
        self.assertEquals('pyhwp', PROJECT_NAME.parseString('pyhwp  :'))

    def test_project_desc(self):
        from gpl.parsers import PROJECT_DESC
        self.assertEquals('hwp file format parser in python',
                          PROJECT_DESC.parseString('   hwp file format parser in python  '))

    def test_project_line_with_lf(self):
        from gpl.parsers import Project
        from gpl.parsers import PROJECT_LINE

        # ok with LF
        self.assertEquals(Project('pyhwp', 'hwp file format parser in python'),
                          PROJECT_LINE.parseString(project_line + LF))
        self.assertEquals(Project('pyhwp'),
                          PROJECT_LINE.parseString('   pyhwp   ' + LF))

    def test_project_line_without_lf(self):
        from gpl.parsers import Project
        from gpl.parsers import PROJECT_LINE

        # ok without LF
        self.assertEquals(Project('pyhwp', 'hwp file format parser in python'),
                          PROJECT_LINE.parseString(project_line))
        self.assertEquals(Project('pyhwp'),
                          PROJECT_LINE.parseString('   pyhwp   '))

    def test_project_line_parser_doesnt_consume_after_lf(self):
        from gpl.parsers import PROJECT_LINE
        # make sure that the parser does not consume after LF
        from gpl.Pysec import match
        self.assertEquals(' NEXTLINE',
                          (PROJECT_LINE & match(' NEXTLINE')).parseString(project_line
                                                                          + LF + ' NEXTLINE'))


class CopyrightTest(TestCase):

    def test_stringify_years(self):
        from gpl import stringify_years
        self.assertEquals('2011-2012',
                          stringify_years([2011, 2012]))
        self.assertEquals('2011-2013',
                          stringify_years([2011, 2012, 2013]))
        self.assertEquals('2011-2013,2015',
                          stringify_years([2011, 2012, 2013, 2015]))
        self.assertEquals('2009,2011-2013,2015',
                          stringify_years([2009, 2011, 2012, 2013, 2015]))

    def test_copyright(self):
        from gpl.parsers import COPYRIGHT_SIGN
        self.assertTrue(COPYRIGHT_SIGN.parseString('Copyright (C)'))

        from gpl.parsers import Span
        self.assertEquals('2010', str(Span(2010)))
        self.assertEquals('2010-2012', str(Span(2010, 2012)))

        from gpl.parsers import YEAR_SPAN
        self.assertEquals(Span(2010, 2012),
                          YEAR_SPAN.parseString('2010-2012'))
        self.assertEquals(Span(2010, 2010),
                          YEAR_SPAN.parseString('2010'))

        from gpl.parsers import YEARS
        self.assertEquals(set([2010]),
                          YEARS.parseString('2010'))
        self.assertEquals(set([2010, 2011]),
                          YEARS.parseString('2010,2011'))
        self.assertEquals(set([2010, 2011, 2012]),
                          YEARS.parseString('2010-2012'))
        self.assertEquals(set([2010, 2011, 2013, 2014, 2015, 2017]),
                          YEARS.parseString('2010,2011,2013-2015,2017'))

        from gpl.parsers import AUTHOR_NAME
        self.assertEquals('Hello World',
                          AUTHOR_NAME.parseString('Hello World'))
        self.assertEquals('Hello World',
                          AUTHOR_NAME.parseString('Hello World <'))

        from gpl.parsers import AUTHOR_EMAIL
        self.assertEquals('user@example.tld',
                          AUTHOR_EMAIL.parseString('<user@example.tld>'))

        from gpl.parsers import Author
        from gpl.parsers import AUTHOR
        self.assertEquals(Author('hong gil-dong', 'hongd@example.tld'),
                          AUTHOR.parseString('hong gil-dong <hongd@example.tld>'))
        self.assertEquals(Author('hong gil-dong'),
                          (AUTHOR.parseString('hong gil-dong')))
        self.assertEquals(Author(None, 'hongd@example.tld'),
                          (AUTHOR.parseString('<hongd@example.tld>')))

        from gpl.parsers import AUTHORS
        self.assertEquals([Author('mete0r'),
                           Author('hong gil-dong', 'hongd@ex.tld')],
                          AUTHORS.parseString('mete0r, hong gil-dong <hongd@ex.tld>'))

        from gpl.parsers import Copyright
        from gpl.parsers import COPYRIGHT_LINE
        # ok with LF
        self.assertEquals(Copyright(set([2010, 2011, 2012]),
                                    [Author('mete0r')]),
                          (COPYRIGHT_LINE.parseString(copyright_line + LF)))

        # ok without LF
        self.assertEquals(Copyright(set([2010, 2011, 2012]),
                                    [Author('mete0r')]),
                          (COPYRIGHT_LINE.parseString(copyright_line)))

        # make sure that the parser does not consume after the LF
        from gpl.Pysec import match
        self.assertEquals(' NEXTLINE',
                          (COPYRIGHT_LINE & match(' NEXTLINE')).parseString(copyright_line + LF + ' NEXTLINE'))

    def test_generic_line(self):
        from gpl.parsers import GENERIC_LINE
        self.assertEquals(generic_line,
                          GENERIC_LINE.parseString(generic_line + LF))


class LicenseTest(TestCase):
    def test_license(self):
        from gpl.parsers import LICENSE

        text = '''#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# ''' + project_line + '''
# ''' + copyright_line + '''
#
#    This file is part of pyhwp project.
#
#   license text.

import unittest
'''
        print LICENSE.parseString(text)

########NEW FILE########
__FILENAME__ = jxml_coverage
# -*- coding: utf-8 -*-
from __future__ import with_statement

import logging
import sys
import os.path

import colorama
from colorama import Fore, Back, Style
from docopt import docopt

from jxml.etree import XSLTCoverage
from jxml.etree import xsltcoverage


def colorama_init(f):
    def wrapper(*args, **kwargs):
        colorama.init()
        try:
            return f(*args, **kwargs)
        finally:
            colorama.deinit()
    return wrapper


@colorama_init
def annotate_main():
    __doc__ = '''
    Usage: jxml-annotate [options] <xml-file>...

    <xml-file>  Cobertura-compatible coverage data file
    --color=[auto|yes|no]    Output with colors

    Example:
        jxml-annotate --color=yes coverage.xml | less -R
    '''
    args = docopt(__doc__)

    logging.basicConfig()
    logger = logging.getLogger('jxml.annotate')

    use_color = args['--color'] == 'yes'
    if args['--color'] in ('auto', None):
        use_color = sys.stdout.isatty()

    coverage = XSLTCoverage()
    for arg in args['<xml-file>']:
        coverage.read_from(arg)

    traces = coverage.traces
    for filename in sorted(traces):
        covered_lines = traces[filename]
        if not os.path.exists(filename):
            logger.info('skipping %s: not exists', filename)
            continue
        print filename

        with open(filename) as f:
            for line_no, line in enumerate(f):
                line_no += 1
                count = covered_lines.get(line_no, 0)
                annotated = '%8d: %s' % (count, line)

                if use_color:
                    if count == 0:
                        color = Fore.RED
                    else:
                        color = Fore.RESET
                    annotated = color + annotated + Fore.RESET
                sys.stdout.write(annotated)

    print ''


def load_tests(filenames):
    import unittest
    ts = unittest.TestSuite()
    testloader = unittest.defaultTestLoader
    for filename in filenames:
        d = dict()
        execfile(filename, d)
        for name in d:
            x = d[name]
            if isinstance(x, type) and issubclass(x, unittest.TestCase):
                ts.addTests(testloader.loadTestsFromTestCase(x))
    return ts


def cov_test_main():
    __doc__ = '''
    Usage: jxml-cov-test [options] <output-file> <unittest-file>...

    <output-file>       Cobertura-compatible coverage data file.
    <unittest-file>     unittest files.

    Example:
        jxml-cov-test coverage.xml test1.py test2.py
    '''
    args = docopt(__doc__)

    logging.basicConfig()
    logger = logging.getLogger('jxml.cov-test')

    from java.lang import System
    import unittest

    props = System.getProperties()
    props['javax.xml.transform.TransformerFactory'] = 'org.apache.xalan.processor.TransformerFactoryImpl'
    props['javax.xml.parsers.DocumentBuilderFactory'] = 'org.apache.xerces.jaxp.DocumentBuilderFactoryImpl'
    props['javax.xml.parsers.SAXParserFactory'] = 'org.apache.xerces.jaxp.SAXParserFactoryImpl'

    output_name = args['<output-file>']
    test_filenames = args['<unittest-file>']
    ts = load_tests(test_filenames)
    runner = unittest.TextTestRunner()
    with xsltcoverage(output_name) as coverage:
        runner.run(ts)

########NEW FILE########
__FILENAME__ = test_jaxp
# -*- coding: utf-8 -*-

import unittest

from java.lang import System
from java.io import File
from java.io import ByteArrayOutputStream
from javax.xml.parsers import DocumentBuilderFactory
from javax.xml.transform import TransformerFactory
from javax.xml.transform.dom import DOMSource
from javax.xml.transform.stream import StreamSource
from javax.xml.transform.stream import StreamResult

dbfac = DocumentBuilderFactory.newInstance()
dbfac.namespaceAware = True
docfac = dbfac.newDocumentBuilder()
print type(dbfac)

transfac = TransformerFactory.newInstance()

src_dom = docfac.parse('hello.xml')
src_source = DOMSource(src_dom)


def unsigned_byte(x):
    if x < 0:
        return 256 + x
    return x


def Transformer(xsl_source):
    transformer = transfac.newTransformer(xsl_source)
    def transform(src_source):
        outputstream = ByteArrayOutputStream()
        dst_result = StreamResult(outputstream)
        transformer.transform(src_source, dst_result)
        return ''.join(chr(unsigned_byte(x)) for x in outputstream.toByteArray())
    return transform


def transform(xsl_source, src_source):
    transform = Transformer(xsl_source)
    return transform(src_source)


class TestXSLT(unittest.TestCase):

    xsl_path = 'xsl/import-test.xsl'

    def test_xsl_dom(self):

        xsl_dom = docfac.parse(self.xsl_path)
        # DOMSource with System Id
        xsl_source = DOMSource(xsl_dom, self.xsl_path)

        result = transform(xsl_source, src_source)
        #print result
        self.assertTrue('world' in result)

    def test_xsl_stream(self):
        xsl_source = StreamSource(self.xsl_path)

        result = transform(xsl_source, src_source)
        #print result
        self.assertTrue('world' in result)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_lxml
# -*- coding: utf-8 -*-
from __future__ import with_statement

import os.path
import sys
import unittest
from unittest import TestCase

from lxml import etree
from lxml.etree import ElementTree
from lxml.etree import Element
from lxml.etree import SubElement
from lxml.etree import QName


class ElementTreeTest(TestCase):

    def test_etree_parse(self):
        with open('sample.xml') as f:
            et = etree.parse(f)
        et = etree.parse('sample.xml')

    def test_etree_fromstring(self):
        with open('sample.xml') as f:
            text = f.read()
        et = etree.fromstring(text)

    def test_etree_from_file(self):
        with open('sample.xml') as f:
            et = ElementTree(file=f)
        root = et.getroot()
        self.assertEquals('{http://example.tld}document', root.tag)
        self.assertEquals('x', root.prefix)
        self.assertTrue('x' in root.nsmap)

        with open('hello.xml') as f:
            et = ElementTree(file=f)
        root = et.getroot()
        self.assertEquals('hello', root.tag)
        self.assertEquals(None, root.prefix)
        self.assertEquals({}, root.nsmap)

    def test_etree_tostring(self):
        with open('sample.xml') as f:
            et = etree.parse(f)
        etree.tostring(et, encoding='utf-8', xml_declaration=True)
        etree.tostring(et.getroot()[0], encoding='utf-8', xml_declaration=True)

    def test_from_element(self):
        elem = Element('document')
        tree = ElementTree(elem)
        self.assertEquals('document', tree.getroot().tag)

        with open('sample.xml') as f:
            et = ElementTree(file=f)
        root = et.getroot()

        tree = ElementTree(root)
        self.assertEquals(root.base, tree.getroot().base)
        self.assertEquals(et.docinfo.URL, tree.docinfo.URL)

    def test_docinfo(self):
        with open('sample.xml') as f:
            et = etree.parse(f)
        import os.path
        self.assertEquals(os.path.abspath('sample.xml'), et.docinfo.URL)
        self.assertEquals('', et.docinfo.doctype)
        self.assertEquals('utf-8', et.docinfo.encoding)
        self.assertEquals(None, et.docinfo.externalDTD)
        self.assertEquals(None, et.docinfo.internalDTD)
        self.assertEquals(None, et.docinfo.public_id)
        self.assertEquals('document', et.docinfo.root_name)
        self.assertFalse(et.docinfo.standalone)
        self.assertEquals(None, et.docinfo.system_url)
        self.assertEquals('1.0', et.docinfo.xml_version)

        et.docinfo.URL = 'http://example.tld'
        self.assertEquals('http://example.tld', et.docinfo.URL)

    def test_parser(self):
        pass

    def test__copy__(self):
        pass

    def test__deepcopy__(self):
        pass

    def test_setroot(self):
        from lxml.etree import XML
        a = XML('<a />').getroottree()
        b = XML('<b />').getroottree()
        a._setroot(b.getroot())
        self.assertEquals('b', a.getroot().tag)

    def test_find(self):
        pass

    def test_findall(self):
        pass

    def test_findtext(self):
        pass

    def test_getiterator(self):
        pass

    def test_getpath(self):
        pass

    def test_getroot(self):
        with open('sample.xml') as f:
            et = etree.parse(f)
        tree = etree.parse('sample.xml')
        root = tree.getroot()
        self.assertEquals('{http://example.tld}document', root.tag)

    def test_iter(self):
        pass

    def test_iterfind(self):
        pass

    def test_parse(self):
        pass

    def test_relaxng(self):
        pass

    def test_write(self):
        with open('sample.xml') as f:
            tree = etree.parse(f)

        import tempfile
        import os
        fd, name = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'w') as f:
                tree.write(f)
            with open(name) as f:
                tree2 = etree.parse(f)
        finally:
            os.unlink(name)
        self.assertEquals(tree.getroot().tag, tree2.getroot().tag)

    def test_write_c14n(self):
        pass

    def test_xinclude(self):
        pass

    def test_xmlschema(self):
        pass

    def test_xpath(self):
        with open('sample.xml') as f:
            et = etree.parse(f)
        tree = etree.parse('sample.xml')

        nsmap = dict(x='http://example.tld')

        # element
        result = tree.xpath('//x:paragraph', namespaces=nsmap)
        self.assertEquals(1, len(result))
        self.assertEquals('{http://example.tld}paragraph',
                          result[0].tag)

        # attribute
        result = tree.xpath('@version', namespaces=nsmap)
        self.assertEquals(['1.0'], result)

        # string
        result = tree.xpath('"foo"', namespaces=nsmap)
        self.assertEquals('foo', result)

        # number expression
        result = tree.xpath('1', namespaces=nsmap)
        self.assertEquals(1.0, result)

        result = tree.xpath('"1.0"', namespaces=nsmap)
        # should be string, but alas, it returns a number in jxml
        if sys.platform.startswith('java'):
            self.assertEquals(1.0, result)
        else:
            self.assertEquals('1.0', result)

    def test_xslt(self):
        tree = etree.XML('<hello />').getroottree()
        with open('xsl/import-test.xsl') as f:
            xsl_tree = etree.parse(f)
        result = tree.xslt(xsl_tree)
        self.assertEquals('world', result.getroot().tag)


class ElementTest(TestCase):

    def setUp(self):
        with open('sample.xml') as f:
            self.et = ElementTree(file=f)
        self.root = self.et.getroot()

    def tearDown(self):
        pass

    def test_Element(self):
        elem = Element('document', dict(a='1', b='2'), c='3')
        self.assertEquals('document', elem.tag)
        self.assertEquals(dict(a='1', b='2', c='3'),
                          elem.attrib)

        nsmap = dict(a='http://a.example.tld', c='http://c.example.tld')
        elem = Element('{http://a.example.tld}document',
                       {'{http://a.example.tld}a': '1',
                        '{http://b.example.tld}a': '2',
                        'a': '3'},
                       nsmap)

        self.assertEquals('a', elem.prefix)
        self.assertEquals('{http://a.example.tld}document', elem.tag)
        self.assertEquals(nsmap['a'], elem.nsmap['a'])
        self.assertEquals(nsmap['c'], elem.nsmap['c'])
        self.assertTrue('http://b.example.tld' in elem.nsmap.values())
        self.assertEquals('1', elem.get('{http://a.example.tld}a'))
        self.assertEquals('2', elem.get('{http://b.example.tld}a'))
        self.assertEquals('3', elem.get('a'))

    def test_SubElement(self):
        elem = Element('document')
        child = SubElement(elem, 'paragraph')
        grandchild = SubElement(child, 'span')
        self.assertEquals('paragraph', elem[0].tag)
        self.assertEquals('span', elem[0][0].tag)

    def test_base(self):
        uri = os.path.abspath('sample.xml')
        with open(uri) as f:
            et = etree.parse(f)
        root = et.getroot()
        self.assertEquals(uri, root.base)

    def test_tag(self):
        elem = Element('HwpDoc')
        self.assertEquals('HwpDoc', elem.tag)

        elem = Element('{http://www.w3.org/1999/XSL/Transform}stylesheet')
        self.assertTrue(elem.prefix)
        self.assertEquals('{http://www.w3.org/1999/XSL/Transform}stylesheet', elem.tag)

        elem = Element('{http://www.w3.org/1999/XSL/Transform}stylesheet',
                       nsmap=dict(xsl='http://www.w3.org/1999/XSL/Transform'))
        self.assertEquals('xsl', elem.prefix)
        self.assertEquals('{http://www.w3.org/1999/XSL/Transform}stylesheet', elem.tag)

    def test_nsmap(self):
        self.assertEquals(dict(x='http://example.tld'),
                          self.root.nsmap)
        self.assertEquals(dict(x='http://example.tld',
                               z='http://z.example.tld'),
                          self.root[1].nsmap)

    def test_prefix(self):
        self.assertEquals('x', self.root.prefix)
        self.assertEquals('z', self.root[1].prefix)

    def test_text(self):
        self.assertEquals('text', self.root[0].text)
        self.assertEquals(None, self.root[1].text)

    def test_tail(self):
        self.assertEquals('tail', self.root[0].tail)
        self.assertEquals(None, self.root[0][0].tail)

    def test_attrib(self):
        self.assertEquals({'version': '1.0'},
                          self.root.attrib)
        self.assertEquals({'a': '1',
                           '{http://example.tld}b': '2',
                           '{http://z.example.tld}c': '3'},
                          self.root[1].attrib)

    def test__contains__(self):
        pass

    def test__copy__(self):
        pass

    def test__deepcopy__(self):
        pass

    def test__delitem__(self):
        pass

    def test__getitem__(self):
        paragraph = self.root.__getitem__(0)
        self.assertEquals('{http://example.tld}paragraph', paragraph.tag)
        paragraph = self.root[0]
        self.assertEquals('{http://example.tld}paragraph', paragraph.tag)

        paragraph = self.root.__getitem__(1)
        self.assertEquals('{http://z.example.tld}object', paragraph.tag)
        paragraph = self.root[1]
        self.assertEquals('{http://z.example.tld}object', paragraph.tag)

        child = self.root.__getitem__(-1)
        self.assertEquals('{http://example.tld}third', child.tag)
        child = self.root[-1]
        self.assertEquals('{http://example.tld}third', child.tag)

    def test__iter__(self):
        it = self.root.__iter__()

        paragraph = it.next()
        self.assertEquals('{http://example.tld}paragraph',
                          paragraph.tag)
        self.assertEquals('text', paragraph.text)
        self.assertEquals('tail', paragraph.tail)

        paragraph = it.next()
        self.assertEquals('{http://z.example.tld}object',
                          paragraph.tag)

        child = it.next()
        self.assertEquals('{http://example.tld}third',
                          child.tag)

        self.assertRaises(StopIteration, it.next)

    def test__len__(self):
        self.assertEquals(3, self.root.__len__())
        self.assertEquals(3, len(self.root))

    def test__nonzero__(self):
        pass

    def test__repr__(self):
        pass

    def test__reversed__(self):
        it = self.root.__reversed__()

        child = it.next()
        self.assertEquals('{http://example.tld}third',
                          child.tag)

        paragraph = it.next()
        self.assertEquals('{http://z.example.tld}object',
                          paragraph.tag)

        paragraph = it.next()
        self.assertEquals('{http://example.tld}paragraph',
                          paragraph.tag)
        self.assertEquals('text', paragraph.text)
        self.assertEquals('tail', paragraph.tail)

        self.assertRaises(StopIteration, it.next)

    def test__setitem__(self):
        new_child = Element('new-child')
        self.root.__setitem__(1, new_child)
        self.assertEquals('new-child', self.root[1].tag)

        new_child = Element('new-child2')
        self.assertRaises(IndexError, self.root.__setitem__, 3, new_child)

    def test_addnext(self):
        pass

    def test_addprevious(self):
        pass

    def test_append(self):
        new_child = Element('new-child')
        self.root.append(new_child)

        child = self.root[3]
        self.assertEquals('new-child', child.tag)

    def test_clear(self):
        pass

    def test_extend(self):
        pass

    def test_find(self):
        pass

    def test_findall(self):
        pass

    def test_findtext(self):
        pass

    def test_get(self):
        self.assertEquals(None, self.root.get('nonexists'))
        self.assertEquals('1.0', self.root.get('version'))
        self.assertEquals('1', self.root[1].get('a'))
        self.assertEquals('2', self.root[1].get('{http://example.tld}b'))
        self.assertEquals('3', self.root[1].get('{http://z.example.tld}c'))

    def test_getchildren(self):
        children = self.root.getchildren()

        child = children[0]
        self.assertEquals('{http://example.tld}paragraph',
                          child.tag)
        self.assertEquals('text', child.text)
        self.assertEquals('tail', child.tail)

        child = children[1]
        self.assertEquals('{http://z.example.tld}object',
                          child.tag)

        child = children[2]
        self.assertEquals('{http://example.tld}third',
                          child.tag)

    def test_getiterator(self):
        pass

    def test_getnext(self):
        child = self.root[0]
        child = child.getnext()
        self.assertEquals('{http://z.example.tld}object',
                          child.tag)
        child = child.getnext()
        self.assertEquals('{http://example.tld}third',
                          child.tag)
        child = child.getnext()
        self.assertEquals(None, child)

    def test_getparent(self):
        parent = self.root.getparent()
        self.assertEquals(None, parent)

        for child in self.root:
            parent = child.getparent()
            self.assertEquals('{http://example.tld}document',
                              parent.tag)

    def test_getprevious(self):
        child = self.root[-1]
        self.assertEquals('{http://example.tld}third',
                          child.tag)
        child = child.getprevious()
        self.assertEquals('{http://z.example.tld}object',
                          child.tag)
        child = child.getprevious()
        self.assertEquals('{http://example.tld}paragraph',
                          child.tag)
        child = child.getprevious()
        self.assertEquals(None, child)

    def test_getroottree(self):
        elem = Element('HwpDoc')
        self.assertTrue(elem.getroottree() is not None)

    def test_index(self):
        pass

    def test_insert(self):
        pass

    def test_items(self):
        pass

    def test_iter(self):
        pass

    def test_iterancestors(self):
        span = self.root[0][0]
        it = span.iterancestors()

        parent = it.next()
        self.assertEquals('{http://example.tld}paragraph',
                          parent.tag)

        parent = it.next()
        self.assertEquals('{http://example.tld}document',
                          parent.tag)

        self.assertRaises(StopIteration, it.next)

        # with tags predicate

        it = span.iterancestors('{http://example.tld}document')

        parent = it.next()
        self.assertEquals('{http://example.tld}document',
                          parent.tag)

        self.assertRaises(StopIteration, it.next)

    def test_iterchildren(self):
        pass

    def test_descendants(self):
        pass

    def test_iterfind(self):
        pass

    def test_siblings(self):
        pass

    def test_itertext(self):
        pass

    def test_keys(self):
        self.assertEquals(set(['version']),
                          set(self.root.keys()))
        self.assertEquals(set(['a', '{http://example.tld}b',
                               '{http://z.example.tld}c']),
                          set(self.root[1].keys()))

    def test_makeelement(self):
        pass

    def test_remove(self):
        pass

    def test_replace(self):
        pass

    def test_set(self):
        self.root.set('{http://example.tld}a', '1')
        self.assertEquals('1', self.root.get('{http://example.tld}a'))
        self.root.set('{http://c.example.tld}a', '2')
        self.assertEquals('2', self.root.get('{http://c.example.tld}a'))
        self.root.set('a', '3')
        self.assertEquals('3', self.root.get('a'))

    def test_values(self):
        self.root[1].values()

    def test_xpath(self):
        nsmap = dict(x='http://example.tld')

        # element
        result = self.root.xpath('//x:paragraph', namespaces=nsmap)
        self.assertEquals(1, len(result))
        self.assertEquals('{http://example.tld}paragraph',
                          result[0].tag)

        # attribute
        result = self.root.xpath('@version', namespaces=nsmap)
        self.assertEquals(['1.0'], result)

        # string
        result = self.root.xpath('"foo"', namespaces=nsmap)
        self.assertEquals('foo', result)

        # number expression
        result = self.root.xpath('1', namespaces=nsmap)
        self.assertEquals(1.0, result)

        result = self.root.xpath('"1.0"', namespaces=nsmap)
        # should be string, but alas, it returns a number in jxml
        if sys.platform.startswith('java'):
            self.assertEquals(1.0, result)
        else:
            self.assertEquals('1.0', result)


class QNameTest(TestCase):

    text = '{http://example.tld}document'
    namespace = 'http://example.tld'
    localname = 'document'

    def test_from_text(self):
        qname = QName(self.text)
        self.assertEquals(self.text, qname.text)
        self.assertEquals(self.namespace, qname.namespace)
        self.assertEquals(self.localname, qname.localname)

        qname = QName('document')
        self.assertEquals('document', qname.text)
        self.assertEquals(None, qname.namespace)
        self.assertEquals('document', qname.localname)

    def test_from_nsuri_and_tag(self):
        qname = QName(self.namespace, self.localname)
        self.assertEquals(self.text, qname.text)
        self.assertEquals(self.namespace, qname.namespace)
        self.assertEquals(self.localname, qname.localname)

    def test_from_element(self):
        element = Element(self.text)
        qname = QName(element)
        self.assertEquals(self.text, qname.text)
        self.assertEquals(self.namespace, qname.namespace)
        self.assertEquals(self.localname, qname.localname)


class XPathTest(TestCase):

    def test_xpath(self):
        from lxml.etree import parse
        from lxml.etree import XPath
        with file('sample.xml') as f:
            doc = parse(f)

        nsmap = dict(x='http://example.tld')

        # element
        xpath = XPath('//x:paragraph', namespaces=nsmap)
        result = xpath(doc)
        self.assertEquals(1, len(result))
        self.assertEquals('{http://example.tld}paragraph',
                          result[0].tag)

        # attribute
        xpath = XPath('@version', namespaces=nsmap)
        result = xpath(doc)
        self.assertEquals(['1.0'], result)

        # string
        xpath = XPath('"foo"', namespaces=nsmap)
        result = xpath(doc)
        self.assertEquals('foo', result)

        # number
        xpath = XPath('1', namespaces=nsmap)
        self.assertEquals(1, xpath(doc))

        # string, but alas, it returns a number in jxml
        xpath = XPath('"1.0"', namespaces=nsmap)
        result = xpath(doc)
        if sys.platform.startswith('java'):
            self.assertEquals(1.0, result)
        else:
            self.assertEquals('1.0', result)

        # Boolean
        xpath = XPath('1 = 1', namespaces=nsmap)
        self.assertEquals(True, xpath(doc))


class XSLTTest(TestCase):

    def test_from_element(self):
        with open('xsl/import-test.xsl') as f:
            xsl_tree = etree.parse(f)
        etree.XSLT(xsl_tree.getroot())

    def test_xslt_with_default_parser(self):
        with open('xsl/import-test.xsl') as f:
            xsl_tree = etree.parse(f)
        transform = etree.XSLT(xsl_tree)
        result = transform(etree.XML('<hello />'))
        self.assertEquals('world', result.getroot().tag)

    def test_text_output(self):
        with open('text-output.xsl') as f:
            xsl_tree = etree.parse(f)
        transform = etree.XSLT(xsl_tree)
        result = transform(etree.XML('<hello/>'))
        self.assertEquals(None, result.getroot())
        self.assertEquals(u'world', unicode(result))
        self.assertEquals('world', str(result))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = backend
# -*- coding: utf-8 -*-
import logging
import sys
import os

logfmt = logging.Formatter((' backend %5d ' % os.getpid())
                           +'%(message)s')
logger = logging.getLogger('backend')
logger.setLevel(logging.INFO)


logger.info('backend: %s', os.getpid())
logger.info('sys.executable = %s', sys.executable)

import unohelper
g_ImplementationHelper = unohelper.ImplementationHelper()

def implementation(component_name, *services):
    def decorator(cls):
        g_ImplementationHelper.addImplementation(cls, component_name, services)
        return cls
    return decorator


from com.sun.star.task import XJob

@implementation('backend.TestRunnerJob')
class TestRunnerJob(unohelper.Base, XJob):

    def __init__(self, context):
        self.context = context

    def execute(self, arguments):
        import sys
        args = dict((nv.Name, nv.Value) for nv in arguments)

        cwd = os.getcwd()
        working_dir = args['working_dir']
        os.chdir(working_dir)
        try:
            logstream = args['logstream']
            logstream = FileFromStream(logstream)
            loghandler = logging.StreamHandler(logstream)
            loghandler.setFormatter(logfmt)
            logger.addHandler(loghandler)
            try:
                logger.info('current dir: %s', cwd)
                logger.info('working dir: %s', working_dir)
                logger.info('sys.path:')
                for x in sys.path:
                    logger.info('- %s', x)
                return self.run(args)
            finally:
                logger.removeHandler(loghandler)
        finally:
            os.chdir(cwd)

    def run(self, args):
        import cPickle
        outstream = args.get('outputstream')
        outstream = FileFromStream(outstream)

        extra_path = args.get('extra_path')
        if extra_path:
            logger.info('extra_path: %s', ' '.join(extra_path))
            sys.path.extend(extra_path)

        logconf_path = args.get('logconf_path')
        if logconf_path:
            import logging.config
            logging.config.fileConfig(logconf_path)

        from hwp5.plat import _uno
        _uno.enable()

        pickled_testsuite = args.get('pickled_testsuite')
        if not pickled_testsuite:
            logger.error('pickled_testsuite is required')
            return cPickle.dumps(dict(successful=False, tests=0, failures=0,
                                      errors=0))

        pickled_testsuite = str(pickled_testsuite)
        testsuite = cPickle.loads(pickled_testsuite)
        logger.info('Test Suite Unpickled')

        from unittest import TextTestRunner
        testrunner = TextTestRunner(stream=outstream)
        result = testrunner.run(testsuite)
        result = dict(successful=result.wasSuccessful(),
                      tests=result.testsRun,
                      failures=list(str(x) for x in result.failures),
                      errors=list(str(x) for x in result.errors))
        return cPickle.dumps(result)


import contextlib


@contextlib.contextmanager
def sandbox(working_dir, **kwargs):
    import os
    import sys

    backup = dict()
    class NOTHING:
        pass
    if not hasattr(sys, 'argv'):
        sys.argv = NOTHING

    NAMES = ['path', 'argv', 'stdin', 'stdout', 'stderr']
    for x in NAMES:
        assert x in kwargs

    backup['cwd'] = os.getcwd()
    os.chdir(working_dir)
    for x in NAMES:
        backup[x] = getattr(sys, x)
        setattr(sys, x, kwargs[x])

    try:
        yield
    finally:
        for x in NAMES:
            setattr(sys, x, backup[x])
        os.chdir(backup['cwd'])

        if sys.argv is NOTHING:
            del sys.argv


@implementation('backend.RemoteRunJob')
class RemoteRunJob(unohelper.Base, XJob):

    def __init__(self, context):
        self.context = context

    def execute(self, arguments):
        args = dict((nv.Name, nv.Value) for nv in arguments)

        logpath = args.get('logfile')
        if logpath is not None:
            logfile = file(logpath, 'a')
            loghandler = logging.StreamHandler(logfile)
            logger.addHandler(loghandler)

        import datetime
        logger.info('-'*10 + (' start at %s' % datetime.datetime.now()) + '-'*10)
        try:
            return self.run(args)
        finally:
            logger.info('-'*10 + (' stop at %s' % datetime.datetime.now()) + '-'*10)
            if logpath is not None:
                logger.removeHandler(loghandler)

    def run(self, args):
        import cPickle

        working_dir = args['working_dir']
        path = cPickle.loads(str(args['path']))
        argv = cPickle.loads(str(args['argv']))
        stdin = FileFromStream(args['stdin'])
        stdout = FileFromStream(args['stdout'])
        stderr = FileFromStream(args['stderr'])

        script = argv[0]
        with sandbox(working_dir, path=path, argv=argv, stdin=stdin,
                     stdout=stdout, stderr=stderr):
            g = dict(__name__='__main__')
            try:
                execfile(script, g)
            except SystemExit, e:
                return e.code
            except Exception, e:
                logger.exception(e)
                raise
            except:
                import traceback
                logger.error('%s' % traceback.format_exc())
                raise


@implementation('backend.ConsoleJob')
class ConsoleJob(unohelper.Base, XJob):

    def __init__(self, context):
        self.context = context

    def execute(self, arguments):
        args = dict((nv.Name, nv.Value) for nv in arguments)

        cwd = os.getcwd()
        try:
            inp = args['inp']
            outstream = args['outstream']

            outfile = FileFromStream(outstream)

            import sys
            orig = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = outfile
            try:
                console = Console(inp, outfile)
                try:
                    console.interact('LibreOffice Python Console (pid: %s)' %
                                     os.getpid())
                    return 0
                except SystemExit, e:
                    return e.code
            finally:
                sys.stdout, sys.stderr = orig
        finally:
            os.chdir(cwd)


from code import InteractiveConsole
class Console(InteractiveConsole):

    def __init__(self, inp, outfile):
        InteractiveConsole.__init__(self)
        self.inp = inp
        self.outfile = outfile

    def write(self, data):
        self.outfile.write(data)
        self.outfile.flush()

    def raw_input(self, prompt=''):
        import uno
        arg = uno.createUnoStruct('com.sun.star.beans.NamedValue')
        arg.Name = 'prompt'
        arg.Value = prompt
        args = arg,
        result = self.inp.execute(args)
        if result is None:
            raise EOFError()
        return result


class FileFromStream(object):
    ''' A file-like object based on XInputStream/XOuputStream/XSeekable

    :param stream: a stream object which implements
    com.sun.star.io.XInputStream, com.sun.star.io.XOutputStream or
    com.sun.star.io.XSeekable
    '''
    def __init__(self, stream, encoding='utf-8'):
        import uno
        self.stream = stream
        self.encoding = encoding

        if hasattr(stream, 'readBytes'):
            def read(size=None):
                if size is None:
                    data = ''
                    while True:
                        bytes = uno.ByteSequence('')
                        n_read, bytes = stream.readBytes(bytes, 4096)
                        if n_read == 0:
                            return data
                        data += bytes.value
                bytes = uno.ByteSequence('')
                n_read, bytes = stream.readBytes(bytes, size)
                return bytes.value
            self.read = read

        if hasattr(stream, 'seek'):
            self.tell = stream.getPosition

            def seek(offset, whence=0):
                if whence == 0:
                    pass
                elif whence == 1:
                    offset += stream.getPosition()
                elif whence == 2:
                    offset += stream.getLength()
                stream.seek(offset)
            self.seek = seek

        if hasattr(stream, 'writeBytes'):
            def write(s):
                if isinstance(s, unicode):
                    s = s.encode(self.encoding)
                stream.writeBytes(uno.ByteSequence(s))
            self.write = write

            def flush():
                stream.flush()
            self.flush = flush

    def close(self):
        if hasattr(self.stream, 'closeInput'):
            self.stream.closeInput()
        elif hasattr(self.stream, 'closeOutput'):
            self.stream.closeOutput()


'''
import os.path
from uno import systemPathToFileUrl
from unokit.ucb import open_url
from unokit.services import css

path = os.path.abspath('samples/sample-5017.hwp')
print path
url = systemPathToFileUrl(path)
print url
inp = open_url(url)
print inp

# 여기서 segfault
stg = css.embed.OLESimpleStorage(inp)
print stg
'''


'''
SegFault가 나는 stacktrace는 다음과 같다

StgDirEntry::StgDirEntry
    sot/source/sdstor/
StgEntry::Load
    sot/source/sdstor/
ToUpperUnicode
    sot/source/sdstor/stgelem.cxx
CharClass
    unotools/source/i18n/charclass.cxx
intl_createInstance
    unotools/source/i18n/instance.hxx

여기서 ::comphelper::getProcessServiceFactory로 얻은 XMultiServiceFactory가
null 값인 것 같다.

----

uno를 사용하는 프로그램들 (desktop app/unopkg, 각종 unittest 프로그램)은
처음 실행 시 다음과 같은 과정을 거치는 듯 하다.

1. ::cppu::defaultBootstrap_InitialComponentContext()을 호출, local context 생성
   - unorc 등을 검색, application.rdb, user.rdb 등에 접근

   - pyuno.so 의 getComponentContext()에서 수행: PYUNOLIBDIR 즉 pyuno.so가 있는
     디렉토리에서 pyuno.rc가 있으면 그것으로 초기화)
   - desktop app: appinit.cxx의 CreateApplicationServiceManager()에서 수행
   - unopkg: unopkg_misc.cxx의 bootstrapStandAlone()에서 수행.
     ucbhelper::ContentBroker도 함께 초기화한다.

2. 이렇게 생성한 local context로부터 ServiceManager를 얻어
   ::comphelper::setProcessServiceFactory()를 사용하여 프로세스 전역 service
   factory로 등록

   - uno.py와 pyuno.so는 이 작업을 하지 않는다.
   - desktop app: app.cxx의 ensureProcessServiceFactory()에서 수행
   - unopkg: unopkg_misc.cxx의 bootstrapStandAlone()에서 함께 수행.


* desktop app: desktop/source/app/
* unopkg: desktop/source/pkgchk/unopkg/

'''

logger.info('%s: end of file', __name__)

########NEW FILE########
__FILENAME__ = description
# -*- coding: utf-8 -*-
from __future__ import with_statement
import logging


logger = logging.getLogger(__name__)


NS_URI = 'http://openoffice.org/extensions/description/2006'
NS_URI_DEP = 'http://openoffice.org/extensions/description/2006'
NS_URI_XLINK = 'http://www.w3.org/1999/xlink'

NS = '{' + NS_URI + '}'
NS_DEP = '{' + NS_URI_DEP + '}'
NS_XLINK = '{' + NS_URI_XLINK + '}'


def as_dict(f):
    def wrapper(*args, **kwargs):
        return dict(f(*args, **kwargs))
    wrapper.items = f
    return wrapper


@as_dict
def get_display_name(doc):
    root = doc.getroot()
    for elt in root.findall(NS + 'display-name/' + NS + 'name'):
        yield elt.get('lang'), elt.text


def set_display_name(doc, display_name):
    import xml.etree.ElementTree as ET
    root = doc.getroot()
    dispname = ET.SubElement(root, 'display-name')
    for lang, name in display_name.items():
        elt = ET.SubElement(dispname, 'name')
        elt.set('lang', lang)
        elt.text = name


@as_dict
def get_extension_description(doc):
    root = doc.getroot()
    for elt in root.findall(NS + 'extension-description/' + NS + 'src'):
        yield elt.get('lang'), elt.get(NS_XLINK + 'href')


def set_extension_description(doc, description):
    import xml.etree.ElementTree as ET
    root = doc.getroot()
    desc = ET.SubElement(root, 'extension-description')
    for lang, url in description.items():
        elt = ET.SubElement(desc, 'src')
        elt.set('lang', lang)
        elt.set('xlink:href', url)


@as_dict
def get_publisher(doc):
    root = doc.getroot()
    for elt in root.findall(NS + 'publisher/' + NS + 'name'):
        yield elt.get('lang'), dict(name=elt.text,
                                    url=elt.get(NS_XLINK + 'href'))


def set_publisher(doc, publisher):
    import xml.etree.ElementTree as ET
    root = doc.getroot()
    pub = ET.SubElement(root, 'publisher')
    for lang, dct in publisher.items():
        elt = ET.SubElement(pub, 'name')
        elt.set('lang', lang)
        elt.set('xlink:href', dct['url'])
        elt.text = dct['name']


def get_license_accept_by(doc):
    root = doc.getroot()
    for elt in root.findall(NS + 'registration/' + NS + 'simple-license'):
        accept_by = elt.get('accept-by')
        if accept_by:
            return accept_by


def get_license(doc):
    root = doc.getroot()
    for elt in root.findall(NS + 'registration/' + NS + 'simple-license'):
        return dict((elt.get('lang'), elt.get(NS_XLINK + 'href'))
                    for elt in elt.findall(NS + 'license-text'))
    return dict()


def get_oo_min_version(doc):
    root = doc.getroot()
    for dep in root.findall(NS + 'dependencies'):
        for elt in dep.findall(NS + 'OpenOffice.org-minimal-version'):
            return elt.get('value')


class Description(object):

    @classmethod
    def parse(cls, f):
        import xml.etree.ElementTree as ET

        doc = ET.parse(f)
        root = doc.getroot()

        def getvalue(xpath, default=None):
            for elt in root.findall(xpath):
                value = elt.get('value', default)
                if value:
                    return value
            return default

        return cls(identifier=getvalue(NS + 'identifier'),
                   version=getvalue(NS + 'version'),
                   platform=getvalue(NS + 'platform', 'all'),
                   display_name=get_display_name(doc),
                   description=get_extension_description(doc),
                   publisher=get_publisher(doc),
                   license_accept_by=get_license_accept_by(doc),
                   license=get_license(doc),
                   oo_min_version=get_oo_min_version(doc))

    def __init__(self,
                 identifier='noname',
                 version='0.0',
                 platform='all',
                 display_name=dict(),
                 description=dict(),
                 publisher=dict(),
                 license_accept_by='admin',
                 license=dict(),
                 oo_min_version=None):
        ''' Generate description.xml

        :param f: output file
        :param identifier: extension identifier
        :param version: extension version
        :param platform: target platform
        :param display_name: localizations of display name
        :param description: localizations of extension description
        :param publisher: localizations of publisher
        :param license_accept_by: who is supposed to accept the license
        :param license: localization of license
        :param oo_min_version: minimal version of LibreOffice

        Each localization parameters are dicts, whose keys are language identifiers
        defined in RFC 3066.

        ``identifier`` specifies `Extension Identifier
        <http://wiki.openoffice.org/wiki/Documentation/DevGuide/Extensions/Extension_Identifiers>`_.

        ``version`` specifies `Extension Version
        <http://wiki.openoffice.org/wiki/Documentation/DevGuide/Extensions/Extension_Versions>`_.

        ``platform`` specifies supposed `Target Platform
        <http://wiki.openoffice.org/wiki/Documentation/DevGuide/Extensions/Target_Platform>`_  on which this extension
        runs. Default value is ``all``.

        ``display_name`` specifies localized `Display Names
        <http://wiki.openoffice.org/wiki/Documentation/DevGuide/Extensions/Display_Name>`_.
        It's a localization dict whose values are localized unicode strings, e.g.::

            display_name = {
                'en': 'Example Filter',
                'ko': u'예제 필터'
            }

        Values of ``description`` is a URL of description file, e.g.::

            description = {
                'en': 'description/en.txt',
                'ko': 'description/ko.txt'
            }

        ``publisher`` specifies `Publisher Information
        <http://wiki.openoffice.org/wiki/Documentation/DevGuide/Extensions/Publisher_Information>`_.
        It's a localization dict whose values are dicts themselves, which have
        ``name`` and ``url``.  ``name`` is a localized name of the publisher and
        ``url`` is a URL of the publisher. For example::

            publisher = {
                'en': {
                    'name': 'John Doe',
                    'url': 'http://example.tld'
                },
                'ko': {
                    'name': u'홍길동',
                    'url': 'http://example.tld'
                }
            }

        Optional ``license_accept_by`` specifies who is supposed to accept the
        license. ``admin`` or ``user``. Default value is 'admin'.

        Optional ``license`` is a localization dict whose values are an URL of
        license file. For example::

            license = {
                'en': 'registration/COPYING'
            }

        See `Simple License
        <http://wiki.openoffice.org/wiki/Documentation/DevGuide/Extensions/Simple_License>`_.
        '''
        self.identifier = identifier
        self.version = version
        self.platform = platform
        self.display_name = display_name
        self.description = description
        self.publisher = publisher
        self.license_accept_by = license_accept_by
        self.license = license
        self.oo_min_version = oo_min_version

    def write(self, f):

        # see http://wiki.openoffice.org/wiki/Documentation/DevGuide/Extensions/Description_of_XML_Elements

        import xml.etree.ElementTree as ET

        root = ET.Element('description', {'xmlns': NS_URI,
                                          'xmlns:dep': NS_URI_DEP,
                                          'xmlns:xlink': NS_URI_XLINK})
        doc = ET.ElementTree(root)

        ET.SubElement(root, 'identifier').set('value', self.identifier)
        ET.SubElement(root, 'version').set('value', self.version)
        ET.SubElement(root, 'platform').set('value', self.platform)

        set_display_name(doc, self.display_name)

        set_extension_description(doc, self.description)

        set_publisher(doc, self.publisher)

        if self.license:
            reg = ET.SubElement(root, 'registration')
            lic = ET.SubElement(reg, 'simple-license')
            lic.set('accept-by', self.license_accept_by)
            for lang, url in self.license.items():
                elt = ET.SubElement(lic, 'license-text')
                elt.set('lang', lang)
                elt.set('xlink:href', url)

        if self.oo_min_version is not None:
            dep = ET.SubElement(root, 'dependencies')
            minver = ET.SubElement(dep, 'OpenOffice.org-minimal-version')
            minver.set('dep:name', 'LibreOffice ' + self.oo_min_version)
            minver.set('value', self.oo_min_version)

        f.write('<?xml version="1.0" encoding="utf-8"?>')
        doc.write(f, encoding='utf-8')

    def required_files(self):
        for url in self.description.values():
            yield url
        for url in self.license.values():
            yield url


def print_human_readable(desc, root_stg=None):
    ''' Print summary in human readable form.

    :param desc: an instance of Description
    :param root_stg: root storage of description.xml
    '''
    from storage import resolve_path
    print 'identifier:', desc.identifier
    print 'version:', desc.version
    print 'platform:', desc.platform

    print 'display-name:'
    for lang, name in desc.display_name.items():
        print '  [%s] %s' % (lang, name)

    print 'extension-description:'
    for lang, url in desc.description.items():
        if not root_stg or resolve_path(root_stg, url):
            state = ''
        else:
            state = ' -- MISSING'
        print '  [%s] %s%s' % (lang, url, state)

    print 'publisher:'
    for lang, publisher in desc.publisher.items():
        print '  [%s] %s (%s)' % (lang,
                                       publisher['name'],
                                       publisher['url'])
    if desc.license:
        print 'license: accept-by', desc.license_accept_by
        for lang, url in desc.license.items():
            if not root_stg or resolve_path(root_stg, url):
                state = ''
            else:
                state = ' -- MISSING'
            print '  [%s] %s%s' % (lang, url, state)

    if desc.oo_min_version:
        print 'dependencies:'
        print '  LibreOffice minimal version:', desc.oo_min_version


def init_main():
    doc = '''Usage: oxt-desc-init [options] <desc-file>

    --help      Print this screen.
    '''

    from docopt import docopt
    args = docopt(doc)
    logging.basicConfig(level=logging.INFO)

    description = Description(identifier='tld.example',
                              version='0.1',
                              display_name=dict(en='Example extension'),
                              publisher=dict(en=dict(name='Publisher Name',
                                                     url='http://example.tld')),
                              license=dict(url=dict(en='COPYING')),
                              description=dict(en='description/en.txt'))
    with file(args['<desc-file>'], 'w') as f:
        description.write(f)


def show_main():
    doc = '''Usage: oxt-desc-show [options] <desc-file>

    --help      Show this screen.
    '''
    from docopt import docopt
    args = docopt(doc)
    logging.basicConfig(level=logging.INFO)

    with file(args['<desc-file>']) as f:
        desc = Description.parse(f)

    print_human_readable(desc)


def version_main():
    doc = '''Usage: oxt-desc-version [options] <desc-file> [<new-version>]

    --help      Show this screen.
    '''
    from docopt import docopt
    args = docopt(doc)
    logging.basicConfig(level=logging.INFO)

    with file(args['<desc-file>'], 'r') as f:
        desc = Description.parse(f)

    new_version = args['<new-version>']
    if new_version is not None:
        logger.info('old: %s', desc.version)
        desc.version = new_version
        logger.info('new: %s', desc.version)
        with file(args['<desc-file>'], 'w') as f:
            desc.write(f)
    else:
        print desc.version


def ls_main():
    doc = '''Usage: oxt-desc-ls [options] <desc-file>

    --help      Show this screen.
    '''
    from docopt import docopt
    args = docopt(doc)
    logging.basicConfig(level=logging.INFO)

    with file(args['<desc-file>']) as f:
        desc = Description.parse(f)

    for path in desc.required_files():
        print path

########NEW FILE########
__FILENAME__ = manifest
# -*- coding: utf-8 -*-
from __future__ import with_statement
import logging


logger = logging.getLogger(__name__)


NS_URI = 'urn:oasis:names:tc:opendocument:xmlns:manifest:1.0'
NS_URI = 'http://openoffice.org/2001/manifest'
NS_PREFIX = 'manifest'


class Manifest(object):
    ''' Represent ``META-INF/manifest.xml`` file.
    '''

    def __init__(self, namespace_uri=NS_URI):
        self.entries = dict()
        self.NS_URI = namespace_uri

    @property
    def NS(self):
        return '{' + self.NS_URI + '}'

    def __setitem__(self, full_path, value):
        if isinstance(value, basestring):
            value = {'media-type': value}
        self.entries[full_path] = value

    def __getitem__(self, full_path):
        return self.entries[full_path]

    def __delitem__(self, full_path):
        del self.entries[full_path]

    def __iter__(self):
        for full_path in sorted(self.entries):
            yield full_path
    
    def add_file(self, full_path, media_type):
        self[full_path] = {'media-type': media_type}

    def load(self, f):
        if isinstance(f, basestring):
            with file(f) as f:
                return self.load(f)
        import xml.etree.ElementTree as ET

        doc = ET.parse(f)
        root = doc.getroot()
        NS = self.NS
        for e in root.findall(NS + 'file-entry'):
            self.add_file(e.get(NS + 'full-path'),
                          e.get(NS + 'media-type'))

    def dump(self, f):
        import xml.etree.ElementTree as ET

        root = ET.Element(NS_PREFIX + ':manifest',
                          {'xmlns:' + NS_PREFIX: self.NS_URI})
        doc = ET.ElementTree(root)
        for path in self:
            e = self.entries[path]
            attrs = dict((NS_PREFIX + ':' + k, v)
                         for k, v in e.items())
            attrs[NS_PREFIX + ':full-path'] = path
            ET.SubElement(root, NS_PREFIX + ':file-entry', attrs)

        f.write('<?xml version="1.0" encoding="utf-8"?>')
        doc.write(f, encoding='utf-8')

    def save(self, path):
        with file(path, 'w') as f:
            self.dump(f)


def init_main():
    doc = '''Usage: oxt-manifest-init [options] <manifest-file>

    --help          Show this screen.
    '''
    from docopt import docopt
    args = docopt(doc)
    logging.basicConfig(level=logging.INFO)

    with file(args['<manifest-file>'], 'w') as f:
        manifest = Manifest()
        manifest.dump(f)


def ls_main():
    doc = '''Usage: oxt-manifest-ls [options] <manifest-file>

    --help          Show this screen.
    '''
    from docopt import docopt
    args = docopt(doc)
    logging.basicConfig(level=logging.INFO)

    with file(args['<manifest-file>']) as f:
        manifest = Manifest()
        manifest.load(f)

    for path in manifest:
        e = manifest[path]
        print ' '.join([path, e['media-type']])


def add_main():
    doc = '''Usage: oxt-manifest-add [options] <manifest-file> <file> <media-type>

    --help          Show this screen.

    '''
    from docopt import docopt

    args = docopt(doc)
    logging.basicConfig(level=logging.INFO)

    with file(args['<manifest-file>']) as f:
        manifest = Manifest()
        manifest.load(f)

    media_type = args['<media-type>']
    path = args['<file>']

    manifest[path] = media_type
    logger.info('Add %s: %s', path, media_type)

    with file(args['<manifest-file>'], 'w') as f:
        manifest.dump(f)


def rm_main():
    doc = '''Usage: oxt-manifest-rm [options] <manifest-file> <files>...

    -r <root-dir>   Project root. If omitted, current directory will be used.
    --help          Show this screen.

    '''
    from docopt import docopt

    args = docopt(doc)
    logging.basicConfig(level=logging.INFO)

    with file(args['<manifest-file>']) as f:
        manifest = Manifest()
        manifest.load(f)

    for path in args['<files>']:
        if path in manifest:
            del manifest[path]
            logger.info('RM %s', path)
        else:
            logger.warning('Skip %s; not found', path)

    with file(args['<manifest-file>'], 'w') as f:
        manifest.dump(f)

########NEW FILE########
__FILENAME__ = package
# -*- coding: utf-8 -*-
from __future__ import with_statement
import logging
import os.path
from storage import open_storage
from storage import resolve_path
from storage import makedirs_to_file
from storage import put_file
from storage import copy_file
from storage import iterate_files_recursively
from storage._zipfile import ZipFileStorage
from storage.fs import FileSystemStorage
from manifest import Manifest
from description import Description


logger = logging.getLogger(__name__)


def is_package(folder):
    if 'META-INF' not in folder:
        return False
    if 'manifest.xml' not in folder['META-INF']:
        return False
    return True


MANIFEST_PATH = os.path.join('META-INF', 'manifest.xml')
DESCRIPTION_PATH = 'description.xml'


def add_file(stg, manifest, path, full_path, media_type):
    ''' add a file into the storage and manifest.

    :param stg: a storage
    :param manifest: an instance of Manifest
    :param path: path to the file on the filesystem.
    :param full_path: ``manifest:full-path`` value of ``manifest:file-entry``
    :param media_type: ``manifest:media-type`` value of ``manifest:file-entry``
    '''
    node = makedirs_to_file(stg, full_path)
    put_file(node, path)
    manifest[full_path] = media_type
    return node


def add_component_file(stg, manifest, path, full_path, type, platform=None):
    ''' add a component file.

    :param stg: a storage
    :param manifest: an instance of Manifest
    :param path: path to the file on the filesystem.
    :param full_path: ``manifest:full-path`` value of ``manifest:file-entry``
    :param type: ``native``, ``Java``, ``Python`` or None
    :param platform: supposed platform to run this component.

    if ``type`` is None, this component is meant to be registered with
    `Passive Component Registration
    <http://wiki.openoffice.org/wiki/Documentation/DevGuide/Extensions/Passive_Component_Registration>`_
    and the file specified with ``path`` should be an XML file, which is
    defined in the document above.

    For more informations, see `File Format
    <http://wiki.openoffice.org/wiki/Documentation/DevGuide/Extensions/File_Format>`_.
    '''
    mimetype = 'application/vnd.sun.star.uno-component'
    if type:
        mimetype += '; ' + type
    if platform:
        mimetype += '; ' + platform
    return add_file(stg, manifest, path, full_path, mimetype=mimetype)


def add_type_library(stg, manifest, path, full_path, type):
    ''' add a UNO type library.

    :param stg: a storage
    :param manifest: an instance of Manifest
    :param type: ``RDB`` or ``Java``
    '''

    typelib_extensions = dict(RDB='.rdb', Java='.jar')

    if type not in typelib_extensions.keys():
        raise ValueError('type: unsupported value of %r' % type)

    if not full_path.lower().endswith(typelib_extensions[type]):
        msg = 'adding %r type library %r with name %r: really intended?'
        logger.warning(msg, type, path, full_path)

    mimetype = 'application/vnd.sun.star.uno-typelibrary'
    mimetype += '; type=' + type
    return add_file(stg, manifest, path, full_path, mimetype)


def add_basic_library(stg, manifest, path, full_path):
    ''' add a basic library

    :param stg: a storage
    :param manifest: an instance of Manifest
    '''
    mimetype = 'application/vnd.sun.star.basic-library'
    return add_file(stg, manifest, path, full_path, mimetype=mimetype)


def add_dialog_library(stg, manifest, path, full_path):
    ''' add a dialog library

    :param stg: a storage
    :param manifest: an instance of Manifest
    '''
    mimetype = 'application/vnd.sun.star.dialog-library'
    return add_file(stg, manifest, path, full_path, mimetype=mimetype)


def add_configuration_data_file(stg, manifest, path, full_path):
    ''' add a configuration data file.

    :param stg: a storage
    :param manifest: an instance of Manifest
    '''
    mimetype = 'application/vnd.sun.star.configuration-data'
    return add_file(stg, manifest, path, full_path, mimetype=mimetype)


def add_configuration_schema_file(stg, manifest, path, full_path):
    ''' add a configuration schema file.

    :param stg: a storage
    :param manifest: an instance of Manifest
    '''
    mimetype = 'application/vnd.sun.star.configuration-schema'
    return add_file(stg, manifest, path, full_path, mimetype=mimetype)


def build(package_path, manifest, description, files=dict(),
          storage_factory=ZipFileStorage):
    ''' Build a OXT Package.

    :param package_path: path to an .oxt package to be built
    :param manifest: an instance of Manifest
    :param description: an instance of Description
    :param files: package files, in a form of (path, node) dict
    :param storage_factory: storage factory for the package.
                            Default to ZipFileStorage
    '''

    assert not any(node is None for node in files.values())
    assert all(path in files for path in manifest)
    assert all(path in files for path in description.required_files())

    logger.info('creating %s', package_path)
    with storage_factory(package_path, 'w') as stg:
        logger.info('writing %s', MANIFEST_PATH)
        manifest_node = makedirs_to_file(stg, MANIFEST_PATH)
        with manifest_node.open('w') as f:
            manifest.dump(f)

        logger.info('writing %s', DESCRIPTION_PATH)
        desc_node = makedirs_to_file(stg, DESCRIPTION_PATH)
        with desc_node.open('w') as f:
            description.write(f)

        for path in sorted(files):
            node = files[path]
            logger.info('writing %s', path)
            dest = makedirs_to_file(stg, path)
            copy_file(node, dest)


def build_from(package_path,
               src_folder,
               manifest_path=None,
               description_path=None,
               files=[],
               excludes=[],
               storage_factory=ZipFileStorage):

    if manifest_path:
        with file(manifest_path) as f:
            manifest = Manifest()
            manifest.load(f)
    else:
        node = resolve_path(src_folder, MANIFEST_PATH)
        if node:
            with node.open() as f:
                manifest = Manifest()
                manifest.load(f)
        else:
            logger.error('%s: not found' % MANIFEST_PATH)
            raise IOError('%s: not found' % MANIFEST_PATH)

    if description_path:
        with file(description_path) as f:
            description = Description.parse(f)
    else:
        node = resolve_path(src_folder, DESCRIPTION_PATH)
        if node:
            with node.open() as f:
                description = Description.parse(f)
        else:
            raise IOError('%s: not found' % DESCRIPTION_PATH)

    package_path = make_output_path(package_path, description)
    package_files = dict()

    from itertools import chain
    required_files = chain(manifest, description.required_files())
    for path in required_files:
        node = resolve_path(src_folder, path)
        if node is None:
            raise IOError('%s: not found' % path)
        package_files[path] = node

    files = ((path, resolve_path(src_folder, path)) for path in files)
    files = expand_folders(files)
    files = exclude_files(excludes, files)
    package_files.update(files)

    return build(package_path, manifest, description, package_files,
                 storage_factory=storage_factory)


def make_output_path(path, desc=None):
    if os.path.isdir(path):
        dirname = path
        name = ''
    else:
        dirname, name = os.path.split(path)

    # default name will be used if not given
    if name == '':
        if desc is None:
            raise ValueError('%s: invalid path' % path)
        name = package_name_from_desc(desc)

    return os.path.join(dirname, name)


def package_name_from_desc(desc):
    id = desc.identifier
    version = desc.version
    if version:
        return '-'.join([id, version]) + '.oxt'
    else:
        return id + '.oxt'


def expand_folders(resolved_nodes):
    for path, node in resolved_nodes:
        if hasattr(node, '__iter__'):
            for path, node in iterate_files_recursively(node, path):
                yield path, node
        else:
            yield path, node


def exclude_files(patterns, resolved_nodes):
    from fnmatch import fnmatch
    for path, node in resolved_nodes:
        excluded = False
        for pat in patterns:
            if fnmatch(path, pat):
                logger.info('exclude %s (by %s)', path, pat)
                excluded = True
        if not excluded:
            yield path, node


def init_main():
    doc = '''Usage: oxt-pkg-init [options] <package-path>

    --help      Print this screen.
    '''

    from docopt import docopt
    args = docopt(doc)
    logging.basicConfig(level=logging.INFO)

    package_path = args['<package-path>']

    manifest = Manifest()
    description = Description()

    with open_storage(package_path, 'w') as stg:
        with makedirs_to_file(stg, MANIFEST_PATH).open('w') as f:
            manifest.dump(f)
        with makedirs_to_file(stg, DESCRIPTION_PATH).open('w') as f:
            description.write(f)


def show_main():
    doc = '''Usage: oxt-pkg-show [options] <package-path>

    --help      Print this screen.
    '''

    from docopt import docopt
    args = docopt(doc)
    logging.basicConfig(level=logging.INFO)

    package_path = args['<package-path>']
    with open_storage(package_path) as pkg:
        with resolve_path(pkg, MANIFEST_PATH).open() as f:
            manifest = Manifest()
            manifest.load(f)

        with resolve_path(pkg, DESCRIPTION_PATH).open() as f:
            description = Description.parse(f)

        from description import print_human_readable
        print_human_readable(description, pkg)

        for path in manifest:
            item = manifest[path]
            print path, item['media-type'],
            node = resolve_path(pkg, path)
            if node:
                print '-- OK'
            else:
                print '-- MISSING'


def build_main():
    doc = '''Usage: oxt-pkg-build [options] <src-folder> <add-files>...

    -o OUTPUT-PATH                  Output path
    -m MANIFEST                     META-INF/manifest.xml
    -d DESCRIPT                     description.xml
    -E EXCLUDE, --exclude=EXCLUDE   exclude patterns; separated by %r.
                --help              Print this screen.

    <src-folder>                    root folder containing package files
    <add-files>                     additional files (relative to <src-folder>)
    ''' % os.pathsep

    from docopt import docopt
    args = docopt(doc)
    logging.basicConfig(level=logging.INFO)

    src_folder_path = args['<src-folder>']
    add_files = args['<add-files>']
    output_path = args['-o'] or '.'
    manifest_path = args['-m']
    description_path = args['-d']
    excludes = args['--exclude'] or ''
    excludes = excludes.strip().split(os.pathsep)

    with FileSystemStorage(src_folder_path) as src_folder:
        build_from(output_path,
                   src_folder,
                   manifest_path=manifest_path,
                   description_path=description_path,
                   files=add_files,
                   excludes=excludes)


def check_main():
    doc = '''Usage: oxt-pkg-show [options] <package-path>

    --help      Print this screen.
    '''

    from docopt import docopt
    args = docopt(doc)
    logging.basicConfig(level=logging.INFO)

    package_path = args['<package-path>']
    with open_storage(package_path) as pkg:
        with resolve_path(pkg, MANIFEST_PATH).open() as f:
            manifest = Manifest()
            manifest.load(f)

        with resolve_path(pkg, DESCRIPTION_PATH).open() as f:
            description = Description.parse(f)

        missing = dict()

        for path in manifest:
            node = resolve_path(pkg, path)
            if node is None:
                missing[path] = MANIFEST_PATH

        for path in description.required_files():
            node = resolve_path(pkg, path)
            if node is None:
                missing[path] = DESCRIPTION_PATH

        if missing:
            for path in sorted(missing):
                referer = missing[path]
                logger.error('%s: MISSING (refered in %s)',
                             path, referer)
            raise SystemExit(1)
        else:
            logger.info('%s: OK, identifier=%s, version=%s', package_path,
                        description.identifier, description.version)

########NEW FILE########
__FILENAME__ = remote
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010 mete0r@sarangbang.or.kr
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from __future__ import with_statement
import contextlib
import logging


logger = logging.getLogger(__name__)


@contextlib.contextmanager
def soffice_subprocess(**kwargs):
    ''' Create an remote instance of soffice '''

    args = [kwargs.get('soffice', 'soffice')]

    if 'accept' in kwargs:
        args.append('--accept=%s' % kwargs['accept'])
    
    if kwargs.get('headless', True):
        args.append('--headless')

    if kwargs.get('invisible', True):
        args.append('--invisible')

    if kwargs.get('nologo', True):
        args.append('--nologo')

    if kwargs.get('norestore', True):
        args.append('--norestore')

    if kwargs.get('nodefault', True):
        args.append('--nodefault')

    if kwargs.get('nofirstwizard', True):
        args.append('--nofirstwizard')

    import subprocess
    p = subprocess.Popen(args)
    pid = p.pid
    logger.info('soffice(%s) has been started.', pid)
    try:
        yield p
    finally:
        import time
        n = 0
        p.poll()
        while p.returncode is None:
            n += 1
            if n > 3:
                p.kill()
                logger.info('trying to kill soffice(%s)', pid)
                return
            p.terminate()
            time.sleep(1)
            p.poll()
        logger.info('soffice(%s) has been terminated with exit code %d',
                    pid, p.returncode)


def connect_remote_context(uno_link, max_tries=10):
    ''' Connect to the remote soffice instance and get the context. '''

    from unokit.services import css
    resolver = css.bridge.UnoUrlResolver()
    uno_url = 'uno:'+uno_link+'StarOffice.ComponentContext'
    logger.info('uno_url: %s', uno_url)
    from com.sun.star.connection import NoConnectException
    while True:
        max_tries -= 1

        try:
            return resolver.resolve(uno_url)
        except NoConnectException, e:
            if max_tries <= 0:
                raise
            logger.info('%s - retrying', type(e).__name__)

            import time
            time.sleep(1)
            continue


@contextlib.contextmanager
def new_remote_context(pipe='oxt.tool', retry=3, make_current=True, **kwargs):
    ''' Create a remote soffice instance and get its context

    :param pipe: connection pipe name
    :param retry: connect retry count; default True.
    :param make_current: whether the remote context would be pushed to be
        current context; default True.
    :param **kwargs: arguments to soffice_subprocess()
    :returns: remote context
    '''
    uno_link = 'pipe,name=%s;urp;' % pipe

    logger.debug('uno_link: %s', uno_link)

    kwargs['accept'] = uno_link
    while retry >= 0:
        with soffice_subprocess(**kwargs):
            import time
            time.sleep(1)
            try:
                context = connect_remote_context(uno_link, max_tries=10)
            except Exception, e:
                logger.exception(e)
                retry -= 1
                continue

            if make_current:
                import unokit.contexts
                unokit.contexts.push(context)
                try:
                    yield context
                finally:
                    unokit.contexts.pop()
            else:
                yield context
            return


class RemoteContextLayer:

    @classmethod
    def setUp(cls):
        cls.context = new_remote_context()
        cls.context.__enter__()

    @classmethod
    def tearDown(cls):
        cls.context.__exit__(None, None, None)


########NEW FILE########
__FILENAME__ = fs
# -*- coding: utf-8 -*-
from __future__ import with_statement
import logging
import os.path
from contextlib import contextmanager


logger = logging.getLogger(__name__)


class FileSystemNode(object):

    def __init__(self, path):
        self.path = path


class FileSystemFile(FileSystemNode):

    def open(self, *args, **kwargs):
        return file(self.path, *args, **kwargs)

    @contextmanager
    def path_on_filesystem(self):
        yield self.path

    def delete(self):
        os.unlink(self.path)


class FileSystemFolder(FileSystemNode):

    def __iter__(self):
        return iter(os.listdir(self.path))

    def __getitem__(self, name):
        if name in self:
            path = os.path.join(self.path, name)
            if os.path.isdir(path):
                return FileSystemFolder(path=path)
            else:
                return FileSystemFile(path=path)
        raise KeyError(name)

    def file(self, name):
        path = os.path.join(self.path, name)
        return FileSystemFile(path)
    
    def folder(self, name):
        path = os.path.join(self.path, name)
        os.mkdir(path)
        return FileSystemFolder(path)


class FileSystemStorage(FileSystemFolder):

    def __init__(self, path, mode='r'):
        if not os.path.exists(path):
            if mode == 'r':
                raise IOError('%s: not found' % path)
            elif mode in ('a', 'w'):
                os.makedirs(path)
        if not os.path.isdir(path):
            raise IOError('%s: not a directory' % path)
        FileSystemFolder.__init__(self, path)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

########NEW FILE########
__FILENAME__ = path
# -*- coding: utf-8 -*-
from __future__ import with_statement
import logging
import os


logger = logging.getLogger(__name__)


def split(path):
    path_segments = path.split(os.sep)
    path_segments = (seg for seg in path_segments if seg)
    path_segments = list(path_segments)
    return path_segments


def get_ancestors(path):
    path_segments = split(path)
    path = ''
    for seg in path_segments[:-1]:
        path = os.path.join(path, seg)
        yield path

########NEW FILE########
__FILENAME__ = _zipfile
# -*- coding: utf-8 -*-
from __future__ import with_statement
import logging
import os.path
from zipfile import ZIP_DEFLATED
from path import split as path_split
from path import get_ancestors as path_ancestors


logger = logging.getLogger(__name__)


def zipfile_nodes(zipfile):
    seen = set()
    for path in zipfile.namelist():
        for anc_path in path_ancestors(path):
            if anc_path not in seen:
                yield anc_path, ZipFileFolder(zipfile, anc_path)
                seen.add(anc_path)
        if path not in seen:
            if path.endswith('/'):
                yield path, ZipFileFolder(zipfile, path)
            else:
                yield path, ZipFileFile(zipfile, path)
            seen.add(path)


class ZipFileNode(object):
    
    def __init__(self, zipfile, path):
        self.zipfile = zipfile
        self.path = path


class ZipFileFile(ZipFileNode):

    def open(self, mode='r', compress_type=ZIP_DEFLATED):
        if mode.startswith('r'):
            return ZipFileStream(self.zipfile.open(self.path, mode))
        elif mode == 'w':
            return ZipFileStream(ZipFileWritable(self.zipfile, self.path,
                                                 compress_type=compress_type))

    def put(self, filesystem_path, compress_type=ZIP_DEFLATED):
        self.zipfile.write(filesystem_path, self.path, compress_type)


class ZipFileFolder(ZipFileNode):

    def childs(self):
        prefix = path_split(self.path)
        prefix_len = len(prefix)
        for path, node in zipfile_nodes(self.zipfile):
            path_segments = path_split(path)
            if len(path_segments) == prefix_len + 1:
                if path_segments[:prefix_len] == prefix:
                    yield path_segments[-1], node

    def __iter__(self):
        for name, node in self.childs():
            yield name

    def __getitem__(self, name):
        for node_name, node in self.childs():
            if node_name == name:
                return node
        raise KeyError(name)

    def file(self, name):
        path = os.path.join(self.path, name)
        return ZipFileFile(self.zipfile, path)

    def folder(self, name):
        path = os.path.join(self.path, name)
        return ZipFileFolder(self.zipfile, path)


class ZipFileStorage(ZipFileFolder):

    def __init__(self, *args, **kwargs):
        import zipfile
        self.zipfile = zipfile.ZipFile(*args, **kwargs)
        self.path = ''

    def childs(self):
        for path, node in zipfile_nodes(self.zipfile):
            path_segments = path_split(path)
            if len(path_segments) == 1:
                yield path_segments[-1], node

    def close(self):
        self.zipfile.close()

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()


class ZipFileStream(object):

    def __init__(self, stream):
        self.stream = stream

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def __enter__(self):
        return self.stream

    def __exit__(self, *args, **kwargs):
        self.close()


class ZipFileWritable(object):

    def __init__(self, zipfile, path, compress_type=ZIP_DEFLATED):
        self.zipfile = zipfile
        self.path = path
        self.compress_type = compress_type

        import tempfile
        fd, tmp_path = tempfile.mkstemp()
        self.tmp_f = os.fdopen(fd, 'w')
        self.tmp_path = tmp_path

    def __getattr__(self, name):
        return getattr(self.tmp_f, name)

    def close(self):
        self.tmp_f.close()
        self.zipfile.write(self.tmp_path, self.path, self.compress_type)
        os.unlink(self.tmp_path)

########NEW FILE########
__FILENAME__ = mixin_storage
# -*- coding: utf-8 -*-
from __future__ import with_statement
from oxt_tool.storage import resolve_path
from oxt_tool.storage import makedirs
from oxt_tool.storage import makedirs_to_file
from oxt_tool.storage import put_file
from oxt_tool.storage import get_file
from oxt_tool.storage import openable_path_on_filesystem
from oxt_tool.storage import copy_file


class StorageTestMixin(object):

    def test_storage(self):
        stg = self.create_fixture_storage()
        self.assertTrue(hasattr(stg, 'close'))
        try:
            self.assertTrue(hasattr(stg, '__enter__'))
            self.assertTrue(hasattr(stg, '__exit__'))
        finally:
            stg.close()

    def test_folder_in(self):
        with self.create_fixture_folder() as folder:
            self.assertTrue('bar.txt' in folder)
            self.assertTrue('baz.txt' in folder)
            self.assertTrue('bar' in folder)
            self.assertFalse('nonexists' in folder)

    def test_folder_iterate(self):
        with self.create_fixture_folder() as folder:
            self.assertEquals(set(['bar.txt', 'baz.txt', 'bar']),
                              set(folder))

    def test_folder_getitem(self):
        with self.create_fixture_folder() as folder:
            self.assertTrue(hasattr(folder['bar.txt'], 'open'))
            self.assertTrue(hasattr(folder['baz.txt'], 'open'))
            self.assertTrue(hasattr(folder['bar'], '__iter__'))
            try:
                folder['nonexists'] 
                assert False, 'KeyError expected'
            except KeyError:
                pass

    def test_file_open_for_reading(self):
        with self.create_fixture_folder() as folder:
            f = folder['bar.txt'].open()
            try:
                self.assertTrue(hasattr(f, '__enter__'))
                self.assertTrue(hasattr(f, '__exit__'))
                self.assertEquals('Hello', f.read())
            finally:
                f.close()

    def test_file_open_for_writing(self):
        with self.create_fixture_folder() as folder:
            f = folder['bar.txt'].open('w')
            try:
                self.assertTrue(hasattr(f, '__enter__'))
                self.assertTrue(hasattr(f, '__exit__'))
                self.assertTrue(hasattr(f, 'fileno'))
                f.write('Hello World')
            finally:
                f.close()

        with self.get_fixture_folder() as folder:
            f = folder['bar.txt'].open()
            try:
                self.assertEquals('Hello World', f.read())
            finally:
                f.close()

    def test_folder_new_file(self):
        with self.create_fixture_folder() as folder:
            self.assertTrue('new-file.txt' not in folder)
            node = folder.file('new-file.txt')
            f = node.open('w')
            try:
                f.write('new-file-contents')
            finally:
                f.close()

        with self.get_fixture_folder() as folder:
            self.assertTrue('new-file.txt' in folder)
            node = folder['new-file.txt']
            f = node.open()
            try:
                self.assertEquals('new-file-contents',
                                  f.read())
            finally:
                f.close()

    def test_folder_new_folder(self):
        with self.create_fixture_folder() as folder:
            self.assertTrue('new-folder' not in folder)
            new_folder = folder.folder('new-folder')

            # we can assert that the new folder exists
            # only if there are at least one file in the folder.
            # (e.g. zipfile)
            node = new_folder.file('file-in-new-folder')
            f = node.open('w')
            try:
                f.write('hello')
            finally:
                f.close()

        with self.get_fixture_folder() as folder:
            self.assertTrue('new-folder' in folder)

    def test_resolve_path(self):
        with self.create_fixture_folder() as folder:
            res = resolve_path(folder, '')
            self.assertEquals(folder, res)

            res = resolve_path(folder, '/')
            self.assertEquals(folder, res)

    def test_makedirs(self):
        import os.path

        dirname = '1'
        path = os.path.join(dirname, 'marker')
        with self.create_fixture_folder() as folder:
            res = makedirs(folder, '')
            self.assertEquals(folder, res)

            fld = makedirs(folder, dirname)
            with fld.file('marker').open('w') as f:
                f.write(dirname)
        with self.get_fixture_folder() as folder:
            node = resolve_path(folder, path)
            with node.open() as f:
                self.assertEquals(dirname, f.read())

        dirname = os.path.join(dirname, '2')
        path = os.path.join(dirname, 'marker')
        with self.create_fixture_folder() as folder:
            fld = makedirs(folder, dirname)
            with fld.file('marker').open('w') as f:
                f.write(dirname)
        with self.get_fixture_folder() as folder:
            node = resolve_path(folder, path)
            with node.open() as f:
                self.assertEquals(dirname, f.read())

        # on existing non-folder
        dirname = 'bar.txt'
        with self.create_fixture_folder() as folder:
            try:
                makedirs(folder, dirname)
                assert False, 'exception expected'
            except:
                pass

        # under existing non-folder
        dirname = os.path.join(dirname, 'should-fail')
        with self.create_fixture_folder() as folder:
            try:
                makedirs(folder, dirname)
                assert False, 'exception expected'
            except:
                pass
        with self.get_fixture_folder() as folder:
            self.assertEquals(None, resolve_path(folder, dirname))

    def test_makedirs_to_file(self):
        import os.path
        path = os.path.join('hello', 'world', 'makedirs')
        with self.create_fixture_folder() as folder:
            node = makedirs_to_file(folder, path)
            with node.open('w'):
                pass
        with self.get_fixture_folder() as folder:
            node = resolve_path(folder, path)
            self.assertTrue(node is not None)

    def test_file_put(self):
        import os
        data = os.urandom(5000)
        path = self.id() + '.bin'
        with file(path, 'w') as f:
            f.write(data)
        with self.create_fixture_folder() as folder:
            node = folder.file('new-file')
            put_file(node, path)
        with self.get_fixture_folder() as folder:
            node = folder['new-file']
            with node.open() as f:
                self.assertEquals(data, f.read())

    def test_file_get(self):
        path = self.id() + '.got'
        with self.create_fixture_folder() as folder:
            node = folder['bar.txt']
            get_file(node, path)
        with file(path) as f:
            self.assertEquals('Hello', f.read())

    def test_openable_path_on_filesystem(self):
        with self.create_fixture_folder() as folder:
            with folder.file('new-file').open('w') as f:
                f.write('new-content')
            node = folder['new-file']
            with openable_path_on_filesystem(node) as path:
                with file(path) as f:
                    self.assertEquals('new-content', f.read())

            with openable_path_on_filesystem(node, writeback=True) as path:
                with file(path, 'w') as f:
                    f.write('modified-content')
            with node.open() as f:
                self.assertEquals('modified-content', f.read())

    def test_file_copy(self):
        with self.create_fixture_folder() as testee:

            #
            # copy from/to zipfile
            #
            from oxt_tool.storage._zipfile import ZipFileStorage
            zfs = ZipFileStorage(self.id() + '.zipstg.zip', 'a')
            with zfs.file('from-zipfile').open('w') as f:
                f.write('copied-from-zipfile')

            # zipfile to testee
            copy_file(zfs['from-zipfile'], testee.file('from-zipfile'))
            with testee['from-zipfile'].open() as f:
                self.assertEquals('copied-from-zipfile', f.read())

            # testee to zipfile
            copy_file(testee['bar.txt'], zfs.file('from-testee'))
            with zfs['from-testee'].open() as f:
                self.assertEquals('Hello', f.read())

            #
            # copy from/to filesystem
            #
            from oxt_tool.storage.fs import FileSystemStorage
            fss_path = self.id() + '.fsstg'
            import shutil
            import os.path
            if os.path.exists(fss_path):
                shutil.rmtree(fss_path)
            os.mkdir(fss_path)
            fss = FileSystemStorage(fss_path)
            with fss.file('from-fs').open('w') as f:
                f.write('copied-from-fs')

            # fs to testee
            copy_file(fss['from-fs'], testee.file('from-fs'))
            with testee['from-fs'].open() as f:
                self.assertEquals('copied-from-fs', f.read())

            # testee to fs
            copy_file(testee['bar.txt'], fss.file('from-testee'))
            with fss['from-testee'].open() as f:
                self.assertEquals('Hello', f.read())

########NEW FILE########
__FILENAME__ = test_fs
# -*- coding: utf-8 -*-
from __future__ import with_statement
import unittest
from contextlib import contextmanager
from mixin_storage import StorageTestMixin


class TestFileSystem(unittest.TestCase, StorageTestMixin):

    @property
    def fixture_path(self):
        return self.id()

    def create_fixture_storage(self):
        from oxt_tool.storage.fs import FileSystemStorage
        return FileSystemStorage(self.fixture_path, 'a')
    
    @contextmanager
    def create_fixture_folder(self):
        import os.path
        import shutil
        path = self.fixture_path
        if os.path.exists(path):
            shutil.rmtree(path)
        os.mkdir(path)
        os.mkdir(os.path.join(path, 'bar'))
        with file(os.path.join(path, 'bar.txt'), 'w') as f:
            f.write('Hello')
        with file(os.path.join(path, 'baz.txt'), 'w') as f:
            f.write('World')
        from oxt_tool.storage.fs import FileSystemFolder
        yield FileSystemFolder(path)

    @contextmanager
    def get_fixture_folder(self):
        from oxt_tool.storage.fs import FileSystemFolder
        yield FileSystemFolder(self.fixture_path)

########NEW FILE########
__FILENAME__ = test_package
# -*- coding: utf-8 -*-
from __future__ import with_statement
import unittest
from oxt_tool.package import is_package
from oxt_tool.storage import open_storage
from oxt_tool.storage import resolve_path
from oxt_tool.storage.fs import FileSystemStorage
from oxt_tool.manifest import Manifest
from oxt_tool.description import Description


class PackageTest(unittest.TestCase):

    def test_package_name_from_desc(self):
        from oxt_tool.package import package_name_from_desc
        desc = Description(identifier='pyhwp.example', version='')
        self.assertEquals('pyhwp.example.oxt', package_name_from_desc(desc))
        desc.version = '0.1'
        self.assertEquals('pyhwp.example-0.1.oxt', package_name_from_desc(desc))

    def test_make_output_path(self):
        from oxt_tool.package import make_output_path

        self.assertEquals('abc.oxt', make_output_path('abc.oxt'))
        self.assertEquals('./abc.oxt', make_output_path('./abc.oxt'))
        self.assertEquals('abc/def.oxt', make_output_path('abc/def.oxt'))

        desc = Description(identifier='example', version='0.1')
        self.assertEquals('example-0.1.oxt', make_output_path('', desc))
        self.assertEquals('./example-0.1.oxt', make_output_path('.', desc))
        self.assertEquals('abc/example-0.1.oxt', make_output_path('abc/', desc))

        dirpath = self.id()
        import shutil
        import os.path
        if os.path.exists(dirpath):
            shutil.rmtree(dirpath)
        os.mkdir(dirpath)
        self.assertEquals(os.path.join(dirpath, 'example-0.1.oxt'),
                          make_output_path(dirpath, desc))


class BuildPackageTest(unittest.TestCase):

    def test_build_minimal(self):
        from oxt_tool.package import build

        manifest = Manifest()
        description = Description()
        oxt_path = self.id() + '.oxt'
        build(oxt_path, manifest, description)
        with open_storage(oxt_path) as pkg:
            self.assertTrue(is_package(pkg))

    def test_build_missing(self):
        from oxt_tool.package import build

        oxt_path = self.id() + '.oxt'

        manifest = Manifest()
        description = Description(license=dict(en='COPYING'))
        files = dict()
        try:
            build(oxt_path, manifest, description, files=files)
            assert False, 'exception expected'
        except Exception:
            pass

    def test_build_typical(self):
        from oxt_tool.package import build
        from oxt_tool.storage import makedirs_to_file

        manifest = Manifest()
        description = Description()

        import os.path
        import shutil
        src_folder_path = self.id()
        if os.path.exists(src_folder_path):
            shutil.rmtree(src_folder_path)
        src_folder = FileSystemStorage(src_folder_path, 'w')

        license_path = 'COPYING'
        license_node = makedirs_to_file(src_folder, license_path)
        with license_node.open('w') as f:
            f.write('GNU AGPL')
        description.license['en'] = license_path

        oxt_path = self.id() + '.oxt'

        files = {license_path: license_node}
        build(oxt_path, manifest, description, files=files)

        with open_storage(oxt_path) as pkg:
            with resolve_path(pkg, 'COPYING').open() as f:
                self.assertEquals('GNU AGPL', f.read())

########NEW FILE########
__FILENAME__ = test_storage_path
# -*- coding: utf-8 -*-
import unittest
from oxt_tool.storage.path import split as path_split
from oxt_tool.storage.path import get_ancestors as path_ancestors


class TestStoragePath(unittest.TestCase):
    
    def test_path_split(self):
        self.assertEquals([], path_split('/'))
        self.assertEquals([], path_split(''))
        self.assertEquals(['name'], path_split('name'))
        self.assertEquals(['dir', 'base'], path_split('dir/base'))
        self.assertEquals(['dir', 'base'], path_split('/dir/base'))
        self.assertEquals(['grand', 'parent', 'child'],
                          path_split('grand/parent/child'))

    def test_path_ancestors(self):
        self.assertEquals(set(['top', 'top/grand', 'top/grand/parent']),
                          set(path_ancestors('top/grand/parent/child')))

########NEW FILE########
__FILENAME__ = test_zipfile
# -*- coding: utf-8 -*-
from __future__ import with_statement
import unittest
from oxt_tool.storage import _zipfile
from mixin_storage import StorageTestMixin
import contextlib


class TestZipFile(unittest.TestCase, StorageTestMixin):

    @property
    def zipfile_path(self):
        return self.id() + '.zip'

    def zipfile_create(self):
        import zipfile
        return zipfile.ZipFile(self.zipfile_path, 'w')

    def zipfile_get(self):
        import zipfile
        return zipfile.ZipFile(self.zipfile_path, 'r')

    def test_zipfile_folder(self):
        import os
        zf = self.zipfile_create()
        try:
            zf.writestr(os.sep.join(['foo', 'bar.txt']), 'Hello')
            _zipfile.ZipFileFolder(zf, 'foo')
        finally:
            zf.close()

    def test_zipfile_file(self):
        import os
        zf = self.zipfile_create()
        try:
            path = os.sep.join(['foo', 'bar.txt'])
            zf.writestr(path, 'Hello')
            _zipfile.ZipFileFile(zf, path)
        finally:
            zf.close()

    def test_zipfile_file_put(self):
        path = self.id() + '.txt'
        with file(path, 'w') as f:
            f.write('new-file-content')
        with self.create_fixture_folder() as folder:
            folder.file('new-file').put(path)
        with self.get_fixture_folder() as folder:
            with folder['new-file'].open() as f:
                self.assertEquals('new-file-content', f.read())

    def create_fixture_storage(self):
        return _zipfile.ZipFileStorage(self.zipfile_path, 'w')

    @contextlib.contextmanager
    def create_fixture_zipfile(self):
        import os
        zf = self.zipfile_create()
        try:
            zf.writestr(os.sep.join(['foo', 'bar.txt']), 'Hello')
            zf.writestr(os.sep.join(['foo', 'baz.txt']), 'World')
            zf.writestr(os.sep.join(['foo', 'bar', 'baz']), 'Hello World')
            yield zf
        finally:
            zf.close()

    @contextlib.contextmanager
    def create_fixture_folder(self):
        with self.create_fixture_zipfile() as zf:
            yield _zipfile.ZipFileFolder(zf, 'foo')

    @contextlib.contextmanager
    def get_fixture_folder(self):
        zf = self.zipfile_get()
        try:
            yield _zipfile.ZipFileFolder(zf, 'foo')
        finally:
            zf.close()

    def test_zipfile_nodes(self):
        import os.path
        from oxt_tool.storage._zipfile import zipfile_nodes
        with self.create_fixture_zipfile() as zipfile:
            nodes = dict(zipfile_nodes(zipfile))
            self.assertEquals(set(['foo',
                                   os.path.join('foo', 'bar'),
                                   os.path.join('foo', 'bar.txt'),
                                   os.path.join('foo', 'baz.txt'),
                                   os.path.join('foo', 'bar', 'baz')]),
                              set(nodes.keys()))
            self.assertTrue(hasattr(nodes['foo'], '__getitem__'))
            self.assertTrue(hasattr(nodes[os.path.join('foo', 'bar')],
                                    '__getitem__'))
            self.assertTrue(hasattr(nodes[os.path.join('foo', 'bar.txt')],
                                    'open'))
            self.assertTrue(hasattr(nodes[os.path.join('foo', 'baz.txt')],
                                    'open'))
            self.assertTrue(hasattr(nodes[os.path.join('foo', 'bar', 'baz')],
                                    'open'))

########NEW FILE########
__FILENAME__ = pyhwp_zestreleaser_cmds
# -*- coding: utf-8 -*-
#   pyhwp.zestreleaser.cmds: A zest.releaser plugin to provide command hooks
#   Copyright (C) 2013  mete0r@sarangbang.or.kr
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os.path
import subprocess
import logging


logger = logging.getLogger(__name__)


RELEASE_HOOKS_DIR = 'release-hooks'


def call_hooks(hooks_root, hook_type):
    hooks_dir = os.path.join(hooks_root, hook_type)
    if os.path.isdir(hooks_dir):
        hooks = sorted(os.listdir(hooks_dir))
        for hook in hooks:
            hook_path = os.path.join(hooks_dir, hook)
            if os.path.isfile(hook_path) and os.access(hook_path, os.X_OK):
                logger.info('%s: %s', hook_type, hook_path)
                subprocess.check_call([hook_path])


def prerelease_before(data):
    logger.debug('data: %r', data)
    call_hooks(RELEASE_HOOKS_DIR, 'prerelease.before')


def prerelease_middle(data):
    logger.debug('data: %r', data)
    call_hooks(RELEASE_HOOKS_DIR, 'prerelease.middle')


def prerelease_after(data):
    logger.debug('data: %r', data)
    call_hooks(RELEASE_HOOKS_DIR, 'prerelease.after')


def release_before(data):
    logger.debug('data: %r', data)
    call_hooks(RELEASE_HOOKS_DIR, 'release.before')


def release_middle(data):
    logger.debug('data: %r', data)
    call_hooks(RELEASE_HOOKS_DIR, 'release.middle')


def release_after(data):
    logger.debug('data: %r', data)
    call_hooks(RELEASE_HOOKS_DIR, 'release.after')


def postrelease_before(data):
    logger.debug('data: %r', data)
    call_hooks(RELEASE_HOOKS_DIR, 'postrelease.before')


def postrelease_middle(data):
    logger.debug('data: %r', data)
    call_hooks(RELEASE_HOOKS_DIR, 'postrelease.middle')


def postrelease_after(data):
    logger.debug('data: %r', data)
    call_hooks(RELEASE_HOOKS_DIR, 'postrelease.after')

########NEW FILE########
__FILENAME__ = pyhwp_unpack
# -*- coding: utf-8 -*-
import sys
import os.path
import logging
import tempfile
import shutil

import setuptools.archive_util


logger = logging.getLogger(__name__)


def main():
    logging.basicConfig()
    logger.setLevel(logging.DEBUG)

    src = sys.argv[1]
    dst = sys.argv[2]

    strip_toplevel_dir = True

    if not os.path.exists(dst):
        os.makedirs(dst)

    if not os.path.isdir(dst):
        logger.error('%s: not a directory', dst)

    if strip_toplevel_dir:
        tempdir = tempfile.mkdtemp()
        try:
            setuptools.archive_util.unpack_archive(src, tempdir)
            toplevel_items = os.listdir(tempdir)
            if len(toplevel_items) > 1:
                logger.error('%s has no single top-level directory', src)
                raise SystemExit(1)
            root = os.path.join(tempdir, toplevel_items[0])
            for item in os.listdir(root):
                src_item = os.path.join(root, item)
                dst_item = os.path.join(dst, item)
                if os.path.exists(dst_item):
                    if os.path.isdir(dst_item):
                        shutil.rmtree(dst_item)
                    else:
                        os.unlink(dst_item)
                shutil.move(src_item, dst)
        finally:
            shutil.rmtree(tempdir)
    else:
        setuptools.archive_util.unpack_archive(src, dst)

########NEW FILE########
__FILENAME__ = subtree
# -*- coding: utf-8 -*-
import sys
import logging

from docopt import docopt
from lxml import etree

from xsltest.xmltool import __version__
from xsltest import context_subtree

logger = logging.getLogger(__name__)


doc = ''' xmltool subtree

Usage:
    xmltool-subtree <xpath>
    xmltool-subtree --help

Options:

    -h --help               Show this screen

'''


def main():
    logger.debug('argv: %r', sys.argv)
    args = docopt(doc, version=__version__)
    logger.debug('args: %r', args)

    params = dict(xpath=args['<xpath>'])
    # TODO: workaround
    params['sourceline'] = 0

    execute = context_subtree(params)

    xmldoc = etree.parse(sys.stdin)
    result = execute(xmldoc.getroot())
    result = etree.tostring(result, xml_declaration=True, encoding='utf-8')
    sys.stdout.write(result)
    sys.stdout.flush()

########NEW FILE########
__FILENAME__ = wrap
# -*- coding: utf-8 -*-
import sys
import logging

from docopt import docopt
from lxml import etree

from xsltest.xmltool import __version__
from xsltest import context_wrap_subnodes

logger = logging.getLogger(__name__)


doc = ''' xmltool wrap

Usage:
    xmltool-wrap <xpath>
    xmltool-wrap --help

Options:

    -h --help               Show this screen

'''


def main():
    logger.debug('argv: %r', sys.argv)
    args = docopt(doc, version=__version__)
    logger.debug('args: %r', args)

    params = dict(xpath=args['<xpath>'])
    # TODO: workaround
    params['sourceline'] = 0

    execute = context_wrap_subnodes(params)

    xmldoc = etree.parse(sys.stdin)
    result = execute(xmldoc.getroot())
    result = etree.tostring(result, xml_declaration=True, encoding='utf-8')
    sys.stdout.write(result)
    sys.stdout.flush()

########NEW FILE########
__FILENAME__ = xslt

# -*- coding: utf-8 -*-
import os
import sys
import logging

from docopt import docopt
from lxml import etree

from xsltest.xmltool import __version__
from xsltest import context_xslt

logger = logging.getLogger(__name__)


doc = ''' xmltool xslt

Usage:
    xmltool-xslt [--wrap=WRAP --mode=MODE --select=SELECT] <stylesheet>
    xmltool-xslt --help

Options:

    -h --help               Show this screen

'''


def main():
    logger.debug('argv: %r', sys.argv)
    args = docopt(doc, version=__version__)
    logger.debug('args: %r', args)

    stylesheet_path = os.path.abspath(args['<stylesheet>'])
    params = dict(stylesheet_path=stylesheet_path,
                  wrap=args['--wrap'], mode=args['--mode'],
                  select=args['--select'])
    # TODO: workaround
    params['sourceline'] = 0

    execute = context_xslt(params)

    xmldoc = etree.parse(sys.stdin)
    result = execute(xmldoc.getroot())
    result = etree.tostring(result, xml_declaration=True, encoding='utf-8')
    sys.stdout.write(result)
    sys.stdout.flush()

########NEW FILE########
__FILENAME__ = adapters
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010,2011,2012 mete0r@sarangbang.or.kr
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import uno
import unohelper
from com.sun.star.io import XInputStream, XSeekable, XOutputStream


class InputStreamFromFileLike(unohelper.Base, XInputStream, XSeekable):
    ''' Implementation of XInputStream, XSeekable based on a file-like object

    Implements com.sun.star.io.XInputStream and com.sun.star.io.XSeekable

    :param f: a file-like object
    '''
    def __init__(self, f, dontclose=False):
        self.f = f
        self.dontclose = dontclose

    def readBytes(self, aData, nBytesToRead):
        data = self.f.read(nBytesToRead)
        return len(data), uno.ByteSequence(data)

    readSomeBytes = readBytes

    def skipBytes(self, nBytesToSkip):
        self.f.read(nBytesToSkip)

    def available(self):
        return 0

    def closeInput(self):
        if not self.dontclose:
            self.f.close()

    def seek(self, location):
        self.f.seek(location)

    def getPosition(self):
        pos = self.f.tell()
        return pos

    def getLength(self):
        pos = self.f.tell()
        try:
            self.f.seek(0, 2)
            length = self.f.tell()
            return length
        finally:
            self.f.seek(pos)


class OutputStreamToFileLike(unohelper.Base, XOutputStream):
    ''' Implementation of XOutputStream based on a file-like object.

    Implements com.sun.star.io.XOutputStream.

    :param f: a file-like object
    '''
    def __init__(self, f, dontclose=False):
        self.f = f
        self.dontclose = dontclose

    def writeBytes(self, bytesequence):
        self.f.write(bytesequence.value)

    def flush(self):
        self.f.flush()

    def closeOutput(self):
        if not self.dontclose:
            self.f.close()


class FileFromStream(object):
    ''' A file-like object based on XInputStream/XOuputStream/XSeekable

    :param stream: a stream object which implements
    com.sun.star.io.XInputStream, com.sun.star.io.XOutputStream or
    com.sun.star.io.XSeekable
    '''
    def __init__(self, stream):
        self.stream = stream

        if hasattr(stream, 'readBytes'):
            def read(size=None):
                if size is None:
                    data = ''
                    while True:
                        bytes = uno.ByteSequence('')
                        n_read, bytes = stream.readBytes(bytes, 4096)
                        if n_read == 0:
                            return data
                        data += bytes.value
                bytes = uno.ByteSequence('')
                n_read, bytes = stream.readBytes(bytes, size)
                return bytes.value
            self.read = read

        if hasattr(stream, 'seek'):
            self.tell = stream.getPosition

            def seek(offset, whence=0):
                if whence == 0:
                    pass
                elif whence == 1:
                    offset += stream.getPosition()
                elif whence == 2:
                    offset += stream.getLength()
                stream.seek(offset)
            self.seek = seek

        if hasattr(stream, 'writeBytes'):
            def write(s):
                stream.writeBytes(uno.ByteSequence(s))
            self.write = write

            def flush():
                stream.flush()
            self.flush = flush

    def close(self):
        if hasattr(self.stream, 'closeInput'):
            self.stream.closeInput()
        elif hasattr(self.stream, 'closeOutput'):
            self.stream.closeOutput()

########NEW FILE########
__FILENAME__ = configuration
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010,2011,2012 mete0r@sarangbang.or.kr
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

def open_config(nodepath):
    from unokit.services import css
    from unokit.util import dict_to_propseq
    provider = css.configuration.ConfigurationProvider()
    param = dict_to_propseq(dict(nodepath=nodepath))
    configaccess = 'com.sun.star.configuration.ConfigurationAccess'
    return provider.createInstanceWithArguments(configaccess, param)


def get_soffice_product_info():
    config = open_config('/org.openoffice.Setup')

    # see schema in libreoffice/officecfg/registry/schema/org/office/Setup.xcs

    version = tuple(int(x) for x in config.Product.ooSetupVersionAboutBox.split('.'))
    if hasattr(config.Product, 'ooSetupVersionAboutBoxSuffix'):
        # seems for libreoffice >= 3.5 only
        version += (config.Product.ooSetupVersionAboutBoxSuffix,)
    return dict(vendor=config.Product.ooVendor,
                name=config.Product.ooName,
                version=version,
                locale=config.L10N.ooLocale)

########NEW FILE########
__FILENAME__ = contexts
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010,2011,2012 mete0r@sarangbang.or.kr
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import uno
import threading


tls = threading.local()
localcontext = uno.getComponentContext()


def get_stack():
    try:
        return tls.context_stack
    except AttributeError:
        tls.context_stack = []
        return tls.context_stack


def push(context):
    return get_stack().append(context)


def pop():
    return get_stack().pop()


def get_current():
    stack = get_stack()
    if len(stack) == 0:
        return localcontext
    return stack[-1]

########NEW FILE########
__FILENAME__ = services
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010,2011,2012 mete0r@sarangbang.or.kr
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

def create_service(name, *args):
    import unokit.contexts
    context = unokit.contexts.get_current()
    sm = context.ServiceManager
    if len(args) > 0:
        return sm.createInstanceWithArgumentsAndContext(name, args, context)
    else:
        return sm.createInstanceWithContext(name, context)


class NamespaceNode(object):
    def __init__(self, dotted_name):
        self.dotted_name = dotted_name

    def __getattr__(self, name):
        return NamespaceNode(self.dotted_name + '.' + name)

    def __call__(self, *args):
        return create_service(self.dotted_name, *args)

    def __iter__(self):
        import unokit.contexts
        context = unokit.contexts.get_current()
        sm = context.ServiceManager
        prefix = self.dotted_name + '.'
        for name in sm.AvailableServiceNames:
            if name.startswith(prefix):
                basename = name[len(prefix):]
                if basename.find('.') == -1:
                    yield basename


css = NamespaceNode('com.sun.star')

########NEW FILE########
__FILENAME__ = singletons
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010,2011,2012 mete0r@sarangbang.or.kr
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

def get_singleton(name):
    import unokit.contexts
    context = unokit.contexts.get_current()
    return context.getValueByName('/singletons/'+name)


def iter_singleton_names():
    import unokit.contexts
    context = unokit.contexts.get_current()
    names = (name[len('/singletons/'):]
             for name in context.ElementNames
             if (name.startswith('/singletons/')
                 and not name.endswith('/service')))
    return names


class NamespaceNode(object):
    def __init__(self, dotted_name):
        self.dotted_name = dotted_name

    def __getattr__(self, name):
        import unokit.contexts
        context = unokit.contexts.get_current()
        dotted_name = self.dotted_name + '.' + name
        full_name = '/singletons/' + dotted_name
        if full_name in context.ElementNames:
            return context.getValueByName(full_name)
        return NamespaceNode(self.dotted_name + '.' + name)

    def __iter__(self):
        prefix = self.dotted_name + '.'
        for name in iter_singleton_names():
            if name.startswith(prefix):
                basename = name[len(prefix):]
                if basename.find('.') == -1:
                    yield basename


css = NamespaceNode('com.sun.star')

########NEW FILE########
__FILENAME__ = test_configuration
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010,2011,2012 mete0r@sarangbang.or.kr
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from unittest import TestCase


class TestBase(TestCase):
    pass


class GetSofficeProductInfoTest(TestBase):
    def test_basic(self):
        from unokit.configuration import get_soffice_product_info
        info = get_soffice_product_info()
        self.assertTrue('name' in info)
        self.assertTrue('vendor' in info)
        self.assertTrue('version' in info)
        self.assertTrue('locale' in info)

########NEW FILE########
__FILENAME__ = test_singletons
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010,2011,2012 mete0r@sarangbang.or.kr
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from unittest import TestCase


class TestBase(TestCase):
    pass


class TestSingletons(TestBase):
    def test_extman(self):
        from unokit.singletons import css
        extman = css.deployment.ExtensionManager
        self.assertTrue(extman is not None)

    def test_pkginfo_prov(self):
        from unokit.singletons import css
        pkginfo_prov = css.deployment.PackageInformationProvider
        self.assertTrue(pkginfo_prov is not None)

        for ext_id, ext_ver in pkginfo_prov.ExtensionList:
            ext_loc = pkginfo_prov.getPackageLocation(ext_id)
            print ext_id, ext_ver, ext_loc
            self.assertTrue(ext_loc != '')

########NEW FILE########
__FILENAME__ = test_ucb
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010,2011,2012 mete0r@sarangbang.or.kr
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from unittest import TestCase


class TestBase(TestCase):
    pass


class OpenURLTest(TestBase):
    def test_basic(self):
        #import os.path
        #from uno import systemPathToFileUrl
        from unokit.ucb import open_url

        #path = os.path.abspath('fixtures/sample-5017.hwp')
        #url = systemPathToFileUrl(path)
        inputstream = open_url('http://google.com')
        inputstream.closeInput()

########NEW FILE########
__FILENAME__ = ucb
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010,2011,2012 mete0r@sarangbang.or.kr
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


def open_url(url):
    ''' open InputStream from a URL.

    :param url: a URL to open an InputStream.
    :returns: an instance of InputStream
    '''

    # see http://wiki.openoffice.org/wiki/Documentation/DevGuide/UCB/Using_the_UCB_API

    from unokit.services import css
    ucb = css.ucb.UniversalContentBroker('Local', 'Office')
    content_id = ucb.createContentIdentifier(url)
    content = ucb.queryContent(content_id)

    import unohelper
    from com.sun.star.io import XActiveDataSink
    class DataSink(unohelper.Base, XActiveDataSink):
        def setInputStream(self, stream):
            self.stream = stream
        def getInputStream(self):
            return self.stream
    datasink = DataSink()

    from com.sun.star.ucb import Command, OpenCommandArgument2
    openargs = OpenCommandArgument2()
    openargs.Mode = 2 # OpenMode.DOCUMENT
    openargs.Priority = 32768
    openargs.Sink = datasink

    command = Command()
    command.Name = 'open'
    command.Handle = -1
    command.Argument = openargs

    content.execute(command, 0, None)
    return datasink.stream

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
#
#   pyhwp : hwp file format parser in python
#   Copyright (C) 2010,2011,2012 mete0r@sarangbang.or.kr
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import uno


def unofy_value(value):
    if isinstance(value, dict):
        value = dict_to_propseq(value)
    elif isinstance(value, list):
        value = tuple(value)
    return value


def xenumeration_list(xenum):
    return list(iterate(xenum))


def dict_to_propseq(d):
    from com.sun.star.beans import PropertyValue
    DIRECT_VALUE = uno.Enum('com.sun.star.beans.PropertyState', 'DIRECT_VALUE')
    return tuple(PropertyValue(k, 0, unofy_value(v), DIRECT_VALUE)
                 for k, v in d.iteritems())


def propseq_to_dict(propvalues):
    return dict((p.Name, p.Value) for p in propvalues)


def enumerate(xenumaccess):
    ''' Enumerate an instance of com.sun.star.container.XEnumerationAccess '''
    if hasattr(xenumaccess, 'createEnumeration'):
        xenum = xenumaccess.createEnumeration()
        return iterate(xenum)
    else:
        return iter([])


def iterate(xenum):
    ''' Iterate an instance of com.sun.star.container.XEnumeration '''
    if hasattr(xenum, 'hasMoreElements'):
        while xenum.hasMoreElements():
            yield xenum.nextElement()


def dump(obj):
    from binascii import b2a_hex
    if hasattr(obj, 'ImplementationId'):
        print 'Implementation Id:', b2a_hex(obj.ImplementationId.value)
        print

    if hasattr(obj, 'ImplementationName'):
        print 'Implementation Name:', obj.ImplementationName
        print

    if hasattr(obj, 'SupportedServiceNames'):
        print 'Supported Services:'
        for x in obj.SupportedServiceNames:
            print '', x
        print

    if hasattr(obj, 'Types'):
        print 'Types:'
        for x in obj.Types:
            print '', x.typeClass.value, x.typeName
        print


def dumpdir(obj):
    print 'dir:'
    for e in sorted(dir(obj)):
        print '', e
    print

########NEW FILE########
