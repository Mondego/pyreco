__FILENAME__ = coverage_settings
from settings import *

TEST_RUNNER='coverage_test_runner.test_runner_with_coverage'

COVERAGE_MODULES = [
    'django_static.templatetags.django_static',
]

########NEW FILE########
__FILENAME__ = coverage_test_runner
from time import time
import os
import shutil
from django.test.simple import DjangoTestSuiteRunner

from django.conf import settings


import coverage
def test_runner_with_coverage(test_labels, verbosity=1, interactive=True, 
                              failfast=None, extra_tests=[]):
    """
    Custom test runner.  Follows the django.test.simple.run_tests() interface.
    """
    # Start code coverage before anything else if necessary
    if hasattr(settings, 'COVERAGE_MODULES'):
        cov = coverage.coverage()
        #coverage.use_cache(0) # Do not cache any of the coverage.py stuff
        cov.use_cache(0) # Do not cache any of the coverage.py stuff
        cov.start()

    test_runner = DjangoTestSuiteRunner(verbosity=verbosity, interactive=interactive, failfast=failfast)
    test_results = test_runner.run_tests(test_labels, extra_tests=extra_tests)

    # Stop code coverage after tests have completed
    if hasattr(settings, 'COVERAGE_MODULES'):
        cov.stop()

    # Print code metrics header
    print ''
    print '----------------------------------------------------------------------'
    print ' Unit Test Code Coverage Results'
    print '----------------------------------------------------------------------'

    # Report code coverage metrics
    if hasattr(settings, 'COVERAGE_MODULES'):
        coverage_modules = []
        for module in settings.COVERAGE_MODULES:
            coverage_modules.append(__import__(module, globals(), locals(), ['']))
        cov.report(coverage_modules, show_missing=1)
        cov.html_report(coverage_modules, directory='coverage_report')
        # Print code metrics footer
        print '----------------------------------------------------------------------'

    return test_results

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = django_static
# python
import os
import re
import sys
import stat
import shutil
import codecs
from collections import defaultdict
from cStringIO import StringIO
from subprocess import Popen, PIPE
import warnings

# django
from django import template
from django.conf import settings
from django.template import TemplateSyntaxError

register = template.Library()

try:
    import slimmer
except ImportError:
    slimmer = None

try:
    import cssmin
except ImportError:
    cssmin = None

try:
    import jsmin
except ImportError:
    jsmin = None

################################################################################
# The reason we're setting all of these into `settings` is so that in the code
# we can do things like `if settings.DJANGO_STATIC:` rather than the verbose
# and ugly `getattr(settings, 'DJANGO_STATIC')`.
# And the reason why these aren't set as constants variables is to make the code
# much easier to test because in the unit tests we can then do
# settings.DJANGO_STATIC_SAVE_PREFIX = '/tmp/test' and stuff like that.
settings.DJANGO_STATIC_USE_SYMLINK = getattr(settings, "DJANGO_STATIC_USE_SYMLINK", True)
settings.DJANGO_STATIC = getattr(settings, 'DJANGO_STATIC', False)
settings.DJANGO_STATIC_SAVE_PREFIX = getattr(settings, 'DJANGO_STATIC_SAVE_PREFIX', '')
settings.DJANGO_STATIC_NAME_PREFIX = getattr(settings, 'DJANGO_STATIC_NAME_PREFIX', '')
settings.DJANGO_STATIC_MEDIA_URL = \
  getattr(settings, "DJANGO_STATIC_MEDIA_URL", None)
settings.DJANGO_STATIC_MEDIA_URL_ALWAYS = \
  getattr(settings, "DJANGO_STATIC_MEDIA_URL_ALWAYS", False)

settings.DJANGO_STATIC_MEDIA_ROOTS = getattr(settings, "DJANGO_STATIC_MEDIA_ROOTS",
                               [settings.MEDIA_ROOT])

if sys.platform == "win32":
    _CAN_SYMLINK = False
else:
    _CAN_SYMLINK = settings.DJANGO_STATIC_USE_SYMLINK

# Wheree the mapping filename -> annotated_filename is kept
_FILE_MAP = {}

## These two methods are put here if someone wants to access the django_static
## functionality from code rather than from a django template
## E.g.
##   from django_static import slimfile
##   print slimfile('/css/foo.js')

def slimfile(filename):
    return _static_file(filename,
                        symlink_if_possible=_CAN_SYMLINK,
                        optimize_if_possible=True)

def staticfile(filename):
    return _static_file(filename,
                        symlink_if_possible=_CAN_SYMLINK,
                        optimize_if_possible=False)


def _load_file_proxy():
    # This is a function so that it can be unit tested more easily
    try:
        file_proxy_name = settings.DJANGO_STATIC_FILE_PROXY
        if not file_proxy_name:
            #warnings.warn("Empty DJANGO_STATIC_FILE_PROXY settings")
            raise AttributeError
        from django.utils.importlib import import_module
        _module_name, _function_name = file_proxy_name.rsplit('.', 1)
        file_proxy_module = import_module(_module_name)
        return getattr(file_proxy_module, _function_name)
    except AttributeError:
        def file_proxy_nothing(uri, *args, **kwargs):
            return uri
        return file_proxy_nothing
file_proxy = _load_file_proxy()

def _load_filename_generator():
    filename_generator = getattr(settings, 'DJANGO_STATIC_FILENAME_GENERATOR', None)
    if filename_generator:
        from django.utils.importlib import import_module
        _module_name, _function_name = filename_generator.rsplit('.', 1)
        file_generator_module = import_module(_module_name)
        return getattr(file_generator_module, _function_name)
    def default_filename_generator(apart, new_m_time):
        new_filename = ''.join([apart[0], '.%s' % new_m_time, apart[1]])
        return new_filename
    return default_filename_generator

_generate_filename = _load_filename_generator()

# this defines what keyword arguments you can always expect to get from in the
# file proxy function you've defined.
fp_default_kwargs = dict(new=False, changed=False, checked=False, notfound=False)


class SlimContentNode(template.Node):

    def __init__(self, nodelist, format=None):
        self.nodelist = nodelist
        self.format = format

    def render(self, context):
        code = self.nodelist.render(context)
        if slimmer is None:
            return code

        if self.format not in ('css','js','html','xhtml'):
            self.format = slimmer.guessSyntax(code)

        if self.format == 'css':
            return slimmer.css_slimmer(code)
        elif self.format in ('js', 'javascript'):
            return slimmer.js_slimmer(code)
        elif self.format == 'xhtml':
            return slimmer.xhtml_slimmer(code)
        elif self.format == 'html':
            return slimmer.html_slimmer(code)
        else:
            raise TemplateSyntaxError("Unrecognized format for slimming content")

        return code



@register.tag(name='slimcontent')
def do_slimcontent(parser, token):
    nodelist = parser.parse(('endslimcontent',))
    parser.delete_first_token()

    _split = token.split_contents()
    format = ''
    if len(_split) > 1:
        tag_name, format = _split
        if not (format[0] == format[-1] and format[0] in ('"', "'")):
            raise template.TemplateSyntaxError, \
                          "%r tag's argument should be in quotes" % tag_name

    return SlimContentNode(nodelist, format[1:-1])



@register.tag(name='slimfile')
def slimfile_node(parser, token):
    """For example:
         {% slimfile "/js/foo.js" %}
         or
         {% slimfile "/js/foo.js" as variable_name %}
    Or for multiples:
         {% slimfile "/foo.js; /bar.js" %}
         or
         {% slimfile "/foo.js; /bar.js" as variable_name %}
    """
    return staticfile_node(parser, token, optimize_if_possible=True)


@register.tag(name='staticfile')
def staticfile_node(parser, token, optimize_if_possible=False):
    """For example:
         {% staticfile "/js/foo.js" %}
         or
         {% staticfile "/js/foo.js" as variable_name %}
    Or for multiples:
         {% staticfile "/foo.js; /bar.js" %}
         or
         {% staticfile "/foo.js; /bar.js" as variable_name %}
    """
    args = token.split_contents()
    tag = args[0]

    if len(args) == 4 and args[-2] == 'as':
        context_name = args[-1]
        args = args[:-2]
    else:
        context_name = None

    filename = parser.compile_filter(args[1])

    return StaticFileNode(filename,
                          symlink_if_possible=_CAN_SYMLINK,
                          optimize_if_possible=optimize_if_possible,
                          context_name=context_name)


class StaticFileNode(template.Node):

    def __init__(self, filename_var,
                 optimize_if_possible=False,
                 symlink_if_possible=False,
                 context_name=None):
        self.filename_var = filename_var
        self.optimize_if_possible = optimize_if_possible
        self.symlink_if_possible = symlink_if_possible
        self.context_name = context_name

    def render(self, context):
        filename = self.filename_var.resolve(context)
        if not settings.DJANGO_STATIC:
            if settings.DJANGO_STATIC_MEDIA_URL_ALWAYS:
                return settings.DJANGO_STATIC_MEDIA_URL + filename
            return filename
        new_filename = _static_file([x.strip() for x in filename.split(';')],
                            optimize_if_possible=self.optimize_if_possible,
                            symlink_if_possible=self.symlink_if_possible)
        if self.context_name:
            context[self.context_name] = new_filename
            return ''
        return new_filename


@register.tag(name='slimall')
def do_slimallfiles(parser, token):
    nodelist = parser.parse(('endslimall',))
    parser.delete_first_token()

    return StaticFilesNode(nodelist,
                           symlink_if_possible=_CAN_SYMLINK,
                           optimize_if_possible=True)


@register.tag(name='staticall')
def do_staticallfiles(parser, token):
    nodelist = parser.parse(('endstaticall',))
    parser.delete_first_token()

    return StaticFilesNode(nodelist,
                           symlink_if_possible=_CAN_SYMLINK,
                           optimize_if_possible=False)




SCRIPTS_REGEX = re.compile('<script [^>]*src=["\']([^"\']+)["\'].*?</script>')
STYLES_REGEX = re.compile('<link.*?href=["\']([^"\']+)["\'].*?>', re.M|re.DOTALL)
IMG_REGEX = re.compile('<img.*?src=["\']((?!data:)[^"\']+)["\'].*?>', re.M|re.DOTALL)
ASYNC_DEFER_REGEX = re.compile('async|defer')

class StaticFilesNode(template.Node):
    """find all static files in the wrapped code and run staticfile (or
    slimfile) on them all by analyzing the code.
    """
    def __init__(self, nodelist, optimize_if_possible=False,
                 symlink_if_possible=False):
        self.nodelist = nodelist
        self.optimize_if_possible = optimize_if_possible

        self.symlink_if_possible = symlink_if_possible

    def render(self, context):
        """inspect the code and look for files that can be turned into combos.
        Basically, the developer could type this:
        {% slimall %}
          <link href="/one.css"/>
          <link href="/two.css"/>
        {% endslimall %}
        And it should be reconsidered like this:
          <link href="{% slimfile "/one.css;/two.css" %}"/>
        which we already have routines for doing.
        """
        code = self.nodelist.render(context)
        if not settings.DJANGO_STATIC:
            # Append MEDIA_URL if set
            # quick and dirty
            if settings.DJANGO_STATIC_MEDIA_URL_ALWAYS:
                for match in STYLES_REGEX.finditer(code):
                    for filename in match.groups():
                        code = (code.replace(filename,
                                             settings.DJANGO_STATIC_MEDIA_URL + filename))

                for match in SCRIPTS_REGEX.finditer(code):
                    for filename in match.groups():
                        code = (code.replace(filename,
                                             settings.DJANGO_STATIC_MEDIA_URL + filename))

                return code

            return code

        new_js_filenames = []
        for match in SCRIPTS_REGEX.finditer(code):
            whole_tag = match.group()
            async_defer = ASYNC_DEFER_REGEX.search(whole_tag)
            for filename in match.groups():

                optimize_if_possible = self.optimize_if_possible
                if optimize_if_possible and \
                  (filename.endswith('.min.js') or filename.endswith('.minified.js')):
                    # Override! Because we simply don't want to run slimmer
                    # on files that have the file extension .min.js
                    optimize_if_possible = False

                new_js_filenames.append(filename)
                code = code.replace(whole_tag, '')

        # Now, we need to combine these files into one
        if new_js_filenames:
            new_js_filename = _static_file(new_js_filenames,
                               optimize_if_possible=optimize_if_possible,
                               symlink_if_possible=self.symlink_if_possible)
        else:
            new_js_filename = None

        new_image_filenames = []
        def image_replacer(match):
            tag = match.group()
            for filename in match.groups():
                new_filename = _static_file(filename,
                                            symlink_if_possible=self.symlink_if_possible)
                if new_filename != filename:
                    tag = tag.replace(filename, new_filename)
            return tag

        code = IMG_REGEX.sub(image_replacer, code)

        new_css_filenames = defaultdict(list)

        # It's less trivial with CSS because we can't combine those that are
        # of different media
        media_regex = re.compile('media=["\']([^"\']+)["\']')
        for match in STYLES_REGEX.finditer(code):
            whole_tag = match.group()
            try:
                media_type = media_regex.findall(whole_tag)[0]
            except IndexError:
                media_type = ''

            for filename in match.groups():
                new_css_filenames[media_type].append(filename)
                code = code.replace(whole_tag, '')

        # Now, we need to combine these files into one
        new_css_filenames_combined = {}
        if new_css_filenames:
            for media_type, filenames in new_css_filenames.items():
                r = _static_file(filenames,
                                 optimize_if_possible=self.optimize_if_possible,
                                 symlink_if_possible=self.symlink_if_possible)
                new_css_filenames_combined[media_type] = r


        if new_js_filename:
            # Now is the time to apply the name prefix if there is one
            if async_defer:
                new_tag = ('<script %s src="%s"></script>' %
                        (async_defer.group(0), new_js_filename))
            else:
                new_tag = '<script src="%s"></script>' % new_js_filename
            code = "%s%s" % (new_tag, code)

        for media_type, new_css_filename in new_css_filenames_combined.items():
            extra_params = ''
            if media_type:
                extra_params += ' media="%s"' % media_type
            new_tag = '<link rel="stylesheet"%s href="%s"/>' % \
              (extra_params, new_css_filename)
            code = "%s%s" % (new_tag, code)

        return code

