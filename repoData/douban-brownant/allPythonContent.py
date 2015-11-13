__FILENAME__ = app
from __future__ import absolute_import, unicode_literals

from warnings import warn

from six import string_types
from six.moves import urllib
from werkzeug.utils import import_string
from werkzeug.urls import url_decode, url_encode
from werkzeug.routing import Map, Rule, NotFound, RequestRedirect

from .request import Request
from .exceptions import NotSupported
from .utils import to_bytes_safe


class Brownant(object):
    """The app which could manage whole crawler system."""

    def __init__(self):
        self.url_map = Map(strict_slashes=False, host_matching=True,
                           redirect_defaults=False)

    def add_url_rule(self, host, rule_string, endpoint, **options):
        """Add a url rule to the app instance.

        The url rule is the same with Flask apps and other Werkzeug apps.

        :param host: the matched hostname. e.g. "www.python.org"
        :param rule_string: the matched path pattern. e.g. "/news/<int:id>"
        :param endpoint: the endpoint name as a dispatching key such as the
                         qualified name of the object.
        """
        rule = Rule(rule_string, host=host, endpoint=endpoint, **options)
        self.url_map.add(rule)

    def parse_url(self, url_string):
        """Parse the URL string with the url map of this app instance.

        :param url_string: the origin URL string.
        :returns: the tuple as `(url, url_adapter, query_args)`, the url is
                  parsed by the standard library `urlparse`, the url_adapter is
                  from the werkzeug bound URL map, the query_args is a
                  multidict from the werkzeug.
        """
        url = urllib.parse.urlparse(url_string)
        url = self.validate_url(url)
        url_adapter = self.url_map.bind(server_name=url.hostname,
                                        url_scheme=url.scheme,
                                        path_info=url.path)
        query_args = url_decode(url.query)
        return url, url_adapter, query_args

    def validate_url(self, url):
        """Validate the :class:`~urllib.parse.ParseResult` object.

        This method will make sure the :meth:`~brownant.app.BrownAnt.parse_url`
        could work as expected even meet a unexpected URL string.

        :param url: the parsed url.
        :type url: :class:`~urllib.parse.ParseResult`
        """
        # fix up the non-ascii path
        url_path = to_bytes_safe(url.path)
        url_path = urllib.parse.quote(url_path, safe=b"/%")

        # fix up the non-ascii query
        url_query = to_bytes_safe(url.query)
        url_query = urllib.parse.quote(url_query, safe=b"?=&")

        url = urllib.parse.ParseResult(url.scheme, url.netloc, url_path,
                                       url.params, url_query, url.fragment)

        # validate the components of URL
        has_hostname = url.hostname is not None and len(url.hostname) > 0
        has_http_scheme = url.scheme in ("http", "https")
        has_path = not len(url.path) or url.path.startswith("/")

        if not (has_hostname and has_http_scheme and has_path):
            raise NotSupported("invalid url: %s" % repr(url))

        return url

    def dispatch_url(self, url_string):
        """Dispatch the URL string to the target endpoint function.

        :param url_string: the origin URL string.
        :returns: the return value of calling dispatched function.
        """
        url, url_adapter, query_args = self.parse_url(url_string)

        try:
            endpoint, kwargs = url_adapter.match()
        except NotFound:
            raise NotSupported(url_string)
        except RequestRedirect as e:
            new_url = "{0.new_url}?{1}".format(e, url_encode(query_args))
            return self.dispatch_url(new_url)

        try:
            handler = import_string(endpoint)
            request = Request(url=url, args=query_args)
            return handler(request, **kwargs)
        except RequestRedirect as e:
            return self.dispatch_url(e.new_url)

    def mount_site(self, site):
        """Mount a supported site to this app instance.

        :param site: the site instance be mounted.
        """
        if isinstance(site, string_types):
            site = import_string(site)
        site.play_actions(target=self)


class BrownAnt(Brownant):
    def __init__(self, *args, **kwargs):
        warn("The class name 'BrownAnt' has been deprecated. Please use "
             "'Brownant' instead.", DeprecationWarning)
        super(BrownAnt, self).__init__(*args, **kwargs)


def redirect(url):
    """Raise the :class:`~werkzeug.routing.RequestRedirect` exception to lead
    the app dispatching current request to another URL.

    :param url: the target URL.
    """
    raise RequestRedirect(url)

########NEW FILE########
__FILENAME__ = dinergate
from six import with_metaclass
from werkzeug.utils import cached_property

from brownant.pipeline.network import HTTPClientProperty


class DinergateType(type):
    """The metaclass of :class:`~brownant.dinergate.Dinergate` and its
    subclasses.

    This metaclass will give all members are instance of
    :class:`~werkzeug.utils.cached_property` default names. It is because many
    pipeline properties are subclasses of
    :class:`~werkzeug.utils.cached_property`, but them would not be created by
    decorating functions. They will has not built-in :attr:`__name__`, which
    may cause them could not cache values as expected.
    """

    def __new__(metacls, name, bases, members):
        cls = type.__new__(metacls, name, bases, members)
        for name in dir(cls):
            value = getattr(cls, name)
            if isinstance(value, cached_property) and not value.__name__:
                value.__name__ = name
                value.__module__ = cls.__module__
        return cls


