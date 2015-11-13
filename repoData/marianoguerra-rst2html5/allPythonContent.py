__FILENAME__ = html
'''classes to ease the creation of html documents'''

import xml.etree.ElementTree as ET

if callable(ET.Element):
    class Element(ET._ElementInterface, object):
        pass
else:
    class Element(ET.Element):
        pass

def quote(text):
    """encode html entities"""
    text = unicode(text)
    return text.translate({
        ord('&'): u'&amp;',
        ord('<'): u'&lt;',
        ord('"'): u'&quot;',
        ord('>'): u'&gt;',
        ord('@'): u'&#64;',
        0xa0: u'&nbsp;'})

def nop(text):
    return text

def to_str(value):
    if isinstance(value, unicode):
        return value
    else:
        return str(value)

def escape_attrs(node):
    node.attrib = dict([(key.rstrip("_"), str(val))
        for (key, val) in node.attrib.iteritems()])

    for child in node:
        escape_attrs(child)

class TagBase(Element):
    "base class for all tags"

    SELF_CLOSING = False
    COMPACT = False
    QUOTE = True

    def __init__(self, childs, attrs):
        "add childs and call parent constructor"
        tag = self.__class__.__name__.lower()
        Element.__init__(self, tag, attrs)

        for child in childs:
            self.append(child)

        escape_attrs(self)

    def append(self, child):
        if not isinstance(child, Element):
            if self._children:
                last_children = self._children[-1]
                
                if last_children.tail is None:
                    last_children.tail = to_str(child)
                else:
                    last_children.tail += to_str(child)

            elif self.text is None:
                self.text = to_str(child)
            else:
                self.text += to_str(child)
        else:
            Element.append(self, child)

    def __repr__(self):
        return ET.tostring(self, "utf-8", "html")

    def __str__(self):
        "return a string representation"
        return ET.tostring(self, "utf-8", "html")

Comment = ET.Comment

