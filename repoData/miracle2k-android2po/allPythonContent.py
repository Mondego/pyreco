__FILENAME__ = commands
from __future__ import absolute_import

import os
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
from lxml import etree
from babel.messages import pofile, Catalog

from . import convert
from .env import resolve_locale
from .termcolors import colored


__all__ = ('CommandError', 'ExportCommand', 'ImportCommand', 'InitCommand',)


class CommandError(Exception):
    pass


def read_catalog(filename, **kwargs):
    """Helper to read a catalog from a .po file.
    """
    file = open(filename, 'rb')
    try:
        return pofile.read_po(file, **kwargs)
    finally:
        file.close()


def catalog2string(catalog, **kwargs):
    """Helper that returns a babel message catalog as a string.

    This is a simple shortcut around pofile.write_po().
    """
    sf = StringIO.StringIO()
    pofile.write_po(sf, catalog, **kwargs)
    return sf.getvalue()


def xml2string(tree, action):
    """Helper that returns a ``ResourceTree`` as an XML string.

    TODO: It would be cool if this could try to recreate the formatting
    of the original xml file.
    """
    ENCODING = 'utf-8'
    dom = convert.write_xml(tree, warnfunc=action.message)
    return etree.tostring(dom, xml_declaration=True,
                          encoding=ENCODING, pretty_print=True)


def read_xml(action, filename, **kw):
    """Wrapper around the base read_xml() that pipes warnings
    into the given action.

    Also handles errors and returns false if the file is invalid.
    """
    try:
        return convert.read_xml(filename, warnfunc=action.message, **kw)
    except convert.InvalidResourceError, e:
        action.done('failed')
        action.message('Failed parsing "%s": %s' % (filename.rel, e), 'error')
        return False


def xml2po(env, action, *a, **kw):
    """Wrapper around the base xml2po() that uses the filters configured
    by the environment.
    """
    def xml_filter(name):
        for filter in env.config.ignores:
            if filter.match(name):
                return True
    kw['filter'] = xml_filter
    if action:
        kw['warnfunc'] = action.message
    return convert.xml2po(*a, **kw)


def po2xml(env, action, *a, **kw):
    """Wrapper around the base po2xml() that uses the filters configured
    by the environment.
    """
    def po_filter(message):
        if env.config.ignore_fuzzy and message.fuzzy:
            return True
    kw['filter'] = po_filter
    kw['warnfunc'] = action.message
    return convert.po2xml(*a, **kw)


def get_catalog_counts(catalog):
    """Return 3-tuple (total count, number of translated strings, number
    of fuzzy strings), based on the given gettext catalog.
    """
    # Make sure we don't count the header
    return (len(catalog),
            len([m for m in catalog if m.string and m.id]),
            len([m for m in catalog if m.string and m.id and m.fuzzy]))


def list_languages(source, env, writer):
    """Return a list of languages (by simply calling the proper
    environment method.

    However, commands should use this helper rather than working
    with the environment directly, as this outputs helpful
    diagnostic messages along the way.
    """
    assert source in ('gettext', 'android')
    languages = getattr(env,
        'get_gettext_languages' if source=='gettext' else 'get_android_languages')()
    lstr = ", ".join(map(unicode, languages))
    writer.action('info',
                  "Found %d language(s): %s" % (len(languages), lstr))
    writer.message('List of languages was based on %s' % (
        'the existing gettext catalogs' if source=='gettext'
        else 'the existing Android resource directories'
    ))
    return languages


def ensure_directories(cmd, path):
    """Ensure that the given directory exists.
    """
    # Collect all the individual directories we need to create.
    # Yes, I know about os.makedirs(), but I'd like to print out
    # every single directory created.
    needs_creating = []
    while not path.exists():
        if path in needs_creating:
            break
        needs_creating.append(path)
        path = path.dir

    for path in reversed(needs_creating):
        cmd.w.action('mkdir', path)
        os.mkdir(path)


def write_file(cmd, filename, content, update=True, action=None,
               ignore_exists=False):
    """Helper that writes a file, while sending the proper actions
    to the command's writer for stdout display of what's going on.

    ``content`` may be a callable. This is useful if you would like
    to exploit the ``update=False`` check this function provides,
    rather than doing that yourself before bothering to generate the
    content you want to write.

    When ``update`` is not set, then if the file already exists we don't
    change or overwrite it.

    If a Writer.Action is given in ``action``, it will be used to print
    out messages. Otherwise, a new action will be started using the
    filename as the text. If ``action`` is ``False``, nothing will be
    printed.
    """
    if action is None:
        action = cmd.w.begin(filename)

    if filename.exists():
        if not update:
            if ignore_exists:
                # Downgade level of this message
                action.update(severity='info')
            action.done('exists')
            return False
        else:
            old_hash = filename.hash()
    else:
        old_hash = None

    ensure_directories(cmd, filename.dir)

    f = open(filename, 'wb')
    try:
        if callable(content):
            content = content()
        f.write(content)
        f.flush()
    finally:
        f.close()

    if not action is False:
        if old_hash is None:
            action.done('created')
        elif old_hash != filename.hash():
            action.done('updated')
        else:
            # Note that this is merely for user information. We
            # nevertheless wrote a new version of the file, we can't
            # actually determine a change without generating the new
            # version.
            action.done('unchanged')
    return True


class Command(object):
    """Abstract base command class.
    """

    def __init__(self, env, writer):
        self.env = env
        self.w = writer

    @classmethod
    def setup_arg_parser(cls, argparser):
        """A command should register it's sub-arguments here with the
        given argparser instance.
        """

    def execute(self):
        raise NotImplementedError()


class InitCommand(Command):
    """The init command; to initialize new languages.
    """

    @classmethod
    def setup_arg_parser(cls, parser):
        parser.add_argument('language', nargs='*',
                            help='Language code to initialize. If none given, all '+
                            'languages lacking a .po file will be initialized.')

    def make_or_get_template(self, kind, read_action=None, do_write=False,
                             update=True):
        """Return the .pot template file (as a Catalog) for the given kind.

        If ``do_write`` is given, the template file will be saved in the
        proper location. If ``update`` is ``False``, then an existing file
        will not be overridden, however.

        If ``do_write`` is disabled, then you need to given ``read_action``,
        the action which needs the template. This is so we can fail the
        proper action if generating the template goes wrong.

        Once generated, the template will be cached as a class member,
        and on subsequent access the cached version is returned.
        """
        # Implement caching - only generate the catalog the first time
        # this function is called.
        if not hasattr(self, '_template_catalogs'):
            self._template_catalogs = {}

        if kind in self._template_catalogs:
            return self._template_catalogs[kind], False

        # Only one, xor the other.
        assert read_action or do_write and not (read_action and do_write)

        template_pot = self.env.default.po(kind)
        if do_write:
            action = self.w.begin(template_pot)
        else:
            action = read_action

        # Read the XML, bail out if that fails
        xmldata = read_xml(action, self.env.default.xml(kind))
        if xmldata is False:
            return False, False

        # Actually generate the catalog
        template_catalog = xml2po(self.env, action, xmldata)
        self._template_catalogs[kind] = template_catalog

        # Write the catalog as a template to disk if necessary.
        something_written = False
        if do_write:
            # Note that this is always rendered with "ignore_exists",
            # i.e. we only log this action if we change the template.
            if write_file(self, template_pot,
                          content=lambda: catalog2string(template_catalog),
                          action=action, ignore_exists=True, update=update):
                something_written = True

        return template_catalog, something_written

    def generate_templates(self, update=True):
        """Generate the template files.

        Do this only if they are not disabled.
        """
        something_written = False
        if not self.env.config.no_template:
            for kind in self.env.xmlfiles:
                _, write_happend = self.make_or_get_template(
                    kind, do_write=True, update=update)
                if write_happend:
                    something_written = True
        return something_written

    def generate_po(self, target_po_file, default_data, action,
                    language_data=None, language_data_files=None,
                    update=True, ignore_exists=False):
        """Helper to generate a .po file.

        ``default_data`` is the collective data from the language neutral XML
        files, and this is what the .po we generate will be based on.

        ``language_data`` is collective data from the corresponding
        language-specific XML files, in case such data is available.

        ``language_data_files`` is the list of files that ``language_data``
        is based upon. This is because in some cases multiple XML files
        might need to be combined into one gettext catalog.

        If ``update`` is not set than we will bail out early
        if the file doesn't exist.
        """
        # This is a function so that it only will be run if write_file()
        # actually needs it.
        def make_catalog():
            if language_data is not None:
                action.message('Using existing translations from %s' % ", ".join(
                    [l.rel for l in language_data_files]))
                lang_catalog, unmatched = xml2po(self.env, action,
                                                 default_data,
                                                 language_data)
                if unmatched:
                    action.message("Existing translation XML files for this "
                                   "language contains strings not found in the "
                                   "default XML files: %s" % (", ".join(unmatched)))
            else:
                action.message('No corresponding XML exists, generating catalog '+
                               'without translations')
                lang_catalog = xml2po(self.env, action, default_data)

            catalog = catalog2string(lang_catalog)

            num_total, num_translated, _ = get_catalog_counts(lang_catalog)
            action.message("%d strings processed, %d translated." % (
                num_total, num_translated))
            return catalog

        return write_file(self, target_po_file, content=make_catalog,
                          action=action, update=update,
                          ignore_exists=ignore_exists)

    def _iterate(self, language, require_translation=True):
        """Yield 5-tuples in the form of: (
            action object,
            target .po file,
            source xml data,
            translated xml data,
            list of files translated xml data was read from
        )

        This is implemeted as a separate iterator so that later on we can
        also support a mechanism in which multiple xml files are stored in
        one .po file, i.e. on export, multiple xml files needs to be able
        to yield into a single .po target.
        """
        for kind in self.env.xmlfiles:
            language_po = language.po(kind)
            language_xml = language.xml(kind)

            action = self.w.begin(language_po)

            language_data = None
            if not language_xml.exists():
                if require_translation:
                    # It's easily possible that say a arrays.xml only
                    # exists in values/, but not in values-xx/.
                    action.done('skipped')
                    action.message('%s doesn\'t exist' % language_po.rel,
                                   'warning')
                    continue
            else:
                language_data = read_xml(action, language_xml, language=language)
                if language_data == False:
                    # File was invalid
                    continue

            template_data = read_xml(action, self.env.default.xml(kind))
            if template_data is False:
                # File was invalid
                continue

            yield action, language_po, template_data, language_data, [language_xml]

    def yield_languages(self, env, source='android'):
        if env.options.language:
            for code in env.options.language:
                if code == '-':
                    # This allows specifying - to only build the template
                    continue
                language = resolve_locale(code, env)
                if language:
                    yield language

        else:
            for l in list_languages(source, env, self.w):
                yield l

    def execute(self):
        env = self.env

        # First, make sure the templates exist. This makes the "init"
        # command everything needed to bootstrap.
        # TODO: Test that this happens.
        something_done = self.generate_templates(update=False)

        # Only show [exists] actions if a specific language was requested.
        show_exists = not bool(env.options.language)

        for language in self.yield_languages(env):
            # For each language, generate a .po file. In case a language
            # already exists (that is, it's xml files exist, use the
            # existing translations for the new gettext catalog).
            for (action,
                 target_po,
                 template_data,
                 lang_data,
                 lang_files) in self._iterate(language, require_translation=False):
                if self.generate_po(target_po, template_data, action,
                                    lang_data, lang_files,
                                    update=False,
                                    ignore_exists=show_exists):
                    something_done = True

            # Also for each language, generate the empty .xml resource files.
            # This will make us pick up the language on subsequent runs.
            for kind in self.env.xmlfiles:
                if write_file(self, language.xml(kind),
                              """<?xml version='1.0' encoding='utf-8'?>\n<resources>\n</resources>""",
                              update=False, ignore_exists=show_exists):
                    something_done = True

        if not something_done:
            self.w.action('info', 'Nothing to do.', 'default')


class ExportCommand(InitCommand):
    """The export command.

    Inherits from ``InitCommand`` to be able to use ``generate_templates``.
    Both commands need to write the templates.
    """

    @classmethod
    def setup_arg_parser(cls, parser):
        parser.add_argument(
            'language', nargs='*',
            help='Language code to export. If not given, all '+
                 'initialized languages will be exported.')

    def execute(self):
        env = self.env
        w = self.w

        # First, always update the template files. Note that even if
        # template generation is disabled, we still need to have the
        # catalogs at least in memory for the updating process later on.
        #
        # TODO: Do we really want to regenerate the templates every
        # time, or should the user be able to set fixed meta data, and
        # we simply merge subsequent updates in?
        self.generate_templates()

        initial_warning = False

        for language in self.yield_languages(env, 'gettext'):
            for kind in self.env.xmlfiles:
                target_po = language.po(kind)
                if not target_po.exists():
                    w.action('skipped', target_po)
                    w.message('File does not exist yet. '+
                              'Use the \'init\' command.')
                    initial_warning = True
                    continue

                action = w.begin(target_po)
                # If we do not provide a locale, babel will consider this
                # catalog a template and always write out the default
                # header. It seemingly does not consider the "Language"
                # header inside the file at all, and indeed deletes it.
                # TODO: It deletes all headers it doesn't know, and
                # overrides others. That sucks.
                lang_catalog = read_catalog(target_po, locale=language.code)
                catalog, _ = self.make_or_get_template(kind, action)
                if catalog is None:
                    # Something went wrong parsing the catalog
                    continue
                lang_catalog.update(catalog)

                # Set the correct plural forms.
                current_plurals = lang_catalog.plural_forms
                convert.set_catalog_plural_forms(lang_catalog, language)
                if lang_catalog.plural_forms != current_plurals:
                    action.message(
                        'The Plural-Forms header of this catalog '
                        'has been updated to what android2po '
                        'requires for plurals support. See the '
                        'README for more information.', 'warning')

                # TODO: Should we include previous?
                write_file(self, target_po,
                           catalog2string(lang_catalog, include_previous=False),
                           action=action)

        if initial_warning:
            print ""
            print colored("Warning: One or more .po files were skipped "+\
                  "because they did not exist yet. Use the 'init' command "+\
                  "to generate them for the first time.",
                  fg='magenta', opts=('bold',))


class ImportCommand(Command):
    """The import command.
    """

    def process(self, language):
        """Process importing the given language.
        """

        # In order to implement the --require-min-complete option, we need
        # to first determine the translation status across all .po catalogs
        # for this language. We can keep the catalogs in memory because we
        # will need them later anyway.
        catalogs = {}
        count_total = 0
        count_translated = 0
        for kind in self.env.xmlfiles:
            language_po = language.po(kind)
            if not language_po.exists():
                continue
            catalogs[kind] = catalog = read_catalog(language_po)
            catalog.language = language
            ntotal, ntrans, nfuzzy = get_catalog_counts(catalog)
            count_total += ntotal
            count_translated += ntrans
            if self.env.config.ignore_fuzzy:
                count_translated -= nfuzzy

        # Compare our count with what is required, if anything.
        skip_due_to_incomplete = False
        min_required = self.env.config.min_completion
        if count_total == 0:
            actual_completeness = 1
        else:
            actual_completeness = count_translated / float(count_total)
        if min_required:
            skip_due_to_incomplete = actual_completeness < min_required

        # Now loop through the list of target files, and either create
        # them, or print a status message for each indicating that they
        # were skipped.
        for kind in self.env.xmlfiles:
            language_xml = language.xml(kind)
            action = self.w.begin(language_xml)

            if skip_due_to_incomplete:
                # TODO: Creating a catalog object here is kind of clunky.
                # Idially, we'd refactor convert.py so that we can use a
                # dict to represent a resource XML file.
                xmldata = po2xml(self.env, action, Catalog(locale=language.code))
                write_file(self, language_xml, xml2string(xmldata, action),
                           action=False)
                action.done('skipped', status=('%s catalogs aren\'t '
                                               'complete enough - %.2f done' % (
                                                   language.code,
                                                   actual_completeness)))
                continue

            if not language_po.exists():
                action.done('skipped')
                self.w.message('%s doesn\'t exist' % language_po.rel, 'warning')
                continue

            content = xml2string(po2xml(self.env, action, catalogs[kind]), action)
            write_file(self, language_xml, content, action=action)

    def execute(self):
        for language in list_languages('gettext', self.env, self.w):
            self.process(language)

########NEW FILE########
__FILENAME__ = compat
__all__ = ('OrderedDict',)

try:
    from collections import OrderedDict
except ImportError:
    # http://code.activestate.com/recipes/576693/
    from UserDict import DictMixin

    class OrderedDict(dict, DictMixin):

        def __init__(self, *args, **kwds):
            if len(args) > 1:
                raise TypeError('expected at most 1 arguments, got %d' % len(args))
            try:
                self.__end
            except AttributeError:
                self.clear()
            self.update(*args, **kwds)

        def clear(self):
            self.__end = end = []
            end += [None, end, end]         # sentinel node for doubly linked list
            self.__map = {}                 # key --> [key, prev, next]
            dict.clear(self)

        def __setitem__(self, key, value):
            if key not in self:
                end = self.__end
                curr = end[1]
                curr[2] = end[1] = self.__map[key] = [key, curr, end]
            dict.__setitem__(self, key, value)

        def __delitem__(self, key):
            dict.__delitem__(self, key)
            key, prev, next = self.__map.pop(key)
            prev[2] = next
            next[1] = prev

        def __iter__(self):
            end = self.__end
            curr = end[2]
            while curr is not end:
                yield curr[0]
                curr = curr[2]

        def __reversed__(self):
            end = self.__end
            curr = end[1]
            while curr is not end:
                yield curr[0]
                curr = curr[1]

        def popitem(self, last=True):
            if not self:
                raise KeyError('dictionary is empty')
            key = reversed(self).next() if last else iter(self).next()
            value = self.pop(key)
            return key, value

        def __reduce__(self):
            items = [[k, self[k]] for k in self]
            tmp = self.__map, self.__end
            del self.__map, self.__end
            inst_dict = vars(self).copy()
            self.__map, self.__end = tmp
            if inst_dict:
                return (self.__class__, (items,), inst_dict)
            return self.__class__, (items,)

        def keys(self):
            return list(self)

        setdefault = DictMixin.setdefault
        update = DictMixin.update
        pop = DictMixin.pop
        values = DictMixin.values
        items = DictMixin.items
        iterkeys = DictMixin.iterkeys
        itervalues = DictMixin.itervalues
        iteritems = DictMixin.iteritems

        def __repr__(self):
            if not self:
                return '%s()' % (self.__class__.__name__,)
            return '%s(%r)' % (self.__class__.__name__, self.items())

        def copy(self):
            return self.__class__(self)

        @classmethod
        def fromkeys(cls, iterable, value=None):
            d = cls()
            for key in iterable:
                d[key] = value
            return d

        def __eq__(self, other):
            if isinstance(other, OrderedDict):
                return len(self)==len(other) and \
                       all(p==q for p, q in  zip(self.items(), other.items()))
            return dict.__eq__(self, other)

        def __ne__(self, other):
            return not self == other
########NEW FILE########
__FILENAME__ = config
from os import path
import argparse


__all__ = ('Config',)


