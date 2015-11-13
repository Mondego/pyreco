__FILENAME__ = arguments
from classytags.exceptions import InvalidFlag
from classytags.utils import TemplateConstant, NULL, mixin
from classytags.values import (StringValue, IntegerValue, ListValue, ChoiceValue, 
    DictValue, StrictStringValue)
from django import template
from django.core.exceptions import ImproperlyConfigured


class Argument(object):
    """
    A basic single value argument.
    """
    value_class = StringValue

    def __init__(self, name, default=None, required=True, resolve=True):
        self.name = name
        self.default = default
        self.required = required
        self.resolve = resolve

    def __repr__(self):  # pragma: no cover
        return '<%s: %s>' % (self.__class__.__name__, self.name)

    def get_default(self):
        """
        Get the default value
        """
        return TemplateConstant(self.default)

    def parse_token(self, parser, token):
        if self.resolve:
            return parser.compile_filter(token)
        else:
            return TemplateConstant(token)

    def parse(self, parser, token, tagname, kwargs):
        """
        Parse a token.
        """
        if self.name in kwargs:
            return False
        else:
            value = self.parse_token(parser, token)
            kwargs[self.name] = self.value_class(value)
            return True


class StringArgument(Argument):
    value_class = StrictStringValue


class KeywordArgument(Argument):
    """
    A single 'key=value' argument
    """
    wrapper_class = DictValue

    def __init__(self, name, default=None, required=True, resolve=True,
                 defaultkey=None, splitter='='):
        super(KeywordArgument, self).__init__(name, default, required, resolve)
        self.defaultkey = defaultkey
        self.splitter = splitter

    def get_default(self):
        if self.defaultkey:
            return self.wrapper_class({
                self.defaultkey: TemplateConstant(self.default)
            })
        else:
            return self.wrapper_class({})

    def parse_token(self, parser, token):
        if self.splitter in token:
            key, raw_value = token.split(self.splitter, 1)
            value = super(KeywordArgument, self).parse_token(parser, raw_value)
        else:
            key = self.defaultkey
            value = super(KeywordArgument, self).parse_token(parser, token)
        return key, self.value_class(value)

    def parse(self, parser, token, tagname, kwargs):
        if self.name in kwargs:  # pragma: no cover
            return False
        else:
            key, value = self.parse_token(parser, token)
            kwargs[self.name] = self.wrapper_class({
                key: value
            })
            return True


class IntegerArgument(Argument):
    """
    Same as Argument but converts the value to integers.
    """
    value_class = IntegerValue


class ChoiceArgument(Argument):
    """
    An Argument which checks if it's value is in a predefined list of choices.
    """

    def __init__(self, name, choices, default=None, required=True,
                 resolve=True):
        super(ChoiceArgument, self).__init__(name, default, required, resolve)
        if default or not required:
            value_on_error = default
        else:
            value_on_error = choices[0]
        self.value_class = mixin(
            self.value_class,
            ChoiceValue,
            attrs={
                'choices': choices,
                'value_on_error': value_on_error,
            }
        )


class MultiValueArgument(Argument):
    """
    An argument which allows multiple values.
    """
    sequence_class = ListValue
    value_class = StringValue

    def __init__(self, name, default=NULL, required=True, max_values=None,
                 resolve=True):
        self.max_values = max_values
        if default is NULL:
            default = []
        else:
            required = False
        super(MultiValueArgument, self).__init__(name, default, required,
                                                 resolve)

    def parse(self, parser, token, tagname, kwargs):
        """
        Parse a token.
        """
        value = self.value_class(self.parse_token(parser, token))
        if self.name in kwargs:
            if self.max_values and len(kwargs[self.name]) == self.max_values:
                return False
            kwargs[self.name].append(value)
        else:
            kwargs[self.name] = self.sequence_class(value)
        return True


class MultiKeywordArgument(KeywordArgument):
    def __init__(self, name, default=None, required=True, resolve=True,
                 max_values=None, splitter='='):
        if not default:
            default = {}
        else:
            default = dict(default)
        super(MultiKeywordArgument, self).__init__(name, default, required,
                                                   resolve, NULL, splitter)
        self.max_values = max_values

    def get_default(self):
        items = self.default.items()
        return self.wrapper_class(
            dict([(key, TemplateConstant(value)) for key, value in items])
        )

    def parse(self, parser, token, tagname, kwargs):
        key, value = self.parse_token(parser, token)
        if key is NULL:
            raise template.TemplateSyntaxError(
                "MultiKeywordArgument arguments require key=value pairs"
            )
        if self.name in kwargs:
            if self.max_values and len(kwargs[self.name]) == self.max_values:
                return False
            kwargs[self.name][key] = value
        else:
            kwargs[self.name] = self.wrapper_class({
                key: value
            })
        return True


class Flag(Argument):
    """
    A boolean flag
    """
    def __init__(self, name, default=NULL, true_values=None, false_values=None,
                 case_sensitive=False):
        if default is not NULL:
            required = False
        else:
            required = True
        super(Flag, self).__init__(name, default, required)
        if true_values is None:
            true_values = []
        if false_values is None:
            false_values = []
        if case_sensitive:
            self.mod = lambda x: x
        else:
            self.mod = lambda x: str(x).lower()
        self.true_values = [self.mod(tv) for tv in true_values]
        self.false_values = [self.mod(fv) for fv in false_values]
        if not any([self.true_values, self.false_values]):
            raise ImproperlyConfigured(
                "Flag must specify either true_values and/or false_values"
            )

    def parse(self, parser, token, tagname, kwargs):
        """
        Parse a token.
        """
        ltoken = self.mod(token)
        if self.name in kwargs:
            return False
        if self.true_values and ltoken in self.true_values:
            kwargs[self.name] = TemplateConstant(True)
        elif self.false_values and ltoken in self.false_values:
            kwargs[self.name] = TemplateConstant(False)
        elif self.default is NULL:
            allowed_values = []
            if self.true_values:
                allowed_values += self.true_values
            if self.false_values:
                allowed_values += self.false_values
            raise InvalidFlag(self.name, token, allowed_values, tagname)
        else:
            kwargs[self.name] = self.get_default()
        return True

########NEW FILE########
__FILENAME__ = blocks
# -*- coding: utf-8 -*-
from django.core.exceptions import ImproperlyConfigured


def _collect(name, parser):
    collector = getattr(name, 'collect', None)
    if callable(collector):
        return collector(parser)
    return name


class BlockDefinition(object):
    """
    Definition of 'parse-until-blocks' used by the parser.
    """
    def __init__(self, alias, *names):
        self.alias = alias
        self.names = names

    def validate(self, options):
        for name in self.names:
            validator = getattr(name, 'validate', None)
            if callable(validator):
                validator(options)

    def collect(self, parser):
        return [_collect(name, parser) for name in self.names]


class VariableBlockName(object):
    def __init__(self, template, argname):
        self.template = template
        self.argname = argname

    def validate(self, options):
        if self.argname not in options.all_argument_names:
            raise ImproperlyConfigured(
                "Invalid block definition, %r not a valid argument name, "
                "available argument names: %r" % (self.argname,
                                                  options.all_argument_names)
            )

    def collect(self, parser):
        value = parser.kwargs[self.argname]
        return self.template % {'value': value.literal}

########NEW FILE########
__FILENAME__ = compat
# -*- coding: utf-8 -*-

try:  # pragma: no cover
    compat_basestring = basestring
except NameError:
    compat_basestring = str

try:
    compat_next = next
except NameError:  # pragma: no cover
    def compat_next(it):
        return it.next()

########NEW FILE########
__FILENAME__ = core
from classytags.blocks import BlockDefinition
from classytags.compat import compat_basestring
from classytags.parser import Parser
from classytags.utils import StructuredOptions, get_default_name
from django.template import Node


class Options(object):
    """
    Option class holding the arguments of a tag.
    """
    def __init__(self, *options, **kwargs):
        self.options = {}
        self.breakpoints = []
        self.combined_breakpoints = {}
        current_breakpoint = None
        last = None
        self.options[current_breakpoint] = []
        self.all_argument_names = []
        for value in options:
            if isinstance(value, compat_basestring):
                if isinstance(last, compat_basestring):
                    self.combined_breakpoints[last] = value
                self.breakpoints.append(value)
                current_breakpoint = value
                self.options[current_breakpoint] = []
            else:
                self.options[current_breakpoint].append(value)
                self.all_argument_names.append(value.name)
            last = value
        self.blocks = []
        for block in kwargs.get('blocks', []):
            if isinstance(block, BlockDefinition):
                block_definition = block
            elif isinstance(block, compat_basestring):
                block_definition = BlockDefinition(block, block)
            else:
                block_definition = BlockDefinition(block[1], block[0])
            block_definition.validate(self)
            self.blocks.append(block_definition)
        if 'parser_class' in kwargs:
            self.parser_class = kwargs['parser_class']
        else:
            self.parser_class = Parser

    def get_parser_class(self):
        return self.parser_class

    def bootstrap(self):
        """
        Bootstrap this options
        """
        return StructuredOptions(self.options, self.breakpoints, self.blocks, self.combined_breakpoints)

    def parse(self, parser, tokens):
        """
        Parse template tokens into a dictionary
        """
        argument_parser_class = self.get_parser_class()
        argument_parser = argument_parser_class(self)
        return argument_parser.parse(parser, tokens)


