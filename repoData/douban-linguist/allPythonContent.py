__FILENAME__ = blob_helper
# -*- coding: utf-8 -*-

import re
import urllib
from os.path import realpath, dirname, splitext, basename, join

import yaml
import mime
import charlockholmes
from pygments import lexers
from pygments import highlight
from pygments.formatters import HtmlFormatter

from language import Language
from generated import Generated

MEGABYTE = 1024 * 1024

DIR = dirname(realpath(__file__))
VENDOR_PATH = join(DIR, "vendor.yml")
VENDORED_PATHS = yaml.load(open(VENDOR_PATH))
VENDORED_REGEXP = re.compile('|'.join(VENDORED_PATHS))


class BlobHelper(object):
    """
    DEPRECATED Avoid mixing into Blob classes. Prefer functional interfaces
    like `Language.detect` over `Blob#language`. Functions are much easier to
    cache and compose.

    Avoid adding additional bloat to this module.

    BlobHelper is a mixin for Blobish classes that respond to "name",
      "data" and "size" such as Grit::Blob.
    """

    @property
    def ext_name(self):
        """
        Public: Get the extname of the path

        Examples
          blob(name='foo.rb').extname
          # => '.rb'

        Returns a String
        """
        return splitext(self.name)[1].lower()

    @property
    def _mime_type(self):
        if hasattr(self, '__mime_type'):
            return self.__mime_type
        guesses = mime.Types.of(self.name)
        mimetypes = [mt for mt in guesses if mt.is_ascii]
        if mimetypes:
            self.__mime_type = mimetypes[0]
        elif guesses:
            self.__mime_type = guesses[0]
        else:
            self.__mime_type = None
        return self.__mime_type

    @property
    def mime_type(self):
        """
        Public: Get the actual blob mime type

        Examples

          # => 'text/plain'
          # => 'text/html'

        Returns a mime type String.
        """
        return self._mime_type.to_s if self._mime_type else 'text/plain'

    @property
    def is_binary_mime_type(self):
        """
        Internal: Is the blob binary according to its mime type

        Return true or false
        """
        return self._mime_type.is_binary if self._mime_type else False

    @property
    def is_likely_binary(self):
        """
        Internal: Is the blob binary according to its mime type,
        overriding it if we have better data from the languages.yml
        database.

        Return true or false
        """
        return self.is_binary_mime_type and not Language.find_by_filename(self.name)

    @property
    def content_type(self):
        """
        Public: Get the Content-Type header value

        This value is used when serving raw blobs.

        Examples

          # => 'text/plain; charset=utf-8'
          # => 'application/octet-stream'

        Returns a content type String.
        """
        if hasattr(self, '_content_type'):
            return self._content_type

        if self.is_binary_mime_type or self.is_binary:
            self._content_type = self.mime_type
        else:
            encoding = self.encoding
            self._content_type = "text/plain; charset=%s" % encoding.lower() if encoding else "text/plain"
        return self._content_type

    @property
    def disposition(self):
        """
        Public: Get the Content-Disposition header value

        This value is used when serving raw blobs.

          # => "attachment; filename=file.tar"
          # => "inline"

        Returns a content disposition String.
        """
        if self.is_text or self.is_image:
            return 'inline'
        elif self.name is None:
            return 'attachment'
        else:
            return 'attachment; filename=%s' % urllib.quote_plus(basename(self.name))

    @property
    def encoding(self):
        if self.detect_encoding:
            return self.detect_encoding.get('encoding')

    @property
    def detect_encoding(self):
        """
        Try to guess the encoding

        Returns: a hash, with :encoding, :confidence, :type
                 this will return nil if an error occurred during detection or
                 no valid encoding could be found
        """
        if hasattr(self, '_detect_encoding'):
            return self._detect_encoding

        if self.data:
            self._detect_encoding = charlockholmes.detect(self.data)
            return self._detect_encoding

    @property
    def is_image(self):
        """
        Public: Is the blob a supported image format?

        Return true or false
        """
        return self.ext_name in ('.png', '.jpg', '.jpeg', '.gif')

    @property
    def is_solid(self):
        """
        Public: Is the blob a support 3D model format?

        Return true or false
        """
        return self.ext_name == '.stl'

    @property
    def is_pdf(self):
        """
        Public: Is the blob a supported 3D model format?

        Return true or false
        """
        return self.ext_name == '.pdf'

    @property
    def is_csv(self):
        """
        Public: Is this blob a CSV file?

        Return true or false
        """
        return self.is_text and self.ext_name == '.csv'

    @property
    def is_text(self):
        """
        Public: Is the blob text?

        Return true or false
        """
        return not self.is_binary

    @property
    def is_binary(self):
        if self.data is None:
            # Large blobs aren't even loaded into memory
            return True
        elif self.data == "":
            # Treat blank files as text
            return False
        elif self.encoding is None:
            # Charlock doesn't know what to think
            return True
        else:
            # If Charlock says its binary
            return self.detect_encoding.get('type') == 'binary'

    @property
    def is_large(self):
        """
        Public: Is the blob too big to load?

        Return false or true
        """
        return self.size > MEGABYTE

    @property
    def loc(self):
        """
        Public: Get number of lines of code

        Requires Blob#data

        Returns Integer
        """
        return len(self.lines)

    @property
    def sloc(self):
        """
        Public: Get number of source lines of code

        Requires Blob#data

        Returns Integer
        """
        return len(filter(re.compile('\S').search, self.lines))

    @property
    def is_safe_to_colorize(self):
        """
        Public: Is the blob safe to colorize?

        We use Pygments for syntax highlighting blobs. Pygments
        can be too slow for very large blobs or for certain
        corner-case blobs.

        Return true or false
        """
        return not self.is_large and self.is_text and not self.is_high_ratio_of_long_lines

    @property
    def is_high_ratio_of_long_lines(self):
        """
        Internal: Does the blob have a ratio of long lines?
        These types of files are usually going to make Pygments.rb
        angry if we try to colorize them.

        Return true or false
        """
        if self.loc == 0:
            return False
        return self.size / self.loc > 5000

    @property
    def is_viewable(self):
        """
        Public: Is the blob viewable?

        Non-viewable blobs will just show a "View Raw" link

        Return true or false
        """
        return not self.is_large and self.is_text

    @property
    def is_vendored(self):
        """
        Public: Is the blob in a vendored directory?

        Vendored files are ignored by language statistics.

        See "vendor.yml" for a list of vendored conventions that match
        this pattern.

        Return true or false
        """
        if VENDORED_REGEXP.search(self.name):
            return True

    @property
    def lines(self):
        """
        Public: Get each line of data

        Requires Blob#data

        Returns an Array of lines
        """
        if hasattr(self, '_lines'):
            return self._lines
        if self.is_viewable and self.data:
            self._lines = re.split('\r\n|\r|\n', self.data)
        else:
            self._lines = []
        return self._lines

    @property
    def is_generated(self):
        """
        Public: Is the blob a generated file?

        Generated source code is suppressed in diffs and is ignored by
        language statistics.

        May load Blob#data

        Return true or false
        """
        if hasattr(self, '_is_generated'):
            return self._is_generated

        def _data_func():
            return self.data

        self._is_generated = Generated.is_generated(self.name, _data_func)
        return self._is_generated

    @property
    def language(self):
        """
        Public: Detects the Language of the blob.

        May load Blob#data

        Returns a Language or nil if none is detected
        """
        if hasattr(self, '_language'):
            return self._language

        _data = getattr(self, '_data', False)
        if _data and isinstance(_data, basestring):
            data = _data
        else:
            data = lambda: '' if (self.is_binary_mime_type or self.is_binary) else self.data
        self._language = Language.detect(self.name, data, self.mode)
        return self._language

    @property
    def lexer(self):
        """
        Internal: Get the lexer of the blob.

        Returns a Lexer.
        """
        return self.language.lexer if self.language else lexers.find_lexer_class('Text only')

    def colorize(self, options={}):
        """
        Public: Highlight syntax of blob

        options - A Hash of options (defaults to {})

        Returns html String
        """
        if not self.is_safe_to_colorize:
            return
        return highlight(self.data, self.lexer(), HtmlFormatter(**options))

########NEW FILE########
__FILENAME__ = classifier
# -*- coding: utf-8 -*-
import os
import sys
import math
from functools import partial

is_py27 = sys.version_info >= (2, 7)
if is_py27:
    from collections import Counter
from tokenizer import Tokenizer


class Classifier(object):
    """ Language bayesian classifier. """

    verbosity = int(os.environ.get('LINGUIST_DEBUG', '0'))

    @classmethod
    def train(cls, db, language, data):
        """
        Set LINGUIST_DEBUG=1 or =2 to see probabilities per-token,
        per-language.  See also dump_all_tokens, below.

        Public: Train classifier that data is a certain language.

          db       - Hash classifier database object
          language - String language of data
          data     - String contents of file

          Examples

            Classifier.train(db, 'Ruby', "def hello; end")

          Returns nothing.
        """
        tokens = Tokenizer.tokenize(data)
        db['tokens_total'] = db.get('tokens_total', 0)
        db['languages_total'] = db.get('languages_total', 0)
        db['tokens'] = db.get('tokens', {})
        db['language_tokens'] = db.get('language_tokens', {})
        db['languages'] = db.get('languages', {})

        for token in tokens:
            db['tokens'][language] = db['tokens'].get(language, {})
            db['tokens'][language][token] = db['tokens'][language].get(token, 0)
            db['tokens'][language][token] += 1
            db['language_tokens'][language] = db['language_tokens'].get(language, 0)
            db['language_tokens'][language] += 1
            db['tokens_total'] += 1

        db['languages'][language] = db['languages'].get(language, 0)
        db['languages'][language] += 1
        db['languages_total'] += 1

    def __init__(self, db={}):
        self.tokens = db.get('tokens')
        self.tokens_total = db.get('tokens_total')
        self.languages = db.get('languages')
        self.languages_total = db.get('languages_total')
        self.language_tokens = db.get('language_tokens')

    def __repr__(self):
        return '<Classifier>'

    @classmethod
    def classify(cls, db, tokens, languages=[]):
        """
        Public: Guess language of data.

        db        - Hash of classifer tokens database.
        data      - Array of tokens or String data to analyze.
        languages - Array of language name Strings to restrict to.

        Examples

          Classifier.classify(db, "def hello; end")
          # => [ 'Ruby', 0.90], ['Python', 0.2], ... ]

        Returns sorted Array of result pairs. Each pair contains the
        String language name and a Float score.
        """
        languages = languages or db.get('languages', {}).keys()
        return cls(db)._classify(tokens, languages)

    def _classify(self, tokens, languages):
        """
        Internal: Guess language of data

        data      - Array of tokens or String data to analyze.
        languages - Array of language name Strings to restrict to.

        Returns sorted Array of result pairs. Each pair contains the
        String language name and a Float score.
        """
        if tokens is None:
            return []

        if isinstance(tokens, basestring):
            tokens = Tokenizer.tokenize(tokens)

        scores = {}
        if self.verbosity >= 2:
            self.dump_all_tokens(tokens, languages)
        for language in languages:
            scores[language] = self.tokens_probability(tokens, language) + self.language_probability(language)
            if self.verbosity >= 1:
                print '%10s = %10.3f + %7.3f = %10.3f\n' % (language,
                                                            self.tokens_probability(tokens, language),
                                                            self.language_probability(language),
                                                            scores[language])
        return sorted(scores.iteritems(), key=lambda t: t[1], reverse=True)

    def tokens_probability(self, tokens, language):
        """
        Internal: Probably of set of tokens in a language occuring - P(D | C)

        tokens   - Array of String tokens.
        language - Language to check.

        Returns Float between 0.0 and 1.0.
        """
        token_probability = partial(self.token_probability, language=language)
        return reduce(lambda x, y: x + math.log(token_probability(y)), tokens, 0.0)

    def token_probability(self, token, language=''):
        """
        Internal: Probably of token in language occuring - P(F | C)

        token    - String token.
        language - Language to check.

        Returns Float between 0.0 and 1.0.
        """
        probability = float(self.tokens.get(language, {}).get(token, 0))
        if probability == 0.0:
            return 1 / float(self.tokens_total)
        else:
            return probability / float(self.language_tokens[language])

    def language_probability(self, language):
        """
        Internal: Probably of a language occuring - P(C)

        language - Language to check.

        Returns Float between 0.0 and 1.0.
        """
        return math.log(float(self.languages[language]) / float(self.languages_total))

    def dump_all_tokens(self, tokens, languages):
        """
        Internal: show a table of probabilities for each <token,language> pair.

        The number in each table entry is the number of "points" that each
        token contributes toward the belief that the file under test is a
        particular language.  Points are additive.

        Points are the number of times a token appears in the file, times
        how much more likely (log of probability ratio) that token is to
        appear in one language vs.  the least-likely language.  Dashes
        indicate the least-likely language (and zero points) for each token.
        """
        maxlen = max([len(token) for token in tokens])

        print '%ss' % maxlen
        print '    #' + ''.join(['%10s' for lang in languages])

        if not is_py27:
            return

        tokmap = Counter(tokens)
        for tok, count in tokmap.most_common():
            arr = [(lang, self.token_probability(tok, lang)) for lang in languages]
            minlen = min([n for lang, n in arr])
            minlog = math.log(minlen)

            if not reduce(lambda x, y: x and y[1] == arr[0][1], arr, True):
                print '%*s%5d' % (maxlen, tok, count)

                for ent in arr:
                    if ent[1] == minlen:
                        print '         -'
                    else:
                        print '%10.3f' % (math.log(ent[1]) - minlog)

########NEW FILE########
__FILENAME__ = file_blob
# -*- coding: utf-8 -*-

from os import stat
from blob_helper import BlobHelper


class FileBlob(BlobHelper):
    """
    A FileBlob is a wrapper around a File object to make it quack
    like a Grit::Blob. It provides the basic interface: `name`,
    `data`, and `size`.
    """

    def __init__(self, path, base_path=None):
        """
        Public: Initialize a new FileBlob from a path

          path      - A path String that exists on the file system.
          base_path - Optional base to relativize the path

        Returns a FileBlob.


        """
        self.path = path

        """
        Public: name

        Examples

          FileBlob.new("/path/to/linguist/lib/linguist.rb").name
          # =>  "/path/to/linguist/lib/linguist.rb"

          FileBlob.new("/path/to/linguist/lib/linguist.rb",
                       "/path/to/linguist").name
          # =>  "lib/linguist.rb"

        Returns a String
        """
        if base_path:
            base_path = base_path.rstrip('/')
        self.name = base_path and path.replace('%s/' % base_path, '', 1) or path

    def __repr__(self):
        return '<FileBlob name:%s>' % self.name

    @property
    def stat(self):
        return stat(self.path)

    @property
    def mode(self):
        """
        Public: Read file permissions

        Returns a String like '100644'
        """
        mode = self.stat.st_mode
        return oct(mode)

    @property
    def data(self):
        """
        Public: Read file contents.

        Returns a String.
        """
        if hasattr(self, '_data'):
            return self._data
        self._data = file(self.path).read()
        return self._data

    @property
    def size(self):
        """
        Public: Get byte size

        Returns an Integer.
        """
        return self.stat.st_size

########NEW FILE########
__FILENAME__ = generated
# -*- coding: utf-8 -*-

import re
from os.path import splitext

XCODE_PROJECT_EXT_NAMES = ('.xib', '.nib', '.storyboard', '.pbxproj',
                           '.xcworkspacedata', '.xcuserstate')


