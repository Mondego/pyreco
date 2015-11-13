__FILENAME__ = admin
# -*- coding: utf-8 -*-

# django-lint -- Static analysis tool for Django projects and applications
# Copyright (C) 2008-2009 Chris Lamb <chris@chris-lamb.co.uk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pylint.interfaces import IASTNGChecker
from pylint.checkers import BaseChecker

from .utils import nodeisinstance

class AdminChecker(BaseChecker):
    __implements__ = IASTNGChecker

    name = 'django_admin'
    msgs = {
        'W8020': (
            'Admin class %r not in admin.py',
            'loldongs',),
    }

    ADMIN_BASE_CLASSES = (
        'django.contrib.admin.options.ModelAdmin',
    )

    def visit_module(self, node):
        self.module = node

    def leave_class(self, node):
        if not nodeisinstance(node, self.ADMIN_BASE_CLASSES):
            return

        if not self.module.file.endswith('admin.py'):
            # Admin classes not in an app's admin.py can cause circular import
            # problems throughout a project.
            #
            # This is because registering an admin class implies a call to
            # models.get_apps() which attempts to import *every* models.py in
            # the project.
            #
            # Whilst your project should probably not have significant
            # inter-app dependencies, importing every possible models.py does
            # not help the situation and can cause ImportError when models are
            # loaded in different scenarios.
            self.add_message('W8020', node=node, args=(node.name,))

########NEW FILE########
__FILENAME__ = model_fields
# -*- coding: utf-8 -*-

# django-lint -- Static analysis tool for Django projects and applications
# Copyright (C) 2008-2009 Chris Lamb <chris@chris-lamb.co.uk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from logilab import astng

from pylint.interfaces import IASTNGChecker
from pylint.checkers import BaseChecker
from pylint.checkers.utils import safe_infer

from utils import is_model

