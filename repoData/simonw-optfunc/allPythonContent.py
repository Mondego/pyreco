__FILENAME__ = demo
#!/usr/bin/env python
import optfunc

def upper(filename, verbose = False):
    "Usage: %prog <file> [--verbose] - output file content in uppercase"
    s = open(filename).read()
    if verbose:
        print "Processing %s bytes..." % len(s)
    print s.upper()

if __name__ == '__main__':
    optfunc.run(upper)

########NEW FILE########
__FILENAME__ = geocode
#!/usr/bin/env python
# Depends on geocoders from http://github.com/simonw/geocoders being on the 
# python path.
import geocoders
import optfunc
import os

# We use notstrict because we want to be able to trigger the list_geocoders
# option without being forced to provide the normally mandatory 's' argument
@optfunc.notstrict
@optfunc.arghelp('list_geocoders', 'list available geocoders and exit')
def geocode(s, api_key='', geocoder='google', list_geocoders=False):
    "Usage: %prog <location string> --api-key <api-key>" 
    available = [
        f.replace('.py', '')
        for f in os.listdir(os.path.dirname(geocoders.__file__))
        if f.endswith('.py') and not f.startswith('_') and f != 'utils.py'
    ]
    if list_geocoders:
        print 'Available geocoders: %s' % (', '.join(available))
        return
    
    assert geocoder in available, '"%s" is not a known geocoder' % geocoder
    assert s, 'Enter a string to geocode'
    
    mod = __import__('geocoders.%s' % geocoder, {}, {}, ['geocoders'])
    
    name, (lat, lon) =  mod.geocoder(api_key)(s)
    print '%s\t%s\t%s' % (name, lat, lon)

optfunc.main(geocode)

########NEW FILE########
__FILENAME__ = optfunc
from optparse import OptionParser, make_option
import sys, inspect, re

single_char_prefix_re = re.compile('^[a-zA-Z0-9]_')

class ErrorCollectingOptionParser(OptionParser):
    def __init__(self, *args, **kwargs):
        self._errors = []
        self._custom_names = {}
        # can't use super() because OptionParser is an old style class
        OptionParser.__init__(self, *args, **kwargs)
    
    def parse_args(self, argv):
        options, args = OptionParser.parse_args(self, argv)
        for k,v in options.__dict__.iteritems():
            if k in self._custom_names:
                options.__dict__[self._custom_names[k]] = v
                del options.__dict__[k]
        return options, args

    def error(self, msg):
        self._errors.append(msg)

def func_to_optionparser(func):
    args, varargs, varkw, defaultvals = inspect.getargspec(func)
    defaultvals = defaultvals or ()
    options = dict(zip(args[-len(defaultvals):], defaultvals))
    argstart = 0
    if func.__name__ == '__init__':
        argstart = 1
    if defaultvals:
        required_args = args[argstart:-len(defaultvals)]
    else:
        required_args = args[argstart:]
    
    # Build the OptionParser:
    opt = ErrorCollectingOptionParser(usage = func.__doc__)
    
    helpdict = getattr(func, 'optfunc_arghelp', {})
    
    # Add the options, automatically detecting their -short and --long names
    shortnames = set(['h'])
    for funcname, example in options.items():
        # They either explicitly set the short with x_blah...
        name = funcname
        if single_char_prefix_re.match(name):
            short = name[0]
            name = name[2:]
            opt._custom_names[name] = funcname
        # Or we pick the first letter from the name not already in use:
        else:
            for short in name:
                if short not in shortnames:
                    break
        
        shortnames.add(short)
        short_name = '-%s' % short
        long_name = '--%s' % name.replace('_', '-')
        if example in (True, False, bool):
            action = 'store_true'
        else:
            action = 'store'
        opt.add_option(make_option(
            short_name, long_name, action=action, dest=name, default=example,
            help = helpdict.get(funcname, '')
        ))
    
    return opt, required_args

