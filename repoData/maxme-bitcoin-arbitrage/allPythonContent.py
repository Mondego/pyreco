__FILENAME__ = arbitrage
# Copyright (C) 2013, Maxime Biais <maxime@biais.org>

import logging
import argparse
import sys
from arbitrer import Arbitrer


class ArbitrerCLI:
    def __init__(self):
        self.inject_verbose_info()

    def inject_verbose_info(self):
        logging.VERBOSE = 15
        logging.verbose = lambda x: logging.log(logging.VERBOSE, x)
        logging.addLevelName(logging.VERBOSE, "VERBOSE")

    def exec_command(self, args):
        if "watch" in args.command:
            self.arbitrer.loop()
        if "replay-history" in args.command:
            self.arbitrer.replay_history(args.replay_history)
        if "get-balance" in args.command:
            if not args.markets:
                logging.error("You must use --markets argument to specify markets")
                sys.exit(2)
            pmarkets = args.markets.split(",")
            pmarketsi = []
            for pmarket in pmarkets:
                exec('import private_markets.' + pmarket.lower())
                market = eval('private_markets.' + pmarket.lower()
                              + '.Private' + pmarket + '()')
                pmarketsi.append(market)
            for market in pmarketsi:
                print(market)

    def create_arbitrer(self, args):
        self.arbitrer = Arbitrer()
        if args.observers:
            self.arbitrer.init_observers(args.observers.split(","))
        if args.markets:
            self.arbitrer.init_markets(args.markets.split(","))

    def main(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("-d", "--debug", help="debug verbosity",
                            action="store_true")
        parser.add_argument("-v", "--verbose", help="verbose mode",
                            action="store_true")
        parser.add_argument("-o", "--observers", type=str,
                            help="observers, example: -oLogger,Emailer")
        parser.add_argument("-m", "--markets", type=str,
                            help="markets, example: -mMtGox,Bitstamp")
        parser.add_argument("command", nargs='*', default="watch",
                            help='verb: "watch|replay-history|get-balance"')
        args = parser.parse_args()
        level = logging.INFO
        if args.verbose:
            level = logging.VERBOSE
        if args.debug:
            level = logging.DEBUG
        logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s',
                            level=level)
        self.create_arbitrer(args)
        self.exec_command(args)

def main():
    cli = ArbitrerCLI()
    cli.main()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = arbitrer
# Copyright (C) 2013, Maxime Biais <maxime@biais.org>

import public_markets
import observers
import config
import time
import logging
import json
from concurrent.futures import ThreadPoolExecutor, wait


class Arbitrer(object):
    def __init__(self):
        self.markets = []
        self.observers = []
        self.depths = {}
        self.init_markets(config.markets)
        self.init_observers(config.observers)
        self.threadpool = ThreadPoolExecutor(max_workers=10)

    def init_markets(self, markets):
        self.market_names = markets
        for market_name in markets:
            exec('import public_markets.' + market_name.lower())
            market = eval('public_markets.' + market_name.lower() + '.' +
                          market_name + '()')
            self.markets.append(market)

    def init_observers(self, _observers):
        self.observer_names = _observers
        for observer_name in _observers:
            exec('import observers.' + observer_name.lower())
            observer = eval('observers.' + observer_name.lower() + '.' +
                            observer_name + '()')
            self.observers.append(observer)

    def get_profit_for(self, mi, mj, kask, kbid):
        if self.depths[kask]["asks"][mi]["price"] \
           >= self.depths[kbid]["bids"][mj]["price"]:
            return 0, 0, 0, 0

        max_amount_buy = 0
        for i in range(mi + 1):
            max_amount_buy += self.depths[kask]["asks"][i]["amount"]
        max_amount_sell = 0
        for j in range(mj + 1):
            max_amount_sell += self.depths[kbid]["bids"][j]["amount"]
        max_amount = min(max_amount_buy, max_amount_sell, config.max_tx_volume)

        buy_total = 0
        w_buyprice = 0
        for i in range(mi + 1):
            price = self.depths[kask]["asks"][i]["price"]
            amount = min(max_amount, buy_total + self.depths[
                         kask]["asks"][i]["amount"]) - buy_total
            if amount <= 0:
                break
            buy_total += amount
            if w_buyprice == 0:
                w_buyprice = price
            else:
                w_buyprice = (w_buyprice * (
                    buy_total - amount) + price * amount) / buy_total

        sell_total = 0
        w_sellprice = 0
        for j in range(mj + 1):
            price = self.depths[kbid]["bids"][j]["price"]
            amount = min(max_amount, sell_total + self.depths[
                         kbid]["bids"][j]["amount"]) - sell_total
            if amount < 0:
                break
            sell_total += amount
            if w_sellprice == 0 or sell_total == 0:
                w_sellprice = price
            else:
                w_sellprice = (w_sellprice * (
                    sell_total - amount) + price * amount) / sell_total

        profit = sell_total * w_sellprice - buy_total * w_buyprice
        return profit, sell_total, w_buyprice, w_sellprice

    def get_max_depth(self, kask, kbid):
        i = 0
        if len(self.depths[kbid]["bids"]) != 0 and \
           len(self.depths[kask]["asks"]) != 0:
            while self.depths[kask]["asks"][i]["price"] \
                  < self.depths[kbid]["bids"][0]["price"]:
                if i >= len(self.depths[kask]["asks"]) - 1:
                    break
                i += 1
        j = 0
        if len(self.depths[kask]["asks"]) != 0 and \
           len(self.depths[kbid]["bids"]) != 0:
            while self.depths[kask]["asks"][0]["price"] \
                  < self.depths[kbid]["bids"][j]["price"]:
                if j >= len(self.depths[kbid]["bids"]) - 1:
                    break
                j += 1
        return i, j

    def arbitrage_depth_opportunity(self, kask, kbid):
        maxi, maxj = self.get_max_depth(kask, kbid)
        best_profit = 0
        best_i, best_j = (0, 0)
        best_w_buyprice, best_w_sellprice = (0, 0)
        best_volume = 0
        for i in range(maxi + 1):
            for j in range(maxj + 1):
                profit, volume, w_buyprice, w_sellprice = self.get_profit_for(
                    i, j, kask, kbid)
                if profit >= 0 and profit >= best_profit:
                    best_profit = profit
                    best_volume = volume
                    best_i, best_j = (i, j)
                    best_w_buyprice, best_w_sellprice = (
                        w_buyprice, w_sellprice)
        return best_profit, best_volume, \
               self.depths[kask]["asks"][best_i]["price"], \
               self.depths[kbid]["bids"][best_j]["price"], \
               best_w_buyprice, best_w_sellprice

    def arbitrage_opportunity(self, kask, ask, kbid, bid):
        perc = (bid["price"] - ask["price"]) / bid["price"] * 100
        profit, volume, buyprice, sellprice, weighted_buyprice,\
            weighted_sellprice = self.arbitrage_depth_opportunity(kask, kbid)
        if volume == 0 or buyprice == 0:
            return
        perc2 = (1 - (volume - (profit / buyprice)) / volume) * 100
        for observer in self.observers:
            observer.opportunity(
                profit, volume, buyprice, kask, sellprice, kbid,
                perc2, weighted_buyprice, weighted_sellprice)

    def __get_market_depth(self, market, depths):
        depths[market.name] = market.get_depth()

    def update_depths(self):
        depths = {}
        futures = []
        for market in self.markets:
            futures.append(self.threadpool.submit(self.__get_market_depth,
                                                  market, depths))
        wait(futures, timeout=20)
        return depths

    def tickers(self):
        for market in self.markets:
            logging.verbose("ticker: " + market.name + " - " + str(
                market.get_ticker()))

    def replay_history(self, directory):
        import os
        import json
        import pprint
        files = os.listdir(directory)
        files.sort()
        for f in files:
            depths = json.load(open(directory + '/' + f, 'r'))
            self.depths = {}
            for market in self.market_names:
                if market in depths:
                    self.depths[market] = depths[market]
            self.tick()

    def tick(self):
        for observer in self.observers:
            observer.begin_opportunity_finder(self.depths)

        for kmarket1 in self.depths:
            for kmarket2 in self.depths:
                if kmarket1 == kmarket2:  # same market
                    continue
                market1 = self.depths[kmarket1]
                market2 = self.depths[kmarket2]
                if market1["asks"] and market2["bids"] \
                   and len(market1["asks"]) > 0 and len(market2["bids"]) > 0:
                    if float(market1["asks"][0]['price']) \
                       < float(market2["bids"][0]['price']):
                        self.arbitrage_opportunity(kmarket1, market1["asks"][0],
                                                   kmarket2, market2["bids"][0])

        for observer in self.observers:
            observer.end_opportunity_finder()

    def loop(self):
        while True:
            self.depths = self.update_depths()
            self.tickers()
            self.tick()
            time.sleep(config.refresh_rate)

