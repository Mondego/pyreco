__FILENAME__ = css
# -*- coding: utf-8 -*-
# This file is part of CairoSVG
# Copyright © 2010-2012 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with CairoSVG.  If not, see <http://www.gnu.org/licenses/>.

"""
Optionally handle CSS stylesheets.

"""

import os
from .parser import HAS_LXML

# Detect optional depedencies
# pylint: disable=W0611
try:
    import tinycss
    import cssselect
    CSS_CAPABLE = HAS_LXML
except ImportError:
    CSS_CAPABLE = False
# pylint: enable=W0611


# Python 2/3 compat
iteritems = getattr(dict, "iteritems", dict.items)  # pylint: disable=C0103


def find_stylesheets(tree, url):
    """Find the stylesheets included in ``tree``."""
    # TODO: support contentStyleType on <svg>
    default_type = "text/css"
    process = tree.getprevious()
    while process is not None:
        if (getattr(process, "target", None) == "xml-stylesheet" and
                process.attrib.get("type", default_type) == "text/css"):
            # TODO: handle web URLs
            filename = process.attrib.get("href")
            if filename:
                path = os.path.join(os.path.dirname(url), filename)
                if os.path.isfile(path):
                    yield tinycss.make_parser().parse_stylesheet_file(path)
        process = process.getprevious()
    for element in tree.iter():
        # http://www.w3.org/TR/SVG/styling.html#StyleElement
        if (element.tag == "style"
                and element.get("type", default_type) == "text/css"
                and element.text):
            # TODO: pass href for relative URLs
            # TODO: support media types
            # TODO: what if <style> has children elements?
            yield tinycss.make_parser().parse_stylesheet(element.text)


def find_stylesheets_rules(stylesheet, url):
    """Find the rules in a stylesheet."""
    for rule in stylesheet.rules:
        if isinstance(rule, tinycss.css21.ImportRule):
            css_path = os.path.normpath(
                os.path.join(os.path.dirname(url), rule.uri))
            if not os.path.exists(css_path):
                continue
            with open(css_path) as f:
                stylesheet = tinycss.make_parser().parse_stylesheet(f.read())
                for rule in find_stylesheets_rules(stylesheet, css_path):
                    yield rule
        if not rule.at_keyword:
            yield rule


def find_style_rules(tree):
    """Find the style rules in ``tree``."""
    for stylesheet in find_stylesheets(tree.xml_tree, tree.url):
        # TODO: warn for each stylesheet.errors
        for rule in find_stylesheets_rules(stylesheet, tree.url):
            yield rule


def get_declarations(rule):
    """Get the declarations in ``rule``."""
    for declaration in rule.declarations:
        if declaration.name.startswith("-"):
            # Ignore properties prefixed by "-"
            continue
        # TODO: filter out invalid values
        yield (
            declaration.name,
            declaration.value.as_css(),
            bool(declaration.priority))


def match_selector(rule, tree):
    """Yield the ``(element, specificity)`` in ``tree`` matching ``rule``."""
    selector_list = cssselect.parse(rule.selector.as_css())
    translator = cssselect.GenericTranslator()
    for selector in selector_list:
        if not selector.pseudo_element:
            specificity = selector.specificity()
            for element in tree.xpath(translator.selector_to_xpath(selector)):
                yield element, specificity


def apply_stylesheets(tree):
    """Apply the stylesheet in ``tree`` to ``tree``."""
    if not CSS_CAPABLE:
        # TODO: warn?
        return
    style_by_element = {}
    for rule in find_style_rules(tree):
        declarations = list(get_declarations(rule))
        for element, specificity in match_selector(rule, tree.xml_tree):
            style = style_by_element.setdefault(element, {})
            for name, value, important in declarations:
                weight = important, specificity
                if name in style:
                    _old_value, old_weight = style[name]
                    if old_weight > weight:
                        continue
                style[name] = value, weight

    for element, style in iteritems(style_by_element):
        values = ["%s: %s" % (name, value)
                  for name, (value, weight) in iteritems(style)]
        element.set("_style", ";".join(values))

########NEW FILE########
__FILENAME__ = features
# -*- coding: utf-8 -*-
# This file is part of CairoSVG
# Copyright © 2010-2012 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with CairoSVG.  If not, see <http://www.gnu.org/licenses/>.

"""
Helpers related to SVG conditional processing.

"""

import locale


ROOT = "http://www.w3.org/TR/SVG11/feature"
LOCALE = locale.getdefaultlocale()[0] or ""
SUPPORTED_FEATURES = set(
    ROOT + "#" + feature for feature in [
        "SVG",
        "SVG-static",
        "CoreAttribute",
        "Structure",
        "BasicStructure",
        "ConditionalProcessing",
        "Image",
        "Style",
        "ViewportAttribute",
        "Shape",
        "BasicText",
        "BasicPaintAttribute",
        "OpacityAttribute",
        "BasicGraphicsAttribute",
        "Marker",
        "Gradient",
        "Pattern",
        "Clip",
        "BasicClip",
        "Mask"
    ])


def has_features(features):
    """Check whether ``features`` are supported by CairoSVG."""
    return SUPPORTED_FEATURES >= set(features.strip().split(" "))


def support_languages(languages):
    """Check whether one of ``languages`` is part of the user locales."""
    for language in languages.split(","):
        language = language.strip()
        if language and LOCALE.startswith(language):
            return True
    return False


def match_features(node):
    """Check the node match the conditional processing attributes."""
    features = node.attrib.get("requiredFeatures")
    languages = node.attrib.get("systemLanguage")
    if "requiredExtensions" in node.attrib:
        return False
    if features is not None and not has_features(features):
        return False
    if languages is not None and not support_languages(languages):
        return False
    return True

########NEW FILE########
__FILENAME__ = parser
# -*- coding: utf-8 -*-
# This file is part of CairoSVG
# Copyright © 2010-2012 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with CairoSVG.  If not, see <http://www.gnu.org/licenses/>.

"""
SVG Parser.

"""

# Fallbacks for Python 2/3 and lxml/ElementTree
# pylint: disable=E0611,F0401,W0611
try:
    import lxml.etree as ElementTree
    from lxml.etree import XMLSyntaxError as ParseError
    HAS_LXML = True
except ImportError:
    from xml.etree import ElementTree
    from xml.parsers import expat
    # ElementTree's API changed between 2.6 and 2.7
    # pylint: disable=C0103
    ParseError = getattr(ElementTree, 'ParseError', expat.ExpatError)
    # pylint: enable=C0103
    HAS_LXML = False

try:
    from urllib import urlopen
    import urlparse
except ImportError:
    from urllib.request import urlopen
    from urllib import parse as urlparse  # Python 3
# pylint: enable=E0611,F0401,W0611


import re
import gzip
import uuid
import os.path

from .css import apply_stylesheets
from .features import match_features
from .surface.helpers import urls, rotations, pop_rotation, flatten


# Python 2/3 compat
# pylint: disable=C0103,W0622
try:
    basestring
except NameError:
    basestring = str
# pylint: enable=C0103,W0622


def remove_svg_namespace(tree):
    """Remove the SVG namespace from ``tree`` tags.

    ``lxml.cssselect`` does not support empty/default namespaces, so remove any
    SVG namespace.

    """
    prefix = "{http://www.w3.org/2000/svg}"
    prefix_len = len(prefix)
    iterator = (
        tree.iter() if hasattr(tree, 'iter')
        else tree.getiterator())
    for element in iterator:
        tag = element.tag
        if hasattr(tag, "startswith") and tag.startswith(prefix):
            element.tag = tag[prefix_len:]


def handle_white_spaces(string, preserve):
    """Handle white spaces in text nodes."""
    # http://www.w3.org/TR/SVG/text.html#WhiteSpace
    if not string:
        return ""
    if preserve:
        string = re.sub("[\n\r\t]", " ", string)
    else:
        string = re.sub("[\n\r]", "", string)
        string = re.sub("\t", " ", string)
        string = re.sub(" +", " ", string)
    return string


