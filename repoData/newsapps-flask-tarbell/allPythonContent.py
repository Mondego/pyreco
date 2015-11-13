__FILENAME__ = app
import os
import json
import imp
import mimetypes
import xlrd
import csv
import re
import requests
import time
import sys
import traceback

from httplib import BadStatusLine
from flask import Flask, render_template, send_from_directory, Response
from jinja2 import Markup, TemplateSyntaxError
from jinja2.loaders import BaseLoader
from jinja2.utils import open_if_exists
from jinja2.exceptions import TemplateNotFound
from jinja2._compat import string_types
from pprint import pformat
from slughifi import slughifi
from string import uppercase
from werkzeug.wsgi import FileWrapper
from utils import filter_files
from clint.textui import puts, colored

from .oauth import get_drive_api

# in seconds
SPREADSHEET_CACHE_TTL = 4 

# pass template variables to files with these mimetypes
TEMPLATE_TYPES = [
    "text/html",
    "text/css",
    "application/javascript",
]

def split_template_path(template):
    """Split a path into segments and perform a sanity check.  If it detects
    '..' in the path it will raise a `TemplateNotFound` error.
    """
    pieces = []
    for piece in template.split('/'):
        if os.path.sep in piece \
           or (os.path.altsep and os.path.altsep in piece) or \
           piece == os.path.pardir:
            raise TemplateNotFound(template)
        elif piece and piece != '.':
            pieces.append(piece)
    return pieces

class TarbellFileSystemLoader(BaseLoader):
    def __init__(self, searchpath, encoding='utf-8'):
        if isinstance(searchpath, string_types):
            searchpath = [searchpath]
        self.searchpath = list(searchpath)
        self.encoding = encoding

    def get_source(self, environment, template):
        pieces = split_template_path(template)
        for searchpath in self.searchpath:
            filename = os.path.join(searchpath, *pieces)
            f = open_if_exists(filename)
            if f is None:
                continue
            try:
                contents = f.read().decode(self.encoding)
            finally:
                f.close()

            mtime = os.path.getmtime(filename)

            def uptodate():
                try:
                    return os.path.getmtime(filename) == mtime
                except OSError:
                    return False
            return contents, filename, uptodate
        raise TemplateNotFound(template)

    def list_templates(self):
        found = set()
        for searchpath in self.searchpath:
            for dirpath, dirnames, filenames in filter_files(searchpath):
                for filename in filenames:
                    template = os.path.join(dirpath, filename) \
                        [len(searchpath):].strip(os.path.sep) \
                                          .replace(os.path.sep, '/')
                    if template[:2] == './':
                        template = template[2:]
                    if template not in found:
                        found.add(template)
        return sorted(found)


def silent_none(value):
    if value is None:
        return ''
    return value


def pprint_lines(value):
    pformatted = pformat(value, width=1, indent=4)
    formatted = "{0}\n {1}\n{2}".format(
        pformatted[0],
        pformatted[1:-1],
        pformatted[-1]
    )
    return Markup(formatted)


def process_xlsx(content):
    """Turn Excel file contents into Tarbell worksheet data"""
    data = {}
    workbook = xlrd.open_workbook(file_contents=content)
    worksheets = workbook.sheet_names()
    for worksheet_name in worksheets:
        worksheet = workbook.sheet_by_name(worksheet_name)
        worksheet.name = slughifi(worksheet.name)
        headers = make_headers(worksheet)
        worksheet_data = make_worksheet_data(headers, worksheet)
        data[worksheet.name] = worksheet_data
    return data


def copy_global_values(data):
    """Copy values worksheet into global namespace."""
    for k, v in data['values'].items():
        if not data.get(k):
            data[k] = v
        else:
            puts("There is both a worksheet and a "
                 "value named '{0}'. The worksheet data "
                 "will be preserved.".format(k))
    data.pop("values", None)
    return data


def make_headers(worksheet):
    """Make headers"""
    headers = {}
    cell_idx = 0
    while cell_idx < worksheet.ncols:
        cell_type = worksheet.cell_type(0, cell_idx)
        if cell_type == 1:
            header = slughifi(worksheet.cell_value(0, cell_idx))
            if not header.startswith("_"):
                headers[cell_idx] = header
        cell_idx += 1
    return headers


def make_worksheet_data(headers, worksheet):
    # Make data
    data = []
    row_idx = 1
    while row_idx < worksheet.nrows:
        cell_idx = 0
        row_dict = {}
        while cell_idx < worksheet.ncols:
            cell_type = worksheet.cell_type(row_idx, cell_idx)
            if cell_type > 0 and cell_type < 5:
                cell_value = worksheet.cell_value(row_idx, cell_idx)
                try:
                    row_dict[headers[cell_idx]] = cell_value
                except KeyError:
                    try:
                        column = uppercase[cell_idx]
                    except IndexError:
                        column = cell_idx
                        puts("There is no header for cell with value '{0}' in column '{1}' of '{2}'" .format(
                            cell_value, column, worksheet.name
                        ))
            cell_idx += 1
        data.append(row_dict)
        row_idx += 1

    # Magic key handling
    if 'key' in headers.values():
        keyed_data = {}
        for row in data:
            if 'key' in row.keys():
                key = slughifi(row['key'])
                if keyed_data.get(key):
                    puts("There is already a key named '{0}' with value "
                           "'{1}' in '{2}'. It is being overwritten with "
                           "value '{3}'.".format(key,
                                   keyed_data.get(key),
                                   worksheet.name,
                                   row))

                # Magic values worksheet
                if worksheet.name == "values":
                    value = row.get('value')
                    if value:
                        keyed_data[key] = value
                else:
                    keyed_data[key] = row

        data = keyed_data

    return data


