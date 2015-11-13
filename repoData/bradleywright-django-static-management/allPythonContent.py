__FILENAME__ = lib
import os
import sys
import subprocess

from django.conf import settings
from django.core import exceptions
from django.core.management.base import CommandError

def get_version(end_file, relative_filename, versioner):
    """gets the file version based on the versioner provided"""
    try:
        dot = versioner.rindex('.')
    except ValueError:
        raise exceptions.ImproperlyConfigured, '%s isn\'t a versioner' % versioner
    v_module, v_classname = versioner[:dot], versioner[dot+1:]
    try:
        mod = __import__(v_module, {}, {}, [''])
    except ImportError, e:
        raise exceptions.ImproperlyConfigured, 'Error importing versioner %s: "%s"' % (v_module, e)
    try:
        v_class = getattr(mod, v_classname)
    except AttributeError:
        raise exceptions.ImproperlyConfigured, 'Versioner module "%s" does not define a "%s" class' % (v_module, v_classname)

    version = v_class()(end_file)
    dot = relative_filename.rindex('.')
    return relative_filename[:dot+1] + version + relative_filename[dot:]

def write_versions(versions, version_writer):
    """writes the versions specified in the dictionary provided"""
    try:
        dot = version_writer.rindex('.')
    except ValueError:
        raise exceptions.ImproperlyConfigured, '%s isn\'t a version writer' % version_writer
    v_module, v_classname = version_writer[:dot], version_writer[dot+1:]
    try:
        mod = __import__(v_module, {}, {}, [''])
    except ImportError, e:
        raise exceptions.ImproperlyConfigured, 'Error importing version writer %s: "%s"' % (v_module, e)
    try:
        v_class = getattr(mod, v_classname)
    except AttributeError:
        raise exceptions.ImproperlyConfigured, 'Version writer module "%s" does not define a "%s" class' % (v_module, v_classname)
    try:
        v_class(versions)
    except TypeError:
        v_class()(versions)

def static_combine(end_file, to_combine, delimiter="\n/* Begin: %s */\n", compress=False):
    """joins paths together to create a single file
    
    Usage: static_combine(my_ultimate_file, list_of_paths, [delimiter])
    
    delimiter is set to a Javascript and CSS safe comment to note where files 
    start"""
    # FIXME this fails in the face of @import directives in the CSS.
    # a) we need to move all remote @imports up to the top
    # b) we need to recursively expand all local @imports
    combo_file = open(end_file, 'w')
    to_write = ''
    for static_file in to_combine:
        if os.path.isfile(static_file):
            if delimiter:
                to_write += delimiter % os.path.split(static_file)[1]
            to_write += file(static_file).read()
    if to_write:
        combo_file.write(to_write)
        combo_file.close()
        if compress:
            try:
                command =  settings.STATIC_MANAGEMENT_COMPRESS_CMD % end_file
            except AttributeError, error:
                raise CommandError("STATIC_MANAGEMENT_COMPRESS_CMD not set")
            except TypeError, error:
                raise CommandError("No string substitution provided for the input file to be passed to the argument ('cmd %s')")
            proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
            to_write = proc.communicate()[0]
            if proc.returncode != 0:
                raise CommandError("STATIC_MANAGEMENT_COMPRESS_CMD failed to run: %s" % command)
            compressed_file = open(end_file, 'w')
            compressed_file.write(to_write)
            compressed_file.close()

########NEW FILE########
__FILENAME__ = static_combine
import os
import shutil
import re
from optparse import OptionParser, make_option

from django.core.management.base import BaseCommand
from django.conf import settings

from static_management.lib import static_combine, get_version, write_versions

try:
    CSS_ASSET_PATTERN = re.compile(settings.STATIC_MANAGEMENT_CSS_ASSET_PATTERN)
except AttributeError:
    CSS_ASSET_PATTERN = re.compile('(?P<url>url(\([\'"]?(?P<filename>[^)]+\.[a-z]{3,4})(?P<fragment>#\w+)?[\'"]?\)))')

try:
    from os.path import relpath
