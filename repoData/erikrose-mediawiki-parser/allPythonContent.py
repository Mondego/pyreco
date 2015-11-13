__FILENAME__ = apostrophes
"""
MediaWiki-style markup; from py-wikimarkup

Copyright (C) 2008 David Cramer <dcramer@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.

"""
import re

_quotePat = re.compile(u"(''+)", re.UNICODE)

default_tags = {'bold': '<strong>',
                'bold_close': '</strong>',
                'italic': '<em>',
                'italic_close': '</em>'}


def parse_one_line(text, tags=default_tags):
        arr = _quotePat.split(text.strip())
        if len(arr) == 1:
            return text

        # First, do some preliminary work. This may shift some apostrophes from
        # being mark-up to being text. It also counts the number of occurrences
        # of bold and italics mark-ups.
        numBold = numItalics = 0
        for i, r in enumerate(arr):
            if i % 2:
                l = len(r)
                if l == 4:
                    arr[i-1] += u"'"
                    arr[i] = u"'''"
                elif l > 5:
                    arr[i-1] += u"'" * (len(arr[i]) - 5)
                    arr[i] = u"'''''"
                if l == 2:
                    numItalics += 1
                elif l == 3:
                    numBold += 1
                elif l == 5:
                    numItalics += 1
                    numBold += 1

        # If there is an odd number of both bold and italics, it is likely
        # that one of the bold ones was meant to be an apostrophe followed
        # by italics. Which one we cannot know for certain, but it is more
        # likely to be one that has a single-letter word before it.
        if numBold % 2 and numItalics % 2:
            firstSingleLetterWord = firstMultiLetterWord = firstSpace = -1
            for i, r in enumerate(arr):
                if i % 2 and len(r) == 3:
                    x1 = arr[i-1][-1:]
                    x2 = arr[i-1][-2:-1]
                    if x1 == u' ':
                        if firstSpace == -1:
                            firstSpace = i
                    elif x2 == u' ':
                        if firstSingleLetterWord == -1:
                            firstSingleLetterWord = i
                    elif firstMultiLetterWord == -1:
                        firstMultiLetterWord = i

            # If there is a single-letter word, use it!
            if firstSingleLetterWord > -1:
                arr[firstSingleLetterWord] = u"''"
                arr[firstSingleLetterWord - 1] += u"'"
            # If not, but there's a multi-letter word, use that one.
            elif firstMultiLetterWord > -1:
                arr[firstMultiLetterWord] = u"''"
                arr[firstMultiLetterWord - 1] += u"'"
            # ... otherwise use the first one that has neither.
            # (notice that it is possible for all three to be -1 if, for example,
            # there is only one pentuple-apostrophe in the line)
            elif firstSpace > -1:
                arr[firstSpace] = u"''"
                arr[firstSpace - 1] += u"'"

        # Now let's actually convert our apostrophic mush to HTML!
        output = []
        buffer = []
        state = ''
        for i, r in enumerate(arr):
            if not i % 2:
                if state == 'both':
                    buffer.append(r)
                else:
                    output.append(r)
            else:
                if len(r) == 2:
                    if state == 'i':
                        output.append(tags['italic_close'])
                        state = ''
                    elif state == 'bi':
                        output.append(tags['italic_close'])
                        state = 'b'
                    elif state == 'ib':
                        output.append(tags['bold_close']+tags['italic_close']+tags['bold'])
                        state = 'b'
                    elif state == 'both':
                        output.append(tags['bold']+tags['italic'])
                        output.append(u''.join(buffer))
                        output.append(tags['italic_close'])
                        state = 'b'
                    else: # ''
                        output.append(tags['italic'])
                        state += 'i'
                elif len(r) == 3:
                    if state == 'b':
                        output.append(tags['bold_close'])
                        state = ''
                    elif state == 'bi':
                        output.append(tags['italic_close']+tags['bold_close']+tags['italic'])
                        state = 'i'
                    elif state == 'ib':
                        output.append(tags['bold_close'])
                        state = 'i'
                    elif state == 'both':
                        output.append(tags['italic']+tags['bold'])
                        output.append(u''.join(buffer))
                        output.append(tags['bold_close'])
                        state = 'i'
                    else: # ''
                        output.append(tags['bold'])
                        state += 'b'
                elif len(r) == 5:
                    if state == 'b':
                        output.append(tags['bold_close']+tags['italic'])
                        state = 'i'
                    elif state == 'i':
                        output.append(tags['italic_close']+tags['bold'])
                        state = 'b'
                    elif state == 'bi':
                        output.append(tags['italic_close']+tags['bold_close'])
                        state = ''
                    elif state == 'ib':
                        output.append(tags['bold_close']+tags['italic_close'])
                        state = ''
                    elif state == 'both':
                        output.append(tags['italic']+tags['bold'])
                        output.append(u''.join(buffer))
                        output.append(tags['bold_close']+tags['italic_close'])
                        state = ''
                    else: # ''
                        buffer = []
                        state = 'both'

        if state == 'b' or state == 'ib':
            output.append(tags['bold_close'])
        if state == 'i' or state == 'bi' or state == 'ib':
            output.append(tags['italic_close'])
        if state == 'bi':
            output.append(tags['bold_close'])
        if state == 'both' and buffer != []:
            output.append(tags['italic']+tags['bold'])
            output.append(u''.join(buffer))
            output.append(tags['bold_close']+tags['italic_close'])
        return u''.join(output)


def parse(text, tags=default_tags):
    lines = text.split(u'\n')
    return u'\n'.join(parse_one_line(line, tags) for line in lines)

########NEW FILE########
__FILENAME__ = config
output = 'html'

########NEW FILE########
__FILENAME__ = constants
# Different from html5lib.constants.entities in that (1) some of these are
# supported with variations of case, (2) this lacks &apos;, for which there's a
# complicated discussion at http://www.mail-archive.com/mediawiki-
# cvs@lists.wikimedia.org/msg01907.html.
#
# These are current as of MW 1.16.0.
html_entities = {
    u'Aacute':     193,
    u'aacute':     225,
    u'Acirc':      194,
    u'acirc':      226,
    u'acute':      180,
    u'AElig':      198,
    u'aelig':      230,
    u'Agrave':     192,
    u'agrave':     224,
    u'alefsym':    8501,
    u'Alpha':      913,
    u'alpha':      945,
    u'amp':        38,
    u'and':        8743,
    u'ang':        8736,
    u'Aring':      197,
    u'aring':      229,
    u'asymp':      8776,
    u'Atilde':     195,
    u'atilde':     227,
    u'Auml':       196,
    u'auml':       228,
    u'bdquo':      8222,
    u'Beta':       914,
    u'beta':       946,
    u'brvbar':     166,
    u'bull':       8226,
    u'cap':        8745,
    u'Ccedil':     199,
    u'ccedil':     231,
    u'cedil':      184,
    u'cent':       162,
    u'Chi':        935,
    u'chi':        967,
    u'circ':       710,
    u'clubs':      9827,
    u'cong':       8773,
    u'copy':       169,
    u'crarr':      8629,
    u'cup':        8746,
    u'curren':     164,
    u'dagger':     8224,
    u'Dagger':     8225,
    u'darr':       8595,
    u'dArr':       8659,
    u'deg':        176,
    u'Delta':      916,
    u'delta':      948,
    u'diams':      9830,
    u'divide':     247,
    u'Eacute':     201,
    u'eacute':     233,
    u'Ecirc':      202,
    u'ecirc':      234,
    u'Egrave':     200,
    u'egrave':     232,
    u'empty':      8709,
    u'emsp':       8195,
    u'ensp':       8194,
    u'Epsilon':    917,
    u'epsilon':    949,
    u'equiv':      8801,
    u'Eta':        919,
    u'eta':        951,
    u'ETH':        208,
    u'eth':        240,
    u'Euml':       203,
    u'euml':       235,
    u'euro':       8364,
    u'exist':      8707,
    u'fnof':       402,
    u'forall':     8704,
    u'frac12':     189,
    u'frac14':     188,
    u'frac34':     190,
    u'frasl':      8260,
    u'Gamma':      915,
    u'gamma':      947,
    u'ge':         8805,
    u'gt':         62,
    u'harr':       8596,
    u'hArr':       8660,
    u'hearts':     9829,
    u'hellip':     8230,
    u'Iacute':     205,
    u'iacute':     237,
    u'Icirc':      206,
    u'icirc':      238,
    u'iexcl':      161,
    u'Igrave':     204,
    u'igrave':     236,
    u'image':      8465,
    u'infin':      8734,
    u'int':        8747,
    u'Iota':       921,
    u'iota':       953,
    u'iquest':     191,
    u'isin':       8712,
    u'Iuml':       207,
    u'iuml':       239,
    u'Kappa':      922,
    u'kappa':      954,
    u'Lambda':     923,
    u'lambda':     955,
    u'lang':       9001,
    u'laquo':      171,
    u'larr':       8592,
    u'lArr':       8656,
    u'lceil':      8968,
    u'ldquo':      8220,
    u'le':         8804,
    u'lfloor':     8970,
    u'lowast':     8727,
    u'loz':        9674,
    u'lrm':        8206,
    u'lsaquo':     8249,
    u'lsquo':      8216,
    u'lt':         60,
    u'macr':       175,
    u'mdash':      8212,
    u'micro':      181,
    u'middot':     183,
    u'minus':      8722,
    u'Mu':         924,
    u'mu':         956,
    u'nabla':      8711,
    u'nbsp':       160,
    u'ndash':      8211,
    u'ne':         8800,
    u'ni':         8715,
    u'not':        172,
    u'notin':      8713,
    u'nsub':       8836,
    u'Ntilde':     209,
    u'ntilde':     241,
    u'Nu':         925,
    u'nu':         957,
    u'Oacute':     211,
    u'oacute':     243,
    u'Ocirc':      212,
    u'ocirc':      244,
    u'OElig':      338,
    u'oelig':      339,
    u'Ograve':     210,
    u'ograve':     242,
    u'oline':      8254,
    u'Omega':      937,
    u'omega':      969,
    u'Omicron':    927,
    u'omicron':    959,
    u'oplus':      8853,
    u'or':         8744,
    u'ordf':       170,
    u'ordm':       186,
    u'Oslash':     216,
    u'oslash':     248,
    u'Otilde':     213,
    u'otilde':     245,
    u'otimes':     8855,
    u'Ouml':       214,
    u'ouml':       246,
    u'para':       182,
    u'part':       8706,
    u'permil':     8240,
    u'perp':       8869,
    u'Phi':        934,
    u'phi':        966,
    u'Pi':         928,
    u'pi':         960,
    u'piv':        982,
    u'plusmn':     177,
    u'pound':      163,
    u'prime':      8242,
    u'Prime':      8243,
    u'prod':       8719,
    u'prop':       8733,
    u'Psi':        936,
    u'psi':        968,
    u'quot':       34,
    u'radic':      8730,
    u'rang':       9002,
    u'raquo':      187,
    u'rarr':       8594,
    u'rArr':       8658,
    u'rceil':      8969,
    u'rdquo':      8221,
    u'real':       8476,
    u'reg':        174,
    u'rfloor':     8971,
    u'Rho':        929,
    u'rho':        961,
    u'rlm':        8207,
    u'rsaquo':     8250,
    u'rsquo':      8217,
    u'sbquo':      8218,
    u'Scaron':     352,
    u'scaron':     353,
    u'sdot':       8901,
    u'sect':       167,
    u'shy':        173,
    u'Sigma':      931,
    u'sigma':      963,
    u'sigmaf':     962,
    u'sim':        8764,
    u'spades':     9824,
    u'sub':        8834,
    u'sube':       8838,
    u'sum':        8721,
    u'sup':        8835,
    u'sup1':       185,
    u'sup2':       178,
    u'sup3':       179,
    u'supe':       8839,
    u'szlig':      223,
    u'Tau':        932,
    u'tau':        964,
    u'there4':     8756,
    u'Theta':      920,
    u'theta':      952,
    u'thetasym':   977,
    u'thinsp':     8201,
    u'THORN':      222,
    u'thorn':      254,
    u'tilde':      732,
    u'times':      215,
    u'trade':      8482,
    u'Uacute':     218,
    u'uacute':     250,
    u'uarr':       8593,
    u'uArr':       8657,
    u'Ucirc':      219,
    u'ucirc':      251,
    u'Ugrave':     217,
    u'ugrave':     249,
    u'uml':        168,
    u'upsih':      978,
    u'Upsilon':    933,
    u'upsilon':    965,
    u'Uuml':       220,
    u'uuml':       252,
    u'weierp':     8472,
    u'Xi':         926,
    u'xi':         958,
    u'Yacute':     221,
    u'yacute':     253,
    u'yen':        165,
    u'Yuml':       376,
    u'yuml':       255,
    u'Zeta':       918,
    u'zeta':       950,
    u'zwj':        8205,
    u'zwnj':       8204
}

########NEW FILE########
__FILENAME__ = html
from constants import html_entities
from pijnu.library.node import Nil, Nodes, Node
from mediawiki_parser import wikitextParser
import apostrophes

def toolset(allowed_tags, allowed_autoclose_tags, allowed_attributes, interwiki, namespaces):
    tags_stack = []

    external_autonumber = []
    """ This is for the autonumbering of external links.
    e.g.: "[http://www.mozilla.org] [http://fr.wikipedia.org]"
    is rendered as: "<a href="...">[1]</a> <a href="...">[2]</a>
    """

    category_links = []
    """ This will contain the links to the categories of the article. """
    interwiki_links = []
    """ This will contain the links to the foreign versions of the article. """

    for namespace, value in namespaces.iteritems():
        assert value in range(16), "Incorrect value for namespaces"
    """
    Predefined namespaces; source: includes/Defines.php of MediaWiki-1.17.0
    'NS_MAIN', 0
    'NS_TALK', 1
    'NS_USER', 2
    'NS_USER_TALK', 3
    'NS_PROJECT', 4
    'NS_PROJECT_TALK', 5
    'NS_FILE', 6
    'NS_FILE_TALK', 7
    'NS_MEDIAWIKI', 8
    'NS_MEDIAWIKI_TALK', 9
    'NS_TEMPLATE', 10
    'NS_TEMPLATE_TALK', 11
    'NS_HELP', 12
    'NS_HELP_TALK', 13
    'NS_CATEGORY', 14
    'NS_CATEGORY_TALK', 15 
    """

    def balance_tags(tag=None):
        i = 0
        if tag is not None:
            try:
                i = tags_stack.index(tag, -1)
            except ValueError:
                return ''
        result = ''
        while len(tags_stack) > i:
            result += '</%s>' % tags_stack.pop()
        return result

    def content(node):
        return apostrophes.parse('%s' % node.leaf() + balance_tags())

    def render_title1(node):
        node.value = '<h1>' + content(node) +  '</h1>\n'

    def render_title2(node):
        node.value = '<h2>' + content(node) +  '</h2>\n'

    def render_title3(node):
        node.value = '<h3>' + content(node) +  '</h3>\n'

    def render_title4(node):
        node.value = '<h4>' + content(node) +  '</h4>\n'

    def render_title5(node):
        node.value = '<h5>' + content(node) +  '</h5>\n'

    def render_title6(node):
        node.value = '<h6>' + content(node) +  '</h6>\n'

    def render_raw_text(node):
        node.value = "%s" % node.leaf()

    def render_paragraph(node):
        value = content(node)
        if value != '':
            node.value = '<p>' + value +  '</p>\n'

    def render_wikitext(node):
        node.value = content(node)

    def render_body(node):
        metadata = ''
        if category_links != []:
            metadata += '<p>Categories: ' + ', '.join(category_links) + '</p>\n'
        if interwiki_links != []:
            metadata += '<p>Interwiki: ' + ', '.join(interwiki_links) + '</p>\n'
        node.value = '<body>\n' + content(node) + metadata + '</body>'

    def render_entity(node):
        value = '%s' % node.leaf()
        if value in html_entities:
            node.value = '%s' % unichr(html_entities[value])
        else:
            node.value = '&amp;%s;' % value

    def render_lt(node):
        node.value = '&lt;'

    def render_gt(node):
        node.value = '&gt;'

    def process_attribute(node, allowed_tag):
        assert len(node.value) == 2, "Bad AST shape!"
        attribute_name = node.value[0].value
        attribute_value = node.value[1].value
        if attribute_name in allowed_attributes or not allowed_tag:
            return '%s="%s"' % (attribute_name, attribute_value)
        return ''

    def process_attributes(node, allowed_tag):
        result = ''
        if len(node.value) == 1:
            pass
        elif len(node.value) == 2:
            attributes = node.value[1].value
            for i in range(len(attributes)):
                attribute = process_attribute(attributes[i], allowed_tag)
                if attribute is not '':
                    result += ' ' + attribute 
        else:
            raise Exception("Bad AST shape!")
        return result

    def render_attribute(node):
        node.value = process_attribute(node, True)

    def render_tag_open(node):
        tag_name = node.value[0].value
        if tag_name in allowed_autoclose_tags:
            render_tag_autoclose(node)
        elif tag_name in allowed_tags:
            attributes = process_attributes(node, True)
            tags_stack.append(tag_name)
            node.value = '<%s%s>' % (tag_name, attributes) 
        else:
            attributes = process_attributes(node, False)
            node.value = '&lt;%s%s&gt;' % (tag_name, attributes)

    def render_tag_close(node):
        tag_name = node.value[0].value
        if tag_name in allowed_autoclose_tags:
            render_tag_autoclose(node)
        elif tag_name in allowed_tags:
            node.value = balance_tags(tag_name)
        else:
            node.value = "&lt;/%s&gt;" % tag_name

    def render_tag_autoclose(node):
        tag_name = node.value[0].value
        if tag_name in allowed_autoclose_tags:
            attributes = process_attributes(node, True)
            node.value = '<%s%s />' % (tag_name, attributes) 
        else:
            attributes = process_attributes(node, False)
            node.value = '&lt;%s%s /&gt;' % (tag_name, attributes)

    def render_table(node):
        table_parameters = ''
        table_content = ''
        if isinstance(node.value, Nodes) and node.value[0].tag == 'table_begin':
            attributes = node.value[0].value[0]
            for attribute in attributes:
                if attribute.tag == 'HTML_attribute' and attribute.value != '':
                    table_parameters += ' ' + attribute.value
            contents = node.value[1].value
            for item in contents:
                table_content += content(item)
        else:
            table_content = content(node)
        node.value = '<table%s>\n<tr>\n%s</tr>\n</table>\n' % (table_parameters, table_content)

    def render_cell_content(node):
        if isinstance(node.value, Nil):
            return None
        cell_parameters = ''
        cell_content = ''
        if len(node.value) > 1:
            values = node.value[0].value
            for value in values:
                if isinstance(value, Node):
                    if value.tag == 'HTML_attribute' and value.value != '':
                        cell_parameters += ' ' + value.value
                    else:
                        cell_content += value.leaf()
                else:
                    cell_content += value
            cell_content += content(node.value[1])
        else:
            cell_content = content(node)
        return (cell_parameters, cell_content)

    def render_table_header_cell(node):
        result = ''
        if isinstance(node.value, Nodes):
            for i in range(len(node.value)):
                content = render_cell_content(node.value[i])
                result += '\t<th%s>%s</th>\n' % content
        else:
            content = render_cell_content(node)
            result = '\t<th%s>%s</th>\n' % content            
        if result != '':
            node.value = result

    def render_table_normal_cell(node):
        result = ''
        if isinstance(node.value, Nodes):
            for i in range(len(node.value)):
                content = render_cell_content(node.value[i])
                result += '\t<td%s>%s</td>\n' % content
        else:
            content = render_cell_content(node)
            result = '\t<td%s>%s</td>\n' % content            
        if result != '':
            node.value = result

    def render_table_empty_cell(node):
        node.value = '\t<td></td>\n'

    def render_table_caption(node):
        content = render_cell_content(node)
        if content is not None:
            node.value = '\t<caption%s>%s</caption>\n' % content

    def render_table_line_break(node):
        line_parameters = ''
        if node.value != '':
            assert len(node.value) == 1, "Bad AST shape!"
            parameters = node.value[0].value
            for value in parameters:
                if value.tag == 'HTML_attribute' and value.value != '':
                    line_parameters += ' ' + value.value
        node.value = '</tr>\n<tr%s>\n' % line_parameters

    def render_preformatted(node):
        node.value = '<pre>' + content(node) +  '</pre>\n'

    def render_hr(node):
        node.value = '<hr />\n'

    def render_ul(list):
        result = '<ul>\n'
        for i in range(len(list)):
            result += '\t<li>' + content(list[i]) +  '</li>\n'
        result += '</ul>\n'
        return result

    def render_ol(list):
        result = '<ol>\n'
        for i in range(len(list)):
            result += '\t<li>' + content(list[i]) +  '</li>\n'
        result += '</ol>\n'
        return result

    def render_dd(list):
        result = '<dl>\n'
        for i in range(len(list)):
            result += '\t<dd>' + content(list[i]) +  '</dd>\n'
        result += '</dl>\n'
        return result

    def render_dt(list):
        result = '<dl>\n'
        for i in range(len(list)):
            result += '\t<dt>' + content(list[i]) +  '</dt>\n'
        result += '</dl>\n'
        return result

    def collapse_list(list):
        i = 0
        while i+1 < len(list):
            if list[i].tag == 'bullet_list_leaf' and list[i+1].tag == '@bullet_sub_list@' or \
               list[i].tag == 'number_list_leaf' and list[i+1].tag == '@number_sub_list@' or \
               list[i].tag == 'colon_list_leaf' and list[i+1].tag == '@colon_sub_list@' or \
               list[i].tag == 'semi_colon_list_leaf' and list[i+1].tag == '@semi_colon_sub_list@':
                list[i].value.append(list[i+1].value[0])
                list.pop(i+1)
            else:
                i += 1
        for i in range(len(list)):
            if isinstance(list[i].value, Nodes):
                collapse_list(list[i].value)

    def select_items(nodes, i, value):
        list_tags = ['bullet_list_leaf', 'number_list_leaf', 'colon_list_leaf', 'semi_colon_list_leaf']
        list_tags.remove(value)
        if isinstance(nodes[i].value, Nodes):
            render_lists(nodes[i].value)
        items = [nodes[i]]
        while i + 1 < len(nodes) and nodes[i+1].tag not in list_tags:
            if isinstance(nodes[i+1].value, Nodes):
                render_lists(nodes[i+1].value)
            items.append(nodes.pop(i+1))
        return items

    def render_lists(list):
        i = 0
        while i < len(list):
            if list[i].tag == 'bullet_list_leaf' or list[i].tag == '@bullet_sub_list@':
                list[i].value = render_ul(select_items(list, i, 'bullet_list_leaf'))
            elif list[i].tag == 'number_list_leaf' or list[i].tag == '@number_sub_list@':
                list[i].value = render_ol(select_items(list, i, 'number_list_leaf'))
            elif list[i].tag == 'colon_list_leaf' or list[i].tag == '@colon_sub_list@':
                list[i].value = render_dd(select_items(list, i, 'colon_list_leaf'))
            elif list[i].tag == 'semi_colon_list_leaf' or list[i].tag == '@semi_colon_sub_list@':
                list[i].value = render_dt(select_items(list, i, 'semi_colon_list_leaf'))
            i += 1

    def render_list(node):
        assert isinstance(node.value, Nodes), "Bad AST shape!"
        collapse_list(node.value)
        render_lists(node.value)

    def render_url(node):
        node.value = '<a href="%s">%s</a>' % (node.leaf(), node.leaf())

    def render_external_link(node):
        if len(node.value) == 1:
            external_autonumber.append(node.leaf())
            node.value = '<a href="%s">[%s]</a>' % (node.leaf(), len(external_autonumber))
        else:
            text = node.value[1].leaf()
            node.value = '<a href="%s">%s</a>' % (node.value[0].leaf(), text)

    def render_interwiki(prefix, page):
        link = '<a href="%s">%s</a>' % (interwiki[prefix] + page, page)
        if link not in interwiki_links:
            interwiki_links.append(link)

    def render_category(category_name):
        link = '<a href="%s">%s</a>' % (category_name, category_name)
        if link not in category_links:
            category_links.append(link)

    def render_file(file_name, arguments):
        """ This implements a basic handling of images.
        MediaWiki supports much more parameters (see includes/Parser.php).
        """
        style = ''
        thumbnail = False
        legend = ''
        if arguments != []:
            parameters = arguments[0].value
            for parameter in parameters:
                parameter = '%s' % parameter.leaf()
                if parameter[-2:] == 'px':
                    size = parameter[0:-2]
                    if 'x' in size:
                        size_x, size_y = size.split('x', 1)
                        try:
                            size_x = int(size_x)
                            size_y = int(size_y)
                            style += 'width:%spx;height:%spx' % (size_x, size_y)
                        except:
                            legend = parameter
                    else:
                        try:
                            size_x = int(size)
                            style += 'width:%spx;' % size_x
                        except:
                            legend = parameter
                elif parameter in ['left', 'right', 'center']:
                    style += 'float:%s;' % parameter
                elif parameter in ['thumb', 'thumbnail']:
                    thumbnail = True
                elif parameter == 'border':
                    style += 'border:1px solid grey'
                else:
                    legend = parameter
        result = '<img src="%s" style="%s" alt="" />' % (file_name, style)
        if thumbnail:
            result = '<div class="thumbnail">%s<p>%s</p></div>\n' % (result, legend)
        return result

    def render_internal_link(node):
        force_link = False
        url = ''
        page_name = node.value.pop(0).value
        if page_name[0] == ':':
            force_link = True
            page_name = page_name[1:]
        if ':' in page_name:
            namespace, page_name = page_name.split(':', 1)
            if namespace in interwiki and not force_link:
                render_interwiki(namespace, page_name)
                node.value = ''
                return
            elif namespace in interwiki:
                url = interwiki[namespace]
                namespace = ''
            if namespace in namespaces:
                if namespaces[namespace] == 6 and not force_link:  # File
                    node.value = render_file(page_name, node.value)
                    return
                elif namespaces[namespace] == 14 and not force_link:  # Category
                    render_category(page_name)
                    node.value = ''
                    return
            if namespace:
                page_name = namespace + ':' + page_name
        if len(node.value) == 0:
            text = page_name
        else:
            text = '|'.join('%s' % item.leaf() for item in node.value[0])
        node.value = '<a href="%s%s">%s</a>' % (url, page_name, text)

    return locals()

