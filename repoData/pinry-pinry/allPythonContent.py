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

import os, shutil, sys, tempfile
from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --setup-source and --download-base to point to
local resources, you can keep this script from going over the network.
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
# load/install distribute

to_reload = False
try:
    import pkg_resources, setuptools
    if not hasattr(pkg_resources, '_distribute'):
        to_reload = True
        raise ImportError
except ImportError:
    ez = {}

    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib2 import urlopen

    exec(urlopen('http://python-distribute.org/distribute_setup.py').read(), ez)
    setup_args = dict(to_dir=tmpeggs, download_delay=0, no_fake=True)
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

ws  = pkg_resources.working_set

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

distribute_path = ws.find(
    pkg_resources.Requirement.parse('distribute')).location

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
        search_path=[distribute_path])
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
if subprocess.call(cmd, env=dict(os.environ, PYTHONPATH=distribute_path)) != 0:
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
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Pinry documentation build configuration file, created by
# sphinx-quickstart on Wed Sep 25 02:21:23 2013.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Pinry'
copyright = u'2013, Isaac Bythewood'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.3.2'
# The full version, including alpha/beta/rc tags.
release = '1.3.2'

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
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all
# documents.
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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

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
html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

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
htmlhelp_basename = 'Pinrydoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Pinry.tex', u'Pinry Documentation',
   u'Isaac Bythewood', 'manual'),
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


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'pinry', u'Pinry Documentation',
     [u'Isaac Bythewood'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Pinry', u'Pinry Documentation',
   u'Isaac Bythewood', 'Pinry', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pinry.settings.development")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = api
from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from tastypie.exceptions import Unauthorized
from tastypie.resources import ModelResource
from django_images.models import Thumbnail

from .models import Pin, Image
from ..users.models import User


class PinryAuthorization(DjangoAuthorization):
    """
    Pinry-specific Authorization backend with object-level permission checking.
    """
    def update_detail(self, object_list, bundle):
        klass = self.base_checks(bundle.request, bundle.obj.__class__)

        if klass is False:
            raise Unauthorized("You are not allowed to access that resource.")

        permission = '%s.change_%s' % (klass._meta.app_label, klass._meta.module_name)

        if not bundle.request.user.has_perm(permission, bundle.obj):
            raise Unauthorized("You are not allowed to access that resource.")

        return True

    def delete_detail(self, object_list, bundle):
        klass = self.base_checks(bundle.request, bundle.obj.__class__)

        if klass is False:
            raise Unauthorized("You are not allowed to access that resource.")

        permission = '%s.delete_%s' % (klass._meta.app_label, klass._meta.module_name)

        if not bundle.request.user.has_perm(permission, bundle.obj):
            raise Unauthorized("You are not allowed to access that resource.")

        return True


class UserResource(ModelResource):
    gravatar = fields.CharField(readonly=True)

    def dehydrate_gravatar(self, bundle):
        return bundle.obj.gravatar

    class Meta:
        list_allowed_methods = ['get']
        filtering = {
            'username': ALL
        }
        queryset = User.objects.all()
        resource_name = 'user'
        fields = ['username']
        include_resource_uri = False


def filter_generator_for(size):
    def wrapped_func(bundle, **kwargs):
        return bundle.obj.get_by_size(size)
    return wrapped_func


class ThumbnailResource(ModelResource):
    class Meta:
        list_allowed_methods = ['get']
        fields = ['image', 'width', 'height']
        queryset = Thumbnail.objects.all()
        resource_name = 'thumbnail'
        include_resource_uri = False


class ImageResource(ModelResource):
    standard = fields.ToOneField(ThumbnailResource, full=True,
                                 attribute=lambda bundle: filter_generator_for('standard')(bundle))
    thumbnail = fields.ToOneField(ThumbnailResource, full=True,
                                  attribute=lambda bundle: filter_generator_for('thumbnail')(bundle))
    square = fields.ToOneField(ThumbnailResource, full=True,
                               attribute=lambda bundle: filter_generator_for('square')(bundle))

    class Meta:
        fields = ['image', 'width', 'height']
        include_resource_uri = False
        resource_name = 'image'
        queryset = Image.objects.all()
        authorization = DjangoAuthorization()


class PinResource(ModelResource):
    submitter = fields.ToOneField(UserResource, 'submitter', full=True)
    image = fields.ToOneField(ImageResource, 'image', full=True)
    tags = fields.ListField()

    def hydrate_image(self, bundle):
        url = bundle.data.get('url', None)
        if url:
            image = Image.objects.create_for_url(url)
            bundle.data['image'] = '/api/v1/image/{}/'.format(image.pk)
        return bundle

    def hydrate(self, bundle):
        """Run some early/generic processing

        Make sure that user is authorized to create Pins first, before
        we hydrate the Image resource, creating the Image object in process
        """
        submitter = bundle.data.get('submitter', None)
        if not submitter:
            bundle.data['submitter'] = '/api/v1/user/{}/'.format(bundle.request.user.pk)
        else:
            if not '/api/v1/user/{}/'.format(bundle.request.user.pk) == submitter:
                raise Unauthorized("You are not authorized to create Pins for other users")
        return bundle

    def dehydrate_tags(self, bundle):
        return map(str, bundle.obj.tags.all())

    def build_filters(self, filters=None):
        orm_filters = super(PinResource, self).build_filters(filters)
        if filters and 'tag' in filters:
            orm_filters['tags__name__in'] = filters['tag'].split(',')
        return orm_filters

    def save_m2m(self, bundle):
        tags = bundle.data.get('tags', None)
        if tags:
            bundle.obj.tags.set(*tags)
        return super(PinResource, self).save_m2m(bundle)

    class Meta:
        fields = ['id', 'url', 'origin', 'description']
        ordering = ['id']
        filtering = {
            'submitter': ALL_WITH_RELATIONS
        }
        queryset = Pin.objects.all()
        resource_name = 'pin'
        include_resource_uri = False
        always_return_data = True
        authorization = PinryAuthorization()

########NEW FILE########
__FILENAME__ = context_processors
from django.conf import settings


def template_settings(request):
    return {
        'API_LIMIT_PER_PAGE': settings.API_LIMIT_PER_PAGE,
    }


########NEW FILE########
__FILENAME__ = feeds
from __future__ import unicode_literals

from django.contrib.syndication.views import Feed
from django.contrib.sites.models import get_current_site
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from django_images.models import Thumbnail
from taggit.models import Tag

from .models import Pin


def filter_generator_for(size):
    def wrapped_func(obj):
        return Thumbnail.objects.get_or_create_at_size(obj.pk, size)
    return wrapped_func


class LatestPins(Feed):
    title = 'Latest Pins'
    link = '/'
    description = 'The latest pins from around the internet.'

    domain_name = None

    item_enclosure_mime_type = 'image/jpeg'

    def get_object(self, request):
        """
        Doing this as a fix for Django's not including the domain name in
        enclosure urls.
        """
        try:
            request_type = 'http'
            if request.is_secure(): request_type = 'https'
            self.domain_name = ''.join([request_type, '://',
                                        get_current_site(request).domain])
        except:
            pass

    def items(self):
        return Pin.objects.order_by('-published')[:15]

    def item_pubdate(self, item):
        return item.published

    def item_link(self, item):
        return item.url

    def item_title(self, item):
        return item.url

    def item_description(self, item):
        tags = ', '.join(tag.name for tag in item.tags.all())
        return ''.join(['Description: ', item.description or 'None',
                        ' | Tags: ', tags or 'None'])

    def item_enclosure_url(self, item):
        slug = unicode(filter_generator_for('standard')(item.image).image.url)
        return self.domain_name + slug

    def item_enclosure_length(self, item):
        return filter_generator_for('standard')(item.image).image.size


class LatestUserPins(Feed):
    description = 'The latest pins from around the internet.'

    domain_name = None

    item_enclosure_mime_type = 'image/jpeg'

    def get_object(self, request, user):
        """
        Doing this as a fix for Django's not including the domain name in
        enclosure urls.
        """
        request_type = 'http'
        if request.is_secure(): request_type = 'https'
        self.domain_name = ''.join([request_type, '://',
                                    get_current_site(request).domain])
        return get_object_or_404(User, username=user)

    def title(self, obj):
        return 'Latest Pins from ' + obj.username

    def link(self, obj):
        return '/pins/user/' + obj.username + '/'

    def items(self, obj):
        return Pin.objects.filter(submitter=obj).order_by('-published')[:15]

    def item_pubdate(self, item):
        return item.published

    def item_link(self, item):
        return item.url

    def item_title(self, item):
        return item.url

    def item_description(self, item):
        tags = ', '.join(tag.name for tag in item.tags.all())
        return ''.join(['Description: ', item.description or 'None',
                        ' | Tags: ', tags or 'None'])

    def item_enclosure_url(self, item):
        slug = unicode(filter_generator_for('standard')(item.image).image.url)
        return self.domain_name + slug

    def item_enclosure_length(self, item):
        return filter_generator_for('standard')(item.image).image.size


class LatestTagPins(Feed):
    link = '/'
    description = 'The latest pins from around the internet.'

    domain_name = None

    item_enclosure_mime_type = 'image/jpeg'

    def get_object(self, request, tag):
        """
        Doing this as a fix for Django's not including the domain name in
        enclosure urls.
        """
        request_type = 'http'
        if request.is_secure(): request_type = 'https'
        self.domain_name = ''.join([request_type, '://',
                                    get_current_site(request).domain])
        return get_object_or_404(Tag, name=tag)

    def title(self, obj):
        return 'Latest Pins in ' + obj.name

    def link(self, obj):
        return '/pins/tag/' + obj.name + '/'

    def items(self, obj):
        return Pin.objects.filter(tags=obj).order_by('-published')[:15]

    def item_pubdate(self, item):
        return item.published

    def item_link(self, item):
        return item.url

    def item_title(self, item):
        return item.url

    def item_description(self, item):
        tags = ', '.join(tag.name for tag in item.tags.all())
        return ''.join(['Description: ', item.description or 'None',
                        ' | Tags: ', tags or 'None'])

    def item_enclosure_url(self, item):
        slug = unicode(filter_generator_for('standard')(item.image).image.url)
        return self.domain_name + slug

    def item_enclosure_length(self, item):
        return filter_generator_for('standard')(item.image).image.size


########NEW FILE########
__FILENAME__ = forms
from django import forms

from django_images.models import Image


FIELD_NAME_MAPPING = {
    'image': 'qqfile',
}


class ImageForm(forms.ModelForm):
    def add_prefix(self, field_name):
        field_name = FIELD_NAME_MAPPING.get(field_name, field_name)
        return super(ImageForm, self).add_prefix(field_name)

    class Meta:
        model = Image
        fields = ('image',)
########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Pin'
        db.create_table(u'core_pin', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submitter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True)),
            ('origin', self.gf('django.db.models.fields.URLField')(max_length=200, null=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('image', self.gf('django.db.models.fields.related.ForeignKey')(related_name='pin', to=orm['django_images.Image'])),
            ('published', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['Pin'])


    def backwards(self, orm):
        # Deleting model 'Pin'
        db.delete_table(u'core_pin')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.pin': {
            'Meta': {'object_name': 'Pin'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'pin'", 'to': u"orm['django_images.Image']"}),
            'origin': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True'}),
            'published': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'submitter': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True'})
        },
        u'django_images.image': {
            'Meta': {'object_name': 'Image'},
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '255'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        u'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        u'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'taggit_taggeditem_tagged_items'", 'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'taggit_taggeditem_items'", 'to': u"orm['taggit.Tag']"})
        }
    }

    complete_apps = ['core']
