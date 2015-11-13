__FILENAME__ = authoring
# coding: utf-8

__author__ = 'Alex Musayev'
__email__ = 'alex.musayev@gmail.com'
__copyright__ = "Copyright 2012, %s <http://alex.musayev.com>" % __author__
__license__ = 'GNU GPL 3'
__status__ = 'Development'
__url__ = 'http://github.com/dreikanter/wp2md'

########NEW FILE########
__FILENAME__ = html2text
#!/usr/bin/env python
"""html2text: Turn HTML into equivalent Markdown-structured text."""
__version__ = "3.200.3"
__author__ = "Aaron Swartz (me@aaronsw.com)"
__copyright__ = "(C) 2004-2008 Aaron Swartz. GNU GPL 3."
__contributors__ = ["Martin 'Joey' Schulze", "Ricardo Reyes", "Kevin Jay North"]

# TODO:
#   Support decoded entities with unifiable.

try:
    True
except NameError:
    setattr(__builtins__, 'True', 1)
    setattr(__builtins__, 'False', 0)

def has_key(x, y):
    if hasattr(x, 'has_key'): return x.has_key(y)
    else: return y in x

try:
    import htmlentitydefs
    import urlparse
    import HTMLParser
except ImportError: #Python3
    import html.entities as htmlentitydefs
    import urllib.parse as urlparse
    import html.parser as HTMLParser
try: #Python3
    import urllib.request as urllib
except:
    import urllib
import optparse, re, sys, codecs, types

try: from textwrap import wrap
except: pass

import sys

PY2 = sys.version_info[0] == 2

strtype = unicode if PY2 else str

# Use Unicode characters instead of their ascii psuedo-replacements
UNICODE_SNOB = 0

# Escape all special characters.  Output is less readable, but avoids corner case formatting issues.
ESCAPE_SNOB = 0

# Put the links after each paragraph instead of at the end.
LINKS_EACH_PARAGRAPH = 0

# Wrap long lines at position. 0 for no wrapping. (Requires Python 2.3.)
BODY_WIDTH = 78

# Don't show internal links (href="#local-anchor") -- corresponding link targets
# won't be visible in the plain text file anyway.
SKIP_INTERNAL_LINKS = True

# Use inline, rather than reference, formatting for images and links
INLINE_LINKS = True

# Number of pixels Google indents nested lists
GOOGLE_LIST_INDENT = 36

IGNORE_ANCHORS = False
IGNORE_IMAGES = False
IGNORE_EMPHASIS = False

### Entity Nonsense ###

def name2cp(k):
    if k == 'apos': return ord("'")
    if hasattr(htmlentitydefs, "name2codepoint"): # requires Python 2.3
        return htmlentitydefs.name2codepoint[k]
    else:
        k = htmlentitydefs.entitydefs[k]
        if k.startswith("&#") and k.endswith(";"): return int(k[2:-1]) # not in latin-1
        return ord(codecs.latin_1_decode(k)[0])

unifiable = {'rsquo':"'", 'lsquo':"'", 'rdquo':'"', 'ldquo':'"',
'copy':'(C)', 'mdash':'--', 'nbsp':' ', 'rarr':'->', 'larr':'<-', 'middot':'*',
'ndash':'-', 'oelig':'oe', 'aelig':'ae',
'agrave':'a', 'aacute':'a', 'acirc':'a', 'atilde':'a', 'auml':'a', 'aring':'a',
'egrave':'e', 'eacute':'e', 'ecirc':'e', 'euml':'e',
'igrave':'i', 'iacute':'i', 'icirc':'i', 'iuml':'i',
'ograve':'o', 'oacute':'o', 'ocirc':'o', 'otilde':'o', 'ouml':'o',
'ugrave':'u', 'uacute':'u', 'ucirc':'u', 'uuml':'u',
'lrm':'', 'rlm':''}

unifiable_n = {}

for k in unifiable.keys():
    unifiable_n[name2cp(k)] = unifiable[k]

### End Entity Nonsense ###

def onlywhite(line):
    """Return true if the line does only consist of whitespace characters."""
    for c in line:
        if c is not ' ' and c is not '  ':
            return c is ' '
    return line

def hn(tag):
    if tag[0] == 'h' and len(tag) == 2:
        try:
            n = int(tag[1])
            if n in range(1, 10): return n
        except ValueError: return 0

def dumb_property_dict(style):
    """returns a hash of css attributes"""
    return dict([(x.strip(), y.strip()) for x, y in [z.split(':', 1) for z in style.split(';') if ':' in z]]);

def dumb_css_parser(data):
    """returns a hash of css selectors, each of which contains a hash of css attributes"""
    # remove @import sentences
    data += ';'
    importIndex = data.find('@import')
    while importIndex != -1:
        data = data[0:importIndex] + data[data.find(';', importIndex) + 1:]
        importIndex = data.find('@import')

    # parse the css. reverted from dictionary compehension in order to support older pythons
    elements =  [x.split('{') for x in data.split('}') if '{' in x.strip()]
    try:
        elements = dict([(a.strip(), dumb_property_dict(b)) for a, b in elements])
    except ValueError:
        elements = {} # not that important

    return elements

def element_style(attrs, style_def, parent_style):
    """returns a hash of the 'final' style attributes of the element"""
    style = parent_style.copy()
    if 'class' in attrs:
        for css_class in attrs['class'].split():
            css_style = style_def['.' + css_class]
            style.update(css_style)
    if 'style' in attrs:
        immediate_style = dumb_property_dict(attrs['style'])
        style.update(immediate_style)
    return style

def google_list_style(style):
    """finds out whether this is an ordered or unordered list"""
    if 'list-style-type' in style:
        list_style = style['list-style-type']
        if list_style in ['disc', 'circle', 'square', 'none']:
            return 'ul'
    return 'ol'

def google_has_height(style):
    """check if the style of the element has the 'height' attribute explicitly defined"""
    if 'height' in style:
        return True
    return False