class ModelFieldsChecker(BaseChecker):
    __implements__ = IASTNGChecker

    name = 'django_model_fields'
    msgs = {
        'W6000': ('%s: Nullable CharField or TextField', ''),
        'W6001': (
            "%s: Naive tree structure implementation using ForeignKey('self')",
        ''),
        'W6002': (
            'Model has too many fields (%d/%d); consider splitting model',
        ''),
        'W6003': ('Model has no fields', ''),
        'W6004': ('%s: Field is nullable but blank=False', ''),
        'W6005': ('%s: uses brittle unique_for_%s', ''),
        'W6006': ('%s: ForeignKey missing related_name', ''),
        'W6007': (
            '%s: CharField with huge (%d/%d) max_length instead of TextField',
        ''),
        'W6008': ('%s: Uses superceded auto_now or auto_now_add', ''),
        'W6009': (
            '%s: NullBooleanField instead of BooleanField with null=True',
        ''),
        'W6010': ('%s: %s has database-dependent limits', ''),
        'W6011': ('%s: URLField uses verify_exists=True default', ''),
        'W6012': (
            '%s: BooleanField with default=True will not be reflected in database',
        ''),
        'W6013': (
            '%s: Unique ForeignKey constraint better modelled as OneToOneField',
        ''),
        'W6014': ('%s: primary_key=True should imply unique=True', ''),
        'W6015': ('%s: %s=False is implicit', ''),
        'W6016': ('%s: Nullable ManyToManyField makes no sense', ''),
    }

    options = (
        ('max-model-fields', {
            'default': 20,
            'type': 'int',
            'metavar': '<int>',
            'help': 'Maximum number of fields for a model',
        }),
        ('max-charfield-length', {
            'default': 512,
            'type': 'int',
            'metavar': '<int>',
            'help': 'Maximum size of max_length on a CharField',
        }),
    )

    def visit_module(self, node):
        self.field_count = 0

    def leave_class(self, node):
        if not is_model(node):
            return

        if is_model(node, check_base_classes=False) and self.field_count == 0:
            self.add_message('W6003', node=node)
        elif self.field_count > self.config.max_model_fields:
            self.add_message('W6002', node=node,
                args=(self.field_count, self.config.max_model_fields))

        self.field_count = 0

    def visit_callfunc(self, node):
        if not is_model(node.frame()):
            # We only care about fields attached to models
            return

        val = safe_infer(node)
        if not val or not val.root().name.startswith('django.db.models.fields'):
            # Not a field
            return

        assname = '(unknown name)'
        x = node.parent.get_children().next()
        if isinstance(x, astng.AssName):
            assname = x.name

        self.field_count += 1

        # Parse kwargs
        options = dict([(option, None) for option in (
            'null',
            'blank',
            'unique',
            'default',
            'auto_now',
            'primary_key',
            'auto_now_add',
            'verify_exists',
            'related_name',
            'max_length',
            'unique_for_date',
            'unique_for_month',
            'unique_for_year',
        )])

        for arg in node.args:
            if not isinstance(arg, astng.Keyword):
                continue

            for option in options.keys():
                if arg.arg == option:
                    try:
                        options[option] = safe_infer(arg.value).value
                    except AttributeError:
                        # Don't lint this field if we cannot infer everything
                        return

        if not val.name.lower().startswith('null'):
            for option in ('null', 'blank'):
                if options[option] is False:
                    self.add_message('W6015', node=node, args=(assname, option,))

        # Field type specific checks
        if val.name in ('CharField', 'TextField'):
            if options['null']:
                self.add_message('W6000', node=node, args=(assname,))

            if val.name == 'CharField' and \
                    options['max_length'] > self.config.max_charfield_length:
                self.add_message('W6007', node=node, args=(
                    assname,
                    options['max_length'],
                    self.config.max_charfield_length,
                ))

        elif val.name == 'BooleanField':
            if options['default']:
                self.add_message('W6012', node=node, args=(assname,))

        elif val.name == 'ForeignKey':
            val = safe_infer(node.args[0])
            if isinstance(val, astng.Const) and val.value == 'self':
                self.add_message('W6001', node=node, args=(assname,))

            elif not options['related_name']:
                self.add_message('W6006', node=node, args=(assname,))

            if options['primary_key'] and options['unique'] is False:
                self.add_message('W6014', node=node, args=(assname,))
            elif options['primary_key'] or options['unique']:
                self.add_message('W6013', node=node, args=(assname,))

        elif val.name == 'URLField':
            if options['verify_exists'] is None:
                self.add_message('W6011', node=node, args=(assname,))

        elif val.name in ('PositiveSmallIntegerField', 'SmallIntegerField'):
            self.add_message('W6010', node=node, args=(assname, val.name))

        elif val.name == 'NullBooleanField':
            self.add_message('W6009', node=node, args=(assname,))

        elif val.name == 'ManyToManyField':
            if options['null']:
                self.add_message('W6016', node=node, args=(assname,))

        # Generic checks
        if options['null'] and not options['blank']:
            self.add_message('W6004', node=node, args=(assname,))

        if options['auto_now'] or options['auto_now_add']:
            self.add_message('W6008', node=node, args=(assname,))

        for suffix in ('date', 'month', 'year'):
            if options['unique_for_%s' % suffix]:
                self.add_message('W6005', node=node, args=(assname, suffix))

########NEW FILE########
__FILENAME__ = model_methods
# -*- coding: utf-8 -*-

# django-lint -- Static analysis tool for Django projects and applications
# Copyright (C) 2008-2009 Chris Lamb <chris@chris-lamb.co.uk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os.path

from logilab import astng

from pylint.interfaces import IASTNGChecker
from pylint.checkers import BaseChecker
from pylint.checkers.utils import safe_infer

from utils import is_model

try:
    from itertools import combinations
