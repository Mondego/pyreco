__FILENAME__ = tests
# encoding=utf-8

import twitter_text, sys, os, json, argparse, re
from twitter_text.unicode import force_unicode

narrow_build = True
try:
    unichr(0x20000)
    narrow_build = False
except:
    pass

parser = argparse.ArgumentParser(description = u'Run the integration tests for twitter_text')
parser.add_argument('--ignore-narrow-errors', '-i', help = u'Ignore errors caused by narrow builds', default = False, action = 'store_true')
args = parser.parse_args()

try:
    import yaml
except ImportError:
    raise Exception('You need to install pyaml to run the tests')
# from http://stackoverflow.com/questions/2890146/how-to-force-pyyaml-to-load-strings-as-unicode-objects
from yaml import Loader, SafeLoader
def construct_yaml_str(self, node):
    return self.construct_scalar(node)
Loader.add_constructor(u'tag:yaml.org,2002:str', construct_yaml_str)
SafeLoader.add_constructor(u'tag:yaml.org,2002:str', construct_yaml_str)

try:
    from bs4 import BeautifulSoup
except ImportError:
    try:
        from BeautifulSoup import BeautifulSoup
    except ImportError:
        raise Exception('You need to install BeautifulSoup to run the tests')

def success(text):
    return (u'\033[92m%s\033[0m\n' % text).encode('utf-8')

def error(text):
    return (u'\033[91m%s\033[0m\n' % text).encode('utf-8')

attempted = 0

def assert_equal_without_attribute_order(result, test, failure_message = None):
    global attempted
    attempted += 1
    # Beautiful Soup sorts the attributes for us so we can skip all the hoops the ruby version jumps through
    assert BeautifulSoup(result) == BeautifulSoup(test.get('expected')), error(u'Test %d Failed: %s' % (attempted, test.get('description')))
    sys.stdout.write(success(u'Test %d Passed: %s' % (attempted, test.get('description'))))
    sys.stdout.flush()

def assert_equal(result, test):
    global attempted
    attempted += 1
    assert result == test.get('expected'), error(u'\nTest %d Failed: %s%s' % (attempted, test.get('description'), u'\n%s' % test.get('hits') if test.get('hits') else ''))
    sys.stdout.write(success(u'Test %d Passed: %s' % (attempted, test.get('description'))))
    sys.stdout.flush()

# extractor section
extractor_file = open(os.path.join('twitter-text-conformance', 'extract.yml'), 'r')
extractor_tests = yaml.load(force_unicode(extractor_file.read()))
extractor_file.close()

sys.stdout.write('Testing Extractor\n')
sys.stdout.flush()

for section in extractor_tests.get('tests'):
    sys.stdout.write('\nTesting Extractor: %s\n' % section)
    sys.stdout.flush()
    for test in extractor_tests.get('tests').get(section):
        if (args.ignore_narrow_errors or narrow_build) and section in ['hashtags'] and test.get('description') in ['Hashtag with ideographic iteration mark']:
            sys.stdout.write('Skipping: %s\n' % test.get('description'))
            sys.stdout.flush()
            continue
        extractor = twitter_text.extractor.Extractor(test.get('text'))
        if section == 'mentions':
            assert_equal(extractor.extract_mentioned_screen_names(), test)
        elif section == 'mentions_with_indices':
            assert_equal(extractor.extract_mentioned_screen_names_with_indices(), test)
        elif section == 'mentions_or_lists_with_indices':
            assert_equal(extractor.extract_mentions_or_lists_with_indices(), test)
        elif section == 'replies':
            assert_equal(extractor.extract_reply_screen_name(), test)
        elif section == 'urls':
            assert_equal(extractor.extract_urls(), test)
        elif section == 'urls_with_indices':
            assert_equal(extractor.extract_urls_with_indices(), test)
        elif section == 'hashtags':
            assert_equal(extractor.extract_hashtags(), test)
        elif section == 'cashtags':
            assert_equal(extractor.extract_cashtags(), test)
        elif section == 'hashtags_with_indices':
            assert_equal(extractor.extract_hashtags_with_indices(), test)
        elif section == 'cashtags_with_indices':
            assert_equal(extractor.extract_cashtags_with_indices(), test)

# autolink section
autolink_file = open(os.path.join('twitter-text-conformance', 'autolink.yml'), 'r')
autolink_tests = yaml.load(force_unicode(autolink_file.read()))
autolink_file.close()

sys.stdout.write('\nTesting Autolink\n')
sys.stdout.flush()

autolink_options = {'suppress_no_follow': True}

for section in autolink_tests.get('tests'):
    sys.stdout.write('\nTesting Autolink: %s\n' % section)
    for test in autolink_tests.get('tests').get(section):
        if (args.ignore_narrow_errors or narrow_build) and section in ['hashtags'] and test.get('description') in ['Autolink a hashtag containing ideographic iteration mark']:
            sys.stdout.write('Skipping: %s\n' % test.get('description'))
            sys.stdout.flush()
            continue
        autolink = twitter_text.autolink.Autolink(test.get('text'))
        if section == 'usernames':
            assert_equal_without_attribute_order(autolink.auto_link_usernames_or_lists(autolink_options), test)
        elif section == 'cashtags':
            assert_equal_without_attribute_order(autolink.auto_link_cashtags(autolink_options), test)
        elif section == 'urls':
            assert_equal_without_attribute_order(autolink.auto_link_urls(autolink_options), test)
        elif section == 'hashtags':
            assert_equal_without_attribute_order(autolink.auto_link_hashtags(autolink_options), test)
        elif section == 'all':
            assert_equal_without_attribute_order(autolink.auto_link(autolink_options), test)
        elif section == 'lists':
            assert_equal_without_attribute_order(autolink.auto_link_usernames_or_lists(autolink_options), test)
        elif section == 'json':
            assert_equal_without_attribute_order(autolink.auto_link_with_json(json.loads(test.get('json')), autolink_options), test)

# hit_highlighting section
hit_highlighting_file = open(os.path.join('twitter-text-conformance', 'hit_highlighting.yml'), 'r')
hit_highlighting_tests = yaml.load(force_unicode(hit_highlighting_file.read()))
hit_highlighting_file.close()

sys.stdout.write('\nTesting Hit Highlighting\n')
sys.stdout.flush()

for section in hit_highlighting_tests.get('tests'):
    sys.stdout.write('\nTesting Hit Highlighting: %s\n' % section)
    for test in hit_highlighting_tests.get('tests').get(section):
        hit_highlighter = twitter_text.highlighter.HitHighlighter(test.get('text'))
        if section == 'plain_text':
            assert_equal(hit_highlighter.hit_highlight(hits = test.get('hits')), test)
        elif section == 'with_links':
            assert_equal_without_attribute_order(hit_highlighter.hit_highlight(hits = test.get('hits')), test)

# validation section
validation_tested = False
validate_tests = None
try:
    validate_file = open(os.path.join('twitter-text-conformance', 'validate.yml'), 'r')
    validate_file_contents = validate_file.read()
    validate_tests = yaml.load(re.sub(ur'\\n', '\n', validate_file_contents.encode('unicode-escape')))
    validate_file.close()
except ValueError:
    sys.stdout.write('\nValidation tests were skipped because of wide character issues\n')
    sys.stdout.flush()

if validate_tests:
    sys.stdout.write('\nTesting Validation\n')
    sys.stdout.flush()

    for section in validate_tests.get('tests'):
        sys.stdout.write('\nTesting Validation: %s\n' % section)
        for test in validate_tests.get('tests').get(section):
            validator = twitter_text.validation.Validation(test.get('text'))
            if section == 'tweets':
                assert_equal(not validator.tweet_invalid(), test)
            elif section == 'usernames':
                assert_equal(validator.valid_username(), test)
            elif section == 'lists':
                assert_equal(validator.valid_list(), test)
            elif section == 'hashtags':
                assert_equal(validator.valid_hashtag(), test)
            elif section == 'urls':
                assert_equal(validator.valid_url(), test)

sys.stdout.write(u'\033[0m-------\n\033[92m%d tests passed.\033[0m\n' % attempted)
sys.stdout.flush()
sys.exit(os.EX_OK)
########NEW FILE########
__FILENAME__ = autolink
# encoding=utf-8

import re, cgi

from twitter_text.regex import REGEXEN
from twitter_text.unicode import force_unicode
from twitter_text.extractor import Extractor

# Default CSS class for auto-linked lists
DEFAULT_LIST_CLASS = "tweet-url list-slug"
# Default CSS class for auto-linked usernames
DEFAULT_USERNAME_CLASS = "tweet-url username"
# Default CSS class for auto-linked hashtags
DEFAULT_HASHTAG_CLASS = "tweet-url hashtag"
# Default CSS class for auto-linked cashtags
DEFAULT_CASHTAG_CLASS = "tweet-url cashtag"

# Default URL base for auto-linked usernames
DEFAULT_USERNAME_URL_BASE = "https://twitter.com/"
# Default URL base for auto-linked lists
DEFAULT_LIST_URL_BASE = "https://twitter.com/"
# Default URL base for auto-linked hashtags
DEFAULT_HASHTAG_URL_BASE = "https://twitter.com/#!/search?q=%23"
# Default URL base for auto-linked cashtags
DEFAULT_CASHTAG_URL_BASE = "https://twitter.com/#!/search?q=%24"

