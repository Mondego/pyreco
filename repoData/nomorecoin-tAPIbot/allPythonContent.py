__FILENAME__ = api
import hashlib
import hmac
import json
import time
import urllib
import urllib2

###TODO:
# add instance of helper.Log?
# PEP8-ify
# Better exception handling

#------------
# Private API
#------------

class tradeapi:
    '''Trading and account-specific info from btc-e API'''
    def __init__(self,key,secret):
        self.api = key
        self.secret = secret
        self.url = 'https://btc-e.com/tapi'
        self.tradeData = {}
        
    def update(self):
        '''Wrapper for poll method, return response reassigned to dict'''
        raw = self.poll()
        if raw['success'] == 0: # API response has failed
            print('API response returned status "fail", trying call again.')
            self.update() # try again
        output = raw.get('return')
        self.tradeData['funds'] = output['funds']
        self.tradeData['openOrders'] = output['open_orders']
        self.tradeData['transCount'] = output['transaction_count']
        self.tradeData['apiRights'] = output['rights']
        self.tradeData['serverTime'] = output['server_time']
        if self.tradeData['openOrders'] > 0:
            self.tradeData['orders'] = self.getOrders()
        return self.tradeData
		
    def poll(self):
        '''Request private API info from BTC-e'''
        send = {'method':
        'getInfo',
        'nonce':int(time.time())}
        response = self.postdata(self.url,send)
        return response
        
    def trade(self,pair,orderType,orderRate,orderAmount):
        '''Place trade. Note: all args required'''
        send = {'method':
        'Trade',
        'nonce':int(time.time()),
        'pair':pair,
        'type':orderType,
        'rate':orderRate,
        'amount':orderAmount}
        return self.postdata(self.url,send)
                
    def getOrders(self,):
        '''Returns all open orders, modified from raw return'''
        send = {'method':
        'OrderList',
        'nonce':int(time.time())}
        return self.postdata(self.url,send)

    def cancelOrder(self,orderId):
        '''Cancel an order by specific orderId'''
        send = {'method':
        'CancelOrder',
        'nonce':int(time.time()),
        'order_id':orderId}
        return self.postdata(self.url,send)
        
    def postdata(self,url,datadict):
        '''Appends POST to request, sends, parses JSON response'''
        data = urllib.urlencode(datadict)
        headers = {
        'User-Agent':'nomorePy',
        'Accept':'text/xml,application/xml,application/xhtml+xml,text/html,text/json,application/json,text/plain',
        'Accept-Language':'en',
        'Key':self.api,
        'Sign':self.sign(data)
        }
        request = urllib2.Request(url,data,headers)
        while True: 
            try:
                response = json.loads(urllib2.urlopen(request).read())
                if response['success'] == 0:
                    # API call returned failed status
                    pass
                return response
            except (urllib2.URLError, urllib2.HTTPError) as e:
                print 'Connection Error, sleeping...'
                for second in range(5):
                    time.sleep(1)
                continue
            except Exception as e:
                print e
                print 'Sleeping, then retrying'
                for second in range(5):
                    time.sleep(1)
                continue
        
    def sign(self,param):
        H = hmac.new(self.secret, digestmod=hashlib.sha512)
        H.update(param)
        return H.hexdigest()
		
        
#------------
# Public API
#------------

class publicapi(object):
    '''Parse BTC-e Public API'''
        
    def __init__(self):
        self.url = 'https://btc-e.com/api/2/' #append pair, method
        self.tickerDict = {}
        
    def update(self,pairs):
        '''Updates pairs set to True,
        where pairs is dict of booleans currencies.'''
        for pair in pairs:
            if pairs[pair]:
                self.updatePair(pair)
        return self.tickerDict 

    def poll(self,url):
        '''Generic public API parsing method, returns parsed dict'''
        while True:
            try:
                request = urllib2.Request(url)
                response = json.loads(urllib2.urlopen(request).read())
                return response
            except urllib2.URLError as e:
                print "Caught URL Error, sleeping..."
                for second in range(5):
                    time.sleep(1) 
                print "Retrying connection now."
                continue
            except urllib2.HTTPError as e:
                print "Caught HTTP Error, sleeping..."
                for second in range(5):
                    time.sleep(1) 
                print "Retrying connection now."
                continue
            except Exception as e:
                print 'publicapi.poll caught other Exception:'
                print e
                print 'Sleeping...'
                for second in range(5):
                    time.sleep(1) 
                print "Retrying now."
                continue

    def ticker(self,pair):
        '''Returns ticker dict for a single pair'''
        url = self.url + pair + '/ticker'
        raw = self.poll(url)
        ticker = raw['ticker']
        return ticker

    def depth(self,pair):
        '''Returns depth dict for a single pair'''
        url = self.url + pair + '/depth'
        depth = self.poll(url)
        return depth

    def trades(self,pair):
        url = self.url + pair + '/trades'
        trades = self.poll(url)
        return trades

    def getLast(self,pair):
        '''Returns most recent traded price of pair'''
        trades = self.trades(pair)
        price = trades[0].get('price')
        return price

    def getLastID(self,pair):
        '''Returns ID of last trade for pair'''
        trades = self.trades(pair)
        tradeID = trades[0].get('tid')
        return tradeID
        
    def updatePair(self,pair):
        '''Update stored ticker info for a single pair, reassigns to variables'''
        tick = self.ticker(pair)
        data = {}
        data['high'] = tick.get('high',0)
        data['low'] = tick.get('low',0)
        data['last'] = tick.get('last',0)
        data['buy'] = tick.get('buy',0)
        data['sell'] = tick.get('sell',0)
        data['vol'] = tick.get('vol',0)
        data['volCur'] = tick.get('vol_cur',0)
        data['avg'] = tick.get('avg',0)
        # uncomment depth/trades for gigantic dict
        #data['depth'] = self.depth(pair)
        #data['trades'] = self.trades(pair)
        self.tickerDict[pair] = data
        return self.tickerDict[pair]

