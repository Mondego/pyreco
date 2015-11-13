__FILENAME__ = base
from django.contrib.staticfiles import finders
from django.core.exceptions import SuspiciousOperation
from django.utils.functional import lazy
from static_precompiler.models import Dependency
from static_precompiler.settings import STATIC_ROOT, ROOT, OUTPUT_DIR
from static_precompiler.utils import get_mtime, normalize_path
import logging
import os
import posixpath


logger = logging.getLogger("static_precompiler")


class BaseCompiler(object):

    supports_dependencies = False

    def is_supported(self, source_path):
        """ Return True iff provided source file type is supported by this precompiler.

        :param source_path: relative path to a source file
        :type source_path: str
        :returns: bool

        """
        raise NotImplementedError

    #noinspection PyMethodMayBeStatic
    def get_full_source_path(self, source_path):
        """ Return the full path to the given source file.
            Check if the source file exists.
            The returned path is OS-dependent.

        :param source_path: relative path to a source file
        :type source_path: str
        :returns: str
        :raises: ValueError

        """
        norm_source_path = normalize_path(source_path.lstrip("/"))

        if STATIC_ROOT:
            full_path = os.path.join(STATIC_ROOT, norm_source_path)
            if os.path.exists(full_path):
                return full_path

        try:
            full_path = finders.find(norm_source_path)
        except SuspiciousOperation:
            full_path = None

        if full_path is None:
            raise ValueError("Can't find staticfile named: {0}".format(source_path))

        return full_path

    def get_output_filename(self, source_filename):
        """ Return the name of compiled file based on the name of source file.

        :param source_filename: name of a source file
        :type source_filename: str
        :returns: str

        """
        raise NotImplementedError

    def get_output_path(self, source_path):
        """ Get relative path to compiled file based for the given source file.
            The returned path is in posix format.

        :param source_path: relative path to a source file
        :type source_path: str
        :returns: str

        """
        source_dir = os.path.dirname(source_path)
        source_filename = os.path.basename(source_path)
        output_filename = self.get_output_filename(source_filename)
        return posixpath.join(OUTPUT_DIR, source_dir, output_filename)

    def get_full_output_path(self, source_path):
        """ Get full path to compiled file based for the given source file.
            The returned path is OS-dependent.

        :param source_path: relative path to a source file
        :type source_path: str
        :returns: str

        """
        return os.path.join(ROOT, normalize_path(self.get_output_path(source_path.lstrip("/"))))

    def get_source_mtime(self, source_path):
        """ Get the modification time of the source file.

        :param source_path: relative path to a source file
        :type source_path: str
        :returns: int

        """
        return get_mtime(self.get_full_source_path(source_path))

    def get_output_mtime(self, source_path):
        """ Get the modification time of the compiled file.
            Return None of compiled file does not exist.

        :param source_path: relative path to a source file
        :type source_path: str
        :returns: int, None

        """
        full_output_path = self.get_full_output_path(source_path)
        if not os.path.exists(full_output_path):
            return None
        return get_mtime(full_output_path)

    def should_compile(self, source_path, watch=False):
        """ Return True iff provided source file should be compiled.

        :param source_path: relative path to a source file
        :type source_path: str
        :param watch: whether the method was invoked from watch utility
        :type watch: bool
        :returns: bool

        """
        compiled_mtime = self.get_output_mtime(source_path)

        if compiled_mtime is None:
            return True

        source_mtime = self.get_source_mtime(source_path)

        if self.supports_dependencies:
            for dependency in self.get_dependencies(source_path):
                if compiled_mtime <= self.get_source_mtime(dependency):
                    return True

        return compiled_mtime <= source_mtime

    def get_source(self, source_path):
        """ Get the source code to be compiled.

        :param source_path: relative path to a source file
        :type source_path: str
        :returns: str

        """
        with open(self.get_full_source_path(source_path)) as source:
            return source.read()

    def write_output(self, output, source_path):
        """ Write the compiled output to a file.

        :param output: compiled code
        :type output: str
        :param source_path: relative path to a source file
        :type source_path: str

        """
        output_path = self.get_full_output_path(source_path)
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        compiled_file = open(output_path, "w+")
        compiled_file.write(output)
        compiled_file.close()

    def compile(self, source_path, watch=False):
        """ Compile the given source path and return relative path to the compiled file.
            Raise ValueError is the source file type is not supported.
            May raise a StaticCompilationError if something goes wrong with compilation.
        :param source_path: relative path to a source file
        :type source_path: str
        :param watch: whether the method was invoked from watch utility
        :type watch: bool

        :returns: str

        """
        if not self.is_supported(source_path):
            raise ValueError("'{0}' file type is not supported by '{1}'".format(
                source_path, self.__class__.__name__
            ))
        if self.should_compile(source_path, watch=watch):

            compiled = self.compile_file(source_path)
            compiled = self.postprocess(compiled, source_path)
            self.write_output(compiled, source_path)

            if self.supports_dependencies:
                self.update_dependencies(source_path, self.find_dependencies(source_path))

            logging.info("Compiled: '{0}'".format(source_path))

        return self.get_output_path(source_path)

    def compile_lazy(self, source_path):
        """ Return a lazy object which, when translated to string, compiles the specified source path and returns
            the path to the compiled file.
            Raise ValueError is the source file type is not supported.
            May raise a StaticCompilationError if something goes wrong with compilation.
            :param source_path: relative path to a source file
            :type source_path: str

            :returns: str
        """
        return self.compile(source_path)

    compile_lazy = lazy(compile_lazy, str)

    def compile_file(self, source_path):
        """ Compile the source file. Return the compiled code.
            May raise a StaticCompilationError if something goes wrong with compilation.

        :param source_path: path to the source file
        :type source_path: str
        :returns: str

        """
        raise NotImplementedError

    def compile_source(self, source):
        """ Compile the source code. May raise a StaticCompilationError
            if something goes wrong with compilation.

        :param source: source code
        :type source: str
        :returns: str

        """
        raise NotImplementedError

    #noinspection PyMethodMayBeStatic,PyUnusedLocal
    def postprocess(self, compiled, source_path):
        """ Post-process the compiled code.

        :param compiled: compiled code
        :type compiled: str
        :param source_path: relative path to a source file
        :type source_path: str
        :returns: str
        """
        return compiled

    def find_dependencies(self, source_path):
        """ Find the dependencies for the given source file.

        :param source_path: relative path to a source file
        :type source_path: str
        :returns: list
        """
        raise NotImplementedError

    #noinspection PyMethodMayBeStatic
    def get_dependencies(self, source_path):
        """ Get the saved dependencies for the given source file.

        :param source_path: relative path to a source file
        :type source_path: str
        :returns: list of str
        """
        return list(Dependency.objects.filter(
            source=source_path
        ).order_by("depends_on").values_list(
            "depends_on", flat=True
        ))

    #noinspection PyMethodMayBeStatic
    def get_dependents(self, source_path):
        """ Get a list of files that depends on the given source file.

        :param source_path: relative path to a source file
        :type source_path: str
        :returns: list of str
        """
        return list(Dependency.objects.filter(
            depends_on=source_path
        ).order_by("source").values_list(
            "source", flat=True
        ))

    #noinspection PyMethodMayBeStatic
    def update_dependencies(self, source_path, dependencies):
        """ Updates the saved dependencies for the given source file.

        :param source_path: relative path to a source file
        :type source_path: str
        :param dependencies: list of files that source file depends on
        :type dependencies: list of str

        """
        if not dependencies:
            Dependency.objects.filter(source=source_path).delete()
        else:
            Dependency.objects.filter(
                source=source_path
            ).exclude(
                depends_on__in=dependencies,
            ).delete()
            for dependency in dependencies:
                Dependency.objects.get_or_create(
                    source=source_path,
                    depends_on=dependency,
                )

    def handle_changed_file(self, source_path):
        """ Handle the modification of the source file.

        :param source_path: relative path to a source file
        :type source_path: str

        """
        self.compile(source_path, watch=True)
        for dependent in self.get_dependents(source_path):
            self.compile(dependent, watch=True)

########NEW FILE########
__FILENAME__ = coffeescript
from static_precompiler.exceptions import StaticCompilationError
from static_precompiler.compilers.base import BaseCompiler
from static_precompiler.settings import COFFEESCRIPT_EXECUTABLE
from static_precompiler.utils import run_command


