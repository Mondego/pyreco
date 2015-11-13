__FILENAME__ = premailer
import threading
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
import cgi
import codecs
import gzip
import operator
import os
import re
import urllib2
import urlparse

import cssutils
from lxml import etree
from lxml.cssselect import CSSSelector


__all__ = ['PremailerError', 'Premailer', 'transform']


class PremailerError(Exception):
    pass


grouping_regex = re.compile('([:\-\w]*){([^}]+)}')


def merge_styles(old, new, class_=''):
    """
    if ::
      old = 'font-size:1px; color: red'
    and ::
      new = 'font-size:2px; font-weight: bold'
    then ::
      return 'color: red; font-size:2px; font-weight: bold'

    In other words, the new style bits replace the old ones.

    The @class_ parameter can be something like ':hover' and if that
    is there, you split up the style with '{...} :hover{...}'
    Note: old could be something like '{...} ::first-letter{...}'

    """

    def csstext_to_pairs(csstext):
        parsed = cssutils.css.CSSVariablesDeclaration(csstext)
        for key in parsed:
            yield (key, parsed.getVariableValue(key))

    new_keys = set()
    news = []

    # The code below is wrapped in a critical section implemented via ``RLock``-class lock.
    # The lock is required to avoid ``cssutils`` concurrency issues documented in issue #65
    with merge_styles._lock:
        for k, v in csstext_to_pairs(new):
            news.append((k.strip(), v.strip()))
            new_keys.add(k.strip())

        groups = {}
        grouped_split = grouping_regex.findall(old)
        if grouped_split:
            for old_class, old_content in grouped_split:
                olds = []
                for k, v in csstext_to_pairs(old_content):
                    olds.append((k.strip(), v.strip()))
                groups[old_class] = olds
        else:
            olds = []
            for k, v in csstext_to_pairs(old):
                olds.append((k.strip(), v.strip()))
            groups[''] = olds

    # Perform the merge
    relevant_olds = groups.get(class_, {})
    merged = [style for style in relevant_olds if style[0] not in new_keys] + news
    groups[class_] = merged

    if len(groups) == 1:
        return '; '.join('%s:%s' % (k, v) for
                          (k, v) in sorted(groups.values()[0]))
    else:
        all = []
        for class_, mergeable in sorted(groups.items(),
                                        lambda x, y: cmp(x[0].count(':'),
                                                         y[0].count(':'))):
            all.append('%s{%s}' % (class_,
                                   '; '.join('%s:%s' % (k, v)
                                              for (k, v)
                                              in mergeable)))
        return ' '.join(x for x in all if x != '{}')

# The lock is used in merge_styles function to work around threading concurrency bug of cssutils library.
# The bug is documented in issue #65. The bug's reproduction test in test_premailer.test_multithreading.
merge_styles._lock = threading.RLock()

def make_important(bulk):
    """makes every property in a string !important.
    """
    return ';'.join('%s !important' % p if not p.endswith('!important') else p
                    for p in bulk.split(';'))


_element_selector_regex = re.compile(r'(^|\s)\w')
_cdata_regex = re.compile(r'\<\!\[CDATA\[(.*?)\]\]\>', re.DOTALL)
_importants = re.compile('\s*!important')
# These selectors don't apply to all elements. Rather, they specify
# which elements to apply to.
FILTER_PSEUDOSELECTORS = [':last-child', ':first-child', 'nth-child']