class TagMeta(type):
    """
    Metaclass for the Tag class that set's the name attribute onto the class
    and a _decorated_function pseudo-function which is used by Django's
    template system to get the tag name.
    """
    def __new__(cls, name, bases, attrs):
        parents = [base for base in bases if isinstance(base, TagMeta)]
        if not parents:
            return super(TagMeta, cls).__new__(cls, name, bases, attrs)
        tag_name = str(attrs.get('name', get_default_name(name)))

        def fake_func():
            pass  # pragma: no cover

        fake_func.__name__ = tag_name
        attrs['_decorated_function'] = fake_func
        attrs['name'] = str(tag_name)
        return super(TagMeta, cls).__new__(cls, name, bases, attrs)


class Tag(TagMeta('TagMeta', (Node,), {})):
    """
    Main Tag class.
    """
    options = Options()

    def __init__(self, parser, tokens):
        self.kwargs, self.blocks = self.options.parse(parser, tokens)
        self.child_nodelists = []
        for key, value in self.blocks.items():
            setattr(self, key, value)
            self.child_nodelists.append(key)

    def render(self, context):
        """
        INTERNAL method to prepare rendering
        Usually you should not override this method, but rather use render_tag.
        """
        items = self.kwargs.items()
        kwargs = dict([(key, value.resolve(context)) for key, value in items])
        kwargs.update(self.blocks)
        return self.render_tag(context, **kwargs)

    def render_tag(self, context, **kwargs):
        """
        The method you should override in your custom tags
        """
        raise NotImplementedError

    def __repr__(self):
        return '<Tag: %s>' % self.name

########NEW FILE########
__FILENAME__ = exceptions
from django.template import TemplateSyntaxError

__all__ = ['ArgumentRequiredError', 'InvalidFlag', 'BreakpointExpected',
           'TooManyArguments']


class BaseError(TemplateSyntaxError):
    template = ''

    def __str__(self):  # pragma: no cover
        return self.template % self.__dict__


class ArgumentRequiredError(BaseError):
    template = "The tag '%(tagname)s' requires the '%(argname)s' argument."

    def __init__(self, argument, tagname):
        self.argument = argument
        self.tagname = tagname
        self.argname = self.argument.name


class InvalidFlag(BaseError):
    template = ("The flag '%(argname)s' for the tag '%(tagname)s' must be one "
                "of %(allowed_values)s, but got '%(actual_value)s'")

    def __init__(self, argname, actual_value, allowed_values, tagname):
        self.argname = argname
        self.tagname = tagname
        self.actual_value = actual_value
        self.allowed_values = allowed_values


class BreakpointExpected(BaseError):
    template = ("Expected one of the following breakpoints: %(breakpoints)s "
                "in %(tagname)s, got '%(got)s' instead.")

    def __init__(self, tagname, breakpoints, got):
        self.breakpoints = ', '.join(["'%s'" % bp for bp in breakpoints])
        self.tagname = tagname
        self.got = got


class TrailingBreakpoint(BaseError):
    template = ("Tag %(tagname)s ends in trailing breakpoint '%(breakpoint)s' without an argument following.")

    def __init__(self, tagname, breakpoint):
        self.tagname = tagname
        self.breakpoint = breakpoint


class TooManyArguments(BaseError):
    template = "The tag '%(tagname)s' got too many arguments: %(extra)s"

    def __init__(self, tagname, extra):
        self.tagname = tagname
        self.extra = ', '.join(["'%s'" % e for e in extra])


class TemplateSyntaxWarning(Warning):
    """
    Used for variable cleaning TemplateSyntaxErrors when in non-debug-mode.
    """

########NEW FILE########
__FILENAME__ = helpers
from classytags.core import Tag
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string


class AsTag(Tag):
    """
    Same as tag but allows for an optional 'as varname'. The 'as varname'
    options must be added 'manually' to the options class.
    """
    def __init__(self, parser, tokens):
        super(AsTag, self).__init__(parser, tokens)
        if len(self.options.breakpoints) < 1:
            raise ImproperlyConfigured(
                "AsTag subclasses require at least one breakpoint."
            )
        last_breakpoint = self.options.options[self.options.breakpoints[-1]]
        optscount = len(last_breakpoint)
        if optscount != 1:
            raise ImproperlyConfigured(
                "The last breakpoint of AsTag subclasses require exactly one "
                "argument, got %s instead." % optscount
            )
        self.varname_name = last_breakpoint[-1].name

    def render_tag(self, context, **kwargs):
        """
        INTERNAL!

        Get's the value for the current context and arguments and puts it into
        the context if needed or returns it.
        """
        varname = kwargs.pop(self.varname_name)
        if varname:
            value = self.get_value_for_context(context, **kwargs)
            context[varname] = value
            return ''
        else:
            value = self.get_value(context, **kwargs)
        return value

    def get_value_for_context(self, context, **kwargs):
        """
        Called when a value for a varname (in the "as varname" case) should is
        requested. This can be used to for example suppress exceptions in this
        case.

        Returns the value to be set.
        """
        return self.get_value(context, **kwargs)

    def get_value(self, context, **kwargs):
        """
        Returns the value for the current context and arguments.
        """
        raise NotImplementedError


class InclusionTag(Tag):
    """
    A helper Tag class which allows easy inclusion tags.

    The template attribute must be set.

    Instead of render_tag, override get_context in your subclasses.

    Optionally override get_template in your subclasses.
    """
    template = None

    def render_tag(self, context, **kwargs):
        """
        INTERNAL!

        Gets the context and data to render.
        """
        template = self.get_template(context, **kwargs)
        data = self.get_context(context, **kwargs)
        output = render_to_string(template, data)
        return output

    def get_template(self, context, **kwargs):
        """
        Returns the template to be used for the current context and arguments.
        """
        return self.template

    def get_context(self, context, **kwargs):
        """
        Returns the context to render the template with.
        """
        return {}

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = parser
from classytags.exceptions import (BreakpointExpected, TooManyArguments,
    ArgumentRequiredError, TrailingBreakpoint)
from copy import deepcopy
from django import template