########NEW FILE########
__FILENAME__ = models
import requests
from cStringIO import StringIO

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import models, transaction

from django_images.models import Image as BaseImage, Thumbnail
from taggit.managers import TaggableManager

from ..users.models import User


class ImageManager(models.Manager):
    # FIXME: Move this into an asynchronous task
    def create_for_url(self, url):
        file_name = url.split("/")[-1]
        buf = StringIO()
        response = requests.get(url)
        buf.write(response.content)
        obj = InMemoryUploadedFile(buf, 'image', file_name,
                                   None, buf.tell(), None)
        # create the image and its thumbnails in one transaction, removing
        # a chance of getting Database into a inconsistent state when we
        # try to create thumbnails one by one later
        image = self.create(image=obj)
        for size in settings.IMAGE_SIZES.keys():
            Thumbnail.objects.get_or_create_at_size(image.pk, size)
        return image


class Image(BaseImage):
    objects = ImageManager()

    class Meta:
        proxy = True


class Pin(models.Model):
    submitter = models.ForeignKey(User)
    url = models.URLField(null=True)
    origin = models.URLField(null=True)
    description = models.TextField(blank=True, null=True)
    image = models.ForeignKey(Image, related_name='pin')
    published = models.DateTimeField(auto_now_add=True)
    tags = TaggableManager()

    def __unicode__(self):
        return self.url

