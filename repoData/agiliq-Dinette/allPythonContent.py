__FILENAME__ = admin
from django.contrib import admin

from dinette import models

admin.site.register(models.SuperCategory)
admin.site.register(models.Category)
admin.site.register(models.Ftopics)
admin.site.register(models.Reply)
admin.site.register(models.DinetteUserProfile)
admin.site.register(models.SiteConfig)
admin.site.register(models.NavLink)




########NEW FILE########
__FILENAME__ = extra_settings
# Dinette Settings
import os

TOPIC_PAGE_SIZE = 3

REPLY_PAGE_SIZE = 3

AUTH_PROFILE_MODULE = 'dinette.DinetteUserProfile'

RANKS_NAMES_DATA = ((30, "Member"), (100, "Senior Member"), (300, 'Star'))

FLOOD_TIME = 1000

HAYSTACK_SITECONF = "dinette.search"

HAYSTACK_SEARCH_ENGINE = 'whoosh'

HAYSTACK_WHOOSH_PATH = os.path.join(os.path.dirname(os.path.normpath(__file__)),'index.db')

SITE_URL = "http://127.0.0.1:8000"

########NEW FILE########
__FILENAME__ = forms
from django.forms import ModelForm
from django import forms

from dinette.models import Ftopics ,Reply

#create a form from this Ftopics and use this when posting the a Topic
class FtopicForm(ModelForm):
    subject = forms.CharField(widget = forms.TextInput(attrs={"size":90}))
    message = forms.CharField(widget = forms.Textarea(attrs={"cols":90, "rows":10}))
    class Meta:
        model = Ftopics
        fields = ('subject', 'message', 'message_markup_type', 'file' )
            

#create a form from Reply
class ReplyForm(ModelForm):
    message = forms.CharField(widget = forms.Textarea(attrs={"cols":90, "rows":10}))
    class Meta:
        model = Reply
        fields = ('message', 'message_markup_type', 'file')
            
########NEW FILE########
__FILENAME__ = postmarkup
# -*- coding: UTF-8 -*-

"""
Post Markup
Author: Will McGugan (http://www.willmcgugan.com)
"""

__version__ = "1.1.4"

import re
from urllib import quote, unquote, quote_plus, urlencode
from urlparse import urlparse, urlunparse

pygments_available = True
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, ClassNotFound
    from pygments.formatters import HtmlFormatter
except ImportError:
    # Make Pygments optional
    pygments_available = False


def annotate_link(domain):
    """This function is called by the url tag. Override to disable or change behaviour.

    domain -- Domain parsed from url

    """
    return u" [%s]"%_escape(domain)


_re_url = re.compile(r"((https?):((//)|(\\\\))+[\w\d:#@%/;$()~_?\+-=\\\.&]*)", re.MULTILINE|re.UNICODE)


_re_html=re.compile('<.*?>|\&.*?\;', re.UNICODE)
def textilize(s):
    """Remove markup from html"""
    return _re_html.sub("", s)

_re_excerpt = re.compile(r'\[".*?\]+?.*?\[/".*?\]+?', re.DOTALL|re.UNICODE)
_re_remove_markup = re.compile(r'\[.*?\]', re.DOTALL|re.UNICODE)

_re_break_groups = re.compile(r'\n+', re.DOTALL|re.UNICODE)

def get_excerpt(post):
    """Returns an excerpt between ["] and [/"]

    post -- BBCode string"""

    match = _re_excerpt.search(post)
    if match is None:
        return ""
    excerpt = match.group(0)
    excerpt = excerpt.replace(u'\n', u"<br/>")
    return _re_remove_markup.sub("", excerpt)

def strip_bbcode(bbcode):

    """Strips bbcode tags from a string.

    bbcode -- A string to remove tags from

    """

    return u"".join([t[1] for t in PostMarkup.tokenize(bbcode) if t[0] == PostMarkup.TOKEN_TEXT])


def create(include=None, exclude=None, use_pygments=True, **kwargs):

    """Create a postmarkup object that converts bbcode to XML snippets. Note
    that creating postmarkup objects is _not_ threadsafe, but rendering the
    html _is_ threadsafe. So typically you will need just one postmarkup instance
    to render the bbcode accross threads.

    include -- List or similar iterable containing the names of the tags to use
               If omitted, all tags will be used
    exclude -- List or similar iterable containing the names of the tags to exclude.
               If omitted, no tags will be excluded
    use_pygments -- If True, Pygments (http://pygments.org/) will be used for the code tag,
                    otherwise it will use <pre>code</pre>
    kwargs -- Remaining keyword arguments are passed to tag constructors.

    """

    postmarkup = PostMarkup()
    postmarkup_add_tag = postmarkup.tag_factory.add_tag

    def add_tag(tag_class, name, *args, **kwargs):
        if include is None or name in include:
            if exclude is not None and name in exclude:
                return
            postmarkup_add_tag(tag_class, name, *args, **kwargs)



    add_tag(SimpleTag, 'b', 'strong')
    add_tag(SimpleTag, 'i', 'em')
    add_tag(SimpleTag, 'u', 'u')
    add_tag(SimpleTag, 's', 'strike')

    add_tag(LinkTag, 'link', **kwargs)
    add_tag(LinkTag, 'url', **kwargs)

    add_tag(QuoteTag, 'quote')

    add_tag(SearchTag, u'wiki',
            u"http://en.wikipedia.org/wiki/Special:Search?search=%s", u'wikipedia.com', **kwargs)
    add_tag(SearchTag, u'google',
            u"http://www.google.com/search?hl=en&q=%s&btnG=Google+Search", u'google.com', **kwargs)
    add_tag(SearchTag, u'dictionary',
            u"http://dictionary.reference.com/browse/%s", u'dictionary.com', **kwargs)
    add_tag(SearchTag, u'dict',
            u"http://dictionary.reference.com/browse/%s", u'dictionary.com', **kwargs)

    add_tag(ImgTag, u'img')
    add_tag(ListTag, u'list')
    add_tag(ListItemTag, u'*')

    add_tag(SizeTag, u"size")
    add_tag(ColorTag, u"color")
    add_tag(CenterTag, u"center")

    if use_pygments:
        assert pygments_available, "Install Pygments (http://pygments.org/) or call create with use_pygments=False"
        add_tag(PygmentsCodeTag, u'code', **kwargs)
    else:
        add_tag(CodeTag, u'code', **kwargs)

    add_tag(ParagraphTag, u"p")

    return postmarkup

class TagBase(object):

    def __init__(self, name, enclosed=False, auto_close=False, inline=False, strip_first_newline=False, **kwargs):
        """Base class for all tags.

        name -- The name of the bbcode tag
        enclosed -- True if the contents of the tag should not be bbcode processed.
        auto_close -- True if the tag is standalone and does not require a close tag.
        inline -- True if the tag generates an inline html tag.

        """

        self.name = name
        self.enclosed = enclosed
        self.auto_close = auto_close
        self.inline = inline
        self.strip_first_newline = strip_first_newline

        self.open_pos = None
        self.close_pos = None
        self.open_node_index = None
        self.close_node_index = None

    def open(self, parser, params, open_pos, node_index):
        """ Called when the open tag is initially encountered. """
        self.params = params
        self.open_pos = open_pos
        self.open_node_index = node_index

    def close(self, parser, close_pos, node_index):
        """ Called when the close tag is initially encountered. """
        self.close_pos = close_pos
        self.close_node_index = node_index

    def render_open(self, parser, node_index):
        """ Called to render the open tag. """
        pass

    def render_close(self, parser, node_index):
        """ Called to render the close tag. """
        pass

    def get_contents(self, parser):
        """Returns the string between the open and close tag."""
        return parser.markup[self.open_pos:self.close_pos]

    def get_contents_text(self, parser):
        """Returns the string between the the open and close tag, minus bbcode tags."""
        return u"".join( parser.get_text_nodes(self.open_node_index, self.close_node_index) )

    def skip_contents(self, parser):
        """Skips the contents of a tag while rendering."""
        parser.skip_to_node(self.close_node_index)

    def __str__(self):
        return '[%s]'%self.name


class SimpleTag(TagBase):

    """A tag that can be rendered with a simple substitution. """

    def __init__(self, name, html_name, **kwargs):
        """ html_name -- the html tag to substitute."""
        TagBase.__init__(self, name, inline=True)
        self.html_name = html_name

    def render_open(self, parser, node_index):
        return u"<%s>"%self.html_name

    def render_close(self, parser, node_index):
        return u"</%s>"%self.html_name


class DivStyleTag(TagBase):

    """A simple tag that is replaces with a div and a style."""

    def __init__(self, name, style, value, **kwargs):
        TagBase.__init__(self, name)
        self.style = style
        self.value = value

    def render_open(self, parser, node_index):
        return u'<div style="%s:%s;">' % (self.style, self.value)

    def render_close(self, parser, node_index):
        return u'</div>'


class LinkTag(TagBase):

    _safe_chars = frozenset('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
               'abcdefghijklmnopqrstuvwxyz'
               '0123456789'
               '_.-=/&?:%&')

    _re_domain = re.compile(r"//([a-z0-9-\.]*)", re.UNICODE)

    def __init__(self, name, annotate_links=True, **kwargs):
        TagBase.__init__(self, name, inline=True)

        self.annotate_links = annotate_links


    def render_open(self, parser, node_index):

        self.domain = u''
        tag_data = parser.tag_data
        nest_level = tag_data['link_nest_level'] = tag_data.setdefault('link_nest_level', 0) + 1

        if nest_level > 1:
            return u""

        if self.params:
            url = self.params.strip()
        else:
            url = self.get_contents_text(parser).strip()
            url = _unescape(url)

        self.domain = ""

        if u"javascript:" in url.lower():
            return ""

        if ':' not in url:
            url = 'http://' + url

        scheme, uri = url.split(':', 1)

        if scheme not in ['http', 'https']:
            return u''

        try:
            domain = self._re_domain.search(uri.lower()).group(1)
        except IndexError:
            return u''

        domain = domain.lower()
        if domain.startswith('www.'):
            domain = domain[4:]

        def percent_encode(s):
            safe_chars = self._safe_chars
            def replace(c):
                if c not in safe_chars:
                    return "%%%02X"%ord(c)
                else:
                    return c
            return "".join([replace(c) for c in s])

        self.url = percent_encode(url.encode('utf-8', 'replace'))
        self.domain = domain

        if not self.url:
            return u""

        if self.domain:
            return u'<a href="%s">'%self.url
        else:
            return u""


    def render_close(self, parser, node_index):

        tag_data = parser.tag_data
        tag_data['link_nest_level'] -= 1

        if tag_data['link_nest_level'] > 0:
            return u''

        if self.domain:
            return u'</a>'+self.annotate_link(self.domain)
        else:
            return u''

    def annotate_link(self, domain=None):

        if domain and self.annotate_links:
            return annotate_link(domain)
        else:
            return u""


class QuoteTag(TagBase):

    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, strip_first_newline=True)

    def open(self, parser, *args):
        TagBase.open(self, parser, *args)

    def close(self, parser, *args):
        TagBase.close(self, parser, *args)

    def render_open(self, parser, node_index):
        if self.params:
            return u"<div class='quotebox'><blockquote><em>%s</em><br/>"%(PostMarkup.standard_replace(self.params))
        else:
            return u"<div class='quotebox'><blockquote>"


    def render_close(self, parser, node_index):
        return u"</div></blockquote>"


class SearchTag(TagBase):

    def __init__(self, name, url, label="", annotate_links=True, **kwargs):
        TagBase.__init__(self, name, inline=True)
        self.url = url
        self.label = label
        self.annotate_links = annotate_links

    def render_open(self, parser, node_idex):

        if self.params:
            search=self.params
        else:
            search=self.get_contents(parser)
        link = u'<a href="%s">' % self.url
        if u'%' in link:
            return link%quote_plus(search.encode("UTF-8"))
        else:
            return link

    def render_close(self, parser, node_index):

        if self.label:
            if self.annotate_links:
                return u'</a>'+ annotate_link(self.label)
            else:
                return u'</a>'
        else:
            return u''


class PygmentsCodeTag(TagBase):

    def __init__(self, name, pygments_line_numbers=False, **kwargs):
        TagBase.__init__(self, name, enclosed=True, strip_first_newline=True)
        self.line_numbers = pygments_line_numbers

    def render_open(self, parser, node_index):

        contents = self.get_contents(parser)
        self.skip_contents(parser)

        try:
            lexer = get_lexer_by_name(self.params, stripall=True)
        except ClassNotFound:
            contents = _escape(contents)
            return '<div class="code"><pre>%s</pre></div>' % contents

        formatter = HtmlFormatter(linenos=self.line_numbers, cssclass="code")
        return highlight(contents, lexer, formatter)



class CodeTag(TagBase):

    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, enclosed=True, strip_first_newline=True)

    def render_open(self, parser, node_index):

        contents = _escape_no_breaks(self.get_contents(parser))
        self.skip_contents(parser)
        return '<div class="code"><pre>%s</pre></div>' % contents


class ImgTag(TagBase):

    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, inline=True)

    def render_open(self, parser, node_index):

        contents = self.get_contents(parser)
        self.skip_contents(parser)

        contents = strip_bbcode(contents).replace(u'"', "%22")

        return u'<img src="%s"></img>' % contents


