__FILENAME__ = callbacks
"""A set of basic callbacks for bleach.linkify."""
from __future__ import unicode_literals


def nofollow(attrs, new=False):
    if attrs['href'].startswith('mailto:'):
        return attrs
    rel = [x for x in attrs.get('rel', '').split(' ') if x]
    if not 'nofollow' in [x.lower() for x in rel]:
        rel.append('nofollow')
    attrs['rel'] = ' '.join(rel)

    return attrs


def target_blank(attrs, new=False):
    if attrs['href'].startswith('mailto:'):
        return attrs
    attrs['target'] = '_blank'
    return attrs

########NEW FILE########
__FILENAME__ = encoding
import datetime
from decimal import Decimal
import types
import six


def is_protected_type(obj):
    """Determine if the object instance is of a protected type.

    Objects of protected types are preserved as-is when passed to
    force_unicode(strings_only=True).
    """
    return isinstance(obj, (
        six.integer_types +
        (types.NoneType,
         datetime.datetime, datetime.date, datetime.time,
         float, Decimal))
    )


def force_unicode(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Similar to smart_text, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    # Handle the common case first, saves 30-40% when s is an instance of
    # six.text_type. This function gets called often in that setting.
    if isinstance(s, six.text_type):
        return s
    if strings_only and is_protected_type(s):
        return s
    try:
        if not isinstance(s, six.string_types):
            if hasattr(s, '__unicode__'):
                s = s.__unicode__()
            else:
                if six.PY3:
                    if isinstance(s, bytes):
                        s = six.text_type(s, encoding, errors)
                    else:
                        s = six.text_type(s)
                else:
                    s = six.text_type(bytes(s), encoding, errors)
        else:
            # Note: We use .decode() here, instead of six.text_type(s,
            # encoding, errors), so that if s is a SafeBytes, it ends up being
            # a SafeText at the end.
            s = s.decode(encoding, errors)
    except UnicodeDecodeError as e:
        if not isinstance(s, Exception):
            raise UnicodeDecodeError(*e.args)
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
__FILENAME__ = sanitizer
from __future__ import unicode_literals
import re
from xml.sax.saxutils import escape, unescape

from html5lib.constants import tokenTypes
from html5lib.sanitizer import HTMLSanitizerMixin
from html5lib.tokenizer import HTMLTokenizer


PROTOS = HTMLSanitizerMixin.acceptable_protocols
PROTOS.remove('feed')


class BleachSanitizerMixin(HTMLSanitizerMixin):
    """Mixin to replace sanitize_token() and sanitize_css()."""

    allowed_svg_properties = []

    def sanitize_token(self, token):
        """Sanitize a token either by HTML-encoding or dropping.

        Unlike HTMLSanitizerMixin.sanitize_token, allowed_attributes can be
        a dict of {'tag': ['attribute', 'pairs'], 'tag': callable}.

        Here callable is a function with two arguments of attribute name
        and value. It should return true of false.

        Also gives the option to strip tags instead of encoding.

        """
        if (getattr(self, 'wildcard_attributes', None) is None and
                isinstance(self.allowed_attributes, dict)):
            self.wildcard_attributes = self.allowed_attributes.get('*', [])

        if token['type'] in (tokenTypes['StartTag'], tokenTypes['EndTag'],
                             tokenTypes['EmptyTag']):
            if token['name'] in self.allowed_elements:
                if 'data' in token:
                    if isinstance(self.allowed_attributes, dict):
                        allowed_attributes = self.allowed_attributes.get(
                            token['name'], [])
                        if not callable(allowed_attributes):
                            allowed_attributes += self.wildcard_attributes
                    else:
                        allowed_attributes = self.allowed_attributes
                    attrs = dict([(name, val) for name, val in
                                  token['data'][::-1]
                                  if (allowed_attributes(name, val)
                                      if callable(allowed_attributes)
                                      else name in allowed_attributes)])
                    for attr in self.attr_val_is_uri:
                        if not attr in attrs:
                            continue
                        val_unescaped = re.sub("[`\000-\040\177-\240\s]+", '',
                                               unescape(attrs[attr])).lower()
                        # Remove replacement characters from unescaped
                        # characters.
                        val_unescaped = val_unescaped.replace("\ufffd", "")
                        if (re.match(r'^[a-z0-9][-+.a-z0-9]*:', val_unescaped)
                            and (val_unescaped.split(':')[0] not in
                                 self.allowed_protocols)):
                            del attrs[attr]
                    for attr in self.svg_attr_val_allows_ref:
                        if attr in attrs:
                            attrs[attr] = re.sub(r'url\s*\(\s*[^#\s][^)]+?\)',
                                                 ' ',
                                                 unescape(attrs[attr]))
                    if (token['name'] in self.svg_allow_local_href and
                            'xlink:href' in attrs and
                            re.search(r'^\s*[^#\s].*', attrs['xlink:href'])):
                        del attrs['xlink:href']
                    if 'style' in attrs:
                        attrs['style'] = self.sanitize_css(attrs['style'])
                    token['data'] = [(name, val) for name, val in
                                     attrs.items()]
                return token
            elif self.strip_disallowed_elements:
                pass
            else:
                if token['type'] == tokenTypes['EndTag']:
                    token['data'] = '</{0!s}>'.format(token['name'])
                elif token['data']:
                    attr = ' {0!s}="{1!s}"'
                    attrs = ''.join([attr.format(k, escape(v)) for k, v in
                                    token['data']])
                    token['data'] = '<{0!s}{1!s}>'.format(token['name'], attrs)
                else:
                    token['data'] = '<{0!s}>'.format(token['name'])
                if token['selfClosing']:
                    token['data'] = token['data'][:-1] + '/>'
                token['type'] = tokenTypes['Characters']
                del token["name"]
                return token
        elif token['type'] == tokenTypes['Comment']:
            if not self.strip_html_comments:
                return token
        else:
            return token

    def sanitize_css(self, style):
        """HTMLSanitizerMixin.sanitize_css replacement.

        HTMLSanitizerMixin.sanitize_css always whitelists background-*,
        border-*, margin-*, and padding-*. We only whitelist what's in
        the whitelist.

        """
        # disallow urls
        style = re.compile('url\s*\(\s*[^\s)]+?\s*\)\s*').sub(' ', style)

        # gauntlet
        # TODO: Make sure this does what it's meant to - I *think* it wants to
        # validate style attribute contents.
        parts = style.split(';')
        gauntlet = re.compile("""^([-/:,#%.'"\sa-zA-Z0-9!]|\w-\w|'[\s\w]+'"""
                              """\s*|"[\s\w]+"|\([\d,%\.\s]+\))*$""")
        for part in parts:
            if not gauntlet.match(part):
                return ''

        if not re.match("^\s*([-\w]+\s*:[^:;]*(;\s*|$))*$", style):
            return ''

        clean = []
        for prop, value in re.findall('([-\w]+)\s*:\s*([^:;]*)', style):
            if not value:
                continue
            if prop.lower() in self.allowed_css_properties:
                clean.append(prop + ': ' + value + ';')
            elif prop.lower() in self.allowed_svg_properties:
                clean.append(prop + ': ' + value + ';')

        return ' '.join(clean)


class BleachSanitizer(HTMLTokenizer, BleachSanitizerMixin):
    def __init__(self, stream, encoding=None, parseMeta=True, useChardet=True,
                 lowercaseElementName=True, lowercaseAttrName=True, **kwargs):
        HTMLTokenizer.__init__(self, stream, encoding, parseMeta, useChardet,
                               lowercaseElementName, lowercaseAttrName,
                               **kwargs)

    def __iter__(self):
        for token in HTMLTokenizer.__iter__(self):
            token = self.sanitize_token(token)
            if token:
                yield token

########NEW FILE########
__FILENAME__ = test_basics
import six
import html5lib
from nose.tools import eq_

import bleach
from bleach.tests.tools import in_


def test_empty():
    eq_('', bleach.clean(''))


def test_nbsp():
    if six.PY3:
        expected = '\xa0test string\xa0'
    else:
        expected = six.u('\\xa0test string\\xa0')

    eq_(expected, bleach.clean('&nbsp;test string&nbsp;'))


def test_comments_only():
    comment = '<!-- this is a comment -->'
    open_comment = '<!-- this is an open comment'
    eq_('', bleach.clean(comment))
    eq_('', bleach.clean(open_comment))
    eq_(comment, bleach.clean(comment, strip_comments=False))
    eq_('{0!s}-->'.format(open_comment), bleach.clean(open_comment,
                                                      strip_comments=False))


def test_with_comments():
    html = '<!-- comment -->Just text'
    eq_('Just text', bleach.clean(html))
    eq_(html, bleach.clean(html, strip_comments=False))


def test_no_html():
    eq_('no html string', bleach.clean('no html string'))


def test_allowed_html():
    eq_('an <strong>allowed</strong> tag',
        bleach.clean('an <strong>allowed</strong> tag'))
    eq_('another <em>good</em> tag',
        bleach.clean('another <em>good</em> tag'))


def test_bad_html():
    eq_('a <em>fixed tag</em>',
        bleach.clean('a <em>fixed tag'))


def test_function_arguments():
    TAGS = ['span', 'br']
    ATTRS = {'span': ['style']}

    eq_('a <br><span style="">test</span>',
        bleach.clean('a <br/><span style="color:red">test</span>',
                     tags=TAGS, attributes=ATTRS))


def test_named_arguments():
    ATTRS = {'a': ['rel', 'href']}
    s = ('<a href="http://xx.com" rel="alternate">xx.com</a>',
         '<a rel="alternate" href="http://xx.com">xx.com</a>')

    eq_('<a href="http://xx.com">xx.com</a>', bleach.clean(s[0]))
    in_(s, bleach.clean(s[0], attributes=ATTRS))


def test_disallowed_html():
    eq_('a &lt;script&gt;safe()&lt;/script&gt; test',
        bleach.clean('a <script>safe()</script> test'))
    eq_('a &lt;style&gt;body{}&lt;/style&gt; test',
        bleach.clean('a <style>body{}</style> test'))


def test_bad_href():
    eq_('<em>no link</em>',
        bleach.clean('<em href="fail">no link</em>'))


def test_bare_entities():
    eq_('an &amp; entity', bleach.clean('an & entity'))
    eq_('an &lt; entity', bleach.clean('an < entity'))
    eq_('tag &lt; <em>and</em> entity',
        bleach.clean('tag < <em>and</em> entity'))
    eq_('&amp;', bleach.clean('&amp;'))


def test_escaped_entities():
    s = '&lt;em&gt;strong&lt;/em&gt;'
    eq_(s, bleach.clean(s))


def test_serializer():
    s = '<table></table>'
    eq_(s, bleach.clean(s, tags=['table']))
    eq_('test<table></table>', bleach.linkify('<table>test</table>'))
    eq_('<p>test</p>', bleach.clean('<p>test</p>', tags=['p']))


def test_no_href_links():
    s = '<a name="anchor">x</a>'
    eq_(s, bleach.linkify(s))


def test_weird_strings():
    s = '</3'
    eq_(bleach.clean(s), '')


def test_xml_render():
    parser = html5lib.HTMLParser()
    eq_(bleach._render(parser.parseFragment('')), '')


def test_stripping():
    eq_('a test <em>with</em> <b>html</b> tags',
        bleach.clean('a test <em>with</em> <b>html</b> tags', strip=True))
    eq_('a test <em>with</em>  <b>html</b> tags',
        bleach.clean('a test <em>with</em> <img src="http://example.com/"> '
                     '<b>html</b> tags', strip=True))

    s = '<p><a href="http://example.com/">link text</a></p>'
    eq_('<p>link text</p>', bleach.clean(s, tags=['p'], strip=True))
    s = '<p><span>multiply <span>nested <span>text</span></span></span></p>'
    eq_('<p>multiply nested text</p>', bleach.clean(s, tags=['p'], strip=True))

    s = ('<p><a href="http://example.com/"><img src="http://example.com/">'
         '</a></p>')
    eq_('<p><a href="http://example.com/"></a></p>',
        bleach.clean(s, tags=['p', 'a'], strip=True))


def test_allowed_styles():
    ATTR = ['style']
    STYLE = ['color']
    blank = '<b style=""></b>'
    s = '<b style="color: blue;"></b>'
    eq_(blank, bleach.clean('<b style="top:0"></b>', attributes=ATTR))
    eq_(s, bleach.clean(s, attributes=ATTR, styles=STYLE))
    eq_(s, bleach.clean('<b style="top: 0; color: blue;"></b>',
                        attributes=ATTR, styles=STYLE))


def test_idempotent():
    """Make sure that applying the filter twice doesn't change anything."""
    dirty = '<span>invalid & </span> < extra http://link.com<em>'

    clean = bleach.clean(dirty)
    eq_(clean, bleach.clean(clean))

    linked = bleach.linkify(dirty)
    eq_(linked, bleach.linkify(linked))


def test_rel_already_there():
    """Make sure rel attribute is updated not replaced"""
    linked = ('Click <a href="http://example.com" rel="tooltip">'
              'here</a>.')
    link_good = (('Click <a href="http://example.com" rel="tooltip nofollow">'
                  'here</a>.'),
                 ('Click <a rel="tooltip nofollow" href="http://example.com">'
                  'here</a>.'))

    in_(link_good, bleach.linkify(linked))
    in_(link_good, bleach.linkify(link_good[0]))


def test_lowercase_html():
    """We should output lowercase HTML."""
    dirty = '<EM CLASS="FOO">BAR</EM>'
    clean = '<em class="FOO">BAR</em>'
    eq_(clean, bleach.clean(dirty, attributes=['class']))


def test_wildcard_attributes():
    ATTR = {
        '*': ['id'],
        'img': ['src'],
    }
    TAG = ['img', 'em']
    dirty = ('both <em id="foo" style="color: black">can</em> have '
             '<img id="bar" src="foo"/>')
    clean = ('both <em id="foo">can</em> have <img src="foo" id="bar">',
             'both <em id="foo">can</em> have <img id="bar" src="foo">')
    in_(clean, bleach.clean(dirty, tags=TAG, attributes=ATTR))


def test_sarcasm():
    """Jokes should crash.<sarcasm/>"""
    dirty = 'Yeah right <sarcasm/>'
    clean = 'Yeah right &lt;sarcasm/&gt;'
    eq_(clean, bleach.clean(dirty))

########NEW FILE########
__FILENAME__ = test_css
from functools import partial

from nose.tools import eq_

from bleach import clean


clean = partial(clean, tags=['p'], attributes=['style'])


def test_allowed_css():
    tests = (
        ('font-family: Arial; color: red; float: left; '
         'background-color: red;', 'color: red;', ['color']),
        ('border: 1px solid blue; color: red; float: left;', 'color: red;',
         ['color']),
        ('border: 1px solid blue; color: red; float: left;',
         'color: red; float: left;', ['color', 'float']),
        ('color: red; float: left; padding: 1em;', 'color: red; float: left;',
         ['color', 'float']),
        ('color: red; float: left; padding: 1em;', 'color: red;', ['color']),
        ('cursor: -moz-grab;', 'cursor: -moz-grab;', ['cursor']),
        ('color: hsl(30,100%,50%);', 'color: hsl(30,100%,50%);', ['color']),
        ('color: rgba(255,0,0,0.4);', 'color: rgba(255,0,0,0.4);', ['color']),
        ("text-overflow: ',' ellipsis;", "text-overflow: ',' ellipsis;",
         ['text-overflow']),
        ('text-overflow: "," ellipsis;', 'text-overflow: "," ellipsis;',
         ['text-overflow']),
        ('font-family: "Arial";', 'font-family: "Arial";', ['font-family']),
    )

    p_single = '<p style="{0!s}">bar</p>'
    p_double = "<p style='{0!s}'>bar</p>"

    def check(i, o, s):
        if '"' in i:
            eq_(p_double.format(o), clean(p_double.format(i), styles=s))
        else:
            eq_(p_single.format(o), clean(p_single.format(i), styles=s))

    for i, o, s in tests:
        yield check, i, o, s


def test_valid_css():
    """The sanitizer should fix missing CSS values."""
    styles = ['color', 'float']
    eq_('<p style="float: left;">foo</p>',
        clean('<p style="float: left; color: ">foo</p>', styles=styles))
    eq_('<p style="">foo</p>',
        clean('<p style="color: float: left;">foo</p>', styles=styles))


def test_style_hang():
    """The sanitizer should not hang on any inline styles"""
    # TODO: Neaten this up. It's copypasta from MDN/Kuma to repro the bug
    style = ("""margin-top: 0px; margin-right: 0px; margin-bottom: 1.286em; """
             """margin-left: 0px; padding-top: 15px; padding-right: 15px; """
             """padding-bottom: 15px; padding-left: 15px; border-top-width: """
             """1px; border-right-width: 1px; border-bottom-width: 1px; """
             """border-left-width: 1px; border-top-style: dotted; """
             """border-right-style: dotted; border-bottom-style: dotted; """
             """border-left-style: dotted; border-top-color: rgb(203, 200, """
             """185); border-right-color: rgb(203, 200, 185); """
             """border-bottom-color: rgb(203, 200, 185); border-left-color: """
             """rgb(203, 200, 185); background-image: initial; """
             """background-attachment: initial; background-origin: initial; """
             """background-clip: initial; background-color: """
             """rgb(246, 246, 242); overflow-x: auto; overflow-y: auto; """
             """font: normal normal normal 100%/normal 'Courier New', """
             """'Andale Mono', monospace; background-position: initial """
             """initial; background-repeat: initial initial;""")
    html = '<p style="{0!s}">Hello world</p>'.format(style)
    styles = [
        'border', 'float', 'overflow', 'min-height', 'vertical-align',
        'white-space',
        'margin', 'margin-left', 'margin-top', 'margin-bottom', 'margin-right',
        'padding', 'padding-left', 'padding-top', 'padding-bottom',
        'padding-right',
        'background',
        'background-color',
        'font', 'font-size', 'font-weight', 'text-align', 'text-transform',
    ]

    expected = ("""<p style="margin-top: 0px; margin-right: 0px; """
                """margin-bottom: 1.286em; margin-left: 0px; padding-top: """
                """15px; padding-right: 15px; padding-bottom: 15px; """
                """padding-left: 15px; background-color: """
                """rgb(246, 246, 242); font: normal normal normal """
                """100%/normal 'Courier New', 'Andale Mono', monospace;">"""
                """Hello world</p>""")

    result = clean(html, styles=styles)
    eq_(expected, result)

########NEW FILE########
__FILENAME__ = test_links
try:
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus

from html5lib.tokenizer import HTMLTokenizer
from nose.tools import eq_

from bleach import linkify, url_re, DEFAULT_CALLBACKS as DC
from bleach.tests.tools import in_


def test_url_re():
    def no_match(s):
        match = url_re.search(s)
        if match:
            assert not match, 'matched {0!s}'.format(s[slice(*match.span())])
    yield no_match, 'just what i am looking for...it'


def test_empty():
    eq_('', linkify(''))


def test_simple_link():
    in_(('a <a href="http://example.com" rel="nofollow">http://example.com'
        '</a> link',
        'a <a rel="nofollow" href="http://example.com">http://example.com'
        '</a> link'),
        linkify('a http://example.com link'))
    in_(('a <a href="https://example.com" rel="nofollow">https://example.com'
        '</a> link',
        'a <a rel="nofollow" href="https://example.com">https://example.com'
        '</a> link'),
        linkify('a https://example.com link'))
    in_(('a <a href="http://example.com" rel="nofollow">example.com</a> link',
         'a <a rel="nofollow" href="http://example.com">example.com</a> link'),
        linkify('a example.com link'))


def test_trailing_slash():
    in_(('<a href="http://examp.com/" rel="nofollow">http://examp.com/</a>',
         '<a rel="nofollow" href="http://examp.com/">http://examp.com/</a>'),
        linkify('http://examp.com/'))
    in_(('<a href="http://example.com/foo/" rel="nofollow">'
         'http://example.com/foo/</a>',
         '<a rel="nofollow" href="http://example.com/foo/">'
         'http://example.com/foo/</a>'),
        linkify('http://example.com/foo/'))
    in_(('<a href="http://example.com/foo/bar/" rel="nofollow">'
         'http://example.com/foo/bar/</a>',
         '<a rel="nofollow" href="http://example.com/foo/bar/">'
         'http://example.com/foo/bar/</a>'),
        linkify('http://example.com/foo/bar/'))


def test_mangle_link():
    """We can muck with the href attribute of the link."""
    def filter_url(attrs, new=False):
        quoted = quote_plus(attrs['href'])
        attrs['href'] = 'http://bouncer/?u={0!s}'.format(quoted)
        return attrs

    in_(('<a href="http://bouncer/?u=http%3A%2F%2Fexample.com" rel="nofollow">'
         'http://example.com</a>',
         '<a rel="nofollow" href="http://bouncer/?u=http%3A%2F%2Fexample.com">'
         'http://example.com</a>'),
        linkify('http://example.com', DC + [filter_url]))


def test_mangle_text():
    """We can muck with the inner text of a link."""

    def ft(attrs, new=False):
        attrs['_text'] = 'bar'
        return attrs

    eq_('<a href="http://ex.mp">bar</a> <a href="http://ex.mp/foo">bar</a>',
        linkify('http://ex.mp <a href="http://ex.mp/foo">foo</a>', [ft]))


def test_email_link():
    tests = (
        ('a james@example.com mailto', False, 'a james@example.com mailto'),
        ('a james@example.com.au mailto', False,
            'a james@example.com.au mailto'),
        ('a <a href="mailto:james@example.com">james@example.com</a> mailto',
            True, 'a james@example.com mailto'),
        ('aussie <a href="mailto:james@example.com.au">'
            'james@example.com.au</a> mailto', True,
            'aussie james@example.com.au mailto'),
        # This is kind of a pathological case. I guess we do our best here.
        (('email to <a href="james@example.com" rel="nofollow">'
          'james@example.com</a>',
          'email to <a rel="nofollow" href="james@example.com">'
          'james@example.com</a>'),
         True,
         'email to <a href="james@example.com">james@example.com</a>'),
    )

    def _check(o, p, i):
        if isinstance(o, (list, tuple)):
            in_(o, linkify(i, parse_email=p))
        else:
            eq_(o, linkify(i, parse_email=p))

    for (o, p, i) in tests:
        yield _check, o, p, i


def test_email_link_escaping():
    tests = (
        ('''<a href='mailto:"james"@example.com'>'''
            '''"james"@example.com</a>''',
            '"james"@example.com'),
        ('''<a href="mailto:&quot;j'ames&quot;@example.com">'''
            '''"j'ames"@example.com</a>''',
            '"j\'ames"@example.com'),
        ('''<a href='mailto:"ja>mes"@example.com'>'''
            '''"ja&gt;mes"@example.com</a>''',
            '"ja>mes"@example.com'),
    )

    def _check(o, i):
        eq_(o, linkify(i, parse_email=True))

    for (o, i) in tests:
        yield _check, o, i


def test_prevent_links():
    """Returning None from any callback should remove links or prevent them
    from being created."""

    def no_new_links(attrs, new=False):
        if new:
            return None
        return attrs

    def no_old_links(attrs, new=False):
        if not new:
            return None
        return attrs

    def noop(attrs, new=False):
        return attrs

    in_text = 'a ex.mp <a href="http://example.com">example</a>'
    out_text = 'a <a href="http://ex.mp">ex.mp</a> example'
    tests = (
        ([noop], ('a <a href="http://ex.mp">ex.mp</a> '
                  '<a href="http://example.com">example</a>'), 'noop'),
        ([no_new_links, noop], in_text, 'no new, noop'),
        ([noop, no_new_links], in_text, 'noop, no new'),
        ([no_old_links, noop], out_text, 'no old, noop'),
        ([noop, no_old_links], out_text, 'noop, no old'),
        ([no_old_links, no_new_links], 'a ex.mp example', 'no links'),
    )

    def _check(cb, o, msg):
        eq_(o, linkify(in_text, cb), msg)

    for (cb, o, msg) in tests:
        yield _check, cb, o, msg


def test_set_attrs():
    """We can set random attributes on links."""

    def set_attr(attrs, new=False):
        attrs['rev'] = 'canonical'
        return attrs

    in_(('<a href="http://ex.mp" rev="canonical">ex.mp</a>',
         '<a rev="canonical" href="http://ex.mp">ex.mp</a>'),
        linkify('ex.mp', [set_attr]))


def test_only_proto_links():
    """Only create links if there's a protocol."""
    def only_proto(attrs, new=False):
        if new and not attrs['_text'].startswith(('http:', 'https:')):
            return None
        return attrs

    in_text = 'a ex.mp http://ex.mp <a href="/foo">bar</a>'
    out_text = ('a ex.mp <a href="http://ex.mp">http://ex.mp</a> '
                '<a href="/foo">bar</a>')
    eq_(out_text, linkify(in_text, [only_proto]))


def test_stop_email():
    """Returning None should prevent a link from being created."""
    def no_email(attrs, new=False):
        if attrs['href'].startswith('mailto:'):
            return None
        return attrs
    text = 'do not link james@example.com'
    eq_(text, linkify(text, parse_email=True, callbacks=[no_email]))


def test_tlds():
    in_(('<a href="http://example.com" rel="nofollow">example.com</a>',
         '<a rel="nofollow" href="http://example.com">example.com</a>'),
        linkify('example.com'))
    in_(('<a href="http://example.co.uk" rel="nofollow">example.co.uk</a>',
         '<a rel="nofollow" href="http://example.co.uk">example.co.uk</a>'),
        linkify('example.co.uk'))
    in_(('<a href="http://example.edu" rel="nofollow">example.edu</a>',
         '<a rel="nofollow" href="http://example.edu">example.edu</a>'),
        linkify('example.edu'))
    eq_('example.xxx', linkify('example.xxx'))
    eq_(' brie', linkify(' brie'))
    in_(('<a href="http://bit.ly/fun" rel="nofollow">bit.ly/fun</a>',
         '<a rel="nofollow" href="http://bit.ly/fun">bit.ly/fun</a>'),
        linkify('bit.ly/fun'))


def test_escaping():
    eq_('&lt; unrelated', linkify('< unrelated'))


def test_nofollow_off():
    eq_('<a href="http://example.com">example.com</a>',
        linkify('example.com', []))


def test_link_in_html():
    in_(('<i><a href="http://yy.com" rel="nofollow">http://yy.com</a></i>',
         '<i><a rel="nofollow" href="http://yy.com">http://yy.com</a></i>'),
        linkify('<i>http://yy.com</i>'))

    in_(('<em><strong><a href="http://xx.com" rel="nofollow">http://xx.com'
         '</a></strong></em>',
         '<em><strong><a rel="nofollow" href="http://xx.com">http://xx.com'
         '</a></strong></em>'),
        linkify('<em><strong>http://xx.com</strong></em>'))


def test_links_https():
    in_(('<a href="https://yy.com" rel="nofollow">https://yy.com</a>',
         '<a rel="nofollow" href="https://yy.com">https://yy.com</a>'),
        linkify('https://yy.com'))


def test_add_rel_nofollow():
    """Verify that rel="nofollow" is added to an existing link"""
    in_(('<a href="http://yy.com" rel="nofollow">http://yy.com</a>',
         '<a rel="nofollow" href="http://yy.com">http://yy.com</a>'),
        linkify('<a href="http://yy.com">http://yy.com</a>'))


def test_url_with_path():
    in_(('<a href="http://example.com/path/to/file" rel="nofollow">'
         'http://example.com/path/to/file</a>',
         '<a rel="nofollow" href="http://example.com/path/to/file">'
         'http://example.com/path/to/file</a>'),
        linkify('http://example.com/path/to/file'))


def test_link_ftp():
    in_(('<a href="ftp://ftp.mozilla.org/some/file" rel="nofollow">'
         'ftp://ftp.mozilla.org/some/file</a>',
         '<a rel="nofollow" href="ftp://ftp.mozilla.org/some/file">'
         'ftp://ftp.mozilla.org/some/file</a>'),
        linkify('ftp://ftp.mozilla.org/some/file'))


def test_link_query():
    in_(('<a href="http://xx.com/?test=win" rel="nofollow">'
        'http://xx.com/?test=win</a>',
        '<a rel="nofollow" href="http://xx.com/?test=win">'
        'http://xx.com/?test=win</a>'),
        linkify('http://xx.com/?test=win'))
    in_(('<a href="http://xx.com/?test=win" rel="nofollow">'
        'xx.com/?test=win</a>',
        '<a rel="nofollow" href="http://xx.com/?test=win">'
        'xx.com/?test=win</a>'),
        linkify('xx.com/?test=win'))
    in_(('<a href="http://xx.com?test=win" rel="nofollow">'
        'xx.com?test=win</a>',
        '<a rel="nofollow" href="http://xx.com?test=win">'
        'xx.com?test=win</a>'),
        linkify('xx.com?test=win'))


def test_link_fragment():
    in_(('<a href="http://xx.com/path#frag" rel="nofollow">'
         'http://xx.com/path#frag</a>',
         '<a rel="nofollow" href="http://xx.com/path#frag">'
         'http://xx.com/path#frag</a>'),
        linkify('http://xx.com/path#frag'))


def test_link_entities():
    in_(('<a href="http://xx.com/?a=1&amp;b=2" rel="nofollow">'
        'http://xx.com/?a=1&amp;b=2</a>',
        '<a rel="nofollow" href="http://xx.com/?a=1&amp;b=2">'
        'http://xx.com/?a=1&amp;b=2</a>'),
        linkify('http://xx.com/?a=1&b=2'))


def test_escaped_html():
    """If I pass in escaped HTML, it should probably come out escaped."""
    s = '&lt;em&gt;strong&lt;/em&gt;'
    eq_(s, linkify(s))


def test_link_http_complete():
    in_(('<a href="https://user:pass@ftp.mozilla.org/x/y.exe?a=b&amp;c=d'
        '&amp;e#f" rel="nofollow">'
        'https://user:pass@ftp.mozilla.org/x/y.exe?a=b&amp;c=d&amp;e#f</a>',
        '<a rel="nofollow" href="https://user:pass@ftp.mozilla.org/x/'
        'y.exe?a=b&amp;c=d&amp;e#f">'
        'https://user:pass@ftp.mozilla.org/x/y.exe?a=b&amp;c=d&amp;e#f</a>'),
        linkify('https://user:pass@ftp.mozilla.org/x/y.exe?a=b&c=d&e#f'))


def test_non_url():
    """document.vulnerable should absolutely not be linkified."""
    s = 'document.vulnerable'
    eq_(s, linkify(s))


def test_javascript_url():
    """javascript: urls should never be linkified."""
    s = 'javascript:document.vulnerable'
    eq_(s, linkify(s))


def test_unsafe_url():
    """Any unsafe char ({}[]<>, etc.) in the path should end URL scanning."""
    in_(('All your{"<a href="http://xx.yy.com/grover.png" '
         'rel="nofollow">xx.yy.com/grover.png</a>"}base are',
         'All your{"<a rel="nofollow" href="http://xx.yy.com/grover.png"'
         '>xx.yy.com/grover.png</a>"}base are'),
        linkify('All your{"xx.yy.com/grover.png"}base are'))


def test_skip_pre():
    """Skip linkification in <pre> tags."""
    simple = 'http://xx.com <pre>http://xx.com</pre>'
    linked = ('<a href="http://xx.com" rel="nofollow">http://xx.com</a> '
              '<pre>http://xx.com</pre>',
              '<a rel="nofollow" href="http://xx.com">http://xx.com</a> '
              '<pre>http://xx.com</pre>')
    all_linked = ('<a href="http://xx.com" rel="nofollow">http://xx.com</a> '
                  '<pre><a href="http://xx.com" rel="nofollow">http://xx.com'
                  '</a></pre>',
                  '<a rel="nofollow" href="http://xx.com">http://xx.com</a> '
                  '<pre><a rel="nofollow" href="http://xx.com">http://xx.com'
                  '</a></pre>')
    in_(linked, linkify(simple, skip_pre=True))
    in_(all_linked, linkify(simple))

    already_linked = '<pre><a href="http://xx.com">xx</a></pre>'
    nofollowed = ('<pre><a href="http://xx.com" rel="nofollow">xx</a></pre>',
                  '<pre><a rel="nofollow" href="http://xx.com">xx</a></pre>')
    in_(nofollowed, linkify(already_linked))
    in_(nofollowed, linkify(already_linked, skip_pre=True))


def test_libgl():
    """libgl.so.1 should not be linkified."""
    eq_('libgl.so.1', linkify('libgl.so.1'))


def test_end_of_sentence():
    """example.com. should match."""
    outs = ('<a href="http://{0!s}" rel="nofollow">{0!s}</a>{1!s}',
            '<a rel="nofollow" href="http://{0!s}">{0!s}</a>{1!s}')
    intxt = '{0!s}{1!s}'

    def check(u, p):
        in_([out.format(u, p) for out in outs],
            linkify(intxt.format(u, p)))

    tests = (
        ('example.com', '.'),
        ('example.com', '...'),
        ('ex.com/foo', '.'),
        ('ex.com/foo', '....'),
    )

    for u, p in tests:
        yield check, u, p


def test_end_of_clause():
    """example.com/foo, shouldn't include the ,"""
    in_(('<a href="http://ex.com/foo" rel="nofollow">ex.com/foo</a>, bar',
         '<a rel="nofollow" href="http://ex.com/foo">ex.com/foo</a>, bar'),
        linkify('ex.com/foo, bar'))


def test_sarcasm():
    """Jokes should crash.<sarcasm/>"""
    dirty = 'Yeah right <sarcasm/>'
    clean = 'Yeah right &lt;sarcasm/&gt;'
    eq_(clean, linkify(dirty))


def test_wrapping_parentheses():
    """URLs wrapped in parantheses should not include them."""
    outs = ('{0!s}<a href="http://{1!s}" rel="nofollow">{2!s}</a>{3!s}',
            '{0!s}<a rel="nofollow" href="http://{1!s}">{2!s}</a>{3!s}')

    tests = (
        ('(example.com)', ('(', 'example.com', 'example.com', ')')),
        ('(example.com/)', ('(', 'example.com/', 'example.com/', ')')),
        ('(example.com/foo)', ('(', 'example.com/foo',
         'example.com/foo', ')')),
        ('(((example.com/))))', ('(((', 'example.com/)',
         'example.com/)', ')))')),
        ('example.com/))', ('', 'example.com/))', 'example.com/))', '')),
        ('http://en.wikipedia.org/wiki/Test_(assessment)',
         ('', 'en.wikipedia.org/wiki/Test_(assessment)',
          'http://en.wikipedia.org/wiki/Test_(assessment)', '')),
        ('(http://en.wikipedia.org/wiki/Test_(assessment))',
         ('(', 'en.wikipedia.org/wiki/Test_(assessment)',
          'http://en.wikipedia.org/wiki/Test_(assessment)', ')')),
        ('((http://en.wikipedia.org/wiki/Test_(assessment))',
         ('((', 'en.wikipedia.org/wiki/Test_(assessment',
          'http://en.wikipedia.org/wiki/Test_(assessment', '))')),
        ('(http://en.wikipedia.org/wiki/Test_(assessment)))',
         ('(', 'en.wikipedia.org/wiki/Test_(assessment))',
          'http://en.wikipedia.org/wiki/Test_(assessment))', ')')),
        ('(http://en.wikipedia.org/wiki/)Test_(assessment',
         ('(', 'en.wikipedia.org/wiki/)Test_(assessment',
          'http://en.wikipedia.org/wiki/)Test_(assessment', '')),
    )

    def check(test, expected_output):
        in_([o.format(*expected_output) for o in outs], linkify(test))

    for test, expected_output in tests:
        yield check, test, expected_output


def test_ports():
    """URLs can contain port numbers."""
    tests = (
        ('http://foo.com:8000', ('http://foo.com:8000', '')),
        ('http://foo.com:8000/', ('http://foo.com:8000/', '')),
        ('http://bar.com:xkcd', ('http://bar.com', ':xkcd')),
        ('http://foo.com:81/bar', ('http://foo.com:81/bar', '')),
        ('http://foo.com:', ('http://foo.com', ':')),
    )

    def check(test, output):
        outs = ('<a href="{0}" rel="nofollow">{0}</a>{1}',
                '<a rel="nofollow" href="{0}">{0}</a>{1}')
        in_([out.format(*output) for out in outs],
            linkify(test))

    for test, output in tests:
        yield check, test, output


def test_tokenizer():
    """Linkify doesn't always have to sanitize."""
    raw = '<em>test<x></x></em>'
    eq_('<em>test&lt;x&gt;&lt;/x&gt;</em>', linkify(raw))
    eq_(raw, linkify(raw, tokenizer=HTMLTokenizer))


def test_ignore_bad_protocols():
    eq_('foohttp://bar',
        linkify('foohttp://bar'))
    in_(('fohttp://<a href="http://exampl.com" rel="nofollow">exampl.com</a>',
         'fohttp://<a rel="nofollow" href="http://exampl.com">exampl.com</a>'),
        linkify('fohttp://exampl.com'))


def test_max_recursion_depth():
    """If we hit the max recursion depth, just return the string."""
    test = '<em>' * 2000 + 'foo' + '</em>' * 2000
    eq_(test, linkify(test))


def test_link_emails_and_urls():
    """parse_email=True shouldn't prevent URLs from getting linkified."""
    output = ('<a href="http://example.com" rel="nofollow">'
              'http://example.com</a> <a href="mailto:person@example.com">'
              'person@example.com</a>',
              '<a rel="nofollow" href="http://example.com">'
              'http://example.com</a> <a href="mailto:person@example.com">'
              'person@example.com</a>')
    in_(output, linkify('http://example.com person@example.com',
                        parse_email=True))


def test_links_case_insensitive():
    """Protocols and domain names are case insensitive."""
    expect = ('<a href="HTTP://EXAMPLE.COM" rel="nofollow">'
              'HTTP://EXAMPLE.COM</a>',
              '<a rel="nofollow" href="HTTP://EXAMPLE.COM">'
              'HTTP://EXAMPLE.COM</a>')
    in_(expect, linkify('HTTP://EXAMPLE.COM'))


def test_elements_inside_links():
    in_(('<a href="#" rel="nofollow">hello<br></a>',
         '<a rel="nofollow" href="#">hello<br></a>'),
        linkify('<a href="#">hello<br></a>'))

    in_(('<a href="#" rel="nofollow"><strong>bold</strong> hello<br></a>',
         '<a rel="nofollow" href="#"><strong>bold</strong> hello<br></a>'),
        linkify('<a href="#"><strong>bold</strong> hello<br></a>'))

########NEW FILE########
__FILENAME__ = test_security
"""More advanced security tests"""

from nose.tools import eq_

from bleach import clean


def test_nested_script_tag():
    eq_('&lt;&lt;script&gt;script&gt;evil()&lt;&lt;/script&gt;/script&gt;',
        clean('<<script>script>evil()<</script>/script>'))
    eq_('&lt;&lt;x&gt;script&gt;evil()&lt;&lt;/x&gt;/script&gt;',
        clean('<<x>script>evil()<</x>/script>'))


def test_nested_script_tag_r():
    eq_('&lt;script&lt;script&gt;&gt;evil()&lt;/script&lt;&gt;&gt;',
        clean('<script<script>>evil()</script</script>>'))


def test_invalid_attr():
    IMG = ['img', ]
    IMG_ATTR = ['src']

    eq_('<a href="test">test</a>',
        clean('<a onclick="evil" href="test">test</a>'))
    eq_('<img src="test">',
        clean('<img onclick="evil" src="test" />',
              tags=IMG, attributes=IMG_ATTR))
    eq_('<img src="test">',
        clean('<img href="invalid" src="test" />',
              tags=IMG, attributes=IMG_ATTR))


def test_unquoted_attr():
    eq_('<abbr title="mytitle">myabbr</abbr>',
        clean('<abbr title=mytitle>myabbr</abbr>'))


def test_unquoted_event_handler():
    eq_('<a href="http://xx.com">xx.com</a>',
        clean('<a href="http://xx.com" onclick=foo()>xx.com</a>'))


def test_invalid_attr_value():
    eq_('&lt;img src="javascript:alert(\'XSS\');"&gt;',
        clean('<img src="javascript:alert(\'XSS\');">'))


def test_invalid_href_attr():
    eq_('<a>xss</a>',
        clean('<a href="javascript:alert(\'XSS\')">xss</a>'))


def test_invalid_filter_attr():
    IMG = ['img', ]
    IMG_ATTR = {'img': lambda n, v: n == 'src' and v == "http://example.com/"}

    eq_('<img src="http://example.com/">',
        clean('<img onclick="evil" src="http://example.com/" />',
              tags=IMG, attributes=IMG_ATTR))

    eq_('<img>', clean('<img onclick="evil" src="http://badhost.com/" />',
                       tags=IMG, attributes=IMG_ATTR))


def test_invalid_tag_char():
    eq_('&lt;script xss="" src="http://xx.com/xss.js"&gt;&lt;/script&gt;',
        clean('<script/xss src="http://xx.com/xss.js"></script>'))
    eq_('&lt;script src="http://xx.com/xss.js"&gt;&lt;/script&gt;',
        clean('<script/src="http://xx.com/xss.js"></script>'))


def test_unclosed_tag():
    eq_('&lt;script src="http://xx.com/xss.js&amp;lt;b"&gt;',
        clean('<script src=http://xx.com/xss.js<b>'))
    eq_('&lt;script src="http://xx.com/xss.js" &lt;b=""&gt;',
        clean('<script src="http://xx.com/xss.js"<b>'))
    eq_('&lt;script src="http://xx.com/xss.js" &lt;b=""&gt;',
        clean('<script src="http://xx.com/xss.js" <b>'))


def test_strip():
    """Using strip=True shouldn't result in malicious content."""
    s = '<scri<script>pt>alert(1)</scr</script>ipt>'
    eq_('pt&gt;alert(1)ipt&gt;', clean(s, strip=True))
    s = '<scri<scri<script>pt>pt>alert(1)</script>'
    eq_('pt&gt;pt&gt;alert(1)', clean(s, strip=True))


def test_nasty():
    """Nested, broken up, multiple tags, are still foiled!"""
    test = ('<scr<script></script>ipt type="text/javascript">alert("foo");</'
            '<script></script>script<del></del>>')
    expect = ('&lt;scr&lt;script&gt;&lt;/script&gt;ipt type="text/javascript"'
              '&gt;alert("foo");&lt;/script&gt;script&lt;del&gt;&lt;/del&gt;'
              '&gt;')
    eq_(expect, clean(test))


def test_poster_attribute():
    """Poster attributes should not allow javascript."""
    tags = ['video']
    attrs = {'video': ['poster']}
    test = '<video poster="javascript:alert(1)"></video>'
    expect = '<video></video>'
    eq_(expect, clean(test, tags=tags, attributes=attrs))
    ok = '<video poster="/foo.png"></video>'
    eq_(ok, clean(ok, tags=tags, attributes=attrs))


def test_feed_protocol():
    eq_('<a>foo</a>', clean('<a href="feed:file:///tmp/foo">foo</a>'))

########NEW FILE########
__FILENAME__ = test_unicode
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from nose.tools import eq_

from bleach import clean, linkify
from bleach.tests.tools import in_


def test_japanese_safe_simple():
    eq_('ヘルプとチュートリアル', clean('ヘルプとチュートリアル'))
    eq_('ヘルプとチュートリアル', linkify('ヘルプとチュートリアル'))


def test_japanese_strip():
    eq_('<em>ヘルプとチュートリアル</em>',
        clean('<em>ヘルプとチュートリアル</em>'))
    eq_('&lt;span&gt;ヘルプとチュートリアル&lt;/span&gt;',
        clean('<span>ヘルプとチュートリアル</span>'))


def test_russian_simple():
    eq_('Домашняя', clean('Домашняя'))
    eq_('Домашняя', linkify('Домашняя'))


def test_mixed():
    eq_('Домашняяヘルプとチュートリアル',
        clean('Домашняяヘルプとチュートリアル'))


def test_mixed_linkify():
    in_(('Домашняя <a href="http://example.com" rel="nofollow">'
        'http://example.com</a> ヘルプとチュートリアル',
        'Домашняя <a rel="nofollow" href="http://example.com">'
        'http://example.com</a> ヘルプとチュートリアル'),
        linkify('Домашняя http://example.com ヘルプとチュートリアル'))


def test_url_utf8():
    """Allow UTF8 characters in URLs themselves."""
    outs = ('<a href="{0!s}" rel="nofollow">{0!s}</a>',
            '<a rel="nofollow" href="{0!s}">{0!s}</a>')

    out = lambda url: [x.format(url) for x in outs]

    tests = (
        ('http://éxámplé.com/', out('http://éxámplé.com/')),
        ('http://éxámplé.com/íàñá/', out('http://éxámplé.com/íàñá/')),
        ('http://éxámplé.com/íàñá/?foo=bar',
         out('http://éxámplé.com/íàñá/?foo=bar')),
        ('http://éxámplé.com/íàñá/?fóo=bár',
         out('http://éxámplé.com/íàñá/?fóo=bár')),
    )

    def check(test, expected_output):
        in_(expected_output, linkify(test))

    for test, expected_output in tests:
        yield check, test, expected_output

########NEW FILE########
__FILENAME__ = tools


def in_(l, a, msg=None):
    """Shorthand for 'assert a in l, "%r not in %r" % (a, l)
    """
    if not a in l:
        raise AssertionError(msg or "%r not in %r" % (a, l))

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Bleach documentation build configuration file, created by
# sphinx-quickstart on Fri May 11 21:11:39 2012.
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
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.pngmath', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Bleach'
copyright = u'2012-2104, James Socol'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.4'
# The full version, including alpha/beta/rc tags.
release = '1.4.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
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
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Bleachdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Bleach.tex', u'Bleach Documentation',
   u'James Socol', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'bleach', u'Bleach Documentation',
     [u'James Socol'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Bleach', u'Bleach Documentation',
   u'James Socol', 'Bleach', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
