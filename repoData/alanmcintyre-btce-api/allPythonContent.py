__FILENAME__ = common
# Copyright (c) 2013 Alan McIntyre

import httplib
import json
import decimal
import re

class InvalidTradePairException(Exception):
    ''' Exception raised when an invalid pair is passed. '''
    pass

class InvalidTradeTypeException(Exception):
    ''' Exception raise when invalid trade type is passed. '''
    pass

class InvalidTradeAmountException(Exception):
    ''' Exception raised if trade amount is too much or too little. '''
    pass

decimal.getcontext().rounding = decimal.ROUND_DOWN
exps = [decimal.Decimal("1e-%d" % i) for i in range(16)]

btce_domain = "btc-e.com"

all_currencies = ("btc", "usd", "rur", "ltc", "nmc", "eur", "nvc",
                  "trc", "ppc", "ftc", "xpm")
all_pairs = ("btc_usd", "btc_rur", "btc_eur", "ltc_btc", "ltc_usd",
             "ltc_rur", "ltc_eur", "nmc_btc", "nmc_usd", "nvc_btc",
             "nvc_usd", "usd_rur", "eur_usd", "eur_rur", "trc_btc",
             "ppc_btc", "ppc_usd", "ftc_btc", "xpm_btc")

max_digits = {"btc_usd": 3,
              "btc_rur": 5,
              "btc_eur": 5,
              "ltc_btc": 5,
              "ltc_usd": 6,
              "ltc_rur": 5,
              "ltc_eur": 3,
              "nmc_btc": 5,
              "nmc_usd": 3,
              "nvc_btc": 5,
              "nvc_usd": 3,
              "usd_rur": 5,
              "eur_usd": 5,
              "eur_rur": 5,
              "trc_btc": 5,
              "ppc_btc": 5,
              "ppc_usd": 3,
              "ftc_btc": 5,
              "xpm_btc": 5}

min_orders = {"btc_usd": decimal.Decimal("0.01"),
              "btc_rur": decimal.Decimal("0.01"),
              "btc_eur": decimal.Decimal("0.01"),
              "ltc_btc": decimal.Decimal("0.1"),
              "ltc_usd": decimal.Decimal("0.1"),
              "ltc_rur": decimal.Decimal("0.1"),
              "ltc_eur": decimal.Decimal("0.1"),
              "nmc_btc": decimal.Decimal("0.1"),
              "nmc_usd": decimal.Decimal("0.1"),
              "nvc_btc": decimal.Decimal("0.1"),
              "nvc_usd": decimal.Decimal("0.1"),
              "usd_rur": decimal.Decimal("0.1"),
              "eur_usd": decimal.Decimal("0.1"),
              "eur_rur": decimal.Decimal("0.1"),
              "trc_btc": decimal.Decimal("0.1"),
              "ppc_btc": decimal.Decimal("0.1"),
              "ppc_usd": decimal.Decimal("0.1"),
              "ftc_btc": decimal.Decimal("0.1"),
              "xpm_btc": decimal.Decimal("0.1")}


def parseJSONResponse(response):
    def parse_decimal(var):
        return decimal.Decimal(var)

    try:
        r = json.loads(response, parse_float=parse_decimal,
                       parse_int=parse_decimal)
    except Exception as e:
        msg = "Error while attempting to parse JSON response:"\
              " %s\nResponse:\n%r" % (e, response)
        raise Exception(msg)

    return r

HEADER_COOKIE_RE = re.compile(r'__cfduid=([a-f0-9]{46})')
BODY_COOKIE_RE = re.compile(r'document\.cookie="a=([a-f0-9]{32});path=/;";')

class BTCEConnection:
    def __init__(self, timeout=30):
        self.conn = httplib.HTTPSConnection(btce_domain, timeout=timeout)
        self.cookie = None

    def close(self):
        self.conn.close()

    def getCookie(self):
        self.cookie = ""

        self.conn.request("GET", '/')
        response = self.conn.getresponse()

        setCookieHeader = response.getheader("Set-Cookie")
        match = HEADER_COOKIE_RE.search(setCookieHeader)
        if match:
            self.cookie = "__cfduid=" + match.group(1)

        match = BODY_COOKIE_RE.search(response.read())
        if match:
            if self.cookie != "":
                self.cookie += '; '
            self.cookie += "a=" + match.group(1)

    def makeRequest(self, url, extra_headers=None, params="", with_cookie=False):
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        if extra_headers is not None:
            headers.update(extra_headers)

        if with_cookie:
            if self.cookie is None:
                self.getCookie()

            headers.update({"Cookie": self.cookie})

        self.conn.request("POST", url, params, headers)
        response = self.conn.getresponse().read()

        return response

    def makeJSONRequest(self, url, extra_headers=None, params=""):
        response = self.makeRequest(url, extra_headers, params)
        return parseJSONResponse(response)


def validatePair(pair):
    if pair not in all_pairs:
        if "_" in pair:
            a, b = pair.split("_", 1)
            swapped_pair = "%s_%s" % (b, a)
            if swapped_pair in all_pairs:
                msg = "Unrecognized pair: %r (did you mean %s?)"
                msg = msg % (pair, swapped_pair)
                raise InvalidTradePairException(msg)
        raise InvalidTradePairException("Unrecognized pair: %r" % pair)


def validateOrder(pair, trade_type, rate, amount):
    validatePair(pair)
    if trade_type not in ("buy", "sell"):
        raise InvalidTradeTypeException("Unrecognized trade type: %r" % trade_type)

    minimum_amount = min_orders[pair]
    formatted_min_amount = formatCurrency(minimum_amount, pair)
    if amount < minimum_amount:
        msg = "Trade amount too small; should be >= %s" % formatted_min_amount
        raise InvalidTradeAmountException(msg)


def truncateAmountDigits(value, digits):
    quantum = exps[digits]
    if type(value) is float:
        value = str(value)
    if type(value) is str:
        value = decimal.Decimal(value)
    return value.quantize(quantum)


