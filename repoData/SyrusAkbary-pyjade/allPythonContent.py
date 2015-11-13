__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for django_prueba project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
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

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '_r4d7*&$@r18hy7w=pi!%97nha-_!k$#+y%go1blia6u%gs$&l'

# List of callables that know how to import templates from various sources.

TEMPLATE_LOADERS = (
    ('pyjade.ext.django.Loader',(
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )),
)

# TEMPLATE_LOADERS = (
#     'django.template.loaders.filesystem.Loader',
#     'django.template.loaders.app_directories.Loader',
# #     'django.template.loaders.eggs.Loader',
# )

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'django_example.urls'

TEMPLATE_DIRS = (
    'templates/'
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()
from django.shortcuts import render

def my_view(request):
    # View code here...
    return render(request, 'test.jade', {"foo": "bar"})

urlpatterns = patterns('',
    # Examples:
    url(r'^$', my_view, name='home'),
    # url(r'^django_prueba/', include('django_prueba.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = run
from flask import Flask,render_template
app = Flask(__name__)

app.jinja_env.add_extension('pyjade.ext.jinja.PyJadeExtension')
app.debug = True
@app.route('/')
@app.route('/<name>')
def hello(name=None):
    return render_template('hello.jade', name=name)

if __name__ == "__main__":
    app.run()
########NEW FILE########
__FILENAME__ = compiler
import re
import os
import six

class Compiler(object):
    RE_INTERPOLATE = re.compile(r'(\\)?([#!]){(.*?)}')
    doctypes = {
        '5': '<!DOCTYPE html>'
      , 'xml': '<?xml version="1.0" encoding="utf-8" ?>'
      , 'default': '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
      , 'transitional': '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
      , 'strict': '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">'
      , 'frameset': '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">'
      , '1.1': '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">'
      , 'basic': '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML Basic 1.1//EN" "http://www.w3.org/TR/xhtml-basic/xhtml-basic11.dtd">'
      , 'mobile': '<!DOCTYPE html PUBLIC "-//WAPFORUM//DTD XHTML Mobile 1.2//EN" "http://www.openmobilealliance.org/tech/DTD/xhtml-mobile12.dtd">'
    }
    inlineTags = [
        'a'
      , 'abbr'
      , 'acronym'
      , 'b'
      , 'br'
      , 'code'
      , 'em'
      , 'font'
      , 'i'
      , 'img'
      , 'ins'
      , 'kbd'
      , 'map'
      , 'samp'
      , 'small'
      , 'span'
      , 'strong'
      , 'sub'
      , 'sup'
      , 'textarea'
    ]
    selfClosing = [
        'meta'
      , 'img'
      , 'link'
      , 'input'
      , 'area'
      , 'base'
      , 'col'
      , 'br'
      , 'hr'
    ]
    autocloseCode = 'if,for,block,filter,autoescape,with,trans,spaceless,comment,cache,macro,localize,compress,raw'.split(',')

    filters = {}

    def __init__(self, node, **options):
        self.options = options
        self.node = node
        self.hasCompiledDoctype = False
        self.hasCompiledTag = False
        self.pp = options.get('pretty', True)
        self.debug = options.get('compileDebug', False) is not False
        self.filters.update(options.get('filters', {}))
        self.doctypes.update(options.get('doctypes', {}))
        # self.var_processor = options.get('var_processor', lambda x: x)
        self.selfClosing.extend(options.get('selfClosing', []))
        self.autocloseCode.extend(options.get('autocloseCode', []))
        self.inlineTags.extend(options.get('inlineTags', []))
        self.useRuntime = options.get('useRuntime', True)
        self.extension = options.get('extension', None) or '.jade'
        self.indents = 0
        self.doctype = None
        self.terse = False
        self.xml = False
        self.mixing = 0
        self.variable_start_string = options.get("variable_start_string", "{{")
        self.variable_end_string = options.get("variable_end_string", "}}")
        if 'doctype' in self.options: self.setDoctype(options['doctype'])
        self.instring = False

    def var_processor(self, var):
        if isinstance(var,six.string_types) and var.startswith('_ '):
            var = '_("%s")'%var[2:]
        return var

    def compile_top(self):
        return ''

    def compile(self):
        self.buf = [self.compile_top()]
        self.lastBufferedIdx = -1
        self.visit(self.node)
        compiled = u''.join(self.buf)
        if isinstance(compiled, six.binary_type):
            compiled = six.text_type(compiled, 'utf8')
        return compiled

    def setDoctype(self, name):
        self.doctype = self.doctypes.get(name or 'default',
                                         '<!DOCTYPE %s>' % name)
        self.terse = name in ['5','html']
        self.xml = self.doctype.startswith('<?xml')

    def buffer(self, str):
        if self.lastBufferedIdx == len(self.buf):
            self.lastBuffered += str
            self.buf[self.lastBufferedIdx - 1] = self.lastBuffered
        else:
            self.buf.append(str)
            self.lastBuffered = str;
            self.lastBufferedIdx = len(self.buf)

    def visit(self, node, *args, **kwargs):
        # debug = self.debug
        # if debug:
        #     self.buf.append('__jade.unshift({ lineno: %d, filename: %s });' % (node.line,('"%s"'%node.filename) if node.filename else '__jade[0].filename'));

        # if node.debug==False and self.debug:
        #     self.buf.pop()
        #     self.buf.pop()

        self.visitNode(node, *args, **kwargs)
        # if debug: self.buf.append('__jade.shift();')

    def visitNode (self, node, *args, **kwargs):
        name = node.__class__.__name__
        if self.instring and name != 'Tag':
            self.buffer('\n')
            self.instring = False
        return getattr(self, 'visit%s' % name)(node, *args, **kwargs)

    def visitLiteral(self, node):
        self.buffer(node.str)

    def visitBlock(self, block):
        for node in block.nodes:
            self.visit(node)

    def visitCodeBlock(self, block):
        self.buffer('{%% block %s %%}' % block.name)
        if block.mode=='prepend':
            self.buffer('%ssuper()%s' % (self.variable_start_string,
                                         self.variable_end_string))
        self.visitBlock(block)
        if block.mode == 'append':
            self.buffer('%ssuper()%s' % (self.variable_start_string,
                                         self.variable_end_string))
        self.buffer('{% endblock %}')

    def visitDoctype(self,doctype=None):
        if doctype and (doctype.val or not self.doctype):
            self.setDoctype(doctype.val or 'default')

        if self.doctype:
            self.buffer(self.doctype)
        self.hasCompiledDoctype = True

    def visitMixin(self,mixin):
        if mixin.block:
            self.buffer('{%% macro %s(%s) %%}' % (mixin.name, mixin.args))
            self.visitBlock(mixin.block)
            self.buffer('{% endmacro %}')
        else:
          self.buffer('%s%s(%s)%s' % (self.variable_start_string, mixin.name,
                                      mixin.args, self.variable_end_string))

    def visitTag(self,tag):
        self.indents += 1
        name = tag.name
        if not self.hasCompiledTag:
            if not self.hasCompiledDoctype and 'html' == name:
                self.visitDoctype()
            self.hasCompiledTag = True

        if self.pp and name not in self.inlineTags and not tag.inline:
            self.buffer('\n' + '  ' * (self.indents - 1))
        if name in self.inlineTags or tag.inline:
            self.instring = False

        closed = name in self.selfClosing and not self.xml
        self.buffer('<%s' % name)
        self.visitAttributes(tag.attrs)
        self.buffer('/>' if not self.terse and closed else '>')

        if not closed:
            if tag.code: self.visitCode(tag.code)
            if tag.text: self.buffer(self.interpolate(tag.text.nodes[0].lstrip()))
            self.escape = 'pre' == tag.name
            # empirically check if we only contain text
            textOnly = tag.textOnly or not bool(len(tag.block.nodes))
            self.instring = False
            self.visit(tag.block)

            if self.pp and not name in self.inlineTags and not textOnly:
                self.buffer('\n' + '  ' * (self.indents-1))

            self.buffer('</%s>' % name)
        self.indents -= 1

    def visitFilter(self,filter):
        if filter.name not in self.filters:
          if filter.isASTFilter:
            raise Exception('unknown ast filter "%s"' % filter.name)
          else:
            raise Exception('unknown filter "%s"' % filter.name)

        fn = self.filters.get(filter.name)
        if filter.isASTFilter:
            self.buf.append(fn(filter.block, self, filter.attrs))
        else:
            text = ''.join(filter.block.nodes)
            text = self.interpolate(text)
            filter.attrs = filter.attrs or {}
            filter.attrs['filename'] = self.options.get('filename', None)
            self.buffer(fn(text, filter.attrs))

    def _interpolate(self, attr, repl):
        return self.RE_INTERPOLATE.sub(lambda matchobj:repl(matchobj.group(3)),
                                       attr)

    def interpolate(self, text, escape=True):
        if escape:
            return self._interpolate(text,lambda x:'%s%s|escape%s' % (self.variable_start_string, x, self.variable_end_string))
        return self._interpolate(text,lambda x:'%s%s%s' % (self.variable_start_string, x, self.variable_end_string))


    def visitText(self,text):
        script = text.parent and text.parent.name == 'script'
        text = ''.join(text.nodes)
        text = self.interpolate(text, script)
        self.buffer(text)
        if self.pp:
            self.buffer('\n')

    def visitString(self,text):
        text = ''.join(text.nodes)
        text = self.interpolate(text)
        self.buffer(text)
        self.instring = True

    def visitComment(self,comment):
        if not comment.buffer: return
        if self.pp:
            self.buffer('\n' + '  ' * (self.indents))
        self.buffer('<!--%s-->' % comment.val)

    def visitAssignment(self,assignment):
        self.buffer('{%% set %s = %s %%}' % (assignment.name, assignment.val))


    def format_path(self,path):
        has_extension = os.path.basename(path).find('.') > -1
        if not has_extension:
            path += self.extension
        return path

    def visitExtends(self,node):
        path = self.format_path(node.path)
        self.buffer('{%% extends "%s" %%}' % (path))

    def visitInclude(self,node):
        path = self.format_path(node.path)
        self.buffer('{%% include "%s" %%}' % (path))

    def visitBlockComment(self, comment):
        if not comment.buffer:
            return
        isConditional = comment.val.strip().startswith('if')
        self.buffer('<!--[%s]>' % comment.val.strip() if isConditional else '<!--%s' % comment.val)
        self.visit(comment.block)
        self.buffer('<![endif]-->' if isConditional else '-->')

    def visitConditional(self, conditional):
        TYPE_CODE = {
            'if': lambda x: 'if %s'%x,
            'unless': lambda x: 'if not %s'%x,
            'elif': lambda x: 'elif %s'%x,
            'else': lambda x: 'else'
        }
        self.buf.append('{%% %s %%}' % TYPE_CODE[conditional.type](conditional.sentence))
        if conditional.block:
            self.visit(conditional.block)
            for next in conditional.next:
              self.visitConditional(next)
        if conditional.type in ['if','unless']:
            self.buf.append('{% endif %}')


    def visitVar(self, var, escape=False):
        var = self.var_processor(var)
        return ('%s%s%s%s' % (self.variable_start_string, var,
                              '|escape' if escape else '', self.variable_end_string))

    def visitCode(self,code):
        if code.buffer:
            val = code.val.lstrip()

            self.buf.append(self.visitVar(val, code.escape))
        else:
            self.buf.append('{%% %s %%}' % code.val)

        if code.block:
            # if not code.buffer: self.buf.append('{')
            self.visit(code.block)
            # if not code.buffer: self.buf.append('}')

            if not code.buffer:
              codeTag = code.val.strip().split(' ', 1)[0]
              if codeTag in self.autocloseCode:
                  self.buf.append('{%% end%s %%}' % codeTag)

    def visitEach(self,each):
        self.buf.append('{%% for %s in %s|__pyjade_iter:%d %%}' % (','.join(each.keys), each.obj, len(each.keys)))
        self.visit(each.block)
        self.buf.append('{% endfor %}')

    def attributes(self,attrs):
        return "%s__pyjade_attrs(%s)%s" % (self.variable_start_string, attrs, self.variable_end_string)

    def visitDynamicAttributes(self, attrs):
        buf, classes, params = [], [], {}
        terse='terse=True' if self.terse else ''
        for attr in attrs:
            if attr['name'] == 'class':
                classes.append('(%s)' % attr['val'])
            else:
                pair = "('%s',(%s))" % (attr['name'], attr['val'])
                buf.append(pair)

        if classes:
            classes = " , ".join(classes)
            buf.append("('class', (%s))" % classes)

        buf = ', '.join(buf)
        if self.terse: params['terse'] = 'True'
        if buf: params['attrs'] = '[%s]' % buf
        param_string = ', '.join(['%s=%s' % (n, v) for n, v in six.iteritems(params)])
        if buf or terse:
            self.buf.append(self.attributes(param_string))

    def visitAttributes(self, attrs):
        temp_attrs = []
        for attr in attrs:
            if (not self.useRuntime and not attr['name']=='class') or attr['static']: #
                if temp_attrs:
                    self.visitDynamicAttributes(temp_attrs)
                    temp_attrs = []
                n, v = attr['name'], attr['val']
                if isinstance(v, six.string_types):
                    if self.useRuntime or attr['static']:
                        self.buf.append(' %s=%s' % (n, v))
                    else:
                        self.buf.append(' %s="%s"' % (n, self.visitVar(v)))
                elif v is True:
                    if self.terse:
                        self.buf.append(' %s' % (n,))
                    else:
                        self.buf.append(' %s="%s"' % (n, n))
            else:
                temp_attrs.append(attr)

        if temp_attrs: self.visitDynamicAttributes(temp_attrs)

    @classmethod
    def register_filter(cls, name, f):
        cls.filters[name] = f

    @classmethod
    def register_autoclosecode(cls, name):
        cls.autocloseCode.append(name)


#1-

########NEW FILE########
__FILENAME__ = convert
from __future__ import print_function
import logging
import codecs
from optparse import OptionParser
from pyjade.utils import process
import os

def convert_file():
    support_compilers_list = ['django', 'jinja', 'underscore', 'mako', 'tornado', 'html']
    available_compilers = {}
    for i in support_compilers_list:
        try:
            compiler_class = __import__('pyjade.ext.%s' % i, fromlist=['pyjade']).Compiler
        except ImportError as e:
            logging.warning(e)
        else:
            available_compilers[i] = compiler_class

    usage = "usage: %prog [options] file [output]"
    parser = OptionParser(usage)
    parser.add_option("-o", "--output", dest="output",
                    help="Write output to FILE", metavar="FILE")
    # use a default compiler here to sidestep making a particular
    # compiler absolutely necessary (ex. django)
    default_compiler = sorted(available_compilers.keys())[0]
    parser.add_option("-c", "--compiler", dest="compiler",
                    choices=list(available_compilers.keys()),
                    default=default_compiler,
                    type="choice",
                    help=("COMPILER must be one of %s, default is %s" %
                          (', '.join(list(available_compilers.keys())), default_compiler)))
    parser.add_option("-e", "--ext", dest="extension",
                      help="Set import/extends default file extension",
                      metavar="FILE")

    options, args = parser.parse_args()
    if len(args) < 1:
        print("Specify the input file as the first argument.")
        exit()
    file_output = options.output or (args[1] if len(args) > 1 else None)
    compiler = options.compiler

    if options.extension:
        extension = '.%s' % options.extension
    elif options.output:
        extension = os.path.splitext(options.output)[1]
    else:
        extension = None

    if compiler in available_compilers:
        template = codecs.open(args[0], 'r', encoding='utf-8').read()
        output = process(template, compiler=available_compilers[compiler],
                         staticAttrs=True, extension=extension)
        if file_output:
            outfile = codecs.open(file_output, 'w', encoding='utf-8')
            outfile.write(output)
        else:
            print(output)
    else:
        raise Exception('You must have %s installed!' % compiler)

if __name__ == '__main__':
    convert_file()

########NEW FILE########
__FILENAME__ = exceptions
class CurrentlyNotSupported(Exception):
    pass
########NEW FILE########
__FILENAME__ = compiler
import logging
import os

from pyjade import Compiler as _Compiler, Parser, register_filter
from pyjade.runtime import attrs
from pyjade.exceptions import CurrentlyNotSupported
from pyjade.utils import process

from django.conf import settings

class Compiler(_Compiler):
    autocloseCode = 'if,ifchanged,ifequal,ifnotequal,for,block,filter,autoescape,with,trans,blocktrans,spaceless,comment,cache,localize,compress,verbatim'.split(',')
    useRuntime = True

    def __init__(self, node, **options):
        if settings.configured:
            options.update(getattr(settings,'PYJADE',{}))
        super(Compiler, self).__init__(node, **options)

    def visitCodeBlock(self,block):
        self.buffer('{%% block %s %%}'%block.name)
        if block.mode=='append': self.buffer('{{block.super}}')
        self.visitBlock(block)
        if block.mode=='prepend': self.buffer('{{block.super}}')
        self.buffer('{% endblock %}')

    def visitAssignment(self,assignment):
        self.buffer('{%% __pyjade_set %s = %s %%}'%(assignment.name,assignment.val))

    def visitMixin(self,mixin):
        self.mixing += 1
        if not mixin.call:
          self.buffer('{%% __pyjade_kwacro %s %s %%}'%(mixin.name,mixin.args)) 
          self.visitBlock(mixin.block)
          self.buffer('{% end__pyjade_kwacro %}')
        elif mixin.block:
          raise CurrentlyNotSupported("The mixin blocks are not supported yet.")
        else:
          self.buffer('{%% __pyjade_usekwacro %s %s %%}'%(mixin.name,mixin.args))
        self.mixing -= 1

    def visitCode(self,code):
        if code.buffer:
            val = code.val.lstrip()
            val = self.var_processor(val)
            self.buf.append('{{%s%s}}'%(val,'|force_escape' if code.escape else ''))
        else:
            self.buf.append('{%% %s %%}'%code.val)

        if code.block:
            self.visit(code.block)

            if not code.buffer:
              codeTag = code.val.strip().split(' ',1)[0]
              if codeTag in self.autocloseCode:
                  self.buf.append('{%% end%s %%}'%codeTag)

    def attributes(self,attrs):
        return "{%% __pyjade_attrs %s %%}"%attrs


from django import template
template.add_to_builtins('pyjade.ext.django.templatetags')

from django.utils.translation import trans_real

try:
    from django.utils.encoding import force_text as to_text
except ImportError:
    from django.utils.encoding import force_unicode as to_text

def decorate_templatize(func):
    def templatize(src, origin=None):
        src = to_text(src, settings.FILE_CHARSET)
        html = process(src,compiler=Compiler)
        return func(html, origin)

    return templatize

trans_real.templatize = decorate_templatize(trans_real.templatize)

try:
    from django.contrib.markup.templatetags.markup import markdown

    @register_filter('markdown')
    def markdown_filter(x,y):
        return markdown(x)
        
except ImportError:
    pass


########NEW FILE########
__FILENAME__ = loader
from __future__ import absolute_import
import hashlib

from django.template.base import TemplateDoesNotExist
from django.template.loader import BaseLoader, get_template_from_string, find_template_loader, make_origin
import os

from django.conf import settings
from .compiler import Compiler
from pyjade import Parser

from pyjade.utils import process
# from django.template.loaders.cached import Loader

class Loader(BaseLoader):
    is_usable = True

    def __init__(self, loaders):
        self.template_cache = {}
        self._loaders = loaders
        self._cached_loaders = []

    @property
    def loaders(self):
        # Resolve loaders on demand to avoid circular imports
        if not self._cached_loaders:
            # Set self._cached_loaders atomically. Otherwise, another thread
            # could see an incomplete list. See #17303.
            cached_loaders = []
            for loader in self._loaders:
                cached_loaders.append(find_template_loader(loader))
            self._cached_loaders = cached_loaders
        return self._cached_loaders

    def find_template(self, name, dirs=None):
        for loader in self.loaders:
            try:
                template, display_name = loader(name, dirs)
                return (template, make_origin(display_name, loader, name, dirs))
            except TemplateDoesNotExist:
                pass
        raise TemplateDoesNotExist(name)

    def load_template_source(self, template_name, template_dirs=None):
        for loader in self.loaders:
            try:
                return loader.load_template_source(template_name,template_dirs)
            except TemplateDoesNotExist:
                pass
        raise TemplateDoesNotExist(template_name)

    def load_template(self, template_name, template_dirs=None):
        key = template_name
        if template_dirs:
            # If template directories were specified, use a hash to differentiate
            key = '-'.join([template_name, hashlib.sha1('|'.join(template_dirs)).hexdigest()])

        
        if settings.DEBUG or key not in self.template_cache:

            if os.path.splitext(template_name)[1] in ('.jade',):
                try:
                    source, display_name = self.load_template_source(template_name, template_dirs)
                    source=process(source,filename=template_name,compiler=Compiler)
                    origin = make_origin(display_name, self.load_template_source, template_name, template_dirs)
                    template = get_template_from_string(source, origin, template_name)
                except NotImplementedError:
                    template, origin = self.find_template(template_name, template_dirs)
            else:
                template, origin = self.find_template(template_name, template_dirs)
            if not hasattr(template, 'render'):
                try:
                    template = get_template_from_string(process(source,filename=template_name,compiler=Compiler), origin, template_name)
                except (TemplateDoesNotExist, UnboundLocalError):
                    # If compiling the template we found raises TemplateDoesNotExist,
                    # back off to returning he source and display name for the template
                    # we were asked to load. This allows for correct identification (later)
                    # of the actual template that does not exist.
                    return template, origin
            self.template_cache[key] = template
        return self.template_cache[key], None

    # def _preprocess(self, source, name, filename=None):
    #     parser = Parser(source,filename=filename)
    #     block = parser.parse()
    #     compiler = Compiler(block)
    #     return compiler.compile().strip()

    def reset(self):
        "Empty the template cache."
        self.template_cache.clear()

########NEW FILE########
__FILENAME__ = templatetags
"""
A smarter {% if %} tag for django templates.

While retaining current Django functionality, it also handles equality,
greater than and less than operators. Some common case examples::

    {% if articles|length >= 5 %}...{% endif %}
    {% if "ifnotequal tag" != "beautiful" %}...{% endif %}
"""
import unittest
from django import template
from django.template import FilterExpression
from django.template.loader import get_template
import six

from pyjade.runtime import iteration

register = template.Library()

@register.tag(name="__pyjade_attrs")
def do_evaluate(parser, token):
  '''Calls an arbitrary method on an object.'''
  code = token.contents
  firstspace = code.find(' ')
  if firstspace >= 0:
    code = code[firstspace+1:]
  return Evaluator(code)

class Evaluator(template.Node):
  '''Calls an arbitrary method of an object'''
  def __init__(self, code):
    self.code = code
    
  def render(self, context):
    '''Evaluates the code in the page and returns the result'''
    modules = {
      'pyjade': __import__('pyjade')
    }
    context['false'] = False
    context['true'] = True
    try:
        return unicode(eval('pyjade.runtime.attrs(%s)'%self.code,modules,context))
    except NameError:
        return ''

@register.tag(name="__pyjade_set")
def do_set(parser, token):
  '''Calls an arbitrary method on an object.'''
  code = token.contents
  firstspace = code.find(' ')
  if firstspace >= 0:
    code = code[firstspace+1:]
  return Setter(code)

class Setter(template.Node):
  '''Calls an arbitrary method of an object'''
  def __init__(self, code):
    self.code = code
    
  def render(self, context):
    '''Evaluates the code in the page and returns the result'''
    modules = {
    }
    context['false'] = False
    context['true'] = True
    new_ctx = eval('dict(%s)'%self.code,modules,context)
    context.update(new_ctx)
    return ''

register.filter('__pyjade_iter', iteration)



# Support for macros in Django, taken from https://gist.github.com/skyl/1715202
# Author: Skylar Saveland

def _setup_macros_dict(parser):
    ## Metadata of each macro are stored in a new attribute
    ## of 'parser' class. That way we can access it later
    ## in the template when processing 'usemacro' tags.
    try:
        ## Only try to access it to eventually trigger an exception
        parser._macros
    except AttributeError:
        parser._macros = {}
 
 
class DefineMacroNode(template.Node):
    def __init__(self, name, nodelist, args):
 
        self.name = name
        self.nodelist = nodelist
        self.args = []
        self.kwargs = {}
        for a in args:
            a = a.rstrip(',')
            if "=" not in a:
                self.args.append(a)
            else:
                name, value = a.split("=")
                self.kwargs[name] = value
 
    def render(self, context):
        ## empty string - {% macro %} tag does no output
        return ''
 
 
@register.tag(name="__pyjade_kwacro")
def do_macro(parser, token):
    try:
        args = token.split_contents()
        tag_name, macro_name, args = args[0], args[1], args[2:]
    except IndexError:
        m = ("'%s' tag requires at least one argument (macro name)"
            % token.contents.split()[0])
        raise template.TemplateSyntaxError(m)
    # TODO: could do some validations here,
    # for now, "blow your head clean off"
    nodelist = parser.parse(('end__pyjade_kwacro', ))
    parser.delete_first_token()
 
    ## Metadata of each macro are stored in a new attribute
    ## of 'parser' class. That way we can access it later
    ## in the template when processing 'usemacro' tags.
    _setup_macros_dict(parser)
    parser._macros[macro_name] = DefineMacroNode(macro_name, nodelist, args)
    return parser._macros[macro_name]
 
 
class LoadMacrosNode(template.Node):
    def render(self, context):
        ## empty string - {% loadmacros %} tag does no output
        return ''
 
 
@register.tag(name="__pyjade_loadkwacros")
def do_loadmacros(parser, token):
    try:
        tag_name, filename = token.split_contents()
    except IndexError:
        m = ("'%s' tag requires at least one argument (macro name)"
            % token.contents.split()[0])
        raise template.TemplateSyntaxError(m)
    if filename[0] in ('"', "'") and filename[-1] == filename[0]:
        filename = filename[1:-1]
    t = get_template(filename)
    macros = t.nodelist.get_nodes_by_type(DefineMacroNode)
    ## Metadata of each macro are stored in a new attribute
    ## of 'parser' class. That way we can access it later
    ## in the template when processing 'usemacro' tags.
    _setup_macros_dict(parser)
    for macro in macros:
        parser._macros[macro.name] = macro
    return LoadMacrosNode()
 
 
class UseMacroNode(template.Node):
 
    def __init__(self, macro, fe_args, fe_kwargs):
        self.macro = macro
        self.fe_args = fe_args
        self.fe_kwargs = fe_kwargs
 
    def render(self, context):
 
        for i, arg in enumerate(self.macro.args):
            try:
                fe = self.fe_args[i]
                context[arg] = fe.resolve(context)
            except IndexError:
                context[arg] = ""
 
        for name, default in six.iteritems(self.macro.kwargs):
            if name in self.fe_kwargs:
                context[name] = self.fe_kwargs[name].resolve(context)
            else:
                context[name] = FilterExpression(default,
                                                 self.macro.parser
                ).resolve(context)
 
        return self.macro.nodelist.render(context)
 
 
@register.tag(name="__pyjade_usekwacro")
def do_usemacro(parser, token):
    try:
        args = token.split_contents()
        tag_name, macro_name, values = args[0], args[1], args[2:]
    except IndexError:
        m = ("'%s' tag requires at least one argument (macro name)"
             % token.contents.split()[0])
        raise template.TemplateSyntaxError(m)
    try:
        macro = parser._macros[macro_name]
    except (AttributeError, KeyError):
        m = "Macro '%s' is not defined" % macro_name
        raise template.TemplateSyntaxError(m)
 
    fe_kwargs = {}
    fe_args = []
 
    for val in values:
        val = val.rstrip(',')
        if "=" in val:
            # kwarg
            name, value = val.split("=")
            fe_kwargs[name] = FilterExpression(value, parser)
        else:  # arg
            # no validation, go for it ...
            fe_args.append(FilterExpression(val, parser))
 
    macro.parser = parser
    return UseMacroNode(macro, fe_args, fe_kwargs)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = html
# -*- coding: utf-8 -*-

import contextlib

import pyjade
from pyjade.runtime import is_mapping, iteration, escape
import six
import os

def process_param(key, value, terse=False):
    if terse:
        if (key == value) or (value is True):
            return key
    if isinstance(value, six.binary_type):
        value = value.decode('utf8')
    return '''%s="%s"''' % (key, value)


TYPE_CODE = {
    'if': lambda v: bool(v),
    'unless': lambda v: not bool(v),
    'elsif': lambda v: bool(v),
    'else': lambda v: True}


@contextlib.contextmanager
def local_context_manager(compiler, local_context):
    old_local_context = compiler.local_context
    new_local_context = dict(compiler.local_context)
    new_local_context.update(local_context)
    compiler.local_context = new_local_context
    yield
    compiler.local_context = old_local_context


class Compiler(pyjade.compiler.Compiler):
    global_context = dict()
    local_context = dict()
    mixins = dict()
    useRuntime = True
    def _do_eval(self, value):
        if isinstance(value, six.string_types):
            value = value.encode('utf-8')
        try:
            value = eval(value, self.global_context, self.local_context)
        except:
            return None
        return value

    def _get_value(self, attr):
        value = attr['val']
        if attr['static']:
            return attr['val']
        if isinstance(value, six.string_types):
            return self._do_eval(value)
        else:
            return attr['name']

    def _make_mixin(self, mixin):
        arg_names = [arg.strip() for arg in mixin.args.split(",")]
        def _mixin(self, args):
            if args:
                arg_values = self._do_eval(args)
            else:
                arg_values = []
            local_context = dict(zip(arg_names, arg_values))
            with local_context_manager(self, local_context):
                self.visitBlock(mixin.block)
        return _mixin

    def interpolate(self, text, escape=True):
        return self._interpolate(text, lambda x: str(self._do_eval(x)))

    def visitInclude(self, node):
        if os.path.exists(node.path):
            src = open(node.path, 'r').read()
        elif os.path.exists("%s.jade" % node.path):
            src = open("%s.jade" % node.path, 'r').read()
        else:
            raise Exception("Include path doesn't exists")

        parser = pyjade.parser.Parser(src)
        block = parser.parse()
        self.visit(block)

    def visitExtends(self, node):
        raise pyjade.exceptions.CurrentlyNotSupported()

    def visitMixin(self, mixin):
        if mixin.block:
            self.mixins[mixin.name] = self._make_mixin(mixin)
        else:
            self.mixins[mixin.name](self, mixin.args)

    def visitAssignment(self, assignment):
        self.global_context[assignment.name] = self._do_eval(assignment.val)

    def visitConditional(self, conditional):
        if not conditional.sentence:
            value = False
        else:
            value = self._do_eval(conditional.sentence)
        if TYPE_CODE[conditional.type](value):
            self.visit(conditional.block)
        elif conditional.next:
            for item in conditional.next:
                self.visitConditional(item)

    def visitCode(self, code):
        if code.buffer:
            val = code.val.lstrip()
            val = self.var_processor(val)
            val = self._do_eval(val)
            if code.escape:
                val = str(val).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            self.buf.append(val)
        if code.block:
            self.visit(code.block)
        if not code.buffer and not code.block:
            six.exec_(code.val.lstrip(), self.global_context, self.local_context)

    def visitEach(self, each):
        obj = iteration(self._do_eval(each.obj), len(each.keys))
        for item in obj:
            local_context = dict()
            if len(each.keys) > 1:
                for (key, value) in zip(each.keys, item):
                    local_context[key] = value
            else:
                local_context[each.keys[0]] = item
            with local_context_manager(self, local_context):
                self.visit(each.block)

    def attributes(self, attrs):
        return " ".join(['''%s="%s"''' % (k,v) for (k,v) in attrs.items()])

    def visitDynamicAttributes(self, attrs):
        classes = []
        params = []
        for attr in attrs:
            if attr['name'] == 'class':
                value = self._get_value(attr)
                if isinstance(value, list):
                    classes.extend(value)
                else:
                    classes.append(value)
            else:
                value = self._get_value(attr)
                if value is True:
                    params.append((attr['name'], True))
                elif value not in (None,False):
                    params.append((attr['name'], escape(value)))
        if classes:
            classes = [six.text_type(c) for c in classes]
            params.append(('class', " ".join(classes)))
        if params:
            self.buf.append(" "+" ".join([process_param(k, v, self.terse) for (k,v) in params]))

HTMLCompiler = Compiler

def process_jade(src):
    parser = pyjade.parser.Parser(src)
    block = parser.parse()
    compiler = Compiler(block, pretty=True)
    return compiler.compile()

########NEW FILE########
__FILENAME__ = jinja
from jinja2.ext import Extension
import os
import pyjade.runtime

from pyjade import Compiler as _Compiler
from pyjade.runtime import attrs as _attrs, iteration
from jinja2.runtime import Undefined
from pyjade.utils import process

ATTRS_FUNC = '__pyjade_attrs'
ITER_FUNC = '__pyjade_iter'

def attrs(attrs, terse=False):
    return _attrs(attrs, terse, Undefined)

class Compiler(_Compiler):

    def visitCodeBlock(self,block):
        if self.mixing > 0:
          if self.mixing > 1:
            caller_name = '__pyjade_caller_%d' % self.mixing
          else:
            caller_name = 'caller'
          self.buffer('{%% if %s %%}%s %s() %s{%% endif %%}' % (caller_name, self.variable_start_string,
              caller_name, self.variable_end_string))
        else:
          self.buffer('{%% block %s %%}'%block.name)
          if block.mode=='append': self.buffer('%ssuper()%s' % (self.variable_start_string, self.variable_end_string))
          self.visitBlock(block)
          if block.mode=='prepend': self.buffer('%ssuper()%s' % (self.variable_start_string, self.variable_end_string))
          self.buffer('{% endblock %}')

    def visitMixin(self,mixin):
        self.mixing += 1
        if not mixin.call:
          self.buffer('{%% macro %s(%s) %%}'%(mixin.name,mixin.args))
          self.visitBlock(mixin.block)
          self.buffer('{% endmacro %}')
        elif mixin.block:
          if self.mixing > 1:
            self.buffer('{%% set __pyjade_caller_%d=caller %%}' % self.mixing)
          self.buffer('{%% call %s(%s) %%}'%(mixin.name,mixin.args))
          self.visitBlock(mixin.block)
          self.buffer('{% endcall %}')
        else:
          self.buffer('%s%s(%s)%s' % (self.variable_start_string, mixin.name, mixin.args, self.variable_end_string))
        self.mixing -= 1

    def visitAssignment(self,assignment):
        self.buffer('{%% set %s = %s %%}'%(assignment.name,assignment.val))

    def visitCode(self,code):
        if code.buffer:
            val = code.val.lstrip()
            val = self.var_processor(val)
            self.buf.append('%s%s%s%s' % (self.variable_start_string, val,'|escape' if code.escape else '',
                self.variable_end_string))
        else:
            self.buf.append('{%% %s %%}'%code.val)

        if code.block:
            # if not code.buffer: self.buf.append('{')
            self.visit(code.block)
            # if not code.buffer: self.buf.append('}')

            if not code.buffer:
              codeTag = code.val.strip().split(' ',1)[0]
              if codeTag in self.autocloseCode:
                  self.buf.append('{%% end%s %%}'%codeTag)

    def visitEach(self,each):
        self.buf.append("{%% for %s in %s(%s,%d) %%}"%(','.join(each.keys),ITER_FUNC,each.obj,len(each.keys)))
        self.visit(each.block)
        self.buf.append('{% endfor %}')

    def attributes(self,attrs):
        return "%s%s(%s)%s" % (self.variable_start_string, ATTRS_FUNC,attrs, self.variable_end_string)


class PyJadeExtension(Extension):

    # def exception_handler(self,pt):
    #     # print '******************************'
    #     # print pt.exc_type
    #     # print pt.exc_value
    #     # print pt.frames[0].tb
    #     # line = pt.frames[0].tb.tb_lineno
    #     # pt.frames[0].tb.tb_lineno = line+10

    #     # print '******************************'
    #     _,_,tb = fake_exc_info((pt.exc_type,pt.exc_value, pt.frames[0].tb),'asfdasfdasdf',7)
    #     # pt.frames = [tb]
    #     raise pt.exc_type, pt.exc_value, tb
    options = {}
    file_extensions = '.jade'
    def __init__(self, environment):
        super(PyJadeExtension, self).__init__(environment)

        environment.extend(
            pyjade=self,
            # jade_env=JinjaEnvironment(),
        )

        # environment.exception_handler = self.exception_handler
        # get_corresponding_lineno
        environment.globals[ATTRS_FUNC] = attrs
        environment.globals[ITER_FUNC] = iteration
        self.variable_start_string = environment.variable_start_string
        self.variable_end_string = environment.variable_end_string
        self.options["variable_start_string"] = environment.variable_start_string
        self.options["variable_end_string"] = environment.variable_end_string

    def preprocess(self, source, name, filename=None):
        if (not name or
           (name and not os.path.splitext(name)[1] in self.file_extensions)):
            return source
        return process(source,filename=name,compiler=Compiler,**self.options)

########NEW FILE########
__FILENAME__ = mako
import os
import sys

from pyjade import Parser, Compiler as _Compiler
from pyjade.runtime import attrs as _attrs
from pyjade.utils import process
ATTRS_FUNC = '__pyjade_attrs'
ITER_FUNC = '__pyjade_iter'

def attrs(attrs, terse=False):
    return _attrs(attrs, terse, MakoUndefined)

class Compiler(_Compiler):
    useRuntime = True
    def compile_top(self):
        return '# -*- coding: utf-8 -*-\n<%%! from pyjade.runtime import attrs as %s, iteration as %s\nfrom mako.runtime import Undefined %%>' % (ATTRS_FUNC,ITER_FUNC)

    def interpolate(self, text, escape=True):
        return self._interpolate(text,lambda x:'${%s}'%x)

    def visitCodeBlock(self,block):
        if self.mixing > 0:
          self.buffer('${caller.body() if caller else ""}')
        else:
          self.buffer('<%%block name="%s">'%block.name)
          if block.mode=='append': self.buffer('${parent.%s()}'%block.name)
          self.visitBlock(block)
          if block.mode=='prepend': self.buffer('${parent.%s()}'%block.name)
          self.buffer('</%block>')

    def visitMixin(self,mixin):
        self.mixing += 1
        if not mixin.call:
          self.buffer('<%%def name="%s(%s)">'%(mixin.name,mixin.args))
          self.visitBlock(mixin.block)
          self.buffer('</%def>')
        elif mixin.block:
          self.buffer('<%%call expr="%s(%s)">'%(mixin.name,mixin.args))
          self.visitBlock(mixin.block)
          self.buffer('</%call>')
        else:
          self.buffer('${%s(%s)}'%(mixin.name,mixin.args))
        self.mixing -= 1

    def visitAssignment(self,assignment):
        self.buffer('<%% %s = %s %%>'%(assignment.name,assignment.val))

    def visitExtends(self,node):
        path = self.format_path(node.path)
        self.buffer('<%%inherit file="%s"/>'%(path))

    def visitInclude(self,node):
        path = self.format_path(node.path)
        self.buffer('<%%include file="%s"/>'%(path))


    def visitConditional(self,conditional):
        TYPE_CODE = {
            'if': lambda x: 'if %s'%x,
            'unless': lambda x: 'if not %s'%x,
            'elif': lambda x: 'elif %s'%x,
            'else': lambda x: 'else'
        }
        self.buf.append('\\\n%% %s:\n'%TYPE_CODE[conditional.type](conditional.sentence))
        if conditional.block:
            self.visit(conditional.block)
            for next in conditional.next:
              self.visitConditional(next)
        if conditional.type in ['if','unless']: self.buf.append('\\\n% endif\n')


    def visitVar(self,var,escape=False):
        return '${%s%s}'%(var,'| h' if escape else '| n')

    def visitCode(self,code):
        if code.buffer:
            val = code.val.lstrip()
            val = self.var_processor(val)
            self.buf.append(self.visitVar(val, code.escape))
        else:
            self.buf.append('<%% %s %%>'%code.val)

        if code.block:
            # if not code.buffer: self.buf.append('{')
            self.visit(code.block)
            # if not code.buffer: self.buf.append('}')

            if not code.buffer:
              codeTag = code.val.strip().split(' ',1)[0]
              if codeTag in self.autocloseCode:
                  self.buf.append('</%%%s>'%codeTag)

    def visitEach(self,each):
        self.buf.append('\\\n%% for %s in %s(%s,%d):\n'%(','.join(each.keys),ITER_FUNC,each.obj,len(each.keys)))
        self.visit(each.block)
        self.buf.append('\\\n% endfor\n')

    def attributes(self,attrs):
        return "${%s(%s, undefined=Undefined)}"%(ATTRS_FUNC,attrs)



def preprocessor(source):
    return process(source,compiler=Compiler)

########NEW FILE########
__FILENAME__ = underscore
import os
from itertools import count
from pyjade import Parser, Compiler as _Compiler
from pyjade.runtime import attrs
from pyjade.utils import process
import six

def process_param(key, value, terse=False):
    if terse:
        if (key == value) or (value is True):
            return key
    if isinstance(value, six.binary_type):
        value = value.decode('utf8')
    return '''%s="%s"''' % (key, value)

class Compiler(_Compiler):
    def __init__(self, *args, **kws):
      _Compiler.__init__(self, *args, **kws)
      self._i = count()

    def visitAssignment(self,assignment):
        self.buffer('<%% var %s = %s; %%>'%(assignment.name,assignment.val))

    def visitCode(self,code):
        if code.buffer:
            val = code.val.lstrip()
            self.buf.append('<%%%s %s %%>'%('=' if code.escape else '-', val))
        else:
            self.buf.append('<%% %s'%code.val) #for loop

        if code.block:
            self.buf.append(' { %>') #for loop
            # if not code.buffer: self.buf.append('{')
            self.visit(code.block)
            # if not code.buffer: self.buf.append('}')

            if not code.buffer:
              codeTag = code.val.strip().split(' ',1)[0]
              if codeTag in self.autocloseCode:
                  self.buf.append('<% } %>')
        elif not code.buffer:
            self.buf.append('; %>') #for loop
          
 
    def visitEach(self,each):
        #self.buf.append('{%% for %s in %s %%}'%(','.join(each.keys),each.obj))
        __i = self._i.next()
        self.buf.append('<%% for (_i_%s = 0, _len_%s = %s.length; _i_%s < _len_%s; _i_%s++) { ' %(__i, __i, each.obj, __i, __i, __i))
        if len(each.keys) > 1:
          for i, k in enumerate(each.keys):
            self.buf.append('%s = %s[_i_%s][%s];' % (k, each.obj, __i, i))
        else:
          for k in each.keys:
            self.buf.append('%s = %s[_i_%s];' % (k, each.obj, __i))
        self.buf.append(' %>')
        self.visit(each.block)
        self.buf.append('<% } %>')

    def _do_eval(self, value):
        if isinstance(value, six.string_types):
            value = value.encode('utf-8')
        try:
            value = eval(value, {}, {})
        except:
            return "<%%= %s %%>" % value
        return value

    def _get_value(self, attr):
        value = attr['val']
        if attr['static']:
            return attr['val']
        if isinstance(value, six.string_types):
            return self._do_eval(value)
        else:
            return attr['name']

    def visitAttributes(self,attrs):
        classes = []
        params = []
        for attr in attrs:
            if attr['name'] == 'class':
                value = self._get_value(attr)
                if isinstance(value, list):
                    classes.extend(value)
                else:
                    classes.append(value)
            else:
                value = self._get_value(attr)
                if (value is not None) and (value is not False):
                    params.append((attr['name'], value))
        if classes:
            classes = [six.text_type(c) for c in classes]
            params.append(('class', " ".join(classes)))
        if params:
            self.buf.append(" "+" ".join([process_param(k, v, self.terse) for (k,v) in params]))

    def visitConditional(self,conditional):
        TYPE_CODE = {
            'if': lambda x: 'if (%s)'%x,
            'unless': lambda x: 'if (!%s)'%x,
            'elif': lambda x: '} else if (%s)'%x,
            'else': lambda x: '} else'
        }
        self.buf.append('\n<%% %s { %%>'%TYPE_CODE[conditional.type](conditional.sentence))
        if conditional.block:
            self.visit(conditional.block)
            for next in conditional.next:
              self.visitConditional(next)
        if conditional.type in ['if','unless']: self.buf.append('\n<% } %>\n')
        
    def interpolate(self, text, escape=True):
        return self._interpolate(text,lambda x:'<%%= %s %%>'%x)

########NEW FILE########
__FILENAME__ = filters
from __future__ import absolute_import
from .compiler import Compiler

def register_filter(name=None):
    def decorator(f):
        Compiler.register_filter(name, f)
        return f
    return decorator

@register_filter('cdata')
def cdata_filter(x, y):
    return '<![CDATA[\n%s\n]]>'%x

try:
    import coffeescript
    @register_filter('coffeescript')
    def coffeescript_filter(x, y):
        return '<script>%s</script>' % coffeescript.compile(x)

except ImportError:
    pass

try:
    import markdown
    @register_filter('markdown')
    def markdown_filter(x, y):
        return markdown.markdown(x, output_format='html5')

except ImportError:
    pass

########NEW FILE########
__FILENAME__ = lexer
from __future__ import absolute_import
import re
from collections import deque
import six


class Token:
    def __init__(self, **kwds):
        self.buffer = None
        self.__dict__.update(kwds)

    def __str__(self):
        return self.__dict__.__str__()


def regexec(regex, input):
    matches = regex.match(input)
    if matches:
        return (input[matches.start():matches.end()],) + matches.groups()
    return None


class Lexer(object):
    RE_INPUT = re.compile(r'\r\n|\r')
    RE_COMMENT = re.compile(r'^ *\/\/(-)?([^\n]*)')
    RE_TAG = re.compile(r'^(\w[-:\w]*)')
    RE_FILTER = re.compile(r'^:(\w+)')
    RE_DOCTYPE = re.compile(r'^(?:!!!|doctype) *([^\n]+)?')
    RE_ID = re.compile(r'^#([\w-]+)')
    RE_CLASS = re.compile(r'^\.([\w-]+)')
    RE_STRING = re.compile(r'^(?:\| ?)([^\n]+)')
    RE_TEXT = re.compile(r'^([^\n]+)')
    RE_EXTENDS = re.compile(r'^extends? +([^\n]+)')
    RE_PREPEND = re.compile(r'^prepend +([^\n]+)')
    RE_APPEND = re.compile(r'^append +([^\n]+)')
    RE_BLOCK = re.compile(r'''^block(( +(?:(prepend|append) +)?([^\n]*))|\n)''')
    RE_YIELD = re.compile(r'^yield *')
    RE_INCLUDE = re.compile(r'^include +([^\n]+)')
    RE_ASSIGNMENT = re.compile(r'^(-\s+var\s+)?(\w+) += *([^;\n]+)( *;? *)')
    RE_MIXIN = re.compile(r'^mixin +([-\w]+)(?: *\((.*)\))?')
    RE_CALL = re.compile(r'^\+([-\w]+)(?: *\((.*)\))?')
    RE_CONDITIONAL = re.compile(r'^(?:- *)?(if|unless|else if|elif|else)\b([^\n]*)')
    RE_BLANK = re.compile(r'^\n *\n')
    # RE_WHILE = re.compile(r'^while +([^\n]+)')
    RE_EACH = re.compile(r'^(?:- *)?(?:each|for) +([\w, ]+) +in +([^\n]+)')
    RE_CODE = re.compile(r'^(!?=|-)([^\n]+)')
    RE_ATTR_INTERPOLATE = re.compile(r'#\{([^}]+)\}')
    RE_ATTR_PARSE = re.compile(r'''^['"]|['"]$''')
    RE_INDENT_TABS = re.compile(r'^\n(\t*) *')
    RE_INDENT_SPACES = re.compile(r'^\n( *)')
    RE_COLON = re.compile(r'^: *')
    # RE_ = re.compile(r'')

    def __init__(self, string, **options):
        if isinstance(string, six.binary_type):
            string = six.text_type(string, 'utf8')
        self.options = options
        self.input = self.RE_INPUT.sub('\n', string)
        self.colons = self.options.get('colons', False)
        self.deferredTokens = deque()
        self.lastIndents = 0
        self.lineno = 1
        self.stash = deque()
        self.indentStack = deque()
        self.indentRe = None
        self.pipeless = False

    def tok(self, type, val=None):
        return Token(type=type, line=self.lineno, val=val)

    def consume(self, len):
        self.input = self.input[len:]

    def scan(self, regexp, type):
        captures = regexec(regexp, self.input)
        # print regexp,type, self.input, captures
        if captures:
            # print captures
            self.consume(len(captures[0]))
            # print 'a',self.input
            if len(captures) == 1:
                return self.tok(type, None)
            return self.tok(type, captures[1])

    def defer(self, tok):
        self.deferredTokens.append(tok)

    def lookahead(self, n):
        # print self.stash
        fetch = n - len(self.stash)
        while True:
            fetch -= 1
            if not fetch >= 0:
                break
            self.stash.append(self.next())
        return self.stash[n - 1]

    def indexOfDelimiters(self, start, end):
        str, nstart, nend, pos = self.input, 0, 0, 0
        for i, s in enumerate(str):
            if start == s:
                nstart += 1
            elif end == s:
                nend += 1
                if nend == nstart:
                    pos = i
                    break
        return pos

    def stashed(self):
        # print self.stash
        return len(self.stash) and self.stash.popleft()

    def deferred(self):
        return len(self.deferredTokens) and self.deferredTokens.popleft()

    def eos(self):
        # print 'eos',bool(self.input)
        if self.input:
            return
        if self.indentStack:
            self.indentStack.popleft()
            return self.tok('outdent')
        else:
            return self.tok('eos')

    def blank(self):
        if self.pipeless:
            return
        captures = regexec(self.RE_BLANK, self.input)
        if captures:
            self.consume(len(captures[0]) - 1)
            return self.next()

    def comment(self):
        captures = regexec(self.RE_COMMENT, self.input)
        if captures:
            self.consume(len(captures[0]))
            tok = self.tok('comment', captures[2])
            tok.buffer = '-' != captures[1]
            return tok

    def tag(self):
        captures = regexec(self.RE_TAG, self.input)
        # print self.input,captures,re.match('^(\w[-:\w]*)',self.input)
        if captures:
            self.consume(len(captures[0]))
            name = captures[1]
            if name.endswith(':'):
                name = name[:-1]
                tok = self.tok('tag', name)
                self.defer(self.tok(':'))
                while self.input[0] == ' ':
                    self.input = self.input[1:]
            else:
                tok = self.tok('tag', name)
            return tok

    def filter(self):
        return self.scan(self.RE_FILTER, 'filter')

    def doctype(self):
        # print self.scan(self.RE_DOCTYPE, 'doctype')
        return self.scan(self.RE_DOCTYPE, 'doctype')

    def id(self):
        return self.scan(self.RE_ID, 'id')

    def className(self):
        return self.scan(self.RE_CLASS, 'class')

    def string(self):
        return self.scan(self.RE_STRING, 'string')

    def text(self):
        return self.scan(self.RE_TEXT, 'text')

    def extends(self):
        return self.scan(self.RE_EXTENDS, 'extends')

    def prepend(self):
        captures = regexec(self.RE_PREPEND, self.input)
        if captures:
            self.consume(len(captures[0]))
            mode, name = 'prepend', captures[1]
            tok = self.tok('block', name)
            tok.mode = mode
            return tok

    def append(self):
        captures = regexec(self.RE_APPEND, self.input)
        if captures:
            self.consume(len(captures[0]))
            mode, name = 'append', captures[1]
            tok = self.tok('block', name)
            tok.mode = mode
            return tok

    def block(self):
        captures = regexec(self.RE_BLOCK, self.input)
        if captures:
            self.consume(len(captures[0]))
            mode = captures[3] or 'replace'
            name = captures[4] or ''
            tok = self.tok('block', name)
            tok.mode = mode
            return tok

    def _yield(self):
        return self.scan(self.RE_YIELD, 'yield')

    def include(self):
        return self.scan(self.RE_INCLUDE, 'include')

    def assignment(self):
        captures = regexec(self.RE_ASSIGNMENT, self.input)
        if captures:
            self.consume(len(captures[0]))
            name, val = captures[2:4]
            tok = self.tok('assignment')
            tok.name = name
            tok.val = val
            return tok

    def mixin(self):
        captures = regexec(self.RE_MIXIN, self.input)
        if captures:
            self.consume(len(captures[0]))
            tok = self.tok('mixin', captures[1])
            tok.args = captures[2]
            return tok

    def call(self):
        captures = regexec(self.RE_CALL, self.input)
        if captures:
            self.consume(len(captures[0]))
            tok = self.tok('call', captures[1])
            tok.args = captures[2]
            return tok

    def conditional(self):
        captures = regexec(self.RE_CONDITIONAL, self.input)
        if captures:
            self.consume(len(captures[0]))
            type, sentence = captures[1:]
            tok = self.tok('conditional', type)
            tok.sentence = sentence
            return tok

    # def _while(self):
    #     captures = regexec(self.RE_WHILE,self.input)
    #     if captures:
    #         self.consume(len(captures[0]))
    #         return self.tok('code','while(%s)'%captures[1])

    def each(self):
        captures = regexec(self.RE_EACH, self.input)
        if captures:
            self.consume(len(captures[0]))
            tok = self.tok('each', None)
            tok.keys = [x.strip() for x in captures[1].split(',')]
            tok.code = captures[2]
            return tok

    def code(self):
        captures = regexec(self.RE_CODE, self.input)
        if captures:
            self.consume(len(captures[0]))
            flags, name = captures[1:]
            tok = self.tok('code', name)
            tok.escape = flags.startswith('=')
            #print captures
            tok.buffer = '=' in flags 
            # print tok.buffer
            return tok

    def attrs(self):
        if '(' == self.input[0]:
            index = self.indexOfDelimiters('(', ')')
            string = self.input[1:index]
            tok = self.tok('attrs')
            l = len(string)
            colons = self.colons
            states = ['key']

            class Namespace:
                key = u''
                val = u''
                quote = u''
                literal = True

                def reset(self):
                    self.key = self.val = self.quote = u''
                    self.literal = True

                def __str__(self):
                    return dict(key=self.key, val=self.val, quote=self.quote,
                                literal=self.literal).__str__()
            ns = Namespace()

            def state():
                return states[-1]

            def interpolate(attr):
                attr, num = self.RE_ATTR_INTERPOLATE.subn(lambda matchobj: '%s+%s+%s' % (ns.quote, matchobj.group(1), ns.quote), attr)
                return attr, (num > 0)

            self.consume(index + 1)
            from .utils import odict
            tok.attrs = odict()
            tok.static_attrs = set()
            str_nums = list(map(str, range(10)))
            # print '------'
            def parse(c):
                real = c
                if colons and ':' == c:
                    c = '='
                ns.literal = ns.literal and (state() not in ('object', 'array',
                                                             'expr'))
                # print ns, c, states
                if c in (',', '\n') or (c == ' ' and state() == 'val' and len(states) == 2 and ns.val.strip()):
                    s = state()
                    if s in ('expr', 'array', 'string', 'object'):
                        ns.val += c
                    else:
                        states.append('key')
                        ns.val = ns.val.strip()
                        ns.key = ns.key.strip()
                        if not ns.key:
                            return
                        # ns.literal = ns.quote
                        if not ns.literal:
                            if '!' == ns.key[-1]:
                                ns.literal = True
                                ns.key = ns.key[:-1]
                        ns.key = ns.key.strip("'\"")
                        if not ns.val:
                            tok.attrs[ns.key] = True
                        else:
                            tok.attrs[ns.key], is_interpolated = interpolate(ns.val)
                            ns.literal = ns.literal and not is_interpolated
                        if ns.literal:
                            tok.static_attrs.add(ns.key)
                        ns.reset()
                elif '=' == c:
                    s = state()
                    if s == 'key char':
                        ns.key += real
                    elif s in ('val', 'expr', 'array', 'string', 'object'):
                        ns.val += real
                    else:
                        states.append('val')
                elif '(' == c:
                    if state() in ('val', 'expr'):
                        states.append('expr')
                    ns.val += c
                elif ')' == c:
                    if state() in ('val', 'expr'):
                        states.pop()
                    ns.val += c
                elif '{' == c:
                    if 'val' == state():
                        states.append('object')
                    ns.val += c
                elif '}' == c:
                    if 'object' == state():
                        states.pop()
                    ns.val += c
                elif '[' == c:
                    if 'val' == state():
                        states.append('array')
                    ns.val += c
                elif ']' == c:
                    if 'array' == state():
                        states.pop()
                    ns.val += c
                elif c in ('"', "'"):
                    s = state()
                    if 'key' == s:
                        states.append('key char')
                    elif 'key char' == s:
                        states.pop()
                    elif 'string' == s:
                        if c == ns.quote:
                            states.pop()
                        ns.val += c
                    else:
                        states.append('string')
                        ns.val += c
                        ns.quote = c
                elif '' == c:
                    pass
                else:
                    s = state()
                    ns.literal = ns.literal and (s in ('key', 'string') or c in str_nums)
                    # print c, s, ns.literal
                    if s in ('key', 'key char'):
                        ns.key += c
                    else:
                        ns.val += c

            for char in string:
                parse(char)

            parse(',')

            return tok

    def indent(self):
        if self.indentRe:
            captures = regexec(self.indentRe, self.input)
        else:
            regex = self.RE_INDENT_TABS
            captures = regexec(regex, self.input)
            if captures and not captures[1]:
                regex = self.RE_INDENT_SPACES
                captures = regexec(regex, self.input)
            if captures and captures[1]:
                self.indentRe = regex

        if captures:
            indents = len(captures[1])
            self.lineno += 1
            self.consume(indents + 1)

            if not self.input:
                return self.tok('newline')
            if self.input[0] in (' ', '\t'):
                raise Exception('Invalid indentation, you can use tabs or spaces but not both')

            if '\n' == self.input[0]:
                return self.tok('newline')

            if self.indentStack and indents < self.indentStack[0]:
                while self.indentStack and self.indentStack[0] > indents:
                    self.stash.append(self.tok('outdent'))
                    self.indentStack.popleft()
                tok = self.stash.pop()
            elif indents and (not self.indentStack or indents != self.indentStack[0]):
                self.indentStack.appendleft(indents)
                tok = self.tok('indent', indents)
            else:
                tok = self.tok('newline')

            return tok

    def pipelessText(self):
        if self.pipeless:
            if '\n' == self.input[0]:
                return
            i = self.input.find('\n')
            if -1 == i:
                i = len(self.input)
            str = self.input[:i]
            self.consume(len(str))
            return self.tok('text', str)

    def colon(self):
        return self.scan(self.RE_COLON, ':')

    def advance(self):
        return self.stashed() or self.next()

    def next(self):
        return self.deferred() \
            or self.blank() \
            or self.eos() \
            or self.pipelessText() \
            or self._yield() \
            or self.doctype() \
            or self.extends() \
            or self.append() \
            or self.prepend() \
            or self.block() \
            or self.include() \
            or self.mixin() \
            or self.call() \
            or self.conditional() \
            or self.each() \
            or self.assignment() \
            or self.tag() \
            or self.filter() \
            or self.code() \
            or self.id() \
            or self.className() \
            or self.attrs() \
            or self.indent() \
            or self.comment() \
            or self.colon() \
            or self.string() \
            or self.text()

            ##or self._while() \

########NEW FILE########
__FILENAME__ = nodes
from collections import deque
import six

class Node(object):
	debug = False
	def __str__(self):
		return self.__dict__.__str__()
class BlockComment(Node):
	def __init__(self,val,block,buffer):
		self.block = block
		self.val = val
		self.buffer = buffer

class Block(Node):
	def __init__(self,node=None):
		self.nodes = deque()
		self.debug = False
		if node: self.append(node)

	def replace(self,other):
		other.nodes = self.nodes

	def append(self,node):
		return self.nodes.append(node)

	def prepend(self,node):
		return self.nodes.appendleft(node)

	def isEmpty(self):
		return bool(self.nodes)

	def unshift(self,node):
		return self.nodes.unshift(node)

class CodeBlock(Block): pass

class Code(Node):
	def __init__(self,val,buffer,escape):
		self.val = val
		self.block=None
		self.buffer = buffer
		self.escape = escape
class Comment(Node):
	def __init__(self,val,buffer):
		self.val = val
		self.buffer = buffer


class Doctype(Node):
	def __init__(self,val):
		self.val = val

class Each(Node):
	def __init__(self,obj, keys, block=None):
		self.obj = obj
		self.keys = keys
		self.block = block

class Assignment(Node):
	def __init__(self,name, val):
		self.name = name
		self.val = val

class Mixin(Node):
	def __init__(self, name, args, block, call):
		self.name = name
		self.args = args
		self.block = block
		self.call = call

class Extends(Node):
	def __init__(self,path):
		self.path = path

class Include(Node):
	def __init__(self,path,extra=None):
		self.path = path
		self.extra = extra

class Conditional(Node):
	may_contain_tags = {'if': ['elif', 'else'],
						'for': ['else'],
						'elif': ['elif','else'],
						'unless': ['elif', 'else']}
	def __init__(self,type, sentence, block=None):
		self.type = type
		self.sentence = sentence
		self.block = block
		self.next = []
	def can_append(self,type):
		n = (self.next and self.next[-1].type) or self.type
		return type in self.may_contain_tags.get(n,[])
	def append(self,next):
		self.next.append(next)

class Filter(Node):
	def __init__(self,name, block, attrs):
		self.name = name
		self.block = block
		self.attrs = attrs
		self.isASTFilter = isinstance(block,Block)

class Literal(Node):
	def __init__(self,str):
		self.str = str.replace('\\','\\\\')

class Tag(Node):
	def __init__(self,name, block=None, inline=False):
		self.name = name
		self.textOnly = False
		self.code = None
		self.text = None
		self._attrs = []
		self.inline = inline
		self.block = block or Block()

	@classmethod
	def static(self, string, only_remove=False):
		if not isinstance(string,six.string_types) or not string: return string
		if string[0] in ('"',"'"):
			if string[0]==string[-1]: string = string[1:-1]
			else: return string
		if only_remove: return string
		return '"%s"'%string

	def setAttribute(self,name,val,static=True):
		self._attrs.append(dict(name=name,val=val,static=static))
		return self

	def removeAttribute(self,name):
		for attr in self._attrs:
			if attr and attr['name'] == name: self._attrs.remove(attr)

	def getAttribute(self,name):
		for attr in self._attrs:
			if attr and attr['name'] == name: return attr['val']

	@property
	def attrs(self):
		attrs = []
		classes = []
		static_classes = True
		for attr in self._attrs:
			name = attr['name']
			val = attr['val']
			static = attr['static'] # and isinstance(val,six.string_types)
			if static:
				val = self.static(val)
			if val in ("True","False","None"):
				val = val=="True"
				static = True
			d = dict(name=name,val=val,static=static)
			if name=='class':
				static_classes = static_classes and static
				classes.append(d)
			else:
				attrs.append(d)
		if classes:
			if static_classes:
				classes = [dict(name='class', val='"%s"'%' '.join([a['val'][1:-1] for a in classes]), static=True)]
			else:
				for attr in classes: attr['static'] = static_classes
		return attrs+classes

class Text(Node):
	parent = None

	def __init__(self, line=None):
		self.nodes = []
		if isinstance(line,six.string_types): self.append(line)

	def append(self,node):
		return self.nodes.append(node)

class String(Text): pass

########NEW FILE########
__FILENAME__ = parser
from __future__ import absolute_import
from .lexer import Lexer
from . import nodes
import six

textOnly = ('script','style')

class Parser(object):
    def __init__(self,str,filename=None,**options):
        self.input = str
        self.lexer = Lexer(str,**options)
        self.filename = filename
        self.bloks = {}
        self.options = options
        self.contexts = [self]
        self.extending = False
        self._spaces = None

    def context(self,parser):
        if parser: self.context.append(parser)
        else: self.contexts.pop()

    def advance(self):
        return self.lexer.advance()

    def skip(self,n):
        while n>1: # > 0?
            self.advance()
            n -= 1

    def peek(self):
        p = self.lookahead(1)
        return p

    def line(self):
        return self.lexer.lineno

    def lookahead(self,n):
        return self.lexer.lookahead(n)

    def parse (self):
        block = nodes.Block()
        parser = None
        block.line = self.line()

        while 'eos' != self.peek().type:
            if 'newline' == self.peek().type: self.advance()
            else: block.append(self.parseExpr())

        parser = self.extending
        if parser:
            self.context(parser)
            ast = parser.parse()
            self.context()
            return ast

        return block

    def expect(self,type):
        t = self.peek().type
        if t == type: return self.advance()
        else:
            raise Exception('expected "%s" but got "%s" in file %s on line %d' %
                            (type, t, self.filename, self.line()))

    def accept(self,type):
        if self.peek().type == type: return self.advance()

    def parseExpr(self):
        t = self.peek().type
        if 'yield' == t:
            self.advance()
            block = nodes.Block()
            block._yield = True
            return block
        elif t in ('id','class'):
            tok = self.advance()
            self.lexer.defer(self.lexer.tok('tag','div'))
            self.lexer.defer(tok)
            return self.parseExpr()

        funcName = 'parse%s'%t.capitalize()
        if hasattr(self,funcName):
            return getattr(self,funcName)()
        else:
            raise Exception('unexpected token "%s" in file %s on line %d' %
                            (t, self.filename, self.line()))

    def parseString(self):
        tok = self.expect('string')
        node = nodes.String(tok.val)
        node.line = self.line()
        return node

    def parseText(self):
        tok = self.expect('text')
        node = nodes.Text(tok.val)
        node.line = self.line()
        return node

    def parseBlockExpansion(self):
        if ':'== self.peek().type:
            self.advance()
            return nodes.Block(self.parseExpr())
        else:
            return self.block()

    def parseAssignment(self):
        tok = self.expect('assignment')
        return nodes.Assignment(tok.name,tok.val)

    def parseCode(self):
        tok = self.expect('code')
        node = nodes.Code(tok.val,tok.buffer,tok.escape) #tok.escape
        block,i = None,1
        node.line = self.line()
        while self.lookahead(i) and 'newline'==self.lookahead(i).type:
            i+= 1
        block = 'indent' == self.lookahead(i).type
        if block:
            self.skip(i-1)
            node.block = self.block()
        return node

    def parseComment(self):
        tok = self.expect('comment')

        if 'indent'==self.peek().type:
            node = nodes.BlockComment(tok.val, self.block(), tok.buffer)
        else:
            node = nodes.Comment(tok.val,tok.buffer)

        node.line = self.line()
        return node

    def parseDoctype(self):
        tok = self.expect('doctype')
        node = nodes.Doctype(tok.val)
        node.line = self.line()
        return node

    def parseFilter(self):
        tok = self.expect('filter')
        attrs = self.accept('attrs')
        self.lexer.pipeless = True
        block = self.parseTextBlock()
        self.lexer.pipeless = False

        node = nodes.Filter(tok.val, block, attrs and attrs.attrs)
        node.line = self.line()
        return node

    def parseASTFilter(self):
        tok = self.expect('tag')
        attrs = self.accept('attrs')

        self.expect(':')
        block = self.block()

        node = nodes.Filter(tok.val, block, attrs and attrs.attrs)
        node.line = self.line()
        return node

    def parseEach(self):
        tok = self.expect('each')
        node = nodes.Each(tok.code, tok.keys)
        node.line = self.line()
        node.block = self.block()
        return node

    def parseConditional(self):
        tok = self.expect('conditional')
        node = nodes.Conditional(tok.val, tok.sentence)
        node.line = self.line()
        node.block = self.block()
        while True:
            t = self.peek()
            if 'conditional' == t.type and node.can_append(t.val):
                node.append(self.parseConditional())
            else:
                break
        return node

    def parseExtends(self):
        path = self.expect('extends').val.strip('"\'')
        return nodes.Extends(path)

    def parseCall(self):
        tok = self.expect('call')
        name = tok.val
        args = tok.args
        if args is None:
            args = ""
        block = self.block() if 'indent' == self.peek().type else None
        return nodes.Mixin(name,args,block,True)

    def parseMixin(self):
        tok = self.expect('mixin')
        name = tok.val
        args = tok.args
        if args is None:
            args = ""
        block = self.block() if 'indent' == self.peek().type else None
        return nodes.Mixin(name,args,block,block is None)

    def parseBlock(self):
        block = self.expect('block')
        mode = block.mode
        name = block.val.strip()
        block = self.block(cls=nodes.CodeBlock) if 'indent'==self.peek().type else nodes.CodeBlock(nodes.Literal(''))
        block.mode = mode
        block.name = name
        return block

    def parseInclude(self):
        path = self.expect('include').val.strip()
        return nodes.Include(path)

    def parseTextBlock(self, tag=None):
        text = nodes.Text()
        text.line = self.line()
        if (tag):
            text.parent == tag
        spaces = self.expect('indent').val
        if not self._spaces: self._spaces = spaces
        indent = ' '*(spaces-self._spaces)
        while 'outdent' != self.peek().type:
            t = self.peek().type
            if 'newline'==t:
                text.append('\n')
                self.advance()
            elif 'indent'==t:
                text.append('\n')
                for node in self.parseTextBlock().nodes: text.append(node)
                text.append('\n')
            else:
                text.append(indent+self.advance().val)

        if spaces == self._spaces: self._spaces = None
        self.expect('outdent')
        return text

    def block(self,cls=nodes.Block):
        block = cls()
        block.line = self.line()
        self.expect('indent')
        while 'outdent' != self.peek().type:
            if 'newline'== self.peek().type:
                self.advance()
            else:
                block.append(self.parseExpr())
        self.expect('outdent')
        return block

    def parseTag(self):
        i = 2
        if 'attrs'==self.lookahead(i).type: i += 1
        if ':'==self.lookahead(i).type:
            if 'indent' == self.lookahead(i+1).type:
                return self.parseASTFilter

        name = self.advance().val
        tag = nodes.Tag(name)
        dot = None

        tag.line = self.line()

        while True:
            t = self.peek().type
            if t in ('id','class'):
                tok = self.advance()
                tag.setAttribute(tok.type,'"%s"'%tok.val,True)
                continue
            # if t=='id':
            #     tok = self.advance()
            #     tag.setId(tok.val)
            #     continue
            # elif t=='class':
            #     tok = self.advance()
            #     tag.addClass(tok.val)
            #     continue
            elif 'attrs'==t:
                tok = self.advance()
                for n,v in six.iteritems(tok.attrs):
                    tag.setAttribute(n,v,n in tok.static_attrs)
                continue
            else:
                break

        v = self.peek().val
        if '.'== v:
            dot = tag.textOnly = True
            self.advance()
        elif '<'== v: #For inline elements
            tag.inline = True
            self.advance()

        t = self.peek().type
        if 'string'==t: tag.text = self.parseString()
        elif 'text'==t: tag.text = self.parseText()
        elif 'code'==t: tag.code = self.parseCode()
        elif ':'==t:
            self.advance()
            tag.block = nodes.Block()
            tag.block.append(self.parseExpr())

        while 'newline' == self.peek().type: self.advance()

        tag.textOnly = tag.textOnly or tag.name in textOnly

        if 'script'== tag.name:
            type = tag.getAttribute('type')
            if not dot and type and 'text/javascript' !=type.strip('"\''): tag.textOnly = False

        if 'indent' == self.peek().type:
            if tag.textOnly:
                self.lexer.pipeless = True
                tag.block = self.parseTextBlock(tag)
                self.lexer.pipeless = False
            else:
                block = self.block()
                if tag.block:
                    for node in block.nodes:
                        tag.block.append(node)
                else:
                    tag.block = block

        return tag

########NEW FILE########
__FILENAME__ = runtime
from __future__ import absolute_import
from .utils import odict
import types
import six
from itertools import chain

try:
    from collections import Mapping as MappingType
except ImportError:
    import UserDict
    MappingType = (UserDict.UserDict, UserDict.DictMixin, dict)

def flatten(l, ltypes=(list, tuple)):
    ltype = type(l)
    l = list(l)
    i = 0
    while i < len(l):
        while isinstance(l[i], ltypes):
            if not l[i]:
                l.pop(i)
                i -= 1
                break
            else:
                l[i:i + 1] = l[i]
        i += 1
    return ltype(l)

def escape(s):
    """Convert the characters &, <, >, ' and " in string s to HTML-safe
    sequences.  Use this if you need to display text that might contain
    such characters in HTML.  Marks return value as markup string.
    """
    if hasattr(s, '__html__'):
        return s.__html__()
    if isinstance(s, six.binary_type):
        s = six.text_type(str(s), 'utf8')
    elif isinstance(s, six.text_type):
        s = s
    else:
        s = str(s)

    return (s
        .replace('&', '&amp;')
        .replace('>', '&gt;')
        .replace('<', '&lt;')
        .replace("'", '&#39;')
        .replace('"', '&#34;')
    )

def attrs (attrs=[],terse=False, undefined=None):
    buf = []
    if bool(attrs):
        buf.append(u'')
        for k,v in attrs:
            if undefined is not None and isinstance(v, undefined):
                continue
            if v!=None and (v!=False or type(v)!=bool):
                if k=='class' and isinstance(v, (list, tuple)):
                    v = u' '.join(map(str,flatten(v)))
                t = v==True and type(v)==bool
                if t and not terse: v=k
                buf.append(u'%s'%k if terse and t else u'%s="%s"'%(k,escape(v)))
    return u' '.join(buf)


def is_mapping(value):
    return isinstance(value, MappingType)


def is_iterable(ob):
    if isinstance(ob, six.string_types):
        return False
    try:
        iter(ob)
        return True
    except TypeError:
        return False


def get_cardinality(ob):
    if isinstance(ob, six.string_types):
        return 1
    try:
        return len(ob)
    except TypeError:
        return 1


def iteration(obj, num_keys):
    """
    Jade iteration supports "for 'value' [, key]?" iteration only.
    PyJade has implicitly supported value unpacking instead, without
    the list indexes. Trying to not break existing code, the following
    rules are applied:

      1. If the object is a mapping type, return it as-is, and assume
         the caller has the correct set of keys defined.

      2. If the object's values are iterable (and not string-like):
         a. If the number of keys matches the cardinality of the object's
            values, return the object as-is.
         b. If the number of keys is one more than the cardinality of
            values, return a list of [v(0), v(1), ... v(n), index]

      3. Else the object's values are not iterable, or are string like:
         a. if there's only one key, return the list
         b. otherwise return a list of (value,index) tuples

    """

    # If the object is a mapping type, return it as-is
    if is_mapping(obj):
        return obj

    _marker = []

    iter_obj = iter(obj)
    head = next(iter_obj, _marker)
    iter_obj = chain([head], iter_obj)

    if head is _marker:
        # Empty list
        return []

    if is_iterable(head):
        if num_keys == get_cardinality(head) + 1:
            return (tuple(item) + (ix,) for ix, item in enumerate(iter_obj))
        else:
            return iter_obj

    elif num_keys == 2:
        return ((item, ix) for ix, item in enumerate(iter_obj))

    else:
        return iter_obj

########NEW FILE########
__FILENAME__ = test_cases
from __future__ import print_function
import pyjade
import pyjade.ext.html
from pyjade.utils import process
from pyjade.exceptions import CurrentlyNotSupported
import six

from nose import with_setup

processors =  {}
jinja_env = None

def teardown_func():
    pass


try:
    from jinja2 import Environment, FileSystemLoader
    from pyjade.ext.jinja import PyJadeExtension
    jinja_env = Environment(extensions=[PyJadeExtension], loader=FileSystemLoader('cases/'))
    def jinja_process (src, filename):
        global jinja_env
        template = jinja_env.get_template(filename)
        return template.render()

    processors['Jinja2'] = jinja_process
except ImportError:
    pass

# Test jinja2 with custom variable syntax: "{%#.-.** variable **.-.#%}"
try:
    from jinja2 import Environment, FileSystemLoader
    from pyjade.ext.jinja import PyJadeExtension
    jinja_env = Environment(extensions=[PyJadeExtension], loader=FileSystemLoader('cases/'),
			variable_start_string = "{%#.-.**", variable_end_string="**.-.#%}"
    )
    def jinja_process_variable_start_string (src, filename):
        global jinja_env
        template = jinja_env.get_template(filename)
        return template.render()

    processors['Jinja2-variable_start_string'] = jinja_process_variable_start_string
except ImportError:
    pass

try:
    import tornado.template
    from pyjade.ext.tornado import patch_tornado
    patch_tornado()

    loader = tornado.template.Loader('cases/')
    def tornado_process (src, filename):
        global loader, tornado
        template = tornado.template.Template(src,name='_.jade',loader=loader)
        generated = template.generate()
        if isinstance(generated, six.binary_type):
            generated = generated.decode("utf-8")
        return generated

    processors['Tornado'] = tornado_process
except ImportError:
    pass

try:
    from django.conf import settings
    settings.configure(
        TEMPLATE_DIRS=("cases/",),
        TEMPLATE_LOADERS = (
        ('pyjade.ext.django.Loader', (
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        )),
        )
    )
    import django.template
    import django.template.loader
    from pyjade.ext.django import Compiler as DjangoCompiler

    def django_process(src, filename):
        compiled = process(src, filename=filename,compiler = DjangoCompiler)
        print(compiled)
        t = django.template.Template(compiled)

        ctx = django.template.Context()
        return t.render(ctx)

    processors['Django'] = django_process
except ImportError:
    pass

try:
    import pyjade.ext.mako
    import mako.template
    from mako.lookup import TemplateLookup
    dirlookup = TemplateLookup(directories=['cases/'],preprocessor=pyjade.ext.mako.preprocessor)

    def mako_process(src, filename):
        t = mako.template.Template(src, lookup=dirlookup,preprocessor=pyjade.ext.mako.preprocessor, default_filters=['decode.utf8'])
        return t.render()

    processors['Mako'] = mako_process

except ImportError:
    pass

def setup_func():
    global jinja_env, processors

def html_process(src, filename):
    return pyjade.ext.html.process_jade(src)

processors['Html'] = html_process

def run_case(case,process):
    global processors
    processor = processors[process]
    jade_file = open('cases/%s.jade'%case)
    jade_src = jade_file.read()
    if isinstance(jade_src, six.binary_type):
        jade_src = jade_src.decode('utf-8')
    jade_file.close()

    html_file = open('cases/%s.html'%case)
    html_src = html_file.read().strip('\n')
    if isinstance(html_src, six.binary_type):
        html_src = html_src.decode('utf-8')
    html_file.close()
    try:
        processed_jade = processor(jade_src, '%s.jade'%case).strip('\n')
        print('PROCESSED\n',processed_jade,len(processed_jade))
        print('EXPECTED\n',html_src,len(html_src))
        assert processed_jade==html_src

    except CurrentlyNotSupported:
        pass

exclusions = {
    'Html': set(['mixins', 'mixin.blocks', 'layout', 'unicode']),
    'Mako': set(['layout']),
    'Tornado': set(['layout']),
    'Jinja2': set(['layout']),
    'Jinja2-variable_start_string': set(['layout']),
    'Django': set(['layout'])}
    

@with_setup(setup_func, teardown_func)
def test_case_generator():
    global processors

    import os
    import sys
    for dirname, dirnames, filenames in os.walk('cases/'):
        # raise Exception(filenames)
        filenames = filter(lambda x:x.endswith('.jade'),filenames)
        filenames = list(map(lambda x:x.replace('.jade',''),filenames))
        for processor in processors.keys():
            for filename in filenames:
                if not filename in exclusions[processor]:
                    yield run_case, filename,processor

########NEW FILE########
__FILENAME__ = test_runtime
from pyjade import runtime


class TestIteration(object):

    def test_it_returns_mappings_unaltered(self):
        mapping = {}
        assert runtime.iteration(mapping, 1) is mapping

    def test_it_returns_empty_list_on_empty_input(self):
        l = iter([])
        assert list(runtime.iteration(l, 1)) == []

    def test_it_iterates_as_is_if_numkeys_is_same_as_cardinality(self):
        l = [(1, 2), (3, 4)]
        assert list(runtime.iteration(l, 2)) == l

    def test_it_extends_with_index_if_items_are_iterable(self):
        l = [('a',), ('b',)]
        assert list(runtime.iteration(l, 2)) == [('a', 0), ('b', 1)]

    def test_it_adds_index_if_items_are_strings(self):
        l = ['a', 'b']
        assert list(runtime.iteration(l, 2)) == [('a', 0), ('b', 1)]

    def test_it_adds_index_if_items_are_non_iterable(self):
        l = [1, 2]
        assert list(runtime.iteration(l, 2)) == [(1, 0), (2, 1)]

    def test_it_doesnt_swallow_first_item_of_iterators(self):
        l = [1, 2]
        iterator = iter(l)
        assert list(runtime.iteration(iterator, 1)) == l

########NEW FILE########
__FILENAME__ = utils
from __future__ import absolute_import
try:
    from itertools import izip, imap
except:
    izip, imap = zip, map
from copy import deepcopy
import six

from .compiler import Compiler

missing = object()

class odict(dict):
    """
    Ordered dict example implementation.

    This is the proposed interface for a an ordered dict as proposed on the
    Python mailinglist (proposal_).

    It's a dict subclass and provides some list functions.  The implementation
    of this class is inspired by the implementation of Babel but incorporates
    some ideas from the `ordereddict`_ and Django's ordered dict.

    The constructor and `update()` both accept iterables of tuples as well as
    mappings:

    >>> d = odict([('a', 'b'), ('c', 'd')])
    >>> d.update({'foo': 'bar'})
    >>> d
    odict.odict([('a', 'b'), ('c', 'd'), ('foo', 'bar')])

    Keep in mind that when updating from dict-literals the order is not
    preserved as these dicts are unsorted!

    You can copy an odict like a dict by using the constructor, `copy.copy`
    or the `copy` method and make deep copies with `copy.deepcopy`:

    >>> from copy import copy, deepcopy
    >>> copy(d)
    odict.odict([('a', 'b'), ('c', 'd'), ('foo', 'bar')])
    >>> d.copy()
    odict.odict([('a', 'b'), ('c', 'd'), ('foo', 'bar')])
    >>> odict(d)
    odict.odict([('a', 'b'), ('c', 'd'), ('foo', 'bar')])
    >>> d['spam'] = []
    >>> d2 = deepcopy(d)
    >>> d2['spam'].append('eggs')
    >>> d
    odict.odict([('a', 'b'), ('c', 'd'), ('foo', 'bar'), ('spam', [])])
    >>> d2
    odict.odict([('a', 'b'), ('c', 'd'), ('foo', 'bar'), ('spam', ['eggs'])])

    All iteration methods as well as `keys`, `values` and `items` return
    the values ordered by the the time the key-value pair is inserted:

    >>> d.keys()
    ['a', 'c', 'foo', 'spam']
    >>> d.values()
    ['b', 'd', 'bar', []]
    >>> d.items()
    [('a', 'b'), ('c', 'd'), ('foo', 'bar'), ('spam', [])]
    >>> list(d.iterkeys())
    ['a', 'c', 'foo', 'spam']
    >>> list(d.itervalues())
    ['b', 'd', 'bar', []]
    >>> list(d.iteritems())
    [('a', 'b'), ('c', 'd'), ('foo', 'bar'), ('spam', [])]

    Index based lookup is supported too by `byindex` which returns the
    key/value pair for an index:

    >>> d.byindex(2)
    ('foo', 'bar')

    You can reverse the odict as well:

    >>> d.reverse()
    >>> d
    odict.odict([('spam', []), ('foo', 'bar'), ('c', 'd'), ('a', 'b')])

    And sort it like a list:

    >>> d.sort(key=lambda x: x[0].lower())
    >>> d
    odict.odict([('a', 'b'), ('c', 'd'), ('foo', 'bar'), ('spam', [])])

    .. _proposal: http://thread.gmane.org/gmane.comp.python.devel/95316
    .. _ordereddict: http://www.xs4all.nl/~anthon/Python/ordereddict/
    """

    def __init__(self, *args, **kwargs):
        dict.__init__(self)
        self._keys = []
        self.update(*args, **kwargs)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._keys.remove(key)

    def __setitem__(self, key, item):
        if key not in self:
            self._keys.append(key)
        dict.__setitem__(self, key, item)

    def __deepcopy__(self, memo=None):
        if memo is None:
            memo = {}
        d = memo.get(id(self), missing)
        if d is not missing:
            return d
        memo[id(self)] = d = self.__class__()
        dict.__init__(d, deepcopy(self.items(), memo))
        d._keys = self._keys[:]
        return d

    def __getstate__(self):
        return {'items': dict(self), 'keys': self._keys}

    def __setstate__(self, d):
        self._keys = d['keys']
        dict.update(d['items'])

    def __reversed__(self):
        return reversed(self._keys)

    def __eq__(self, other):
        if isinstance(other, odict):
            if not dict.__eq__(self, other):
                return False
            return self.items() == other.items()
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __cmp__(self, other):
        if isinstance(other, odict):
            return cmp(self.items(), other.items())
        elif isinstance(other, dict):
            return dict.__cmp__(self, other)
        return NotImplemented

    @classmethod
    def fromkeys(cls, iterable, default=None):
        return cls((key, default) for key in iterable)

    def clear(self):
        del self._keys[:]
        dict.clear(self)

    def copy(self):
        return self.__class__(self)

    def items(self):
        return list(zip(self._keys, self.values()))

    def iteritems(self):
        return izip(self._keys, self.itervalues())

    def keys(self):
        return self._keys[:]

    def iterkeys(self):
        return iter(self._keys)

    def pop(self, key, default=missing):
        if default is missing:
            return dict.pop(self, key)
        elif key not in self:
            return default
        self._keys.remove(key)
        return dict.pop(self, key, default)

    def popitem(self, key):
        self._keys.remove(key)
        return dict.popitem(key)

    def setdefault(self, key, default=None):
        if key not in self:
            self._keys.append(key)
        dict.setdefault(self, key, default)

    def update(self, *args, **kwargs):
        sources = []
        if len(args) == 1:
            if hasattr(args[0], 'items'):
                sources.append(six.iteritems(args[0]))
            else:
                sources.append(iter(args[0]))
        elif args:
            raise TypeError('expected at most one positional argument')
        if kwargs:
            sources.append(kwargs.iteritems())
        for iterable in sources:
            for key, val in iterable:
                self[key] = val

    def values(self):
        return list(map(self.get, self._keys))

    def itervalues(self):
        return imap(self.get, self._keys)

    def index(self, item):
        return self._keys.index(item)

    def byindex(self, item):
        key = self._keys[item]
        return (key, dict.__getitem__(self, key))

    def reverse(self):
        self._keys.reverse()

    def sort(self, *args, **kwargs):
        self._keys.sort(*args, **kwargs)

    def __repr__(self):
        return 'odict.odict(%r)' % self.items()

    __copy__ = copy
    __iter__ = iterkeys

from .parser import Parser
from .ext.html import Compiler as HTMLCompiler

def process(src,filename=None,parser=Parser,compiler=HTMLCompiler, **kwargs):
    _parser = parser(src,filename=filename)
    block = _parser.parse()
    _compiler = compiler(block, **kwargs)
    return _compiler.compile().strip()

########NEW FILE########
__FILENAME__ = test_jinja
from __future__ import print_function
import pyjade
a = pyjade.Parser('''doctype 5
html
    head: title Hello from flask
    body(attr="2" ba=2)
        if name
            h1(class="red") Hello 
                = name
            span.description #{name|capitalize} is a great name!
        else
            h1 Hello World!''')
block = a.parse()
import pyjade.ext.jinja
compiler = pyjade.ext.jinja.Compiler(block)
print(compiler.compile())
# OUT: <!DOCTYPE html>
# OUT: <html{{__pyjade_attrs(terse=True)}}>
# OUT:   <head{{__pyjade_attrs(terse=True)}}>
# OUT:     <title{{__pyjade_attrs(terse=True)}}>Hello from flask
# OUT:     </title>
# OUT:   </head>
# OUT:   <body{{__pyjade_attrs(terse=True, attrs=[('attr',("2" ba=2))])}}>{% if  name %}
# OUT:     <h1{{__pyjade_attrs(terse=True, attrs=[('class', (("red")))])}}>Hello {{name|escape}}
# OUT:     </h1><span{{__pyjade_attrs(terse=True, attrs=[('class', (('description')))])}}>{{name|capitalize}} is a great name!</span>{% else %}
# OUT:     <h1{{__pyjade_attrs(terse=True)}}>Hello World!
# OUT:     </h1>{% endif %}
# OUT:   </body>
# OUT: </html>

########NEW FILE########