class Node(dict):
    """SVG node with dict-like properties and children."""
    def __init__(self, node, parent=None, parent_children=False, url=None):
        """Create the Node from ElementTree ``node``, with ``parent`` Node."""
        super(Node, self).__init__()
        self.children = ()

        self.root = False
        self.tag = node.tag
        self.text = node.text
        self.node = node

        # Inherits from parent properties
        if parent is not None:
            items = parent.copy()
            not_inherited = (
                "transform", "opacity", "style", "viewBox", "stop-color",
                "stop-opacity", "width", "height", "filter", "mask", "rotate",
                "{http://www.w3.org/1999/xlink}href", "id", "x", "y",
                "overflow", "clip", "clip-path")
            for attribute in not_inherited:
                if attribute in items:
                    del items[attribute]

            self.update(items)
            self.url = url or parent.url
            self.parent = parent
        else:
            self.url = getattr(self, "url", None)
            self.parent = getattr(self, "parent", None)

        self.update(dict(self.node.attrib.items()))

        # Give an id for nodes that don't have one
        if "id" not in self:
            self["id"] = uuid.uuid4().hex

        # Handle the CSS
        style = self.pop("_style", "") + ";" + self.pop("style", "").lower()
        for declaration in style.split(";"):
            if ":" in declaration:
                name, value = declaration.split(":", 1)
                self[name.strip()] = value.strip()

        # Replace currentColor by a real color value
        color_attributes = (
            "fill", "stroke", "stop-color", "flood-color",
            "lighting-color")
        for attribute in color_attributes:
            if self.get(attribute) == "currentColor":
                self[attribute] = self.get("color", "black")

        # Replace inherit by the parent value
        for attribute, value in dict(self).items():
            if value == "inherit":
                if parent is not None and attribute in parent:
                    self[attribute] = parent.get(attribute)
                else:
                    del self[attribute]

        # Manage text by creating children
        if self.tag in ("text", "textPath", "a"):
            self.children, _ = self.text_children(node, True, True)

        if parent_children:
            self.children = [Node(child.node, parent=self)
                             for child in parent.children]
        elif not self.children:
            self.children = []
            for child in node:
                if isinstance(child.tag, basestring):
                    if match_features(child):
                        self.children.append(Node(child, self))
                        if self.tag == "switch":
                            break

    def text_children(self, node, trailing_space, text_root=False):
        """Create children and return them."""
        children = []
        space = "{http://www.w3.org/XML/1998/namespace}space"
        preserve = self.get(space) == "preserve"
        self.text = handle_white_spaces(node.text, preserve)
        if trailing_space and not preserve:
            self.text = self.text.lstrip(" ")
        original_rotate = rotations(self)
        rotate = list(original_rotate)
        if original_rotate:
            pop_rotation(self, original_rotate, rotate)
        if self.text:
            trailing_space = self.text.endswith(" ")
        for child in node:
            if child.tag == "tref":
                href = child.get("{http://www.w3.org/1999/xlink}href")
                tree_urls = urls(href)
                url = tree_urls[0] if tree_urls else None
                child_tree = Tree(url=url, parent=self)
                child_tree.clear()
                child_tree.update(self)
                child_node = Node(
                    child, parent=child_tree, parent_children=True)
                child_node.tag = "tspan"
                # Retrieve the referenced node and get its flattened text
                # and remove the node children.
                child = child_tree.xml_tree
                child.text = flatten(child)
            else:
                child_node = Node(child, parent=self)
            child_preserve = child_node.get(space) == "preserve"
            child_node.text = handle_white_spaces(child.text, child_preserve)
            child_node.children, trailing_space = \
                child_node.text_children(child, trailing_space)
            trailing_space = child_node.text.endswith(" ")
            if original_rotate and "rotate" not in child_node:
                pop_rotation(child_node, original_rotate, rotate)
            children.append(child_node)
            if child.tail:
                anonymous = Node(ElementTree.Element("tspan"), parent=self)
                anonymous.text = handle_white_spaces(child.tail, preserve)
                if original_rotate:
                    pop_rotation(anonymous, original_rotate, rotate)
                if trailing_space and not preserve:
                    anonymous.text = anonymous.text.lstrip(" ")
                if anonymous.text:
                    trailing_space = anonymous.text.endswith(" ")
                children.append(anonymous)

        if text_root and not children and not preserve:
            self.text = self.text.rstrip(" ")

        return children, trailing_space


class Tree(Node):
    """SVG tree."""
    def __new__(cls, **kwargs):
        tree_cache = kwargs.get("tree_cache")
        if tree_cache:
            if "url" in kwargs:
                url_parts = kwargs["url"].split("#", 1)
                if len(url_parts) == 2:
                    url, element_id = url_parts
                else:
                    url, element_id = url_parts[0], None
                parent = kwargs.get("parent")
                if parent and not url:
                    url = parent.url
                if (url, element_id) in tree_cache:
                    cached_tree = tree_cache[(url, element_id)]
                    new_tree = Node(cached_tree.xml_tree, parent)
                    new_tree.xml_tree = cached_tree.xml_tree
                    new_tree.url = url
                    new_tree.tag = cached_tree.tag
                    new_tree.root = True
                    return new_tree
        return dict.__new__(cls)

    def __init__(self, **kwargs):
        """Create the Tree from SVG ``text``."""
        if getattr(self, "xml_tree", None) is not None:
            # The tree has already been parsed
            return

        # Make the parameters keyword-only:
        bytestring = kwargs.pop("bytestring", None)
        file_obj = kwargs.pop("file_obj", None)
        url = kwargs.pop("url", None)
        parent = kwargs.pop("parent", None)
        parent_children = kwargs.pop("parent_children", None)
        tree_cache = kwargs.pop("tree_cache", None)
        element_id = None

        if bytestring is not None:
            tree = ElementTree.fromstring(bytestring)
            self.url = url
        elif file_obj is not None:
            tree = ElementTree.parse(file_obj).getroot()
            if url:
                self.url = url
            else:
                self.url = getattr(file_obj, "name", None)
        elif url is not None:
            if "#" in url:
                url, element_id = url.split("#", 1)
            else:
                element_id = None
            if parent and parent.url:
                if url:
                    url = urlparse.urljoin(parent.url, url)
                elif element_id:
                    url = parent.url
            self.url = url
            if url:
                if urlparse.urlparse(url).scheme:
                    input_ = urlopen(url)
                else:
                    input_ = url  # filename
                if os.path.splitext(url)[1].lower() == "svgz":
                    input_ = gzip.open(url)
                tree = ElementTree.parse(input_).getroot()
            else:
                root_parent = parent
                while root_parent.parent:
                    root_parent = root_parent.parent
                tree = root_parent.xml_tree
        else:
            raise TypeError(
                "No input. Use one of bytestring, file_obj or url.")
        remove_svg_namespace(tree)
        self.xml_tree = tree
        apply_stylesheets(self)
        if element_id:
            iterator = (
                tree.iter() if hasattr(tree, "iter")
                else tree.getiterator())
            for element in iterator:
                if element.get("id") == element_id:
                    self.xml_tree = element
                    break
            else:
                raise TypeError(
                    'No tag with id="%s" found.' % element_id)
        super(Tree, self).__init__(self.xml_tree, parent, parent_children, url)
        self.root = True
        if tree_cache is not None and url is not None:
            tree_cache[(self.url, self["id"])] = self

########NEW FILE########
__FILENAME__ = colors
# -*- coding: utf-8 -*-
# This file is part of CairoSVG
# Copyright © 2010-2012 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with CairoSVG.  If not, see <http://www.gnu.org/licenses/>.

"""
SVG colors.

"""