# Default attributes for invisible span tag
DEFAULT_INVISIBLE_TAG_ATTRS = "style='position:absolute;left:-9999px;'"

DEFAULT_OPTIONS = {
  'list_class':             DEFAULT_LIST_CLASS,
  'username_class':         DEFAULT_USERNAME_CLASS,
  'hashtag_class':          DEFAULT_HASHTAG_CLASS,
  'cashtag_class':          DEFAULT_CASHTAG_CLASS,

  'username_url_base':      DEFAULT_USERNAME_URL_BASE,
  'list_url_base':          DEFAULT_LIST_URL_BASE,
  'hashtag_url_base':       DEFAULT_HASHTAG_URL_BASE,
  'cashtag_url_base':       DEFAULT_CASHTAG_URL_BASE,

  'invisible_tag_attrs':    DEFAULT_INVISIBLE_TAG_ATTRS,
}

OPTIONS_NOT_ATTRIBUTES = (
    'url_class',
    'list_class',
    'username_class',
    'hashtag_class',
    'cashtag_class',
    'username_url_base',
    'list_url_base',
    'hashtag_url_base',
    'cashtag_url_base',
    'username_url_transform',
    'list_url_transform',
    'hashtag_url_transform',
    'cashtag_url_transform',
    'link_url_transform',
    'username_include_symbol',
    'suppress_lists',
    'suppress_no_follow',
    'url_entities',
    'invisible_tag_attrs',
    'symbol_tag',
    'text_with_symbol_tag',
    'url_target',
    'link_attribute_transform',
    'link_text_transform',
)

HTML_ENTITIES = {
  '&': '&amp;',
  '>': '&gt;',
  '<': '&lt;',
  '"': '&quot;',
  "'": '&#39;',
}

BOOLEAN_ATTRIBUTES = (
    'disabled', 
    'readonly',
    'multiple',
    'checked',
)

def default_transform(entity, text):
    return text