class Generated(object):

    def __init__(self, name, data):
        self.name = name
        self.ext_name = splitext(self.name)[1].lower()
        self._data = data

    def __repr__(self):
        return '<Generated name:%s>' % self.name

    @classmethod
    def is_generated(cls, name, data):
        return cls(name, data)._is_generated

    @property
    def data(self):
        if hasattr(self, 'real_data'):
            return self.real_data
        self.real_data = self._data() if callable(self._data) else self._data
        return self.real_data

    @property
    def lines(self):
        return self.data and self.data.split("\n", -1) or []

    @property
    def _is_generated(self):
        return any((self.name == "Gemfile.lock",
                    self.is_minified_files,
                    self.is_compiled_coffeescript,
                    self.is_xcode_project_file,
                    self.is_generated_parser,
                    self.is_generated_net_docfile,
                    self.is_generated_net_designer_file,
                    self.is_generated_protocol_buffer,
                    self.is_generated_jni_header))

    @property
    def is_xcode_project_file(self):
        """
        Internal: Is the blob an XCode project file?

        Generated if the file extension is an XCode project
        file extension.

        Returns True of False.
        """
        return self.ext_name in XCODE_PROJECT_EXT_NAMES

    @property
    def is_minified_files(self):
        """
        Internal: Is the blob minified files?

        Consider a file minified if it contains more than 5% spaces.
        Currently, only JS and CSS files are detected by this method.

        Returns True or False.
        """
        if self.ext_name not in ('.js', '.css'):
            return False
        if self.data and len(self.data) > 200:
            count_space = sum([1 for _ in self.data if _ <= ' '])
            return (count_space / float(len(self.data))) < 0.05
        return False

    @property
    def is_compiled_coffeescript(self):
        """
        Internal: Is the blob of JS generated by CoffeeScript?

        CoffeeScript is meant to output JS that would be difficult to
        tell if it was generated or not. Look for a number of patterns
        output by the CS compiler.

        Return True or False
        """
        if self.ext_name != ".js":
            return False

        lines = self.lines

        # CoffeeScript generated by > 1.2 include a comment on the first line
        if len(lines) > 0 \
                and re.compile('^\/\/ Generated by ', re.DOTALL).search(lines[0]):
            return True

        if len(lines) < 3:
            return False

        if len(lines) > 2 \
                and lines[0] == '(function() {'  \
                and lines[-2] == '}).call(this);' \
                and lines[-1] == '':
            # First line is module closure opening
            # Second to last line closes module closure
            # Last line is blank
            score = 0
            count_keys = lambda r, s: len(re.compile(r, re.DOTALL).findall(s))
            for line in lines:
                if re.compile('var ', re.DOTALL).search(line):
                    # Underscored temp vars are likely to be Coffee
                    score += 1 * count_keys('(_fn|_i|_len|_ref|_results)', line)
                    # bind and extend functions are very Coffee specific
                    score += 3 * count_keys('(__bind|__extends|__hasProp|__indexOf|__slice)', line)
            return score > 3
        return False

    @property
    def is_generated_net_docfile(self):
        """
        Internal: Is this a generated documentation file for a .NET assembly?

        .NET developers often check in the XML Intellisense file along with an
        assembly - however, these don't have a special extension, so we have to
        dig into the contents to determine if it's a docfile. Luckily, these files
        are extremely structured, so recognizing them is easy.

        Returns True or False
          return false unless extname.downcase == ".xml"
          return false unless lines.count > 3
        """
        if self.ext_name != ".xml":
            return False

        lines = self.lines

        if len(lines) < 3:
            return False

        """
        .NET Docfiles always open with <doc> and their first tag is an
        <assembly> tag
        """
        return '<doc>' in lines[1] \
               and '<assembly>' in lines[2] \
               and '</doc>' in lines[-2]

    @property
    def is_generated_net_designer_file(self):
        """
        Internal: Is this a codegen file for a .NET project?

        Visual Studio often uses code generation to generate partial
        classes, and these files can be quite unwieldy. Let's hide them.

        Returns true or false
        """
        return self.name.lower().endswith('.designer.cs')

    @property
    def is_generated_parser(self):
        """
        Internal: Is the blob of JS a parser generated by PEG.js?

        PEG.js-generated parsers are not meant to be consumed by humans.

        Return True or False
        """
        if self.ext_name != ".js":
            return False

        # PEG.js-generated parsers include a comment near the top  of the file
        # that marks them as such.
        lines = self.lines
        if len(lines) < 5:
            return False

        if re.compile('^(?:[^\/]|\/[^\*])*\/\*(?:[^\*]|\*[^\/])*Generated by PEG.js', re.DOTALL).search(''.join(lines[0:5])):
            return True
        return False

    @property
    def is_generated_protocol_buffer(self):
        """
        Internal: Is the blob a C++, Java or Python source file generated by the
        Protocol Buffer compiler?

        Returns true of false.
        """
        if self.ext_name not in ('.py', '.java', '.h', '.cc', '.cpp'):
            return False

        if len(self.lines) < 1:
            return False

        return 'Generated by the protocol buffer compiler.  DO NOT EDIT!' in self.lines[0]

    @property
    def is_generated_jni_header(self):
        """
        Internal: Is the blob a C/C header generated by the Java JNI tool javah?

        Returns true of false.
        """
        if self.ext_name != '.h':
            return False
        if len(self.lines) < 2:
            return False

        return all(("/* DO NOT EDIT THIS FILE - it is machine generated */" in self.lines[0],
                    "#include <jni.h>" in self.lines[1]))

    @property
    def is_node_modules(self):
        """
        node_modules/ can contain large amounts of files, in general not meant
        for humans in pull requests.

        Returns true or false.
        """
        return bool(re.compile('node_modules/').search(self.name))

########NEW FILE########
__FILENAME__ = language
# -*- coding: utf-8 -*-

import re
import urllib
from os.path import realpath, dirname, basename, splitext, join
from collections import defaultdict

import yaml
from pygments import lexers
from pygments import highlight
from pygments.formatters import HtmlFormatter

from classifier import Classifier
from samples import DATA

DIR = dirname(realpath(__file__))
POPULAR_PATH = join(DIR, "popular.yml")
LANGUAGES_PATH = join(DIR, "languages.yml")

POPULAR = yaml.load(open(POPULAR_PATH))
LANGUAGES = yaml.load(open(LANGUAGES_PATH))


class ItemMeta(type):
    def __getitem__(cls, item):
        return cls.find_by_name(item)


class Language(object):
    """
    Language names that are recognizable by GitHub. Defined languages
    can be highlighted, searched and listed under the Top Languages page.

    Languages are defined in `lib/linguist/languages.yml`.
    """

    __metaclass__ = ItemMeta
    languages = []
    index = {}
    name_index = {}
    alias_index = {}
    extension_index = defaultdict(list)
    filename_index = defaultdict(list)
    primary_extension_index = {}

    _colors = []
    _ace_modes = []

    # Valid Languages types
    TYPES = ('data', 'markup', 'programming')

    @staticmethod
    def detectable_markup():
        # Names of non-programming languages that we will still detect
        # Returns an array
        return ["CSS", "Less", "Sass", "TeX"]

    @classmethod
    def create(cls, attributes={}):
        language = cls(attributes)
        cls.languages.append(language)

        # All Language names should be unique. Raise if there is a duplicate.
        if language.name in cls.name_index:
            raise ValueError("Duplicate language name: %s" % language.name)
        # Language name index
        name = language.name
        cls.index[name] = cls.name_index[name] = language
        cls.index[name.lower()] = cls.name_index[name.lower()] = language

        # All Language aliases should be unique.
        # Raise if there is a duplicate.
        for name in language.aliases:
            if name in cls.alias_index:
                raise ValueError("Duplicate alias: %s " % name)
            cls.index[name] = cls.alias_index[name] = language

        for extension in language.extensions:
            if not extension.startswith('.'):
                raise ValueError("Extension is missing a '.': %s" % extension)
            cls.extension_index[extension].append(language)

        if language.primary_extension in cls.primary_extension_index:
            raise ValueError("Duplicate primary extension: %s" % language.primary_extension)
        cls.primary_extension_index[language.primary_extension] = language

        for filename in language.filenames:
            cls.filename_index[filename].append(language)
        return language

    def __init__(self, attributes={}):
        # name is required
        if 'name' not in attributes:
            raise KeyError('missing name')
        self.name = attributes['name']

        # Set type
        self.type = attributes.get('type')
        if self.type and self.type not in self.TYPES:
            raise ValueError('invalid type: %s' % self.type)

        self.color = attributes['color']

        # Set aliases
        aliases = attributes.get('aliases', [])
        self.aliases = [self.default_alias_name] + aliases

        # Lookup Lexer object
        lexer = attributes.get('lexer') or self.name
        self.lexer = lexers.find_lexer_class(lexer)
        if not self.lexer:
            raise TypeError('%s is missing lexer' % self.name)

        self.ace_mode = attributes['ace_mode']
        self.wrap = attributes.get('wrap') or False

        # Set legacy search term
        self.search_term = attributes.get('search_term') or self.default_alias_name

        # Set extensions or default to [].
        self.extensions = attributes.get('extensions', [])
        self.filenames = attributes.get('filenames', [])

        self.primary_extension = attributes.get('primary_extension')
        if not self.primary_extension:
            raise KeyError('%s is missing primary extension' % self.name)

        # Prepend primary extension unless its already included
        if self.primary_extension not in self.extensions:
            self.extensions = [self.primary_extension] + self.extensions

        # Set popular, and searchable flags
        self.popular = attributes.get('popular', False)
        self.searchable = attributes.get('searchable', True)

        # If group name is set, save the name so we can lazy load it later
        group_name = attributes.get('group_name')
        if group_name:
            self._group = None
            self.group_name = group_name
        else:
            self._group = self

    def __repr__(self):
        return '<Language name:%s>' % self.name

    def __eq__(self, target):
        return self.name == target.name and self.extensions == target.extensions

    @classmethod
    def find_by_name(cls, name):
        """
        Public: Look up Language by its proper name.

        name - The String name of the Language

         Examples

           Language.find_by_name('Ruby')
           # => #<Language name:"Ruby">

        Returns the Language or nil if none was found.
        """
        return cls.name_index.get(name) or cls.find_by_alias(name)

    @classmethod
    def find_by_filename(cls, filename):
        """
        Public: Look up Languages by filename.
        filename - The path String.

        Examples
          Language.find_by_filename('foo.rb')
          # => [#<Language name:"Ruby">]

        Returns all matching Languages or [] if none were found.
        """
        name, extname = basename(filename), splitext(filename)[1]

        lang = cls.primary_extension_index.get(extname)
        langs = lang and [lang] or []
        langs.extend(cls.filename_index.get(name, []))
        langs.extend(cls.extension_index.get(extname, []))
        return list(set(langs))

    @classmethod
    def find_by_alias(cls, name):
        """
        Public: Look up Language by one of its aliases.

        name - A String alias of the Language

        Examples

          Language.find_by_alias('cpp')
          # => #<Language name:"Ruby">

        Returns the Language or nil if none was found.
        """
        return cls.alias_index.get(name)

    @classmethod
    def colors(cls):
        if cls._colors:
            return cls._colors
        cls._colors = sorted(filter(lambda l: l.color, cls.all()), key=lambda l: l.name.lower())
        return cls._colors

    @classmethod
    def ace_modes(cls):
        if cls._ace_modes:
            return cls._ace_modes
        cls._ace_modes = sorted(filter(lambda l: l.ace_mode, cls.all()), key=lambda l: l.name.lower())
        return cls._ace_modes

    @classmethod
    def all(cls):
        """
        Public: Get all Languages
        Returns an Array of Languages
        """
        return cls.languages

    @classmethod
    def detect(cls, name, data, mode=None):
        """
        Public: Detects the Language of the blob.

          name - String filename
          data - String blob data. A block also maybe passed in for lazy
                 loading. This behavior is deprecated and you should
                 always pass in a String.
          mode - Optional String mode (defaults to nil)

        Returns Language or nil.

        A bit of an elegant hack. If the file is executable but
        extensionless, append a "magic" extension so it can be
        classified with other languages that have shebang scripts.
        """
        extname = splitext(name)[1]
        if not extname and mode and (int(mode, 8) & 05 == 05):
            name += ".script!"

        possible_languages = cls.find_by_filename(name)

        if not possible_languages:
            return

        if len(possible_languages) == 1:
            return possible_languages[0]

        data = data() if callable(data) else data
        if data is None or data == "":
            return

        _pns = [p.name for p in possible_languages]
        result = Classifier.classify(DATA, data, _pns)
        if result:
            return cls[result[0][0]]

    def colorize(self, text, options={}):
        return highlight(text, self.lexer(), HtmlFormatter(**options))

    @property
    def group(self):
        return self._group or self.find_by_name(self.group_name)

    @property
    def is_popular(self):
        """
        Is it popular?
        Returns true or false
        """
        return self.popular

    @property
    def is_unpopular(self):
        """
        Is it not popular?
        Returns true or false
        """
        return not self.popular

    @property
    def is_searchable(self):
        """
        Is it searchable?

        Unsearchable languages won't by indexed by solr and won't show
        up in the code search dropdown.

        Returns true or false
        """
        return self.searchable

    @property
    def default_alias_name(self):
        """
        Internal: Get default alias name
        Returns the alias name String
        """
        return re.sub('\s', '-', self.name.lower())

    @property
    def escaped_name(self):
        """
        Public: Get URL escaped name.

        Examples:
          "C%23"
          "C%2B%2B"
          "Common%20Lisp"

        Returns the escaped String.
        """
        return urllib.quote(self.name, '')

extensions = DATA['extnames']
filenames = DATA['filenames']
popular = POPULAR

for name, options in sorted(LANGUAGES.iteritems(), key=lambda k: k[0]):
    options['extensions'] = options.get('extensions', [])
    options['filenames'] = options.get('filenames', [])

    def _merge(data, item_name):
        items = data.get(name, [])
        for item in items:
            if item not in options[item_name]:
                options[item_name].append(item)

    _merge(extensions, 'extensions')
    _merge(filenames, 'filenames')

    Language.create(dict(name=name,
                         color=options.get('color'),
                         type=options.get('type'),
                         aliases=options.get('aliases', []),
                         lexer=options.get('lexer'),
                         ace_mode=options.get('ace_mode'),
                         wrap=options.get('wrap'),
                         group_name=options.get('group'),
                         searchable=options.get('searchable', True),
                         search_term=options.get('search_term'),
                         extensions=sorted(options['extensions']),
                         primary_extension=options.get('primary_extension'),
                         filenames=options['filenames'],
                         popular=name in popular))

########NEW FILE########
__FILENAME__ = md5
# -*- coding: utf-8 -*-

import hashlib


class MD5(object):

    def __repr__(self):
        return '<MD5>'

    @classmethod
    def hexdigest(cls, obj):
        digest = hashlib.md5()

        if isinstance(obj, (str, int)):
            digest.update(obj.__class__.__name__)
            digest.update('%s' % obj)

        elif isinstance(obj, bool) or obj is None:
            digest.update(obj.__class__.__name__)

        elif isinstance(obj, (list, tuple)):
            digest.update(obj.__class__.__name__)
            for e in obj:
                digest.update(cls.hexdigest(e))

        elif isinstance(obj, dict):
            digest.update(obj.__class__.__name__)
            hexs = [cls.hexdigest([k, v]) for k, v in obj.iteritems()]
            hexs.sort()
            for e in hexs:
                digest.update(e)

        else:
            raise TypeError("can't convert %s into String" % obj)

        return digest.hexdigest()

########NEW FILE########
__FILENAME__ = repository
# -*- coding: utf-8 -*-
import os
import re
from collections import defaultdict
from functools import partial
from itertools import imap

from file_blob import FileBlob
from language import Language


class Repository(object):
    """
    A Repository is an abstraction of a Grit::Repo or a basic file
    system tree. It holds a list of paths pointing to Blobish objects.

    Its primary purpose is for gathering language statistics across
    the entire project.
    """

    def __init__(self, enum):
        """
        Public: Initialize a new Repository

        enum - Enumerator that responds to `each` and
            yields Blob objects

        Returns a Repository
        """
        self.enum = enum
        self.computed_stats = False
        self._language = self._size = None
        self.sizes = defaultdict(int)

    def __repr__(self):
        return '<Repository computed_stats:%s>' % self.computed_stats

    @classmethod
    def from_directory(cls, base_path):
        """
        Public: Initialize a new Repository from a File directory

        base_path - A path String

        Returns a Repository
        """
        blob = partial(FileBlob, base_path=base_path)
        enum = imap(blob, cls.get_files(base_path))
        return cls(enum)

    @staticmethod
    def get_files(base_path):
        join, isfile = os.path.join, os.path.isfile
        for root, dirs, files in os.walk(base_path, topdown=False, followlinks=False):
            if re.search('\/\.', root):
                continue
            for f in files:
                full_path = join(root, f)
                if isfile(full_path):
                    yield full_path

    @property
    def languages(self):
        """
        Public: Returns a breakdown of language stats.

          Examples

            # => { Language['Ruby'] => 46319,
                   Language['JavaScript'] => 258 }

          Returns a Hash of Language keys and Integer size values.
        """
        self.compute_stats
        return self.sizes

    @property
    def language(self):
        """
        Public: Get primary Language of repository.

        Returns a Language
        """
        self.compute_stats
        return self._language

    @property
    def size(self):
        """
        Public: Get the total size of the repository.

        Returns a byte size Integer
        """
        self.compute_stats
        return self._size

    @property
    def compute_stats(self):
        """
        Internal: Compute language breakdown for each blob in the Repository.

        Returns nothing
        """
        if self.computed_stats:
            return

        for blob in self.enum:
            # Skip vendored
            if blob.is_vendored:
                continue
            # Skip files that are likely binary
            if blob.is_likely_binary:
                continue
            # Skip generated blobs
            if blob.is_generated or blob.language is None:
                continue
            # Only include programming languages and acceptable markup languages
            if blob.language.type == 'programming' or blob.language.name in Language.detectable_markup():
                self.sizes[blob.language.group] += blob.size

        # Compute total size
        self._size = sum(self.sizes.itervalues())

        # Get primary language
        primary = sorted(self.sizes.iteritems(), key=lambda t: t[1], reverse=True)
        if primary:
            self._language = primary[0][0]

        self.computed_stats = True

########NEW FILE########
__FILENAME__ = samples
# -*- coding: utf-8 -*-
import json
from os import listdir
from os.path import realpath, dirname, exists, join, splitext
from collections import defaultdict

from classifier import Classifier
from md5 import MD5

DIR = dirname(realpath(__file__))
ROOT = join(dirname(dirname(DIR)), "samples")
PATH = join(DIR, "samples.json")
DATA = {}

if exists(PATH):
    DATA = json.load(open(PATH))


