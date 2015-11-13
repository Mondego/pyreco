__FILENAME__ = pyobfuscate
#!/usr/bin/env python
#
# Execute the file with the same name as myself minus the extension.
# Author: Peter Astrand <astrand@cendio.se>
#
import os, sys
root, ext = os.path.splitext(sys.argv[0])
execfile(root)

########NEW FILE########
__FILENAME__ = global_lib
# Library for the globals test

external_global_top = "a"
external_global_ro = "b"
external_global_rw = "c"


########NEW FILE########
__FILENAME__ = bug1583

import sys

def foo(bar):
    return sum(map(lambda x: x+bar, [1, 2, 3]))

sys.exit(2*foo(5))



########NEW FILE########
__FILENAME__ = bug1673
__all__ = ["gvar", "colliding"]
import sys
gvar = 47
def foo():
    global gvar
    gvar += 2
    colliding = 33
    assert 0 == locals().has_key("colliding")
    return gvar
sys.exit(foo())


########NEW FILE########
__FILENAME__ = commblanks
#
# A comment at top.
#

import sys

a = 12

b = 16

c = 14

def test():
    return a+b+c

if "__main__" == __name__:
    sys.exit(test())

########NEW FILE########
__FILENAME__ = defafteruse

import sys

class Server:
    def fun(self):
        agenthost = "arne"
        return get_fortytwo(agenthost,kwarg=42)

def get_fortytwo(agenthost, kwarg=3):
    foo = agenthost
    return kwarg

s = Server()

sys.exit(s.fun())

########NEW FILE########
__FILENAME__ = dyn_all
foo = ["aaa"]
__all__ = ["bbb"] + foo

def bbb():
    return 40

def aaa():
    return 2

########NEW FILE########
__FILENAME__ = global

import sys

def foo():
    return glob*2

def main():
    global glob
    glob = 21
    return foo()

sys.exit(main())

########NEW FILE########
__FILENAME__ = import
import sys

from tobeimported import foo

sys.exit(foo())


########NEW FILE########
__FILENAME__ = importall_star
from tobeimported_everything import *
import sys

sys.exit(one()+two()+thirtynine())


########NEW FILE########
__FILENAME__ = importpackage
import sys

from package.tobeimported import foo

sys.exit(foo())

########NEW FILE########
__FILENAME__ = importpackage_as
import sys

from package.tobeimported import foo as bar

sys.exit(bar())

########NEW FILE########
__FILENAME__ = keywordclass

__all__ = ["ClassWithKeywords"]

class ClassWithKeywords:
    def __init__(self, kwarg = 3):
        self.kwarg = kwarg

    def fortytwo(self, arg=6):
        return self.kwarg + arg
        

########NEW FILE########
__FILENAME__ = keywordclassuser

import keywordclass
import sys

k = keywordclass.ClassWithKeywords(kwarg=20)

sys.exit(k.fortytwo(arg=22))

########NEW FILE########
__FILENAME__ = keywordfunc

import sys

SOMETHING=21

def foo(bar=SOMETHING):
    return bar

def gazonk(startval=2):
    return startval + foo()

if "__main__" == __name__:
    sys.exit(gazonk(startval=21))





########NEW FILE########
__FILENAME__ = lambda_global

import sys

def sort(x, y):
    return cmp(x,y)

def main():
    l = [120,300,42]
    l.sort(lambda x, y: sort(x, y))
    return l[0]


if "__main__" == __name__:
    sys.exit(main())

########NEW FILE########
__FILENAME__ = tobeimported

__all__ = ["foo"]

def bar():
    return 40

def foo():
    return bar() + 2
 

########NEW FILE########
__FILENAME__ = power

import sys

x = 2
y = x**2
sys.exit(y)

########NEW FILE########
__FILENAME__ = tobeimported

__all__ = ["foo"]

def bar():
    return 40

def foo():
    return bar() + 2

########NEW FILE########
__FILENAME__ = tobeimported_everything

__all__ = ["one", "two", "thirtynine"]

def one():
    return 1

def two():
    return 2

def thirtynine():
    return 39

        
        

########NEW FILE########
__FILENAME__ = test_args
#!/usr/bin/env python

import unittest

def function_none():
    pass

def function_args(a, b, c):
    assert a == 1
    assert b == 2
    assert c == 3
    assert "a" in locals()
    assert "b" in locals()
    assert "c" in locals()

def function_default(expected, arg=12):
    assert expected == arg
    assert "expected" in locals()
    assert "arg" in locals()

