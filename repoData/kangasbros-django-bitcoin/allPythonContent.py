__FILENAME__ = admin
# vim: tabstop=4 expandtab autoindent shiftwidth=4 fileencoding=utf-8

from django.contrib import admin

from django_bitcoin import models

class TransactionAdmin(admin.ModelAdmin):
    """Management of ``Transaction`` - Disable address etc editing
    """

    list_display = ('address', 'created_at', 'amount')
    readonly_fields = ('address', 'created_at', 'amount')


class BitcoinAddressAdmin(admin.ModelAdmin):
    """Deal with ``BitcoinAddress``
    No idea in being able to edit the address, as that would not
    sync with the network
    """

    list_display = ('address', 'label', 'created_at', 'least_received', 'active')
    readonly_fields = ('address',)


class PaymentAdmin(admin.ModelAdmin):
    """Allow the edit of ``description``
    """

    list_display = ('created_at', 'description', 'paid_at', 'address', 'amount', 'amount_paid', 'active')
    readonly_fields = ('address', 'amount', 'amount_paid', 'created_at', 'updated_at', 'paid_at', 'withdrawn_total', 'transactions')


class WalletTransactionAdmin(admin.ModelAdmin):
    """Inter-site transactions
    """

    list_display = ('created_at', 'from_wallet', 'to_wallet', 'to_bitcoinaddress', 'amount')
    readonly_fields = ('created_at', 'from_wallet', 'to_wallet', 'to_bitcoinaddress', 'amount')


class WalletAdmin(admin.ModelAdmin):
    """Admin ``Wallet``
    """
    addresses = lambda wallet: wallet.addresses.all()
    addresses.short_description = 'Addresses'

    list_display = ('created_at', 'label', 'updated_at')
    readonly_fields = ('created_at', 'updated_at', addresses, 'transactions_with')


admin.site.register(models.Transaction, TransactionAdmin)
admin.site.register(models.BitcoinAddress, BitcoinAddressAdmin)
admin.site.register(models.Payment, PaymentAdmin)
admin.site.register(models.WalletTransaction, WalletTransactionAdmin)
admin.site.register(models.Wallet, WalletAdmin)

# EOF


########NEW FILE########
__FILENAME__ = BCAddressField
#
# Django field type for a Bitcoin Address
#
import re
from django import forms
from django.forms.util import ValidationError
import hashlib


class BCAddressField(forms.CharField):
    default_error_messages = {
        'invalid': 'Invalid Bitcoin address.',
        }

    def __init__(self, *args, **kwargs):
        super(BCAddressField, self).__init__(*args, **kwargs)

    def clean(self, value):
        if not value and not self.required:
            return None

        if not value.startswith(u"1") and not value.startswith(u"3"):
            raise ValidationError(self.error_messages['invalid'])
        value = value.strip()

        if "\n" in value:
            raise ValidationError(u"Multiple lines in the bitcoin address")

        if " " in value:
            raise ValidationError(u"Spaces in the bitcoin address")

        if re.match(r"[a-zA-Z1-9]{27,35}$", value) is None:
            raise ValidationError(self.error_messages['invalid'])
        version = get_bcaddress_version(value)
        if version is None:
            raise ValidationError(self.error_messages['invalid'])
        return value


def is_valid_btc_address(value):
    value = value.strip()
    if re.match(r"[a-zA-Z1-9]{27,35}$", value) is None:
        return False
    version = get_bcaddress_version(value)
    if version is None:
        return False
    return True


__b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
__b58base = len(__b58chars)


def b58encode(v):
    """ encode v, which is a string of bytes, to base58.
    """

    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += (256**i) * ord(c)

    result = ''
    while long_value >= __b58base:
        div, mod = divmod(long_value, __b58base)
        result = __b58chars[mod] + result
        long_value = div
    result = __b58chars[long_value] + result

    # Bitcoin does a little leading-zero-compression:
    # leading 0-bytes in the input become leading-1s
    nPad = 0
    for c in v:
        if c == '\0': nPad += 1
        else: break

    return (__b58chars[0]*nPad) + result

def b58decode(v, length):
    """ decode v into a string of len bytes
    """
    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += __b58chars.find(c) * (__b58base**i)

    result = ''
    while long_value >= 256:
        div, mod = divmod(long_value, 256)
        result = chr(mod) + result
        long_value = div
    result = chr(long_value) + result

    nPad = 0
    for c in v:
        if c == __b58chars[0]: nPad += 1
        else: break

    result = chr(0)*nPad + result
    if length is not None and len(result) != length:
        return None

    return result


def b36encode(number, alphabet='0123456789abcdefghijklmnopqrstuvwxyz'):
    """Converts an integer to a base36 string."""
    if not isinstance(number, (int, long)):
        long_value = 0L
        for (i, c) in enumerate(number[::-1]):
            long_value += (256**i) * ord(c)
        number = long_value

    base36 = '' if number != 0 else '0'
    sign = ''
    if number < 0:
        sign = '-'
        number = -number

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36


def b36decode(number):
    return int(number, 36)


def get_bcaddress_version(strAddress):
    """ Returns None if strAddress is invalid.    Otherwise returns integer version of address. """
    addr = b58decode(strAddress, 25)
    if addr is None: return None
    version = addr[0]
    checksum = addr[-4:]
    vh160 = addr[:-4] # Version plus hash160 is what is checksummed
    h3=hashlib.sha256(hashlib.sha256(vh160).digest()).digest()
    if h3[0:4] == checksum:
        return ord(version)
    return None

########NEW FILE########
__FILENAME__ = context_processors
from django_bitcoin.models import bitcoinprice_eur, bitcoinprice_usd

def bitcoinprice(request):
    return {'bitcoinprice_eur': bitcoinprice_eur(),
        'bitcoinprice_usd': bitcoinprice_usd(),
        }

########NEW FILE########
__FILENAME__ = currency
# -*- coding: utf-8 -*-
"""Usage:

>>> currency.exchange(
...     currency.Money("10.0", "BTC"),
...     "BTC")
Money("10.0", "BTC")

Default valid currencies are BTC, EUR and USD. Change exchange rate
sources and add new ones by the setting BITCOIN_CURRENCIES, which
should be a list of dotted paths to Currency subclasses (or other
classes) which implement both to_btc(decimal amount) -> decimal and
from_btc(decimal amount) -> decimal.

You can subclass or instance the `Exchange` class to e.g. maintain
multiple different exchange rates from different sources in your own
code. Default `exchange` uses Bitcoincharts.
"""

import decimal

from django.core.cache import cache

import json
import jsonrpc
import sys
import urllib
import urllib2
import random
import hashlib
import base64
from decimal import Decimal
import decimal
import warnings


from django_bitcoin import settings

class ConversionError(Exception):
    pass

class TemporaryConversionError(ConversionError):
    pass

class Exchange(object):
    def __init__(self):
        self.currencies = {}

    def register_currency(self, klass):
        self.currencies[klass.identifier] = klass

    def get_rate(self, currency, target="BTC"):
        """Rate is inferred from a dummy exchange"""
        start = Money(currency, "1.0")
        end = self(start, target)
        return end.amount

    def __call__(self, money, target="BTC"):
        """Gets the current equivalent amount of the given Money in
        the target currency
        """
        if not hasattr(money, "identifier"):
            raise ConversionError(
                "Use annotated currency (e.g. Money) as "
                "the unit argument")

        if money.identifier not in self.currencies:
            raise ConversionError(
                "Unknown source currency %(identifier)s. "
                "Available currencies: %(currency_list)s" % {
                    "identifier": money.identifier,
                    "currency_list": u", ".join(self.currencies.keys())})

        if target not in self.currencies:
            raise ConversionError(
                "Unknown target currency %(identifier)s. "
                "Available currencies: %(currency_list)s" % {
                    "identifier": target,
                    "currency_list": u", ".join(self.currencies.keys())})

        btc = self.currencies[money.identifier].to_btc(money.amount)
        return Money(target, self.currencies[target].from_btc(btc))

class Money(object):
    def __init__(self, identifier, amount, *args, **kwargs):
        self.identifier = identifier
        self.amount = decimal.Decimal(amount)

    def __add__(self, other):
        if (not hasattr(other, "identifier")
            or other.identifier != self.identifier):
            raise ConversionError("Cannot add different currencies "
                                  "or non-currencies together")
        return Money(self.identifier, self.amount + other.amount)

    def __sub__(self, other):
        if (not hasattr(other, "identifier")
            or other.identifier != self.identifier):
            raise ConversionError("Cannot subtract different currencies "
                                  "or non-currencies together")
        return Money(self.identifier, self.amount - other.amount)

    def __mul__(self, other):
        if hasattr(other, "identifier"):
            raise ConversionError("Cannot multiply currency "
                                  "with any currency")
        return Money(self.identifier, self.amount * other)

    def __div__(self, other):
        if hasattr(other, "identifier"):
            raise ConversionError("Cannot divide currency "
                                  "with any currency")
        return Money(self.identifier, self.amount / other)

    def __unicode__(self):
        return u"%s %s" % (self.identifier, self.amount)

class Currency(object):
    def to_btc(self, amount):
        raise NotImplementedError
    def from_btc(self, amount):
        raise NotImplementedError

class BTCCurrency(Currency):
    identifier = "BTC"

    def to_btc(self, amount):
        return amount

    def from_btc(self, amount):
        return amount

class BitcoinChartsCurrency(Currency):
    period = "24h"

    def __init__(self):
        self.cache_key = "%s_in_btc" % self.identifier
        self.cache_key_old = "%s_was_in_btc" % self.identifier

    def populate_cache(self):
        try:
            f = urllib2.urlopen(
                u"http://bitcoincharts.com/t/weighted_prices.json")
            result=f.read()
            j=json.loads(result)
            base_price = j[self.identifier]
            cache.set(self.cache_key, base_price, 60*60)
            #print result
        except:
            print "Unexpected error:", sys.exc_info()[0]

        if not cache.get(self.cache_key):
            if not cache.get(self.cache_key_old):
                raise TemporaryConversionError(
                    "Cache not enabled, reliable exchange rate is not available for %s" % self.identifier)
            cache.set(self.cache_key, cache.get(self.cache_key_old), 60*60)

        cache.set(self.cache_key_old, cache.get(self.cache_key), 60*60*24*7)

    def get_factor(self):
        cached = cache.get(self.cache_key)
        if cached:
            factor = cached[self.period]
        else:
            self.populate_cache()
            factor = cache.get(self.cache_key)[self.period]
        return decimal.Decimal(factor)

    def to_btc(self, amount):
        return amount * self.get_factor()

    def from_btc(self, amount):
        return amount / self.get_factor()

class EURCurrency(BitcoinChartsCurrency):
    identifier = "EUR"

class USDCurrency(BitcoinChartsCurrency):
    identifier = "USD"

exchange = Exchange()

# simple utility functions for conversions

CURRENCY_CHOICES = (
    ('BTC', 'BTC'),
    ('USD', 'USD'),
    ('EUR', 'EUR'),
    ('AUD', 'AUD'),
    ('BRL', 'BRL'),
    ('CAD', 'CAD'),
    ('CHF', 'CHF'),
    ('CNY', 'CNY'),
    ('GBP', 'GBP'),
    ('NZD', 'NZD'),
    ('PLN', 'PLN'),
    ('RUB', 'RUB'),
    ('SEK', 'SEK'),
    ('SLL', 'SLL'),
)

RATE_PERIOD_CHOICES=("24h", "7d", "30d",)

market_parameters=('high', 'low', 'bid', 'ask', 'close',)


def markets_chart():
    cache_key="bitcoincharts_markets"
    cache_key_old="bitcoincharts_markets_old"
    if not cache.get(cache_key):
        try:
            f = urllib2.urlopen(
                u"http://bitcoincharts.com/t/markets.json")
            result=f.read()
            j=json.loads(result)
            final_markets={}
            for market in j:
                b=True
                for mp in market_parameters:
                    if not market[mp]:
                        b=False
                        break
                if b:
                    # print market['symbol']
                    final_markets[market['symbol'].lower()]=market
            cache.set(cache_key, final_markets, 60*5)
            #print result
        except Exception, err:
            print "Unexpected error:", sys.exc_info()[0], err

        if not cache.get(cache_key):
            if not cache.get(cache_key_old):
                raise Exception(
                    "Cache not enabled, reliable market data is not available")
            cache.set(cache_key, cache.get(cache_key_old), 60*5)

        cache.set(cache_key_old, cache.get(cache_key), 60*60*24*7)
    return cache.get(cache_key)


def currency_exchange_rates():
    cache_key="currency_exchange_rates"
    cache_key_old="currency_exchange_rates_old"
    if not cache.get(cache_key):
        try:
            f = urllib2.urlopen(
                u"http://openexchangerates.org/latest.json")
            result=f.read()
            j=json.loads(result)
            cache.set(cache_key, j, 60*5)
            #print result
        except Exception, err:
            print "Unexpected error:", sys.exc_info()[0], err

        if not cache.get(cache_key):
            if not cache.get(cache_key_old):
                raise Exception(
                    "Cache not enabled, reliable market data is not available")
            cache.set(cache_key, cache.get(cache_key_old), 60*5)

        cache.set(cache_key_old, cache.get(cache_key), 60*60*24*7)
    return cache.get(cache_key)


MTGOX_CURRENCIES = ("USD", "EUR", "AUD", "CAD", "CHF", "CNY", "DKK",
    "GBP", "HKD", "JPY", "NZD", "PLN", "RUB", "SEK", "SGD", "THB")

def get_mtgox_rate_table():
    cache_key_old="bitcoincharts_all_old"
    old_table = cache.get(cache_key_old)
    if not old_table:
        old_table = {}
        for c in MTGOX_CURRENCIES:
            old_table[c] = {'24h': None, '7d': None, '30d': None}
    for c in MTGOX_CURRENCIES:
        try:
            f = urllib2.urlopen(
                u"https://mtgox.com/api/1/BTC"+c+"/ticker")
            result=f.read()
            j=json.loads(result)
            old_table[c]['24h'] = Decimal(j['vwap']['value'])
        except Exception, err:
            print "Unexpected error:", sys.exc_info()[0], err


def get_rate_table():
    cache_key="bitcoincharts_all"
    cache_key_old="bitcoincharts_all_old"
    if not cache.get(cache_key):
        try:
            f = urllib2.urlopen(
                u"http://bitcoincharts.com/t/weighted_prices.json")
            result=f.read()
            j=json.loads(result)
            cache.set(cache_key, j, 60*60)
            print result
        # except ValueError:

        except:
            print "Unexpected error:", sys.exc_info()[0]

        if not cache.get(cache_key):
            if not cache.get(cache_key_old):
                raise TemporaryConversionError(
                    "Cache not enabled, reliable exchange rate is not available")
            cache.set(cache_key, cache.get(cache_key_old), 60*60)

        cache.set(cache_key_old, cache.get(cache_key), 60*60*24*7)
    return cache.get(cache_key)


def currency_exchange_rates():
    cache_key="currency_exchange_rates"
    cache_key_old="currency_exchange_rates_old"
    if not cache.get(cache_key):
        try:
            f = urllib2.urlopen(
                settings.BITCOIN_OPENEXCHANGERATES_URL)
            result=f.read()
            j=json.loads(result)
            cache.set(cache_key, j, 60*5)
            #print result
        except Exception, err:
            print "Unexpected error:", sys.exc_info()[0], err

        if not cache.get(cache_key):
            if not cache.get(cache_key_old):
                raise Exception(
                    "Cache not enabled, reliable market data is not available")
            cache.set(cache_key, cache.get(cache_key_old), 60*60*2)

        cache.set(cache_key_old, cache.get(cache_key), 60*60*24*7)
    return cache.get(cache_key)

def currency_list():
    return get_rate_table().keys()

def big_currency_list():
    return sorted(["BTC"] + currency_exchange_rates()["rates"].keys())

def get_currency_rate(currency="USD", rate_period="24h"):
    try:
        return Decimal(get_rate_table()[currency][rate_period])
    except KeyError:
        try:
            return Decimal(currency_exchange_rates()['rates'][currency])*Decimal(get_rate_table()['USD'][rate_period])
        except:
            return None

def btc2currency(amount, currency="USD", rate_period="24h"):
    if currency == "BTC":
        return amount
    rate=get_currency_rate(currency, rate_period)
    if rate==None:
        return None
    return (amount*rate).quantize(Decimal("0.01"))

def currency2btc(amount, currency="USD", rate_period="24h"):
    if currency == "BTC":
        return amount
    rate=get_currency_rate(currency, rate_period)
    if rate==None:
        return None
    return (amount/rate).quantize(Decimal("0.00000001"))



########NEW FILE########
__FILENAME__ = forms
# coding=utf-8
# vim: ai ts=4 sts=4 et sw=4

from django.db import models
from django import forms
from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.utils.translation import get_language_from_request, ugettext_lazy as _
from djangoextras.forms import CurrencyField
from django_bitcoin.models import BitcoinEscrow

class BitcoinEscrowBuyForm(ModelForm):
    class Meta:
        model=BitcoinEscrow
        fields = ('buyer_address', 'buyer_phone', 'buyer_email')


########NEW FILE########
__FILENAME__ = authproxy

"""
  Copyright 2011 Jeff Garzik

  AuthServiceProxy has the following improvements over python-jsonrpc's
  ServiceProxy class:

  - HTTP connections persist for the life of the AuthServiceProxy object
    (if server supports HTTP/1.1)
  - sends protocol 'version', per JSON-RPC 1.1
  - sends proper, incrementing 'id'
  - sends Basic HTTP authentication headers
  - parses all JSON numbers that look like floats as Decimal
  - uses standard Python json lib

  Previous copyright, from python-jsonrpc/jsonrpc/proxy.py:

  Copyright (c) 2007 Jan-Klaas Kollhof

  This file is part of jsonrpc.

  jsonrpc is free software; you can redistribute it and/or modify
  it under the terms of the GNU Lesser General Public License as published by
  the Free Software Foundation; either version 2.1 of the License, or
  (at your option) any later version.

  This software is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Lesser General Public License for more details.

  You should have received a copy of the GNU Lesser General Public License
  along with this software; if not, write to the Free Software
  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import httplib
import base64
import json
import decimal
import urlparse

USER_AGENT = "AuthServiceProxy/0.1"

HTTP_TIMEOUT = 30

class JSONRPCException(Exception):
    def __init__(self, rpcError):
        Exception.__init__(self)
        self.error = rpcError

class AuthServiceProxy(object):
    def __init__(self, serviceURL, serviceName=None):
        self.__serviceURL = serviceURL
        self.__serviceName = serviceName
        self.__url = urlparse.urlparse(serviceURL)
        if self.__url.port is None:
            port = 80
        else:
            port = self.__url.port
        self.__idcnt = 0
        authpair = "%s:%s" % (self.__url.username, self.__url.password)
        self.__authhdr = "Basic %s" % (base64.b64encode(authpair))
        if self.__url.scheme == 'https':
            self.__conn = httplib.HTTPSConnection(self.__url.hostname, port, None, None,False,
                    HTTP_TIMEOUT)
        else:
            self.__conn = httplib.HTTPConnection(self.__url.hostname, port, False,
                    HTTP_TIMEOUT)

    def __getattr__(self, name):
        if self.__serviceName != None:
            name = "%s.%s" % (self.__serviceName, name)
        return AuthServiceProxy(self.__serviceURL, name)

    def __call__(self, *args):
        self.__idcnt += 1

        postdata = json.dumps({
             'version': '1.1',
             'method': self.__serviceName,
             'params': args,
             'id': self.__idcnt})
        self.__conn.request('POST', self.__url.path, postdata,
                 { 'Host' : self.__url.hostname,
                     'User-Agent' : USER_AGENT,
                     'Authorization' : self.__authhdr,
                     'Content-type' : 'application/json' })

        httpresp = self.__conn.getresponse()
        if httpresp is None:
            raise JSONRPCException({
              'code' : -342, 'message' : 'missing HTTP response from server'})

        resp = json.loads(httpresp.read(), parse_float=decimal.Decimal)
        #print resp
        if resp['error'] != None:
            raise JSONRPCException(unicode(resp['error']))
        elif 'result' not in resp:
            raise JSONRPCException({
                'code' : -343, 'message' : 'missing JSON-RPC result'})
        else:
            return resp['result']



########NEW FILE########
__FILENAME__ = json
json = __import__('json')
loads = json.loads
dumps = json.dumps
JSONEncodeException = TypeError
JSONDecodeException = ValueError

########NEW FILE########
__FILENAME__ = proxy
from authproxy import AuthServiceProxy as ServiceProxy, JSONRPCException

########NEW FILE########
__FILENAME__ = CheckDbIntegrity
from django.core.management.base import NoArgsCommand
from django.conf import settings
import os
import sys
import re
import codecs
import commands
import urllib2
import urllib
import json
import random
from time import sleep
import math
from django_bitcoin.models import Wallet, BitcoinAddress, WalletTransaction, DepositTransaction
from django_bitcoin.utils import bitcoind
from django.db.models import Avg, Max, Min, Sum
from decimal import Decimal

class Command(NoArgsCommand):
    help = 'This checks that alles is in ordnung in django_bitcoin.'

    def handle_noargs(self, **options):
        # BitcoinAddress.objects.filter(active=True)
        bitcoinaddress_sum = BitcoinAddress.objects.filter(active=True)\
            .aggregate(Sum('least_received_confirmed'))['least_received_confirmed__sum'] or Decimal(0)
        print "Total received, sum", bitcoinaddress_sum
        transaction_wallets_sum = WalletTransaction.objects.filter(from_wallet__id__gt=0, to_wallet__id__gt=0)\
            .aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        print "Total transactions, sum", transaction_wallets_sum
        transaction_out_sum = WalletTransaction.objects.filter(from_wallet__id__gt=0)\
        	.exclude(to_bitcoinaddress="").exclude(to_bitcoinaddress="")\
            .aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        print "Total outgoing, sum", transaction_out_sum
        # for x in WalletTransaction.objects.filter(from_wallet__id__gt=0, to_wallet__isnull=True, to_bitcoinaddress=""):
        # 	print x.amount, x.created_at
        fee_sum = WalletTransaction.objects.filter(from_wallet__id__gt=0, to_wallet__isnull=True, to_bitcoinaddress="")\
            .aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        print "Fees, sum", fee_sum
        print "DB balance", (bitcoinaddress_sum - transaction_out_sum - fee_sum)
        print "----"
        bitcoind_balance = bitcoind.bitcoind_api.getbalance()
        print "Bitcoind balance", bitcoind_balance
        print "----"
        print "Wallet quick check"
        total_sum = Decimal(0)
        for w in Wallet.objects.filter(last_balance__lt=0):
            if w.total_balance()<0:
                bal = w.total_balance()
                # print w.id, bal
                total_sum += bal
        print "Negatives:", Wallet.objects.filter(last_balance__lt=0).count(), "Amount:", total_sum
        print "Migration check"
        tot_received = WalletTransaction.objects.filter(from_wallet=None).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        tot_received_bitcoinaddress = BitcoinAddress.objects.filter(migrated_to_transactions=True)\
            .aggregate(Sum('least_received_confirmed'))['least_received_confirmed__sum'] or Decimal(0)
        tot_received_unmigrated = BitcoinAddress.objects.filter(migrated_to_transactions=False)\
            .aggregate(Sum('least_received_confirmed'))['least_received_confirmed__sum'] or Decimal(0)
        if tot_received != tot_received_bitcoinaddress:
            raise Exception("wrong total receive amount! "+str(tot_received)+", "+str(tot_received_bitcoinaddress))
        print "Total " + str(tot_received) + " BTC deposits migrated, unmigrated " + str(tot_received_unmigrated) + " BTC"
        print "Migration check #2"
        dts = DepositTransaction.objects.filter(address__migrated_to_transactions=False).exclude(transaction=None)
        if dts.count() > 0:
            print "Illegal transaction!", dts
        if WalletTransaction.objects.filter(from_wallet=None, deposit_address=None).count() > 0:
            print "Illegal deposit transactions!"
        print "Wallet check"
        for w in Wallet.objects.filter(last_balance__gt=0):
            lb = w.last_balance
            tb_sql = w.total_balance_sql()
            tb = w.total_balance()
            if lb != tb or w.last_balance != tb or tb != tb_sql:
                print "Wallet balance error!", w.id, lb, tb_sql, tb
                print w.sent_transactions.all().count()
                print w.received_transactions.all().count()
                print w.sent_transactions.all().aggregate(Max('created_at'))['created_at__max']
                print w.received_transactions.all().aggregate(Max('created_at'))['created_at__max']
                # Wallet.objects.filter(id=w.id).update(last_balance=w.total_balance_sql())
        # print w.created_at, w.sent_transactions.all(), w.received_transactions.all()
            # if random.random() < 0.001:
            #     sleep(1)
        print "Address check"
        for ba in BitcoinAddress.objects.filter(least_received_confirmed__gt=0, migrated_to_transactions=True):
            dts = DepositTransaction.objects.filter(address=ba, wallet=ba.wallet)
            s = dts.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
            if s != ba.least_received:
                print "DepositTransaction error", ba.address, ba.least_received, s
                print "BitcoinAddress check"
        for ba in BitcoinAddress.objects.filter(migrated_to_transactions=True):
            dts = ba.deposittransaction_set.filter(address=ba, confirmations__gte=settings.BITCOIN_MINIMUM_CONFIRMATIONS)
            deposit_sum = dts.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
            wt_sum = WalletTransaction.objects.filter(deposit_address=ba).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
            if wt_sum != deposit_sum or ba.least_received_confirmed != deposit_sum:
                print "Bitcoinaddress integrity error!", ba.address, deposit_sum, wt_sum, ba.least_received_confirmed
            # if random.random() < 0.001:
            #     sleep(1)



########NEW FILE########
__FILENAME__ = CheckOldTransactions
from django.core.management.base import NoArgsCommand
from time import sleep, time
from django_bitcoin.utils import bitcoind
from django_bitcoin.models import BitcoinAddress
from django.conf import settings
from decimal import Decimal
import datetime

RUN_TIME_SECONDS = 60


class Command(NoArgsCommand):
    help = """This needs transactions signaling enabled. Polls\
     incoming transactions via listtransactions -bitcoind call, and checks\
      the balances accordingly.
      To enable, add this command to your cron, and set
      BITCOIN_TRANSACTION_SIGNALING = True
      After that, you will get signals from the transactions you do.
      balance_changed = django.dispatch.Signal(providing_args=["balance", "changed"])
