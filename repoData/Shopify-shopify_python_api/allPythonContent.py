__FILENAME__ = shopify_api
#!/usr/bin/env python
"""shopify_api.py wrapper script for running it the source directory"""

import sys
import os.path

# Use the development rather than installed version
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

execfile(os.path.join(project_root, 'scripts', 'shopify_api.py'))

########NEW FILE########
__FILENAME__ = shopify_api
#!/usr/bin/env python

import shopify
import code
import sys
import os
import os.path
import glob
import subprocess
import yaml

def start_interpreter(**variables):
    console = type('shopify ' + shopify.version.VERSION, (code.InteractiveConsole, object), {})
    import readline
    console(variables).interact()

class ConfigFileError(StandardError):
    pass

def usage(usage_string):
    """Decorator to add a usage string to a function"""
    def decorate(func):
        func.usage = usage_string
        return func
    return decorate

class TasksMeta(type):
    _prog = os.path.basename(sys.argv[0])

    def __new__(mcs, name, bases, new_attrs):
        cls = type.__new__(mcs, name, bases, new_attrs)

        tasks = new_attrs.keys()
        tasks.append("help")
        def filter_func(item):
            return not item.startswith("_") and hasattr(getattr(cls, item), "__call__")
        tasks = filter(filter_func, tasks)
        cls._tasks = sorted(tasks)

        return cls

    def run_task(cls, task=None, *args):
        if task in [None, '-h', '--help']:
            cls.help()
            return

        # Allow unambigious abbreviations of tasks
        if task not in cls._tasks:
            matches = filter(lambda item: item.startswith(task), cls._tasks)
            if len(matches) == 1:
                task = matches[0]
            else:
                print >>sys.stderr, 'Could not find task "%s".' % (task)

        task_func = getattr(cls, task)
        task_func(*args)

    @usage("help [TASK]")
    def help(cls, task=None):
        """Describe available tasks or one specific task"""
        if task is None:
            usage_list = []
            for task in iter(cls._tasks):
                task_func = getattr(cls, task)
                usage_string = "  %s %s" % (cls._prog, task_func.usage)
                desc = task_func.__doc__.splitlines()[0]
                usage_list.append((usage_string, desc))
            max_len = reduce(lambda m, item: max(m, len(item[0])), usage_list, 0)
            print("Tasks:")
            cols = int(os.environ.get("COLUMNS", 80))
            for line, desc in usage_list:
                task_func = getattr(cls, task)
                if desc:
                    line = "%s%s  # %s" % (line, " " * (max_len - len(line)), desc)
                if len(line) > cols:
                    line = line[:cols - 3] + "..."
                print(line)
        else:
            task_func = getattr(cls, task)
            print("Usage:")
            print("  %s %s" % (cls._prog, task_func.usage))
            print("")
            print(task_func.__doc__)


class Tasks(object):
    __metaclass__ = TasksMeta

    _shop_config_dir = os.path.join(os.environ["HOME"], ".shopify", "shops")
    _default_symlink = os.path.join(_shop_config_dir, "default")

    @classmethod
    @usage("list")
    def list(cls):
        """list available connections"""
        for c in cls._available_connections():
            prefix = " * " if cls._is_default(c) else "   "
            print(prefix + c)

    @classmethod
    @usage("add CONNECTION")
    def add(cls, connection):
        """create a config file for a connection named CONNECTION"""
        filename = cls._get_config_filename(connection)
        if os.path.exists(filename):
            raise ConfigFileError("There is already a config file at " + filename)
        else:
            config = dict(protocol='https')
            domain = raw_input("Domain? (leave blank for %s.myshopify.com) " % (connection))
            if not domain.strip():
                domain = "%s.myshopify.com" % (connection)
            config['domain'] = domain
            print("")
            print("open https://%s/admin/api in your browser to get API credentials" % (domain))
            config['api_key'] = raw_input("API key? ")
            config['password'] = raw_input("Password? ")
            if not os.path.isdir(cls._shop_config_dir):
                os.makedirs(cls._shop_config_dir)
            file(filename, 'w').write(yaml.dump(config, default_flow_style=False, explicit_start="---"))
        if len(cls._available_connections()) == 1:
            cls.default(connection)

    @classmethod
    @usage("remove CONNECTION")
    def remove(cls, connection):
        """remove the config file for CONNECTION"""
        filename = cls._get_config_filename(connection)
        if os.path.exists(filename):
            if cls._is_default(connection):
                os.remove(cls._default_symlink)
            os.remove(filename)
        else:
            cls._no_config_file_error(filename)

    @classmethod
    @usage("edit [CONNECTION]")
    def edit(cls, connection=None):
        """open the config file for CONNECTION with you default editor"""
        filename = cls._get_config_filename(connection)
        if os.path.exists(filename):
            editor = os.environ.get("EDITOR")
            if editor:
                subprocess.call([editor, filename])
            else:
                print("Please set an editor in the EDITOR environment variable")
        else:
            cls._no_config_file_error(filename)

    @classmethod
    @usage("show [CONNECTION]")
    def show(cls, connection=None):
        """output the location and contents of the CONNECTION's config file"""
        if connection is None:
            connection = cls._default_connection()
        filename = cls._get_config_filename(connection)
        if os.path.exists(filename):
            print(filename)
            print(file(filename).read())
        else:
            cls._no_config_file_error(filename)

    @classmethod
    @usage("default [CONNECTION]")
    def default(cls, connection=None):
        """show the default connection, or make CONNECTION the default"""
        if connection is not None:
            target = cls._get_config_filename(connection)
            if os.path.exists(target):
                if os.path.exists(cls._default_symlink):
                    os.remove(cls._default_symlink)
                os.symlink(target, cls._default_symlink)
            else:
                cls._no_config_file_error(target)
        if os.path.exists(cls._default_symlink):
            print("Default connection is " + cls._default_connection())
        else:
            print("There is no default connection set")

    @classmethod
    @usage("console [CONNECTION]")
    def console(cls, connection=None):
        """start an API console for CONNECTION"""
        filename = cls._get_config_filename(connection)
        if not os.path.exists(filename):
            cls._no_config_file_error(filename)

        config = yaml.safe_load(file(filename).read())
        print("using %s" % (config["domain"]))
        session = cls._session_from_config(config)
        shopify.ShopifyResource.activate_session(session)

        start_interpreter(shopify=shopify)

    @classmethod
    @usage("version")
    def version(cls, connection=None):
        """output the shopify library version"""
        print(shopify.version.VERSION)

    @classmethod
    def _available_connections(cls):
        return map(lambda item: os.path.splitext(os.path.basename(item))[0],
              glob.glob(os.path.join(cls._shop_config_dir, "*.yml")))

    @classmethod
    def _default_connection_target(cls):
        if not os.path.exists(cls._default_symlink):
            return None
        target = os.readlink(cls._default_symlink)
        return os.path.join(cls._shop_config_dir, target)


    @classmethod
    def _default_connection(cls):
        target = cls._default_connection_target()
        if not target:
            return None
        return os.path.splitext(os.path.basename(target))[0]

    @classmethod
    def _get_config_filename(cls, connection):
        if connection is None:
            return cls._default_symlink
        else:
            return os.path.join(cls._shop_config_dir, connection + ".yml")

    @classmethod
    def _session_from_config(cls, config):
        session = shopify.Session(config.get("domain"))
        session.protocol = config.get("protocol", "https")
        session.api_key = config.get("api_key")
        session.token = config.get("password")
        return session

    @classmethod
    def _is_default(cls, connection):
        return connection == cls._default_connection()

    @classmethod
    def _no_config_file_error(cls, filename):
        raise ConfigFileError("There is no config file at " + filename)

try:
    Tasks.run_task(*sys.argv[1:])
except ConfigFileError, e:
    print(e)

########NEW FILE########
__FILENAME__ = base
import pyactiveresource.connection
from pyactiveresource.activeresource import ActiveResource, ResourceMeta, formats
import shopify.yamlobjects
import shopify.mixins as mixins
import shopify
import threading
import urllib
import urllib2
import urlparse
import sys

