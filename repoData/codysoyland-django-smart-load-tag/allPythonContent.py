__FILENAME__ = models

########NEW FILE########
__FILENAME__ = smart_load
from django.template import Library, Node
from smart_load_tag.utils import load

register = Library()


class SmartLoadNode(Node):
    def render(self, context):
        return ''


class ImportNode(Node):
    def render(self, context):
        return ''


class LoaderTag(object):
    """
    Base class to implement import tags.

    Must define `parse_arguments` method, which returns a list of template
    libraries to load.
    """
    def __call__(self, parser, token):
        # remove commas (they are not semantically significant)
        args = token.contents.replace(',', '').split()
        args.pop(0) # remove command name ('load')

        # TODO: Raise appropriate template syntax errors when incorrect arguments are
        # passed. Currently a variety of random exceptions can occur.
        libs = self.parse_arguments(args)

        for lib in libs:
            self.load(parser, **lib)

        return self.node()

    def parse_lib_tag(self, token):
        """
        Parse "lib_name" or "app_name.lib_name"
        """
        lib = token.split('.')
        if len(lib) > 1:
            lib, tag = lib
        else:
            lib, tag = lib[0], '*'
        return (lib, tag)

    def load(self, *args, **kwargs):
        load(*args, **kwargs)


class LoadTag(LoaderTag):
    node = SmartLoadNode

    def parse_arguments(self, args):
        """
        Handles smart load tag argument parsing.

        Returns list of dictionaries keyed by:
            lib, tag, name, namespace, app
        """
        libs = []

        while True:
            try:
                token = args.pop(0)
            except IndexError:
                break

            lib, tag = self.parse_lib_tag(token)

            # get app, namespace, and name
            app = namespace = name = None
            while True:
                try:
                    token = args.pop(0)
                except IndexError:
                    token = None
                if token == 'from':
                    app = args.pop(0)
                elif token == 'as':
                    name = args.pop(0)
                elif token == 'into':
                    namespace = args.pop(0)
                elif token is None:
                    break
                else:
                    args.insert(0, token)
                    break
            libs.append({
                'lib': lib,
                'tag': tag,
                'name': name,
                'namespace': namespace,
                'app': app,
            })

        return libs


class ImportTag(LoaderTag):
    node = ImportNode

    def parse_arguments(self, args):
        """
        Handles import tag argument parsing.

        Returns list of dictionaries keyed by:
            lib, tag, name, namespace, app
        """
        libs = []

        while True:
            try:
                token = args.pop(0)
            except IndexError:
                break

            if token == '*':
                assert args.pop(0) == 'from'
                lib, tag = self.parse_lib_tag(args.pop(0))
                namespace = None
            else:
                lib, tag = self.parse_lib_tag(token)
                namespace = lib

            # get app, namespace, and name
            app = name = None
            while True:
                try:
                    token = args.pop(0)
                except IndexError:
                    token = None
                if token == 'as':
                    if tag == '*':
                        namespace = args.pop(0)
                    else:
                        namespace = None
                        name = args.pop(0)
                elif token == 'from':
                    app = args.pop(0)
                elif token is None:
                    break
                else:
                    args.insert(0, token)
                    break

            libs.append({
                'lib': lib,
                'tag': tag,
                'name': name,
                'namespace': namespace,
                'app': app,
            })

        return libs


register.tag('load', LoadTag())
register.tag('import', ImportTag())

########NEW FILE########
__FILENAME__ = utils
from django.template import Library, TemplateSyntaxError, InvalidTemplateLibrary, get_templatetags_modules, import_library

