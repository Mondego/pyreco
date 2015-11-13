__FILENAME__ = directives
# -*- coding: utf-8 -*-
"""
    sphinx.domains.http
    ~~~~~~~~~~~~~~~~~~~

    Directives for the HTTP domain.
"""

import re
from urlparse import urlsplit

from docutils.nodes import literal, strong, Text
from docutils.parsers.rst import directives

from sphinx.locale import l_, _
from sphinx.directives import ObjectDescription
from sphinx.util.docfields import TypedField

from sphinx_http_domain.docfields import NoArgGroupedField, ResponseField
from sphinx_http_domain.nodes import (desc_http_method, desc_http_url,
                                      desc_http_path, desc_http_patharg,
                                      desc_http_query, desc_http_queryparam,
                                      desc_http_fragment, desc_http_response)
from sphinx_http_domain.utils import slugify, slugify_url

try:
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl

class HTTPDescription(ObjectDescription):
    def get_anchor(self, name, sig):
        """
        Returns anchor for cross-reference IDs.

        *name* is whatever :meth:`handle_signature()` returned.
        """
        return self.typ + '-' + self.get_id(name, sig)

    def get_entry(self, name, sig):
        """
        Returns entry to add for cross-reference IDs.

        *name* is whatever :meth:`handle_signature()` returned.
        """
        return name

    def get_id(self, name, sig):
        """
        Returns cross-reference ID.

        *name* is whatever :meth:`handle_signature()` returned.
        """
        return name

    def add_target_and_index(self, name, sig, signode):
        """
        Add cross-reference IDs and entries to self.indexnode, if applicable.

        *name* is whatever :meth:`handle_signature()` returned.
        """
        anchor = self.get_anchor(name, sig)
        id = self.get_id(name, sig)
        self.add_target(anchor=anchor, entry=self.get_entry(name, sig),
                        id=id, sig=sig, signode=signode)
        self.add_index(anchor=anchor, name=name, sig=sig)

    def add_target(self, anchor, id, entry, sig, signode):
        """Add cross-references to self.env.domaindata, if applicable."""
        if anchor not in self.state.document.ids:
            signode['names'].append(anchor)
            signode['ids'].append(anchor)
            signode['first'] = (not self.names)
            self.state.document.note_explicit_target(signode)
            data = self.env.domaindata['http'][self.typ]
            if id in data:
                otherdocname = data[id][0]
                self.env.warn(
                    self.env.docname,
                    'duplicate method description of %s, ' % sig +
                    'other instance in ' +
                    self.env.doc2path(otherdocname) +
                    ', use :noindex: for one of them',
                    self.lineno
                )
            data[id] = entry

    def add_index(self, anchor, name, sig):
        """
        Add index entries to self.indexnode, if applicable.

        *name* is whatever :meth:`handle_signature()` returned.
        """
        raise NotImplemented