class Premailer(object):

    def __init__(self, html, base_url=None,
                 preserve_internal_links=False,
                 preserve_inline_attachments=True,
                 exclude_pseudoclasses=True,
                 keep_style_tags=False,
                 include_star_selectors=False,
                 remove_classes=True,
                 strip_important=True,
                 external_styles=None,
                 method="html",
                 base_path=None,
                 disable_basic_attributes=None,
                 disable_validation=False):
        self.html = html
        self.base_url = base_url
        self.preserve_internal_links = preserve_internal_links
        self.preserve_inline_attachments = preserve_inline_attachments
        self.exclude_pseudoclasses = exclude_pseudoclasses
        # whether to delete the <style> tag once it's been processed
        self.keep_style_tags = keep_style_tags
        self.remove_classes = remove_classes
        # whether to process or ignore selectors like '* { foo:bar; }'
        self.include_star_selectors = include_star_selectors
        if isinstance(external_styles, basestring):
            external_styles = [external_styles]
        self.external_styles = external_styles
        self.strip_important = strip_important
        self.method = method
        self.base_path = base_path
        if disable_basic_attributes is None:
            disable_basic_attributes = []
        self.disable_basic_attributes = disable_basic_attributes
        self.disable_validation = disable_validation

    def _parse_style_rules(self, css_body, ruleset_index):
        leftover = []
        rules = []
        rule_index = 0
        # empty string
        if not css_body:
            return rules, leftover
        sheet = cssutils.parseString(css_body, validate=not self.disable_validation)
        for rule in sheet:
            # ignore comment
            if rule.type == rule.COMMENT:
                continue
            # handle media rule
            if rule.type == rule.MEDIA_RULE:
                leftover.append(rule)
                continue
            bulk = ';'.join(
                u'{0}:{1}'.format(key, rule.style[key])
                for key in rule.style.keys()
            )
            selectors = (
                x.strip()
                for x in rule.selectorText.split(',')
                if x.strip() and not x.strip().startswith('@')
            )
            for selector in selectors:
                if (':' in selector and self.exclude_pseudoclasses and
                    ':' + selector.split(':', 1)[1]
                        not in FILTER_PSEUDOSELECTORS):
                    # a pseudoclass
                    leftover.append((selector, bulk))
                    continue
                elif selector == '*' and not self.include_star_selectors:
                    continue

                # Crudely calculate specificity
                id_count = selector.count('#')
                class_count = selector.count('.')
                element_count = len(_element_selector_regex.findall(selector))

                specificity = (id_count, class_count, element_count, ruleset_index, rule_index)

                rules.append((specificity, selector, bulk))
                rule_index += 1

        return rules, leftover

    def transform(self, pretty_print=True, **kwargs):
        """change the self.html and return it with CSS turned into style
        attributes.
        """
        if etree is None:
            return self.html

        if self.method == 'xml':
            parser = etree.XMLParser(ns_clean=False, resolve_entities=False)
        else:
            parser = etree.HTMLParser()
        stripped = self.html.strip()
        tree = etree.fromstring(stripped, parser).getroottree()
        page = tree.getroot()
        # lxml inserts a doctype if none exists, so only include it in
        # the root if it was in the original html.
        root = tree if stripped.startswith(tree.docinfo.doctype) else page

        if page is None:
            print repr(self.html)
            raise PremailerError("Could not parse the html")
        assert page is not None

        ##
        ## style selectors
        ##

        rules = []
        index = 0

        for element in CSSSelector('style,link[rel~=stylesheet]')(page):
            # If we have a media attribute whose value is anything other than
            # 'screen', ignore the ruleset.
            media = element.attrib.get('media')
            if media and media != 'screen':
                continue

            is_style = element.tag == 'style'
            if is_style:
                css_body = element.text
            else:
                href = element.attrib.get('href')
                if not href:
                    continue
                css_body = self._load_external(href)

            these_rules, these_leftover = self._parse_style_rules(css_body, index)
            index += 1
            rules.extend(these_rules)

            parent_of_element = element.getparent()
            if these_leftover:
                if is_style:
                    style = element
                else:
                    style = etree.Element('style')
                    style.attrib['type'] = 'text/css'

                lines = []
                for item in these_leftover:
                    if isinstance(item, tuple):
                        k, v = item
                        lines.append('%s {%s}' % (k, make_important(v)))
                    # media rule
                    else:
                        for rule in item.cssRules:
                            if isinstance(rule, cssutils.css.csscomment.CSSComment):
                                continue
                            for key in rule.style.keys():
                                rule.style[key] = (
                                    rule.style.getPropertyValue(key, False),
                                    '!important'
                                )
                        lines.append(item.cssText)
                style.text = '\n'.join(lines)
                if self.method == 'xml':
                    style.text = etree.CDATA(style.text)

                if not is_style:
                    element.addprevious(style)
                    parent_of_element.remove(element)

            elif not self.keep_style_tags or not is_style:
                parent_of_element.remove(element)

        if self.external_styles:
            for stylefile in self.external_styles:
                css_body = self._load_external(stylefile)
                these_rules, these_leftover = self._parse_style_rules(css_body, index)
                index += 1
                rules.extend(these_rules)

        # rules is a tuple of (specificity, selector, styles), where specificity is a tuple
        # ordered such that more specific rules sort larger.
        rules.sort(key=operator.itemgetter(0))

        first_time = []
        first_time_styles = []
        for __, selector, style in rules:
            new_selector = selector
            class_ = ''
            if ':' in selector:
                new_selector, class_ = re.split(':', selector, 1)
                class_ = ':%s' % class_
            # Keep filter-type selectors untouched.
            if class_ in FILTER_PSEUDOSELECTORS:
                class_ = ''
            else:
                selector = new_selector

            sel = CSSSelector(selector)
            for item in sel(page):
                old_style = item.attrib.get('style', '')
                if not item in first_time:
                    new_style = merge_styles(old_style, style, class_)
                    first_time.append(item)
                    first_time_styles.append((item, old_style))
                else:
                    new_style = merge_styles(old_style, style, class_)
                item.attrib['style'] = new_style
                self._style_to_basic_html_attributes(item, new_style,
                                                     force=True)

        # Re-apply initial inline styles.
        for item, inline_style in first_time_styles:
            old_style = item.attrib.get('style', '')
            if not inline_style:
                continue
            new_style = merge_styles(old_style, inline_style, class_)
            item.attrib['style'] = new_style
            self._style_to_basic_html_attributes(item, new_style, force=True)

        if self.remove_classes:
            # now we can delete all 'class' attributes
            for item in page.xpath('//@class'):
                parent = item.getparent()
                del parent.attrib['class']

        ##
        ## URLs
        ##
        if self.base_url:
            for attr in ('href', 'src'):
                for item in page.xpath("//@%s" % attr):
                    parent = item.getparent()
                    if attr == 'href' and self.preserve_internal_links \
                           and parent.attrib[attr].startswith('#'):
                        continue
                    if attr == 'src' and self.preserve_inline_attachments \
                           and parent.attrib[attr].startswith('cid:'):
                        continue
                    if not self.base_url.endswith('/'):
                        self.base_url += '/'
                    parent.attrib[attr] = urlparse.urljoin(self.base_url,
                        parent.attrib[attr].lstrip('/'))

        kwargs.setdefault('method', self.method)
        kwargs.setdefault('pretty_print', pretty_print)
        out = etree.tostring(root, **kwargs)
        if self.method == 'xml':
            out = _cdata_regex.sub(lambda m: '/*<![CDATA[*/%s/*]]>*/' % m.group(1), out)
        if self.strip_important:
            out = _importants.sub('', out)
        return out

    def _load_external_url(self, url):
        r = urllib2.urlopen(url)
        _, params = cgi.parse_header(r.headers.get('Content-Type', ''))
        encoding = params.get('charset', 'utf-8')
        if 'gzip' in r.info().get('Content-Encoding', ''):
            buf = StringIO.StringIO(r.read())
            f = gzip.GzipFile(fileobj=buf)
            out = f.read().decode(encoding)
        else:
            out = r.read().decode(encoding)
        return out

    def _load_external(self, url):
        """loads an external stylesheet from a remote url or local path
        """
        if url.startswith('//'):
            # then we have to rely on the base_url
            if self.base_url and 'https://' in self.base_url:
                url = 'https:' + url
            else:
                url = 'http:' + url

        if url.startswith('http://') or url.startswith('https://'):
            css_body = self._load_external_url(url)
        else:
            stylefile = url
            if not os.path.isabs(stylefile):
                stylefile = os.path.abspath(
                    os.path.join(self.base_path or '', stylefile)
                )
            if os.path.exists(stylefile):
                with codecs.open(stylefile, encoding='utf-8') as f:
                    css_body = f.read()
            elif self.base_url:
                url = urlparse.urljoin(self.base_url, url)
                return self._load_external(url)
            else:
                raise ValueError(u"Could not find external style: %s" %
                                 stylefile)
        return css_body

    def _style_to_basic_html_attributes(self, element, style_content,
                                        force=False):
        """given an element and styles like
        'background-color:red; font-family:Arial' turn some of that into HTML
        attributes. like 'bgcolor', etc.

        Note, the style_content can contain pseudoclasses like:
        '{color:red; border:1px solid green} :visited{border:1px solid green}'
        """
        if style_content.count('}') and \
          style_content.count('{') == style_content.count('{'):
            style_content = style_content.split('}')[0][1:]

        attributes = {}
        for key, value in [x.split(':') for x in style_content.split(';')
                           if len(x.split(':')) == 2]:
            key = key.strip()

            if key == 'text-align':
                attributes['align'] = value.strip()
            elif key == 'background-color':
                attributes['bgcolor'] = value.strip()
            elif key == 'width' or key == 'height':
                value = value.strip()
                if value.endswith('px'):
                    value = value[:-2]
                attributes[key] = value
            #else:
            #    print "key", repr(key)
            #    print 'value', repr(value)

        for key, value in attributes.items():
            if key in element.attrib and not force or key in self.disable_basic_attributes:
                # already set, don't dare to overwrite
                continue
            element.attrib[key] = value