def load(parser, lib, tag='*', name=None, namespace=None, app=None):
    """
    Determine and load tags into parser.

    If only a parser and lib are provided, it will behave just like Django's
    built-in {% load %} tag. Additional arguments provide more control over
    its behavior.

    Arguments:

    - parser        (required) Template parser to load the tag into.
    - lib           (required) Name of template library to load.
    - tag           If '*', it will load all tags from the given library. If a
                    string is provided, it will load a tag of that name.
    - name          Name to assign to the loaded tag (defaults to the name
                    registered to the template library object).
    - namespace     String to prepend to the name of the tag.
    - app           Tries to load the tag from the given app name.
    """
    try:
        lib_name = lib
        lib = Library()
        module_lib = get_library(lib_name, app)
        lib.tags.update(module_lib.tags)
        lib.filters.update(module_lib.filters)
        if tag != '*':
            lib.tags = {tag: lib.tags[tag]}
        if name:
            for tag in lib.tags.keys():
                lib.tags[name] = lib.tags[tag]
                if tag != name:
                    del lib.tags[tag]
        if namespace:
            for tag in lib.tags.keys():
                lib.tags['%s.%s' % (namespace, tag)] = lib.tags[tag]
                del lib.tags[tag]
        parser.add_library(lib)
    except InvalidTemplateLibrary, e:
        raise TemplateSyntaxError("'%s' is not a valid tag library: %s" % (lib, e))

def get_library(library_name, app_name=None):
    """
    (Forked from django.template.get_library)

    Load the template library module with the given name.

    If library is not already loaded loop over all templatetags modules to locate it.

    {% load somelib %} and {% load someotherlib %} loops twice.
    """
    #TODO: add in caching. (removed when forked from django.template.get_library).
    templatetags_modules = get_templatetags_modules()
    tried_modules = []
    best_match_lib = None
    last_found_lib = None
    app_name_parts = 0
    if app_name:
        app_name_parts = app_name.count('.')
    for module in templatetags_modules:
        taglib_module = '%s.%s' % (module, library_name)
        tried_modules.append(taglib_module)
        lib = import_library(taglib_module)
        if not lib:
            continue
        last_found_lib = lib

        if not app_name:
            continue

        module_list = module.split('.')
        module_list.pop() # remove the last part 'templetags'
        current_app = '.'.join(module_list)
        if current_app == app_name:
            break

        start = len(module_list) - app_name_parts - 1
        if start < 0:
            continue

        partial_app = '.'.join(module_list[start:])
        if partial_app == app_name:
            best_match_lib = lib

    if best_match_lib:
        last_found_lib = best_match_lib
    if not last_found_lib:
        raise InvalidTemplateLibrary("Template library %s not found, tried %s" % (library_name, ','.join(tried_modules)))

    return last_found_lib

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = lib1
from django.template import Library, TextNode

register = Library()

def do_tag1(parser, token):
    return TextNode('<app 1 lib 1 tag 1>')

def do_tag2(parser, token):
    return TextNode('<app 1 lib 1 tag 2>')

register.tag('tag1', do_tag1)
register.tag('tag2', do_tag2)

########NEW FILE########
__FILENAME__ = lib2
from django.template import Library, TextNode

register = Library()

def do_tag1(parser, token):
    return TextNode('<app 1 lib 2 tag 1>')

def do_tag2(parser, token):
    return TextNode('<app 1 lib 2 tag 2>')

register.tag('tag1', do_tag1)
register.tag('tag2', do_tag2)

########NEW FILE########
__FILENAME__ = lib3
from django.template import Library, TextNode

register = Library()

def do_tag3(parser, token):
    return TextNode('<app 1 lib 3 tag 3>')

register.tag('tag3', do_tag3)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = lib1
from django.template import Library, TextNode

register = Library()

def do_tag1(parser, token):
    return TextNode('<app 2 lib 1 tag 1>')

def do_tag2(parser, token):
    return TextNode('<app 2 lib 1 tag 2>')

register.tag('tag1', do_tag1)
register.tag('tag2', do_tag2)

########NEW FILE########
__FILENAME__ = lib2
from django.template import Library, TextNode

register = Library()

def do_tag1(parser, token):
    return TextNode('<app 2 lib 2 tag 1>')