class ListTag(TagBase):

    def __init__(self, name,  **kwargs):
        TagBase.__init__(self, name, strip_first_newline=True)

    def open(self, parser, params, open_pos, node_index):
        TagBase.open(self, parser, params, open_pos, node_index)

    def close(self, parser, close_pos, node_index):
        TagBase.close(self, parser, close_pos, node_index)


    def render_open(self, parser, node_index):

        self.close_tag = u""

        tag_data = parser.tag_data
        tag_data.setdefault("ListTag.count", 0)

        if tag_data["ListTag.count"]:
            return u""

        tag_data["ListTag.count"] += 1

        tag_data["ListItemTag.initial_item"]=True

        if self.params == "1":
            self.close_tag = u"</li></ol>"
            return u"<ol><li>"
        elif self.params == "a":
            self.close_tag = u"</li></ol>"
            return u'<ol style="list-style-type: lower-alpha;"><li>'
        elif self.params == "A":
            self.close_tag = u"</li></ol>"
            return u'<ol style="list-style-type: upper-alpha;"><li>'
        else:
            self.close_tag = u"</li></ul>"
            return u"<ul><li>"

    def render_close(self, parser, node_index):

        tag_data = parser.tag_data
        tag_data["ListTag.count"] -= 1

        return self.close_tag


class ListItemTag(TagBase):

    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name)
        self.closed = False

    def render_open(self, parser, node_index):

        tag_data = parser.tag_data
        if not tag_data.setdefault("ListTag.count", 0):
            return u""

        if tag_data["ListItemTag.initial_item"]:
            tag_data["ListItemTag.initial_item"] = False
            return

        return u"</li><li>"


class SizeTag(TagBase):

    valid_chars = frozenset("0123456789")

    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, inline=True)

    def render_open(self, parser, node_index):

        try:
            self.size = int( "".join([c for c in self.params if c in self.valid_chars]) )
        except ValueError:
            self.size = None

        if self.size is None:
            return u""

        self.size = self.validate_size(self.size)

        return u'<span style="font-size:%spx">' % self.size

    def render_close(self, parser, node_index):

        if self.size is None:
            return u""

        return u'</span>'

    def validate_size(self, size):

        size = min(64, size)
        size = max(4, size)
        return size


class ColorTag(TagBase):

    valid_chars = frozenset("#0123456789abcdefghijklmnopqrstuvwxyz")

    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, inline=True)

    def render_open(self, parser, node_index):

        valid_chars = self.valid_chars
        color = self.params.split()[0:1][0].lower()
        self.color = "".join([c for c in color if c in valid_chars])

        if not self.color:
            return u""

        return u'<span style="color:%s">' % self.color

    def render_close(self, parser, node_index):

        if not self.color:
            return u''
        return u'</span>'


class CenterTag(TagBase):

    def render_open(self, parser, node_index, **kwargs):
        return u'<div style="text-align:center;">'


    def render_close(self, parser, node_index):
        return u'</div>'


class ParagraphTag(TagBase):

    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name)

    def render_open(self, parser, node_index, **kwargs):

        tag_data = parser.tag_data
        level = tag_data.setdefault('ParagraphTag.level', 0)

        ret = []
        if level > 0:
            ret.append(u'</p>')
            tag_data['ParagraphTag.level'] -= 1;

        ret.append(u'<p>')
        tag_data['ParagraphTag.level'] += 1;
        return u''.join(ret)

    def render_close(self, parser, node_index):

        tag_data = parser.tag_data
        level = tag_data.setdefault('ParagraphTag.level', 0)

        if not level:
            return u''

        tag_data['ParagraphTag.level'] -= 1;

        return u'</p>'

class SectionTag(TagBase):

    """A specialised tag that stores its contents in a dictionary. Can be
    used to define extra contents areas.

    """

    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, enclosed=True)

    def render_open(self, parser, node_index):

        self.section_name = self.params.strip().lower().replace(u' ', u'_')

        contents = self.get_contents(parser)
        self.skip_contents(parser)

        tag_data = parser.tag_data
        sections = tag_data.setdefault('sections', {})

        sections.setdefault(self.section_name, []).append(contents)

        return u''


# http://effbot.org/zone/python-replace.htm
class MultiReplace:

    def __init__(self, repl_dict):

        # string to string mapping; use a regular expression
        keys = repl_dict.keys()
        keys.sort(reverse=True) # lexical order
        pattern = u"|".join([re.escape(key) for key in keys])
        self.pattern = re.compile(pattern)
        self.dict = repl_dict

    def replace(self, s):
        # apply replacement dictionary to string

        def repl(match, get=self.dict.get):
            item = match.group(0)
            return get(item, item)
        return self.pattern.sub(repl, s)

    __call__ = replace


def _escape(s):
    return PostMarkup.standard_replace(s.rstrip('\n'))

def _escape_no_breaks(s):
    return PostMarkup.standard_replace_no_break(s.rstrip('\n'))

def _unescape(s):
    return PostMarkup.standard_unreplace(s)

class TagFactory(object):

    def __init__(self):

        self.tags = {}

    @classmethod
    def tag_factory_callable(cls, tag_class, name, *args, **kwargs):
        """
        Returns a callable that returns a new tag instance.
        """
        def make():
            return tag_class(name, *args, **kwargs)

        return make


    def add_tag(self, cls, name, *args, **kwargs):

        self.tags[name] = self.tag_factory_callable(cls, name, *args, **kwargs)

    def __getitem__(self, name):

        return self.tags[name]()

    def __contains__(self, name):

        return name in self.tags

    def get(self, name, default=None):

        if name in self.tags:
            return self.tags[name]()

        return default


class _Parser(object):

    """ This is an interface to the parser, used by Tag classes. """

    def __init__(self, post_markup, tag_data=None):

        self.pm = post_markup
        if tag_data is None:
            self.tag_data = {}
        else:
            self.tag_data = tag_data
        self.render_node_index = 0

    def skip_to_node(self, node_index):

        """ Skips to a node, ignoring intermediate nodes. """
        assert node_index is not None, "Node index must be non-None"
        self.render_node_index = node_index

    def get_text_nodes(self, node1, node2):

        """ Retrieves the text nodes between two node indices. """

        if node2 is None:
            node2 = node1+1

        return [node for node in self.nodes[node1:node2] if not callable(node)]

    def begin_no_breaks(self):

        """Disables replacing of newlines with break tags at the start and end of text nodes.
        Can only be called from a tags 'open' method.

        """
        assert self.phase==1, "Can not be called from render_open or render_close"
        self.no_breaks_count += 1

    def end_no_breaks(self):

        """Re-enables auto-replacing of newlines with break tags (see begin_no_breaks)."""

        assert self.phase==1, "Can not be called from render_open or render_close"
        if self.no_breaks_count:
            self.no_breaks_count -= 1


class PostMarkup(object):

    standard_replace = MultiReplace({   u'<':u'&lt;',
                                        u'>':u'&gt;',
                                        u'&':u'&amp;',
                                        u'\n':u'<br/>'})

    standard_unreplace = MultiReplace({  u'&lt;':u'<',
                                         u'&gt;':u'>',
                                         u'&amp;':u'&'})

    standard_replace_no_break = MultiReplace({  u'<':u'&lt;',
                                                u'>':u'&gt;',
                                                u'&':u'&amp;',})

    TOKEN_TAG, TOKEN_PTAG, TOKEN_TEXT = range(3)

    _re_end_eq = re.compile(u"\]|\=", re.UNICODE)
    _re_quote_end = re.compile(u'\"|\]', re.UNICODE)

    # I tried to use RE's. Really I did.
    @classmethod
    def tokenize(cls, post):

        re_end_eq = cls._re_end_eq
        re_quote_end = cls._re_quote_end

        text = True
        pos = 0

        def find_first(post, pos, re_ff):
            try:
                return re_ff.search(post, pos).start()
            except AttributeError:
                return -1

        TOKEN_TAG, TOKEN_PTAG, TOKEN_TEXT = range(3)

        post_find = post.find
        while True:

            brace_pos = post_find(u'[', pos)
            if brace_pos == -1:
                if pos<len(post):
                    yield TOKEN_TEXT, post[pos:], pos, len(post)
                return
            if brace_pos - pos > 0:
                yield TOKEN_TEXT, post[pos:brace_pos], pos, brace_pos

            pos = brace_pos
            end_pos = pos+1

            open_tag_pos = post_find(u'[', end_pos)
            end_pos = find_first(post, end_pos, re_end_eq)
            if end_pos == -1:
                yield TOKEN_TEXT, post[pos:], pos, len(post)
                return

            if open_tag_pos != -1 and open_tag_pos < end_pos:
                yield TOKEN_TEXT, post[pos:open_tag_pos], pos, open_tag_pos
                end_pos = open_tag_pos
                pos = end_pos
                continue

            if post[end_pos] == ']':
                yield TOKEN_TAG, post[pos:end_pos+1], pos, end_pos+1
                pos = end_pos+1
                continue

            if post[end_pos] == '=':
                try:
                    end_pos += 1
                    while post[end_pos] == ' ':
                        end_pos += 1
                    if post[end_pos] != '"':
                        end_pos = post_find(u']', end_pos+1)
                        if end_pos == -1:
                            return
                        yield TOKEN_TAG, post[pos:end_pos+1], pos, end_pos+1
                    else:
                        end_pos = find_first(post, end_pos, re_quote_end)
                        if end_pos==-1:
                            return
                        if post[end_pos] == '"':
                            end_pos = post_find(u'"', end_pos+1)
                            if end_pos == -1:
                                return
                            end_pos = post_find(u']', end_pos+1)
                            if end_pos == -1:
                                return
                            yield TOKEN_PTAG, post[pos:end_pos+1], pos, end_pos+1
                        else:
                            yield TOKEN_TAG, post[pos:end_pos+1], pos, end_pos
                    pos = end_pos+1
                except IndexError:
                    return

    def add_tag(self, cls, name, *args, **kwargs):
        return self.tag_factory.add_tag(cls, name, *args, **kwargs)

    def tagify_urls(self, postmarkup ):

        """ Surrounds urls with url bbcode tags. """

        def repl(match):
            return u'[url]%s[/url]' % match.group(0)

        text_tokens = []
        TOKEN_TEXT = PostMarkup.TOKEN_TEXT
        for tag_type, tag_token, start_pos, end_pos in self.tokenize(postmarkup):

            if tag_type == TOKEN_TEXT:
                text_tokens.append(_re_url.sub(repl, tag_token))
            else:
                text_tokens.append(tag_token)

        return u"".join(text_tokens)


    def __init__(self, tag_factory=None):

        self.tag_factory = tag_factory or TagFactory()


    def default_tags(self):

        """ Add some basic tags. """

        add_tag = self.tag_factory.add_tag

        add_tag(SimpleTag, u'b', u'strong')
        add_tag(SimpleTag, u'i', u'em')
        add_tag(SimpleTag, u'u', u'u')
        add_tag(SimpleTag, u's', u's')


    def get_supported_tags(self):

        """ Returns a list of the supported tags. """

        return sorted(self.tag_factory.tags.keys())


    def insert_paragraphs(self, post_markup):

        """Inserts paragraph tags in place of newlines. A more complex task than
        it may seem -- Multiple newlines result in just one paragraph tag, and
        paragraph tags aren't inserted inside certain other tags (such as the
        code tag). Returns a postmarkup string.

        post_markup -- A string containing the raw postmarkup

        """

        parts = [u'[p]']
        tag_factory = self.tag_factory
        enclosed_count = 0

        TOKEN_TEXT = PostMarkup.TOKEN_TEXT
        TOKEN_TAG = PostMarkup.TOKEN_TAG

        for tag_type, tag_token, start_pos, end_pos in self.tokenize(post_markup):

            if tag_type == TOKEN_TEXT:
                if enclosed_count:
                    parts.append(post_markup[start_pos:end_pos])
                else:
                    txt = post_markup[start_pos:end_pos]
                    txt = _re_break_groups.sub(u'[p]', txt)
                    parts.append(txt)
                continue

            elif tag_type == TOKEN_TAG:
                tag_token = tag_token[1:-1].lstrip()
                if ' ' in tag_token:
                    tag_name = tag_token.split(u' ', 1)[0]
                else:
                    if '=' in tag_token:
                        tag_name = tag_token.split(u'=', 1)[0]
                    else:
                        tag_name = tag_token
            else:
                tag_token = tag_token[1:-1].lstrip()
                tag_name = tag_token.split(u'=', 1)[0]

            tag_name = tag_name.strip().lower()

            end_tag = False
            if tag_name.startswith(u'/'):
                end_tag = True
                tag_name = tag_name[1:]

            tag = tag_factory.get(tag_name, None)
            if tag is not None and tag.enclosed:
                if end_tag:
                    enclosed_count -= 1
                else:
                    enclosed_count += 1

            parts.append(post_markup[start_pos:end_pos])

        new_markup = u"".join(parts)
        return new_markup

    # Matches simple blank tags containing only whitespace
    _re_blank_tags = re.compile(r"\<(\w+?)\>\s*\</\1\>")

    @classmethod
    def cleanup_html(cls, html):
        """Cleans up html. Currently only removes blank tags, i.e. tags containing only
        whitespace. Only applies to tags without attributes. Tag removal is done
        recursively until there are no more blank tags. So <strong><em></em></strong>
        would be completely removed.

        html -- A string containing (X)HTML

        """

        original_html = ''
        while original_html != html:
            original_html = html
            html = cls._re_blank_tags.sub(u"", html)
        return html


    def render_to_html(self,
                       post_markup,
                       encoding="ascii",
                       exclude_tags=None,
                       auto_urls=True,
                       paragraphs=False,
                       clean=True,
                       tag_data=None):

        """Converts post markup (ie. bbcode) to XHTML. This method is threadsafe,
        buy virtue that the state is entirely stored on the stack.

        post_markup -- String containing bbcode.
        encoding -- Encoding of string, defaults to "ascii" if the string is not
        already unicode.
        exclude_tags -- A collection of tag names to ignore.
        auto_urls -- If True, then urls will be wrapped with url bbcode tags.
        paragraphs -- If True then line breaks will be replaced with paragraph
        tags, rather than break tags.
        clean -- If True, html will be run through the cleanup_html method.
        tag_data -- An optional dictionary to store tag data in. The default of
        None will create a dictionary internaly. Set this to your own dictionary
        if you want to retrieve information from the Tag Classes.


        """

        if not isinstance(post_markup, unicode):
            post_markup = unicode(post_markup, encoding, 'replace')

        if auto_urls:
            post_markup = self.tagify_urls(post_markup)

        if paragraphs:
            post_markup = self.insert_paragraphs(post_markup)

        parser = _Parser(self, tag_data=tag_data)
        parser.markup = post_markup

        if exclude_tags is None:
            exclude_tags = []

        tag_factory = self.tag_factory


        nodes = []
        parser.nodes = nodes

        parser.phase = 1
        parser.no_breaks_count = 0
        enclosed_count = 0
        open_stack = []
        tag_stack = []
        break_stack = []
        remove_next_newline = False

        def check_tag_stack(tag_name):

            for tag in reversed(tag_stack):
                if tag_name == tag.name:
                    return True
            return False

        def redo_break_stack():

            while break_stack:
                tag = break_stack.pop()
                open_tag(tag)
                tag_stack.append(tag)

        def break_inline_tags():

            while tag_stack:
                if tag_stack[-1].inline:
                    tag = tag_stack.pop()
                    close_tag(tag)
                    break_stack.append(tag)
                else:
                    break

        def open_tag(tag):
            def call(node_index):
                return tag.render_open(parser, node_index)
            nodes.append(call)

        def close_tag(tag):
            def call(node_index):
                return tag.render_close(parser, node_index)
            nodes.append(call)

        TOKEN_TEXT = PostMarkup.TOKEN_TEXT
        TOKEN_TAG = PostMarkup.TOKEN_TAG

        # Pass 1
        for tag_type, tag_token, start_pos, end_pos in self.tokenize(post_markup):

            raw_tag_token = tag_token

            if tag_type == TOKEN_TEXT:
                if parser.no_breaks_count:
                    tag_token = tag_token.strip()
                    if not tag_token:
                        continue
                if remove_next_newline:
                    tag_token = tag_token.lstrip(' ')
                    if tag_token.startswith('\n'):
                        tag_token = tag_token.lstrip(' ')[1:]
                        if not tag_token:
                            continue
                    remove_next_newline = False

                if tag_stack and tag_stack[-1].strip_first_newline:
                    tag_token = tag_token.lstrip()
                    tag_stack[-1].strip_first_newline = False
                    if not tag_stack[-1]:
                        tag_stack.pop()
                        continue

                if not enclosed_count:
                    redo_break_stack()

                nodes.append(self.standard_replace(tag_token))
                continue

            elif tag_type == TOKEN_TAG:
                tag_token = tag_token[1:-1].lstrip()
                if ' ' in tag_token:
                    tag_name, tag_attribs = tag_token.split(u' ', 1)
                    tag_attribs = tag_attribs.strip()
                else:
                    if '=' in tag_token:
                        tag_name, tag_attribs = tag_token.split(u'=', 1)
                        tag_attribs = tag_attribs.strip()
                    else:
                        tag_name = tag_token
                        tag_attribs = u""
            else:
                tag_token = tag_token[1:-1].lstrip()
                tag_name, tag_attribs = tag_token.split(u'=', 1)
                tag_attribs = tag_attribs.strip()[1:-1]

            tag_name = tag_name.strip().lower()

            end_tag = False
            if tag_name.startswith(u'/'):
                end_tag = True
                tag_name = tag_name[1:]


            if enclosed_count and tag_stack[-1].name != tag_name:
                continue

            if tag_name in exclude_tags:
                continue

            if not end_tag:

                tag = tag_factory.get(tag_name, None)
                if tag is None:
                    continue

                redo_break_stack()

                if not tag.inline:
                    break_inline_tags()

                tag.open(parser, tag_attribs, end_pos, len(nodes))
                if tag.enclosed:
                    enclosed_count += 1
                tag_stack.append(tag)

                open_tag(tag)

                if tag.auto_close:
                    tag = tag_stack.pop()
                    tag.close(self, start_pos, len(nodes)-1)
                    close_tag(tag)

            else:

                if break_stack and break_stack[-1].name == tag_name:
                    break_stack.pop()
                    tag.close(parser, start_pos, len(nodes))
                elif check_tag_stack(tag_name):
                    while tag_stack[-1].name != tag_name:
                        tag = tag_stack.pop()
                        break_stack.append(tag)
                        close_tag(tag)

                    tag = tag_stack.pop()
                    tag.close(parser, start_pos, len(nodes))
                    if tag.enclosed:
                        enclosed_count -= 1

                    close_tag(tag)

                    if not tag.inline:
                        remove_next_newline = True

        if tag_stack:
            redo_break_stack()
            while tag_stack:
                tag = tag_stack.pop()
                tag.close(parser, len(post_markup), len(nodes))
                if tag.enclosed:
                    enclosed_count -= 1
                close_tag(tag)

        parser.phase = 2
        # Pass 2
        parser.nodes = nodes

        text = []
        parser.render_node_index = 0
        while parser.render_node_index < len(parser.nodes):
            i = parser.render_node_index
            node_text = parser.nodes[i]
            if callable(node_text):
                node_text = node_text(i)
            if node_text is not None:
                text.append(node_text)
            parser.render_node_index += 1

        html = u"".join(text)
        if clean:
            html = self.cleanup_html(html)
        return html

    # A shortcut for render_to_html
    __call__ = render_to_html


