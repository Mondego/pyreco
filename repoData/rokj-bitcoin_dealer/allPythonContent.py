__FILENAME__ = functions
import datetime


def console_log(message):
    now = datetime.datetime.now()
    print "%s - %s" % (now.strftime("%Y-%m-%d %H:%M:%S"), message)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _

class Skeleton(models.Model):
    datetime_created = models.DateTimeField(auto_now=False, auto_now_add=True, null=False, blank=False)
    datetime_updated = models.DateTimeField(auto_now=True, auto_now_add=True, null=False, blank=False)
    datetime_deleted = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

class SkeletonU(Skeleton):
    '''
    Skeleton model with Users included.
    '''
    created_by = models.ForeignKey(User, related_name='%(app_label)s_%(class)s_created_by', null=False)
    updated_by = models.ForeignKey(User, related_name='%(app_label)s_%(class)s_updated_by', null=True, blank=True)

    class Meta:
        abstract = True

class Settings(SkeletonU):
    key = models.CharField(_('Key'), max_length=50, null=False, blank=False, unique=True)
    value = models.CharField(_('Value'), max_length=50)
    description = models.TextField(_('Description'), null=True, blank=True)

    __unicode__ = lambda self: u'%s = %s' % (self.key, self.value)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.forms import ModelForm
from django.forms.widgets import Select
from models import Trade, TradeLog, Currency, Exchange

class ExchangeAdmin(admin.ModelAdmin):
    exclude = ('created_by', 'updated_by', 'datetime_deleted', )
    #readonly_fields = ('name', )

    def save_model(self, request, obj, form, change):
        if obj.active == False:
            my_trades = Trade.objects.filter(active=True)

        if not change:
            obj.created_by = request.user
        else:
            obj.updated_by = request.user

        obj.save()

    # Kudos to http://www.b-list.org/weblog/2008/dec/24/admin/
    def has_change_permission(self, request, obj=None):
        has_class_permission = super(ExchangeAdmin, self).has_change_permission(request, obj)
        if not has_class_permission:
            return False
        if obj is not None and not request.user.is_superuser and request.user.id != obj.created_by.id:
            return False
        return True

    # Kudos to http://www.b-list.org/weblog/2008/dec/24/admin/
    def queryset(self, request):
        if request.user.is_superuser:
            return Exchange.objects.all()
        return Exchange.objects.filter(created_by = request.user)

class CurrencyAdmin(admin.ModelAdmin):
    exclude = ('created_by', 'updated_by', 'datetime_deleted', )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        else:
            obj.updated_by = request.user

        obj.save()

    # Kudos to http://www.b-list.org/weblog/2008/dec/24/admin/
    def has_change_permission(self, request, obj=None):
        has_class_permission = super(CurrencyAdmin, self).has_change_permission(request, obj)
        if not has_class_permission:
            return False
        if obj is not None and not request.user.is_superuser and request.user.id != obj.created_by.id:
            return False
        return True

    # Kudos to http://www.b-list.org/weblog/2008/dec/24/admin/
    def queryset(self, request):
        if request.user.is_superuser:
            return Currency.objects.all()
        return Currency.objects.filter(created_by = request.user)

class TradeAdminForm(ModelForm):
    class Meta:
        model = Trade

    def __init__(self, *args, **kwargs):
        super(TradeAdminForm, self).__init__(*args, **kwargs)
        self.fields["related"].widget = Select()
        self.fields["related"].queryset = Trade.objects.order_by('-id',)

class TradeAdmin(admin.ModelAdmin):
    exclude = ('user', 'created_by', 'updated_by', 'datetime_deleted', )
    list_display = ('pk', '_buy_or_sell', '_watch_price', 'price', 'amount', 'approximate_total', 'total', 'currency', 'exchange', 'status', 'related', 'completed', 'active', 'datetime_updated', )
    fields = ('watch_price', 'lp_higher', 'buy_or_sell', 'price', 'amount', 'total', 'currency', 'related', 'exchange', 'exchange_oid', 'status', 'completed', 'active', )
    ordering = ('-id',)
    readonly_fields = ( 'exchange_oid', 'completed', 'total',)
    form = TradeAdminForm

    def _watch_price(self, obj):
        if obj.lp_higher == True:
            return _('if price is') + ' >= %s' % (obj.watch_price)
        else:
            return _('if price is') + ' <= %s' % (obj.watch_price)
    _watch_price.short_description = 'Price to watch'
    _watch_price.admin_order_field = 'watch_price'

    def _buy_or_sell(self, obj):
        if obj.buy_or_sell == True:
            return _('Buying')
        else:
            return _('Selling')
    _buy_or_sell.short_description = 'Buying or selling'
    _buy_or_sell.admin_order_field = 'buy_or_sell'

    # Kudos to http://www.b-list.org/weblog/2008/dec/24/admin/
    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
            obj.created_by = request.user
        else:
            obj.updated_by = request.user

        obj.save()

    # Kudos to http://www.b-list.org/weblog/2008/dec/24/admin/
    def has_change_permission(self, request, obj=None):
        has_class_permission = super(TradeAdmin, self).has_change_permission(request, obj)
        if not has_class_permission:
            return False
        if obj is not None and not request.user.is_superuser and request.user.id != obj.created_by.id:
            return False
        return True

    # Kudos to http://www.b-list.org/weblog/2008/dec/24/admin/
    def queryset(self, request):
        if request.user.is_superuser:
            return Trade.objects.all()
        return Trade.objects.filter(created_by = request.user)

class TradeLogAdmin(admin.ModelAdmin):
    list_display = ('pk', 'datetime', 'trade', 'log', 'log_desc',)

admin.site.register(Trade, TradeAdmin)
admin.site.register(TradeLog, TradeLogAdmin)
admin.site.register(Exchange, ExchangeAdmin)
admin.site.register(Currency, CurrencyAdmin)

########NEW FILE########
__FILENAME__ = bitstamp1
import re, time, hmac, hashlib

from decimal import Decimal
import requests
from common.functions import console_log
from exchange.exchange_abstract import ExchangeAbstract