########NEW FILE########
__FILENAME__ = bootstrap_field
from django.template import loader, Context, Library


register = Library()


@register.simple_tag
def bootstrap_field(field):
    template = loader.get_template('core/templatetags/bootstrap_field.html')
    return template.render(Context({'field': field}))

########NEW FILE########
__FILENAME__ = api
import mock

from django_images.models import Thumbnail
from taggit.models import Tag
from tastypie.exceptions import Unauthorized
from tastypie.test import ResourceTestCase

from .helpers import ImageFactory, PinFactory, UserFactory
from ..models import Pin, Image
from ...users.models import User


__all__ = ['ImageResourceTest', 'PinResourceTest']


def filter_generator_for(size):
    def wrapped_func(obj):
        return Thumbnail.objects.get_or_create_at_size(obj.pk, size)
    return wrapped_func


def mock_requests_get(url):
    response = mock.Mock(content=open('logo.png', 'rb').read())
    return response


class ImageResourceTest(ResourceTestCase):
    def test_post_create_unsupported(self):
        """Make sure that new images can't be created using API"""
        response = self.api_client.post('/api/v1/image/', format='json', data={})
        self.assertHttpUnauthorized(response)

    def test_list_detail(self):
        image = ImageFactory()
        thumbnail = filter_generator_for('thumbnail')(image)
        standard = filter_generator_for('standard')(image)
        square = filter_generator_for('square')(image)
        response = self.api_client.get('/api/v1/image/', format='json')
        self.assertDictEqual(self.deserialize(response)['objects'][0], {
            u'image': unicode(image.image.url),
            u'height': image.height,
            u'width': image.width,
            u'standard': {
                u'image': unicode(standard.image.url),
                u'width': standard.width,
                u'height': standard.height,
            },
            u'thumbnail': {
                u'image': unicode(thumbnail.image.url),
                u'width': thumbnail.width,
                u'height': thumbnail.height,
            },
            u'square': {
                u'image': unicode(square.image.url),
                u'width': square.width,
                u'height': square.height,
            },
        })