"""

    def handle_noargs(self, **options):
        start_time = time()
        last_check_time = None
        print "starting overall1", time() - start_time, datetime.datetime.now()
        print "starting round", time() - start_time
        if not last_check_time:
            addresses_json = bitcoind.bitcoind_api.listreceivedbyaddress(0, True)
            addresses = {}
            for t in addresses_json:
                addresses[t['address']] = Decimal(t['amount'])
            print "bitcoind query done"
            last_id = 9999999999999999999
            while True:
                db_addresses = BitcoinAddress.objects.filter(active=True, wallet__isnull=False, id__lt=last_id).order_by("-id")[:10000]
                if len(db_addresses) == 0:
                    return
                for ba in db_addresses:
                    if ba.address in addresses.keys() and\
                        ba.least_received < addresses[ba.address]:
                        ba.query_bitcoind()
                        ba.query_bitcoind(0)
                    last_id=min(ba.id, last_id)
                print "finished 1000 scan", time() - start_time, last_id

########NEW FILE########
__FILENAME__ = CheckTransactions
from django.core.management.base import NoArgsCommand
from time import sleep, time
from django_bitcoin.utils import bitcoind
from django_bitcoin.models import BitcoinAddress, DepositTransaction
from django.conf import settings
from decimal import Decimal
import datetime

RUN_TIME_SECONDS = 60


class Command(NoArgsCommand):
    help = """This needs transactions signaling enabled. Polls\
     incoming transactions via listtransactions -bitcoind call, and checks\
      the balances accordingly.
      To enable, add this command to your cron, and set
      BITCOIN_TRANSACTION_SIGNALING = True
      After that, you will get signals from the transactions you do.
      balance_changed = django.dispatch.Signal(providing_args=["balance", "changed"])
"""

    def handle_noargs(self, **options):
        start_time = time()
        last_check_time = None
        print "starting overall1", time() - start_time, datetime.datetime.now()
        while time() - start_time < float(RUN_TIME_SECONDS):
            print "starting round", time() - start_time
            # print "starting standard", time() - start_time
            transactions = bitcoind.bitcoind_api.listtransactions("*", 50, 0)
            for t in transactions:
                if t[u'category'] != u'immature' and (not last_check_time or (int(t['time'])) >= last_check_time) and t[u'amount']>0:
                    dps = DepositTransaction.objects.filter(txid=t[u'txid'])
                    if dps.count() == 0:
                        try:
                            ba = BitcoinAddress.objects.get(address=t['address'], active=True, wallet__isnull=False)
                            if ba:
                                ba.query_bitcoind(0, triggered_tx=t[u'txid'])
                            last_check_time = int(t['time'])
                        except BitcoinAddress.DoesNotExist:
                            pass
                    elif Decimal(str(t[u'amount'])) == dps[0].amount and int(t[u'confirmations'])>dps[0].confirmations and dps.count()==1:
                        dp = dps[0]
                        DepositTransaction.objects.filter(id=dp.id).update(confirmations=int(t[u'confirmations']))
                        if int(t[u'confirmations']) >= settings.BITCOIN_MINIMUM_CONFIRMATIONS:
                            dp.address.query_bitcoind(triggered_tx=t[u'txid'])
                elif not last_check_time:
                    last_check_time = int(t['time'])
            print "done listtransactions checking, starting checking least_received>least_received_confirmed", time() - start_time
            for ba in BitcoinAddress.objects.filter(active=True,
                wallet__isnull=False).extra(where=["least_received>least_received_confirmed"]).order_by("?")[:5]:
                ba.query_bitcoind()
            print "done, sleeping...", time() - start_time
            sleep(1)
        print "finished all", datetime.datetime.now()

########NEW FILE########
__FILENAME__ = CreateInitialDepositTransactions
from django.core.management.base import NoArgsCommand, BaseCommand
from django.conf import settings
import os
import sys
import re
import codecs
import commands
import urllib2
import urllib
import json
import random
from time import sleep
import math
import datetime
from django_bitcoin.models import DepositTransaction, BitcoinAddress, WalletTransaction, Wallet
from django.db.models import Avg, Max, Min, Sum
from decimal import Decimal

from distributedlock import distributedlock, MemcachedLock, LockNotAcquiredError
from django.core.cache import cache

from django.db import transaction

from optparse import make_option
from django.contrib.auth.models import User


@transaction.commit_manually
def flush_transaction():
    transaction.commit()


def CacheLock(key, lock=None, blocking=True, timeout=10):
    if lock is None:
        lock = MemcachedLock(key=key, client=cache, timeout=timeout)

    return distributedlock(key, lock, blocking)

import pytz  # 3rd party

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-u", "--users",
            action='store', type="str", dest="users"),
        )
    help = 'This creates the revenue report for a specific month.'

    def handle(self, *args, **options):

        dt_now = datetime.datetime.now()

        wallet_query = Wallet.objects.all()

        if options['users']:
            w_ids = []
            for u in options['users'].split(","):
                w_ids.append(User.objects.get(username=u).get_profile().wallet.id)
            wallet_query = wallet_query.filter(id__in=w_ids)

        for w in wallet_query:
            for ba in BitcoinAddress.objects.filter(wallet=w).exclude(migrated_to_transactions=True):
                original_balance = ba.wallet.last_balance
                with CacheLock('query_bitcoind_'+str(ba.id)):
                    dts = DepositTransaction.objects.filter(address=ba, wallet=ba.wallet)
                    for dp in dts:
                        wt = WalletTransaction.objects.create(amount=dp.amount, to_wallet=ba.wallet, created_at=ba.created_at,
                        description=ba.address, deposit_address=ba)
                        DepositTransaction.objects.filter(id=dp.id).update(transaction=wt)
                    s = dts.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
                    if s < ba.least_received_confirmed and ba.least_received_confirmed > 0:
                        wt = WalletTransaction.objects.create(amount=ba.least_received_confirmed - s, to_wallet=ba.wallet, created_at=ba.created_at,
                            description=u"Deposits "+ba.address+u" "+ ba.created_at.strftime("%x")  + u" - "+ dt_now.strftime("%x"),
                            deposit_address=ba)
                        dt = DepositTransaction.objects.create(address=ba, amount=wt.amount, wallet=ba.wallet,
                            created_at=ba.created_at, transaction=wt, confirmations=settings.BITCOIN_MINIMUM_CONFIRMATIONS,
                            description=u"Deposits "+ba.address+u" "+ ba.created_at.strftime("%x")  + u" - "+ dt_now.strftime("%x"))
                        print dt.description, dt.amount
                    elif s > ba.least_received_confirmed:
                        print "TOO MUCH!!!", ba.address
                    elif s < ba.least_received_confirmed:
                        print "too little, address", ba.address, ba.least_received_confirmed, s
                    BitcoinAddress.objects.filter(id=ba.id).update(migrated_to_transactions=True)
                flush_transaction()
                wt_sum = WalletTransaction.objects.filter(deposit_address=ba).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
                if wt_sum != ba.least_received_confirmed:
                    raise Exception("wrong amount! "+str(ba.address))
                w = Wallet.objects.get(id=ba.wallet.id)
                if original_balance != w.total_balance_sql():
                    raise Exception("wrong wallet amount! "+str(ba.address))
                tot_received = WalletTransaction.objects.filter(from_wallet=None).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
                tot_received_bitcoinaddress = BitcoinAddress.objects.filter(migrated_to_transactions=True)\
                    .aggregate(Sum('least_received_confirmed'))['least_received_confirmed__sum'] or Decimal(0)
                if tot_received != tot_received_bitcoinaddress:
                    raise Exception("wrong total receive amount! "+str(ba.address))

        print "Migrated, doing final check..."
        tot_received = WalletTransaction.objects.filter(from_wallet=None).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        tot_received_bitcoinaddress = BitcoinAddress.objects.filter(migrated_to_transactions=True)\
            .aggregate(Sum('least_received_confirmed'))['least_received_confirmed__sum'] or Decimal(0)
        if tot_received != tot_received_bitcoinaddress:
            raise Exception("wrong total receive amount! "+str(ba.address))
        print "Final check succesfull."

########NEW FILE########
__FILENAME__ = ExtensiveWalletTest
from django.core.management.base import NoArgsCommand
from django.conf import settings
import os
import sys
import re
import codecs
import commands
import urllib2
import urllib
import json
import random
from time import sleep
import math
import datetime
from django_bitcoin import Wallet
from django_bitcoin.utils import bitcoind
from decimal import Decimal
import warnings
import twitter

class Command(NoArgsCommand):
    help = 'Tweet with LocalBitcoins.com account.'

    def handle_noargs(self, **options):
        final_wallets = []
        process_num = random.randint(0, 1000)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore",category=RuntimeWarning)
            for i in range(0, 3):
                w = Wallet.objects.create()
                # print "starting w.id", w.id
                addr = w.receiving_address()
                # print "taddr", w.id, addr
                final_wallets.append(w)
        for w in final_wallets:
            if w.total_balance_sql() > 0:
                print str(process_num) + " error", w.id
                raise Exception("damn!")
            # print "final", w.id, w.static_receiving_address(), w.receiving_address()
        print str(process_num) + " loading 0.001 to wallet #1", w1.static_receiving_address()
        w1 = final_wallets[0]
        w2 = final_wallets[1]
        w3 = final_wallets[2]
        bitcoind.send(w1.static_receiving_address(), Decimal("0.001"))
        while w1.total_balance_sql() <= 0:
            sleep(1)
            w1 = Wallet.objects.get(id=w1.id)
            # print w1.last_balance
        print str(process_num) + " w1.last_balance " + str(w1.last_balance)
        print str(process_num) + "loading"
        w1.send_to_wallet(w2, Decimal("0.0002"))
        w1.send_to_wallet(w3, Decimal("0.0005"))
        w3.send_to_address(w1, Decimal("0.0004"))
        print str(process_num) + " w1.last_balance " + str(w1.last_balance)
        print str(process_num) + " w2.last_balance " + str(w2.last_balance)
        print str(process_num) + " w3.last_balance " + str(w3.last_balance)
        while w1.total_balance_sql() <= 0:
            sleep(1)
            w1 = Wallet.objects.get(id=w1.id)
        print str(process_num) + "catching"
        print str(process_num) + " w1.last_balance " + str(w1.last_balance)
        print str(process_num) + " w2.last_balance " + str(w2.last_balance)
        print str(process_num) + " w3.last_balance " + str(w3.last_balance)



########NEW FILE########
__FILENAME__ = FixLastBalancesConcurrency
from django.core.management.base import NoArgsCommand
from time import sleep, time
from django_bitcoin.utils import bitcoind
from django_bitcoin.models import BitcoinAddress
from django_bitcoin.models import Wallet
from django.conf import settings
from decimal import Decimal


class Command(NoArgsCommand):
    help = """fix balances