class BitStamp1(ExchangeAbstract):
    """
    See:
    https://www.bitstamp.net/api/
    """

    _last_price = {}
    _order = None

    ticker_url = { "method": "GET", "url": "https://www.bitstamp.net/api/ticker/" }
    buy_url = { "method": "POST", "url": "https://www.bitstamp.net/api/buy/" }
    sell_url = { "method": "POST", "url": "https://www.bitstamp.net/api/sell/" }
    #order_url = { "method": "POST", "url": "https://data.mtgox.com/api/1/generic/private/order/result" }
    #open_orders_url = { "method": "POST", "url": "https://data.mtgox.com/api/1/generic/private/orders" }

    key = None
    secret = None
    client_id = None

    @property
    def order(self):
        return self._order

    @order.setter
    def order(self, order):
        self._order = order

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

        self._last_price = {}
        self._order = None

    def _change_currency_url(self, url, currency):
        return re.sub(r'BTC\w{3}', r'BTC' + currency, url)

    def _create_nonce(self):
        return int(time.time() * 1000000)

    def _send_request(self, url, params, extra_headers=None):
        headers = {
            'Content-type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}

        if extra_headers is not None:
            for k, v in extra_headers.iteritems():
                headers[k] = v

        if url["method"] == "GET":
            response = requests.get(url['url'], params=params, headers=headers)
        elif url["method"] == "POST":
            response = requests.post(url['url'], data=params, headers=headers)

        if response and response.status_code == requests.codes.ok:
            return response.json()

        return None

    def _to_int_price(self, price, currency):
        ret_price = None
        
        ret_price = Decimal(price).quantize(Decimal('0.01'))
            #ret_price = int(price * 100000)

        return ret_price

    def _to_int_amount(self, amount):
        amount = Decimal(amount).quantize(Decimal('0.01'))
        return amount

    def get_last_price(self, currency):
        if currency in self._last_price:
            return self._last_price[currency]

        self.ticker_url["url"] = self._change_currency_url(self.ticker_url["url"], currency)

        response = self._send_request(self.ticker_url, {})
        if response:
            self._last_price[currency] = Decimal(response[u"last"])
            return Decimal(response[u"last"])

        return None
    
    def get_orders(self):
        return None

    def buy(self, price, amount, currency):
        """
        bid == buy
        ask == sell

        Returns order ID if order was placed successfully.
        """
        if not self.key or self.key is None:
            console_log("bitstamp: key not set; check settings.py")
            return None

        if not self.secret or self.secret is None:
            console_log("bitstamp: secret not set; check settings.py")
            return None

        price = self._to_int_price(price, currency)
        amount = self._to_int_amount(amount)

        if not price or price is None:
            #console_log("there is no conversion forumla for currency %s" % (currency))

            return None

        if not amount or amount is None:
            return None

        self.buy_url["url"] = self._change_currency_url(self.buy_url["url"], currency)

        nonce = str(self._create_nonce())
        message = nonce + self.client_id + self.key
        signature = hmac.new(self.secret, msg=message, digestmod=hashlib.sha256).hexdigest().upper()

        params = {'key': self.key, 'signature': signature, 'nonce': nonce, "amount": str(amount),
                  "price": str(price)}

        response = self._send_request(self.buy_url, params)

        if response and u"id" in response:
            return response[u"id"]

        if response and u"error" in response:
            console_log("bitstamp: error returned from server with message: %s" % response[u"error"])

        return None

    def sell(self, price, amount, currency):
        """
        ask == sell
        """
        
        if not self.key or self.key is None:
            console_log("bitstamp: key not set; check settings.py")
            return None

        if not self.secret or self.secret is None:
            console_log("bitstamp: secret not set; check settings.py")
            return None

        price = self._to_int_price(price, currency)
        amount = self._to_int_amount(amount)
        
        if not price or price is None:
            #console_log("there is no conversion forumla for currency %s" % (currency))

            return None

        if not amount or amount is None: return None

        self.sell_url["url"] = self._change_currency_url(self.sell_url["url"], currency)
        
        nonce = str(self._create_nonce())
        message = nonce + self.client_id + self.key
        signature = hmac.new(self.secret, msg=message, digestmod=hashlib.sha256).hexdigest().upper()

        params = {'key': self.key, 'signature': signature, 'nonce': nonce, "amount": str(amount),
                  "price": str(price)}
       
        response = self._send_request(self.sell_url, params)
        
        if response and u"id" in response:
            return response[u"id"]

        if response and u"error" in response:
            console_log("bitstamp: error returned from server with message: %s" % response[u"error"])

        return None
    
    def get_order(self, trade):
        return None
########NEW FILE########
__FILENAME__ = mtgox
import sys, os, urllib, urllib2, time, json, hmac, hashlib, base64

class MtGox():
    """
    DEPRECATED will be. This is implementation for MtGox API version 0 which we
    do not use anymore.

    See:
    https://mtgox.com/support/tradeAPI
    https://en.bitcoin.it/wiki/MtGox/API#Authentication

    examples:
    https://mtgox.com/code/buyBTC.php?name=%s&pass=%s&amount=%s&price=%s
    https://mtgox.com/code/getOrders.php?name=%s&pass=%s
    """    

    ticker_url = "http://mtgox.com/api/0/data/ticker.php"
    buy_url = "https://mtgox.com/api/0/buyBTC.php"
    sell_url = "https://mtgox.com/api/0/sellBTC.php"
    orders_url = "https://mtgox.com/code/getOrders.php"
    balance_url = "https://mtgox.com/api/0/getFunds.php"

    username = None
    password = None
    key = None
    secret = None
    currency = None

    def __init__(self, kwargs):
        """
        We have to do this:

        self.username = username
        self.password = password
        self.key = key
        self.secret = secret
        self.currency = currency
        """

        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def _create_nonce(self):
        return int(time.time()*100)

    def _send_request(self, url, params, extra_headers = None):
        headers = { 'X_REQUESTED_WITH' :'XMLHttpRequest', 'ACCEPT': 'application/json, text/javascript, */*; q=0.01', 'User-Agent': 'Mozilla/5.0 (compatible; bitcoin dealer client; v0.2.0; using Python)' }
        if extra_headers is not None:
            for k, v in extra_headers.iteritems():
                headers[k] = v

        data = urllib.urlencode(params)
        req = urllib2.Request(url, data, headers)
        req.add_header("Content-type", "application/x-www-form-urlencoded")
        f = urllib2.urlopen(req)
        response = f.read()
        f.close()

        return json.loads(response) 

    def get_orders(self):
        params = { 'name': self.username, 'pass': self.password }
        return self._send_request(self.orders_url, params)

    def get_price(self):
        return self._send_request(self.ticker_url, {})

    def get_balance(self):
        if not self.username or self.username is None: return
        if not self.password or self.password is None: return
        if not self.key or self.key is None: return
        if not self.secret or self.secret is None: return

        params = { 'name': self.username, 'pass': self.password, 'nonce': self._create_nonce() }
        headers = { 'Rest-Key': self.key, 'Rest-Sign': hmac.new(base64.b64decode(self.secret), '&'.join(params), hashlib.sha512) }

        response = self._send_request(self.balance_url, params, headers)
        if response:
            return response

        return None

    def buy(self, price, amount):
        if not price or price is None: return
        if not amount or amount is None: return
        if not self.username or self.username is None: return
        if not self.password or self.password is None: return

        params = { 'name': self.username, 'pass': self.password, 'nonce': self._create_nonce(), 'amount': amount, 'price': price, 'Currency': self.currency }
        headers = { 'Rest-Key': self.key, 'Rest-Sign': hmac.new(base64.b64decode(self.secret), '&'.join(params), hashlib.sha512) }
        response = self._send_request(self.buy_url, params, headers)

        if response:
            return response

        return None
    
    def sell(self, price, amount):
        if not price or price is None: return
        if not amount or amount is None: return
        if not self.username or self.username is None: return
        if not self.password or self.password is None: return

        params = { 'name': self.username, 'pass': self.password, 'nonce': self._create_nonce(), 'amount': amount, 'price': price, 'Currency': self.currency }
        headers = { 'Rest-Key': self.key, 'Rest-Sign': hmac.new(base64.b64decode(self.secret), '&'.join(params), hashlib.sha512) }
        response = self._send_request(self.sell_url, params, headers)

        if response:
            return response

        return None

        

########NEW FILE########
__FILENAME__ = mtgox1
import sys, os, re, urllib, urllib3, httplib, time, json, hmac, hashlib, base64

from decimal import Decimal
from common.functions import console_log
from exchange.exchange_abstract import ExchangeAbstract, Order

class MtGox1(ExchangeAbstract):
    """
    See:
    https://en.bitcoin.it/wiki/MtGox/API
    """

    _last_price = {}
    _order = None

    ticker_url = { "method": "GET", "url": "http://data.mtgox.com/api/1/BTCUSD/ticker_fast" }
    buy_url = { "method": "POST", "url": "https://data.mtgox.com/api/1/BTCUSD/private/order/add" }
    sell_url = { "method": "POST", "url": "https://data.mtgox.com/api/1/BTCUSD/private/order/add" }
    order_url = { "method": "POST", "url": "https://data.mtgox.com/api/1/generic/private/order/result" }
    open_orders_url = { "method": "POST", "url": "https://data.mtgox.com/api/1/generic/private/orders" }
    cancel_url = { "method": "POST", "url": " https://data.mtgox.com/api/1/BTCUSD/private/order/cancel" }
    
    key = None
    secret = None
    classname = None

    @property
    def order(self):
        return self._order

    @order.setter
    def order(self, order):
        self._order = order

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

        self._last_price = {}
        self._order = None

    def _change_currency_url(self, url, currency):
        return re.sub(r'BTC\w{3}', r'BTC' + currency, url)

    def _create_nonce(self):
        return int(time.time() * 1000000)

    def _send_request(self, url, params, extra_headers=None):
        headers = { 'Content-type': 'application/x-www-form-urlencoded', 'Accept': 'application/json, text/javascript, */*; q=0.01', 'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)' }

        if extra_headers is not None:
            for k, v in extra_headers.iteritems():
                headers[k] = v

        http_pool = urllib3.connection_from_url(url['url'])
        response = http_pool.urlopen(url['method'], url['url'], body=urllib.urlencode(params), headers=headers)

        if response.status == 200:
            return json.loads(response.data)

        return None

    def _to_int_price(self, price, currency):
        ret_price = None

        if currency == "USD" or currency == "EUR" or currency == "GBP" or currency == "PLN" or currency == "CAD" or currency == "AUD" or currency == "CHF" or currency == "CNY" or currency == "NZD" or currency == "RUB" or currency == "DKK" or currency == "HKD" or currency == "SGD" or currency == "THB":
            ret_price = Decimal(price)
            ret_price = int(price * 100000)
        elif currency == "JPY" or currency == "SEK":
            ret_price = Decimal(price)
            ret_price = int(price * 1000)

        return ret_price

    def _to_int_amount(self, amount):
        amount = Decimal(amount)

        return int(amount * 100000000)

    def get_order(self, trade):
        """
        Method gets particular order.
        """

        if not self.key or self.key is None:
            console_log("mtgox: key not set; check settings.py")
            return

        if not self.secret or self.secret is None:
            console_log("mtgox: secret not set; check settings.py")
            return

        order_type = ""
        if trade.buy_or_sell == True:
            order_type = "bid"
        elif trade.buy_or_sell == False:
            order_type = "ask"
        params = [ ("nonce", self._create_nonce()), ("order", trade.exchange_oid), ("type", order_type) ]
        headers = { 'Rest-Key': self.key, 'Rest-Sign': base64.b64encode(str(hmac.new(base64.b64decode(self.secret), urllib.urlencode(params), hashlib.sha512).digest())) }

        response = self._send_request(self.order_url, params, headers)
        if response and u"result" in response and response[u"result"] == u"success":
            order = Order()
            if u"trades" in response[u"return"]:
                order.trades = response[u"return"][u"trades"]

                sum_price = 0
                sum_amount = 0
                for exchange_trade in response[u"return"]["trades"]:
                    if str(trade.currency) == str(exchange_trade[u"currency"]):
                        sum_price += Decimal(exchange_trade[u"amount"][u"value"]) * Decimal((exchange_trade[u"price"][u"value"]))
                        sum_amount += Decimal(exchange_trade[u"amount"][u"value"])

                order.sum_price = sum_price
                order.sum_amount = sum_amount

                return order
        elif response and u"result" in response and response[u"result"] == u"error":
            return {"error": response[u"error"]}

        return None

    def get_orders(self):
        """
        Method gets open orders.
        """

        if not self.key or self.key is None:
            console_log("mtgox: key not set; check settings.py")
            return

        if not self.secret or self.secret is None:
            console_log("mtgox: secret not set; check settings.py")
            return

        params = [ (u"nonce", self._create_nonce()) ]
        headers = { 'Rest-Key': self.key, 'Rest-Sign': base64.b64encode(str(hmac.new(base64.b64decode(self.secret), urllib.urlencode(params), hashlib.sha512).digest())) }

        response = self._send_request(self.open_orders_url, params, headers)

        if response and u"result" in response and response[u"result"] == u"success":
            return response[u"return"]

        return None

    def get_last_price(self, currency):
        if currency in self._last_price:
            return self._last_price[currency]

        self.ticker_url["url"] = self._change_currency_url(self.ticker_url["url"], currency)

        response = self._send_request(self.ticker_url, {})
        if response and u"result" in response and response[u"result"] == u"success" and u"return" in response and u"last_local" in response[u"return"]:
            self._last_price[currency] = Decimal(response[u"return"][u"last_local"][u"value"])

            return Decimal(response[u"return"][u"last_local"][u"value"])

        return None

    def get_balance(self):
        """
        For future use.
        """

        if not self.key or self.key is None:
            console_log("mtgox: key not set; check settings.py")
            return

        if not self.secret or self.secret is None:
            console_log("mtgox: secret not set; check settings.py")
            return


        params = [ (u"nonce", self._create_nonce()) ]
        headers = { 'Rest-Key': self.key, 'Rest-Sign': base64.b64encode(str(hmac.new(base64.b64decode(self.secret), urllib.urlencode(params), hashlib.sha512).digest())) }

        response = self._send_request(self.balance_url, params, headers)

        if response and "result" in response and response["result"] == "success":
            return response

        return None

    def buy(self, price, amount, currency):
        """
        bid == buy
        ask == sell

        Returns order ID if order was placed successfully.
        """
        if not self.key or self.key is None:
            console_log("mtgox: key not set; check settings.py")
            return None

        if not self.secret or self.secret is None:
            console_log("mtgox: secret not set; check settings.py")
            return None


        price = self._to_int_price(price, currency)
        amount = self._to_int_amount(amount)

        if not price or price is None:
            console_log("mtgox: there is no conversion forumla for currency %s" % (currency))

            return None

        if not amount or amount is None: return None


        self.buy_url["url"] = self._change_currency_url(self.buy_url["url"], currency)

        params = [ ("nonce", self._create_nonce()), ("amount_int", str(amount)), ("price_int", str(price)), ("type", "bid") ]
        headers = { 'Rest-Key': self.key, 'Rest-Sign': base64.b64encode(str(hmac.new(base64.b64decode(self.secret), urllib.urlencode(params), hashlib.sha512).digest())) }

        response = self._send_request(self.buy_url, params, headers)

        if response and u"result" in response and response[u"result"] == u"success":
            return response[u"return"]

        return None

    def sell(self, price, amount, currency):
        """
        ask == sell
        """

        if not self.key or self.key is None:
            console_log("mtgox: key not set; check settings.py")
            return

        if not self.secret or self.secret is None:
            console_log("mtgox: secret not set; check settings.py")
            return


        price = self._to_int_price(price, currency)
        amount = self._to_int_amount(amount)

        if not price or price is None:
            console_log("there is no conversion forumla for currency %s" % (currency))

            return None

        if not amount or amount is None: return None

        self.sell_url["url"] = self._change_currency_url(self.sell_url["url"], currency)

        params = [ ("nonce", self._create_nonce()), ("amount_int", str(amount)), ("price_int", str(price)), ("type", "ask") ]
        headers = { 'Rest-Key': self.key, 'Rest-Sign': base64.b64encode(str(hmac.new(base64.b64decode(self.secret), urllib.urlencode(params), hashlib.sha512).digest())) }

        response = self._send_request(self.sell_url, params, headers)

        if response and u"result" in response and response[u"result"] == u"success":
            return response[u"return"]

        return None

########NEW FILE########
__FILENAME__ = exchange_abstract
from abc import ABCMeta, abstractmethod, abstractproperty
#import settings as settings

class Order:
    """
    This one is not abstract, but just base class for setting 
    exchange["blabla"].order.trades = exchanges["blabla"].get_order(trades)
    """
    trades = None
    sum_price = 0
    sum_amount = 0
    

    def __init__(self):
        self.trades = None
        self.sum_price = 0
        self.sum_amount = 0

class ExchangeAbstract:
    __metaclass__ = ABCMeta

    @abstractproperty
    def order(self):
        return 'Should never see this'

    @order.setter
    def order(self, order):
        return

    def __init__(self):
        return

    @abstractmethod
    def get_order(self, trade):
        """
        Should return Order() with mandatory attributes set sum_price,
        sum_amount and optional trades.
        
        order = Order()
        
        order.sum_price = total money amount spent/got from particular order.
        order.sum_amount = total amount ot Bitcoins got/sold
        order.trades = this is optional for now. You can put trades from particular order.
        """

        return None

    @abstractmethod
    def get_orders(self):
        """
        Retrieves orders for particular exchange.

        This method is used for check_status function in scripts/dealing.py,
        but right now, when only MtGox API version 1 is implemented, returned
        data is not structured. I/you should do it, when implementing support
        for other exchanges.
        """

        return None

    @abstractmethod
    def get_last_price(self, currency):
        """
        Retrieves last price from for particular currency.

        Should return Decimal value of a price.
        """

        return None

    @abstractmethod
    def buy(self, price, amount, currency):
        """ 
        bid == buy

        Should return order ID if order was placed successfully.
        """

        return None

    @abstractmethod
    def sell(self, price, amount, currency):
        """ 
        bid == buy

        Should return order ID if order was placed successfully.
        """

        return None

########NEW FILE########
__FILENAME__ = models
from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from common.models import Skeleton, SkeletonU

SELL_TIME = ( 
    ('now', 'now'),
    ('at sell price', 'at sell price'),
    ('after fixed time', 'after fixed time')
)

TRADE_STATUS = (
    ('waiting', 'waiting'),
    ('buying', 'buying'),
    ('bought', 'bought'),
    ('selling', 'selling'),
    ('sold', 'sold'),
    ('stop', 'stop'),
    ('stopped', 'stopped'),
    ('cancel', 'cancel'),
    ('canceled', 'canceled'),
    ('not enough funds', 'not enough funds')
)

LOG = (
    ('waiting', 'waiting'),
    ('buying', 'buying'),
    ('bought', 'bought'),
    ('selling', 'selling'),
    ('sold', 'sold'),
    ('stop', 'stop'),
    ('stopped', 'stopped'),
    ('cancel', 'cancel'),
    ('canceled', 'canceled'),
    ('not enough funds', 'not enough funds'),
    ('could not get price', 'could not get price'),
    ('could not get orders', 'could not get orders'),
    ('custom', 'custom'),
    ('no data found', 'no data found')
)

class Currency(SkeletonU):
    name = models.CharField(_('Currency name'), max_length=30, null=False, blank=False, unique=True)
    abbreviation = models.CharField(_('Abbreviation'), max_length=5, null=False, blank=False, unique=True)
    symbol = models.CharField(_('Currency symbol'), max_length=3, null=True, blank=True)

    def __unicode__(self):
        return u'%s' % (self.abbreviation)

class Exchange(SkeletonU):
    name = models.CharField(_('Exchange name'), max_length=40, null=False, blank=False, unique=True, db_index=True)
    description = models.TextField(_('Description'), null=True, blank=True)
    url = models.URLField(_('URL of exchange'), max_length=255, blank=True, null=True)
    currencies = models.ManyToManyField(Currency, null=True, blank=True) # for future use
    active = models.BooleanField(_('Active or not'), help_text=_('If active is set to false on exchange, then all trades for this exchange will be deactivated and cancelled (if exchange does support this action).'), default=False, null=False, blank=False)

    def __unicode__(self):
        return u"%s" % (self.name)

"""
For future
class UserExchangeCurrency(SkeletonU):
    user = models.ForeignKey(User, related_name='(app_label)s_%(class)s_user', null=False, blank=False)
    exchange = models.ForeignKey(Exchange, related_name='(app_label)s_%(class)s_user', null=False, blank=False)
    currency = models.ForeignKey(Currency, related_name='(app_label)s_%(class)s_user', null=False, blank=False)
    active = models.BooleanField(_('Active or not'), help_text=_('If active is set to false on exchange, then all trades for this exchange will be deactivated and cancelled (if exchange does support this action).'), default=False, null=False, blank=False)
"""

class Trade(SkeletonU):
    """
    buy_or_sell == True => BUY
    buy_or_sell == False => SELL
    """

    user = models.ForeignKey(User, related_name='(app_label)s_%(class)s_user', null=False, blank=False)
    lp_higher = models.BooleanField(_('Is last price price higher/lower?'), help_text=_('TRUE == if last price is higher or equal to watch price; FALSE == if last price is lower or equal to watch price'), default=False, null=False, blank=False)
    buy_or_sell = models.BooleanField(_('Buy or sell?'), help_text=_('TRUE == buy; FALSE == sell'), default=False, null=False, blank=False)
    watch_price = models.DecimalField(_('Price to watch'), max_digits=10, decimal_places=5, null=False, blank=False)
    price = models.DecimalField(_('Buy or sell at price'), max_digits=10, decimal_places=5, null=False, blank=False)
    amount = models.DecimalField(_('Amount'), max_digits=16, decimal_places=8, null=False, blank=False)
    total_price = models.DecimalField(_('Total price'), help_text=_('This is real total money spent/got on exchange for this trade (it includes fees if exchange supports that)'), max_digits=10, decimal_places=5, null=True, blank=True)
    total_amount = models.DecimalField(_('Total amount'), help_text=_('This is real total number of Bitcoins bought/sold on exchange for this trade (it includes fees if exchange supports that)'), max_digits=16, decimal_places=8, null=True, blank=True)
    status = models.CharField(_('Status of trade'), help_text=_('Status of trade (you do not have to set/change this, unless you know what are you doing).'), max_length=30, null=False, blank=False, choices=TRADE_STATUS, default='waiting')
    active = models.BooleanField(_('Active or not'), help_text=_('active == TRUE, not active == FALSE'), default=False, null=False, blank=False)
    completed = models.BooleanField(_('Completed on exchange'), help_text=_('This is true if trade was fully executed/completed or not on exchange'), default=False, null=False, blank=False)
    exchange_oid = models.CharField(_('Exchanges order ID'), help_text=_('Some exchanges return id of a trade (MtGox has following format http://en.wikipedia.org/wiki/UUID).'), max_length=36, null=True, blank=True, db_index=True) 
    related = models.ForeignKey('self', help_text=_('Only if related order was successfully executed, only then this order will be executed also.'), null=True, blank=True)
    exchange = models.ForeignKey(Exchange, related_name='(app_label)s_%(class)s_exchange', null=False, blank=False) 
    currency = models.ForeignKey(Currency, related_name='(app_label)s_%(class)s_currency', null=False, blank=False)

    def approximate_total(self):
        return u"%s" % (round(Decimal(self.price*self.amount), 8))

    def total(self):
        if self.completed == True:
            trade_log = TradeLog.objects.filter(trade=self.pk,log="no data found")
            if trade_log and len(trade_log) > 0:
                return u"no transactions found"

            if not self.total_price or not self.total_amount:
                return u""

            return u"%s (%s BTCs)" % (self.total_price, self.total_amount,)

        return u""

    def __unicode__(self):
        return u"%s - %s %s %s" % (self.pk, self.watch_price, self.price, self.amount)

class TradeLog(SkeletonU):
    datetime = models.DateTimeField(_('Datetime of log'), auto_now=True, auto_now_add=True, null=False, blank=False)
    trade = models.ForeignKey(Trade, related_name='%(app_label)s_%(class)s_trade', null=False, blank=False)
    log = models.CharField(_('Log'), max_length=40, null=False, blank=False, choices=LOG)
    log_desc = models.TextField(_('Log description'), null=False, blank=False)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os, sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bitcoin_dealer.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = dealing
import sys, os, time, datetime
import urllib2
from decimal import *

sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('../bitcoin_dealer'))