except ImportError:
    def relpath(path, start):
        """This only works on POSIX systems and is ripped out of Python 2.6 posixpath.py"""
        start_list = os.path.abspath(start).split('/')
        path_list = os.path.abspath(path).split('/')

        # Work out how much of the filepath is shared by start and path.
        i = len(os.path.commonprefix([start_list, path_list]))

        rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
        if not rel_list:
            return '.'
        return os.path.join(*rel_list)

class Command(BaseCommand):
    """static management commands for static_combine argument"""
    
    option_list = BaseCommand.option_list + (
        make_option("-c", "--compress", action="store_true", dest="compress", default=False, help='Runs the compression script defined in "STATIC_MANAGEMENT_COMPRESS_CMD" on the final combined files'),
        make_option("-o", "--output", action="store_true", dest="output", default=False, help='Outputs the list of filenames with version info using the "STATIC_MANAGEMENT_VERSION_OUTPUT"'),
        make_option("-w", "--write-version", action="store_true", dest="write-version", default=False, help='Produces versioned combined files in addition to non-versioned ones'),
    )
    
    def handle(self, *args, **kwargs):
        self.options = kwargs
        self.files_created = []
        self.versions = {}
        self.abs_versions = {}
        self.css_files = []
        map(self.files_created.append, self.find_assets())
        self.combine_js()
        # Do the get_versions for everything except the CSS
        self.get_versions()
        self.combine_css()
        map(self.replace_css, self.css_files)
        # Do the CSS get_versions only after having replaced all references in the CSS.
        self.get_versions(css_only=True)
        self.write_versions()
    
    def combine_js(self):
        try:
            js_files = settings.STATIC_MANAGEMENT['js']
        except AttributeError:
            print "Static JS files not provided. You must provide a set of files to combine."
            raise SystemExit(1)
        combine_files(js_files, self.options)
        map(self.files_created.append, js_files)
    
    def combine_css(self):
        try:
            css_files = settings.STATIC_MANAGEMENT['css']
        except AttributeError:
            print "Static CSS files not provided. You must provide a set of files to combine."
            raise SystemExit(1)
        combine_files(css_files, self.options)
        for file in css_files:
            self.css_files.append(file)
            self.files_created.append(file)

    def replace_css(self, filename):
        tmp = os.tmpfile()
        rel_filename = os.path.join(settings.MEDIA_ROOT, filename)
        css = open(rel_filename, mode='r')
        for line in css:
            matches = []
            for match in re.finditer(CSS_ASSET_PATTERN, line):
                try:
                    grp = match.groupdict()
                    absolute = grp['filename'].startswith('/')
                    if absolute:
                        asset_path = os.path.join(settings.MEDIA_ROOT, '.'+grp['filename'])
                    else:
                        asset_path = os.path.join(os.path.dirname(rel_filename), grp['filename'])
                    asset = relpath(asset_path, settings.MEDIA_ROOT)
                    asset_version = 'url(%s%s)' % (self.abs_versions[asset], grp.get('fragment') or '')
                    matches.append((grp['url'], asset_version))
                except KeyError:
                    print "Failed to find %s in version map. Is it an absolute path?" % asset
                    raise SystemExit(1)
            for old, new in matches:
                line = line.replace(old, new)
            tmp.write(line)
        tmp.flush()
        tmp.seek(0)
        css.close()
        css = open(rel_filename, mode='wb')
        shutil.copyfileobj(tmp, css)

    def find_assets(self):
        if settings.STATIC_MANAGEMENT_ASSET_PATHS:
            exp = re.compile(settings.STATIC_MANAGEMENT_ASSET_PATTERN)
            for path, recurse in settings.STATIC_MANAGEMENT_ASSET_PATHS:
                if recurse:
                    for root, dirs, files in os.walk(os.path.join(settings.MEDIA_ROOT, path)):
                        for filename in files:
                            if exp.match(filename):
                                yield relpath(os.path.join(root, filename), settings.MEDIA_ROOT)
                else:
                    for filename in os.listdir(os.path.join(settings.MEDIA_ROOT, path)):
                        full_filename = os.path.join(settings.MEDIA_ROOT, os.path.join(path, filename))
                        if not os.path.isdir(full_filename):
                            if exp.match(filename):
                                yield relpath(full_filename, settings.MEDIA_ROOT)

    def get_versions(self, css_only=False):
        hosts = settings.STATIC_MANAGEMENT_HOSTNAMES
        i = 0
        if css_only:
            files = self.css_files
        else:
            files = self.files_created
        for main_file in files:
            if i > len(hosts) - 1:
                i = 0
            version = get_version(os.path.join(settings.MEDIA_ROOT, main_file), main_file, settings.STATIC_MANAGEMENT_VERSIONER)
            self.versions[main_file] = version
            self.abs_versions[main_file] = hosts[i] + version
            i += 1

    def write_versions(self):
        for main_file in self.files_created:
            if self.options['write-version']:
                shutil.copy2(os.path.join(settings.MEDIA_ROOT, main_file),
                             os.path.join(settings.MEDIA_ROOT, self.versions[main_file]))
        if self.options['output']:
            write_versions(self.abs_versions, settings.STATIC_MANAGEMENT_VERSION_WRITER)