########NEW FILE########
__FILENAME__ = fiatconverter
# Copyright (C) 2013, Maxime Biais <maxime@biais.org>

import urllib.request
import sys
import json
import logging
import time


class FiatConverter:
    __shared_state = {}
    rate_exchange_url = "http://rate-exchange.appspot.com/currency?from=%s&to=%s"
    rate_exchange_url_yahoo = "http://download.finance.yahoo.com/d/quotes.csv?s=%s%s=X&f=sl1d1&e=.csv"

    def __init__(self):
        """USD is used as pivot"""
        self.__dict__ = self.__shared_state
        self.rates = {
            "USD": 1,
            "EUR": 0.77,
            "CNY": 6.15,
            "SEK": 6.6,
        }
        self.update_delay = 60 * 60 # every hour
        self.last_update = 0
        self.bank_fee = 0.007 # FIXME: bank fee

    def get_currency_pair(self, code_from, code_to):
        url = self.rate_exchange_url % (code_from, code_to)
        res = urllib.request.urlopen(url)
        data = json.loads(res.read().decode('utf8'))
        rate = 0
        if "rate" in data:
            rate = float(data["rate"]) * (1.0 - self.bank_fee)
        else:
            logging.error("Can't update fiat conversion rate: %s", url)
        return rate

    def get_currency_pair_yahoo(self, code_from, code_to):
        url = self.rate_exchange_url_yahoo % (code_from, code_to)
        res = urllib.request.urlopen(url)
        data = res.read().decode('utf8').split(",")[1]
        rate = float(data) * (1.0 - self.bank_fee)
        return rate

    def update_currency_pair(self, code_to):
        if code_to == "USD":
            return
        code_from = "USD"
        try:
            rate = self.get_currency_pair(code_from, code_to)
        except urllib.error.HTTPError:
            rate = self.get_currency_pair_yahoo(code_from, code_to)
        if rate:
            self.rates[code_to] = rate

    def update(self):
        timediff = time.time() - self.last_update
        if timediff < self.update_delay:
            return
        self.last_update = time.time()
        for currency in self.rates:
            self.update_currency_pair(currency)

    def convert(self, price, code_from, code_to):
        self.update()
        rate_from = self.rates[code_from]
        rate_to = self.rates[code_to]
        return price / rate_from * rate_to


if __name__ == "__main__":
    fc = FiatConverter()
    print(fc.convert(12., "USD", "EUR"))
    print(fc.convert(12., "EUR", "USD"))
    print(fc.rates)

########NEW FILE########
__FILENAME__ = emailer
import logging
from .observer import Observer
import config
import smtplib


def send_email(subject, message):
    _to = config.smtp_to
    _from = config.smtp_from
    mime_message = """From: Python Arbitrage Script <%(_from)s>
To: <%(_to)s>
Subject: %(subject)s

%(message)s
""" % locals()
    try:
        smtpObj = smtplib.SMTP(config.smtp_host)
        smtpObj.sendmail(_from, [_to], mime_message)
    except smtplib.SMTPException:
        logging.warn("Unable to send email")

class Emailer(Observer):
    def opportunity(self, profit, volume, buyprice, kask, sellprice, kbid, perc,
                    weighted_buyprice, weighted_sellprice):
        if profit > config.profit_thresh and perc > config.perc_thresh:
            message = """profit: %f USD with volume: %f BTC
buy at %.4f (%s) sell at %.4f (%s) ~%.2f%%
""" % (profit, volume, buyprice, kask, sellprice, kbid, perc)
            send_email("Arbitrage Bot", message)

########NEW FILE########
__FILENAME__ = historydumper
from .observer import Observer
import json
import time
import os


class HistoryDumper(Observer):
    out_dir = 'history/'

    def __init__(self):
        try:
            os.mkdir(self.out_dir)
        except:
            pass

    def begin_opportunity_finder(self, depths):
        filename = self.out_dir + 'order-book-' + \
            str(int(time.time())) + '.json'
        fp = open(filename, 'w')
        json.dump(depths, fp)

    def end_opportunity_finder(self):
        pass

    def opportunity(self, profit, volume, buyprice, kask, sellprice, kbid, perc, weighted_buyprice, weighted_sellprice):
        pass