from django import db

from exchange.exchange.mtgox1 import MtGox1
from exchange.exchange.bitstamp1 import BitStamp1
# from exchange.exchange.btce1 import BtcE1
from exchange.models import Trade, TradeLog, Exchange
from common.functions import console_log
import exchange.exchange_abstract
import settings as settings


def trade(trades):
    
    #last prices for every exchange
    last_prices_exchanges = {}
    
    for trade in trades:
        if trade.exchange.name in exchanges and trade.exchange.name not in last_prices_exchanges:
            last_price = exchanges[trade.exchange.name].get_last_price(trade.currency.abbreviation)
            last_prices_exchanges[trade.exchange.name] = last_price
        elif trade.exchange.name in exchanges:
            last_price = last_prices_exchanges[trade.exchange.name]
        else:
            continue

        if last_price is None: continue
        try:
            watch_price = Decimal(trade.watch_price)
            # we are BUYING, when last price is higher or equal to watch price (lp_higher == True) and there is no related "sell" order
            if trade.active == True and trade.lp_higher == True and trade.buy_or_sell == True and trade.related is None:
                if last_price >= watch_price:
                    response = exchanges[trade.exchange.name].buy(trade.price, trade.amount, trade.currency.abbreviation)

                    if response and response is not None:
                        trade.active = False
                        trade.status = "buying"
                        trade.exchange_oid = response
                        trade.save()

                        trade_log = TradeLog(created_by=trade.user, trade=trade, log="buying", log_desc="Buying %s." % (trade.pk))
                        trade_log.save()

                        if settings.bd_debug == True:
                            console_log("buying, when last price (%s) is higher or equal than watch price (%s) and there is no related sell order (buying at price: %s, amount: %s, currency: %s)" % (last_price, trade.watch_price, trade.price, trade.amount, trade.currency.abbreviation))

            # we are BUYING, when last price is lower or equal to watch price (lp_higher == False) and there is no related "sell" order
            elif trade.active == True and trade.lp_higher == False and trade.buy_or_sell == True and trade.related is None:
                if last_price <= watch_price:
                    
                    response = exchanges[trade.exchange.name].buy(trade.price, trade.amount, trade.currency.abbreviation)
                    if response and response is not None:
                        trade.active = False
                        trade.status = "buying"
                        trade.exchange_oid = response
                        trade.save()

                        trade_log = TradeLog(created_by=trade.user, trade=trade, log="buying", log_desc="Buying %s." % (trade.pk))
                        trade_log.save()

                        if settings.bd_debug == True:
                            console_log("buying, when last price (%s) is lower or equal that watch price (%s) and there is no related sell order (buying at price: %s, amount: %s, currency: %s)" % (last_price, trade.watch_price, trade.price, trade.amount, trade.currency.abbreviation))

            # we are BUYING, when last price is higher or equal to watch price (lp_higher == True) and related "sell" order has been fully "sold"
            elif trade.active == True and trade.lp_higher == True and trade.buy_or_sell == True and trade.related is not None:
                if trade.related.status == "sold" and trade.status == "waiting":
                    if last_price >= watch_price:
                        response = exchanges[trade.exchange.name].buy(trade.price, trade.amount, trade.currency.abbreviation)

                        if response and response is not None:
                            trade.active = False
                            trade.status = "buying"
                            trade.exchange_oid = response
                            trade.save()

                            trade_log = TradeLog(created_by=trade.user, trade=trade, log="buying", log_desc="Buying %s (related %s sold)." % (trade.pk, trade.related.pk))
                            trade_log.save()

                            if settings.bd_debug == True:
                                console_log("buying, when last price (%s) is higher or equal to watch price (%s) and related sell order was sold (buying at price: %s, amount: %s, currency: %s, related: %s)" % (last_price, trade.watch_price, trade.price, trade.amount, trade.currency.abbreviation, trade.related.pk))

            # we are BUYING, when last price is lower or equal to watch price (lp_hihger == False) and related "sell" order has been fully "sold"
            elif trade.active == True and trade.lp_higher == False and trade.buy_or_sell == True and trade.related is not None:
                if trade.related.status == "sold" and trade.status == "waiting":
                    if last_price <= watch_price:
                        response = exchanges[trade.exchange.name].buy(trade.price, trade.amount, trade.currency.abbreviation)

                        if response and response is not None:
                            trade.active = False
                            trade.status = "buying"
                            trade.exchange_oid = response
                            trade.save()

                            trade_log = TradeLog(created_by=trade.user, trade=trade, log="buying", log_desc="Buying %s (related %s sold)." % (trade.pk, trade.related.pk))
                            trade_log.save()

                            if settings.bd_debug == True:
                                console_log("buying, when last price (%s) is lower or equal to watch price (%s) and related sell order was sold (buying at price: %s, amount: %s, currency: %s, related: %s)" % (last_price, trade.watch_price, trade.price, trade.amount, trade.currency.abbreviation, trade.related.pk))

            # we are SELLING, when last price is higher or equal to watch price (lp_higher == True) and there is no related "buy" order
            elif trade.active == True and trade.lp_higher == True and trade.buy_or_sell == False and trade.related is None:
                if last_price >= watch_price:
                    response = exchanges[trade.exchange.name].sell(trade.price, trade.amount, trade.currency.abbreviation)

                    if response and response is not None:
                        trade.active = False
                        trade.status = "selling"
                        trade.exchange_oid = response
                        trade.save()

                        trade_log = TradeLog(created_by=trade.user, trade=trade, log="selling", log_desc="Selling %s." % (trade.pk))
                        trade_log.save()

                        if settings.bd_debug == True:
                            console_log("selling, when last price (%s) is higher or equal to watch price (%s) and there is no related buy order (selling at price: %s, amount: %s, currency: %s)" % (last_price, trade.watch_price, trade.price, trade.amount, trade.currency.abbreviation))

            # we are SELLING, when last price is lower or equal to watch price (lp_higher == False) and there is no related "buy" order
            elif trade.active == True and trade.lp_higher == False and trade.buy_or_sell == False and trade.related is None:
                if last_price <= watch_price:
                    
                    response = exchanges[trade.exchange.name].sell(trade.price, trade.amount, trade.currency.abbreviation)
                    if response and response is not None:
                        
                        trade.active = False
                        trade.status = "selling"
                        trade.exchange_oid = response
                        trade.save()

                        trade_log = TradeLog(created_by=trade.user, trade=trade, log="selling", log_desc="Selling %s." % (trade.pk))
                        trade_log.save()

                        if settings.bd_debug == True:
                            console_log("selling, when last price (%s) is lower or equal to watch price (%s) and there is no related buy order (selling at price: %s, amount: %s, currency: %s)" % (last_price, trade.watch_price, trade.price, trade.amount, trade.currency.abbreviation))

            # we are SELLING, when last price is higher or equal to watch price (lp_higher == True) and related "buy" order has been fully "bought"
            elif trade.active == True and trade.lp_higher == True and trade.buy_or_sell == False and trade.related is not None:
                if trade.related.status == "bought" and trade.status == "waiting":
                    if last_price >= watch_price:
                        response = exchanges[trade.exchange.name].sell(trade.price, trade.amount, trade.currency.abbreviation)

                        if response and response is not None:
                            trade.active = False
                            trade.status = "selling"
                            trade.exchange_oid = response
                            trade.save()

                            trade_log = TradeLog(created_by=trade.user, trade=trade, log="selling", log_desc="Selling %s (related %s bought)." % (trade.pk, trade.related.pk))
                            trade_log.save()

                            if settings.bd_debug == True:
                                console_log("selling, when last price (%s) is higher or equal to watch price (%s) and related buy was bought (selling at price: %s, amount: %s, currency: %s, related: %s)" % (last_price, trade.watch_price, trade.price, trade.amount, trade.currency.abbreviation, trade.related.pk))

            # we are SELLING, when last price is lower or equal to watch price and related "buy" order has been fully "bought"
            elif trade.active == True and trade.lp_higher == False and trade.buy_or_sell == False and trade.related is not None:
                if trade.related.status == "bought" and trade.status == "waiting":
                    if last_price <= watch_price:
                        response = exchanges[trade.exchange.name].sell(trade.price, trade.amount, trade.currency.abbreviation)

                        if response and response is not None:
                            trade.active = False
                            trade.status = "selling"
                            trade.exchange_oid = response
                            trade.save()

                            trade_log = TradeLog(created_by=trade.user, trade=trade, log="selling", log_desc="Selling %s (related %s bought)." % (trade.pk, trade.related.pk))
                            trade_log.save()

                            if settings.bd_debug == True:
                                console_log("selling, when last price (%s) is lower or equal to watch price (%s) and related buy was bought (selling at price: %s, amount: %s, currency: %s, related: %s)" % (last_price, trade.watch_price, trade.price, trade.amount, trade.currency.abbreviation, trade.related.pk))
            
            elif trade.active == True and trade.lp_higher == False and trade.buy_or_sell == False and trade.related is not None:
                if trade.related.status == "bought" and trade.status == "waiting":
                    if last_price <= watch_price:
                        response = exchanges[trade.exchange.name].sell(trade.price, trade.amount, trade.currency.abbreviation)

                        if response and response is not None:
                            trade.active = False
                            trade.status = "selling"
                            trade.exchange_oid = response
                            trade.save()

                            trade_log = TradeLog(created_by=trade.user, trade=trade, log="selling", log_desc="Selling %s (related %s bought)." % (trade.pk, trade.related.pk))
                            trade_log.save()

                            if settings.bd_debug == True:
                                console_log("selling, when last price (%s) is lower or equal to watch price (%s) and related buy was bought (selling at price: %s, amount: %s, currency: %s, related: %s)" % (last_price, trade.watch_price, trade.price, trade.amount, trade.currency.abbreviation, trade.related.pk))
        
        
        
        except:
            raise