class CoffeeScript(BaseCompiler):

    def is_supported(self, source_path):
        return source_path.endswith(".coffee")

    def get_output_filename(self, source_filename):
        return source_filename[:-7] + ".js"

    def compile_file(self, source_path):
        return self.compile_source(self.get_source(source_path))

    def compile_source(self, source):
        args = [
            COFFEESCRIPT_EXECUTABLE,
            "-c",
            "-s",
            "-p",
        ]
        out, errors = run_command(args, source)
        if errors:
            raise StaticCompilationError(errors)

        return out

########NEW FILE########
__FILENAME__ = less
from static_precompiler.exceptions import StaticCompilationError
from static_precompiler.compilers.base import BaseCompiler
from static_precompiler.settings import LESS_EXECUTABLE
from static_precompiler.utils import run_command, convert_urls
import os
import posixpath
import re


class LESS(BaseCompiler):

    supports_dependencies = True

    IMPORT_RE = re.compile(r"@import\s+(.+?)\s*;", re.DOTALL)
    IMPORT_ITEM_RE = re.compile(r"([\"'])(.+?)\1")
    EXTENSION = ".less"

    def is_supported(self, source_path):
        return source_path.endswith(self.EXTENSION)

    def get_output_filename(self, source_filename):
        return source_filename[:-len(self.EXTENSION)] + ".css"

    def should_compile(self, source_path, watch=False):
        # Do not auto-compile the files that start with "_"
        if watch and os.path.basename(source_path).startswith("_"):
            return False
        return super(LESS, self).should_compile(source_path, watch)

    def compile_file(self, source_path):
        full_source_path = self.get_full_source_path(source_path)
        args = [
            LESS_EXECUTABLE,
            full_source_path,
        ]
        # `cwd` is a directory containing `source_path`. Ex: source_path = '1/2/3', full_source_path = '/abc/1/2/3' -> cwd = '/abc'
        cwd = os.path.normpath(os.path.join(full_source_path, *([".."] * len(source_path.split("/")))))
        out, errors = run_command(args, None, cwd=cwd)
        if errors:
            raise StaticCompilationError(errors)

        return out

    def compile_source(self, source):
        args = [
            LESS_EXECUTABLE,
            "-"
        ]

        out, errors = run_command(args, source)

        if errors:
            raise StaticCompilationError(errors)

        return out

    def postprocess(self, compiled, source_path):
        return convert_urls(compiled, source_path)

    def find_imports(self, source):
        """ Find the imported files in the source code.

        :param source: source code
        :type source: str
        :returns: list of str

        """
        imports = set()
        for import_string in self.IMPORT_RE.findall(source):
            import_string = import_string.strip()
            if import_string.startswith("(css)"):
                continue
            if "url(" in import_string:
                continue
            match = self.IMPORT_ITEM_RE.search(import_string)
            if not match:
                continue
            import_item = match.groups()[1].strip()
            if not import_item:
                continue
            if import_item.endswith(".css") and not import_string.startswith("(inline)"):
                continue
            imports.add(import_item)

        return sorted(imports)

    def locate_imported_file(self, source_dir, import_path):
        """ Locate the imported file in the source directory.
            Return the relative path to the imported file in posix format.

        :param source_dir: source directory
        :type source_dir: str
        :param import_path: path to the imported file
        :type import_path: str
        :returns: str

        """
        if not import_path.endswith(self.EXTENSION):
            import_path += self.EXTENSION

        path = posixpath.normpath(posixpath.join(source_dir, import_path))

        try:
            self.get_full_source_path(path)
            return path
        except ValueError:
            pass

        filename = posixpath.basename(import_path)
        if filename[0] != "_":
            path = posixpath.normpath(posixpath.join(
                source_dir,
                posixpath.dirname(import_path),
                "_" + filename,
            ))

        try:
            self.get_full_source_path(path)
            return path
        except ValueError:
            pass

        raise StaticCompilationError(
            "Can't locate the imported file: {0}".format(import_path)
        )

    def find_dependencies(self, source_path):
        source = self.get_source(source_path)
        source_dir = posixpath.dirname(source_path)
        dependencies = set()
        for import_path in self.find_imports(source):
            import_path = self.locate_imported_file(source_dir, import_path)
            dependencies.add(import_path)
            dependencies.update(self.find_dependencies(import_path))
        return sorted(dependencies)


########NEW FILE########
__FILENAME__ = scss
from static_precompiler import settings
from static_precompiler.exceptions import StaticCompilationError
from static_precompiler.compilers.base import BaseCompiler
from static_precompiler.utils import run_command, convert_urls
import os
import posixpath
import re


class SCSS(BaseCompiler):

    supports_dependencies = True

    IMPORT_RE = re.compile(r"@import\s+(.+?)\s*;", re.DOTALL)
    EXTENSION = ".scss"

    # noinspection PyMethodMayBeStatic
    def compass_enabled(self):
        return settings.SCSS_USE_COMPASS

    def is_supported(self, source_path):
        return source_path.endswith(self.EXTENSION)

    def get_output_filename(self, source_filename):
        return source_filename[:-len(self.EXTENSION)] + ".css"

    def should_compile(self, source_path, watch=False):
        # Do not auto-compile the files that start with "_"
        if watch and os.path.basename(source_path).startswith("_"):
            return False
        return super(SCSS, self).should_compile(source_path, watch)

    def compile_file(self, source_path):
        full_source_path = self.get_full_source_path(source_path)
        args = [
            settings.SCSS_EXECUTABLE,
            "-C",
            full_source_path,
        ]

        if self.compass_enabled():
            args.append("--compass")

        # `cwd` is a directory containing `source_path`. Ex: source_path = '1/2/3', full_source_path = '/abc/1/2/3' -> cwd = '/abc'
        cwd = os.path.normpath(os.path.join(full_source_path, *([".."] * len(source_path.split("/")))))
        out, errors = run_command(args, None, cwd=cwd)

        if errors:
            raise StaticCompilationError(errors)

        return out

    def compile_source(self, source):
        args = [
            settings.SCSS_EXECUTABLE,
            "-s",
            "--scss",
            "-C",
        ]

        if self.compass_enabled():
            args.append("--compass")

        out, errors = run_command(args, source)
        if errors:
            raise StaticCompilationError(errors)

        return out

    def postprocess(self, compiled, source_path):
        return convert_urls(compiled, source_path)

    def parse_import_string(self, import_string):
        """ Extract import items from import string.
        :param import_string: import string
        :type import_string: str
        :returns: list of str
        """
        items = []
        item = ""
        in_quotes = False
        quote = ""
        in_parentheses = False
        item_allowed = True

        for char in import_string:

            if char == ")":
                in_parentheses = False
                continue

            if in_parentheses:
                continue

            if char == "(":
                item = ""
                in_parentheses = True
                continue

            if char == ",":
                if in_quotes:
                    item += char
                else:
                    if item:
                        items.append(item)
                        item = ""
                    item_allowed = True
                continue

            if char in " \t\n\r\f\v":
                if in_quotes:
                    item += char
                elif item:
                    items.append(item)
                    item_allowed = False
                    item = ""
                continue

            if char in "\"'":
                if in_quotes:
                    if char == quote:
                        # Close quote
                        in_quotes = False
                    else:
                        item += char
                else:
                    in_quotes = True
                    quote = char
                continue

            if not item_allowed:
                break

            item += char

        if item:
            items.append(item)

        return sorted(items)

    def find_imports(self, source):
        """ Find the imported files in the source code.

        :param source: source code
        :type source: str
        :returns: list of str

        """
        imports = set()
        for import_string in self.IMPORT_RE.findall(source):
            for import_item in self.parse_import_string(import_string):
                import_item = import_item.strip()
                if not import_item:
                    continue
                if import_item.endswith(".css"):
                    continue
                if import_item.startswith("http://") or \
                   import_item.startswith("https://"):
                    continue
                if self.compass_enabled() and (import_item in ("compass", "compass.scss") or import_item.startswith("compass/")):
                    # Ignore compass imports if Compass is enabled.
                    continue
                imports.add(import_item)
        return sorted(imports)

    def locate_imported_file(self, source_dir, import_path):
        """ Locate the imported file in the source directory.
            Return the path to the imported file relative to STATIC_ROOT

        :param source_dir: source directory
        :type source_dir: str
        :param import_path: path to the imported file
        :type import_path: str
        :returns: str

        """
        if not import_path.endswith(self.EXTENSION):
            import_path += self.EXTENSION
        path = posixpath.normpath(posixpath.join(source_dir, import_path))

        try:
            self.get_full_source_path(path)
            return path
        except ValueError:
            pass

        filename = posixpath.basename(import_path)
        if filename[0] != "_":
            path = posixpath.normpath(posixpath.join(
                source_dir,
                posixpath.dirname(import_path),
                "_" + filename,
            ))

        try:
            self.get_full_source_path(path)
            return path
        except ValueError:
            pass

        raise StaticCompilationError(
            "Can't locate the imported file: {0}".format(import_path)
        )

    def find_dependencies(self, source_path):
        source = self.get_source(source_path)
        source_dir = posixpath.dirname(source_path)
        dependencies = set()
        for import_path in self.find_imports(source):
            import_path = self.locate_imported_file(source_dir, import_path)
            dependencies.add(import_path)
            dependencies.update(self.find_dependencies(import_path))
        return sorted(dependencies)


