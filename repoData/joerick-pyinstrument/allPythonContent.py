__FILENAME__ = settings
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

DEBUG = True
TEMPLATE_DEBUG = True

SECRET_KEY = 'qg7_r+b@)(--as*(4ls$j$$(9i(pl_@y$g0j0r+!=@&$he(+o%'

ROOT_URLCONF = 'django_test.urls'
WSGI_APPLICATION = 'django_test.wsgi.application'

MIDDLEWARE_CLASSES = (
    'pyinstrument.middleware.ProfilerMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'django_test.views.hello_world'),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse

def hello_world(request):
    return HttpResponse('Hello, world!')

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_test.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = middleware
from django.http import HttpResponse
from django.conf import settings
from pyinstrument import Profiler
from pyinstrument.profiler import NotMainThreadError

not_main_thread_message = (
    'pyinstrument can only be used on the main thread. Run your server process in single-threaded '
    'mode. \n\nWith the built-in server, you can do this with '
    '\n./manage.py runserver --nothreading --noreload')


class ProfilerMiddleware(object):
    def __init__(self):
        self.profiler = None

    def process_request(self, request):
        if getattr(settings, 'PYINSTRUMENT_URL_ARGUMENT', 'profile') in request.GET:
            self.profiler = Profiler()
            try:
                self.profiler.start()
            except NotMainThreadError:
                raise NotMainThreadError(not_main_thread_message)
                self.profiler = None


    def process_response(self, request, response):
        if self.profiler:
            try:
                self.profiler.stop()

                return HttpResponse(self.profiler.output_html())
            except NotMainThreadError:
                raise NotMainThreadError(not_main_thread_message)
            finally:
                self.profiler = None
        else:
            return response

########NEW FILE########
__FILENAME__ = profiler
# -*- coding: utf-8 -*-
import sys
import os
import timeit
import signal
from collections import deque
from operator import methodcaller

timer = timeit.default_timer


class NotMainThreadError(Exception):
    '''pyinstrument must be used on the main thread in signal mode'''
    def __init__(self, message=''):
        super(NotMainThreadError, self).__init__(message or NotMainThreadError.__doc__)


class SignalUnavailableError(Exception):
    '''pyinstrument uses signal.SIGALRM in signal mode, which is not available on your system.

    You can pass the argument 'use_signal=False' to run in setprofile mode.'''
    def __init__(self, message=''):
        super(SignalUnavailableError, self).__init__(message or SignalUnavailableError.__doc__)


class Profiler(object):
    def __init__(self, use_signal=True):
        if use_signal:
            try:
                signal.SIGALRM
            except AttributeError:
                raise SignalUnavailableError()

        self.interval = 0.001
        self.last_profile_time = 0
        self.stack_self_time = {}
        self.use_signal = use_signal

    def start(self):
        self.last_profile_time = timer()

        if self.use_signal:
            try:
                signal.signal(signal.SIGALRM, self._signal)
            except ValueError:
                raise NotMainThreadError()

            signal.setitimer(signal.ITIMER_REAL, self.interval, 0.0)
        else:
            sys.setprofile(self._profile)

    def stop(self):
        if self.use_signal:
            signal.setitimer(signal.ITIMER_REAL, 0.0, 0.0)

            try:
                signal.signal(signal.SIGALRM, signal.SIG_IGN)
            except ValueError:
                raise NotMainThreadError()
        else:
            sys.setprofile(None)

    def _signal(self, signum, frame):
        now = timer()
        time_since_last_signal = now - self.last_profile_time

        self._record(frame, time_since_last_signal)

        signal.setitimer(signal.ITIMER_REAL, self.interval, 0.0)
        self.last_profile_time = now

    def _profile(self, frame, event, arg):
        now = timer()
        time_since_last_signal = now - self.last_profile_time

        if time_since_last_signal < self.interval:
            return

        if event == 'call':
            frame = frame.f_back

        self._record(frame, time_since_last_signal)

        self.last_profile_time = now

    def _record(self, frame, time):
        stack = self._call_stack_for_frame(frame)
        self.stack_self_time[stack] = self.stack_self_time.get(stack, 0) + time

    def _call_stack_for_frame(self, frame):
        result_list = deque()

        while frame is not None:
            result_list.appendleft(self._identifier_for_frame(frame))
            frame = frame.f_back

        return tuple(result_list)

    def _identifier_for_frame(self, frame):
        return '%s\t%s:%i' % (frame.f_code.co_name, frame.f_code.co_filename, frame.f_code.co_firstlineno)

    def root_frame(self):
        """
        Returns the parsed results in the form of a tree of Frame objects
        """
        if not hasattr(self, '_root_frame'):
            self._root_frame = Frame()

            # define a recursive function that builds the hierarchy of frames given the
            # stack of frame identifiers
            def frame_for_stack(stack):
                if len(stack) == 0:
                    return self._root_frame

                parent = frame_for_stack(stack[:-1])
                frame_name = stack[-1]

                if not frame_name in parent.children_dict:
                    parent.add_child(Frame(frame_name, parent))

                return parent.children_dict[frame_name]

            for stack, self_time in self.stack_self_time.iteritems():
                frame_for_stack(stack).self_time = self_time

        return self._root_frame

    def first_interesting_frame(self):
        """ 
        Traverse down the frame hierarchy until a frame is found with more than one child
        """
        frame = self.root_frame()

        while len(frame.children) <= 1:
            if frame.children:
                frame = frame.children[0]
            else:
                # there are no branches
                return self.root_frame()

        return frame

    def starting_frame(self, root=False):
        if root:
            return self.root_frame()
        else:
            return self.first_interesting_frame()

    def output_text(self, root=False, unicode=False, color=False):
        return self.starting_frame(root=root).as_text(unicode=unicode, color=color)

    def output_html(self, root=False):
        resources_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources/')

        with open(os.path.join(resources_dir, 'style.css')) as f:
            css = f.read()

        with open(os.path.join(resources_dir, 'profile.js')) as f:
            js = f.read()

        with open(os.path.join(resources_dir, 'jquery-1.11.0.min.js')) as f:
            jquery_js = f.read()

        body = self.starting_frame(root).as_html()

        page = '''
            <html>
            <head>
                <style>{css}</style>
                <script>{jquery_js}</script>
            </head>
            <body>
                {body}
                <script>{js}</script>
            </body>
            </html>'''.format(css=css, js=js, jquery_js=jquery_js, body=body)

        return page


class Frame(object):
    """
    Object that represents a stack frame in the parsed tree
    """
    def __init__(self, identifier='', parent=None):
        self.identifier = identifier
        self.parent = parent
        self.children_dict = {}
        self.self_time = 0

    @property
    def function(self):
        if self.identifier:
            return self.identifier.split('\t')[0]

    @property
    def code_position(self):
        if self.identifier:
            return self.identifier.split('\t')[1]

    @property
    def file_path(self):
        if self.identifier:
            return self.code_position.split(':')[0]

    @property
    def line_no(self):
        if self.identifier:
            return int(self.code_position.split(':')[1])

    @property
    def file_path_short(self):
        """ Return the path resolved against the closest entry in sys.path """
        if not hasattr(self, '_file_path_short'):
            if self.file_path:
                result = None

                for path in sys.path:
                    candidate = os.path.relpath(self.file_path, path)
                    if not result or (len(candidate.split('/')) < len(result.split('/'))):
                        result = candidate

                self._file_path_short = result
            else: 
                self._file_path_short = None

        return self._file_path_short

    @property
    def code_position_short(self):
        if self.identifier:
            return '%s:%i' % (self.file_path_short, self.line_no)

    # stylistically I'd rather this was a property, but using @property appears to use twice
    # as many stack frames, so I'm forced into using a function since this method is recursive
    # down the call tree.
    def time(self):
        if not hasattr(self, '_time'):
            # can't use a sum(<generator>) expression here sadly, because this method
            # recurses down the call tree, and the generator uses an extra stack frame,
            # meaning we hit the stack limit when the profiled code is 500 frames deep.
            self._time = self.self_time

            for child in self.children:
                self._time += child.time()

        return self._time

    @property
    def proportion_of_parent(self):
        if not hasattr(self, '_proportion_of_parent'):
            if self.parent and self.time():
                try:
                    self._proportion_of_parent = self.time() / self.parent.time()
                except ZeroDivisionError:
                    self._proportion_of_parent = float('nan')
            else:
                self._proportion_of_parent = 1.0

        return self._proportion_of_parent

    @property
    def proportion_of_total(self):
        if not hasattr(self, '_proportion_of_total'):
            if not self.parent:
                self._proportion_of_total = 1.0
            else:
                self._proportion_of_total = self.parent.proportion_of_total * self.proportion_of_parent

        return self._proportion_of_total

    @property
    def children(self):
        return self.children_dict.values()

    @property
    def sorted_children(self):
        if not hasattr(self, '_sorted_children'):
            self._sorted_children = sorted(self.children, key=methodcaller('time'), reverse=True)

        return self._sorted_children

    def add_child(self, child):
        self.children_dict[child.identifier] = child

    def as_text(self, indent=u'', child_indent=u'', unicode=False, color=False):
        colors = colors_enabled if color else colors_disabled
        time_str = '{:.3f}'.format(self.time())

        if color:
            time_str = self._ansi_color_for_time() + time_str + colors.end

        result = u'{indent}{time_str} {function}  {c.faint}{code_position}{c.end}\n'.format(
            indent=indent,
            time_str=time_str,
            function=self.function,
            code_position=self.code_position_short,
            c=colors_enabled if color else colors_disabled)

        children = filter(lambda f: f.proportion_of_total > 0.01, self.sorted_children)

        if children:
            last_child = children[-1]

        for child in children:
            if child is not last_child:
                c_indent = child_indent + (u'├─ ' if unicode else '|- ')
                cc_indent = child_indent + (u'│  ' if unicode else '|  ')
            else:
                c_indent = child_indent + (u'└─ ' if unicode else '`- ')
                cc_indent = child_indent + u'   '
            result += child.as_text(indent=c_indent,
                                    child_indent=cc_indent,
                                    unicode=unicode,
                                    color=color)

        return result

    def as_html(self):
        start_collapsed = all(child.proportion_of_total < 0.1 for child in self.children)

        extra_class = ''
        extra_class += 'collapse ' if start_collapsed else ''
        extra_class += 'no_children ' if not self.children else ''

        result = '''<div class="frame {extra_class}" data-time="{time}" date-parent-time="{parent_proportion}">
            <div class="frame-info">
                <span class="time">{time:.3f}s</span>
                <span class="total-percent">{total_proportion:.1%}</span>
                <!--<span class="parent-percent">{parent_proportion:.1%}</span>-->
                <span class="function">{function}</span>
                <span class="code-position">{code_position}</span>
            </div>'''.format(
                time=self.time(),
                function=self.function,
                code_position=self.code_position_short,
                parent_proportion=self.proportion_of_parent, 
                total_proportion=self.proportion_of_total,
                extra_class=extra_class)

        result += '<div class="frame-children">'

        for child in self.sorted_children:
            result += child.as_html()

        result += '</div></div>'

        return result

    def _ansi_color_for_time(self):
        colors = colors_enabled
        if self.proportion_of_total > 0.6:
            return colors.red
        elif self.proportion_of_total > 0.2:
            return colors.yellow
        elif self.proportion_of_total > 0.05:
            return colors.green
        else:
            return colors.bright_green + colors.faint

    def __repr__(self):
        return 'Frame(identifier=%s, time=%f, children=%r)' % (self.identifier, self.time(), self.children)


class colors_enabled:
    red = '\033[31m'
    green = '\033[32m'
    yellow = '\033[33m'
    blue = '\033[34m'
    cyan = '\033[36m'
    bright_green = '\033[92m'

    bold = '\033[1m'
    faint = '\033[2m'

    end = '\033[0m'


class colors_disabled:
    def __getattr__(self, key):
        return ''

colors_disabled = colors_disabled()

########NEW FILE########
__FILENAME__ = __main__
from optparse import OptionParser
import sys
import os
import codecs
from pyinstrument import Profiler

def main():
    usage = "usage: %prog [-h] [-o output_file_path] scriptfile [arg] ..."
    parser = OptionParser(usage=usage)
    parser.allow_interspersed_args = False
    parser.add_option('', '--html',
        dest="output_html", action='store_true',
        help="output HTML instead of text", default=False)
    parser.add_option('-o', '--outfile',
        dest="outfile", action='store', 
        help="save stats to <outfile>", default=None)

    if not sys.argv[1:]:
        parser.print_usage()
        sys.exit(2)

    (options, args) = parser.parse_args()
    sys.argv[:] = args

    if len(args) > 0:
        progname = args[0]
        sys.path.insert(0, os.path.dirname(progname))

        with open(progname, 'rb') as fp:
            code = compile(fp.read(), progname, 'exec')
        globs = {
            '__file__': progname,
            '__name__': '__main__',
            '__package__': None,
        }

        profiler = Profiler()
        profiler.start()

        try:
            exec code in globs, None
        except SystemExit, KeyboardInterrupt:
            pass

        profiler.stop()

        if options.outfile:
            f = codecs.open(options.outfile, 'w', 'utf-8')
            unicode = True
            color = False
        else:
            f = sys.stdout
            unicode = stdout_supports_unicode()
            color = stdout_supports_color()

        if options.output_html:
            f.write(profiler.output_html())
        else:
            f.write(profiler.output_text(unicode=unicode, color=color))

        f.close()
    else:
        parser.print_usage()
    return parser

def stdout_supports_color():
    """
    Returns True if the running system's terminal supports color, and False
    otherwise.

    Borrowed from Django
    https://github.com/django/django/blob/master/django/core/management/color.py
    """
    plat = sys.platform
    supported_platform = plat != 'Pocket PC' and (plat != 'win32' or
                                                  'ANSICON' in os.environ)

    is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    if not supported_platform or not is_a_tty:
        return False
    return True

def stdout_supports_unicode():
    is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    utf_in_locale = 'utf' in os.environ.get('LC_CTYPE', '').lower()

    return is_a_tty and utf_in_locale

if __name__ == '__main__':
    main()

########NEW FILE########
