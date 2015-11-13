__FILENAME__ = build-i18n
#!/usr/bin/env python

from __future__ import unicode_literals

import os
import sys

from django.core.management.commands.compilemessages import compile_messages
from djblets.util.filesystem import is_exe_in_path


if __name__ == '__main__':
    if not is_exe_in_path('msgfmt'):
        raise RuntimeError('Could not find the "msgfmt" binary.')

    cwd = os.getcwd()
    os.chdir(os.path.realpath('djblets'))
    compile_messages(sys.stdout)
    os.chdir(cwd)

########NEW FILE########
__FILENAME__ = build-media
#!/usr/bin/env python

import os
import sys

scripts_dir = os.path.abspath(os.path.dirname(__file__))

# Source root directory
sys.path.insert(0, os.path.abspath(os.path.join(scripts_dir, '..', '..')))

from djblets import django_version

import __main__
__main__.__requires__ = [django_version]
import pkg_resources

from django.core.management import call_command


if __name__ == '__main__':
    os.putenv('FORCE_BUILD_MEDIA', '1')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djblets.settings')

    ret = call_command('collectstatic', interactive=False, verbosity=2)
    sys.exit(ret)

########NEW FILE########
__FILENAME__ = release
#!/usr/bin/env python
#
# Performs a release of Review Board. This can only be run by the core
# developers with release permissions.
#

import os
import re
import shutil
import sys
import tempfile

from fabazon.s3 import S3Bucket

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from djblets import __version__, __version_info__, is_release


PY_VERSIONS = ["2.6", "2.7"]

LATEST_PY_VERSION = PY_VERSIONS[-1]

PACKAGE_NAME = 'Djblets'

RELEASES_BUCKET_NAME = 'downloads.reviewboard.org'
RELEASES_BUCKET_KEY = '/releases/%s/%s.%s/' % (PACKAGE_NAME,
                                               __version_info__[0],
                                               __version_info__[1])


built_files = []


def execute(cmdline):
    print ">>> %s" % cmdline
    if os.system(cmdline) != 0:
        sys.stderr.write('!!! Error invoking command.\n')
        sys.exit(1)


def run_setup(target, pyver=LATEST_PY_VERSION):
    execute("python%s ./setup.py release %s" % (pyver, target))


def clone_git_tree(git_dir):
    new_git_dir = tempfile.mkdtemp(prefix='djblets-release.')

    os.chdir(new_git_dir)
    execute('git clone %s .' % git_dir)

    return new_git_dir


def build_targets():
    for pyver in PY_VERSIONS:
        run_setup('bdist_egg', pyver)
        built_files.append(('dist/%s-%s-py%s.egg'
                            % (PACKAGE_NAME, __version__, pyver),
                            'application/octet-stream'))

    run_setup('sdist')
    built_files.append(('dist/%s-%s.tar.gz' % (PACKAGE_NAME, __version__),
                        'application/x-tar'))


def build_news():
    def linkify_bugs(line):
        return re.sub(r'(Bug #(\d+))',
                      r'<a href="http://www.reviewboard.org/bug/\2">\1</a>',
                      line)

    content = ""
    html_content = ""

    saw_version = False
    in_list = False
    in_item = False

    fp = open("NEWS", "r")

    for line in fp.xreadlines():
        line = line.rstrip()

        if line.startswith("version "):
            if saw_version:
                # We're done.
                break

            saw_version = True
        elif line.startswith("\t* "):
            if in_item:
                html_content += "</li>\n"
                in_item = False

            if in_list:
                html_content += "</ul>\n"

            html_content += "<p><b>%s</b></p>\n" % line[3:]
            html_content += "<ul>\n"
            in_list = True
        elif line.startswith("\t\t* "):
            if not in_list:
                sys.stderr.write("*** Found a list item without a list!\n")
                continue

            if in_item:
                html_content += "</li>\n"

            html_content += " <li>%s" % linkify_bugs(line[4:])
            in_item = True
        elif line.startswith("\t\t  "):
            if not in_item:
                sys.stderr.write("*** Found list item content without "
                                 "a list item!\n")
                continue

            html_content += " " + linkify_bugs(line[4:])

        content += line + "\n"

    fp.close()

    if in_item:
        html_content += "</li>\n"

    if in_list:
        html_content += "</ul>\n"

    content = content.rstrip()

    filename = "dist/%s-%s.NEWS" % (PACKAGE_NAME, __version__)
    built_files.append((filename, 'text/plain'))
    fp = open(filename, "w")
    fp.write(content)
    fp.close()

    filename = "dist/%s-%s.NEWS.html" % (PACKAGE_NAME, __version__)
    fp = open(filename, "w")
    fp.write(html_content)
    fp.close()


def upload_files():
    bucket = S3Bucket(RELEASES_BUCKET_NAME)

    for filename, mimetype in built_files:
        bucket.upload(filename,
                      '%s%s' % (RELEASES_BUCKET_KEY,
                                filename.split('/')[-1]),
                      mimetype=mimetype,
                      public=True)

    bucket.upload_directory_index(RELEASES_BUCKET_KEY)

    # This may be a new directory, so rebuild the parent as well.
    parent_key = '/'.join(RELEASES_BUCKET_KEY.split('/')[:-2])
    bucket.upload_directory_index(parent_key)


def tag_release():
    execute("git tag release-%s" % __version__)


def register_release():
    if __version_info__[3] == 'final':
        run_setup("register")


def main():
    if not os.path.exists("setup.py"):
        sys.stderr.write("This must be run from the root of the "
                         "Djblets tree.\n")
        sys.exit(1)

    if not is_release():
        sys.stderr.write('This has not been marked as a release in '
                         'djblets/__init__.py\n')
        sys.exit(1)

    cur_dir = os.getcwd()
    git_dir = clone_git_tree(cur_dir)

    build_targets()
    build_news()
    upload_files()

    os.chdir(cur_dir)
    shutil.rmtree(git_dir)

    tag_release()
    register_release()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = forms
#
# forms.py -- Forms for authentication
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from django import forms
from django.contrib import auth
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from djblets.db.query import get_object_or_none


class RegistrationForm(forms.Form):
    """Registration form that should be appropriate for most cases."""

    username = forms.RegexField(r"^[a-zA-Z0-9_\-\.]*$",
                                max_length=30,
                                error_message='Only A-Z, 0-9, "_", "-", and "." allowed.')
    password1 = forms.CharField(label=_('Password'),
                                min_length=5,
                                max_length=30,
                                widget=forms.PasswordInput)
    password2 = forms.CharField(label=_('Password (confirm)'),
                                widget=forms.PasswordInput)
    email = forms.EmailField(label=_('E-mail address'))
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)

    def __init__(self, request=None, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.request = request

    def clean_password2(self):
        formdata = self.cleaned_data
        if 'password1' in formdata:
            if formdata['password1'] != formdata['password2']:
                raise ValidationError(_('Passwords must match'))
        return formdata['password2']

    def save(self):
        if not self.errors:
            try:
                user = auth.models.User.objects.create_user(
                    self.cleaned_data['username'],
                    self.cleaned_data['email'],
                    self.cleaned_data['password1'])
                user.first_name = self.cleaned_data['first_name']
                user.last_name = self.cleaned_data['last_name']
                user.save()
                return user
            except:
                # We check for duplicate users here instead of clean, since it's
                # possible that two users could race for a name.
                if get_object_or_none(User,
                                      username=self.cleaned_data['username']):
                    self.errors['username'] = forms.util.ErrorList(
                        [_('Sorry, this username is taken.')])
                else:
                    raise

########NEW FILE########
__FILENAME__ = util
#
# util.py - Helper utilities for authentication
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
# Copyright (c) 2007  Micah Dowty
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext as _


def validate_test_cookie(form, request):
    if not request.session.test_cookie_worked():
        form.errors['submit'] = forms.util.ErrorList(
            [_('Cookies must be enabled.')])

def validate_old_password(form, user, field_name='password'):
    if (not form.errors.get(field_name) and
            not user.check_password(form.data.get(field_name))):
        form.errors[field_name] = forms.util.ErrorList(
            [_('Incorrect password.')])

########NEW FILE########
__FILENAME__ = views
#
# views.py -- Views for the authentication app
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
# Copyright (C) 2007 Micah Dowty
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from django.contrib import auth
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.views.decorators.csrf import csrf_protect

from djblets.auth.forms import RegistrationForm
from djblets.auth.util import validate_test_cookie


###########################
#    User Registration    #
###########################

@csrf_protect
def register(request, next_page, form_class=RegistrationForm,
             extra_context={},
             template_name="accounts/register.html"):
    if request.method == 'POST':
        form = form_class(data=request.POST, request=request)
        form.full_clean()
        validate_test_cookie(form, request)

        if form.is_valid():
            user = form.save()
            if user:
                user = auth.authenticate(
                    username=form.cleaned_data['username'],
                    password=form.cleaned_data['password1'])
                assert user
                auth.login(request, user)
                try:
                    request.session.delete_test_cookie()
                except KeyError:
                    # Do nothing
                    pass

                return HttpResponseRedirect(next_page)
    else:
        form = form_class(request=request)

    request.session.set_test_cookie()

    context = {
        'form': form,
    }
    context.update(extra_context)

    return render_to_response(template_name, RequestContext(request, context))

########NEW FILE########
__FILENAME__ = backend
from __future__ import unicode_literals
from hashlib import md5
import logging
import zlib

from django.conf import settings
from django.core.cache import cache
from django.contrib.sites.models import Site
from django.utils.six.moves import (cPickle as pickle,
                                    cStringIO as StringIO)

from djblets.cache.errors import MissingChunkError


DEFAULT_EXPIRATION_TIME = 60 * 60 * 24 * 30 # 1 month
CACHE_CHUNK_SIZE = 2**20 - 1024 # almost 1M (memcached's slab limit)

# memcached key size constraint (typically 250, but leave a few bytes for the
# large data handling)
MAX_KEY_SIZE = 240


def _cache_fetch_large_data(cache, key, compress_large_data):
    chunk_count = cache.get(make_cache_key(key))
    data = []

    chunk_keys = [make_cache_key('%s-%d' % (key, i))
                  for i in range(int(chunk_count))]
    chunks = cache.get_many(chunk_keys)
    for chunk_key in chunk_keys:
        try:
            data.append(chunks[chunk_key][0])
        except KeyError:
            logging.debug('Cache miss for key %s.' % chunk_key)
            raise MissingChunkError

    data = b''.join(data)

    if compress_large_data:
        data = zlib.decompress(data)

    try:
        unpickler = pickle.Unpickler(StringIO(data))
        data = unpickler.load()
    except Exception as e:
        logging.warning('Unpickle error for cache key "%s": %s.' % (key, e))
        raise e

    return data


def _cache_store_large_data(cache, key, data, expiration, compress_large_data):
    # We store large data in the cache broken into chunks that are 1M in size.
    # To do this easily, we first pickle the data and compress it with zlib.
    # This gives us a string which can be chunked easily. These are then stored
    # individually in the cache as single-element lists (so the cache backend
    # doesn't try to convert binary data to utf8). The number of chunks needed
    # is stored in the cache under the unadorned key
    file = StringIO()
    pickler = pickle.Pickler(file)
    pickler.dump(data)
    data = file.getvalue()

    if compress_large_data:
        data = zlib.compress(data)

    i = 0
    while len(data) > CACHE_CHUNK_SIZE:
        chunk = data[0:CACHE_CHUNK_SIZE]
        data = data[CACHE_CHUNK_SIZE:]
        cache.set(make_cache_key('%s-%d' % (key, i)), [chunk], expiration)
        i += 1
    cache.set(make_cache_key('%s-%d' % (key, i)), [data], expiration)

    cache.set(make_cache_key(key), '%d' % (i + 1), expiration)


def cache_memoize(key, lookup_callable,
                  expiration=getattr(settings, 'CACHE_EXPIRATION_TIME',
                                     DEFAULT_EXPIRATION_TIME),
                  force_overwrite=False,
                  large_data=False,
                  compress_large_data=True):
    """Memoize the results of a callable inside the configured cache.

    Keyword arguments:
    expiration          -- The expiration time for the key.
    force_overwrite     -- If True, the value will always be computed and stored
                           regardless of whether it exists in the cache already.
    large_data          -- If True, the resulting data will be pickled, gzipped,
                           and (potentially) split up into megabyte-sized chunks.
                           This is useful for very large, computationally
                           intensive hunks of data which we don't want to store
                           in a database due to the way things are accessed.
    compress_large_data -- Compresses the data with zlib compression when
                           large_data is True.
    """
    if large_data:
        if not force_overwrite and make_cache_key(key) in cache:
            try:
                data = _cache_fetch_large_data(cache, key, compress_large_data)
                return data
            except Exception as e:
                logging.warning('Failed to fetch large data from cache for '
                                'key %s: %s.' % (key, e))
        else:
            logging.debug('Cache miss for key %s.' % key)

        data = lookup_callable()
        _cache_store_large_data(cache, key, data, expiration,
                                compress_large_data)
        return data

    else:
        key = make_cache_key(key)
        if not force_overwrite and key in cache:
            return cache.get(key)
        data = lookup_callable()

        # Most people will be using memcached, and memcached has a limit of 1MB.
        # Data this big should be broken up somehow, so let's warn about this.
        # Users should hopefully be using large_data=True in this case.
        # XXX - since 'data' may be a sequence that's not a string/unicode,
        #       this can fail. len(data) might be something like '6' but the
        #       data could exceed a megabyte. The best way to catch this would
        #       be an exception, but while python-memcached defines an exception
        #       type for this, it never uses it, choosing instead to fail
        #       silently. WTF.
        if len(data) >= CACHE_CHUNK_SIZE:
            logging.warning('Cache data for key "%s" (length %s) may be too '
                            'big for the cache.' % (key, len(data)))

        try:
            cache.set(key, data, expiration)
        except:
            pass
        return data


def make_cache_key(key):
    """Creates a cache key guaranteed to avoid conflicts and size limits.

    The cache key will be prefixed by the site's domain, and will be
    changed to an MD5SUM if it's larger than the maximum key size.
    """
    try:
        site = Site.objects.get_current()

        # The install has a Site app, so prefix the domain to the key.
        # If a SITE_ROOT is defined, also include that, to allow for multiple
        # instances on the same host.
        site_root = getattr(settings, 'SITE_ROOT', None)

        if site_root:
            key = '%s:%s:%s' % (site.domain, site_root, key)
        else:
            key = '%s:%s' % (site.domain, key)
    except:
        # The install doesn't have a Site app, so use the key as-is.
        pass

    # Adhere to memcached key size limit
    if len(key) > MAX_KEY_SIZE:
        digest = md5(key.encode('utf-8')).hexdigest();

        # Replace the excess part of the key with a digest of the key
        key = key[:MAX_KEY_SIZE - len(digest)] + digest

    # Make sure this is a non-unicode string, in order to prevent errors
    # with some backends.
    key = key.encode('utf-8')

    return key

########NEW FILE########
__FILENAME__ = backend_compat
from __future__ import unicode_literals
import logging

from django.core.cache import (DEFAULT_CACHE_ALIAS, parse_backend_uri,
                               InvalidCacheBackendError)


BACKEND_CLASSES = {
    'db': 'db.DatabaseCache',
    'dummy': 'dummy.DummyCache',
    'file': 'filebased.FileBasedCache',
    'locmem': 'locmem.LocMemCache',
    'memcached': 'memcached.CacheClass',
}


def normalize_cache_backend(cache_backend):
    """Returns a new-style CACHES dictionary from any given cache_backend.

    Django has supported two formats for a cache backend. The old-style
    CACHE_BACKEND string, and the new-style CACHES dictionary.

    This function will accept either as input and return a cahe backend in the
    form of a CACHES dictionary as a result. The result won't be a full-on
    CACHES, with named cache entries inside. Rather, it will be a cache entry.

    If a CACHES dictionary is passed, the "default" cache will be the result.
    """
    if not cache_backend:
        return {}

    if isinstance(cache_backend, dict):
        if DEFAULT_CACHE_ALIAS in cache_backend:
            return cache_backend[DEFAULT_CACHE_ALIAS]

        return {}

    try:
        engine, host, params = parse_backend_uri(cache_backend)
    except InvalidCacheBackendError as e:
        logging.error('Invalid cache backend (%s) found while loading '
                      'siteconfig: %s' % (cache_backend, e))
        return {}

    if engine in BACKEND_CLASSES:
        engine = 'django.core.cache.backends.%s' % BACKEND_CLASSES[engine]
    else:
        engine = '%s.CacheClass' % engine

    defaults = {
        'BACKEND': engine,
        'LOCATION': host,
    }
    defaults.update(params)

    return defaults

########NEW FILE########
__FILENAME__ = context_processors
from __future__ import unicode_literals

from django.conf import settings


def media_serial(request):
    """
    Exposes a media serial number that can be appended to a media filename
    in order to make a URL that can be cached forever without fear of change.
    The next time the file is updated and the server is restarted, a new
    path will be accessed and cached.

    This returns the value of settings.MEDIA_SERIAL, which must either be
    set manually or ideally should be set to the value of
    djblets.cache.serials.generate_media_serial().
    """
    return {'MEDIA_SERIAL': getattr(settings, "MEDIA_SERIAL", "")}


def ajax_serial(request):
    """
    Exposes a serial number that can be appended to filenames involving
    dynamic loads of URLs in order to make a URL that can be cached forever
    without fear of change.

    This returns the value of settings.AJAX_SERIAL, which must either be
    set manually or ideally should be set to the value of
    djblets.cache.serials.generate_ajax_serial().
    """
    return {'AJAX_SERIAL': getattr(settings, "AJAX_SERIAL", "")}

########NEW FILE########
__FILENAME__ = errors
class MissingChunkError(Exception):
    pass

########NEW FILE########
__FILENAME__ = serials
from __future__ import unicode_literals
import logging
import os

from django.conf import settings
from django.utils import importlib


def generate_media_serial():
    """
    Generates a media serial number that can be appended to a media filename
    in order to make a URL that can be cached forever without fear of change.
    The next time the file is updated and the server is restarted, a new
    path will be accessed and cached.

    This will crawl the media files (using directories in MEDIA_SERIAL_DIRS if
    specified, or all of STATIC_ROOT otherwise), figuring out the latest
    timestamp, and return that value.
    """
    MEDIA_SERIAL = getattr(settings, "MEDIA_SERIAL", 0)

    if not MEDIA_SERIAL:
        media_dirs = getattr(settings, "MEDIA_SERIAL_DIRS", ["."])

        for media_dir in media_dirs:
            media_path = os.path.join(settings.STATIC_ROOT, media_dir)

            for root, dirs, files in os.walk(media_path):
                for name in files:
                    mtime = int(os.stat(os.path.join(root, name)).st_mtime)

                    if mtime > MEDIA_SERIAL:
                        MEDIA_SERIAL = mtime

        setattr(settings, "MEDIA_SERIAL", MEDIA_SERIAL)


def generate_ajax_serial():
    """
    Generates a serial number that can be appended to filenames involving
    dynamic loads of URLs in order to make a URL that can be cached forever
    without fear of change.

    This will crawl the template files (using directories in TEMPLATE_DIRS),
    figuring out the latest timestamp, and return that value.
    """
    AJAX_SERIAL = getattr(settings, "AJAX_SERIAL", 0)

    if not AJAX_SERIAL:
        template_dirs = getattr(settings, "TEMPLATE_DIRS", ["."])

        for template_path in template_dirs:
            for root, dirs, files in os.walk(template_path):
                for name in files:
                    mtime = int(os.stat(os.path.join(root, name)).st_mtime)

                    if mtime > AJAX_SERIAL:
                        AJAX_SERIAL = mtime

        setattr(settings, "AJAX_SERIAL", AJAX_SERIAL)


def generate_locale_serial(packages):
    """Generate a locale serial for the given set of packages.

    This will be equal to the most recent mtime of all the .mo files that
    contribute to the localization of the given packages.
    """
    serial = 0

    paths = []
    for package in packages:
        try:
            p = importlib.import_module(package)
            path = os.path.join(os.path.dirname(p.__file__), 'locale')
            paths.append(path)
        except Exception as e:
            logging.error(
                'Failed to import package %s to compute locale serial: %s'
                % (package, e))

    for locale_path in paths:
        for root, dirs, files in os.walk(locale_path):
            for name in files:
                if name.endswith('.mo'):
                    mtime = int(os.stat(os.path.join(root, name)).st_mtime)
                    if mtime > serial:
                        serial = mtime

    return serial


def generate_cache_serials():
    """
    Wrapper around generate_media_serial and generate_ajax_serial to
    generate all serial numbers in one go.

    This should be called early in the startup, such as in the site's
    main urls.py.
    """
    generate_media_serial()
    generate_ajax_serial()

########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals

from django import forms
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils import six
from django.utils.translation import ugettext_lazy as _


class ConfigPageForm(forms.Form):
    """Base class for a form on a ConfigPage.

    ConfigPageForms belong to ConfigPages, and will be displayed when
    navigating to that ConfigPage.

    A simple form presents fields that can be filled out and posted. More
    advanced forms can supply their own template or even their own
    JavaScript models and views.
    """
    form_id = None
    form_title = None

    save_label = _('Save')

    template_name = 'configforms/config_page_form.html'

    css_bundle_names = []
    js_bundle_names = []

    js_model_class = None
    js_view_class = None

    form_target = forms.CharField(
        required=False,
        widget=forms.HiddenInput)

    def __init__(self, page, request, user, *args, **kwargs):
        super(ConfigPageForm, self).__init__(*args, **kwargs)
        self.page = page
        self.request = request
        self.user = user
        self.profile = user.get_profile()

        self.fields['form_target'].initial = self.form_id
        self.load()

    def set_initial(self, field_values):
        """Sets the initial fields for the form based on provided data.

        This can be used during load() to fill in the fields based on
        data from the database or another source.
        """
        for field, value in six.iteritems(field_values):
            self.fields[field].initial = value

    def is_visible(self):
        """Returns whether the form should be visible.

        This can be overridden to hide forms based on certain criteria.
        """
        return True

    def get_js_model_data(self):
        """Returns data to pass to the JavaScript Model during instantiation.

        If js_model_class is provided, the data returned from this function
        will be provided to the model when constructued.
        """
        return {}

    def get_js_view_data(self):
        """Returns data to pass to the JavaScript View during instantiation.

        If js_view_class is provided, the data returned from this function
        will be provided to the view when constructued.
        """
        return {}

    def render(self):
        """Renders the form."""
        return render_to_string(
            self.template_name,
            RequestContext(self.request, {
                'form': self,
                'page': self.page,
            }))

    def load(self):
        """Loads data for the form.

        By default, this does nothing. Subclasses can override this to
        load data into the fields based on data from the database or
        from another source.
        """
        pass

    def save(self):
        """Saves the form data.

        Subclasses can override this to save data from the fields into
        the database.
        """
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = pages
from __future__ import unicode_literals

from django.template.context import RequestContext
from django.template.loader import render_to_string


class ConfigPage(object):
    """Base class for a page of configuration forms.

    Each ConfigPage is represented in the main page by an entry in the
    navigation sidebar. When the user has navigated to that page, any
    forms owned by the ConfigPage will be displayed.
    """
    page_id = None
    page_title = None
    form_classes = None
    template_name = 'configforms/config_page.html'

    def __init__(self, config_view, request, user):
        self.config_view = config_view
        self.request = request
        self.forms = [
            form_cls(self, request, user)
            for form_cls in self.form_classes
        ]

    def is_visible(self):
        """Returns whether the page should be visible.

        Visible pages are shown in the sidebar and can be navigated to.

        By default, a page is visible if at least one of its forms are
        also visible.
        """
        for form in self.forms:
            if form.is_visible():
                return True

        return False

    def render(self):
        """Renders the page as HTML."""
        return render_to_string(
            self.template_name,
            RequestContext(self.request, {
                'page': self,
                'forms': self.forms,
            }))

########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals

from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.generic.base import TemplateView


class ConfigPagesView(TemplateView):
    """Base view for a set of configuration pages.

    This will render the page for managing a set of configuration sub-pages.
    Subclasses are expected to provide ``title`` and ``page_classes``.

    To dynamically compute pages, implement a ``page_classes`` method and
    decorate it with @property.
    """
    title = None
    nav_title = None
    pages_id = 'config_pages'
    template_name = 'configforms/config.html'
    page_classes = []

    css_bundle_names = []
    js_bundle_names = []

    js_model_class = None
    js_view_class = 'Djblets.Config.PagesView'

    http_method_names = ['get', 'post']

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        self.pages = [
            page_cls(self, request, request.user)
            for page_cls in self.page_classes
        ]

        forms = {}

        # Store a mapping of form IDs to form instances, and check for
        # duplicates.
        for page in self.pages:
            for form in page.forms:
                # This should already be handled during form registration.
                assert form.form_id not in forms, \
                    'Duplicate form ID %s (on page %s)' % (
                        form.form_id, page.page_id)

                forms[form.form_id] = form

        if request.method == 'POST':
            form_id = request.POST.get('form_target')

            if form_id is None:
                return HttpResponseBadRequest()

            if form_id not in forms:
                return Http404

            # Replace the form in the list with a new instantiation containing
            # the form data. If we fail to save, this will ensure the error is
            # shown on the page.
            old_form = forms[form_id]
            form_cls = old_form.__class__
            form = form_cls(old_form.page, request, request.user, request.POST)
            forms[form_id] = form

            if form.is_valid():
                form.save()

                return HttpResponseRedirect(request.path)

        self.forms = forms.values()

        return super(ConfigPagesView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return {
            'page_title': self.title,
            'nav_title': self.nav_title or self.title,
            'pages_id': self.pages_id,
            'pages': self.pages,
            'css_bundle_names': self.css_bundle_names,
            'js_bundle_names': self.js_bundle_names,
            'js_model_class': self.js_model_class,
            'js_view_class': self.js_view_class,
            'js_model_data': self.get_js_model_data(),
            'js_view_data': self.get_js_view_data(),
            'forms': self.forms,
        }

    def get_js_view_data(self):
        """Returns custom options to pass to the JavaScript view.

        By default, this will return an empty dictionary. Subclasses can
        override to provide custom data.
        """
        return {}

    def get_js_model_data(self):
        """Returns custom attributes to pass to the JavaScript model.

        By default, this will return an empty dictionary. Subclasses can
        override to provide custom data.
        """
        return {}

########NEW FILE########
__FILENAME__ = grids
#
# grids.py -- Basic definitions for datagrids
#
# Copyright (c) 2008-2009  Christian Hammond
# Copyright (c) 2008-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

import logging
import traceback

import pytz
from django.conf import settings
from django.contrib.auth.models import SiteProfileNotAvailable
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import InvalidPage, QuerySetPaginator
from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext, Context
from django.template.defaultfilters import date, timesince
from django.template.loader import render_to_string, get_template
from django.utils import six
from django.utils.cache import patch_cache_control
from django.utils.functional import cached_property
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from djblets.util.http import get_url_params_except


# Registration of all datagrid classes to columns.
_column_registry = {}


class Column(object):
    """A column in a data grid.

    The column is the primary component of the data grid. It is used to
    display not only the column header but the HTML for the cell as well.

    Columns can be tied to database fields and can be used for sorting.
    Not all columns have to allow for this, though.

    Columns can have an image, text, or both in the column header. The
    contents of the cells can be instructed to link to the object on the
    row or the data in the cell.

    If a Column defines an image_class, then it will be assumed that the
    class represents an icon, perhaps as part of a spritesheet, and will
    display it in a <div>. An image_url cannot also be defined.
    """
    SORT_DESCENDING = 0
    SORT_ASCENDING = 1

    def __init__(self, label=None, id=None, detailed_label=None,
                 detailed_label_html=None, field_name=None, db_field=None,
                 image_url=None, image_class=None, image_width=None,
                 image_height=None, image_alt="", shrink=False, expand=False,
                 sortable=False,
                 default_sort_dir=SORT_DESCENDING, link=False,
                 link_func=None, cell_clickable=False, css_class=""):
        assert not (image_class and image_url)

        self.id = id
        self.field_name = field_name
        self.db_field = db_field or field_name
        self.label = label
        self.detailed_label = detailed_label or self.label
        self.detailed_label_html = detailed_label_html or self.detailed_label
        self.image_url = image_url
        self.image_class = image_class
        self.image_width = image_width
        self.image_height = image_height
        self.image_alt = image_alt
        self.shrink = shrink
        self.expand = expand
        self.sortable = sortable
        self.default_sort_dir = default_sort_dir
        self.cell_clickable = False
        self.link = link
        self.link_func = (
            link_func or
            (lambda state, x, y: state.datagrid.link_to_object(state, x, y)))
        self.css_class = css_class

    def setup_state(self, state):
        """Sets up any state that may be needed for the column.

        This is called once per column per datagrid instance.

        By default, no additional state is set up. Subclasses can override
        this to set any variables they may need.
        """
        pass

    def get_sort_field(self, state):
        """Returns the field used for sorting this column.

        By default, this uses the provided db_field.
        """
        return self.db_field

    def get_toggle_url(self, state):
        """
        Returns the URL of the current page with this column's visibility
        toggled.
        """
        columns = [column.id for column in state.datagrid.columns]

        if state.active:
            try:
                columns.remove(self.id)
            except ValueError:
                pass
        else:
            columns.append(self.id)

        url_params = get_url_params_except(state.datagrid.request.GET,
                                           'columns')
        if url_params:
            url_params = url_params + '&'

        return "?%scolumns=%s" % (url_params, ",".join(columns))

    def get_header(self, state):
        """
        Displays a sortable column header.

        The column header will include the current sort indicator, if it
        belongs in the sort list. It will also be made clickable in order
        to modify the sort order appropriately, if sortable.
        """
        datagrid = state.datagrid
        in_sort = False
        sort_direction = self.SORT_DESCENDING
        sort_primary = False
        sort_url = ""
        unsort_url = ""

        if self.sortable:
            sort_list = list(datagrid.sort_list)

            if sort_list:
                rev_column_id = "-%s" % self.id
                new_column_id = self.id
                cur_column_id = ""

                if self.id in sort_list:
                    # This column is currently being sorted in
                    # ascending order.
                    sort_direction = self.SORT_ASCENDING
                    cur_column_id = self.id
                    new_column_id = rev_column_id
                elif rev_column_id in sort_list:
                    # This column is currently being sorted in
                    # descending order.
                    sort_direction = self.SORT_DESCENDING
                    cur_column_id = rev_column_id
                    new_column_id = self.id

                if cur_column_id:
                    in_sort = True
                    sort_primary = (sort_list[0] == cur_column_id)

                    if not sort_primary:
                        # If this is not the primary column, we want to keep
                        # the sort order intact.
                        new_column_id = cur_column_id

                    # Remove this column from the current location in the list
                    # so we can move it to the front of the list.
                    sort_list.remove(cur_column_id)

                # Insert the column name into the beginning of the sort list.
                sort_list.insert(0, new_column_id)
            else:
                # There's no sort list to begin with. Make this column
                # the only entry.
                sort_list = [self.id]

            # We can only support two entries in the sort list, so truncate
            # this.
            del(sort_list[2:])

            url_params = get_url_params_except(
                datagrid.request.GET,
                "sort", "datagrid-id", "gridonly", "columns")
            if url_params:
                url_params = url_params + '&'

            url_prefix = "?%ssort=" % url_params
            unsort_url = url_prefix + ','.join(sort_list[1:])
            sort_url   = url_prefix + ','.join(sort_list)

        ctx = Context({
            'column': self,
            'column_state': state,
            'in_sort': in_sort,
            'sort_ascending': sort_direction == self.SORT_ASCENDING,
            'sort_primary': sort_primary,
            'sort_url': sort_url,
            'unsort_url': unsort_url,
        })

        return mark_safe(datagrid.column_header_template_obj.render(ctx))

    def collect_objects(self, state, object_list):
        """Iterates through the objects and builds a cache of data to display.

        This optimizes the fetching of data in the grid by grabbing all the
        IDs of related objects that will be queried for rendering, loading
        them all at once, and populating the cache.
        """
        id_field = '%s_id' % self.field_name
        ids = set()
        model = None

        for obj in object_list:
            if not hasattr(obj, id_field):
                # This isn't the field type you're looking for.
                return

            ids.add(getattr(obj, id_field))

            if not model:
                field = getattr(obj.__class__, self.field_name).field

                try:
                    model = field.rel.to
                except AttributeError:
                    # No idea what this is. Bail.
                    return

        if model:
            for obj in model.objects.filter(pk__in=ids):
                state.data_cache[obj.pk] = obj

    def render_cell(self, state, obj, render_context):
        """Renders the table cell containing column data."""
        datagrid = state.datagrid
        rendered_data = self.render_data(state, obj)
        url = ''
        css_class = ''

        if self.link:
            try:
                url = self.link_func(state, obj, rendered_data)
            except AttributeError:
                pass

        if self.css_class:
            if six.callable(self.css_class):
                css_class = self.css_class(obj)
            else:
                css_class = self.css_class

        key = "%s:%s:%s:%s" % (state.last, rendered_data, url, css_class)

        if key not in state.cell_render_cache:
            ctx = Context(render_context)
            ctx.update({
                'column': self,
                'column_state': state,
                'css_class': css_class,
                'url': url,
                'data': mark_safe(rendered_data)
            })

            state.cell_render_cache[key] = \
                mark_safe(datagrid.cell_template_obj.render(ctx))

        return state.cell_render_cache[key]

    def render_data(self, state, obj):
        """Renders the column data to a string. This may contain HTML."""
        id_field = '%s_id' % self.field_name

        # Look for this directly so that we don't end up fetching the
        # data for the object.
        if id_field in obj.__dict__:
            pk = obj.__dict__[id_field]

            if pk in state.data_cache:
                return state.data_cache[pk]
            else:
                value = getattr(obj, self.field_name)
                state.data_cache[pk] = escape(value)
                return value
        else:
            # Follow . separators like in the django template library
            value = obj
            for field_name in self.field_name.split('.'):
                if field_name:
                    value = getattr(value, field_name)

                    if six.callable(value):
                        value = value()

            return escape(value)

    def augment_queryset(self, state, queryset):
        """Augments a queryset with new queries.

        Subclasses can override this to extend the queryset to provide
        additional information, usually using queryset.extra(). This must
        return a queryset based on the original queryset.

        This should not restrict the query in any way, or the datagrid may
        not operate properly. It must only add additional data to the
        queryset.
        """
        return queryset


class StatefulColumn(object):
    """A stateful wrapper for a Column instance.

    Columns must be stateless, as they are shared across all instances of
    a particular DataGrid. However, some state is needed for columns, such
    as their widths or active status.

    StatefulColumn wraps a Column instance and provides state storage,
    and also provides a convenient way to call methods on a Column and pass
    the state.

    Attributes owned by the Column can be accessed directly through the
    StatefulColumn.

    Likewise, any functions owned by the Column can be accessed as well.
    The function will be invoked with this StatefulColumn as the first
    parameter passed.
    """
    def __init__(self, datagrid, column):
        self.datagrid = datagrid
        self.column = column
        self.active = False
        self.last = False
        self.width = 0
        self.data_cache = {}
        self.cell_render_cache = {}

        column.setup_state(self)

    @property
    def toggle_url(self):
        """Returns the visibility toggle URL of the column.

        This is a convenience used by templates to call Column.get_toggle_url
        with the current state.
        """
        return self.column.get_toggle_url(self)

    @property
    def header(self):
        """Returns the header of the column.

        This is a convenience used by templates to call Column.get_header
        with the current state.
        """
        return self.column.get_header(self)

    def __getattr__(self, name):
        """Returns an attribute from the parent Column.

        This is called when accessing an attribute not found directly on
        StatefulColumn. The attribute will be fetched from the Column
        (if it exists there).

        In the case of accessing a function, a wrapper will be returned
        that will automatically pass this StatefulColumn instance as the
        first parameter.
        """
        result = getattr(self.column, name)

        if callable(result):
            return lambda *args, **kwargs: result(self, *args, **kwargs)

        return result


class CheckboxColumn(Column):
    """A column that renders a checkbox.

    The is_selectable and is_selected functions can be overridden to
    control whether a checkbox is displayed in a row and whether that
    checkbox is initially checked.

    The checkboxes have a data-object-id attribute that contains the ID of
    the object that row represents. This allows the JavaScript code to
    determine which rows have been checked, and operate on that
    accordingly.

    The checkboxes also have a data-checkbox-name attribute that
    contains the value passed in to the checkbox_name parameter of its
    constructor.
    """
    def __init__(self, checkbox_name='select', shrink=True,
                 show_checkbox_header=True,
                 detailed_label=_('Select Rows'),
                 *args, **kwargs):
        super(CheckboxColumn, self).__init__(
            shrink=shrink,
            label=mark_safe(
                '<input class="datagrid-header-checkbox"'
                ' type="checkbox" data-checkbox-name="%s" />'
                % checkbox_name),
            detailed_label=detailed_label,
            detailed_label_html=mark_safe(
                '<input type="checkbox" /> %s'
                % detailed_label),
            *args, **kwargs)

        self.show_checkbox_header = show_checkbox_header
        self.checkbox_name = checkbox_name

    def render_data(self, state, obj):
        if self.is_selectable(state, obj):
            checked = ''

            if self.is_selected(state, obj):
                checked = 'checked="true"'

            return ('<input type="checkbox" data-object-id="%s" '
                    'data-checkbox-name="%s" %s />'
                    % (obj.pk, escape(self.checkbox_name), checked))
        else:
            return ''

    def is_selectable(self, state, obj):
        """Returns whether an object can be selected.

        If this returns False, no checkbox will be rendered for this item.
        """
        return True

    def is_selected(self, state, obj):
        """Returns whether an object has been selected.

        If this returns True, the checkbox will be checked.
        """
        return False


class DateTimeColumn(Column):
    """A column that renders a date or time."""
    def __init__(self, label, format=None, sortable=True,
                 timezone=pytz.utc, *args, **kwargs):
        super(DateTimeColumn, self).__init__(label, sortable=sortable,
                                             *args, **kwargs)
        self.format = format
        self.timezone = timezone

    def render_data(self, state, obj):
        # If the datetime object is tz aware, conver it to local time
        datetime = getattr(obj, self.field_name)
        if settings.USE_TZ:
            datetime = pytz.utc.normalize(datetime).\
                astimezone(self.timezone)

        return date(datetime, self.format)


class DateTimeSinceColumn(Column):
    """A column that renders a date or time relative to now."""
    def __init__(self, label, sortable=True, timezone=pytz.utc,
                 *args, **kwargs):
        super(DateTimeSinceColumn, self).__init__(label, sortable=sortable,
                                                  *args, **kwargs)

    def render_data(self, state, obj):
        return _("%s ago") % timesince(getattr(obj, self.field_name))


class DataGrid(object):
    """
    A representation of a list of objects, sorted and organized by
    columns. The sort order and column lists can be customized. allowing
    users to view this data however they prefer.

    This is meant to be subclassed for specific uses. The subclasses are
    responsible for defining one or more column types. It can also set
    one or more of the following optional variables:

        * 'title':                  The title of the grid.
        * 'profile_sort_field':     The variable name in the user profile
                                    where the sort order can be loaded and
                                    saved.
        * 'profile_columns_field":  The variable name in the user profile
                                    where the columns list can be loaded and
                                    saved.
        * 'paginate_by':            The number of items to show on each page
                                    of the grid. The default is 50.
        * 'paginate_orphans':       If this number of objects or fewer are
                                    on the last page, it will be rolled into
                                    the previous page. The default is 3.
        * 'page':                   The page to display. If this is not
                                    specified, the 'page' variable passed
                                    in the URL will be used, or 1 if that is
                                    not specified.
        * 'listview_template':      The template used to render the list view.
                                    The default is 'datagrid/listview.html'
        * 'column_header_template': The template used to render each column
                                    header. The default is
                                    'datagrid/column_header.html'
        * 'cell_template':          The template used to render a cell of
                                    data. The default is 'datagrid/cell.html'
        * 'optimize_sorts':         Whether or not to optimize queries when
                                    using multiple sorts. This can offer a
                                    speed improvement, but may need to be
                                    turned off for more advanced querysets
                                    (such as when using extra()).
                                    The default is True.
    """
    _columns = None

    @classmethod
    def add_column(cls, column):
        """Adds a new column for this datagrid.

        This can be used to add columns to a DataGrid subclass after
        the subclass has already been defined.

        The column added must have a unique ID already set.
        """
        cls._populate_columns()

        if not column.id:
            raise KeyError(
                'Custom datagrid columns must have a unique id attribute.')

        if column.id in _column_registry[cls]:
            raise KeyError('"%s" is already a registered column for %s'
                           % (column.id, cls.__name__))

        _column_registry[cls][column.id] = column

    @classmethod
    def remove_column(cls, column):
        """Removes a column from this datagrid.

        This can be used to remove columns previously added through
        add_column().
        """
        cls._populate_columns()

        try:
            del _column_registry[cls][column.id]
        except KeyError:
            raise KeyError('"%s" is not a registered column for %s'
                           % (column.id, cls.__name__))

    @classmethod
    def get_column(cls, column_id):
        """Returns the column with the given ID.

        If not found, this will return None.
        """
        cls._populate_columns()

        return _column_registry[cls].get(column_id)

    @classmethod
    def get_columns(cls):
        """Returns the list of registered columns for this datagrid."""
        cls._populate_columns()

        return six.itervalues(_column_registry[cls])

    @classmethod
    def _populate_columns(cls):
        """Populates the default list of columns for the datagrid.

        The default list contains all columns added in the class definition.
        """
        if cls not in _column_registry:
            _column_registry[cls] = {}

            for key in dir(cls):
                column = getattr(cls, key)

                if isinstance(column, Column):
                    column.id = key

                    if not column.field_name:
                        column.field_name = column.id

                    if not column.db_field:
                        column.db_field = column.field_name

                    cls.add_column(column)

    def __init__(self, request, queryset=None, title="", extra_context={},
                 optimize_sorts=True):
        self.request = request
        self.queryset = queryset
        self.rows = []
        self.columns = []
        self.column_map = {}
        self.id_list = []
        self.paginator = None
        self.page = None
        self.sort_list = None
        self.state_loaded = False
        self.page_num = 0
        self.id = None
        self.extra_context = dict(extra_context)
        self.optimize_sorts = optimize_sorts

        if not hasattr(request, "datagrid_count"):
            request.datagrid_count = 0

        self.id = "datagrid-%s" % request.datagrid_count
        request.datagrid_count += 1

        # Customizable variables
        self.title = title
        self.profile_sort_field = None
        self.profile_columns_field = None
        self.paginate_by = 50
        self.paginate_orphans = 3
        self.listview_template = 'datagrid/listview.html'
        self.column_header_template = 'datagrid/column_header.html'
        self.cell_template = 'datagrid/cell.html'

    @cached_property
    def cell_template_obj(self):
        obj = get_template(self.cell_template)

        if not obj:
            logging.error("Unable to load template '%s' for datagrid "
                          "cell. This may be an installation issue.",
                          self.cell_template,
                          extra={
                              'request': self.request,
                          })

        return obj

    @cached_property
    def column_header_template_obj(self):
        obj = get_template(self.column_header_template)

        if not obj:
            logging.error("Unable to load template '%s' for datagrid "
                          "column headers. This may be an installation "
                          "issue.",
                          self.column_header_template,
                          extra={
                              'request': self.request,
                          })

        return obj

    @property
    def all_columns(self):
        """Returns all columns in the datagrid, sorted by label."""
        return [
            self.get_stateful_column(column)
            for column in sorted(self.get_columns(),
                                 key=lambda x: x.detailed_label)
        ]

    def get_stateful_column(self, column):
        """Returns a StatefulColumn for the given Column instance.

        If one has already been created, it will be returned.
        """
        if column not in self.column_map:
            self.column_map[column] = StatefulColumn(self, column)

        return self.column_map[column]

    def load_state(self, render_context=None):
        """
        Loads the state of the datagrid.

        This will retrieve the user-specified or previously stored
        sorting order and columns list, as well as any state a subclass
        may need.
        """
        if self.state_loaded:
            return

        profile_sort_list = None
        profile_columns_list = None
        profile = None
        profile_dirty = False

        # Get the saved settings for this grid in the profile. These will
        # work as defaults and allow us to determine if we need to save
        # the profile.
        if self.request.user.is_authenticated():
            try:
                profile = self.request.user.get_profile()

                if self.profile_sort_field:
                    profile_sort_list = \
                        getattr(profile, self.profile_sort_field, None)

                if self.profile_columns_field:
                    profile_columns_list = \
                        getattr(profile, self.profile_columns_field, None)
            except SiteProfileNotAvailable:
                pass
            except ObjectDoesNotExist:
                pass


        # Figure out the columns we're going to display
        # We're also going to calculate the column widths based on the
        # shrink and expand values.
        colnames_str = self.request.GET.get('columns', profile_columns_list)

        if colnames_str:
            colnames = colnames_str.split(',')
        else:
            colnames = self.default_columns
            colnames_str = ",".join(colnames)

        expand_columns = []
        normal_columns = []

        for colname in colnames:
            column_def = self.get_column(colname)

            if not column_def:
                # The user specified a column that doesn't exist. Skip it.
                continue

            column = self.get_stateful_column(column_def)
            self.columns.append(column)
            column.active = True

            if column.expand:
                # This column is requesting all remaining space. Save it for
                # later so we can tell how much to give it. Each expanded
                # column will count as two normal columns when calculating
                # the normal sized columns.
                expand_columns.append(column)
            elif column.shrink:
                # Make this as small as possible.
                column.width = 0
            else:
                # We'll divide the column widths equally after we've built
                # up the lists of expanded and normal sized columns.
                normal_columns.append(column)

        self.columns[-1].last = True

        # Try to figure out the column widths for each column.
        # We'll start with the normal sized columns.
        total_pct = 100

        # Each expanded column counts as two normal columns.
        normal_column_width = total_pct / (len(self.columns) +
                                           len(expand_columns))

        for column in normal_columns:
            column.width = normal_column_width
            total_pct -= normal_column_width

        if len(expand_columns) > 0:
            expanded_column_width = total_pct / len(expand_columns)
        else:
            expanded_column_width = 0

        for column in expand_columns:
            column.width = expanded_column_width


        # Now get the sorting order for the columns.
        sort_str = self.request.GET.get('sort', profile_sort_list)

        if sort_str:
            self.sort_list = sort_str.split(',')
        else:
            self.sort_list = self.default_sort
            sort_str = ",".join(self.sort_list)


        # A subclass might have some work to do for loading and saving
        # as well.
        if self.load_extra_state(profile):
            profile_dirty = True


        # Now that we have all that, figure out if we need to save new
        # settings back to the profile.
        if profile:
            if (self.profile_columns_field and
                    colnames_str != profile_columns_list):
                setattr(profile, self.profile_columns_field, colnames_str)
                profile_dirty = True

            if self.profile_sort_field and sort_str != profile_sort_list:
                setattr(profile, self.profile_sort_field, sort_str)
                profile_dirty = True

            if profile_dirty:
                profile.save()

        self.state_loaded = True

        # Fetch the list of objects and have it ready.
        self.precompute_objects(render_context)

    def load_extra_state(self, profile):
        """
        Loads any extra state needed for this grid.

        This is used by subclasses that may have additional data to load
        and save. This should return True if any profile-stored state has
        changed, or False otherwise.
        """
        return False

    def precompute_objects(self, render_context=None):
        """
        Builds the queryset and stores the list of objects for use in
        rendering the datagrid.
        """
        query = self.queryset
        use_select_related = False

        # Generate the actual list of fields we'll be sorting by
        sort_list = []
        for sort_item in self.sort_list:
            if sort_item[0] == "-":
                base_sort_item = sort_item[1:]
                prefix = "-"
            else:
                base_sort_item = sort_item
                prefix = ""

            if sort_item:
                column = self.get_column(base_sort_item)
                if not column:
                    logging.warning('Skipping non-existing sort column "%s" '
                                    'for user "%s".',
                                    base_sort_item, self.request.user.username)
                    continue

                stateful_column = self.get_stateful_column(column)

                if stateful_column:
                    sort_field = stateful_column.get_sort_field()
                    sort_list.append(prefix + sort_field)

                    # Lookups spanning tables require that we query from those
                    # tables. In order to keep things simple, we'll just use
                    # select_related so that we don't have to figure out the
                    # table relationships. We only do this if we have a lookup
                    # spanning tables.
                    if '.' in sort_field:
                        use_select_related = True

        if sort_list:
            query = query.order_by(*sort_list)

        query = self.post_process_queryset(query)

        self.paginator = QuerySetPaginator(query.distinct(), self.paginate_by,
                                           self.paginate_orphans)

        page_num = self.request.GET.get('page', 1)

        # Accept either "last" or a valid page number.
        if page_num == "last":
            page_num = self.paginator.num_pages

        try:
            self.page = self.paginator.page(page_num)
        except InvalidPage:
            raise Http404

        self.id_list = []

        if self.optimize_sorts and len(sort_list) > 0:
            # This can be slow when sorting by multiple columns. If we
            # have multiple items in the sort list, we'll request just the
            # IDs and then fetch the actual details from that.
            self.id_list = list(self.page.object_list.values_list(
                'pk', flat=True))

            # Make sure to unset the order. We can't meaningfully order these
            # results in the query, as what we really want is to keep it in
            # the order specified in id_list, and we certainly don't want
            # the database to do any special ordering (possibly slowing things
            # down). We'll set the order properly in a minute.
            self.page.object_list = self.post_process_queryset(
                self.queryset.model.objects.filter(
                    pk__in=self.id_list).order_by())

        if use_select_related:
            self.page.object_list = \
                self.page.object_list.select_related(depth=1)

        if self.id_list:
            # The database will give us the items in a more or less random
            # order, since it doesn't know to keep it in the order provided by
            # the ID list. This will place the results back in the order we
            # expect.
            index = dict([(id, pos) for (pos, id) in enumerate(self.id_list)])
            object_list = [None] * len(self.id_list)

            for obj in list(self.page.object_list):
                object_list[index[obj.pk]] = obj
        else:
            # Grab the whole list at once. We know it won't be too large,
            # and it will prevent one query per row.
            object_list = list(self.page.object_list)

        for column in self.columns:
            column.collect_objects(object_list)

        if render_context is None:
            render_context = self._build_render_context()

        self.rows = [
            {
                'object': obj,
                'cells': [column.render_cell(obj, render_context)
                          for column in self.columns]
            }
            for obj in object_list if obj is not None
        ]

    def post_process_queryset(self, queryset):
        """Add column-specific data to the queryset.

        Individual columns can define additional joins and extra info to add on
        to the queryset. This handles adding all of those.
        """
        for column in self.columns:
            queryset = column.augment_queryset(queryset)

        return queryset

    def render_listview(self, render_context=None):
        """
        Renders the standard list view of the grid.

        This can be called from templates.
        """
        try:
            if render_context is None:
                render_context = self._build_render_context()

            self.load_state(render_context)

            extra_query = get_url_params_except(self.request.GET, 'page')

            context = {
                'datagrid': self,
                'is_paginated': self.page.has_other_pages(),
                'results_per_page': self.paginate_by,
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
                'page': self.page.number,
                'last_on_page': self.page.end_index(),
                'first_on_page': self.page.start_index(),
                'pages': self.paginator.num_pages,
                'hits': self.paginator.count,
                'page_range': self.paginator.page_range,
                'extra_query': extra_query,
            }

            if self.page.has_next():
                context['next'] = self.page.next_page_number()
            else:
                context['next'] = None

            if self.page.has_previous():
                context['previous'] = self.page.previous_page_number()
            else:
                context['previous'] = None

            context.update(self.extra_context)
            context.update(render_context)

            return mark_safe(render_to_string(self.listview_template,
                                              Context(context)))
        except Exception:
            trace = traceback.format_exc();
            logging.error('Failed to render datagrid:\n%s' % trace,
                          extra={
                              'request': self.request,
                          })
            return mark_safe('<pre>%s</pre>' % trace)

    def render_listview_to_response(self, request=None, render_context=None):
        """
        Renders the listview to a response, preventing caching in the
        process.
        """
        response = HttpResponse(
            six.text_type(self.render_listview(render_context)))
        patch_cache_control(response, no_cache=True, no_store=True, max_age=0,
                            must_revalidate=True)
        return response

    def render_to_response(self, template_name, extra_context={}):
        """
        Renders a template containing this datagrid as a context variable.
        """
        render_context = self._build_render_context()
        self.load_state(render_context)

        # If the caller is requesting just this particular grid, return it.
        if self.request.GET.get('gridonly', False) and \
           self.request.GET.get('datagrid-id', None) == self.id:
            return self.render_listview_to_response(
                render_context=render_context)

        context = {
            'datagrid': self
        }
        context.update(extra_context)
        context.update(render_context)

        return render_to_response(template_name, Context(context))

    def _build_render_context(self):
        """Builds a dictionary containing RequestContext contents.

        A RequestContext can be expensive, so it's best to reuse the
        contents of one when possible. This is not easy with a standard
        RequestContext, but it's possible to build one and then pull out
        the contents into a dictionary.
        """
        request_context = RequestContext(self.request)
        render_context = {}

        for d in request_context:
            render_context.update(d)

        return render_context

    @staticmethod
    def link_to_object(state, obj, value):
        return obj.get_absolute_url()

    @staticmethod
    def link_to_value(state, obj, value):
        return value.get_absolute_url()

########NEW FILE########
__FILENAME__ = datagrid
#
# datagrid.py -- Template tags used in datagrids
#
# Copyright (c) 2008-2009  Christian Hammond
# Copyright (c) 2008-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from django import template


register = template.Library()


# Heavily based on paginator by insin
# http://www.djangosnippets.org/snippets/73/
@register.inclusion_tag('datagrid/paginator.html', takes_context=True)
def paginator(context, adjacent_pages=3):
    """Renders a paginator used for jumping between pages of results."""
    page_nums = range(max(1, context['page'] - adjacent_pages),
                      min(context['pages'], context['page'] + adjacent_pages)
                      + 1)

    return {
        'hits': context['hits'],
        'results_per_page': context['results_per_page'],
        'page': context['page'],
        'pages': context['pages'],
        'page_numbers': page_nums,
        'next': context['next'],
        'previous': context['previous'],
        'has_next': context['has_next'],
        'has_previous': context['has_previous'],
        'show_first': 1 not in page_nums,
        'show_last': context['pages'] not in page_nums,
        'extra_query': context.get('extra_query', None),
    }

########NEW FILE########
__FILENAME__ = tests
#
# tests.py -- Unit tests for classes in djblets.datagrid
#
# Copyright (c) 2007-2008  Christian Hammond
# Copyright (c) 2007-2008  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.http import HttpRequest

from djblets.datagrid.grids import (Column, DataGrid, DateTimeSinceColumn,
                                    StatefulColumn)
from djblets.testing.testcases import TestCase
from djblets.util.dates import get_tz_aware_utcnow


def populate_groups():
    for i in range(1, 100):
        group = Group(name="Group %02d" % i)
        group.save()


class GroupDataGrid(DataGrid):
    objid = Column("ID", link=True, sortable=True, field_name="id")
    name = Column("Group Name", link=True, sortable=True, expand=True)

    def __init__(self, request):
        DataGrid.__init__(self, request, Group.objects.all(), "All Groups")
        self.default_sort = []
        self.default_columns = ['objid', 'name']


class ColumnsTest(TestCase):
    def testDateTimeSinceColumn(self):
        """Testing DateTimeSinceColumn"""
        class DummyObj:
            time = None

        column = DateTimeSinceColumn("Test", field_name='time')
        state = StatefulColumn(None, column)

        if settings.USE_TZ:
            now = get_tz_aware_utcnow()
        else:
            now = datetime.now()

        obj = DummyObj()
        obj.time = now
        self.assertEqual(column.render_data(state, obj), "0\xa0minutes ago")

        obj.time = now - timedelta(days=5)
        self.assertEqual(column.render_data(state, obj), "5\xa0days ago")

        obj.time = now - timedelta(days=7)
        self.assertEqual(column.render_data(state, obj), "1\xa0week ago")


class DataGridTest(TestCase):
    def setUp(self):
        self.old_auth_profile_module = getattr(settings, "AUTH_PROFILE_MODULE",
                                               None)
        settings.AUTH_PROFILE_MODULE = None
        populate_groups()
        self.user = User(username="testuser")
        self.request = HttpRequest()
        self.request.user = self.user
        self.datagrid = GroupDataGrid(self.request)

    def tearDown(self):
        settings.AUTH_PROFILE_MODULE = self.old_auth_profile_module

    def testRender(self):
        """Testing basic datagrid rendering"""
        self.datagrid.render_listview()

    def testRenderToResponse(self):
        """Testing rendering datagrid to HTTPResponse"""
        self.datagrid.render_listview_to_response()

    def testSortAscending(self):
        """Testing datagrids with ascending sort"""
        self.request.GET['sort'] = "name,objid"
        self.datagrid.load_state()

        self.assertEqual(self.datagrid.sort_list, ["name", "objid"])
        self.assertEqual(len(self.datagrid.rows), self.datagrid.paginate_by)
        self.assertEqual(self.datagrid.rows[0]['object'].name, "Group 01")
        self.assertEqual(self.datagrid.rows[1]['object'].name, "Group 02")
        self.assertEqual(self.datagrid.rows[2]['object'].name, "Group 03")

        # Exercise the code paths when rendering
        self.datagrid.render_listview()

    def testSortDescending(self):
        """Testing datagrids with descending sort"""
        self.request.GET['sort'] = "-name"
        self.datagrid.load_state()

        self.assertEqual(self.datagrid.sort_list, ["-name"])
        self.assertEqual(len(self.datagrid.rows), self.datagrid.paginate_by)
        self.assertEqual(self.datagrid.rows[0]['object'].name, "Group 99")
        self.assertEqual(self.datagrid.rows[1]['object'].name, "Group 98")
        self.assertEqual(self.datagrid.rows[2]['object'].name, "Group 97")

        # Exercise the code paths when rendering
        self.datagrid.render_listview()


    def testCustomColumns(self):
        """Testing datagrids with custom column orders"""
        self.request.GET['columns'] = "objid"
        self.datagrid.load_state()

        self.assertEqual(len(self.datagrid.rows), self.datagrid.paginate_by)
        self.assertEqual(len(self.datagrid.rows[0]['cells']), 1)

        # Exercise the code paths when rendering
        self.datagrid.render_listview()

########NEW FILE########
__FILENAME__ = evolution
#
# dbevolution.py -- Helpers for database evolutions
#
# Copyright (c) 2008-2009  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from django_evolution.mutations import BaseMutation


class FakeChangeFieldType(BaseMutation):
    """
    Changes the type of the field to a similar type.
    This is intended only when the new type is really a version of the
    old type, such as a subclass of that Field object. The two fields
    should be compatible or there could be migration issues.
    """
    def __init__(self, model_name, field_name, new_type):
        self.model_name = model_name
        self.field_name = field_name
        self.new_type = new_type

    def __repr__(self):
        return "FakeChangeFieldType('%s', '%s', '%s')" % \
            (self.model_name, self.field_name, self.new_type)

    def simulate(self, app_label, proj_sig):
        app_sig = proj_sig[app_label]
        model_sig = app_sig[self.model_name]
        field_dict = model_sig['fields']
        field_sig = field_dict[self.field_name]

        field_sig['field_type'] = self.new_type

    def mutate(self, app_label, proj_sig):
        # We can just call simulate, since it does the same thing.
        # We're not actually generating SQL, but rather tricking
        # Django Evolution.
        self.simulate(app_label, proj_sig)
        return ""

########NEW FILE########
__FILENAME__ = fields
#
# fields.py -- Model fields.
#
# Copyright (c) 2007-2008  Christian Hammond
# Copyright (c) 2007-2008  David Trowbridge
# Copyright (c) 2008-2013  Beanbag, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from ast import literal_eval
from datetime import datetime
import base64
import json
import logging

from django import forms
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import F
from django.utils import six
from django.utils.encoding import smart_unicode

from djblets.db.validators import validate_json
from djblets.util.dates import get_tz_aware_utcnow


class Base64DecodedValue(str):
    """
    A subclass of string that can be identified by Base64Field, in order
    to prevent double-encoding or double-decoding.
    """
    pass


class Base64FieldCreator(object):
    def __init__(self, field):
        self.field = field

    def __set__(self, obj, value):
        pk_val = obj._get_pk_val(obj.__class__._meta)
        pk_set = pk_val is not None and smart_unicode(pk_val) != ''

        if (isinstance(value, Base64DecodedValue) or not pk_set):
            obj.__dict__[self.field.name] = base64.encodestring(value)
        else:
            obj.__dict__[self.field.name] = value

        setattr(obj, "%s_initted" % self.field.name, True)

    def __get__(self, obj, type=None):
        if obj is None:
            raise AttributeError('Can only be accessed via an instance.')

        value = obj.__dict__[self.field.name]

        if value is None:
            return None
        else:
            return Base64DecodedValue(base64.decodestring(value))


class Base64Field(models.TextField):
    """
    A subclass of TextField that encodes its data as base64 in the database.
    This is useful if you're dealing with unknown encodings and must guarantee
    that no modifications to the text occurs and that you can read/write
    the data in any database with any encoding.
    """
    serialize_to_string = True

    def contribute_to_class(self, cls, name):
        super(Base64Field, self).contribute_to_class(cls, name)
        setattr(cls, self.name, Base64FieldCreator(self))

    def get_db_prep_value(self, value, connection=None, prepared=False):
        if isinstance(value, Base64DecodedValue):
            value = base64.encodestring(value)

        return value

    def save_form_data(self, instance, data):
        setattr(instance, self.name, Base64DecodedValue(data))

    def to_python(self, value):
        if isinstance(value, Base64DecodedValue):
            return value
        else:
            return Base64DecodedValue(base64.decodestring(value))

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)

        if isinstance(value, Base64DecodedValue):
            return base64.encodestring(value)
        else:
            return value


class ModificationTimestampField(models.DateTimeField):
    """
    A subclass of DateTimeField that only auto-updates the timestamp when
    updating an existing object or when the value of the field is None. This
    specialized field is equivalent to DateTimeField's auto_now=True, except
    it allows for custom timestamp values (needed for
    serialization/deserialization).
    """
    def __init__(self, verbose_name=None, name=None, **kwargs):
        kwargs.update({
            'editable': False,
            'blank': True,
        })
        models.DateTimeField.__init__(self, verbose_name, name, **kwargs)

    def pre_save(self, model, add):
        if not add or getattr(model, self.attname) is None:

            if settings.USE_TZ:
                value = get_tz_aware_utcnow()
            else:
                value = datetime.now()

            setattr(model, self.attname, value)
            return value

        return super(ModificationTimestampField, self).pre_save(model, add)

    def get_internal_type(self):
        return "DateTimeField"


class JSONFormField(forms.CharField):
    """Provides a form field for JSON input.

    This is meant to be used by JSONField, and handles the work of
    normalizing a Python data structure back into a serialized JSON
    string for editing.
    """
    def __init__(self, encoder=None, *args, **kwargs):
        super(JSONFormField, self).__init__(*args, **kwargs)
        self.encoder = encoder or DjangoJSONEncoder()

    def prepare_value(self, value):
        if isinstance(value, six.string_types):
            return value
        else:
            return self.encoder.encode(value)


class JSONField(models.TextField):
    """
    A field for storing JSON-encoded data. The data is accessible as standard
    Python data types and is transparently encoded/decoded to/from a JSON
    string in the database.
    """
    serialize_to_string = True
    default_validators = [validate_json]

    def __init__(self, verbose_name=None, name=None,
                 encoder=DjangoJSONEncoder(), **kwargs):
        blank = kwargs.pop('blank', True)
        models.TextField.__init__(self, verbose_name, name, blank=blank,
                                  **kwargs)
        self.encoder = encoder

    def contribute_to_class(self, cls, name):
        def get_json(model_instance):
            return self.dumps(getattr(model_instance, self.attname, None))

        def set_json(model_instance, json):
            setattr(model_instance, self.attname, self.loads(json))

        super(JSONField, self).contribute_to_class(cls, name)

        setattr(cls, "get_%s_json" % self.name, get_json)
        setattr(cls, "set_%s_json" % self.name, set_json)

        models.signals.post_init.connect(self.post_init, sender=cls)

    def pre_save(self, model_instance, add):
        return self.dumps(getattr(model_instance, self.attname, None))

    def post_init(self, instance=None, **kwargs):
        value = self.value_from_object(instance)

        if value:
            value = self.loads(value)
        else:
            value = {}

        setattr(instance, self.attname, value)

    def get_db_prep_save(self, value, *args, **kwargs):
        if not isinstance(value, six.string_types):
            value = self.dumps(value)

        return super(JSONField, self).get_db_prep_save(value, *args, **kwargs)

    def value_to_string(self, obj):
        return self.dumps(self.value_from_object(obj))

    def dumps(self, data):
        if isinstance(data, six.string_types):
            return data
        else:
            return self.encoder.encode(data)

    def loads(self, val):
        try:
            val = json.loads(val, encoding=settings.DEFAULT_CHARSET)

            # XXX We need to investigate why this is happening once we have
            #     a solid repro case.
            if isinstance(val, six.string_types):
                logging.warning("JSONField decode error. Expected dictionary, "
                                "got string for input '%s'" % val)
                # For whatever reason, we may have gotten back
                val = json.loads(val, encoding=settings.DEFAULT_CHARSET)
        except ValueError:
            # There's probably embedded unicode markers (like u'foo') in the
            # string. We have to eval it.
            try:
                val = literal_eval(val)
            except Exception as e:
                logging.error('Failed to eval JSONField data "%r": %s'
                              % (val, e))
                val = {}

            if isinstance(val, six.string_types):
                logging.warning('JSONField decode error after literal_eval: '
                                'Expected dictionary, got string: %r' % val)
                val = {}

        return val

    def formfield(self, **kwargs):
        return super(JSONField, self).formfield(
            form_class=JSONFormField,
            encoder=self.encoder,
            **kwargs)


class CounterField(models.IntegerField):
    """A field that provides atomic counter updating and smart initialization.

    The CounterField makes it easy to atomically update an integer,
    incrementing or decrementing it, without raise conditions or conflicts.
    It can update a single instance at a time, or a batch of objects at once.

    CounterField is useful for storing counts of objects, reducing the number
    of queries performed. This requires that the calling code properly
    increments or decrements at all the right times, of course.

    This takes an optional ``initializer`` parameter that, if provided, can
    be used to auto-populate the field the first time the model instance is
    loaded, perhaps based on querying a number of related objects. The value
    passed to ``initializer`` must be a function taking the model instance
    as a parameter, and must return an integer or None. If it returns None,
    the counter will not be updated or saved.

    The model instance will gain four new functions:

        * ``increment_{field_name}`` - Atomically increment by one.
        * ``decrement_{field_name}`` - Atomically decrement by one.
        * ``reload_{field_name}`` - Reload the value in this instance from the
                                    database.
        * ``reinit_{field_name}`` - Re-initializes the stored field using the
                                    initializer function.

    The field on the class (not the instance) provides two functions for
    batch-updating models:

        * ``increment`` - Takes a queryset and increments this field for
                          each object.
        * ``decrement`` - Takes a queryset and decrements this field for
                          each object.
    """
    @classmethod
    def increment_many(cls, model_instance, values, reload_object=True):
        """Increments several fields on a model instance at once.

        This takes a model instance and dictionary of fields to values,
        and will increment each of those fields by that value.

        If reload_object is True, then the fields on the instance will
        be reloaded to reflect the current values.
        """
        cls._update_values(model_instance, values, reload_object, 1)

    @classmethod
    def decrement_many(cls, model_instance, values, reload_object=True):
        """Decrements several fields on a model instance at once.

        This takes a model instance and dictionary of fields to values,
        and will decrement each of those fields by that value.

        If reload_object is True, then the fields on the instance will
        be reloaded to reflect the current values.
        """
        cls._update_values(model_instance, values, reload_object, -1)

    @classmethod
    def _update_values(cls, model_instance, values, reload_object, multiplier):
        update_values = {}

        for attname, value in six.iteritems(values):
            if value != 0:
                update_values[attname] = F(attname) + value * multiplier

        if update_values:
            queryset = model_instance.__class__.objects.filter(
                pk=model_instance.pk)
            queryset.update(**update_values)

            if reload_object:
                cls._reload_model_instance(model_instance,
                                           six.iterkeys(update_values))

    @classmethod
    def _reload_model_instance(cls, model_instance, attnames):
        """Reloads the value in this instance from the database."""
        q = model_instance.__class__.objects.filter(pk=model_instance.pk)
        values = q.values(*attnames)[0]

        for attname, value in six.iteritems(values):
            setattr(model_instance, attname, value)

    def __init__(self, verbose_name=None, name=None,
                 initializer=None, default=None, **kwargs):
        kwargs.update({
            'blank': True,
            'null': True,
        })

        super(CounterField, self).__init__(verbose_name, name, default=default,
                                           **kwargs)

        self._initializer = initializer
        self._locks = {}

    def increment(self, queryset, increment_by=1):
        """Increments this field on every object in the provided queryset."""
        queryset.update(**{self.attname: F(self.attname) + increment_by})

    def decrement(self, queryset, decrement_by=1):
        """Decrements this field on every object in the provided queryset."""
        queryset.update(**{self.attname: F(self.attname) - decrement_by})

    def contribute_to_class(self, cls, name):
        def _increment(model_instance, reload_object=True, increment_by=1):
            """Increments this field by one."""
            if increment_by != 0:
                self.increment(cls.objects.filter(pk=model_instance.pk),
                               increment_by)

                if reload_object:
                    _reload(model_instance)

        def _decrement(model_instance, reload_object=True, decrement_by=1):
            """Decrements this field by one."""
            if decrement_by != 0:
                self.decrement(cls.objects.filter(pk=model_instance.pk),
                               decrement_by)

                if reload_object:
                    _reload(model_instance)

        def _reload(model_instance):
            """Reloads the value in this instance from the database."""
            self._reload_model_instance(model_instance, [self.attname])

        def _reinit(model_instance):
            """Re-initializes the value in the database from the initializer."""
            if not (model_instance.pk or self._initializer or
                    six.callable(self._initializer)):
                # We don't want to end up defaulting this to 0 if creating a
                # new instance unless an initializer is provided. Instead,
                # we'll want to handle this the next time the object is
                # accessed.
                return

            if self._initializer and six.callable(self._initializer):
                self._locks[model_instance] = 1
                value = self._initializer(model_instance)
                del self._locks[model_instance]
            else:
                value = 0

            if value is not None:
                setattr(model_instance, self.attname, value)

                if model_instance.pk:
                    model_instance.save(update_fields=[self.attname])

        super(CounterField, self).contribute_to_class(cls, name)

        setattr(cls, 'increment_%s' % self.name, _increment)
        setattr(cls, 'decrement_%s' % self.name, _decrement)
        setattr(cls, 'reload_%s' % self.name, _reload)
        setattr(cls, 'reinit_%s' % self.name, _reinit)
        setattr(cls, self.attname, self)

        models.signals.post_init.connect(self._post_init, sender=cls)

    def _post_init(self, instance=None, **kwargs):
        if not instance or instance in self._locks:
            # Prevent the possibility of recursive lookups where this
            # same CounterField on this same instance tries to initialize
            # more than once. In this case, this will have the updated
            # value shortly.
            return

        value = self.value_from_object(instance)

        if value is None:
            reinit = getattr(instance, 'reinit_%s' % self.name)
            reinit()

########NEW FILE########
__FILENAME__ = managers
#
# managers.py -- Managers for Django database models.
#
# Copyright (c) 2007-2013  Beanbag, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#


from __future__ import unicode_literals

from django.db import models, IntegrityError


class ConcurrencyManager(models.Manager):
    """
    A class designed to work around database concurrency issues.
    """
    def get_or_create(self, **kwargs):
        """
        A wrapper around get_or_create that makes a final attempt to get
        the object if the creation fails.

        This helps with race conditions in the database where, between the
        original get() and the create(), another process created the object,
        causing us to fail. We'll then execute a get().

        This is still prone to race conditions, but they're even more rare.
        A delete() would have to happen before the unexpected create() but
        before the get().
        """
        try:
            return super(ConcurrencyManager, self).get_or_create(**kwargs)
        except IntegrityError:
            kwargs.pop('defaults', None)
            return self.get(**kwargs)

########NEW FILE########
__FILENAME__ = query
from __future__ import unicode_literals

from django.db.models.manager import Manager


def get_object_or_none(klass, *args, **kwargs):
    if isinstance(klass, Manager):
        manager = klass
        klass = manager.model
    else:
        manager = klass._default_manager

    try:
        return manager.get(*args, **kwargs)
    except klass.DoesNotExist:
        return None

########NEW FILE########
__FILENAME__ = validators
from __future__ import unicode_literals
import json

from django.core.exceptions import ValidationError
from django.utils import six


def validate_json(value):
    """Validates content going into a JSONField.

    This will raise a ValidationError if the value is a string
    (representing a serialized JSON payload, possibly from the admin UI)
    and cannot be loaded properly.
    """
    if isinstance(value, six.string_types):
        try:
            json.loads(value)
        except ValueError as e:
            raise ValidationError(six.text_type(e), code='invalid')

########NEW FILE########
__FILENAME__ = admin
#
# admin.py -- Admin UI model registration.
#
# Copyright (c) 2010-2011  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from django.contrib import admin

from djblets.extensions.models import RegisteredExtension


class RegisteredExtensionAdmin(admin.ModelAdmin):
    list_display = ('class_name', 'name', 'enabled')


admin.site.register(RegisteredExtension, RegisteredExtensionAdmin)

########NEW FILE########
__FILENAME__ = base
#
# base.py -- Compatibility file for older extensions.
#
# Copyright (c) 2010-2013  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from djblets.extensions.extension import Extension, ExtensionInfo
from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint
from djblets.extensions.manager import ExtensionManager
from djblets.extensions.settings import Settings


__all__ = [
    'Extension', 'ExtensionHook', 'ExtensionHookPoint', 'ExtensionInfo',
    'ExtensionManager', 'Settings',
]

########NEW FILE########
__FILENAME__ = errors
#
# errors.py -- Extension errors.
#
# Copyright (c) 2010-2011  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from django.utils.translation import ugettext as _


class EnablingExtensionError(Exception):
    """An extension could not be enabled."""
    def __init__(self, message, load_error=None, needs_reload=False):
        self.message = message
        self.load_error = load_error
        self.needs_reload = needs_reload


class DisablingExtensionError(Exception):
    """An extension could not be disabled."""
    pass


class InstallExtensionError(Exception):
    """An extension could not be installed."""
    def __init__(self, message, load_error=None):
        self.message = message
        self.load_error = load_error


class InvalidExtensionError(Exception):
    """An extension does not exist."""
    def __init__(self, extension_id):
        super(InvalidExtensionError, self).__init__()
        self.message = _("Cannot find extension with id %s") % extension_id

########NEW FILE########
__FILENAME__ = extension
#
# extension.py -- Base classes for extensions
#
# Copyright (c) 2010-2013  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

import inspect
import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import get_mod_func
from django.utils.encoding import python_2_unicode_compatible

from djblets.extensions.settings import Settings


class JSExtension(object):
    """Base class for a JavaScript extension.

    This can be subclassed to provide the information needed to initialize
    a JavaScript extension.

    The JSExtension subclass is expected to define a :py:attr:`model_class`
    attribute naming its JavaScript counterpart. This would be the variable
    name for the (uninitialized) model for the extension, defined in a
    JavaScript bundle.

    It may also define :py:attr:`apply_to`, which is a list of URL names that
    the extension will be initialized on. If not provided, the extension will
    be initialized on all pages.

    To provide additional data to the model instance, the JSExtension subclass
    can implement :py:meth:`get_model_data` and return a dictionary of data
    to pass.
    """
    model_class = None
    apply_to = None

    def __init__(self, extension):
        self.extension = extension

    def applies_to(self, url_name):
        """Returns whether this extension applies to the given URL name."""
        return self.apply_to is None or url_name in self.apply_to

    def get_model_data(self):
        """Returns model data for the Extension model instance in JavaScript.

        Subclasses can override this to return custom data to pass to
        the extension.
        """
        return {}


class Extension(object):
    """Base class for an extension.

    Extensions must subclass for this class. They'll automatically have
    support for settings, adding hooks, and plugging into the administration
    UI.


    Configuration
    -------------

    If an extension supports configuration in the UI, it should set
    :py:attr:`is_configurable` to True.

    If an extension would like to specify defaults for the settings
    dictionary it should provide a dictionary in :py:attr:`default_settings`.

    If an extension would like a django admin site for modifying the database,
    it should set :py:attr:`has_admin_site` to True.


    Static Media
    ------------

    Extensions should list all other extension names that they require in
    :py:attr:`requirements`.

    Extensions can define static media bundle for Less/CSS and JavaScript
    files, which will automatically be compiled, minified, combined, and
    packaged. An Extension class can define a :py:attr:`css_bundles` and
    a :py:attr:`js_bundles`. Each is a dictionary mapping bundle names
    to bundle dictionary. These mostly follow the Django Pipeline bundle
    format.

    For example:

        class MyExtension(Extension):
            css_bundles = {
                'default': {
                    'source_filenames': ['css/default.css'],
                    'output_filename': 'css/default.min.css',
                },
            }

    ``source_filenames`` is a list of files within the extension module's
    static/ directory that should be bundled together. When testing against
    a developer install with ``DEBUG = True``, these files will be individually
    loaded on the page. However, in a production install, with a properly
    installed extension package, the compiled bundle file will be loaded
    instead, offering a file size and download savings.

    ``output_filename`` is optional. If not specified, the bundle name will
    be used as a base for the filename.

    A bundle name of ``default`` is special. It will be loaded automatically
    on any page supporting extensions (provided the ``load_extensions_js`` and
    ``load_extensions_css`` template tags are used).

    Bundles can also specify an optional ``apply_to`` field, which is a list
    of URL names for pages that the bundle should be automatically loaded on.
    This works like the ``default`` bundle, but for those specific pages.

    Bundles can also be loaded manually within a TemplateHook template
    by using ``{% ext_css_bundle extension "bundle-name" %}`` or
    ``{% ext_js_bundle extension "bundle-name" %}``.


    JavaScript extensions
    ---------------------

    An Extension subclass can define one or more JavaScript extension classes,
    which may apply across all pages or only a subset of them.

    Each is defined as a :py:class:`JSExtension` subclass, and listed in
    Extension's :py:attr:`js_extensions` list. See the documentation on
    JSExtension for more information.

    Any page using the ``init_js_extensions`` template tag will automatically
    initialize any JavaScript extensions appropriate for that page, passing the
    server-stored settings.


    Middleware
    ----------

    If an extension has any middleware, it should set :py:attr:`middleware`
    to a list of class names. This extension's middleware will be loaded after
    any middleware belonging to any extensions in the :py:attr:`requirements`
    list.


    Template Context Processors
    ---------------------------

    Extensions may need to provide additional context variables to templates.
    This can usually be accomplished through a TemplateHook, but sometimes
    it's necessary to provide context variables for other pages (such as
    those controlled by a third-party module).

    To add additional context processors, set :py:attr:`context_processors`
    to a list of class names. They will be added to
    ``settings.TEMPLATE_CONTEXT_PROCESSORS`` automatically.
    """
    metadata = None
    is_configurable = False
    default_settings = {}
    has_admin_site = False
    requirements = []
    resources = []
    apps = []
    context_processors = []
    middleware = []

    css_bundles = {}
    js_bundles = {}

    js_extensions = []

    def __init__(self, extension_manager):
        self.extension_manager = extension_manager
        self.hooks = set()
        self.settings = Settings(self)
        self.admin_site = None
        self.middleware_instances = []

        for middleware_cls in self.middleware:
            # We may be loading in traditional middleware (which doesn't take
            # any parameters in the constructor), or special Extension-aware
            # middleware (which takes an extension parameter). We need to
            # try to introspect and figure out what it is.
            try:
                arg_spec = inspect.getargspec(middleware_cls.__init__)
            except (AttributeError, TypeError):
                # There's no custom __init__ here. It may not exist
                # in the case of an old-style object, in which case we'll
                # get an AttributeError. Or, it may be a new-style object
                # with no custom __init__, in which case we'll get a TypeError.
                arg_spec = None

            if arg_spec and len(arg_spec) >= 2 and arg_spec[1] == 'extension':
                middleware_instance = middleware_cls(self)
            else:
                middleware_instance = middleware_cls()

            self.middleware_instances.append(middleware_instance)

        self.initialize()

    def initialize(self):
        """Initializes the extension.

        Subclasses can override this to provide any custom initialization.
        They do not need to call the parent function, as it does nothing.
        """
        pass

    def shutdown(self):
        """Shuts down the extension.

        By default, this calls shutdown_hooks.

        Subclasses should override this if they need custom shutdown behavior.
        """
        self.shutdown_hooks()

    def shutdown_hooks(self):
        """Shuts down all hooks for the extension."""
        for hook in self.hooks:
            if hook.initialized:
                hook.shutdown()

    def _get_admin_urlconf(self):
        if not hasattr(self, "_admin_urlconf_module"):
            try:
                name = "%s.%s" % (get_mod_func(self.__class__.__module__)[0],
                                  "admin_urls")
                self._admin_urlconf_module = __import__(name, {}, {}, [''])
            except Exception as e:
                raise ImproperlyConfigured(
                    "Error while importing extension's admin URLconf %r: %s" %
                    (name, e))

        return self._admin_urlconf_module
    admin_urlconf = property(_get_admin_urlconf)

    def get_bundle_id(self, name):
        """Returns the ID for a CSS or JavaScript bundle."""
        return '%s-%s' % (self.id, name)


@python_2_unicode_compatible
class ExtensionInfo(object):
    """Information on an extension.

    This class stores the information and metadata on an extension. This
    includes the name, version, author information, where it can be downloaded,
    whether or not it's enabled or installed, and anything else that may be
    in the Python package for the extension.
    """
    def __init__(self, entrypoint, ext_class):
        metadata = {}

        for line in entrypoint.dist.get_metadata_lines("PKG-INFO"):
            key, value = line.split(": ", 1)

            if value != "UNKNOWN":
                metadata[key] = value

        # Extensions will often override "Name" to be something
        # user-presentable, but we sometimes need the package name
        self.package_name = metadata.get('Name')

        if ext_class.metadata is not None:
            metadata.update(ext_class.metadata)

        self.metadata = metadata
        self.name = metadata.get('Name')
        self.version = metadata.get('Version')
        self.summary = metadata.get('Summary')
        self.description = metadata.get('Description')
        self.author = metadata.get('Author')
        self.author_email = metadata.get('Author-email')
        self.license = metadata.get('License')
        self.url = metadata.get('Home-page')
        self.author_url = metadata.get('Author-home-page', self.url)
        self.app_name = '.'.join(ext_class.__module__.split('.')[:-1])
        self.enabled = False
        self.installed = False
        self.is_configurable = ext_class.is_configurable
        self.has_admin_site = ext_class.has_admin_site
        self.installed_htdocs_path = \
            os.path.join(settings.MEDIA_ROOT, 'ext', self.package_name)
        self.installed_static_path = \
            os.path.join(settings.STATIC_ROOT, 'ext', ext_class.id)

    def __str__(self):
        return "%s %s (enabled = %s)" % (self.name, self.version, self.enabled)

########NEW FILE########
__FILENAME__ = forms
#
# forms.py -- Form classes useful for extensions
#
# Copyright (c) 2010-2011  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from djblets.siteconfig.forms import SiteSettingsForm


class SettingsForm(SiteSettingsForm):
    """Settings form for extension configuration.

    A base form for loading/saving settings for an extension. This is meant
    to be overridden by extensions to provide configuration pages. Any fields
    defined by the form will be loaded and saved automatically.
    """
    def __init__(self, extension, *args, **kwargs):
        self.extension = extension
        self.settings = extension.settings

        super(SettingsForm, self).__init__(extension.settings, *args, **kwargs)

########NEW FILE########
__FILENAME__ = hooks
#
# hooks.py -- Common extension hook points.
#
# Copyright (c) 2010-2011  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

import uuid

from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils import six


class ExtensionHook(object):
    """The base class for a hook into some part of the project.

    ExtensionHooks are classes that can hook into an
    :py:class:`ExtensionHookPoint` to provide some level of functionality
    in a project. A project should provide a subclass of ExtensionHook that
    will provide functions for getting data or anything else that's needed,
    and then extensions will subclass that specific ExtensionHook.

    A base ExtensionHook subclass must use :py:class:`ExtensionHookPoint`
    as a metaclass. For example::

        from django.utils import six

        @six.add_metaclass(ExtensionHookPoint)
        class NavigationHook(ExtensionHook):
    """
    def __init__(self, extension):
        self.extension = extension
        self.extension.hooks.add(self)
        self.__class__.add_hook(self)
        self.initialized = True

    def shutdown(self):
        assert self.initialized

        self.__class__.remove_hook(self)
        self.initialized = False


class ExtensionHookPoint(type):
    """A metaclass used for base Extension Hooks.

    Base :py:class:`ExtensionHook` classes use :py:class:`ExtensionHookPoint`
    as a metaclass. This metaclass stores the list of registered hooks that
    an :py:class:`ExtensionHook` will automatically register with.
    """
    def __init__(cls, name, bases, attrs):
        super(ExtensionHookPoint, cls).__init__(name, bases, attrs)

        if not hasattr(cls, "hooks"):
            cls.hooks = []

    def add_hook(cls, hook):
        """Adds an ExtensionHook to the list of active hooks.

        This is called automatically by :py:class:`ExtensionHook`.
        """
        cls.hooks.append(hook)

    def remove_hook(cls, hook):
        """Removes an ExtensionHook from the list of active hooks.

        This is called automatically by :py:class:`ExtensionHook`.
        """
        cls.hooks.remove(hook)


class AppliesToURLMixin(object):
    """A mixin for hooks to allow restricting to certain URLs.

    This provides an applies_to() function for the hook that can be used
    by consumers to determine if the hook should apply to the current page.
    """
    def __init__(self, extension, apply_to=[], *args, **kwargs):
        super(AppliesToURLMixin, self).__init__(extension)
        self.apply_to = apply_to

    def applies_to(self, request):
        """Returns whether or not this hook applies to the page.

        This will determine whether any of the URL names provided in
        ``apply_to`` matches the current requested page.
        """
        return (not self.apply_to or
                request.resolver_match.url_name in self.apply_to)


@six.add_metaclass(ExtensionHookPoint)
class DataGridColumnsHook(ExtensionHook):
    """Adds columns to a datagrid.

    This hook allows an extension to register new columns to any datagrid.
    These columns can be added by the user, rearranged, and sorted, like
    any other column.

    Each column must have an id already set, and it must be unique.
    """
    def __init__(self, extension, datagrid_cls, columns):
        super(DataGridColumnsHook, self).__init__(extension)
        self.datagrid_cls = datagrid_cls
        self.columns = columns

        for column in columns:
            self.datagrid_cls.add_column(column)

    def shutdown(self):
        super(DataGridColumnsHook, self).shutdown()

        for column in self.columns:
            self.datagrid_cls.remove_column(column)


@six.add_metaclass(ExtensionHookPoint)
class URLHook(ExtensionHook):
    """Custom URL hook.

    A hook that installs custom URLs. These URLs reside in a project-specified
    parent URL.
    """
    def __init__(self, extension, patterns):
        super(URLHook, self).__init__(extension)
        self.patterns = patterns
        self.dynamic_urls = self.extension.extension_manager.dynamic_urls
        self.dynamic_urls.add_patterns(patterns)

    def shutdown(self):
        super(URLHook, self).shutdown()

        self.dynamic_urls.remove_patterns(self.patterns)


@six.add_metaclass(ExtensionHookPoint)
class SignalHook(ExtensionHook):
    """Connects to a Django signal.

    This will handle connecting to a signal, calling the specified callback
    when fired. It will disconnect from the signal when the extension is
    disabled.
    """
    def __init__(self, extension, signal, callback, sender=None):
        super(SignalHook, self).__init__(extension)

        self.signal = signal
        self.callback = callback
        self.dispatch_uid = uuid.uuid1()

        signal.connect(callback, sender=sender, weak=False,
                       dispatch_uid=self.dispatch_uid)

    def shutdown(self):
        super(SignalHook, self).shutdown()

        self.signal.disconnect(dispatch_uid=self.dispatch_uid)


@six.add_metaclass(ExtensionHookPoint)
class TemplateHook(AppliesToURLMixin, ExtensionHook):
    """Custom templates hook.

    A hook that renders a template at hook points defined in another template.
    """
    _by_name = {}

    def __init__(self, extension, name, template_name=None, apply_to=[],
                 extra_context={}):
        super(TemplateHook, self).__init__(extension, apply_to=apply_to)
        self.name = name
        self.template_name = template_name
        self.extra_context = extra_context

        if not name in self.__class__._by_name:
            self.__class__._by_name[name] = [self]
        else:
            self.__class__._by_name[name].append(self)

    def shutdown(self):
        super(TemplateHook, self).shutdown()

        self.__class__._by_name[self.name].remove(self)

    def render_to_string(self, request, context):
        """Renders the content for the hook.

        By default, this renders the provided template name to a string
        and returns it.
        """
        context_data = {
            'extension': self.extension,
        }
        context_data.update(self.get_extra_context(request, context))
        context_data.update(self.extra_context)

        # Note that context.update implies a push().
        context.update(context_data)

        s = render_to_string(self.template_name,
                             RequestContext(request, context))

        context.pop()

        return s

    def get_extra_context(self, request, context):
        """Returns extra context for the hook.

        Subclasses can override this to provide additional context
        dynamically beyond what's passed in to the constructor.

        By default, an empty dictionary is returned.
        """
        return {}

    @classmethod
    def by_name(cls, name):
        return cls._by_name.get(name, [])

########NEW FILE########
__FILENAME__ = loaders
#
# loaders.py -- Loaders for extension data.
#
# Copyright (c) 2010-2011  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from django.template import TemplateDoesNotExist
from pkg_resources import _manager as manager

from djblets.extensions.manager import get_extension_managers


def load_template_source(template_name, template_dirs=None):
    """Loads templates from enabled extensions."""
    if manager:
        resource = "templates/" + template_name

        for extmgr in get_extension_managers():
            for ext in extmgr.get_enabled_extensions():
                package = ext.info.app_name

                try:
                    return (manager.resource_string(package, resource),
                            'extension:%s:%s ' % (package, resource))
                except Exception:
                    pass

    raise TemplateDoesNotExist(template_name)

load_template_source.is_usable = manager is not None

########NEW FILE########
__FILENAME__ = manager
#
# manager.py -- Extension management and registration.
#
# Copyright (c) 2010-2013  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

import datetime
import errno
import logging
import os
import pkg_resources
import shutil
import sys
import tempfile
import threading
import time
import traceback

from django.conf import settings
from django.conf.urls import patterns, include
from django.contrib.admin.sites import AdminSite
from django.core.cache import cache
from django.core.files import locks
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.management.color import no_style
from django.core.urlresolvers import reverse
from django.db.models import loading
from django.template.loader import template_source_loaders
from django.utils import six
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule
from django.utils.six.moves import cStringIO as StringIO
from django.utils.translation import ugettext as _
from django_evolution.management.commands.evolve import Command as Evolution
from setuptools.command import easy_install

from djblets.cache.backend import make_cache_key
from djblets.extensions.errors import (EnablingExtensionError,
                                       InstallExtensionError,
                                       InvalidExtensionError)
from djblets.extensions.extension import ExtensionInfo
from djblets.extensions.models import RegisteredExtension
from djblets.extensions.signals import (extension_initialized,
                                        extension_uninitialized)
from djblets.urls.resolvers import DynamicURLResolver


class SettingListWrapper(object):
    """Wraps list-based settings to provide management and ref counting.

    This can be used instead of direct access to a list in Django
    settings to ensure items are never added more than once, and only
    removed when nothing needs it anymore.

    Each item in the list is ref-counted. The initial items from the
    setting are populated and start with a ref count of 1. Adding items
    will increment a ref count for the item, adding it to the list
    if it doesn't already exist. Removing items reduces the ref count,
    removing when it hits 0.
    """
    def __init__(self, setting_name, display_name):
        self.setting_name = setting_name
        self.display_name = display_name
        self.ref_counts = {}

        self.setting = getattr(settings, setting_name)

        if isinstance(self.setting, tuple):
            self.setting = list(self.setting)
            setattr(settings, setting_name, self.setting)

        for item in self.setting:
            self.ref_counts[item] = 1

    def add(self, item):
        """Adds an item to the setting.

        If the item is already in the list, it won't be added again.
        The ref count will just be incremented.

        If it's a new item, it will be added to the list with a ref count
        of 1.
        """
        if item in self.ref_counts:
            self.ref_counts[item] += 1
        else:
            assert item not in self.setting, \
                   ("Extension's %s %s is already in settings.%s, with "
                    "ref count of 0."
                    % (self.display_name, item, self.setting_name))

            self.ref_counts[item] = 1
            self.setting.append(item)

    def add_list(self, items):
        """Adds a list of items to the setting."""
        for item in items:
            self.add(item)

    def remove(self, item):
        """Removes an item from the setting.

        The item's ref count will be decremented. If it hits 0, it will
        be removed from the list.
        """
        assert item in self.ref_counts, \
               ("Extension's %s %s is missing a ref count."
                % (self.display_name, item))
        assert item in self.setting, \
               ("Extension's %s %s is not in settings.%s"
                % (self.display_name, item, self.setting_name))

        if self.ref_counts[item] == 1:
            del self.ref_counts[item]
            self.setting.remove(item)
        else:
            self.ref_counts[item] -= 1

    def remove_list(self, items):
        """Removes a list of items from the setting."""
        for item in items:
            try:
                self.remove(item)
            except ValueError:
                # This may have already been removed. Ignore the error.
                pass


class ExtensionManager(object):
    """A manager for all extensions.

    ExtensionManager manages the extensions available to a project. It can
    scan for new extensions, enable or disable them, determine dependencies,
    install into the database, and uninstall.

    An installed extension is one that has been installed by a Python package
    on the system.

    A registered extension is one that has been installed and information then
    placed in the database. This happens automatically after scanning for
    an installed extension. The registration data stores whether or not it's
    enabled, and stores various pieces of information on the extension.

    An enabled extension is one that is actively enabled and hooked into the
    project.

    Each project should have one ExtensionManager.
    """
    VERSION_SETTINGS_KEY = '_extension_installed_version'

    def __init__(self, key):
        self.key = key

        self.pkg_resources = None

        self._extension_classes = {}
        self._extension_instances = {}
        self._load_errors = {}

        # State synchronization
        self._sync_key = make_cache_key('extensionmgr:%s:gen' % key)
        self._last_sync_gen = None
        self._load_lock = threading.Lock()

        self.dynamic_urls = DynamicURLResolver()

        # Extension middleware instances, ordered by dependencies.
        self.middleware = []

        # Wrap the INSTALLED_APPS and TEMPLATE_CONTEXT_PROCESSORS settings
        # to allow for ref-counted add/remove operations.
        self._installed_apps_setting = SettingListWrapper(
            'INSTALLED_APPS',
            'installed app')
        self._context_processors_setting = SettingListWrapper(
            'TEMPLATE_CONTEXT_PROCESSORS',
            'context processor')

        _extension_managers.append(self)

    def get_url_patterns(self):
        """Returns the URL patterns for the Extension Manager.

        This should be included in the root urlpatterns for the site.
        """
        return patterns('', self.dynamic_urls)

    def is_expired(self):
        """Returns whether or not the extension state is possibly expired.

        Extension state covers the lists of extensions and each extension's
        configuration. It can expire if the state synchronization value
        falls out of cache or is changed.

        Each ExtensionManager has its own state synchronization cache key.
        """
        sync_gen = cache.get(self._sync_key)

        return (sync_gen is None or
                (type(sync_gen) is int and sync_gen != self._last_sync_gen))

    def clear_sync_cache(self):
        cache.delete(self._sync_key)

    def get_absolute_url(self):
        return reverse("djblets.extensions.views.extension_list")

    def get_can_disable_extension(self, registered_extension):
        extension_id = registered_extension.class_name

        return (registered_extension.extension_class is not None and
                (self.get_enabled_extension(extension_id) is not None or
                 extension_id in self._load_errors))

    def get_can_enable_extension(self, registered_extension):
        return (registered_extension.extension_class is not None and
                self.get_enabled_extension(
                    registered_extension.class_name) is None)

    def get_enabled_extension(self, extension_id):
        """Returns an enabled extension with the given ID."""
        if extension_id in self._extension_instances:
            return self._extension_instances[extension_id]

        return None

    def get_enabled_extensions(self):
        """Returns the list of all enabled extensions."""
        return list(self._extension_instances.values())

    def get_installed_extensions(self):
        """Returns the list of all installed extensions."""
        return list(self._extension_classes.values())

    def get_installed_extension(self, extension_id):
        """Returns the installed extension with the given ID."""
        if extension_id not in self._extension_classes:
            raise InvalidExtensionError(extension_id)

        return self._extension_classes[extension_id]

    def get_dependent_extensions(self, dependency_extension_id):
        """Returns a list of all extensions required by an extension."""
        if dependency_extension_id not in self._extension_instances:
            raise InvalidExtensionError(dependency_extension_id)

        dependency = self.get_installed_extension(dependency_extension_id)
        result = []

        for extension_id, extension in six.iteritems(self._extension_classes):
            if extension_id == dependency_extension_id:
                continue

            for ext_requirement in extension.info.requirements:
                if ext_requirement == dependency:
                    result.append(extension_id)

        return result

    def enable_extension(self, extension_id):
        """Enables an extension.

        Enabling an extension will install any data files the extension
        may need, any tables in the database, perform any necessary
        database migrations, and then will start up the extension.
        """
        if extension_id in self._extension_instances:
            # It's already enabled.
            return

        if extension_id not in self._extension_classes:
            if extension_id in self._load_errors:
                raise EnablingExtensionError(
                    _('There was an error loading this extension'),
                    self._load_errors[extension_id],
                    needs_reload=True)

            raise InvalidExtensionError(extension_id)

        ext_class = self._extension_classes[extension_id]

        # Enable extension dependencies
        for requirement_id in ext_class.requirements:
            self.enable_extension(requirement_id)

        extension = self._init_extension(ext_class)

        ext_class.registration.enabled = True
        ext_class.registration.save()

        self._clear_template_cache()
        self._bump_sync_gen()
        self._recalculate_middleware()

        return extension

    def disable_extension(self, extension_id):
        """Disables an extension.

        Disabling an extension will remove any data files the extension
        installed and then shut down the extension and all of its hooks.

        It will not delete any data from the database.
        """
        has_load_error = extension_id in self._load_errors

        if not has_load_error:
            if extension_id not in self._extension_instances:
                # It's not enabled.
                return

            if extension_id not in self._extension_classes:
                raise InvalidExtensionError(extension_id)

            extension = self._extension_instances[extension_id]

            for dependent_id in self.get_dependent_extensions(extension_id):
                self.disable_extension(dependent_id)

            self._uninstall_extension(extension)
            self._uninit_extension(extension)
            self._unregister_static_bundles(extension)

            registration = extension.registration
        else:
            del self._load_errors[extension_id]

            if extension_id in self._extension_classes:
                # The class was loadable, so it just couldn't be instantiated.
                # Update the registration on the class.
                ext_class = self._extension_classes[extension_id]
                registration = ext_class.registration
            else:
                registration = RegisteredExtension.objects.get(
                    class_name=extension_id)

        registration.enabled = False
        registration.save(update_fields=['enabled'])

        self._clear_template_cache()
        self._bump_sync_gen()
        self._recalculate_middleware()

    def install_extension(self, install_url, package_name):
        """Install an extension from a remote source.

        Installs an extension from a remote URL containing the
        extension egg. Installation may fail if a malformed install_url
        or package_name is passed, which will cause an InstallExtensionError
        exception to be raised. It is also assumed that the extension is not
        already installed.
        """

        try:
            easy_install.main(["-U", install_url])

            # Update the entry points.
            dist = pkg_resources.get_distribution(package_name)
            dist.activate()
            pkg_resources.working_set.add(dist)
        except pkg_resources.DistributionNotFound:
            raise InstallExtensionError(_("Invalid package name."))
        except SystemError:
            raise InstallExtensionError(
                _('Installation failed (probably malformed URL).'))

        # Refresh the extension manager.
        self.load(True)

    def load(self, full_reload=False):
        """
        Loads all known extensions, initializing any that are recorded as
        being enabled.

        If this is called a second time, it will refresh the list of
        extensions, adding new ones and removing deleted ones.

        If full_reload is passed, all state is cleared and we reload all
        extensions and state from scratch.
        """
        with self._load_lock:
            self._load_extensions(full_reload)

    def _load_extensions(self, full_reload=False):
        if full_reload:
            # We're reloading everything, so nuke all the cached copies.
            self._clear_extensions()
            self._clear_template_cache()
            self._load_errors = {}

        # Preload all the RegisteredExtension objects
        registered_extensions = {}
        for registered_ext in RegisteredExtension.objects.all():
            registered_extensions[registered_ext.class_name] = registered_ext

        found_extensions = {}
        found_registrations = {}
        registrations_to_fetch = []
        find_registrations = False
        extensions_changed = False

        for entrypoint in self._entrypoint_iterator():
            registered_ext = None

            try:
                ext_class = entrypoint.load()
            except Exception as e:
                logging.error("Error loading extension %s: %s" %
                              (entrypoint.name, e))
                extension_id = '%s.%s' % (entrypoint.module_name,
                                          '.'.join(entrypoint.attrs))
                self._store_load_error(extension_id, e)
                continue

            # A class's extension ID is its class name. We want to
            # make this easier for users to access by giving it an 'id'
            # variable, which will be accessible both on the class and on
            # instances.
            class_name = ext_class.id = "%s.%s" % (ext_class.__module__,
                                                   ext_class.__name__)
            self._extension_classes[class_name] = ext_class
            found_extensions[class_name] = ext_class

            # Don't override the info if we've previously loaded this
            # class.
            if not getattr(ext_class, 'info', None):
                ext_class.info = ExtensionInfo(entrypoint, ext_class)

            registered_ext = registered_extensions.get(class_name)

            if registered_ext:
                found_registrations[class_name] = registered_ext

                if not hasattr(ext_class, 'registration'):
                    find_registrations = True
            else:
                registrations_to_fetch.append(class_name)
                find_registrations = True

        if find_registrations:
            if registrations_to_fetch:
                stored_registrations = list(
                    RegisteredExtension.objects.filter(
                        class_name__in=registrations_to_fetch))

                # Go through the list of registrations found in the database
                # and mark them as found for later processing.
                for registered_ext in stored_registrations:
                    class_name = registered_ext.class_name
                    found_registrations[class_name] = registered_ext

            # Go through each registration we still need and couldn't find,
            # and create an entry in the database. These are going to be
            # newly discovered extensions.
            for class_name in registrations_to_fetch:
                if class_name not in found_registrations:
                    registered_ext, is_new = \
                        RegisteredExtension.objects.get_or_create(
                            class_name=class_name,
                            defaults={
                                'name': entrypoint.dist.project_name
                            })

                    found_registrations[class_name] = registered_ext

        # Now we have all the RegisteredExtension instances. Go through
        # and initialize each of them.
        for class_name, registered_ext in six.iteritems(found_registrations):
            ext_class = found_extensions[class_name]
            ext_class.registration = registered_ext

            if (ext_class.registration.enabled and
                ext_class.id not in self._extension_instances):

                try:
                    self._init_extension(ext_class)
                except EnablingExtensionError:
                    # When in debug mode, we want this error to be noticed.
                    # However, in production, it shouldn't break the whole
                    # server, so continue on.
                    if not settings.DEBUG:
                        continue

                extensions_changed = True

        # At this point, if we're reloading, it's possible that the user
        # has removed some extensions. Go through and remove any that we
        # can no longer find.
        #
        # While we're at it, since we're at a point where we've seen all
        # extensions, we can set the ExtensionInfo.requirements for
        # each extension
        for class_name, ext_class in six.iteritems(self._extension_classes):
            if class_name not in found_extensions:
                if class_name in self._extension_instances:
                    self.disable_extension(class_name)

                del self._extension_classes[class_name]
                extensions_changed = True
            else:
                ext_class.info.requirements = \
                    [self.get_installed_extension(requirement_id)
                     for requirement_id in ext_class.requirements]

        # Add the sync generation if it doesn't already exist.
        self._add_new_sync_gen()
        self._last_sync_gen = cache.get(self._sync_key)
        settings.AJAX_SERIAL = self._last_sync_gen

        if extensions_changed:
            self._recalculate_middleware()

    def _clear_extensions(self):
        """Clear the entire list of known extensions.

        This will bring the ExtensionManager back to the state where
        it doesn't yet know about any extensions, requiring a re-load.
        """
        for extension in self.get_enabled_extensions():
            self._uninit_extension(extension)

        for extension_class in self.get_installed_extensions():
            if hasattr(extension_class, 'info'):
                delattr(extension_class, 'info')

            if hasattr(extension_class, 'registration'):
                delattr(extension_class, 'registration')

        self._extension_classes = {}
        self._extension_instances = {}

    def _clear_template_cache(self):
        """Clears the Django template caches."""
        if template_source_loaders:
            for template_loader in template_source_loaders:
                if hasattr(template_loader, 'reset'):
                    template_loader.reset()

    def _init_extension(self, ext_class):
        """Initializes an extension.

        This will register the extension, install any URLs that it may need,
        and make it available in Django's list of apps. It will then notify
        that the extension has been initialized.
        """
        extension_id = ext_class.id

        assert extension_id not in self._extension_instances

        try:
            extension = ext_class(extension_manager=self)
        except Exception as e:
            logging.error('Unable to initialize extension %s: %s'
                          % (ext_class, e), exc_info=1)
            error_details = self._store_load_error(extension_id, e)
            raise EnablingExtensionError(
                _('Error initializing extension: %s') % e,
                error_details)

        if extension_id in self._load_errors:
            del self._load_errors[extension_id]

        self._extension_instances[extension_id] = extension

        if extension.has_admin_site:
            self._init_admin_site(extension)

        # Installing the urls must occur after _init_admin_site(). The urls
        # for the admin site will not be generated until it is called.
        self._install_admin_urls(extension)

        self._register_static_bundles(extension)

        extension.info.installed = extension.registration.installed
        extension.info.enabled = True
        self._add_to_installed_apps(extension)
        self._context_processors_setting.add_list(extension.context_processors)
        self._reset_templatetags_cache()
        ext_class.instance = extension

        try:
            self._install_extension_media(ext_class)
        except InstallExtensionError as e:
            raise EnablingExtensionError(e.message, e.load_error)

        extension_initialized.send(self, ext_class=extension)

        return extension

    def _uninit_extension(self, extension):
        """Uninitializes the extension.

        This will shut down the extension, remove any URLs, remove it from
        Django's list of apps, and send a signal saying the extension was
        shut down.
        """
        extension.shutdown()

        if hasattr(extension, "admin_urlpatterns"):
            self.dynamic_urls.remove_patterns(
                extension.admin_urlpatterns)

        if hasattr(extension, "admin_site_urlpatterns"):
            self.dynamic_urls.remove_patterns(
                extension.admin_site_urlpatterns)

        if hasattr(extension, 'admin_site'):
            del extension.admin_site

        self._context_processors_setting.remove_list(
            extension.context_processors)
        self._remove_from_installed_apps(extension)
        self._reset_templatetags_cache()
        extension.info.enabled = False
        extension_uninitialized.send(self, ext_class=extension)

        del self._extension_instances[extension.id]
        extension.__class__.instance = None

    def _store_load_error(self, extension_id, err):
        """Stores and returns a load error for the extension ID."""
        error_details = '%s\n\n%s' % (err, traceback.format_exc())
        self._load_errors[extension_id] = error_details

        return error_details

    def _reset_templatetags_cache(self):
        """Clears the Django templatetags_modules cache."""
        # We'll import templatetags_modules here because
        # we want the most recent copy of templatetags_modules
        from django.template.base import (get_templatetags_modules,
                                          templatetags_modules)
        # Wipe out the contents
        del(templatetags_modules[:])

        # And reload the cache
        get_templatetags_modules()

    def _install_extension_media(self, ext_class):
        """Installs extension static media.

        This method is a wrapper around _install_extension_media_internal to
        check whether we actually need to install extension media, and avoid
        contention among multiple threads/processes when doing so.

        We need to install extension media if it hasn't been installed yet,
        or if the version of the extension media that we installed is different
        from the current version of the extension.
        """
        lockfile = os.path.join(tempfile.gettempdir(), ext_class.id + '.lock')
        extension = ext_class.instance

        old_version = extension.settings.get(self.VERSION_SETTINGS_KEY)
        cur_version = ext_class.info.version
        if ext_class.registration.installed and old_version == cur_version:
            # Nothing to do
            return

        if not old_version:
            logging.debug('Installing extension media for %s', ext_class.info)
        else:
            logging.debug('Reinstalling extension media for %s because '
                          'version changed from %s',
                          ext_class.info, old_version)

        while old_version != cur_version:
            with open(lockfile, 'w') as f:
                try:
                    locks.lock(f, locks.LOCK_EX)
                except IOError as e:
                    if e.errno == errno.EINTR:
                        # Sleep for one second, then try again
                        time.sleep(1)
                        extension.settings.load()
                        old_version = extension.settings.get(
                            self.VERSION_SETTINGS_KEY)
                        continue
                    else:
                        raise e

                self._install_extension_media_internal(ext_class)
                extension.settings.set(self.VERSION_SETTINGS_KEY, cur_version)
                extension.settings.save()
                old_version = cur_version

                locks.unlock(f)

        os.unlink(lockfile)

    def _install_extension_media_internal(self, ext_class):
        """Installs extension data.

        Performs any installation necessary for an extension.

        If the extension has a legacy htdocs/ directory for static media
        files, they will be installed into MEDIA_ROOT/ext/, and a warning
        will be logged.

        If the extension has a modern static/ directory, they will be
        installed into STATIC_ROOT/ext/.
        """
        ext_htdocs_path = ext_class.info.installed_htdocs_path
        ext_htdocs_path_exists = os.path.exists(ext_htdocs_path)

        if ext_htdocs_path_exists:
            # First, get rid of the old htdocs contents, so we can start
            # fresh.
            shutil.rmtree(ext_htdocs_path, ignore_errors=True)

        if pkg_resources.resource_exists(ext_class.__module__, 'htdocs'):
            # This is an older extension that doesn't use the static file
            # support. Log a deprecation notice and then install the files.
            logging.warning('The %s extension uses the deprecated "htdocs" '
                            'directory for static files. It should be updated '
                            'to use a "static" directory instead.'
                            % ext_class.info.name)

            extracted_path = \
                pkg_resources.resource_filename(ext_class.__module__, 'htdocs')

            shutil.copytree(extracted_path, ext_htdocs_path, symlinks=True)

        # We only want to install static media on a non-DEBUG install.
        # Otherwise, we run the risk of creating a new 'static' directory and
        # causing Django to look up all static files (not just from
        # extensions) from there instead of from their source locations.
        if not settings.DEBUG:
            ext_static_path = ext_class.info.installed_static_path
            ext_static_path_exists = os.path.exists(ext_static_path)

            if ext_static_path_exists:
                # Also get rid of the old static contents.
                shutil.rmtree(ext_static_path, ignore_errors=True)

            if pkg_resources.resource_exists(ext_class.__module__, 'static'):
                extracted_path = \
                    pkg_resources.resource_filename(ext_class.__module__,
                                                    'static')

                shutil.copytree(extracted_path, ext_static_path, symlinks=True)

        # Mark the extension as installed
        ext_class.registration.installed = True
        ext_class.registration.save()

        # Now let's build any tables that this extension might need
        self._add_to_installed_apps(ext_class)

        # Call syncdb to create the new tables
        loading.cache.loaded = False
        call_command('syncdb', verbosity=0, interactive=False)

        # Run evolve to do any table modification
        try:
            stream = StringIO()
            evolution = Evolution()
            evolution.style = no_style()
            evolution.execute(verbosity=0, interactive=False,
                              execute=True, hint=False,
                              compile_sql=False, purge=False,
                              database=False,
                              stdout=stream, stderr=stream)

            output = stream.getvalue()

            if output:
                logging.info('Evolved extension models for %s: %s',
                             ext_class.id, stream.read())

            stream.close()
        except CommandError as e:
            # Something went wrong while running django-evolution, so
            # grab the output.  We can't raise right away because we
            # still need to put stdout back the way it was
            output = stream.getvalue()
            stream.close()

            logging.error('Error evolving extension models: %s: %s',
                          e, output, exc_info=1)

            load_error = self._store_load_error(ext_class.id, output)
            raise InstallExtensionError(six.text_type(e), load_error)

        # Remove this again, since we only needed it for syncdb and
        # evolve.  _init_extension will add it again later in
        # the install.
        self._remove_from_installed_apps(ext_class)

        # Mark the extension as installed
        ext_class.registration.installed = True
        ext_class.registration.save()

    def _uninstall_extension(self, extension):
        """Uninstalls extension data.

        Performs any uninstallation necessary for an extension.

        This will uninstall the contents of MEDIA_ROOT/ext/ and
        STATIC_ROOT/ext/.
        """
        extension.settings.set(self.VERSION_SETTINGS_KEY, None)
        extension.settings.save()

        extension.registration.installed = False
        extension.registration.save()

        for path in (extension.info.installed_htdocs_path,
                     extension.info.installed_static_path):
            if os.path.exists(path):
                shutil.rmtree(path, ignore_errors=True)

    def _install_admin_urls(self, extension):
        """Installs administration URLs.

        This provides URLs for configuring an extension, plus any additional
        admin urlpatterns that the extension provides.
        """
        prefix = self.get_absolute_url()

        if hasattr(settings, 'SITE_ROOT'):
            prefix = prefix[len(settings.SITE_ROOT):]

        # Note that we're adding to the resolve list on the root of the
        # install, and prefixing it with the admin extensions path.
        # The reason we're not just making this a child of our extensions
        # urlconf is that everything in there gets passed an
        # extension_manager variable, and we don't want to force extensions
        # to handle this.

        if extension.is_configurable:
            urlconf = extension.admin_urlconf
            if hasattr(urlconf, "urlpatterns"):
                extension.admin_urlpatterns = patterns('',
                    (r'^%s%s/config/' % (prefix, extension.id),
                     include(urlconf.__name__)))

                self.dynamic_urls.add_patterns(
                    extension.admin_urlpatterns)

        if getattr(extension, 'admin_site', None):
            extension.admin_site_urlpatterns = patterns('',
                (r'^%s%s/db/' % (prefix, extension.id),
                include(extension.admin_site.urls)))

            self.dynamic_urls.add_patterns(
                extension.admin_site_urlpatterns)

    def _register_static_bundles(self, extension):
        """Registers the extension's static bundles with Pipeline.

        Each static bundle will appear as an entry in Pipeline. The
        bundle name and filenames will be changed to include the extension
        ID for the static file lookups.
        """
        def _add_prefix(filename):
            return 'ext/%s/%s' % (extension.id, filename)

        def _add_bundles(pipeline_bundles, extension_bundles, default_dir,
                         ext):
            for name, bundle in six.iteritems(extension_bundles):
                new_bundle = bundle.copy()

                new_bundle['source_filenames'] = [
                    _add_prefix(filename)
                    for filename in bundle.get('source_filenames', [])
                ]

                new_bundle['output_filename'] = _add_prefix(bundle.get(
                    'output_filename',
                    '%s/%s.min%s' % (default_dir, name, ext)))

                pipeline_bundles[extension.get_bundle_id(name)] = new_bundle

        if not hasattr(settings, 'PIPELINE_CSS'):
            settings.PIPELINE_CSS = {}

        if not hasattr(settings, 'PIPELINE_JS'):
            settings.PIPELINE_JS = {}

        _add_bundles(settings.PIPELINE_CSS, extension.css_bundles,
                     'css', '.css')
        _add_bundles(settings.PIPELINE_JS, extension.js_bundles,
                     'js', '.js')

    def _unregister_static_bundles(self, extension):
        """Unregisters the extension's static bundles from Pipeline.

        Every static bundle previously registered will be removed.
        """
        def _remove_bundles(pipeline_bundles, extension_bundles):
            for name, bundle in six.iteritems(extension_bundles):
                try:
                    del pipeline_bundles[extension.get_bundle_id(name)]
                except KeyError:
                    pass

        if hasattr(settings, 'PIPELINE_CSS'):
            _remove_bundles(settings.PIPELINE_CSS, extension.css_bundles)

        if hasattr(settings, 'PIPELINE_JS'):
            _remove_bundles(settings.PIPELINE_JS, extension.js_bundles)

    def _init_admin_site(self, extension):
        """Creates and initializes an admin site for an extension.

        This creates the admin site and imports the extensions admin
        module to register the models.

        The url patterns for the admin site are generated in
        _install_admin_urls().
        """
        extension.admin_site = AdminSite(extension.info.app_name)

        # Import the extension's admin module.
        try:
            admin_module_name = '%s.admin' % extension.info.app_name
            if admin_module_name in sys.modules:
                # If the extension has been loaded previously and
                # we are re-enabling it, we must reload the module.
                # Just importing again will not cause the ModelAdmins
                # to be registered.
                reload(sys.modules[admin_module_name])
            else:
                import_module(admin_module_name)
        except ImportError:
            mod = import_module(extension.info.app_name)

            # Decide whether to bubble up this error. If the app just
            # doesn't have an admin module, we can ignore the error
            # attempting to import it, otherwise we want it to bubble up.
            if module_has_submodule(mod, 'admin'):
                raise ImportError(
                    "Importing admin module for extension %s failed"
                    % extension.info.app_name)

    def _add_to_installed_apps(self, extension):
        self._installed_apps_setting.add_list(
            extension.apps or [extension.info.app_name])

    def _remove_from_installed_apps(self, extension):
        self._installed_apps_setting.remove_list(
            extension.apps or [extension.info.app_name])

    def _entrypoint_iterator(self):
        return pkg_resources.iter_entry_points(self.key)

    def _bump_sync_gen(self):
        """Bumps the synchronization generation value.

        If there's an existing synchronization generation in cache,
        increment it. Otherwise, start fresh with a new one.

        This will also set ``settings.AJAX_SERIAL``, which will guarantee any
        cached objects that depends on templates and use this serial number
        will be invalidated, allowing TemplateHooks and other hooks
        to be re-run.
        """
        try:
            self._last_sync_gen = cache.incr(self._sync_key)
        except ValueError:
            self._last_sync_gen = self._add_new_sync_gen()

        settings.AJAX_SERIAL = self._last_sync_gen

    def _add_new_sync_gen(self):
        val = time.mktime(datetime.datetime.now().timetuple())
        return cache.add(self._sync_key, int(val))

    def _recalculate_middleware(self):
        """Recalculates the list of middleware."""
        self.middleware = []
        done = set()

        for e in self.get_enabled_extensions():
            self.middleware.extend(self._get_extension_middleware(e, done))

    def _get_extension_middleware(self, extension, done):
        """Returns a list of middleware for 'extension' and its dependencies.

        This is a recursive utility function initially called by
        _recalculate_middleware() that ensures that middleware for all
        dependencies are inserted before that of the given extension.  It
        also ensures that each extension's middleware is inserted only once.
        """
        middleware = []

        if extension in done:
            return middleware

        done.add(extension)

        for req in extension.requirements:
            e = self.get_enabled_extension(req)

            if e:
                middleware.extend(self._get_extension_middleware(e, done))

        middleware.extend(extension.middleware_instances)
        return middleware


_extension_managers = []


def get_extension_managers():
    return _extension_managers

########NEW FILE########
__FILENAME__ = middleware
#
# middleware.py -- Middleware for extensions.
#
# Copyright (c) 2010-2011  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

import threading

from djblets.extensions.manager import get_extension_managers


class ExtensionsMiddleware(object):
    """Middleware to manage extension lifecycles and data."""
    def __init__(self, *args, **kwargs):
        super(ExtensionsMiddleware, self).__init__(*args, **kwargs)

        self._lock = threading.Lock()

    def process_request(self, request):
        self._check_expired()

    def process_view(self, request, view, args, kwargs):
        request._djblets_extensions_kwargs = kwargs

    def _check_expired(self):
        """Checks each ExtensionManager for expired extension state.

        When the list of extensions on an ExtensionManager changes, or when
        the configuration of an extension changes, any other threads/processes
        holding onto extensions and configuration will go stale. This function
        will check each of those to see if they need to re-load their
        state.

        This is meant to be called before every HTTP request.
        """
        for extension_manager in get_extension_managers():
            # We're going to check the expiration, and then only lock if it's
            # expired. Following that, we'll check again.
            #
            # We do this in order to prevent locking unnecessarily, which could
            # impact performance or cause a problem if a thread is stuck.
            #
            # We're checking the expiration twice to prevent every blocked
            # thread from making its own attempt to reload the extensions once
            # the first thread holding the lock finishes the reload.
            if extension_manager.is_expired():
                with self._lock:
                    # Check again, since another thread may have already
                    # reloaded.
                    if extension_manager.is_expired():
                        extension_manager.load(full_reload=True)


class ExtensionsMiddlewareRunner(object):
    """Middleware to execute middleware from extensions.

    The process_*() methods iterate over all extensions' middleware, calling
    the given method if it exists. The semantics of how Django executes each
    method are preserved.

    This middleware should be loaded after the main extension middleware
    (djblets.extensions.middleware.ExtensionsMiddleware). It's probably
    a good idea to have it be at the very end so that everything else in the
    core that needs to be initialized is done before any extension's
    middleware is run.
    """

    def process_request(self, request):
        return self._call_until('process_request', False, request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        return self._call_until('process_view', False, request, view_func,
                                view_args, view_kwargs)

    def process_template_response(self, request, response):
        return self._call_chain_response('process_template_response', request,
                                         response)

    def process_response(self, request, response):
        return self._call_chain_response('process_response', request, response)

    def process_exception(self, request, exception):
        return self._call_until('process_exception', True, request, exception)

    def _call_until(self, func_name, reverse, *args, **kwargs):
        """Call extension middleware until a truthy value is returned."""
        r = None

        for f in self._middleware_funcs(func_name, reverse):
            r = f(*args, **kwargs)

            if r:
                break

        return r

    def _call_chain_response(self, func_name, request, response):
        """Call extension middleware, passing response from one to the next."""
        for f in self._middleware_funcs(func_name, True):
            response = f(request, response)

        return response

    def _middleware_funcs(self, func_name, reverse=False):
        """Generator yielding the given middleware function for all extensions.

        If an extension's middleware does not implement 'func_name', it is
        skipped.
        """
        middleware = []

        for mgr in get_extension_managers():
            middleware.extend(mgr.middleware)

        if reverse:
            middleware.reverse()

        for m in middleware:
            f = getattr(m, func_name, None)

            if f:
                yield f

########NEW FILE########
__FILENAME__ = models
#
# models.py -- Extension models.
#
# Copyright (c) 2010-2011  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from djblets.db.fields import JSONField
from djblets.extensions.errors import InvalidExtensionError


@python_2_unicode_compatible
class RegisteredExtension(models.Model):
    """Extension registration info.

    An extension that was both installed and enabled at least once. This
    may contain settings for the extension.

    This does not contain full information for the extension, such as the
    author or description. That is provided by the Extension object itself.
    """
    class_name = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=32)
    enabled = models.BooleanField(default=False)
    installed = models.BooleanField(default=False)
    settings = JSONField()

    def __str__(self):
        return self.name

    def get_extension_class(self):
        """Retrieves the python object for the extensions class."""
        if not hasattr(self, '_extension_class'):
            cls = None

            try:
                # Import the function here to avoid a mutual
                # dependency.
                from djblets.extensions.manager import get_extension_managers

                for manager in get_extension_managers():
                    try:
                        cls = manager.get_installed_extension(self.class_name)
                        break
                    except InvalidExtensionError:
                        continue
            except:
                return None

            self._extension_class = cls

        return self._extension_class

    extension_class = property(get_extension_class)

########NEW FILE########
__FILENAME__ = packaging
from __future__ import unicode_literals

import inspect
import os
import sys

import pkg_resources
from django.core.management import call_command
from django.utils import six
from setuptools.command.build_py import build_py
from setuptools import Command


class BuildStaticFiles(Command):
    """Builds static files for the extension.

    This will build the static media files used by the extension. JavaScript
    bundles will be minified and versioned. CSS bundles will be processed
    through lesscss (if using .less files), minified and versioned.

    This must be subclassed by the project offering the extension support.
    The subclass must provide the extension_entrypoint_group and
    django_settings_module parameters.

    extension_entrypoint_group is the group name that entry points register
    into.

    django_settings_module is the Python module path for the project's
    settings module, for use in the DJANGO_SETTINGS_MODULE environment
    variable.
    """
    description = 'Build static media files'
    extension_entrypoint_group = None
    django_settings_module = None

    user_options = [
        (b'remove-source-files', None, 'remove source files from the package'),
    ]
    boolean_options = [b'remove-source-files']

    def initialize_options(self):
        self.build_lib = None
        self.remove_source_files = False

    def finalize_options(self):
        self.set_undefined_options('build', ('build_lib', 'build_lib'))

    def get_lessc_global_vars(self):
        """Returns a dictionary of LessCSS global variables and their values.

        This can be implemented by subclasses to provide global variables for
        .less files for processing.

        By default, this defines two variables: `STATIC_ROOT` and `DEBUG`.

        `STATIC_ROOT` is set to an empty string. This will effectively cause
        any imports using `@{STATIC_ROOT}` to look up in the include path.
        Projects using less.js for the runtime can then define `STATIC_ROOT` to
        their standard static URL, ensuring lookups work for development and
        packaged extensions.

        `DEBUG` is set to false. Runtimes using less.js can set this to
        settings.DEBUG for templates. This can be useful for LessCSS guards.

        This requires LessCSS 1.5.1 or higher.
        """
        return {
            'DEBUG': False,
            'STATIC_ROOT': '',
        }

    def get_lessc_include_path(self):
        """Returns the include path for LessCSS imports.

        By default, this will include the parent directory of every path in
        STATICFILES_DIRS, plus the static directory of the extension.
        """
        from django.conf import settings

        less_include = set()

        for staticfile_dir in settings.STATICFILES_DIRS:
            if isinstance(staticfile_dir, tuple):
                staticfile_dir = staticfile_dir[1]

            less_include.add(os.path.dirname(staticfile_dir))

        return less_include

    def run(self):
        from django.conf import settings

        # Prepare to import the project's settings file, and the extension
        # modules that are being shipped, so we can scan for the bundled
        # media.
        old_settings_module = os.environ.get('DJANGO_SETTINGS_MODULE')
        os.environ['DJANGO_SETTINGS_MODULE'] = self.django_settings_module
        cwd = os.getcwd()
        sys.path = [
            os.path.join(cwd, package_name)
            for package_name in self.distribution.packages
        ] + sys.path

        # Set up the common Django settings for the builds.
        settings.STATICFILES_FINDERS = (
            'djblets.extensions.staticfiles.PackagingFinder',
        )
        settings.STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'
        settings.INSTALLED_APPS = [
            'django.contrib.staticfiles',
        ]
        settings.CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            },
        }

        # Load the entry points this package is providing, so we'll know
        # which extensions to scan.
        entrypoints = pkg_resources.EntryPoint.parse_map(
            self.distribution.entry_points,
            dist=self.distribution)

        extension_entrypoints = \
            entrypoints.get(self.extension_entrypoint_group)
        assert extension_entrypoints, 'No extension entry points were defined.'

        # Begin building pipeline bundles for each of the bundles defined
        # in the extension.
        for ep_name, entrypoint in six.iteritems(extension_entrypoints):
            try:
                extension = entrypoint.load(require=False)
            except ImportError:
                sys.stderr.write(
                    'Error loading the extension for entry point %s\n'
                    % ep_name)
                raise

            self._build_static_media(extension)

        # Restore the environment, so we don't possibly interfere with
        # anything else.
        if old_settings_module is not None:
            os.environ['DJANGO_SETTINGS_MODULE'] = old_settings_module

        sys.path = sys.path[len(self.distribution.packages):]

    def _build_static_media(self, extension):
        from django.conf import settings

        pipeline_js = {}
        pipeline_css = {}

        self._add_bundle(pipeline_js, extension.js_bundles, 'js', '.js')
        self._add_bundle(pipeline_css, extension.css_bundles, 'css', '.css')

        # Get the location of the static/ directory within the module in the
        # source tree. We're going to use it to look up static files for
        # input, and as a relative path within the module for the output.
        module_dir = os.path.dirname(inspect.getmodule(extension).__file__)
        static_dir = os.path.join(module_dir, 'static')

        if not os.path.exists(static_dir):
            # This extension doesn't define any static files.
            return

        from djblets.extensions.staticfiles import PackagingFinder
        PackagingFinder.extension_static_dir = static_dir

        settings.STATICFILES_DIRS = list(settings.STATICFILES_DIRS) + [
            PackagingFinder.extension_static_dir
        ]

        # Register the include path and any global variables used for
        # building .less files.
        settings.PIPELINE_LESS_ARGUMENTS = ' '.join(
            [
                '--include-path=%s'
                    % os.path.pathsep.join(self.get_lessc_include_path())
            ] + [
                '--global-var="%s=%s"'
                    % (key, self._serialize_lessc_value(value))
                for key, value in six.iteritems(self.get_lessc_global_vars())
            ]
        )

        settings.PIPELINE_JS = pipeline_js
        settings.PIPELINE_CSS = pipeline_css
        settings.PIPELINE_ENABLED = True
        settings.PIPELINE_STORAGE = \
            'djblets.extensions.staticfiles.PackagingStorage'
        settings.STATIC_ROOT = \
            os.path.join(self.build_lib,
                         os.path.relpath(os.path.join(module_dir, 'static')))

        # Due to how Pipeline copies and stores its settings, we actually
        # have to copy over some of these, as they'll be from the original
        # loaded settings.
        from pipeline.conf import settings as pipeline_settings

        for key in six.iterkeys(pipeline_settings.__dict__):
            if hasattr(settings, key):
                setattr(pipeline_settings, key, getattr(settings, key))

        # Collect and process all static media files.
        call_command('collectstatic', interactive=False, verbosity=2)

        if self.remove_source_files:
            self._remove_source_files(
                pipeline_css, os.path.join(settings.STATIC_ROOT, 'css'))
            self._remove_source_files(
                pipeline_js, os.path.join(settings.STATIC_ROOT, 'js'))

    def _add_bundle(self, pipeline_bundles, extension_bundles, default_dir,
                    ext):
        for name, bundle in six.iteritems(extension_bundles):
            if 'output_filename' not in bundle:
                bundle['output_filename'] = \
                    '%s/%s.min%s' % (default_dir, name, ext)

            pipeline_bundles[name] = bundle

    def _remove_source_files(self, pipeline_bundles, media_build_dir):
        """Removes all source files, leaving only built bundles."""
        for root, dirs, files in os.walk(media_build_dir, topdown=False):
            for name in files:
                full_path = os.path.join(root, name)

                # A valid file will be represented as one of:
                #
                #     (bundle_name, 'min', stamp, ext)
                #     (bundle_name, 'min', ext)
                #
                # We keep both the pre-stamped and post-stamped versions so
                # that Django's CachedFilesStorage can generate and cache
                # the stamp from the contents of the non-stamped file.
                name_parts = name.split('.')

                if (len(name_parts) < 3 or
                    name_parts[0] not in pipeline_bundles or
                    name_parts[1] != 'min'):
                    # This doesn't appear to be a file representing a bundle,
                    # so we should get rid of it.
                    os.unlink(os.path.join(root, name))

            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except:
                    # The directory is probably not empty yet.
                    pass

    def _serialize_lessc_value(self, value):
        if isinstance(value, six.text_type):
            return '"%s"' % value
        elif isinstance(value, bool):
            if value:
                return 'true'
            else:
                return 'false'
        elif isinstance(value, int):
            return '%d' % value
        else:
            raise TypeError('%r is not a valid lessc global variable value'
                            % value)


class BuildPy(build_py):
    def run(self):
        self.run_command('build_static_files')
        build_py.run(self)


def build_extension_cmdclass(build_static_files_cls):
    """Builds a cmdclass to pass to setup.

    This is passed a subclass of BuildStaticFiles, and returns something
    that can be passed to setup().
    """
    return {
        'build_static_files': build_static_files_cls,
        'build_py': BuildPy,
    }

########NEW FILE########
__FILENAME__ = resources
from __future__ import unicode_literals

from django.conf.urls import patterns, include
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.utils import six

from djblets.extensions.errors import (DisablingExtensionError,
                                       EnablingExtensionError,
                                       InvalidExtensionError)
from djblets.extensions.models import RegisteredExtension
from djblets.urls.resolvers import DynamicURLResolver
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_permission_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST,
                                   ENABLE_EXTENSION_FAILED,
                                   DISABLE_EXTENSION_FAILED,
                                   PERMISSION_DENIED)
from djblets.webapi.resources import WebAPIResource


class ExtensionResource(WebAPIResource):
    """Provides information on installed extensions."""
    model = RegisteredExtension
    fields = {
        'author': {
            'type': str,
            'description': 'The author of the extension.',
        },
        'author_url': {
            'type': str,
            'description': "The author's website.",
        },
        'can_disable': {
            'type': bool,
            'description': 'Whether or not the extension can be disabled.',
        },
        'can_enable': {
            'type': bool,
            'description': 'Whether or not the extension can be enabled.',
        },
        'class_name': {
            'type': str,
            'description': 'The class name for the extension.',
        },
        'enabled': {
            'type': bool,
            'description': 'Whether or not the extension is enabled.',
        },
        'installed': {
            'type': bool,
            'description': 'Whether or not the extension is installed.',
        },
        'loadable': {
            'type': bool,
            'description': 'Whether or not the extension is currently '
                           'loadable. An extension may be installed but '
                           'missing or may be broken due to a bug.',
        },
        'load_error': {
            'type': str,
            'description': 'If the extension could not be loaded, this will '
                           'contain any errors captured while trying to load.',
        },
        'name': {
            'type': str,
            'description': 'The name of the extension.',
        },
        'summary': {
            'type': str,
            'description': "A summary of the extension's functionality.",
        },
        'version': {
            'type': str,
            'description': 'The installed version of the extension.',
        },
    }
    name = 'extension'
    plural_name = 'extensions'
    uri_object_key = 'extension_name'
    uri_object_key_regex = r'[.A-Za-z0-9_-]+'
    model_object_key = 'class_name'

    allowed_methods = ('GET', 'PUT')

    def __init__(self, extension_manager):
        super(ExtensionResource, self).__init__()
        self._extension_manager = extension_manager
        self._dynamic_patterns = DynamicURLResolver()
        self._resource_url_patterns_map = {}

        # We want ExtensionResource to notice when extensions are
        # initialized or uninitialized, so connect some methods to
        # those signals.
        from djblets.extensions.signals import (extension_initialized,
                                                extension_uninitialized)
        extension_initialized.connect(self._on_extension_initialized)
        extension_uninitialized.connect(self._on_extension_uninitialized)

    def serialize_author_field(self, extension, *args, **kwargs):
        if extension.extension_class is None:
            return None

        return extension.extension_class.info.author

    def serialize_author_url_field(self, extension, *args, **kwargs):
        if extension.extension_class is None:
            return None

        return extension.extension_class.info.author_url

    def serialize_can_disable_field(self, extension, *args, **kwargs):
        return self._extension_manager.get_can_disable_extension(extension)

    def serialize_can_enable_field(self, extension, *args, **kwargs):
        return self._extension_manager.get_can_enable_extension(extension)

    def serialize_loadable_field(self, extension, *args, **kwargs):
        return (extension.extension_class is not None and
                extension.class_name not in self._extension_manager._load_errors)

    def serialize_load_error_field(self, extension, *args, **kwargs):
        return self._extension_manager._load_errors.get(extension.class_name)

    def serialize_name_field(self, extension, *args, **kwargs):
        if extension.extension_class is None:
            return extension.name
        else:
            return extension.extension_class.info.name

    def serialize_summary_field(self, extension, *args, **kwargs):
        if extension.extension_class is None:
            return None

        return extension.extension_class.info.summary

    def serialize_version_field(self, extension, *args, **kwargs):
        if extension.extension_class is None:
            return None

        return extension.extension_class.info.version

    @webapi_response_errors(DOES_NOT_EXIST, PERMISSION_DENIED)
    @webapi_login_required
    def get_list(self, request, *args, **kwargs):
        """Returns the list of known extensions.

        Each extension in the list has been installed, but may not be
        enabled.
        """
        return WebAPIResource.get_list(self, request, *args, **kwargs)

    def get_links(self, resources=[], obj=None, request=None, *args, **kwargs):
        links = super(ExtensionResource, self).get_links(
            resources, obj, request=request, *args, **kwargs)

        if request and obj:
            admin_base_href = '%s%s' % (
                request.build_absolute_uri(reverse('extension-list')),
                obj.class_name)

            extension_cls = obj.extension_class

            if extension_cls:
                extension_info = extension_cls.info

                if extension_info.is_configurable:
                    links['admin-configure'] = {
                        'method': 'GET',
                        'href': '%s/config/' % admin_base_href,
                    }

                if extension_info.has_admin_site:
                    links['admin-database'] = {
                        'method': 'GET',
                        'href': '%s/db/' % admin_base_href,
                    }

        return links

    @webapi_login_required
    @webapi_permission_required('extensions.change_registeredextension')
    @webapi_response_errors(PERMISSION_DENIED, DOES_NOT_EXIST,
                            ENABLE_EXTENSION_FAILED, DISABLE_EXTENSION_FAILED)
    @webapi_request_fields(
        required={
            'enabled': {
                'type': bool,
                'description': 'Whether or not to make the extension active.'
            },
        },
    )
    def update(self, request, *args, **kwargs):
        """Updates the state of the extension.

        If ``enabled`` is true, then the extension will be enabled, if it is
        not already. If false, it will be disabled.
        """
        # Try to find the registered extension
        try:
            registered_extension = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        extension_id = registered_extension.class_name

        if kwargs.get('enabled'):
            try:
                self._extension_manager.enable_extension(extension_id)
            except EnablingExtensionError as e:
                err = ENABLE_EXTENSION_FAILED.with_message(six.text_type(e))

                return err, {
                    'load_error': e.load_error,
                    'needs_reload': e.needs_reload,
                }
            except InvalidExtensionError as e:
                raise
                return ENABLE_EXTENSION_FAILED.with_message(six.text_type(e))
        else:
            try:
                self._extension_manager.disable_extension(extension_id)
            except (DisablingExtensionError, InvalidExtensionError) as e:
                return DISABLE_EXTENSION_FAILED.with_message(six.text_type(e))

        # Refetch extension, since the ExtensionManager may have changed
        # the model.
        registered_extension = self.get_object(request, *args, **kwargs)

        return 200, {
            self.item_result_key: registered_extension
        }

    def get_url_patterns(self):
        # We want extension resource URLs to be dynamically modifiable,
        # so we override get_url_patterns in order to capture and store
        # a reference to the url_patterns at /api/extensions/.
        url_patterns = super(ExtensionResource, self).get_url_patterns()
        url_patterns += patterns('', self._dynamic_patterns)

        return url_patterns

    def get_related_links(self, obj=None, request=None, *args, **kwargs):
        """Returns links to the resources provided by the extension.

        The result should be a dictionary of link names to a dictionary of
        information. The information should contain:

        * 'method' - The HTTP method
        * 'href' - The URL
        * 'title' - The title of the link (optional)
        * 'resource' - The WebAPIResource instance
        * 'list-resource' - True if this links to a list resource (optional)
        """
        links = {}

        if obj and obj.enabled:
            extension = obj.get_extension_class()

            if not extension:
                return links

            for resource in extension.resources:
                links[resource.name_plural] = {
                    'method': 'GET',
                    'href': "%s%s/" % (
                        self.get_href(obj, request, *args, **kwargs),
                        resource.uri_name),
                    'resource': resource,
                    'list-resource': not resource.singleton,
                }

        return links

    def _attach_extension_resources(self, extension):
        """
        Attaches an extension's resources to /api/extensions/{extension.id}/.
        """

        # Bail out if there are no resources to attach
        if not extension.resources:
            return

        if extension in self._resource_url_patterns_map:
            # This extension already had its urlpatterns
            # mapped and attached.  Nothing to do here.
            return

        # We're going to store references to the URL patterns
        # that are generated for this extension's resources.
        self._resource_url_patterns_map[extension] = []

        # For each resource, generate the URLs
        for resource in extension.resources:
            self._resource_url_patterns_map[extension].extend(patterns('',
                (r'^%s/%s/' % (extension.id, resource.uri_name),
                 include(resource.get_url_patterns()))))

        self._dynamic_patterns.add_patterns(
            self._resource_url_patterns_map[extension])

    def _unattach_extension_resources(self, extension):
        """
        Unattaches an extension's resources from
        /api/extensions/{extension.id}/.
        """

        # Bail out if there are no resources for this extension
        if not extension.resources:
            return

        # If this extension has never had its resource URLs
        # generated, then we don't have anything to worry
        # about.
        if not extension in self._resource_url_patterns_map:
            return

        # Remove the URL patterns
        self._dynamic_patterns.remove_patterns(
            self._resource_url_patterns_map[extension])

        # Delete the URL patterns so that we can regenerate
        # them when the extension is re-enabled.  This is to
        # avoid caching incorrect URL patterns during extension
        # development, when extension resources are likely to
        # change.
        del self._resource_url_patterns_map[extension]

    def _on_extension_initialized(self, sender, ext_class=None, **kwargs):
        """
        Signal handler that notices when an extension has been initialized.
        """
        self._attach_extension_resources(ext_class)

    def _on_extension_uninitialized(self, sender, ext_class=None, **kwargs):
        """
        Signal handler that notices and reacts when an extension
        has been uninitialized.
        """
        self._unattach_extension_resources(ext_class)

########NEW FILE########
__FILENAME__ = settings
#
# settings.py -- Settings storage operations for extensions.
#
# Copyright (c) 2010-2013  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from django.utils.translation import ugettext as _

from djblets.extensions.signals import settings_saved


class Settings(dict):
    """
    Settings data for an extension. This is a glorified dictionary that
    acts as a proxy for the extension's stored settings in the database.

    Callers must call save() when they want to make the settings persistent.

    If a key is not found in the dictionary, extension.default_settings
    will be checked as well.
    """
    def __init__(self, extension):
        dict.__init__(self)
        self.extension = extension
        self.load()

    def __getitem__(self, key):
        """Retrieve an item from the dictionary.

        This will attempt to return a default value from
        extension.default_settings if the setting has not
        been set.
        """
        if super(Settings, self).__contains__(key):
            return super(Settings, self).__getitem__(key)

        if key in self.extension.default_settings:
            return self.extension.default_settings[key]

        raise KeyError(
            _('The settings key "%(key)s" was not found in extension %(ext)s')
            % {
                'key': key,
                'ext': self.extension.id
            })

    def __contains__(self, key):
        """Indicate if the setting is present.

        If the key is not present in the settings dictionary
        check the default settings as well.
        """
        if super(Settings, self).__contains__(key):
            return True

        return key in self.extension.default_settings

    def get(self, key, default=None):
        """Returns a setting.

        This will return the setting's stored value, or its default value if
        unset.

        If the key isn't a valid setting, the provided default will be
        returned instead.
        """
        # dict.get doesn't call __getitem__ internally, and instead looks up
        # straight from the internal dictionary data. So, we need to handle it
        # ourselves in order to support defaults through __getitem__.
        try:
            return self[key]
        except KeyError:
            return default

    def set(self, key, value):
        """Sets a setting's value.

        This is equivalent to setting the value through standard dictionary
        attribute storage.
        """
        self[key] = value

    def load(self):
        """Loads the settings from the database."""
        try:
            self.update(self.extension.registration.settings)
        except ValueError:
            # The settings in the database are invalid. We'll have to discard
            # it. Note that this should never happen unless the user
            # hand-modifies the entries and breaks something.
            pass

    def save(self):
        """Saves all current settings to the database."""
        registration = self.extension.registration
        registration.settings = dict(self)
        registration.save()

        settings_saved.send(sender=self.extension)

        # Make sure others are aware that the configuration changed.
        self.extension.extension_manager._bump_sync_gen()

########NEW FILE########
__FILENAME__ = signals
#
# signals.py -- Extension-related signals.
#
# Copyright (c) 2010-2011  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from django.dispatch import Signal


extension_initialized = Signal(providing_args=["ext_class"])
extension_uninitialized = Signal(providing_args=["ext_class"])
settings_saved = Signal()

########NEW FILE########
__FILENAME__ = staticfiles
from __future__ import unicode_literals

import os

from django.contrib.staticfiles.finders import BaseFinder, FileSystemFinder
from django.contrib.staticfiles.utils import get_files
from django.core.files.storage import FileSystemStorage
from pipeline.storage import PipelineFinderStorage
from pkg_resources import resource_filename

from djblets.extensions.manager import get_extension_managers


class ExtensionStaticStorage(FileSystemStorage):
    """Provides access to static files owned by an extension.

    This is a thin wrapper around FileSystemStorage that determines the
    path to the static directory within the extension. It will only operate
    on files within that path.
    """
    source_dir = 'static'
    prefix = None

    def __init__(self, extension, *args, **kwargs):
        location = resource_filename(extension.__class__.__module__,
                                     self.source_dir)

        super(ExtensionStaticStorage, self).__init__(location, *args, **kwargs)


class ExtensionFinder(BaseFinder):
    """Finds static files within enabled extensions.

    ExtensionFinder can list static files belonging to an extension, and
    find the path of a static file, given an extension ID and path.

    All static files are expected to be in the form of
    ``ext/<extension_id>/<path>``, where ``extension_id`` is the ID given to
    an extension (based on the full class path for the extension class).

    An extension is only valid if it has a "static" directory.
    """
    storage_class = ExtensionStaticStorage

    def __init__(self, *args, **kwargs):
        super(ExtensionFinder, self).__init__(*args, **kwargs)

        self.storages = {}
        self.ignored_extensions = set()

    def list(self, ignore_patterns):
        """Lists static files within all enabled extensions."""
        for extension_manager in get_extension_managers():
            for extension in extension_manager.get_enabled_extensions():
                storage = self._get_storage(extension)

                if storage and storage.exists(''):
                    for path in get_files(storage, ignore_patterns):
                        yield path, storage

    def find(self, path, all=False):
        """Finds the real path to a static file, given a static path.

        The path must start with "ext/<extension_id>/". The files within will
        map to files within the extension's "static" directory.
        """
        parts = path.split('/', 2)

        if len(parts) < 3 or parts[0] != 'ext':
            return []

        extension_id, path = parts[1:]

        for extension_manager in get_extension_managers():
            extension = extension_manager.get_enabled_extension(extension_id)

            if extension:
                match = self._find_in_extension(extension, path)

                if match:
                    # The static file support allows for the same name
                    # across many locations, but as we involve extension IDs,
                    # we know we'll only have one.
                    if all:
                        return [match]
                    else:
                        return match

                break

        return []

    def _find_in_extension(self, extension, path):
        storage = self._get_storage(extension)

        if storage and storage.exists(path):
            matched_path = storage.path(path)

            if matched_path:
                return matched_path

        return None

    def _get_storage(self, extension):
        if extension in self.ignored_extensions:
            return None

        storage = self.storages.get(extension)

        if storage is None:
            storage = self.storage_class(extension)

            if not os.path.isdir(storage.location):
                self.ignored_extensions.add(extension)
                return None

            self.storages[extension] = storage

        return storage


class PackagingStorage(PipelineFinderStorage):
    """Looks up stored files when packaging an extension.

    This is a special Pipeline static file storage implementation that can
    locate the proper Storage class when trying to find a file.

    This works just like PipelineFinderStorage, but can interface with
    PackagingFinder to trigger a lookup across all storages, since
    PackagingFinder by default limits to the extension's static files.
    """
    def find_storage(self, name):
        for finder in self.finders.get_finders():
            if isinstance(finder, PackagingFinder):
                files = finder.list([], all_storages=True)
            else:
                files = finder.list([])

            for path, storage in files:
                matched_path = self._match_location(
                    name,
                    path,
                    getattr(storage, 'prefix', None))

                if matched_path:
                    return matched_path, storage

        raise ValueError("The file '%s' could not be found with %r."
                         % (name, self))

    def _match_location(self, name, path, prefix=None):
        if prefix:
            if prefix != name[:len(prefix)]:
                return None

            prefix = '%s%s' % (prefix, os.sep)
            name = name[len(prefix):]

        norm_path = os.path.normpath(path)
        norm_name = os.path.normpath(name)

        if (norm_path == norm_name or
            os.path.splitext(norm_path)[0] == os.path.splitext(norm_name)[0]):
            return name

        return None


class PackagingFinder(FileSystemFinder):
    """Finds static media files for an extension.

    This is used during packaging to list only static media files provided by
    the extension, but to allow looking up static media from all apps.

    It works with PackagingStorage to do the appropriate lookup given the
    parameters passed.

    Essentially, when collecting static media (using the collectstatic
    management command), Django will call `list()` on the finders, grabbing
    every known static file, and packaging those. For extensions, we don't
    want to grab media files from the main apps, and want to limit only to the
    files bundled with the extension.

    There are times when we do want to list all files, though. For example,
    when referencing definitions files provided by the project for .less
    files.

    In the default case, PackagingFinder.list will only look up files from
    the extension, but if given an extra parameter that PackagingStorage
    can pass (used for finding referenced files), it will look through all
    storages.
    """
    storage_class = PackagingStorage
    extension_static_dir = None

    def list(self, ignore_patterns, all_storages=False):
        if all_storages:
            locations = self.locations
        else:
            locations = [('', self.extension_static_dir)]

        for prefix, root in locations:
            storage = self.storages[root]

            for path in get_files(storage, ignore_patterns):
                yield path, storage

########NEW FILE########
__FILENAME__ = djblets_extensions
from __future__ import unicode_literals

import logging

from django import template
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.utils import six
from pipeline.templatetags.compressed import (CompressedCSSNode,
                                              CompressedJSNode)

from djblets.extensions.hooks import TemplateHook
from djblets.extensions.manager import get_extension_managers
from djblets.util.decorators import basictag


register = template.Library()


@register.tag
@basictag(takes_context=True)
def template_hook_point(context, name):
    """Registers a place where TemplateHooks can render to."""
    def _render_hooks():
        request = context['request']

        for hook in TemplateHook.by_name(name):
            if hook.applies_to(request):
                context.push()

                try:
                    yield hook.render_to_string(request, context)
                except Exception as e:
                    logging.error('Error rendering TemplateHook %r: %s',
                                  hook, e, exc_info=1)

                context.pop()

    return ''.join(_render_hooks())


@register.tag
@basictag(takes_context=True)
def ext_static(context, extension, path):
    """Outputs the URL to the given static media file provided by an extension.

    This works like the {% static %} template tag, but takes an extension
    and generates a URL for the media file within the extension.

    This is meant to be used with
    :py:class:`djblets.extensions.staticfiles.ExtensionFinder`.
    """
    return static('ext/%s/%s' % (extension.id, path))


def _render_bundle(context, node_cls, extension, name, bundle_type):
    try:
        return node_cls('"%s"' % extension.get_bundle_id(name)).render(context)
    except Exception as e:
        logging.critical("Unable to load %s bundle '%s' for "
                         "extension '%s' (%s): %s",
                         bundle_type, name, extension.info.name,
                         extension.id, e, exc_info=1)
        return ''


def _render_css_bundle(context, extension, name):
    return _render_bundle(context, CompressedCSSNode, extension, name, 'CSS')


def _render_js_bundle(context, extension, name):
    return _render_bundle(context, CompressedJSNode, extension, name,
                          'JavaScript')


@register.tag
@basictag(takes_context=True)
def ext_css_bundle(context, extension, name):
    """Outputs HTML to import an extension's CSS bundle."""
    return _render_css_bundle(context, extension, name)


@register.tag
@basictag(takes_context=True)
def ext_js_bundle(context, extension, name):
    """Outputs HTML to import an extension's JavaScript bundle."""
    return _render_js_bundle(context, extension, name)


def _get_extension_bundles(extension_manager_key, context, bundle_attr,
                           renderer):
    """Returns media bundles that can be rendered on the current page.

    This will look through all enabled extensions and find any with static
    media bundles that should be included on the current page, as indicated
    by the context.

    All bundles marked "default" will be included, as will any with an
    ``apply_to`` field containing a URL name matching the current page.
    """
    request = context['request']

    if not getattr(request, 'resolver_match', None):
        return

    requested_url_name = request.resolver_match.url_name

    for manager in get_extension_managers():
        if manager.key != extension_manager_key:
            continue

        for extension in manager.get_enabled_extensions():
            bundles = getattr(extension, bundle_attr, {})

            for bundle_name, bundle in six.iteritems(bundles):
                if (bundle_name == 'default' or
                    requested_url_name in bundle.get('apply_to', [])):
                    yield renderer(context, extension, bundle_name)

        break


@register.tag
@basictag(takes_context=True)
def load_extensions_css(context, extension_manager_key):
    """Loads all CSS bundles that can be rendered on the current page.

    This will include all "default" bundles and any with an ``apply_to``
    containing a URL name matching the current page.
    """
    return ''.join(_get_extension_bundles(
        extension_manager_key, context, 'css_bundles', _render_css_bundle))


@register.tag
@basictag(takes_context=True)
def load_extensions_js(context, extension_manager_key):
    """Loads all JavaScript bundles that can be rendered on the current page.

    This will include all "default" bundles and any with an ``apply_to``
    containing a URL name matching the current page.
    """
    return ''.join(_get_extension_bundles(
        extension_manager_key, context, 'js_bundles', _render_js_bundle))


@register.inclusion_tag('extensions/init_js_extensions.html',
                        takes_context=True)
def init_js_extensions(context, extension_manager_key):
    """Initializes all JavaScript extensions.

    Each extension's required JavaScript files will be loaded in the page,
    and their JavaScript-side Extension subclasses will be instantiated.
    """
    url_name = context['request'].resolver_match.url_name

    for manager in get_extension_managers():
        if manager.key == extension_manager_key:
            js_extensions = []

            for extension in manager.get_enabled_extensions():
                for js_extension_cls in extension.js_extensions:
                    js_extension = js_extension_cls(extension)

                    if js_extension.applies_to(url_name):
                        js_extensions.append(js_extension)

            return {
                'url_name': url_name,
                'js_extensions': js_extensions,
            }

    return {}

########NEW FILE########
__FILENAME__ = admin_urls

########NEW FILE########
__FILENAME__ = urls
from __future__ import unicode_literals

from django.conf.urls import patterns


urlpatterns = patterns('djblets.extensions.views',
    (r'^$', 'test_url')
)

########NEW FILE########
__FILENAME__ = tests
#
# tests.py -- Unit tests for extensions.
#
# Copyright (c) 2010-2013  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

import logging
import os
import threading
import time

from django.conf import settings
from django.conf.urls import include, patterns
from django.core.exceptions import ImproperlyConfigured
from django.dispatch import Signal
from django.template import Context, Template
from django.utils import six
from kgb import SpyAgency
from mock import Mock

from djblets.extensions.extension import Extension, ExtensionInfo
from djblets.extensions.hooks import (ExtensionHook, ExtensionHookPoint,
                                      SignalHook, TemplateHook, URLHook)
from djblets.extensions.manager import (_extension_managers, ExtensionManager,
                                        SettingListWrapper)
from djblets.extensions.settings import Settings
from djblets.extensions.signals import settings_saved
from djblets.testing.testcases import TestCase


class SettingsTest(TestCase):
    def setUp(self):
        # Build up a mocked extension
        self.extension = Mock()
        self.extension.registration = Mock()
        self.test_dict = {
            'test_key1': 'test_value1',
            'test_key2': 'test_value2',
        }
        self.extension.registration.settings = self.test_dict
        self.settings = Settings(self.extension)

    def test_constructor(self):
        """Testing the Extension's Settings constructor"""
        # Build the Settings objects
        self.assertEqual(self.extension, self.settings.extension)

        # Ensure that the registration settings dict gets
        # added to this Settings
        self.assertEqual(self.test_dict['test_key1'],
                         self.settings['test_key1'])

    def test_load_updates_dict(self):
        """Testing that Settings.load correctly updates core dict"""
        new_dict = {
            'test_new_key': 'test_new_value',
            'test_key1': 'new_value',
        }
        self.extension.registration.settings = new_dict
        self.settings.load()

        # Should have added test_new_key, and modified test_key1
        self.assertEqual(new_dict['test_new_key'],
                         self.settings['test_new_key'])
        self.assertEqual(new_dict['test_key1'], self.settings['test_key1'])

        # Should have left test_key2 alone
        self.assertEqual(self.test_dict['test_key2'],
                         self.settings['test_key2'])

    def test_load_silently_discards(self):
        """Testing that Settings.load silently ignores invalid settings"""
        some_string = 'This is a string'
        self.extension.registration.settings = some_string

        try:
            self.settings.load()
        except Exception:
            self.fail("Shouldn't have raised an exception")

    def test_save_updates_database(self):
        """Testing that Settings.save will correctly update registration"""
        registration = self.extension.registration
        self.settings['test_new_key'] = 'Test new value'
        generated_dict = dict(self.settings)
        self.settings.save()

        self.assertTrue(registration.save.called)
        self.assertEqual(generated_dict, registration.settings)

    def test_save_emits_settings_saved_signal(self):
        """Testing that Settings.save emits the settings_saved signal"""
        saw = {}

        def on_settings_saved(*args, **kwargs):
            saw['signal'] = True

        settings_saved.connect(on_settings_saved, sender=self.extension)

        self.settings['test_new_key'] = 'Test new value'
        self.settings.save()

        self.assertIn('signal', saw)


class TestExtensionWithRegistration(Extension):
    """Dummy extension for testing."""
    registration = Mock()
    registration.settings = dict()


@six.add_metaclass(ExtensionHookPoint)
class DummyHook(ExtensionHook):
    def __init__(self, extension):
        super(DummyHook, self).__init__(extension)
        self.foo = [1]

    def shutdown(self):
        super(DummyHook, self).shutdown()
        self.foo.pop()


class ExtensionTest(SpyAgency, TestCase):
    def setUp(self):
        manager = ExtensionManager('')
        self.extension = \
            TestExtensionWithRegistration(extension_manager=manager)

        for index in range(0, 5):
            hook = DummyHook(self.extension)
            self.spy_on(hook.shutdown)
            self.extension.hooks.add(hook)

    def test_extension_constructor(self):
        """Testing Extension construction"""
        self.assertEqual(type(self.extension.settings), Settings)
        self.assertEqual(self.extension, self.extension.settings.extension)

    def test_shutdown(self):
        """Testing Extension.shutdown"""
        self.extension.shutdown()

        for hook in self.extension.hooks:
            self.assertTrue(hook.shutdown.called)

    def test_shutdown_twice(self):
        """Testing Extension.shutdown when called twice"""
        self.extension.shutdown()

        for hook in self.extension.hooks:
            self.assertTrue(hook.shutdown.called)
            hook.shutdown.reset_calls()

        self.extension.shutdown()

        for hook in self.extension.hooks:
            self.assertFalse(hook.shutdown.called)

    def test_get_admin_urlconf(self):
        """Testing Extension with admin URLConfs"""
        did_fail = False
        old_module = self.extension.__class__.__module__
        self.extension.__class__.__module__ = 'djblets.extensions.test.test'

        try:
            self.extension._get_admin_urlconf()
        except ImproperlyConfigured:
            did_fail = True
        finally:
            self.extension.__class__.__module__ = old_module

            if did_fail:
                self.fail("Should have loaded admin_urls.py")


class ExtensionInfoTest(TestCase):
    def test_metadata_from_package(self):
        """Testing ExtensionInfo metadata from package"""
        entrypoint = Mock()
        entrypoint.dist = Mock()

        test_author = 'Test author lorem ipsum'
        test_description = 'Test description lorem ipsum'
        test_email = 'Test author@email.com'
        test_home_page = 'http://www.example.com'
        test_license = 'Test License MIT GPL Apache Drivers'
        test_module_name = 'testextension.dummy.dummy'
        test_extension_id = '%s:DummyExtension' % test_module_name
        test_module_to_app = 'testextension.dummy'
        test_project_name = 'TestProjectName'
        test_summary = 'Test summary lorem ipsum'
        test_version = '1.0'

        test_htdocs_path = os.path.join(settings.MEDIA_ROOT, 'ext',
                                        test_project_name)
        test_static_path = os.path.join(settings.STATIC_ROOT, 'ext',
                                        test_extension_id)

        test_metadata = {
            'Name': test_project_name,
            'Version': test_version,
            'Summary': test_summary,
            'Description': test_description,
            'Author': test_author,
            'Author-email': test_email,
            'License': test_license,
            'Home-page': test_home_page,
        }

        entrypoint.dist.get_metadata_lines = Mock(
            return_value=[
                "%s: %s" % (key, value)
                for key, value in six.iteritems(test_metadata)
            ])

        entrypoint.dist.project_name = test_project_name
        entrypoint.dist.version = test_version

        ext_class = Mock()
        ext_class.__module__ = test_module_name
        ext_class.id = test_extension_id
        ext_class.metadata = None
        extension_info = ExtensionInfo(entrypoint, ext_class)

        self.assertEqual(extension_info.app_name, test_module_to_app)
        self.assertEqual(extension_info.author, test_author)
        self.assertEqual(extension_info.author_email, test_email)
        self.assertEqual(extension_info.description, test_description)
        self.assertFalse(extension_info.enabled)
        self.assertEqual(extension_info.installed_htdocs_path,
                         test_htdocs_path)
        self.assertEqual(extension_info.installed_static_path,
                         test_static_path)
        self.assertFalse(extension_info.installed)
        self.assertEqual(extension_info.license, test_license)
        self.assertEqual(extension_info.metadata, test_metadata)
        self.assertEqual(extension_info.name, test_project_name)
        self.assertEqual(extension_info.summary, test_summary)
        self.assertEqual(extension_info.url, test_home_page)
        self.assertEqual(extension_info.version, test_version)

    def test_custom_metadata(self):
        """Testing ExtensionInfo metadata from Extension.metadata"""
        entrypoint = Mock()
        entrypoint.dist = Mock()

        test_author = 'Test author lorem ipsum'
        test_description = 'Test description lorem ipsum'
        test_email = 'Test author@email.com'
        test_home_page = 'http://www.example.com'
        test_license = 'Test License MIT GPL Apache Drivers'
        test_module_name = 'testextension.dummy.dummy'
        test_module_to_app = 'testextension.dummy'
        test_project_name = 'TestProjectName'
        test_summary = 'Test summary lorem ipsum'
        test_version = '1.0'

        test_htdocs_path = os.path.join(settings.MEDIA_ROOT, 'ext',
                                        'Dummy')

        test_metadata = {
            'Name': test_project_name,
            'Version': test_version,
            'Summary': test_summary,
            'Description': test_description,
            'Author': test_author,
            'Author-email': test_email,
            'License': test_license,
            'Home-page': test_home_page,
        }

        entrypoint.dist.get_metadata_lines = Mock(
            return_value=[
                "%s: %s" % (key, 'Dummy')
                for key, value in six.iteritems(test_metadata)
            ])

        entrypoint.dist.project_name = 'Dummy'
        entrypoint.dist.version = 'Dummy'

        ext_class = Mock()
        ext_class.__module__ = test_module_name
        ext_class.metadata = test_metadata

        extension_info = ExtensionInfo(entrypoint, ext_class)

        self.assertEqual(extension_info.app_name, test_module_to_app)
        self.assertEqual(extension_info.author, test_author)
        self.assertEqual(extension_info.author_email, test_email)
        self.assertEqual(extension_info.description, test_description)
        self.assertFalse(extension_info.enabled)
        self.assertEqual(extension_info.installed_htdocs_path, test_htdocs_path)
        self.assertFalse(extension_info.installed)
        self.assertEqual(extension_info.license, test_license)
        self.assertEqual(extension_info.metadata, test_metadata)
        self.assertEqual(extension_info.name, test_project_name)
        self.assertEqual(extension_info.summary, test_summary)
        self.assertEqual(extension_info.url, test_home_page)
        self.assertEqual(extension_info.version, test_version)


@six.add_metaclass(ExtensionHookPoint)
class TestExtensionHook(ExtensionHook):
    """A dummy ExtensionHook to test with"""


class ExtensionHookTest(TestCase):
    def setUp(self):
        manager = ExtensionManager('')
        self.extension = \
            TestExtensionWithRegistration(extension_manager=manager)
        self.extension_hook = TestExtensionHook(self.extension)

    def test_registration(self):
        """Testing ExtensionHook registration"""
        self.assertEqual(self.extension, self.extension_hook.extension)
        self.assertTrue(self.extension_hook in self.extension.hooks)
        self.assertTrue(self.extension_hook in
                        self.extension_hook.__class__.hooks)

    def test_shutdown(self):
        """Testing ExtensionHook.shutdown"""
        self.extension_hook.shutdown()
        self.assertTrue(self.extension_hook not in
                        self.extension_hook.__class__.hooks)


class ExtensionHookPointTest(TestCase):
    def setUp(self):
        manager = ExtensionManager('')
        self.extension = \
            TestExtensionWithRegistration(extension_manager=manager)
        self.extension_hook_class = TestExtensionHook
        self.dummy_hook = Mock()
        self.extension_hook_class.add_hook(self.dummy_hook)

    def test_extension_hook_class_gets_hooks(self):
        """Testing ExtensionHookPoint.hooks"""
        self.assertTrue(hasattr(self.extension_hook_class, "hooks"))

    def test_add_hook(self):
        """Testing ExtensionHookPoint.add_hook"""
        self.assertTrue(self.dummy_hook in self.extension_hook_class.hooks)

    def test_remove_hook(self):
        """Testing ExtensionHookPoint.remove_hook"""
        self.extension_hook_class.remove_hook(self.dummy_hook)
        self.assertTrue(self.dummy_hook not in self.extension_hook_class.hooks)


class ExtensionManagerTest(SpyAgency, TestCase):
    def setUp(self):
        class TestExtension(Extension):
            """An empty, dummy extension for testing"""
            css_bundles = {
                'default': {
                    'source_filenames': ['test.css'],
                }
            }

            js_bundles = {
                'default': {
                    'source_filenames': ['test.js'],
                }
            }

        self.key = 'test_key'
        self.extension_class = TestExtension
        self.manager = ExtensionManager(self.key)
        self.fake_entrypoint = Mock()
        self.fake_entrypoint.load = Mock(return_value=self.extension_class)
        self.fake_entrypoint.dist = Mock()

        self.test_author = 'Test author lorem ipsum'
        self.test_description = 'Test description lorem ipsum'
        self.test_email = 'Test author@email.com'
        self.test_home_page = 'http://www.example.com'
        self.test_license = 'Test License MIT GPL Apache Drivers'
        self.test_module_name = 'testextension.dummy.dummy'
        self.test_module_to_app = 'testextension.dummy'
        self.test_project_name = 'TestProjectName'
        self.test_summary = 'Test summary lorem ipsum'
        self.test_version = '1.0'

        self.test_metadata = {
            'Name': self.test_project_name,
            'Version': self.test_version,
            'Summary': self.test_summary,
            'Description': self.test_description,
            'Author': self.test_author,
            'Author-email': self.test_email,
            'License': self.test_license,
            'Home-page': self.test_home_page,
        }

        self.fake_entrypoint.dist.get_metadata_lines = Mock(
            return_value=[
                "%s: %s" % (key, value)
                for key, value in six.iteritems(self.test_metadata)
            ])

        self.fake_entrypoint.dist.project_name = self.test_project_name
        self.fake_entrypoint.dist.version = self.test_version

        self.manager._entrypoint_iterator = Mock(
            return_value=[self.fake_entrypoint]
        )
        self.manager.load()

    def tearDown(self):
        self.manager.clear_sync_cache()

    def test_added_to_extension_managers(self):
        """Testing ExtensionManager registration"""
        self.assertTrue(self.manager in _extension_managers)

    def test_get_enabled_extensions_returns_empty(self):
        """Testing ExtensionManager.get_enabled_extensions with no extensions"""
        self.assertEqual(len(self.manager.get_enabled_extensions()), 0)

    def test_load(self):
        """Testing ExtensionManager.get_installed_extensions with loaded extensions"""
        self.assertEqual(len(self.manager.get_installed_extensions()), 1)
        self.assertTrue(self.extension_class in
                        self.manager.get_installed_extensions())
        self.assertTrue(hasattr(self.extension_class, 'info'))
        self.assertEqual(self.extension_class.info.name,
                         self.test_project_name)
        self.assertTrue(hasattr(self.extension_class, 'registration'))
        self.assertEqual(self.extension_class.registration.name,
                         self.test_project_name)

    def test_load_full_reload_hooks(self):
        """Testing ExtensionManager.load with full_reload=True"""
        self.assertEqual(len(self.manager.get_installed_extensions()), 1)

        extension = self.extension_class(extension_manager=self.manager)
        extension = self.manager.enable_extension(self.extension_class.id)

        URLHook(extension, ())
        self.assertEqual(len(URLHook.hooks), 1)
        self.assertEqual(URLHook.hooks[0].extension, extension)

        self.manager.load(full_reload=True)

        self.assertEqual(len(URLHook.hooks), 0)

    def test_load_concurrent_threads(self):
        """Testing ExtensionManager.load with concurrent threads"""
        # There are a number of things that could go wrong both during
        # uninitialization and during initialization of extensions, if
        # two threads attempt to reload at the same time and locking isn't
        # properly implemented.
        #
        # Extension uninit could be called twice, resulting in one thread
        # attempting to access state that's already been destroyed. We
        # could end up hitting:
        #
        #     "Extension's installed app <app> is missing a ref count."
        #     "'<Extension>' object has no attribute 'info'."
        #
        # (Without locking, we end up hitting the latter in this test.)
        #
        # If an extension is being initialized twice simultaneously, then
        # it can hit other errors. An easy one to hit is this assertion:
        #
        #     assert extension_id not in self._extension_instances
        #
        # With proper locking, these issues don't come up. That's what
        # this test case is attempting to check for.
        def _sleep_and_call(manager, orig_func, *args):
            # This works well enough to throw a monkey wrench into things.
            # One thread will be slightly ahead of the other.
            time.sleep(0.2)

            try:
                orig_func(*args)
            except Exception as e:
                logging.error('%s\n', e, exc_info=1)
                exceptions.append(e)

        def _init_extension(manager, *args):
            _sleep_and_call(manager, orig_init_extension, *args)

        def _uninit_extension(manager, *args):
            _sleep_and_call(manager, orig_uninit_extension, *args)

        def _loader(main_connection):
            # Insert the connection from the main thread, so that we can
            # perform lookups. We never write.
            from django.db import connections
            connections['default'] = main_connection

            self.manager.load(full_reload=True)

        # Enable one extension. This extension's state will get a bit messed
        # up if the thread locking fails. We only need one to trigger this.
        self.assertEqual(len(self.manager.get_installed_extensions()), 1)
        self.manager.enable_extension(self.extension_class.id)

        orig_init_extension = self.manager._init_extension
        orig_uninit_extension = self.manager._uninit_extension

        self.spy_on(self.manager._load_extensions)
        self.spy_on(self.manager._init_extension, call_fake=_init_extension)
        self.spy_on(self.manager._uninit_extension,
                    call_fake=_uninit_extension)

        # Store the main connection. We're going to let the threads share it.
        # This trick courtesy of the Django unit tests
        # (django/tests/bakcends/tests.py)
        from django.db import connections
        main_connection = connections['default']
        main_connection.allow_thread_sharing = True

        exceptions = []

        # Make the load request twice, simultaneously.
        t1 = threading.Thread(target=_loader, args=[main_connection])
        t2 = threading.Thread(target=_loader, args=[main_connection])
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(self.manager._load_extensions.calls), 2)
        self.assertEqual(len(self.manager._uninit_extension.calls), 2)
        self.assertEqual(len(self.manager._init_extension.calls), 2)
        self.assertEqual(exceptions, [])

    def test_enable_registers_static_bundles(self):
        """Testing ExtensionManager registers static bundles when enabling extension"""
        settings.PIPELINE_CSS = {}
        settings.PIPELINE_JS = {}

        extension = self.extension_class(extension_manager=self.manager)
        extension = self.manager.enable_extension(self.extension_class.id)

        self.assertEqual(len(settings.PIPELINE_CSS), 1)
        self.assertEqual(len(settings.PIPELINE_JS), 1)

        key = '%s-default' % extension.id
        self.assertIn(key, settings.PIPELINE_CSS)
        self.assertIn(key, settings.PIPELINE_JS)

        css_bundle = settings.PIPELINE_CSS[key]
        js_bundle = settings.PIPELINE_JS[key]

        self.assertIn('source_filenames', css_bundle)
        self.assertEqual(css_bundle['source_filenames'],
                         ['ext/%s/test.css' % extension.id])

        self.assertIn('output_filename', css_bundle)
        self.assertEqual(css_bundle['output_filename'],
                         'ext/%s/css/default.min.css' % extension.id)

        self.assertIn('source_filenames', js_bundle)
        self.assertEqual(js_bundle['source_filenames'],
                         ['ext/%s/test.js' % extension.id])

        self.assertIn('output_filename', js_bundle)
        self.assertEqual(js_bundle['output_filename'],
                         'ext/%s/js/default.min.js' % extension.id)

    def test_disable_unregisters_static_bundles(self):
        """Testing ExtensionManager unregisters static bundles when disabling extension"""
        settings.PIPELINE_CSS = {}
        settings.PIPELINE_JS = {}

        extension = self.extension_class(extension_manager=self.manager)
        extension = self.manager.enable_extension(self.extension_class.id)

        self.assertEqual(len(settings.PIPELINE_CSS), 1)
        self.assertEqual(len(settings.PIPELINE_JS), 1)

        self.manager.disable_extension(extension.id)

        self.assertEqual(len(settings.PIPELINE_CSS), 0)
        self.assertEqual(len(settings.PIPELINE_JS), 0)

    def test_extension_list_sync(self):
        """Testing ExtensionManager extension list synchronization cross-process."""
        key = 'extension-list-sync'

        manager1 = ExtensionManager(key)
        manager2 = ExtensionManager(key)

        for manager in (manager1, manager2):
            manager._entrypoint_iterator = Mock(
                return_value=[self.fake_entrypoint]
            )

        manager1.load()
        manager2.load()

        self.assertEqual(len(manager1.get_installed_extensions()), 1)
        self.assertEqual(len(manager2.get_installed_extensions()), 1)
        self.assertEqual(len(manager1.get_enabled_extensions()), 0)
        self.assertEqual(len(manager2.get_enabled_extensions()), 0)

        manager1.enable_extension(self.extension_class.id)
        self.assertEqual(len(manager1.get_enabled_extensions()), 1)
        self.assertEqual(len(manager2.get_enabled_extensions()), 0)

        self.assertFalse(manager1.is_expired())
        self.assertTrue(manager2.is_expired())

        manager2.load(full_reload=True)
        self.assertEqual(len(manager1.get_enabled_extensions()), 1)
        self.assertEqual(len(manager2.get_enabled_extensions()), 1)
        self.assertFalse(manager1.is_expired())
        self.assertFalse(manager2.is_expired())

    def test_extension_settings_sync(self):
        """Testing ExtensionManager extension settings synchronization cross-process."""
        key = 'extension-settings-sync'
        setting_key = 'foo'
        setting_val = 'abc123'

        manager1 = ExtensionManager(key)
        manager2 = ExtensionManager(key)

        for manager in (manager1, manager2):
            manager._entrypoint_iterator = Mock(
                return_value=[self.fake_entrypoint]
            )

        manager1.load()

        extension1 = manager1.enable_extension(self.extension_class.id)

        manager2.load()

        self.assertFalse(manager1.is_expired())
        self.assertFalse(manager2.is_expired())

        extension2 = manager2.get_enabled_extension(self.extension_class.id)
        self.assertNotEqual(extension2, None)

        self.assertFalse(setting_key in extension1.settings)
        self.assertFalse(setting_key in extension2.settings)
        extension1.settings[setting_key] = setting_val
        extension1.settings.save()

        self.assertFalse(setting_key in extension2.settings)

        self.assertFalse(manager1.is_expired())
        self.assertTrue(manager2.is_expired())

        manager2.load(full_reload=True)
        extension2 = manager2.get_enabled_extension(self.extension_class.id)

        self.assertFalse(manager1.is_expired())
        self.assertFalse(manager2.is_expired())
        self.assertTrue(setting_key in extension1.settings)
        self.assertTrue(setting_key in extension2.settings)
        self.assertEqual(extension1.settings[setting_key], setting_val)
        self.assertEqual(extension2.settings[setting_key], setting_val)


class SettingListWrapperTests(TestCase):
    """Unit tests for djblets.extensions.manager.SettingListWrapper."""
    def test_loading_from_setting(self):
        """Testing SettingListWrapper constructor loading from settings"""
        settings.TEST_SETTING_LIST = ['item1', 'item2']
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')

        self.assertEqual(wrapper.ref_counts.get('item1'), 1)
        self.assertEqual(wrapper.ref_counts.get('item2'), 1)

    def test_add_with_new_item(self):
        """Testing SettingListWrapper.add with new item"""
        settings.TEST_SETTING_LIST = []
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')
        wrapper.add('item1')

        self.assertEqual(settings.TEST_SETTING_LIST, ['item1'])
        self.assertEqual(wrapper.ref_counts.get('item1'), 1)

    def test_add_with_existing_item(self):
        """Testing SettingListWrapper.add with existing item"""
        settings.TEST_SETTING_LIST = ['item1']
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')
        wrapper.add('item1')

        self.assertEqual(settings.TEST_SETTING_LIST, ['item1'])
        self.assertEqual(wrapper.ref_counts.get('item1'), 2)

    def test_remove_with_ref_count_1(self):
        """Testing SettingListWrapper.remove with ref_count == 1"""
        settings.TEST_SETTING_LIST = ['item1']
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')

        self.assertEqual(wrapper.ref_counts.get('item1'), 1)
        wrapper.remove('item1')

        self.assertEqual(settings.TEST_SETTING_LIST, [])
        self.assertFalse('item1' in wrapper.ref_counts)

    def test_remove_with_ref_count_gt_1(self):
        """Testing SettingListWrapper.remove with ref_count > 1"""
        settings.TEST_SETTING_LIST = ['item1']
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')
        wrapper.add('item1')

        self.assertEqual(wrapper.ref_counts.get('item1'), 2)
        wrapper.remove('item1')

        self.assertEqual(settings.TEST_SETTING_LIST, ['item1'])
        self.assertEqual(wrapper.ref_counts.get('item1'), 1)


class SignalHookTest(SpyAgency, TestCase):
    """Unit tests for djblets.extensions.hooks.SignalHook."""
    def setUp(self):
        manager = ExtensionManager('')
        self.test_extension = \
            TestExtensionWithRegistration(extension_manager=manager)
        self.patterns = patterns('',
            (r'^url_hook_test/', include('djblets.extensions.test.urls')))

        self.signal = Signal()
        self.spy_on(self._on_signal_fired)

    def test_initialize(self):
        """Testing SignalHook initialization connects to signal"""
        SignalHook(self.test_extension, self.signal, self._on_signal_fired)

        self.assertEqual(len(self._on_signal_fired.calls), 0)
        self.signal.send(self)
        self.assertEqual(len(self._on_signal_fired.calls), 1)

    def test_shutdown(self):
        """Testing SignalHook.shutdown disconnects from signal"""
        hook = SignalHook(self.test_extension, self.signal,
                          self._on_signal_fired)
        hook.shutdown()

        self.assertEqual(len(self._on_signal_fired.calls), 0)
        self.signal.send(self)
        self.assertEqual(len(self._on_signal_fired.calls), 0)

    def _on_signal_fired(self, *args, **kwargs):
        pass


class URLHookTest(TestCase):
    def setUp(self):
        manager = ExtensionManager('')
        self.test_extension = \
            TestExtensionWithRegistration(extension_manager=manager)
        self.patterns = patterns('',
            (r'^url_hook_test/', include('djblets.extensions.test.urls')))
        self.url_hook = URLHook(self.test_extension, self.patterns)

    def test_url_registration(self):
        """Testing URLHook URL registration"""
        self.assertTrue(set(self.patterns)
            .issubset(set(self.url_hook.dynamic_urls.url_patterns)))
        # And the URLHook should be added to the extension's list of hooks
        self.assertTrue(self.url_hook in self.test_extension.hooks)

    def test_shutdown_removes_urls(self):
        """Testing URLHook.shutdown"""
        # On shutdown, a URLHook's patterns should no longer be in its
        # parent URL resolver's pattern collection.
        self.url_hook.shutdown()
        self.assertFalse(
            set(self.patterns).issubset(
                set(self.url_hook.dynamic_urls.url_patterns)))

        # But the URLHook should still be in the extension's list of hooks
        self.assertTrue(self.url_hook in self.test_extension.hooks)


class TemplateHookTest(TestCase):
    def setUp(self):
        manager = ExtensionManager('')
        self.extension = \
            TestExtensionWithRegistration(extension_manager=manager)
        self.hook_with_applies_name = "template-hook-with-applies-name"
        self.hook_no_applies_name = "template-hook-no-applies-name"
        self.template_hook_no_applies = TemplateHook(self.extension,
            self.hook_no_applies_name, "test_module/some_template.html", [])
        self.template_hook_with_applies = TemplateHook(self.extension,
            self.hook_with_applies_name, "test_module/some_template.html", [
                'test-url-name',
                'url_2',
                'url_3',
            ]
        )

        self.request = Mock()
        self.request._djblets_extensions_kwargs = {}
        self.request.path_info = '/'
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'root'

    def test_hook_added_to_class_by_name(self):
        """Testing TemplateHook registration"""
        self.assertTrue(self.template_hook_with_applies in
                        self.template_hook_with_applies.__class__
                            ._by_name[self.hook_with_applies_name])

        # The TemplateHook should also be added to the Extension's collection
        # of hooks.
        self.assertTrue(self.template_hook_with_applies in
                        self.extension.hooks)

    def test_hook_shutdown(self):
        """Testing TemplateHook shutdown"""
        self.template_hook_with_applies.shutdown()
        self.assertTrue(self.template_hook_with_applies not in
                        self.template_hook_with_applies.__class__
                            ._by_name[self.hook_with_applies_name])

        # The TemplateHook should still be in the Extension's collection
        # of hooks.
        self.assertTrue(self.template_hook_with_applies in
                        self.extension.hooks)

    def test_applies_to_default(self):
        """Testing TemplateHook.applies_to defaults to everything"""
        self.assertTrue(self.template_hook_no_applies.applies_to(self.request))
        self.assertTrue(self.template_hook_no_applies.applies_to(None))

    def test_applies_to(self):
        """Testing TemplateHook.applies_to customization"""
        self.assertFalse(
            self.template_hook_with_applies.applies_to(self.request))

        self.request.resolver_match.url_name = 'test-url-name'
        self.assertTrue(
            self.template_hook_with_applies.applies_to(self.request))

    def test_context_doesnt_leak(self):
        """Testing TemplateHook's context won't leak state"""
        class MyTemplateHook(TemplateHook):
            def render_to_string(self, request, context):
                context['leaky'] = True

                return ''

        hook = MyTemplateHook(self.extension, 'test')
        context = Context({})
        context['request'] = None

        t = Template(
            '{% load djblets_extensions %}'
            '{% template_hook_point "test" %}')
        t.render(context).strip()

        self.assertNotIn('leaky', context)

    def test_sandbox(self):
        """Testing TemplateHook sandboxing"""
        class MyTemplateHook(TemplateHook):
            def render_to_string(self, request, context):
                raise Exception('Oh noes')

        hook = MyTemplateHook(self.extension, 'test')
        context = Context({})
        context['request'] = None

        t = Template(
            '{% load djblets_extensions %}'
            '{% template_hook_point "test" %}')
        t.render(context).strip()

        # Didn't crash. We're good.


# A dummy function that acts as a View method
test_view_method = Mock()

########NEW FILE########
__FILENAME__ = urls
#
# urls.py -- URLs for the Admin UI.
#
# Copyright (c) 2010-2011  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from django.conf.urls import patterns, url


urlpatterns = patterns('djblets.extensions.views',
    url(r'^$', 'extension_list', name='extension-list'),
)

########NEW FILE########
__FILENAME__ = views
#
# views.py -- Views for the Admin UI.
#
# Copyright (c) 2010-2011  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.views.decorators.csrf import csrf_protect


@csrf_protect
@staff_member_required
def extension_list(request, extension_manager,
                   template_name='extensions/extension_list.html'):
    if request.method == 'POST':
        if 'full-reload' in request.POST:
            extension_manager.load(full_reload=True)

        return HttpResponseRedirect('.')
    else:
        # Refresh the extension list.
        extension_manager.load()

        return render_to_response(template_name, RequestContext(request))


@csrf_protect
@staff_member_required
def configure_extension(request, ext_class, form_class, extension_manager,
                        template_name='extensions/configure_extension.html'):
    extension = extension_manager.get_enabled_extension(ext_class.id)

    if not extension or not extension.is_configurable:
        raise Http404

    if request.method == 'POST':
        form = form_class(extension, request.POST, request.FILES)

        if form.is_valid():
            form.save()

            return HttpResponseRedirect(request.path + '?saved=1')
    else:
        form = form_class(extension)

    return render_to_response(template_name, RequestContext(request, {
        'extension': extension,
        'form': form,
        'saved': request.GET.get('saved', 0),
    }))

########NEW FILE########
__FILENAME__ = feedtags
from __future__ import unicode_literals

import calendar
import datetime

from django import template


register = template.Library()


@register.filter
def feeddate(datetuple):
    """
    A filter that converts the date tuple provided from feedparser into
    a datetime object.
    """
    return datetime.datetime.utcfromtimestamp(calendar.timegm(datetuple))

########NEW FILE########
__FILENAME__ = tests
#
# tests.py -- Unit tests for classes in djblets.feedview
#
# Copyright (c) 2008  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from djblets.testing.testcases import TestCase


class FeedViewTests(TestCase):
    urls = "djblets.feedview.test_urls"

    def testViewFeedPage(self):
        """Testing view_feed with the feed-page.html template"""
        response = self.client.get('/feed/')
        self.assertContains(response, "Django 1.0 alpha released", 1)
        self.assertContains(response, "Introducing Review Board News", 1)

    def testViewFeedInline(self):
        """Testing view_feed with the feed-inline.html template"""
        response = self.client.get('/feed-inline/')
        self.assertContains(response, "Django 1.0 alpha released", 1)
        self.assertContains(response, "Introducing Review Board News", 1)

    def testViewFeedError(self):
        """Testing view_feed with a URL error"""
        response = self.client.get('/feed-error/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('error' in response.context)

########NEW FILE########
__FILENAME__ = test_urls
from __future__ import unicode_literals

import os.path

from django.conf.urls import patterns


FEED_URL = "file://%s/testdata/sample.rss" % os.path.dirname(__file__)


urlpatterns = patterns('djblets.feedview.views',
    (r'^feed/$',
     'view_feed',
     {
         'template_name': 'feedview/feed-page.html',
         'url': FEED_URL
     }),
    (r'^feed-inline/$',
     'view_feed',
     {
         'template_name': 'feedview/feed-inline.html',
         'url': FEED_URL
     }),
    (r'^feed-error/$',
     'view_feed',
     {
         'template_name':
         'feedview/feed-inline.html',
         'url': 'http://example.fake/dummy.rss'
     }),
)

########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils.six.moves import http_client
from django.utils.six.moves.urllib.error import URLError
from django.utils.six.moves.urllib.request import urlopen

from djblets.cache.backend import cache_memoize


DEFAULT_EXPIRATION = 2 * 24 * 60 * 60 # 2 days


def view_feed(request, url, template_name="feedview/feed-page.html",
              cache_expiration=DEFAULT_EXPIRATION, extra_context={}):
    """
    Renders an RSS or Atom feed using the given template. This will use
    a cached copy if available in order to reduce hits to the server.
    """
    def fetch_feed():
        import feedparser

        data = urlopen(url).read()

        parser = feedparser.parse(data)

        context = {
            'parser': parser,
        }
        context.update(extra_context)

        return render_to_string(template_name,
                                RequestContext(request, context))

    try:
        return HttpResponse(cache_memoize("feed-%s" % url, fetch_feed,
                            cache_expiration,
                            force_overwrite=('reload' in request.GET)))
    except (URLError, http_client.HTTPException) as e:
        context = {
            'error': e,
        }
        context.update(extra_context)

        return render_to_response(template_name,
                                  RequestContext(request, context))

########NEW FILE########
__FILENAME__ = fields
from __future__ import unicode_literals

from django import forms
import pytz


TIMEZONE_CHOICES = tuple(zip(pytz.common_timezones, pytz.common_timezones))


class TimeZoneField(forms.ChoiceField):
    """A form field that only allows pytz common timezones as the choices."""
    def __init__(self, choices=TIMEZONE_CHOICES, *args, **kwargs):
        super(TimeZoneField, self).__init__(choices, *args, **kwargs)

########NEW FILE########
__FILENAME__ = gravatars
#
# gravatars.py -- Decorational template tags
#
# Copyright (c) 2008-2009  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from django import template

from djblets.gravatars import (get_gravatar_url,
                               get_gravatar_url_for_email)
from djblets.util.decorators import basictag


register = template.Library()


@register.tag
@basictag(takes_context=True)
def gravatar(context, user, size=None):
    """
    Outputs the HTML for displaying a user's gravatar.

    This can take an optional size of the image (defaults to 80 if not
    specified).

    This is also influenced by the following settings:

        GRAVATAR_SIZE    - Default size for gravatars
        GRAVATAR_RATING  - Maximum allowed rating (g, pg, r, x)
        GRAVATAR_DEFAULT - Default image set to show if the user hasn't
                           specified a gravatar (identicon, monsterid, wavatar)

    See http://www.gravatar.com/ for more information.
    """
    url = get_gravatar_url(context['request'], user, size)

    if url:
        return ('<img src="%s" width="%s" height="%s" alt="%s" '
                '     class="gravatar"/>' %
                (url, size, size, user.get_full_name() or user.username))
    else:
        return ''


@register.tag
@basictag(takes_context=True)
def gravatar_url(context, email, size=None):
    """
    Outputs the URL for a gravatar for the given email address.

    This can take an optional size of the image (defaults to 80 if not
    specified).

    This is also influenced by the following settings:

        GRAVATAR_SIZE    - Default size for gravatars
        GRAVATAR_RATING  - Maximum allowed rating (g, pg, r, x)
        GRAVATAR_DEFAULT - Default image set to show if the user hasn't
                           specified a gravatar (identicon, monsterid, wavatar)

    See http://www.gravatar.com/ for more information.
    """
    return get_gravatar_url_for_email(context['request'], email, size)

########NEW FILE########
__FILENAME__ = middleware
#
# middleware.py -- Middleware implementation for logging
#
# Copyright (c) 2008-2009  Christian Hammond
# Copyright (c) 2008-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

import logging
import sys
import time
import traceback

from django.conf import settings
from django.db import connection
from django.db.backends import util
from django.utils import six
from django.utils.six.moves import cStringIO as StringIO

from djblets.log import init_logging, init_profile_logger, log_timed


class CursorDebugWrapper(util.CursorDebugWrapper):
    """
    Replacement for CursorDebugWrapper which stores a traceback in
    `connection.queries`. This will dramatically increase the overhead of having
    DEBUG=True, so use with caution.
    """
    def execute(self, sql, params=()):
        start = time.time()
        try:
            return self.cursor.execute(sql, params)
        finally:
            stop = time.time()
            sql = self.db.ops.last_executed_query(self.cursor, sql, params)
            self.db.queries.append({
                'sql': sql,
                'time': stop - start,
                'stack': traceback.format_stack(),
            })
util.CursorDebugWrapper = CursorDebugWrapper


def reformat_sql(sql):
    sql = sql.replace('`,`', '`, `')
    sql = sql.replace('SELECT ', 'SELECT\t')
    sql = sql.replace('` FROM ', '`\nFROM\t')
    sql = sql.replace(' WHERE ', '\nWHERE\t')
    sql = sql.replace(' INNER JOIN ', '\nINNER JOIN\t')
    sql = sql.replace(' LEFT OUTER JOIN ', '\nLEFT OUTER JOIN\t')
    sql = sql.replace(' OUTER JOIN ', '\nOUTER JOIN\t')
    sql = sql.replace(' ON ', '\n    ON ')
    sql = sql.replace(' ORDER BY ', '\nORDER BY\t')
    return sql


class LoggingMiddleware(object):
    """
    A piece of middleware that sets up logging.

    This a few settings to configure.

    LOGGING_ENABLED
    ---------------

    Default: False

    Sets whether or not logging is enabled.


    LOGGING_DIRECTORY
    -----------------

    Default: None

    Specifies the directory that log files should be stored in.
    This directory must be writable by the process running Django.


    LOGGING_NAME
    ------------

    Default: None

    The name of the log files, excluding the extension and path. This will
    usually be the name of the website or web application. The file extension
    will be automatically appended when the file is written.


    LOGGING_ALLOW_PROFILING
    -----------------------

    Default: False

    Specifies whether or not code profiling is allowed. If True, visiting
    any page with a ``?profiling=1`` parameter in the URL will cause the
    request to be profiled and stored in a ``.prof`` file using the defined
    ``LOGGING_DIRECTORY`` and ``LOGGING_NAME``.


    LOGGING_LINE_FORMAT
    -------------------

    Default: "%(asctime)s - %(levelname)s - %(message)s"

    The format for lines in the log file. See Python's logging documentation
    for possible values in the format string.


    LOGGING_PAGE_TIMES
    ------------------

    Default: False

    If enabled, page access times will be logged. Specifically, it will log
    the initial request, the finished render and response, and the total
    time it look.

    The username and page URL will be included in the logs.


    LOGGING_LEVEL
    -------------

    Default: "DEBUG"

    The minimum level to log. Possible values are ``DEBUG``, ``INFO``,
    ``WARNING``, ``ERROR`` and ``CRITICAL``.
    """

    def process_request(self, request):
        """
        Processes an incoming request. This will set up logging.
        """
        if getattr(settings, 'LOGGING_PAGE_TIMES', False):
            request._page_timedloginfo = \
                log_timed('Page request: HTTP %s %s (by %s)' %
                          (request.method, request.path, request.user))

        if ('profiling' in request.GET and
            getattr(settings, "LOGGING_ALLOW_PROFILING", False)):
            settings.DEBUG = True

    def process_view(self, request, callback, callback_args, callback_kwargs):
        """
        Handler for processing a view. This will run the profiler on the view
        if profiling is allowed in the settings and the user specified the
        profiling parameter on the URL.
        """
        init_logging()

        if ('profiling' in request.GET and
            getattr(settings, "LOGGING_ALLOW_PROFILING", False)):
            import cProfile
            self.profiler = cProfile.Profile()
            args = (request,) + callback_args
            settings.DEBUG = True
            return self.profiler.runcall(callback, *args, **callback_kwargs)

    def process_response(self, request, response):
        """
        Handler for processing a response. Dumps the profiling information
        to the profile log file.
        """
        timedloginfo = getattr(request, '_page_timedloginfo', None)

        if timedloginfo:
            timedloginfo.done()

        if ('profiling' in request.GET and
            getattr(settings, "LOGGING_ALLOW_PROFILING", False)):

            init_profile_logger()

            self.profiler.create_stats()

            # Capture the stats
            out = StringIO()
            old_stdout, sys.stdout = sys.stdout, out
            self.profiler.print_stats(1)
            sys.stdout = old_stdout

            profile_log = logging.getLogger("profile")
            profile_log.log(logging.INFO,
                            "Profiling results for %s (HTTP %s):",
                            request.path, request.method)
            profile_log.log(logging.INFO, out.getvalue().strip())

            profile_log.log(logging.INFO,
                            '%d database queries made\n',
                            len(connection.queries))

            queries = {}
            for query in connection.queries:
                sql = reformat_sql(query['sql'])
                stack = ''.join(query['stack'][:-1])
                time = query['time']
                if sql in queries:
                    queries[sql].append((time, stack))
                else:
                    queries[sql] = [(time, stack)]

            times = {}
            for sql, entries in six.iteritems(queries):
                time = sum((float(entry[0]) for entry in entries))
                tracebacks = '\n\n'.join((entry[1] for entry in entries))
                times[time] = \
                    'SQL Query profile (%d times, %.3fs average)\n%s\n\n%s\n\n' % \
                    (len(entries), time / len(entries), sql, tracebacks)

            sorted_times = sorted(six.iterkeys(times), reverse=1)
            for time in sorted_times:
                profile_log.log(logging.INFO, times[time])

        return response

    def process_exception(self, request, exception):
        """Handle for exceptions on a page.

        Logs the exception, along with the username and path where the
        exception occurred.
        """
        logging.error("Exception thrown for user %s at %s\n\n%s",
                      request.user, request.build_absolute_uri(),
                      exception, exc_info=1)

########NEW FILE########
__FILENAME__ = siteconfig
#
# siteconfig.py -- Siteconfig definitions for the log app
#
# Copyright (c) 2008-2009  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from djblets.log import DEFAULT_LOG_LEVEL

settings_map = {
    'logging_enabled':         'LOGGING_ENABLED',
    'logging_directory':       'LOGGING_DIRECTORY',
    'logging_allow_profiling': 'LOGGING_ALLOW_PROFILING',
    'logging_level':           'LOGGING_LEVEL',
}

defaults = {
    'logging_enabled':         False,
    'logging_directory':       None,
    'logging_allow_profiling': False,
    'logging_level':           DEFAULT_LOG_LEVEL,
}

########NEW FILE########
__FILENAME__ = urls
from __future__ import unicode_literals

from django.conf.urls import patterns, url


urlpatterns = patterns('djblets.log.views',
    url(r'^server/$', 'server_log', name='server-log')
)

########NEW FILE########
__FILENAME__ = views
#
# views.py -- Views for the log app
#
# Copyright (c) 2009  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

import calendar
import datetime
import logging
import os
import re
import time

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils import six
from django.utils.six.moves.urllib.parse import urlencode
from django.utils.translation import ugettext_lazy as _


LEVELS = (
    (logging.DEBUG, 'debug', _('Debug')),
    (logging.INFO, 'info', _('Info')),
    (logging.WARNING, 'warning', _('Warning')),
    (logging.ERROR, 'error', _('Error')),
    (logging.CRITICAL, 'critical', _('Critical')),
)


# Matches the default timestamp format in the logging module.
TIMESTAMP_FMT = '%Y-%m-%d %H:%M:%S'

LOG_LINE_RE = re.compile(
    r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - '
    r'(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL) - '
    r'(?P<message>.*)')


def parse_timestamp(format, timestamp_str):
    """Utility function to parse a timestamp into a datetime.datetime.

    Python 2.5 and up have datetime.strptime, but Python 2.4 does not,
    so we roll our own as per the documentation.

    If passed a timestamp_str of None, we will return None as a convenience.
    """
    if not timestamp_str:
        return None

    return datetime.datetime(*time.strptime(timestamp_str, format)[0:6])


def build_query_string(request, params):
    """Builds a query string that includes the specified parameters along
    with those that were passed to the page.

    params is a dictionary.
    """
    query_parts = []

    for key, value in six.iteritems(request.GET):
        if key not in params:
            query_parts.append(urlencode({
                key: value
            }))

    for key, value in six.iteritems(params):
        if value is not None:
            query_parts.append(urlencode({
                key: value
            }))

    return '?' + '&'.join(query_parts)


def iter_log_lines(from_timestamp, to_timestamp, requested_levels):
    """Generator that iterates over lines in a log file, yielding the
    yielding information about the lines."""
    log_filename = os.path.join(settings.LOGGING_DIRECTORY,
                                settings.LOGGING_NAME + '.log')

    line_info = None

    try:
        fp = open(log_filename, 'r')
    except IOError:
        # We'd log this, but it'd do very little good in practice.
        # It would only appear on the console when using the development
        # server, but production users would never see anything. So,
        # just return gracefully. We'll show an empty log, which is
        # about accurate.
        return

    for line in fp:
        line = line.rstrip()

        m = LOG_LINE_RE.match(line)

        if m:
            if line_info:
                # We have a fully-formed log line and this new line isn't
                # part of it, so yield it now.
                yield line_info
                line_info = None

            timestamp_str = m.group('timestamp')
            level = m.group('level')
            message = m.group('message')

            if not requested_levels or level.lower() in requested_levels:
                timestamp = parse_timestamp(TIMESTAMP_FMT,
                                            timestamp_str.split(',')[0])

                timestamp_date = timestamp.date()

                if ((from_timestamp and from_timestamp > timestamp_date) or
                    (to_timestamp and to_timestamp < timestamp_date)):
                    continue

                line_info = (timestamp, level, message)
        elif line_info:
            line_info = (line_info[0],
                         line_info[1],
                         line_info[2] + "\n" + line)

    if line_info:
        yield line_info

    fp.close()


def get_log_filtersets(request, requested_levels,
                       from_timestamp, to_timestamp):
    """Returns the filtersets that will be used in the log view."""
    logger = logging.getLogger('')
    level_filters = [
        {
            'name': _('All'),
            'url': build_query_string(request, {'levels': None}),
            'selected': len(requested_levels) == 0,
        }
    ] + [
        {
            'name': label_name,
            'url': build_query_string(request, {'levels': level_name}),
            'selected': level_name in requested_levels,
        }
        for level_id, level_name, label_name in LEVELS
        if logger.isEnabledFor(level_id)
    ]

    from_timestamp_str = request.GET.get('from', None)
    to_timestamp_str = request.GET.get('to', None)
    today = datetime.date.today()
    today_str = today.strftime('%Y-%m-%d')
    one_week_ago = today - datetime.timedelta(days=7)
    one_week_ago_str = one_week_ago.strftime('%Y-%m-%d')
    month_range = calendar.monthrange(today.year, today.month)
    this_month_begin_str = today.strftime('%Y-%m-01')
    this_month_end_str = today.strftime('%Y-%m-') + str(month_range[1])

    date_filters = [
        {
            'name': _('Any date'),
            'url': build_query_string(request, {
                'from': None,
                'to': None,
            }),
            'selected': from_timestamp_str is None and
                        to_timestamp_str is None,
        },
        {
            'name': _('Today'),
            'url': build_query_string(request, {
                'from': today_str,
                'to': today_str,
            }),
            'selected': from_timestamp_str == today_str and
                        to_timestamp_str == today_str,
        },
        {
            'name': _('Past 7 days'),
            'url': build_query_string(request, {
                'from': one_week_ago_str,
                'to': today_str,
            }),
            'selected': from_timestamp_str == one_week_ago_str and
                        to_timestamp_str == today_str,
        },
        {
            'name': _('This month'),
            'url': build_query_string(request, {
                'from': this_month_begin_str,
                'to': this_month_end_str,
            }),
            'selected': from_timestamp_str == this_month_begin_str and
                        to_timestamp_str == this_month_end_str,
        },
    ]

    return (
        (_("By date"), date_filters),
        (_("By level"), level_filters),
    )


@staff_member_required
def server_log(request, template_name='log/log.html'):
    """Displays the server log."""

    # First check if logging is even configured. If it's not, just return
    # a 404.
    if (not getattr(settings, "LOGGING_ENABLED", False) or
        not getattr(settings, "LOGGING_DIRECTORY", None)):
        raise Http404()

    requested_levels = []

    # Get the list of levels to show.
    if 'levels' in request.GET:
        requested_levels = request.GET.get('levels').split(',')

    # Get the timestamp ranges.
    from_timestamp = parse_timestamp('%Y-%m-%d', request.GET.get('from'))
    to_timestamp = parse_timestamp('%Y-%m-%d', request.GET.get('to'))

    if from_timestamp:
        from_timestamp = from_timestamp.date()

    if to_timestamp:
        to_timestamp = to_timestamp.date()

    # Get the filters to show.
    filtersets = get_log_filtersets(request, requested_levels,
                                    from_timestamp, to_timestamp)

    # Grab the lines from the log file.
    log_lines = iter_log_lines(from_timestamp, to_timestamp, requested_levels)

    # Figure out the sorting
    sort_type = request.GET.get('sort', 'asc')

    if sort_type == 'asc':
        reverse_sort_type = 'desc'
    else:
        reverse_sort_type = 'asc'
        log_lines = reversed(list(log_lines))

    response = render_to_response(template_name, RequestContext(request, {
        'log_lines': log_lines,
        'filtersets': filtersets,
        'sort_url': build_query_string(request, {'sort': reverse_sort_type}),
        'sort_type': sort_type,
    }))

    return response

########NEW FILE########
__FILENAME__ = settings
#
# Settings for djblets.
#
# This is meant for internal use only. We use it primarily for building
# static media to bundle with djblets.
#
# This should generally not be used in a project.
from __future__ import unicode_literals

import os


SECRET_KEY = '47157c7ae957f904ab809d8c5b77e0209221d4c0'

USE_I18N=True

DEBUG = False
DJBLETS_ROOT = os.path.abspath(os.path.dirname(__file__))
HTDOCS_ROOT = os.path.join(DJBLETS_ROOT, 'htdocs')
STATIC_ROOT = os.path.join(HTDOCS_ROOT, 'static')
STATIC_URL = '/'

STATICFILES_DIRS = (
    os.path.join(DJBLETS_ROOT, 'static'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
)

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

PIPELINE_JS = {
    'djblets-config-forms': {
        'source_filenames': (
            'djblets/js/configForms/base.js',
            'djblets/js/configForms/collections/listItemsCollection.js',
            'djblets/js/configForms/models/listItemModel.js',
            'djblets/js/configForms/models/listModel.js',
            'djblets/js/configForms/views/listItemView.js',
            'djblets/js/configForms/views/listView.js',
            'djblets/js/configForms/views/pagesView.js',
            'djblets/js/configForms/views/tableItemView.js',
            'djblets/js/configForms/views/tableView.js',
        ),
        'output_filename': 'djblets/js/config-forms.min.js',
    },
    'djblets-datagrid': {
        'source_filenames': ('djblets/js/datagrid.js',),
        'output_filename': 'djblets/js/datagrid.min.js',
    },
    'djblets-extensions-admin': {
        'source_filenames': (
            'djblets/js/extensions/models/extensionManagerModel.js',
            'djblets/js/extensions/views/extensionManagerView.js',
        ),
        'output_filename': 'djblets/js/extensions-admin.min.js',
    },
    'djblets-extensions': {
        'source_filenames': (
            'djblets/js/extensions/base.js',
            'djblets/js/extensions/models/extensionModel.js',
            'djblets/js/extensions/models/extensionHookModel.js',
            'djblets/js/extensions/models/extensionHookPointModel.js',
        ),
        'output_filename': 'djblets/js/extensions.min.js',
    },
    'djblets-gravy': {
        'source_filenames': (
            # These are in dependency order
            'djblets/js/jquery.gravy.hacks.js',
            'djblets/js/jquery.gravy.util.js',
            'djblets/js/jquery.gravy.retina.js',
            'djblets/js/jquery.gravy.autosize.js',
            'djblets/js/jquery.gravy.inlineEditor.js',
            'djblets/js/jquery.gravy.modalBox.js',
            'djblets/js/jquery.gravy.tooltip.js',
            'djblets/js/jquery.gravy.funcQueue.js',
        ),
        'output_filename': 'djblets/js/jquery.gravy.min.js',
    },
    'djblets-js-tests': {
        'source_filenames': (
            'djblets/js/configForms/models/tests/listItemModelTests.js',
            'djblets/js/configForms/views/tests/listItemViewTests.js',
            'djblets/js/configForms/views/tests/listViewTests.js',
        ),
        'output_filename': 'djblets/js/tests.min.js',
    },
}

PIPELINE_CSS = {
    'djblets-admin': {
        'source_filenames': (
            'djblets/css/admin.less',
            'djblets/css/extensions.less',
        ),
        'output_filename': 'djblets/css/admin.min.css',
    },
    'djblets-config-forms': {
        'source_filenames': (
            'djblets/css/config-forms.less',
        ),
        'output_filename': 'djblets/css/config-forms.min.css',
    },
    'djblets-datagrid': {
        'source_filenames': (
            'djblets/css/datagrid.less',
        ),
        'output_filename': 'djblets/css/datagrid.min.css',
    },
}

INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'djblets.auth',
    'djblets.datagrid',
    'djblets.extensions',
    'djblets.feedview',
    'djblets.gravatars',
    'djblets.log',
    'djblets.pipeline',
    'djblets.siteconfig',
    'djblets.testing',
    'djblets.util',
    'djblets.webapi',
]

PIPELINE_CSS_COMPRESSOR = None
PIPELINE_JS_COMPRESSOR = 'pipeline.compressors.uglifyjs.UglifyJSCompressor'

# On production (site-installed) builds, we always want to use the pre-compiled
# versions. We want this regardless of the DEBUG setting (since they may
# turn DEBUG on in order to get better error output).
#
# On a build running out of a source tree, for testing purposes, we want to
# use the raw .less and JavaScript files when DEBUG is set. When DEBUG is
# turned off in a non-production build, though, we want to be able to play
# with the built output, so treat it like a production install.

if not DEBUG or os.getenv('FORCE_BUILD_MEDIA', ''):
    PIPELINE_COMPILERS = ['pipeline.compilers.less.LessCompiler']
    PIPELINE_ENABLED = True
elif DEBUG:
    PIPELINE_COMPILERS = []
    PIPELINE_ENABLED = False

########NEW FILE########
__FILENAME__ = admin
#
# admin.py -- Admin site definitions for siteconfig
#
# Copyright (c) 2008-2009  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from django.contrib import admin

from djblets.siteconfig.models import SiteConfiguration


class SiteConfigurationAdmin(admin.ModelAdmin):
    list_display = ('site', 'version')


admin.site.register(SiteConfiguration, SiteConfigurationAdmin)

########NEW FILE########
__FILENAME__ = context_processors
#
# context_processors.py -- Context processors for the siteconfig app.
#
# Copyright (c) 2008-2009  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

import logging

from django.conf import settings

from djblets.siteconfig.models import SiteConfiguration


def siteconfig(request):
    """Provides variables for accessing site configuration data.

    This will provide templates with a 'siteconfig' variable, representing
    the SiteConfiguration for the installation, and a 'siteconfig_settings',
    representing all settings on the SiteConfiguration.

    siteconfig_settings is preferred over accessing siteconfig.settings, as
    it will properly handle returning default values.
    """
    try:
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig_settings = siteconfig.settings_wrapper
    except Exception, e:
        logging.error('Unable to load SiteConfiguration: %s', e, exc_info=1)

        siteconfig = None
        siteconfig_settings = None

    return {
        'siteconfig': siteconfig,
        'siteconfig_settings': siteconfig_settings,
    }


def settings_vars(request):
    return {'settings': settings}

########NEW FILE########
__FILENAME__ = django_settings
#
# djblets/siteconfig/django_settings.py
#
# Copyright (c) 2008  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.cache import DEFAULT_CACHE_ALIAS
from django.utils import six, timezone

from djblets.cache.backend_compat import normalize_cache_backend


def _set_cache_backend(settings, key, value):
    settings.CACHES[DEFAULT_CACHE_ALIAS] = normalize_cache_backend(value)


def _set_static_url(settings, key, value):
    settings.STATIC_URL = value
    staticfiles_storage.base_url = value


def _set_timezone(settings, key, value):
    settings.TIME_ZONE = value

    # Internally, Django will also set os.environ['TZ'] to this value
    # and call time.tzset() when initially loading settings. We don't do
    # that, because it can have consequences.
    #
    # You can think of the timezone being set initially by Django as being
    # the core timezone that will be used for anything outside of a request.
    # What we set here is the timezone that Django will use in its own
    # timezone-related functions (for DateTimeFields and the like).
    #
    # That does mean that time.localtime and other functions will not
    # produce reliable dates. However, we need to ensure that any date/time
    # code is timezone-aware anyway, and works with our setting.
    #
    # To see how using os.environ['TZ'] would cause us problems, read
    # http://blog.chipx86.com/2013/01/26/weird-bugs-django-timezones-and-importing-from-eggs/
    timezone.activate(settings.TIME_ZONE)


locale_settings_map = {
    'locale_timezone':             { 'key': 'TIME_ZONE',
                                     'deserialize_func': str,
                                     'setter': _set_timezone },
    'locale_language_code':        'LANGUAGE_CODE',
    'locale_date_format':          'DATE_FORMAT',
    'locale_datetime_format':      'DATETIME_FORMAT',
    'locale_default_charset':      { 'key': 'DEFAULT_CHARSET',
                                     'deserialize_func': str },
    'locale_language_code':        'LANGUAGE_CODE',
    'locale_month_day_format':     'MONTH_DAY_FORMAT',
    'locale_time_format':          'TIME_FORMAT',
    'locale_year_month_format':    'YEAR_MONTH_FORMAT',
}

mail_settings_map = {
    'mail_server_address':         'SERVER_EMAIL',
    'mail_default_from':           'DEFAULT_FROM_EMAIL',
    'mail_host':                   'EMAIL_HOST',
    'mail_port':                   'EMAIL_PORT',
    'mail_host_user':              { 'key': 'EMAIL_HOST_USER',
                                     'deserialize_func': bytes },
    'mail_host_password':          { 'key': 'EMAIL_HOST_PASSWORD',
                                     'deserialize_func': bytes },
    'mail_use_tls':                'EMAIL_USE_TLS',
}

site_settings_map = {
    'site_media_root':             'MEDIA_ROOT',
    'site_media_url':              'MEDIA_URL',
    'site_static_root':            'STATIC_ROOT',
    'site_static_url':             { 'key': 'STATIC_URL',
                                     'setter': _set_static_url },
    'site_prepend_www':            'PREPEND_WWW',
    'site_upload_temp_dir':        'FILE_UPLOAD_TEMP_DIR',
    'site_upload_max_memory_size': 'FILE_UPLOAD_MAX_MEMORY_SIZE',
}

cache_settings_map = {
    'cache_backend':               { 'key': 'CACHES',
                                     'setter': _set_cache_backend },
    'cache_expiration_time':       'CACHE_EXPIRATION_TIME',
}


# Don't build unless we need it.
_django_settings_map = {}


def get_django_settings_map():
    """
    Returns the settings map for all Django settings that users may need
    to customize.
    """
    if not _django_settings_map:
        _django_settings_map.update(locale_settings_map)
        _django_settings_map.update(mail_settings_map)
        _django_settings_map.update(site_settings_map)
        _django_settings_map.update(cache_settings_map)

    return _django_settings_map


def generate_defaults(settings_map):
    """
    Utility function to generate a defaults mapping.
    """
    defaults = {}

    for siteconfig_key, setting_data in six.iteritems(settings_map):
        if isinstance(setting_data, dict):
            setting_key = setting_data['key']
        else:
            setting_key = setting_data

        if hasattr(settings, setting_key):
            defaults[siteconfig_key] = getattr(settings, setting_key)

    return defaults


def get_locale_defaults():
    """
    Returns the locale-related Django defaults that projects may want to
    let users customize.
    """
    return generate_defaults(locale_settings_map)


def get_mail_defaults():
    """
    Returns the mail-related Django defaults that projects may want to
    let users customize.
    """
    return generate_defaults(mail_settings_map)


def get_site_defaults():
    """
    Returns the site-related Django defaults that projects may want to
    let users customize.
    """
    return generate_defaults(site_settings_map)


def get_cache_defaults():
    """
    Returns the cache-related Django defaults that projects may want to
    let users customize.
    """
    return generate_defaults(cache_settings_map)


def get_django_defaults():
    """
    Returns all Django defaults that projects may want to let users customize.
    """
    return generate_defaults(get_django_settings_map())


def apply_django_settings(siteconfig, settings_map=None):
    """
    Applies all settings from the site configuration to the Django settings
    object.
    """
    if settings_map is None:
        settings_map = get_django_settings_map()

    for key, setting_data in six.iteritems(settings_map):
        if key in siteconfig.settings:
            value = siteconfig.get(key)
            setter = setattr

            if isinstance(setting_data, dict):
                setting_key = setting_data['key']

                if 'setter' in setting_data:
                    setter = setting_data['setter']

                if ('deserialize_func' in setting_data and
                    six.callable(setting_data['deserialize_func'])):
                    value = setting_data['deserialize_func'](value)
            else:
                setting_key = setting_data

            setter(settings, setting_key, value)

########NEW FILE########
__FILENAME__ = forms
#
# forms.py -- Forms for the siteconfig app.
#
# Copyright (c) 2008-2009  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from django import forms
from django.utils import six


class SiteSettingsForm(forms.Form):
    """
    A base form for loading/saving settings for a SiteConfiguration. This is
    meant to be subclassed for different settings pages. Any fields defined
    by the form will be loaded/saved automatically.
    """
    def __init__(self, siteconfig, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.siteconfig = siteconfig
        self.disabled_fields = {}
        self.disabled_reasons = {}

        self.load()

    def load(self):
        """
        Loads settings from the ```SiteConfiguration''' into this form.
        The default values in the form will be the values in the settings.

        This also handles setting disabled fields based on the
        ```disabled_fields''' and ```disabled_reasons''' variables set on
        this form.
        """
        for field in self.fields:
            value = self.siteconfig.get(field)
            self.fields[field].initial = value

            if field in self.disabled_fields:
                self.fields[field].widget.attrs['disabled'] = 'disabled'

    def save(self):
        """
        Saves settings from the form back into the ```SiteConfiguration'''.
        """
        if not self.errors:
            if hasattr(self, "Meta"):
                save_blacklist = getattr(self.Meta, "save_blacklist", [])
            else:
                save_blacklist = []

            for key, value in six.iteritems(self.cleaned_data):
                if key not in save_blacklist:
                    self.siteconfig.set(key, value)

            self.siteconfig.save()

########NEW FILE########
__FILENAME__ = get-siteconfig
from __future__ import unicode_literals

from optparse import make_option

from django.core.management.base import CommandError, NoArgsCommand
from django.utils.translation import ugettext as _

from djblets.siteconfig.models import SiteConfiguration


class Command(NoArgsCommand):
    """Displays a setting in the site configuration."""
    option_list = NoArgsCommand.option_list + (
        make_option('--key', action='store', dest='key',
                    help='The existing key to display (dot-separated)'),
    )

    def handle_noargs(self, **options):
        siteconfig = SiteConfiguration.objects.get_current()

        key = options['key']

        if key is None:
            raise CommandError(_('--key must be provided'))

        path = key.split('.')
        node = siteconfig.settings
        valid_key = True

        for item in path[:-1]:
            try:
                node = node[item]
            except KeyError:
                valid_key = False

        if valid_key:
            key_basename = path[-1]

            if key_basename not in node:
                valid_key = False

        if not valid_key:
            raise CommandError(_("'%s' is not a valid settings key") % key)

        self.stdout.write(node[key_basename])

########NEW FILE########
__FILENAME__ = list-siteconfig
from __future__ import unicode_literals

import json

from django.core.management.base import NoArgsCommand

from djblets.siteconfig.models import SiteConfiguration


class Command(NoArgsCommand):
    """Lists the site configuration."""
    def handle_noargs(self, **options):
        siteconfig = SiteConfiguration.objects.get_current()

        self.stdout.write(json.dumps(siteconfig.settings, indent=2))

########NEW FILE########
__FILENAME__ = set-siteconfig
from __future__ import unicode_literals

from optparse import make_option

from django.core.management.base import CommandError, NoArgsCommand
from django.utils import six
from django.utils.translation import ugettext as _

from djblets.siteconfig.models import SiteConfiguration


class Command(NoArgsCommand):
    """Sets a setting in the site configuration.

    This cannot create new settings. It can only set existing ones.
    """
    option_list = NoArgsCommand.option_list + (
        make_option('--key', action='store', dest='key',
                    help=_('The existing key to modify (dot-separated)')),
        make_option('--value', action='store', dest='value',
                    help=_('The value to store')),
    )

    def handle_noargs(self, **options):
        siteconfig = SiteConfiguration.objects.get_current()

        key = options['key']
        value = options['value']

        if key is None:
            raise CommandError(_('--key must be provided'))

        if value is None:
            raise CommandError(_('--value must be provided'))

        path = key.split('.')
        node = siteconfig.settings
        valid_key = True

        for item in path[:-1]:
            try:
                node = node[item]
            except KeyError:
                valid_key = False

        if valid_key:
            key_basename = path[-1]

            if key_basename not in node:
                valid_key = False

        if not valid_key:
            raise CommandError(_("'%s' is not a valid settings key") % key)

        stored_value = node[key_basename]
        value_type = type(stored_value)

        if value_type not in (six.text_type, six.binary_type, int, bool):
            raise CommandError(_("Cannot set %s keys") % value_type.__name__)

        try:
            if value_type is bool:
                if value not in ('1', '0'):
                    raise TypeError
                else:
                    value = (value == '1')

            norm_value = value_type(value)
        except TypeError:
            raise CommandError(
                _("'%(value)s' is not a valid %(type)s") % {
                    'value': value,
                    'type': value_type.__name__,
                })

        self.stdout.write(_("Setting '%(key)s' to %(value)s") % {
            'key': key,
            'value': norm_value
        })
        node[key_basename] = norm_value
        siteconfig.save()

########NEW FILE########
__FILENAME__ = managers
#
# managers.py -- Model managers for siteconfig objects
#
# Copyright (c) 2008-2009  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from django.contrib.sites.models import Site
from django.db import models
from django.utils import six


_SITECONFIG_CACHE = {}


class SiteConfigurationManager(models.Manager):
    """
    A Manager that provides a get_current function for retrieving the
    SiteConfiguration for this particular running site.
    """
    def get_current(self):
        """
        Returns the site configuration on the active site.
        """
        from djblets.siteconfig.models import SiteConfiguration
        global _SITECONFIG_CACHE

        # This will handle raising a ImproperlyConfigured if not set up
        # properly.
        site = Site.objects.get_current()

        if site.id not in _SITECONFIG_CACHE:
            _SITECONFIG_CACHE[site.id] = \
                SiteConfiguration.objects.get(site=site)

        return _SITECONFIG_CACHE[site.id]

    def clear_cache(self):
        global _SITECONFIG_CACHE
        _SITECONFIG_CACHE = {}

    def check_expired(self):
        """
        Checks each cached SiteConfiguration to find out if its settings
        have expired. This should be called on each request to ensure that
        the copy of the settings is up-to-date in case another web server
        worker process modifies the settings in the database.
        """
        global _SITECONFIG_CACHE

        for key, siteconfig in six.iteritems(_SITECONFIG_CACHE.copy()):
            if siteconfig.is_expired():
                try:
                    # This is stale. Get rid of it so we can load it next time.
                    del _SITECONFIG_CACHE[key]
                except KeyError:
                    pass

########NEW FILE########
__FILENAME__ = middleware
#
# middleware.py -- Middleware for the siteconfig app
#
# Copyright (c) 2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from djblets.siteconfig.models import SiteConfiguration


class SettingsMiddleware(object):
    """
    Middleware that performs necessary operations for siteconfig settings.

    Right now, the primary responsibility is to check on each request if
    the settings have expired, so that a web server worker process doesn't
    end up with a stale view of the site settings.
    """
    def process_request(self, request):
        SiteConfiguration.objects.check_expired()

########NEW FILE########
__FILENAME__ = models
#
# models.py -- Models for the siteconfig app
#
# Copyright (c) 2008-2009  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from django.contrib.sites.models import Site
from django.core.cache import cache
from django.db import models
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible

from djblets.db.fields import JSONField
from djblets.siteconfig.managers import SiteConfigurationManager


_DEFAULTS = {}


class SiteConfigSettingsWrapper(object):
    """Wraps the settings for a SiteConfiguration.

    This is used by the context processor for templates to wrap accessing
    settings data, properly returning defaults.
    """
    def __init__(self, siteconfig):
        self.siteconfig = siteconfig

    def __getattr__(self, key):
        return self.siteconfig.get(key)


@python_2_unicode_compatible
class SiteConfiguration(models.Model):
    """
    Configuration data for a site. The version and all persistent settings
    are stored here.

    The usual way to retrieve a SiteConfiguration is to use
    ```SiteConfiguration.objects.get_current()'''
    """
    site = models.ForeignKey(Site, related_name="config")
    version = models.CharField(max_length=20)
    settings = JSONField()

    objects = SiteConfigurationManager()

    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)

        # Optimistically try to set the Site to the current site instance,
        # which either is cached now or soon will be. That way, we avoid
        # a lookup on the relation later.
        cur_site = Site.objects.get_current()

        if cur_site.pk == self.site_id:
            self.site = cur_site

        # Add this key if it doesn't already exist.
        cache_key = self.__get_sync_cache_key()
        cache.add(cache_key, 1)
        self._last_sync_gen = cache.get(cache_key)

        self.settings_wrapper = SiteConfigSettingsWrapper(self)

    def get(self, key, default=None):
        """
        Retrieves a setting. If the setting is not found, the default value
        will be returned. This is represented by the default parameter, if
        passed in, or a global default if set.
        """
        if default is None and self.id in _DEFAULTS:
            default = _DEFAULTS[self.id].get(key, None)

        return self.settings.get(key, default)

    def set(self, key, value):
        """
        Sets a setting. The key should be a string, but the value can be
        any native Python object.
        """
        self.settings[key] = value

    def add_defaults(self, defaults_dict):
        """
        Adds a dictionary of defaults to this SiteConfiguration. These
        defaults will be used when calling ```get''', if that setting wasn't
        saved in the database.
        """
        if self.id not in _DEFAULTS:
            _DEFAULTS[self.id] = {}

        _DEFAULTS[self.id].update(defaults_dict)

    def add_default(self, key, default_value):
        """
        Adds a single default setting.
        """
        self.add_defaults({key: default_value})

    def get_defaults(self):
        """
        Returns all default settings registered with this SiteConfiguration.
        """
        if self.id not in _DEFAULTS:
            _DEFAULTS[self.id] = {}

        return _DEFAULTS[self.id]

    def is_expired(self):
        """
        Returns whether or not this SiteConfiguration is expired and needs
        to be reloaded.
        """
        sync_gen = cache.get(self.__get_sync_cache_key())

        return (sync_gen is None or
                (type(sync_gen) == int and sync_gen != self._last_sync_gen))

    def save(self, clear_caches=True, **kwargs):
        cache_key = self.__get_sync_cache_key()

        try:
            self._last_sync_gen = cache.incr(cache_key)
        except ValueError:
            self._last_sync_gen = cache.add(cache_key, 1)

        if clear_caches:
            # The cached siteconfig might be stale now. We'll want a refresh.
            # Also refresh the Site cache, since callers may get this from
            # Site.config.
            SiteConfiguration.objects.clear_cache()
            Site.objects.clear_cache()

        super(SiteConfiguration, self).save(**kwargs)

    def __get_sync_cache_key(self):
        return "%s:siteconfig:%s:generation" % (self.site.domain, self.id)

    def __str__(self):
        return "%s (version %s)" % (six.text_type(self.site), self.version)

########NEW FILE########
__FILENAME__ = tests
#
# tests.py -- Unit tests for classes in djblets.siteconfig
#
# Copyright (c) 2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.utils import six

from djblets.siteconfig.django_settings import (apply_django_settings,
                                                cache_settings_map,
                                                mail_settings_map)
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.testcases import TestCase


class SiteConfigTest(TestCase):
    def setUp(self):
        self.siteconfig = SiteConfiguration(site=Site.objects.get_current())
        self.siteconfig.save()

    def tearDown(self):
        self.siteconfig.delete()
        SiteConfiguration.objects.clear_cache()

    def testMailAuthDeserialize(self):
        """Testing mail authentication settings deserialization"""
        # This is bug 1476. We deserialized the e-mail settings to Unicode
        # strings automatically, but this broke mail sending on some setups.
        # The HMAC library is incompatible with Unicode strings in more recent
        # Python 2.6 versions. Now we deserialize as a string. This test
        # ensures that these settings never break again.

        username = 'myuser'
        password = 'mypass'

        self.assertEqual(type(username), six.text_type)
        self.assertEqual(type(password), six.text_type)

        self.siteconfig.set('mail_host_user', username)
        self.siteconfig.set('mail_host_password', password)
        apply_django_settings(self.siteconfig, mail_settings_map)

        self.assertEqual(settings.EMAIL_HOST_USER, username)
        self.assertEqual(settings.EMAIL_HOST_PASSWORD, password)
        self.assertEqual(type(settings.EMAIL_HOST_USER), bytes)
        self.assertEqual(type(settings.EMAIL_HOST_PASSWORD), bytes)

        # Simulate the failure point in HMAC
        import hmac
        settings.EMAIL_HOST_USER.translate(hmac.trans_5C)
        settings.EMAIL_HOST_PASSWORD.translate(hmac.trans_5C)

    def testSynchronization(self):
        """Testing synchronizing SiteConfigurations through cache"""
        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertFalse(siteconfig1.is_expired())

        siteconfig2 = SiteConfiguration.objects.get(site=self.siteconfig.site)
        siteconfig2.set('foobar', 123)

        # Save, and prevent clearing of caches to simulate still having the
        # stale cache around for another thread.
        siteconfig2.save(clear_caches=False)

        self.assertTrue(siteconfig1.is_expired())

        SiteConfiguration.objects.check_expired()

        # See if we fetch the same one again
        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertEqual(siteconfig1.get('foobar'), 123)

    def testSynchronizationExpiredCache(self):
        """Testing synchronizing SiteConfigurations with an expired cache"""
        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertFalse(siteconfig1.is_expired())

        siteconfig2 = SiteConfiguration.objects.get(site=self.siteconfig.site)
        siteconfig2.set('foobar', 123)

        # Save, and prevent clearing of caches to simulate still having the
        # stale cache around for another thread.
        siteconfig2.save(clear_caches=False)

        cache.delete('%s:siteconfig:%s:generation' %
                     (siteconfig2.site.domain, siteconfig2.id))

        self.assertTrue(siteconfig1.is_expired())

        SiteConfiguration.objects.check_expired()

        # See if we fetch the same one again
        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertEqual(siteconfig1.get('foobar'), 123)

    def test_cache_backend(self):
        """Testing cache backend setting with CACHES['default']"""
        settings.CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': 'foo',
            },
            'staticfiles': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': 'staticfiles-cache',
            }
        }

        self.siteconfig.set('cache_backend', 'memcached://localhost:12345/')
        apply_django_settings(self.siteconfig, cache_settings_map)

        self.assertEqual(settings.CACHES['default']['BACKEND'],
                         'django.core.cache.backends.memcached.CacheClass')
        self.assertEqual(settings.CACHES['default']['LOCATION'],
                         'localhost:12345')
        self.assertTrue('staticfiles' in settings.CACHES)

    def test_cache_backend_with_caches(self):
        """Testing cache backend setting with siteconfig-stored CACHES"""
        settings.CACHES['staticfiles'] = {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'staticfiles-cache',
        }

        self.siteconfig.set('cache_backend', {
            'default': {
                'BACKEND': 'django.core.cache.backends.memcached.CacheClass',
                'LOCATION': 'localhost:12345',
            },
        })

        apply_django_settings(self.siteconfig, cache_settings_map)

        self.assertEqual(settings.CACHES['default']['BACKEND'],
                         'django.core.cache.backends.memcached.CacheClass')
        self.assertEqual(settings.CACHES['default']['LOCATION'],
                         'localhost:12345')
        self.assertTrue('staticfiles' in settings.CACHES)

########NEW FILE########
__FILENAME__ = views
#
# views.py -- Views for the siteconfig app
#
# Copyright (c) 2008-2009  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.views.decorators.csrf import csrf_protect

from djblets.siteconfig.models import SiteConfiguration


@csrf_protect
@staff_member_required
def site_settings(request, form_class,
                  template_name="siteconfig/settings.html",
                  extra_context={}):
    """
    Provides a front-end for customizing Review Board settings.
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if request.method == "POST":
        form = form_class(siteconfig, request.POST, request.FILES)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(".?saved=1")
    else:
        form = form_class(siteconfig)

    context = {
        'form': form,
        'saved': request.GET.get('saved', 0)
    }
    context.update(extra_context)

    return render_to_response(template_name, RequestContext(request, context))

########NEW FILE########
__FILENAME__ = decorators
from __future__ import unicode_literals


def add_fixtures(fixtures, replace=False):
    """Adds or replaces the fixtures used for this test.

    This must be used along with :py:func:`djblets.testing.testcases.TestCase`.
    """
    def _dec(func):
        func._fixtures = fixtures
        func._replace_fixtures = replace
        return func

    return _dec

########NEW FILE########
__FILENAME__ = testcases
#
# testing.py -- Some classes useful for unit testing django-based applications
#
# Copyright (c) 2007-2010  Christian Hammond
# Copyright (c) 2007-2010  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import print_function, unicode_literals

import socket
import threading

from django.core.handlers.wsgi import WSGIHandler
from django.core.servers import basehttp
from django.template import Node
from django.test import testcases


class StubNodeList(Node):
    def __init__(self, default_text):
        self.default_text = default_text

    def render(self, context):
        return self.default_text


class StubParser:
    def __init__(self, default_text):
        self.default_text = default_text

    def parse(self, until):
        return StubNodeList(self.default_text)

    def delete_first_token(self):
        pass


class TestCase(testcases.TestCase):
    """Base class for test cases.

    Individual tests on this TestCase can use the :py:func:`add_fixtures`
    decorator to add or replace the fixtures used for the test.
    """
    def __call__(self, *args, **kwargs):
        method = getattr(self, self._testMethodName)
        old_fixtures = getattr(self, 'fixtures', [])

        if hasattr(method, '_fixtures'):
            if getattr(method, '_replace_fixtures'):
                self.fixtures = method._fixtures
            else:
                self.fixtures = old_fixtures + method._fixtures

        super(TestCase, self).__call__(*args, **kwargs)

        if old_fixtures:
            self.fixtures = old_fixtures


class TagTest(TestCase):
    """Base testing setup for custom template tags"""

    def setUp(self):
        self.parser = StubParser(self.getContentText())

    def getContentText(self):
        return "content"


# The following is all based on the code at
# http://trac.getwindmill.com/browser/trunk/windmill/authoring/djangotest.py,
# which is based on the changes submitted for Django in ticket 2879
# (http://code.djangoproject.com/ticket/2879)
#
# A lot of this can go away when/if this patch is committed to Django.

# Code from django_live_server_r8458.diff @  http://code.djangoproject.com/ticket/2879#comment:41
# Editing to monkey patch django rather than be in trunk

class StoppableWSGIServer(basehttp.WSGIServer):
    """
    WSGIServer with short timeout, so that server thread can stop this server.
    """
    def server_bind(self):
        """Sets timeout to 1 second."""
        basehttp.WSGIServer.server_bind(self)
        self.socket.settimeout(1)

    def get_request(self):
        """Checks for timeout when getting request."""
        try:
            sock, address = self.socket.accept()
            sock.settimeout(None)
            return (sock, address)
        except socket.timeout:
            raise


class WSGIRequestHandler(basehttp.WSGIRequestHandler):
    """A custom WSGIRequestHandler that logs all output to stdout.

    Normally, WSGIRequestHandler will color-code messages and log them
    to stderr. It also filters out admin and favicon.ico requests. We don't
    need any of this, and certainly don't want it in stderr, as we'd like
    to only show it on failure.
    """
    def log_message(self, format, *args):
        print(format % args)


class TestServerThread(threading.Thread):
    """Thread for running a http server while tests are running."""

    def __init__(self, address, port):
        self.address = address
        self.port = port
        self._stopevent = threading.Event()
        self.started = threading.Event()
        self.error = None
        super(TestServerThread, self).__init__()

    def run(self):
        """
        Sets up test server and database and loops over handling http requests.
        """
        try:
            handler = basehttp.AdminMediaHandler(WSGIHandler())
            server_address = (self.address, self.port)
            httpd = StoppableWSGIServer(server_address,
                                        WSGIRequestHandler)
            httpd.set_app(handler)
            self.started.set()
        except basehttp.WSGIServerException as e:
            self.error = e
            self.started.set()
            return

        # Must do database stuff in this new thread if database in memory.
        from django.conf import settings

        if hasattr(settings, 'DATABASES'):
            db_engine = settings.DATABASES['default']['ENGINE']
            test_db_name = settings.DATABASES['default']['TEST_NAME']
        else:
            db_engine = settings.DATABASE_ENGINE
            test_db_name = settings.TEST_DATABASE_NAME

        if (db_engine.endswith('sqlite3') and
            (not test_db_name or test_db_name == ':memory:')):
            # Import the fixture data into the test database.
            if hasattr(self, 'fixtures'):
                # We have to use this slightly awkward syntax due to the fact
                # that we're using *args and **kwargs together.
                testcases.call_command('loaddata', verbosity=0, *self.fixtures)

        # Loop until we get a stop event.
        while not self._stopevent.isSet():
            httpd.handle_request()

    def join(self, timeout=None):
        """Stop the thread and wait for it to finish."""
        self._stopevent.set()
        threading.Thread.join(self, timeout)

########NEW FILE########
__FILENAME__ = urls
from __future__ import unicode_literals

from django.conf.urls import patterns, url, include


urlpatterns = patterns('djblets.extensions.tests',
    url(r'^$', 'test_view_method', name="test-url-name"),
    url(r'^admin/extensions/', include('djblets.extensions.urls')),
)

########NEW FILE########
__FILENAME__ = context_processors
from __future__ import unicode_literals

from django.conf import settings


def site_root(request):
    """
    Exposes a SITE_ROOT variable in templates. This assumes that the
    project has been configured with a SITE_ROOT settings variable and
    proper support for basing the installation in a subdirectory.
    """
    return {'SITE_ROOT': settings.SITE_ROOT}

########NEW FILE########
__FILENAME__ = decorators
from django.conf import settings

from djblets.util.decorators import simple_decorator


@simple_decorator
def add_root_url(url_func):
    """Decorates a function that returns a URL in order to add the SITE_ROOT."""
    def _add_root(*args, **kwargs):
        url = url_func(*args, **kwargs)

        if url[0] != '/':
            raise ValueError('Returned URL is not absolute')

        if hasattr(settings, 'SITE_ROOT'):
            return '%s%s' % (settings.SITE_ROOT, url[1:])
        else:
            return url

    return _add_root

########NEW FILE########
__FILENAME__ = patterns
from __future__ import unicode_literals

from django.conf.urls import url
from django.core.urlresolvers import RegexURLPattern
from django.views.decorators.cache import never_cache


def never_cache_patterns(prefix, *args):
    """
    Prevents any included URLs from being cached by the browser.

    It's sometimes desirable not to allow browser caching for a set of URLs.
    This can be used just like patterns().
    """
    pattern_list = []
    for t in args:
        if isinstance(t, (list, tuple)):
            t = url(prefix=prefix, *t)
        elif isinstance(t, RegexURLPattern):
            t.add_prefix(prefix)

        t._callback = never_cache(t.callback)
        pattern_list.append(t)

    return pattern_list

########NEW FILE########
__FILENAME__ = resolvers
from __future__ import unicode_literals

from django.core.urlresolvers import (RegexURLResolver, clear_url_caches,
                                      get_resolver)


class DynamicURLResolver(RegexURLResolver):
    """A URL resolver that allows for dynamically altering URL patterns.

    A standard RegexURLResolver expects that a list of URL patterns will
    be set once and never again change. In most applications, this is a
    good assumption. However, some that are more specialized may need
    to be able to swap in URL patterns dynamically. For example, those
    that can plug in third-party extensions.

    DynamicURLResolver makes it easy to add and remove URL patterns. Any
    time the list of URL patterns changes, they'll be immediately available
    for all URL resolution and reversing.

    The usage is very simple::

        dynamic_patterns = DynamicURLResolver()
        urlpatterns = patterns('', dynamic_patterns)

        dynamic_patterns.add_patterns([
            url(...),
            url(...),
        ])

    DynamicURLResolver will handle managing all the lookup caches to ensure
    that there won't be any stale entries affecting any dynamic URL patterns.
    """
    def __init__(self, regex=r'', app_name=None, namespace=None):
        super(DynamicURLResolver, self).__init__(regex=regex,
                                                 urlconf_name=[],
                                                 app_name=app_name,
                                                 namespace=namespace)
        self._resolver_chain = None

    @property
    def url_patterns(self):
        """Returns the current list of URL patterns.

        This is a simplified version of RegexURLResolver.url_patterns that
        simply returns the preset list of patterns. Unlike the original
        function, we don't care if the list is empty.
        """
        # Internally, urlconf_module represents whatever we're accessing
        # for the list of URLs. It can be a list, or it can be something
        # with a 'urlpatterns' property (intended for a urls.py). However,
        # we force this to be a list in the constructor (as urlconf_name,
        # which gets stored as urlconf_module), so we know we can just
        # return it as-is.
        return self.urlconf_module

    def add_patterns(self, patterns):
        """Adds a list of URL patterns.

        The patterns will be made immediately available for use for any
        lookups or reversing.
        """
        self.url_patterns.extend(patterns)
        self._clear_cache()

    def remove_patterns(self, patterns):
        """Removes a list of URL patterns.

        These patterns will no longer be able to be looked up or reversed.
        """
        for pattern in patterns:
            try:
                self.url_patterns.remove(pattern)
            except ValueError:
                # This may have already been removed. Ignore the error.
                pass

        self._clear_cache()

    def _clear_cache(self):
        """Clears the internal resolver caches.

        This will clear all caches for this resolver and every parent
        of this resolver, in order to ensure that the next lookup or reverse
        will result in a lookup in this resolver. By default, every
        RegexURLResolver in Django will cache all results from its children.

        We take special care to only clear the caches of the resolvers in
        our parent chain.
        """
        for resolver in self.resolver_chain:
            resolver._reverse_dict.clear()
            resolver._namespace_dict.clear()
            resolver._app_dict.clear()

        clear_url_caches()

    @property
    def resolver_chain(self):
        """Returns every RegexURLResolver between here and the root.

        The list of resolvers is cached in order to prevent having to locate
        the resolvers more than once.
        """
        if self._resolver_chain is None:
            self._resolver_chain = \
                self._find_resolver_chain(get_resolver(None))

        return self._resolver_chain

    def _find_resolver_chain(self, resolver):
        if resolver == self:
            return [resolver]

        for url_pattern in resolver.url_patterns:
            if isinstance(url_pattern, RegexURLResolver):
                resolvers = self._find_resolver_chain(url_pattern)

                if resolvers:
                    resolvers.append(resolver)
                    return resolvers

        return []

########NEW FILE########
__FILENAME__ = root
#
# rooturl.py -- URL patterns for rooted sites.
#
# Copyright (c) 2007-2010  Christian Hammond
# Copyright (c) 2010-2013  Beanbag, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# 'Software'), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import patterns, include, handler404, handler500
from django.core.exceptions import ImproperlyConfigured


# Ensures that we can run nose on this without needing to set SITE_ROOT.
# Also serves to let people know if they set one variable without the other.
if hasattr(settings, 'SITE_ROOT'):
    if not hasattr(settings, 'SITE_ROOT_URLCONF'):
        raise ImproperlyConfigured('SITE_ROOT_URLCONF must be set when '
                                   'using SITE_ROOT')

    urlpatterns = patterns('',
        (r'^%s' % settings.SITE_ROOT[1:], include(settings.SITE_ROOT_URLCONF)),
    )
else:
    urlpatterns = None


__all__ = [
    'handler404',
    'handler500',
    'urlpatterns',
]

########NEW FILE########
__FILENAME__ = cache
from __future__ import unicode_literals
import warnings

from djblets.cache.backend_compat import normalize_cache_backend


warnings.warn('djblets.util.cache is deprecated. Use '
              'djblets.cache.backend_compat.', DeprecationWarning)


__all__ = ['normalize_cache_backend']

########NEW FILE########
__FILENAME__ = contextmanagers
#
# misc.py -- Miscellaneous utilities.
#
# Copyright (c) 2011  Beanbag, Inc.
# Copyright (c) 2011  Mike Conley
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from contextlib import contextmanager
import logging
import os
import signal
import sys

from django.utils.translation import ugettext as _


def kill_process(pid):
    """Kill a process."""
    # This is necessary because we need to continue supporting Python 2.5,
    # which doesn't have Popen.kill(). This is inspired by
    # http://stackoverflow.com/questions/1064335
    if sys.platform == 'win32':
        import ctypes
        PROCESS_TERMINATE = 1
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_TERMINATE, False, pid)
        ctypes.windll.kernel32.TerminateProcess(handle, -1)
        ctypes.windll.kernel32.CloseHandle(handle)
    else:
        os.kill(pid, signal.SIGKILL)


@contextmanager
def controlled_subprocess(process_name, process):
    """
    A context manager for a subprocess that guarantees that a process
    is terminated, even if exceptions are thrown while using it.

    The process_name argument is used for logging when the process goes
    down fighting.  The process argument is a process returned by
    subprocess.Popen.

    Example usage:

    process = subprocess.Popen(['patch', '-o', newfile, oldfile])

    with controlled_subprocess("patch", process) as p:
        # ... do things with the process p

    Once outside the with block, you can rest assured that the subprocess
    is no longer running.
    """

    caught_exception = None

    try:
        yield process
    except Exception as e:
        caught_exception = e

    # If we haven't gotten a returncode at this point, we assume the
    # process is blocked.  Let's kill it.
    if process.returncode is None and process.poll() is None:
        logging.warning(
            _("The process '%(name)s' with PID '%(pid)s' did not exit "
              "cleanly and will be killed automatically.")
            % {
                'name': process_name,
                'pid': process.pid,
            })

        kill_process(process.pid)
        # Now that we've killed the process, we'll grab the return code,
        # in order to clear the zombie.
        process.wait()

    # If we caught an exception earlier, re-raise it.
    if caught_exception:
        raise caught_exception

########NEW FILE########
__FILENAME__ = context_processors
#
# context_processors.py -- Miscellaneous context processors
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals
import warnings

from djblets.siteconfig.context_processors import settings_vars as settingsVars
from djblets.urls.context_processors import site_root as siteRoot
from djblets.cache.context_processors import (ajax_serial as ajaxSerial,
                                              media_serial as mediaSerial)


warnings.warn('djblets.util.context_processors is deprecated',
              DeprecationWarning)


__all__ = [
    'ajaxSerial',
    'mediaSerial',
    'settingsVars',
    'siteRoot',
]

########NEW FILE########
__FILENAME__ = dates
#
# dates.py -- Date-related utilities.
#
# Copyright (c) 2008-2009  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

import calendar
from datetime import datetime

from django.db.models import DateField
from django.utils import six
from django.utils.timezone import utc


def http_date(timestamp):
    """
    A wrapper around Django's http_date that accepts DateFields and
    datetime objects directly.
    """
    from django.utils.http import http_date

    if isinstance(timestamp, (DateField, datetime)):
        return http_date(calendar.timegm(timestamp.timetuple()))
    elif isinstance(timestamp, six.string_types):
        return timestamp
    else:
        return http_date(timestamp)


def get_latest_timestamp(timestamps):
    """
    Returns the latest timestamp in a list of timestamps.
    """
    latest = None

    for timestamp in timestamps:
        if latest is None or timestamp > latest:
            latest = timestamp

    return latest


def get_tz_aware_utcnow():
    """Returns a UTC aware datetime object"""
    return datetime.utcnow().replace(tzinfo=utc)

########NEW FILE########
__FILENAME__ = db
from __future__ import unicode_literals
import warnings

from djblets.db.managers import ConcurrencyManager


warnings.warn('djblets.util.db is deprecated', DeprecationWarning)


__all__ = ['ConcurrencyManager']

########NEW FILE########
__FILENAME__ = dbevolution
from __future__ import unicode_literals
import warnings

from djblets.db.evolution import FakeChangeFieldType


warnings.warn('djblets.util.dbevolution is deprecated. Use '
              'djblets.db.evolution instead.', DeprecationWarning)


__all__ = ['FakeChangeFieldType']

########NEW FILE########
__FILENAME__ = decorators
#
# decorators.py -- Miscellaneous, useful decorators.  This might end up moving
#                  to something with a different name.
#
# Copyright (c) 2007  David Trowbridge
# Copyright (c) 2007  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals
from functools import update_wrapper
from inspect import getargspec
import warnings

from django import template
from django.conf import settings
from django.template import TemplateSyntaxError, Variable


# The decorator decorator.  This is copyright unknown, verbatim from
# http://wiki.python.org/moin/PythonDecoratorLibrary
def simple_decorator(decorator):
    """This decorator can be used to turn simple functions
       into well-behaved decorators, so long as the decorators
       are fairly simple. If a decorator expects a function and
       returns a function (no descriptors), and if it doesn't
       modify function attributes or docstring, then it is
       eligible to use this. Simply apply @simple_decorator to
       your decorator and it will automatically preserve the
       docstring and function attributes of functions to which
       it is applied."""
    def new_decorator(f):
        g = decorator(f)
        g.__name__ = f.__name__
        g.__doc__ = f.__doc__
        g.__dict__.update(f.__dict__)
        return g
    # Now a few lines needed to make simple_decorator itself
    # be a well-behaved decorator.
    new_decorator.__name__ = decorator.__name__
    new_decorator.__doc__ = decorator.__doc__
    new_decorator.__dict__.update(decorator.__dict__)
    return new_decorator


def augment_method_from(klass):
    """Augments a class's method with new decorators or documentation.

    This is useful when a class needs to add new decorators or new
    documentation to a parent class's method, without changing the behavior
    or burying the existing decorators.

    The methods using this decorator can provide code to run at the end of
    the parent function. Usually, though, it will just have an empty body
    of ``pass``.
    """
    def _dec(func):
        def _call(*args, **kwargs):
            try:
                f = augmented_func(*args, **kwargs)
            finally:
                func(*args, **kwargs)

            return f

        augmented_func = getattr(klass, func.__name__)

        _call.__name__ = func.__name__
        _call.__doc__ = func.__doc__ or augmented_func.__doc__
        _call.__dict__.update(augmented_func.__dict__)
        _call.__dict__.update(func.__dict__)

        real_func = _call.__dict__.get('_augmented_func', augmented_func)
        _call.__dict__['_augmented_func'] = real_func

        return _call

    return _dec


def basictag(takes_context=False):
    """
    A decorator similar to Django's @register.simple_tag that optionally
    takes a context parameter. This condenses many tag implementations down
    to a few lines of code.

    Example:
        @register.tag
        @basictag(takes_context=True)
        def printuser(context):
            return context['user']
    """
    class BasicTagNode(template.Node):
        def __init__(self, take_context, tag_name, tag_func, args):
            self.takes_context = takes_context
            self.tag_name = tag_name
            self.tag_func = tag_func
            self.args = args

        def render(self, context):
            args = [Variable(var).resolve(context) for var in self.args]

            if self.takes_context:
                return self.tag_func(context, *args)
            else:
                return self.tag_func(*args)

    def basictag_func(tag_func):
        def _setup_tag(parser, token):
            bits = token.split_contents()
            tag_name = bits[0]
            del(bits[0])

            params, xx, xxx, defaults = getargspec(tag_func)
            max_args = len(params)

            if takes_context:
                if params[0] == 'context':
                    max_args -= 1 # Ignore context
                else:
                    raise TemplateSyntaxError(
                        "Any tag function decorated with takes_context=True "
                        "must have a first argument of 'context'")

            min_args = max_args - len(defaults or [])

            if not min_args <= len(bits) <= max_args:
                if min_args == max_args:
                    raise TemplateSyntaxError(
                        "%r tag takes %d arguments." % (tag_name, min_args))
                else:
                    raise TemplateSyntaxError(
                        "%r tag takes %d to %d arguments, got %d." %
                        (tag_name, min_args, max_args, len(bits)))

            return BasicTagNode(takes_context, tag_name, tag_func, bits)

        _setup_tag.__name__ = tag_func.__name__
        _setup_tag.__doc__ = tag_func.__doc__
        _setup_tag.__dict__.update(tag_func.__dict__)
        return _setup_tag

    return basictag_func


def blocktag(*args, **kwargs):
    """Creates a block template tag with beginning/end tags.

    This does all the hard work of creating a template tag that can
    parse the arguments passed in and then parse all nodes between a
    beginning and end tag (such as myblock/endmyblock).

    By default, the end tag is prefixed with "end", but that can be
    changed by passing `end_prefix="end_"` or similar to @blocktag.

    blocktag will call the wrapped function with `context`  and `nodelist`
    parameters, as well as any parameters passed to the tag. It will
    also ensure that a proper error is raised if too many or too few
    parameters are passed.

    For example:

        @register.tag
        @blocktag
        def divify(context, nodelist, div_id=None):
            s = "<div"

            if div_id:
                s += " id='%s'" % div_id

            return s + ">" + nodelist.render(context) + "</div>"
    """
    class BlockTagNode(template.Node):
        def __init__(self, tag_name, tag_func, nodelist, args):
            self.tag_name = tag_name
            self.tag_func = tag_func
            self.nodelist = nodelist
            self.args = args

        def render(self, context):
            args = [Variable(var).resolve(context) for var in self.args]
            return self.tag_func(context, self.nodelist, *args)

    def _blocktag_func(tag_func):
        def _setup_tag(parser, token):
            bits = token.split_contents()
            tag_name = bits[0]
            del(bits[0])

            params, xx, xxx, defaults = getargspec(tag_func)
            max_args = len(params) - 2 # Ignore context and nodelist
            min_args = max_args - len(defaults or [])

            if not min_args <= len(bits) <= max_args:
                if min_args == max_args:
                    raise TemplateSyntaxError(
                        "%r tag takes %d arguments." % (tag_name, min_args))
                else:
                    raise TemplateSyntaxError(
                        "%r tag takes %d to %d arguments, got %d." %
                        (tag_name, min_args, max_args, len(bits)))

            nodelist = parser.parse((('%s%s' % (end_prefix, tag_name)),))
            parser.delete_first_token()
            return BlockTagNode(tag_name, tag_func, nodelist, bits)

        update_wrapper(_setup_tag, tag_func)

        return _setup_tag

    end_prefix = kwargs.get('end_prefix', 'end')

    if len(args) == 1 and callable(args[0]):
        # This is being called in the @blocktag form.
        return _blocktag_func(args[0])
    else:
        # This is being called in the @blocktag(...) form.
        return _blocktag_func


@simple_decorator
def root_url(url_func):
    """Decorates a function that returns a URL in order to add the SITE_ROOT."""
    def _add_root(*args, **kwargs):
        url = url_func(*args, **kwargs)

        if url[0] != '/':
            raise ValueError('Returned URL is not absolute')

        if hasattr(settings, 'SITE_ROOT'):
            return '%s%s' % (settings.SITE_ROOT, url[1:])
        else:
            return url

    warnings.warn('djblets.util.decorators.root_url is deprecated.',
                  DeprecationWarning)

    return _add_root

########NEW FILE########
__FILENAME__ = fields
from __future__ import unicode_literals
import warnings

from djblets.db.fields import (Base64DecodedValue, Base64Field,
                               Base64FieldCreator, CounterField, JSONField,
                               ModificationTimestampField)
from djblets.db.validators import validate_json


warnings.warn('djblets.util.fields is deprecated. Use '
              'djblets.db.fields instead.', DeprecationWarning)


__all__ = [
    'Base64DecodedValue',
    'Base64Field',
    'Base64FieldCreator',
    'CounterField',
    'JSONField',
    'ModificationTimestampField',
    'validate_json',
]

########NEW FILE########
__FILENAME__ = filesystem
#
# filesystem.py -- Filesystem-related functions
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

import os
import sys


def is_exe_in_path(name):
    """Checks whether an executable is in the user's search path.

    This expects a name without any system-specific executable extension.
    It will append the proper extension as necessary. For example,
    use "myapp" and not "myapp.exe".

    This will return True if the app is in the path, or False otherwise.
    """

    if sys.platform == 'win32' and not name.endswith('.exe'):
        name += ".exe"

    for dir in os.environ['PATH'].split(os.pathsep):
        if os.path.exists(os.path.join(dir, name)):
            return True

    return False

########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals
import warnings

from djblets.forms.fields import TIMEZONE_CHOICES, TimeZoneField


warnings.warn('djblets.util.forms is deprecated. Use '
              'djblets.forms.fields instead.', DeprecationWarning)


__all__ = [
    'TIMEZONE_CHOICES',
    'TimeZoneField',
]

########NEW FILE########
__FILENAME__ = http
#
# http.py -- HTTP-related utilities.
#
# Copyright (c) 2008-2009  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from django.http import HttpResponse
from django.utils import six
from django.utils.six.moves.urllib.parse import urlencode

from djblets.util.dates import http_date


class HttpResponseNotAcceptable(HttpResponse):
    status_code = 406


def set_last_modified(response, timestamp):
    """
    Sets the Last-Modified header in a response based on a DateTimeField.
    """
    response['Last-Modified'] = http_date(timestamp)


def get_modified_since(request, last_modified):
    """
    Checks if a Last-Modified timestamp is newer than the requested
    HTTP_IF_MODIFIED_SINCE from the browser. This can be used to bail
    early if no updates have been performed since the last access to the
    page.

    This can take a DateField, datetime, HTTP date-formatted string, or
    a function for the last_modified timestamp. If a function is passed,
    it will only be called if the HTTP_IF_MODIFIED_SINCE header is present.
    """
    if_modified_since = request.META.get('HTTP_IF_MODIFIED_SINCE', None)

    if if_modified_since is not None:
        if six.callable(last_modified):
            last_modified = last_modified()

        return (if_modified_since == http_date(last_modified))

    return False


def set_etag(response, etag):
    """
    Sets the ETag header in a response.
    """
    response['ETag'] = etag


def etag_if_none_match(request, etag):
    """
    Checks if an ETag matches the If-None-Match header sent by the browser.
    This can be used to bail early if no updates have been performed since
    the last access to the page.
    """
    return etag == request.META.get('HTTP_IF_NONE_MATCH', None)


def etag_if_match(request, etag):
    """
    Checks if an ETag matches the If-Match header sent by the browser. This
    is used by PUT requests to to indicate that the update should only happen
    if the specified ETag matches the header.
    """
    return etag == request.META.get('HTTP_IF_MATCH', None)


def get_http_accept_lists(request):
    """Returns lists of mimetypes from the request's Accept header.

    This will return two lists, a list of acceptable mimetypes in order
    of requested priority, and a list of unacceptable mimetypes.
    """
    # Check cached copies for this in the request so we only ever do it once.
    if (hasattr(request, 'djblets_acceptable_mimetypes') and
        hasattr(request, 'djblets_unacceptable_mimetypes')):
        return request.djblets_acceptable_mimetypes, \
               request.djblets_unacceptable_mimetypes

    acceptable_mimetypes = []
    unacceptable_mimetypes = []

    for accept_item in request.META.get('HTTP_ACCEPT', '').strip().split(','):
        parts = accept_item.strip().split(";")
        mimetype = parts[0]
        priority = 1.0

        for part in parts[1:]:
            try:
                key, value = part.split('=')
            except ValueError:
                # There's no '=' in that part.
                continue

            if key == 'q':
                try:
                    priority = float(value)
                except ValueError:
                    # The value isn't a number.
                    continue

        if priority == 0:
            unacceptable_mimetypes.append(mimetype)
        else:
            acceptable_mimetypes.append((mimetype, priority))

    acceptable_mimetypes.sort(key=lambda x: x[1], reverse=True)
    acceptable_mimetypes = [mimetype[0] for mimetype in acceptable_mimetypes]

    setattr(request, 'djblets_acceptable_mimetypes', acceptable_mimetypes)
    setattr(request, 'djblets_unacceptable_mimetypes', unacceptable_mimetypes)

    return acceptable_mimetypes, unacceptable_mimetypes


def get_http_requested_mimetype(request, supported_mimetypes):
    """Gets the mimetype that should be used for returning content.

    This is based on the client's requested list of mimetypes (in the
    HTTP Accept header) and the supported list of mimetypes that can be
    returned in this request.

    If a valid mimetype that can be used is found, it will be returned.
    Otherwise, None is returned, and the caller is expected to return
    HttpResponseNotAccepted.
    """
    acceptable_mimetypes, unacceptable_mimetypes = \
        get_http_accept_lists(request)

    supported_mimetypes_set = set(supported_mimetypes)
    acceptable_mimetypes_set = set(acceptable_mimetypes)
    unacceptable_mimetypes_set = set(unacceptable_mimetypes)

    if not supported_mimetypes_set.intersection(acceptable_mimetypes_set):
        # None of the requested mimetypes are in the supported list.
        # See if there are any mimetypes that are explicitly forbidden.
        if '*/*' in unacceptable_mimetypes:
            acceptable_mimetypes = []
            unacceptable_mimetypes = supported_mimetypes
        else:
            acceptable_mimetypes = [
                mimetype
                for mimetype in supported_mimetypes
                if mimetype not in unacceptable_mimetypes_set
            ]

    if acceptable_mimetypes:
        for mimetype in acceptable_mimetypes:
            if mimetype in supported_mimetypes:
                return mimetype

    # We didn't find any mimetypes that are on the supported list.
    # We need to choose a default now.
    for mimetype in supported_mimetypes:
        if mimetype not in unacceptable_mimetypes:
            return mimetype

    return None


def is_mimetype_a(mimetype, parent_mimetype):
    """Returns whether or not a given mimetype is a subset of another.

    This is generally used to determine if vendor-specific mimetypes is
    a subset of another type. For example,
    :mimetype:`application/vnd.djblets.foo+json` is a subset of
    :mimetype:`application/json`.
    """
    parts = mimetype.split('/')
    parent_parts = parent_mimetype.split('/')

    return (parts[0] == parent_parts[0] and
            (parts[1] == parent_parts[1] or
             parts[1].endswith('+' + parent_parts[1])))


def get_url_params_except(query, *params):
    """Return a URL query string that filters out some params.

    This is used often when one wants to preserve some GET parameters and not
    others.
    """
    return urlencode([
        (key.encode('utf-8'), value.encode('utf-8'))
        for key, value in six.iteritems(query)
        if key not in params
    ])

########NEW FILE########
__FILENAME__ = humanize
#
# humanize.py -- Functions to humanize values
#
# Copyright (c) 2012  Beanbag, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals


def humanize_list(value):
    """
    Humanizes a list of values, inserting commas and "and" where appropriate.

      ========================= ======================
      Example List              Resulting string
      ========================= ======================
      ``["a"]``                 ``"a"``
      ``["a", "b"]``            ``"a and b"``
      ``["a", "b", "c"]``       ``"a, b and c"``
      ``["a", "b", "c", "d"]``  ``"a, b, c, and d"``
      ========================= ======================
    """
    if len(value) == 0:
        return ""
    elif len(value) == 1:
        return value[0]

    s = ", ".join(value[:-1])

    if len(value) > 3:
        s += ","

    return "%s and %s" % (s, value[-1])

########NEW FILE########
__FILENAME__ = misc
#
# misc.py -- Miscellaneous utilities.
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals
import warnings

from djblets.cache.backend import cache_memoize, make_cache_key
from djblets.cache.serials import (generate_ajax_serial,
                                   generate_cache_serials,
                                   generate_locale_serial,
                                   generate_media_serial)
from djblets.db.query import get_object_or_none
from djblets.urls.patterns import never_cache_patterns


warnings.warn('djblets.util.misc is deprecated', DeprecationWarning)


__all__ = [
    'cache_memoize',
    'generate_ajax_serial',
    'generate_cache_serials',
    'generate_locale_serial',
    'generate_media_serial',
    'get_object_or_none',
    'make_cache_key',
    'never_cache_patterns',
]

########NEW FILE########
__FILENAME__ = rooturl
from __future__ import unicode_literals
import warnings

from djblets.urls.root import urlpatterns


warnings.warn('djblets.util.rooturl is deprecated. Use '
              'djblets.urls.root instead.', DeprecationWarning)


__all__ = ['urlpatterns']

########NEW FILE########
__FILENAME__ = serializers
import datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.utils.encoding import force_text
from django.utils.functional import Promise


class DjbletsJSONEncoder(DjangoJSONEncoder):
    """Encodes data into JSON-compatible structures.

    This is a specialization of DjangoJSONEncoder that converts
    lazily ugettext strings to real strings, and chops off the milliseconds
    and microseconds of datetimes.
    """
    def default(self, obj):
        if isinstance(obj, Promise):
            # Handles initializing lazily created ugettext messages.
            return force_text(obj)
        elif isinstance(obj, datetime.datetime):
            # This is like DjangoJSONEncoder's datetime encoding
            # implementation, except that it filters out the milliseconds
            # in addition to microseconds. This ensures consistency between
            # database-stored timestamps and serialized objects.
            r = obj.isoformat()

            if obj.microsecond:
                r = r[:19] + r[26:]

            if r.endswith('+00:00'):
                r = r[:-6] + 'Z'

            return r

        return super(DjbletsJSONEncoder, self).default(obj)

########NEW FILE########
__FILENAME__ = djblets_deco
#
# djblets_deco.py -- Decorational template tags
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from django import template
from django.template.loader import render_to_string

from djblets.util.decorators import blocktag


register = template.Library()


@register.tag
@blocktag
def box(context, nodelist, classname=None):
    """
    Displays a box container around content, with an optional class name.
    """
    return render_to_string('deco/box.html', {
        'classname': classname or "",
        'content': nodelist.render(context)
    })


@register.tag
@blocktag
def errorbox(context, nodelist, box_id=None):
    """
    Displays an error box around content, with an optional ID.
    """
    return render_to_string('deco/errorbox.html', {
        'box_id': box_id or "",
        'content': nodelist.render(context)
    })

########NEW FILE########
__FILENAME__ = djblets_email
#
# djblets_email.py -- E-mail formatting template tags
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

import re

from django import template
from django.template.loader import render_to_string

from djblets.util.decorators import basictag, blocktag


register = template.Library()


@register.tag
@basictag(takes_context=True)
def quoted_email(context, template_name):
    """
    Renders a specified template as a quoted reply, using the current context.
    """
    return quote_text(render_to_string(template_name, context))


@register.tag
@blocktag
def condense(context, nodelist, max_newlines=3):
    """Condenses a block of text.

    This will ensure that there are never more than the given number of
    consecutive newlines. It's particularly useful when formatting plain text
    output, to avoid issues with template tags adding unwanted newlines.
    """
    text = nodelist.render(context).strip()
    text = re.sub(r'\n{%d,}' % (max_newlines + 1), '\n' * max_newlines, text)
    return text


@register.filter
def quote_text(text, level=1):
    """
    Quotes a block of text the specified number of times.
    """
    lines = text.split("\n")
    quoted = ""

    for line in lines:
        quoted += "%s%s\n" % ("> " * level, line)

    return quoted.rstrip()


########NEW FILE########
__FILENAME__ = djblets_forms
#
# djblets_forms.py -- Form-related template tags
#
# Copyright (c) 2008-2009  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from django import template
from django.forms import BooleanField
from django.utils.encoding import force_unicode
from django.utils.html import escape


register = template.Library()


@register.simple_tag
def label_tag(field):
    """
    Outputs the tag for a field's label. This gives more fine-grained
    control over the appearance of the form.

    This exists because a template can't access this directly from a field
    in newforms.
    """
    is_checkbox = is_field_checkbox(field)

    s = '<label for="%s"' % form_field_id(field)

    classes = []

    if field.field.required:
        classes.append("required")

    if is_checkbox:
        classes.append("vCheckboxLabel")

    if classes:
        s += ' class="%s"' % " ".join(classes)

    s += '>%s' % force_unicode(escape(field.label))

    if not is_checkbox:
        s += ':'

    s += '</label>'

    return s


@register.filter
def form_field_id(field):
    """
    Outputs the ID of a field.
    """
    widget = field.field.widget
    id_ = widget.attrs.get('id') or field.auto_id

    if id_:
        return widget.id_for_label(id_)

    return ""


@register.filter
def is_field_checkbox(field):
    """
    Returns whether or not this field is a checkbox (a ```BooleanField''').
    """
    return isinstance(field.field, BooleanField)


@register.filter
def form_field_has_label_first(field):
    """
    Returns whether or not this field should display the label before the
    widget. This is the case in all fields except checkboxes.
    """
    return not is_field_checkbox(field)

########NEW FILE########
__FILENAME__ = djblets_images
#
# djblets_images.py -- Image-related template tags
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

import logging
import os
import tempfile

from django import template
from django.core.files import File
from django.utils.six.moves import cStringIO as StringIO
try:
    from PIL import Image
except ImportError:
    import Image


register = template.Library()


def save_image_to_storage(image, storage, filename):
    """Save an image to storage."""
    (fd, tmp) = tempfile.mkstemp()
    file = os.fdopen(fd, 'w+b')
    image.save(file, 'png')
    file.close()

    file = File(open(tmp, 'rb'))
    storage.save(filename, file)
    file.close()

    os.unlink(tmp)


@register.simple_tag
def crop_image(file, x, y, width, height):
    """
    Crops an image at the specified coordinates and dimensions, returning the
    resulting URL of the cropped image.
    """
    filename = file.name
    storage = file.storage
    basename = filename

    if filename.find(".") != -1:
        basename = filename.rsplit('.', 1)[0]
    new_name = '%s_%d_%d_%d_%d.png' % (basename, x, y, width, height)


    if not storage.exists(new_name):
        try:
            file = storage.open(filename)
            data = StringIO(file.read())
            file.close()

            image = Image.open(data)
            image = image.crop((x, y, x + width, y + height))

            save_image_to_storage(image, storage, new_name)
        except (IOError, KeyError) as e:
            logging.error('Error cropping image file %s at %d, %d, %d, %d '
                          'and saving as %s: %s' %
                          (filename, x, y, width, height, new_name, e),
                          exc_info=1)
            return ""

    return storage.url(new_name)


# From http://www.djangosnippets.org/snippets/192
@register.filter
def thumbnail(file, size='400x100'):
    """
    Creates a thumbnail of an image with the specified size, returning
    the URL of the thumbnail.
    """
    x, y = [int(x) for x in size.split('x')]

    filename = file.name
    if filename.find(".") != -1:
        basename, format = filename.rsplit('.', 1)
        miniature = '%s_%s.%s' % (basename, size, format)
    else:
        basename = filename
        miniature = '%s_%s' % (basename, size)

    storage = file.storage

    if not storage.exists(miniature):
        try:
            file = storage.open(filename, 'rb')
            data = StringIO(file.read())
            file.close()

            image = Image.open(data)
            image.thumbnail([x, y], Image.ANTIALIAS)

            save_image_to_storage(image, storage, miniature)
        except (IOError, KeyError) as e:
            logging.error('Error thumbnailing image file %s and saving '
                          'as %s: %s' % (filename, miniature, e),
                          exc_info=1)
            return ""

    return storage.url(miniature)

########NEW FILE########
__FILENAME__ = djblets_js
#
# djblets_js.py -- JavaScript-related template tags
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

import json

from django import template
from django.core.serializers import serialize
from django.db.models.query import QuerySet
from django.utils import six
from django.utils.safestring import mark_safe

from djblets.util.serializers import DjbletsJSONEncoder


register = template.Library()


@register.simple_tag
def form_dialog_fields(form):
    """
    Translates a Django Form object into a JavaScript list of fields.
    The resulting list of fields can be used to represent the form
    dynamically.
    """
    s = ''

    for field in form:
        s += "{ name: '%s', " % field.name

        if field.is_hidden:
            s += "hidden: true, "
        else:
            s += "label: '%s', " % field.label_tag(field.label + ":")

            if field.field.required:
                s += "required: true, "

            if field.field.help_text:
                s += "help_text: '%s', " % field.field.help_text

        s += "widget: '%s' }," % six.text_type(field)

    # Chop off the last ','
    return "[ %s ]" % s[:-1]


@register.filter
def json_dumps(value, indent=None):
    if isinstance(value, QuerySet):
        result = serialize('json', value, indent=indent)
    else:
        result = json.dumps(value, indent=indent, cls=DjbletsJSONEncoder)

    return mark_safe(result)


@register.filter
def json_dumps_items(d, append=''):
    """Dumps a list of keys/values from a dictionary, without braces.

    This works very much like ``json_dumps``, but doesn't output the
    surrounding braces. This allows it to be used within a JavaScript
    object definition alongside other custom keys.

    If the dictionary is not empty, and ``append`` is passed, it will be
    appended onto the results. This is most useful when you want to append
    a comma after all the dictionary items, in order to provide further
    keys in the template.
    """
    if not d:
        return ''

    return mark_safe(json_dumps(d)[1:-1] + append)

########NEW FILE########
__FILENAME__ = djblets_utils
#
# djblets_utils.py -- Various utility template tags
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

import datetime
import os

from django import template
from django.template import TemplateSyntaxError
from django.template.defaultfilters import stringfilter
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.timezone import is_aware

from djblets.util.decorators import basictag, blocktag
from djblets.util.dates import get_tz_aware_utcnow
from djblets.util.humanize import humanize_list


register = template.Library()


@register.tag
@blocktag
def definevar(context, nodelist, varname):
    """
    Defines a variable in the context based on the contents of the block.
    This is useful when you need to reuse the results of some tag logic
    multiple times in a template or in a blocktrans tag.
    """
    context[varname] = nodelist.render(context)
    return ""


@register.tag
@blocktag
def ifuserorperm(context, nodelist, user, perm):
    """
    Renders content depending on whether the logged in user is the specified
    user or has the specified permission.

    This is useful when you want to restrict some code to the owner of a
    review request or to a privileged user that has the abilities of the
    owner.

    Example::

        {% ifuserorperm myobject.user "myobject.can_change_status" %}
        Owner-specific content here...
        {% endifuserorperm %}
    """
    if _check_userorperm(context, user, perm):
        return nodelist.render(context)

    return ''


@register.tag
@blocktag
def ifnotuserandperm(context, nodelist, user, perm):
    """
    The opposite of ifuserorperm.

    Renders content if the logged in user is not the specified user and doesn't
    have the specified permission.

    Example::

        {% ifuserorperm myobject.user "myobject.can_change_status" %}
        Owner-specific content here...
        {% endifuserorperm %}
        {% ifnotuserandperm myobject.user "myobject.can_change_status" %}
        Another owner-specific content here...
        {% endifnotuserandperm %}
    """
    if not _check_userorperm(context, user, perm):
        return nodelist.render(context)

    return ''


def _check_userorperm(context, user, perm):
    from django.contrib.auth.models import AnonymousUser, User

    req_user = context.get('user', None)

    if isinstance(req_user, AnonymousUser):
        return False

    if req_user.has_perm(perm):
        return True

    return ((isinstance(user, User) and user == req_user) or
            user == req_user.pk)


@register.tag
@basictag(takes_context=True)
def include_as_string(context, template_name):
    s = render_to_string(template_name, context)
    s = s.replace("'", "\\'")
    s = s.replace("\n", "\\\n")
    return "'%s'" % s


@register.tag
@blocktag
def attr(context, nodelist, attrname):
    """
    Sets an HTML attribute to a value if the value is not an empty string.
    """
    content = nodelist.render(context)

    if content.strip() == "":
        return ""

    return ' %s="%s"' % (attrname, content)


@register.filter
def escapespaces(value):
    """HTML-escapes all spaces with ``&nbsp;`` and newlines with ``<br />``."""
    return value.replace('  ', '&nbsp; ').replace('\n', '<br />')


@register.simple_tag
def ageid(timestamp):
    """
    Returns an ID based on the difference between a timestamp and the
    current time.

    The ID is returned based on the following differences in days:

      ========== ====
      Difference ID
      ========== ====
      0          age1
      1          age2
      2          age3
      3          age4
      4 or more  age5
      ========== ====
    """
    if timestamp is None:
        return ""

    # Convert datetime.date into datetime.datetime
    if timestamp.__class__ is not datetime.datetime:
        timestamp = datetime.datetime(timestamp.year, timestamp.month,
                                      timestamp.day)

    now = datetime.datetime.utcnow()

    if is_aware(timestamp):
        now = get_tz_aware_utcnow()

    delta = now - (timestamp -
                   datetime.timedelta(0, 0, timestamp.microsecond))

    if delta.days == 0:
        return "age1"
    elif delta.days == 1:
        return "age2"
    elif delta.days == 2:
        return "age3"
    elif delta.days == 3:
        return "age4"
    else:
        return "age5"


@register.filter
def user_displayname(user):
    """
    Returns the display name of the user.

    If the user has a full name set, it will display this. Otherwise, it will
    display the username.
    """
    return user.get_full_name() or user.username


register.filter('humanize_list', humanize_list)


@register.filter
def contains(container, value):
    """Returns True if the specified value is in the specified container."""
    return value in container


@register.filter
def getitem(container, value):
    """Returns the attribute of a specified name from a container."""
    return container[value]


@register.filter
def exclude_item(container, item):
    """Excludes an item from a list."""
    if isinstance(container, list):
        container = list(container)

        if item in container:
            container.remove(item)
    else:
        raise TemplateSyntaxError("remove_item expects a list")

    return container


@register.filter
def indent(value, numspaces=4):
    """Indents a string by the specified number of spaces."""
    indent_str = ' ' * numspaces
    return indent_str + value.replace('\n', '\n' + indent_str)


@register.filter
def basename(value):
    """Returns the basename of a path."""
    return os.path.basename(value)


@register.filter(name="range")
def range_filter(value):
    """
    Turns an integer into a range of numbers.

    This is useful for iterating with the "for" tag. For example:

    {% for i in 10|range %}
      {{i}}
    {% endfor %}
    """
    return range(value)


@register.filter
def realname(user):
    """
    Returns the real name of a user, if available, or the username.

    If the user has a full name set, this will return the full name.
    Otherwise, this returns the username.
    """
    full_name = user.get_full_name()
    if full_name == '':
        return user.username
    else:
        return full_name


@register.filter
@stringfilter
def startswith(value1, value2):
    """Returns true if value1 starts with value2."""
    return value1.startswith(value2)


@register.filter
@stringfilter
def endswith(value1, value2):
    """Returns true if value1 ends with value2."""
    return value1.endswith(value2)


@register.filter
@stringfilter
def paragraphs(text):
    """
    Adds <p>...</p> tags around blocks of text in a string. This expects
    that each paragraph in the string will be on its own line. Blank lines
    are filtered out.
    """
    s = ""

    for line in text.splitlines():
        if line:
            s += "<p>%s</p>\n" %  line

    return mark_safe(s)
paragraphs.is_safe = True

########NEW FILE########
__FILENAME__ = testing
#
# testing.py -- Some classes useful for unit testing django-based applications
#
# Copyright (c) 2007-2010  Christian Hammond
# Copyright (c) 2007-2010  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals
import warnings

from djblets.testing.testcases import (StubNodeList, StubParser,
                                       TagTest, TestCase)


warnings.warn('djblets.util.testing is deprecated. Use '
              'djblets.testing.testcases instead.', DeprecationWarning)


__all__ = ['StubNodeList', 'StubParser', 'TagTest', 'TestCase']

########NEW FILE########
__FILENAME__ = tests
#
# tests.py -- Unit tests for classes in djblets.util
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

import datetime
import unittest

from django.conf import settings
from django.conf.urls import include, patterns, url
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.urlresolvers import NoReverseMatch, reverse
from django.http import HttpRequest
from django.template import Token, TOKEN_TEXT, TemplateSyntaxError
from django.utils import six
from django.utils.html import strip_spaces_between_tags

from djblets.cache.backend import (cache_memoize, make_cache_key,
                                  CACHE_CHUNK_SIZE)
from djblets.db.fields import JSONField
from djblets.testing.testcases import TestCase, TagTest
from djblets.urls.resolvers import DynamicURLResolver
from djblets.util.http import (get_http_accept_lists,
                               get_http_requested_mimetype,
                               is_mimetype_a)
from djblets.util.templatetags import (djblets_deco, djblets_email,
                                       djblets_utils)


def normalize_html(s):
    return strip_spaces_between_tags(s).strip()


class CacheTest(TestCase):
    def tearDown(self):
        cache.clear()

    def test_cache_memoize(self):
        """Testing cache_memoize"""
        cacheKey = "abc123"
        testStr = "Test 123"

        def cacheFunc(cacheCalled=[]):
            self.assertTrue(not cacheCalled)
            cacheCalled.append(True)
            return testStr

        result = cache_memoize(cacheKey, cacheFunc)
        self.assertEqual(result, testStr)

        # Call a second time. We should only call cacheFunc once.
        result = cache_memoize(cacheKey, cacheFunc)
        self.assertEqual(result, testStr)

    def test_cache_memoize_large_files(self):
        """Testing cache_memoize with large files"""
        cacheKey = "abc123"

        # This takes into account the size of the pickle data, and will
        # get us to exactly 2 chunks of data in cache.
        data = 'x' * (CACHE_CHUNK_SIZE * 2 - 8)

        def cacheFunc(cacheCalled=[]):
            self.assertTrue(not cacheCalled)
            cacheCalled.append(True)
            return data

        result = cache_memoize(cacheKey, cacheFunc, large_data=True,
                               compress_large_data=False)
        self.assertEqual(result, data)

        self.assertTrue(make_cache_key(cacheKey) in cache)
        self.assertTrue(make_cache_key('%s-0' % cacheKey) in cache)
        self.assertTrue(make_cache_key('%s-1' % cacheKey) in cache)
        self.assertFalse(make_cache_key('%s-2' % cacheKey) in cache)

        result = cache_memoize(cacheKey, cacheFunc, large_data=True,
                               compress_large_data=False)
        self.assertEqual(result, data)


class BoxTest(TagTest):
    def testPlain(self):
        """Testing box tag"""
        node = djblets_deco.box(self.parser, Token(TOKEN_TEXT, 'box'))
        context = {}

        self.assertEqual(normalize_html(node.render(context)),
                         '<div class="box-container"><div class="box">' +
                         '<div class="box-inner">\ncontent\n  ' +
                         '</div></div></div>')

    def testClass(self):
        """Testing box tag (with extra class)"""
        node = djblets_deco.box(self.parser, Token(TOKEN_TEXT, 'box "class"'))
        context = {}

        self.assertEqual(normalize_html(node.render(context)),
                         '<div class="box-container"><div class="box class">' +
                         '<div class="box-inner">\ncontent\n  ' +
                         '</div></div></div>')

    def testError(self):
        """Testing box tag (invalid usage)"""
        self.assertRaises(TemplateSyntaxError,
                          lambda: djblets_deco.box(
                              self.parser,
                              Token(TOKEN_TEXT, 'box "class" "foo"')))


class ErrorBoxTest(TagTest):
    def testPlain(self):
        """Testing errorbox tag"""
        node = djblets_deco.errorbox(self.parser,
                                     Token(TOKEN_TEXT, 'errorbox'))

        context = {}

        self.assertEqual(normalize_html(node.render(context)),
                         '<div class="errorbox">\ncontent\n</div>')

    def testId(self):
        """Testing errorbox tag (with id)"""
        node = djblets_deco.errorbox(self.parser,
                                     Token(TOKEN_TEXT, 'errorbox "id"'))

        context = {}

        self.assertEqual(normalize_html(node.render(context)),
                         '<div class="errorbox" id="id">\ncontent\n</div>')


    def testError(self):
        """Testing errorbox tag (invalid usage)"""
        self.assertRaises(TemplateSyntaxError,
                          lambda: djblets_deco.errorbox(
                              self.parser,
                              Token(TOKEN_TEXT, 'errorbox "id" "foo"')))


class HttpTest(TestCase):
    def setUp(self):
        self.request = HttpRequest()
        self.request.META['HTTP_ACCEPT'] = \
            'application/json;q=0.5,application/xml,text/plain;q=0.0,*/*;q=0.0'

    def test_http_accept_lists(self):
        """Testing djblets.http.get_http_accept_lists"""

        acceptable_mimetypes, unacceptable_mimetypes = \
            get_http_accept_lists(self.request)

        self.assertEqual(acceptable_mimetypes,
                         ['application/xml', 'application/json'])
        self.assertEqual(unacceptable_mimetypes, ['text/plain', '*/*'])

    def test_get_requested_mimetype_with_supported_mimetype(self):
        """Testing djblets.http.get_requested_mimetype with supported mimetype"""
        self.assertEqual(
            get_http_requested_mimetype(self.request, ['foo/bar',
                                                       'application/json']),
            'application/json')
        self.assertEqual(
            get_http_requested_mimetype(self.request, ['application/xml']),
            'application/xml')
        self.assertEqual(
            get_http_requested_mimetype(self.request, ['application/json',
                                                       'application/xml']),
            'application/xml')

    def test_get_requested_mimetype_with_no_consensus(self):
        """Testing djblets.http.get_requested_mimetype with no consensus between client and server"""
        self.request = HttpRequest()
        self.request.META['HTTP_ACCEPT'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'

        self.assertEqual(
            get_http_requested_mimetype(self.request, ['application/json',
                                                       'application/x-foo']),
            'application/json')

    def test_get_requested_mimetype_with_wildcard_supported_mimetype(self):
        """Testing djblets.http.get_requested_mimetype with supported */* mimetype"""
        self.request = HttpRequest()
        self.request.META['HTTP_ACCEPT'] = '*/*'
        self.assertEqual(
            get_http_requested_mimetype(self.request, ['application/json',
                                                       'application/xml']),
            'application/json')

    def test_get_requested_mimetype_with_unsupported_mimetype(self):
        """Testing djblets.http.get_requested_mimetype with unsupported mimetype"""
        self.assertEqual(
            get_http_requested_mimetype(self.request, ['text/plain']),
            None)
        self.assertEqual(
            get_http_requested_mimetype(self.request, ['foo/bar']),
            None)

    def test_is_mimetype_a(self):
        """Testing djblets.util.http.is_mimetype_a"""
        self.assertTrue(is_mimetype_a('application/json',
                                      'application/json'))
        self.assertTrue(is_mimetype_a('application/vnd.foo+json',
                                      'application/json'))
        self.assertFalse(is_mimetype_a('application/xml',
                                       'application/json'))
        self.assertFalse(is_mimetype_a('foo/vnd.bar+json',
                                       'application/json'))


class AgeIdTest(TagTest):
    def setUp(self):
        TagTest.setUp(self)

        self.now = datetime.datetime.utcnow()

        self.context = {
            'now':    self.now,
            'minus1': self.now - datetime.timedelta(1),
            'minus2': self.now - datetime.timedelta(2),
            'minus3': self.now - datetime.timedelta(3),
            'minus4': self.now - datetime.timedelta(4),
        }

    def testNow(self):
        """Testing ageid tag (now)"""
        self.assertEqual(djblets_utils.ageid(self.now), 'age1')

    def testMinus1(self):
        """Testing ageid tag (yesterday)"""
        self.assertEqual(djblets_utils.ageid(self.now - datetime.timedelta(1)),
                         'age2')

    def testMinus2(self):
        """Testing ageid tag (two days ago)"""
        self.assertEqual(djblets_utils.ageid(self.now - datetime.timedelta(2)),
                         'age3')

    def testMinus3(self):
        """Testing ageid tag (three days ago)"""
        self.assertEqual(djblets_utils.ageid(self.now - datetime.timedelta(3)),
                         'age4')

    def testMinus4(self):
        """Testing ageid tag (four days ago)"""
        self.assertEqual(djblets_utils.ageid(self.now - datetime.timedelta(4)),
                         'age5')

    def testNotDateTime(self):
        """Testing ageid tag (non-datetime object)"""
        class Foo:
            def __init__(self, now):
                self.day   = now.day
                self.month = now.month
                self.year  = now.year

        self.assertEqual(djblets_utils.ageid(Foo(self.now)), 'age1')


class TestEscapeSpaces(unittest.TestCase):
    def test(self):
        """Testing escapespaces filter"""
        self.assertEqual(djblets_utils.escapespaces('Hi there'),
                         'Hi there')
        self.assertEqual(djblets_utils.escapespaces('Hi  there'),
                         'Hi&nbsp; there')
        self.assertEqual(djblets_utils.escapespaces('Hi  there\n'),
                         'Hi&nbsp; there<br />')


class TestHumanizeList(unittest.TestCase):
    def test0(self):
        """Testing humanize_list filter (length 0)"""
        self.assertEqual(djblets_utils.humanize_list([]), '')

    def test1(self):
        """Testing humanize_list filter (length 1)"""
        self.assertEqual(djblets_utils.humanize_list(['a']), 'a')

    def test2(self):
        """Testing humanize_list filter (length 2)"""
        self.assertEqual(djblets_utils.humanize_list(['a', 'b']), 'a and b')

    def test3(self):
        """Testing humanize_list filter (length 3)"""
        self.assertEqual(djblets_utils.humanize_list(['a', 'b', 'c']),
                         'a, b and c')

    def test4(self):
        """Testing humanize_list filter (length 4)"""
        self.assertEqual(djblets_utils.humanize_list(['a', 'b', 'c', 'd']),
                         'a, b, c, and d')


class TestIndent(unittest.TestCase):
    def test(self):
        """Testing indent filter"""
        self.assertEqual(djblets_utils.indent('foo'), '    foo')
        self.assertEqual(djblets_utils.indent('foo', 3), '   foo')
        self.assertEqual(djblets_utils.indent('foo\nbar'),
                         '    foo\n    bar')


class QuotedEmailTagTest(TagTest):
    def testInvalid(self):
        """Testing quoted_email tag (invalid usage)"""
        self.assertRaises(TemplateSyntaxError,
                          lambda: djblets_email.quoted_email(self.parser,
                              Token(TOKEN_TEXT, 'quoted_email')))


class CondenseTagTest(TagTest):
    def getContentText(self):
        return "foo\nbar\n\n\n\n\n\n\nfoobar!"

    def test_plain(self):
        """Testing condense tag"""
        node = djblets_email.condense(self.parser,
                                      Token(TOKEN_TEXT, 'condense'))
        self.assertEqual(node.render({}), "foo\nbar\n\n\nfoobar!")

    def test_with_max_indents(self):
        """Testing condense tag with custom max_indents"""
        node = djblets_email.condense(self.parser,
                                      Token(TOKEN_TEXT, 'condense 1'))
        self.assertEqual(node.render({}), "foo\nbar\nfoobar!")


class QuoteTextFilterTest(unittest.TestCase):
    def testPlain(self):
        """Testing quote_text filter (default level)"""
        self.assertEqual(djblets_email.quote_text('foo\nbar'),
                         "> foo\n> bar")

    def testLevel2(self):
        """Testing quote_text filter (level 2)"""
        self.assertEqual(djblets_email.quote_text('foo\nbar', 2),
                         "> > foo\n> > bar")


class JSONFieldTests(unittest.TestCase):
    """Unit tests for JSONField."""

    def setUp(self):
        self.field = JSONField()

    def test_dumps_with_json_dict(self):
        """Testing JSONField with dumping a JSON dictionary"""
        result = self.field.dumps({'a': 1})
        self.assertTrue(isinstance(result, six.string_types))
        self.assertEqual(result, '{"a": 1}')

    def test_dumps_with_json_string(self):
        """Testing JSONField with dumping a JSON string"""
        result = self.field.dumps('{"a": 1, "b": 2}')
        self.assertTrue(isinstance(result, six.string_types))
        self.assertEqual(result, '{"a": 1, "b": 2}')

    def test_loading_json_dict(self):
        """Testing JSONField with loading a JSON dictionary"""
        result = self.field.loads('{"a": 1, "b": 2}')
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('a' in result)
        self.assertTrue('b' in result)

    def test_loading_json_broken_dict(self):
        """Testing JSONField with loading a badly serialized JSON dictionary"""
        result = self.field.loads('{u"a": 1, u"b": 2}')
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('a' in result)
        self.assertTrue('b' in result)

    def test_loading_json_array(self):
        """Testing JSONField with loading a JSON array"""
        result = self.field.loads('[1, 2, 3]')
        self.assertTrue(isinstance(result, list))
        self.assertEqual(result, [1, 2, 3])

    def test_loading_string(self):
        """Testing JSONField with loading a stored string"""
        result = self.field.loads('"foo"')
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(result, {})

    def test_loading_broken_string(self):
        """Testing JSONField with loading a broken stored string"""
        result = self.field.loads('u"foo"')
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(result, {})

    def test_loading_python_code(self):
        """Testing JSONField with loading Python code"""
        result = self.field.loads('locals()')
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(result, {})

    def test_validate_with_valid_json_string(self):
        """Testing JSONField with validating a valid JSON string"""
        self.field.run_validators('{"a": 1, "b": 2}')

    def test_validate_with_invalid_json_string(self):
        """Testing JSONField with validating an invalid JSON string"""
        self.assertRaises(ValidationError,
                          lambda: self.field.run_validators('foo'))

    def test_validate_with_json_dict(self):
        """Testing JSONField with validating a JSON dictionary"""
        self.field.run_validators({'a': 1, 'b': 2})


class URLResolverTests(unittest.TestCase):
    def setUp(self):
        self._old_root_urlconf = settings.ROOT_URLCONF

    def tearDown(self):
        settings.ROOT_URLCONF = self._old_root_urlconf

    def test_dynamic_url_resolver(self):
        """Testing DynamicURLResolver"""
        self.dynamic_urls = DynamicURLResolver()

        settings.ROOT_URLCONF = patterns('',
            url(r'^root/', include(patterns('', self.dynamic_urls))),
            url(r'^foo/', self._dummy_view, name='foo'),
        )

        new_patterns = patterns('',
            url(r'^bar/$', self._dummy_view, name='bar'),
            url(r'^baz/$', self._dummy_view, name='baz'),
        )

        # The new patterns shouldn't reverse, just the original "foo".
        reverse('foo')
        self.assertRaises(NoReverseMatch, reverse, 'bar')
        self.assertRaises(NoReverseMatch, reverse, 'baz')

        # Add the new patterns. Now reversing should work.
        self.dynamic_urls.add_patterns(new_patterns)

        reverse('foo')
        reverse('bar')
        reverse('baz')

        # Get rid of the patterns again. We should be back in the original
        # state.
        self.dynamic_urls.remove_patterns(new_patterns)

        reverse('foo')
        self.assertRaises(NoReverseMatch, reverse, 'bar')
        self.assertRaises(NoReverseMatch, reverse, 'baz')

    def _dummy_view(self):
        pass

########NEW FILE########
__FILENAME__ = urlresolvers
from __future__ import unicode_literals
import warnings

from djblets.urls.resolvers import DynamicURLResolver


warnings.warn('djblets.util.urlresolvers is deprecated. See '
              'djblets.urls.resolvers.', DeprecationWarning)


__all__ = ['DynamicURLResolver']

########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals

from django.utils.translation import get_language
from django.views.i18n import javascript_catalog

from djblets.cache.backend import cache_memoize
from djblets.cache.serials import generate_locale_serial


locale_serials = {}


def cached_javascript_catalog(request, domain='djangojs', packages=None):
    """A cached version of javascript_catalog."""
    global locale_serials

    package_str = '_'.join(packages)
    try:
        serial = locale_serials[package_str]
    except KeyError:
        serial = generate_locale_serial(packages)
        locale_serials[package_str] = serial

    return cache_memoize(
        'jsi18n-%s-%s-%s-%d' % (domain, package_str, get_language(), serial),
        lambda: javascript_catalog(request, domain, packages),
        large_data=True,
        compress_large_data=True)

########NEW FILE########
__FILENAME__ = auth
#
# auth.py -- Authentication helpers for webapi
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

import logging

from django.conf import settings
from django.contrib import auth
from django.core.exceptions import ImproperlyConfigured
from django.views.decorators.http import require_POST

from djblets.webapi.core import WebAPIResponse, WebAPIResponseError
from djblets.webapi.decorators import webapi
from djblets.webapi.errors import LOGIN_FAILED


_auth_backends = []


class WebAPIAuthBackend(object):
    """Handles a form of authentication for the web API.

    This can be overridden to provide custom forms of authentication, or to
    support multiple types of authentication.

    More than one authentication backend can be used with the web API. In that
    case, the client can make the determination about which to use.

    Auth backends generally need to only override the `get_credentials`
    method, though more specialized ones may override other methods as well.

    They must also provide `www_auth_scheme` which is a WWW-Authenticate
    scheme value.
    """
    www_auth_scheme = None

    def get_auth_headers(self, request):
        """Returns extra authentication headers for the response."""
        return {}

    def authenticate(self, request):
        """Authenticates a request against this auth backend.

        This will fetch the credentials and attempt an authentication against
        those credentials.

        This function must return None to indicate it should be skipped
        and another backend should be tried, or a tuple indicating the
        success/failure and additional details for the client.

        The tuple is in the form of:

            (is_successful, error_message, headers)

        The error message and headers can be None to use the default error
        message and headers from the LOGIN_FAILED error. In most cases,
        they should be None, unless there are more specific instructions
        needed for authenticating.
        """
        credentials = self.get_credentials(request)

        if not credentials:
            return None

        if isinstance(credentials, dict):
            result = self.login_with_credentials(request, **credentials)
        else:
            assert isinstance(credentials, tuple)
            result = credentials

        return result

    def get_credentials(self, request):
        """Returns credentials provided in the request.

        This returns a dictionary of all credentials necessary for this
        auth backend. By default, this expects 'username' and 'password',
        though more specialized auth backends may provide other information.
        These credentials will be passed to `login_with_credentials`.

        This function must be implemented by the subclass.
        """
        raise NotImplementedError

    def login_with_credentials(self, request, username, password, **kwargs):
        """Logs in against the main authentication backends.

        This takes the provided credentials from the request (as returned by
        `get_credentials`) and attempts a login against the main
        authentication backends used by Django.
        """
        # Don't authenticate if a user is already logged in and the
        # username matches.
        #
        # Note that this does mean that a new password will fail. However,
        # the user is already logged in, and querying the backend for every
        # request is excessive, so it's a tradeoff. The user already has
        # access to the server at this point anyway.
        if (request.user.is_authenticated() and
            request.user.username == username):
            return True, None, None

        log_extra = {
            'request': request,
        }

        logging.debug("Attempting authentication on API for "
                      "user %s" % username,
                      extra=log_extra)
        user = auth.authenticate(username=username, password=password)

        if user and user.is_active:
            auth.login(request, user)

            return True, None, None

        logging.debug("API Login failed. No valid user found.",
                      extra=log_extra)
        auth.logout(request)

        return False, None, None


class WebAPIBasicAuthBackend(WebAPIAuthBackend):
    """Handles HTTP Basic Authentication for the web API."""
    www_auth_scheme = 'Basic realm="Web API"'

    def get_credentials(self, request):
        try:
            realm, encoded_auth = request.META['HTTP_AUTHORIZATION'].split(' ')
            username, password = encoded_auth.decode('base64').split(':', 1)
        except ValueError:
            logging.warning("Failed to parse HTTP_AUTHORIZATION header %s" %
                            request.META['HTTP_AUTHORIZATION'],
                            exc_info=1,
                            extra={'request': request})
            return

        if realm != 'Basic':
            return None

        return {
            'username': username,
            'password': password,
        }


def check_login(request):
    """Checks if a login request was made.

    If the client specifies a HTTP_AUTHORIZATION header, this will attempt
    to authenticate using a supported authentication method.
    """
    if 'HTTP_AUTHORIZATION' in request.META:
        for auth_backend_cls in get_auth_backends():
            result = auth_backend_cls().authenticate(request)

            if result is not None:
                return result

    return None


def get_auth_backends():
    """Returns the list of web API authentication backends.

    This defaults to WebAPIBasicAuthBackend, for HTTP Basic Auth, but can be
    overridden by setting settings.WEB_API_AUTH_BACKENDS to a list of
    class paths.
    """
    global _auth_backends

    if not _auth_backends:
        class_paths = getattr(
            settings, 'WEB_API_AUTH_BACKENDS', [
                'djblets.webapi.auth.WebAPIBasicAuthBackend',
            ])

        _auth_backends = []

        for class_path in class_paths:
            i = class_path.rfind('.')
            module, attr = class_path[:i], class_path[i + 1:]

            try:
                mod = __import__(module, {}, {}, [attr])
            except ImportError as e:
                raise ImproperlyConfigured(
                    'Error importing web API auth backend %s: %s'
                    % (module, e))

            try:
                _auth_backends.append(getattr(mod, attr))
            except AttributeError:
                raise ImproperlyConfigured(
                    'Module "%s" does not define a "%s" class for the web API '
                    'auth backend'
                    % (module, attr))

    return _auth_backends


def reset_auth_backends():
    """Resets the list of authentication backends.

    The list will be recomputed the next time an authentication backend needs
    to be used.
    """
    global _auth_backends

    _auth_backends = []


@require_POST
@webapi
def account_login(request, *args, **kwargs):
    username = request.POST.get('username', None)
    password = request.POST.get('password', None)

    user = auth.authenticate(username=username, password=password)

    if not user or not user.is_active:
        return WebAPIResponseError(request, LOGIN_FAILED)

    auth.login(request, user)

    return WebAPIResponse(request)


@webapi
def account_logout(request, *args, **kwargs):
    auth.logout(request)
    return WebAPIResponse(request)

########NEW FILE########
__FILENAME__ = core
#
# core.py -- Core classes for webapi
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

import json
from xml.sax.saxutils import XMLGenerator

from django.conf import settings
from django.http import HttpResponse
from django.utils import six
from django.utils.encoding import force_unicode
from django.utils.six.moves import cStringIO as StringIO

from djblets.util.http import (get_http_requested_mimetype,
                               get_url_params_except,
                               is_mimetype_a)
from djblets.webapi.errors import INVALID_FORM_DATA


SPECIAL_PARAMS = ('api_format', 'callback', '_method', 'expand')


class WebAPIEncoder(object):
    """
    Encodes an object into a dictionary of fields and values.

    This object is used for both JSON and XML API formats.

    Projects can subclass this to provide representations of their objects.
    To make use of a encoder, add the path to the encoder class to
    the project's settings.WEB_API_ENCODERS list.

    For example:

    WEB_API_ENCODERS = (
        'myproject.webapi.MyEncoder',
    )
    """

    def encode(self, o, *args, **kwargs):
        """
        Encodes an object.

        This is expected to return either a dictionary or a list. If the
        object being encoded is not supported, return None, or call
        the superclass's encode method.
        """
        return None


class JSONEncoderAdapter(json.JSONEncoder):
    """
    Adapts a WebAPIEncoder to be used with json.

    This takes an existing encoder and makes it available to use as a
    json.JSONEncoder. This is used internally when generating JSON from a
    WebAPIEncoder, but can be used in other projects for more specific
    purposes as well.
    """

    def __init__(self, encoder, *args, **kwargs):
        json.JSONEncoder.__init__(self, *args, **kwargs)
        self.encoder = encoder

    def encode(self, o, *args, **kwargs):
        self.encode_args = args
        self.encode_kwargs = kwargs
        return super(JSONEncoderAdapter, self).encode(o)

    def default(self, o):
        """
        Encodes an object using the supplied WebAPIEncoder.

        If the encoder is unable to encode this object, a TypeError is raised.
        """
        result = self.encoder.encode(o, *self.encode_args, **self.encode_kwargs)

        if result is None:
            raise TypeError("%r is not JSON serializable" % (o,))

        return result


class XMLEncoderAdapter(object):
    """
    Adapts a WebAPIEncoder to output XML.

    This takes an existing encoder and adapts it to output a simple XML format.
    """

    def __init__(self, encoder, *args, **kwargs):
        self.encoder = encoder

    def encode(self, o, *args, **kwargs):
        self.level = 0
        self.doIndent = False

        stream = StringIO()
        self.xml = XMLGenerator(stream, settings.DEFAULT_CHARSET)
        self.xml.startDocument()
        self.startElement("rsp")
        self.__encode(o, *args, **kwargs)
        self.endElement("rsp")
        self.xml.endDocument()
        self.xml = None

        return stream.getvalue()

    def __encode(self, o, *args, **kwargs):
        if isinstance(o, dict):
            for key, value in six.iteritems(o):
                attrs = {}

                if isinstance(key, six.integer_types):
                    attrs['value'] = str(key)
                    key = 'int'

                self.startElement(key, attrs)
                self.__encode(value, *args, **kwargs)
                self.endElement(key)
        elif isinstance(o, (tuple, list)):
            self.startElement("array")

            for i in o:
                self.startElement("item")
                self.__encode(i, *args, **kwargs)
                self.endElement("item")

            self.endElement("array")
        elif isinstance(o, six.string_types):
            self.text(o)
        elif isinstance(o, six.integer_types):
            self.text("%d" % o)
        elif isinstance(o, bool):
            if o:
                self.text("True")
            else:
                self.text("False")
        elif o is None:
            pass
        else:
            result = self.encoder.encode(o, *args, **kwargs)

            if result is None:
                raise TypeError("%r is not XML serializable" % (o,))

            return self.__encode(result, *args, **kwargs)

    def startElement(self, name, attrs={}):
        self.addIndent()
        self.xml.startElement(name, attrs)
        self.level += 1
        self.doIndent = True

    def endElement(self, name):
        self.level -= 1
        self.addIndent()
        self.xml.endElement(name)
        self.doIndent = True

    def text(self, value):
        self.xml.characters(value)
        self.doIndent = False

    def addIndent(self):
        if self.doIndent:
            self.xml.ignorableWhitespace('\n' + ' ' * self.level)


class WebAPIResponse(HttpResponse):
    """
    An API response, formatted for the desired file format.
    """
    supported_mimetypes = [
        'application/json',
        'application/xml',
    ]

    def __init__(self, request, obj={}, stat='ok', api_format=None,
                 status=200, headers={}, encoders=[],
                 encoder_kwargs={}, mimetype=None, supported_mimetypes=None):
        if not api_format:
            if request.method == 'GET':
                api_format = request.GET.get('api_format', None)
            else:
                api_format = request.POST.get('api_format', None)

        if not supported_mimetypes:
            supported_mimetypes = self.supported_mimetypes

        if not mimetype:
            if not api_format:
                mimetype = get_http_requested_mimetype(request,
                                                       supported_mimetypes)
            elif api_format == "json":
                mimetype = 'application/json'
            elif api_format == "xml":
                mimetype = 'application/xml'

        if not mimetype:
            self.status_code = 400
            self.content_set = True
            return

        if not request.is_ajax() and request.FILES:
            # When uploading a file using AJAX to a webapi view,
            # we must set the mimetype to text/plain. If we use
            # application/json instead, the browser will ask the user
            # to save the file. It's not great, but it's what we must do.
            mimetype = 'text/plain'

        super(WebAPIResponse, self).__init__(content_type=mimetype,
                                             status=status)
        self.request = request
        self.callback = request.GET.get('callback', None)
        self.api_data = {'stat': stat}
        self.api_data.update(obj)
        self.content_set = False
        self.mimetype = mimetype
        self.encoders = encoders or get_registered_encoders()
        self.encoder_kwargs = encoder_kwargs

        for header, value in six.iteritems(headers):
            self[header] = value

        # Prevent IE8 from trying to download some AJAX responses as if they
        # were files.
        self['X-Content-Type-Options'] = 'nosniff'

    def _get_content(self):
        """
        Returns the API response content in the appropriate format.

        This is an overridden version of HttpResponse._get_content that
        generates the resulting content when requested, rather than
        generating it up-front in the constructor. This is used so that
        the @webapi decorator can set the appropriate API format before
        the content is generated, but after the response is created.
        """
        class MultiEncoder(WebAPIEncoder):
            def __init__(self, encoders):
                self.encoders = encoders

            def encode(self, *args, **kwargs):
                for encoder in self.encoders:
                    result = encoder.encode(*args, **kwargs)

                    if result is not None:
                        return result

                return None

        if not self.content_set:
            adapter = None
            encoder = MultiEncoder(self.encoders)

            # See the note above about the check for text/plain.
            if (self.mimetype == 'text/plain' or
                is_mimetype_a(self.mimetype, 'application/json')):
                adapter = JSONEncoderAdapter(encoder)
            elif is_mimetype_a(self.mimetype, "application/xml"):
                adapter = XMLEncoderAdapter(encoder)
            else:
                assert False

            content = adapter.encode(self.api_data, request=self.request,
                                     **self.encoder_kwargs)

            if self.callback != None:
                content = "%s(%s);" % (self.callback, content)

            self.content = content
            self.content_set = True

        return super(WebAPIResponse, self).content

    def _set_content(self, value):
        HttpResponse.content.fset(self, value)

    content = property(_get_content, _set_content)


class WebAPIResponsePaginated(WebAPIResponse):
    """
    A response containing a list of results with pagination.

    This accepts the following parameters to the URL:

    * start - The index of the first item (0-based index).
    * max-results - The maximum number of results to return in the request.
    """
    def __init__(self, request, queryset, results_key="results",
                 prev_key="prev", next_key="next",
                 total_results_key="total_results",
                 default_max_results=25, max_results_cap=200,
                 serialize_object_func=None,
                 extra_data={}, *args, **kwargs):
        try:
            start = max(int(request.GET.get('start', 0)), 0)
        except ValueError:
            start = 0

        try:
            max_results = \
                min(int(request.GET.get('max-results', default_max_results)),
                    max_results_cap)
        except ValueError:
            max_results = default_max_results

        results = queryset[start:start + max_results]

        total_results = queryset.count()

        if total_results == 0:
            results = []
        elif serialize_object_func:
            results = [serialize_object_func(obj)
                       for obj in results]
        else:
            results = list(results)

        data = {
            results_key: results,
            total_results_key: total_results,
        }
        data.update(extra_data)

        full_path = request.build_absolute_uri(request.path)

        query_parameters = get_url_params_except(request.GET,
                                                 'start', 'max-results')
        if query_parameters:
            query_parameters = '&' + query_parameters

        if start > 0:
            data['links'][prev_key] = {
                'method': 'GET',
                'href': '%s?start=%s&max-results=%s%s' %
                        (full_path, max(start - max_results, 0), max_results,
                         query_parameters),
            }

        if start + len(results) < total_results:
            data['links'][next_key] = {
                'method': 'GET',
                'href': '%s?start=%s&max-results=%s%s' %
                        (full_path, start + max_results, max_results,
                         query_parameters),
            }

        WebAPIResponse.__init__(self, request, obj=data, *args, **kwargs)


class WebAPIResponseError(WebAPIResponse):
    """
    A general error response, containing an error code and a human-readable
    message.
    """
    def __init__(self, request, err, extra_params={}, headers={},
                 *args, **kwargs):
        errdata = {
            'err': {
                'code': err.code,
                'msg': err.msg
            }
        }
        errdata.update(extra_params)

        headers = headers.copy()

        if callable(err.headers):
            headers.update(err.headers(request))
        else:
            headers.update(err.headers)

        WebAPIResponse.__init__(self, request, obj=errdata, stat="fail",
                                status=err.http_status, headers=headers,
                                *args, **kwargs)


class WebAPIResponseFormError(WebAPIResponseError):
    """
    An error response class designed to return all errors from a form class.
    """
    def __init__(self, request, form, *args, **kwargs):
        fields = {}

        for field in form.errors:
            fields[field] = [force_unicode(e) for e in form.errors[field]]

        WebAPIResponseError.__init__(self, request, INVALID_FORM_DATA, {
            'fields': fields
        }, *args, **kwargs)


__registered_encoders = None

def get_registered_encoders():
    """
    Returns a list of registered Web API encoders.
    """
    global __registered_encoders

    if __registered_encoders is None:
        __registered_encoders = []

        encoders = getattr(settings, 'WEB_API_ENCODERS',
                           ['djblets.webapi.encoders.BasicAPIEncoder'])

        for encoder in encoders:
            encoder_path = encoder.split('.')
            if len(encoder_path) > 1:
                encoder_module_name = '.'.join(encoder_path[:-1])
            else:
                encoder_module_name = '.'

            encoder_module = __import__(encoder_module_name, {}, {},
                                        encoder_path[-1])
            encoder_class = getattr(encoder_module, encoder_path[-1])
            __registered_encoders.append(encoder_class())

    return __registered_encoders


# Backwards-compatibility
#
# This must be done after the classes in order to avoid a
# circular import problem.
from djblets.webapi.encoders import BasicAPIEncoder

########NEW FILE########
__FILENAME__ = decorators
#
# decorators.py -- Decorators used for webapi views
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from django.http import HttpRequest
from django.utils import six

from djblets.webapi.core import SPECIAL_PARAMS
from djblets.webapi.errors import (NOT_LOGGED_IN, PERMISSION_DENIED,
                                   INVALID_FORM_DATA)


def _find_httprequest(args):
    if isinstance(args[0], HttpRequest):
        request = args[0]
    else:
        # This should be in a class then.
        assert len(args) > 1
        request = args[1]
        assert isinstance(request, HttpRequest)

    return request


def copy_webapi_decorator_data(from_func, to_func):
    """Copies and merges data from one decorated function to another.

    This will copy over the standard function information (name, docs,
    and dictionary data), but will also handle intelligently merging
    together data set by webapi decorators, such as the list of
    possible errors.
    """
    had_errors = (hasattr(to_func, 'response_errors') or
                  hasattr(from_func, 'response_errors'))
    had_fields = (hasattr(to_func, 'required_fields') or
                  hasattr(from_func, 'required_fields'))

    from_errors = getattr(from_func, 'response_errors', set())
    to_errors = getattr(to_func, 'response_errors', set())
    from_required_fields = getattr(from_func, 'required_fields', {}).copy()
    from_optional_fields = getattr(from_func, 'optional_fields', {}).copy()
    to_required_fields = getattr(to_func, 'required_fields', {}).copy()
    to_optional_fields = getattr(to_func, 'optional_fields', {}).copy()

    to_func.__name__ = from_func.__name__
    to_func.__doc__ = from_func.__doc__
    to_func.__dict__.update(from_func.__dict__)

    # Only copy if one of the two functions had this already.
    if had_errors:
        to_func.response_errors = to_errors.union(from_errors)

    if had_fields:
        to_func.required_fields = from_required_fields
        to_func.required_fields.update(to_required_fields)
        to_func.optional_fields = from_optional_fields
        to_func.optional_fields.update(to_optional_fields)

    return to_func


def webapi_decorator(decorator):
    """Decorator for simple webapi decorators.

    This is meant to be used for other webapi decorators in order to
    intelligently preserve information, like the possible response
    errors. It handles merging lists of errors and other information
    instead of overwriting one list with another, as simple_decorator
    would do.
    """
    return copy_webapi_decorator_data(
        decorator,
        lambda f: copy_webapi_decorator_data(f, decorator(f)))


@webapi_decorator
def webapi(view_func):
    """Indicates that a view is a Web API handler."""
    return view_func


def webapi_response_errors(*errors):
    """Specifies the type of errors that the response may return.

    This can be used for generating documentation or schemas that cover
    the possible error responses of methods on a resource.
    """
    @webapi_decorator
    def _dec(view_func):
        def _call(*args, **kwargs):
            return view_func(*args, **kwargs)

        _call.response_errors = set(errors)

        return _call

    return _dec


@webapi_decorator
def webapi_login_required(view_func):
    """
    Checks that the user is logged in before invoking the view. If the user
    is not logged in, a NOT_LOGGED_IN error (HTTP 401 Unauthorized) is
    returned.
    """
    @webapi_response_errors(NOT_LOGGED_IN)
    def _checklogin(*args, **kwargs):
        request = _find_httprequest(args)

        if request.user.is_authenticated():
            return view_func(*args, **kwargs)
        else:
            return NOT_LOGGED_IN

    _checklogin.login_required = True

    return _checklogin


def webapi_permission_required(perm):
    """
    Checks that the user is logged in and has the appropriate permissions
    to access this view. A PERMISSION_DENIED error is returned if the user
    does not have the proper permissions.
    """
    @webapi_decorator
    def _dec(view_func):
        @webapi_response_errors(NOT_LOGGED_IN, PERMISSION_DENIED)
        def _checkpermissions(*args, **kwargs):
            request = _find_httprequest(args)

            if not request.user.is_authenticated():
                response = NOT_LOGGED_IN
            elif not request.user.has_perm(perm):
                response = PERMISSION_DENIED
            else:
                response = view_func(*args, **kwargs)

            return response

        return _checkpermissions

    return _dec


def webapi_request_fields(required={}, optional={}, allow_unknown=False):
    """Validates incoming fields for a request.

    This is a helpful decorator for ensuring that the fields in the request
    match what the caller expects.

    If any field is set in the request that is not in either ``required``
    or ``optional`` and ``allow_unknown`` is True, the response will be an
    INVALID_FORM_DATA error. The exceptions are the special fields
    ``method`` and ``callback``.

    If any field in ``required`` is not passed in the request, these will
    also be listed in the INVALID_FORM_DATA response.

    The ``required`` and ``optional`` parameters are dictionaries
    mapping field name to an info dictionary, which contains the following
    keys:

      * ``type`` - The data type for the field.
      * ```description`` - A description of the field.

    For example:

        @webapi_request_fields(required={
            'name': {
                'type': str,
                'description': 'The name of the object',
            }
        })
    """
    @webapi_decorator
    def _dec(view_func):
        @webapi_response_errors(INVALID_FORM_DATA)
        def _validate(*args, **kwargs):
            request = _find_httprequest(args)

            if request.method == 'GET':
                request_fields = request.GET
            else:
                request_fields = request.POST

            extra_fields = {}
            invalid_fields = {}
            supported_fields = required.copy()
            supported_fields.update(optional)

            for field_name, value in six.iteritems(request_fields):
                if field_name in SPECIAL_PARAMS:
                    # These are special names and can be ignored.
                    continue

                if field_name not in supported_fields:
                    if allow_unknown:
                        extra_fields[field_name] = value
                    else:
                        invalid_fields[field_name] = ['Field is not supported']

            for field_name, info in six.iteritems(required):
                temp_fields = request_fields

                if info['type'] == file:
                    temp_fields = request.FILES

                if temp_fields.get(field_name, None) is None:
                    invalid_fields[field_name] = ['This field is required']

            new_kwargs = kwargs.copy()
            new_kwargs['extra_fields'] = extra_fields

            for field_name, info in six.iteritems(supported_fields):
                if isinstance(info['type'], file):
                    continue

                value = request_fields.get(field_name, None)

                if value is not None:
                    if type(info['type']) in (list, tuple):
                        # This is a multiple-choice. Make sure the value is
                        # valid.
                        choices = info['type']

                        if value not in choices:
                            invalid_fields[field_name] = [
                                '"%s" is not a valid value. Valid values '
                                'are: %s' % (
                                    value,
                                    ', '.join(['"%s"' % choice
                                                for choice in choices])
                                )
                            ]
                    else:
                        try:
                            if issubclass(info['type'], bool):
                                value = value in (1, "1", True, "True", "true")
                            elif issubclass(info['type'], int):
                                try:
                                    value = int(value)
                                except ValueError:
                                    invalid_fields[field_name] = [
                                        '"%s" is not an integer' % value
                                    ]
                        except TypeError:
                            # The field isn't a class type. This is a
                            # coding error on the developer's side.
                            raise TypeError('"%s" is not a valid field type' %
                                            info['type'])

                    new_kwargs[field_name] = value

            if invalid_fields:
                return INVALID_FORM_DATA, {
                    'fields': invalid_fields,
                }

            return view_func(*args, **new_kwargs)

        _validate.required_fields = required.copy()
        _validate.optional_fields = optional.copy()

        if hasattr(view_func, 'required_fields'):
            _validate.required_fields.update(view_func.required_fields)

        if hasattr(view_func, 'optional_fields'):
            _validate.optional_fields.update(view_func.optional_fields)

        return _validate

    return _dec

########NEW FILE########
__FILENAME__ = encoders
from __future__ import unicode_literals

from django.contrib.auth.models import User, Group
from django.db.models.query import QuerySet

from djblets.util.serializers import DjbletsJSONEncoder
from djblets.webapi.core import WebAPIEncoder


class BasicAPIEncoder(WebAPIEncoder):
    """
    A basic encoder that encodes dates, times, QuerySets, Users, and Groups.
    """
    def encode(self, o, *args, **kwargs):
        if isinstance(o, QuerySet):
            return list(o)
        elif isinstance(o, User):
            return {
                'id': o.id,
                'username': o.username,
                'first_name': o.first_name,
                'last_name': o.last_name,
                'fullname': o.get_full_name(),
                'email': o.email,
                'url': o.get_absolute_url(),
            }
        elif isinstance(o, Group):
            return {
                'id': o.id,
                'name': o.name,
            }
        else:
            try:
                return DjbletsJSONEncoder().default(o)
            except TypeError:
                return None


class ResourceAPIEncoder(WebAPIEncoder):
    """An encoder that encodes objects based on registered resources."""
    def encode(self, o, *args, **kwargs):
        if isinstance(o, QuerySet):
            return list(o)
        else:
            calling_resource = kwargs.pop('calling_resource', None)

            if calling_resource:
                serializer = calling_resource.get_serializer_for_object(o)
            else:
                from djblets.webapi.resources import get_resource_for_object

                serializer = get_resource_for_object(o)

            if serializer:
                return serializer.serialize_object(o, *args, **kwargs)
            else:
                try:
                    return DjbletsJSONEncoder().default(o)
                except TypeError:
                    return None

########NEW FILE########
__FILENAME__ = errors
#
# errors.py -- Error classes and codes for webapi
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals


class WebAPIError(object):
    """
    An API error, containing an error code and human readable message.
    """
    def __init__(self, code, msg, http_status=400, headers={}):
        self.code = code
        self.msg = msg
        self.http_status = http_status
        self.headers = headers

    def __repr__(self):
        return '<API Error %d, HTTP %d: %s>' % (self.code, self.http_status,
                                                self.msg)

    def with_overrides(self, msg=None, headers=None):
        """Overrides the default message and/or headers for an error."""
        if headers is None:
            headers = self.headers

        return WebAPIError(self.code, msg or self.msg, self.http_status,
                           headers)

    def with_message(self, msg):
        """
        Overrides the default message for a WebAPIError with something
        more context specific.

        Example:
        return ENABLE_EXTENSION_FAILED.with_message('some error message')
        """
        return self.with_overrides(msg)


def _get_auth_headers(request):
    from djblets.webapi.auth import get_auth_backends

    headers = {}
    www_auth_schemes = []

    for auth_backend_cls in get_auth_backends():
        auth_backend = auth_backend_cls()

        if auth_backend.www_auth_scheme:
            www_auth_schemes.append(auth_backend.www_auth_scheme)

        headers.update(auth_backend.get_auth_headers(request))

    if www_auth_schemes:
        headers['WWW-Authenticate'] = ', '.join(www_auth_schemes)

    return headers


#
# Standard error messages
#
NO_ERROR                  = WebAPIError(0,
                                        "If you see this, yell at the "
                                        "developers")
SERVICE_NOT_CONFIGURED    = WebAPIError(1,
                                        "The web service has not yet "
                                        "been configured",
                                        http_status=503)

DOES_NOT_EXIST            = WebAPIError(100,
                                        "Object does not exist",
                                        http_status=404)
PERMISSION_DENIED         = WebAPIError(101,
                                        "You don't have permission for this",
                                        http_status=403)
INVALID_ATTRIBUTE         = WebAPIError(102,
                                        "Invalid attribute",
                                        http_status=400)
NOT_LOGGED_IN             = WebAPIError(103,
                                        "You are not logged in",
                                        http_status=401,
                                        headers=_get_auth_headers)
LOGIN_FAILED              = WebAPIError(104,
                                        "The username or password was "
                                        "not correct",
                                        http_status=401,
                                        headers=_get_auth_headers)
INVALID_FORM_DATA         = WebAPIError(105,
                                        "One or more fields had errors",
                                        http_status=400)
MISSING_ATTRIBUTE         = WebAPIError(106,
                                        "Missing value for the attribute",
                                        http_status=400)
ENABLE_EXTENSION_FAILED   = WebAPIError(107,
                                        "There was a problem enabling "
                                        "the extension",
                                        http_status=500) # 500 Internal Server
                                                         #     Error
DISABLE_EXTENSION_FAILED  = WebAPIError(108,
                                        "There was a problem disabling "
                                        "the extension",
                                        http_status=500) # 500 Internal Server
                                                         #     Error
EXTENSION_INSTALLED       = WebAPIError(109,
                                        "This extension has already been "
                                        "installed.",
                                        http_status=409)
INSTALL_EXTENSION_FAILED  = WebAPIError(110,
                                        "An error occurred while "
                                        "installing the extension",
                                        http_status=409)

########NEW FILE########
__FILENAME__ = resources
from __future__ import unicode_literals

from hashlib import sha1

from django.conf.urls import include, patterns, url
from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.fields.related import (
    ManyRelatedObjectsDescriptor,
    ReverseManyRelatedObjectsDescriptor)
from django.db.models.query import QuerySet
from django.http import (HttpResponseNotAllowed, HttpResponse,
                         HttpResponseNotModified)
from django.utils import six
from django.views.decorators.vary import vary_on_headers

from djblets.util.decorators import augment_method_from
from djblets.util.http import (get_modified_since, etag_if_none_match,
                               set_last_modified, set_etag,
                               get_http_requested_mimetype)
from djblets.urls.patterns import never_cache_patterns
from djblets.webapi.auth import check_login
from djblets.webapi.core import (WebAPIResponse,
                                 WebAPIResponseError,
                                 WebAPIResponsePaginated,
                                 SPECIAL_PARAMS)
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST,
                                   LOGIN_FAILED,
                                   NOT_LOGGED_IN,
                                   PERMISSION_DENIED,
                                   WebAPIError)


_model_to_resources = {}
_name_to_resources = {}
_class_to_resources = {}


class WebAPIResource(object):
    """A resource living at a specific URL, representing an object or list
    of objects.

    A WebAPIResource is a RESTful resource living at a specific URL. It
    can represent either an object or a list of objects, and can respond
    to various HTTP methods (GET, POST, PUT, DELETE).

    Subclasses are expected to override functions and variables in order to
    provide specific functionality, such as modifying the resource or
    creating a new resource.


    Representing Models
    -------------------

    Most resources will have ``model`` set to a Model subclass, and
    ``fields`` set to list the fields that would be shown when

    Each resource will also include a ``link`` dictionary that maps
    a key (resource name or action) to a dictionary containing the URL
    (``href``) and the HTTP method that's to be used for that URL
    (``method``). This will include a special ``self`` key that links to
    that resource's actual location.

    An example of this might be::

       'links': {
           'self': {
               'method': 'GET',
               'href': '/path/to/this/resource/'
           },
           'update': {
               'method': 'PUT',
               'href': '/path/to/this/resource/'
           }
       }

    Resources associated with a model may want to override the ``get_queryset``
    function to return a queryset with a more specific query.

    By default, an individual object's key name in the resulting payloads
    will be set to the lowercase class name of the object, and the plural
    version used for lists will be the same but with 's' appended to it. This
    can be overridden by setting ``name`` and ``name_plural``.


    Matching Objects
    ----------------

    Objects are generally queried by their numeric object ID and mapping that
    to the object's ``pk`` attribute. For this to work, the ``uri_object_key``
    attribute must be set to the name in the regex for the URL that will
    be captured and passed to the handlers for this resource. The
    ``uri_object_key_regex`` attribute can be overridden to specify the
    regex for matching this ID (useful for capturing names instead of
    numeric IDs) and ``model_object_key`` can be overridden to specify the
    model field that will be matched against.


    Parents and URLs
    ----------------

    Resources typically have a parent resource, of which the resource is
    a subclass. Resources will often list their children (by setting
    ``list_child_resources`` and ``item_child_resources`` in a subclass
    to lists of other WebAPIResource instances). This makes the entire tree
    navigatable. The URLs are built up automatically, so long as the result
    of get_url_patterns() from top-level resources are added to the Django
    url_patterns variables commonly found in urls.py.

    Child objects should set the ``model_parent_key`` variable to the
    field name of the object's parent in the resource hierarchy. This
    allows WebAPIResource to build a URL with the right values filled in in
    order to make a URL to this object.

    If the parent is dynamic based on certain conditions, then the
    ``get_parent_object`` function can be overridden instead.


    Object Serialization
    --------------------

    Objects are serialized through the ``serialize_object`` function.
    This rarely needs to be overridden, but can be called from WebAPIEncoders
    in order to serialize the object. By default, this will loop through
    the ``fields`` variable and add each value to the resulting dictionary.

    Values can be specially serialized by creating functions in the form of
    ``serialize_<fieldname>_field``. These functions take the object being
    serialized and must return a value that can be fed to the encoder.

    By default, resources will not necessarily serialize the objects in their
    own payloads. Instead, they will look up the registered resource instance
    for the model using ``get_resource_for_object``, and serialize with that.
    A resource can override that logic for its own payloads by providing
    a custom ``get_serializer_for_object`` method.


    Handling Requests
    -----------------

    WebAPIResource calls the following functions based on the type of
    HTTP request:

      * ``get`` - HTTP GET for individual objects.
      * ``get_list`` - HTTP GET for resources representing lists of objects.
      * ``create`` - HTTP POST on resources representing lists of objects.
                     This is expected to return the object and an HTTP
                     status of 201 CREATED, on success.
      * ``update`` - HTTP PUT on individual objects to modify their state
                     based on full or partial data.
      * ``delete`` - HTTP DELETE on an individual object. This is expected
                     to return a status of HTTP 204 No Content on success.
                     The default implementation just deletes the object.

    Any function that is not implemented will return an HTTP 405 Method
    Not Allowed. Functions that have handlers provided should set
    ``allowed_methods`` to a tuple of the HTTP methods allowed. For example::

        allowed_methods = ('GET', POST', 'DELETE')

    These functions are passed an HTTPRequest and a list of arguments
    captured in the URL and are expected to return standard HTTP response
    codes, along with a payload in most cases. The functions can return any of:

      * A HttpResponse
      * A WebAPIResponse
      * A WebAPIError
      * A tuple of (WebAPIError, Payload)
      * A tuple of (WebAPIError, Payload Dictionary, Headers Dictionary)
      * A tuple of (HTTP status, Payload)
      * A tuple of (HTTP status, Payload Dictionary, Headers Dictionary)

    In general, it's best to return one of the tuples containing an HTTP
    status, and not any object, but there are cases where an object is
    necessary.

    Commonly, a handler will need to fetch parent objects in order to make
    some request. The values for all captured object IDs in the URL are passed
    to the handler, but it's best to not use these directly. Instead, the
    handler should accept a **kwargs parameter, and then call the parent
    resource's ``get_object`` function and pass in that **kwargs. For example::

      def create(self, request, *args, **kwargs):
          try:
              my_parent = myParentResource.get_object(request, *args, **kwargs)
          except ObjectDoesNotExist:
              return DOES_NOT_EXIST


    Expanding Resources
    -------------------

    The resulting data returned from a resource will by default provide
    links to child resources. If a lot of aggregated data is needed, then
    instead of making several queries the caller can use the ``?expand=``
    parameter. This takes a comma-separated list of keys in the resource
    names found in the payloads and expands them instead of linking to them.

    This can result in really large downloads, if deep expansion is made
    when accessing lists of resources. However, it can also result in less
    strain on the server if used correctly.


    Faking HTTP Methods
    -------------------

    There are clients that can't actually request anything but HTTP POST
    and HTTP GET. An HTML form is one such example, and Flash applications
    are another. For these cases, an HTTP POST can be made, with a special
    ``_method`` parameter passed to the URL. This can be set to the HTTP
    method that's desired. For example, ``PUT`` or ``DELETE``.


    Permissions
    -----------

    Unless overridden, an object cannot be modified, created, or deleted
    if the user is not logged in and if an appropriate permission function
    does not return True. These permission functions are:

    * ``has_access_permissions`` - Used for HTTP GET calls. Returns True
                                   by default.
    * ``has_modify_permissions`` - Used for HTTP POST or PUT calls, if
                                   called by the subclass. Returns False
                                   by default.
    * ``has_delete_permissions`` - Used for HTTP DELETE permissions. Returns
                                   False by default.


    Browser Caching
    ---------------

    To improve performance, resources can make use of browser-side caching.
    If a resource is accessed more than once, and it hasn't changed,
    the resource will return an :http:`304`.

    There are two methods for caching: Last Modified headers, and ETags.

    Last Modified
    ~~~~~~~~~~~~~

    A resource can set ``last_modified_field`` to the name of a DateTimeField
    in the model. This will be used to determine if the resource has changed
    since the last request.

    If a bit more work is needed, the ``get_last_modified`` function
    can instead be overridden. This takes the request and object and is
    expected to return a timestamp.

    ETags
    ~~~~~

    ETags are arbitrary, unique strings that represent the state of a resource.
    There should only ever be one possible ETag per state of the resource.

    A resource can set the ``etag_field`` to the name of a field in the
    model.

    If no field really works, ``autogenerate_etags`` can be set. This will
    generate a suitable ETag based on all fields in the resource. For this
    to work correctly, no custom data can be added to the payload, and
    links cannot be dynamic.

    If more work is needed, the ``get_etag`` function can instead be
    overridden. It will take a request and object and is expected to return
    a string.


    Mimetypes
    ---------

    Resources should list the possible mimetypes they'll accept and return in
    :py:attr:`allowed_mimetypes`. Each entry in the list is a dictionary
    with 'list' containing a mimetype for resource lists, and 'item'
    containing the equivalent mimetype for a resource item. In the case of
    a singleton, 'item' will contain the mimetype. If the mimetype is not
    applicable to one of the resource forms, the corresponding entry
    should contain None.

    Entries in these lists are checked against the mimetypes requested in the
    HTTP Accept header, and, by default, the returned data will be sent in
    that mimetype. If the requested data is a resource list, the corresponding
    resource item mimetype will also be sent in the 'Item-Content-Type'
    header.

    By default, this lists will have entries with both 'list' and 'item'
    containing :mimetype:`application/json` and :mimetype:`application/xml`,
    along with any resource-specific mimetypes, if used.

    Resource-specific Mimetypes
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    In order to better identify resources, resources can provide their
    own custom mimetypes. These are known as vendor-specific mimetypes, and
    are subsets of :mimetype:`application/json` and :mimetype:`application/xml`.
    An example would be :mimetype:`application/vnd.example.com.myresource+json`.

    To enable this on a resource, set :py:attr:`mimetype_vendor` to the
    vendor name. This is often a domain name. For example::

        mimetype_vendor = 'djblets.org'

    The resource names will then be generated based on the name of the
    resource (:py:attr:`name_plural` for resource lists, :py:attr:`name` for
    resource items and singletons). These can be customized as well::

        mimetype_list_resource_name = 'myresource-list'
        mimetype_item_resource_name = 'myresource'

    When these are used, any client requesting either the resource-specific
    mimetype or the more generic mimetype will by default receive a payload
    with the resource-specific mimetype. This makes it easier to identify
    the schema of resource data without hard-coding any knowledge of the
    URI.
    """

    # Configuration
    model = None
    fields = {}
    uri_object_key_regex = r'[0-9]+'
    uri_object_key = None
    model_object_key = 'pk'
    model_parent_key = None
    last_modified_field = None
    etag_field = None
    autogenerate_etags = False
    singleton = False
    list_child_resources = []
    item_child_resources = []
    allowed_methods = ('GET',)
    mimetype_vendor = None
    mimetype_list_resource_name = None
    mimetype_item_resource_name = None
    allowed_mimetypes = [
        {'list': mime, 'item': mime}
        for mime in WebAPIResponse.supported_mimetypes
    ]

    # State
    method_mapping = {
        'GET': 'get',
        'POST': 'post',
        'PUT': 'put',
        'DELETE': 'delete',
    }

    _parent_resource = None
    _mimetypes_cache = None

    def __init__(self):
        _name_to_resources[self.name] = self
        _name_to_resources[self.name_plural] = self
        _class_to_resources[self.__class__] = self

        # Mark this class, and any subclasses, to be Web API handlers
        self.is_webapi_handler = True

        # Copy this list, because otherwise we may modify the class-level
        # version of it.
        self.allowed_mimetypes = list(self.allowed_mimetypes)

        if self.mimetype_vendor:
            # Generate list and item resource-specific mimetypes
            # for each supported mimetype, and add them as a pair to the
            # allowed mimetypes.
            for mimetype_pair in self.allowed_mimetypes:
                vend_mimetype_pair = {
                    'list': None,
                    'item': None,
                }

                for key, is_list in [('list', True), ('item', False)]:
                    if (key in mimetype_pair and
                        (mimetype_pair[key] in
                         WebAPIResponse.supported_mimetypes)):
                        vend_mimetype_pair[key] = \
                            self._build_resource_mimetype(mimetype_pair[key],
                                                          is_list)

                if vend_mimetype_pair['list'] or vend_mimetype_pair['item']:
                    self.allowed_mimetypes.append(vend_mimetype_pair)

    @vary_on_headers('Accept', 'Cookie')
    def __call__(self, request, api_format=None, *args, **kwargs):
        """Invokes the correct HTTP handler based on the type of request."""
        auth_result = check_login(request)

        if isinstance(auth_result, tuple):
            auth_success, auth_message, auth_headers = auth_result

            if not auth_success:
                err = LOGIN_FAILED

                if auth_message:
                    err = err.with_message(auth_message)

                return WebAPIResponseError(
                    request,
                    err=err,
                    headers=auth_headers or {},
                    api_format=api_format,
                    mimetype=self._build_error_mimetype(request))

        method = request.method

        if method == 'POST':
            # Not all clients can do anything other than GET or POST.
            # So, in the case of POST, we allow overriding the method
            # used.
            method = request.POST.get('_method', kwargs.get('_method', method))
        elif method == 'PUT':
            # Normalize the PUT data so we can get to it.
            # This is due to Django's treatment of PUT vs. POST. They claim
            # that PUT, unlike POST, is not necessarily represented as form
            # data, so they do not parse it. However, that gives us no clean way
            # of accessing the data. So we pretend it's POST for a second in
            # order to parse.
            #
            # This must be done only for legitimate PUT requests, not faked
            # ones using ?method=PUT.
            try:
                request.method = 'POST'
                request._load_post_and_files()
                request.method = 'PUT'
            except AttributeError:
                request.META['REQUEST_METHOD'] = 'POST'
                request._load_post_and_files()
                request.META['REQUEST_METHOD'] = 'PUT'

        request._djblets_webapi_method = method
        request._djblets_webapi_kwargs = kwargs
        request.PUT = request.POST

        if method in self.allowed_methods:
            if (method == "GET" and
                not self.singleton and
                (self.uri_object_key is None or
                 self.uri_object_key not in kwargs)):
                view = self.get_list
            else:
                view = getattr(self, self.method_mapping.get(method, None))
        else:
            view = None

        if view and six.callable(view):
            result = view(request, api_format=api_format, *args, **kwargs)

            if isinstance(result, WebAPIResponse):
                return result
            elif isinstance(result, WebAPIError):
                return WebAPIResponseError(
                    request,
                    err=result,
                    api_format=api_format,
                    mimetype=self._build_error_mimetype(request))
            elif isinstance(result, tuple):
                headers = {}

                if method == 'GET':
                    request_params = request.GET
                else:
                    request_params = request.POST

                if len(result) == 3:
                    headers = result[2]

                if 'Location' in headers:
                    extra_querystr = '&'.join([
                        '%s=%s' % (param, request_params[param])
                        for param in SPECIAL_PARAMS
                        if param in request_params
                    ])

                    if extra_querystr:
                        if '?' in headers['Location']:
                            headers['Location'] += '&' + extra_querystr
                        else:
                            headers['Location'] += '?' + extra_querystr

                if isinstance(result[0], WebAPIError):
                    return WebAPIResponseError(
                        request,
                        err=result[0],
                        headers=headers,
                        extra_params=result[1],
                        api_format=api_format,
                        mimetype=self._build_error_mimetype(request))
                else:
                    response_args = self.build_response_args(request)
                    headers.update(response_args.pop('headers', {}))
                    return WebAPIResponse(
                        request,
                        status=result[0],
                        obj=result[1],
                        headers=headers,
                        api_format=api_format,
                        encoder_kwargs=dict({
                            'calling_resource': self,
                        }, **kwargs),
                        **response_args)
            elif isinstance(result, HttpResponse):
                return result
            else:
                raise AssertionError(result)
        else:
            return HttpResponseNotAllowed(self.allowed_methods)

    @property
    def __name__(self):
        return self.__class__.__name__

    @property
    def name(self):
        """Returns the name of the object, used for keys in the payloads."""
        if not hasattr(self, '_name'):
            if self.model:
                self._name = self.model.__name__.lower()
            else:
                self._name = self.__name__.lower()

        return self._name

    @property
    def name_plural(self):
        """Returns the plural name of the object, used for lists."""
        if not hasattr(self, '_name_plural'):
            if self.singleton:
                self._name_plural = self.name
            else:
                self._name_plural = self.name + 's'

        return self._name_plural

    @property
    def item_result_key(self):
        """Returns the key for single objects in the payload."""
        return self.name

    @property
    def list_result_key(self):
        """Returns the key for lists of objects in the payload."""
        return self.name_plural

    @property
    def uri_name(self):
        """Returns the name of the resource in the URI.

        This can be overridden when the name in the URI needs to differ
        from the name used for the resource.
        """
        return self.name_plural.replace('_', '-')

    def _build_resource_mimetype(self, mimetype, is_list):
        if is_list:
            resource_name = self.mimetype_list_resource_name or \
                            self.name_plural.replace('_', '-')
        else:
            resource_name = self.mimetype_item_resource_name or \
                            self.name.replace('_', '-')

        return self._build_vendor_mimetype(mimetype, resource_name)

    def _build_error_mimetype(self, request):
        mimetype = get_http_requested_mimetype(
            request, WebAPIResponse.supported_mimetypes)

        if self.mimetype_vendor:
            mimetype = self._build_vendor_mimetype(mimetype, 'error')

        return mimetype

    def _build_vendor_mimetype(self, mimetype, name):
        parts = mimetype.split('/')

        return '%s/vnd.%s.%s+%s' % (parts[0],
                                     self.mimetype_vendor,
                                     name,
                                     parts[1])

    def build_response_args(self, request):
        is_list = (request._djblets_webapi_method == 'GET' and
                   not self.singleton and
                   (self.uri_object_key is None or
                    self.uri_object_key not in request._djblets_webapi_kwargs))

        if is_list:
            key = 'list'
        else:
            key = 'item'

        supported_mimetypes = [
            mime[key]
            for mime in self.allowed_mimetypes
            if mime.get(key)
        ]

        mimetype = get_http_requested_mimetype(request, supported_mimetypes)

        if (self.mimetype_vendor and
            mimetype in WebAPIResponse.supported_mimetypes):
            mimetype = self._build_resource_mimetype(mimetype, is_list)

        response_args = {
            'supported_mimetypes': supported_mimetypes,
            'mimetype': mimetype,
        }

        if is_list:
            for mimetype_pair in self.allowed_mimetypes:
                if (mimetype_pair.get('list') == mimetype and
                    mimetype_pair.get('item')):
                    response_args['headers'] = {
                        'Item-Content-Type': mimetype_pair['item'],
                    }
                    break

        return response_args

    def get_object(self, request, id_field=None, *args, **kwargs):
        """Returns an object, given captured parameters from a URL.

        This will perform a query for the object, taking into account
        ``model_object_key``, ``uri_object_key``, and any captured parameters
        from the URL.

        This requires that ``model`` and ``uri_object_key`` be set.

        Throws django.core.exceptions.ObjectDoesNotExist if the requested
        object does not exist.
        """
        assert self.model
        assert self.singleton or self.uri_object_key

        if 'is_list' in kwargs:
            # Don't pass this in to _get_queryset, since we're not fetching
            # a list, and don't want the extra optimizations for lists to
            # kick in.
            del kwargs['is_list']

        queryset = self._get_queryset(request, *args, **kwargs)

        if self.singleton:
            return queryset.get()
        else:
            id_field = id_field or self.model_object_key

            return queryset.get(**{
                id_field: kwargs[self.uri_object_key]
            })

    def post(self, *args, **kwargs):
        """Handles HTTP POSTs.

        This is not meant to be overridden unless there are specific needs.

        This will invoke ``create`` if doing an HTTP POST on a list resource.

        By default, an HTTP POST is not allowed on individual object
        resourcces.
        """

        if 'POST' not in self.allowed_methods:
            return HttpResponseNotAllowed(self.allowed_methods)

        if (self.uri_object_key is None or
            kwargs.get(self.uri_object_key, None) is None):
            return self.create(*args, **kwargs)

        # Don't allow POSTs on children by default.
        allowed_methods = list(self.allowed_methods)
        allowed_methods.remove('POST')

        return HttpResponseNotAllowed(allowed_methods)

    def put(self, request, *args, **kwargs):
        """Handles HTTP PUTs.

        This is not meant to be overridden unless there are specific needs.

        This will just invoke ``update``.
        """
        return self.update(request, *args, **kwargs)

    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def get(self, request, api_format, *args, **kwargs):
        """Handles HTTP GETs to individual object resources.

        By default, this will check for access permissions and query for
        the object. It will then return a serialized form of the object.

        This may need to be overridden if needing more complex logic.
        """
        if (not self.model or
            (self.uri_object_key is None and not self.singleton)):
            return HttpResponseNotAllowed(self.allowed_methods)

        try:
            obj = self.get_object(request, *args, **kwargs)
        except self.model.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_access_permissions(request, obj, *args, **kwargs):
            return self.get_no_access_error(request, obj=obj, *args, **kwargs)

        last_modified_timestamp = self.get_last_modified(request, obj)
        etag = self.get_etag(request, obj)

        if ((last_modified_timestamp and
             get_modified_since(request, last_modified_timestamp)) or
            (('If-None-Match' in request.META or etag) and
             etag_if_none_match(request, etag))):
            return HttpResponseNotModified()



        data = {
            self.item_result_key: self.serialize_object(obj, request=request,
                                                        *args, **kwargs),
        }

        response = WebAPIResponse(request,
                                  status=200,
                                  obj=data,
                                  api_format=api_format,
                                  **self.build_response_args(request))

        if last_modified_timestamp:
            set_last_modified(response, last_modified_timestamp)

        if etag:
            set_etag(response, etag)

        return response

    @webapi_response_errors(NOT_LOGGED_IN, PERMISSION_DENIED, DOES_NOT_EXIST)
    @webapi_request_fields(
        optional={
            'start': {
                'type': int,
                'description': 'The 0-based index of the first result in '
                               'the list. The start index is usually the '
                               'previous start index plus the number of '
                               'previous results. By default, this is 0.',
            },
            'max-results': {
                'type': int,
                'description': 'The maximum number of results to return in '
                               'this list. By default, this is 25. There is '
                               'a hard limit of 200; if you need more than '
                               '200 results, you will need to make more '
                               'than one request, using the "next" '
                               'pagination link.',
            }
        },
        allow_unknown=True
    )
    def get_list(self, request, *args, **kwargs):
        """Handles HTTP GETs to list resources.

        By default, this will query for a list of objects and return the
        list in a serialized form.
        """
        data = {
            'links': self.get_links(self.list_child_resources,
                                    request=request, *args, **kwargs),
        }

        if not self.has_list_access_permissions(request, *args, **kwargs):
            return self.get_no_access_error(request, *args, **kwargs)

        if self.model:
            try:
                queryset = self._get_queryset(request, is_list=True,
                                              *args, **kwargs)
            except ObjectDoesNotExist:
                return DOES_NOT_EXIST

            return WebAPIResponsePaginated(
                request,
                queryset=queryset,
                results_key=self.list_result_key,
                serialize_object_func=
                    lambda obj:
                        self.get_serializer_for_object(obj).serialize_object(
                            obj, request=request, *args, **kwargs),
                extra_data=data,
                **self.build_response_args(request))
        else:
            return 200, data

    @webapi_login_required
    def create(self, request, api_format, *args, **kwargs):
        """Handles HTTP POST requests to list resources.

        This is used to create a new object on the list, given the
        data provided in the request. It should usually return
        HTTP 201 Created upon success.

        By default, this returns HTTP 405 Method Not Allowed.
        """
        return HttpResponseNotAllowed(self.allowed_methods)

    @webapi_login_required
    def update(self, request, api_format, *args, **kwargs):
        """Handles HTTP PUT requests to object resources.

        This is used to update an object, given full or partial data provided
        in the request. It should usually return HTTP 200 OK upon success.

        By default, this returns HTTP 405 Method Not Allowed.
        """
        return HttpResponseNotAllowed(self.allowed_methods)

    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, api_format, *args, **kwargs):
        """Handles HTTP DELETE requests to object resources.

        This is used to delete an object, if the user has permissions to
        do so.

        By default, this deletes the object and returns HTTP 204 No Content.
        """
        if not self.model or self.uri_object_key is None:
            return HttpResponseNotAllowed(self.allowed_methods)

        try:
            obj = self.get_object(request, *args, **kwargs)
        except self.model.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, obj, *args, **kwargs):
            return self.get_no_access_error(request, obj=obj, *args, **kwargs)

        obj.delete()

        return 204, {}

    def get_queryset(self, request, is_list=False, *args, **kwargs):
        """Returns a queryset used for querying objects or lists of objects.

        Throws django.core.exceptions.ObjectDoesNotExist if the requested
        object does not exist.

        This can be overridden to filter the object list, such as for hiding
        non-public objects.

        The ``is_list`` parameter can be used to specialize the query based
        on whether an individual object or a list of objects is being queried.
        """
        return self.model.objects.all()

    def get_url_patterns(self):
        """Returns the Django URL patterns for this object and its children.

        This is used to automatically build up the URL hierarchy for all
        objects. Projects should call this for top-level resources and
        return them in the ``urls.py`` files.
        """
        urlpatterns = never_cache_patterns('',
            url(r'^$', self, name=self._build_named_url(self.name_plural)),
        )

        for resource in self.list_child_resources:
            resource._parent_resource = self
            child_regex = r'^' + resource.uri_name + r'/'
            urlpatterns += patterns('',
                url(child_regex, include(resource.get_url_patterns())),
            )

        if self.uri_object_key or self.singleton:
            # If the resource has particular items in it...
            if self.uri_object_key:
                base_regex = r'^(?P<%s>%s)/' % (self.uri_object_key,
                                                self.uri_object_key_regex)
            elif self.singleton:
                base_regex = r'^'

            urlpatterns += never_cache_patterns('',
                url(base_regex + r'$', self,
                    name=self._build_named_url(self.name))
            )

            for resource in self.item_child_resources:
                resource._parent_resource = self
                child_regex = base_regex + resource.uri_name + r'/'
                urlpatterns += patterns('',
                    url(child_regex, include(resource.get_url_patterns())),
                )

        return urlpatterns

    def has_access_permissions(self, request, obj, *args, **kwargs):
        """Returns whether or not the user has read access to this object."""
        return True

    def has_list_access_permissions(self, request, *args, **kwargs):
        """Returns whether or not the user has read access to this list."""
        if self._parent_resource and self.model_parent_key:
            try:
                parent_obj = self._parent_resource.get_object(
                    request, *args, **kwargs)

                return self._parent_resource.has_access_permissions(
                    request, parent_obj, *args, **kwargs)
            except:
                # Other errors, like Does Not Exist, should be caught
                # separately. As of here, we'll allow it to pass, so that
                # the error isn't a Permission Denied when it should be
                # a Does Not Exist.
                pass

        return True

    def has_modify_permissions(self, request, obj, *args, **kwargs):
        """Returns whether or not the user can modify this object."""
        return False

    def has_delete_permissions(self, request, obj, *args, **kwargs):
        """Returns whether or not the user can delete this object."""
        return False

    def serialize_object(self, obj, *args, **kwargs):
        """Serializes the object into a Python dictionary."""
        data = {
            'links': self.get_links(self.item_child_resources, obj,
                                     *args, **kwargs),
        }

        request = kwargs.get('request', None)
        expand = request.GET.get('expand', request.POST.get('expand', ''))
        expanded_resources = expand.split(',')

        for field in six.iterkeys(self.fields):
            serialize_func = getattr(self, "serialize_%s_field" % field, None)

            if serialize_func and six.callable(serialize_func):
                value = serialize_func(obj, request=request)
            else:
                value = getattr(obj, field)

                if isinstance(value, models.Manager):
                    value = value.all()
                elif isinstance(value, models.ForeignKey):
                    value = value.get()

            expand_field = field in expanded_resources

            if isinstance(value, models.Model) and not expand_field:
                resource = self.get_serializer_for_object(value)
                assert resource

                data['links'][field] = {
                    'method': 'GET',
                    'href': resource.get_href(value, *args, **kwargs),
                    'title': six.text_type(value),
                }
            elif isinstance(value, QuerySet) and not expand_field:
                data[field] = [
                    {
                        'method': 'GET',
                        'href': self.get_serializer_for_object(o).get_href(
                                     o, *args, **kwargs),
                        'title': six.text_type(o),
                    }
                    for o in value
                ]
            elif isinstance(value, QuerySet):
                data[field] = list(value)
            else:
                data[field] = value

        for resource_name in expanded_resources:
            if resource_name not in data['links']:
                continue

            # Try to find the resource from the child list.
            found = False

            for resource in self.item_child_resources:
                if resource_name in [resource.name, resource.name_plural]:
                    found = True
                    break

            if not found or not resource.model:
                continue

            del data['links'][resource_name]

            extra_kwargs = {
                self.uri_object_key: getattr(obj, self.model_object_key),
            }
            extra_kwargs.update(**kwargs)
            extra_kwargs.update(self.get_href_parent_ids(obj, **kwargs))

            data[resource_name] = resource._get_queryset(
                is_list=True, *args, **extra_kwargs)

        return data

    def get_serializer_for_object(self, obj):
        """Returns the serializer used to serialize an object.

        This is called when serializing objects for payloads returned
        by this resource instance. It must return the resource instance
        that will be responsible for serializing the given object for the
        payload.

        By default, this calls ``get_resource_for_object`` to find the
        appropriate resource.
        """
        return get_resource_for_object(obj)

    def get_links(self, resources=[], obj=None, request=None,
                  *args, **kwargs):
        """Returns a dictionary of links coming off this resource.

        The resulting links will point to the resources passed in
        ``resources``, and will also provide special resources for
        ``self`` (which points back to the official location for this
        resource) and one per HTTP method/operation allowed on this
        resource.
        """
        links = {}
        base_href = None

        if obj:
            base_href = self.get_href(obj, request, *args, **kwargs)

        if not base_href:
            # We may have received None from the URL above.
            if request:
                base_href = request.build_absolute_uri()
            else:
                base_href = ''

        links['self'] = {
            'method': 'GET',
            'href': base_href,
        }

        # base_href without any query arguments.
        i = base_href.find('?')

        if i != -1:
            clean_base_href = base_href[:i]
        else:
            clean_base_href = base_href

        if 'POST' in self.allowed_methods and not obj:
            links['create'] = {
                'method': 'POST',
                'href': clean_base_href,
            }

        if 'PUT' in self.allowed_methods and obj:
            links['update'] = {
                'method': 'PUT',
                'href': clean_base_href,
            }

        if 'DELETE' in self.allowed_methods and obj:
            links['delete'] = {
                'method': 'DELETE',
                'href': clean_base_href,
            }

        for resource in resources:
            links[resource.name_plural] = {
                'method': 'GET',
                'href': '%s%s/' % (clean_base_href, resource.uri_name),
            }

        for key, info in six.iteritems(
                self.get_related_links(obj, request, *args, **kwargs)):
            links[key] = {
                'method': info['method'],
                'href': info['href'],
            }

            if 'title' in info:
                links[key]['title'] = info['title']

        return links

    def get_related_links(self, obj=None, request=None, *args, **kwargs):
        """Returns links related to this resource.

        The result should be a dictionary of link names to a dictionary of
        information. The information should contain:

        * 'method' - The HTTP method
        * 'href' - The URL
        * 'title' - The title of the link (optional)
        * 'resource' - The WebAPIResource instance
        * 'list-resource' - True if this links to a list resource (optional)
        """
        return {}

    def get_href(self, obj, request, *args, **kwargs):
        """Returns the URL for this object."""
        if not self.uri_object_key:
            return None

        href_kwargs = {
            self.uri_object_key: getattr(obj, self.model_object_key),
        }
        href_kwargs.update(self.get_href_parent_ids(obj, **kwargs))

        return request.build_absolute_uri(
            reverse(self._build_named_url(self.name), kwargs=href_kwargs))

    def get_href_parent_ids(self, obj, **kwargs):
        """Returns a dictionary mapping parent object keys to their values for
        an object.
        """
        parent_ids = {}

        if self._parent_resource and self.model_parent_key:
            parent_obj = self.get_parent_object(obj)
            parent_ids = self._parent_resource.get_href_parent_ids(
                parent_obj, **kwargs)

            if self._parent_resource.uri_object_key:
                parent_ids[self._parent_resource.uri_object_key] = \
                    getattr(parent_obj, self._parent_resource.model_object_key)

        return parent_ids

    def get_parent_object(self, obj):
        """Returns the parent of an object.

        By default, this uses ``model_parent_key`` to figure out the parent,
        but it can be overridden for more complex behavior.
        """
        parent_obj = getattr(obj, self.model_parent_key)

        if isinstance(parent_obj, (models.Manager, models.ForeignKey)):
            parent_obj = parent_obj.get()

        return parent_obj

    def get_last_modified(self, request, obj):
        """Returns the last modified timestamp of an object.

        By default, this uses ``last_modified_field`` to determine what
        field in the model represents the last modified timestamp of
        the object.

        This can be overridden for more complex behavior.
        """
        if self.last_modified_field:
            return getattr(obj, self.last_modified_field)

        return None

    def get_etag(self, request, obj):
        """Returns the ETag representing the state of the object.

        By default, this uses ``etag_field`` to determine what field in
        the model is unique enough to represent the state of the object.

        This can be overridden for more complex behavior.
        """
        if self.etag_field:
            return six.text_type(getattr(obj, self.etag_field))
        elif self.autogenerate_etags:
            return self.generate_etag(obj, self.fields, request=request)

        return None

    def generate_etag(self, obj, fields, request):
        """Generates an ETag from the serialized values of all given fields."""
        values = []

        for field in fields:
            serialize_func = getattr(self, "serialize_%s_field" % field, None)

            if serialize_func and six.callable(serialize_func):
                values.append(serialize_func(obj, request=request))
            else:
                values.append(six.text_type(getattr(obj, field)))

        data = ':'.join(fields)
        return sha1(data.encode('utf-8')).hexdigest()

    def get_no_access_error(self, request, *args, **kwargs):
        """Returns an appropriate error when access is denied.

        By default, this will return PERMISSION_DENIED if the user is logged
        in, and NOT_LOGGED_IN if the user is anonymous.

        Subclasses can override this to return different or more detailed
        errors.
        """
        if request.user.is_authenticated():
            return PERMISSION_DENIED
        else:
            return NOT_LOGGED_IN

    def _build_named_url(self, name):
        """Builds a Django URL name from the provided name."""
        return '%s-resource' % name.replace('_', '-')

    def _get_queryset(self, request, is_list=False, *args, **kwargs):
        """Returns an optimized queryset.

        This calls out to the resource's get_queryset(), and then performs
        some optimizations to better fetch related objects, reducing future
        lookups in this request.
        """
        queryset = self.get_queryset(request, is_list=is_list, *args, **kwargs)
        queryset = queryset.select_related()

        if is_list:
            if not hasattr(self, '_prefetch_related_fields'):
                self._prefetch_related_fields = []

                for field in six.iterkeys(self.fields):
                    if hasattr(self, 'serialize_%s_field' % field):
                        continue

                    field_type = getattr(self.model, field, None)

                    if (field_type and
                        isinstance(field_type,
                                   (ReverseManyRelatedObjectsDescriptor,
                                    ManyRelatedObjectsDescriptor))):
                        self._prefetch_related_fields.append(field)

            if self._prefetch_related_fields:
                queryset = \
                    queryset.prefetch_related(*self._prefetch_related_fields)

        return queryset


class RootResource(WebAPIResource):
    """The root of a resource tree.

    This is meant to be instantiated with a list of immediate child
    resources. The result of ``get_url_patterns`` should be included in
    a project's ``urls.py``.
    """
    name = 'root'
    singleton = True

    def __init__(self, child_resources=[], include_uri_templates=True):
        super(RootResource, self).__init__()
        self.list_child_resources = child_resources
        self._uri_templates = {}
        self._include_uri_templates = include_uri_templates

    def get_etag(self, request, obj, *args, **kwargs):
        return sha1(repr(obj).encode('utf-8')).hexdigest()

    def get(self, request, *args, **kwargs):
        """
        Retrieves the list of top-level resources, and a list of
        :term:`URI templates` for accessing any resource in the tree.
        """
        data = self.serialize_root(request, *args, **kwargs)
        etag = self.get_etag(request, data)

        if etag_if_none_match(request, etag):
            return HttpResponseNotModified()

        return 200, data, {
            'ETag': etag,
        }

    def serialize_root(self, request, *args, **kwargs):
        """Serializes the contents of the root resource.

        By default, this just provides links and URI templates. Subclasses
        can override this to provide additional data, or to otherwise
        change the structure of the root resource.
        """
        data = {
            'links': self.get_links(self.list_child_resources,
                                     request=request, *args, **kwargs),
        }

        if self._include_uri_templates:
            data['uri_templates'] = self.get_uri_templates(request, *args,
                                                            **kwargs)

        return data

    def get_uri_templates(self, request, *args, **kwargs):
        """Returns all URI templates in the resource tree.

        REST APIs can be very chatty if a client wants to be well-behaved
        and crawl the resource tree asking for the links, instead of
        hard-coding the paths. The benefit is that they can keep from
        breaking when paths change. The downside is that it can take many
        HTTP requests to get the right resource.

        This list of all URI templates allows clients who know the resource
        name and the data they care about to simply plug them into the
        URI template instead of trying to crawl over the whole tree. This
        can make things far more efficient.
        """
        if not self._uri_templates:
            self._uri_templates = {}

        base_href = request.build_absolute_uri()
        if base_href not in self._uri_templates:
            templates = {}
            for name, href in self._walk_resources(self, base_href):
                templates[name] = href

            self._uri_templates[base_href] = templates

        return self._uri_templates[base_href]

    def _walk_resources(self, resource, list_href):
        yield resource.name_plural, list_href

        for child in resource.list_child_resources:
            child_href = list_href + child.uri_name + '/'

            for name, href in self._walk_resources(child, child_href):
                yield name, href

        if resource.uri_object_key:
            object_href = '%s{%s}/' % (list_href, resource.uri_object_key)

            yield resource.name, object_href

            for child in resource.item_child_resources:
                child_href = object_href + child.uri_name + '/'

                for name, href in self._walk_resources(child, child_href):
                    yield name, href

    def api_404_handler(self, request, api_format=None, *args, **kwargs):
        """Default handler at the end of the URL patterns.

        This returns an API 404, instead of a normal django 404."""
        return WebAPIResponseError(
            request,
            err=DOES_NOT_EXIST,
            api_format=api_format)

    def get_url_patterns(self):
        """Returns the Django URL patterns for this object and its children.

        This returns the same list as WebAPIResource.get_url_patterns, but also
        introduces a generic catch-all 404 handler which returns API errors
        instead of HTML.
        """
        urlpatterns = super(RootResource, self).get_url_patterns()
        urlpatterns += never_cache_patterns(
            '', url(r'.*', self.api_404_handler))
        return urlpatterns


class UserResource(WebAPIResource):
    """A default resource for representing a Django User model."""
    model = User
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the user.',
        },
        'username': {
            'type': str,
            'description': "The user's username.",
        },
        'first_name': {
            'type': str,
            'description': "The user's first name.",
        },
        'last_name': {
            'type': str,
            'description': "The user's last name.",
        },
        'fullname': {
            'type': str,
            'description': "The user's full name (first and last).",
        },
        'email': {
            'type': str,
            'description': "The user's e-mail address",
        },
        'url': {
            'type': str,
            'description': "The URL to the user's page on the site. "
                           "This is deprecated and will be removed in a "
                           "future version.",
        },
    }

    uri_object_key = 'username'
    uri_object_key_regex = r'[A-Za-z0-9@\._\-\'\+]+'
    model_object_key = 'username'
    autogenerate_etags = True

    allowed_methods = ('GET',)

    def serialize_fullname_field(self, user, **kwargs):
        return user.get_full_name()

    def serialize_url_field(self, user, **kwargs):
        return user.get_absolute_url()

    def has_modify_permissions(self, request, user, *args, **kwargs):
        """Returns whether or not the user can modify this object."""
        return request.user.is_authenticated() and user.pk == request.user.pk

    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Retrieves the list of users on the site."""
        pass


class GroupResource(WebAPIResource):
    """A default resource for representing a Django Group model."""
    model = Group
    fields = ('id', 'name')

    uri_object_key = 'group_name'
    uri_object_key_regex = r'[A-Za-z0-9_\-]+'
    model_object_key = 'name'
    autogenerate_etags = True

    allowed_methods = ('GET',)


def register_resource_for_model(model, resource):
    """Registers a resource as the official location for a model.

    ``resource`` can be a callable function that takes an instance of
    ``model`` and returns a ``WebAPIResource``.
    """
    _model_to_resources[model] = resource


def unregister_resource_for_model(model):
    """Removes the official location for a model."""
    del _model_to_resources[model]


def get_resource_for_object(obj):
    """Returns the resource for an object."""
    resource = _model_to_resources.get(obj.__class__, None)

    if not isinstance(resource, WebAPIResource) and six.callable(resource):
        resource = resource(obj)

    return resource


def get_resource_from_name(name):
    """Returns the resource of the specified name."""
    return _name_to_resources.get(name, None)

def get_resource_from_class(klass):
    """Returns the resource with the specified resource class."""
    return _class_to_resources.get(klass, None)

def unregister_resource(resource):
    """Unregisters a resource from the caches."""
    del _name_to_resources[resource.name]
    del _name_to_resources[resource.name_plural]
    del _class_to_resources[resource.__class__]


user_resource = UserResource()
group_resource = GroupResource()

# These are good defaults, and will be overridden if another class calls
# register_resource_for_model on these models.
register_resource_for_model(User, user_resource)
register_resource_for_model(Group, group_resource)

########NEW FILE########
__FILENAME__ = tests
#
# tests.py -- Unit tests for classes in djblets.webapi
#
# Copyright (c) 2011  Beanbag, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import print_function, unicode_literals

import json

from django.contrib.auth.models import AnonymousUser, User
from django.test.client import RequestFactory

from djblets.testing.testcases import TestCase
from djblets.webapi.decorators import (copy_webapi_decorator_data,
                                       webapi_login_required,
                                       webapi_permission_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED,
                                   WebAPIError)
from djblets.webapi.resources import (UserResource, WebAPIResource,
                                      unregister_resource)


class WebAPIDecoratorTests(TestCase):
    def test_copy_webapi_decorator_data(self):
        """Testing copy_webapi_decorator_data"""
        def func1():
            """Function 1"""

        def func2():
            """Function 2"""

        func1.test1 = True
        func1.response_errors = set(['a', 'b'])
        func2.test2 = True
        func2.response_errors = set(['c', 'd'])

        result = copy_webapi_decorator_data(func1, func2)
        self.assertEqual(result, func2)

        self.assertTrue(hasattr(func2, 'test1'))
        self.assertTrue(hasattr(func2, 'test2'))
        self.assertTrue(hasattr(func2, 'response_errors'))
        self.assertTrue(func2.test1)
        self.assertTrue(func2.test2)
        self.assertEqual(func2.response_errors, set(['a', 'b', 'c', 'd']))
        self.assertEqual(func2.__doc__, 'Function 1')
        self.assertEqual(func2.__name__, 'func1')

        self.assertFalse(hasattr(func1, 'test2'))
        self.assertEqual(func1.response_errors, set(['a', 'b']))

    def test_webapi_response_errors_state(self):
        """Testing @webapi_response_errors state"""
        def orig_func():
            """Function 1"""

        func = webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN)(orig_func)

        self.assertFalse(hasattr(orig_func, 'response_errors'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertEqual(func.response_errors,
                         set([DOES_NOT_EXIST, NOT_LOGGED_IN]))

    def test_webapi_response_errors_preserves_state(self):
        """Testing @webapi_response_errors preserves decorator state"""
        @webapi_response_errors(DOES_NOT_EXIST)
        @webapi_response_errors(NOT_LOGGED_IN)
        def func():
            """Function 1"""

        self.assertEqual(func.__name__, 'func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertEqual(func.response_errors,
                         set([DOES_NOT_EXIST, NOT_LOGGED_IN]))

    def test_webapi_response_errors_call(self):
        """Testing @webapi_response_errors calls original function"""
        @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN)
        def func():
            func.seen = True

        func()

        self.assertTrue(hasattr(func, 'seen'))

    def test_webapi_login_required_state(self):
        """Testing @webapi_login_required state"""
        def orig_func():
            """Function 1"""

        func = webapi_login_required(orig_func)

        self.assertFalse(hasattr(orig_func, 'login_required'))
        self.assertFalse(hasattr(orig_func, 'response_errors'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertTrue(hasattr(func, 'login_required'))
        self.assertTrue(func.login_required)
        self.assertEqual(func.response_errors, set([NOT_LOGGED_IN]))

    def test_webapi_login_required_preserves_state(self):
        """Testing @webapi_login_required preserves decorator state"""
        @webapi_response_errors(DOES_NOT_EXIST)
        def orig_func():
            """Function 1"""

        func = webapi_login_required(orig_func)

        self.assertFalse(hasattr(orig_func, 'login_required'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertTrue(hasattr(func, 'login_required'))
        self.assertTrue(func.login_required)
        self.assertEqual(func.response_errors,
                         set([DOES_NOT_EXIST, NOT_LOGGED_IN]))

    def test_webapi_login_required_call_when_authenticated(self):
        """Testing @webapi_login_required calls when authenticated"""
        @webapi_login_required
        def func(request):
            func.seen = True

        request = RequestFactory().request()
        request.user = User()
        result = func(request)

        self.assertTrue(hasattr(func, 'seen'))
        self.assertEqual(result, None)

    def test_webapi_login_required_call_when_anonymous(self):
        """Testing @webapi_login_required calls when anonymous"""
        @webapi_login_required
        def func(request):
            func.seen = True

        request = RequestFactory().request()
        request.user = AnonymousUser()
        result = func(request)

        self.assertFalse(hasattr(func, 'seen'))
        self.assertEqual(result, NOT_LOGGED_IN)

    def test_webapi_permission_required_state(self):
        """Testing @webapi_permission_required state"""
        def orig_func():
            """Function 1"""

        func = webapi_permission_required('myperm')(orig_func)

        self.assertFalse(hasattr(orig_func, 'response_errors'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertEqual(func.response_errors,
                         set([NOT_LOGGED_IN, PERMISSION_DENIED]))

    def test_webapi_permission_required_preserves_state(self):
        """Testing @webapi_permission_required preserves decorator state"""
        @webapi_response_errors(DOES_NOT_EXIST)
        def orig_func():
            """Function 1"""

        func = webapi_permission_required('myperm')(orig_func)

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertEqual(func.response_errors,
                         set([DOES_NOT_EXIST, NOT_LOGGED_IN,
                              PERMISSION_DENIED]))

    def test_webapi_permission_required_call_when_anonymous(self):
        """Testing @webapi_permission_required calls when anonymous"""
        @webapi_permission_required('foo')
        def func(request):
            func.seen = True

        request = RequestFactory().request()
        request.user = AnonymousUser()
        result = func(request)

        self.assertFalse(hasattr(func, 'seen'))
        self.assertEqual(result, NOT_LOGGED_IN)

    def test_webapi_permission_required_call_when_has_permission(self):
        """Testing @webapi_permission_required calls when has permission"""
        @webapi_permission_required('foo')
        def func(request):
            func.seen = True

        request = RequestFactory().request()
        request.user = User()
        request.user.has_perm = lambda perm: True
        result = func(request)

        self.assertTrue(hasattr(func, 'seen'))
        self.assertEqual(result, None)

    def test_webapi_permission_required_call_when_no_permission(self):
        """Testing @webapi_permission_required calls when no permission"""
        @webapi_permission_required('foo')
        def func(request):
            func.seen = True

        request = RequestFactory().request()
        request.user = User()
        request.user.has_perm = lambda perm: False
        result = func(request)

        self.assertFalse(hasattr(func, 'seen'))
        self.assertEqual(result, PERMISSION_DENIED)

    def test_webapi_request_fields_state(self):
        """Testing @webapi_request_fields state"""
        def orig_func():
            """Function 1"""

        required = {
            'required_param': {
                'type': bool,
                'description': 'Required param'
            },
        }

        optional = {
            'optional_param': {
                'type': bool,
                'description': 'Optional param'
            },
        }

        func = webapi_request_fields(required, optional)(orig_func)

        self.assertFalse(hasattr(orig_func, 'required_fields'))
        self.assertFalse(hasattr(orig_func, 'optional_fields'))
        self.assertFalse(hasattr(orig_func, 'response_errors'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertTrue(hasattr(func, 'required_fields'))
        self.assertTrue(hasattr(func, 'optional_fields'))
        self.assertEqual(func.required_fields, required)
        self.assertEqual(func.optional_fields, optional)
        self.assertEqual(func.response_errors, set([INVALID_FORM_DATA]))

    def test_webapi_request_fields_preserves_state(self):
        """Testing @webapi_request_fields preserves decorator state"""
        required1 = {
            'required1': {
                'type': bool,
                'description': 'Required param'
            },
        }

        optional1 = {
            'optional1': {
                'type': bool,
                'description': 'Optional param'
            },
        }

        @webapi_request_fields(required1, optional1)
        @webapi_response_errors(DOES_NOT_EXIST)
        def orig_func():
            """Function 1"""

        required2 = {
            'required2': {
                'type': bool,
                'description': 'Required param'
            },
        }

        optional2 = {
            'optional2': {
                'type': bool,
                'description': 'Optional param'
            },
        }

        func = webapi_request_fields(required2, optional2)(orig_func)

        expected_required = required1.copy()
        expected_required.update(required2)
        expected_optional = optional1.copy()
        expected_optional.update(optional2)

        self.assertTrue(hasattr(orig_func, 'required_fields'))
        self.assertTrue(hasattr(orig_func, 'optional_fields'))
        self.assertTrue(hasattr(orig_func, 'response_errors'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertTrue(hasattr(func, 'required_fields'))
        self.assertTrue(hasattr(func, 'optional_fields'))
        self.assertEqual(func.required_fields, expected_required)
        self.assertEqual(func.optional_fields, expected_optional)
        self.assertEqual(func.response_errors,
                         set([DOES_NOT_EXIST, INVALID_FORM_DATA]))

    def test_webapi_request_fields_call_normalizes_params(self):
        """Testing @webapi_request_fields normalizes params to function"""
        @webapi_request_fields(
            required={
                'required_param': {
                    'type': int,
                }
            },
            optional={
                'optional_param': {
                    'type': bool,
                }
            },
        )
        def func(request, required_param=None, optional_param=None,
                 extra_fields={}):
            func.seen = True
            self.assertTrue(isinstance(required_param, int))
            self.assertTrue(isinstance(optional_param, bool))
            self.assertEqual(required_param, 42)
            self.assertTrue(optional_param)
            self.assertFalse(extra_fields)

        result = func(RequestFactory().get(
            path='/',
            data={
                'required_param': '42',
                'optional_param': '1',
            }
        ))

        self.assertTrue(hasattr(func, 'seen'))
        self.assertEqual(result, None)

    def test_webapi_request_fields_call_with_unexpected_arg(self):
        """Testing @webapi_request_fields with unexpected argument"""
        @webapi_request_fields(
            required={
                'required_param': {
                    'type': int,
                }
            },
        )
        def func(request, required_param=None, extra_fields={}):
            func.seen = True

        result = func(RequestFactory().get(
            path='/',
            data={
                'required_param': '42',
                'optional_param': '1',
            }
        ))

        self.assertFalse(hasattr(func, 'seen'))
        self.assertEqual(result[0], INVALID_FORM_DATA)
        self.assertTrue('fields' in result[1])
        self.assertTrue('optional_param' in result[1]['fields'])

    def test_webapi_request_fields_call_with_allow_unknown(self):
        """Testing @webapi_request_fields with allow_unknown=True"""
        @webapi_request_fields(
            required={
                'required_param': {
                    'type': int,
                }
            },
            allow_unknown=True
        )
        def func(request, required_param=None, extra_fields={}):
            func.seen = True
            self.assertEqual(required_param, 42)
            self.assertTrue('optional_param' in extra_fields)
            self.assertEqual(extra_fields['optional_param'], '1')

        result = func(RequestFactory().get(
            path='/',
            data={
                'required_param': '42',
                'optional_param': '1',
            }
        ))

        self.assertTrue(hasattr(func, 'seen'))
        self.assertEqual(result, None)

    def test_webapi_request_fields_call_filter_special_params(self):
        """Testing @webapi_request_fields filters special params"""
        @webapi_request_fields(
            required={
                'required_param': {
                    'type': int,
                }
            },
        )
        def func(request, required_param=None, extra_fields={}):
            func.seen = True
            self.assertTrue(isinstance(required_param, int))
            self.assertEqual(required_param, 42)
            self.assertFalse(extra_fields)

        result = func(RequestFactory().get(
            path='/',
            data={
                'required_param': '42',
                'api_format': 'json',
            }
        ))

        self.assertTrue(hasattr(func, 'seen'))
        self.assertEqual(result, None)

    def test_webapi_request_fields_call_validation_int(self):
        """Testing @webapi_request_fields with int parameter validation"""
        @webapi_request_fields(
            required={
                'myint': {
                    'type': int,
                }
            }
        )
        def func(request, myint=False, extra_fields={}):
            func.seen = True

        result = func(RequestFactory().get(
            path='/',
            data={
                'myint': 'abc',
            }
        ))

        self.assertFalse(hasattr(func, 'seen'))
        self.assertEqual(result[0], INVALID_FORM_DATA)
        self.assertTrue('fields' in result[1])
        self.assertTrue('myint' in result[1]['fields'])


class WebAPIErrorTests(TestCase):
    def test_with_message(self):
        """Testing WebAPIError.with_message"""
        orig_msg = 'Original message'
        new_msg = 'New message'
        headers = {
            'foo': 'bar',
        }

        orig_error = WebAPIError(123, orig_msg, http_status=500,
                                 headers=headers)
        new_error = orig_error.with_message(new_msg)

        self.assertNotEqual(orig_error, new_error)
        self.assertEqual(new_error.msg, new_msg)
        self.assertEqual(new_error.headers, headers)
        self.assertEqual(new_error.code, orig_error.code)
        self.assertEqual(new_error.http_status, orig_error.http_status)
        self.assertEqual(orig_error.msg, orig_msg)
        self.assertEqual(orig_error.headers, headers)

    def test_with_overrides(self):
        """Testing WebAPIError.with_overrides"""
        orig_msg = 'Original message'
        new_msg = 'New message'
        orig_headers = {
            'foo': 'bar',
        }
        new_headers = {
            'abc': '123',
        }

        orig_error = WebAPIError(123, orig_msg, http_status=500,
                                 headers=orig_headers)
        new_error = orig_error.with_overrides(new_msg, headers=new_headers)

        self.assertNotEqual(orig_error, new_error)
        self.assertEqual(new_error.msg, new_msg)
        self.assertEqual(new_error.headers, new_headers)
        self.assertEqual(new_error.code, orig_error.code)
        self.assertEqual(new_error.http_status, orig_error.http_status)
        self.assertEqual(orig_error.msg, orig_msg)
        self.assertEqual(orig_error.headers, orig_headers)


class WebAPIResourceTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.test_resource = None

    def tearDown(self):
        if self.test_resource:
            unregister_resource(self.test_resource)

    def test_vendor_mimetypes(self):
        """Testing WebAPIResource with vendor-specific mimetypes"""
        class TestResource(WebAPIResource):
            mimetype_vendor = 'djblets'

        self.test_resource = TestResource()

        item_mimetypes = [
            mimetype['item']
            for mimetype in self.test_resource.allowed_mimetypes
            if 'item' in mimetype
        ]

        list_mimetypes = [
            mimetype['list']
            for mimetype in self.test_resource.allowed_mimetypes
            if 'list' in mimetype
        ]

        self.assertEqual(len(list_mimetypes), 4)
        self.assertEqual(len(item_mimetypes), 4)

        self.assertTrue('application/json' in
                        list_mimetypes)
        self.assertTrue('application/xml' in
                        list_mimetypes)
        self.assertTrue('application/vnd.djblets.testresources+json' in
                        list_mimetypes)
        self.assertTrue('application/vnd.djblets.testresources+xml' in
                        list_mimetypes)

        self.assertTrue('application/json' in
                        item_mimetypes)
        self.assertTrue('application/xml' in
                        item_mimetypes)
        self.assertTrue('application/vnd.djblets.testresource+json' in
                        item_mimetypes)
        self.assertTrue('application/vnd.djblets.testresource+xml' in
                        item_mimetypes)

    def test_vendor_mimetypes_with_custom(self):
        """Testing WebAPIResource with vendor-specific and custom mimetypes"""
        class TestResource(WebAPIResource):
            mimetype_vendor = 'djblets'
            allowed_mimetypes = WebAPIResource.allowed_mimetypes + [
                {'item': 'text/html'},
            ]

        self.test_resource = TestResource()

        item_mimetypes = [
            mimetype['item']
            for mimetype in self.test_resource.allowed_mimetypes
            if 'item' in mimetype
        ]

        list_mimetypes = [
            mimetype['list']
            for mimetype in self.test_resource.allowed_mimetypes
            if 'list' in mimetype
        ]

        self.assertEqual(len(list_mimetypes), 4)
        self.assertEqual(len(item_mimetypes), 5)

        self.assertTrue('application/json' in
                        list_mimetypes)
        self.assertTrue('application/xml' in
                        list_mimetypes)
        self.assertTrue('application/vnd.djblets.testresources+json' in
                        list_mimetypes)
        self.assertTrue('application/vnd.djblets.testresources+xml' in
                        list_mimetypes)

        self.assertTrue('application/json' in
                        item_mimetypes)
        self.assertTrue('application/xml' in
                        item_mimetypes)
        self.assertTrue('application/vnd.djblets.testresource+json' in
                        item_mimetypes)
        self.assertTrue('application/vnd.djblets.testresource+xml' in
                        item_mimetypes)
        self.assertTrue('application/vnd.djblets.testresource+xml' in
                        item_mimetypes)
        self.assertTrue('text/html' in
                        item_mimetypes)

    def test_get_with_vendor_mimetype(self):
        """Testing WebAPIResource with GET and vendor-specific mimetypes"""
        class TestResource(WebAPIResource):
            allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
            mimetype_vendor = 'djblets'
            uri_object_key = 'id'

            def get(self, *args, **kwargs):
                return 200, {}

            create = get
            update = get
            delete = get

        self.test_resource = TestResource()
        self._test_mimetype_responses(
            self.test_resource,
            '/api/tests/',
            'application/vnd.djblets.testresources+json',
            'application/vnd.djblets.testresources+xml')
        self._test_mimetype_responses(
            self.test_resource,
            '/api/tests/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            method='post')

        self._test_mimetype_responses(
            self.test_resource,
            '/api/tests/1/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            view_kwargs={'id': 1},
            method='put')
        self._test_mimetype_responses(
            self.test_resource,
            '/api/tests/1/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            view_kwargs={'id': 1},
            method='delete')

    def test_get_with_item_mimetype(self):
        """Testing WebAPIResource with GET and Item-Content-Type header"""
        class TestResource(WebAPIResource):
            allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
            mimetype_vendor = 'djblets'
            uri_object_key = 'id'

            def get(self, *args, **kwargs):
                return 200, {}

            create = get
            update = get
            delete = get

        self.test_resource = TestResource()
        self._test_item_mimetype_responses(
            self.test_resource,
            '/api/tests/',
            'application/vnd.djblets.testresources+json',
            'application/vnd.djblets.testresources+xml',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml')
        self._test_item_mimetype_responses(
            self.test_resource,
            '/api/tests/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            None,
            None,
            method='post')

        self._test_item_mimetype_responses(
            self.test_resource,
            '/api/tests/1/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            None,
            None,
            view_kwargs={'id': 1},
            method='put')
        self._test_item_mimetype_responses(
            self.test_resource,
            '/api/tests/',
            'application/vnd.djblets.testresources+json',
            'application/vnd.djblets.testresources+xml',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml')
        self._test_item_mimetype_responses(
            self.test_resource,
            '/api/tests/1/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            None,
            None,
            view_kwargs={'id': 1},
            method='delete')

    def _test_mimetype_responses(self, resource, url, json_mimetype,
                                 xml_mimetype, **kwargs):
        self._test_mimetype_response(resource, url, '*/*', json_mimetype,
                                     **kwargs)
        self._test_mimetype_response(resource, url, 'application/json',
                                     json_mimetype, **kwargs)
        self._test_mimetype_response(resource, url, json_mimetype,
                                     json_mimetype, **kwargs)
        self._test_mimetype_response(resource, url, 'application/xml',
                                     xml_mimetype, **kwargs)
        self._test_mimetype_response(resource, url, xml_mimetype, xml_mimetype,
                                     **kwargs)

    def _test_mimetype_response(self, resource, url, accept_mimetype,
                                response_mimetype, method='get',
                                view_kwargs={}):
        func = getattr(self.factory, method)

        if accept_mimetype:
            request = func(url, HTTP_ACCEPT=accept_mimetype)
        else:
            request = func(url)

        response = resource(request, **view_kwargs)
        print(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], response_mimetype)

    def _test_item_mimetype_responses(self, resource, url, json_mimetype,
                                      xml_mimetype, json_item_mimetype,
                                      xml_item_mimetype, **kwargs):
        self._test_item_mimetype_response(resource, url, '*/*',
                                          json_item_mimetype, **kwargs)
        self._test_item_mimetype_response(resource, url, 'application/json',
                                          json_item_mimetype, **kwargs)
        self._test_item_mimetype_response(resource, url, json_mimetype,
                                          json_item_mimetype, **kwargs)
        self._test_item_mimetype_response(resource, url, 'application/xml',
                                          xml_item_mimetype, **kwargs)
        self._test_item_mimetype_response(resource, url, xml_mimetype,
                                          xml_item_mimetype, **kwargs)

    def _test_item_mimetype_response(self, resource, url, accept_mimetype,
                                     response_item_mimetype=None,
                                     method='get', view_kwargs={}):
        func = getattr(self.factory, method)

        if accept_mimetype:
            request = func(url, HTTP_ACCEPT=accept_mimetype)
        else:
            request = func(url)

        response = resource(request, **view_kwargs)
        print(response)
        self.assertEqual(response.status_code, 200)

        if response_item_mimetype:
            self.assertEqual(response['Item-Content-Type'],
                             response_item_mimetype)
        else:
            self.assertTrue('Item-Content-Type' not in response)


class WebAPICoreTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user_resource = UserResource()

    def tearDown(self):
        unregister_resource(self.user_resource)

    def test_pagination_serialization_encoding(self):
        """Testing WebAPIResponsePaginated query parameter encoding"""
        # This test is for an issue when query parameters included unicode
        # characters. In this case, creating the 'self' or pagination links
        # would cause a KeyError. If this test runs fine without any uncaught
        # exceptions, then it means we're good.
        request = self.factory.get('/api/users/?q=%D0%B5')
        response = self.user_resource(request)
        print(response)

        rsp = json.loads(response.content)
        self.assertEqual(rsp['links']['self']['href'],
                         'http://testserver/api/users/?q=%D0%B5')

########NEW FILE########
__FILENAME__ = run-pyflakes
#!/usr/bin/env python
#
# Utility script to run pyflakes with the modules we care about and
# exclude errors we know to be fine.

import os
import re
import subprocess
import sys


def main():
    cur_dir = os.path.dirname(__file__)
    os.chdir(os.path.join(cur_dir, ".."))
    modules = sys.argv[1:]

    if not modules:
        modules = ['djblets']

    p = subprocess.Popen(['pyflakes'] + modules,
                         stderr=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         close_fds=True)

    contents = p.stdout.readlines()

    # Read in the exclusions file
    exclusions = {}
    fp = open(os.path.join(cur_dir, "pyflakes.exclude"), "r")

    for line in fp.readlines():
        exclusions[line.rstrip()] = 1

    fp.close()

    # Now filter things
    for line in contents:
        line = line.rstrip()
        test_line = re.sub(r':[0-9]+:', r':*:', line, 1)
        test_line = re.sub(r'line [0-9]+', r'line *', test_line)

        if test_line not in exclusions:
            print line

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import nose
import os
import stat
import sys


def run_tests(verbosity=1, interactive=False):
    from django.conf import settings
    from django.core import management
    from django.db import connection
    from django.test.utils import (setup_test_environment,
                                   teardown_test_environment)

    setup_test_environment()
    settings.DEBUG = False

    for path in (settings.MEDIA_ROOT, settings.STATIC_ROOT):
        if not os.path.exists(path):
            os.mkdir(path, 0755)

    old_db_name = 'default'
    connection.creation.create_test_db(verbosity, autoclobber=not interactive)
    management.call_command('syncdb', verbosity=verbosity,
                            interactive=interactive)

    nose_argv = ['runtests.py', '-v',
                 '--with-coverage',
                 '--with-doctest',
                 '--doctest-extension=.txt',
                 '--cover-package=djblets']

    # Don't test context manager code on Python 2.4.
    try:
        import contextlib
    except ImportError:
        nose_argv.append('--ignore-files=contextmanagers.py')

    if len(sys.argv) > 2:
        nose_argv += sys.argv[2:]

    # If the test files are executable on the file system, nose will need the
    #  --exe argument to run them
    known_file = os.path.join(os.path.dirname(__file__), '..', 'djblets',
                              'settings.py')

    if (os.path.exists(known_file) and
        os.stat(known_file).st_mode & stat.S_IXUSR):
        nose_argv.append('--exe')

    nose.main(argv=nose_argv)

    connection.creation.destroy_test_db(old_name, verbosity)
    teardown_test_environment()


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, os.getcwd())
    os.environ['DJANGO_SETTINGS_MODULE'] = "tests.settings"
    run_tests()

########NEW FILE########
__FILENAME__ = settings
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'djblets_test.db',
    }
}


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
STATIC_ROOT = 'tests/static'
MEDIA_ROOT = 'tests/media'

# URL that handles the media served from STATIC_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
STATIC_URL = '/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'af=y9ydd51a0g#bevy0+p#(7ime@m#k)$4$9imoz*!rl97w0j0'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
)

ROOT_URLCONF = 'djblets.testing.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
]


base_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                         "..", "djblets"))

for entry in os.listdir(base_path):
    fullpath = os.path.join(base_path, entry)

    if (os.path.isdir(fullpath) and
        os.path.exists(os.path.join(fullpath, "__init__.py"))):
        INSTALLED_APPS += ["djblets.%s" % entry]


INSTALLED_APPS += ['django_evolution']

########NEW FILE########