def make_parser(allowed_tags=[], allowed_autoclose_tags=[], allowed_attributes=[], interwiki={}, namespaces={}):
    """Constructs the parser for the HTML backend.
    
    :arg allowed_tags: List of the HTML tags that should be allowed in the parsed wikitext.
            Opening tags will be closed. Closing tags with no opening tag will be removed.
            All the tags that are not in the list will be output as &lt;tag&gt;.
    :arg allowed_autoclose_tags: List of the self-closing tags that should be allowed in the
            parsed wikitext. All the other self-closing tags will be output as &lt;tag /&gt;
    :arg allowed_attributes: List of the HTML attributes that should be allowed in the parsed
            tags (e.g.: class="", style=""). All the other attributes (e.g.: onclick="") will
            be removed.
    :arg interwiki: List of the allowed interwiki prefixes (en, fr, es, commons, etc.)
    :arg namespaces: List of the namespaces of the wiki (File, Category, Template, etc.),
            including the localized version of those strings (Modele, Categorie, etc.),
            associated to the corresponding namespace code.
    """
    tools = toolset(allowed_tags, allowed_autoclose_tags, allowed_attributes, interwiki, namespaces)
    return wikitextParser.make_parser(tools)

########NEW FILE########
__FILENAME__ = parser
# -*- coding: utf8 -*-

import time
start_time = time.time()

# get the parser
from pijnu import makeParser
preprocessorGrammar = file("preprocessor.pijnu").read()
makeParser(preprocessorGrammar)

mediawikiGrammar = file("mediawiki.pijnu").read()
makeParser(mediawikiGrammar)

allowed_tags = ['p', 'span', 'b', 'i', 'small', 'center']
allowed_autoclose_tags = ['br', 'hr']
allowed_parameters = ['class', 'style', 'name', 'id', 'scope']
interwiki = {'ar': 'http://ar.wikipedia.org/wiki/',
             'az': 'http://az.wikipedia.org/wiki/',
             'br': 'http://br.wikipedia.org/wiki/',
             'ca': 'http://ca.wikipedia.org/wiki/',
             'cs': 'http://cs.wikipedia.org/wiki/',
             'da': 'http://da.wikipedia.org/wiki/',
             'de': 'http://de.wikipedia.org/wiki/',
             'en': 'http://en.wikipedia.org/wiki/',
             'eo': 'http://eo.wikipedia.org/wiki/',
             'es': 'http://es.wikipedia.org/wiki/',
             'fr': 'http://fr.wikipedia.org/wiki/'}

namespaces = {'Template':   10,
              u'Catégorie': 14,
              'Category':   14,
              'File':        6,
              'Fichier':     6,
              'Image':       6}
templates = {'listen': u"""{| style="text-align:center; background: #f9f9f9; color: #000;font-size:90%; line-height:1.1em; float:right;clear:right; margin:1em 1.5em 1em 1em; width:300px; border: 1px solid #aaa; padding: 0.1em;" cellspacing="7"
! class="media audio" style="background-color:#ccf; line-height:3.1em" | Fichier audio
|-
|<span style="height:20px; width:100%; padding:4pt; padding-left:0.3em; line-height:2em;" cellspacing="0">'''[[Media:{{{filename|{{{nomfichier|{{{2|}}}}}}}}}|{{{title|{{{titre|{{{1|}}}}}}}}}]]''' ''([[:Fichier:{{{filename|{{{nomfichier|{{{2|}}}}}}}}}|info]])''<br /><small>{{{suitetexte|{{{description|}}}}}}</small>
<center>[[Fichier:{{{filename|{{{nomfichier|{{{2|}}}}}}}}}|noicon]]</center></span><br /><span style="height:20px; width:100%; padding-left:0.3em;" cellspacing="0"><span title="Des difficultés pour écouter le fichier ?">[[Image:Circle question mark.png|14px|link=Aide:Écouter des sons ogg|Des difficultés  pour  écouter le fichier ?]] ''[[Aide:Écouter des sons ogg|Des problèmes pour écouter le fichier ?]]''</span>
|}
""",
            '3e': '3<sup>e</sup>'}

from preprocessor import make_parser
preprocessor = make_parser(templates)

from html import make_parser
parser = make_parser(allowed_tags, allowed_autoclose_tags, allowed_parameters, interwiki, namespaces)

# import the source in a utf-8 string
import codecs
fileObj = codecs.open("wikitext.txt", "r", "utf-8")
source = fileObj.read()

# The last line of the file will not be parsed correctly if
# there is no newline at the end of file, so, we add one.
if source[-1] != '\n':
  source += '\n'

preprocessed_text = preprocessor.parse(source)
tree = parser.parse(preprocessed_text.leaves())

output = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="fr">
<head><title>Test!</title></head>""" + tree.leaves() + "</html>"

file("article.htm", "w").write(output.encode('UTF-8'))

end_time = time.time()
print "Parsed and rendered in", end_time - start_time, "s."
########NEW FILE########
__FILENAME__ = preprocessor
from constants import html_entities

templates = {}
parsed_templates = {}  # Caches templates, to accelerate and avoid infinite loops

def substitute_named_entity(node):
    value = '%s' % node.leaf()
    if value in html_entities and value not in ['lt', 'gt']:
        node.value = unichr(html_entities[value])
    else:
        node.value = '&%s;' % value

def substitute_numbered_entity(node):
    try:
        value = int(node.leaf())
        # We eliminate some characters such as < and >
        if value in [60, 62]:
            raise Exception()
        node.value = unichr(value)
    except:
        node.value = '&#%s;' % value

def substitute_template_parameter(node, values={}):
    assert len(node.value) > 0, "Bad AST shape!"
    parameter_id = node.value[0].value
    if parameter_id in values:
        node.value = values[parameter_id]
    else:
        if len(node.value) > 1:
            # This is the default value
            node.value = node.value[1].value
        else:
            # No value at all: display the name of the parameter
            node.value = '{{{%s}}}' %  parameter_id

def substitute_template(node):
    node_to_str = '%s' % node
    if node_to_str in parsed_templates:
        if parsed_templates[node_to_str] is not None:
            result = parsed_templates[node_to_str]
        else:
            result = 'Infinite template call detected!'
    else:
        parsed_templates[node_to_str] = None
        if len(node.value) > 0:
            page_name = node.value[0].value
            count = 0
            parameters = {}
            if len(node.value) > 1:
                for parameter in node.value[1].value:
                    if isinstance(parameter.value, unicode) or \
                       isinstance(parameter.value, str) or \
                       len(parameter.value) == 1:
                        # It is a standalone parameter
                        count += 1 
                        parameters['%s' % count] = parameter.value
                    elif len(parameter.value) == 2 and \
                         parameter.value[0].tag == 'parameter_name' and \
                         parameter.value[1].tag == 'parameter_value':
                        parameter_name = parameter.value[0].value
                        parameter_value = parameter.value[1].value
                        parameters['%s' % parameter_name] = parameter_value
                    else:
                        raise Exception("Bad AST shape!")
            if page_name in templates:
                template = parse_template(templates[page_name], parameters)
                result = '%s' % template
            else:
                # FIXME: should be a link to page_name if page_name begins with a namespace
                # that is valid for this wiki or to Template:page_name otherwise
                result = '[[Template:%s]]' % page_name
        else:
            result = '{{}}'
    node.value = result
    parsed_templates[node_to_str] = result

toolset = {'substitute_template': substitute_template,
           'substitute_template_parameter': substitute_template_parameter,
           'substitute_named_entity': substitute_named_entity,
           'substitute_numbered_entity': substitute_numbered_entity}

from mediawiki_parser import preprocessorParser

def make_parser(template_dict):
    global templates
    templates = template_dict
    global parsed_templates
    parsed_templates = {}
    return preprocessorParser.make_parser(toolset)

def parse_template(template, parameters):
    def subst_param(node):
        substitute_template_parameter(node, parameters)

    toolset['substitute_template_parameter'] = subst_param
    parser = preprocessorParser.make_parser(toolset)
    result = parser.parse(template)
    
    # We reinitialize this so that we won't pollute other templates with our values
    toolset['substitute_template_parameter'] = substitute_template_parameter
    return result.value

########NEW FILE########
__FILENAME__ = preprocessorParser
""" preprocessor
<definition>
# Codes

    LF                      : '
'
    CR                      : '
'
    EOL                     : LF / CR
    TAB                     : "	"
    L_BRACKET               : "["
    R_BRACKET               : "\]"
    L_BRACE                 : "{"                                                                   : drop
    R_BRACE                 : "}"                                                                   : drop
    SPACE                   : " "                                                                   : drop
    SPACETAB                : SPACE / TAB                                                           : drop
    SPACETABEOL             : SPACE / TAB / EOL                                                     : drop
    PIPE                    : "|"                                                                   : drop
    BANG                    : "!"                                                                   : drop
    EQUAL                   : "="                                                                   : drop
    LT                      : "<"                                                                   : drop
    GT                      : ">"                                                                   : drop
    HASH                    : "#"                                                                   : drop
    DASH                    : "-"                                                                   : drop
    AMP                     : "&"                                                                   : drop
    SEMICOLON               : ";"                                                                   : drop
    TEMPLATE_BEGIN          : L_BRACE{2}                                                            : drop
    TEMPLATE_END            : R_BRACE{2}                                                            : drop
    PARAMETER_BEGIN         : L_BRACE{3}                                                            : drop
    PARAMETER_END           : R_BRACE{3}                                                            : drop

# Predefined tags

    NOWIKI_BEGIN            : "<nowiki>"
    NOWIKI_END              : "</nowiki>"
    PRE_BEGIN               : "<pre>"
    PRE_END                 : "</pre>"
    special_tag             : NOWIKI_BEGIN/NOWIKI_END/PRE_BEGIN/PRE_END

# Characters

    any_char                : [\x20..\xff] / '/'
    esc_char                : L_BRACKET/R_BRACKET/PIPE/L_BRACE/R_BRACE/LT/GT/AMP/SEMICOLON
    raw_char                : !esc_char any_char
    raw_text                : (raw_char / TAB)+                                                     : join

# HTML comments
# HTML comments are totally ignored and do not appear in the final text

    comment_content         : ((!(DASH{2} GT) [\x20..\xff])+ / SPACETABEOL)*
    html_comment            : LT BANG DASH{2} comment_content DASH{2} GT                            : drop

# Text

    page_name               : raw_char+                                                             : join

# Template parameters
# Those parameters should be substituted by their value when the current page is a template
# or by their optional default value in any case

    parameter_id            : raw_char+                                                             : join
    parameter_value         : inline?                                                               : keep
    optional_default_value  : (PIPE SPACETABEOL* parameter_value)? SPACETABEOL*                     : liftNode
    template_parameter      : PARAMETER_BEGIN parameter_id optional_default_value PARAMETER_END     : substitute_template_parameter

# Links

    LINK_PIPE               : PIPE                                                                  : restore
    internal_link           : L_BRACKET{2} inline (LINK_PIPE inline)* R_BRACKET{2}                  : join
    external_link           : L_BRACKET inline (SPACE inline)* R_BRACKET                            : join
    link                    : internal_link / external_link

# Templates

    value_content           : (inline / (!(SPACETABEOL* (TEMPLATE_END / PIPE)) (any_char / EOL)))*  : keep
    parameter_value         : value_content SPACETABEOL*
    optional_value          : parameter_value?
    parameter_equal         : SPACETABEOL* EQUAL SPACETABEOL*
    parameter_name          : (!(esc_char/parameter_equal) raw_char)+                               : join
    named_parameter         : parameter_name parameter_equal optional_value
    standalone_parameter    : value_content?                                                        : join
    parameter               : SPACETABEOL* PIPE SPACETABEOL* (named_parameter/standalone_parameter) : liftValue
    parameters              : parameter*
    template                : TEMPLATE_BEGIN page_name parameters SPACETABEOL* TEMPLATE_END         : substitute_template

# inline allows to have templates/links inside templates/links

    structure               : link / template / template_parameter
    inline                  : (structure / raw_text)+                                               : @
    numbered_entity         : AMP HASH [0..9]+ SEMICOLON                                            : substitute_numbered_entity
    named_entity            : AMP [a..zA..Z]+ SEMICOLON                                             : substitute_named_entity
    entity                  : named_entity / numbered_entity

# Pre and nowiki tags
# Preformatted acts like nowiki (disables wikitext parsing)
# We allow any char without parsing them as long as the tag is not closed

    pre_text                : (!PRE_END any_char)*                                                  : join
    preformatted            : PRE_BEGIN pre_text PRE_END                                            : liftValue
    eol_to_space            : EOL*                                                                  : replace_by_space
    nowiki_text             : (!NOWIKI_END (any_char/eol_to_space))*                                : join
    nowiki                  : NOWIKI_BEGIN nowiki_text NOWIKI_END                                   : liftValue

# Text types

    styled_text             : template / template_parameter / entity
    not_styled_text         : html_comment / preformatted / nowiki
    allowed_char            : esc_char{1}                                                           : restore liftValue
    allowed_text            : raw_text / allowed_char
    wikitext                : (not_styled_text / styled_text / allowed_text / EOL)+                 : join

