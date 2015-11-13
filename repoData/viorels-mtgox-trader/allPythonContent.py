__FILENAME__ = api

from httplib2 import Http
import simplejson as json
from urlparse import urlunparse
from urllib import urlencode

class ServerError(Exception):
    def __init__(self, ret):
        self.ret = ret
    def __str__(self):
        return "Server error: %s" % self.ret

class UserError(Exception):
    def __init__(self, errmsg):
        self.errmsg = errmsg
    def __str__(self):
        return self.errmsg

class MTGox:
    """MTGox API"""
    def __init__(self, user, password):
        self.user = user
        self.password = password
        self.server = "mtgox.com"
        self.timeout = 10
        self.actions = {"_get_ticker": ("GET", "/code/data/ticker.php"),
                        "get_depth": ("GET", "/code/data/getDepth.php"),
                        "get_trades": ("GET", "/code/data/getTrades.php"),
                        "get_balance": ("POST", "/code/getFunds.php"),
                        "buy_btc": ("POST", "/code/buyBTC.php"),
                        "sell_btc": ("POST", "/code/sellBTC.php"),
                        "_get_orders": ("POST", "/code/getOrders.php"),
                        "_cancel_order": ("POST", "/code/cancelOrder.php"),
                        "_withdraw": ("POST", "/code/withdraw.php")}
        
        for action, (method, _) in self.actions.items():
            def _handler(action=action, **args):
                return self._request(action, method=method, args=args)
            setattr(self, action, _handler)

    def get_ticker(self):
        return self._get_ticker()["ticker"]

    def get_orders(self):
        return self._get_orders()["orders"] # can also return balance

    def cancel_order(self, oid, typ=None):
        orders = self.get_orders()
        if typ is None:
            order = [o for o in orders if o["oid"] == oid]
            if order:
                typ = order[0]["type"]
            else:
                raise UserError("unknown order/type")
        return self._cancel_order(oid=oid, type=typ)


    def withdraw(self, amount, btca, group1="BTC"):
        return self._withdraw(amount=amount, btca=btca, group1=group1)["status"] # can also return balance

    def _request(self, action, method="GET", args={}):
        query = args.copy()
        data = None
        headers = {}
        if method == "GET":
            url = self._url(action)
        if method == "POST":
            url = self._url(action, scheme="https")
            query["name"] = self.user
            query["pass"] = self.password
            data = urlencode(query)
            headers['Content-type'] = 'application/x-www-form-urlencoded'

        h = Http(cache=None, timeout=self.timeout)
        try:
            #print "%s %s\n> |%s|" % (method, url, data)
            resp, content = h.request(url, method, headers=headers, body=data)
            #print "< %s (%s)" % (content, resp)
            if resp.status == 200:
                data = json.loads(content)
                if "error" in data:
                    raise UserError(data["error"])
                else:
                    return data 
            else:
                raise ServerError(content)
        except AttributeError, e: # 'NoneType' object has no attribute 'makefile'
            raise ServerError("timeout/refused")
        except ValueError, e:
            raise ServerError("%s: %s" % (e, content))

    def _url(self, action, scheme="http", args={}):
        url = urlunparse((scheme,
                          self.server,
                          self.actions[action][1], # path
                          '',
                          urlencode(args),
                          ''))
        return url

class ExchB(MTGox):
    def __init__(self,user,password):
	MTGox.__init__(self,user,password) 
        self.server = "www.exchangebitcoins.com"
        self.actions = {"_get_ticker": ("GET", "/data/ticker"),
                        "get_depth": ("GET", "/data/depth"),
                        "get_trades": ("GET", "/data/recent"),
                        "get_balance": ("POST", "/data/getFunds"),
                        "buy_btc": ("POST", "/data/buyBTC"),
                        "sell_btc": ("POST", "/data/sellBTC"),
                        "_get_orders": ("POST", "/data/getOrders"),
                        "_cancel_order": ("POST", "/data/cancelOrder")}
        
	


########NEW FILE########
__FILENAME__ = balance
#!/usr/bin/env python

from settings import *

balance = exchange.get_balance()
print balance


########NEW FILE########
__FILENAME__ = buy
#!/usr/bin/env python

import sys

from settings import * 

if len(sys.argv) in (2, 3):
    amount = sys.argv[1]
    bid = sys.argv[2] if len(sys.argv) == 3 else None
else:
    print "Usage: %s <amount> [bid]" % sys.argv[0]
    exit(1)

status = exchange.buy_btc(amount=amount, price=bid)
print status


########NEW FILE########
__FILENAME__ = cancel
#!/usr/bin/env python