class MA(publicapi):
    '''Generates a moving average signal, limited to 150 points'''
    
    def __init__(self,pair,MAtype,reqPoints):
        self.tick = publicapi()
        self.type = MAtype
        self.reqPoints = reqPoints
        self.pair = pair
        self.priceList = []
        self.dataList = []
        self.volumeData = []
        self.active = False
        self.value = None
        self.lastTID = None
        self.update()

    def getTrades(self):
        '''Returns full list of trades from API'''
        # replace, use publicapi instance to accomplish this
        url = 'https://btc-e.com/api/2/' + self.pair + '/trades'
        while True:
            try:
                json = urllib2.urlopen(url).read()
                (true,false,null) = (True,False,None)
                result = eval(json)
                return result
            except Exception, e:
                # TODO: Handle this better!
                print("Error parsing trades.")
                print("Exception details: %s." %e)
                for second in range(5):
                    time.sleep(1) 
                print "Retrying now."     
                continue

    def addPoint(self,point):
        '''Appends a single point to a MA signal data list'''
        self.dataList.append(point)
        self.activate()
        return self.value

    def update(self):
        '''Perform the steps to update one tick/bar for an MA signal'''
        if self.type == 'SMA':
            rawPrices = self.getTrades()
            # TODO: Investigate storing >150 data points
            self.priceList = [] # reset list, this caps data points to 150
            for trade in rawPrices:
                price = trade.get('price')
                self.priceList.append(price)
            self.dataList = self.priceList[-self.reqPoints:]
            self.activate()
            return self.value
        elif self.type == 'VMA' or self.type == 'VWMA':
            rawTrades = self.getTrades()
            volumeList = []
            weightedList = []
            for trade in rawTrades:
                price = trade.get('price')
                volume = trade.get('amount')
                volumeList.append(volume)
                weightedList.append(price*volume)
            self.dataList = weightedList[-self.reqPoints:]
            self.volumeData = volumeList[-self.reqPoints:]
            self.activate()
            return self.value
        elif self.type == 'EMA':
            # implement EMA calculation
            pass
        
    def activate(self):
        '''
        Flag a MA signal active only when there are enough data points.
        Configured by user.
        '''
        if len(self.dataList) >= self.reqPoints:
            self.active = True
            self.calc() 
            return self.active

    def calc(self):
        '''Calculate MA value for current bar/tick'''
        if self.active:
            if self.type == 'VMA' or self.type == 'VWMA':
                self.value = sum(self.dataList)/sum(self.volumeData)
            elif self.type == 'SMA':
                self.value = sum(self.dataList)/self.reqPoints 
            return self.value
                
        
    def changeReqPoints(self,reqPoints):
        '''Change the MA signal window, ie: number of trailing data points.'''
        self.reqPoints = reqPoints
        self.update()
        return self.reqPoints

    def __str__(self):
        return str(self.value)

########NEW FILE########
__FILENAME__ = Application
import helper
import trader
import time

# TODO: complete re-write/refactor. Seriously.

# print a comforting startup message for impatient users
print'Greetings, human. tAPI-bot loading...'

# Fire up the magic
trader = trader.trade()
config = trader.config
log = trader.log
log.info('tAPI-bot Starting')
# printing needs instantiated classes
printing = helper.Printing(log,config,trader)

def printConfig():
    '''Output basic configured info as reminder to user'''
    # Why not log instead? Are we asking user to confirm settings?
    pass  # until implemented