class PinResourceTest(ResourceTestCase):
    def setUp(self):
        super(PinResourceTest, self).setUp()
        self.user = UserFactory(password='password')
        self.api_client.client.login(username=self.user.username, password='password')

    @mock.patch('requests.get', mock_requests_get)
    def test_post_create_url(self):
        url = 'http://testserver/mocked/logo.png'
        post_data = {
            'submitter': '/api/v1/user/{}/'.format(self.user.pk),
            'url': url,
            'description': 'That\'s an Apple!'
        }
        response = self.api_client.post('/api/v1/pin/', data=post_data)
        self.assertHttpCreated(response)
        self.assertEqual(Pin.objects.count(), 1)
        self.assertEqual(Image.objects.count(), 1)

        # submitter is optional, current user will be used by default
        post_data = {
            'url': url,
            'description': 'That\'s an Apple!',
            'origin': None
        }
        response = self.api_client.post('/api/v1/pin/', data=post_data)
        self.assertHttpCreated(response)

    @mock.patch('requests.get', mock_requests_get)
    def test_post_create_url_with_empty_tags(self):
        url = 'http://testserver/mocked/logo.png'
        post_data = {
            'submitter': '/api/v1/user/{}/'.format(self.user.pk),
            'url': url,
            'description': 'That\'s an Apple!',
            'tags': []
        }
        response = self.api_client.post('/api/v1/pin/', data=post_data)
        self.assertHttpCreated(response)
        self.assertEqual(Pin.objects.count(), 1)
        self.assertEqual(Image.objects.count(), 1)
        pin = Pin.objects.get(url=url)
        self.assertEqual(pin.tags.count(), 0)

    @mock.patch('requests.get', mock_requests_get)
    def test_post_create_url_unauthorized(self):
        url = 'http://testserver/mocked/logo.png'
        post_data = {
            'submitter': '/api/v1/user/2/',
            'url': url,
            'description': 'That\'s an Apple!',
            'tags': []
        }
        with self.assertRaises(Unauthorized):
            response = self.api_client.post('/api/v1/pin/', data=post_data)
        self.assertEqual(Pin.objects.count(), 0)
        self.assertEqual(Image.objects.count(), 0)

    @mock.patch('requests.get', mock_requests_get)
    def test_post_create_url_with_empty_origin(self):
        url = 'http://testserver/mocked/logo.png'
        post_data = {
            'submitter': '/api/v1/user/{}/'.format(self.user.pk),
            'url': url,
            'description': 'That\'s an Apple!',
            'origin': None
        }
        response = self.api_client.post('/api/v1/pin/', data=post_data)
        self.assertHttpCreated(response)
        self.assertEqual(Pin.objects.count(), 1)
        self.assertEqual(Image.objects.count(), 1)
        self.assertEqual(Pin.objects.get(url=url).origin, None)

    @mock.patch('requests.get', mock_requests_get)
    def test_post_create_url_with_origin(self):
        origin = 'http://testserver/mocked/'
        url = origin + 'logo.png'
        post_data = {
            'submitter': '/api/v1/user/{}/'.format(self.user.pk),
            'url': url,
            'description': 'That\'s an Apple!',
            'origin': origin
        }
        response = self.api_client.post('/api/v1/pin/', data=post_data)
        self.assertHttpCreated(response)
        self.assertEqual(Pin.objects.count(), 1)
        self.assertEqual(Image.objects.count(), 1)
        self.assertEqual(Pin.objects.get(url=url).origin, origin)

    def test_post_create_obj(self):
        image = ImageFactory()
        post_data = {
            'submitter': '/api/v1/user/{}/'.format(self.user.pk),
            'image': '/api/v1/image/{}/'.format(image.pk),
            'description': 'That\'s something else (probably a CC logo)!',
            'tags': ['random', 'tags'],
        }
        response = self.api_client.post('/api/v1/pin/', data=post_data)
        self.assertEqual(
            self.deserialize(response)['description'],
            'That\'s something else (probably a CC logo)!'
        )
        self.assertHttpCreated(response)
        # A number of Image objects should stay the same as we are using an existing image
        self.assertEqual(Image.objects.count(), 1)
        self.assertEqual(Pin.objects.count(), 1)
        self.assertEquals(Tag.objects.count(), 2)

    def test_put_detail_unauthenticated(self):
        self.api_client.client.logout()
        uri = '/api/v1/pin/{}/'.format(PinFactory().pk)
        response = self.api_client.put(uri, format='json', data={})
        self.assertHttpUnauthorized(response)

    def test_put_detail_unauthorized(self):
        uri = '/api/v1/pin/{}/'.format(PinFactory(submitter=self.user).pk)
        user = UserFactory(password='password')
        self.api_client.client.login(username=user.username, password='password')
        response = self.api_client.put(uri, format='json', data={})
        self.assertHttpUnauthorized(response)

    def test_put_detail(self):
        pin = PinFactory(submitter=self.user)
        uri = '/api/v1/pin/{}/'.format(pin.pk)
        new = {'description': 'Updated description'}

        response = self.api_client.put(uri, format='json', data=new)
        self.assertHttpAccepted(response)
        self.assertEqual(Pin.objects.count(), 1)
        self.assertEqual(Pin.objects.get(pk=pin.pk).description, new['description'])

    def test_delete_detail_unauthenticated(self):
        uri = '/api/v1/pin/{}/'.format(PinFactory(submitter=self.user).pk)
        self.api_client.client.logout()
        self.assertHttpUnauthorized(self.api_client.delete(uri))

    def test_delete_detail_unauthorized(self):
        uri = '/api/v1/pin/{}/'.format(PinFactory(submitter=self.user).pk)
        User.objects.create_user('test', 'test@example.com', 'test')
        self.api_client.client.login(username='test', password='test')
        self.assertHttpUnauthorized(self.api_client.delete(uri))

    def test_delete_detail(self):
        uri = '/api/v1/pin/{}/'.format(PinFactory(submitter=self.user).pk)
        self.assertHttpAccepted(self.api_client.delete(uri))
        self.assertEqual(Pin.objects.count(), 0)

    def test_get_list_json_ordered(self):
        _, pin = PinFactory(), PinFactory()
        response = self.api_client.get('/api/v1/pin/', format='json', data={'order_by': '-id'})
        self.assertValidJSONResponse(response)
        self.assertEqual(self.deserialize(response)['objects'][0]['id'], pin.id)

    def test_get_list_json_filtered_by_tags(self):
        pin = PinFactory()
        response = self.api_client.get('/api/v1/pin/', format='json', data={'tag': pin.tags.all()[0]})
        self.assertValidJSONResponse(response)
        self.assertEqual(self.deserialize(response)['objects'][0]['id'], pin.pk)

    def test_get_list_json_filtered_by_submitter(self):
        pin = PinFactory(submitter=self.user)
        response = self.api_client.get('/api/v1/pin/', format='json', data={'submitter__username': self.user.username})
        self.assertValidJSONResponse(response)
        self.assertEqual(self.deserialize(response)['objects'][0]['id'], pin.pk)

    def test_get_list_json(self):
        image = ImageFactory()
        pin = PinFactory(**{
            'submitter': self.user,
            'image': image,
            'url': 'http://testserver/mocked/logo.png',
            'description': u'Mocked Description',
            'origin': None
        })
        standard = filter_generator_for('standard')(image)
        thumbnail = filter_generator_for('thumbnail')(image)
        square = filter_generator_for('square')(image)
        response = self.api_client.get('/api/v1/pin/', format='json')
        self.assertValidJSONResponse(response)
        self.assertDictEqual(self.deserialize(response)['objects'][0], {
            u'id': pin.id,
            u'submitter': {
                u'username': unicode(self.user.username),
                u'gravatar': unicode(self.user.gravatar)
            },
            u'image': {
                u'image': unicode(image.image.url),
                u'width': image.width,
                u'height': image.height,
                u'standard': {
                    u'image': unicode(standard.image.url),
                    u'width': standard.width,
                    u'height': standard.height,
                },
                u'thumbnail': {
                    u'image': unicode(thumbnail.image.url),
                    u'width': thumbnail.width,
                    u'height': thumbnail.height,
                },
                u'square': {
                    u'image': unicode(square.image.url),
                    u'width': square.width,
                    u'height': square.height,
                    },
            },
            u'url': pin.url,
            u'origin': pin.origin,
            u'description': pin.description,
            u'tags': [tag.name for tag in pin.tags.all()]
        })