COLORS = {
    "aliceblue": "rgb(240, 248, 255)",
    "antiquewhite": "rgb(250, 235, 215)",
    "aqua": "rgb(0, 255, 255)",
    "aquamarine": "rgb(127, 255, 212)",
    "azure": "rgb(240, 255, 255)",
    "beige": "rgb(245, 245, 220)",
    "bisque": "rgb(255, 228, 196)",
    "black": "rgb(0, 0, 0)",
    "blanchedalmond": "rgb(255, 235, 205)",
    "blue": "rgb(0, 0, 255)",
    "blueviolet": "rgb(138, 43, 226)",
    "brown": "rgb(165, 42, 42)",
    "burlywood": "rgb(222, 184, 135)",
    "cadetblue": "rgb(95, 158, 160)",
    "chartreuse": "rgb(127, 255, 0)",
    "chocolate": "rgb(210, 105, 30)",
    "coral": "rgb(255, 127, 80)",
    "cornflowerblue": "rgb(100, 149, 237)",
    "cornsilk": "rgb(255, 248, 220)",
    "crimson": "rgb(220, 20, 60)",
    "cyan": "rgb(0, 255, 255)",
    "darkblue": "rgb(0, 0, 139)",
    "darkcyan": "rgb(0, 139, 139)",
    "darkgoldenrod": "rgb(184, 134, 11)",
    "darkgray": "rgb(169, 169, 169)",
    "darkgreen": "rgb(0, 100, 0)",
    "darkgrey": "rgb(169, 169, 169)",
    "darkkhaki": "rgb(189, 183, 107)",
    "darkmagenta": "rgb(139, 0, 139)",
    "darkolivegreen": "rgb(85, 107, 47)",
    "darkorange": "rgb(255, 140, 0)",
    "darkorchid": "rgb(153, 50, 204)",
    "darkred": "rgb(139, 0, 0)",
    "darksalmon": "rgb(233, 150, 122)",
    "darkseagreen": "rgb(143, 188, 143)",
    "darkslateblue": "rgb(72, 61, 139)",
    "darkslategray": "rgb(47, 79, 79)",
    "darkslategrey": "rgb(47, 79, 79)",
    "darkturquoise": "rgb(0, 206, 209)",
    "darkviolet": "rgb(148, 0, 211)",
    "deeppink": "rgb(255, 20, 147)",
    "deepskyblue": "rgb(0, 191, 255)",
    "dimgray": "rgb(105, 105, 105)",
    "dimgrey": "rgb(105, 105, 105)",
    "dodgerblue": "rgb(30, 144, 255)",
    "firebrick": "rgb(178, 34, 34)",
    "floralwhite": "rgb(255, 250, 240)",
    "forestgreen": "rgb(34, 139, 34)",
    "fuchsia": "rgb(255, 0, 255)",
    "gainsboro": "rgb(220, 220, 220)",
    "ghostwhite": "rgb(248, 248, 255)",
    "gold": "rgb(255, 215, 0)",
    "goldenrod": "rgb(218, 165, 32)",
    "gray": "rgb(128, 128, 128)",
    "grey": "rgb(128, 128, 128)",
    "green": "rgb(0, 128, 0)",
    "greenyellow": "rgb(173, 255, 47)",
    "honeydew": "rgb(240, 255, 240)",
    "hotpink": "rgb(255, 105, 180)",
    "indianred": "rgb(205, 92, 92)",
    "indigo": "rgb(75, 0, 130)",
    "ivory": "rgb(255, 255, 240)",
    "khaki": "rgb(240, 230, 140)",
    "lavender": "rgb(230, 230, 250)",
    "lavenderblush": "rgb(255, 240, 245)",
    "lawngreen": "rgb(124, 252, 0)",
    "lemonchiffon": "rgb(255, 250, 205)",
    "lightblue": "rgb(173, 216, 230)",
    "lightcoral": "rgb(240, 128, 128)",
    "lightcyan": "rgb(224, 255, 255)",
    "lightgoldenrodyellow": "rgb(250, 250, 210)",
    "lightgray": "rgb(211, 211, 211)",
    "lightgreen": "rgb(144, 238, 144)",
    "lightgrey": "rgb(211, 211, 211)",
    "lightpink": "rgb(255, 182, 193)",
    "lightsalmon": "rgb(255, 160, 122)",
    "lightseagreen": "rgb(32, 178, 170)",
    "lightskyblue": "rgb(135, 206, 250)",
    "lightslategray": "rgb(119, 136, 153)",
    "lightslategrey": "rgb(119, 136, 153)",
    "lightsteelblue": "rgb(176, 196, 222)",
    "lightyellow": "rgb(255, 255, 224)",
    "lime": "rgb(0, 255, 0)",
    "limegreen": "rgb(50, 205, 50)",
    "linen": "rgb(250, 240, 230)",
    "magenta": "rgb(255, 0, 255)",
    "maroon": "rgb(128, 0, 0)",
    "mediumaquamarine": "rgb(102, 205, 170)",
    "mediumblue": "rgb(0, 0, 205)",
    "mediumorchid": "rgb(186, 85, 211)",
    "mediumpurple": "rgb(147, 112, 219)",
    "mediumseagreen": "rgb(60, 179, 113)",
    "mediumslateblue": "rgb(123, 104, 238)",
    "mediumspringgreen": "rgb(0, 250, 154)",
    "mediumturquoise": "rgb(72, 209, 204)",
    "mediumvioletred": "rgb(199, 21, 133)",
    "midnightblue": "rgb(25, 25, 112)",
    "mintcream": "rgb(245, 255, 250)",
    "mistyrose": "rgb(255, 228, 225)",
    "moccasin": "rgb(255, 228, 181)",
    "navajowhite": "rgb(255, 222, 173)",
    "navy": "rgb(0, 0, 128)",
    "oldlace": "rgb(253, 245, 230)",
    "olive": "rgb(128, 128, 0)",
    "olivedrab": "rgb(107, 142, 35)",
    "orange": "rgb(255, 165, 0)",
    "orangered": "rgb(255, 69, 0)",
    "orchid": "rgb(218, 112, 214)",
    "palegoldenrod": "rgb(238, 232, 170)",
    "palegreen": "rgb(152, 251, 152)",
    "paleturquoise": "rgb(175, 238, 238)",
    "palevioletred": "rgb(219, 112, 147)",
    "papayawhip": "rgb(255, 239, 213)",
    "peachpuff": "rgb(255, 218, 185)",
    "peru": "rgb(205, 133, 63)",
    "pink": "rgb(255, 192, 203)",
    "plum": "rgb(221, 160, 221)",
    "powderblue": "rgb(176, 224, 230)",
    "purple": "rgb(128, 0, 128)",
    "red": "rgb(255, 0, 0)",
    "rosybrown": "rgb(188, 143, 143)",
    "royalblue": "rgb(65, 105, 225)",
    "saddlebrown": "rgb(139, 69, 19)",
    "salmon": "rgb(250, 128, 114)",
    "sandybrown": "rgb(244, 164, 96)",
    "seagreen": "rgb(46, 139, 87)",
    "seashell": "rgb(255, 245, 238)",
    "sienna": "rgb(160, 82, 45)",
    "silver": "rgb(192, 192, 192)",
    "skyblue": "rgb(135, 206, 235)",
    "slateblue": "rgb(106, 90, 205)",
    "slategray": "rgb(112, 128, 144)",
    "slategrey": "rgb(112, 128, 144)",
    "snow": "rgb(255, 250, 250)",
    "springgreen": "rgb(0, 255, 127)",
    "steelblue": "rgb(70, 130, 180)",
    "tan": "rgb(210, 180, 140)",
    "teal": "rgb(0, 128, 128)",
    "thistle": "rgb(216, 191, 216)",
    "tomato": "rgb(255, 99, 71)",
    "turquoise": "rgb(64, 224, 208)",
    "violet": "rgb(238, 130, 238)",
    "wheat": "rgb(245, 222, 179)",
    "white": "rgb(255, 255, 255)",
    "whitesmoke": "rgb(245, 245, 245)",
    "yellow": "rgb(255, 255, 0)",
    "yellowgreen": "rgb(154, 205, 50)",

    "activeborder": "#0000ff",
    "activecaption": "#0000ff",
    "appworkspace": "#ffffff",
    "background": "#ffffff",
    "buttonface": "#000000",
    "buttonhighlight": "#cccccc",
    "buttonshadow": "#333333",
    "buttontext": "#000000",
    "captiontext": "#000000",
    "graytext": "#333333",
    "highlight": "#0000ff",
    "highlighttext": "#cccccc",
    "inactiveborder": "#333333",
    "inactivecaption": "#cccccc",
    "inactivecaptiontext": "#333333",
    "infobackground": "#cccccc",
    "infotext": "#000000",
    "menu": "#cccccc",
    "menutext": "#333333",
    "scrollbar": "#cccccc",
    "threeddarkshadow": "#333333",
    "threedface": "#cccccc",
    "threedhighlight": "#ffffff",
    "threedlightshadow": "#333333",
    "threedshadow": "#333333",
    "window": "#cccccc",
    "windowframe": "#cccccc",
    "windowtext": "#000000"}


def color(string=None, opacity=1):
    """Replace ``string`` representing a color by a RGBA tuple."""
    if not string or string in ("none", "transparent"):
        return (0, 0, 0, 0)

    string = string.strip().lower()

    if string in COLORS:
        string = COLORS[string]

    if string.startswith("rgba"):
        r, g, b, a = tuple(
            float(i.strip(" %")) * 2.55 if "%" in i else float(i)
            for i in string.strip(" rgba()").split(","))
        return r / 255, g / 255, b / 255, a * opacity
    elif string.startswith("rgb"):
        r, g, b = tuple(
            float(i.strip(" %")) / 100 if "%" in i else float(i) / 255
            for i in string.strip(" rgb()").split(","))
        return r, g, b, opacity

    if len(string) in (4, 5):
        string = "#" + "".join(2 * char for char in string[1:])
    if len(string) == 9:
        opacity *= int(string[7:9], 16) / 255

    try:
        plain_color = tuple(
            int(value, 16) / 255. for value in (
                string[1:3], string[3:5], string[5:7]))
    except ValueError:
        # Unknown color, return black
        return (0, 0, 0, 1)
    else:
        return plain_color + (opacity,)

########NEW FILE########
__FILENAME__ = defs
# -*- coding: utf-8 -*-
# This file is part of CairoSVG
# Copyright © 2010-2012 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with CairoSVG.  If not, see <http://www.gnu.org/licenses/>.

"""
Externally defined elements managers.

This module handles gradients and patterns.

"""

from math import radians

from . import cairo
from .colors import color
from .helpers import node_format, preserve_ratio, paint, urls, transform
from .shapes import rect
from .units import size
from ..parser import Tree
from ..features import match_features


BLEND_OPERATORS = {
    "normal": 2,
    "multiply": 14,
    "screen": 15,
    "darken": 17,
    "lighten": 18}


def update_def_href(surface, def_name, def_dict):
    """Update the attributes of the def according to its href attribute."""
    def_node = def_dict[def_name]
    href = def_node.get("{http://www.w3.org/1999/xlink}href")
    if href and href[0] == "#" and href[1:] in def_dict:
        href_urls = urls(href)
        href_url = href_urls[0] if href_urls else None
        href_name = href_url[1:]
        if href_name in def_dict:
            update_def_href(surface, href_name, def_dict)
            href_node = def_dict[href_name]
            def_dict[def_name] = Tree(
                url="#%s" % def_name, parent=href_node,
                parent_children=(not def_node.children),
                tree_cache=surface.tree_cache)
            # Inherit attributes generally not inherited
            for key, value in href_node.items():
                if key not in def_dict[def_name]:
                    def_dict[def_name][key] = value


def parse_def(surface, node):
    """Parse the SVG definitions."""
    for def_type in (
            "marker", "gradient", "pattern", "path", "mask", "filter"):
        if def_type in node.tag.lower():
            getattr(surface, def_type + "s")[node["id"]] = node


def gradient_or_pattern(surface, node, name):
    """Gradient or pattern color."""
    if name in surface.gradients:
        update_def_href(surface, name, surface.gradients)
        return draw_gradient(surface, node, name)
    elif name in surface.patterns:
        update_def_href(surface, name, surface.patterns)
        return draw_pattern(surface, node, name)


def marker(surface, node):
    """Store a marker definition."""
    parse_def(surface, node)


def mask(surface, node):
    """Store a mask definition."""
    parse_def(surface, node)


def filter_(surface, node):
    """Store a filter definition."""
    parse_def(surface, node)


def linear_gradient(surface, node):
    """Store a linear gradient definition."""
    parse_def(surface, node)


def radial_gradient(surface, node):
    """Store a radial gradient definition."""
    parse_def(surface, node)


def pattern(surface, node):
    """Store a pattern definition."""
    parse_def(surface, node)


def clip_path(surface, node):
    """Store a clip path definition."""
    surface.paths[node["id"]] = node


def paint_mask(surface, node, name, opacity):
    """Paint the mask of the current surface."""
    mask_node = surface.masks[name]
    mask_node.tag = "g"
    mask_node["opacity"] = opacity

    if mask_node.get("maskUnits") == "userSpaceOnUse":
        width_ref, height_ref = "x", "y"
    else:
        x = size(surface, node.get("x"), "x")
        y = size(surface, node.get("y"), "y")
        width = size(surface, node.get("width"), "x")
        height = size(surface, node.get("height"), "y")
        width_ref = width
        height_ref = height
        mask_node["transform"] = "%s scale(%f, %f)" % (
            mask_node.get("transform", ""), width, height)

    mask_node["x"] = size(surface, mask_node.get("x", "-10%"), width_ref)
    mask_node["y"] = size(surface, mask_node.get("y", "-10%"), height_ref)
    mask_node["height"] = size(
        surface, mask_node.get("height", "120%"), width_ref)
    mask_node["width"] = size(
        surface, mask_node.get("width", "120%"), height_ref)

    if mask_node.get("maskUnits") == "userSpaceOnUse":
        x = mask_node["x"]
        y = mask_node["y"]
        mask_node["viewBox"] = "%f %f %f %f" % (
            mask_node["x"], mask_node["y"],
            mask_node["width"], mask_node["height"])

    from . import SVGSurface  # circular import
    mask_surface = SVGSurface(mask_node, None, surface.dpi, surface)
    surface.context.save()
    surface.context.translate(x, y)
    surface.context.scale(
        mask_node["width"] / mask_surface.width,
        mask_node["height"] / mask_surface.height)
    surface.context.mask_surface(mask_surface.cairo)
    surface.context.restore()