def resolve_args(func, argv):
    parser, required_args = func_to_optionparser(func)
    options, args = parser.parse_args(argv)
    
    # Special case for stdin/stdout/stderr
    for pipe in ('stdin', 'stdout', 'stderr'):
        if pipe in required_args:
            required_args.remove(pipe)
            setattr(options, 'optfunc_use_%s' % pipe, True)
    
    # Do we have correct number af required args?
    if len(required_args) != len(args):
        if not hasattr(func, 'optfunc_notstrict'):
            parser._errors.append('Required %d arguments, got %d' % (
                len(required_args), len(args)
            ))
    
    # Ensure there are enough arguments even if some are missing
    args += [None] * (len(required_args) - len(args))
    for i, name in enumerate(required_args):
        setattr(options, name, args[i])
    
    return options.__dict__, parser._errors

def run(
        func, argv=None, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr
    ):
    argv = argv or sys.argv[1:]
    include_func_name_in_errors = False
    
    # Handle multiple functions
    if isinstance(func, (tuple, list)):
        funcs = dict([
            (fn.__name__, fn) for fn in func
        ])
        try:
            func_name = argv.pop(0)
        except IndexError:
            func_name = None
        if func_name not in funcs:
            names = ["'%s'" % fn.__name__ for fn in func]
            s = ', '.join(names[:-1])
            if len(names) > 1:
                s += ' or %s' % names[-1]
            stderr.write("Unknown command: try %s\n" % s)
            return
        func = funcs[func_name]
        include_func_name_in_errors = True

    if inspect.isfunction(func):
        resolved, errors = resolve_args(func, argv)
    elif inspect.isclass(func):
        if hasattr(func, '__init__'):
            resolved, errors = resolve_args(func.__init__, argv)
        else:
            resolved, errors = {}, []
    else:
        raise TypeError('arg is not a Python function or class')
    
    # Special case for stdin/stdout/stderr
    for pipe in ('stdin', 'stdout', 'stderr'):
        if resolved.pop('optfunc_use_%s' % pipe, False):
            resolved[pipe] = locals()[pipe]
    
    if not errors:
        try:
            return func(**resolved)
        except Exception, e:
            if include_func_name_in_errors:
                stderr.write('%s: ' % func.__name__)
            stderr.write(str(e) + '\n')
    else:
        if include_func_name_in_errors:
            stderr.write('%s: ' % func.__name__)
        stderr.write("%s\n" % '\n'.join(errors))

def main(*args, **kwargs):
    prev_frame = inspect.stack()[-1][0]
    mod = inspect.getmodule(prev_frame)
    if mod is not None and mod.__name__ == '__main__':
        run(*args, **kwargs)
    return args[0] # So it won't break anything if used as a decorator

# Decorators
def notstrict(fn):
    fn.optfunc_notstrict = True
    return fn

def arghelp(name, help):
    def inner(fn):
        d = getattr(fn, 'optfunc_arghelp', {})
        d[name] = help
        setattr(fn, 'optfunc_arghelp', d)
        return fn
    return inner

########NEW FILE########
__FILENAME__ = subcommands_demo
#!/usr/bin/env python
import optfunc

def one(arg):
    print "One: %s" % arg

def two(arg):
    print "Two: %s" % arg

def three(arg):
    print "Three: %s" % arg

optfunc.main([one, two, three])

########NEW FILE########
__FILENAME__ = test
import unittest
import optfunc
from StringIO import StringIO