class Dinergate(with_metaclass(DinergateType)):
    """The simple classify crawler.

    In order to work with unnamed properties such as the instances of
    :class:`~brownant.pipeline.base.PipelineProperty`, the meta class
    :class:`~brownant.dinergate.DinergateType` will scan subclasses of this
    class and name all unnamed members which are instances of
    :class:`~werkzeug.utils.cached_property`.

    :param request: the standard parameter passed by app.
    :type request: :class:`~brownant.request.Request`
    :param http_client: the session instance of python-requests.
    :type http_client: :class:`requests.Session`
    :param kwargs: other arguments from the URL pattern.
    """

    #: the URL template string for generating crawled target. the `self` could
    #: be referenced in the template.
    #: (e.g. `"http://www.example.com/items/{self.item_id}?page={self.page}"`)
    URL_TEMPLATE = None

    http_client = HTTPClientProperty()

    def __init__(self, request, http_client=None, **kwargs):
        self.request = request
        if http_client:
            self.http_client = http_client
        # assign arguments from URL pattern
        vars(self).update(kwargs)

    @property
    def url(self):
        """The fetching target URL.

        The default behavior of this property is build URL string with the
        :const:`~brownant.dinergate.Dinergate.URL_TEMPLATE`.

        The subclasses could override
        :const:`~brownant.dinergate.Dinergate.URL_TEMPLATE` or use a different
        implementation.
        """
        if not self.URL_TEMPLATE:
            raise NotImplementedError
        return self.URL_TEMPLATE.format(self=self)

########NEW FILE########
__FILENAME__ = exceptions
from __future__ import absolute_import, unicode_literals


class BrownantException(Exception):
    """The base exception of the Brownant framework."""


class NotSupported(BrownantException):
    """The given URL or other identity is from a platform which not support.

    This exception means any url rules of the app which matched the URL could
    not be found.
    """

########NEW FILE########
__FILENAME__ = base
from werkzeug.utils import cached_property


class PipelineProperty(cached_property):
    """The base class of pipeline properties.

    There are three kinds of initial parameters.

    - The required attribute. If a keyword argument's name was defined in
      :attr:`~brownant.pipeline.base.PipelineProperty.required_attrs`, it will
      be assigned as an instance attribute.

    - The attr_name. It is the member of
      :attr:`~brownant.pipeline.base.PipelineProperty.attr_names`, whose name
      always end with `_attr`, such as `text_attr`.

    - The option. It will be placed at an instance owned :class:`dict` named
      :attr:`~brownant.pipeline.base.PipelineProperty.options`. The subclasses
      could set default option value in the
      :meth:`~brownant.pipeline.base.PipelineProperty.prepare`.

    A workable subclass of :class:`~brownant.pipeline.base.PipelineProperty`
    should implement the abstruct method
    :meth:`~PipelineProperty.provide_value`, which accept an argument, the
    instance of :class:`~brownant.dinergate.Dinergate`.

    Overriding :meth:`~brownant.pipeline.base.PipelineProperty.prepare` is
    optional in subclasses.

    :param kwargs: the parameters with the three kinds.
    """

    #: the names of required attributes.
    required_attrs = set()

    def __init__(self, **kwargs):
        super(PipelineProperty, self).__init__(self.provide_value)
        self.__name__ = None
        self.__module__ = None
        self.__doc__ = None

        #: the definition of attr_names
        self.attr_names = {}
        #: the definition of options
        self.options = {}

        assigned_attrs = set()
        for name, value in kwargs.items():
            assigned_attrs.add(name)

            # names of attrs
            if name.endswith("_attr"):
                self.attr_names[name] = value
            # required attrs
            elif name in self.required_attrs:
                setattr(self, name, value)
            # optional attrs
            else:
                self.options[name] = value
        missing_attrs = self.required_attrs - assigned_attrs
        if missing_attrs:
            raise TypeError("missing %r" % ", ".join(missing_attrs))

        self.prepare()

    def prepare(self):
        """This method will be called after instance ininialized. The
        subclasses could override the implementation.

        In general purpose, the implementation of this method should give
        default value to options and the members of
        :attr:`~brownant.pipeline.base.PipelineProperty.attr_names`.

        Example:

        .. code-block:: python

           def prepare(self):
               self.attr_names.setdefault("text_attr", "text")
               self.options.setdefault("use_proxy", False)
        """

    def get_attr(self, obj, name):
        """Get attribute of the target object with the configured attribute
        name in the :attr:`~brownant.pipeline.base.PipelineProperty.attr_names`
        of this instance.

        :param obj: the target object.
        :type obj: :class:`~brownant.dinergate.Dinergate`
        :param name: the internal name used in the
                :attr:`~brownant.pipeline.base.PipelineProperty.attr_names`.
                (.e.g. `"text_attr"`)
        """
        attr_name = self.attr_names[name]
        return getattr(obj, attr_name)

########NEW FILE########
__FILENAME__ = html
import lxml.html

from brownant.pipeline.base import PipelineProperty