def function_posargs(*args):
    # FIXME: args could be obfuscated in theory, but the obfuscator is
    #        currently unable.
    #assert "args" not in locals()
    pass

def function_kwargs(**kwargs):
    # FIXME: Dito
    #assert "kwargs" not in locals()
    pass

class FunctionArgumentTest(unittest.TestCase):
    def test_none(self):
        function_none()

    def test_pos(self):
        function_args(1, 2, 3)

    def test_named(self):
        function_args(c=3, b=2, a=1)

    def test_default(self):
        function_default(12)

    def test_default_pos(self):
        function_default(13, 13)

    def test_default_named(self):
        function_default(13, arg=13)

    def test_posargs(self):
        function_posargs()
        function_posargs(1, 2, 3)

    def test_kwargs(self):
        function_kwargs()
        function_kwargs(a=1, b=2, c=3)

class Dummy:
    def method_none(self):
        pass

    def method_args(self, a, b, c):
        assert a == 1
        assert b == 2
        assert c == 3
        assert "a" in locals()
        assert "b" in locals()
        assert "c" in locals()

    def method_default(self, expected, arg=12):
        assert expected == arg
        assert "expected" in locals()
        assert "arg" in locals()

class MethodArgumentTest(unittest.TestCase):
    def test_none(self):
        obj = Dummy()
        obj.method_none()

    def test_pos(self):
        obj = Dummy()
        obj.method_args(1, 2, 3)

    def test_named(self):
        obj = Dummy()
        obj.method_args(c=3, b=2, a=1)

    def test_default(self):
        obj = Dummy()
        obj.method_default(12)

    def test_default_pos(self):
        obj = Dummy()
        obj.method_default(13, 13)

    def test_default_named(self):
        obj = Dummy()
        obj.method_default(13, arg=13)

if "__main__" == __name__:
    unittest.main()

########NEW FILE########
__FILENAME__ = test_classes
#!/usr/bin/env python

import unittest

__all__ = ["GlobalClass"]

class LocalClass:
	def method_a():
		pass

class GlobalClass:
	def method_b():
		pass

class OuterNestedClass:
	class InnerNestedClass:
		pass

def nested_function(test):
	class InnerNestedClass:
		pass
	test.assertFalse("InnerNestedClass" in locals())

# This crashed the obfuscator at one point
class EmptyAncestors():
	pass

class ClassTest(unittest.TestCase):
	def test_local(self):
		self.assertFalse("LocalClass" in globals())

	def test_local_method(self):
		obj = LocalClass()
		# Method names should not be obfuscated as we don't
		# know what the object is until runtime
		self.assertTrue(hasattr(obj, "method_a"))

	def test_global(self):
		self.assertTrue("GlobalClass" in globals())

	def test_global_method(self):
		obj = GlobalClass()
		# See test_local_method()
		self.assertTrue(hasattr(obj, "method_b"))

	def test_nested_class(self):
		self.assertFalse("OuterNestedClass" in globals())
		self.assertTrue(hasattr(OuterNestedClass, "InnerNestedClass"))

	def test_nested_function(self):
		nested_function(self)

if "__main__" == __name__:
    unittest.main()

########NEW FILE########
__FILENAME__ = test_globals
#!/usr/bin/env python

import unittest

# Locally defined global variable should be obfuscated
local_global = 1

# Check that referenced are properly followed
local_reffed_global = 2

def check_func_ref(self):
    var = local_reffed_global
    self.assertFalse("var" in locals())
    self.assertEqual(var, 2)

def check_func_write(val):
    global local_reffed_global
    local_reffed_global = val

# Locally defined globals can be missing on the module scope
# Unfortunately we don't know if this variable is only declared here,
# or if it also comes via a * import. The obfuscator assumes the worst
# and lets it remain in the clear.
def check_func_define(self):
    global hidden_local_global
    hidden_local_global = 3
    self.assertFalse("hidden_local_global" in locals())
    self.assertTrue("hidden_local_global" in globals())

# Multiple global references at once
local_global_a = 4
local_global_b = 5

def check_func_multi_write(a, b):
    global local_global_a, local_global_b
    local_global_a = a
    local_global_b = b