def google_text_emphasis(style):
    """return a list of all emphasis modifiers of the element"""
    emphasis = []
    if 'text-decoration' in style:
        emphasis.append(style['text-decoration'])
    if 'font-style' in style:
        emphasis.append(style['font-style'])
    if 'font-weight' in style:
        emphasis.append(style['font-weight'])
    return emphasis

def google_fixed_width_font(style):
    """check if the css of the current element defines a fixed width font"""
    font_family = ''
    if 'font-family' in style:
        font_family = style['font-family']
    if 'Courier New' == font_family or 'Consolas' == font_family:
        return True
    return False

def list_numbering_start(attrs):
    """extract numbering from list element attributes"""
    if 'start' in attrs:
        return int(attrs['start']) - 1
    else:
        return 0

class HTML2Text(HTMLParser.HTMLParser):
    def __init__(self, out=None, baseurl=''):
        HTMLParser.HTMLParser.__init__(self)

        # Config options
        self.unicode_snob = UNICODE_SNOB
        self.escape_snob = ESCAPE_SNOB
        self.links_each_paragraph = LINKS_EACH_PARAGRAPH
        self.body_width = BODY_WIDTH
        self.skip_internal_links = SKIP_INTERNAL_LINKS
        self.inline_links = INLINE_LINKS
        self.google_list_indent = GOOGLE_LIST_INDENT
        self.ignore_links = IGNORE_ANCHORS
        self.ignore_images = IGNORE_IMAGES
        self.ignore_emphasis = IGNORE_EMPHASIS
        self.google_doc = False
        self.ul_item_mark = '*'
        self.emphasis_mark = '_'
        self.strong_mark = '**'

        if out is None:
            self.out = self.outtextf
        else:
            self.out = out

        self.outtextlist = []  # empty list to store output characters before they are "joined"

        try:
            self.outtext = unicode()
        except NameError:  # Python3
            self.outtext = str()

        self.quiet = 0
        self.p_p = 0  # number of newline character to print before next output
        self.outcount = 0
        self.start = 1
        self.space = 0
        self.a = []
        self.astack = []
        self.maybe_automatic_link = None
        self.absolute_url_matcher = re.compile(r'^[a-zA-Z+]+://')
        self.acount = 0
        self.list = []
        self.blockquote = 0
        self.pre = 0
        self.startpre = 0
        self.code = False
        self.br_toggle = ''
        self.lastWasNL = 0
        self.lastWasList = False
        self.style = 0
        self.style_def = {}
        self.tag_stack = []
        self.emphasis = 0
        self.drop_white_space = 0
        self.inheader = False
        self.abbr_title = None  # current abbreviation definition
        self.abbr_data = None  # last inner HTML (for abbr being defined)
        self.abbr_list = {}  # stack of abbreviations to write later
        self.baseurl = baseurl

        try: del unifiable_n[name2cp('nbsp')]
        except KeyError: pass
        unifiable['nbsp'] = '&nbsp_place_holder;'


    def feed(self, data):
        data = data.replace("</' + 'script>", "</ignore>")
        HTMLParser.HTMLParser.feed(self, data)

    def handle(self, data):
        self.feed(data)
        self.feed("")
        return self.optwrap(self.close())

    def outtextf(self, s):
        self.outtextlist.append(s)
        if s: self.lastWasNL = s[-1] == '\n'

    def close(self):
        HTMLParser.HTMLParser.close(self)

        self.pbr()
        self.o('', 0, 'end')

        self.outtext = self.outtext.join(self.outtextlist)
        if self.unicode_snob:
            try:
                nbsp = unichr(name2cp('nbsp'))
            except:
                nbsp = chr(name2cp('nbsp'))
        else:
            nbsp = strtype(' ')
        self.outtext = self.outtext.replace(strtype('&nbsp_place_holder;'), nbsp)

        return self.outtext

    def handle_charref(self, c):
        self.o(self.charref(c), 1)

    def handle_entityref(self, c):
        self.o(self.entityref(c), 1)

    def handle_starttag(self, tag, attrs):
        self.handle_tag(tag, attrs, 1)

    def handle_endtag(self, tag):
        self.handle_tag(tag, None, 0)

    def previousIndex(self, attrs):
        """ returns the index of certain set of attributes (of a link) in the
            self.a list

            If the set of attributes is not found, returns None
        """
        if not has_key(attrs, 'href'): return None

        i = -1
        for a in self.a:
            i += 1
            match = 0

            if has_key(a, 'href') and a['href'] == attrs['href']:
                if has_key(a, 'title') or has_key(attrs, 'title'):
                        if (has_key(a, 'title') and has_key(attrs, 'title') and
                            a['title'] == attrs['title']):
                            match = True
                else:
                    match = True

            if match: return i

    def drop_last(self, nLetters):
        if not self.quiet:
            self.outtext = self.outtext[:-nLetters]

    def handle_emphasis(self, start, tag_style, parent_style):
        """handles various text emphases"""
        tag_emphasis = google_text_emphasis(tag_style)
        parent_emphasis = google_text_emphasis(parent_style)

        # handle Google's text emphasis
        strikethrough =  'line-through' in tag_emphasis and self.hide_strikethrough
        bold = 'bold' in tag_emphasis and not 'bold' in parent_emphasis
        italic = 'italic' in tag_emphasis and not 'italic' in parent_emphasis
        fixed = google_fixed_width_font(tag_style) and not \
                google_fixed_width_font(parent_style) and not self.pre

        if start:
            # crossed-out text must be handled before other attributes
            # in order not to output qualifiers unnecessarily
            if bold or italic or fixed:
                self.emphasis += 1
            if strikethrough:
                self.quiet += 1
            if italic:
                self.o(self.emphasis_mark)
                self.drop_white_space += 1
            if bold:
                self.o(self.strong_mark)
                self.drop_white_space += 1
            if fixed:
                self.o('`')
                self.drop_white_space += 1
                self.code = True
        else:
            if bold or italic or fixed:
                # there must not be whitespace before closing emphasis mark
                self.emphasis -= 1
                self.space = 0
                self.outtext = self.outtext.rstrip()
            if fixed:
                if self.drop_white_space:
                    # empty emphasis, drop it
                    self.drop_last(1)
                    self.drop_white_space -= 1
                else:
                    self.o('`')
                self.code = False
            if bold:
                if self.drop_white_space:
                    # empty emphasis, drop it
                    self.drop_last(2)
                    self.drop_white_space -= 1
                else:
                    self.o(self.strong_mark)
            if italic:
                if self.drop_white_space:
                    # empty emphasis, drop it
                    self.drop_last(1)
                    self.drop_white_space -= 1
                else:
                    self.o(self.emphasis_mark)
            # space is only allowed after *all* emphasis marks
            if (bold or italic) and not self.emphasis:
                    self.o(" ")
            if strikethrough:
                self.quiet -= 1

    def handle_tag(self, tag, attrs, start):
        #attrs = fixattrs(attrs)
        if attrs is None:
            attrs = {}
        else:
            attrs = dict(attrs)

        if self.google_doc:
            # the attrs parameter is empty for a closing tag. in addition, we
            # need the attributes of the parent nodes in order to get a
            # complete style description for the current element. we assume
            # that google docs export well formed html.
            parent_style = {}
            if start:
                if self.tag_stack:
                  parent_style = self.tag_stack[-1][2]
                tag_style = element_style(attrs, self.style_def, parent_style)
                self.tag_stack.append((tag, attrs, tag_style))
            else:
                dummy, attrs, tag_style = self.tag_stack.pop()
                if self.tag_stack:
                    parent_style = self.tag_stack[-1][2]

        if hn(tag):
            self.p()
            if start:
                self.inheader = True
                self.o(hn(tag)*"#" + ' ')
            else:
                self.inheader = False
                return # prevent redundant emphasis marks on headers

        if tag in ['p', 'div']:
            if self.google_doc:
                if start and google_has_height(tag_style):
                    self.p()
                else:
                    self.soft_br()
            else:
                self.p()

        if tag == "br" and start: self.o("  \n")

        if tag == "hr" and start:
            self.p()
            self.o("* * *")
            self.p()

        if tag in ["head", "style", 'script']:
            if start: self.quiet += 1
            else: self.quiet -= 1

        if tag == "style":
            if start: self.style += 1
            else: self.style -= 1

        if tag in ["body"]:
            self.quiet = 0 # sites like 9rules.com never close <head>

        if tag == "blockquote":
            if start:
                self.p(); self.o('> ', 0, 1); self.start = 1
                self.blockquote += 1
            else:
                self.blockquote -= 1
                self.p()

        if tag in ['em', 'i', 'u'] and not self.ignore_emphasis: self.o(self.emphasis_mark)
        if tag in ['strong', 'b'] and not self.ignore_emphasis: self.o(self.strong_mark)
        if tag in ['del', 'strike', 's']:
            if start:
                self.o("<"+tag+">")
            else:
                self.o("</"+tag+">")

        if self.google_doc:
            if not self.inheader:
                # handle some font attributes, but leave headers clean
                self.handle_emphasis(start, tag_style, parent_style)

        if tag in ["code", "tt"] and not self.pre: self.o('`') #TODO: `` `this` ``
        if tag == "abbr":
            if start:
                self.abbr_title = None
                self.abbr_data = ''
                if has_key(attrs, 'title'):
                    self.abbr_title = attrs['title']
            else:
                if self.abbr_title != None:
                    self.abbr_list[self.abbr_data] = self.abbr_title
                    self.abbr_title = None
                self.abbr_data = ''

        if tag == "a" and not self.ignore_links:
            if start:
                if has_key(attrs, 'href') and not (self.skip_internal_links and attrs['href'].startswith('#')):
                    self.astack.append(attrs)
                    self.maybe_automatic_link = attrs['href']
                else:
                    self.astack.append(None)
            else:
                if self.astack:
                    a = self.astack.pop()
                    if self.maybe_automatic_link:
                        self.maybe_automatic_link = None
                    elif a:
                        if self.inline_links:
                            self.o("](" + escape_md(a['href']) + ")")
                        else:
                            i = self.previousIndex(a)
                            if i is not None:
                                a = self.a[i]
                            else:
                                self.acount += 1
                                a['count'] = self.acount
                                a['outcount'] = self.outcount
                                self.a.append(a)
                            self.o("][" + str(a['count']) + "]")

        if tag == "img" and start and not self.ignore_images:
            if has_key(attrs, 'src'):
                attrs['href'] = attrs['src']
                alt = attrs.get('alt', '')
                self.o("![" + escape_md(alt) + "]")

                if self.inline_links:
                    self.o("(" + escape_md(attrs['href']) + ")")
                else:
                    i = self.previousIndex(attrs)
                    if i is not None:
                        attrs = self.a[i]
                    else:
                        self.acount += 1
                        attrs['count'] = self.acount
                        attrs['outcount'] = self.outcount
                        self.a.append(attrs)
                    self.o("[" + str(attrs['count']) + "]")

        if tag == 'dl' and start: self.p()
        if tag == 'dt' and not start: self.pbr()
        if tag == 'dd' and start: self.o('    ')
        if tag == 'dd' and not start: self.pbr()

        if tag in ["ol", "ul"]:
            # Google Docs create sub lists as top level lists
            if (not self.list) and (not self.lastWasList):
                self.p()
            if start:
                if self.google_doc:
                    list_style = google_list_style(tag_style)
                else:
                    list_style = tag
                numbering_start = list_numbering_start(attrs)
                self.list.append({'name':list_style, 'num':numbering_start})
            else:
                if self.list: self.list.pop()
            self.lastWasList = True
        else:
            self.lastWasList = False

        if tag == 'li':
            self.pbr()
            if start:
                if self.list: li = self.list[-1]
                else: li = {'name':'ul', 'num':0}
                if self.google_doc:
                    nest_count = self.google_nest_count(tag_style)
                else:
                    nest_count = len(self.list)
                self.o("  " * nest_count) #TODO: line up <ol><li>s > 9 correctly.
                if li['name'] == "ul": self.o(self.ul_item_mark + " ")
                elif li['name'] == "ol":
                    li['num'] += 1
                    self.o(str(li['num'])+". ")
                self.start = 1

        if tag in ["table", "tr"] and start: self.p()
        if tag == 'td': self.pbr()

        if tag == "pre":
            if start:
                self.startpre = 1
                self.pre = 1
            else:
                self.pre = 0
            self.p()

    def pbr(self):
        if self.p_p == 0:
            self.p_p = 1

    def p(self):
        self.p_p = 2

    def soft_br(self):
        self.pbr()
        self.br_toggle = '  '

    def o(self, data, puredata=0, force=0):
        if self.abbr_data is not None:
            self.abbr_data += data

        if not self.quiet:
            if self.google_doc:
                # prevent white space immediately after 'begin emphasis' marks ('**' and '_')
                lstripped_data = data.lstrip()
                if self.drop_white_space and not (self.pre or self.code):
                    data = lstripped_data
                if lstripped_data != '':
                    self.drop_white_space = 0

            if puredata and not self.pre:
                data = re.sub('\s+', ' ', data)
                if data and data[0] == ' ':
                    self.space = 1
                    data = data[1:]
            if not data and not force: return

            if self.startpre:
                #self.out(" :") #TODO: not output when already one there
                if not data.startswith("\n"):  # <pre>stuff...
                    data = "\n" + data

            bq = (">" * self.blockquote)
            if not (force and data and data[0] == ">") and self.blockquote: bq += " "

            if self.pre:
                if not self.list:
                    bq += "    "
                #else: list content is already partially indented
                for i in xrange(len(self.list)):
                    bq += "    "
                data = data.replace("\n", "\n"+bq)

            if self.startpre:
                self.startpre = 0
                if self.list:
                    data = data.lstrip("\n") # use existing initial indentation

            if self.start:
                self.space = 0
                self.p_p = 0
                self.start = 0

            if force == 'end':
                # It's the end.
                self.p_p = 0
                self.out("\n")
                self.space = 0

            if self.p_p:
                self.out((self.br_toggle+'\n'+bq)*self.p_p)
                self.space = 0
                self.br_toggle = ''

            if self.space:
                if not self.lastWasNL: self.out(' ')
                self.space = 0

            if self.a and ((self.p_p == 2 and self.links_each_paragraph) or force == "end"):
                if force == "end": self.out("\n")

                newa = []
                for link in self.a:
                    if self.outcount > link['outcount']:
                        self.out("   ["+ str(link['count']) +"]: " + urlparse.urljoin(self.baseurl, link['href']))
                        if has_key(link, 'title'): self.out(" ("+link['title']+")")
                        self.out("\n")
                    else:
                        newa.append(link)

                if self.a != newa: self.out("\n") # Don't need an extra line when nothing was done.

                self.a = newa

            if self.abbr_list and force == "end":
                for abbr, definition in self.abbr_list.items():
                    self.out("  *[" + abbr + "]: " + definition + "\n")

            self.p_p = 0
            self.out(data)
            self.outcount += 1

    def handle_data(self, data):
        if r'\/script>' in data: self.quiet -= 1

        if self.style:
            self.style_def.update(dumb_css_parser(data))

        if not self.maybe_automatic_link is None:
            href = self.maybe_automatic_link
            if href == data and self.absolute_url_matcher.match(href):
                self.o("<" + data + ">")
                return
            else:
                self.o("[")
                self.maybe_automatic_link = None

        if not self.code and not self.pre:
            data = escape_md_section(data, snob=self.escape_snob)
        self.o(data, 1)

    def unknown_decl(self, data): pass

    def charref(self, name):
        if name[0] in ['x','X']:
            c = int(name[1:], 16)
        else:
            c = int(name)

        if not self.unicode_snob and c in unifiable_n.keys():
            return unifiable_n[c]
        else:
            try:
                return unichr(c)
            except NameError: #Python3
                return chr(c)

    def entityref(self, c):
        if not self.unicode_snob and c in unifiable.keys():
            return unifiable[c]
        else:
            try: name2cp(c)
            except KeyError: return "&" + c + ';'
            else:
                try:
                    return unichr(name2cp(c))
                except NameError: #Python3
                    return chr(name2cp(c))

    def replaceEntities(self, s):
        s = s.group(1)
        if s[0] == "#":
            return self.charref(s[1:])
        else: return self.entityref(s)

    r_unescape = re.compile(r"&(#?[xX]?(?:[0-9a-fA-F]+|\w{1,8}));")
    def unescape(self, s):
        return self.r_unescape.sub(self.replaceEntities, s)

    def google_nest_count(self, style):
        """calculate the nesting count of google doc lists"""
        nest_count = 0
        if 'margin-left' in style:
            nest_count = int(style['margin-left'][:-2]) / self.google_list_indent
        return nest_count


    def optwrap(self, text):
        """Wrap all paragraphs in the provided text."""
        if not self.body_width:
            return text

        assert wrap, "Requires Python 2.3."
        result = ''
        newlines = 0
        for para in text.split("\n"):
            if len(para) > 0:
                if not skipwrap(para):
                    result += "\n".join(wrap(para, self.body_width))
                    if para.endswith('  '):
                        result += "  \n"
                        newlines = 1
                    else:
                        result += "\n\n"
                        newlines = 2
                else:
                    if not onlywhite(para):
                        result += para + "\n"
                        newlines = 1
            else:
                if newlines < 2:
                    result += "\n"
                    newlines += 1
        return result