def draw_gradient(surface, node, name):
    """Gradients colors."""
    gradient_node = surface.gradients[name]

    transform(surface, gradient_node.get("gradientTransform"))

    if gradient_node.get("gradientUnits") == "userSpaceOnUse":
        width_ref, height_ref = "x", "y"
        diagonal_ref = "xy"
    else:
        x = size(surface, node.get("x"), "x")
        y = size(surface, node.get("y"), "y")
        width = size(surface, node.get("width"), "x")
        height = size(surface, node.get("height"), "y")
        width_ref = height_ref = diagonal_ref = 1

    if gradient_node.tag == "linearGradient":
        x1 = size(surface, gradient_node.get("x1", "0%"), width_ref)
        x2 = size(surface, gradient_node.get("x2", "100%"), width_ref)
        y1 = size(surface, gradient_node.get("y1", "0%"), height_ref)
        y2 = size(surface, gradient_node.get("y2", "0%"), height_ref)
        gradient_pattern = cairo.LinearGradient(x1, y1, x2, y2)

    elif gradient_node.tag == "radialGradient":
        r = size(surface, gradient_node.get("r", "50%"), diagonal_ref)
        cx = size(surface, gradient_node.get("cx", "50%"), width_ref)
        cy = size(surface, gradient_node.get("cy", "50%"), height_ref)
        fx = size(surface, gradient_node.get("fx", str(cx)), width_ref)
        fy = size(surface, gradient_node.get("fy", str(cy)), height_ref)
        gradient_pattern = cairo.RadialGradient(fx, fy, 0, cx, cy, r)

    if gradient_node.get("gradientUnits") != "userSpaceOnUse":
        gradient_pattern.set_matrix(cairo.Matrix(
            1 / width, 0, 0, 1 / height, - x / width, - y / height))
    gradient_pattern.set_extend(getattr(
        cairo, "EXTEND_%s" % node.get("spreadMethod", "pad").upper()))

    offset = 0
    for child in gradient_node.children:
        offset = max(offset, size(surface, child.get("offset"), 1))
        stop_color = color(
            child.get("stop-color", "black"),
            float(child.get("stop-opacity", 1)))
        gradient_pattern.add_color_stop_rgba(offset, *stop_color)

    gradient_pattern.set_extend(getattr(
        cairo, "EXTEND_%s" % gradient_node.get("spreadMethod", "pad").upper()))

    surface.context.set_source(gradient_pattern)
    return True


def draw_pattern(surface, node, name):
    """Draw a pattern image."""
    pattern_node = surface.patterns[name]
    pattern_node.tag = "g"
    transform(surface, pattern_node.get("patternTransform"))

    if pattern_node.get("viewBox"):
        if not (size(surface, pattern_node.get("width", 1), 1) and
                size(surface, pattern_node.get("height", 1), 1)):
            return False
    else:
        if not (size(surface, pattern_node.get("width", 0), 1) and
                size(surface, pattern_node.get("height", 0), 1)):
            return False

    if pattern_node.get("patternUnits") == "userSpaceOnUse":
        x = size(surface, pattern_node.get("x"), "x")
        y = size(surface, pattern_node.get("y"), "y")
        pattern_width = size(surface, pattern_node.get("width", 0), 1)
        pattern_height = size(surface, pattern_node.get("height", 0), 1)
    else:
        width = size(surface, node.get("width"), "x")
        height = size(surface, node.get("height"), "y")
        x = size(surface, pattern_node.get("x"), 1) * width
        y = size(surface, pattern_node.get("y"), 1) * height
        pattern_width = \
            size(surface, pattern_node.pop("width", "0"), 1) * width
        pattern_height = \
            size(surface, pattern_node.pop("height", "0"), 1) * height
        if "viewBox" not in pattern_node:
            pattern_node["width"] = pattern_width
            pattern_node["height"] = pattern_height
            if pattern_node.get("patternContentUnits") == "objectBoundingBox":
                pattern_node["transform"] = "scale(%s, %s)" % (width, height)
    from . import SVGSurface  # circular import
    pattern_surface = SVGSurface(pattern_node, None, surface.dpi, surface)
    pattern_pattern = cairo.SurfacePattern(pattern_surface.cairo)
    pattern_pattern.set_extend(cairo.EXTEND_REPEAT)
    pattern_pattern.set_matrix(cairo.Matrix(
        pattern_surface.width / pattern_width, 0, 0,
        pattern_surface.height / pattern_height, -x, -y))
    surface.context.set_source(pattern_pattern)
    return True


def draw_marker(surface, node, position="mid"):
    """Draw a marker."""
    if position == "start":
        node.markers = {
            "start": list(urls(node.get("marker-start", ""))),
            "mid": list(urls(node.get("marker-mid", ""))),
            "end": list(urls(node.get("marker-end", "")))}
        all_markers = list(urls(node.get("marker", "")))
        for markers_list in node.markers.values():
            markers_list.extend(all_markers)
    pending_marker = (
        surface.context.get_current_point(), node.markers[position])

    if position == "start":
        node.pending_markers.append(pending_marker)
        return
    elif position == "end":
        node.pending_markers.append(pending_marker)

    while node.pending_markers:
        next_point, markers = node.pending_markers.pop(0)
        angle1 = node.tangents.pop(0)
        angle2 = node.tangents.pop(0)

        if angle1 is None:
            angle1 = angle2

        for active_marker in markers:
            if not active_marker.startswith("#"):
                continue
            active_marker = active_marker[1:]
            if active_marker in surface.markers:
                marker_node = surface.markers[active_marker]

                angle = marker_node.get("orient", "0")
                if angle == "auto":
                    angle = float(angle1 + angle2) / 2
                else:
                    angle = radians(float(angle))

                temp_path = surface.context.copy_path()
                current_x, current_y = next_point

                if node.get("markerUnits") == "userSpaceOnUse":
                    base_scale = 1
                else:
                    base_scale = size(
                        surface, surface.parent_node.get("stroke-width"))

                # Returns 4 values
                scale_x, scale_y, translate_x, translate_y = \
                    preserve_ratio(surface, marker_node)

                width, height, viewbox = node_format(surface, marker_node)
                if viewbox:
                    viewbox_width = viewbox[2]
                    viewbox_height = viewbox[3]
                else:
                    viewbox_width = width or 0
                    viewbox_height = height or 0

                surface.context.new_path()
                for child in marker_node.children:
                    surface.context.save()
                    surface.context.translate(current_x, current_y)
                    surface.context.rotate(angle)
                    surface.context.scale(
                        base_scale / viewbox_width * float(scale_x),
                        base_scale / viewbox_height * float(scale_y))
                    surface.context.translate(translate_x, translate_y)
                    surface.draw(child)
                    surface.context.restore()
                surface.context.append_path(temp_path)

    if position == "mid":
        node.pending_markers.append(pending_marker)


def apply_filter_before(surface, node):
    if node["id"] in surface.masks:
        return

    names = urls(node.get("filter"))
    name = names[0][1:] if names else None
    if name in surface.filters:
        filter_node = surface.filters[name]
        for child in filter_node.children:
            # Offset
            if child.tag == "feOffset":
                if filter_node.get("primitiveUnits") == "objectBoundingBox":
                    width = size(surface, node.get("width"), "x")
                    height = size(surface, node.get("height"), "y")
                    dx = size(surface, child.get("dx", 0), 1) * width
                    dy = size(surface, child.get("dy", 0), 1) * height
                else:
                    dx = size(surface, child.get("dx", 0), 1)
                    dy = size(surface, child.get("dy", 0), 1)
                surface.context.translate(dx, dy)


def apply_filter_after(surface, node):
    surface.context.set_operator(BLEND_OPERATORS["normal"])

    if node["id"] in surface.masks:
        return

    names = urls(node.get("filter"))
    name = names[0][1:] if names else None
    if name in surface.filters:
        filter_node = surface.filters[name]
        for child in filter_node.children:
            # Blend
            if child.tag == "feBlend":
                surface.context.set_operator(BLEND_OPERATORS.get(
                    child.get("mode", "normal"), BLEND_OPERATORS["normal"]))
            # Flood
            elif child.tag == "feFlood":
                surface.context.new_path()
                if filter_node.get("primitiveUnits") == "objectBoundingBox":
                    x = size(surface, node.get("x"), "x")
                    y = size(surface, node.get("y"), "y")
                    width = size(surface, node.get("width"), "x")
                    height = size(surface, node.get("height"), "y")
                else:
                    x, y, width, height = 0, 0, 1, 1
                x += size(surface, child.get("x", 0), 1)
                y += size(surface, child.get("y", 0), 1)
                width *= size(surface, child.get("width", 0), 1)
                height *= size(surface, child.get("height", 0), 1)
                rect(surface, dict(x=x, y=y, width=width, height=height))
                surface.context.set_source_rgba(*color(
                    paint(child.get("flood-color"))[1],
                    float(child.get("flood-opacity", 1))))
                surface.context.fill()
                surface.context.new_path()


def use(surface, node):
    """Draw the content of another SVG file."""
    surface.context.save()
    surface.context.translate(
        size(surface, node.get("x"), "x"), size(surface, node.get("y"), "y"))
    if "x" in node:
        del node["x"]
    if "y" in node:
        del node["y"]
    if "viewBox" in node:
        del node["viewBox"]
    if "mask" in node:
        del node["mask"]
    href = node.get("{http://www.w3.org/1999/xlink}href")
    tree_urls = urls(href)
    url = tree_urls[0] if tree_urls else None
    tree = Tree(url=url, parent=node, tree_cache=surface.tree_cache)

    if not match_features(tree.xml_tree):
        return

    if tree.tag == "svg":
        # Explicitely specified
        # http://www.w3.org/TR/SVG11/struct.html#UseElement
        if "width" in node and "height" in node:
            tree["width"], tree["height"] = node["width"], node["height"]

    surface.set_context_size(*node_format(surface, tree))
    surface.draw(tree)
    node.pop("fill", None)
    node.pop("stroke", None)
    surface.context.restore()
    # Restore twice, because draw does not restore at the end of svg tags
    if tree.tag != "use":
        surface.context.restore()

