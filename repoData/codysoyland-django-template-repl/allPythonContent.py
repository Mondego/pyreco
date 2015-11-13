__FILENAME__ = runtests
import os, sys
from django.conf import settings

DIRNAME = os.path.dirname(__file__)
sys.path.append(os.path.join(DIRNAME, 'src'))
settings.configure(
    DEBUG=True,
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
        }
    },
    ROOT_URLCONF='template_repl.urls',
    INSTALLED_APPS=(
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.admin',
        'template_repl',
    )
)

from django.test.simple import DjangoTestSuiteRunner
test_runner = DjangoTestSuiteRunner(verbosity=1)
failures = test_runner.run_tests(['template_repl', ])
if failures:
    sys.exit(failures)

########NEW FILE########
__FILENAME__ = completion
from django.template import Lexer, TOKEN_TEXT

class Completer(object):
    """
    Provides command-line completion compatible with readline
    using the `complete` method.

    Completion works by splitting text into three segments, a
    `prefix`, a `pivot`, and a `partial`.

    The prefix is the first part of the line, which does not affect
    guessed completions.

    The pivot is the metacharacter which affects completion. There
    are 4 metacharacters. Each has a separate handler to guess input.

        PIVOT   HANDLER
        -----   -------
        |       filter
        %       tag
        {       variable
        :       variable

    The partial is the third segment. It is used to filter guesses
    provided by the pivot handler. For example, if the pivot is a pipe,
    the pivot handler would guess a list of filters and remove elements
    from the list that don't start with the text in the partial.
    """
    def __init__(self, context, parser):
        self.completion_matches = []
        self.context = context
        self.parser = parser

    def complete(self, text, state):
        """
        This hackjob is the result of how readline calls the completer.
        It calls this method with the same text but an increasing "state"
        value and wants you to return guesses, one at a time, ending with
        None, telling readline you have no more guesses. I'm just using it
        as a kind of wrapper for get_completion_matches().
        """
        if not self.completion_matches and state == 0:
            self.completion_matches = self.get_completion_matches(text)
        try:
            return self.completion_matches.pop()
        except IndexError:
            return None

    def get_completion_matches(self, text):
        """
        Return list of completion matches given the input `text`.
        """
        vars = set()
        for dct in self.context.dicts:
            vars.update(dct.keys())
        vars = list(vars)
        filters = self.parser.filters.keys()
        tags = list(self.parser.tags.keys())
        tags.extend(['endif', 'endifequal', 'endfor', 'endwhile', 'endfilter', 'endcomment'])

        (prefix, pivot, partial) = self._get_completion_ppp(text)

        if pivot == '{':
            possibilities = [' %s' % var for var in vars]
        elif pivot in ' :':
            possibilities = ['%s' % var for var in vars]
        elif pivot == '%':
            possibilities = [' %s' % tag for tag in tags]
        elif pivot == '|':
            possibilities = ['%s' % filt for filt in filters]

        # Filter out possibilites that do not start with the text in the partial
        possibilities = filter(
            lambda poss: poss.startswith(partial),
            possibilities)

        return [(prefix + pivot + poss) for poss in possibilities]

    def _get_completion_ppp(self, text):
        """
        Return tuple containing the prefix, pivot, and partial
        of the current line of input.

            >>> completer._get_completion_ppp('{{')
            ('{', '{', '')
            >>> completer._get_completion_ppp('{{ var }}{% get_')
            ('{{ var }}{', '%', ' get_')

        How it works:
        1. Tokenize text, add first n-1 tokens to "prefix".
        2. Split on final "|%{:". Call it "pivot".
        3. Any text after pivot is called the "partial".
        4. Text prior to the pivot but after the first n-1 tokens
           is appended to the prefix.
        """
        if len(text) == 0:
            return ('', '', '')

        prefix = ''
        partial = ''
        pivot = ''

        tokens = Lexer(text, None).tokenize()

        if tokens[-1].token_type != TOKEN_TEXT:
            return (text, '', '')

        prefix_tokens = tokens[:-1]
        working_area = tokens[-1].contents

        prefix = text[:-len(working_area)]

        # Iterate backwards through string, finding the first
        # occurrence of any of the chars "|%{:". Call it the pivot.
        for index, char in list(enumerate(working_area))[::-1]:
            if char == ' ':
                if ' ' in working_area[:index]:
                    pivot = char
                    break
            if char in '|%{:':
                pivot = char
                break

        # No pivot was found
        if len(pivot) == 0:
            return (text, '', '')

        pieces = working_area.split(pivot)

        prefix += pivot.join(pieces[:-1])
        partial = pieces[-1]

        return (prefix, pivot, partial)