_postmarkup = create(use_pygments=pygments_available)
def render_bbcode(bbcode,
                  encoding="ascii",
                  exclude_tags=None,
                  auto_urls=True,
                  paragraphs=False,
                  clean=True,
                  tag_data=None):

    """ Renders a bbcode string in to XHTML. This is a shortcut if you don't
        need to customize any tags.

        post_markup -- String containing bbcode.
        encoding -- Encoding of string, defaults to "ascii" if the string is not
        already unicode.
        exclude_tags -- A collection of tag names to ignore.
        auto_urls -- If True, then urls will be wrapped with url bbcode tags.
        paragraphs -- If True then line breaks will be replaces with paragraph
        tags, rather than break tags.
        clean -- If True, html will be run through a cleanup_html method.
        tag_data -- An optional dictionary to store tag data in. The default of
        None will create a dictionary internally.

    """
    return _postmarkup(bbcode,
                       encoding,
                       exclude_tags=exclude_tags,
                       auto_urls=auto_urls,
                       paragraphs=paragraphs,
                       clean=clean,
                       tag_data=tag_data)



def _tests():

    import sys
    #sys.stdout=open('test.htm', 'w')

    post_markup = create(use_pygments=True)

    tests = []
    print """<link rel="stylesheet" href="code.css" type="text/css" />\n"""

    tests.append(']')
    tests.append('[')
    tests.append(':-[ Hello, [b]World[/b]')

    tests.append("[link=http://www.willmcgugan.com]My homepage[/link]")
    tests.append('[link="http://www.willmcgugan.com"]My homepage[/link]')
    tests.append("[link http://www.willmcgugan.com]My homepage[/link]")
    tests.append("[link]http://www.willmcgugan.com[/link]")

    tests.append(u"[b]Hello André[/b]")
    tests.append(u"[google]André[/google]")
    tests.append("[s]Strike through[/s]")
    tests.append("[b]bold [i]bold and italic[/b] italic[/i]")
    tests.append("[google]Will McGugan[/google]")
    tests.append("[wiki Will McGugan]Look up my name in Wikipedia[/wiki]")

    tests.append("[quote Will said...]BBCode is very cool[/quote]")

    tests.append("""[code python]
# A proxy object that calls a callback when converted to a string
class TagStringify(object):
    def __init__(self, callback, raw):
        self.callback = callback
        self.raw = raw
        r[b]=3
    def __str__(self):
        return self.callback()
    def __repr__(self):
        return self.__str__()
[/code]""")


    tests.append(u"[img]http://upload.wikimedia.org/wikipedia/commons"\
                 "/6/61/Triops_longicaudatus.jpg[/img]")

    tests.append("[list][*]Apples[*]Oranges[*]Pears[/list]")
    tests.append("""[list=1]
    [*]Apples
    [*]Oranges
    are not the only fruit
    [*]Pears
[/list]""")
    tests.append("[list=a][*]Apples[*]Oranges[*]Pears[/list]")
    tests.append("[list=A][*]Apples[*]Oranges[*]Pears[/list]")

    long_test="""[b]Long test[/b]

New lines characters are converted to breaks."""\
"""Tags my be [b]ove[i]rl[/b]apped[/i].

[i]Open tags will be closed.
[b]Test[/b]"""

    tests.append(long_test)

    tests.append("[dict]Will[/dict]")

    tests.append("[code unknownlanguage]10 print 'In yr code'; 20 goto 10[/code]")

    tests.append("[url=http://www.google.com/coop/cse?cx=006850030468302103399%3Amqxv78bdfdo]CakePHP Google Groups[/url]")
    tests.append("[url=http://www.google.com/search?hl=en&safe=off&client=opera&rls=en&hs=pO1&q=python+bbcode&btnG=Search]Search for Python BBCode[/url]")
    #tests = []
    # Attempt to inject html in to unicode
    tests.append("[url=http://www.test.com/sfsdfsdf/ter?t=\"></a><h1>HACK</h1><a>\"]Test Hack[/url]")

    tests.append('Nested urls, i.e. [url][url]www.becontrary.com[/url][/url], are condensed in to a single tag.')

    tests.append(u'[google]ɸβfvθðsz[/google]')

    tests.append(u'[size 30]Hello, World![/size]')

    tests.append(u'[color red]This should be red[/color]')
    tests.append(u'[color #0f0]This should be green[/color]')
    tests.append(u"[center]This should be in the center!")

    tests.append('Nested urls, i.e. [url][url]www.becontrary.com[/url][/url], are condensed in to a single tag.')

    #tests = []
    tests.append('[b]Hello, [i]World[/b]! [/i]')

    tests.append('[b][center]This should be centered![/center][/b]')

    tests.append('[list][*]Hello[i][*]World![/i][/list]')


    tests.append("""[list=1]
    [*]Apples
    [*]Oranges
    are not the only fruit
    [*]Pears
[/list]""")

    tests.append("[b]urls such as http://www.willmcgugan.com are authomaticaly converted to links[/b]")

    tests.append("""
[b]
[code python]
parser.markup[self.open_pos:self.close_pos]
[/code]
asdasdasdasdqweqwe
""")

    tests.append("""[list 1]
[*]Hello
[*]World
[/list]""")


    #tests = []
    tests.append("[b][p]Hello, [p]World")
    tests.append("[p][p][p]")

    tests.append("http://www.google.com/search?as_q=bbcode&btnG=%D0%9F%D0%BE%D0%B8%D1%81%D0%BA")

    #tests=["""[b]b[i]i[/b][/i]"""]

    for test in tests:
        print u"<pre>%s</pre>"%str(test.encode("ascii", "xmlcharrefreplace"))
        print u"<p>%s</p>"%str(post_markup(test).encode("ascii", "xmlcharrefreplace"))
        print u"<hr/>"
        print

    #print repr(post_markup('[url=<script>Attack</script>]Attack[/url]'))

    #print repr(post_markup('http://www.google.com/search?as_q=%D0%9F%D0%BE%D0%B8%D1%81%D0%BA&test=hai'))

    #p = create(use_pygments=False)
    #print (p('[code]foo\nbar[/code]'))

    #print render_bbcode("[b]For the lazy, use the http://www.willmcgugan.com render_bbcode function.[/b]")

    smarkup = create()
    smarkup.add_tag(SectionTag, 'section')

    test = """Hello, World.[b][i]This in italics
[section sidebar]This is the [b]sidebar[/b][/section]
[section footer]
This is the footer
[/section]
More text"""

    print smarkup(test, paragraphs=True, clean=False)
    tag_data = {}
    print smarkup(test, tag_data=tag_data, paragraphs=True, clean=True)
    print tag_data

def _run_unittests():

    # TODO: Expand tests for better coverage!

    import unittest

    class TestPostmarkup(unittest.TestCase):

        def testcleanuphtml(self):

            postmarkup = create()

            tests = [("""\n<p>\n </p>\n""", ""),
                     ("""<b>\n\n<i>   </i>\n</b>Test""", "Test"),
                     ("""<p id="test">Test</p>""", """<p id="test">Test</p>"""),]

            for test, result in tests:
                self.assertEqual(PostMarkup.cleanup_html(test).strip(), result)


        def testsimpletag(self):

            postmarkup = create()

            tests= [ ('[b]Hello[/b]', "<strong>Hello</strong>"),
                     ('[i]Italic[/i]', "<em>Italic</em>"),
                     ('[s]Strike[/s]', "<strike>Strike</strike>"),
                     ('[u]underlined[/u]', "<u>underlined</u>"),
                     ]

            for test, result in tests:
                self.assertEqual(postmarkup(test), result)


        def testoverlap(self):

            postmarkup = create()

            tests= [ ('[i][b]Hello[/i][/b]', "<em><strong>Hello</strong></em>"),
                     ('[b]bold [u]both[/b] underline[/u]', '<strong>bold <u>both</u></strong><u> underline</u>')
                     ]

            for test, result in tests:
                self.assertEqual(postmarkup(test), result)

        def testlinks(self):

            postmarkup = create(annotate_links=False)

            tests= [ ('[link=http://www.willmcgugan.com]blog1[/link]', '<a href="http://www.willmcgugan.com">blog1</a>'),
                     ('[link="http://www.willmcgugan.com"]blog2[/link]', '<a href="http://www.willmcgugan.com">blog2</a>'),
                     ('[link http://www.willmcgugan.com]blog3[/link]', '<a href="http://www.willmcgugan.com">blog3</a>'),
                     ('[link]http://www.willmcgugan.com[/link]', '<a href="http://www.willmcgugan.com">http://www.willmcgugan.com</a>')
                     ]

            for test, result in tests:
                self.assertEqual(postmarkup(test), result)


    suite = unittest.TestLoader().loadTestsFromTestCase(TestPostmarkup)
    unittest.TextTestRunner(verbosity=2).run(suite)