"""

    def handle_noargs(self, **options):
        print "starting..."
        for w in Wallet.objects.all():
            w.last_balance = w.total_balance()
            w.save()




########NEW FILE########
__FILENAME__ = FlushBitcoin
from django.core.management.base import NoArgsCommand
from django.conf import settings
import os
import sys
import re
import codecs
import commands
import urllib2
import urllib
import json
import numpy
import random
from time import sleep
import math
from django_bitcoin.models import RefillPaymentQueue, UpdatePayments

class Command(NoArgsCommand):
    help = 'Create a profile object for users which do not have one.'

    def handle_noargs(self, **options):
        RefillPaymentQueue()
        UpdatePayments()

########NEW FILE########
__FILENAME__ = GetHistoricalRates
from django.core.management.base import NoArgsCommand
from django.conf import settings
import os
import sys
import re
import codecs
import commands
import urllib2
import urllib
import json
import random
from time import sleep
import math
import datetime
from django_bitcoin.models import get_historical_price

import pytz  # 3rd party

class Command(NoArgsCommand):
    help = 'Create a profile object for users which do not have one.'

    def handle_noargs(self, **options):
        u = datetime.datetime.utcnow()
        u = u.replace(tzinfo=pytz.utc)
        print u, get_historical_price()

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Transaction'
        db.create_table('django_bitcoin_transaction', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=16, decimal_places=8)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal('django_bitcoin', ['Transaction'])

        # Adding model 'BitcoinAddress'
        db.create_table('django_bitcoin_bitcoinaddress', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('least_received', self.gf('django.db.models.fields.DecimalField')(default='0', max_digits=16, decimal_places=8)),
        ))
        db.send_create_signal('django_bitcoin', ['BitcoinAddress'])

        # Adding model 'Payment'
        db.create_table('django_bitcoin_payment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=16, decimal_places=8)),
            ('amount_paid', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=16, decimal_places=8)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')()),
            ('paid_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('withdrawn_total', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=16, decimal_places=8)),
        ))
        db.send_create_signal('django_bitcoin', ['Payment'])

        # Adding M2M table for field transactions on 'Payment'
        db.create_table('django_bitcoin_payment_transactions', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('payment', models.ForeignKey(orm['django_bitcoin.payment'], null=False)),
            ('transaction', models.ForeignKey(orm['django_bitcoin.transaction'], null=False))
        ))
        db.create_unique('django_bitcoin_payment_transactions', ['payment_id', 'transaction_id'])

        # Adding model 'WalletTransaction'
        db.create_table('django_bitcoin_wallettransaction', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('from_wallet', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sent_transactions', to=orm['django_bitcoin.Wallet'])),
            ('to_wallet', self.gf('django.db.models.fields.related.ForeignKey')(related_name='received_transactions', null=True, to=orm['django_bitcoin.Wallet'])),
            ('to_bitcoinaddress', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=16, decimal_places=8)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
        ))
        db.send_create_signal('django_bitcoin', ['WalletTransaction'])

        # Adding model 'Wallet'
        db.create_table('django_bitcoin_wallet', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')()),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
        ))
        db.send_create_signal('django_bitcoin', ['Wallet'])

        # Adding M2M table for field addresses on 'Wallet'
        db.create_table('django_bitcoin_wallet_addresses', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('wallet', models.ForeignKey(orm['django_bitcoin.wallet'], null=False)),
            ('bitcoinaddress', models.ForeignKey(orm['django_bitcoin.bitcoinaddress'], null=False))
        ))
        db.create_unique('django_bitcoin_wallet_addresses', ['wallet_id', 'bitcoinaddress_id'])


    def backwards(self, orm):
        
        # Deleting model 'Transaction'
        db.delete_table('django_bitcoin_transaction')

        # Deleting model 'BitcoinAddress'
        db.delete_table('django_bitcoin_bitcoinaddress')

        # Deleting model 'Payment'
        db.delete_table('django_bitcoin_payment')

        # Removing M2M table for field transactions on 'Payment'
        db.delete_table('django_bitcoin_payment_transactions')

        # Deleting model 'WalletTransaction'
        db.delete_table('django_bitcoin_wallettransaction')

        # Deleting model 'Wallet'
        db.delete_table('django_bitcoin_wallet')

        # Removing M2M table for field addresses on 'Wallet'
        db.delete_table('django_bitcoin_wallet_addresses')


    models = {
        'django_bitcoin.bitcoinaddress': {
            'Meta': {'object_name': 'BitcoinAddress'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'least_received': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.payment': {
            'Meta': {'object_name': 'Payment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'amount_paid': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'paid_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'transactions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Transaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {}),
            'withdrawn_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'django_bitcoin.wallet': {
            'Meta': {'object_name': 'Wallet'},
            'addresses': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.BitcoinAddress']", 'symmetrical': 'False'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'transactions_with': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Wallet']", 'through': "orm['django_bitcoin.WalletTransaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'django_bitcoin.wallettransaction': {
            'Meta': {'object_name': 'WalletTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'from_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_transactions'", 'to': "orm['django_bitcoin.Wallet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'to_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'received_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        }
    }

    complete_apps = ['django_bitcoin']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_bitcoinaddress_label
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'BitcoinAddress.label'
        db.add_column('django_bitcoin_bitcoinaddress', 'label', self.gf('django.db.models.fields.CharField')(default=None, max_length=50, null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'BitcoinAddress.label'
        db.delete_column('django_bitcoin_bitcoinaddress', 'label')


    models = {
        'django_bitcoin.bitcoinaddress': {
            'Meta': {'object_name': 'BitcoinAddress'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'least_received': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.payment': {
            'Meta': {'object_name': 'Payment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'amount_paid': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'paid_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'transactions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Transaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {}),
            'withdrawn_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'django_bitcoin.wallet': {
            'Meta': {'object_name': 'Wallet'},
            'addresses': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.BitcoinAddress']", 'symmetrical': 'False'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'transactions_with': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Wallet']", 'through': "orm['django_bitcoin.WalletTransaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'django_bitcoin.wallettransaction': {
            'Meta': {'object_name': 'WalletTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'from_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_transactions'", 'to': "orm['django_bitcoin.Wallet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'to_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'received_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        }
    }

    complete_apps = ['django_bitcoin']

########NEW FILE########
__FILENAME__ = 0003_auto__add_unique_bitcoinaddress_address
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding unique constraint on 'BitcoinAddress', fields ['address']
        db.create_unique('django_bitcoin_bitcoinaddress', ['address'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'BitcoinAddress', fields ['address']
        db.delete_unique('django_bitcoin_bitcoinaddress', ['address'])


    models = {
        'django_bitcoin.bitcoinaddress': {
            'Meta': {'object_name': 'BitcoinAddress'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'least_received': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.payment': {
            'Meta': {'object_name': 'Payment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'amount_paid': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'paid_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'transactions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Transaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {}),
            'withdrawn_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'django_bitcoin.wallet': {
            'Meta': {'object_name': 'Wallet'},
            'addresses': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.BitcoinAddress']", 'symmetrical': 'False'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'transactions_with': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Wallet']", 'through': "orm['django_bitcoin.WalletTransaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'django_bitcoin.wallettransaction': {
            'Meta': {'object_name': 'WalletTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'from_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_transactions'", 'to': "orm['django_bitcoin.Wallet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'to_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'received_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        }
    }

    complete_apps = ['django_bitcoin']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_bitcoinaddress_least_received_confirmed
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'BitcoinAddress.least_received_confirmed'
        db.add_column('django_bitcoin_bitcoinaddress', 'least_received_confirmed',
                      self.gf('django.db.models.fields.DecimalField')(default='0', max_digits=16, decimal_places=8),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'BitcoinAddress.least_received_confirmed'
        db.delete_column('django_bitcoin_bitcoinaddress', 'least_received_confirmed')

    models = {
        'django_bitcoin.bitcoinaddress': {
            'Meta': {'object_name': 'BitcoinAddress'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'least_received': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'least_received_confirmed': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.payment': {
            'Meta': {'object_name': 'Payment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'amount_paid': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'paid_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'transactions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Transaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {}),
            'withdrawn_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'django_bitcoin.wallet': {
            'Meta': {'object_name': 'Wallet'},
            'addresses': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.BitcoinAddress']", 'symmetrical': 'False'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'transactions_with': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Wallet']", 'through': "orm['django_bitcoin.WalletTransaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'django_bitcoin.wallettransaction': {
            'Meta': {'object_name': 'WalletTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'from_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_transactions'", 'to': "orm['django_bitcoin.Wallet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'to_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'received_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        }
    }

    complete_apps = ['django_bitcoin']
########NEW FILE########
__FILENAME__ = 0005_auto__add_field_bitcoinaddress_wallet
# -*- coding: utf-8 -*-
import datetime
from south.db import db

from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'BitcoinAddress.wallet'
        db.add_column('django_bitcoin_bitcoinaddress', 'wallet',
                      self.gf('django.db.models.fields.related.ForeignKey')(related_name='addresses', null=True, to=orm['django_bitcoin.Wallet']),
                      keep_default=False)

        sql = """
        UPDATE django_bitcoin_bitcoinaddress SET wallet_id = 
        (SELECT wallet_id FROM django_bitcoin_wallet_addresses WHERE bitcoinaddress_id=django_bitcoin_bitcoinaddress.id LIMIT 1)
        """

        db.execute(sql)

        sql = """
        SELECT id, (SELECT wallet_id FROM django_bitcoin_wallet_addresses WHERE bitcoinaddress_id=django_bitcoin_bitcoinaddress.id LIMIT 1)
        FROM django_bitcoin_bitcoinaddress;
        """

        # Removing M2M table for field addresses on 'Wallet'
        db.delete_table('django_bitcoin_wallet_addresses')


    def backwards(self, orm):
        # Deleting field 'BitcoinAddress.wallet'
        raise RuntimeError("Cannot reverse this migration.")


    models = {
        'django_bitcoin.bitcoinaddress': {
            'Meta': {'object_name': 'BitcoinAddress'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'least_received': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'least_received_confirmed': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'addresses'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.payment': {
            'Meta': {'object_name': 'Payment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'amount_paid': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'paid_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'transactions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Transaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {}),
            'withdrawn_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'django_bitcoin.wallet': {
            'Meta': {'object_name': 'Wallet'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'transactions_with': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Wallet']", 'through': "orm['django_bitcoin.WalletTransaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'django_bitcoin.wallettransaction': {
            'Meta': {'object_name': 'WalletTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'from_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_transactions'", 'to': "orm['django_bitcoin.Wallet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'to_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'received_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        }
    }

    complete_apps = ['django_bitcoin']
########NEW FILE########
__FILENAME__ = 0006_auto__add_field_wallet_transaction_counter
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Wallet.transaction_counter'
        db.add_column('django_bitcoin_wallet', 'transaction_counter',
                      self.gf('django.db.models.fields.IntegerField')(default=1),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Wallet.transaction_counter'
        db.delete_column('django_bitcoin_wallet', 'transaction_counter')


    models = {
        'django_bitcoin.bitcoinaddress': {
            'Meta': {'object_name': 'BitcoinAddress'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'least_received': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'least_received_confirmed': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'addresses'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.payment': {
            'Meta': {'object_name': 'Payment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'amount_paid': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'paid_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'transactions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Transaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {}),
            'withdrawn_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'django_bitcoin.wallet': {
            'Meta': {'object_name': 'Wallet'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'transaction_counter': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'transactions_with': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Wallet']", 'through': "orm['django_bitcoin.WalletTransaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'django_bitcoin.wallettransaction': {
            'Meta': {'object_name': 'WalletTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'from_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_transactions'", 'to': "orm['django_bitcoin.Wallet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'to_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'received_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        }
    }

    complete_apps = ['django_bitcoin']
########NEW FILE########
__FILENAME__ = 0007_auto__add_field_wallet_last_balance
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Wallet.last_balance'
        db.add_column('django_bitcoin_wallet', 'last_balance',
                      self.gf('django.db.models.fields.DecimalField')(default='0', max_digits=16, decimal_places=8),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Wallet.last_balance'
        db.delete_column('django_bitcoin_wallet', 'last_balance')


    models = {
        'django_bitcoin.bitcoinaddress': {
            'Meta': {'object_name': 'BitcoinAddress'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'least_received': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'least_received_confirmed': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'addresses'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.payment': {
            'Meta': {'object_name': 'Payment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'amount_paid': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'paid_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'transactions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Transaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {}),
            'withdrawn_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'django_bitcoin.wallet': {
            'Meta': {'object_name': 'Wallet'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'last_balance': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '5', 'decimal_places': '2'}),
            'transaction_counter': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'transactions_with': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Wallet']", 'through': "orm['django_bitcoin.WalletTransaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'django_bitcoin.wallettransaction': {
            'Meta': {'object_name': 'WalletTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'from_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_transactions'", 'to': "orm['django_bitcoin.Wallet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'to_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'received_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        }
    }

    complete_apps = ['django_bitcoin']
########NEW FILE########
__FILENAME__ = 0008_auto__add_historicalprice__chg_field_wallet_last_balance
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'HistoricalPrice'
        db.create_table('django_bitcoin_historicalprice', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('price', self.gf('django.db.models.fields.DecimalField')(max_digits=16, decimal_places=2)),
            ('params', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('currency', self.gf('django.db.models.fields.CharField')(max_length=10)),
        ))
        db.send_create_signal('django_bitcoin', ['HistoricalPrice'])


        # Changing field 'Wallet.last_balance'
        db.alter_column('django_bitcoin_wallet', 'last_balance', self.gf('django.db.models.fields.DecimalField')(max_digits=16, decimal_places=8))

    def backwards(self, orm):
        # Deleting model 'HistoricalPrice'
        db.delete_table('django_bitcoin_historicalprice')


        # Changing field 'Wallet.last_balance'
        db.alter_column('django_bitcoin_wallet', 'last_balance', self.gf('django.db.models.fields.DecimalField')(max_digits=5, decimal_places=2))

    models = {
        'django_bitcoin.bitcoinaddress': {
            'Meta': {'object_name': 'BitcoinAddress'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'least_received': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'least_received_confirmed': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'addresses'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.historicalprice': {
            'Meta': {'object_name': 'HistoricalPrice'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'params': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '16', 'decimal_places': '2'})
        },
        'django_bitcoin.payment': {
            'Meta': {'object_name': 'Payment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'amount_paid': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'paid_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'transactions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Transaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {}),
            'withdrawn_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'django_bitcoin.wallet': {
            'Meta': {'object_name': 'Wallet'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'last_balance': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'transaction_counter': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'transactions_with': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Wallet']", 'through': "orm['django_bitcoin.WalletTransaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'django_bitcoin.wallettransaction': {
            'Meta': {'object_name': 'WalletTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'from_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_transactions'", 'to': "orm['django_bitcoin.Wallet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'to_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'received_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        }
    }

    complete_apps = ['django_bitcoin']
########NEW FILE########
__FILENAME__ = 0009_auto__add_deposittransaction
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'DepositTransaction'
        db.create_table('django_bitcoin_deposittransaction', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('address', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['django_bitcoin.BitcoinAddress'])),
            ('amount', self.gf('django.db.models.fields.DecimalField')(default='0', max_digits=16, decimal_places=8)),
            ('description', self.gf('django.db.models.fields.CharField')(default=None, max_length=100, null=True, blank=True)),
            ('wallet', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['django_bitcoin.Wallet'])),
        ))
        db.send_create_signal('django_bitcoin', ['DepositTransaction'])


    def backwards(self, orm):
        # Deleting model 'DepositTransaction'
        db.delete_table('django_bitcoin_deposittransaction')


    models = {
        'django_bitcoin.bitcoinaddress': {
            'Meta': {'object_name': 'BitcoinAddress'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'least_received': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'least_received_confirmed': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'addresses'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.deposittransaction': {
            'Meta': {'object_name': 'DepositTransaction'},
            'address': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.BitcoinAddress']"}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.historicalprice': {
            'Meta': {'object_name': 'HistoricalPrice'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'params': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '16', 'decimal_places': '2'})
        },
        'django_bitcoin.payment': {
            'Meta': {'object_name': 'Payment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'amount_paid': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'paid_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'transactions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Transaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {}),
            'withdrawn_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'django_bitcoin.wallet': {
            'Meta': {'object_name': 'Wallet'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'last_balance': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'transaction_counter': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'transactions_with': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Wallet']", 'through': "orm['django_bitcoin.WalletTransaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'django_bitcoin.wallettransaction': {
            'Meta': {'object_name': 'WalletTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'from_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_transactions'", 'to': "orm['django_bitcoin.Wallet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'to_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'received_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        }
    }

    complete_apps = ['django_bitcoin']
########NEW FILE########
__FILENAME__ = 0010_auto__add_field_deposittransaction_confirmations__add_field_deposittra
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'DepositTransaction.confirmations'
        db.add_column('django_bitcoin_deposittransaction', 'confirmations',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)

        # Adding field 'DepositTransaction.txid'
        db.add_column('django_bitcoin_deposittransaction', 'txid',
                      self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True),
                      keep_default=False)

        # Adding field 'WalletTransaction.txid'
        db.add_column('django_bitcoin_wallettransaction', 'txid',
                      self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'DepositTransaction.confirmations'
        db.delete_column('django_bitcoin_deposittransaction', 'confirmations')

        # Deleting field 'DepositTransaction.txid'
        db.delete_column('django_bitcoin_deposittransaction', 'txid')

        # Deleting field 'WalletTransaction.txid'
        db.delete_column('django_bitcoin_wallettransaction', 'txid')


    models = {
        'django_bitcoin.bitcoinaddress': {
            'Meta': {'object_name': 'BitcoinAddress'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'least_received': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'least_received_confirmed': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'addresses'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.deposittransaction': {
            'Meta': {'object_name': 'DepositTransaction'},
            'address': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.BitcoinAddress']"}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'confirmations': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'txid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.historicalprice': {
            'Meta': {'object_name': 'HistoricalPrice'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'params': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '16', 'decimal_places': '2'})
        },
        'django_bitcoin.payment': {
            'Meta': {'object_name': 'Payment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'amount_paid': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'paid_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'transactions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Transaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {}),
            'withdrawn_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'django_bitcoin.wallet': {
            'Meta': {'object_name': 'Wallet'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'last_balance': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'transaction_counter': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'transactions_with': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Wallet']", 'through': "orm['django_bitcoin.WalletTransaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'django_bitcoin.wallettransaction': {
            'Meta': {'object_name': 'WalletTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'from_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_transactions'", 'to': "orm['django_bitcoin.Wallet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'to_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'received_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"}),
            'txid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['django_bitcoin']
########NEW FILE########
__FILENAME__ = 0011_auto__add_outgoingtransaction__add_field_wallettransaction_outgoing_tr
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'OutgoingTransaction'
        db.create_table('django_bitcoin_outgoingtransaction', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('expires_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('executed_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('under_execution', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('to_bitcoinaddress', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=16, decimal_places=8)),
            ('txid', self.gf('django.db.models.fields.CharField')(default=None, max_length=100, null=True, blank=True)),
        ))
        db.send_create_signal('django_bitcoin', ['OutgoingTransaction'])

        # Adding field 'WalletTransaction.outgoing_transaction'
        db.add_column('django_bitcoin_wallettransaction', 'outgoing_transaction',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['django_bitcoin.OutgoingTransaction'], null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting model 'OutgoingTransaction'
        db.delete_table('django_bitcoin_outgoingtransaction')

        # Deleting field 'WalletTransaction.outgoing_transaction'
        db.delete_column('django_bitcoin_wallettransaction', 'outgoing_transaction_id')


    models = {
        'django_bitcoin.bitcoinaddress': {
            'Meta': {'object_name': 'BitcoinAddress'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'least_received': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'least_received_confirmed': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'addresses'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.deposittransaction': {
            'Meta': {'object_name': 'DepositTransaction'},
            'address': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.BitcoinAddress']"}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'confirmations': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'txid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.historicalprice': {
            'Meta': {'object_name': 'HistoricalPrice'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'params': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '16', 'decimal_places': '2'})
        },
        'django_bitcoin.outgoingtransaction': {
            'Meta': {'object_name': 'OutgoingTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'executed_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'expires_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'txid': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'under_execution': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'django_bitcoin.payment': {
            'Meta': {'object_name': 'Payment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'amount_paid': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'paid_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'transactions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Transaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {}),
            'withdrawn_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'django_bitcoin.wallet': {
            'Meta': {'object_name': 'Wallet'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'last_balance': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'transaction_counter': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'transactions_with': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Wallet']", 'through': "orm['django_bitcoin.WalletTransaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'django_bitcoin.wallettransaction': {
            'Meta': {'object_name': 'WalletTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'from_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_transactions'", 'to': "orm['django_bitcoin.Wallet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'outgoing_transaction': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['django_bitcoin.OutgoingTransaction']", 'null': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'to_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'received_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"}),
            'txid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['django_bitcoin']
########NEW FILE########
__FILENAME__ = 0012_auto__add_field_deposittransaction_transaction__chg_field_wallettransa
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'DepositTransaction.transaction'
        db.add_column('django_bitcoin_deposittransaction', 'transaction',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['django_bitcoin.WalletTransaction'], null=True),
                      keep_default=False)


        # Changing field 'WalletTransaction.from_wallet'
        db.alter_column('django_bitcoin_wallettransaction', 'from_wallet_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['django_bitcoin.Wallet']))
        # Adding field 'BitcoinAddress.migrated_to_transactions'
        db.add_column('django_bitcoin_bitcoinaddress', 'migrated_to_transactions',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        pass
        # Deleting field 'DepositTransaction.transaction'
        # db.delete_column('django_bitcoin_deposittransaction', 'transaction_id')


        # User chose to not deal with backwards NULL issues for 'WalletTransaction.from_wallet'
        #raise RuntimeError("Cannot reverse this migration. 'WalletTransaction.from_wallet' and its values cannot be restored.")
        # Deleting field 'BitcoinAddress.migrated_to_transactions'
        # db.delete_column('django_bitcoin_bitcoinaddress', 'migrated_to_transactions')


    models = {
        'django_bitcoin.bitcoinaddress': {
            'Meta': {'object_name': 'BitcoinAddress'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'least_received': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'least_received_confirmed': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'migrated_to_transactions': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'addresses'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.deposittransaction': {
            'Meta': {'object_name': 'DepositTransaction'},
            'address': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.BitcoinAddress']"}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'confirmations': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'transaction': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['django_bitcoin.WalletTransaction']", 'null': 'True'}),
            'txid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.historicalprice': {
            'Meta': {'object_name': 'HistoricalPrice'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'params': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '16', 'decimal_places': '2'})
        },
        'django_bitcoin.outgoingtransaction': {
            'Meta': {'object_name': 'OutgoingTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'executed_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'expires_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'txid': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'under_execution': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'django_bitcoin.payment': {
            'Meta': {'object_name': 'Payment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'amount_paid': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'paid_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'transactions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Transaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {}),
            'withdrawn_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'django_bitcoin.wallet': {
            'Meta': {'object_name': 'Wallet'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'last_balance': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'transaction_counter': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'transactions_with': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Wallet']", 'through': "orm['django_bitcoin.WalletTransaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'django_bitcoin.wallettransaction': {
            'Meta': {'object_name': 'WalletTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'from_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'outgoing_transaction': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['django_bitcoin.OutgoingTransaction']", 'null': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'to_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'received_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"}),
            'txid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['django_bitcoin']
########NEW FILE########
__FILENAME__ = 0013_auto__add_field_wallettransaction_deposit_address
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'WalletTransaction.deposit_address'
        db.add_column('django_bitcoin_wallettransaction', 'deposit_address',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['django_bitcoin.BitcoinAddress'], null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'WalletTransaction.deposit_address'
        db.delete_column('django_bitcoin_wallettransaction', 'deposit_address_id')


    models = {
        'django_bitcoin.bitcoinaddress': {
            'Meta': {'object_name': 'BitcoinAddress'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'least_received': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'least_received_confirmed': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'migrated_to_transactions': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'addresses'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.deposittransaction': {
            'Meta': {'object_name': 'DepositTransaction'},
            'address': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.BitcoinAddress']"}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'confirmations': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'transaction': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['django_bitcoin.WalletTransaction']", 'null': 'True'}),
            'txid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.historicalprice': {
            'Meta': {'object_name': 'HistoricalPrice'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'params': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '16', 'decimal_places': '2'})
        },
        'django_bitcoin.outgoingtransaction': {
            'Meta': {'object_name': 'OutgoingTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'executed_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'expires_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'txid': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'under_execution': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'django_bitcoin.payment': {
            'Meta': {'object_name': 'Payment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'amount_paid': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'paid_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'transactions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Transaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {}),
            'withdrawn_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'django_bitcoin.wallet': {
            'Meta': {'object_name': 'Wallet'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'last_balance': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'transaction_counter': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'transactions_with': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Wallet']", 'through': "orm['django_bitcoin.WalletTransaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'django_bitcoin.wallettransaction': {
            'Meta': {'object_name': 'WalletTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'deposit_address': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.BitcoinAddress']", 'null': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'from_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'outgoing_transaction': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['django_bitcoin.OutgoingTransaction']", 'null': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'to_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'received_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"}),
            'txid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['django_bitcoin']
########NEW FILE########
__FILENAME__ = 0014_auto__add_field_deposittransaction_under_execution
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'DepositTransaction.under_execution'
        db.add_column('django_bitcoin_deposittransaction', 'under_execution',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'DepositTransaction.under_execution'
        db.delete_column('django_bitcoin_deposittransaction', 'under_execution')


    models = {
        'django_bitcoin.bitcoinaddress': {
            'Meta': {'object_name': 'BitcoinAddress'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'least_received': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'least_received_confirmed': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'migrated_to_transactions': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'addresses'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.deposittransaction': {
            'Meta': {'object_name': 'DepositTransaction'},
            'address': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.BitcoinAddress']"}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'confirmations': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'transaction': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['django_bitcoin.WalletTransaction']", 'null': 'True'}),
            'txid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'under_execution': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.historicalprice': {
            'Meta': {'object_name': 'HistoricalPrice'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'params': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '16', 'decimal_places': '2'})
        },
        'django_bitcoin.outgoingtransaction': {
            'Meta': {'object_name': 'OutgoingTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'executed_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'expires_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'txid': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'under_execution': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'django_bitcoin.payment': {
            'Meta': {'object_name': 'Payment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'amount_paid': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'paid_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'transactions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Transaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {}),
            'withdrawn_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'django_bitcoin.wallet': {
            'Meta': {'object_name': 'Wallet'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'last_balance': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'transaction_counter': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'transactions_with': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Wallet']", 'through': "orm['django_bitcoin.WalletTransaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'django_bitcoin.wallettransaction': {
            'Meta': {'object_name': 'WalletTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'deposit_address': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.BitcoinAddress']", 'null': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'from_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'outgoing_transaction': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['django_bitcoin.OutgoingTransaction']", 'null': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'to_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'received_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"}),
            'txid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['django_bitcoin']
########NEW FILE########
__FILENAME__ = 0015_auto__add_field_wallettransaction_deposit_transaction
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'WalletTransaction.deposit_transaction'
        db.add_column('django_bitcoin_wallettransaction', 'deposit_transaction',
                      self.gf('django.db.models.fields.related.OneToOneField')(to=orm['django_bitcoin.DepositTransaction'], unique=True, null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'WalletTransaction.deposit_transaction'
        db.delete_column('django_bitcoin_wallettransaction', 'deposit_transaction_id')


    models = {
        'django_bitcoin.bitcoinaddress': {
            'Meta': {'object_name': 'BitcoinAddress'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'least_received': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'least_received_confirmed': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'migrated_to_transactions': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'addresses'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.deposittransaction': {
            'Meta': {'object_name': 'DepositTransaction'},
            'address': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.BitcoinAddress']"}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'confirmations': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'transaction': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['django_bitcoin.WalletTransaction']", 'null': 'True'}),
            'txid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'under_execution': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'wallet': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.Wallet']"})
        },
        'django_bitcoin.historicalprice': {
            'Meta': {'object_name': 'HistoricalPrice'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'params': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '16', 'decimal_places': '2'})
        },
        'django_bitcoin.outgoingtransaction': {
            'Meta': {'object_name': 'OutgoingTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'executed_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'expires_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'txid': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'under_execution': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'django_bitcoin.payment': {
            'Meta': {'object_name': 'Payment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'amount_paid': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'paid_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'transactions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Transaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {}),
            'withdrawn_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'})
        },
        'django_bitcoin.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'django_bitcoin.wallet': {
            'Meta': {'object_name': 'Wallet'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'last_balance': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '16', 'decimal_places': '8'}),
            'transaction_counter': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'transactions_with': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['django_bitcoin.Wallet']", 'through': "orm['django_bitcoin.WalletTransaction']", 'symmetrical': 'False'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'django_bitcoin.wallettransaction': {
            'Meta': {'object_name': 'WalletTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '16', 'decimal_places': '8'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'deposit_address': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_bitcoin.BitcoinAddress']", 'null': 'True'}),
            'deposit_transaction': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['django_bitcoin.DepositTransaction']", 'unique': 'True', 'null': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'from_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'outgoing_transaction': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['django_bitcoin.OutgoingTransaction']", 'null': 'True'}),
            'to_bitcoinaddress': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'to_wallet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'received_transactions'", 'null': 'True', 'to': "orm['django_bitcoin.Wallet']"}),
            'txid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['django_bitcoin']
########NEW FILE########
__FILENAME__ = mock_bitcoin_objects
# vim: tabstop=4 expandtab autoindent shiftwidth=4 fileencoding=utf-8

import decimal

import mock

from django_bitcoin import utils

## bitcoin mock objects

## Patch your test cases which access bitcoin with these decorators
## eg:
#@mock.patch('django_bitcoin.utils.bitcoind', new=mock_bitcoin_objects.mock_bitcoind)
#@mock.patch('django_bitcoin.models.bitcoind', new=mock_bitcoin_objects.mock_bitcoind)
#def test_wallet_received():
#    ...

import random
import string
ADDR_CHARS = '%s%s' % (string.letters, string.digits)
ADDR_LEN = 34
def create_address(self):
    return ''.join([random.choice(ADDR_CHARS) for i in xrange(ADDR_LEN)])

## FIRST
mock_bitcoind = mock.Mock(wraps=utils.bitcoind, spec=utils.bitcoind)

mock_received_123 = mock.Mock()
mock_received_123.return_value = decimal.Decimal(123)

mock_bitcoind.total_received = mock.mocksignature(utils.bitcoind.total_received, mock=mock_received_123)

mock_bitcoind.send = mock.mocksignature(utils.bitcoind.send)

mock_bitcoind_address = mock.Mock()
mock_bitcoind_address.side_effect = create_address

mock_bitcoind.create_address = mock.mocksignature(utils.bitcoind.create_address, mock=mock_bitcoind_address)

## SECOND
mock_bitcoind_other = mock.Mock(wraps=utils.bitcoind, spec=utils.bitcoind)

mock_received_65535 = mock.Mock()
mock_received_65535.return_value = decimal.Decimal(65535)

mock_bitcoind_other.total_received = mock.mocksignature(utils.bitcoind.total_received, mock=mock_received_65535)

mock_bitcoind_other.send = mock.mocksignature(utils.bitcoind.send)

mock_bitcoind_other_address = mock.Mock()
mock_bitcoind_other_address.side_effect = create_address

mock_bitcoind_other.create_address = mock.mocksignature(utils.bitcoind.create_address, mock=mock_bitcoind_other_address)

# EOF


########NEW FILE########
__FILENAME__ = models
from __future__ import with_statement

import datetime
import random
import hashlib
import base64
import pytz
from decimal import Decimal

from django.db import models
from django.contrib.sites.models import Site
from django.contrib.auth.models import User

from django_bitcoin.utils import *
from django_bitcoin.utils import bitcoind
from django_bitcoin import settings

from django.utils.translation import ugettext as _

import django.dispatch

import jsonrpc

from BCAddressField import is_valid_btc_address

from django.db import transaction as db_transaction
from celery import task
from distributedlock import distributedlock, MemcachedLock, LockNotAcquiredError
from django.db.models import Avg, Max, Min, Sum

def CacheLock(key, lock=None, blocking=True, timeout=10000):
    if lock is None:
        lock = MemcachedLock(key=key, client=cache, timeout=timeout)

    return distributedlock(key, lock, blocking)

def NonBlockingCacheLock(key, lock=None, blocking=False, timeout=10000):
    if lock is None:
        lock = MemcachedLock(key=key, client=cache, timeout=timeout)

    return distributedlock(key, lock, blocking)

balance_changed = django.dispatch.Signal(providing_args=["changed", "transaction", "bitcoinaddress"])
balance_changed_confirmed = django.dispatch.Signal(providing_args=["changed", "transaction", "bitcoinaddress"])


currencies = (
    (1, "USD"),
    (2, "EUR"),
    (3, "BTC")
)

# XXX There *is* a risk when dealing with less then 6 confirmations. Check:
# http://eprint.iacr.org/2012/248.pdf
# http://blockchain.info/double-spends
# for an informed decision.
confirmation_choices = (
    (0, "0, (quick, recommended)"),
    (1, "1, (safer, slower for the buyer)"),
    (5, "5, (for the paranoid, not recommended)")
)

class Transaction(models.Model):
    created_at = models.DateTimeField(default=datetime.datetime.now)
    amount = models.DecimalField(
        max_digits=16,
        decimal_places=8,
        default=Decimal("0.0"))
    address = models.CharField(max_length=50)


class DepositTransaction(models.Model):

    created_at = models.DateTimeField(default=datetime.datetime.now)
    address = models.ForeignKey('BitcoinAddress')

    amount = models.DecimalField(max_digits=16, decimal_places=8, default=Decimal(0))
    description = models.CharField(max_length=100, blank=True, null=True, default=None)

    wallet = models.ForeignKey("Wallet")

    under_execution = models.BooleanField(default=False) # execution fail
    transaction = models.ForeignKey('WalletTransaction', null=True, default=None)

    confirmations = models.IntegerField(default=0)
    txid = models.CharField(max_length=100, blank=True, null=True)

    def __unicode__(self):
        return self.address.address + u", " + unicode(self.amount)

# class BitcoinBlock(models.Model):
#     created_at = models.DateTimeField(default=datetime.datetime.now)
#     blockhash = models.CharField(max_length=100)
#     blockheight = models.IntegerField()
#     confirmations = models.IntegerField(default=0)
#     parent = models.ForeignKey('BitcoinBlock')

class OutgoingTransaction(models.Model):

    created_at = models.DateTimeField(default=datetime.datetime.now)
    expires_at = models.DateTimeField(default=datetime.datetime.now)
    executed_at = models.DateTimeField(null=True,default=None)
    under_execution = models.BooleanField(default=False) # execution fail
    to_bitcoinaddress = models.CharField(
        max_length=50,
        blank=True)
    amount = models.DecimalField(
        max_digits=16,
        decimal_places=8,
        default=Decimal("0.0"))
    # description = models.CharField(max_length=100, blank=True)

    txid = models.CharField(max_length=100, blank=True, null=True, default=None)

    def __unicode__(self):
        return unicode(self.created_at) + ": " + self.to_bitcoinaddress + u", " + unicode(self.amount)

@task()
def update_wallet_balance(wallet_id):
    w = Wallet.objects.get(id=wallet_id)
    Wallet.objects.filter(id=wallet_id).update(last_balance=w.total_balance_sql())

from time import sleep

# @task()
# @db_transaction.commit_manually
# def process_outgoing_transactions():
#     if cache.get("process_outgoing_transactions"):
#         print "process ongoing, skipping..."
#         db_transaction.rollback()
#         return
#     if cache.get("wallet_downtime_utc"):
#         db_transaction.rollback()
#         return
#     # try out bitcoind connection
#     print bitcoind.bitcoind_api.getinfo()
#     with NonBlockingCacheLock('process_outgoing_transactions'):
#         update_wallets = []
#         for ot in OutgoingTransaction.objects.filter(executed_at=None)[:3]:
#             result = None
#             updated = OutgoingTransaction.objects.filter(id=ot.id,
#                 executed_at=None, txid=None, under_execution=False).select_for_update().update(executed_at=datetime.datetime.now(), txid=result)
#             db_transaction.commit()
#             if updated:
#                 try:
#                     result = bitcoind.send(ot.to_bitcoinaddress, ot.amount)
#                     updated2 = OutgoingTransaction.objects.filter(id=ot.id, txid=None).select_for_update().update(txid=result)
#                     db_transaction.commit()
#                     if updated2:
#                         transaction = bitcoind.gettransaction(result)
#                         if Decimal(transaction['fee']) < Decimal(0):
#                             wt = ot.wallettransaction_set.all()[0]
#                             fee_transaction = WalletTransaction.objects.create(
#                                 amount=Decimal(transaction['fee']) * Decimal(-1),
#                                 from_wallet_id=wt.from_wallet_id)
#                             update_wallets.append(wt.from_wallet_id)
#                 except jsonrpc.JSONRPCException as e:
#                     if e.error == u"{u'message': u'Insufficient funds', u'code': -4}":
#                         OutgoingTransaction.objects.filter(id=ot.id, txid=None,
#                             under_execution=False).select_for_update().update(executed_at=None)
#                         db_transaction.commit()
#                         # sleep(10)
#                         raise
#                     else:
#                         OutgoingTransaction.objects.filter(id=ot.id).select_for_update().update(under_execution=True)
#                         db_transaction.commit()
#                         raise

#             else:
#                 raise Exception("Outgoingtransaction can't be updated!")
#         db_transaction.commit()
#         for wid in update_wallets:
#             update_wallet_balance.delay(wid)

# TODO: Group outgoing transactions to save on tx fees

def fee_wallet():
    master_wallet_id = cache.get("django_bitcoin_fee_wallet_id")
    if master_wallet_id:
        return Wallet.objects.get(id=master_wallet_id)
    try:
        mw = Wallet.objects.get(label="django_bitcoin_fee_wallet")
    except Wallet.DoesNotExist:
        mw = Wallet.objects.create(label="django_bitcoin_fee_wallet")
        mw.save()
    cache.set("django_bitcoin_fee_wallet_id", mw.id)
    return mw

def filter_doubles(outgoing_list):
    ot_ids = []
    ot_addresses = []
    for ot in outgoing_list:
        if ot.to_bitcoinaddress not in ot_addresses:
            ot_ids.append(ot.id)
            ot_addresses.append(ot.to_bitcoinaddress)
    return ot_ids


@task()
@db_transaction.autocommit
def process_outgoing_transactions():
    if OutgoingTransaction.objects.filter(executed_at=None, expires_at__lte=datetime.datetime.now()).count()>0 or \
        OutgoingTransaction.objects.filter(executed_at=None).count()>6:
        blockcount = bitcoind.bitcoind_api.getblockcount()
        with NonBlockingCacheLock('process_outgoing_transactions'):
            ots_ids = filter_doubles(OutgoingTransaction.objects.filter(executed_at=None).order_by("expires_at")[:15])
            ots = OutgoingTransaction.objects.filter(executed_at=None, id__in=ots_ids)
            update_wallets = []
            transaction_hash = {}
            for ot in ots:
                transaction_hash[ot.to_bitcoinaddress] = float(ot.amount)
            updated = OutgoingTransaction.objects.filter(id__in=ots_ids,
                executed_at=None).select_for_update().update(executed_at=datetime.datetime.now())
            if updated == len(ots):
                try:
                    result = bitcoind.sendmany(transaction_hash)
                except jsonrpc.JSONRPCException as e:
                    if e.error == u"{u'message': u'Insufficient funds', u'code': -4}" or \
                        e.error == u"{u'message': u'Insufficient funds', u'code': -6}":
                        u2 = OutgoingTransaction.objects.filter(id__in=ots_ids, under_execution=False
                            ).select_for_update().update(executed_at=None)
                    else:
                        u2 = OutgoingTransaction.objects.filter(id__in=ots_ids, under_execution=False
                            ).select_for_update().update(under_execution=True, txid=e.error)
                    raise
                OutgoingTransaction.objects.filter(id__in=ots_ids).update(txid=result)
                transaction = bitcoind.gettransaction(result)
                if Decimal(transaction['fee']) < Decimal(0):
                    fw = fee_wallet()
                    fee_amount = Decimal(transaction['fee']) * Decimal(-1)
                    orig_fee_transaction = WalletTransaction.objects.create(
                            amount=fee_amount,
                            from_wallet=fw,
                            to_wallet=None)
                    i = 1
                    for ot_id in ots_ids:
                        wt = WalletTransaction.objects.get(outgoing_transaction__id=ot_id)
                        update_wallets.append(wt.from_wallet_id)
                        fee_transaction = WalletTransaction.objects.create(
                            amount=(fee_amount / Decimal(i)).quantize(Decimal("0.00000001")),
                            from_wallet_id=wt.from_wallet_id,
                            to_wallet=fw,
                            description="fee")
                        i += 1
                else:
                    raise Exception("Updated amount not matchinf transaction amount!")
            for wid in update_wallets:
                update_wallet_balance.delay(wid)
    # elif OutgoingTransaction.objects.filter(executed_at=None).count()>0:
    #     next_run_at = OutgoingTransaction.objects.filter(executed_at=None).aggregate(Min('expires_at'))['expires_at__min']
    #     if next_run_at:
    #         process_outgoing_transactions.retry(
    #             countdown=max(((next_run_at - datetime.datetime.now(pytz.utc)) + datetime.timedelta(seconds=5)).total_seconds(), 5))


class BitcoinAddress(models.Model):
    address = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(default=datetime.datetime.now)
    active = models.BooleanField(default=False)
    least_received = models.DecimalField(max_digits=16, decimal_places=8, default=Decimal(0))
    least_received_confirmed = models.DecimalField(max_digits=16, decimal_places=8, default=Decimal(0))
    label = models.CharField(max_length=50, blank=True, null=True, default=None)

    wallet = models.ForeignKey("Wallet", null=True, related_name="addresses")

    migrated_to_transactions = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Bitcoin addresses'

    def query_bitcoind(self, minconf=settings.BITCOIN_MINIMUM_CONFIRMATIONS, triggered_tx=None):
        raise Exception("Deprecated")
        with CacheLock('query_bitcoind'):
            r = bitcoind.total_received(self.address, minconf=minconf)

            if r > self.least_received_confirmed and \
                minconf >= settings.BITCOIN_MINIMUM_CONFIRMATIONS:
                transaction_amount = r - self.least_received_confirmed
                if settings.BITCOIN_TRANSACTION_SIGNALING:
                    if self.wallet:
                        balance_changed_confirmed.send(sender=self.wallet,
                            changed=(transaction_amount), bitcoinaddress=self)

                updated = BitcoinAddress.objects.select_for_update().filter(id=self.id, least_received_confirmed=self.least_received_confirmed).update(least_received_confirmed=r)

                if self.least_received < r:
                    BitcoinAddress.objects.select_for_update().filter(id=self.id,
                        least_received=self.least_received).update(least_received=r)

                if self.wallet and updated:
                    dps = DepositTransaction.objects.filter(address=self, transaction=None,
                        amount__lte=transaction_amount, wallet=self.wallet).order_by("-amount", "-id")
                    total_confirmed_amount = Decimal(0)
                    confirmed_dps = []
                    for dp in dps:
                        if dp.amount <= transaction_amount - total_confirmed_amount:
                            DepositTransaction.objects.filter(id=dp.id).update(confirmations=minconf)
                            total_confirmed_amount += dp.amount
                            confirmed_dps.append(dp.id)
                    if total_confirmed_amount < transaction_amount:
                        dp = DepositTransaction.objects.create(address=self, amount=transaction_amount - total_confirmed_amount, wallet=self.wallet,
                            confirmations=minconf, txid=triggered_tx)
                        confirmed_dps.append(dp.id)
                    if self.migrated_to_transactions and updated:
                        wt = WalletTransaction.objects.create(to_wallet=self.wallet, amount=transaction_amount, description=self.address,
                            deposit_address=self, deposit_transaction=deposit_tx)
                        DepositTransaction.objects.select_for_update().filter(address=self, wallet=self.wallet,
                            id__in=confirmed_dps, transaction=None).update(transaction=wt)
                    update_wallet_balance.delay(self.wallet.id)

            elif r > self.least_received:
                transaction_amount = r - self.least_received
                if settings.BITCOIN_TRANSACTION_SIGNALING:
                    if self.wallet:
                        balance_changed.send(sender=self.wallet, changed=(transaction_amount), bitcoinaddress=self)
                # self.least_received = r
                # self.save()
                updated = BitcoinAddress.objects.select_for_update().filter(id=self.id, least_received=self.least_received).update(least_received=r)
                if self.wallet and minconf==0 and updated:
                    DepositTransaction.objects.create(address=self, amount=transaction_amount, wallet=self.wallet,
                        confirmations=0, txid=triggered_tx)
            return r

    def query_bitcoin_deposit(self, deposit_tx):
        if deposit_tx.transaction:
            print "Already has a transaction!"
            return
        with CacheLock('query_bitcoind'):
            r = bitcoind.total_received(self.address, minconf=settings.BITCOIN_MINIMUM_CONFIRMATIONS)
            received_amount = r - self.least_received_confirmed

            if received_amount >= deposit_tx.amount and not deposit_tx.under_execution:
                if settings.BITCOIN_TRANSACTION_SIGNALING:
                    if self.wallet:
                        balance_changed_confirmed.send(sender=self.wallet,
                            changed=(deposit_tx.amount), bitcoinaddress=self)

                updated = BitcoinAddress.objects.select_for_update().filter(id=self.id,
                    least_received_confirmed=self.least_received_confirmed).update(
                    least_received_confirmed=self.least_received_confirmed + deposit_tx.amount)

                if self.wallet and updated:
                    DepositTransaction.objects.select_for_update().filter(id=deposit_tx.id).update(under_execution=True)
                    deposit_tx.under_execution = True
                    self.least_received_confirmed = self.least_received_confirmed + deposit_tx.amount
                    if self.least_received < self.least_received_confirmed:
                        updated = BitcoinAddress.objects.select_for_update().filter(id=self.id).update(
                            least_received=self.least_received_confirmed)
                    if self.migrated_to_transactions:
                        wt = WalletTransaction.objects.create(to_wallet=self.wallet, amount=deposit_tx.amount, description=self.address,
                            deposit_address=self)
                        deposit_tx.transaction = wt
                        DepositTransaction.objects.select_for_update().filter(id=deposit_tx.id).update(transaction=wt)
                    self.wallet.update_last_balance(deposit_tx.amount)
                else:
                    print "transaction not updated!"
            else:
                print "This path should not occur, but whatever."
                # raise Exception("Should be never this way")
            return r

    def query_unconfirmed_deposits(self):
        r = bitcoind.total_received(self.address, minconf=0)
        if r > self.least_received:
            transaction_amount = r - self.least_received
            if settings.BITCOIN_TRANSACTION_SIGNALING:
                if self.wallet:
                    balance_changed.send(sender=self.wallet, changed=(transaction_amount), bitcoinaddress=self)
            updated = BitcoinAddress.objects.select_for_update().filter(id=self.id, least_received=self.least_received).update(least_received=r)
            if updated:
                self.least_received = r

    def received(self, minconf=settings.BITCOIN_MINIMUM_CONFIRMATIONS):
        if settings.BITCOIN_TRANSACTION_SIGNALING:
            if minconf >= settings.BITCOIN_MINIMUM_CONFIRMATIONS:
                return self.least_received_confirmed
            else:
                return self.least_received
        return self.query_bitcoind(minconf)

    def __unicode__(self):
        if self.label:
            return u'%s (%s)' % (self.label, self.address)
        return self.address



def new_bitcoin_address():
    while True:
        with db_transaction.autocommit():
            db_transaction.enter_transaction_management()
            db_transaction.commit()
            bp = BitcoinAddress.objects.filter(Q(active=False) & Q(wallet__isnull=True) & \
                    Q(least_received__lte=0))
            if len(bp) < 1:
                refill_payment_queue()
                db_transaction.commit()
                print "refilling queue...", bp
            else:
                bp = bp[0]
                updated = BitcoinAddress.objects.select_for_update().filter(Q(id=bp.id) & Q(active=False) & Q(wallet__isnull=True) & \
                    Q(least_received__lte=0)).update(active=True)
                db_transaction.commit()
                if updated:
                    return bp
                else:
                    print "wallet transaction concurrency:", bp.address


class Payment(models.Model):
    description = models.CharField(
        max_length=255,
        blank=True)
    address = models.CharField(
        max_length=50)
    amount = models.DecimalField(
        max_digits=16,
        decimal_places=8,
        default=Decimal("0.0"))
    amount_paid = models.DecimalField(
        max_digits=16,
        decimal_places=8,
        default=Decimal("0.0"))
    active = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=datetime.datetime.now)
    updated_at = models.DateTimeField()

    paid_at = models.DateTimeField(null=True, default=None)

    withdrawn_total = models.DecimalField(
        max_digits=16,
        decimal_places=8,
        default=Decimal("0.0"))

    transactions = models.ManyToManyField(Transaction)

    def calculate_amount(self, proportion):
        return quantitize_bitcoin(
            Decimal((proportion/Decimal("100.0"))*self.amount))

    def add_transaction(self, amount, address):
        self.withdrawn_total += amount
        bctrans = self.transactions.create(
            amount=amount,
            address=address)
        self.save()

        return bctrans

    def withdraw_proportion(self, address, proportion):
        if proportion<=Decimal("0") or proportion>Decimal("100"):
            raise Exception("Illegal proportion.")

        amount = self.calculate_amount(proportion)

        if self.amount-self.withdrawn_total > amount:
            raise Exception("Trying to withdraw too much.")

        self.add_transaction(amount, address)
        bitcoind.send(address, amount)

    @classmethod
    def withdraw_proportion_all(cls, address, bitcoin_payments_proportions):
        """hash BitcoinPayment -> Proportion"""
        final_amount=Decimal("0.0")
        print bitcoin_payments_proportions
        for bp, proportion in bitcoin_payments_proportions.iteritems():
            am=bp.calculate_amount(proportion)
            final_amount+=am
            bp.add_transaction(am, address)
        bitcoind.send(address, final_amount)
        return True

    def withdraw_amounts(self, addresses_shares):
        """hash address -> percentage (string -> Decimal)"""
        if self.amount_paid<self.amount:
            raise Exception("Not paid.")
        if self.withdrawn_at:
            raise Exception("Trying to withdraw again.")
        if sum(addresses_shares.values())>100:
            raise Exception("Sum of proportions must be <=100.")
        #self.withdraw_addresses=",".join(addresses)
        #self.withdraw_proportions=",".join([str(x) for x in proportions])
        amounts=[]
        for p in addresses_shares.values():
            if p<=0:
                raise Exception()
            am=quantitize_bitcoin(Decimal((p/Decimal("100.0"))*self.amount))
            amounts.append(am)
        #self.withdraw_proportions=",".join([str(x) for x in ])
        if sum(amounts)>self.amount:
            raise Exception("Sum of calculated amounts exceeds funds.")
        return amounts

    @classmethod
    def calculate_amounts(cls, bitcoinpayments, addresses_shares):
        amounts_all=[Decimal("0.0") for _i in addresses_shares]
        for amount, payment in zip(amounts_all, bitcoinpayments):
            withdrawn=payment.withdraw_amounts(addresses_shares)
            amounts_all=[(w+total) for w, total in zip(withdrawn, amounts_all)]
        return amounts_all

    @classmethod
    def withdraw_all(cls, bitcoinpayments, addresses_shares):
        #if len(bitcoinpayments)!=len(addresses_shares):
        #    raise Exception("")
        amounts_all=Payment.calculate_amounts(bitcoinpayments, addresses_shares)
        for bp in bitcoinpayments:
            am=bp.withdraw_amounts(addresses_shares)
            bp.withdraw_addresses=",".join(addresses_shares.keys())
            bp.withdraw_proportions=",".join(
                [str(x) for x in addresses_shares.values()])
            bp.withdraw_amounts=",".join(
                [str(x) for x in am])
            bp.withdrawn_at=datetime.datetime.now()
            bp.withdrawn_total=sum(am)
            bp.save()
        for i, share in enumerate(addresses_shares.keys()):
            bitcoind.send(share, amounts_all[i])
        return True

    def is_paid(self, minconf=1):
        if self.paid_at:
            return True
        self.update_payment(minconf=minconf)
        return self.amount_paid>=self.amount

    def getbalance(self, minconf=1):
        return bitcoind.total_received(self.address, minconf=minconf)

    def update_payment(self, minconf=1):
        new_amount=Decimal(bitcoin_getbalance(self.address, minconf=minconf))
        print "blaa", new_amount, self.address
        if new_amount>=self.amount:
            self.amount_paid=new_amount
            self.paid_at=datetime.datetime.now()
            self.save()
        #elif (datetime.datetime.now()-self.updated_at)>datetime.timedelta(hours=PAYMENT_VALID_HOURS):
        #    self.deactivate()

    def deactivate(self):
        return False
        if self.amount_paid > Decimal("0"):
            return False
        self.active=False
        self.description=""
        self.save()
        return True

    def save(self, **kwargs):
        self.updated_at = datetime.datetime.now()
        return super(Payment, self).save(**kwargs)

    def __unicode__(self):
        return unicode(self.amount_paid)

    @models.permalink
    def get_absolute_url(self):
        return ('view_or_url_name',)

class WalletTransaction(models.Model):
    created_at = models.DateTimeField(default=datetime.datetime.now)
    from_wallet = models.ForeignKey(
        'Wallet',
        null=True,
        related_name="sent_transactions")
    to_wallet = models.ForeignKey(
        'Wallet',
        null=True,
        related_name="received_transactions")
    to_bitcoinaddress = models.CharField(
        max_length=50,
        blank=True)
    outgoing_transaction = models.ForeignKey('OutgoingTransaction', null=True, default=None)
    amount = models.DecimalField(
        max_digits=16,
        decimal_places=8,
        default=Decimal("0.0"))
    description = models.CharField(max_length=100, blank=True)

    deposit_address = models.ForeignKey(BitcoinAddress, null=True)
    txid = models.CharField(max_length=100, blank=True, null=True)
    deposit_transaction = models.OneToOneField(DepositTransaction, null=True)

    def __unicode__(self):
        if self.from_wallet and self.to_wallet:
            return u"Wallet transaction "+unicode(self.amount)
        elif self.from_wallet and self.to_bitcoinaddress:
            return u"Outgoing bitcoin transaction "+unicode(self.amount)
        elif self.to_wallet and not self.from_wallet:
            return u"Deposit "+unicode(self.amount)
        return u"Fee "+unicode(self.amount)

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.from_wallet and not self.to_wallet:
            raise ValidationError('Wallet transaction error - define a wallet.')

    def confirmation_status(self,
                            minconf=settings.BITCOIN_MINIMUM_CONFIRMATIONS,
                            transactions=None):
        """
        Returns the confirmed and unconfirmed parts of this transfer.
        Also accepts and returns a list of transactions that are being
        currently used.

        The sum of the two amounts is the total transaction amount.
        """

        if not transactions: transactions = {}

        if minconf == 0 or self.to_bitcoinaddress:
            return (0, self.amount, transactions)

        _, confirmed, txs = self.from_wallet.balance(minconf=minconf,
                                             timeframe=self.created_at,
                                             transactions=transactions)
        transactions.update(txs)

        if confirmed > self.amount: confirmed = self.amount
        unconfirmed = self.amount - confirmed

        return (unconfirmed, confirmed, transactions)

from django.db.models import Q

class Wallet(models.Model):
    created_at = models.DateTimeField(default=datetime.datetime.now)
    updated_at = models.DateTimeField()

    label = models.CharField(max_length=50, blank=True)
    # DEPRECATED: changed to foreign key
    # addresses = models.ManyToManyField(BitcoinAddress, through="WalletBitcoinAddress")
    transactions_with = models.ManyToManyField(
        'self',
        through=WalletTransaction,
        symmetrical=False)

    transaction_counter = models.IntegerField(default=1)
    last_balance = models.DecimalField(default=Decimal(0), max_digits=16, decimal_places=8)

    # track_transaction_value = models.BooleanField(default=False)

    # tries to update instantly, if not succesful updates using sql query (celery task)
    def update_last_balance(self, amount):
        if self.__class__.objects.filter(id=self.id, last_balance=self.last_balance
            ).update(last_balance=(self.last_balance + amount)) < 1:
            update_wallet_balance.apply_async((self.id,), countdown=1)

    def __unicode__(self):
        return u"%s: %s" % (self.label,
                            self.created_at.strftime('%Y-%m-%d %H:%M'))

    def save(self, *args, **kwargs):
        '''No need for labels.'''
        self.updated_at = datetime.datetime.now()
        super(Wallet, self).save(*args, **kwargs)
        #super(Wallet, self).save(*args, **kwargs)

    def receiving_address(self, fresh_addr=True):
        while True:
            usable_addresses = self.addresses.filter(active=True).order_by("id")
            if fresh_addr:
                usable_addresses = usable_addresses.filter(least_received=Decimal(0))
            if usable_addresses.count():
                return usable_addresses[0].address
            addr = new_bitcoin_address()
            updated = BitcoinAddress.objects.select_for_update().filter(Q(id=addr.id) & Q(active=True) & Q(least_received__lte=0) & Q(wallet__isnull=True))\
                          .update(active=True, wallet=self)
            print "addr_id", addr.id, updated
            # db_transaction.commit()
            if updated:
                return addr.address
            else:
                raise Exception("Concurrency error!")

    def static_receiving_address(self):
        ''' Returns a static receiving address for this Wallet object.'''
        return self.receiving_address(fresh_addr=False)

    def send_to_wallet(self, otherWallet, amount, description=''):

        if type(amount) != Decimal:
            amount = Decimal(amount)
        amount = amount.quantize(Decimal('0.00000001'))

        with db_transaction.autocommit():
            db_transaction.enter_transaction_management()
            db_transaction.commit()
            if settings.BITCOIN_UNCONFIRMED_TRANSFERS:
                avail = self.total_balance_unconfirmed()
            else:
                avail = self.total_balance()
            updated = Wallet.objects.filter(Q(id=self.id)).update(last_balance=avail)

            if self == otherWallet:
                raise Exception(_("Can't send to self-wallet"))
            if not otherWallet.id or not self.id:
                raise Exception(_("Some of the wallets not saved"))
            if amount <= 0:
                raise Exception(_("Can't send zero or negative amounts"))
            if amount > avail:
                raise Exception(_("Trying to send too much"))
            # concurrency check
            new_balance = avail - amount
            updated = Wallet.objects.filter(Q(id=self.id) & Q(transaction_counter=self.transaction_counter) &
                Q(last_balance=avail))\
              .update(last_balance=new_balance, transaction_counter=self.transaction_counter+1)
            if not updated:
                print "wallet transaction concurrency:", new_balance, avail, self.transaction_counter, self.last_balance, self.total_balance()
                raise Exception(_("Concurrency error with transactions. Please try again."))
            # db_transaction.commit()
            # concurrency check end
            transaction = WalletTransaction.objects.create(
                amount=amount,
                from_wallet=self,
                to_wallet=otherWallet,
                description=description)
            # db_transaction.commit()
            self.transaction_counter = self.transaction_counter+1
            self.last_balance = new_balance
            # updated = Wallet.objects.filter(Q(id=otherWallet.id))\
            #   .update(last_balance=otherWallet.total_balance_sql())
            otherWallet.update_last_balance(amount)

            if settings.BITCOIN_TRANSACTION_SIGNALING:
                balance_changed.send(sender=self,
                    changed=(Decimal(-1) * amount), transaction=transaction)
                balance_changed.send(sender=otherWallet,
                    changed=(amount), transaction=transaction)
                balance_changed_confirmed.send(sender=self,
                    changed=(Decimal(-1) * amount), transaction=transaction)
                balance_changed_confirmed.send(sender=otherWallet,
                    changed=(amount), transaction=transaction)
            return transaction

    def send_to_address(self, address, amount, description='', expires_seconds=settings.BITCOIN_OUTGOING_DEFAULT_DELAY_SECONDS):
        if settings.BITCOIN_DISABLE_OUTGOING:
            raise Exception("Outgoing transactions disabled! contact support.")
        address = address.strip()

        if type(amount) != Decimal:
            amount = Decimal(amount)
        amount = amount.quantize(Decimal('0.00000001'))

        if not is_valid_btc_address(str(address)):
            raise Exception(_("Not a valid bitcoin address") + ":" + address)
        if amount <= 0:
            raise Exception(_("Can't send zero or negative amounts"))
        # concurrency check
        with db_transaction.autocommit():
            db_transaction.enter_transaction_management()
            db_transaction.commit()
            avail = self.total_balance()
            updated = Wallet.objects.filter(Q(id=self.id)).update(last_balance=avail)
            if amount > avail:
                raise Exception(_("Trying to send too much"))
            new_balance = avail - amount
            updated = Wallet.objects.filter(Q(id=self.id) & Q(transaction_counter=self.transaction_counter) &
                Q(last_balance=avail) )\
              .update(last_balance=new_balance, transaction_counter=self.transaction_counter+1)
            if not updated:
                print "address transaction concurrency:", new_balance, avail, self.transaction_counter, self.last_balance, self.total_balance()
                raise Exception(_("Concurrency error with transactions. Please try again."))
            # concurrency check end
            outgoing_transaction = OutgoingTransaction.objects.create(amount=amount, to_bitcoinaddress=address,
                expires_at=datetime.datetime.now()+datetime.timedelta(seconds=expires_seconds))
            bwt = WalletTransaction.objects.create(
                amount=amount,
                from_wallet=self,
                to_bitcoinaddress=address,
                outgoing_transaction=outgoing_transaction,
                description=description)
            process_outgoing_transactions.apply_async((), countdown=(expires_seconds+1))
            # try:
            #     result = bitcoind.send(address, amount)
            # except jsonrpc.JSONRPCException:
            #     bwt.delete()
            #     updated2 = Wallet.objects.filter(Q(id=self.id) & Q(last_balance=new_balance)).update(last_balance=avail)
            #     raise
            self.transaction_counter = self.transaction_counter+1
            self.last_balance = new_balance

            # check if a transaction fee exists, and deduct it from the wallet
            # TODO: because fee can't be known beforehand, can result in negative wallet balance.
            # currently isn't much of a issue, but might be in the future, depending of the application
            # transaction = bitcoind.gettransaction(result)
            # fee_transaction = None
            # total_amount = amount
            # if Decimal(transaction['fee']) < Decimal(0):
            #     fee_transaction = WalletTransaction.objects.create(
            #         amount=Decimal(transaction['fee']) * Decimal(-1),
            #         from_wallet=self)
            #     total_amount += fee_transaction.amount
            #     updated = Wallet.objects.filter(Q(id=self.id))\
            #         .update(last_balance=new_balance-fee_transaction.amount)
            if settings.BITCOIN_TRANSACTION_SIGNALING:
                balance_changed.send(sender=self,
                    changed=(Decimal(-1) * amount), transaction=bwt)
                balance_changed_confirmed.send(sender=self,
                    changed=(Decimal(-1) * amount), transaction=bwt)
            return (bwt, None)

    def update_transaction_cache(self,
                                 mincf=settings.BITCOIN_MINIMUM_CONFIRMATIONS):
        """
        Finds the timestamp from the oldest transaction found with wasn't yet
        confirmed. If none, returns the current timestamp.
        """
        if mincf == 0: return datetime.datetime.now()

        transactions_checked = "bitcoin_transactions_checked_%d" % mincf
        oldest_unconfirmed = "bitcoin_oldest_unconfirmed_%d" % mincf

        if cache.get(transactions_checked):
            return cache.get(oldest_unconfirmed)
        else:
            cache.set(transactions_checked, True, 60*15)
            current_timestamp = datetime.datetime.now()
            transactions = WalletTransaction.objects.all()
            oldest = cache.get(oldest_unconfirmed)
            if oldest:
                transactions = transactions.filter(created_at__gte=oldest)

            transactions_cache = {}
            for t in transactions.order_by('created_at'):
                unc, _, txs =  t.confirmation_status(minconf=mincf, transactions=transactions_cache)
                transactions_cache.update(txs)
                if unc:
                    cache.set(oldest_unconfirmed, t.created_at)
                    return t.created_at
            cache.set(oldest_unconfirmed, current_timestamp)
            return current_timestamp

    def balance(self, minconf=settings.BITCOIN_MINIMUM_CONFIRMATIONS,
                timeframe=None, transactions=None):
        """
        Returns a "greater or equal than minimum"  total ammount received at
        this wallet with the given confirmations at the given timeframe.
        """
        if minconf == settings.BITCOIN_MINIMUM_CONFIRMATIONS:
            return self.total_balance_sql(True)
        elif minconf == 0:
            return self.total_balance_sql(False)
        raise Exception("Incorrect minconf parameter")

    def total_balance_sql(self, confirmed=True):
        from django.db import connection
        cursor = connection.cursor()
        if confirmed == False:
            sql="""
             SELECT IFNULL((SELECT SUM(least_received) FROM django_bitcoin_bitcoinaddress ba WHERE ba.wallet_id=%(id)s), 0)
            + IFNULL((SELECT SUM(amount) FROM django_bitcoin_wallettransaction wt WHERE wt.to_wallet_id=%(id)s AND wt.from_wallet_id>0), 0)
            - IFNULL((SELECT SUM(amount) FROM django_bitcoin_wallettransaction wt WHERE wt.from_wallet_id=%(id)s), 0) as total_balance;
            """ % {'id': self.id}
            cursor.execute(sql)
            return cursor.fetchone()[0]
        else:
            sql="""
             SELECT IFNULL((SELECT SUM(least_received_confirmed) FROM django_bitcoin_bitcoinaddress ba WHERE ba.wallet_id=%(id)s AND ba.migrated_to_transactions=0), 0)
            + IFNULL((SELECT SUM(amount) FROM django_bitcoin_wallettransaction wt WHERE wt.to_wallet_id=%(id)s), 0)
            - IFNULL((SELECT SUM(amount) FROM django_bitcoin_wallettransaction wt WHERE wt.from_wallet_id=%(id)s), 0) as total_balance;
            """ % {'id': self.id}
            cursor.execute(sql)
            self.last_balance = cursor.fetchone()[0]
            return self.last_balance

    def total_balance(self, minconf=settings.BITCOIN_MINIMUM_CONFIRMATIONS):
        """
        Returns the total confirmed balance from the Wallet.
        """
        if not settings.BITCOIN_UNCONFIRMED_TRANSFERS:
            # if settings.BITCOIN_TRANSACTION_SIGNALING:
            #     if minconf == settings.BITCOIN_MINIMUM_CONFIRMATIONS:
            #         return self.total_balance_sql()
            #     elif mincof == 0:
            #         self.total_balance_sql(False)
            if minconf >= settings.BITCOIN_MINIMUM_CONFIRMATIONS:
                self.last_balance = self.total_received(minconf) - self.total_sent()
                return self.last_balance
            else:
                return self.total_received(minconf) - self.total_sent()
        else:
            return self.balance(minconf)[1]

    def total_balance_historical(self, balance_date, minconf=settings.BITCOIN_MINIMUM_CONFIRMATIONS):
        if settings.BITCOIN_TRANSACTION_SIGNALING:
            if minconf == settings.BITCOIN_MINIMUM_CONFIRMATIONS:
                s = self.addresses.filter(created_at__lte=balance_date, migrated_to_transactions=False).aggregate(models.Sum("least_received_confirmed"))['least_received_confirmed__sum'] or Decimal(0)
            elif minconf == 0:
                s = self.addresses.filter(created_at__lte=balance_date, migrated_to_transactions=False).aggregate(models.Sum("least_received"))['least_received__sum'] or Decimal(0)
            else:
                s = sum([a.received(minconf=minconf) for a in self.addresses.filter(created_at__lte=balance_date, migrated_to_transactions=False)])
        else:
            s = sum([a.received(minconf=minconf) for a in self.addresses.filter(created_at__lte=balance_date)])
        rt = self.received_transactions.filter(created_at__lte=balance_date).aggregate(models.Sum("amount"))['amount__sum'] or Decimal(0)
        received = (s + rt)
        sent = self.sent_transactions.filter(created_at__lte=balance_date).aggregate(models.Sum("amount"))['amount__sum'] or Decimal(0)
        return received - sent

    def total_balance_unconfirmed(self):
        if not settings.BITCOIN_UNCONFIRMED_TRANSFERS:
            return self.total_received(0) - self.total_sent()
        else:
            x = self.balance()
            return x[0] + x[1]

    def unconfirmed_balance(self):
        if not settings.BITCOIN_UNCONFIRMED_TRANSFERS:
            return self.total_received(0) - self.total_sent()
        else:
            return self.balance()[0]

    def total_received(self, minconf=settings.BITCOIN_MINIMUM_CONFIRMATIONS):
        """Returns the raw ammount ever received by this wallet."""
        if settings.BITCOIN_TRANSACTION_SIGNALING:
            if minconf == settings.BITCOIN_MINIMUM_CONFIRMATIONS:
                s = self.addresses.filter(migrated_to_transactions=False).aggregate(models.Sum("least_received_confirmed"))['least_received_confirmed__sum'] or Decimal(0)
            elif minconf == 0:
                s = self.addresses.all().aggregate(models.Sum("least_received"))['least_received__sum'] or Decimal(0)
            else:
                s = sum([a.received(minconf=minconf) for a in self.addresses.filter(migrated_to_transactions=False)])
        else:
            s = sum([a.received(minconf=minconf) for a in self.addresses.filter(migrated_to_transactions=False)])
        if minconf == 0:
            rt = self.received_transactions.filter(from_wallet__gte=1).aggregate(models.Sum("amount"))['amount__sum'] or Decimal(0)
        else:
            rt = self.received_transactions.aggregate(models.Sum("amount"))['amount__sum'] or Decimal(0)
        return (s + rt)

    def total_sent(self):
        """Returns the raw ammount ever sent by this wallet."""
        return self.sent_transactions.aggregate(models.Sum("amount"))['amount__sum'] or Decimal(0)

    def has_history(self):
        """Returns True if this wallet was any transacion history."""
        if self.received_transactions.all().count():
            return True
        if self.sent_transactions.all().count():
            return True
        if filter(lambda x: x.received(), self.addresses.all()):
            return True
        return False

    def merge_wallet(self, other_wallet):
        if self.id>0 and other_wallet.id>0:
            from django.db import connection, transaction
            cursor = connection.cursor()
            cursor.execute("UPDATE django_bitcoin_bitcoinaddress SET wallet_id="+str(other_wallet.id)+\
                " WHERE wallet_id="+str(self.id))
            cursor.execute("UPDATE django_bitcoin_wallettransaction SET from_wallet_id="+str(other_wallet.id)+\
                " WHERE from_wallet_id="+str(self.id))
            cursor.execute("UPDATE django_bitcoin_wallettransaction SET to_wallet_id="+str(other_wallet.id)+\
                " WHERE to_wallet_id="+str(self.id))
            cursor.execute("DELETE FROM django_bitcoin_wallettransaction WHERE to_wallet_id=from_wallet_id")
            transaction.commit_unless_managed()

    # def save(self, **kwargs):
    #     self.updated_at = datetime.datetime.now()
    #     super(Wallet, self).save(**kwargs)

### Maybe in the future

# class FiatWalletTransaction(models.Model):
#     """Transaction for storing fiat currencies"""
#     pass

# class FiatWallet(models.Model):
#     """Wallet for storing fiat currencies"""
#     pass

# class BitcoinEscrow(models.Model):
#     """Bitcoin escrow payment"""

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     seller = models.ForeignKey(User)

#     bitcoin_payment = models.ForeignKey(Payment)

#     confirm_hash = models.CharField(max_length=50, blank=True)

#     buyer_address = models.TextField()
#     buyer_phone = models.CharField(max_length=20, blank=True)
#     buyer_email = models.EmailField(max_length=75)

#     def save(self, **kwargs):
#         super(BitcoinEscrow, self).save(**kwargs)
#         if not self.confirm_hash:
#             self.confirm_hash=generateuniquehash(
#                 length=32,
#                 extradata=str(self.id))
#             super(BitcoinEscrow, self).save(**kwargs)

#     @models.permalink
#     def get_absolute_url(self):
#         return ('view_or_url_name',)


def refill_payment_queue():
    c=BitcoinAddress.objects.filter(active=False, wallet=None).count()
    # print "count", c
    if settings.BITCOIN_ADDRESS_BUFFER_SIZE>c:
        for i in range(0,settings.BITCOIN_ADDRESS_BUFFER_SIZE-c):
            BitcoinAddress.objects.create(address = bitcoind.create_address(), active=False)


def update_payments():
    if not cache.get('last_full_check'):
        cache.set('bitcoinprice', cache.get('bitcoinprice_old'))
    bps=BitcoinPayment.objects.filter(active=True)
    for bp in bps:
        bp.amount_paid=Decimal(bitcoin_getbalance(bp.address))
        bp.save()
        print bp.amount
        print bp.amount_paid

@transaction.commit_on_success
def new_bitcoin_payment(amount):
    bp=BitcoinPayment.objects.filter(active=False)
    if len(bp)<1:
        refill_payment_queue()
        bp=BitcoinPayment.objects.filter(active=False)
    bp=bp[0]
    bp.active=True
    bp.amount=amount
    bp.save()
    return bp

def getNewBitcoinPayment(amount):
    warnings.warn("Use new_bitcoin_payment(amount) instead",
                  DeprecationWarning)
    return new_bitcoin_payment(amount)

@transaction.commit_on_success
def new_bitcoin_payment_eur(amount):
    print bitcoinprice_eur()
    return new_bitcoin_payment(Decimal(amount)/Decimal(bitcoinprice_eur()['24h']))

def getNewBitcoinPayment_eur(amount):
    return new_bitcoin_payment_eur(amount)

# initialize the conversion module

from django_bitcoin import currency

from django.core import urlresolvers
from django.utils import importlib

for dottedpath in settings.BITCOIN_CURRENCIES:
    mod, func = urlresolvers.get_mod_func(dottedpath)
    klass = getattr(importlib.import_module(mod), func)
    currency.exchange.register_currency(klass())

# Historical prie storage

class HistoricalPrice(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=16, decimal_places=2)
    params = models.CharField(max_length=50)
    currency = models.CharField(max_length=10)

    class Meta:
        verbose_name = _('HistoricalPrice')
        verbose_name_plural = _('HistoricalPrices')

    def __unicode__(self):
        return str(self.created_at) + " - " + str(self.price) + " - " + str(self.params)

def set_historical_price(curr="EUR"):
    markets = currency.markets_chart()
    # print markets
    markets_currency = sorted(filter(lambda m: m['currency']==curr and m['volume']>1 and not m['symbol'].startswith("mtgox"),
        markets.values()), key=lambda m: -m['volume'])[:3]
    # print markets_currency
    price = sum([m['avg'] for m in markets_currency]) / len(markets_currency)
    hp = HistoricalPrice.objects.create(price=Decimal(str(price)), params=",".join([m['symbol']+"_avg" for m in markets_currency]), currency=curr,
            created_at=datetime.datetime.now())
    print "Created new",hp
    return hp

def get_historical_price_object(dt=None, curr="EUR"):
    query = HistoricalPrice.objects.filter(currency=curr)
    if dt:
        try:
            query = query.filter(created_at__lte=dt).order_by("-created_at")
            return query[0]
        except IndexError:
            return None
    try:
        # print datetime.datetime.now()
        query=HistoricalPrice.objects.filter(currency=curr,
            created_at__gte=datetime.datetime.now() - datetime.timedelta(minutes=settings.HISTORICALPRICES_FETCH_TIMESPAN_MINUTES)).\
            order_by("-created_at")
        # print query
        return query[0]
    except IndexError:
        return set_historical_price()

def get_historical_price(dt=None, curr="EUR"):
    return get_historical_price_object().price




# EOF

########NEW FILE########
__FILENAME__ = pywallet
#!/usr/bin/env python

# PyWallet 1.2.1 (Public Domain)
# http://github.com/joric/pywallet
# Most of the actual PyWallet code placed in the public domain.
# PyWallet includes portions of free software, listed below.

# BitcoinTools (wallet.dat handling code, MIT License)
# https://github.com/gavinandresen/bitcointools
# Copyright (c) 2010 Gavin Andresen

# python-ecdsa (EC_KEY implementation, MIT License)
# http://github.com/warner/python-ecdsa
# "python-ecdsa" Copyright (c) 2010 Brian Warner
# Portions written in 2005 by Peter Pearson and placed in the public domain.

# SlowAES (aes.py code, Apache 2 License)
# http://code.google.com/p/slowaes/
# Copyright (c) 2008, Josh Davis (http://www.josh-davis.org), 
# Alex Martelli (http://www.aleax.it)
# Ported from C code written by Laurent Haan (http://www.progressive-coding.com)

import os, sys, time
import json
import logging
import struct
import StringIO
import traceback
import socket
import types
import string
import exceptions
import hashlib
import random
import math

max_version = 60000
addrtype = 0
json_db = {}
private_keys = []
password = None

def determine_db_dir():
    import os
    import os.path
    import platform
    if platform.system() == "Darwin":
        return os.path.expanduser("~/Library/Application Support/Bitcoin/")
    elif platform.system() == "Windows":
        return os.path.join(os.environ['APPDATA'], "Bitcoin")
    return os.path.expanduser("~/.bitcoin")

# from the SlowAES project, http://code.google.com/p/slowaes (aes.py)

def append_PKCS7_padding(s):
    """return s padded to a multiple of 16-bytes by PKCS7 padding"""
    numpads = 16 - (len(s)%16)
    return s + numpads*chr(numpads)

def strip_PKCS7_padding(s):
    """return s stripped of PKCS7 padding"""
    if len(s)%16 or not s:
        raise ValueError("String of len %d can't be PCKS7-padded" % len(s))
    numpads = ord(s[-1])
    if numpads > 16:
        raise ValueError("String ending with %r can't be PCKS7-padded" % s[-1])
    return s[:-numpads]

class AES(object):
    # valid key sizes
    keySize = dict(SIZE_128=16, SIZE_192=24, SIZE_256=32)

    # Rijndael S-box
    sbox =  [0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67,
            0x2b, 0xfe, 0xd7, 0xab, 0x76, 0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59,
            0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0, 0xb7,
            0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1,
            0x71, 0xd8, 0x31, 0x15, 0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05,
            0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75, 0x09, 0x83,
            0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29,
            0xe3, 0x2f, 0x84, 0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b,
            0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf, 0xd0, 0xef, 0xaa,
            0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c,
            0x9f, 0xa8, 0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc,
            0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2, 0xcd, 0x0c, 0x13, 0xec,
            0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19,
            0x73, 0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee,
            0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb, 0xe0, 0x32, 0x3a, 0x0a, 0x49,
            0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
            0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4,
            0xea, 0x65, 0x7a, 0xae, 0x08, 0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6,
            0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a, 0x70,
            0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9,
            0x86, 0xc1, 0x1d, 0x9e, 0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e,
            0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf, 0x8c, 0xa1,
            0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0,
            0x54, 0xbb, 0x16]

    # Rijndael Inverted S-box
    rsbox = [0x52, 0x09, 0x6a, 0xd5, 0x30, 0x36, 0xa5, 0x38, 0xbf, 0x40, 0xa3,
            0x9e, 0x81, 0xf3, 0xd7, 0xfb , 0x7c, 0xe3, 0x39, 0x82, 0x9b, 0x2f,
            0xff, 0x87, 0x34, 0x8e, 0x43, 0x44, 0xc4, 0xde, 0xe9, 0xcb , 0x54,
            0x7b, 0x94, 0x32, 0xa6, 0xc2, 0x23, 0x3d, 0xee, 0x4c, 0x95, 0x0b,
            0x42, 0xfa, 0xc3, 0x4e , 0x08, 0x2e, 0xa1, 0x66, 0x28, 0xd9, 0x24,
            0xb2, 0x76, 0x5b, 0xa2, 0x49, 0x6d, 0x8b, 0xd1, 0x25 , 0x72, 0xf8,
            0xf6, 0x64, 0x86, 0x68, 0x98, 0x16, 0xd4, 0xa4, 0x5c, 0xcc, 0x5d,
            0x65, 0xb6, 0x92 , 0x6c, 0x70, 0x48, 0x50, 0xfd, 0xed, 0xb9, 0xda,
            0x5e, 0x15, 0x46, 0x57, 0xa7, 0x8d, 0x9d, 0x84 , 0x90, 0xd8, 0xab,
            0x00, 0x8c, 0xbc, 0xd3, 0x0a, 0xf7, 0xe4, 0x58, 0x05, 0xb8, 0xb3,
            0x45, 0x06 , 0xd0, 0x2c, 0x1e, 0x8f, 0xca, 0x3f, 0x0f, 0x02, 0xc1,
            0xaf, 0xbd, 0x03, 0x01, 0x13, 0x8a, 0x6b , 0x3a, 0x91, 0x11, 0x41,
            0x4f, 0x67, 0xdc, 0xea, 0x97, 0xf2, 0xcf, 0xce, 0xf0, 0xb4, 0xe6,
            0x73 , 0x96, 0xac, 0x74, 0x22, 0xe7, 0xad, 0x35, 0x85, 0xe2, 0xf9,
            0x37, 0xe8, 0x1c, 0x75, 0xdf, 0x6e , 0x47, 0xf1, 0x1a, 0x71, 0x1d,
            0x29, 0xc5, 0x89, 0x6f, 0xb7, 0x62, 0x0e, 0xaa, 0x18, 0xbe, 0x1b ,
            0xfc, 0x56, 0x3e, 0x4b, 0xc6, 0xd2, 0x79, 0x20, 0x9a, 0xdb, 0xc0,
            0xfe, 0x78, 0xcd, 0x5a, 0xf4 , 0x1f, 0xdd, 0xa8, 0x33, 0x88, 0x07,
            0xc7, 0x31, 0xb1, 0x12, 0x10, 0x59, 0x27, 0x80, 0xec, 0x5f , 0x60,
            0x51, 0x7f, 0xa9, 0x19, 0xb5, 0x4a, 0x0d, 0x2d, 0xe5, 0x7a, 0x9f,
            0x93, 0xc9, 0x9c, 0xef , 0xa0, 0xe0, 0x3b, 0x4d, 0xae, 0x2a, 0xf5,
            0xb0, 0xc8, 0xeb, 0xbb, 0x3c, 0x83, 0x53, 0x99, 0x61 , 0x17, 0x2b,
            0x04, 0x7e, 0xba, 0x77, 0xd6, 0x26, 0xe1, 0x69, 0x14, 0x63, 0x55,
            0x21, 0x0c, 0x7d]

    def getSBoxValue(self,num):
        """Retrieves a given S-Box Value"""
        return self.sbox[num]

    def getSBoxInvert(self,num):
        """Retrieves a given Inverted S-Box Value"""
        return self.rsbox[num]

    def rotate(self, word):
        """ Rijndael's key schedule rotate operation.

        Rotate a word eight bits to the left: eg, rotate(1d2c3a4f) == 2c3a4f1d
        Word is an char list of size 4 (32 bits overall).
        """
        return word[1:] + word[:1]

    # Rijndael Rcon
    Rcon = [0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36,
            0x6c, 0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97,
            0x35, 0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72,
            0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66,
            0xcc, 0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04,
            0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d,
            0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3,
            0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61,
            0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a,
            0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40,
            0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc,
            0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5,
            0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a,
            0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d,
            0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c,
            0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35,
            0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4,
            0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc,
            0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04, 0x08,
            0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a,
            0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 0x7d,
            0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2,
            0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 0x74,
            0xe8, 0xcb ]

    def getRconValue(self, num):
        """Retrieves a given Rcon Value"""
        return self.Rcon[num]

    def core(self, word, iteration):
        """Key schedule core."""
        # rotate the 32-bit word 8 bits to the left
        word = self.rotate(word)
        # apply S-Box substitution on all 4 parts of the 32-bit word
        for i in range(4):
            word[i] = self.getSBoxValue(word[i])
        # XOR the output of the rcon operation with i to the first part
        # (leftmost) only
        word[0] = word[0] ^ self.getRconValue(iteration)
        return word

    def expandKey(self, key, size, expandedKeySize):
        """Rijndael's key expansion.

        Expands an 128,192,256 key into an 176,208,240 bytes key

        expandedKey is a char list of large enough size,
        key is the non-expanded key.
        """
        # current expanded keySize, in bytes
        currentSize = 0
        rconIteration = 1
        expandedKey = [0] * expandedKeySize

        # set the 16, 24, 32 bytes of the expanded key to the input key
        for j in range(size):
            expandedKey[j] = key[j]
        currentSize += size

        while currentSize < expandedKeySize:
            # assign the previous 4 bytes to the temporary value t
            t = expandedKey[currentSize-4:currentSize]

            # every 16,24,32 bytes we apply the core schedule to t
            # and increment rconIteration afterwards
            if currentSize % size == 0:
                t = self.core(t, rconIteration)
                rconIteration += 1
            # For 256-bit keys, we add an extra sbox to the calculation
            if size == self.keySize["SIZE_256"] and ((currentSize % size) == 16):
                for l in range(4): t[l] = self.getSBoxValue(t[l])

            # We XOR t with the four-byte block 16,24,32 bytes before the new
            # expanded key.  This becomes the next four bytes in the expanded
            # key.
            for m in range(4):
                expandedKey[currentSize] = expandedKey[currentSize - size] ^ \
                        t[m]
                currentSize += 1

        return expandedKey

    def addRoundKey(self, state, roundKey):
        """Adds (XORs) the round key to the state."""
        for i in range(16):
            state[i] ^= roundKey[i]
        return state

    def createRoundKey(self, expandedKey, roundKeyPointer):
        """Create a round key.
        Creates a round key from the given expanded key and the
        position within the expanded key.
        """
        roundKey = [0] * 16
        for i in range(4):
            for j in range(4):
                roundKey[j*4+i] = expandedKey[roundKeyPointer + i*4 + j]
        return roundKey

    def galois_multiplication(self, a, b):
        """Galois multiplication of 8 bit characters a and b."""
        p = 0
        for counter in range(8):
            if b & 1: p ^= a
            hi_bit_set = a & 0x80
            a <<= 1
            # keep a 8 bit
            a &= 0xFF
            if hi_bit_set:
                a ^= 0x1b
            b >>= 1
        return p

    #
    # substitute all the values from the state with the value in the SBox
    # using the state value as index for the SBox
    #
    def subBytes(self, state, isInv):
        if isInv: getter = self.getSBoxInvert
        else: getter = self.getSBoxValue
        for i in range(16): state[i] = getter(state[i])
        return state

    # iterate over the 4 rows and call shiftRow() with that row
    def shiftRows(self, state, isInv):
        for i in range(4):
            state = self.shiftRow(state, i*4, i, isInv)
        return state

    # each iteration shifts the row to the left by 1
    def shiftRow(self, state, statePointer, nbr, isInv):
        for i in range(nbr):
            if isInv:
                state[statePointer:statePointer+4] = \
                        state[statePointer+3:statePointer+4] + \
                        state[statePointer:statePointer+3]
            else:
                state[statePointer:statePointer+4] = \
                        state[statePointer+1:statePointer+4] + \
                        state[statePointer:statePointer+1]
        return state

    # galois multiplication of the 4x4 matrix
    def mixColumns(self, state, isInv):
        # iterate over the 4 columns
        for i in range(4):
            # construct one column by slicing over the 4 rows
            column = state[i:i+16:4]
            # apply the mixColumn on one column
            column = self.mixColumn(column, isInv)
            # put the values back into the state
            state[i:i+16:4] = column

        return state

    # galois multiplication of 1 column of the 4x4 matrix
    def mixColumn(self, column, isInv):
        if isInv: mult = [14, 9, 13, 11]
        else: mult = [2, 1, 1, 3]
        cpy = list(column)
        g = self.galois_multiplication

        column[0] = g(cpy[0], mult[0]) ^ g(cpy[3], mult[1]) ^ \
                    g(cpy[2], mult[2]) ^ g(cpy[1], mult[3])
        column[1] = g(cpy[1], mult[0]) ^ g(cpy[0], mult[1]) ^ \
                    g(cpy[3], mult[2]) ^ g(cpy[2], mult[3])
        column[2] = g(cpy[2], mult[0]) ^ g(cpy[1], mult[1]) ^ \
                    g(cpy[0], mult[2]) ^ g(cpy[3], mult[3])
        column[3] = g(cpy[3], mult[0]) ^ g(cpy[2], mult[1]) ^ \
                    g(cpy[1], mult[2]) ^ g(cpy[0], mult[3])
        return column

    # applies the 4 operations of the forward round in sequence
    def aes_round(self, state, roundKey):
        state = self.subBytes(state, False)
        state = self.shiftRows(state, False)
        state = self.mixColumns(state, False)
        state = self.addRoundKey(state, roundKey)
        return state

    # applies the 4 operations of the inverse round in sequence
    def aes_invRound(self, state, roundKey):
        state = self.shiftRows(state, True)
        state = self.subBytes(state, True)
        state = self.addRoundKey(state, roundKey)
        state = self.mixColumns(state, True)
        return state

    # Perform the initial operations, the standard round, and the final
    # operations of the forward aes, creating a round key for each round
    def aes_main(self, state, expandedKey, nbrRounds):
        state = self.addRoundKey(state, self.createRoundKey(expandedKey, 0))
        i = 1
        while i < nbrRounds:
            state = self.aes_round(state,
                                   self.createRoundKey(expandedKey, 16*i))
            i += 1
        state = self.subBytes(state, False)
        state = self.shiftRows(state, False)
        state = self.addRoundKey(state,
                                 self.createRoundKey(expandedKey, 16*nbrRounds))
        return state

    # Perform the initial operations, the standard round, and the final
    # operations of the inverse aes, creating a round key for each round
    def aes_invMain(self, state, expandedKey, nbrRounds):
        state = self.addRoundKey(state,
                                 self.createRoundKey(expandedKey, 16*nbrRounds))
        i = nbrRounds - 1
        while i > 0:
            state = self.aes_invRound(state,
                                      self.createRoundKey(expandedKey, 16*i))
            i -= 1
        state = self.shiftRows(state, True)
        state = self.subBytes(state, True)
        state = self.addRoundKey(state, self.createRoundKey(expandedKey, 0))
        return state

    # encrypts a 128 bit input block against the given key of size specified
    def encrypt(self, iput, key, size):
        output = [0] * 16
        # the number of rounds
        nbrRounds = 0
        # the 128 bit block to encode
        block = [0] * 16
        # set the number of rounds
        if size == self.keySize["SIZE_128"]: nbrRounds = 10
        elif size == self.keySize["SIZE_192"]: nbrRounds = 12
        elif size == self.keySize["SIZE_256"]: nbrRounds = 14
        else: return None

        # the expanded keySize
        expandedKeySize = 16*(nbrRounds+1)

        # Set the block values, for the block:
        # a0,0 a0,1 a0,2 a0,3
        # a1,0 a1,1 a1,2 a1,3
        # a2,0 a2,1 a2,2 a2,3
        # a3,0 a3,1 a3,2 a3,3
        # the mapping order is a0,0 a1,0 a2,0 a3,0 a0,1 a1,1 ... a2,3 a3,3
        #
        # iterate over the columns
        for i in range(4):
            # iterate over the rows
            for j in range(4):
                block[(i+(j*4))] = iput[(i*4)+j]

        # expand the key into an 176, 208, 240 bytes key
        # the expanded key
        expandedKey = self.expandKey(key, size, expandedKeySize)

        # encrypt the block using the expandedKey
        block = self.aes_main(block, expandedKey, nbrRounds)

        # unmap the block again into the output
        for k in range(4):
            # iterate over the rows
            for l in range(4):
                output[(k*4)+l] = block[(k+(l*4))]
        return output

    # decrypts a 128 bit input block against the given key of size specified
    def decrypt(self, iput, key, size):
        output = [0] * 16
        # the number of rounds
        nbrRounds = 0
        # the 128 bit block to decode
        block = [0] * 16
        # set the number of rounds
        if size == self.keySize["SIZE_128"]: nbrRounds = 10
        elif size == self.keySize["SIZE_192"]: nbrRounds = 12
        elif size == self.keySize["SIZE_256"]: nbrRounds = 14
        else: return None

        # the expanded keySize
        expandedKeySize = 16*(nbrRounds+1)

        # Set the block values, for the block:
        # a0,0 a0,1 a0,2 a0,3
        # a1,0 a1,1 a1,2 a1,3
        # a2,0 a2,1 a2,2 a2,3
        # a3,0 a3,1 a3,2 a3,3
        # the mapping order is a0,0 a1,0 a2,0 a3,0 a0,1 a1,1 ... a2,3 a3,3

        # iterate over the columns
        for i in range(4):
            # iterate over the rows
            for j in range(4):
                block[(i+(j*4))] = iput[(i*4)+j]
        # expand the key into an 176, 208, 240 bytes key
        expandedKey = self.expandKey(key, size, expandedKeySize)
        # decrypt the block using the expandedKey
        block = self.aes_invMain(block, expandedKey, nbrRounds)
        # unmap the block again into the output
        for k in range(4):
            # iterate over the rows
            for l in range(4):
                output[(k*4)+l] = block[(k+(l*4))]
        return output

class AESModeOfOperation(object):

    aes = AES()

    # structure of supported modes of operation
    modeOfOperation = dict(OFB=0, CFB=1, CBC=2)

    # converts a 16 character string into a number array
    def convertString(self, string, start, end, mode):
        if end - start > 16: end = start + 16
        if mode == self.modeOfOperation["CBC"]: ar = [0] * 16
        else: ar = []

        i = start
        j = 0
        while len(ar) < end - start:
            ar.append(0)
        while i < end:
            ar[j] = ord(string[i])
            j += 1
            i += 1
        return ar

    # Mode of Operation Encryption
    # stringIn - Input String
    # mode - mode of type modeOfOperation
    # hexKey - a hex key of the bit length size
    # size - the bit length of the key
    # hexIV - the 128 bit hex Initilization Vector
    def encrypt(self, stringIn, mode, key, size, IV):
        if len(key) % size:
            return None
        if len(IV) % 16:
            return None
        # the AES input/output
        plaintext = []
        iput = [0] * 16
        output = []
        ciphertext = [0] * 16
        # the output cipher string
        cipherOut = []
        # char firstRound
        firstRound = True
        if stringIn != None:
            for j in range(int(math.ceil(float(len(stringIn))/16))):
                start = j*16
                end = j*16+16
                if  end > len(stringIn):
                    end = len(stringIn)
                plaintext = self.convertString(stringIn, start, end, mode)
                # print 'PT@%s:%s' % (j, plaintext)
                if mode == self.modeOfOperation["CFB"]:
                    if firstRound:
                        output = self.aes.encrypt(IV, key, size)
                        firstRound = False
                    else:
                        output = self.aes.encrypt(iput, key, size)
                    for i in range(16):
                        if len(plaintext)-1 < i:
                            ciphertext[i] = 0 ^ output[i]
                        elif len(output)-1 < i:
                            ciphertext[i] = plaintext[i] ^ 0
                        elif len(plaintext)-1 < i and len(output) < i:
                            ciphertext[i] = 0 ^ 0
                        else:
                            ciphertext[i] = plaintext[i] ^ output[i]
                    for k in range(end-start):
                        cipherOut.append(ciphertext[k])
                    iput = ciphertext
                elif mode == self.modeOfOperation["OFB"]:
                    if firstRound:
                        output = self.aes.encrypt(IV, key, size)
                        firstRound = False
                    else:
                        output = self.aes.encrypt(iput, key, size)
                    for i in range(16):
                        if len(plaintext)-1 < i:
                            ciphertext[i] = 0 ^ output[i]
                        elif len(output)-1 < i:
                            ciphertext[i] = plaintext[i] ^ 0
                        elif len(plaintext)-1 < i and len(output) < i:
                            ciphertext[i] = 0 ^ 0
                        else:
                            ciphertext[i] = plaintext[i] ^ output[i]
                    for k in range(end-start):
                        cipherOut.append(ciphertext[k])
                    iput = output
                elif mode == self.modeOfOperation["CBC"]:
                    for i in range(16):
                        if firstRound:
                            iput[i] =  plaintext[i] ^ IV[i]
                        else:
                            iput[i] =  plaintext[i] ^ ciphertext[i]
                    # print 'IP@%s:%s' % (j, iput)
                    firstRound = False
                    ciphertext = self.aes.encrypt(iput, key, size)
                    # always 16 bytes because of the padding for CBC
                    for k in range(16):
                        cipherOut.append(ciphertext[k])
        return mode, len(stringIn), cipherOut

    # Mode of Operation Decryption
    # cipherIn - Encrypted String
    # originalsize - The unencrypted string length - required for CBC
    # mode - mode of type modeOfOperation
    # key - a number array of the bit length size
    # size - the bit length of the key
    # IV - the 128 bit number array Initilization Vector
    def decrypt(self, cipherIn, originalsize, mode, key, size, IV):
        # cipherIn = unescCtrlChars(cipherIn)
        if len(key) % size:
            return None
        if len(IV) % 16:
            return None
        # the AES input/output
        ciphertext = []
        iput = []
        output = []
        plaintext = [0] * 16
        # the output plain text string
        stringOut = ''
        # char firstRound
        firstRound = True
        if cipherIn != None:
            for j in range(int(math.ceil(float(len(cipherIn))/16))):
                start = j*16
                end = j*16+16
                if j*16+16 > len(cipherIn):
                    end = len(cipherIn)
                ciphertext = cipherIn[start:end]
                if mode == self.modeOfOperation["CFB"]:
                    if firstRound:
                        output = self.aes.encrypt(IV, key, size)
                        firstRound = False
                    else:
                        output = self.aes.encrypt(iput, key, size)
                    for i in range(16):
                        if len(output)-1 < i:
                            plaintext[i] = 0 ^ ciphertext[i]
                        elif len(ciphertext)-1 < i:
                            plaintext[i] = output[i] ^ 0
                        elif len(output)-1 < i and len(ciphertext) < i:
                            plaintext[i] = 0 ^ 0
                        else:
                            plaintext[i] = output[i] ^ ciphertext[i]
                    for k in range(end-start):
                        stringOut += chr(plaintext[k])
                    iput = ciphertext
                elif mode == self.modeOfOperation["OFB"]:
                    if firstRound:
                        output = self.aes.encrypt(IV, key, size)
                        firstRound = False
                    else:
                        output = self.aes.encrypt(iput, key, size)
                    for i in range(16):
                        if len(output)-1 < i:
                            plaintext[i] = 0 ^ ciphertext[i]
                        elif len(ciphertext)-1 < i:
                            plaintext[i] = output[i] ^ 0
                        elif len(output)-1 < i and len(ciphertext) < i:
                            plaintext[i] = 0 ^ 0
                        else:
                            plaintext[i] = output[i] ^ ciphertext[i]
                    for k in range(end-start):
                        stringOut += chr(plaintext[k])
                    iput = output
                elif mode == self.modeOfOperation["CBC"]:
                    output = self.aes.decrypt(ciphertext, key, size)
                    for i in range(16):
                        if firstRound:
                            plaintext[i] = IV[i] ^ output[i]
                        else:
                            plaintext[i] = iput[i] ^ output[i]
                    firstRound = False
                    if originalsize is not None and originalsize < end:
                        for k in range(originalsize-start):
                            stringOut += chr(plaintext[k])
                    else:
                        for k in range(end-start):
                            stringOut += chr(plaintext[k])
                    iput = ciphertext
        return stringOut

# end of aes.py code

# pywallet crypter implementation

crypter = None

try:
    from Crypto.Cipher import AES
    crypter = 'pycrypto'
except:
    pass

class Crypter_pycrypto( object ):
    def SetKeyFromPassphrase(self, vKeyData, vSalt, nDerivIterations, nDerivationMethod):
        if nDerivationMethod != 0:
            return 0
        data = vKeyData + vSalt
        for i in xrange(nDerivIterations):
            data = hashlib.sha512(data).digest()
        self.SetKey(data[0:32])
        self.SetIV(data[32:32+16])
        return len(data)

    def SetKey(self, key):
        self.chKey = key

    def SetIV(self, iv):
        self.chIV = iv[0:16]

    def Encrypt(self, data):
        return AES.new(self.chKey,AES.MODE_CBC,self.chIV).encrypt(data)[0:32]
 
    def Decrypt(self, data):
        return AES.new(self.chKey,AES.MODE_CBC,self.chIV).decrypt(data)[0:32]

try:
    if not crypter:
        import ctypes
        import ctypes.util
        ssl = ctypes.cdll.LoadLibrary (ctypes.util.find_library ('ssl') or 'libeay32')
        crypter = 'ssl'
except:
    pass

class Crypter_ssl(object):
    def __init__(self):
        self.chKey = ctypes.create_string_buffer (32)
        self.chIV = ctypes.create_string_buffer (16)

    def SetKeyFromPassphrase(self, vKeyData, vSalt, nDerivIterations, nDerivationMethod):
        if nDerivationMethod != 0:
            return 0
        strKeyData = ctypes.create_string_buffer (vKeyData)
        chSalt = ctypes.create_string_buffer (vSalt)
        return ssl.EVP_BytesToKey(ssl.EVP_aes_256_cbc(), ssl.EVP_sha512(), chSalt, strKeyData,
            len(vKeyData), nDerivIterations, ctypes.byref(self.chKey), ctypes.byref(self.chIV))

    def SetKey(self, key):
        self.chKey = ctypes.create_string_buffer(key)

    def SetIV(self, iv):
        self.chIV = ctypes.create_string_buffer(iv)

    def Encrypt(self, data):
        buf = ctypes.create_string_buffer(len(data) + 16)
        written = ctypes.c_int(0)
        final = ctypes.c_int(0)
        ctx = ssl.EVP_CIPHER_CTX_new()
        ssl.EVP_CIPHER_CTX_init(ctx)
        ssl.EVP_EncryptInit_ex(ctx, ssl.EVP_aes_256_cbc(), None, self.chKey, self.chIV)
        ssl.EVP_EncryptUpdate(ctx, buf, ctypes.byref(written), data, len(data))
        output = buf.raw[:written.value]
        ssl.EVP_EncryptFinal_ex(ctx, buf, ctypes.byref(final))
        output += buf.raw[:final.value]
        return output

    def Decrypt(self, data):
        buf = ctypes.create_string_buffer(len(data) + 16)
        written = ctypes.c_int(0)
        final = ctypes.c_int(0)
        ctx = ssl.EVP_CIPHER_CTX_new()
        ssl.EVP_CIPHER_CTX_init(ctx)
        ssl.EVP_DecryptInit_ex(ctx, ssl.EVP_aes_256_cbc(), None, self.chKey, self.chIV)
        ssl.EVP_DecryptUpdate(ctx, buf, ctypes.byref(written), data, len(data))
        output = buf.raw[:written.value]
        ssl.EVP_DecryptFinal_ex(ctx, buf, ctypes.byref(final))
        output += buf.raw[:final.value]
        return output

class Crypter_pure(object):
    def __init__(self):
        self.m = AESModeOfOperation()
        self.cbc = self.m.modeOfOperation["CBC"]
        self.sz = self.m.aes.keySize["SIZE_256"]

    def SetKeyFromPassphrase(self, vKeyData, vSalt, nDerivIterations, nDerivationMethod):
        if nDerivationMethod != 0:
            return 0
        data = vKeyData + vSalt
        for i in xrange(nDerivIterations):
            data = hashlib.sha512(data).digest()
        self.SetKey(data[0:32])
        self.SetIV(data[32:32+16])
        return len(data)

    def SetKey(self, key):
        self.chKey = [ord(i) for i in key]

    def SetIV(self, iv):
        self.chIV = [ord(i) for i in iv]

    def Encrypt(self, data):
        mode, size, cypher = self.m.encrypt(data, self.cbc, self.chKey, self.sz, self.chIV)
        return ''.join(map(chr, cypher))
 
    def Decrypt(self, data):
        chData = [ord(i) for i in data]
        return self.m.decrypt(chData, self.sz, self.cbc, self.chKey, self.sz, self.chIV)

# secp256k1

_p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2FL
_r = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141L
_b = 0x0000000000000000000000000000000000000000000000000000000000000007L
_a = 0x0000000000000000000000000000000000000000000000000000000000000000L
_Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798L
_Gy = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8L

# python-ecdsa code (EC_KEY implementation)

class CurveFp( object ):
    def __init__( self, p, a, b ):
        self.__p = p
        self.__a = a
        self.__b = b

    def p( self ):
        return self.__p

    def a( self ):
        return self.__a

    def b( self ):
        return self.__b

    def contains_point( self, x, y ):
        return ( y * y - ( x * x * x + self.__a * x + self.__b ) ) % self.__p == 0

class Point( object ):
    def __init__( self, curve, x, y, order = None ):
        self.__curve = curve
        self.__x = x
        self.__y = y
        self.__order = order
        if self.__curve: assert self.__curve.contains_point( x, y )
        if order: assert self * order == INFINITY
 
    def __add__( self, other ):
        if other == INFINITY: return self
        if self == INFINITY: return other
        assert self.__curve == other.__curve
        if self.__x == other.__x:
            if ( self.__y + other.__y ) % self.__curve.p() == 0:
                return INFINITY
            else:
                return self.double()

        p = self.__curve.p()
        l = ( ( other.__y - self.__y ) * \
                    inverse_mod( other.__x - self.__x, p ) ) % p
        x3 = ( l * l - self.__x - other.__x ) % p
        y3 = ( l * ( self.__x - x3 ) - self.__y ) % p
        return Point( self.__curve, x3, y3 )

    def __mul__( self, other ):
        def leftmost_bit( x ):
            assert x > 0
            result = 1L
            while result <= x: result = 2 * result
            return result / 2

        e = other
        if self.__order: e = e % self.__order
        if e == 0: return INFINITY
        if self == INFINITY: return INFINITY
        assert e > 0
        e3 = 3 * e
        negative_self = Point( self.__curve, self.__x, -self.__y, self.__order )
        i = leftmost_bit( e3 ) / 2
        result = self
        while i > 1:
            result = result.double()
            if ( e3 & i ) != 0 and ( e & i ) == 0: result = result + self
            if ( e3 & i ) == 0 and ( e & i ) != 0: result = result + negative_self
            i = i / 2
        return result

    def __rmul__( self, other ):
        return self * other

    def __str__( self ):
        if self == INFINITY: return "infinity"
        return "(%d,%d)" % ( self.__x, self.__y )

    def double( self ):
        if self == INFINITY:
            return INFINITY

        p = self.__curve.p()
        a = self.__curve.a()
        l = ( ( 3 * self.__x * self.__x + a ) * \
                    inverse_mod( 2 * self.__y, p ) ) % p
        x3 = ( l * l - 2 * self.__x ) % p
        y3 = ( l * ( self.__x - x3 ) - self.__y ) % p
        return Point( self.__curve, x3, y3 )

    def x( self ):
        return self.__x

    def y( self ):
        return self.__y

    def curve( self ):
        return self.__curve
    
    def order( self ):
        return self.__order
        
INFINITY = Point( None, None, None )

def inverse_mod( a, m ):
    if a < 0 or m <= a: a = a % m
    c, d = a, m
    uc, vc, ud, vd = 1, 0, 0, 1
    while c != 0:
        q, c, d = divmod( d, c ) + ( c, )
        uc, vc, ud, vd = ud - q*uc, vd - q*vc, uc, vc
    assert d == 1
    if ud > 0: return ud
    else: return ud + m

class Signature( object ):
    def __init__( self, r, s ):
        self.r = r
        self.s = s
        
class Public_key( object ):
    def __init__( self, generator, point ):
        self.curve = generator.curve()
        self.generator = generator
        self.point = point
        n = generator.order()
        if not n:
            raise RuntimeError, "Generator point must have order."
        if not n * point == INFINITY:
            raise RuntimeError, "Generator point order is bad."
        if point.x() < 0 or n <= point.x() or point.y() < 0 or n <= point.y():
            raise RuntimeError, "Generator point has x or y out of range."

    def verifies( self, hash, signature ):
        G = self.generator
        n = G.order()
        r = signature.r
        s = signature.s
        if r < 1 or r > n-1: return False
        if s < 1 or s > n-1: return False
        c = inverse_mod( s, n )
        u1 = ( hash * c ) % n
        u2 = ( r * c ) % n
        xy = u1 * G + u2 * self.point
        v = xy.x() % n
        return v == r

class Private_key( object ):
    def __init__( self, public_key, secret_multiplier ):
        self.public_key = public_key
        self.secret_multiplier = secret_multiplier

    def der( self ):
        hex_der_key = '06052b8104000a30740201010420' + \
            '%064x' % self.secret_multiplier + \
            'a00706052b8104000aa14403420004' + \
            '%064x' % self.public_key.point.x() + \
            '%064x' % self.public_key.point.y()
        return hex_der_key.decode('hex')

    def sign( self, hash, random_k ):
        G = self.public_key.generator
        n = G.order()
        k = random_k % n
        p1 = k * G
        r = p1.x()
        if r == 0: raise RuntimeError, "amazingly unlucky random number r"
        s = ( inverse_mod( k, n ) * \
                    ( hash + ( self.secret_multiplier * r ) % n ) ) % n
        if s == 0: raise RuntimeError, "amazingly unlucky random number s"
        return Signature( r, s )

class EC_KEY(object):
    def __init__( self, secret ):
        curve = CurveFp( _p, _a, _b )
        generator = Point( curve, _Gx, _Gy, _r )
        self.pubkey = Public_key( generator, generator * secret )
        self.privkey = Private_key( self.pubkey, secret )
        self.secret = secret

# end of python-ecdsa code

# pywallet openssl private key implementation

def i2d_ECPrivateKey(pkey, compressed=False):
    if compressed:
        key = '3081d30201010420' + \
            '%064x' % pkey.secret + \
            'a081a53081a2020101302c06072a8648ce3d0101022100' + \
            '%064x' % _p + \
            '3006040100040107042102' + \
            '%064x' % _Gx + \
            '022100' + \
            '%064x' % _r + \
            '020101a124032200'
    else:
        key = '308201130201010420' + \
            '%064x' % pkey.secret + \
            'a081a53081a2020101302c06072a8648ce3d0101022100' + \
            '%064x' % _p + \
            '3006040100040107044104' + \
            '%064x' % _Gx + \
            '%064x' % _Gy + \
            '022100' + \
            '%064x' % _r + \
            '020101a144034200'

    return key.decode('hex') + i2o_ECPublicKey(pkey, compressed)

def i2o_ECPublicKey(pkey, compressed=False):
    # public keys are 65 bytes long (520 bits)
    # 0x04 + 32-byte X-coordinate + 32-byte Y-coordinate
    # 0x00 = point at infinity, 0x02 and 0x03 = compressed, 0x04 = uncompressed
    # compressed keys: <sign> <x> where <sign> is 0x02 if y is even and 0x03 if y is odd
    if compressed:
        if pkey.pubkey.point.y() & 1:
            key = '03' + '%064x' % pkey.pubkey.point.x()
        else:
            key = '02' + '%064x' % pkey.pubkey.point.x()
    else:
        key = '04' + \
            '%064x' % pkey.pubkey.point.x() + \
            '%064x' % pkey.pubkey.point.y()

    return key.decode('hex')

# bitcointools hashes and base58 implementation

def hash_160(public_key):
    md = hashlib.new('ripemd160')
    md.update(hashlib.sha256(public_key).digest())
    return md.digest()

def public_key_to_bc_address(public_key):
    h160 = hash_160(public_key)
    return hash_160_to_bc_address(h160)

def hash_160_to_bc_address(h160):
    vh160 = chr(addrtype) + h160
    h = Hash(vh160)
    addr = vh160 + h[0:4]
    return b58encode(addr)

def bc_address_to_hash_160(addr):
    bytes = b58decode(addr, 25)
    return bytes[1:21]

__b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
__b58base = len(__b58chars)

def b58encode(v):
    """ encode v, which is a string of bytes, to base58.        
    """

    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += (256**i) * ord(c)

    result = ''
    while long_value >= __b58base:
        div, mod = divmod(long_value, __b58base)
        result = __b58chars[mod] + result
        long_value = div
    result = __b58chars[long_value] + result

    # Bitcoin does a little leading-zero-compression:
    # leading 0-bytes in the input become leading-1s
    nPad = 0
    for c in v:
        if c == '\0': nPad += 1
        else: break

    return (__b58chars[0]*nPad) + result

def b58decode(v, length):
    """ decode v into a string of len bytes
    """
    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += __b58chars.find(c) * (__b58base**i)

    result = ''
    while long_value >= 256:
        div, mod = divmod(long_value, 256)
        result = chr(mod) + result
        long_value = div
    result = chr(long_value) + result

    nPad = 0
    for c in v:
        if c == __b58chars[0]: nPad += 1
        else: break

    result = chr(0)*nPad + result
    if length is not None and len(result) != length:
        return None

    return result

# end of bitcointools base58 implementation


# address handling code

def Hash(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def EncodeBase58Check(secret):
    hash = Hash(secret)
    return b58encode(secret + hash[0:4])

def DecodeBase58Check(sec):
    vchRet = b58decode(sec, None)
    secret = vchRet[0:-4]
    csum = vchRet[-4:]
    hash = Hash(secret)
    cs32 = hash[0:4]
    if cs32 != csum:
        return None
    else:
        return secret

def PrivKeyToSecret(privkey):
    if len(privkey) == 279:
        return privkey[9:9+32]
    else:
        return privkey[8:8+32]

def SecretToASecret(secret, compressed=False):
    vchIn = chr((addrtype+128)&255) + secret
    if compressed: vchIn += '\01'
    return EncodeBase58Check(vchIn)

def ASecretToSecret(sec):
    vch = DecodeBase58Check(sec)
    if vch and vch[0] == chr((addrtype+128)&255):
        return vch[1:]
    else:
        return False

def regenerate_key(sec):
    b = ASecretToSecret(sec)
    if not b:
        return False
    b = b[0:32]
    secret = int('0x' + b.encode('hex'), 16)
    return EC_KEY(secret)

def GetPubKey(pkey, compressed=False):
    return i2o_ECPublicKey(pkey, compressed)

def GetPrivKey(pkey, compressed=False):
    return i2d_ECPrivateKey(pkey, compressed)

def GetSecret(pkey):
    return ('%064x' % pkey.secret).decode('hex')

def is_compressed(sec):
    b = ASecretToSecret(sec)
    return len(b) == 33

# bitcointools wallet.dat handling code

def create_env(db_dir):
    db_env = DBEnv(0)
    r = db_env.open(db_dir, (DB_CREATE|DB_INIT_LOCK|DB_INIT_LOG|DB_INIT_MPOOL|DB_INIT_TXN|DB_THREAD|DB_RECOVER))
    return db_env

def parse_CAddress(vds):
    d = {'ip':'0.0.0.0','port':0,'nTime': 0}
    try:
        d['nVersion'] = vds.read_int32()
        d['nTime'] = vds.read_uint32()
        d['nServices'] = vds.read_uint64()
        d['pchReserved'] = vds.read_bytes(12)
        d['ip'] = socket.inet_ntoa(vds.read_bytes(4))
        d['port'] = vds.read_uint16()
    except:
        pass
    return d

def deserialize_CAddress(d):
    return d['ip']+":"+str(d['port'])

def parse_BlockLocator(vds):
    d = { 'hashes' : [] }
    nHashes = vds.read_compact_size()
    for i in xrange(nHashes):
        d['hashes'].append(vds.read_bytes(32))
        return d

def deserialize_BlockLocator(d):
  result = "Block Locator top: "+d['hashes'][0][::-1].encode('hex_codec')
  return result

def parse_setting(setting, vds):
    if setting[0] == "f":    # flag (boolean) settings
        return str(vds.read_boolean())
    elif setting[0:4] == "addr": # CAddress
        d = parse_CAddress(vds)
        return deserialize_CAddress(d)
    elif setting == "nTransactionFee":
        return vds.read_int64()
    elif setting == "nLimitProcessors":
        return vds.read_int32()
    return 'unknown setting'

class SerializationError(Exception):
    """ Thrown when there's a problem deserializing or serializing """