########NEW FILE########
__FILENAME__ = forms
from django.test import TestCase
from ..forms import ImageForm


__all__ = ['ImageFormTest']

class ImageFormTest(TestCase):
    def test_image_field_prefix(self):
        """Assert that the image field has a proper name"""
        form = ImageForm()
        self.assertInHTML("<input id='id_qqfile' name='qqfile' type='file' />", str(form))
########NEW FILE########
__FILENAME__ = helpers
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.files.images import ImageFile
from django.db.models.query import QuerySet
from django.test import TestCase
from django_images.models import Thumbnail

import factory
from taggit.models import Tag

from ..models import Pin, Image
from ...users.models import User


TEST_IMAGE_PATH = 'logo.png'


class UserFactory(factory.Factory):
    FACTORY_FOR = User

    username = factory.Sequence(lambda n: 'user_{}'.format(n))
    email = factory.Sequence(lambda n: 'user_{}@example.com'.format(n))

    @factory.post_generation(extract_prefix='password')
    def set_password(self, create, extracted, **kwargs):
        self.set_password(extracted)
        self.save()

    @factory.post_generation(extract_prefix='user_permissions')
    def set_user_permissions(self, create, extracted, **kwargs):
        self.user_permissions = Permission.objects.filter(codename__in=['add_pin', 'add_image'])