def combine_files(files, options):
    for main_file in files:
        # create file
        main_file_path = os.path.join(settings.MEDIA_ROOT, main_file)
        # go and get sub files
        to_combine = recurse_files(main_file, files[main_file], files)
        to_combine_paths = [os.path.join(settings.MEDIA_ROOT, f_name) for f_name in to_combine if os.path.exists(os.path.join(settings.MEDIA_ROOT, f_name))]
        static_combine(os.path.join(settings.MEDIA_ROOT, main_file), to_combine_paths, compress=options['compress'])

def recurse_files(name, files, top):
    """
    given following format:
    
    {
        "filename": ["file1", "file2", "file3"],
        "filename2": ["filename", "file4"]
    }
    
    name="filename"
    files=["file1", "file2", "file3"]
    top = Whole dictionary
    
    if a value on the left appears on the right, inherit those files
    """
    combine_files = []
    for to_cat in files:
        if to_cat in top:
            combine_files.extend(recurse_files(to_cat, top[to_cat], top))
        else:
            combine_files.append(to_cat)
    return combine_files

########NEW FILE########
__FILENAME__ = models
# empty models.py to register with installed_apps
########NEW FILE########
__FILENAME__ = static_asset
import os
import time
import sys

from django import template
from django.conf import settings
from static_management.lib import static_combine

register = template.Library()

@register.simple_tag
def static_asset(file_name):
    """produces the full versioned path for a static asset

    <img alt="Logo" src="{% static_asset "img/logo.png" %}>"""
    if settings.DEBUG:
        if file_name.startswith('http://'):
            return file_name
        else:
            if settings.STATIC_MANAGEMENT_MISSING_FILE_ERROR:
                path = os.path.join(settings.MEDIA_ROOT, file_name)
                if not os.path.exists(path):
                    raise template.TemplateSyntaxError, '%s does not exist' % os.path.abspath(path)
            return "%s%s?cachebust=%s" % (settings.MEDIA_URL, file_name, time.time())
    else:
        try:
            return settings.STATIC_MANAGEMENT_VERSIONS[file_name]
        except AttributeError:
            raise template.TemplateSyntaxError, "%s not in static version settings" % file_name

########NEW FILE########
__FILENAME__ = static_combo
import os
import time

from django import template
from django.conf import settings
from static_management.lib import static_combine

register = template.Library()

@register.simple_tag
def static_combo_css(file_name, media=None):
    """combines files in settings

    {% static_combo_css "css/main.css" %}"""
    # override the default if an override exists
    try:
        link_format = settings.STATIC_MANAGEMENT_CSS_LINK
    except AttributeError:
        if media:
            link_format = '<link rel="stylesheet" type="text/css" href="%%s" media="%s">\n' % media
        else:
            link_format = '<link rel="stylesheet" type="text/css" href="%s">\n'
    files = static_combo_css_urls(file_name)
    formatted_files = [link_format % filename for filename in files]
    return "\n".join(formatted_files)