class LocalGlobalTest(unittest.TestCase):
    def test_simple(self):
        self.assertFalse("local_global" in globals())

    def test_reffed(self):
        self.assertFalse("local_reffed_global" in globals())

    def test_func_ref(self):
        check_func_ref(self)

    def check_method_ref(self):
        var = local_reffed_global
        self.assertFalse("var" in locals())
        self.assertEqual(var, 2)

    def test_method_ref(self):
        self.check_method_ref()

    def test_func_write(self):
        check_func_write('x')
        self.assertEqual(local_reffed_global, 'x')
        check_func_write(2)
        self.assertEqual(local_reffed_global, 2)

    def check_method_write(self, val):
        global local_reffed_global
        local_reffed_global = val

    def test_method_write(self):
        self.check_method_write('x')
        self.assertEqual(local_reffed_global, 'x')
        self.check_method_write(2)
        self.assertEqual(local_reffed_global, 2)

    def test_func_define(self):
        check_func_define(self)
        self.assertEqual(hidden_local_global, 3)

    def test_multi(self):
        self.assertFalse("local_global_a" in globals())
        self.assertFalse("local_global_b" in globals())

    def test_func_multi_write(self):
        check_func_multi_write('y', 'z')
        self.assertEqual(local_global_a, 'y')
        self.assertEqual(local_global_b, 'z')
        check_func_multi_write(4, 5)
        self.assertEqual(local_global_a, 4)
        self.assertEqual(local_global_b, 5)

    def check_method_multi_write(self, a, b):
        global local_global_a, local_global_b
        local_global_a = a
        local_global_b = b

    def test_method_multi_write(self):
        self.check_method_multi_write('y', 'z')
        self.assertEqual(local_global_a, 'y')
        self.assertEqual(local_global_b, 'z')
        self.check_method_multi_write(4, 5)
        self.assertEqual(local_global_a, 4)
        self.assertEqual(local_global_b, 5)

# Check that external references do not get obfuscated
from global_lib import *

# Local copies should still get obfuscated though
local_copy = external_global_top

def check_func_external_ref(self):
    var = external_global_ro
    self.assertFalse("var" in locals())
    self.assertEqual(var, "b")

def check_func_external_write(val):
    global external_global_rw
    external_global_rw = val

class ExternalGlobalTest(unittest.TestCase):
    def test_name(self):
        self.assertTrue("external_global_top" in globals())
        self.assertTrue("external_global_ro" in globals())
        self.assertTrue("external_global_rw" in globals())

    def test_copy(self):
        self.assertFalse("local_copy" in globals())

    def test_func_ref(self):
        check_func_external_ref(self)

    def check_method_ref(self):
        var = external_global_ro
        self.assertFalse("var" in locals())
        self.assertEqual(var, "b")

    def test_method_ref(self):
        self.check_method_ref()

    def test_func_write(self):
        check_func_external_write('x')
        self.assertEqual(external_global_rw, 'x')
        check_func_external_write("c")
        self.assertEqual(external_global_rw, "c")

    def check_method_write(self, val):
        global external_global_rw
        external_global_rw = val

    def test_method_write(self):
        self.check_method_write('x')
        self.assertEqual(external_global_rw, 'x')
        self.check_method_write("c")
        self.assertEqual(external_global_rw, "c")

if "__main__" == __name__:
    unittest.main()

########NEW FILE########
__FILENAME__ = test_lambda
#!/usr/bin/env python

import unittest

__all__ = ["public_global"]

private_global = 1
public_global = 2

def arg_func(arg):
    f = lambda : arg
    return f()

class LambdaTest(unittest.TestCase):
    def test_simple(self):
        f = lambda: True
        self.assertTrue(f())

    def test_arg(self):
        f = lambda b: b
        self.assertTrue(f(True))

    def test_local(self):
        var = 3
        f = lambda : var
        self.assertTrue(f() == 3)

    def test_local_arg(self):
        self.assertTrue(arg_func(4) == 4)

    def test_private_global(self):
        self.assertFalse("private_global" in globals())
        f = lambda : private_global
        self.assertTrue(f() == 1)

    def test_public_global(self):
        self.assertTrue("public_global" in globals())
        f = lambda : public_global
        self.assertTrue(f() == 2)

if "__main__" == __name__:
    unittest.main()

########NEW FILE########
__FILENAME__ = test_literals
#!/usr/bin/env python

import unittest

# Check that multi line literals don't get destroyed.
#
# Bug 1: Line starting with a string was assumed to be a doc string
#
dictionary = {
    'key1': (12, 'foobar', None,
             "another string", 44,
             "foo",
             None),
    'key2': (12, 'foobar', None,
             "another string", 44,
             "foo",
             None)
    }

class LiteralTest(unittest.TestCase):
    def test_dictionary(self):
        self.assertTrue("key1" in dictionary.keys())
        self.assertTrue("key2" in dictionary.keys())
        self.assertEqual(dictionary["key1"][5], "foo")
        self.assertEqual(dictionary["key2"][5], "foo")