class SASS(SCSS):

    EXTENSION = ".sass"
    IMPORT_RE = re.compile(r"@import\s+(.+?)\s*(?:\n|$)")

    def compile_source(self, source):
        args = [
            settings.SCSS_EXECUTABLE,
            "-s",
            "-C",
        ]

        if self.compass_enabled():
            args.append("--compass")

        out, errors = run_command(args, source)
        if errors:
            raise StaticCompilationError(errors)

        return out

########NEW FILE########
__FILENAME__ = exceptions


class StaticCompilationError(Exception):
    pass


class UnsupportedFile(Exception):
    pass

########NEW FILE########
__FILENAME__ = finders
from django.contrib.staticfiles.finders import BaseStorageFinder
from django.core.files.storage import FileSystemStorage
from static_precompiler.settings import ROOT


class StaticPrecompilerFileStorage(FileSystemStorage):
    """
    Standard file system storage for files handled by django-static-precompiler.

    The default for ``location`` is ``STATIC_PRECOMPILER_ROOT``
    """
    def __init__(self, location=None, base_url=None):
        if location is None:
            location = ROOT
        super(StaticPrecompilerFileStorage, self).__init__(location, base_url)


class StaticPrecompilerFinder(BaseStorageFinder):
    """
    A staticfiles finder that looks in STATIC_PRECOMPILER_ROOT
    for compiled files, to be used during development
    with staticfiles development file server or during
    deployment.
    """
    storage = StaticPrecompilerFileStorage

    def list(self, ignore_patterns):
        return []

########NEW FILE########
__FILENAME__ = static_precompiler_watch
from django.contrib.staticfiles.finders import get_finders
from django.core.files.storage import FileSystemStorage
from django.core.management.base import NoArgsCommand
from optparse import make_option
from static_precompiler.exceptions import StaticCompilationError
from static_precompiler.settings import STATIC_ROOT
from static_precompiler.utils import get_compilers
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import os
import time


def get_watched_dirs():
    dirs = set([STATIC_ROOT])
    for finder in get_finders():
        if hasattr(finder, "storages"):
            for storage in finder.storages.values():
                if isinstance(storage, FileSystemStorage):
                    dirs.add(storage.location)
    return sorted(dirs)


class EventHandler(FileSystemEventHandler):

    def __init__(self, watched_dir, verbosity, compilers):
        self.watched_dir = watched_dir
        self.verbosity = verbosity
        self.compilers = compilers
        super(EventHandler, self).__init__()

    def on_any_event(self, e):
        if e.is_directory or e.event_type not in ("created", "modified"):
            return
        path = e.src_path[len(self.watched_dir):]
        if path.startswith("/"):
            path = path[1:]
        for compiler in self.compilers:
            if compiler.is_supported(path):
                if self.verbosity > 1:
                    if e.event_type == "created":
                        print("Created: '{0}'".format(path))
                    else:
                        print("Modified: '{0}'".format(path))
                try:
                    compiler.handle_changed_file(path)
                except (StaticCompilationError, ValueError) as e:
                    print(e)
                break