class Parser(object):
    """
    Argument parsing class. A new instance of this gets created each time a tag
    get's parsed.
    """
    def __init__(self, options):
        self.options = options.bootstrap()

    def parse(self, parser, tokens):
        """
        Parse a token stream
        """
        self.parser = parser
        self.bits = tokens.split_contents()
        self.tagname = self.bits.pop(0)
        self.kwargs = {}
        self.blocks = {}
        self.forced_next = None
        # Get the first chunk of arguments until the next breakpoint
        self.arguments = self.options.get_arguments()
        self.current_argument = None
        # get a copy of the bits (tokens)
        self.todo = list(self.bits)
        # parse the bits (tokens)
        breakpoint = False
        for bit in self.bits:
            breakpoint = self.handle_bit(bit)
        if breakpoint:
            raise TrailingBreakpoint(self.tagname, breakpoint)
        # finish the bits (tokens)
        self.finish()
        # parse block tags
        self.parse_blocks()
        return self.kwargs, self.blocks

    def handle_bit(self, bit):
        """
        Handle the current bit
        """
        breakpoint = False
        if self.forced_next is not None:
            if bit != self.forced_next:
                raise BreakpointExpected(self.tagname, [self.forced_next], bit)
        elif bit in self.options.reversed_combined_breakpoints:
            expected = self.options.reversed_combined_breakpoints[bit]
            raise BreakpointExpected(self.tagname, [expected], bit)
        # Check if the current bit is the next breakpoint
        if bit == self.options.next_breakpoint:
            self.handle_next_breakpoint(bit)
            breakpoint = bit
        # Check if the current bit is a future breakpoint
        elif bit in self.options.breakpoints:
            self.handle_breakpoints(bit)
            breakpoint = bit
        # Otherwise it's a 'normal' argument
        else:
            self.handle_argument(bit)
        if bit in self.options.combined_breakpoints:
            self.forced_next = self.options.combined_breakpoints[bit]
        else:
            self.forced_next = None
        # remove from todos
        del self.todo[0]
        return breakpoint

    def handle_next_breakpoint(self, bit):
        """
        Handle a bit which is the next breakpoint by checking the current
        breakpoint scope is finished or can be finished and then shift to the
        next scope.
        """
        # Check if any unhandled argument in the current breakpoint is required
        self.check_required()
        # Shift the breakpoint to the next one
        self.options.shift_breakpoint()
        # Get the next chunk of arguments
        self.arguments = self.options.get_arguments()
        if self.arguments:
            self.current_argument = self.arguments.pop(0)
        else:
            self.current_argument = None

    def handle_breakpoints(self, bit):
        """
        Handle a bit which is a future breakpoint by trying to finish all
        intermediate breakpoint codes as well as the current scope and then
        shift.
        """
        # While we're not at our target breakpoint
        while bit != self.options.current_breakpoint:
            # Check required arguments
            self.check_required()
            # Shift to the next breakpoint
            self.options.shift_breakpoint()
            self.arguments = self.options.get_arguments()
        self.current_argument = self.arguments.pop(0)

    def handle_argument(self, bit):
        """
        Handle the current argument.
        """
        # If we don't have an argument yet
        if self.current_argument is None:
            try:
                # try to get the next one
                self.current_argument = self.arguments.pop(0)
            except IndexError:
                # If we don't have any arguments, left, raise a
                # TooManyArguments error
                raise TooManyArguments(self.tagname, self.todo)
        # parse the current argument and check if this bit was handled by this
        # argument
        handled = self.current_argument.parse(self.parser, bit, self.tagname,
                                              self.kwargs)
        # While this bit is not handled by an argument
        while not handled:
            try:
                # Try to get the next argument
                self.current_argument = self.arguments.pop(0)
            except IndexError:
                # If there is no next argument but there are still breakpoints
                # Raise an exception that we expected a breakpoint
                if self.options.breakpoints:
                    raise BreakpointExpected(self.tagname,
                                             self.options.breakpoints, bit)
                elif self.options.next_breakpoint:
                    raise BreakpointExpected(self.tagname,
                                             [self.options.next_breakpoint],
                                             bit)
                else:
                    # Otherwise raise a TooManyArguments excption
                    raise TooManyArguments(self.tagname, self.todo)
            # Try next argument
            handled = self.current_argument.parse(self.parser, bit,
                                                  self.tagname, self.kwargs)

    def finish(self):
        """
        Finish up parsing by checking all remaining breakpoint scopes
        """
        # Check if there are any required arguments left in the current
        # breakpoint
        self.check_required()
        # While there are still breakpoints left
        while self.options.next_breakpoint:
            # Shift to the next breakpoint
            self.options.shift_breakpoint()
            self.arguments = self.options.get_arguments()
            # And check this breakpoints arguments for required arguments.
            self.check_required()
        #if self.current_argument is not None:
        #    self.arguments = [self.current_argument]
        #    self.check_required()

    def parse_blocks(self):
        """
        Parse template blocks for block tags.

        Example:
            {% a %} b {% c %} d {% e %} f {% g %}
             => pre_c: b
                pre_e: d
                pre_g: f
            {% a %} b {% f %}
             => pre_c: b
                pre_e: None
                pre_g: None
        """
        # if no blocks are defined, bail out
        if not self.options.blocks:
            return
        # copy the blocks
        blocks = deepcopy(self.options.blocks)
        identifiers = {}
        for block in blocks:
            identifiers[block] = block.collect(self)
        while blocks:
            current_block = blocks.pop(0)
            current_identifiers = identifiers[current_block]
            block_identifiers = list(current_identifiers)
            for block in blocks:
                block_identifiers += identifiers[block]
            nodelist = self.parser.parse(block_identifiers)
            token = self.parser.next_token()
            while token.contents not in current_identifiers:
                empty_block = blocks.pop(0)
                current_identifiers = identifiers[empty_block]
                self.blocks[empty_block.alias] = template.NodeList()
            self.blocks[current_block.alias] = nodelist

    def check_required(self):
        """
        Iterate over arguments, checking if they're required, otherwise
        populating the kwargs dictionary with their defaults.
        """
        for argument in self.arguments:
            if argument.required:
                raise ArgumentRequiredError(argument, self.tagname)
            else:
                self.kwargs[argument.name] = argument.get_default()

########NEW FILE########
__FILENAME__ = context_managers
# -*- coding: utf-8 -*-
from django import template
from django.conf import settings


class NULL:
    pass


class SettingsOverride(object):  # pragma: no cover
    """
    Overrides Django settings within a context and resets them to their inital
    values on exit.

    Example:

        with SettingsOverride(DEBUG=True):
            # do something
    """
    def __init__(self, **overrides):
        self.overrides = overrides

    def __enter__(self):
        self.old = {}
        for key, value in self.overrides.items():
            self.old[key] = getattr(settings, key, NULL)
            setattr(settings, key, value)

    def __exit__(self, type, value, traceback):
        for key, value in self.old.items():
            if value is not NULL:
                setattr(settings, key, value)
            else:
                delattr(settings, key)  # do not pollute the context!


class TemplateTags(object):  # pragma: no cover
    def __init__(self, *tags):
        self.lib = template.Library()
        for tag in tags:
            self.lib.tag(tag)

    def __enter__(self):
        self.old = list(template.builtins)
        template.builtins.insert(0, self.lib)

    def __exit__(self, type, value, traceback):
        template.builtins[:] = self.old

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = testrunner
from django.conf import settings  # pragma: no cover
from django.test.simple import DjangoTestSuiteRunner  # pragma: no cover

try:  # pragma: no cover
    from xmlrunner import XMLTestRunner as runner
except:  # pragma: no cover
    runner = False


class TestSuiteRunner(DjangoTestSuiteRunner):  # pragma: no cover
    use_runner = runner

    def run_suite(self, suite, **kwargs):
        if self.use_runner and not self.failfast:
            return self.use_runner(
                output=getattr(settings, 'JUNIT_OUTPUT_DIR', '.')
            ).run(suite)
        else:
            return super(TestSuiteRunner, self).run_suite(suite, **kwargs)

    def setup_databases(self, *args, **kwargs):
        # no need for a database...
        pass
    teardown_databases = setup_databases

########NEW FILE########
__FILENAME__ = run_tests
import sys  # pragma: no cover
import os  # pragma: no cover


def configure_settings(env_name):  # pragma: no cover
    from classytags.test import project
    import classytags

    PROJECT_DIR = os.path.abspath(os.path.dirname(project.__file__))

    MEDIA_ROOT = os.path.join(PROJECT_DIR, 'media')

    TEMPLATE_DIRS = (
        os.path.join(PROJECT_DIR, 'templates'),
    )

    dirname = os.path.dirname(classytags.__file__)
    JUNIT_OUTPUT_DIR = os.path.join(
        os.path.abspath(dirname), '..', 'junit-%s' % env_name
    )

    ADMINS = tuple()
    DEBUG = False

    gettext = lambda x: x

    from django.conf import settings

    settings.configure(
        PROJECT_DIR=PROJECT_DIR,
        DEBUG=DEBUG,
        TEMPLATE_DEBUG=DEBUG,
        ADMINS=ADMINS,
        CACHE_BACKEND='locmem:///',
        MANAGERS=ADMINS,
        TIME_ZONE='America/Chicago',
        SITE_ID=1,
        USE_I18N=True,
        MEDIA_ROOT=MEDIA_ROOT,
        MEDIA_URL='/media/',
        ADMIN_MEDIA_PREFIX='/media_admin/',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        SECRET_KEY='test-secret-key',
        TEMPLATE_LOADERS=(
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
            'django.template.loaders.eggs.Loader',
        ),
        INTERNAL_IPS=('127.0.0.1',),
        ROOT_URLCONF='classytags.test.project.urls',
        TEMPLATE_DIRS=TEMPLATE_DIRS,
        INSTALLED_APPS=(
            'classytags',
            'classytags.test.project',
        ),
        gettext=lambda s: s,
        LANGUAGE_CODE="en-us",
        APPEND_SLASH=True,
        TEST_RUNNER='classytags.test.project.testrunner.TestSuiteRunner',
        JUNIT_OUTPUT_DIR=JUNIT_OUTPUT_DIR
    )

    return settings


def run_tests(*test_args):  # pragma: no cover
    test_args = list(test_args)
    if '--direct' in test_args:
        test_args.remove('--direct')
        dirname = os.path.abspath(os.path.dirname(__file__))
        sys.path.insert(0, os.path.join(dirname, "..", ".."))

    failfast = False

    test_labels = []

    test_args_enum = dict([(val, idx) for idx, val in enumerate(test_args)])

    env_name = ''
    if '--env-name' in test_args:
        env_name = test_args[test_args_enum['--env-name'] + 1]
        test_args.remove('--env-name')
        test_args.remove(env_name)

    if '--failfast' in test_args:
        test_args.remove('--failfast')
        failfast = True

    for label in test_args:
        test_labels.append('classytags.%s' % label)

    if not test_labels:
        test_labels.append('classytags')

    settings = configure_settings(env_name)

    from django.test.utils import get_runner

    runner_class = get_runner(settings)
    runner = runner_class(verbosity=1, interactive=True, failfast=failfast)
    failures = runner.run_tests(test_labels)
    sys.exit(failures)