"""

from pijnu.library import *


def make_parser(actions=None):
    """Return a parser.

    The parser's toolset functions are (optionally) augmented (or overridden)
    by a map of additional ones passed in.

    """
    if actions is None:
        actions = {}

    # Start off with the imported pijnu library functions:
    toolset = globals().copy()

    parser = Parser()
    state = parser.state

### title: preprocessor ###
    
    
    def toolset_from_grammar():
        """Return a map of toolset functions hard-coded into the grammar."""
    ###   <toolset>
        def replace_by_space(node):
            node.value = ' '
        
    
        return locals().copy()
    
    toolset.update(toolset_from_grammar())
    toolset.update(actions)
    
    ###   <definition>
    # recursive pattern(s)
    inline = Recursive(name='inline')
    # Codes
    
    LF = Char('\n', expression="'\n'", name='LF')
    CR = Char('\n', expression="'\n'", name='CR')
    EOL = Choice([LF, CR], expression='LF / CR', name='EOL')
    TAB = Word('\t', expression='"\t"', name='TAB')
    L_BRACKET = Word('[', expression='"["', name='L_BRACKET')
    R_BRACKET = Word(']', expression='"\\]"', name='R_BRACKET')
    L_BRACE = Word('{', expression='"{"', name='L_BRACE')(toolset['drop'])
    R_BRACE = Word('}', expression='"}"', name='R_BRACE')(toolset['drop'])
    SPACE = Word(' ', expression='" "', name='SPACE')(toolset['drop'])
    SPACETAB = Choice([SPACE, TAB], expression='SPACE / TAB', name='SPACETAB')(toolset['drop'])
    SPACETABEOL = Choice([SPACE, TAB, EOL], expression='SPACE / TAB / EOL', name='SPACETABEOL')(toolset['drop'])
    PIPE = Word('|', expression='"|"', name='PIPE')(toolset['drop'])
    BANG = Word('!', expression='"!"', name='BANG')(toolset['drop'])
    EQUAL = Word('=', expression='"="', name='EQUAL')(toolset['drop'])
    LT = Word('<', expression='"<"', name='LT')(toolset['drop'])
    GT = Word('>', expression='">"', name='GT')(toolset['drop'])
    HASH = Word('#', expression='"#"', name='HASH')(toolset['drop'])
    DASH = Word('-', expression='"-"', name='DASH')(toolset['drop'])
    AMP = Word('&', expression='"&"', name='AMP')(toolset['drop'])
    SEMICOLON = Word(';', expression='";"', name='SEMICOLON')(toolset['drop'])
    TEMPLATE_BEGIN = Repetition(L_BRACE, numMin=2, numMax=2, expression='L_BRACE{2}', name='TEMPLATE_BEGIN')(toolset['drop'])
    TEMPLATE_END = Repetition(R_BRACE, numMin=2, numMax=2, expression='R_BRACE{2}', name='TEMPLATE_END')(toolset['drop'])
    PARAMETER_BEGIN = Repetition(L_BRACE, numMin=3, numMax=3, expression='L_BRACE{3}', name='PARAMETER_BEGIN')(toolset['drop'])
    PARAMETER_END = Repetition(R_BRACE, numMin=3, numMax=3, expression='R_BRACE{3}', name='PARAMETER_END')(toolset['drop'])
    
    # Predefined tags
    
    NOWIKI_BEGIN = Word('<nowiki>', expression='"<nowiki>"', name='NOWIKI_BEGIN')
    NOWIKI_END = Word('</nowiki>', expression='"</nowiki>"', name='NOWIKI_END')
    PRE_BEGIN = Word('<pre>', expression='"<pre>"', name='PRE_BEGIN')
    PRE_END = Word('</pre>', expression='"</pre>"', name='PRE_END')
    special_tag = Choice([NOWIKI_BEGIN, NOWIKI_END, PRE_BEGIN, PRE_END], expression='NOWIKI_BEGIN/NOWIKI_END/PRE_BEGIN/PRE_END', name='special_tag')
    
    # Characters
    
    any_char = Choice([Klass(u' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff', expression='[\\x20..\\xff]'), Char('/', expression="'/'")], expression="[\\x20..\\xff] / '/'", name='any_char')
    esc_char = Choice([L_BRACKET, R_BRACKET, PIPE, L_BRACE, R_BRACE, LT, GT, AMP, SEMICOLON], expression='L_BRACKET/R_BRACKET/PIPE/L_BRACE/R_BRACE/LT/GT/AMP/SEMICOLON', name='esc_char')
    raw_char = Sequence([NextNot(esc_char, expression='!esc_char'), any_char], expression='!esc_char any_char', name='raw_char')
    raw_text = Repetition(Choice([raw_char, TAB], expression='raw_char / TAB'), numMin=1, numMax=False, expression='(raw_char / TAB)+', name='raw_text')(toolset['join'])
    
    # HTML comments
    # HTML comments are totally ignored and do not appear in the final text
    
    comment_content = Repetition(Choice([Repetition(Sequence([NextNot(Sequence([Repetition(DASH, numMin=2, numMax=2, expression='DASH{2}'), GT], expression='DASH{2} GT'), expression='!(DASH{2} GT)'), Klass(u' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff', expression='[\\x20..\\xff]')], expression='!(DASH{2} GT) [\\x20..\\xff]'), numMin=1, numMax=False, expression='(!(DASH{2} GT) [\\x20..\\xff])+'), SPACETABEOL], expression='(!(DASH{2} GT) [\\x20..\\xff])+ / SPACETABEOL'), numMin=False, numMax=False, expression='((!(DASH{2} GT) [\\x20..\\xff])+ / SPACETABEOL)*', name='comment_content')
    html_comment = Sequence([LT, BANG, Repetition(DASH, numMin=2, numMax=2, expression='DASH{2}'), comment_content, Repetition(DASH, numMin=2, numMax=2, expression='DASH{2}'), GT], expression='LT BANG DASH{2} comment_content DASH{2} GT', name='html_comment')(toolset['drop'])
    
    # Text
    
    page_name = Repetition(raw_char, numMin=1, numMax=False, expression='raw_char+', name='page_name')(toolset['join'])
    
    # Template parameters
    # Those parameters should be substituted by their value when the current page is a template
    # or by their optional default value in any case
    
    parameter_id = Repetition(raw_char, numMin=1, numMax=False, expression='raw_char+', name='parameter_id')(toolset['join'])
    parameter_value = Option(inline, expression='inline?', name='parameter_value')(toolset['keep'])
    optional_default_value = Sequence([Option(Sequence([PIPE, Repetition(SPACETABEOL, numMin=False, numMax=False, expression='SPACETABEOL*'), parameter_value], expression='PIPE SPACETABEOL* parameter_value'), expression='(PIPE SPACETABEOL* parameter_value)?'), Repetition(SPACETABEOL, numMin=False, numMax=False, expression='SPACETABEOL*')], expression='(PIPE SPACETABEOL* parameter_value)? SPACETABEOL*', name='optional_default_value')(toolset['liftNode'])
    template_parameter = Sequence([PARAMETER_BEGIN, parameter_id, optional_default_value, PARAMETER_END], expression='PARAMETER_BEGIN parameter_id optional_default_value PARAMETER_END', name='template_parameter')(toolset['substitute_template_parameter'])
    
    # Links
    
    LINK_PIPE = Clone(PIPE, expression='PIPE', name='LINK_PIPE')(toolset['restore'])
    internal_link = Sequence([Repetition(L_BRACKET, numMin=2, numMax=2, expression='L_BRACKET{2}'), inline, Repetition(Sequence([LINK_PIPE, inline], expression='LINK_PIPE inline'), numMin=False, numMax=False, expression='(LINK_PIPE inline)*'), Repetition(R_BRACKET, numMin=2, numMax=2, expression='R_BRACKET{2}')], expression='L_BRACKET{2} inline (LINK_PIPE inline)* R_BRACKET{2}', name='internal_link')(toolset['join'])
    external_link = Sequence([L_BRACKET, inline, Repetition(Sequence([SPACE, inline], expression='SPACE inline'), numMin=False, numMax=False, expression='(SPACE inline)*'), R_BRACKET], expression='L_BRACKET inline (SPACE inline)* R_BRACKET', name='external_link')(toolset['join'])
    link = Choice([internal_link, external_link], expression='internal_link / external_link', name='link')
    
    # Templates
    
    value_content = Repetition(Choice([inline, Sequence([NextNot(Sequence([Repetition(SPACETABEOL, numMin=False, numMax=False, expression='SPACETABEOL*'), Choice([TEMPLATE_END, PIPE], expression='TEMPLATE_END / PIPE')], expression='SPACETABEOL* (TEMPLATE_END / PIPE)'), expression='!(SPACETABEOL* (TEMPLATE_END / PIPE))'), Choice([any_char, EOL], expression='any_char / EOL')], expression='!(SPACETABEOL* (TEMPLATE_END / PIPE)) (any_char / EOL)')], expression='inline / (!(SPACETABEOL* (TEMPLATE_END / PIPE)) (any_char / EOL))'), numMin=False, numMax=False, expression='(inline / (!(SPACETABEOL* (TEMPLATE_END / PIPE)) (any_char / EOL)))*', name='value_content')(toolset['keep'])
    parameter_value = Sequence([value_content, Repetition(SPACETABEOL, numMin=False, numMax=False, expression='SPACETABEOL*')], expression='value_content SPACETABEOL*', name='parameter_value')
    optional_value = Option(parameter_value, expression='parameter_value?', name='optional_value')
    parameter_equal = Sequence([Repetition(SPACETABEOL, numMin=False, numMax=False, expression='SPACETABEOL*'), EQUAL, Repetition(SPACETABEOL, numMin=False, numMax=False, expression='SPACETABEOL*')], expression='SPACETABEOL* EQUAL SPACETABEOL*', name='parameter_equal')
    parameter_name = Repetition(Sequence([NextNot(Choice([esc_char, parameter_equal], expression='esc_char/parameter_equal'), expression='!(esc_char/parameter_equal)'), raw_char], expression='!(esc_char/parameter_equal) raw_char'), numMin=1, numMax=False, expression='(!(esc_char/parameter_equal) raw_char)+', name='parameter_name')(toolset['join'])
    named_parameter = Sequence([parameter_name, parameter_equal, optional_value], expression='parameter_name parameter_equal optional_value', name='named_parameter')
    standalone_parameter = Option(value_content, expression='value_content?', name='standalone_parameter')(toolset['join'])
    parameter = Sequence([Repetition(SPACETABEOL, numMin=False, numMax=False, expression='SPACETABEOL*'), PIPE, Repetition(SPACETABEOL, numMin=False, numMax=False, expression='SPACETABEOL*'), Choice([named_parameter, standalone_parameter], expression='named_parameter/standalone_parameter')], expression='SPACETABEOL* PIPE SPACETABEOL* (named_parameter/standalone_parameter)', name='parameter')(toolset['liftValue'])
    parameters = Repetition(parameter, numMin=False, numMax=False, expression='parameter*', name='parameters')
    template = Sequence([TEMPLATE_BEGIN, page_name, parameters, Repetition(SPACETABEOL, numMin=False, numMax=False, expression='SPACETABEOL*'), TEMPLATE_END], expression='TEMPLATE_BEGIN page_name parameters SPACETABEOL* TEMPLATE_END', name='template')(toolset['substitute_template'])
    
    # inline allows to have templates/links inside templates/links
    
    structure = Choice([link, template, template_parameter], expression='link / template / template_parameter', name='structure')
    inline **= Repetition(Choice([structure, raw_text], expression='structure / raw_text'), numMin=1, numMax=False, expression='(structure / raw_text)+', name='inline')
    numbered_entity = Sequence([AMP, HASH, Repetition(Klass(u'0123456789', expression='[0..9]'), numMin=1, numMax=False, expression='[0..9]+'), SEMICOLON], expression='AMP HASH [0..9]+ SEMICOLON', name='numbered_entity')(toolset['substitute_numbered_entity'])
    named_entity = Sequence([AMP, Repetition(Klass(u'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', expression='[a..zA..Z]'), numMin=1, numMax=False, expression='[a..zA..Z]+'), SEMICOLON], expression='AMP [a..zA..Z]+ SEMICOLON', name='named_entity')(toolset['substitute_named_entity'])
    entity = Choice([named_entity, numbered_entity], expression='named_entity / numbered_entity', name='entity')
    
    # Pre and nowiki tags
    # Preformatted acts like nowiki (disables wikitext parsing)
    # We allow any char without parsing them as long as the tag is not closed
    
    pre_text = Repetition(Sequence([NextNot(PRE_END, expression='!PRE_END'), any_char], expression='!PRE_END any_char'), numMin=False, numMax=False, expression='(!PRE_END any_char)*', name='pre_text')(toolset['join'])
    preformatted = Sequence([PRE_BEGIN, pre_text, PRE_END], expression='PRE_BEGIN pre_text PRE_END', name='preformatted')(toolset['liftValue'])
    eol_to_space = Repetition(EOL, numMin=False, numMax=False, expression='EOL*', name='eol_to_space')(toolset['replace_by_space'])
    nowiki_text = Repetition(Sequence([NextNot(NOWIKI_END, expression='!NOWIKI_END'), Choice([any_char, eol_to_space], expression='any_char/eol_to_space')], expression='!NOWIKI_END (any_char/eol_to_space)'), numMin=False, numMax=False, expression='(!NOWIKI_END (any_char/eol_to_space))*', name='nowiki_text')(toolset['join'])
    nowiki = Sequence([NOWIKI_BEGIN, nowiki_text, NOWIKI_END], expression='NOWIKI_BEGIN nowiki_text NOWIKI_END', name='nowiki')(toolset['liftValue'])
    
    # Text types
    
    styled_text = Choice([template, template_parameter, entity], expression='template / template_parameter / entity', name='styled_text')
    not_styled_text = Choice([html_comment, preformatted, nowiki], expression='html_comment / preformatted / nowiki', name='not_styled_text')
    allowed_char = Repetition(esc_char, numMin=1, numMax=1, expression='esc_char{1}', name='allowed_char')(toolset['restore'], toolset['liftValue'])
    allowed_text = Choice([raw_text, allowed_char], expression='raw_text / allowed_char', name='allowed_text')
    wikitext = Repetition(Choice([not_styled_text, styled_text, allowed_text, EOL], expression='not_styled_text / styled_text / allowed_text / EOL'), numMin=1, numMax=False, expression='(not_styled_text / styled_text / allowed_text / EOL)+', name='wikitext')(toolset['join'])

    symbols = locals().copy()
    symbols.update(actions)
    parser._recordPatterns(symbols)
    parser._setTopPattern("wikitext")
    parser.grammarTitle = "preprocessor"
    parser.filename = "preprocessorParser.py"

    return parser

########NEW FILE########
__FILENAME__ = raw
from constants import html_entities
from mediawiki_parser import wikitextParser

def toolset():
    def render_title1(node):
        pass

    def render_title2(node):
        pass

    def render_title3(node):
        pass

    def render_title4(node):
        pass

    def render_title5(node):
        pass

    def render_title6(node):
        pass

    def render_raw_text(node):
        pass

    def render_paragraph(node):
        pass

    def render_wikitext(node):
        pass

    def render_body(node):
        pass

    def render_entity(node):
        value = '%s' % node.leaf()
        if value in html_entities:
            node.value = '%s' % unichr(html_entities[value])
        else:
            node.value = '&%s;' % value

    def render_lt(node):
        pass

    def render_gt(node):
        pass

    def render_tag_open(node):
        pass

    def render_tag_close(node):
        pass

    def render_tag_autoclose(node):
        pass

    def render_attribute(node):
        pass

    def render_table(node):
        pass

    def render_table_line_break(node):
        pass

    def render_table_header_cell(node):
        pass

    def render_table_normal_cell(node):
        pass

    def render_table_empty_cell(node):
        pass

    def render_table_caption(node):
        pass

    def render_preformatted(node):
        pass

    def render_hr(node):
        pass

    def render_li(node):
        pass

    def render_list(node):
        pass

    def render_url(node):
        pass

    def render_external_link(node):
        pass

    def render_internal_link(node):
        pass

    return locals()

def make_parser():
    return wikitextParser.make_parser(toolset())

########NEW FILE########
__FILENAME__ = test_comments
# -*- coding: utf8 -*-

from mediawiki_parser.tests import ParserTestCase


class CommentsTests(ParserTestCase):
    def test_comment_before_title(self):
        source = '<!-- comment -->=Title 1=\n'
        result = "[title1:[raw_text:'Title 1']]"
        self.parsed_equal_string(source, result, None)

    def test_comment_before_preformatted_paragraph(self):
        source = "<!-- comment --> This is a preformatted paragraph.\n"
        result = """body:
   preformatted_lines:
      preformatted_line:
         preformatted_inline:
            raw_text:This is a preformatted paragraph.
         EOL_KEEP:
"""
        self.parsed_equal_tree(source, result, None)

    def test_comment_before_list(self):
        source = '<!--comment\n-->* text\n'
        result = "[list:[bullet_list_leaf:[raw_text:' text']]]"
        self.parsed_equal_string(source, result, None)

    def test_comment_inside_list(self):
        source = '*<!--comment---->** other text\n'
        result = "[list:[@bullet_sub_list@:[@bullet_sub_list@:[bullet_list_leaf:[raw_text:' other text']]]]]"
        self.parsed_equal_string(source, result, None)

    def test_comment_inside_paragraph(self):
        source = "This is a<!-- this is an HTML \t\n comment --> paragraph.\n"
        result = """body:
   paragraphs:
      paragraph:
         raw_text:This is a paragraph."""
        self.parsed_equal_tree(source, result, None)

    def test_empty_comment(self):
        source = 'an <!----> empty comment'
        result = "[raw_text:'an  empty comment']"
        self.parsed_equal_string(source, result, 'inline')

    def test_special_chars_in_comment(self):
        source = u'a <!--\n\t你好--> comment'
        result = "[raw_text:'a  comment']"
        self.parsed_equal_string(source, result, 'inline')

########NEW FILE########
__FILENAME__ = test_html_postprocessor
# -*- coding: utf8 -*-

from mediawiki_parser.tests import PostprocessorTestCase


class HTMLBackendTests(PostprocessorTestCase):
    def test_simple_title2(self):
        source = '== A title ==\n'
        result = "<h2> A title </h2>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_simple_title6(self):
        source = '====== Test! ======\n'
        result = "<h6> Test! </h6>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_simple_allowed_open_tag(self):
        source = 'a<span>test'
        result = 'a<span>test'
        self.parsed_equal_string(source, result, 'inline', {}, 'html')

    def test_complex_allowed_open_tag(self):
        """ The postprocessor should remove the disallowed attributes. """
        source = '<span class="wikitext" style="color:red" onclick="javascript:alert()">'
        result = '<span class="wikitext" style="color:red">'
        self.parsed_equal_string(source, result, 'inline', {}, 'html')

    def test_simple_disallowed_open_tag(self):
        source = 'another <a> test'
        result = 'another &lt;a&gt; test'
        self.parsed_equal_string(source, result, 'inline', {}, 'html')

    def test_complex_disallowed_open_tag(self):
        """ The postprocessor doesn't remove the disallowed attributes, but outputs everything as text. """
        source = '<a href="test" class="test" style="color:red" anything="anything">'
        result = '&lt;a href="test" class="test" style="color:red" anything="anything"&gt;'
        self.parsed_equal_string(source, result, 'inline', {}, 'html')

    def test_simple_allowed_autoclose_tag(self):
        source = 'a<br />test'
        result = 'a<br />test'
        self.parsed_equal_string(source, result, 'inline', {}, 'html')

    def test_complex_allowed_autoclose_tag(self):
        source = 'one more <br name="test" /> test'
        result = 'one more <br name="test" /> test'
        self.parsed_equal_string(source, result, 'inline', {}, 'html')

    def test_simple_disallowed_autoclose_tag(self):
        source = 'a<test />test'
        result = 'a&lt;test /&gt;test'
        self.parsed_equal_string(source, result, 'inline', {}, 'html')

    def test_complex_disallowed_autoclose_tag(self):
        source = '<img src="file.png" />'
        result = '&lt;img src="file.png" /&gt;'
        self.parsed_equal_string(source, result, 'inline', {}, 'html')

    def test_simple_table(self):
        source = """{|
! cellA
! cellB
|- style="color:red"
| cell C
| cell D
|}
"""
        result = """<table>
<tr>
\t<th> cellA</th>
\t<th> cellB</th>
</tr>
<tr style="color:red">
\t<td> cell C</td>
\t<td> cell D</td>
</tr>
</table>
"""
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_complex_table(self):
        source = """{| style="background:blue" {{prettyTable}}
|+ style="color:red" | Table {{title|parameter}}
|-
|
! scope=col | Title A
! scope=col | Title B
|-
! scope=row | Line 1
| style="test:test" | data L1.A
|data L1.B
|-
! scope=row | Line 2
|data L2.A
|data {{template|with|parameters=L2.B}}
|}
"""
        result = """<table style="background:blue" class="prettyTable">
<tr>
\t<caption style="color:red"> Table This is the title with a parameter!</caption>
</tr>
<tr>
\t<th scope="col"> Title A</th>
\t<th scope="col"> Title B</th>
</tr>
<tr>
\t<th scope="row"> Line 1</th>
\t<td style="test:test"> data L1.A</td>
\t<td>data L1.B</td>
</tr>
<tr>
\t<th scope="row"> Line 2</th>
\t<td>data L2.A</td>
\t<td>data <a href="Template:template">Template:template</a></td>
</tr>
</table>
"""
        templates = {'prettyTable': 'class="prettyTable"',
                     'title': 'This is the title with a {{{1}}}!'}
        self.parsed_equal_string(source, result, 'wikitext', templates, 'html')

    def test_wikitext_in_table(self):
        source = """{| cellpadding="10"
|- valign="top"
|

* Line : {{template}}
* other line : [[link]]...
|
== title ==
----
::: lists
|}
"""
        result = """<table>
<tr>
</tr>
<tr>
\t<td><ul>
\t<li> Line : <a href="Template:template">Template:template</a></li>
\t<li> other line : <a href="link">link</a>...</li>
</ul>
</td>
\t<td><h2> title </h2>
<hr />
<dl>
\t<dd><dl>
\t<dd><dl>
\t<dd> lists</dd>
</dl>
</dd>
</dl>
</dd>
</dl>
</td>
</tr>
</table>
"""
        templates = {'prettyTable': 'class="prettyTable"',
                     'title': 'This is the title with a {{{1}}}!'}
        self.parsed_equal_string(source, result, 'wikitext', templates, 'html')

    def test_nested_tables(self):
        source = """{| style="background:blue" {{prettyTable}}
|+ style="color:red" | Table {{title|1=true}}
|-
! scope=col | First (mother)
! scope=col | table
|
{| style="background:red" {{prettyTable}}
! scope=row | Second (daughter) table
|data L1.A
|data L1.B
|-
! scope=row | in the first one
|data L2.A
|data L2.B
|}
|-
| first
| table
| again
|}
"""
        result = """<table style="background:blue" class="prettyTable">
<tr>
\t<caption style="color:red"> Table This is the title, true!</caption>
</tr>
<tr>
\t<th scope="col"> First (mother)</th>
\t<th scope="col"> table</th>
\t<td><table style="background:red" class="prettyTable">
<tr>
\t<th scope="row"> Second (daughter) table</th>
\t<td>data L1.A</td>
\t<td>data L1.B</td>
</tr>
<tr>
\t<th scope="row"> in the first one</th>
\t<td>data L2.A</td>
\t<td>data L2.B</td>
</tr>
</table>
</td>
</tr>
<tr>
\t<td> first</td>
\t<td> table</td>
\t<td> again</td>
</tr>
</table>
"""
        templates = {'prettyTable': 'class="prettyTable"',
                     'title': 'This is the title, {{{1}}}!'}
        self.parsed_equal_string(source, result, 'wikitext', templates, 'html')

    def test_horizontal_rule(self):
        source = """test
----
test
"""
        result = """<p>test</p>
<hr />
<p>test</p>
"""
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_preformatted_paragraph(self):
        source = """ test
 {{template}}
 test
"""
        templates = {'template': 'content'}
        result = """<pre>test
<a href="Template:template">Template:template</a>
test
</pre>
"""
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_italic(self):
        source = "Here, we have ''italic'' text.\n"
        result = "<p>Here, we have <em>italic</em> text.</p>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_bold(self):
        source = "Here, we have '''bold''' text.\n"
        result = "<p>Here, we have <strong>bold</strong> text.</p>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_bold_and_italic_case1(self):
        source = "Here, we have '''''bold and italic''''' text.\n"
        result = "<p>Here, we have <em><strong>bold and italic</strong></em> text.</p>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_bold_italic_case2(self):
        source = "Here, we have ''italic only and '''bold and italic''''' text.\n"
        result = "<p>Here, we have <em>italic only and <strong>bold and italic</strong></em> text.</p>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_bold_italic_case3(self):
        source = "Here, we have '''bold only and ''bold and italic''''' text.\n"
        result = "<p>Here, we have <strong>bold only and <em>bold and italic</em></strong> text.</p>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_bold_italic_case4(self):
        source = "Here, we have '''''bold and italic''' and italic only''.\n"
        result = "<p>Here, we have <em><strong>bold and italic</strong> and italic only</em>.</p>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_bold_italic_case5(self):
        source = "Here, we have '''''bold and italic'' and bold only'''.\n"
        result = "<p>Here, we have <strong><em>bold and italic</em> and bold only</strong>.</p>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_bold_italic_case6(self):
        source = "Here, we have ''italic, '''bold and italic''' and italic only''.\n"
        result = "<p>Here, we have <em>italic, <strong>bold and italic</strong> and italic only</em>.</p>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_bold_italic_case7(self):
        source = "Here, we have '''bold, ''bold and italic'' and bold only'''.\n"
        result = "<p>Here, we have <strong>bold, <em>bold and italic</em> and bold only</strong>.</p>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_bold_italic_case8(self):
        source = """'''Le gras :'''

et l'''italique''...
"""
        result = "<p><strong>Le gras :</strong></p>\n<p>et l'<em>italique</em>...</p>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_bold_italic_case9(self):
        source = """'''he

lo'''
"""
        result = "<p><strong>he</strong></p>\n<p>lo<strong></strong></p>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_bold_italic_case10(self):
        source = """'''hi!
"""
        result = "<p><strong>hi!</strong></p>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_bold_italic_case11(self):
        source = """''hi again!
"""
        result = "<p><em>hi again!</em></p>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_bold_italic_case12(self):
        source = """'''''bold and italic!
"""
        result = "<p><em><strong>bold and italic!</strong></em></p>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_bold_italic_case13(self):
        source = """'''
"""
        result = "<p><strong></strong></p>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_bold_italic_case14(self):
        source = """''
"""
        result = "<p><em></em></p>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_bold_italic_case15(self):
        source = """'''''
"""
        result = "<p><em><strong></strong></em></p>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_italic_template(self):
        source = "Here, we have ''italic {{template}}!''.\n"
        result = "<p>Here, we have <em>italic text!</em>.</p>\n"
        templates = {'template': 'text'}
        self.parsed_equal_string(source, result, 'wikitext', templates, 'html')

    def test_styles_in_template(self):
        source = "Here, we have {{template}}.\n"
        result = "<p>Here, we have <strong>text</strong> and <em>more text</em> and <em><strong>still more text</strong></em>.</p>\n"
        templates = {'template': "'''text''' and ''more text'' and '''''still more text'''''"}
        self.parsed_equal_string(source, result, 'wikitext', templates, 'html')

    def test_simple_bullet_list(self):
        source = """* item 1
** item 2
*** item 3
** item 2
"""
        result = """<ul>
\t<li> item 1<ul>
\t<li> item 2<ul>
\t<li> item 3</li>
</ul>
</li>
\t<li> item 2</li>
</ul>
</li>
</ul>
"""
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_simple_numbered_list(self):
        source = """## item 2
### item 3
## item 2
### item 3
"""
        result = """<ol>
\t<li><ol>
\t<li> item 2</li>
</ol>
</li>
\t<li><ol>
\t<li><ol>
\t<li> item 3</li>
</ol>
</li>
</ol>
</li>
\t<li><ol>
\t<li> item 2</li>
</ol>
</li>
\t<li><ol>
\t<li><ol>
\t<li> item 3</li>
</ol>
</li>
</ol>
</li>
</ol>
"""
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_simple_semicolon_list(self):
        source = """; item 1
;; item 2
;; item 2
; item 1
; item 1
;;; item 3
"""
        result = """<dl>
\t<dt> item 1<dl>
\t<dt> item 2</dt>
\t<dt> item 2</dt>
</dl>
</dt>
\t<dt> item 1</dt>
\t<dt> item 1<dl>
\t<dt><dl>
\t<dt> item 3</dt>
</dl>
</dt>
</dl>
</dt>
</dl>
"""
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_simple_colon_list(self):
        source = """: item 1
::: item 3
:: item 2
: item 1
:: item 2
:: item 2
"""
        result = """<dl>
\t<dd> item 1<dl>
\t<dd><dl>
\t<dd> item 3</dd>
</dl>
</dd>
\t<dd> item 2</dd>
</dl>
</dd>
\t<dd> item 1<dl>
\t<dd> item 2</dd>
\t<dd> item 2</dd>
</dl>
</dd>
</dl>
"""
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_formatted_mixed_list(self):
        source = """: item 1
; this is ''italic''
* and '''bold''' here
# a [[link]]
: a {{template}}
"""
        result = """<dl>
\t<dd> item 1</dd>
</dl>
<dl>
\t<dt>this is <em>italic</em></dt>
</dl>
<ul>
\t<li>and <strong>bold</strong> here</li>
</ul>
<ol>
\t<li> a <a href="link">link</a></li>
</ol>
<dl>
\t<dd> a template!</dd>
</dl>
"""
        templates = {'template': 'template!'}
        self.parsed_equal_string(source, result, 'wikitext', templates, 'html')

    def test_complex_mixed_list(self):
        source = """*level 1
*level 1
**level 2
**#level 3
**level 2
:: level 2
; level 1
##level 2
##;level 3
####level 4
#**#level 4
:*;#*: weird syntax
* end
"""
        result = """<ul>
\t<li>level 1</li>
\t<li>level 1<ul>
\t<li>level 2<ol>
\t<li>level 3</li>
</ol>
</li>
\t<li>level 2</li>
</ul>
</li>
\t<li><dl>
\t<dd> level 2</dd>
</dl>
</li>
</ul>
<dl>
\t<dt> level 1</dt>
\t<dt><ol>
\t<li>level 2</li>
</ol>
</dt>
\t<dt><ol>
\t<li><dl>
\t<dt>level 3</dt>
</dl>
</li>
</ol>
</dt>
\t<dt><ol>
\t<li><ol>
\t<li><ol>
\t<li>level 4</li>
</ol>
</li>
</ol>
</li>
</ol>
</dt>
\t<dt><ul>
\t<li><ul>
\t<li><ol>
\t<li>level 4</li>
</ol>
</li>
</ul>
</li>
</ul>
</dt>
\t<dt><ul>
\t<li><dl>
\t<dt><ol>
\t<li><ul>
\t<li><dl>
\t<dd> weird syntax</dd>
</dl>
</li>
</ul>
</li>
</ol>
</dt>
</dl>
</li>
</ul>
</dt>
</dl>
<ul>
\t<li> end</li>
</ul>
"""
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_tag_balancing_in_title6(self):
        """Close open tags"""
        source = '======<b>Test!======\n'
        result = "<h6><b>Test!</b></h6>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_tag_balancing_in_title2(self):
        """Ignore close tags for non-open tags"""
        source = '==Test!</i>==\n'
        result = "<h2>Test!</h2>\n"
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_convert_autoclose_tags(self):
        """Ignore close tags for non-open tags"""
        source = 'convert this: <br></br><br/> and <hr>this </hr> too <hr/>!\n'
        result = '<p>convert this: <br /><br /><br /> and <hr />this <hr /> too <hr />!</p>\n'
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_tag_balancing_in_mixed_structures(self):
        """Ignore close tags for non-open tags"""
        source = """==<b>Test!</i>==
* test <i>test</b>
A paragraph with a </hr> tag and a <span style="color:blue">span.

a {{template}}</b>.

Note: an <span>open tag can be closed {{in a template}}
"""
        result = """<h2><b>Test!</b></h2>
<ul>
\t<li> test <i>test</i></li>
</ul>
<p>A paragraph with a <hr /> tag and a <span style="color:blue">span.</span></p>
<p>a text<i>text.</i></p>
<p>Note: an <span>open tag can be closed like </span> this!</p>
"""
        templates = {'template': 'text<i>text',
                     'in a template': 'like </span> this!'}
        self.parsed_equal_string(source, result, 'wikitext', templates, 'html')

    def test_inline_url(self):
        source = 'text http://www.mozilla.org text\n'
        result = '<p>text <a href="http://www.mozilla.org">http://www.mozilla.org</a> text</p>\n'
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_external_links(self):
        source = "text [http://www.mozilla.org], [http://www.github.com] and [http://fr.wikipedia.org ''French'' Wikipedia] text\n"
        result = '<p>text <a href="http://www.mozilla.org">[1]</a>, <a href="http://www.github.com">[2]</a> and <a href="http://fr.wikipedia.org"><em>French</em> Wikipedia</a> text</p>\n'
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

    def test_internal_links(self):
        source = "Links: [[page]], [[page|alternate]], [[page|alternate|alternate2]] and [[Page name|a{{test}}c]]\n"
        result = '<p>Links: <a href="page">page</a>, <a href="page">alternate</a>, <a href="page">alternate|alternate2</a> and <a href="Page name">abc</a></p>\n'
        templates = {'test': 'b'}
        self.parsed_equal_string(source, result, 'wikitext', templates, 'html')

    def test_categories_and_category_links(self):
        source = u"[[:Category:Cat name|a ''text'']]\n[[Catégorie:Ma catégorie]]\n[[Category:My category|sort key]]\n"
        result = u'<body>\n<p><a href="Category:Cat name">a <em>text</em></a></p>\n<p>Categories: <a href="Ma catégorie">Ma catégorie</a>, <a href="My category">My category</a></p>\n</body>'
        self.parsed_equal_string(source, result, 'body', {}, 'html')

    def test_interwiki_links(self):
        source = u"[[:fr:Un lien...|texte]]\n[[fr:Mon article]]\n[[en:My article]]\n"
        result = u'<body>\n<p><a href="http://fr.wikipedia.org/wiki/Un lien...">texte</a></p>\n<p>Interwiki: <a href="http://fr.wikipedia.org/wiki/Mon article">Mon article</a>, <a href="http://en.wikipedia.org/wiki/My article">My article</a></p>\n</body>'
        self.parsed_equal_string(source, result, 'body', {}, 'html')

    def test_files(self):
        source = """[[Image:File.png|thumb|right|200px|Legend]]
[[Image:File.png|thumb|right|200x100px|'''Formatted''' [[legend]]!]]
[[File:Name.png]]
[[:File:Name.png|link to a file]]
[[File:Test.jpg|left|thumbnail]]
"""
        result = """<p><div class="thumbnail"><img src="File.png" style="float:right;width:200px;" alt="" /><p>Legend</p></div>
<div class="thumbnail"><img src="File.png" style="float:right;width:200px;height:100px" alt="" /><p><strong>Formatted</strong> <a href="legend">legend</a>!</p></div>
<img src="Name.png" style="" alt="" /><a href="File:Name.png">link to a file</a><div class="thumbnail"><img src="Test.jpg" style="float:left;" alt="" /><p></p></div>
</p>
"""
        self.parsed_equal_string(source, result, 'wikitext', {}, 'html')