########NEW FILE########
__FILENAME__ = logger
import logging
from .observer import Observer


class Logger(Observer):
    def opportunity(self, profit, volume, buyprice, kask, sellprice, kbid, perc,
                    weighted_buyprice, weighted_sellprice):
        logging.info("profit: %f USD with volume: %f BTC - buy at %.4f (%s) sell at %.4f (%s) ~%.2f%%" % (profit, volume, buyprice, kask, sellprice, kbid, perc))

########NEW FILE########
__FILENAME__ = observer
import abc


class Observer(object, metaclass=abc.ABCMeta):
    def begin_opportunity_finder(self, depths):
        pass

    def end_opportunity_finder(self):
        pass

    ## abstract
    @abc.abstractmethod
    def opportunity(self, profit, volume, buyprice, kask, sellprice, kbid, perc, weighted_buyprice, weighted_sellprice):
        pass

########NEW FILE########
__FILENAME__ = specializedtraderbot
import logging
import config
import time
from .observer import Observer
from private_markets import mtgox
from private_markets import bitcoincentral
from .emailer import send_email


class SpecializedTraderBot(Observer):
    def __init__(self):
        self.mtgox = mtgox.PrivateMtGox()
        self.btcentral = bitcoincentral.PrivateBitcoinCentral()
        self.clients = {
            "MtGoxEUR": self.mtgox,
            "BitcoinCentralEUR": self.btcentral,
        }
        self.profit_percentage_thresholds = {  # Graph
            "MtGoxEUR": {"BitcoinCentralEUR": 3.5},
            "BitcoinCentralEUR": {"MtGoxEUR": 1},
        }
        self.trade_wait = 60 * 5  # in seconds
        self.last_trade = 0
        self.potential_trades = []

    def begin_opportunity_finder(self, depths):
        self.potential_trades = []

    def end_opportunity_finder(self):
        if not self.potential_trades:
            return
        self.potential_trades.sort(key=lambda x: x[0])
        # Execute only the best (more profitable)
        self.execute_trade(*self.potential_trades[0][1:])

    def get_min_tradeable_volume(self, buyprice, eur_bal, btc_bal):
        min1 = float(eur_bal) / ((1. + config.balance_margin) * buyprice)
        min2 = float(btc_bal) / (1. + config.balance_margin)
        return min(min1, min2) * 0.95

    def update_balance(self):
        for kclient in self.clients:
            self.clients[kclient].get_info()

    def opportunity(self, profit, volume, buyprice, kask, sellprice, kbid, perc,
                    weighted_buyprice, weighted_sellprice):
        if kask not in self.clients:
            logging.warn(
                "Can't automate this trade, client not available: %s" % (kask))
            return
        if kbid not in self.clients:
            logging.warn(
                "Can't automate this trade, client not available: %s" % (kbid))
            return
        if perc < self.profit_percentage_thresholds[kask][kbid]:
            logging.warn("Can't automate this trade, profit=%f is lower than defined threshold %f"
                         % (perc, self.profit_percentage_thresholds[kask][kbid]))
            return

        if perc > 20:  # suspicous profit, added after discovering btc-central may send corrupted order book
            logging.warn("Profit=%f seems malformed" % (perc, ))
            return

        # Update client balance
        self.update_balance()

        # maximum volume transaction with current balances
        max_volume = self.get_min_tradeable_volume(
            buyprice, self.clients[kask].eur_balance,
            self.clients[kbid].btc_balance)
        volume = min(volume, max_volume, config.max_tx_volume)
        if volume < config.min_tx_volume:
            logging.warn("Can't automate this trade, minimum volume transaction not reached %f/%f" % (volume, config.min_tx_volume))
            logging.info("Balance on %s: %f EUR - Balance on %s: %f BTC" % (kask, self.clients[kask].eur_balance, kbid, self.clients[kbid].btc_balance))
            return

        current_time = time.time()
        if current_time - self.last_trade < self.trade_wait:
            logging.warn("Can't automate this trade, last trade occured %s seconds ago"
                         % (current_time - self.last_trade))
            return

        self.potential_trades.append([profit, volume, kask, kbid, weighted_buyprice,
                                      weighted_sellprice])

    def execute_trade(self, volume, kask, kbid, weighted_buyprice, weighted_sellprice):
        self.last_trade = time.time()
        logging.info("Buy @%s %f BTC and sell @%s" % (kask, volume, kbid))
        send_email("Bought @%s %f BTC and sold @%s" % (kask, volume, kbid),
                   "weighted_buyprice=%f weighted_sellprice=%f" % (weighted_buyprice, weighted_sellprice))
        self.clients[kask].buy(volume)
        self.clients[kbid].sell(volume)

########NEW FILE########
__FILENAME__ = traderbot
import logging
import config
import time
from .observer import Observer
from .emailer import send_email
from fiatconverter import FiatConverter
from private_markets import mtgoxeur
from private_markets import mtgoxusd
from private_markets import bitstampusd