class BCDataStream(object):
    def __init__(self):
        self.input = None
        self.read_cursor = 0

    def clear(self):
        self.input = None
        self.read_cursor = 0

    def write(self, bytes):    # Initialize with string of bytes
        if self.input is None:
            self.input = bytes
        else:
            self.input += bytes

    def map_file(self, file, start):    # Initialize with bytes from file
        self.input = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
        self.read_cursor = start
    def seek_file(self, position):
        self.read_cursor = position
    def close_file(self):
        self.input.close()

    def read_string(self):
        # Strings are encoded depending on length:
        # 0 to 252 :    1-byte-length followed by bytes (if any)
        # 253 to 65,535 : byte'253' 2-byte-length followed by bytes
        # 65,536 to 4,294,967,295 : byte '254' 4-byte-length followed by bytes
        # ... and the Bitcoin client is coded to understand:
        # greater than 4,294,967,295 : byte '255' 8-byte-length followed by bytes of string
        # ... but I don't think it actually handles any strings that big.
        if self.input is None:
            raise SerializationError("call write(bytes) before trying to deserialize")

        try:
            length = self.read_compact_size()
        except IndexError:
            raise SerializationError("attempt to read past end of buffer")

        return self.read_bytes(length)

    def write_string(self, string):
        # Length-encoded as with read-string
        self.write_compact_size(len(string))
        self.write(string)

    def read_bytes(self, length):
        try:
            result = self.input[self.read_cursor:self.read_cursor+length]
            self.read_cursor += length
            return result
        except IndexError:
            raise SerializationError("attempt to read past end of buffer")

        return ''

    def read_boolean(self): return self.read_bytes(1)[0] != chr(0)
    def read_int16(self): return self._read_num('<h')
    def read_uint16(self): return self._read_num('<H')
    def read_int32(self): return self._read_num('<i')
    def read_uint32(self): return self._read_num('<I')
    def read_int64(self): return self._read_num('<q')
    def read_uint64(self): return self._read_num('<Q')

    def write_boolean(self, val): return self.write(chr(1) if val else chr(0))
    def write_int16(self, val): return self._write_num('<h', val)
    def write_uint16(self, val): return self._write_num('<H', val)
    def write_int32(self, val): return self._write_num('<i', val)
    def write_uint32(self, val): return self._write_num('<I', val)
    def write_int64(self, val): return self._write_num('<q', val)
    def write_uint64(self, val): return self._write_num('<Q', val)

    def read_compact_size(self):
        size = ord(self.input[self.read_cursor])
        self.read_cursor += 1
        if size == 253:
            size = self._read_num('<H')
        elif size == 254:
            size = self._read_num('<I')
        elif size == 255:
            size = self._read_num('<Q')
        return size

    def write_compact_size(self, size):
        if size < 0:
            raise SerializationError("attempt to write size < 0")
        elif size < 253:
             self.write(chr(size))
        elif size < 2**16:
            self.write('\xfd')
            self._write_num('<H', size)
        elif size < 2**32:
            self.write('\xfe')
            self._write_num('<I', size)
        elif size < 2**64:
            self.write('\xff')
            self._write_num('<Q', size)

    def _read_num(self, format):
        (i,) = struct.unpack_from(format, self.input, self.read_cursor)
        self.read_cursor += struct.calcsize(format)
        return i

    def _write_num(self, format, num):
        s = struct.pack(format, num)
        self.write(s)