########NEW FILE########
__FILENAME__ = test_links
# -*- coding: utf8 -*-

from mediawiki_parser.tests import ParserTestCase


class LinksTests(ParserTestCase):
    def test_simple_internal_link(self):
        source = '[[article]]'
        result = "[internal_link:[page_name:'article']]"
        self.parsed_equal_string(source, result, 'inline')

    def test_advanced_internal_link(self):
        source = '[[article|alternate]]'
        result = "[internal_link:[page_name:'article'  link_arguments:[link_argument:[raw_text:'alternate']]]]"
        self.parsed_equal_string(source, result, 'inline')

    def test_special_chars_in_internal_link(self):
        source = '[[article|}}]]'
        result = "[internal_link:[page_name:'article'  link_arguments:[link_argument:'}}']]]"
        self.parsed_equal_string(source, result, 'inline')

    def test_template_in_internal_link(self):
        source = "[[article|{{template|value=pass}}]]"
        result = "[internal_link:[page_name:'article'  link_arguments:[link_argument:[raw_text:'test: pass']]]]"
        templates = {'template': 'test: {{{value}}}'}
        self.parsed_equal_string(source, result, 'inline', templates)

    def test_category(self):
        source = '[[Category:Category name|sort key]]'
        result = "[internal_link:[page_name:'Category:Category name'  link_arguments:[link_argument:[raw_text:'sort key']]]]"
        self.parsed_equal_string(source, result, 'inline')

    def test_link_to_category(self):
        source = '[[:Category:MyCategory|mycategory]]'
        result = "[internal_link:[page_name:':Category:MyCategory'  link_arguments:[link_argument:[raw_text:'mycategory']]]]"
        self.parsed_equal_string(source, result, 'inline')

    def test_category_foreign_language(self):
        source = u'[[Catégorie:Nom de catégorie]]'
        result = u"[internal_link:[page_name:'Catégorie:Nom de catégorie']]"
        self.parsed_equal_string(source, result, 'inline')

    def test_image(self):
        source = '[[File:Filename.png]]'
        result = "[internal_link:[page_name:'File:Filename.png']]"
        self.parsed_equal_string(source, result, 'inline')

    def test_image_with_parameter(self):
        source = '[[File:File name.JPG|25px]]'
        result = "[internal_link:[page_name:'File:File name.JPG'  link_arguments:[link_argument:[raw_text:'25px']]]]"
        self.parsed_equal_string(source, result, 'inline')

    def test_image_with_parameters(self):
        source = '[[Category:Category name|thumb|300px|left|Legend|alt=Image description]]'
        result = "[internal_link:[page_name:'Category:Category name'  link_arguments:[link_argument:[raw_text:'thumb']  link_argument:[raw_text:'300px']  link_argument:[raw_text:'left']  link_argument:[raw_text:'Legend']  link_argument:[raw_text:'alt=Image description']]]]"
        self.parsed_equal_string(source, result, 'inline')

    def test_inline_url(self):
        source = 'An URL: http://www.mozilla.org'
        result = "[raw_text:'An URL: '  inline_url:[url:'http://www.mozilla.org']]"
        self.parsed_equal_string(source, result, 'inline')

    def test_external_link(self):
        source = "[http://www.mozilla.org]"
        result = "[external_link:[url:'http://www.mozilla.org']]"
        self.parsed_equal_string(source, result, 'inline')

    def test_formatted_text_in_external_link(self):
        source = "[http://www.mozilla.org this is an ''external'' link]"
        result = "[external_link:[url:'http://www.mozilla.org'  optional_link_text:[raw_text:'this is an \'\'external\'\' link']]]"
        self.parsed_equal_string(source, result, 'inline')

    def test_spacetabs_in_external_link(self):
        source = '[http://www.mozilla.org         some text]'
        result = "[external_link:[url:'http://www.mozilla.org'  optional_link_text:[raw_text:'some text']]]"
        self.parsed_equal_string(source, result, 'inline')

    def test_HTML_external_link(self):
        # By default, HTML links are not allowed
        source = '<a href="http://www.mozilla.org">this is an external link</a>'
        result = "[tag_open:[tag_name:'a'  optional_attributes:[optional_attribute:[attribute_name:'href'  value_quote:'http://www.mozilla.org']]]  raw_text:'this is an external link'  tag_close:[tag_name:'a']]"
        self.parsed_equal_string(source, result, 'inline')

########NEW FILE########
__FILENAME__ = test_lists
# -*- coding: utf8 -*-

from mediawiki_parser.tests import ParserTestCase


class ListsTests(ParserTestCase):
    def test_1_bullet_list(self):
        source = '* text\n'
        result = "[list:[bullet_list_leaf:[raw_text:' text']]]"
        self.parsed_equal_string(source, result, None)

    def test_2_bullet_list(self):
        source = '** other text\n'
        result = "[list:[@bullet_sub_list@:[bullet_list_leaf:[raw_text:' other text']]]]"
        self.parsed_equal_string(source, result, None)

    def test_3_bullet_list(self):
        source = '*** other text\n'
        result = "[list:[@bullet_sub_list@:[@bullet_sub_list@:[bullet_list_leaf:[raw_text:' other text']]]]]"
        self.parsed_equal_string(source, result, None)

    def test_1_hash_list(self):
        source = '# text\n'
        result = "[list:[number_list_leaf:[raw_text:' text']]]"
        self.parsed_equal_string(source, result, None)

    def test_2_hash_list(self):
        source = "## more text\n"
        result = "[list:[@number_sub_list@:[number_list_leaf:[raw_text:' more text']]]]"
        self.parsed_equal_string(source, result, None)

    def test_3_hash_list(self):
        source = "### ''other text''\n"
        result = "[list:[@number_sub_list@:[@number_sub_list@:[number_list_leaf:[raw_text:' \'\'other text\'\'']]]]]"
        self.parsed_equal_string(source, result, None)

    def test_1_colon_list(self):
        source = ": more text\n"
        result = "[list:[colon_list_leaf:[raw_text:' more text']]]"
        self.parsed_equal_string(source, result, None)

    def test_4_colon_list(self):
        source = ":::: more {{text}}!\n"
        result = "[list:[@colon_sub_list@:[@colon_sub_list@:[@colon_sub_list@:[colon_list_leaf:[raw_text:' more words!']]]]]]"
        templates = {'text': 'words'}
        self.parsed_equal_string(source, result, None, templates)

    def test_1_semicolon_list(self):
        source = '; still more [[text]]\n'
        result = "[list:[semi_colon_list_leaf:[raw_text:' still more '  internal_link:[page_name:'text']]]]"
        self.parsed_equal_string(source, result, None)

    def test_2_semicolon_list(self):
        source = ';; still more [[text]]\n'
        result = "[list:[@semi_colon_sub_list@:[semi_colon_list_leaf:[raw_text:' still more '  internal_link:[page_name:'text']]]]]"
        self.parsed_equal_string(source, result, None)

    def test_1_colon_1_bullet_list(self):
        source = ':* more complicated case\n'
        result = "[list:[@colon_sub_list@:[bullet_list_leaf:[raw_text:' more complicated case']]]]"
        self.parsed_equal_string(source, result, None)

    def test_1_semicolon_1_bullet_list(self):
        source = ';* same as previous line\n'
        result = "[list:[@semi_colon_sub_list@:[bullet_list_leaf:[raw_text:' same as previous line']]]]"
        self.parsed_equal_string(source, result, None)

    def test_2_semicolon_2_bullet_list(self):
        source = '::** another complicated case\n'
        result = "[list:[@colon_sub_list@:[@colon_sub_list@:[@bullet_sub_list@:[bullet_list_leaf:[raw_text:' another complicated case']]]]]]"
        self.parsed_equal_string(source, result, None)

    def test_composed_list(self):
        source = "*:*;#*: this is {{correct}} syntax!\n"
        result = "[list:[@bullet_sub_list@:[@colon_sub_list@:[@bullet_sub_list@:[@semi_colon_sub_list@:[@number_sub_list@:[@bullet_sub_list@:[colon_list_leaf:[raw_text:' this is '  internal_link:[page_name:'Template:correct']  raw_text:' syntax!']]]]]]]]]"
        self.parsed_equal_string(source, result, None)

    def test_multiline_bullet_list(self):
        source = """* This example...
** shows the shape...
*** of the resulting ...
** AST
"""
        result = """body:
   list:
      bullet_list_leaf:
         raw_text: This example...
      @bullet_sub_list@:
         bullet_list_leaf:
            raw_text: shows the shape...
      @bullet_sub_list@:
         @bullet_sub_list@:
            bullet_list_leaf:
               raw_text: of the resulting ...
      @bullet_sub_list@:
         bullet_list_leaf:
            raw_text: AST"""
        self.parsed_equal_tree(source, result, None)

    def test_list_with_template_produces_single_list(self):
        source = """* This example...
{{template}}
*it...
"""
        result = """body:
   list:
      bullet_list_leaf:
         raw_text: This example...
      bullet_list_leaf:
         raw_text: checks
      bullet_list_leaf:
         raw_text:it..."""
        templates = {'template': '* checks'}
        self.parsed_equal_tree(source, result, None, templates)

########NEW FILE########
__FILENAME__ = test_nowiki
# -*- coding: utf8 -*-

from mediawiki_parser.tests import ParserTestCase


class NowikiTests(ParserTestCase):
    def test_nowiki_section(self):
        source = '<nowiki>some [[text]] that should {{not}} be changed</nowiki>\n'
        result = "[paragraphs:[paragraph:[nowiki:'some [[text]] that should {{not}} be changed']]]"
        self.parsed_equal_string(source, result, None)

    def test_nested_nowiki(self):
        # This looks weird but is the actual behavior of MediaWiki
        source = '<nowiki>some [[text]] <nowiki>that should </nowiki>{{not}} be changed</nowiki>\n'
        result = "[paragraphs:[paragraph:[nowiki:'some [[text]] <nowiki>that should '  internal_link:[page_name:'Template:not']  raw_text:' be changed'  tag_close:[tag_name:'nowiki']]]]"
        self.parsed_equal_string(source, result, None)

    def test_multiline_nowiki(self):
        source = """some <nowiki> [[text]] that

should {{not}} be </nowiki> changed
"""
        result = "[paragraphs:[paragraph:[raw_text:'some '  nowiki:' [[text]] that should {{not}} be '  raw_text:' changed']]]"
        self.parsed_equal_string(source, result, None)

########NEW FILE########
__FILENAME__ = test_paragraphs
# -*- coding: utf8 -*-

from mediawiki_parser.tests import ParserTestCase


class ParagraphsTests(ParserTestCase):
    def test_single_line_paragraph(self):
        source = "This is a paragraph.\n"
        result = """body:
   paragraphs:
      paragraph:
         raw_text:This is a paragraph."""
        self.parsed_equal_tree(source, result, None)

    def test_multi_line_paragraph(self):
        source = """This is a paragraph.
With a newline in the middle.
"""
        result = """body:
   paragraphs:
      paragraph:
         paragraph_line:
            raw_text:This is a paragraph.
         paragraph_line:
            raw_text:With a newline in the middle."""
        self.parsed_equal_tree(source, result, None)

    def test_2_paragraphs(self):
        source = """This is a paragraph.

Followed by another one.
"""
        result = """body:
   paragraphs:
      paragraph:
         raw_text:This is a paragraph.
      paragraph:
         raw_text:Followed by another one."""
        self.parsed_equal_tree(source, result, None)

    def test_blank_line_in_paragraphs(self):
        source = """This is a paragraph.


Followed a blank line and another paragraph.
"""
        result = """body:
   paragraphs:
      paragraph:
         raw_text:This is a paragraph.
      blank_paragraph:
      paragraph:
         raw_text:Followed a blank line and another paragraph."""
        self.parsed_equal_tree(source, result, None)

    def test_styled_text_in_paragraph(self):
        source = """Styled text such as ''italic'', '''bold''', {{templates}} and {{{template parameters}}} also work.
"""
        result = """body:
   paragraphs:
      paragraph:
         raw_text:Styled text such as ''italic'', '''bold''', 
         internal_link:
            page_name:Template:templates
         raw_text: and 
         allowed_char:{
         allowed_char:{
         allowed_char:{
         raw_text:template parameters
         allowed_char:}
         allowed_char:}
         allowed_char:}
         raw_text: also work."""
        self.parsed_equal_tree(source, result, None)

########NEW FILE########
__FILENAME__ = test_preformatted_paragraphs
# -*- coding: utf8 -*-

from mediawiki_parser.tests import ParserTestCase


class PreformattedParagraphsTests(ParserTestCase):
    def test_single_line_paragraph(self):
        source = " This is a preformatted paragraph.\n"
        result = """body:
   preformatted_lines:
      preformatted_line:
         preformatted_inline:
            raw_text:This is a preformatted paragraph.
         EOL_KEEP:
"""
        self.parsed_equal_tree(source, result, None)

    def test_preformatted_and_normal_paragraphs(self):
        source = """ This is a preformatted paragraph.
Followed by a "normal" one.
"""
        result = """body:
   preformatted_lines:
      preformatted_line:
         preformatted_inline:
            raw_text:This is a preformatted paragraph.
         EOL_KEEP:

   paragraphs:
      paragraph:
         raw_text:Followed by a "normal" one."""
        self.parsed_equal_tree(source, result, None)

    def test_multiline_paragraph(self):
        source = """ This is a multiline
 preformatted paragraph.
"""
        result = """body:
   preformatted_lines:
      preformatted_line:
         preformatted_inline:
            raw_text:This is a multiline
         EOL_KEEP:

      preformatted_line:
         preformatted_inline:
            raw_text:preformatted paragraph.
         EOL_KEEP:
"""
        self.parsed_equal_tree(source, result, None)

    def test_style_in_preformatted_paragraph(self):
        source = """ Styled text such as ''italic'', '''bold''', {{templates}} also work.
"""
        result = """body:
   preformatted_lines:
      preformatted_line:
         preformatted_inline:
            raw_text:Styled text such as ''italic'', '''bold''', 
            internal_link:
               page_name:Template:templates
            raw_text: also work.
         EOL_KEEP:
"""
        self.parsed_equal_tree(source, result, None)

    def test_tabs_in_preformatted_paragraph(self):
        source = """ Preformatted\tparagraph
 \twith
 \t\tmultiple tabs.
"""
        result = """body:
   preformatted_lines:
      preformatted_line:
         preformatted_inline:
            raw_text:Preformatted
            tab_to_8_spaces: 
            raw_text:paragraph
         EOL_KEEP:

      preformatted_line:
         preformatted_inline:
            tab_to_8_spaces: 
            raw_text:with
         EOL_KEEP:

      preformatted_line:
         preformatted_inline:
            tab_to_8_spaces: 
            tab_to_8_spaces: 
            raw_text:multiple tabs.
         EOL_KEEP:
"""
        self.parsed_equal_tree(source, result, None)

    def test_html_pre_paragraph(self):
        source = """<pre>
Preformatted paragraph.
</pre>
"""
        result = """body:
   preformatted_paragraph:
      preformatted_text:
         raw_text:Preformatted paragraph."""
        self.parsed_equal_tree(source, result, None)

    def test_formatted_html_pre_paragraph(self):
        # <pre> should act like <nowiki>
        source = "<pre>some [[text]] that should {{not}} be changed</pre>\n"
        result = "[paragraphs:[paragraph:[preformatted:'some [[text]] that should {{not}} be changed']]]"
        self.parsed_equal_string(source, result, None)

    def test_html_pre_in_paragraph(self):
        source = "Normal paragraph <pre>Preformatted one</pre> Normal one.\n"
        result = """body:
   paragraphs:
      paragraph:
         raw_text:Normal paragraph 
         preformatted:Preformatted one
         raw_text: Normal one."""
        self.parsed_equal_tree(source, result, None)

    def test_pre_paragraph_in_table(self):
        source = """{|
|-
! <pre>Text</pre>
|}
"""
        result = """body:
   table:
      table_line_break:
      table_line_header:
         table_cell:
            table_cell_content:
               raw_text: 
               preformatted:Text"""
        self.parsed_equal_tree(source, result, None)

########NEW FILE########
__FILENAME__ = test_rules
# -*- coding: utf8 -*-

from mediawiki_parser.tests import ParserTestCase