class TraderBot(Observer):
    def __init__(self):
        self.clients = {
            "MtGoxEUR": mtgoxeur.PrivateMtGoxEUR(),
            "MtGoxUSD": mtgoxusd.PrivateMtGoxUSD(),
            "BitstampUSD": bitstampusd.PrivateBitstampUSD(),
        }
        self.fc = FiatConverter()
        self.trade_wait = 120  # in seconds
        self.last_trade = 0
        self.potential_trades = []

    def begin_opportunity_finder(self, depths):
        self.potential_trades = []

    def end_opportunity_finder(self):
        if not self.potential_trades:
            return
        self.potential_trades.sort(key=lambda x: x[0])
        # Execute only the best (more profitable)
        self.execute_trade(*self.potential_trades[0][1:])

    def get_min_tradeable_volume(self, buyprice, usd_bal, btc_bal):
        min1 = float(usd_bal) / ((1 + config.balance_margin) * buyprice)
        min2 = float(btc_bal) / (1 + config.balance_margin)
        return min(min1, min2)

    def update_balance(self):
        for kclient in self.clients:
            self.clients[kclient].get_info()

    def opportunity(self, profit, volume, buyprice, kask, sellprice, kbid, perc,
                    weighted_buyprice, weighted_sellprice):
        if profit < config.profit_thresh or perc < config.perc_thresh:
            logging.verbose("[TraderBot] Profit or profit percentage lower than"+
                            " thresholds")
            return
        if kask not in self.clients:
            logging.warn("[TraderBot] Can't automate this trade, client not "+
                         "available: %s" % kask)
            return
        if kbid not in self.clients:
            logging.warn("[TraderBot] Can't automate this trade, " +
                         "client not available: %s" % kbid)
            return
        volume = min(config.max_tx_volume, volume)

        # Update client balance
        self.update_balance()
        max_volume = self.get_min_tradeable_volume(buyprice,
                                                   self.clients[kask].usd_balance,
                                                   self.clients[kbid].btc_balance)
        volume = min(volume, max_volume, config.max_tx_volume)
        if volume < config.min_tx_volume:
            logging.warn("Can't automate this trade, minimum volume transaction"+
                         " not reached %f/%f" % (volume, config.min_tx_volume))
            logging.warn("Balance on %s: %f USD - Balance on %s: %f BTC"
                         % (kask, self.clients[kask].usd_balance, kbid,
                            self.clients[kbid].btc_balance))
            return
        current_time = time.time()
        if current_time - self.last_trade < self.trade_wait:
            logging.warn("[TraderBot] Can't automate this trade, last trade " +
                         "occured %.2f seconds ago" %
                         (current_time - self.last_trade))
            return
        self.potential_trades.append([profit, volume, kask, kbid,
                                      weighted_buyprice, weighted_sellprice,
                                      buyprice, sellprice])

    def watch_balances(self):
        pass

    def execute_trade(self, volume, kask, kbid, weighted_buyprice,
                      weighted_sellprice, buyprice, sellprice):
        self.last_trade = time.time()
        logging.info("Buy @%s %f BTC and sell @%s" % (kask, volume, kbid))
        self.clients[kask].buy(volume, buyprice)
        self.clients[kbid].sell(volume, sellprice)

########NEW FILE########
__FILENAME__ = traderbotsim
import logging
import config
from .observer import Observer
from private_markets import mtgox
from private_markets import bitcoincentral
from .traderbot import TraderBot
import json


class MockMarket(object):
    def __init__(self, name, fee=0, usd_balance=500., btc_balance=15., persistent=True):
        self.name = name
        self.filename = "traderbot-sim-" + name + ".json"
        self.usd_balance = usd_balance
        self.btc_balance = btc_balance
        self.fee = fee
        self.persistent = persistent
        if self.persistent:
            try:
                self.load()
            except IOError:
                pass

    def buy(self, volume, price):
        logging.info("execute buy %f BTC @ %f on %s" %
                     (volume, price, self.name))
        self.usd_balance -= price * volume
        self.btc_balance += volume - volume * self.fee
        if self.persistent:
            self.save()

    def sell(self, volume, price):
        logging.info("execute sell %f BTC @ %f on %s" %
                     (volume, price, self.name))
        self.btc_balance -= volume
        self.usd_balance += price * volume - price * volume * self.fee
        if self.persistent:
            self.save()

    def load(self):
        data = json.load(open(self.filename, "r"))
        self.usd_balance = data["usd"]
        self.btc_balance = data["btc"]

    def save(self):
        data = {'usd': self.usd_balance, 'btc': self.btc_balance}
        json.dump(data, open(self.filename, "w"))

    def balance_total(self, price):
        return self.usd_balance + self.btc_balance * price

    def get_info(self):
        pass


class TraderBotSim(TraderBot):
    def __init__(self):
        self.mtgox = MockMarket("mtgox", 0.006)  # 0.6% fee
        self.btcentral = MockMarket("bitcoin-central", 0.00489)
        self.intersango = MockMarket("intersango", 0.0065)
        self.bitcoin24 = MockMarket("bitcoin24", 0)
        self.bitstamp = MockMarket("bitstamp", 0.005)  # 0.5% fee
        self.clients = {
            "MtGoxEUR": self.mtgox,
            "MtGoxUSD": self.mtgox,
            "BitstampUSD": self.bitstamp,
        }
        self.profit_thresh = 1  # in EUR
        self.perc_thresh = 0.6  # in %
        self.trade_wait = 120
        self.last_trade = 0

    def total_balance(self, price):
        market_balances = [i.balance_total(
            price) for i in set(self.clients.values())]
        return sum(market_balances)

    def execute_trade(self, volume, kask, kbid, 
                      weighted_buyprice, weighted_sellprice,
                      buyprice, sellprice):
        self.clients[kask].buy(volume, buyprice)
        self.clients[kbid].sell(volume, sellprice)

if __name__ == "__main__":
    t = TraderBotSim()
    print(t.total_balance(33))

########NEW FILE########
__FILENAME__ = xmppmessager
import logging
import config
import time
from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout
from .observer import Observer


class MyXMPPClient(ClientXMPP):
    def __init__(self):
        logger = logging.getLogger("sleekxmpp")
        logger.setLevel(logging.ERROR)
        ClientXMPP.__init__(self, config.xmpp_jid, config.xmpp_password)
        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)
        self.connect()
        self.process(block=False)

    def session_start(self, event):
        self.send_presence()
        self.get_roster()

    def msend_message(self, message):
        logging.debug('Sending XMPP message: "%s" to %s' % (message,
                                                            config.xmpp_to))
        self.send_message(mto=config.xmpp_to, mbody=message, mtype='chat')

    def message(self, msg):
        # TODO: Use this to control / re-config
        pass  # msg.reply("%(body)s" % msg).send()

class XmppMessager(Observer):
    def __init__(self):
        self.xmppclient = MyXMPPClient()

    def opportunity(self, profit, volume, buyprice, kask, sellprice, kbid, perc,
                    weighted_buyprice, weighted_sellprice):
        if profit > config.profit_thresh and perc > config.perc_thresh:
            message = "profit: %f USD with volume: %f BTC - buy at %.4f (%s) sell at %.4f (%s) ~%.2f%%" % (profit, volume, buyprice, kask, sellprice, kbid, perc)
            self.xmppclient.msend_message(message)

########NEW FILE########
__FILENAME__ = bitcoincentral
from .market import Market
import time
import base64
import hmac
import urllib.request
import urllib.parse
import urllib.error
import urllib.request
import urllib.error
import urllib.parse
import hashlib
import sys
import json
import config