def percentage(string):
    errstr = "must be a float between 0 and 1, not %r" % string
    try:
        value = float(string)
    except ValueError:
        raise argparse.ArgumentTypeError(errstr)
    if value < 0 or value > 1:
        raise argparse.ArgumentTypeError(errstr)
    return value


class Config(object):
    """Defines all the options supported by our configuration system.
    """
    OPTIONS = (
        {'name': 'android',
         'help': 'Android resource directory ($PROJECT/res by default)',
         'dest': 'resource_dir',
         'kwargs': {'metavar': 'DIR',}
         # No default, and will not actually be stored on the config object.
        },
        {'name': 'gettext',
         'help': 'directory containing the .po files ($PROJECT/locale by default)',
         'dest': 'gettext_dir',
         'kwargs': {'metavar': 'DIR',}
         # No default, and will not actually be stored on the config object.
        },
        {'name': 'groups',
         'help': 'process the given default XML files (for example '+
                 '"strings arrays"); by default all files which contain '+
                 'string resources will be used',
         'dest': 'groups',
         'default': [],
         'kwargs': {'nargs': '+', 'metavar': 'GROUP'}
        },
        {'name': 'no-template',
         'help': 'do not generate a .pot template file on export',
         'dest': 'no_template',
         'default': False,
         'kwargs': {'action': 'store_true',}
        },
        {'name': 'template',
         'help': 'filename to use for the .pot file(s); may contain the '+
                 '%%(domain)s and %%(group)s variables',
         'dest': 'template_name',
         'default': '',
         'kwargs': {'metavar': 'NAME',}
        },
        {'name': 'ignore',
         'help': 'ignore the given message; can be given multiple times; '+
                 'regular expressions can be used if putting the value '+
                 'inside slashes (/match/)',
         'dest': 'ignores',
         'default': [],
         'kwargs': {'metavar': 'MATCH', 'action': 'append', 'nargs': '+'}
        },
        {'name': 'ignore-fuzzy',
         'help': 'during import, ignore messages marked as fuzzy in .po files',
         'dest': 'ignore_fuzzy',
         'default': False,
         'kwargs': {'action': 'store_true',}
        },
        {'name': 'require-min-complete',
         'help': 'ignore a language\'s .po file(s) completely if there '+
                 'aren\'t at least the given percentage of translations',
         'dest': 'min_completion',
         'default': 0,
         'kwargs': {'metavar': 'FLOAT', 'type': percentage}
        },
        {'name': 'domain',
         'help': 'gettext po domain to use, affects the .po filenames',
         'dest': 'domain',
         'default': None,
        },
        {'name': 'layout',
         'help': 'how and where .po files are stored; may be "default", '+
                  '"gnu", or a custom path using the variables %%(locale)s '+
                  '%%(domain)s and optionally %%(group)s. E.g., '+
                  '"%%(group)s-%%(locale)s.po" will write to "strings-es.po" '+
                  'for Spanish in strings.xml.',
         'dest': 'layout',
         'default': 'default',
        },
    )

    def __init__(self):
        """Initialize all configuration values with a default.

        It is important that we do this here manually, rather than relying
        on the "default" mechanism of argparse, because we have multiple
        potential congiguration sources (command line, config file), and
        we don't want defaults to override actual values.

        The attributes we define here are also used to determine
        which command line options passed should be assigned to this
        object, and which should be exposed via a separate ``options``
        namespace.
        """
        for optdef in self.OPTIONS:
            if 'default' in optdef:
                setattr(self, optdef['dest'], optdef['default'])

    @classmethod
    def setup_arguments(cls, parser):
        """Setup our configuration values as arguments in the ``argparse``
        object in ``parser``.
        """
        for optdef in cls.OPTIONS:
            names = ('--%s' % optdef.get('name'),)
            kwargs = {
                'help': optdef.get('help', None),
                'dest': optdef.get('dest', None),
                # We handle defaults ourselves. This is actually important,
                # or defaults from one config source may override valid
                # values from another.
                'default': argparse.SUPPRESS,
            }
            kwargs.update(optdef.get('kwargs', {}))
            parser.add_argument(*names, **kwargs)

    @classmethod
    def rebase_paths(cls, config, base_path):
        """Make those config values that are paths relative to
        ``base_path``, because by default, paths are relative to
        the current working directory.
        """
        for name in ('gettext_dir', 'resource_dir'):
            value = getattr(config, name, None)
            if value is not None:
                setattr(config, name, path.normpath(path.join(base_path, value)))

########NEW FILE########
__FILENAME__ = convert
"""This module does the hard work of converting.

It uses a simply dict-based memory representation of Android XML string
resource files, via the ``ResourceTree`` class. The .po files are
represented in memory via Babel's ``Catalog`` class.

The process thus is:

    read_xml() -> ResourceTree -> xml2po() -> Catalog -> po2xml
    -> ResourceTree -> write_xml()

"""

from itertools import chain
from collections import namedtuple
from compat import OrderedDict
from lxml import etree
from babel.messages import Catalog
from babel.plural import _plural_tags as PLURAL_TAGS


__all__ = ('xml2po', 'po2xml', 'read_xml', 'write_xml',
           'set_catalog_plural_forms', 'InvalidResourceError',)


class InvalidResourceError(Exception):
    pass


class UnsupportedResourceError(Exception):
    """A resource in a XML file can't be processed.
    """
    def __init__(self, reason):
        self.reason = reason


WHITESPACE = ' \n\t'     # Whitespace that we collapse
EOF = None


# Some AOSP projects like to include xliff:* tags to annotate
# strings with more information for translators. This is actually harder
# to support than it might look like: We want the translators to see at
# least a tag called "xliff", not the namespace URIs, but we currently
# don't have a way to define namespaces in the .po files (comments?),
# so in order to properly generate an XML on import, we can only deal
# with a fixed list of namespace that we now about.
KNOWN_NAMESPACES = {
    'urn:oasis:names:tc:xliff:document:1.2': 'xliff',
}


# The methods here sometimes need to notify the caller about warnings
# processing on; this is why they all take a ``warn_func`` argument.
# By default, if no warnfunc is passed, this dummy will be used.
dummy_warn = lambda message, severity=None: None


# These classes are used for the memory representation of an Android
# string resource file. ``ResourceTree`` holds ``StringArray``,
# ``Plurals`` and ``Translation`` objects, and ``StringArray`` and
# ``Plurals`` can also hold ``Translation`` objects.
class ResourceTree(OrderedDict):
    language = None
    def __init__(self, language=None):
        OrderedDict.__init__(self)
        self.language = language
class StringArray(list): pass
class Plurals(dict): pass
Translation = namedtuple('Translation', ['text', 'comments', 'formatted'])


def get_element_text(tag, name, warnfunc=dummy_warn):
    """Return a tuple of the contents of the lxml ``element`` with the
    Android specific stuff decoded and whether the text includes
    formatting codes.

    "Contents" isn't just the text; it handles nested HTML tags as well.
    """

    def convert_text(text):
        """This is called for every distinct block of text, as they
        are separated by tags.

        It handles most of the Android syntax rules: quoting, escaping,
        collapsing duplicate whitespace etc.
        """
        # '<' and '>' as literal characters inside a text need to be
        # escaped; this is because we need to differentiate them to
        # actual tags inside a resource string which we write to the
        # .po file as literal '<', '>' characters. As a result, if the
        # user puts &lt; inside his Android resource file, this is how
        # it will end up in the .po file as well.
        # We only do this for '<' and '<' right now, which is of course
        # a hack. We'd need to process at least &amp; as well, because
        # right now '&lt;' and '&amp;lt;' both generate the same on
        # import. However, if we were to do that, a simple non-HTML
        # text like "FAQ & Help" would end up us "FAQ &amp; Help" in
        # the .po - not particularly nice.
        # TODO: I can see two approaches to solve this: Handle things
        # differently depending on whether there are nested tags. We'd
        # be able to handle both '&amp;lt;' in a HTML string and output
        # a nice & character in a plaintext string.
        # Option 2: It might be possible to note the type of encoding
        # we did in a .po comment. That would even allow us to present
        # a string containing tags encoded using entities (but not actual
        # nested XML tags) using plain < and > characters in the .po
        # file. Instead of a comment, we could change the import code
        # to require a look at the original resource xml file to
        # determine which kind of encoding was done.
        text = text.replace('<', '&lt;')
        text = text.replace('>', "&gt;")

        # We need to collapse multiple whitespace while paying
        # attention to Android's quoting and escaping.
        space_count = 0
        active_quote = False
        active_percent = False
        active_escape = False
        formatted = False
        i = 0
        text = list(text) + [EOF]
        while i < len(text):
            c = text[i]

            # Handle whitespace collapsing
            if c is not EOF and c in WHITESPACE:
                space_count += 1
            elif space_count > 1:
                # Remove duplicate whitespace; Pay attention: We
                # don't do this if we are currently inside a quote,
                # except for one special case: If we have unbalanced
                # quotes, e.g. we reach eof while a quote is still
                # open, we *do* collapse that trailing part; this is
                # how Android does it, for some reason.
                if not active_quote or c is EOF:
                    # Replace by a single space, will get rid of
                    # non-significant newlines/tabs etc.
                    text[i-space_count : i] = ' '
                    i -= space_count - 1
                space_count = 0
            elif space_count == 1:
                # At this point we have a single whitespace character,
                # but it might be a newline or tab. If we write this
                # kind of insignificant whitespace into the .po file,
                # it will be considered significant on import. So,
                # make sure that this kind of whitespace is always a
                # standard space.
                text[i-1] = ' '
                space_count = 0
            else:
                space_count = 0

            # Handle quotes
            if c == '"' and not active_escape:
                active_quote = not active_quote
                del text[i]
                i -= 1

            # If the string is run through a formatter, it will have
            # percentage signs for String.format
            if c == '%' and not active_escape:
                active_percent = not active_percent
            elif not active_escape and active_percent:
                formatted = True
                active_percent = False

            # Handle escapes
            if c == '\\':
                if not active_escape:
                    active_escape = True
                else:
                    # A double-backslash represents a single;
                    # simply deleting the current char will do.
                    del text[i]
                    i -= 1
                    active_escape = False
            else:
                if active_escape:
                    # Handle the limited amount of escape codes
                    # that we support.
                    # TODO: What about \r, or \r\n?
                    if c is EOF:
                        # Basically like any other char, but put
                        # this first so we can use the ``in`` operator
                        # in the clauses below without issue.
                        pass
                    elif c == 'n':
                        text[i-1 : i+1] = '\n'  # an actual newline
                        i -= 1
                    elif c == 't':
                        text[i-1 : i+1] = '\t'  # an actual tab
                        i -= 1
                    elif c in '"\'@':
                        text[i-1 : i] = ''        # remove the backslash
                        i -= 1
                    elif c == 'u':
                        # Unicode sequence. Android is nice enough to deal
                        # with those in a way which let's us just capture
                        # the next 4 characters and raise an error if they
                        # are not valid (rather than having to use a new
                        # state to parse the unicode sequence).
                        # Exception: In case we are at the end of the
                        # string, we support incomplete sequences by
                        # prefixing the missing digits with zeros.
                        # Note: max(len()) is needed in the slice due to
                        # trailing ``None`` element.
                        max_slice = min(i+5, len(text)-1)
                        codepoint_str = "".join(text[i+1 : max_slice])
                        if len(codepoint_str) < 4:
                            codepoint_str = u"0" * (4-len(codepoint_str)) + codepoint_str
                        print repr(codepoint_str)
                        try:
                            # We can't trust int() to raise a ValueError,
                            # it will ignore leading/trailing whitespace.
                            if not codepoint_str.isalnum():
                                raise ValueError(codepoint_str)
                            codepoint = unichr(int(codepoint_str, 16))
                        except ValueError:
                            raise UnsupportedResourceError('bad unicode escape sequence')

                        text[i-1 : max_slice] = codepoint
                        i -= 1
                    else:
                        # All others, remove, like Android does as well.
                        # However, Android does so silently, we show a
                        # warning so the dev can fix the problem.
                        warnfunc(('Resource "%s": removing unsupported '
                                  'escape sequence "%s"') % (
                                    name, "".join(text[i-1 : i+1])), 'warning')
                        text[i-1 : i+1] = ''
                        i -= 1
                    active_escape = False

            i += 1

        # Join the string together again, but w/o EOF marker
        return "".join(text[:-1]), formatted

    def get_tag_name(elem):
        """For tags without a namespace, returns ("tag", None).
        For tags with a known-namespace, returns ("prefix:tag", None).
        For tags with an unknown-namespace, returns ("tag", ("prefix", "ns"))
        """
        if elem.prefix:
            namespace = elem.nsmap[elem.prefix]
            raw_name = elem.tag[elem.tag.index('}')+1:]
            if namespace in KNOWN_NAMESPACES:
                return "%s:%s" % (KNOWN_NAMESPACES[namespace], raw_name), None
            return "%s:%s" % (elem.prefix, raw_name), (elem.prefix, namespace)
        return elem.tag, None

    # We need to recreate the contents of this tag; this is more
    # complicated than you might expect; firstly, there is nothing
    # built into lxml (or any other parser I have seen for that
    # matter). While it is possible to use ``etree.tostring``
    # to render this tag and it's children, this still would give
    # us valid XML code; when in fact we want to decode everything
    # XML (including entities), *except* tags. Much more than that
    # though, the processing rules the Android xml format needs
    # require custom processing anyway.
    value = u""
    formatted = False
    for ev, elem  in etree.iterwalk(tag, events=('start', 'end',)):
        is_root = elem == tag
        has_children = len(tag) > 0
        if ev == 'start':
            if not is_root:
                # Take care of the tag name, namespace and attributes.
                # Since we can't store namespace urls in a .po file, dealing
                # with (unknown) namespaces requires generating a xmlns
                # attribute.
                # TODO: We are currently not dealing correctly with
                # attribute values that need escaping.
                tag_name, to_declare = get_tag_name(elem)
                params = ["%s=\"%s\"" % (k, v) for k, v in elem.attrib.items()]
                if to_declare:
                    name, url = to_declare
                    params.append('xmlns:%s="%s"' % (name, url))
                params_str = " %s" % " ".join(params) if params else ""
                value += u"<%s%s>" % (tag_name, params_str)
            if elem.text is not None:
                t = elem.text
                # Leading/Trailing whitespace is removed completely
                # ONLY if there are no nested tags. Handle this before
                # calling ``convert_text``, so that whitespace
                # protecting quotes can still be considered.
                if is_root and not has_children and len(tag) == 0:
                    t = t.strip(WHITESPACE)

                # Resources that start with @ reference other resources.
                # While we aren't particularily interested in converting
                # those, we also can't do it right now because we wouldn't
                # be able to differ between literal @ characters and the
                # reference syntax during import.
                #
                # While it may seem a bit early to deal with this here, we
                # have no choice, because the caller needs *some* way of
                # differentating between an escaped literal '@' and this
                # kind of resource-reference. Since we unescape literals,
                # we need to do something with the reference-@.
                if is_root and not has_children and t and t[0] == '@':
                    raise UnsupportedResourceError(
                        'resource references (%s) are not supported' % t)

                converted_value, elem_formatted = convert_text(t)
                if elem_formatted:
                    formatted = True
                value += converted_value
        elif ev == 'end':
            # The closing root tag has no info for us at all.
            if not is_root:
                tag_name, _ = get_tag_name(elem)
                value += u"</%s>" % tag_name
                if elem.tail is not None:
                    converted_value, elem_formatted = convert_text(elem.tail)
                    if elem_formatted:
                        formatted = True
                    value += converted_value

    # Babel can't handle empty msgids, even when using a unique context;
    # not sure if this is a general gettext limitation, but it's not
    # unlikely that other tools would have problems, so it's for the better
    # in any case.
    if value == u'':
        raise UnsupportedResourceError('empty resources not supported')
    return value, formatted


def read_xml(file, language=None, warnfunc=dummy_warn):
    """Load all resource names from an Android strings.xml resource file.

    The result is a ``ResourceTree`` instance.
    """
    result = ResourceTree(language)
    comment = []

    try:
        doc = etree.parse(file)
    except etree.XMLSyntaxError, e:
        raise InvalidResourceError(e)

    for tag in doc.getroot():
        # Collect comments so we can add them to the element that they precede.
        if tag.tag == etree.Comment:
            comment.append(tag.text)
            continue

        # Ignore elements we cannot or should not process
        if not 'name' in tag.attrib:
            comment = []
            continue
        if tag.attrib.get('translatable') == 'false':
            comment = []
            continue

        name = tag.attrib['name']
        if name in result:
            warnfunc('Duplicate resource id found: %s, ignoring.' % name,
                     'warning')
            comment = []
            continue

        if tag.tag == 'string':
            try:
                text, formatted = get_element_text(tag, name, warnfunc)
            except UnsupportedResourceError, e:
                warnfunc('"%s" has been skipped, reason: %s' % (
                    name, e.reason), 'info')
            else:
                translation = Translation(text, comment, formatted)
                result[name] = translation

        elif tag.tag == 'string-array':
            result[name] = StringArray()
            for child in tag.findall('item'):
                try:
                    text, formatted = get_element_text(child, name, warnfunc)
                except UnsupportedResourceError, e:
                    # XXX: We currently can't handle this, because even if
                    # we write out a .po file with the proper array
                    # indices, and items like this one missing, during
                    # import we still need to write out those items that
                    # we have now skipped, since the Android format is only
                    # a simple list of items, i.e. we need to specify the
                    # fully array, and can't override individual items on
                    # a per-translation basis.
                    #
                    # To fix this, we have two options: Either we support
                    # annotating gettext messages, in which case we could
                    # indicate whether or not a message like this was a
                    # reference and should be escaped or not. Or, better,
                    # the import process would need to use information from
                    # the default strings.xml file to fill the vacancies.
                    warnfunc(('Warning: The array "%s" contains items '+
                              'that can\'t be processed (reason: %s) - '
                              'the array will be incomplete') %
                                    (name, e.reason), 'warning')
                else:
                    translation = Translation(text, comment, formatted)
                    result[name].append(translation)

        elif tag.tag == 'plurals':
            result[name] = Plurals()
            for child in tag.findall('item'):
                try:
                    quantity = child.attrib['quantity']
                    assert quantity in PLURAL_TAGS
                except (IndexError, AssertionError):
                    warnfunc(('"%s" contains a plural with no or '+
                              'an invalid quantity') % name, 'warning')
                else:
                    try:
                        text, formatted = get_element_text(child, name, warnfunc)
                    except UnsupportedResourceError, e:
                        warnfunc(('Warning: The plural "%s" can\'t '+
                                  'be processed (reason: %s) - '
                                  'the plural will be incomplete') %
                                 (name, e.reason), 'warning')
                    else:
                        translation = Translation(text, comment, formatted)
                        result[name][quantity] = translation

        # We now have processed a tag. We either added those comments to
        # the translation we created based on the tag, or the comments
        # relate to a tag we do not support. In any case, dismiss them.
        comment = []

    return result