"""
id: Order ID
type: 1 for sell order or 2 for buy order
status: 1 for active, 2 for not enough funds
"""
def check_status(trades, orders):
    for trade in trades:
        found = None
        for order in orders:
            if str(trade.exchange_oid) == str(order[u"oid"]):
                found = order
                break

        if found is not None:
            if trade.status == "selling" and found[u"status"] == u"invalid":
                trade.status = "not enough funds"
                trade.save()

                trade_log = TradeLog(created_by=trade.user, trade=trade, log="not enough funds", log_desc="Not enough funds for trade %s." % (trade.pk))
                trade_log.save()
                if (settings.bd_debug == True):
					console_log("not enoguh funds for sell at price: %s, amount: %s, currency: %s, trade: %s" % (trade.price, trade.amount, trade.currency.abbreviation, trade.pk))
            if trade.status == "buying" and found[u"status"] == u"invalid":
                trade.status = "not enough funds"
                trade.save()

                trade_log = TradeLog(created_by=trade.user, trade=trade, log="not enough funds", log_desc="Not enough funds for trade %s." % (trade.pk))
                trade_log.save()
                if (settings.bd_debug == True):
					console_log("not enoguh funds for buy at price: %s, amount: %s, currency: %s, trade: %s" % (trade.price, trade.amount, trade.currency.abbreviation, trade.pk))
        else:
            if trade.status == "selling":
                trade.status = "sold"
                trade.save()

                trade_log = TradeLog(created_by=trade.user, trade=trade, log="sold", log_desc="Sold trade %s." % (trade.pk))
                trade_log.save()
                if (settings.bd_debug == True):
				    console_log("sold %s bitcoins at %s %s" % (trade.amount, trade.price, trade.currency.abbreviation))
            elif trade.status == "buying":
                trade.status = "bought"
                trade.save()

                trade_log = TradeLog(created_by=trade.user, trade=trade, log="bought", log_desc="Bought trade %s." % (trade.pk))
                trade_log.save()
                if (settings.bd_debug == True):
					console_log("bought %s bitcoins at %s %s" % (trade.amount, trade.price, trade.currency.abbreviation))

        """
        Not working properly now.
        if trade.exchange_oid is not None and trade.completed == False and (trade.status == "buying" or trade.status == "bought" or trade.status == "selling" or trade.status == "sold"):
            if (settings.bd_debug == True):
                if trade.status == "buying" or trade.status == "selling":
    	            console_log("trade %s at price %s, amount %s and currency %s is still not being completed, so we will check for completed transactions" % (trade.pk, trade.price, trade.amount, trade.currency.abbreviation))
                elif trade.status == "bought" or trade.status == "sold":
    	            console_log("trade %s at price %s, amount %s and currency %s was fully executed, but we do not have a final sum of money we got/spent for the trade, so we will do this right now" % (trade.pk, trade.price, trade.amount, trade.currency.abbreviation))
	                    
            exchanges[trade.exchange.name].order = None        
            exchanges[trade.exchange.name].order = exchanges[trade.exchange.name].get_order(trade)

            # isinstance not working properly, so we "hack" a little bit
            if hasattr(exchanges[trade.exchange.name].order, "sum_price") and hasattr(exchanges[trade.exchange.name].order, "sum_amount"):
                trade.total_price = exchanges[trade.exchange.name].order.sum_price
                trade.total_amount = exchanges[trade.exchange.name].order.sum_amount
                if (trade.status == "bought" or trade.status == "sold"):
                    if (settings.bd_debug == True):
                        console_log("trade %s at price %s, amount %s and currency %s completed" % (trade.pk, trade.price, trade.amount, trade.currency.abbreviation))
                    trade.completed = True
                trade.save()


            elif isinstance(exchanges[trade.exchange.name].order, dict):
                if "error" in exchanges[trade.exchange.name].order:
                    trade.completed = True
                    trade.save()

                    trade_log = TradeLog(created_by=trade.user, trade=trade, log="custom", log_desc="Error for trade %s with message %s from exchange." % (trade.pk, exchanges[trade.exchange.name].order["error"]))
                    trade_log.save()

                    if (settings.bd_debug == True):
        	            console_log("trade %s at price %s, amount %s and currency %s completed with error on getting transactions from exchange. Message was %s." % (trade.pk, trade.price, trade.amount, trade.currency.abbreviation, exchanges[trade.exchange.name].order["error"]))
        """