# Store the response from the last request in the connection object
class ShopifyConnection(pyactiveresource.connection.Connection):
    response = None

    def __init__(self, site, user=None, password=None, timeout=None,
                 format=formats.JSONFormat):
        super(ShopifyConnection, self).__init__(site, user, password, timeout, format)

    def _open(self, *args, **kwargs):
        self.response = None
        try:
            self.response = super(ShopifyConnection, self)._open(*args, **kwargs)
        except pyactiveresource.connection.ConnectionError, err:
            self.response = err.response
            raise
        return self.response

# Inherit from pyactiveresource's metaclass in order to use ShopifyConnection
class ShopifyResourceMeta(ResourceMeta):

    @property
    def connection(cls):
        """HTTP connection for the current thread"""
        local = cls._threadlocal
        if not getattr(local, 'connection', None):
            # Make sure these variables are no longer affected by other threads.
            local.user = cls.user
            local.password = cls.password
            local.site = cls.site
            local.timeout = cls.timeout
            local.headers = cls.headers
            local.format = cls.format
            if cls.site is None:
                raise ValueError("No shopify session is active")
            local.connection = ShopifyConnection(
                cls.site, cls.user, cls.password, cls.timeout, cls.format)
        return local.connection

    def get_user(cls):
        return getattr(cls._threadlocal, 'user', ShopifyResource._user)

    def set_user(cls, value):
        cls._threadlocal.connection = None
        ShopifyResource._user = cls._threadlocal.user = value

    user = property(get_user, set_user, None,
                    "The username for HTTP Basic Auth.")

    def get_password(cls):
        return getattr(cls._threadlocal, 'password', ShopifyResource._password)

    def set_password(cls, value):
        cls._threadlocal.connection = None
        ShopifyResource._password = cls._threadlocal.password = value

    password = property(get_password, set_password, None,
                        "The password for HTTP Basic Auth.")

    def get_site(cls):
        return getattr(cls._threadlocal, 'site', ShopifyResource._site)

    def set_site(cls, value):
        cls._threadlocal.connection = None
        ShopifyResource._site = cls._threadlocal.site = value
        if value is not None:
            host = urlparse.urlsplit(value)[1]
            auth_info, host = urllib2.splituser(host)
            if auth_info:
                user, password = urllib2.splitpasswd(auth_info)
                if user:
                    cls.user = urllib.unquote(user)
                if password:
                    cls.password = urllib.unquote(password)

    site = property(get_site, set_site, None,
                    'The base REST site to connect to.')

    def get_timeout(cls):
        return getattr(cls._threadlocal, 'timeout', ShopifyResource._timeout)

    def set_timeout(cls, value):
        cls._threadlocal.connection = None
        ShopifyResource._timeout = cls._threadlocal.timeout = value

    timeout = property(get_timeout, set_timeout, None,
                       'Socket timeout for HTTP requests')

    def get_headers(cls):
        if not hasattr(cls._threadlocal, 'headers'):
            cls._threadlocal.headers = ShopifyResource._headers.copy()
        return cls._threadlocal.headers

    def set_headers(cls, value):
        cls._threadlocal.headers = value

    headers = property(get_headers, set_headers, None,
                       'The headers sent with HTTP requests')

    def get_format(cls):
        return getattr(cls._threadlocal, 'format', ShopifyResource._format)

    def set_format(cls, value):
        cls._threadlocal.connection = None
        ShopifyResource._format = cls._threadlocal.format = value

    format = property(get_format, set_format, None,
                      'Encoding used for request and responses')


class ShopifyResource(ActiveResource, mixins.Countable):
    __metaclass__ = ShopifyResourceMeta
    _format = formats.JSONFormat
    _threadlocal = threading.local()
    _headers = {'User-Agent': 'ShopifyPythonAPI/%s Python/%s' % (shopify.VERSION, sys.version.split(' ', 1)[0])}

    def __init__(self, attributes=None, prefix_options=None):
        if attributes is not None and prefix_options is None:
            prefix_options, attributes = self.__class__._split_options(attributes)
        return super(ShopifyResource, self).__init__(attributes, prefix_options)

    def is_new(self):
        return not self.id

    def _load_attributes_from_response(self, response):
        if response.body.strip():
            self._update(self.__class__.format.decode(response.body))

    @classmethod
    def activate_session(cls, session):
        cls.site = session.site
        cls.user = None
        cls.password = None
        cls.headers['X-Shopify-Access-Token'] = session.token

    @classmethod
    def clear_session(cls):
        cls.site = None
        cls.user = None
        cls.password = None
        cls.headers.pop('X-Shopify-Access-Token', None)

########NEW FILE########
__FILENAME__ = mixins
import shopify.resources

class Countable(object):

    @classmethod
    def count(cls, _options=None, **kwargs):
        if _options is None:
            _options = kwargs
        return int(cls.get("count", **_options))


class Metafields(object):

    def metafields(self):
        return shopify.resources.Metafield.find(resource=self.__class__.plural, resource_id=self.id)

    def add_metafield(self, metafield):
        if self.is_new():
            raise ValueError("You can only add metafields to a resource that has been saved")

        metafield._prefix_options = dict(resource=self.__class__.plural, resource_id=self.id)
        metafield.save()
        return metafield


class Events(object):

    def events(self):
        return shopify.resources.Event.find(resource=self.__class__.plural, resource_id=self.id)

########NEW FILE########
__FILENAME__ = address
from ..base import ShopifyResource