class TarbellSite:
    def __init__(self, path, client_secrets_path=None, quiet=False):
        self.app = Flask(__name__)

        self.quiet = quiet

        self.app.jinja_env.finalize = silent_none  # Don't print "None"
        self.app.debug = True  # Always debug

        self.path = path
        self.project, self.base = self.load_project(path)

        self.data = {}
        self.expires = 0

        self.app.add_url_rule('/', view_func=self.preview)
        self.app.add_url_rule('/<path:path>', view_func=self.preview)
        self.app.add_template_filter(slughifi, 'slugify')
        self.app.add_template_filter(pprint_lines, 'pprint_lines')

    def load_project(self, path):
        base = None
        base_dir = os.path.join(path, "_base/")

        # Get the base as register it as a blueprint
        if os.path.exists(os.path.join(base_dir, "base.py")):
            filename, pathname, description = imp.find_module('base', [base_dir])
            base = imp.load_module('base', filename, pathname, description)
            self.app.register_blueprint(base.blueprint)
        else:
            puts("No _base/base.py file found")

        filename, pathname, description = imp.find_module('tarbell_config', [path])
        project = imp.load_module('project', filename, pathname, description)

        try:
            self.key = project.SPREADSHEET_KEY
            self.client = get_drive_api(self.path)
        except AttributeError:
            self.key = None
            self.client = None

        try:
            project.CREATE_JSON
        except AttributeError:
            project.CREATE_JSON = False

        try:
            project.DEFAULT_CONTEXT
        except AttributeError:
            project.DEFAULT_CONTEXT = {}

        try:
            project.EXCLUDES
        except AttributeError:
            project.EXCLUDES = []

        try:
            self.app.register_blueprint(project.blueprint)
        except AttributeError:
            pass

        # Set up template loaders
        template_dirs = [path]
        if os.path.isdir(base_dir):
            template_dirs.append(base_dir)

        self.app.jinja_loader = TarbellFileSystemLoader(template_dirs)

        return project, base

    def preview(self, path=None, extra_context=None, publish=False):
        """ Preview a project path """
        if path is None:
            path = 'index.html'

        ## Serve JSON
        if self.project.CREATE_JSON and path == 'data.json':
            context = self.get_context(publish)
            return Response(json.dumps(context), mimetype="application/json")

        ## Detect files
        filepath = None
        for root, dirs, files in filter_files(self.path):
            # Does it exist under _base?
            basepath = os.path.join(root, "_base", path)
            try:
                with open(basepath):
                    mimetype, encoding = mimetypes.guess_type(basepath)
                    filepath = basepath
            except IOError:
                pass

            # Does it exist under regular path?
            fullpath = os.path.join(root, path)
            try:
                with open(fullpath):
                    mimetype, encoding = mimetypes.guess_type(fullpath)
                    filepath = fullpath
            except IOError:
                pass

        if filepath and mimetype and mimetype in TEMPLATE_TYPES:
            context = self.get_context(publish)
            # Mix in defaults
            context.update({
                "PROJECT_PATH": self.path,
                "PREVIEW_SERVER": not publish,
                "ROOT_URL": "127.0.0.1:5000",
                "PATH": path,
                "SPREADSHEET_KEY": self.key,
            })
            if extra_context:
                context.update(extra_context)
            try:
                rendered = render_template(path, **context)
                return Response(rendered, mimetype=mimetype)
            except TemplateSyntaxError:
                ex_type, ex, tb = sys.exc_info()
                stack = traceback.extract_tb(tb)
                error = stack[-1]
                puts("\n{0} can't be parsed by Jinja, serving static".format(colored.red(filepath)))
                puts("\nLine {0}:".format(colored.green(error[1])))
                puts("  {0}".format(colored.yellow(error[3])))
                puts("\nFull traceback:")
                traceback.print_tb(tb)
                puts("")
                del tb

        if filepath:
            dir, filename = os.path.split(filepath)
            return send_from_directory(dir, filename)

        return Response(status=404)

    def get_context(self, publish=False):
        """
        Use optional CONTEXT_SOURCE_FILE setting to determine data source.
        Return the parsed data.

        Can be an http|https url or local file. Supports csv and excel files.
        """
        context = self.project.DEFAULT_CONTEXT
        try:
            file = self.project.CONTEXT_SOURCE_FILE
            # CSV
            if re.search(r'(csv|CSV)$', file):
                context.update(self.get_context_from_csv())
            # Excel
            if re.search(r'(xlsx|XLSX|xls|XLS)$', file):
                pass
        except AttributeError:
            context.update(self.get_context_from_gdoc())

        return context

    def get_context_from_csv(self):
        """
        Open CONTEXT_SOURCE_FILE, parse and return a context
        """
        if re.search('^(http|https)://', self.project.CONTEXT_SOURCE_FILE):
            data = requests.get(self.project.CONTEXT_SOURCE_FILE)
            reader = csv.reader(
                data.iter_lines(), delimiter=',', quotechar='"')
            ret = {rows[0]: rows[1] for rows in reader}
        else:
            try:
                with open(self.project.CONTEXT_SOURCE_FILE) as csvfile:
                    reader = csv.reader(csvfile, delimiter=',', quotechar='"')
                    ret = {rows[0]: rows[1] for rows in reader}
            except IOError:
                file = "%s/%s" % (
                    os.path.abspath(self.path),
                    self.project.CONTEXT_SOURCE_FILE)
                with open(file) as csvfile:
                    reader = csv.reader(csvfile, delimiter=',', quotechar='"')
                    ret = {rows[0]: rows[1] for rows in reader}
        ret.update({
            "CONTEXT_SOURCE_FILE": self.project.CONTEXT_SOURCE_FILE,
        })
        return ret

    def get_context_from_gdoc(self):
        """Wrap getting context in a simple caching mechanism."""
        try:
            start = int(time.time())
            if not self.data or start > self.expires:
                self.data = self._get_context_from_gdoc(self.project.SPREADSHEET_KEY)
                end = int(time.time())
                self.expires = end + SPREADSHEET_CACHE_TTL
            return self.data
        except AttributeError:
            return {}

    def _get_context_from_gdoc(self, key):
        """Create a Jinja2 context from a Google spreadsheet."""
        try:
            content = self.export_xlsx(key)
            data = process_xlsx(content)
            if 'values' in data:
                data = copy_global_values(data)
            return data
        except BadStatusLine:
            # Stale connection, reset API and data
            puts("Connection reset, reloading drive API")
            self.client = get_drive_api(self.path)
            self.data = {}
            return self._get_context_from_gdoc(key)

    def export_xlsx(self, key):
        """Download xlsx version of spreadsheet"""
        spreadsheet_file = self.client.files().get(fileId=key).execute()
        links = spreadsheet_file.get('exportLinks')
        downloadurl = links.get('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp, content = self.client._http.request(downloadurl)
        return content

    def generate_static_site(self, output_root, extra_context):
        base_dir = os.path.join(self.path, "_base/")

        for root, dirs, files in filter_files(base_dir):
            for filename in files:
                self._copy_file(root.replace("_base/", ""), filename, output_root, extra_context)

        for root, dirs, files in filter_files(self.path):
            for filename in files:
                self._copy_file(root, filename, output_root, extra_context)

    def _copy_file(self, root, filename, output_root, extra_context=None):
        # Strip out full filesystem paths
        rel_path = os.path.join(root.replace(self.path, ""), filename)
        if rel_path.startswith("/"):
            rel_path = rel_path[1:]
        output_path = os.path.join(output_root, rel_path)
        output_dir = os.path.dirname(output_path)

        if not self.quiet:
            puts("Writing {0}".format(output_path))
        with self.app.test_request_context():
            preview = self.preview(rel_path, extra_context=extra_context, publish=True)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            with open(output_path, "wb") as f:
                if isinstance(preview.response, FileWrapper):
                    f.write(preview.response.file.read())
                else:
                    f.write(preview.data)

########NEW FILE########
__FILENAME__ = cli
# -*- coding: utf-8 -*-

"""
tarbell.cli
~~~~~~~~~

This module provides the CLI interface to tarbell.
"""

import os
import glob
import sh
import sys
import imp
import jinja2
import codecs
import tempfile
import shutil
import pkg_resources

from subprocess import call
from clint import args
from clint.textui import colored, puts

from apiclient import errors
from apiclient.http import MediaFileUpload as _MediaFileUpload

from tarbell import __VERSION__ as VERSION

from .app import pprint_lines, process_xlsx, copy_global_values
from .oauth import get_drive_api
from .contextmanagers import ensure_settings, ensure_project
from .configure import tarbell_configure
from .utils import list_get, black, split_sentences, show_error, get_config_from_args
from .s3 import S3Url, S3Sync


# --------
# Dispatch
# --------
def main():
    """Primary Tarbell command dispatch."""
    command = Command.lookup(args.get(0))

    if len(args) == 0 or args.contains(('-h', '--help', 'help')):
        display_info(args)
        sys.exit(1)

    elif args.contains(('-v', '--version')):
        display_version()
        sys.exit(1)

    elif command:
        arg = args.get(0)
        args.remove(arg)
        command.__call__(command, args)
        sys.exit()

    else:
        show_error(colored.red('Error! Unknown command `{0}`.\n'
                               .format(args.get(0))))
        display_info(args)
        sys.exit(1)


def display_info(args):
    """Displays Tarbell info."""
    puts('\n{0}\n'.format(
        black('Tarbell: Simple web publishing'),
    ))

    puts('Usage: {0}\n'.format(colored.cyan('tarbell <command>')))
    puts('Commands:\n')
    for command in Command.all_commands():
        usage = command.usage or command.name
        help = command.help or ''
        puts('{0:50} {1}'.format(
                colored.green(usage),
                split_sentences(help)))

    config = get_config_from_args(args)
    if not os.path.isfile(config):
        puts('\n---\n\n{0}: {1}'.format(
            colored.red("Warning"),
            "No Tarbell configuration found. Run:"
        ))
        puts('\n    {0}'.format(
            colored.green("tarbell configure")
        ))
        puts('\n{0}'.format(
            "to configure Tarbell."
        ))

    puts('\n{0}'.format(
        black(u'Crafted by the Chicago Tribune News Applications team\n')
    ))


def display_version():
    """Displays Tarbell version/release."""
    puts('You are using Tarbell v{0}'.format(
        colored.green(VERSION)
    ))


def tarbell_generate(command, args, skip_args=False, extra_context=None, quiet=False):
    """Generate static files."""

    output_root = None
    with ensure_settings(command, args) as settings, ensure_project(command, args) as site:
        if not skip_args:
            output_root = list_get(args, 0, False)
        if quiet:
            site.quiet = True
        if not output_root:
            output_root = tempfile.mkdtemp(prefix="{0}-".format(site.project.__name__))

        if args.contains('--context'):
            site.project.CONTEXT_SOURCE_FILE = args.value_after('--context')

        site.generate_static_site(output_root, extra_context)
        if not quiet:
            puts("\nCreated site in {0}".format(output_root))
        return output_root

def git_interact(line, stdin):
    print line
    print stdin.put('foo')


def tarbell_install(command, args):
    """Install a project."""
    with ensure_settings(command, args) as settings:
        project_url = args.get(0)
        puts("\n- Getting project information for {0}".format(project_url))
        project_name = project_url.split("/").pop()
        message = None
        error = None

        # Create a tempdir and clone
        tempdir = tempfile.mkdtemp()
        try:
            testgit = sh.git.bake(_cwd=tempdir, _tty_out=False)
            puts(testgit.clone(project_url, '.', *['--depth=1', '--bare']))
            config = testgit.show("HEAD:tarbell_config.py")
            puts("\n- Found tarbell_config.py")
            path = _get_path(project_name, settings, mkdir=True)
            git = sh.git.bake(_cwd=path)
            puts(git.clone(project_url, '.'))
            puts(git.submodule.update(*['--init', '--recursive']))
            submodule = sh.git.bake(_cwd=os.path.join(path, '_base'))
            puts(submodule.fetch())
            puts(submodule.checkout(VERSION))
            message = "\n- Done installing project in {0}".format(colored.yellow(path))
        except sh.ErrorReturnCode_128:
            error = "Not a Tarbell project!"
        finally:
            _delete_dir(tempdir)
            if message:
                puts(message)
            if error:
                show_error(error)

def tarbell_install_template(command, args):
    """Install a project template."""
    with ensure_settings(command, args) as settings:
        template_url = args.get(0)

        matches = [template for template in settings.config["project_templates"] if template["url"] == template_url]
        if matches:
            puts("\n{0} already exists. Nothing more to do.\n".format(
                colored.yellow(template_url)
            ))
            sys.exit()

        puts("\nInstalling {0}".format(colored.cyan(template_url))) 
        tempdir = tempfile.mkdtemp()
        puts("\n- Cloning repo to {0}".format(colored.green(tempdir))) 
        tempdir = tempfile.mkdtemp()
        git = sh.git.bake(_cwd=tempdir)
        puts(git.clone(template_url, '.'))
        puts(git.fetch())
        puts(git.checkout(VERSION))
        filename, pathname, description = imp.find_module('base', [tempdir])
        base = imp.load_module('base', filename, pathname, description)
        puts("\n- Found _base/base.py")
        try:
            name = base.NAME
            puts("\n- Name specified in base.py: {0}".format(colored.yellow(name)))
        except AttributeError:
            name = template_url.split("/")[-1]
            puts("\n- No name specified in base.py, using '{0}'".format(colored.yellow(name)))

        settings.config["project_templates"].append({"name": name, "url": template_url})
        settings.save()

        _delete_dir(tempdir)

        puts("\n+ Added new project template: {0}".format(colored.yellow(name)))


def tarbell_list(command, args):
    """List tarbell projects."""
    with ensure_settings(command, args) as settings:
        projects_path = settings.config.get("projects_path")
        if not projects_path:
            show_error("{0} does not exist".format(projects_path))
            sys.exit()

        puts("\nListing projects in {0}\n".format(
            colored.yellow(projects_path)
        ))

        for directory in os.listdir(projects_path):
            project_path = os.path.join(projects_path, directory)
            try:
                filename, pathname, description = imp.find_module('tarbell_config', [project_path])
                config = imp.load_module(directory, filename, pathname, description)
                puts("{0:30} {1}".format(
                    colored.red(config.NAME),
                    colored.cyan(config.TITLE)
                ))

                puts("{0}".format(colored.yellow(project_path))),
                puts("")

            except ImportError:
                pass

        puts("Use {0} to switch to a project\n".format(
            colored.green("tarbell switch <projectname>")
            ))


def tarbell_list_templates(command, args):
    with ensure_settings(command, args) as settings:
        puts("\nAvailable project templates\n")
        _list_templates(settings)
        puts("")


def tarbell_publish(command, args):
    """Publish a site by calling s3cmd"""
    with ensure_settings(command, args) as settings, ensure_project(command, args) as site:
        bucket_name = list_get(args, 0, "staging")

        try:
            bucket_url = S3Url(site.project.S3_BUCKETS[bucket_name])
        except KeyError:
            show_error(
                "\nThere's no bucket configuration called '{0}' in "
                "tarbell_config.py.".format(colored.yellow(bucket_name)))
            sys.exit(1)

        extra_context = {
            "ROOT_URL": bucket_url,
            "S3_BUCKET": bucket_url.root,
            "BUCKET_NAME": bucket_name,
        }

        tempdir = "{0}/".format(tarbell_generate(command,
            args, extra_context=extra_context, skip_args=True, quiet=True))
        try:
            puts("\nDeploying {0} to {1} ({2})\n".format(
                colored.yellow(site.project.TITLE),
                colored.red(bucket_name),
                colored.green(bucket_url)
            ))
            # Get creds
            kwargs = settings.config['s3_credentials'].get(bucket_url.root)
            if not kwargs:
                kwargs = {
                    'access_key_id': settings.config['default_s3_access_key_id'],
                    'secret_access_key': settings.config['default_s3_secret_access_key'],
                }
                puts("Using default bucket credentials")
            else:
                puts("Using custom bucket configuration for {0}".format(bucket_url.root))

            kwargs['excludes'] = site.project.EXCLUDES
            s3 = S3Sync(tempdir, bucket_url, **kwargs)
            s3.deploy_to_s3()
            puts("\nIf you have website hosting enabled, you can see your project at:")
            puts(colored.green("http://{0}\n".format(bucket_url)))
        except KeyboardInterrupt:
            show_error("ctrl-c pressed, bailing out!")
        except KeyError:
            show_error("Credentials for bucket {0} not configured -- run {1} or add credentials to {2}".format(colored.red(bucket_url), colored.yellow("tarbell configure s3"), colored.yellow("~/.tarbell/settings.yaml")))
        finally:
            _delete_dir(tempdir)


def _delete_dir(dir):
    """Delete tempdir"""
    try:
        shutil.rmtree(dir)  # delete directory
    except OSError as exc:
        if exc.errno != 2:  # code 2 - no such file or directory
            raise  # re-raise exception
    except UnboundLocalError:
        pass


def tarbell_newproject(command, args):
    """Create new Tarbell project."""
    with ensure_settings(command, args) as settings:

        # Create directory or bail
        name = _get_project_name(args)
        puts("Creating {0}".format(colored.cyan(name)))
        path = _get_path(name, settings)
        title = _get_project_title()
        template = _get_template(settings)

        # Init repo
        git = sh.git.bake(_cwd=path)
        puts(git.init())

        # Create submodule
        puts(git.submodule.add(template['url'], '_base'))
        puts(git.submodule.update(*['--init']))

        # Get submodule branches, switch to current version
        submodule = sh.git.bake(_cwd=os.path.join(path, '_base'))
        puts(submodule.fetch())
        puts(submodule.checkout(VERSION))

        # Create spreadsheet
        key = _create_spreadsheet(name, title, path, settings)

        # Create config file
        _copy_config_template(name, title, template, path, key, settings)

        # Copy html files
        puts(colored.green("\nCopying html files..."))
        files = glob.iglob(os.path.join(path, "_base", "*.html"))
        for file in files:
            if os.path.isfile(file):
                dir, filename = os.path.split(file)
                if not filename.startswith("_") and not filename.startswith("."):
                    puts("Copying {0} to {1}".format(filename, path))
                    shutil.copy2(file, path)
        ignore = os.path.join(path, "_base", ".gitignore")
        if os.path.isfile(ignore):
            shutil.copy2(ignore, path)

        # Commit
        puts(colored.green("\nInitial commit"))
        puts(git.add('.'))
        puts(git.commit(m='Created {0} from {1}'.format(name, template['url'])))

        # Set up remote url
        remote_url = raw_input("\nWhat is the URL of your project repository? (e.g. git@github.com:myaccount/myproject.git, leave blank to skip) ")
        if remote_url:
            puts("\nCreating new remote 'origin' to track {0}.".format(colored.yellow(remote_url)))
            git.remote.add(*["origin", remote_url])
            puts("\n{0}: Don't forget! It's up to you to create this remote and push to it.".format(colored.cyan("Warning")))
        else:
            puts("\n- Not setting up remote repository. Use your own version control!")


        # Messages
        puts("\nAll done! To preview your new project, type:\n")
        puts("{0} {1}".format(colored.green("tarbell switch"), colored.green(name)))
        puts("\nor\n")
        puts("{0}".format(colored.green("cd %s" % path)))
        puts("{0}".format(colored.green("tarbell serve\n")))

        puts("\nYou got this!\n")


def _get_project_name(args):
        """Get project name"""
        name = args.get(0)
        puts("")
        while not name:
            name = raw_input("What is the project's short directory name? (e.g. my_project) ")
        return name


def _get_project_title():
        """Get project title"""
        title = None
        puts("")
        while not title:
            title = raw_input("What is the project's full title? (e.g. My awesome project) ")

        return title


def _get_path(name, settings, mkdir=True):
    """Generate a project path."""
    default_projects_path = settings.config.get("projects_path")
    path = None

    if default_projects_path:
        path = raw_input("\nWhere would you like to create this project? [{0}/{1}] ".format(default_projects_path, name))
        if not path:
            path = os.path.join(default_projects_path, name)
    else:
        while not path:
            path = raw_input("\nWhere would you like to create this project? (e.g. ~/tarbell/) ")

    path = os.path.expanduser(path)

    if mkdir:
        try:
            os.mkdir(path)
        except OSError, e:
            if e.errno == 17:
                show_error("ABORTING: Directory {0} already exists.".format(path))
            else:
                show_error("ABORTING: OSError {0}".format(e))
            sys.exit()

    return path


def _get_template(settings):
    """Prompt user to pick template from a list."""
    puts("\nPick a template\n")
    template = None
    while not template:
        _list_templates(settings)
        index = raw_input("\nWhich template would you like to use? [1] ")
        if not index:
            index = "1"
        try:
            index = int(index) - 1
            return settings.config["project_templates"][index]
        except:
            puts("\"{0}\" isn't a valid option!".format(colored.red("{0}".format(index))))
            pass


def _list_templates(settings):
    """List templates from settings."""
    for idx, option in enumerate(settings.config.get("project_templates"), start=1):
        puts("  {0:5} {1:36}\n      {2}\n".format(
            colored.yellow("[{0}]".format(idx)),
            colored.cyan(option.get("name")),
            option.get("url")
        ))


def _create_spreadsheet(name, title, path, settings):
    """Create Google spreadsheet"""
    if not settings.client_secrets:
        return None

    create = raw_input("{0} found. Would you like to create a Google spreadsheet? [Y/n] ".format(
        colored.cyan("client_secrets")
    ))
    if create and not create.lower() == "y":
        return puts("Not creating spreadsheet...")

    email_message = (
        "What Google account should have access to this "
        "this spreadsheet? (Use a full email address, such as "
        "your.name@gmail.com or the Google account equivalent.) ") 

    if settings.config.get("google_account"):
        email = raw_input("\n{0}(Default: {1}) ".format(email_message,
                                             settings.config.get("google_account")
                                            ))
        if not email:
            email = settings.config.get("google_account")
    else:
        email = None
        while not email:
            email = raw_input(email_message)

    try:
        media_body = _MediaFileUpload(os.path.join(path, '_base/_spreadsheet.xlsx'),
                                      mimetype='application/vnd.ms-excel')
    except IOError:
        show_error("_base/_spreadsheet.xlsx doesn't exist!")
        return None

    service = get_drive_api(settings.path)
    body = {
        'title': '{0} (Tarbell)'.format(title),
        'description': '{0} ({1})'.format(title, name),
        'mimeType': 'application/vnd.ms-excel',
    }
    try:
        newfile = service.files()\
            .insert(body=body, media_body=media_body, convert=True).execute()
        _add_user_to_file(newfile['id'], service, user_email=email)
        puts("\n{0}! View the spreadsheet at {1}".format(
            colored.green("Success"),
            colored.yellow("https://docs.google.com/spreadsheet/ccc?key={0}"
                           .format(newfile['id']))
            ))
        return newfile['id']
    except errors.HttpError, error:
        show_error('An error occurred creating spreadsheet: {0}'.format(error))
        return None


def _add_user_to_file(file_id, service, user_email,
                      perm_type='user', role='reader'):
    """
    Grants the given set of permissions for a given file_id. service is an
    already-credentialed Google Drive service instance.
    """
    new_permission = {
        'value': user_email,
        'type': perm_type,
        'role': role
    }
    try:
        service.permissions()\
            .insert(fileId=file_id, body=new_permission)\
            .execute()
    except errors.HttpError, error:
        print 'An error occurred: %s' % error


def _copy_config_template(name, title, template, path, key, settings):
        """Get and render tarbell_config.py.template from base"""
        puts("\nCopying configuration file")
        context = settings.config
        context.update({
            "default_context": {
                "name": name,
                "title": title,
            },
            "name": name,
            "title": title,
            "template_repo_url": template.get('url'),
            "key": key,
        })

        # @TODO refactor this a bit
        if not key:
            spreadsheet_path = os.path.join(path, '_base/', '_spreadsheet.xlsx')
            with open(spreadsheet_path, "rb") as f:
                try:
                    puts("Copying _base/_spreadsheet.xlsx to tarbell_config.py's DEFAULT_CONTEXT") 
                    data = process_xlsx(f.read())
                    if 'values' in data:
                        data = copy_global_values(data)
                    context["default_context"].update(data)
                except IOError:
                    show_error("No spreadsheet available")

        s3_buckets = settings.config.get("s3_buckets")
        if s3_buckets:
            puts("")
            for bucket, bucket_conf in s3_buckets.items():
                puts("Configuring {0} bucket at {1}\n".format(
                    colored.green(bucket),
                    colored.yellow("{0}/{1}".format(bucket_conf['uri'], name))
                ))

        puts("\n- Creating {0} project configuration file".format(
            colored.cyan("tarbell_config.py")
        ))
        template_dir = os.path.dirname(pkg_resources.resource_filename("tarbell", "templates/tarbell_config.py.template"))
        loader = jinja2.FileSystemLoader(template_dir)
        env = jinja2.Environment(loader=loader)
        env.filters["pprint_lines"] = pprint_lines  # For dumping context
        content = env.get_template('tarbell_config.py.template').render(context)
        codecs.open(os.path.join(path, "tarbell_config.py"), "w", encoding="utf-8").write(content)
        puts("\n- Done copying configuration file")


def tarbell_serve(command, args):
    """Serve the current Tarbell project."""
    with ensure_project(command, args) as site:
        address = list_get(args, 0, "").split(":")
        ip = list_get(address, 0, '127.0.0.1')
        port = list_get(address, 1, '5000')
        puts("Press {0} to stop the server".format(colored.red("ctrl-c")))
        site.app.run(ip, port=int(port))


def tarbell_switch(command, args):
    """Switch to a project"""
    with ensure_settings(command, args) as settings:
        projects_path = settings.config.get("projects_path")
        if not projects_path:
            show_error("{0} does not exist".format(projects_path))
            sys.exit()
        project = args.get(0)
        args.remove(project)
        project_path = os.path.join(projects_path, project)
        if os.path.isdir(project_path):
            os.chdir(project_path)
            puts("\nSwitching to {0}".format(colored.red(project)))
            puts("Edit this project's templates at {0}".format(colored.yellow(project_path)))
            puts("Running preview server...")
            tarbell_serve(command, args)
        else:
            show_error("{0} isn't a tarbell project".format(project_path))


def tarbell_update(command, args):
    """Update the current tarbell project."""
    with ensure_settings(command, args) as settings, ensure_project(command, args) as site:
        puts("Updating to latest base template\n")
        git = sh.git.bake(_cwd=os.path.join(site.path, '_base'))
        git.fetch()
        puts(colored.yellow("Checking out {0}".format(VERSION)))
        puts(git.checkout(VERSION))
        puts(colored.yellow("Stashing local changes"))
        puts(git.stash())
        puts(colored.yellow("Pull latest changes"))
        puts(git.pull('origin', VERSION))



def tarbell_unpublish(command, args):
    with ensure_settings(command, args) as settings, ensure_project(command, args) as site:
        """Delete a project."""
        show_error("Not implemented!")


class Command(object):
    COMMANDS = {}
    SHORT_MAP = {}

    @classmethod
    def register(klass, command):
        klass.COMMANDS[command.name] = command
        if command.short:
            for short in command.short:
                klass.SHORT_MAP[short] = command

    @classmethod
    def lookup(klass, name):
        if name in klass.SHORT_MAP:
            return klass.SHORT_MAP[name]
        if name in klass.COMMANDS:
            return klass.COMMANDS[name]
        else:
            return None

    @classmethod
    def all_commands(klass):
        return sorted(klass.COMMANDS.values(),
                      key=lambda cmd: cmd.name)

    def __init__(self, name=None, short=None, fn=None, usage=None, help=None):
        self.name = name
        self.short = short
        self.fn = fn
        self.usage = usage
        self.help = help

    def __call__(self, *args, **kw_args):
        return self.fn(*args, **kw_args)


def def_cmd(name=None, short=None, fn=None, usage=None, help=None):
    """Define a command."""
    command = Command(name=name, short=short, fn=fn, usage=usage, help=help)
    Command.register(command)


# Note that the tarbell_configure function is imported from contextmanagers.py
def_cmd(
    name='configure',
    fn=tarbell_configure,
    usage='configure <subcommand (optional)>',
    help="Configure Tarbell. Subcommand can be one of 'drive', 's3', 'path', or 'templates'.")


def_cmd(
    name='generate',
    fn=tarbell_generate,
    usage='generate <output dir (optional)>',
    help=('Generate static files for the current project. If no output '
          'directory is specified, create a temporary directory'))


def_cmd(
    name='install',
    fn=tarbell_install,
    usage='install <url to project repository>',
    help='Install a pre-existing project')


def_cmd(
    name='install-template',
    fn=tarbell_install_template,
    usage='install-template <url to template>',
    help='Install a project template')


def_cmd(
    name='list',
    fn=tarbell_list,
    usage='list',
    help='List all projects.')

def_cmd(
    name='list-templates',
    fn=tarbell_list_templates,
    usage='list-templates',
    help='List installed project templates')

def_cmd(
    name='publish',
    fn=tarbell_publish,
    usage='publish <target (default: staging)>',
    help='Publish the current project to <target>.')


def_cmd(
    name='newproject',
    fn=tarbell_newproject,
    usage='newproject <project>',
    help='Create a new project named <project>')


def_cmd(
    name='serve',
    fn=tarbell_serve,
    usage='serve <address (optional)>',
    help=('Run a preview server (typically handled by `switch`). '
          'Supply an optional address for the preview server such as '
          '`192.168.56.1:8080`'))


def_cmd(
    name='switch',
    fn=tarbell_switch,
    usage='switch <project> <address (optional)>',
    help=('Switch to the project named <project> and start a preview server. '
          'Supply an optional address for the preview server such as '
          '`192.168.56.1:8080`'))


def_cmd(
    name='update',
    fn=tarbell_update,
    usage='update',
    help='Update base template in current project.')


def_cmd(
    name='unpublish',
    fn=tarbell_unpublish,
    usage='unpublish <target (default: staging)>',
    help='Remove the current project from <target>.')

########NEW FILE########
__FILENAME__ = configure
# -*- coding: utf-8 -*-

"""
tarbell.configure
~~~~~~~~~~~~~~~~~

This module provides the Tarbell configure command.
"""

import os
import sys
import yaml
import shutil

from subprocess import call
from datetime import datetime
from clint.textui import colored, puts

from .settings import Settings
from .oauth import get_drive_api
from .utils import list_get, get_config_from_args, show_error

try:
    import readline
except ImportError:
    pass

def tarbell_configure(command, args):
    """Tarbell configuration routine"""
    puts("Configuring Tarbell. Press ctrl-c to bail out!")

    # Check if there's settings configured
    path = get_config_from_args(args)
    prompt = True
    if len(args):
        prompt = False

    settings = _get_or_create_config(path)

    if prompt or "drive" in args:
        settings.update(_setup_google_spreadsheets(settings, path, prompt))
    if prompt or "s3" in args:
        settings.update(_setup_s3(settings, path, prompt))
    if prompt or "path" in args:
        settings.update(_setup_tarbell_project_path(settings, path, prompt))
    if prompt or "templates" in args:
        settings.update(_setup_default_templates(settings, path, prompt))

    with open(path, 'w') as f:
        puts("\nWriting {0}".format(colored.green(path)))
        yaml.dump(settings, f, default_flow_style=False)

    if all:
        puts("\n- Done configuring Tarbell. Type `{0}` for help.\n"
             .format(colored.green("tarbell")))

    return Settings(path)


def _get_or_create_config(path, prompt=True):
    """Get or create a Tarbell configuration directory."""
    dirname = os.path.dirname(path)
    filename = os.path.basename(path)

    try:
        os.makedirs(dirname)
    except OSError:
        pass

    if os.path.isfile(path):
        puts("{0} already exists, backing up".format(colored.green(path)))
        _backup(dirname, filename)

    with open(path, 'w+r') as f:
        settings = yaml.load(f)
        if settings and settings.get('s3_buckets') and not settings.get('default_s3_buckets'):
            puts("- Automatically updating default bucket configuration from `s3_buckets` to `default_s3_buckets`")
            settings['default_s3_buckets'] = settings['s3_buckets']
            del settings['s3_buckets']

    return settings or {}


def _setup_google_spreadsheets(settings, path, prompt=True):
    """Set up a Google spreadsheet"""
    if prompt:
        use = raw_input("\nWould you like to use Google spreadsheets [Y/n]? ")
        if use.lower() != "y" and use != "":
            return settings

    dirname = os.path.dirname(path)

    secrets = os.path.join(dirname, 'client_secrets.json')

    write_secrets = True
    if os.path.isfile(secrets):
        write_secrets_input = raw_input("client_secrets.json already exists. Would you like to overwrite it? [y/N] ")
        if not write_secrets_input.lower().startswith('y'):
            write_secrets = False

    if write_secrets:
        puts(("\nLogin in to Google and go to {0} to create an app and generate the "
              "\n{1} authentication file. You should create credentials for an `installed app`. See "
              "\n{2} for more information."
              .format(colored.red("https://code.google.com/apis/console/"),
                      colored.yellow("client_secrets.json"),
                      colored.red("http://tarbell.readthedocs.com/#correctlink")
                     )
            ))

        secrets_path = raw_input(("\nWhere is your client secrets file? "
                                  "[~/Downloads/client_secrets.json] "
                                ))

        if secrets_path == "":
            secrets_path = os.path.join("~", "Downloads/client_secrets.json")

        secrets_path = os.path.expanduser(secrets_path)

        puts("\nCopying {0} to {1}\n"
             .format(colored.green(secrets_path),
                     colored.green(dirname))
        )

        _backup(dirname, "client_secrets.json")
        try:
            shutil.copy(secrets_path, os.path.join(dirname, 'client_secrets.json'))
        except shutil.Error, e:
            show_error(str(e))

    # Now, try and obtain the API for the first time
    get_api = raw_input("Would you like to authenticate your client_secrets.json? [Y/n] ")
    if get_api == '' or get_api.lower().startswith('y'):
        get_drive_api(dirname, reset_creds=True)

    ret = {}
    default_account = settings.get("google_account", "")
    account = raw_input(("What Google account should have access to new spreadsheets? "
                         "(e.g. somebody@gmail.com, leave blank to specify for each new "
                         "project) [{0}] ".format(default_account)
                        ))
    if default_account != "" and account == "":
        account = default_account
    if account != "":
        ret = { "google_account" : account }

    return ret
    puts("\n- Done configuring Google spreadsheets.")


def _setup_s3(settings, path, prompt=True):
    """Prompt user to set up Amazon S3"""
    ret = {'default_s3_buckets': {}, 's3_credentials': settings.get('s3_credentials', {})}

    if prompt:
        use = raw_input("\nWould you like to set up Amazon S3? [Y/n] ")
        if use.lower() != "y" and use != "":
            puts("\n- Not configuring Amazon S3.")
            return ret

    existing_access_key = settings.get('default_s3_access_key_id', None) or \
                          os.environ.get('AWS_ACCESS_KEY_ID', None)
    existing_secret_key = settings.get('default_s3_secret_access_key', None) or \
                          os.environ.get('AWS_SECRET_ACCESS_KEY', None)

    #import ipdb; ipdb.set_trace();

    access_key_prompt = "\nPlease enter your default Amazon Access Key ID:"
    if existing_access_key:
        access_key_prompt += ' [%s] ' % existing_access_key
    else:
        access_key_prompt += ' (leave blank to skip) '
    default_aws_access_key_id = raw_input(access_key_prompt)

    if default_aws_access_key_id == '' and existing_access_key:
        default_aws_access_key_id = existing_access_key


    if default_aws_access_key_id:
        secret_key_prompt = "\nPlease enter your default Amazon Secret Access Key:"
        if existing_secret_key:
            secret_key_prompt += ' [%s] ' % existing_secret_key
        else:
            secret_key_prompt += ' (leave blank to skip) '
        default_aws_secret_access_key = raw_input(secret_key_prompt)

        if default_aws_secret_access_key == '' and existing_secret_key:
            default_aws_secret_access_key = existing_secret_key

        ret.update({
            'default_s3_access_key_id': default_aws_access_key_id,
            'default_s3_secret_access_key': default_aws_secret_access_key,
        })

    # If we're all set with AWS creds, we can setup our default
    # staging and production buckets
    if default_aws_access_key_id and default_aws_secret_access_key:
        existing_staging_bucket = None
        existing_production_bucket = None
        if settings.get('default_s3_buckets'):
            existing_staging_bucket = settings['default_s3_buckets'].get('staging', None)
            existing_production_bucket = settings['default_s3_buckets'].get('production', None)

        staging_prompt = "\nWhat is your default staging bucket?"
        if existing_staging_bucket:
            staging_prompt += ' [%s] ' % existing_staging_bucket
        else:
            staging_prompt += ' (e.g. apps.beta.myorg.com, leave blank to skip) '
        staging = raw_input(staging_prompt)

        if staging == '' and existing_staging_bucket:
            staging = existing_staging_bucket
        if staging != "":
            ret['default_s3_buckets'].update({
                'staging': staging,
            })

        production_prompt = "\nWhat is your default production bucket?"
        if existing_production_bucket:
            production_prompt += ' [%s] ' % existing_production_bucket
        else:
            production_prompt += ' (e.g. apps.myorg.com, leave blank to skip) '
        production = raw_input(production_prompt)

        if production == '' and existing_production_bucket:
            production = existing_production_bucket
        if production != "":
            ret['default_s3_buckets'].update({
                'production': production,
            })


    more_prompt = "\nWould you like to add bucket credentials? [y/N] "
    while raw_input(more_prompt).lower() == 'y':
        ## Ask for a uri
        additional_s3_bucket = raw_input(
            "\nPlease specify an additional bucket (e.g. "
            "additional.bucket.myorg.com/, leave blank to skip adding bucket) ")
        if additional_s3_bucket == "":
            continue

        ## Ask for an access key, if it differs from the default
        additional_access_key_prompt = "\nPlease specify an AWS Access Key ID for this bucket:"

        if default_aws_access_key_id:
            additional_access_key_prompt += ' [%s] ' % default_aws_access_key_id
        else:
            additional_access_key_prompt += ' (leave blank to skip adding bucket) '

        additional_aws_access_key_id = raw_input(additional_access_key_prompt)

        if additional_aws_access_key_id == "" and default_aws_access_key_id:
            additional_aws_access_key_id = default_aws_access_key_id
        elif additional_aws_access_key_id == "":
            continue

        # Ask for a secret key, if it differs from default
        additional_secret_key_prompt = "\nPlease specify an AWS Secret Access Key for this bucket:"

        if default_aws_secret_access_key:
            additional_secret_key_prompt += ' [%s] ' % default_aws_secret_access_key
        else:
            additional_secret_key_prompt += ' (leave blank to skip adding bucket) '

        additional_aws_secret_access_key = raw_input(
            additional_secret_key_prompt)

        if additional_aws_secret_access_key == "" and default_aws_secret_access_key:
            additional_aws_secret_access_key = default_aws_secret_access_key
        elif additional_aws_secret_access_key == "":
            continue

        ret['s3_credentials'][additional_s3_bucket] = {
            'access_key_id': additional_aws_access_key_id,
            'secret_access_key': additional_aws_secret_access_key,
        }

    puts("\n- Done configuring Amazon S3.")
    return ret


def _setup_tarbell_project_path(settings, path, prompt=True):
    """Prompt user to set up project path."""
    default_path = os.path.expanduser(os.path.join("~", "tarbell"))
    projects_path = raw_input("\nWhat is your Tarbell projects path? [Default: {0}, 'none' to skip] ".format(colored.green(default_path)))
    if projects_path == "":
        projects_path = default_path
    if projects_path.lower() == 'none':
        puts("\n- Not creating projects directory.")
        return {}

    if os.path.isdir(projects_path):
        puts("\nDirectory exists!")
    else:
        puts("\nDirectory does not exist.")
        make = raw_input("\nWould you like to create it? [Y/n] ")
        if make.lower() == "y" or not make:
            os.makedirs(projects_path)
    puts("\nProjects path is {0}".format(projects_path))
    puts("\n- Done setting up projects path.")
    return {"projects_path": projects_path}


def _setup_default_templates(settings, path, prompt=True):
    """Add some (hardcoded) default templates."""
    project_templates = [{
        "name": "Basic Bootstrap 3 template",
        "url": "https://github.com/newsapps/tarbell-template",
    }, {
        "name": "Searchable map template",
        "url": "https://github.com/eads/tarbell-map-template",
    }]
    for project in project_templates:
        puts("+ Adding {0} ({1})".format(project["name"], project["url"]))

    puts("\n- Done configuring project templates.")
    return {"project_templates": project_templates}


def _backup(path, filename):
    """Backup a file."""
    target = os.path.join(path, filename)
    if os.path.isfile(target):
        dt = datetime.now()
        new_filename = ".{0}.{1}.{2}".format(
            filename, dt.isoformat(), "backup"
        )
        destination = os.path.join(path, new_filename)
        puts("- Backing up {0} to {1}".format(
            colored.cyan(target),
            colored.cyan(destination)
        ))

        shutil.copy(target, destination)

########NEW FILE########
__FILENAME__ = contextmanagers
# -*- coding: utf-8 -*-

"""
tarbell.cli
~~~~~~~~~

This module provides context managers for Tarbell projects.
"""

import os
import sys

from clint.textui import colored, puts

from .app import TarbellSite
from .settings import Settings
from .utils import show_error, get_config_from_args, list_get
from .configure import tarbell_configure

from copy import copy

class EnsureSettings():
    """Ensure the user has a Tarbell configuration."""
    def __init__(self, command, args):
        self.command = command
        self.path = get_config_from_args(args)

    def __enter__(self):
        if (os.path.isfile(self.path)):
            settings = Settings(self.path)
            # beta2 and older check
            if settings.config.get('s3_buckets'):
                puts(colored.red("--- Warning! ---\n"))
                puts("Your configuration file is out of date. Amazon S3 publishing will not work.")
                puts("Run {0} to update your Amazon S3 configuration.".format(
                    colored.yellow('tarbell configure s3')
                    ))
                puts(colored.red("\n----------------\n"))
                if self.command.name == "publish":
                    show_error("publish called, exiting.")
                    sys.exit(1)

            return settings

        else:
            puts("\n{0}: {1}".format(
                colored.red("Warning:"),
                "No Tarbell configuration found, running {0}.".format(
                    colored.green("tarbell configure")
                )
            ))
            settings = tarbell_configure(self.args)
            puts("\n\n Trying to run {0} again".format(
                colored.yellow("tarbell {0}".format(self.args.get(0)))
            ))
            return settings

    def __exit__(self, type, value, traceback):
        # @TODO This isn't quite right, __enter__ does too much work.
        pass


class EnsureProject():
    """Context manager to ensure the user is in a Tarbell site environment."""
    def __init__(self, command, args):
        self.command = command
        self.args = args

    def __enter__(self):
        return self.ensure_site()

    def __exit__(self, type, value, traceback):
        pass

    def ensure_site(self, path=None):
        if not path:
            path = os.getcwd()

        if path is "/":
            show_error(("The current directory is not part of a Tarbell "
                        "project"))
            sys.exit(1)

        if not os.path.exists(os.path.join(path, 'tarbell_config.py')):
            path = os.path.realpath(os.path.join(path, '..'))
            return self.ensure_site(path)
        else:
            os.chdir(path)
            site = TarbellSite(path)
            return site

# Lowercase aliases
ensure_settings = EnsureSettings
ensure_project = EnsureProject

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Tarbell documentation build configuration file, created by
# sphinx-quickstart on Fri Sep 27 12:40:21 2013.
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
import sphinx_rtd_theme

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Tarbell'
copyright = u'2013, Chicago Tribune News Applications Team and David Eads'

# The short X.Y version.
version = '0.9'

# The full version, including alpha/beta/rc tags.
release = '0.9-beta4'

exclude_patterns = ['_build']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "sphinx_rtd_theme"

html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

html_static_path = ['_static']

# If false, no module index is generated.
html_domain_indices = False

# If false, no index is generated.
html_use_index = False

# Output file base name for HTML help builder.
htmlhelp_basename = 'Tarbelldoc'

# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'tarbell', u'Tarbell Documentation',
     [u'News Apps and David Eads'], 1)
]

# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Tarbell', u'Tarbell Documentation',
   u'News Apps and David Eads', 'Tarbell', 'A very simple publishing tool.',
   'Miscellaneous'),
]

########NEW FILE########
__FILENAME__ = oauth
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from oauth2client import client
from oauth2client import keyring_storage
from oauth2client import tools
from apiclient import discovery
import getpass
import httplib2
import os

OAUTH_SCOPE = 'https://www.googleapis.com/auth/drive'

# Force the noauth_local_webserver flag to cover remote operation (e.g.
# using these commands on a server or in a virtual machine.)
parser = ArgumentParser(description=__doc__,
                        formatter_class=RawDescriptionHelpFormatter,
                        parents=[tools.argparser])
flags = parser.parse_args(['--noauth_local_webserver'])


def get_drive_api(path, reset_creds=False):
    """
    Reads the local client secrets file if available (otherwise, opens a
    browser tab to walk through the OAuth 2.0 process, and stores the client
    secrets for future use) and then authorizes those credentials. Returns a
    Google Drive API service object.
    """
    # Retrieve credentials from local storage, if possible
    storage = keyring_storage.Storage('tarbell', getpass.getuser())
    credentials = None
    if not reset_creds:
        credentials = storage.get()
    if not credentials:
        flow = client.flow_from_clientsecrets(os.path.join(path,
                                              'client_secrets.json'),
                                              scope=OAUTH_SCOPE)
        credentials = tools.run_flow(flow, storage, flags)
        storage.put(credentials)
    http = httplib2.Http()
    http = credentials.authorize(http)
    service = discovery.build('drive', 'v2', http=http)
    return service