def transform(html, base_url=None):
    return Premailer(html, base_url=base_url).transform()


if __name__ == '__main__':
    html = """<html>
        <head>
        <title>Test</title>
        <style>
        h1, h2 { color:red; }
        strong {
          text-decoration:none
          }
        p { font-size:2px }
        p.footer { font-size: 1px}
        </style>
        </head>
        <body>
        <h1>Hi!</h1>
        <p><strong>Yes!</strong></p>
        <p class="footer" style="color:red">Feetnuts</p>
        </body>
        </html>"""
    p = Premailer(html)
    print p.transform()

########NEW FILE########
__FILENAME__ = test_premailer
import sys
import re
from contextlib import contextmanager
from StringIO import StringIO
import gzip

from nose.tools import eq_, ok_
import mock

from premailer import Premailer, etree, merge_styles
from .__main__ import main


whitespace_between_tags = re.compile('>\s*<')


@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


@contextmanager
def provide_input(content):
    old_stdin = sys.stdin
    sys.stdin = StringIO(content)
    try:
        with captured_output() as (out, err):
            yield out, err
    finally:
        sys.stdin = old_stdin
        sys.stdin = StringIO(content)


def test_merge_styles_basic():
    old = 'font-size:1px; color: red'
    new = 'font-size:2px; font-weight: bold'
    expect = 'color:red;', 'font-size:2px;', 'font-weight:bold'
    result = merge_styles(old, new)
    for each in expect:
        assert each in result


def test_merge_styles_with_class():
    old = 'color:red; font-size:1px;'
    new, class_ = 'font-size:2px; font-weight: bold', ':hover'

    # because we're dealing with dicts (random order) we have to
    # test carefully.
    # We expect something like this:
    #  {color:red; font-size:1px} :hover{font-size:2px; font-weight:bold}

    result = merge_styles(old, new, class_)
    ok_(result.startswith('{'))
    ok_(result.endswith('}'))
    ok_(' :hover{' in result)
    split_regex = re.compile('{([^}]+)}')
    eq_(len(split_regex.findall(result)), 2)
    expect_first = 'color:red', 'font-size:1px'
    expect_second = 'font-weight:bold', 'font-size:2px'
    for each in expect_first:
        ok_(each in split_regex.findall(result)[0])
    for each in expect_second:
        ok_(each in split_regex.findall(result)[1])


def test_merge_styles_non_trivial():
    old = 'background-image:url("data:image/png;base64,iVBORw0KGg")'
    new = 'font-size:2px; font-weight: bold'
    expect = (
        'background-image:url("data:image/png;base64,iVBORw0KGg")',
        'font-size:2px;',
        'font-weight:bold'
    )
    result = merge_styles(old, new)
    for each in expect:
       assert each in result


def test_basic_html():
    """test the simplest case"""
    if not etree:
        # can't test it
        return

    html = """<html>
    <head>
    <title>Title</title>
    <style type="text/css">
    h1, h2 { color:red; }
    strong {
        text-decoration:none
        }
    </style>
    </head>
    <body>
    <h1>Hi!</h1>
    <p><strong>Yes!</strong></p>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    <title>Title</title>
    </head>
    <body>
    <h1 style="color:red">Hi!</h1>
    <p><strong style="text-decoration:none">Yes!</strong></p>
    </body>
    </html>"""

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_empty_style_tag():
    """empty style tag"""
    if not etree:
        # can't test it
        return

    html = """<html>
    <head>
    <title></title>
    <style type="text/css"></style>
    </head>
    <body>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    <title></title>
    </head>
    <body>
    </body>
    </html>"""

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_mixed_pseudo_selectors():
    """mixing pseudo selectors with straight forward selectors"""
    if not etree:
        # can't test it
        return

    html = """<html>
    <head>
    <title>Title</title>
    <style type="text/css">
    p { color: yellow }
    a { color: blue }
    a:hover { color: pink }
    </style>
    </head>
    <body>
    <p>
      <a href="#">Page</a>
    </p>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    <title>Title</title>
    <style type="text/css">a:hover {color:pink}</style>
    </head>
    <body>
    <p style="color:yellow"><a href="#" style="color:blue">Page</a></p>
    </body>
    </html>"""

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_basic_html_with_pseudo_selector():
    """test the simplest case"""
    if not etree:
        # can't test it
        return

    html = """
    <html>
    <style type="text/css">
    h1 { border:1px solid black }
    p { color:red;}
    p::first-letter { float:left; }
    </style>
    <h1 style="font-weight:bolder">Peter</h1>
    <p>Hej</p>
    </html>
    """

    expect_html = """<html>
    <head>
    <style type="text/css">p::first-letter {float:left}</style>
    </head>
    <body>
    <h1 style="border:1px solid black; font-weight:bolder">Peter</h1>
    <p style="color:red">Hej</p>
    </body>
    </html>"""

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_parse_style_rules():
    p = Premailer('html')  # won't need the html
    func = p._parse_style_rules
    rules, leftover = func("""
    h1, h2 { color:red; }
    /* ignore
        this */
    strong {
        text-decoration:none
        }
    ul li {  list-style: 2px; }
    a:hover { text-decoration: underline }
    """, 0)

    # 'rules' is a list, turn it into a dict for
    # easier assertion testing
    rules_dict = {}
    rules_specificity = {}
    for specificity, k, v in rules:
        rules_dict[k] = v
        rules_specificity[k] = specificity

    assert 'h1' in rules_dict
    assert 'h2' in rules_dict
    assert 'strong' in rules_dict
    assert 'ul li' in rules_dict

    assert rules_dict['h1'] == 'color:red'
    assert rules_dict['h2'] == 'color:red'
    assert rules_dict['strong'] == 'text-decoration:none'
    assert rules_dict['ul li'] == 'list-style:2px'
    assert 'a:hover' not in rules_dict

    p = Premailer('html', exclude_pseudoclasses=True)  # won't need the html
    func = p._parse_style_rules
    rules, leftover = func("""
    ul li {  list-style: 2px; }
    a:hover { text-decoration: underline }
    """, 0)

    assert len(rules) == 1
    specificity, k, v = rules[0]
    assert k == 'ul li'
    assert v == 'list-style:2px'

    assert len(leftover) == 1
    k, v = leftover[0]
    assert (k, v) == ('a:hover', 'text-decoration:underline'), (k, v)


