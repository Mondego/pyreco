__FILENAME__ = config
from __future__ import unicode_literals
from datetime import datetime

import simplejson as json
from iso8601 import iso8601
import wac

from balanced import exc
from . import __version__


API_ROOT = 'https://api.balancedpayments.com'


# config
def configure(
        user=None,
        root_url=API_ROOT,
        api_revision='1.1',
        user_agent='balanced-python/' + __version__,
        accept_type='application/vnd.api+json',
        **kwargs
):
    kwargs.setdefault('headers', {})

    for key, value in (
        ('content-type', 'application/json;revision=' + api_revision),
        ('accept', '{0};revision={1}'.format(accept_type, api_revision))
    ):
        kwargs['headers'].setdefault(key, value)

    if 'error_cls' not in kwargs:
        kwargs['error_cls'] = exc.convert_error

    if user:
        kwargs['auth'] = (user, None)

    # apply
    Client.config = Config(root_url, user_agent=user_agent, **kwargs)


class Config(wac.Config):

    api_revision = None

    user_agent = None


default_config = Config(API_ROOT)


# client

class Client(wac.Client):

    config = default_config

    @staticmethod
    def _default_serialize(o):
        if isinstance(o, datetime):
            return o.isoformat() + 'Z'
        raise TypeError(
            'Object of type {} with value of {} is not '
            'JSON serializable'.format(type(o), repr(o))
        )

    def _serialize(self, data):
        data = json.dumps(data, default=self._default_serialize)
        return 'application/json', data

    @staticmethod
    def _parse_deserialized(e):
        if isinstance(e, dict):
            for k in e.iterkeys():
                if k.endswith('_at') and isinstance(e[k], basestring):
                    e[k] = iso8601.parse_date(e[k])
        return e

    def _deserialize(self, response):
        if response.headers['Content-Type'] != 'application/json':
            raise Exception("Unsupported content-type '{}'".format(
                response.headers['Content-Type']
            ))
        if not response.content:
            return None
        data = json.loads(response.content)
        return self._parse_deserialized(data)


configure()

client = Client()

########NEW FILE########
__FILENAME__ = exc
from __future__ import unicode_literals

import httplib

import wac


class BalancedError(Exception):

    def __str__(self):
        attrs = ', '.join([
            '{0}={1}'.format(k, repr(v))
            for k, v in self.__dict__.iteritems()
        ])
        return '{0}({1})'.format(self.__class__.__name__, attrs)


class ResourceError(BalancedError):
    pass


class NoResultFound(BalancedError):
    pass


class MultipleResultsFound(BalancedError):
    pass


class FundingSourceNotCreditable(Exception):
    pass


def convert_error(ex):
    if not hasattr(ex.response, 'data'):
        return ex
    return HTTPError.from_response(**ex.response.data)(ex)


class HTTPError(BalancedError, wac.Error):

    class __metaclass__(type):

        def __new__(meta_cls, name, bases, dikt):
            cls = type.__new__(meta_cls, name, bases, dikt)
            cls.types = [
                getattr(cls, k)
                for k in dir(cls)
                if k.isupper() and isinstance(getattr(cls, k), basestring)
            ]
            cls.type_to_error.update(zip(cls.types, [cls] * len(cls.types)))
            return cls

    def __init__(self, requests_ex):
        super(wac.Error, self).__init__(requests_ex)
        self.status_code = requests_ex.response.status_code
        data = getattr(requests_ex.response, 'data', {})
        for k, v in data.get('errors', [{}])[0].iteritems():
            setattr(self, k, v)

    @classmethod
    def format_message(cls, requests_ex):
        data = getattr(requests_ex.response, 'data', {})
        status = httplib.responses[requests_ex.response.status_code]
        error = data['errors'][0]
        status = error.pop('status', status)
        status_code = error.pop('status_code',
                                requests_ex.response.status_code)
        desc = error.pop('description', None)
        message = ': '.join(str(v) for v in [status, status_code, desc] if v)
        return message

    @classmethod
    def from_response(cls, **data):
        try:
            err = data['errors'][0]
            exc = cls.type_to_error.get(err['category_code'], HTTPError)
        except:
            exc = HTTPError
        return exc

    type_to_error = {}


class FundingInstrumentVerificationFailure(HTTPError):
    pass


class BankAccountVerificationFailure(FundingInstrumentVerificationFailure):
    AUTH_NOT_PENDING = 'bank-account-authentication-not-pending'
    AUTH_FAILED = 'bank-account-authentication-failed'
    AUTH_DUPLICATED = 'bank-account-authentication-already-exists'

########NEW FILE########
__FILENAME__ = resources
from __future__ import unicode_literals

import uritemplate
import wac

from balanced import exc, config, utils


registry = wac.ResourceRegistry(route_prefix='/')


class JSONSchemaCollection(wac.ResourceCollection):

    @property
    def href(self):
        return self.uri


class ObjectifyMixin(wac._ObjectifyMixin):

    def _objectify(self, resource_cls, **fields):
        # setting values locally, not from server
        if 'links' not in fields:
            for key, value in fields.iteritems():
                setattr(self, key, value)
        else:
            self._construct_from_response(**fields)

    def _construct_from_response(self, **payload):
        payload = self._hydrate(payload)
        meta = payload.pop('meta', None)

        if isinstance(self, wac.Page):
            for key, value in meta.iteritems():
                setattr(self, key, value)

        # the remaining keys here are just hypermedia resources
        for _type, resources in payload.iteritems():
            # Singular resources are represented as JSON objects. However,
            # they are still wrapped inside an array:
            cls = Resource.registry[_type]

            for resource_body in resources:
                # if we couldn't determine the type of this object we use a
                # generic resource object, target that instead.
                if isinstance(self, (cls, Resource)):
                    # we are loading onto our self, self is the target
                    target = self
                else:
                    target = cls()
                for key, value in resource_body.iteritems():
                    if key in ('links',):
                        continue
                    setattr(target, key, value)

                # if loading into a collection
                if target != self:
                    # ensure that we have a collection to hold this item
                    if not hasattr(self, _type):
                        setattr(self, _type, [])
                    getattr(self, _type).append(target)

    @classmethod
    def _hydrate(cls, payload):
        """
        Construct links for objects
        """
        links = payload.pop('links', {})
        for key, uri in links.iteritems():
            variables = uritemplate.variables(uri)
            # marketplaces.card_holds
            collection, resource_type = key.split('.')
            item_attribute = item_property = resource_type
            # if parsed from uri then retrieve. e.g. customer.id
            for item in payload[collection]:
                # find type, fallback to Resource if we can't determine the
                # type e.g. marketplace.owner_customer
                collection_type = Resource.registry.get(resource_type,
                                                        Resource)

                def extract_variables_from_item(item, variables):
                    for v in variables:
                        _, item_attribute = v.split('.')
                        # HACK: https://github.com/PoundPay/balanced/issues/184
                        if item_attribute == 'self':
                            item_attribute = 'id'
                        item_value = item['links'].get(
                            item_attribute, item.get(item_attribute)
                        )
                        if item_value:
                            yield v, item_value

                item_variables = dict(
                    extract_variables_from_item(item, variables))

                # expand variables if we have them, else this is a link like
                # /debits
                if item_variables:
                    parsed_link = uritemplate.expand(uri, item_variables)
                else:
                    parsed_link = uri

                # check if this is a collection or a singular item
                if any(
                        parsed_link.endswith(value)
                        for value in item_variables.itervalues()
                ):
                    # singular
                    if not item_property.endswith('_href'):
                        item_property += '_href'
                    lazy_href = parsed_link

                elif '{' in parsed_link and '}' in parsed_link:
                    # the link is of the form /asdf/{asdf} which means
                    # that the variables could not be resolved as it
                    # was None.  Instead of making it into a page object
                    # we explicitly set it to None to represent the
                    # attribute is None
                    lazy_href = None
                else:
                    # collection
                    lazy_href = JSONSchemaCollection(
                        collection_type, parsed_link)
                item.setdefault(item_property, lazy_href)
        return payload


class JSONSchemaPage(wac.Page, ObjectifyMixin):

    @property
    def items(self):
        try:
            try:
                return getattr(self, self.resource_cls.type)
            except AttributeError:
                # horrid hack because event callbacks are misnamed.
                return self.event_callbacks
        except AttributeError:
            # Notice:
            # there is no resources key in the response from server
            # if the list is empty, so when we try to get something like
            # `debits`, an AttributeError will be raised. Not sure is this
            # behavior a bug of server, but anyway, this is just a workaround
            # here for solving the problem. The issue was posted here
            # https://github.com/balanced/balanced-python/issues/93
            return []


class JSONSchemaResource(wac.Resource, ObjectifyMixin):

    collection_cls = JSONSchemaCollection

    page_cls = JSONSchemaPage

    def save(self):
        cls = type(self)
        attrs = self.__dict__.copy()
        href = attrs.pop('href', None)

        if not href:
            if not cls.uri_gen or not cls.uri_gen.root_uri:
                raise TypeError(
                    'Unable to create {0} resources directly'.format(
                        cls.__name__
                    )
                )
            href = cls.uri_gen.root_uri

        method = cls.client.put if 'id' in attrs else cls.client.post

        attrs = dict(
            (k, v.href if isinstance(v, Resource) else v)
            for k, v in attrs.iteritems()
            if not isinstance(v, (cls.collection_cls))
        )

        resp = method(href, data=attrs)

        instance = self.__class__(**resp.data)
        self.__dict__.clear()
        self.__dict__.update(instance.__dict__)

        return self

    def delete(self):
        self.client.delete(self.href)

    def __dir__(self):
        return self.__dict__.keys()

    def __getattr__(self, item):
        if isinstance(item, basestring):
            suffix = '_href'
            if suffix not in item:
                href = getattr(self, item + suffix, None)
                if href:
                    item_type = Resource.registry.get(item + 's', Resource)
                    setattr(self, item, item_type.get(href))
                    return getattr(self, item)
        raise AttributeError(
            "'{0}' has no attribute '{1}'".format(
                self.__class__.__name__, item
            )
        )


class Resource(JSONSchemaResource):

    client = config.client

    registry = registry

    uri_gen = wac.URIGen('/resources', '{resource}')

    def unstore(self):
        return self.delete()

    @classmethod
    def fetch(cls, href):
        return cls.get(href)

    @classmethod
    def get(cls, href):
        if href.startswith('/resources'):
            # hackety hack hax
            # resource is an abstract type, we shouldn't have it comeing back itself
            # instead we need to figure out the type based off the api response
            resp = cls.client.get(href)
            resource = [
                k for k in resp.data.keys() if k != 'links' and k != 'meta'
            ]
            if resource:
                return Resource.registry.get(resource[0], cls)(**resp.data)
            return cls(**resp.data)
        return super(Resource, cls).get(href)


class Marketplace(Resource):
    """
    A Marketplace represents your central broker for all operations on the
    Balanced API.

    A Marketplace has a single `owner_customer` which represents your person or
    business.

    All Resources apart from APIKeys are associated with a Marketplace.

    A Marketplace has an escrow account which receives all funds from Debits
    that are not associated with Orders. The sum of the escrow (`in_escrow`) is
    (Debits - Refunds + Reversals - Credits).
    """

    type = 'marketplaces'

    uri_gen = wac.URIGen('/marketplaces', '{marketplace}')

    @utils.classproperty
    def mine(cls):
        """
        Returns an instance representing the marketplace associated with the
        current API key used for this request.
        """
        return cls.query.one()

    my_marketplace = mine


class APIKey(Resource):
    """
    Your APIKey is used to authenticate when performing operations on the
    Balanced API. You must create an APIKey before you create a Marketplace.

    **NOTE:** Never give out or expose your APIKey. You may POST to this
    endpoint to create new APIKeys and then DELETE any old keys.
    """
    type = 'api_keys'

    uri_gen = wac.URIGen('/api_keys', '{api_key}')


class CardHold(Resource):

    type = 'card_holds'

    uri_gen = wac.URIGen('/card_holds', '{card_hold}')

    def cancel(self):
        self.is_void = False
        return self.save()

    def capture(self, **kwargs):
        return Debit(
            href=self.debits.href,
            **kwargs
        ).save()


class Transaction(Resource):
    """
    Any transfer, funds from or to, your Marketplace's escrow account or the
    escrow account of an Order associated with your Marketplace.
    E.g. a Credit, Debit, Refund, or Reversal.

    If the Transaction is associated with an Order then it will be applied to
    the Order's escrow account, not to the Marketplace's escrow account.
    """

    type = 'transactions'