def runLoop(times=1, inf = True):
    '''Main loop, refresh, display, and trade'''
    while times > 0:
        # check volatility before attempting to trade
        # TODO: move to trader
        volatility = trader.check_volatility()
        min_volatility = config.min_volatility
        print('Volatility is %.2f' % volatility)+'%'
        if volatility >= min_volatility:
            trader.update()
            if config.verbose:
                printing.displayBalance()
            if config.showTicker:
                printing.displayTicker()
            last = trader.last
            log.info('Last Price: %s' %(last))
            print('Last Price: %s' %(last))
            printing.separator()
            # dirty, dirty loop
            if not inf:
                times -= 1
            if times >= 1:
                for second in range(config.sleepTime):
                    time.sleep(1)
        else:
            v_sleep = config.volatility_sleep
            print('Volatility below threshold.')
            print('Sleeping for %s seconds.' % v_sleep)
            for second in range(v_sleep):
                time.sleep(1)

# TODO: read version from file
print'tAPI-bot v0.52 ready.'
runLoop()

#python is pretty awesome

########NEW FILE########
__FILENAME__ = helper
import logging
import time
from ConfigParser import SafeConfigParser
import pylab

class Log(object):
    
    def __init__(self,f='Log.log'):
        FORMAT = '%(asctime)s %(levelname)s %(message)s'
        logging.basicConfig(filename=f,
                            level=logging.DEBUG,
                            format=FORMAT)
        
    def info(self, string):
        logging.info(string)

    def warning(self, string):
        logging.warning(string)

    def error(self, string):
        logging.error(string)

    def critical(self, string):
        logging.critical(string)

    def exception(self, string):
        FORMAT = '%(asctime)s %(levelname)s %(message)s %(funcName)s exc_info'
        logging.basicConfig(filename=f,
                            level=logging.DEBUG,
                            format=FORMAT)
        logging.exception(string)
        

class Config(object):
    '''Read a user configuration file, store values in instance variables'''

    def __init__(self,f='settings.ini'):
        self.file = f
        self.parser = SafeConfigParser()
        self.updateAll()

    def updateAll(self):
        '''Update and store all user settings'''
        self.parser.read(self.file) # TODO: except if file not found, generate defaults
        # API Info
        self.apikey = self.parser.get('API','key')
        self.apisecret = self.parser.get('API','secret')
        # Settings
        self.showTicker = self.parser.getboolean('Settings','showTicker')
        self.verbose = self.parser.getboolean('Settings','verbose')
        self.sleepTime = self.parser.getint('Settings','sleeptime')
        self.saveGraph = self.parser.getboolean('Settings','saveGraph')
        self.graphDPI = self.parser.getint('Settings','graphDPI')
        # Trading
        self.simMode = self.parser.getboolean('Trading','simMode')
        self.pair = self.parser.get('Trading','pair')
        self.min_volatility = self.parser.getfloat('Trading','min_volatility')
        self.volatility_sleep = self.parser.getint('Trading','volatility_sleep')
        self.longOn = self.parser.get('Trading','longOn')
        self.orderType = self.parser.get('Trading','orderType')
        self.fokTimeout = self.parser.getint('Trading','fokTimeout')
        self.fee = self.parser.getfloat('Trading','fee')
        # Signals
        self.MAtype = self.parser.get('Signals','MAtype')
        self.signalType = self.parser.get('Signals','signalType')
        if self.signalType == 'single':
            self.single = self.parser.getint('Signals','single')
        elif self.signalType == 'dual':
            self.fast = self.parser.getint('Signals','fast')
            self.slow = self.parser.getint('Signals','slow')
        elif self.signalType == 'ribbon':
            self.ribbonStart = self.parser.getint('Signals','ribbonStart')
            # Not implemented
            #self.numRibbon = self.parser.getint('Signals','numRibbon')
            self.ribbonSpacing = self.parser.getint('Signals','ribbonSpacing')
        self.priceBand = self.parser.getboolean('Signals','priceBand')
        # Pairs
        # Updated for version 0.52
        self.pairs = {}
        self.pairs['btc_usd'] = self.parser.getboolean('Pairs','btc_usd')
        self.pairs['btc_rur'] = self.parser.getboolean('Pairs','btc_rur')
        self.pairs['btc_eur'] = self.parser.getboolean('Pairs','btc_eur')
        self.pairs['ltc_btc'] = self.parser.getboolean('Pairs','ltc_btc')
        self.pairs['ltc_usd'] = self.parser.getboolean('Pairs','ltc_usd')
        self.pairs['ltc_rur'] = self.parser.getboolean('Pairs','ltc_rur')
        self.pairs['ltc_eur'] = self.parser.getboolean('Pairs','ltc_eur')
        self.pairs['nmc_btc'] = self.parser.getboolean('Pairs','nmc_btc')
        self.pairs['nmc_usd'] = self.parser.getboolean('Pairs','nmc_usd')
        self.pairs['nvc_btc'] = self.parser.getboolean('Pairs','nvc_btc')
        self.pairs['nvc_usd'] = self.parser.getboolean('Pairs','nvc_usd')
        self.pairs['usd_rur'] = self.parser.getboolean('Pairs','usd_rur')
        self.pairs['eur_usd'] = self.parser.getboolean('Pairs','eur_usd')
        self.pairs['trc_btc'] = self.parser.getboolean('Pairs','trc_btc')
        self.pairs['ppc_btc'] = self.parser.getboolean('Pairs','ppc_btc')
        self.pairs['ftc_btc'] = self.parser.getboolean('Pairs','ftc_btc')

    def updateSignals(self):
        '''Update only signals section'''
        self.parser.read(self.file)
        self.signalType = self.parser.get('Signals','signalType')
        if self.signalType == 'single':
            self.single = self.parser.get('Signals','single')
        elif self.signalType == 'dual':
            self.fast = self.parser.getint('Signals','fast')
            self.slow = self.parser.getint('Signals','slow')
        elif self.signalType == 'ribbon':
            self.ribbonStart = self.parser.get('Signals','ribbonStart')
            self.numRibbon = self.parser.get('Signals','numRibbon')
            self.ribbonSpacing = self.parser.get('Signals','ribbonSpacing')

    def updateTrading(self):
        '''Update only trading section'''
        self.parser.read(self.file)
        self.simMode = self.parser.getboolean('Trading','simMode')
        self.pair = self.parser.get('Trading','pair')
        self.longOn = self.parser.get('Trading','longOn')
        self.orderType = self.parser.get('Trading','orderType')

    def updateSettings(self):
        '''Update only settings section'''
        self.parser.read(self.file)
        self.showTicker = self.parser.getboolean('Settings','showTicker')
        self.verbose = self.parser.getboolean('Settings','verbose')
        self.sleepTime = self.parser.getint('Settings','sleeptime')
        self.saveGraph = self.parser.getboolean('Settings','saveGraph')
        self.graphDPI = self.parser.getint('Settings','graphDPI')

    def updatePairs(self):
        self.parser.read(self.file)
        
    
