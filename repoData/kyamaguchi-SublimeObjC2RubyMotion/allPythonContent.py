__FILENAME__ = CodeConverter
import re

class CodeConverter(object):
    def __init__(self, s):
        self.s = s

    def result(self):
        self.mark_spaces_in_string()
        self.remove_comments()
        self.multilines_to_one_line()
        self.replace_nsstring()
        self.convert_blocks()
        self.convert_square_brackets_expression()
        self.remove_semicolon_at_the_end()
        self.remove_autorelease()
        self.remove_type_declaration()
        self.convert_boolean()
        self.convert_float()
        self.convert_cg_rect_make()
        self.tidy_up()
        self.restore_characters_in_string()
        return self.s

    # Helpers
    def convert_args(self, matchobj):
        # Consider args with colon followed by spaces
        following_args = re.sub(r'([^:]+)(\s+)(\S+):', r'\1,\3:', matchobj.group(2))
        # Clear extra spaces after colons
        following_args = re.sub(r':\s+', ':', following_args)
        return "%s(%s)" % (matchobj.group(1), following_args)

    def convert_block_args(self, args):
        if args is None:
            return ''
        else:
            args = re.sub(r'^\(\s*(.*)\s*\)', r'\1', args)
            args = [re.sub(r'\s*[a-zA-Z_0-9]+\s*\*?\s*(\S+)\s*', r'\1', s) for s in args.split(',')]
            if len(args) > 1:
                return '|' + ','.join(args) + '|'
            else:
                return args[0]

    def convert_block_with_args(self, matchobj):
        args = self.convert_block_args(matchobj.group(1))
        return "->%s{%s}" % (args, matchobj.group(2))

    def ruby_style_code(self, matchobj):
        msg = re.sub(r'([^:]+)\:\s*(.+)', self.convert_args, matchobj.group(2))
        return "%s.%s" % (matchobj.group(1), msg)

    def arrange_multilines(self, matchobj):
        if matchobj.group(2) == '}' and '{' not in matchobj.group(1):
            return matchobj.group()
        elif matchobj.group(2) == ']':
            return matchobj.group()
        else:
            return "%s%s " % (matchobj.group(1), matchobj.group(2))

    # Special characters in string (TODO refactoring)
    def characters_to_mark(self, matchobj):
        val = re.sub(r' ', '__SPACE__', matchobj.group(1))
        val = re.sub(r',', '__COMMA__', val)
        val = re.sub(r':', '__SEMICOLON__', val)
        val = re.sub(r'/', '__SLASH__', val)
        return val

    def restore_characters_in_string(self):
        self.s = re.sub(r'__SPACE__', ' ', self.s)
        self.s = re.sub(r'__COMMA__', ',', self.s)
        self.s = re.sub(r'__SEMICOLON__', ':', self.s)
        self.s = re.sub(r'__SLASH__', '/', self.s)
        return self

    # Conversions
    def remove_comments(self):
        self.s = re.sub(re.compile(r'^[ \t]*//.*\n', re.MULTILINE), '', self.s)
        self.s = re.sub(re.compile(r'^(.*)//.*(\n|$)', re.MULTILINE), r'\1\2', self.s)
        return self

    def multilines_to_one_line(self):
        # Remove trailing white space first. Refs: TrimTrailingWhiteSpace
        self.s = re.sub(r'[\t ]+$', '', self.s)
        self.s = re.sub(re.compile(r'(.*)([^;\s{])$\n^\s*', re.MULTILINE), self.arrange_multilines, self.s)
        return self

    def replace_nsstring(self):
        self.s = re.sub(r'@("(?:[^\\"]|\\.)*")', r'\1', self.s)
        return self

    def mark_spaces_in_string(self):
        self.s = re.sub(r'("(?:[^\\"]|\\.)*")', self.characters_to_mark, self.s)
        return self

    def tidy_up(self):
        # convert arguments separated by ','
        self.s = re.sub(r',([a-zA-Z_0-9]+):', r', \1:', self.s)
        # convert block
        self.s = re.sub(r':->{([^}]+)}', r': -> {\1}', self.s)
        # convert block with one args
        self.s = re.sub(r':->([a-zA-Z_0-9]+){([^}]+)}', r': -> \1 {\2}', self.s)
        return self

    def convert_blocks(self):
        self.s = re.sub(r'\^\s*(\([^)]+\))?\s*{([^}]+)}', self.convert_block_with_args, self.s)
        return self

    def convert_square_brackets_expression(self):
        max_attempt = 10 # Avoid infinite loops
        attempt_count = 0
        square_pattern = re.compile(r'\[([^\[\]]+?)\s+([^\[\]]+?)\]')
        while True:
            attempt_count += 1
            m = re.search(square_pattern, self.s)
            if attempt_count > max_attempt :
                break
            elif m :
                self.s = re.sub(square_pattern, self.ruby_style_code, self.s)
            else :
                break
        return self

    def remove_semicolon_at_the_end(self):
        self.s = re.sub(r';', '', self.s)
        return self

    def remove_autorelease(self):
        self.s = re.sub(r'\.autorelease', '', self.s)
        return self

    def remove_type_declaration(self):
        self.s = re.sub(re.compile(r'^(\s*)[a-zA-Z_0-9]+\s*\*\s*([^=]+)=', re.MULTILINE), r'\1\2=', self.s)
        return self

    def convert_boolean(self):
        self.s = re.sub(r'\bYES\b','true', self.s)
        self.s = re.sub(r'\bNO\b','false', self.s)
        return self

    def convert_float(self):
        self.s = re.sub(r'\b(\d+)\.0f\b', r'\1', self.s)
        self.s = re.sub(r'\b(\d+\.\d+)f\b', r'\1', self.s)
        return self

    def convert_cg_rect_make(self):
        self.s = re.sub(r'CGRectMake\( *(\d+(?:\.\d+)?) *, *(\d+(?:\.\d+)?) *, *(\d+(?:\.\d+)?) *, *(\d+(?:\.\d+)?) *\)', r'[[\1, \2], [\3, \4]]', self.s)
        return self