class PrivateBitcoinCentral(Market):
    balance_url = "https://bitcoin-central.net/api/v1/balances/"
    trade_url = "https://bitcoin-central.net/api/v1/trade_orders/"
    withdraw_url = "https://bitcoin-central.net/api/v1/transfers/send_bitcoins/"

    def __init__(self):
        # FIXME: update this file when bitcoin central re-opens
        raise Exception("BitcoinCentral is closed")
        super().__init__()
        self.username = config.bitcoincentral_username
        self.password = config.bitcoincentral_password
        self.currency = "EUR"
        self.get_info()

    def _create_nonce(self):
        return int(time.time() * 1000000)

    def _send_request(self, url, params=[], extra_headers=None):
        headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
        }
        if extra_headers is not None:
            for k, v in extra_headers.items():
                headers[k] = v

        req = None
        if params:
            req = urllib.request.Request(
                url, json.dumps(params), headers=headers)
        else:
            req = urllib.request.Request(url, headers=headers)
        userpass = '%s:%s' % (self.username, self.password)
        base64string = base64.b64encode(bytes(
            userpass, 'utf-8')).decode('ascii')
        req.add_header("Authorization", "Basic %s" % base64string)
        response = urllib.request.urlopen(req)
        code = response.getcode()
        if code == 200:
            jsonstr = response.read().decode('utf-8')
            return json.loads(jsonstr)
        return None

    def trade(self, amount, ttype, price=None):
        # params = [("amount", amount), ("currency", self.currency), ("type",
        # ttype)]
        params = {"amount": amount, "currency": self.currency, "type": ttype}
        if price:
            params["price"] = price
        response = self._send_request(self.trade_url, params)
        return response

    def buy(self, amount, price=None):
        response = self.trade(amount, "buy", price)

    def sell(self, amount, price=None):
        response = self.trade(amount, "sell", price)
        print(response)

    def withdraw(self, amount, address):
        params = {"amount": amount, "address": address}
        response = self._send_request(self.trade_url, params)
        return response

    def deposit(self):
        return config.bitcoincentral_address

    def get_info(self):
        response = self._send_request(self.balance_url)
        if response:
            self.btc_balance = response["BTC"]
            self.eur_balance = response["EUR"]
            self.usd_balance = self.fc.convert(self.eur_balance, "EUR", "USD")

if __name__ == "__main__":
    market = PrivateBitcoinCentral()
    market.get_info()
    print(market)

########NEW FILE########
__FILENAME__ = bitstampusd
# Copyright (C) 2013, Maxime Biais <maxime@biais.org>

from .market import Market, TradeException
import time
import base64
import hmac
import urllib.request
import urllib.parse
import urllib.error
import urllib.request
import urllib.error
import urllib.parse
import hashlib
import sys
import json
import config


class PrivateBitstampUSD(Market):
    balance_url = "https://www.bitstamp.net/api/balance/"
    buy_url = "https://www.bitstamp.net/api/buy/"
    sell_url = "https://www.bitstamp.net/api/sell/"

    def __init__(self):
        super().__init__()
        self.username = config.bitstamp_username
        self.password = config.bitstamp_password
        self.currency = "USD"
        self.get_info()

    def _send_request(self, url, params={}, extra_headers=None):
        headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
        }
        if extra_headers is not None:
            for k, v in extra_headers.items():
                headers[k] = v

        params['user'] = self.username
        params['password'] = self.password
        postdata = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(url, postdata, headers=headers)
        response = urllib.request.urlopen(req)
        code = response.getcode()
        if code == 200:
            jsonstr = response.read().decode('utf-8')
            return json.loads(jsonstr)
        return None

    def _buy(self, amount, price):
        """Create a buy limit order"""
        params = {"amount": amount, "price": price}
        response = self._send_request(self.buy_url, params)
        if "error" in response:
            raise TradeException(response["error"])

    def _sell(self, amount, price):
        """Create a sell limit order"""
        params = {"amount": amount, "price": price}
        response = self._send_request(self.sell_url, params)
        if "error" in response:
            raise TradeException(response["error"])

    def get_info(self):
        """Get balance"""
        response = self._send_request(self.balance_url)
        if response:
            self.btc_balance = float(response["btc_available"])
            self.usd_balance = float(response["usd_available"])

########NEW FILE########
__FILENAME__ = market
# Copyright (C) 2013, Maxime Biais <maxime@biais.org>

import logging
from fiatconverter import FiatConverter

class TradeException(Exception):
    pass

class Market:
    def __init__(self):
        self.name = self.__class__.__name__
        self.btc_balance = 0.
        self.eur_balance = 0.
        self.usd_balance = 0.
        self.fc = FiatConverter()

    def __str__(self):
        return "%s: %s" % (self.name, str({"btc_balance": self.btc_balance,
                                           "eur_balance": self.eur_balance,
                                           "usd_balance": self.usd_balance}))

    def buy(self, amount, price):
        """Orders are always priced in USD"""
        local_currency_price = self.fc.convert(price, "USD", self.currency)
        logging.info("Buy %f BTC at %f %s (%f USD) @%s" % (amount,
                     local_currency_price, self.currency, price, self.name))
        self._buy(amount, local_currency_price)


    def sell(self, amount, price):
        """Orders are always priced in USD"""
        local_currency_price = self.fc.convert(price, "USD", self.currency)
        logging.info("Sell %f BTC at %f %s (%f USD) @%s" % (amount,
                     local_currency_price, self.currency, price, self.name))
        self._sell(amount, local_currency_price)

    def _buy(self, amount, price):
        raise NotImplementedError("%s.sell(self, amount, price)" % self.name)

    def _sell(self, amount, price):
        raise NotImplementedError("%s.sell(self, amount, price)" % self.name)

    def deposit(self):
        raise NotImplementedError("%s.sell(self, amount, price)" % self.name)

    def withdraw(self, amount, address):
        raise NotImplementedError("%s.sell(self, amount, price)" % self.name)

    def get_info(self):
        raise NotImplementedError("%s.sell(self, amount, price)" % self.name)

########NEW FILE########
__FILENAME__ = bitcoin24eur
import urllib.request
import urllib.error
import urllib.parse
import json
from .market import Market


class Bitcoin24EUR(Market):
    def __init__(self):
        super(Bitcoin24EUR, self).__init__("EUR")
        self.update_rate = 20

    def update_depth(self):
        res = urllib.request.urlopen(
            'https://bitcoin-24.com/api/EUR/orderbook.json')
        depth = json.loads(res.read().decode('utf8'))
        self.depth = self.format_depth(depth)

    def sort_and_format(self, l, reverse=False):
        l.sort(key=lambda x: float(x[0]), reverse=reverse)
        r = []
        for i in l:
            r.append({'price': float(i[0]), 'amount': float(i[1])})
        return r

    def format_depth(self, depth):
        bids = self.sort_and_format(depth['bids'], True)
        asks = self.sort_and_format(depth['asks'], False)
        return {'asks': asks, 'bids': bids}