class Printing(object):

    def __init__(self,log,config,trader):
        # Access to instantiated classes
        self.log = log
        self.config = config
        self.trader = trader

    def separator(self,num=1):
        '''print a 79 char line separator, dashes'''
        for i in range(num):
            print('-')*79
    
    def displayBalance(self):
        '''Print significant balances, open orders'''
        orders = self.trader.tradeData.get('openOrders', 'Failed to read orderCount')
##        uncomment 3 lines below for orderType debug printing
##        ordertype = type(orders)
##        print'DEBUG: helper.displayBalance orders TYPE is',ordertype
##        print'DEBUG: helper.displayBalance orders:',orders
        if type(orders) == int and orders > 0: 
            print"Open Orders:",orders
            self.processOrders(printOutput=True)
            self.separator()
        print'Available Balances:'
        funds = self.trader.tradeData['funds']
        for bal in funds.keys():
            if funds[bal] >= 0.01:
                print bal.upper()+':',funds[bal]
        self.separator()

    def processOrders(self, printOutput = False):
        '''Duild dict of open orders, by native ID. Update global orderData'''
        orderData = self.trader.tradeData.get('orders',None)
        if orderData.get('success') == 0: #order data contains failed api call
            orderData = self.trader.tapi.getOrders()
        if printOutput:
            try:
                for key in orderData.keys():
                    order = orderData[key]
                    print('ID: %s %s %s %s at %s' %(key,
                                                    order['pair'],
                                                    order['type'],
                                                    order['amount'],
                                                    order['rate']))
            except TypeError as e:
                # TODO add debug flag for printing output to console on errors
                print'TypeError in processOrders:'
                print e
                logging.error('Type error in helper.processOrders: %s' % e)
                logging.info('orderData: %s' % orderData)
            except KeyError as e:
                print'KeyError in processOrders'
                print e
                logging.error('Key error in helper.processOrders: %s' % e)
                logging.info('orderData: %s' % orderData)
        return orderData

    def displayTicker(self):
        '''Display ticker for any configured pairs'''
        for pair in self.config.pairs:
            if self.config.pairs[pair]:
                self.printTicker(pair, self.trader.tickerData)

    def printTicker(self, pair, tickerData):
        '''Modular print, prints all ticker values of one pair'''
        # needs access to tickerData dict
        data = self.trader.tickerData[pair]
        first = pair[:3].upper()
        second = pair[4:].upper()
        print str(first)+'/'+str(second)+' Volume'
        print str(first),':',data['volCur'],second,':',data['vol']
        print'Last:',data['last'],'Avg:',data['avg']
        print'High:',data['high'],'Low:',data['low']
        print'Bid :',data['sell'],'Ask:',data['buy']
        self.separator()
        
        
# Python is awesome

########NEW FILE########
__FILENAME__ = trader
import helper
import api
import time
import pylab

##TODO:
##    develop oscillator (aroon?) and implement plotting
##    look at implementing n number ribbon lines
##    implement and test min_volatility check
##    remove longOn/shortPosition if possible
##    refactor/conform to PEP8 instead of MIT trickery