while True:
    time.sleep(settings.check_interval)
    try:

        try:
            exchanges.clear()
        except NameError:
            exchanges = {}

        active_exchanges = Exchange.objects.filter(active=True)
        for exchange in active_exchanges:
            if exchange.name in settings.EXCHANGES:
                exchanges[exchange.name] = getattr(sys.modules[__name__], settings.EXCHANGES[exchange.name]["classname"])(**settings.EXCHANGES[exchange.name]) # with (**settings.EXCHANGES[exchange.name]) at the end, constructor of class gets called with settings paramaters http://stackoverflow.com/questions/553784/can-you-use-a-string-to-instantiate-a-class-in-python

        my_trades = Trade.objects.filter(exchange__in=active_exchanges, active=True)
        trade(my_trades)

        # we check for statuses of our orders
        all_my_trades = Trade.objects.all()
        
        my_open_orders = []
        for exchange, exchange_data in exchanges.iteritems():
            open_orders = exchanges[exchange].get_orders()
            if open_orders is not None:
                # when we will implement another exchange, we will need following line instead of the second following line
                # my_open_orders.append(open_orders)
                my_open_orders = open_orders

        if all_my_trades is not None and len(all_my_trades) > 0 and my_open_orders is not None:
            check_status(all_my_trades, my_open_orders)
            if (settings.bd_debug == True):
	            console_log("just checked statuses of orders...")

        if (settings.bd_debug == True):
            console_log("sleeping %d seconds..." % settings.check_interval)

    except urllib2.URLError as err:
        console_log("could not connect to some url: %s" % (err))
        pass
    except ValueError as (err):
        # got this error once
        console_log("No JSON object could be decoded ???: %s " % (err))
        pass
    except:
        raise

    db.reset_queries()