if __name__ == '__main__':  # pragma: no cover
    run_tests(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = tests
from __future__ import with_statement
from distutils.version import LooseVersion
from classytags import (arguments, core, exceptions, utils, parser, helpers,
    values)
from classytags.blocks import BlockDefinition, VariableBlockName
from classytags.compat import compat_next
from classytags.test.context_managers import SettingsOverride, TemplateTags
import django
from django import template
from django.core.exceptions import ImproperlyConfigured
from unittest import TestCase
import sys
import warnings

DJANGO_1_4_OR_HIGHER = (
    LooseVersion(django.get_version()) >= LooseVersion('1.4')
)


class DummyTokens(list):
    def __init__(self, *tokens):
        super(DummyTokens, self).__init__(['dummy_tag'] + list(tokens))

    def split_contents(self):
        return self


class DummyParser(object):
    @staticmethod
    def compile_filter(token):
        return utils.TemplateConstant(token)
dummy_parser = DummyParser()


class _Warning(object):
    def __init__(self, message, category, filename, lineno):
        self.message = message
        self.category = category
        self.filename = filename
        self.lineno = lineno


def _collect_warnings(observe_warning, f, *args, **kwargs):
    def show_warning(message, category, filename, lineno, file=None,
                     line=None):
        assert isinstance(message, Warning)
        observe_warning(
            _Warning(message.args[0], category, filename, lineno)
        )

    # Disable the per-module cache for every module otherwise if the warning
    # which the caller is expecting us to collect was already emitted it won't
    # be re-emitted by the call to f which happens below.
    for v in sys.modules.values():
        if v is not None:
            try:
                v.__warningregistry__ = None
            except:  # pragma: no cover
                # Don't specify a particular exception type to handle in case
                # some wacky object raises some wacky exception in response to
                # the setattr attempt.
                pass

    orig_filters = warnings.filters[:]
    orig_show = warnings.showwarning
    warnings.simplefilter('always')
    try:
        warnings.showwarning = show_warning
        result = f(*args, **kwargs)
    finally:
        warnings.filters[:] = orig_filters
        warnings.showwarning = orig_show
    return result


class ClassytagsTests(TestCase):
    def failUnlessWarns(self, category, message, f, *args, **kwargs):
        warnings_shown = []
        result = _collect_warnings(warnings_shown.append, f, *args, **kwargs)

        if not warnings_shown:  # pragma: no cover
            self.fail("No warnings emitted")
        first = warnings_shown[0]
        for other in warnings_shown[1:]:  # pragma: no cover
            if ((other.message, other.category) !=
                    (first.message, first.category)):
                self.fail("Can't handle different warnings")
        self.assertEqual(first.message, message)
        self.assertTrue(first.category is category)

        return result
    assertWarns = failUnlessWarns

    def _tag_tester(self, klass, templates):
        """
        Helper method to test a template tag by rendering it and checkout
        output.

        *klass* is a template tag class (subclass of core.Tag)
        *templates* is a sequence of a triple (template-string, output-string,
        context)
        """

        tag_message = ("Rendering of template %(in)r resulted in "
                       "%(realout)r, expected %(out)r using %(ctx)r.")

        with TemplateTags(klass):
            for tpl, out, ctx in templates:
                t = template.Template(tpl)
                c = template.Context(ctx)
                s = t.render(c)
                self.assertEqual(s, out, tag_message % {
                    'in': tpl,
                    'out': out,
                    'ctx': ctx,
                    'realout': s,
                })
                for key, value in ctx.items():
                    self.assertEqual(c.get(key), value)

    def test_simple_parsing(self):
        """
        Test very basic single argument parsing
        """
        options = core.Options(
            arguments.Argument('myarg'),
        )
        dummy_tokens = DummyTokens('myval')
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(len(kwargs), 1)
        dummy_context = {}
        self.assertEqual(kwargs['myarg'].resolve(dummy_context), 'myval')

    def test_simple_parsing_too_many_arguments(self):
        options = core.Options(
            arguments.Argument('myarg'),
        )
        dummy_tokens = DummyTokens('myval', 'myval2')
        self.assertRaises(exceptions.TooManyArguments,
                          options.parse, dummy_parser, dummy_tokens)

    def test_optional_default(self):
        """
        Test basic optional argument parsing
        """
        options = core.Options(
            arguments.Argument('myarg'),
            arguments.Argument('optarg', required=False, default=None),
        )
        dummy_tokens = DummyTokens('myval')
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(len(kwargs), 2)
        dummy_context = {}
        self.assertEqual(kwargs['myarg'].resolve(dummy_context), 'myval')
        self.assertEqual(kwargs['optarg'].resolve(dummy_context), None)

    def test_optional_given(self):
        options = core.Options(
            arguments.Argument('myarg'),
            arguments.Argument('optarg', required=False, default=None),
        )
        dummy_tokens = DummyTokens('myval', 'optval')
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(len(kwargs), 2)
        dummy_context = {}
        self.assertEqual(kwargs['myarg'].resolve(dummy_context), 'myval')
        self.assertEqual(kwargs['optarg'].resolve(dummy_context), 'optval')

    def test_breakpoints_not_enough_arguments(self):
        """
        Test parsing with breakpoints
        """
        options = core.Options(
            arguments.Argument('myarg'),
            'as',
            arguments.Argument('varname'),
            'using',
            arguments.Argument('using'),
        )
        dummy_tokens = DummyTokens('myval')
        self.assertRaises(exceptions.ArgumentRequiredError,
                          options.parse, dummy_parser, dummy_tokens)

    def test_breakpoint_breakpoint_expected(self):
        options = core.Options(
            arguments.Argument('myarg'),
            'as',
            arguments.Argument('varname'),
            'using',
            arguments.Argument('using'),
        )
        dummy_tokens = DummyTokens('myval', 'myname')
        self.assertRaises(exceptions.BreakpointExpected,
                          options.parse, dummy_parser, dummy_tokens)

    def test_breakpoint_breakpoint_expected_second(self):
        options = core.Options(
            arguments.Argument('myarg'),
            'as',
            arguments.Argument('varname'),
            'using',
            arguments.Argument('using'),
        )
        dummy_tokens = DummyTokens('myval', 'as', 'myname', 'something')
        self.assertRaises(exceptions.BreakpointExpected,
                          options.parse, dummy_parser, dummy_tokens)

    def test_breakpoint_trailing(self):
        options = core.Options(
            arguments.Argument('myarg'),
            'as',
            arguments.Argument('varname', required=False),
        )
        dummy_tokens = DummyTokens('myval', 'as')
        self.assertRaises(exceptions.TrailingBreakpoint,
                          options.parse, dummy_parser, dummy_tokens)

    def test_breakpoint_okay(self):
        options = core.Options(
            arguments.Argument('myarg'),
            'as',
            arguments.Argument('varname'),
            'using',
            arguments.Argument('using'),
        )
        dummy_tokens = DummyTokens('myval', 'as', 'myname', 'using',
                                   'something')
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(len(kwargs), 3)
        dummy_context = {}
        self.assertEqual(kwargs['myarg'].resolve(dummy_context), 'myval')
        self.assertEqual(kwargs['varname'].resolve(dummy_context), 'myname')
        self.assertEqual(kwargs['using'].resolve(dummy_context), 'something')

    def test_flag_true_value(self):
        """
        Test flag arguments
        """
        options = core.Options(
            arguments.Flag('myflag', true_values=['on'], false_values=['off'])
        )
        dummy_tokens = DummyTokens('on')
        dummy_context = {}
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(kwargs['myflag'].resolve(dummy_context), True)

    def test_flag_false_value(self):
        options = core.Options(
            arguments.Flag('myflag', true_values=['on'], false_values=['off'])
        )
        dummy_tokens = DummyTokens('off')
        dummy_context = {}
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(kwargs['myflag'].resolve(dummy_context), False)

    def test_flag_wrong_value(self):
        options = core.Options(
            arguments.Flag('myflag', true_values=['on'], false_values=['off'])
        )
        # test exceptions
        dummy_tokens = DummyTokens('myval')
        self.assertRaises(exceptions.InvalidFlag,
                          options.parse, dummy_parser, dummy_tokens)

    def test_flag_wrong_value_no_false(self):
        options = core.Options(
            arguments.Flag('myflag', true_values=['on'])
        )
        dummy_tokens = DummyTokens('myval')
        self.assertRaises(exceptions.InvalidFlag,
                          options.parse, dummy_parser, dummy_tokens)

    def test_flag_wrong_value_no_true(self):
        options = core.Options(
            arguments.Flag('myflag', false_values=['off'])
        )
        dummy_tokens = DummyTokens('myval')
        self.assertRaises(exceptions.InvalidFlag,
                          options.parse, dummy_parser, dummy_tokens)
        self.assertRaises(ImproperlyConfigured, arguments.Flag, 'myflag')

    def test_case_sensitive_flag_typo(self):
        # test case sensitive flag
        options = core.Options(
            arguments.Flag('myflag', true_values=['on'], default=False,
                           case_sensitive=True)
        )
        dummy_tokens = DummyTokens('On')
        dummy_context = {}
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(kwargs['myflag'].resolve(dummy_context), False)

    def test_case_sensitive_flag_okay(self):
        options = core.Options(
            arguments.Flag(
                'myflag',
                true_values=['on'],
                default=False,
                case_sensitive=True
            )
        )
        dummy_tokens = DummyTokens('on')
        dummy_context = {}
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(kwargs['myflag'].resolve(dummy_context), True)

    def test_multiflag(self):
        # test multi-flag
        options = core.Options(
            arguments.Flag('flagone', true_values=['on'], default=False),
            arguments.Flag('flagtwo', false_values=['off'], default=True),
        )
        dummy_tokens = DummyTokens('On', 'On')
        dummy_context = {}
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(kwargs['flagone'].resolve(dummy_context), True)
        self.assertEqual(kwargs['flagtwo'].resolve(dummy_context), True)

    def test_multi_value_single_value(self):
        """
        Test simple multi value arguments
        """
        options = core.Options(
            arguments.MultiValueArgument('myarg')
        )
        # test single token MVA
        dummy_tokens = DummyTokens('myval')
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(len(kwargs), 1)
        dummy_context = {}
        # test resolving to list
        self.assertEqual(kwargs['myarg'].resolve(dummy_context), ['myval'])

    def test_multi_value_two_values(self):
        options = core.Options(
            arguments.MultiValueArgument('myarg')
        )
        # test double token MVA
        dummy_tokens = DummyTokens('myval', 'myval2')
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(len(kwargs), 1)
        dummy_context = {}
        self.assertEqual(kwargs['myarg'].resolve(dummy_context),
                         ['myval', 'myval2'])

    def test_multi_value_three_values(self):
        options = core.Options(
            arguments.MultiValueArgument('myarg')
        )
        # test triple token MVA
        dummy_tokens = DummyTokens('myval', 'myval2', 'myval3')
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(len(kwargs), 1)
        dummy_context = {}
        self.assertEqual(kwargs['myarg'].resolve(dummy_context),
                         ['myval', 'myval2', 'myval3'])

    def test_multi_value_max_values_single(self):
        # test max_values option
        options = core.Options(
            arguments.MultiValueArgument('myarg', max_values=2)
        )
        dummy_tokens = DummyTokens('myval')
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(len(kwargs), 1)
        dummy_context = {}
        self.assertEqual(kwargs['myarg'].resolve(dummy_context), ['myval'])

    def test_multi_value_max_values_double(self):
        options = core.Options(
            arguments.MultiValueArgument('myarg', max_values=2)
        )
        dummy_tokens = DummyTokens('myval', 'myval2')
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(len(kwargs), 1)
        dummy_context = {}
        self.assertEqual(kwargs['myarg'].resolve(dummy_context),
                         ['myval', 'myval2'])

    def test_multi_value_max_values_too_many(self):
        options = core.Options(
            arguments.MultiValueArgument('myarg', max_values=2)
        )
        dummy_tokens = DummyTokens('myval', 'myval2', 'myval3')
        self.assertRaises(exceptions.TooManyArguments,
                          options.parse, dummy_parser, dummy_tokens)

    def test_multi_value_no_resolve(self):
        # test no resolve
        options = core.Options(
            arguments.MultiValueArgument('myarg', resolve=False)
        )
        argparser = parser.Parser(options)
        dummy_tokens = DummyTokens('myval', "'myval2'")
        kwargs, blocks = argparser.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        dummy_context = {}
        self.assertEqual(kwargs['myarg'].resolve(dummy_context),
                         ['myval', 'myval2'])

    def test_multi_value_defaults(self):
        # test default
        options = core.Options(
            arguments.MultiValueArgument('myarg', default=['hello', 'world']),
        )
        argparser = parser.Parser(options)
        dummy_tokens = DummyTokens()
        kwargs, blocks = argparser.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        dummy_context = {}
        self.assertEqual(kwargs['myarg'].resolve(dummy_context),
                         ['hello', 'world'])

    def test_complex_all_arguments(self):
        """
        test a complex tag option parser
        """
        options = core.Options(
            arguments.Argument('singlearg'),
            arguments.MultiValueArgument('multiarg', required=False),
            'as',
            arguments.Argument('varname', required=False),
            'safe',
            arguments.Flag('safe', true_values=['on', 'true'], default=False)
        )
        # test simple 'all arguments given'
        dummy_tokens = DummyTokens(1, 2, 3, 'as', 4, 'safe', 'true')
        dummy_context = {}
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(len(kwargs), 4)
        expected = [
            ('singlearg', 1),
            ('multiarg', [2, 3]),
            ('varname', 4),
            ('safe', True)
        ]
        for key, value in expected:
            self.assertEqual(kwargs[key].resolve(dummy_context), value)

    def test_complex_only_first_argument(self):
        options = core.Options(
            arguments.Argument('singlearg'),
            arguments.MultiValueArgument('multiarg', required=False),
            'as',
            arguments.Argument('varname', required=False),
            'safe',
            arguments.Flag('safe', true_values=['on', 'true'], default=False)
        )
        # test 'only first argument given'
        dummy_tokens = DummyTokens(1)
        dummy_context = {}
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(len(kwargs), 4)
        expected = [
            ('singlearg', 1),
            ('multiarg', []),
            ('varname', None),
            ('safe', False)
        ]
        for key, value in expected:
            self.assertEqual(kwargs[key].resolve(dummy_context), value)

    def test_complext_first_and_last_argument(self):
        options = core.Options(
            arguments.Argument('singlearg'),
            arguments.MultiValueArgument('multiarg', required=False),
            'as',
            arguments.Argument('varname', required=False),
            'safe',
            arguments.Flag('safe', true_values=['on', 'true'], default=False)
        )
        # test first argument and last argument given
        dummy_tokens = DummyTokens(2, 'safe', 'false')
        dummy_context = {}
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(len(kwargs), 4)
        expected = [
            ('singlearg', 2),
            ('multiarg', []),
            ('varname', None),
            ('safe', False)
        ]
        for key, value in expected:
            self.assertEqual(kwargs[key].resolve(dummy_context), value)

    def test_cycle(self):
        """
        This test re-implements django's cycle tag (because it's quite crazy)
        and checks if it works.
        """
        from itertools import cycle as itertools_cycle

        class Cycle(core.Tag):
            name = 'classy_cycle'

            options = core.Options(
                arguments.MultiValueArgument('values'),
                'as',
                arguments.Argument('varname', required=False, resolve=False),
            )

            def render_tag(self, context, values, varname):
                if self not in context.render_context:
                    context.render_context[self] = itertools_cycle(values)
                cycle_iter = context.render_context[self]
                value = compat_next(cycle_iter)
                if varname:
                    context[varname] = value
                return value

        origtpl = template.Template(
            '{% for thing in sequence %}'
            '{% cycle "1" "2" "3" "4" %}'
            '{% endfor %}'
        )
        sequence = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        context = template.Context({'sequence': sequence})
        original = origtpl.render(context)
        with TemplateTags(Cycle):
            classytpl = template.Template(
                '{% for thing in sequence %}'
                '{% classy_cycle "1" "2" "3" "4" %}'
                '{% endfor %}'
            )
            classy = classytpl.render(context)
        self.assertEqual(original, classy)
        origtpl = template.Template(
            '{% for thing in sequence %}'
            '{% cycle "1" "2" "3" "4" as myvarname %}'
            '{% endfor %}'
        )
        sequence = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        context = template.Context({'sequence': sequence})
        original = origtpl.render(context)
        with TemplateTags(Cycle):
            classytpl = template.Template(
                '{% for thing in sequence %}'
                '{% classy_cycle "1" "2" "3" "4" as myvarname %}'
                '{% endfor %}'
            )
            classy = classytpl.render(context)
        self.assertEqual(original, classy)

    def test_naming(self):
        # test implicit naming
        class MyTag(core.Tag):
            pass
        lib = template.Library()
        lib.tag(MyTag)
        msg = "'my_tag' not in %s" % lib.tags.keys()
        self.assertTrue('my_tag' in lib.tags, msg)
        # test explicit naming

        class MyTag2(core.Tag):
            name = 'my_tag_2'

        lib = template.Library()
        lib.tag(MyTag2)
        msg = "'my_tag_2' not in %s" % lib.tags.keys()
        self.assertTrue('my_tag_2' in lib.tags, msg)
        # test named registering
        lib = template.Library()
        lib.tag('my_tag_3', MyTag)
        msg = "'my_tag_3' not in %s" % lib.tags.keys()
        self.assertTrue('my_tag_3' in lib.tags, msg)
        msg = "'my_tag' in %s" % lib.tags.keys()
        self.assertTrue('my_tag' not in lib.tags, msg)
        lib = template.Library()
        lib.tag('my_tag_4', MyTag2)
        msg = "'my_tag_4' not in %s" % lib.tags.keys()
        self.assertTrue('my_tag_4' in lib.tags, msg)
        msg = "'my_tag2' in %s" % lib.tags.keys()
        self.assertTrue('my_tag2' not in lib.tags, msg)

    def test_hello_world(self):
        class Hello(core.Tag):
            options = core.Options(
                arguments.Argument('name', required=False, default='world'),
                'as',
                arguments.Argument('varname', required=False, resolve=False)
            )

            def render_tag(self, context, name, varname):
                output = 'hello %s' % name
                if varname:
                    context[varname] = output
                    return ''
                return output
        tpls = [
            ('{% hello %}', 'hello world', {}),
            ('{% hello "classytags" %}', 'hello classytags', {}),
            ('{% hello as myvar %}', '', {'myvar': 'hello world'}),
            ('{% hello "my friend" as othervar %}', '',
             {'othervar': 'hello my friend'})
        ]
        self._tag_tester(Hello, tpls)

    def test_blocks(self):
        class Blocky(core.Tag):
            options = core.Options(
                blocks=['a', 'b', 'c', 'd', 'e'],
            )

            def render_tag(self, context, **nodelists):
                tpl = "%(a)s;%(b)s;%(c)s;%(d)s;%(e)s"
                data = {}
                for key, value in nodelists.items():
                    data[key] = value.render(context)
                return tpl % data
        templates = [
            ('{% blocky %}1{% a %}2{% b %}3{% c %}4{% d %}5{% e %}',
             '1;2;3;4;5', {},),
            ('{% blocky %}12{% b %}3{% c %}4{% d %}5{% e %}', '12;;3;4;5',
             {},),
            ('{% blocky %}123{% c %}4{% d %}5{% e %}', '123;;;4;5', {},),
            ('{% blocky %}1234{% d %}5{% e %}', '1234;;;;5', {},),
            ('{% blocky %}12345{% e %}', '12345;;;;', {},),
            ('{% blocky %}1{% a %}23{% c %}4{% d %}5{% e %}', '1;23;;4;5',
             {},),
            ('{% blocky %}1{% a %}23{% c %}45{% e %}', '1;23;;45;', {},),
        ]
        self._tag_tester(Blocky, templates)

    def test_astag(self):
        class Dummy(helpers.AsTag):
            options = core.Options(
                'as',
                arguments.Argument('varname', resolve=False, required=False),
            )

            def get_value(self, context):
                return "dummy"
        templates = [
            ('{% dummy %}:{{ varname }}', 'dummy:', {},),
            ('{% dummy as varname %}:{{ varname }}', ':dummy', {},),
        ]
        self._tag_tester(Dummy, templates)

    def test_inclusion_tag(self):
        class Inc(helpers.InclusionTag):
            template = 'test.html'

            options = core.Options(
                arguments.Argument('var'),
            )

            def get_context(self, context, var):
                return {'var': var}
        templates = [
            ('{% inc var %}', 'inc', {'var': 'inc'},),
        ]
        self._tag_tester(Inc, templates)

        class Inc2(helpers.InclusionTag):
            template = 'test.html'

        templates = [
            ('{% inc2 %}', '', {},),
        ]
        self._tag_tester(Inc2, templates)

    def test_integer_variable(self):
        options = core.Options(
            arguments.IntegerArgument('integer', resolve=False),
        )
        # test okay
        with SettingsOverride(DEBUG=False):
            dummy_tokens = DummyTokens('1')
            kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
            dummy_context = {}
            self.assertEqual(kwargs['integer'].resolve(dummy_context), 1)
            # test warning
            dummy_tokens = DummyTokens('one')
            kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
            dummy_context = {}
            one = repr('one')
            message = arguments.IntegerValue.errors['clean'] % {'value': one}
            self.assertWarns(exceptions.TemplateSyntaxWarning,
                             message, kwargs['integer'].resolve, dummy_context)
            self.assertEqual(kwargs['integer'].resolve(dummy_context),
                             values.IntegerValue.value_on_error)
            # test exception
        with SettingsOverride(DEBUG=True):
            dummy_tokens = DummyTokens('one')
            kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
            dummy_context = {}
            message = values.IntegerValue.errors['clean'] % {
                'value': repr('one')
            }
            self.assertRaises(template.TemplateSyntaxError,
                              kwargs['integer'].resolve, dummy_context)
        # test the same as above but with resolving

        class IntegerTag(core.Tag):
            options = core.Options(
                arguments.IntegerArgument('integer')
            )

            def render_tag(self, context, integer):
                return integer

        with TemplateTags(IntegerTag):
            tpl = template.Template("{% integer_tag i %}")
        with SettingsOverride(DEBUG=False):
            # test okay
            context = template.Context({'i': '1'})
            self.assertEqual(tpl.render(context), '1')
            # test warning
            context = template.Context({'i': 'one'})
            message = values.IntegerValue.errors['clean'] % {
                 'value': repr('one')
            }
            self.assertWarns(exceptions.TemplateSyntaxWarning,
                             message, tpl.render, context)
            self.assertEqual(int(tpl.render(context)),
                             values.IntegerValue.value_on_error)
        # test exception
        with SettingsOverride(DEBUG=True):
            context = template.Context({'i': 'one'})
            message = arguments.IntegerValue.errors['clean'] % {'value': one}
            self.assertRaises(template.TemplateSyntaxError, tpl.render,
                              context)
            # reset settings

    def test_not_implemented_errors(self):
        class Fail(core.Tag):
            pass

        class Fail2(helpers.AsTag):
            pass

        class Fail3(helpers.AsTag):
            options = core.Options(
                'as',
            )

        class Fail4(helpers.AsTag):
            options = core.Options(
                'as',
                arguments.Argument('varname', resolve=False),
            )

        if DJANGO_1_4_OR_HIGHER:
            exc_class = NotImplementedError
        else:  # pragma: no cover
            exc_class = template.TemplateSyntaxError

        with TemplateTags(Fail, Fail2, Fail3, Fail4):
            context = template.Context({})
            tpl = template.Template("{% fail %}")
            self.assertRaises(exc_class, tpl.render, context)
            self.assertRaises(ImproperlyConfigured,
                              template.Template, "{% fail2 %}")
            self.assertRaises(ImproperlyConfigured,
                              template.Template, "{% fail3 %}")
            tpl = template.Template("{% fail4 as something %}")
            self.assertRaises(exc_class, tpl.render, context)

    def test_too_many_arguments(self):
        class NoArg(core.Tag):
            pass
        with TemplateTags(NoArg):
            self.assertRaises(exceptions.TooManyArguments,
                              template.Template, "{% no_arg a arg %}")

    def test_choice_argument(self):
        options = core.Options(
            arguments.ChoiceArgument('choice',
                                     choices=['one', 'two', 'three']),
        )
        # this is settings dependant!
        with SettingsOverride(DEBUG=True):
            for good in ('one', 'two', 'three'):
                dummy_tokens = DummyTokens(good)
                kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
                dummy_context = {}
                self.assertEqual(kwargs['choice'].resolve(dummy_context), good)
            bad = 'four'
            dummy_tokens = DummyTokens(bad)
            kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
            dummy_context = {}
            self.assertRaises(template.TemplateSyntaxError,
                              kwargs['choice'].resolve, dummy_context)
        with SettingsOverride(DEBUG=False):
            self.assertEqual(kwargs['choice'].resolve(dummy_context), 'one')
            # test other value class

            class IntegerChoiceArgument(arguments.ChoiceArgument):
                value_class = values.IntegerValue

            default = 2
            options = core.Options(
                IntegerChoiceArgument('choice', choices=[1, 2, 3],
                                      default=default),
            )
        with SettingsOverride(DEBUG=True):
            for good in ('1', '2', '3'):
                dummy_tokens = DummyTokens(good)
                kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
                dummy_context = {}
                self.assertEqual(kwargs['choice'].resolve(dummy_context),
                                 int(good))
            bad = '4'
            dummy_tokens = DummyTokens(bad)
            kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
            dummy_context = {}
            self.assertRaises(template.TemplateSyntaxError,
                              kwargs['choice'].resolve, dummy_context)
        with SettingsOverride(DEBUG=False):
            self.assertEqual(kwargs['choice'].resolve(dummy_context), default)
            # reset settings

    def test_keyword_argument(self):
        class KeywordArgumentTag(core.Tag):
            name = 'kwarg_tag'
            options = core.Options(
                arguments.KeywordArgument('named', defaultkey='defaultkey'),
            )

            def render_tag(self, context, named):
                return '%s:%s' % (
                    list(named.keys())[0], list(named.values())[0]
                )

        ctx = {'key': 'thekey', 'value': 'thevalue'}
        templates = [
            ("{% kwarg_tag key='value' %}", 'key:value', ctx),
            ("{% kwarg_tag 'value' %}", 'defaultkey:value', ctx),
            ("{% kwarg_tag key=value %}", 'key:thevalue', ctx),
            ("{% kwarg_tag value %}", 'defaultkey:thevalue', ctx),
        ]
        self._tag_tester(KeywordArgumentTag, templates)

        class KeywordArgumentTag2(KeywordArgumentTag):
            name = 'kwarg_tag'
            options = core.Options(
                arguments.KeywordArgument(
                    'named',
                    defaultkey='defaultkey',
                    resolve=False,
                    required=False,
                    default='defaultvalue'
                ),
            )

        templates = [
            ("{% kwarg_tag %}", 'defaultkey:defaultvalue', ctx),
            ("{% kwarg_tag key='value' %}", 'key:value', ctx),
            ("{% kwarg_tag 'value' %}", 'defaultkey:value', ctx),
            ("{% kwarg_tag key=value %}", 'key:value', ctx),
            ("{% kwarg_tag value %}", 'defaultkey:value', ctx),
        ]
        self._tag_tester(KeywordArgumentTag2, templates)

    def test_multi_keyword_argument(self):
        opts = core.Options(
            arguments.MultiKeywordArgument('multi', max_values=2),
        )

        class MultiKeywordArgumentTag(core.Tag):
            name = 'multi_kwarg_tag'
            options = opts

            def render_tag(self, context, multi):
                items = sorted(multi.items())
                return ','.join(['%s:%s' % item for item in items])

        ctx = {'key': 'thekey', 'value': 'thevalue'}
        templates = [
            ("{% multi_kwarg_tag key='value' key2='value2' %}",
             'key:value,key2:value2', ctx),
            ("{% multi_kwarg_tag key=value %}", 'key:thevalue', ctx),
        ]
        self._tag_tester(MultiKeywordArgumentTag, templates)
        dummy_tokens = DummyTokens('key="value"', 'key2="value2"',
                                   'key3="value3"')
        self.assertRaises(exceptions.TooManyArguments,
                          opts.parse, dummy_parser, dummy_tokens)

    def test_custom_parser(self):
        class CustomParser(parser.Parser):
            def parse_blocks(self):
                return

        options = core.Options(
            blocks=[
                ('end_my_tag', 'nodelist'),
            ],
            parser_class=CustomParser
        )
        dummy_tokens = DummyTokens()
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})

    def test_repr(self):
        class MyTag(core.Tag):
            name = 'mytag'
        tag = MyTag(dummy_parser, DummyTokens())
        self.assertEqual('<Tag: mytag>', repr(tag))

    def test_non_required_multikwarg(self):
        options = core.Options(
            arguments.MultiKeywordArgument('multi', required=False),
        )
        dummy_tokens = DummyTokens()
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertTrue('multi' in kwargs)
        self.assertEqual(kwargs['multi'], {})
        options = core.Options(
            arguments.MultiKeywordArgument('multi', required=False,
                                           default={'hello': 'world'}),
        )
        dummy_tokens = DummyTokens()
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertTrue('multi' in kwargs)
        self.assertEqual(kwargs['multi'].resolve({}), {'hello': 'world'})

    def test_resolve_kwarg(self):
        class ResolveKwarg(core.Tag):
            name = 'kwarg'
            options = core.Options(
                arguments.KeywordArgument('named'),
            )

            def render_tag(self, context, named):
                return '%s:%s' % (
                    list(named.keys())[0], list(named.values())[0]
                )

        class NoResolveKwarg(core.Tag):
            name = 'kwarg'
            options = core.Options(
                arguments.KeywordArgument('named', resolve=False),
            )

            def render_tag(self, context, named):
                return '%s:%s' % (
                    list(named.keys())[0], list(named.values())[0]
                )

        resolve_templates = [
            ("{% kwarg key=value %}", "key:test", {'value': 'test'}),
            ("{% kwarg key='value' %}", "key:value", {'value': 'test'}),
        ]

        noresolve_templates = [
            ("{% kwarg key=value %}", "key:value", {'value': 'test'}),
        ]

        self._tag_tester(ResolveKwarg, resolve_templates)
        self._tag_tester(NoResolveKwarg, noresolve_templates)

    def test_kwarg_default(self):
        options = core.Options(
            arguments.KeywordArgument('kwarg', required=False,
                                      defaultkey='mykey'),
        )
        dummy_tokens = DummyTokens()
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertTrue('kwarg' in kwargs)
        self.assertEqual(kwargs['kwarg'].resolve({}), {'mykey': None})
        options = core.Options(
            arguments.KeywordArgument('kwarg', required=False,
                                      default='hello'),
        )
        dummy_tokens = DummyTokens()
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertTrue('kwarg' in kwargs)
        self.assertEqual(kwargs['kwarg'].resolve({}), {})
        options = core.Options(
            arguments.KeywordArgument('kwarg', required=False,
                                      default='hello', defaultkey='key'),
        )
        dummy_tokens = DummyTokens()
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertTrue('kwarg' in kwargs)
        self.assertEqual(kwargs['kwarg'].resolve({}), {'key': 'hello'})

    def test_multikwarg_no_key(self):
        options = core.Options(
            arguments.MultiKeywordArgument('multi'),
        )
        with SettingsOverride(DEBUG=True):
            dummy_tokens = DummyTokens('value')
            self.assertRaises(template.TemplateSyntaxError,
                              options.parse, dummy_parser, dummy_tokens)
        with SettingsOverride(DEBUG=False):
            dummy_tokens = DummyTokens('value')
            self.assertRaises(template.TemplateSyntaxError,
                              options.parse, dummy_parser, dummy_tokens)

    def test_inclusion_tag_context_pollution(self):
        """
        Check the `keep_render_context` and `push_pop_context` attributes on
        InclusionTag work as advertised and prevent 'context pollution'
        """
        class NoPushPop(helpers.InclusionTag):
            template = 'inclusion.html'

            def get_context(self, context):
                return context.update({'pollution': True})

        class Standard(helpers.InclusionTag):
            template = 'inclusion.html'

            def get_context(self, context):
                return {'pollution': True}

        with TemplateTags(NoPushPop, Standard):
            # push pop pollution
            ctx1 = template.Context({'pollution': False})
            tpl1 = template.Template("{% no_push_pop %}")
            tpl1.render(ctx1)
            self.assertEqual(ctx1['pollution'], True)
            ctx2 = template.Context({'pollution': False})
            tpl2 = template.Template("{% standard %}")
            tpl2.render(ctx2)
            self.assertEqual(ctx2['pollution'], False)

    def test_named_block(self):
        class StartBlock(core.Tag):
            options = core.Options(
                arguments.Argument("myarg"),
                blocks=[
                    BlockDefinition("nodelist",
                                    VariableBlockName("end_block %(value)s",
                                                      'myarg'),
                                    "end_block")
                ]
            )

            def render_tag(self, context, myarg, nodelist):
                return "nodelist:%s;myarg:%s" % (nodelist.render(context),
                                                 myarg)

        with TemplateTags(StartBlock):
            ctx = template.Context()
            tpl = template.Template(
                "{% start_block 'hello' %}nodelist-content"
                "{% end_block 'hello' %}"
            )
            output = tpl.render(ctx)
            expected_output = 'nodelist:nodelist-content;myarg:hello'
            self.assertEqual(output, expected_output)

            ctx = template.Context({'hello': 'world'})
            tpl = template.Template(
                "{% start_block hello %}nodelist-content{% end_block hello %}"
            )
            output = tpl.render(ctx)
            expected_output = 'nodelist:nodelist-content;myarg:world'
            self.assertEqual(output, expected_output)

    def test_fail_named_block(self):
        vbn = VariableBlockName('endblock %(value)s', 'myarg')
        self.assertRaises(ImproperlyConfigured, core.Options,
                          blocks=[BlockDefinition('nodelist', vbn)])

    def test_named_block_noresolve(self):
        class StartBlock(core.Tag):
            options = core.Options(
                arguments.Argument("myarg", resolve=False),
                blocks=[
                    BlockDefinition("nodelist",
                                    VariableBlockName("end_block %(value)s",
                                                      'myarg'),
                                    "end_block")
                ]
            )

            def render_tag(self, context, myarg, nodelist):
                return "nodelist:%s;myarg:%s" % (nodelist.render(context),
                                                 myarg)

        with TemplateTags(StartBlock):
            ctx = template.Context()
            tpl = template.Template(
                "{% start_block 'hello' %}nodelist-content"
                "{% end_block 'hello' %}"
            )
            output = tpl.render(ctx)
            expected_output = 'nodelist:nodelist-content;myarg:hello'
            self.assertEqual(output, expected_output)

    def test_strict_string(self):
        options = core.Options(
            arguments.StringArgument('string', resolve=False),
        )
        with SettingsOverride(DEBUG=False):
            #test ok
            dummy_tokens = DummyTokens('string')
            kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
            dummy_context = {}
            self.assertEqual(
                kwargs['string'].resolve(dummy_context), 'string'
            )
            #test warning
            dummy_tokens = DummyTokens(1)
            kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
            dummy_context = {}
            message = values.StrictStringValue.errors['clean'] % {
                'value': repr(1)
            }
            self.assertWarns(
                exceptions.TemplateSyntaxWarning,
                message,
                kwargs['string'].resolve,
                dummy_context
            )
        with SettingsOverride(DEBUG=True):
            # test exception
            dummy_tokens = DummyTokens(1)
            kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
            dummy_context = {}
            self.assertRaises(
                template.TemplateSyntaxError,
                kwargs['string'].resolve,
                dummy_context
            )

    def test_get_value_for_context(self):
        message = 'exception handled'

        class MyException(Exception):
            pass

        class SuppressException(helpers.AsTag):
            options = core.Options(
                arguments.Argument('name'),
                'as',
                arguments.Argument('var', resolve=False, required=False),
            )

            def get_value(self, context, name):
                raise MyException(name)

            def get_value_for_context(self, context, name):
                try:
                    return self.get_value(context, name)
                except MyException:
                    return message

        dummy_tokens_with_as = DummyTokens('name', 'as', 'var')
        tag = SuppressException(DummyParser(), dummy_tokens_with_as)
        context = {}
        self.assertEqual(tag.render(context), '')
        self.assertEqual(context['var'], message)

        dummy_tokens_no_as = DummyTokens('name')
        tag = SuppressException(DummyParser(), dummy_tokens_no_as)
        self.assertRaises(MyException, tag.render, {})