class trade(object):
    '''Handle trading, reporting, and signals'''
    def __init__(self):
        self.log = helper.Log()
        self.config = helper.Config()
        self.tick = api.publicapi()
        self.keyCheck()
        self.tapi = api.tradeapi(self.config.apikey,self.config.apisecret)
        self.signals = signals(self.config)
        self.tradeData = self.tapi.update()
        self.tickerData = self.tick.update(self.config.pairs)
        self.standingOrders = {}
        self.last = self.tick.getLast(self.config.pair)
        self.lastID = self.tick.getLastID(self.config.pair)
        self.shortPosition = None
        self.longOn = self.config.longOn
        self.current_volatility = self.check_volatility()

    def check_volatility_day(self):
        '''
        Returns difference in API high/low, as percent. Value is float.
        '''
        # must update tickerData before calculating
        self.tickerData = self.tick.update(self.config.pairs)
        # get high/low
        try:
            low = self.tickerData.get(self.config.pair).get('low')
            high = self.tickerData.get(self.config.pair).get('high')
        except TypeError, e:
            print('Check pair in settings.ini!')
            print e
        # calculate percent absolute difference
        delta = float(high - low)/low
        self.current_volatility = delta*100.0
        p = self.config.pair
        v = self.current_volatility
        self.log.info('%s 24-hour volatility is currently %.2f percent' %(p, v))
        return abs(self.current_volatility)

    def check_volatility(self):
        '''
        Checks absolute difference in min/max price over last 150 trades.
        Returns value as percent. Value is a float.
        '''
        prices = []
        for trade in self.tick.trades(self.config.pair):
            prices.append(trade.get('price'))
        min_price = min(prices)
        max_price = max(prices)
        # calculate percent absolute difference
        delta = float(max_price - min_price)/min_price
        self.current_volatility = delta*100.0
        p = self.config.pair
        v = self.current_volatility
        self.log.info('%s volatility is currently %.2f percent' %(p, v))
        return abs(self.current_volatility)

    def keyCheck(self):
        '''Verify a key and secret are found, and have API access'''
        # check valid key length
        if len(self.config.apikey) <= 43 or len(self.config.apisecret) <= 63:
            self.log.warning('API credentials too short. Exiting.')
            import sys
            sys.exit('Verify you have input API key and secret.')
        # attempt to connect with credentials
        test = api.tradeapi(self.config.apikey,self.config.apisecret)
        # store the output
        self.rights = test.poll().get('return').get('rights')
        if type(self.rights) == None:
            self.log.warning('keycheck rights are Nonetype')
            self.log.warning(self.rights)
            import sys
            sys.exit('Verify you have input API key and secret.')
            
        info = self.rights.get('info')
        trade = self.rights.get('trade')
        if info:
            self.log.info('API info rights enabled')
        if trade:
            self.log.info('API trade rights enabled')
        if not info:
            self.log.warning('API info rights not enabled, cannot continue.')
            import sys
            sys.exit('API info rights not enabled. Exiting.')
        if not trade:
            self.log.info('API trade rights not enabled. Trading disabled.')
            ## TODO: activate sim mode if trade rights not enabled
            

    def update(self):
        '''wrapper, execute a step of trader instance'''
        self.tickerData = self.tick.update(self.config.pairs)
        self.tradeData = self.tapi.update()
        self.check_volatility()
        self.determinePosition()
        self.signals.update()
        self.last = self.tick.getLast(self.config.pair)
        oldID = self.lastID
        self.lastID = self.tick.getLastID(self.config.pair)
        if oldID != self.lastID: # new trade has occurred
            self.evalOrder()
            self.signals.updatePlot(self.last)
        self.updateStandingOrders()
        self.killUnfilled()
        
    def determinePosition(self):
        '''determine which pair user is long on, then position from balance'''
        # TODO: do this better.
        if self.config.simMode:
            return self.shortPosition
        pair = self.config.pair
        if self.config.longOn == 'first':
            longCur = pair[:3]
            shortCur = pair[4:]
        elif self.config.longOn == 'second':
            longCur = pair[4:]
            shortCur = pair[:3]
        balShort = self.tradeData['funds'].get(shortCur,0)
        if self.config.longOn == 'first':
            normShort = balShort/self.last
        else:
            normShort = balShort*self.last
        balLong = self.tradeData['funds'].get(longCur,0)
        if normShort > balLong:
            self.shortPosition = True
        else:
            self.shortPosition = False
    
    def updateLast(self):
        '''update last price and last trade id instance variables'''
        self.last = self.tick.getLast(self.config.pair)
        self.lastID = self.tick.getLastID(self.config.pair)

    def evalOrder(self):
        '''Make decision and execute trade based on configured signals'''
        signalType = self.config.signalType
        price = self.tick.getLast(self.config.pair)
        if self.shortPosition == None:
            self.determinePosition()
        ## TODO: move signal checking to signals class
        if signalType == 'single':
            if self.signals.single.value < price:
                print'Market trending up'
                self.log.info('Market trending up')
                #investigate
                #if self.shortPosition:
                self.placeBid()
            elif self.signals.single.value > price:
                print'Market trending down'
                self.log.info('Market trending down')
                if not self.shortPosition:
                    self.placeAsk()
        if signalType == 'dual':
            # lines cross each other = trade signal
            if self.signals.fastMA.value > self.signals.slowMA.value:
                print'Market trending up'
                self.log.info('Market trending up')
                #investigate
                #if self.shortPosition:
                self.placeBid()
            elif self.signals.fastMA.value < self.signals.slowMA.value:
                print'Market trending down'
                self.log.info('Market trending down')
                if not self.shortPosition:
                    self.placeAsk()
        if signalType == 'ribbon':
            # all ribbons cross price = trade signal
            rib1 = self.signals.rib1.value
            rib2 = self.signals.rib2.value
            rib3 = self.signals.rib3.value
            if rib1 < price  and rib2 < price and rib3 < price:
                print'Market trending up'
                self.log.info('Market trending up')
                #investigate
                #if self.shortPosition:
                self.placeBid()
            elif rib1 > price and rib2 > price and rib3 > price:
                print'Market trending down'
                self.log.info('Market trending down')
                if not self.shortPosition:
                    self.placeAsk()

    def getPip(self):
        '''provides correct minimum pip for orders, BTC-e specific'''
        pair = self.config.pair
        if 'ltc' in pair or 'nmc' in pair:
            return 0.00001
        else:
            return 0.001
        
    def placeBid(self):
        pair = self.config.pair
        pip = self.getPip()
        cur = pair[4:]
        balance = self.tradeData.get('funds').get(cur)
        if self.config.orderType == 'market':
            rate = self.calcDepthRequired(balance,'buy')
        elif self.config.orderType == 'fokLast':
            rate = self.tick.ticker(pair).get('last')
        elif self.config.orderType == 'fokTop':
            bids = self.tick.depth(pair).get('bids')
            highBid = bids[0]
            rate = (highBid[0] + pip)
        amount = balance/rate
        # round, API rejects beyond 8 places
        amount = round((balance/rate),8)
        # trying without this hack
        #amount = amount - 0.00001
        if self.config.simMode:
            self.log.info('Simulated buy: %s %s' % (pair,rate))
            print('Simulated buy: %s %s' % (pair,rate))
            self.shortPosition = False
            self.log.info('shortPosition %s' % self.shortPosition)
        else:
            order = self.placeOrder('buy',rate,amount)
            self.log.info('Attempted buy: %s %s %s' % (pair,rate,amount))
            if order:
                self.log.info('Order successfully placed')
            else:
                self.log.info('Order failed')

    def placeAsk(self):
        pair = self.config.pair
        pip = self.getPip()
        cur = pair[:3]
        balance = self.tradeData.get('funds').get(cur)
        ## TODO: add configurable balance multiplier range
        # round, API rejects beyond 8 places
        amount = round(balance,8)
        if self.config.orderType == 'market':
            rate = self.calcDepthRequired(amount,'sell')
        elif self.config.orderType == 'fokLast':
            rate = self.tick.ticker(pair).get('last')
        elif self.config.orderType == 'fokTop':
            asks = self.tick.depth(pair).get('asks')
            lowAsk = asks[0]
            rate = (lowAsk[0] - pip)
        if self.config.simMode:
            self.log.info('Simulated sell: %s %s' % (pair,rate))
            print('Simulated sell: %s %s' % (pair,rate))
            self.shortPosition = True
            self.log.info('shortPosition %s' % self.shortPosition)
        else:
            order = self.placeOrder('sell',rate,amount)
            self.log.info('Attempted sell: %s %s %s' % (pair,rate,amount))
            if order:
                self.log.info('Order successfully placed')
            else:
                self.log.info('Order failed')

    def placeOrder(self,orderType,rate,amount):
        pair = self.config.pair
        if amount < 0.1: #  can't trade < 0.1
            self.log.warning('Attempted order below 0.1: %s' % amount)
            return False
        else:
            self.log.info('Placing order')
            response = self.tapi.trade(pair,orderType,rate,amount)
            if response['success'] == 0:
                response = response['error']
                self.log.info('Order returned error:/n %s' % response)
                print('Order returned error:/n %s' % (response))
                return False
            elif response.get('return').get('remains') == 0:
                print('Trade Executed!')
                #response = response['return']
                #print response
                self.log.info('Details: %s' %(response))
                return True
            else:
                response = response['return']
                self.trackOrder(response,self.config.pair,orderType,rate)
                print('Order Placed, awaiting fill')
                #print response
                #self.log.info('Order placed, awaiting fill')
                self.log.info('Details: %s' % (response))
                return True

    def calcDepthRequired(self,amount,orderType):
        '''
        Determine price for an order of amount to fill immediately
        assumes depth is list of lists as [price,amount]
        '''
        depth = self.tick.depth(self.config.pair)
        if orderType == 'sell':
            depth = depth['bids']
        elif orderType == 'buy':
            depth = depth['asks']
        else:
            raise InvalidOrderType
        total = 0
        for order in depth:
            total += order[1]
            if total > amount:
                rate = order[0]
                return rate

    def trackOrder(self,response,pair,orderType,rate):
        '''Add unfilled order to tracking dict'''
        order = {}
        order['rate'] = rate
        order['type'] = orderType
        order['pair'] = pair
        order['killcount'] = 0
        orderID = response['order_id']
        debugType = type(orderID)
        print('DEBUG: trackOrder orderID type is %s' % (debugType))
        self.standingOrders[orderID] = order
        return self.standingOrders[orderID]

    def updateStandingOrders(self):
        '''Update tracked order information'''
        raw = self.tapi.getOrders()
        updatedOrders = raw.get('return',{})
        for orderID in self.standingOrders.keys():
            print('Updating tracking for OrderID %s' % (orderID))
            if str(orderID) in updatedOrders.keys():
                print('Found orderID in API response, updating')
                #ordType = type(orderID)
                #print('orderId type is: %s' % (ordType))
                #print('Updated Orders: %s' % (updatedOrders))
                updated = updatedOrders.get(str(orderID))
                #print('updated variable: %s' % (updated))
                order = self.standingOrders.get(orderID)
                #print('order variable: %s' % (order))
                # make sure standing orders includes timestamp
                if order.get('timestamp_created') == None:
                    print('Found no timestamp, updating now')
                    order['timestamp_created'] = updated['timestamp_created']
                order['amount'] = updated['amount']
                self.standingOrders[orderID] = order
            else: #  not found in API response, assume cancelled or filled
                print('Could not find OrderID in API response, incrementing killcount')
                order = self.standingOrders[orderID]
                killcount = order['killcount']
                killcount += 1
                order['killcount'] = killcount
                #print('Order update: killcount check: %s' %(order))
                self.standingOrders[orderID] = order
                if order['killcount'] > 3:
                    self.log.info('Removing order: %s from tracking.' %(orderID))
                    self.log.info('OrderID %s: %s' % (orderID,order))
                    del self.standingOrders[orderID]
        return self.standingOrders

    def killUnfilled(self):
        '''Cancel any tracked order older than configured seconds'''
        orderType = self.config.orderType
        if orderType == 'fokTop' or orderType == 'fokLast':
            now = time.time()
            seconds = self.config.fokTimeout
            for order in self.standingOrders:
                timestamp = self.standingOrders[order].get('timestamp_created',now)
                if now - timestamp > seconds:
                    self.log.info('Cancelling order: %s' % self.standingOrders[order])
                    self.tapi.cancelOrder(order)