class Command(NoArgsCommand):

    help = 'Watch for static files changes and re-compile them if necessary.'

    requires_model_validation = False

    option_list = NoArgsCommand.option_list + (
        make_option("--no-initial-scan",
                    action="store_false",
                    dest="initial_scan",
                    default=True,
                    help="Skip the initial scan of watched directories."),
    )

    def handle_noargs(self, **options):

        watched_dirs = get_watched_dirs()

        print("Watching directories:")
        for watched_dir in watched_dirs:
            print(watched_dir)
        print("\nPress Control+C to exit.\n")

        verbosity = int(options["verbosity"])

        compilers = get_compilers()

        if options["initial_scan"]:
            # Scan the watched directories and compile everything
            for watched_dir in watched_dirs:
                for dirname, dirnames, filenames in os.walk(watched_dir):
                    for filename in filenames:
                        path = os.path.join(dirname, filename)[len(watched_dir):]
                        if path.startswith("/"):
                            path = path[1:]
                        for compiler in compilers:
                            if compiler.is_supported(path):
                                try:
                                    compiler.handle_changed_file(path)
                                except (StaticCompilationError, ValueError) as e:
                                    print(e)
                                break

        observer = Observer()

        for watched_dir in watched_dirs:
            handler = EventHandler(watched_dir, verbosity, compilers)
            observer.schedule(handler, path=watched_dir, recursive=True)

        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()

        observer.join()

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    # noinspection PyUnusedLocal
    def forwards(self, orm):
        # Adding model 'Dependency'
        db.create_table('static_precompiler_dependency', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('source', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
            ('depends_on', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
        ))
        db.send_create_signal('static_precompiler', ['Dependency'])

        # Adding unique constraint on 'Dependency', fields ['source', 'depends_on']
        db.create_unique('static_precompiler_dependency', ['source', 'depends_on'])

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def backwards(self, orm):
        # Removing unique constraint on 'Dependency', fields ['source', 'depends_on']
        db.delete_unique('static_precompiler_dependency', ['source', 'depends_on'])

        # Deleting model 'Dependency'
        db.delete_table('static_precompiler_dependency')

    models = {
        'static_precompiler.dependency': {
            'Meta': {'unique_together': "(('source', 'depends_on'),)", 'object_name': 'Dependency'},
            'depends_on': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'})
        }
    }

    complete_apps = ['static_precompiler']

########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_dependency_source__chg_field_dependency_depends_on
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    # noinspection PyUnusedLocal
    def forwards(self, orm):

        # Changing field 'Dependency.source'
        db.alter_column('static_precompiler_dependency', 'source', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Changing field 'Dependency.depends_on'
        db.alter_column('static_precompiler_dependency', 'depends_on', self.gf('django.db.models.fields.CharField')(max_length=255))

    # noinspection PyUnusedLocal
    def backwards(self, orm):

        # Changing field 'Dependency.source'
        db.alter_column('static_precompiler_dependency', 'source', self.gf('django.db.models.fields.CharField')(max_length=500))

        # Changing field 'Dependency.depends_on'
        db.alter_column('static_precompiler_dependency', 'depends_on', self.gf('django.db.models.fields.CharField')(max_length=500))

    models = {
        'static_precompiler.dependency': {
            'Meta': {'unique_together': "(('source', 'depends_on'),)", 'object_name': 'Dependency'},
            'depends_on': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'})
        }
    }

    complete_apps = ['static_precompiler']

########NEW FILE########
__FILENAME__ = models
from django.db import models


class Dependency(models.Model):

    source = models.CharField(max_length=255, db_index=True)
    depends_on = models.CharField(max_length=255, db_index=True)

    class Meta:
        unique_together = ("source", "depends_on")

########NEW FILE########
__FILENAME__ = settings
# coding: utf-8
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import os


STATIC_ROOT = getattr(settings, "STATIC_ROOT", getattr(settings, "MEDIA_ROOT"))
STATIC_URL = getattr(settings, "STATIC_URL", getattr(settings, "MEDIA_URL"))

POSIX_COMPATIBLE = True if os.name == 'posix' else False

MTIME_DELAY = getattr(settings, "STATIC_PRECOMPILER_MTIME_DELAY", 10)  # 10 seconds

COMPILERS = getattr(settings, "STATIC_PRECOMPILER_COMPILERS", (
    "static_precompiler.compilers.CoffeeScript",
    "static_precompiler.compilers.SASS",
    "static_precompiler.compilers.SCSS",
    "static_precompiler.compilers.LESS",
))

ROOT = getattr(settings, "STATIC_PRECOMPILER_ROOT",
               getattr(settings, "STATIC_ROOT",
                       getattr(settings, "MEDIA_ROOT")))

if not ROOT:
    raise ImproperlyConfigured("You must specify either STATIC_ROOT or STATIC_PRECOMPILER_ROOT folder.")


OUTPUT_DIR = getattr(settings, "STATIC_PRECOMPILER_OUTPUT_DIR",
                     "COMPILED")

# Use cache for inline compilation
USE_CACHE = getattr(settings, "STATIC_PRECOMPILER_USE_CACHE", True)

# Cache timeout for inline compilation
CACHE_TIMEOUT = getattr(
    settings,
    "STATIC_PRECOMPILER_CACHE_TIMEOUT",
    60 * 60 * 24 * 30
)  # 30 days

COFFEESCRIPT_EXECUTABLE = getattr(settings, "COFFEESCRIPT_EXECUTABLE", "coffee")
SCSS_EXECUTABLE = getattr(settings, "SCSS_EXECUTABLE", "sass")
SCSS_USE_COMPASS = getattr(settings, "SCSS_USE_COMPASS", False)
LESS_EXECUTABLE = getattr(settings, "LESS_EXECUTABLE", "lessc")

PREPEND_STATIC_URL = getattr(settings, 'STATIC_PRECOMPILER_PREPEND_STATIC_URL', False)

########NEW FILE########
__FILENAME__ = base
from django.core.cache import cache
from django.template import Node
from static_precompiler.settings import USE_CACHE, CACHE_TIMEOUT
from static_precompiler.utils import get_cache_key, get_hexdigest


class BaseInlineNode(Node):

    compiler = None

    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        source = self.nodelist.render(context)

        if USE_CACHE:
            cache_key = get_cache_key(get_hexdigest(source))
            cached = cache.get(cache_key, None)
            if cached is not None:
                return cached
            output = self.compiler.compile_source(source)
            cache.set(cache_key, output, CACHE_TIMEOUT)
            return output

        return self.compiler.compile_source(source)

########NEW FILE########
__FILENAME__ = coffeescript
from django.template.base import Library
from static_precompiler.compilers import CoffeeScript
from static_precompiler.templatetags.base import BaseInlineNode
from static_precompiler.utils import prepend_static_url


register = Library()
compiler = CoffeeScript()


class InlineCoffeescriptNode(BaseInlineNode):

    compiler = compiler


#noinspection PyUnusedLocal
@register.tag(name="inlinecoffeescript")
def do_inlinecoffeescript(parser, token):
    nodelist = parser.parse(("endinlinecoffeescript",))
    parser.delete_first_token()
    return InlineCoffeescriptNode(nodelist)


@register.simple_tag
def coffeescript(path):
    return prepend_static_url(compiler.compile(str(path)))


########NEW FILE########
__FILENAME__ = less
from django.template.base import Library
from static_precompiler.compilers import LESS
from static_precompiler.templatetags.base import BaseInlineNode
from static_precompiler.utils import prepend_static_url


register = Library()
compiler = LESS()


class InlineLESSNode(BaseInlineNode):

    compiler = compiler


#noinspection PyUnusedLocal
@register.tag(name="inlineless")
def do_inlinecoffeescript(parser, token):
    nodelist = parser.parse(("endinlineless",))
    parser.delete_first_token()
    return InlineLESSNode(nodelist)


@register.simple_tag
def less(path):
    return prepend_static_url(compiler.compile(str(path)))


########NEW FILE########
__FILENAME__ = sass
from django.template.base import Library
from static_precompiler.compilers import SASS
from static_precompiler.templatetags.base import BaseInlineNode
from static_precompiler.utils import prepend_static_url


register = Library()
compiler = SASS()


class InlineSASSNode(BaseInlineNode):

    compiler = compiler


#noinspection PyUnusedLocal
@register.tag(name="inlinesass")
def do_inlinecoffeescript(parser, token):
    nodelist = parser.parse(("endinlinesass",))
    parser.delete_first_token()
    return InlineSASSNode(nodelist)


@register.simple_tag
def sass(path):
    return prepend_static_url(compiler.compile(str(path)))


########NEW FILE########
__FILENAME__ = scss
from django.template.base import Library
from static_precompiler.compilers import SCSS
from static_precompiler.templatetags.base import BaseInlineNode
from static_precompiler.utils import prepend_static_url


register = Library()
compiler = SCSS()


class InlineSCSSNode(BaseInlineNode):

    compiler = compiler


#noinspection PyUnusedLocal
@register.tag(name="inlinescss")
def do_inlinecoffeescript(parser, token):
    nodelist = parser.parse(("endinlinescss",))
    parser.delete_first_token()
    return InlineSCSSNode(nodelist)


@register.simple_tag
def scss(path):
    return prepend_static_url(compiler.compile(str(path)))


########NEW FILE########
__FILENAME__ = django_settings
# noinspection PyUnresolvedReferences
from django.conf.global_settings import *
import os

DEBUG = True
SECRET_KEY = "static_precompiler"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

STATIC_ROOT = MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'static')
STATIC_URL = MEDIA_URL = "/static/"

# noinspection PyUnresolvedReferences
STATICFILES_DIRS = (
    os.path.join(os.path.dirname(__file__), 'staticfiles_dir'),
    ("prefix", os.path.join(os.path.dirname(__file__), 'staticfiles_dir_with_prefix')),
)

INSTALLED_APPS = (
    "static_precompiler",
)
MTIME_DELAY = 2

SCSS_USE_COMPASS = True

########NEW FILE########
__FILENAME__ = test_base_compiler
from django.core import management
from mock import patch, MagicMock
from static_precompiler.compilers.base import BaseCompiler
from static_precompiler.models import Dependency
from static_precompiler.settings import OUTPUT_DIR, ROOT
import os
import shutil
import unittest


class BaseCompilerTestCase(unittest.TestCase):

    def setUp(self):
        from django.conf import settings as django_settings
        self.django_settings = django_settings

        output_dir = os.path.join(self.django_settings.STATIC_ROOT, OUTPUT_DIR)

        # Remove the output directory if it exists to start from scratch
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)

        management.call_command('syncdb', interactive=False, verbosity=0)

    def tearDown(self):
        output_dir = os.path.join(self.django_settings.STATIC_ROOT, OUTPUT_DIR)

        # Remove the output directory
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)

        management.call_command('flush', interactive=False, verbosity=0)

    def test_is_supported(self):
        compiler = BaseCompiler()
        self.assertRaises(
            NotImplementedError,
            lambda: compiler.is_supported("dummy.coffee")
        )

    def test_get_output_filename(self):
        compiler = BaseCompiler()
        self.assertRaises(
            NotImplementedError,
            lambda: compiler.get_output_filename("dummy.coffee")
        )

    def test_get_full_source_path(self):

        compiler = BaseCompiler()

        root = os.path.dirname(__file__)

        self.assertEqual(
            compiler.get_full_source_path("scripts/test.coffee"),
            os.path.join(root, "static", "scripts", "test.coffee"),
        )

        # Source file doesn't exist
        self.assertRaises(
            ValueError,
            lambda: compiler.get_full_source_path("scripts/does-not-exist.coffee")
        )

        self.assertEqual(
            compiler.get_full_source_path("another_test.coffee"),
            os.path.normpath(
                os.path.join(
                    root,
                    "staticfiles_dir",
                    "another_test.coffee"
                )
            )
        )

        self.assertEqual(
            compiler.get_full_source_path("prefix/another_test.coffee"),
            os.path.normpath(
                os.path.join(
                    root,
                    "staticfiles_dir_with_prefix",
                    "another_test.coffee"
                )
            )
        )

    def test_get_output_path(self):
        compiler = BaseCompiler()
        compiler.get_output_filename = MagicMock(
            side_effect=lambda source_path: source_path.replace(".coffee", ".js")
        )
        self.assertEqual(
            compiler.get_output_path("scripts/test.coffee"),
            OUTPUT_DIR + "/scripts/test.js"
        )

    def test_get_full_output_path(self):
        compiler = BaseCompiler()
        compiler.get_output_path = MagicMock(
            return_value=OUTPUT_DIR + "/dummy.js"
        )
        self.assertEqual(
            compiler.get_full_output_path("dummy.coffee"),
            os.path.join(ROOT, OUTPUT_DIR, "dummy.js")
        )

    def test_get_source_mtime(self):
        compiler = BaseCompiler()
        compiler.get_full_source_path = MagicMock(return_value="dummy.coffee")
        with patch("static_precompiler.compilers.base.get_mtime") as mocked_get_mtime:
            mocked_get_mtime.return_value = 1
            self.assertEqual(compiler.get_source_mtime("dummy.coffee"), 1)
            mocked_get_mtime.assert_called_with("dummy.coffee")
            #noinspection PyUnresolvedReferences
            compiler.get_full_source_path.assert_called_with("dummy.coffee")

    def test_get_output_mtime(self):
        compiler = BaseCompiler()
        compiler.get_full_output_path = MagicMock(return_value="dummy.js")
        with patch("os.path.exists") as mocked_os_path_exists:
            mocked_os_path_exists.return_value = False
            self.assertEqual(compiler.get_output_mtime("dummy.coffee"), None)
            mocked_os_path_exists.assert_called_with("dummy.js")
            mocked_os_path_exists.return_value = True
            with patch("static_precompiler.compilers.base.get_mtime") as mocked_get_mtime:
                mocked_get_mtime.return_value = 1
                self.assertEqual(compiler.get_output_mtime("dummy.coffee"), 1)
                mocked_get_mtime.assert_called_with("dummy.js")

    def test_should_compile(self):
        compiler = BaseCompiler()
        compiler.get_source_mtime = MagicMock()
        compiler.get_output_mtime = MagicMock()
        compiler.get_dependencies = MagicMock(return_value=["B", "C"])
        mtimes = dict(
            A=1,
            B=3,
            C=5,
        )
        compiler.get_source_mtime.side_effect = lambda x: mtimes[x]

        compiler.get_output_mtime.return_value = None
        self.assertTrue(compiler.should_compile("A"))

        compiler.supports_dependencies = True

        compiler.get_output_mtime.return_value = 6
        self.assertFalse(compiler.should_compile("A"))

        compiler.get_output_mtime.return_value = 5
        self.assertTrue(compiler.should_compile("A"))

        compiler.get_output_mtime.return_value = 4
        self.assertTrue(compiler.should_compile("A"))

        compiler.get_output_mtime.return_value = 2
        self.assertTrue(compiler.should_compile("A"))

        compiler.supports_dependencies = False

        compiler.get_output_mtime.return_value = 2
        self.assertFalse(compiler.should_compile("A"))

        compiler.get_output_mtime.return_value = 1
        self.assertTrue(compiler.should_compile("A"))

        compiler.get_output_mtime.return_value = 0
        self.assertTrue(compiler.should_compile("A"))

    def test_get_source(self):
        compiler = BaseCompiler()
        self.assertEqual(
            compiler.get_source("scripts/test.coffee"),
            'console.log "Hello, World!"'
        )

    def test_write_output(self):
        compiler = BaseCompiler()
        output_path = os.path.join(ROOT, OUTPUT_DIR, "dummy.js")
        self.assertFalse(os.path.exists(output_path))
        compiler.get_full_output_path = MagicMock(return_value=output_path)
        compiler.write_output("compiled", "dummy.coffee")
        self.assertTrue(os.path.exists(output_path))
        with open(output_path) as output:
            self.assertEqual(output.read(), "compiled")

    def test_compile_source(self):
        compiler = BaseCompiler()
        self.assertRaises(
            NotImplementedError,
            lambda: compiler.compile_source("source")
        )

    def test_postprocess(self):
        compiler = BaseCompiler()
        self.assertEqual(compiler.postprocess("compiled", "dummy.coffee"), "compiled")

    #noinspection PyUnresolvedReferences
    def test_compile(self):
        compiler = BaseCompiler()
        compiler.is_supported = MagicMock()
        compiler.should_compile = MagicMock()
        compiler.compile_file = MagicMock(return_value="compiled")
        compiler.write_output = MagicMock()
        compiler.get_output_path = MagicMock(return_value="dummy.js")
        compiler.postprocess = MagicMock(
            side_effect=lambda compiled, source_path: compiled
        )
        compiler.update_dependencies = MagicMock()
        compiler.find_dependencies = MagicMock(return_value=["A", "B"])

        compiler.is_supported.return_value = False
        self.assertRaises(ValueError, lambda: compiler.compile("dummy.coffee"))

        self.assertEqual(compiler.compile_file.call_count, 0)
        self.assertEqual(compiler.postprocess.call_count, 0)
        self.assertEqual(compiler.write_output.call_count, 0)

        compiler.is_supported.return_value = True
        compiler.should_compile.return_value = False
        self.assertEqual(compiler.compile("dummy.coffee"), "dummy.js")

        self.assertEqual(compiler.compile_file.call_count, 0)
        self.assertEqual(compiler.postprocess.call_count, 0)
        self.assertEqual(compiler.write_output.call_count, 0)

        compiler.should_compile.return_value = True
        self.assertEqual(compiler.compile("dummy.coffee"), "dummy.js")

        self.assertEqual(compiler.compile_file.call_count, 1)
        compiler.compile_file.assert_called_with("dummy.coffee")

        self.assertEqual(compiler.postprocess.call_count, 1)
        compiler.postprocess.assert_called_with("compiled", "dummy.coffee")

        self.assertEqual(compiler.write_output.call_count, 1)
        compiler.write_output.assert_called_with("compiled", "dummy.coffee")

        self.assertEqual(compiler.update_dependencies.call_count, 0)

        compiler.supports_dependencies = True
        compiler.compile("dummy.coffee")
        compiler.find_dependencies.assert_called_with("dummy.coffee")
        compiler.update_dependencies.assert_called_with("dummy.coffee", ["A", "B"])

    def test_compile_lazy(self):
        compiler = BaseCompiler()
        compiler.compile = MagicMock()
        compiler.compile.return_value = "dummy.js"

        lazy_compiled = compiler.compile_lazy("dummy.coffee")

        # noinspection PyUnresolvedReferences
        self.assertEqual(compiler.compile.call_count, 0)

        self.assertEqual(str(lazy_compiled), "dummy.js")

        # noinspection PyUnresolvedReferences
        self.assertEqual(compiler.compile.call_count, 1)
        # noinspection PyUnresolvedReferences
        compiler.compile.assert_called_with("dummy.coffee")

    def test_find_dependencies(self):
        compiler = BaseCompiler()
        self.assertRaises(
            NotImplementedError,
            lambda: compiler.find_dependencies("dummy.coffee")
        )

    def test_get_dependencies(self):
        compiler = BaseCompiler()
        self.assertFalse(Dependency.objects.exists())

        self.assertEqual(
            compiler.get_dependencies("spam.scss"),
            [],
        )

        Dependency.objects.create(
            source="spam.scss",
            depends_on="ham.scss"
        )
        Dependency.objects.create(
            source="spam.scss",
            depends_on="eggs.scss"
        )

        self.assertEqual(
            compiler.get_dependencies("spam.scss"),
            ["eggs.scss", "ham.scss"],
        )

    def test_get_dependents(self):
        compiler = BaseCompiler()
        self.assertFalse(Dependency.objects.exists())

        self.assertEqual(
            compiler.get_dependents("spam.scss"),
            [],
        )

        Dependency.objects.create(
            source="ham.scss",
            depends_on="spam.scss"
        )
        Dependency.objects.create(
            source="eggs.scss",
            depends_on="spam.scss"
        )

        self.assertEqual(
            compiler.get_dependents("spam.scss"),
            ["eggs.scss", "ham.scss"],
        )

    def test_update_dependencies(self):
        compiler = BaseCompiler()

        self.assertFalse(Dependency.objects.exists())

        compiler.update_dependencies("A", ["B", "C"])
        self.assertEqual(
            sorted(Dependency.objects.values_list("source", "depends_on")),
            [("A", "B"), ("A", "C")]
        )

        compiler.update_dependencies("A", ["B", "C", "D"])
        self.assertEqual(
            sorted(Dependency.objects.values_list("source", "depends_on")),
            [("A", "B"), ("A", "C"), ("A", "D")]
        )

        compiler.update_dependencies("A", ["E"])
        self.assertEqual(
            sorted(Dependency.objects.values_list("source", "depends_on")),
            [("A", "E")]
        )

        compiler.update_dependencies("B", ["C"])
        self.assertEqual(
            sorted(Dependency.objects.values_list("source", "depends_on")),
            [("A", "E"), ("B", "C")]
        )

        compiler.update_dependencies("A", [])
        self.assertEqual(
            sorted(Dependency.objects.values_list("source", "depends_on")),
            [("B", "C")]
        )