class Samples(object):
    """
    Model for accessing classifier training data.
    """

    def __repr__(self):
        return '<Samples>'

    @classmethod
    def generate(cls):
        data = cls.data()
        json.dump(data, open(PATH, 'w'), indent=2)

    @classmethod
    def each(cls, func):
        for category in listdir(ROOT):
            if category in ('Binary', 'Text'):
                continue
            dirname = join(ROOT, category)
            for filename in listdir(dirname):
                if filename == 'filenames':
                    subdirname = join(dirname, filename)
                    for subfilename in listdir(subdirname):
                        func({'path': join(subdirname, subfilename),
                              'language': category,
                              'filename': subfilename})
                else:
                    _extname = splitext(filename)[1]
                    path = join(dirname, filename)
                    if _extname == '':
                        raise '%s is missing an extension, maybe it belongs in filenames/subdir' % path
                    func({'path': path,
                          'language': category,
                          'extname': _extname})

    @classmethod
    def data(cls):
        """
        Public: Build Classifier from all samples.

        Returns trained Classifier.
        """
        db = {'extnames': defaultdict(list),
              'filenames': defaultdict(list)}

        def _learn(sample):
            _extname = sample.get('extname')
            _filename = sample.get('filename')
            _langname = sample['language']

            if _extname:
                if _extname not in db['extnames'][_langname]:
                    db['extnames'][_langname].append(_extname)
                    db['extnames'][_langname].sort()

            if _filename:
                db['filenames'][_langname].append(_filename)
                db['filenames'][_langname].sort()

            data = open(sample['path']).read()
            Classifier.train(db, _langname, data)

        cls.each(_learn)

        db['md5'] = MD5.hexdigest(db)
        return db

########NEW FILE########
__FILENAME__ = tokenizer
# -*- coding: utf-8 -*-
from re import compile, escape

from scanner import StringScanner, StringRegexp

"""
Generic programming language tokenizer.

Tokens are designed for use in the language bayes classifier.
It strips any data strings or comments and preserves significant
language symbols.
"""

# Read up to 100KB
BYTE_LIMIT = 100000

# Start state on token, ignore anything till the next newline
SINGLE_LINE_COMMENTS = [
    '//',  # C
    '#',   # Python, Ruby
    '%',   # Tex
]

# Start state on opening token, ignore anything until the closing
# token is reached.
MULTI_LINE_COMMENTS = [
    [r'/*', r'*/'],     # C
    [r'<!--', r'-->'],  # XML
    [r'{-', r'-}'],     # Haskell
    [r'(*', r'*)'],     # Coq
    [r'"""', r'"""'],   # Python
    [r"'''", r"'''"],   # Python
]

MULTI_LINE_COMMENT_DICT = dict([(s, StringRegexp(escape(e)))
                                for s, e in MULTI_LINE_COMMENTS])

START_SINGLE_LINE_COMMENT = StringRegexp('|'.join(map(lambda c: '\s*%s ' % escape(c), SINGLE_LINE_COMMENTS)))
START_MULTI_LINE_COMMENT = StringRegexp('|'.join(map(lambda c: escape(c[0]), MULTI_LINE_COMMENTS)))


REGEX_SHEBANG = StringRegexp(r'^#!.+')
REGEX_BOL = StringRegexp(r'\n|\Z')
REGEX_DOUBLE_QUOTE = StringRegexp(r'"')
REGEX_SINGLE_QUOTE = StringRegexp(r"'")
REGEX_DOUBLE_END_QUOTE = StringRegexp(r'[^\\]"')
REGEX_SINGLE_END_QUOTE = StringRegexp(r"[^\\]'")
REGEX_NUMBER_LITERALS = StringRegexp(r'(0x)?\d(\d|\.)*')
REGEX_SGML = StringRegexp(r'<[^\s<>][^<>]*>')
REGEX_COMMON_PUNCTUATION = StringRegexp(r';|\{|\}|\(|\)|\[|\]')
REGEX_REGULAR_TOKEN = StringRegexp(r'[\w\.@#\/\*]+')
REGEX_COMMON_OPERATORS = StringRegexp(r'<<?|\+|\-|\*|\/|%|&&?|\|\|?')
REGEX_EMIT_START_TOKEN = StringRegexp(r'<\/?[^\s>]+')
REGEX_EMIT_TRAILING = StringRegexp(r'\w+=')
REGEX_EMIT_WORD = StringRegexp(r'\w+')
REGEX_EMIT_END_TAG = StringRegexp('>')

REGEX_SHEBANG_FULL = StringRegexp(r'^#!\s*\S+')
REGEX_SHEBANG_WHITESPACE = StringRegexp(r'\s+')
REGEX_SHEBANG_NON_WHITESPACE = StringRegexp(r'\S+')


class Tokenizer(object):

    def __repr__(self):
        return '<Tokenizer>'

    @classmethod
    def tokenize(cls, data):
        """
        Public: Extract tokens from data

        data - String to tokenize

        Returns Array of token Strings.
        """
        return cls().extract_tokens(data)

    def extract_tokens(self, data):
        """
        Internal: Extract generic tokens from data.

        data - String to scan.

        Examples

          extract_tokens("printf('Hello')")
          # => ['printf', '(', ')']

        Returns Array of token Strings.
        """
        s = StringScanner(data)
        tokens = []
        while not s.is_eos:
            if s.pos >= BYTE_LIMIT:
                break
            token = s.scan(REGEX_SHEBANG)
            if token:
                name = self.extract_shebang(token)
                if name:
                    tokens.append('SHEBANG#!%s' % name)
                continue

            # Single line comment
            if s.is_bol and s.scan(START_SINGLE_LINE_COMMENT):
                s.skip_until(REGEX_BOL)
                continue

            # Multiline comments
            token = s.scan(START_MULTI_LINE_COMMENT)
            if token:
                close_token = MULTI_LINE_COMMENT_DICT[token]
                s.skip_until(close_token)
                continue

            # Skip single or double quoted strings
            if s.scan(REGEX_DOUBLE_QUOTE):
                if s.peek(1) == '"':
                    s.getch
                else:
                    s.skip_until(REGEX_DOUBLE_END_QUOTE)
                continue
            if s.scan(REGEX_SINGLE_QUOTE):
                if s.peek(1) == "'":
                    s.getch
                else:
                    s.skip_until(REGEX_SINGLE_END_QUOTE)
                continue

            # Skip number literals
            if s.scan(REGEX_NUMBER_LITERALS):
                continue

            # SGML style brackets
            token = s.scan(REGEX_SGML)
            if token:
                for t in self.extract_sgml_tokens(token):
                    tokens.append(t)
                continue

            # Common programming punctuation
            token = s.scan(REGEX_COMMON_PUNCTUATION)
            if token:
                tokens.append(token)
                continue

            # Regular token
            token = s.scan(REGEX_REGULAR_TOKEN)
            if token:
                tokens.append(token)
                continue

            # Common operators
            token = s.scan(REGEX_COMMON_OPERATORS)
            if token:
                tokens.append(token)
                continue

            s.getch
        return tokens

    @classmethod
    def extract_shebang(cls, data):
        """
        Internal: Extract normalized shebang command token.

        Examples

          extract_shebang("#!/usr/bin/ruby")
          # => "ruby"

          extract_shebang("#!/usr/bin/env node")
          # => "node"

        Returns String token or nil it couldn't be parsed.
        """
        s = StringScanner(data)
        path = s.scan(REGEX_SHEBANG_FULL)
        if path:
            script = path.split('/')[-1]
            if script == 'env':
                s.scan(REGEX_SHEBANG_WHITESPACE)
                script = s.scan(REGEX_SHEBANG_NON_WHITESPACE)
            if script:
                script = compile(r'[^\d]+').match(script).group(0)
            return script
        return

    def extract_sgml_tokens(self, data):
        """
        Internal: Extract tokens from inside SGML tag.

        data - SGML tag String.

            Examples

              extract_sgml_tokens("<a href='' class=foo>")
              # => ["<a>", "href="]

        Returns Array of token Strings.
        """
        s = StringScanner(data)
        tokens = []
        append = tokens.append

        while not s.is_eos:
            # Emit start token
            token = s.scan(REGEX_EMIT_START_TOKEN)
            if token:
                append(token + '>')
                continue

            # Emit attributes with trailing =
            token = s.scan(REGEX_EMIT_TRAILING)
            if token:
                append(token)

                # Then skip over attribute value
                if s.scan(REGEX_DOUBLE_QUOTE):
                    s.skip_until(REGEX_DOUBLE_END_QUOTE)
                    continue
                if s.scan(REGEX_SINGLE_QUOTE):
                    s.skip_until(REGEX_SINGLE_END_QUOTE)
                    continue
                s.skip_until(REGEX_EMIT_WORD)
                continue

            # Emit lone attributes
            token = s.scan(REGEX_EMIT_WORD)
            if token:
                append(token)

            # Stop at the end of the tag
            if s.scan(REGEX_EMIT_END_TAG):
                s.terminate
                continue

            s.getch

        return tokens

########NEW FILE########
__FILENAME__ = django-models-base
from __future__ import unicode_literals

import copy
import sys
from functools import update_wrapper
from future_builtins import zip

import django.db.models.manager     # Imported to register signal handler.
from django.conf import settings
from django.core.exceptions import (ObjectDoesNotExist,
    MultipleObjectsReturned, FieldError, ValidationError, NON_FIELD_ERRORS)
from django.core import validators
from django.db.models.fields import AutoField, FieldDoesNotExist
from django.db.models.fields.related import (ManyToOneRel,
    OneToOneField, add_lazy_relation)
from django.db import (router, transaction, DatabaseError,
    DEFAULT_DB_ALIAS)
from django.db.models.query import Q
from django.db.models.query_utils import DeferredAttribute
from django.db.models.deletion import Collector
from django.db.models.options import Options
from django.db.models import signals
from django.db.models.loading import register_models, get_model
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import curry
from django.utils.encoding import smart_str, force_unicode
from django.utils.text import get_text_list, capfirst


class ModelBase(type):
    """
    Metaclass for all models.
    """
    def __new__(cls, name, bases, attrs):
        super_new = super(ModelBase, cls).__new__
        parents = [b for b in bases if isinstance(b, ModelBase)]
        if not parents:
            # If this isn't a subclass of Model, don't do anything special.
            return super_new(cls, name, bases, attrs)

        # Create the class.
        module = attrs.pop('__module__')
        new_class = super_new(cls, name, bases, {'__module__': module})
        attr_meta = attrs.pop('Meta', None)
        abstract = getattr(attr_meta, 'abstract', False)
        if not attr_meta:
            meta = getattr(new_class, 'Meta', None)
        else:
            meta = attr_meta
        base_meta = getattr(new_class, '_meta', None)

        if getattr(meta, 'app_label', None) is None:
            # Figure out the app_label by looking one level up.
            # For 'django.contrib.sites.models', this would be 'sites'.
            model_module = sys.modules[new_class.__module__]
            kwargs = {"app_label": model_module.__name__.split('.')[-2]}
        else:
            kwargs = {}

        new_class.add_to_class('_meta', Options(meta, **kwargs))
        if not abstract:
            new_class.add_to_class('DoesNotExist', subclass_exception(b'DoesNotExist',
                    tuple(x.DoesNotExist
                            for x in parents if hasattr(x, '_meta') and not x._meta.abstract)
                                    or (ObjectDoesNotExist,), module))
            new_class.add_to_class('MultipleObjectsReturned', subclass_exception(b'MultipleObjectsReturned',
                    tuple(x.MultipleObjectsReturned
                            for x in parents if hasattr(x, '_meta') and not x._meta.abstract)
                                    or (MultipleObjectsReturned,), module))
            if base_meta and not base_meta.abstract:
                # Non-abstract child classes inherit some attributes from their
                # non-abstract parent (unless an ABC comes before it in the
                # method resolution order).
                if not hasattr(meta, 'ordering'):
                    new_class._meta.ordering = base_meta.ordering
                if not hasattr(meta, 'get_latest_by'):
                    new_class._meta.get_latest_by = base_meta.get_latest_by

        is_proxy = new_class._meta.proxy

        if getattr(new_class, '_default_manager', None):
            if not is_proxy:
                # Multi-table inheritance doesn't inherit default manager from
                # parents.
                new_class._default_manager = None
                new_class._base_manager = None
            else:
                # Proxy classes do inherit parent's default manager, if none is
                # set explicitly.
                new_class._default_manager = new_class._default_manager._copy_to_model(new_class)
                new_class._base_manager = new_class._base_manager._copy_to_model(new_class)

        # Bail out early if we have already created this class.
        m = get_model(new_class._meta.app_label, name,
                      seed_cache=False, only_installed=False)
        if m is not None:
            return m

        # Add all attributes to the class.
        for obj_name, obj in attrs.items():
            new_class.add_to_class(obj_name, obj)

        # All the fields of any type declared on this model
        new_fields = new_class._meta.local_fields + \
                     new_class._meta.local_many_to_many + \
                     new_class._meta.virtual_fields
        field_names = set([f.name for f in new_fields])

        # Basic setup for proxy models.
        if is_proxy:
            base = None
            for parent in [cls for cls in parents if hasattr(cls, '_meta')]:
                if parent._meta.abstract:
                    if parent._meta.fields:
                        raise TypeError("Abstract base class containing model fields not permitted for proxy model '%s'." % name)
                    else:
                        continue
                if base is not None:
                    raise TypeError("Proxy model '%s' has more than one non-abstract model base class." % name)
                else:
                    base = parent
            if base is None:
                    raise TypeError("Proxy model '%s' has no non-abstract model base class." % name)
            if (new_class._meta.local_fields or
                    new_class._meta.local_many_to_many):
                raise FieldError("Proxy model '%s' contains model fields." % name)
            new_class._meta.setup_proxy(base)
            new_class._meta.concrete_model = base._meta.concrete_model
        else:
            new_class._meta.concrete_model = new_class

        # Do the appropriate setup for any model parents.
        o2o_map = dict([(f.rel.to, f) for f in new_class._meta.local_fields
                if isinstance(f, OneToOneField)])

        for base in parents:
            original_base = base
            if not hasattr(base, '_meta'):
                # Things without _meta aren't functional models, so they're
                # uninteresting parents.
                continue

            parent_fields = base._meta.local_fields + base._meta.local_many_to_many
            # Check for clashes between locally declared fields and those
            # on the base classes (we cannot handle shadowed fields at the
            # moment).
            for field in parent_fields:
                if field.name in field_names:
                    raise FieldError('Local field %r in class %r clashes '
                                     'with field of similar name from '
                                     'base class %r' %
                                        (field.name, name, base.__name__))
            if not base._meta.abstract:
                # Concrete classes...
                base = base._meta.concrete_model
                if base in o2o_map:
                    field = o2o_map[base]
                elif not is_proxy:
                    attr_name = '%s_ptr' % base._meta.module_name
                    field = OneToOneField(base, name=attr_name,
                            auto_created=True, parent_link=True)
                    new_class.add_to_class(attr_name, field)
                else:
                    field = None
                new_class._meta.parents[base] = field
            else:
                # .. and abstract ones.
                for field in parent_fields:
                    new_class.add_to_class(field.name, copy.deepcopy(field))

                # Pass any non-abstract parent classes onto child.
                new_class._meta.parents.update(base._meta.parents)

            # Inherit managers from the abstract base classes.
            new_class.copy_managers(base._meta.abstract_managers)

            # Proxy models inherit the non-abstract managers from their base,
            # unless they have redefined any of them.
            if is_proxy:
                new_class.copy_managers(original_base._meta.concrete_managers)

            # Inherit virtual fields (like GenericForeignKey) from the parent
            # class
            for field in base._meta.virtual_fields:
                if base._meta.abstract and field.name in field_names:
                    raise FieldError('Local field %r in class %r clashes '\
                                     'with field of similar name from '\
                                     'abstract base class %r' % \
                                        (field.name, name, base.__name__))
                new_class.add_to_class(field.name, copy.deepcopy(field))

        if abstract:
            # Abstract base models can't be instantiated and don't appear in
            # the list of models for an app. We do the final setup for them a
            # little differently from normal models.
            attr_meta.abstract = False
            new_class.Meta = attr_meta
            return new_class

        new_class._prepare()
        register_models(new_class._meta.app_label, new_class)

        # Because of the way imports happen (recursively), we may or may not be
        # the first time this model tries to register with the framework. There
        # should only be one class for each model, so we always return the
        # registered version.
        return get_model(new_class._meta.app_label, name,
                         seed_cache=False, only_installed=False)

    def copy_managers(cls, base_managers):
        # This is in-place sorting of an Options attribute, but that's fine.
        base_managers.sort()
        for _, mgr_name, manager in base_managers:
            val = getattr(cls, mgr_name, None)
            if not val or val is manager:
                new_manager = manager._copy_to_model(cls)
                cls.add_to_class(mgr_name, new_manager)

    def add_to_class(cls, name, value):
        if hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)

    def _prepare(cls):
        """
        Creates some methods once self._meta has been populated.
        """
        opts = cls._meta
        opts._prepare(cls)

        if opts.order_with_respect_to:
            cls.get_next_in_order = curry(cls._get_next_or_previous_in_order, is_next=True)
            cls.get_previous_in_order = curry(cls._get_next_or_previous_in_order, is_next=False)
            # defer creating accessors on the foreign class until we are
            # certain it has been created
            def make_foreign_order_accessors(field, model, cls):
                setattr(
                    field.rel.to,
                    'get_%s_order' % cls.__name__.lower(),
                    curry(method_get_order, cls)
                )
                setattr(
                    field.rel.to,
                    'set_%s_order' % cls.__name__.lower(),
                    curry(method_set_order, cls)
                )
            add_lazy_relation(
                cls,
                opts.order_with_respect_to,
                opts.order_with_respect_to.rel.to,
                make_foreign_order_accessors
            )

        # Give the class a docstring -- its definition.
        if cls.__doc__ is None:
            cls.__doc__ = "%s(%s)" % (cls.__name__, ", ".join([f.attname for f in opts.fields]))

        if hasattr(cls, 'get_absolute_url'):
            cls.get_absolute_url = update_wrapper(curry(get_absolute_url, opts, cls.get_absolute_url),
                                                  cls.get_absolute_url)

        signals.class_prepared.send(sender=cls)