########NEW FILE########
__FILENAME__ = ObjC2RubyMotion
import sublime, sublime_plugin, sys

if sys.version_info >= (3, 0):
    from .CodeConverter import CodeConverter
else:
    from CodeConverter import CodeConverter

class ObjcToRubyMotionCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        for region in self.view.sel():
            if region.empty():
                line = self.view.line(region)
                self.replace_objc(edit, line)
            else:
                self.replace_objc(edit, region)

    def replace_objc(self, edit, region):
        # Get the selected text
        s = self.view.substr(region)

        # Replace the selection with transformed text
        self.view.replace(edit, region, CodeConverter(s).result())

########NEW FILE########
__FILENAME__ = all_test
import unittest, os, sys, glob

if __name__ == '__main__':
    PROJECT_ROOT = os.path.dirname(__file__)
    test_file_strings = glob.glob(os.path.join(PROJECT_ROOT, 'test_*.py'))
    module_strings = [os.path.splitext(os.path.basename(str))[0] for str in test_file_strings]
    suites = [unittest.defaultTestLoader.loadTestsFromName(str) for str in module_strings]
    testSuite = unittest.TestSuite(suites)
    text_runner = unittest.TextTestRunner().run(testSuite)
    if not text_runner.wasSuccessful():
        sys.exit(1)

########NEW FILE########
__FILENAME__ = custom_test_case
class CustomTestCase(object):
    def assertSentence(self, result, expected):
        try:
            self.assertEqual(result, expected)
        except AssertionError as e:
            e.args = (e.args[0].replace("\\n", "\n"),) # edit the exception's message
            raise

########NEW FILE########
__FILENAME__ = test_basic
import unittest, os, sys
from custom_test_case import CustomTestCase