class ElementTreeProperty(PipelineProperty):
    """The element tree built from a text response property. There is an usage
    example::

        class MySite(Dinergate):
            text_response = "<html></html>"
            div_response = "<div></div>"
            xml_response = (u"<?xml version='1.0' encoding='UTF-8'?>"
                            u"<result>\u6d4b\u8bd5</result>")
            etree = ElementTreeProperty()
            div_etree = ElementTreeProperty(text_response_attr="div_response")
            xml_etree = ElementTreeProperty(text_response_attr="xml_response",
                                            encoding="utf-8")

        site = MySite(request)
        print(site.etree)  # output: <Element html at 0x1f59350>
        print(site.div_etree)  # output: <Element div at 0x1f594d0>
        print(site.xml_etree)  # output: <Element result at 0x25b14b0>

    :param text_response_attr: optional. default: `"text_response"`.
    :param encoding: optional. default: `None`. The output text could be
                     encoded to a specific encoding.

    .. versionadded:: 0.1.4
       The `encoding` optional parameter.
    """

    def prepare(self):
        self.attr_names.setdefault("text_response_attr", "text_response")
        self.options.setdefault("encoding", None)

    def provide_value(self, obj):
        text_response = self.get_attr(obj, "text_response_attr")
        if self.options["encoding"]:
            text_response = text_response.encode(self.options["encoding"])
        return lxml.html.fromstring(text_response)


class XPathTextProperty(PipelineProperty):
    """The text extracted from a element tree property by XPath. There is an
    example for usage::

        class MySite(Dinergate):
            # omit page_etree
            title = XPathTextProperty(xpath=".//h1[@id='title']/text()",
                                      etree_attr="page_etree",
                                      strip_spaces=True,
                                      pick_mode="first")
            links = XPathTextProperty(xpath=".//*[@id='links']/a/@href",
                                      etree_attr="page_etree",
                                      strip_spaces=True,
                                      pick_mode="join",
                                      joiner="|")

    :param xpath: the xpath expression for extracting text.
    :param etree_attr: optional. default: `"etree"`.
    :param strip_spaces: optional. default: `False`. if it be `True`,
                         the spaces in the beginning and the end of texts will
                         be striped.
    :param pick_mode: optional. default: `"join"`, and could be "join", "first"
                      or "keep". while `"join"` be detected, the texts will be
                      joined to one. if the `"first"` be detected, only
                      the first text would be picked. if the `"keep"` be
                      detected, the original value will be picked.
    :param joiner: optional. default is a space string. it is no sense in
                   assigning this parameter while the `pick_mode` is not
                   `"join"`. otherwise, the texts will be joined by this
                   string.

    .. versionadded:: 0.1.4
       The new option value `"keep"` of the `pick_mode` parameter.
    """

    required_attrs = {"xpath"}

    def prepare(self):
        self.attr_names.setdefault("etree_attr", "etree")
        self.options.setdefault("strip_spaces", False)
        self.options.setdefault("pick_mode", "join")
        self.options.setdefault("joiner", " ")

    def choice_pick_impl(self):
        pick_mode = self.options["pick_mode"]
        impl = {
            "join": self.pick_joining,
            "first": self.pick_first,
            "keep": self.keep_value,
        }.get(pick_mode)

        if not impl:
            raise ValueError("%r is not valid pick mode" % pick_mode)
        return impl

    def pick_joining(self, value):
        joiner = self.options["joiner"]
        return joiner.join(value)

    def pick_first(self, value):
        return value[0] if value else ""

    def keep_value(self, value):
        return value

    def provide_value(self, obj):
        etree = self.get_attr(obj, "etree_attr")
        value = etree.xpath(self.xpath)
        pick_value = self.choice_pick_impl()

        if self.options["strip_spaces"]:
            value = [v.strip() for v in value if v.strip()]

        return pick_value(value)

########NEW FILE########
__FILENAME__ = network
from requests import Session

from brownant.pipeline.base import PipelineProperty
from brownant.exceptions import NotSupported


class HTTPClientProperty(PipelineProperty):
    """The python-requests session property.

    :param session_class: the class of session instance. default be
                          :class:`~requests.Session`.
    """

    def prepare(self):
        self.options.setdefault("session_class", Session)

    def provide_value(self, obj):
        session_class = self.options["session_class"]
        session = session_class()
        return session


class URLQueryProperty(PipelineProperty):
    """The query argument property. The usage is simple::

        class MySite(Dinergate):
            item_id = URLQueryProperty(name="item_id", type=int)

    It equals to this::

        class MySite(Dinergate):
            @cached_property
            def item_id(self):
                value = self.request.args.get("item_id", type=int)
                if not value:
                    raise NotSupported
                return value

    A failure convertion with given type (:exc:`ValueError` be raised) will
    lead the value fallback to :obj:`None`. It is the same with the behavior of
    the :class:`~werkzeug.datastructures.MultiDict`.

    :param name: the query argument name.
    :param request_attr: optional. default: `"request"`.
    :param type: optionl. default: `None`. this value will be passed to
                 :meth:`~werkzeug.datastructures.MultiDict.get`.
    :param required: optionl. default: `True`. while this value be true, the
                     :exc:`~brownant.exceptions.NotSupported` will be raised
                     for meeting empty value.
    """

    required_attrs = {"name"}

    def prepare(self):
        self.attr_names.setdefault("request_attr", "request")
        self.options.setdefault("type", None)
        self.options.setdefault("required", True)

    def provide_value(self, obj):
        request = self.get_attr(obj, "request_attr")
        value = request.args.get(self.name, type=self.options["type"])
        if self.options["required"] and value is None:
            raise NotSupported
        return value