ordered_list_matcher = re.compile(r'\d+\.\s')
unordered_list_matcher = re.compile(r'[-\*\+]\s')
md_chars_matcher = re.compile(r"([\\\[\]\(\)])")
md_chars_matcher_all = re.compile(r"([`\*_{}\[\]\(\)#!])")
md_dot_matcher = re.compile(r"""
    ^             # start of line
    (\s*\d+)      # optional whitespace and a number
    (\.)          # dot
    (?=\s)        # lookahead assert whitespace
    """, re.MULTILINE | re.VERBOSE)
md_plus_matcher = re.compile(r"""
    ^
    (\s*)
    (\+)
    (?=\s)
    """, flags=re.MULTILINE | re.VERBOSE)
md_dash_matcher = re.compile(r"""
    ^
    (\s*)
    (-)
    (?=\s|\-)     # followed by whitespace (bullet list, or spaced out hr)
                  # or another dash (header or hr)
    """, flags=re.MULTILINE | re.VERBOSE)
slash_chars = r'\`*_{}[]()#+-.!'
md_backslash_matcher = re.compile(r'''
    (\\)          # match one slash
    (?=[%s])      # followed by a char that requires escaping
    ''' % re.escape(slash_chars),
    flags=re.VERBOSE)

def skipwrap(para):
    # If the text begins with four spaces or one tab, it's a code block; don't wrap
    if para[0:4] == '    ' or para[0] == '\t':
        return True
    # If the text begins with only two "--", possibly preceded by whitespace, that's
    # an emdash; so wrap.
    stripped = para.lstrip()
    if stripped[0:2] == "--" and len(stripped) > 2 and stripped[2] != "-":
        return False
    # I'm not sure what this is for; I thought it was to detect lists, but there's
    # a <br>-inside-<span> case in one of the tests that also depends upon it.
    if stripped[0:1] == '-' or stripped[0:1] == '*':
        return True
    # If the text begins with a single -, *, or +, followed by a space, or an integer,
    # followed by a ., followed by a space (in either case optionally preceeded by
    # whitespace), it's a list; don't wrap.
    if ordered_list_matcher.match(stripped) or unordered_list_matcher.match(stripped):
        return True
    return False