def test_precedence_comparison():
    p = Premailer('html')  # won't need the html
    rules, leftover = p._parse_style_rules("""
    #identified { color:blue; }
    h1, h2 { color:red; }
    ul li {  list-style: 2px; }
    li.example { color:green; }
    strong { text-decoration:none }
    div li.example p.sample { color:black; }
    """, 0)

    # 'rules' is a list, turn it into a dict for
    # easier assertion testing
    rules_specificity = {}
    for specificity, k, v in rules:
        rules_specificity[k] = specificity

    # Last in file wins
    assert rules_specificity['h1'] < rules_specificity['h2']
    # More elements wins
    assert rules_specificity['strong'] < rules_specificity['ul li']
    # IDs trump everything
    assert (rules_specificity['div li.example p.sample'] <
            rules_specificity['#identified'])

    # Classes trump multiple elements
    assert (rules_specificity['ul li'] <
            rules_specificity['li.example'])


def test_base_url_fixer():
    """if you leave some URLS as /foo and set base_url to
    'http://www.google.com' the URLS become 'http://www.google.com/foo'
    """
    if not etree:
        # can't test it
        return

    html = '''<html>
    <head>
    <title>Title</title>
    </head>
    <body>
    <img src="/images/foo.jpg">
    <img src="/images/bar.gif">
    <img src="http://www.googe.com/photos/foo.jpg">
    <a href="/home">Home</a>
    <a href="http://www.peterbe.com">External</a>
    <a href="subpage">Subpage</a>
    <a href="#internal_link">Internal Link</a>
    </body>
    </html>
    '''

    expect_html = '''<html>
    <head>
    <title>Title</title>
    </head>
    <body>
    <img src="http://kungfupeople.com/images/foo.jpg">
    <img src="http://kungfupeople.com/images/bar.gif">
    <img src="http://www.googe.com/photos/foo.jpg">
    <a href="http://kungfupeople.com/home">Home</a>
    <a href="http://www.peterbe.com">External</a>
    <a href="http://kungfupeople.com/subpage">Subpage</a>
    <a href="#internal_link">Internal Link</a>
    </body>
    </html>'''

    p = Premailer(html, base_url='http://kungfupeople.com',
                  preserve_internal_links=True)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_base_url_with_path():
    """if you leave some URLS as /foo and set base_url to
    'http://www.google.com' the URLS become 'http://www.google.com/foo'
    """
    if not etree:
        # can't test it
        return

    html = '''<html>
    <head>
    <title>Title</title>
    </head>
    <body>
    <img src="/images/foo.jpg">
    <img src="/images/bar.gif">
    <img src="http://www.googe.com/photos/foo.jpg">
    <a href="/home">Home</a>
    <a href="http://www.peterbe.com">External</a>
    <a href="http://www.peterbe.com/base/">External 2</a>
    <a href="subpage">Subpage</a>
    <a href="#internal_link">Internal Link</a>
    </body>
    </html>
    '''

    expect_html = '''<html>
    <head>
    <title>Title</title>
    </head>
    <body>
    <img src="http://kungfupeople.com/base/images/foo.jpg">
    <img src="http://kungfupeople.com/base/images/bar.gif">
    <img src="http://www.googe.com/photos/foo.jpg">
    <a href="http://kungfupeople.com/base/home">Home</a>
    <a href="http://www.peterbe.com">External</a>
    <a href="http://www.peterbe.com/base/">External 2</a>
    <a href="http://kungfupeople.com/base/subpage">Subpage</a>
    <a href="#internal_link">Internal Link</a>
    </body>
    </html>'''

    p = Premailer(html, base_url='http://kungfupeople.com/base',
                  preserve_internal_links=True)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_style_block_with_external_urls():
    """
    From http://github.com/peterbe/premailer/issues/#issue/2

    If you have
      body { background:url(http://example.com/bg.png); }
    the ':' inside '://' is causing a problem
    """
    if not etree:
        # can't test it
        return

    html = """<html>
    <head>
    <title>Title</title>
    <style type="text/css">
    body {
      color:#123;
      background: url(http://example.com/bg.png);
      font-family: Omerta;
    }
    </style>
    </head>
    <body>
    <h1>Hi!</h1>
    </body>
    </html>"""

    expect_html = '''<html>
    <head>
    <title>Title</title>
    </head>
    <body style="background:url(http://example.com/bg.png); color:#123; font-family:Omerta">
    <h1>Hi!</h1>
    </body>
    </html>'''

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()
    eq_(expect_html, result_html)


def test_shortcut_function():
    # you don't have to use this approach:
    #   from premailer import Premailer
    #   p = Premailer(html, base_url=base_url)
    #   print p.transform()
    # You can do it this way:
    #   from premailer import transform
    #   print transform(html, base_url=base_url)

    if not etree:
        # can't test it
        return

    html = '''<html>
    <head>
    <style type="text/css">h1{color:#123}</style>
    </head>
    <body>
    <h1>Hi!</h1>
    </body>
    </html>'''

    expect_html = '''<html>
    <head></head>
    <body>
    <h1 style="color:#123">Hi!</h1>
    </body>
    </html>'''

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    assert expect_html == result_html, result_html


