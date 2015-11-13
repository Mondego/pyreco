__FILENAME__ = context_processors
from django.conf import settings


def cachebuster(request):
    return {'cachebuster_unique_string': settings.CACHEBUSTER_UNIQUE_STRING}

########NEW FILE########
__FILENAME__ = git
__author__ = 'James Addison'

import os

def unique_string(file):
    # TODO: consider using 'inspect' to get the calling module rather than
    # forcing the user to pass it in.  It's passed in because we need to find the .git dir
    # for the calling module, not that of django-cachebuster!
    base_dir = original_dir = os.path.dirname(os.path.abspath(file))
    while True:
        git_dir = os.path.normpath(os.path.join(base_dir, '.git'))
        if os.path.isdir(git_dir):
            break

        new_base_dir = os.path.dirname(base_dir)

        # if they are the same, then we've reached the root directory and
        # can't move up anymore - there is no .git directory.
        if new_base_dir == base_dir:
            raise EnvironmentError, "django-cachebuster could not find a '.git' directory in your project path. (Moving up from %s)" % original_dir

        base_dir = new_base_dir

    # Read the HEAD ref
    fhead = open(os.path.join(git_dir, 'HEAD'), 'r')
    if fhead:
        ref = None
        try:
            line = fhead.readline().strip()
            ref_name = line.split(" ")[1].strip()

            # Read the commit id
            fref = open(os.path.join(git_dir, ref_name), 'r')
            if fref:
                ref = fref.readline().strip()
                fref.close()
        except IndexError:
            # if we get here, it means the git project is in a 'detached HEAD' state - ie. on a tag.
            # just get the commit hash from HEAD instead!
            ref = line.strip()

        fhead.close()
        
        if ref:
            return unicode(ref)

    raise EnvironmentError, "django-cachebuster ran into a problem parsing a commit hash in your .git directory. (%s)" % git_dir


########NEW FILE########
__FILENAME__ = models
__author__ = 'James Addison'
  
########NEW FILE########
__FILENAME__ = cachebuster
__author__ = 'James Addison'

import posixpath
import datetime
import urllib
import os

from django import template
from django.conf import settings

try:
    # finders won't exist if we're not using Django 1.3+
    from django.contrib.staticfiles import finders
except ImportError:
    finders = None


register = template.Library()


@register.tag(name="media")
def do_media(parser, token):
    return CacheBusterTag(token, True)


@register.tag(name="static")
def do_static(parser, token):
    return CacheBusterTag(token, False)


class CacheBusterTag(template.Node):
    def __init__(self, token, is_media):
        self.is_media = is_media

        try:
            tokens = token.split_contents()
        except ValueError:
            raise template.TemplateSyntaxError, "'%r' tag must have one or two arguments" % token.contents.split()[0]

        self.path = tokens[1]
        self.force_timestamp = len(tokens) == 3 and tokens[2] or False

    def render(self, context):
        # self.path may be a template variable rather than a simple static file string
        try:
            path = template.Variable(self.path).resolve(context)
        except template.VariableDoesNotExist:
            path = self.path

        path = posixpath.normpath(urllib.unquote(path)).lstrip('/')

        if self.is_media:
            url_prepend = settings.MEDIA_URL
            unique_prepend = getattr(settings, 'CACHEBUSTER_PREPEND_MEDIA', False)
            unique_string = self.get_file_modified(os.path.join(settings.MEDIA_ROOT, path))
        else:
            # django versions < 1.3 don't have a STATIC_URL, so fall back to MEDIA_URL
            url_prepend = getattr(settings, "STATIC_URL", settings.MEDIA_URL)
            unique_prepend = getattr(settings, 'CACHEBUSTER_PREPEND_STATIC', False)

            if settings.DEBUG and finders:
                absolute_path = finders.find(path)
            else:
                # django versions < 1.3 don't have a STATIC_ROOT, so fall back to MEDIA_ROOT
                absolute_path = os.path.join(getattr(settings, 'STATIC_ROOT', settings.MEDIA_ROOT), path)

            if self.force_timestamp:
                unique_string = self.get_file_modified(absolute_path)
            else:
                unique_string = getattr(settings, 'CACHEBUSTER_UNIQUE_STRING', None)
                if not unique_string:
                    unique_string = self.get_file_modified(absolute_path)

        # Add in harder cachebusting required for CloudFront et al
        if unique_prepend:
          return url_prepend + unique_string + '/' + path
        else:
          return url_prepend + path + '?' + unique_string

    def get_file_modified(self, path):
        try:
            return datetime.datetime.fromtimestamp(os.path.getmtime(os.path.abspath(path))).strftime('%S%M%H%d%m%y')
        except:
            # if the file can't be found, return this; it will be an
            # indicator to the developer that collectstatic needs to be run
            # (as if the resulting 404 for the missing file wouldn't be)
            return '000000000000'

########NEW FILE########
__FILENAME__ = tests
__author__ = 'James Addison'

########NEW FILE########
__FILENAME__ = views
__author__ = 'jaddison'

"""
Views and functions for serving static files. These are only to be used during
development, and SHOULD NOT be used in a production setting.
"""
from django.conf import settings
from django.http import Http404
from django.views.static import serve as django_serve
try:
    # only in django 1.3+
    from django.contrib.staticfiles.views import serve as django_staticfiles_serve
except ImportError:
    django_staticfiles_serve = None


def static_serve(request, path, document_root=None, show_indexes=False):
    try:
        if django_staticfiles_serve:
            return django_staticfiles_serve(request, path, document_root)
        else:
            return django_serve(request, path, document_root, show_indexes)
    except Http404:
        if getattr(settings, 'CACHEBUSTER_PREPEND_STATIC', False):
            unique_string, new_path = path.split("/", 1)
            if django_staticfiles_serve:
                return django_staticfiles_serve(request, new_path, document_root)
            else:
                return django_serve(request, new_path, document_root, show_indexes)
        raise


def media_serve(request, path, document_root=None, show_indexes=False):
    try:
        return django_serve(request, path, document_root, show_indexes)
    except Http404:
        if getattr(settings, 'CACHEBUSTER_PREPEND_MEDIA', False):
            unique_string, new_path = path.split("/", 1)
            return django_serve(request, new_path, document_root, show_indexes)
        raise

########NEW FILE########