def wrapwrite(text):
    text = text.encode('utf-8')
    try: #Python3
        sys.stdout.buffer.write(text)
    except AttributeError:
        sys.stdout.write(text)

def html2text(html, baseurl=''):
    h = HTML2Text(baseurl=baseurl)
    return h.handle(html)

def unescape(s, unicode_snob=False):
    h = HTML2Text()
    h.unicode_snob = unicode_snob
    return h.unescape(s)

def escape_md(text):
    """Escapes markdown-sensitive characters within other markdown constructs."""
    return md_chars_matcher.sub(r"\\\1", text)

def escape_md_section(text, snob=False):
    """Escapes markdown-sensitive characters across whole document sections."""
    text = md_backslash_matcher.sub(r"\\\1", text)
    if snob:
        text = md_chars_matcher_all.sub(r"\\\1", text)
    text = md_dot_matcher.sub(r"\1\\\2", text)
    text = md_plus_matcher.sub(r"\1\\\2", text)
    text = md_dash_matcher.sub(r"\1\\\2", text)
    return text


def main():
    baseurl = ''

    p = optparse.OptionParser('%prog [(filename|url) [encoding]]',
                              version='%prog ' + __version__)
    p.add_option("--ignore-emphasis", dest="ignore_emphasis", action="store_true",
        default=IGNORE_EMPHASIS, help="don't include any formatting for emphasis")
    p.add_option("--ignore-links", dest="ignore_links", action="store_true",
        default=IGNORE_ANCHORS, help="don't include any formatting for links")
    p.add_option("--ignore-images", dest="ignore_images", action="store_true",
        default=IGNORE_IMAGES, help="don't include any formatting for images")
    p.add_option("-g", "--google-doc", action="store_true", dest="google_doc",
        default=False, help="convert an html-exported Google Document")
    p.add_option("-d", "--dash-unordered-list", action="store_true", dest="ul_style_dash",
        default=False, help="use a dash rather than a star for unordered list items")
    p.add_option("-e", "--asterisk-emphasis", action="store_true", dest="em_style_asterisk",
        default=False, help="use an asterisk rather than an underscore for emphasized text")
    p.add_option("-b", "--body-width", dest="body_width", action="store", type="int",
        default=BODY_WIDTH, help="number of characters per output line, 0 for no wrap")
    p.add_option("-i", "--google-list-indent", dest="list_indent", action="store", type="int",
        default=GOOGLE_LIST_INDENT, help="number of pixels Google indents nested lists")
    p.add_option("-s", "--hide-strikethrough", action="store_true", dest="hide_strikethrough",
        default=False, help="hide strike-through text. only relevant when -g is specified as well")
    p.add_option("--escape-all", action="store_true", dest="escape_snob",
        default=False, help="Escape all special characters.  Output is less readable, but avoids corner case formatting issues.")
    (options, args) = p.parse_args()

    # process input
    encoding = "utf-8"
    if len(args) > 0:
        file_ = args[0]
        if len(args) == 2:
            encoding = args[1]
        if len(args) > 2:
            p.error('Too many arguments')

        if file_.startswith('http://') or file_.startswith('https://'):
            baseurl = file_
            j = urllib.urlopen(baseurl)
            data = j.read()
            if encoding is None:
                try:
                    from feedparser import _getCharacterEncoding as enc
                except ImportError:
                    enc = lambda x, y: ('utf-8', 1)
                encoding = enc(j.headers, data)[0]
                if encoding == 'us-ascii':
                    encoding = 'utf-8'
        else:
            data = open(file_, 'rb').read()
            if encoding is None:
                try:
                    from chardet import detect
                except ImportError:
                    detect = lambda x: {'encoding': 'utf-8'}
                encoding = detect(data)['encoding']
    else:
        data = sys.stdin.read()

    if PY2:
        data = data.decode(encoding)

    h = HTML2Text(baseurl=baseurl)
    # handle options
    if options.ul_style_dash: h.ul_item_mark = '-'
    if options.em_style_asterisk:
        h.emphasis_mark = '*'
        h.strong_mark = '__'

    h.body_width = options.body_width
    h.list_indent = options.list_indent
    h.ignore_emphasis = options.ignore_emphasis
    h.ignore_links = options.ignore_links
    h.ignore_images = options.ignore_images
    h.google_doc = options.google_doc
    h.hide_strikethrough = options.hide_strikethrough
    h.escape_snob = options.escape_snob

    wrapwrite(h.handle(data))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = version
