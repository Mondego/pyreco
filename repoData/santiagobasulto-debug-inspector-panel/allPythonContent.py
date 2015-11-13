__FILENAME__ = console_utils
MINIMUM_WIDTH = 22
TITLE = "Debug Info"
RIGHT_PADDING = 2


def console_debug(record):
    val = generate_line("Value", record.value)
    clas = generate_line("Class", record.class_name)
    module_name = generate_line("Module Name: ", record.module_name)
    width = longest_line_width([val, clas, module_name]) + RIGHT_PADDING
    print_title(width)
    print_complete(val, width)
    print_complete(clas, width)
    print_complete(module_name, width)
    print_ending(width)


def print_title(width):
    free_space = width - (len(TITLE) + 2)
    to_left = free_space / 2
    if free_space % 2 == 0:
        to_right = to_left
    else:
        to_right = to_left - 1
    print "%s %s %s" % ("#" * to_left, TITLE, "#" * to_right)


def print_complete(line, width):
    completed_line = line
    if len(line) < width:
        to_complete = width - len(line) - 1
        completed_line = "%s%s%s" % (line, " " * to_complete, "#")
    print completed_line


def print_ending(width):
    print "#" * width


def generate_line(title, value):
    return "# %s: %s" % (title, value)


def longest_line_width(lines):
    max_width = MINIMUM_WIDTH
    for l in lines:
        if len(l) > max_width:
            max_width = len(l)
    return max_width

########NEW FILE########
__FILENAME__ = inspector
from django.conf import settings
from django.template.loader import render_to_string
from debug_toolbar.panels import DebugPanel
from console_utils import console_debug
import inspect
try:
    import threading
except ImportError:
    threading = None

CONSTANT_ID = 1
RECORDS = {}


class DebugRecord(object):
    def __init__(self, *args, **kwargs):
        pass


def clear_record_for_current_thread():
    if threading is None:
        t_id = CONSTANT_ID
    else:
        t_id = threading.currentThread()
    RECORDS[t_id] = []


def get_record_for_current_thread():
    if threading is None:
        t_id = CONSTANT_ID
    else:
        t_id = threading.currentThread()
    if t_id not in RECORDS:
        RECORDS[t_id] = []
    return RECORDS[t_id]


def log_record(record):
    slot = get_record_for_current_thread()
    slot.append(record)


def debug_class(the_class, record):
    """ Adds class and module information
    """
    record.class_name = the_class.__name__
    record.docs = the_class.__doc__
    module = inspect.getmodule(the_class)
    debug_module(module, record)


def debug_module(module, record):
    import __builtin__
    record.source_file = "__builtin__"
    if module != __builtin__:
        record.source_file = inspect.getsourcefile(module)
    record.module_name = module.__name__


def debug_default(value, record):
    __class = value.__class__
    debug_class(__class, record)


def debug(value, console=True):
    if not hasattr(settings, 'DEBUG') or settings.DEBUG is False:
        return
    stack = inspect.stack()[1]
    frm = stack[0]
    print frm.f_locals
    record = DebugRecord()
    record.globals = frm.f_globals
    record.locals = frm.f_locals
    record.value = str(value)
    record.invoked = {}
    record.invoked['file'] = stack[1]
    record.invoked['line'] = stack[2]
    record.invoked['function'] = stack[3]

    if inspect.isclass(value):
        debug_class(value, record)
    elif inspect.ismodule(value):
        debug_module(value, record)
    else:
        debug_default(value, record)

    record.dir = dir(record)
    log_record(record)
    if console:
        console_debug(record)


class InspectorPanel(DebugPanel):

    name = 'InspectorPanel'
    template = 'inspector.html'
    has_content = True

    def __init__(self, *args, **kwargs):
        super(InspectorPanel, self).__init__(*args, **kwargs)
        clear_record_for_current_thread()

    def nav_title(self):
        return 'Inspector Panel'

    def nav_subtitle(self):
        records = get_record_for_current_thread()
        return "%s values to debug" % len(records)

    def title(self):
        return 'All values to debug'

    def url(self):
        return ''

    def content(self):

        context = self.context.copy()

        records = get_record_for_current_thread()
        context.update({
            'records': records,
            'count': len(records)
        })

        return render_to_string(self.template, context)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase


class TestVarName(TestCase):

    def test_tonto(self):
        print "Hello world"

########NEW FILE########
__FILENAME__ = runtests
import os
import sys
from django.conf import settings

if not settings.configured:
    settings_dict = dict(
        INSTALLED_APPS=(
            #'django.contrib.contenttypes',
            'inspector_panel',
            'inspector_panel.tests',
            ),
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3"
                }
            },
        )

    settings.configure(**settings_dict)


def runtests(*test_args):
    if not test_args:
        test_args = ['tests']

    parent = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, parent)

    from django.test.simple import DjangoTestSuiteRunner
    failures = DjangoTestSuiteRunner(
        verbosity=1, interactive=True, failfast=False).run_tests(test_args)
    sys.exit(failures)

########NEW FILE########