def test_css_with_pseudoclasses_included():
    "Pick up the pseudoclasses too and include them"
    if not etree:
        # can't test it
        return

    html = '''<html>
    <head>
    <style type="text/css">
    a.special:link { text-decoration:none; }
    a { color:red; }
    a:hover { text-decoration:none; }
    a,a:hover,
    a:visited { border:1px solid green; }
    p::first-letter {float: left; font-size: 300%}
    </style>
    </head>
    <body>
    <a href="#" class="special">Special!</a>
    <a href="#">Page</a>
    <p>Paragraph</p>
    </body>
    </html>'''

    p = Premailer(html, exclude_pseudoclasses=False)
    result_html = p.transform()

    # because we're dealing with random dicts here we can't predict what
    # order the style attribute will be written in so we'll look for things
    # manually.
    assert '<p style="::first-letter{font-size:300%; float:left}">' \
           'Paragraph</p>' in result_html

    assert 'style="{color:red; border:1px solid green}' in result_html
    assert ' :visited{border:1px solid green}' in result_html
    assert ' :hover{border:1px solid green; text-decoration:none}' in \
           result_html


def test_css_with_pseudoclasses_excluded():
    "Skip things like `a:hover{}` and keep them in the style block"
    if not etree:
        # can't test it
        return

    html = '''<html>
    <head>
    <style type="text/css">
    a { color:red; }
    a:hover { text-decoration:none; }
    a,a:hover,
    a:visited { border:1px solid green; }
    p::first-letter {float: left; font-size: 300%}
    </style>
    </head>
    <body>
    <a href="#">Page</a>
    <p>Paragraph</p>
    </body>
    </html>'''

    expect_html = '''<html>
    <head>
    <style type="text/css">a:hover {text-decoration:none}
    a:hover {border:1px solid green}
    a:visited {border:1px solid green}p::first-letter {float:left;font-size:300%}
    </style>
    </head>
    <body>
    <a href="#" style="border:1px solid green; color:red">Page</a>
    <p>Paragraph</p>
    </body>
    </html>'''

    p = Premailer(html, exclude_pseudoclasses=True)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    expect_html = re.sub('}\s+', '}', expect_html)
    result_html = result_html.replace('}\n', '}')

    eq_(expect_html, result_html)


def test_css_with_html_attributes():
    """Some CSS styles can be applied as normal HTML attribute like
    'background-color' can be turned into 'bgcolor'
    """
    if not etree:
        # can't test it
        return

    html = """<html>
    <head>
    <style type="text/css">
    td { background-color:red; }
    p { text-align:center; }
    table { width:200px; }
    </style>
    </head>
    <body>
    <p>Text</p>
    <table>
      <tr>
        <td>Cell 1</td>
        <td>Cell 2</td>
      </tr>
    </table>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    </head>
    <body>
    <p style="text-align:center" align="center">Text</p>
    <table style="width:200px" width="200">
      <tr>
        <td style="background-color:red" bgcolor="red">Cell 1</td>
        <td style="background-color:red" bgcolor="red">Cell 2</td>
      </tr>
    </table>
    </body>
    </html>"""

    p = Premailer(html, exclude_pseudoclasses=True)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    expect_html = re.sub('}\s+', '}', expect_html)
    result_html = result_html.replace('}\n', '}')

    eq_(expect_html, result_html)


def test_css_disable_basic_html_attributes():
    """Some CSS styles can be applied as normal HTML attribute like
    'background-color' can be turned into 'bgcolor'
    """
    if not etree:
        # can't test it
        return

    html = """<html>
    <head>
    <style type="text/css">
    td { background-color:red; }
    p { text-align:center; }
    table { width:200px; height: 300px; }
    </style>
    </head>
    <body>
    <p>Text</p>
    <table>
      <tr>
        <td>Cell 1</td>
        <td>Cell 2</td>
      </tr>
    </table>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    </head>
    <body>
    <p style="text-align:center">Text</p>
    <table style="height:300px; width:200px">
      <tr>
        <td style="background-color:red" bgcolor="red">Cell 1</td>
        <td style="background-color:red" bgcolor="red">Cell 2</td>
      </tr>
    </table>
    </body>
    </html>"""

    p = Premailer(html, exclude_pseudoclasses=True, disable_basic_attributes=['align', 'width', 'height'])
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    expect_html = re.sub('}\s+', '}', expect_html)
    result_html = result_html.replace('}\n', '}')

    eq_(expect_html, result_html)


def test_apple_newsletter_example():
    # stupidity test
    import os

    html_file = os.path.join(os.path.dirname(__file__),
                             'test-apple-newsletter.html')
    html = open(html_file).read()

    p = Premailer(html, exclude_pseudoclasses=False,
                  keep_style_tags=True,
                  strip_important=False)
    result_html = p.transform()
    ok_('<html>' in result_html)
    ok_('<style media="only screen and (max-device-width: 480px)" '
        'type="text/css">\n'
        '* {line-height: normal !important; -webkit-text-size-adjust: 125%}\n'
        '</style>' in result_html)


def test_mailto_url():
    """if you use URL with mailto: protocol, they should stay as mailto:
    when baseurl is used
    """
    if not etree:
        # can't test it
        return

    html = """<html>
    <head>
    <title>Title</title>
    </head>
    <body>
    <a href="mailto:e-mail@example.com">e-mail@example.com</a>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    <title>Title</title>
    </head>
    <body>
    <a href="mailto:e-mail@example.com">e-mail@example.com</a>
    </body>
    </html>"""

    p = Premailer(html, base_url='http://kungfupeople.com')
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    assert expect_html == result_html