class Address(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = application_charge
from ..base import ShopifyResource


class ApplicationCharge(ShopifyResource):

    def activate(self):
        self._load_attributes_from_response(self.post("activate"))

########NEW FILE########
__FILENAME__ = article
from ..base import ShopifyResource
from shopify import mixins
from comment import Comment


class Article(ShopifyResource, mixins.Metafields, mixins.Events):
    _prefix_source = "/admin/blogs/$blog_id/"

    @classmethod
    def _prefix(cls, options={}):
        blog_id = options.get("blog_id")
        if blog_id:
            return "/admin/blogs/%s" % (blog_id)
        else:
            return "/admin"

    def comments(self):
        return Comment.find(article_id=self.id)

    @classmethod
    def authors(cls, **kwargs):
        return cls.get('authors', **kwargs)

    @classmethod
    def tags(cls, **kwargs):
        return cls.get('tags', **kwargs)

########NEW FILE########
__FILENAME__ = asset
from ..base import ShopifyResource
import base64


class Asset(ShopifyResource):
    _primary_key = "key"
    _prefix_source = "/admin/themes/$theme_id/"

    @classmethod
    def _prefix(cls, options={}):
        theme_id = options.get("theme_id")
        if theme_id:
            return "/admin/themes/%s" % theme_id
        else:
            return "/admin"

    @classmethod
    def _element_path(cls, id, prefix_options={}, query_options=None):
        if query_options is None:
            prefix_options, query_options = cls._split_options(prefix_options)
        return "%s%s.%s%s" % (cls._prefix(prefix_options)+'/', cls.plural,
                              cls.format.extension, cls._query_string(query_options))

    @classmethod
    def find(cls, key=None, **kwargs):
        """
        Find an asset by key
        E.g.
            shopify.Asset.find('layout/theme.liquid', theme_id=99)
        """
        if not key:
            return super(Asset, cls).find(**kwargs)

        params = {"asset[key]": key}
        params.update(kwargs)
        theme_id = params.get("theme_id")
        path_prefix = "/admin/themes/%s" % (theme_id) if theme_id else "/admin"

        resource = cls.find_one("%s/assets.%s" % (path_prefix, cls.format.extension), **params)

        if theme_id and resource:
            resource._prefix_options["theme_id"] = theme_id
        return resource

    def __get_value(self):
        data = self.attributes.get("value")
        if data:
            return data
        data = self.attributes.get("attachment")
        if data:
            return base64.b64decode(data)

    def __set_value(self, data):
        self.__wipe_value_attributes()
        self.attributes["value"] = data

    value = property(__get_value, __set_value, None, "The asset's value or attachment")

    def attach(self, data):
        self.attachment = base64.b64encode(data)

    def destroy(self):
        options = {"asset[key]": self.key}
        options.update(self._prefix_options)
        return self.__class__.connection.delete(self._element_path(self.key, options), self.__class__.headers)

    def is_new(self):
        return False

    def __setattr__(self, name, value):
        if name in ("value", "attachment", "src", "source_key"):
            self.__wipe_value_attributes()
        return super(Asset, self).__setattr__(name, value)

    def __wipe_value_attributes(self):
        for attr in ("value", "attachment", "src", "source_key"):
            if attr in self.attributes:
                del self.attributes[attr]

########NEW FILE########
__FILENAME__ = billing_address
from ..base import ShopifyResource


class BillingAddress(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = blog
from ..base import ShopifyResource
from shopify import mixins
from article import Article


class Blog(ShopifyResource, mixins.Metafields, mixins.Events):

    def articles(self):
        return Article.find(blog_id=self.id)

########NEW FILE########
__FILENAME__ = carrier_service
from ..base import ShopifyResource


class CarrierService(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = cart
from ..base import ShopifyResource


class Cart(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = collect
from ..base import ShopifyResource


class Collect(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = comment
from ..base import ShopifyResource


class Comment(ShopifyResource):

    def remove(self):
        self._load_attributes_from_response(self.post("remove"))

    def spam(self):
        self._load_attributes_from_response(self.post("spam"))

    def approve(self):
        self._load_attributes_from_response(self.post("approve"))

    def restore(self):
        self._load_attributes_from_response(self.post("restore"))

    def not_spam(self):
        self._load_attributes_from_response(self.post("not_spam"))

########NEW FILE########
__FILENAME__ = country
from ..base import ShopifyResource


class Country(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = customer
from ..base import ShopifyResource
from shopify import mixins


class Customer(ShopifyResource, mixins.Metafields):

    @classmethod
    def search(cls, **kwargs):
        """
        Search for customers matching supplied query

        Args:
           q: Text to search for customers ("q" is short for query)
           f: Filters to apply to customers ("f" is short for query)
           page: Page to show (default: 1)
           limit: Maximum number of results to show (default: 50, maximum: 250)
        Returns:
           An array of customers.
        """
        return cls._build_list(cls.get("search", **kwargs))

########NEW FILE########
__FILENAME__ = customer_group
from customer_saved_search import CustomerSavedSearch


class CustomerGroup(CustomerSavedSearch):
    pass

########NEW FILE########
__FILENAME__ = customer_saved_search
from ..base import ShopifyResource
from customer import Customer


class CustomerSavedSearch(ShopifyResource):

    def customers(cls, **kwargs):
        return Customer._build_list(cls.get("customers", **kwargs))

########NEW FILE########
__FILENAME__ = custom_collection
from ..base import ShopifyResource
from shopify import mixins
from collect import Collect
import product


class CustomCollection(ShopifyResource, mixins.Metafields, mixins.Events):

    def products(self):
        return product.Product.find(collection_id=self.id)

    def add_product(self, product):
        return Collect.create({'collection_id': self.id, 'product_id': product.id})

    def remove_product(self, product):
        collect = Collect.find_first(collection_id=self.id, product_id=product.id)
        if collect:
            collect.destroy()

########NEW FILE########
__FILENAME__ = event
from ..base import ShopifyResource

class Event(ShopifyResource):
    _prefix_source = "/admin/$resource/$resource_id/"

    @classmethod
    def _prefix(cls, options={}):
        resource = options.get("resource")
        if resource:
            return "/admin/%s/%s" % (resource, options["resource_id"])
        else:
            return "/admin"

########NEW FILE########
__FILENAME__ = fulfillment
from ..base import ShopifyResource


class Fulfillment(ShopifyResource):
    _prefix_source = "/admin/orders/$order_id/"

    def cancel(self):
        self._load_attributes_from_response(self.post("cancel"))

    def complete(self):
        self._load_attributes_from_response(self.post("complete"))

########NEW FILE########
__FILENAME__ = fulfillment_service
from ..base import ShopifyResource


class FulfillmentService(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = image
from ..base import ShopifyResource
import base64
import re


class Image(ShopifyResource):
    _prefix_source = "/admin/products/$product_id/"

    def __getattr__(self, name):
        if name in ["pico", "icon", "thumb", "small", "compact", "medium", "large", "grande", "original"]:
            return re.sub(r"/(.*)\.(\w{2,4})", r"/\1_%s.\2" % (name), self.src)
        else:
            return super(Image, self).__getattr__(name)

    def attach_image(self, data, filename=None):
        self.attributes["attachment"] = base64.b64encode(data)
        if filename:
            self.attributes["filename"] = filename

########NEW FILE########
__FILENAME__ = line_item
from ..base import ShopifyResource


class LineItem(ShopifyResource):
  class Property(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = metafield
from ..base import ShopifyResource


class Metafield(ShopifyResource):
    _prefix_source = "/admin/$resource/$resource_id/"

    @classmethod
    def _prefix(cls, options={}):
        resource = options.get("resource")
        if resource:
            return "/admin/%s/%s" % (resource, options["resource_id"])
        else:
            return "/admin"

########NEW FILE########
__FILENAME__ = note_attribute
from ..base import ShopifyResource


class NoteAttribute(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = option
from ..base import ShopifyResource


class Option(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = order
from ..base import ShopifyResource
from shopify import mixins
from transaction import Transaction


class Order(ShopifyResource, mixins.Metafields, mixins.Events):

    def close(self):
        self._load_attributes_from_response(self.post("close"))

    def open(self):
        self._load_attributes_from_response(self.post("open"))

    def cancel(self, **kwargs):
        self._load_attributes_from_response(self.post("cancel", **kwargs))

    def transactions(self):
        return Transaction.find(order_id=self.id)

    def capture(self, amount=""):
        return Transaction.create({"amount": amount, "kind": "capture", "order_id": self.id})

########NEW FILE########
__FILENAME__ = order_risk
from ..base import ShopifyResource

class OrderRisk(ShopifyResource):
  _prefix_source = "/admin/orders/$order_id/"
  _plural = "risks"

########NEW FILE########
__FILENAME__ = page
from ..base import ShopifyResource
from shopify import mixins


class Page(ShopifyResource, mixins.Metafields, mixins.Events):
    pass

########NEW FILE########
__FILENAME__ = payment_details
from ..base import ShopifyResource


class PaymentDetails(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = product
from ..base import ShopifyResource
from shopify import mixins
from custom_collection import CustomCollection
from smart_collection import SmartCollection


class Product(ShopifyResource, mixins.Metafields, mixins.Events):

    def price_range(self):
        prices = [float(variant.price) for variant in self.variants]
        f = "%0.2f"
        min_price = min(prices)
        max_price = max(prices)
        if min_price != max_price:
            return "%s - %s" % (f % min_price, f % max_price)
        else:
            return f % min_price

    def collections(self):
        return CustomCollection.find(product_id=self.id)

    def smart_collections(self):
        return SmartCollection.find(product_id=self.id)

    def add_to_collection(self, collection):
        return collection.add_product(self)

    def remove_from_collection(self, collection):
        return collection.remove_product(self)

    def add_variant(self, variant):
        variant.attributes['product_id'] = self.id
        return variant.save()

########NEW FILE########
__FILENAME__ = product_search_engine
from ..base import ShopifyResource


class ProductSearchEngine(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = province
from ..base import ShopifyResource


class Province(ShopifyResource):
    _prefix_source = "/admin/countries/$country_id/"

########NEW FILE########
__FILENAME__ = receipt
from ..base import ShopifyResource


class Receipt(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = recurring_application_charge
from ..base import ShopifyResource


class RecurringApplicationCharge(ShopifyResource):

    @classmethod
    def current(cls):
        return cls.find_first(status="active")

    def cancel(self):
        self._load_attributes_from_response(self.destroy)

    def activate(self):
        self._load_attributes_from_response(self.post("activate"))

########NEW FILE########
__FILENAME__ = redirect
from ..base import ShopifyResource


class Redirect(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = rule
from ..base import ShopifyResource


class Rule(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = script_tag
from ..base import ShopifyResource


class ScriptTag(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = shipping_address
from ..base import ShopifyResource


class ShippingAddress(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = shipping_line
from ..base import ShopifyResource


class ShippingLine(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = shop
from ..base import ShopifyResource
from metafield import Metafield
from event import Event


class Shop(ShopifyResource):

    @classmethod
    def current(cls):
        return cls.find_one("/admin/shop." + cls.format.extension)

    def metafields(self):
        return Metafield.find()

    def add_metafield(self, metafield):
        if self.is_new():
            raise ValueError("You can only add metafields to a resource that has been saved")
        metafield.save()
        return metafield

    def events(self):
        return Event.find()

########NEW FILE########
__FILENAME__ = smart_collection
from ..base import ShopifyResource
from shopify import mixins
import product


class SmartCollection(ShopifyResource, mixins.Metafields, mixins.Events):

    def products(self):
        return product.Product.find(collection_id=self.id)

########NEW FILE########
__FILENAME__ = tax_line
from ..base import ShopifyResource


class TaxLine(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = theme
from ..base import ShopifyResource


class Theme(ShopifyResource):
    pass

########NEW FILE########
__FILENAME__ = transaction
from ..base import ShopifyResource


class Transaction(ShopifyResource):
    _prefix_source = "/admin/orders/$order_id/"

########NEW FILE########
__FILENAME__ = variant
from ..base import ShopifyResource
from shopify import mixins


class Variant(ShopifyResource, mixins.Metafields):
    _prefix_source = "/admin/products/$product_id/"

    @classmethod
    def _prefix(cls, options={}):
        product_id = options.get("product_id")
        if product_id:
            return "/admin/products/%s" % (product_id)
        else:
            return "/admin"

    def save(self):
        if 'product_id' not in self._prefix_options:
            self._prefix_options['product_id'] = self.product_id
        return super(ShopifyResource, self).save()

########NEW FILE########
__FILENAME__ = webhook
from ..base import ShopifyResource


class Webhook(ShopifyResource):

    def __get_format(self):
        return self.attributes.get("format")

    def __set_format(self, data):
        self.attributes["format"] = data

    format = property(__get_format, __set_format, None, "Format attribute")

########NEW FILE########
__FILENAME__ = session
import time
import urllib
import urllib2
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
try:
    import simplejson as json
except ImportError:
    import json
import re
from contextlib import contextmanager

class ValidationException(Exception):
    pass

class Session(object):
    api_key = None
    secret = None
    protocol = 'https'

    @classmethod
    def setup(cls, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(cls, k, v)

    @classmethod
    @contextmanager
    def temp(cls, domain, token):
        import shopify
        original_domain = shopify.ShopifyResource.get_site()
        original_token = shopify.ShopifyResource.get_headers().get('X-Shopify-Access-Token')
        original_session = shopify.Session(original_domain, original_token)

        session = Session(domain, token)
        shopify.ShopifyResource.activate_session(session)
        yield
        shopify.ShopifyResource.activate_session(original_session)

    def __init__(self, shop_url, token=None, params=None):
        self.url = self.__prepare_url(shop_url)
        self.token = token
        return

    def create_permission_url(self, scope, redirect_uri=None):
        query_params = dict(client_id=self.api_key, scope=",".join(scope))
        if redirect_uri: query_params['redirect_uri'] = redirect_uri
        return "%s://%s/admin/oauth/authorize?%s" % (self.protocol, self.url, urllib.urlencode(query_params))

    def request_token(self, params):
        if self.token:
            return self.token

        if not self.validate_params(params):
            raise ValidationException('Invalid Signature: Possibly malicious login')

        code = params['code']

        url = "%s://%s/admin/oauth/access_token?" % (self.protocol, self.url)
        query_params = dict(client_id=self.api_key, client_secret=self.secret, code=code)
        request = urllib2.Request(url, urllib.urlencode(query_params))
        response = urllib2.urlopen(request)

        if response.code == 200:
            self.token = json.loads(response.read())['access_token']
            return self.token
        else:
            raise Exception(response.msg)

    @property
    def site(self):
        return "%s://%s/admin" % (self.protocol, self.url)

    @property
    def valid(self):
        return self.url is not None and self.token is not None

    @staticmethod
    def __prepare_url(url):
        if not url or (url.strip() == ""):
            return None
        url = re.sub("https?://", "", url)
        url = re.sub("/.*", "", url)
        if url.find(".") == -1:
            url += ".myshopify.com"
        return url

    @classmethod
    def validate_params(cls, params):
        # Avoid replay attacks by making sure the request
        # isn't more than a day old.
        one_day = 24 * 60 * 60
        if int(params['timestamp']) < time.time() - one_day:
            return False

        return cls.validate_signature(params)

    @classmethod
    def validate_signature(cls, params):
        if "signature" not in params:
            return False

        sorted_params = ""
        signature = params['signature']

        for k in sorted(params.keys()):
            if k != "signature":
                sorted_params += k + "=" + str(params[k])

        return md5(cls.secret + sorted_params).hexdigest() == signature

########NEW FILE########
__FILENAME__ = version
VERSION = '2.0.4'

########NEW FILE########
__FILENAME__ = yamlobjects
try:
    # Shopify serializes receipts in YAML format, and yaml.safe_load will
    # not automatically load custom types because of security purpose,
    # so create safe loaders for types returned from Shopify here.
    #
    # The YAMLObject metaclass will automatically add these classes to
    # the list of constructors for yaml.safe_load to use.
    import yaml

    class YAMLHashWithIndifferentAccess(yaml.YAMLObject):
        yaml_tag = '!map:ActiveSupport::HashWithIndifferentAccess'
        yaml_loader = yaml.SafeLoader

        @classmethod
        def from_yaml(cls, loader, node):
            return loader.construct_mapping(node, cls)
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = article_test
import shopify
from test_helper import TestCase

class ArticleTest(TestCase):

    def test_create_article(self):
        self.fake("blogs/1008414260/articles", method='POST', body=self.load_fixture('article'), headers={'Content-type': 'application/json'})
        article = shopify.Article({'blog_id':1008414260})
        article.save()
        self.assertEqual("First Post", article.title)

    def test_get_article(self):
        self.fake('articles/6242736', method='GET', body=self.load_fixture('article'))
        article = shopify.Article.find(6242736)
        self.assertEqual("First Post", article.title)

    def test_update_article(self):
        self.fake('articles/6242736', method='GET', body=self.load_fixture('article'))
        article = shopify.Article.find(6242736)

        self.fake('articles/6242736', method='PUT', body=self.load_fixture('article'), headers={'Content-type': 'application/json'})
        article.save()

    def test_get_articles(self):
        self.fake("articles", method='GET', body=self.load_fixture('articles'))
        articles = shopify.Article.find()
        self.assertEqual(3, len(articles))

    def test_get_articles_namespaced(self):
        self.fake("blogs/1008414260/articles", method='GET', body=self.load_fixture('articles'))
        articles = shopify.Article.find(blog_id=1008414260)
        self.assertEqual(3, len(articles))

    def test_get_article_namespaced(self):
        self.fake("blogs/1008414260/articles/6242736", method='GET', body=self.load_fixture('article'))
        article = shopify.Article.find(6242736, blog_id=1008414260)
        self.assertEqual("First Post", article.title)

    def test_get_authors(self):
        self.fake("articles/authors", method='GET', body=self.load_fixture('authors'))
        authors = shopify.Article.authors()
        self.assertEqual("Shopify", authors[0])
        self.assertEqual("development shop", authors[-1])

    def test_get_authors_for_blog_id(self):
        self.fake("blogs/1008414260/articles/authors", method='GET', body=self.load_fixture('authors'))
        authors = shopify.Article.authors(blog_id=1008414260)
        self.assertEqual(3, len(authors))

    def test_get_tags(self):
        self.fake("articles/tags", method='GET', body=self.load_fixture('tags'))
        tags = shopify.Article.tags()
        self.assertEqual("consequuntur", tags[0])
        self.assertEqual("repellendus", tags[-1])

    def test_get_tags_for_blog_id(self):
        self.fake("blogs/1008414260/articles/tags", method='GET', body=self.load_fixture('tags'))
        tags = shopify.Article.tags(blog_id=1008414260)
        self.assertEqual("consequuntur", tags[0])
        self.assertEqual("repellendus", tags[-1])

    def test_get_popular_tags(self):
        self.fake("articles/tags.json?limit=1&popular=1", extension=False, method='GET', body=self.load_fixture('tags'))
        tags = shopify.Article.tags(popular=1, limit=1)
        self.assertEqual(3, len(tags))

########NEW FILE########
__FILENAME__ = asset_test
import shopify
from test_helper import TestCase

class AssetTest(TestCase):

    def test_get_assets(self):
        self.fake("assets", method='GET', body=self.load_fixture('assets'))
        v = shopify.Asset.find()

    def test_get_asset(self):
        self.fake("assets.json?asset%5Bkey%5D=templates%2Findex.liquid", extension=False, method='GET', body=self.load_fixture('asset'))
        v = shopify.Asset.find('templates/index.liquid')

    def test_update_asset(self):
        self.fake("assets.json?asset%5Bkey%5D=templates%2Findex.liquid", extension=False, method='GET', body=self.load_fixture('asset'))
        v = shopify.Asset.find('templates/index.liquid')

        self.fake("assets", method='PUT', body=self.load_fixture('asset'), headers={'Content-type': 'application/json'})
        v.save()

    def test_get_assets_namespaced(self):
        self.fake("themes/1/assets", method='GET', body=self.load_fixture('assets'))
        v = shopify.Asset.find(theme_id = 1)

    def test_get_asset_namespaced(self):
        self.fake("themes/1/assets.json?asset%5Bkey%5D=templates%2Findex.liquid&theme_id=1", extension=False, method='GET', body=self.load_fixture('asset'))
        v = shopify.Asset.find('templates/index.liquid', theme_id=1)

    def test_update_asset_namespaced(self):
        self.fake("themes/1/assets.json?asset%5Bkey%5D=templates%2Findex.liquid&theme_id=1", extension=False, method='GET', body=self.load_fixture('asset'))
        v = shopify.Asset.find('templates/index.liquid', theme_id=1)

        self.fake("themes/1/assets", method='PUT', body=self.load_fixture('asset'), headers={'Content-type': 'application/json'})
        v.save()

    def test_delete_asset_namespaced(self):
        self.fake("themes/1/assets.json?asset%5Bkey%5D=templates%2Findex.liquid&theme_id=1", extension=False, method='GET', body=self.load_fixture('asset'))
        v = shopify.Asset.find('templates/index.liquid', theme_id=1)

        self.fake("themes/1/assets.json?asset%5Bkey%5D=templates%2Findex.liquid", extension=False, method='DELETE', body="{}")
        v.destroy()

########NEW FILE########
__FILENAME__ = base_test
import shopify
from test_helper import TestCase
from pyactiveresource.activeresource import ActiveResource
from mock import patch
import threading

class BaseTest(TestCase):

    @classmethod
    def setUpClass(self):
        self.session1 = shopify.Session('shop1.myshopify.com', 'token1')
        self.session2 = shopify.Session('shop2.myshopify.com', 'token2')

    def setUp(self):
        super(BaseTest, self).setUp()

    def tearDown(self):
        shopify.ShopifyResource.clear_session()

    def test_activate_session_should_set_site_and_headers_for_given_session(self):
        shopify.ShopifyResource.activate_session(self.session1)

        self.assertIsNone(ActiveResource.site)
        self.assertEqual('https://shop1.myshopify.com/admin', shopify.ShopifyResource.site)
        self.assertEqual('https://shop1.myshopify.com/admin', shopify.Shop.site)
        self.assertIsNone(ActiveResource.headers)
        self.assertEqual('token1', shopify.ShopifyResource.headers['X-Shopify-Access-Token'])
        self.assertEqual('token1', shopify.Shop.headers['X-Shopify-Access-Token'])

    def test_clear_session_should_clear_site_and_headers_from_Base(self):
        shopify.ShopifyResource.activate_session(self.session1)
        shopify.ShopifyResource.clear_session()

        self.assertIsNone(ActiveResource.site)
        self.assertIsNone(shopify.ShopifyResource.site)
        self.assertIsNone(shopify.Shop.site)

        self.assertIsNone(ActiveResource.headers)
        self.assertFalse('X-Shopify-Access-Token' in shopify.ShopifyResource.headers)
        self.assertFalse('X-Shopify-Access-Token' in shopify.Shop.headers)

    def test_activate_session_with_one_session_then_clearing_and_activating_with_another_session_shoul_request_to_correct_shop(self):
        shopify.ShopifyResource.activate_session(self.session1)
        shopify.ShopifyResource.clear_session
        shopify.ShopifyResource.activate_session(self.session2)

        self.assertIsNone(ActiveResource.site)
        self.assertEqual('https://shop2.myshopify.com/admin', shopify.ShopifyResource.site)
        self.assertEqual('https://shop2.myshopify.com/admin', shopify.Shop.site)

        self.assertIsNone(ActiveResource.headers)
        self.assertEqual('token2', shopify.ShopifyResource.headers['X-Shopify-Access-Token'])
        self.assertEqual('token2', shopify.Shop.headers['X-Shopify-Access-Token'])

    def test_delete_should_send_custom_headers_with_request(self):
        shopify.ShopifyResource.activate_session(self.session1)

        org_headers=shopify.ShopifyResource.headers
        shopify.ShopifyResource.set_headers({'X-Custom': 'abc'})

        with patch('shopify.ShopifyResource.connection.delete') as mock:
            shopify.ShopifyResource.delete('1')
            mock.assert_called_with('/admin/shopify_resources/1.json', {'X-Custom': 'abc'})

        shopify.ShopifyResource.set_headers(org_headers)

    def test_headers_includes_user_agent(self):
        self.assertTrue('User-Agent' in shopify.ShopifyResource.headers)
        t = threading.Thread(target=lambda: self.assertTrue('User-Agent' in shopify.ShopifyResource.headers))
        t.start()
        t.join()

    def test_headers_is_thread_safe(self):
        def testFunc():
            shopify.ShopifyResource.headers['X-Custom'] = 'abc'
            self.assertTrue('X-Custom' in shopify.ShopifyResource.headers)

        t1 = threading.Thread(target=testFunc)
        t1.start()
        t1.join()

        t2 = threading.Thread(target=lambda: self.assertFalse('X-Custom' in shopify.ShopifyResource.headers))
        t2.start()
        t2.join()

########NEW FILE########
__FILENAME__ = blog_test
import shopify
from test_helper import TestCase

class BlogTest(TestCase):
    
    def test_blog_creation(self):
        self.fake('blogs', method='POST', code=202, body=self.load_fixture('blog'), headers={'Content-type': 'application/json'})
        blog = shopify.Blog.create({'title': "Test Blog"})
        self.assertEqual("Test Blog", blog.title)

########NEW FILE########
__FILENAME__ = carrier_service_test
import shopify
from test_helper import TestCase

class CarrierServiceTest(TestCase):
    def test_create_new_carrier_service(self):
        self.fake("carrier_services", method='POST', body=self.load_fixture('carrier_service'), headers={'Content-type': 'application/json'})

        carrier_service = shopify.CarrierService.create({'name': "Some Postal Service"})
        self.assertEqual("Some Postal Service", carrier_service.name)

    def test_get_carrier_service(self):
        self.fake("carrier_services/123456", method='GET', body=self.load_fixture('carrier_service'))

        carrier_service = shopify.CarrierService.find(123456)
        self.assertEqual("Some Postal Service", carrier_service.name)

########NEW FILE########
__FILENAME__ = cart_test
import shopify
from test_helper import TestCase

class CartTest(TestCase):
  
  def test_all_should_return_all_carts(self):
    self.fake('carts')
    carts = shopify.Cart.find()
    self.assertEqual(2, len(carts))
    self.assertEqual(2, carts[0].id)
    self.assertEqual("3eed8183d4281db6ea82ee2b8f23e9cc", carts[0].token)
    self.assertEqual(1, len(carts[0].line_items))
    self.assertEqual('test', carts[0].line_items[0].title)

########NEW FILE########
__FILENAME__ = customer_saved_search_test
import shopify
from test_helper import TestCase

class CustomerSavedSearchTest(TestCase):
    
    def setUp(self):
        super(CustomerSavedSearchTest, self).setUp()
        self.load_customer_saved_search()

    def test_get_customers_from_customer_saved_search(self):
        self.fake('customer_saved_searches/8899730/customers', body=self.load_fixture('customer_saved_search_customers'))
        self.assertEqual(1, len(self.customer_saved_search.customers()))
        self.assertEqual(112223902, self.customer_saved_search.customers()[0].id)

    def test_get_customers_from_customer_saved_search_with_params(self):
        self.fake('customer_saved_searches/8899730/customers.json?limit=1', extension=False, body=self.load_fixture('customer_saved_search_customers'))
        customers = self.customer_saved_search.customers(limit = 1)
        self.assertEqual(1, len(customers))
        self.assertEqual(112223902, customers[0].id)

    def load_customer_saved_search(self):
        self.fake('customer_saved_searches/8899730', body=self.load_fixture('customer_saved_search'))
        self.customer_saved_search = shopify.CustomerSavedSearch.find(8899730)

########NEW FILE########
__FILENAME__ = fulfillment_service_test
import shopify
from test_helper import TestCase

class FulfillmentServiceTest(TestCase):
    def test_create_new_fulfillment_service(self):
        self.fake("fulfillment_services", method='POST', body=self.load_fixture('fulfillment_service'), headers={'Content-type': 'application/json'})

        fulfillment_service = shopify.FulfillmentService.create({'name': "SomeService"})
        self.assertEqual("SomeService", fulfillment_service.name)

    def test_get_fulfillment_service(self):
        self.fake("fulfillment_services/123456", method='GET', body=self.load_fixture('fulfillment_service'))

        fulfillment_service = shopify.FulfillmentService.find(123456)
        self.assertEqual("SomeService", fulfillment_service.name)

########NEW FILE########
__FILENAME__ = fulfillment_test
import shopify
from test_helper import TestCase
from pyactiveresource.activeresource import ActiveResource

class FulFillmentTest(TestCase):
  
    def setUp(self):
        super(FulFillmentTest, self).setUp()
        self.fake("orders/450789469/fulfillments/255858046", method='GET', body=self.load_fixture('fulfillment'))

    def test_able_to_complete_fulfillment(self):
        fulfillment = shopify.Fulfillment.find(255858046, order_id=450789469)

        success = self.load_fixture('fulfillment')
        success = success.replace('pending','success')
        self.fake("orders/450789469/fulfillments/255858046/complete", method='POST', headers={'Content-length':'0', 'Content-type': 'application/json'}, body=success)

        self.assertEqual('pending', fulfillment.status)
        fulfillment.complete()
        self.assertEqual('success', fulfillment.status)
    
    def test_able_to_cancel_fulfillment(self):
        fulfillment = shopify.Fulfillment.find(255858046, order_id=450789469)

        cancelled = self.load_fixture('fulfillment')
        cancelled = cancelled.replace('pending', 'cancelled')
        self.fake("orders/450789469/fulfillments/255858046/cancel", method='POST', headers={'Content-length':'0', 'Content-type': 'application/json'}, body=cancelled)

        self.assertEqual('pending', fulfillment.status)
        fulfillment.cancel()
        self.assertEqual('cancelled', fulfillment.status)

########NEW FILE########
__FILENAME__ = image_test
import shopify
from test_helper import TestCase

class ImageTest(TestCase):

  def test_create_image(self):
    self.fake("products/632910392/images", method='POST', body=self.load_fixture('image'), headers={'Content-type': 'application/json'})
    image = shopify.Image({'product_id':632910392})
    image.position = 1
    image.attachment = "R0lGODlhbgCMAPf/APbr48VySrxTO7IgKt2qmKQdJeK8lsFjROG5p/nz7Zg3MNmnd7Q1MLNVS9GId71hSJMZIuzTu4UtKbeEeakhKMl8U8WYjfr18YQaIbAf=="
    image.save()

    self.assertEqual('http://cdn.shopify.com/s/files/1/0006/9093/3842/products/ipod-nano.png?v=1389388540', image.src)
    self.assertEqual(850703190, image.id)

  def test_get_images(self):
    self.fake("products/632910392/images", method='GET', body=self.load_fixture('images'))
    image = shopify.Image.find(product_id=632910392)
    self.assertEqual(2, len(image))

  def test_get_image(self):
    self.fake("products/632910392/images/850703190", method='GET', body=self.load_fixture('image'))
    image = shopify.Image.find(850703190, product_id=632910392)
    self.assertEqual(850703190, image.id)

########NEW FILE########
__FILENAME__ = order_risk_test
import shopify
from test_helper import TestCase

class OrderRiskTest(TestCase):

  def test_create_order_risk(self):
    self.fake("orders/450789469/risks", method='POST', body= self.load_fixture('order_risk'), headers={'Content-type': 'application/json'})
    v = shopify.OrderRisk({'order_id':450789469})
    v.message = "This order was placed from a proxy IP"
    v.recommendation = "cancel"
    v.score = "1.0"
    v.source = "External"
    v.merchant_message = "This order was placed from a proxy IP"
    v.display = True
    v.cause_cancel = True
    v.save()

    self.assertEqual(284138680, v.id)

  def test_get_order_risks(self):
    self.fake("orders/450789469/risks", method='GET', body= self.load_fixture('order_risks'))
    v = shopify.OrderRisk.find(order_id=450789469)
    self.assertEqual(2, len(v))

  def test_get_order_risk(self):
    self.fake("orders/450789469/risks/284138680", method='GET', body= self.load_fixture('order_risk'))
    v = shopify.OrderRisk.find(284138680, order_id=450789469)
    self.assertEqual(284138680, v.id)

  def test_delete_order_risk(self):
    self.fake("orders/450789469/risks/284138680", method='GET', body= self.load_fixture('order_risk'))
    self.fake("orders/450789469/risks/284138680", method='DELETE', body="destroyed")
    v = shopify.OrderRisk.find(284138680, order_id=450789469)
    v.destroy()

  def test_delete_order_risk(self):
    self.fake("orders/450789469/risks/284138680", method='GET', body= self.load_fixture('order_risk'))
    self.fake("orders/450789469/risks/284138680", method='PUT', body= self.load_fixture('order_risk'), headers={'Content-type': 'application/json'})

    v = shopify.OrderRisk.find(284138680, order_id=450789469)
    v.position = 3
    v.save()

########NEW FILE########
__FILENAME__ = order_test
import shopify
from test_helper import TestCase
from pyactiveresource.activeresource import ActiveResource
from pyactiveresource.util import xml_to_dict

class OrderTest(TestCase):

    def test_should_be_loaded_correctly_from_order_xml(self):
        order_xml = """<?xml version="1.0" encoding="UTF-8"?>
          <order>
            <note-attributes type="array">
              <note-attribute>
                <name>size</name>
                <value>large</value>
              </note-attribute>
            </note-attributes>
          </order>"""
        order = shopify.Order(xml_to_dict(order_xml)["order"])

        self.assertEqual(1, len(order.note_attributes))

        note_attribute = order.note_attributes[0]
        self.assertEqual("size", note_attribute.name)
        self.assertEqual("large", note_attribute.value)

    def test_should_be_able_to_add_note_attributes_to_an_order(self):
        order = shopify.Order()
        order.note_attributes = []
        order.note_attributes.append(shopify.NoteAttribute({'name': "color", 'value': "blue"}))

        order_xml = xml_to_dict(order.to_xml())
        note_attributes = order_xml["order"]["note_attributes"]
        self.assertTrue(isinstance(note_attributes, list))

        attribute = note_attributes[0]
        self.assertEqual("color", attribute["name"])
        self.assertEqual("blue", attribute["value"])

    def test_get_order(self):
        self.fake('orders/450789469', method='GET', body=self.load_fixture('order'))
        order = shopify.Order.find(450789469)
        self.assertEqual('bob.norman@hostmail.com', order.email)

    def test_get_order_transaction(self):
        self.fake('orders/450789469', method='GET', body=self.load_fixture('order'))
        order = shopify.Order.find(450789469)
        self.fake('orders/450789469/transactions', method='GET', body=self.load_fixture('transaction'))
        transactions = order.transactions()
        self.assertEqual("409.94", transactions[0].amount)

########NEW FILE########
__FILENAME__ = product_test
import shopify
from test_helper import TestCase

class ProductTest(TestCase):

    def setUp(self):
        super(ProductTest, self).setUp()

        self.fake("products/632910392", body=self.load_fixture('product'))
        self.product = shopify.Product.find(632910392)

    def test_add_metafields_to_product(self):
        self.fake("products/632910392/metafields", method='POST', code=201, body=self.load_fixture('metafield'), headers={'Content-type': 'application/json'})

        field = self.product.add_metafield(shopify.Metafield({'namespace': "contact", 'key': "email", 'value': "123@example.com", 'value_type': "string"}))

        self.assertFalse(field.is_new())
        self.assertEqual("contact", field.namespace)
        self.assertEqual("email", field.key)
        self.assertEqual("123@example.com", field.value)

    def test_get_metafields_for_product(self):
        self.fake("products/632910392/metafields", body=self.load_fixture('metafields'))

        metafields = self.product.metafields()

        self.assertEqual(2, len(metafields))
        for field in metafields:
            self.assertTrue(isinstance(field, shopify.Metafield))

    def test_update_loaded_variant(self):
        self.fake("products/632910392/variants/808950810", method='PUT', code=200, body=self.load_fixture('variant'))

        variant = self.product.variants[0]
        variant.price = "0.50"
        variant.save

    def test_add_variant_to_product(self):
        self.fake("products/632910392/variants", method='POST', body=self.load_fixture('variant'), headers={'Content-type': 'application/json'})
        self.fake("products/632910392/variants/808950810", method='PUT', code=200, body=self.load_fixture('variant'), headers={'Content-type': 'application/json'})
        v = shopify.Variant()
        self.assertTrue(self.product.add_variant(v))

########NEW FILE########
__FILENAME__ = recurring_charge_test
import shopify
from test_helper import TestCase

class RecurringApplicationChargeTest(TestCase):
    def test_activate_charge(self):
        # Just check that calling activate doesn't raise an exception.
        self.fake("recurring_application_charges/35463/activate", method='POST',headers={'Content-length':'0', 'Content-type': 'application/json'}, body=" ")
        charge = shopify.RecurringApplicationCharge({'id': 35463})
        charge.activate()

########NEW FILE########
__FILENAME__ = session_test
import shopify
from test_helper import TestCase
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import time

class SessionTest(TestCase):

    def test_not_be_valid_without_a_url(self):
        session = shopify.Session("", "any-token")
        self.assertFalse(session.valid)

    def test_not_be_valid_without_token(self):
        session = shopify.Session("testshop.myshopify.com")
        self.assertFalse(session.valid)

    def test_be_valid_with_any_token_and_any_url(self):
        session = shopify.Session("testshop.myshopify.com", "any-token")
        self.assertTrue(session.valid)

    def test_not_raise_error_without_params(self):
        session = shopify.Session("testshop.myshopify.com", "any-token")

    def test_raise_error_if_params_passed_but_signature_omitted(self):
        with self.assertRaises(shopify.ValidationException):
            session = shopify.Session("testshop.myshopify.com")
            token = session.request_token({'code':'any_code', 'foo': 'bar', 'timestamp':'1234'})

    def test_setup_api_key_and_secret_for_all_sessions(self):
        shopify.Session.setup(api_key="My test key", secret="My test secret")
        self.assertEqual("My test key", shopify.Session.api_key)
        self.assertEqual("My test secret", shopify.Session.secret)

    def test_use_https_protocol_by_default_for_all_sessions(self):
        self.assertEqual('https', shopify.Session.protocol)

    def test_temp_reset_shopify_ShopifyResource_site_to_original_value(self):
        shopify.Session.setup(api_key="key", secret="secret")
        session1 = shopify.Session('fakeshop.myshopify.com', 'token1')
        shopify.ShopifyResource.activate_session(session1)

        assigned_site = ""
        with shopify.Session.temp("testshop.myshopify.com", "any-token"):
            assigned_site = shopify.ShopifyResource.site

        self.assertEqual('https://testshop.myshopify.com/admin', assigned_site)
        self.assertEqual('https://fakeshop.myshopify.com/admin', shopify.ShopifyResource.site)

    def test_temp_reset_shopify_ShopifyResource_site_to_original_value_when_using_a_non_standard_port(self):
        shopify.Session.setup(api_key="key", secret="secret")
        session1 = shopify.Session('fakeshop.myshopify.com:3000', 'token1')
        shopify.ShopifyResource.activate_session(session1)

        assigned_site = ""
        with shopify.Session.temp("testshop.myshopify.com", "any-token"):
            assigned_site = shopify.ShopifyResource.site

        self.assertEqual('https://testshop.myshopify.com/admin', assigned_site)
        self.assertEqual('https://fakeshop.myshopify.com:3000/admin', shopify.ShopifyResource.site)

    def test_temp_works_without_currently_active_session(self):
        shopify.ShopifyResource.clear_session()

        assigned_site = ""
        with shopify.Session.temp("testshop.myshopify.com", "any-token"):
            assigned_site = shopify.ShopifyResource.site

        self.assertEqual('https://testshop.myshopify.com/admin', assigned_site)
        self.assertEqual('https://None/admin', shopify.ShopifyResource.site)

    def test_create_permission_url_returns_correct_url_with_single_scope_no_redirect_uri(self):
        shopify.Session.setup(api_key="My_test_key", secret="My test secret")
        session = shopify.Session('http://localhost.myshopify.com')
        scope = ["write_products"]
        permission_url = session.create_permission_url(scope)
        self.assertEqual("https://localhost.myshopify.com/admin/oauth/authorize?scope=write_products&client_id=My_test_key", permission_url)

    def test_create_permission_url_returns_correct_url_with_single_scope_and_redirect_uri(self):
        shopify.Session.setup(api_key="My_test_key", secret="My test secret")
        session = shopify.Session('http://localhost.myshopify.com')
        scope = ["write_products"]
        permission_url = session.create_permission_url(scope, "my_redirect_uri.com")
        self.assertEqual("https://localhost.myshopify.com/admin/oauth/authorize?scope=write_products&redirect_uri=my_redirect_uri.com&client_id=My_test_key", permission_url)

    def test_create_permission_url_returns_correct_url_with_dual_scope_no_redirect_uri(self):
        shopify.Session.setup(api_key="My_test_key", secret="My test secret")
        session = shopify.Session('http://localhost.myshopify.com')
        scope = ["write_products","write_customers"]
        permission_url = session.create_permission_url(scope)
        self.assertEqual("https://localhost.myshopify.com/admin/oauth/authorize?scope=write_products%2Cwrite_customers&client_id=My_test_key", permission_url)

    def test_create_permission_url_returns_correct_url_with_no_scope_no_redirect_uri(self):
        shopify.Session.setup(api_key="My_test_key", secret="My test secret")
        session = shopify.Session('http://localhost.myshopify.com')
        scope = []
        permission_url = session.create_permission_url(scope)
        self.assertEqual("https://localhost.myshopify.com/admin/oauth/authorize?scope=&client_id=My_test_key", permission_url)

    def test_raise_exception_if_code_invalid_in_request_token(self):
        shopify.Session.setup(api_key="My test key", secret="My test secret")
        session = shopify.Session('http://localhost.myshopify.com')
        self.fake(None, url='https://localhost.myshopify.com/admin/oauth/access_token', method='POST', code=404, body='{"error" : "invalid_request"}', has_user_agent=False)

        with self.assertRaises(shopify.ValidationException):
            session.request_token({'code':'any-code', 'timestamp':'1234'})

        self.assertFalse(session.valid)

    def test_return_site_for_session(self):
        session = shopify.Session("testshop.myshopify.com", "any-token")
        self.assertEqual("https://testshop.myshopify.com/admin", session.site)

    def test_return_token_if_signature_is_valid(self):
        shopify.Session.secret='secret'
        params = {'code': 'any-code', 'timestamp': time.time()}
        sorted_params = self.make_sorted_params(params)
        signature = md5(shopify.Session.secret + sorted_params).hexdigest()
        params['signature'] = signature

        self.fake(None, url='https://localhost.myshopify.com/admin/oauth/access_token', method='POST', body='{"access_token" : "token"}', has_user_agent=False)
        session = shopify.Session('http://localhost.myshopify.com')
        token = session.request_token(params)
        self.assertEqual("token", token)

    def test_raise_error_if_signature_does_not_match_expected(self):
        shopify.Session.secret='secret'
        params = {'foo': 'hello', 'timestamp': time.time()}
        sorted_params = self.make_sorted_params(params)
        signature = md5(shopify.Session.secret + sorted_params).hexdigest()
        params['signature'] = signature
        params['bar'] = 'world'
        params['code'] = 'code'

        with self.assertRaises(shopify.ValidationException):
            session = shopify.Session('http://localhost.myshopify.com')
            session = session.request_token(params)

    def test_raise_error_if_timestamp_is_too_old(self):
        shopify.Session.secret='secret'
        one_day = 24 * 60 * 60
        params = {'code': 'any-code', 'timestamp': time.time()-(2*one_day)}
        sorted_params = self.make_sorted_params(params)
        signature = md5(shopify.Session.secret + sorted_params).hexdigest()
        params['signature'] = signature

        with self.assertRaises(shopify.ValidationException):
            session = shopify.Session('http://localhost.myshopify.com')
            session = session.request_token(params)


    def make_sorted_params(self, params):
        sorted_params = ""
        for k in sorted(params.keys()):
            if k != "signature":
                sorted_params += k + "=" + str(params[k])
        return sorted_params

########NEW FILE########
__FILENAME__ = shop_test
import shopify
from test_helper import TestCase

class ShopTest(TestCase):
    def setUp(self):
        super(ShopTest, self).setUp()
        self.fake("shop")
        self.shop = shopify.Shop.current()

    def test_current_should_return_current_shop(self):
        self.assertTrue(isinstance(self.shop,shopify.Shop))
        self.assertEqual("Apple Computers", self.shop.name)
        self.assertEqual("apple.myshopify.com", self.shop.myshopify_domain)
        self.assertEqual(690933842, self.shop.id)
        self.assertEqual("2007-12-31T19:00:00-05:00", self.shop.created_at)
        self.assertIsNone(self.shop.tax_shipping)

    def test_get_metafields_for_shop(self):
        self.fake("metafields")

        metafields = self.shop.metafields()

        self.assertEqual(2, len(metafields))
        for field in metafields:
            self.assertTrue(isinstance(field, shopify.Metafield))

    def test_add_metafield(self):
        self.fake("metafields", method='POST', code=201, body=self.load_fixture('metafield'), headers={'Content-type': 'application/json'})

        field = self.shop.add_metafield( shopify.Metafield({'namespace': "contact", 'key': "email", 'value': "123@example.com", 'value_type': "string"}))

        self.assertFalse(field.is_new())
        self.assertEqual("contact", field.namespace)
        self.assertEqual("email", field.key)
        self.assertEqual("123@example.com", field.value)

    def test_events(self):
        self.fake("events")

        events = self.shop.events()

        self.assertEqual(3, len(events))
        for event in events:
            self.assertTrue(isinstance(event, shopify.Event))

########NEW FILE########
__FILENAME__ = test_helper
import os
import sys
import unittest
from pyactiveresource.activeresource import ActiveResource
from pyactiveresource.testing import http_fake
import shopify

class TestCase(unittest.TestCase):

    def setUp(self):
        ActiveResource.site = None
        ActiveResource.headers=None

        shopify.ShopifyResource.clear_session()
        shopify.ShopifyResource.site = "https://this-is-my-test-show.myshopify.com/admin"
        shopify.ShopifyResource.password = None
        shopify.ShopifyResource.user = None

        http_fake.initialize()
        self.http = http_fake.TestHandler
        self.http.set_response(Exception('Bad request'))
        self.http.site = 'https://this-is-my-test-show.myshopify.com'

    def load_fixture(self, name, format='json'):
        return open(os.path.dirname(__file__)+'/fixtures/%s.%s' % (name, format), 'r').read()

    def fake(self, endpoint, **kwargs):
        body = kwargs.pop('body', None) or self.load_fixture(endpoint)
        format = kwargs.pop('format','json')
        method = kwargs.pop('method','GET')

        if ('extension' in kwargs and not kwargs['extension']):
            extension = ""
        else:
            extension = ".%s" % (kwargs.pop('extension', 'json'))

        url = "https://this-is-my-test-show.myshopify.com/admin/%s%s" % (endpoint, extension)
        try:
           url = kwargs['url']
        except KeyError:
           pass

        headers = {}
        if kwargs.pop('has_user_agent', True):
            userAgent = 'ShopifyPythonAPI/%s Python/%s' % (shopify.VERSION, sys.version.split(' ', 1)[0])
            headers['User-agent'] = userAgent

        try:
            headers.update(kwargs['headers'])
        except KeyError:
           pass

        code = kwargs.pop('code', 200)

        self.http.respond_to(
          method, url, headers, body=body, code=code)

########NEW FILE########
__FILENAME__ = transaction_test
import shopify
from test_helper import TestCase

class TransactionTest(TestCase):
    def setUp(self):
        super(TransactionTest, self).setUp()
        self.fake("orders/450789469/transactions/389404469", method='GET', body=self.load_fixture('transaction'))

    def test_should_find_a_specific_transaction(self):
        transaction = shopify.Transaction.find(389404469, order_id=450789469)
        self.assertEqual("409.94", transaction.amount)

########NEW FILE########
__FILENAME__ = variant_test
import shopify
from test_helper import TestCase

class VariantTest(TestCase):

    def test_get_variants(self):
        self.fake("products/632910392/variants", method='GET', body=self.load_fixture('variants'))
        v = shopify.Variant.find(product_id = 632910392)

    def test_get_variant_namespaced(self):
        self.fake("products/632910392/variants/808950810", method='GET', body=self.load_fixture('variant'))
        v = shopify.Variant.find(808950810, product_id = 632910392)

    def test_update_variant_namespace(self):
        self.fake("products/632910392/variants/808950810", method='GET', body=self.load_fixture('variant'))
        v = shopify.Variant.find(808950810, product_id = 632910392)

        self.fake("products/632910392/variants/808950810", method='PUT', body=self.load_fixture('variant'), headers={'Content-type': 'application/json'})
        v.save()

    def test_create_variant(self):
        self.fake("products/632910392/variants", method='POST', body=self.load_fixture('variant'), headers={'Content-type': 'application/json'})
        v = shopify.Variant({'product_id':632910392})
        v.save()

    def test_create_variant_then_add_parent_id(self):
        self.fake("products/632910392/variants", method='POST', body=self.load_fixture('variant'), headers={'Content-type': 'application/json'})
        v = shopify.Variant()
        v.product_id = 632910392
        v.save()
        
    def test_get_variant(self):
        self.fake("variants/808950810", method='GET', body=self.load_fixture('variant'))
        v = shopify.Variant.find(808950810)

########NEW FILE########