def truncateAmount(value, pair):
    return truncateAmountDigits(value, max_digits[pair])


def formatCurrencyDigits(value, digits):
    s = str(truncateAmountDigits(value, digits))
    dot = s.index(".")
    while s[-1] == "0" and len(s) > dot + 2:
        s = s[:-1]

    return s


def formatCurrency(value, pair):
    return formatCurrencyDigits(value, max_digits[pair])

########NEW FILE########
__FILENAME__ = keyhandler
# Copyright (c) 2013 Alan McIntyre

import warnings


class KeyData(object):
    def __init__(self, secret, nonce):
        self.secret = secret
        self.nonce = nonce


class KeyHandler(object):
    '''KeyHandler handles the tedious task of managing nonces associated
    with a BTC-e API key/secret pair.
    The getNextNonce method is threadsafe, all others are not.'''
    def __init__(self, filename=None, resaveOnDeletion=True):
        '''The given file is assumed to be a text file with three lines
        (key, secret, nonce) per entry.'''
        if not resaveOnDeletion:
            warnings.warn("The resaveOnDeletion argument to KeyHandler will"
                          " default to True in future versions.")
        self._keys = {}
        self.resaveOnDeletion = False
        self.filename = filename
        if filename is not None:
            self.resaveOnDeletion = resaveOnDeletion
            f = open(filename, "rt")
            while True:
                key = f.readline().strip()
                if not key:
                    break
                secret = f.readline().strip()
                nonce = int(f.readline().strip())
                self.addKey(key, secret, nonce)

    def __del__(self):
        self.close()

    def close(self):
        if self.resaveOnDeletion:
            self.save(self.filename)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def keys(self):
        return self._keys.keys()

    def getKeys(self):
        return self._keys.keys()

    def save(self, filename):
        f = open(filename, "wt")
        for k, data in self._keys.items():
            f.write("%s\n%s\n%d\n" % (k, data.secret, data.nonce))

    def addKey(self, key, secret, next_nonce):
        self._keys[key] = KeyData(secret, next_nonce)

    def getNextNonce(self, key):
        data = self._keys.get(key)
        if data is None:
            raise KeyError("Key not found: %r" % key)

        nonce = data.nonce
        data.nonce += 1

        return nonce

    def getSecret(self, key):
        data = self._keys.get(key)
        if data is None:
            raise KeyError("Key not found: %r" % key)

        return data.secret

    def setNextNonce(self, key, next_nonce):
        data = self._keys.get(key)
        if data is None:
            raise KeyError("Key not found: %r" % key)
        data.nonce = next_nonce

########NEW FILE########
__FILENAME__ = public
# Copyright (c) 2013 Alan McIntyre

import datetime
import decimal

from btceapi import common


def getTradeFee(pair, connection=None):
    '''
    Retrieve the fee (in percent) associated with trades for a given pair.
    '''

    common.validatePair(pair)

    if connection is None:
        connection = common.BTCEConnection()

    fees = connection.makeJSONRequest("/api/2/%s/fee" % pair)
    if type(fees) is not dict:
        raise TypeError("The response is not a dict.")

    trade_fee = fees.get(u'trade')
    if type(trade_fee) is not decimal.Decimal:
        raise TypeError("The response does not contain a trade fee")

    return trade_fee


class Ticker(object):
    __slots__ = ('high', 'low', 'avg', 'vol', 'vol_cur', 'last', 'buy', 'sell',
                 'updated', 'server_time')

    def __init__(self, **kwargs):
        for s in Ticker.__slots__:
            setattr(self, s, kwargs.get(s))

        self.updated = datetime.datetime.fromtimestamp(self.updated)
        self.server_time = datetime.datetime.fromtimestamp(self.server_time)

    def __getstate__(self):
        return dict((k, getattr(self, k)) for k in Ticker.__slots__)

    def __setstate__(self, state):
        for k, v in state.items():
            setattr(self, k, v)


def getTicker(pair, connection=None):
    '''Retrieve the ticker for the given pair.  Returns a Ticker instance.'''

    common.validatePair(pair)

    if connection is None:
        connection = common.BTCEConnection()

    response = connection.makeJSONRequest("/api/2/%s/ticker" % pair)

    if type(response) is not dict:
        raise TypeError("The response is a %r, not a dict." % type(response))

    return Ticker(**response[u'ticker'])


def getDepth(pair, connection=None):
    '''Retrieve the depth for the given pair.  Returns a tuple (asks, bids);
    each of these is a list of (price, volume) tuples.'''

    common.validatePair(pair)

    if connection is None:
        connection = common.BTCEConnection()

    depth = connection.makeJSONRequest("/api/2/%s/depth" % pair)
    if type(depth) is not dict:
        raise TypeError("The response is not a dict.")

    asks = depth.get(u'asks')
    if type(asks) is not list:
        raise TypeError("The response does not contain an asks list.")

    bids = depth.get(u'bids')
    if type(bids) is not list:
        raise TypeError("The response does not contain a bids list.")

    return asks, bids


class Trade(object):
    __slots__ = ('pair', 'trade_type', 'price', 'tid', 'amount', 'date')

    def __init__(self, **kwargs):
        for s in Trade.__slots__:
            setattr(self, s, kwargs.get(s))

        if type(self.date) in (int, float, decimal.Decimal):
            self.date = datetime.datetime.fromtimestamp(self.date)
        elif type(self.date) in (str, unicode):
            if "." in self.date:
                self.date = datetime.datetime.strptime(self.date,
                                                       "%Y-%m-%d %H:%M:%S.%f")
            else:
                self.date = datetime.datetime.strptime(self.date,
                                                       "%Y-%m-%d %H:%M:%S")

    def __getstate__(self):
        return dict((k, getattr(self, k)) for k in Trade.__slots__)

    def __setstate__(self, state):
        for k, v in state.items():
            setattr(self, k, v)