TAGS = {
    "a": (True, True, False, "Defines a hyperlink"),
    "abbr": (True, False, False, "Defines an abbreviation"),
    "address": (True, False, False, "Defines an address element"),
    "area": (True, False, False, "Defines an area inside an image map"),
    "article": (True, False, False, "Defines an article"),
    "aside": (True, False, False, "Defines content aside from the page content"),
    "audio": (True, False, False, "Defines sound content"),
    "b": (True, False, False, "Defines bold text"),
    "base": (True, False, False, "Defines a base URL for all the links in a page"),
    "bdi": (True, False, False, "Defines text that is isolated from its surrounding"
        "text direction settings"),
    "bdo": (True, False, False, "Defines the direction of text display"),
    "blockquote": (True, False, False, "Defines a long quotation"),
    "body": (True, False, False, "Defines the body element"),
    "br": (True, False, True, "Inserts a single line break"),
    "button": (True, False, False, "Defines a push button"),
    "canvas": (True, False, False, "Defines graphics"),
    "caption": (True, False, False, "Defines a table caption"),
    "cite": (True, True, False, "Defines a citation"),
    "code": (True, False, False, "Defines computer code text"),
    "col": (True, False, False, "Defines attributes for table columns "),
    "colgroup": (True, False, False, "Defines groups of table columns"),
    "command": (True, False, False, "Defines a command button"),
    "datalist": (True, False, False, "Defines a list of options for an input field"),
    "dd": (True, False, False, "Defines a definition description"),
    "del": (True, False, False, "Defines deleted text"),
    "details": (True, False, False, "Defines details of an element"),
    "dfn": (True, False, False, "Defines a definition term"),
    "div": (True, False, False, "Defines a section in a document"),
    "dl": (True, False, False, "Defines a definition list"),
    "dt": (True, False, False, "Defines a definition term"),
    "em": (True, True, False, "Defines emphasized text "),
    "embed": (True, False, False, "Defines external interactive content or plugin"),
    "fieldset": (True, False, False, "Defines a fieldset"),
    "figcaption": (True, False, False, "Defines the caption of a figure element"),
    "figure": (True, False, False, "Defines a group of media content, and their caption"),
    "footer": (True, False, False, "Defines a footer for a section or page"),
    "form": (True, False, False, "Defines a form "),
    "h1": (True, True, False, "Defines header level 1"),
    "h2": (True, True, False, "Defines header level 2"),
    "h3": (True, True, False, "Defines header level 3"),
    "h4": (True, True, False, "Defines header level 4"),
    "h5": (True, True, False, "Defines header level 5"),
    "h6": (True, True, False, "Defines header level 6"),
    "head": (True, False, False, "Defines information about the document"),
    "header": (True, False, False, "Defines a header for a section or page"),
    "hgroup": (True, False, False, "Defines information about a section in a document"),
    "hr": (True, False, True, "Defines a horizontal rule"),
    "html": (True, False, False, "Defines an html document"),
    "i": (True, True, False, "Defines italic text"),
    "iframe": (True, False, False, "Defines an inline sub window (frame)"),
    "img": (True, False, True, "Defines an image"),
    "input": (True, False, True, "Defines an input field"),
    "ins": (True, False, False, "Defines inserted text"),
    "keygen": (True, False, False, "Defines a key pair generator field (for forms)"),
    "kbd": (True, False, False, "Defines keyboard text"),
    "label": (True, True, False, "Defines a label for a form control"),
    "legend": (True, False, False, "Defines a title in a fieldset"),
    "li": (True, False, False, "Defines a list item"),
    "link": (True, False, True, "Defines a resource reference"),
    "map": (True, False, False, "Defines an image map "),
    "mark": (True, False, False, "Defines marked text"),
    "menu": (True, False, False, "Defines a menu list"),
    "meta": (True, False, True, "Defines meta information"),
    "meter": (True, False, False, "Defines a scalar measurement within a known range"),
    "nav": (True, False, False, "Defines navigation links"),
    "noscript": (True, False, False, "Defines a noscript section"),
    "object": (True, False, False, "Defines an embedded object"),
    "ol": (True, False, False, "Defines an ordered list"),
    "optgroup": (True, False, False, "Defines an option group"),
    "option": (True, False, False, "Defines an option in a drop-down list"),
    "output": (True, False, False, "Defines the result of a calculation"),
    "p": (True, True, False, "Defines a paragraph"),
    "param": (True, False, False, "Defines a parameter for an object"),
    "pre": (True, True, False, "Defines preformatted text"),
    "progress": (True, False, False, "Represents the progress of a task"),
    "q": (True, False, False, "Defines a short quotation"),
    "rp": (True, False, False, "Used in ruby annotations to define what to show if a "
            "browser does not support the ruby element"),
    "rt": (True, False, False, "Defines explanation to ruby annotations"),
    "ruby": (True, False, False, "Defines ruby annotations"),
    "s": (True, True, False, "Defines text that is no longer correct"),
    "samp": (True, False, False, "Defines sample computer code"),
    "script": (False, True, False, "Defines a script"),
    "section": (True, False, False, "Defines a section"),
    "select": (True, False, False, "Defines a selectable list"),
    "small": (True, True, False, "Defines smaller text"),
    "source": (True, False, False, "Defines multiple media resources for media elements, "
            "such as audio and video"),
    "span": (True, True, False, "Defines a section in a document"),
    "strong": (True, True, False, "Defines strong text"),
    "style": (False, False, False, "Defines a style definition"),
    "sub": (True, True, False, "Defines subscripted text"),
    "summary": (True, False, False, "Defines the header of a 'detail' element"),
    "sup": (True, True, False, "Defines superscripted text"),
    "table": (True, False, False, "Defines a table"),
    "tbody": (True, False, False, "Defines a table body"),
    "td": (True, False, False, "Defines a table cell"),
    "textarea": (True, False, False, "Defines a text area"),
    "tfoot": (True, False, False, "Defines a table footer"),
    "th": (True, False, False, "Defines a table header"),
    "thead": (True, False, False, "Defines a table header"),
    "time": (True, False, False, "Defines a date/time"),
    "title": (True, False, False, "Defines the document title"),
    "tr": (True, False, False, "Defines a table row"),
    "track": (True, False, False, "Defines text tracks used in mediaplayers"),
    "ul": (True, False, False, "Defines an unordered list"),
    "var": (True, True, False, "Defines a variable"),
    "video": (True, False, False, "Defines a video or movie"),
    "wbr": (True, False, False, "Defines a possible line-break")
}