if __name__ == "__main__":
    market = Bitcoin24EUR()
    print(json.dumps(market.get_ticker()))

########NEW FILE########
__FILENAME__ = bitcoin24usd
import urllib.request
import urllib.error
import urllib.parse
import json
from .market import Market


class Bitcoin24USD(Market):
    def __init__(self):
        super(Bitcoin24USD, self).__init__("USD")
        self.update_rate = 60

    def update_depth(self):
        res = urllib.request.urlopen(
            'https://bitcoin-24.com/api/USD/orderbook.json')
        depth = json.loads(res.read().decode('utf8'))
        self.depth = self.format_depth(depth)

    def sort_and_format(self, l, reverse=False):
        l.sort(key=lambda x: float(x[0]), reverse=reverse)
        r = []
        for i in l:
            r.append({'price': float(i[0]), 'amount': float(i[1])})
        return r

    def format_depth(self, depth):
        bids = self.sort_and_format(depth['bids'], True)
        asks = self.sort_and_format(depth['asks'], False)
        return {'asks': asks, 'bids': bids}

if __name__ == "__main__":
    market = Bitcoin24USD()
    print(json.dumps(market.get_ticker()))

########NEW FILE########
__FILENAME__ = bitcoincentraleur
import urllib.request
import urllib.error
import urllib.parse
import json
from .market import Market


class BitcoinCentralEUR(Market):
    def __init__(self):
        super(BitcoinCentralEUR, self).__init__("EUR")
        # bitcoin central maximum call / day = 5000
        # keep 2500 for other operations
        self.update_rate = 24 * 60 * 60 / 2500

    def update_depth(self):
        res = urllib.request.urlopen(
            'https://bitcoin-central.net/api/data/eur/depth')
        depth = json.loads(res.read().decode('utf8'))
        self.depth = self.format_depth(depth)

    def sort_and_format(self, l, reverse=False):
        l.sort(key=lambda x: float(x['price']), reverse=reverse)
        r = []
        for i in l:
            r.append({'price': float(i[
                     'price']), 'amount': float(i['amount'])})
        return r

    def format_depth(self, depth):
        bids = self.sort_and_format(depth['bids'], True)
        asks = self.sort_and_format(depth['asks'], False)
        return {'asks': asks, 'bids': bids}

if __name__ == "__main__":
    market = BitcoinCentralEUR()
    print(market.get_ticker())

########NEW FILE########
__FILENAME__ = bitcoincentralusd
import urllib.request
import urllib.error
import urllib.parse
import json
from .market import Market


class BitcoinCentralUSD(Market):
    def __init__(self):
        super(BitcoinCentralUSD, self).__init__("USD")
        self.update_rate = 60

    def update_depth(self):
        res = urllib.request.urlopen(
            'https://bitcoin-central.net/api/v1/depth?currency=USD')
        depth = json.loads(res.read().decode('utf8'))
        self.depth = self.format_depth(depth)

    def sort_and_format(self, l, reverse=False):
        l.sort(key=lambda x: float(x['price']), reverse=reverse)
        r = []
        for i in l:
            r.append({'price': float(i[
                     'price']), 'amount': float(i['amount'])})
        return r

    def format_depth(self, depth):
        bids = self.sort_and_format(depth['bids'], True)
        asks = self.sort_and_format(depth['asks'], False)
        return {'asks': asks, 'bids': bids}

if __name__ == "__main__":
    market = BitcoinCentralEUR()
    print(market.get_ticker())

########NEW FILE########
__FILENAME__ = bitfinexusd
import urllib.request
import urllib.error
import urllib.parse
import json
import logging
from .market import Market


class BitfinexUSD(Market):
    def __init__(self):
        super().__init__("USD")
        self.update_rate = 20
        self.depth = {'asks': [{'price': 0, 'amount': 0}], 'bids': [
            {'price': 0, 'amount': 0}]}

    def update_depth(self):
        res = urllib.request.urlopen(
            'https://api.bitfinex.com/v1/book/btcusd')
        jsonstr = res.read().decode('utf8')
        try:
            depth = json.loads(jsonstr)
        except Exception:
            logging.error("%s - Can't parse json: %s" % (self.name, jsonstr))
        self.depth = self.format_depth(depth)

    def sort_and_format(self, l, reverse=False):
        l.sort(key=lambda x: float(x["price"]), reverse=reverse)
        r = []
        for i in l:
            r.append({'price': float(i['price']),
                      'amount': float(i['amount'])})
        return r

    def format_depth(self, depth):
        bids = self.sort_and_format(depth['bids'], True)
        asks = self.sort_and_format(depth['asks'], False)
        return {'asks': asks, 'bids': bids}

########NEW FILE########
__FILENAME__ = bitfloorusd
import urllib.request
import urllib.error
import urllib.parse
import json
from .market import Market


class BitfloorUSD(Market):
    def __init__(self):
        super(BitfloorUSD, self).__init__("USD")
        self.update_rate = 60

    def update_depth(self):
        res = urllib.request.urlopen('https://api.bitfloor.com/book/L2/1')
        depth = json.loads(res.read().decode('utf8'))
        self.depth = self.format_depth(depth)

    def sort_and_format(self, l, reverse=False):
        l.sort(key=lambda x: float(x[0]), reverse=reverse)
        r = []
        for i in l:
            r.append({'price': float(i[0]), 'amount': float(i[1])})
        return r

    def format_depth(self, depth):
        bids = self.sort_and_format(depth['bids'], True)
        asks = self.sort_and_format(depth['asks'], False)
        return {'asks': asks, 'bids': bids}

if __name__ == "__main__":
    market = BitfloorUSD()
    print(market.get_ticker())

########NEW FILE########
__FILENAME__ = bitstampusd
import urllib.request
import urllib.error
import urllib.parse
import json
import sys
from .market import Market