if "__main__" == __name__:
    unittest.main()

########NEW FILE########
__FILENAME__ = test_locals
#!/usr/bin/env python

import unittest

__all__ = ["public_variable"]

def function_write(test):
	just_write = 1
	test.assertFalse("just_write" in locals())

def function_read_write(test):
	read_write = 2
	if read_write:
		pass
	test.assertFalse("read_write" in locals())

def function_public(test):
	# A different variable mentioned in __all__ shouldn't
	# prevent obfuscation
	public_variable = 3
	test.assertFalse("public_variable" in locals())

def function_nested(test):
	# Nested function definitions makes the scope handling really
	# confusing
	def nested(test):
		test.assertTrue(var == 12)
	var = 12
	test.assertFalse("var" in locals())
	test.assertFalse("nested" in locals())
	nested(test)

def function_double_nested(test):
	def nested_a(test):
		def nested_b(test):
			test.assertTrue(var == 666)
		test.assertFalse("nested_b" in locals())
	var = 666
	test.assertFalse("var" in locals())
	test.assertFalse("nested_a" in locals())
	nested_a(test)

class FunctionTest(unittest.TestCase):
	def test_just_write(self):
		function_write(self)

	def test_read_write(self):
		function_read_write(self)

	def test_public(self):
		function_public(self)

	def test_nested(self):
		function_nested(self)

	def test_double_nested(self):
		function_double_nested(self)

class Dummy:
	def method_write(self, test):
		just_write = 1
		test.assertFalse("just_write" in locals())

	def method_read_write(self, test):
		read_write = 2
		if read_write:
			pass
		test.assertFalse("read_write" in locals())

	def method_public(self, test):
		# A different variable mentioned in __all__ shouldn't
		# prevent obfuscation
		public_variable = 3
		test.assertFalse("public_variable" in locals())

class MethodTest(unittest.TestCase):
	def test_just_write(self):
		obj = Dummy()
		obj.method_write(self)

	def test_read_write(self):
		obj = Dummy()
		obj.method_read_write(self)

	def test_public(self):
		obj = Dummy()
		obj.method_public(self)

if "__main__" == __name__:
    unittest.main()

########NEW FILE########
__FILENAME__ = test_pyobfuscate
#!/usr/bin/env python

import unittest
import sys
sys.path = ["/opt/thinlinc/modules"] + sys.path
import subprocess
import re
import os
import tempfile