def open_wallet(db_env, writable=False):
    db = DB(db_env)
    flags = DB_THREAD | (DB_CREATE if writable else DB_RDONLY)
    try:
        r = db.open("wallet.dat", "main", DB_BTREE, flags)
    except DBError:
        r = True

    if r is not None:
        logging.error("Couldn't open wallet.dat/main. Try quitting Bitcoin and running this again.")
        sys.exit(1)
    
    return db

def parse_wallet(db, item_callback):
    kds = BCDataStream()
    vds = BCDataStream()

    for (key, value) in db.items():
        d = { }

        kds.clear(); kds.write(key)
        vds.clear(); vds.write(value)

        type = kds.read_string()

        d["__key__"] = key
        d["__value__"] = value
        d["__type__"] = type

        try:
            if type == "tx":
                d["tx_id"] = kds.read_bytes(32)
            elif type == "name":
                d['hash'] = kds.read_string()
                d['name'] = vds.read_string()
            elif type == "version":
                d['version'] = vds.read_uint32()
            elif type == "minversion":
                d['minversion'] = vds.read_uint32()
            elif type == "setting":
                d['setting'] = kds.read_string()
                d['value'] = parse_setting(d['setting'], vds)
            elif type == "key":
                d['public_key'] = kds.read_bytes(kds.read_compact_size())
                d['private_key'] = vds.read_bytes(vds.read_compact_size())
            elif type == "wkey":
                d['public_key'] = kds.read_bytes(kds.read_compact_size())
                d['private_key'] = vds.read_bytes(vds.read_compact_size())
                d['created'] = vds.read_int64()
                d['expires'] = vds.read_int64()
                d['comment'] = vds.read_string()
            elif type == "ckey":
                d['public_key'] = kds.read_bytes(kds.read_compact_size())
                d['crypted_key'] = vds.read_bytes(vds.read_compact_size())
            elif type == "mkey":
                d['nID'] = kds.read_int32()
                d['crypted_key'] = vds.read_bytes(vds.read_compact_size())
                d['salt'] = vds.read_bytes(vds.read_compact_size())
                d['nDerivationMethod'] = vds.read_int32()
                d['nDeriveIterations'] = vds.read_int32()
                d['vchOtherDerivationParameters'] = vds.read_bytes(vds.read_compact_size())
            elif type == "defaultkey":
                d['key'] = vds.read_bytes(vds.read_compact_size())
            elif type == "pool":
                d['n'] = kds.read_int64()
                d['nVersion'] = vds.read_int32()
                d['nTime'] = vds.read_int64()
                d['public_key'] = vds.read_bytes(vds.read_compact_size())
            elif type == "acc":
                d['account'] = kds.read_string()
                d['nVersion'] = vds.read_int32()
                d['public_key'] = vds.read_bytes(vds.read_compact_size())
            elif type == "acentry":
                d['account'] = kds.read_string()
                d['n'] = kds.read_uint64()
                d['nVersion'] = vds.read_int32()
                d['nCreditDebit'] = vds.read_int64()
                d['nTime'] = vds.read_int64()
                d['otherAccount'] = vds.read_string()
                d['comment'] = vds.read_string()
            elif type == "bestblock":
                d['nVersion'] = vds.read_int32()
                d.update(parse_BlockLocator(vds))
            
            item_callback(type, d)

        except Exception, e:
            traceback.print_exc()
            print("ERROR parsing wallet.dat, type %s" % type)
            print("key data in hex: %s"%key.encode('hex_codec'))
            print("value data in hex: %s"%value.encode('hex_codec'))
            sys.exit(1)
    