########NEW FILE########
__FILENAME__ = templateshell
from django.core.management.base import BaseCommand
from django.test.utils import setup_test_environment
from django.test.client import Client
from django.template.context import Context
from optparse import make_option
from template_repl import run_shell
from template_repl.utils import pdb_with_context

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-u', '--url', dest='url', help='Preload context from given URL (just the path, such as "/admin/").', default=None),
        make_option('-c', '--context', dest='context', help='Supply context as dictionary. Note: This gets evaled.', default=None),
        make_option('--pdb', dest='use_pdb', action='store_true', help='Use the template context provided by -u or -c in a pdb shell instead of a template shell.', default=False),
    )
    help = 'Shell to interact with the template language. Context can be loaded by passing a URL with -u.'

    def handle(self, url, context, use_pdb, *args, **kwargs):
        if context:
            context_dict = eval(context)
        else:
            context_dict = {}
        context = Context(context_dict)
        if url is not None:
            setup_test_environment()
            client = Client()
            response = client.get(url)
            if not response.context:
                print 'Response for given URL contains no context (code %s).' % response.status_code
            else:
                if isinstance(response.context, Context):
                    context = response.context
                elif type(response.context) == list:
                    context = response.context[0]
                else:
                    try:
                        from django.test.utils import ContextList
                    except ImportError:
                        pass
                    else:
                        if isinstance(response.context, ContextList):
                            # TODO: probably should try to merge all contexts
                            context = response.context[0]
        if use_pdb:
            pdb_with_context(context)
        else:
            run_shell(context)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = repl
import re
import sys
import code
import readline
from django.template import Parser, Lexer, Context, TemplateSyntaxError
from template_repl import get_version
from template_repl.completion import Completer

class TemplateREPL(code.InteractiveConsole, object):
    def __init__(self, parser=None, context=None, output=None):
        """
        The template REPL object has a single parser and context instance
        that persist for the length of the shell session.
        """
        super(TemplateREPL, self).__init__()

        self.context = context or Context()
        self.parser = parser or Parser([])
        self.output = output or sys.stdout
        self.completer = Completer(context = self.context, parser = self.parser)

    def interact(self, banner=None):
        try:
            super(TemplateREPL, self).interact(banner)
        except ExitREPL:
            # Fail silently. This exception is just meant to break
            # out of the interact() call.
            pass

    def runsource(self, source, filename="<input>", symbol="single"):
        """
        readline calls this method with the current source buffer. This method
        can return True to instruct readline to capture another line of input
        using the "..." prompt or return False to tell readline to clear the
        source buffer and capture a new phrase.

        How it works:
        1. Tokenize input.
        2. Load parser with tokens.
        3. Attempt to parse, loading a list with nodes.
        4. If unclosed tag exception is raised, get more user input.
        5. If everything went smoothly, print output, otherwise print exception.
        """
        if source == 'exit':
            raise ExitREPL()
        if not source:
            return False
        tokens = Lexer(source, None).tokenize()
        self.parser.tokens = tokens
        nodes = []
        try:
            try:
                for node in self.parser.parse():
                    nodes.append(node)
            except TemplateSyntaxError as e:
                if e.args[0].startswith('Unclosed tags'):
                    # inside block, so ask for more input
                    return True
                else:
                    raise
            for node in nodes:
                self.output.write('%s' % (node.render(self.context),))
            self.output.write('\n')
            return False
        except:
            self.showtraceback()
            return False

    def raw_input(self, prompt):
        """
        I'm overloading raw_input here so that I can swap out the completer
        before and after each line of input. This is because the completer
        is global. There might be a better way of doing this.

        TODO: I think I need to do a similar hack to fix readline history,
        as history currently gets munged between PDB and template-repl.
        """
        orig_delims = readline.get_completer_delims()
        orig_completer = readline.get_completer()

        readline.set_completer(self.completer.complete)
        readline.set_completer_delims('')

        output = super(TemplateREPL, self).raw_input(prompt)

        readline.set_completer(orig_completer)
        readline.set_completer_delims(orig_delims)

        return output

class ExitREPL(Exception):
    pass

########NEW FILE########
__FILENAME__ = repl
from template_repl import run_shell
from django.template import Node, Library
from template_repl.utils import pdb_with_context
from django.template import TemplateSyntaxError

register = Library()