# coding: utf-8

__version_info__ = (0, 8, 1)
__version__ = '.'.join(map(str, __version_info__))


def get_version():
    return __version__

########NEW FILE########
__FILENAME__ = wp2md
#!/usr/bin/env python
"""A script to convert Wordpress XML dumps to plain text/markdown files."""

import argparse
import codecs
import datetime
import logging
import markdown
import os.path
import re
import sys
import time
import traceback
from xml.etree.ElementTree import XMLParser
from . import html2text

PY2 = sys.version_info[0] == 2

str_t = unicode if PY2 else str

# XML elements to save (starred ones are additional fields
# generated during export data processing)
WHAT2SAVE = {
    'channel': [
        'title',
        'description',
        'author_display_name',
        'author_login',
        'author_email',
        'base_site_url',
        'base_blog_url',
        'export_date',          # Generated: data export timestamp
        'content',              # Generated: items list
        # 'link',
        # 'language',
    ],
    'item': [
        'title',
        'link',
        'creator',
        'description',
        'post_id',
        'post_date',
        'post_date_gmt',
        'comment_status',
        'post_name',
        'status',
        'post_type',
        'excerpt',
        'content',              # Generated: item content
        'comments',             # Generated: comments lis
        # 'guid',
        # 'is_sticky',
        # 'menu_order',
        # 'ping_status',
        # 'post_parent',
        # 'post_password',
    ],
    'comment': [
        'comment_id',
        'comment_author',
        'comment_author_email',
        'comment_author_url',
        'comment_author_IP',
        'comment_date',
        'comment_date_gmt',
        'comment_content',
        'comment_approved',
        'comment_type',
        # 'comment_parent',
        # 'comment_user_id',
    ],
}