def test_strip_important():
    """Get rid of !important. Makes no sense inline."""
    html = """<html>
    <head>
    <style type="text/css">
    p {
        height:100% !important;
        width:100% !important;
    }
    </style>
    </head>
    <body>
    <p>Paragraph</p>
    </body>
    </html>
    """
    expect_html = """<html>
    <head>
    </head>
    <body>
    <p style="height:100%; width:100%" width="100%" height="100%">Paragraph</p>
    </body>
    </html>"""

    p = Premailer(html, strip_important=True)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_inline_wins_over_external():
    html = """<html>
    <head>
    <style type="text/css">
    div {
        text-align: left;
    }
    /* This tests that a second loop for the same style still doesn't
     * overwrite it. */
    div {
        text-align: left;
    }
    </style>
    </head>
    <body>
    <div style="text-align:right">Some text</div>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    </head>
    <body>
    <div style="text-align:right" align="right">Some text</div>
    </body>
    </html>"""

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_last_child():
    html = """<html>
    <head>
    <style type="text/css">
    div {
        text-align: right;
    }
    div:last-child {
        text-align: left;
    }
    </style>
    </head>
    <body>
    <div>First child</div>
    <div>Last child</div>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    </head>
    <body>
    <div style="text-align:right" align="right">First child</div>
    <div style="text-align:left" align="left">Last child</div>
    </body>
    </html>"""

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_last_child_exclude_pseudo():
    html = """<html>
    <head>
    <style type="text/css">
    div {
        text-align: right;
    }
    div:last-child {
        text-align: left;
    }
    </style>
    </head>
    <body>
    <div>First child</div>
    <div>Last child</div>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    </head>
    <body>
    <div style="text-align:right" align="right">First child</div>
    <div style="text-align:left" align="left">Last child</div>
    </body>
    </html>"""

    p = Premailer(html, exclude_pseudoclasses=True)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_mediaquery():
    html = """<html>
    <head>
    <style type="text/css">
    div {
        text-align: right;
    }
    @media print{
        div {
            text-align: center;
            color: white;
        }
        div {
            font-size: 999px;
        }
    }
    </style>
    </head>
    <body>
    <div>First div</div>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    <style type="text/css">@media print {
    div {
        text-align: center !important;
        color: white !important
        }
    div {
        font-size: 999px !important
        }
    }</style>
    </head>
    <body>
    <div style="text-align:right" align="right">First div</div>
    </body>
    </html>"""

    p = Premailer(html, strip_important=False)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_child_selector():
    html = """<html>
    <head>
    <style type="text/css">
    body > div {
        text-align: right;
    }
    </style>
    </head>
    <body>
    <div>First div</div>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    </head>
    <body>
    <div style="text-align:right" align="right">First div</div>
    </body>
    </html>"""

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_doctype():
    html = (
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
        '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
        """<html>
        <head>
        </head>
        <body>
        </body>
        </html>"""
    )

    expect_html = (
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
        '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
        """<html>
        <head>
        </head>
        <body>
        </body>
        </html>"""
    )

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_prefer_inline_to_class():
    html = """<html>
    <head>
    <style>
    .example {
        color: black;
    }
    </style>
    </head>
    <body>
    <div class="example" style="color:red"></div>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    </head>
    <body>
    <div style="color:red"></div>
    </body>
    </html>"""

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_favour_rule_with_element_over_generic():
    html = """<html>
    <head>
    <style>
    div.example {
        color: green;
    }
    .example {
        color: black;
    }
    </style>
    </head>
    <body>
    <div class="example"></div>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    </head>
    <body>
    <div style="color:green"></div>
    </body>
    </html>"""

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_favour_rule_with_class_over_generic():
    html = """<html>
    <head>
    <style>
    div.example {
        color: green;
    }
    div {
        color: black;
    }
    </style>
    </head>
    <body>
    <div class="example"></div>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    </head>
    <body>
    <div style="color:green"></div>
    </body>
    </html>"""

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_favour_rule_with_id_over_others():
    html = """<html>
    <head>
    <style>
    #identified {
        color: green;
    }
    div.example {
        color: black;
    }
    </style>
    </head>
    <body>
    <div class="example" id="identified"></div>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    </head>
    <body>
    <div id="identified" style="color:green"></div>
    </body>
    </html>"""

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_multiple_style_elements():
    """Asserts that rules from multiple style elements are inlined correctly."""
    if not etree:
        # can't test it
        return

    html = """<html>
    <head>
    <title>Title</title>
    <style type="text/css">
    h1, h2 { color:red; }
    strong {
        text-decoration:none
        }
    </style>
    <style type="text/css">
    h1, h2 { color:green; }
    p {
        font-size:120%
        }
    </style>
    </head>
    <body>
    <h1>Hi!</h1>
    <p><strong>Yes!</strong></p>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    <title>Title</title>
    </head>
    <body>
    <h1 style="color:green">Hi!</h1>
    <p style="font-size:120%"><strong style="text-decoration:none">Yes!</strong></p>
    </body>
    </html>"""

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_style_attribute_specificity():
    """Stuff already in style attributes beats style tags."""
    if not etree:
        # can't test it
        return

    html = """<html>
    <head>
    <title>Title</title>
    <style type="text/css">
    h1 { color: pink }
    h1.foo { color: blue }
    </style>
    </head>
    <body>
    <h1 class="foo" style="color: green">Hi!</h1>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    <title>Title</title>
    </head>
    <body>
    <h1 style="color:green">Hi!</h1>
    </body>
    </html>"""

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_ignore_style_elements_with_media_attribute():
    """Asserts that style elements with media attributes other than
    'screen' are ignored."""
    if not etree:
        # can't test it
        return

    html = """<html>
    <head>
    <title>Title</title>
    <style type="text/css">
        h1, h2 { color:red; }
        strong {
            text-decoration:none
        }
    </style>
    <style type="text/css" media="screen">
        h1, h2 { color:green; }
        p {
            font-size:16px;
            }
    </style>
    <style type="text/css" media="only screen and (max-width: 480px)">
        h1, h2 { color:orange; }
        p {
            font-size:120%;
        }
    </style>
    </head>
    <body>
    <h1>Hi!</h1>
    <p><strong>Yes!</strong></p>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    <title>Title</title>
    <style type="text/css" media="only screen and (max-width: 480px)">
        h1, h2 { color:orange; }
        p {
            font-size:120%;
        }
    </style>
    </head>
    <body>
    <h1 style="color:green">Hi!</h1>
    <p style="font-size:16px"><strong style="text-decoration:none">Yes!</strong></p>
    </body>
    </html>"""

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_leftover_important():
    """Asserts that leftover styles should be marked as !important."""
    if not etree:
        # can't test it
        return

    html = """<html>
    <head>
    <title>Title</title>
    <style type="text/css">
    a { color: red; }
    a:hover { color: green; }
    a:focus { color: blue !important; }
    </style>
    </head>
    <body>
    <a href="#">Hi!</a>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    <title>Title</title>
    <style type="text/css">a:hover {color:green !important}
a:focus {color:blue !important}</style>
    </head>
    <body>
    <a href="#" style="color:red">Hi!</a>
    </body>
    </html>"""

    p = Premailer(html,
                  keep_style_tags=True,
                  strip_important=False)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_basic_xml():
    """Test the simplest case with xml"""
    if not etree:
        # can't test it
        return

    html = """<html>
<head>
<title>Title</title>
<style type="text/css">
img { border: none; }
</style>
</head>
<body>
<img src="test.png" alt="test"/>
</body>
</html>"""

    expect_html = """<html>
<head>
<title>Title</title>
</head>
<body>
<img src="test.png" alt="test" style="border:none"/>
</body>
</html>"""

    p = Premailer(html, method="xml")
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_xml_cdata():
    """Test that CDATA is set correctly on remaining styles"""
    if not etree:
        # can't test it
        return

    html = """<html>
<head>
<title>Title</title>
<style type="text/css">
span:hover > a { background: red; }
</style>
</head>
<body>
<span><a>Test</a></span>
</body>
</html>"""

    expect_html = """<html>
<head>
<title>Title</title>
<style type="text/css">/*<![CDATA[*/span:hover > a {background:red}/*]]>*/</style>
</head>
<body>
<span><a>Test</a></span>
</body>
</html>"""

    p = Premailer(html, method="xml")
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_command_line_fileinput_from_stdin():
    html = '<style>h1 { color:red; }</style><h1>Title</h1>'
    expect_html = """
    <html>
    <head></head>
    <body><h1 style="color:red">Title</h1></body>
    </html>
    """

    with provide_input(html) as (out, err):
        main([])
    result_html = out.getvalue().strip()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_command_line_fileinput_from_argument():
    with captured_output() as (out, err):
        main(['-f', 'premailer/test-apple-newsletter.html'])

    result_html = out.getvalue().strip()

    ok_('<html>' in result_html)
    ok_('<style media="only screen and (max-device-width: 480px)" '
        'type="text/css">\n'
        '* {line-height: normal !important; -webkit-text-size-adjust: 125%}\n'
        '</style>' in result_html)