class MultiBreakpointTests(TestCase):
    def test_optional_firstonly(self):
        options = core.Options(
            arguments.Argument('first'),
            'also',
            'using',
            arguments.Argument('second', required=False),
        )
        # check only using the first argument
        dummy_tokens = DummyTokens('firstval')
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(len(kwargs), 2)
        dummy_context = {}
        self.assertEqual(kwargs['first'].resolve(dummy_context), 'firstval')
        self.assertEqual(kwargs['second'].resolve(dummy_context), None)
        
    def test_optional_both(self):
        options = core.Options(
            arguments.Argument('first'),
            'also',
            'using',
            arguments.Argument('second', required=False),
        )
        # check using both arguments and both breakpoints
        dummy_tokens = DummyTokens('firstval', 'also', 'using', 'secondval')
        kwargs, blocks = options.parse(dummy_parser, dummy_tokens)
        self.assertEqual(blocks, {})
        self.assertEqual(len(kwargs), 2)
        dummy_context = {}
        self.assertEqual(kwargs['first'].resolve(dummy_context), 'firstval')
        self.assertEqual(kwargs['second'].resolve(dummy_context), 'secondval')
    
    def test_partial_breakpoints(self):
        options = core.Options(
            arguments.Argument('first'),
            'also',
            'using',
            arguments.Argument('second', required=False),
        )
        # check only using the first breakpoint
        dummy_tokens = DummyTokens('firstval', 'also')
        self.assertRaises(
            exceptions.TrailingBreakpoint,
            options.parse, dummy_parser, dummy_tokens
        )
    
    def test_partial_breakpoints_second(self):
        options = core.Options(
            arguments.Argument('first'),
            'also',
            'using',
            arguments.Argument('second', required=False),
        )
        # check only using the second breakpoint
        dummy_tokens = DummyTokens('firstval', 'using')
        self.assertRaises(
            exceptions.BreakpointExpected,
            options.parse, dummy_parser, dummy_tokens
        )
    
    def test_partial_breakpoints_both(self):
        options = core.Options(
            arguments.Argument('first'),
            'also',
            'using',
            arguments.Argument('second', required=False),
        )
        # check only using the first breakpoint
        dummy_tokens = DummyTokens('firstval', 'also', 'secondval')
        # should raise an exception
        self.assertRaises(
            exceptions.BreakpointExpected,
            options.parse, dummy_parser, dummy_tokens
        )
    
    def test_partial_breakpoints_second_both(self):
        options = core.Options(
            arguments.Argument('first'),
            'also',
            'using',
            arguments.Argument('second', required=False),
        )
        # check only using the second breakpoint
        dummy_tokens = DummyTokens('firstval', 'using', 'secondval')
        self.assertRaises(
            exceptions.BreakpointExpected,
            options.parse, dummy_parser, dummy_tokens
        )

    def test_partial_breakpoints_both_trailing(self):
        options = core.Options(
            arguments.Argument('first'),
            'also',
            'using',
            arguments.Argument('second', required=False),
        )
        dummy_tokens = DummyTokens('firstval', 'also', 'using')
        self.assertRaises(
            exceptions.TrailingBreakpoint,
            options.parse, dummy_parser, dummy_tokens
        )