class Autolink(object):
    def __init__(self, text, **kwargs):
        self.text = force_unicode(text)
        self.parent = kwargs.get('parent', False)
        self.extractor = Extractor(self.text)

    def auto_link_with_json(self, json_obj, options = {}):
        # concantenate entities
        entities = []
        if 'entities' in json_obj:
            json_obj = json_obj.get('entities')
        for key in json_obj:
            if type(json_obj[key]) == list:
                entities = entities + json_obj[key]

        # map JSON entity to twitter_text entity
        for entity in entities:
            if 'text' in entity:
                entity['hashtag'] = entity.get('text')

        return self.auto_link_entities(entities, options)

    def auto_link_entities(self, entities = [], options = {}):
        if not self.text:
            return self.text

        # NOTE deprecate these attributes not options keys in options hash, then use html_attrs
        options = dict(DEFAULT_OPTIONS.items() + options.items())
        options['html_attrs'] = self._extract_html_attrs_from_options(options)
        if not options.get('suppress_no_follow', False):
            options['html_attrs']['rel'] = "nofollow"

        entities.sort(key = lambda entity: entity['indices'][0], reverse = True)
        chars = self.text

        for entity in entities:
            if 'url' in entity:
                chars = self._link_to_url(entity, chars, options)
            elif 'hashtag' in entity:
                chars = self._link_to_hashtag(entity, chars, options)
            elif 'screen_name' in entity:
                chars = self._link_to_screen_name(entity, chars, options)
            elif 'cashtag' in entity:
                chars = self._link_to_cashtag(entity, chars, options)

        return chars

    def auto_link(self, options = {}):
        """
        Add <a></a> tags around the usernames, lists, hashtags and URLs in the provided text.
        The <a> tags can be controlled with the following entries in the options hash.
        Also any elements in the options hash will be converted to HTML attributes
        and place in the <a> tag.

        @url_class                  class to add to url <a> tags
        @list_class                 class to add to list <a> tags
        @username_class             class to add to username <a> tags
        @hashtag_class              class to add to hashtag <a> tags
        @cashtag_class              class to add to cashtag <a> tags
        @username_url_base          the value for href attribute on username links. The @username (minus the @) will be appended at the end of this.
        @list_url_base              the value for href attribute on list links. The @username/list (minus the @) will be appended at the end of this.
        @hashtag_url_base           the value for href attribute on hashtag links. The #hashtag (minus the #) will be appended at the end of this.
        @cashtag_url_base           the value for href attribute on cashtag links. The $cashtag (minus the $) will be appended at the end of this.
        @invisible_tag_attrs        HTML attribute to add to invisible span tags
        @username_include_symbol    place the @ symbol within username and list links
        @suppress_lists             disable auto-linking to lists
        @suppress_no_follow         do not add rel="nofollow" to auto-linked items
        @symbol_tag                 tag to apply around symbol (@, #, $) in username / hashtag / cashtag links
        @text_with_symbol_tag       tag to apply around text part in username / hashtag / cashtag links
        @url_target                 the value for target attribute on URL links.
        @link_attribute_transform   function to modify the attributes of a link based on the entity. called with |entity, attributes| params, and should modify the attributes hash.
        @link_text_transform        function to modify the text of a link based on the entity. called with (entity, text) params, and should return a modified text.
        """
        return self.auto_link_entities(self.extractor.extract_entities_with_indices({'extract_url_without_protocol': False}), options)

    def auto_link_usernames_or_lists(self, options = {}):
        """
        Add <a></a> tags around the usernames and lists in the provided text. The
        <a> tags can be controlled with the following entries in the options hash.
        Also any elements in the options hash will be converted to HTML attributes
        and place in the <a> tag.

        @list_class                 class to add to list <a> tags
        @username_class             class to add to username <a> tags
        @username_url_base          the value for href attribute on username links. The @username (minus the @) will be appended at the end of this.
        @list_url_base              the value for href attribute on list links. The @username/list (minus the @) will be appended at the end of this.
        @username_include_symbol    place the @ symbol within username and list links
        @suppress_lists             disable auto-linking to lists
        @suppress_no_follow         do not add rel="nofollow" to auto-linked items
        @symbol_tag                 tag to apply around symbol (@, #, $) in username / hashtag / cashtag links
        @text_with_symbol_tag       tag to apply around text part in username / hashtag / cashtag links
        @link_attribute_transform   function to modify the attributes of a link based on the entity. called with (entity, attributes) params, and should modify the attributes hash.
        @link_text_transform        function to modify the text of a link based on the entity. called with (entity, text) params, and should return a modified text.
        """
        return self.auto_link_entities(self.extractor.extract_mentions_or_lists_with_indices(), options)

    def auto_link_hashtags(self, options = {}):
        """
        Add <a></a> tags around the hashtags in the provided text.
        The <a> tags can be controlled with the following entries in the options hash.
        Also any elements in the options hash will be converted to HTML attributes
        and place in the <a> tag.

        @hashtag_class              class to add to hashtag <a> tags
        @hashtag_url_base           the value for href attribute. The hashtag text (minus the #) will be appended at the end of this.
        @suppress_no_follow         do not add rel="nofollow" to auto-linked items
        @symbol_tag                 tag to apply around symbol (@, #, $) in username / hashtag / cashtag links
        @text_with_symbol_tag       tag to apply around text part in username / hashtag / cashtag links
        @link_attribute_transform   function to modify the attributes of a link based on the entity. called with (entity, attributes) params, and should modify the attributes hash.
        @link_text_transform        function to modify the text of a link based on the entity. called with (entity, text) params, and should return a modified text.
        """
        return self.auto_link_entities(self.extractor.extract_hashtags_with_indices(), options)

    def auto_link_cashtags(self, options = {}):
        """
        Add <a></a> tags around the cashtags in the provided text.
        The <a> tags can be controlled with the following entries in the options hash.
        Also any elements in the options hash will be converted to HTML attributes
        and place in the <a> tag.

        @cashtag_class:: class to add to cashtag <a> tags
        @cashtag_url_base           the value for href attribute. The cashtag text (minus the $) will be appended at the end of this.
        @suppress_no_follow         do not add rel="nofollow" to auto-linked items
        @symbol_tag                 tag to apply around symbol (@, #, $) in username / hashtag / cashtag links
        @text_with_symbol_tag       tag to apply around text part in username / hashtag / cashtag links
        @link_attribute_transform   function to modify the attributes of a link based on the entity. called with (entity, attributes) params, and should modify the attributes hash.
        @link_text_transform        function to modify the text of a link based on the entity. called with (entity, text) params, and should return a modified text.
        """
        return self.auto_link_entities(self.extractor.extract_cashtags_with_indices(), options)

    def auto_link_urls(self, options = {}):
        """
        Add <a></a> tags around the URLs in the provided text.
        The <a> tags can be controlled with the following entries in the options hash.
        Also any elements in the options hash will be converted to HTML attributes
        and place in the <a> tag.

        @url_class                  class to add to url <a> tags
        @invisible_tag_attrs        HTML attribute to add to invisible span tags
        @suppress_no_follow         do not add rel="nofollow" to auto-linked items
        @symbol_tag                 tag to apply around symbol (@, #, $) in username / hashtag / cashtag links
        @text_with_symbol_tag       tag to apply around text part in username / hashtag / cashtag links
        @url_target                 the value for target attribute on URL links.
        @link_attribute_transform   function to modify the attributes of a link based on the entity. called with (entity, attributes) params, and should modify the attributes hash.
        @link_text_transform        function to modify the text of a link based on the entity. called with (entity, text) params, and should return a modified text.
        """
        return self.auto_link_entities(self.extractor.extract_urls_with_indices({'extract_url_without_protocol': False}), options)

    # begin private methods
    def _html_escape(self, text):
        for char in HTML_ENTITIES:
            text = text.replace(char, HTML_ENTITIES[char])
        return text

    def _extract_html_attrs_from_options(self, options = {}):
        html_attrs = options.get('html_attrs', {})
        options = options.copy()
        if 'html_attrs' in options:
            del(options['html_attrs'])
        for option in options.keys():
            if not option in OPTIONS_NOT_ATTRIBUTES:
                html_attrs[option] = options[option]
        return html_attrs

    def _url_entities_hash(self, url_entities):
        entities = {}
        for entity in url_entities:
            entities[entity.get('url')] = entity
        return entities

    def _link_to_url(self, entity, chars, options = {}):
        url = entity.get('url')

        href = options.get('link_url_transform', lambda x: x)(url)

        # NOTE auto link to urls do not use any default values and options
        # like url_class but use suppress_no_follow.
        html_attrs = self._extract_html_attrs_from_options(options)
        if options.get('url_class'):
            html_attrs['class'] = options.get('url_class')

        # add target attribute only if @url_target is specified
        if options.get('url_target'):
            html_attrs['target'] = options.get('url_target')

        url_entities = self._url_entities_hash(options.get('url_entities', {}))

        # use entity from @url_entities if available
        url_entity = url_entities.get(url, entity)
        if url_entity.get('display_url'):
            html_attrs['title'] = url_entity.get('expanded_url')
            link_text = self._link_url_with_entity(url_entity, options)
        else:
            link_text = self._html_escape(url)

        link = self._link_to_text(entity, link_text, href, html_attrs, options)
        return chars[:entity['indices'][0]] + link + chars[entity['indices'][1]:]

    def _link_url_with_entity(self, entity, options = {}):
        """
        Goal: If a user copies and pastes a tweet containing t.co'ed link, the resulting paste
        should contain the full original URL (expanded_url), not the display URL.

        Method: Whenever possible, we actually emit HTML that contains expanded_url, and use
        font-size:0 to hide those parts that should not be displayed (because they are not part of display_url).
        Elements with font-size:0 get copied even though they are not visible.
        Note that display:none doesn't work here. Elements with display:none don't get copied.

        Additionally, we want to *display* ellipses, but we don't want them copied.  To make this happen we
        wrap the ellipses in a tco-ellipsis class and provide an onCopy handler that sets display:none on
        everything with the tco-ellipsis class.

        Exception: pic.twitter.com images, for which expandedUrl = "https://twitter.com/#!/username/status/1234/photo/1
        For those URLs, display_url is not a substring of expanded_url, so we don't do anything special to render the elided parts.
        For a pic.twitter.com URL, the only elided part will be the "https://", so this is fine.
        """
        display_url = entity.get('display_url').decode('utf-8')
        expanded_url = entity.get('expanded_url')
        invisible_tag_attrs = options.get('invisible_tag_attrs', DEFAULT_INVISIBLE_TAG_ATTRS)

        display_url_sans_ellipses = re.sub(ur'…', u'', display_url)

        if expanded_url.find(display_url_sans_ellipses) > -1:
            before_display_url, after_display_url = expanded_url.split(display_url_sans_ellipses, 2)
            preceding_ellipsis = re.search(ur'\A…', display_url)
            following_ellipsis = re.search(ur'…\z', display_url)
            if preceding_ellipsis is not None:
                preceding_ellipsis = preceding_ellipsis.group()
            else:
                preceding_ellipsis = ''
            if following_ellipsis is not None:
                following_ellipsis = following_ellipsis.group()
            else:
                following_ellipsis = ''

            # As an example: The user tweets "hi http://longdomainname.com/foo"
            # This gets shortened to "hi http://t.co/xyzabc", with display_url = "…nname.com/foo"
            # This will get rendered as:
            # <span class='tco-ellipsis'> <!-- This stuff should get displayed but not copied -->
            #   …
            #   <!-- There's a chance the onCopy event handler might not fire. In case that happens,
            #        we include an &nbsp; here so that the … doesn't bump up against the URL and ruin it.
            #        The &nbsp; is inside the tco-ellipsis span so that when the onCopy handler *does*
            #        fire, it doesn't get copied.  Otherwise the copied text would have two spaces in a row,
            #        e.g. "hi  http://longdomainname.com/foo".
            #   <span style='font-size:0'>&nbsp;</span>
            # </span>
            # <span style='font-size:0'>  <!-- This stuff should get copied but not displayed -->
            #   http://longdomai
            # </span>
            # <span class='js-display-url'> <!-- This stuff should get displayed *and* copied -->
            #   nname.com/foo
            # </span>
            # <span class='tco-ellipsis'> <!-- This stuff should get displayed but not copied -->
            #   <span style='font-size:0'>&nbsp;</span>
            #   …
            # </span>

            return u"<span class='tco-ellipsis'>%s<span %s>&nbsp;</span></span><span %s>%s</span><span class='js-display-url'>%s</span><span %s>%s</span><span class='tco-ellipsis'><span %s>&nbsp;</span>%s</span>" % (preceding_ellipsis, invisible_tag_attrs, invisible_tag_attrs, self._html_escape(before_display_url), self._html_escape(display_url_sans_ellipses), invisible_tag_attrs, self._html_escape(after_display_url), invisible_tag_attrs, following_ellipsis)
        else:
            return self._html_escape(display_url)

    def _link_to_hashtag(self, entity, chars, options = {}):
        hashchar = chars[entity['indices'][0]]
        hashtag = entity['hashtag']
        hashtag_class = options.get('hashtag_class')

        if REGEXEN['rtl_chars'].search(hashtag):
            hashtag_class += ' rtl'

        href = options.get('hashtag_url_transform', lambda ht: u'%s%s' % (options.get('hashtag_url_base'), ht))(hashtag)

        html_attrs = {}
        html_attrs.update(options.get('html_attrs', {}))
        html_attrs = {
            'class':    hashtag_class,
            'title':    u'#%s' % hashtag,
        }

        link = self._link_to_text_with_symbol(entity, hashchar, hashtag, href, html_attrs, options)
        return chars[:entity['indices'][0]] + link + chars[entity['indices'][1]:]

    def _link_to_cashtag(self, entity, chars, options = {}):
        dollar = chars[entity['indices'][0]]
        cashtag = entity['cashtag']

        href = options.get('cashtag_url_transform', lambda ct: u'%s%s' % (options.get('cashtag_url_base'), ct))(cashtag)

        html_attrs = {
            'class': options.get('cashtag_class'),
            'title': u'$%s' % cashtag
        }
        html_attrs.update(options.get('html_attrs', {}))

        link = self._link_to_text_with_symbol(entity, dollar, cashtag, href, html_attrs, options)
        return chars[:entity['indices'][0]] + link + chars[entity['indices'][1]:]

    def _link_to_screen_name(self, entity, chars, options = {}):
        name = u'%s%s' % (entity['screen_name'], entity.get('list_slug') or '')
        chunk = options.get('link_text_transform', default_transform)(entity, name)
        name = name.lower()

        at = chars[entity['indices'][0]]

        html_attrs = options.get('html_attrs', {}).copy()
        if 'title' in html_attrs:
            del(html_attrs['title'])

        if entity.get('list_slug') and not options.get('supress_lists'):
            href = options.get('list_url_transform', lambda sn: u'%s%s' % (options.get('list_url_base'), sn))(name)
            html_attrs['class'] = options.get('list_class')
        else:
            href = options.get('username_url_transform', lambda sn: u'%s%s' % (options.get('username_url_base'), sn))(name)
            html_attrs['class'] = options.get('username_class')

        link = self._link_to_text_with_symbol(entity, at, chunk, href, html_attrs, options)
        return chars[:entity['indices'][0]] + link + chars[entity['indices'][1]:]

    def _link_to_text_with_symbol(self, entity, symbol, text, href, attributes = {}, options = {}):
        tagged_symbol = u'<%s>%s</%s>' % (options.get('symbol_tag'), symbol, options.get('symbol_tag')) if options.get('symbol_tag') else symbol
        text = self._html_escape(text)
        tagged_text = u'<%s>%s</%s>' % (options.get('text_with_symbol_tag'), text, options.get('text_with_symbol_tag')) if options.get('text_with_symbol_tag') else text
        if options.get('username_include_symbol') or not REGEXEN['at_signs'].match(symbol):
            return u'%s' % self._link_to_text(entity, tagged_symbol + tagged_text, href, attributes, options)
        else:
            return u'%s%s' % (tagged_symbol, self._link_to_text(entity, tagged_text, href, attributes, options))

    def _link_to_text(self, entity, text, href, attributes = {}, options = {}):
        attributes['href'] = href
        if options.get('link_attribute_transform'):
            attributes = options.get('link_attribute_transform')(entity, attributes)
        text = options.get('link_text_transform', default_transform)(entity, text)
        return u'<a %s>%s</a>' % (self._tag_attrs(attributes), text)

    def _tag_attrs(self, attributes = {}):
        attrs = []
        for key in sorted(attributes.keys()):
            value = attributes[key]
            if key in BOOLEAN_ATTRIBUTES:
                attrs.append(key)
                continue
            if type(value) == list:
                value = u' '.join(value)
            attrs.append(u'%s="%s"' % (self._html_escape(key), self._html_escape(value)))

        return u' '.join(attrs)