class ModelState(object):
    """
    A class for storing instance state
    """
    def __init__(self, db=None):
        self.db = db
        # If true, uniqueness validation checks will consider this a new, as-yet-unsaved object.
        # Necessary for correct validation of new instances of objects with explicit (non-auto) PKs.
        # This impacts validation only; it has no effect on the actual save.
        self.adding = True

class Model(object):
    __metaclass__ = ModelBase
    _deferred = False

    def __init__(self, *args, **kwargs):
        signals.pre_init.send(sender=self.__class__, args=args, kwargs=kwargs)

        # Set up the storage for instance state
        self._state = ModelState()

        # There is a rather weird disparity here; if kwargs, it's set, then args
        # overrides it. It should be one or the other; don't duplicate the work
        # The reason for the kwargs check is that standard iterator passes in by
        # args, and instantiation for iteration is 33% faster.
        args_len = len(args)
        if args_len > len(self._meta.fields):
            # Daft, but matches old exception sans the err msg.
            raise IndexError("Number of args exceeds number of fields")

        fields_iter = iter(self._meta.fields)
        if not kwargs:
            # The ordering of the zip calls matter - zip throws StopIteration
            # when an iter throws it. So if the first iter throws it, the second
            # is *not* consumed. We rely on this, so don't change the order
            # without changing the logic.
            for val, field in zip(args, fields_iter):
                setattr(self, field.attname, val)
        else:
            # Slower, kwargs-ready version.
            for val, field in zip(args, fields_iter):
                setattr(self, field.attname, val)
                kwargs.pop(field.name, None)
                # Maintain compatibility with existing calls.
                if isinstance(field.rel, ManyToOneRel):
                    kwargs.pop(field.attname, None)

        # Now we're left with the unprocessed fields that *must* come from
        # keywords, or default.

        for field in fields_iter:
            is_related_object = False
            # This slightly odd construct is so that we can access any
            # data-descriptor object (DeferredAttribute) without triggering its
            # __get__ method.
            if (field.attname not in kwargs and
                    isinstance(self.__class__.__dict__.get(field.attname), DeferredAttribute)):
                # This field will be populated on request.
                continue
            if kwargs:
                if isinstance(field.rel, ManyToOneRel):
                    try:
                        # Assume object instance was passed in.
                        rel_obj = kwargs.pop(field.name)
                        is_related_object = True
                    except KeyError:
                        try:
                            # Object instance wasn't passed in -- must be an ID.
                            val = kwargs.pop(field.attname)
                        except KeyError:
                            val = field.get_default()
                    else:
                        # Object instance was passed in. Special case: You can
                        # pass in "None" for related objects if it's allowed.
                        if rel_obj is None and field.null:
                            val = None
                else:
                    try:
                        val = kwargs.pop(field.attname)
                    except KeyError:
                        # This is done with an exception rather than the
                        # default argument on pop because we don't want
                        # get_default() to be evaluated, and then not used.
                        # Refs #12057.
                        val = field.get_default()
            else:
                val = field.get_default()
            if is_related_object:
                # If we are passed a related instance, set it using the
                # field.name instead of field.attname (e.g. "user" instead of
                # "user_id") so that the object gets properly cached (and type
                # checked) by the RelatedObjectDescriptor.
                setattr(self, field.name, rel_obj)
            else:
                setattr(self, field.attname, val)

        if kwargs:
            for prop in kwargs.keys():
                try:
                    if isinstance(getattr(self.__class__, prop), property):
                        setattr(self, prop, kwargs.pop(prop))
                except AttributeError:
                    pass
            if kwargs:
                raise TypeError("'%s' is an invalid keyword argument for this function" % kwargs.keys()[0])
        super(Model, self).__init__()
        signals.post_init.send(sender=self.__class__, instance=self)

    def __repr__(self):
        try:
            u = unicode(self)
        except (UnicodeEncodeError, UnicodeDecodeError):
            u = '[Bad Unicode data]'
        return smart_str('<%s: %s>' % (self.__class__.__name__, u))

    def __str__(self):
        if hasattr(self, '__unicode__'):
            return force_unicode(self).encode('utf-8')
        return '%s object' % self.__class__.__name__

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self._get_pk_val() == other._get_pk_val()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._get_pk_val())

    def __reduce__(self):
        """
        Provides pickling support. Normally, this just dispatches to Python's
        standard handling. However, for models with deferred field loading, we
        need to do things manually, as they're dynamically created classes and
        only module-level classes can be pickled by the default path.
        """
        data = self.__dict__
        model = self.__class__
        # The obvious thing to do here is to invoke super().__reduce__()
        # for the non-deferred case. Don't do that.
        # On Python 2.4, there is something weird with __reduce__,
        # and as a result, the super call will cause an infinite recursion.
        # See #10547 and #12121.
        defers = []
        if self._deferred:
            from django.db.models.query_utils import deferred_class_factory
            factory = deferred_class_factory
            for field in self._meta.fields:
                if isinstance(self.__class__.__dict__.get(field.attname),
                        DeferredAttribute):
                    defers.append(field.attname)
            model = self._meta.proxy_for_model
        else:
            factory = simple_class_factory
        return (model_unpickle, (model, defers, factory), data)

    def _get_pk_val(self, meta=None):
        if not meta:
            meta = self._meta
        return getattr(self, meta.pk.attname)

    def _set_pk_val(self, value):
        return setattr(self, self._meta.pk.attname, value)

    pk = property(_get_pk_val, _set_pk_val)

    def serializable_value(self, field_name):
        """
        Returns the value of the field name for this instance. If the field is
        a foreign key, returns the id value, instead of the object. If there's
        no Field object with this name on the model, the model attribute's
        value is returned directly.

        Used to serialize a field's value (in the serializer, or form output,
        for example). Normally, you would just access the attribute directly
        and not use this method.
        """
        try:
            field = self._meta.get_field_by_name(field_name)[0]
        except FieldDoesNotExist:
            return getattr(self, field_name)
        return getattr(self, field.attname)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        """
        Saves the current instance. Override this in a subclass if you want to
        control the saving process.

        The 'force_insert' and 'force_update' parameters can be used to insist
        that the "save" must be an SQL insert or update (or equivalent for
        non-SQL backends), respectively. Normally, they should not be set.
        """
        if force_insert and (force_update or update_fields):
            raise ValueError("Cannot force both insert and updating in model saving.")

        if update_fields is not None:
            # If update_fields is empty, skip the save. We do also check for
            # no-op saves later on for inheritance cases. This bailout is
            # still needed for skipping signal sending.
            if len(update_fields) == 0:
                return

            update_fields = frozenset(update_fields)
            field_names = set([field.name for field in self._meta.fields
                               if not field.primary_key])
            non_model_fields = update_fields.difference(field_names)

            if non_model_fields:
                raise ValueError("The following fields do not exist in this "
                                 "model or are m2m fields: %s"
                                 % ', '.join(non_model_fields))

        self.save_base(using=using, force_insert=force_insert,
                       force_update=force_update, update_fields=update_fields)
    save.alters_data = True

    def save_base(self, raw=False, cls=None, origin=None, force_insert=False,
                  force_update=False, using=None, update_fields=None):
        """
        Does the heavy-lifting involved in saving. Subclasses shouldn't need to
        override this method. It's separate from save() in order to hide the
        need for overrides of save() to pass around internal-only parameters
        ('raw', 'cls', and 'origin').
        """
        using = using or router.db_for_write(self.__class__, instance=self)
        assert not (force_insert and (force_update or update_fields))
        assert update_fields is None or len(update_fields) > 0
        if cls is None:
            cls = self.__class__
            meta = cls._meta
            if not meta.proxy:
                origin = cls
        else:
            meta = cls._meta

        if origin and not meta.auto_created:
            signals.pre_save.send(sender=origin, instance=self, raw=raw, using=using,
                                  update_fields=update_fields)

        # If we are in a raw save, save the object exactly as presented.
        # That means that we don't try to be smart about saving attributes
        # that might have come from the parent class - we just save the
        # attributes we have been given to the class we have been given.
        # We also go through this process to defer the save of proxy objects
        # to their actual underlying model.
        if not raw or meta.proxy:
            if meta.proxy:
                org = cls
            else:
                org = None
            for parent, field in meta.parents.items():
                # At this point, parent's primary key field may be unknown
                # (for example, from administration form which doesn't fill
                # this field). If so, fill it.
                if field and getattr(self, parent._meta.pk.attname) is None and getattr(self, field.attname) is not None:
                    setattr(self, parent._meta.pk.attname, getattr(self, field.attname))

                self.save_base(cls=parent, origin=org, using=using,
                               update_fields=update_fields)

                if field:
                    setattr(self, field.attname, self._get_pk_val(parent._meta))
            if meta.proxy:
                return

        if not meta.proxy:
            non_pks = [f for f in meta.local_fields if not f.primary_key]

            if update_fields:
                non_pks = [f for f in non_pks if f.name in update_fields]

            # First, try an UPDATE. If that doesn't update anything, do an INSERT.
            pk_val = self._get_pk_val(meta)
            pk_set = pk_val is not None
            record_exists = True
            manager = cls._base_manager
            if pk_set:
                # Determine if we should do an update (pk already exists, forced update,
                # no force_insert)
                if ((force_update or update_fields) or (not force_insert and
                        manager.using(using).filter(pk=pk_val).exists())):
                    if force_update or non_pks:
                        values = [(f, None, (raw and getattr(self, f.attname) or f.pre_save(self, False))) for f in non_pks]
                        if values:
                            rows = manager.using(using).filter(pk=pk_val)._update(values)
                            if force_update and not rows:
                                raise DatabaseError("Forced update did not affect any rows.")
                            if update_fields and not rows:
                                raise DatabaseError("Save with update_fields did not affect any rows.")
                else:
                    record_exists = False
            if not pk_set or not record_exists:
                if meta.order_with_respect_to:
                    # If this is a model with an order_with_respect_to
                    # autopopulate the _order field
                    field = meta.order_with_respect_to
                    order_value = manager.using(using).filter(**{field.name: getattr(self, field.attname)}).count()
                    self._order = order_value

                fields = meta.local_fields
                if not pk_set:
                    if force_update or update_fields:
                        raise ValueError("Cannot force an update in save() with no primary key.")
                    fields = [f for f in fields if not isinstance(f, AutoField)]

                record_exists = False

                update_pk = bool(meta.has_auto_field and not pk_set)
                result = manager._insert([self], fields=fields, return_id=update_pk, using=using, raw=raw)

                if update_pk:
                    setattr(self, meta.pk.attname, result)
            transaction.commit_unless_managed(using=using)

        # Store the database on which the object was saved
        self._state.db = using
        # Once saved, this is no longer a to-be-added instance.
        self._state.adding = False

        # Signal that the save is complete
        if origin and not meta.auto_created:
            signals.post_save.send(sender=origin, instance=self, created=(not record_exists),
                                   update_fields=update_fields, raw=raw, using=using)


    save_base.alters_data = True

    def delete(self, using=None):
        using = using or router.db_for_write(self.__class__, instance=self)
        assert self._get_pk_val() is not None, "%s object can't be deleted because its %s attribute is set to None." % (self._meta.object_name, self._meta.pk.attname)

        collector = Collector(using=using)
        collector.collect([self])
        collector.delete()

    delete.alters_data = True

    def _get_FIELD_display(self, field):
        value = getattr(self, field.attname)
        return force_unicode(dict(field.flatchoices).get(value, value), strings_only=True)

    def _get_next_or_previous_by_FIELD(self, field, is_next, **kwargs):
        if not self.pk:
            raise ValueError("get_next/get_previous cannot be used on unsaved objects.")
        op = is_next and 'gt' or 'lt'
        order = not is_next and '-' or ''
        param = smart_str(getattr(self, field.attname))
        q = Q(**{'%s__%s' % (field.name, op): param})
        q = q|Q(**{field.name: param, 'pk__%s' % op: self.pk})
        qs = self.__class__._default_manager.using(self._state.db).filter(**kwargs).filter(q).order_by('%s%s' % (order, field.name), '%spk' % order)
        try:
            return qs[0]
        except IndexError:
            raise self.DoesNotExist("%s matching query does not exist." % self.__class__._meta.object_name)

    def _get_next_or_previous_in_order(self, is_next):
        cachename = "__%s_order_cache" % is_next
        if not hasattr(self, cachename):
            op = is_next and 'gt' or 'lt'
            order = not is_next and '-_order' or '_order'
            order_field = self._meta.order_with_respect_to
            obj = self._default_manager.filter(**{
                order_field.name: getattr(self, order_field.attname)
            }).filter(**{
                '_order__%s' % op: self._default_manager.values('_order').filter(**{
                    self._meta.pk.name: self.pk
                })
            }).order_by(order)[:1].get()
            setattr(self, cachename, obj)
        return getattr(self, cachename)

    def prepare_database_save(self, unused):
        return self.pk

    def clean(self):
        """
        Hook for doing any extra model-wide validation after clean() has been
        called on every field by self.clean_fields. Any ValidationError raised
        by this method will not be associated with a particular field; it will
        have a special-case association with the field defined by NON_FIELD_ERRORS.
        """
        pass

    def validate_unique(self, exclude=None):
        """
        Checks unique constraints on the model and raises ``ValidationError``
        if any failed.
        """
        unique_checks, date_checks = self._get_unique_checks(exclude=exclude)

        errors = self._perform_unique_checks(unique_checks)
        date_errors = self._perform_date_checks(date_checks)

        for k, v in date_errors.items():
            errors.setdefault(k, []).extend(v)

        if errors:
            raise ValidationError(errors)

    def _get_unique_checks(self, exclude=None):
        """
        Gather a list of checks to perform. Since validate_unique could be
        called from a ModelForm, some fields may have been excluded; we can't
        perform a unique check on a model that is missing fields involved
        in that check.
        Fields that did not validate should also be excluded, but they need
        to be passed in via the exclude argument.
        """
        if exclude is None:
            exclude = []
        unique_checks = []

        unique_togethers = [(self.__class__, self._meta.unique_together)]
        for parent_class in self._meta.parents.keys():
            if parent_class._meta.unique_together:
                unique_togethers.append((parent_class, parent_class._meta.unique_together))

        for model_class, unique_together in unique_togethers:
            for check in unique_together:
                for name in check:
                    # If this is an excluded field, don't add this check.
                    if name in exclude:
                        break
                else:
                    unique_checks.append((model_class, tuple(check)))

        # These are checks for the unique_for_<date/year/month>.
        date_checks = []

        # Gather a list of checks for fields declared as unique and add them to
        # the list of checks.

        fields_with_class = [(self.__class__, self._meta.local_fields)]
        for parent_class in self._meta.parents.keys():
            fields_with_class.append((parent_class, parent_class._meta.local_fields))

        for model_class, fields in fields_with_class:
            for f in fields:
                name = f.name
                if name in exclude:
                    continue
                if f.unique:
                    unique_checks.append((model_class, (name,)))
                if f.unique_for_date and f.unique_for_date not in exclude:
                    date_checks.append((model_class, 'date', name, f.unique_for_date))
                if f.unique_for_year and f.unique_for_year not in exclude:
                    date_checks.append((model_class, 'year', name, f.unique_for_year))
                if f.unique_for_month and f.unique_for_month not in exclude:
                    date_checks.append((model_class, 'month', name, f.unique_for_month))
        return unique_checks, date_checks

    def _perform_unique_checks(self, unique_checks):
        errors = {}

        for model_class, unique_check in unique_checks:
            # Try to look up an existing object with the same values as this
            # object's values for all the unique field.

            lookup_kwargs = {}
            for field_name in unique_check:
                f = self._meta.get_field(field_name)
                lookup_value = getattr(self, f.attname)
                if lookup_value is None:
                    # no value, skip the lookup
                    continue
                if f.primary_key and not self._state.adding:
                    # no need to check for unique primary key when editing
                    continue
                lookup_kwargs[str(field_name)] = lookup_value

            # some fields were skipped, no reason to do the check
            if len(unique_check) != len(lookup_kwargs.keys()):
                continue

            qs = model_class._default_manager.filter(**lookup_kwargs)

            # Exclude the current object from the query if we are editing an
            # instance (as opposed to creating a new one)
            # Note that we need to use the pk as defined by model_class, not
            # self.pk. These can be different fields because model inheritance
            # allows single model to have effectively multiple primary keys.
            # Refs #17615.
            model_class_pk = self._get_pk_val(model_class._meta)
            if not self._state.adding and model_class_pk is not None:
                qs = qs.exclude(pk=model_class_pk)
            if qs.exists():
                if len(unique_check) == 1:
                    key = unique_check[0]
                else:
                    key = NON_FIELD_ERRORS
                errors.setdefault(key, []).append(self.unique_error_message(model_class, unique_check))

        return errors

    def _perform_date_checks(self, date_checks):
        errors = {}
        for model_class, lookup_type, field, unique_for in date_checks:
            lookup_kwargs = {}
            # there's a ticket to add a date lookup, we can remove this special
            # case if that makes it's way in
            date = getattr(self, unique_for)
            if date is None:
                continue
            if lookup_type == 'date':
                lookup_kwargs['%s__day' % unique_for] = date.day
                lookup_kwargs['%s__month' % unique_for] = date.month
                lookup_kwargs['%s__year' % unique_for] = date.year
            else:
                lookup_kwargs['%s__%s' % (unique_for, lookup_type)] = getattr(date, lookup_type)
            lookup_kwargs[field] = getattr(self, field)

            qs = model_class._default_manager.filter(**lookup_kwargs)
            # Exclude the current object from the query if we are editing an
            # instance (as opposed to creating a new one)
            if not self._state.adding and self.pk is not None:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                errors.setdefault(field, []).append(
                    self.date_error_message(lookup_type, field, unique_for)
                )
        return errors

    def date_error_message(self, lookup_type, field, unique_for):
        opts = self._meta
        return _("%(field_name)s must be unique for %(date_field)s %(lookup)s.") % {
            'field_name': unicode(capfirst(opts.get_field(field).verbose_name)),
            'date_field': unicode(capfirst(opts.get_field(unique_for).verbose_name)),
            'lookup': lookup_type,
        }

    def unique_error_message(self, model_class, unique_check):
        opts = model_class._meta
        model_name = capfirst(opts.verbose_name)

        # A unique field
        if len(unique_check) == 1:
            field_name = unique_check[0]
            field = opts.get_field(field_name)
            field_label = capfirst(field.verbose_name)
            # Insert the error into the error dict, very sneaky
            return field.error_messages['unique'] %  {
                'model_name': unicode(model_name),
                'field_label': unicode(field_label)
            }
        # unique_together
        else:
            field_labels = map(lambda f: capfirst(opts.get_field(f).verbose_name), unique_check)
            field_labels = get_text_list(field_labels, _('and'))
            return _("%(model_name)s with this %(field_label)s already exists.") %  {
                'model_name': unicode(model_name),
                'field_label': unicode(field_labels)
            }

    def full_clean(self, exclude=None):
        """
        Calls clean_fields, clean, and validate_unique, on the model,
        and raises a ``ValidationError`` for any errors that occured.
        """
        errors = {}
        if exclude is None:
            exclude = []

        try:
            self.clean_fields(exclude=exclude)
        except ValidationError as e:
            errors = e.update_error_dict(errors)

        # Form.clean() is run even if other validation fails, so do the
        # same with Model.clean() for consistency.
        try:
            self.clean()
        except ValidationError as e:
            errors = e.update_error_dict(errors)

        # Run unique checks, but only for fields that passed validation.
        for name in errors.keys():
            if name != NON_FIELD_ERRORS and name not in exclude:
                exclude.append(name)
        try:
            self.validate_unique(exclude=exclude)
        except ValidationError as e:
            errors = e.update_error_dict(errors)

        if errors:
            raise ValidationError(errors)

    def clean_fields(self, exclude=None):
        """
        Cleans all fields and raises a ValidationError containing message_dict
        of all validation errors if any occur.
        """
        if exclude is None:
            exclude = []

        errors = {}
        for f in self._meta.fields:
            if f.name in exclude:
                continue
            # Skip validation for empty fields with blank=True. The developer
            # is responsible for making sure they have a valid value.
            raw_value = getattr(self, f.attname)
            if f.blank and raw_value in validators.EMPTY_VALUES:
                continue
            try:
                setattr(self, f.attname, f.clean(raw_value, self))
            except ValidationError as e:
                errors[f.name] = e.messages

        if errors:
            raise ValidationError(errors)