########NEW FILE########
__FILENAME__ = utils
from copy import copy
from classytags.compat import compat_basestring
import re


class NULL:
    """
    Internal type to differentiate between None and No-Input
    """


class TemplateConstant(object):
    """
    A 'constant' internal template variable which basically allows 'resolving'
    returning it's initial value
    """
    def __init__(self, value):
        self.literal = value
        if isinstance(value, compat_basestring):
            self.value = value.strip('"\'')
        else:
            self.value = value

    def __repr__(self):  # pragma: no cover
        return '<TemplateConstant: %s>' % repr(self.value)

    def resolve(self, context):
        return self.value


class StructuredOptions(object):
    """
    Bootstrapped options
    """
    def __init__(self, options, breakpoints, blocks, combind_breakpoints):
        self.options = options
        self.breakpoints = copy(breakpoints)
        self.blocks = copy(blocks)
        self.combined_breakpoints = dict(combind_breakpoints.items())
        self.reversed_combined_breakpoints = dict((v,k) for k,v in combind_breakpoints.items())
        self.current_breakpoint = None
        if self.breakpoints:
            self.next_breakpoint = self.breakpoints.pop(0)
        else:
            self.next_breakpoint = None

    def shift_breakpoint(self):
        """
        Shift to the next breakpoint
        """
        self.current_breakpoint = self.next_breakpoint
        if self.breakpoints:
            self.next_breakpoint = self.breakpoints.pop(0)
        else:
            self.next_breakpoint = None

    def get_arguments(self):
        """
        Get the current arguments
        """
        return copy(self.options[self.current_breakpoint])