def test_multithreading():
    """The test tests thread safety of merge_styles function which employs thread non-safe cssutils calls.
        The test would fail if merge_styles would have not been thread-safe """

    import threading
    import logging
    THREADS = 30
    REPEATS = 100


    class RepeatMergeStylesThread(threading.Thread):
        """The thread is instantiated by test and run multiple times in parallel."""
        exc = None
        def __init__(self, old, new, class_):
            """The constructor just stores merge_styles parameters"""
            super(RepeatMergeStylesThread, self).__init__()
            self.old, self.new, self.class_ = old, new, class_

        def run(self):
            """Calls merge_styles in a loop and sets exc attribute if merge_styles raises an exception."""
            for i in range(0, REPEATS):
                try:
                    merge_styles(self.old, self.new, self.class_)
                except Exception, e:
                    logging.exception("Exception in thread %s", self.name)
                    self.exc = e

    old = 'background-color:#ffffff;'
    new = 'background-color:#dddddd;'
    class_ = ''

    # start multiple threads concurrently; each calls merge_styles many times
    threads = [RepeatMergeStylesThread(old, new, class_) for i in range(0, THREADS)]
    for t in threads:
        t.start()

    # wait until all threads are done
    for t in threads:
        t.join()

    # check if any thread raised exception while in merge_styles call
    exceptions = [t.exc for t in threads if t.exc is not None]
    eq_(exceptions, [])

def test_external_links():
    """Test loading stylesheets via link tags"""
    if not etree:
        # can't test it
        return

    html = """<html>
    <head>
    <title>Title</title>
    <style type="text/css">
    h1 { color:red; }
    h3 { color:yellow; }
    </style>
    <link href="premailer/test-external-links.css" rel="stylesheet" type="text/css">
    <style type="text/css">
    h1 { color:orange; }
    </style>
    </head>
    <body>
    <h1>Hello</h1>
    <h2>World</h2>
    <h3>Test</h3>
    <a href="#">Link</a>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    <title>Title</title>
    <style type="text/css">a:hover {color:purple !important}</style>
    </head>
    <body>
    <h1 style="color:orange">Hello</h1>
    <h2 style="color:green">World</h2>
    <h3 style="color:yellow">Test</h3>
    <a href="#" style="color:pink">Link</a>
    </body>
    </html>"""

    p = Premailer(html,
        strip_important=False)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_external_styles_and_links():
    """Test loading stylesheets via both the 'external_styles' argument and link tags"""
    if not etree:
        # can't test it
        return

    html = """<html>
    <head>
    <link href="test-external-links.css" rel="stylesheet" type="text/css">
    <style type="text/css">
    h1 { color: red; }
    </style>
    </head>
    <body>
    <h1>Hello</h1>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    <style type="text/css">a:hover {color:purple !important}</style>
    </head>
    <body>
    <h1 style="color:brown">Hello</h1>
    </body>
    </html>"""

    p = Premailer(html,
        strip_important=False,
        external_styles=['test-external-styles.css'],
        base_path='premailer/')
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


class MockResponse:

    def __init__(self, content, gzip=False):
        self.content = content
        self.headers = {}
        self.gzip = gzip

    def info(self):
        if self.gzip:
            return {'Content-Encoding': 'gzip'}
        else:
            return {}
    def read(self):
        if self.gzip:
            out = StringIO()
            with gzip.GzipFile(fileobj=out, mode="w") as f:
                f.write(self.content)
            return out.getvalue()
        else:
            return self.content