class ObfuscateTest(unittest.TestCase):
    def mkstemp(self):
        """wrapper for mkstemp, calling mktemp if mkstemp is not available"""
        if hasattr(tempfile, "mkstemp"):
            return tempfile.mkstemp()
        else:
            fname = tempfile.mktemp()
            return os.open(fname, os.O_RDWR|os.O_CREAT), fname

    def run_pyobfuscate(self, testfile, args=[]):
        cmdline = ["../pyobfuscate"] + args + [testfile]
        p = subprocess.Popen(cmdline,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        (stdout, stderr) = p.communicate()
        assert '' == stderr, "pyobfuscate wrote to stderr: %s" % stderr
        return stdout

    def obfuscate_and_write(self, testfile, outfile, args=[]):
        open(outfile, 'w').write(self.run_pyobfuscate(testfile, args))

    def run_src(self, src):
        f, fname = self.mkstemp()
        os.write(f, src)
        os.close(f)
        retcode = subprocess.call([sys.executable, fname])
        os.remove(fname)
        return retcode

    def obfuscate_and_run_file(self, testfile, args=[]):
        output = self.run_pyobfuscate(testfile, args)
        return self.run_src(output)

    def obfuscate_and_run_src(self, src, args=[]):
        f, fname = self.mkstemp()
        os.write(f, src)
        os.close(f)
        retcode = self.obfuscate_and_run_file(fname, args)
        os.remove(fname)
        return retcode
    
    def test_DontKeepblanks(self):
        """Don't keep blanks unless told so"""
        output = self.run_pyobfuscate("testfiles/commblanks.py")
        assert None == re.search(output, "^$"), "Blank lines in output"
        lines = output.split("\n")
        assert "#" == lines[0][0], "First line is not a comment"
        assert 42 == self.run_src(output)        

    def test_Keepblanks(self):
        """Keep blanks when told so"""
        output = self.run_pyobfuscate("testfiles/commblanks.py",
                                      args=["--keepblanks"])
        lines = output.split("\n")
        assert '' == lines[5], "Blank lines removed"
        assert 42 == self.run_src(output)

    def test_lambdaGlobal(self):
        """Support lambda constructs referencing global functions.
        Test inspired by log message for revision 1.15"""
        assert 42 == self.obfuscate_and_run_file("testfiles/lambda_global.py"), "Incorrect value returned after obfuscation"

    def test_power(self):
        """Handle power operator correctly. Bug 1411"""
        assert 4 == self.obfuscate_and_run_file("testfiles/power.py"), "Incorrect value returned after obfuscation"

    def test_keywordfunc(self):
        """Handle keyword functions correctly.
        Test inspired by revision 1.8 and revision 1.9"""
        assert 42 == self.obfuscate_and_run_file("testfiles/keywordfunc.py"), "Incorrect value returned after obfuscation"

    def test_importlist(self):
        """Handle from <x> import <y>"""
        self.obfuscate_and_write("testfiles/tobeimported.py",
                                 "generated/tobeimported.py")
        self.obfuscate_and_write("testfiles/import.py",
                                 "generated/import.py")
        assert 42 == subprocess.call([sys.executable, "generated/import.py"]), "Incorrect value returned after obfuscation"

    def test_import_package(self):
        """Handle from x.y import z"""
        self.obfuscate_and_write("testfiles/package/tobeimported.py",
                                 "generated/package/tobeimported.py")
        self.obfuscate_and_write("testfiles/package/__init__.py",
                                 "generated/package/__init__.py")

        self.obfuscate_and_write("testfiles/importpackage.py",
                                 "generated/importpackage.py")
        assert 42 == subprocess.call([sys.executable,
                                      "generated/importpackage.py"],
                                     env={"PYTHONPATH":"generated"}), "Incorrect value returned after obfuscation"

    def test_import_package_as(self):
        """Handle from x.y import z as a"""
        self.obfuscate_and_write("testfiles/package/tobeimported.py",
                                 "generated/package/tobeimported.py")
        self.obfuscate_and_write("testfiles/package/__init__.py",
                                 "generated/package/__init__.py")

        self.obfuscate_and_write("testfiles/importpackage_as.py",
                                 "generated/importpackage_as.py")
        assert 42 == subprocess.call([sys.executable,
                                      "generated/importpackage_as.py"],
                                     env={"PYTHONPATH":"generated"}), "Incorrect value returned after obfuscation"

    def test_import_everything(self):
        self.obfuscate_and_write("testfiles/tobeimported_everything.py",
                                 "generated/tobeimported_everything.py")
        self.obfuscate_and_write("testfiles/importall_star.py",
                                 "generated/importall_star.py")
        assert 42 == subprocess.call([sys.executable, "generated/importall_star.py"]), "Incorrect value returned after obfuscation"

    def test_import_dyn_all(self):
        """Verify that trying to import from a file with dynamic __all__ fails"""
        cmdline = ["../pyobfuscate", "testfiles/dyn_all.py"]        
        p = subprocess.Popen(cmdline,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        (stdout, stderr) = p.communicate()
        assert -1 != stderr.find("__all__ is not a list of constants"), "pyobufscate didn't bail out with an error on file with dynamic __all__"

    def test_import_with_keywords(self):
        """Verify that an imported class, defined in __all__, does not get obfuscated keyword arguments"""
        self.obfuscate_and_write("testfiles/keywordclass.py",
                                 "generated/keywordclass.py")
        self.obfuscate_and_write("testfiles/keywordclassuser.py",
                                 "generated/keywordclassuser.py")
        assert 42 == subprocess.call([sys.executable, "generated/keywordclassuser.py"]), "Incorrect value returned after obfuscation"

    def test_global_stmt(self):
        """Verify use of 'global' keyword"""
        assert 42 == self.obfuscate_and_run_file("testfiles/global.py"), "Incorrect value returned after obfuscation"

    def test_definition_after_use(self):
        """Verify that a function defined after it's used works as expected"""
        output = self.run_pyobfuscate("testfiles/defafteruse.py")
        assert 42 == self.run_src(output), "Incorrect value returned after obfuscation"

    def test_bug1583(self):
        """Verify that bug 1583 is not present (lambda obfuscation problems)"""
        output = self.run_pyobfuscate("testfiles/bug1583.py")
        assert 42 == self.run_src(output), "Incorrect value returned after obfuscation"

    def test_bug1673(self):
        """Verify that bug 1673 is not present (global variable handling)"""
        output = self.run_pyobfuscate("testfiles/bug1673.py")
        assert 49 == self.run_src(output), "Incorrect value returned after obfuscation"

                                 

    
if "__main__" == __name__:
    unittest.main()

########NEW FILE########