class HTTPMethod(HTTPDescription):
    """
    Description of a general HTTP method.
    """
    typ = 'method'
    nodetype = literal

    option_spec = {
        'noindex': directives.flag,
        'title': directives.unchanged,
        'label-name': directives.unchanged,
    }
    doc_field_types = [
        TypedField('argument', label=l_('Path arguments'),
                   names=('arg', 'argument', 'patharg'),
                   typenames=('argtype', 'pathargtype'),
                   can_collapse=True),
        TypedField('parameter', label=l_('Query params'),
                   names=('param', 'parameter', 'queryparam'),
                   typenames=('paramtype', 'queryparamtype'),
                   typerolename='response',
                   can_collapse=True),
        TypedField('optional_parameter', label=l_('Opt. params'),
                   names=('optparam', 'optional', 'optionalparameter'),
                   typenames=('optparamtype',),
                   can_collapse=True),
        TypedField('fragment', label=l_('Fragments'),
                   names=('frag', 'fragment'),
                   typenames=('fragtype',),
                   can_collapse=True),
        ResponseField('response', label=l_('Responses'),
                      names=('resp', 'responds', 'response'),
                      typerolename='response',
                      can_collapse=True)
    ]

    # RE for HTTP method signatures
    sig_re = re.compile(
        (
            r'^'
            r'(?:(GET|POST|PUT|DELETE)\s+)?'  # HTTP method
            r'(.+)'                           # URL
            r'\s*$'
        ),
        re.IGNORECASE
    )

    # Note, path_re.findall() will produce an extra ('', '') tuple
    # at the end of its matches. You should strip it off, or you will
    path_re = re.compile(
        (
            r'([^{]*)'                  # Plain text
            r'(\{[^}]*\})?'             # {arg} in matched braces
        ),
        re.VERBOSE
    )

    def node_from_method(self, method):
        """Returns a ``desc_http_method`` Node from a ``method`` string."""
        if method is None:
            method = 'GET'
        return desc_http_method(method, method.upper())

    def node_from_url(self, url):
        """Returns a ``desc_http_url`` Node from a ``url`` string."""
        if url is None:
            raise ValueError
        # Split URL into path, query, and fragment
        path, query, fragment = self.split_url(url)
        urlnode = desc_http_url()
        urlnode += self.node_from_path(path)
        node = self.node_from_query(query)
        if node:
            urlnode += node
        node = self.node_from_fragment(fragment)
        if node:
            urlnode += node
        return urlnode

    def node_from_path(self, path):
        """Returns a ``desc_http_path`` Node from a ``path`` string."""
        if path:
            pathnode = desc_http_path(path)
            path_segments = self.path_re.findall(path)[:-1]
            for text, arg in path_segments:
                pathnode += Text(text)
                if arg:
                    arg = arg[1:-1]     # Strip off { and }
                    pathnode += desc_http_patharg(arg, arg)
            return pathnode
        else:
            raise ValueError

    def node_from_query(self, query):
        """Returns a ``desc_http_query`` Node from a ``query`` string."""
        if query:
            querynode = desc_http_query(query)
            query_params = query.split('&')
            for p in query_params:
                querynode += desc_http_queryparam(p, p)
            return querynode

    def node_from_fragment(self, fragment):
        """Returns a ``desc_http_fragment`` Node from a ``fragment`` string."""
        if fragment:
            return desc_http_fragment(fragment, fragment)

    def split_url(self, url):
        """
        Splits a ``url`` string into its components.
        Returns (path, query string, fragment).
        """
        _, _, path, query, fragment = urlsplit(url)
        return (path, query, fragment)

    def handle_signature(self, sig, signode):
        """
        Transform an HTTP method signature into RST nodes.
        Returns (method name, full URL).
        """
        # Match the signature to extract the method and URL
        m = self.sig_re.match(sig)
        if m is None:
            raise ValueError
        method, url = m.groups()
        # Append nodes to signode for method and url
        signode += self.node_from_method(method)
        signode += self.node_from_url(url)
        # Name and title
        name = self.options.get('label-name',
                                slugify_url(method.lower() + '-' + url))
        title = self.options.get('title', sig)
        return (method.upper(), url, name, title)

    def get_entry(self, name, sig):
        """
        Returns entry to add for cross-reference IDs.

        *name* is whatever :meth:`handle_signature()` returned.
        """
        method, _, _, title = name
        return (self.env.docname, sig, title, method)

    def get_id(self, name, sig):
        """
        Returns cross-reference ID.

        *name* is whatever :meth:`handle_signature()` returned.
        """
        return name[2]

    def add_index(self, anchor, name, sig):
        """
        Add index entries to self.indexnode, if applicable.

        *name* is whatever :meth:`handle_signature()` returned.
        """
        method, url, id, title = name
        if title != sig:
            self.indexnode['entries'].append(('single',
                                              _("%s (HTTP method)") % title,
                                              anchor, anchor))
        self.indexnode['entries'].append(
            ('single',
             _("%(method)s (HTTP method); %(url)s") % {'method': method,
                                                       'url': url},
             anchor, anchor)
        )


class HTTPResponse(HTTPDescription):
    """
    Description of a general HTTP response.
    """
    typ = 'response'
    nodetype = strong

    option_spec = {
        'noindex': directives.flag,
    }
    doc_field_types = [
        TypedField('data', label=l_('Data'),
                   names=('data',),
                   typenames=('datatype', 'type'),
                   typerolename='response',
                   can_collapse=True),
        NoArgGroupedField('contenttype', label=l_('Content Types'),
                          names=('contenttype', 'mimetype', 'format'),
                          can_collapse=True),
    ]

    def handle_signature(self, sig, signode):
        """
        Transform an HTTP response into RST nodes.
        Returns the reference name.
        """
        name = slugify(sig)
        signode += desc_http_response(name, sig)
        return name

    def get_entry(self, name, sig):
        return (self.env.docname, sig, sig)

    def add_index(self, anchor, name, sig):
        """
        Add index entries to self.indexnode, if applicable.

        *name* is whatever :meth:`handle_signature()` returned.
        """
        self.indexnode['entries'].append(('single',
                                          _("%s (HTTP response)") % sig,
                                          anchor, anchor))
        self.indexnode['entries'].append(('single',
                                          _("HTTP response; %s") % sig,
                                          anchor, anchor))