@mock.patch('premailer.premailer.urllib2')
def test_external_styles_on_http(urllib2):
    """Test loading styles that are genuinely external"""

    html = """<html>
    <head>
    <link href="https://www.com/style1.css" rel="stylesheet" type="text/css">
    <link href="//www.com/style2.css" rel="stylesheet" type="text/css">
    <link href="//www.com/style3.css" rel="stylesheet" type="text/css">
    </head>
    <body>
    <h1>Hello</h1>
    <h2>World</h2>
    <h3>World</h3>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    </head>
    <body>
    <h1 style="color:brown">Hello</h1>
    <h2 style="color:pink">World</h2>
    <h3 style="color:red">World</h3>
    </body>
    </html>"""

    def mocked_urlopen(url):
        if 'style1.css' in url:
            return MockResponse(
                "h1 { color: brown }"
            )
        if 'style2.css' in url:
            return MockResponse(
                "h2 { color: pink }"
            )
        if 'style3.css' in url:
            return MockResponse(
                "h3 { color: red }", gzip=True
            )
    urllib2.urlopen = mocked_urlopen

    p = Premailer(html)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


@mock.patch('premailer.premailer.urllib2')
def test_external_styles_with_base_url(urllib2):
    """Test loading styles that are genuinely external if you use
    the base_url"""

    html = """<html>
    <head>
    <link href="style.css" rel="stylesheet" type="text/css">
    </head>
    <body>
    <h1>Hello</h1>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    </head>
    <body>
    <h1 style="color:brown">Hello</h1>
    </body>
    </html>"""

    def mocked_urlopen(url):
        if url == 'http://www.peterbe.com/style.css':
            return MockResponse(
                "h1 { color: brown }"
            )
        raise NotImplementedError(url)

    urllib2.urlopen = mocked_urlopen

    p = Premailer(
        html,
        base_url='http://www.peterbe.com/'
    )
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)

def test_disabled_validator():
    """test disabled_validator"""
    if not etree:
        # can't test it
        return

    html = """<html>
    <head>
    <title>Title</title>
    <style type="text/css">
    h1, h2 { fo:bar; }
    strong {
        color:baz;
        text-decoration:none;
        }
    </style>
    </head>
    <body>
    <h1>Hi!</h1>
    <p><strong>Yes!</strong></p>
    </body>
    </html>"""

    expect_html = """<html>
    <head>
    <title>Title</title>
    </head>
    <body>
    <h1 style="fo:bar">Hi!</h1>
    <p><strong style="color:baz; text-decoration:none">Yes!</strong></p>
    </body>
    </html>"""

    p = Premailer(html, disable_validation=True)
    result_html = p.transform()

    expect_html = whitespace_between_tags.sub('><', expect_html).strip()
    result_html = whitespace_between_tags.sub('><', result_html).strip()

    eq_(expect_html, result_html)


def test_comments_in_media_queries():
    """CSS comments inside a media query block should not be a problem"""
    html = """<!doctype html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Document</title>
        <style>
        @media screen {
            /* comment */
        }
        </style>
    </head>
    <body></body>
    </html>"""

    p = Premailer(html, disable_validation=True)
    result_html = p.transform()
    print result_html

########NEW FILE########
__FILENAME__ = __main__
import sys
import argparse

from premailer import Premailer


def main(args):
    """Command-line tool to transform html style to inline css

    Usage::

        $ echo '<style>h1 { color:red; }</style><h1>Title</h1>' | python -m premailer
        <h1 style="color:red"></h1>
        $ cat newsletter.html | python -m premailer
    """

    parser = argparse.ArgumentParser(usage='python -m premailer [options]')

    parser.add_argument(
        "-f", "--file", nargs='?', type=argparse.FileType('r'),
        help="Specifies the input file.  The default is stdin.",
        default=sys.stdin, dest="infile"
    )

    parser.add_argument(
        "-o", "--output", nargs='?', type=argparse.FileType('w'),
        help="Specifies the output file.  The default is stdout.",
        default=sys.stdout, dest="outfile"
    )

    parser.add_argument(
        "--base-url", default=None, type=str, dest="base_url"
    )

    parser.add_argument(
        "--remove-internal-links", default=True,
        help="Remove links that start with a '#' like anchors.",
        dest="preserve_internal_links"
    )

    parser.add_argument(
        "--exclude-pseudoclasses", default=False,
        help="Pseudo classes like p:last-child', p:first-child, etc",
        action="store_true", dest="exclude_pseudoclasses"
    )

    parser.add_argument(
        "--preserve-style-tags", default=False,
        help="Do not delete <style></style> tags from the html document.",
        action="store_false", dest="keep_style_tags"
    )

    parser.add_argument(
        "--remove-star-selectors", default=True,
        help="All wildcard selectors like '* {color: black}' will be removed.",
        action="store_false", dest="include_star_selectors"
    )

    parser.add_argument(
        "--remove-classes", default=False,
        help="Remove all class attributes from all elements",
        action="store_true", dest="remove_classes"
    )

    parser.add_argument("--strip-important", default=False,
                        help="Remove '!important' for all css declarations.",
                        action="store_true", dest="strip_important")

    parser.add_argument(
        "--method", default="html", dest="method",
        help="The type of html to output. 'html' for HTML, 'xml' for XHTML."
    )

    parser.add_argument(
        "--base-path", default=None, dest="base_path",
        help="The base path for all external stylsheets."
    )

    parser.add_argument(
        "--external-style", action="append", dest="external_styles",
        help="The path to an external stylesheet to be loaded."
    )
    parser.add_argument(
        "--disable-basic-attributes", dest="disable_basic_attributes",
        help="Disable provided basic attributes (comma separated)", default=[]
    )

    parser.add_argument(
        "--disable-validation", default=False,
        action="store_true", dest="disable_validation",
        help="Disable CSSParser validation of attributes and values",
    )

    options = parser.parse_args(args)

    if options.disable_basic_attributes:
        options.disable_basic_attributes = options.disable_basic_attributes.split()

    p = Premailer(
        html=options.infile.read().decode('utf-8'),
        base_url=options.base_url,
        preserve_internal_links=options.preserve_internal_links,
        exclude_pseudoclasses=options.exclude_pseudoclasses,
        keep_style_tags=options.keep_style_tags,
        include_star_selectors=options.include_star_selectors,
        remove_classes=options.remove_classes,
        strip_important=options.strip_important,
        external_styles=options.external_styles,
        method=options.method,
        base_path=options.base_path,
        disable_basic_attributes=options.disable_basic_attributes,
        disable_validation=options.disable_validation
    )
    options.outfile.write(p.transform())
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

########NEW FILE########