def suite():
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    test_suite.addTest(loader.loadTestsFromTestCase(BaseCompilerTestCase))
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = test_coffeescript
# coding: utf-8
from django.template import Context
from django.template.loader import get_template_from_string
from mock import patch, MagicMock
from static_precompiler.compilers.coffeescript import CoffeeScript
from static_precompiler.exceptions import StaticCompilationError
import unittest


class CoffeeScriptTestCase(unittest.TestCase):

    @staticmethod
    def clean_javascript(js):
        """ Remove comments and all blank lines. """
        return "\n".join(
            line for line in js.split("\n") if line.strip() and not line.startswith("//")
        )

    def test_is_supported(self):
        compiler = CoffeeScript()
        self.assertEqual(compiler.is_supported("dummy"), False)
        self.assertEqual(compiler.is_supported("dummy.coffee"), True)

    def test_get_output_filename(self):
        compiler = CoffeeScript()
        self.assertEqual(compiler.get_output_filename("dummy.coffee"), "dummy.js")
        self.assertEqual(
            compiler.get_output_filename("dummy.coffee.coffee"),
            "dummy.coffee.js"
        )

    def test_compile_file(self):
        compiler = CoffeeScript()

        self.assertEqual(
            self.clean_javascript(compiler.compile_file("scripts/test.coffee")),
            """(function() {\n  console.log("Hello, World!");\n}).call(this);"""
        )

    def test_compile_source(self):
        compiler = CoffeeScript()

        self.assertEqual(
            self.clean_javascript(compiler.compile_source('console.log "Hello, World!"')),
            """(function() {\n  console.log("Hello, World!");\n}).call(this);"""
        )

        self.assertRaises(
            StaticCompilationError,
            lambda: compiler.compile_source('console.log "Hello, World!')
        )

        # Test non-ascii
        self.assertEqual(
            self.clean_javascript(compiler.compile_source('console.log "Привет, Мир!"')),
            """(function() {\n  console.log("Привет, Мир!");\n}).call(this);"""
        )

    def test_coffessecript_templatetag(self):
        template = get_template_from_string("""{% load coffeescript %}{% coffeescript "dummy.coffee" %}""")
        with patch("static_precompiler.templatetags.coffeescript.compiler") as mocked_compiler:
            mocked_compiler.compile = MagicMock(return_value="dummy.js")
            self.assertEqual(
                template.render(Context({})),
                "dummy.js",
            )

    def test_inlinecoffessecript_templatetag(self):
        template = get_template_from_string("""{% load coffeescript %}{% inlinecoffeescript %}source{% endinlinecoffeescript %}""")
        with patch("static_precompiler.templatetags.coffeescript.InlineCoffeescriptNode.compiler") as mocked_compiler:
            mocked_compiler.compile_source = MagicMock(return_value="compiled")
            self.assertEqual(
                template.render(Context({})),
                "compiled",
            )