def plural_to_gettext(rule):
    """This is a copy of the code of ``babel.plural.to_gettext``.

    We need to use a custom version, because the original only returns
    a full plural_forms string, which the Babel catalog object does not
    allow us to assign to anything. Instead, we need the expr and the
    plural count separately. See http://babel.edgewall.org/ticket/291.
    """
    from babel.plural import (PluralRule, _fallback_tag, _plural_tags,
                              _GettextCompiler)
    rule = PluralRule.parse(rule)

    used_tags = rule.tags | set([_fallback_tag])
    _compile = _GettextCompiler().compile
    _get_index = [tag for tag in _plural_tags if tag in used_tags].index

    expr = ['(']
    for tag, ast in rule.abstract:
        expr.append('%s ? %d : ' % (_compile(ast), _get_index(tag)))
    expr.append('%d)' % _get_index(_fallback_tag))
    return len(used_tags), ''.join(expr)


def set_catalog_plural_forms(catalog, language):
    """Set the catalog to use the correct plural forms for the
    language.
    """
    try:
        catalog._num_plurals, catalog._plural_expr = plural_to_gettext(
            language.locale.plural_form)
    except KeyError:
        # Babel/CDLR seems to be lacking this data sometimes, for
        # example for "uk"; fortunately, ignoring this is narrowly
        # acceptable.
        pass


def xml2po(resources, translations=None, filter=None, warnfunc=dummy_warn):
    """Return ``resources`` as a Babel .po ``Catalog`` instance.

    If given, ``translations`` will be used for the translated values.
    In this case, the returned value is a 2-tuple (catalog, unmatched),
    with the latter being a list of Android string resource names that
    are in the translated file, but not in the original.

    Both ``resources`` and ``translations`` must be ``ResourceTree``
    objects, as returned by ``read_xml()``.

    From the application perspective, it will call this function with
    a ``translations`` object when initializing a new .po file based on
    an existing resource file (the 'init' command). For 'export', this
    function is called without translations. It will thus generate what
    is essentially a POT file (an empty .po file), and this will be
    merged into the existing .po catalogs, as per how gettext usually
    """
    assert not translations or translations.language

    catalog = Catalog()
    if translations is not None:
        catalog.locale = translations.language.locale
        # We cannot let Babel determine the plural expr for the locale by
        # itself. It will use a custom list of plural expressions rather
        # than generate them based on CLDR.
        # See http://babel.edgewall.org/ticket/290.
        set_catalog_plural_forms(catalog, translations.language)

    for name, org_value in resources.iteritems():
        if filter and filter(name):
            continue

        trans_value = None
        if translations:
            trans_value = translations.pop(name, trans_value)

        if isinstance(org_value, StringArray):
            # a string-array, write as "name:index"
            if len(org_value) == 0:
                warnfunc("Warning: string-array '%s' is empty" % name, 'warning')
                continue

            if not isinstance(trans_value, StringArray):
                if trans_value:
                    warnfunc(('""%s" is a string-array in the reference '
                              'file, but not in the translation.') %
                                    name, 'warning')
                trans_value = StringArray()

            for index, item in enumerate(org_value):
                item_trans = trans_value[index].text if index < len(trans_value) else u''

                # If the string has formatting markers, indicate it in
                # the gettext output
                flags = []
                if item.formatted:
                    flags.append('c-format')

                ctx = "%s:%d" % (name, index)
                catalog.add(item.text, item_trans, auto_comments=item.comments,
                            flags=flags, context=ctx)

        elif isinstance(org_value, Plurals):
            # a plurals, convert to a gettext plurals
            if len(org_value) == 0:
                warnfunc("Warning: plurals '%s' is empty" % name, 'warning')
                continue

            if not isinstance(trans_value, Plurals):
                if trans_value:
                    warnfunc(('""%s" is a plurals in the reference '
                              'file, but not in the translation.') %
                                    name, 'warning')
                trans_value = Plurals()

            # Taking the Translation objects for each quantity in ``org_value``,
            # we build a list of strings, which is how plurals are represented
            # in Babel.
            #
            # Since gettext only allows comments/flags on the whole
            # thing at once, we merge the comments/flags of all individual
            # plural strings into one.
            formatted = False
            comments = []
            for _, translation in org_value.items():
                if translation.formatted:
                    formatted = True
                comments.extend(translation.comments)

            # For the message id, choose any two plural forms, but prefer
            # "one" and "other", assuming an English master resource.
            temp = org_value.copy()
            singular =\
                temp.pop('one') if 'one' in temp else\
                temp.pop('other') if 'other' in temp else\
                temp.pop(temp.keys()[0])
            plural =\
                temp.pop('other') if 'other' in temp else\
                temp[temp.keys()[0]] if temp else\
                singular
            msgid = (singular.text, plural.text)
            del temp, singular, plural

            # We pick the quantities supported by the language (the rest
            # would be ignored by Android as well).
            msgstr = ''
            if trans_value:
                allowed_keywords = translations.language.plural_keywords
                msgstr = ['' for i in range(len(allowed_keywords))]
                for quantity, translation in trans_value.items():
                    try:
                        index = translations.language.plural_keywords.index(quantity)
                    except ValueError:
                        warnfunc(
                            ('"plurals "%s" uses quantity "%s", which '
                             'is not supported for this language. See '
                             'the README for an explanation. The '
                             'quantity has been ignored') %
                                    (name, quantity), 'warning')
                    else:
                        msgstr[index] = translation.text

            flags = []
            if formatted:
                flags.append('c-format')
            catalog.add(msgid, tuple(msgstr), flags=flags,
                        auto_comments=comments, context=name)

        else:
            # a normal string

            # If the string has formatting markers, indicate it in
            # the gettext output
            # TODO DRY this.
            flags = []
            if org_value.formatted:
                flags.append('c-format')

            catalog.add(org_value.text, trans_value.text if trans_value else u'',
                        flags=flags, auto_comments=org_value.comments, context=name)

    if translations is not None:
        # At this point, trans_strings only contains those for which
        # no original existed.
        return catalog, translations.keys()
    else:
        return catalog


def write_to_dom(elem_name, value, ref, namespaces=None, warnfunc=dummy_warn):
    """Create a DOM object with the tag name ``elem_name``, containing
    the string ``value`` formatted according to Android XML rules.

    The result might be a <string>-tag, or a <item>-tag as found as
    children of <string-array>, for example.

    It might feel awkward at first that the Android-XML formatting
    does not happen in a separate method, but is part of the creation
    of a tag, but due to us having to do certain formatting based on
    child DOM elements that ``value`` may include, the two fit
    naturally together (see the POSTPROCESS section of this function).

    If one of our supported namespace prefixes is used within nested tags
    inside ``value``, the appropriate data is added to the
    ``namespaces`` dict, if given, so the caller may generate the
    proper declarations.
    """

    loose_parser = etree.XMLParser(recover=True)

    if value is None:
        value = ''

    # PREPROCESS
    # The translations may contain arbitrary XHTML, which we need
    # to inject into the DOM to properly output. That means parsing
    # it first.
    # This will now get really messy, since certain XML entities
    # we have unescaped for the translators convenience, while the
    # tag entities &lt; and &gt; we have not, to differentiate them
    # from actual nested tags. Is there any good way to restore this
    # properly?
    # TODO: In particular, the code below will once we do anything
    # bit more complicated with entities, like &amp;amp;lt;
    value = value.replace('&', '&amp;')
    value = value.replace('&amp;lt;', '&lt;')
    value = value.replace('&amp;gt;', '&gt;')

    # PARSE
    #
    # Namespace handling complicates things a bit. We want the value
    # we inject to support nested XML with certain supported namespace
    # prefixes, but lxml doesn't seem to allow us to predefine those
    # (https://answers.launchpad.net/lxml/+question/111660).
    # So we use a wrapping element with xmlns attributes that we ignore
    # after parsing.
    namespace_text = " ".join(['xmlns:%s="%s"' % (prefix, ns) for ns, prefix in KNOWN_NAMESPACES.items()])
    value_to_parse = "<root %s><%s>%s</%s></root>" % (namespace_text, elem_name, value, elem_name)
    try:
        elem = etree.fromstring(value_to_parse)
    except etree.XMLSyntaxError, e:
        elem = etree.fromstring(value_to_parse, loose_parser)
        warnfunc(('%s contains invalid XHTML (%s); Falling back to '
                  'loose parser.') % (ref, e), 'warning')

    # Within the generated DOM, search for use of one of our supported
    # namespace prefixes, so we can keep track of which namespaces have
    # been used.
    if namespaces is not None:
        for c in elem.iterdescendants():
            if c.prefix:
                nsuri = c.nsmap[c.prefix]
                if nsuri in KNOWN_NAMESPACES:
                    namespaces[KNOWN_NAMESPACES[nsuri]] = nsuri
    # Then, proceed with the actual element that we wanted to create.
    elem = elem[0]

    def quote(text):
        """Return ``text`` surrounded by quotes if necessary.
        """
        if text is None:
            return

        # If there is trailing or leading whitespace, even if it's
        # just a single space character, we need quoting.
        needs_quoting = text.strip(WHITESPACE) != text

        # Otherwise, there might be collapsible spaces inside the text.
        if not needs_quoting:
            space_count = 0
            for c in chain(text, [EOF]):
                if c is not EOF and c in WHITESPACE:
                    space_count += 1
                    if space_count >= 2:
                        needs_quoting = True
                        break
                else:
                    space_count = 0

        if needs_quoting:
            return '"%s"' % text
        return text

    def escape(text):
        """Escape all the characters we know need to be escaped
        in an Android XML file."""
        if text is None:
            return
        text = text.replace('\\', '\\\\')
        text = text.replace('\n', '\\n')
        text = text.replace('\t', '\\t')
        text = text.replace('\'', '\\\'')
        text = text.replace('"', '\\"')
        # Strictly speaking, @ only needs to be escaped when
        # it's the first character. But, since our target XML
        # files are basically generate-only and unlikely to be
        # edited by a user, don't bother with pretty.
        text = text.replace('@', '\\@')
        return text

    # POSTPROCESS
    for child_elem in elem.iter():
        # Strictly speaking, we wouldn't want to touch things
        # like the root elements tail, but it doesn't matter here,
        # since they are going to be empty string anyway.
        child_elem.text = quote(escape(child_elem.text))
        child_elem.tail = quote(escape(child_elem.tail))

    return elem

def sort_plural_keywords(x, y):
    """Comparator that sorts CLDR  plural keywords starting with 'zero'
    and ending with 'other'."""
    return cmp(PLURAL_TAGS.index(x) if x in PLURAL_TAGS else -1,
               PLURAL_TAGS.index(y) if y in PLURAL_TAGS else -1)


def po2xml(catalog, with_untranslated=False, filter=None, warnfunc=dummy_warn):
    """Convert the gettext catalog in ``catalog`` to a ``ResourceTree``
    instance (our in-memory representation of an Android XML resource)

    This currently relies entirely in the fact that we can use the context
    of each message to specify the Android resource name (which we need
    to do to handle duplicates, but this is a nice by-product). However
    that also means we cannot handle arbitrary catalogs.

    The latter would in theory be possible by using the original,
    untranslated XML to match up a messages id to a resource name, but
    right now we don't support this (and it's not clear it would be
    necessary, even).

    If ``with_untranslated`` is given, then strings in the catalog
    that have no translation are written out with the original id,
    whenever this is safely possible. This does not include string-arrays,
    which for technical reasons always must include all elements, and it
    does not include plurals, for which the same is true.
    """

    # Validate that the plurals in the .po catalog match those that
    # we expect on the Android side per CLDR definition. However, we
    # only want to trouble the user with this if plurals are actually
    # used.
    plural_validation = {'done': False}
    def validate_plural_config():
        if plural_validation['done']:
            return
        if catalog.num_plurals != len(catalog.language.plural_keywords):
            warnfunc(('Catalog defines %d plurals, we expect %d for '
                      'this language. See the README for an '
                      'explanation. plurals have very likely been '
                      'incorrectly written.') % (
                catalog.num_plurals, len(catalog.language.plural_keywords)), 'error')
            pass
        plural_validation['done'] = True

    xml_tree = ResourceTree(getattr(catalog, 'language', None))
    for message in catalog:
        if not message.id:
            # This is the header
            continue

        if not message.context:
            warnfunc(('Ignoring message "%s": has no context; somebody other '+
                      'than android2po seems to have added to this '+
                      'catalog.') % message.id, 'error')
            continue

        if filter and filter(message):
            continue

        # Both string and id will contain a tuple of this is a plural
        value = message.string or message.id

        # A colon indicates a string array
        if ':' in message.context:
            # Collect all the strings of this array with their indices,
            # so when we're done processing the whole catalog, we can
            # sort by index and restore the proper array order.
            name, index = message.context.split(':', 2)
            index = int(index)
            xml_tree.setdefault(name, StringArray())
            while index >= len(xml_tree[name]):
                xml_tree[name].append(None)  # fill None for missing indices
            if xml_tree[name][index] is not None:
                warnfunc(('Duplicate index %s in array "%s"; ignoring '+
                          'the message. The catalog has possibly been '+
                          'corrupted.') % (index, name), 'error')
            xml_tree[name][index] = value

        # A plurals message
        elif isinstance(message.string, tuple):
            validate_plural_config()

            # Untranslated: Do not include those even with with_untranslated
            # is enabled - this is because even if we could put the plural
            # definition from the master resource here, it wouldn't make
            # sense in the context of another language. Instead, let access
            # to the untranslated master version continue to work.
            if not any(message.string):
                continue

            # We need to work with ``message.string`` directly rather than
            # ``value``, since ``message.id`` will only be a 2-tuple made
            # up of the msgid and msgid_plural definitions.
            xml_tree[message.context] = Plurals([
                (k, None) for k in catalog.language.plural_keywords])
            for index, keyword in enumerate(catalog.language.plural_keywords):
                # Assume each keyword matches one index.
                try:
                    xml_tree[message.context][keyword] = message.string[index]
                except IndexError:
                    # Plurals are not matching up, validate_plural_config()
                    # has already raised a warning.
                    break

        # A standard string.
        else:
            if not message.string and not with_untranslated:
                # Untranslated.
                continue
            xml_tree[message.context] = value

    return xml_tree


def write_xml(tree, warnfunc=dummy_warn):
    """Takes a ``ResourceTree`` (our in-memory representation of an Android
    XML resource) and returns a XML DOM (via an etree.Element).
    """
    # Convert the xml tree we've built into an actual Android XML DOM.
    root_tags = []
    namespaces_used = {}
    for name, value in tree.iteritems():
        if isinstance(value, StringArray):
            # string-array - first, sort by index
            array_el = etree.Element('string-array')
            array_el.attrib['name'] = name
            for i, v in enumerate(value):
                item_el = write_to_dom(
                    'item', v, '"%s" index %d' % (name, i), namespaces_used,
                    warnfunc)
                array_el.append(item_el)
            root_tags.append(array_el)
        elif isinstance(value, Plurals):
            # plurals
            plural_el = etree.Element('plurals')
            plural_el.attrib['name'] = name
            for k in sorted(value, cmp=sort_plural_keywords):
                item_el = write_to_dom(
                    'item', value[k], '"%s" quantity %s' % (name, k),
                    namespaces_used, warnfunc)
                item_el.attrib["quantity"] = k
                plural_el.append(item_el)
            root_tags.append(plural_el)
        else:
            # standard string
            string_el = write_to_dom(
                'string', value, '"%s"' % name, namespaces_used, warnfunc)
            string_el.attrib['name'] = name
            root_tags.append(string_el)

    # Generate the root element, define the namespaces that have been
    # used across all of our child elements.
    root_el = etree.Element('resources', nsmap=namespaces_used)
    for e in root_tags:
        root_el.append(e)
    return root_el

########NEW FILE########
__FILENAME__ = env
from __future__ import absolute_import

import os
import re
import glob
from argparse import Namespace
from os import path
from babel import Locale
from babel.core import UnknownLocaleError
from .config import Config
from .utils import Path, format_to_re
from .convert import read_xml, InvalidResourceError


__all__ = ('EnvironmentError', 'IncompleteEnvironment',
           'Environment', 'Language', 'resolve_locale')


class EnvironmentError(Exception):
    pass


class IncompleteEnvironment(EnvironmentError):
    pass


class Language(object):
    """Represents a single language.
    """

    def __init__(self, code, env=None):
        self.code = code
        self.env = env
        self.locale = Locale(code) if code else None

    def __unicode__(self):
        return unicode(self.code)

    def xml(self, kind):
        # Android uses a special language code format for the region part
        parts = tuple(self.code.split('_', 2))
        if len(parts) == 2:
            android_code = "%s-r%s" % parts
        else:
            android_code = "%s" % parts
        return self.env.path(self.env.resource_dir,
                             'values-%s/%s.xml' % (android_code, kind))

    def po(self, kind):
        filename = self.env.config.layout % {
            'group': kind,
            'domain': self.env.config.domain or 'android',
            'locale': self.code}
        return self.env.path(self.env.gettext_dir, filename)

    @property
    def plural_keywords(self):
        # Use .abstract rather than .rules because latter loses order
        return [r[0] for r in self.locale.plural_form.abstract] + ['other']


class DefaultLanguage(Language):
    """A special version of ``Language``, representing the default
    language.

    For the Android side, this means the XML files in the values/
    directory. For the gettext side, it means the .pot file(s).
    """

    def __init__(self, env):
        super(DefaultLanguage, self).__init__(None, env)

    def __unicode__(self):
        return u'<def>'

    def xml(self, kind):
        return self.env.path(self.env.resource_dir, 'values/%s.xml' % kind)

    def po(self, kind):
        filename = self.env.config.template_name % {
            'group': kind,
            'domain': self.env.config.domain or 'android',
        }
        return self.env.path(self.env.gettext_dir, filename)


def resolve_locale(code, env):
    """Return a ``Language`` instance for a locale code.

    Deals with incorrect values."""
    try:
        return Language(code, env)
    except UnknownLocaleError:
        env.w.action('failed', '%s is not a valid locale' % code)



def find_project_dir_and_config():
    """Goes upwards through the directory hierarchy and tries to find
    either an Android project directory, a config file for ours, or both.

    The latter case (both) can only happen if the config file is in the
    root of the Android directory, because once we have either, we stop
    searching.

    Note that the two are distinct, in that if a config file is found,
    it's directory is not considered a "project directory" from which
    default paths can be derived.

    Returns a 2-tuple (project_dir, config_file).
    """
    cur = os.getcwdu()

    while True:
        project_dir = config_file = None

        manifest_path = path.join(cur, 'AndroidManifest.xml')
        if path.exists(manifest_path) and path.isfile(manifest_path):
            project_dir = cur

        config_path = path.join(cur, '.android2po')
        if path.exists(config_path) and path.isfile(config_path):
            config_file = config_path

        # Stop once we found either.
        if project_dir or config_file:
            return project_dir, config_file

        # Stop once we're at the root of the filesystem.
        old = cur
        cur = path.normpath(path.join(cur, path.pardir))
        if cur == old:
            # No further change, we are probably at root level.
            # TODO: Is there a better way? Is path.ismount suitable?
            # Or we could split the path into pieces by path.sep.
            break

    return None, None