PROJECT_ROOT = os.path.dirname(__file__)
sys.path.append(os.path.join(PROJECT_ROOT, ".."))

from CodeConverter import CodeConverter

class TestBasic(unittest.TestCase, CustomTestCase):

    def test_initialize(self):
        self.assertSentence(CodeConverter('foo').s, 'foo')

    # def test_python_version(self):
    #     # Python for Sublime Text 2 is 2.6.7 (r267:88850, Oct 11 2012, 20:15:00)
    #     print('Your version is ' + sys.version)
    #     if sys.version_info[:2] != (2, 6):
    #         print('Sublime Text 2 uses python 2.6.7')
    #     self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_block
import unittest, os, sys
from custom_test_case import CustomTestCase

PROJECT_ROOT = os.path.dirname(__file__)
sys.path.append(os.path.join(PROJECT_ROOT, ".."))

from CodeConverter import CodeConverter

class TestBlock(unittest.TestCase, CustomTestCase):

    def test_preserve_multilines_with_block_with_multilines(self):
        source   = """[aSet enumerateObjectsUsingBlock:^(id obj, BOOL *stop){
     NSLog(@"Object Found: %@", obj);
} ];"""
        expected = """[aSet enumerateObjectsUsingBlock:^(id obj, BOOL *stop){
     NSLog(@"Object Found: %@", obj);
} ];"""
        self.assertSentence(CodeConverter(source).multilines_to_one_line().s, expected)

    def test_multilines_with_one_line_block(self):
        source   = """[UIView animateWithDuration:0.2
                             animations:^{view.alpha = 0.0;}]"""
        expected = """[UIView animateWithDuration:0.2 animations:^{view.alpha = 0.0;}]"""
        self.assertSentence(CodeConverter(source).multilines_to_one_line().s, expected)

    def test_multilines_with_one_line_blocks(self):
        source   = """[UIView animateWithDuration:0.2
                             animations:^{view.alpha = 0.0;}
                             completion:^(BOOL finished){ [view removeFromSuperview]; }];"""
        expected = """[UIView animateWithDuration:0.2 animations:^{view.alpha = 0.0;} completion:^(BOOL finished){ [view removeFromSuperview]; }];"""
        self.assertSentence(CodeConverter(source).multilines_to_one_line().s, expected)

    def test_block_without_args(self):
        source   = """[UIView animateWithDuration:0.2
                             animations:^{view.alpha = 0.0;}]"""
        expected = """[UIView animateWithDuration:0.2 animations:->{view.alpha = 0.0;}]"""
        self.assertSentence(CodeConverter(source).multilines_to_one_line().convert_blocks().s, expected)

    def test_block_with_one_args(self):
        source   = """[UIView animateWithDuration:0.2
                             animations:^{view.alpha = 0.0;}
                             completion:^( BOOL finished ){ [view removeFromSuperview]; }];"""
        expected = """[UIView animateWithDuration:0.2 animations:->{view.alpha = 0.0;} completion:->finished{ [view removeFromSuperview]; }];"""
        self.assertSentence(CodeConverter(source).multilines_to_one_line().convert_blocks().s, expected)

    def test_block_with_two_args(self):
        source   = """[aSet enumerateObjectsUsingBlock:^(id obj, BOOL *stop){
      NSLog(@"Object Found: %@", obj);
} ];"""
        expected = """[aSet enumerateObjectsUsingBlock:->|obj,stop|{
      NSLog(@"Object Found: %@", obj);
} ];"""
        self.assertSentence(CodeConverter(source).multilines_to_one_line().convert_blocks().s, expected)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_bugfix
import unittest, os, sys
from custom_test_case import CustomTestCase

PROJECT_ROOT = os.path.dirname(__file__)
sys.path.append(os.path.join(PROJECT_ROOT, ".."))

from CodeConverter import CodeConverter