def _ff_test():

    def ff1(post, pos, c1, c2):
        f1 = post.find(c1, pos)
        f2 = post.find(c2, pos)
        if f1 == -1:
            return f2
        if f2 == -1:
            return f1
        return min(f1, f2)

    re_ff=re.compile('a|b', re.UNICODE)

    def ff2(post, pos, c1, c2):
        try:
            return re_ff.search(post).group(0)
        except AttributeError:
            return -1

    text = u"sdl;fk;sdlfks;dflksd;flksdfsdfwerwerwgwegwegwegwegwegegwweggewwegwegwegwettttttttttttttttttttttttttttttttttgggggggggg;slbdfkwelrkwelrkjal;sdfksdl;fksdf;lb"

    REPEAT = 100000

    from time import time

    start = time()
    for n in xrange(REPEAT):
        ff1(text, 0, "a", "b")
    end = time()
    print end - start

    start = time()
    for n in xrange(REPEAT):
        ff2(text, 0, "a", "b")
    end = time()
    print end - start



if __name__ == "__main__":

    _tests()
    _run_unittests()
    #_ff_test()

########NEW FILE########
__FILENAME__ = daily_updates
from django.core.management.base import NoArgsCommand
from django.template.loader import render_to_string
from django.contrib.sites.models import Site
from django.contrib.auth.models import User

from mailer import send_html_mail

import datetime

from dinette.models import Ftopics, Reply, DinetteUserProfile

class Command(NoArgsCommand):
    help = """
           Cron job to send daily updates to subscribed users
           Sample cron usage:
           python manage.py daily_updates
           """
    
    def handle_noargs(self, **options):
        site = Site.objects.get_current()
        subject = "Daily Digest: %s" %( site.name)
        from_address = '%s notifications <admin@%s>' %(site.name, site.domain)
        to_address = User.objects.filter(dinetteuserprofile__is_subscribed_to_digest=True).values_list('email', flat=True)
        
        yesterday = datetime.datetime.now() - datetime.timedelta(1)
        topics = Ftopics.objects.filter(created_on__gt=yesterday)
        replies = Reply.objects.filter(updated_on__gt=yesterday)
        users = DinetteUserProfile.objects.filter(user__date_joined__gt=yesterday)
        active_users = DinetteUserProfile.objects.filter(user__last_login__gt=yesterday)

        if any([topics, replies, users, active_users]):
            variables = {'site': site, 'topics': topics, 'replies': replies, 'users': users, 'active_users': active_users}
            html_message = render_to_string('dinette/email/daily_updates.html', variables)
            send_html_mail(subject, html_message, html_message, from_address, to_address)


########NEW FILE########
__FILENAME__ = middleware
import datetime

from dinette.models import DinetteUserProfile


class UserActivity:
    def process_request(self, req):
        if req.user.is_authenticated():
            #last = req.user.get_profile().last_activity
            try:
                try:
                    user_profile = req.user.get_profile()
                except DinetteUserProfile.DoesNotExist:
                    now = datetime.datetime.now()
                    user_profile, created = DinetteUserProfile.objects.get_or_create(user = req.user, last_activity = now, last_session_activity = now)
                now = datetime.datetime.now()
                user_profile.last_activity=now
                dinette_activity_at = req.session.get("dinette_activity_at", [])
                req.session["dinette_activity_at"] = dinette_activity_at = rotate_with(dinette_activity_at, now)
                user_profile.last_session_activity = dinette_activity_at[0]
                user_profile.save()
            except:
                from django.conf import settings
                if settings.DEBUG:
                    raise
                else:
                    pass


def get_last_activity_with_hour_offset(lst, now = None):
    "Given a list of datetimes, find the most recent time which is at least one hour ago"
    if not now:
        now = datetime.datetime.now()
    from copy import deepcopy
    lst = deepcopy(lst)
    lst.reverse()
    for el in lst:
        if now - el > datetime.timedelta(hours =1):
            return el
    
            
def rotate_with(lst, el, maxsize = 10):
    """
    >>> rotate_with(range(5), 200)
    [200, 0, 1, 2, 3]
    >>> rotate_with(range(10), -1)
    [-1, 0, 1, 2, 3, 4, 5, 6, 7, 8]
    >>> rotate_with([], 1)
    [1]
    >>> rotate_with([5, 2], -1)
    [-1, 5, 2]
    """
    if len(lst)>=maxsize:
        lst.pop()
    lst.insert(0, el)
    return lst

########NEW FILE########
__FILENAME__ = 0001_initial