class TextResponseProperty(PipelineProperty):
    """The text response which returned by fetching network resource.

    Getting this property is network I/O operation in the first time. The
    http request implementations are all provided by :mod:`requests`.

    The usage example::

        class MySite(Dinergate):
            foo_http = requests.Session()
            foo_url = "http://example.com"
            foo_text = TextResponseProperty(url_attr="foo_url",
                                            http_client="foo_http",
                                            proxies=PROXIES)

    :param url_attr: optional. default: `"url"`. it point to the property which
                     could provide the fetched url.
    :param http_client_attr: optional. default: `"http_client"`. it point to
                             an http client property which is instance of
                             :class:`requests.Session`
    :param kwargs: the optional arguments which will be passed to
                   :meth:`requests.Session.get`.
    """

    def prepare(self):
        self.attr_names.setdefault("url_attr", "url")
        self.attr_names.setdefault("http_client_attr", "http_client")

    def provide_value(self, obj):
        url = self.get_attr(obj, "url_attr")
        http_client = self.get_attr(obj, "http_client_attr")
        response = http_client.get(url, **self.options)
        response.raise_for_status()
        return response.text

########NEW FILE########
__FILENAME__ = request
from __future__ import absolute_import, unicode_literals


class Request(object):
    """The request object.

    :param url: the raw URL inputted from the dispatching app.
    :type url: :class:`urllib.parse.ParseResult`
    :param args: the query arguments decoded from query string of the URL.
    :type args: :class:`werkzeug.datastructures.MultiDict`
    """

    def __init__(self, url, args):
        self.url = url
        self.args = args

    def __repr__(self):
        return "Request(url={self.url}, args={self.args})".format(self=self)

########NEW FILE########
__FILENAME__ = site
from __future__ import absolute_import, unicode_literals


class Site(object):
    """The site supported object which could be mounted to app instance.

    :param name: the name of the supported site.
    """

    def __init__(self, name):
        self.name = name
        self.actions = []

    def record_action(self, method_name, *args, **kwargs):
        """Record the method-calling action.

        The actions expect to be played on an target object.

        :param method_name: the name of called method.
        :param args: the general arguments for calling method.
        :param kwargs: the keyword arguments for calling method.
        """
        self.actions.append((method_name, args, kwargs))

    def play_actions(self, target):
        """Play record actions on the target object.

        :param target: the target which recive all record actions, is a brown
                       ant app instance normally.
        :type target: :class:`~brownant.app.Brownant`
        """
        for method_name, args, kwargs in self.actions:
            method = getattr(target, method_name)
            method(*args, **kwargs)

    def route(self, host, rule, **options):
        """The decorator to register wrapped function as the brown ant app.

        All optional parameters of this method are compatible with the
        :meth:`~brownant.app.Brownant.add_url_rule`.

        Registered functions or classes must be import-able with its qualified
        name. It is different from the :class:`~flask.Flask`, but like a
        lazy-loading mode. Registered objects only be loaded before the first
        using.

        The right way::

            @site.route("www.example.com", "/item/<int:item_id>")
            def spam(request, item_id):
                pass

        The wrong way::

            def egg():
                # the function could not be imported by its qualified name
                @site.route("www.example.com", "/item/<int:item_id>")
                def spam(request, item_id):
                    pass

            egg()

        :param host: the limited host name.
        :param rule: the URL path rule as string.
        :param options: the options to be forwarded to the
                        :class:`werkzeug.routing.Rule` object.
        """
        def decorator(func):
            endpoint = "{func.__module__}:{func.__name__}".format(func=func)
            self.record_action("add_url_rule", host, rule, endpoint, **options)
            return func
        return decorator

########NEW FILE########
__FILENAME__ = utils
from six import text_type


def to_bytes_safe(text, encoding="utf-8"):
    """Convert the input value into bytes type.

    If the input value is string type and could be encode as UTF-8 bytes, the
    encoded value will be returned. Otherwise, the encoding has failed, the
    origin value will be returned as well.

    :param text: the input value which could be string or bytes.
    :param encoding: the expected encoding be used while converting the string
                     input into bytes.
    :rtype: :class:`~__builtin__.bytes`
    """
    if not isinstance(text, (bytes, text_type)):
        raise TypeError("must be string type")

    if isinstance(text, text_type):
        return text.encode(encoding)

    return text

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# brownant documentation build configuration file, created by
# sphinx-quickstart on Sun Sep 29 00:53:05 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