class Credit(Transaction):
    """
    A Credit represents a transfer of funds from your Marketplace's
    escrow account to a FundingInstrument.

    Credits are created by calling the `credit` method on a FundingInstrument.
    """

    type = 'credits'

    uri_gen = wac.URIGen('/credits', '{credit}')

    def reverse(self, **kwargs):
        """
        Reverse a Credit.  If no amount is specified it will reverse the entire
        amount of the Credit, you may create many Reversals up to the sum of
        the total amount of the original Credit.

        :rtype: Reversal
        """
        return Reversal(
            href=self.reversals.href,
            **kwargs
        ).save()


class Debit(Transaction):
    """
    A Debit represents a transfer of funds from a FundingInstrument to your
    Marketplace's escrow account.

    A Debit may be created directly, or it will be created as a side-effect
    of capturing a CardHold. If you create a Debit directly it will implicitly
    create the associated CardHold if the FundingInstrument supports this.
    """

    type = 'debits'

    uri_gen = wac.URIGen('/debits', '{debit}')

    def refund(self, **kwargs):
        """
        Refunds this Debit. If no amount is specified it will refund the entire
        amount of the Debit, you may create many Refunds up to the sum total
        of the original Debit's amount.

        :rtype: Refund
        """
        return Refund(
            href=self.refunds.href,
            **kwargs
        ).save()


class Refund(Transaction):
    """
    A Refund represents a reversal of funds from a Debit. A Debit can have
    many Refunds associated with it up to the total amount of the original
    Debit. Funds are returned to your Marketplace's escrow account
    proportional to the amount of the Refund.
    """

    type = 'refunds'

    uri_gen = wac.URIGen('/refunds', '{refund}')


class Reversal(Transaction):
    """
    A Reversal represents a reversal of funds from a Credit. A Credit can have
    many Reversal associated with it up to the total amount of the original
    Credit. Funds are returned to your Marketplace's escrow account
    proportional to the amount of the Reversal.
    """

    type = 'reversals'

    uri_gen = wac.URIGen('/reversals', '{reversal}')


class FundingInstrument(Resource):
    """
    A FundingInstrument is either (or both) a source or destination of funds.
    You may perform `debit` or `credit` operations on a FundingInstrument to
    transfer funds to or from your Marketplace's escrow.
    """

    type = 'funding_instruments'

    def associate_to_customer(self, customer):
        try:
            self.links
        except AttributeError:
            self.links = {}
        self.links['customer'] = utils.extract_href_from_object(customer)
        self.save()

    def debit(self, amount, **kwargs):
        """
        Creates a Debit of funds from this FundingInstrument to your
        Marketplace's escrow account.

        :param appears_on_statement_as: If None then Balanced will use the
            `domain_name` property from your Marketplace.
        :rtype: Debit
        """
        return Debit(
            href=self.debits.href,
            amount=amount,
            **kwargs
        ).save()

    def credit(self, amount, **kwargs):
        """
        Creates a Credit of funds from your Marketplace's escrow account to
        this FundingInstrument.

        :rtype: Credit
        """
 
        if not hasattr(self, 'credits'):
            raise exc.FundingSourceNotCreditable()
        return Credit(
            href=self.credits.href,
            amount=amount,
            **kwargs
        ).save()


class BankAccount(FundingInstrument):
    """
    A BankAccount is both a source, and a destination of, funds. You may
    create Debits and Credits to and from, this funding instrument.
    """

    type = 'bank_accounts'

    uri_gen = wac.URIGen('/bank_accounts', '{bank_account}')

    def verify(self):
        """
        Creates a verification of the associated BankAccount so it can
        perform verified operations (debits).

        :rtype: BankAccountVerification
        """
        return BankAccountVerification(
            href=self.bank_account_verifications.href
        ).save()


class BankAccountVerification(Resource):
    """
    Represents an attempt to verify the associated BankAccount so it can
    perform verified operations (debits).
    """

    type = 'bank_account_verifications'

    def confirm(self, amount_1, amount_2):
        self.amount_1 = amount_1
        self.amount_2 = amount_2
        return self.save()


class Card(FundingInstrument):
    """
    A card represents a source of funds. You may Debit funds from the Card.
    """

    type = 'cards'

    uri_gen = wac.URIGen('/cards', '{card}')

    def hold(self, amount, **kwargs):
        return CardHold(
            href=self.card_holds.href,
            amount=amount,
            **kwargs
        ).save()


class Customer(Resource):
    """
    A Customer represents a business or person within your Marketplace. A
    Customer can have many funding instruments such as cards and bank accounts
    associated to them. Customers are logical grouping constructs for
    associating many Transactions and FundingInstruments.
    """

    type = 'customers'

    uri_gen = wac.URIGen('/customers', '{customer}')

    def create_order(self, **kwargs):
        return Order(href=self.orders.href, **kwargs).save()


class Order(Resource):
    """
    An Order is a logical construct for grouping Transactions.

    An Order may have 0:n Transactions associated with it so long as the sum
    (`amount_escrowed`) which is calculated as
    (Debits - Refunds - Credits + Reversals), is always >= 0.
    """

    type = 'orders'

    uri_gen = wac.URIGen('/orders', '{order}')

    def credit_to(self, destination, amount, **kwargs):
        return destination.credit(order=self.href,
                                  amount=amount,
                                  **kwargs)

    def debit_from(self, source, amount, **kwargs):
        return source.debit(order=self.href,
                            amount=amount,
                            **kwargs)


class Callback(Resource):
    """
    A Callback is a publicly accessible location that can receive POSTed JSON
    data whenever an Event is generated.
    """

    type = 'callbacks'

    uri_gen = wac.URIGen('/callbacks', '{callback}')


class Dispute(Resource):
    """
    A dispute occurs when a customer disputes a transaction that
    occurred on their funding instrument.
    """
    type = 'disputes'

    uri_gen = wac.URIGen('/disputes', '{dispute}')


class Event(Resource):
    """
    An Event is a snapshot of another resource at a point in time when
    something significant occurred. Events are created when resources are
    created, updated, deleted or otherwise change state such as a Credit being
    marked as failed.
    """

    type = 'events'

    uri_gen = wac.URIGen('/events', '{event}')


class EventCallback(Resource):
    """
    Represents a single event being sent to a callback.
    """

    type = 'event_callbacks'


class EventCallbackLog(Resource):
    """
    Represents a request and response from single attempt to notify a callback
    of an event.
    """

    type = 'event_callback_logs'


class ExternalAccount(FundingInstrument):
    """
    An External Account represents a source of funds provided by an external, 3rd
    party processor. You may Debit funds from the account if can_debit is true.
    """

    type = 'external_accounts'

    uri_gen = wac.URIGen('/external_accounts', '{external_account}')

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals


class ClassPropertyDescriptor(object):

    def __init__(self, fget, fset=None):
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        return self.fget.__get__(obj, klass)()

    def __set__(self, obj, value):
        if not self.fset:
            raise AttributeError("can't set attribute")
        type_ = type(obj)
        return self.fset.__get__(obj, type_)(value)

    def setter(self, func):
        if not isinstance(func, (classmethod, staticmethod)):
            func = classmethod(func)
        self.fset = func
        return self


def classproperty(func):
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)

    return ClassPropertyDescriptor(func)


def extract_href_from_object(obj):
    if isinstance(obj, basestring):
        return obj
    if isinstance(obj, dict):
        return obj['href']
    return obj.href

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# balanced documentation build configuration file, created by
# sphinx-quickstart on Wed Jun 20 15:15:54 2012.
#
# This file is execfile()d with the current directory set to its containing
# dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.


import sys
import os

sys.path.append(os.path.abspath('../../balanced'))
sys.path.append(os.path.abspath('../../'))


# -- General configuration ----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.ifconfig']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'balanced'
copyright = u'2012, Balanced'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1'
# The full version, including alpha/beta/rc tags.
release = '0.8.9'

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
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all
# documents.
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


# -- Options for HTML output --------------------------------------------------

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
htmlhelp_basename = 'balanceddoc'