class signals(object):
    '''Generate and track signals for trading'''
    def __init__(self,configInstance):
        self.config = configInstance
        self.initSignals()
        self.plot = Plot(self.signalType,self.config.pair,self.config.graphDPI)
        self.log = helper.Log()

    def initSignals(self):
        '''Init instances of signals configured'''
        self.signalType = self.config.signalType
        if self.signalType == 'single':
            self.single = self.createSignal(self.config.single)
        elif self.signalType == 'dual':
            self.slowMA = self.createSignal(self.config.slow)
            self.fastMA = self.createSignal(self.config.fast)
        elif self.signalType == 'ribbon':
            start = self.config.ribbonStart
            step = self.config.ribbonSpacing
            self.rib1 = self.createSignal(start)
            self.rib2 = self.createSignal(start+step)
            self.rib3 = self.createSignal(start+step+step)

    def createSignal(self,reqPoints):
        '''Create an instance of one signal'''
        MAtype = self.config.MAtype
        pair = self.config.pair
        signal = api.MA(pair,MAtype,reqPoints)
        return signal

    def update(self):
        '''Update all existing signal calculations'''
        if self.signalType == 'single':
            self.single.update()
        if self.signalType == 'dual':
            self.slowMA.update()
            self.fastMA.update()
        if self.signalType == 'ribbon':
            self.rib1.update()
            self.rib2.update()
            self.rib3.update()

    def updatePlot(self,price):
        self.plot.append('price',price)
        if self.signalType == 'single':
            single = self.single.value
            self.plot.append('single',single)
            self.printSpread(price,single)
        if self.signalType == 'dual':
            fast = self.fastMA.value
            slow = self.slowMA.value
            self.plot.append('fast',fast)
            self.plot.append('slow',slow)
            self.printSpread(fast,slow)
        if self.signalType == 'ribbon':
            rib1 = self.rib1.value
            rib2 = self.rib2.value
            rib3 = self.rib3.value
            self.plot.append('rib1',rib1)
            self.plot.append('rib2',rib2)
            self.plot.append('rib3',rib3)
            self.printSpread(rib1,rib3)
        self.plot.updatePlot()

    def printSpread(self, fast, slow):
        '''Print the signal gap, for highest and lowest signals'''
        delta = float(fast - slow)/slow # % difference
        spread = delta*100.0
        print('Signal Spread: %.2f' % (spread))+'%'
        self.log.info('Signal Spread: %.2f' % (spread)+'%')
                          
    def checkSignalConfig(self):
        if self.config.signalType == 'single':
            self.singlePoints()
        elif self.config.signalType == 'dual':
            self.dualPoints()
        elif self.config.signalType == 'ribbon':
            self.ribbonPoints()

    def singlePoints(self):
        single = self.config.single
        self.config.updateSignals()
        if single != self.config.single:
            self.single.changeReqPoints(self.config.single)
            log.info('Single MA is now %s' % (self.config.single))

    def dualPoints(self):
        # store current values
        fast = self.config.fast
        slow = self.config.slow
        # update signals section of config
        self.config.updateSignals()
        # check for changes
        if fast != self.config.fast:
            self.fastMA.changeReqPoints(self.config.fast)
            log.info('fastMA is now %s' % (self.config.fast))
        if oldslow != config.slow:
            self.slowMA.changeReqPoints(self.config.slow)
            log.info('slowMA is now %s' % (self.config.slow))

    def ribbonPoints(self):
        start = self.config.ribbonStart
        step = self.config.ribbonSpacing
        self.config.updateSignals()
        if start != self.config.ribbonStart or step != self.config.ribbonSpacing:
            self.rib1.changeReqPoints(start)
            self.rib2.changeReqPoints(start+step)
            self.rib3.changeReqPoints(start+step+step)
            log.info('Ribbon start: %s, spacing: %s' %(self.config.ribbonStart,
                                                       self.config.ribbonSpacing))
                     