class RulesTests(ParserTestCase):
    def test_simple_rule(self):
        source = '----\n'
        result = "[horizontal_rule:'']"
        self.parsed_equal_string(source, result, None)

    def test_rule_too_short(self):
        # In this case, it is a paragraph!
        source = '---\n'
        result = "[paragraphs:[paragraph:[raw_text:'---']]]"
        self.parsed_equal_string(source, result, None)

    def test_rule_too_long(self):
        # In this case, it is a paragraph!
        source = '----\n'
        result = "[horizontal_rule:'']"
        self.parsed_equal_string(source, result, None)

    def test_inline_after_rule(self):
        # In this case, it is a paragraph!
        source = '------ {{template|arg=[[link]]}}\n'
        result = u"[horizontal_rule:[@inline@:[raw_text:' test: '  internal_link:[page_name:'link']]]]"
        templates = {'template': 'test: {{{arg}}}'}
        self.parsed_equal_string(source, result, None, templates)

########NEW FILE########
__FILENAME__ = test_special_chars
# -*- coding: utf8 -*-

from mediawiki_parser.tests import ParserTestCase


class SpecialCharsTests(ParserTestCase):
    def test_tabs_in_text(self):
        source = "Some\ttext and\t\ttabs."
        result = "[raw_text:'Some'  tab_to_space:' '  raw_text:'text and'  tab_to_space:' '  raw_text:'tabs.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_unicode_chars(self):
        source = u"Some Unicode characters: 你好."
        result = u"[raw_text:'Some Unicode characters: 你好.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_unicode_chars_in_links(self):
        source = u"[[你好|你好]]"
        result = u"[internal_link:[page_name:'你好'  link_arguments:[link_argument:[raw_text:'你好']]]]"
        self.parsed_equal_string(source, result, 'inline')

    def test_hash(self):
        source = 'This # should pass.'
        result = "[raw_text:'This # should pass.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_l_brace(self):
        source = 'This { should pass.'
        result = "[raw_text:'This '  allowed_char:'{'  raw_text:' should pass.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_r_brace(self):
        source = 'This } should pass.'
        result = "[raw_text:'This '  allowed_char:'}'  raw_text:' should pass.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_double_l_brace(self):
        source = 'This {{ should pass.'
        result = "[raw_text:'This '  allowed_char:'{'  allowed_char:'{'  raw_text:' should pass.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_double_r_brace(self):
        source = 'This }} should pass.'
        result = "[raw_text:'This '  allowed_char:'}'  allowed_char:'}'  raw_text:' should pass.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_lt(self):
        source = 'This < should pass.'
        result = "[raw_text:'This '  LT:'<'  raw_text:' should pass.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_gt(self):
        source = 'This > should pass.'
        result = "[raw_text:'This '  GT:'>'  raw_text:' should pass.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_lt_gt(self):
        "Entities corresponding to < and > should be left untouched"
        source = 'This is a tag: <p> but &lt;p&gt; and &#60;p&#62; are not tags.'
        result = "[raw_text:'This is a tag: '  tag_open:[tag_name:'p']  raw_text:' but '  entity:'<'  raw_text:'p'  entity:'>'  raw_text:' and '  allowed_char:'&'  raw_text:'#60'  allowed_char:';'  raw_text:'p'  allowed_char:'&'  raw_text:'#62'  allowed_char:';'  raw_text:' are not tags.']"
        self.parsed_equal_string(source, result, 'inline')        

    def test_l_bracket(self):
        source = 'This [ should pass.'
        result = "[raw_text:'This '  allowed_char:'['  raw_text:' should pass.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_double_l_bracket(self):
        source = 'This [[ should pass.'
        result = "[raw_text:'This '  allowed_char:'['  allowed_char:'['  raw_text:' should pass.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_r_bracket(self):
        source = 'This ] should pass.'
        result = "[raw_text:'This '  allowed_char:']'  raw_text:' should pass.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_double_r_bracket(self):
        source = 'This ]] should pass.'
        result = "[raw_text:'This '  allowed_char:']'  allowed_char:']'  raw_text:' should pass.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_pipe(self):
        source = 'This | should pass.'
        result = "[raw_text:'This '  allowed_char:'|'  raw_text:' should pass.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_equal(self):
        source = 'This = should pass.'
        result = "[raw_text:'This = should pass.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_colon(self):
        source = 'This: should pass.'
        result = "[raw_text:'This: should pass.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_semicolon(self):
        source = 'This; should pass.'
        result = "[raw_text:'This'  allowed_char:';'  raw_text:' should pass.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_quotes(self):
        source = 'This "should" pass.'
        result = "[raw_text:'This \"should\" pass.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_dash(self):
        source = 'This - should pass.'
        result = "[raw_text:'This - should pass.']"
        self.parsed_equal_string(source, result, 'inline')

    def test_double_r_bracket_with_link(self):
        source = 'This should be a [[link]] and [[plain text'
        result = "[raw_text:'This should be a '  internal_link:[page_name:'link']  raw_text:' and '  allowed_char:'['  allowed_char:'['  raw_text:'plain text']"
        self.parsed_equal_string(source, result, 'inline')

    def test_valid_named_entities(self):
        source = '&Alpha;&beta;&gamma; &diams;'
        result = u"[raw_text:'Αβγ ♦']"
        self.parsed_equal_string(source, result, 'inline')

    def test_valid_numbered_entities(self):
        source = '&#169;&#8212; &#9830;'
        result = u"[raw_text:'©— ♦']"
        self.parsed_equal_string(source, result, 'inline')

    def test_invalid_named_entities(self):
        source = '&abcd;&1234; &apos;'
        result = "[entity:'&abcd;'  entity:'&1234;'  raw_text:' '  entity:'&apos;']"
        self.parsed_equal_string(source, result, 'inline')

    def test_invalid_numbered_entities(self):
        source = '&#12252524534; &#04359435;'
        result = "[allowed_char:'&'  raw_text:'#12252524534'  allowed_char:';'  raw_text:' '  allowed_char:'&'  raw_text:'#4359435'  allowed_char:';']"
        self.parsed_equal_string(source, result, 'inline')

    def test_valid_entities_in_links(self):
        source = 'a [[test&copy;test]] and two other: [[&diams;]] [[&#8212;]]'
        result = u"[raw_text:'a '  internal_link:[page_name:'test©test']  raw_text:' and two other: '  internal_link:[page_name:'♦']  raw_text:' '  internal_link:[page_name:'—']]"
        self.parsed_equal_string(source, result, 'inline')

    def test_invalid_entities_in_links(self):
        source = 'a [[test&abcd;test]] and two other: [[&efgh;]] [[&#8282828212;]]'
        result = "[raw_text:'a '  allowed_char:'['  allowed_char:'['  raw_text:'test'  entity:'&abcd;'  raw_text:'test'  allowed_char:']'  allowed_char:']'  raw_text:' and two other: '  allowed_char:'['  allowed_char:'['  entity:'&efgh;'  allowed_char:']'  allowed_char:']'  raw_text:' '  allowed_char:'['  allowed_char:'['  allowed_char:'&'  raw_text:'#8282828212'  allowed_char:';'  allowed_char:']'  allowed_char:']']"
        self.parsed_equal_string(source, result, 'inline')

    def test_valid_entities_in_template_calls(self):
        source = 'a {{test&copy;test}} and another: {{&diams;}}'
        result = u"[raw_text:'a '  internal_link:[page_name:'Template:test©test']  raw_text:' and another: '  internal_link:page_name['Template:♦']]"
        #self.parsed_equal_string(source, result, 'inline')
        import nose
        raise nose.SkipTest

    def test_invalid_entities_in_template_calls(self):
        source = 'a {{test&abcd;test}} and another: {{&efgh;}}'
        result = "[raw_text:'a '  allowed_char:'{'  allowed_char:'{'  raw_text:'test'  entity:'&abcd;'  raw_text:'test'  allowed_char:'}'  allowed_char:'}'  raw_text:' and another: '  allowed_char:'{'  allowed_char:'{'  entity:'&efgh;'  allowed_char:'}'  allowed_char:'}']"
        self.parsed_equal_string(source, result, 'inline')

########NEW FILE########
__FILENAME__ = test_tables
# -*- coding: utf8 -*-

from mediawiki_parser.tests import ParserTestCase


class TablesTests(ParserTestCase):
    def test_table_cell(self):
        source = 'style="color:red" | cell 1'
        result = """table_cell:
   table_parameter:
      HTML_attribute:
         attribute_name:style
         value_quote:color:red
   table_cell_content:
      raw_text: cell 1"""
        self.parsed_equal_tree(source, result, 'table_cell')

    def test_table_other_cell(self):
        source = '|| cell 1'
        result = "[table_cell_content:[raw_text:' cell 1']]"
        self.parsed_equal_string(source, result, 'table_other_cell')

    def test_table_special_line(self):
        source = '|-\n'
        result = ""
        self.parsed_equal_string(source, result, 'table_special_line')

    def test_table_line_with_css(self):
        source = '| style="color:red" | cell 1\n'
        result = """table_line_cells:
   table_cell:
      table_parameter:
         HTML_attribute:
            attribute_name:style
            value_quote:color:red
      table_cell_content:
         raw_text: cell 1"""
        self.parsed_equal_tree(source, result, 'table_line')

    def test_table_line_with_multiple_attributes(self):
        source = '| style="color:red" id=\'test\' name=test| cell 1\n'
        result = """table_line_cells:
   table_cell:
      table_parameter:
         HTML_attribute:
            attribute_name:style
            value_quote:color:red
         HTML_attribute:
            attribute_name:id
            value_apostrophe:test
         HTML_attribute:
            attribute_name:name
            value_noquote:test
      table_cell_content:
         raw_text: cell 1"""
        self.parsed_equal_tree(source, result, 'table_line')

    def test_table_line_without_css(self):
        source = '| cell 1\n'
        result = "[table_cell:[table_cell_content:[raw_text:' cell 1']]]"
        self.parsed_equal_string(source, result, 'table_line')

    def test_table_line_with_dash(self):
        source = '|data L2-B\n'
        result = "[table_cell:[table_cell_content:[raw_text:'data L2-B']]]"
        self.parsed_equal_string(source, result, 'table_line')

    def test_table_line_with_2_cells(self):
        source = '| cell 1 || cell 2\n'
        result = """table_line_cells:
   table_cell:
      table_cell_content:
         raw_text: cell 1 
   table_cell:
      table_cell_content:
         raw_text: cell 2"""
        self.parsed_equal_tree(source, result, 'table_line')

    def test_table_line_with_HTML_in_1st_cell(self):
        source = '| style="color:red" | cell 1 || cell 2\n'
        result = """table_line_cells:
   table_cell:
      table_parameter:
         HTML_attribute:
            attribute_name:style
            value_quote:color:red
      table_cell_content:
         raw_text: cell 1 
   table_cell:
      table_cell_content:
         raw_text: cell 2"""
        self.parsed_equal_tree(source, result, 'table_line')

    def test_table_line_with_HTML_in_2nd_cell(self):
        source = '| cell 1 || style="color:red" | cell 2\n'
        result = """table_line_cells:
   table_cell:
      table_cell_content:
         raw_text: cell 1 
   table_cell:
      table_parameter:
         HTML_attribute:
            attribute_name:style
            value_quote:color:red
      table_cell_content:
         raw_text: cell 2"""
        self.parsed_equal_tree(source, result, 'table_line')

    def test_table_header_with_css(self):
        source = '! scope=row | Line 1\n'
        result = """table_line_header:
   table_cell:
      table_parameter:
         HTML_attribute:
            attribute_name:scope
            value_noquote:row
      table_cell_content:
         raw_text: Line 1"""
        self.parsed_equal_tree(source, result, 'table_line')

    def test_table_line_with_global_css(self):
        source = '|- style="color:red"\n'
        result = "[table_parameters:[HTML_attribute:[attribute_name:'style'  value_quote:'color:red']]]"
        self.parsed_equal_string(source, result, 'table_line')

    def test_table_multiline_content(self):
        source = """{|
| test1
test2
|}
""" 
        result = """table:
   table_cell:
      table_cell_content:
         @clean_inline@:
            raw_text: test1
         table_multiline_content:
            table_paragraph:
               paragraph_line:
                  raw_text:test2"""
        self.parsed_equal_tree(source, result, 'table')

    def test_table_with_css(self):
        source = """{|
! cellA
! cellB
|- style="color:red"
| cell C
| cell D
|}
"""
        result = """table:
   table_line_header:
      table_cell:
         table_cell_content:
            raw_text: cellA
   table_line_header:
      table_cell:
         table_cell_content:
            raw_text: cellB
   table_line_break:
      table_parameters:
         HTML_attribute:
            attribute_name:style
            value_quote:color:red
   table_line_cells:
      table_cell:
         table_cell_content:
            raw_text: cell C
   table_line_cells:
      table_cell:
         table_cell_content:
            raw_text: cell D"""
        self.parsed_equal_tree(source, result, "table")

    def test_table_with_template(self):
        source = """{|
|+ Table {{title|parameter=yes}}
| cell 1 || cell 2
|-
| cell 3 || cell 4
|}
"""
        result = """table:
   table_title:
      raw_text: Table test: yes
   table_line_cells:
      table_cell:
         table_cell_content:
            raw_text: cell 1 
      table_cell:
         table_cell_content:
            raw_text: cell 2
   table_line_break:
   table_line_cells:
      table_cell:
         table_cell_content:
            raw_text: cell 3 
      table_cell:
         table_cell_content:
            raw_text: cell 4"""
        templates = {'title': 'test: {{{parameter}}}'}
        self.parsed_equal_tree(source, result, "table", templates)

    def test_table_with_HTML_and_template(self):
        source = """{| class="table" {{prettyTable}}
|+ style="color:red" | Table {{title|parameter}}
|-
|
! scope=col | Title A
! scope=col | Title B
|-
! scope=row | Line 1
|data L1.A
|data L1.B
|-
! scope=row | Line 2
|data L2.A
|data {{template|with|parameters=L2.B}}
|}
"""
        result = """table:
   table_begin:
      table_parameters:
         HTML_attribute:
            attribute_name:class
            value_quote:table
         HTML_attribute:
            attribute_name:style
            value_quote:color:blue
   table_content:
      table_title:
         table_parameter:
            HTML_attribute:
               attribute_name:style
               value_quote:color:red
         @inline@:
            raw_text: Table test: parameter
      table_line_break:
      table_empty_cell:
      table_line_header:
         table_cell:
            table_parameter:
               HTML_attribute:
                  attribute_name:scope
                  value_noquote:col
            table_cell_content:
               raw_text: Title A
      table_line_header:
         table_cell:
            table_parameter:
               HTML_attribute:
                  attribute_name:scope
                  value_noquote:col
            table_cell_content:
               raw_text: Title B
      table_line_break:
      table_line_header:
         table_cell:
            table_parameter:
               HTML_attribute:
                  attribute_name:scope
                  value_noquote:row
            table_cell_content:
               raw_text: Line 1
      table_line_cells:
         table_cell:
            table_cell_content:
               raw_text:data L1.A
      table_line_cells:
         table_cell:
            table_cell_content:
               raw_text:data L1.B
      table_line_break:
      table_line_header:
         table_cell:
            table_parameter:
               HTML_attribute:
                  attribute_name:scope
                  value_noquote:row
            table_cell_content:
               raw_text: Line 2
      table_line_cells:
         table_cell:
            table_cell_content:
               raw_text:data L2.A
      table_line_cells:
         table_cell:
            table_cell_content:
               raw_text:data with and L2.B..."""
        templates = {'prettyTable': 'style="color:blue"',
                     'title': 'test: {{{1}}}',
                     'template': '{{{1}}} and {{{parameters}}}...'}
        self.parsed_equal_tree(source, result, "table", templates)

    def test_nested_tables(self):
        source = """{| class="table" {{prettyTable}}
|+ style="color:red" | Table {{title|1=true}}
|-
! scope=col | First (mother)
! scope=col | table
|
{| class="table" {{prettyTable}}
|-
! scope=row | Second (daughter) table
|data L1.A
|data L1.B
|-
! scope=row | in the first one
|data L2.A
|data L2.B
|}
|-
| first
| table
| again
|}
"""
        result = """table:
   table_begin:
      table_parameters:
         HTML_attribute:
            attribute_name:class
            value_quote:table
         HTML_attribute:
            attribute_name:style
            value_quote:color:blue
   table_content:
      table_title:
         table_parameter:
            HTML_attribute:
               attribute_name:style
               value_quote:color:red
         @inline@:
            raw_text: Table test: true
      table_line_break:
      table_line_header:
         table_cell:
            table_parameter:
               HTML_attribute:
                  attribute_name:scope
                  value_noquote:col
            table_cell_content:
               raw_text: First (mother)
      table_line_header:
         table_cell:
            table_parameter:
               HTML_attribute:
                  attribute_name:scope
                  value_noquote:col
            table_cell_content:
               raw_text: table
      table_line_cells:
         table_cell:
            table_cell_content:
               @table_structure@:
                  table_begin:
                     table_parameters:
                        HTML_attribute:
                           attribute_name:class
                           value_quote:table
                        HTML_attribute:
                           attribute_name:style
                           value_quote:color:blue
                  table_content:
                     table_line_break:
                     table_line_header:
                        table_cell:
                           table_parameter:
                              HTML_attribute:
                                 attribute_name:scope
                                 value_noquote:row
                           table_cell_content:
                              raw_text: Second (daughter) table
                     table_line_cells:
                        table_cell:
                           table_cell_content:
                              raw_text:data L1.A
                     table_line_cells:
                        table_cell:
                           table_cell_content:
                              raw_text:data L1.B
                     table_line_break:
                     table_line_header:
                        table_cell:
                           table_parameter:
                              HTML_attribute:
                                 attribute_name:scope
                                 value_noquote:row
                           table_cell_content:
                              raw_text: in the first one
                     table_line_cells:
                        table_cell:
                           table_cell_content:
                              raw_text:data L2.A
                     table_line_cells:
                        table_cell:
                           table_cell_content:
                              raw_text:data L2.B
      table_line_break:
      table_line_cells:
         table_cell:
            table_cell_content:
               raw_text: first
      table_line_cells:
         table_cell:
            table_cell_content:
               raw_text: table
      table_line_cells:
         table_cell:
            table_cell_content:
               raw_text: again"""
        templates = {'prettyTable': 'style="color:blue"',
                     'title': 'test: {{{1}}}'}
        self.parsed_equal_tree(source, result, "table", templates)

########NEW FILE########
__FILENAME__ = test_tags
# -*- coding: utf8 -*-

from mediawiki_parser.tests import ParserTestCase


class TagsTests(ParserTestCase):
    def test_basic_tag(self):
        source = '<a>'
        result = "[tag_name:'a']"
        self.parsed_equal_string(source, result, 'tag')

    def test_open_tag_with_standalone_attribute(self):
        # Not correct in XML but correct in HTML
        source = '<table noborder>'
        result = """tag_open:
   tag_name:table
   optional_attributes:
      optional_attribute:
         attribute_name:noborder"""
        self.parsed_equal_tree(source, result, 'tag')

    def test_open_tag_with_attribute(self):
        source = '<a style="color:red">'
        result = """tag_open:
   tag_name:a
   optional_attributes:
      optional_attribute:
         attribute_name:style
         value_quote:color:red"""
        self.parsed_equal_tree(source, result, 'tag')

    def test_autoclose_tag_with_attribute(self):
        source = '<img src="http://www.mozilla.org/test.png"/>'
        result = """tag_autoclose:
   tag_name:img
   optional_attributes:
      optional_attribute:
         attribute_name:src
         value_quote:http://www.mozilla.org/test.png"""
        self.parsed_equal_tree(source, result, 'tag')

    def test_url_in_tag_attribute(self):
        source = '<a href="http://www.mozilla.org" style="color:red">'
        result = """tag_open:
   tag_name:a
   optional_attributes:
      optional_attribute:
         attribute_name:href
         value_quote:http://www.mozilla.org
      optional_attribute:
         attribute_name:style
         value_quote:color:red"""
        self.parsed_equal_tree(source, result, 'tag')

    def test_multiple_tags(self):
        source = 'a <tag name="mytag" attribute=value /> and <span style=\'color: red\'>text</span>...'
        result = """@inline@:
   raw_text:a 
   tag_autoclose:
      tag_name:tag
      optional_attributes:
         optional_attribute:
            attribute_name:name
            value_quote:mytag
         optional_attribute:
            attribute_name:attribute
            value_noquote:value
   raw_text: and 
   tag_open:
      tag_name:span
      optional_attributes:
         optional_attribute:
            attribute_name:style
            value_apostrophe:color: red
   raw_text:text
   tag_close:
      tag_name:span
   raw_text:..."""
        self.parsed_equal_tree(source, result, 'inline')

########NEW FILE########
__FILENAME__ = test_templates
# -*- coding: utf8 -*-

from mediawiki_parser.tests import PreprocessorTestCase