class TestBugfix(unittest.TestCase, CustomTestCase):

    # For Bugfix
    def test_string_including_spaces(self):
        source   = '[[UIAlertView alloc] initWithTitle:@"Warning" message:@"  too many alerts!  \"  "];'
        expected = 'UIAlertView.alloc.initWithTitle("Warning",message:"  too many alerts!  \"  ");'
        self.assertSentence(CodeConverter(source).replace_nsstring().convert_square_brackets_expression().s, expected)

    def test_multiline_with_block_arg_wont_join_lines(self):
        source   = """[UIView animateWithDuration:0.2
                             animations:^{view.alpha = 0.0;}]
"""
        expected = """[UIView animateWithDuration:0.2 animations:^{view.alpha = 0.0;}]
"""
        self.assertSentence(CodeConverter(source).multilines_to_one_line().s, expected)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_comment
import unittest, os, sys
from custom_test_case import CustomTestCase

PROJECT_ROOT = os.path.dirname(__file__)
sys.path.append(os.path.join(PROJECT_ROOT, ".."))

from CodeConverter import CodeConverter

class TestComment(unittest.TestCase, CustomTestCase):

    def test_remove_line_comment(self):
        source   = """  // comment here
  [self foo];"""
        expected = '  [self foo];'
        self.assertSentence(CodeConverter(source).remove_comments().s, expected)

    def test_remove_line_comment_in_multilines(self):
        source   = """
  // comment here
  [self foo];

  // comment2 here
  [self bar];
"""
        expected = """
  [self foo];

  [self bar];
"""
        self.assertSentence(CodeConverter(source).remove_comments().s, expected)

    def test_remove_inline_comment(self):
        source   = '  [self foo];// comment here '
        expected = '  [self foo];'
        self.assertSentence(CodeConverter(source).remove_comments().s, expected)

    def test_dont_remove_url(self):
        source   = 'NSURL* url = [NSURL URLWithString:@"http://www.sublimetext.com/"];'
        expected = 'url = NSURL.URLWithString("http://www.sublimetext.com/")'
        self.assertSentence(CodeConverter(source).result(), expected)

    def test_remove_inline_comment_in_multilines(self):
        source   = """  [self foo];// comment here
  [self bar];// comment2 here"""
        expected = """  [self foo];
  [self bar];"""
        self.assertSentence(CodeConverter(source).remove_comments().s, expected)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_multilines
import unittest, os, sys
from custom_test_case import CustomTestCase

PROJECT_ROOT = os.path.dirname(__file__)
sys.path.append(os.path.join(PROJECT_ROOT, ".."))

from CodeConverter import CodeConverter

class TestMultilines(unittest.TestCase, CustomTestCase):

    def test_multilines_to_one_line(self):
        source   = """first_line;
                      second_line
                      third_line"""
        expected = """first_line;
                      second_line third_line"""
        self.assertSentence(CodeConverter(source).multilines_to_one_line().s, expected)

    def test_multilines_to_one_line_with_args(self):
        source   = """UIAlertView* alert = [[[UIAlertView alloc] initWithTitle:@"Warning"
                                                                       message:@"too many alerts"
                                                                      delegate:nil"""
        expected = 'UIAlertView* alert = [[[UIAlertView alloc] initWithTitle:@"Warning" message:@"too many alerts" delegate:nil'
        self.assertSentence(CodeConverter(source).multilines_to_one_line().s, expected)

    def test_multilines_to_one_line_for_trailing_white_space(self):
        source   = """first_line;
                      second_line   """
        expected = """first_line;
                      second_line"""
        self.assertSentence(CodeConverter(source).multilines_to_one_line().s, expected)

    def test_multilines_to_one_line_for_blank_line(self):
        source   = """first_line;

                      second_line"""
        expected = """first_line;

                      second_line"""
        self.assertSentence(CodeConverter(source).multilines_to_one_line().s, expected)

    def test_multiline_with_braces(self):
        source   = """    if (self) {
        [self addMainLabel];
        [self addSubLabel];
        [self setupBackground];
    }
"""
        expected = """    if (self) {
        self.addMainLabel
        self.addSubLabel
        self.setupBackground
    }
"""
        result = CodeConverter(source).result()
        self.assertSentence(result, expected)

    def test_multiline_expression(self):
        source   = """UIAlertView* alert = [[[UIAlertView alloc] initWithTitle:@"Warning"
                                                                       message:@"too many alerts"
                                                                      delegate:nil
                                                             cancelButtonTitle:@"OK"
                                                             otherButtonTitles:nil] autorelease];
                      [alert show]"""
        expected = """alert = UIAlertView.alloc.initWithTitle("Warning", message:"too many alerts", delegate:nil, cancelButtonTitle:"OK", otherButtonTitles:nil)
                      alert.show"""
        result = CodeConverter(source).result()
        self.assertSentence(result, expected)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_number