def update_wallet(db, type, data):
    """Write a single item to the wallet.
    db must be open with writable=True.
    type and data are the type code and data dictionary as parse_wallet would
    give to item_callback.
    data's __key__, __value__ and __type__ are ignored; only the primary data
    fields are used.
    """
    d = data
    kds = BCDataStream()
    vds = BCDataStream()

    # Write the type code to the key
    kds.write_string(type)
    vds.write("")                         # Ensure there is something

    try:
        if type == "tx":
            raise NotImplementedError("Writing items of type 'tx'")
            kds.write(d['tx_id'])
        elif type == "name":
            kds.write_string(d['hash'])
            vds.write_string(d['name'])
        elif type == "version":
            vds.write_uint32(d['version'])
        elif type == "minversion":
            vds.write_uint32(d['minversion'])
        elif type == "setting":
            raise NotImplementedError("Writing items of type 'setting'")
            kds.write_string(d['setting'])
            #d['value'] = parse_setting(d['setting'], vds)
        elif type == "key":
            kds.write_string(d['public_key'])
            vds.write_string(d['private_key'])
        elif type == "wkey":
            kds.write_string(d['public_key'])
            vds.write_string(d['private_key'])
            vds.write_int64(d['created'])
            vds.write_int64(d['expires'])
            vds.write_string(d['comment'])
        elif type == "ckey":
            kds.write_string(d['public_key'])
            vds.write_string(d['crypted_key'])
        elif type == "defaultkey":
            vds.write_string(d['key'])
        elif type == "pool":
            kds.write_int64(d['n'])
            vds.write_int32(d['nVersion'])
            vds.write_int64(d['nTime'])
            vds.write_string(d['public_key'])
        elif type == "acc":
            kds.write_string(d['account'])
            vds.write_int32(d['nVersion'])
            vds.write_string(d['public_key'])
        elif type == "acentry":
            kds.write_string(d['account'])
            kds.write_uint64(d['n'])
            vds.write_int32(d['nVersion'])
            vds.write_int64(d['nCreditDebit'])
            vds.write_int64(d['nTime'])
            vds.write_string(d['otherAccount'])
            vds.write_string(d['comment'])
        elif type == "bestblock":
            vds.write_int32(d['nVersion'])
            vds.write_compact_size(len(d['hashes']))
            for h in d['hashes']:
                vds.write(h)
        else:
            print "Unknown key type: "+type

        # Write the key/value pair to the database
        db.put(kds.input, vds.input)

    except Exception, e:
        print("ERROR writing to wallet.dat, type %s"%type)
        print("data dictionary: %r"%data)
        traceback.print_exc()