class TestOptFunc(unittest.TestCase):
    def test_three_positional_args(self):
        
        has_run = [False]
        def func(one, two, three):
            has_run[0] = True
        
        # Should only have the -h help option
        parser, required_args = optfunc.func_to_optionparser(func)
        self.assertEqual(len(parser.option_list), 1)
        self.assertEqual(str(parser.option_list[0]), '-h/--help')
        
        # Should have three required args
        self.assertEqual(required_args, ['one', 'two', 'three'])
        
        # Running it with the wrong number of arguments should cause an error
        for argv in (
            ['one'],
            ['one', 'two'],
            ['one', 'two', 'three', 'four'],
        ):
            e = StringIO()
            optfunc.run(func, argv, stderr=e)
            self.assert_('Required 3 arguments' in e.getvalue(), e.getvalue())
            self.assertEqual(has_run[0], False)
        
        # Running it with the right number of arguments should be fine
        e = StringIO()
        optfunc.run(func, ['one', 'two', 'three'], stderr=e)
        self.assertEqual(e.getvalue(), '')
        self.assertEqual(has_run[0], True)
    
    def test_one_arg_one_option(self):
        
        has_run = [False]
        def func(one, option=''):
            has_run[0] = (one, option)
        
        # Should have -o option as well as -h option
        parser, required_args = optfunc.func_to_optionparser(func)
        self.assertEqual(len(parser.option_list), 2)
        strs = [str(o) for o in parser.option_list]
        self.assert_('-h/--help' in strs)
        self.assert_('-o/--option' in strs)
        
        # Should have one required arg
        self.assertEqual(required_args, ['one'])
        
        # Should execute
        self.assert_(not has_run[0])
        optfunc.run(func, ['the-required', '-o', 'the-option'])
        self.assert_(has_run[0])
        self.assertEqual(has_run[0], ('the-required', 'the-option'))
        
        # Option should be optional
        has_run[0] = False
        optfunc.run(func, ['required2'])
        self.assert_(has_run[0])
        self.assertEqual(has_run[0], ('required2', ''))
    
    def test_options_are_correctly_named(self):
        def func1(one, option='', verbose=False):
            pass
        
        parser, required_args = optfunc.func_to_optionparser(func1)
        strs = [str(o) for o in parser.option_list]
        self.assertEqual(strs, ['-h/--help', '-o/--option', '-v/--verbose'])
    
    def test_option_with_hyphens(self):
        def func2(option_with_hyphens=True):
            pass
        
        parser, required_args = optfunc.func_to_optionparser(func2)
        strs = [str(o) for o in parser.option_list]
        self.assertEqual(strs, ['-h/--help', '-o/--option-with-hyphens'])
    
    def test_options_with_same_inital_use_next_letter(self):
        def func1(one, version='', verbose=False):
            pass
        
        parser, required_args = optfunc.func_to_optionparser(func1)
        strs = [str(o) for o in parser.option_list]
        self.assertEqual(strs, ['-h/--help', '-v/--version', '-e/--verbose'])

        def func2(one, host=''):
            pass
        
        parser, required_args = optfunc.func_to_optionparser(func2)
        strs = [str(o) for o in parser.option_list]
        self.assertEqual(strs, ['-h/--help', '-o/--host'])
    
    def test_short_option_can_be_named_explicitly(self):
        def func1(one, option='', q_verbose=False):
            pass
        
        parser, required_args = optfunc.func_to_optionparser(func1)
        strs = [str(o) for o in parser.option_list]
        self.assertEqual(strs, ['-h/--help', '-o/--option', '-q/--verbose'])

        e = StringIO()
        optfunc.run(func1, ['one', '-q'], stderr=e)
        self.assertEqual(e.getvalue().strip(), '')
    
    def test_notstrict(self):
        "@notstrict tells optfunc to tolerate missing required arguments"
        def strict_func(one):
            pass
        
        e = StringIO()
        optfunc.run(strict_func, [], stderr=e)
        self.assertEqual(e.getvalue().strip(), 'Required 1 arguments, got 0')
        
        @optfunc.notstrict
        def notstrict_func(one):
            pass
        
        e = StringIO()
        optfunc.run(notstrict_func, [], stderr=e)
        self.assertEqual(e.getvalue().strip(), '')
    
    def test_arghelp(self):
        "@arghelp('foo', 'help about foo') sets help text for parameters"
        @optfunc.arghelp('foo', 'help about foo')
        def foo(foo = False):
            pass
        
        parser, required_args = optfunc.func_to_optionparser(foo)
        opt = parser.option_list[1]
        self.assertEqual(str(opt), '-f/--foo')
        self.assertEqual(opt.help, 'help about foo')
    
    def test_multiple_invalid_subcommand(self):
        "With multiple subcommands, invalid first arg should raise an error"
        def one(arg):
            pass
        def two(arg):
            pass
        def three(arg):
            pass
        
        # Invalid first argument should raise an error
        e = StringIO()
        optfunc.run([one, two], ['three'], stderr=e)
        self.assertEqual(
            e.getvalue().strip(), "Unknown command: try 'one' or 'two'"
        )
        e = StringIO()
        optfunc.run([one, two, three], ['four'], stderr=e)
        self.assertEqual(
            e.getvalue().strip(),
            "Unknown command: try 'one', 'two' or 'three'"
        )
        
        # No argument at all should raise an error
        e = StringIO()
        optfunc.run([one, two, three], [], stderr=e)
        self.assertEqual(
            e.getvalue().strip(),
            "Unknown command: try 'one', 'two' or 'three'"
        )
    
    def test_multiple_valid_subcommand_invalid_argument(self):
        "Subcommands with invalid arguments should report as such"
        def one(arg):
            executed.append(('one', arg))
        
        def two(arg):
            executed.append(('two', arg))

        e = StringIO()
        executed = []
        optfunc.run([one, two], ['one'], stderr=e)
        self.assertEqual(
            e.getvalue().strip(), 'one: Required 1 arguments, got 0'
        )
    
    def test_multiple_valid_subcommand_valid_argument(self):
        "Subcommands with valid arguments should execute as expected"
        def one(arg):
            executed.append(('one', arg))
        
        def two(arg):
            executed.append(('two', arg))

        e = StringIO()
        executed = []
        optfunc.run([one, two], ['two', 'arg!'], stderr=e)
        self.assertEqual(e.getvalue().strip(), '')
        self.assertEqual(executed, [('two', 'arg!')])

    def test_run_class(self):
        class Class:
            def __init__(self, one, option=''):
                self.has_run = [(one, option)]
        
        class NoInitClass:
            pass

        # Should execute
        e = StringIO()
        c = optfunc.run(Class, ['the-required', '-o', 'the-option'], stderr=e)
        self.assertEqual(e.getvalue().strip(), '')
        self.assert_(c.has_run[0])
        self.assertEqual(c.has_run[0], ('the-required', 'the-option'))
        
        # Option should be optional
        c = None
        e = StringIO()
        c = optfunc.run(Class, ['required2'], stderr=e)
        self.assertEqual(e.getvalue().strip(), '')
        self.assert_(c.has_run[0])
        self.assertEqual(c.has_run[0], ('required2', ''))

        # Classes without init should work too
        c = None
        e = StringIO()
        c = optfunc.run(NoInitClass, [], stderr=e)
        self.assert_(c)
        self.assertEqual(e.getvalue().strip(), '')
    
    def test_stdin_special_argument(self):
        consumed = []
        def func(stdin):
            consumed.append(stdin.read())
        
        class FakeStdin(object):
            def read(self):
                return "hello"
        
        optfunc.run(func, stdin=FakeStdin())
        self.assertEqual(consumed, ['hello'])
    
    def test_stdout_special_argument(self):
        def upper(stdin, stdout):
            stdout.write(stdin.read().upper())
        
        class FakeStdin(object):
            def read(self):
                return "hello"
        
        class FakeStdout(object):
            written = ''
            def write(self, w):
                self.written = w
        
        stdout = FakeStdout()
        self.assertEqual(stdout.written, '')
        optfunc.run(upper, stdin=FakeStdin(), stdout=stdout)
        self.assertEqual(stdout.written, 'HELLO')
    
    def test_stderr_special_argument(self):
        def upper(stderr):
            stderr.write('an error')
        
        class FakeStderr(object):
            written = ''
            def write(self, w):
                self.written = w
        
        stderr = FakeStderr()
        self.assertEqual(stderr.written, '')
        optfunc.run(upper, stderr=stderr)
        self.assertEqual(stderr.written, 'an error')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