########NEW FILE########
__FILENAME__ = settings
# Django settings for bitcoin_dealer project.
# -*- coding: utf-8 -*-
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('', ''),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'bitcoin_dealer',                      # Or path to database file if using sqlite3.
        'USER': 'bitcoin',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Ljubljana'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

if DEBUG == True:
    MEDIA_URL = 'http://127.0.0.1:8000/'
else:
    MEDIA_URL = 'http://127.0.0.1:8000/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
if DEBUG == True:
    # STATIC_URL = 'http://127.0.0.1:8000/static/'
    STATIC_URL = '/static/'
else:
    STATIC_URL = 'http://127.0.0.1:8000/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = ''

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.    
    '',
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'bitcoin_dealer.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.

    os.path.join(os.path.dirname(__file__), 'templates').replace('\\', '/'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    #'django.contrib.admindocs',
    'exchange',
    'common'
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-bitcoin'
    }
}

EXCHANGES = {
    'mtgox': {
        'classname': 'MtGox1', # DO NOT CHANGE THIS
        # exchange specific (you can set everything below to your needs)
        'key': '',
        'secret': '',
    },
    'bitstamp':{
        'classname': 'BitStamp1',
        # change specific (put your user ID and Password here)
        'key': '',
        'secret': '',
        'client_id': '',
    }
}

check_interval = 7
bd_debug = True

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'bitcoin_dealer.views.home', name='home'),
    # url(r'^bitcoin_dealer/', include('bitcoin_dealer.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class UserSettings(SkeletonU):
    user = models.ForeignKey(User)
    key = models.CharField(_('Key'), max_length=50, null=False, blank=False, db_index=True)
    value = models.CharField(_('Value'), max_length=50)

    __unicode__ = lambda self: u'%s = %s' % (self.key, self.value)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