########NEW FILE########
__FILENAME__ = s3
import fnmatch
import hashlib
import gzip
import mimetypes
import os
import re
import shutil
import sys
import tempfile

from boto.exception import S3ResponseError
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from clint.textui import puts, colored
from urllib import quote_plus
from urllib2 import urlopen

from .utils import show_error

EXCLUDES = ['.git', '^\.']


class S3Url(str):
    def __new__(self, content):
        # Parse
        if not content.endswith("/"):
            content = "{0}/".format(content)
        if content.startswith("s3://"):
            content = content[5:]
        self.root, self.path = content.split("/", 1)
        return str.__new__(self, content.rstrip("/"))


class S3Sync:
    def __init__(self, directory, bucket, access_key_id, secret_access_key, force=False, excludes=[]):
        connection = S3Connection(access_key_id, secret_access_key)
        self.force = force
        self.bucket = bucket
        self.excludes = r'|'.join([fnmatch.translate(x) for x in EXCLUDES + excludes]) or r'$.'
        self.directory = directory.rstrip('/')

        try:
            self.connection = connection.get_bucket(bucket.root)
        except S3ResponseError, e:
            show_error("S3 error! See below:\n")
            puts("{0}\n".format(str(e)))
            sys.exit()

    def deploy_to_s3(self):
        """
        Deploy a directory to an s3 bucket.
        """
        self.tempdir = tempfile.mkdtemp('s3deploy')

        for keyname, absolute_path in self.find_file_paths():
            self.s3_upload(keyname, absolute_path)

        shutil.rmtree(self.tempdir, True)
        return True

    def s3_upload(self, keyname, absolute_path):
        """
        Upload a file to s3
        """
        mimetype = mimetypes.guess_type(absolute_path)
        options = {'Content-Type': mimetype[0]}

        if mimetype[0] is not None and mimetype[0].startswith('text/'):
            upload = open(absolute_path)
            options['Content-Encoding'] = 'gzip'
            key_parts = keyname.split('/')
            filename = key_parts.pop()
            temp_path = os.path.join(self.tempdir, filename)
            gzfile = gzip.open(temp_path, 'wb')
            gzfile.write(upload.read())
            gzfile.close()
            absolute_path = temp_path

        hash = '"{0}"'.format(hashlib.md5(open(absolute_path, 'rb').read()).hexdigest())
        key = "{0}/{1}".format(self.bucket.path, keyname)
        existing = self.connection.get_key(key)

        if self.force or not existing or (existing.etag != hash):
            k = Key(self.connection)
            k.key = key
            puts("+ Uploading {0}/{1}".format(self.bucket, keyname))
            k.set_contents_from_filename(absolute_path, options, policy='public-read')
        else:
            puts("- Skipping  {0}/{1}, files match".format(self.bucket, keyname))


    def find_file_paths(self):
        """
        A generator function that recursively finds all files in the upload directory.
        """
        paths = []
        for root, dirs, files in os.walk(self.directory, topdown=True):
            dirs[:] = [os.path.join(root, d) for d in dirs]
            dirs[:] = [d for d in dirs if not re.match(self.excludes, d)]
            rel_path = os.path.relpath(root, self.directory)
            for f in files:
                if rel_path == '.':
                    path = (f, os.path.join(root, f))
                else:
                    path = (os.path.join(rel_path, f), os.path.join(root, f))
                if not re.match(self.excludes, path[0]):
                    paths.append(path)
        return paths

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
import yaml
import os