import sys

from settings import * 

if len(sys.argv) == 2:
    oid = sys.argv[1]
else:
    print "Usage: %s <order id>" % sys.argv[0]
    exit(1)

status = exchange.cancel_order(oid=oid)
print status


########NEW FILE########
__FILENAME__ = defaultsettings
#!/usr/bin/env python

#
#  Copy to settings.py, enter credentials for the 
#  exchange(s) you would like to connect to and uncomment
#  the corresponding exchange line.
#

from api import ExchB, MTGox

EXCHB_USER = 'your_username'
EXCHB_PASSWORD = 'your_password'

MTGOX_USER = 'your_username'
MTGOX_PASSWORD = 'your_password'

# uncomment the exchange you want to use
#exchange = ExchB(user=EXCHB_USER, password=EXCHB_PASSWORD)
exchange = MTGox(user=MTGOX_USER, password=MTGOX_PASSWORD)

########NEW FILE########
__FILENAME__ = depth
#!/usr/bin/env python

from settings import *

depth = exchange.get_depth()

bids = sorted(depth['bids'], key=lambda bid: bid[0])
asks = sorted(depth['asks'], key=lambda bid: bid[0])

print "*** Bids"
for price, amount in bids:
    print "%s\t%s" % (price, amount)

print "\n*** Asks"
for price, amount in asks:
    print "%s\t%s" % (price, amount)


########NEW FILE########
__FILENAME__ = orders
#!/usr/bin/env python

import time

from settings import *

orders = exchange.get_orders()

now = time.time()
for order in orders:
    order["type_text"] = {1: "sell", 2: "buy", "Sell": "sell", "Buy": "buy"}[order["type"]]
    if "status" in order:
       order["status_text"] = {1: "active", 
                               2: "not enough funds"}[int(order["status"])]
    else:
       order["status_text"] = "active"
    order["ago"] = int((now - int(order["date"]))/60)
    print ("%(oid)s %(type_text)s %(amount)s at %(price)s %(ago)s minutes ago, "
           "%(status_text)s" % order)



########NEW FILE########
__FILENAME__ = sell
#!/usr/bin/env python

import sys

from settings import *

if len(sys.argv) in (2, 3):
    amount = sys.argv[1]
    ask = sys.argv[2] if len(sys.argv) == 3 else None
else:
    print "Usage: %s <amount> [ask]" % sys.argv[0]
    exit(1)

status = exchange.sell_btc(amount=amount, price=ask)
print status


########NEW FILE########
__FILENAME__ = ticker
#!/usr/bin/env python

from settings import *

ticker = exchange.get_ticker()

if ticker:
    for key in ("last", "buy", "sell", "low", "high", "vol"):
        print "%s\t: %s" % (key, ticker[key])
else:
    print "failed, see logs"


########NEW FILE########
__FILENAME__ = trades
#!/usr/bin/env python

import time

from settings import *

trades = exchange.get_trades()

now = time.time()
for tr in trades:
    # also print tid
    print "%s \t@ %s (%s minutes ago)" % (tr["amount"], 
                                          tr["price"], 
                                          int((now - tr["date"])/60))


########NEW FILE########
__FILENAME__ = watch
#!/usr/bin/env python

import time

from settings import *

wait = 60

last_trades = {}
last_bids = []
last_asks = []

while True:
    trades = exchange.get_trades()

    now = time.time()
    for tr in trades:
        if not last_trades.has_key(tr["tid"]):
            last_trades[tr["tid"]] = tr
            # also print tid
            print "%s: %s \t@ %s (%s minutes ago)" % (tr["tid"],
                                                      tr["amount"], 
                                                      tr["price"], 
                                                      int((now - tr["date"])/60))

    time.sleep(wait)
    continue

    depth = exchange.get_depth()

    bids = sorted(depth['bids'], key=lambda bid: bid[0])
    asks = sorted(depth['asks'], key=lambda bid: bid[0])

    print "*** Bids"
    for price, amount in bids:
        print "%s\t%s" % (price, amount)

    print "\n*** Asks"
    for price, amount in asks:
        print "%s\t%s" % (price, amount)

    time.sleep(wait)


########NEW FILE########
__FILENAME__ = withdraw
#!/usr/bin/env python

import sys

from settings import *

if len(sys.argv) == 3:
    _, amount, address = sys.argv
else:
    print "Usage: %s <amount> <BTC address>" % sys.argv[0]
    exit(1)

status = exchange.withdraw(group1="BTC", btca=address, amount=amount)
print status


########NEW FILE########