def find_android_kinds(resource_dir, get_all=False):
    """Return a list of Android XML resource types that are in use.

    For this, we simply have a look which xml files exists in the
    default values/ resource directory, and return those which
    include string resources.

    If ``get_all`` is given, the test for string resources will be
    skipped.
    """
    kinds = []
    search_dir = path.join(resource_dir, 'values')
    for name in os.listdir(search_dir):
        filename = path.join(search_dir, name)
        if path.isfile(filename) and name.endswith('.xml'):
            # We want to support arbitrary xml resource file names, but
            # we also need to make sure we only return those which actually
            # contain string resources. More specifically, a file named
            # my-colors.xml, containing only color resources, should not
            # result in a my-colors.po catalog to be created.
            #
            # We thus attempt to read each file here, see if there are any
            # strings in it. If we fail to parse a file, we return it and
            # trust that whatever command the user selected will later also
            # stumble and show a proper error.
            #
            # TODO:
            # I'm not entirely happy about this. One obvious problem is that
            # we are likely to parse these xml files twice, which seems like
            # a code smell. One potential solution: Stores the parsed XML
            # result directly in memory, with the environment, rather than
            # parsing it a second time later.
            #
            # We could also opt to fail outright if we encounter an invalid
            # XML file here, since the error doesn't belong to any "action".
            kind = path.splitext(name)[0]
            if kind in ('strings', 'arrays') or get_all:
                # These kinds are special, they are always supposed to
                # contain something translatable, so always include them.
                kinds.append(kind)
            else:
                try:
                    strings = read_xml(filename)
                except InvalidResourceError, e:
                    raise EnvironmentError('Failed to parse "%s": %s' % (filename, e))
                else:
                    # If there are any strings in the file, detect as
                    # a kind of xml file.
                    if strings:
                        kinds.append(kind)
    return kinds


class Environment(object):
    """Environment is the main object that holds all the data with
    which we run.

    Usage:

        env = Environment()
        env.pop_from_config(config)
        env.init()
    """

    def __init__(self, writer):
        self.w = writer
        self.xmlfiles = []
        self.default = DefaultLanguage(self)
        self.config = Config()
        self.auto_gettext_dir = None
        self.auto_resource_dir = None
        self.resource_dir = None
        self.gettext_dir = None

        # Try to determine if we are inside a project; if so, we a) might
        # find a configuration file, and b) can potentially assume some
        # default directory names.
        self.project_dir, self.config_file = find_project_dir_and_config()

    def _pull_into(self, namespace, target):
        """If for a value ``namespace`` there exists a corresponding
        attribute on ``target``, then update that attribute with the
        values from ``namespace``, and then remove the value from
        ``namespace``.

        This is needed because certain options, if passed on the command
        line, need nevertheless to be stored in the ``self.config``
        object. We therefore **pull** those values in, and return the
        rest of the options.
        """
        for name in dir(namespace):
            if name.startswith('_'):
                continue
            if name in target.__dict__:
                setattr(target, name, getattr(namespace, name))
                delattr(namespace, name)
        return namespace

    def _pull_into_self(self, namespace):
        """This is essentially like ``self._pull_info``, but we pull
        values into the environment object itself, and in order to avoid
        conflicts between option values and attributes on the environment
        (for example ``config``), we explicitly specify the values we're
        interested in: It's the "big" ones which we would like to make
        available on the environment object directly.
        """
        for name in ('resource_dir', 'gettext_dir'):
            if hasattr(namespace, name):
                setattr(self, name, getattr(namespace, name))
                delattr(namespace, name)
        return namespace

    def pop_from_options(self, argparse_namespace):
        """Apply the set of options given on the command line.

        These means that we need those options that are "configuration"
        values to end up in ``self.config``. The normal options will
        be made available as ``self.options``.
        """
        rest = self._pull_into_self(argparse_namespace)
        rest = self._pull_into(rest, self.config)
        self.options = rest

    def pop_from_config(self, argparse_namespace):
        """Load the values we support into our attributes, remove them
        from the ``config`` namespace, and store whatever is left in
        ``self.config``.
        """
        rest = self._pull_into_self(argparse_namespace)
        rest = self._pull_into(rest, self.config)
        # At this point, there shouldn't be anything left, because
        # nothing should be included in the argparse result that we
        # don't consider a configuration option.
        ns = Namespace()
        assert rest == ns

    def auto_paths(self):
        """Try to auto-fill some path values that don't have values yet.
        """
        if self.project_dir:
            if not self.resource_dir:
                self.resource_dir = path.join(self.project_dir, 'res')
                self.auto_resource_dir = True
            if not self.gettext_dir:
                self.gettext_dir = path.join(self.project_dir, 'locale')
                self.auto_gettext_dir = True

    def path(self, *pargs):
        """Helper that constructs a Path object using the project dir
        as the base."""
        return Path(*pargs, base=self.project_dir)

    def init(self):
        """Initialize the environment.

        This entails finding the default Android language resource files,
        and in the process doing some basic validation.
        An ``EnvironmentError`` is thrown if there is something wrong.
        """
        # If either of those is not specified, we can't continue. Raise a
        # special exception that let's the caller display the proper steps
        # on how to proceed.
        if not self.resource_dir or not self.gettext_dir:
            raise IncompleteEnvironment()

        # It's not enough for directories to be specified; they really
        # should exist as well. In particular, the locale/ directory is
        # not part of the standard Android tree and thus likely to not
        # exist yet, so we create it automatically, but ONLY if it wasn't
        # specified explicitely. If the user gave a specific location,
        # it seems right to let him deal with it fully.
        if not path.exists(self.gettext_dir) and self.auto_gettext_dir:
            os.makedirs(self.gettext_dir)
        elif not path.exists(self.gettext_dir):
            raise EnvironmentError('Gettext directory at "%s" doesn\'t exist.' %
                                   self.gettext_dir)
        elif not path.exists(self.resource_dir):
            raise EnvironmentError('Android resource direcory at "%s" doesn\'t exist.' %
                                   self.resource_dir)

        # Find the Android XML resources that are our original source
        # files, i.e. for example the values/strings.xml file.
        groups_found = find_android_kinds(self.resource_dir,
                                          get_all=bool(self.config.groups))
        if self.config.groups:
            self.xmlfiles = self.config.groups
            _missing = set(self.config.groups) - set(groups_found)
            if _missing:
                raise EnvironmentError('Unable to find the default XML '
                    'files for the following groups: %s' % (
                        ", ".join(["%s (%s)" % (
                            g, path.join(self.resource_dir, 'values', "%s.xml" % g)) for g in _missing])
                    ))
        else:
            self.xmlfiles = groups_found
        if not self.xmlfiles:
            raise EnvironmentError('no language-neutral string resources found in "values/".')

        # If regular expressions are used as ignore filters, precompile
        # those to help speed things along. For simplicity, we also
        # convert all static ignores to regexes.
        compiled_list = []
        for ignore_list in self.config.ignores:
            for ignore in ignore_list:
                if ignore.startswith('/') and ignore.endswith('/'):
                    compiled_list.append(re.compile(ignore[1:-1]))
                else:
                    compiled_list.append(re.compile("^%s$" % re.escape(ignore)))
        self.config.ignores = compiled_list

        # Validate the layout option, and resolve magic constants ("gnu")
        # to an actual format string.
        layout = self.config.layout
        multiple_pos = len(self.xmlfiles) > 1
        if not layout or layout == 'default':
            if self.config.domain and multiple_pos:
                layout = '%(domain)s-%(group)s-%(locale)s.po'
            elif self.config.domain:
                layout = '%(domain)s-%(locale)s.po'
            elif multiple_pos:
                layout = '%(group)s-%(locale)s.po'
            else:
                layout = '%(locale)s.po'
        elif layout == 'gnu':
            if multiple_pos:
                layout = '%(locale)s/LC_MESSAGES/%(group)s-%(domain)s.po'
            else:
                layout = '%(locale)s/LC_MESSAGES/%(domain)s.po'
        else:
            # TODO: These tests essentially disallow any advanced
            # formatting syntax. While that is unlikely to be used
            # or needed, a better way to test for the existance of
            # a placeholder would probably be to insert a unique string
            # and see if it comes out at the end; or, come up with
            # a proper regex to parse.
            if not '%(locale)s' in layout:
                raise EnvironmentError('--layout lacks %(locale)s variable')
            if self.config.domain and not '%(domain)s' in layout:
                raise EnvironmentError('--layout needs %(domain)s variable, ',
                                       'since you have set a --domain')
            if multiple_pos and not '%(group)s' in layout:
                raise EnvironmentError('--layout needs %%(group)s variable, '
                                       'since you have multiple groups: %s' % (
                                           ", ".join(self.xmlfiles)))
        self.config.layout = layout

        # The --template option needs similar processing:
        template = self.config.template_name
        if not template:
            if self.config.domain and multiple_pos:
                template = '%(domain)s-%(group)s.pot'
            elif self.config.domain:
                template = '%(domain)s.pot'
            elif multiple_pos:
                template = '%(group)s.pot'
            else:
                template = 'template.pot'
        elif '%s' in template and not '%(group)s' in template:
            # In an earlier version the --template option only
            # supported a %s placeholder for the XML kind. Make
            # sure we still support this.
            # TODO: Would be nice we if could raise a deprecation
            # warning here somehow. That means adding a callback
            # to this function. Or, probably we should just make the
            # environment aware of the writer object. This would
            # simplify other things as well.
            template = template.replace('%s', '%(group)s')
        else:
            # Note that we do not validate %(domain)s here; we expressively
            # allow the user to define a template without a domain.
            # TODO: See the same case above when handling --layout
            if multiple_pos and not '%(group)s' in template:
                raise EnvironmentError('--template needs %%(group)s variable, '
                                       'since you have multiple groups: %s' % (
                                           ", ".join(self.xmlfiles)))
        self.config.template_name = template

    LANG_DIR = re.compile(r'^values-(\w\w)(?:-r(\w\w))?$')
    def get_android_languages(self):
        """Finds the languages that already exist inside the Android
        resource directory.

        Return value is a list of ``Language`` instances.
        """
        languages = []
        for name in os.listdir(self.resource_dir):
            match = self.LANG_DIR.match(name)
            if not match:
                continue
            country, region = match.groups()
            code = "%s" % country
            if region:
                code += "_%s" % region
            language = resolve_locale(code, self)
            if language:
                languages.append(language)
        return languages

    def get_gettext_languages(self):
        """Finds the languages that already exist inside the gettext
        directory.

        This is a little more though than on the Android side, since
        we give the user a lot of flexibility in configuring how the
        .po files are layed out.

        Return value is a list of ``Language`` instances.
        """

        # Build a glob pattern based on the layout. This will enable
        # us to easily get a list of files that match the pattern.
        glob_pattern = self.config.layout % {
            'domain': self.config.domain,
            'group': '*',
            'locale': '*',
        }

        # Temporarily switch to the gettext directory. This allows us
        # to simply call glob() using the relative pattern, rather than
        # having to deal with making a full path, and then later on
        # stripping the full path again for the regex matching, and
        # potentially even running into problems when, say, the pattern
        # contains references like ../ to a parent directory.
        old_dir = os.getcwd()
        os.chdir(self.gettext_dir)
        try:
            list = glob.glob(glob_pattern)

            # We now have a list of matching .po files, but now idea
            # which languages they represent, because we don't know
            # which part of the filename is the locale. To solve this,
            # we build a regular expression from the format string,
            # one with a capture group where the locale code should be.
            regex = re.compile(format_to_re(self.config.layout))

            # We then try to match every single file returned by glob.
            # In this way, we can build a list of unique locale codes.
            languages = {}
            for item in list:
                m = regex.match(item)
                if not m:
                    continue
                code = m.groupdict()['locale']
                if not code in languages:
                    language = resolve_locale(code, self)
                    if language:
                        languages[code] = language

            return languages.values()
        finally:
            os.chdir(old_dir)

########NEW FILE########
__FILENAME__ = program
"""Implements the command line interface.
"""

from __future__ import absolute_import

import sys
from os import path

import argparse
if hasattr(argparse, '__version__') and argparse.__version__ < '1.1':
    raise RuntimeError('Needs at least argparse 1.1 to function, you are '+
                       'using: %s' % argparse.__version__)

# Resist the temptation to use "*". It won't work on Python 2.5.
from .commands import InitCommand, ExportCommand, ImportCommand, CommandError
from .env import IncompleteEnvironment, EnvironmentError, Environment, Language
from .config import Config
from .utils import Writer


__all__ = ('main', 'run',)


COMMANDS = {
    'init': InitCommand,
    'export': ExportCommand,
    'import': ImportCommand,
}


def parse_args(argv):
    """Builds an argument parser based on all commands and configuration
    values that we support.
    """
    from . import get_version
    parser = argparse.ArgumentParser(add_help=True,
        description='Convert Android string resources to gettext .po '+
                    'files, an import them back.',
        epilog='Written by: Michael Elsdoerfer <michael@elsdoerfer.com>')
    parser.add_argument('--version', action='version', version=get_version())

    # Create parser for arguments shared by all commands.
    base_parser = argparse.ArgumentParser(add_help=False)
    group = base_parser.add_mutually_exclusive_group()
    group.add_argument('--verbose', '-v', action='store_true',
                       help='be extra verbose')
    group.add_argument('--quiet', '-q', action='store_true',
                       help='be extra quiet')
    base_parser.add_argument('--config', '-c', metavar='FILE',
                             help='config file to use')
    # Add the arguments that set/override the configuration.
    group = base_parser.add_argument_group('configuration',
        'Those can also be specified in a configuration file. If given '
        'here, values from the configuration file will be overwritten.')
    Config.setup_arguments(group)
    # Add our commands with the base arguments + their own.
    subparsers = parser.add_subparsers(dest="command", title='commands',
                                       description='valid commands',
                                       help='additional help')
    for name, cmdclass in COMMANDS.items():
        cmd_parser = subparsers.add_parser(name, parents=[base_parser], add_help=True)
        group = cmd_parser.add_argument_group('command arguments')
        cmdclass.setup_arg_parser(group)

    return parser.parse_args(argv[1:])


def read_config(file):
    """Read the config file in ``file``.

    ``file`` may either be a file object, or a filename.

    The config file currently is simply a file with command line options,
    each option on a separate line.

    Just for reference purposes, the following ticket should be noted,
    which intends to extend argparse with support for configuration files:
        http://code.google.com/p/argparse/issues/detail?id=35
    Note however that the current patch doesn't seem to provide an easy
    way to make paths in the config relative to the config file location,
    as we currently need.
    """

    if hasattr(file, 'read'):
        lines = file.readlines()
        if hasattr(file, 'name'):
            filename = file.name
        else:
            filename = None
    else:
        # Open the config file and read the arguments.
        filename = file
        f = open(file, 'rb')
        try:
            lines = f.readlines()
        finally:
            f.close()

    args = filter(lambda x: bool(x),     # get rid of '' elements
                  map(str.strip,         # get rid of surrounding whitespace
                      " ".join(filter(lambda x: not x.strip().startswith('#'),
                                      lines)
                      ).split(" ")))

    # Use a parser that specifically only supports those options that
    # we want to support within a config file (as opposed to all the
    # options available through the command line interface).
    parser = argparse.ArgumentParser(add_help=False)
    Config.setup_arguments(parser)
    config, unprocessed = parser.parse_known_args(args)
    if unprocessed:
        raise CommandError("unsupported config values: %s" % ' '.join(unprocessed))

    # Post process the config: Paths in the config file should be relative
    # to the config location, not the current working directory.
    if filename:
        Config.rebase_paths(config, path.dirname(filename))

    return config


def make_env_and_writer(argv):
    """Given the command line arguments in ``argv``, construct an
    environment.

    This entails everything from parsing the command line, parsing
    a config file, if there is one, merging the two etc.

    Returns a 2-tuple (``Environment`` instance, ``Writer`` instance).
    """

    # Parse the command line arguments first. This is helpful in
    # that any potential syntax errors there will cause us to
    # fail before doing anything else.
    options = parse_args(argv)

    # Setup the writer verbosity threshold based on the options.
    writer = Writer()
    if options.verbose:
        writer.verbosity = 3
    elif options.quiet:
        writer.verbosity = 1
    else:
        writer.verbosity = 2

    env = Environment(writer)

    # Try to load a config file, either if given at the command line,
    # or the one that was automatically found. Note that even if a
    # config file is used, using the default paths is still supported.
    # That is, you can provide some extra configuration values
    # through a file, potentially shared across multiple projects, and
    # still rely on simply calling the script inside a default
    # project's directory hierarchy.
    config_file = None
    if options.config:
        config_file = options.config
        env.config_file = config_file
    elif env.config_file:
        config_file = env.config_file
        writer.action('info', "Using auto-detected config file: %s"  % config_file)
    if config_file:
        env.pop_from_config(read_config(config_file))

    # Now that we have applied the config file, also apply the command
    # line options. Those will thus override the config values.
    env.pop_from_options(options)

    # Some paths, if we still don't have values for them, can be deducted
    # from the project directory.
    env.auto_paths()
    if env.auto_gettext_dir or env.auto_resource_dir:
        # Let the user know we are deducting information from the
        # project that we found.
        writer.action('info',
                      "Assuming default directory structure in %s" % env.project_dir)

    # Initialize the environment. This mainly loads the list of
    # languages, but also does some basic validation.
    try:
        env.init()
    except IncompleteEnvironment:
        if not env.project_dir:
            if not env.config_file:
                raise CommandError('You need to run this from inside an '
                    'Android project directory, or specify the source and '
                    'target directories manually, either as command line '
                    'options, or through a configuration file')
            else:
                raise CommandError('Your configuration file does not specify '
                    'the source and target directory, and you are not running '
                    'the script from inside an Android project directory.')
    except EnvironmentError, e:
        raise CommandError(e)

    # We're done. Just print some info out for the user.
    writer.action('info',
                  "Using as Android resource dir: %s" % env.resource_dir)
    writer.action('info', "Using as gettext dir: %s" % env.gettext_dir)

    return env, writer


def main(argv):
    """The program.

    Returns an error code or None.
    """
    try:
        # Build an environment from the list of arguments.
        env, writer = make_env_and_writer(argv)
        try:
            cmd = COMMANDS[env.options.command](env, writer)
            command_result = cmd.execute()
        finally:
            writer.finish()
        return 1 if writer.erroneous else 0
    except CommandError, e:
        print 'Error:', e
        return 2


def run():
    """Simplified interface to main().
    """
    sys.exit(main(sys.argv) or 0)

########NEW FILE########
__FILENAME__ = termcolors
"""termcolors.py - this is adapted from Django SVN (utils/termcolors.py)
revision 12800.

The support for color palettes has been removed, and the supports_color()
helper from core/management/color.py has been merged in.#

colored() was added to provide a warpper around colorize() that falss back
on printing non-color text if the terminal doesn't support it.

__all__ was added.
"""

import sys


__all__ = ('colorize', 'colored', 'make_style', 'supports_color',)


color_names = ('black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white')
foreground = dict([(color_names[x], '3%s' % x) for x in range(8)])
background = dict([(color_names[x], '4%s' % x) for x in range(8)])

RESET = '0'
opt_dict = {'bold': '1', 'underscore': '4', 'blink': '5', 'reverse': '7', 'conceal': '8'}


def colored(text='', *args, **kwargs):
    """Render the text with the given color style if supported (see
    ``colorize`` for arguments), or without color otherwise.
    """
    if supports_color():
        return colorize(text, *args, **kwargs)
    else:
        return text