def rewrite_wallet(db_env, destFileName, pre_put_callback=None):
    db = open_wallet(db_env)

    db_out = DB(db_env)
    try:
        r = db_out.open(destFileName, "main", DB_BTREE, DB_CREATE)
    except DBError:
        r = True

    if r is not None:
        logging.error("Couldn't open %s."%destFileName)
        sys.exit(1)

    def item_callback(type, d):
        if (pre_put_callback is None or pre_put_callback(type, d)):
            db_out.put(d["__key__"], d["__value__"])

    parse_wallet(db, item_callback)
    db_out.close()
    db.close()

# end of bitcointools wallet.dat handling code

# wallet.dat reader / writer

def read_wallet(json_db, db_env, print_wallet, print_wallet_transactions, transaction_filter):
    global password

    db = open_wallet(db_env)

    json_db['keys'] = []
    json_db['pool'] = []
    json_db['names'] = {}

    def item_callback(type, d):

        if type == "name":
            json_db['names'][d['hash']] = d['name']

        elif type == "version":
            json_db['version'] = d['version']

        elif type == "minversion":
            json_db['minversion'] = d['minversion']

        elif type == "setting":
            if not json_db.has_key('settings'): json_db['settings'] = {}
            json_db["settings"][d['setting']] = d['value']

        elif type == "defaultkey":
            json_db['defaultkey'] = public_key_to_bc_address(d['key'])

        elif type == "key":
            addr = public_key_to_bc_address(d['public_key'])
            compressed = d['public_key'][0] != '\04'
            sec = SecretToASecret(PrivKeyToSecret(d['private_key']), compressed)
            private_keys.append(sec)
            json_db['keys'].append({'addr' : addr, 'sec' : sec})
#            json_db['keys'].append({'addr' : addr, 'sec' : sec, 
#                'secret':PrivKeyToSecret(d['private_key']).encode('hex'),
#                'pubkey':d['public_key'].encode('hex'), 
#                'privkey':d['private_key'].encode('hex')})

        elif type == "wkey":
            if not json_db.has_key('wkey'): json_db['wkey'] = []
            json_db['wkey']['created'] = d['created']

        elif type == "ckey":
            addr = public_key_to_bc_address(d['public_key'])
            ckey = d['crypted_key']
            pubkey = d['public_key']
            json_db['keys'].append( {'addr' : addr, 'ckey': ckey.encode('hex'), 'pubkey': pubkey.encode('hex') })

        elif type == "mkey":
            mkey = {}
            mkey['nID'] = d['nID']
            mkey['crypted_key'] = d['crypted_key'].encode('hex')
            mkey['salt'] = d['salt'].encode('hex')
            mkey['nDeriveIterations'] = d['nDeriveIterations']
            mkey['nDerivationMethod'] = d['nDerivationMethod']
            mkey['vchOtherDerivationParameters'] = d['vchOtherDerivationParameters'].encode('hex')
            json_db['mkey'] = mkey

            if password:
                global crypter
                if crypter == 'pycrypto':
                    crypter = Crypter_pycrypto()
                elif crypter == 'ssl':
                    crypter = Crypter_ssl()
                else:
                    crypter = Crypter_pure()
                    logging.warning("pycrypto or libssl not found, decryption may be slow")
                res = crypter.SetKeyFromPassphrase(password, d['salt'], d['nDeriveIterations'], d['nDerivationMethod'])
                if res == 0:
                    logging.error("Unsupported derivation method")
                    sys.exit(1)
                masterkey = crypter.Decrypt(d['crypted_key'])
                crypter.SetKey(masterkey)

        elif type == "pool":
            json_db['pool'].append( {'n': d['n'], 'addr': public_key_to_bc_address(d['public_key']), 'nTime' : d['nTime'] } )

        elif type == "acc":
            json_db['acc'] = d['account']
            print("Account %s (current key: %s)"%(d['account'], public_key_to_bc_address(d['public_key'])))

        elif type == "acentry":
            json_db['acentry'] = (d['account'], d['nCreditDebit'], d['otherAccount'], time.ctime(d['nTime']), d['n'], d['comment'])

        elif type == "bestblock":
            json_db['bestblock'] = d['hashes'][0][::-1].encode('hex_codec')

        else:
            json_db[type] = 'unsupported'

    parse_wallet(db, item_callback)

    db.close()

    for k in json_db['keys']:
        addr = k['addr']
        if addr in json_db['names'].keys():
            k["label"] = json_db['names'][addr]
        else:
            k["reserve"] = 1

    crypted = 'mkey' in json_db.keys()

    if crypted and not password:
        logging.warning("encrypted wallet, specify password to decrypt")

    if crypted and password:
        check = True
        for k in json_db['keys']:
            ckey = k['ckey'].decode('hex')
            public_key = k['pubkey'].decode('hex')
            crypter.SetIV(Hash(public_key))
            secret = crypter.Decrypt(ckey)
            compressed = public_key[0] != '\04'

            if check:
                check = False
                pkey = EC_KEY(int('0x' + secret.encode('hex'), 16))
                if public_key != GetPubKey(pkey, compressed):
                    logging.error("wrong password")
                    sys.exit(1)

            sec = SecretToASecret(secret, compressed)
            k['sec'] = sec
            k['secret'] = secret.encode('hex')
            del(k['ckey'])
            del(k['secret'])
            del(k['pubkey'])
            private_keys.append(sec)

    del(json_db['pool'])
    del(json_db['names'])

def importprivkey(db, sec):

    pkey = regenerate_key(sec)
    if not pkey:
        return False

    compressed = is_compressed(sec)

    secret = GetSecret(pkey)
    private_key = GetPrivKey(pkey, compressed)
    public_key = GetPubKey(pkey, compressed)
    addr = public_key_to_bc_address(public_key)

    print "Address: %s" % addr
    print "Privkey: %s" % SecretToASecret(secret, compressed)

    global crypter, password, json_db

    crypted = 'mkey' in json_db.keys()

    if crypted:
        if password:
            crypter.SetIV(Hash(public_key))
            crypted_key = crypter.Encrypt(secret)
            update_wallet(db, 'ckey', { 'public_key' : public_key, 'crypted_key' : crypted_key })
            update_wallet(db, 'name', { 'hash' : addr, 'name' : '' })
            return True
        else:
            logging.error("password not specified")
            sys.exit(1)
    else:
        update_wallet(db, 'key', { 'public_key' : public_key, 'private_key' : private_key })
        update_wallet(db, 'name', { 'hash' : addr, 'name' : '' })
        return True

    return False

def privkey2address(sec):
    print "trying import", sec
    pkey = regenerate_key(sec)
    print pkey
    if not pkey:
        return None

    compressed = is_compressed(sec)

    public_key = GetPubKey(pkey, compressed)
    return public_key_to_bc_address(public_key)

from optparse import OptionParser

def main():

    global max_version, addrtype

    parser = OptionParser(usage="%prog [options]", version="%prog 1.2")

    parser.add_option("--dumpwallet", dest="dump", action="store_true",
        help="dump wallet in json format")

    parser.add_option("--importprivkey", dest="key",
        help="import private key from vanitygen")

    parser.add_option("--datadir", dest="datadir", 
        help="wallet directory (defaults to bitcoin default)")

    parser.add_option("--testnet", dest="testnet", action="store_true",
        help="use testnet subdirectory and address type")

    parser.add_option("--password", dest="password",
        help="password for the encrypted wallet")

    (options, args) = parser.parse_args()

    if options.dump is None and options.key is None:
        print "A mandatory option is missing\n"
        parser.print_help()
        sys.exit(1)

    if options.datadir is None:
        db_dir = determine_db_dir()
    else:
        db_dir = options.datadir

    if options.testnet:
        db_dir += "/testnet"
        addrtype = 111

    db_env = create_env(db_dir)

    global password

    if options.password:
        password = options.password

    read_wallet(json_db, db_env, True, True, "")

    if json_db.get('minversion') > max_version:
        print "Version mismatch (must be <= %d)" % max_version
        exit(1)

    if options.dump:
        print json.dumps(json_db, sort_keys=True, indent=4)

    elif options.key:
        if options.key in private_keys:
            print "Already exists"
        else:    
            db = open_wallet(db_env, writable=True)

            if importprivkey(db, options.key):
                print "Imported successfully"
            else:
                print "Bad private key"

            db.close()

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = settings
from django.conf import settings
from decimal import Decimal

MAIN_ACCOUNT = getattr(
    settings,
    "BITCOIND_MAIN_ACCOUNT",
    "somerandomstring14aqqwd")
BITCOIND_CONNECTION_STRING = getattr(
    settings,
    "BITCOIND_CONNECTION_STRING",
    "")
BITCOIN_PAYMENT_BUFFER_SIZE = getattr(
    settings,
    "BITCOIN_PAYMENT_BUFFER_SIZE",
    5)
BITCOIN_ADDRESS_BUFFER_SIZE = getattr(
    settings,
    "BITCOIN_ADDRESS_BUFFER_SIZE",
    5)
PAYMENT_VALID_HOURS = getattr(
    settings,
    "BITCOIND_PAYMENT_VALID_HOURS",
    128)
REUSE_ADDRESSES = getattr(
    settings,
    "BITCOIND_REUSE_ADDRESSES",
    True)
ESCROW_PAYMENT_TIME_HOURS = getattr(
    settings,
    "BITCOIND_ESCROW_PAYMENT_TIME_HOURS",
    4)
ESCROW_RELEASE_TIME_DAYS = getattr(
    settings,
    "BITCOIND_ESCROW_RELEASE_TIME_DAYS",
    14)
BITCOIN_MINIMUM_CONFIRMATIONS = getattr(
    settings,
    "BITCOIN_MINIMUM_CONFIRMATIONS",
    3)
BITCOIN_TRANSACTION_CACHING = getattr(
    settings,
    "BITCOIN_TRANSACTION_CACHING",
    False)
BITCOIN_TRANSACTION_SIGNALING = getattr(
    settings,
    "BITCOIN_TRANSACTION_SIGNALING",
    False)
BITCOIN_DISABLE_OUTGOING = getattr(
    settings,
    "BITCOIN_DISABLE_OUTGOING",
    False)
BITCOIN_CURRENCIES = getattr(
    settings,
    "BITCOIN_CURRENCIES",
    [
        "django_bitcoin.currency.BTCCurrency",
        "django_bitcoin.currency.EURCurrency",
        "django_bitcoin.currency.USDCurrency"
        ])
# Allow transfer of unconfirmed ammounts between wallets
BITCOIN_UNCONFIRMED_TRANSFERS = getattr(
    settings,
    "BITCOIN_UNCONFIRMED_TRANSFERS",
    False)

BITCOIN_PRIVKEY_FEE = getattr(
    settings,
    "BITCOIN_PRIVKEY_FEE",
    Decimal("0.0005"))

BITCOIN_OPENEXCHANGERATES_URL = getattr(
    settings,
    "BITCOIN_OPENEXCHANGERATES_URL",
    "http://openexchangerates.org/api/latest.json")

HISTORICALPRICES_FETCH_TIMESPAN_MINUTES = getattr(
    settings,
    "HISTORICALPRICES_FETCH_TIMESPAN_HOURS",
    60)

BITCOIN_OUTGOING_DEFAULT_DELAY_SECONDS = getattr(
    settings,
    "BITCOIN_OUTGOING_DEFAULT_DELAY_SECONDS",
    2)

ENABLE_INTERNAL_TRANSACTIONS = getattr(
    settings,
    "ENABLE_INTERNAL_TRANSACTIONS",
    True)


########NEW FILE########
__FILENAME__ = tasks
from __future__ import with_statement

import datetime
import random
import hashlib
import base64
from decimal import Decimal

from django.db import models

from django_bitcoin.utils import bitcoind
from django_bitcoin import settings

from django.utils.translation import ugettext as _
from django_bitcoin.models import DepositTransaction, BitcoinAddress

import django.dispatch

import jsonrpc

from BCAddressField import is_valid_btc_address

from django.db import transaction as db_transaction
from celery import task
from distributedlock import distributedlock, MemcachedLock, LockNotAcquiredError
from django.core.cache import cache

from django.core.mail import mail_admins

def NonBlockingCacheLock(key, lock=None, blocking=False, timeout=10000):
    if lock is None:
        lock = MemcachedLock(key=key, client=cache, timeout=timeout)

    return distributedlock(key, lock, blocking)

@task()
def query_transactions():
    with NonBlockingCacheLock("query_transactions_ongoing"):
        blockcount = bitcoind.bitcoind_api.getblockcount()
        max_query_block = blockcount - settings.BITCOIN_MINIMUM_CONFIRMATIONS - 1
        if cache.get("queried_block_index"):
            query_block = min(int(cache.get("queried_block_index")), max_query_block)
        else:
            query_block = blockcount - 100
        blockhash = bitcoind.bitcoind_api.getblockhash(query_block)
        # print query_block, blockhash
        transactions = bitcoind.bitcoind_api.listsinceblock(blockhash)
        # print transactions
        transactions = [tx for tx in transactions["transactions"] if tx["category"]=="receive"]
        print transactions
        for tx in transactions:
            ba = BitcoinAddress.objects.filter(address=tx[u'address'])
            if ba.count() > 1:
                raise Exception(u"Too many addresses!")
            if ba.count() == 0:
                print "no address found, address", tx[u'address']
                continue
            ba = ba[0]
            dps = DepositTransaction.objects.filter(txid=tx[u'txid'], amount=tx['amount'], address=ba)
            if dps.count() > 1:
                raise Exception(u"Too many deposittransactions for the same ID!")
            elif dps.count() == 0:
                deposit_tx = DepositTransaction.objects.create(wallet=ba.wallet,
                    address=ba,
                    amount=tx['amount'],
                    txid=tx[u'txid'],
                    confirmations=int(tx['confirmations']))
                if deposit_tx.confirmations >= settings.BITCOIN_MINIMUM_CONFIRMATIONS:
                    ba.query_bitcoin_deposit(deposit_tx)
                else:
                    ba.query_unconfirmed_deposits()
            elif dps.count() == 1 and not dps[0].under_execution:
                deposit_tx = dps[0]
                if int(tx['confirmations']) >= settings.BITCOIN_MINIMUM_CONFIRMATIONS:
                    ba.query_bitcoin_deposit(deposit_tx)
                if int(tx['confirmations']) > deposit_tx.confirmations:
                    DepositTransaction.objects.filter(id=deposit_tx.id).update(confirmations=int(tx['confirmations']))
            elif dps.count() == 1:
                print "already processed", dps[0].txid, dps[0].transaction
            else:
                print "FUFFUFUU"

        cache.set("queried_block_index", max_query_block)

import sys
from cStringIO import StringIO