def suite():
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    test_suite.addTest(loader.loadTestsFromTestCase(CoffeeScriptTestCase))
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = test_less
# coding: utf-8
from django.template import Context
from django.template.loader import get_template_from_string
from mock import patch, MagicMock
from static_precompiler.compilers import LESS
from static_precompiler.exceptions import StaticCompilationError
from static_precompiler.utils import normalize_path
import os
import unittest


class LESSTestCase(unittest.TestCase):

    def test_is_supported(self):
        compiler = LESS()
        self.assertEqual(compiler.is_supported("dummy"), False)
        self.assertEqual(compiler.is_supported("dummy.less"), True)

    def test_get_output_filename(self):
        compiler = LESS()
        self.assertEqual(compiler.get_output_filename("dummy.less"), "dummy.css")
        self.assertEqual(
            compiler.get_output_filename("dummy.less.less"),
            "dummy.less.css"
        )

    def test_compile_file(self):
        compiler = LESS()

        self.assertEqual(
            compiler.compile_file("styles/test.less"),
            """p {
  font-size: 15px;
}
p a {
  color: red;
}
h1 {
  color: blue;
}
"""
        )

    def test_compile_source(self):
        compiler = LESS()

        self.assertEqual(
            compiler.compile_source("p {font-size: 15px; a {color: red;}}"),
            "p {\n  font-size: 15px;\n}\np a {\n  color: red;\n}\n"
        )

        self.assertRaises(
            StaticCompilationError,
            lambda: compiler.compile_source('invalid syntax')
        )

        # Test non-ascii
        NON_ASCII = """.external_link:first-child:before {
  content: "Zobacz także:";
  background: url(картинка.png);
}
"""
        self.assertEqual(
            compiler.compile_source(NON_ASCII),
            NON_ASCII
        )

    def test_postprocesss(self):
        compiler = LESS()
        with patch("static_precompiler.compilers.less.convert_urls") as mocked_convert_urls:
            mocked_convert_urls.return_value = "spam"
            self.assertEqual(compiler.postprocess("ham", "eggs"), "spam")
            mocked_convert_urls.assert_called_with("ham", "eggs")

    def test_find_imports(self):
        compiler = LESS()
        source = """
@import "foo.css";
@import " ";
@import "foo.less";
@import (reference) "reference.less";
@import (inline) "inline.css";
@import (less) "less.less";
@import (css) "css.css";
@import (once) "once.less";
@import (multiple) "multiple.less";
@import "screen.less" screen;
@import url(url-import);
@import 'single-quotes.less';
@import "no-extension";
"""
        expected = sorted([
            "foo.less",
            "reference.less",
            "inline.css",
            "less.less",
            "once.less",
            "multiple.less",
            "screen.less",
            "single-quotes.less",
            "no-extension",
        ])
        self.assertEqual(
            compiler.find_imports(source),
            expected
        )

    def test_locate_imported_file(self):
        compiler = LESS()
        with patch("os.path.exists") as mocked_os_path_exist:

            root = os.path.dirname(__file__)

            existing_files = set()
            for f in ("A/B.less", "D.less"):
                existing_files.add(os.path.join(root, "static", normalize_path(f)))

            mocked_os_path_exist.side_effect = lambda x: x in existing_files

            self.assertEqual(
                compiler.locate_imported_file("A", "B.less"),
                "A/B.less"
            )
            self.assertEqual(
                compiler.locate_imported_file("E", "../D"),
                "D.less"
            )
            self.assertEqual(
                compiler.locate_imported_file("E", "../A/B.less"),
                "A/B.less"
            )
            self.assertEqual(
                compiler.locate_imported_file("", "D.less"),
                "D.less"
            )
            self.assertRaises(
                StaticCompilationError,
                lambda: compiler.locate_imported_file("", "Z.less")
            )

    def test_find_dependencies(self):
        compiler = LESS()
        files = {
            "A.less": "@import 'B/C.less';",
            "B/C.less": "@import '../E';",
            "E.less": "p {color: red;}",
        }
        compiler.get_source = MagicMock(side_effect=lambda x: files[x])

        root = os.path.dirname(__file__)

        existing_files = set()
        for f in files:
            existing_files.add(os.path.join(root, "static", normalize_path(f)))

        with patch("os.path.exists") as mocked_os_path_exist:
            mocked_os_path_exist.side_effect = lambda x: x in existing_files

            self.assertEqual(
                compiler.find_dependencies("A.less"),
                ["B/C.less", "E.less"]
            )
            self.assertEqual(
                compiler.find_dependencies("B/C.less"),
                ["E.less"]
            )
            self.assertEqual(
                compiler.find_dependencies("E.less"),
                []
            )

    def test_less_templatetag(self):
        template = get_template_from_string("""{% load less %}{% less "dummy.less" %}""")
        with patch("static_precompiler.templatetags.less.compiler") as mocked_compiler:
            mocked_compiler.compile = MagicMock(return_value="dummy.css")
            self.assertEqual(
                template.render(Context({})),
                "dummy.css",
            )

    def test_inlineless_templatetag(self):
        template = get_template_from_string("""{% load less %}{% inlineless %}source{% endinlineless %}""")
        with patch("static_precompiler.templatetags.less.InlineLESSNode.compiler") as mocked_compiler:
            mocked_compiler.compile_source = MagicMock(return_value="compiled")
            self.assertEqual(
                template.render(Context({})),
                "compiled",
            )


def suite():
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    test_suite.addTest(loader.loadTestsFromTestCase(LESSTestCase))
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = test_scss
# coding: utf-8
from django.template import Context
from django.template.loader import get_template_from_string
from mock import patch, MagicMock
from static_precompiler.compilers import SASS, SCSS
from static_precompiler.exceptions import StaticCompilationError
from static_precompiler.utils import normalize_path, fix_line_breaks
import os
import unittest