########NEW FILE########
__FILENAME__ = extractor
# encoding=utf-8

from twitter_text.regex import REGEXEN
from twitter_text.unicode import force_unicode

class Extractor(object):
    """
    A module for including Tweet parsing in a class. This module provides function for the extraction and processing
    of usernames, lists, URLs and hashtags.
    """
    
    def __init__(self, text):
        self.text = force_unicode(text)

    def _remove_overlapping_entities(self, entities):
        """
        Remove overlapping entities.
        This returns a new list with no overlapping entities.
        """

        # sort by start index
        entities.sort(key = lambda entity: entity['indices'][0])

        # remove duplicates
        prev    =   None
        for entity in [e for e in entities]:
            if prev and prev['indices'][1] > entity['indices'][0]:
                entities.remove(entity)
            else:
                prev    =   entity
        return entities

    def extract_entities_with_indices(self, options = {}, transform = lambda x: x):
        """
        Extracts all usernames, lists, hashtags and URLs  in the Tweet text
        along with the indices for where the entity ocurred
        If the text is None or contains no entity an empty list
        will be returned.

        If a transform is given then it will be called for each entity.
        """
        if not self.text:
            return []

        # extract all entities
        entities    =   self.extract_urls_with_indices(options) + \
                        self.extract_hashtags_with_indices({'check_url_overlap': False}) + \
                        self.extract_mentions_or_lists_with_indices() + \
                        self.extract_cashtags_with_indices()

        entities    =   self._remove_overlapping_entities(entities)

        for entity in entities:
            entity  =   transform(entity)

        return entities

    def extract_mentioned_screen_names(self, transform = lambda x: x):
        """
        Extracts a list of all usernames mentioned in the Tweet text. If the
        text is None or contains no username mentions an empty list
        will be returned.

        If a transform is given then it will be called for each username.
        """
        return [transform(mention['screen_name']) for mention in self.extract_mentioned_screen_names_with_indices()]

    def extract_mentioned_screen_names_with_indices(self, transform = lambda x: x):
        """
        Extracts a list of all usernames mentioned in the Tweet text
        along with the indices for where the mention ocurred.  If the
        text is None or contains no username mentions, an empty list
        will be returned.

        If a transform is given, then it will be called with each username, the start
        index, and the end index in the text.
        """
        if not self.text:
            return []

        possible_screen_names = []
        for match in self.extract_mentions_or_lists_with_indices():
            if not match['list_slug']:
                possible_screen_names.append({
                    'screen_name':  transform(match['screen_name']),
                    'indices':      match['indices']
                })
        return possible_screen_names

    def extract_mentions_or_lists_with_indices(self, transform = lambda x: x):
        """
        Extracts a list of all usernames or lists mentioned in the Tweet text
        along with the indices for where the mention ocurred.  If the
        text is None or contains no username or list mentions, an empty list
        will be returned.

        If a transform is given, then it will be called with each username, list slug, the start
        index, and the end index in the text. The list_slug will be an empty stirng
        if this is a username mention.
        """
        if not REGEXEN['at_signs'].search(self.text):
            return []

        possible_entries    =   []
        for match in REGEXEN['valid_mention_or_list'].finditer(self.text):
            try:
                after = self.text[match.end()]
            except IndexError:
                # the mention was the last character in the string
                after = None
            if after and REGEXEN['end_mention_match'].match(after) or match.groups()[2].find('http') == 0:
                continue
            possible_entries.append({
                'screen_name':  transform(match.groups()[2]),
                'list_slug':    match.groups()[3] or '',
                'indices':      [match.start() + len(match.groups()[0]), match.end()]
            })

        return possible_entries
        
    def extract_reply_screen_name(self, transform = lambda x: x):
        """
        Extracts the username username replied to in the Tweet text. If the
        text is None or is not a reply None will be returned.

        If a transform is given then it will be called with the username replied to (if any)
        """
        if not self.text:
            return None

        possible_screen_name = REGEXEN['valid_reply'].match(self.text)
        if possible_screen_name is not None:
            if possible_screen_name.group(1).find('http') > -1:
                possible_screen_name = None
            else:
                possible_screen_name = transform(possible_screen_name.group(1))
        return possible_screen_name
        
    def extract_urls(self, transform = lambda x: x):
        """
        Extracts a list of all URLs included in the Tweet text. If the
        text is None or contains no URLs an empty list
        will be returned.

        If a transform is given then it will be called for each URL.
        """
        return [transform(url['url']) for url in self.extract_urls_with_indices()]
        
    def extract_urls_with_indices(self, options = {'extract_url_without_protocol': True}):
        """
        Extracts a list of all URLs included in the Tweet text along
        with the indices. If the text is None or contains no
        URLs an empty list will be returned.

        If a block is given then it will be called for each URL.
        """
        urls = []
        for match in REGEXEN['valid_url'].finditer(self.text):
            complete, before, url, protocol, domain, port, path, query = match.groups()
            start_position = match.start() + len(before or '')
            end_position = match.end()
            # If protocol is missing and domain contains non-ASCII characters,
            # extract ASCII-only domains.
            if not protocol:
                if not options.get('extract_url_without_protocol') or REGEXEN['invalid_url_without_protocol_preceding_chars'].search(before):
                    continue
                last_url = None
                last_url_invalid_match = None
                for ascii_domain in REGEXEN['valid_ascii_domain'].finditer(domain):
                    ascii_domain = ascii_domain.group()
                    last_url = {
                        'url':      ascii_domain,
                        'indices':  [start_position - len(before or '') + complete.find(ascii_domain), start_position - len(before or '') + complete.find(ascii_domain) + len(ascii_domain)]
                    }
                    last_url_invalid_match = REGEXEN['invalid_short_domain'].search(ascii_domain) is not None
                    if not last_url_invalid_match:
                        urls.append(last_url)
                # no ASCII-only domain found. Skip the entire URL
                if not last_url:
                    continue
                if path:
                    last_url['url'] = url.replace(domain, last_url['url'])
                    last_url['indices'][1] = end_position
                    if last_url_invalid_match:
                        urls.append(last_url)
            else:
                if REGEXEN['valid_tco_url'].match(url):
                    url = REGEXEN['valid_tco_url'].match(url).group()
                    end_position = start_position + len(url)
                urls.append({
                    'url':      url,
                    'indices':  [start_position, end_position]
                })
        return urls
        
    def extract_hashtags(self, transform = lambda x: x):
        """
        Extracts a list of all hashtags included in the Tweet text. If the
        text is None or contains no hashtags an empty list
        will be returned. The list returned will not include the leading #
        character.

        If a block is given then it will be called for each hashtag.
        """
        return [transform(hashtag['hashtag']) for hashtag in self.extract_hashtags_with_indices()]
        
    def extract_hashtags_with_indices(self, options = {'check_url_overlap': True}, transform = lambda x: x):
        """
        Extracts a list of all hashtags included in the Tweet text. If the
        text is None or contains no hashtags an empty list
        will be returned. The list returned will not include the leading #
        character.

        If a block is given then it will be called for each hashtag.
        """
        tags = []
        for match in REGEXEN['valid_hashtag'].finditer(self.text):
            before, hashchar, hashtext = match.groups()
            start_position, end_position = match.span()
            start_position = start_position + len(before)
            if not (REGEXEN['end_hashtag_match'].match(self.text[end_position]) if len(self.text) > end_position else None) and not hashtext.find('http') == 0 and not REGEXEN['numeric_only'].match(hashtext):
                tags.append({
                    'hashtag':  hashtext,
                    'indices':  [start_position, end_position]
                })

        if options.get('check_url_overlap'):
            urls = self.extract_urls_with_indices()
            if len(urls):
                tags = tags + urls
                # remove duplicates
                tags = self._remove_overlapping_entities(tags)
                tags = [tag for tag in tags if 'hashtag' in tag]

        return tags

    def extract_cashtags(self, transform = lambda x: x):
        """
        Extracts a list of all cashtags included in the Tweet text. If the
        text is None or contains no cashtags an empty list
        will be returned. The list returned will not include the leading $
        character.

        If a block is given then it will be called for each cashtag.
        """
        return [cashtag['cashtag'] for cashtag in self.extract_cashtags_with_indices()]

    def extract_cashtags_with_indices(self, transform = lambda x: x):
        """
        Extracts a list of all cashtags included in the Tweet text. If the
        text is None or contains no cashtags an empty list
        will be returned. The list returned will not include the leading $
        character.

        If a block is given then it will be called for each cashtag.
        """
        if not self.text or self.text.find('$') == -1:
            return []

        tags = []
        for match in REGEXEN['valid_cashtag'].finditer(self.text):
            before, dollar, cashtext = match.groups()
            start_position, end_position = match.span()
            start_position = start_position + len(before or '')
            tags.append({
                'cashtag':  cashtext,
                'indices':  [start_position, end_position]
            })

        return tags