class BitstampUSD(Market):
    def __init__(self):
        super(BitstampUSD, self).__init__("USD")
        self.update_rate = 20

    def update_depth(self):
        url = 'https://www.bitstamp.net/api/order_book/'
        req = urllib.request.Request(url, None, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "User-Agent": "curl/7.24.0 (x86_64-apple-darwin12.0)"})
        res = urllib.request.urlopen(req)
        depth = json.loads(res.read().decode('utf8'))
        self.depth = self.format_depth(depth)

    def sort_and_format(self, l, reverse):
        r = []
        for i in l:
            r.append({'price': float(i[0]), 'amount': float(i[1])})
        r.sort(key=lambda x: float(x['price']), reverse=reverse)
        return r

    def format_depth(self, depth):
        bids = self.sort_and_format(depth['bids'], True)
        asks = self.sort_and_format(depth['asks'], False)
        return {'asks': asks, 'bids': bids}

if __name__ == "__main__":
    market = BitstampUSD()
    print(market.get_ticker())

########NEW FILE########
__FILENAME__ = btceeur
import urllib.request
import urllib.error
import urllib.parse
import json
from .market import Market


class BtceEUR(Market):
    def __init__(self):
        super(BtceEUR, self).__init__("EUR")
        # bitcoin central maximum call / day = 5000
        # keep 2500 for other operations
        self.update_rate = 60

    def update_depth(self):
        url = 'https://btc-e.com/api/2/btc_eur/depth'
        req = urllib.request.Request(url, None, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "User-Agent": "curl/7.24.0 (x86_64-apple-darwin12.0)"})
        res = urllib.request.urlopen(req)
        depth = json.loads(res.read().decode('utf8'))
        self.depth = self.format_depth(depth)

    def sort_and_format(self, l, reverse=False):
        l.sort(key=lambda x: float(x[0]), reverse=reverse)
        r = []
        for i in l:
            r.append({'price': float(i[0]), 'amount': float(i[1])})
        return r

    def format_depth(self, depth):
        bids = self.sort_and_format(depth['bids'], True)
        asks = self.sort_and_format(depth['asks'], False)
        return {'asks': asks, 'bids': bids}

if __name__ == "__main__":
    market = BtceEUR()
    print(market.get_ticker())

########NEW FILE########
__FILENAME__ = btceusd
import urllib.request
import urllib.error
import urllib.parse
import json
from .market import Market


class BtceUSD(Market):
    def __init__(self):
        super(BtceUSD, self).__init__("USD")
        self.update_rate = 60

    def update_depth(self):
        url = 'https://btc-e.com/api/2/btc_usd/depth'
        req = urllib.request.Request(url, None, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "User-Agent": "curl/7.24.0 (x86_64-apple-darwin12.0)"})
        res = urllib.request.urlopen(req)
        depth = json.loads(res.read().decode('utf8'))
        self.depth = self.format_depth(depth)

    def sort_and_format(self, l, reverse=False):
        l.sort(key=lambda x: float(x[0]), reverse=reverse)
        r = []
        for i in l:
            r.append({'price': float(i[0]), 'amount': float(i[1])})
        return r

    def format_depth(self, depth):
        bids = self.sort_and_format(depth['bids'], True)
        asks = self.sort_and_format(depth['asks'], False)
        return {'asks': asks, 'bids': bids}

if __name__ == "__main__":
    market = BtceUSD()
    print(market.get_ticker())

########NEW FILE########
__FILENAME__ = campbxusd
import urllib.request
import urllib.error
import urllib.parse
import json
from .market import Market


class CampBXUSD(Market):
    def __init__(self):
        super(CampBXUSD, self).__init__("USD")
        self.update_rate = 60

    def update_depth(self):
        req = urllib.request.Request('http://campbx.com/api/xdepth.php')
        req.add_header('User-Agent', 'Mozilla/5.0')
        res = urllib.request.urlopen(req)
        depth = json.loads(res.read().decode('utf8'))
        self.depth = self.format_depth(depth)

    def sort_and_format(self, l, reverse=False):
        l.sort(key=lambda x: float(x[0]), reverse=reverse)
        r = []
        for i in l:
            r.append({'price': float(i[0]), 'amount': float(i[1])})
        return r

    def format_depth(self, depth):
        bids = self.sort_and_format(depth['Bids'], True)
        asks = self.sort_and_format(depth['Asks'], False)
        return {'asks': asks, 'bids': bids}

if __name__ == "__main__":
    market = CampBXUSD()
    print(market.get_ticker())

########NEW FILE########
__FILENAME__ = intersangoeur
import urllib.request
import urllib.error
import urllib.parse
import json
from .market import Market


class IntersangoEUR(Market):
    def __init__(self):
        super(IntersangoEUR, self).__init__("EUR")
        self.update_rate = 30

    def update_depth(self):
        res = urllib.request.urlopen(
            'https://intersango.com//api/depth.php?currency_pair_id=2')
        depth = json.loads(res.read().decode('utf8'))
        self.depth = self.format_depth(depth)

    def sort_and_format(self, l, reverse=False):
        l.sort(key=lambda x: float(x[0]), reverse=reverse)
        r = []
        for i in l:
            r.append({'price': float(i[0]), 'amount': float(i[1])})
        return r

    def format_depth(self, depth):
        bids = self.sort_and_format(depth['bids'], True)
        asks = self.sort_and_format(depth['asks'], False)
        return {'asks': asks, 'bids': bids}

if __name__ == "__main__":
    market = IntersangoEUR()
    print(json.dumps(market.get_ticker()))

########NEW FILE########
__FILENAME__ = krakeneur
from ._kraken import Kraken

class KrakenEUR(Kraken):
    def __init__(self):
        super().__init__("EUR", "XXBTZEUR")

########NEW FILE########
__FILENAME__ = krakenusd
from ._kraken import Kraken

class KrakenUSD(Kraken):
    def __init__(self):
        super().__init__("USD", "XXBTZUSD")

########NEW FILE########
__FILENAME__ = market
import time
import urllib.request
import urllib.error
import urllib.parse
import config
import logging
import sys
from fiatconverter import FiatConverter
from utils import log_exception