########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-
# This file is part of CairoSVG
# Copyright © 2010-2012 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with CairoSVG.  If not, see <http://www.gnu.org/licenses/>.

"""
Surface helpers.

"""

from math import cos, sin, tan, atan2, radians

from . import cairo
from .units import size

# Python 2/3 management
# pylint: disable=C0103
try:
    Error = cairo.Error
except AttributeError:
    Error = SystemError
# pylint: enable=C0103


class PointError(Exception):
    """Exception raised when parsing a point fails."""


def distance(x1, y1, x2, y2):
    """Get the distance between two points."""
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


def paint(value):
    """Extract from value an uri and a color.

    See http://www.w3.org/TR/SVG/painting.html#SpecifyingPaint

    """
    if not value:
        return None, None

    value = value.strip()

    if value.startswith("url"):
        source = urls(value.split(")")[0])[0][1:]
        color = value.split(")", 1)[-1].strip() or None
    else:
        source = None
        color = value.strip() or None

    return (source, color)


def node_format(surface, node):
    """Return ``(width, height, viewbox)`` of ``node``."""
    width = size(surface, node.get("width"), "x")
    height = size(surface, node.get("height"), "y")
    viewbox = node.get("viewBox")
    if viewbox:
        viewbox = tuple(float(position) for position in viewbox.split())
        width = width or viewbox[2]
        height = height or viewbox[3]
    return width, height, viewbox


def normalize(string=None):
    """Normalize a string corresponding to an array of various values."""
    string = string.replace("-", " -")
    string = string.replace(",", " ")

    while "  " in string:
        string = string.replace("  ", " ")

    string = string.replace("e -", "e-")
    string = string.replace("E -", "E-")

    values = string.split(" ")
    string = ""
    for value in values:
        if value.count(".") > 1:
            numbers = value.split(".")
            string += "%s.%s " % (numbers.pop(0), numbers.pop(0))
            string += ".%s " % " .".join(numbers)
        else:
            string += value + " "

    return string.strip()


def point(surface, string=None):
    """Return ``(x, y, trailing_text)`` from ``string``."""
    if not string:
        return (0, 0, "")

    try:
        x, y, string = (string.strip() + " ").split(" ", 2)
    except ValueError:
        raise PointError("The point cannot be found in string %s" % string)

    return size(surface, x, "x"), size(surface, y, "y"), string


def point_angle(cx, cy, px, py):
    """Return angle between x axis and point knowing given center."""
    return atan2(py - cy, px - cx)


def preserve_ratio(surface, node):
    """Manage the ratio preservation."""
    if node.tag == "marker":
        scale_x = size(surface, node.get("markerWidth", "3"), "x")
        scale_y = size(surface, node.get("markerHeight", "3"), "y")
        translate_x = -size(surface, node.get("refX"))
        translate_y = -size(surface, node.get("refY"))
    elif node.tag in ("svg", "image"):
        width, height, _ = node_format(surface, node)
        scale_x = width / node.image_width
        scale_y = height / node.image_height

        align = node.get("preserveAspectRatio", "xMidYMid").split(" ")[0]
        if align == "none":
            return scale_x, scale_y, 0, 0
        else:
            mos_properties = node.get("preserveAspectRatio", "").split()
            meet_or_slice = (
                mos_properties[1] if len(mos_properties) > 1 else None)
            if meet_or_slice == "slice":
                scale_value = max(scale_x, scale_y)
            else:
                scale_value = min(scale_x, scale_y)
            scale_x = scale_y = scale_value

            x_position = align[1:4].lower()
            y_position = align[5:].lower()

            if x_position == "min":
                translate_x = 0

            if y_position == "min":
                translate_y = 0

            if x_position == "mid":
                translate_x = (width / scale_x - node.image_width) / 2.

            if y_position == "mid":
                translate_y = (height / scale_y - node.image_height) / 2.

            if x_position == "max":
                translate_x = width / scale_x - node.image_width

            if y_position == "max":
                translate_y = height / scale_y - node.image_height

    return scale_x, scale_y, translate_x, translate_y


def quadratic_points(x1, y1, x2, y2, x3, y3):
    """Return the quadratic points to create quadratic curves."""
    xq1 = x2 * 2 / 3 + x1 / 3
    yq1 = y2 * 2 / 3 + y1 / 3
    xq2 = x2 * 2 / 3 + x3 / 3
    yq2 = y2 * 2 / 3 + y3 / 3
    return xq1, yq1, xq2, yq2, x3, y3


def rotate(x, y, angle):
    """Rotate a point of an angle around the origin point."""
    return x * cos(angle) - y * sin(angle), y * cos(angle) + x * sin(angle)


def transform(surface, string):
    """Update ``surface`` matrix according to transformation ``string``."""
    if not string:
        return

    transformations = string.split(")")
    matrix = cairo.Matrix()
    for transformation in transformations:
        for ttype in ("scale", "translate", "matrix", "rotate", "skewX",
                      "skewY"):
            if ttype in transformation:
                transformation = transformation.replace(ttype, "")
                transformation = transformation.replace("(", "")
                transformation = normalize(transformation).strip() + " "
                values = []
                while transformation:
                    value, transformation = transformation.split(" ", 1)
                    # TODO: manage the x/y sizes here
                    values.append(size(surface, value))
                if ttype == "matrix":
                    matrix = cairo.Matrix(*values).multiply(matrix)
                elif ttype == "rotate":
                    angle = radians(float(values.pop(0)))
                    x, y = values or (0, 0)
                    matrix.translate(x, y)
                    matrix.rotate(angle)
                    matrix.translate(-x, -y)
                elif ttype == "skewX":
                    tangent = tan(radians(float(values[0])))
                    matrix = \
                        cairo.Matrix(1, 0, tangent, 1, 0, 0).multiply(matrix)
                elif ttype == "skewY":
                    tangent = tan(radians(float(values[0])))
                    matrix = \
                        cairo.Matrix(1, tangent, 0, 1, 0, 0).multiply(matrix)
                elif ttype == "translate":
                    if len(values) == 1:
                        values += (0,)
                    matrix.translate(*values)
                elif ttype == "scale":
                    if len(values) == 1:
                        values = 2 * values
                    matrix.scale(*values)
    apply_matrix_transform(surface, matrix)


def apply_matrix_transform(surface, matrix):
    try:
        matrix.invert()
    except Error:
        # Matrix not invertible, clip the surface to an empty path
        active_path = surface.context.copy_path()
        surface.context.new_path()
        surface.context.clip()
        surface.context.append_path(active_path)
    else:
        matrix.invert()
        surface.context.transform(matrix)


def urls(string):
    """Parse a comma-separated list of url() strings."""
    if not string:
        return []

    string = string.strip()
    if string.startswith("url"):
        string = string[3:]
    return [
        link.strip("() '\"") for link in string.rsplit(")")[0].split(",")
        if link.strip("() '\"")]


def rect(string):
    """Parse the rect value of a clip."""
    if not string:
        return []
    string = string.strip()
    if string.startswith("rect"):
        return string[4:].strip('() ').split(',')
    else:
        return []


def rotations(node):
    """Retrieves the original rotations of a `text` or `tspan` node."""
    if "rotate" in node:
        original_rotate = [
            float(i) for i in normalize(node["rotate"]).strip().split(" ")]
        return original_rotate
    return []


def pop_rotation(node, original_rotate, rotate):
    """Removes the rotations of a node that are already used."""
    node["rotate"] = " ".join(
        str(rotate.pop(0) if rotate else original_rotate[-1])
        for i in range(len(node.text)))


def zip_letters(xl, yl, dxl, dyl, rl, word):
    """Returns a list with the current letter's positions (x, y and rotation).
    E.g.: for letter 'L' with positions x = 10, y = 20 and rotation = 30:
    >>> [[10, 20, 30], 'L']

    Store the last value of each position and pop the first one in order to
    avoid setting an x,y or rotation value that have already been used.
    """
    return (
        ([pl.pop(0) if pl else None for pl in (xl, yl, dxl, dyl, rl)], char)
        for char in word)


def flatten(node):
    flattened_text = [node.text or ""]
    for child in list(node):
        flattened_text.append(flatten(child))
        flattened_text.append(child.tail or "")
        node.remove(child)
    return "".join(flattened_text)

########NEW FILE########
__FILENAME__ = image
# -*- coding: utf-8 -*-
# This file is part of CairoSVG
# Copyright © 2010-2012 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with CairoSVG.  If not, see <http://www.gnu.org/licenses/>.

"""
Images manager.

"""

import base64
import gzip
from io import BytesIO
try:
    from urllib import urlopen, unquote
    import urlparse
    unquote_to_bytes = lambda data: unquote(
        data.encode('ascii') if isinstance(data, unicode) else data)
except ImportError:
    from urllib.request import urlopen
    from urllib import parse as urlparse  # Python 3
    from urllib.parse import unquote_to_bytes

from . import cairo
from .helpers import node_format, size, preserve_ratio
from ..parser import Tree


def open_data_url(url):
    """Decode URLs with the 'data' scheme. urllib can handle them
    in Python 2, but that is broken in Python 3.

    Inspired from Python 2.7.2’s urllib.py.

    """
    # syntax of data URLs:
    # dataurl   := "data:" [ mediatype ] [ ";base64" ] "," data
    # mediatype := [ type "/" subtype ] *( ";" parameter )
    # data      := *urlchar
    # parameter := attribute "=" value
    try:
        header, data = url.split(",", 1)
    except ValueError:
        raise IOError("bad data URL")
    header = header[5:]  # len("data:") == 5
    if header:
        semi = header.rfind(";")
        if semi >= 0 and "=" not in header[semi:]:
            encoding = header[semi+1:]
        else:
            encoding = ""
    else:
        encoding = ""

    data = unquote_to_bytes(data)
    if encoding == "base64":
        missing_padding = 4 - len(data) % 4
        if missing_padding:
            data += b"=" * missing_padding
        return base64.decodestring(data)
    return data