def colorize(text='', opts=(), **kwargs):
    """
    Returns your text, enclosed in ANSI graphics codes.

    Depends on the keyword arguments 'fg' and 'bg', and the contents of
    the opts tuple/list.

    Returns the RESET code if no parameters are given.

    Valid colors:
        'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'

    Valid options:
        'bold'
        'underscore'
        'blink'
        'reverse'
        'conceal'
        'noreset' - string will not be auto-terminated with the RESET code

    Examples:
        colorize('hello', fg='red', bg='blue', opts=('blink',))
        colorize()
        colorize('goodbye', opts=('underscore',))
        print colorize('first line', fg='red', opts=('noreset',))
        print 'this should be red too'
        print colorize('and so should this')
        print 'this should not be red'
    """
    code_list = []
    if text == '' and len(opts) == 1 and opts[0] == 'reset':
        return '\x1b[%sm' % RESET
    for k, v in kwargs.iteritems():
        if k == 'fg':
            code_list.append(foreground[v])
        elif k == 'bg':
            code_list.append(background[v])
    for o in opts:
        if o in opt_dict:
            code_list.append(opt_dict[o])
    if 'noreset' not in opts:
        text = text + '\x1b[%sm' % RESET
    return ('\x1b[%sm' % ';'.join(code_list)) + text


def make_style(opts=(), **kwargs):
    """
    Returns a function with default parameters for colorize()

    Example:
        bold_red = make_style(opts=('bold',), fg='red')
        print bold_red('hello')
        KEYWORD = make_style(fg='yellow')
        COMMENT = make_style(fg='blue', opts=('bold',))
    """
    return lambda text: colorize(text, opts, **kwargs)


def supports_color():
    """
    Returns True if the running system's terminal supports color, and False
    otherwise.
    """
    unsupported_platform = (sys.platform in ('win32', 'Pocket PC'))
    # isatty is not always implemented, #6223.
    is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    if unsupported_platform or not is_a_tty:
        return False
    return True

########NEW FILE########
__FILENAME__ = utils
from __future__ import absolute_import

import os, sys, re, uuid, locale
import codecs
try:
    from hashlib import md5
except ImportError:
   import md5
from os import path

from .termcolors import colored


__all__ = ('Path', 'Writer', 'file_md5', 'format_to_re',)


def format_to_re(format):
    """Return the regular expression that matches all possible values
    the given Python 2 format string (using %(foo)s placeholders) can
    possibly resolve to.

    Each placeholder in the format string is captured in a named group.

    The difficult part here is inserting unescaped regular expression
    syntax in place of the format variables, while still properly
    escaping the rest.

    See this link for more info on the problem:
    http://stackoverflow.com/questions/2654856/python-convert-format-string-to-regular-expression
    """
    UNIQ = uuid.uuid1().hex
    assert not UNIQ in format
    class MarkPlaceholders(dict):
        def __getitem__(self, key):
            return UNIQ+('(?P<%s>.*?)'%key)+UNIQ
    parts = (format % MarkPlaceholders()).split(UNIQ)
    for i in range(0, len(parts), 2):
        parts[i] = re.escape(parts[i])
    return ''.join(parts)


def file_md5(filename):
    """Generate the md5 hash of the given file.
    """
    h = md5()
    f = open(filename, 'rb')
    try:
        while True:
            # 128 is the md5 digest blocksize
            data = f.read(128*10)
            if not data:
                break
            h.update(data)
        return h.digest()
    finally:
        f.close()


class Path(unicode):
    """Helper representing a filesystem path that can be "bound" to a base
    path. You can then ask it to render as a relative path to that base.
    """

    def __new__(self, *parts, **kwargs):
        base = kwargs.pop('base', None)
        if kwargs:
            raise TypeError()
        self.base = base
        abs = path.normpath(path.abspath(path.join(*parts)))
        return unicode.__new__(self, abs)

    @property
    def rel(self):
        """Return this path relative to the base it was bound to.
        """
        base =  self.base or os.getcwd()
        if not hasattr(path, 'relpath'):
            # Python < 2.6 doesn't have relpath, and I don't want
            # to bother with a wbole bunch of code for this. See
            # if we can simply remove the prefix, and if not, 2.5
            # users will have to live with the absolute path.
            if self.path.startswith(base):
                return self.path[len(base)+1:]
            return self.abs
        return path.relpath(self, start=base)

    @property
    def abs(self):
        return self

    def exists(self):
        return path.exists(self)

    @property
    def dir(self):
        return Path(path.dirname(self), base=self.base)

    def hash(self):
        return file_md5(self)


class Writer():
    """Helps printing messages to the output, in a very particular form.

    Supported are two concepts, "actions" and "messages". A message is
    always the child of an action. There is a limited set of action
    types (we call them events). Each event and each message may have a
    "severity". The severity can determine how a message or event is
    rendered (if the terminals supports colors), and will also affect
    whether a action or message is rendered at all, depending on verbosity
    settings.

    If a message exceeds it's action in severity causing the message to
    be visible but the action not, the action will forcably be rendered as
    well. For this reason, the class keeps track of the last message that
    should have been printed.

    There is also a mechanism which allows to delay printing an action.
    That is, you may begin constructing an action and collecting it's
    messages, and only later print it out. You would want to do this if
    the event type can only be determined after the action is completed,
    since it often indicates the outcome.
    """

    # Action types and their default levels
    EVENTS = {
        'info': 'info',
        'mkdir': 'default',
        'updated': 'default',
        'unchanged': 'default',
        'skipped': 'warning',
        'created': 'default',
        'exists': 'default',
        'failed': 'error',}

    # Levels and the minimum verbosity required to show them
    LEVELS = {'default': 2, 'warning': 1, 'error': 0, 'info': 3}

    # +2 for [ and ]
    # +1 for additional left padding
    max_event_len = max([len(k) for k in EVENTS.keys()]) + 2 + 1

    class Action(dict):
        def __init__(self, writer, *more, **data):
            self.writer = writer
            self.messages = []
            self.is_done = False
            self.awaiting_promotion = False
            dict.__init__(self, {'text': '', 'status': None, 'severity': None})
            self.update(*more, **data)

        def __setitem__(self, name, value):
            if name == 'severity':
                assert value in Writer.LEVELS, 'Not a valid severity value'
            dict.__setitem__(self, name, value)

        def done(self, event, *more, **data):
            """Mark this action as done. This will cause it and it's
            current messages to be printed, provided they pass the
            verbosity threshold, of course.
            """
            assert event in Writer.EVENTS, 'Not a valid event type'
            self['event'] = event
            self.update(*more, **data)
            self.writer._print_action(self)
            if self in self.writer._pending_actions:
                self.writer._pending_actions.remove(self)
            self.is_done = True
            if self.severity == 'error':
                self.writer.erroneous = True

        def update(self, text=None, severity=None, **more_data):
            """Update the message with the given data.
            """
            if text:
                self['text'] = text
            if severity:
                self['severity'] = severity
            dict.update(self, **more_data)

        def message(self, message, severity='info'):
            """Print a message belonging to this action.

            If the action is not yet done, this will be added to
            an internal queue.

            If the action is done, but was not printed because it didn't
            pass the verbosity threshold, it will be printed now.

            By default, all messages use a loglevel of 'info'.
            """
            is_allowed = self.writer.allowed(severity)
            if severity == 'error':
                self.writer.erroneous = True
            if not self.is_done:
                if is_allowed:
                    self.messages.append((message, severity))
            elif is_allowed:
                if self.awaiting_promotion:
                    self.writer._print_action(self, force=True)
                self.writer._print_message(message, severity)

        @property
        def event(self):
            return self['event']

        @property
        def severity(self):
            sev = self['severity']
            if not sev:
                sev = Writer.EVENTS[self.event]
            return sev

    def __init__(self, verbosity=LEVELS['default']):
        self._current_action = None
        self._pending_actions = []
        self.verbosity = verbosity
        self.erroneous = False

        # Create a codec writer wrapping stdout
        isatty = sys.stdout.isatty() \
            if hasattr(sys.stdout, 'isatty') else False
        self.stdout = codecs.getwriter(
            sys.stdout.encoding
                if isatty
                else locale.getpreferredencoding())(sys.stdout)

    def action(self, event, *a, **kw):
        action = Writer.Action(self, *a, **kw)
        action.done(event)
        return action

    def begin(self, *a, **kw):
        """Begin a new action, and return it. The action will not be
        printed until you call ``done()`` on it.

        In the meantime, you can attach message to it though, which will
        be printed together with the action once it is "done".
        """
        action = Writer.Action(self, *a, **kw)
        self._pending_actions.append(action)
        return action

    def message(self, *a, **kw):
        """Attach a message to the last action to be completed. This
        includes actions that have not yet been printed (due to not
        passing the threshold), but does not include actions that are
        not yet marked as 'done'.
        """
        self._current_action.message(*a, **kw)

    def finish(self):
        """Close down all pending actions that have been began(), but
        are not yet done.

        Not the sibling of begin()!
        """
        for action in self._pending_actions:
            if not action.is_done:
                action.done('failed')
        self._pending_actions = []

    def allowed(self, severity):
        """Return ``True`` if mesages with this severity pass
        the current verbosity threshold.
        """
        return self.verbosity >= self.LEVELS[severity]

    def _get_style_for_level(self, severity):
        """Return a dict that can be passed as **kwargs to colored().
        """
        # Other colors that work moderately well on both dark and
        # light backgrounds and aren't yet used: cyan, green
        return {
            'default': {'fg': 'blue'},
            'info': {},
            'warning': {'fg': 'magenta'},
            'error': {'fg': 'red'},
        }.get(severity, {})

    def get_style_for_action(self, action):
        """First looks at the event type to determine a style, then
        falls back to severity for good measure.
        """
        try:
            return {
                'info': {},   # alyways render info in default
                'exists': {'fg': 'blue'}
            }[action.event]
        except KeyError:
            return self._get_style_for_level(action.severity)

    def _print_action(self, action, force=False):
        """Print the action and all it's attached messages.
        """
        if force or self.allowed(action.severity) or action.messages:
            self._print_action_header(action)
            for m, severity in action.messages:
                self._print_message(m, severity)
            action.awaiting_promotion = False
        else:
            # Indicates that this message has not been printed yet,
            # and is waiting for a dependent message that needs to
            # be printed to trigger it.
            action.awaiting_promotion = True
        self._current_action = action

    def _print_action_header(self, action):
        text = action['text']
        status = action['status']
        if isinstance(text, Path):
            # Handle Path instances manually. This doesn't happen
            # automatically because we haven't figur out how to make
            # that class represent itself through the relative path
            # by default, while still returning the full path if it
            # is used, say, during an open() operation.
            text = text.rel
        if status:
            text = "%s (%s)" % (text, status)
        tag = "[%s]" % action['event']

        style = self.get_style_for_action(action)
        self.stdout.write(colored("%*s" % (self.max_event_len, tag), opts=('bold',), **style))
        self.stdout.write(colored(opts=('noreset',), **style))
        self.stdout.write(" ")
        self.stdout.write(text)
        self.stdout.write(colored())
        self.stdout.write("\n")

    def _print_message(self, message, severity):
        style = self._get_style_for_level(severity)
        self.stdout.write(colored(" "*(self.max_event_len+1) + u"- %s" % message,
                          **style))
        self.stdout.write("\n")

########NEW FILE########
__FILENAME__ = test_plurals
"""Android supports plurals. Make sure we can handle them properly.
"""

from StringIO import StringIO
from lxml import etree
from babel.messages.catalog import Catalog
from android2po import xml2po, po2xml, read_xml
from android2po.env import Language
from ..helpers import TestWarnFunc


def xmlstr2po(string):
    return xml2po(read_xml(StringIO(string)))


def test_read_master_xml():
    """Convert a master XML resource to a catalog, ensure that the
    plurals' msgid/msgid_plural values are correctly set.

    (what the export command does).
    """
    catalog = xmlstr2po('''
        <resources>
            <plurals name="foo">
                <item quantity="one">bar</item>
                <item quantity="other">bars</item>
            </plurals>
        </resources>
    ''')
    assert len(list(catalog)) == 2
    assert [m.context for m in catalog if m.id] == ['foo']
    assert [m.id for m in catalog if m.id] == [('bar', 'bars')]


def test_read_language_xml():
    """Convert a XML resource to a catalog, while matching strings
    up with translations from another resource.

    (what the init command does).
    """
    wfunc = TestWarnFunc()

    catalog, _ = xml2po(read_xml(StringIO('''
        <resources>
            <plurals name="foo">
                <item quantity="one">one</item>
                <item quantity="other">other</item>
            </plurals>
        </resources>
    ''')), read_xml(StringIO('''
        <resources>
            <plurals name="foo">
                <item quantity="one">ro one</item>
                <item quantity="few">ro few</item>
                <item quantity="many">ro many</item>
                <item quantity="other">ro other</item>
            </plurals>
        </resources>
    '''),
            language=Language('ro')), # Romanian
            warnfunc=wfunc)

    # A warning has been written for the unsupported quantity
    assert len(wfunc.logs) == 1
    assert 'uses quantity "many", which is not supported ' in wfunc.logs[0]

    assert [m.id for m in catalog if m.id] == [('one', 'other')]
    # Note: Romanian does not use the "many" string, so it is not included.
    assert [m.string for m in catalog if m.id] == [
        ('ro one', 'ro few', 'ro other')]

    # Make sure the catalog has the proper header
    assert catalog.num_plurals == 3
    assert catalog.plural_expr == '((n == 1) ? 0 : ((n == 0) || ((n != 1) && ((n % 100) >= 1 && (n % 100) <= 19))) ? 1 : 2)'


def test_write():
    """Test a basic po2xml() call.

    (what the import command does).
    """
    catalog = Catalog()
    catalog.language = Language('bs') # Bosnian
    catalog.add(('foo', 'foos'), ('one', 'few', 'many', 'other'), context='foo')
    assert po2xml(catalog) == {'foo': {
        'few': 'few', 'many': 'many', 'other': 'other', 'one': 'one'}}


def test_write_incomplete_plural():
    """Test behaviour with incompletely translated plurals in .po."""
    catalog = Catalog()
    catalog.language = Language('bs') # Bosnian
    catalog.add(('foo', 'foos'), ('one', '', 'many', ''), context='foo')
    assert po2xml(catalog) == {'foo': {
        'few': '', 'many': 'many', 'other': '', 'one': 'one'}}


def test_write_incorrect_plural():
    """Test what happens when the .po catalog contains the wrong
    plural information.
    """
    catalog = Catalog()
    catalog.language = Language('lt') # Lithuanian
    # Lithuanian has three plurals, we define 2.
    catalog._num_plurals, catalog._plural_expr = 2, '(n != 1)'
    catalog.add(('foo', 'foos'), ('a', 'b',), context='foo')

    wfunc = TestWarnFunc()
    xml = po2xml(catalog, warnfunc=wfunc)

    # A warning was written
    assert len(wfunc.logs) == 1
    assert '2 plurals, we expect 3' in wfunc.logs[0]

    # The missing plural is empty
    assert xml == {'foo': {'few': 'b', 'other': None, 'one': 'a'}}


def test_write_ignore_untranslated_plural():
    """An untranslated plural is not included in the XML.
    """
    catalog = Catalog()
    catalog.language =  Language('en')
    catalog.add(('foo', 'foos'), context='foo')
    assert po2xml(catalog) == {}

    # Even with ``with_untranslated``, we still do not include
    # empty plural (they would just block access to the untranslated
    # master version, which we cannot copy into the target).
    assert po2xml(catalog) == {}


########NEW FILE########
__FILENAME__ = test_read_write_xml
"""Test converting from our internal ``ResourceTree`` structure to and from
actual XML.

The other tests validate only the ``ResourceTree`` created. Note that the
escaping details etc. are tested in test_text.py.
"""

from lxml import etree
from android2po.convert import write_xml, Plurals, StringArray


def c(dom):
    print etree.tostring(write_xml(dom))
    return etree.tostring(write_xml(dom))


class TestWriteXML(object):

    def test_string(self):
        assert c({'foo': 'bar'}) == \
            '<resources><string name="foo">bar</string></resources>'

    def test_plurals(self):
        assert c({'foo': Plurals({'one': 'bar', 'other': 'bars'})}) == \
            '<resources><plurals name="foo"><item quantity="one">bar</item><item quantity="other">bars</item></plurals></resources>'

    def test_arrays(self):
        assert c({'foo': StringArray(['bar1', 'bar2'])}) == \
            '<resources><string-array name="foo"><item>bar1</item><item>bar2</item></string-array></resources>'

########NEW FILE########
__FILENAME__ = test_special
"""Various conversion-special cases.
"""

from __future__ import absolute_import

from StringIO import StringIO
from lxml import etree
from babel.messages import Catalog
from nose.tools import assert_raises
from android2po import xml2po, po2xml, read_xml, write_xml
from ..helpers import TempProject, TestWarnFunc


def xmlstr2po(string):
    return xml2po(read_xml(StringIO(string)))


def test_trailing_whitespace():
    # [bug] Make sure that whitespace after the <string> tag does not
    # end up as part of the value.
    catalog = xmlstr2po(
        '<resources><string name="foo">bar</string>    \t\t  </resources>')
    assert list(catalog)[1].id == 'bar'


def test_translatable():
    """Strings marked as translatable=False will be skipped.
    """
    catalog = xmlstr2po(
        '<resources><string name="foo" translatable="false">bar</string></resources>')
    assert len(catalog) == 0

    catalog = xmlstr2po(
        '<resources><string name="foo" translatable="true">bar</string></resources>')
    assert list(catalog)[1].id == 'bar'

    catalog = xmlstr2po(
        '<resources><string-array name="foo" translatable="false"><item>bla</item></string-array></resources>')
    assert len(catalog) == 0


def test_formatted():
    """Strings with "%1$s" and other Java-style format markers
       will be marked as c-format in the gettext flags.
    """
    catalog = xmlstr2po(
        '<resources><string name="foo">foo %1$s bar</string></resources>')
    assert "c-format" in list(catalog)[1].flags

    catalog = xmlstr2po(
        '<resources><string name="foo">foo %% bar</string></resources>')
    assert "c-format" not in list(catalog)[1].flags

    catalog = xmlstr2po(
        '<resources><string name="foo">foo</string></resources>')
    assert "c-format" not in list(catalog)[1].flags

    catalog = xmlstr2po(
        '<resources><string-array name="foo"><item>foo %1$s bar</item></string-array></resources>')
    assert "c-format" in list(catalog)[1].flags

    catalog = xmlstr2po(
        '<resources><string-array name="foo"><item>foo %% bar</item></string-array></resources>')
    assert "c-format" not in list(catalog)[1].flags

    catalog = xmlstr2po(
        '<resources><string-array name="foo"><item>bar</item></string-array></resources>')
    assert "c-format" not in list(catalog)[1].flags

    # Babel likes to add python-format
    catalog = xmlstr2po(
        '<resources><string name="foo">foo %s bar</string></resources>')
    assert "c-format" in list(catalog)[1].flags
    assert not "python-format" in list(catalog)[1].flags

    catalog = xmlstr2po(
        '<resources><string-array name="foo"><item>foo %s bar</item></string-array></resources>')
    assert "c-format" in list(catalog)[1].flags
    assert not "python-format" in list(catalog)[1].flags

    # Ensure that Babel doesn't add python-format on update ("export")
    # either. Yes, this is hard to get rid of.
    p = TempProject(default_xml={'foo': 'with %s format'})
    try:
        p.program('init', {'de': ''})
        p.program('export')
        catalog = p.get_po('de.po')
        assert not 'python-format' in list(catalog)[1].flags
    finally:
        p.delete()