class Market(object):
    def __init__(self, currency):
        self.name = self.__class__.__name__
        self.currency = currency
        self.depth_updated = 0
        self.update_rate = 60
        self.fc = FiatConverter()
        self.fc.update()

    def get_depth(self):
        timediff = time.time() - self.depth_updated
        if timediff > self.update_rate:
            self.ask_update_depth()
        timediff = time.time() - self.depth_updated
        if timediff > config.market_expiration_time:
            logging.warn('Market: %s order book is expired' % self.name)
            self.depth = {'asks': [{'price': 0, 'amount': 0}], 'bids': [
                {'price': 0, 'amount': 0}]}
        return self.depth

    def convert_to_usd(self):
        if self.currency == "USD":
            return
        for direction in ("asks", "bids"):
            for order in self.depth[direction]:
                order["price"] = self.fc.convert(order["price"], self.currency, "USD")

    def ask_update_depth(self):
        try:
            self.update_depth()
            self.convert_to_usd()
            self.depth_updated = time.time()
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            logging.error("HTTPError, can't update market: %s" % self.name)
            log_exception(logging.DEBUG)
        except Exception as e:
            logging.error("Can't update market: %s - %s" % (self.name, str(e)))
            log_exception(logging.DEBUG)

    def get_ticker(self):
        depth = self.get_depth()
        res = {'ask': 0, 'bid': 0}
        if len(depth['asks']) > 0 and len(depth["bids"]) > 0:
            res = {'ask': depth['asks'][0],
                   'bid': depth['bids'][0]}
        return res

    ## Abstract methods
    def update_depth(self):
        pass

    def buy(self, price, amount):
        pass

    def sell(self, price, amount):
        pass

########NEW FILE########
__FILENAME__ = _kraken
import urllib.request
import urllib.error
import urllib.parse
import json
from .market import Market

class Kraken(Market):
    def __init__(self, currency, code):
        super().__init__(currency)
        self.code = code
        self.update_rate = 30

    def update_depth(self):
        url = 'https://api.kraken.com/0/public/Depth'
        req = urllib.request.Request(url, b"pair=" + bytes(self.code, "ascii"),
                                     headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "User-Agent": "curl/7.24.0 (x86_64-apple-darwin12.0)"})
        res = urllib.request.urlopen(req)
        depth = json.loads(res.read().decode('utf8'))
        self.depth = self.format_depth(depth)

    def sort_and_format(self, l, reverse=False):
        l.sort(key=lambda x: float(x[0]), reverse=reverse)
        r = []
        for i in l:
            r.append({'price': float(i[0]), 'amount': float(i[1])})
        return r

    def format_depth(self, depth):
        bids = self.sort_and_format(depth['result'][self.code]['bids'], True)
        asks = self.sort_and_format(depth['result'][self.code]['asks'], False)
        return {'asks': asks, 'bids': bids}

########NEW FILE########
__FILENAME__ = arbitrage_speed_test
import sys
sys.path.append('../')
import json
import arbitrage
import time
from observers import observer


class TestObserver(observer.Observer):
    def opportunity(self, profit, volume, buyprice, kask, sellprice, kbid,
                    perc, weighted_buyprice, weighted_sellprice):
        print("Time: %.3f" % profit)

def main():
    arbitrer = arbitrage.Arbitrer()
    depths = arbitrer.depths = json.load(open("speed-test.json"))
    start_time = time.time()
    testobs = TestObserver()
    arbitrer.observers = [testobs]
    arbitrer.arbitrage_opportunity("BitstampUSD", depths["BitstampUSD"]["asks"][0],
                                   "MtGoxEUR", depths["MtGoxEUR"]["asks"][0])
    # FIXME: add asserts
    elapsed = time.time() - start_time
    print("Time: %.3f" % elapsed)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = arbitrage_test
import sys
sys.path.append('../')
import unittest

import arbitrage

depths1 = {
    'BitcoinCentralEUR':
    {'asks': [{'amount': 4, 'price': 32.8},
              {'amount': 8, 'price': 32.9},
              {'amount': 2, 'price': 33.0},
              {'amount': 3, 'price': 33.6}],
     'bids': [{'amount': 2, 'price': 31.8},
              {'amount': 4, 'price': 31.6},
              {'amount': 6, 'price': 31.4},
              {'amount': 2, 'price': 30}]},
    'MtGoxEUR':
    {'asks': [{'amount': 1, 'price': 34.2},
              {'amount': 2, 'price': 34.3},
              {'amount': 3, 'price': 34.5},
              {'amount': 3, 'price': 35.0}],
     'bids': [{'amount': 2, 'price': 33.2},
              {'amount': 3, 'price': 33.1},
              {'amount': 5, 'price': 32.6},
              {'amount': 10, 'price': 32.3}]}}

depths2 = {
    'BitcoinCentralEUR':
    {'asks': [{'amount': 4, 'price': 32.8},
              {'amount': 8, 'price': 32.9},
              {'amount': 2, 'price': 33.0},
              {'amount': 3, 'price': 33.6}]},
    'MtGoxEUR':
    {'bids': [{'amount': 2, 'price': 33.2},
              {'amount': 3, 'price': 33.1},
              {'amount': 5, 'price': 32.6},
              {'amount': 10, 'price': 32.3}]}}

depths3 = {
    'BitcoinCentralEUR':
    {'asks': [{'amount': 1, 'price': 34.2},
              {'amount': 2, 'price': 34.3},
              {'amount': 3, 'price': 34.5},
              {'amount': 3, 'price': 35.0}]},
    'MtGoxEUR':
    {'bids': [{'amount': 2, 'price': 33.2},
              {'amount': 3, 'price': 33.1},
              {'amount': 5, 'price': 32.6},
              {'amount': 10, 'price': 32.3}]}}


class TestArbitrage(unittest.TestCase):
    def setUp(self):
        self.arbitrer = arbitrage.Arbitrer()

    def test_getprofit1(self):
        self.arbitrer.depths = depths2
        profit, vol, wb, ws = self.arbitrer.get_profit_for(
            0, 0, 'BitcoinCentralEUR', 'MtGoxEUR')
        assert(80 == int(profit * 100))
        assert(vol == 2)

    def test_getprofit2(self):
        self.arbitrer.depths = depths2
        profit, vol, wb, ws = self.arbitrer.get_profit_for(
            2, 1, 'BitcoinCentralEUR', 'MtGoxEUR')
        assert(159 == int(profit * 100))
        assert(vol == 5)

    def test_getprofit3(self):
        self.arbitrer.depths = depths3
        profit, vol, wb, ws = self.arbitrer.get_profit_for(
            2, 1, 'BitcoinCentralEUR', 'MtGoxEUR')
        assert(profit == 0)
        assert(vol == 0)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = utils
import os
import sys
import traceback
import logging

def log_exception(level):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    for i in traceback.extract_tb(exc_traceback):
        # line = (os.path.basename(i[0]), i[1], i[2])
        line = (i[0], i[1], i[2])
        logging.log(level, 'File "%s", line %d, in %s' % line)
        logging.log(level, '\t%s' % i[3])

########NEW FILE########