############################################
# HELPER FUNCTIONS (CURRIED MODEL METHODS) #
############################################

# ORDERING METHODS #########################

def method_set_order(ordered_obj, self, id_list, using=None):
    if using is None:
        using = DEFAULT_DB_ALIAS
    rel_val = getattr(self, ordered_obj._meta.order_with_respect_to.rel.field_name)
    order_name = ordered_obj._meta.order_with_respect_to.name
    # FIXME: It would be nice if there was an "update many" version of update
    # for situations like this.
    for i, j in enumerate(id_list):
        ordered_obj.objects.filter(**{'pk': j, order_name: rel_val}).update(_order=i)
    transaction.commit_unless_managed(using=using)


def method_get_order(ordered_obj, self):
    rel_val = getattr(self, ordered_obj._meta.order_with_respect_to.rel.field_name)
    order_name = ordered_obj._meta.order_with_respect_to.name
    pk_name = ordered_obj._meta.pk.name
    return [r[pk_name] for r in
            ordered_obj.objects.filter(**{order_name: rel_val}).values(pk_name)]


##############################################
# HELPER FUNCTIONS (CURRIED MODEL FUNCTIONS) #
##############################################

def get_absolute_url(opts, func, self, *args, **kwargs):
    return settings.ABSOLUTE_URL_OVERRIDES.get('%s.%s' % (opts.app_label, opts.module_name), func)(self, *args, **kwargs)


########
# MISC #
########

class Empty(object):
    pass

def simple_class_factory(model, attrs):
    """Used to unpickle Models without deferred fields.

    We need to do this the hard way, rather than just using
    the default __reduce__ implementation, because of a
    __deepcopy__ problem in Python 2.4
    """
    return model

def model_unpickle(model, attrs, factory):
    """
    Used to unpickle Model subclasses with deferred fields.
    """
    cls = factory(model, attrs)
    return cls.__new__(cls)
model_unpickle.__safe_for_unpickle__ = True

def subclass_exception(name, parents, module):
    return type(name, parents, {'__module__': module})

########NEW FILE########
__FILENAME__ = flask-view
# -*- coding: utf-8 -*-
"""
    flask.views
    ~~~~~~~~~~~

    This module provides class-based views inspired by the ones in Django.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from .globals import request


http_method_funcs = frozenset(['get', 'post', 'head', 'options',
                               'delete', 'put', 'trace', 'patch'])


class View(object):
    """Alternative way to use view functions.  A subclass has to implement
    :meth:`dispatch_request` which is called with the view arguments from
    the URL routing system.  If :attr:`methods` is provided the methods
    do not have to be passed to the :meth:`~flask.Flask.add_url_rule`
    method explicitly::

        class MyView(View):
            methods = ['GET']

            def dispatch_request(self, name):
                return 'Hello %s!' % name

        app.add_url_rule('/hello/<name>', view_func=MyView.as_view('myview'))

    When you want to decorate a pluggable view you will have to either do that
    when the view function is created (by wrapping the return value of
    :meth:`as_view`) or you can use the :attr:`decorators` attribute::

        class SecretView(View):
            methods = ['GET']
            decorators = [superuser_required]

            def dispatch_request(self):
                ...

    The decorators stored in the decorators list are applied one after another
    when the view function is created.  Note that you can *not* use the class
    based decorators since those would decorate the view class and not the
    generated view function!
    """

    #: A for which methods this pluggable view can handle.
    methods = None

    #: The canonical way to decorate class-based views is to decorate the
    #: return value of as_view().  However since this moves parts of the
    #: logic from the class declaration to the place where it's hooked
    #: into the routing system.
    #:
    #: You can place one or more decorators in this list and whenever the
    #: view function is created the result is automatically decorated.
    #:
    #: .. versionadded:: 0.8
    decorators = []

    def dispatch_request(self):
        """Subclasses have to override this method to implement the
        actual view function code.  This method is called with all
        the arguments from the URL rule.
        """
        raise NotImplementedError()

    @classmethod
    def as_view(cls, name, *class_args, **class_kwargs):
        """Converts the class into an actual view function that can be used
        with the routing system.  Internally this generates a function on the
        fly which will instantiate the :class:`View` on each request and call
        the :meth:`dispatch_request` method on it.

        The arguments passed to :meth:`as_view` are forwarded to the
        constructor of the class.
        """
        def view(*args, **kwargs):
            self = view.view_class(*class_args, **class_kwargs)
            return self.dispatch_request(*args, **kwargs)

        if cls.decorators:
            view.__name__ = name
            view.__module__ = cls.__module__
            for decorator in cls.decorators:
                view = decorator(view)

        # we attach the view class to the view function for two reasons:
        # first of all it allows us to easily figure out what class-based
        # view this thing came from, secondly it's also used for instantiating
        # the view class so you can actually replace it with something else
        # for testing purposes and debugging.
        view.view_class = cls
        view.__name__ = name
        view.__doc__ = cls.__doc__
        view.__module__ = cls.__module__
        view.methods = cls.methods
        return view


class MethodViewType(type):

    def __new__(cls, name, bases, d):
        rv = type.__new__(cls, name, bases, d)
        if 'methods' not in d:
            methods = set(rv.methods or [])
            for key in d:
                if key in http_method_funcs:
                    methods.add(key.upper())
            # if we have no method at all in there we don't want to
            # add a method list.  (This is for instance the case for
            # the baseclass or another subclass of a base method view
            # that does not introduce new methods).
            if methods:
                rv.methods = sorted(methods)
        return rv


class MethodView(View):
    """Like a regular class-based view but that dispatches requests to
    particular methods.  For instance if you implement a method called
    :meth:`get` it means you will response to ``'GET'`` requests and
    the :meth:`dispatch_request` implementation will automatically
    forward your request to that.  Also :attr:`options` is set for you
    automatically::

        class CounterAPI(MethodView):

            def get(self):
                return session.get('counter', 0)

            def post(self):
                session['counter'] = session.get('counter', 0) + 1
                return 'OK'

        app.add_url_rule('/counter', view_func=CounterAPI.as_view('counter'))
    """
    __metaclass__ = MethodViewType

    def dispatch_request(self, *args, **kwargs):
        meth = getattr(self, request.method.lower(), None)
        # if the request method is HEAD and we don't have a handler for it
        # retry with GET
        if meth is None and request.method == 'HEAD':
            meth = getattr(self, 'get', None)
        assert meth is not None, 'Unimplemented method %r' % request.method
        return meth(*args, **kwargs)

########NEW FILE########
__FILENAME__ = protocol_buffer_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: protocol-buffer.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)




DESCRIPTOR = _descriptor.FileDescriptor(
  name='protocol-buffer.proto',
  package='persons',
  serialized_pb='\n\x15protocol-buffer.proto\x12\x07persons\"\x16\n\x06Person\x12\x0c\n\x04name\x18\x01 \x02(\t')




_PERSON = _descriptor.Descriptor(
  name='Person',
  full_name='persons.Person',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='persons.Person.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=34,
  serialized_end=56,
)

DESCRIPTOR.message_types_by_name['Person'] = _PERSON

class Person(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _PERSON

  # @@protoc_insertion_point(class_scope:persons.Person)


# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = tornado-httpserver
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A non-blocking, single-threaded HTTP server.

Typical applications have little direct interaction with the `HTTPServer`
class except to start a server at the beginning of the process
(and even that is often done indirectly via `tornado.web.Application.listen`).

This module also defines the `HTTPRequest` class which is exposed via
`tornado.web.RequestHandler.request`.
"""

from __future__ import absolute_import, division, with_statement

import Cookie
import logging
import socket
import time

from tornado.escape import utf8, native_str, parse_qs_bytes
from tornado import httputil
from tornado import iostream
from tornado.netutil import TCPServer
from tornado import stack_context
from tornado.util import b, bytes_type

try:
    import ssl  # Python 2.6+
except ImportError:
    ssl = None


class HTTPServer(TCPServer):
    r"""A non-blocking, single-threaded HTTP server.

    A server is defined by a request callback that takes an HTTPRequest
    instance as an argument and writes a valid HTTP response with
    `HTTPRequest.write`. `HTTPRequest.finish` finishes the request (but does
    not necessarily close the connection in the case of HTTP/1.1 keep-alive
    requests). A simple example server that echoes back the URI you
    requested::

        import httpserver
        import ioloop

        def handle_request(request):
           message = "You requested %s\n" % request.uri
           request.write("HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n%s" % (
                         len(message), message))
           request.finish()

        http_server = httpserver.HTTPServer(handle_request)
        http_server.listen(8888)
        ioloop.IOLoop.instance().start()

    `HTTPServer` is a very basic connection handler. Beyond parsing the
    HTTP request body and headers, the only HTTP semantics implemented
    in `HTTPServer` is HTTP/1.1 keep-alive connections. We do not, however,
    implement chunked encoding, so the request callback must provide a
    ``Content-Length`` header or implement chunked encoding for HTTP/1.1
    requests for the server to run correctly for HTTP/1.1 clients. If
    the request handler is unable to do this, you can provide the
    ``no_keep_alive`` argument to the `HTTPServer` constructor, which will
    ensure the connection is closed on every request no matter what HTTP
    version the client is using.

    If ``xheaders`` is ``True``, we support the ``X-Real-Ip`` and ``X-Scheme``
    headers, which override the remote IP and HTTP scheme for all requests.
    These headers are useful when running Tornado behind a reverse proxy or
    load balancer.

    `HTTPServer` can serve SSL traffic with Python 2.6+ and OpenSSL.
    To make this server serve SSL traffic, send the ssl_options dictionary
    argument with the arguments required for the `ssl.wrap_socket` method,
    including "certfile" and "keyfile"::

       HTTPServer(applicaton, ssl_options={
           "certfile": os.path.join(data_dir, "mydomain.crt"),
           "keyfile": os.path.join(data_dir, "mydomain.key"),
       })

    `HTTPServer` initialization follows one of three patterns (the
    initialization methods are defined on `tornado.netutil.TCPServer`):

    1. `~tornado.netutil.TCPServer.listen`: simple single-process::

            server = HTTPServer(app)
            server.listen(8888)
            IOLoop.instance().start()

       In many cases, `tornado.web.Application.listen` can be used to avoid
       the need to explicitly create the `HTTPServer`.

    2. `~tornado.netutil.TCPServer.bind`/`~tornado.netutil.TCPServer.start`:
       simple multi-process::

            server = HTTPServer(app)
            server.bind(8888)
            server.start(0)  # Forks multiple sub-processes
            IOLoop.instance().start()

       When using this interface, an `IOLoop` must *not* be passed
       to the `HTTPServer` constructor.  `start` will always start
       the server on the default singleton `IOLoop`.

    3. `~tornado.netutil.TCPServer.add_sockets`: advanced multi-process::

            sockets = tornado.netutil.bind_sockets(8888)
            tornado.process.fork_processes(0)
            server = HTTPServer(app)
            server.add_sockets(sockets)
            IOLoop.instance().start()

       The `add_sockets` interface is more complicated, but it can be
       used with `tornado.process.fork_processes` to give you more
       flexibility in when the fork happens.  `add_sockets` can
       also be used in single-process servers if you want to create
       your listening sockets in some way other than
       `tornado.netutil.bind_sockets`.

    """
    def __init__(self, request_callback, no_keep_alive=False, io_loop=None,
                 xheaders=False, ssl_options=None, **kwargs):
        self.request_callback = request_callback
        self.no_keep_alive = no_keep_alive
        self.xheaders = xheaders
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options,
                           **kwargs)

    def handle_stream(self, stream, address):
        HTTPConnection(stream, address, self.request_callback,
                       self.no_keep_alive, self.xheaders)


class _BadRequestException(Exception):
    """Exception class for malformed HTTP requests."""
    pass