def test_invalid_xhtml():
    """Ensure we can deal with broken XML in messages.
    """
    c = Catalog()
    c.add('Foo', '<i>Tag is not closed', context="foo")

    # [bug] This caused an exception in 16263b.
    dom = write_xml(po2xml(c))

    # The tag was closed automatically (our loose parser tries to fix errors).
    assert etree.tostring(dom) == '<resources><string name="foo"><i>Tag is not closed</i></string></resources>'


def test_untranslated():
    """Test that by default, untranslated strings are not included in the
    imported XML.
    """
    catalog = Catalog()
    catalog.add('green', context='color1')
    catalog.add('red', 'rot', context='color2')
    assert po2xml(catalog) == {'color2': 'rot'}

    # If with_untranslated is passed, then all strings are included.
    # Note that arrays behave differently (they always include all
    # strings), and this is tested in test_string_arrays.py).
    assert po2xml(catalog, with_untranslated=True) ==\
           {'color1': 'green', 'color2': 'rot'}


class Xml2PoTest:
    """Helper to test xml2po() with ability to check warnings.
    """
    @classmethod
    def make_raw(cls, content):
        logger = TestWarnFunc()
        return xml2po(read_xml(StringIO(content), warnfunc=logger),
                      warnfunc=logger), logger.logs

    @classmethod
    def make(cls, name, value):
        return cls.make_raw('<resources><string name="%s">%s</string></resources>' % (
            name, value))


class TestAndroidResourceReferences(Xml2PoTest):
    """Dealing with things like @string/app_name is not quite
    as straightforward as one might think.

    Note that the low-level escaping is tested in test_text.py.
    """

    def test_not_exported(self):
        """Strings with @-references are not being included during
        export.
        """
        catalog, logs = self.make('foo', '@string/app_name')
        assert len(catalog) == 0

        # A log message was printed
        assert 'resource reference' in logs[0]

        # Leading whitespace is stripped, as usual...
        catalog, _ = self.make('foo', '     @string/app_name     ')
        assert len(catalog) == 0

        # ...except if this is HTML.
        catalog, _ = self.make('foo', '@string/app_name<b>this is html</b>')
        assert len(catalog) == 1

    def test_string_array(self):
        """string-arrays that include @references are even more
        complicated. We don't currently support them properly, and
        need to raise a warning.
        """
        catalog, logs = self.make_raw('''
              <resources><string-array name="test">
                  <item>no-ref</item>
                  <item>@ref</item>
                  <item>@seems <b>like a ref</b></item>
              </string-array></resources>''')
        # One item, the reference, will be missing.
        assert len(catalog) == 2

        # A warning was printed
        assert 'resource reference' in logs[0]


def test_empty_resources():
    """Empty resources are removed and not included in a catalog.
    """
    catalog, logs = Xml2PoTest.make('foo', '     ')
    assert len(catalog) == 0
    assert 'empty' in logs[0]

    catalog, logs = Xml2PoTest.make_raw('''
        <resources>
            <string-array name="test">
                <item></item>
                <item>          </item>
            </string-array>
        </resources>
    ''')
    assert len(catalog) == 0
    assert 'empty' in logs[0]
    assert 'empty' in logs[1]


class TestComments:
    """Test the processing of comments in xml files.
    """

    def test_string(self):
        catalog = xmlstr2po(
        '''<resources>
              <!-- Comment 1 -->
              <!-- Comment 2 -->
              <string name="string1">value1</string>
              <string name="string2">value2</string>
           </resources>''')
        # TODO: Should those be stripped? Otherwise formatted (linebreaks etc)?
        assert catalog.get('value1', context='string1').auto_comments == [' Comment 1 ', ' Comment 2 ']
        assert catalog.get('value2', context='string2').auto_comments == []

    def test_string_array(self):
        catalog = xmlstr2po(
        '''<resources>
              <!-- Comment 1 -->
              <!-- Comment 2 -->
              <string-array name="array">
                  <item>item1</item>
                  <!-- this will be ignored -->
                  <item>item2</item>
              </string-array>
              <string name="string">value</string>
           </resources>''')
        assert catalog.get('item1', context='array:0').auto_comments == [' Comment 1 ', ' Comment 2 ']
        assert catalog.get('item2', context='array:1').auto_comments == [' Comment 1 ', ' Comment 2 ']
        assert catalog.get('value', context='string').auto_comments == []

    def test_translatable(self):
        """[bug] Make sure translatable=false and comments play nice together.
        """
        catalog = xmlstr2po(
        '''<resources>
              <!-- Comment 1 -->
              <!-- Comment 2 -->
              <string name="string1" translatable="false">value1</string>
              <string name="string2">value2</string>
           </resources>''')
        # The comments of string1 do not end up with string2.
        assert catalog.get('value2', context='string2').auto_comments == []

    def test_nameless(self):
        """This is an edge-case, but we don't (can't) process strings
        without a name. Comments are not passed along there either.
        """
        catalog = xmlstr2po(
        '''<resources>
              <!-- Comment 1 -->
              <!-- Comment 2 -->
              <string>value1</string>
              <string name="string2">value2</string>
           </resources>''')
        # The comments of string1 do not end up with string2.
        assert catalog.get('value2', context='string2').auto_comments == []

########NEW FILE########
__FILENAME__ = test_string_arrays
"""Android supports string-arrays. Make sure we can handle them properly.
"""

from __future__ import absolute_import

from android2po import xml2po, po2xml, read_xml
from StringIO import StringIO
from lxml import etree
from babel.messages.catalog import Catalog
from ..helpers import TestWarnFunc
from android2po.env import Language


def xmlstr2po(string):
    return xml2po(read_xml(StringIO(string)))


def test_read_template():
    """Test basic read.
    """
    catalog = xmlstr2po('''
        <resources>
            <string-array name="colors">
                <item>red</item>
                <item>green</item>
            </string-array>
        </resources>
    ''')
    assert len(list(catalog)) == 3
    assert [m.context for m in catalog if m.id] == ['colors:0', 'colors:1']


def test_read_order():
    """Test that a strings of a string-array have the same position
    in the final catalog as the string-array had in the xml file, e.g.
    order is maintained for the string-array.
    """
    catalog = xmlstr2po('''
        <resources>
            <string name="before">foo</string>
            <string-array name="colors">
                <item>red</item>
                <item>green</item>
            </string-array>
            <string name="after">bar</string>
        </resources>
    ''')
    assert len(list(catalog)) == 5
    assert [m.context for m in catalog if m.id] == [
                'before', 'colors:0', 'colors:1', 'after']


def test_read_language():
    """Test that when reading a translated xml file, the translations
    of a string array are properly matched up with to strings in the
    untranslated template.
    """
    catalog, _ = xml2po(read_xml(StringIO('''
        <resources>
            <string-array name="colors">
                <item>red</item>
                <item>green</item>
            </string-array>
        </resources>
    ''')), read_xml(StringIO('''
        <resources>
            <string-array name="colors">
                <item>rot</item>
                <item>gruen</item>
            </string-array>
        </resources>
    '''), language=Language('de')))

    assert len(list(catalog)) == 3
    assert [m.context for m in catalog if m.id] == ['colors:0', 'colors:1']
    assert [m.id for m in catalog if m.id] == ['red', 'green']
    assert [m.string for m in catalog if m.id] == ['rot', 'gruen']


def test_write():
    """Test writing a basic catalog.
    """
    catalog = Catalog()
    catalog.add('green', context='colors:0')
    catalog.add('red', context='colors:1')
    assert po2xml(catalog) == {'colors': ['green', 'red']}


def test_write_order():
    """Test that when writing a catalog with string-arrays, order is
    maintained; both of the string-array tag in the list of all strings,
    as well as the array strings themselves.
    """
    catalog = Catalog()
    catalog.add('foo', 'foo', context='before')
    catalog.add('red', 'rot', context='colors:1')
    catalog.add('green', 'gruen', context='colors:0')
    catalog.add('bar', 'bar', context='after')
    assert po2xml(catalog) == {
        'before': 'foo',
        'colors': ['gruen', 'rot'],
        'after': 'bar'}


def test_write_order_long_array():
    """[Regression] Test that order is maintained for a long array.
    """
    catalog = Catalog()
    catalog.add('foo', 'foo', context='before')
    for i in range(0, 13):
        catalog.add('loop%d' % i, 'schleife%d' % i, context='colors:%d' % i)
    catalog.add('bar', 'bar', context='after')
    assert po2xml(catalog) == {
        'before': 'foo',
        'colors': ['schleife0', 'schleife1', 'schleife2', 'schleife3',
                   'schleife4', 'schleife5', 'schleife6', 'schleife7',
                   'schleife8', 'schleife9', 'schleife10', 'schleife11',
                   'schleife12'],
        'after': 'bar'}


def test_write_missing_translations():
    """[Regression] Specifically test that arrays are not written to the
    XML in an incomplete fashion if parts of the array are not translated.
    """
    catalog = Catalog()
    catalog.add('green', context='colors:0')    # does not have a translation
    catalog.add('red', 'rot', context='colors:1')
    assert po2xml(catalog) == {'colors': ['green', 'rot']}


def test_write_skipped_ids():
    """Test that arrays were ids are missing are written properly out as well.
    """
    # TODO: Indices missing at the end of the array will not be noticed,
    # because we are not aware of the arrays full length.
    # TODO: If we where smart enough to look in the original resource XML,
    # we could fill in missing array strings with the untranslated value.
    catalog = Catalog()
    catalog.add('red', context='colors:3')
    catalog.add('green', context='colors:1')
    assert po2xml(catalog) == {'colors': [None, 'green', None, 'red']}


def test_unknown_escapes():
    """Test that unknown escapes are processed correctly, with a warning,
    for string-array items as well.
    """
    wfunc = TestWarnFunc()
    xml2po(read_xml(StringIO('''
              <resources><string-array name="test">
                  <item>foo: \k</item>
              </string-array></resources>'''), warnfunc=wfunc))
    assert len(wfunc.logs) == 1
    assert 'unsupported escape' in wfunc.logs[0]

########NEW FILE########
__FILENAME__ = test_text
# coding: utf8
"""Test the actual conversion of the text inside an Android xml file
and a gettext .po file; since the rules of both formats differ, the
actual characters/bytes of each version will differ, while still
representing the same localizable message.

Tests in here ensure that this conversation happens correctly; that is,
as closely to the way Android itself processes it's format as possible,
without modifying a string (in terms of significant content).

This currently follows the behavior I was seeing on an emulator running
the Android 1.6 SDK release, with an application compiled against the
2.0 SDK release.
"""

from __future__ import absolute_import

import re
from StringIO import StringIO
from lxml import etree
from babel.messages import Catalog
from nose.tools import assert_raises
from android2po import xml2po, po2xml, read_xml, write_xml
from ..helpers import TestWarnFunc


class TestFromXML():
    """Test reading from Android's XML format.
    """

    @classmethod
    def assert_convert(cls, xml, po=None, namespaces={}, warnfunc=None):
        """Helper that passes the string in ``xml`` through our xml
        parsing mechanism, and checks the resulting po catalog string
        against ``po``.

        If ``po`` is not given, we check against ``xml`` instead, i.e.
        expect the string to remain unchanged.
        """
        key = 'test'
        extra = {}
        warnfunc = warnfunc or TestWarnFunc()
        xmltree = read_xml(StringIO(
            '<resources %s><string name="%s">%s</string></resources>' % (
                " ".join(['xmlns:%s="%s"' % (name, url)
                          for name, url in namespaces.items()]),
                key, xml)), warnfunc=warnfunc)
        catalog = xml2po(xmltree, warnfunc=warnfunc)
        match = po if po is not None else xml
        for message in catalog:
            if message.context == key:
                #print "'%s' == '%s'" % (message.id, match)
                print repr(match), '==', repr(message.id)
                assert message.id == match
                break
        else:
            raise KeyError(warnfunc.logs)

    @classmethod
    def assert_convert_error(cls, xml, error_match):
        """Ensure that the given xml resource string cannot be processed and
        results in the given error.
        """
        wfunc = TestWarnFunc()
        key = 'test'
        catalog = xml2po(read_xml(
            StringIO('<resources><string name="%s">%s</string></resources>' % (
                key, xml)), warnfunc=wfunc))
        assert not catalog.get(xml, context=key)
        for line in wfunc.logs:
            if error_match in line:
                return
        assert False, "error output not matched"

    def test_helpers_negative(self):
        """Ensure that the helper functions we use (self.assert_*) work
        by calling them in a way in which they should fail.
        """
        assert_raises(AssertionError, self.assert_convert_error, r'good', '')
        assert_raises(AssertionError, self.assert_convert_error, r'',
                      'will not be found 12345')

    def test_basic(self):
        """Test some basic string variations.
        """
        # No nested tags.
        self.assert_convert('bar')
        # Nested tags only.
        self.assert_convert('<b>world</b>')
        # [bug] Trailing text + nested tags.
        self.assert_convert('hello <b>world</b>')
        # Multiple levels of nesting.
        self.assert_convert('<b><u>hello</u> world</b>')

    def test_tags_and_attributes(self):
        """Test certain XML-inherited syntax elements, in particular,
        that attributes of nested tags are rendered properly.

        I haven't actually tested if Android even supports them, but
        there should be no damage from our side in persisting them.
        If they, say, aren't allowed, the developer will have to deal
        with it anyway.
        """
        self.assert_convert('<b name="">foo</b>')
        # Order is persisted.
        self.assert_convert('<b k1="1" k2="2" k3="3">foo</b>')
        # Quotes are normalized.
        self.assert_convert('<b k2=\'2\'>foo</b>', '<b k2="2">foo</b>')

        # Since we can't know whether a tag was self-closing, such
        # tags are going to be expanded when going through us.
        self.assert_convert('<b />', '<b></b>')

    def test_namespaces(self):
        """Some AOSP projects like to include xliff tags to annotate
        strings with more information for translators.
        """

        # Test namespaces that we know about; thos can be put into the
        # .po file without a xmlns attribute; the downside is that we
        # must enforce a certain prefix, and can't just use whatever the
        # user defined.
        self.assert_convert('Shortcut <foo:g id="name" example="Browser">%s</foo:g> already exists',
                            'Shortcut <xliff:g id="name" example="Browser">%s</xliff:g> already exists',
                            namespaces={'foo': 'urn:oasis:names:tc:xliff:document:1.2'})

        # Test with an unknown namespace. We must ensure that the namespace
        # url is added to the tag we write to the .po file, or we won't be
        # able to properly generate the namespace back when importing (since
        # we have no other place to store the namespace url).
        self.assert_convert('Shortcut <my:g>%s</my:g> already exists',
                            'Shortcut <my:g xmlns:my="urn:custom">%s</my:g> already exists',
                            namespaces={'my': 'urn:custom'})

    def test_whitespace(self):
        """Test various whitespace handling scenarios.
        """
        # Intermediate whitespace is collapsed.
        self.assert_convert('a      b       c', 'a b c')
        # Leading and trailing whitespace is removed completely only
        # if no tags are nested.
        self.assert_convert('    a  ', 'a')
        # If there are nested tags, normal whitespace collapsing rules
        # apply at the beginning and end of the string instead.
        self.assert_convert('    <b></b>  ', ' <b></b> ')
        # Whitespace collapsing does not reach beyond a nested tag, i.e.
        # each text between two tags manages it's whitespace independently.
        self.assert_convert('   <b>   <u>    </u>  </b>  ', ' <b> <u> </u> </b> ')

        # Newlines and even tabs are considered whitespace as well.
        self.assert_convert('a    \n\n   \n   \n\n  b', 'a b')
        self.assert_convert('a  \t\t   \t  b', 'a b')
        # [bug] Edge case in which a non-significant newline/tab used to
        # end up in the output (when the last whitespace character was
        # such a newline or tab (or other whitespace other than 'space').
        self.assert_convert('a\n\n\nb', 'a b')
        self.assert_convert('a\t\t\tb', 'a b')
        # [bug] This is a related edge case: A single non-significant
        # newline or tab must not be maintained as an actual newline/tab,
        # but as a space.
        self.assert_convert('\n<b></b>', ' <b></b>')

        # An all whitespace string isn't even included.
        assert_raises(KeyError, self.assert_convert, '   ', '')

        # Quoting protects whitespace.
        self.assert_convert('"    a     b    "', '    a     b    ')

    def test_escaping(self):
        """Test escaping.
        """
        self.assert_convert(r'new\nline',  'new\nline')
        self.assert_convert(r'foo:\tbar',  'foo:\tbar')
        self.assert_convert(r'my name is \"earl\"',  'my name is "earl"')
        self.assert_convert(r'my name is \'earl\'',  'my name is \'earl\'')
        self.assert_convert(r'\\',  '\\')

        # Test a practical case of a double-backslash protecting an
        # escape sequence.
        self.assert_convert(r'\\n',  r'\n')

        # XXX: Android seems to even normalize inserted newlines:
        #    r'\n\n\n\n\n' (as a literal string) ends up as ''
        #    r'a\n\n\n\n\n' (as a literal string) ends up as 'a'
        #    r'a\n\n\n\n\nb' (as a literal string) ends up as 'a\nb'
        # It doesn't do the same for tabs:
        #    r'a\t\t\t\tb' has the tabs included
        # Actually! This only seems to be the case when you output the
        # string using the log; setting it to the caption of a textview,
        # for example, keeps the multiple linebreaks.

        # @ is used to reference other resources, but if it's escaped,
        # we want a raw @ instead. Note that for this to work well,
        # we need to make sure we don't include unescaped @-resource
        # reference at all in the gettext catalogs.
        self.assert_convert(r'\@string/app_name', '@string/app_name')
        self.assert_convert(r'foo \@test bar', 'foo @test bar')

        # A double slash can be used to protect escapes.
        self.assert_convert(r'new\\nline',  'new\\nline')

        # Edge case of having a backslash as the last char; Android
        # handles this as expected (removes it), and we also handle it
        # as expected from us: We keep it unchanged.
        # [bug] Used to throw an exception.
        self.assert_convert('edge-case\\')

    def test_unicode_sequences(self):
        """Test unicode escape codes.
        """
        # The simple cases.
        self.assert_convert(r'\u2022',  u'•')
        self.assert_convert(r'\u21F6',  u'⇶')    # uppercase hex
        self.assert_convert(r'\u21f6',  u'⇶')    # lowercase hex
        self.assert_convert(r'\u21f65',  u'⇶5')

        # The error cases.
        self.assert_convert_error(r'\uzzzz', 'bad unicode')
        self.assert_convert_error(r'\u fin',  'bad unicode')
        self.assert_convert_error(r'\u12 fin',  'bad unicode')
        self.assert_convert_error(r'\uzzzz foo',  'bad unicode')
        # Special cases due to how Python's int() works - it ignores
        # trailing or leading whitespace, which can cause incorrect
        # sequences to be converted nontheless.
        self.assert_convert_error(r'\u     |', 'bad unicode')
        self.assert_convert_error(r'\u  11', 'bad unicode')
        self.assert_convert_error(r'\u11   |', 'bad unicode')
        self.assert_convert_error(r'\u11 |', 'bad unicode')
        self.assert_convert_error(r'\u11\t\t', 'bad unicode')

        # Of course, this wouldln't be the Android resource format
        # if there weren't again special rules about how this works
        # when we are at the end of a string; incomplete sequences
        # are allowed here, with the missing digets assumed to be
        # zero (big-endian).
        self.assert_convert(r'\u219',  u'ș')
        self.assert_convert(r'\u21',  u'!')
        # Different from other special cases, a trailing whitespace
        # is not allowed here though.
        # XXX Making this work right: It's not entirely straightforward
        # due to the string being trimmed before the unicode unescaping
        # code get's it's hands on it.
        #self.assert_convert_error(r'\u21 ',  'bad unicode')


    def test_unknown_escapes(self):
        """Test an unknown escape sequence is removed.
        """
        wfunc = TestWarnFunc()
        self.assert_convert(r'foo:\kbar',  'foo:bar', warnfunc=wfunc)
        assert len(wfunc.logs) == 1
        assert 'unsupported escape' in wfunc.logs[0]

    def test_quoting(self):
        """Android allows quoting using a "..." syntax.
        """
        # With multiple quote-blocks: whitespace is preserved within
        # the blocks, collapsed outside of them.
        self.assert_convert('   a"    c"   d  ', 'a    c d')
        # Test the special case of unbalanced quotes, which seems to
        # cause whitespace protection ONLY until the last block till
        # the end of the string, which *is* collapsed. Of course, in
        # this case we could assume that the standard tail trimming
        # is responsible for that phenomenon...
        self.assert_convert('"   a   b   ', '   a   b')
        # ...however, we are seeing the same thing when using nested
        # tags. Quoting cannot span across tag boundaries, and if you
        # try and thus have unbalanced quotes, you are still seeing
        # the strange behavior of the trailing whitespace not being
        # protected.
        self.assert_convert('"   a    b   <b></b>', '   a    b <b></b>')

        # Quoting also protects other kinds of whitespace.
        self.assert_convert('"   \n\t\t   \n\n "', '   \n\t\t   \n\n ')

        # Test an apostrophe inside quotes; we don't care much though,
        # we don't try to recreate Android's stricter error handling.
        # Instead, we just let it through in either case.
        self.assert_convert('"\'"', '\'')       # standalone   '
        self.assert_convert('"\\\'"', '\'')     # escaped:     \'

        # Quoting also works with the &quot; entity
        self.assert_convert('&quot;    &quot;', '    ')

    def test_entitites(self):
        """Test that various kinds of XML entities are correctly transcoded.
        """
        # Standard entities are decoded for the .po file.
        self.assert_convert('FAQ &amp; Help', 'FAQ & Help')
        self.assert_convert('Let&apos;s go!', 'Let\'s go!')
        self.assert_convert('A &#126; B', 'A ~ B')

        # An exception are &lt; and &gt; because we need to be able to
        # differentiate between actual nested tags in the XML and encoded
        # tags when converting back, those entities need to be persisted.
        self.assert_convert('&lt;b&gt;bold&lt;/b&gt;')

    def test_strange_escaping(self):
        """TODO: There is a somewhat strange phenomenon in the Android
        parser that we don't handle yet.
           (1)  'a            '   yields   'a'    but
           (2)  'a  \ '           yields   'a '   and
           (3)  'a   \z   '       yields   'a '.
           (4)  'a \ \ \ \ '      yields   'a'
        (2) and (3) would look like a \-sequence counting as a break for
        whitespace collapsing, but (4) doesn't fit into this explanation.
        """
        pass

    def test_whitespace_collapsing(self):
        """[Regression] There used to be a bug with whitespace collapsing
        deleting to many characters, in such a way that it only  became
        apparent  when escape sequences became involved that could then
        subsequently not be treated properly.
        """
        self.assert_convert('''a    \\n''', 'a \n')
        self.assert_convert('''\\n \\n''', '\n \n')