def create_tags(ctx):
    "create all classes and put them in ctx"

    for (tag, info) in TAGS.iteritems():
        class_name = tag.title()
        quote, compact, self_closing, docs = info

        def __init__(self, *childs, **attrs):
            TagBase.__init__(self, childs, attrs)

        cls = type(class_name, (TagBase,), {
            "__doc__": docs,
            "__init__": __init__
        })

        cls.QUOTE = quote
        cls.COMPACT = compact
        cls.SELF_CLOSING = self_closing

        ctx[class_name] = cls

create_tags(globals())

class Raw(Element):
    def __init__(self, content):
        self.content = ET.fromstring(content)
        Element.__init__(self, self.content.tag, self.content.attrib)

    def __iter__(self):
        yield self.content

    def __repr__(self):
        return ET.tostring(self.content, "utf-8", "html")

    def __str__(self):
        "return a string representation"
        return ET.tostring(self.content, "utf-8", "html")

    def append(self, content):
        pass

def raw(content):
    return Raw(content)

DOCTYPE = "<!DOCTYPE html>"

HEADINGS = {
    1: H1,
    2: H2,
    3: H3,
    4: H4,
    5: H5,
    6: H6
}

########NEW FILE########
__FILENAME__ = postprocessors
import os

import html5css3
import html
import json

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst import Directive

BASE_PATH = os.path.dirname(__file__)

join_path = os.path.join

def as_list(val):
    """return a list with val if val is not already a list, val otherwise"""
    if isinstance(val, list):
        return val
    else:
        return [val]

def abspath(path):
    return join_path(BASE_PATH, path)

def js_fullpath(path, embed=True):
    content = open(path).read().decode('utf-8')

    if embed:
        return html.Script(content)
    else:
        return html.Script(src=path)

def js(path, embed=True):
    return js_fullpath(abspath(path), embed)

def css(path, embed=True):
    content = open(abspath(path)).read().decode('utf-8')

    if embed:
        return html.Style(content, type="text/css")
    else:
        return html.Link(href=path, rel="stylesheet", type="text/css")

def pretty_print_code(tree, embed=True, params=None):
    head = tree[0]
    body = tree[1]

    body.append(js(join_path("thirdparty", "prettify.js"), embed))
    body.append(html.Script("$(function () { prettyPrint() })"))

    head.append(css(join_path("thirdparty", "prettify.css")))

def jquery(tree, embed=True, params=None):
    body = tree[1]
    body.append(js(join_path("thirdparty", "jquery.js"), embed))

def add_class(element, cls_name):
    cls = element.get("class", "")

    if cls:
        cls += " " + cls_name
    else:
        cls += cls_name

    element.set("class", cls)