def do_tag2(parser, token):
    return TextNode('<app 2 lib 2 tag 2>')

register.tag('tag1', do_tag1)
register.tag('tag2', do_tag2)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = lib3
from django.template import Library, TextNode

register = Library()

def do_tag3(parser, token):
    return TextNode('<app 3 sub_app1 lib 3 tag 3>')

register.tag('tag3', do_tag3)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite',
        'USER': '', 'PASSWORD': '', 'HOST': '', 'PORT': '',
    }
}

TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True
MEDIA_ROOT = ''
MEDIA_URL = ''
ADMIN_MEDIA_PREFIX = '/media/'
SECRET_KEY = 'j9q9$_tyy+khh8a&l13ehtjfa*$55&pm_!$2cl$9=1z)f=wpcl'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'testproject.urls'

TEMPLATE_DIRS = ()

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'smart_load_tag',
    'testproject.app1',
    'testproject.app2',
    'testproject.app3.sub_app1',
    'testproject.testapp',
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.template import Template, Context

class LoaderTestCase(TestCase):
    def render_string(self, data, context=None):
        context = context and Context(context) or Context()
        return Template(data).render(context)

    def assertTemplateRenders(self, template, output):
        self.assertEqual(self.render_string(template), output)

class SmartLoadTestCase(LoaderTestCase):
    def test_basic(self):
        """
        Standard {% load %} backwards compatibility
        """
        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% load lib1 %}'
            '{% tag1 %}'
            '{% tag2 %}'
        ,
            '<app 2 lib 1 tag 1>'
            '<app 2 lib 1 tag 2>'
        )

        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% load lib2 %}'
            '{% tag1 %}'
            '{% tag2 %}'
        ,
            '<app 2 lib 2 tag 1>'
            '<app 2 lib 2 tag 2>'
        )

        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% load lib1 lib2 %}'
            '{% tag1 %}'
            '{% tag2 %}'
        ,
            '<app 2 lib 2 tag 1>'
            '<app 2 lib 2 tag 2>'
        )

        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% load lib2 lib1 %}'
            '{% tag1 %}'
            '{% tag2 %}'
        ,
            '<app 2 lib 1 tag 1>'
            '<app 2 lib 1 tag 2>'
        )

    def test_namespace(self):
        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% load lib1 into lib1 %}'
            '{% lib1.tag1 %}'
            '{% lib1.tag2 %}'
        ,
            '<app 2 lib 1 tag 1>'
            '<app 2 lib 1 tag 2>'
        )

    def test_naming(self):
        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% load lib1.tag1 as lib1tag1 %}'
            '{% lib1tag1 %}'
        ,
            '<app 2 lib 1 tag 1>'
        )

        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% load lib1.tag2 as lib1tag2 %}'
            '{% lib1tag2 %}'
        ,
            '<app 2 lib 1 tag 2>'
        )

    def test_app(self):
        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% load lib1 from app1 %}'
            '{% tag1 %}'
            '{% tag2 %}'
        ,
            '<app 1 lib 1 tag 1>'
            '<app 1 lib 1 tag 2>'
        )

        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% load lib1 from app2 %}'
            '{% tag1 %}'
            '{% tag2 %}'
        ,
            '<app 2 lib 1 tag 1>'
            '<app 2 lib 1 tag 2>'
        )

    def test_complex(self):
        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% load lib1 from app1 into lib1, lib2 from app2 into lib2 %}'
            '{% lib1.tag1 %}'
            '{% lib1.tag2 %}'
            '{% lib2.tag1 %}'
            '{% lib2.tag2 %}'
        ,
            '<app 1 lib 1 tag 1>'
            '<app 1 lib 1 tag 2>'
            '<app 2 lib 2 tag 1>'
            '<app 2 lib 2 tag 2>'
        )

        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% load lib1.tag2 from app1 into tags as mytag1 %}'
            '{% load lib1.tag2 from app2 into tags as mytag2 %}'
            '{% tags.mytag1 %}'
            '{% tags.mytag2 %}'
        ,
            '<app 1 lib 1 tag 2>'
            '<app 2 lib 1 tag 2>'
        )

        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% load lib1.tag1 from app2 as app2lib1tag1 into rockin_tags, lib2, lib2.tag2 from app1 as lib2tag2 %}'
            '{% rockin_tags.app2lib1tag1 %}'
            '{% lib2tag2 %}'
            '{% tag1 %}'
            '{% tag2 %}'
        ,
            '<app 2 lib 1 tag 1>'
            '<app 1 lib 2 tag 2>'
            '<app 2 lib 2 tag 1>'
            '<app 2 lib 2 tag 2>'
        )

    def test_sub_app(self):
        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% load lib3 %}'
            '{% tag3 %}'
        ,
            '<app 3 sub_app1 lib 3 tag 3>'
        )

        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% load lib3 from app1 %}'
            '{% tag3 %}'
        ,
            '<app 1 lib 3 tag 3>'
        )

        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% load lib3 from sub_app1 %}'
            '{% tag3 %}'
        ,
            '<app 3 sub_app1 lib 3 tag 3>'
        )

        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% load lib3 from app3.sub_app1 %}'
            '{% tag3 %}'
        ,
            '<app 3 sub_app1 lib 3 tag 3>'
        )