class TagFactory(factory.Factory):
    FACTORY_FOR = Tag

    name = factory.Sequence(lambda n: 'tag_{}'.format(n))


class ImageFactory(factory.Factory):
    FACTORY_FOR = Image

    image = factory.LazyAttribute(lambda a: ImageFile(open(TEST_IMAGE_PATH, 'rb')))

    @factory.post_generation()
    def create_thumbnails(self, create, extracted, **kwargs):
        for size in settings.IMAGE_SIZES.keys():
            Thumbnail.objects.get_or_create_at_size(self.pk, size)


class PinFactory(factory.Factory):
    FACTORY_FOR = Pin

    submitter = factory.SubFactory(UserFactory)
    image = factory.SubFactory(ImageFactory)

    @factory.post_generation(extract_prefix='tags')
    def add_tags(self, create, extracted, **kwargs):
        if isinstance(extracted, Tag):
            self.tags.add(extracted)
        elif isinstance(extracted, list):
            self.tags.add(*extracted)
        elif isinstance(extracted, QuerySet):
            self.tags = extracted
        else:
            self.tags.add(TagFactory())


class PinFactoryTest(TestCase):
    def test_default_tags(self):
        tags = PinFactory.create().tags.all()
        self.assertTrue(all([tag.name.startswith('tag_') for tag in tags]))
        self.assertEqual(tags.count(), 1)

    def test_custom_tag(self):
        custom = 'custom_tag'
        self.assertEqual(PinFactory(tags=Tag.objects.create(name=custom)).tags.get(pk=1).name, custom)

    def test_custom_tags_list(self):
        tags = TagFactory.create_batch(2)
        PinFactory(tags=tags)
        self.assertEqual(Tag.objects.count(), 2)

    def test_custom_tags_queryset(self):
        TagFactory.create_batch(2)
        tags = Tag.objects.all()
        PinFactory(tags=tags)
        self.assertEqual(Tag.objects.count(), 2)

    def test_empty_tags(self):
        PinFactory(tags=[])
        self.assertEqual(Tag.objects.count(), 0)

########NEW FILE########
__FILENAME__ = views
from django.conf import settings
from django.core.urlresolvers import reverse
from django.template import TemplateDoesNotExist
from django.test import TestCase

from .api import UserFactory
from ...core.models import Image


__all__ = ['CreateImageTest']