class HTTPConnection(object):
    """Handles a connection to an HTTP client, executing HTTP requests.

    We parse HTTP headers and bodies, and execute the request callback
    until the HTTP conection is closed.
    """
    def __init__(self, stream, address, request_callback, no_keep_alive=False,
                 xheaders=False):
        self.stream = stream
        self.address = address
        self.request_callback = request_callback
        self.no_keep_alive = no_keep_alive
        self.xheaders = xheaders
        self._request = None
        self._request_finished = False
        # Save stack context here, outside of any request.  This keeps
        # contexts from one request from leaking into the next.
        self._header_callback = stack_context.wrap(self._on_headers)
        self.stream.read_until(b("\r\n\r\n"), self._header_callback)
        self._write_callback = None

    def write(self, chunk, callback=None):
        """Writes a chunk of output to the stream."""
        assert self._request, "Request closed"
        if not self.stream.closed():
            self._write_callback = stack_context.wrap(callback)
            self.stream.write(chunk, self._on_write_complete)

    def finish(self):
        """Finishes the request."""
        assert self._request, "Request closed"
        self._request_finished = True
        if not self.stream.writing():
            self._finish_request()

    def _on_write_complete(self):
        if self._write_callback is not None:
            callback = self._write_callback
            self._write_callback = None
            callback()
        # _on_write_complete is enqueued on the IOLoop whenever the
        # IOStream's write buffer becomes empty, but it's possible for
        # another callback that runs on the IOLoop before it to
        # simultaneously write more data and finish the request.  If
        # there is still data in the IOStream, a future
        # _on_write_complete will be responsible for calling
        # _finish_request.
        if self._request_finished and not self.stream.writing():
            self._finish_request()

    def _finish_request(self):
        if self.no_keep_alive:
            disconnect = True
        else:
            connection_header = self._request.headers.get("Connection")
            if connection_header is not None:
                connection_header = connection_header.lower()
            if self._request.supports_http_1_1():
                disconnect = connection_header == "close"
            elif ("Content-Length" in self._request.headers
                    or self._request.method in ("HEAD", "GET")):
                disconnect = connection_header != "keep-alive"
            else:
                disconnect = True
        self._request = None
        self._request_finished = False
        if disconnect:
            self.stream.close()
            return
        self.stream.read_until(b("\r\n\r\n"), self._header_callback)

    def _on_headers(self, data):
        try:
            data = native_str(data.decode('latin1'))
            eol = data.find("\r\n")
            start_line = data[:eol]
            try:
                method, uri, version = start_line.split(" ")
            except ValueError:
                raise _BadRequestException("Malformed HTTP request line")
            if not version.startswith("HTTP/"):
                raise _BadRequestException("Malformed HTTP version in HTTP Request-Line")
            headers = httputil.HTTPHeaders.parse(data[eol:])

            # HTTPRequest wants an IP, not a full socket address
            if getattr(self.stream.socket, 'family', socket.AF_INET) in (
                socket.AF_INET, socket.AF_INET6):
                # Jython 2.5.2 doesn't have the socket.family attribute,
                # so just assume IP in that case.
                remote_ip = self.address[0]
            else:
                # Unix (or other) socket; fake the remote address
                remote_ip = '0.0.0.0'

            self._request = HTTPRequest(
                connection=self, method=method, uri=uri, version=version,
                headers=headers, remote_ip=remote_ip)

            content_length = headers.get("Content-Length")
            if content_length:
                content_length = int(content_length)
                if content_length > self.stream.max_buffer_size:
                    raise _BadRequestException("Content-Length too long")
                if headers.get("Expect") == "100-continue":
                    self.stream.write(b("HTTP/1.1 100 (Continue)\r\n\r\n"))
                self.stream.read_bytes(content_length, self._on_request_body)
                return

            self.request_callback(self._request)
        except _BadRequestException, e:
            logging.info("Malformed HTTP request from %s: %s",
                         self.address[0], e)
            self.stream.close()
            return

    def _on_request_body(self, data):
        self._request.body = data
        content_type = self._request.headers.get("Content-Type", "")
        if self._request.method in ("POST", "PATCH", "PUT"):
            if content_type.startswith("application/x-www-form-urlencoded"):
                arguments = parse_qs_bytes(native_str(self._request.body))
                for name, values in arguments.iteritems():
                    values = [v for v in values if v]
                    if values:
                        self._request.arguments.setdefault(name, []).extend(
                            values)
            elif content_type.startswith("multipart/form-data"):
                fields = content_type.split(";")
                for field in fields:
                    k, sep, v = field.strip().partition("=")
                    if k == "boundary" and v:
                        httputil.parse_multipart_form_data(
                            utf8(v), data,
                            self._request.arguments,
                            self._request.files)
                        break
                else:
                    logging.warning("Invalid multipart/form-data")
        self.request_callback(self._request)


class HTTPRequest(object):
    """A single HTTP request.

    All attributes are type `str` unless otherwise noted.

    .. attribute:: method

       HTTP request method, e.g. "GET" or "POST"

    .. attribute:: uri

       The requested uri.

    .. attribute:: path

       The path portion of `uri`

    .. attribute:: query

       The query portion of `uri`

    .. attribute:: version

       HTTP version specified in request, e.g. "HTTP/1.1"

    .. attribute:: headers

       `HTTPHeader` dictionary-like object for request headers.  Acts like
       a case-insensitive dictionary with additional methods for repeated
       headers.

    .. attribute:: body

       Request body, if present, as a byte string.

    .. attribute:: remote_ip

       Client's IP address as a string.  If `HTTPServer.xheaders` is set,
       will pass along the real IP address provided by a load balancer
       in the ``X-Real-Ip`` header

    .. attribute:: protocol

       The protocol used, either "http" or "https".  If `HTTPServer.xheaders`
       is set, will pass along the protocol used by a load balancer if
       reported via an ``X-Scheme`` header.

    .. attribute:: host

       The requested hostname, usually taken from the ``Host`` header.

    .. attribute:: arguments

       GET/POST arguments are available in the arguments property, which
       maps arguments names to lists of values (to support multiple values
       for individual names). Names are of type `str`, while arguments
       are byte strings.  Note that this is different from
       `RequestHandler.get_argument`, which returns argument values as
       unicode strings.

    .. attribute:: files

       File uploads are available in the files property, which maps file
       names to lists of :class:`HTTPFile`.

    .. attribute:: connection

       An HTTP request is attached to a single HTTP connection, which can
       be accessed through the "connection" attribute. Since connections
       are typically kept open in HTTP/1.1, multiple requests can be handled
       sequentially on a single connection.
    """
    def __init__(self, method, uri, version="HTTP/1.0", headers=None,
                 body=None, remote_ip=None, protocol=None, host=None,
                 files=None, connection=None):
        self.method = method
        self.uri = uri
        self.version = version
        self.headers = headers or httputil.HTTPHeaders()
        self.body = body or ""
        if connection and connection.xheaders:
            # Squid uses X-Forwarded-For, others use X-Real-Ip
            self.remote_ip = self.headers.get(
                "X-Real-Ip", self.headers.get("X-Forwarded-For", remote_ip))
            if not self._valid_ip(self.remote_ip):
                self.remote_ip = remote_ip
            # AWS uses X-Forwarded-Proto
            self.protocol = self.headers.get(
                "X-Scheme", self.headers.get("X-Forwarded-Proto", protocol))
            if self.protocol not in ("http", "https"):
                self.protocol = "http"
        else:
            self.remote_ip = remote_ip
            if protocol:
                self.protocol = protocol
            elif connection and isinstance(connection.stream,
                                           iostream.SSLIOStream):
                self.protocol = "https"
            else:
                self.protocol = "http"
        self.host = host or self.headers.get("Host") or "127.0.0.1"
        self.files = files or {}
        self.connection = connection
        self._start_time = time.time()
        self._finish_time = None

        self.path, sep, self.query = uri.partition('?')
        arguments = parse_qs_bytes(self.query)
        self.arguments = {}
        for name, values in arguments.iteritems():
            values = [v for v in values if v]
            if values:
                self.arguments[name] = values

    def supports_http_1_1(self):
        """Returns True if this request supports HTTP/1.1 semantics"""
        return self.version == "HTTP/1.1"

    @property
    def cookies(self):
        """A dictionary of Cookie.Morsel objects."""
        if not hasattr(self, "_cookies"):
            self._cookies = Cookie.SimpleCookie()
            if "Cookie" in self.headers:
                try:
                    self._cookies.load(
                        native_str(self.headers["Cookie"]))
                except Exception:
                    self._cookies = {}
        return self._cookies

    def write(self, chunk, callback=None):
        """Writes the given chunk to the response stream."""
        assert isinstance(chunk, bytes_type)
        self.connection.write(chunk, callback=callback)

    def finish(self):
        """Finishes this HTTP request on the open connection."""
        self.connection.finish()
        self._finish_time = time.time()

    def full_url(self):
        """Reconstructs the full URL for this request."""
        return self.protocol + "://" + self.host + self.uri

    def request_time(self):
        """Returns the amount of time it took for this request to execute."""
        if self._finish_time is None:
            return time.time() - self._start_time
        else:
            return self._finish_time - self._start_time

    def get_ssl_certificate(self):
        """Returns the client's SSL certificate, if any.

        To use client certificates, the HTTPServer must have been constructed
        with cert_reqs set in ssl_options, e.g.::

            server = HTTPServer(app,
                ssl_options=dict(
                    certfile="foo.crt",
                    keyfile="foo.key",
                    cert_reqs=ssl.CERT_REQUIRED,
                    ca_certs="cacert.crt"))

        The return value is a dictionary, see SSLSocket.getpeercert() in
        the standard library for more details.
        http://docs.python.org/library/ssl.html#sslsocket-objects
        """
        try:
            return self.connection.stream.socket.getpeercert()
        except ssl.SSLError:
            return None

    def __repr__(self):
        attrs = ("protocol", "host", "method", "uri", "version", "remote_ip",
                 "body")
        args = ", ".join(["%s=%r" % (n, getattr(self, n)) for n in attrs])
        return "%s(%s, headers=%s)" % (
            self.__class__.__name__, args, dict(self.headers))

    def _valid_ip(self, ip):
        try:
            res = socket.getaddrinfo(ip, 0, socket.AF_UNSPEC,
                                     socket.SOCK_STREAM,
                                     0, socket.AI_NUMERICHOST)
            return bool(res)
        except socket.gaierror, e:
            if e.args[0] == socket.EAI_NONAME:
                return False
            raise
        return True

########NEW FILE########
__FILENAME__ = framework
# -*- coding: utf-8 -*-

import os
import sys

TEST_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(TEST_DIR)
LIBS_DIR = os.path.join(ROOT_DIR, "linguist")
sys.path.insert(0, LIBS_DIR)

from unittest import main, TestCase


class LinguistTestBase(TestCase):
    def setUp(self):
        pass

########NEW FILE########
__FILENAME__ = run
# -*- coding: utf-8 -*-

import os
import sys

TEST_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(TEST_DIR)
sys.path.insert(0, ROOT_DIR)

from unittest import main, TestSuite, findTestCases

def get_test_module_names():
    file_names = os.listdir(os.curdir)
    for fn in file_names:
        if fn.startswith('test') and fn.endswith('.py'):
            yield 'tests.' + fn[:-3]

def suite():
    alltests = TestSuite()

    for module_name in get_test_module_names():
        module = __import__(module_name, fromlist=[module_name])
        alltests.addTest(findTestCases(module))

    return alltests


if __name__ == '__main__':
    main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = test_blob
# -*- coding: utf-8 -*-

from os.path import realpath, dirname, join
from pygments.lexers import find_lexer_class
from framework import LinguistTestBase, main
from libs.file_blob import FileBlob
from libs.samples import Samples

DIR = dirname(dirname(realpath(__file__)))
SAMPLES_PATH = join(DIR, "samples")

colorize = """<div class="highlight"><pre><span class="k">module</span> <span class="nn">Foo</span>
<span class="k">end</span>
</pre></div>
"""

colorize_without_wrapper = """<span class="k">module</span> <span class="nn">Foo</span>
<span class="k">end</span>
"""


class TestFileBob(LinguistTestBase):

    def blob(self, name):
        if not name.startswith('/'):
            name = join(SAMPLES_PATH, name)
        return FileBlob(name, SAMPLES_PATH)

    def script_blob(self, name):
        blob = self.blob(name)
        blob.name = 'script'
        return blob

    def test_name(self):
        assert 'foo.rb' == self.blob('foo.rb').name

    def test_mime_type(self):
        assert 'application/postscript' == self.blob('Binary/octocat.ai').mime_type
        assert 'application/x-ruby' == self.blob("Ruby/grit.rb").mime_type
        assert "application/x-sh" == self.blob("Shell/script.sh").mime_type
        assert "application/xml" == self.blob("XML/bar.xml").mime_type
        assert "audio/ogg" == self.blob("Binary/foo.ogg").mime_type
        assert "text/plain" == self.blob("Text/README").mime_type

    def test_content_type(self):
        assert "application/pdf" == self.blob("Binary/foo.pdf").content_type
        assert "audio/ogg" == self.blob("Binary/foo.ogg").content_type
        assert "image/png" == self.blob("Binary/foo.png").content_type
        assert "text/plain; charset=iso-8859-2" == self.blob("Text/README").content_type

    def test_disposition(self):
        assert "attachment; filename=foo+bar.jar" == self.blob("Binary/foo bar.jar").disposition
        assert "attachment; filename=foo.bin" == self.blob("Binary/foo.bin").disposition
        assert "attachment; filename=linguist.gem" == self.blob("Binary/linguist.gem").disposition
        assert "attachment; filename=octocat.ai" == self.blob("Binary/octocat.ai").disposition
        assert "inline" == self.blob("Text/README").disposition
        assert "inline" == self.blob("Text/foo.txt").disposition
        assert "inline" == self.blob("Ruby/grit.rb").disposition
        assert "inline" == self. blob("Binary/octocat.png").disposition

    def test_data(self):
        assert "module Foo\nend\n" == self.blob("Ruby/foo.rb").data

    def test_lines(self):
        assert ["module Foo", "end", ""] == self.blob("Ruby/foo.rb").lines
        assert ["line 1", "line 2", ""] == self.blob("Text/mac.txt").lines

    def test_size(self):
        assert 15 == self.blob("Ruby/foo.rb").size

    def test_loc(self):
        assert 3 == self.blob("Ruby/foo.rb").loc

    def test_sloc(self):
        assert 2 == self.blob("Ruby/foo.rb").sloc

    def test_encoding(self):
        assert "ISO-8859-2" == self.blob("Text/README").encoding
        assert "ISO-8859-1" == self.blob("Text/dump.sql").encoding
        assert "UTF-8" == self.blob("Text/foo.txt").encoding
        assert None == self.blob("Binary/dog.o").encoding

    def test_binary(self):
        # Large blobs aren't loaded
        large_blob = self.blob("git.exe")
        large_blob._data = None
        assert large_blob.is_binary

        assert self.blob("Binary/git.deb").is_binary
        assert self.blob("Binary/git.exe").is_binary
        assert self.blob("Binary/hello.pbc").is_binary
        assert self.blob("Binary/linguist.gem").is_binary
        assert self.blob("Binary/octocat.ai").is_binary
        assert self.blob("Binary/octocat.png").is_binary
        assert self.blob("Binary/zip").is_binary
        assert not self.blob("Text/README").is_binary
        assert not self.blob("Text/file.txt").is_binary
        assert not self.blob("Ruby/foo.rb").is_binary
        assert not self.blob("Perl/script.pl").is_binary

    def test_text(self):
        assert self.blob("Text/README").is_text
        assert self.blob("Text/dump.sql").is_text
        assert self.blob("Text/file.json").is_text
        assert self.blob("Text/file.txt").is_text
        assert self.blob("Text/md").is_text
        assert self.blob("Shell/script.sh").is_text
        assert self.blob("Text/txt").is_text

    def test_image(self):
        assert self.blob("Binary/octocat.gif").is_image
        assert self.blob("Binary/octocat.jpeg").is_image
        assert self.blob("Binary/octocat.jpg").is_image
        assert self.blob("Binary/octocat.png").is_image
        assert not self.blob("Binary/octocat.ai").is_image
        assert not self.blob("Binary/octocat.psd").is_image

    def test_solid(self):
        assert self.blob("Binary/cube.stl").is_solid
        assert self.blob("Text/cube.stl").is_solid

    def test_viewable(self):
        assert self.blob("Text/README").is_viewable
        assert self.blob("Ruby/foo.rb").is_viewable
        assert self.blob("Perl/script.pl").is_viewable
        assert not self.blob("Binary/linguist.gem").is_viewable
        assert not self.blob("Binary/octocat.ai").is_viewable
        assert not self.blob("Binary/octocat.png").is_viewable

    def test_csv(self):
        assert self.blob("Text/cars.csv").is_csv

    def test_pdf(self):
        assert self.blob("Binary/foo.pdf").is_pdf

    def test_generated(self):
        assert not self.blob("Text/README").is_generated

        # Xcode project files
        assert self.blob("XML/MainMenu.xib").is_generated
        assert self.blob("Binary/MainMenu.nib").is_generated
        assert self.blob("XML/project.pbxproj").is_generated

        # Gemfile.locks
        assert self.blob("Gemfile.lock").is_generated

        # Generated .NET Docfiles
        assert self.blob("XML/net_docfile.xml").is_generated

        # Long line
        assert not self.blob("JavaScript/uglify.js").is_generated

        # Inlined JS, but mostly code
        assert not self.blob("JavaScript/json2_backbone.js").is_generated

        # Minified JS
        assert not self.blob("JavaScript/jquery-1.6.1.js").is_generated
        assert self.blob("JavaScript/jquery-1.6.1.min.js").is_generated
        assert self.blob("JavaScript/jquery-1.4.2.min.js").is_generated

        # CoffeeScript-is_generated JS
        # TODO

        # TypeScript-is_generated JS
        # TODO

        # PEG.js-is_generated parsers
        assert self.blob("JavaScript/parser.js").is_generated

        # These examples are too basic to tell
        assert not self.blob("JavaScript/empty.js").is_generated
        assert not self.blob("JavaScript/hello.js").is_generated

        assert self.blob("JavaScript/intro-old.js").is_generated
        assert self.blob("JavaScript/classes-old.js").is_generated

        assert self.blob("JavaScript/intro.js").is_generated
        assert self.blob("JavaScript/classes.js").is_generated

        # Protocol Buffer generated code
        assert self.blob("C++/protocol-buffer.pb.h").is_generated
        assert self.blob("C++/protocol-buffer.pb.cc").is_generated
        assert self.blob("Java/ProtocolBuffer.java").is_generated
        assert self.blob("Python/protocol_buffer_pb2.py").is_generated

        # Generated JNI
        assert self.blob("C/jni_layer.h").is_generated

        # Minified CSS
        assert not self.blob("CSS/bootstrap.css").is_generated
        assert self.blob("CSS/bootstrap.min.css").is_generated

    def test_vendored(self):
        assert not self.blob("Text/README").is_vendored
        assert not self.blob("ext/extconf.rb").is_vendored

        # Dependencies
        assert self.blob("dependencies/windows/headers/GL/glext.h").is_vendored

        # Node depedencies
        assert  self.blob("node_modules/coffee-script/lib/coffee-script.js").is_vendored

        # Rails vendor/
        assert  self.blob("vendor/plugins/will_paginate/lib/will_paginate.rb").is_vendored

        # 'thirdparty' directory
        assert self.blob("thirdparty/lib/main.c").is_vendored

        # C deps
        assert  self.blob("deps/http_parser/http_parser.c").is_vendored
        assert  self.blob("deps/v8/src/v8.h").is_vendored

        # Debian packaging
        assert  self.blob("debian/cron.d").is_vendored

        # Prototype
        assert not self.blob("public/javascripts/application.js").is_vendored
        assert  self.blob("public/javascripts/prototype.js").is_vendored
        assert  self.blob("public/javascripts/effects.js").is_vendored
        assert  self.blob("public/javascripts/controls.js").is_vendored
        assert  self.blob("public/javascripts/dragdrop.js").is_vendored

        # jQuery
        assert  self.blob("jquery.js").is_vendored
        assert  self.blob("public/javascripts/jquery.js").is_vendored
        assert  self.blob("public/javascripts/jquery.min.js").is_vendored
        assert  self.blob("public/javascripts/jquery-1.7.js").is_vendored
        assert  self.blob("public/javascripts/jquery-1.7.min.js").is_vendored
        assert  self.blob("public/javascripts/jquery-1.5.2.js").is_vendored
        assert  self.blob("public/javascripts/jquery-1.6.1.js").is_vendored
        assert  self.blob("public/javascripts/jquery-1.6.1.min.js").is_vendored
        assert  self.blob("public/javascripts/jquery-1.10.1.js").is_vendored
        assert  self.blob("public/javascripts/jquery-1.10.1.min.js").is_vendored
        assert not self.blob("public/javascripts/jquery.github.menu.js").is_vendored

        # jQuery UI
        assert self.blob("themes/ui-lightness/jquery-ui.css").is_vendored
        assert self.blob("themes/ui-lightness/jquery-ui-1.8.22.custom.css").is_vendored
        assert self.blob("themes/ui-lightness/jquery.ui.accordion.css").is_vendored
        assert self.blob("ui/i18n/jquery.ui.datepicker-ar.js").is_vendored
        assert self.blob("ui/i18n/jquery-ui-i18n.js").is_vendored
        assert self.blob("ui/jquery.effects.blind.js").is_vendored
        assert self.blob("ui/jquery-ui-1.8.22.custom.js").is_vendored
        assert self.blob("ui/jquery-ui-1.8.22.custom.min.js").is_vendored
        assert self.blob("ui/jquery-ui-1.8.22.js").is_vendored
        assert self.blob("ui/jquery-ui-1.8.js").is_vendored
        assert self.blob("ui/jquery-ui.min.js").is_vendored
        assert self.blob("ui/jquery.ui.accordion.js").is_vendored
        assert self.blob("ui/minified/jquery.effects.blind.min.js").is_vendored
        assert self.blob("ui/minified/jquery.ui.accordion.min.js").is_vendored

        # MooTools
        assert  self.blob("public/javascripts/mootools-core-1.3.2-full-compat.js").is_vendored
        assert  self.blob("public/javascripts/mootools-core-1.3.2-full-compat-yc.js").is_vendored

        # Dojo
        assert  self.blob("public/javascripts/dojo.js").is_vendored

        # MochiKit
        assert  self.blob("public/javascripts/MochiKit.js").is_vendored

        # YUI
        assert  self.blob("public/javascripts/yahoo-dom-event.js").is_vendored
        assert  self.blob("public/javascripts/yahoo-min.js").is_vendored
        assert  self.blob("public/javascripts/yuiloader-dom-event.js").is_vendored

        # WYS editors
        assert  self.blob("public/javascripts/ckeditor.js").is_vendored
        assert  self.blob("public/javascripts/tiny_mce.js").is_vendored
        assert  self.blob("public/javascripts/tiny_mce_popup.js").is_vendored
        assert  self.blob("public/javascripts/tiny_mce_src.js").is_vendored

        # Fabric
        assert  self.blob("fabfile.py").is_vendored

        # WAF
        assert  self.blob("waf").is_vendored

        # Visual Studio IntelliSense
        assert  self.blob("Scripts/jquery-1.7-vsdoc.js").is_vendored

        # Microsoft Ajax
        assert  self.blob("Scripts/MicrosoftAjax.debug.js").is_vendored
        assert  self.blob("Scripts/MicrosoftAjax.js").is_vendored
        assert  self.blob("Scripts/MicrosoftMvcAjax.debug.js").is_vendored
        assert  self.blob("Scripts/MicrosoftMvcAjax.js").is_vendored
        assert  self.blob("Scripts/MicrosoftMvcValidation.debug.js").is_vendored
        assert  self.blob("Scripts/MicrosoftMvcValidation.js").is_vendored

        # jQuery validation plugin (MS bundles this with asp.net mvc)
        assert  self.blob("Scripts/jquery.validate.js").is_vendored
        assert  self.blob("Scripts/jquery.validate.min.js").is_vendored
        assert  self.blob("Scripts/jquery.validate.unobtrusive.js").is_vendored
        assert  self.blob("Scripts/jquery.validate.unobtrusive.min.js").is_vendored
        assert  self.blob("Scripts/jquery.unobtrusive-ajax.js").is_vendored
        assert  self.blob("Scripts/jquery.unobtrusive-ajax.min.js").is_vendored

        # NuGet Packages
        assert  self.blob("packages/Modernizr.2.0.6/Content/Scripts/modernizr-2.0.6-development-only.js").is_vendored

        # Test fixtures
        assert self.blob("test/fixtures/random.rkt").is_vendored
        assert self.blob("Test/fixtures/random.rkt").is_vendored

        # Cordova/PhoneGap
        assert self.blob("cordova.js").is_vendored
        assert self.blob("cordova.min.js").is_vendored
        assert self.blob("cordova-2.1.0.js").is_vendored
        assert self.blob("cordova-2.1.0.min.js").is_vendored

        # Vagrant
        assert self.blob("Vagrantfile").is_vendored

    def test_language(self):
        def _check_lang(sample):
            blob = self.blob(sample['path'])
            assert blob.language, 'No language for %s' % sample['path']
            assert sample['language'] == blob.language.name, blob.name

        Samples.each(_check_lang)

    def test_lexer(self):
        assert find_lexer_class('Ruby') == self.blob("Ruby/foo.rb").lexer

    def test_colorize(self):
        assert colorize == self.blob("Ruby/foo.rb").colorize()

    def test_colorize_does_skip_minified_files(self):
        assert None == self.blob("JavaScript/jquery-1.6.1.min.js").colorize()

    # Pygments.rb was taking exceeding long on this particular file
    def test_colorize_doesnt_blow_up_with_files_with_high_ratio_of_long_lines(self):
        assert None == self.blob("JavaScript/steelseries-min.js").colorize()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_classifier