class Settings:
    """Simple object representation of Tarbell settings."""
    def __init__(self, path):
        self.path = path

        self.config = {}
        try:
            with open(self.path) as f:
                self.config = yaml.load(f)
        except IOError:
            pass

        self.client_secrets = False
        client_secrets_path = os.path.join(os.path.dirname(self.path), "client_secrets.json")
        try:
            with open(client_secrets_path) as f:
                self.client_secrets = True
        except IOError:
            pass

    def save(self):
        with open(self.path, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False)

########NEW FILE########
__FILENAME__ = slughifi
# -*- coding: utf-8 -*-
import re
from types import UnicodeType
import unicodedata


def slugify(value):
    """
    Normalizes string, removes non-alpha characters, and converts hyphens
    and spaces to underscores.
    """
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(re.sub('[^\w\s-]', '', value).strip())
    return re.sub('[-\s]+', '_', value)

# default unicode character mapping ( you may not see some chars, leave as is )
char_map = {u'À': 'A', u'Á': 'A', u'Â': 'A', u'Ã': 'A', u'Ä': 'Ae', u'Å': 'A', u'Æ': 'A', u'Ā': 'A', u'Ą': 'A', u'Ă': 'A', u'Ç': 'C', u'Ć': 'C', u'Č': 'C', u'Ĉ': 'C', u'Ċ': 'C', u'Ď': 'D', u'Đ': 'D', u'È': 'E', u'É': 'E', u'Ê': 'E', u'Ë': 'E', u'Ē': 'E', u'Ę': 'E', u'Ě': 'E', u'Ĕ': 'E', u'Ė': 'E', u'Ĝ': 'G', u'Ğ': 'G', u'Ġ': 'G', u'Ģ': 'G', u'Ĥ': 'H', u'Ħ': 'H', u'Ì': 'I', u'Í': 'I', u'Î': 'I', u'Ï': 'I', u'Ī': 'I', u'Ĩ': 'I', u'Ĭ': 'I', u'Į': 'I', u'İ': 'I', u'Ĳ': 'IJ', u'Ĵ': 'J', u'Ķ': 'K', u'Ľ': 'K', u'Ĺ': 'K', u'Ļ': 'K', u'Ŀ': 'K', u'Ł': 'L', u'Ñ': 'N', u'Ń': 'N', u'Ň': 'N', u'Ņ': 'N', u'Ŋ': 'N', u'Ò': 'O', u'Ó': 'O', u'Ô': 'O', u'Õ': 'O', u'Ö': 'Oe', u'Ø': 'O', u'Ō': 'O', u'Ő': 'O', u'Ŏ': 'O', u'Œ': 'OE', u'Ŕ': 'R', u'Ř': 'R', u'Ŗ': 'R', u'Ś': 'S', u'Ş': 'S', u'Ŝ': 'S', u'Ș': 'S', u'Š': 'S', u'Ť': 'T', u'Ţ': 'T', u'Ŧ': 'T', u'Ț': 'T', u'Ù': 'U', u'Ú': 'U', u'Û': 'U', u'Ü': 'Ue', u'Ū': 'U', u'Ů': 'U', u'Ű': 'U', u'Ŭ': 'U', u'Ũ': 'U', u'Ų': 'U', u'Ŵ': 'W', u'Ŷ': 'Y', u'Ÿ': 'Y', u'Ý': 'Y', u'Ź': 'Z', u'Ż': 'Z', u'Ž': 'Z', u'à': 'a', u'á': 'a', u'â': 'a', u'ã': 'a', u'ä': 'ae', u'ā': 'a', u'ą': 'a', u'ă': 'a', u'å': 'a', u'æ': 'ae', u'ç': 'c', u'ć': 'c', u'č': 'c', u'ĉ': 'c', u'ċ': 'c', u'ď': 'd', u'đ': 'd', u'è': 'e', u'é': 'e', u'ê': 'e', u'ë': 'e', u'ē': 'e', u'ę': 'e', u'ě': 'e', u'ĕ': 'e', u'ė': 'e', u'ƒ': 'f', u'ĝ': 'g', u'ğ': 'g', u'ġ': 'g', u'ģ': 'g', u'ĥ': 'h', u'ħ': 'h', u'ì': 'i', u'í': 'i', u'î': 'i', u'ï': 'i', u'ī': 'i', u'ĩ': 'i', u'ĭ': 'i', u'į': 'i', u'ı': 'i', u'ĳ': 'ij', u'ĵ': 'j', u'ķ': 'k', u'ĸ': 'k', u'ł': 'l', u'ľ': 'l', u'ĺ': 'l', u'ļ': 'l', u'ŀ': 'l', u'ñ': 'n', u'ń': 'n', u'ň': 'n', u'ņ': 'n', u'ŉ': 'n', u'ŋ': 'n', u'ò': 'o', u'ó': 'o', u'ô': 'o', u'õ': 'o', u'ö': 'oe', u'ø': 'o', u'ō': 'o', u'ő': 'o', u'ŏ': 'o', u'œ': 'oe', u'ŕ': 'r', u'ř': 'r', u'ŗ': 'r', u'ś': 's', u'š': 's', u'ť': 't', u'ù': 'u', u'ú': 'u', u'û': 'u', u'ü': 'ue', u'ū': 'u', u'ů': 'u', u'ű': 'u', u'ŭ': 'u', u'ũ': 'u', u'ų': 'u', u'ŵ': 'w', u'ÿ': 'y', u'ý': 'y', u'ŷ': 'y', u'ż': 'z', u'ź': 'z', u'ž': 'z', u'ß': 'ss', u'ſ': 'ss', u'Α': 'A', u'Ά': 'A', u'Ἀ': 'A', u'Ἁ': 'A', u'Ἂ': 'A', u'Ἃ': 'A', u'Ἄ': 'A', u'Ἅ': 'A', u'Ἆ': 'A', u'Ἇ': 'A', u'ᾈ': 'A', u'ᾉ': 'A', u'ᾊ': 'A', u'ᾋ': 'A', u'ᾌ': 'A', u'ᾍ': 'A', u'ᾎ': 'A', u'ᾏ': 'A', u'Ᾰ': 'A', u'Ᾱ': 'A', u'Ὰ': 'A', u'Ά': 'A', u'ᾼ': 'A', u'Β': 'B', u'Γ': 'G', u'Δ': 'D', u'Ε': 'E', u'Έ': 'E', u'Ἐ': 'E', u'Ἑ': 'E', u'Ἒ': 'E', u'Ἓ': 'E', u'Ἔ': 'E', u'Ἕ': 'E', u'Έ': 'E', u'Ὲ': 'E', u'Ζ': 'Z', u'Η': 'I', u'Ή': 'I', u'Ἠ': 'I', u'Ἡ': 'I', u'Ἢ': 'I', u'Ἣ': 'I', u'Ἤ': 'I', u'Ἥ': 'I', u'Ἦ': 'I', u'Ἧ': 'I', u'ᾘ': 'I', u'ᾙ': 'I', u'ᾚ': 'I', u'ᾛ': 'I', u'ᾜ': 'I', u'ᾝ': 'I', u'ᾞ': 'I', u'ᾟ': 'I', u'Ὴ': 'I', u'Ή': 'I', u'ῌ': 'I', u'Θ': 'TH', u'Ι': 'I', u'Ί': 'I', u'Ϊ': 'I', u'Ἰ': 'I', u'Ἱ': 'I', u'Ἲ': 'I', u'Ἳ': 'I', u'Ἴ': 'I', u'Ἵ': 'I', u'Ἶ': 'I', u'Ἷ': 'I', u'Ῐ': 'I', u'Ῑ': 'I', u'Ὶ': 'I', u'Ί': 'I', u'Κ': 'K', u'Λ': 'L', u'Μ': 'M', u'Ν': 'N', u'Ξ': 'KS', u'Ο': 'O', u'Ό': 'O', u'Ὀ': 'O', u'Ὁ': 'O', u'Ὂ': 'O', u'Ὃ': 'O', u'Ὄ': 'O', u'Ὅ': 'O', u'Ὸ': 'O', u'Ό': 'O', u'Π': 'P', u'Ρ': 'R', u'Ῥ': 'R', u'Σ': 'S', u'Τ': 'T', u'Υ': 'Y', u'Ύ': 'Y', u'Ϋ': 'Y', u'Ὑ': 'Y', u'Ὓ': 'Y', u'Ὕ': 'Y', u'Ὗ': 'Y', u'Ῠ': 'Y', u'Ῡ': 'Y', u'Ὺ': 'Y', u'Ύ': 'Y', u'Φ': 'F', u'Χ': 'X', u'Ψ': 'PS', u'Ω': 'O', u'Ώ': 'O', u'Ὠ': 'O', u'Ὡ': 'O', u'Ὢ': 'O', u'Ὣ': 'O', u'Ὤ': 'O', u'Ὥ': 'O', u'Ὦ': 'O', u'Ὧ': 'O', u'ᾨ': 'O', u'ᾩ': 'O', u'ᾪ': 'O', u'ᾫ': 'O', u'ᾬ': 'O', u'ᾭ': 'O', u'ᾮ': 'O', u'ᾯ': 'O', u'Ὼ': 'O', u'Ώ': 'O', u'ῼ': 'O', u'α': 'a', u'ά': 'a', u'ἀ': 'a', u'ἁ': 'a', u'ἂ': 'a', u'ἃ': 'a', u'ἄ': 'a', u'ἅ': 'a', u'ἆ': 'a', u'ἇ': 'a', u'ᾀ': 'a', u'ᾁ': 'a', u'ᾂ': 'a', u'ᾃ': 'a', u'ᾄ': 'a', u'ᾅ': 'a', u'ᾆ': 'a', u'ᾇ': 'a', u'ὰ': 'a', u'ά': 'a', u'ᾰ': 'a', u'ᾱ': 'a', u'ᾲ': 'a', u'ᾳ': 'a', u'ᾴ': 'a', u'ᾶ': 'a', u'ᾷ': 'a', u'β': 'b', u'γ': 'g', u'δ': 'd', u'ε': 'e', u'έ': 'e', u'ἐ': 'e', u'ἑ': 'e', u'ἒ': 'e', u'ἓ': 'e', u'ἔ': 'e', u'ἕ': 'e', u'ὲ': 'e', u'έ': 'e', u'ζ': 'z', u'η': 'i', u'ή': 'i', u'ἠ': 'i', u'ἡ': 'i', u'ἢ': 'i', u'ἣ': 'i', u'ἤ': 'i', u'ἥ': 'i', u'ἦ': 'i', u'ἧ': 'i', u'ᾐ': 'i', u'ᾑ': 'i', u'ᾒ': 'i', u'ᾓ': 'i', u'ᾔ': 'i', u'ᾕ': 'i', u'ᾖ': 'i', u'ᾗ': 'i', u'ὴ': 'i', u'ή': 'i', u'ῂ': 'i', u'ῃ': 'i', u'ῄ': 'i', u'ῆ': 'i', u'ῇ': 'i', u'θ': 'th', u'ι': 'i', u'ί': 'i', u'ϊ': 'i', u'ΐ': 'i', u'ἰ': 'i', u'ἱ': 'i', u'ἲ': 'i', u'ἳ': 'i', u'ἴ': 'i', u'ἵ': 'i', u'ἶ': 'i', u'ἷ': 'i', u'ὶ': 'i', u'ί': 'i', u'ῐ': 'i', u'ῑ': 'i', u'ῒ': 'i', u'ΐ': 'i', u'ῖ': 'i', u'ῗ': 'i', u'κ': 'k', u'λ': 'l', u'μ': 'm', u'ν': 'n', u'ξ': 'ks', u'ο': 'o', u'ό': 'o', u'ὀ': 'o', u'ὁ': 'o', u'ὂ': 'o', u'ὃ': 'o', u'ὄ': 'o', u'ὅ': 'o', u'ὸ': 'o', u'ό': 'o', u'π': 'p', u'ρ': 'r', u'ῤ': 'r', u'ῥ': 'r', u'σ': 's', u'ς': 's', u'τ': 't', u'υ': 'y', u'ύ': 'y', u'ϋ': 'y', u'ΰ': 'y', u'ὐ': 'y', u'ὑ': 'y', u'ὒ': 'y', u'ὓ': 'y', u'ὔ': 'y', u'ὕ': 'y', u'ὖ': 'y', u'ὗ': 'y', u'ὺ': 'y', u'ύ': 'y', u'ῠ': 'y', u'ῡ': 'y', u'ῢ': 'y', u'ΰ': 'y', u'ῦ': 'y', u'ῧ': 'y', u'φ': 'f', u'χ': 'x', u'ψ': 'ps', u'ω': 'o', u'ώ': 'o', u'ὠ': 'o', u'ὡ': 'o', u'ὢ': 'o', u'ὣ': 'o', u'ὤ': 'o', u'ὥ': 'o', u'ὦ': 'o', u'ὧ': 'o', u'ᾠ': 'o', u'ᾡ': 'o', u'ᾢ': 'o', u'ᾣ': 'o', u'ᾤ': 'o', u'ᾥ': 'o', u'ᾦ': 'o', u'ᾧ': 'o', u'ὼ': 'o', u'ώ': 'o', u'ῲ': 'o', u'ῳ': 'o', u'ῴ': 'o', u'ῶ': 'o', u'ῷ': 'o', u'¨': '', u'΅': '', u'᾿': '', u'῾': '', u'῍': '', u'῝': '', u'῎': '', u'῞': '', u'῏': '', u'῟': '', u'῀': '', u'῁': '', u'΄': '', u'΅': '', u'`': '', u'῭': '', u'ͺ': '', u'᾽': '', u'А': 'A', u'Б': 'B', u'В': 'V', u'Г': 'G', u'Д': 'D', u'Е': 'E', u'Ё': 'E', u'Ж': 'ZH', u'З': 'Z', u'И': 'I', u'Й': 'I', u'К': 'K', u'Л': 'L', u'М': 'M', u'Н': 'N', u'О': 'O', u'П': 'P', u'Р': 'R', u'С': 'S', u'Т': 'T', u'У': 'U', u'Ф': 'F', u'Х': 'KH', u'Ц': 'TS', u'Ч': 'CH', u'Ш': 'SH', u'Щ': 'SHCH', u'Ы': 'Y', u'Э': 'E', u'Ю': 'YU', u'Я': 'YA', u'а': 'A', u'б': 'B', u'в': 'V', u'г': 'G', u'д': 'D', u'е': 'E', u'ё': 'E', u'ж': 'ZH', u'з': 'Z', u'и': 'I', u'й': 'I', u'к': 'K', u'л': 'L', u'м': 'M', u'н': 'N', u'о': 'O', u'п': 'P', u'р': 'R', u'с': 'S', u'т': 'T', u'у': 'U', u'ф': 'F', u'х': 'KH', u'ц': 'TS', u'ч': 'CH', u'ш': 'SH', u'щ': 'SHCH', u'ы': 'Y', u'э': 'E', u'ю': 'YU', u'я': 'YA', u'Ъ': '', u'ъ': '', u'Ь': '', u'ь': '', u'ð': 'd', u'Ð': 'D', u'þ': 'th', u'Þ': 'TH',
            u'ა': 'a', u'ბ': 'b', u'გ': 'g', u'დ': 'd', u'ე': 'e', u'ვ': 'v', u'ზ': 'z', u'თ': 't', u'ი': 'i', u'კ': 'k', u'ლ': 'l', u'მ': 'm', u'ნ': 'n', u'ო': 'o', u'პ': 'p', u'ჟ': 'zh', u'რ': 'r', u'ს': 's', u'ტ': 't', u'უ': 'u', u'ფ': 'p', u'ქ': 'k', u'ღ': 'gh', u'ყ': 'q', u'შ': 'sh', u'ჩ': 'ch', u'ც': 'ts', u'ძ': 'dz', u'წ': 'ts', u'ჭ': 'ch', u'ხ': 'kh', u'ჯ': 'j', u'ჰ': 'h'}