except ImportError:
    # Python <= 2.5 fallback
    def combinations(iterable, r):
        if r:
            for i, cur in enumerate(iterable):
                for xs in combinations(iterable[:i] + iterable[i + 1:], r - 1):
                    yield [cur] + xs
        else:
            yield []

class ModelMethodsChecker(BaseChecker):
    __implements__ = IASTNGChecker

    name = 'django_model_models'
    msgs = {
        'W8010': (
            'Too many models (%d/%d); consider splitting application',
        '',),
        'W8011': ('Use __unicode__ instead of __str__', '',),
        'W8012': ('Method should come after standard model methods', '',),
        'W8013': ('%s should come before %r', '',),
        'W8015': (
            '%d models have common prefix (%r) - rename or split application',
        '',),
    }

    options = (
        ('max-models', {
            'default': 10,
            'type': 'int',
            'metavar': '<int>',
            'help': 'Maximum number of models per module',
        }),
    )

    def visit_module(self, node):
        self.model_names = []

    def leave_module(self, node):
        if len(self.model_names) >= self.config.max_models:
            self.add_message('W8010', node=node.root(),
                args=(len(self.model_names), self.config.max_models))

        if not self.model_names:
            return

        for names in combinations(self.model_names, 4):
            common = os.path.commonprefix(names)
            if len(common) >= 4:
                # Whitelist a few common names
                if common.lower() in ('abstract',):
                    continue

                # How many actually have this prefix?
                xs = filter(lambda x: x.startswith(common), self.model_names)

                self.add_message('W8015', node=node.root(),
                    args=(len(xs), common,))
                break

    def _visit_django_attribute(self, node, is_method=True):
        try:
            idx = [
                'Meta',
                '__unicode__',
                '__str__',
                'save',
                'delete',
                'get_absolute_url',
            ].index(node.name)

            if self.prev_idx == -1:
                self.add_message('W8012', node=self.prev_node)

            elif idx < self.prev_idx:
                noun = is_method and 'Standard model method' or '"Meta" class'
                self.add_message(
                    'W8013', node=node, args=(noun, self.prev_node.name)
                )

        except ValueError:
            idx = -1

        self.prev_idx = idx
        self.prev_node = node

    def visit_function(self, node):
        if not is_model(node.parent.frame()):
            return

        if node.name == '__str__':
            self.add_message('W8011', node=node)

        self._visit_django_attribute(node)

    def visit_class(self, node):
        if is_model(node):
            self.model_names.append(node.name)
            self.prev_idx = None
            self.prev_node = None

        elif is_model(node.parent.frame()):
            # Nested class
            self._visit_django_attribute(node, is_method=False)

    def visit_assname(self, node):
        if not is_model(node.parent.frame()):
            return

        if self.prev_idx >= 0:
            self.add_message('W8013', node=node, args=(
                '%r assignment' % node.name, self.prev_node.name,
            ))

    def leave_class(self, node):
        if node.name == 'Meta' and is_model(node.parent.parent):
            # Annotate the model with information from the Meta class
            try:
                val = safe_infer(node.locals['abstract'][-1]).value
                if val is True:
                    node.parent.parent._django_abstract = True
            except KeyError:
                pass
            return

        if not is_model(node):
            return

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-

# django-lint -- Static analysis tool for Django projects and applications
# Copyright (C) 2008-2009 Chris Lamb <chris@chris-lamb.co.uk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from logilab import astng

from pylint.interfaces import IASTNGChecker
from pylint.checkers import BaseChecker
from pylint.checkers.utils import safe_infer