########NEW FILE########
__FILENAME__ = highlighter
# encoding=utf-8

import re
from HTMLParser import HTMLParser

from twitter_text.regex import UNICODE_SPACES
from twitter_text.unicode import force_unicode

DEFAULT_HIGHLIGHT_TAG = 'em'

# from http://stackoverflow.com/questions/753052/strip-html-from-strings-in-python
class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

class HitHighlighter(object):
    def __init__(self, text, **kwargs):
        self.text = force_unicode(text)
        self.parent = kwargs.get('parent', False)

    def hit_highlight(self, hits = [], **kwargs):
        if not hits and not kwargs.get('query'):
            return self.text

        if not hits and kwargs.get('query'):
            stripped_text   =   strip_tags(self.text)
            for match in re.finditer(ur'%s' % kwargs.get('query'), stripped_text):
                hits.append(match.span())

        if hits and not type(hits) == list:
            raise Exception('The syntax for the hit_highlight method has changed. You must pass in a list of lists containing the indices of the strings you want to match.')

        tag_name = kwargs.get('tag', DEFAULT_HIGHLIGHT_TAG)
        tags = [u'<%s>' % tag_name, u'</%s>' % tag_name]

        text = self.text
        chunks = re.split(r'[<>]', text)
        text_chunks = []
        for index, chunk in enumerate(chunks):
            if not index % 2:
                text_chunks.append(chunk)
        for hit in sorted(hits, key = lambda chunk: chunk[1], reverse = True):
            hit_start, hit_end = hit
            placed = 0
            for index, chunk in enumerate(chunks):
                if placed == 2:
                    continue
                if index % 2:
                    # we're inside a <tag>
                    continue
                chunk_start = len(u''.join(text_chunks[0:index / 2]))
                chunk_end = chunk_start + len(chunk)
                if hit_start >= chunk_start and hit_start < chunk_end:
                    chunk = chunk[:hit_start - chunk_start] + tags[0] + chunk[hit_start - chunk_start:]
                    if hit_end <= chunk_end:
                        hit_end += len(tags[0])
                        chunk_end += len(tags[0])
                    placed = 1
                if hit_end > chunk_start and hit_end <= chunk_end:
                    chunk = chunk[:hit_end - chunk_start] + tags[1] + chunk[hit_end - chunk_start:]
                    placed = 2
                chunks[index] = chunk
            if placed == 1:
                chunks[-1] = chunks[-1] + tags[1]
        result = []
        for index, chunk in enumerate(chunks):
            if index % 2:
                # we're inside a <tag>
                result.append(u'<%s>' % chunk)
            else:
                result.append(chunk)
        self.text = u''.join(result)
        return self.text
########NEW FILE########
__FILENAME__ = regex
#  encoding=utf-8

# A collection of regular expressions for parsing Tweet text. The regular expression
# list is frozen at load time to ensure immutability. These reular expressions are
# used throughout the Twitter classes. Special care has been taken to make
# sure these reular expressions work with Tweets in all languages.
import re, string

REGEXEN = {} # :nodoc:

def regex_range(start, end = None):
    if end:
        return u'%s-%s' % (unichr(start), unichr(end))
    else:
        return u'%s' % unichr(start)

# Space is more than %20, U+3000 for example is the full-width space used with Kanji. Provide a short-hand
# to access both the list of characters and a pattern suitible for use with String#split
#  Taken from: ActiveSupport::Multibyte::Handlers::UTF8Handler::UNICODE_WHITESPACE
UNICODE_SPACES = []
for space in reduce(lambda x,y: x + y if type(y) == list else x + [y], [
        range(0x0009, 0x000D),  # White_Space # Cc   [5] <control-0009>..<control-000D>
        0x0020,                 # White_Space # Zs       SPACE
        0x0085,                 # White_Space # Cc       <control-0085>
        0x00A0,                 # White_Space # Zs       NO-BREAK SPACE
        0x1680,                 # White_Space # Zs       OGHAM SPACE MARK
        0x180E,                 # White_Space # Zs       MONGOLIAN VOWEL SEPARATOR
        range(0x2000, 0x200A),  # White_Space # Zs  [11] EN QUAD..HAIR SPACE
        0x2028,                 # White_Space # Zl       LINE SEPARATOR
        0x2029,                 # White_Space # Zp       PARAGRAPH SEPARATOR
        0x202F,                 # White_Space # Zs       NARROW NO-BREAK SPACE
        0x205F,                 # White_Space # Zs       MEDIUM MATHEMATICAL SPACE
        0x3000,                 # White_Space # Zs       IDEOGRAPHIC SPACE
    ]):
    UNICODE_SPACES.append(unichr(space))
REGEXEN['spaces'] = re.compile(ur''.join(UNICODE_SPACES))

# Characters not allowed in Tweets
INVALID_CHARACTERS  =   [
    0xFFFE, 0xFEFF,                         # BOM
    0xFFFF,                                 # Special
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E, # Directional change
]
REGEXEN['invalid_control_characters']   =   [unichr(x) for x in INVALID_CHARACTERS]

REGEXEN['list_name'] = re.compile(ur'^[a-zA-Z][a-zA-Z0-9_\-\u0080-\u00ff]{0,24}$')

# Latin accented characters
# Excludes 0xd7 from the range (the multiplication sign, confusable with "x").
# Also excludes 0xf7, the division sign
LATIN_ACCENTS = [
    regex_range(0x00c0, 0x00d6),
    regex_range(0x00d8, 0x00f6),
    regex_range(0x00f8, 0x00ff),
    regex_range(0x0100, 0x024f),
    regex_range(0x0253, 0x0254),
    regex_range(0x0256, 0x0257),
    regex_range(0x0259),
    regex_range(0x025b),
    regex_range(0x0263),
    regex_range(0x0268),
    regex_range(0x026f),
    regex_range(0x0272),
    regex_range(0x0289),
    regex_range(0x028b),
    regex_range(0x02bb),
    regex_range(0x0300, 0x036f),
    regex_range(0x1e00, 0x1eff),
]
REGEXEN['latin_accents'] = re.compile(ur''.join(LATIN_ACCENTS), re.IGNORECASE | re.UNICODE)
LATIN_ACCENTS = u''.join(LATIN_ACCENTS)

RTL_CHARACTERS = ''.join([
    regex_range(0x0600,0x06FF),
    regex_range(0x0750,0x077F),
    regex_range(0x0590,0x05FF),
    regex_range(0xFE70,0xFEFF)
])

NON_LATIN_HASHTAG_CHARS = ''.join([
    # Cyrillic (Russian, Ukrainian, etc.)
    regex_range(0x0400, 0x04ff), # Cyrillic
    regex_range(0x0500, 0x0527), # Cyrillic Supplement
    regex_range(0x2de0, 0x2dff), # Cyrillic Extended A
    regex_range(0xa640, 0xa69f), # Cyrillic Extended B
    regex_range(0x0591, 0x05bf), # Hebrew
    regex_range(0x05c1, 0x05c2),
    regex_range(0x05c4, 0x05c5),
    regex_range(0x05c7),
    regex_range(0x05d0, 0x05ea),
    regex_range(0x05f0, 0x05f4),
    regex_range(0xfb12, 0xfb28), # Hebrew Presentation Forms
    regex_range(0xfb2a, 0xfb36),
    regex_range(0xfb38, 0xfb3c),
    regex_range(0xfb3e),
    regex_range(0xfb40, 0xfb41),
    regex_range(0xfb43, 0xfb44),
    regex_range(0xfb46, 0xfb4f),
    regex_range(0x0610, 0x061a), # Arabic
    regex_range(0x0620, 0x065f),
    regex_range(0x066e, 0x06d3),
    regex_range(0x06d5, 0x06dc),
    regex_range(0x06de, 0x06e8),
    regex_range(0x06ea, 0x06ef),
    regex_range(0x06fa, 0x06fc),
    regex_range(0x06ff),
    regex_range(0x0750, 0x077f), # Arabic Supplement
    regex_range(0x08a0),         # Arabic Extended A
    regex_range(0x08a2, 0x08ac),
    regex_range(0x08e4, 0x08fe),
    regex_range(0xfb50, 0xfbb1), # Arabic Pres. Forms A
    regex_range(0xfbd3, 0xfd3d),
    regex_range(0xfd50, 0xfd8f),
    regex_range(0xfd92, 0xfdc7),
    regex_range(0xfdf0, 0xfdfb),
    regex_range(0xfe70, 0xfe74), # Arabic Pres. Forms B
    regex_range(0xfe76, 0xfefc),
    regex_range(0x200c, 0x200c), # Zero-Width Non-Joiner
    regex_range(0x0e01, 0x0e3a), # Thai
    regex_range(0x0e40, 0x0e4e), # Hangul (Korean)
    regex_range(0x1100, 0x11ff), # Hangul Jamo
    regex_range(0x3130, 0x3185), # Hangul Compatibility Jamo
    regex_range(0xA960, 0xA97F), # Hangul Jamo Extended-A
    regex_range(0xAC00, 0xD7AF), # Hangul Syllables
    regex_range(0xD7B0, 0xD7FF), # Hangul Jamo Extended-B
    regex_range(0xFFA1, 0xFFDC)  # Half-width Hangul
])