from south.db import db
from django.db import models
from dinette.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'DinetteUserProfile'
        db.create_table('dinette_dinetteuserprofile', (
            ('id', orm['dinette.DinetteUserProfile:id']),
            ('user', orm['dinette.DinetteUserProfile:user']),
            ('last_activity', orm['dinette.DinetteUserProfile:last_activity']),
            ('userrank', orm['dinette.DinetteUserProfile:userrank']),
            ('last_posttime', orm['dinette.DinetteUserProfile:last_posttime']),
            ('photo', orm['dinette.DinetteUserProfile:photo']),
            ('signature', orm['dinette.DinetteUserProfile:signature']),
        ))
        db.send_create_signal('dinette', ['DinetteUserProfile'])
        
        # Adding model 'Ftopics'
        db.create_table('dinette_ftopics', (
            ('id', orm['dinette.Ftopics:id']),
            ('category', orm['dinette.Ftopics:category']),
            ('subject', orm['dinette.Ftopics:subject']),
            ('slug', orm['dinette.Ftopics:slug']),
            ('message', orm['dinette.Ftopics:message']),
            ('file', orm['dinette.Ftopics:file']),
            ('attachment_type', orm['dinette.Ftopics:attachment_type']),
            ('filename', orm['dinette.Ftopics:filename']),
            ('viewcount', orm['dinette.Ftopics:viewcount']),
            ('replies', orm['dinette.Ftopics:replies']),
            ('created_on', orm['dinette.Ftopics:created_on']),
            ('updated_on', orm['dinette.Ftopics:updated_on']),
            ('posted_by', orm['dinette.Ftopics:posted_by']),
            ('announcement_flag', orm['dinette.Ftopics:announcement_flag']),
            ('is_closed', orm['dinette.Ftopics:is_closed']),
            ('is_sticky', orm['dinette.Ftopics:is_sticky']),
            ('is_hidden', orm['dinette.Ftopics:is_hidden']),
        ))
        db.send_create_signal('dinette', ['Ftopics'])
        
        # Adding model 'SiteConfig'
        db.create_table('dinette_siteconfig', (
            ('id', orm['dinette.SiteConfig:id']),
            ('name', orm['dinette.SiteConfig:name']),
            ('tag_line', orm['dinette.SiteConfig:tag_line']),
        ))
        db.send_create_signal('dinette', ['SiteConfig'])
        
        # Adding model 'Category'
        db.create_table('dinette_category', (
            ('id', orm['dinette.Category:id']),
            ('name', orm['dinette.Category:name']),
            ('slug', orm['dinette.Category:slug']),
            ('description', orm['dinette.Category:description']),
            ('ordering', orm['dinette.Category:ordering']),
            ('super_category', orm['dinette.Category:super_category']),
            ('created_on', orm['dinette.Category:created_on']),
            ('updated_on', orm['dinette.Category:updated_on']),
            ('posted_by', orm['dinette.Category:posted_by']),
        ))
        db.send_create_signal('dinette', ['Category'])
        
        # Adding model 'Reply'
        db.create_table('dinette_reply', (
            ('id', orm['dinette.Reply:id']),
            ('topic', orm['dinette.Reply:topic']),
            ('posted_by', orm['dinette.Reply:posted_by']),
            ('message', orm['dinette.Reply:message']),
            ('file', orm['dinette.Reply:file']),
            ('attachment_type', orm['dinette.Reply:attachment_type']),
            ('filename', orm['dinette.Reply:filename']),
            ('created_on', orm['dinette.Reply:created_on']),
            ('updated_on', orm['dinette.Reply:updated_on']),
        ))
        db.send_create_signal('dinette', ['Reply'])
        
        # Adding model 'SuperCategory'
        db.create_table('dinette_supercategory', (
            ('id', orm['dinette.SuperCategory:id']),
            ('name', orm['dinette.SuperCategory:name']),
            ('description', orm['dinette.SuperCategory:description']),
            ('ordering', orm['dinette.SuperCategory:ordering']),
            ('created_on', orm['dinette.SuperCategory:created_on']),
            ('updated_on', orm['dinette.SuperCategory:updated_on']),
            ('posted_by', orm['dinette.SuperCategory:posted_by']),
        ))
        db.send_create_signal('dinette', ['SuperCategory'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'DinetteUserProfile'
        db.delete_table('dinette_dinetteuserprofile')
        
        # Deleting model 'Ftopics'
        db.delete_table('dinette_ftopics')
        
        # Deleting model 'SiteConfig'
        db.delete_table('dinette_siteconfig')
        
        # Deleting model 'Category'
        db.delete_table('dinette_category')
        
        # Deleting model 'Reply'
        db.delete_table('dinette_reply')
        
        # Deleting model 'SuperCategory'
        db.delete_table('dinette_supercategory')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dinette.category': {
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderated_by': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cposted'", 'to': "orm['auth.User']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'super_category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.SuperCategory']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.dinetteuserprofile': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'dinette.ftopics': {
            'announcement_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'replies': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '1034', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'viewcount': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'dinette.reply': {
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Ftopics']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.siteconfig': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tag_line': ('django.db.models.fields.TextField', [], {'max_length': '100'})
        },
        'dinette.supercategory': {
            'accessgroups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['dinette']

########NEW FILE########
__FILENAME__ = 0002_reply_num

from south.db import db
from django.db import models
from dinette.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding field 'Reply.reply_number'
        db.add_column('dinette_reply', 'reply_number', orm['dinette.reply:reply_number'])
        
    
    
    def backwards(self, orm):
        
        # Deleting field 'Reply.reply_number'
        db.delete_column('dinette_reply', 'reply_number')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dinette.category': {
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderated_by': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cposted'", 'to': "orm['auth.User']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'super_category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.SuperCategory']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.dinetteuserprofile': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'dinette.ftopics': {
            'announcement_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'replies': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '1034', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'viewcount': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'dinette.reply': {
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'reply_number': ('django.db.models.fields.SmallIntegerField', [], {}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Ftopics']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.siteconfig': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tag_line': ('django.db.models.fields.TextField', [], {'max_length': '100'})
        },
        'dinette.supercategory': {
            'accessgroups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['dinette']

########NEW FILE########
__FILENAME__ = 0003_num_replies

from south.db import db
from django.db import models
from dinette.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding field 'Ftopics.last_reply_on'
        db.add_column('dinette_ftopics', 'last_reply_on', orm['dinette.ftopics:last_reply_on'])
        
        # Adding field 'Ftopics.num_replies'
        db.add_column('dinette_ftopics', 'num_replies', orm['dinette.ftopics:num_replies'])
        
        # Changing field 'Ftopics.slug'
        # (to signature: django.db.models.fields.SlugField(max_length=200, db_index=True))
        db.alter_column('dinette_ftopics', 'slug', orm['dinette.ftopics:slug'])
        
        # Changing field 'Ftopics.subject'
        # (to signature: django.db.models.fields.CharField(max_length=999))
        db.alter_column('dinette_ftopics', 'subject', orm['dinette.ftopics:subject'])
        
    
    
    def backwards(self, orm):
        
        # Deleting field 'Ftopics.last_reply_on'
        db.delete_column('dinette_ftopics', 'last_reply_on')
        
        # Deleting field 'Ftopics.num_replies'
        db.delete_column('dinette_ftopics', 'num_replies')
        
        # Changing field 'Ftopics.slug'
        # (to signature: django.db.models.fields.SlugField(max_length=1034, db_index=True))
        db.alter_column('dinette_ftopics', 'slug', orm['dinette.ftopics:slug'])
        
        # Changing field 'Ftopics.subject'
        # (to signature: django.db.models.fields.CharField(max_length=1024))
        db.alter_column('dinette_ftopics', 'subject', orm['dinette.ftopics:subject'])
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dinette.category': {
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderated_by': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cposted'", 'to': "orm['auth.User']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'super_category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.SuperCategory']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.dinetteuserprofile': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'dinette.ftopics': {
            'announcement_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'replies': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '200', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'viewcount': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'dinette.reply': {
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'reply_number': ('django.db.models.fields.SmallIntegerField', [], {}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Ftopics']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.siteconfig': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tag_line': ('django.db.models.fields.TextField', [], {'max_length': '100'})
        },
        'dinette.supercategory': {
            'accessgroups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['dinette']

########NEW FILE########
__FILENAME__ = 0004_populate_values

from south.db import db
from django.db import models
from dinette.models import *

class Migration:
    
    def forwards(self, orm):
        "Write your forwards migration here"
        topics = orm.Ftopics.objects.all()
        for topic in topics:
            topic.num_replies = topic.reply_set.count()
            if topic.reply_set.count():
                last_reply = topic.reply_set.order_by("-created_on")[0]
                topic.last_reply_on = last_reply.created_on
            else:
                topic.last_reply_on = topic.created_on
            topic.save()
        
        replies = Reply.objects.all()
        for reply in replies:
            reply.reply_number = Reply.objects.filter(topic = reply.topic, created_on__lte = reply.created_on).count()
            reply.save()
        
            
        
    
    
    def backwards(self, orm):
        "Write your backwards migration here"
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dinette.category': {
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderated_by': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cposted'", 'to': "orm['auth.User']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'super_category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.SuperCategory']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.dinetteuserprofile': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'dinette.ftopics': {
            'announcement_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'replies': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '200', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'viewcount': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'dinette.reply': {
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'reply_number': ('django.db.models.fields.SmallIntegerField', [], {}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Ftopics']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.siteconfig': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tag_line': ('django.db.models.fields.TextField', [], {'max_length': '100'})
        },
        'dinette.supercategory': {
            'accessgroups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['dinette']

Migration.no_dry_run = True



########NEW FILE########
__FILENAME__ = 0005_unique_profiles

from south.db import db
from django.db import models
from dinette.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Creating unique_together for [user] on DinetteUserProfile.
        db.create_unique('dinette_dinetteuserprofile', ['user_id'])
        
    
    
    def backwards(self, orm):
        
        # Deleting unique_together for [user] on DinetteUserProfile.
        db.delete_unique('dinette_dinetteuserprofile', ['user_id'])
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dinette.category': {
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderated_by': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cposted'", 'to': "orm['auth.User']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'super_category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.SuperCategory']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.dinetteuserprofile': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'dinette.ftopics': {
            'announcement_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'replies': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '200', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'viewcount': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'dinette.reply': {
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'reply_number': ('django.db.models.fields.SmallIntegerField', [], {}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Ftopics']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.siteconfig': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tag_line': ('django.db.models.fields.TextField', [], {'max_length': '100'})
        },
        'dinette.supercategory': {
            'accessgroups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['dinette']

########NEW FILE########
__FILENAME__ = 0006_profile

from south.db import db
from django.db import models
from dinette.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Changing field 'DinetteUserProfile.last_activity'
        # (to signature: django.db.models.fields.DateTimeField())
        db.alter_column('dinette_dinetteuserprofile', 'last_activity', orm['dinette.dinetteuserprofile:last_activity'])
        
    
    
    def backwards(self, orm):
        
        # Changing field 'DinetteUserProfile.last_activity'
        # (to signature: django.db.models.fields.DateTimeField(auto_now_add=True, blank=True))
        db.alter_column('dinette_dinetteuserprofile', 'last_activity', orm['dinette.dinetteuserprofile:last_activity'])
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dinette.category': {
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderated_by': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cposted'", 'to': "orm['auth.User']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'super_category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.SuperCategory']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.dinetteuserprofile': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'dinette.ftopics': {
            'announcement_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'replies': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '200', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'viewcount': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'dinette.reply': {
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'reply_number': ('django.db.models.fields.SmallIntegerField', [], {}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Ftopics']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.siteconfig': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tag_line': ('django.db.models.fields.TextField', [], {'max_length': '100'})
        },
        'dinette.supercategory': {
            'accessgroups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['dinette']

########NEW FILE########
__FILENAME__ = 0007_profile_last_sessiom

from south.db import db
from django.db import models
from dinette.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding field 'DinetteUserProfile.last_session_activity'
        db.add_column('dinette_dinetteuserprofile', 'last_session_activity', orm['dinette.dinetteuserprofile:last_session_activity'])
        
    
    
    def backwards(self, orm):
        
        # Deleting field 'DinetteUserProfile.last_session_activity'
        db.delete_column('dinette_dinetteuserprofile', 'last_session_activity')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dinette.category': {
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderated_by': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cposted'", 'to': "orm['auth.User']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'super_category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.SuperCategory']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.dinetteuserprofile': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_session_activity': ('django.db.models.fields.DateTimeField', [], {}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'dinette.ftopics': {
            'announcement_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'replies': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '200', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'viewcount': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'dinette.reply': {
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'reply_number': ('django.db.models.fields.SmallIntegerField', [], {}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Ftopics']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.siteconfig': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tag_line': ('django.db.models.fields.TextField', [], {'max_length': '100'})
        },
        'dinette.supercategory': {
            'accessgroups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['dinette']

########NEW FILE########
__FILENAME__ = 0008_nav_links

from south.db import db
from django.db import models
from dinette.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'NavLink'
        db.create_table('dinette_navlink', (
            ('id', orm['dinette.navlink:id']),
            ('title', orm['dinette.navlink:title']),
            ('url', orm['dinette.navlink:url']),
        ))
        db.send_create_signal('dinette', ['NavLink'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'NavLink'
        db.delete_table('dinette_navlink')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dinette.category': {
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderated_by': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cposted'", 'to': "orm['auth.User']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'super_category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.SuperCategory']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.dinetteuserprofile': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_session_activity': ('django.db.models.fields.DateTimeField', [], {}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'dinette.ftopics': {
            'announcement_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'replies': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '200', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'viewcount': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'dinette.navlink': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'dinette.reply': {
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'reply_number': ('django.db.models.fields.SmallIntegerField', [], {}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Ftopics']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.siteconfig': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tag_line': ('django.db.models.fields.TextField', [], {'max_length': '100'})
        },
        'dinette.supercategory': {
            'accessgroups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['dinette']

########NEW FILE########
__FILENAME__ = 0009_markup
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'DinetteUserProfile.last_activity'
        db.alter_column('dinette_dinetteuserprofile', 'last_activity', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True))

        # Changing field 'DinetteUserProfile.last_session_activity'
        db.alter_column('dinette_dinetteuserprofile', 'last_session_activity', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True))

        # Adding field 'Ftopics.message_markup_type'
        db.add_column('dinette_ftopics', 'message_markup_type', self.gf('django.db.models.fields.CharField')(default='markdown', max_length=30), keep_default=False)

        # Adding field 'Ftopics._message_rendered'
        db.add_column('dinette_ftopics', '_message_rendered', self.gf('django.db.models.fields.TextField')(default=''), keep_default=False)

        # Changing field 'Ftopics.message'
        db.alter_column('dinette_ftopics', 'message', self.gf('markupfield.fields.MarkupField')())

        # Adding field 'Reply.message_markup_type'
        db.add_column('dinette_reply', 'message_markup_type', self.gf('django.db.models.fields.CharField')(default='markdown', max_length=30), keep_default=False)

        # Adding field 'Reply._message_rendered'
        db.add_column('dinette_reply', '_message_rendered', self.gf('django.db.models.fields.TextField')(default=''), keep_default=False)

        # Changing field 'Reply.message'
        db.alter_column('dinette_reply', 'message', self.gf('markupfield.fields.MarkupField')())


    def backwards(self, orm):
        
        # Changing field 'DinetteUserProfile.last_activity'
        db.alter_column('dinette_dinetteuserprofile', 'last_activity', self.gf('django.db.models.fields.DateTimeField')())

        # Changing field 'DinetteUserProfile.last_session_activity'
        db.alter_column('dinette_dinetteuserprofile', 'last_session_activity', self.gf('django.db.models.fields.DateTimeField')())

        # Deleting field 'Ftopics.message_markup_type'
        db.delete_column('dinette_ftopics', 'message_markup_type')

        # Deleting field 'Ftopics._message_rendered'
        db.delete_column('dinette_ftopics', '_message_rendered')

        # Changing field 'Ftopics.message'
        db.alter_column('dinette_ftopics', 'message', self.gf('django.db.models.fields.TextField')())

        # Deleting field 'Reply.message_markup_type'
        db.delete_column('dinette_reply', 'message_markup_type')

        # Deleting field 'Reply._message_rendered'
        db.delete_column('dinette_reply', '_message_rendered')

        # Changing field 'Reply.message'
        db.alter_column('dinette_reply', 'message', self.gf('django.db.models.fields.TextField')())


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dinette.category': {
            'Meta': {'object_name': 'Category'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderated_by': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'moderaters'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cposted'", 'to': "orm['auth.User']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'super_category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.SuperCategory']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.dinetteuserprofile': {
            'Meta': {'object_name': 'DinetteUserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_session_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'dinette.ftopics': {
            'Meta': {'object_name': 'Ftopics'},
            '_message_rendered': ('django.db.models.fields.TextField', [], {}),
            'announcement_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'message': ('markupfield.fields.MarkupField', [], {}),
            'message_markup_type': ('django.db.models.fields.CharField', [], {'default': "'markdown'", 'max_length': '30'}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'replies': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '200', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'viewcount': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'dinette.navlink': {
            'Meta': {'object_name': 'NavLink'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'dinette.reply': {
            'Meta': {'object_name': 'Reply'},
            '_message_rendered': ('django.db.models.fields.TextField', [], {}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('markupfield.fields.MarkupField', [], {}),
            'message_markup_type': ('django.db.models.fields.CharField', [], {'default': "'markdown'", 'max_length': '30'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'reply_number': ('django.db.models.fields.SmallIntegerField', [], {}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Ftopics']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.siteconfig': {
            'Meta': {'object_name': 'SiteConfig'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tag_line': ('django.db.models.fields.TextField', [], {'max_length': '100'})
        },
        'dinette.supercategory': {
            'Meta': {'object_name': 'SuperCategory'},
            'accessgroups': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'can_access_forums'", 'symmetrical': 'False', 'to': "orm['auth.Group']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['dinette']

########NEW FILE########
__FILENAME__ = 0010_migrate_reply_markup
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

from dinette.libs.postmarkup import render_bbcode

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        for reply in orm.Reply.objects.all():
            # migrate older bbcode replies to markup
            reply._message_rendered = render_bbcode(reply.message.raw)
            reply.save()

    def backwards(self, orm):
        "Write your backwards methods here."


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dinette.category': {
            'Meta': {'object_name': 'Category'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderated_by': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'moderaters'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cposted'", 'to': "orm['auth.User']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'super_category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.SuperCategory']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.dinetteuserprofile': {
            'Meta': {'object_name': 'DinetteUserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_session_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'dinette.ftopics': {
            'Meta': {'object_name': 'Ftopics'},
            '_message_rendered': ('django.db.models.fields.TextField', [], {}),
            'announcement_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'message': ('markupfield.fields.MarkupField', [], {}),
            'message_markup_type': ('django.db.models.fields.CharField', [], {'default': "'markdown'", 'max_length': '30'}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'replies': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '200', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'viewcount': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'dinette.navlink': {
            'Meta': {'object_name': 'NavLink'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'dinette.reply': {
            'Meta': {'object_name': 'Reply'},
            '_message_rendered': ('django.db.models.fields.TextField', [], {}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('markupfield.fields.MarkupField', [], {}),
            'message_markup_type': ('django.db.models.fields.CharField', [], {'default': "'markdown'", 'max_length': '30'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'reply_number': ('django.db.models.fields.SmallIntegerField', [], {}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Ftopics']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.siteconfig': {
            'Meta': {'object_name': 'SiteConfig'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tag_line': ('django.db.models.fields.TextField', [], {'max_length': '100'})
        },
        'dinette.supercategory': {
            'Meta': {'object_name': 'SuperCategory'},
            'accessgroups': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'can_access_forums'", 'symmetrical': 'False', 'to': "orm['auth.Group']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['dinette']

########NEW FILE########
__FILENAME__ = 0011_userprofile_slug
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'DinetteUserProfile.slug'
        db.add_column('dinette_dinetteuserprofile', 'slug', self.gf('django.db.models.fields.SlugField')(default='', max_length=200, db_index=True), keep_default=False)

    def backwards(self, orm):
        
        # Deleting field 'DinetteUserProfile.slug'
        db.delete_column('dinette_dinetteuserprofile', 'slug')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dinette.category': {
            'Meta': {'object_name': 'Category'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderated_by': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'moderaters'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cposted'", 'to': "orm['auth.User']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'super_category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.SuperCategory']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.dinetteuserprofile': {
            'Meta': {'object_name': 'DinetteUserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_session_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '200', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'dinette.ftopics': {
            'Meta': {'object_name': 'Ftopics'},
            '_message_rendered': ('django.db.models.fields.TextField', [], {}),
            'announcement_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'message': ('markupfield.fields.MarkupField', [], {}),
            'message_markup_type': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '30'}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'replies': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '200', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'viewcount': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'dinette.navlink': {
            'Meta': {'object_name': 'NavLink'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'dinette.reply': {
            'Meta': {'object_name': 'Reply'},
            '_message_rendered': ('django.db.models.fields.TextField', [], {}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('markupfield.fields.MarkupField', [], {}),
            'message_markup_type': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '30'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'reply_number': ('django.db.models.fields.SmallIntegerField', [], {}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Ftopics']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.siteconfig': {
            'Meta': {'object_name': 'SiteConfig'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tag_line': ('django.db.models.fields.TextField', [], {'max_length': '100'})
        },
        'dinette.supercategory': {
            'Meta': {'object_name': 'SuperCategory'},
            'accessgroups': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'can_access_forums'", 'symmetrical': 'False', 'to': "orm['auth.Group']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['dinette']

########NEW FILE########
__FILENAME__ = 0012_populate_slugs
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from django.template.defaultfilters import slugify

class Migration(DataMigration):

    def forwards(self, orm):
        for profile in orm.DinetteUserProfile.objects.all():
            slug = slugify(profile.user.username)
            if slug == "":
                slug = profile.user.id
            profile.slug = slug
            profile.save()
        "Write your forwards methods here."


    def backwards(self, orm):
        "Write your backwards methods here."


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dinette.category': {
            'Meta': {'object_name': 'Category'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderated_by': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'moderaters'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cposted'", 'to': "orm['auth.User']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'super_category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.SuperCategory']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.dinetteuserprofile': {
            'Meta': {'object_name': 'DinetteUserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_session_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '200', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'dinette.ftopics': {
            'Meta': {'object_name': 'Ftopics'},
            '_message_rendered': ('django.db.models.fields.TextField', [], {}),
            'announcement_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'message': ('markupfield.fields.MarkupField', [], {}),
            'message_markup_type': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '30'}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'replies': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '200', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'viewcount': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'dinette.navlink': {
            'Meta': {'object_name': 'NavLink'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'dinette.reply': {
            'Meta': {'object_name': 'Reply'},
            '_message_rendered': ('django.db.models.fields.TextField', [], {}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('markupfield.fields.MarkupField', [], {}),
            'message_markup_type': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '30'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'reply_number': ('django.db.models.fields.SmallIntegerField', [], {}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Ftopics']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.siteconfig': {
            'Meta': {'object_name': 'SiteConfig'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tag_line': ('django.db.models.fields.TextField', [], {'max_length': '100'})
        },
        'dinette.supercategory': {
            'Meta': {'object_name': 'SuperCategory'},
            'accessgroups': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'can_access_forums'", 'symmetrical': 'False', 'to': "orm['auth.Group']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['dinette']

########NEW FILE########
__FILENAME__ = 0013_auto__add_unique_dinetteuserprofile_slug
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding unique constraint on 'DinetteUserProfile', fields ['slug']
        db.create_unique('dinette_dinetteuserprofile', ['slug'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'DinetteUserProfile', fields ['slug']
        db.delete_unique('dinette_dinetteuserprofile', ['slug'])


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dinette.category': {
            'Meta': {'object_name': 'Category'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderated_by': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'moderaters'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cposted'", 'to': "orm['auth.User']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'super_category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.SuperCategory']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.dinetteuserprofile': {
            'Meta': {'object_name': 'DinetteUserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_session_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '200', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'dinette.ftopics': {
            'Meta': {'object_name': 'Ftopics'},
            '_message_rendered': ('django.db.models.fields.TextField', [], {}),
            'announcement_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'message': ('markupfield.fields.MarkupField', [], {}),
            'message_markup_type': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '30'}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'replies': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '200', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'viewcount': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'dinette.navlink': {
            'Meta': {'object_name': 'NavLink'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'dinette.reply': {
            'Meta': {'object_name': 'Reply'},
            '_message_rendered': ('django.db.models.fields.TextField', [], {}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('markupfield.fields.MarkupField', [], {}),
            'message_markup_type': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '30'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'reply_number': ('django.db.models.fields.SmallIntegerField', [], {}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Ftopics']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.siteconfig': {
            'Meta': {'object_name': 'SiteConfig'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tag_line': ('django.db.models.fields.TextField', [], {'max_length': '100'})
        },
        'dinette.supercategory': {
            'Meta': {'object_name': 'SuperCategory'},
            'accessgroups': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'can_access_forums'", 'symmetrical': 'False', 'to': "orm['auth.Group']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['dinette']

########NEW FILE########
__FILENAME__ = 0014_add_subscriptions
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding M2M table for field subscribers on 'Ftopics'
        db.create_table('dinette_ftopics_subscribers', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('ftopics', models.ForeignKey(orm['dinette.ftopics'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('dinette_ftopics_subscribers', ['ftopics_id', 'user_id'])


    def backwards(self, orm):
        
        # Removing M2M table for field subscribers on 'Ftopics'
        db.delete_table('dinette_ftopics_subscribers')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dinette.category': {
            'Meta': {'object_name': 'Category'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderated_by': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'moderaters'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cposted'", 'to': "orm['auth.User']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'super_category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.SuperCategory']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.dinetteuserprofile': {
            'Meta': {'object_name': 'DinetteUserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_session_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '200', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'dinette.ftopics': {
            'Meta': {'object_name': 'Ftopics'},
            '_message_rendered': ('django.db.models.fields.TextField', [], {}),
            'announcement_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'message': ('markupfield.fields.MarkupField', [], {}),
            'message_markup_type': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '30'}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'replies': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '200', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'subscribers'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'viewcount': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'dinette.navlink': {
            'Meta': {'object_name': 'NavLink'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'dinette.reply': {
            'Meta': {'object_name': 'Reply'},
            '_message_rendered': ('django.db.models.fields.TextField', [], {}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('markupfield.fields.MarkupField', [], {}),
            'message_markup_type': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '30'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'reply_number': ('django.db.models.fields.SmallIntegerField', [], {}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Ftopics']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.siteconfig': {
            'Meta': {'object_name': 'SiteConfig'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tag_line': ('django.db.models.fields.TextField', [], {'max_length': '100'})
        },
        'dinette.supercategory': {
            'Meta': {'object_name': 'SuperCategory'},
            'accessgroups': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'can_access_forums'", 'symmetrical': 'False', 'to': "orm['auth.Group']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['dinette']

########NEW FILE########
__FILENAME__ = 0015_add_digest_subscription
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'DinetteUserProfile.is_subscribed_to_digest'
        db.add_column('dinette_dinetteuserprofile', 'is_subscribed_to_digest', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'DinetteUserProfile.is_subscribed_to_digest'
        db.delete_column('dinette_dinetteuserprofile', 'is_subscribed_to_digest')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dinette.category': {
            'Meta': {'object_name': 'Category'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderated_by': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'moderaters'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cposted'", 'to': "orm['auth.User']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '110', 'db_index': 'True'}),
            'super_category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.SuperCategory']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.dinetteuserprofile': {
            'Meta': {'object_name': 'DinetteUserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_subscribed_to_digest': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_posttime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_session_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '200', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'userrank': ('django.db.models.fields.CharField', [], {'default': "'Junior Member'", 'max_length': '30'})
        },
        'dinette.ftopics': {
            'Meta': {'object_name': 'Ftopics'},
            '_message_rendered': ('django.db.models.fields.TextField', [], {}),
            'announcement_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Category']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_closed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_reply_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'message': ('markupfield.fields.MarkupField', [], {}),
            'message_markup_type': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '30'}),
            'num_replies': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'replies': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '200', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '999'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'subscribers'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'viewcount': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'dinette.navlink': {
            'Meta': {'object_name': 'NavLink'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'dinette.reply': {
            'Meta': {'object_name': 'Reply'},
            '_message_rendered': ('django.db.models.fields.TextField', [], {}),
            'attachment_type': ('django.db.models.fields.CharField', [], {'default': "'nofile'", 'max_length': '20'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "'dummyname.txt'", 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('markupfield.fields.MarkupField', [], {}),
            'message_markup_type': ('django.db.models.fields.CharField', [], {'default': "'bbcode'", 'max_length': '30'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'reply_number': ('django.db.models.fields.SmallIntegerField', [], {}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dinette.Ftopics']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'dinette.siteconfig': {
            'Meta': {'object_name': 'SiteConfig'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tag_line': ('django.db.models.fields.TextField', [], {'max_length': '100'})
        },
        'dinette.supercategory': {
            'Meta': {'object_name': 'SuperCategory'},
            'accessgroups': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'can_access_forums'", 'symmetrical': 'False', 'to': "orm['auth.Group']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['dinette']

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User, Group
from django.conf import settings
from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify
from django.db.models.signals import post_save
from django.template.defaultfilters import truncatewords
from django.core.urlresolvers import reverse

import hashlib
from BeautifulSoup import BeautifulSoup
import datetime
from dinette.libs.postmarkup import render_bbcode
from markupfield.fields import MarkupField

class SiteConfig(models.Model):
    name = models.CharField(max_length = 100)
    tag_line = models.TextField(max_length = 100)

class SuperCategory(models.Model):
    name = models.CharField(max_length = 100)
    description = models.TextField(default='')
    ordering = models.PositiveIntegerField(default = 1)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    posted_by = models.ForeignKey(User)
    accessgroups = models.ManyToManyField(Group, related_name='can_access_forums')
    
    class Meta:
        verbose_name = "Super Category"
        verbose_name_plural = "Super Categories"
        ordering = ('-ordering', 'created_on')
        
    def __unicode__(self):
        return self.name
 
    
class Category(models.Model):
    name = models.CharField(max_length = 100)
    slug = models.SlugField(max_length = 110)
    description = models.TextField(default='')
    ordering = models.PositiveIntegerField(default = 1)
    super_category = models.ForeignKey(SuperCategory)    
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    posted_by = models.ForeignKey(User, related_name='cposted')
    moderated_by = models.ManyToManyField(User, related_name='moderaters')
    
    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ('ordering','-created_on')
    
    def save(self, *args, **kwargs):
        if not self.slug:
            slug = slugify(self.name)
            same_slug_count = Category.objects.filter(slug__startswith = slug).count()
            if same_slug_count:
                slug = slug + str(same_slug_count)
            self.slug = slug
        super(Category, self).save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse("dinette_index", args=[self.slug])
    
    def getCategoryString(self):
        return "category/%s" % self.slug
    
    def noofPosts(self):
        count = 0
        for topic in self.get_topics():
            #total posts for this topic = total replies + 1 (1 is for the topic as we are considering it as topic)
            count += topic.reply_set.count() + 1
        return count
    
    def lastPostDatetime(self):
        ''' we are assuming post can be topic / reply
         we are finding out the last post / (if exists) last reply datetime '''                
        return self.lastPost().created_on
        
    def lastPostedUser(self):
        '''  we are assuming post can be topic / reply
             we are finding out the last post / (if exists) last reply datetime '''
        return self.lastPost().posted_by
        
    def lastPost(self):
        if(self.ftopics_set.count() == 0):
            return self   
        obj = self.ftopics_set.order_by('-created_on')[0]        
        if (obj.reply_set.count() > 0 ):
            return obj.reply_set.order_by("-created_on")[0]
        else :
            return obj  
    
    def get_topics(self):
        return Ftopics.objects.filter(category=self)

    def __unicode__(self):
        return self.name 
    

class TopicManager(models.Manager):
    use_for_related_fields = True

    def get_query_set(self):
        return super(TopicManager, self).get_query_set().filter(is_hidden = False)
    
    def get_new_since(self, when):
        "Topics with new replies after @when"
        now = datetime.datetime.now()
        return self.filter(last_reply_on__gt = now)
    

class Ftopics(models.Model):
    category = models.ForeignKey(Category)
    posted_by = models.ForeignKey(User)
    subject = models.CharField(max_length=999)
    slug = models.SlugField(max_length = 200, db_index = True) 
    message = MarkupField(default_markup_type=getattr(settings,
                                                      'DEFAULT_MARKUP_TYPE',
                                                      'markdown'),
                          markup_choices=settings.MARKUP_RENDERERS,
                          escape_html=True,
                          )
    file = models.FileField(upload_to='dinette/files',default='',null=True,blank=True)
    attachment_type = models.CharField(max_length=20,default='nofile')
    filename = models.CharField(max_length=100,default="dummyname.txt")
    viewcount = models.IntegerField(default=0)
    replies = models.IntegerField(default=0)    
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    last_reply_on = models.DateTimeField(auto_now_add=True)
    num_replies = models.PositiveSmallIntegerField(default = 0)
    
    #Moderation features
    announcement_flag = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)
    is_sticky = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    
    # use TopicManager as default, prevent leaking of hidden topics
    default = models.Manager()
    objects = TopicManager()

    # for topic subscriptions
    subscribers = models.ManyToManyField(User, related_name='subscribers')
    
    class Meta:
        ordering = ('-is_sticky', '-last_reply_on',)
        get_latest_by = ('created_on')
        verbose_name = "Topic"
        verbose_name_plural = "Topics"
        
    def save(self, *args, **kwargs):
        if not self.slug:
            slug = slugify(self.subject)
            slug = slug[:198]
            same_slug_count = Ftopics.objects.filter(slug__startswith = slug).count()
            if same_slug_count:
                slug = slug + str(same_slug_count)
            self.slug = slug
        super(Ftopics, self).save(*args, **kwargs)
        
    def __unicode__(self):
        return self.subject
    
    def get_absolute_url(self):
        return reverse('dinette_topic_detail', kwargs={'categoryslug':self.category.slug, 'topic_slug': self.slug})
    
    def htmlfrombbcode(self):
        if(len(self.message.raw.strip()) >  0):            
            return render_bbcode(self.message.raw)
        else :
            return ""
        
    def search_snippet(self):
        msg = "%s %s"% (self.subject, self.message.rendered)
        return truncatewords(msg, 50) 
        
    def getTopicString(self):
        #which is helpful for doing reverse lookup of an feed url for a topic         
        return "topic/%s" % self.slug
        
    def lastPostDatetime(self):
        return self.lastPost().created_on
        
    def lastPostedUser(self):
        return self.lastPost().posted_by.username
    
    def lastPost(self):
        if (self.reply_set.count() == 0):
            return self       
        return self.reply_set.order_by('-created_on')[0]        
        
    def classname(self):
        return  self.__class__.__name__
         

class ReplyManager(models.Manager):
    use_for_related_fields = True

    def get_query_set(self):
        return super(ReplyManager, self).get_query_set().filter(topic__is_hidden=False)

# Create Replies for a topic
class Reply(models.Model):
    topic = models.ForeignKey(Ftopics)
    posted_by = models.ForeignKey(User)

    message = MarkupField(default_markup_type=getattr(settings,
                                                      'DEFAULT_MARKUP_TYPE',
                                                      'markdown'),
                          markup_choices=settings.MARKUP_RENDERERS,
                          escape_html=True,
                          )
    file = models.FileField(upload_to='dinette/files',default='',null=True,blank=True)
    attachment_type = models.CharField(max_length=20,default='nofile')
    filename = models.CharField(max_length=100,default="dummyname.txt")
    
    reply_number = models.SmallIntegerField()
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    
    # replies for hidden topics should be hidden as well
    default = models.Manager()
    objects = ReplyManager()

    class Meta:
        verbose_name = "Reply"
        verbose_name_plural = "Replies"
        ordering = ('created_on',)
        get_latest_by = ('created_on', )
        
    def save(self, *args, **kwargs):
        if not self.pk:
            self.reply_number = self.topic.reply_set.all().count() + 1
        super(Reply, self).save(*args, **kwargs)
    
    def __unicode__(self):
        return truncatewords(self.message, 10)
    
    def search_snippet(self):
        msg = "%s %s"%(self.message.rendered, self.topic.subject)
        return truncatewords(msg, 100)
    
    
    @models.permalink
    def get_absolute_url(self):
        return ('dinette_topic_detail',(),{'categoryslug':self.topic.category.slug,'topic_slug': self.topic.slug})
    
    def get_url_with_fragment(self):
        page = (self.reply_number-1)/settings.REPLY_PAGE_SIZE + 1
        url =  self.get_absolute_url()
        if not page == 1:
            return "%s?page=%s#%s" % (url, page, self.reply_number)
        else:
            return "%s#%s" % (url, self.reply_number)
            
    
    def htmlfrombbcode(self):
        soup = BeautifulSoup(self.message.raw)
        #remove all html tags from the message
        onlytext = ''.join(soup.findAll(text=True))
        
        #get the bbcode for the text
        if(len(onlytext.strip()) >  0):            
            return render_bbcode(onlytext)
        else :
            return ""
    
    def classname(self):
        return  self.__class__.__name__
        
        
class DinetteUserProfile(models.Model):
    user = models.ForeignKey(User, unique = True)
    last_activity = models.DateTimeField(auto_now_add=True)
    #When was the last session. Used in page activity since last session.
    last_session_activity = models.DateTimeField(auto_now_add=True)
    userrank = models.CharField(max_length=30, default="Junior Member")
    last_posttime = models.DateTimeField(auto_now_add=True)
    photo = models.ImageField(upload_to='dinette/files', null=True, blank=True)
    signature = models.CharField(max_length = 1000, null = True, blank = True)
    slug = models.SlugField(max_length=200, db_index=True, unique=True)
    is_subscribed_to_digest = models.BooleanField(default=False)
    
    def __unicode__(self):
        return self.user.username
    
    #Populate the user fields for easy access
    @property
    def username(self):
        return self.user.username
    
    @property
    def first_name(self):
        return self.user.first_name
    
    @property
    def last_name(self):
        return self.user.last_name
    
    def get_total_posts(self):
        print self.user.ftopics_set.count() + self.user.reply_set.count()
        return self.user.ftopics_set.count() + self.user.reply_set.count()
    
    def is_online(self):
        from django.conf import settings
        last_online_duration = getattr(settings, 'LAST_ONLINE_DURATION', 900)
        now = datetime.datetime.now()
        if (now - self.last_activity).seconds < last_online_duration:
            return True
        return False   

    def getMD5(self):
        m = hashlib.md5()
        m.update(self.user.email)        
        return m.hexdigest()
    
    def get_since_last_visit(self):
        "Topics with new relies since last visit"
        return Ftopics.objects.get_new_since(self.last_session_activity)
     
    @models.permalink
    def get_absolute_url(self):
        return ('dinette_user_profile', [self.slug])
    
    def save(self, *args, **kwargs):
        if not self.slug:
            slug = slugify(self.user.username)
            if slug:
                same_slug_count = self._default_manager.filter(slug__startswith=slug).count()
                if same_slug_count:
                    slug = slug + str(same_slug_count)
                self.slug = slug
            else:
                #fallback to user id
                slug = self.user.id
        super(DinetteUserProfile, self).save(*args, **kwargs)
    
class NavLink(models.Model):
    title = models.CharField(max_length = 100)
    url = models.URLField()
    
    class Meta:
        verbose_name = "Navigation Link"
        verbose_name_plural = "Navigation Links"
        
    def __unicode__(self):
        return self.title
    
       
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        DinetteUserProfile.objects.create(user=instance)
        
def update_topic_on_reply(sender, instance, created, **kwargs):
    if created:
        instance.topic.last_reply_on = instance.created_on
        instance.topic.num_replies += 1
        instance.topic.save()

def notify_subscribers_on_reply(sender, instance, created, **kwargs):
    if created:
        site = Site.objects.get_current()
        subject = "%s replied on %s" %(instance.posted_by, instance.topic.subject)
        body = instance.message.rendered
        from_email = getattr(settings, 'DINETTE_FROM_EMAIL', '%s notifications <admin@%s>' %(site.name, site.domain))
        # exclude the user who posted this, even if he is subscribed
        for subscriber in instance.topic.subscribers.exclude(username=instance.posted_by.username):
            subscriber.email_user(subject, body, from_email)

post_save.connect(create_user_profile, sender=User)
post_save.connect(update_topic_on_reply, sender=Reply)
post_save.connect(notify_subscribers_on_reply, sender=Reply)

########NEW FILE########
__FILENAME__ = search
import haystack
haystack.autodiscover()
########NEW FILE########
__FILENAME__ = search_indexes
from haystack import indexes
from haystack import site

from dinette.models import Ftopics, Reply, DinetteUserProfile

class TopicIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    subject = indexes.CharField(model_attr="subject")
    message = indexes.CharField(model_attr="_message_rendered")
    
class ReplyIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    message = indexes.CharField(model_attr="_message_rendered")
    
class UserprofileIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    username = indexes.CharField(model_attr="username")
    first_name = indexes.CharField(model_attr="first_name")
    last_name = indexes.CharField(model_attr="last_name")
    
site.register(Ftopics, TopicIndex)
site.register(Reply, ReplyIndex)
site.register(DinetteUserProfile, UserprofileIndex)

########NEW FILE########
__FILENAME__ = dinette_tags
from django import  template
from django.contrib.sites.models import Site
from django.conf import settings

from dinette.models import Ftopics, SiteConfig, NavLink

register = template.Library()

class BaseDinetteNode(template.Node):
    @classmethod
    def handle_token(cls, parser, token):
        tokens = token.contents.split()
        if len(tokens) == 3:
            if tokens[1] != "as":
                 raise template.TemplateSyntaxError("Second argument in %r must be 'as'" % tokens[0])
            return cls(
                        as_varname=tokens[2]
                        )
        else:
            return cls()

class GetAnnouncementNode(BaseDinetteNode):
    def __init__(self, as_varname='announcement'):
        self.as_varname = as_varname

    def render(self, context):
        try:
            ancount = Ftopics.objects.filter(announcement_flag=True).count()
            if(ancount > 0):
                announcement = Ftopics.objects.filter(announcement_flag=True).latest()
                context[self.as_varname] = announcement
                return ''
        except Ftopics.DoesNotExist:
            return ''

@register.tag
def get_announcement(parser, token):
    return GetAnnouncementNode.handle_token(parser, token)

class GetNavLinksNode(BaseDinetteNode):
    def __init__(self, as_varname='nav_links'):
        self.as_varname = as_varname

    def render(self, context):
        context[self.as_varname] = NavLink.objects.all()
        return ''

@register.tag
def get_forumwide_links(parser, token):
    return GetNavLinksNode.handle_token(parser, token)

@register.simple_tag
def get_site_name():
    try:
        config = SiteConfig.objects.get(id=1)
        return config.name
    except SiteConfig.DoesNotExist:
        return ''

@register.simple_tag
def get_site_tag_line():
    try:
        config = SiteConfig.objects.get(id=1)
        return config.tag_line
    except SiteConfig.DoesNotExist:
        return ''
    
@register.simple_tag
def get_main_site_name():
    try:
        name = Site.objects.get_current().name
        return name
    except:
        return ''

@register.simple_tag
def get_main_site_domain():
    try:
        domain = Site.objects.get_current().domain
        return domain
    except:
        return ''

@register.simple_tag
def get_login_url():
    return settings.LOGIN_URL

@register.simple_tag
def get_logout_url():
    return settings.LOGOUT_URL

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from dinette.views import LatestTopicsByCategory,LatestRepliesOfTopic


urlpatterns = patterns('dinette.views',
    url(r'^$','index_page',name='dinette_category'),
    url(r'^new/$','new_topics',name='dinette_new_for_user'),
    url(r'^active/$','active',name='dinette_active'),
    url(r'^unanswered/$','unanswered',name='dinette_unanswered'),

    url(r'^search/$','search',name='dinette_search'),

    # user profile page
    url(r'^users/(?P<slug>[\w-]+)$', 'user_profile', name='dinette_user_profile'),

    # subscribe to digest
    url(r'^digest/subscribe/$', 'subscribeDigest', name='dinette_subscribe_to_digest'),
    url(r'^digest/unsubscribe/$', 'unsubscribeDigest', name='dinette_unsubscribe_from_digest'),

    url(r'^(?P<categoryslug>[\w-]+)/$','category_details', name='dinette_index'),
    url(r'^(?P<categoryslug>[\w-]+)/page(?P<pageno>\d+)/$','category_details', name='dinette_index2'),
    url(r'^post/topic/$','postTopic', name='dinette_posttopic'),
    url(r'^post/reply/$','postReply', name='dinette_postreply'),
    url(r'^(?P<categoryslug>[\w-]+)/(?P<topic_slug>[\w-]+)/$','topic_detail', name='dinette_topic_detail'),
    url(r'^(?P<categoryslug>[\w-]+)/(?P<topic_slug>[\w-]+)/page(?P<pageno>\d+)/$','topic_detail', name='dinette_reply_detail_paged'),

    #moderation views - Hence dont bother with SEF urls
    url(r'^moderate/topic/(?P<topic_id>\d+)/close/$','moderate_topic', {'action':'close'}, name='dinette_moderate_close'),
    url(r'^moderate/topic/(?P<topic_id>\d+)/stickyfy/$','moderate_topic', {'action':'sticky'}, name='dinette_moderate_sticky'),
    url(r'^moderate/topic/(?P<topic_id>\d+)/annoucement/$','moderate_topic', {'action':'announce'}, name='dinette_moderate_announce'),
    url(r'^moderate/topic/(?P<topic_id>\d+)/hide/$','moderate_topic', {'action':'hide'}, name='dinette_moderate_hide'),

    # post actions, permitted to OP and mods
    url(r'^delete/reply/(?P<reply_id>\d+)$','deleteReply', name='dinette_deletereply'),
    url(r'^edit/reply/(?P<reply_id>\d+)$','editReply', name='dinette_editreply'),

    # subscribe to topic
    url(r'^subscribe/topic/(?P<topic_id>\d+)', 'subscribeTopic', name='dinette_subscribe_to_topic'),
    url(r'^unsubscribe/topic/(?P<topic_id>\d+)', 'unsubscribeTopic', name='dinette_unsubscribe_from_topic'),
)


urlpatterns += patterns('',
    url(r'^feeds/category/(?P<whichcategory>[\w/-]+)/$', LatestTopicsByCategory(), name='dinette_feed_url'),
    url(r'^feeds/topic/(?P<whichtopic>[\w/-]+)/$', LatestRepliesOfTopic() ,name='dinette_topic_url'),
)

########NEW FILE########
__FILENAME__ = views
from django.http import (
    HttpResponse, Http404, HttpResponseForbidden,
    HttpResponseRedirect)
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.template.loader import render_to_string
from django.contrib.syndication.views import Feed
from django.contrib.auth.models import User, Group
from django.conf import settings
from django.contrib.auth.views import (
    login as auth_login, logout as auth_logout)
from django.views.generic.list import ListView

from datetime import datetime, timedelta
import logging

try:
    import simplejson
except ImportError:
    from django.utils import simplejson

from dinette.models import Ftopics, Category, Reply, DinetteUserProfile
from dinette.forms import FtopicForm, ReplyForm


#Create module logger
#several logging configurations are configured in the models
mlogger = logging.getLogger(__name__)

json_mimetype = 'application/javascript'


def index_page(request):
    #groups which this user has access
    if request.user.is_authenticated():
        groups = [group for group in request.user.groups.all()] + \
            [group for group in Group.objects.filter(name="general")]
    else:
        #we are treating user who have not loggedin belongs to general group
        groups = Group.objects.filter(name="general")
    #logic which decide which forum does this user have access to
    forums = []
    for group in groups:
        forums.extend([each for each in group.can_access_forums.all()])
    forums = set(forums)
    forums = sorted(forums, cmp=lambda x, y: int(y.ordering) - int(x.ordering))
    totaltopics = Ftopics.objects.count()
    totalposts = totaltopics + Reply.objects.count()
    totalusers = User.objects.count()
    now = datetime.now()
    users_online = DinetteUserProfile.objects.filter(
        last_activity__gte=now - timedelta(seconds=900)).count()
    last_registered_user = User.objects.order_by('-date_joined')[0]
    payload = {
        'users_online': users_online, 'forums_list': forums,
        'totaltopics': totaltopics, 'totalposts': totalposts,
        'totalusers': totalusers, 'last_registered_user': last_registered_user
    }
    return render_to_response(
        "dinette/mainindex.html", payload, RequestContext(request))


def category_details(request, categoryslug,  pageno=1):
    #build a form for posting topics
    topicform = FtopicForm()
    category = get_object_or_404(Category, slug=categoryslug)
    queryset = Ftopics.objects.filter(category__id__exact=category.id)
    topic_page_size = getattr(settings, "TOPIC_PAGE_SIZE", 10)
    payload = {
        'topicform': topicform, 'category': category,
        'authenticated': request.user.is_authenticated(),
        'topic_list': queryset, "topic_page_size": topic_page_size
    }
    return render_to_response(
        "dinette/category_details.html", payload, RequestContext(request))


topic_list = ListView.as_view(
    template_name='dinette/topiclist.html',
    model=Ftopics, context_object_name='topic', paginate_by=2)


def topic_detail(request, categoryslug, topic_slug, pageno=1):
    topic = get_object_or_404(Ftopics, slug=topic_slug)
    show_moderation_items = False
    if request.user in topic.category.moderated_by.all():
        show_moderation_items = True
    #some body has viewed this topic
    topic.viewcount = topic.viewcount + 1
    topic.save()
    #we also need to display the reply form
    replylist = topic.reply_set.all()
    reply_page_size = getattr(settings, "REPLY_PAGE_SIZE", 10)
    replyform = ReplyForm()
    payload = {
        'topic': topic, 'replyform': replyform, 'reply_list': replylist,
        'show_moderation_items': show_moderation_items,
        "reply_page_size": reply_page_size}
    return render_to_response(
        "dinette/topic_detail.html", payload, RequestContext(request))


@login_required
def postTopic(request):
    mlogger.info("In post Topic page.....................")
    mlogger.debug("Type of request.user %s" % type(request.user))

    topic = FtopicForm(request.POST, request.FILES)

    if not topic.is_valid():
        d = {"is_valid": "false", "response_html": topic.as_table()}
        json = simplejson.dumps(d)
        if request.FILES:
            json = "<textarea>"+simplejson.dumps(d)+"</textarea>"
        else:
            json = simplejson.dumps(d)
        return HttpResponse(json, mimetype=json_mimetype)

    #code which checks for flood control
    if (datetime.now()-request.user.get_profile().last_posttime).seconds < settings.FLOOD_TIME:
    #oh....... user trying to flood us Stop him
        d2 = {"is_valid": "flood", "errormessage": "Flood control.................."}
        if request.FILES:
            json = "<textarea>"+simplejson.dumps(d2)+"</textarea>"
        else :
            json = simplejson.dumps(d2)
        return HttpResponse(json, mimetype = json_mimetype)

    ftopic = topic.save(commit=False)
    #only if there is any file
    if request.FILES :
        if(request.FILES['file'].content_type.find("image") >= 0 ) :
            ftopic.attachment_type = "image"
        else :
            ftopic.attachment_type = "text"
        ftopic.filename = request.FILES['file'].name

    ftopic.posted_by = request.user

    mlogger.debug("categoryid= %s" %request.POST['categoryid'])
    ftopic.category  = Category.objects.get(pk = request.POST['categoryid'])

    #Assigning user rank
    mlogger.debug("Assigning an user rank and last posted datetime")
    assignUserElements(request.user)
    ftopic.save()
    #autosubsribe
    ftopic.subscribers.add(request.user)

    mlogger.debug("what is the message (%s %s) " % (ftopic.message,ftopic.subject))
    payload = {'topic':ftopic}
    response_html = render_to_string('dinette/topic_detail_frag.html', payload,RequestContext(request))
    mlogger.debug("what is the response = %s " % response_html)

    d2 = {"is_valid":"true","response_html":response_html}

    #this the required for ajax file uploads
    if request.FILES :
        json = "<textarea>"+simplejson.dumps(d2)+"</textarea>"
    else :
        json = simplejson.dumps(d2)
    return HttpResponse(json, mimetype = json_mimetype)

@login_required
def postReply(request):
    mlogger.info("in post reply.................")
    freply = ReplyForm(request.POST,request.FILES)

    if not freply.is_valid():
        d = {"is_valid":"false","response_html":freply.as_table()}
        json = simplejson.dumps(d)
        if request.FILES :
            json = "<textarea>"+simplejson.dumps(d)+"</textarea>"
        else:
            json = simplejson.dumps(d)
        return HttpResponse(json, mimetype = json_mimetype)



    #code which checks for flood control
    if (datetime.now() -(request.user.get_profile().last_posttime)).seconds <= settings.FLOOD_TIME:
    #oh....... user trying to flood us Stop him
        d2 = {"is_valid":"flood","errormessage":"You have posted message too recently. Please wait a while before trying again."}
        if request.FILES :
            json = "<textarea>"+simplejson.dumps(d2)+"</textarea>"
        else :
            json = simplejson.dumps(d2)
        return HttpResponse(json, mimetype = json_mimetype)


    reply = freply.save(commit=False)
     #only if there is any file
    if len(request.FILES.keys()) == 1 :
        if(request.FILES['file'].content_type.find("image") >= 0 ) :
            reply.attachment_type = "image"
        else :
            reply.attachment_type = "text"

        reply.filename = request.FILES['file'].name

    reply.posted_by = request.user
    mlogger.debug("toipcid= %s" %request.POST['topicid'])
    reply.topic = Ftopics.objects.get(pk = request.POST['topicid'])
    #Assigning user rank
    mlogger.debug("Assigning an user rank, and last posted datetime")
    assignUserElements(request.user)
    reply.save()
    payload = {'reply':reply}
    mlogger.debug("what is the replymesage = %s" %reply.message)
    response_html = render_to_string('dinette/replydetail_frag.html', payload ,RequestContext(request))
    mlogger.debug("what is the response = %s " % response_html)

    d2 = {"is_valid":"true","response_html":response_html}

    if request.FILES :
        #this the required for ajax file uploads
        json = "<textarea>"+simplejson.dumps(d2)+"</textarea>"
    else:
        json = simplejson.dumps(d2)

    return HttpResponse(json, mimetype = json_mimetype)

@login_required
def deleteReply(request, reply_id):
    resp= {"status": "1", "message": "Successfully deleted the reply"}
    try:
        reply = Reply.objects.get(pk=reply_id)
        if not (reply.posted_by == request.user or request.user in reply.topic.category.moderated_by.all()):
            return HttpResponseForbidden()
        reply.delete()
    except:
        resp["status"] = 0
        resp["message"] = "Error deleting message"
    json = simplejson.dumps(resp)
    return HttpResponse(json, mimetype = json_mimetype)

@login_required
def editReply(request, reply_id):
    reply = get_object_or_404(Reply, pk=reply_id)
    if not (reply.posted_by == request.user or request.user in reply.topic.category.moderated_by.all()):
        return HttpResponseForbidden()

    if request.POST:
        form = ReplyForm(request.POST, request.FILES, instance=reply)
        if form.is_valid():
            form.save()
            #redirect to prev page
            return HttpResponseRedirect(reply.get_url_with_fragment())
    else:
        # message should be original input, not the rendered one
        form = ReplyForm(instance=reply, initial={'message': reply.message.raw})

    return render_to_response('dinette/edit_reply.html', {'replyform': form, 'reply_id': reply_id}, context_instance=RequestContext(request))

class LatestTopicsByCategory(Feed):
    title_template = 'dinette/feeds/title.html'
    description_template = 'dinette/feeds/description.html'

    def get_object(self, request, whichcategory):
        mlogger.debug("Feed for category %s " % whichcategory)
        return get_object_or_404(Category, slug=whichcategory)

    def title(self, obj):
        return "Latest topics in category %s" % obj.name

    def link(self, obj):
        return  settings.SITE_URL

    def items(self, obj):
        return obj.ftopics_set.all()[:10]

    #construct these links by means of reverse lookup  by
    #using permalink decorator
    def item_link(self,obj):
        return  obj.get_absolute_url()

    def item_pubdate(self,obj):
        return obj.created_on


class LatestRepliesOfTopic(Feed):
    title_template = 'dinette/feeds/title.html'
    description_template = 'dinette/feeds/description.html'

    def get_object(self, request, whichtopic):
        mlogger.debug("Feed for category %s " % whichtopic)
        return get_object_or_404(Ftopics, slug=whichtopic)

    def title(self, obj):
        return "Latest replies in topic %s" % obj.subject

    def link(self, obj):
        return  settings.SITE_URL

    def items(self, obj):
        list = []
        list.insert(0,obj)
        for obj in obj.reply_set.all()[:10] :
            list.append(obj)
        return list

     #construct these links by means of reverse lookup  by
     #using permalink decorator
    def item_link(self,obj):
        return  obj.get_absolute_url()

    def item_pubdate(self,obj):
        return obj.created_on



def assignUserElements(user):
    ranks = getattr(settings, 'RANKS_NAMES_DATA')
    rank = ''
    if ranks:
        totalposts = user.ftopics_set.count() + user.reply_set.count()
        for el in ranks:
            if totalposts == el[0]:
                rank = el[1]
        if rank:
            userprofile = user.get_profile()
            userprofile.userrank = rank
            #this is the time when user posted his last post
            userprofile.last_posttime = datetime.now()
            userprofile.save()


###Moderation views###
@login_required
def moderate_topic(request, topic_id, action):
    topic = get_object_or_404(Ftopics, pk = topic_id)
    if not request.user in topic.category.moderated_by.all():
        raise Http404
    if request.method == 'POST':
        if action == 'close':
            if topic.is_closed:
                message = 'You have reopened topic %s'%topic.subject
            else:
                message = 'You have closed topic %s'%topic.subject
            topic.is_closed = not topic.is_closed
        elif action == 'announce':
            if topic.announcement_flag:
                message = '%s is no longer an announcement.' % topic.subject
            else:
                message = '%s is now an announcement.' % topic.subject
            topic.announcement_flag = not topic.announcement_flag
        elif action == 'sticky':
            if topic.is_sticky:
                message = '%s has been unstickied.' % topic.subject
            else:
                message = '%s has been stickied.' % topic.subject
            topic.is_sticky = not topic.is_sticky
        elif action == 'hide':
            if topic.is_hidden:
                message = '%s has been unhidden.' % topic.subject
            else:
                message = "%s has been hidden and won't show up any further." % topic.subject
            topic.is_hidden = not topic.is_hidden
        topic.save()
        payload = {'topic_id':topic.pk, 'message':message}
        resp = simplejson.dumps(payload)
        return HttpResponse(resp, mimetype = json_mimetype)
    else:
        return HttpResponse('This view must be called via post')

def login(request):
    return auth_login(request)

def logout(request):
    return auth_logout(request)

def user_profile(request, slug):
    user_profile = get_object_or_404(User, dinetteuserprofile__slug=slug)
    return render_to_response('dinette/user_profile.html', {}, RequestContext(request, {'user_profile': user_profile}))

@login_required
def new_topics(request):
    userprofile = request.user.get_profile()
    new_topic_list = userprofile.get_since_last_visit()
    return topic_list(request, new_topic_list, page_message = "Topics since your last visit")

def active(request):
    #Time filter = 48 hours
    days_ago_2 = datetime.now() - timedelta(days = 2)
    topics = Ftopics.objects.filter(last_reply_on__gt =  days_ago_2)
    active_topics = topics.extra(select= {"activity":"viewcount+100*num_replies"}).order_by("-activity")
    return topic_list(request, active_topics, page_message = "Most active Topics")

def unanswered(request):
    unanswered_topics = Ftopics.objects.filter(replies = 0)
    return topic_list(request, unanswered_topics, page_message = "Unanswered Topics")

def topic_list(request, queryset, page_message):
    payload = {"new_topic_list": queryset, "page_message": page_message}
    return render_to_response("dinette/new_topics.html", payload, RequestContext(request))

def search(request):
    from haystack.views import SearchView
    search_view = SearchView(template = "dinette/search.html")
    return search_view(request)

@login_required
def subscribeTopic(request, topic_id):
    topic = get_object_or_404(Ftopics, pk=topic_id)
    topic.subscribers.add(request.user)
    next = request.GET.get('next', topic.get_absolute_url())
    return redirect(next)

@login_required
def unsubscribeTopic(request, topic_id):
    topic = get_object_or_404(Ftopics, pk=topic_id)
    topic.subscribers.remove(request.user)
    next = request.GET.get('next', topic.get_absolute_url())
    return redirect(next)

@login_required
def subscribeDigest(request):
    user = get_object_or_404(User, pk=request.user.id)
    profile = user.get_profile()
    profile.is_subscribed_to_digest = True
    profile.save()
    next = request.GET.get('next', user.get_profile().get_absolute_url())
    return redirect(next)

@login_required
def unsubscribeDigest(request):
    user = get_object_or_404(User, pk=request.user.id)
    profile = user.get_profile()
    profile.is_subscribed_to_digest = False
    profile.save()
    next = request.GET.get('next', user.get_profile().get_absolute_url())
    return redirect(next)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^login/', 'django.contrib.auth.views.login', name='auth_login'),
    url(r'^logout/', 'django.contrib.auth.views.logout', name='auth_logout'),
)

########NEW FILE########
__FILENAME__ = views

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# Django settings for forum project.
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG
PROJECT_DIR = os.path.dirname(__file__)

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'dinette.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = 'dinette/media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/site_media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '9oezy17)u&_!3n%@qb^iqz%ur2%v(5=0uas@@#4)=n@5xy3m1j'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'dinette.middleware.UserActivity',
    'pagination.middleware.PaginationMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_DIR, 'templates')
)
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth', 
    'django.core.context_processors.debug', 
    'django.core.context_processors.i18n', 
    'django.core.context_processors.media', 
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request',
    'django.core.context_processors.static',
)



INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'dinette',

    'compressor',
    'google_analytics',
    'sorl.thumbnail',
    'pagination',

    'accounts',
)

STATIC_URL = '/static/'

from localsettings import *

########NEW FILE########
__FILENAME__ = settings_travis
# Django settings for forum project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'dinette.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = 'dinette/media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/site_media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '9oezy17)u&_!3n%@qb^iqz%ur2%v(5=0uas@@#4)=n@5xy3m1j'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'pagination.middleware.PaginationMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth', 
    'django.core.context_processors.debug', 
    'django.core.context_processors.i18n', 
    'django.core.context_processors.media', 
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request',
    'django.core.context_processors.static',
)



INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'dinette',

    'compressor',
    'google_analytics',
    'sorl.thumbnail',
    'pagination'
)


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'dev.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

from dinette.extra_settings import *

import os
from subprocess import call

from markupfield.markup import DEFAULT_MARKUP_TYPES
from dinette.libs.postmarkup import render_bbcode

COMPRESS = False
DEFAULT_MARKUP_TYPES.append(('bbcode', render_bbcode))
MARKUP_RENDERERS = DEFAULT_MARKUP_TYPES
DEFAULT_MARKUP_TYPE = "bbcode"

AUTH_PROFILE_MODULE = "dinette.DinetteUserProfile"
REPLY_PAGE_SIZE = 10
FLOOD_TIME = 0
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)
STATIC_URL = '/static/'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings
from django.conf.urls.static import static

from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    (r'^forum/', include('dinette.urls')),
    (r'^accounts/', include('accounts.urls')),

    (r'^admin/', include(admin.site.urls)),
)

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

########NEW FILE########