def getTradeHistory(pair, connection=None, count=None):
    '''Retrieve the trade history for the given pair.  Returns a list of
    Trade instances.  If count is not None, it should be an integer, and
    specifies the number of items from the trade history that will be
    processed and returned.'''

    common.validatePair(pair)

    if connection is None:
        connection = common.BTCEConnection()

    history = connection.makeJSONRequest("/api/2/%s/trades" % pair)

    if type(history) is not list:
        raise TypeError("The response is a %r, not a list." % type(history))

    result = []

    # Limit the number of items returned if requested.
    if count is not None:
        history = history[:count]

    for h in history:
        h["pair"] = pair
        t = Trade(**h)
        result.append(t)
    return result

########NEW FILE########
__FILENAME__ = scraping
# Copyright (c) 2013 Alan McIntyre

from HTMLParser import HTMLParser
import datetime
import warnings
from btceapi.common import BTCEConnection, all_pairs


class BTCEScraper(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.messageId = None
        self.messageTime = None
        self.messageUser = None
        self.messageText = None
        self.messages = []
        self.reserves24change = None
        self.reservesALFAcashier = None
        self.usersOnline = None
        self.botsOnline = None

        self.inMessageA = False
        self.inMessageSpan = False
        self.in24changeSpan = False
        self.inALFAcashierSpan = False
        self.inUsersOnlineDiv = False

        self.devOnline = False
        self.supportOnline = False
        self.adminOnline = False

    def handle_data(self, data):
        # Capture contents of <a> and <span> tags, which contain
        # the user ID and the message text, respectively.
        if self.inMessageA:
            self.messageUser = data.strip()
        elif self.inMessageSpan:
            self.messageText = data.strip()
        elif self.in24changeSpan:
            self.reserves24change = int(data)
        elif self.inALFAcashierSpan:
            self.reservesALFAcashier = int(data)
        elif self.inUsersOnlineDiv:
            utext, ucount, bottext, botcount = data.split()
            self.usersOnline = int(ucount)
            self.botsOnline = int(botcount)
            self.inUsersOnlineDiv = False

    def handle_starttag(self, tag, attrs):
        if tag == 'p':
            # Check whether this <p> tag has id="msgXXXXXX" and
            # class="chatmessage"; if not, it doesn't contain a message.
            messageId = None
            for k, v in attrs:
                if k == 'id':
                    if v[:3] != 'msg':
                        return
                    messageId = v
                if k == 'class' and v != 'chatmessage':
                    return

            # This appears to be a message <p> tag, so set the message ID.
            # Other code in this class assumes that if self.messageId is None,
            # the tags being processed are not relevant.
            if messageId is not None:
                self.messageId = messageId
        elif tag == 'a':
            if self.messageId is not None:
                # Check whether this <a> tag has class="chatmessage" and a
                # time string in the title attribute; if not, it's not part
                # of a message.
                messageTime = None
                for k, v in attrs:
                    if k == 'title':
                        messageTime = v
                    if k == 'class' and v != 'chatmessage':
                        return

                if messageTime is None:
                    return

                # This appears to be a message <a> tag, so remember the message
                # time and set the inMessageA flag so the tag's data can be
                # captured in the handle_data method.
                self.inMessageA = True
                self.messageTime = messageTime
            else:
                for k, v in attrs:
                    if k != 'href':
                        continue

                    # If the <a> tag for dev/support/admin is present, then
                    # they are online (otherwise nothing appears on the
                    # page for them).
                    if v == 'https://btc-e.com/profile/1':
                        self.devOnline = True
                    elif v == 'https://btc-e.com/profile/2':
                        self.supportOnline = True
                    elif v == 'https://btc-e.com/profile/3':
                        self.adminOnline = True
        elif tag == 'span':
            if self.messageId is not None:
                self.inMessageSpan = True
            else:
                for k, v in attrs:
                    if k == 'id':
                        if v == '_24CH_reserve':
                            self.in24changeSpan = True
                            return
                        elif v == 'ALFA_reserve':
                            self.inALFAcashierSpan = True
                            return
        elif tag == 'div':
            for k, v in attrs:
                if k == 'id' and v == "users-online":
                    self.inUsersOnlineDiv = True

    def handle_endtag(self, tag):
        if tag == 'p' and self.messageId is not None:
            # exiting from the message <p> tag

            # check for invalid message contents
            if self.messageId is None:
                warnings.warn("Missing message ID")
            if self.messageUser is None:
                warnings.warn("Missing message user")
            if self.messageTime is None:
                warnings.warn("Missing message time")

            if self.messageText is None:
                # messageText will be None if the message consists entirely
                # of emoticons.
                self.messageText = ''

            # parse message time
            t = datetime.datetime.now()
            messageTime = t.strptime(self.messageTime, '%d.%m.%y %H:%M:%S')

            self.messages.append((self.messageId, self.messageUser,
                                  messageTime, self.messageText))
            self.messageId = None
            self.messageUser = None
            self.messageTime = None
            self.messageText = None
        elif tag == 'a' and self.messageId is not None:
            self.inMessageA = False
        elif tag == 'span':
            self.inMessageSpan = False
            self.in24changeSpan = False
            self.inALFAcashierSpan = False


class ScraperResults(object):
    __slots__ = ('messages', 'reserves24change', 'reservesALFAcashier',
                 'usersOnline', 'botsOnline', 'devOnline', 'supportOnline',
                 'adminOnline')

    def __init__(self):
        self.messages = None
        self.reserves24change = None
        self.reservesALFAcashier = None
        self.usersOnline = None
        self.botsOnline = None
        self.devOnline = False
        self.supportOnline = False
        self.adminOnline = False

    def __getstate__(self):
        return dict((k, getattr(self, k)) for k in ScraperResults.__slots__)

    def __setstate__(self, state):
        for k, v in state.items():
            setattr(self, k, v)


_current_pair_index = 0


def scrapeMainPage(connection=None):
    if connection is None:
        connection = BTCEConnection()

    parser = BTCEScraper()

    # Rotate through the currency pairs between chat requests so that the
    # chat pane contents will update more often than every few minutes.
    global _current_pair_index
    _current_pair_index = (_current_pair_index + 1) % len(all_pairs)
    current_pair = all_pairs[_current_pair_index]

    response = connection.makeRequest('/exchange/%s' % current_pair,
                                      with_cookie=True)

    parser.feed(parser.unescape(response.decode('utf-8')))
    parser.close()

    r = ScraperResults()
    r.messages = parser.messages
    r.reserves24change = parser.reserves24change
    r.reservesALFAcashier = parser.reservesALFAcashier
    r.usersOnline = parser.usersOnline
    r.botsOnline = parser.botsOnline
    r.devOnline = parser.devOnline
    r.supportOnline = parser.supportOnline
    r.adminOnline = parser.adminOnline

    return r

########NEW FILE########
__FILENAME__ = trade
# Copyright (c) 2013 Alan McIntyre

import urllib
import hashlib
import hmac
import warnings
from datetime import datetime

from btceapi import common
from btceapi import keyhandler


class InvalidNonceException(Exception):
    def __init__(self, method, expectedNonce, actualNonce):
        Exception.__init__(self)
        self.method = method
        self.expectedNonce = expectedNonce
        self.actualNonce = actualNonce

    def __str__(self):
        return "Expected a nonce greater than %d" % self.expectedNonce

class InvalidSortOrderException(Exception):
    ''' Exception thrown when an invalid sort order is passed '''
    pass

class TradeAccountInfo(object):
    '''An instance of this class will be returned by
    a successful call to TradeAPI.getInfo.'''

    def __init__(self, info):
        funds = info.get(u'funds')
        for c in common.all_currencies:
            setattr(self, "balance_%s" % c, funds.get(unicode(c), 0))

        self.open_orders = info.get(u'open_orders')
        self.server_time = datetime.fromtimestamp(info.get(u'server_time'))

        self.transaction_count = info.get(u'transaction_count')
        rights = info.get(u'rights')
        self.info_rights = (rights.get(u'info') == 1)
        self.withdraw_rights = (rights.get(u'withdraw') == 1)
        self.trade_rights = (rights.get(u'trade') == 1)


class TransactionHistoryItem(object):
    '''A list of instances of this class will be returned by
    a successful call to TradeAPI.transHistory.'''

    def __init__(self, transaction_id, info):
        self.transaction_id = transaction_id
        items = ("type", "amount", "currency", "desc",
                 "status", "timestamp")
        for n in items:
            setattr(self, n, info.get(n))
        self.timestamp = datetime.fromtimestamp(self.timestamp)


class TradeHistoryItem(object):
    '''A list of instances of this class will be returned by
    a successful call to TradeAPI.tradeHistory.'''

    def __init__(self, transaction_id, info):
        self.transaction_id = transaction_id
        items = ("pair", "type", "amount", "rate", "order_id",
                 "is_your_order", "timestamp")
        for n in items:
            setattr(self, n, info.get(n))
        self.timestamp = datetime.fromtimestamp(self.timestamp)


class OrderItem(object):
    '''A list of instances of this class will be returned by
    a successful call to TradeAPI.activeOrders.'''

    def __init__(self, order_id, info):
        self.order_id = int(order_id)
        vnames = ("pair", "type", "amount", "rate", "timestamp_created",
                  "status")
        for n in vnames:
            setattr(self, n, info.get(n))
        self.timestamp_created = datetime.fromtimestamp(self.timestamp_created)


class TradeResult(object):
    '''An instance of this class will be returned by
    a successful call to TradeAPI.trade.'''

    def __init__(self, info):
        self.received = info.get(u"received")
        self.remains = info.get(u"remains")
        self.order_id = info.get(u"order_id")
        funds = info.get(u'funds')
        for c in common.all_currencies:
            setattr(self, "balance_%s" % c, funds.get(unicode(c), 0))


class CancelOrderResult(object):
    '''An instance of this class will be returned by
    a successful call to TradeAPI.cancelOrder.'''

    def __init__(self, info):
        self.order_id = info.get(u"order_id")
        funds = info.get(u'funds')
        for c in common.all_currencies:
            setattr(self, "balance_%s" % c, funds.get(unicode(c), 0))


def setHistoryParams(params, from_number, count_number, from_id, end_id,
                     order, since, end):
    if from_number is not None:
        params["from"] = "%d" % from_number
    if count_number is not None:
        params["count"] = "%d" % count_number
    if from_id is not None:
        params["from_id"] = "%d" % from_id
    if end_id is not None:
        params["end_id"] = "%d" % end_id
    if order is not None:
        if order not in ("ASC", "DESC"):
            raise InvalidSortOrderException("Unexpected order parameter: %r" % order)
        params["order"] = order
    if since is not None:
        params["since"] = "%d" % since
    if end is not None:
        params["end"] = "%d" % end


class TradeAPI(object):
    def __init__(self, key, handler):
        self.key = key
        self.handler = handler

        if not isinstance(self.handler, keyhandler.KeyHandler):
            raise TypeError("The handler argument must be a"
                            " keyhandler.KeyHandler")

        # We depend on the key handler for the secret
        self.secret = handler.getSecret(key)

    def _post(self, params, connection=None, raiseIfInvalidNonce=False):
        params["nonce"] = self.handler.getNextNonce(self.key)
        encoded_params = urllib.urlencode(params)

        # Hash the params string to produce the Sign header value
        H = hmac.new(self.secret, digestmod=hashlib.sha512)
        H.update(encoded_params)
        sign = H.hexdigest()

        if connection is None:
            connection = common.BTCEConnection()

        headers = {"Key": self.key, "Sign": sign}
        result = connection.makeJSONRequest("/tapi", headers, encoded_params)

        success = result.get(u'success')
        if not success:
            err_message = result.get(u'error')
            method = params.get("method", "[uknown method]")

            if "invalid nonce" in err_message:
                # If the nonce is out of sync, make one attempt to update to
                # the correct nonce.  This sometimes happens if a bot crashes
                # and the nonce file doesn't get saved, so it's reasonable to
                # attempt one correction.  If multiple threads/processes are
                # attempting to use the same key, this mechanism will
                # eventually fail and the InvalidNonce will be emitted so that
                # you'll end up here reading this comment. :)

                # The assumption is that the invalid nonce message looks like
                # "invalid nonce parameter; on key:4, you sent:3"
                s = err_message.split(",")
                expected = int(s[-2].split(":")[1])
                actual = int(s[-1].split(":")[1])
                if raiseIfInvalidNonce:
                    raise InvalidNonceException(method, expected, actual)

                warnings.warn("The nonce in the key file is out of date;"
                              " attempting to correct.")
                self.handler.setNextNonce(self.key, expected + 1)
                return self._post(params, connection, True)
            elif "no orders" in err_message and method == "ActiveOrders":
                # ActiveOrders returns failure if there are no orders;
                # intercept this and return an empty dict.
                return {}

            raise Exception("%s call failed with error: %s"
                            % (method, err_message))

        if u'return' not in result:
            raise Exception("Response does not contain a 'return' item.")

        return result.get(u'return')

    def getInfo(self, connection=None):
        params = {"method": "getInfo"}
        return TradeAccountInfo(self._post(params, connection))

    def transHistory(self, from_number=None, count_number=None,
                     from_id=None, end_id=None, order="DESC",
                     since=None, end=None, connection=None):

        params = {"method": "TransHistory"}

        setHistoryParams(params, from_number, count_number, from_id, end_id,
                         order, since, end)

        orders = self._post(params, connection)
        result = []
        for k, v in orders.items():
            result.append(TransactionHistoryItem(int(k), v))

        # We have to sort items here because the API returns a dict
        if "ASC" == order:
            result.sort(key=lambda a: a.transaction_id, reverse=False)
        elif "DESC" == order:
            result.sort(key=lambda a: a.transaction_id, reverse=True)

        return result

    def tradeHistory(self, from_number=None, count_number=None,
                     from_id=None, end_id=None, order=None,
                     since=None, end=None, pair=None, connection=None):

        params = {"method": "TradeHistory"}

        setHistoryParams(params, from_number, count_number, from_id, end_id,
                         order, since, end)

        if pair is not None:
            common.validatePair(pair)
            params["pair"] = pair

        orders = list(self._post(params, connection).items())
        orders.sort(reverse=order != "ASC")
        result = []
        for k, v in orders:
            result.append(TradeHistoryItem(int(k), v))

        return result

    def activeOrders(self, pair=None, connection=None):

        params = {"method": "ActiveOrders"}

        if pair is not None:
            common.validatePair(pair)
            params["pair"] = pair

        orders = self._post(params, connection)
        result = []
        for k, v in orders.items():
            result.append(OrderItem(k, v))

        return result

    def trade(self, pair, trade_type, rate, amount, connection=None):
        common.validateOrder(pair, trade_type, rate, amount)
        params = {"method": "Trade",
                  "pair": pair,
                  "type": trade_type,
                  "rate": common.formatCurrency(rate, pair),
                  "amount": common.formatCurrency(amount, pair)}

        return TradeResult(self._post(params, connection))

    def cancelOrder(self, order_id, connection=None):
        params = {"method": "CancelOrder",
                  "order_id": order_id}
        return CancelOrderResult(self._post(params, connection))

########NEW FILE########
__FILENAME__ = cancel-orders
#!/usr/bin/python
import sys
import btceapi

# This sample shows use of a KeyHandler.  For each API key in the file
# passed in as the first argument, all pending orders for the specified
# pair and type will be canceled.

if len(sys.argv) < 4:
    print "Usage: cancel_orders.py <key file> <pair> <order type>"
    print "    key file - Path to a file containing key/secret/nonce data"
    print "    pair - A currency pair, such as btc_usd"
    print "    order type - Type of orders to process, either 'buy' or 'sell'"
    sys.exit(1)

key_file = sys.argv[1]
pair = sys.argv[2]
order_type = unicode(sys.argv[3])

handler = btceapi.KeyHandler(key_file)
for key in handler.keys:
    print "Canceling orders for key %s" % key

    t = btceapi.TradeAPI(key, handler)

    try:
        # Get a list of orders for the given pair, and cancel the ones
        # with the correct order type.
        orders = t.activeOrders(pair = pair)
        for o in orders:
            if o.type == order_type:
                print "  Canceling %s %s order for %f @ %f" % (pair, order_type,
                    o.amount, o.rate)
                t.cancelOrder(o.order_id)

        if not orders:
            print "  There are no %s %s orders" % (pair, order_type)
    except Exception as e:
        print "  An error occurred: %s" % e

########NEW FILE########
__FILENAME__ = compute-account-value
#!/usr/bin/python
import sys

import btceapi

if len(sys.argv) < 2:
    print "Usage: compute-account-value.py <key file>"
    print "    key file - Path to a file containing key/secret/nonce data"
    sys.exit(1)

key_file = sys.argv[1]
with btceapi.KeyHandler(key_file, resaveOnDeletion=True) as handler:
    for key in handler.getKeys():
        print "Computing value for key %s" % key

        # NOTE: In future versions, the handler argument will be required.
        conn = btceapi.BTCEConnection()
        t = btceapi.TradeAPI(key, handler)

        try:
            r = t.getInfo(connection = conn)

            exchange_rates = {}
            for pair in btceapi.all_pairs:
                asks, bids = btceapi.getDepth(pair)
                exchange_rates[pair] = bids[0][0]

            btc_total = 0
            for currency in btceapi.all_currencies:
                balance = getattr(r, "balance_" + currency)
                if currency == "btc":
                    print "\t%s balance: %s" % (currency.upper(), balance)
                    btc_total += balance
                else:
                    pair = "%s_btc" % currency
                    if pair in btceapi.all_pairs:
                        btc_equiv = balance * exchange_rates[pair]
                    else:
                        pair = "btc_%s" % currency
                        btc_equiv = balance / exchange_rates[pair]

                    bal_str = btceapi.formatCurrency(balance, pair)
                    btc_str = btceapi.formatCurrency(btc_equiv, "btc_usd")
                    print "\t%s balance: %s (~%s BTC)" % (currency.upper(),
                                                          bal_str, btc_str)
                    btc_total += btc_equiv

            print "\tCurrent value of open orders:"
            orders = t.activeOrders(connection = conn)
            if orders:
                for o in orders:
                    c1, c2 = o.pair.split("_")
                    c2_equiv = o.amount * exchange_rates[o.pair]
                    if c2 == "btc":
                        btc_equiv = c2_equiv
                    else:
                        btc_equiv = c2_equiv / exchange_rates["btc_%s" % c2]

                    btc_str = btceapi.formatCurrency(btc_equiv, pair)
                    print "\t\t%s %s %s @ %s (~%s BTC)" % (o.type, o.amount,
                                                           o.pair, o.rate,
                                                           btc_str)
                    btc_total += btc_equiv
            else:
                print "\t\tThere are no open orders."

            btc_str = btceapi.formatCurrency(btc_total, "btc_usd")
            print "\n\tTotal estimated value: %s BTC" % btc_str
            for fiat in ("usd", "eur", "rur"):
                fiat_pair = "btc_%s" % fiat
                fiat_total = btc_total * exchange_rates[fiat_pair]
                fiat_str = btceapi.formatCurrencyDigits(fiat_total, 2)
                print "\t                       %s %s" % (fiat_str,
                                                          fiat.upper())

        except Exception as e:
            print "  An error occurred: %s" % e
            raise e


########NEW FILE########
__FILENAME__ = print-account-info
#!/usr/bin/python
import sys

import btceapi

if len(sys.argv) < 2:
    print "Usage: print-account-info.py <key file>"
    print "    key file - Path to a file containing key/secret/nonce data"
    sys.exit(1)

key_file = sys.argv[1]
handler = btceapi.KeyHandler(key_file, resaveOnDeletion=True)
for key in handler.getKeys():
    print "Printing info for key %s" % key

    # NOTE: In future versions, the handler argument will be required.
    conn = btceapi.BTCEConnection()
    t = btceapi.TradeAPI(key, handler)

    try:
        r = t.getInfo(connection = conn)

        for currency in btceapi.all_currencies:
            balance = getattr(r, "balance_" + currency)
            print "\t%s balance: %s" % (currency.upper(), balance)
        print "\tInformation rights: %r" % r.info_rights
        print "\tTrading rights: %r" % r.trade_rights
        print "\tWithrawal rights: %r" % r.withdraw_rights
        print "\tServer time: %r" % r.server_time
        print "\tItems in transaction history: %r" % r.transaction_count
        print "\tNumber of open orders: %r" % r.open_orders
        print "\topen orders:"
        orders = t.activeOrders(connection = conn)
        if orders:
            for o in orders:
                print "\t\torder id: %r" % o.order_id
                print "\t\t    type: %s" % o.type
                print "\t\t    pair: %s" % o.pair
                print "\t\t    rate: %s" % o.rate
                print "\t\t  amount: %s" % o.amount
                print "\t\t created: %r" % o.timestamp_created
                print "\t\t  status: %r" % o.status
                print
        else:
            print "\t\tno orders"

    except Exception as e:
        print "  An error occurred: %s" % e
        raise e


########NEW FILE########
__FILENAME__ = print-trans-history
#!/usr/bin/python
import sys

import btceapi

if len(sys.argv) < 2:
    print "Usage: print-trans-history.py <key file>"
    print "    key file - Path to a file containing key/secret/nonce data"
    sys.exit(1)

key_file = sys.argv[1]
# NOTE: In future versions, resaveOnDeletion will default to True.
handler = btceapi.KeyHandler(key_file, resaveOnDeletion=True)
for key in handler.getKeys():
    print "Printing info for key %s" % key

    # NOTE: In future versions, the handler argument will be required.
    t = btceapi.TradeAPI(key, handler)

    try:
        th = t.transHistory()
        for h in th:
            print "\t\t        id: %r" % h.transaction_id
            print "\t\t      type: %r" % h.type
            print "\t\t    amount: %r" % h.amount
            print "\t\t  currency: %r" % h.currency
            print "\t\t      desc: %s" % h.desc
            print "\t\t    status: %r" % h.status
            print "\t\t timestamp: %r" % h.timestamp
            print

    except Exception as e:
        print "  An error occurred: %s" % e


########NEW FILE########
__FILENAME__ = show-chat
#!/usr/bin/python
import btceapi

mainPage = btceapi.scrapeMainPage()
for message in mainPage.messages:
    msgId, user, time, text = message
    print "%s %s: %s" % (time, user, text)

print
if mainPage.reserves24change is not None:
    print "24change reserves: %d USD" % mainPage.reserves24change
else:
    print "24change reserves: ?? USD"

if mainPage.reservesALFAcashier is not None:
    print "ALFAcashier reserves: %d USD" % mainPage.reservesALFAcashier
else:
    print "ALFAcashier reserves: ?? USD"

print "%d users online" % mainPage.usersOnline
print "%d bots online" % mainPage.botsOnline
print "dev online: %s" % ('yes' if mainPage.devOnline else 'no')
print "support online: %s" % ('yes' if mainPage.supportOnline else 'no')
print "admin online: %s" % ('yes' if mainPage.adminOnline else 'no')
########NEW FILE########
__FILENAME__ = show-depth
#!/usr/bin/python
import sys
import pylab
import numpy as np

import btceapi

# If an argument is provided to this script, it will be interpreted
# as a currency pair for which depth should be displayed. Otherwise
# the BTC/USD depth will be displayed.

if len(sys.argv) >= 2:
    pair = sys.argv[1]
    print "Showing depth for %s" % pair
else:
    print "No currency pair provided, defaulting to btc_usd"
    pair = "btc_usd"

asks, bids = btceapi.getDepth(pair)

print len(asks), len(bids)

ask_prices, ask_volumes = zip(*asks)
bid_prices, bid_volumes = zip(*bids)

pylab.plot(ask_prices, np.cumsum(ask_volumes), 'r-')
pylab.plot(bid_prices, np.cumsum(bid_volumes), 'g-')
pylab.grid()
pylab.title("%s depth" % pair)
pylab.show()

########NEW FILE########
__FILENAME__ = show-fees
#!/usr/bin/python
import btceapi

print "Trading fees:"
connection = btceapi.BTCEConnection()
for pair in btceapi.all_pairs:
    fee = btceapi.getTradeFee(pair, connection)
    print "    %s %.3f %%" % (pair, fee)

########NEW FILE########
__FILENAME__ = show-history
#!/usr/bin/python
import sys
import pylab
import btceapi

# If an argument is provided to this script, it will be interpreted
# as a currency pair for which history should be displayed. Otherwise
# the BTC/USD history will be displayed.

if len(sys.argv) >= 2:
    pair = sys.argv[1]
    print "Showing history for %s" % pair
else:
    print "No currency pair provided, defaulting to btc_usd"
    pair = "btc_usd"
    
history = btceapi.getTradeHistory(pair)

print len(history)

pylab.plot([t.date for t in history if t.trade_type == u'ask'],
           [t.price for t in history if t.trade_type == u'ask'], 'ro')

pylab.plot([t.date for t in history if t.trade_type == u'bid'],
           [t.price for t in history if t.trade_type == u'bid'], 'go')

pylab.grid()          
pylab.show()

########NEW FILE########
__FILENAME__ = show-tickers
#!/usr/bin/python
import btceapi

attrs = ('high', 'low', 'avg', 'vol', 'vol_cur', 'last',
         'buy', 'sell', 'updated', 'server_time')

print "Tickers:"
connection = btceapi.BTCEConnection()
for pair in btceapi.all_pairs:
    ticker = btceapi.getTicker(pair, connection)
    print pair
    for a in attrs:
        print "\t%s %s" % (a, getattr(ticker, a))

########NEW FILE########
__FILENAME__ = watch
#!/usr/bin/python
import sys
import time

import wx
import matplotlib
matplotlib.use("WXAgg")
matplotlib.rcParams['toolbar'] = 'None'

import matplotlib.pyplot as plt
import pylab

import btceapi


class Chart(object):
    def __init__(self, symbol):
        self.symbol = symbol
        self.base = symbol.split("_")[0].upper()
        self.alt = symbol.split("_")[1].upper()

        self.ticks = btceapi.getTradeHistory(self.symbol)
        self.last_tid = max([t.tid for t in self.ticks])

        self.fig = plt.figure()
        self.axes = self.fig.add_subplot(111)
        self.bid_line, = self.axes.plot(*zip(*self.bid), \
                linestyle='None', marker='o', color='red')
        self.ask_line, = self.axes.plot(*zip(*self.ask), \
                linestyle='None', marker='o', color='green')
        
        self.fig.canvas.draw()

        self.timer_id = wx.NewId()
        self.actor = self.fig.canvas.manager.frame
        self.timer = wx.Timer(self.actor, id=self.timer_id)
        self.timer.Start(10000) # update every 10 seconds
        wx.EVT_TIMER(self.actor, self.timer_id, self.update)

        pylab.show()

    @property
    def bid(self):
        return [(t.date, t.price) for t in self.ticks if t.trade_type == u'bid']

    @property
    def ask(self):
        return [(t.date, t.price) for t in self.ticks if t.trade_type == u'ask']

    def update(self, event):
        ticks = btceapi.getTradeHistory(self.symbol)
        self.ticks += [t for t in ticks if t.tid > self.last_tid]

        for t in ticks:
            if t.tid > self.last_tid:
                print "%s: %s %f at %s %f" % \
                        (t.trade_type, self.base, t.amount, self.alt, t.price)

        self.last_tid = max([t.tid for t in ticks])

        x, y = zip(*self.bid)
        self.bid_line.set_xdata(x)
        self.bid_line.set_ydata(y)

        x, y = zip(*self.ask)
        self.ask_line.set_xdata(x)
        self.ask_line.set_ydata(y)

        pylab.gca().relim()
        pylab.gca().autoscale_view()

        self.fig.canvas.draw()


if __name__ == "__main__":
    symbol = "btc_usd"
    try:
        symbol = sys.argv[1]
    except IndexError:
        pass

    chart = Chart(symbol)


########NEW FILE########
__FILENAME__ = test_common
import decimal
import random
import unittest
from btceapi.common import *


class TestCommon(unittest.TestCase):
    def test_formatCurrency(self):
        self.assertEqual(formatCurrencyDigits(1.123456789, 1), "1.1")
        self.assertEqual(formatCurrencyDigits(1.123456789, 2), "1.12")
        self.assertEqual(formatCurrencyDigits(1.123456789, 3), "1.123")
        self.assertEqual(formatCurrencyDigits(1.123456789, 4), "1.1234")
        self.assertEqual(formatCurrencyDigits(1.123456789, 5), "1.12345")
        self.assertEqual(formatCurrencyDigits(1.123456789, 6), "1.123456")
        self.assertEqual(formatCurrencyDigits(1.123456789, 7), "1.1234567")

        for i in range(2, 8):
            print i
            self.assertEqual(formatCurrencyDigits(1.12, i), "1.12")
            self.assertEqual(formatCurrencyDigits(44.0, i), "44.0")

    def test_formatCurrencyByPair(self):
        for p, d in max_digits.items():
            self.assertEqual(formatCurrency(1.12, p),
                             formatCurrencyDigits(1.12, d))
            self.assertEqual(formatCurrency(44.0, p),
                             formatCurrencyDigits(44.0, d))
            self.assertEqual(truncateAmount(1.12, p),
                             truncateAmountDigits(1.12, d))
            self.assertEqual(truncateAmount(44.0, p),
                             truncateAmountDigits(44.0, d))

    def test_truncateAmount(self):
        for p, d in max_digits.items():
            self.assertEqual(truncateAmount(1.12, p),
                             truncateAmountDigits(1.12, d))
            self.assertEqual(truncateAmount(44.0, p),
                             truncateAmountDigits(44.0, d))

    def test_validatePair(self):
        for pair in all_pairs:
            validatePair(pair)
        self.assertRaises(InvalidTradePairException,
                          validatePair, "not_a_real_pair")

    def test_validateOrder(self):
        for pair in all_pairs:
            t = random.choice(("buy", "sell"))
            a = random.random()
            if pair[4] == "btc":
                validateOrder(pair, t, a, decimal.Decimal("0.01"))
            else:
                validateOrder(pair, t, a, decimal.Decimal("0.1"))

            t = random.choice(("buy", "sell"))
            a = decimal.Decimal(str(random.random()))
            if pair[:4] == "btc_":
                self.assertRaises(InvalidTradeAmountException,
                                  validateOrder, pair, t, a,
                                  decimal.Decimal("0.009999"))
            else:
                self.assertRaises(InvalidTradeAmountException,
                                  validateOrder, pair, t, a,
                                  decimal.Decimal("0.09999"))

        self.assertRaises(InvalidTradePairException,
                          validateOrder, "foo_bar", "buy",
                          decimal.Decimal("1.0"), decimal.Decimal("1.0"))
        self.assertRaises(InvalidTradeTypeException,
                          validateOrder, "btc_usd", "foo",
                          decimal.Decimal("1.0"), decimal.Decimal("1.0"))

    def test_parseJSONResponse(self):
        json1 = """
                {"asks":[[3.29551,0.5],[3.29584,5]],
                "bids":[[3.29518,15.51461],[3,27.5]]}
                """
        parsed = parseJSONResponse(json1)
        asks = parsed.get("asks")
        self.assertEqual(asks[0], [decimal.Decimal("3.29551"),
                                   decimal.Decimal("0.5")])
        self.assertEqual(asks[1], [decimal.Decimal("3.29584"),
                                   decimal.Decimal("5")])
        bids = parsed.get("bids")
        self.assertEqual(bids[0], [decimal.Decimal("3.29518"),
                                   decimal.Decimal("15.51461")])
        self.assertEqual(bids[1], [decimal.Decimal("3"),
                                   decimal.Decimal("27.5")])

    def test_pair_identity(self):
        self.assertEqual(set(max_digits.keys()), set(min_orders.keys()))
        self.assertEqual(set(max_digits.keys()), set(all_pairs))

    def test_currency_sets(self):
        currencies_from_pairs = set()
        for p in all_pairs:
            c1, c2 = p.split("_")
            currencies_from_pairs.add(c1)
            currencies_from_pairs.add(c2)

        self.assertEqual(currencies_from_pairs, set(all_currencies))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_public
import decimal
import unittest
from btceapi.public import *


class TestPublic(unittest.TestCase):
    def test_constructTrade(self):
        d = {"pair": "btc_usd",
             "trade_type": "bid",
             "price": decimal.Decimal("1.234"),
             "tid": 1,
             "amount": decimal.Decimal("3.2"),
             "date": 1368805684.878004}

        t = Trade(**d)
        self.assertEqual(t.pair, d.get("pair"))
        self.assertEqual(t.trade_type, d.get("trade_type"))
        self.assertEqual(t.price, d.get("price"))
        self.assertEqual(t.tid, d.get("tid"))
        self.assertEqual(t.amount, d.get("amount"))
        assert type(t.date) is datetime.datetime
        test_date = datetime.datetime.fromtimestamp(1368805684.878004)
        self.assertEqual(t.date, test_date)

        # check conversion of decimal dates
        d["date"] = decimal.Decimal("1368805684.878004")
        t = Trade(**d)
        assert type(t.date) is datetime.datetime
        self.assertEqual(t.date, test_date)

        # check conversion of integer dates
        d["date"] = 1368805684
        test_date = datetime.datetime.fromtimestamp(1368805684)
        t = Trade(**d)
        assert type(t.date) is datetime.datetime
        self.assertEqual(t.date, test_date)

        # check conversion of string dates with no fractional seconds
        d["date"] = "2013-05-17 08:48:04"
        t = Trade(**d)
        assert type(t.date) is datetime.datetime
        self.assertEqual(t.date, datetime.datetime(2013, 5, 17, 8, 48, 4, 0))

        # check conversion of string dates with fractional seconds
        d["date"] = "2013-05-17 08:48:04.878004"
        t = Trade(**d)
        assert type(t.date) is datetime.datetime
        self.assertEqual(t.date,
                         datetime.datetime(2013, 5, 17, 8, 48, 4, 878004))

        # check conversion of unicode dates with no fractional seconds
        d["date"] = u"2013-05-17 08:48:04"
        t = Trade(**d)
        assert type(t.date) is datetime.datetime
        self.assertEqual(t.date, datetime.datetime(2013, 5, 17, 8, 48, 4, 0))

        # check conversion of string dates with fractional seconds
        d["date"] = u"2013-05-17 08:48:04.878004"
        t = Trade(**d)
        assert type(t.date) is datetime.datetime
        self.assertEqual(t.date,
                         datetime.datetime(2013, 5, 17, 8, 48, 4, 878004))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