@task()
def check_integrity():
    from django_bitcoin.models import Wallet, BitcoinAddress, WalletTransaction, DepositTransaction
    from django_bitcoin.utils import bitcoind
    from django.db.models import Avg, Max, Min, Sum
    from decimal import Decimal

    import sys
    from cStringIO import StringIO
    backup = sys.stdout
    sys.stdout = StringIO()

    bitcoinaddress_sum = BitcoinAddress.objects.filter(active=True)\
        .aggregate(Sum('least_received_confirmed'))['least_received_confirmed__sum'] or Decimal(0)
    print "Total received, sum", bitcoinaddress_sum
    transaction_wallets_sum = WalletTransaction.objects.filter(from_wallet__id__gt=0, to_wallet__id__gt=0)\
        .aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    print "Total transactions, sum", transaction_wallets_sum
    transaction_out_sum = WalletTransaction.objects.filter(from_wallet__id__gt=0)\
        .exclude(to_bitcoinaddress="").exclude(to_bitcoinaddress="")\
        .aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    print "Total outgoing, sum", transaction_out_sum
    # for x in WalletTransaction.objects.filter(from_wallet__id__gt=0, to_wallet__isnull=True, to_bitcoinaddress=""):
    #   print x.amount, x.created_at
    fee_sum = WalletTransaction.objects.filter(from_wallet__id__gt=0, to_wallet__isnull=True, to_bitcoinaddress="")\
        .aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    print "Fees, sum", fee_sum
    print "DB balance", (bitcoinaddress_sum - transaction_out_sum - fee_sum)
    print "----"
    bitcoind_balance = bitcoind.bitcoind_api.getbalance()
    print "Bitcoind balance", bitcoind_balance
    print "----"
    print "Wallet quick check"
    total_sum = Decimal(0)
    for w in Wallet.objects.filter(last_balance__lt=0):
        if w.total_balance()<0:
            bal = w.total_balance()
            # print w.id, bal
            total_sum += bal
    print "Negatives:", Wallet.objects.filter(last_balance__lt=0).count(), "Amount:", total_sum
    print "Migration check"
    tot_received = WalletTransaction.objects.filter(from_wallet=None).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    tot_received_bitcoinaddress = BitcoinAddress.objects.filter(migrated_to_transactions=True)\
        .aggregate(Sum('least_received_confirmed'))['least_received_confirmed__sum'] or Decimal(0)
    tot_received_unmigrated = BitcoinAddress.objects.filter(migrated_to_transactions=False)\
        .aggregate(Sum('least_received_confirmed'))['least_received_confirmed__sum'] or Decimal(0)
    if tot_received != tot_received_bitcoinaddress:
        print "wrong total receive amount! "+str(tot_received)+", "+str(tot_received_bitcoinaddress)
    print "Total " + str(tot_received) + " BTC deposits migrated, unmigrated " + str(tot_received_unmigrated) + " BTC"
    print "Migration check #2"
    dts = DepositTransaction.objects.filter(address__migrated_to_transactions=False).exclude(transaction=None)
    if dts.count() > 0:
        print "Illegal transaction!", dts
    if WalletTransaction.objects.filter(from_wallet=None, deposit_address=None).count() > 0:
        print "Illegal deposit transactions!"
    print "Wallet check"
    for w in Wallet.objects.filter(last_balance__gt=0):
        lb = w.last_balance
        tb_sql = w.total_balance_sql()
        tb = w.total_balance()
        if lb != tb or w.last_balance != tb or tb != tb_sql:
            print "Wallet balance error!", w.id, lb, tb_sql, tb
            print w.sent_transactions.all().count()
            print w.received_transactions.all().count()
            print w.sent_transactions.all().aggregate(Max('created_at'))['created_at__max']
            print w.received_transactions.all().aggregate(Max('created_at'))['created_at__max']
            # Wallet.objects.filter(id=w.id).update(last_balance=w.total_balance_sql())
    # print w.created_at, w.sent_transactions.all(), w.received_transactions.all()
        # if random.random() < 0.001:
        #     sleep(1)
    print "Address check"
    for ba in BitcoinAddress.objects.filter(least_received_confirmed__gt=0, migrated_to_transactions=True):
        dts = DepositTransaction.objects.filter(address=ba, wallet=ba.wallet)
        s = dts.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        if s != ba.least_received:
            print "DepositTransaction error", ba.address, ba.least_received, s
            print "BitcoinAddress check"
    for ba in BitcoinAddress.objects.filter(migrated_to_transactions=True):
        dts = ba.deposittransaction_set.filter(address=ba, confirmations__gte=settings.BITCOIN_MINIMUM_CONFIRMATIONS)
        deposit_sum = dts.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        wt_sum = WalletTransaction.objects.filter(deposit_address=ba).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        if wt_sum != deposit_sum or ba.least_received_confirmed != deposit_sum:
            print "Bitcoinaddress integrity error!", ba.address, deposit_sum, wt_sum, ba.least_received_confirmed
        # if random.random() < 0.001:
        #     sleep(1)

    integrity_test_output = sys.stdout.getvalue() # release output
    # ####

    sys.stdout.close()  # close the stream
    sys.stdout = backup # restore original stdout
    mail_admins("Integrity check", integrity_test_output)

########NEW FILE########
__FILENAME__ = currency_conversions
from django import template
from django_bitcoin import currency

import json
from decimal import Decimal

import urllib

from django.core.urlresolvers import reverse,  NoReverseMatch

register = template.Library()

# currency conversion functions

@register.filter
def bitcoinformat(value):
    # print "bitcoinformat", value
    if value == None:
        return None
    if not (isinstance(value, float) or isinstance(value, Decimal)):
        return str(value).rstrip('0').rstrip('.')
    return ("%.8f" % value).rstrip('0').rstrip('.')

@register.filter
def currencyformat(value):
    if value == None:
        return None
    if not (isinstance(value, float) or isinstance(value, Decimal)):
        return str(value).rstrip('0').rstrip('.')
    return ("%.2f" % value)

@register.filter
def btc2usd(value):
    return (Decimal(value)*currency.exchange.get_rate('USD')).quantize(Decimal("0.01"))

@register.filter
def usd2btc(value):
    return (Decimal(value)/currency.exchange.get_rate('USD')).quantize(Decimal("0.00000001"))

@register.filter
def btc2eur(value):
    return (Decimal(value)*currency.exchange.get_rate('EUR')).quantize(Decimal("0.01"))

@register.filter
def eur2btc(value):
    return (Decimal(value)/currency.exchange.get_rate('EUR')).quantize(Decimal("0.00000001"))

@register.filter
def btc2currency(value, other_currency="USD", rate_period="24h"):
    if other_currency=="BTC":
        return bitcoinformat(value)
    return currencyformat(currency.btc2currency(value, other_currency, rate_period))

@register.filter
def currency2btc(value, other_currency="USD", rate_period="24h"):
    if other_currency=="BTC":
        return currencyformat(value)
    return bitcoinformat(currency.currency2btc(value, other_currency, rate_period))

@register.simple_tag
def exchangerates_json():
    return json.dumps(currency.get_rate_table())


@register.inclusion_tag('wallet_history.html')
def wallet_history(wallet):
    return {'wallet': wallet}


@register.filter
def show_addr(address, arg):
    '''
    Display a bitcoin address with plus the link to its blockexplorer page.
    '''
    # note: i disapprove including somewhat unnecessary depencies such as this, especially since blockexplorer is  unreliable service
    link ="<a href='http://blockexplorer.com/%s/'>%s</a>"
    if arg == 'long':
        return link % (address, address)
    else:
        return link % (address, address[:8])


@register.inclusion_tag('wallet_tagline.html')
def wallet_tagline(wallet):
    return {'wallet': wallet, 'balance_usd': btc2usd(wallet.total_balance())}


@register.inclusion_tag('bitcoin_payment_qr.html')
def bitcoin_payment_qr(address, amount=Decimal("0"), description='', display_currency=''):
    currency_amount=Decimal(0)
    if display_currency:
        currency_amount=(Decimal(amount)*currency.exchange.get_rate(display_currency)).quantize(Decimal("0.01"))
    try:
        image_url = reverse('qrcode', args=('dummy',))
    except NoReverseMatch,e:
        raise ImproperlyConfigured('Make sure you\'ve included django_bitcoin.urls')
    qr = "bitcoin:"+address+("", "?amount="+str(amount))[amount>0]
    qr = urllib.quote(qr)
    address_qrcode = reverse('qrcode', args=(qr,))
    return {'address': address, 
            'address_qrcode': address_qrcode,
            'amount': amount, 
            'description': description, 
            'display_currency': display_currency,
            'currency_amount': currency_amount,
            }

########NEW FILE########
__FILENAME__ = listinceblock_testing

python manage.py shell_plus
from django_bitcoin.tasks import query_transactions
query_transactions()
for d in DepositTransaction.objects.all().order_by("-id")[:10]:
    print d.created_at, d.amount, d.transaction, d.under_execution

quit()



python manage.py shell_plus
from django_bitcoin.tasks import check_integrity
check_integrity()
quit()

python manage.py shell_plus
from django_bitcoin.models import update_wallet_balance
for w in Wallet.objects.filter(last_balance__gt=0):
    lb = w.last_balance
    tb_sql = w.total_balance_sql()
    tb = w.total_balance()
    if lb != tb_sql:
        print "error", w.id, lb, tb_sql
        update_wallet_balance.delay(w.id)

python manage.py shell_plus
from django_bitcoin.tasks import process_outgoing_group
process_outgoing_group()
quit()


for ot in OutgoingTransaction.objects.filter(under_execution=True):
    print ot.to_bitcoinaddress, ot.amount, ot.txid

for ot in OutgoingTransaction.objects.filter(txid=None).exclude(executed_at=None):
    print ot.executed_at, ot.to_bitcoinaddress, ot.amount, ot.txid


from decimal import Decimal
from django.db.models import Avg, Max, Min, Sum
for ba in BitcoinAddress.objects.filter(least_received_confirmed__gt=0, migrated_to_transactions=True):
    dts = DepositTransaction.objects.filter(address=ba, wallet=ba.wallet)
    s = dts.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    wt_sum = WalletTransaction.objects.filter(deposit_address=ba).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    if s != ba.least_received:
        print "DepositTransaction error", ba.address, ba.least_received, s
        print "BitcoinAddress check"
        for d in dts:
            print "d", d.address, d.amount, d.created_at, d.transaction, d.txid
            if not d.transaction and s > ba.least_received:
                print "DELETED"
                d.delete()
        for wt in ba.wallettransaction_set.all():
            print "wt", wt.deposit_address, wt.amount, wt.created_at, wt.deposittransaction_set.all()
        if s < ba.least_received:
            # deposit_tx = DepositTransaction.objects.create(wallet=ba.wallet,
            #         address=ba,
            #         amount=ba.least_received - s,
            #         txid="fix_manual",
            #         confirmations=9999)
            print "ADDED"

quit()

from django_bitcoin.models import process_outgoing_transactions

ots = OutgoingTransaction.objects.filter(txid=None).exclude(executed_at=None).order_by("id")[:2]
for ot in ots:
    print ot.executed_at, ot.to_bitcoinaddress, ot.amount, ot.txid
    print OutgoingTransaction.objects.filter(id=ot.id).update(executed_at=None)

process_outgoing_transactions()

import datetime
import pytz
next_run_at = OutgoingTransaction.objects.all().aggregate(Min('expires_at'))['expires_at__min']
countdown=max(((next_run_at - datetime.datetime.now(pytz.utc)) + datetime.timedelta(seconds=5)).total_seconds(), 5)
if next_run_at:
    process_outgoing_transactions.retry(
        countdown=min(((next_run_at - datetime.datetime.now()) + datetime.timedelta(seconds=5)).total_seconds(), 0) )

python manage.py shell_plus
import datetime
from decimal import Decimal
from django.db.models import Avg, Max, Min, Sum
BitcoinAddress.objects.aggregate(Sum('least_received'))['least_received__sum'] or Decimal(0)
BitcoinAddress.objects.aggregate(Sum('least_received_confirmed'))['least_received_confirmed__sum'] or Decimal(0)
bas = BitcoinAddress.objects.extra(where=["least_received>least_received_confirmed",])
for ba in bas:
    print ba.address, ba.least_received, ba.least_received_confirmed, ba.wallet.total_balance_sql(), ba.wallet.total_balance_sql(confirmed=False)
    print ba.wallet.total_balance(), ba.wallet.total_balance_unconfirmed()


python manage.py shell_plus
from decimal import Decimal
from django.db.models import Avg, Max, Min, Sum
for w in Wallet.objects.all():
    if w.total_balance()>0 or w.total_balance(0)>0 or w.total_balance_sql(confirmed=False)>0:
        print w.id, w.total_balance(), w.total_balance_sql()
        print w.id, w.total_balance(0), w.total_balance_sql(confirmed=False), w.total_balance_sql(confirmed=False)

from decimal import Decimal
from django.db.models import Avg, Max, Min, Sum
for ba in BitcoinAddress.objects.filter(migrated_to_transactions=True):
        dts = ba.deposittransaction_set.filter(address=ba, confirmations__gte=settings.BITCOIN_MINIMUM_CONFIRMATIONS)
        deposit_sum = dts.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        wt_sum = WalletTransaction.objects.filter(deposit_address=ba).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        if wt_sum != deposit_sum or ba.least_received_confirmed != deposit_sum:
            print "Bitcoinaddress integrity error!", ba.address, deposit_sum, wt_sum, ba.least_received_confirmed

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
__FILENAME__ = test_zero_confirmation
from django.core.management import setup_environ
import settings
setup_environ(settings)

# Tests only with internal transf
from decimal import Decimal
import unittest
from django_bitcoin import Wallet


class InternalChangesTest(unittest.TestCase):
    def setUp(self):
        self.origin = Wallet.objects.all()[0]

        self.w1 = Wallet.objects.create()
        self.w2 = Wallet.objects.create()
        self.w3 = Wallet.objects.create()
        self.w4 = Wallet.objects.create()
        self.w5 = Wallet.objects.create()
        self.w6 = Wallet.objects.create()
        self.w7 = Wallet.objects.create()

    def testTransactions(self):
        # t1
        self.origin.send_to_wallet(self.w1, Decimal('5'))
        self.assertEquals(self.w1.balance(), (Decimal('0'), Decimal('5')))

        # t2
        self.w1.send_to_wallet(self.w2, Decimal('1'))
        self.assertEquals(self.w1.balance(), (Decimal('0'), Decimal('4')))
        self.assertEquals(self.w2.balance(), (Decimal('0'), Decimal('1')))

        # t3
        self.w1.send_to_wallet(self.w3, Decimal('2'))
        self.assertEquals(self.w1.balance(), (Decimal('0'), Decimal('2')))
        self.assertEquals(self.w3.balance(), (Decimal('0'), Decimal('2')))

        # t1'
        raw_input('Transfer 2 bitcoins to wallet %s' %
                self.w1.static_receiving_address())

        # t4
        self.w1.send_to_wallet(self.w4, Decimal('4'))
        self.assertEquals(self.w1.balance(), (Decimal('0'), Decimal('0')))
        self.assertEquals(self.w4.balance(), (Decimal('2'), Decimal('2')))

        # t2'
        raw_input('Transfer 2 bitcoins to wallet %s' %
                self.w3.static_receiving_address())

        # t5
        self.w3.send_to_wallet(self.w4, Decimal('4'))
        self.assertEquals(self.w3.balance(), (Decimal('0'), Decimal('0')))
        self.assertEquals(self.w4.balance(), (Decimal('4'), Decimal('4')))

        # t3'
        raw_input('Transfer 2 bitcoins to wallet %s' %
                self.w4.static_receiving_address())

        # t6
        self.w4.send_to_wallet(self.w1, Decimal('10'))
        self.assertEquals(self.w1.balance(), (Decimal('6'), Decimal('4')))
        self.assertEquals(self.w4.balance(), (Decimal('0'), Decimal('0')))

        # t7
        self.w1.send_to_wallet(self.w5, Decimal('6'))
        self.assertEquals(self.w1.balance(), (Decimal('4'), Decimal('0')))
        self.assertEquals(self.w5.balance(), (Decimal('2'), Decimal('4')))

        # t4'
        raw_input('Transfer 2 bitcoins to wallet %s' %
                self.w5.static_receiving_address())

        # t8
        self.w5.send_to_wallet(self.w6, Decimal('8'))
        self.assertEquals(self.w5.balance(), (Decimal('0'), Decimal('0')))
        self.assertEquals(self.w6.balance(), (Decimal('4'), Decimal('4')))

        # t9
        self.w6.send_to_wallet(self.w7, Decimal('4'))
        self.assertEquals(self.w6.balance(), (Decimal('4'), Decimal('0')))
        self.assertEquals(self.w7.balance(), (Decimal('0'), Decimal('4')))

        # t5'
        raw_input('Transfer 2 bitcoins to wallet %s' %
                self.w7.static_receiving_address())

        # t10
        self.w7.send_to_wallet(self.w5, Decimal('6'))
        self.assertEquals(self.w5.balance(), (Decimal('2'), Decimal('4')))
        self.assertEquals(self.w7.balance(), (Decimal('0'), Decimal('0')))

        # t11
        self.w6.send_to_wallet(self.w5, Decimal('2'))
        self.assertEquals(self.w5.balance(), (Decimal('4'), Decimal('4')))
        self.assertEquals(self.w6.balance(), (Decimal('2'), Decimal('0')))

        self.clear()

    def clear(self):
        self.w1.delete()
        self.w2.delete()
        self.w3.delete()
        self.w4.delete()
        self.w5.delete()
        self.w6.delete()
        self.w7.delete()

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('django_bitcoin.views',
    url(r'^qrcode/(?P<key>.+)$','qrcode_view',name='qrcode'),
)

########NEW FILE########
__FILENAME__ = utils
# vim: tabstop=4 expandtab autoindent shiftwidth=4 fileencoding=utf-8

import os
import json
import jsonrpc
import sys
import urllib
import urllib2
import random
import hashlib
import base64
from decimal import Decimal
import decimal
import warnings

from django.core.cache import cache
from django.db import transaction

from django_bitcoin import settings
from django_bitcoin import currency

from pywallet import privkey2address

# BITCOIND COMMANDS


def quantitize_bitcoin(d):
    return d.quantize(Decimal("0.00000001"))


def decimal_float(d):
    return float(d.quantize(Decimal("0.00000001")))


class BitcoindConnection(object):
    def __init__(self, connection_string, main_account_name):
        self.bitcoind_api = jsonrpc.ServiceProxy(connection_string)
        self.account_name = main_account_name

    def total_received(self, address, minconf=settings.BITCOIN_MINIMUM_CONFIRMATIONS):
        if settings.BITCOIN_TRANSACTION_CACHING:
            cache_key=address+"_"+str(minconf)
            cached = cache.get(cache_key)
            if cached!=None:
                return cached
            cached=decimal.Decimal(
                self.bitcoind_api.getreceivedbyaddress(address, minconf))
            cache.set(cache_key, cached, 5)
            return cached
        return decimal.Decimal(
                self.bitcoind_api.getreceivedbyaddress(address, minconf))

    def send(self, address, amount, *args, **kwargs):
        #print "sending", address, amount
        return self.bitcoind_api.sendtoaddress(address, float(amount), *args, **kwargs)

    def sendmany(self, address_amount_dict, *args, **kwargs):
        #print "sending", address, amount
        return self.bitcoind_api.sendmany(self.account_name, address_amount_dict, *args, **kwargs)

    def create_address(self, for_account=None, *args, **kwargs):
        return self.bitcoind_api.getnewaddress(
            for_account or self.account_name, *args, **kwargs)

    def gettransaction(self, txid, *args, **kwargs):
        # dir (self.bitcoind_api)
        return self.bitcoind_api.gettransaction(txid, *args, **kwargs)

    # if address_to is defined, also empties the private key to that address
    def importprivatekey(self, key):
        # import private key functionality here later
        # NOTE: only
        label = "import"
        address_from = privkey2address(key)
        if not address_from or not address_from.startswith("1"):
            print address_from
            return None
        # print address_from
        try:
            self.bitcoind_api.importprivkey(key, label)
        except jsonrpc.JSONRPCException:
            pass
        unspent_transactions = self.bitcoind_api.listunspent(1, 9999999, [address_from])
        return (address_from, quantitize_bitcoin(Decimal(sum([Decimal(x['amount']) for x in unspent_transactions]))))

    def redeemprivatekey(self, key, address_from, address_to):
        if type(address_to) == str or type(address_to) == unicode:
            address_to = ((address_to, None),)
        if address_from != privkey2address(key):
            return None
        unspent_transactions = self.bitcoind_api.listunspent(1, 9999999, [address_from])
        tot_amount = sum([Decimal(x['amount']) for x in unspent_transactions])
        tot_fee = len(unspent_transactions) * settings.BITCOIN_PRIVKEY_FEE
        tot_spend = tot_fee
        if tot_amount > tot_spend:
            final_arr = {}
            for addr in address_to:
                if addr[1] and addr[1]<0:
                    raise Exception("No negative spend values allowed")
                if addr[1] and tot_amount > addr[1] + tot_spend:
                    final_arr[addr[0]] = decimal_float(addr[1])
                    tot_spend += addr[1]
                elif not addr[1] and tot_amount > tot_spend:
                    final_arr[addr[0]] = decimal_float((tot_amount - tot_spend))
                    break
                else:
                    return None  # raise Exception("Invalid amount parameters")
            # print final_arr
            # print unspent_transactions
            spend_transactions = [{"txid": ut['txid'], "vout": ut['vout']} for ut in unspent_transactions]
            spend_transactions_sign = [{"txid": ut['txid'], "vout": ut['vout'], "scriptPubKey": ut['scriptPubKey']} for ut in unspent_transactions]
            raw_transaction = self.bitcoind_api.createrawtransaction(spend_transactions, final_arr)
            raw_transaction_signed = self.bitcoind_api.signrawtransaction(raw_transaction, spend_transactions_sign, [key])
            # print raw_transaction, raw_transaction_signed
            return self.bitcoind_api.sendrawtransaction(raw_transaction_signed['hex'])
        else:
            return None

        # return self.bitcoind_api.gettransaction(txid, *args, **kwargs)

bitcoind = BitcoindConnection(settings.BITCOIND_CONNECTION_STRING,
                              settings.MAIN_ACCOUNT)

def bitcoin_getnewaddress(account_name=None):
    warnings.warn("Use bitcoind.create_address(...) instead",
                  DeprecationWarning)
    return bitcoind.create_address(account_name=account_name)

def bitcoin_getbalance(address, minconf=1):
    warnings.warn("Use bitcoind.total_received(...) instead",
                  DeprecationWarning)
    return bitcoind.total_received(address, minconf)

def bitcoin_getreceived(address, minconf=settings.BITCOIN_MINIMUM_CONFIRMATIONS):
    warnings.warn("Use bitcoind.total_received(...) instead",
                  DeprecationWarning)
    return bitcoind.total_received(address, minconf)

def bitcoin_sendtoaddress(address, amount):
    warnings.warn("Use bitcoind.send(...) instead",
                  DeprecationWarning)
    return bitcoind.send(address, amount)

# --------

def bitcoinprice_usd():
    """return bitcoin price from any service we can get it"""
    warnings.warn("Use django_bitcoin.currency.exchange.get_rate('USD')",
                  DeprecationWarning)
    return {"24h": currency.exchange.get_rate("USD")}

def bitcoinprice_eur():
    warnings.warn("Use django_bitcoin.currency.exchange.get_rate('EUR')",
                  DeprecationWarning)
    return {"24h": currency.exchange.get_rate("EUR")}

def bitcoinprice(currency):
    warnings.warn("Use django_bitcoin.currency.exchange.get_rate(currency)",
                  DeprecationWarning)
    return currency.exchange.get_rate(currency)

# ------

# generate a random hash
def generateuniquehash(length=43, extradata=''):
    # cryptographically safe random
    r=str(os.urandom(64))
    m = hashlib.sha256()
    m.update(r+str(extradata))
    key=m.digest()
    key=base64.urlsafe_b64encode(key)
    return key[:min(length, 43)]

import string

ALPHABET = string.ascii_uppercase + string.ascii_lowercase + \
           string.digits + '_-'
ALPHABET_REVERSE = dict((c, i) for (i, c) in enumerate(ALPHABET))
BASE = len(ALPHABET)
SIGN_CHARACTER = '%'

def int2base64(n):
    if n < 0:
        return SIGN_CHARACTER + num_encode(-n)
    s = []
    while True:
        n, r = divmod(n, BASE)
        s.append(ALPHABET[r])
        if n == 0: break
    return ''.join(reversed(s))

def base642int(s):
    if s[0] == SIGN_CHARACTER:
        return -num_decode(s[1:])
    n = 0
    for c in s:
        n = n * BASE + ALPHABET_REVERSE[c]
    return n

########NEW FILE########
__FILENAME__ = views
# Create your views here.
from django.http import HttpResponseRedirect, HttpResponse
from django.core.cache import cache
import qrcode
import StringIO

def qrcode_view(request, key):
    cache_key="qrcode:"+key
    c=cache.get(cache_key)
    if not c:
        img = qrcode.make(key, box_size=4)
        output = StringIO.StringIO()
        img.save(output, "PNG")
        c = output.getvalue()
        cache.set(cache_key, c, 60*60)
    return HttpResponse(c, mimetype="image/png")

########NEW FILE########