########NEW FILE########
__FILENAME__ = docfields
# -*- coding: utf-8 -*-
"""
    Fields for the HTTP domain.
"""

from docutils import nodes

from sphinx.util.docfields import GroupedField, TypedField


class ResponseField(TypedField):
    """
    Like a TypedField, but with automatic descriptions.

    Just like a TypedField, you can use a ResponseField with or without
    a type::

        :param 200: description of response
        :type 200: SomeObject

        -- or --

        :param SomeObject 200: description of response

    In addition, ResponseField will provide a default description of
    the status code, if you provide none::

        :param 404:

        -- is equivalent to --

        :param 404: Not Found
    """
    # List of HTTP Status Codes, derived from:
    # http://en.wikipedia.org/wiki/List_of_HTTP_status_codes
    status_codes = {
        # 1xx Informational
        '100': 'Continue',
        '101': 'Switching Protocols',
        '102': 'Processing',
        '122': 'Request-URI too long',
        # 2xx Success
        '200': 'OK',
        '201': 'Created',
        '202': 'Accepted',
        '203': 'Non-Authoritative Information',
        '204': 'No Content',
        '205': 'Reset Content',
        '206': 'Partial Content',
        '207': 'Multi-Status',
        '226': 'IM Used',
        # 3xx Redirection
        '300': 'Multiple Choices',
        '301': 'Moved Permanently',
        '302': 'Found',
        '303': 'See Other',
        '304': 'Not Modified',
        '305': 'Use Proxy',
        '306': 'Switch Proxy',
        '307': 'Temporary Redirect',
        # 4xx Client Error
        '400': 'Bad Request',
        '401': 'Unauthorized',
        '402': 'Payment Requrired',
        '403': 'Forbidden',
        '404': 'Not Found',
        '405': 'Method Not Allowed',
        '406': 'Not Acceptable',
        '407': 'Proxy Authentication Requried',
        '408': 'Request Timeout',
        '409': 'Conflict',
        '410': 'Gone',
        '411': 'Length Required',
        '412': 'Precondition Failed',
        '413': 'Request Entity Too Large',
        '414': 'Request-URI Too Long',
        '415': 'Unsupported Media Type',
        '416': 'Requested Range Not Satisfiable',
        '417': 'Expectation Failed',
        '418': "I'm a teapot",
        '422': 'Unprocessable Entity',
        '423': 'Locked',
        '424': 'Failed Dependency',
        '425': 'Unordered Collection',
        '426': 'Upgrade Required',
        '444': 'No Response',
        '449': 'Retry With',
        '450': 'Block by Windows Parental Controls',
        '499': 'Client Closed Request',
        # 5xx Server Error
        '500': 'Interal Server Error',
        '501': 'Not Implemented',
        '502': 'Bad Gateway',
        '503': 'Service Unavailable',
        '504': 'Gateway Timeout',
        '505': 'HTTP Version Not Supported',
        '506': 'Variant Also Negotiates',
        '507': 'Insufficient Storage',
        '509': 'Bandwith Limit Exceeded',
        '510': 'Not Extended',
    }

    def default_content(self, fieldarg):
        """
        Given a fieldarg, returns the status code description in list form.

        The default status codes are provided in self.status_codes.
        """
        try:
            return [nodes.Text(self.status_codes[fieldarg])]
        except KeyError:
            return []

    def make_entry(self, fieldarg, content):
        # Wrap Field.make_entry, but intercept empty content and replace
        # it with default content.
        if not content:
            content = self.default_content(fieldarg)
        return super(TypedField, self).make_entry(fieldarg, content)


class NoArgGroupedField(GroupedField):
    def __init__(self, *args, **kwargs):
        super(NoArgGroupedField, self).__init__(*args, **kwargs)
        self.has_arg = False

    def make_field(self, types, domain, items):
        if len(items) == 1 and self.can_collapse:
            super(NoArgGroupedField, self).make_field(types, domain, items)
        fieldname = nodes.field_name('', self.label)
        listnode = self.list_type()
        for fieldarg, content in items:
            par = nodes.paragraph()
            par += content
            listnode += nodes.list_item('', par)
        fieldbody = nodes.field_body('', listnode)
        return nodes.field('', fieldname, fieldbody)

########NEW FILE########
__FILENAME__ = nodes
# -*- coding: utf-8 -*-
"""
    Nodes for the HTTP domain.
"""