_re1 = re.compile('(.)([A-Z][a-z]+)')
_re2 = re.compile('([a-z0-9])([A-Z])')


def get_default_name(name):
    """
    Turns "CamelCase" into "camel_case"
    """
    return _re2.sub(r'\1_\2', _re1.sub(r'\1_\2', name)).lower()


def mixin(parent, child, attrs={}):
    return type(
        '%sx%s' % (parent.__name__, child.__name__),
        (child, parent),
        attrs
    )

########NEW FILE########
__FILENAME__ = values
from classytags.compat import compat_basestring
from classytags.exceptions import TemplateSyntaxWarning
from django import template
from django.conf import settings
import warnings


class StringValue(object):
    errors = {}
    value_on_error = ""

    def __init__(self, var):
        self.var = var
        if hasattr(self.var, 'literal'):  # django.template.base.Variable
            self.literal = self.var.literal
        else:  # django.template.base.FilterExpression
            self.literal = self.var.token

    def resolve(self, context):
        resolved = self.var.resolve(context)
        return self.clean(resolved)

    def clean(self, value):
        return value

    def error(self, value, category):
        data = self.get_extra_error_data()
        data['value'] = repr(value)
        message = self.errors.get(category, "") % data
        if settings.DEBUG:
            raise template.TemplateSyntaxError(message)
        else:
            warnings.warn(message, TemplateSyntaxWarning)
            return self.value_on_error

    def get_extra_error_data(self):
        return {}