class REPLNode(Node):
    def __init__(self, use_pdb, *args, **kwargs):
        self.use_pdb = use_pdb
        return super(REPLNode, self).__init__(*args, **kwargs)
    def render(self, context):
        if self.use_pdb:
            pdb_with_context(context)
        else:
            run_shell(context)
        return ''

@register.tag
def repl(parser, token):
    use_pdb = False
    bits = token.contents.split()
    if len(bits) > 1:
        if bits[1] == 'pdb':
            use_pdb = True
        else:
            raise TemplateSyntaxError('The second argument to the "repl" tag, if present, must be "pdb".')
    return REPLNode(use_pdb)

########NEW FILE########
__FILENAME__ = tests
from template_repl.repl import TemplateREPL
from django.template import Context
from django.test import TestCase
from io import StringIO

def mock_interaction(commands, context={}):
    context = Context(context)
    output = ''
    output_buffer = StringIO()
    console = TemplateREPL(output=output_buffer, context=context)
    for command in commands:
        console.push(command)
    output_buffer.seek(0)
    output = output_buffer.read()
    return output

class TestREPL(TestCase):
    def test_simple(self):
        output = mock_interaction(['textnode'])
        self.assertEqual(output, 'textnode\n')
    def test_var(self):
        output = mock_interaction(['{{ a }}'], {'a': 'testvar'})
        self.assertEqual(output, 'testvar\n')
    def test_loop(self):
        output = mock_interaction(
            ['{% for thing in things %}', '{{ thing }}', '{% endfor %}'],
            {'things': ['one', 'two', 'three']}
        )
        self.assertEqual(output, '\none\n\ntwo\n\nthree\n\n')

class TestCompletion(TestCase):
    def setUp(self):
        self.repl = TemplateREPL(
            context = Context({
                'food': ['tacos', 'ice cream', 'sushi'],
                'folly': 'fail',
                'banana': 'nomnom!banana!',
            })
        )

    def assertExactCompletion(self, text, completion):
        """Assert set in `completion` to be identical to completion set"""
        matches = self.repl.completer.get_completion_matches(text)
        self.assertEqual(set(matches), set(completion))

    def assertInCompletion(self, text, completion):
        """Assert all items in `completion` are in the completion set"""
        matches = self.repl.completer.get_completion_matches(text)
        for item in completion:
            self.assert_(item in matches)

    def assertNonCompletion(self, text, completion):
        """Assert all items in `completion` are not in the completion set"""
        matches = self.repl.completer.get_completion_matches(text)
        for item in completion:
            self.assert_(item not in matches)

    def test_variables(self):
        self.assertExactCompletion('{{', ['{{ food', '{{ folly', '{{ banana', '{{ True', '{{ False', '{{ None'])
        self.assertExactCompletion('{{ ', ['{{ food', '{{ folly', '{{ banana', '{{ True', '{{ False', '{{ None'])
        self.assertExactCompletion('{{ T', ['{{ True'])
        self.assertExactCompletion('{{ fo', ['{{ food', '{{ folly'])
        self.assertExactCompletion('{{ foo', ['{{ food'])

    def test_tags(self):
        self.assertInCompletion('{%', ['{% if', '{% for'])
        self.assertInCompletion('{% ', ['{% if', '{% for'])
        self.assertExactCompletion('{% if', ['{% ifequal', '{% if', '{% ifnotequal', '{% ifchanged'])

    # TODO: test filters, space separated variables, and longer expressions with more tokens

    def test_ppp(self):
        """
        Tests for _get_completion_ppp() function which returns the
        "ppp" (Prefix, Pivot, and Partial) for a given input
        """
        self.assertEqual(
            self.repl.completer._get_completion_ppp('{{'),
            ('{', '{', ''))

        self.assertEqual(
            self.repl.completer._get_completion_ppp('{{ var }}{% get_'),
            ('{{ var }}{', '%', ' get_'))

        self.assertEqual(
            self.repl.completer._get_completion_ppp('{% tag %}{{ this|m'),
            ('{% tag %}{{ this', '|', 'm'))

        self.assertEqual(
            self.repl.completer._get_completion_ppp('{{ this|m:'),
            ('{{ this|m', ':', ''))

########NEW FILE########
__FILENAME__ = urls
# This only exists for the test runner.
from django.conf.urls import patterns

urlpatterns = patterns('')

########NEW FILE########
__FILENAME__ = utils
def pdb_with_context(context):
    vars = []
    for context_dict in context.dicts:
        for k, v in context_dict.items():
            vars.append(k)
            locals()[k] = v
    try:
        import ipdb as pdb
    except ImportError:
        import pdb
    pdb.set_trace()

########NEW FILE########