# -*- coding: utf-8 -*-

from framework import LinguistTestBase, main
from libs.classifier import Classifier
from libs.tokenizer import Tokenizer
from libs.samples import DATA

TEST_FILE = "../samples/%s"

class TestClassifier(LinguistTestBase):

    def fixture(self, name):
        return open(TEST_FILE % name).read()

    def test_classify(self):
        db = {}
        Classifier.train(db, "Ruby", self.fixture("Ruby/foo.rb"))
        Classifier.train(db, "Objective-C", self.fixture("Objective-C/Foo.h"))
        Classifier.train(db, "Objective-C", self.fixture("Objective-C/Foo.m"))

        rs = Classifier.classify(db, self.fixture("Objective-C/hello.m"))
        assert "Objective-C" == rs[0][0]

        tokens = Tokenizer.tokenize(self.fixture("Objective-C/hello.m"))
        rs = Classifier.classify(db, tokens)
        assert "Objective-C" == rs[0][0]

    def test_restricted_classify(self):
        db = {}
        Classifier.train(db, "Ruby", self.fixture("Ruby/foo.rb"))
        Classifier.train(db, "Objective-C", self.fixture("Objective-C/Foo.h"))
        Classifier.train(db, "Objective-C", self.fixture("Objective-C/Foo.m"))

        rs = Classifier.classify(db, self.fixture("Objective-C/hello.m"), ["Objective-C"])
        assert "Objective-C" == rs[0][0]

        rs = Classifier.classify(db, self.fixture("Objective-C/hello.m"), ["Ruby"])
        assert "Ruby" == rs[0][0]

    def test_instance_classify_empty(self):
        rs = Classifier.classify(DATA, "")
        r = rs[0]
        assert r[1] < 0.5, str(r)

    def test_instance_classify_none(self):
        assert [] == Classifier.classify(DATA, None)

    def test_classify_ambiguous_languages(self):
        #TODO
        """
        Samples.each do |sample|
          language  = Linguist::Language.find_by_name(sample[:language])
          languages = Language.find_by_filename(sample[:path]).map(&:name)
          next unless languages.length > 1

          results = Classifier.classify(Samples::DATA, File.read(sample[:path]), languages)
          assert_equal language.name, results.first[0], "#{sample[:path]}\n#{results.inspect}"
        end
        """

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_language
# -*- coding: utf-8 -*-

from pygments.lexers import find_lexer_class
from framework import LinguistTestBase, main
from libs.language import Language


colorize = """<div class="highlight"><pre><span class="k">def</span> <span class="nf">foo</span>
  <span class="s1">&#39;foo&#39;</span>
<span class="k">end</span>
</pre></div>
"""


class TestLanguage(LinguistTestBase):

    def test_lexer(self):
        assert find_lexer_class('ActionScript 3') == Language['ActionScript'].lexer
        assert find_lexer_class('Bash') == Language['Gentoo Ebuild'].lexer
        assert find_lexer_class('Bash') == Language['Gentoo Eclass'].lexer
        assert find_lexer_class('Bash') == Language['Shell'].lexer
        assert find_lexer_class('C') == Language['OpenCL'].lexer
        assert find_lexer_class('C') == Language['XS'].lexer
        assert find_lexer_class('C++') == Language['C++'].lexer
        assert find_lexer_class('Coldfusion HTML') == Language['ColdFusion'].lexer
        assert find_lexer_class('Coq') == Language['Coq'].lexer
        assert find_lexer_class('FSharp') == Language['F#'].lexer
        assert find_lexer_class('FSharp') == Language['F#'].lexer
        assert find_lexer_class('Fortran') == Language['FORTRAN'].lexer
        assert find_lexer_class('Gherkin') == Language['Cucumber'].lexer
        assert find_lexer_class('Groovy') == Language['Groovy'].lexer
        assert find_lexer_class('HTML') == Language['HTML'].lexer
        assert find_lexer_class('HTML+Django/Jinja') == Language['HTML+Django'].lexer
        assert find_lexer_class('HTML+PHP') == Language['HTML+PHP'].lexer
        assert find_lexer_class('HTTP') == Language['HTTP'].lexer
        assert find_lexer_class('JSON') == Language['JSON'].lexer
        assert find_lexer_class('Java') == Language['ChucK'].lexer
        assert find_lexer_class('Java') == Language['Java'].lexer
        assert find_lexer_class('JavaScript') == Language['JavaScript'].lexer
        assert find_lexer_class('MOOCode') == Language['Moocode'].lexer
        assert find_lexer_class('MuPAD') == Language['mupad'].lexer
        assert find_lexer_class('NASM') == Language['Assembly'].lexer
        assert find_lexer_class('OCaml') == Language['OCaml'].lexer
        assert find_lexer_class('Ooc') == Language['ooc'].lexer
        assert find_lexer_class('OpenEdge ABL') == Language['OpenEdge ABL'].lexer
        assert find_lexer_class('REBOL') == Language['Rebol'].lexer
        assert find_lexer_class('RHTML') == Language['HTML+ERB'].lexer
        assert find_lexer_class('RHTML') == Language['RHTML'].lexer
        assert find_lexer_class('Ruby') == Language['Mirah'].lexer
        assert find_lexer_class('Ruby') == Language['Ruby'].lexer
        assert find_lexer_class('S') == Language['R'].lexer
        assert find_lexer_class('Scheme') == Language['Emacs Lisp'].lexer
        assert find_lexer_class('Scheme') == Language['Nu'].lexer
        assert find_lexer_class('Racket') == Language['Racket'].lexer
        assert find_lexer_class('Scheme') == Language['Scheme'].lexer
        assert find_lexer_class('Standard ML') == Language['Standard ML'].lexer
        assert find_lexer_class('TeX') == Language['TeX'].lexer
        assert find_lexer_class('verilog') == Language['Verilog'].lexer
        assert find_lexer_class('XSLT') == Language['XSLT'].lexer
        assert find_lexer_class('aspx-vb') == Language['ASP'].lexer
        # assert find_lexer_class('haXe') == Language['Haxe'].lexer
        assert find_lexer_class('reStructuredText') == Language['reStructuredText'].lexer

    def test_find_by_alias(self):
        assert Language['ASP'] == Language.find_by_alias('asp')
        assert Language['ASP'] == Language.find_by_alias('aspx')
        assert Language['ASP'] == Language.find_by_alias('aspx-vb')
        assert Language['ActionScript'] == Language.find_by_alias('as3')
        assert Language['ApacheConf'] == Language.find_by_alias('apache')
        assert Language['Assembly'] == Language.find_by_alias('nasm')
        assert Language['Batchfile'] == Language.find_by_alias('bat')
        assert Language['C#'] == Language.find_by_alias('c#')
        assert Language['C#'] == Language.find_by_alias('csharp')
        assert Language['C'] == Language.find_by_alias('c')
        assert Language['C++'] == Language.find_by_alias('c++')
        assert Language['C++'] == Language.find_by_alias('cpp')
        assert Language['CoffeeScript'] == Language.find_by_alias('coffee')
        assert Language['CoffeeScript'] == Language.find_by_alias('coffee-script')
        assert Language['ColdFusion'] == Language.find_by_alias('cfm')
        assert Language['Common Lisp'] == Language.find_by_alias('common-lisp')
        assert Language['Common Lisp'] == Language.find_by_alias('lisp')
        assert Language['Darcs Patch'] == Language.find_by_alias('dpatch')
        assert Language['Dart'] == Language.find_by_alias('dart')
        assert Language['Emacs Lisp'] == Language.find_by_alias('elisp')
        assert Language['Emacs Lisp'] == Language.find_by_alias('emacs')
        assert Language['Emacs Lisp'] == Language.find_by_alias('emacs-lisp')
        assert Language['Gettext Catalog'] == Language.find_by_alias('pot')
        assert Language['HTML'] == Language.find_by_alias('html')
        assert Language['HTML'] == Language.find_by_alias('xhtml')
        assert Language['HTML+ERB'] == Language.find_by_alias('html+erb')
        assert Language['HTML+ERB'] == Language.find_by_alias('erb')
        assert Language['IRC log'] == Language.find_by_alias('irc')
        assert Language['JSON'] == Language.find_by_alias('json')
        assert Language['Java Server Pages'] == Language.find_by_alias('jsp')
        assert Language['Java'] == Language.find_by_alias('java')
        assert Language['JavaScript'] == Language.find_by_alias('javascript')
        assert Language['JavaScript'] == Language.find_by_alias('js')
        assert Language['Literate Haskell'] == Language.find_by_alias('lhs')
        assert Language['Literate Haskell'] == Language.find_by_alias('literate-haskell')
        assert Language['Objective-C'] == Language.find_by_alias('objc')
        assert Language['OpenEdge ABL'] == Language.find_by_alias('openedge')
        assert Language['OpenEdge ABL'] == Language.find_by_alias('progress')
        assert Language['OpenEdge ABL'] == Language.find_by_alias('abl')
        assert Language['Parrot Internal Representation'] == Language.find_by_alias('pir')
        assert Language['PowerShell'] == Language.find_by_alias('posh')
        assert Language['Puppet'] == Language.find_by_alias('puppet')
        assert Language['Pure Data'] == Language.find_by_alias('pure-data')
        assert Language['Raw token data'] == Language.find_by_alias('raw')
        assert Language['Ruby'] == Language.find_by_alias('rb')
        assert Language['Ruby'] == Language.find_by_alias('ruby')
        assert Language['Scheme'] == Language.find_by_alias('scheme')
        assert Language['Shell'] == Language.find_by_alias('bash')
        assert Language['Shell'] == Language.find_by_alias('sh')
        assert Language['Shell'] == Language.find_by_alias('shell')
        assert Language['Shell'] == Language.find_by_alias('zsh')
        assert Language['TeX'] == Language.find_by_alias('tex')
        assert Language['TypeScript'] == Language.find_by_alias('ts')
        assert Language['VimL'] == Language.find_by_alias('vim')
        assert Language['VimL'] == Language.find_by_alias('viml')
        assert Language['reStructuredText'] == Language.find_by_alias('rst')
        assert Language['YAML'] == Language.find_by_alias('yml')

    def test_groups(self):
        # Test a couple identity cases
        assert Language['Perl'] == Language['Perl'].group
        assert Language['Python'] == Language['Python'].group
        assert Language['Ruby'] == Language['Ruby'].group

        # Test a few special groups
        assert Language['Assembly'] == Language['GAS'].group
        assert Language['C'] == Language['OpenCL'].group
        assert Language['Haskell'] == Language['Literate Haskell'].group
        assert Language['Java'] == Language['Java Server Pages'].group
        assert Language['Python'] == Language['Cython'].group
        assert Language['Python'] == Language['NumPy'].group
        assert Language['Shell'] == Language['Batchfile'].group
        assert Language['Shell'] == Language['Gentoo Ebuild'].group
        assert Language['Shell'] == Language['Gentoo Eclass'].group
        assert Language['Shell'] == Language['Tcsh'].group

        # Ensure everyone has a group
        for language in Language.all():
            assert language.group, "%s has no group" % language

    def test_search_term(self):
        assert 'perl' == Language['Perl'].search_term
        assert 'python' == Language['Python'].search_term
        assert 'ruby' == Language['Ruby'].search_term
        assert 'common-lisp' == Language['Common Lisp'].search_term
        assert 'html+erb' == Language['HTML+ERB'].search_term
        assert 'max/msp' == Language['Max'].search_term
        assert 'puppet' == Language['Puppet'].search_term
        assert 'pure-data' == Language['Pure Data'].search_term

        assert 'aspx-vb' == Language['ASP'].search_term
        assert 'as3' == Language['ActionScript'].search_term
        assert 'nasm' == Language['Assembly'].search_term
        assert 'bat' == Language['Batchfile'].search_term
        assert 'csharp' == Language['C#'].search_term
        assert 'cpp' == Language['C++'].search_term
        assert 'cfm' == Language['ColdFusion'].search_term
        assert 'dpatch' == Language['Darcs Patch'].search_term
        assert 'fsharp' == Language['F#'].search_term
        assert 'pot' == Language['Gettext Catalog'].search_term
        assert 'irc' == Language['IRC log'].search_term
        assert 'lhs' == Language['Literate Haskell'].search_term
        assert 'ruby' == Language['Mirah'].search_term
        assert 'raw' == Language['Raw token data'].search_term
        assert 'bash' == Language['Shell'].search_term
        assert 'vim' == Language['VimL'].search_term
        assert 'jsp' == Language['Java Server Pages'].search_term
        assert 'rst' == Language['reStructuredText'].search_term

    def test_popular(self):
        assert Language['Ruby'].is_popular
        assert Language['Perl'].is_popular
        assert Language['Python'].is_popular
        assert Language['Assembly'].is_unpopular
        assert Language['Brainfuck'].is_unpopular

    def test_programming(self):
        assert 'programming' == Language['JavaScript'].type
        assert 'programming' == Language['Perl'].type
        assert 'programming' == Language['PowerShell'].type
        assert 'programming' == Language['Python'].type
        assert 'programming' == Language['Ruby'].type
        assert 'programming' == Language['TypeScript'].type

    def test_markup(self):
        assert 'markup' == Language['HTML'].type

    def test_data(self):
        assert 'data' == Language['YAML'].type

    def test_other(self):
        assert None == Language['Brainfuck'].type
        assert None == Language['Makefile'].type

    def test_searchable(self):
        assert True == Language['Ruby'].is_searchable
        assert False == Language['Gettext Catalog'].is_searchable
        assert False == Language['SQL'].is_searchable

    def test_find_by_name(self):
        assert Language['Ruby'] == Language.name_index['Ruby']

    def test_find_all_by_name(self):
        for language in Language.all():
            assert language == Language[language.name]
            assert language == Language.name_index[language.name]

    def test_find_all_by_alias(self):
        for language in Language.all():
            for name in language.aliases:
                assert language == Language.find_by_alias(name)

    def test_find_by_filename(self):
        assert [Language['Shell']] == Language.find_by_filename('PKGBUILD')
        assert [Language['Ruby']] == Language.find_by_filename('foo.rb')
        assert [Language['Ruby']] == Language.find_by_filename('foo/bar.rb')
        assert [Language['Ruby']] == Language.find_by_filename('Rakefile')
        assert [Language['Ruby']] == Language.find_by_filename('PKGBUILD.rb')
        assert Language['ApacheConf'] == Language.find_by_filename('httpd.conf')[0]
        assert [Language['ApacheConf']] == Language.find_by_filename('.htaccess')
        assert Language['Nginx'] == Language.find_by_filename('nginx.conf')[0]
        assert ['C', 'C++', 'Objective-C'] == sorted(map(lambda l: l.name, Language.find_by_filename('foo.h')))
        assert [] == Language.find_by_filename('rb')
        assert [] == Language.find_by_filename('.rb')
        assert [] == Language.find_by_filename('.nkt')
        assert [Language['Shell']] == Language.find_by_filename('.bashrc')
        assert [Language['Shell']] == Language.find_by_filename('bash_profile')
        assert [Language['Shell']] == Language.find_by_filename('.zshrc')
        assert [Language['Clojure']] == Language.find_by_filename('riemann.config')
        assert [Language['HTML+Django']] == Language.find_by_filename('index.jinja')

    def test_find(self):
        assert 'Ruby' == Language['Ruby'].name
        assert 'Ruby' == Language['ruby'].name
        assert 'C++' == Language['C++'].name
        assert 'C++' == Language['c++'].name
        assert 'C++' == Language['cpp'].name
        assert 'C#' == Language['C#'].name
        assert 'C#' == Language['c#'].name
        assert 'C#' == Language['csharp'].name
        assert None == Language['defunkt']

    def test_name(self):
        assert 'Perl' == Language.name_index['Perl'].name
        assert 'Python' == Language.name_index['Python'].name
        assert 'Ruby' == Language.name_index['Ruby'].name

    def test_escaped_name(self):
        assert 'C' == Language['C'].escaped_name
        assert 'C%23' == Language['C#'].escaped_name
        assert 'C%2B%2B' == Language['C++'].escaped_name
        assert 'Objective-C' == Language['Objective-C'].escaped_name
        assert 'Common%20Lisp' == Language['Common Lisp'].escaped_name

    def test_error_without_name(self):
        self.assertRaises(KeyError, Language, {})

    def test_color(self):
        assert '#701516' == Language['Ruby'].color
        assert '#3581ba' == Language['Python'].color
        assert '#f15501' == Language['JavaScript'].color
        assert '#31859c' == Language['TypeScript'].color

    def test_colors(self):
        Language['Ruby'] in Language.colors()
        Language['Python'] in Language.colors()

    def test_ace_mode(self):
        assert 'c_cpp' == Language['C++'].ace_mode
        assert 'coffee' == Language['CoffeeScript'].ace_mode
        assert 'csharp' == Language['C#'].ace_mode
        assert 'css' == Language['CSS'].ace_mode
        assert 'javascript' == Language['JavaScript'].ace_mode

    def test_ace_modes(self):
        assert Language['Ruby'] in Language.ace_modes()
        assert Language['FORTRAN'] not in Language.ace_modes()

    def test_wrap(self):
        assert False == Language['C'].wrap
        assert True == Language['Markdown'].wrap

    def test_extensions(self):
        assert '.pl' in Language['Perl'].extensions
        assert '.py' in Language['Python'].extensions
        assert '.rb' in Language['Ruby'].extensions

    def test_primary_extension(self):
        assert '.pl' == Language['Perl'].primary_extension
        assert '.py' == Language['Python'].primary_extension
        assert '.rb' == Language['Ruby'].primary_extension
        assert '.js' == Language['JavaScript'].primary_extension
        assert '.coffee' == Language['CoffeeScript'].primary_extension
        assert '.t' == Language['Turing'].primary_extension
        assert '.ts' == Language['TypeScript'].primary_extension

        # This is a nasty requirement, but theres some code in GitHub that
        # expects this. Really want to drop this.
        for language in Language.all():
            assert language.primary_extension, "%s has no primary extension" % language

    def test_eql(self):
        assert Language['Ruby'] == Language['Ruby']
        assert Language['Ruby'] != Language['Python']

    def test_colorize(self):
        assert colorize == Language['Ruby'].colorize("def foo\n  'foo'\nend\n")


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_md5
# -*- coding: utf-8 -*-