class TemplatesTests(PreprocessorTestCase):
    def test_existent_template_without_parameter(self):
        source = "a {{Template}}"
        result = "a template content"
        templates = {'Template': 'template content'}
        self.parsed_equal_string(source, result, templates)

    def test_nonexistant_template_without_parameter(self):
        source = "a {{test}}"
        result = "a [[Template:test]]"
        self.parsed_equal_string(source, result)

    def test_numeric_template_parameter(self):
        source = "{{{1}}}"
        result = "{{{1}}}"
        self.parsed_equal_string(source, result)

    def test_text_template_parameter(self):
        source = "{{{A text}}}"
        result = "{{{A text}}}"
        self.parsed_equal_string(source, result)

    def test_template_name_as_parameter_name(self):
        "Template should of course not be substituted in this case."
        source = "a {{{Template}}}"
        result = "a {{{Template}}}"
        templates = {'Template': 'template content'}
        self.parsed_equal_string(source, result, templates)

    def test_template_parameter_with_default_value(self):
        source = "{{{parameter name|default value}}}"
        result = "default value"
        self.parsed_equal_string(source, result)

    def test_template_parameter_with_void_default_value(self):
        source = "{{{parameter name|}}}"
        result = ""
        self.parsed_equal_string(source, result)

    def test_nested_default_values(self):
        source = "Cheese or dessert? Person1: {{menu|cheese=camembert}}; person2: {{menu|dessert=apple}}; person3: {{menu}}."
        result = "Cheese or dessert? Person1: Menu: camembert; person2: Menu: apple; person3: Menu: not cheese nor dessert."
        templates = {'menu': 'Menu: {{{cheese|{{{dessert|not cheese nor dessert}}}}}}'}
        self.parsed_equal_string(source, result, templates)

    def test_template_with_parameters(self):
        source = "{{Template with|1=parameter| 2 = parameters}}"
        result = "test parameter parameters"
        templates = {'Template with': 'test {{{1}}} {{{2}}}'}
        self.parsed_equal_string(source, result, templates)

    def test_template_with_automatic_numbering_parameters(self):
        source = "a {{Template with|parameter1|parameter2}}"
        result = "a test: parameter1 parameter2"
        templates = {'Template with': 'test: {{{1}}} {{{2}}}'}
        self.parsed_equal_string(source, result, templates)

    def test_equal_in_template_parameter(self):
        source = "a {{Template with|1=a=b|2=text text = test test}}"
        result = "a test: a=b text text = test test"
        templates = {'Template with': 'test: {{{1}}} {{{2}}}'}
        self.parsed_equal_string(source, result, templates)

    def test_empty_template_parameter(self):
        "We pass an empty value, which is different than no value at all."
        source = "a {{Template with|1=}}"
        result = "a test: "
        templates = {'Template with': 'test: {{{1}}}'}
        self.parsed_equal_string(source, result, templates)

    def test_pipe_in_template_parameter(self):
        source = "a {{Template with|apple{{!}}orange{{!}}lemon}}"
        result = "a test: apple|orange|lemon"
        templates = {'Template with': 'test: {{{1}}}',
                     '!': '|'}
        self.parsed_equal_string(source, result, templates)

    def test_template_parameters_precedence(self):
        "Defining a second time the same parameter should overwrite the previous one"
        source = "a {{Template with|parameter1|1=parameter2}}"
        result = "a test: parameter2"
        templates = {'Template with': 'test: {{{1}}}'}
        self.parsed_equal_string(source, result, templates)

    def test_template_with_multiline_named_parameters(self):
        source = """{{Template which
 | has = test1
continues here
 | multi = test2
 | line parameters = test3
}}"""
        result = "Tests: test1\ncontinues here test3 test2..."
        templates = {'Template which': 'Tests: {{{has}}} {{{line parameters}}} {{{multi}}}...'}
        self.parsed_equal_string(source, result, templates)

    def test_template_with_special_chars_in_parameters(self):
        source = "Special chars: {{Template with|1=#<>--| two = '{'}'[']'}}."
        result = "Special chars: test #<>-- '{'}'[']' default."
        templates = {'Template with': 'test {{{1}}} {{{two}}} {{{other param|default}}}'}
        self.parsed_equal_string(source, result, templates)

    def test_template_with_special_chars_in_standalone_parameter(self):
        source = "Special chars: {{Template with|#<>--|'{'}'[']'}}."
        result = "Special chars: test #<>-- '{'}'[']' default."
        templates = {'Template with': 'test {{{1}}} {{{2}}} {{{other param|default}}}'}
        self.parsed_equal_string(source, result, templates)

    def test_links_in_template_arguments(self):
        source = "A {{Template with|1=[http://www.mozilla.org a link] |2=[[inside]] | 3 = [[the|parameters]]}}."
        result = "A test: [http://www.mozilla.org a link]  [[inside]]  [[the|parameters]]."
        templates = {'Template with': 'test: {{{1}}} {{{2}}} {{{3}}}'}
        self.parsed_equal_string(source, result, templates)

    def test_formatted_template_arguments(self):
        "The formatted arguments are allowed, but will be processed in the parser, not in the preprocessor."
        source = "A {{Template with|an argument ''in italic'' |and another one '''in bold'''}}."
        result = "A test: an argument ''in italic''  and another one '''in bold'''."
        templates = {'Template with': 'test: {{{1}}} {{{2}}}'}
        self.parsed_equal_string(source, result, templates)

    def test_template_in_nowiki_section(self):
        "<nowiki> sections must be left untouched"
        source = "a <nowiki>{{Template with|an argument ''in italic'' |and another one '''in bold'''}} section </nowiki>."
        result = "a <nowiki>{{Template with|an argument ''in italic'' |and another one '''in bold'''}} section </nowiki>."
        self.parsed_equal_string(source, result)

    def test_template_in_preformatted_section(self):
        "<pre> sections must be left untouched"
        source = "a <pre>{{Template with|an argument ''in italic'' |and another one '''in bold'''}} section </pre>."
        result = "a <pre>{{Template with|an argument ''in italic'' |and another one '''in bold'''}} section </pre>."
        self.parsed_equal_string(source, result)

    def test_nested_template(self):
        source = "A {{Template with|{{other|inside}}}}."
        result = "A test is inside."
        templates = {'Template with': 'test {{{1}}}',
                     'other': 'is {{{1}}}'}
        self.parsed_equal_string(source, result, templates)

    def test_nested_templates(self):
        source = "{{Template with|1={{other}} |2= {{templates}}| 3 = {{nested|inside=1}} }}"
        result = "1: [[Template:other]] ; 2: another nested template with parameter inside!; 3: nested template with parameter 1 "
        templates = {'Template with': '1: {{{1}}}; 2: {{{2}}}; 3: {{{3}}}',
                     'templates': 'another {{nested|inside = inside}}!',
                     'nested': 'nested template with parameter {{{inside}}}'}
        self.parsed_equal_string(source, result, templates)

    def test_nested_templates_with_tag(self):
        source = "{{Template with|1=<tag>{{other}}}}"
        result = "1: <tag>[[Template:other]]"
        templates = {'Template with': '1: {{{1}}}'}
        self.parsed_equal_string(source, result, templates)

    def test_self_nested_templates(self):
        source = "{{template 2|1=Value1|name={{template 2|1=Value1|name=Value for name}}}}"
        result = '"Template 2" has 2 parameters: Value1 and: "Template 2" has 2 parameters: Value1 and: Value for name!!'
        templates = {'template 2': '"Template 2" has 2 parameters: {{{1}}} and: {{{name|default}}}!'}
        self.parsed_equal_string(source, result, templates)

    def test_infinite_loop_calls_protection(self):
        source = "We call {{a}} and {{b}}"
        result = 'We call calls calls calls Infinite template call detected! and calls calls Infinite template call detected!'
        templates = {'a': 'calls {{b}}',
                     'b': 'calls {{c}}',
                     'c': 'calls {{a}}'}
        self.parsed_equal_string(source, result, templates)

    def test_finite_loop_calls(self):
        source = "A call {{aa|{{bb}}}}"
        result = 'A call calls calls calls calls end'
        templates = {'aa': 'calls {{{1|end}}}',
                     'bb': 'calls {{cc}}',
                     'cc': 'calls {{aa}}'}
        self.parsed_equal_string(source, result, templates)

########NEW FILE########
__FILENAME__ = test_text_postprocessor
# -*- coding: utf8 -*-

from mediawiki_parser.tests import PostprocessorTestCase


class TextBackendTests(PostprocessorTestCase):
    def test_simple_title(self):
        source = '= A title =\n'
        result = ' A title \n'
        self.parsed_equal_string(source, result, 'wikitext', {}, 'text')

    def test_simple_title2(self):
        source = '== A title ==\n'
        result = ' A title \n'
        self.parsed_equal_string(source, result, 'wikitext', {}, 'text')

    def test_simple_title3(self):
        source = '=== A title ===\n'
        result = ' A title \n'
        self.parsed_equal_string(source, result, 'wikitext', {}, 'text')

    def test_simple_title4(self):
        source = '==== A title ====\n'
        result = ' A title \n'
        self.parsed_equal_string(source, result, 'wikitext', {}, 'text')

    def test_simple_title5(self):
        source = '==== A title ====\n'
        result = ' A title \n'
        self.parsed_equal_string(source, result, 'wikitext', {}, 'text')

    def test_simple_title6(self):
        source = '====== Test! ======\n'
        result = ' Test! \n'
        self.parsed_equal_string(source, result, 'wikitext', {}, 'text')

    def test_simple_title_without_method(self):
        source = '= A title =\n'
        result = ' A title \n'
        self.parsed_equal_string(source, result, None, {}, 'text')

    def test_simple_title2_without_method(self):
        source = '== A title ==\n'
        result = ' A title \n'
        self.parsed_equal_string(source, result, None, {}, 'text')

    def test_simple_title3_without_method(self):
        source = '=== A title ===\n'
        result = ' A title \n'
        self.parsed_equal_string(source, result, None, {}, 'text')

    def test_simple_title4_without_method(self):
        source = '==== A title ====\n'
        result = ' A title \n'
        self.parsed_equal_string(source, result, None, {}, 'text')

    def test_simple_title5_without_method(self):
        source = '==== A title ====\n'
        result = ' A title \n'
        self.parsed_equal_string(source, result, None, {}, 'text')

    def test_simple_title6_without_method(self):
        source = '====== Test! ======\n'
        result = ' Test! \n'
        self.parsed_equal_string(source, result, None, {}, 'text')

    def test_simple_allowed_open_tag(self):
        source = 'a<p>test'
        result = 'a\ntest'
        self.parsed_equal_string(source, result, 'inline', {}, 'text')

    def test_complex_allowed_open_tag(self):
        """ The attributes are ignored. """
        source = 'a<p class="wikitext" style="color:red" onclick="javascript:alert()">test'
        result = 'a\ntest'
        self.parsed_equal_string(source, result, 'inline', {}, 'text')

    def test_simple_disallowed_open_tag(self):
        source = '<a>'
        result = '<a>'
        self.parsed_equal_string(source, result, 'inline', {}, 'text')

    def test_complex_disallowed_open_tag(self):
        source = '<a href="test" class="test" style="color:red" anything="anything">'
        result = '<a href="test" class="test" style="color:red" anything="anything">'
        self.parsed_equal_string(source, result, 'inline', {}, 'text')

    def test_simple_allowed_autoclose_tag(self):
        source = 'a<br />test'
        result = 'a\ntest'
        self.parsed_equal_string(source, result, 'inline', {}, 'text')

    def test_complex_allowed_autoclose_tag(self):
        source = 'one more <br name="test" /> test'
        result = 'one more \n test'
        self.parsed_equal_string(source, result, 'inline', {}, 'text')

    def test_simple_disallowed_autoclose_tag(self):
        source = '<test />'
        result = '<test />'
        self.parsed_equal_string(source, result, 'inline', {}, 'text')

    def test_complex_disallowed_autoclose_tag(self):
        source = '<img src="file.png" />'
        result = '<img src="file.png" />'
        self.parsed_equal_string(source, result, 'inline', {}, 'text')

    def test_italic(self):
        source = "Here, we have ''italic'' text.\n"
        result = "Here, we have _italic_ text.\n"
        self.parsed_equal_string(source, result, None, {}, 'text')

    def test_bold(self):
        source = "Here, we have '''bold''' text.\n"
        result = "Here, we have *bold* text.\n"
        self.parsed_equal_string(source, result, None, {}, 'text')

    def test_bold_and_italic_case1(self):
        source = "Here, we have '''''bold and italic''''' text.\n"
        result = "Here, we have _*bold and italic*_ text.\n"
        self.parsed_equal_string(source, result, None, {}, 'text')

    def test_bold_italic_case2(self):
        source = "Here, we have ''italic only and '''bold and italic''''' text.\n"
        result = "Here, we have _italic only and *bold and italic*_ text.\n"
        self.parsed_equal_string(source, result, None, {}, 'text')

    def test_bold_italic_case3(self):
        source = "Here, we have '''bold only and ''bold and italic''''' text.\n"
        result = "Here, we have *bold only and _bold and italic_* text.\n"
        self.parsed_equal_string(source, result, None, {}, 'text')

    def test_bold_italic_case4(self):
        source = "Here, we have '''''bold and italic''' and italic only''.\n"
        result = "Here, we have _*bold and italic* and italic only_.\n"
        self.parsed_equal_string(source, result, None, {}, 'text')

    def test_bold_italic_case5(self):
        source = "Here, we have '''''bold and italic'' and bold only'''.\n"
        result = "Here, we have *_bold and italic_ and bold only*.\n"
        self.parsed_equal_string(source, result, None, {}, 'text')

    def test_bold_italic_case6(self):
        source = "Here, we have ''italic, '''bold and italic''' and italic only''.\n"
        result = "Here, we have _italic, *bold and italic* and italic only_.\n"
        self.parsed_equal_string(source, result, None, {}, 'text')

    def test_bold_italic_case7(self):
        source = "Here, we have '''bold, ''bold and italic'' and bold only'''.\n"
        result = "Here, we have *bold, _bold and italic_ and bold only*.\n"
        self.parsed_equal_string(source, result, None, {}, 'text')

    def test_bold_italic_case8(self):
        source = """'''Le gras :'''

et l'''italique''...
"""
        result = "*Le gras :*\net l'_italique_...\n"
        self.parsed_equal_string(source, result, None, {}, 'text')

    def test_italic_template(self):
        source = "Here, we have ''italic {{template}}!''.\n"
        result = "Here, we have _italic text!_.\n"
        templates = {'template': 'text'}
        self.parsed_equal_string(source, result, None, templates, 'text')

    def test_styles_in_template(self):
        source = "Here, we have {{template}}.\n"
        result = "Here, we have *text* and _more text_ and _*still more text*_.\n"
        templates = {'template': "'''text''' and ''more text'' and '''''still more text'''''"}
        self.parsed_equal_string(source, result, None, templates, 'text')

########NEW FILE########
__FILENAME__ = test_titles
# -*- coding: utf8 -*-

from mediawiki_parser.tests import ParserTestCase


class TitlesTests(ParserTestCase):
    def test_title1(self):
        source = '=Title 1=\n'
        result = "[title1:[raw_text:'Title 1']]"
        self.parsed_equal_string(source, result, None)

    def test_title2(self):
        source = '== Title 2 ==\n'
        result = "[title2:[raw_text:' Title 2 ']]"
        self.parsed_equal_string(source, result, None)

    def test_title3_extra_spacetab(self):
        # Ignore extra spaces and tabs
        source = '===Title 3===                    \n'
        result = "[title3:[raw_text:'Title 3']]"
        self.parsed_equal_string(source, result, None)

    def test_title4(self):
        source = '==== Title 4 ====\n'
        result = "[title4:[raw_text:' Title 4 ']]"
        self.parsed_equal_string(source, result, None)

    def test_title5(self):
        source = '===== Title 5 =====\n'
        result = "[title5:[raw_text:' Title 5 ']]"
        self.parsed_equal_string(source, result, None)

    def test_title6(self):
        source = '====== Title 6 ======\n'
        result = "[title6:[raw_text:' Title 6 ']]"
        self.parsed_equal_string(source, result, None)

    def test_title7(self):
        # Max level is 6; keep extra equals
        source = '======= Title 6 =======\n'
        result = "[title6:[raw_text:'= Title 6 =']]"
        self.parsed_equal_string(source, result, None)

    def test_link_in_title(self):
        source = '= [[a link]] =\n'
        result = "[title1:[raw_text:' '  internal_link:[page_name:'a link']  raw_text:' ']]"
        self.parsed_equal_string(source, result, None)

    def test_italic_in_title(self):
        source = "== ''italic text'' ==\n"
        result = "[title2:[raw_text:' \'\'italic text\'\' ']]"
        self.parsed_equal_string(source, result, None)

    def test_bold_in_title(self):
        source = "=== '''bold text''' ===\n"
        result = "[title3:[raw_text:' \'\'\'bold text\'\'\' ']]"
        self.parsed_equal_string(source, result, None)

    def test_formatted_link_in_title(self):
        source = "==== [[Title 4|formatted link]] ====\n"
        result = "[title4:[raw_text:' '  internal_link:[page_name:'Title 4'  link_arguments:[link_argument:[raw_text:'formatted link']]]  raw_text:' ']]"
        self.parsed_equal_string(source, result, None)

    def test_simple_template_in_title(self):
        source = '===== {{Title 5}} =====\n'
        result = "[title5:[raw_text:' '  internal_link:[page_name:'Template:Title 5']  raw_text:' ']]"
        self.parsed_equal_string(source, result, None)

    def test_braces_in_title(self):
        source = '====== { Title 6} ======\n'
        result = "[title6:[raw_text:' '  allowed_char:'{'  raw_text:' Title 6'  allowed_char:'}'  raw_text:' ']]"
        self.parsed_equal_string(source, result, None)

    def test_equal_in_title(self):
        source = '== Title = title ==\n'
        result = "[title2:[raw_text:' Title = title ']]"
        self.parsed_equal_string(source, result, None)

    def test_more_equal_in_title(self):
        source = '== Title == title ==\n'
        result = "[title2:[raw_text:' Title == title ']]"
        self.parsed_equal_string(source, result, None)

########NEW FILE########
__FILENAME__ = text
from constants import html_entities
from mediawiki_parser import wikitextParser
import apostrophes

def toolset():
    def render_tag_p(attributes):
        return '\n'

    def render_tag_br(attributes):
        return '\n'

    allowed_tags = {'p': render_tag_p,
                    'br': render_tag_br}

    def render_title1(node):
        node.value = '%s\n' % node.leaf()

    def render_title2(node):
        node.value = '%s\n' % node.leaf()

    def render_title3(node):
        node.value = '%s\n' % node.leaf()

    def render_title4(node):
        node.value = '%s\n' % node.leaf()

    def render_title5(node):
        node.value = '%s\n' % node.leaf()

    def render_title6(node):
        node.value = '%s\n' % node.leaf()

    def render_raw_text(node):
        pass

    def render_paragraph(node):
        node.value = '%s\n' % node.leaf()

    def render_wikitext(node):
        pass

    def render_body(node):
        tags = {'bold': '*', 'bold_close': '*', 'italic': '_', 'italic_close': '_'}
        node.value = apostrophes.parse('%s' % node.leaves(), tags)

    def render_entity(node):
        value = '%s' % node.leaf()
        if value in html_entities:
            node.value = '%s' % unichr(html_entities[value])
        else:
            node.value = '&%s;' % value

    def render_lt(node):
        pass

    def render_gt(node):
        pass

    def process_attribute(node, allowed_tag):
        assert len(node.value) == 2, "Bad AST shape!"
        attribute_name = node.value[0].value
        attribute_value = node.value[1].value
        return '%s="%s"' % (attribute_name, attribute_value)

    def process_attributes(node, allowed_tag):
        result = ''
        if len(node.value) == 1:
            pass
        elif len(node.value) == 2:
            attributes = node.value[1].value
            for i in range(len(attributes)):
                attribute = process_attribute(attributes[i], allowed_tag)
                if attribute is not '':
                    result += ' ' + attribute 
        else:
            raise Exception("Bad AST shape!")
        return result

    def render_attribute(node):
        node.value = process_attribute(node, True)

    def render_tag_open(node):
        tag_name = node.value[0].value
        if tag_name in allowed_tags:
            attributes = process_attributes(node, True)
            tag_processor = allowed_tags[tag_name]
            node.value = tag_processor(attributes) 
        else:
            attributes = process_attributes(node, False)
            node.value = '<%s%s>' % (tag_name, attributes)

    def render_tag_close(node):
        node.value = ''

    def render_tag_autoclose(node):
        tag_name = node.value[0].value
        if tag_name in allowed_tags:
            attributes = process_attributes(node, True)
            tag_processor = allowed_tags[tag_name]
            node.value = tag_processor(attributes) 
        else:
            attributes = process_attributes(node, False)
            node.value = '<%s%s />' % (tag_name, attributes)

    def render_table(node):
        pass

    def render_table_line_break(node):
        node.value = '\n'

    def render_table_header_cell(node):
        pass

    def render_table_normal_cell(node):
        pass

    def render_table_empty_cell(node):
        pass

    def render_table_caption(node):
        pass

    def render_preformatted(node):
        pass

    def render_hr(node):
        node.value = '------'

    def render_li(node):
        pass

    def render_list(node):
        pass

    def render_url(node):
        pass

    def render_external_link(node):
        pass

    def render_internal_link(node):
        pass

    return locals()

def make_parser():
    return wikitextParser.make_parser(toolset())