def image(surface, node):
    """Draw an image ``node``."""
    url = node.get("{http://www.w3.org/1999/xlink}href")
    if not url:
        return
    if url.startswith("data:"):
        image_bytes = open_data_url(url)
    else:
        base_url = node.get("{http://www.w3.org/XML/1998/namespace}base")
        if base_url:
            url = urlparse.urljoin(base_url, url)
        if node.url:
            url = urlparse.urljoin(node.url, url)
        if urlparse.urlparse(url).scheme:
            input_ = urlopen(url)
        else:
            input_ = open(url, 'rb')  # filename
        image_bytes = input_.read()

    if len(image_bytes) < 5:
        return

    x, y = size(surface, node.get("x"), "x"), size(surface, node.get("y"), "y")
    width = size(surface, node.get("width"), "x")
    height = size(surface, node.get("height"), "y")
    surface.context.rectangle(x, y, width, height)
    surface.context.clip()

    if image_bytes[:4] == b"\x89PNG":
        png_file = BytesIO(image_bytes)
    elif (image_bytes[:5] in (b"<svg ", b"<?xml", b"<!DOC") or
            image_bytes[:2] == b"\x1f\x8b"):
        if image_bytes[:2] == b"\x1f\x8b":
            image_bytes = gzip.GzipFile(fileobj=BytesIO(image_bytes)).read()
        surface.context.save()
        surface.context.translate(x, y)
        if "x" in node:
            del node["x"]
        if "y" in node:
            del node["y"]
        if "viewBox" in node:
            del node["viewBox"]
        tree = Tree(
            url=url, bytestring=image_bytes, tree_cache=surface.tree_cache)
        tree_width, tree_height, viewbox = node_format(surface, tree)
        if not tree_width or not tree_height:
            tree_width = tree["width"] = width
            tree_height = tree["height"] = height
        node.image_width = tree_width or width
        node.image_height = tree_height or height
        scale_x, scale_y, translate_x, translate_y = \
            preserve_ratio(surface, node)
        surface.set_context_size(*node_format(surface, tree))
        surface.context.translate(*surface.context.get_current_point())
        surface.context.scale(scale_x, scale_y)
        surface.context.translate(translate_x, translate_y)
        surface.draw(tree)
        surface.context.restore()
        # Restore twice, because draw does not restore at the end of svg tags
        surface.context.restore()
        return
    else:
        try:
            from PIL import Image
            png_file = BytesIO()
            Image.open(BytesIO(image_bytes)).save(png_file, 'PNG')
            png_file.seek(0)
        except:
            # No way to handle the image
            return

    image_surface = cairo.ImageSurface.create_from_png(png_file)

    node.image_width = image_surface.get_width()
    node.image_height = image_surface.get_height()
    scale_x, scale_y, translate_x, translate_y = preserve_ratio(surface, node)

    surface.context.rectangle(x, y, width, height)
    pattern_pattern = cairo.SurfacePattern(image_surface)
    surface.context.save()
    surface.context.translate(*surface.context.get_current_point())
    surface.context.scale(scale_x, scale_y)
    surface.context.translate(translate_x, translate_y)
    surface.context.set_source(pattern_pattern)
    surface.context.fill()
    surface.context.restore()

########NEW FILE########
__FILENAME__ = path
# -*- coding: utf-8 -*-
# This file is part of CairoSVG
# Copyright © 2010-2012 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with CairoSVG.  If not, see <http://www.gnu.org/licenses/>.

"""
Paths manager.

"""

from math import pi, radians

from .defs import draw_marker
from .helpers import normalize, point, point_angle, quadratic_points, rotate
from .units import size


PATH_LETTERS = "achlmqstvzACHLMQSTVZ"
PATH_TAGS = (
    "circle", "ellipse", "line", "path", "polygon", "polyline", "rect")


def path(surface, node):
    """Draw a path ``node``."""
    string = node.get("d", "")

    if not string.strip():
        # Don't draw empty paths at all
        return

    draw_marker(surface, node, "start")

    for letter in PATH_LETTERS:
        string = string.replace(letter, " %s " % letter)

    last_letter = None
    string = normalize(string)

    while string:
        string = string.strip()
        if string.split(" ", 1)[0] in PATH_LETTERS:
            letter, string = (string + " ").split(" ", 1)
        elif letter == "M":
            letter = "L"
        elif letter == "m":
            letter = "l"

        if letter in "aA":
            # Elliptic curve
            x1, y1 = surface.context.get_current_point()
            rx, ry, string = point(surface, string)
            rotation, string = string.split(" ", 1)
            rotation = radians(float(rotation))

            # The large and sweep values are not always separated from the
            # following values, here is the crazy parser
            large, string = string[0], string[1:].strip()
            while not large[-1].isdigit():
                large, string = large + string[0], string[1:].strip()
            sweep, string = string[0], string[1:].strip()
            while not sweep[-1].isdigit():
                sweep, string = sweep + string[0], string[1:].strip()

            large, sweep = bool(int(large)), bool(int(sweep))

            x3, y3, string = point(surface, string)

            if letter == "A":
                # Absolute x3 and y3, convert to relative
                x3 -= x1
                y3 -= y1

            # rx=0 or ry=0 means straight line
            if not rx or not ry:
                string = "l %f %f %s" % (x3, y3, string)
                continue

            radii_ratio = ry / rx

            # Cancel the rotation of the second point
            xe, ye = rotate(x3, y3, -rotation)
            ye /= radii_ratio

            # Find the angle between the second point and the x axis
            angle = point_angle(0, 0, xe, ye)

            # Put the second point onto the x axis
            xe = (xe ** 2 + ye ** 2) ** .5
            ye = 0

            # Update the x radius if it is too small
            rx = max(rx, xe / 2)

            # Find one circle centre
            xc = xe / 2
            yc = (rx ** 2 - xc ** 2) ** .5

            # Choose between the two circles according to flags
            if not (large ^ sweep):
                yc = -yc

            # Define the arc sweep
            arc = \
                surface.context.arc if sweep else surface.context.arc_negative

            # Put the second point and the center back to their positions
            xe, ye = rotate(xe, 0, angle)
            xc, yc = rotate(xc, yc, angle)

            # Find the drawing angles
            angle1 = point_angle(xc, yc, 0, 0)
            angle2 = point_angle(xc, yc, xe, ye)

            # Store the tangent angles
            node.tangents.extend((-angle1, -angle2))

            # Draw the arc
            surface.context.save()
            surface.context.translate(x1, y1)
            surface.context.rotate(rotation)
            surface.context.scale(1, radii_ratio)
            arc(xc, yc, rx, angle1, angle2)
            surface.context.restore()

        elif letter == "c":
            # Relative curve
            x, y = surface.context.get_current_point()
            x1, y1, string = point(surface, string)
            x2, y2, string = point(surface, string)
            x3, y3, string = point(surface, string)
            node.tangents.extend((
                point_angle(x2, y2, x1, y1), point_angle(x2, y2, x3, y3)))
            surface.context.rel_curve_to(x1, y1, x2, y2, x3, y3)

            # Save absolute values for x and y, useful if next letter is s or S
            x1 += x
            x2 += x
            x3 += x
            y1 += y
            y2 += y
            y3 += y

        elif letter == "C":
            # Curve
            x1, y1, string = point(surface, string)
            x2, y2, string = point(surface, string)
            x3, y3, string = point(surface, string)
            node.tangents.extend((
                point_angle(x2, y2, x1, y1), point_angle(x2, y2, x3, y3)))
            surface.context.curve_to(x1, y1, x2, y2, x3, y3)

        elif letter == "h":
            # Relative horizontal line
            x, string = (string + " ").split(" ", 1)
            old_x, old_y = surface.context.get_current_point()
            angle = 0 if size(surface, x, "x") > 0 else pi
            node.tangents.extend((-angle, angle))
            surface.context.rel_line_to(size(surface, x, "x"), 0)

        elif letter == "H":
            # Horizontal line
            x, string = (string + " ").split(" ", 1)
            old_x, old_y = surface.context.get_current_point()
            angle = 0 if size(surface, x, "x") > old_x else pi
            node.tangents.extend((-angle, angle))
            surface.context.line_to(size(surface, x, "x"), old_y)

        elif letter == "l":
            # Relative straight line
            x, y, string = point(surface, string)
            angle = point_angle(0, 0, x, y)
            node.tangents.extend((-angle, angle))
            surface.context.rel_line_to(x, y)

        elif letter == "L":
            # Straight line
            x, y, string = point(surface, string)
            old_x, old_y = surface.context.get_current_point()
            angle = point_angle(old_x, old_y, x, y)
            node.tangents.extend((-angle, angle))
            surface.context.line_to(x, y)

        elif letter == "m":
            # Current point relative move
            x, y, string = point(surface, string)
            if surface.context.has_current_point():
                surface.context.rel_move_to(x, y)
            else:
                surface.context.move_to(x, y)

        elif letter == "M":
            # Current point move
            x, y, string = point(surface, string)
            surface.context.move_to(x, y)

        elif letter == "q":
            # Relative quadratic curve
            x1, y1 = 0, 0
            x2, y2, string = point(surface, string)
            x3, y3, string = point(surface, string)
            xq1, yq1, xq2, yq2, xq3, yq3 = quadratic_points(
                x1, y1, x2, y2, x3, y3)
            surface.context.rel_curve_to(xq1, yq1, xq2, yq2, xq3, yq3)
            node.tangents.extend((0, 0))

        elif letter == "Q":
            # Quadratic curve
            x1, y1 = surface.context.get_current_point()
            x2, y2, string = point(surface, string)
            x3, y3, string = point(surface, string)
            xq1, yq1, xq2, yq2, xq3, yq3 = quadratic_points(
                x1, y1, x2, y2, x3, y3)
            surface.context.curve_to(xq1, yq1, xq2, yq2, xq3, yq3)
            node.tangents.extend((0, 0))

        elif letter == "s":
            # Relative smooth curve
            x, y = surface.context.get_current_point()
            x1 = x3 - x2 if last_letter in "csCS" else 0
            y1 = y3 - y2 if last_letter in "csCS" else 0
            x2, y2, string = point(surface, string)
            x3, y3, string = point(surface, string)
            node.tangents.extend((
                point_angle(x2, y2, x1, y1), point_angle(x2, y2, x3, y3)))
            surface.context.rel_curve_to(x1, y1, x2, y2, x3, y3)

            # Save absolute values for x and y, useful if next letter is s or S
            x1 += x
            x2 += x
            x3 += x
            y1 += y
            y2 += y
            y3 += y

        elif letter == "S":
            # Smooth curve
            x, y = surface.context.get_current_point()
            x1 = x3 + (x3 - x2) if last_letter in "csCS" else x
            y1 = y3 + (y3 - y2) if last_letter in "csCS" else y
            x2, y2, string = point(surface, string)
            x3, y3, string = point(surface, string)
            node.tangents.extend((
                point_angle(x2, y2, x1, y1), point_angle(x2, y2, x3, y3)))
            surface.context.curve_to(x1, y1, x2, y2, x3, y3)

        elif letter == "t":
            # Relative quadratic curve end
            if last_letter not in "QqTt":
                x2, y2, x3, y3 = 0, 0, 0, 0
            elif last_letter in "QT":
                x2 -= x1
                y2 -= y1
                x3 -= x1
                y3 -= y1
            x2 = x3 - x2
            y2 = y3 - y2
            x1, y1 = 0, 0
            x3, y3, string = point(surface, string)
            xq1, yq1, xq2, yq2, xq3, yq3 = quadratic_points(
                x1, y1, x2, y2, x3, y3)
            node.tangents.extend((0, 0))
            surface.context.rel_curve_to(xq1, yq1, xq2, yq2, xq3, yq3)

        elif letter == "T":
            # Quadratic curve end
            abs_x, abs_y = surface.context.get_current_point()
            if last_letter not in "QqTt":
                x2, y2, x3, y3 = abs_x, abs_y, abs_x, abs_y
            elif last_letter in "qt":
                x2 += x1
                y2 += y1
            x2 = 2 * abs_x - x2
            y2 = 2 * abs_y - y2
            x1, y1 = abs_x, abs_y
            x3, y3, string = point(surface, string)
            xq1, yq1, xq2, yq2, xq3, yq3 = quadratic_points(
                x1, y1, x2, y2, x3, y3)
            node.tangents.extend((0, 0))
            surface.context.curve_to(xq1, yq1, xq2, yq2, xq3, yq3)

        elif letter == "v":
            # Relative vertical line
            y, string = (string + " ").split(" ", 1)
            old_x, old_y = surface.context.get_current_point()
            angle = pi / 2 if size(surface, y, "y") > 0 else -pi / 2
            node.tangents.extend((-angle, angle))
            surface.context.rel_line_to(0, size(surface, y, "y"))

        elif letter == "V":
            # Vertical line
            y, string = (string + " ").split(" ", 1)
            old_x, old_y = surface.context.get_current_point()
            angle = pi / 2 if size(surface, y, "y") > 0 else -pi / 2
            node.tangents.extend((-angle, angle))
            surface.context.line_to(old_x, size(surface, y, "y"))

        elif letter in "zZ":
            # End of path
            node.tangents.extend((0, 0))
            surface.context.close_path()

        string = string.strip()

        if string and letter not in "mMzZ":
            draw_marker(surface, node, "mid")

        last_letter = letter

    if node.tangents != [None]:
        # node.tangents == [None] means empty path
        node.tangents.append(node.tangents[-1])
        draw_marker(surface, node, "end")