CJ_HASHTAG_CHARACTERS = ''.join([
    regex_range(0x30A1, 0x30FA), regex_range(0x30FC, 0x30FE), # Katakana (full-width)
    regex_range(0xFF66, 0xFF9F), # Katakana (half-width)
    regex_range(0xFF10, 0xFF19), regex_range(0xFF21, 0xFF3A), regex_range(0xFF41, 0xFF5A), # Latin (full-width)
    regex_range(0x3041, 0x3096), regex_range(0x3099, 0x309E), # Hiragana
    regex_range(0x3400, 0x4DBF), # Kanji (CJK Extension A)
    regex_range(0x4E00, 0x9FFF), # Kanji (Unified)
])

try:
    CJ_HASHTAG_CHARACTERS = ''.join([
        CJ_HASHTAG_CHARACTERS,
        regex_range(0x20000, 0x2A6DF), # Kanji (CJK Extension B)
        regex_range(0x2A700, 0x2B73F), # Kanji (CJK Extension C)
        regex_range(0x2B740, 0x2B81F), # Kanji (CJK Extension D)
        regex_range(0x2F800, 0x2FA1F), regex_range(0x3003), regex_range(0x3005), regex_range(0x303B) # Kanji (CJK supplement)
    ])
except ValueError:
    # this is a narrow python build so these extended Kanji characters won't work
    pass

PUNCTUATION_CHARS = ur'!"#$%&\'()*+,-./:;<=>?@\[\]^_\`{|}~'
SPACE_CHARS = ur" \t\n\x0B\f\r"
CTRL_CHARS = ur"\x00-\x1F\x7F"

# A hashtag must contain latin characters, numbers and underscores, but not all numbers.
HASHTAG_ALPHA = ur'[a-z_%s]' % (LATIN_ACCENTS + NON_LATIN_HASHTAG_CHARS + CJ_HASHTAG_CHARACTERS)
HASHTAG_ALPHANUMERIC = ur'[a-z0-9_%s]' % (LATIN_ACCENTS + NON_LATIN_HASHTAG_CHARS + CJ_HASHTAG_CHARACTERS)
HASHTAG_BOUNDARY = ur'\A|\z|\[|[^&a-z0-9_%s]' % (LATIN_ACCENTS + NON_LATIN_HASHTAG_CHARS + CJ_HASHTAG_CHARACTERS)

HASHTAG = re.compile(ur'(%s)(#|＃)(%s*%s%s*)' % (HASHTAG_BOUNDARY, HASHTAG_ALPHANUMERIC, HASHTAG_ALPHA, HASHTAG_ALPHANUMERIC), re.IGNORECASE)

REGEXEN['valid_hashtag'] = HASHTAG
REGEXEN['end_hashtag_match'] = re.compile(ur'\A(?:[#＃]|:\/\/)', re.IGNORECASE | re.UNICODE)
REGEXEN['numeric_only'] = re.compile(ur'^[\d]+$')

REGEXEN['valid_mention_preceding_chars'] = re.compile(r'(?:[^a-zA-Z0-9_!#\$%&*@＠]|^|RT:?)')
REGEXEN['at_signs'] = re.compile(ur'[@＠]')
REGEXEN['valid_mention_or_list'] = re.compile(
    ur'(%s)' % REGEXEN['valid_mention_preceding_chars'].pattern.decode('utf-8') +   # preceding character
    ur'(%s)' % REGEXEN['at_signs'].pattern +                                        # at mark
    ur'([a-zA-Z0-9_]{1,20})' +                                                      # screen name
    ur'(\/[a-zA-Z][a-zA-Z0-9_\-]{0,24})?'                                           # list (optional)
)
REGEXEN['valid_reply'] = re.compile(ur'^(?:[%s])*%s([a-zA-Z0-9_]{1,20})' % (REGEXEN['spaces'].pattern, REGEXEN['at_signs'].pattern), re.IGNORECASE | re.UNICODE)
 # Used in Extractor for final filtering
REGEXEN['end_mention_match'] = re.compile(ur'\A(?:%s|[%s]|:\/\/)' % (REGEXEN['at_signs'].pattern, REGEXEN['latin_accents'].pattern), re.IGNORECASE | re.UNICODE)

# URL related hash regex collection
REGEXEN['valid_url_preceding_chars'] = re.compile(ur'(?:[^A-Z0-9@＠$#＃%s]|^)' % ur''.join(REGEXEN['invalid_control_characters']), re.IGNORECASE | re.UNICODE)
REGEXEN['invalid_url_without_protocol_preceding_chars'] = re.compile(ur'[-_.\/]$')
DOMAIN_VALID_CHARS = ur'[^%s%s%s%s%s]' % (PUNCTUATION_CHARS, SPACE_CHARS, CTRL_CHARS, ur''.join(REGEXEN['invalid_control_characters']), ur''.join(UNICODE_SPACES))
REGEXEN['valid_subdomain'] = re.compile(ur'(?:(?:%s(?:[_-]|%s)*)?%s\.)' % (DOMAIN_VALID_CHARS, DOMAIN_VALID_CHARS, DOMAIN_VALID_CHARS), re.IGNORECASE | re.UNICODE)
REGEXEN['valid_domain_name'] = re.compile(ur'(?:(?:%s(?:[-]|%s)*)?%s\.)' % (DOMAIN_VALID_CHARS, DOMAIN_VALID_CHARS, DOMAIN_VALID_CHARS), re.IGNORECASE | re.UNICODE)
REGEXEN['valid_gTLD'] = re.compile(ur'(?:(?:academy|actor|aero|agency|arpa|asia|bar|bargains|berlin|best|bid|bike|biz|blue|boutique|build|builders|buzz|cab|camera|camp|cards|careers|cat|catering|center|ceo|cheap|christmas|cleaning|clothing|club|codes|coffee|com|community|company|computer|construction|contractors|cool|coop|cruises|dance|dating|democrat|diamonds|directory|domains|edu|education|email|enterprises|equipment|estate|events|expert|exposed|farm|fish|flights|florist|foundation|futbol|gallery|gift|glass|gov|graphics|guitars|guru|holdings|holiday|house|immobilien|industries|info|institute|int|international|jobs|kaufen|kim|kitchen|kiwi|koeln|kred|land|lighting|limo|link|luxury|management|mango|marketing|menu|mil|mobi|moda|monash|museum|nagoya|name|net|neustar|ninja|okinawa|onl|org|partners|parts|photo|photography|photos|pics|pink|plumbing|post|pro|productions|properties|pub|qpon|recipes|red|rentals|repair|report|reviews|rich|ruhr|sexy|shiksha|shoes|singles|social|solar|solutions|supplies|supply|support|systems|tattoo|technology|tel|tienda|tips|today|tokyo|tools|training|travel|uno|vacations|ventures|viajes|villas|vision|vote|voting|voto|voyage|wang|watch|wed|wien|wiki|works|xxx|xyz|zone|дети|онлайн|орг|сайт|بازار|شبكة|みんな|中信|中文网|公司|公>益|在线|我爱你|政务|游戏|移动|网络|集团|삼성)(?=[^0-9a-z]|$))', re.IGNORECASE | re.UNICODE)
REGEXEN['valid_ccTLD'] = re.compile(ur'(?:(?:ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bl|bm|bn|bo|bq|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cu|cv|cw|cx|cy|cz|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mf|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|um|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|za|zm|zw|мон|рф|срб|укр|қаз|الاردن|الجزائر|السعودية|المغرب|امارات|ایران|بھارت|تونس|سودان|سورية|عمان|فلسطين|قطر|مصر|مليسيا|پاکستان|भारत|বাংলা|ভারত|ਭਾਰਤ|ભારત|இந்தியா|இலங்கை|சிங்கப்பூர்|భారత్|ලංකා|ไทย|გე|中国|中加坡|湾|台灣|新香港|한국)(?=[^0-9a-z]|$))', re.IGNORECASE | re.UNICODE)
REGEXEN['valid_punycode'] = re.compile(ur'(?:xn--[0-9a-z]+)', re.IGNORECASE | re.UNICODE)

REGEXEN['valid_domain'] = re.compile(ur'(?:%s*%s(?:%s|%s|%s))' % (REGEXEN['valid_subdomain'].pattern, REGEXEN['valid_domain_name'].pattern, REGEXEN['valid_gTLD'].pattern, REGEXEN['valid_ccTLD'].pattern, REGEXEN['valid_punycode'].pattern), re.IGNORECASE | re.UNICODE)

# This is used in Extractor
REGEXEN['valid_ascii_domain'] = re.compile(ur'(?:(?:[A-Za-z0-9\-_]|[%s])+\.)+(?:%s|%s|%s)' % (REGEXEN['latin_accents'].pattern, REGEXEN['valid_gTLD'].pattern, REGEXEN['valid_ccTLD'].pattern, REGEXEN['valid_punycode'].pattern), re.IGNORECASE | re.UNICODE)

# This is used in Extractor for stricter t.co URL extraction
REGEXEN['valid_tco_url'] = re.compile(ur'^https?:\/\/t\.co\/[a-z0-9]+', re.IGNORECASE | re.UNICODE)

# This is used in Extractor to filter out unwanted URLs.
REGEXEN['invalid_short_domain'] = re.compile(ur'\A%s%s\Z' % (REGEXEN['valid_domain_name'].pattern, REGEXEN['valid_ccTLD'].pattern), re.IGNORECASE | re.UNICODE)