########NEW FILE########
__FILENAME__ = wikitextParser
""" wikitext
<definition>
# Codes

    LF                      : '
'
    CR                      : '
'
    EOL                     : LF / CR                                                               : drop
    L_BRACKET               : "["                                                                   : drop
    R_BRACKET               : "\]"                                                                  : drop
    L_BRACE                 : "{"                                                                   : drop
    R_BRACE                 : "}"                                                                   : drop
    SPACE                   : " "                                                                   : drop
    TAB                     : "	"                                                                   : drop
    SPACETAB                : SPACE / TAB                                                           : drop
    SPACETABEOL             : SPACE / TAB / EOL                                                     : drop
    AMP                     : "&"                                                                   : drop
    PIPE                    : "|"                                                                   : drop
    BANG                    : "!"                                                                   : drop
    EQUAL                   : "="                                                                   : drop
    BULLET                  : "*"                                                                   : drop
    HASH                    : "#"                                                                   : drop
    COLON                   : ":"                                                                   : drop
    LT                      : "<"                                                                   : render_lt
    GT                      : ">"                                                                   : render_gt
    SLASH                   : "/"                                                                   : drop
    SEMICOLON               : ";"                                                                   : drop
    DASH                    : "-"                                                                   : drop
    TABLE_BEGIN             : "{|"                                                                  : drop
    TABLE_END               : "|}"                                                                  : drop
    TABLE_NEWLINE           : "|-"                                                                  : drop
    TABLE_TITLE             : "|+"                                                                  : drop
    QUOTE                   : "\""                                                                  : drop
    APOSTROPHE              : "\'"                                                                  : drop
    TITLE6_BEGIN            : EQUAL{6}                                                              : drop
    TITLE5_BEGIN            : EQUAL{5}                                                              : drop
    TITLE4_BEGIN            : EQUAL{4}                                                              : drop
    TITLE3_BEGIN            : EQUAL{3}                                                              : drop
    TITLE2_BEGIN            : EQUAL{2}                                                              : drop
    TITLE1_BEGIN            : EQUAL{1}                                                              : drop
    TITLE6_END              : EQUAL{6} SPACETAB* EOL                                                : drop
    TITLE5_END              : EQUAL{5} SPACETAB* EOL                                                : drop
    TITLE4_END              : EQUAL{4} SPACETAB* EOL                                                : drop
    TITLE3_END              : EQUAL{3} SPACETAB* EOL                                                : drop
    TITLE2_END              : EQUAL{2} SPACETAB* EOL                                                : drop
    TITLE1_END              : EQUAL{1} SPACETAB* EOL                                                : drop
    LINK_BEGIN              : L_BRACKET{2}                                                          : drop
    LINK_END                : R_BRACKET{2}                                                          : drop

# Protocols

    HTTPS                   : "https://"                                                            : liftValue
    HTTP                    : "http://"                                                             : liftValue
    FTP                     : "ftp://"                                                              : liftValue
    protocol                : HTTPS / HTTP / FTP                                                    : liftValue

# Predefined tags

    NOWIKI_BEGIN            : "<nowiki>"                                                            : drop
    NOWIKI_END              : "</nowiki>"                                                           : drop
    PRE_BEGIN               : "<pre>"                                                               : drop
    PRE_END                 : "</pre>"                                                              : drop
    SPECIAL_TAG             : NOWIKI_BEGIN/NOWIKI_END/PRE_BEGIN/PRE_END

# Characters

    ESC_CHAR                : L_BRACKET/R_BRACKET/protocol/PIPE/L_BRACE/R_BRACE/LT/GT/SLASH/AMP/SEMICOLON/TAB
    TITLE_END               : TITLE6_END/TITLE5_END/TITLE4_END/TITLE3_END/TITLE2_END/TITLE1_END
    ESC_SEQ                 : SPECIAL_TAG / ESC_CHAR / TITLE_END
    tab_to_space            : TAB+                                                                  : replace_by_space
    raw_char                : (!ESC_SEQ [\x20..\xff])
    raw_text                : raw_char+                                                             : join render_raw_text
    alpha_num               : [a..zA..Z0..9]
    alpha_num_text          : alpha_num+                                                            : join
    any_char                : [\x20..\xff] / tab_to_space
    any_text                : any_char+                                                             : join

# HTML tags

    value_quote             : QUOTE ((!(GT/QUOTE) any_char) / TAB)+ QUOTE                           : join
    value_apostrophe        : APOSTROPHE ((!(GT/APOSTROPHE) any_char) / TAB)+ APOSTROPHE            : join
    value_noquote           : (!(GT/SPACETAB/SLASH) raw_char)+                                      : join
    attribute_value         : (EQUAL (value_quote / value_apostrophe / value_noquote))              : liftNode
    attribute_name          : (!(EQUAL/SLASH/SPACETAB) raw_char)+                                   : join
    tag_name                : (!(SPACE/SLASH) alpha_num)+                                           : join
    optional_attribute      : SPACETABEOL+ attribute_name attribute_value?
    optional_attributes     : optional_attribute*
    tag_lt                  : LT                                                                    : drop
    tag_gt                  : GT                                                                    : drop
    tag_open                : tag_lt tag_name optional_attributes SPACETABEOL* tag_gt               : render_tag_open
    tag_close               : tag_lt SLASH tag_name tag_gt                                          : render_tag_close
    tag_autoclose           : tag_lt tag_name optional_attributes SPACETABEOL* SLASH tag_gt         : render_tag_autoclose
    tag                     : tag_autoclose / tag_open / tag_close

# HTML entities

    entity                  : AMP alpha_num_text SEMICOLON                                          : render_entity

# HTML comments

    # HTML comments are totally ignored and do not appear in the final text
    comment_content         : ((!(DASH{2} GT) [\x20..\xff])+ / SPACETABEOL)*
    html_comment            : tag_lt BANG DASH{2} comment_content DASH{2} tag_gt                    : drop
    optional_comment        : html_comment*

# Text

    page_name               : (raw_char / '/')+                                                     : join
# TODO: allow IPv6 addresses (http://[::1]/etc)
    address                 : (!(QUOTE/R_BRACKET) [\x21..\xff])+                                    : liftValue
    url                     : protocol address                                                      : join
    inline_url              : url{1}                                                                : render_url

# Links

    allowed_in_link         : (!(R_BRACKET/PIPE) ESC_CHAR)+                                         : restore join
    link_text               : (clean_inline / allowed_in_link)*                                     : liftValue
    link_argument           : PIPE link_text                                                        : liftValue
    link_arguments          : link_argument*
    internal_link           : LINK_BEGIN page_name link_arguments LINK_END                          : render_internal_link
    optional_link_text      : SPACETAB+ link_text                                                   : liftValue
    external_link           : L_BRACKET url optional_link_text? R_BRACKET                           : render_external_link
    link                    : internal_link / external_link

# Pre and nowiki tags

    # Preformatted acts like nowiki (disables wikitext parsing)
    tab_to_2_spaces         : TAB                                                                   : replace_by_2_spaces
    pre_text                : (tab_to_2_spaces / (!PRE_END any_char))*                              : join
    preformatted            : PRE_BEGIN pre_text PRE_END                                            : liftValue
    # We allow any char without parsing them as long as the tag is not closed
    eol_to_space            : EOL*                                                                  : replace_by_space
    nowiki_text             : (!NOWIKI_END (any_char/eol_to_space))*                                : join
    nowiki                  : NOWIKI_BEGIN nowiki_text NOWIKI_END                                   : liftValue

# Text types

    styled_text             : link / inline_url / html_comment / tag / entity
    not_styled_text         : preformatted / nowiki
    allowed_char            : ESC_CHAR{1}                                                           : restore liftValue
    allowed_text            : raw_text / LT / GT / tab_to_space / allowed_char
    clean_inline            : (not_styled_text / styled_text / raw_text)+                           : @
    inline                  : (not_styled_text / styled_text / allowed_text)+                       : @

# Paragraphs

    special_line_begin      : SPACE/EQUAL/BULLET/HASH/COLON/DASH{4}/TABLE_BEGIN/SEMICOLON
    paragraph_line          : !special_line_begin inline EOL                                        : liftValue
    blank_paragraph         : EOL{2}                                                                : drop keep
    paragraph               : paragraph_line+                                                       : liftValue render_paragraph
    paragraphs              : (blank_paragraph/EOL/paragraph)+

# Titles

    title6                  : TITLE6_BEGIN inline TITLE6_END                                        : liftValue render_title6
    title5                  : TITLE5_BEGIN inline TITLE5_END                                        : liftValue render_title5
    title4                  : TITLE4_BEGIN inline TITLE4_END                                        : liftValue render_title4
    title3                  : TITLE3_BEGIN inline TITLE3_END                                        : liftValue render_title3
    title2                  : TITLE2_BEGIN inline TITLE2_END                                        : liftValue render_title2
    title1                  : TITLE1_BEGIN inline TITLE1_END                                        : liftValue render_title1
    title                   : title6 / title5 / title4 / title3 / title2 / title1

# Lists

    LIST_CHAR               : BULLET / HASH / COLON / SEMICOLON
    list_leaf_content       : !LIST_CHAR inline EOL                                                 : liftValue

    bullet_list_leaf        : BULLET optional_comment list_leaf_content                             : liftValue
    bullet_sub_list         : BULLET optional_comment list_item                                     : @

    number_list_leaf        : HASH optional_comment list_leaf_content                               : liftValue
    number_sub_list         : HASH optional_comment list_item                                       : @

    colon_list_leaf         : COLON optional_comment list_leaf_content                              : liftValue
    colon_sub_list          : COLON optional_comment list_item                                      : @

    semi_colon_list_leaf    : SEMICOLON optional_comment list_leaf_content                          : liftValue
    semi_colon_sub_list     : SEMICOLON optional_comment list_item                                  : @

    list_leaf               : semi_colon_list_leaf/colon_list_leaf/number_list_leaf/bullet_list_leaf: @
    sub_list                : semi_colon_sub_list/colon_sub_list/number_sub_list/bullet_sub_list    : @
    list_item               : sub_list / list_leaf                                                  : @
    list                    : list_item+                                                            : render_list

# Preformatted

    EOL_KEEP                : EOL                                                                   : restore
    tab_to_8_spaces         : TAB                                                                   : replace_by_8_spaces
    any_char_but_tab        : raw_text / LT / GT / (!TAB ESC_CHAR)                                  : join
    preformatted_inline     : (tab_to_8_spaces / not_styled_text / styled_text / any_char_but_tab)+
    preformatted_line       : SPACE preformatted_inline EOL_KEEP                                    : liftValue
    preformatted_lines      : preformatted_line+
    preformatted_text       : preformatted_inline EOL?                                              : liftValue
    preformatted_paragraph  : PRE_BEGIN EOL preformatted_text PRE_END EOL
    preformatted_group      : preformatted_paragraph / preformatted_lines                           : render_preformatted

# Special lines

    horizontal_rule         : DASH{4} DASH* inline* EOL                                             : liftValue keep render_hr

    # This should never happen
    invalid_line            : any_text EOL                                                          : liftValue

# Tables

    HTML_attribute          : SPACETAB* attribute_name attribute_value SPACETAB*                    : render_attribute
    table_parameters_pipe   : (SPACETAB* HTML_attribute+ SPACETAB* PIPE !PIPE)?                     : liftNode
    table_parameters        : (HTML_attribute / clean_inline)+
    table_parameter         : table_parameters_pipe{0..1}                                           : liftValue
    table_wikitext          : list/horizontal_rule/preformatted_group/title/table_structure
    table_inline            : !(PIPE/BANG) clean_inline EOL?                                        : liftNode
    table_paragraph         : (!(PIPE/BANG/TABLE_NEWLINE/TABLE_TITLE/TABLE_END) paragraph_line)     : render_paragraph
    table_multiline_content : (table_paragraph / table_wikitext / EOL)*
    table_cell_content      : table_inline? table_multiline_content                                 : liftValue
    table_cell              : table_parameter table_cell_content
    table_other_cell        : (PIPE{2} table_cell)*                                                 : liftValue liftNode
    table_line_cells        : PIPE table_cell table_other_cell                                      : render_table_normal_cell
    table_line_header       : BANG table_cell table_other_cell                                      : render_table_header_cell
    table_empty_cell        : PIPE EOL &(PIPE/BANG/TABLE_END)                                       : keep
    table_line_break        : TABLE_NEWLINE table_parameters* EOL                                   : keep liftValue render_table_line_break
    table_title             : TABLE_TITLE table_parameter inline EOL                                : liftValue render_table_caption
    table_special_line      : table_title / table_line_break
    table_normal_line       : table_empty_cell / table_line_cells / table_line_header
    table_line              : !TABLE_END (table_special_line / table_normal_line)                   : liftNode
    table_content           : (table_line / EOL)*                                                   : liftNode
    table_begin             : TABLE_BEGIN table_parameters*                                         : liftValue
    table_structure         : table_begin SPACETABEOL* table_content TABLE_END                      : @ liftValue render_table 
    table                   : table_structure EOL                                                   : liftValue

# Top pattern

    valid_syntax            : list/horizontal_rule/preformatted_group/title/table/EOL/paragraphs
    wikitext                : optional_comment (valid_syntax/invalid_line)+                         : liftValue render_wikitext
    body                    : wikitext{1}                                                           : liftValue render_body

"""

from pijnu.library import *


def make_parser(actions=None):
    """Return a parser.

    The parser's toolset functions are (optionally) augmented (or overridden)
    by a map of additional ones passed in.

    """
    if actions is None:
        actions = {}

    # Start off with the imported pijnu library functions:
    toolset = globals().copy()

    parser = Parser()
    state = parser.state