class SettingsChecker(BaseChecker):
    __implements__ = IASTNGChecker

    name = 'django_settings_checker'
    msgs = {
        'W7001': ('Missing required field %r', '',),
        'W7002': ('Empty %r setting', '',),
        'W7003': ('%s after %s', ''),
        'W7005': ('Non-absolute directory %r in TEMPLATE_DIRS', ''),
        'W7006': ('%r in TEMPLATE_DIRS should use forward slashes', ''),
    }

    def leave_module(self, node):
        if node.name.split('.')[-1] != 'settings':
            return

        self.check_required_fields(node)
        self.check_middleware(node)
        self.check_template_dirs(node)

    def check_required_fields(self, node):
        REQUIRED_FIELDS = {
            'DEBUG': bool,
            'TEMPLATE_DEBUG': bool,
            'INSTALLED_APPS': tuple,
            'MANAGERS': tuple,
            'ADMINS': tuple,
            'MIDDLEWARE_CLASSES': tuple,
        }

        for field, req_type in REQUIRED_FIELDS.iteritems():
            if field not in node.locals.keys():
                self.add_message('W7001', args=field, node=node)
                continue

            if req_type is tuple:
                ass = node.locals[field][-1]
                val = safe_infer(ass)

                if val and not val.get_children():
                    self.add_message('W7002', args=field, node=ass)

    def get_constant_values(self, node, key):
        try:
            ass = node.locals[key][-1]
        except KeyError:
            return

        try:
            xs = safe_infer(ass).get_children()
        except AttributeError:
            return

        try:
            xs_iterable = iter(xs)
        except TypeError:
            return

        return [(x, x.value) for x in xs if isinstance(safe_infer(x), astng.Const)]

    def check_middleware(self, node):
        middleware = self.get_constant_values(node, 'MIDDLEWARE_CLASSES')
        if middleware is None:
            return

        relations = ((
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        ), (
            'django.middleware.http.ConditionalGetMiddleware',
            'django.middleware.common.CommonMiddleware',
        ))

        lookup = [y for x, y in middleware]
        node_lookup = dict([(y, x) for x, y in middleware])

        for a, b in relations:
            try:
                if lookup.index(a) > lookup.index(b):
                    self.add_message(
                        'W7003',
                        args=tuple([x.split('.')[-1] for x in (a, b)]),
                        node=node_lookup[a],
                    )
            except ValueError:
                pass

    def check_template_dirs(self, node):
        template_dirs = self.get_constant_values(node, 'TEMPLATE_DIRS')
        if template_dirs is None:
            return

        for dirnode, dirname in template_dirs:
            if not (dirname.startswith('/') or dirname[1:].startswith(':')):
                self.add_message('W7005', args=dirname, node=dirnode)

            if dirname.find('\\') > 0:
                self.add_message('W7006', args=dirname, node=dirnode)

########NEW FILE########
__FILENAME__ = size
# -*- coding: utf-8 -*-

# django-lint -- Static analysis tool for Django projects and applications
# Copyright (C) 2008-2009 Chris Lamb <chris@chris-lamb.co.uk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pylint.interfaces import IASTNGChecker
from pylint.checkers import BaseChecker

class SizeChecker(BaseChecker):
    __implements__ = IASTNGChecker

    name = 'django_size_checker'
    msgs = {
        'W8001': (
            '%r is actually a directory; consider splitting application',
        '',),
    }

    def leave_module(self, node):
        for candidate in ('views', 'models'):
            if not node.name.endswith('.%s' % candidate):
                continue

            if node.file.endswith('__init__.py'):
                # When 'models' is a directory, django.test.simple.run_tests
                # cannot tell the difference between a tests.py module that is
                # raising an ImportError and when it doesn't exist (so it
                # silently discards that app). This is not good!
                self.add_message('W8001', args=node.name, node=node)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

# django-lint -- Static analysis tool for Django projects and applications
# Copyright (C) 2008-2009 Chris Lamb <chris@chris-lamb.co.uk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from logilab import astng

from itertools import chain
from pylint.checkers.utils import safe_infer

def is_model(node, **kwargs):
    return nodeisinstance(node, ('django.db.models.base.Model',), **kwargs)