REGEXEN['valid_port_number'] = re.compile(ur'[0-9]+')

REGEXEN['valid_general_url_path_chars'] = re.compile(ur"[a-z0-9!\*';:=\+\,\.\$\/%%#\[\]\-_~&|@%s]" % LATIN_ACCENTS, re.IGNORECASE | re.UNICODE)
# Allow URL paths to contain balanced parens
#  1. Used in Wikipedia URLs like /Primer_(film)
#  2. Used in IIS sessions like /S(dfd346)/
REGEXEN['valid_url_balanced_parens'] = re.compile(ur'\(%s+\)' % REGEXEN['valid_general_url_path_chars'].pattern, re.IGNORECASE | re.UNICODE)
# Valid end-of-path chracters (so /foo. does not gobble the period).
#   1. Allow =&# for empty URL parameters and other URL-join artifacts
REGEXEN['valid_url_path_ending_chars'] = re.compile(ur'[a-z0-9=_#\/\+\-%s]|(?:%s)' % (LATIN_ACCENTS, REGEXEN['valid_url_balanced_parens'].pattern), re.IGNORECASE | re.UNICODE)
REGEXEN['valid_url_path'] = re.compile(ur'(?:(?:%s*(?:%s %s*)*%s)|(?:%s+\/))' % (REGEXEN['valid_general_url_path_chars'].pattern, REGEXEN['valid_url_balanced_parens'].pattern, REGEXEN['valid_general_url_path_chars'].pattern, REGEXEN['valid_url_path_ending_chars'].pattern, REGEXEN['valid_general_url_path_chars'].pattern), re.IGNORECASE | re.UNICODE)

REGEXEN['valid_url_query_chars'] = re.compile(ur"[a-z0-9!?\*'\(\);:&=\+\$\/%#\[\]\-_\.,~|@]", re.IGNORECASE | re.UNICODE)
REGEXEN['valid_url_query_ending_chars'] = re.compile(ur'[a-z0-9_&=#\/]', re.IGNORECASE | re.UNICODE)
REGEXEN['valid_url'] = re.compile(ur'((%s)((https?:\/\/)?(%s)(?::(%s))?(/%s*)?(\?%s*%s)?))' % (
    REGEXEN['valid_url_preceding_chars'].pattern,
    REGEXEN['valid_domain'].pattern,
    REGEXEN['valid_port_number'].pattern,
    REGEXEN['valid_url_path'].pattern,
    REGEXEN['valid_url_query_chars'].pattern,
    REGEXEN['valid_url_query_ending_chars'].pattern
), re.IGNORECASE | re.UNICODE)
#   Matches
#   $1 total match
#   $2 Preceeding chracter
#   $3 URL
#   $4 Protocol (optional)
#   $5 Domain(s)
#   $6 Port number (optional)
#   $7 URL Path and anchor
#   $8 Query String

REGEXEN['cashtag'] = re.compile(ur'[a-z]{1,6}(?:[._][a-z]{1,2})?', re.IGNORECASE)
REGEXEN['valid_cashtag'] = re.compile(ur'(^|[%s])(\$|＄|﹩)(%s)(?=$|\s|[%s])' % (REGEXEN['spaces'].pattern, REGEXEN['cashtag'].pattern, PUNCTUATION_CHARS), re.IGNORECASE)

# These URL validation pattern strings are based on the ABNF from RFC 3986
REGEXEN['validate_url_unreserved'] = re.compile(ur'[a-z0-9\-._~]', re.IGNORECASE | re.UNICODE)
REGEXEN['validate_url_pct_encoded'] = re.compile(ur'(?:%[0-9a-f]{2})', re.IGNORECASE | re.UNICODE)
REGEXEN['validate_url_sub_delims'] = re.compile(ur"[!$&'()*+,;=]", re.IGNORECASE | re.UNICODE)
REGEXEN['validate_url_pchar'] = re.compile(ur'(?:%s|%s|%s|[:\|@])' % (REGEXEN['validate_url_unreserved'].pattern, REGEXEN['validate_url_pct_encoded'].pattern, REGEXEN['validate_url_sub_delims'].pattern), re.IGNORECASE | re.UNICODE)

REGEXEN['validate_url_scheme'] = re.compile(ur'(?:[a-z][a-z0-9+\-.]*)', re.IGNORECASE | re.UNICODE)
REGEXEN['validate_url_userinfo'] = re.compile(ur'(?:%s|%s|%s|:)*' % (REGEXEN['validate_url_unreserved'].pattern, REGEXEN['validate_url_pct_encoded'].pattern, REGEXEN['validate_url_sub_delims'].pattern), re.IGNORECASE | re.UNICODE)

REGEXEN['validate_url_dec_octet'] = re.compile(ur'(?:[0-9]|(?:[1-9][0-9])|(?:1[0-9]{2})|(?:2[0-4][0-9])|(?:25[0-5]))', re.IGNORECASE | re.UNICODE)
REGEXEN['validate_url_ipv4'] = re.compile(ur'(?:%s(?:\.%s){3})' % (REGEXEN['validate_url_dec_octet'].pattern, REGEXEN['validate_url_dec_octet'].pattern), re.IGNORECASE | re.UNICODE)

# Punting on real IPv6 validation for now
REGEXEN['validate_url_ipv6'] = re.compile(ur'(?:\[[a-f0-9:\.]+\])', re.IGNORECASE | re.UNICODE)

# Also punting on IPvFuture for now
REGEXEN['validate_url_ip'] = re.compile(ur'(?:%s|%s)' % (REGEXEN['validate_url_ipv4'].pattern, REGEXEN['validate_url_ipv6'].pattern), re.IGNORECASE | re.UNICODE)

# This is more strict than the rfc specifies
REGEXEN['validate_url_subdomain_segment'] = re.compile(ur'(?:[a-z0-9](?:[a-z0-9_\-]*[a-z0-9])?)', re.IGNORECASE | re.UNICODE)
REGEXEN['validate_url_domain_segment'] = re.compile(ur'(?:[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?)', re.IGNORECASE | re.UNICODE)
REGEXEN['validate_url_domain_tld'] = re.compile(ur'(?:[a-z](?:[a-z0-9\-]*[a-z0-9])?)', re.IGNORECASE | re.UNICODE)
REGEXEN['validate_url_domain'] = re.compile(ur'(?:(?:%s\.)*(?:%s\.)%s)' % (REGEXEN['validate_url_subdomain_segment'].pattern, REGEXEN['validate_url_domain_segment'].pattern, REGEXEN['validate_url_domain_tld'].pattern), re.IGNORECASE | re.UNICODE)

REGEXEN['validate_url_host'] = re.compile(ur'(?:%s|%s)' % (REGEXEN['validate_url_ip'].pattern, REGEXEN['validate_url_domain'].pattern), re.IGNORECASE | re.UNICODE)

# Unencoded internationalized domains - this doesn't check for invalid UTF-8 sequences
REGEXEN['validate_url_unicode_subdomain_segment'] = re.compile(ur'(?:(?:[a-z0-9]|[^\x00-\x7f])(?:(?:[a-z0-9_\-]|[^\x00-\x7f])*(?:[a-z0-9]|[^\x00-\x7f]))?)', re.IGNORECASE | re.UNICODE)
REGEXEN['validate_url_unicode_domain_segment'] = re.compile(ur'(?:(?:[a-z0-9]|[^\x00-\x7f])(?:(?:[a-z0-9\-]|[^\x00-\x7f])*(?:[a-z0-9]|[^\x00-\x7f]))?)', re.IGNORECASE | re.UNICODE)
REGEXEN['validate_url_unicode_domain_tld'] = re.compile(ur'(?:(?:[a-z]|[^\x00-\x7f])(?:(?:[a-z0-9\-]|[^\x00-\x7f])*(?:[a-z0-9]|[^\x00-\x7f]))?)', re.IGNORECASE | re.UNICODE)
REGEXEN['validate_url_unicode_domain'] = re.compile(ur'(?:(?:%s\.)*(?:%s\.)%s)' % (REGEXEN['validate_url_unicode_subdomain_segment'].pattern, REGEXEN['validate_url_unicode_domain_segment'].pattern, REGEXEN['validate_url_unicode_domain_tld'].pattern), re.IGNORECASE | re.UNICODE)

REGEXEN['validate_url_unicode_host'] = re.compile(ur'(?:%s|%s)' % (REGEXEN['validate_url_ip'].pattern, REGEXEN['validate_url_unicode_domain'].pattern), re.IGNORECASE | re.UNICODE)

REGEXEN['validate_url_port'] = re.compile(ur'[0-9]{1,5}')

REGEXEN['validate_url_unicode_authority'] = re.compile(ur'(?:(%s)@)?(%s)(?::(%s))?' % (REGEXEN['validate_url_userinfo'].pattern, REGEXEN['validate_url_unicode_host'].pattern, REGEXEN['validate_url_port'].pattern), re.IGNORECASE | re.UNICODE)

REGEXEN['validate_url_authority'] = re.compile(ur'(?:(%s)@)?(%s)(?::(%s))?' % (REGEXEN['validate_url_userinfo'].pattern, REGEXEN['validate_url_host'].pattern, REGEXEN['validate_url_port'].pattern), re.IGNORECASE | re.UNICODE)