class CreateImageTest(TestCase):
    def setUp(self):
        self.user = UserFactory(password='password')
        self.client.login(username=self.user.username, password='password')

    def test_get_browser(self):
        response = self.client.get(reverse('core:create-image'))
        self.assertRedirects(response, reverse('core:recent-pins'))

    def test_get_xml_http_request(self):
        with self.assertRaises(TemplateDoesNotExist):
            self.client.get(reverse('core:create-image'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_post(self):
        with open(settings.SITE_ROOT + 'logo.png', mode='rb') as image:
            response = self.client.post(reverse('core:create-image'), {'qqfile': image})
        image = Image.objects.latest('pk')
        self.assertJSONEqual(response.content, {'success': {'id': image.pk}})

    def test_post_error(self):
        response = self.client.post(reverse('core:create-image'), {'qqfile': None})
        self.assertJSONEqual(response.content, {
            'error': {'image': ['This field is required.']}
        })

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

from tastypie.api import Api

from .api import ImageResource, ThumbnailResource, PinResource, UserResource
from .feeds import LatestPins, LatestUserPins, LatestTagPins
from .views import CreateImage


v1_api = Api(api_name='v1')
v1_api.register(ImageResource())
v1_api.register(ThumbnailResource())
v1_api.register(PinResource())
v1_api.register(UserResource())


urlpatterns = patterns('',
    url(r'^api/', include(v1_api.urls, namespace='api')),

    url(r'feeds/latest-pins/tag/(?P<tag>(\w|-)+)/', LatestTagPins()),
    url(r'feeds/latest-pins/user/(?P<user>(\w|-)+)/', LatestUserPins()),
    url(r'feeds/latest-pins/', LatestPins()),

    url(r'^pins/pin-form/$', TemplateView.as_view(template_name='core/pin_form.html'),
        name='pin-form'),
    url(r'^pins/create-image/$', CreateImage.as_view(), name='create-image'),

    url(r'^pins/tag/(?P<tag>(\w|-)+)/$', TemplateView.as_view(template_name='core/pins.html'),
        name='tag-pins'),
    url(r'^pins/user/(?P<user>(\w|-)+)/$', TemplateView.as_view(template_name='core/pins.html'),
        name='user-pins'),
    url(r'^(?P<pin>\d+)/$', TemplateView.as_view(template_name='core/pins.html'),
        name='recent-pins'),
    url(r'^$', TemplateView.as_view(template_name='core/pins.html'),
        name='recent-pins'),
)

########NEW FILE########
__FILENAME__ = utils
import hashlib
import os

def upload_path(instance, filename, **kwargs):
    hasher = hashlib.md5()
    for chunk in instance.image.chunks():
        hasher.update(chunk)
    hash = hasher.hexdigest()
    base, ext = os.path.splitext(filename)
    return '%(first)s/%(second)s/%(hash)s/%(base)s%(ext)s' % {
        'first': hash[0],
        'second': hash[1],
        'hash': hash,
        'base': base,
        'ext': ext,
    }

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponseRedirect
from django.conf import settings
from django.core.urlresolvers import reverse
from django.views.generic import CreateView
from django_images.models import Image

from braces.views import JSONResponseMixin, LoginRequiredMixin
from django_images.models import Thumbnail

from .forms import ImageForm


class CreateImage(JSONResponseMixin, LoginRequiredMixin, CreateView):
    template_name = None  # JavaScript-only view
    model = Image
    form_class = ImageForm

    def get(self, request, *args, **kwargs):
        if not request.is_ajax():
            return HttpResponseRedirect(reverse('core:recent-pins'))
        return super(CreateImage, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        image = form.save()
        for size in settings.IMAGE_SIZES:
            Thumbnail.objects.get_or_create_at_size(image.pk, size)
        return self.render_json_response({
            'success': {
                'id': image.id
            }
        })

    def form_invalid(self, form):
        return self.render_json_response({'error': form.errors})

########NEW FILE########
__FILENAME__ = development
from pinry.settings import *

import os


DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(SITE_ROOT, 'development.db'),
    }
}

SECRET_KEY = 'fake-key'

########NEW FILE########
__FILENAME__ = production
from pinry.settings import *

import os


DEBUG = False
TEMPLATE_DEBUG = DEBUG

# TODO: I recommend using psycopg2 w/ postgres but sqlite3 is good enough.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(SITE_ROOT, 'production.db'),
    }
}

# TODO: Be sure to set this.
SECRET_KEY = ''

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


urlpatterns = patterns('',
    url(r'', include('pinry.core.urls', namespace='core')),
    url(r'', include('pinry.users.urls', namespace='users')),
)


if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += patterns('', url(r'^media/(?P<path>.*)$',
        'django.views.static.serve', {'document_root': settings.MEDIA_ROOT,}),)

########NEW FILE########
__FILENAME__ = backends
from django.core.validators import email_re

from pinry.core.models import Pin
from pinry.users.models import User


class CombinedAuthBackend(object):
    def authenticate(self, username=None, password=None):
        is_email = email_re.match(username)
        if is_email:
            qs = User.objects.filter(email=username)
        else:
            qs = User.objects.filter(username=username)

        try:
            user = qs.get()
        except User.DoesNotExist:
            return None
        if user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def has_perm(self, user, perm, obj=None):
        """
        A very simplistic authorization mechanism for now. Basically a pin owner can do anything with the pin.
        """
        if obj and isinstance(obj, Pin):
            return obj.submitter == user
        return False

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext, ugettext_lazy as _
from django.contrib.auth.models import User