class ImportTestCase(LoaderTestCase):
    def test_basic(self):
        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% import lib1 %}'
            '{% lib1.tag1 %}'
            '{% lib1.tag2 %}'
        ,
            '<app 2 lib 1 tag 1>'
            '<app 2 lib 1 tag 2>'
        )

    def test_namespace(self):
        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% import lib1 as my_lib %}'
            '{% my_lib.tag1 %}'
        ,
            '<app 2 lib 1 tag 1>'
        )

    def test_single_import(self):
        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% import lib1.tag1 %}'
            '{% lib1.tag1 %}'
        ,
            '<app 2 lib 1 tag 1>'
        )

    def test_specific_app(self):
        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% import lib1 from app1 %}'
            '{% import lib2 from app2 %}'
            '{% lib1.tag1 %}'
            '{% lib2.tag1 %}'
        ,
            '<app 1 lib 1 tag 1>'
            '<app 2 lib 2 tag 1>'
        )

    def test_specific_app_and_name(self):
        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% import lib1 from app1 as my_lib1 %}'
            '{% my_lib1.tag1 %}'
        ,
            '<app 1 lib 1 tag 1>'
        )

    def test_changed_name(self):
        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% import lib1.tag1 as my_tag %}'
            '{% my_tag %}'
        ,
            '<app 2 lib 1 tag 1>'
        )

    def test_no_namespace(self):
        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% import * from lib1 %}'
            '{% tag1 %}'
        ,
            '<app 2 lib 1 tag 1>'
        )

    def test_no_namespace_with_specific_app(self):
        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% import * from lib1 from app1 %}'
            '{% tag1 %}'
        ,
            '<app 1 lib 1 tag 1>'
        )

    def test_sub_app(self):
        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% import * from lib3 %}'
            '{% tag3 %}'
        ,
            '<app 3 sub_app1 lib 3 tag 3>'
        )

        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% import * from lib3 from app1 %}'
            '{% tag3 %}'
        ,
            '<app 1 lib 3 tag 3>'
        )

        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% import * from lib3 from sub_app1 %}'
            '{% tag3 %}'
        ,
            '<app 3 sub_app1 lib 3 tag 3>'
        )

        self.assertTemplateRenders(
            '{% load smart_load %}'
            '{% import * from lib3 from app3.sub_app1 %}'
            '{% tag3 %}'
        ,
            '<app 3 sub_app1 lib 3 tag 3>'
        )

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
)

########NEW FILE########