REFERRED_CSS_URLS_REGEX = re.compile('url\(((?!data:)[^\)]+)\)')
REFERRED_CSS_URLLESS_IMPORTS_REGEX = re.compile('@import\s+[\'"]([^\'"]+)[\'"]')

def _static_file(filename,
                 optimize_if_possible=False,
                 symlink_if_possible=False,
                 warn_no_file=True):
    """
    """
    if not settings.DJANGO_STATIC:
        return file_proxy(filename, disabled=True)

    def wrap_up(filename):
        if settings.DJANGO_STATIC_MEDIA_URL_ALWAYS:
            return settings.DJANGO_STATIC_MEDIA_URL + filename
        elif settings.DJANGO_STATIC_MEDIA_URL:
            return settings.DJANGO_STATIC_MEDIA_URL + filename
        return filename

    is_combined_files = isinstance(filename, list)
    if is_combined_files and len(filename) == 1:
        # e.g. passed a list of files but only one so treat it like a
        # single file
        filename = filename[0]
        is_combined_files = False

    if is_combined_files:
        map_key = ';'.join(filename)
    else:
        map_key = filename

    new_filename, m_time = _FILE_MAP.get(map_key, (None, None))

    # we might already have done a conversion but the question is
    # if the file has changed. This we only want
    # to bother with when in DEBUG mode because it adds one more
    # unnecessary operation.
    if new_filename:
        if settings.DEBUG:
            # need to check if the original has changed
            old_new_filename = new_filename
            new_filename = None
        else:
            # This is really fast and only happens when NOT in DEBUG mode
            # since it doesn't do any comparison
            return file_proxy(wrap_up(new_filename), **fp_default_kwargs)
    else:
        # This is important so that we can know that there wasn't an
        # old file which will help us know we don't need to delete
        # the old one
        old_new_filename = None


    if not new_filename:
        if is_combined_files:
            # It's a list! We have to combine it into one file
            new_file_content = StringIO()
            each_m_times = []
            extension = None
            for each in filename:
                filepath, path = _find_filepath_in_roots(each)
                if not filepath:
                    raise OSError("Failed to find %s in %s" % (each,
                        ",".join(settings.DJANGO_STATIC_MEDIA_ROOTS)))

                if extension:
                    if os.path.splitext(filepath)[1] != extension:
                        raise ValueError("Mismatching file extension in combo %r" % \
                          each)
                else:
                    extension = os.path.splitext(filepath)[1]
                each_m_times.append(os.stat(filepath)[stat.ST_MTIME])
                new_file_content.write(open(filepath, 'r').read().strip())
                new_file_content.write('\n')

            filename = _combine_filenames(filename)
            # Set the root path of the combined files to the first entry
            # in the MEDIA_ROOTS list. This way django-static behaves a
            # little more predictible.
            path = settings.DJANGO_STATIC_MEDIA_ROOTS[0]
            new_m_time = max(each_m_times)

        else:
            filepath, path = _find_filepath_in_roots(filename)
            if not filepath:
                if warn_no_file:
                    msg = "Can't find file %s in %s" % \
                      (filename, ",".join(settings.DJANGO_STATIC_MEDIA_ROOTS))
                    warnings.warn(msg)
                return file_proxy(wrap_up(filename),
                                  **dict(fp_default_kwargs,
                                         filepath=filepath,
                                         notfound=True))

            new_m_time = os.stat(filepath)[stat.ST_MTIME]

        if m_time:
            # we had the filename in the map
            if m_time != new_m_time:
                # ...but it has changed!
                m_time = None
            else:
                # ...and it hasn't changed!
                return file_proxy(wrap_up(old_new_filename))

        if not m_time:
            # We did not have the filename in the map OR it has changed
            apart = os.path.splitext(filename)
            new_filename = _generate_filename(apart, new_m_time)
            fileinfo = (settings.DJANGO_STATIC_NAME_PREFIX + new_filename,
                        new_m_time)

            _FILE_MAP[map_key] = fileinfo
            if old_new_filename:
                old_new_filename = old_new_filename.replace(
                                      settings.DJANGO_STATIC_NAME_PREFIX, '')
                old_new_filepath = _filename2filepath(old_new_filename,
                        settings.DJANGO_STATIC_SAVE_PREFIX or path)
                if not os.path.isdir(os.path.dirname(old_new_filepath)):
                    _mkdir(os.path.dirname(old_new_filepath))

                if os.path.isfile(old_new_filepath):
                    os.remove(old_new_filepath)
    new_filepath = _filename2filepath(new_filename,
            settings.DJANGO_STATIC_SAVE_PREFIX or path)

    if not os.path.isdir(os.path.dirname(new_filepath)):
        _mkdir(os.path.dirname(new_filepath))


    # Files are either slimmered or symlinked or just copied. Basically, only
    # .css and .js can be slimmered but not all are. For example, an already
    # minified say jquery.min.js doesn't need to be slimmered nor does it need
    # to be copied.
    # If you're on windows, it will always have to do a copy.
    # When symlinking, what the achievement is is that it gives the file a
    # unique and different name than the original.
    #
    # The caller of this method is responsible for dictacting if we're should
    # slimmer and if we can symlink.
    if optimize_if_possible:
        # Then we expect to be able to modify the content and we will
        # definitely need to write a new file.
        if is_combined_files:
            content = new_file_content.getvalue().decode('utf-8')
        else:
            #content = open(filepath).read()
            content = codecs.open(filepath, 'r', 'utf-8').read()
        if new_filename.endswith('.js') and has_optimizer(JS):
            content = optimize(content, JS)
        elif new_filename.endswith('.css') and has_optimizer(CSS):
            content = optimize(content, CSS)

            # and _static_file() all images refered in the CSS file itself
            def replacer(match):
                this_filename = match.groups()[0]

                if (this_filename.startswith('"') and this_filename.endswith('"')) or \
                  (this_filename.startswith("'") and this_filename.endswith("'")):
                    this_filename = this_filename[1:-1]
                # It's really quite common that the CSS file refers to the file
                # that doesn't exist because if you refer to an image in CSS for
                # a selector you never use you simply don't suffer.
                # That's why we say not to warn on nonexisting files

                replace_with = this_filename

                if not (this_filename.startswith('/') or \
                  (this_filename.startswith('http') and '://' in this_filename)):
                    # if the referenced filename is something like
                    # 'images/foo.jpg' or 'sub/module.css' then we need to copy the
                    # current relative directory
                    replace_with = this_filename
                    this_filename = os.path.join(os.path.dirname(filename), this_filename)
                optimize_again = optimize_if_possible and \
                                 this_filename.lower().endswith('.css') or False
                new_filename = _static_file(this_filename,
                                            symlink_if_possible=symlink_if_possible,
                                            optimize_if_possible=optimize_again,
                                            warn_no_file=settings.DEBUG and True or False)
                return match.group().replace(replace_with, new_filename)

            content = REFERRED_CSS_URLS_REGEX.sub(replacer, content)
            content = REFERRED_CSS_URLLESS_IMPORTS_REGEX.sub(replacer, content)

        elif slimmer or cssmin:
            raise ValueError(
              "Unable to slimmer file %s. Unrecognized extension" % new_filename)
        #print "** STORING:", new_filepath
        codecs.open(new_filepath, 'w', 'utf-8').write(content)
    elif symlink_if_possible and not is_combined_files:
        #print "** SYMLINK:", filepath, '-->', new_filepath

        # The reason we have to do this strange while loop is that it can
        # happen that in between the time it takes to destroy symlink till you
        # can create it, another thread or process might be trying to do the
        # exact same thing with just a fraction of a second difference, thus
        # making it possible to, at the time of creating the symlink, that it's
        # already there which will raise an OSError.
        #
        # This is quite possible when Django for example starts multiple fcgi
        # threads roughly all at the same time. An alternative approach would
        # be to store the global variable _FILE_MAP in a cache or something
        # which would effectively make it thread safe but that has the annoying
        # disadvantage that it remains in the cache between server restarts and
        # for a production environment, server restarts very often happen
        # because you have upgraded the code (and the static files). So, an
        # alternative is to use a cache so that thread number 2, number 3 etc
        # gets the file mappings of the first thread and then let this cache
        # only last for a brief amount of time. That amount of time would
        # basically be equivalent of the time the sys admin or developer would
        # have to wait between new code deployment and refreshed symlinks for
        # the static files. That feels convoluted and complex so I've decided
        # to instead use this rather obtuse while loop which is basically built
        # to try X number of times. If it still fails after X number of attempts
        # there's something else wrong with the IO which needs to bubble up.
        _max_attempts = 10
        while True:
            try:
                if os.path.lexists(new_filepath):
                    # since in the other cases we write a new file, it doesn't matter
                    # that the file existed before.
                    # That's not the case with symlinks
                    os.unlink(new_filepath)

                os.symlink(filepath, new_filepath)
                break
            except OSError:
                _max_attempts -= 1
                if _max_attempts <= 0:
                    raise
    elif is_combined_files:
        #print "** STORING COMBO:", new_filepath
        open(new_filepath, 'w').write(new_file_content.getvalue())
    else:
        # straight copy
        #print "** STORING COPY:", new_filepath
        shutil.copyfile(filepath, new_filepath)

    return file_proxy(wrap_up(settings.DJANGO_STATIC_NAME_PREFIX + new_filename),
                      **dict(fp_default_kwargs, new=True,
                             filepath=new_filepath, checked=True))