class UserCreationForm(forms.ModelForm):
    """
    A form that creates a user, with no privileges, from the given username,
    email, and password.
    """
    error_messages = {
        'duplicate_username': _("A user with that username already exists."),
    }
    username = forms.RegexField(label=_("Username"), max_length=30,
        regex=r'^[\w-]+$')
    password = forms.CharField(label=_("Password"),
        widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("username", "email")

    def clean_username(self):
        # Since User.username is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        username = self.cleaned_data["username"]
        try:
            User._default_manager.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(self.error_messages['duplicate_username'])

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse


class Public(object):
    def process_request(self, request):
        if settings.PUBLIC == False and not request.user.is_authenticated():
            acceptable_paths = [
                '/login/',
                '/private/',
                '/register/',
            ]
            if request.path not in acceptable_paths:
                return HttpResponseRedirect(reverse('users:private'))

########NEW FILE########
__FILENAME__ = models
import hashlib

from django.contrib.auth.models import User as BaseUser


class User(BaseUser):
    @property
    def gravatar(self):
        return hashlib.md5(self.email).hexdigest()

    class Meta:
        proxy = True
########NEW FILE########
__FILENAME__ = tests
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings

import mock

from .auth.backends import CombinedAuthBackend
from ..core.models import Image, Pin
from .models import User


def mock_requests_get(url):
    response = mock.Mock(content=open('logo.png', 'rb').read())
    return response


class CombinedAuthBackendTest(TestCase):
    def setUp(self):
        self.backend = CombinedAuthBackend()
        self.username = 'jdoe'
        self.email = 'jdoe@example.com'
        self.password = 'password'
        User.objects.create_user(username=self.username, email=self.email, password=self.password)

    def test_authenticate_username(self):
        self.assertTrue(self.backend.authenticate(username=self.username, password=self.password))

    def test_authenticate_email(self):
        self.assertTrue(self.backend.authenticate(username=self.email, password=self.password))

    def test_authenticate_wrong_password(self):
        self.assertIsNone(self.backend.authenticate(username=self.username, password='wrong-password'))

    def test_authenticate_unknown_user(self):
        self.assertIsNone(self.backend.authenticate(username='wrong-username', password='wrong-password'))

    @mock.patch('requests.get', mock_requests_get)
    def test_has_perm_on_pin(self):
        image = Image.objects.create_for_url('http://testserver/mocked/screenshot.png')
        user = User.objects.get(username=self.username)
        pin = Pin.objects.create(submitter=user, image=image)
        self.assertTrue(self.backend.has_perm(user, 'add_pin', pin))

    @mock.patch('requests.get', mock_requests_get)
    def test_has_perm_on_pin_unauthorized(self):
        image = Image.objects.create_for_url('http://testserver/mocked/screenshot.png')
        user = User.objects.get(username=self.username)
        other_user = User.objects.create_user('test', 'test@example.com', 'test')
        pin = Pin.objects.create(submitter=user, image=image)
        self.assertFalse(self.backend.has_perm(other_user, 'add_pin', pin))


class CreateUserTest(TestCase):
    def test_create_post(self):
        data = {
            'username': 'jdoe',
            'email': 'jdoe@example.com',
            'password': 'password'
        }
        response = self.client.post(reverse('users:register'), data=data)
        self.assertRedirects(response, reverse('core:recent-pins'))
        self.assertIn('_auth_user_id', self.client.session)

    @override_settings(ALLOW_NEW_REGISTRATIONS=False)
    def test_create_post_not_allowed(self):
        response = self.client.get(reverse('users:register'))
        self.assertRedirects(response, reverse('core:recent-pins'))


class LogoutViewTest(TestCase):
    def setUp(self):
        User.objects.create_user(username='jdoe', password='password')
        self.client.login(username='jdoe', password='password')

    def test_logout_view(self):
        response = self.client.get(reverse('users:logout'))
        self.assertRedirects(response, reverse('core:recent-pins'))

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from .views import CreateUser

urlpatterns = patterns('',
    url(r'^private/$', 'pinry.users.views.private', name='private'),
    url(r'^register/$', CreateUser.as_view(), name='register'),
    url(r'^login/$', 'django.contrib.auth.views.login',
        {'template_name': 'users/login.html'}, name='login'),
    url(r'^logout/$', 'pinry.users.views.logout_user', name='logout'),
)

########NEW FILE########
__FILENAME__ = views
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.functional import lazy
from django.views.generic import CreateView

from .forms import UserCreationForm
from pinry.users.models import User


reverse_lazy = lambda name=None, *args: lazy(reverse, str)(name, args=args)


class CreateUser(CreateView):
    template_name = 'users/register.html'
    model = User
    form_class = UserCreationForm
    success_url = reverse_lazy('core:recent-pins')

    def get(self, request, *args, **kwargs):
        if not settings.ALLOW_NEW_REGISTRATIONS:
            messages.error(request, "The admin of this service is not allowing new registrations.")
            return HttpResponseRedirect(reverse('core:recent-pins'))
        return super(CreateUser, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        redirect = super(CreateUser, self).form_valid(form)
        permissions = Permission.objects.filter(codename__in=['add_pin', 'add_image'])
        user = authenticate(username=form.cleaned_data['username'],
                            password=form.cleaned_data['password'])
        user.user_permissions = permissions
        login(self.request, user)
        return redirect


@login_required
def logout_user(request):
    logout(request)
    messages.success(request, 'You have successfully logged out.')
    return HttpResponseRedirect(reverse('core:recent-pins'))


def private(request):
    return TemplateResponse(request, 'users/private.html', None)

########NEW FILE########
__FILENAME__ = wsgi
import os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pinry.settings.production")


from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