class SCSSTestCase(unittest.TestCase):

    def test_is_supported(self):
        compiler = SCSS()
        self.assertEqual(compiler.is_supported("dummy"), False)
        self.assertEqual(compiler.is_supported("dummy.scss"), True)

    def test_get_output_filename(self):
        compiler = SCSS()
        self.assertEqual(compiler.get_output_filename("dummy.scss"), "dummy.css")
        self.assertEqual(
            compiler.get_output_filename("dummy.scss.scss"),
            "dummy.scss.css"
        )

    def test_compile_file(self):
        compiler = SCSS()

        self.assertEqual(
            fix_line_breaks(compiler.compile_file("styles/test.scss")),
            "p {\n  font-size: 15px; }\n  p a {\n    color: red; }\n"
        )

    def test_compile_source(self):
        compiler = SCSS()

        self.assertEqual(
            fix_line_breaks(compiler.compile_source("p {font-size: 15px; a {color: red;}}")),
            "p {\n  font-size: 15px; }\n  p a {\n    color: red; }\n"
        )

        self.assertRaises(
            StaticCompilationError,
            lambda: compiler.compile_source('invalid syntax')
        )

        # Test non-ascii
        NON_ASCII = """@charset "UTF-8";
.external_link:first-child:before {
  content: "Zobacz także:";
  background: url(картинка.png); }
"""
        self.assertEqual(
            fix_line_breaks(compiler.compile_source(NON_ASCII)),
            NON_ASCII
        )

    def test_postprocesss(self):
        compiler = SCSS()
        with patch("static_precompiler.compilers.scss.convert_urls") as mocked_convert_urls:
            mocked_convert_urls.return_value = "spam"
            self.assertEqual(compiler.postprocess("ham", "eggs"), "spam")
            mocked_convert_urls.assert_called_with("ham", "eggs")

    def test_parse_import_string(self):
        compiler = SCSS()
        import_string = """"foo, bar" , "foo", url(bar,baz),
         'bar,foo',bar screen, projection"""
        self.assertEqual(
            compiler.parse_import_string(import_string), [
                "bar",
                "bar,foo",
                "foo",
                "foo, bar",
            ]
        )
        import_string = """"foo,bar", url(bar,baz), 'bar,foo',bar screen, projection"""
        self.assertEqual(
            compiler.parse_import_string(import_string), [
                "bar",
                "bar,foo",
                "foo,bar",
            ]
        )
        import_string = """"foo" screen"""
        self.assertEqual(
            compiler.parse_import_string(import_string), [
                "foo",
            ]
        )

    def test_find_imports(self):
        compiler = SCSS()
        source = """
@import "foo.css", ;
@import " ";
@import "foo.scss";
@import "foo";
@import "foo.css";
@import "foo" screen;
@import "http://foo.com/bar";
@import url(foo);
@import "rounded-corners",
        "text-shadow";
@import "compass";
@import "compass.scss";
@import "compass/css3";
@import url(http://fonts.googleapis.com/css?family=Arvo:400,700,400italic,700italic);
@import url("http://fonts.googleapis.com/css?family=Open+Sans:300italic,400italic,600italic,700italic,400,700,600,300");
@import "foo,bar", url(bar,baz), 'bar,foo';
"""

        compiler.compass_enabled = MagicMock()
        compiler.compass_enabled.return_value = False

        expected = [
            "bar,foo",
            "compass",
            "compass.scss",
            "compass/css3",
            "foo",
            "foo,bar",
            "foo.scss",
            "rounded-corners",
            "text-shadow",
        ]
        self.assertEqual(
            compiler.find_imports(source),
            expected
        )

        compiler.compass_enabled.return_value = True
        expected = [
            "bar,foo",
            "foo",
            "foo,bar",
            "foo.scss",
            "rounded-corners",
            "text-shadow",
        ]
        self.assertEqual(
            compiler.find_imports(source),
            expected
        )

    def test_locate_imported_file(self):
        compiler = SCSS()
        with patch("os.path.exists") as mocked_os_path_exist:

            root = os.path.dirname(__file__)

            existing_files = set()
            for f in ("A/B.scss", "A/_C.scss", "D.scss"):
                existing_files.add(os.path.join(root, "static", normalize_path(f)))

            mocked_os_path_exist.side_effect = lambda x: x in existing_files

            self.assertEqual(
                compiler.locate_imported_file("A", "B.scss"),
                "A/B.scss"
            )
            self.assertEqual(
                compiler.locate_imported_file("A", "C"),
                "A/_C.scss"
            )
            self.assertEqual(
                compiler.locate_imported_file("E", "../D"),
                "D.scss"
            )
            self.assertEqual(
                compiler.locate_imported_file("E", "../A/B.scss"),
                "A/B.scss"
            )
            self.assertEqual(
                compiler.locate_imported_file("", "D.scss"),
                "D.scss"
            )
            self.assertRaises(
                StaticCompilationError,
                lambda: compiler.locate_imported_file("", "Z.scss")
            )

    def test_find_dependencies(self):
        compiler = SCSS()
        files = {
            "A.scss": "@import 'B/C.scss';",
            "B/C.scss": "@import '../E';",
            "_E.scss": "p {color: red;}",
            "compass-import.scss": '@import "compass"',
        }
        compiler.get_source = MagicMock(side_effect=lambda x: files[x])

        root = os.path.dirname(__file__)

        existing_files = set()
        for f in files:
            existing_files.add(os.path.join(root, "static", normalize_path(f)))

        with patch("os.path.exists") as mocked_os_path_exist:
            mocked_os_path_exist.side_effect = lambda x: x in existing_files

            self.assertEqual(
                compiler.find_dependencies("A.scss"),
                ["B/C.scss", "_E.scss"]
            )
            self.assertEqual(
                compiler.find_dependencies("B/C.scss"),
                ["_E.scss"]
            )
            self.assertEqual(
                compiler.find_dependencies("_E.scss"),
                []
            )

    def test_scss_templatetag(self):
        template = get_template_from_string("""{% load scss %}{% scss "dummy.scss" %}""")
        with patch("static_precompiler.templatetags.scss.compiler") as mocked_compiler:
            mocked_compiler.compile = MagicMock(return_value="dummy.css")
            self.assertEqual(
                template.render(Context({})),
                "dummy.css",
            )

    def test_inlinescss_templatetag(self):
        template = get_template_from_string("""{% load scss %}{% inlinescss %}source{% endinlinescss %}""")
        with patch("static_precompiler.templatetags.scss.InlineSCSSNode.compiler") as mocked_compiler:
            mocked_compiler.compile_source = MagicMock(return_value="compiled")
            self.assertEqual(
                template.render(Context({})),
                "compiled",
            )

    def test_compass(self):
        compiler = SCSS()

        self.assertEqual(
            fix_line_breaks(compiler.compile_file("test-compass.scss")),
            "p {\n  background: url('/static/images/test.png'); }\n"
        )

    def test_compass_import(self):
        compiler = SCSS()

        with patch.object(compiler, "compass_enabled", return_value=True):
            self.assertEqual(
                fix_line_breaks(compiler.compile_file("styles/test-compass-import.scss")),
                ".round-corners {\n  -webkit-border-radius: 4px 4px;\n  -moz-border-radius: 4px / 4px;\n  border-radius: 4px / 4px; }\n"
            )

        with patch.object(compiler, "compass_enabled", return_value=False):
            self.assertRaises(StaticCompilationError, lambda: compiler.compile_file("styles/test-compass-import.scss"))