REGEXEN['validate_url_path'] = re.compile(ur'(/%s*)*' % REGEXEN['validate_url_pchar'].pattern, re.IGNORECASE | re.UNICODE)
REGEXEN['validate_url_query'] = re.compile(ur'(%s|/|\?)*' % REGEXEN['validate_url_pchar'].pattern, re.IGNORECASE | re.UNICODE)
REGEXEN['validate_url_fragment'] = re.compile(ur'(%s|/|\?)*' % REGEXEN['validate_url_pchar'].pattern, re.IGNORECASE | re.UNICODE)

# Modified version of RFC 3986 Appendix B
REGEXEN['validate_url_unencoded'] = re.compile(ur'\A(?:([^:/?#]+)://)?([^/?#]*)([^?#]*)(?:\?([^#]*))?(?:\#(.*))?\Z', re.IGNORECASE | re.UNICODE)

REGEXEN['rtl_chars'] = re.compile(ur'[%s]' % RTL_CHARACTERS, re.IGNORECASE | re.UNICODE)

########NEW FILE########
__FILENAME__ = twitterize
try:
    from django.template import Library
    from django.template.defaultfilters import stringfilter
except:
    raise Exception('Django is not installed.')

from twitter_text import TwitterText

register = Library()

@register.filter(name = 'twitter_text')
@stringfilter
def twitter_text(text, search_query = False):
    """
    Parses a text string through the TwitterText auto_link method and if search_query is passed, through the hit_highlight method.
    """
    tt = TwitterText(text)
    if search_query:
        tt.text     =   tt.highlighter.hit_highlight(query = search_query)
    tt.text         =   tt.autolink.auto_link()
    return tt.text
twitter_text.is_safe = True
########NEW FILE########
__FILENAME__ = unicode
import types, datetime
from decimal import Decimal

# borrowed from django.utils.encoding
class TwitterTextUnicodeDecodeError(UnicodeDecodeError):
    def __init__(self, obj, *args):
        self.obj = obj
        UnicodeDecodeError.__init__(self, *args)

    def __str__(self):
        original = UnicodeDecodeError.__str__(self)
        return '%s. You passed in %r (%s)' % (original, self.obj,
                type(self.obj))

def is_protected_type(obj):
    """Determine if the object instance is of a protected type.

    Objects of protected types are preserved as-is when passed to
    force_unicode(strings_only=True).
    """
    return isinstance(obj, (
        types.NoneType,
        int, long,
        datetime.datetime, datetime.date, datetime.time,
        float, Decimal)
    )

def force_unicode(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Similar to smart_unicode, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and is_protected_type(s):
        return s
    try:
        if not isinstance(s, basestring,):
            if hasattr(s, '__unicode__'):
                s = unicode(s)
            else:
                try:
                    s = unicode(str(s), encoding, errors)
                except UnicodeEncodeError:
                    if not isinstance(s, Exception):
                        raise
                    # If we get to here, the caller has passed in an Exception
                    # subclass populated with non-ASCII data without special
                    # handling to display as a string. We need to handle this
                    # without raising a further exception. We do an
                    # approximation to what the Exception's standard str()
                    # output should be.
                    s = ' '.join([force_unicode(arg, encoding, strings_only,
                            errors) for arg in s])
        elif not isinstance(s, unicode):
            # Note: We use .decode() here, instead of unicode(s, encoding,
            # errors), so that if s is a SafeString, it ends up being a
            # SafeUnicode at the end.
            s = s.decode(encoding, errors)
    except UnicodeDecodeError, e:
        if not isinstance(s, Exception):
            raise TwitterTextUnicodeDecodeError(s, *e.args)
        else:
            # If we get to here, the caller has passed in an Exception
            # subclass populated with non-ASCII bytestring data without a
            # working unicode method. Try to handle this without raising a
            # further exception by individually forcing the exception args
            # to unicode.
            s = ' '.join([force_unicode(arg, encoding, strings_only,
                    errors) for arg in s])
    return s

########NEW FILE########
__FILENAME__ = validation
# encoding=utf-8

import re

from twitter_text.unicode import force_unicode
from twitter_text.extractor import Extractor
from twitter_text.regex import REGEXEN

MAX_LENGTH = 140

DEFAULT_TCO_URL_LENGTHS = {
  'short_url_length': 22,
  'short_url_length_https': 23,
  'characters_reserved_per_media': 22,
}

class Validation(object):
    def __init__(self, text, **kwargs):
        self.text = force_unicode(text)
        self.parent = kwargs.get('parent', False)
        
    def tweet_length(self, options = {}):
        """
        Returns the length of the string as it would be displayed. This is equivilent to the length of the Unicode NFC
        (See: http://www.unicode.org/reports/tr15). This is needed in order to consistently calculate the length of a
        string no matter which actual form was transmitted. For example:

             U+0065  Latin Small Letter E
         +   U+0301  Combining Acute Accent
         ----------
         =   2 bytes, 2 characters, displayed as é (1 visual glyph)
             … The NFC of {U+0065, U+0301} is {U+00E9}, which is a single chracter and a +display_length+ of 1

         The string could also contain U+00E9 already, in which case the canonicalization will not change the value.
        """

        assert (not self.parent or not getattr(self.parent, 'has_been_linked', False) ), 'The validator should only be run on text before it has been modified.'

        for key in DEFAULT_TCO_URL_LENGTHS:
            if not key in options:
                options[key] = DEFAULT_TCO_URL_LENGTHS[key]

        length = len(self.text)
        # thanks force_unicode for making this so much simpler than the ruby version

        for url in Extractor(self.text).extract_urls_with_indices():
            # remove the link of the original URL
            length += url['indices'][0] - url['indices'][1]
            # add the length of the t.co URL that will replace it
            length += options.get('short_url_length_https') if url['url'].lower().find('https://') > -1 else options.get('short_url_length')

        if self.parent and hasattr(self.parent, 'tweet_length'):
            self.parent.tweet_length = length
        return length
    
    def tweet_invalid(self):
        """
        Check the text for any reason that it may not be valid as a Tweet. This is meant as a pre-validation
        before posting to api.twitter.com. There are several server-side reasons for Tweets to fail but this pre-validation
        will allow quicker feedback.
        
        Returns false if this text is valid. Otherwise one of the following Symbols will be returned:
        
            "Too long":: if the text is too long
            "Empty text":: if the text is empty
            "Invalid characters":: if the text contains non-Unicode or any of the disallowed Unicode characters
        """

        valid = True # optimism
        validation_error = None

        if not self.tweet_length():
            valid, validation_error = False, 'Empty text'

        if self.tweet_length() > MAX_LENGTH:
            valid, validation_error = False, 'Too long'

        if re.search(ur''.join(REGEXEN['invalid_control_characters']), self.text):
            valid, validation_error = False, 'Invalid characters'
            
        if self.parent and hasattr(self.parent, 'tweet_is_valid'):
            self.parent.tweet_is_valid = valid
        if self.parent and hasattr(self.parent, 'tweet_validation_error'):
            self.parent.tweet_validation_error = validation_error

        return validation_error if not valid else False

    def valid_tweet_text(self):
        return not self.tweet_invalid()

    def valid_username(self):
        if not self.text:
            return False

        extracted = Extractor(self.text).extract_mentioned_screen_names()

        return len(extracted) == 1 and extracted[0] == self.text[1:]

    def valid_list(self):
        match = re.compile(ur'^%s$' % REGEXEN['valid_mention_or_list'].pattern).search(self.text)
        return bool(match is not None and match.groups()[0] == "" and match.groups()[3])

    def valid_hashtag(self):
        if not self.text:
            return False

        extracted = Extractor(self.text).extract_hashtags()

        return len(extracted) == 1 and extracted[0] == self.text[1:]

    def valid_url(self, unicode_domains = True, require_protocol = True):
        if not self.text:
            return False

        url_parts = REGEXEN['validate_url_unencoded'].match(self.text)

        if not (url_parts and url_parts.string == self.text):
            return False

        scheme, authority, path, query, fragment = url_parts.groups()

        if not (
            (
                not require_protocol 
                or (
                    self._valid_match(scheme, REGEXEN['validate_url_scheme']) 
                    and re.compile(ur'^https?$', re.IGNORECASE).match(scheme)
                )
            )
            and (
                path == ''
                or self._valid_match(path, REGEXEN['validate_url_path'])
            )
            and self._valid_match(query, REGEXEN['validate_url_query'], True)
            and self._valid_match(fragment, REGEXEN['validate_url_fragment'], True)
        ):
            return False

        return bool(
            (
                unicode_domains 
                and self._valid_match(authority, REGEXEN['validate_url_unicode_authority'])
                and REGEXEN['validate_url_unicode_authority'].match(authority).string == authority
            )
            or (
                not unicode_domains
                and self._valid_match(authority, REGEXEN['validate_url_authority'])
                and REGEXEN['validate_url_authority'].match(authority).string == authority
            )
        )

    def _valid_match(self, string, re_obj, optional = False):
        if optional and string is None:
            return True
        match = re_obj.match(string)
        if optional:
            return not (string and (match is None or not match.string[match.span()[0]:match.span()[1]] == string))
        else:
            return bool(string and match and match.string[match.span()[0]:match.span()[1]] == string)

########NEW FILE########