from docutils import nodes

from sphinx.util.texescape import tex_escape_map


class HttpNode(nodes.Part, nodes.Inline, nodes.TextElement):
    """Generic HTTP node."""
    _writers = ['text', 'html', 'latex', 'man']

    def set_first(self):
        try:
            self.children[0].first = True
        except IndexError:
            pass

    @classmethod
    def contribute_to_app(cls, app):
        kwargs = {}
        for writer in cls._writers:
            visit = getattr(cls, 'visit_' + writer, None)
            depart = getattr(cls, 'depart_' + writer, None)
            if visit and depart:
                kwargs[writer] = (visit, depart)
        app.add_node(cls, **kwargs)

    @staticmethod
    def visit_text(self, node):
        pass

    @staticmethod
    def depart_text(self, node):
        pass

    @staticmethod
    def visit_latex(self, node):
        pass

    @staticmethod
    def depart_latex(self, node):
        pass

    @staticmethod
    def visit_man(self, node):
        pass

    @staticmethod
    def depart_man(self, node):
        pass


class desc_http_method(HttpNode):
    """HTTP method node."""
    def astext(self):
        return nodes.TextElement.astext(self) + ' '

    @staticmethod
    def depart_text(self, node):
        self.add_text(' ')

    @staticmethod
    def visit_html(self, node):
        self.body.append(self.starttag(node, 'tt', '',
                                       CLASS='descclassname deschttpmethod'))

    @staticmethod
    def depart_html(self, node):
        self.body.append(' </tt>')

    @staticmethod
    def visit_latex(self, node):
        self.body.append(r'\code{')
        self.literal_whitespace += 1

    @staticmethod
    def depart_latex(self, node):
        self.body.append(r'}~')
        self.literal_whitespace -= 1

    @staticmethod
    def depart_man(self, node):
        self.body.append(r'\~')


class desc_http_url(HttpNode):
    """HTTP URL node."""
    @staticmethod
    def visit_html(self, node):
        self.body.append(self.starttag(node, 'tt', '',
                                       CLASS='descname deschttpurl'))

    @staticmethod
    def depart_html(self, node):
        self.body.append('</tt>')

    @staticmethod
    def visit_latex(self, node):
        self.body.append(r'\bfcode{')
        self.literal_whitespace += 1

    @staticmethod
    def depart_latex(self, node):
        self.body.append(r'}')
        self.literal_whitespace -= 1


class desc_http_path(HttpNode):
    """HTTP path node. Contained in the URL node."""
    @staticmethod
    def visit_html(self, node):
        self.body.append(self.starttag(node, 'span', '',
                                       CLASS='deschttppath'))

    @staticmethod
    def depart_html(self, node):
        self.body.append('</span>')


class desc_http_patharg(HttpNode):
    """
    HTTP path argument node. Contained in the path node.

    This node is created when {argument} is found inside the path.
    """
    wrapper = (u'{', u'}')

    def astext(self, node):
        return (self.wrapper[0] +
                nodes.TextElement.astext(node) +
                self.wrapper[1])

    @staticmethod
    def visit_text(self, node):
        self.add_text(node.wrapper[0])

    @staticmethod
    def depart_text(self, node):
        self.add_text(node.wrapper[1])

    @staticmethod
    def visit_html(self, node):
        self.body.append(
            self.starttag(node, 'em', '', CLASS='deschttppatharg') +
            self.encode(node.wrapper[0]) +
            self.starttag(node, 'span', '', CLASS='deschttppatharg')
        )

    @staticmethod
    def depart_html(self, node):
        self.body.append('</span>' +
                         self.encode(node.wrapper[1]) +
                         '</em>')

    @staticmethod
    def visit_latex(self, node):
        self.body.append(r'\emph{' +
                         node.wrapper[0].translate(tex_escape_map))

    @staticmethod
    def depart_latex(self, node):
        self.body.append(node.wrapper[1].translate(tex_escape_map) +
                         '}')

    @staticmethod
    def visit_man(self, node):
        self.body.append(self.defs['emphasis'][0])
        self.body.append(self.deunicode(node.wrapper[0]))

    @staticmethod
    def depart_man(self, node):
        self.body.append(self.deunicode(node.wrapper[1]))
        self.body.append(self.defs['emphasis'][1])