########NEW FILE########
__FILENAME__ = shapes
# -*- coding: utf-8 -*-
# This file is part of CairoSVG
# Copyright © 2010-2012 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with CairoSVG.  If not, see <http://www.gnu.org/licenses/>.

"""
Shapes drawers.

"""

from math import pi

from .helpers import normalize, point, size


def circle(surface, node):
    """Draw a circle ``node`` on ``surface``."""
    r = size(surface, node.get("r"))
    if not r:
        return
    cx = size(surface, node.get("cx"), "x")
    cy = size(surface, node.get("cy"), "y")

    # Set "standard" values that may be used by gradients
    node["width"], node["height"] = str(r * 2), str(r * 2)
    node["x"], node["y"] = str(cx - r), str(cy - r)

    surface.context.new_sub_path()
    surface.context.arc(cx, cy, r, 0, 2 * pi)


def ellipse(surface, node):
    """Draw an ellipse ``node`` on ``surface``."""
    rx = size(surface, node.get("rx"), "x")
    ry = size(surface, node.get("ry"), "y")
    if not rx or not ry:
        return
    cx = size(surface, node.get("cx"), "x")
    cy = size(surface, node.get("cy"), "y")

    # Set "standard" values that may be used by gradients
    node["width"], node["height"] = str(rx * 2), str(ry * 2)
    node["x"], node["y"] = str(cx - rx), str(cy - ry)

    ratio = ry / rx
    surface.context.new_sub_path()
    surface.context.save()
    surface.context.scale(1, ratio)
    surface.context.arc(cx, cy / ratio, rx, 0, 2 * pi)
    surface.context.restore()


def line(surface, node):
    """Draw a line ``node``."""
    x1, y1, x2, y2 = tuple(
        size(surface, node.get(position), position[0])
        for position in ("x1", "y1", "x2", "y2"))
    surface.context.move_to(x1, y1)
    surface.context.line_to(x2, y2)


def polygon(surface, node):
    """Draw a polygon ``node`` on ``surface``."""
    polyline(surface, node)
    surface.context.close_path()


def polyline(surface, node):
    """Draw a polyline ``node``."""
    points = normalize(node.get("points"))
    if points:
        x, y, points = point(surface, points)
        surface.context.move_to(x, y)
        while points:
            x, y, points = point(surface, points)
            surface.context.line_to(x, y)


def rect(surface, node):
    """Draw a rect ``node`` on ``surface``."""
    x, y = size(surface, node.get("x"), "x"), size(surface, node.get("y"), "y")
    width = size(surface, node.get("width"), "x")
    height = size(surface, node.get("height"), "y")
    rx = node.get("rx")
    ry = node.get("ry")
    if rx and ry is None:
        ry = rx
    elif ry and rx is None:
        rx = ry
    rx = size(surface, rx, "x")
    ry = size(surface, ry, "y")

    if rx == 0 or ry == 0:
        surface.context.rectangle(x, y, width, height)
    else:
        if rx > width / 2.:
            rx = width / 2.
        if ry > height / 2.:
            ry = height / 2.

        # Inspired by Cairo Cookbook
        # http://cairographics.org/cookbook/roundedrectangles/
        ARC_TO_BEZIER = 4 * (2 ** .5 - 1) / 3
        c1 = ARC_TO_BEZIER * rx
        c2 = ARC_TO_BEZIER * ry

        surface.context.new_path()
        surface.context.move_to(x + rx, y)
        surface.context.rel_line_to(width - 2 * rx, 0)
        surface.context.rel_curve_to(c1, 0, rx, c2, rx, ry)
        surface.context.rel_line_to(0, height - 2 * ry)
        surface.context.rel_curve_to(0, c2, c1 - rx, ry, -rx, ry)
        surface.context.rel_line_to(-width + 2 * rx, 0)
        surface.context.rel_curve_to(-c1, 0, -rx, -c2, -rx, -ry)
        surface.context.rel_line_to(0, -height + 2 * ry)
        surface.context.rel_curve_to(0, -c2, rx - c1, -ry, rx, -ry)
        surface.context.close_path()

########NEW FILE########
__FILENAME__ = svg
# -*- coding: utf-8 -*-
# This file is part of CairoSVG
# Copyright © 2010-2012 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with CairoSVG.  If not, see <http://www.gnu.org/licenses/>.

"""
Root tag drawer.

"""

from .helpers import preserve_ratio, node_format
from .units import size


def svg(surface, node):
    """Draw a svg ``node``."""
    width, height, viewbox = node_format(surface, node)
    if viewbox:
        rect_x, rect_y = viewbox[0:2]
        node.image_width = viewbox[2]
        node.image_height = viewbox[3]
    else:
        rect_x, rect_y = 0, 0
        node.image_width = size(surface, node.get("width"), "x")
        node.image_height = size(surface, node.get("height"), "y")

    if node.parent is None:
        return

    if node.get("preserveAspectRatio", "none") != "none":
        scale_x, scale_y, translate_x, translate_y = \
            preserve_ratio(surface, node)
        rect_width, rect_height = width, height
    else:
        scale_x, scale_y, translate_x, translate_y = (1, 1, 0, 0)
        rect_width, rect_height = node.image_width, node.image_height
    surface.context.translate(*surface.context.get_current_point())
    surface.context.rectangle(rect_x, rect_y, rect_width, rect_height)
    surface.context.clip()
    surface.context.scale(scale_x, scale_y)
    surface.context.translate(translate_x, translate_y)

########NEW FILE########
__FILENAME__ = tags
# -*- coding: utf-8 -*-
# This file is part of CairoSVG
# Copyright © 2010-2012 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with CairoSVG.  If not, see <http://www.gnu.org/licenses/>.

"""
SVG tags functions.

"""

from .defs import (
    clip_path, filter_, linear_gradient, marker, mask, pattern,
    radial_gradient, use)
from .image import image
from .path import path
from .shapes import circle, ellipse, line, polygon, polyline, rect
from .svg import svg
from .text import text

TAGS = {
    "a": text,
    "circle": circle,
    "clipPath": clip_path,
    "ellipse": ellipse,
    "filter": filter_,
    "image": image,
    "line": line,
    "linearGradient": linear_gradient,
    "marker": marker,
    "mask": mask,
    "path": path,
    "pattern": pattern,
    "polyline": polyline,
    "polygon": polygon,
    "radialGradient": radial_gradient,
    "rect": rect,
    "svg": svg,
    "text": text,
    "textPath": text,
    "tspan": text,
    "use": use}