class StrictStringValue(StringValue):
    errors = {
        "clean": "%(value)s is not a string",
    }
    value_on_error = ""

    def clean(self, value):
        if not isinstance(value, compat_basestring):
            return self.error(value, "clean")
        return value


class IntegerValue(StringValue):
    errors = {
        "clean": "%(value)s could not be converted to Integer",
    }
    value_on_error = 0

    def clean(self, value):
        try:
            return int(value)
        except ValueError:
            return self.error(value, "clean")


class ListValue(list, StringValue):
    """
    A list of template variables for easy resolving
    """
    def __init__(self, value):
        list.__init__(self)
        self.append(value)

    def resolve(self, context):
        resolved = [item.resolve(context) for item in self]
        return self.clean(resolved)


class DictValue(dict, StringValue):
    def __init__(self, value):
        dict.__init__(self, value)

    def resolve(self, context):
        resolved = dict(
            [(key, value.resolve(context)) for key, value in self.items()]
        )
        return self.clean(resolved)


class ChoiceValue(object):
    errors = {
        "choice": "%(value)s is not a valid choice. Valid choices: "
                  "%(choices)s.",
    }
    choices = []

    def clean(self, value):
        cleaned = super(ChoiceValue, self).clean(value)
        if cleaned in self.choices:
            return cleaned
        else:
            return self.error(cleaned, "choice")

    def get_extra_error_data(self):
        data = super(ChoiceValue, self).get_extra_error_data()
        data['choices'] = self.choices
        return data

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-classy-tags documentation build configuration file, created by
# sphinx-quickstart on Mon Aug  9 21:31:48 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ["sphinx.ext.intersphinx"]

intersphinx_mapping = {'django': ('http://readthedocs.org/projects/eric/django/docs/', None)}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-classy-tags'
copyright = u'2010, Jonas Obrist'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.3'
# The full version, including alpha/beta/rc tags.
release = '0.3.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-classy-tagsdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-classy-tags.tex', u'django-classy-tags Documentation',
   u'Jonas Obrist', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = runtests
# -*- coding: utf-8 -*-
import warnings
import os
import sys

urlpatterns = []

TEMPLATE_DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
}


INSTALLED_APPS = [
    'classytags',
    'classytags.test.project',
]

TEMPLATE_DIRS = [
    os.path.join(os.path.dirname(__file__), 'test_templates'),
]


ROOT_URLCONF = 'runtests'

def main():
    from django.conf import settings
    settings.configure(
        INSTALLED_APPS = INSTALLED_APPS,
        ROOT_URLCONF = ROOT_URLCONF,
        DATABASES = DATABASES,
        TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner',
        TEMPLATE_DIRS = TEMPLATE_DIRS,
        TEMPLATE_DEBUG = TEMPLATE_DEBUG
    )

    # Run the test suite, including the extra validation tests.
    from django.test.utils import get_runner
    TestRunner = get_runner(settings)

    test_runner = TestRunner(verbosity=1, interactive=False, failfast=False)
    warnings.simplefilter("ignore")
    failures = test_runner.run_tests(['classytags'])
    sys.exit(failures)


if __name__ == "__main__":
    main()

########NEW FILE########