class SASSTestCase(unittest.TestCase):

    def test_is_supported(self):
        compiler = SASS()
        self.assertEqual(compiler.is_supported("dummy"), False)
        self.assertEqual(compiler.is_supported("dummy.sass"), True)

    def test_get_output_filename(self):
        compiler = SASS()
        self.assertEqual(compiler.get_output_filename("dummy.sass"), "dummy.css")
        self.assertEqual(
            compiler.get_output_filename("dummy.sass.sass"),
            "dummy.sass.css"
        )

    def test_compile_file(self):
        compiler = SASS()

        self.assertEqual(
            fix_line_breaks(compiler.compile_file("styles/test.sass")),
            "p {\n  font-size: 15px; }\n  p a {\n    color: red; }\n"
        )

    def test_compile_source(self):
        compiler = SASS()

        self.assertEqual(
            fix_line_breaks(compiler.compile_source("p\n  font-size: 15px")),
            "p {\n  font-size: 15px; }\n"
        )

        self.assertRaises(
            StaticCompilationError,
            lambda: compiler.compile_source('invalid syntax')
        )

    def test_find_imports(self):
        compiler = SASS()
        source = """@import foo.sass
@import "foo.css"
@import foo screen
@import "http://foo.com/bar"
@import url(foo)
@import "rounded-corners", text-shadow
@import "foo,bar", url(bar,baz), 'bar,foo',bar screen, projection"""
        expected = [
            "bar",
            "bar,foo",
            "foo",
            "foo,bar",
            "foo.sass",
            "rounded-corners",
            "text-shadow",
        ]
        self.assertEqual(
            compiler.find_imports(source),
            expected
        )

    def test_sass_templatetag(self):
        template = get_template_from_string("""{% load sass %}{% sass "dummy.sass" %}""")
        with patch("static_precompiler.templatetags.sass.compiler") as mocked_compiler:
            mocked_compiler.compile = MagicMock(return_value="dummy.css")
            self.assertEqual(
                template.render(Context({})),
                "dummy.css",
            )

    def test_inlinesass_templatetag(self):
        template = get_template_from_string("""{% load sass %}{% inlinesass %}source{% endinlinesass %}""")
        with patch("static_precompiler.templatetags.sass.InlineSASSNode.compiler") as mocked_compiler:
            mocked_compiler.compile_source = MagicMock(return_value="compiled")
            self.assertEqual(
                template.render(Context({})),
                "compiled",
            )


def suite():
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    test_suite.addTest(loader.loadTestsFromTestCase(SASSTestCase))
    test_suite.addTest(loader.loadTestsFromTestCase(SCSSTestCase))
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = test_static_precompiler_watch
from static_precompiler.management.commands.static_precompiler_watch import get_watched_dirs
from static_precompiler.settings import STATIC_ROOT
import os
import unittest


class StaticPrecompilerWatchTestCase(unittest.TestCase):

    def test_get_watched_dirs(self):

        self.assertEqual(get_watched_dirs(), sorted([
            os.path.join(os.path.dirname(__file__), "staticfiles_dir"),
            os.path.join(os.path.dirname(__file__), "staticfiles_dir_with_prefix"),
            STATIC_ROOT
        ]))


def suite():
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    test_suite.addTest(loader.loadTestsFromTestCase(StaticPrecompilerWatchTestCase))
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = test_url_converter
# coding: utf-8
from mock import MagicMock
from static_precompiler.utils import URLConverter
import unittest


class URLConverterTestCase(unittest.TestCase):

    def test_convert_url(self):
        converter = URLConverter()
        self.assertEqual(
            converter.convert_url("http://dummy.jpg", "styles/"),
            "http://dummy.jpg"
        )
        self.assertEqual(
            converter.convert_url("https://dummy.jpg", "styles/"),
            "https://dummy.jpg"
        )
        self.assertEqual(
            converter.convert_url("/dummy.jpg", "styles/"),
            "/dummy.jpg"
        )
        self.assertEqual(
            converter.convert_url("data:abc", "styles/"),
            "data:abc"
        )
        self.assertEqual(
            converter.convert_url("dummy.jpg", "styles/"),
            "/static/styles/dummy.jpg"
        )
        self.assertEqual(
            converter.convert_url("./dummy.jpg", "styles/"),
            "/static/styles/dummy.jpg"
        )
        self.assertEqual(
            converter.convert_url("../images/dummy.jpg", "styles/"),
            "/static/images/dummy.jpg"
        )

    def test_convert(self):
        converter = URLConverter()
        converter.convert_url = MagicMock(return_value="spam.jpg")
        self.assertEqual(
            converter.convert("p {\n  background-url: url(ham.jpg);\n}", ""),
            "p {\n  background-url: url('spam.jpg');\n}"
        )
        self.assertEqual(
            converter.convert('p {\n  background-url: url("ham.jpg");\n}', ""),
            "p {\n  background-url: url('spam.jpg');\n}"
        )
        self.assertEqual(
            converter.convert("p {\n  background-url: url('ham.jpg');\n}", ""),
            "p {\n  background-url: url('spam.jpg');\n}"
        )
        self.assertEqual(
            converter.convert(""".external_link:first-child:before {
  content: "Zobacz także:";
  background: url(картинка.png); }
""", ""),
            """.external_link:first-child:before {
  content: "Zobacz także:";
  background: url('spam.jpg'); }
""")


def suite():
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    test_suite.addTest(loader.loadTestsFromTestCase(URLConverterTestCase))
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = utils
from hashlib import md5
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.templatetags.static import static
from django.utils.encoding import smart_str, smart_bytes
from django.utils.importlib import import_module
# noinspection PyUnresolvedReferences
from six.moves.urllib import parse as urllib_parse
from static_precompiler.exceptions import UnsupportedFile
from static_precompiler.settings import MTIME_DELAY, POSIX_COMPATIBLE, COMPILERS, \
    STATIC_URL, PREPEND_STATIC_URL
import os
import re
import socket
import subprocess


def normalize_path(posix_path):
    """ Convert posix style path to OS-dependent path.
    """
    if POSIX_COMPATIBLE:
        return posix_path
    return os.path.join(*posix_path.split("/"))


def fix_line_breaks(text):
    """ Convert Win line breaks to Unix
    """
    return text.replace("\r\n", "\n")


def get_hexdigest(plaintext, length=None):
    digest = md5(smart_bytes(plaintext)).hexdigest()
    if length:
        return digest[:length]
    return digest


def get_cache_key(key):
    return "django_coffescript.{0}.{1}".format(socket.gethostname(), key)


def get_mtime_cachekey(filename):
    return get_cache_key("mtime.{0}".format(get_hexdigest(filename)))


def get_mtime(filename):
    if MTIME_DELAY:
        key = get_mtime_cachekey(filename)
        mtime = cache.get(key)
        if mtime is None:
            mtime = os.path.getmtime(filename)
            cache.set(key, mtime, MTIME_DELAY)
        return mtime
    return os.path.getmtime(filename)


#noinspection PyShadowingBuiltins
def run_command(args, input=None, cwd=None):

    popen_kwargs = dict(
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if cwd is not None:
        popen_kwargs["cwd"] = cwd

    if input is not None:
        popen_kwargs["stdin"] = subprocess.PIPE

    if os.name == "nt":
        popen_kwargs["shell"] = True

    p = subprocess.Popen(args, **popen_kwargs)

    if input:
        input = smart_bytes(input)

    output, error = p.communicate(input)

    return smart_str(output), smart_str(error)


class URLConverter(object):

    URL_PATTERN = re.compile(r"url\(([^\)]+)\)")

    @staticmethod
    def convert_url(url, source_dir):
        assert source_dir[-1] == "/"
        url = url.strip(' \'"')
        if url.startswith(('http://', 'https://', '/', 'data:')):
            return url
        return urllib_parse.urljoin(STATIC_URL, urllib_parse.urljoin(source_dir, url))

    def convert(self, content, path):
        source_dir = os.path.dirname(path)
        if not source_dir.endswith("/"):
            source_dir += "/"
        return self.URL_PATTERN.sub(
            lambda matchobj: "url('{0}')".format(
                self.convert_url(matchobj.group(1), source_dir)
            ),
            content
        )


url_converter = URLConverter()


def convert_urls(content, path):
    return url_converter.convert(content, path)


compilers = None


def get_compilers():
    global compilers

    if compilers is None:
        compilers = []
        for compiler_path in COMPILERS:
            try:
                compiler_module, compiler_classname = compiler_path.rsplit('.', 1)
            except ValueError:
                raise ImproperlyConfigured('{0} isn\'t a compiler module'.format(compiler_path))
            try:
                mod = import_module(compiler_module)
            except ImportError as e:
                raise ImproperlyConfigured('Error importing compiler {0}: "{1}"'.format(compiler_module, e))
            try:
                compiler_class = getattr(mod, compiler_classname)
            except AttributeError:
                raise ImproperlyConfigured('Compiler module "{0}" does not define a "{1}" class'.format(compiler_module, compiler_classname))

            compilers.append(compiler_class())

    return compilers


def compile_static(path):

    for compiler in get_compilers():
        if compiler.is_supported(path):
            return compiler.compile(path)

    raise UnsupportedFile("The source file '{0}' is not supported by any of available compilers.".format(path))


def compile_static_lazy(path):

    for compiler in get_compilers():
        if compiler.is_supported(path):
            return compiler.compile_lazy(path)

    raise UnsupportedFile("The source file '{0}' is not supported by any of available compilers.".format(path))


def prepend_static_url(path):
    
    if PREPEND_STATIC_URL:
        path = static(path)
    return path

########NEW FILE########