import unittest, os, sys
from custom_test_case import CustomTestCase

PROJECT_ROOT = os.path.dirname(__file__)
sys.path.append(os.path.join(PROJECT_ROOT, ".."))

from CodeConverter import CodeConverter

class TestNumber(unittest.TestCase, CustomTestCase):

    def test_convert_float(self):
        source   = 'CGRect rect = CGRectMake(100.0f, 100.0f, 10.5f, 10.5f);'
        expected = 'CGRect rect = CGRectMake(100, 100, 10.5, 10.5);'
        self.assertSentence(CodeConverter(source).convert_float().s, expected)

    def test_convert_cg_rect_make(self):
        source   = 'CGRectMake( 100 , 100 , 10.5 , 10.5 )'
        expected = '[[100, 100], [10.5, 10.5]]'
        self.assertSentence(CodeConverter(source).convert_cg_rect_make().s, expected)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_replace
import unittest, os, sys
from custom_test_case import CustomTestCase

PROJECT_ROOT = os.path.dirname(__file__)
sys.path.append(os.path.join(PROJECT_ROOT, ".."))

from CodeConverter import CodeConverter

class TestReplace(unittest.TestCase, CustomTestCase):

    def test_replace_nsstring(self):
        source   = 'NSDictionary *updatedLatte = [responseObject objectForKey:@"latte"];'
        expected = 'NSDictionary *updatedLatte = [responseObject objectForKey:"latte"];'
        self.assertSentence(CodeConverter(source).replace_nsstring().s, expected)

    def test_convert_square_brackets_expression(self):
        source   = '[self notifyCreated];'
        expected = 'self.notifyCreated;'
        self.assertSentence(CodeConverter(source).convert_square_brackets_expression().s, expected)

    def test_convert_square_brackets_expression_with_args(self):
        source   = '[self updateFromJSON:updatedLatte];'
        expected = 'self.updateFromJSON(updatedLatte);'
        self.assertSentence(CodeConverter(source).convert_square_brackets_expression().s, expected)

    def test_convert_square_brackets_expression_with_multiple_args(self):
        source   = '[[[UITabBarItem alloc] initWithTabBarSystemItem:UITabBarSystemItemBookmarks tag:0] autorelease];'
        expected = 'UITabBarItem.alloc.initWithTabBarSystemItem(UITabBarSystemItemBookmarks,tag:0).autorelease;'
        self.assertSentence(CodeConverter(source).convert_square_brackets_expression().s, expected)

    def test_remove_semicolon_at_the_end(self):
        source   = '[[[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]] autorelease];'
        expected = '[[[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]] autorelease]'
        self.assertSentence(CodeConverter(source).remove_semicolon_at_the_end().s, expected)

    def test_remove_autorelease(self):
        source   = '[[[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]] autorelease]'
        expected = 'UIWindow.alloc.initWithFrame(UIScreen.mainScreen.bounds)'
        obj = CodeConverter(source).convert_square_brackets_expression()
        obj.remove_autorelease()
        self.assertSentence(obj.s, expected)

    def test_remove_type_declaration(self):
        source   = 'UIWindow* aWindow = [[[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]] autorelease]'
        expected = 'aWindow = [[[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]] autorelease]'
        self.assertSentence(CodeConverter(source).remove_type_declaration().s, expected)

    def test_remove_type_declaration_with_lead_spaces(self):
        source   = '    UIWindow* aWindow = [[[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]] autorelease]'
        expected = '    aWindow = [[[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]] autorelease]'
        self.assertSentence(CodeConverter(source).remove_type_declaration().s, expected)

    def test_converts_boolean_yes(self):
        source = '[button setAttr:YES];'
        expected = '[button setAttr:true];'
        self.assertSentence(CodeConverter(source).convert_boolean().s, expected)

    def test_converts_boolean_no(self):
        source = '[button setAttr:NO];'
        expected = '[button setAttr:false];'
        self.assertSentence(CodeConverter(source).convert_boolean().s, expected)

    def test_avoid_unexpected_replacement_for_boolean(self):
        source = '[ZNOAuth foo:"NOW"];'
        expected = '[ZNOAuth foo:"NOW"];'
        self.assertSentence(CodeConverter(source).convert_boolean().s, expected)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_replace_all