def nodeisinstance(node, klasses, check_base_classes=True):
    if not isinstance(node, astng.Class):
        return False

    for base in node.bases:
        val = safe_infer(base)
        if not val:
            continue
        if isinstance(val, astng.bases._Yes):
            continue

        nodes = [val]
        if check_base_classes:
            try:
                nodes = chain([val], val.ancestors())
            except TypeError:
                pass

        for node in nodes:
            qual = '%s.%s' % (node.root().name, node.name)
            if qual in klasses:
                return True

    return False

########NEW FILE########
__FILENAME__ = script
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# django-lint -- Static analysis tool for Django projects and applications
# Copyright (C) 2008-2009 Chris Lamb <chris@chris-lamb.co.uk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys

from pylint import checkers, lint
from optparse import OptionParser

from DjangoLint import AstCheckers

def main():
    usage = """ %prog [options] target

    Django Lint is a tool that statically analyses Django projects and
    applications, checking for programming errors and bad code smells. For
    example, it reports nullable "CharField" fields, as well as reporting for
    unspecified options in settings.py.

    The `target` argument is mandatory and can specify either a directory
    containing a Django project, a single application or a single file.
    """.rstrip()

    parser = OptionParser(usage=usage)
    parser.add_option(
        '-r',
        '--reports',
        dest='report',
        action='store_true',
        default=False,
        help='generate report',
    )
    parser.add_option(
        '-p',
        '--pylint',
        dest='pylint',
        action='store_true',
        default=False,
        help='run normal PyLint checks',
    )
    parser.add_option(
        '-e',
        '--errors',
        dest='errors',
        action='store_true',
        default=False,
        help='only show errors',
    )
    parser.add_option(
        '-f',
        '--format',
        dest='outputformat',
        metavar='OUTPUT',
        default='text',
        help='Set the output format. Available formats are text,'
        'parseable, colorized, msvs (visual studio) and html',
    )

    options, args = parser.parse_args()

    try:
        args[0]
    except IndexError:
        args = ['.']

    targets = [os.path.abspath(arg) for arg in args]

    for target in targets:
        if not os.path.exists(target):
            try:
                # Is target a module?
                x = __import__(args[0], locals(), globals(), [], -1)
                target = sys.modules[args[0]].__path__[0]
            except:
                pass

        if not os.path.exists(target):
            raise parser.error(
                "The specified target (%r) does not exist" \
                    % target
            )

        path = target
        while True:
            flag = False
            for django_file in ('manage.py', 'models.py', 'urls.py'):
                if os.path.exists(os.path.join(path, django_file)):
                    sys.path.insert(0, os.path.dirname(path))
                    flag = True
                    break
            if flag:
                break

            path = os.path.dirname(path)

            if path == '/':
                raise parser.error(
                    "The specified target (%r) does not appear to be part of a " \
                    "Django application" % target
                )

    try:
        import django
    except ImportError:
        print >>sys.stderr, "E: Cannot import `django' module, exiting.."
        return 1

    linter = lint.PyLinter()
    linter.set_option('reports', options.report)
    linter.set_option('output-format', options.outputformat)

    if options.pylint:
        checkers.initialize(linter)
        for msg in ('C0111', 'C0301'):
            linter.disable(msg)

    AstCheckers.register(linter)

    if options.errors:
        linter.set_option('disable-msg-cat', 'WCRI')
        linter.set_option('reports', False)
        linter.set_option('persistent', False)

    linter.check(targets)

    return linter.msg_status

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/python
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
# Django settings for django_lint_example project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS_MISSING = ADMINS

DATABASE_ENGINE = ''           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = ''             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

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
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'r_t-fx@9&8nuxf!i!07@@wo-yto%wk=p(-i$(4*612ukhdt4g&'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
)

ROOT_URLCONF = 'django_lint_example.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    'relative/directory',
    'C:\windows\user',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'example',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^django_lint_example/', include('django_lint_example.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/(.*)', admin.site.root),
)

########NEW FILE########