def deckjs(tree, embed=True, params=None):
    head = tree[0]
    body = tree[1]

    def path(*args):
        return join_path("thirdparty", "deckjs", *args)

    head.remove(head.find("./style"))
    add_class(body, "deck-container")

    for section in tree.findall(".//section"):
        add_class(section, "slide")

    # Core and extension CSS files
    head.append(css(path("core", "deck.core.css"), embed))
    head.append(css(path("extensions", "goto", "deck.goto.css"), embed))
    head.append(css(path("extensions", "menu", "deck.menu.css"), embed))
    head.append(css(path("extensions", "navigation", "deck.navigation.css"), embed))
    head.append(css(path("extensions", "status", "deck.status.css"), embed))
    head.append(css(path("extensions", "hash", "deck.hash.css"), embed))

    # Theme CSS files (menu swaps these out)
    head.append(css(path("themes", "style", "web-2.0.css"), embed))
    head.append(css(path("themes", "transition", "horizontal-slide.css"), embed))

    body.append(js(path("modernizr.custom.js"), embed))
    jquery(tree, embed)

    # Deck Core and extensions
    body.append(js(path("core", "deck.core.js"), embed))
    body.append(js(path("extensions", "hash", "deck.hash.js"), embed))
    body.append(js(path("extensions", "menu", "deck.menu.js"), embed))
    body.append(js(path("extensions", "goto", "deck.goto.js"), embed))
    body.append(js(path("extensions", "status", "deck.status.js"), embed))
    body.append(js(path("extensions", "navigation", "deck.navigation.js"), embed))

    body.append(html.Script("$(function () { $.deck('.slide'); });"))

def add_js(tree, embed=True, params=None):
    params = params or {}
    paths = as_list(params.get("path", []))

    body = tree[1]
    for path in paths:
        body.append(js_fullpath(path, embed))

def revealjs(tree, embed=True, params=None):
    head = tree[0]
    body = tree[1]
    params = params or {}
    theme_name = params.pop("theme", "default") + ".css"

    def path(*args):
        return join_path("thirdparty", "revealjs", *args)

    add_class(body, "reveal")
    slides = html.Div(class_="slides")

    for item in list(body):
        body.remove(item)
        slides.append(item)

    body.append(slides)

    # <link rel="stylesheet" href="css/reveal.css">
    # <link rel="stylesheet" href="css/theme/default.css" id="theme">
    head.append(css(path("css", "reveal.css"), embed))
    head.append(css(path("css", "theme", theme_name), embed))

    # <script src="lib/js/head.min.js"></script>
    # <script src="js/reveal.min.js"></script>
    body.append(js(path("lib", "js", "head.min.js"), embed))
    body.append(js(path("js", "reveal.min.js"), embed))

    head.append(css("rst2html5-reveal.css", embed))

    params['history'] = True
    param_s = json.dumps(params)
    body.append(
        html.Script("$(function () { Reveal.initialize(%s); });" % param_s))

def impressjs(tree, embed=True, params=None):
    head = tree[0]
    body = tree[1]

    def path(*args):
        return join_path("thirdparty", "impressjs", *args)

    # remove the default style
    #head.remove(head.find("./style"))
    add_class(body, "impress-not-supported")
    failback = html.Div('<div class="fallback-message">' + 
        '<p>Your browser <b>doesn\'t support the features required</b> by' + 
        'impress.js, so you are presented with a simplified version of this' + 
        'presentation.</p>' + 
        '<p>For the best experience please use the latest <b>Chrome</b>,' + 
        '<b>Safari</b> or <b>Firefox</b> browser.</p></div>')

    slides = html.Div(id="impress")

    for item in list(body):
        body.remove(item)
        slides.append(item)

    body.append(slides)

    # <script src="js/impress.js"></script>
    body.append(js(path("js", "impress.js"), embed))

    body.append(html.Script("impress().init();"))

def bootstrap_css(tree, embed=True, params=None):
    head = tree[0]

    head.append(css(join_path("thirdparty", "bootstrap.css"), embed))
    head.append(css("rst2html5.css", embed))