class TestToXML():
    """Test writing to Android XML files.
    """

    @classmethod
    def assert_convert(cls, po, xml=None, namespaces={}):
        """Helper that passes the string in ``po`` through our po
        to xml converter, and checks the resulting xml string value
        against ``xml``.

        If ``xml`` is not given, we check against ``po`` instead, i.e.
        expect the string to remain unchanged.
        """
        key = 'test'
        catalog = Catalog()
        catalog.add(po, po, context=key)
        warnfunc = TestWarnFunc()
        dom = write_xml(po2xml(catalog, warnfunc=warnfunc), warnfunc=warnfunc)
        elem = dom.xpath('/resources/string[@name="%s"]' % key)[0]
        elem_as_text = etree.tostring(elem, encoding=unicode)
        value = re.match("^[^>]+>(.*)<[^<]+$", elem_as_text).groups(1)[0]
        match = xml if xml is not None else po
        print "'%s' == '%s'" % (value, match)
        print repr(value), '==', repr(match)
        assert value == match

        # If ``namespaces`` are set, the test expects those to be defined
        # in the root of the document
        for prefix, uri in namespaces.items():
            assert dom.nsmap[prefix] == uri

        # In this case, the reverse (converting back to po) always needs to
        # give us the original again, so this allows for a nice extra check.
        if not match:    # Skip this if we are doing a special, custom match.
            TestFromXML.assert_convert(match, po, namespaces)

        return warnfunc

    def test_basic(self):
        """Test some basic string variations.
        """
        # No nested tags.
        self.assert_convert('bar')
        # Nested tags.
        self.assert_convert('<b>foo</b>')
        # Multiple levels of nesting.
        self.assert_convert('<b><u>foo</u>bar</b>')

    def test_whitespace(self):
        """Test whitespace from the .po file is properly quoted within
        the xml file.
        """
        # In the default case, we can copy the input 1:1
        self.assert_convert('hello world')
        # However, if the input contains consecutive whitespace that would
        # be collapsed, we simply escape the whole thing.
        self.assert_convert('hello     world', '"hello     world"')
        self.assert_convert(' before and after ', '" before and after "')

        # If nested tags are used, the quoting needs to happen separately
        # for each block.
        self.assert_convert('   <b>inside</b>  ', '"   "<b>inside</b>"  "')
        self.assert_convert('<b>  inside  </b>bcd', '<b>"  inside  "</b>bcd')
        # As we know, if there are no need tags, leading and trailing
        # whitespace is trimmed fully. We thus need to protect it even if
        # there is just a single space. We currently handle this very roughly,
        # be just quoting any such whitespace, even if it's not strictly
        # necessary. TODO: This could be improved!
        self.assert_convert(' a ', '" a "')
        self.assert_convert('<b>hello</b> world', '<b>hello</b>" world"')

        # Note newlines and tabs here; while they are considered collapsible
        # inside Android's XML format, we only put significant whitespace
        # our .po files. Ergo, when importing, multiple newlines (or tabs)
        # will either need to be quoted, or escaped. We chose the latter.
        self.assert_convert('a \n\n\n b \t\t\t c', 'a \\n\\n\\n b \\t\\t\\t c')

    def test_namespaces(self):
        """Some AOSP projects like to include xliff tags to annotate
        strings with more information for translators.
        """

        # Test a namespace prefix that is know to us. Such prefixes may
        # be used in the .po file (and generated by us for .po files),
        # without the need to define that prefix via an xmlns attribute
        # on the tag in question itself.
        #
        # Usage of such a prefix in any string causes the prefix/namespaces
        # to be defined at the root-level.
        self.assert_convert('Shortcut <xliff:g id="name" example="Browser">%s</xliff:g> already exists',
                            '"Shortcut "<xliff:g id="name" example="Browser">%s</xliff:g>" already exists"',
                            namespaces={'xliff': 'urn:oasis:names:tc:xliff:document:1.2'})

        # Test with an unknown namespace. We don't really do anything
        # special here, we just require that the prefix be defined directly
        # on the tag in question.
        self.assert_convert('A <my:g xmlns:my="urn:custom">%s</my:g> B',
                            '"A "<my:g xmlns:my="urn:custom">%s</my:g>" B"')

    def test_entities(self):
        """Test entity conversion when putting stuff into XML.
        """
        # A raw amp is properly encoded.
        self.assert_convert('FAQ & Help', 'FAQ &amp; Help')
        # Encoded tags are maintained literally, are not further escaped.
        self.assert_convert('&lt;b&gt;bold&lt;/b&gt;', '&lt;b&gt;bold&lt;/b&gt;')

        # apos and quot are not using the entity, but the raw character;
        # although both need to be escaped, of course, see the
        # separate testing we do for that.
        self.assert_convert("'", "\\'")
        self.assert_convert('"', '\\"')

    def test_escaping(self):
        # Quotes are escaped.
        self.assert_convert('Let\'s go', 'Let\\\'s go')
        self.assert_convert('Pete "the horn" McCraw', 'Pete \\"the horn\\" McCraw')
        # The apos is even escaped when quoting is already applied. This
        # is not strictly necessary, but doesn't hurt and is easier for us.
        # Patches to improve that behavior are welcome, of course.
        self.assert_convert('   \'   ', '"   \\\'   "')

        # Newlines and tabs are replaced by their escape sequences;
        # whitespace we always consider significant in .po, so multiple
        # newlines/tabs are not collapsed.
        self.assert_convert('line1\n\n\nline3', 'line1\\n\\n\\nline3')
        self.assert_convert('line1\t\t\tline3', 'line1\\t\\t\\tline3')

        # Also, backslash are escaped into double backslashes.
        self.assert_convert('\\', r'\\')

        # @ is used to reference other resources and needs to be escaped.
        self.assert_convert('@string/app_name', r'\@string/app_name')
        self.assert_convert('foo @test bar', r'foo \@test bar')

        # Test a practical case of a double backslash used to protect
        # what would otherwise be considered a escape sequence.
        self.assert_convert('\\n', r'\\n')

        # Unicode escape sequences get converted to the actual unicode
        # character on export (see issue #6), but there is not good way
        # for us to decide which characters we should escape on import.
        # Fortunately, the resource files are unicode, so it's ok if we
        # place the actual codepoint there.
        self.assert_convert(u'•', u'•')

    def test_invalid_xhtml(self):
        """The .po contains invalid XHTML."""
        wfunc = self.assert_convert('<b>foo</b', xml='<b>foo</b>')
        assert 'contains invalid XHTML' in wfunc.logs[0]

########NEW FILE########
__FILENAME__ = helpers
import os, sys
from os.path import join, dirname, exists
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
import tempfile
import shutil
from lxml import etree

from babel.messages import pofile
from android2po import program as a2po
from android2po.convert import read_xml, write_xml


__all__ = ('ProgramTest', 'TempProject', 'TestWarnFunc',
           'SystemExitCaught', 'NonZeroReturned',)



class SystemExitCaught(Exception):
    pass


class NonZeroReturned(Exception):
    pass


def mkfile(path, content=''):
    f = open(path, 'w')
    f.write(content)
    f.flush()
    f.close()


class TestWarnFunc(object):
    """Object that can be passed to the ``warnfunc`` paramter of
    for example xml2po(), and collects the warnings so we
    can test whether they are in fact generated.
    """
    def __init__(self):
        self.logs = []
    def __call__(self, msg, severity):
        print msg
        self.logs.append(msg)


class Tee(object):
    """Return a stdout-compatible object that will pipe data written
    into it to all of the file-objects in ``args``."""

    def __init__(self, *args):
        self.args = args

    def write(self, data):
        for f in self.args:
            f.write(data)


class TempProject(object):
    """Represents a dummy-Android project in a temporary directory that
    we can run our command line tool on.
    """

    def __init__(self, manifest=True, resource_dir='res', locale_dir='locale',
                 config=None, default_xml={}, xml_langs=[]):
        self.dir = dir = tempfile.mkdtemp()
        self.locale_dir = self.p(locale_dir)
        self.resource_dir = self.p(resource_dir)

        if manifest:
            mkfile(self.p('AndroidManifest.xml'))
        if config is not None:
            self.write_config(config)

        os.mkdir(self.locale_dir)
        os.mkdir(self.resource_dir)
        if default_xml not in (False, None):
            self.write_xml(default_xml)
        # Language-XML files that should be created by default
        for code in xml_langs:
            self.write_xml(lang=code)

    def __del__(self):
        self.delete()

    def delete(self):
        """Delete all the files of this temporary project.
        """
        if os.path.exists(self.dir):
            shutil.rmtree(self.dir)

    def p(self, *w):
        """Join a path relative to the project directory.
        """
        return join(self.dir, *w)

    def write_config(self, config):
        """Write a configuration file.
        """
        if isinstance(config, (list, tuple)):
            config = "\n".join(config)
        mkfile(self.p('.android2po'), config)

    def write_xml(self, data={}, lang=None, kind='strings'):
        if isinstance(data, basestring):
            content = data
        else:
            content = etree.tostring(write_xml(data))

        folder = 'values'
        if lang:
            folder = "%s-%s" % (folder, lang)
        filename = self.p(self.resource_dir, folder, '%s.xml' % kind)
        if not exists(dirname(filename)):
            os.makedirs(dirname(filename))
        mkfile(filename, content)

    def write_po(self, catalog, filename=None):
        if not filename:
            filename = '%s.po' % catalog.locale
        file = open(join(self.locale_dir, '%s' % filename), 'wb')
        try:
            return pofile.write_po(file, catalog)
        finally:
            file.close()

    def program(self, command=None, kwargs={}, expect=None):
        """Run android2po in this project's working directory.

        Return the program output.
        """
        args = ['a2po-test']
        if command:
            args.append(command)
        for k, v in kwargs.iteritems():
            if v is True or not v:
                args.append(k)
            else:
                if not isinstance(v, (list, tuple)):
                    # A tuple may be used to pass the same argument multiple
                    # times with different values.
                    v = [v]
                for w in v:
                    if isinstance(w, (list, tuple)):
                        # This is starting to get messy, but this allows the
                        # caller to generate "--arg val1 val2" by passing as
                        # the dict: {'arg': [['val1', 'val2']]}
                        args.append('%s' % k)
                        args.extend(w)
                    else:
                        # Otherwise, we set a single value, and we use "=",
                        # so that arguments that are defined as nargs='+'
                        # will not capture more than the value "w".
                        args.append("%s=%s" % (k, w))

        old_cwd = os.getcwd()
        os.chdir(self.dir)
        # Sometimes we might want to check a certain message was printed
        # out, so in addition to having nose capture the output, we
        # want to as well.
        old_stdout = sys.stdout
        stdout_capture = StringIO.StringIO()
        sys.stdout = Tee(sys.stdout, stdout_capture)
        # argparse likes to write to stderr, let it be handled like
        # normal stdout (i.e. captured by nose as well as us).
        old_stderr = sys.stderr
        sys.stderr = sys.stdout
        try:
            try:
                print "Running: %s" % " ".join(args)
                ret = a2po.main(args)
            except SystemExit, e:
                # argparse likes to raise this if arguments are invalid.
                raise SystemExitCaught('SystemExit raised by program: %s', e)
            else:
                if expect is not None:
                    if ret != expect:
                        raise ValueError(
                            'Program returned code %d, expected %d' % (
                                ret, expect))
                elif ret:
                    raise NonZeroReturned('Program returned non-zero: %d', ret)
                return stdout_capture.getvalue()
        finally:
            os.chdir(old_cwd)
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def get_po(self, filename):
        file = open(join(self.locale_dir, '%s' % filename), 'rb')
        try:
            return pofile.read_po(file)
        finally:
            file.close()

    def get_xml(self, lang=None, kind='strings', raw=False):
        dirname = 'values'
        if lang:
            dirname = "%s-%s" % (dirname, lang)
        filename = self.p(self.resource_dir, dirname, '%s.xml' % kind)
        if raw:
            return open(filename).read()
        else:
            return read_xml(filename)


class ProgramTest(object):
    """Base-class for tests that helps with setting up dummy projects
    and having android2po run on them.
    """

    def setup_project(self, *args, **kwargs):
        """Setup a fake Android project in a temporary directory
        that we can work with.
        """
        p = TempProject(*args, **kwargs)
        self.projects.append(p)
        return p

    def setup(self):
        # Start with a fresh list of projects for the test.
        self.projects = []

    def teardown(self):
        # Clear all projects that might have been created by the test.
        for p in self.projects:
            p.delete()

########NEW FILE########
__FILENAME__ = test_commands
"""TOOD: We need to test the basic command functionality, ensuring that
at it's core, import, export and init are operative, create the files they
should create, skip the files they should skip when they should be skipped,
etc. In particular, we should test both the case of multiple XML input files
(strings.xml, arrays.xml), and the case of only single source.

"test_options" tests the commands in combination with specific options and
will thus ensure that commands run, but does not check that they do the
right thing.
"""

from nose.tools import assert_raises
from babel.messages import Catalog
from android2po.convert import StringArray
from helpers import ProgramTest


class TestExport(ProgramTest):

    def test_export_with_empty_master_xml(self):
        """[Regression] Test that export works fine if the master
        resource is empty."""
        p = self.setup_project(xml_langs=['de'])
        p.write_xml(data="""<resources></resources>""", lang='de')
        p.write_po(Catalog('de'))
        assert not '[failed]' in p.program('export')


class TestImport(ProgramTest):

    pass


class TestPlurals(ProgramTest):
    """Test plural support on the program level.

    Low-level plural tests are in convert/
    """

    def test_init(self):
        """Test that the init command generates the proper plural form."""
        p = self.setup_project()
        p.write_xml(data="""<resources></resources>""")
        p.write_xml(data="""<resources></resources>""", lang='ja')
        p.program('init')
        catalog = p.get_po('ja.po')
        assert catalog.num_plurals == 1
        assert catalog.plural_expr == '(0)'

    def test_export(self):
        """Test that the export command maintains the proper plural form,
        and actually replaces an incorrect one."""
        p = self.setup_project()
        p.write_xml(data="""<resources></resources>""")
        p.write_xml(data="""<resources></resources>""", lang='ja')

        # Generate a catalog with different plural rules than we expect
        catalog = Catalog('ja')
        catalog._num_plurals, catalog._plural_expr = 2, '(n < 2)'
        p.write_po(catalog)

        # Export should override the info
        assert 'Plural-Forms header' in p.program('export')
        catalog = p.get_po('ja.po')
        assert catalog.num_plurals == 1
        assert catalog.plural_expr == '(0)'