class desc_http_query(HttpNode):
    """HTTP query string node. Contained in the URL node."""
    prefix = u'?'

    def astext(self):
        return self.prefix + nodes.TextElement.astext(self)

    @staticmethod
    def visit_text(self, node):
        self.add_text(node.prefix)
        node.set_first()

    @staticmethod
    def visit_html(self, node):
        self.body.append(
            self.starttag(node, 'span', '', CLASS='deschttpquery') +
            self.encode(node.prefix)
        )
        node.set_first()

    @staticmethod
    def depart_html(self, node):
        self.body.append('</span>')

    @staticmethod
    def visit_latex(self, node):
        self.body.append(node.prefix.translate(tex_escape_map))
        node.set_first()

    @staticmethod
    def visit_man(self, node):
        self.body.append(self.deunicode(node.prefix))
        node.set_first()


class desc_http_queryparam(HttpNode):
    """
    HTTP query string parameter node. Contained in the query string node.

    This node is created for each parameter inside a query string.
    """
    child_text_separator = u'&'
    first = False

    @staticmethod
    def visit_text(self, node):
        if not node.first:
            self.add_text(node.child_text_separator)

    @staticmethod
    def visit_html(self, node):
        if not node.first:
            self.body.append(self.encode(node.child_text_separator))
        self.body.append(self.starttag(node, 'em', '',
                                       CLASS='deschttpqueryparam'))

    @staticmethod
    def depart_html(self, node):
        self.body.append('</em>')

    @staticmethod
    def visit_latex(self, node):
        if not node.first:
            self.body.append(
                node.child_text_separator.translate(tex_escape_map)
            )
        self.body.append('\emph{')

    @staticmethod
    def depart_latex(self, node):
        self.body.append('}')

    @staticmethod
    def visit_man(self, node):
        if not node.first:
            self.body.append(self.deunicode(node.child_text_separator))
        self.body.append(self.defs['emphasis'][0])

    @staticmethod
    def depart_man(self, node):
        self.body.append(self.defs['emphasis'][1])


class desc_http_fragment(HttpNode):
    """HTTP fragment node. Contained in the URL node."""
    prefix = u'#'

    def astext(self):
        return self.prefix + nodes.TextElement.astext(self)

    @staticmethod
    def visit_text(self, node):
        self.add_text(node.prefix)

    @staticmethod
    def visit_html(self, node):
        self.body.append(self.encode(node.prefix) +
                         self.starttag(node, 'em', '',
                                       CLASS='deschttpfragment'))

    @staticmethod
    def depart_html(self, node):
        self.body.append('</em>')

    @staticmethod
    def visit_latex(self, node):
        self.body.append(node.prefix.translate(tex_escape_map) +
                         r'\emph{')

    @staticmethod
    def depart_latex(self, node):
        self.body.append('}')

    @staticmethod
    def visit_man(self, node):
        self.body.append(self.deunicode(node.prefix))
        self.body.append(self.defs['emphasis'][0])

    @staticmethod
    def depart_man(self, node):
        self.body.append(self.defs['emphasis'][1])


class desc_http_response(HttpNode):
    """HTTP response node."""

    @staticmethod
    def visit_html(self, node):
        self.body.append(self.starttag(node, 'strong', '',
                                       CLASS='deschttpresponse'))

    @staticmethod
    def depart_html(self, node):
        self.body.append('</strong>')

    @staticmethod
    def visit_latex(self, node):
        self.body.append(r'\textbf{')

    @staticmethod
    def depart_latex(self, node):
        self.body.append('}')

    @staticmethod
    def visit_man(self, node):
        self.body.append(self.defs['strong'][0])

    @staticmethod
    def depart_man(self, node):
        self.body.append(self.defs['strong'][1])

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
"""
    sphinx.domains.http
    ~~~~~~~~~~~~~~~~~~~

    Utilities for the HTTP domain.
"""

import re
import unicodedata


_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_strip_url_re = re.compile(r'[^\w\s/?=&#;{}-]')
_slugify_hyphenate_re = re.compile(r'[^\w]+')


def slugify(value, strip_re=_slugify_strip_re):
    """
    Normalizes string, converts to lowercase, removes non-alpha
    characters, and converts spaces to hyphens.

    From Django's "django/template/defaultfilters.py".
    """
    if not isinstance(value, unicode):
        value = unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(strip_re.sub('', value).strip().lower())
    return _slugify_hyphenate_re.sub('-', value)


def slugify_url(value):
    """
    Normalizes URL, converts to lowercase, removes non-URL
    characters, and converts non-alpha characters to hyphens.
    """
    return slugify(value, strip_re=_slugify_strip_url_re)

########NEW FILE########