@register.simple_tag
def static_combo_js(file_name):
    """combines files in settings

    {% static_combo_js "js/main.js" %}"""
    # override the default if an override exists
    try:
        script_format = settings.STATIC_MANAGEMENT_SCRIPT_SRC
    except AttributeError:
        script_format = '<script type="text/javascript" src="%s"></script>\n'
    files = static_combo_js_urls(file_name)
    formatted_files = [script_format % filename for filename in files]
    return "\n".join(formatted_files)

@register.simple_tag
def static_combo_css_urls(file_name, separator=None):
    "Wraps static_combo_urls as a template tag"
    return _static_combo_urls(file_name, separator, 'css')

@register.simple_tag
def static_combo_js_urls(file_name, separator=None):
    "Wraps static_combo_urls as a template tag"
    return _static_combo_urls(file_name, separator, 'js')

def _static_combo_urls(file_name, separator=None, key='css'):
    """Returns a list of URLs.
    If `separator` is provided, return a string separated by the argument.
    Otherwise returns a Python list of URLs"""
    files = _group_file_names_and_output(file_name, key)
    if separator:
        return separator.join(files)
    return files

def _group_file_names_and_output(parent_name, inheritance_key):
    """helper function to do most of the heavy lifting of the above template tags"""
    try:
        file_names = settings.STATIC_MANAGEMENT[inheritance_key][parent_name]
    except AttributeError:
        raise template.TemplateSyntaxError, "%s not in static combo settings" % parent_name
    output = []
    if settings.DEBUG:
        # we need to echo out each one
        media_url = settings.MEDIA_URL
        for file_name in file_names:
            file_path = os.path.join(settings.MEDIA_ROOT, file_name)
            if file_name in settings.STATIC_MANAGEMENT[inheritance_key]:
                output = output + _group_file_names_and_output(file_name, inheritance_key)
            else:
                if os.path.exists(file_path):
                    # need to append a cachebust as per static_asset
                    to_output = os.path.join(settings.MEDIA_URL, file_name)
                    if hasattr(settings, 'STATIC_MANAGEMENT_CACHEBUST') and settings.STATIC_MANAGEMENT_CACHEBUST:
                        to_output += "?cachebust=%s" % time.time()
                    output.append(to_output)
                else:
                    raise template.TemplateSyntaxError, "%s does not exist" % file_path
    else:
        try:
            parent_name = settings.STATIC_MANAGEMENT_VERSIONS[parent_name]
        except (AttributeError, KeyError):
            raise template.TemplateSyntaxError, "%s not in static version settings" % parent_name
        # return "combined" files
        output.append(parent_name)
    return output

########NEW FILE########
__FILENAME__ = versioners
import os
import hashlib

__all__ = ['SHA1Sum', 'MD5Sum', 'FileTimestamp']

class SHA1Sum(object):
    def __call__(self, filename):
        f = open(filename, mode='rb')
        try:
            return hashlib.sha1(f.read()).hexdigest()[:8]
        finally:
            f.close()

class MD5Sum(object):
    def __call__(self, filename):
        f = open(filename, mode='rb')
        try:
            return hashlib.md5(f.read()).hexdigest()[:8]
        finally:
            f.close()

class FileTimestamp(object):
    def __call__(self, filename):
        return str(int(os.stat(filename).st_mtime))

########NEW FILE########
__FILENAME__ = writers
import os
import sys

from django.conf import settings

try:
    import yaml
except ImportError:
    pass

__all__ = ['YamlWriter']

class YamlWriter(object):
    """Writes the version map to a YAML file"""
    def __call__(self, versions):
        obj = {'STATIC_MANAGEMENT_VERSIONS': versions}
        # Clobber existing YAML file
        fstream = open(settings.STATIC_MANAGEMENT_YAML_FILE, mode='w')
        try:
            yaml.dump(obj, stream=fstream)
        finally:
            fstream.close()

########NEW FILE########