import unittest, os, sys
from custom_test_case import CustomTestCase

PROJECT_ROOT = os.path.dirname(__file__)
sys.path.append(os.path.join(PROJECT_ROOT, ".."))

from CodeConverter import CodeConverter

class TestReplaceAll(unittest.TestCase, CustomTestCase):

    # All replacement
    def test_replace_objc(self):
        source   = 'UIWindow* aWindow = [[[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]] autorelease];'
        expected = 'aWindow = UIWindow.alloc.initWithFrame(UIScreen.mainScreen.bounds)'
        self.assertSentence(CodeConverter(source).result(), expected)

    def test_block_with_two_args_in_one_line(self):
        source   = """[aSet enumerateObjectsUsingBlock:^(id obj, BOOL *stop){ obj = nil; } ];"""
        expected = """aSet.enumerateObjectsUsingBlock(->|obj,stop|{ obj = nil } )"""
        self.assertSentence(CodeConverter(source).result(), expected)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_tidy
import unittest, os, sys
from custom_test_case import CustomTestCase

PROJECT_ROOT = os.path.dirname(__file__)
sys.path.append(os.path.join(PROJECT_ROOT, ".."))

from CodeConverter import CodeConverter

class TestTidy(unittest.TestCase, CustomTestCase):

    def test_tidy_args(self):
        source   = """UITabBarItem.alloc.initWithTabBarSystemItem(UITabBarSystemItemBookmarks,tag:0)"""
        expected = """UITabBarItem.alloc.initWithTabBarSystemItem(UITabBarSystemItemBookmarks, tag:0)"""
        self.assertSentence(CodeConverter(source).tidy_up().s, expected)

    def test_tidy_args(self):
        source   = 'NSLog(@"test,string:")'
        expected = 'NSLog("test,string:")'
        self.assertSentence(CodeConverter(source).result(), expected)

    def test_tidy_args_with_block(self):
        source   = """UIView.animateWithDuration(0.2,animations:->{ view.alpha = 0.0 })"""
        expected = """UIView.animateWithDuration(0.2, animations: -> { view.alpha = 0.0 })"""
        self.assertSentence(CodeConverter(source).result(), expected)

    def test_tidy_block_with_one_args(self):
        source   = """[UIView animateWithDuration:0.2
                             animations:^{ view.alpha = 0.0; }
                             completion:^( BOOL finished ){ [view removeFromSuperview]; }];"""
        expected = """UIView.animateWithDuration(0.2, animations: -> { view.alpha = 0.0 }, completion: -> finished { view.removeFromSuperview })"""
        self.assertSentence(CodeConverter(source).result(), expected)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