def replace_char(m):
    char = m.group()
    if char in char_map:
        return char_map[char]
    else:
        return char


def slughifi(value, overwrite_char_map={}):
    """
        High Fidelity slugify - slughifi.py, v 0.1

        Examples :

        >>> text = 'C\'est déjà l\'été.'

        >>> slughifi(text)
        'cest-deja-lete'

        >>> slughifi(text, overwrite_char_map={u'\': '-',})
        'c-est-deja-l-ete'

        >>> slughifi(text, do_slugify=False)
        "C'est deja l'ete."

        # Normal slugify removes accented characters
        >>> slugify(text)
        'cest-dj-lt'

    """

    # unicodification
    if type(value) != UnicodeType:
        value = unicode(value, 'utf-8', 'ignore')

    # overwrite chararcter mapping
    char_map.update(overwrite_char_map)

    # try to replace chars
    value = re.sub('[^a-zA-Z0-9\\s\\-]{1}', replace_char, value)

    value = slugify(value)

    return value.encode('ascii', 'ignore')

########NEW FILE########
__FILENAME__ = config
URL_ROOT = ''

########NEW FILE########
__FILENAME__ = config
GOOGLE_DOC = {
    'key': '0Ak3IIavLYTovdHI4ODdQMzR1b0NzUHR1dTdialRQUXc',
}