# Wordpress RSS items to public-static page header fields mapping
# (undefined names will remain unchanged)
FIELD_MAP = {
    'creator': 'author',
    'post_date': 'created',
    'post_date_gmt': 'created_gmt',
}

DEFAULT_MAX_NAME_LEN = 50
UNTITLED = 'untitled'
MD_URL_RE = None

log = logging.getLogger(__name__)
conf = {}
stats = {
    'page': 0,
    'post': 0,
    'comment': 0,
}


# Configuration and logging

def init():
    global conf
    args = parse_args()
    init_logging(args.l, args.v)
    conf = {
        'source_file': args.source,
        'dump_path': args.d,
        'page_path': args.pg,
        'post_path': args.ps,
        'draft_path': args.dr,
        'verbose': args.v,
        'parse_date_fmt': args.u,
        'post_date_fmt': args.o,
        'date_fmt': args.f,
        'page_date_fmt': args.ef,
        'file_date_fmt': args.p,
        'log_file': args.l,
        'md_input': args.m,
        'max_name_len': args.n,
        'ref_links': args.r,
        'fix_urls': args.url,
        'base_url': args.b,
    }

    try:
        value = int(conf['max_name_len'])
        if value < 0 or value > 100:
            raise ValueError()
        conf['max_name_len'] = value
    except:
        log.warn('Bad post name length limitation value. Using default.')
        conf['max_name_len'] = DEFAULT_MAX_NAME_LEN


def init_logging(log_file, verbose):
    try:
        global log
        log.setLevel(logging.DEBUG)
        log_level = logging.DEBUG if verbose else logging.INFO

        channel = logging.StreamHandler()
        channel.setLevel(log_level)
        fmt = '%(message)s'
        channel.setFormatter(logging.Formatter(fmt))
        log.addHandler(channel)

        if log_file:
            channel = logging.FileHandler(log_file)
            channel.setLevel(logging.DEBUG)
            fmt = '%(asctime)s %(levelname)s: %(message)s'
            channel.setFormatter(logging.Formatter(fmt, '%H:%M:%S'))
            log.addHandler(channel)

    except Exception as e:
        log.debug(traceback.format_exc())
        raise Exception(getxm('Logging initialization failed', e))


def parse_args():
    desc = __doc__.split('\n\n')[0]
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        '-v',
        action='store_true',
        default=False,
        help='verbose logging')
    parser.add_argument(
        '-l',
        action='store',
        metavar='FILE',
        default=None,
        help='log to file')
    parser.add_argument(
        '-d',
        action='store',
        metavar='PATH',
        default='{year}{month}{day}_{source}',
        help='destination path for generated files')
    parser.add_argument(
        '-u',
        action='store',
        metavar='FMT',
        default="%a, %d %b %Y %H:%M:%S +0000",
        help='<pubDate> date/time parsing format')
    parser.add_argument(
        '-o',
        action='store',
        metavar='FMT',
        default="%Y %H:%M:%S",
        help='<wp:post_date> and <wp:post_date_gmt> parsing format')
    parser.add_argument(
        '-f',
        action='store',
        metavar='FMT',
        default="%Y-%m-%d %H:%M:%S",
        help='date/time fields parsing format for input data')
    parser.add_argument(
        '-ef',
        action='store',
        metavar='FMT',
        default="%Y/%m/%d %H:%M:%S",
        help='date/time fields format for generated pages')
    parser.add_argument(
        '-p',
        action='store',
        metavar='FMT',
        default="%Y%m%d",
        help='date prefix format for generated files')
    parser.add_argument(
        '-m',
        action='store_true',
        default=False,
        help='preprocess content with Markdown (helpful for MD input)')
    parser.add_argument(
        '-n',
        action='store',
        metavar='LEN',
        default=DEFAULT_MAX_NAME_LEN,
        help='post name (slug) length limit for file naming')
    parser.add_argument(
        '-r',
        action='store_true',
        default=False,
        help='generate reference links instead of inline')
    parser.add_argument(
        '-ps',
        action='store',
        metavar='PATH',
        default=os.path.join("posts", "{year}{month}{day}-{name}.md"),
        help='post files path (see docs for variable names)')
    parser.add_argument(
        '-pg',
        action='store',
        metavar='PATH',
        default=os.path.join("pages", "{name}.md"),
        help='page files path')
    parser.add_argument(
        '-dr',
        action='store',
        metavar='PATH',
        default="drafts/{name}.md",
        help='draft files path')
    parser.add_argument(
        '-url',
        action='store_false',
        default=True,
        help="keep absolute URLs in hrefs and image srcs")
    parser.add_argument(
        '-b',
        action='store',
        metavar='URL',
        default=None,
        help='base URL to subtract from hrefs (default is the root)')
    parser.add_argument(
        'source',
        action='store',
        help='source XML dump exported from Wordpress')
    return parser.parse_args(sys.argv[1:])