class Plot(object):
    '''Plot and save graph of moving averages and price'''
    def __init__(self,signalType,pair,graphDPI):
        # todo: add subplot for oscillator
        self.plotType = signalType
        self.pair = pair #  for graph title
        self.DPI = graphDPI
        self.graph = pylab.figure()
        pylab.rcParams.update({'legend.labelspacing':0.25,
                               'legend.fontsize':'x-small'})
        # create dict with linestyles for each configured line
        self.build()
        
    def build(self):
        self.toPlot = {}
        self.toPlot['price'] = {'label':'Price','color':'k','style':'-'}
        if self.plotType == 'single':
            self.toPlot['single'] = {'label':'MA','color':'g','style':':'}
        elif self.plotType == 'dual':
            self.toPlot['fast'] = {'label':'Fast MA','color':'r','style':':'}
            self.toPlot['slow'] = {'label':'Slow MA','color':'b','style':':'}
        elif self.plotType == 'ribbon':
            self.toPlot['rib1'] = {'label':'Fast MA','color':'r','style':':'}
            self.toPlot['rib2'] = {'label':'Mid MA','color':'m','style':':'}
            self.toPlot['rib3'] = {'label':'Slow MA','color':'b','style':':'}

    def changeDPI(self,DPI):
        self.DPI = DPI
        
    def append(self,line,value):
        '''Append new point to specified line['values'] in toPlot dict'''
        self.toPlot[line].setdefault('values', []).append(value)

    def updatePlot(self):
        '''Clear, re-draw, and save.
        Allows viewing "real-time" as an image
        '''
        # clear figure and axes
        pylab.clf()
        pylab.cla()
        pylab.grid(True, axis='y', linewidth=1, color='gray', linestyle='--')
        # plot each line
        for line in self.toPlot:
            values = self.toPlot[line].get('values')
            label = self.toPlot[line].get('label')
            color = self.toPlot[line].get('color')
            style = self.toPlot[line].get('style')
            #print values,label,color,style
            pylab.plot(values, label=label, color=color, linestyle=style)
        ylims = self.getYlims() 
        pylab.ylim(ylims)
        # labels
        pylab.title("Moving Averages against Price of %s" % self.pair)
        pylab.xlabel("Ticks")
        pylab.ylabel("Price")
        # legend top-left
        pylab.legend(loc=2)
        # save and close
        pylab.savefig('graph.png',dpi=self.DPI)
        pylab.close(self.graph)

    def getYlims(self):
        '''
        Create plot limits from min,max in plot lists,
        with 0.1% buffer added to top and bottom of graph
        '''
        maxList = []
        minList = []
        for line in self.toPlot:
            values = self.toPlot[line].get('values')
            maxList.append(max(values))
            minList.append(min(values))
        ymax = max(maxList)
        ymax = round(ymax+(ymax*0.001),2) #  0.1% buffer
        ymin = min(minList)
        ymin = round(ymin-(ymin*0.001),2)
        ylims = (ymin,ymax)
        return ylims
    
# Python is awesome

########NEW FILE########
