__FILENAME__ = mcslldb_commands
#!/usr/bin/env python
# encoding: utf-8

import json as json_lib
from os import system
from tempfile import NamedTemporaryFile

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import JavascriptLexer

from mcslldb_helpers import get_value, lldb_command


@lldb_command
def json(debugger, expression):
    # get JSON string
    value = get_value(debugger, expression)
    json_string = value.GetObjectDescription()

    # prettify JSON
    pretty_json_string = json_lib.dumps(json_lib.loads(json_string),
                                        sort_keys=True, indent=4)

    # render HTML with highlighted JSON
    formatter = HtmlFormatter(linenos=True)
    html = """
<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf-8">

        <style>
            {style}
        </style>
    </head>

    <body>
        {body}
    </body>
</html>
    """.format(**{
        'style': formatter.get_style_defs('.highlight'),
        'body': highlight(pretty_json_string, JavascriptLexer(), formatter),
    })

    # save HTML to a temporary file
    with NamedTemporaryFile(delete=False) as f:
        f.write(html)

        # add ".html" extension
        original_path = f.name
        path = original_path + '.html'
        system('mv "%s" "%s"' % (original_path, path))

    # show HTML in Quick Look and delete file at the end
    system('qlmanage -p "%s" > /dev/null && rm "%s" &' % (path, path))

########NEW FILE########
__FILENAME__ = mcslldb_helpers
#!/usr/bin/env python
# encoding: utf-8

from functools import wraps
import shlex
import sys


LLDB_COMMANDS = []


class CommandException(Exception):
    pass


class DummyDebugger(object):

    def HandleCommand(self, s):
        print s


def get_value(debugger, expression):
    target = debugger.GetSelectedTarget()
    process = target.GetProcess()
    thread = process.GetSelectedThread()
    frame = thread.GetSelectedFrame()
    value = frame.EvaluateExpression(expression)

    error_message = str(value.GetError())
    if error_message != 'success':
        raise CommandException(error_message)

    return value


def lldb_command(function):
    r"""
    Decorate command functions.

    Example:

        @lldb_command
        def uppercase(debugger, *args):
            return '\n'.join(x.upper() for x in args)

    Usage:

        (lldb) uppercase foo bar baz
        FOO
        BAR
        BAZ

    """

    @wraps(function)
    def wrapper(debugger, argument_string, result_file, internal_dict):
        args = shlex.split(argument_string)
        try:
            result = function(debugger, *args)
        except CommandException as exception:
            result = exception.message

        if result:
            result_file.write(result)
            result_file.write('\n')

    LLDB_COMMANDS.append(wrapper)

    return wrapper


def register_commands(debugger):
    imported_module_names = set()

    for function in LLDB_COMMANDS:
        function_name = function.__name__
        module_name = function.__module__

        if module_name not in imported_module_names:
            module_path = sys.modules[module_name].__file__.rstrip('c')
            debugger.HandleCommand('command script import %s' % module_path)
            imported_module_names.add(module_name)

        debugger.HandleCommand('command script add -f %s.%s %s' % \
            (module_name, function_name, function_name))

########NEW FILE########
__FILENAME__ = mcslldb_main
#!/usr/bin/env python
# encoding: utf-8

from mcslldb_helpers import DummyDebugger, register_commands


def __lldb_init_module(debugger, internal_dict):
    import mcslldb_commands
    assert mcslldb_commands  # silence pyflakes

    register_commands(debugger)


if __name__ == '__main__':
    __lldb_init_module(DummyDebugger(), {})

########NEW FILE########