DEFAULT_CONTEXT = {
    'title': 'Tarbell project test',
}

# URL_ROOT = 'example-project'
# DONT_PUBLISH = False
# CREATE_JSON = False
CONTEXT_SOURCE_FILE = 'project/data/project.csv'

########NEW FILE########
__FILENAME__ = test
import os
import unittest
from tarbell.app import TarbellSite


class TarbellSiteTestCase(unittest.TestCase):
    """
    Tests for the TarbellSite class methods.
    """
    def setUp(self):
        """ Get a fake Tarbell site instance. """
        test_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'example')

        self.site = TarbellSite(test_dir)

    def test_init(self):
        """
        Creating an instance of TarbellSite without a path
        raises a TypeError exception.
        """
        self.assertRaises(TypeError, TarbellSite, )

    def test_filter_files(self):
        name, project, project_path = self.site.projects[0]

        filtered = self.site.filter_files(project_path)
        next = filtered.next()

        """
        Each project tuple has a length of 3
        """
        self.assertEqual(len(next), 3)

        """
        The first item in the project tuple equals the project_path passed
        """
        self.assertEqual(project_path, next[0])

    def test_sort_modules(self):
        """
        Our "base" project is always the last item in the
        return list of sorted modules
        """
        projects = sorted(self.site.projects, cmp=self.site.sort_modules)
        self.assertEqual(projects[-1][0], "base")

    def test_load_projects(self):
        """
        Load projects returns a list with length of 2, since our test app
        has two sub directories: base and project.
        """
        self.assertEqual(len(self.site.load_projects()), 2)

    @unittest.skip('')
    def test_preview(self):
        pass

    def test_get_context(self):
        """
        Our get_context method should return a dictionary
        """
        self.assertTrue(isinstance(self.site.get_context(), dict))

    def test_get_context_from_csv(self):
        """
        Our get_context_from_csv should fetch a local file path or an url
        """
        self.assertTrue(isinstance(self.site.get_context_from_csv(), dict))

        self.site.CONTEXT_SOURCE_FILE = 'https://raw.github.com/newsapps/'
        'flask-tarbell/0.9/tarbell/tests/example/project/data/project.csv'

        self.assertTrue(isinstance(self.site.get_context_from_csv(), dict))

    @unittest.skip('')
    def test_get_context_from_gdoc(self):
        pass

    @unittest.skip('')
    def test__get_context_from_gdoc(self):
        pass

    @unittest.skip('')
    def test_export_xlsx(self):
        pass

    @unittest.skip('')
    def test_process_xlsx(self):
        pass

    @unittest.skip('')
    def test_copy_global_values(self):
        pass

    @unittest.skip('')
    def test_make_headers(self):
        pass

    @unittest.skip('')
    def test_make_worksheet_data(self):
        pass

    @unittest.skip('')
    def test_generate_static_site(self):
        pass


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