########NEW FILE########
__FILENAME__ = text
# -*- coding: utf-8 -*-
# This file is part of CairoSVG
# Copyright © 2010-2012 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with CairoSVG.  If not, see <http://www.gnu.org/licenses/>.

"""
Text drawers.

"""

from math import cos, sin, radians

# Python 2/3 management
# pylint: disable=E0611
# pylint: enable=E0611

from . import cairo
from .helpers import distance, normalize, point_angle, zip_letters
from .units import size


def path_length(path):
    """Get the length of ``path``."""
    total_length = 0
    for item in path:
        if item[0] == cairo.PATH_MOVE_TO:
            old_point = item[1]
        elif item[0] == cairo.PATH_LINE_TO:
            new_point = item[1]
            length = distance(
                old_point[0], old_point[1], new_point[0], new_point[1])
            total_length += length
            old_point = new_point
    return total_length


def point_following_path(path, width):
    """Get the point at ``width`` distance on ``path``."""
    total_length = 0
    for item in path:
        if item[0] == cairo.PATH_MOVE_TO:
            old_point = item[1]
        elif item[0] == cairo.PATH_LINE_TO:
            new_point = item[1]
            length = distance(
                old_point[0], old_point[1], new_point[0], new_point[1])
            total_length += length
            if total_length < width:
                old_point = new_point
            else:
                length -= total_length - width
                angle = point_angle(
                    old_point[0], old_point[1], new_point[0], new_point[1])
                x = cos(angle) * length + old_point[0]
                y = sin(angle) * length + old_point[1]
                return x, y


def text(surface, node):
    """Draw a text ``node``."""
    # Set black as default text color
    if not node.get("fill"):
        node["fill"] = "#000000"

    font_size = size(surface, node.get("font-size", "12pt"))
    font_family = (node.get("font-family") or "sans-serif").split(",")[0]
    font_style = getattr(
        cairo, ("font_slant_%s" % node.get("font-style")).upper(),
        cairo.FONT_SLANT_NORMAL)
    font_weight = getattr(
        cairo, ("font_weight_%s" % node.get("font-weight")).upper(),
        cairo.FONT_WEIGHT_NORMAL)
    surface.context.select_font_face(font_family, font_style, font_weight)
    surface.context.set_font_size(font_size)
    ascent, descent, _, max_x_advance, max_y_advance = (
        surface.context.font_extents())

    text_path_href = (
        node.get("{http://www.w3.org/1999/xlink}href", "") or
        node.parent.get("{http://www.w3.org/1999/xlink}href", ""))
    text_path = surface.paths.get(text_path_href.lstrip("#"))
    letter_spacing = size(surface, node.get("letter-spacing"))
    x_bearing, y_bearing, width, height = (
        surface.context.text_extents(node.text)[:4])

    x, y, dx, dy, rotate = [], [], [], [], [0]
    if "x" in node:
        x = [size(surface, i, "x")
             for i in normalize(node["x"]).strip().split(" ")]
    if "y" in node:
        y = [size(surface, i, "y")
             for i in normalize(node["y"]).strip().split(" ")]
    if "dx" in node:
        dx = [size(surface, i, "x")
              for i in normalize(node["dx"]).strip().split(" ")]
    if "dy" in node:
        dy = [size(surface, i, "y")
              for i in normalize(node["dy"]).strip().split(" ")]
    if "rotate" in node:
        rotate = [radians(float(i)) if i else 0
                  for i in normalize(node["rotate"]).strip().split(" ")]
    last_r = rotate[-1]
    letters_positions = zip_letters(x, y, dx, dy, rotate, node.text)

    text_anchor = node.get("text-anchor")
    if text_anchor == "middle":
        x_align = width / 2. + x_bearing
    elif text_anchor == "end":
        x_align = width + x_bearing
    else:
        x_align = 0

    # XXX This is a hack. The rest of the baseline alignment
    # tags of the SVG 1.1 spec (section 10.9.2) are
    # not supported. We only try to align things
    # that look like Western horizontal fonts.
    # Finally, we add a "display-anchor" attribute
    # for aligning the specific text rather than the
    # font baseline.
    # Nonetheless, there are times when one needs to align
    # text vertically, and this will at least make that
    # possible.
    if max_x_advance > 0 and max_y_advance == 0:
        display_anchor = node.get("display-anchor")
        alignment_baseline = node.get("alignment-baseline")
        if display_anchor == "middle":
            y_align = -height / 2.0 - y_bearing
        elif display_anchor == "top":
            y_align = -y_bearing
        elif display_anchor == "bottom":
            y_align = -height - y_bearing
        elif (alignment_baseline == "central" or
              alignment_baseline == "middle"):
            # XXX This is wrong--Cairo gives no reasonable access
            # to x-height information, so we use font top-to-bottom
            y_align = (ascent + descent) / 2.0 - descent
        elif (alignment_baseline == "text-before-edge" or
              alignment_baseline == "before_edge" or
              alignment_baseline == "top" or
              alignment_baseline == "text-top"):
            y_align = ascent
        elif (alignment_baseline == "text-after-edge" or
              alignment_baseline == "after_edge" or
              alignment_baseline == "bottom" or
              alignment_baseline == "text-bottom"):
            y_align = -descent
        else:
            y_align = 0

    if text_path:
        surface.stroke_and_fill = False
        surface.draw(text_path)
        surface.stroke_and_fill = True
        cairo_path = surface.context.copy_path_flat()
        surface.context.new_path()
        start_offset = size(
            surface, node.get("startOffset", 0), path_length(cairo_path))
        surface.text_path_width += start_offset
        x1, y1 = point_following_path(cairo_path, surface.text_path_width)

    if node.text:
        for [x, y, dx, dy, r], letter in letters_positions:
            if x:
                surface.cursor_d_position[0] = 0
            if y:
                surface.cursor_d_position[1] = 0
            surface.cursor_d_position[0] += dx or 0
            surface.cursor_d_position[1] += dy or 0
            extents = surface.context.text_extents(letter)[4]
            surface.context.save()
            if text_path:
                surface.text_path_width += extents + letter_spacing
                point_on_path = point_following_path(
                    cairo_path,
                    surface.text_path_width + surface.cursor_d_position[0])
                if point_on_path:
                    x2, y2 = point_on_path
                else:
                    continue
                surface.context.translate(x1, y1)
                surface.context.rotate(point_angle(x1, y1, x2, y2))
                surface.context.translate(0, surface.cursor_d_position[1])
                surface.context.move_to(0, 0)
                x1, y1 = x2, y2
            else:
                x = surface.cursor_position[0] if x is None else x
                y = surface.cursor_position[1] if y is None else y
                surface.context.move_to(x + letter_spacing, y)
                cursor_position = x + letter_spacing + extents, y
                surface.context.rel_move_to(*surface.cursor_d_position)
                surface.context.rel_move_to(-x_align, y_align)
                surface.context.rotate(last_r if r is None else r)

            surface.context.text_path(letter)
            surface.context.restore()
            if not text_path:
                surface.cursor_position = cursor_position
    else:
        x = x[0] if x else surface.cursor_position[0]
        y = y[0] if y else surface.cursor_position[1]
        dx = dx[0] if dx else 0
        dy = dy[0] if dy else 0
        surface.cursor_position = (x + dx, y + dy)

########NEW FILE########
__FILENAME__ = units
# -*- coding: utf-8 -*-
# This file is part of CairoSVG
# Copyright © 2010-2012 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with CairoSVG.  If not, see <http://www.gnu.org/licenses/>.

"""
Units functions.

"""


UNITS = {
    "mm": 1 / 25.4,
    "cm": 1 / 2.54,
    "in": 1,
    "pt": 1 / 72.,
    "pc": 1 / 6.,
    "px": None}


def size(surface, string, reference="xy"):
    """Replace a ``string`` with units by a float value.

    If ``reference`` is a float, it is used as reference for percentages. If it
    is ``'x'``, we use the viewport width as reference. If it is ``'y'``, we
    use the viewport height as reference. If it is ``'xy'``, we use
    ``(viewport_width ** 2 + viewport_height ** 2) ** .5 / 2 ** .5`` as
    reference.

    """
    if not string:
        return 0.

    try:
        return float(string)
    except ValueError:
        # Not a float, try something else
        pass

    if "%" in string:
        if reference == "x":
            reference = surface.context_width or 0
        elif reference == "y":
            reference = surface.context_height or 0
        elif reference == "xy":
            reference = (
                (surface.context_width ** 2 + surface.context_height ** 2)
                ** .5 / 2 ** .5)
        return float(string.strip(" %")) * reference / 100
    elif "em" in string:
        return surface.font_size * float(string.strip(" em"))
    elif "ex" in string:
        # Assume that 1em == 2ex
        return surface.font_size * float(string.strip(" ex")) / 2

    for unit, coefficient in UNITS.items():
        if unit in string:
            number = float(string.strip(" " + unit))
            return number * (surface.dpi * coefficient if coefficient else 1)

    # Try to return the number at the beginning of the string
    return_string = ""
    while string and (string[0].isdigit() or string[0] in "+-."):
        return_string += string[0]
        string = string[1:]

    # Unknown size or multiple sizes
    return float(return_string or 0)

########NEW FILE########
__FILENAME__ = cairosvg
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of CairoSVG
# Copyright © 2010-2012 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with CairoSVG.  If not, see <http://www.gnu.org/licenses/>.

"""
CairoSVG entry point.

"""

import cairosvg
cairosvg.main()

########NEW FILE########
__FILENAME__ = generate
#!/usr/bin/env python2

import os
import fontforge

for filename in os.listdir("."):
    font, extension = os.path.splitext(filename)
    if extension == ".svg":
        print("Generating %s" % font)
        try:
            fontforge.open("%s.svg" % font).generate("%s.otf" % font)
        except:
            pass

########NEW FILE########