# -- Options for LaTeX output -------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author,
# documentclass [howto/manual]).
latex_documents = [
  ('index', 'balanced.tex', u'balanced Documentation',
   u'Balanced', 'manual'),
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


# -- Options for manual page output -------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'balanced', u'balanced Documentation',
     [u'Balanced'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'balanced', u'balanced Documentation',
   u'Balanced', 'balanced', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = accounting
#!/usr/bin/env python
'''
Generate a csv report of month end transaction balances;
please ensure your RAM is commensurate with your transaction volume.

python examples/accounting.py --api_key [Marketplace API Key] > Report.csv
python examples/accounting.py --api_key [Marketplace API Key] --use_cache > gnuplot ...

'''

import argparse
import calendar
import csv
from itertools import groupby
import os
import pickle
import sys

import balanced


def generate_report(args):
    balanced.configure(args.api_key)
    marketplace = balanced.Marketplace.mine

    if args.use_cache:
        credits = pickle.load(open('cache/credits.obj'))
        debits = pickle.load(open('cache/debits.obj'))
        refunds = pickle.load(open('cache/refunds.obj'))

    else:
        if not os.path.exists('./cache'):
            os.makedirs('./cache')

        print 'Downloading Debits'
        debits = balanced.Debit.query.all()

        print 'Downloading Credits'
        credits = balanced.Credit.query.all()

        print 'Downloading Refunds'
        refunds = balanced.Refund.query.all()

        print 'Caching Transactions'
        with open('cache/debits.obj', 'w') as f:
            pickle.dump(debits, f)

        with open('cache/credits.obj', 'w') as f:
            pickle.dump(credits, f)

        with open('cache/refunds.obj', 'w') as f:
            pickle.dump(refunds, f)

    txns = sorted(credits + debits + refunds, key=lambda x: x.created_at)

    def group(xs, head, tail):
        return {key: [tail(x) for x in group]
                for key, group in
                groupby(sorted(xs, key=head),
                        head)}

    # (year, month, txn)
    txns_by_period = [(t.created_at.year,
                       t.created_at.month,
                       t) for t in txns]

    # {year: [(month, txn)]}
    txns_by_year = group(txns_by_period,
                         lambda (y, m, txn): y,
                         lambda (y, m, txn): (m, txn))

    group_by_month = lambda xs: group(xs, lambda (a, b): a, lambda (a, b): b)

    # {year: {month: [txn]}}
    txns_by_year_by_month = {key: group_by_month(txns_by_year[key])
                             for key in txns_by_year}

    headers = ['Year', 'Month', 'Debits', 'Refunds', 'Credits',
               'Credits Pending', 'Escrow Balance']
    writer = csv.DictWriter(sys.stdout, headers)
    writer.writeheader()
    rolling_balance = 0

    for year in sorted(txns_by_year_by_month):
        for month in sorted(txns_by_year_by_month[year]):
            txns = txns_by_year_by_month[year][month]
            monthly_credits = [txn for txn in txns
                               if type(txn) == balanced.resources.Credit]
            monthly_debits = [txn for txn in txns
                              if type(txn) == balanced.resources.Debit]
            monthly_refunds = [txn for txn in txns
                               if type(txn) == balanced.resources.Refund]

            credit_amount = sum([c.amount for c in monthly_credits
                                 if c.status == 'paid'])
            debit_amount = sum([d.amount for d in monthly_debits
                                if d.status == 'succeeded'])
            refund_amount = sum([r.amount for r in monthly_refunds])
            credits_pending_amount = sum([c.amount for c in monthly_credits
                                          if c.status == 'pending'])

            rolling_balance += debit_amount
            rolling_balance -= (refund_amount + credit_amount)

            row = {}
            row['Year'] = str(year)
            row['Month'] = calendar.month_name[month]
            row['Debits'] = debit_amount / 100.0
            row['Refunds'] = refund_amount / 100.0
            row['Credits'] = credit_amount / 100.0
            row['Credits Pending'] = credits_pending_amount / 100.0
            row['Escrow Balance'] = (rolling_balance -
                                     credits_pending_amount) / 100.0
            writer.writerow(row)

def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--api_key', action='store', dest='api_key',
                            required=True)
    arg_parser.add_argument('--use_cache', action='store_true')
    args = arg_parser.parse_args()
    generate_report(args)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = bank_account_debits
'''
Learn how to verify a bank account so you can debit with it.
'''
from __future__ import unicode_literals

import balanced


def init():
    key = balanced.APIKey().save()
    balanced.configure(key.secret)
    balanced.Marketplace().save()


def main():
    init()

    # create a bank account
    bank_account = balanced.BankAccount(
        account_number='1234567890',
        routing_number='321174851',
        name='Jack Q Merchant',
    ).save()
    customer = balanced.Customer().save()
    bank_account.associate_to_customer(customer)

    print 'you can\'t debit until you authenticate'
    try:
        bank_account.debit(100)
    except balanced.exc.HTTPError as ex:
        print 'Debit failed, %s' % ex.message

    # verify
    verification = bank_account.verify()

    print 'PROTIP: for TEST bank accounts the valid amount is always 1 and 1'
    try:
        verification.confirm(amount_1=1, amount_2=2)
    except balanced.exc.BankAccountVerificationFailure as ex:
        print 'Authentication error , %s' % ex.message

    # reload
    verification = balanced.BankAccount.fetch(
        bank_account.href
    ).bank_account_verification

    if verification.confirm(1, 1).verification_status != 'succeeded':
        raise Exception('unpossible')
    debit = bank_account.debit(100)

    print 'debited the bank account %s for %d cents' % (
        debit.source.href,
        debit.amount
    )
    print 'and there you have it'


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = events_and_callbacks
"""
Welcome weary traveller. Sick of polling for state changes? Well today have I
got good news for you. Run this example below to see how to get yourself some
callback goodness and to understand how events work.
"""
from __future__ import unicode_literals
import time

import balanced

from helpers import RequestBinClient


def init():
    key = balanced.APIKey().save()
    balanced.configure(key.secret)
    balanced.Marketplace().save()


def main():
    init()
    request_bin = RequestBinClient()

    print 'let\'s create a callback'
    balanced.Callback(
        url=request_bin.callback_url,
    ).save()

    print 'let\'s create a card and associate it with a new account'
    card = balanced.Card(
        expiration_month='12',
        csc='123',
        number='5105105105105100',
        expiration_year='2020',
    ).save()

    print 'generate a debit (which implicitly creates and captures a hold)'
    card.debit(100)

    print 'event creation is an async operation, let\'s wait until we have ' \
          'some events!'
    while not balanced.Event.query.count():
        print 'Zzzz'
        time.sleep(0)

    print 'Woop, we got some events, let us see what there is to look at'
    for event in balanced.Event.query:
        print 'this was a {0} event, it occurred at {1}, the callback has a ' \
              'status of {2}'.format(
            event.type,
            event.occurred_at,
            event.callback_statuses
        )

    print 'you can inspect each event to see the logs'
    event = balanced.Event.query.first()
    for callback in event.callbacks:
        print 'inspecting callback to {0} for event {1}'.format(
            callback.url,
            event.type,
        )
        for log in callback.logs:
            print 'this attempt to the callback has a status "{0}"'.format(
                log.status
            )

    print 'ok, let\'s check with requestb.in to see if our callbacks fired'
    print 'we received {0} callbacks, you can view them at {1}'.format(
        len(request_bin.get_requests()),
        request_bin.view_url,
    )


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = examples
from __future__ import unicode_literals

import balanced


print "create our new api key"
api_key = balanced.APIKey().save()
print "Our secret is: ", api_key.secret

print "configure with our secret " + api_key.secret
balanced.configure(api_key.secret)

print "create our marketplace"
marketplace = balanced.Marketplace().save()

# what's my marketplace?
if not balanced.Marketplace.my_marketplace:
    raise Exception("Marketplace.my_marketplace should not be nil")
print "what's my marketplace?, easy: Marketplace.my_marketplace: {0}".format(
    balanced.Marketplace.my_marketplace
)

print "My marketplace's name is: {0}".format(marketplace.name)
print "Changing it to TestFooey"
marketplace.name = "TestFooey"
marketplace.save()
print "My marketplace name is now: {0}".format(marketplace.name)
if marketplace.name != 'TestFooey':
    raise Exception("Marketplace name is NOT TestFooey!")

print "cool! let's create a new card."
card = balanced.Card(
    number="5105105105105100",
    expiration_month="12",
    expiration_year="2015",
).save()

print "Our card href: " + card.href

print "create our **buyer** account"
buyer = balanced.Customer(email="buyer@example.org", source=card).save()
print "our buyer account: " + buyer.href

print "hold some amount of funds on the buyer, lets say 15$"
the_hold = card.hold(1500)

print "ok, no more holds! lets just capture it (for the full amount)"
debit = the_hold.capture()

print "hmm, how much money do i have in escrow? should equal the debit amount"
marketplace = balanced.Marketplace.my_marketplace
if marketplace.in_escrow != 1500:
    raise Exception("1500 is not in escrow! this is wrong")
print "i have {0} in escrow!".format(marketplace.in_escrow)

print "cool. now let me refund the full amount"
refund = debit.refund()  # the full amount!

print ("ok, we have a merchant that's signing up, let's create an account for "
       "them first, lets create their bank account.")

bank_account = balanced.BankAccount(
    account_number="1234567890",
    routing_number="321174851",
    name="Jack Q Merchant",
).save()

merchant = balanced.Customer(
    email_address="merchant@example.org",
    name="Billy Jones",
    address={
        'street_address': "801 High St.",
        'postal_code': "94301",
        'country': "USA",
    },
    dob="1842-01",
    phone_number="+16505551234",
    destination=bank_account,
).save()

print "oh our buyer is interested in buying something for 130.00$"
another_debit = card.debit(13000, appears_on_statement_as="MARKETPLACE.COM")

print "lets credit our merchant 110.00$"
credit = bank_account.credit(
    11000, description="Buyer purchased something on MARKETPLACE.COM")

print "lets assume the marketplace charges 15%, so it earned $20"
mp_credit = marketplace.owner_customer.bank_accounts.first().credit(
    2000, description="Our commission from MARKETPLACE.COM")

print "ok lets invalid a card"
card.delete()

assert buyer.cards.count() == 0

print "invalidating a bank account"
bank_account.delete()

print "associate a card with an exiting customer"
card = balanced.Card(
    number="5105105105105100",
    expiration_month="12",
    expiration_year="2015",
).save()

card.associate_to_customer(buyer)

assert buyer.cards.count() == 1

print "and there you have it :)"

########NEW FILE########
__FILENAME__ = orders
from __future__ import unicode_literals

import balanced


key = balanced.APIKey().save()
balanced.configure(key.secret)
balanced.Marketplace().save()

# here's the merchant customer who is going to be the recipient of the order
merchant = balanced.Customer().save()
bank_account = balanced.BankAccount(
    account_number="1234567890",
    routing_number="321174851",
    name="Jack Q Merchant",
).save()
bank_account.associate_to_customer(merchant)

order = merchant.create_order(description='foo order')

card = balanced.Card(
    number="5105105105105100",
    expiration_month="12",
    expiration_year="2015",
).save()

# debit the card and associate with the order.
card.debit(amount=100, order=order)

order = balanced.Order.fetch(order.href)

# the order captured the amount of the debit
assert order.amount_escrowed == 100

# pay out half
credit = bank_account.credit(amount=50, order=order)

order = balanced.Order.fetch(order.href)

# half the money remains
assert order.amount_escrowed == 50

# let's try paying out to another funding instrument that is not the recipient
# of the order.
another_bank_account = balanced.BankAccount(
    account_number="1234567890",
    routing_number="321174851",
    name="Jack Q Merchant",
).save()

another_merchant = balanced.Customer().save()
another_bank_account.associate_to_customer(another_merchant)

# cannot credit to a bank account which is not assigned to either the
# marketplace or the merchant associated with the order.
try:
    another_credit = another_bank_account.credit(amount=50, order=order)
except balanced.exc.BalancedError as ex:
    print ex

assert ex is not None

########NEW FILE########
__FILENAME__ = render_scenarios
import glob2
import os
import json
import balanced
import pprint
import requests
import sys

from pprint import PrettyPrinter
from mako.template import Template
from mako.lookup import TemplateLookup

class colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

SCENARIO_CACHE_URL = 'https://raw.githubusercontent.com/balanced/balanced-docs/master/scenario.cache'

def construct_response(scenario_name):
    # load up response data
    data = json.load(open('scenario.cache','r'))
    lookup = TemplateLookup(directories=['./scenarios'])

    for path in glob2.glob('./scenarios/**/request.mako'):
        if path != scenario_name:
            continue
        event_name = path.split('/')[-2]
        template = Template("${response}")
        try:
            response = data[event_name].get('response', {})
            text = template.render(response=response).strip()
            response =  json.loads(text)
            del response["links"]
            for key, value in response.items():
                response = value[0]
                type = key
                resource = balanced.Resource()
                object_type = resource.registry[type]
                object_instance = object_type()
                for key, value in response.items():
                   setattr(object_instance, key, value)
            text = template.render(response=object_instance)
        except KeyError:
            text = ''
    return text

def render_executables():
    # load up scenario data
    data = json.load(open('scenario.cache','r'))
    lookup = TemplateLookup(directories=['./scenarios'])

    for path in glob2.glob('./scenarios/**/request.mako'):
        event_name = path.split('/')[-2]
        template = Template(filename=path, lookup=lookup,)
        try:
            request = data[event_name].get('request', {})
            payload = request.get('payload')
            text = template.render(api_key=data['api_key'],
                                   request=request, payload=payload).strip()
        except KeyError:
            text = ''
            print colors.YELLOW + "WARN: Skipped {} since {} not in scenario.cache".format(
                path, event_name) + colors.RESET
        with open(os.path.join(os.path.dirname(path),
                               'executable.py'), 'w+') as write_to:
            write_to.write(text)

def render_mako():
    for path in glob2.glob('./scenarios/**/request.mako'):
        dir = os.path.dirname(path)
        with open(os.path.join(dir, 'python.mako'), 'w+b') as wfile:
            definition = open(os.path.join(dir, 'definition.mako'),'r').read()
            request = open(os.path.join(dir, 'executable.py'),'r').read()
            response = construct_response(path)
            body = "% if mode == 'definition':\n{}".format(definition) + "\n" \
                   "% elif mode == 'request':\n" + request + "\n" \
                    "% elif mode == 'response':\n" + response + "\n% endif"
            wfile.write(body)

def fetch_scenario_cache():
    try:
        os.remove('scenario.cache')
    except OSError:
        pass

    with open('scenario.cache', 'wb') as fo:
        response = requests.get(SCENARIO_CACHE_URL)
        if not response.ok:
            sys.exit()
        for block in response.iter_content():
            fo.write(block)

if __name__ == "__main__":
    print colors.GREEN + "Obtaining scenario cache..." + colors.RESET
    fetch_scenario_cache()
    print colors.GREEN + "Making Executables..." + colors.RESET
    render_executables()
    print colors.GREEN + "Rendering new mako files..." + colors.RESET
    render_mako()


########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

api_key = balanced.APIKey().save()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

key = balanced.APIKey.fetch('/api_keys/AK7gg5FNb0Owb6hErcMm0CZ7')
key.delete()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

keys = balanced.APIKey.query
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

key = balanced.APIKey.fetch('/api_keys/AK7gg5FNb0Owb6hErcMm0CZ7')
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

card = balanced.Card.fetch('/bank_accounts/BA7zu6QXmylsn0o6qVpS8UO9')
card.associate_to_customer('/customers/CU7yCmXG2RxyyIkcHG3SIMUF')
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

bank_account = balanced.BankAccount(
  routing_number='121000358',
  account_type='checking',
  account_number='9900000001',
  name='Johann Bernoulli'
).save()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

bank_account = balanced.BankAccount.fetch('/bank_accounts/BA7zu6QXmylsn0o6qVpS8UO9')
bank_account.credit(
  amount=5000
)
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

bank_account = balanced.BankAccount.fetch('/bank_accounts/BA7lb2roygfhwDfbvikDLcHP')
bank_account.debit(
  appears_on_statement_as='Statement text',
  amount=5000,
  description='Some descriptive text for the debit in the dashboard'
)
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

bank_account = balanced.BankAccount.fetch('/bank_accounts/BA7sojXcP7oSdQyrjUA7wXg9')
bank_account.delete()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

bank_accounts = balanced.BankAccount.query
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

bank_account = balanced.BankAccount.fetch('/bank_accounts/BA7sojXcP7oSdQyrjUA7wXg9')
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

bank_account = balanced.BankAccount.fetch('/bank_accounts/BA7sojXcP7oSdQyrjUA7wXg9')
bank_account.meta = {
  'twitter.id'='1234987650',
  'facebook.user_id'='0192837465',
  'my-own-customer-id'='12345'
}
bank_account.save()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

bank_account = balanced.BankAccount.fetch('/bank_accounts/BA7lb2roygfhwDfbvikDLcHP')
verification = bank_account.verify()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')
verification = balanced.BankAccountVerification.fetch('/verifications/BZ7n38gpwYou03mkP4Vt83Cl')
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

verification = balanced.BankAccountVerification.fetch('/verifications/BZ7n38gpwYou03mkP4Vt83Cl')
verification.confirm(amount_1=1, amount_2=1)
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

callback = balanced.Callback(
  url='http://www.example.com/callback',
  method='post'
).save()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

callback = balanced.Callback.fetch('/callbacks/CB7DP9sW9wRe19dFRutynahb')
callback.unstore()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

callbacks = balanced.Callback.query
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

callback = balanced.Callback.fetch('/callbacks/CB7DP9sW9wRe19dFRutynahb')
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

card = balanced.Card.fetch('/cards/CCf1fF6z2RjwvniinUVefhb')
card.associate_to_customer('/customers/CU7yCmXG2RxyyIkcHG3SIMUF')
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

card = balanced.Card(
  cvv='123',
  expiration_month='12',
  number='5105105105105100',
  expiration_year='2020'
).save()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-2jJSjIixy2qkOMmIONPtXnawOUftBDRSK')

card = balanced.Card(
  expiration_month='05',
  name='Johannes Bach',
  expiration_year='2020',
  number='4342561111111118'
).save()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

card = balanced.Card(
  cvv='123',
  expiration_month='12',
  number='6500000000000002',
  expiration_year='3000'
).save()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-2jJSjIixy2qkOMmIONPtXnawOUftBDRSK')

card = balanced.Card.fetch('/cards/CC7nMc4BAti7DgvWmpGV5e6N')
card.credit(
  amount=5000,
  description='Some descriptive text for the debit in the dashboard'
)
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

card = balanced.Card.fetch('/cards/CCf1fF6z2RjwvniinUVefhb')
card.debit(
  appears_on_statement_as='Statement text',
  amount=5000,
  description='Some descriptive text for the debit in the dashboard'
)
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

card = balanced.Card.fetch('/cards/CCIcOaBZBsK9o6Nbqmuu7B3')
card.debit(
  appears_on_statement_as='Statement text',
  amount=5000,
  description='Some descriptive text for the debit in the dashboard'
)
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

card = balanced.Card.fetch('/cards/CC832pqCbRPor1ewRdxPvnv')
card.unstore()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

card_hold = balanced.CardHold.fetch('/card_holds/HL7K6mNHtWSl33Whc0WDOJ81')
debit = card_hold.capture(
  appears_on_statement_as='ShowsUpOnStmt',
  description='Some descriptive text for the debit in the dashboard'
)
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

card = balanced.Card.fetch('/cards/CC7JlMyXyZ8W3RBfE1SSlnrD')
card_hold = card.hold(
  amount=5000,
  description='Some descriptive text for the debit in the dashboard'
)
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

card_holds = balanced.CardHold.query
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

card_hold = balanced.CardHold.fetch('/card_holds/HL7K6mNHtWSl33Whc0WDOJ81')
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

card_hold = balanced.CardHold.fetch('/card_holds/HL7K6mNHtWSl33Whc0WDOJ81')
card_hold.description = 'update this description'
card_hold.meta = {
  'holding.for': 'user1',
  'meaningful.key': 'some.value',
}
card_hold.save()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

card_hold = balanced.CardHold.fetch('/card_holds/HL4F8FdmMdyVxzE515FygGd')
card_hold.cancel()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

cards = balanced.Card.query
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

card = balanced.Card.fetch('/cards/CC832pqCbRPor1ewRdxPvnv')
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

card = balanced.Card.fetch('/cards/CC832pqCbRPor1ewRdxPvnv')
card.meta = {
  'twitter.id': '1234987650',
  'facebook.user_id': '0192837465',
  'my-own-customer-id': '12345'
}
card.save()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

credits = balanced.Credit.query
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

bank_account = balanced.BankAccount.fetch('/bank_accounts/BA7sojXcP7oSdQyrjUA7wXg9/credits')
credits = bank_account.credits
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

order = balanced.Order.fetch('/orders/OR5QcYnwysJXQswImokq6ZSx')
bank_account = balanced.BankAccount.fetch('/bank_accounts/BA5KLH6jhFgtVENHXOcF3Cfj/credits')
order.credit_to(
    amount=5000,
    destination=bank_account
)
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

credit = balanced.Credit.fetch('/credits/CRjCksasJ36xjkBXRYvlCh7')
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

credit = balanced.Credit.fetch('/credits/CRjCksasJ36xjkBXRYvlCh7')
credit.meta = {
  'twitter.id': '1234987650',
  'facebook.user_id': '0192837465',
  'my-own-customer-id': '12345'
}
credit.save()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

customer = balanced.Customer(
    dob_year=1963,
    dob_month=7,
    name='Henry Ford',
    address={
        'postal_code': '48120'
    }
).save()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

customer = balanced.Customer.fetch('/customers/CUxN95d3eKLokMS6CymVtIB')
customer.unstore()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

customers = balanced.Customer.query
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

customer = balanced.Customer.fetch('/customers/CUrtoxuYO4XmXZi6NzXKBLL')
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

customer = balanced.Debit.fetch('/customers/CUrtoxuYO4XmXZi6NzXKBLL')
customer.email = 'email@newdomain.com'
customer.meta = {
  'shipping-preference': 'ground'
}
customer.save()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

debit = balanced.Debit.fetch('/debits/WDJ66VlXnDyDx5AS5uplxyt')
dispute = debit.dispute
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

debits = balanced.Debit.query
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

order = balanced.Order.fetch('/orders/OR5QcYnwysJXQswImokq6ZSx')
card = balanced.Card.fetch('/cards/CC5OD6648yiKfSzfj6z6MdXr')
order.debit_from(
    amount=5000,
    source=card,
)
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

debit = balanced.Debit.fetch('/debits/WDh5j4t3Rkh7oeONR9Izy61')
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

debit = balanced.Debit.fetch('/debits/WDh5j4t3Rkh7oeONR9Izy61')
debit.description = 'New description for debit'
debit.meta = {
  'facebook.id': '1234567890',
  'anykey': 'valuegoeshere',
}
debit.save()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

disputes = balanced.Dispute.query
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

dispute = balanced.Dispute.fetch('/disputes/DT180PABUUjnj5wdE2pcwXQD')
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

events = balanced.Event.query
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

event = balanced.Event.fetch('/events/EVec6e7ac2ccc411e389ba061e5f402045')
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

merchant_customer = balanced.Customer.fetch('/customers/CUxN95d3eKLokMS6CymVtIB')
merchant_customer.create_order(
  description='Order #12341234'
).save()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

orders = balanced.Order.query
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

order = balanced.Order.fetch('/orders/OR1oqq5PzdHGkB0GBJJiagNT')
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

order = balanced.Order.fetch('/orders/OR1oqq5PzdHGkB0GBJJiagNT')
order.description = 'New description for order'
order.meta = {
  'anykey': 'valuegoeshere',
  'product.id': '1234567890'
}
order.save()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

debit = balanced.Debit.fetch('/debits/WDEg9ofx83CeAhiwI1QmA17')
refund = debit.refund(
    amount=3000,
    description="Refund for Order #1111",
    meta={
        "merchant.feedback": "positive",
        "user.refund_reason": "not happy with product",
        "fulfillment.item.condition": "OK",
    }
)
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

refunds = balanced.Refund.query
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

refund = balanced.Refund.fetch('/refunds/RFFFulVVpBiNWpJ2VLMto1L')
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

refund = balanced.Refund.fetch('/refunds/RFFFulVVpBiNWpJ2VLMto1L')
refund.description = 'update this description'
refund.meta = {
  'user.refund.count': '3',
  'refund.reason': 'user not happy with product',
  'user.notes': 'very polite on the phone',
}
refund.save()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

credit = balanced.Credit.fetch('/credits/CR1ynmPUlJGbV9EMyqkowHJP')
reversal = credit.reverse(
    amount=3000,
    description="Reversal for Order #1111",
    meta={
        "merchant.feedback": "positive",
        "user.refund_reason": "not happy with product",
        "fulfillment.item.condition": "OK",
    }
)
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

reversals = balanced.Reversal.query
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

refund = balanced.Reversal.fetch('/reversals/RV1zj7hidB6KZ7MxLESBXRJD')
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

reversal = balanced.Reversal.fetch('/reversals/RV1zj7hidB6KZ7MxLESBXRJD')
reversal.description = 'update this description'
reversal.meta = {
  'user.refund.count': '3',
  'refund.reason': 'user not happy with product',
  'user.notes': 'very polite on the phone',
}
reversal.save()
########NEW FILE########
__FILENAME__ = executable
import balanced

balanced.configure('ak-test-aUV295IugdhWSNx2JFckYBCSvfY2ibgq')

api_key = balanced.APIKey()
api_key.save()
########NEW FILE########
__FILENAME__ = executable

########NEW FILE########
__FILENAME__ = executable

########NEW FILE########
__FILENAME__ = executable

########NEW FILE########
__FILENAME__ = executable

########NEW FILE########
__FILENAME__ = executable

########NEW FILE########
__FILENAME__ = acceptance_suite
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import date
import inspect
import time

import balanced
import copy
import requests
import unittest2 as unittest

from fixtures import cards, merchants, bank_accounts


class TestCases(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        balanced.config.root_uri = 'http://127.0.0.1:5000/'
        if not balanced.config.api_key_secret:
            api_key = balanced.APIKey().save()
            balanced.configure(api_key.secret)
            cls.api_key = api_key
            cls.merchant = api_key.merchant
            balanced.Marketplace().save()


class AcceptanceUseCases(TestCases):

    def setUp(self):
        self.valid_international_address = {
            'street_address': '24 Grosvenor Square London, Mayfair, London',
            'country_code': 'GBR',
        }
        self.person = {
            'name': 'James Bond',
        }
        self.valid_us_address = {
            'street_address': '1 Large Prime St',
            'city': 'Gaussian',
            'state': 'CA',
            'postal_code': '99971',
        }
        self.us_card_payload = {
            'name': 'Richard Feynman',
            'card_number': cards.TEST_CARDS['visa'][0],
            'expiration_month': 12,
            'expiration_year': date.today().year + 1,
        }
        self.us_card_payload.update(self.valid_us_address)

        self.bank_account_payload = {
            'name': 'Galileo Galilei',
            'account_number': '28304871049',
            'bank_code': '121042882',
        }

    def test_00_merchant_expectations(self):
        mps = balanced.Marketplace.query.all()
        self.assertEqual(len(mps), 1)

    def _create_buyer_account(self):
        mp = balanced.Marketplace.query.one()
        card_payload = dict(self.us_card_payload)
        card = balanced.Card(**card_payload).save()
        card_uri = card.uri
        buyer = mp.create_buyer(
            email_address='albert@einstein.com',
            card_uri=card_uri,
            meta={'foo': 'bar'},
        )
        return buyer

    def _find_buyer_account(self):
        mp = balanced.Marketplace.query.one()
        accounts = list(mp.accounts)
        filtered_accounts = [
            account for account in accounts if account.roles == ['buyer']
        ]
        if not filtered_accounts:
            buyer = self._create_buyer_account()
        else:
            for account in filtered_accounts:
                # this account will fail any debit, so don't use it
                if account.email_address == 'stephen@hawking.com':
                    continue
                buyer = account
        return buyer

    def test_merchant_expectations(self):
        mps = balanced.Marketplace.query.all()
        self.assertEqual(len(mps), 1)

    @unittest.skip('need balanced fix')
    def test_valid_non_us_address_no_postal_code(self):
        card_number = cards.TEST_CARDS['visa'][0]
        card_payload = {
            'card_number': card_number,
            'expiration_month': 12,
            'expiration_year': date.today().year + 1,
        }
        card_payload.update(self.valid_international_address)
        card_payload.update(self.person)
        balanced.Card(**card_payload).save()

    def test_valid_us_address(self):
        buyer = self._create_buyer_account()
        self.assertTrue(buyer.id.startswith('AC'), buyer.id)
        self.assertEqual(buyer.roles, ['buyer'])
        self.assertDictEqual(buyer.meta, {'foo': 'bar'})

    def test_fractional_debit(self):
        buyer_account = self._find_buyer_account()
        bad_amount = (3.14, 100.32)
        for amount in bad_amount:
            with self.assertRaises(requests.HTTPError) as exc:
                buyer_account.debit(
                    amount=amount,
                    appears_on_statement_as='pi',
                )
            the_exception = exc.exception
            self.assertEqual(the_exception.status_code, 400)

    def test_create_simple_credit(self):
        mp = balanced.Marketplace.query.one()
        payload = dict(self.bank_account_payload)
        bank_account = balanced.BankAccount(**payload).save()
        merchant = mp.create_merchant(
            'cvraman@spectroscopy.com',
            merchant=merchants.BUSINESS_MERCHANT,
            bank_account_uri=bank_account.uri,
        )
        self.assertItemsEqual(merchant.roles, ['merchant'])

        amount = 10000
        buyer_account = self._find_buyer_account()
        buyer_account.debit(amount=amount)
        merchant.credit(amount)

    def test_credit_lower_than_escrow(self):
        mp = balanced.Marketplace.query.one()
        escrow_balance = mp.in_escrow
        credit_amount = escrow_balance + 10000
        merchants = mp.accounts
        merchant = merchants[0]
        with self.assertRaises(requests.HTTPError) as exc:
            merchant.credit(amount=credit_amount)
        the_exception = exc.exception
        self.assertEqual(the_exception.status_code, 409)

    def test_valid_international_address(self):
        for card_payload in cards.generate_international_card_payloads():
            card = balanced.Card(**card_payload).save()
            self.assertEqual(card.street_address,
                             card_payload['street_address'])

    def test_bad_card(self):
        mp = balanced.Marketplace.query.one()
        card_payload = dict(self.us_card_payload)
        card_payload['card_number'] = cards.AUTH_INVALID_CARD
        bad_card = balanced.Card(**card_payload).save()
        bad_card_uri = bad_card.uri
        buyer = mp.create_buyer(
            email_address='stephen@hawking.com',
            card_uri=bad_card_uri,
            meta={'foo': 'bar'},
        )
        with self.assertRaises(requests.HTTPError) as exc:
            buyer.debit(777)
        the_exception = exc.exception
        self.assertEqual(the_exception.status_code, 402)
        self.assertEqual(the_exception.category_code, 'card-declined')

    def test_transactions_using_second_card(self):
        mp = balanced.Marketplace.query.one()
        card_payload = dict(self.us_card_payload)
        old_card = balanced.Card(**card_payload).save()
        old_card_uri = old_card.uri
        buyer = mp.create_buyer(
            email_address='inspector@lestrade.com',
            card_uri=old_card_uri,
            meta={'foo': 'bar'},
        )

        card_payload = dict(self.us_card_payload)
        new_card = balanced.Card(**card_payload).save()
        new_card_uri = new_card.uri
        buyer.add_card(card_uri=new_card_uri)

        # Test default card
        debit = buyer.debit(777)
        self.assertEqual(debit.source.id, new_card.id)

        # Test explicit card
        debit = buyer.debit(777, source_uri=new_card_uri)
        self.assertEqual(debit.source.id, new_card.id)

    def test_associate_bad_cards(self):
        mp = balanced.Marketplace.query.one()
        card_payload = dict(self.us_card_payload)
        card = balanced.Card(**card_payload).save()
        card_uri = card.uri
        buyer = mp.create_buyer(
            email_address='james@watson.com',
            card_uri=card_uri,
            meta={'foo': 'bar'},
        )
        # Invalid card
        card_payload = dict(self.us_card_payload)
        card_payload['is_valid'] = False
        card = balanced.Card(**card_payload).save()
        card_uri = card.uri
        with self.assertRaises(requests.HTTPError) as exc:
            buyer.add_card(card_uri=card_uri)
        the_exception = exc.exception
        self.assertEqual(the_exception.status_code, 409)
        self.assertEqual(the_exception.category_code,
                         'card-not-valid')

        # Already-associated card
        card_payload = dict(self.us_card_payload)
        card = balanced.Card(**card_payload).save()
        card_uri = card.uri
        mp.create_buyer(
            email_address='james@moriarty.com',
            card_uri=card_uri,
            meta={'foo': 'bar'},
        )
        with self.assertRaises(requests.HTTPError) as exc:
            buyer.add_card(card_uri=card_uri)
        the_exception = exc.exception
        self.assertEqual(the_exception.status_code, 409)
        self.assertEqual(the_exception.category_code,
                         'card-already-funding-src')

        # Completely fake card uri
        with self.assertRaises(requests.HTTPError) as exc:
            buyer.add_card(card_uri='/completely/fake')
        the_exception = exc.exception
        self.assertEqual(the_exception.status_code, 400)

    def test_transactions_invalid_funding_sources(self):
        mp = balanced.Marketplace.query.one()
        card_payload = dict(self.us_card_payload)
        card = balanced.Card(**card_payload).save()
        card_uri = card.uri
        buyer = mp.create_buyer(
            email_address='sherlock@holmes.com',
            card_uri=card_uri,
            meta={'foo': 'bar'},
        )
        # invalidate card
        card.is_valid = False
        card.save()

        # Now use the card
        with self.assertRaises(requests.HTTPError) as exc:
            # ...implicitly
            buyer.debit(6000)
        the_exception = exc.exception
        self.assertEqual(the_exception.status_code, 409)
        self.assertEqual(the_exception.category_code,
                         'no-funding-source')

        with self.assertRaises(requests.HTTPError) as exc:
            # ... and explicitly
            buyer.debit(7000, source_uri=card.uri)
        the_exception = exc.exception
        self.assertEqual(the_exception.status_code, 409)
        self.assertEqual(the_exception.category_code,
                         'card-not-valid')

        with self.assertRaises(requests.HTTPError) as exc:
            buyer.credit(8000)
        the_exception = exc.exception
        self.assertEqual(the_exception.status_code, 409)
        self.assertEqual(the_exception.category_code,
                         'no-funding-destination')

    def test_merchant_no_bank_account(self):
        mp = balanced.Marketplace.query.one()
        merchant_payload = copy.deepcopy(merchants.BUSINESS_MERCHANT)
        merchant_payload['tax_id'] = '123456789'

        merchant = mp.create_merchant(
            'pauli@exclusion.com',
            merchant=merchant_payload,
        )
        # now try to credit
        amount = 10000
        buyer_account = self._find_buyer_account()
        buyer_account.debit(amount=amount)
        with self.assertRaises(requests.HTTPError) as exc:
            merchant.credit(amount)
        the_exception = exc.exception
        self.assertEqual(the_exception.status_code, 409)

        # try to debit
        with self.assertRaises(requests.HTTPError) as exc:
            merchant.debit(600)
        the_exception = exc.exception
        self.assertEqual(the_exception.status_code, 409)

        # add a card, make sure we can use it
        card_payload = dict(self.us_card_payload)
        card = balanced.Card(**card_payload).save()
        card_uri = card.uri
        merchant.add_card(card_uri=card_uri)

        # try to debit again
        debit = merchant.debit(601)
        self.assertEqual(debit.source.id, card.id)

    def test_add_funding_destination_to_nonmerchant(self):
        mp = balanced.Marketplace.query.one()
        card_payload = dict(self.us_card_payload)
        card = balanced.Card(**card_payload).save()
        card_uri = card.uri
        buyer = mp.create_buyer(
            email_address='irene@adler.com',
            card_uri=card_uri,
            meta={'foo': 'bar'},
        )
        # Debit money from this buyer to ensure the marketplace has enough to
        # credit her later
        buyer.debit(2 * 700)
        bank_account_payload = dict(self.bank_account_payload)
        bank_account = balanced.BankAccount(**bank_account_payload).save()
        bank_account_uri = bank_account.uri
        buyer.add_bank_account(bank_account_uri=bank_account_uri)

        # Implicit
        credit = buyer.credit(700)
        self.assertEqual(credit.destination.id, bank_account.id)
        # Explicit
        credit = buyer.credit(700, destination_uri=bank_account_uri)
        self.assertEqual(credit.destination.id, bank_account.id)

    def test_update_stupid_values(self):
        mp = balanced.Marketplace.query.one()
        card_payload = dict(self.us_card_payload)
        card = balanced.Card(**card_payload).save()
        card_uri = card.uri
        buyer = mp.create_buyer(
            email_address='inspector@gregson.com',
            card_uri=card_uri,
            meta={'foo': 'bar'},
        )
        # Add a bank account to test crediting
        bank_account_payload = dict(self.bank_account_payload)
        bank_account = balanced.BankAccount(**bank_account_payload).save()
        bank_account_uri = bank_account.uri
        buyer.add_bank_account(bank_account_uri=bank_account_uri)

        name = buyer.name
        buyer.name = 's' * 1000
        with self.assertRaises(requests.HTTPError) as exc:
            buyer.save()
        the_exception = exc.exception
        self.assertIn('must have length <=', the_exception.description)
        buyer.name = name

        with self.assertRaises(requests.HTTPError) as exc:
            buyer.debit(100 ** 100)
        the_exception = exc.exception
        self.assertEqual(the_exception.status_code, 400)
        self.assertIn('must be <=', the_exception.description)

        with self.assertRaises(requests.HTTPError) as exc:
            buyer.credit(100 ** 100)
        the_exception = exc.exception
        self.assertEqual(the_exception.status_code, 400)
        self.assertIn('must be <=', the_exception.description)

    def test_zzz_remove_owner_merchant_account_bank_account(self):
        mp = balanced.Marketplace.query.one()
        owner = mp.owner_account
        ba = owner.bank_accounts[0]
        ba.is_valid = False
        ba.save()

        with self.assertRaises(requests.HTTPError) as exc:
            owner.debit(600)
        the_exception = exc.exception
        self.assertEqual(the_exception.status_code, 409)
        self.assertEqual('no-funding-source',
                         the_exception.category_code)

        with self.assertRaises(requests.HTTPError) as exc:
            owner.credit(900)
        the_exception = exc.exception
        self.assertEqual(the_exception.status_code, 409)
        self.assertEqual('no-funding-destination',
                         the_exception.category_code)

    def test_redirect_on_merchant_failure(self):

        mp = balanced.Marketplace.query.one()
        merchant = copy.deepcopy(merchants.PERSON_MERCHANT)
        merchant['region'] = 'EX'
        merchant['postal_code'] = '99999'
        with self.assertRaises(requests.HTTPError) as ex:
            merchant = mp.create_merchant('testing@redirect.com',
                                          merchant=merchant)
        the_exception = ex.exception
        self.assertEqual(the_exception.status_code, 300)


class AICases(TestCases):

    email_address_counter = 0

    def setUp(self):
        try:
            self.mp = balanced.Marketplace.my_marketplace
        except:
            self.mp = balanced.Marketplace().save()

    def _email_address(self):
        self.email_address_counter += 1
        return 'suite+{}+{}@example.com'.format(
            time.time(), self.email_address_counter)

    def _test_transaction_successes(self, cases):
        results = []
        for callable, kwargs, validate_cls, validate_kwargs in cases:
            if inspect.isclass(callable):
                resource = callable(**kwargs).save()
            else:
                resource = callable(**kwargs)
            if validate_cls is not None:
                self.assertTrue(isinstance(resource, validate_cls))
                for k, v in validate_kwargs.iteritems():
                    resource_v = getattr(resource, k)
                    if isinstance(v, balanced.Resource):
                        self.assertEqual(v.id, resource_v.id)
                    else:
                        self.assertEqual(v, resource_v)
            results.append(resource)
        return results

    def _test_transaction_failures(self, cases):
        for callable, kwargs, exc, message in cases:
            with self.assertRaises(exc) as ex_ctx:
                if inspect.isclass(callable):
                    callable(**kwargs).save()
                else:
                    callable(**kwargs)
            ex = ex_ctx.exception
            self.assertIn(message, str(ex))

    def test_hold_successes(self):
        card1 = self.mp.create_card(**cards.CARD)
        card2 = self.mp.create_card(**cards.CARD)
        buyer = self.mp.create_buyer(self._email_address(), card1.uri)
        buyer.add_card(card2.uri)

        cases = [
            (buyer.hold,
             dict(amount=100),
             balanced.Hold,
             dict(amount=100, account=buyer, source=card2),
             ),
            (buyer.hold,
             dict(amount=123, source_uri=card1.uri),
             balanced.Hold,
             dict(amount=123, account=buyer, source=card1),
             ),
        ]

        holds = self._test_transaction_successes(cases)

        cases = [
            (holds[0].capture,
             dict(),
             balanced.Debit,
             dict(amount=100, account=buyer, source=card2)),
            (holds[1].void,
             dict(),
             None,
             dict())
        ]
        self._test_transaction_successes(cases)

    def test_hold_failures(self):
        card1 = self.mp.create_card(**cards.CARD)
        buyer1 = self.mp.create_buyer(self._email_address(), card1.uri)
        card2 = self.mp.create_card(**cards.CARD)
        buyer2 = self.mp.create_buyer(self._email_address(), card2.uri)

        cases = [
            (buyer1.hold,
             dict(amount=-100),
             balanced.exc.HTTPError,
             'Invalid field [amount] - "-100" must be >= ',
             ),
            (buyer1.hold,
             dict(amount=100, source_uri=card2.uri),
             balanced.exc.HTTPError,
             ' is not associated with account',
             ),
        ]
        self._test_transaction_failures(cases)

    def test_refund_successes(self):
        card1 = self.mp.create_card(**cards.CARD)
        card2 = self.mp.create_card(**cards.CARD)
        buyer = self.mp.create_buyer(self._email_address(), card1.uri)
        buyer.add_card(card2.uri)

        debit1 = buyer.debit(amount=101)
        debit2 = buyer.hold(amount=102).capture()
        debit3 = buyer.debit(amount=103, source_uri=card2.uri)

        cases = [
            (debit1.refund,
             dict(amount=11, description='TestDesc'),
             balanced.Refund,
             dict(debit=debit1, amount=11, description='TestDesc'),
             ),
            (debit2.refund,
             dict(amount=12),
             balanced.Refund,
             dict(debit=debit2, amount=12, description=None),
             ),
            (debit3.refund,
             dict(),
             balanced.Refund,
             dict(debit=debit3, amount=103, description=None),
             ),
        ]
        self._test_transaction_successes(cases)

    def test_refund_failures(self):
        card1 = self.mp.create_card(**cards.CARD)
        card2 = self.mp.create_card(**cards.CARD)
        buyer = self.mp.create_buyer(self._email_address(), card1.uri)
        buyer.add_card(card2.uri)

        debit1 = buyer.debit(amount=101)
        debit1.refund()
        debit2 = buyer.debit(amount=102)

        cases = [
            (debit1.refund,
             dict(),
             balanced.exc.HTTPError,
             'Amount must be less than the remaining debit amount',
             ),
            (debit2.refund,
             dict(amount=1000002),
             balanced.exc.HTTPError,
             'Invalid field [amount] - "1000002" must be <= 102',
             ),
        ]
        self._test_transaction_failures(cases)

    def test_credit_successes(self):
        card = self.mp.create_card(**cards.CARD)
        buyer = self.mp.create_buyer(self._email_address(), card.uri)
        buyer.debit(555)

        ba1 = balanced.BankAccount(
            **bank_accounts.BANK_ACCOUNT).save()
        ba2 = balanced.BankAccount(
            **bank_accounts.BANK_ACCOUNT).save()
        merchant = self.mp.create_merchant(
            self._email_address(),
            merchant=merchants.BUSINESS_MERCHANT,
            bank_account_uri=ba1.uri,
        )
        merchant.add_bank_account(ba2.uri)

        cases = [
            (merchant.credit,
             dict(amount=51),
             balanced.Credit,
             dict(destination=ba2, amount=51),
             ),
            (merchant.credit,
             dict(amount=52, destination_uri=ba1.uri),
             balanced.Credit,
             dict(destination=ba1, amount=52),
             ),
        ]
        self._test_transaction_successes(cases)

    def test_credit_failures(self):
        card = self.mp.create_card(**cards.CARD)
        buyer = self.mp.create_buyer(self._email_address(), card.uri)

        ba1 = balanced.BankAccount(
            **bank_accounts.BANK_ACCOUNT).save()
        ba2 = balanced.BankAccount(
            **bank_accounts.BANK_ACCOUNT).save()
        merchant = self.mp.create_merchant(
            self._email_address(),
            merchant=merchants.BUSINESS_MERCHANT,
            bank_account_uri=ba1.uri,
        )

        cases = [
            (merchant.credit,
             dict(amount=52, destination_uri=ba1.uri),
             balanced.exc.HTTPError,
             'has insufficient funds to cover a transfer of',
             ),
            (merchant.credit,
             dict(amount=52.12),
             balanced.exc.HTTPError,
             '"52.12" is not an integer',
             ),
            (merchant.credit,
             dict(amount=-52),
             balanced.exc.HTTPError,
             '"-52" must be >=',
             ),
        ]
        self._test_transaction_failures(cases)

        buyer.debit(555)

        cases = [
            (merchant.credit,
             dict(amount=52, destination_uri=ba2.uri),
             balanced.exc.HTTPError,
             'is not associated with account',
             ),
        ]
        self._test_transaction_failures(cases)

        ba1.delete()

        cases = [
            (merchant.credit,
             dict(amount=52),
             balanced.exc.HTTPError,
             'has no funding destination',
             ),
        ]
        self._test_transaction_failures(cases)

    def test_debits_successes(self):
        buyer_card = self.mp.create_card(**cards.CARD)
        buyer = self.mp.create_buyer(self._email_address(), buyer_card.uri)

        ba = balanced.BankAccount(
            **bank_accounts.BANK_ACCOUNT).save()
        merchant = self.mp.create_merchant(
            self._email_address(),
            merchant=merchants.BUSINESS_MERCHANT,
            bank_account_uri=ba.uri,
        )
        merchant_card = self.mp.create_card(**cards.CARD)
        merchant.add_card(merchant_card.uri)

        cases = [
            (merchant.debit,
             dict(amount=52),
             balanced.Debit,
             dict(account=merchant,
                  source=merchant_card,
                  amount=52,
                  description=None),
             ),
            (buyer.debit,
             dict(amount=112, description='都留市'),
             balanced.Debit,
             dict(account=buyer,
                  source=buyer_card,
                  amount=112,
                  description='都留市'),
             ),
        ]
        self._test_transaction_successes(cases)

    def test_debits_failures(self):
        buyer_card = self.mp.create_card(**cards.CARD)
        buyer = self.mp.create_buyer(self._email_address(), buyer_card.uri)

        ba = balanced.BankAccount(
            **bank_accounts.BANK_ACCOUNT).save()
        merchant = self.mp.create_merchant(
            self._email_address(),
            merchant=merchants.BUSINESS_MERCHANT,
            bank_account_uri=ba.uri,
        )
        merchant_card = self.mp.create_card(**cards.CARD)
        merchant.add_card(merchant_card.uri)
        merchant_card.is_valid = False
        merchant_card.save()

        cases = [
        ]
        self._test_transaction_failures(cases)

    def test_upgrade_account_to_merchant_invalid_uri(self):
        card = self.mp.create_card(**cards.CARD)
        buyer = self.mp.create_buyer('a@b.com', card.uri)
        with self.assertRaises(balanced.exc.HTTPError) as ex_ctx:
            buyer.promote_to_merchant('/no/a/merchant')
        ex = ex_ctx.exception
        self.assertEqual(ex.status_code, 400)
        self.assertIn(
            'Invalid field [merchant_uri] - "v1/no/a/merchant" does not '
            'resolve to merchant',
            str(ex))

    def test_upgrade_account_to_merchant_success(self):
        card = self.mp.create_card(**cards.CARD)
        with balanced.key_switcher(None):
            api_key = balanced.APIKey().save()
        merchant = api_key.merchant
        buyer = self.mp.create_buyer(self._email_address(), card.uri)
        self.assertItemsEqual(buyer.roles, ['buyer'])
        buyer.promote_to_merchant(merchant.uri)
        self.assertItemsEqual(buyer.roles, ['buyer', 'merchant'])

    def test_debit_uses_newly_added_funding_src(self):
        bank_account = balanced.BankAccount(
            **bank_accounts.BANK_ACCOUNT).save()
        merchant_account = self.mp.create_merchant(
            self._email_address(),
            merchant=merchants.BUSINESS_MERCHANT,
            bank_account_uri=bank_account.uri,
        )

        # debit card
        card = balanced.Card(**cards.CARD).save()
        merchant_account.add_card(card.uri)
        debit = merchant_account.debit(amount=100)
        self.assertEqual(debit.source.id, card.id)

    def test_maximum_credit_amount(self):
        bank_account = balanced.BankAccount(
            **bank_accounts.BANK_ACCOUNT).save()
        merchant_account = self.mp.create_merchant(
            self._email_address(),
            merchant=merchants.BUSINESS_MERCHANT,
            bank_account_uri=bank_account.uri,
        )
        balanced.bust_cache()
        self.mp = balanced.Marketplace.my_marketplace
        if self.mp.in_escrow:
            merchant_account.credit(self.mp.in_escrow)
        with self.assertRaises(balanced.exc.HTTPError) as ex_ctx:
            merchant_account.credit(100)
        ex = ex_ctx.exception
        self.assertIn('has insufficient funds to cover a transfer of', str(ex))
        card = self.mp.create_card(**cards.CARD)
        buyer = self.mp.create_buyer(self._email_address(), card.uri)
        buyer.debit(200)
        merchant_account.credit(100)

    def test_maximum_debit_amount(self):
        card = self.mp.create_card(**cards.CARD)
        buyer = self.mp.create_buyer(self._email_address(), card.uri)
        with self.assertRaises(balanced.exc.HTTPError) as ex_ctx:
            buyer.debit(10 ** 9 + 1)
        ex = ex_ctx.exception
        self.assertIn('must be <= 1000000000', str(ex))

    def test_maximum_hold_amount(self):
        card = self.mp.create_card(**cards.CARD)
        buyer = self.mp.create_buyer(self._email_address(), card.uri)
        with self.assertRaises(balanced.exc.HTTPError) as ex_ctx:
            buyer.hold(10 ** 9 + 1)
        ex = ex_ctx.exception
        self.assertIn('must be <= 1000000000', str(ex))

    def test_maximum_refund_amount(self):
        bank_account = balanced.BankAccount(
            **bank_accounts.BANK_ACCOUNT).save()
        merchant = self.mp.create_merchant(
            self._email_address(),
            merchant=merchants.BUSINESS_MERCHANT,
            bank_account_uri=bank_account.uri,
        )
        balanced.bust_cache()
        self.mp = balanced.Marketplace.my_marketplace
        if self.mp.in_escrow:
            merchant.credit(self.mp.in_escrow)
        card = self.mp.create_card(**cards.CARD)
        buyer = self.mp.create_buyer(self._email_address(), card.uri)
        debit = buyer.debit(200)
        bank_account = balanced.BankAccount(
            **bank_accounts.BANK_ACCOUNT).save()
        merchant.credit(100)
        with self.assertRaises(balanced.exc.HTTPError) as ex_ctx:
            debit.refund()
        ex = ex_ctx.exception
        self.assertIn('balance insufficient to issue refund', str(ex))
        ex = ex_ctx.exception
        buyer.debit(100)
        debit.refund()

    def test_view_credits_once_bank_account_has_been_invalidated(self):
        bank_account = balanced.BankAccount(
            **bank_accounts.BANK_ACCOUNT).save()
        merchant = self.mp.create_merchant(
            self._email_address(),
            merchant=merchants.BUSINESS_MERCHANT,
            bank_account_uri=bank_account.uri,
        )
        card = self.mp.create_card(
            **cards.CARD)
        buyer = self.mp.create_buyer(self._email_address(), card.uri)
        buyer.debit(100 + 200 + 300)
        credit1 = merchant.credit(100)
        credit2 = merchant.credit(200)
        credit3 = merchant.credit(300)
        merchant.bank_accounts[0].invalid = True
        merchant.bank_accounts[0].save()
        self.assertItemsEqual(
            [credit1.id, credit2.id, credit3.id],
            [c.id for c in merchant.credits]
        )

    def test_create_merchants_with_same_identity_on_same_marketplace(self):
        with balanced.key_switcher(None):
            api_key = balanced.APIKey().save()
        merchant = api_key.merchant
        merch_account_1 = self.mp.create_merchant(
            self._email_address(),
            merchant_uri=merchant.uri)
        merch_account_2 = self.mp.create_merchant(
            self._email_address(),
            merchant_uri=merchant.uri)
        self.assertEqual(merch_account_1.roles, ['merchant'])
        self.assertEqual(merch_account_2.roles, ['merchant'])

    def test_tokenize_card_without_address(self):
        balanced.Card(**cards.CARD_NO_ADDRESS).save()

    def test_delete_bank_account(self):
        bank_account = balanced.BankAccount(
            **bank_accounts.BANK_ACCOUNT).save()
        bank_account.delete()

    def test_verify_test_bank_account(self):
        bank_account = balanced.BankAccount(
            **bank_accounts.BANK_ACCOUNT).save()
        verification = bank_account.verify()
        verification.confirm(1, 1)
        ex = balanced.exc.FundingInstrumentVerificationFailure
        with self.assertRaises(ex):
            verification.confirm(1, 1)

    def test_verify_test_bank_account_failure(self):
        bank_account = balanced.BankAccount(
            **bank_accounts.BANK_ACCOUNT).save()
        verification = bank_account.verify()
        ex = balanced.exc.FundingInstrumentVerificationFailure
        for _ in xrange(verification.remaining_attempts):
            with self.assertRaises(ex):
                verification.confirm(1, 2)
        with self.assertRaises(ex):
            verification.confirm(1, 1)

########NEW FILE########
__FILENAME__ = test_balanced
from __future__ import unicode_literals

from tests.utils import TestCase


class TestBalancedImportStar(TestCase):

    def test_import_star(self):
        # not sure who uses import * any more, but we should
        # test this
        try:
            # the __import__ doesn't do what I want here.
            # and doing a "from balanced import *" generates an
            # unsupressable SyntaxWarning.
            exec "from balanced import *"  # pylint: disable-msg=W0122
        except Exception as exc:
            raise ImportError("%s" % exc)

########NEW FILE########
__FILENAME__ = test_client
from __future__ import unicode_literals

import balanced

from . import utils


class TestClient(utils.TestCase):

    def setUp(self):
        super(TestClient, self).setUp()

    def test_configure(self):
        expected_headers = {
            'content-type': 'application/json;revision=1.1',
            'accept': 'application/vnd.api+json;revision=1.1',
            'User-Agent': u'balanced-python/' + balanced.__version__,
        }
        self.assertDictContainsSubset(
            expected_headers, balanced.config.client.config.headers
        )

########NEW FILE########
__FILENAME__ = test_resource
from __future__ import unicode_literals

import balanced

from . import fixtures, utils


class TestResourceConstruction(utils.TestCase):

    def setUp(self):
        super(TestResourceConstruction, self).setUp()

    def test_load_resource(self):
        resp = fixtures.Resources.marketplaces
        marketplace = balanced.Marketplace(**resp)
        self.assertIsNotNone(marketplace.debits)

########NEW FILE########
__FILENAME__ = test_suite
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
import time
from datetime import date

import unittest2 as unittest
import requests

import balanced
from balanced import exc as bexc

# fixtures

TEST_CARDS = {
    'visa': [
        '4112344112344113',
        '4110144110144115',
        '4114360123456785',
        '4061724061724061',
    ],
    'mastercard': [
        '5111005111051128'
        '5112345112345114'
        '5115915115915118'
        '5116601234567894'
    ],
    'amex': [
        '371144371144376',
        '341134113411347',
    ],
    'discover': [
        '6011016011016011',
        '6559906559906557',
    ]
}

PERSON = {
    'name': 'William James',
    'address': {
        'line1': '167 West 74th Street',
        'line2': 'Apt 7',
        'state': 'NY',
        'city': 'NYC',
        'postal_code': '10023',
        'country_code': 'USA',
    },
    'dob': '1842-12',
    'phone': '+16505551234',
    'email': 'python-client@example.org',
}

BUSINESS = PERSON.copy()
BUSINESS['ein'] = '123456789'
BUSINESS['business_name'] = 'Foo corp'

CARD = {
    'name': 'Johnny Fresh',
    'number': '4444424444444440',
    'expiration_month': 12,
    'expiration_year': date.today().year + 1,
    'csc': '123',
    'address': {
        'line1': '123 Fake Street',
        'line2': 'Apt 7',
        'city': 'Jollywood',
        'state': 'CA',
        'postal_code': '90210',
        'country_code': 'US',
    }
}

#: a card which will always create a dispute when you debit it
DISPUTE_CARD = CARD.copy()
DISPUTE_CARD['number'] = '6500000000000002'

CREDITABLE_CARD = {
    'name': 'Johannes Bach',
    'number': '4342561111111118',
    'expiration_month': 05,
    'expiration_year': date.today().year + 1,
}

NON_CREDITABLE_CARD = {
    'name': 'Georg Telemann',
    'number': '4111111111111111',
    'expiration_month': 12,
    'expiration_year': date.today().year + 1,
}

INTERNATIONAL_CARD = {
    'name': 'Johnny Fresh',
    'number': '4444424444444440',
    'expiration_month': 12,
    'expiration_year': date.today().year + 1,
    'address': {
        'street_address': '田原３ー８ー１',
        'city': '都留市',
        'state': '山梨県',
        'postal_code': '4020054',
        'country_code': 'JPN',
    }
}

BANK_ACCOUNT = {
    'name': 'Homer Jay',
    'account_number': '112233a',
    'routing_number': '121042882',
}

BANK_ACCOUNT_W_TYPE = {
    'name': 'Homer Jay',
    'account_number': '112233a',
    'routing_number': '121042882',
    'type': 'checking'
}


class BasicUseCases(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.marketplace, cls.api_key = cls.create_marketplace()

    def setUp(self):
        super(BasicUseCases, self).setUp()
        # some test might rewrite api_key, so we need to configure it
        # here again
        balanced.configure(self.api_key.secret)

    @classmethod
    def create_marketplace(self):
        balanced.configure(None)
        api_key = balanced.APIKey().save()
        balanced.configure(api_key.secret)
        marketplace = balanced.Marketplace().save()
        return marketplace, api_key

    def test_create_a_second_marketplace_should_fail(self):
        with self.assertRaises(requests.HTTPError) as exc:
            balanced.Marketplace().save()
        the_exception = exc.exception
        self.assertEqual(the_exception.status_code, 409)

    def test_index_the_marketplaces(self):
        self.assertEqual(balanced.Marketplace.query.count(), 1)

    def test_create_a_customer(self):
        meta = {'test#': 'test_d'}
        card = balanced.Card(**CARD).save()
        buyer = balanced.Customer(
            source=card,
            meta=meta,
            **PERSON
        ).save()
        self.assertEqual(buyer.name, PERSON['name'])
        self.assertIsNotNone(buyer.created_at)
        self.assertIsNotNone(buyer.href)
        self.assertEqual(buyer.cards.count(), 1)
        self.assertEqual(buyer.cards.first().id, card.id)

    def test_debit_a_card_and_refund(self):
        card = balanced.Card(**CARD).save()
        debit = card.debit(
            amount=1000,
            appears_on_statement_as='atest',
            meta={'fraud': 'yes'},
            description='Descripty')
        self.assertTrue(debit.id.startswith('W'))
        self.assertEqual(debit.description, 'Descripty')
        self.assertEqual(debit.appears_on_statement_as, 'BAL*atest')

        refund = debit.refund(amount=100)
        self.assertTrue(refund.id.startswith('RF'))
        self.assertEqual(refund.debit.href, debit.href)

        another_debit = card.debit(
            amount=1000,
            meta={'fraud': 'yes'})
        self.assertEqual(another_debit.appears_on_statement_as,
                         'BAL*example.com')

        another_debit.refund()

    def test_create_hold_and_void_it(self):
        card = balanced.Card(**CARD).save()
        hold = card.hold(amount=1500, description='Hold me')
        self.assertEqual(hold.description, 'Hold me')
        hold.cancel()

    def test_create_hold_and_capture_it(self):
        card = balanced.Card(**CARD).save()
        hold = card.hold(amount=1500)
        self.assertTrue(hold.id.startswith('HL'))
        debit = hold.capture()
        self.assertEqual(debit.amount, 1500)

    def test_create_a_person_customer(self):
        customer = balanced.Customer(**PERSON).save()
        for key, value in PERSON.iteritems():
            if key == 'dob':
                continue
            if isinstance(value, dict):
                self.assertDictEqual(getattr(customer, key), value)
            else:
                self.assertEqual(getattr(customer, key), value)

    def test_create_a_business_customer(self):
        customer = balanced.Customer(**BUSINESS).save()
        for key, value in BUSINESS.iteritems():
            if key == 'dob':
                continue
            if isinstance(value, dict):
                self.assertDictEqual(getattr(customer, key), value)
            else:
                self.assertEqual(getattr(customer, key), value)

    def test_credit_a_bank_account(self):
        self.create_marketplace()  # NOTE: fresh mp for escrow checks
        card = balanced.Card(**INTERNATIONAL_CARD).save()
        bank_account = balanced.BankAccount(**BANK_ACCOUNT).save()
        debit = card.debit(amount=10000)
        credit = bank_account.credit(amount=1000)
        self.assertTrue(credit.id.startswith('CR'))
        self.assertEqual(credit.amount, 1000)
        with self.assertRaises(requests.HTTPError) as exc:
            bank_account.credit(amount=(debit.amount - credit.amount) + 1)
        self.assertEqual(exc.exception.status_code, 409)
        self.assertEqual(exc.exception.category_code, 'insufficient-funds')

    def test_credit_existing_card(self):
        funding_card = balanced.Card(**CARD).save()
        card = balanced.Card(**CREDITABLE_CARD).save()
        debit = funding_card.debit(amount=250000)
        credit = card.credit(amount=250000)
        self.assertTrue(credit.id.startswith('CR'))
        self.assertEqual(credit.href, '/credits/{0}'.format(credit.id))
        self.assertEqual(credit.status, 'succeeded')
        self.assertEqual(credit.amount, 250000)

    def test_credit_card_in_request(self):
        funding_card = balanced.Card(**CARD).save()
        debit = funding_card.debit(amount=250000)
        credit = balanced.Credit(
            amount=250000,
            description='A sweet ride',
            destination=CREDITABLE_CARD
        ).save()
        self.assertTrue(credit.id.startswith('CR'))
        self.assertEqual(credit.href, '/credits/{0}'.format(credit.id))
        self.assertEqual(credit.status, 'succeeded')
        self.assertEqual(credit.amount, 250000)
        self.assertEqual(credit.description, 'A sweet ride')

    def test_credit_card_can_credit_false(self):
        funding_card = balanced.Card(**CARD).save()
        debit = funding_card.debit(amount=250000)
        card = balanced.Card(**NON_CREDITABLE_CARD).save()
        with self.assertRaises(bexc.FundingSourceNotCreditable) as exc:
            card.credit(amount=250000)

    def test_credit_card_limit(self):
        funding_card = balanced.Card(**CARD).save()
        debit = funding_card.debit(amount=250005)
        card = balanced.Card(**CREDITABLE_CARD).save()
        with self.assertRaises(requests.HTTPError) as exc:
            credit = card.credit(amount=250001)
        self.assertEqual(exc.exception.status_code, 409)
        self.assertEqual(exc.exception.category_code, 'amount-exceeds-limit')

    def test_credit_card_require_name(self):
        funding_card = balanced.Card(**CARD).save()
        debit = funding_card.debit(amount=250005)
        card_payload = CREDITABLE_CARD.copy()
        card_payload.pop("name")
        card = balanced.Card(**card_payload).save()
        with self.assertRaises(requests.HTTPError) as exc:
            credit = card.credit(amount=250001)
        self.assertEqual(exc.exception.status_code, 400)
        self.assertEqual(exc.exception.category_code, 'name-required-to-credit')

    def test_escrow_limit(self):
        self.create_marketplace()  # NOTE: fresh mp for escrow checks
        bank_account = balanced.BankAccount(**BANK_ACCOUNT).save()
        original_balance = 0
        with self.assertRaises(requests.HTTPError) as exc:
            bank_account.credit(amount=original_balance + 1)
        ex = exc.exception
        self.assertEqual(ex.status_code, 409)
        self.assertEqual(ex.category_code, 'insufficient-funds')

    def test_slice_syntax(self):
        total_debit = balanced.Debit.query.count()
        self.assertNotEqual(total_debit, 2)
        self.assertEqual(len(balanced.Debit.query), total_debit)
        sliced_debits = balanced.Debit.query[:2]
        self.assertEqual(len(sliced_debits), 2)
        for debit in sliced_debits:
            self.assertIsInstance(debit, balanced.Debit)
        all_debits = balanced.Debit.query.all()
        last = total_debit * -1
        for index, debit in enumerate(all_debits):
            self.assertEqual(debit.href,
                             balanced.Debit.query[last + index].href)

    def test_filter_and_sort(self):
        card = balanced.Card(**INTERNATIONAL_CARD).save()
        debits = [
            card.debit(amount=1122, meta={'tag': meta})
            for meta in ('1', '1', '2')
        ]

        for meta in ('1', '2'):
            debs = balanced.Debit.query.filter(
                balanced.Debit.f.meta.tag == meta
            )
            self.assertItemsEqual(
                [deb.id for deb in debs],
                [deb.id for deb in debits if deb.meta['tag'] == meta]
            )

        debs = balanced.Debit.query.filter(
            balanced.Debit.f.meta.contains('tag')
        ).sort(balanced.Debit.f.amount.asc())
        self.assertEqual(len(debs), 3)
        self.assertItemsEqual([deb.id for deb in debs],
                              [deb.id for deb in debits])

    def test_create_international_card(self):
        card = balanced.Card(**INTERNATIONAL_CARD).save()
        self.assertTrue(card.id.startswith('CC'))

    def test_credit_bank_account(self):
        card = balanced.Card(**INTERNATIONAL_CARD).save()
        card.debit(50)
        bank_account = balanced.BankAccount(**BANK_ACCOUNT_W_TYPE).save()
        cr = bank_account.credit(50)
        self.assertEqual(cr.amount, 50)

    def test_reverse_a_credit(self):
        card = balanced.Card(**INTERNATIONAL_CARD).save()
        card.debit(5000)
        bank_account = balanced.BankAccount(**BANK_ACCOUNT_W_TYPE).save()
        credit = bank_account.credit(amount=5000)
        reversal = credit.reverse()
        self.assertEqual(reversal.amount, 5000)
        self.assertIn(credit.id, reversal.credit.href)

    def test_delete_bank_account(self):
        customer = balanced.Customer().save()
        bank_account = balanced.BankAccount(**BANK_ACCOUNT_W_TYPE).save()
        bank_account.associate_to_customer(customer)
        bank_account.unstore()

    def test_delete_card(self):
        customer = balanced.Customer().save()
        card = balanced.Card(**CARD).save()
        card.associate_to_customer(customer)
        card.unstore()

    def test_fetch_resource(self):
        customer = balanced.Customer().save()
        customer2 = balanced.Customer.fetch(customer.href)
        for prop in ('id', 'href', 'name', 'created_at'):
            self.assertEqual(
                getattr(customer, prop),
                getattr(customer2, prop),
            )

    def test_order(self):
        merchant = balanced.Customer().save()
        bank_account = balanced.BankAccount(**BANK_ACCOUNT).save()
        bank_account.associate_to_customer(merchant)

        order = merchant.create_order(description='foo order')

        card = balanced.Card(**INTERNATIONAL_CARD).save()

        # debit to increment escrow
        card.debit(amount=1000)

        # debit the card and associate with the order.
        card.debit(amount=100, order=order)

        order = balanced.Order.fetch(order.href)

        # the order captured the amount of the debit
        self.assertEqual(order.amount_escrowed, 100)

        # pay out half
        credit = bank_account.credit(amount=50, order=order)

        self.assertEqual(credit.order.href, order.href)

        order = balanced.Order.fetch(order.href)

        # half the money remains
        self.assertEqual(order.amount_escrowed, 50)

        # not enough money in the order to pay out
        with self.assertRaises(balanced.exc.BalancedError):
            bank_account.credit(amount=150, order=order)

    def test_order_restrictions(self):
        merchant = balanced.Customer().save()

        order = merchant.create_order(description='foo order')

        card = balanced.Card(**INTERNATIONAL_CARD).save()

        # debit the card and associate with the order.
        card.debit(amount=100, order=order)

        another_bank_account = balanced.BankAccount(
            account_number="1234567890",
            routing_number="321174851",
            name="Jack Q Merchant",
        ).save()

        # not associated with the order
        with self.assertRaises(balanced.exc.BalancedError):
            another_bank_account.credit(amount=50, order=order)

    def test_order_helper_methods(self):
        merchant = balanced.Customer().save()
        order = merchant.create_order()
        card = balanced.Card(**INTERNATIONAL_CARD).save()

        order.debit_from(source=card, amount=1234)
        bank_account = balanced.BankAccount(
            account_number='1234567890',
            routing_number='321174851',
            name='Someone',
        ).save()
        bank_account.associate_to_customer(merchant)
        order.credit_to(destination=bank_account, amount=1234)

    def test_empty_list(self):
        # NOTE: we need a whole new marketplace to reproduce the bug,
        # otherwise, it's very likely we will consume records created
        # by other tests
        self.create_marketplace()
        self.assertEqual(balanced.Credit.query.all(), [])

    def test_query_pagination(self):
        card = balanced.Card(**CARD).save()
        for _ in xrange(30): card.debit(amount=100)
        self.assertEqual(len(balanced.Debit.query.all()), balanced.Debit.query.count())

    def test_dispute(self):
        card = balanced.Card(**DISPUTE_CARD).save()
        debit = card.debit(amount=100)

        # TODO: this is ugly, I think we should provide a more
        # reliable way to generate dispute, at least it should not
        # take this long
        print >> sys.stderr, (
            'It takes a while before the dispute record created, '
            'take and nap and wake up, then it should be done :/ '
            '(last time I tried it took 10 minutes...)'
        )
        timeout = 12 * 60
        interval = 10
        begin = time.time()
        while True:
            if balanced.Dispute.query.count():
                break
            time.sleep(interval)
            elapsed = time.time() - begin
            print >> sys.stderr, 'Polling disputes..., elapsed', elapsed
            self.assertLess(elapsed, timeout, 'Ouch, timeout')

        dispute = balanced.Dispute.query.one()
        self.assertEqual(dispute.status, 'pending')
        self.assertEqual(dispute.reason, 'fraud')
        self.assertEqual(dispute.transaction.id, debit.id)


    def test_external_accounts(self):
        external_account = balanced.ExternalAccount(
            token='123123123',
            provider='name_of_provider',
        ).save()
        debit = external_account.debit(
            amount=1234
        )
        self.assertEqual(debit.source.id, external_account.id)

    def test_general_resources(self):
        card = balanced.Card(**CARD).save()
        customer = balanced.Customer().save()
        card.associate_to_customer(customer)
        debit = card.debit(amount=1000)
        self.assertIsNotNone(debit)
        self.assertIsNotNone(debit.source)
        self.assertTrue(isinstance(debit.source, balanced.Card))

    def test_get_none_for_none(self):
        card = balanced.Card(**CARD).save()
        customer = balanced.Customer().save()
        self.assertIsNone(card.customer)
        card.associate_to_customer(customer)
        card = balanced.Card.get(card.href)
        self.assertIsNotNone(card.customer)
        self.assertTrue(isinstance(card.customer, balanced.Customer))


class Rev0URIBasicUseCases(unittest.TestCase):
    """This test case ensures all revision 0 URIs can work without a problem
    with current revision 1 client

    """

    @classmethod
    def setUpClass(cls):
        # ensure we won't consume API key from other test case
        balanced.configure()
        cls.api_key = balanced.APIKey().save()
        balanced.configure(cls.api_key.secret)
        cls.marketplace = balanced.Marketplace().save()

    @classmethod
    def _iter_customer_uris(cls, marketplace, customer):
        args = dict(
            mp=marketplace,
            customer=customer,
        )
        for pattern in [
            '/v1/customers/{customer.id}',
            '/v1/marketplaces/{mp.id}/accounts/{customer.id}',
        ]:
            yield pattern.format(**args)

    @classmethod
    def _iter_card_uris(cls, marketplace, customer, card):
        args = dict(
            mp=marketplace,
            customer=customer,
            card=card,
        )
        for pattern in [
            '/v1/customers/{customer.id}/cards/{card.id}',
            '/v1/marketplaces/{mp.id}/cards/{card.id}',
            '/v1/marketplaces/{mp.id}/accounts/{customer.id}/cards/{card.id}',
        ]:
            yield pattern.format(**args)

    @classmethod
    def _iter_bank_account_uris(cls, marketplace, customer, bank_account):
        args = dict(
            mp=marketplace,
            customer=customer,
            bank_account=bank_account,
        )
        for pattern in [
            '/v1/customers/{customer.id}/bank_accounts/{bank_account.id}',
            '/v1/marketplaces/{mp.id}/bank_accounts/{bank_account.id}',
            '/v1/marketplaces/{mp.id}/accounts/{customer.id}/bank_accounts/{bank_account.id}',
        ]:
            yield pattern.format(**args)

    def assert_not_rev0(self, resource):
        """Ensures the given resouce is not in revision 0 format

        """
        self.assert_(not hasattr(resource, '_uris'))

    def test_marketplace(self):
        uri = '/v1/marketplaces/{0}'.format(self.marketplace.id)
        marketplace = balanced.Marketplace.fetch(uri)
        self.assertEqual(marketplace.id, self.marketplace.id)
        self.assert_not_rev0(marketplace)

    def test_customer(self):
        customer = balanced.Customer().save()
        for uri in self._iter_customer_uris(
            marketplace=self.marketplace,
            customer=customer,
        ):
            result_customer = balanced.Customer.fetch(uri)
            self.assertEqual(result_customer.id, customer.id)
            self.assert_not_rev0(result_customer)

    def test_associate_card(self):
        customer = balanced.Customer().save()
        cards = set()
        for uri in self._iter_customer_uris(
            marketplace=self.marketplace,
            customer=customer,
        ):
            card = balanced.Card(**CARD).save()
            card.customer = uri
            card.save()
            cards.add(card.href)
        customer_cards = set(card.href for card in customer.cards)
        self.assertEqual(cards, customer_cards)

    def test_associate_bank_account(self):
        customer = balanced.Customer().save()
        bank_accounts = set()
        for uri in self._iter_customer_uris(
            marketplace=self.marketplace,
            customer=customer,
        ):
            bank_account = balanced.BankAccount(**BANK_ACCOUNT).save()
            bank_account.customer = uri
            bank_account.save()
            bank_accounts.add(bank_account.href)

        customer_bank_accounts = set(
            bank_account.href for bank_account in customer.bank_accounts
        )
        self.assertEqual(bank_accounts, customer_bank_accounts)

    def test_set_default_card(self):
        customer = balanced.Customer().save()
        card1 = balanced.Card(**CARD).save()
        card1.associate_to_customer(customer)
        card2 = balanced.Card(**CARD).save()
        card2.associate_to_customer(customer)
        # set card 1 as the default source
        customer.source = card1.href
        customer.save()
        self.assertEqual(customer.source.href, card1.href)
        for uri in self._iter_card_uris(
            marketplace=self.marketplace,
            customer=customer,
            card=card2,
        ):
            # set the source to card2 via rev0 URI
            customer.source = uri
            customer.save()
            self.assertEqual(customer.source.href, card2.href)

            # set the source back to card1
            customer.source = card1.href
            customer.save()
            self.assertEqual(customer.source.href, card1.href)

    def test_set_default_bank_account(self):
        customer = balanced.Customer().save()
        bank_account1 = balanced.BankAccount(**BANK_ACCOUNT).save()
        bank_account1.associate_to_customer(customer)
        bank_account2 = balanced.BankAccount(**BANK_ACCOUNT).save()
        bank_account2.associate_to_customer(customer)
        # set bank account 1 as the default destination
        customer.destination = bank_account1.href
        customer.save()
        self.assertEqual(customer.destination.href, bank_account1.href)
        for uri in self._iter_bank_account_uris(
            marketplace=self.marketplace,
            customer=customer,
            bank_account=bank_account2,
        ):
            # set the destination to bank_account2 via rev0 URI
            customer.destination = uri
            customer.save()
            self.assertEqual(customer.destination.href, bank_account2.href)

            # set the destination back to bank_account1
            customer.destination = bank_account1.href
            customer.save()
            self.assertEqual(customer.destination.href, bank_account1.href)

    def test_debit(self):
        customer = balanced.Customer().save()
        card = balanced.Card(**CARD).save()
        card.associate_to_customer(customer)
        for uri in self._iter_card_uris(
            marketplace=self.marketplace,
            customer=customer,
            card=card,
        ):
            debit = balanced.Debit(amount=100, source=uri).save()
            self.assertEqual(debit.source.href, card.href)
            self.assertEqual(debit.amount, 100)

    def test_credit(self):
        # make sufficient amount for credit later
        card = balanced.Card(**CARD).save()
        card.debit(amount=1000000)

        customer = balanced.Customer().save()
        bank_account = balanced.BankAccount(**BANK_ACCOUNT).save()
        bank_account.associate_to_customer(customer)
        for uri in self._iter_bank_account_uris(
            marketplace=self.marketplace,
            customer=customer,
            bank_account=bank_account,
        ):
            credit = balanced.Credit(amount=100, destination=uri).save()
            self.assertEqual(credit.destination.href, bank_account.href)
            self.assertEqual(credit.amount, 100)

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals

import contextlib
import multiprocessing
import unittest2 as unittest

from wsgiref.simple_server import make_server


class TestCase(unittest.TestCase):
    pass


class WSGIServerTest(TestCase):

    def setUp(self):
        self.server_process = None

    @contextlib.contextmanager
    def start_server(self, app, port=31337):
        server = make_server('', port, app)
        self.server_process = multiprocessing.Process(
            target=server.serve_forever
        )
        try:
            self.server_process.start()
            yield
        finally:
            self._stop_server()

    def _stop_server(self):
        self.server_process.terminate()
        self.server_process.join()
        del self.server_process
        self.server_process = None

########NEW FILE########