"""
tarbell.utils
~~~~~~~~~

This module provides utilities for Tarbell.
"""

import os
import sys
from clint.textui import colored


def list_get(l, idx, default=None):
    """Get from a list with an optional default value."""
    try:
        if l[idx]:
            return l[idx]
        else:
            return default
    except IndexError:
        return default


def black(s):
    """Black text."""
    #if settings.allow_black_foreground:
        #return colored.black(s)
    #else:
    return s.encode('utf-8')


def split_sentences(s):
    """Split sentences for formatting."""
    sentences = []
    for index, sentence in enumerate(s.split('. ')):
        pad = ''
        if index > 0:
            pad = ' ' * 41
        if sentence.endswith('.'):
            sentence = sentence[:-1]
        sentences.append('%s %s.' % (pad, sentence.strip()))
    return "\n".join(sentences)


def show_error(msg):
    """Displays error message."""
    sys.stdout.flush()
    sys.stderr.write("{0}: {1}".format(colored.red("Error"), msg + '\n'))


def get_config_from_args(args):
    """Get config directory from arguments."""
    return os.path.expanduser(
        os.path.join("~", ".{0}".format("tarbell"), "settings.yaml")
    )
    return path


def filter_files(path):
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [
            dn for dn in dirnames
            if not dn.startswith('.') and not dn.startswith('_')
        ]
        filenames[:] = [
            fn for fn in filenames
            if not fn.endswith('.py') and not fn.endswith('.pyc') and not fn.startswith('.') and not fn.startswith('_')
        ]
        yield dirpath, dirnames, filenames

########NEW FILE########