# Helpers

def getxm(message, exception):
    """Returns annotated exception messge."""
    return ("%s: %s" % (message, str(exception))) if exception else message


def tag_name(name):
    """Removes expanded namespace from tag name."""
    result = name[name.find('}') + 1:]
    if result == 'encoded':
        if name.find('/content/') > -1:
            result = 'content'
        elif name.find('/excerpt/') > -1:
            result = 'excerpt'
    return result


def parse_date(date_str, format, default=None):
    """Parses date string according to specified format."""
    try:
        result = time.strptime(date_str, format)
    except:
        msg = "Error parsing date string '%s'. Using default value." % date_str
        log.debug(msg)
        result = default

    return result


def get_path_fmt(item_type, data):
    """Returns preconfigured export path format for specified
    RSS item type and metadata."""

    if data.get('status', None).lower() == 'draft':
        return conf['draft_path']
    is_post = item_type == 'post'
    return conf['post_path'] if is_post else conf['page_path']


def get_path(item_type, file_name=None, data=None):
    """Generates full path for the generated file using configuration
    and explicitly specified name or RSS item data. At least one argument
    should be specified. @file_name has higher priority during output
    path generation.

    Arguments:
        item_type -- 'post' or 'page'
        file_name -- explicitly defined correct file name.
        data -- preprocessed RSS item data dictionary."""

    if not file_name and type(data) is not dict:
        raise Exception('File name or RSS item data dict should be defined')

    root = conf['dump_path']
    root = root.format(date=time.strftime(conf['file_date_fmt']),
                       year=time.strftime("%Y"),
                       month=time.strftime("%m"),
                       day=time.strftime("%d"),
                       source=os.path.basename(conf['source_file']))

    if file_name:
        relpath = file_name
    else:
        name = data.get('post_name', '').strip()
        name = name or data.get('post_id', UNTITLED)
        relpath = get_path_fmt(item_type, data)
        field = FIELD_MAP.get('post_date', 'post_date')
        post_date = data[field]
        relpath = relpath.format(year=time.strftime("%Y", post_date),
                                 month=time.strftime("%m", post_date),
                                 day=time.strftime("%d", post_date),
                                 name=name,
                                 title=name)

    return uniquify(os.path.join(os.path.abspath(root), relpath))


def uniquify(file_name):
    """Inserts numeric suffix at the end of file name to make
    it's name unique in the directory."""

    suffix = 0
    result = file_name
    while True:
        if os.path.exists(result):
            suffix += 1
            result = insert_suffix(file_name, suffix)
        else:
            return result


def insert_suffix(file_name, suffix):
    """Inserts suffix to the end of file name (before extension).
    If suffix is zero (or False in boolean representation), nothing
    will be inserted.

    Usage:
        >>> insert_suffix('c:/temp/hello.txt', 2)
        c:/temp/hello-2.txt
        >>> insert_suffix('readme.txt', 0)
        readme.txt

    Intended to be used for numeric suffixes for file
    name uniquification (what a word!)."""

    if not suffix:
        return file_name
    base, ext = os.path.splitext(file_name)
    return "%s-%s%s" % (base, suffix, ext)


# Markdown processing and generation

def html2md(html):
    h2t = html2text.HTML2Text()
    h2t.unicode_snob = True
    h2t.inline_links = not conf['ref_links']
    h2t.body_width = 0
    return h2t.handle(html).strip()


def generate_toc(meta, items):
    """Generates MD-formatted index page."""
    content = meta.get('description', '') + '\n\n'
    for item in items:
        content += str_t("* {post_date}: [{title}]({link})\n").format(**item)
    return content


def generate_comments(comments):
    """Generates MD-formatted comments list from parsed data."""

    result = str_t('')
    for comment in comments:
        try:
            approved = comment['comment_approved'] == '1'
            pingback = comment.get('comment_type', '').lower() == 'pingback'
            if approved and not pingback:
                cmfmt = str_t("**[{author}](#{id} \"{timestamp}\"):** {content}\n\n")
                content = html2md(comment['comment_content'])
                result += cmfmt.format(id=comment['comment_id'],
                                       timestamp=comment['comment_date'],
                                       author=comment['comment_author'],
                                       content=content)
        except:
            # Ignore malformed data
            pass

    return result and str_t("## Comments\n\n" + result)


def fix_urls(text):
    """Removes base_url prefix from MD links and image sources."""
    global MD_URL_RE
    if MD_URL_RE is None:
        base_url = re.escape(conf['base_url'])
        MD_URL_RE = re.compile(r'\]\(%s(.*)\)' % base_url)
    return MD_URL_RE.sub(r'](\1)', text)


# Statistics

def stopwatch_set():
    """Starts stopwatch timer."""
    globals()['_stopwatch_start_time'] = datetime.datetime.now()


def stopwatch_get():
    """Returns string representation for elapsed time since last
    stopwatch_set() call."""
    delta = datetime.datetime.now() - globals().get('_stopwatch_start_time', 0)
    delta = str(delta).strip('0:')
    return ('0' + delta) if delta[0] == '.' else delta


def statplusplus(field, value=1):
    global stats
    if field in stats:
        stats[field] += value
    else:
        raise ValueError("Illegal name for stats field: " + str(field))


# Parser data handlers