class TestDealWithBrokenInput(ProgramTest):
    """Make sure we can handle broken input.
    """

    def mkcatalog(locale='de'):
        """Helper that returns a gettext catalog with one message
        already added.

        Tests can add a broken message and then ensure that at least
        the valid message still was processed.
        """
        c = Catalog(locale='de')
        c.add('valid_message', 'valid_value', context='valid_message')
        return c

    def runprogram(self, project, command, args={}, **kw):
        """Helper to run the given command in quiet mode. The warnings
        we test for here should appear even there.
        """
        args['--quiet'] = True
        return project.program(command, args, **kw)

    def test_nocontext(self):
        """Some strings in the .po file do not have a context set.
        """
        p = self.setup_project()
        c = self.mkcatalog()
        c.add('s', 'v',)  # no context!
        p.write_po(c, 'de.po')
        assert 'no context' in self.runprogram(p, 'import', expect=1)
        assert len(p.get_xml('de')) == 1

    def test_duplicate_aray_index(self):
        """An encoded array in the .po file has the same index twice.
        """
        p = self.setup_project()
        c = self.mkcatalog()
        c.add('t1', 'v1', context='myarray:1')
        c.add('t2', 'v2', context='myarray:1')
        p.write_po(c, 'de.po')
        assert 'Duplicate index' in self.runprogram(p, 'import', expect=1)
        xml = p.get_xml('de')
        assert len(xml) == 2
        assert len(xml['myarray']) == 1

    def test_invalid_xhtml(self):
        """XHTML in .po files may be invalid; a forgiving parser will be
        used as a fallback.
        """
        p = self.setup_project()
        c = self.mkcatalog()
        c.add('s', 'I am <b>bold', context='s')
        p.write_po(c, 'de.po')
        assert 'invalid XHTML' in self.runprogram(p, 'import')
        assert p.get_xml('de')['s'].text == 'I am <b>bold</b>'

    # XXX test_duplicate_context

    def test_duplicate_resource_string(self):
        """A resource XML file could contain a string twice.
        """
        p = self.setup_project()
        p.write_xml(data="""<resources><string name="s1">foo</string><string name="s1">bar</string></resources>""")
        assert 'Duplicate resource' in self.runprogram(p, 'init')
        assert len(p.get_po('template.pot')) == 1

    def test_empty_stringarray(self):
        """A warning is shown if a string array is empty.
        """
        p = self.setup_project()
        p.write_xml(data={'s1': StringArray([])})
        assert 'is empty' in self.runprogram(p, 'init')
        assert len(p.get_po('template.pot')) == 0

    def test_type_mismatch(self):
        """A resource name is string-array in the reference file, but a
        normal string in the translation.
        """
        p = self.setup_project(xml_langs=['de'])
        p.write_xml(data={'s1': StringArray(['value'])})
        p.write_xml(data={'s1': 'value'}, lang='de')
        assert 'string-array in the reference' in self.runprogram(p, 'init')
        assert len(p.get_po('template.pot')) == 1

    def test_invalid_resource_xml(self):
        """Resource xml files are so broken we can't parse them.
        """
        # Invalid language resource
        p = self.setup_project(xml_langs=['de'])
        p.write_xml(data="""<resources><string name="s1"> ...""", lang='de')
        assert 'Failed parsing' in self.runprogram(p, 'init', expect=1)
        assert_raises(IOError, p.get_po, 'de.po')

        # Invalid default resource
        p = self.setup_project()
        p.write_xml(data="""<resources><string name="s1"> ...""")
        assert 'Failed parsing' in self.runprogram(p, 'init', expect=1)
        assert_raises(IOError, p.get_po, 'template.pot')

########NEW FILE########
__FILENAME__ = test_config
"""Test reading and parsing the configuration file.
"""

from StringIO import StringIO
from nose.tools import assert_raises
from android2po.program import read_config, CommandError


def test_valid_args():
    c = read_config(StringIO('--gettext xyz\n--android foo'))
    assert c.gettext_dir == 'xyz'
    assert c.resource_dir == 'foo'


def test_invalid_args():
    assert_raises(CommandError, read_config, StringIO('--gettext xyz\n--verbose'))


def test_comments():
    c = read_config(StringIO('''
# This is a comment
--gettext xyz
   # This is a comment with whitespace upfront
'''))
    assert c.gettext_dir == 'xyz'


def test_whitespace():
    """Whitespace in front of lines or at the end is ignored.
    """
    c = read_config(StringIO('''   --gettext xyz  '''))
    assert c.gettext_dir == 'xyz'


def test_path_rebase():
    """Paths in the config file are made relative to their location.
    """
    file = StringIO('''--gettext ../gettext\n--android ../res''')
    file.name = '/opt/proj/android/shared/.config'
    c = read_config(file)
    print c.gettext_dir
    assert c.gettext_dir == '/opt/proj/android/gettext'
    assert c.resource_dir == '/opt/proj/android/res'
########NEW FILE########
__FILENAME__ = test_environment
"""TODO: Test basic environment handling (ensuring the correct config file
is used in the correct circumstances, the project directory is automatically
detected, the proper directories assumed etc).
"""

from tests.helpers import ProgramTest, NonZeroReturned
from nose.tools import assert_raises


class TestCollect(ProgramTest):
    """Make sure we support any XML resource file, including non-standard
    names besides strings.xml, arrays.xml etc.
    """

    def test(self):
        p = self.setup_project(default_xml=False)
        p.write_xml(kind='strings')
        p.write_xml(kind='arrays')
        p.write_xml(kind='file-with-strings', data={'foo': 'bar'})
        p.write_xml(kind='empty-file')
        p.write_xml(kind='file-with-other-stuff',
                    data="""<resources><color name="white">#ffffffff</color></resources>""")
        p.program('init')

        # It's important that we only load files which actually contain
        # translatable strings, and ignore files which only have other
        # resources.
        p.get_po('file-with-strings.pot')
        assert_raises(IOError, p.get_po, 'empty-file.pot')
        assert_raises(IOError, p.get_po, 'file-with-other-stuff.pot')
        # Those are special, and will always be included.
        p.get_po('strings.pot')
        p.get_po('arrays.pot')

    def test_error(self):
        """If any of the default XML files has an error.
        """
        p = self.setup_project(default_xml=False)
        p.write_xml(kind='broken-file',  data="""not really xml""")
        assert_raises(NonZeroReturned, p.program, 'init')


class TestConfig(ProgramTest):

    def test_with_option(self):
        """Regression test: Make sure we can deal with config files that
        have values.
        """
        p = self.setup_project(config="")
        # This used to raise an AssertionError.
        p.program('init')
########NEW FILE########
__FILENAME__ = test_options
"""Tests for each of the various configuration options.
"""

from nose.tools import assert_raises
from tests.helpers import ProgramTest, SystemExitCaught, NonZeroReturned
from babel.messages import Catalog


class TestNoTemplate(ProgramTest):
    """Template pot file can be disabled.
    """

    def test(self):
        # By default, a template file is created.
        p1 = self.setup_project()
        p1.program('export')
        p1.get_po('template.pot')

        # With the right option, we don't see one.
        p2 = self.setup_project()
        p2.program('export', {'--no-template': True})
        assert_raises(IOError, p2.get_po, 'template.pot')


class TestTemplateName(ProgramTest):

    def test_default(self):
        """The default template name without any options.
        """
        p = self.setup_project()
        p.program('export')
        p.get_po('template.pot')

    def test_default_with_domain(self):
        """The default template name if a --domain is configured.
        """
        p = self.setup_project()
        p.program('export', {'--domain': 'foo'})
        p.get_po('foo.pot')

    def test_default_with_group(self):
        """The default template name if multiple xml kinds are used.
        """
        p = self.setup_project()
        p.write_xml(kind='strings')
        p.write_xml(kind='arrays')
        p.program('export')
        p.get_po('strings.pot')
        p.get_po('arrays.pot')

    def test_default_with_groups_and_domain(self):
        """The default template name if both multiple xml kinds and
        the --domain option are used.
        """
        p = self.setup_project()
        p.write_xml(kind='strings')
        p.write_xml(kind='arrays')
        p.program('export', {'--domain': 'foo'})
        p.get_po('foo-strings.pot')
        p.get_po('foo-arrays.pot')

    def test_custom(self):
        """A custom template name can be given.
        """
        p = self.setup_project()
        p.program('export', {'--template': 'foobar1234.pot'})
        p.get_po('foobar1234.pot')

    def test_custom_requires_groups(self):
        """If multiple XML kinds are used, then a custom template name,
        if configured, MUST contain a placeholder for the group.
        """
        p = self.setup_project()
        p.write_xml(kind='strings')
        p.write_xml(kind='arrays')
        assert_raises(NonZeroReturned,
                      p.program, 'export', {'--template': 'mylocation.po'})
        p.program('export', {'--template': '%(group)s.pot'})

    def test_custom_does_NOT_require_domain(self):
        """However, even if a --domain is configured, the template name
        is not required to contain a placeholder for the domain. This
        behavior differs from --layout, where the placeholder then would
        indeed be required.
        """
        p = self.setup_project()
        p.program('export', {'--domain': 'foo', '--template': 'foo.pot'})

    def test_old_var_compatibility(self):
        """Used to be that we only supported %s for the group. This is
        still supported.
        """
        p = self.setup_project()
        p.program('export', {'--template': 'foobar-%s-1234.pot'})
        p.get_po('foobar-strings-1234.pot')


class TestIgnores(ProgramTest):

    def test_init(self):
        """Test that ignores work during 'init'.
        """
        p = self.setup_project(default_xml={'app_name': 'Foo', 'nomatch': 'bar'})
        p.program('init', {'de': '', '--ignore': 'app_name'})
        po = p.get_po('de.po')
        assert po._messages.values()[0].id == 'bar'   # at least once bother to check the actual content
        assert len(p.get_po('template.pot')) == 1

    def test_export(self):
        """Test that ignores work during 'export'.
        """
        p = self.setup_project(default_xml={'app_name': 'Foo', 'nomatch': 'bar'})
        p.program('init', {'de': '', '--ignore': 'app_name'})
        assert len(p.get_po('de.po')) == 1
        assert len(p.get_po('template.pot')) == 1

    def test_regex(self):
        """Test support for regular expressions.
        """
        p = self.setup_project(default_xml={'pref_x': '123', 'nomatch': 'bar'})
        p.program('init', {'de': '', '--ignore': '/^pref_/'})
        assert len(p.get_po('de.po')) == 1

    def test_no_partials(self):
        """Test that non-regex ignores do not match partially.
        """
        p = self.setup_project(default_xml={'pref_x': '123', 'nomatch': 'bar'})
        p.program('init', {'de': '', '--ignore': 'pref'})
        assert len(p.get_po('de.po')) == 2

    def test_multiple(self):
        """Test that multiple ignores work fine.
        """
        p = self.setup_project(default_xml={'pref_x': '123', 'app_name': 'Foo'})
        p.program('init', {'de': '', '--ignore': ('app_name', '/pref/')})
        assert len(p.get_po('de.po')) == 0


class TestIgnoreFuzzy(ProgramTest):
    """Test the --ignore-fuzzy option.
    """

    def test(self):
        p = self.setup_project()
        c = Catalog(locale='de')
        c.add('en1', 'de1', flags=('fuzzy',), context='foo')
        c.add('en2', 'de2', context='bar')
        p.write_po(c, 'de.po')
        p.program('import', {'--ignore-fuzzy': True})
        xml = p.get_xml('de')
        assert not 'foo' in xml
        assert 'bar' in xml


class TestIgnoreMinComplete(ProgramTest):
    """Test the --ignore-min-complete option.
    """

    def test(self):
        p = self.setup_project()

        c = Catalog(locale='de')
        c.add('translated', 'value', context='translated')
        c.add('missing1', context='missing1')
        c.add('missing2', context='missing2')
        c.add('missing3', context='missing3')
        p.write_po(c, 'de.po')

        # At first, we require half the strings to be available.
        # This is clearly not the case in the catalog above.
        p.program('import', {'--require-min-complete': '0.5'})
        assert len(p.get_xml('de')) == 0

        # Now, only require 25% - this should just make the cut.
        p.program('import', {'--require-min-complete': '0.25'})
        assert len(p.get_xml('de')) == 1

    def test_fuzzy(self):
        """This option is affected by the --ignore-fuzzy flag. If
        it is set, fuzzy strings are not counted towards the total.
        """
        p = self.setup_project()

        c = Catalog(locale='de')
        c.add('translated', 'value', context='translated')
        c.add('fuzzy', 'value', context='fuzzy', flags=('fuzzy',))
        p.write_po(c, 'de.po')

        # When fuzzy strings are counted, the catalog above is 100%
        # complete.
        p.program('import', {'--require-min-complete': '1'})
        assert len(p.get_xml('de')) == 2

        # If they aren't, it won't make the cut and the result should
        # be no strings at all being written.
        p.program('import', {'--require-min-complete': '1',
                             '--ignore-fuzzy': True})
        assert len(p.get_xml('de')) == 0

    def test_multiple_pos(self):
        """If the language writes to multiple .po files, those are
        all counted together. Either all of them will be written,
        or none of them will be.
        """
        p = self.setup_project()
        p.write_xml(kind='strings')
        p.write_xml(kind='arrays')

        # Create two catalogs, one fully translated, the other one not
        # at all.
        c = Catalog(locale='de')
        c.add('translated', 'value', context='translated')
        p.write_po(c, 'strings-de.po')

        c = Catalog(locale='de')
        c.add('untranslated', context='untranslated')
        p.write_po(c, 'arrays-de.po')

        # If we require 100% completness on import, both files will
        # be empty, even though one of them is fully translated. But
        # the second drags down the total of the group.
        p.program('import', {'--require-min-complete': '1'})
        assert len(p.get_xml('de', kind='strings')) == 0
        assert len(p.get_xml('de', kind='arrays')) == 0

    def test_clear(self):
        """Explicitely test that if we ignore a language, the xml
        file is overwritten with an empty version. Just not processing
        it is not enough.
        """
        p = self.setup_project()

        # We start out with one string in the XML
        p.write_xml({'string1': 'value1'}, lang='de')
        assert len(p.get_xml('de')) == 1

        c = Catalog(locale='de')
        c.add('string1', context='string1')
        p.write_po(c, 'de.po')

        # Now after the import, the resource file is empty.
        p.program('import', {'--require-min-complete': '1'})
        assert len(p.get_xml('de')) == 0

    def test_error(self):
        """Check that the argument is properly validated.
        """
        p = self.setup_project()
        assert_raises(SystemExitCaught, p.program, 'import', {'--require-min-complete': '3'})
        assert_raises(SystemExitCaught, p.program, 'import', {'--require-min-complete': 'asdf'})


class TestLayoutAndDomain(ProgramTest):
    """Test the --layout and --domain options.
    """

    def test_default_layout(self):
        """The default layout."""
        p = self.setup_project(xml_langs=['de'])
        p.program('init')
        p.get_po('de.po')

    def test_default_with_groups(self):
        """The default while groups are being used.
        """
        p = self.setup_project(xml_langs=['de'])
        p.write_xml({}, kind='arrays')
        p.program('init')
        p.get_po('arrays-de.po')

    def test_default_with_domain(self):
        """The default when a domain is given.
        """
        p = self.setup_project(xml_langs=['de'])
        p.program('init', {'--domain': 'a2potest'})
        p.get_po('a2potest-de.po')

    def test_default_with_groups_and_domain(self):
        """The default with both groups being used and a domain given.
        """
        p = self.setup_project(xml_langs=['de'])
        p.write_xml({}, kind='arrays')
        p.program('init', {'--domain': 'a2potest'})
        p.get_po('a2potest-arrays-de.po')

    def test_gnu(self):
        """Test --layout gnu.
        """
        p = self.setup_project(xml_langs=['de'])
        p.program('init', {'--layout': 'gnu'})
        p.get_po('de/LC_MESSAGES/android.po')

    def test_gnu_with_groups(self):
        """Test --layout gnu.
        """
        p = self.setup_project(xml_langs=['de'])
        p.write_xml({}, kind='arrays')
        p.program('init', {'--layout': 'gnu'})
        p.get_po('de/LC_MESSAGES/strings-android.po')

    def test_gnu_with_domain(self):
        """Test --layout gnu.
        """
        p = self.setup_project(xml_langs=['de'])
        p.program('init', {'--layout': 'gnu', '--domain': 'a2potest'})
        p.get_po('de/LC_MESSAGES/a2potest.po')

    def test_gnu_with_groups_and_domain(self):
        """Test --layout gnu.
        """
        p = self.setup_project(xml_langs=['de'])
        p.write_xml({}, kind='arrays')
        p.program('init', {'--layout': 'gnu', '--domain': 'a2potest'})
        p.get_po('de/LC_MESSAGES/strings-a2potest.po')

    def test_custom_requires_locale(self):
        """A custom --layout always requires a "locale" placeholder.
        """
        p = self.setup_project(xml_langs=['de'])
        assert_raises(NonZeroReturned,
                      p.program, 'init', {'--layout': 'mylocation.po'})
        p.program('init', {'--layout': '%(locale)s.po'})

    def test_custom_requires_domain_var(self):
        """A custom --layout requires a "domain" placeholder if a custom
        domain is given.

        The idea here is that there is zero purpose in specifying --domain,
        if you then do not include it in your filenames. It's essentially
        the only purpose of the option in the first place; certainly right
        now. It may change at a later point.
        """
        p = self.setup_project(xml_langs=['de'])
        assert_raises(NonZeroReturned,
                      p.program, 'init', {'--domain': 'a2potest',
                                          '--layout': '%(locale)s.po'})
        p.program('init', {'--domain': 'a2potest',
                           '--layout': '%(locale)s-%(domain)s.po'})

    def test_custom_requires_group_var(self):
        """A custom --layout requires a "group" placeholder if groups
        are being used.
        """
        p = self.setup_project(xml_langs=['de'])
        p.write_xml({}, kind='arrays')
        assert_raises(NonZeroReturned,
                      p.program, 'init', {'--layout': '%(locale)s.po'})
        p.program('init', {'--layout': '%(locale)s-%(group)s.po'})


class TestGroups(ProgramTest):
    """Test the --groups option.
    """

    def test_restrict_to_subset(self):
        """Use --groups to ignore a file which otherwise would be
        processed.
        """
        p = self.setup_project(default_xml=False)
        p.write_xml(kind='strings')
        p.write_xml(kind='arrays')
        p.program('init', {'--groups': 'strings'})
        # NOTE: Because we have only one group after the restriction,
        # the default name is "template.pot", not "strings.pot". This
        # behavior could well be different: we could opt to always
        # use the group name in the default template name as well as
        # the --groups option gets involved.
        p.get_po('template.pot')
        assert_raises(IOError, p.get_po, 'arrays.pot')

    def test_request_invalid_group(self):
        """Use --groups to refer to a group where the corresponding XML
        file doesn't actually exist.
        """
        p = self.setup_project(default_xml=False)
        p.write_xml(kind='strings')
        p.write_xml(kind='arrays')
        assert_raises(NonZeroReturned, p.program, 'init', {'--groups': 'foobar'})
        # TODO: Test the error message

    def test_request_ignored_group(self):
        """Use --groups to include a file which otherwise would be ignored.
        """
        p = self.setup_project(default_xml=False)
        p.write_xml(kind='strings')
        p.write_xml(kind='no-string-file',
                    data="""<resources><color name="white">#ffffffff</color></resources>""")
        p.program('init', {'--groups': [['strings', 'no-string-file']]})
        p.get_po('no-string-file.pot')
        p.get_po('strings.pot')
########NEW FILE########