### title: wikitext ###
    
    
    def toolset_from_grammar():
        """Return a map of toolset functions hard-coded into the grammar."""
    ###   <toolset>
        def replace_by_space(node):
            node.value = ' '
        
        def replace_by_2_spaces(node):
            node.value = ' '
        
        def replace_by_8_spaces(node):
            node.value = ' '
        
    
        return locals().copy()
    
    toolset.update(toolset_from_grammar())
    toolset.update(actions)
    
    ###   <definition>
    # recursive pattern(s)
    table_structure = Recursive(name='table_structure')
    list_item = Recursive(name='list_item')
    sub_list = Recursive(name='sub_list')
    list_leaf = Recursive(name='list_leaf')
    semi_colon_sub_list = Recursive(name='semi_colon_sub_list')
    colon_sub_list = Recursive(name='colon_sub_list')
    number_sub_list = Recursive(name='number_sub_list')
    bullet_sub_list = Recursive(name='bullet_sub_list')
    inline = Recursive(name='inline')
    clean_inline = Recursive(name='clean_inline')
    # Codes
    
    LF = Char('\n', expression="'\n'", name='LF')
    CR = Char('\n', expression="'\n'", name='CR')
    EOL = Choice([LF, CR], expression='LF / CR', name='EOL')(toolset['drop'])
    L_BRACKET = Word('[', expression='"["', name='L_BRACKET')(toolset['drop'])
    R_BRACKET = Word(']', expression='"\\]"', name='R_BRACKET')(toolset['drop'])
    L_BRACE = Word('{', expression='"{"', name='L_BRACE')(toolset['drop'])
    R_BRACE = Word('}', expression='"}"', name='R_BRACE')(toolset['drop'])
    SPACE = Word(' ', expression='" "', name='SPACE')(toolset['drop'])
    TAB = Word('\t', expression='"\t"', name='TAB')(toolset['drop'])
    SPACETAB = Choice([SPACE, TAB], expression='SPACE / TAB', name='SPACETAB')(toolset['drop'])
    SPACETABEOL = Choice([SPACE, TAB, EOL], expression='SPACE / TAB / EOL', name='SPACETABEOL')(toolset['drop'])
    AMP = Word('&', expression='"&"', name='AMP')(toolset['drop'])
    PIPE = Word('|', expression='"|"', name='PIPE')(toolset['drop'])
    BANG = Word('!', expression='"!"', name='BANG')(toolset['drop'])
    EQUAL = Word('=', expression='"="', name='EQUAL')(toolset['drop'])
    BULLET = Word('*', expression='"*"', name='BULLET')(toolset['drop'])
    HASH = Word('#', expression='"#"', name='HASH')(toolset['drop'])
    COLON = Word(':', expression='":"', name='COLON')(toolset['drop'])
    LT = Word('<', expression='"<"', name='LT')(toolset['render_lt'])
    GT = Word('>', expression='">"', name='GT')(toolset['render_gt'])
    SLASH = Word('/', expression='"/"', name='SLASH')(toolset['drop'])
    SEMICOLON = Word(';', expression='";"', name='SEMICOLON')(toolset['drop'])
    DASH = Word('-', expression='"-"', name='DASH')(toolset['drop'])
    TABLE_BEGIN = Word('{|', expression='"{|"', name='TABLE_BEGIN')(toolset['drop'])
    TABLE_END = Word('|}', expression='"|}"', name='TABLE_END')(toolset['drop'])
    TABLE_NEWLINE = Word('|-', expression='"|-"', name='TABLE_NEWLINE')(toolset['drop'])
    TABLE_TITLE = Word('|+', expression='"|+"', name='TABLE_TITLE')(toolset['drop'])
    QUOTE = Word('"', expression='"\\""', name='QUOTE')(toolset['drop'])
    APOSTROPHE = Word("'", expression='"\\\'"', name='APOSTROPHE')(toolset['drop'])
    TITLE6_BEGIN = Repetition(EQUAL, numMin=6, numMax=6, expression='EQUAL{6}', name='TITLE6_BEGIN')(toolset['drop'])
    TITLE5_BEGIN = Repetition(EQUAL, numMin=5, numMax=5, expression='EQUAL{5}', name='TITLE5_BEGIN')(toolset['drop'])
    TITLE4_BEGIN = Repetition(EQUAL, numMin=4, numMax=4, expression='EQUAL{4}', name='TITLE4_BEGIN')(toolset['drop'])
    TITLE3_BEGIN = Repetition(EQUAL, numMin=3, numMax=3, expression='EQUAL{3}', name='TITLE3_BEGIN')(toolset['drop'])
    TITLE2_BEGIN = Repetition(EQUAL, numMin=2, numMax=2, expression='EQUAL{2}', name='TITLE2_BEGIN')(toolset['drop'])
    TITLE1_BEGIN = Repetition(EQUAL, numMin=1, numMax=1, expression='EQUAL{1}', name='TITLE1_BEGIN')(toolset['drop'])
    TITLE6_END = Sequence([Repetition(EQUAL, numMin=6, numMax=6, expression='EQUAL{6}'), Repetition(SPACETAB, numMin=False, numMax=False, expression='SPACETAB*'), EOL], expression='EQUAL{6} SPACETAB* EOL', name='TITLE6_END')(toolset['drop'])
    TITLE5_END = Sequence([Repetition(EQUAL, numMin=5, numMax=5, expression='EQUAL{5}'), Repetition(SPACETAB, numMin=False, numMax=False, expression='SPACETAB*'), EOL], expression='EQUAL{5} SPACETAB* EOL', name='TITLE5_END')(toolset['drop'])
    TITLE4_END = Sequence([Repetition(EQUAL, numMin=4, numMax=4, expression='EQUAL{4}'), Repetition(SPACETAB, numMin=False, numMax=False, expression='SPACETAB*'), EOL], expression='EQUAL{4} SPACETAB* EOL', name='TITLE4_END')(toolset['drop'])
    TITLE3_END = Sequence([Repetition(EQUAL, numMin=3, numMax=3, expression='EQUAL{3}'), Repetition(SPACETAB, numMin=False, numMax=False, expression='SPACETAB*'), EOL], expression='EQUAL{3} SPACETAB* EOL', name='TITLE3_END')(toolset['drop'])
    TITLE2_END = Sequence([Repetition(EQUAL, numMin=2, numMax=2, expression='EQUAL{2}'), Repetition(SPACETAB, numMin=False, numMax=False, expression='SPACETAB*'), EOL], expression='EQUAL{2} SPACETAB* EOL', name='TITLE2_END')(toolset['drop'])
    TITLE1_END = Sequence([Repetition(EQUAL, numMin=1, numMax=1, expression='EQUAL{1}'), Repetition(SPACETAB, numMin=False, numMax=False, expression='SPACETAB*'), EOL], expression='EQUAL{1} SPACETAB* EOL', name='TITLE1_END')(toolset['drop'])
    LINK_BEGIN = Repetition(L_BRACKET, numMin=2, numMax=2, expression='L_BRACKET{2}', name='LINK_BEGIN')(toolset['drop'])
    LINK_END = Repetition(R_BRACKET, numMin=2, numMax=2, expression='R_BRACKET{2}', name='LINK_END')(toolset['drop'])
    
    # Protocols
    
    HTTPS = Word('https://', expression='"https://"', name='HTTPS')(toolset['liftValue'])
    HTTP = Word('http://', expression='"http://"', name='HTTP')(toolset['liftValue'])
    FTP = Word('ftp://', expression='"ftp://"', name='FTP')(toolset['liftValue'])
    protocol = Choice([HTTPS, HTTP, FTP], expression='HTTPS / HTTP / FTP', name='protocol')(toolset['liftValue'])
    
    # Predefined tags
    
    NOWIKI_BEGIN = Word('<nowiki>', expression='"<nowiki>"', name='NOWIKI_BEGIN')(toolset['drop'])
    NOWIKI_END = Word('</nowiki>', expression='"</nowiki>"', name='NOWIKI_END')(toolset['drop'])
    PRE_BEGIN = Word('<pre>', expression='"<pre>"', name='PRE_BEGIN')(toolset['drop'])
    PRE_END = Word('</pre>', expression='"</pre>"', name='PRE_END')(toolset['drop'])
    SPECIAL_TAG = Choice([NOWIKI_BEGIN, NOWIKI_END, PRE_BEGIN, PRE_END], expression='NOWIKI_BEGIN/NOWIKI_END/PRE_BEGIN/PRE_END', name='SPECIAL_TAG')
    
    # Characters
    
    ESC_CHAR = Choice([L_BRACKET, R_BRACKET, protocol, PIPE, L_BRACE, R_BRACE, LT, GT, SLASH, AMP, SEMICOLON, TAB], expression='L_BRACKET/R_BRACKET/protocol/PIPE/L_BRACE/R_BRACE/LT/GT/SLASH/AMP/SEMICOLON/TAB', name='ESC_CHAR')
    TITLE_END = Choice([TITLE6_END, TITLE5_END, TITLE4_END, TITLE3_END, TITLE2_END, TITLE1_END], expression='TITLE6_END/TITLE5_END/TITLE4_END/TITLE3_END/TITLE2_END/TITLE1_END', name='TITLE_END')
    ESC_SEQ = Choice([SPECIAL_TAG, ESC_CHAR, TITLE_END], expression='SPECIAL_TAG / ESC_CHAR / TITLE_END', name='ESC_SEQ')
    tab_to_space = Repetition(TAB, numMin=1, numMax=False, expression='TAB+', name='tab_to_space')(toolset['replace_by_space'])
    raw_char = Sequence([NextNot(ESC_SEQ, expression='!ESC_SEQ'), Klass(u' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff', expression='[\\x20..\\xff]')], expression='!ESC_SEQ [\\x20..\\xff]', name='raw_char')
    raw_text = Repetition(raw_char, numMin=1, numMax=False, expression='raw_char+', name='raw_text')(toolset['join'], toolset['render_raw_text'])
    alpha_num = Klass(u'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', expression='[a..zA..Z0..9]', name='alpha_num')
    alpha_num_text = Repetition(alpha_num, numMin=1, numMax=False, expression='alpha_num+', name='alpha_num_text')(toolset['join'])
    any_char = Choice([Klass(u' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff', expression='[\\x20..\\xff]'), tab_to_space], expression='[\\x20..\\xff] / tab_to_space', name='any_char')
    any_text = Repetition(any_char, numMin=1, numMax=False, expression='any_char+', name='any_text')(toolset['join'])
    
    # HTML tags
    
    value_quote = Sequence([QUOTE, Repetition(Choice([Sequence([NextNot(Choice([GT, QUOTE], expression='GT/QUOTE'), expression='!(GT/QUOTE)'), any_char], expression='!(GT/QUOTE) any_char'), TAB], expression='(!(GT/QUOTE) any_char) / TAB'), numMin=1, numMax=False, expression='((!(GT/QUOTE) any_char) / TAB)+'), QUOTE], expression='QUOTE ((!(GT/QUOTE) any_char) / TAB)+ QUOTE', name='value_quote')(toolset['join'])
    value_apostrophe = Sequence([APOSTROPHE, Repetition(Choice([Sequence([NextNot(Choice([GT, APOSTROPHE], expression='GT/APOSTROPHE'), expression='!(GT/APOSTROPHE)'), any_char], expression='!(GT/APOSTROPHE) any_char'), TAB], expression='(!(GT/APOSTROPHE) any_char) / TAB'), numMin=1, numMax=False, expression='((!(GT/APOSTROPHE) any_char) / TAB)+'), APOSTROPHE], expression='APOSTROPHE ((!(GT/APOSTROPHE) any_char) / TAB)+ APOSTROPHE', name='value_apostrophe')(toolset['join'])
    value_noquote = Repetition(Sequence([NextNot(Choice([GT, SPACETAB, SLASH], expression='GT/SPACETAB/SLASH'), expression='!(GT/SPACETAB/SLASH)'), raw_char], expression='!(GT/SPACETAB/SLASH) raw_char'), numMin=1, numMax=False, expression='(!(GT/SPACETAB/SLASH) raw_char)+', name='value_noquote')(toolset['join'])
    attribute_value = Sequence([EQUAL, Choice([value_quote, value_apostrophe, value_noquote], expression='value_quote / value_apostrophe / value_noquote')], expression='EQUAL (value_quote / value_apostrophe / value_noquote)', name='attribute_value')(toolset['liftNode'])
    attribute_name = Repetition(Sequence([NextNot(Choice([EQUAL, SLASH, SPACETAB], expression='EQUAL/SLASH/SPACETAB'), expression='!(EQUAL/SLASH/SPACETAB)'), raw_char], expression='!(EQUAL/SLASH/SPACETAB) raw_char'), numMin=1, numMax=False, expression='(!(EQUAL/SLASH/SPACETAB) raw_char)+', name='attribute_name')(toolset['join'])
    tag_name = Repetition(Sequence([NextNot(Choice([SPACE, SLASH], expression='SPACE/SLASH'), expression='!(SPACE/SLASH)'), alpha_num], expression='!(SPACE/SLASH) alpha_num'), numMin=1, numMax=False, expression='(!(SPACE/SLASH) alpha_num)+', name='tag_name')(toolset['join'])
    optional_attribute = Sequence([Repetition(SPACETABEOL, numMin=1, numMax=False, expression='SPACETABEOL+'), attribute_name, Option(attribute_value, expression='attribute_value?')], expression='SPACETABEOL+ attribute_name attribute_value?', name='optional_attribute')
    optional_attributes = Repetition(optional_attribute, numMin=False, numMax=False, expression='optional_attribute*', name='optional_attributes')
    tag_lt = Clone(LT, expression='LT', name='tag_lt')(toolset['drop'])
    tag_gt = Clone(GT, expression='GT', name='tag_gt')(toolset['drop'])
    tag_open = Sequence([tag_lt, tag_name, optional_attributes, Repetition(SPACETABEOL, numMin=False, numMax=False, expression='SPACETABEOL*'), tag_gt], expression='tag_lt tag_name optional_attributes SPACETABEOL* tag_gt', name='tag_open')(toolset['render_tag_open'])
    tag_close = Sequence([tag_lt, SLASH, tag_name, tag_gt], expression='tag_lt SLASH tag_name tag_gt', name='tag_close')(toolset['render_tag_close'])
    tag_autoclose = Sequence([tag_lt, tag_name, optional_attributes, Repetition(SPACETABEOL, numMin=False, numMax=False, expression='SPACETABEOL*'), SLASH, tag_gt], expression='tag_lt tag_name optional_attributes SPACETABEOL* SLASH tag_gt', name='tag_autoclose')(toolset['render_tag_autoclose'])
    tag = Choice([tag_autoclose, tag_open, tag_close], expression='tag_autoclose / tag_open / tag_close', name='tag')
    
    # HTML entities
    
    entity = Sequence([AMP, alpha_num_text, SEMICOLON], expression='AMP alpha_num_text SEMICOLON', name='entity')(toolset['render_entity'])
    
    # HTML comments
    
        # HTML comments are totally ignored and do not appear in the final text
    comment_content = Repetition(Choice([Repetition(Sequence([NextNot(Sequence([Repetition(DASH, numMin=2, numMax=2, expression='DASH{2}'), GT], expression='DASH{2} GT'), expression='!(DASH{2} GT)'), Klass(u' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff', expression='[\\x20..\\xff]')], expression='!(DASH{2} GT) [\\x20..\\xff]'), numMin=1, numMax=False, expression='(!(DASH{2} GT) [\\x20..\\xff])+'), SPACETABEOL], expression='(!(DASH{2} GT) [\\x20..\\xff])+ / SPACETABEOL'), numMin=False, numMax=False, expression='((!(DASH{2} GT) [\\x20..\\xff])+ / SPACETABEOL)*', name='comment_content')
    html_comment = Sequence([tag_lt, BANG, Repetition(DASH, numMin=2, numMax=2, expression='DASH{2}'), comment_content, Repetition(DASH, numMin=2, numMax=2, expression='DASH{2}'), tag_gt], expression='tag_lt BANG DASH{2} comment_content DASH{2} tag_gt', name='html_comment')(toolset['drop'])
    optional_comment = Repetition(html_comment, numMin=False, numMax=False, expression='html_comment*', name='optional_comment')
    
    # Text
    
    page_name = Repetition(Choice([raw_char, Char('/', expression="'/'")], expression="raw_char / '/'"), numMin=1, numMax=False, expression="(raw_char / '/')+", name='page_name')(toolset['join'])
    # TODO: allow IPv6 addresses (http://[::1]/etc)
    address = Repetition(Sequence([NextNot(Choice([QUOTE, R_BRACKET], expression='QUOTE/R_BRACKET'), expression='!(QUOTE/R_BRACKET)'), Klass(u'!"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff', expression='[\\x21..\\xff]')], expression='!(QUOTE/R_BRACKET) [\\x21..\\xff]'), numMin=1, numMax=False, expression='(!(QUOTE/R_BRACKET) [\\x21..\\xff])+', name='address')(toolset['liftValue'])
    url = Sequence([protocol, address], expression='protocol address', name='url')(toolset['join'])
    inline_url = Repetition(url, numMin=1, numMax=1, expression='url{1}', name='inline_url')(toolset['render_url'])
    
    # Links
    
    allowed_in_link = Repetition(Sequence([NextNot(Choice([R_BRACKET, PIPE], expression='R_BRACKET/PIPE'), expression='!(R_BRACKET/PIPE)'), ESC_CHAR], expression='!(R_BRACKET/PIPE) ESC_CHAR'), numMin=1, numMax=False, expression='(!(R_BRACKET/PIPE) ESC_CHAR)+', name='allowed_in_link')(toolset['restore'], toolset['join'])
    link_text = Repetition(Choice([clean_inline, allowed_in_link], expression='clean_inline / allowed_in_link'), numMin=False, numMax=False, expression='(clean_inline / allowed_in_link)*', name='link_text')(toolset['liftValue'])
    link_argument = Sequence([PIPE, link_text], expression='PIPE link_text', name='link_argument')(toolset['liftValue'])
    link_arguments = Repetition(link_argument, numMin=False, numMax=False, expression='link_argument*', name='link_arguments')
    internal_link = Sequence([LINK_BEGIN, page_name, link_arguments, LINK_END], expression='LINK_BEGIN page_name link_arguments LINK_END', name='internal_link')(toolset['render_internal_link'])
    optional_link_text = Sequence([Repetition(SPACETAB, numMin=1, numMax=False, expression='SPACETAB+'), link_text], expression='SPACETAB+ link_text', name='optional_link_text')(toolset['liftValue'])
    external_link = Sequence([L_BRACKET, url, Option(optional_link_text, expression='optional_link_text?'), R_BRACKET], expression='L_BRACKET url optional_link_text? R_BRACKET', name='external_link')(toolset['render_external_link'])
    link = Choice([internal_link, external_link], expression='internal_link / external_link', name='link')
    
    # Pre and nowiki tags
    
        # Preformatted acts like nowiki (disables wikitext parsing)
    tab_to_2_spaces = Clone(TAB, expression='TAB', name='tab_to_2_spaces')(toolset['replace_by_2_spaces'])
    pre_text = Repetition(Choice([tab_to_2_spaces, Sequence([NextNot(PRE_END, expression='!PRE_END'), any_char], expression='!PRE_END any_char')], expression='tab_to_2_spaces / (!PRE_END any_char)'), numMin=False, numMax=False, expression='(tab_to_2_spaces / (!PRE_END any_char))*', name='pre_text')(toolset['join'])
    preformatted = Sequence([PRE_BEGIN, pre_text, PRE_END], expression='PRE_BEGIN pre_text PRE_END', name='preformatted')(toolset['liftValue'])
        # We allow any char without parsing them as long as the tag is not closed
    eol_to_space = Repetition(EOL, numMin=False, numMax=False, expression='EOL*', name='eol_to_space')(toolset['replace_by_space'])
    nowiki_text = Repetition(Sequence([NextNot(NOWIKI_END, expression='!NOWIKI_END'), Choice([any_char, eol_to_space], expression='any_char/eol_to_space')], expression='!NOWIKI_END (any_char/eol_to_space)'), numMin=False, numMax=False, expression='(!NOWIKI_END (any_char/eol_to_space))*', name='nowiki_text')(toolset['join'])
    nowiki = Sequence([NOWIKI_BEGIN, nowiki_text, NOWIKI_END], expression='NOWIKI_BEGIN nowiki_text NOWIKI_END', name='nowiki')(toolset['liftValue'])
    
    # Text types
    
    styled_text = Choice([link, inline_url, html_comment, tag, entity], expression='link / inline_url / html_comment / tag / entity', name='styled_text')
    not_styled_text = Choice([preformatted, nowiki], expression='preformatted / nowiki', name='not_styled_text')
    allowed_char = Repetition(ESC_CHAR, numMin=1, numMax=1, expression='ESC_CHAR{1}', name='allowed_char')(toolset['restore'], toolset['liftValue'])
    allowed_text = Choice([raw_text, LT, GT, tab_to_space, allowed_char], expression='raw_text / LT / GT / tab_to_space / allowed_char', name='allowed_text')
    clean_inline **= Repetition(Choice([not_styled_text, styled_text, raw_text], expression='not_styled_text / styled_text / raw_text'), numMin=1, numMax=False, expression='(not_styled_text / styled_text / raw_text)+', name='clean_inline')
    inline **= Repetition(Choice([not_styled_text, styled_text, allowed_text], expression='not_styled_text / styled_text / allowed_text'), numMin=1, numMax=False, expression='(not_styled_text / styled_text / allowed_text)+', name='inline')
    
    # Paragraphs
    
    special_line_begin = Choice([SPACE, EQUAL, BULLET, HASH, COLON, Repetition(DASH, numMin=4, numMax=4, expression='DASH{4}'), TABLE_BEGIN, SEMICOLON], expression='SPACE/EQUAL/BULLET/HASH/COLON/DASH{4}/TABLE_BEGIN/SEMICOLON', name='special_line_begin')
    paragraph_line = Sequence([NextNot(special_line_begin, expression='!special_line_begin'), inline, EOL], expression='!special_line_begin inline EOL', name='paragraph_line')(toolset['liftValue'])
    blank_paragraph = Repetition(EOL, numMin=2, numMax=2, expression='EOL{2}', name='blank_paragraph')(toolset['drop'], toolset['keep'])
    paragraph = Repetition(paragraph_line, numMin=1, numMax=False, expression='paragraph_line+', name='paragraph')(toolset['liftValue'], toolset['render_paragraph'])
    paragraphs = Repetition(Choice([blank_paragraph, EOL, paragraph], expression='blank_paragraph/EOL/paragraph'), numMin=1, numMax=False, expression='(blank_paragraph/EOL/paragraph)+', name='paragraphs')
    
    # Titles
    
    title6 = Sequence([TITLE6_BEGIN, inline, TITLE6_END], expression='TITLE6_BEGIN inline TITLE6_END', name='title6')(toolset['liftValue'], toolset['render_title6'])
    title5 = Sequence([TITLE5_BEGIN, inline, TITLE5_END], expression='TITLE5_BEGIN inline TITLE5_END', name='title5')(toolset['liftValue'], toolset['render_title5'])
    title4 = Sequence([TITLE4_BEGIN, inline, TITLE4_END], expression='TITLE4_BEGIN inline TITLE4_END', name='title4')(toolset['liftValue'], toolset['render_title4'])
    title3 = Sequence([TITLE3_BEGIN, inline, TITLE3_END], expression='TITLE3_BEGIN inline TITLE3_END', name='title3')(toolset['liftValue'], toolset['render_title3'])
    title2 = Sequence([TITLE2_BEGIN, inline, TITLE2_END], expression='TITLE2_BEGIN inline TITLE2_END', name='title2')(toolset['liftValue'], toolset['render_title2'])
    title1 = Sequence([TITLE1_BEGIN, inline, TITLE1_END], expression='TITLE1_BEGIN inline TITLE1_END', name='title1')(toolset['liftValue'], toolset['render_title1'])
    title = Choice([title6, title5, title4, title3, title2, title1], expression='title6 / title5 / title4 / title3 / title2 / title1', name='title')
    
    # Lists
    
    LIST_CHAR = Choice([BULLET, HASH, COLON, SEMICOLON], expression='BULLET / HASH / COLON / SEMICOLON', name='LIST_CHAR')
    list_leaf_content = Sequence([NextNot(LIST_CHAR, expression='!LIST_CHAR'), inline, EOL], expression='!LIST_CHAR inline EOL', name='list_leaf_content')(toolset['liftValue'])
    
    bullet_list_leaf = Sequence([BULLET, optional_comment, list_leaf_content], expression='BULLET optional_comment list_leaf_content', name='bullet_list_leaf')(toolset['liftValue'])
    bullet_sub_list **= Sequence([BULLET, optional_comment, list_item], expression='BULLET optional_comment list_item', name='bullet_sub_list')
    
    number_list_leaf = Sequence([HASH, optional_comment, list_leaf_content], expression='HASH optional_comment list_leaf_content', name='number_list_leaf')(toolset['liftValue'])
    number_sub_list **= Sequence([HASH, optional_comment, list_item], expression='HASH optional_comment list_item', name='number_sub_list')
    
    colon_list_leaf = Sequence([COLON, optional_comment, list_leaf_content], expression='COLON optional_comment list_leaf_content', name='colon_list_leaf')(toolset['liftValue'])
    colon_sub_list **= Sequence([COLON, optional_comment, list_item], expression='COLON optional_comment list_item', name='colon_sub_list')
    
    semi_colon_list_leaf = Sequence([SEMICOLON, optional_comment, list_leaf_content], expression='SEMICOLON optional_comment list_leaf_content', name='semi_colon_list_leaf')(toolset['liftValue'])
    semi_colon_sub_list **= Sequence([SEMICOLON, optional_comment, list_item], expression='SEMICOLON optional_comment list_item', name='semi_colon_sub_list')
    
    list_leaf **= Choice([semi_colon_list_leaf, colon_list_leaf, number_list_leaf, bullet_list_leaf], expression='semi_colon_list_leaf/colon_list_leaf/number_list_leaf/bullet_list_leaf', name='list_leaf')
    sub_list **= Choice([semi_colon_sub_list, colon_sub_list, number_sub_list, bullet_sub_list], expression='semi_colon_sub_list/colon_sub_list/number_sub_list/bullet_sub_list', name='sub_list')
    list_item **= Choice([sub_list, list_leaf], expression='sub_list / list_leaf', name='list_item')
    list = Repetition(list_item, numMin=1, numMax=False, expression='list_item+', name='list')(toolset['render_list'])
    
    # Preformatted
    
    EOL_KEEP = Clone(EOL, expression='EOL', name='EOL_KEEP')(toolset['restore'])
    tab_to_8_spaces = Clone(TAB, expression='TAB', name='tab_to_8_spaces')(toolset['replace_by_8_spaces'])
    any_char_but_tab = Choice([raw_text, LT, GT, Sequence([NextNot(TAB, expression='!TAB'), ESC_CHAR], expression='!TAB ESC_CHAR')], expression='raw_text / LT / GT / (!TAB ESC_CHAR)', name='any_char_but_tab')(toolset['join'])
    preformatted_inline = Repetition(Choice([tab_to_8_spaces, not_styled_text, styled_text, any_char_but_tab], expression='tab_to_8_spaces / not_styled_text / styled_text / any_char_but_tab'), numMin=1, numMax=False, expression='(tab_to_8_spaces / not_styled_text / styled_text / any_char_but_tab)+', name='preformatted_inline')
    preformatted_line = Sequence([SPACE, preformatted_inline, EOL_KEEP], expression='SPACE preformatted_inline EOL_KEEP', name='preformatted_line')(toolset['liftValue'])
    preformatted_lines = Repetition(preformatted_line, numMin=1, numMax=False, expression='preformatted_line+', name='preformatted_lines')
    preformatted_text = Sequence([preformatted_inline, Option(EOL, expression='EOL?')], expression='preformatted_inline EOL?', name='preformatted_text')(toolset['liftValue'])
    preformatted_paragraph = Sequence([PRE_BEGIN, EOL, preformatted_text, PRE_END, EOL], expression='PRE_BEGIN EOL preformatted_text PRE_END EOL', name='preformatted_paragraph')
    preformatted_group = Choice([preformatted_paragraph, preformatted_lines], expression='preformatted_paragraph / preformatted_lines', name='preformatted_group')(toolset['render_preformatted'])
    
    # Special lines
    
    horizontal_rule = Sequence([Repetition(DASH, numMin=4, numMax=4, expression='DASH{4}'), Repetition(DASH, numMin=False, numMax=False, expression='DASH*'), Repetition(inline, numMin=False, numMax=False, expression='inline*'), EOL], expression='DASH{4} DASH* inline* EOL', name='horizontal_rule')(toolset['liftValue'], toolset['keep'], toolset['render_hr'])
    
        # This should never happen
    invalid_line = Sequence([any_text, EOL], expression='any_text EOL', name='invalid_line')(toolset['liftValue'])
    
    # Tables
    
    HTML_attribute = Sequence([Repetition(SPACETAB, numMin=False, numMax=False, expression='SPACETAB*'), attribute_name, attribute_value, Repetition(SPACETAB, numMin=False, numMax=False, expression='SPACETAB*')], expression='SPACETAB* attribute_name attribute_value SPACETAB*', name='HTML_attribute')(toolset['render_attribute'])
    table_parameters_pipe = Option(Sequence([Repetition(SPACETAB, numMin=False, numMax=False, expression='SPACETAB*'), Repetition(HTML_attribute, numMin=1, numMax=False, expression='HTML_attribute+'), Repetition(SPACETAB, numMin=False, numMax=False, expression='SPACETAB*'), PIPE, NextNot(PIPE, expression='!PIPE')], expression='SPACETAB* HTML_attribute+ SPACETAB* PIPE !PIPE'), expression='(SPACETAB* HTML_attribute+ SPACETAB* PIPE !PIPE)?', name='table_parameters_pipe')(toolset['liftNode'])
    table_parameters = Repetition(Choice([HTML_attribute, clean_inline], expression='HTML_attribute / clean_inline'), numMin=1, numMax=False, expression='(HTML_attribute / clean_inline)+', name='table_parameters')
    table_parameter = Repetition(table_parameters_pipe, numMin=0, numMax=1, expression='table_parameters_pipe{0..1}', name='table_parameter')(toolset['liftValue'])
    table_wikitext = Choice([list, horizontal_rule, preformatted_group, title, table_structure], expression='list/horizontal_rule/preformatted_group/title/table_structure', name='table_wikitext')
    table_inline = Sequence([NextNot(Choice([PIPE, BANG], expression='PIPE/BANG'), expression='!(PIPE/BANG)'), clean_inline, Option(EOL, expression='EOL?')], expression='!(PIPE/BANG) clean_inline EOL?', name='table_inline')(toolset['liftNode'])
    table_paragraph = Sequence([NextNot(Choice([PIPE, BANG, TABLE_NEWLINE, TABLE_TITLE, TABLE_END], expression='PIPE/BANG/TABLE_NEWLINE/TABLE_TITLE/TABLE_END'), expression='!(PIPE/BANG/TABLE_NEWLINE/TABLE_TITLE/TABLE_END)'), paragraph_line], expression='!(PIPE/BANG/TABLE_NEWLINE/TABLE_TITLE/TABLE_END) paragraph_line', name='table_paragraph')(toolset['render_paragraph'])
    table_multiline_content = Repetition(Choice([table_paragraph, table_wikitext, EOL], expression='table_paragraph / table_wikitext / EOL'), numMin=False, numMax=False, expression='(table_paragraph / table_wikitext / EOL)*', name='table_multiline_content')
    table_cell_content = Sequence([Option(table_inline, expression='table_inline?'), table_multiline_content], expression='table_inline? table_multiline_content', name='table_cell_content')(toolset['liftValue'])
    table_cell = Sequence([table_parameter, table_cell_content], expression='table_parameter table_cell_content', name='table_cell')
    table_other_cell = Repetition(Sequence([Repetition(PIPE, numMin=2, numMax=2, expression='PIPE{2}'), table_cell], expression='PIPE{2} table_cell'), numMin=False, numMax=False, expression='(PIPE{2} table_cell)*', name='table_other_cell')(toolset['liftValue'], toolset['liftNode'])
    table_line_cells = Sequence([PIPE, table_cell, table_other_cell], expression='PIPE table_cell table_other_cell', name='table_line_cells')(toolset['render_table_normal_cell'])
    table_line_header = Sequence([BANG, table_cell, table_other_cell], expression='BANG table_cell table_other_cell', name='table_line_header')(toolset['render_table_header_cell'])
    table_empty_cell = Sequence([PIPE, EOL, Next(Choice([PIPE, BANG, TABLE_END], expression='PIPE/BANG/TABLE_END'), expression='&(PIPE/BANG/TABLE_END)')], expression='PIPE EOL &(PIPE/BANG/TABLE_END)', name='table_empty_cell')(toolset['keep'])
    table_line_break = Sequence([TABLE_NEWLINE, Repetition(table_parameters, numMin=False, numMax=False, expression='table_parameters*'), EOL], expression='TABLE_NEWLINE table_parameters* EOL', name='table_line_break')(toolset['keep'], toolset['liftValue'], toolset['render_table_line_break'])
    table_title = Sequence([TABLE_TITLE, table_parameter, inline, EOL], expression='TABLE_TITLE table_parameter inline EOL', name='table_title')(toolset['liftValue'], toolset['render_table_caption'])
    table_special_line = Choice([table_title, table_line_break], expression='table_title / table_line_break', name='table_special_line')
    table_normal_line = Choice([table_empty_cell, table_line_cells, table_line_header], expression='table_empty_cell / table_line_cells / table_line_header', name='table_normal_line')
    table_line = Sequence([NextNot(TABLE_END, expression='!TABLE_END'), Choice([table_special_line, table_normal_line], expression='table_special_line / table_normal_line')], expression='!TABLE_END (table_special_line / table_normal_line)', name='table_line')(toolset['liftNode'])
    table_content = Repetition(Choice([table_line, EOL], expression='table_line / EOL'), numMin=False, numMax=False, expression='(table_line / EOL)*', name='table_content')(toolset['liftNode'])
    table_begin = Sequence([TABLE_BEGIN, Repetition(table_parameters, numMin=False, numMax=False, expression='table_parameters*')], expression='TABLE_BEGIN table_parameters*', name='table_begin')(toolset['liftValue'])
    table_structure **= Sequence([table_begin, Repetition(SPACETABEOL, numMin=False, numMax=False, expression='SPACETABEOL*'), table_content, TABLE_END], expression='table_begin SPACETABEOL* table_content TABLE_END', name='table_structure')(toolset['liftValue'], toolset['render_table'])
    table = Sequence([table_structure, EOL], expression='table_structure EOL', name='table')(toolset['liftValue'])
    
    # Top pattern
    
    valid_syntax = Choice([list, horizontal_rule, preformatted_group, title, table, EOL, paragraphs], expression='list/horizontal_rule/preformatted_group/title/table/EOL/paragraphs', name='valid_syntax')
    wikitext = Sequence([optional_comment, Repetition(Choice([valid_syntax, invalid_line], expression='valid_syntax/invalid_line'), numMin=1, numMax=False, expression='(valid_syntax/invalid_line)+')], expression='optional_comment (valid_syntax/invalid_line)+', name='wikitext')(toolset['liftValue'], toolset['render_wikitext'])
    body = Repetition(wikitext, numMin=1, numMax=1, expression='wikitext{1}', name='body')(toolset['liftValue'], toolset['render_body'])

    symbols = locals().copy()
    symbols.update(actions)
    parser._recordPatterns(symbols)
    parser._setTopPattern("body")
    parser.grammarTitle = "wikitext"
    parser.filename = "wikitextParser.py"

    return parser

########NEW FILE########