def embed_images(tree, embed=True, params=None):
    import base64
    for image in tree.findall(".//img"):
        path = image.attrib['src']
        lowercase_path = path.lower()

        if lowercase_path.endswith(".png"):
            content_type = "image/png"
        elif lowercase_path.endswith(".jpg"):
            content_type = "image/jpg"
        elif lowercase_path.endswith(".gif"):
            content_type = "image/gif"
        else:
            continue

        encoded = base64.b64encode(open(path).read())
        content = "data:%s;base64,%s" % (content_type, encoded)
        image.set('src', content)

def pygmentize(tree, embed=True, params=None):
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters import HtmlFormatter

    pygments_formatter = HtmlFormatter()
    body = tree[1]

    def highlight_code(lang, code):
        try:
            lexer = get_lexer_by_name(lang)
        except ValueError:
            # no lexer found - use the text one instead of an exception
            lexer = get_lexer_by_name('text')

        parsed = highlight(code, lexer, pygments_formatter)
        return parsed

    for block in body.findall(".//pre"):
        cls = block.attrib.get('class', '')
        classes = cls.split()
        if 'code' in classes:
            lang_classes = [cls for cls in classes if cls.startswith('lang-')]

            if len(lang_classes) > 0:
                lang = lang_classes[0][5:]

                new_content = highlight_code(lang, block.text)
                block.tag = 'div'
                block.text = new_content

def mathjax(tree, embed=True, params=None):
    body = tree[1]
    params = params or {}
    config_path = params.get("config")
    url = params.get("url", "http://cdn.mathjax.org/mathjax/latest/MathJax.js")


    if config_path is None:
        content = """
      MathJax.Hub.Config({
        extensions: [],
        jax: ["input/TeX", "output/HTML-CSS"],
        tex2jax: {
          inlineMath: [ ['$','$'], ["\\(","\\)"] ],
          displayMath: [ ['$$','$$'], ["\\[","\\]"] ],
          processEscapes: true
        },
        "HTML-CSS": { availableFonts: ["TeX"] }
      });
        """
    else:
        with open(config_path) as f_in:
            content = f_in.read()

    body.append(html.Script(content, type="text/x-mathjax-config"))
    body.append(html.Script(src=url))


PROCESSORS = {
    "mathjax": {
        "name": "add mathjax support",
        "processor": mathjax
    },
    "jquery": {
        "name": "add jquery",
        "processor": jquery
    },
    "pretty_print_code": {
        "name": "pretty print code",
        "processor": pretty_print_code
    },
    "pygments": {
        "name": "pygments",
        "processor": pygmentize
    },
    "deck_js": {
        "name": "deck.js",
        "processor": deckjs
    },
    "reveal_js": {
        "name": "reveal.js",
        "processor": revealjs
    },
    "impress_js": {
        "name": "impress.js",
        "processor": impressjs
    },
    "bootstrap_css": {
        "name": "bootstrap css",
        "processor": bootstrap_css
    },
    "embed_images": {
        "name": "embed images",
        "processor": embed_images
    },
    "add_js": {
        "name": "add js files",
        "processor": add_js
    }
}

class Code(Directive):
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    has_content = True

    def run(self):
        language = self.arguments[0]
        content = self.content

        attrs = {
            'class': "code lang-" + language
        }

        return [nodes.literal_block('', "\n".join(content), **attrs)]

class Slide3D(Directive):

    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
            'x': int,
            'y': int,
            'z': int,
            'rotate': int,
            'rotate-x': int,
            'rotate-y': int,
            'scale': int,
            'class': directives.unchanged,
            'id': directives.unchanged,
            'title': directives.unchanged
    }
    has_content = True

    def run(self):
        attributes = {}

        for key, value in self.options.iteritems():
            if key in ('class', 'id', 'title'):
                attributes[key] = value
            else:
                attributes['data-' + key] = value

        node = nodes.container(rawsource=self.block_text, **attributes)
        self.state.nested_parse(self.content, self.content_offset, node)

        return [node]

directives.register_directive('slide-3d', Slide3D)
directives.register_directive('code-block', Code)

########NEW FILE########