import alabaster

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Brownant'
copyright = u'2014, Douban Inc.'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1.5'
# The full version, including alpha/beta/rc tags.
release = '0.1.5'

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
exclude_patterns = ['_build', '_static']

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
html_theme = 'alabaster'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    'github_user': 'douban',
    'github_repo': 'brownant',
}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = [alabaster.get_path()]

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
html_sidebars = {
    '**': [
        'about.html',
        'localtoc.html',
        'relations.html',
        'sourcelink.html',
        'searchbox.html'
    ]
}

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
htmlhelp_basename = 'brownantdoc'


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
  ('index', 'brownant.tex', u'Brownant Documentation',
   u'Douban Inc.', 'manual'),
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
    ('index', 'brownant', u'Brownant Documentation',
     [u'Douban Inc.'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'brownant', u'Brownant Documentation',
   u'Douban Inc.', 'brownant', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'Brownant'
epub_author = u'Douban Inc.'
epub_publisher = u'Douban Inc.'
epub_copyright = u'2014, Douban Inc.'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# A tuple containing the cover image and cover page html template filenames.
#epub_cover = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'http://docs.python.org/dev': None,
    'http://docs.python-requests.org/en/latest/': None,
    'http://werkzeug.pocoo.org/docs/': None,
    'http://flask.pocoo.org/docs/': None,
}

########NEW FILE########
__FILENAME__ = test_app
from __future__ import absolute_import, unicode_literals

from pytest import fixture, raises
from mock import patch

from brownant import Brownant, redirect
from brownant.exceptions import NotSupported


class StubEndpoint(object):

    name = __name__ + ".StubEndpoint"

    def __init__(self, request, id_, **kwargs):
        self.request = request
        self.id_ = id_


def redirect_endpoint(request, **kwargs):
    should_redirect = (request.args.get("r") == "1")
    if should_redirect:
        return redirect("http://redirect.example.com/42?id=24")
    return kwargs, request


redirect_endpoint.__qualname__ = __name__ + "." + redirect_endpoint.__name__


@fixture
def app():
    _app = Brownant()
    _app.add_url_rule("m.example.com", "/item/<int:id_>", StubEndpoint.name)
    _app.add_url_rule("m.example.co.jp", "/item/<id_>", StubEndpoint.name)
    return _app


def test_new_app(app):
    assert isinstance(app, Brownant)
    assert callable(app.add_url_rule)
    assert callable(app.dispatch_url)
    assert callable(app.mount_site)


def test_match_url(app):
    stub = app.dispatch_url("http://m.example.com/item/289263?page=1&q=t")

    assert stub.id_ == 289263
    assert stub.request.args["page"] == "1"
    assert stub.request.args["q"] == "t"

    with raises(KeyError):
        stub.request.args["other"]

    assert repr(stub.request).startswith("Request(")
    assert repr(stub.request).endswith(")")
    assert "url=" in repr(stub.request)
    assert "m.example.com" in repr(stub.request)
    assert "/item/289263" in repr(stub.request)
    assert "args=" in repr(stub.request)

    assert stub.request.url.scheme == "http"
    assert stub.request.url.hostname == "m.example.com"
    assert stub.request.url.path == "/item/289263"

    assert stub.request.args.get("page", type=int) == 1
    assert stub.request.args["q"] == "t"


def test_match_url_without_redirect(app):
    app.add_url_rule("detail.example.com", "/item/<int:id_>",
                     StubEndpoint.name, defaults={"p": "a"})
    app.add_url_rule("mdetail.example.com", "/item/<int:id_>",
                     StubEndpoint.name, defaults={"p": "a"})

    stub = app.dispatch_url("http://detail.example.com/item/12346?page=6")
    assert stub.id_ == 12346
    assert stub.request.args.get("page", type=int) == 6

    stub = app.dispatch_url("http://mdetail.example.com/item/12346?page=6")
    assert stub.id_ == 12346
    assert stub.request.args.get("page", type=int) == 6


def test_match_url_with_redirect(app):
    app.add_url_rule("m.example.com", "/42", StubEndpoint.name,
                     redirect_to="item/42")

    stub = app.dispatch_url("http://m.example.com/item/42/?page=6")
    assert stub.id_ == 42
    assert stub.request.args.get("page", type=int) == 6

    stub = app.dispatch_url("http://m.example.com/42?page=6")
    assert stub.id_ == 42
    assert stub.request.args.get("page", type=int) == 6

    stub = app.dispatch_url("http://m.example.com/item/42/")
    assert stub.id_ == 42
    with raises(KeyError):
        stub.request.args["page"]

    stub = app.dispatch_url("http://m.example.com/42")
    assert stub.id_ == 42
    with raises(KeyError):
        stub.request.args["page"]


def test_match_url_and_handle_user_redirect(app):
    domain = "redirect.example.com"
    app.add_url_rule(domain, "/<id>", redirect_endpoint.__qualname__)

    kwargs, request = app.dispatch_url("http://{0}/123?id=5".format(domain))
    assert kwargs == {"id": "123"}
    assert request.args["id"] == "5"

    kwargs, request = app.dispatch_url("http://{0}/1?id=5&r=1".format(domain))
    assert kwargs == {"id": "42"}
    assert request.args["id"] == "24"


def test_match_non_ascii_url(app):
    url = u"http://m.example.co.jp/item/\u30de\u30a4\u30f3\u30c9"
    stub = app.dispatch_url(url)

    encoded_path = "/item/%E3%83%9E%E3%82%A4%E3%83%B3%E3%83%89"
    assert stub.request.url.scheme == "http"
    assert stub.request.url.hostname == "m.example.co.jp"
    assert stub.request.url.path == encoded_path


def test_match_non_ascii_query(app):
    url = u"http://m.example.co.jp/item/test?src=\u63a2\u9669&r=1"
    stub = app.dispatch_url(url)

    assert stub.request.url.scheme == "http"
    assert stub.request.url.hostname == "m.example.co.jp"
    assert stub.request.url.path == "/item/test"
    assert stub.request.url.query == "src=%E6%8E%A2%E9%99%A9&r=1"

    assert set(stub.request.args) == {"src", "r"}
    assert stub.request.args["src"] == u"\u63a2\u9669"
    assert stub.request.args["r"] == "1"


def test_match_unexcepted_url(app):
    unexcepted_url = "http://m.example.com/category/19352"

    with raises(NotSupported) as error:
        app.dispatch_url(unexcepted_url)

    # ensure the exception information is useful
    assert unexcepted_url in str(error)

    # ensure the rule could be added in runtime
    app.add_url_rule("m.example.com", "/category/<int:id_>", StubEndpoint.name)
    stub = app.dispatch_url(unexcepted_url)
    assert stub.id_ == 19352
    assert len(stub.request.args) == 0


def test_match_invalid_url(app):
    # empty string
    with raises(NotSupported) as error:
        app.dispatch_url("")
    assert "invalid" in str(error)

    # has not hostname
    with raises(NotSupported) as error:
        app.dispatch_url("/")
    assert "invalid" in str(error)

    # has not hostname and path
    with raises(NotSupported) as error:
        app.dispatch_url("\\")
    assert "invalid" in str(error)

    # not http scheme
    with raises(NotSupported) as error:
        app.dispatch_url("ftp://example.com")
    assert "invalid" in str(error)

    # valid input
    with raises(NotSupported) as error:
        app.dispatch_url("http://example.com")
    assert "invalid" not in str(error)

    with raises(NotSupported) as error:
        app.dispatch_url("https://example.com")
    assert "invalid" not in str(error)


foo_site = object()


def test_mount_site(app):
    foo_site_name = __name__ + ".foo_site"
    with patch(foo_site_name):
        app.mount_site(foo_site)
        foo_site.play_actions.assert_called_with(target=app)


def test_mount_site_by_string_name(app):
    foo_site_name = __name__ + ".foo_site"
    with patch(foo_site_name):
        app.mount_site(foo_site_name)
        foo_site.play_actions.assert_called_with(target=app)

########NEW FILE########
__FILENAME__ = test_deprecation
from brownant import Brownant, BrownAnt


def test_deprecation(recwarn):
    app = BrownAnt()
    warning = recwarn.pop(DeprecationWarning)

    assert isinstance(app, Brownant)
    assert issubclass(warning.category, DeprecationWarning)
    assert "Brownant" in str(warning.message)
    assert "app.py" in warning.filename
    assert warning.lineno

########NEW FILE########
__FILENAME__ = test_dinergate
from __future__ import absolute_import, unicode_literals

from mock import Mock
from pytest import raises

from brownant import Dinergate


def test_basic():
    from requests import Session
    from werkzeug.utils import cached_property

    @cached_property
    def func_without_name(self):
        return [self]
    func_without_name.__name__ = None

    class FooDinergate(Dinergate):
        bar = func_without_name

    assert FooDinergate.bar.__name__ == "bar"

    mock_request = Mock()
    ant = FooDinergate(mock_request)

    assert ant.request is mock_request
    assert isinstance(ant.http_client, Session)
    assert ant.bar == [ant]


def test_custom_kwargs():
    mock_request = Mock()
    ant = Dinergate(mock_request, foo=42, bar="hello")
    assert ant.foo == 42
    assert ant.bar == "hello"


def test_custom_http_client():
    mock_request = Mock()
    mock_http_client = Mock()
    ant = Dinergate(mock_request, mock_http_client)

    ant.request.args.get("name", type=str)
    mock_request.args.get.assert_called_once_with("name", type=str)

    ant.http_client.post("http://example.com")
    mock_http_client.post.assert_called_once_with("http://example.com")


def test_url_template():
    class FooDinergate(Dinergate):
        foo = 42
        bar = "page"

        URL_TEMPLATE = "http://example.com/{self.bar}/{self.foo}"

    ant = FooDinergate(request=Mock(), http_client=Mock())
    assert ant.url == "http://example.com/page/42"

    dead_ant = Dinergate(request=Mock(), http_client=Mock())
    with raises(NotImplementedError):
        dead_ant.url

########NEW FILE########
__FILENAME__ = test_base
from __future__ import absolute_import, unicode_literals

from pytest import raises

from brownant.pipeline.base import PipelineProperty


def test_required_attrs():
    class SpamProperty(PipelineProperty):
        required_attrs = {"egg"}

        def provide_value(self, obj):
            return obj

    # valid
    spam_property = SpamProperty(egg=42)
    assert spam_property.egg == 42
    assert "egg" not in spam_property.options
    assert "egg" not in spam_property.attr_names
    with raises(AttributeError):
        spam_property.foo

    # invalid
    with raises(TypeError) as excinfo:
        spam_property = SpamProperty(spam=42)
    assert "egg" in repr(excinfo.value)


def test_attr_name():
    class SpamProperty(PipelineProperty):
        def prepare(self):
            self.attr_names.setdefault("egg_attr", "egg")

        def provide_value(self, obj):
            return self.get_attr(obj, "egg_attr")

    class Spam(object):
        def __init__(self, **kwargs):
            vars(self).update(kwargs)

    spam_a = SpamProperty(egg=42)
    assert spam_a.attr_names["egg_attr"] == "egg"
    assert spam_a.provide_value(Spam(egg=1024)) == 1024

    spam_b = SpamProperty(egg=42, egg_attr="foo_egg")
    assert spam_b.attr_names["egg_attr"] == "foo_egg"
    assert spam_b.provide_value(Spam(foo_egg=2048)) == 2048


def test_optional_attr():
    class SpamProperty(PipelineProperty):
        required_attrs = {"egg"}

        def provide_value(self, obj):
            return obj

    spam = SpamProperty(egg=41, foo=42, bar=43, aha_attr=44)
    assert spam.options["foo"] == 42
    assert spam.options["bar"] == 43
    assert "egg" not in spam.options
    assert "aha_attr" not in spam.options

########NEW FILE########
__FILENAME__ = test_html
from __future__ import absolute_import, unicode_literals

from pytest import raises
from mock import patch, Mock

from brownant.pipeline.html import ElementTreeProperty, XPathTextProperty


# ElementTreeProperty

def test_etree_default_attr_name():
    etree = ElementTreeProperty()
    assert etree.attr_names["text_response_attr"] == "text_response"


def test_etree_default_encoding_show_be_none():
    etree = ElementTreeProperty()
    assert etree.options["encoding"] is None


@patch("lxml.html.fromstring")
def test_etree_general_parse_with_default(fromstring):
    mock = Mock()
    etree = ElementTreeProperty()
    etree.provide_value(mock)
    fromstring.assert_called_once_with(mock.text_response)


@patch("lxml.html.fromstring")
def test_etree_general(fromstring):
    mock = Mock()
    etree = ElementTreeProperty(text_response_attr="foo")
    etree.provide_value(mock)
    fromstring.assert_called_once_with(mock.foo)


@patch("lxml.html.fromstring")
def test_etree_general_parse_with_encoding(fromstring):
    mock = Mock()
    etree = ElementTreeProperty(text_response_attr="foo",
                                encoding="utf-8")
    etree.provide_value(mock)
    fromstring.assert_called_once_with(mock.foo.encode("utf-8"))


# XPathTextProperty

def test_xpath_default_attr_name():
    with raises(TypeError):
        XPathTextProperty()

    text = XPathTextProperty(xpath="//path")
    assert text.xpath == "//path"
    assert text.attr_names["etree_attr"] == "etree"
    assert text.options["strip_spaces"] is False
    assert text.options["pick_mode"] == "join"
    assert text.options["joiner"] == " "


def test_xpath_without_spaces():
    mock = Mock()
    mock.tree.xpath.return_value = ["a", "b", "c"]

    # pick_mode: join
    text = XPathTextProperty(xpath="//path", etree_attr="tree",
                             pick_mode="join", joiner="|")
    rv = text.provide_value(mock)
    mock.tree.xpath.assert_called_with("//path")
    assert rv == "a|b|c"

    # pick_mode: first
    text = XPathTextProperty(xpath="//another-path", etree_attr="tree",
                             pick_mode="first")
    rv = text.provide_value(mock)
    mock.tree.xpath.assert_called_with("//another-path")
    assert rv == "a"


def test_xpath_with_striping_spaces():
    mock = Mock()
    mock.tree.xpath.return_value = [" a ", "\n b \n", "\n\n c  \t"]

    # strip_spaces and join
    text = XPathTextProperty(xpath="//foo-path", etree_attr="tree",
                             pick_mode="join", strip_spaces=True)
    rv = text.provide_value(mock)
    mock.tree.xpath.assert_called_with("//foo-path")
    assert rv == "a b c"

    # strip_spaces and first
    text = XPathTextProperty(xpath="//bar-path", etree_attr="tree",
                             pick_mode="first", strip_spaces=True)
    rv = text.provide_value(mock)
    mock.tree.xpath.assert_called_with("//bar-path")
    assert rv == "a"


def test_xpath_keep_pick_mode():
    mock = Mock()
    value = ['a', 'b', 'c']
    mock.tree.xpath.return_value = value

    text = XPathTextProperty(xpath="//foo-path", etree_attr="tree",
                             pick_mode="keep")
    rv = text.provide_value(mock)
    mock.tree.xpath.assert_called_with("//foo-path")
    assert rv == value


def test_xpath_invalid_pick_mode():
    with raises(ValueError) as excinfo:
        text = XPathTextProperty(xpath="//foo-path", pick_mode="unknown")
        text.provide_value(Mock())
    assert "unknown" in repr(excinfo.value)

########NEW FILE########
__FILENAME__ = test_network
from __future__ import absolute_import, unicode_literals

from mock import Mock, patch
from pytest import raises

from brownant.exceptions import NotSupported
from brownant.pipeline.network import (HTTPClientProperty, URLQueryProperty,
                                       TextResponseProperty)


def test_http_client():
    dinergate = Mock()
    with patch("requests.Session") as Session:
        instance = Session.return_value
        http_client = HTTPClientProperty(session_class=Session)
        assert http_client.provide_value(dinergate) is instance
        Session.assert_called_once_with()


def test_url_query():
    mock = Mock()
    mock.request.args.get.return_value = "42"

    url_query = URLQueryProperty(name="value")
    rv = url_query.provide_value(mock)

    assert rv == "42"
    mock.request.args.get.assert_called_once_with("value", type=None)


def test_url_query_type():
    mock = Mock()
    mock.request.args.get.return_value = 42

    url_query = URLQueryProperty(name="value", type=int)
    rv = url_query.provide_value(mock)

    assert rv == 42
    mock.request.args.get.assert_called_once_with("value", type=int)


def test_url_query_required():
    mock = Mock()
    mock.request.args.get.return_value = None

    url_query = URLQueryProperty(name="value")  # default be required
    with raises(NotSupported):
        url_query.provide_value(mock)


def test_url_query_optional():
    mock = Mock()
    mock.request.args.get.return_value = None

    url_query = URLQueryProperty(name="d", type=float, required=False)
    rv = url_query.provide_value(mock)

    assert rv is None
    mock.request.args.get.assert_called_once_with("d", type=float)


def test_url_query_required_boundary_condition():
    mock = Mock()
    mock.request.args.get.return_value = 0

    url_query = URLQueryProperty(name="num")
    rv = url_query.provide_value(mock)

    assert rv == 0
    mock.request.args.get.assert_called_once_with("num", type=None)


def test_text_response():
    class HTTPError(Exception):
        pass

    response = Mock()
    response.text = "OK"
    response.raise_for_status.side_effect = [None, HTTPError()]

    mock = Mock()
    mock.url = "http://example.com"
    mock.http_client.get.return_value = response

    text = TextResponseProperty()
    rv = text.provide_value(mock)

    assert rv == "OK"
    response.raise_for_status.assert_called_once_with()
    mock.http_client.get.assert_called_once_with("http://example.com")

    with raises(HTTPError):
        text.provide_value(mock)

########NEW FILE########
__FILENAME__ = test_site
from __future__ import absolute_import, unicode_literals

from pytest import fixture
from mock import Mock

from brownant import Site


@fixture
def sites():
    _sites = {
        "s1": Site("s1"),
        "s2": Site("s2"),
        "s3": Site("s3"),
    }
    return _sites


def test_new_site(sites):
    assert sites["s1"].name == "s1"
    assert sites["s2"].name == "s2"
    assert sites["s3"].name == "s3"

    assert sites["s1"].actions == []
    assert sites["s2"].actions == []
    assert sites["s3"].actions == []


def test_record_and_play_actions(sites):
    site = sites["s1"]

    mock = Mock()
    site.record_action("method_a", 10, "s", is_it=True)
    site.play_actions(target=mock)
    mock.method_a.assert_called_once_with(10, "s", is_it=True)


def test_route(sites):
    site = sites["s1"]

    @site.route("m.example.com", "/article/<int:article_id>")
    def handler(request, article_id):
        pass

    mock = Mock()
    site.play_actions(target=mock)
    mock.add_url_rule.assert_called_once_with(
        "m.example.com",
        "/article/<int:article_id>",
        __name__ + ":handler"
    )

########NEW FILE########
__FILENAME__ = test_utils
from pytest import raises

from brownant.utils import to_bytes_safe


UNICODE_STRING_SAMPLE = u"\u5b89\u5168 SAFE"
BYTES_SEQUENCE_SAMPLE = b"\xe5\xae\x89\xe5\x85\xa8 SAFE"


def test_to_bytes_safe():
    assert to_bytes_safe(UNICODE_STRING_SAMPLE) == BYTES_SEQUENCE_SAMPLE
    assert to_bytes_safe(BYTES_SEQUENCE_SAMPLE) == BYTES_SEQUENCE_SAMPLE
    assert to_bytes_safe(u"ABC") == b"ABC"
    assert to_bytes_safe(b"ABC") == b"ABC"

    assert type(to_bytes_safe(UNICODE_STRING_SAMPLE)) is bytes
    assert type(to_bytes_safe(BYTES_SEQUENCE_SAMPLE)) is bytes
    assert type(to_bytes_safe(u"ABC")) is bytes
    assert type(to_bytes_safe(b"ABC")) is bytes

    with raises(TypeError):
        to_bytes_safe(42)

########NEW FILE########