def _mkdir(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired " \
                      "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            _mkdir(head)
        if tail:
            os.mkdir(newdir)


def _find_filepath_in_roots(filename):
    """Look for filename in all MEDIA_ROOTS, and return the first one found."""
    for root in settings.DJANGO_STATIC_MEDIA_ROOTS:
        filepath = _filename2filepath(filename, root)
        if os.path.isfile(filepath):
            return filepath, root
    # havent found it in DJANGO_STATIC_MEDIA_ROOTS look for apps' files if we're
    #  in DEBUG mode
    if settings.DEBUG:
        try:
            from django.contrib.staticfiles import finders
            absolute_path = finders.find(filename)
            if absolute_path:
                root, filepath = os.path.split(absolute_path)
                return absolute_path, root
        except ImportError:
            pass
    return None, None

def _filename2filepath(filename, media_root):
    # The reason we're doing this is because the templates will
    # look something like this:
    # src="{{ MEDIA_URL }}/css/foo.css"
    # and if (and often happens in dev mode) MEDIA_URL will
    # just be ''

    if filename.startswith('/'):
        path = os.path.join(media_root, filename[1:])
    else:
        path = os.path.join(media_root, filename)

    return path



def _combine_filenames(filenames, max_length=40):
    """Return a new filename to use as the combined file name for a
    bunch files.
    A precondition is that they all have the same file extension

    Given that the list of files can have different paths, we aim to use the
    most common path.

    Example:
      /somewhere/else/foo.js
      /somewhere/bar.js
      /somewhere/different/too/foobar.js
    The result will be
      /somewhere/foo_bar_foobar.js

    Another thing to note, if the filenames have timestamps in them, combine
    them all and use the highest timestamp.

    """
    path = None
    names = []
    extension = None
    timestamps = []
    for filename in filenames:
        name = os.path.basename(filename)
        if not extension:
            extension = os.path.splitext(name)[1]
        elif os.path.splitext(name)[1] != extension:
            raise ValueError("Can't combine multiple file extensions")

        for each in re.finditer('\.\d{10}\.', name):
            timestamps.append(int(each.group().replace('.','')))
            name = name.replace(each.group(), '.')
        name = os.path.splitext(name)[0]
        names.append(name)

        if path is None:
            path = os.path.dirname(filename)
        else:
            if len(os.path.dirname(filename)) < len(path):
                path = os.path.dirname(filename)


    new_filename = '_'.join(names)
    if timestamps:
        new_filename += ".%s" % max(timestamps)

    new_filename = new_filename[:max_length]
    new_filename += extension

    return os.path.join(path, new_filename)


CSS = 'css'
JS = 'js'

def has_optimizer(type_):
    if type_ == CSS:
        if getattr(settings, 'DJANGO_STATIC_YUI_COMPRESSOR', None):
            return True
        return slimmer is not None or cssmin is not None
    elif type_ == JS:
        if getattr(settings, 'DJANGO_STATIC_CLOSURE_COMPILER', None):
            return True
        if getattr(settings, 'DJANGO_STATIC_YUI_COMPRESSOR', None):
            return True
        if getattr(settings, 'DJANGO_STATIC_JSMIN', None):
            assert jsmin is not None, "jsmin not installed"
            return True
        return slimmer is not None or cssmin is not None
    else:
        raise ValueError("Invalid type %r" % type_)

def optimize(content, type_):
    if type_ == CSS:
        if cssmin is not None:
            return _run_cssmin(content)
        elif getattr(settings, 'DJANGO_STATIC_YUI_COMPRESSOR', None):
            return _run_yui_compressor(content, type_)
        return slimmer.css_slimmer(content)
    elif type_ == JS:
        if getattr(settings, 'DJANGO_STATIC_CLOSURE_COMPILER', None):
            return _run_closure_compiler(content)
        if getattr(settings, 'DJANGO_STATIC_YUI_COMPRESSOR', None):
            return _run_yui_compressor(content, type_)
        if getattr(settings, 'DJANGO_STATIC_JSMIN', None):
            return _run_jsmin(content)
        return slimmer.js_slimmer(content)
    else:
        raise ValueError("Invalid type %r" % type_)

CLOSURE_COMMAND_TEMPLATE = "java -jar %(jarfile)s"
def _run_closure_compiler(jscode):
    cmd = CLOSURE_COMMAND_TEMPLATE % {'jarfile': settings.DJANGO_STATIC_CLOSURE_COMPILER}
    proc = Popen(cmd, shell=True, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    try:
        (stdoutdata, stderrdata) = proc.communicate(jscode)
    except OSError, msg: # pragma: no cover
        # see comment on OSErrors inside _run_yui_compressor()
        stderrdata = \
          "OSError: %s. Try again by making a small change and reload" % msg
    if stderrdata:
        return "/* ERRORS WHEN RUNNING CLOSURE COMPILER\n" + stderrdata + '\n*/\n' + jscode

    return stdoutdata

YUI_COMMAND_TEMPLATE = "java -jar %(jarfile)s --type=%(type)s"
def _run_yui_compressor(code, type_):
    cmd = YUI_COMMAND_TEMPLATE % \
      {'jarfile': settings.DJANGO_STATIC_YUI_COMPRESSOR,
       'type': type_}
    proc = Popen(cmd, shell=True, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    try:
        (stdoutdata, stderrdata) = proc.communicate(code)
    except OSError, msg: # pragma: no cover
        # Sometimes, for unexplicable reasons, you get a Broken pipe when
        # running the popen instance. It's always non-deterministic problem
        # so it probably has something to do with concurrency or something
        # really low level.
        stderrdata = \
          "OSError: %s. Try again by making a small change and reload" % msg

    if stderrdata:
        return "/* ERRORS WHEN RUNNING YUI COMPRESSOR\n" + stderrdata + '\n*/\n' + code

    return stdoutdata


def _run_cssmin(code):
    output = cssmin.cssmin(code)
    return output

def _run_jsmin(code):
    output = jsmin.jsmin(code)
    return output

########NEW FILE########
__FILENAME__ = tests
# -*- coding: UTF-8 -*-

import codecs
import re
import os
import stat
import sys
import time
from tempfile import mkdtemp, gettempdir
from unittest import TestCase
from shutil import rmtree
import warnings

import django_static.templatetags.django_static as _django_static
from django_static.templatetags.django_static import _static_file, _combine_filenames

def _slim_file(x, symlink_if_possible=False,):
    return _django_static._static_file(x, optimize_if_possible=True,
                        symlink_if_possible=symlink_if_possible)

try:
    import slimmer
except ImportError:
    slimmer = None

try:
    import cssmin
except ImportError:
    cssmin = None

if cssmin is None and slimmer is None:
    import warnings
    warnings.warn("Can't run tests that depend on slimmer/cssmin")


from django.conf import settings
from django.template import Template
from django.template import Context
import django.template

## Monkey patch the {% load ... %} tag to always reload our code
## so it can pick up any changes to "settings.py" that happens during
## unit tests
#_original_get_library = django.template.get_library
#def get_library_wrapper(library_name):
#    if library_name == "django_static":
#        reload(sys.modules['django_static.templatetags.django_static'])
#    return _original_get_library(library_name)
#django.template.get_library = get_library_wrapper
#reload(sys.modules['django.template.defaulttags'])

_GIF_CONTENT = 'R0lGODlhBgAJAJEDAGmaywBUpv///////yH5BAEAAAMALAAAAAAGAAkAAAIRnBFwITEoGoyBRWnb\ns27rBRQAOw==\n'
_GIF_CONTENT_DIFFERENT = 'R0lGODlhBAABAJEAANHV3ufr7qy9xGyiyCH5BAAAAAAALAAAAAAEAAEAAAIDnBAFADs=\n'

#TEST_MEDIA_ROOT = os.path.join(gettempdir(), 'fake_media_root')
#_original_MEDIA_ROOT = settings.MEDIA_ROOT
#_MISSING = id(get_library_wrapper) # get semi-random mark
_marker = object()
_saved_settings = []
for name in [ "DEBUG",
              "DJANGO_STATIC",
              "DJANGO_STATIC_SAVE_PREFIX",
              "DJANGO_STATIC_NAME_PREFIX",
              "DJANGO_STATIC_MEDIA_URL",
              "DJANGO_STATIC_MEDIA_URL_ALWAYS",
              "DJANGO_STATIC_FILE_PROXY",
              "DJANGO_STATIC_USE_SYMLINK",
              "DJANGO_STATIC_CLOSURE_COMPILER",
              "DJANGO_STATIC_MEDIA_ROOTS",
              "DJANGO_STATIC_YUI_COMPRESSOR"]:
    _saved_settings.append((name, getattr(settings, name, _marker)))

class TestDjangoStatic(TestCase):

    # NOTE! The reason we keep chaning names in the tests is because of the
    # global object _FILE_MAP in django_static.py (which is questionable)


    def _notice_file(self, filepath):
        assert os.path.isfile(filepath)
        self.__added_filepaths.append(filepath)

    def setUp(self):
        _django_static._FILE_MAP = {}
        self.__added_dirs = []
        self.__added_filepaths = []
        #if not os.path.isdir(TEST_MEDIA_ROOT):
        #    os.mkdir(TEST_MEDIA_ROOT)

        # All tests is going to run off this temp directory
        settings.MEDIA_ROOT = self._mkdir()

        # Set all django-static settings to known values so it isn't
        # dependant on the real values in settings.py
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = ""
        settings.DJANGO_STATIC_NAME_PREFIX = ""
        settings.DJANGO_STATIC_MEDIA_URL = ""
        settings.DJANGO_STATIC_MEDIA_URL_ALWAYS = False
        settings.DJANGO_STATIC_USE_SYMLINK = True
        settings.DJANGO_STATIC_FILE_PROXY = None
        settings.DJANGO_STATIC_CLOSURE_COMPILER = None
        settings.DJANGO_STATIC_YUI_COMPRESSOR = None
        #if hasattr(settings, "DJANGO_STATIC_MEDIA_ROOTS"):
        #    del settings.DJANGO_STATIC_MEDIA_ROOTS
        settings.DJANGO_STATIC_MEDIA_ROOTS = [settings.MEDIA_ROOT]

        super(TestDjangoStatic, self).setUp()

    def _mkdir(self):
        dir = mkdtemp()
        self.__added_dirs.append(dir)
        return dir

    def tearDown(self):
        for filepath in self.__added_filepaths:
            if os.path.isfile(filepath):
                os.remove(filepath)

        # restore things for other potential tests
        for name, value in _saved_settings:
            if value == _marker and hasattr(settings, name):
                delattr(settings, name)
            else:
                setattr(settings, name, value)

        for dir in self.__added_dirs:
            if dir.startswith(gettempdir()):
                rmtree(dir)

        super(TestDjangoStatic, self).tearDown()




    def test__combine_filenames(self):
        """test the private function _combine_filenames()"""

        filenames = ['/somewhere/else/foo.js',
                     '/somewhere/bar.js',
                     '/somewhere/different/too/foobar.js']
        expect = '/somewhere/foo_bar_foobar.js'

        self.assertEqual(_django_static._combine_filenames(filenames), expect)

        filenames = ['/foo.1243892792.js',
                     '/bar.1243893111.js',
                     '/foobar.js']
        expect = '/foo_bar_foobar.1243893111.js'
        self.assertEqual(_django_static._combine_filenames(filenames), expect)


    def test__combine_long_filenames(self):
        """test the private function _combine_filenames()"""

        filenames = ['/jquery_something_%s.js' % x
                     for x in range(10)]
        expect = '/jquery_something_0_jquery_something_1_jq.js'

        self.assertEqual(_django_static._combine_filenames(filenames), expect)


    def test_staticfile_django_static_off(self):
        """You put this in the template:
         {% staticfile "/js/foo.js" %}
        but then you disable DJANGO_STATIC so you should get
          /js/foo.js
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = False

        filename = "/foo.js"
        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write('samplecode()\n')

        media_root_files_before = os.listdir(settings.MEDIA_ROOT)
        template_as_string = """{% load django_static %}
        {% staticfile "/foo.js" %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertEqual(rendered, u"/foo.js")


    def test_staticall_django_static_off(self):
        """You put this in the template:
         {% staticall %}
         <script src="/js/foo.js"></script>
         {% endstaticall %}
        but then you disable DJANGO_STATIC so you should get
          /js/foo.js
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = False

        filename = "/foo.js"
        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write('samplecode()\n')

        media_root_files_before = os.listdir(settings.MEDIA_ROOT)
        template_as_string = """{% load django_static %}
        {% staticall %}
        <script src="/foo.js"></script>
        {% endstaticall %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertEqual(rendered, u'<script src="/foo.js"></script>')

    def test_staticall_with_already_minified_files(self):
        """You put this in the template:
         {% staticall %}
         <script src="/js/foo.js"></script>
         {% endstaticall %}
        but then you disable DJANGO_STATIC so you should get
          /js/foo.js
        """
        if slimmer is None and cssmin is None:
            return

        settings.DEBUG = False
        settings.DJANGO_STATIC = True

        filename = "/foo.js"
        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write("""
        function (var) { return var++; }
        """)

        filename = "/jquery.min.js"
        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write("""
        function jQuery() { return ; }
        """)

        media_root_files_before = os.listdir(settings.MEDIA_ROOT)
        template_as_string = """{% load django_static %}
        {% slimall %}
        <script src="/foo.js"></script>
        <script src="/jquery.min.js"></script>
        {% endslimall %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        regex = re.compile('/foo_jquery\.min\.\d+\.js')
        self.assertTrue(regex.findall(rendered))
        self.assertEqual(rendered.count('<script'), 1)
        self.assertEqual(rendered.count('</script>'), 1)
        new_filename = regex.findall(rendered)[0]

        # check that the parts of the content was slimmed
        self.assertTrue(os.path.basename(new_filename) in \
         os.listdir(settings.MEDIA_ROOT))

    def test_staticall_with_image_tags(self):
        """test when there are image tags in a block of staticall like this:

        {% staticall %}
        <img src="one.png">
        <img src="two.png">
        {% endstaticall %}

        And you should expect something like this:

        <img src="one.1275325988.png">
        <img src="two.1275325247.png">

        """

        open(settings.MEDIA_ROOT + '/img100.gif', 'w').write(_GIF_CONTENT)
        open(settings.MEDIA_ROOT + '/img200.gif', 'w').write(_GIF_CONTENT)

        template_as_string = """{% load django_static %}
        {% staticall %}
        <img src="img100.gif">
        <img src="img200.gif">
        {% endstaticall %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertTrue(re.findall('img100\.\d+\.gif', rendered))
        self.assertTrue(re.findall('img200\.\d+\.gif', rendered))

    def _assertProcessedFileExists(self, dir, org_name):
        head, tail = os.path.splitext(org_name)
        filename_re = re.compile(r"^%s\.\d+\%s$" % (head, tail))
        files = os.listdir(dir)
        match = [ f for f in files if filename_re.match(f) ]
        self.assertEqual(len(match), 1)

    def test_static_in_multiple_media_roots(self):
        """Test that static files in multiple media roots works.

        {% staticall %}
        <img src="one.png">
        <img src="two.png">
        {% endstaticall %}

        The source files are stored in different MEDIA_ROOTs.
        First, run without DJANGO_STATIC_SAVE_PREFIX set and verify
        that the files are stored in the source directories.
        Then, set DJANGO_STATIC_SAVE_PREFIX and verify that the
        processed files are stored there.
        """

        dir1 = settings.MEDIA_ROOT
        dir2 = self._mkdir()
        settings.DJANGO_STATIC_MEDIA_ROOTS = [ dir1, dir2 ]
        dir3 = self._mkdir()

        open(dir1 + '/img100.gif', 'w').write(_GIF_CONTENT)
        open(dir2 + '/img200.gif', 'w').write(_GIF_CONTENT)

        template_as_string = """{% load django_static %}
        {% staticall %}
        <img src="img100.gif">
        <img src="img200.gif">
        {% endstaticall %}
        """
        template = Template(template_as_string)
        context = Context()
        template.render(context).strip()
        self._assertProcessedFileExists(dir1, "img100.gif")
        self._assertProcessedFileExists(dir2, "img200.gif")


    def test_static_in_multiple_media_roots_with_save_prefix(self):
        """same as test_static_in_multiple_media_roots() but with a save
        prefix. """

        dir1 = settings.MEDIA_ROOT
        dir2 = self._mkdir()
        settings.DJANGO_STATIC_MEDIA_ROOTS = [ dir1, dir2 ]
        dir3 = self._mkdir()
        settings.DJANGO_STATIC_SAVE_PREFIX = dir3

        open(dir1 + '/img100.gif', 'w').write(_GIF_CONTENT)
        open(dir2 + '/img200.gif', 'w').write(_GIF_CONTENT)

        template_as_string = """{% load django_static %}
        {% staticall %}
        <img src="img100.gif">
        <img src="img200.gif">
        {% endstaticall %}
        """
        template = Template(template_as_string)
        context = Context()
        template.render(context).strip()
        self._assertProcessedFileExists(dir3, "img100.gif")
        self._assertProcessedFileExists(dir3, "img200.gif")


    def test_combined_files_in_multiple_media_roots(self):
        """Test that static files in multiple media roots works.

        {% staticall %}
        <img src="one.png">
        <img src="two.png">
        {% endstaticall %}

        The source files are stored in different MEDIA_ROOTs.
        First, run without DJANGO_STATIC_SAVE_PREFIX set and verify
        that the files are stored in the source directories.
        Then, set DJANGO_STATIC_SAVE_PREFIX and verify that the
        processed files are stored there.
        """
        dir1 = settings.MEDIA_ROOT
        dir2 = self._mkdir()
        settings.DJANGO_STATIC_MEDIA_ROOTS = [dir1, dir2]

        open(dir1 + '/test_A.js', 'w').write("var A=1;")
        open(dir2 + '/test_B.js', 'w').write("var B=1;")

        template_as_string = """{% load django_static %}
        {% slimfile "/test_A.js;/test_B.js" %}
        """
        template = Template(template_as_string)
        context = Context()
        template.render(context).strip()
        # The result will always be saved in the first dir in
        # MEDIA_ROOTS unless DJANGO_STATIC_SAVE_PREFIX is set
        self._assertProcessedFileExists(dir1, "test_A_test_B.js")

    def test_combined_files_in_multiple_media_roots_with_save_prefix(self):
        """copy of test_combined_files_in_multiple_media_roots() but this time
        with a save prefix"""
        dir1 = settings.MEDIA_ROOT
        dir2 = self._mkdir()
        settings.DJANGO_STATIC_MEDIA_ROOTS = [dir1, dir2]

        open(dir1 + '/test_A.js', 'w').write("var A=1;")
        open(dir2 + '/test_B.js', 'w').write("var B=1;")

        template_as_string = """{% load django_static %}
        {% slimfile "/test_A.js;/test_B.js" %}
        """
        dir3 = self._mkdir()
        settings.DJANGO_STATIC_SAVE_PREFIX = dir3

        template = Template(template_as_string)
        context = Context()
        template.render(context).strip()
        self._assertProcessedFileExists(dir3, "test_A_test_B.js")


    def test_staticfile_single_debug_on(self):
        """Most basic test
        {% staticfile "/js/jquery-1.9.9.min.js" %}
        it should become
        /js/jquery-1.9.9.min.1257xxxxxx.js
        and unlike slimfile() this file should either be a symlink or
        a copy that hasn't changed.
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True

        self._test_staticfile_single('/jquery.min.js',
                                     'function () { return 1; }')


    def test_staticfile_single_debug_off(self):
        """Most basic test
        {% staticfile "/js/jquery-1.9.9.min.js" %}
        it should become
        /js/jquery-1.9.9.min.1257xxxxxx.js
        and unlike slimfile() this file should either be a symlink or
        a copy that hasn't changed.
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True

        self._test_staticfile_single('/jquery-2.min.js',
                                     'function () { return 1; }')

    def test_staticfile_single_debug_off_with_media_url(self):
        """Most basic test
        {% staticfile "/js/jquery-1.9.9.min.js" %}
        it should become
        http://static.example.com/js/jquery-1.9.9.min.1257xxxxxx.js
        and unlike slimfile() this file should either be a symlink or
        a copy that hasn't changed.
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_MEDIA_URL = media_url = 'http://static.example.com'
        settings.DJANGO_STATIC_NAME_PREFIX = '/infinity'
        settings.DJANGO_STATIC_SAVE_PREFIX = os.path.join(settings.MEDIA_ROOT, 'special')

        self._test_staticfile_single('/jquery-3.min.js',
                                     'function () { return 1; }',
                                     media_url=media_url,
                                     name_prefix='/infinity',
                                     save_prefix='special')

    def test_staticfile_single_debug_off_with_name_and_save_prefix_with_media_url(self):
        """Most basic test
        {% staticfile "/js/jquery-1.9.9.min.js" %}
        it should become
        http://static.example.com/js/jquery-1.9.9.min.1257xxxxxx.js
        and unlike slimfile() this file should either be a symlink or
        a copy that hasn't changed.
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_MEDIA_URL = media_url = 'http://static.example.com'

        self._test_staticfile_single('/jquery-4.min.js',
                                     'function () { return 1; }',
                                     media_url=media_url)

    def assertFilenamesAlmostEqual(self, name1, name2):
        # Occasionally we get a failure because the clock ticked to
        # the next second after the file was rendered.
        # Thanks https://github.com/slinkp for this contribution!

        name1, name2 = name1.strip(), name2.strip()
        timestamp_re = re.compile(r'[^\.]\.([0-9]+)\..*')
        t1 = int(timestamp_re.search(name1).group(1))
        t2 = int(timestamp_re.search(name2).group(1))
        self.assert_(t1 - t2 in (-1, 0, 1),
                     "Filenames %r and %r timestamps differ by more than 1" % (name1, name2))


    def _test_staticfile_single(self, filename, code, name_prefix='', save_prefix='',
                               media_url=''):

        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write(code + '\n')

        media_root_files_before = os.listdir(settings.MEDIA_ROOT)

        template_as_string = '{% load django_static %}\n'
        template_as_string += '{% staticfile "' + filename + '" %}'
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        bits = filename.rsplit('.', 1)
        now = int(time.time())
        new_filename = bits[0] + '.%s.' % now + bits[-1]
        self.assertFilenamesAlmostEqual(rendered, media_url + name_prefix + new_filename)

        if save_prefix:
            save_dir = os.path.join(os.path.join(settings.MEDIA_ROOT, save_prefix))
            if os.path.basename(new_filename) not in os.listdir(save_dir):
                # most likely because the clock ticked whilst running the test
                ts = re.findall('\d{2,10}', new_filename)[0]
                previous_second = int(ts) - 1
                other_new_filename = new_filename.replace(ts, str(previous_second))
                self.assertTrue(os.path.basename(other_new_filename) in os.listdir(save_dir))
            else:
                self.assertTrue(os.path.basename(new_filename) in os.listdir(save_dir))
            # The content of the new file should be the same
            new_file = os.listdir(save_dir)[0]
            new_file_path = os.path.join(save_dir, new_file)
            if sys.platform != "win32":
                self.assertTrue(os.path.islink(new_file_path))
            new_code = open(new_file_path).read()
            self.assertTrue(len(new_code.strip()) == len(code.strip()))
        else:
            media_root_files_after = os.listdir(settings.MEDIA_ROOT)
            # assuming the file isn't in a sub directory
            if len(new_filename.split('/')) <= 2:
                self.assertEqual(len(media_root_files_before) + 1,
                                 len(media_root_files_after))

            # Content shouldn't change
            new_file = [x for x in media_root_files_after
                        if x not in media_root_files_before][0]
            new_file_path = os.path.join(settings.MEDIA_ROOT, new_file)
            if sys.platform != "win32":
                self.assertTrue(os.path.islink(new_file_path))
            new_code = open(new_file_path).read()
            self.assertEqual(len(new_code.strip()), len(code.strip()))

        # Run it again just to check that it still works
        rendered = template.render(context).strip()
        self.assertFilenamesAlmostEqual(rendered, media_url + name_prefix + new_filename)

        # pretend that time has passed and 10 seconds has lapsed then re-run the
        # rendering again and depending on settings.DEBUG this is noticed
        # or not.

        from posix import stat_result
        def fake_stat(arg):
            if arg == test_filepath:
                faked = list(orig_os_stat(arg))
                faked[stat.ST_MTIME] = faked[stat.ST_MTIME] + 10
                return stat_result(faked)
            else:
                return orig_os_stat(arg)
        orig_os_stat = os.stat
        os.stat = fake_stat

        rendered = template.render(context).strip()
        if settings.DEBUG:
            new_filename = bits[0] + '.%s.' % (now + 10) + bits[1]
        self.assertFilenamesAlmostEqual(rendered, media_url + name_prefix + new_filename)

        if settings.DEBUG:

            # when time passes and a new file is created, it's important to test
            # that the previously created one is deleted
            if save_prefix:
                # If you use a save prefix, presumbly the directory where the
                # timestamped files are saved didn't exist before so we can
                # assume that the file existed before where none
                files_now = os.listdir(os.path.join(settings.MEDIA_ROOT, save_prefix))
                self.assertEqual(len(files_now), 1)
            else:
                self.assertEqual(len(media_root_files_before) + 1,
                                len(os.listdir(settings.MEDIA_ROOT)))
                self.assertNotEqual(sorted(media_root_files_after),
                                    sorted(os.listdir(settings.MEDIA_ROOT)))



    def test_slimfile_single_debug_on(self):
        """Most basic test
        {% slimfile "/js/foo.js" %}
        it should become:
        /js/foo.1257xxxxxxx.js
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True

        self._test_slimfile_single('/test.js',
                                   'function () { return 1; }')

    def test_slimfile_single_debug_off(self):
        """Most basic test
        {% slimfile "/js/foo.js" %}
        it should become:
        /js/foo.1257xxxxxxx.js
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True

        self._test_slimfile_single('/testing.js',
                                   'var a = function() { return ; }')

    def test_slimfile_single_debug_off_with_name_prefix(self):
        """Most basic test
        {% slimfile "/js/foo.js" %}
        it should become:
        /myprefix/js/foo.1257xxxxxxx.js
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_NAME_PREFIX = '/infinity'

        self._test_slimfile_single('/testing123.js',
                                   'var a = function() { return ; }',
                                   name_prefix='/infinity')

    def test_slimfile_single_debug_on_with_name_prefix(self):
        """Most basic test
        {% slimfile "/js/foo.js" %}
        it should become:
        /myprefix/js/foo.1257xxxxxxx.js
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_NAME_PREFIX = '/infinity'

        self._test_slimfile_single('/testing321.js',
                                   'var a = function() { return ; }',
                                   name_prefix='/infinity')


    def test_slimfile_single_debug_off_with_save_prefix(self):
        """Most basic test
        {% slimfile "/js/foo.js" %}
        it should become:
        /myprefix/js/foo.1257xxxxxxx.js
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = os.path.join(settings.MEDIA_ROOT, 'special')

        self._test_slimfile_single('/testingXXX.js',
                                   'var a = function() { return ; }',
                                   save_prefix='special')

    def test_slimfile_single_debug_on_with_save_prefix(self):
        """Most basic test
        {% slimfile "/js/foo.js" %}
        it should become:
        /myprefix/js/foo.1257xxxxxxx.js
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = os.path.join(settings.MEDIA_ROOT, 'special')

        self._test_slimfile_single('/testingAAA.js',
                                   'var a = function() { return ; }',
                                   save_prefix='special')


    def _test_slimfile_single(self, filename, code, name_prefix='', save_prefix=''):
        if slimmer is None and cssmin is None:
            return

        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write(code + '\n')


        media_root_files_before = os.listdir(settings.MEDIA_ROOT)

        template_as_string = '{% load django_static %}\n'
        template_as_string += '{% slimfile "' + filename + '" %}'
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        bits = filename.split('.')
        now = int(time.time())
        new_filename = bits[0] + '.%s.' % now + bits[1]
        self.assertFilenamesAlmostEqual(rendered, name_prefix + new_filename)

        if save_prefix:
            save_dir = os.path.join(os.path.join(settings.MEDIA_ROOT, save_prefix))
            if os.path.basename(new_filename) not in os.listdir(save_dir):
                # Because the clock has ticked in the time this test was running
                # have to manually check some things.
                # This might be what you have on your hands:
                #  new_filename
                #  /testingXXX.1291842804.js
                #  os.path.basename(new_filename)
                #  testingXXX.1291842804.js
                #  os.listdir(save_dir)
                #  ['testingXXX.1291842803.js']
                ts = re.findall('\d{2,10}', new_filename)[0]
                previous_second = int(ts) - 1
                other_new_filename = new_filename.replace(ts, str(previous_second))
                self.assertTrue(os.path.basename(other_new_filename) in os.listdir(save_dir))

            else:
                self.assertTrue(os.path.basename(new_filename) in os.listdir(save_dir))
            # The content of the new file should be smaller

            new_file = os.path.join(save_dir, os.listdir(save_dir)[0])
            new_code = open(new_file).read()
            self.assertTrue(len(new_code.strip()) < len(code.strip()))
        else:
            media_root_files_after = os.listdir(settings.MEDIA_ROOT)
            # assuming the file isn't in a sub directory
            if len(new_filename.split('/')) <= 2:
                self.assertEqual(len(media_root_files_before) + 1,
                                 len(media_root_files_after))

            # The content of the newly saved file should have been whitespace
            # optimized so we can expect it to contain less bytes
            new_file = [x for x in media_root_files_after
                        if x not in media_root_files_before][0]
            new_code = open(os.path.join(settings.MEDIA_ROOT, new_file)).read()
            self.assertTrue(len(new_code) < len(code))

        # Run it again just to check that it still works
        rendered = template.render(context).strip()
        self.assertFilenamesAlmostEqual(rendered, name_prefix + new_filename)

        # pretend that time has passed and 10 seconds has lapsed then re-run the
        # rendering again and depending on settings.DEBUG this is noticed
        # or not.

        #time.sleep(1)
        from posix import stat_result
        def fake_stat(arg):
            if arg == test_filepath:
                faked = list(orig_os_stat(arg))
                faked[stat.ST_MTIME] = faked[stat.ST_MTIME] + 10
                return stat_result(faked)
            else:
                return orig_os_stat(arg)
        orig_os_stat = os.stat
        os.stat = fake_stat

        rendered = template.render(context).strip()
        if settings.DEBUG:
            new_filename = bits[0] + '.%s.' % (now + 10) + bits[1]
        self.assertFilenamesAlmostEqual(rendered, name_prefix + new_filename)

        if settings.DEBUG:

            # when time passes and a new file is created, it's important to test
            # that the previously created one is deleted
            if save_prefix:
                # If you use a save prefix, presumbly the directory where the
                # timestamped files are saved didn't exist before so we can
                # assume that the file existed before where none
                files_now = os.listdir(os.path.join(settings.MEDIA_ROOT, save_prefix))
                self.assertEqual(len(files_now), 1)
            else:
                self.assertEqual(len(media_root_files_before) + 1,
                                len(os.listdir(settings.MEDIA_ROOT)))
                self.assertNotEqual(sorted(media_root_files_after),
                                    sorted(os.listdir(settings.MEDIA_ROOT)))

    def test_slimfile_multiple_debug_on(self):
        """Where there are multiple files instead if just one:
        {% slimfile "/js/foo.js; /js/bar.js" %}
        it should become:
        /js/foo_bar.1257xxxxx.js
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        #settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        #settings.DJANGO_STATIC_NAME_PREFIX = ''

        filenames = ('/test_1.js', '/test_2.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_slimfile_multiple(filenames, codes)

    def test_slimfile_multiple_debug_off(self):
        """This is effectively the same as test_slimfile_multiple_debug_on()
        with the exception that this time with DEBUG=False which basically
        means that it assumes that the filename doesn't change if the
        filename is mapped at all.
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True
        #settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        #settings.DJANGO_STATIC_NAME_PREFIX = ''

        filenames = ('/test_A.js', '/test_B.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_slimfile_multiple(filenames, codes)

    def test_slimfile_multiple_debug_on_with_name_prefix(self):
        """same as test_slimfile_multiple_debug_on() but this time with a
        name prefix.
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        #settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        settings.DJANGO_STATIC_NAME_PREFIX = '/infinity'

        filenames = ('/test_X.js', '/test_Y.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_slimfile_multiple(filenames, codes, name_prefix='/infinity')

    def test_slimfile_multiple_debug_off_with_name_prefix(self):
        """same as test_slimfile_multiple_debug_on() but this time with a
        name prefix.
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True
        #settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        settings.DJANGO_STATIC_NAME_PREFIX = '/infinity'

        filenames = ('/test_P.js', '/test_Q.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_slimfile_multiple(filenames, codes, name_prefix='/infinity')

    def test_slimfile_multiple_debug_on_with_save_prefix(self):
        """same as test_slimfile_multiple_debug_on() but this time with a
        name prefix.
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = os.path.join(settings.MEDIA_ROOT, 'forever')

        filenames = ('/test_a.js', '/test_b.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_slimfile_multiple(filenames, codes, save_prefix='forever')

    def test_slimfile_multiple_debug_on_with_name_and_save_prefix(self):
        """same as test_slimfile_multiple_debug_on() but this time with a
        name prefix.
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = os.path.join(settings.MEDIA_ROOT, 'forever')
        settings.DJANGO_STATIC_NAME_PREFIX = '/infinity'

        filenames = ('/test_111.js', '/test_222.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_slimfile_multiple(filenames, codes,
                                     name_prefix='/infinity',
                                     save_prefix='forever')


    def _test_slimfile_multiple(self, filenames, codes, name_prefix='', save_prefix=None):

        test_filepaths = []
        for i, filename in enumerate(filenames):
            test_filepath = settings.MEDIA_ROOT + filename
            test_filepaths.append(test_filepath)
            open(test_filepath, 'w')\
              .write(codes[i] + '\n')

        now = int(time.time())

        template_as_string = '{% load django_static %}\n'
        template_as_string += '{% slimfile "' + '; '.join(filenames) + '" %}'
        # First do it without DJANGO_STATIC_MEDIA_URL set

        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        expect_filename = _django_static._combine_filenames(filenames)
        bits = expect_filename.split('.')
        expect_filename = expect_filename[:-3]
        expect_filename += '.%s%s' % (now, os.path.splitext(filenames[0])[1])
        self.assertFilenamesAlmostEqual(rendered, name_prefix + expect_filename)

        if save_prefix:
            new_filenames_set = os.listdir(os.path.join(settings.MEDIA_ROOT, save_prefix))
            self.assertEqual(len(new_filenames_set), 1)
        else:
            filenames_set = set(os.path.basename(x) for x in filenames)
            # what we expect in the media root is all the original
            # filenames plus the newly created one
            new_filenames_set = set(os.listdir(settings.MEDIA_ROOT))
            self.assertEqual(new_filenames_set & filenames_set, filenames_set)
            self.assertEqual(len(filenames_set) + 1, len(new_filenames_set))

        rendered = template.render(context).strip()

        template_as_string = '{% load django_static %}\n'
        template_as_string += '{% slimfile "' + '; '.join(filenames) + '" as new_src %}\n'
        template_as_string += '{{ new_src }}'

        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertFilenamesAlmostEqual(rendered, name_prefix + expect_filename)

        from posix import stat_result
        def fake_stat(arg):
            if arg in test_filepaths:
                faked = list(orig_os_stat(arg))
                faked[stat.ST_MTIME] = faked[stat.ST_MTIME] + 10
                return stat_result(faked)
            else:
                return orig_os_stat(arg)
        orig_os_stat = os.stat
        os.stat = fake_stat

        rendered = template.render(context).strip()
        if settings.DEBUG:
            expect_filename = bits[0] + '.%s.' % (now + 10) + bits[-1]
        else:
            # then it shouldn't change.
            # This effectively means that if you have a live server, and you
            # make some changes to the, say, CSS files your Django templates
            # won't notice this until after you restart Django.
            pass

        self.assertFilenamesAlmostEqual(rendered, name_prefix + expect_filename)


    def test_staticfile_multiple_debug_on(self):
        """Where there are multiple files instead if just one:
        {% slimfile "/js/foo.js; /js/bar.js" %}
        it should become:
        /js/foo_bar.1257xxxxx.js
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True

        filenames = ('/test_33.js', '/test_44.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_staticfile_multiple(filenames, codes)


    def _test_staticfile_multiple(self, filenames, codes, name_prefix='',
                                  save_prefix=None):

        test_filepaths = []
        for i, filename in enumerate(filenames):
            test_filepath = settings.MEDIA_ROOT + filename
            test_filepaths.append(test_filepath)
            open(test_filepath, 'w')\
              .write(codes[i] + '\n')

        now = int(time.time())

        template_as_string = '{% load django_static %}\n'
        template_as_string += '{% staticfile "' + '; '.join(filenames) + '" %}'

        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        expect_filename = _django_static._combine_filenames(filenames)
        bits = expect_filename.split('.')
        expect_filename = expect_filename[:-3]
        expect_filename += '.%s%s' % (now, os.path.splitext(filenames[0])[1])
        self.assertFilenamesAlmostEqual(rendered, name_prefix + expect_filename)

        if save_prefix:
            new_filenames_set = os.listdir(os.path.join(settings.MEDIA_ROOT, save_prefix))
            self.assertEqual(len(new_filenames_set), 1)
        else:
            filenames_set = set(os.path.basename(x) for x in filenames)
            # what we expect in the media root is all the original
            # filenames plus the newly created one
            new_filenames_set = set(os.listdir(settings.MEDIA_ROOT))
            self.assertEqual(new_filenames_set & filenames_set, filenames_set)
            self.assertEqual(len(filenames_set) + 1, len(new_filenames_set))

            new_file = [x for x in new_filenames_set
                        if x not in filenames_set][0]
            new_file_path = os.path.join(settings.MEDIA_ROOT, new_file)

            # the file shouldn't become a symlink
            if sys.platform != "win32":
                self.assertTrue(os.path.lexists(new_file_path))
                self.assertTrue(not os.path.islink(new_file_path))

        rendered = template.render(context).strip()

        template_as_string = '{% load django_static %}\n'
        template_as_string += '{% staticfile "' + '; '.join(filenames) + '" as new_src %}\n'
        template_as_string += '{{ new_src }}'

        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertFilenamesAlmostEqual(rendered, name_prefix + expect_filename)

        from posix import stat_result
        def fake_stat(arg):
            if arg in test_filepaths:
                faked = list(orig_os_stat(arg))
                faked[stat.ST_MTIME] = faked[stat.ST_MTIME] + 10
                return stat_result(faked)
            else:
                return orig_os_stat(arg)
        orig_os_stat = os.stat
        os.stat = fake_stat

        rendered = template.render(context).strip()
        if settings.DEBUG:
            expect_filename = bits[0] + '.%s.' % (now + 10) + bits[-1]
        else:
            # then it shouldn't change.
            # This effectively means that if you have a live server, and you
            # make some changes to the, say, CSS files your Django templates
            # won't notice this until after you restart Django.
            pass

        self.assertFilenamesAlmostEqual(rendered, name_prefix + expect_filename)

    def test_staticall_basic(self):
        settings.DEBUG = True
        settings.DJANGO_STATIC = True

        filenames = ('/test_11.js', '/test_22.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_staticall(filenames, codes)

    def test_staticall_one_file_only(self):
        settings.DEBUG = True
        settings.DJANGO_STATIC = True

        filenames = ('/test_abc.js',)
        codes = ('function (var1, var2)  { return var1+var2; }',)

        self._test_staticall(filenames, codes)

    def test_slimall_basic(self):
        if slimmer is None and cssmin is None:
            return

        settings.DEBUG = True
        settings.DJANGO_STATIC = True

        filenames = ('/testxx.js', '/testyy.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_slimall(filenames, codes)

    def test_slimall_basic_css(self):
        if slimmer is None and cssmin is None:
            return

        settings.DEBUG = True
        settings.DJANGO_STATIC = True

        filenames = ('/adam.css', '/eve.css')
        codes = ('body { gender: male; }',
                 'footer { size: small; }')

        self._test_slimall(filenames, codes)


    def test_slimall_css_files(self):
        if slimmer is None and cssmin is None:
            return

        settings.DEBUG = True
        settings.DJANGO_STATIC = True

        filenames = ('/testxx.css', '/testyy.css')
        codes = ('body { color:blue; }',
                 'p { color:red; }')

        self._test_slimall(filenames, codes,
                           css_medias={'/testxx.css':'screen'})

    def test_slimall_css_files_different_media(self):
        settings.DEBUG = True
        settings.DJANGO_STATIC = True

        filenames = ('/screen1.css', '/screen2.css', '/print_this.css')
        codes = ('body { color:blue; }',
                 'p { color:red; }',
                 'body { margin: 0px; }')

        self._test_slimall(filenames, codes,
                           css_medias={'/print_this.css':'print'})


    def _test_slimall(self, filenames, codes, name_prefix='', media_url='',
                      save_prefix=None,
                      content_slimmed=True,
                      css_medias=None):
        return self._test_staticall(filenames, codes, name_prefix=name_prefix,
                                    media_url=media_url, save_prefix=save_prefix,
                                    content_slimmed=True,
                                    css_medias=css_medias)

    def _test_staticall(self, filenames, codes, name_prefix='', media_url='',
                        save_prefix=None,
                        content_slimmed=False,
                        css_medias=None):

        test_filepaths = []
        for i, filename in enumerate(filenames):
            test_filepath = settings.MEDIA_ROOT + filename
            test_filepaths.append(test_filepath)
            open(test_filepath, 'w')\
              .write(codes[i] + '\n')

        now = int(time.time())
        template_as_string = '{% load django_static %}\n'
        if content_slimmed:
            template_as_string += '{% slimall %}\n'
        else:
            template_as_string += '{% staticall %}\n'

        for filename in filenames:
            if filename.endswith('.js'):
                template_as_string += '<script src="%s"></script>\n' % filename
            elif filename.endswith('.css'):
                if css_medias and css_medias.get(filename):
                    template_as_string += '<link rel="stylesheet" media="%s" href="%s"/>\n' %\
                      (css_medias.get(filename), filename)
                else:
                    template_as_string += '<link rel="stylesheet" href="%s"/>\n' %\
                      filename
            else:
                raise NotImplementedError('????')

        if content_slimmed:
            template_as_string += '{% endslimall %}'
        else:
            template_as_string += '{% endstaticall %}'

        if filenames[0].endswith('.js'):
            assert template_as_string.count('<script ') == len(filenames)
        elif filenames[0].endswith('.css'):
            assert template_as_string.count('<link ') == len(filenames)

        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        if filenames[0].endswith('.js'):
            self.assertEqual(rendered.count('<script '), 1)
        elif filenames[0].endswith('.css'):
            if css_medias is None:
                distinct_medias = set()
            else:
                distinct_medias = set(css_medias.values())
            if '' not in distinct_medias:
                distinct_medias.add('')
            minimum = len(distinct_medias)
            self.assertEqual(rendered.count('<link '), minimum)

        expect_filename = _django_static._combine_filenames(filenames)
        bits = expect_filename.split('.')
        if filenames[0].endswith('.js'):
            expect_filename = expect_filename[:-3]
        elif filenames[0].endswith('.css'):
            if len(distinct_medias) > 1:
                # this is too complicated to test at the moment
                return
            expect_filename = expect_filename[:-4]

        expect_filename += '.%s%s' % (now, os.path.splitext(filenames[0])[1])

        if expect_filename not in rendered:
            # expect_filename is something like
            # '/testxx_testyy.1291842493.css'
            # replace that with a more fuzzy matching
            # This is because the clock might have ticked one second between
            # when the file was created and when the expect_filename
            # variable was prepared.
            ts = re.findall('\d{2,10}', expect_filename)[0]
            previous_second = int(ts) - 1
            other_expect_filename = expect_filename.replace(ts, str(previous_second))
            self.assertTrue(other_expect_filename in rendered, other_expect_filename)

        else:
            self.assertTrue(expect_filename in rendered, expect_filename)

        # this should have created a new file
        if save_prefix:
            new_filenames_set = os.listdir(os.path.join(settings.MEDIA_ROOT, save_prefix))
            self.assertEqual(len(new_filenames_set), 1)
        else:
            filenames_set = set(os.path.basename(x) for x in filenames)
            new_filenames_set = set(os.listdir(settings.MEDIA_ROOT))
            self.assertEqual(new_filenames_set & filenames_set, filenames_set)
            self.assertEqual(len(filenames_set) + 1, len(new_filenames_set))

            new_file = [x for x in new_filenames_set
                        if x not in filenames_set][0]
            new_file_path = os.path.join(settings.MEDIA_ROOT, new_file)

            filepaths = [os.path.join(settings.MEDIA_ROOT, x) for x in filenames_set]

            # the file shouldn't become a symlink
            if sys.platform != "win32" and len(filenames) > 1:
                # unless it's just a single file
                self.assertTrue(os.path.lexists(new_file_path))
                self.assertTrue(not os.path.islink(new_file_path))

                # the content should be the codes combined
                content = open(new_file_path).read()
                expect_content = '\n'.join(codes)
                if content_slimmed:
                    self.assertTrue(len(content.strip()) < len(expect_content.strip()))
                else:
                    self.assertEqual(content.strip(), expect_content.strip())

    def test_stupidity_bug_report_2(self):
        """Reported on
        http://github.com/peterbe/django-static/issues/#issue/2

        This report happens when a user appears to not have any optimization library.
        This happened on Windows where symlinking it not possible.
        """



        settings.MEDIA_URL = "/media/"
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = os.path.join(settings.MEDIA_ROOT, 'forever')

        CSS ="""html {
            background: url('img/bg-top.png') no-repeat center top;
        }"""

        test_filepath = os.path.join(settings.MEDIA_ROOT, 'css')
        if not os.path.isdir(test_filepath):
            os.mkdir(test_filepath)
        test_filepath = os.path.join(test_filepath, 'base.css')
        open(test_filepath, 'w').write(CSS)

        # Because this bug depends on the system being windows and slimmer not
        # being installed, we'll skip the fancy functions and go straight to the
        # ultimate _static_file function
        reload(sys.modules['django_static.templatetags.django_static'])
        result = _django_static._static_file('css/base.css',
                                             optimize_if_possible=False,
                                             symlink_if_possible=False)
        # expect the result to be something like css/base.1273229589.css
        self.assertTrue(result.startswith('css/base.'))
        self.assertTrue(re.findall('base\.\d+\.css', result))


    def test_slim_content(self):
        """test the {% slimcontent %}...{% endslimcontent %} tag"""
        if slimmer is None and cssmin is None:
            return

        template_as_string = """{% load django_static %}
        {% slimcontent %}
        body {
          font-size: 14pt;
        }
        {% endslimcontent %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        expect = u'body{font-size:14pt}'
        self.assertEqual(rendered, expect)


        template_as_string = """{% load django_static %}
        {% slimcontent "js" %}
        function (var1, var2) {
          return var1 + var2;
        }
        {% endslimcontent %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()

        expect = u'function (var1,var2) {return var1 + var2;}'
        self.assertEqual(rendered, expect)

        template_as_string = """{% load django_static %}
        {% slimcontent "html" %}
        <ul>
          <li> one </li>
        </ul>
        {% endslimcontent %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()

        expect = u'<ul><li> one </li></ul>'
        self.assertEqual(rendered, expect)

        html_rendered = rendered
        template_as_string = """{% load django_static %}
        {% slimcontent "xhtml" %}
        <ul>
          <li> one </li>
        </ul>
        {% endslimcontent %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertEqual(html_rendered, rendered)

    def test_bad_slimcontent_usage(self):
        if slimmer is None and cssmin is None:
            return

        # the format argument has to quoted
        template_as_string = """{% load django_static %}
        {% slimcontent html %}
        <ul>
          <li> one </li>
        </ul>
        {% endslimcontent %}
        """
        from django.template import TemplateSyntaxError
        self.assertRaises(TemplateSyntaxError, Template, template_as_string)

        # if it's an unrecognized format such as thml or csss then raise a
        # template syntax error in runtime
        template_as_string = """{% load django_static %}
        {% slimcontent "xxxjunk" %}
        unguessable content
        {% endslimcontent %}
        """
        template = Template(template_as_string)
        context = Context()
        self.assertRaises(TemplateSyntaxError, template.render, context)


    def test_staticfile_as_context_variable(self):
        """Use the 'as' operator to define the src name"""

        settings.DEBUG = True
        settings.DJANGO_STATIC = True

        filename = "/foo.js"
        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write('samplecode()\n')

        media_root_files_before = os.listdir(settings.MEDIA_ROOT)
        template_as_string = """{% load django_static %}
        {% staticfile "/foo.js" as name %}
        <script src="{{ name }}"></script>
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertTrue(
          re.findall('<script src=\"/foo.\d+\.js\"></script>', rendered)
        )


    def test_staticfile_css_with_image_urls(self):
        """staticfile a css file that contains image urls"""
        settings.DEBUG = False
        settings.DJANGO_STATIC = True


        filename = "/medis.css"
        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write("""
        h1 {
          background-image: url('/img1.gif');
        }
        h2 {
          background-image: url("/img2.gif");
        }
        h3 {
          background-image: url(/img3.gif);
        }
        h9 {
          background-image: url(/img9.gif);
        }
        """)

        open(settings.MEDIA_ROOT + '/img1.gif', 'w').write(_GIF_CONTENT)
        open(settings.MEDIA_ROOT + '/img2.gif', 'w').write(_GIF_CONTENT)
        open(settings.MEDIA_ROOT + '/img3.gif', 'w').write(_GIF_CONTENT)
        # deliberately no img9.gif

        template_as_string = """{% load django_static %}
        {% slimfile "/medis.css" %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertTrue(re.findall('medis\.\d+\.css', rendered))

        # open the file an expect that it did staticfile for the images
        # within
        new_filename = re.findall('/medis\.\d+\.css', rendered)[0]
        new_filepath = os.path.join(settings.MEDIA_ROOT,
                                    os.path.basename(new_filename))
        content = open(new_filepath).read()
        self.assertTrue(re.findall('/img1\.\d+\.gif', content))
        self.assertTrue(re.findall('/img2\.\d+\.gif', content))
        self.assertTrue(re.findall('/img3\.\d+\.gif', content))
        self.assertTrue(re.findall('/img9\.gif', content))

    def test_shortcut_functions(self):
        """you can use slimfile() and staticfile() without using template tags"""

        settings.DEBUG = True
        settings.DJANGO_STATIC = True

        filename = "/foo101.js"
        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write("""
        function test() {
          return "done";
        }
        """)

        filename = "/foo102.js"
        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write("""
        function test() {
          return "done";
        }
        """)

        reload(sys.modules['django_static.templatetags.django_static'])
        from django_static.templatetags.django_static import slimfile, staticfile
        result = staticfile('/foo101.js')
        self.assertTrue(re.findall('/foo101\.\d+\.js', result))

        result = slimfile('/foo102.js')
        self.assertTrue(re.findall('/foo102\.\d+\.js', result))
        if slimmer is not None or cssmin is not None:
            # test the content
            new_filepath = os.path.join(settings.MEDIA_ROOT,
                                        os.path.basename(result))
            content = open(new_filepath).read()
            self.assertEqual(content, 'function test(){return "done";}')

    def test_staticfile_on_nonexistant_file(self):
        """should warn and do nothing if try to staticfile a file that doesn't exist"""

        import django_static.templatetags.django_static
        #from django_static.templatetags.django_static import staticfile
        class MockedWarnings:
            def warn(self, msg, *a, **k):
                self.msg = msg

        mocked_warnings = MockedWarnings()
        django_static.templatetags.django_static.warnings = mocked_warnings
        result = django_static.templatetags.django_static.staticfile('/tralalal.js')
        self.assertEqual(result, '/tralalal.js')
        self.assertTrue(mocked_warnings.msg)
        self.assertTrue(mocked_warnings.msg.count('tralalal.js'))

    def test_has_optimizer(self):
        """test the utility function has_optimizer(type)"""
        from django_static.templatetags.django_static import has_optimizer

        # definitely if you have defined a DJANGO_STATIC_YUI_COMPRESSOR
        settings.DJANGO_STATIC_YUI_COMPRESSOR = 'sure'
        self.assertTrue(has_optimizer('css'))
        del settings.DJANGO_STATIC_YUI_COMPRESSOR

        self.assertEqual(has_optimizer('css'), bool(slimmer or cssmin))

        # for javascript
        settings.DJANGO_STATIC_YUI_COMPRESSOR = 'sure'
        settings.DJANGO_STATIC_CLOSURE_COMPILER = 'sure'

        self.assertTrue(has_optimizer('js'))
        del settings.DJANGO_STATIC_CLOSURE_COMPILER
        self.assertTrue(has_optimizer('js'))
        del settings.DJANGO_STATIC_YUI_COMPRESSOR

        self.assertEqual(has_optimizer('js'), bool(slimmer or cssmin))

        self.assertRaises(ValueError, has_optimizer, 'uh')

    def test_running_closure_compiler(self):
        settings.DJANGO_STATIC_CLOSURE_COMPILER = 'mocked'

        import django_static.templatetags.django_static
        optimize = django_static.templatetags.django_static.optimize

        class MockedPopen:
            return_error = False

            def __init__(self, cmd, *a, **__):
                self.cmd = cmd

            def communicate(self, code):
                self.code_in = code
                if self.return_error:
                    return '', 'Something wrong!'
                else:
                    return code.strip().upper(), None

        class BadMockedPopen(MockedPopen):
            return_error = True

        old_Popen = django_static.templatetags.django_static.Popen
        django_static.templatetags.django_static.Popen = MockedPopen

        code = 'function() { return 1 + 2; }'
        new_code = optimize(code, 'js')
        self.assertTrue(new_code.startswith('FUNCTION'))

        django_static.templatetags.django_static.Popen = BadMockedPopen

        new_code = optimize(code, 'js')
        self.assertTrue(code in new_code)
        self.assertTrue(new_code.find('/*') < new_code.find('Something wrong!') < \
          new_code.find('*/'))

        del settings.DJANGO_STATIC_CLOSURE_COMPILER
        django_static.templatetags.django_static.Popen = MockedPopen

        new_code = optimize(code, 'js')

        django_static.templatetags.django_static.Popen = old_Popen


    def test_running_yui_compressor(self):
        if hasattr(settings, 'DJANGO_STATIC_CLOSURE_COMPILER'):
            del settings.DJANGO_STATIC_CLOSURE_COMPILER

        settings.DJANGO_STATIC_YUI_COMPRESSOR = 'mocked'

        import django_static.templatetags.django_static
        optimize = django_static.templatetags.django_static.optimize

        class MockedPopen:
            return_error = False

            def __init__(self, cmd, *a, **__):
                self.cmd = cmd

            def communicate(self, code):
                self.code_in = code
                if self.return_error:
                    return '', 'Something wrong!'
                else:
                    return code.strip().upper(), None

        class BadMockedPopen(MockedPopen):
            return_error = True

        old_Popen = django_static.templatetags.django_static.Popen
        django_static.templatetags.django_static.Popen = MockedPopen

        code = 'function() { return 1 + 2; }'
        new_code = optimize(code, 'js')
        self.assertTrue(new_code.startswith('FUNCTION'))

        django_static.templatetags.django_static.Popen = BadMockedPopen

        new_code = optimize(code, 'js')
        self.assertTrue(code in new_code)
        self.assertTrue(new_code.find('/*') < new_code.find('Something wrong!') < \
          new_code.find('*/'))

        django_static.templatetags.django_static.Popen = MockedPopen

        code = 'body { font: big; }'
        new_code = optimize(code, 'css')
        self.assertTrue(new_code.startswith('body'))

        new_code = optimize(code, 'css')
        del settings.DJANGO_STATIC_YUI_COMPRESSOR

        django_static.templatetags.django_static.Popen = old_Popen

    def test_load_file_proxy(self):

        settings.DEBUG = False
        func = _django_static._load_file_proxy

        if hasattr(settings, 'DJANGO_STATIC_FILE_PROXY'):
            del settings.DJANGO_STATIC_FILE_PROXY

        proxy_function = func()
        self.assertEqual(proxy_function.func_name, 'file_proxy_nothing')
        # this function will always return the first argument
        self.assertEqual(proxy_function('anything', 'other', shit=123), 'anything')
        self.assertEqual(proxy_function(None), None)
        self.assertEqual(proxy_function(123), 123)
        self.assertRaises(TypeError, proxy_function)
        self.assertRaises(TypeError, proxy_function, keyword='argument')

        # the same would happen if DJANGO_STATIC_FILE_PROXY is defined but
        # set to nothing
        settings.DJANGO_STATIC_FILE_PROXY = None
        proxy_function = func()
        self.assertEqual(proxy_function.func_name, 'file_proxy_nothing')

        # Now set it to something sensible
        # This becomes the equivalent of `from django_static.tests import fake_file_proxy`
        # Test that that works to start with
        settings.DJANGO_STATIC_FILE_PROXY = 'django_static.tests.fake_file_proxy'

        proxy_function = func()
        self.assertNotEqual(proxy_function.func_name, 'file_proxy_nothing')

        # but that's not enough, now we need to "monkey patch" this usage
        _django_static.file_proxy = proxy_function

        # now with this set up it will start to proxy and staticfile() or slimfile()

        open(settings.MEDIA_ROOT + '/img100.gif', 'w').write(_GIF_CONTENT)

        template_as_string = """{% load django_static %}
        {% staticfile "/img100.gif" %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertEqual(_last_fake_file_uri, rendered)

        # we can expect that a keyword argument called 'filepath' was used
        self.assertTrue('filepath' in _last_fake_file_keyword_arguments)
        # the filepath should point to the real file
        self.assertTrue(os.path.isfile(_last_fake_file_keyword_arguments['filepath']))

        self.assertTrue('new' in _last_fake_file_keyword_arguments)
        self.assertTrue(_last_fake_file_keyword_arguments['new'])

        self.assertTrue('changed' in _last_fake_file_keyword_arguments)
        self.assertFalse(_last_fake_file_keyword_arguments['changed'])

        self.assertTrue('checked' in _last_fake_file_keyword_arguments)
        self.assertTrue(_last_fake_file_keyword_arguments['checked'])

        # if you run it again, because we're not in debug mode the second time
        # the file won't be checked if it has changed
        assert not settings.DEBUG
        rendered = template.render(context).strip()
        self.assertEqual(_last_fake_file_uri, rendered)
        self.assertFalse(_last_fake_file_keyword_arguments['new'])
        self.assertFalse(_last_fake_file_keyword_arguments['checked'])
        self.assertFalse(_last_fake_file_keyword_arguments['changed'])

        # What if DJANGO_STATIC = False
        # It should still go through the configured file proxy function
        settings.DJANGO_STATIC = False
        rendered = template.render(context).strip()
        self.assertEqual(rendered, '/img100.gif')
        self.assertFalse(_last_fake_file_keyword_arguments['checked'])
        self.assertFalse(_last_fake_file_keyword_arguments['changed'])

    def test_file_proxy_with_name_prefix(self):
        # Test it with a name prefix
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_NAME_PREFIX = '/love-cache'

        open(settings.MEDIA_ROOT + '/imgXXX.gif', 'w').write(_GIF_CONTENT)

        # set up the file proxy
        settings.DJANGO_STATIC_FILE_PROXY = 'django_static.tests.fake_file_proxy'
        func = _django_static._load_file_proxy
        proxy_function = func()
        # but that's not enough, now we need to "monkey patch" this usage
        _django_static.file_proxy = proxy_function

        template_as_string = """{% load django_static %}
        {% staticfile "/imgXXX.gif" %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()

        self.assertEqual(_last_fake_file_uri, rendered)
        self.assertTrue(_last_fake_file_keyword_arguments['new'])
        self.assertTrue('filepath' in _last_fake_file_keyword_arguments)


    def test_cross_optimizing_imported_css(self):
        """Most basic test
        {% slimfile "/css/foobar.css" %}
        it should become
        /foobar.123xxxxxxx.css

        But foobar.css will have to contain these:

            @import "/css/one.css";
            @import "two.css";
            @import url(/css/three.css);
            @import url('two.css');

        Also, in them we're going to refer to images.
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True


        filename = 'css/foobar.css'
        if not os.path.isdir(os.path.join(settings.MEDIA_ROOT, 'css')):
            os.mkdir(os.path.join(settings.MEDIA_ROOT, 'css'))
            if not os.path.isdir(os.path.join(settings.MEDIA_ROOT, 'css', 'deeper')):
                os.mkdir(os.path.join(settings.MEDIA_ROOT, 'css', 'deeper'))

        test_filepath = os.path.join(settings.MEDIA_ROOT, filename)
        open(test_filepath, 'w').write("""
        @import "/css/one.css";
        @import "two.css";
        @import url(/css/deeper/three.css);
        @import url('four.css');
        """)
        template_as_string = """
        {% load django_static %}
        {% slimfile "/css/foobar.css" %}
        """

        # now we need to create all of those mock files
        open(settings.MEDIA_ROOT + '/css/one.css', 'w').write("""
        /* COMMENT ONE */
        p { background-image: url('one.gif'); }
        """)

        open(settings.MEDIA_ROOT + '/css/two.css', 'w').write("""
        /* COMMENT TWO */
        p { background-image: url(two.gif); }
        """)

        open(settings.MEDIA_ROOT + '/css/deeper/three.css', 'w').write("""
        /* COMMENT THREE */
        p { background-image: url("three.gif"); }
        """)

        open(settings.MEDIA_ROOT + '/css/four.css', 'w').write("""
        /* COMMENT FOUR */
        p { background-image: url("/four.gif"); }
        """)

        # now we need to create the images
        open(settings.MEDIA_ROOT + '/css/one.gif', 'w').write(_GIF_CONTENT)
        open(settings.MEDIA_ROOT + '/css/two.gif', 'w').write(_GIF_CONTENT)
        open(settings.MEDIA_ROOT + '/css/deeper/three.gif', 'w').write(_GIF_CONTENT)
        open(settings.MEDIA_ROOT + '/four.gif', 'w').write(_GIF_CONTENT)

        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()

        self.assertTrue(re.findall('/css/foobar\.\d+.css', rendered))
        foobar_content = open(settings.MEDIA_ROOT + rendered).read()
        self.assertTrue(not foobar_content.count('\n'))
        self.assertTrue(re.findall('@import "/css/one\.\d+\.css";', foobar_content))
        # notice how we add the '/css/' path to this one!
        # it was '@import "two.css";' originally
        self.assertTrue(re.findall('@import "/css/two\.\d+\.css";', foobar_content))
        self.assertTrue(re.findall('@import url\(/css/deeper/three\.\d+\.css\);', foobar_content))
        self.assertTrue(re.findall('@import url\(\'/css/four\.\d+\.css\'\);', foobar_content))

        # now lets study the results of each of these files
        filename_one = re.findall('one\.\d+\.css', foobar_content)[0]
        filename_two = re.findall('two\.\d+\.css', foobar_content)[0]
        filename_three = re.findall('three\.\d+\.css', foobar_content)[0]
        filename_four = re.findall('four\.\d+\.css', foobar_content)[0]

        content_one = open(settings.MEDIA_ROOT + '/css/' + filename_one).read()
        self.assertTrue('COMMENT ONE' not in content_one)
        self.assertTrue(re.findall('one\.\d+\.gif', content_one))
        image_filename_one = re.findall('one\.\d+\.gif', content_one)[0]

        content_two = open(settings.MEDIA_ROOT + '/css/' + filename_two).read()
        self.assertTrue('COMMENT TWO' not in content_one)
        self.assertTrue(re.findall('two\.\d+\.gif', content_two))
        image_filename_two = re.findall('two\.\d+\.gif', content_two)[0]

        content_three = open(settings.MEDIA_ROOT + '/css/deeper/' + filename_three).read()
        self.assertTrue('COMMENT THREE' not in content_three)
        self.assertTrue(re.findall('three\.\d+\.gif', content_three))
        image_filename_three = re.findall('three\.\d+\.gif', content_three)[0]

        content_four = open(settings.MEDIA_ROOT + '/css/' + filename_four).read()
        self.assertTrue('COMMENT FOUR' not in content_four)
        self.assertTrue(re.findall('four\.\d+\.gif', content_four))
        image_filename_four = re.findall('four\.\d+\.gif', content_four)[0]

        # now check that these images were actually created
        self.assertTrue(image_filename_one in os.listdir(settings.MEDIA_ROOT + '/css'))
        self.assertTrue(image_filename_two in os.listdir(settings.MEDIA_ROOT + '/css'))
        self.assertTrue(image_filename_three in os.listdir(settings.MEDIA_ROOT + '/css/deeper'))
        self.assertTrue(image_filename_four in os.listdir(settings.MEDIA_ROOT))



    def test_cross_optimizing_imported_css_with_save_prefix_and_name_prefix(self):
        """This test is entirely copied from test_cross_optimizing_imported_css()
        but with SAVE_PREFIX and NAME_PREFIX added.
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_NAME_PREFIX = '/infinity'
        settings.DJANGO_STATIC_NAME_PREFIX = '/infinity'
        settings.DJANGO_STATIC_SAVE_PREFIX = os.path.join(settings.MEDIA_ROOT, 'special')

        filename = 'css/foobar.css'
        if not os.path.isdir(os.path.join(settings.MEDIA_ROOT, 'css')):
            os.mkdir(os.path.join(settings.MEDIA_ROOT, 'css'))
            if not os.path.isdir(os.path.join(settings.MEDIA_ROOT, 'css', 'deeper')):
                os.mkdir(os.path.join(settings.MEDIA_ROOT, 'css', 'deeper'))

        test_filepath = os.path.join(settings.MEDIA_ROOT, filename)
        open(test_filepath, 'w').write("""
        @import "/css/one.css";
        @import "two.css";
        @import url(/css/deeper/three.css);
        @import url('four.css');
        """)
        template_as_string = """
        {% load django_static %}
        {% slimfile "/css/foobar.css" %}
        """

        # now we need to create all of those mock files
        open(settings.MEDIA_ROOT + '/css/one.css', 'w').write("""
        /* COMMENT ONE */
        p { background-image: url('one.gif'); }
        """)

        open(settings.MEDIA_ROOT + '/css/two.css', 'w').write("""
        /* COMMENT TWO */
        p { background-image: url(two.gif); }
        """)

        open(settings.MEDIA_ROOT + '/css/deeper/three.css', 'w').write("""
        /* COMMENT THREE */
        p { background-image: url("three.gif"); }
        """)

        open(settings.MEDIA_ROOT + '/css/four.css', 'w').write("""
        /* COMMENT FOUR */
        p { background-image: url("/four.gif"); }
        """)

        # now we need to create the images
        open(settings.MEDIA_ROOT + '/css/one.gif', 'w').write(_GIF_CONTENT)
        open(settings.MEDIA_ROOT + '/css/two.gif', 'w').write(_GIF_CONTENT)
        open(settings.MEDIA_ROOT + '/css/deeper/three.gif', 'w').write(_GIF_CONTENT)
        open(settings.MEDIA_ROOT + '/four.gif', 'w').write(_GIF_CONTENT)

        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()

        self.assertTrue(re.findall('/infinity/css/foobar\.\d+.css', rendered))
        foobar_content = open(settings.MEDIA_ROOT + '/special' + \
          rendered.replace('/infinity','')).read()
        self.assertTrue(not foobar_content.count('\n'))
        self.assertTrue(re.findall('@import "/infinity/css/one\.\d+\.css";', foobar_content))
        # notice how we add the '/css/' path to this one!
        # it was '@import "two.css";' originally
        self.assertTrue(re.findall('@import "/infinity/css/two\.\d+\.css";', foobar_content))
        self.assertTrue(re.findall('@import url\(/infinity/css/deeper/three\.\d+\.css\);', foobar_content))
        self.assertTrue(re.findall('@import url\(\'/infinity/css/four\.\d+\.css\'\);', foobar_content))

        # now lets study the results of each of these files
        filename_one = re.findall('one\.\d+\.css', foobar_content)[0]
        filename_two = re.findall('two\.\d+\.css', foobar_content)[0]
        filename_three = re.findall('three\.\d+\.css', foobar_content)[0]
        filename_four = re.findall('four\.\d+\.css', foobar_content)[0]

        content_one = open(settings.MEDIA_ROOT + '/special/css/' + filename_one).read()
        self.assertTrue('COMMENT ONE' not in content_one)
        self.assertTrue(re.findall('one\.\d+\.gif', content_one))
        image_filename_one = re.findall('one\.\d+\.gif', content_one)[0]

        content_two = open(settings.MEDIA_ROOT + '/special/css/' + filename_two).read()
        self.assertTrue('COMMENT TWO' not in content_one)
        self.assertTrue(re.findall('two\.\d+\.gif', content_two))
        image_filename_two = re.findall('two\.\d+\.gif', content_two)[0]

        content_three = open(settings.MEDIA_ROOT + '/special/css/deeper/' + filename_three).read()
        self.assertTrue('COMMENT THREE' not in content_three)
        self.assertTrue(re.findall('three\.\d+\.gif', content_three))
        image_filename_three = re.findall('three\.\d+\.gif', content_three)[0]

        content_four = open(settings.MEDIA_ROOT + '/special/css/' + filename_four).read()
        self.assertTrue('COMMENT FOUR' not in content_four)
        self.assertTrue(re.findall('four\.\d+\.gif', content_four))
        image_filename_four = re.findall('four\.\d+\.gif', content_four)[0]

        # now check that these images were actually created
        self.assertTrue(image_filename_one in os.listdir(settings.MEDIA_ROOT + '/special/css'))
        self.assertTrue(image_filename_two in os.listdir(settings.MEDIA_ROOT + '/special/css'))
        self.assertTrue(image_filename_three in os.listdir(settings.MEDIA_ROOT + '/special/css/deeper'))
        self.assertTrue(image_filename_four in os.listdir(settings.MEDIA_ROOT + '/special'))

    def test_slimming_non_ascii_css(self):
        """
        https://github.com/peterbe/django-static/issues/#issue/11
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True


        filename = 'fax.css'
        #if not os.path.isdir(os.path.join(settings.MEDIA_ROOT):
        #    os.mkdir(os.path.join(settings.MEDIA_ROOT, 'css'))
        #    if not os.path.isdir(os.path.join(settings.MEDIA_ROOT, 'css', 'deeper')):
        #        os.mkdir(os.path.join(settings.MEDIA_ROOT, 'css', 'deeper'))

        test_filepath = os.path.join(settings.MEDIA_ROOT, filename)
        codecs.open(test_filepath, 'w', 'utf8').write(u"""
        @font-face {
           font-family: 'da39a3ee5e';
           src: url('da39a3ee5e.eot');
           src: local('☺'), url(data:font/woff;charset=utf-8;base64,[ snip ]) format('truetype');
           font-weight: normal;
           font-style: normal;
        }
        """)

        template_as_string = """
        {% load django_static %}
        {% slimfile "/fax.css" %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertTrue(re.findall('/fax\.\d+.css', rendered))
        content = codecs.open(settings.MEDIA_ROOT + rendered, 'r', 'utf-8').read()

        if slimmer is None and cssmin is None:
            return
        self.assertTrue(u"src:url('/da39a3ee5e.eot');src:local('\u263a')," in content)

    def test_slimming_non_ascii_import_css(self):
        """
        https://github.com/peterbe/django-static/issues/#issue/11
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True


        filename = 'pax.css'
        #if not os.path.isdir(os.path.join(settings.MEDIA_ROOT):
        #    os.mkdir(os.path.join(settings.MEDIA_ROOT, 'css'))
        #    if not os.path.isdir(os.path.join(settings.MEDIA_ROOT, 'css', 'deeper')):
        #        os.mkdir(os.path.join(settings.MEDIA_ROOT, 'css', 'deeper'))

        test_filepath = os.path.join(settings.MEDIA_ROOT, filename)
        codecs.open(test_filepath, 'w', 'utf8').write('@import "bax.css";\n')

        test_filepath = os.path.join(settings.MEDIA_ROOT, 'bax.css')
        codecs.open(test_filepath, 'w', 'utf8').write(u"""
        @font-face {
           font-family: 'da39a3ee5e';
           src: url('da39a3ee5e.eot');
           src: local('☺'), url(data:font/woff;charset=utf-8;base64,[ snip ]) format('truetype');
           font-weight: normal;
           font-style: normal;
        }
        """)

        template_as_string = """
        {% load django_static %}
        {% slimfile "/pax.css" %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertTrue(re.findall('/pax\.\d+.css', rendered))
        content = open(settings.MEDIA_ROOT + rendered).read()
        self.assertTrue(re.findall('/bax\.\d+.css', content))
        generated_filename = re.findall('(/bax\.\d+.css)', content)[0]
        # open the generated new file
        content = codecs.open(settings.MEDIA_ROOT + generated_filename, 'r', 'utf-8').read()
        if slimmer is None and cssmin is None:
            return
        self.assertTrue(u"src:url('/da39a3ee5e.eot');src:local('\u263a')," in content)

    def test_ignoring_data_uri_scheme(self):
        settings.DEBUG = False
        settings.DJANGO_STATIC = True

        html = u"""
            <img src="pax.jpg" />
            <img src="data_foo.jpg" />
            <img src="data:image/png;..." />
            <img src="data:foo/bar;..." />
        """

        css = u"""
            @font-face {
               src: url('da39a3ee5e.eot');
               src: local('☺'), url(data:font/woff;charset=utf-8;base64,[ snip ]) format('truetype');
            }

            a {
                background: url(pax.jpg)
            }

            strong {
                background: url('data_yadda.jpg')
            }
        """

        # first test some html
        re_html = re.findall(_django_static.IMG_REGEX, html)
        self.assertEqual(re_html, [u'pax.jpg', u'data_foo.jpg'])

        # test some css
        re_css = re.findall(_django_static.REFERRED_CSS_URLS_REGEX, css)
        self.assertEqual(re_css, [u"'da39a3ee5e.eot'", u'pax.jpg', u"'data_yadda.jpg'"])

    def test_slimall_with_defer(self):
        settings.DEBUG = False
        settings.DJANGO_STATIC = True

        template_as_string = u"""
            {% load django_static %}
            {% slimall %}
            <script defer src="/foo.js"></script>
            <script defer src="/bar.js"></script>
            {% endslimall %}
        """

        filename = "/foo.js"
        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write("""
        function (var) { return var++; }
        """)

        filename = "/bar.js"
        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write("""
        function (var) { return var++; }
        """)

        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertTrue(rendered.startswith(u'<script defer src="/foo_bar.'))

    def test_setting__DJANGO_STATIC_MEDIA_URL_ALWAYS(self):
        settings.DEBUG = True
        settings.DJANGO_STATIC = False
        settings.DJANGO_STATIC_MEDIA_URL_ALWAYS = False
        settings.DJANGO_STATIC_MEDIA_URL = "//cdn"

        filename = "/foo.js"
        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write('samplecode()\n')

        template_as_string = """{% load django_static %}
        {% staticfile "/foo.js" %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertEqual(rendered, u"/foo.js")

        settings.DJANGO_STATIC_MEDIA_URL_ALWAYS = True
        rendered = template.render(context).strip()
        self.assertEqual(rendered, u"//cdn/foo.js")

        settings.DJANGO_STATIC = True
        rendered = template.render(context).strip()
        self.assertTrue(re.findall("//cdn/foo\.\d+\.js", rendered))

        settings.DJANGO_STATIC = False

        filename = "/bar.js"
        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write('samplecode()\n')

        template_as_string = """{% load django_static %}
        {% slimall %}
        <script src="/bar.js"></script>
        {% endslimall %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertEqual(rendered, u'<script src="//cdn/bar.js"></script>')

        settings.DJANGO_STATIC = True
        rendered = template.render(context).strip()
        self.assertTrue(rendered.startswith(u'<script src="//cdn/bar.'))
        self.assertTrue(re.findall("//cdn/bar\.\d+\.js", rendered))

        template_as_string = """{% load django_static %}
        {% slimall %}
        <link rel="stylesheet" href="/bar.css"/>
        {% endslimall %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertTrue('href="//cdn/bar.css"' in rendered)
        self.assertTrue('media="screen"' not in rendered)

    def test_slimall_with_STATIC_MEDIA_URL(self):
        settings.DEBUG = False
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_MEDIA_URL_ALWAYS = False
        settings.DJANGO_STATIC_MEDIA_URL = "//cdn"

        filename = "/bar.css"
        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write('body { color:#ccc; }\n')

        template_as_string = """{% load django_static %}
        {% slimall %}
        <link rel="stylesheet" href="/bar.css"/>
        {% endslimall %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()

        self.assertTrue(re.findall("//cdn/bar\.\d+\.css", rendered))
        self.assertTrue('media="screen"' not in rendered)
        self.assertTrue('type="text/css"' not in rendered)

    def test_slim_with_jsmin(self):
        try:
            import jsmin
        except ImportError:
            return

        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_JSMIN = True
        settings.DJANGO_STATIC_CLOSURE_COMPILER = None
        settings.DJANGO_STATIC_YUI_COMPRESSOR = None

        dummy_content = "var foo = function(aaa) { return aaa + 1; }"
        open(settings.MEDIA_ROOT + '/test_A.js', 'w')\
          .write(dummy_content)

        template_as_string = """{% load django_static %}
        {% slimfile "/test_A.js" %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertTrue(re.findall("/test_A\.\d+\.js", rendered))
        content = open(settings.MEDIA_ROOT + rendered).read()
        self.assertTrue(len(dummy_content) > len(content))

    def test_fail_yui_compressor(self):
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_CLOSURE_COMPILER = None
        settings.DJANGO_STATIC_YUI_COMPRESSOR = 'Something'

        dummy_content = "var foo = function(aaa) { return aaa + 1; }"
        open(settings.MEDIA_ROOT + '/test_A.js', 'w')\
          .write(dummy_content)

        template_as_string = """{% load django_static %}
        {% slimfile "/test_A.js" %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertTrue(re.findall("/test_A\.\d+\.js", rendered))
        content = open(settings.MEDIA_ROOT + rendered).read()
        self.assertTrue('ERROR' in content)
        self.assertTrue(content.count('/*') and content.count('*/'))
        # find it not compressed
        self.assertTrue(dummy_content in content)

    def test_fail_closure_compressor(self):
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_CLOSURE_COMPILER = 'Something'
        settings.DJANGO_STATIC_YUI_COMPRESSOR = None

        dummy_content = "var foo = function(aaa) { return aaa + 1; }"
        open(settings.MEDIA_ROOT + '/test_A.js', 'w')\
          .write(dummy_content)

        template_as_string = """{% load django_static %}
        {% slimfile "/test_A.js" %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertTrue(re.findall("/test_A\.\d+\.js", rendered))
        content = open(settings.MEDIA_ROOT + rendered).read()
        self.assertTrue('ERROR' in content)
        self.assertTrue(content.count('/*') and content.count('*/'))
        # find it not compressed
        self.assertTrue(dummy_content in content)


# These have to be mutable so that we can record that they have been used as
# global variables.
_last_fake_file_uri = None
_last_fake_file_keyword_arguments = None

def fake_file_proxy(uri, **k):
    # reset the global mutables used to check that file_proxy() was called
    global _last_fake_file_uri
    global _last_fake_file_keyword_arguments

    _last_fake_file_uri = uri
    _last_fake_file_keyword_arguments = k
    return uri

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *


import views

urlpatterns = patterns('',
    url(r'^/?$', views.page, name="page"),
    
)
########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.template import RequestContext

def page(request):
    return render_to_response('page.html', locals(),
                              context_instance=RequestContext(request))    

########NEW FILE########
__FILENAME__ = gorun_settings
DIRECTORIES = (
    (('django_static/tests.py',
      'django_static/templatetags/django_static.py'),
#     './manage.py test django_static.TestDjangoStatic'),     
#     './manage.py test django_static.TestDjangoStatic.test_slimfile_multiple_basic'),
#     './manage.py test django_static.TestDjangoStatic.test_cross_optimizing_imported_css'),
     './manage.py test django_static.TestDjangoStatic.test_cross_optimizing_imported_css_with_save_prefix_and_name_prefix'),
#     './manage.py test django_static.TestDjangoStatic.test_staticall_basic'),
#     './manage.py test django_static.TestDjangoStatic'),
#     './manage.py test django_static.TestDjangoStatic.test_slimall_basic_css'),
#     './manage.py test django_static.TestDjangoStatic.test_slimfiles_scripts'),
#     './manage.py test django_static.TestDjangoStatic.test_slimfiles_styles'),
#     './manage.py test django_static.TestDjangoStatic.test_slimfiles_scripts_and_styles'),
#     './manage.py test django_static.TestDjangoStatic.test_slimfiles_scripts_and_styles_with_name_prefix'),
#     './manage.py test django_static.TestDjangoStatic.test_slimfiles_scripts_and_styles_with_save_and_name_prefix_with_media_url'),     
#     './manage.py test django_static.TestDjangoStatic.test__combine_filenames'),     
)               
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
__FILENAME__ = delete_all_timestamped_files
import os
import re
def delete_here(dir):
    for f in os.listdir(dir):
        if os.path.isdir(os.path.join(dir, f)):
            delete_here(os.path.join(dir, f))
        elif re.findall('\.\d{10}\.', f):
            print os.path.join(dir, f)
            os.remove(os.path.join(dir, f))
if __name__ == '__main__':
    delete_here(os.path.abspath(os.path.dirname(__file__)))
    
########NEW FILE########
__FILENAME__ = settings
# Django settings for django_static project.
import os
OUR_ROOT = os.path.realpath(os.path.dirname(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
# good bye Django 1.1!
#DATABASE_ENGINE = 'sqlite3'
#DATABASE_NAME = TEST_DATABASE_NAME = ':memory:'

CACHE_BACKEND = 'locmem:///'


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
MEDIA_ROOT = os.path.join(OUR_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'nsma0=bc56bwj7h*_*4g0)iibz-uc1^l5$e6df1&yh(r1u*pv8'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    #'django.contrib.auth',
    #'django.contrib.contenttypes',
    #'django.contrib.sessions',
    #'django.contrib.sites',
    'django_static',
    'exampleapp',
)




DJANGO_STATIC = True

#DJANGO_STATIC_CLOSURE_COMPILER = '/home/peterbe/tmp/compiler-latest/compiler.jar'
#DJANGO_STATIC_YUI_COMPRESSOR = '/home/peterbe/tmp/yuicompressor-2.4.2/build/yuicompressor-2.4.2.jar'
#DJANGO_STATIC_JSMIN = True

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from settings import MEDIA_ROOT


urlpatterns = patterns('',
    # Example:
    (r'^exampleapp/', include('exampleapp.urls')),

    # medi
    url(r'^images/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': MEDIA_ROOT + '/images'}),
    url(r'^css/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': MEDIA_ROOT + '/css'}),
    url(r'^javascript/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': MEDIA_ROOT + '/javascript'}),
                       
)

########NEW FILE########