def dump_channel(meta, items):
    """Dumps RSS channel metadata and items index."""
    file_name = get_path('page', 'index.md')
    log.info("Dumping index to '%s'" % file_name)
    fields = WHAT2SAVE['channel']
    meta = {field: meta.get(field, None) for field in fields}

    # Append export_date
    pub_date = meta.get('pubDate', None)
    format = conf['parse_date_fmt']
    meta['export_date'] = parse_date(pub_date, format, time.gmtime())

    # Append table of contents
    meta['content'] = generate_toc(meta, items)

    dump(file_name, meta, fields)


def dump_item(data):
    """Dumps RSS channel item."""
    if not 'post_type' in data:
        log.error('Malformed RSS item: item type is not specified.')
        return

    item_type = data['post_type']
    if item_type not in ['post', 'page', 'draft']:
        return

    fields = WHAT2SAVE['item']
    pdata = {}
    for field in fields:
        pdata[FIELD_MAP.get(field, field)] = data.get(field, '')

    # Post date
    format = conf['date_fmt']
    field = FIELD_MAP.get('post_date', 'post_date')
    value = pdata.get(field, None)
    pdata[field] = value and parse_date(value, format, None)

    # Post date GMT
    field = FIELD_MAP.get('post_date_gmt', 'post_date_gmt')
    value = pdata.get(field, None)
    pdata[field] = value and parse_date(value, format, None)

    dump_path = get_path(item_type, data=pdata)
    log.info("Dumping %s to '%s'" % (item_type, dump_path))

    fields = [FIELD_MAP.get(field, field) for field in fields]
    dump(dump_path, pdata, fields)

    statplusplus(item_type)
    if 'comments' in data:
        statplusplus('comment', len(data['comments']))


def dump(file_name, data, order):
    """Dumps a dictionary to YAML-like text file."""
    try:
        dir_path = os.path.dirname(os.path.abspath(file_name))
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)

        with codecs.open(file_name, 'w', 'utf-8') as f:
            extras = {}
            for field in filter(lambda x: x in data, [item for item in order]):
                if field in ['content', 'comments', 'excerpt']:
                    # Fields for non-standard processing
                    extras[field] = data[field]
                else:
                    if type(data[field]) == time.struct_time:
                        value = time.strftime(conf['page_date_fmt'], data[field])
                    else:
                        value = data[field] or ''
                    f.write(str_t("%s: %s\n") % (str_t(field), str_t(value)))

            if extras:
                excerpt = extras.get('excerpt', '')
                excerpt = excerpt and '<!--%s-->' % excerpt

                content = extras.get('content', '')
                if conf['md_input']:
                    # Using new MD instance works 3x faster than
                    # reusing existing one for some reason
                    md = markdown.Markdown(extensions=[])
                    content = md.convert(content)

                if conf['fix_urls']:
                    content = fix_urls(html2md(content))

                if 'title' in data:
                    content = str_t("# %s\n\n%s") % (data['title'], content)

                comments = generate_comments(extras.get('comments', []))
                extras = filter(None, [excerpt, content, comments])
                f.write('\n' + '\n\n'.join(extras))

    except Exception as e:
        log.error("Error saving data to '%s'" % (file_name))
        log.debug(e)


def store_base_url(channel):
    """Stores base URL in configuration if it's not defined explicitly."""
    if conf['fix_urls'] and not conf['base_url']:
        conf['base_url'] = channel.get('base_site_url', '')


# The Parser

class CustomParser:
    def __init__(self):
        self.section_stack = []
        self.channel = {}
        self.items = []
        self.item = None
        self.cmnt = None
        self.subj = None

    def start(self, tag, attrib):
        tag = tag_name(tag)
        if tag == 'channel':
            self.start_section('channel')

        elif tag == 'item':
            self.item = {'comments': []}
            self.start_section('item')

        elif self.item and tag == 'comment':
            self.cmnt = {}
            self.start_section('comment')

        elif self.cur_section():
            self.subj = tag

        else:
            self.subj = None

    def end(self, tag):
        tag = tag_name(tag)
        if tag == 'comment' and self.cur_section() == 'comment':
            self.end_section()
            self.item['comments'].append(self.cmnt)
            self.cmnt = None

        elif tag == 'item' and self.cur_section() == 'item':
            self.end_section()
            dump_item(self.item)
            self.store_item_info()
            self.item = None

        elif tag == 'channel':
            self.end_section()
            dump_channel(self.channel, self.items)

        elif self.cur_section():
            self.subj = None

    def data(self, data):
        if self.subj:
            if self.cur_section() == 'comment':
                self.cmnt[self.subj] = data

            elif self.cur_section() == 'item':
                self.item[self.subj] = data

            elif self.cur_section() == 'channel':
                self.channel[self.subj] = data
                if self.subj == 'base_site_url':
                    store_base_url(self.channel)
            self.subj = None

    def start_section(self, what):
        self.section_stack.append(what)

    def end_section(self):
        if len(self.section_stack):
            self.section_stack.pop()

    def cur_section(self):
        try:
            return self.section_stack[-1]
        except:
            return None

    def store_item_info(self):
        post_type = self.item.get('post_type', '').lower()
        if not post_type in ['post', 'page']:
            return

        fields = [
            'title',
            'link',
            'post_id',
            'post_date',
            'post_type',
        ]

        self.items.append({})
        for field in fields:
            self.items[-1][field] = self.item.get(field, None)


def main():
    init()
    log.info("Parsing '%s'..." % os.path.basename(conf['source_file']))

    stopwatch_set()
    target = CustomParser()
    parser = XMLParser(target=target)
    if PY2:
        text = open(conf['source_file']).read()
    else:
        text = codecs.open(conf['source_file'], encoding='utf-8').read()
    parser.feed(text)

    log.info('')
    totals = 'Total: posts: {post}; pages: {page}; comments: {comment}'
    log.info(totals.format(**stats))
    log.info('Elapsed time: %s s' % stopwatch_get())


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = __main__
import sys
from .wp2md import main

sys.exit(main())

########NEW FILE########