from framework import LinguistTestBase, main
from libs.md5 import MD5


class TestMD5(LinguistTestBase):

    def test_hexdigest_string(self):
        assert '51d5ab3bb6ceacfd28fb3435b44df469' == MD5.hexdigest('foo')
        assert 'ed7dd53c428168f872ff18e1a4e7a0cb' == MD5.hexdigest('bar')

    def test_hexdigest_integer(self):
        assert 'ae3b28cde02542f81acce8783245430d' == MD5.hexdigest(1)
        assert '23e7c6cacb8383f878ad093b0027d72b' == MD5.hexdigest(2)

    def test_hexdigest_boolean(self):
        assert 'e62f404a21c359f79b2fac2c7a433eaf' == MD5.hexdigest(True)
        assert '9fa6d44ce6c9c565572d7b5a89e8205f' == MD5.hexdigest(False)

        assert MD5.hexdigest("True") != MD5.hexdigest(True)
        assert MD5.hexdigest("False") != MD5.hexdigest(False)

    def test_hexdigest_none(self):
        assert 'a4179d01d58ec2f9c54faeb814a6a50c' == MD5.hexdigest(None)
        assert MD5.hexdigest("None") != MD5.hexdigest(None)

    def test_hexdigest_list(self):
        assert '10ae9fc7d453b0dd525d0edf2ede7961' == MD5.hexdigest([])
        assert '5b89237adcc067a06bdf636d70d15335' == MD5.hexdigest([1])
        assert '60bbd1bf2ba7b4d7e9306969d693422d' == MD5.hexdigest([1, 2, 3])
        assert '57a3796c2e2be53df52f0731054e2b9c' == MD5.hexdigest([1, 2, [3]])

    def test_hexdigest_dict(self):
        assert 'bb4c374392133719a324ab1ba2799cd6' == MD5.hexdigest({})
        assert '1de63be82bec8f13e58d5b2370846df1' == MD5.hexdigest({'a': 1})
        assert '27fbbe666112c19d5d30a3f39f433649' == MD5.hexdigest({'a': 1, 'b': 2})
        assert MD5.hexdigest({'a': 1, 'b': 2}) == MD5.hexdigest({'b': 2, 'a': 1})


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_repository
# -*- coding: utf-8 -*-

from pygments.lexers import find_lexer_class
from framework import LinguistTestBase, main, ROOT_DIR
from libs.repository import Repository
from libs.language import Language

class TestRepository(LinguistTestBase):

    def repo(self, base_path):
        return Repository.from_directory(base_path)

    def linguist_repo(self):
        return self.repo(ROOT_DIR)

    def test_linguist_language(self):
        assert self.linguist_repo().language == Language.find_by_name('Python')

    def test_linguist_languages(self):
        assert self.linguist_repo().languages[Language.find_by_name('Python')] > 2000

    def test_linguist_size(self):
        assert self.linguist_repo().size > 3000

    def test_binary_override(self):
        assert self.repo(ROOT_DIR + '/samples/Nimrod').language == Language.find_by_name('Nimrod')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_samples
# -*- coding: utf-8 -*-

from framework import LinguistTestBase, main
from libs.samples import DATA


class TestSamples(LinguistTestBase):

    def test_verify(self):
        data = DATA
        assert data['languages_total'] == sum(data['languages'].values())
        assert data['tokens_total'] == sum(data['language_tokens'].values())
        assert data['tokens_total'] == sum(reduce(lambda x, y: x + y,
                                                  [token.values() for token in data['tokens'].values()]))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_tokenizer
# -*- coding: utf-8 -*-

from os.path import join
from framework import LinguistTestBase, main, ROOT_DIR
from libs.tokenizer import Tokenizer


class TestTokenizer(LinguistTestBase):

    def tokenize(self, data='', is_path=None):
        if is_path:
            data = open(join(join(ROOT_DIR, "samples"), str(data))).read()
        return Tokenizer.tokenize(data)

    def test_skip_string_literals(self):
        r = ["print"]
        assert r == self.tokenize('print ""')
        assert r == self.tokenize('print "Josh"')
        assert r == self.tokenize("print 'Josh'")
        assert r == self.tokenize('print "Hello \\"Josh\\""')
        assert r == self.tokenize("print 'Hello \\'Josh\\''")
        assert r == self.tokenize("print \"Hello\", \"Josh\"")
        assert r == self.tokenize("print 'Hello', 'Josh'")
        assert r == self.tokenize("print \"Hello\", \"\", \"Josh\"")
        assert r == self.tokenize("print 'Hello', '', 'Josh'")

    def test_skip_number_literals(self):
        assert ['+'] == self.tokenize('1 + 1')
        assert ['add', '(', ')'] == self.tokenize('add(123, 456)')
        assert ['|'] == self.tokenize('0x01 | 0x10')
        assert ['*'] == self.tokenize('500.42 * 1.0')

    def test_skip_comments(self):
        r1, r2, r3 = ['foo'], ['foo', 'bar'], ['%']
        assert r1 == self.tokenize("foo\n# Comment")
        assert r1 == self.tokenize("foo\n# Comment")
        assert r2 == self.tokenize("foo\n# Comment\nbar")
        assert r1 == self.tokenize("foo\n// Comment")
        assert r1 == self.tokenize("foo /* Comment */")
        assert r1 == self.tokenize("foo /* \nComment \n */")
        assert r1 == self.tokenize("foo <!-- Comment -->")
        assert r1 == self.tokenize("foo {- Comment -}")
        assert r1 == self.tokenize("foo (* Comment *)")
        assert r3 == self.tokenize("2 % 10\n% Comment")

    def test_sgml_tags(self):
        assert ["<html>", "</html>"] == self.tokenize("<html> </html>")
        assert ["<div>", "id", "</div>"] == self.tokenize("<div id></div>")
        assert ["<div>", "id=", "</div>"] == self.tokenize("<div id=foo></div>")
        assert ["<div>", "id", "class", "</div>"] == self.tokenize("<div id class></div>")
        assert ["<div>", "id=", "</div>"] == self.tokenize("<div id=\"foo bar\"></div>")
        assert ["<div>", "id=", "</div>"] == self.tokenize("<div id='foo bar'></div>")
        assert ["<?xml>", "version="] == self.tokenize("<?xml version=\"1.0\"?>")

    def test_operators(self):
        assert ["+"] == self.tokenize("1 + 1")
        assert ["-"] == self.tokenize("1 - 1")
        assert ["*"] == self.tokenize("1 * 1")
        assert ["/"] == self.tokenize("1 / 1")
        assert ["%"] == self.tokenize("2 % 5")
        assert ["&"] == self.tokenize("1 & 1")
        assert ["&&"] == self.tokenize("1 && 1")
        assert ["|"] == self.tokenize("1 | 1")
        assert ["||"] == self.tokenize("1 || 1")
        assert ["<"] == self.tokenize("1 < 0x01")
        assert ["<<"] == self.tokenize("1 << 0x01")

    def test_c_tokens(self):
        r1 = "#ifndef HELLO_H #define HELLO_H void hello ( ) ; #endif".split()
        assert r1 == self.tokenize("C/hello.h", True)
        r2 = "#include <stdio.h> int main ( ) { printf ( ) ; return ; }".split()
        assert r2 == self.tokenize("C/hello.c", True)

    def test_cpp_tokens(self):
        r1 = "class Bar { protected char *name ; public void hello ( ) ; }".split()
        assert r1 == self.tokenize("C++/bar.h", True)
        r2 = "#include <iostream> using namespace std ; int main ( ) { cout << << endl ; }".split()
        assert r2 == self.tokenize("C++/hello.cpp", True)

    def test_objective_c_tokens(self):
        r1 = "#import <Foundation/Foundation.h> @interface Foo NSObject { } @end".split()
        assert r1 == self.tokenize("Objective-C/Foo.h", True)
        r2 = "#import <Cocoa/Cocoa.h> int main ( int argc char *argv [ ] ) { NSLog ( @ ) ; return ; }".split()
        assert r2 == self.tokenize("Objective-C/hello.m", True)
        assert "#import @implementation Foo @end".split() == self.tokenize("Objective-C/Foo.m", True)

    def test_shebang(self):
        assert "SHEBANG#!sh" == self.tokenize("Shell/sh.script!", True)[0]
        assert "SHEBANG#!bash" == self.tokenize("Shell/bash.script!", True)[0]
        assert "SHEBANG#!zsh" == self.tokenize("Shell/zsh.script!", True)[0]
        assert "SHEBANG#!perl" == self.tokenize("Perl/perl.script!", True)[0]
        assert "SHEBANG#!python" == self.tokenize("Python/python.script!", True)[0]
        assert "SHEBANG#!ruby" == self.tokenize("Ruby/ruby.script!", True)[0]
        assert "SHEBANG#!ruby" == self.tokenize("Ruby/ruby2.script!", True)[0]
        assert "SHEBANG#!node" == self.tokenize("JavaScript/js.script!", True)[0]
        assert "SHEBANG#!php" == self.tokenize("PHP/php.script!", True)[0]
        assert "SHEBANG#!escript" == self.tokenize("Erlang/factorial.script!", True)[0]
        assert "echo" == self.tokenize("Shell/invalid-shebang.sh", True)[0]

    def test_javscript_tokens(self):
        r = ["(", "function", "(", ")", "{", "console.log", "(", ")", ";", "}", ")",
             ".call", "(", "this", ")", ";"]
        assert r == self.tokenize("JavaScript/hello.js", True)

    def test_json_tokens(self):
        assert "{ [ ] { } }".split() == self.tokenize("JSON/product.json", True)

    def test_ruby_tokens(self):
        assert "module Foo end".split() == self.tokenize("Ruby/foo.rb", True)
        assert "task default do puts end".split(), self.tokenize("Ruby/filenames/Rakefile", True)


if __name__ == '__main__':
    main()

########NEW FILE########
