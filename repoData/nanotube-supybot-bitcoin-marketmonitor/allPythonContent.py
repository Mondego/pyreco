__FILENAME__ = config
###
# Copyright (c) 2010, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot import ircutils
import re

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('BitcoinCentralMonitor', True)

class Channel(registry.String):
    def setValue(self, v):
        if not ircutils.isChannel(v):
            self.error()
        else:
            super(Channel, self).setValue(v)

class CommaSeparatedListOfChannels(registry.SeparatedListOf):
    Value = Channel
    def splitter(self, s):
        return re.split(r'\s*,\s*', s)
    joiner = ', '.join

BitcoinCentralMonitor = conf.registerPlugin('BitcoinCentralMonitor')

conf.registerGlobalValue(BitcoinCentralMonitor, 'channels',
    CommaSeparatedListOfChannels("", """List of channels that should
    receive monitoring output."""))
conf.registerGlobalValue(BitcoinCentralMonitor, 'pollinterval',
    registry.PositiveInteger(10, """Seconds between BitcoinCentral site polls."""))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2010, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot import ircmsgs

import threading
import time
import json

class BitcoinCentralMonitor(callbacks.Plugin):
    """This plugin monitors the BitcoinCentral marketplace for activity.

    Use 'start' command to start monitoring, 'stop' command to stop.
    """

    def __init__(self, irc):
        self.__parent = super(BitcoinCentralMonitor, self)
        self.__parent.__init__(irc)
        self.last_checked = time.time()
        #self.depth_dict = {}
        self.e = threading.Event()
        self.started = threading.Event()

    def _monitorBitcoinCentralTrades(self, irc):
        while not self.e.isSet():
            try:
                new_trades = utils.web.getUrl('http://bitcoin-central.net/trades.json')
                new_trades = json.loads(new_trades, parse_float=str, parse_int=str)
            except:
                continue # let's just try again.
            checked = self.last_checked
            #new_depth = utils.web.getUrl('http://bitcoin-central.net/account/trade_orders/book.json')
            #new_depth = json.loads(new_depth, parse_float=str, parse_int=str)
            # ticker: http://bitcoin-central.net/trades/ticker.json
            for trade in new_trades:
                if float(trade['date']) > checked:
                    checked = float(trade['date'])
                if float(trade['date']) > self.last_checked:
                    out = "BC |%10s|%5s%22s @ %s" % \
                          ('TRADE',
                           trade['currency'],
                           trade['amount'],
                           '$' + trade['price'])
                    out = ircutils.bold(out)
                    for chan in self.registryValue('channels'):
                        irc.queueMsg(ircmsgs.privmsg(chan, out))
            self.last_checked = checked
            time.sleep(self.registryValue('pollinterval'))
        self.started.clear()

    def start(self, irc, msg, args):
        """Start monitoring BitcoinCentral data."""
        if not self.started.isSet():
            self.e.clear()
            self.started.set()
            t = threading.Thread(target=self._monitorBitcoinCentralTrades,
                                 kwargs={'irc':irc})
            t.start()
            irc.reply("Monitoring start successful. Now reporting BitcoinCentral trades.")
        else:
            irc.error("Monitoring already started.")
    start = wrap(thread(start))

    def stop(self, irc, msg, args):
        irc.reply("Stopping BitcoinCentral monitoring.")
        self.e.set()
    stop = wrap(stop)

    def test(self, irc, msg, args):
        """Test connectivity by setting last_checked in the past."""
        irc.reply("Resetting last_checked.")
        self.last_checked = 1
    test = wrap(test, ['owner'])

    def die(self):
        self.e.set()
        self.__parent.die()



Class = BitcoinCentralMonitor


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2010, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class BitcoinCentralMonitorTestCase(PluginTestCase):
    plugins = ('BitcoinCentralMonitor',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2012, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('BitcoinData', True)


BitcoinData = conf.registerPlugin('BitcoinData')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(BitcoinData, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2012, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot import utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

from urllib2 import urlopen
import json
import re
import time
import math
import urllib2

opener = urllib2.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0 (X11; Linux x86_64; rv:22.0) Gecko/20100101 Firefox/22.0')]
urllib2.install_opener(opener)

def getPositiveFloat(irc, msg, args, state, type='positiveFloat'):
    v = args[0]
    try:
        v1 = float(v)
        if v1 <= 0:
            state.errorInvalid(type, args[0])
            return
    except:
        state.errorInvalid(type, args[0])
        return
    state.args.append(v1)
    del args[0]
    
addConverter('positiveFloat', getPositiveFloat)

class BitcoinData(callbacks.Plugin):
    """Includes a bunch of commands to retrieve or calculate various
    bits of data relating to bitcoin and the blockchain."""
    threaded = True

    def _grabapi(self, apipaths):
        sources = ['http://blockchain.info','http://blockexplorer.com', ]
        urls = [''.join(t) for t in zip(sources, apipaths)]
        for url in urls:
            try:
                data = urlopen(url, timeout=5).read()
                return data
            except:
                continue
        else:
            return None

    def _blocks(self):
        data = self._grabapi(['/q/getblockcount']*2)
        return data

    def blocks(self, irc, msg, args):
        '''takes no arguments
        
        Get current block count.'''
        data = self._blocks()
        if data is None or data == '':
            irc.error("Failed to retrieve data. Try again later.")
            return
        irc.reply(data)
    blocks = wrap(blocks)
        
    def _rawblockbyhash(self, blockhash):
        data = self._grabapi(['/rawblock/%s' % blockhash]*2)
        return data
        
    def _rawblockbynum(self, blocknum):
        try:
            data = urlopen('http://blockexplorer.com/b/%s' % blocknum, timeout=5).read()
            m = re.search(r'href="(/rawblock/[0-9a-f]+)"', data)
            bbeurl = m.group(1)
        except:
            bbeurl = 'doesnotexist'
        data = self._grabapi(['/block-height/%s?format=json' % blocknum, bbeurl, ])
        try:
            j = json.loads(data)
            if 'blocks' in j.keys():
                j = j['blocks'][0]
            return j
        except:
            return None

    def _blockdiff(self, blocknum):
        block = self._rawblockbynum(blocknum)
        try:
            diffbits = block['bits']
            hexbits = hex(diffbits)
            target = int(hexbits[4:], 16) * 2 ** (8 * (int(hexbits[2:4], 16) - 3))
            maxtarget = float(0x00000000FFFF0000000000000000000000000000000000000000000000000000)
            diff = maxtarget / target
            return diff
        except:
            return None

    def blockdiff(self, irc, msg, args, blocknum):
        '''<block number>
        
        Get difficulty for specified <block number>.'''
        #data = self._grabapi(['b/%s' % blocknum, 'rawblock/%s' % blocknum])
        # first, let's try to grab from bbe, we need blockhash first
        diff = self._blockdiff(blocknum)
        if diff is None:
            irc.error("Failed to retrieve data. Try again later.")
            return
        irc.reply(diff)
    blockdiff = wrap(blockdiff, ['positiveInt'])

    def _diff(self):
        data = self._grabapi(['/q/getdifficulty']*2)
        return data

    def diff(self, irc, msg, args):
        '''takes no arguments
        
        Get current difficulty.'''
        data = self._diff()
        if data is None or data == '':
            irc.error("Failed to retrieve data. Try again later.")
            return
        irc.reply(data)
    diff = wrap(diff)

    def _hextarget(self, blocknum):
        block = self._rawblockbynum(blocknum)
        try:
            diffbits = block['bits']
            hexbits = hex(diffbits)
            target = int(hexbits[4:], 16) * 2 ** (8 * (int(hexbits[2:4], 16) - 3))
            target = hex(target)[2:-1]
            target = '0'*(64-len(target)) + target
            return target.upper()
        except:
            return None

    def hextarget(self, irc, msg, args, blocknum):
        '''[<block number>]
        
        get the hex target for current block.
        if optional block number is provided, get hex target for that block height.
        '''
        if blocknum is None:
            blocknum = self._blocks()
        target = self._hextarget(blocknum)
        if target is None:
            irc.error("Failed to retrieve data. Try again later.")
            return
        irc.reply(target)
    hextarget = wrap(hextarget, [optional('positiveInt')])

    def _bounty(self):
        data = self._grabapi(['/q/bcperblock']*2)
        try:
            if int(data) > 50:
                return int(data) / 100000000
            else:
                return int(data)
        except:
            return None

    def bounty(self, irc, msg, args):
        '''takes no arguments
        
        Get current block bounty.'''
        data = self._bounty()
        if data is None or data == '':
            irc.error("Failed to retrieve data. Try again later.")
            return
        irc.reply(data)
    bounty = wrap(bounty)

    def _gentime(self, hashrate, difficulty):
        gentime = 2**48/65535*difficulty/hashrate/1000000
        return gentime

    def gentime(self, irc, msg, args, hashrate, difficulty):
        '''<hashrate> [<difficulty>]
        
        Calculate expected time to generate a block using <hashrate> Mhps,
        at current difficulty. If optional <difficulty> argument is provided, expected
        generation time is for supplied difficulty.
        '''
        if difficulty is None:
            try:
                difficulty = float(self._diff())
            except:
                irc.error("Failed to fetch current difficulty. Try again later or supply difficulty manually.")
                return
        gentime = self._gentime(hashrate, difficulty)
        irc.reply("The average time to generate a block at %s Mhps, given difficulty of %s, is %s" % \
                (hashrate, difficulty, utils.timeElapsed(gentime)))
    gentime = wrap(gentime, ['positiveFloat', optional('positiveFloat')])

    def genrate(self, irc, msg, args, hashrate, difficulty):
        '''<hashrate> [<difficulty>]
        
        Calculate expected bitcoin generation rate using <hashrate> Mhps,
        at current difficulty. If optional <difficulty> argument is provided, expected
        generation time is for supplied difficulty.
        '''
        if difficulty is None:
            try:
                difficulty = float(self._diff())
            except:
                irc.error("Failed to retrieve current difficulty. Try again later or supply difficulty manually.")
                return
        gentime = self._gentime(hashrate, difficulty)
        try:
            bounty = float(self._bounty())
        except:
            irc.error("Failed to retrieve current block bounty. Try again later.")
            return
        irc.reply("The expected generation output, at %s Mhps, given difficulty of %s, is %s BTC "
                "per day and %s BTC per hour." % (hashrate, difficulty,
                            bounty*24*60*60/gentime,
                            bounty * 60*60/gentime))
    genrate = wrap(genrate, ['positiveFloat', optional('positiveFloat')])

    def tslb(self, irc, msg, args):
        """takes no arguments
        
        Shows time elapsed since latest generated block.
        This uses the block timestamp, so may be slightly off clock-time.
        """
        blocknum = self._blocks()
        block = self._rawblockbynum(blocknum)
        try:
            blocktime = block['time']
            irc.reply("Time since last block: %s" % utils.timeElapsed(time.time() - blocktime))
        except:
            irc.error("Problem retrieving latest block data.")
    tslb = wrap(tslb)
    
    def _nethash3d(self):
        try:
            estimate = urlopen('http://bitcoin.sipa.be/speed-3D.txt').read()
            estimate = float(estimate)
        except:
            estimate = None
        return estimate
    
    def _nethashsincelast(self):
        try:
            estimate = urlopen('http://blockexplorer.com/q/estimate').read()
            estimate = float(estimate) / 139.696254564
        except:
            estimate = None
        return estimate
    
    def nethash(self, irc, msg, args):
        '''takes no arguments
        
        Shows the current estimate for total network hash rate, in Ghps.
        '''
        data = self._nethash3d()
        if data is None:
            data = self._nethashsincelast()
        if data is None:
            irc.error("Failed to retrieve data. Try again later.")
            return
        irc.reply(data)
    nethash = wrap(nethash)

    def diffchange(self, irc, msg, args):
        """takes no arguments
        
        Shows estimated percent difficulty change.
        """
        currdiff = self._diff()
        try:
            diff3d = self._nethash3d() * 139.696254564
            diff3d = round(100*(diff3d/float(currdiff) - 1), 5)
        except:
            diff3d = None
        try:
            diffsincelast = self._nethashsincelast() * 139.696254564
            diffsincelast = round(100*(diffsincelast/float(currdiff) - 1), 5)
        except:
            diffsincelast = None
        irc.reply("Estimated percent change in difficulty this period | %s %% based on data since last change | %s %% based on data for last three days" % (diffsincelast, diff3d))
    diffchange = wrap(diffchange)
    
    def estimate(self, irc, msg, args):
        """takes no arguments
        
        Shows next difficulty estimate.
        """
        try:
            diff3d = self._nethash3d() * 139.696254564
        except:
            diff3d = None
        try:
            diffsincelast = self._nethashsincelast() * 139.696254564
        except:
            diffsincelast = None
        irc.reply("Next difficulty estimate | %s based on data since last change | %s based on data for last three days" % (diffsincelast, diff3d))
    estimate = wrap(estimate)

    def totalbc(self, irc, msg, args):
        """takes no arguments
        
        Return total number of bitcoins created thus far.
        """
        try:
            blocks = int(self._blocks()) + 1 # offset for block0
        except:
            irc.error("Failed to retrieve block count. Try again later.")
            return
        bounty = 50.
        chunk = 210000
        total = 0.
        while blocks > chunk:
            total += chunk * bounty
            blocks -= 210000
            bounty /= 2.
        if blocks > 0:
            total += blocks * bounty
        irc.reply("%s" % total)
    totalbc = wrap(totalbc)

    def halfreward(self, irc, msg, args):
        """takes no arguments
        
        Show estimated time of next block bounty halving.
        """
        try:
            blocks = int(self._blocks())
        except:
            irc.error("Failed to retrieve block count. Try again later.")
            return
        halfpoint = 210000
        while halfpoint < blocks:
            halfpoint += 210000
        blocksremaining = halfpoint - blocks
        sectohalve = blocksremaining * 10 * 60
        irc.reply("Estimated time of bitcoin block reward halving: %s UTC | Time remaining: %s." % \
                (time.asctime(time.gmtime(time.time() + sectohalve)), utils.timeElapsed(sectohalve)))
    halfreward = wrap(halfreward)

    def _nextretarget(self):
        data = self._grabapi(['/q/nextretarget']*2)
        return data
        
    def nextretarget(self, irc, msg, args):
        """takes no arguments
        
        Shows the block number at which the next difficulty change will take place.
        """
        data = self._nextretarget()
        if data is None or data == '':
            irc.error("Failed to retrieve data. Try again later.")
            return
        irc.reply(data)
    nextretarget = wrap(nextretarget)

    def _prevdiff(self):
        blocks = int(self._blocks())
        prevdiff = self._blockdiff(blocks - 2016)
        return prevdiff
        
    def prevdiff(self, irc, msg, args):
        """takes no arguments
        
        Shows the previous difficulty level.
        """
        data = self._prevdiff()
        if data is None or data == '':
            irc.error("Failed to retrieve data. Try again later.")
            return
        irc.reply(data)
    prevdiff = wrap(prevdiff)
    
    def prevdiffchange(self, irc, msg, args):
        """takes no arguments
        
        Shows the percentage change from previous to current difficulty level.
        """
        try:
            prevdiff = float(self._prevdiff())
            diff = float(self._diff())
        except:
            irc.error("Failed to retrieve data. Try again later.")
            return
        irc.reply("%s" % (round((diff / prevdiff - 1) * 100, 5), ))
    prevdiffchange = wrap(prevdiffchange)

    def _interval(self):
        data = self._grabapi(['/q/interval']*2)
        return data
        
    def interval(self, irc, msg, args):
        """takes no arguments
        
        Shows average interval, in seconds, between last 1000 blocks.
        """
        data = self._interval()
        if data is None or data == '':
            irc.error("Failed to retrieve data. Try again later.")
            return
        irc.reply(data)
    interval = wrap(interval)

    def _timetonext(self):
        try:
            interval = float(self._interval())
            blocks = float(self._blocks())
            retarget = float(self._nextretarget())
            return (retarget - blocks)*interval
        except:
            return None

    def timetonext(self, irc, msg, args):
        """takes no arguments
        
        Show estimated time to next difficulty change.
        """
        data = self._timetonext()
        if data is None:
            irc.error("Failed to retrieve data. Try again later.")
            return
        irc.reply("%s" % data)
    timetonext = wrap(timetonext)

    def bcstats(self, irc, msg, args):
        """takes no arguments
        
        Shows a number of statistics about the state of the block chain.
        """
        blocks = self._blocks()
        diff = self._diff()
        try:
            estimate = self._nethashsincelast() * 139.696254564
        except:
            estimate = None
        try:
            diffchange = round((estimate/float(diff) - 1)  * 100, 5)
        except:
            diffchange = None
        nextretarget = self._nextretarget()
        try:
            blockstoretarget = int(nextretarget) - int(blocks)
        except:
            blockstoretarget = None
        try:
            timetonext = utils.timeElapsed(self._timetonext())
        except:
            timetonext = None        
        
        irc.reply("Current Blocks: %s | Current Difficulty: %s | "
                "Next Difficulty At Block: %s | "
                "Next Difficulty In: %s blocks | "
                "Next Difficulty In About: %s | "
                "Next Difficulty Estimate: %s | "
                "Estimated Percent Change: %s" % (blocks, diff, 
                        nextretarget, blockstoretarget, timetonext, 
                        estimate, diffchange))
    bcstats = wrap(bcstats)

#math calc 1-exp(-$1*1000 * [seconds $*] / (2**32* [bc,diff]))

    def _genprob(self, hashrate, interval, difficulty):
        genprob = 1-math.exp(-hashrate*1000000 * interval / (2**32* difficulty))
        return genprob

    def genprob(self, irc, msg, args, hashrate, interval, difficulty):
        '''<hashrate> <interval> [<difficulty>]
        
        Calculate probability to generate a block using <hashrate> Mhps,
        in <interval> seconds, at current difficulty.
        If optional <difficulty> argument is provided, probability is for supplied difficulty.
        To provide the <interval> argument, a nested 'seconds' command may be helpful.
        '''
        if difficulty is None:
            try:
                difficulty = float(self._diff())
            except:
                irc.error("Failed to current difficulty. Try again later or supply difficulty manually.")
                return
        gp = self._genprob(hashrate, interval, difficulty)
        irc.reply("The probability to generate a block at %s Mhps within %s, given difficulty of %s, is %s" % \
                (hashrate, utils.timeElapsed(interval), difficulty, gp))
    genprob = wrap(genprob, ['positiveFloat', 'positiveInt', optional('positiveFloat')])

    def tblb(self, irc, msg, args, interval):
        """<interval>
        
        Calculate the expected time between blocks which take at least
        <interval> seconds to create.
        To provide the <interval> argument, a nested 'seconds' command may be helpful.
        """
        try:
            difficulty = float(self._diff())
            nh = float(self._nethash3d())
            gp = self._genprob(nh*1000, interval, difficulty)
        except:
            irc.error("Problem retrieving data. Try again later.")
            return
        sblb = (difficulty * 2**48 / 65535) / (nh * 1e9) / (1 - gp)
        irc.reply("The expected time between blocks taking %s to generate is %s" % \
                (utils.timeElapsed(interval), utils.timeElapsed(sblb),))
    tblb = wrap(tblb, ['positiveInt'])


Class = BitcoinData


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2012, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class BitcoinDataTestCase(PluginTestCase):
    plugins = ('BitcoinData',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2013, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('BotBackup', True)


BotBackup = conf.registerPlugin('BotBackup')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(BotBackup, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))

conf.registerGlobalValue(BotBackup, 'precedentBotNicks',
    registry.SpaceSeparatedListOfStrings([], """List of bot nicks which
    have precedence over this bot instance. The bot will remain silent
    on channels unless none of the nicks in this list are present."""))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2013, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


class BotBackup(callbacks.Plugin):
    """This plugin lets you run a live instance of a backup bot. It will keep
    the backup bot silent unless all the precedent bots are offline."""
    threaded=True

    def inFilter(self, irc, msg):
        quiet = False
        if irc.isChannel(msg.args[0]):
            for pn in self.registryValue('precedentBotNicks'):
                if pn in irc.state.channels[msg.args[0]].users:
                    quiet = True
                    break
        if quiet:
            return None
        return msg

Class = BotBackup


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2013, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class BotBackupTestCase(PluginTestCase):
    plugins = ('BotBackup',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2011, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Gatekeeper', True)


Gatekeeper = conf.registerPlugin('Gatekeeper')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Gatekeeper, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))

conf.registerGlobalValue(Gatekeeper, 'targetChannel',
    registry.String("#bitcoin-otc", """Target channel for gatekeeper
    management"""))

conf.registerGlobalValue(Gatekeeper, 'ratingThreshold',
    registry.NonNegativeInteger(0, """Minimum rating to be allowed in."""))

conf.registerGlobalValue(Gatekeeper, 'accountAgeThreshold',
    registry.PositiveInteger(604800, """Minimum account age, in seconds,
    to be allowed in."""))

conf.registerGlobalValue(Gatekeeper, 'invite',
    registry.Boolean(False, """Should the bot invite the user to channel?"""))

conf.registerGlobalValue(Gatekeeper, 'msgOnJoinVoice',
    registry.String("Join #bitcoin-otc-foyer and see channel topic for instructions on getting voice on #bitcoin-otc.",
    """Message to send to unauthed users with instructions on 
    how to get voice in channel."""))

conf.registerGlobalValue(Gatekeeper, 'msgOnJoinIdent',
    registry.String("#bitcoin-otc: \x02Watch out for fraudsters!\x02 Always check authentication with the \x02ident\x02 command before trading, otherwise you could be dealing with an \x02impostor\x02. If in doubt, ask in channel. More info: http://bit.ly/YCGOI3",
    """Message to send to unauthed users with instructions on 
    checking auth and avoiding fraudsters."""))

conf.registerGlobalValue(Gatekeeper, 'talkInChanOnlyForAuthedUsers',
    registry.Boolean(True, """Should the bot only respond in channel for
    authed users?"""))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot import ircmsgs
import time
from supybot import world

class Gatekeeper(callbacks.Plugin):
    """Lets you into #bitcoin-otc, if you're authenticated and
    meet minimum requirements."""
    threaded = True

    def _checkGPGAuth(self, irc, prefix):
        return irc.getCallback('GPG')._ident(prefix)

    def _getGPGInfo(self, irc, nick):
        return irc.getCallback('GPG')._info(nick)

    def _getCumulativeRating(self, irc, nick):
        return irc.getCallback('RatingSystem')._getrating(nick)

    def _gettrust(self, irc, sourcenick, destnick):
        return irc.getCallback('RatingSystem')._gettrust(sourcenick, destnick)

    def outFilter(self, irc, msg):
        if msg.command == 'PRIVMSG' and \
                self.registryValue('talkInChanOnlyForAuthedUsers') and \
                msg.args[0] == self.registryValue('targetChannel') and \
                msg.inReplyTo is not None: # 'say' msgs don't have an inReplyTo
            gpgauth = self._checkGPGAuth(irc, msg.inReplyTo.prefix)
            if gpgauth is None:
                msg = ircmsgs.privmsg(msg.inReplyTo.nick, msg.args[1], msg=msg)
        return msg

    def letmein(self, irc, msg, args):
        """takes no arguments
        
        Gives you voice on #bitcoin-otc if you qualify.
        Also invites you if needed.
        """
        gpgauth = self._checkGPGAuth(irc, msg.prefix)
        if gpgauth is None:
            irc.error("You must authenticate via GPG to use this command.")
            return
        if msg.nick in irc.state.channels[self.registryValue('targetChannel')].voices:
            irc.error("You already have voice in %s." % (self.registryValue('targetChannel'),))
            return
        info = self._getGPGInfo(irc, gpgauth['nick'])
        if info is not None:
            regtimestamp = info[4]
        else:
            # this should not happen
            irc.error("No info on your user in the database.")
            return
        trust_nanotube = self._gettrust(irc, 'nanotube', gpgauth['nick'])
        trust_keefe = self._gettrust(irc, 'keefe', gpgauth['nick'])
        mintrust = min(trust_nanotube[0][0] + trust_nanotube[1][0], 
                trust_keefe[0][0] + trust_keefe[1][0])
        if mintrust >= self.registryValue('ratingThreshold') and \
                    time.time() - regtimestamp > self.registryValue('accountAgeThreshold'):
            if msg.nick not in irc.state.channels[self.registryValue('targetChannel')].users and \
                        self.registryValue('invite'):
                irc.queueMsg(ircmsgs.invite(msg.nick, self.registryValue('targetChannel')))
                irc.reply("You have been invited to %s. Type '/j %s' to enter the channel." % (self.registryValue('targetChannel'), self.registryValue('targetChannel'),))
            if msg.nick in irc.state.channels[self.registryValue('targetChannel')].users:
                irc.queueMsg(ircmsgs.voice(self.registryValue('targetChannel'), msg.nick))
                irc.noReply()
        else:
            irc.error("Insufficient account age or rating. Required minimum account age is %s days, and required minimum trust is %s. Yours are %s days and %s, respectively." % (self.registryValue('accountAgeThreshold')/60/60/24, self.registryValue('ratingThreshold'),(time.time() - regtimestamp)/60/60/24, mintrust))
    letmein = wrap(letmein)
    voiceme = letmein

    def doJoin(self, irc, msg):
        """give voice to users that join and meet requirements."""
        if msg.args[0] != self.registryValue('targetChannel') or irc.network != 'freenode':
            return
        if msg.nick == irc.nick: # ignore our own join msgs.
            return

        gpgauth = self._checkGPGAuth(irc, msg.prefix)
        if gpgauth is None:
            try:
                if (not world.testing) and self.registryValue('msgOnJoinVoice') != "" and msg.nick not in irc.state.channels['#bitcoin-otc-foyer'].users:
                    irc.queueMsg(ircmsgs.privmsg(msg.nick, self.registryValue('msgOnJoinVoice')))
            except KeyError:
                pass
            if (not world.testing) and self.registryValue('msgOnJoinIdent') != "":
                irc.queueMsg(ircmsgs.privmsg(msg.nick, self.registryValue('msgOnJoinIdent')))
            return

        info = self._getGPGInfo(irc, gpgauth['nick'])
        if info is not None:
            regtimestamp = info[4]
        else:
            # this should not happen
            return
        trust_nanotube = self._gettrust(irc, 'nanotube', gpgauth['nick'])
        trust_keefe = self._gettrust(irc, 'keefe', gpgauth['nick'])
        mintrust = min(trust_nanotube[0][0] + trust_nanotube[1][0], 
                trust_keefe[0][0] + trust_keefe[1][0])
        if mintrust >= self.registryValue('ratingThreshold') and \
                time.time() - regtimestamp > self.registryValue('accountAgeThreshold'):
            irc.queueMsg(ircmsgs.voice('#bitcoin-otc', msg.nick))

Class = Gatekeeper


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2011, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *
from supybot import ircmsgs

class GatekeeperTestCase(PluginTestCase):
    plugins = ('Gatekeeper','RatingSystem','GPG','Admin')
    
    def setUp(self):
        PluginTestCase.setUp(self)

        #preseed the GPG db with a GPG registration and auth for nanotube
        gpg = self.irc.getCallback('GPG')
        gpg.db.register('AAAAAAAAAAAAAAA1', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA1',
                    '1somebitcoinaddress', time.time() - 1000000, 'nanotube')
        gpg.authed_users['nanotube!stuff@stuff/somecloak'] = {'nick':'nanotube'}
        gpg.db.register('AAAAAAAAAAAAAAA2', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA2',
                    '1somebitcoinaddress', time.time(), 'registeredguy')
        gpg.db.register('AAAAAAAAAAAAAAA7', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA7',
                    '1somebitcoinaddress', time.time(), 'youngguy')
        gpg.authed_users['youngguy!stuff@123.345.234.34'] = {'nick':'youngguy'}
        gpg.db.register('AAAAAAAAAAAAAAA3', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA3',
                    '1somebitcoinaddress', time.time() - 1000000, 'authedguy')
        gpg.authed_users['authedguy!stuff@123.345.234.34'] = {'nick':'authedguy'}
        gpg.db.register('AAAAAAAAAAAAAAA4', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA4',
                    '1somebitcoinaddress', time.time() - 1000000, 'authedguy2')
        gpg.authed_users['authedguy2!stuff@123.345.234.34'] = {'nick':'authedguy2'}

        # pre-seed the rating db with some ratings
        cb = self.irc.getCallback('RatingSystem')
        cursor = cb.db.db.cursor()
        cursor.execute("""INSERT INTO users VALUES
                          (NULL, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (10, time.time(), 1, 0, 0, 0, 'nanotube','stuff/somecloak'))
        cursor.execute("""INSERT INTO users VALUES
                          (NULL, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (10, time.time(), 1, 0, 0, 0, 'Keefe','stuff/somecloak'))
        cursor.execute("""INSERT INTO users VALUES
                          (NULL, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (10, time.time(), 1, 0, 0, 0, 'authedguy','stuff/somecloak'))
        cursor.execute("""INSERT INTO users VALUES
                          (NULL, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (-10, time.time(), 1, 0, 0, 0, 'authedguy2','stuff/somecloak'))
        cursor.execute("""INSERT INTO ratings VALUES
                        (NULL, ?, ?, ?, ?, ?)""",
                        (3, 1, time.time(), 1, "some notes",)) # nanotube rates authedguy
        cursor.execute("""INSERT INTO ratings VALUES
                        (NULL, ?, ?, ?, ?, ?)""",
                        (2, 1, time.time(), 9, "some notes",)) # nanotube rates keefe
        cursor.execute("""INSERT INTO ratings VALUES
                        (NULL, ?, ?, ?, ?, ?)""",
                        (3, 2, time.time(), 2, "some notes",)) # keefe rates authedguy
        cursor.execute("""INSERT INTO ratings VALUES
                        (NULL, ?, ?, ?, ?, ?)""",
                        (4, 2, time.time(), -5, "some notes",)) # keefe rates authedguy2

        cb.db.db.commit()

    def testLetmein(self):
        def getAfterJoinMessages():
            m = self.irc.takeMsg()
            self.assertEqual(m.command, 'MODE')
            m = self.irc.takeMsg()
            self.assertEqual(m.command, 'WHO')
        self.irc.feedMsg(ircmsgs.join('#bitcoin-otc', prefix=self.prefix))
        getAfterJoinMessages()
        try:
            orignetwork = self.irc.network
            self.irc.network = 'freenode'
            origuser = self.prefix
            self.prefix = 'registeredguy!stuff@123.345.234.34'
            self.assertError('letmein') # not authed
            self.irc.feedMsg(ircmsgs.join('#bitcoin-otc', prefix=self.prefix))
            self.irc.takeMsg()
            self.assertTrue('registeredguy' not in self.irc.state.channels['#bitcoin-otc'].voices)
            self.prefix = 'youngguy!stuff@123.345.234.34'
            self.assertError('letmein') # not enough account age
            self.irc.feedMsg(ircmsgs.join('#bitcoin-otc', prefix=self.prefix))
            self.irc.takeMsg()
            self.assertTrue('youngguy' not in self.irc.state.channels['#bitcoin-otc'].voices)
            self.prefix = 'authedguy2!stuff@123.345.234.34'
            self.assertError('letmein') # negative rating
            self.irc.feedMsg(ircmsgs.join('#bitcoin-otc', prefix=self.prefix))
            self.irc.takeMsg()
            self.assertTrue('authedguy2' not in self.irc.state.channels['#bitcoin-otc'].voices)
            self.prefix = 'authedguy!stuff@123.345.234.34'
            self.assertNotError('letmein') # should be good
            self.irc.feedMsg(ircmsgs.join('#bitcoin-otc', prefix=self.prefix))
            self.irc.takeMsg()
            self.assertTrue('authedguy' in self.irc.state.channels['#bitcoin-otc'].voices)
        finally:
            self.irc.network = orignetwork
            self.prefix = origuser


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# GPG - supybot plugin to authenticate users via GPG keys
# Copyright (C) 2011, Daniel Folkinshteyn <nanotube@users.sourceforge.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('GPG', True)


GPG = conf.registerPlugin('GPG')

conf.registerGlobalValue(GPG, 'authRequestTimeout',
    registry.NonNegativeInteger(300, """Time (seconds) for authentication
    requests to time out."""))
conf.registerGlobalValue(GPG, 'keyservers',
    registry.String("subset.pool.sks-keyservers.net,pgp.mit.edu", """Default keyservers to
    use for key retrieval. Comma-separated list."""))
conf.registerGlobalValue(GPG, 'channels',
    registry.String("#bitcoin-otc", """Channels to monitor for user parts
    for auth removal. Semicolon-separated list."""))
conf.registerGlobalValue(GPG, 'network',
    registry.String("freenode", """Network to monitor for user parts/quits
    and bot quits for auth removal."""))
conf.registerGlobalValue(GPG, 'pastebinWhitelist',
    registry.SpaceSeparatedListOfStrings(['http://pastebin.com','http://paste.debian.net'], 
    """If set, bot will only fetch clearsigned data
    for the verify command from urls in the whitelist, i.e. starting with
    http://domain/optionalpath/."""))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = bitcoin-otc-gpg-eauth-pidgin
#!/usr/bin/env python

#
# Azelphur's quick and ugly Bitcoin-OTC Pidgin auto auth script
# Usage: run the script, enter your GPG password, type ;;eauth YourNick, be happy.
# License: GPL
#
# You must also have the python-gnupg module.
# Get it from http://code.google.com/p/python-gnupg/

VOICEME = True # You can change this if you like

import dbus
import gobject
import re
import urllib2
import gnupg
import sys
from getpass import getpass
from dbus.mainloop.glib import DBusGMainLoop

class PidginOTC:
    def __init__(self):
        self.msg = re.compile('^Request successful for user .+?, hostmask .+. Get your encrypted OTP from (http:\/\/bitcoin-otc.com\/otps\/.+)$')
        self.gpg = gnupg.GPG()
        self.passphrase = getpass("Enter your GPG passphrase: ")
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()
        obj = bus.get_object("im.pidgin.purple.PurpleService", "/im/pidgin/purple/PurpleObject")
        self.purple = dbus.Interface(obj, "im.pidgin.purple.PurpleInterface")

        bus.add_signal_receiver(self.ReceivedImMsg,
                                dbus_interface="im.pidgin.purple.PurpleInterface",
                                signal_name="ReceivedImMsg")

        loop = gobject.MainLoop()

        loop.run()

    def ReceivedImMsg(self, account, sender, message, conversation, flags):
        if sender == 'gribble':
            match = self.msg.match(message) 
            if match:
                print 'recieved request from gribble, grabbing', match.group(1)
                data = urllib2.urlopen(match.group(1)).read()
                decrypted = str(self.gpg.decrypt(data, passphrase=self.passphrase))
                m = re.search("freenode:#bitcoin-otc:[a-f0-9]{56}", decrypted)
                if m is not None:
                    reply = ";;gpg everify "+m.group(0)
                    print 'replying with', reply
                    self.purple.PurpleConvImSend(self.purple.PurpleConvIm(conversation), reply)
                    if VOICEME:
                        self.purple.PurpleConvImSend(self.purple.PurpleConvIm(conversation), ";;voiceme")
                else:
                    print 'Error: Decrypted message does not contain expected challenge string format.'

PidginOTC()
########NEW FILE########
__FILENAME__ = bitcoin-otc-gpg-eauth-weechat
# -*- coding: utf-8 -*-
# otc-auth - WeeChat script for authenticating to #bitcoin-otc gribble bot
#
#
# Copyright (c) 2013 Your Mother's Favorite Programmer
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Imports
try:
    import requests
except ImportError:
    print 'This script requires the requests module.'
    print 'Get it using: pip-2.7 install requests'
    quit()

import re
import tempfile
import time

try:
    import weechat as w
except ImportError:
    print 'This script must be run under WeeChat.'
    print 'Get WeeChat now at: http://www.weechat.org'
    quit()

# Constants
SCRIPT_NAME = 'otc-auth'
SCRIPT_DESC = 'Authenticate to Gribble Bot in freenode\'s #bitcoin-otc'
SCRIPT_HELP = """%s

Authenticate to gribble in freenode's #bitcoin-otc.
Currently only supports gpg authentication.

Future versions will support bitcoin auth using bitcoin-python.

Requires the shell.py script available at:
    http://www.weechat.org/scripts

""" % SCRIPT_DESC

SCRIPT_AUTHOR = 'Your Mother\'s Favorite Programmer'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_VERSION = '1.1.0'

OTC_URL = 'http://bitcoin-otc.com/otps/{}'
OTC_RE = re.compile(r'http://bitcoin-otc.com/otps/[A-Z0-9]+')

# Default config values
settings = { 'gpg'     : 'yes'   # using gpg auth vs. bitcoin
           , 'pw_to'   : '25'    # no. of secs to allow gpg pw entry
           }


#-----------------------------------------------------------#
#                                                           #
#                      GPG Functions                        #
#                                                           #
#-----------------------------------------------------------#
def get_challenge(gpg_id):
    # Make a request to the site
    r = requests.get(OTC_URL.format(gpg_id))
    
    # Return the text of the GET
    return r.text

def decrypt_challenge(challenge):
    # Use a temporary file for decryption
    with tempfile.NamedTemporaryFile(mode='w+') as tf:
        # Write out the challenge to the file
        tf.write(challenge)

        # Use GPG to decrypt this (df == decrypted file)
        with tempfile.NamedTemporaryFile(mode='w+') as df:
            tf.seek(0)
            cmd = 'gpg --yes --batch -o {} -d {}'.format(df.name, tf.name)
            w.command( ''
                     , '/shell {}'.format(cmd)
                     )
            time.sleep(int(settings['pw_to']))
            df.seek(0)
            result = df.read()

    w.command( ''
             , '/query gribble ;;gpg everify {}'.format(result)
             )

#-----------------------------------------------------------#
#                                                           #
#             WeeChat Functions and Callbacks               #
#                                                           #
#-----------------------------------------------------------#
def otc_auth_cmd(data, buffer, args):
    '''
    Run when /otc-auth is entered into weechat.
    '''
    global settings

    # Obtain the gpg ID 
    if args:
        try:
            nick, pw_to = args.split()

            # Save the pw_to in the settings dict
            settings['pw_to'] = pw_to
        except ValueError:
            nick = args
    else:
        server = w.buffer_get_string(w.current_buffer(), 'localvar_server')
        nick = w.info_get('irc_nick', server)

    # Query gribble for eauth
    # Will open up a new window
    w.command( ''
             , '/query gribble ;;gpg eauth {}'.format(nick)
             ) 

    return w.WEECHAT_RC_OK
    
def priv_msg_cb(data, bufferp, uber_empty, tagsn, isdisplayed,
                ishighlight, prefix, message):
    '''
    Executed when gribble replies back to the ;;gpg eauth command.
    '''
    is_pm = w.buffer_get_string(bufferp, 'localvar_type') == 'private'
    if is_pm:
        # Parse out the gpg_id
        btc_urls = OTC_RE.findall(message)
        if btc_urls:
            # Get the gpg id for fetching the challenge
            gpg_id = btc_urls[0].split('/')[-1]

            # Get the challenge and decrypt it
            decrypt_challenge(get_challenge(gpg_id))

    return w.WEECHAT_RC_OK

#-------------------------#
#                         #
#         MAIN            #
#                         #
#-------------------------#
if __name__ == '__main__':
    # Mandatory register function
    if w.register( SCRIPT_NAME
                 , SCRIPT_AUTHOR
                 , SCRIPT_VERSION
                 , SCRIPT_LICENSE
                 , SCRIPT_DESC
                 , ''
                 , ''
                 ):


        # Check the config value
        for opt, def_val in settings.items():
            if not w.config_is_set_plugin(opt):
                w.config_set_plugin(opt, def_val)
            else:
                # Move the saved config values into the dict
                configp = w.config_get('plugins.var.python.otc-auth.%s' % opt)
                config_val = w.config_string(configp)
                settings[opt] = config_val

        # Create the command
        w.hook_command( 'otc-auth'
                      , 'Authenticate with gribble bot in #bitcoin-otc.'
                      , '[username] [password timeout]'
                      , 'Currently only supports gpg authentication.\n'
                        'Requires a username if the name you auth\n'
                        'with is different from your nick on freenode.\n\n'
                        'Password timeout is the number of seconds you\n'
                        'have to enter in your private key\'s password.\n'
                        'Requires the installation of shell.py:\n'
                        '   /script install shell.py\n\n'
                        'After execution, use Ctrl+L to reset your screen.\n'
                      , ''
                      , 'otc_auth_cmd'
                      , ''
                      )

        # Get notifications of gribble query
        w.hook_print('', 'irc_privmsg', 'http://bitcoin-otc.com', 1, 'priv_msg_cb', '')

########NEW FILE########
__FILENAME__ = bitcoin-otc-gpg-eauth.xchat
__module_name__ = 'OTC Auto Eauth'
__module_version__ = '0.3.0'
__module_description__ = 'Automatic eauth for gribble in Freenode #bitcoin-otc. Version 0.2.0 by nanotube <nanotube@users.sourceforge.net>, based on version 0.1.0 by Delia Eris <asphodelia.erin@gmail.com>.'

###############
# ----USER GUIDE----
#
# This script WILL NOT work 'out of the box'.
# You MUST edit the lines marked below as instructed.
#
# You must also have the python-gnupg module. At a minimum,
# get gnupg.py from http://code.google.com/p/python-gnupg/
# and stick it into your .xchat2 directory next to this plugin.
# Or just install it with its setup.py in the usual python fashion.
#
# To initiate authentication, run command /eauth
# Enter your GPG passphrase into the prompt box (blank if none)
# Enjoy being authenticated!
# 
# License: CC0. Attribution is cool, plagiarism isn't.
##############

import xchat
import urllib
import sys
import re

print '\0034',__module_name__, __module_version__,'has been loaded.\003'

# Set this to the correct path to your GPG directory.
_gpghome = '/home/YOUR_USERNAME/.gnupg'
# Set this to your OTC nick.
_otcnick = 'OTC_NICK'
# Set to path where you put gnupg.py, if not in default python search path
_gnupgdir = '/home/YOUR_USERNAME/.xchat2/'

sys.path.append(_gnupgdir)
import gnupg

gpg = gnupg.GPG(gnupghome=_gpghome)

def askpw_cb(word, word_eol, userdata):
    pw = word_eol[0]
    xchat.pw = pw[6:]
    if xchat.pw == "":
        xchat.pw = None
    response_data = str(gpg.decrypt(xchat.challenge_data, passphrase = xchat.pw)).rstrip()
    m = re.search("freenode:#bitcoin-otc:[a-f0-9]{56}", response_data)
    if m is not None:
        xchat.command('msg gribble ;;everify '+ m.group(0))
    else:
        print '\0034OTC Eauth Error: Decrypted message does not contain expected challenge string format.\003'
    return xchat.EAT_ALL
xchat.hook_command('ASKPW', askpw_cb, help="/ASKPW Ask user for gpg passphrase.")

def detect_eauth_challenge(word, word_eol, userdata):
    is_challenge = False
    if word[0] == ':gribble!~gribble@unaffiliated/nanotube/bot/gribble' and re.search('hostmask %s!' % (xchat.get_info('nick'),), word_eol[0]):
        challenge_url = word[-1]
        if challenge_url[:-16] == 'http://bitcoin-otc.com/otps/':
            xchat.challenge_data = urllib.urlopen(challenge_url).read()
            xchat.command('GETSTR "your gpg passphrase" ASKPW "Enter gpg passphrase"')
    return xchat.EAT_NONE

xchat.hook_server('PRIVMSG', detect_eauth_challenge)

def eauth_cb(word, word_eol, userdata):
    xchat.command('msg gribble ;;eauth ' + _otcnick)
    return xchat.EAT_ALL
xchat.hook_command('EAUTH', eauth_cb, help="/EAUTH Initiate auth procedure with gribble.")

########NEW FILE########
__FILENAME__ = gpgsigner
#/usr/bin/env python

#
# script to automatically gpg sign a message, upload it to paste.pocoo.org,
# and spit out the raw paste url. very effort-saving! 
#
# usage: 
# python gpgsigner.py yourchallengestringgoeshere
#

from xmlrpclib import ServerProxy
import subprocess
import sys
import StringIO

input = " ".join(sys.argv[1:])

p1 = subprocess.Popen(['gpg','--clearsign'], stdin = subprocess.PIPE, stdout=subprocess.PIPE)
p1.stdin.write(input)
output = p1.communicate()[0]

s = ServerProxy('http://paste.debian.net/server.pl')
rc = s.paste.addPaste(output, 'mygpgauth', 300)
pasteid = rc['id']
print "http://paste.debian.net/plain/%s/" % (pasteid,)
########NEW FILE########
__FILENAME__ = gpgsigner.py3
#/usr/bin/env python

#
# script to automatically gpg sign a message, upload it to paste.pocoo.org,
# and spit out the raw paste url. very effort-saving! 
#
# usage: 
# python gpgsigner.py yourchallengestringgoeshere
#
# original code by nanotube, python 3 port by PLATO

from xmlrpc.client import ServerProxy
import subprocess
import sys
import io

input = " ".join(sys.argv[1:])

p1 = subprocess.Popen(['gpg','--clearsign'], stdin = subprocess.PIPE, stdout=subprocess.PIPE)
p1.stdin.write(bytes(input, 'UTF8'))
output = p1.communicate()[0]

s = ServerProxy('http://paste.pocoo.org/xmlrpc/')
pasteid = s.pastes.newPaste('text',output.decode())
print ("http://paste.pocoo.org/raw/",pasteid,"/", sep="")

########NEW FILE########
__FILENAME__ = bitcoinsig
# the code below is 'borrowed' almost verbatim from electrum,
# https://gitorious.org/electrum/electrum
# and is under the GPLv3.

import ecdsa
import base64
import hashlib
from ecdsa.util import string_to_number

# secp256k1, http://www.oid-info.com/get/1.3.132.0.10
_p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2FL
_r = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141L
_b = 0x0000000000000000000000000000000000000000000000000000000000000007L
_a = 0x0000000000000000000000000000000000000000000000000000000000000000L
_Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798L
_Gy = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8L
curve_secp256k1 = ecdsa.ellipticcurve.CurveFp( _p, _a, _b )
generator_secp256k1 = ecdsa.ellipticcurve.Point( curve_secp256k1, _Gx, _Gy, _r )
oid_secp256k1 = (1,3,132,0,10)
SECP256k1 = ecdsa.curves.Curve("SECP256k1", curve_secp256k1, generator_secp256k1, oid_secp256k1 ) 

addrtype = 0

# from http://eli.thegreenplace.net/2009/03/07/computing-modular-square-roots-in-python/

def modular_sqrt(a, p):
    """ Find a quadratic residue (mod p) of 'a'. p
    must be an odd prime.
    
    Solve the congruence of the form:
    x^2 = a (mod p)
    And returns x. Note that p - x is also a root.
    
    0 is returned is no square root exists for
    these a and p.
    
    The Tonelli-Shanks algorithm is used (except
    for some simple cases in which the solution
    is known from an identity). This algorithm
    runs in polynomial time (unless the
    generalized Riemann hypothesis is false).
    """
    # Simple cases
    #
    if legendre_symbol(a, p) != 1:
        return 0
    elif a == 0:
        return 0
    elif p == 2:
        return p
    elif p % 4 == 3:
        return pow(a, (p + 1) / 4, p)
    
    # Partition p-1 to s * 2^e for an odd s (i.e.
    # reduce all the powers of 2 from p-1)
    #
    s = p - 1
    e = 0
    while s % 2 == 0:
        s /= 2
        e += 1
        
    # Find some 'n' with a legendre symbol n|p = -1.
    # Shouldn't take long.
    #
    n = 2
    while legendre_symbol(n, p) != -1:
        n += 1
        
    # Here be dragons!
    # Read the paper "Square roots from 1; 24, 51,
    # 10 to Dan Shanks" by Ezra Brown for more
    # information
    #
    
    # x is a guess of the square root that gets better
    # with each iteration.
    # b is the "fudge factor" - by how much we're off
    # with the guess. The invariant x^2 = ab (mod p)
    # is maintained throughout the loop.
    # g is used for successive powers of n to update
    # both a and b
    # r is the exponent - decreases with each update
    #
    x = pow(a, (s + 1) / 2, p)
    b = pow(a, s, p)
    g = pow(n, s, p)
    r = e
    
    while True:
        t = b
        m = 0
        for m in xrange(r):
            if t == 1:
                break
            t = pow(t, 2, p)
            
        if m == 0:
            return x
        
        gs = pow(g, 2 ** (r - m - 1), p)
        g = (gs * gs) % p
        x = (x * gs) % p
        b = (b * g) % p
        r = m
        
def legendre_symbol(a, p):
    """ Compute the Legendre symbol a|p using
    Euler's criterion. p is a prime, a is
    relatively prime to p (if p divides
    a, then a|p = 0)
    
    Returns 1 if a has a square root modulo
    p, -1 otherwise.
    """
    ls = pow(a, (p - 1) / 2, p)
    return -1 if ls == p - 1 else ls

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

def msg_magic(message):
    return "\x18Bitcoin Signed Message:\n" + chr( len(message) ) + message

def Hash(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def hash_160(public_key):
    md = hashlib.new('ripemd160')
    md.update(hashlib.sha256(public_key).digest())
    return md.digest()

def hash_160_to_bc_address(h160):
    vh160 = chr(addrtype) + h160
    h = Hash(vh160)
    addr = vh160 + h[0:4]
    return b58encode(addr)

def public_key_to_bc_address(public_key):
    h160 = hash_160(public_key)
    return hash_160_to_bc_address(h160)

def encode_point(pubkey, compressed=False):
    order = generator_secp256k1.order()
    p = pubkey.pubkey.point
    x_str = ecdsa.util.number_to_string(p.x(), order)
    y_str = ecdsa.util.number_to_string(p.y(), order)
    if compressed:
        return chr(2 + (p.y() & 1)) + x_str
    else:
        return chr(4) + x_str + y_str

def sign_message(private_key, message, compressed=False):
    public_key = private_key.get_verifying_key()
    signature = private_key.sign_digest( Hash( msg_magic( message ) ), sigencode = ecdsa.util.sigencode_string )
    address = public_key_to_bc_address(encode_point(public_key, compressed))
    assert public_key.verify_digest( signature, Hash( msg_magic( message ) ), sigdecode = ecdsa.util.sigdecode_string)
    for i in range(4):
        nV = 27 + i
        if compressed:
            nV += 4
        sig = base64.b64encode( chr(nV) + signature )
        try:
            if verify_message( address, sig, message):
                return sig
        except:
            continue
    else:
        raise BaseException("error: cannot sign message")

def verify_message(address, signature, message):
    """ See http://www.secg.org/download/aid-780/sec1-v2.pdf for the math """
    from ecdsa import numbertheory, ellipticcurve, util
    curve = curve_secp256k1
    G = generator_secp256k1
    order = G.order()
    # extract r,s from signature
    sig = base64.b64decode(signature)
    if len(sig) != 65: raise BaseException("Wrong encoding")
    r,s = util.sigdecode_string(sig[1:], order)
    nV = ord(sig[0])
    if nV < 27 or nV >= 35:
        return False
    if nV >= 31:
        compressed = True
        nV -= 4
    else:
        compressed = False
    recid = nV - 27
    # 1.1
    x = r + (recid/2) * order
    # 1.3
    alpha = ( x * x * x  + curve.a() * x + curve.b() ) % curve.p()
    beta = modular_sqrt(alpha, curve.p())
    y = beta if (beta - recid) % 2 == 0 else curve.p() - beta
    # 1.4 the constructor checks that nR is at infinity
    R = ellipticcurve.Point(curve, x, y, order)
    # 1.5 compute e from message:
    h = Hash( msg_magic( message ) )
    e = string_to_number(h)
    minus_e = -e % order
    # 1.6 compute Q = r^-1 (sR - eG)
    inv_r = numbertheory.inverse_mod(r,order)
    Q = inv_r * ( s * R + minus_e * G )
    public_key = ecdsa.VerifyingKey.from_public_point( Q, curve = SECP256k1 )
    # check that Q is the public key
    public_key.verify_digest( sig[1:], h, sigdecode = ecdsa.util.sigdecode_string)
    # check that we get the original signing address
    addr = public_key_to_bc_address(encode_point(public_key, compressed))
    if address == addr:
        return True
    else:
        #print addr
        return False
        
if __name__ == '__main__':
    # some simple testing code
    print verify_message('16vqGo3KRKE9kTsTZxKoJKLzwZGTodK3ce',
            'HPDs1TesA48a9up4QORIuub67VHBM37X66skAYz0Esg23gdfMuCTYDFORc6XGpKZ2/flJ2h/DUF569FJxGoVZ50=',
            'test message') # good
    print verify_message('16vqGo3KRKE9kTsTZxKoJKLzwZGTodK3ce',
            'HPDs1TesA48a9up4QORIuub67VHBM37X66skAYz0Esg23gdfMuCTYDFORc6XGpKZ2/flJ2h/DUF569FJxGoVZ50=',
            'test message 2') # bad

    private_key = ecdsa.SigningKey.from_string( '5JkuZ6GLsMWBKcDWa5QiD15Uj467phPR', curve = SECP256k1 )
    public_key = private_key.get_verifying_key()
    bitcoinaddress = public_key_to_bc_address( encode_point(public_key) )
    print bitcoinaddress
    sig = sign_message(private_key, 'test message')
    print sig
    print verify_message(bitcoinaddress, sig, 'test message')
    print verify_message('1GdKjTSg2eMyeVvPV5Nivo6kR8yP2GT7wF',
            'GyMn9AdYeZIPWLVCiAblOOG18Qqy4fFaqjg5rjH6QT5tNiUXLS6T2o7iuWkV1gc4DbEWvyi8yJ8FvSkmEs3voWE=',
            'freenode:#bitcoin-otc:b42f7e7ea336db4109df6badc05c6b3ea8bfaa13575b51631c5178a7')

    print verify_message('1Hpj6xv9AzaaXjPPisQrdAD2tu84cnPv3f',
            'INEJxQnSu6mwGnLs0E8eirl5g+0cAC9D5M7hALHD9sK0XQ66CH9mas06gNoIX7K1NKTLaj3MzVe8z3pt6apGJ34=',
            'testtest')
    print verify_message('18uitB5ARAhyxmkN2Sa9TbEuoGN1he83BX',
            'IMAtT1SjRyP6bz6vm5tKDTTTNYS6D8w2RQQyKD3VGPq2i2txGd2ar18L8/nvF1+kAMo5tNc4x0xAOGP0HRjKLjc=',
            'testtest')

    # sign compressed key
    compressed = True
    secret = 'dea7715ddcf5aba27530d6a1393813fbdd09af3aeb5f4f1616f563833d07babb'.decode('hex')
    private_key = ecdsa.SigningKey.from_string( secret, curve = SECP256k1 )
    public_key = private_key.get_verifying_key()
    bitcoinaddress = public_key_to_bc_address( encode_point(public_key, compressed) )
    print bitcoinaddress

    sig = sign_message(private_key, 'test message', compressed)
    print sig

    print verify_message(bitcoinaddress, sig, 'test message')

    print verify_message('1LsPb3D1o1Z7CzEt1kv5QVxErfqzXxaZXv',
            'H3I37ur48/fn52ZvWQT+Mj2wXL36gyjfaN5qcgfiVRTJb1eP1li/IacCQspYnUntiRv8r6GDfJYsdiQ5VzlG3As=',
            'testtest')


########NEW FILE########
__FILENAME__ = gnupg
""" A wrapper for the 'gpg' command::

Portions of this module are derived from A.M. Kuchling's well-designed
GPG.py, using Richard Jones' updated version 1.3, which can be found
in the pycrypto CVS repository on Sourceforge:

http://pycrypto.cvs.sourceforge.net/viewvc/pycrypto/gpg/GPG.py

This module is *not* forward-compatible with amk's; some of the
old interface has changed.  For instance, since I've added decrypt
functionality, I elected to initialize with a 'gnupghome' argument
instead of 'keyring', so that gpg can find both the public and secret
keyrings.  I've also altered some of the returned objects in order for
the caller to not have to know as much about the internals of the
result classes.

While the rest of ISconf is released under the GPL, I am releasing
this single file under the same terms that A.M. Kuchling used for
pycrypto.

Steve Traugott, stevegt@terraluna.org
Thu Jun 23 21:27:20 PDT 2005

This version of the module has been modified from Steve Traugott's version
(see http://trac.t7a.org/isconf/browser/trunk/lib/python/isconf/GPG.py) by
Vinay Sajip to make use of the subprocess module (Steve's version uses os.fork()
and so does not work on Windows). Renamed to gnupg.py to avoid confusion with
the previous versions.

Modifications Copyright (C) 2008-2011 Vinay Sajip. All rights reserved.

A unittest harness (test_gnupg.py) has also been added.
"""
import locale

__author__ = "Vinay Sajip"
__date__  = "$25-Jan-2011 11:40:48$"

try:
    from io import StringIO
    from io import TextIOWrapper
    from io import BufferedReader
    from io import BufferedWriter
except ImportError:
    from cStringIO import StringIO
    class BufferedReader: pass
    class BufferedWriter: pass

import locale
import logging
import os
import socket
from subprocess import Popen
from subprocess import PIPE
import sys
import threading

try:
    import logging.NullHandler as NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def handle(self, record):
            pass
try:
    unicode
    _py3k = False
except NameError:
    _py3k = True

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.addHandler(NullHandler())

def _copy_data(instream, outstream):
    # Copy one stream to another
    sent = 0
    if hasattr(sys.stdin, 'encoding'):
        enc = sys.stdin.encoding
    else:
        enc = 'ascii'
    while True:
        data = instream.read(1024)
        if len(data) == 0:
            break
        sent += len(data)
        logger.debug("sending chunk (%d): %r", sent, data[:256])
        try:
            outstream.write(data)
        except UnicodeError:
            outstream.write(data.encode(enc))
        except:
            # Can sometimes get 'broken pipe' errors even when the data has all
            # been sent
            logger.exception('Error sending data')
            break
    try:
        outstream.close()
    except IOError:
        logger.warning('Exception occurred while closing: ignored', exc_info=1)
    logger.debug("closed output, %d bytes sent", sent)

def _threaded_copy_data(instream, outstream):
    wr = threading.Thread(target=_copy_data, args=(instream, outstream))
    wr.setDaemon(True)
    logger.debug('data copier: %r, %r, %r', wr, instream, outstream)
    wr.start()
    return wr

def _write_passphrase(stream, passphrase, encoding):
    passphrase = '%s\n' % passphrase
    passphrase = passphrase.encode(encoding)
    stream.write(passphrase)
    logger.debug("Wrote passphrase: %r", passphrase)

def _is_sequence(instance):
    return isinstance(instance,list) or isinstance(instance,tuple)

def _wrap_input(inp):
    if isinstance(inp, BufferedWriter):
        oldinp = inp
        inp = TextIOWrapper(inp)
        logger.debug('wrapped input: %r -> %r', oldinp, inp)
    return inp

def _wrap_output(outp):
    if isinstance(outp, BufferedReader):
        oldoutp = outp
        outp = TextIOWrapper(outp)
        logger.debug('wrapped output: %r -> %r', oldoutp, outp)
    return outp

#The following is needed for Python2.7 :-(
def _make_file(s):
    try:
        rv = StringIO(s)
    except (TypeError, UnicodeError):
        from io import BytesIO
        rv = BytesIO(s)
    return rv

def _make_binary_stream(s, encoding):
    try:
        if _py3k:
            if isinstance(s, str):
                s = s.encode(encoding)
        else:
            if type(s) is not str:
                s = s.encode(encoding)
        from io import BytesIO
        rv = BytesIO(s)
    except ImportError:
        rv = StringIO(s)
    return rv

class GPG(object):
    "Encapsulate access to the gpg executable"
    def __init__(self, gpgbinary='gpg', gnupghome=None, verbose=False, use_agent=False):
        """Initialize a GPG process wrapper.  Options are:

        gpgbinary -- full pathname for GPG binary.

        gnupghome -- full pathname to where we can find the public and
        private keyrings.  Default is whatever gpg defaults to.
        """
        self.gpgbinary = gpgbinary
        self.gnupghome = gnupghome
        self.verbose = verbose
        self.use_agent = use_agent
        self.encoding = locale.getpreferredencoding()
        if self.encoding is None: # This happens on Jython!
            self.encoding = sys.stdin.encoding
        if gnupghome and not os.path.isdir(self.gnupghome):
            os.makedirs(self.gnupghome,0x1C0)
        p = self._open_subprocess(["--version"])
        result = Verify() # any result will do for this
        self._collect_output(p, result, stdin=p.stdin)
        if p.returncode != 0:
            raise ValueError("Error invoking gpg: %s: %s" % (p.returncode,
                                                             result.stderr))

    def _open_subprocess(self, args, passphrase=False):
        # Internal method: open a pipe to a GPG subprocess and return
        # the file objects for communicating with it.
        cmd = [self.gpgbinary, '--status-fd 2 --no-tty']
        if self.gnupghome:
            cmd.append('--homedir "%s" ' % self.gnupghome)
        if passphrase:
            cmd.append('--batch --passphrase-fd 0')
        if self.use_agent:
            cmd.append('--use-agent')
        cmd.extend(args)
        cmd = ' '.join(cmd)
        if self.verbose:
            print(cmd)
        logger.debug("%s", cmd)
        return Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)

    def _read_response(self, stream, result):
        # Internal method: reads all the output from GPG, taking notice
        # only of lines that begin with the magic [GNUPG:] prefix.
        #
        # Calls methods on the response object for each valid token found,
        # with the arg being the remainder of the status line.
        lines = []
        while True:
            line = stream.readline()
            lines.append(line)
            if self.verbose:
                print(line)
            logger.debug("%s", line.rstrip())
            if line == "": break
            line = line.rstrip()
            if line[0:9] == '[GNUPG:] ':
                # Chop off the prefix
                line = line[9:]
                L = line.split(None, 1)
                keyword = L[0]
                if len(L) > 1:
                    value = L[1]
                else:
                    value = ""
                result.handle_status(keyword, value)
        result.stderr = ''.join(lines)

    def _read_data(self, stream, result):
        # Read the contents of the file from GPG's stdout
        chunks = []
        while True:
            data = stream.read(1024)
            if len(data) == 0:
                break
            logger.debug("chunk: %r" % data[:256])
            chunks.append(data)
        if _py3k:
            # Join using b'' or '', as appropriate
            result.data = type(data)().join(chunks)
        else:
            result.data = ''.join(chunks)

    def _collect_output(self, process, result, writer=None, stdin=None):
        """
        Drain the subprocesses output streams, writing the collected output
        to the result. If a writer thread (writing to the subprocess) is given,
        make sure it's joined before returning. If a stdin stream is given,
        close it before returning.
        """
        stderr = _wrap_output(process.stderr)
        rr = threading.Thread(target=self._read_response, args=(stderr, result))
        rr.setDaemon(True)
        logger.debug('stderr reader: %r', rr)
        rr.start()

        stdout = process.stdout # _wrap_output(process.stdout)
        dr = threading.Thread(target=self._read_data, args=(stdout, result))
        dr.setDaemon(True)
        logger.debug('stdout reader: %r', dr)
        dr.start()

        dr.join()
        rr.join()
        if writer is not None:
            writer.join()
        process.wait()
        if stdin is not None:
            try:
                stdin.close()
            except IOError:
                pass
        stderr.close()
        stdout.close()

    def _handle_io(self, args, file, result, passphrase=None, binary=False):
        "Handle a call to GPG - pass input data, collect output data"
        # Handle a basic data call - pass data to GPG, handle the output
        # including status information. Garbage In, Garbage Out :)
        p = self._open_subprocess(args, passphrase is not None)
        if not binary and not isinstance(file, BufferedReader):
            stdin = _wrap_input(p.stdin)
        else:
            stdin = p.stdin
        if passphrase:
            _write_passphrase(stdin, passphrase, self.encoding)
        writer = _threaded_copy_data(file, stdin)
        self._collect_output(p, result, writer, stdin)
        return result

    #
    # SIGNATURE METHODS
    #
    def sign(self, message, **kwargs):
        """sign message"""
        f = _make_binary_stream(message, self.encoding)
        result = self.sign_file(f, **kwargs)
        f.close()
        return result

    def sign_file(self, file, keyid=None, passphrase=None, clearsign=True,
                  detach=False, binary=False):
        """sign file"""
        logger.debug("sign_file: %s", file)
        if binary:
            args = ['-s']
        else:
            args = ['-sa']
        # You can't specify detach-sign and clearsign together: gpg ignores
        # the detach-sign in that case.
        if detach:
            args.append("--detach-sign")
        elif clearsign:
            args.append("--clearsign")
        if keyid:
            args.append("--default-key %s" % keyid)
        result = Sign(self.encoding)
        #We could use _handle_io here except for the fact that if the
        #passphrase is bad, gpg bails and you can't write the message.
        #self._handle_io(args, _make_file(message), result, passphrase=passphrase)
        p = self._open_subprocess(args, passphrase is not None)
        try:
            stdin = p.stdin
            if passphrase:
                _write_passphrase(stdin, passphrase, self.encoding)
            writer = _threaded_copy_data(file, stdin)
        except IOError:
            logging.exception("error writing message")
            writer = None
        self._collect_output(p, result, writer, stdin)
        return result

    def verify(self, data):
        """Verify the signature on the contents of the string 'data'

        >>> gpg = GPG(gnupghome="keys")
        >>> input = gpg.gen_key_input(Passphrase='foo')
        >>> key = gpg.gen_key(input)
        >>> assert key
        >>> sig = gpg.sign('hello',keyid=key.fingerprint,passphrase='bar')
        >>> assert not sig
        >>> sig = gpg.sign('hello',keyid=key.fingerprint,passphrase='foo')
        >>> assert sig
        >>> verify = gpg.verify(sig.data)
        >>> assert verify

        """
        f = _make_binary_stream(data, self.encoding)
        result = self.verify_file(f)
        f.close()
        return result

    def verify_file(self, file, data_filename=None):
        "Verify the signature on the contents of the file-like object 'file'"
        logger.debug('verify_file: %r, %r', file, data_filename)
        result = Verify()
        args = ['--verify']
        if data_filename is None:
            self._handle_io(args, file, result, binary=True)
        else:
            logger.debug('Handling detached verification')
            import tempfile
            fd, fn = tempfile.mkstemp(prefix='pygpg')
            s = file.read()
            file.close()
            logger.debug('Wrote to temp file: %r', s)
            os.write(fd, s)
            os.close(fd)
            args.append(fn)
            args.append(data_filename)
            try:
                p = self._open_subprocess(args)
                self._collect_output(p, result, stdin=p.stdin)
            finally:
                os.unlink(fn)
        return result

    #
    # KEY MANAGEMENT
    #

    def import_keys(self, key_data):
        """ import the key_data into our keyring

        >>> import shutil
        >>> shutil.rmtree("keys")
        >>> gpg = GPG(gnupghome="keys")
        >>> input = gpg.gen_key_input()
        >>> result = gpg.gen_key(input)
        >>> print1 = result.fingerprint
        >>> result = gpg.gen_key(input)
        >>> print2 = result.fingerprint
        >>> pubkey1 = gpg.export_keys(print1)
        >>> seckey1 = gpg.export_keys(print1,secret=True)
        >>> seckeys = gpg.list_keys(secret=True)
        >>> pubkeys = gpg.list_keys()
        >>> assert print1 in seckeys.fingerprints
        >>> assert print1 in pubkeys.fingerprints
        >>> str(gpg.delete_keys(print1))
        'Must delete secret key first'
        >>> str(gpg.delete_keys(print1,secret=True))
        'ok'
        >>> str(gpg.delete_keys(print1))
        'ok'
        >>> str(gpg.delete_keys("nosuchkey"))
        'No such key'
        >>> seckeys = gpg.list_keys(secret=True)
        >>> pubkeys = gpg.list_keys()
        >>> assert not print1 in seckeys.fingerprints
        >>> assert not print1 in pubkeys.fingerprints
        >>> result = gpg.import_keys('foo')
        >>> assert not result
        >>> result = gpg.import_keys(pubkey1)
        >>> pubkeys = gpg.list_keys()
        >>> seckeys = gpg.list_keys(secret=True)
        >>> assert not print1 in seckeys.fingerprints
        >>> assert print1 in pubkeys.fingerprints
        >>> result = gpg.import_keys(seckey1)
        >>> assert result
        >>> seckeys = gpg.list_keys(secret=True)
        >>> pubkeys = gpg.list_keys()
        >>> assert print1 in seckeys.fingerprints
        >>> assert print1 in pubkeys.fingerprints
        >>> assert print2 in pubkeys.fingerprints

        """
        result = ImportResult()
        logger.debug('import_keys: %r', key_data[:256])
        data = _make_binary_stream(key_data, self.encoding)
        self._handle_io(['--import'], data, result, binary=True)
        logger.debug('import_keys result: %r', result.__dict__)
        data.close()
        return result

    def recv_keys(self, keyserver, *keyids):
        """Import a key from a keyserver

        >>> import shutil
        >>> shutil.rmtree("keys")
        >>> gpg = GPG(gnupghome="keys")
        >>> result = gpg.recv_key('pgp.mit.edu', '3FF0DB166A7476EA')
        >>> assert result

        """
        result = ImportResult()
        logger.debug('recv_keys: %r', keyids)
        data = _make_binary_stream("", self.encoding)
        #data = ""
        args = ['--keyserver', keyserver, '--recv-keys']
        args.extend(keyids)
        self._handle_io(args, data, result, binary=True)
        logger.debug('recv_keys result: %r', result.__dict__)
        data.close()
        return result

    def delete_keys(self, fingerprints, secret=False):
        which='key'
        if secret:
            which='secret-key'
        if _is_sequence(fingerprints):
            fingerprints = ' '.join(fingerprints)
        args = ["--batch --delete-%s %s" % (which, fingerprints)]
        result = DeleteResult()
        p = self._open_subprocess(args)
        self._collect_output(p, result, stdin=p.stdin)
        return result

    def export_keys(self, keyids, secret=False):
        "export the indicated keys. 'keyid' is anything gpg accepts"
        which=''
        if secret:
            which='-secret-key'
        if _is_sequence(keyids):
            keyids = ' '.join(keyids)
        args = ["--armor --export%s %s" % (which, keyids)]
        p = self._open_subprocess(args)
        # gpg --export produces no status-fd output; stdout will be
        # empty in case of failure
        #stdout, stderr = p.communicate()
        result = DeleteResult() # any result will do
        self._collect_output(p, result, stdin=p.stdin)
        logger.debug('export_keys result: %r', result.data)
        return result.data.decode(self.encoding)

    def list_keys(self, secret=False):
        """ list the keys currently in the keyring

        >>> import shutil
        >>> shutil.rmtree("keys")
        >>> gpg = GPG(gnupghome="keys")
        >>> input = gpg.gen_key_input()
        >>> result = gpg.gen_key(input)
        >>> print1 = result.fingerprint
        >>> result = gpg.gen_key(input)
        >>> print2 = result.fingerprint
        >>> pubkeys = gpg.list_keys()
        >>> assert print1 in pubkeys.fingerprints
        >>> assert print2 in pubkeys.fingerprints

        """

        which='keys'
        if secret:
            which='secret-keys'
        args = "--list-%s --fixed-list-mode --fingerprint --with-colons" % (which,)
        args = [args]
        p = self._open_subprocess(args)

        # there might be some status thingumy here I should handle... (amk)
        # ...nope, unless you care about expired sigs or keys (stevegt)

        # Get the response information
        result = ListKeys()
        self._collect_output(p, result, stdin=p.stdin)
        lines = result.data.decode(self.encoding).splitlines()
        valid_keywords = 'pub uid sec fpr'.split()
        for line in lines:
            if self.verbose:
                print(line)
            logger.debug("line: %r", line.rstrip())
            if not line:
                break
            L = line.strip().split(':')
            if not L:
                continue
            keyword = L[0]
            if keyword in valid_keywords:
                getattr(result, keyword)(L)
        return result

    def gen_key(self, input):
        """Generate a key; you might use gen_key_input() to create the
        control input.

        >>> gpg = GPG(gnupghome="keys")
        >>> input = gpg.gen_key_input()
        >>> result = gpg.gen_key(input)
        >>> assert result
        >>> result = gpg.gen_key('foo')
        >>> assert not result

        """
        args = ["--gen-key --batch"]
        result = GenKey()
        f = _make_file(input)
        self._handle_io(args, f, result)
        f.close()
        return result

    def gen_key_input(self, **kwargs):
        """
        Generate --gen-key input per gpg doc/DETAILS
        """
        parms = {}
        for key, val in list(kwargs.items()):
            key = key.replace('_','-').title()
            parms[key] = val
        parms.setdefault('Key-Type','RSA')
        parms.setdefault('Key-Length',1024)
        parms.setdefault('Name-Real', "Autogenerated Key")
        parms.setdefault('Name-Comment', "Generated by gnupg.py")
        try:
            logname = os.environ['LOGNAME']
        except KeyError:
            logname = os.environ['USERNAME']
        hostname = socket.gethostname()
        parms.setdefault('Name-Email', "%s@%s" % (logname.replace(' ', '_'),
                                                  hostname))
        out = "Key-Type: %s\n" % parms.pop('Key-Type')
        for key, val in list(parms.items()):
            out += "%s: %s\n" % (key, val)
        out += "%commit\n"
        return out

        # Key-Type: RSA
        # Key-Length: 1024
        # Name-Real: ISdlink Server on %s
        # Name-Comment: Created by %s
        # Name-Email: isdlink@%s
        # Expire-Date: 0
        # %commit
        #
        #
        # Key-Type: DSA
        # Key-Length: 1024
        # Subkey-Type: ELG-E
        # Subkey-Length: 1024
        # Name-Real: Joe Tester
        # Name-Comment: with stupid passphrase
        # Name-Email: joe@foo.bar
        # Expire-Date: 0
        # Passphrase: abc
        # %pubring foo.pub
        # %secring foo.sec
        # %commit

    #
    # ENCRYPTION
    #
    def encrypt_file(self, file, recipients, sign=None,
            always_trust=False, passphrase=None,
            armor=True, output=None):
        "Encrypt the message read from the file-like object 'file'"
        args = ['--encrypt']
        if armor:   # create ascii-armored output - set to False for binary output
            args.append('--armor')
        if output:  # write the output to a file with the specified name
            if os.path.exists(output):
                os.remove(output) # to avoid overwrite confirmation message
            args.append('--output %s' % output)
        if not _is_sequence(recipients):
            recipients = (recipients,)
        for recipient in recipients:
            args.append('--recipient %s' % recipient)
        if sign:
            args.append("--sign --default-key %s" % sign)
        if always_trust:
            args.append("--always-trust")
        result = Crypt(self.encoding)
        self._handle_io(args, file, result, passphrase=passphrase, binary=True)
        logger.debug('encrypt result: %r', result.data)
        return result

    def encrypt(self, data, recipients, **kwargs):
        """Encrypt the message contained in the string 'data'

        >>> import shutil
        >>> if os.path.exists("keys"):
        ...     shutil.rmtree("keys")
        >>> gpg = GPG(gnupghome="keys")
        >>> input = gpg.gen_key_input(passphrase='foo')
        >>> result = gpg.gen_key(input)
        >>> print1 = result.fingerprint
        >>> input = gpg.gen_key_input()
        >>> result = gpg.gen_key(input)
        >>> print2 = result.fingerprint
        >>> result = gpg.encrypt("hello",print2)
        >>> message = str(result)
        >>> assert message != 'hello'
        >>> result = gpg.decrypt(message)
        >>> assert result
        >>> str(result)
        'hello'
        >>> result = gpg.encrypt("hello again",print1)
        >>> message = str(result)
        >>> result = gpg.decrypt(message)
        >>> result.status
        'need passphrase'
        >>> result = gpg.decrypt(message,passphrase='bar')
        >>> result.status
        'decryption failed'
        >>> assert not result
        >>> result = gpg.decrypt(message,passphrase='foo')
        >>> result.status
        'decryption ok'
        >>> str(result)
        'hello again'
        >>> result = gpg.encrypt("signed hello",print2,sign=print1)
        >>> result.status
        'need passphrase'
        >>> result = gpg.encrypt("signed hello",print2,sign=print1,passphrase='foo')
        >>> result.status
        'encryption ok'
        >>> message = str(result)
        >>> result = gpg.decrypt(message)
        >>> result.status
        'decryption ok'
        >>> assert result.fingerprint == print1

        """
        data = _make_binary_stream(data, self.encoding)
        result = self.encrypt_file(data, recipients, **kwargs)
        data.close()
        return result

    def decrypt(self, message, **kwargs):
        data = _make_binary_stream(message, self.encoding)
        result = self.decrypt_file(data, **kwargs)
        data.close()
        return result

    def decrypt_file(self, file, always_trust=False, passphrase=None,
                     output=None):
        args = ["--decrypt"]
        if output:  # write the output to a file with the specified name
            if os.path.exists(output):
                os.remove(output) # to avoid overwrite confirmation message
            args.append('--output %s' % output)
        if always_trust:
            args.append("--always-trust")
        result = Crypt(self.encoding)
        self._handle_io(args, file, result, passphrase, binary=True)
        logger.debug('decrypt result: %r', result.data)
        return result

class Verify(object):
    "Handle status messages for --verify"

    def __init__(self):
        self.valid = False
        self.fingerprint = self.creation_date = self.timestamp = None
        self.signature_id = self.key_id = None
        self.username = None

    def __nonzero__(self):
        return self.valid

    __bool__ = __nonzero__

    def handle_status(self, key, value):
        if key in ("TRUST_UNDEFINED", "TRUST_NEVER", "TRUST_MARGINAL",
                   "TRUST_FULLY", "TRUST_ULTIMATE", "RSA_OR_IDEA"):
            pass
        elif key in ("PLAINTEXT", "PLAINTEXT_LENGTH"):
            pass
        elif key == "BADSIG":
            self.valid = False
            self.key_id, self.username = value.split(None, 1)
        elif key == "GOODSIG":
            self.valid = True
            self.key_id, self.username = value.split(None, 1)
        elif key == "VALIDSIG":
            (self.fingerprint,
             self.creation_date,
             self.sig_timestamp,
             self.expire_timestamp) = value.split()[:4]
             # may be different if signature is made with a subkey:
            self.pubkey_fingerprint = value.split()[-1]
        elif key == "SIG_ID":
            (self.signature_id,
             self.creation_date, self.timestamp) = value.split()
        elif key == "ERRSIG":
            self.valid = False
            (self.key_id,
             algo, hash_algo,
             cls,
             self.timestamp) = value.split()[:5]
        elif key == "NO_PUBKEY":
            self.valid = False
            self.key_id = value
        elif key in ("KEYEXPIRED", "SIGEXPIRED",):
            # these are useless in verify, since they are spit out for any
            # pub/subkeys on the key, not just the one doing the signing.
            # if we want to check for signatures with expired key,
            # the relevant flag is EXPKEYSIG.
            pass
        elif key == "EXPKEYSIG":
            # signed with expired key
            self.valid = False
            self.key_id = value.split()[0]
        elif key == "REVKEYSIG":
            # signed with revoked key
            self.valid = False
            self.key_id = value.split()[0]
        else:
            raise ValueError("Unknown status message: %r" % key)

class ImportResult(object):
    "Handle status messages for --import"

    counts = '''count no_user_id imported imported_rsa unchanged
            n_uids n_subk n_sigs n_revoc sec_read sec_imported
            sec_dups not_imported'''.split()
    def __init__(self):
        self.imported = []
        self.results = []
        self.fingerprints = []
        for result in self.counts:
            setattr(self, result, None)

    def __nonzero__(self):
        if self.not_imported: return False
        if not self.fingerprints: return False
        return True

    __bool__ = __nonzero__

    ok_reason = {
        '0': 'Not actually changed',
        '1': 'Entirely new key',
        '2': 'New user IDs',
        '4': 'New signatures',
        '8': 'New subkeys',
        '16': 'Contains private key',
    }

    problem_reason = {
        '0': 'No specific reason given',
        '1': 'Invalid Certificate',
        '2': 'Issuer Certificate missing',
        '3': 'Certificate Chain too long',
        '4': 'Error storing certificate',
    }

    def handle_status(self, key, value):
        if key == "IMPORTED":
            # this duplicates info we already see in import_ok & import_problem
            pass
        elif key == "NODATA":
            self.results.append({'fingerprint': None,
                'problem': '0', 'text': 'No valid data found'})
        elif key == "IMPORT_OK":
            reason, fingerprint = value.split()
            reasons = []
            for code, text in list(self.ok_reason.items()):
                if int(reason) | int(code) == int(reason):
                    reasons.append(text)
            reasontext = '\n'.join(reasons) + "\n"
            self.results.append({'fingerprint': fingerprint,
                'ok': reason, 'text': reasontext})
            self.fingerprints.append(fingerprint)
        elif key == "IMPORT_PROBLEM":
            try:
                reason, fingerprint = value.split()
            except:
                reason = value
                fingerprint = '<unknown>'
            self.results.append({'fingerprint': fingerprint,
                'problem': reason, 'text': self.problem_reason[reason]})
        elif key == "IMPORT_RES":
            import_res = value.split()
            for i in range(len(self.counts)):
                setattr(self, self.counts[i], int(import_res[i]))
        elif key == "KEYEXPIRED":
            self.results.append({'fingerprint': None,
                'problem': '0', 'text': 'Key expired'})
        elif key == "SIGEXPIRED":
            self.results.append({'fingerprint': None,
                'problem': '0', 'text': 'Signature expired'})
        else:
            raise ValueError("Unknown status message: %r" % key)

    def summary(self):
        l = []
        l.append('%d imported'%self.imported)
        if self.not_imported:
            l.append('%d not imported'%self.not_imported)
        return ', '.join(l)

class ListKeys(list):
    ''' Handle status messages for --list-keys.

        Handle pub and uid (relating the latter to the former).

        Don't care about (info from src/DETAILS):

        crt = X.509 certificate
        crs = X.509 certificate and private key available
        sub = subkey (secondary key)
        ssb = secret subkey (secondary key)
        uat = user attribute (same as user id except for field 10).
        sig = signature
        rev = revocation signature
        pkd = public key data (special field format, see below)
        grp = reserved for gpgsm
        rvk = revocation key
    '''
    def __init__(self):
        self.curkey = None
        self.fingerprints = []
        self.uids = []

    def key(self, args):
        vars = ("""
            type trust length algo keyid date expires dummy ownertrust uid
        """).split()
        self.curkey = {}
        for i in range(len(vars)):
            self.curkey[vars[i]] = args[i]
        self.curkey['uids'] = []
        if self.curkey['uid']:
            self.curkey['uids'].append(self.curkey['uid'])
        del self.curkey['uid']
        self.append(self.curkey)

    pub = sec = key

    def fpr(self, args):
        self.curkey['fingerprint'] = args[9]
        self.fingerprints.append(args[9])

    def uid(self, args):
        self.curkey['uids'].append(args[9])
        self.uids.append(args[9])

    def handle_status(self, key, value):
        pass

class Crypt(Verify):
    "Handle status messages for --encrypt and --decrypt"
    def __init__(self, encoding):
        Verify.__init__(self)
        self.data = ''
        self.ok = False
        self.status = ''
        self.encoding = encoding

    def __nonzero__(self):
        if self.ok: return True
        return False

    __bool__ = __nonzero__

    def __str__(self):
        return self.data.decode(self.encoding)

    def handle_status(self, key, value):
        if key in ("ENC_TO", "USERID_HINT", "GOODMDC", "END_DECRYPTION",
                   "BEGIN_SIGNING", "NO_SECKEY"):
            pass
        elif key in ("NEED_PASSPHRASE", "BAD_PASSPHRASE", "GOOD_PASSPHRASE",
                     "MISSING_PASSPHRASE", "DECRYPTION_FAILED"):
            self.status = key.replace("_", " ").lower()
        elif key == "NEED_PASSPHRASE_SYM":
            self.status = 'need symmetric passphrase'
        elif key == "BEGIN_DECRYPTION":
            self.status = 'decryption incomplete'
        elif key == "BEGIN_ENCRYPTION":
            self.status = 'encryption incomplete'
        elif key == "DECRYPTION_OKAY":
            self.status = 'decryption ok'
            self.ok = True
        elif key == "END_ENCRYPTION":
            self.status = 'encryption ok'
            self.ok = True
        elif key == "INV_RECP":
            self.status = 'invalid recipient'
        elif key == "KEYEXPIRED":
            self.status = 'key expired'
        elif key == "SIG_CREATED":
            self.status = 'sig created'
        elif key == "SIGEXPIRED":
            self.status = 'sig expired'
        else:
            Verify.handle_status(self, key, value)

class GenKey(object):
    "Handle status messages for --gen-key"
    def __init__(self):
        self.type = None
        self.fingerprint = None

    def __nonzero__(self):
        if self.fingerprint: return True
        return False

    __bool__ = __nonzero__

    def __str__(self):
        return self.fingerprint or ''

    def handle_status(self, key, value):
        if key in ("PROGRESS", "GOOD_PASSPHRASE", "NODATA"):
            pass
        elif key == "KEY_CREATED":
            (self.type,self.fingerprint) = value.split()
        else:
            raise ValueError("Unknown status message: %r" % key)

class DeleteResult(object):
    "Handle status messages for --delete-key and --delete-secret-key"
    def __init__(self):
        self.status = 'ok'

    def __str__(self):
        return self.status

    problem_reason = {
        '1': 'No such key',
        '2': 'Must delete secret key first',
        '3': 'Ambigious specification',
    }

    def handle_status(self, key, value):
        if key == "DELETE_PROBLEM":
            self.status = self.problem_reason.get(value,
                                                  "Unknown error: %r" % value)
        else:
            raise ValueError("Unknown status message: %r" % key)

class Sign(object):
    "Handle status messages for --sign"
    def __init__(self, encoding):
        self.type = None
        self.fingerprint = None
        self.encoding = encoding

    def __nonzero__(self):
        return self.fingerprint is not None

    __bool__ = __nonzero__

    def __str__(self):
        return self.data.decode(self.encoding)

    def handle_status(self, key, value):
        if key in ("USERID_HINT", "NEED_PASSPHRASE", "BAD_PASSPHRASE",
                   "GOOD_PASSPHRASE", "BEGIN_SIGNING"):
            pass
        elif key == "SIG_CREATED":
            (self.type,
             algo, hashalgo, cls,
             self.timestamp, self.fingerprint
             ) = value.split()
        else:
            raise ValueError("Unknown status message: %r" % key)

########NEW FILE########
__FILENAME__ = plugin
###
# GPG - supybot plugin to authenticate users via GPG keys
# Copyright (C) 2011, Daniel Folkinshteyn <nanotube@users.sourceforge.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###

from supybot import conf
from supybot import ircmsgs
from supybot import world
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.log

import sqlite3
import re
import os
import os.path
import errno
import hashlib
import time
import copy
import logging
import traceback

try:
    gnupg = utils.python.universalImport('gnupg', 'local.gnupg')
except ImportError:
    raise callbacks.Error, \
            "You need the gnupg module installed to use this plugin." 
try:
    bitcoinsig = utils.python.universalImport('local.bitcoinsig')
except ImportError:
    raise callbacks.Error, \
            "You are possibly missing the ecdsa module." 


domainRe = re.compile('^' + utils.web._domain + '$', re.I)
urlRe = re.compile('^' + utils.web._urlRe + '$', re.I)

class GPGDB(object):
    def __init__(self, filename):
        self.filename = filename
        self.db = None

    def _commit(self):
        '''a commit wrapper to give it another few tries if it errors.
        
        which sometimes happens due to:
        OperationalError: database is locked'''
        for i in xrange(10):
            try:
                self.db.commit()
            except:
                time.sleep(1)

    def open(self):
        if os.path.exists(self.filename):
            db = sqlite3.connect(self.filename, timeout=10, check_same_thread = False)
            db.text_factory = str
            self.db = db
            return
        
        db = sqlite3.connect(self.filename, timeout=10, check_same_thread = False)
        db.text_factory = str
        self.db = db
        cursor = self.db.cursor()
        cursor.execute("""CREATE TABLE users (
                          id INTEGER PRIMARY KEY,
                          keyid TEXT,
                          fingerprint TEXT,
                          bitcoinaddress TEXT,
                          registered_at INTEGER,
                          nick TEXT,
                          last_authed_at INTEGER,
                          is_authed INTEGER)
                           """)
        self._commit()
        return

    def close(self):
        self.db.close()

    def getByNick(self, nick):
        cursor = self.db.cursor()
        nick = nick.replace('|','||').replace('_','|_').replace('%','|%')
        cursor.execute("""SELECT * FROM users WHERE nick LIKE ? ESCAPE '|'""", (nick,))
        return cursor.fetchall()

    def getByKey(self, keyid):
        cursor = self.db.cursor()
        cursor.execute("""SELECT * FROM users WHERE keyid = ?""", (keyid,))
        return cursor.fetchall()

    def getByAddr(self, address):
        cursor = self.db.cursor()
        cursor.execute("""SELECT * FROM users WHERE bitcoinaddress = ?""", (address,))
        return cursor.fetchall()

    def getCount(self):
        cursor = self.db.cursor()
        cursor.execute("""SELECT count(*) FROM users""")
        return cursor.fetchall()

    def register(self, keyid, fingerprint, bitcoinaddress, timestamp, nick):
        cursor = self.db.cursor()
        cursor.execute("""INSERT INTO users VALUES
                        (NULL, ?, ?, ?, ?, ?, ?, ?)""",
                        (keyid, fingerprint, bitcoinaddress, timestamp, nick, timestamp, 0))
        self._commit()

    def update_auth_date(self, id, timestamp):
        cursor = self.db.cursor()
        cursor.execute("""UPDATE users SET last_authed_at = ? WHERE id = ?""", (timestamp, id,))
        self._commit()

    def reset_auth_status(self, authed_nicks):
        cursor = self.db.cursor()
        cursor.execute("""UPDATE users SET is_authed = 0 WHERE is_authed = 1""")
        if len(authed_nicks) > 0:
            for nick in authed_nicks:
                nick = nick.replace('|','||').replace('_','|_').replace('%','|%')
                cursor.execute("""UPDATE users SET is_authed = 1 WHERE nick LIKE ? ESCAPE '|'""", (nick,))
        self._commit()

    def set_auth_status(self, nick, state):
        cursor = self.db.cursor()
        nick = nick.replace('|','||').replace('_','|_').replace('%','|%')
        cursor.execute("""UPDATE users SET is_authed = ? WHERE nick LIKE ? ESCAPE '|'""", (state, nick,))
        self._commit()

    def changenick(self, oldnick, newnick):
        cursor = self.db.cursor()
        cursor.execute("""UPDATE users SET nick = ? WHERE nick = ?""",
                        (newnick, oldnick,))
        self._commit()

    def changekey(self, nick, oldkeyid, newkeyid, newkeyfingerprint):
        cursor = self.db.cursor()
        cursor.execute("""UPDATE users SET keyid = ?, fingerprint = ?
                        WHERE (keyid = ? OR keyid IS NULL) and nick = ?""",
                        (newkeyid, newkeyfingerprint, oldkeyid, nick))
        self._commit()

    def changeaddress(self, nick, oldaddress, newaddress):
        cursor = self.db.cursor()
        cursor.execute("""UPDATE users SET bitcoinaddress = ?
                        WHERE nick = ? AND (bitcoinaddress = ? OR bitcoinaddress IS NULL)""",
                        (newaddress, nick, oldaddress,))
        self._commit()

def getGPGKeyID(irc, msg, args, state, type='GPG key id. Please use the long form 16 digit key id'):
    v = args[0]
    m = re.search(r'^(0x)?([0-9A-Fa-f]{16})$', v)
    if m is None:
        state.errorInvalid(type, args[0])
        return
    state.args.append(m.group(2).upper())
    del args[0]

def getUsername(irc, msg, args, state, type='username. Usernames must contain only printable ASCII characters with no whitespace'):
    v = args[0]
    m = re.search(r"^[!-~]+$", v)
    if m is None:
        state.errorInvalid(type, args[0])
        return
    state.args.append(m.group(0))
    del args[0]

addConverter('keyid', getGPGKeyID)
addConverter('username', getUsername)

class GPG(callbacks.Plugin):
    """This plugin lets users create identities based on GPG keys,
    and to authenticate via GPG signed messages."""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(GPG, self)
        self.__parent.__init__(irc)
        self.filename = conf.supybot.directories.data.dirize('GPG.db')
        self.db = GPGDB(self.filename)
        self.db.open()
        try:
            os.makedirs(conf.supybot.directories.data.dirize('otps'))
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise
        self.gpg = gnupg.GPG(gnupghome = conf.supybot.directories.data.dirize('GPGkeyring'))
        try: #restore auth dicts, if we're reloading the plugin
            self.authed_users = utils.gpg_authed_users
            utils.gpg_authed_users = {}
            authednicks = [v['nick'] for k,v in self.authed_users.iteritems()]
            self.db.reset_auth_status(authednicks)
            self.pending_auth = utils.gpg_pending_auth
            utils.gpg_pending_auth = {}
        except AttributeError:
            self.pending_auth = {}
            self.authed_users = {}
            self.db.reset_auth_status([])
        authlogfilename = os.path.join(conf.supybot.directories.log(), 'gpgauthlog.log')
        authlog = logging.getLogger('GPGauth')
        authlog.setLevel(-1)
        if len(authlog.handlers) == 0:
            handler = supybot.log.BetterFileHandler(authlogfilename)
            handler.setLevel(-1)
            handler.setFormatter(supybot.log.pluginFormatter)
            authlog.addHandler(handler)
        self.authlog = authlog
        self.authlog.info("***** loading GPG plugin. *****")

    def die(self):
        self.__parent.die()
        self.db.close()
        # save auth dicts, in case we're reloading the plugin
        utils.gpg_authed_users = self.authed_users
        utils.gpg_pending_auth = self.pending_auth
        self.authlog.info("***** quitting or unloading GPG plugin. *****")

    def _recv_key(self, keyservers, keyid):
        for ks in keyservers:
            try:
                result = self.gpg.recv_keys(ks, keyid)
                if result.results[0].has_key('ok'):
                    return result.results[0]['fingerprint']
            except:
               continue
        else:
            raise Exception(result.stderr)

    def _removeExpiredRequests(self):
        pending_auth_copy = copy.deepcopy(self.pending_auth)
        for hostmask,auth in pending_auth_copy.iteritems():
            try:
                if time.time() - auth['expiry'] > self.registryValue('authRequestTimeout'):
                    if auth['type'] == 'register' and not self.db.getByKey(auth['keyid']):
                        try:
                            self.gpg.delete_keys(auth['fingerprint'])
                        except:
                            pass
                    del self.pending_auth[hostmask]
            except:
                pass #let's keep going

    def _checkURLWhitelist(self, url):
        if not self.registryValue('pastebinWhitelist'):
            return True
        passed = False
        for wu in self.registryValue('pastebinWhitelist'):
            if wu.endswith('/') and url.find(wu) == 0:
                passed = True
                break
            if (not wu.endswith('/')) and (url.find(wu + '/') == 0):
                passed = True
                break
        return passed

    def register(self, irc, msg, args, nick, keyid):
        """<nick> <keyid>

        Register your GPG identity, associating GPG key <keyid> with <nick>.
        <keyid> is a 16 digit key id, with or without the '0x' prefix.
        We look on servers listed in 'plugins.GPG.keyservers' config.
        You will be given a random passphrase to clearsign with your key, and
        submit to the bot with the 'verify' command.
        Your passphrase will expire in 10 minutes.
        """
        self._removeExpiredRequests()
        if self.db.getByNick(nick):
            irc.error("Username already registered. Try a different username.")
            return
        if self.db.getByKey(keyid):
            irc.error("This key already registered in the database.")
            return
        rs = irc.getCallback('RatingSystem')
        rsdata = rs.db.get(nick)
        if len(rsdata) != 0:
            irc.error("This username is reserved for a legacy user. "
                    "Contact otc administrator to reclaim the account, if "
                    "you are an oldtimer since before key auth.")
            return
        keyservers = self.registryValue('keyservers').split(',')
        try:
            fingerprint = self._recv_key(keyservers, keyid)
        except Exception as e:
            irc.error("Could not retrieve your key from keyserver. "
                    "Either it isn't there, or it is invalid.")
            self.log.info("GPG register: failed to retrieve key %s from keyservers %s. Details: %s" % \
                    (keyid, keyservers, e,))
            return
        challenge = "freenode:#bitcoin-otc:" + hashlib.sha256(os.urandom(128)).hexdigest()[:-8]
        request = {msg.prefix: {'keyid':keyid,
                            'nick':nick, 'expiry':time.time(),
                            'type':'register', 'fingerprint':fingerprint,
                            'challenge':challenge}}
        self.pending_auth.update(request)
        self.authlog.info("register request from hostmask %s for user %s, keyid %s." %\
                (msg.prefix, nick, keyid, ))
        irc.reply("Request successful for user %s, hostmask %s. Your challenge string is: %s" %\
                (nick, msg.prefix, challenge,))
    register = wrap(register, ['username', 'keyid'])

    def eregister(self, irc, msg, args, nick, keyid):
        """<nick> <keyid>

        Register your GPG identity, associating GPG key <keyid> with <nick>.
        <keyid> is a 16 digit key id, with or without the '0x' prefix.
        We look on servers listed in 'plugins.GPG.keyservers' config.
        You will be given a link to a page which contains a one time password
        encrypted with your key. Decrypt, and use the 'everify' command with it.
        Your passphrase will expire in 10 minutes.
        """
        self._removeExpiredRequests()
        if self.db.getByNick(nick):
            irc.error("Username already registered. Try a different username.")
            return
        if self.db.getByKey(keyid):
            irc.error("This key already registered in the database.")
            return
        rs = irc.getCallback('RatingSystem')
        rsdata = rs.db.get(nick)
        if len(rsdata) != 0:
            irc.error("This username is reserved for a legacy user. "
                    "Contact otc administrator to reclaim the account, if "
                    "you are an oldtimer since before key auth.")
            return
        keyservers = self.registryValue('keyservers').split(',')
        try:
            fingerprint = self._recv_key(keyservers, keyid)
        except Exception as e:
            irc.error("Could not retrieve your key from keyserver. "
                    "Either it isn't there, or it is invalid.")
            self.log.info("GPG eregister: failed to retrieve key %s from keyservers %s. Details: %s" % \
                    (keyid, keyservers, e,))
            return
        challenge = "freenode:#bitcoin-otc:" + hashlib.sha256(os.urandom(128)).hexdigest()[:-8]
        try:
            data = self.gpg.encrypt(challenge + '\n', keyid, always_trust=True)
            if data.status != "encryption ok":
                raise ValueError, "problem encrypting otp"
            otpfn = conf.supybot.directories.data.dirize('otps/%s' % (keyid,))
            f = open(otpfn, 'w')
            f.write(data.data)
            f.close()
        except Exception, e:
            irc.error("Problem creating encrypted OTP file.")
            self.log.info("GPG eregister: key %s, otp creation %s, exception %s" % \
                    (keyid, data.stderr, e,))
            return
        request = {msg.prefix: {'keyid':keyid,
                            'nick':nick, 'expiry':time.time(),
                            'type':'eregister', 'fingerprint':fingerprint,
                            'challenge':challenge}}
        self.pending_auth.update(request)
        self.authlog.info("eregister request from hostmask %s for user %s, keyid %s." %\
                (msg.prefix, nick, keyid,))
        irc.reply("Request successful for user %s, hostmask %s. Get your encrypted OTP from %s" %\
                (nick, msg.prefix, 'http://bitcoin-otc.com/otps/%s' % (keyid,),))
    eregister = wrap(eregister, ['username', 'keyid'])

    def bcregister(self, irc, msg, args, nick, bitcoinaddress):
        """<nick> <bitcoinaddress>

        Register your identity, associating bitcoin address key <bitcoinaddress>
        with <nick>.
        <bitcoinaddress> should be a standard-type bitcoin address, starting with 1.
        You will be given a random passphrase to sign with your address key, and
        submit to the bot with the 'bcverify' command.
        Your passphrase will expire in 10 minutes.
        """
        self._removeExpiredRequests()
        if self.db.getByNick(nick):
            irc.error("Username already registered. Try a different username.")
            return
        if self.db.getByAddr(bitcoinaddress):
            irc.error("This address is already registered in the database.")
            return
        rs = irc.getCallback('RatingSystem')
        rsdata = rs.db.get(nick)
        if len(rsdata) != 0:
            irc.error("This username is reserved for a legacy user. "
                    "Contact otc administrator to reclaim the account, if "
                    "you are an oldtimer since before key auth.")
            return
        challenge = "freenode:#bitcoin-otc:" + hashlib.sha256(os.urandom(128)).hexdigest()[:-8]
        request = {msg.prefix: {'bitcoinaddress':bitcoinaddress,
                            'nick':nick, 'expiry':time.time(),
                            'type':'bcregister',
                            'challenge':challenge}}
        self.pending_auth.update(request)
        self.authlog.info("bcregister request from hostmask %s for user %s, bitcoinaddress %s." %\
                (msg.prefix, nick, bitcoinaddress, ))
        irc.reply("Request successful for user %s, hostmask %s. Your challenge string is: %s" %\
                (nick, msg.prefix, challenge,))
    bcregister = wrap(bcregister, ['username', 'something'])

    def auth(self, irc, msg, args, nick):
        """<nick>

        Initiate authentication for user <nick>.
        You must have registered a GPG key with the bot for this to work.
        You will be given a random passphrase to clearsign with your key, and
        submit to the bot with the 'verify' command.
        Your passphrase will expire within 10 minutes.
        """
        self._removeExpiredRequests()
        userdata = self.db.getByNick(nick)
        if len(userdata) == 0:
            irc.error("This nick is not registered. Please register.")
            return
        keyid = userdata[0][1]
        fingerprint = userdata[0][2]
        if keyid is None:
            irc.error("You have not registered a GPG key. Try using bcauth instead, or register a GPG key first.")
            return
        challenge = "freenode:#bitcoin-otc:" + hashlib.sha256(os.urandom(128)).hexdigest()[:-8]
        request = {msg.prefix: {'nick':userdata[0][5],
                                'expiry':time.time(), 'keyid':keyid,
                                'type':'auth', 'challenge':challenge,
                                'fingerprint':fingerprint}}
        self.pending_auth.update(request)
        self.authlog.info("auth request from hostmask %s for user %s, keyid %s." %\
                (msg.prefix, nick, keyid, ))
        irc.reply("Request successful for user %s, hostmask %s. Your challenge string is: %s" %\
                (nick, msg.prefix, challenge,))
    auth = wrap(auth, ['username'])

    def eauth(self, irc, msg, args, nick):
        """<nick>

        Initiate authentication for user <nick>.
        You must have registered a GPG key with the bot for this to work.
        You will be given a link to a page which contains a one time password
        encrypted with your key. Decrypt, and use the 'everify' command with it.
        Your passphrase will expire in 10 minutes.
        """
        self._removeExpiredRequests()
        userdata = self.db.getByNick(nick)
        if len(userdata) == 0:
            irc.error("This nick is not registered. Please register.")
            return
        keyid = userdata[0][1]
        fingerprint = userdata[0][2]
        if keyid is None:
            irc.error("You have not registered a GPG key. Try using bcauth instead, or register a GPG key first.")
            return
        challenge = "freenode:#bitcoin-otc:" + hashlib.sha256(os.urandom(128)).hexdigest()[:-8]
        try:
            data = None
            data = self.gpg.encrypt(challenge + '\n', keyid, always_trust=True)
            if data.status != "encryption ok":
                raise ValueError, "problem encrypting otp"
            otpfn = conf.supybot.directories.data.dirize('otps/%s' % (keyid,))
            f = open(otpfn, 'w')
            f.write(data.data)
            f.close()
        except Exception, e:
            irc.error("Problem creating encrypted OTP file.")
            if 'stderr' in dir(data):
                gpgerroroutput = data.stderr
            else:
                gpgerroroutput = None
            self.log.info("GPG eauth: key %s, otp creation %s, exception %s" % \
                    (keyid, gpgerroroutput, e,))
            return
        request = {msg.prefix: {'nick':userdata[0][5],
                                'expiry':time.time(), 'keyid':keyid,
                                'type':'eauth', 'challenge':challenge,
                                'fingerprint':fingerprint}}
        self.pending_auth.update(request)
        self.authlog.info("eauth request from hostmask %s for user %s, keyid %s." %\
                (msg.prefix, nick, keyid, ))
        irc.reply("Request successful for user %s, hostmask %s. Get your encrypted OTP from %s" %\
                (nick, msg.prefix, 'http://bitcoin-otc.com/otps/%s' % (keyid,),))
    eauth = wrap(eauth, ['username'])

    def bcauth(self, irc, msg, args, nick):
        """<nick>

        Initiate authentication for user <nick>.
        You must have registered with the bot with a bitcoin address for this to work.
        You will be given a random passphrase to sign with your address, and
        submit to the bot with the 'bcverify' command.
        Your passphrase will expire within 10 minutes.
        """
        self._removeExpiredRequests()
        userdata = self.db.getByNick(nick)
        if len(userdata) == 0:
            irc.error("This nick is not registered. Please register.")
            return
        bitcoinaddress = userdata[0][3]
        if bitcoinaddress is None:
            irc.error("You have not registered a bitcoin address. Try using auth/eauth instead, or register an address first.")
            return
        challenge = "freenode:#bitcoin-otc:" + hashlib.sha256(os.urandom(128)).hexdigest()[:-8]
        request = {msg.prefix: {'nick':userdata[0][5],
                                'expiry':time.time(),
                                'type':'bcauth', 'challenge':challenge,
                                'bitcoinaddress':bitcoinaddress}}
        self.pending_auth.update(request)
        self.authlog.info("bcauth request from hostmask %s for user %s, bitcoinaddress %s." %\
                (msg.prefix, nick, bitcoinaddress, ))
        irc.reply("Request successful for user %s, hostmask %s. Your challenge string is: %s" %\
                (nick, msg.prefix, challenge,))
    bcauth = wrap(bcauth, ['username'])

    def _unauth(self, irc, hostmask):
        try:
            logmsg = "Terminating session for hostmask %s, authenticated to user %s, keyid %s, bitcoinaddress %s" % (hostmask, self.authed_users[hostmask]['nick'], self.authed_users[hostmask]['keyid'],self.authed_users[hostmask]['bitcoinaddress'],)
            self.authlog.info(logmsg)
            self.db.set_auth_status(self.authed_users[hostmask]['nick'], 0)
            del self.authed_users[hostmask]
            if not world.testing:
                irc.queueMsg(ircmsgs.privmsg("#bitcoin-otc-auth", logmsg))
            return True
        except KeyError:
            return False

    def unauth(self, irc, msg, args):
        """takes no arguments
        
        Unauthenticate, 'logout' of your GPG session.
        """
        if self._unauth(irc, msg.prefix):
            irc.reply("Your GPG session has been terminated.")
        else:
            irc.error("You do not have a GPG session to terminate.")
    unauth = wrap(unauth)

    def _testPresenceInChannels(self, irc, nick):
        """Make sure authenticating user is present in channels being monitored."""
        for channel in self.registryValue('channels').split(';'):
            try:
                if nick in irc.state.channels[channel].users:
                    return True
            except KeyError:
                pass
        else:
            return False

    def verify(self, irc, msg, args, url):
        """<url>

        Verify the latest authentication request by providing a pastebin <url>
        which contains the challenge string clearsigned with your GPG key
        of record. If verified, you'll be authenticated for the duration of the bot's
        or your IRC session on channel (whichever is shorter).
        """
        self._removeExpiredRequests()
        if not self._checkURLWhitelist(url):
            irc.error("Only these pastebins are supported: %s" % \
                    self.registryValue('pastebinWhitelist'))
            return
        if not self._testPresenceInChannels(irc, msg.nick):
            irc.error("In order to authenticate, you must be present in one "
                    "of the following channels: %s" % (self.registryValue('channels'),))
            return
        try:
            authrequest = self.pending_auth[msg.prefix]
        except KeyError:
            irc.error("Could not find a pending authentication request from your hostmask. "
                        "Either it expired, or you changed hostmask, or you haven't made one.")
            return
        if authrequest['type'] not in ['register','auth','changekey']:
            irc.error("No outstanding GPG signature-based request found.")
            return
        try:
            rawdata = utils.web.getUrl(url)
            m = re.search(r'-----BEGIN PGP SIGNED MESSAGE-----\r?\nHash.*?\n-----END PGP SIGNATURE-----', rawdata, re.S)
            data = m.group(0)
        except:
            irc.error("Failed to retrieve clearsigned data. Check your url.")
            return
        if authrequest['challenge'] not in data:
            irc.error("Challenge string not present in signed message.")
            return
        try:
            vo = self.gpg.verify(data)
            if not vo.valid:
                irc.error("Signature verification failed.")
                self.log.info("Signature verification from %s failed. Details: %s" % \
                        (msg.prefix, vo.stderr))
                return
            if vo.key_id != authrequest['keyid'] and vo.pubkey_fingerprint[-16:] != authrequest['keyid']:
                irc.error("Signature is not made with the key on record for this nick.")
                return
        except:
            irc.error("Authentication failed. Please try again.")
            return
        response = ""
        if authrequest['type'] == 'register':
            if self.db.getByNick(authrequest['nick']) or self.db.getByKey(authrequest['keyid']):
                irc.error("Username or key already in the database.")
                return
            self.db.register(authrequest['keyid'], authrequest['fingerprint'], None,
                        time.time(), authrequest['nick'])
            response = "Registration successful. "
        elif authrequest['type'] == 'changekey':
            gpgauth = self._ident(msg.prefix)
            if gpgauth is None:
                irc.error("You must be authenticated in order to change your registered key.")
                return
            if self.db.getByKey(authrequest['keyid']):
                irc.error("This key id already registered. Try a different key.")
                return
            self.db.changekey(gpgauth['nick'], gpgauth['keyid'], authrequest['keyid'], authrequest['fingerprint'])
            response = "Successfully changed key for user %s from %s to %s. " %\
                (gpgauth['nick'], gpgauth['keyid'], authrequest['keyid'],)
        userdata = self.db.getByNick(authrequest['nick'])
        self.authed_users[msg.prefix] = {'timestamp':time.time(),
                    'keyid': authrequest['keyid'], 'nick':authrequest['nick'],
                    'bitcoinaddress':userdata[0][3],
                    'fingerprint':authrequest['fingerprint']}
        del self.pending_auth[msg.prefix]
        logmsg = "verify success from hostmask %s for user %s, keyid %s." %\
                (msg.prefix, authrequest['nick'], authrequest['keyid'],) + response
        self.authlog.info(logmsg)
        self.db.update_auth_date(userdata[0][0], time.time())
        self.db.set_auth_status(userdata[0][5], 1)
        if not world.testing:
            irc.queueMsg(ircmsgs.privmsg("#bitcoin-otc-auth", logmsg))
        irc.reply(response + "You are now authenticated for user '%s' with key %s" %\
                        (authrequest['nick'], authrequest['keyid']))
    verify = wrap(verify, ['httpUrl'])

    def everify(self, irc, msg, args, otp):
        """<otp>

        Verify the latest encrypt-authentication request by providing your decrypted
        one-time password.
        If verified, you'll be authenticated for the duration of the bot's
        or your IRC session on channel (whichever is shorter).
        """
        self._removeExpiredRequests()
        if not self._testPresenceInChannels(irc, msg.nick):
            irc.error("In order to authenticate, you must be present in one "
                    "of the following channels: %s" % (self.registryValue('channels'),))
            return
        try:
            authrequest = self.pending_auth[msg.prefix]
        except KeyError:
            irc.error("Could not find a pending authentication request from your hostmask. "
                        "Either it expired, or you changed hostmask, or you haven't made one.")
            return
        if authrequest['type'] not in ['eregister','eauth','echangekey']:
            irc.error("No outstanding encryption-based request found.")
            return
        if authrequest['challenge'] != otp:
            irc.error("Incorrect one-time password. Try again.")
            return

        response = ""
        if authrequest['type'] == 'eregister':
            if self.db.getByNick(authrequest['nick']) or self.db.getByKey(authrequest['keyid']):
                irc.error("Username or key already in the database.")
                return
            self.db.register(authrequest['keyid'], authrequest['fingerprint'], None,
                        time.time(), authrequest['nick'])
            response = "Registration successful. "
        elif authrequest['type'] == 'echangekey':
            gpgauth = self._ident(msg.prefix)
            if gpgauth is None:
                irc.error("You must be authenticated in order to change your registered key.")
                return
            if self.db.getByKey(authrequest['keyid']):
                irc.error("This key id already registered. Try a different key.")
                return
            self.db.changekey(gpgauth['nick'], gpgauth['keyid'], authrequest['keyid'], authrequest['fingerprint'])
            response = "Successfully changed key for user %s from %s to %s. " %\
                (gpgauth['nick'], gpgauth['keyid'], authrequest['keyid'],)
        userdata = self.db.getByNick(authrequest['nick'])
        self.authed_users[msg.prefix] = {'timestamp':time.time(),
                    'keyid': authrequest['keyid'], 'nick':authrequest['nick'],
                    'bitcoinaddress':userdata[0][3],
                    'fingerprint':authrequest['fingerprint']}
        del self.pending_auth[msg.prefix]
        logmsg = "everify success from hostmask %s for user %s, keyid %s." %\
                (msg.prefix, authrequest['nick'], authrequest['keyid'],) + response
        self.authlog.info(logmsg)
        self.db.update_auth_date(userdata[0][0], time.time())
        self.db.set_auth_status(userdata[0][5], 1)
        if not world.testing:
            irc.queueMsg(ircmsgs.privmsg("#bitcoin-otc-auth", logmsg))
        irc.reply(response + "You are now authenticated for user %s with key %s" %\
                        (authrequest['nick'], authrequest['keyid']))
    everify = wrap(everify, ['something'])

    def bcverify(self, irc, msg, args, data):
        """<signedmessage>

        Verify the latest authentication request by providing the <signedmessage>
        which contains the challenge string signed with your bitcoin address
        of record. If verified, you'll be authenticated for the duration of the bot's
        or your IRC session on channel (whichever is shorter).
        """
        self._removeExpiredRequests()
        if not self._testPresenceInChannels(irc, msg.nick):
            irc.error("In order to authenticate, you must be present in one "
                    "of the following channels: %s" % (self.registryValue('channels'),))
            return
        try:
            authrequest = self.pending_auth[msg.prefix]
        except KeyError:
            irc.error("Could not find a pending authentication request from your hostmask. "
                        "Either it expired, or you changed hostmask, or you haven't made one.")
            return
        if authrequest['type'] not in ['bcregister','bcauth','bcchangekey']:
            irc.error("No outstanding bitcoin-signature-based request found.")
            return
        try:
            result = bitcoinsig.verify_message(authrequest['bitcoinaddress'], data, authrequest['challenge'])
            if not result:
                irc.error("Signature verification failed.")
                return
        except:
            irc.error("Authentication failed. Please try again.")
            self.log.info("bcverify traceback: \n%s" % (traceback.format_exc()))
            return
        response = ""
        if authrequest['type'] == 'bcregister':
            if self.db.getByNick(authrequest['nick']) or self.db.getByAddr(authrequest['bitcoinaddress']):
                irc.error("Username or key already in the database.")
                return
            self.db.register(None, None, authrequest['bitcoinaddress'],
                        time.time(), authrequest['nick'])
            response = "Registration successful. "
        elif authrequest['type'] == 'bcchangekey':
            gpgauth = self._ident(msg.prefix)
            if gpgauth is None:
                irc.error("You must be authenticated in order to change your registered address.")
                return
            if self.db.getByAddr(authrequest['bitcoinaddress']):
                irc.error("This address is already registered. Try a different one.")
                return
            self.db.changeaddress(gpgauth['nick'], gpgauth['bitcoinaddress'], authrequest['bitcoinaddress'])
            response = "Successfully changed address for user %s from %s to %s. " %\
                (gpgauth['nick'], gpgauth['bitcoinaddress'], authrequest['bitcoinaddress'],)
        userdata = self.db.getByNick(authrequest['nick'])
        self.authed_users[msg.prefix] = {'timestamp':time.time(),
                    'keyid': userdata[0][1], 'nick':authrequest['nick'],
                    'bitcoinaddress':authrequest['bitcoinaddress'],
                    'fingerprint':userdata[0][2]}
        del self.pending_auth[msg.prefix]
        logmsg = "bcverify success from hostmask %s for user %s, address %s." %\
                (msg.prefix, authrequest['nick'], authrequest['bitcoinaddress'],) + response
        self.authlog.info(logmsg)
        self.db.update_auth_date(userdata[0][0], time.time())
        self.db.set_auth_status(userdata[0][5], 1)
        if not world.testing:
            irc.queueMsg(ircmsgs.privmsg("#bitcoin-otc-auth", logmsg))
        irc.reply(response + "You are now authenticated for user '%s' with address %s" %\
                        (authrequest['nick'], authrequest['bitcoinaddress']))
    bcverify = wrap(bcverify, ['something'])


    #~ def changenick(self, irc, msg, args, newnick):
        #~ """<newnick>
        
        #~ Changes your GPG registered username to <newnick>.
        #~ You must be authenticated in order to use this command.
        #~ """
        #~ self._removeExpiredRequests()
        #~ gpgauth = self._ident(msg.prefix)
        #~ if gpgauth is None:
            #~ irc.error("You must be authenticated in order to change your registered username.")
            #~ return
        #~ if self.db.getByNick(newnick):
            #~ irc.error("Username already registered. Try a different username.")
            #~ return
        #~ oldnick = gpgauth['nick']
        #~ self.db.changenick(oldnick, newnick)
        #~ gpgauth['nick'] = newnick
        #~ irc.reply("Successfully changed your nick from %s to %s." % (oldnick, newnick,))
    #~ changenick = wrap(changenick, ['something'])

    def changekey(self, irc, msg, args, keyid):
        """<keyid>
        
        Changes your GPG registered key to <keyid>.
        <keyid> is a 16 digit key id, with or without the '0x' prefix.
        We look on servers listed in 'plugins.GPG.keyservers' config.
        You will be given a random passphrase to clearsign with your key, and
        submit to the bot with the 'verify' command.
        You must be authenticated in order to use this command.
        """
        self._removeExpiredRequests()
        gpgauth = self._ident(msg.prefix)
        if gpgauth is None:
            irc.error("You must be authenticated in order to change your registered key.")
            return
        if self.db.getByKey(keyid):
            irc.error("This key id already registered. Try a different key.")
            return

        keyservers = self.registryValue('keyservers').split(',')
        try:
            fingerprint = self._recv_key(keyservers, keyid)
        except Exception as e:
            irc.error("Could not retrieve your key from keyserver. "
                    "Either it isn't there, or it is invalid.")
            self.log.info("GPG changekey: failed to retrieve key %s from keyservers %s. Details: %s" % \
                    (keyid, keyservers, e,))
            return
        challenge = "freenode:#bitcoin-otc:" + hashlib.sha256(os.urandom(128)).hexdigest()[:-8]
        request = {msg.prefix: {'keyid':keyid,
                            'nick':gpgauth['nick'], 'expiry':time.time(),
                            'type':'changekey', 'fingerprint':fingerprint,
                            'challenge':challenge}}
        self.pending_auth.update(request)
        self.authlog.info("changekey request from hostmask %s for user %s, oldkeyid %s, newkeyid %s." %\
                (msg.prefix, gpgauth['nick'], gpgauth['keyid'], keyid, ))
        irc.reply("Request successful for user %s, hostmask %s. Your challenge string is: %s" %\
                (gpgauth['nick'], msg.prefix, challenge,))
    changekey = wrap(changekey, ['keyid',])

    def echangekey(self, irc, msg, args, keyid):
        """<keyid>
        
        Changes your GPG registered key to <keyid>.
        <keyid> is a 16 digit key id, with or without the '0x' prefix.
        We look on servers listed in 'plugins.GPG.keyservers' config.
        You will be given a link to a page which contains a one time password
        encrypted with your key. Decrypt, and use the 'everify' command with it.
        You must be authenticated in order to use this command.
        """
        self._removeExpiredRequests()
        gpgauth = self._ident(msg.prefix)
        if gpgauth is None:
            irc.error("You must be authenticated in order to change your registered key.")
            return
        if self.db.getByKey(keyid):
            irc.error("This key id already registered. Try a different key.")
            return

        keyservers = self.registryValue('keyservers').split(',')
        try:
            fingerprint = self._recv_key(keyservers, keyid)
        except Exception as e:
            irc.error("Could not retrieve your key from keyserver. "
                    "Either it isn't there, or it is invalid.")
            self.log.info("GPG echangekey: failed to retrieve key %s from keyservers %s. Details: %s" % \
                    (keyid, keyservers, e,))
            return
        challenge = "freenode:#bitcoin-otc:" + hashlib.sha256(os.urandom(128)).hexdigest()[:-8]
        try:
            data = self.gpg.encrypt(challenge + '\n', keyid, always_trust=True)
            if data.status != "encryption ok":
                raise ValueError, "problem encrypting otp"
            otpfn = conf.supybot.directories.data.dirize('otps/%s' % (keyid,))
            f = open(otpfn, 'w')
            f.write(data.data)
            f.close()
        except Exception, e:
            irc.error("Problem creating encrypted OTP file.")
            self.log.info("GPG echangekey: key %s, otp creation %s, exception %s" % \
                    (keyid, data.stderr, e,))
            return
        request = {msg.prefix: {'keyid':keyid,
                            'nick':gpgauth['nick'], 'expiry':time.time(),
                            'type':'echangekey', 'fingerprint':fingerprint,
                            'challenge':challenge}}
        self.pending_auth.update(request)
        self.authlog.info("echangekey request from hostmask %s for user %s, oldkeyid %s, newkeyid %s." %\
                (msg.prefix, gpgauth['nick'], gpgauth['keyid'], keyid, ))
        irc.reply("Request successful for user %s, hostmask %s. Get your encrypted OTP from %s" %\
                (gpgauth['nick'], msg.prefix, 'http://bitcoin-otc.com/otps/%s' % (keyid,),))
    echangekey = wrap(echangekey, ['keyid',])

    def changeaddress(self, irc, msg, args, bitcoinaddress):
        """<bitcoinaddress>
        
        Changes your registered address to <bitcoinaddress>.
        You will be given a random passphrase to sign with your new address, and
        submit to the bot with the 'bcverify' command.
        You must be authenticated in order to use this command.
        """
        self._removeExpiredRequests()
        gpgauth = self._ident(msg.prefix)
        if gpgauth is None:
            irc.error("You must be authenticated in order to change your registered key.")
            return
        if self.db.getByAddr(bitcoinaddress):
            irc.error("This address is already registered. Try a different one.")
            return

        challenge = "freenode:#bitcoin-otc:" + hashlib.sha256(os.urandom(128)).hexdigest()[:-8]
        request = {msg.prefix: {'bitcoinaddress':bitcoinaddress,
                            'nick':gpgauth['nick'], 'expiry':time.time(),
                            'type':'bcchangekey',
                            'challenge':challenge}}
        self.pending_auth.update(request)
        self.authlog.info("changeaddress request from hostmask %s for user %s, oldaddress %s, newaddress %s." %\
                (msg.prefix, gpgauth['nick'], gpgauth['bitcoinaddress'], bitcoinaddress, ))
        irc.reply("Request successful for user %s, hostmask %s. Your challenge string is: %s" %\
                (gpgauth['nick'], msg.prefix, challenge,))
    changeaddress = wrap(changeaddress, ['something'])


    def ident(self, irc, msg, args, nick):
        """[<nick>]
        
        Returns details about your GPG identity with the bot, or notes the
        absence thereof.
        If optional <nick> is given, tells you about <nick> instead.
        """        
        if nick is not None:
            try:
                hostmask = irc.state.nickToHostmask(nick)
            except KeyError:
                irc.error("I am not seeing this user on IRC. "
                        "If you want information about a registered gpg user, "
                        "try the 'gpg info' command instead.")
                return
        else:
            hostmask = msg.prefix
            nick = msg.nick
        response = "Nick '%s', with hostmask '%s', is " % (nick, hostmask,)
        try:
            authinfo = self.authed_users[hostmask]
            if irc.nested:
                response = authinfo['nick']
            else:
                if authinfo['nick'].upper() != nick.upper():
                    response = "\x02CAUTION: irc nick differs from otc registered nick.\x02 " + response
                response += ("identified as user '%s', with GPG key id %s, " + \
                        "key fingerprint %s, and bitcoin address %s") % (authinfo['nick'],
                                authinfo['keyid'],
                                authinfo['fingerprint'],
                                authinfo['bitcoinaddress'])
        except KeyError:
            if irc.nested:
                response = ""
            else:
                response += "not identified."
        irc.reply(response)
    ident = wrap(ident, [optional('something')])

    def _info(self, nick):
        """Return info on registered user. For use from other plugins."""
        result = self.db.getByNick(nick)
        if len(result) == 0:
            return None
        else:
            return result[0]

    def info(self, irc, msg, args, optlist, nick):
        """[--key|--address] <nick>

        Returns the registration details of registered user <nick>.
        If '--key' option is given, interpret <nick> as a GPG key ID.
        """
        if 'key' in dict(optlist).keys():
            result = self.db.getByKey(nick)
        elif 'address' in dict(optlist).keys():
            result = self.db.getByAddr(nick)
        else:
            result = self.db.getByNick(nick)
        if len(result) == 0:
            irc.reply("No such user registered.")
            return
        result = result[0]
        authhost = self._identByNick(result[5])
        if authhost is not None:
            authstatus = " Currently authenticated from hostmask %s ." % (authhost,)
            if authhost.split('!')[0].upper() != result[5].upper():
                authstatus += " CAUTION: irc nick differs from otc registered nick."
        else:
            authstatus = " Currently not authenticated."
        irc.reply("User '%s', with keyid %s, fingerprint %s, and bitcoin address %s, registered on %s, last authed on %s. http://b-otc.com/vg?nick=%s .%s" %\
                (result[5], result[1], result[2], result[3], time.ctime(result[4]),
                time.ctime(result[6]), utils.web.urlquote(result[5]), authstatus))
    info = wrap(info, [getopts({'key': '','address':'',}),'something'])

    def stats(self, irc, msg, args):
        """takes no arguments
        
        Gives the statistics on number of registered users,
        number of authenticated users, number of pending authentications.
        """
        self._removeExpiredRequests()
        try:
            regusers = self.db.getCount()[0][0]
            authedusers = len(self.authed_users)
            pendingauths = len(self.pending_auth)
        except:
            irc.error("Problem retrieving statistics. Try again later.")
            return
        irc.reply("There are %s registered users, %s currently authenticated. "
                "There are also %s pending authentication requests." % \
                (regusers, authedusers, pendingauths,))
    stats = wrap(stats)

    def _ident(self, hostmask):
        """Use to check identity status from other plugins."""
        return self.authed_users.get(hostmask, None)

    def _identByNick(self, nick):
        for k,v in self.authed_users.iteritems():
            if v['nick'].lower() == nick.lower():
                return k
        return None

    def doQuit(self, irc, msg):
        """Kill the authentication when user quits."""
        if irc.network == self.registryValue('network'):
            self._unauth(irc, msg.prefix)

    def doPart(self, irc, msg):
        """Kill the authentication when user parts all channels."""
        channels = self.registryValue('channels').split(';')
        if msg.args[0] in channels and irc.network == self.registryValue('network'):
            for channel in channels:
                try:
                    if msg.nick in irc.state.channels[channel].users:
                        break
                except KeyError:
                    pass #oh well, we're not in one of our monitored channels
            else:
                if ircutils.strEqual(msg.nick, irc.nick): #we're parting
                    self.authlog.info("***** clearing authed_users due to self-part. *****")
                    self.authed_users.clear()
                    self.db.reset_auth_status([])
                else:
                    self._unauth(irc, msg.prefix)

    def doError(self, irc, msg):
        """Reset the auth dict when bot gets disconnected."""
        if irc.network == self.registryValue('network'):
            self.authlog.info("***** clearing authed_users due to network error. *****")
            self.authed_users.clear()
            self.db.reset_auth_status([])

    def doKick(self, irc, msg):
        """Kill the authentication when user gets kicked."""
        channels = self.registryValue('channels').split(';')
        if msg.args[0] in channels and irc.network == self.registryValue('network'):
            (channel, nick) = msg.args[:2]
            if ircutils.toLower(irc.nick) in ircutils.toLower(nick):
                self.authlog.info("***** clearing authed_users due to self-kick. *****")
                self.authed_users.clear()
                self.db.reset_auth_status([])
            else:
                try:
                    hostmask = irc.state.nickToHostmask(nick)
                    self._unauth(irc, hostmask)
                except KeyError:
                    pass

    def doNick(self, irc, msg):
        if msg.prefix in self.authed_users.keys():
            newprefix = msg.args[0] + '!' + msg.prefix.split('!',1)[1]
            logmsg = "Attaching authentication for hostmask %s to new hostmask %s due to nick change." %\
                    (msg.prefix, newprefix,)
            self.authlog.info(logmsg)
            if not world.testing:
                irc.queueMsg(ircmsgs.privmsg("#bitcoin-otc-auth", logmsg))
            self.authed_users[newprefix] = self.authed_users[msg.prefix]
            self._unauth(irc, msg.prefix)
            self.db.set_auth_status(self.authed_users[newprefix]['nick'], 1)

Class = GPG

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# GPG - supybot plugin to authenticate users via GPG keys
# Copyright (C) 2011, Daniel Folkinshteyn <nanotube@users.sourceforge.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###

from supybot.test import *
from supybot import ircmsgs
from supybot import conf
from supybot import irclib
from supybot import utils

try:
    gnupg = utils.python.universalImport('gnupg', 'local.gnupg')
except ImportError:
    raise callbacks.Error, \
            "You need the gnupg module installed to use this plugin." 

try:
    bitcoinsig = utils.python.universalImport('local.bitcoinsig')
except ImportError:
    raise callbacks.Error, \
            "You are possibly missing the ecdsa module." 


from xmlrpclib import ServerProxy
import shutil
import os, os.path
import time
import ecdsa

class GPGTestCase(PluginTestCase):
    plugins = ('GPG','RatingSystem','Utilities')

    def setUp(self):
        PluginTestCase.setUp(self)
        self.testkeyid = "21E2EF9EF2197A66" # set this to a testing key that we have pregenerated
        self.testkeyfingerprint = "0A969AE0B143927F9D473F3E21E2EF9EF2197A66"
        self.secringlocation = '/tmp/secring.gpg' #where we store our testing secring (normal location gets wiped by test env)
        self.cb = self.irc.getCallback('GPG')
        self.s = ServerProxy('http://paste.debian.net/server.pl')
        shutil.copy(self.secringlocation, self.cb.gpg.gnupghome)
        
        chan = irclib.ChannelState()
        chan.addUser('test')
        chan.addUser('authedguy2')
        self.irc.state.channels['#test'] = chan

        #preseed the GPG db with a GPG registration and auth with some users
        gpg = self.irc.getCallback('GPG')
        gpg.db.register('AAAAAAAAAAAAAAA1', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA1', 'someaddr',
                    time.time(), 'nanotube')
        gpg.authed_users['nanotube!stuff@stuff/somecloak'] = {'nick':'nanotube',
                'keyid':'AAAAAAAAAAAAAAA1', 'fingerprint':'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA1',
                'bitcoinaddress':'1nthoeubla'}
        gpg.db.register('AAAAAAAAAAAAAAA2', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA2', 'someaddr',
                    time.time(), 'registeredguy')
        gpg.db.register('AAAAAAAAAAAAAAA3', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA3', 'someaddr',
                    time.time(), 'authedguy')
        gpg.authed_users['authedguy!stuff@123.345.234.34'] = {'nick':'authedguy',
                'keyid':'AAAAAAAAAAAAAAA3', 'fingerprint':'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA3',
                'bitcoinaddress':'1nthoeubla'}
        gpg.db.register('AAAAAAAAAAAAAAA4', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA4', None,
                    time.time(), 'authedguy2')
        gpg.authed_users['authedguy2!stuff@123.345.234.34'] = {'nick':'authedguy2',
                'keyid':'AAAAAAAAAAAAAAA4', 'fingerprint':'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA4',
                'bitcoinaddress':None}
        gpg.db.register('AAAAAAAAAAAAAAA5', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA5', 'someaddr',
                    time.time(), 'registered_guy')
        gpg.db.register('AAAAAAAAAAAAAAA6', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA6', 'someaddr',
                    time.time(), 'registe%redguy')

        # create the test ecdsa keypair and resulting bitcoin address
        #~ self.private_key = ecdsa.SigningKey.from_string( '5JkuZ6GLsMWBKcDWa5QiD15Uj467phPR', curve = bitcoinsig.SECP256k1 )
        #~ self.public_key = self.private_key.get_verifying_key()
        #~ self.bitcoinaddress = bitcoinsig.public_key_to_bc_address( '04'.decode('hex') + self.public_key.to_string() )

        #set config to match test environment
        ocn = conf.supybot.plugins.GPG.network()
        conf.supybot.plugins.GPG.network.setValue('test')
        occ = conf.supybot.plugins.GPG.channels()
        conf.supybot.plugins.GPG.channels.setValue('#test')

    def tearDown(self):
        gpg = self.irc.getCallback('GPG')
        gpg.authed_users = {}
        gpg.pending_auth = {}
        PluginTestCase.tearDown(self)

    def testRegister(self):
        # default test user hostmask: test!user@host.domain.tld
        self.assertRegexp('gpg ident', 'not identified')
        self.assertError('register someone 0xBADKEY')
        self.assertError('register someone 0x23420982') # bad length
        self.assertError('register someone 0xAAAABBBBCCCCDDDD') #doesn't exist
        m = self.getMsg('register someone %s' % (self.testkeyid,)) #test without keyserver arg
        self.failUnless('Request successful' in str(m))
        challenge = str(m).split('is: ')[1]
        sd = self.cb.gpg.sign(challenge, keyid = self.testkeyid)
        rc = self.s.paste.addPaste(sd.data, 'gpgtest', 60)
        pasteid = rc['id']
        self.assertRegexp('verify http://paste.debian.net/plain/%s/' % (pasteid,), 
                    'Registration successful. You are now authenticated')

        #are we identified?
        self.assertRegexp('gpg ident', 'is identified')
        self.assertRegexp('gpg ident test', 'is identified')

        #duplicate nick/key registrations
        self.assertError('register someone BBBBBBBBCCCCDDDD') # dupe username
        self.assertError('register newguy %s' % (self.testkeyid,)) #dupe keyid

    def testEregister(self):
        # default test user hostmask: test!user@host.domain.tld
        self.assertRegexp('gpg ident', 'not identified')
        self.assertError('eregister someone 0xBADKEY')
        self.assertError('eregister someone 0x23420982') # bad length
        self.assertError('eregister someone 0xAAAABBBBCCCCDDDD') #doesn't exist
        m = self.getMsg('eregister someone %s' % (self.testkeyid,)) #test without keyserver arg
        self.failUnless('Request successful' in str(m))
        encrypteddata = open(os.path.join(os.getcwd(), 'test-data/otps/%s' % (self.testkeyid,)), 'r').read()
        decrypted = self.cb.gpg.decrypt(encrypteddata)
        self.assertRegexp('everify %s' % (decrypted.data.strip(),), 
                    'Registration successful. You are now authenticated')

        #are we identified?
        self.assertRegexp('gpg ident', 'is identified')
        self.assertRegexp('gpg ident test', 'is identified')

        #duplicate nick/key registrations
        self.assertError('eregister someone BBBBBBBBCCCCDDDD') # dupe username
        self.assertError('eregister newguy %s' % (self.testkeyid,)) #dupe keyid

    def testBcregister(self):
        # create the test ecdsa keypair and resulting bitcoin address
        private_key = ecdsa.SigningKey.from_string( '5JkuZ6GLsMWBKcDWa5QiD15Uj467phPR', curve = bitcoinsig.SECP256k1 )
        public_key = private_key.get_verifying_key()
        bitcoinaddress = bitcoinsig.public_key_to_bc_address( '04'.decode('hex') + public_key.to_string() )
        
        # default test user hostmask: test!user@host.domain.tld
        self.assertRegexp('gpg ident', 'not identified')
        m = self.getMsg('bcregister someone %s' % (bitcoinaddress,))
        self.failUnless('Request successful' in str(m))
        challenge = str(m).split('is: ')[1].strip()
        sig = bitcoinsig.sign_message(private_key, challenge)
        time.sleep(1)
        self.assertRegexp('bcverify %s' % (sig,),
                    'Registration successful. You are now authenticated')
        self.assertRegexp('gpg ident', 'is identified')

    def testIdent(self):
        self.prefix = 'authedguy!stuff@123.345.234.34'
        self.assertRegexp('gpg ident', 'is identified')
        self.assertRegexp('gpg ident authedguy', 'is identified')
        self.assertResponse('echo [gpg ident]', 'authedguy')

    def testStats(self):
        self.assertRegexp('gpg stats', '6 registered users.*3 currently authenticated.*0 pending auth')
        self.assertNotError('gpg auth nanotube')
        self.assertRegexp('gpg stats', '6 registered users.*3 currently authenticated.*1 pending auth')

    def testUnauth(self):
        self.prefix = 'authedguy2!stuff@123.345.234.34'
        self.assertRegexp('gpg ident', 'is identified')
        self.assertRegexp('gpg unauth', 'has been terminated')
        self.assertRegexp('gpg ident', 'not identified')

    def testAuth(self):
        self.assertNotError('gpg register bla %s' % (self.testkeyid,)) # just to get the pubkey into the keyring
        gpg = self.irc.getCallback('GPG')
        gpg.db.register(self.testkeyid, self.testkeyfingerprint,'1somebitcoinaddress',
                    time.time(), 'someone')
        m = self.getMsg('auth someone')
        self.failUnless('Request successful' in str(m))
        challenge = str(m).split('is: ')[1]
        sd = self.cb.gpg.sign(challenge, keyid = self.testkeyid)
        rc = self.s.paste.addPaste(sd.data, 'gpgtest', 60)
        pasteid = rc['id']
        self.assertRegexp('verify http://paste.debian.net/plain/%s/' % (pasteid,),
                    'You are now authenticated')
        self.assertRegexp('gpg ident', 'is identified')

    def testEauth(self):
        self.assertNotError('gpg register bla %s' % (self.testkeyid,)) # just to get the pubkey into the keyring
        gpg = self.irc.getCallback('GPG')
        gpg.db.register(self.testkeyid, self.testkeyfingerprint, 'someaddr',
                    time.time(), 'someone')
        self.assertNotError('eauth someone')
        m = self.getMsg('eauth someone')
        self.failUnless('Request successful' in str(m))
        encrypteddata = open(os.path.join(os.getcwd(), 'test-data/otps/%s' % (self.testkeyid,)), 'r').read()
        decrypted = self.cb.gpg.decrypt(encrypteddata)
        self.assertRegexp('everify %s' % (decrypted.data.strip(),), 'You are now authenticated')
        self.assertRegexp('gpg ident', 'is identified')

    def testBcauth(self):
        # create the test ecdsa keypair and resulting bitcoin address
        private_key = ecdsa.SigningKey.from_string( '5JkuZ6GLsMWBKcDWa5QiD15Uj467phPR', curve = bitcoinsig.SECP256k1 )
        public_key = private_key.get_verifying_key()
        bitcoinaddress = bitcoinsig.public_key_to_bc_address( '04'.decode('hex') + public_key.to_string() )
        
        gpg = self.irc.getCallback('GPG')
        gpg.db.register(self.testkeyid, self.testkeyfingerprint, bitcoinaddress,
                    time.time(), 'someone')
        m = self.getMsg('bcauth someone')
        self.failUnless('Request successful' in str(m))
        challenge = str(m).split('is: ')[1].strip()
        sig = bitcoinsig.sign_message(private_key, challenge)
        time.sleep(1)
        self.assertRegexp('bcverify %s' % (sig,), 'You are now authenticated')

    #~ def testChangenick(self):
        #~ self.assertError('gpg changenick somethingnew') #not authed
        #~ self.prefix = 'authedguy2!stuff@123.345.234.34'
        #~ self.assertRegexp('gpg ident', 'is identified')
        #~ self.assertRegexp('gpg changenick mycoolnewnick',
                #~ 'changed your nick from authedguy2 to mycoolnewnick')
        #~ self.assertRegexp('gpg ident authedguy2', 'identified as user mycoolnewnick')
        #~ self.assertRegexp('gpg info mycoolnewnick', "User 'mycoolnewnick'.* registered on")

    def testChangekey(self):
        self.assertError('gpg changekey AAAAAAAAAAAAAAA1') #not authed
        self.prefix = 'authedguy2!stuff@123.345.234.34'
        self.assertRegexp('gpg ident', 'is identified')
        m = self.getMsg('gpg changekey %s' % (self.testkeyid,))
        self.failUnless('Request successful' in str(m))
        challenge = str(m).split('is: ')[1]
        sd = self.cb.gpg.sign(challenge, keyid = self.testkeyid)
        rc = self.s.paste.addPaste(sd.data, 'gpgtest', 60)
        pasteid = rc['id']
        self.assertRegexp('verify http://paste.debian.net/plain/%s/' % (pasteid,),
                    'Successfully changed key.*You are now authenticated')
        self.assertRegexp('gpg ident', 'is identified.*key id %s' % (self.testkeyid,))

    def testEchangekey(self):
        self.assertError('gpg echangekey AAAAAAAAAAAAAAA1') #not authed
        self.prefix = 'authedguy2!stuff@123.345.234.34'
        self.assertRegexp('gpg ident', 'is identified')
        m = self.getMsg('gpg echangekey %s' % (self.testkeyid,))
        self.failUnless('Request successful' in str(m))
        encrypteddata = open(os.path.join(os.getcwd(), 'test-data/otps/%s' % (self.testkeyid,)), 'r').read()
        decrypted = self.cb.gpg.decrypt(encrypteddata)
        self.assertRegexp('everify %s' % (decrypted.data.strip(),),
                    'Successfully changed key.*You are now authenticated')
        self.assertRegexp('gpg ident', 'is identified.*key id %s' % (self.testkeyid,))

    def testChangeaddress(self):
        # create the test ecdsa keypair and resulting bitcoin address
        private_key = ecdsa.SigningKey.from_string( '5JkuZ6GLsMWBKcDWa5QiD15Uj467phPR', curve = bitcoinsig.SECP256k1 )
        public_key = private_key.get_verifying_key()
        bitcoinaddress = bitcoinsig.public_key_to_bc_address( '04'.decode('hex') + public_key.to_string() )

        self.assertError('gpg changeaddress 1sntoheu') #not authed
        self.prefix = 'authedguy2!stuff@123.345.234.34'
        self.assertRegexp('gpg ident', 'is identified')
        m = self.getMsg('gpg changeaddress %s' % (bitcoinaddress,))
        self.failUnless('Request successful' in str(m))
        challenge = str(m).split('is: ')[1].strip()
        sig = bitcoinsig.sign_message(private_key, challenge)
        time.sleep(1)
        self.assertRegexp('bcverify %s' % (sig,),
                    'Successfully changed address.*You are now authenticated')
        self.assertRegexp('gpg ident', 'is identified.*address %s' % (bitcoinaddress,))
        self.assertRegexp('gpg info authedguy2', 'address %s' % (bitcoinaddress,))

    def testNick(self):
        self.prefix = 'authedguy2!stuff@123.345.234.34'
        self.assertRegexp('gpg ident', 'is identified')
        self.irc.feedMsg(msg=ircmsgs.nick('newnick', prefix=self.prefix))
        self.assertRegexp('gpg ident', 'not identified')
        self.prefix = 'newnick' + '!' + self.prefix.split('!',1)[1]
        self.assertRegexp('gpg ident', 'is identified')

    def testOuit(self):
        self.prefix = 'authedguy!stuff@123.345.234.34'
        self.irc.feedMsg(msg=ircmsgs.quit(prefix=self.prefix))
        self.assertRegexp('gpg ident', 'not identified')
        chan = irclib.ChannelState()

    def testPart(self):
        self.prefix = 'authedguy!stuff@123.345.234.34'
        self.assertRegexp('gpg ident', 'is identified')
        self.irc.feedMsg(msg=ircmsgs.part("#test", prefix=self.prefix))
        self.assertRegexp('gpg ident', 'not identified')

    def testKick(self):
        # do it as the stock test user, because he has admin capability and can kick
        gpg = self.irc.getCallback('GPG')
        gpg.authed_users['test!user@host.domain.tld'] = {'nick':'test',
                'keyid':'AAAAAAAAAAAAAAA4', 'fingerprint':'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA4',
                'bitcoinaddress':'1blabsanthoeu'}
        self.prefix = 'test!user@host.domain.tld' 
        self.assertRegexp('gpg ident', 'is identified')
        self.irc.feedMsg(msg=ircmsgs.kick("#test", 'test', prefix=self.prefix))
        self.assertRegexp('gpg ident', 'not identified')

    def testInfo(self):
        self.assertRegexp('gpg info registeredguy', "User 'registeredguy'.*registered on.*Currently not authenticated")
        self.assertRegexp('gpg info authedguy', "User 'authedguy'.*registered on.*Currently authenticated")
        self.assertRegexp('gpg info authEDguY', "User 'authedguy'.*registered on.*Currently authenticated")
        self.assertRegexp('gpg info AAAAAAAAAAAAAAA1', "No such user registered")
        self.assertRegexp('gpg info --key AAAAAAAAAAAAAAA1', "User 'nanotube'.*registered on")
        self.assertRegexp('gpg info authedgu_', "No such user registered")
        self.assertRegexp('gpg info authed%', "No such user registered")
        self.assertRegexp('gpg info registered_guy', "User 'registered_guy'")
        self.assertRegexp('gpg info registe%redguy', "User 'registe%redguy'")

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# GPGExt - supybot plugin to verify user identity on external sites using GPG keys
# Copyright (C) 2011, Daniel Folkinshteyn <nanotube@users.sourceforge.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('GPGExt', True)


GPGExternal = conf.registerPlugin('GPGExt')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(GPGExternal, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# GPGExt - supybot plugin to verify user identity on external sites using GPG keys
# Copyright (C) 2011, Daniel Folkinshteyn <nanotube@users.sourceforge.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

import re
import base64
from lxml import etree

# regexp to match the gpg_identity tag
# make sure to drop any html tags a site may add after.
gpgtagre = re.compile(r'gpg_identity=([^\s<]+)')

class GPGExt(callbacks.Plugin):
    """This plugin uses the external gpg identity protocol to verify
    a user's identity on external site using his registered GPG key.
    http://wiki.bitcoin-otc.com/wiki/GPG_Identity_Protocol
    Depends on the GPG plugin."""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(GPGExt, self)
        self.__parent.__init__(irc)

    def _checkGPGAuth(self, irc, prefix):
        return irc.getCallback('GPG')._ident(prefix)

    def _checkGPGReg(self, irc, nick):
        return irc.getCallback('GPG').db.getByNick(nick)

    def _verifySetup(self, irc, msg, nick):
        """Initial verification setup."""
        result = {}
        if nick is None:
            gpgauth = self._checkGPGAuth(irc, msg.prefix)
            if gpgauth is not None:
                nick = gpgauth['nick']
            else:
                nick = msg.nick
        gpgreg = self._checkGPGReg(irc, nick)
        if len(gpgreg) == 0:
            result['error'] = "Nick %s not registered in GPG database." % (nick,)
            return result
        keyid = gpgreg[0][1]
        result['nick'] = nick
        result['keyid'] = keyid
        return result

    def _verifyCont(self, irc, msg, pagedata):
        """Next step, process the gpg identity tag."""
        result = {}
        m = gpgtagre.search(pagedata)
        if m is None:
            result['error'] = "GPG identity tag not found on target page."
            return result
        data = m.group(1)
        if '.' in data: # this is a url
            try:
                signedmsg = utils.web.getUrl(data)
            except:
                result['error'] = "Can't retrieve signature from link '%s' in GPG identity tag." % (data,)
                return result
        else:
            try:
                signedmsg = base64.b64decode(data)
            except:
                result['error'] = "Problems base64 decoding key data."
                return result
        try:
            m = re.search(r'-----BEGIN PGP SIGNED MESSAGE-----.*?\n-----END PGP SIGNATURE-----', signedmsg, re.S)
            signedmsg = m.group(0)
        except:
            result['error'] = "Malformed signed message."
            return result
        result['signedmsg'] = signedmsg
        return result


    def _verifyGPGSigData(self, irc, data, keyid):
        """verify data, return site and nick dict if all good, return dict with 'error' otherwise."""
        site = re.search(r'^site: (.*)$', data, re.M)
        user = re.search(r'^user: (.*)$', data, re.M)
        if site is None or user is None:
            return {'error':'Site or user data not found in signed message'}
        try:
            vo = irc.getCallback('GPG').gpg.verify(data)
            if not vo.valid:
                return {'error': 'Signature verification failed.'}
            if vo.key_id != keyid:
                return {'error': 'Signature is not made with the key on record for this nick.'}
        except:
            return {'error':'Signature verification failed.'}
        return {'site':site.group(1), 'user':user.group(1)}

    def verify(self, irc, msg, args, url, nick):
        """<url> [<nick>]
        
        Pulls the gpg signature data from <url>, and verifies it against <nick>'s
        registered gpg key. If <nick> is omitted, uses the requestor's registered nick.
        """
        result = self._verifySetup(irc, msg, nick)
        if result.has_key('error'):
            irc.error(result['error'])
            return
        try:
            pagedata = utils.web.getUrl(url)
        except:
            irc.error("Problem retrieving target url.")
            return
        result.update(self._verifyCont(irc, msg, pagedata))
        if result.has_key('error'):
            irc.error(result['error'])
            return
        result.update(self._verifyGPGSigData(irc, result['signedmsg'], result['keyid']))
        if result.has_key('error'):
            irc.error("GPG identity tag failed to verify with key id %s. Reason: %s" % \
                    (result['keyid'], result['error']))
            return
        irc.reply("Verified signature made with keyid %s, belonging to OTC user %s, "
                "for site %s and user %s. "
                "Note that you must still verify manually that (1) the site and username "
                "match the content of signed message, and (2) that the GPG identity tag "
                "was posted in user-only accessible area of the site." % \
                (result['keyid'], result['nick'], result['site'], result['user'],))
    verify = wrap(verify, ['httpUrl',optional('something')])

    def ebay(self, irc, msg, args, ebaynick, nick):
        """<ebaynick> [<nick>]
        
        Pulls the gpg signature data from <ebaynick> myworld profile on ebay,
        and verifies it against <nick>'s registered gpg key. 
        If <nick> is omitted, uses the requestor's registered nick.
        """
        result = self._verifySetup(irc, msg, nick)
        if result.has_key('error'):
            irc.error(result['error'])
            return
        try:
            url = 'http://myworld.ebay.com/' + ebaynick
            pagedata = utils.web.getUrl(url)
        except:
            irc.error("Problem retrieving target url: %s" % (url,))
            return

        # ebay special: process ebay page
        parser = etree.HTMLParser()
        tree = etree.parse(url, parser)
        context = etree.iterwalk(tree, tag='div')
        ebaybio = ''
        for _, element in context:
            for item in element.items():
                if item[0] == 'id' and item[1] == 'PortalColumnTwo':
                    ebaybio = etree.tostring(element)

        result.update(self._verifyCont(irc, msg, ebaybio))
        if result.has_key('error'):
            irc.error(result['error'])
            return
        result.update(self._verifyGPGSigData(irc, result['signedmsg'], result['keyid']))
        if result.has_key('error'):
            irc.error("GPG identity tag failed to verify with key id %s. Reason: %s" % \
                    (result['keyid'], result['error']))
            return

        #ebay special: check for match of user and site
        if result['user'].lower() != ebaynick.lower() or not re.match(r'(http://)?(www.)?ebay.com', result['site']):
            irc.error("Site or user do not match.")
            return

        irc.reply("Verified signature made with keyid %s, belonging to OTC user %s, "
                "for site %s and user %s. " % \
                (result['keyid'], result['nick'], result['site'], result['user'],))
    ebay = wrap(ebay, ['something',optional('something')])

Class = GPGExt


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# GPGExt - supybot plugin to verify user identity on external sites using GPG keys
# Copyright (C) 2011, Daniel Folkinshteyn <nanotube@users.sourceforge.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###

from supybot.test import *

class GPGExtTestCase(PluginTestCase):
    plugins = ('GPGExt','GPG')

    def setUp(self):
        PluginTestCase.setUp(self)

        #preseed the GPG db with a GPG registration and auth for mndrix
        gpg = self.irc.getCallback('GPG')
        gpg.db.register('CE52C98A48081991', '60E2810AB29BE577E40EF118CE52C98A48081991',
                    time.time(), 'mndrix')
        gpg.authed_users['mndrix!stuff@stuff/somecloak'] = {'nick':'mndrix'}
        gpg.gpg.recv_keys('pgp.mit.edu', 'CE52C98A48081991')
        gpg.db.register('E7F938BEC95594B2', 'D8B11AAC59A873B0F38D475CE7F938BEC95594B2',
                    time.time(), 'nanotube')
        gpg.gpg.recv_keys('pgp.mit.edu', 'E7F938BEC95594B2')

    def testVerify(self):
        self.assertRegexp('GPGExt verify http://myworld.ebay.com/mndrix mndrix', 'Verified signature')
        self.prefix =  'mndrix!stuff@stuff/somecloak'
        self.assertRegexp('GPGExt verify http://www.bitcoin.org/smf/index.php?action=profile;u=2538', 'Verified signature')
        self.assertError('GPGExt verify badurl') # bad url
        self.assertError('GPGExt verify http://google.com') #no tag
        self.assertError('GPGExt verify http://google.com nosuchuser') #bad user
        self.assertRegexp('GPGExt verify http://nanotube.users.sourceforge.net nanotube', 'Verified signature')

    def testEbay(self):
        self.assertRegexp('GPGExt ebay mndrix mndrix', 'Verified signature')
        self.assertError('GPGExt ebay mndrix nanotube')

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2011, remote
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Market', True)


Market = conf.registerPlugin('Market')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Market, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))
conf.registerGlobalValue(Market, 'fullDepthCachePeriod',
     registry.PositiveInteger(245, """Number of seconds to cache the
     full depth data from mtgox, to avoid getting banned."""))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011, remote
# Copyright (c) 2011, nanotube
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot import conf
from supybot import world
from supybot.utils.seq import dameraulevenshtein

import re
import json
import urllib2
import time
import traceback

opener = urllib2.build_opener()
opener.addheaders = [('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64; rv:22.0) Gecko/20100101 Firefox/22.0')]
urlopen = opener.open

def getNonNegativeFloat(irc, msg, args, state, type='non-negative floating point number'):
    try:
        v = float(args[0])
        if v < 0:
            raise ValueError, "only non-negative numbers allowed."
        state.args.append(v)
        del args[0]
    except ValueError:
        state.errorInvalid(type, args[0])

def getPositiveFloat(irc, msg, args, state, type='positive floating point number'):
    try:
        v = float(args[0])
        if v <= 0:
            raise ValueError, "only positive numbers allowed."
        state.args.append(v)
        del args[0]
    except ValueError:
        state.errorInvalid(type, args[0])

def getCurrencyCode(irc, msg, args, state, type='currency code'):
    v = args[0]
    m = re.search(r'^([A-Za-z]{3})$', v)
    if m is None:
        state.errorInvalid(type, args[0])
        return
    state.args.append(m.group(1).upper())
    del args[0]

def getTo(irc, msg, args, state):
    if args[0].lower() in ['in', 'to']:
        args.pop(0)

addConverter('nonNegativeFloat', getNonNegativeFloat)
addConverter('positiveFloat', getPositiveFloat)
addConverter('currencyCode', getCurrencyCode)
addConverter('to', getTo)

class Market(callbacks.Plugin):
    """Add the help for "@plugin help Market" here
    This should describe *how* to use this plugin."""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(Market, self)
        self.__parent.__init__(irc)
        self.lastdepthfetch = 0
        self.depth_cache = {}
        self.currency_cache = {}
        self.ticker_cache = {}
        self.ticker_supported_markets = {'btce':'BTC-E', 'btsp':'Bitstamp',
                'bfx':'Bitfinex', 'btcde':'Bitcoin.de', 'cbx':'CampBX',
                'btcn':'BTCChina', 'btcavg':'BitcoinAverage', 'coinbase':'Coinbase',
                'krk':'Kraken', 'bitmynt':'bitmynt.no', 'bcent':'Bitcoin-Central'}
        self.depth_supported_markets = {'btsp':'Bitstamp', 'krk':'Kraken',
                'btcn':'BTCChina', 'bcent':'Bitcoin-Central'}

    def _queryYahooRate(self, cur1, cur2):
        try:
            cachedvalue = self.currency_cache[cur1+cur2]
            if time.time() - cachedvalue['time'] < 60:
                return cachedvalue['rate']
        except KeyError:
            pass
        queryurl = "http://query.yahooapis.com/v1/public/yql?q=select%%20*%%20from%%20yahoo.finance.xchange%%20where%%20pair=%%22%s%s%%22&env=store://datatables.org/alltableswithkeys&format=json"
        yahoorate = utils.web.getUrl(queryurl % (cur1, cur2,))
        yahoorate = json.loads(yahoorate, parse_float=str, parse_int=str)
        rate = yahoorate['query']['results']['rate']['Rate']
        if float(rate) == 0:
            raise ValueError, "no data"
        self.currency_cache[cur1 + cur2] = {'time':time.time(), 'rate':rate}
        return rate

    def _getMtgoxDepth(self, currency='USD'):
        if world.testing: # avoid hammering api when testing.
            self.depth_cache['mtgox'] = {'time':time.time(), 
                    'depth':json.load(open('/tmp/mtgox.depth.json'))['return']}
            self.depth_cache['mtgox']['depth']['bids'].reverse()
            return
        try:
            cachedvalue = self.depth_cache['mtgox']
            if time.time() - cachedvalue['time'] < self.registryValue('fullDepthCachePeriod'):
                return
        except KeyError:
            pass
        try:
            data = urlopen('http://data.mtgox.com/api/1/BTCUSD/depth/full').read()
            vintage = time.time()
            depth = json.loads(data)['return']
            depth['bids'].reverse() # bids should be listed in descending order
            self.depth_cache['mtgox'] = {'time':vintage, 'depth':depth}
        except:
            pass # oh well, try again later.

    def _getBtspDepth(self, currency='USD'):
        if world.testing: # avoid hammering api when testing.
            depth = json.load(open('/tmp/bitstamp.depth.json'))
            depth['bids'] = [{'price':float(b[0]), 'amount':float(b[1])} for b in depth['bids']]
            depth['asks'] = [{'price':float(b[0]), 'amount':float(b[1])} for b in depth['asks']]
            self.depth_cache['btsp'+currency] = {'time':time.time(), 'depth':depth}
            return
        try:
            cachedvalue = self.depth_cache['btsp'+currency]
            if time.time() - cachedvalue['time'] < self.registryValue('fullDepthCachePeriod'):
                return
        except KeyError:
            pass
        yahoorate = 1
        if currency != 'USD':
            yahoorate = float(self._queryYahooRate('USD', currency))
        try:
            stddepth = {}
            data = urlopen('https://www.bitstamp.net/api/order_book/').read()
            vintage = time.time()
            depth = json.loads(data)
            # make consistent format with mtgox
            depth['bids'] = [{'price':float(b[0])*yahoorate, 'amount':float(b[1])} for b in depth['bids']]
            depth['asks'] = [{'price':float(b[0])*yahoorate, 'amount':float(b[1])} for b in depth['asks']]
            self.depth_cache['btsp'+currency] = {'time':vintage, 'depth':depth}
        except:
            pass # oh well, try again later.

    def _getKrkDepth(self, currency='EUR'):
        if world.testing: # avoid hammering api when testing.
            depth = json.load(open('/tmp/kraken.depth.json'))
            depth = depth['result'][depth['result'].keys()[0]]
            depth['bids'] = [{'price':float(b[0]), 'amount':float(b[1])} for b in depth['bids']]
            depth['asks'] = [{'price':float(b[0]), 'amount':float(b[1])} for b in depth['asks']]
            self.depth_cache['krk'+currency] = {'time':time.time(), 'depth':depth}
            return
        try:
            cachedvalue = self.depth_cache['krk'+currency]
            if time.time() - cachedvalue['time'] < self.registryValue('fullDepthCachePeriod'):
                return
        except KeyError:
            pass
        yahoorate = 1
        try:
            stddepth = {}
            data = urlopen('https://api.kraken.com/0/public/Depth?pair=XBT%s' % (currency,)).read()
            depth = json.loads(data)
            vintage = time.time()
            if len(depth['error']) != 0:
                if "Unknown asset pair" in ticker['error'][0]:
                    # looks like we have unsupported currency, default to EUR
                    depth = json.loads(urlopen("https://api.kraken.com/0/public/Depth?pair=XBTEUR").read())
                    if len(depth['error']) != 0:
                        return # oh well try again later
                    try:
                        stddepth = {'warning':'using yahoo currency conversion'}
                        yahoorate = float(self._queryYahooRate('EUR', currency))
                    except:
                        return # oh well try again later
                else:
                    return
            depth = depth['result'][depth['result'].keys()[0]]
            # make consistent format with mtgox
            stddepth.update({'bids': [{'price':float(b[0])*yahoorate, 'amount':float(b[1])} for b in depth['bids']],
                    'asks': [{'price':float(b[0])*yahoorate, 'amount':float(b[1])} for b in depth['asks']]})
            self.depth_cache['krk'+currency] = {'time':vintage, 'depth':stddepth}
        except:
            pass # oh well, try again later.

    def _getBcentDepth(self, currency='EUR'):
        if world.testing: # avoid hammering api when testing.
            depth = json.load(open('/tmp/bcent.depth.json'))
            depth['bids'] = [{'price':float(b['price']), 'amount':float(b['amount'])} for b in depth['bids']]
            depth['bids'].reverse() # want bids in descending order
            depth['asks'] = [{'price':float(b['price']), 'amount':float(b['amount'])} for b in depth['asks']]
            self.depth_cache['bcent'+currency] = {'time':time.time(), 'depth':depth}
            return
        try:
            cachedvalue = self.depth_cache['bcent'+currency]
            if time.time() - cachedvalue['time'] < self.registryValue('fullDepthCachePeriod'):
                return
        except KeyError:
            pass
        yahoorate = 1
        try:
            stddepth = {}
            data = urlopen('https://bitcoin-central.net/api/v1/data/eur/depth').read()
            depth = json.loads(data)
            vintage = time.time()
            if currency != 'EUR':
                yahoorate = float(self._queryYahooRate('EUR', currency))
            if depth.has_key('errors'):
                return
            # make consistent format with mtgox
            stddepth.update({'bids': [{'price':float(b['price'])*yahoorate, 'amount':float(b['amount'])} for b in depth['bids']],
                    'asks': [{'price':float(b['price'])*yahoorate, 'amount':float(b['amount'])} for b in depth['asks']]})
            stddepth['bids'].reverse()
            self.depth_cache['bcent'+currency] = {'time':vintage, 'depth':stddepth}
        except:
            pass # oh well, try again later.

    def _getBtcnDepth(self, currency='CNY'):
        yahoorate = 1
        if world.testing: # avoid hammering api when testing.
            depth = json.load(open('/tmp/btcchina.depth.json'))
            depth['bids'] = [{'price':float(b[0])*yahoorate, 'amount':float(b[1])} for b in depth['bids']]
            depth['asks'] = [{'price':float(b[0])*yahoorate, 'amount':float(b[1])} for b in depth['asks']]
            depth['asks'].reverse() # asks should be listed in ascending order
            self.depth_cache['btcn'+currency] = {'time':time.time(), 'depth':depth}
            return
        try:
            cachedvalue = self.depth_cache['btcn'+currency]
            if time.time() - cachedvalue['time'] < self.registryValue('fullDepthCachePeriod'):
                return
        except KeyError:
            pass
        if currency != 'CNY':
            yahoorate = float(self._queryYahooRate('CNY', currency))
        try:
            data = urlopen('https://data.btcchina.com/data/orderbook').read()
            vintage = time.time()
            depth = json.loads(data)
            # make consistent format with mtgox
            depth['bids'] = [{'price':float(b[0])*yahoorate, 'amount':float(b[1])} for b in depth['bids']]
            depth['asks'] = [{'price':float(b[0])*yahoorate, 'amount':float(b[1])} for b in depth['asks']]
            depth['asks'].reverse() # asks should be listed in ascending order
            self.depth_cache['btcn'+currency] = {'time':vintage, 'depth':depth}
        except:
            pass # oh well, try again later.

    def _getMtgoxTicker(self, currency):
        stdticker = {}
        yahoorate = 1
        if world.testing and currency == 'USD':
            ticker = json.load(open('/tmp/mtgox.ticker.json'))
        else:
            try:
                cachedvalue = self.ticker_cache['mtgox'+currency]
                if time.time() - cachedvalue['time'] < 3:
                    return cachedvalue['ticker']
            except KeyError:
                pass
            try:
                json_data = urlopen("https://data.mtgox.com/api/2/BTC%s/money/ticker" % (currency.upper(),)).read()
                ticker = json.loads(json_data)
            except Exception, e:
                ticker = {"result":"error", "error":e}
            try:
                ftj = urlopen("https://data.mtgox.com/api/2/BTC%s/money/ticker_fast" % (currency.upper(),)).read()
                tf = json.loads(ftj)
            except Exception, e:
                tf = {"result":"error", "error":e}
            if ticker['result'] == 'error' and currency != 'USD':
                # maybe currency just doesn't exist, so try USD and convert.
                ticker = json.loads(urlopen("https://data.mtgox.com/api/2/BTCUSD/money/ticker").read())
                try:
                    stdticker = {'warning':'using yahoo currency conversion'}
                    yahoorate = float(self._queryYahooRate('USD', currency))
                except:
                    stdticker = {'error':'failed to get currency conversion from yahoo.'}
                    return stdticker
            if ticker['result'] != 'error' and tf['result'] != 'error': # use fast ticker where available
                ticker['data']['buy']['value'] = tf['data']['buy']['value']
                ticker['data']['sell']['value'] = tf['data']['sell']['value']
                ticker['data']['last']['value'] = tf['data']['last']['value']
        if ticker['result'] == 'error':
             stdticker = {'error':ticker['error']}
        else:
            stdticker.update({'bid': float(ticker['data']['buy']['value'])*yahoorate,
                                'ask': float(ticker['data']['sell']['value'])*yahoorate,
                                'last': float(ticker['data']['last']['value'])*yahoorate,
                                'vol': ticker['data']['vol']['value'],
                                'low': float(ticker['data']['low']['value'])*yahoorate,
                                'high': float(ticker['data']['high']['value'])*yahoorate,
                                'avg': float(ticker['data']['vwap']['value'])*yahoorate})
        self.ticker_cache['mtgox'+currency] = {'time':time.time(), 'ticker':stdticker}
        return stdticker

    def _getBtceTicker(self, currency):
        try:
            cachedvalue = self.ticker_cache['btce'+currency]
            if time.time() - cachedvalue['time'] < 3:
                return cachedvalue['ticker']
        except KeyError:
            pass
        stdticker = {}
        if currency.lower() in ['ltc', 'nmc']:
            pair = '%s_btc' % (currency.lower(),)
        else:
            pair = 'btc_%s' % (currency.lower(),)
        json_data = urlopen("https://btc-e.com/api/2/%s/ticker" % (pair,)).read()
        ticker = json.loads(json_data)
        yahoorate = 1
        if ticker.has_key('error'):
            # maybe we have unsupported currency
            ticker = json.loads(urlopen("https://btc-e.com/api/2/btc_usd/ticker").read())
            if ticker.has_key('error'):
                stdticker = {'error':ticker['error']}
                return stdticker
            try:
                stdticker = {'warning':'using yahoo currency conversion'}
                yahoorate = float(self._queryYahooRate('USD', currency))
            except:
                stdticker = {'error':'failed to get currency conversion from yahoo.'}
                return stdticker
        ticker = ticker['ticker']
        if currency.lower() in ['ltc', 'nmc']:
            stdticker = {'bid': round(1.0/ticker['buy'],6),
                            'ask': round(1.0/ticker['sell'],6),
                            'last': round(1.0/ticker['last'],6),
                            'vol': ticker['vol'],
                            'low': round(1.0/ticker['high'],6),
                            'high': round(1.0/ticker['low'],6),
                            'avg': round(1.0/ticker['avg'],6)}
        else:
            stdticker.update({'bid': float(ticker['sell'])*yahoorate,
                            'ask': float(ticker['buy'])*yahoorate,
                            'last': float(ticker['last'])*yahoorate,
                            'vol': ticker['vol_cur'],
                            'low': float(ticker['low'])*yahoorate,
                            'high': float(ticker['high'])*yahoorate,
                            'avg': float(ticker['avg'])*yahoorate})
        self.ticker_cache['btce'+currency] = {'time':time.time(), 'ticker':stdticker}
        return stdticker

    def _getBtspTicker(self, currency):
        try:
            cachedvalue = self.ticker_cache['bitstamp'+currency]
            if time.time() - cachedvalue['time'] < 3:
                return cachedvalue['ticker']
        except KeyError:
            pass
        stdticker = {}
        json_data = urlopen("https://www.bitstamp.net/api/ticker/").read()
        ticker = json.loads(json_data)
        try:
            bcharts = json.loads(urlopen("http://api.bitcoincharts.com/v1/markets.json").read())
            bcharts = filter(lambda x: x['symbol'] == 'bitstampUSD', bcharts)[0]
            avg = float(bcharts['avg'])
        except:
            avg = 0
        yahoorate = 1
        if currency != 'USD':
            try:
                stdticker = {'warning':'using yahoo currency conversion'}
                yahoorate = float(self._queryYahooRate('USD', currency))
            except:
                stdticker = {'error':'failed to get currency conversion from yahoo.'}
                return stdticker
        stdticker.update({'bid': float(ticker['bid'])*yahoorate,
                            'ask': float(ticker['ask'])*yahoorate,
                            'last': float(ticker['last'])*yahoorate,
                            'vol': ticker['volume'],
                            'low': float(ticker['low'])*yahoorate,
                            'high': float(ticker['high'])*yahoorate,
                            'avg': avg*yahoorate})
        self.ticker_cache['bitstamp'+currency] = {'time':time.time(), 'ticker':stdticker}
        return stdticker

    def _getKrkTicker(self, currency):
        try:
            cachedvalue = self.ticker_cache['krk'+currency]
            if time.time() - cachedvalue['time'] < 3:
                return cachedvalue['ticker']
        except KeyError:
            pass
        stdticker = {}
        json_data = urlopen("https://api.kraken.com/0/public/Ticker?pair=XBT%s" % (currency,)).read()
        ticker = json.loads(json_data)
        yahoorate = 1
        if len(ticker['error']) != 0:
            if "Unknown asset pair" in ticker['error'][0]:
                # looks like we have unsupported currency
                ticker = json.loads(urlopen("https://api.kraken.com/0/public/Ticker?pair=XBTEUR").read())
                if len(ticker['error']) != 0:
                    stdticker = {'error':ticker['error']}
                    return stdticker
                try:
                    stdticker = {'warning':'using yahoo currency conversion'}
                    yahoorate = float(self._queryYahooRate('EUR', currency))
                except:
                    stdticker = {'error':'failed to get currency conversion from yahoo.'}
                    return stdticker
            else:
                stdticker = {'error':ticker['error']}
                return stdticker
        ticker = ticker['result'][ticker['result'].keys()[0]]
        stdticker.update({'bid': float(ticker['b'][0])*yahoorate,
                            'ask': float(ticker['a'][0])*yahoorate,
                            'last': float(ticker['c'][0])*yahoorate,
                            'vol': float(ticker['v'][1]),
                            'low': float(ticker['l'][1])*yahoorate,
                            'high': float(ticker['h'][1])*yahoorate,
                            'avg': float(ticker['p'][1])*yahoorate})
        self.ticker_cache['krk'+currency] = {'time':time.time(), 'ticker':stdticker}
        return stdticker

    def _getBcentTicker(self, currency):
        try:
            cachedvalue = self.ticker_cache['bcent'+currency]
            if time.time() - cachedvalue['time'] < 3:
                return cachedvalue['ticker']
        except KeyError:
            pass
        stdticker = {}
        json_data = urlopen("https://bitcoin-central.net/api/v1/data/eur/ticker").read()
        ticker = json.loads(json_data)
        if ticker.has_key('errors'):
            stdticker = {'error':ticker['errors']}
            return stdticker
        yahoorate = 1
        if currency != 'EUR':
            try:
                stdticker = {'warning':'using yahoo currency conversion'}
                yahoorate = float(self._queryYahooRate('EUR', currency))
            except:
                stdticker = {'error':'failed to get currency conversion from yahoo.'}
                return stdticker
        stdticker.update({'bid': float(ticker['bid'])*yahoorate,
                            'ask': float(ticker['ask'])*yahoorate,
                            'last': float(ticker['price'])*yahoorate,
                            'vol': float(ticker['volume']),
                            'low': float(ticker['low'])*yahoorate,
                            'high': float(ticker['high'])*yahoorate,
                            'avg': float(ticker['vwap'])*yahoorate})
        self.ticker_cache['bcent'+currency] = {'time':time.time(), 'ticker':stdticker}
        return stdticker

    def _getBfxTicker(self, currency):
        try:
            cachedvalue = self.ticker_cache['bitfinex'+currency]
            if time.time() - cachedvalue['time'] < 3:
                return cachedvalue['ticker']
        except KeyError:
            pass
        if currency.lower() == 'ltc':
            pair = 'ltcbtc'
        else:
            pair = 'btc%s' % (currency.lower(),)
        json_data = urlopen("https://api.bitfinex.com/v1/ticker/%s" % (pair,)).read()
        spotticker = json.loads(json_data)
        json_data = urlopen("https://api.bitfinex.com/v1/today/%s" % (pair,)).read()
        dayticker = json.loads(json_data)
        if spotticker.has_key('message') or dayticker.has_key('message'):
            stdticker = {'error':spotticker.get('message') or dayticker.get('message')}
        else:
            if currency.lower() == 'ltc':
                stdticker = {'bid': round(1.0/float(spotticker['ask']),6),
                                'ask': round(1.0/float(spotticker['bid']),6),
                                'last': round(1.0/float(spotticker['last_price']),6),
                                'vol': dayticker['volume'],
                                'low': round(1.0/float(dayticker['high']),6),
                                'high': round(1.0/float(dayticker['low']),6),
                                'avg': None}
            else:
                stdticker = {'bid': spotticker['bid'],
                                'ask': spotticker['ask'],
                                'last': spotticker['last_price'],
                                'vol': dayticker['volume'],
                                'low': dayticker['low'],
                                'high': dayticker['high'],
                                'avg': None}
        self.ticker_cache['bitfinex'+currency] = {'time':time.time(), 'ticker':stdticker}
        return stdticker

    def _getBtcdeTicker(self, currency):
        try:
            cachedvalue = self.ticker_cache['btcde'+currency]
            if time.time() - cachedvalue['time'] < 3:
                return cachedvalue['ticker']
        except KeyError:
            pass
        stdticker = {}
        json_data = urlopen("http://api.bitcoincharts.com/v1/markets.json").read()
        ticker = json.loads(json_data)
        trades = urlopen('http://api.bitcoincharts.com/v1/trades.csv?symbol=btcdeEUR').readlines()
        last = float(trades[-1].split(',')[1])
        yahoorate = 1
        if currency != 'EUR':
            stdticker = {'warning':'using yahoo currency conversion'}
            try:
                yahoorate = float(self._queryYahooRate('EUR', currency))
            except:
                stdticker = {'error':'failed to get currency conversion from yahoo.'}
                return stdticker
        ticker = filter(lambda x: x['symbol'] == 'btcdeEUR', ticker)[0]
        stdticker.update({'bid': float(ticker['bid'])*yahoorate,
                            'ask':float(ticker['ask'])*yahoorate,
                            'last': float(last)*yahoorate,
                            'vol': ticker['volume'],
                            'low': float(ticker['low'])*yahoorate,
                            'high': float(ticker['high'])*yahoorate,
                            'avg': float(ticker['avg'])*yahoorate})
        self.ticker_cache['btcde'+currency] = {'time':time.time(), 'ticker':stdticker}
        return stdticker

    def _getCbxTicker(self, currency):
        try:
            cachedvalue = self.ticker_cache['campbx'+currency]
            if time.time() - cachedvalue['time'] < 3:
                return cachedvalue['ticker']
        except KeyError:
            pass
        stdticker = {}
        try:
            json_data = urlopen("http://api.bitcoincharts.com/v1/markets.json").read()
            ticker = json.loads(json_data)
            ticker = filter(lambda x: x['symbol'] == 'cbxUSD', ticker)[0]
        except:
            ticker = {'low':0, 'high':0, 'volume':0, 'avg':0}
        cbx = json.loads(urlopen('http://campbx.com/api/xticker.php').read())
        yahoorate = 1
        if currency != 'USD':
            stdticker = {'warning':'using yahoo currency conversion'}
            try:
                yahoorate = float(self._queryYahooRate('USD', currency))
            except:
                stdticker = {'error':'failed to get currency conversion from yahoo.'}
                return stdticker
        stdticker.update({'bid': float(cbx['Best Bid'])*yahoorate,
                            'ask': float(cbx['Best Ask'])*yahoorate,
                            'last': float(cbx['Last Trade'])*yahoorate,
                            'vol': ticker['volume'],
                            'low': float(ticker['low'])*yahoorate,
                            'high': float(ticker['high'])*yahoorate,
                            'avg': float(ticker['avg'])*yahoorate})
        self.ticker_cache['campbx'+currency] = {'time':time.time(), 'ticker':stdticker}
        return stdticker

    def _getBtcnTicker(self, currency):
        try:
            cachedvalue = self.ticker_cache['btcchina'+currency]
            if time.time() - cachedvalue['time'] < 3:
                return cachedvalue['ticker']
        except KeyError:
            pass
        stdticker = {}
        try:
            json_data = urlopen("http://api.bitcoincharts.com/v1/markets.json").read()
            bcharts = json.loads(json_data)
        except:
            bcharts = [{'symbol':'btcnCNY','avg':None}]
        btcchina = json.loads(urlopen('https://data.btcchina.com/data/ticker').read())['ticker']
        yahoorate = 1
        if currency not in ['CNY', 'RMB']:
            stdticker = {'warning':'using yahoo currency conversion'}
            try:
                yahoorate = float(self._queryYahooRate('CNY', currency))
            except:
                stdticker = {'error':'failed to get currency conversion from yahoo.'}
                return stdticker
        bcharts = filter(lambda x: x['symbol'] == 'btcnCNY', bcharts)[0]
        if bcharts['avg'] is not None:
            avg = float(bcharts['avg'])*yahoorate
        else:
            avg = None
        stdticker.update({'bid': float(btcchina['buy'])*yahoorate,
                            'ask': float(btcchina['sell'])*yahoorate,
                            'last': float(btcchina['last'])*yahoorate,
                            'vol': btcchina['vol'],
                            'low': float(btcchina['low'])*yahoorate,
                            'high': float(btcchina['high'])*yahoorate,
                            'avg': avg})
        self.ticker_cache['btcchina'+currency] = {'time':time.time(), 'ticker':stdticker}
        return stdticker

    def _getBtcavgTicker(self, currency):
        try:
            cachedvalue = self.ticker_cache['bitcoinaverage'+currency]
            if time.time() - cachedvalue['time'] < 3:
                return cachedvalue['ticker']
        except KeyError:
            pass
        try:
            ticker = json.loads(urlopen('https://api.bitcoinaverage.com/ticker/%s' % (currency,)).read())
        except urllib2.HTTPError:
            stdticker = {'error':'Unsupported currency.'}
            return stdticker
        except:
            stdticker = {'error':'Problem retrieving data.'}
            return stdticker
        stdticker = {'bid': float(ticker['bid']),
                            'ask': float(ticker['ask']),
                            'last': float(ticker['last']),
                            'vol': ticker['total_vol'],
                            'low': None,
                            'high': None,
                            'avg': float(ticker['24h_avg'])}
        self.ticker_cache['bitcoinaverage'+currency] = {'time':time.time(), 'ticker':stdticker}
        return stdticker

    def _getCoinbaseTicker(self, currency):
        try:
            cachedvalue = self.ticker_cache['coinbase'+currency]
            if time.time() - cachedvalue['time'] < 3:
                return cachedvalue['ticker']
        except KeyError:
            pass
        stdticker = {}
        try:
            last = json.loads(urlopen('https://coinbase.com/api/v1/prices/spot_rate').read())['amount']
            ask = json.loads(urlopen('https://coinbase.com/api/v1/prices/buy').read())['amount']
            bid = json.loads(urlopen('https://coinbase.com/api/v1/prices/sell').read())['amount']
        except:
            raise # will get caught later
        if currency != 'USD':
            stdticker = {'warning':'using yahoo currency conversion'}
            try:
                yahoorate = float(self._queryYahooRate('USD', currency))
            except:
                stdticker = {'error':'failed to get currency conversion from yahoo.'}
                return stdticker
        else:
            yahoorate = 1
        stdticker.update({'bid': float(bid)*yahoorate,
                            'ask': float(ask)*yahoorate,
                            'last': float(last)*yahoorate,
                            'vol': None,
                            'low': None,
                            'high': None,
                            'avg': None})
        self.ticker_cache['coinbase'+currency] = {'time':time.time(), 'ticker':stdticker}
        return stdticker

    def _getBitmyntTicker(self, currency):
        try:
            cachedvalue = self.ticker_cache['bitmynt'+currency]
            if time.time() - cachedvalue['time'] < 3:
                return cachedvalue['ticker']
        except KeyError:
            pass
        stdticker = {}
        yahoorate = 1
        if currency in ['EUR','NOK']:
            ticker = json.loads(urlopen("http://bitmynt.no/ticker-%s.pl" % (currency.lower(),)).read())
            ticker = ticker[currency.lower()]
        else:
            ticker = json.loads(urlopen("http://bitmynt.no/ticker-eur.pl").read())
            ticker = ticker['eur']
            stdticker = {'warning':'using yahoo currency conversion'}
            try:
                yahoorate = float(self._queryYahooRate('EUR', currency))
            except:
                stdticker = {'error':'failed to get currency conversion from yahoo.'}
                return stdticker
        stdticker.update({'bid': float(ticker['buy'])*yahoorate,
                            'ask': float(ticker['sell'])*yahoorate,
                            'last': (float(ticker['buy']) + float(ticker['sell']))/2*yahoorate,
                            'vol': None,
                            'low': None,
                            'high': None,
                            'avg': None})
        self.ticker_cache['bitmynt'+currency] = {'time':time.time(), 'ticker':stdticker}
        return stdticker

    def _sellbtc(self, bids, value):
        n_coins = value
        total = 0.0
        top = 0.0
        all = False
        for bid in bids:
            if n_coins <= bid['amount']: # we don't have enough
                total += n_coins * bid['price']
                top = bid['price']
                break
            else: # we can eat the entire order
                n_coins -= bid['amount']
                total += bid['amount'] * bid['price']
        else:
            all = True
        return({'n_coins':n_coins, 'total':total, 'top':top, 'all':all})

    def _sellusd(self, bids, value):
        n_coins = 0.0
        total = value
        top = 0.0
        all = False
        for bid in bids:
            if total <= bid['amount'] * bid['price']: 
                n_coins += total / bid['price']
                top = bid['price']
                break
            else: # we can eat the entire order
                n_coins += bid['amount']
                total -= bid['amount'] * bid['price']
        else:
            all = True
        return({'n_coins':n_coins, 'total':total, 'top':top, 'all':all})

    def sell(self, irc, msg, args, optlist, value):
        """[--fiat] [--market <market>] [--currency XXX] <value>
        
        Calculate the effect on the market depth of a market sell order of
        <value> bitcoins. 
        If <market> is provided, uses that exchange. Default is Bitstamp.
        If --currency XXX is provided, converts to that fiat currency. Default is USD.
        If '--fiat' option is given, <value> denotes the size of the order in fiat.
        """
        od = dict(optlist)
        market = od.pop('market','btsp')
        currency = od.pop('currency','USD')
        m = self._getMarketInfo(market, 'depth')
        if m is None:
            irc.error("This is not one of the supported markets. Please choose one of %s." % (self.depth_supported_markets.keys(),))
            return
        m[2](currency)
        cachename = m[0]+currency
        try:
            bids = self.depth_cache[cachename]['depth']['bids']
        except KeyError:
            irc.error("Failure to retrieve order book data. Try again later.")
            traceback.print_exc()
            return
        if od.has_key('fiat'):
            r = self._sellusd(bids, value)
            if r['all']:
                irc.reply("%s | This order would exceed the size of the order book. "
                        "You would sell %.8g bitcoins for a total of %.4f %s and "
                        "take the price to 0."
                        " | Data vintage: %.4f seconds"
                        % (m[1], r['n_coins'], value - r['total'], currency, (time.time() - self.depth_cache[cachename]['time']),))
            else:
                irc.reply("%s | A market order to sell %.4f %s worth of bitcoins right "
                        "now would sell %.8g bitcoins and would take the last "
                        "price down to %.4f %s, resulting in an average price of "
                        "%.4f %s/BTC."
                        " | Data vintage: %.4f seconds"
                        % (m[1], value, currency, r['n_coins'], r['top'], currency,
                        (value/r['n_coins']), currency, (time.time() - self.depth_cache[cachename]['time']),))
        else:
            r = self._sellbtc(bids, value)
            if r['all']:
                irc.reply("%s | This order would exceed the size of the order book. "
                        "You would sell %.8g bitcoins, for a total of %.4f %s and "
                        "take the price to 0."
                        " | Data vintage: %.4f seconds"
                        % (m[1], value - r['n_coins'], r['total'], currency, (time.time() - self.depth_cache[cachename]['time']),))
            else:
                irc.reply("%s | A market order to sell %.8g bitcoins right now would "
                        "net %.4f %s and would take the last price down to %.4f %s, "
                        "resulting in an average price of %.4f %s/BTC."
                        " | Data vintage: %.4f seconds"
                        % (m[1], value, r['total'], currency, r['top'], currency,
                        (r['total']/value), currency, (time.time() - self.depth_cache[cachename]['time'])))
    sell = wrap(sell, [getopts({'fiat':'', 'market':'something', 'currency': 'currencyCode'}), 'nonNegativeFloat'])

    def _buybtc(self, asks, value):
        n_coins = value
        total = 0.0
        top = 0.0
        all = False
        for ask in asks:
            if n_coins <= ask['amount']: # we don't have enough
                total += n_coins * ask['price']
                top = ask['price']
                break
            else: # we can eat the entire order
                n_coins -= ask['amount']
                total += ask['amount'] * ask['price']
                top = ask['price']
        else:
            all = True
        return({'n_coins':n_coins, 'total':total, 'top':top, 'all':all})

    def _buyusd(self, asks, value):
        n_coins = 0.0
        total = value
        top = 0.0
        all = False
        for ask in asks:
            if total <= ask['amount'] * ask['price']: 
                n_coins += total / ask['price']
                top = ask['price']
                break
            else: # we can eat the entire order
                n_coins += ask['amount']
                total -= ask['amount'] * ask['price']
                top = ask['price']
        else:
            all = True
        return({'n_coins':n_coins, 'total':total, 'top':top, 'all':all})

    def buy(self, irc, msg, args, optlist, value):
        """[--fiat] [--market <market>] [--currency XXX] <value>
        
        Calculate the effect on the market depth of a market buy order of
        <value> bitcoins. 
        If <market> is provided, uses that exchange. Default is Bitstamp.
        If --currency XXX is provided, converts to that fiat currency. Default is USD.
        If '--fiat' option is given, <value> denotes the size of the order in fiat.
        """
        od = dict(optlist)
        market = od.pop('market','btsp')
        currency = od.pop('currency','USD')
        m = self._getMarketInfo(market, 'depth')
        if m is None:
            irc.error("This is not one of the supported markets. Please choose one of %s." % (self.depth_supported_markets.keys(),))
            return
        m[2](currency)
        cachename = m[0]+currency
        try:
            asks = self.depth_cache[cachename]['depth']['asks']
        except KeyError:
            irc.error("Failure to retrieve order book data. Try again later.")
            return
        if dict(optlist).has_key('fiat'):
            r = self._buyusd(asks, value)
            if r['all']:
                irc.reply("%s | This order would exceed the size of the order book. "
                        "You would buy %.8g bitcoins for a total of %.4f %s and "
                        "take the price to %.4f."
                        " | Data vintage: %.4f seconds"
                        % (m[1], r['n_coins'], value - r['total'], currency,
                        r['top'], (time.time() - self.depth_cache[cachename]['time']),))
            else:
                irc.reply("%s | A market order to buy %.4f %s worth of bitcoins right "
                        "now would buy %.8g bitcoins and would take the last "
                        "price up to %.4f %s, resulting in an average price of "
                        "%.4f %s/BTC."
                        " | Data vintage: %.4f seconds"
                        % (m[1], value, currency, r['n_coins'], r['top'], currency,
                        (value/r['n_coins']), currency, (time.time() - self.depth_cache[cachename]['time']),))
        else:
            r = self._buybtc(asks, value)
            if r['all']:
                irc.reply("%s | This order would exceed the size of the order book. "
                        "You would buy %.8g bitcoins, for a total of %.4f %s and "
                        "take the price to %.4f."
                        " | Data vintage: %.4f seconds"
                        % (m[1], value - r['n_coins'], r['total'], currency, r['top'],
                        (time.time() - self.depth_cache[cachename]['time']),))
            else:
                irc.reply("%s | A market order to buy %.8g bitcoins right now would "
                        "take %.4f %s and would take the last price up to %.4f %s, "
                        "resulting in an average price of %.4f %s/BTC."
                        " | Data vintage: %.4f seconds"
                        % (m[1], value, r['total'], currency, r['top'], currency,
                        (r['total']/value), currency, (time.time() - self.depth_cache[cachename]['time']),))
    buy = wrap(buy, [getopts({'fiat':'', 'market':'something', 'currency': 'currencyCode'}), 'nonNegativeFloat'])

    def asks(self, irc, msg, args, optlist, pricetarget):
        """[--over] [--market <market>] [--currency XXX] <pricetarget>
        
        Calculate the amount of bitcoins for sale at or under <pricetarget>.
        If '--over' option is given, find coins or at or over <pricetarget>.
        If market is supplied, uses that exchange. Default is Bitstamp.
        If --currency XXX is provided, converts to that fiat currency. Default is USD.
        """
        od = dict(optlist)
        market = od.pop('market','btsp')
        currency = od.pop('currency','USD')
        m = self._getMarketInfo(market, 'depth')
        if m is None:
            irc.error("This is not one of the supported markets. Please choose one of %s." % (self.depth_supported_markets.keys(),))
            return
        m[2](currency)
        cachename = m[0]+currency
        response = "under"
        if dict(optlist).has_key('over'):
            f = lambda price,pricetarget: price >= pricetarget
            response = "over"
        else:
            f = lambda price,pricetarget: price <= pricetarget
        n_coins = 0.0
        total = 0.0
        try:
            asks = self.depth_cache[cachename]['depth']['asks']
        except KeyError:
            irc.error("Failure to retrieve order book data. Try again later.")
            return
        for ask in asks:
            if f(ask['price'], pricetarget):
                n_coins += ask['amount']
                total += (ask['amount'] * ask['price'])

        irc.reply("%s | There are currently %.8g bitcoins offered at "
                "or %s %s %s, worth %s %s in total."
                " | Data vintage: %.4f seconds"
                % (m[1], n_coins, response, pricetarget, currency, total, currency,
                (time.time() - self.depth_cache[cachename]['time']),))
    asks = wrap(asks, [getopts({'over':'', 'market':'something', 'currency': 'currencyCode'}), 'nonNegativeFloat'])

    def bids(self, irc, msg, args, optlist, pricetarget):
        """[--under] [--market <market>] [--currency XXX] <pricetarget>
        
        Calculate the amount of bitcoin demanded at or over <pricetarget>.
        If '--under' option is given, find coins or at or under <pricetarget>.
        If market is supplied, uses that exchange. Default is Bitstamp.
        If --currency XXX is provided, converts to that fiat currency. Default is USD.
        """
        od = dict(optlist)
        market = od.pop('market','btsp')
        currency = od.pop('currency','USD')
        m = self._getMarketInfo(market, 'depth')
        if m is None:
            irc.error("This is not one of the supported markets. Please choose one of %s." % (self.depth_supported_markets.keys(),))
            return
        m[2](currency)
        cachename = m[0]+currency
        response = "over"
        if dict(optlist).has_key('under'):
            f = lambda price,pricetarget: price <= pricetarget
            response = "under"
        else:
            f = lambda price,pricetarget: price >= pricetarget
        n_coins = 0.0
        total = 0.0
        try:
            bids = self.depth_cache[cachename]['depth']['bids']
        except KeyError:
            irc.error("Failure to retrieve order book data. Try again later.")
            return
        for bid in bids:
            if f(bid['price'], pricetarget):
                n_coins += bid['amount']
                total += (bid['amount'] * bid['price'])

        irc.reply("%s | There are currently %.8g bitcoins demanded at "
                "or %s %s %s, worth %s %s in total."
                " | Data vintage: %.4f seconds"
                % (m[1], n_coins, response, pricetarget, currency, total, currency,
                (time.time() - self.depth_cache[cachename]['time']),))
    bids = wrap(bids, [getopts({'under':'', 'market':'something', 'currency': 'currencyCode'}), 'nonNegativeFloat'])

    def obip(self, irc, msg, args, optlist, width):
        """[--market <market>] [--currency XXX] <width>
        
        Calculate the "order book implied price", by finding the weighted
        average price of coins <width> BTC up and down from the spread.
        If market is supplied, uses that exchange. Default is Bitstamp.
        If --currency XXX is provided, converts to that fiat currency. Default is USD.
        """
        od = dict(optlist)
        market = od.pop('market','btsp')
        currency = od.pop('currency','USD')
        m = self._getMarketInfo(market, 'depth')
        if m is None:
            irc.error("This is not one of the supported markets. Please choose one of %s." % (self.depth_supported_markets.keys(),))
            return
        m[2](currency)
        cachename = m[0]+currency
        try:
            asks = self.depth_cache[cachename]['depth']['asks']
            bids = self.depth_cache[cachename]['depth']['bids']
        except KeyError:
            irc.error("Failure to retrieve order book data. Try again later.")
            return

        b = self._buybtc(asks, width)
        s = self._sellbtc(bids, width)
        if b['all'] or s['all']:
            irc.error("The width provided extends past the edge of the order book. Please use a smaller width.")
            return
        obip = (b['total'] + s['total'])/2.0/width
        irc.reply("%s | The weighted average price of BTC, %s coins up and down from the spread, is %.5f %s."
                " | Data vintage: %.4f seconds"
                % (m[1], width, obip, currency, (time.time() - self.depth_cache[cachename]['time']),))
    obip = wrap(obip, [getopts({'market':'something', 'currency': 'currencyCode'}), 'positiveFloat'])

    def baratio(self, irc, msg, args, optlist):
        """[--market <market>] [--currency XXX]
        
        Calculate the ratio of total volume of bids in currency, to total btc volume of asks.
        If '--currency XXX' option is given, converts to currency denoted by given three-letter currency code. Default is USD.
        If market is supplied, uses that exchange. Default is Bitstamp.
        """
        od = dict(optlist)
        market = od.pop('market','btsp')
        currency = od.pop('currency', 'USD')
        m = self._getMarketInfo(market, 'depth')
        if m is None:
            irc.error("This is not one of the supported markets. Please choose one of %s." % (self.depth_supported_markets.keys(),))
            return
        m[2](currency)
        try:
            asks = self.depth_cache[m[0]+currency]['depth']['asks']
            bids = self.depth_cache[m[0]+currency]['depth']['bids']
        except KeyError:
            irc.error("Failure to retrieve order book data. Try again later.")
            return

        totalasks = 0
        for ask in asks:
            totalasks += ask['amount']
        totalbids = 0
        for bid in bids:
            totalbids += bid['amount'] * bid['price']
        ratio = totalbids / totalasks
        irc.reply("%s | Total bids: %d %s. Total asks: %d BTC. Ratio: %.5f %s/BTC."
                " | Data vintage: %.4f seconds"
                % (m[1], totalbids, currency, totalasks, ratio, currency,
                (time.time() - self.depth_cache[m[0]+currency]['time']),))
    baratio = wrap(baratio, [getopts({'market':'something', 'currency': 'currencyCode'})])

    def _getMarketInfo(self, input, action='ticker'):
        sm = getattr(self, action + '_supported_markets')
        sml = sm.keys()+sm.values()
        dl = [dameraulevenshtein(input.lower(), i.lower()) for i in sml]
        if (min(dl) <= 2):
            mkt = (sml)[dl.index(min(dl))]
        else:
            return None
        if mkt.lower() in sm.keys():
            return [mkt.lower(), sm[mkt.lower()],
                    getattr(self, '_get' + mkt.capitalize() + action.capitalize()),]
        r = filter(lambda x: sm[x].lower() == mkt.lower(), sm)
        if len(r) == 1:
            return [r[0], sm[r[0]],
                    getattr(self, '_get' + r[0].capitalize() + action.capitalize()),]
        return None
        
    def premium(self, irc, msg, args, market1, market2):
        '''<market1> <market2>
        
        Calculate the premium of market1 over market2, using last trade price.
        Uses USD exchange rate. If USD is not traded on one of the target
        markets, queries currency conversion from google.
        '''
        r1 = self._getMarketInfo(market1)
        r2 = self._getMarketInfo(market2)
        if r1 is None or r2 is None:
            irc.error("This is not one of the supported markets. Please choose one of %s." % (self.ticker_supported_markets.keys(),))
            return
        try:
            last1 = float(r1[2]('USD')['last'])
            last2 = float(r2[2]('USD')['last'])
        except:
            irc.error("Failure to retrieve ticker. Try again later.")
            return
        prem = (last1-last2)/last2*100
        irc.reply("Premium of %s over %s is currently %s %%." % \
                (r1[1], r2[1], prem,))
    premium = wrap(premium, ['something','something'])
    
    def ticker(self, irc, msg, args, optlist):
        """[--bid|--ask|--last|--high|--low|--avg|--vol] [--currency XXX] [--market <market>|all]
        
        Return pretty-printed ticker. Default market is Bitstamp. 
        If one of the result options is given, returns only that numeric result
        (useful for nesting in calculations).
        
        If '--currency XXX' option  is given, returns ticker for that three-letter currency code.
        It is up to you to make sure the code is a valid currency on your target market.
        Default currency is USD.
        """
        od = dict(optlist)
        currency = od.pop('currency', 'USD')
        market = od.pop('market','btsp')
        r = self._getMarketInfo(market)
        if r is None and market.lower() != 'all':
            irc.error("This is not one of the supported markets. Please choose one of %s or 'all'" % (self.ticker_supported_markets.keys(),))
            return
        if len(od) > 1:
            irc.error("Please only choose at most one result option at a time.")
            return
        if market != 'all':
            try:
                ticker = r[2](currency)
            except Exception, e:
                irc.error("Failure to retrieve ticker. Try again later.")
                self.log.info("Problem retrieving ticker. Market %s, Error: %s" %\
                            (market, e,))
                return
            if ticker.has_key('error'):
                irc.error('Error retrieving ticker. Details: %s' % (ticker['error'],))
                return

            if len(od) == 0:
                irc.reply("%s BTC%s ticker | Best bid: %s, Best ask: %s, Bid-ask spread: %.5f, Last trade: %s, "
                    "24 hour volume: %s, 24 hour low: %s, 24 hour high: %s, 24 hour vwap: %s" % \
                    (r[1], currency, ticker['bid'], ticker['ask'],
                    float(ticker['ask']) - float(ticker['bid']), ticker['last'],
                    ticker['vol'], ticker['low'], ticker['high'],
                    ticker['avg']))
            else:
                key = od.keys()[0]
                irc.reply(ticker[key])
        else:
            response = ""
            sumvol = 0
            sumprc = 0
            for mkt in ['btsp','btce','bfx','cbx','btcn', 'krk', 'bcent']:
                try:
                    r = self._getMarketInfo(mkt)
                    tck = r[2](currency)
                    response += "%s BTC%s last: %s, vol: %s | " % \
                            (r[1], currency, tck['last'], tck['vol'])
                except:
                    continue # we'll just skip this one then
                sumvol += float(tck['vol'])
                sumprc += float(tck['vol']) * float(tck['last'])
            response += "Volume-weighted last average: %s" % (sumprc/sumvol,)
            irc.reply(response)
    ticker = wrap(ticker, [getopts({'bid': '','ask': '','last': '','high': '',
            'low': '', 'avg': '', 'vol': '', 'currency': 'currencyCode', 'market': 'something'})])

#    def goxlag(self, irc, msg, args, optlist):
#        """[--raw]
#        
#        Retrieve mtgox order processing lag. If --raw option is specified
#        only output the raw number of seconds. Otherwise, dress it up."""
#        try:
#            json_data = urlopen("https://mtgox.com/api/2/money/order/lag").read()
#            lag = json.loads(json_data)
#            lag_secs = lag['data']['lag_secs']
#        except:
#            irc.error("Problem retrieving gox lag. Try again later.")
#            return
#
#        if dict(optlist).has_key('raw'):
#            irc.reply("%s" % (lag_secs,))
#            return
        
#        result = "MtGox lag is %s seconds." % (lag_secs,)
#        
#        au = lag_secs / 499.004784
#        meandistance = {0: "... nowhere, really",
#                        0.0001339: "to the other side of the Earth, along the surface",
#                        0.0024: "across the outer diameter of Saturn's rings",
#                        0.00257: "from Earth to Moon",
#                        0.002819: "from Jupiter to its third largest moon, Io",
#                        0.007155: "from Jupiter to its largest moon, Ganymede",
#                        0.00802: "from Saturn to its largest moon, Titan",
#                        0.012567: "from Jupiter to its second largest moon, Callisto",
#                        0.016: "one full loop along the orbit of the Moon around Earth",
#                        0.0257: 'ten times between Earth and Moon',
#                        0.0689: "approximately the distance covered by Voyager 1 in one week",
#                        0.0802: "ten times between Saturn and Titan",
#                        0.12567: "ten times between Jupiter and Callisto",
#                        0.2540: 'between Earth and Venus at their closest approach',
#                        0.257: 'one hundred times between Earth and Moon',
#                        0.2988: 'approximately the distance covered by Voyager 1 in one month',
#                        0.39: 'from the Sun to Mercury',
#                        0.72: 'from the Sun to Venus',
#                        1: 'from the Sun to Earth',
#                        1.52: 'from the Sun to Mars',
#                        2.77: 'from the Sun to Ceres (in the main asteroid belt)',
#                        5.2: 'from the Sun to Jupiter',
#                        9.54: 'from the Sun to Saturn',
#                        19.18: 'from the Sun to Uranus',
#                        30.06: 'from the Sun to Neptune',
#                        39.44: 'from the Sun to Pluto (Kuiper belt)',
#                        100: 'from the Sun to heliopause (out of the solar system!)'}
#        import operator
#        distances = meandistance.keys()
#        diffs = map(lambda x: abs(operator.__sub__(x, au)), distances)
#        bestdist = distances[diffs.index(min(diffs))]
#        objectname = meandistance[bestdist]
#        result += " During this time, light travels %s AU. You could have sent a bitcoin %s (%s AU)." % (au, objectname, bestdist)
#        irc.reply(result)
#    goxlag = wrap(goxlag, [getopts({'raw': ''})])

    def convert(self, irc, msg, args, amount, currency1, currency2):
        """[<amount>] <currency1> [to|in] <currency2>
        
        Convert <currency1> to <currency2> using Yahoo api.
        If optional <amount> is given, converts <amount> units of currency1.
        """
        if amount is None:
            amount = 1
        try:
            result = self._queryYahooRate(currency1, currency2)
            irc.reply(float(result)*amount)
        except:
            irc.error("Problem retrieving data.")
    convert = wrap(convert, [optional('nonNegativeFloat'), 'currencyCode', 'to', 'currencyCode'])

    def avgprc(self, irc, msg, args, currency, timeframe):
        """<currency> <timeframe>

        Returns volume-weighted average price data from BitcoinCharts.
        <currency> is a three-letter currency code, <timeframe> is
        the time window for the average, and can be '24h', '7d', or '30d'.
        """
        try:
            data = urlopen('http://api.bitcoincharts.com/v1/weighted_prices.json').read()
            j = json.loads(data)
            curs = j.keys()
            curs.remove('timestamp')
        except:
            irc.error("Failed to retrieve data. Try again later.")
            return
        try:
            result = j[currency.upper()][timeframe]
        except KeyError:
            irc.error("Data not available. Available currencies are %s, and "
                    "available timeframes are 24h, 7d, 30d." % (', '.join(curs),))
            return
        irc.reply(result)
    avgprc = wrap(avgprc, ['something','something'])

Class = Market


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2011, remote
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class MarketTestCase(PluginTestCase):
    plugins = ('Market',)

    def testAsks(self):
        self.assertError('asks blabla')
        self.assertError('asks --market nosuchthing 1000')
        self.assertRegexp('asks 0', 'There are currently 0 bitcoins offered at or under 0')
        self.assertRegexp('asks --over 5.5', 'There are currently .* bitcoins offered at or over 5')
        self.assertRegexp('asks --market bitstamp 10000', 'There are currently .* bitcoins offered')
        self.assertRegexp('asks --market bitstamp --currency EUR 10000', 'There are currently .* bitcoins offered')
        self.assertRegexp('asks --market btsp --over 5.5', 'There are currently .* bitcoins offered at or over 5')

    def testBids(self):
        self.assertError('bids blabla')
        self.assertError('bids --market nosuchthing 1000')
        self.assertRegexp('bids 10000000', 'There are currently 0 bitcoins demanded at or over 1')
        self.assertRegexp('bids --under 5.5', 'There are currently .* bitcoins demanded at or under 5')
        self.assertRegexp('bids --market bitstamp 1000', 'There are currently .* bitcoins demanded')
        self.assertRegexp('bids --market bitstamp --currency EUR 1000', 'There are currently .* bitcoins demanded')
        self.assertRegexp('bids --market bitstamp --under 5.5', 'There are currently .* bitcoins demanded at or under 5')

    def testTicker(self):
        self.assertRegexp('ticker', 'Best bid')
        self.assertRegexp('ticker --bid', '[\d\.]+')
        self.assertRegexp('ticker --ask', '[\d\.]+')
        self.assertRegexp('ticker --last', '[\d\.]+')
        self.assertRegexp('ticker --high', '[\d\.]+')
        self.assertRegexp('ticker --low', '[\d\.]+')
        self.assertRegexp('ticker --avg', '[\d\.]+')
        self.assertRegexp('ticker --vol', '[\d\.]+')
        self.assertError('ticker --last --bid') # can't have multiple result options
        self.assertRegexp('ticker', 'BTCUSD')
        self.assertRegexp('ticker --currency EUR', 'BTCEUR')
        self.assertRegexp('ticker --currency EUR --currency JPY', 'BTCJPY') # should use the last supplied currency
        self.assertRegexp('ticker --currency EUR --avg', '[\d\.]+')
        self.assertError('ticker --last --bid --currency USD') # can't have multiple result options
        self.assertError('ticker --currency ZZZ') # no such currency
        self.assertError('ticker --currency blablabla') # invalid currency code
        self.assertRegexp('ticker --market bitstamp --currency USD', 'Bitstamp BTCUSD')
        
    def testBuy(self):
        self.assertError('buy blabla')
        self.assertRegexp('buy 100', 'market order to buy .* bitcoins right now would')
        self.assertRegexp('buy --fiat 100', 'market order to buy .* USD worth of bitcoins right now would buy')
        self.assertRegexp('buy --market bitstamp 100', 'market order to buy .* bitcoins right now would')
        self.assertRegexp('buy --market bitstamp --currency EUR 100', 'market order to buy .* bitcoins right now would')
        self.assertRegexp('buy --market btsp --fiat --currency eur 100', 'market order to buy .* EUR worth of bitcoins right now would buy')

    def testSell(self):
        self.assertError('sell blabla')
        self.assertRegexp('sell 100', 'market order to sell .* bitcoins right now would')
        self.assertRegexp('sell --fiat 100', 'market order to sell .* USD worth of bitcoins right now would')
        self.assertRegexp('sell --market btsp 100', 'market order to sell .* bitcoins right now would')
        self.assertRegexp('sell --market btsp --currency eur 100', 'market order to sell .* bitcoins right now would')
        self.assertRegexp('sell --market bitstamp --fiat --currency eur 100', 'market order to sell .* EUR worth of bitcoins right now would')

    def testObip(self):
        self.assertError('obip blabla')
        self.assertRegexp('obip 100', 'weighted average price of BTC, .* coins up and down')
        self.assertRegexp('obip --market btsp 100', 'weighted average price of BTC, .* coins up and down')
        self.assertRegexp('obip --market btsp --currency EUR 100', 'weighted average price of BTC, .* coins up and down')
        self.assertError('obip 0')
        self.assertError('obip -100')

    def testBaratio(self):
        self.assertError('baratio blabla')
        self.assertRegexp('baratio', 'Total bids.*Total asks')
        self.assertRegexp('baratio --market bitstamp', 'Bitstamp | Total bids.*Total asks')
        self.assertRegexp('baratio --market krk', 'Kraken | Total bids.*Total asks')
        self.assertRegexp('baratio --market bitstamp --currency eur', 'Bitstamp | Total bids.*Total asks')

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
import supybot.conf as conf
import supybot.registry as registry
from supybot import ircutils
import re

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('MarketMonitor', True)

class Channel(registry.String):
    def setValue(self, v):
        if not ircutils.isChannel(v):
            self.error()
        else:
            super(Channel, self).setValue(v)

class CommaSeparatedListOfChannels(registry.SeparatedListOf):
    Value = Channel
    def splitter(self, s):
        return re.split(r'\s*,\s*', s)
    joiner = ', '.join

MarketMonitor = conf.registerPlugin('MarketMonitor')

conf.registerGlobalValue(MarketMonitor, 'channels',
    CommaSeparatedListOfChannels("", """List of channels that should
    receive monitoring output."""))
conf.registerGlobalValue(MarketMonitor, 'network',
    registry.String("freenode", """Network that should
    receive monitoring output."""))
conf.registerGlobalValue(MarketMonitor, 'server',
    registry.String("bitcoincharts.com", """Server to connect to."""))
conf.registerGlobalValue(MarketMonitor, 'port',
    registry.PositiveInteger(27007, """Port to connect to."""))
conf.registerGlobalValue(MarketMonitor, 'autostart',
    registry.Boolean(False, """If true, will autostart monitoring upon bot
    startup."""))
conf.registerGlobalValue(MarketMonitor, 'marketsWhitelist',
    registry.SpaceSeparatedListOfStrings("", """Whitelist of markets you
    want to monitor, space separated list of short market names. Leave
    blank to include all."""))
conf.registerGlobalValue(MarketMonitor, 'collapseThreshold',
    registry.Integer(3, """Minimum number of transactions the bot will
    collapse together"""))

class Formats(registry.OnlySomeStrings):
    validStrings = ('raw', 'pretty')

conf.registerGlobalValue(MarketMonitor, 'format',
    Formats('raw', """Format of the output. Choose between 'raw', to
    output messages as-is, and 'pretty', for prettified and aligned output."""))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2010, mizerydearia
# Copyright (c) 2010, Daniel Folkinshteyn <nanotube@users.sourceforge.net>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import decimal
import locale
import telnetlib
import threading
import time
import re
import json
import datetime

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.world as world
from supybot import schedule
from supybot import ircmsgs
from supybot import conf

class MarketMonitor(callbacks.Plugin):
    """Monitor a telnet push server for bitcoin trade data."""
    threaded = True
    callAfter = ['Services']
    def __init__(self, irc):
        self.__parent = super(MarketMonitor, self)
        self.__parent.__init__(irc)
        self.conn = telnetlib.Telnet()
        self.e = threading.Event()
        self.started = threading.Event()
        self.data = ""

        self.marketdata = {}
        # Example: {("mtgox", "USD"): [(volume, price, timestamp),(volume, price, timestamp)], ("th", "USD"): [(volume, price, timestamp)]}
        
        self.raw = []
        self.nextsend = 0 # Timestamp for when we can send next. Handling this manually allows better collapsing.

    def __call__(self, irc, msg):
        self.__parent.__call__(irc, msg)
        if not self.started.isSet() and irc.network == self.registryValue('network') and self.registryValue('autostart'):
            self._start(irc)

    def _reconnect(self, repeat=True):
        while not self.e.isSet():
            try:
                self.conn.close()
                self.conn.open(self.registryValue('server'),
                                    self.registryValue('port'))
                return True
            except Exception, e:
                # this may get verbose, but let's leave this in for now.
                self.log.error('MarketMonitor: reconnect error: %s: %s' % \
                            (e.__class__.__name__, str(e)))
                if not repeat:
                    return False
                time.sleep(5)

    def _monitor(self, irc):
        while not self.e.isSet():
            try:
                lines = self.conn.read_very_eager()
            except Exception, e:
                self.log.error('Error in MarketMonitor reading telnet: %s: %s' % \
                            (e.__class__.__name__, str(e)))
                self._reconnect()
                continue
            try:
                if irc.getCallback('Services').identified and lines: #Make sure you're running the Services plugin, and are identified!
                    lines = lines.split("\n")
                    self._parse(lines)
            except Exception, e:
                self.log.error('Error in MarketMonitor parsing: %s: %s' % \
                            (e.__class__.__name__, str(e)))
                continue # keep going no matter what
            try:
                if time.time() >= self.nextsend:
                    outputs = self._format()
                    if outputs:
                        for output in outputs:
                            for chan in self.registryValue('channels'):
                                irc.queueMsg(ircmsgs.privmsg(chan, output))
                        self.nextsend = time.time()+(conf.supybot.protocols.irc.throttleTime() * len(outputs))
                    self.marketdata = {}
                    self.raw = []
            except Exception, e:
                self.log.error('Error in MarketMonitor sending: %s: %s' % \
                            (e.__class__.__name__, str(e)))
                continue # keep going no matter what
            time.sleep(0.01)
        self.started.clear()
        self.conn.close()

    def _parse(self, msgs):
        # Stitching of messages
        if len(msgs) == 1:
            self.data += msgs[0]
            return
        msgs[0] = self.data + msgs[0]
        self.data = ""
        if not msgs[-1] == "":
            self.data = msgs[-1]

        msgs = msgs[:-1]

        if self.registryValue('format') == 'raw':
            self.raw.extend(msgs)

        #[{"timestamp": 1302015318, "price": "0.7000", "volume": "0.27", "currency": "USD", "symbol": "btcexUSD"}]

        # Parsing of messages
        for data in msgs:
            try:
                d = json.loads(data)
                for needed in "timestamp", "price", "volume", "symbol":
                    assert needed in d
                market, currency = re.match(r"^([a-z0-9]+)([A-Z]+)$", d["symbol"]).groups()
                volume = decimal.Decimal(str(d["volume"]))
                price = decimal.Decimal(str(d["price"]))
                stamp = decimal.Decimal(str(d["timestamp"]))
                if (market, currency) not in self.marketdata:
                    self.marketdata[(market, currency)] = []
                self.marketdata[(market, currency)].append((volume, price, stamp))
            except Exception, e:
                # we really want to keep going no matter what data we get
                self.log.error('Error in MarketMonitor parsing: %s: %s' % \
                                (e.__class__.__name__, str(e)))
                self.log.error('MarketMonitor: Unrecognized data: %s' % data)
                self.data = ""
                return False

    def _format(self):
        if self.registryValue('format') == 'raw':
            return [x.rstrip() for x in self.raw]

        # Making a pretty output
        outputs = []
        try:
            for (market, currency), txs in self.marketdata.iteritems():
                if len(txs) >= self.registryValue('collapseThreshold'):
                    # Collapse transactions to a single transaction with degeneracy
                    (sumvol, sumpr, sumst) = reduce((lambda (sumvol, sumpr, sumst), (vol, pr, st): (sumvol+vol, sumpr+(pr*vol), sumst+(st*vol))), txs, (0,0,0))
                    degeneracy = "x" + str(len(txs))
                    txs = [(sumvol, sumpr/sumvol, sumst/sumvol)]
                else:
                    degeneracy = ""
                for (vol, pr, st) in txs:
                    prfmt = self._moneyfmt(pr, places=8)
                    match = re.search(r"\.\d{2}[0-9]*?(0+)$", prfmt)
                    if match is not None:
                        # pad off the trailing 0s with spaces to retain justification
                        numzeros = len(match.group(1))
                        prfmt = prfmt[:-numzeros] + (" " * numzeros)
                    # don't forget to count irc bold marker character on both ends of bolded items
                    if len(self.registryValue('marketsWhitelist')) == 0 or market in self.registryValue('marketsWhitelist'):
                        out = "{time} {mkt:10} {num:>4} {vol:>10} @ {pr:>16} {cur}".format(time=datetime.datetime.utcfromtimestamp(st).strftime("%b%d %H:%M:%S"),
                                mkt=ircutils.bold(market), num=degeneracy, vol=self._moneyfmt(vol, places=4), pr=ircutils.bold(prfmt), cur=currency)
                        outputs.append((st,out))

            outputs.sort()
        except Exception, e:
            # we really want to keep going no matter what data we get
            self.log.error('Error in MarketMonitor formatting: %s: %s' % \
                            (e.__class__.__name__, str(e)))
            self.log.error('MarketMonitor: Unrecognized data: %s' % self.marketdata)
            return False
        return [out for (_,out) in outputs]

    def die(self):
        self.e.set()
        self.conn.close()
        self.__parent.die()

    def _start(self, irc):
        if not self.started.isSet():
            self.e.clear()
            self.started.set()
            success = self._reconnect(repeat=False)
            if success:
                t = threading.Thread(target=self._monitor, name='MarketMonitor',
                                     kwargs={'irc':irc})
                t.start()
                if hasattr(irc, 'reply'):
                    irc.reply("Monitoring start successful. Now monitoring market data.")
            else:
                if hasattr(irc, 'error'):
                     irc.error("Error connecting to server. See log for details.")
        else:
            irc.error("Monitoring already started.")

    def start(self, irc, msg, args):
        """takes no arguments

        Starts monitoring market data
        """
        irc.reply("Starting market monitoring.")
        self._start(irc)
    start = wrap(start, ['owner'])

    def stop(self, irc, msg, args):
        """takes no arguments

        Stops monitoring market data
        """
        irc.reply("Stopping market monitoring.")
        self.e.set()
    stop = wrap(stop, ['owner'])

    def _moneyfmt(self, value, places=2, curr='', sep=',', dp='.', pos='', neg='-',
        trailneg=''):
        """Convert Decimal to a money formatted string.

        places:  required number of places after the decimal point
        curr:    optional currency symbol before the sign (may be blank)
        sep:     optional grouping separator (comma, period, space, or blank)
        dp:      decimal point indicator (comma or period)
                 only specify as blank when places is zero
        pos:     optional sign for positive numbers: '+', space or blank
        neg:     optional sign for negative numbers: '-', '(', space or blank
        trailneg:optional trailing minus indicator:  '-', ')', space or blank

        >>> d = Decimal('-1234567.8901')
        >>> moneyfmt(d, curr='$')
        '-$1,234,567.89'
        >>> moneyfmt(d, places=0, sep='.', dp='', neg='', trailneg='-')
        '1.234.568-'
        >>> moneyfmt(d, curr='$', neg='(', trailneg=')')
        '($1,234,567.89)'
        >>> moneyfmt(Decimal(123456789), sep=' ')
        '123 456 789.00'
        >>> moneyfmt(Decimal('-0.02'), neg='<', trailneg='>')
        '<0.02>'

        """
        q = decimal.Decimal(10) ** -places      # 2 places --> '0.01'
        sign, digits, exp = value.quantize(q).as_tuple()
        result = []
        digits = map(str, digits)
        build, next = result.append, digits.pop
        if sign:
            build(trailneg)
        for i in range(places):
            build(next() if digits else '0')
        build(dp)
        if not digits:
            build('0')
        i = 0
        while digits:
            build(next())
            i += 1
            if i == 3 and digits:
                i = 0
                build(sep)
        build(curr)
        build(neg if sign else pos)
        return ''.join(reversed(result))

Class = MarketMonitor


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2010, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class MarketMonitorTestCase(ChannelPluginTestCase):
    plugins = ('MarketMonitor') 
    #utilities for the 'echo'
    #user for register for testVacuum
    
    def testStart(self):
        pass
        
    def testStop(self):
        pass

    def testConnectionError(self):
        pass
    
    def testParser(self):
        pass
    

        
# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
import supybot.conf as conf
import supybot.registry as registry
from supybot import ircutils
import re

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('MarketMonitorTicker', True)

class Channel(registry.String):
    def setValue(self, v):
        if not ircutils.isChannel(v):
            self.error()
        else:
            super(Channel, self).setValue(v)

class CommaSeparatedListOfChannels(registry.SeparatedListOf):
    Value = Channel
    def splitter(self, s):
        return re.split(r'\s*,\s*', s)
    joiner = ', '.join

MarketMonitorTicker = conf.registerPlugin('MarketMonitorTicker')

conf.registerGlobalValue(MarketMonitorTicker, 'channels',
    CommaSeparatedListOfChannels("", """List of channels that should
    receive monitoring output."""))
conf.registerGlobalValue(MarketMonitorTicker, 'network',
    registry.String("freenode", """Network that should
    receive monitoring output."""))
conf.registerGlobalValue(MarketMonitorTicker, 'tickerUrl',
    registry.String("https://data.mtgox.com/api/2/BTCUSD/money/ticker", """Url with 
    the ticker data."""))
conf.registerGlobalValue(MarketMonitorTicker, 'autostart',
    registry.Boolean(False, """If true, will autostart monitoring upon bot
    startup."""))
conf.registerGlobalValue(MarketMonitorTicker, 'pollInterval',
    registry.PositiveInteger(30, """Poll interval, in seconds."""))

#conf.registerGlobalValue(MarketMonitorTicker, 'colors',
#    registry.Boolean(False, """If true, upticks will be green and downticks
#    will be red."""))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2010, mizerydearia
# Copyright (c) 2010, Daniel Folkinshteyn <nanotube@users.sourceforge.net>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import decimal
import threading
import time
import re
import json
import datetime
from urllib2 import urlopen

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.world as world
from supybot import ircmsgs

class MarketMonitorTicker(callbacks.Plugin):
    """Monitor a telnet push server for bitcoin trade data."""
    threaded = True
    callAfter = ['Services']
    def __init__(self, irc):
        self.__parent = super(MarketMonitorTicker, self)
        self.__parent.__init__(irc)
        self.e = threading.Event()
        self.started = threading.Event()
        self.cachedticker = None
        self.freshticker = None

    def __call__(self, irc, msg):
        self.__parent.__call__(irc, msg)
        if not self.started.isSet() and irc.network == self.registryValue('network') and self.registryValue('autostart'):
            self._start(irc)

    def _getTicker(self):
        json_data = urlopen(self.registryValue('tickerUrl')).read()
        ticker = json.loads(json_data)
        return ticker['data']

    def _monitor(self, irc):
        while not self.e.isSet():
            self.freshticker = None
            try:
                self.freshticker = self._getTicker()
            except Exception, e:
                self.log.error('Error in MarketMonitorTicker: %s: %s' % \
                            (e.__class__.__name__, str(e)))
                continue
            try:
                if irc.getCallback('Services').identified and self.freshticker is not None:
                    output = self._processdata()
                    if output:
                        for chan in self.registryValue('channels'):
                            irc.queueMsg(ircmsgs.privmsg(chan, output))
            except Exception, e:
                self.log.error('Error in MarketMonitorTicker: %s: %s' % \
                            (e.__class__.__name__, str(e)))
                continue # keep going no matter what
            time.sleep(self.registryValue('pollInterval'))
        self.started.clear()

    def _processdata(self):
        # if we have difference in bid/ask/last, or if cachedticker is missing
        # make output.
        makeoutput = False
        
        timestamp = datetime.datetime.utcfromtimestamp(time.time()).strftime("%b%d %H:%M:%S")
        
        datalist = [timestamp,
                    self.freshticker['buy']['value'],
                    self.freshticker['sell']['value'],
                    self.freshticker['last']['value'],
                    self.freshticker['vol']['value']
            ]
        colorlist = ['light gray'] * 5
        
        if self.cachedticker is None:
            self.cachedticker = self.freshticker
            makeoutput = True
            
        if self.freshticker['buy']['value'] != self.cachedticker['buy']['value'] or \
            self.freshticker['sell']['value'] != self.cachedticker['sell']['value'] or \
            self.freshticker['last']['value'] != self.cachedticker['last']['value'] or \
            self.freshticker['vol']['value'] != self.cachedticker['vol']['value']:
            
            makeoutput = True
            
            colorlist = ['light gray',]
            for item in ['buy','sell','last','vol']:
                if float(self.freshticker[item]['value']) > float(self.cachedticker[item]['value']):
                    colorlist.append('green')
                elif float(self.freshticker[item]['value']) < float(self.cachedticker[item]['value']):
                    colorlist.append('red')
                else:
                    colorlist.append('light gray')

        coloredlist = map(ircutils.mircColor, datalist, colorlist)
        
        self.cachedticker = self.freshticker
        
        if makeoutput:
            output = "{time} | Bid: {bid:<12} | Ask: {ask:<12} | Last: {last:<12} | Volume: {vol}".format(time=coloredlist[0],
                    bid=coloredlist[1],
                    ask=coloredlist[2],
                    last=coloredlist[3],
                    vol=coloredlist[4])
            return output
        else:
            return False

    def die(self):
        self.e.set()
        self.__parent.die()

    def _start(self, irc):
        if not self.started.isSet():
            self.e.clear()
            self.started.set()
            t = threading.Thread(target=self._monitor, name='MarketMonitorTicker',
                                     kwargs={'irc':irc})
            t.start()
            if hasattr(irc, 'reply'):
                irc.reply("Monitoring start successful. Now monitoring market data.")
        else:
            irc.error("Monitoring already started.")

    def start(self, irc, msg, args):
        """takes no arguments

        Starts monitoring market data
        """
        irc.reply("Starting market monitoring.")
        self._start(irc)
    start = wrap(start, ['owner'])

    def stop(self, irc, msg, args):
        """takes no arguments

        Stops monitoring market data
        """
        irc.reply("Stopping market monitoring.")
        self.e.set()
    stop = wrap(stop, ['owner'])

Class = MarketMonitorTicker


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2010, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class MarketMonitorTickerTestCase(PluginTestCase):
    plugins = ('MarketMonitorTicker') 
    
    def testStart(self):
        pass
        
    def testStop(self):
        pass

    def testConnectionError(self):
        pass
    
    def testParser(self):
        pass
    

        
# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2010, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry
from supybot import ircutils
import re

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('MtgoxMonitor', True)

class Channel(registry.String):
    def setValue(self, v):
        if not ircutils.isChannel(v):
            self.error()
        else:
            super(Channel, self).setValue(v)

class CommaSeparatedListOfChannels(registry.SeparatedListOf):
    Value = Channel
    def splitter(self, s):
        return re.split(r'\s*,\s*', s)
    joiner = ', '.join

MtgoxMonitor = conf.registerPlugin('MtgoxMonitor')

conf.registerGlobalValue(MtgoxMonitor, 'channels',
    CommaSeparatedListOfChannels("", """List of channels that should
    receive monitoring output."""))
conf.registerGlobalValue(MtgoxMonitor, 'pollinterval',
    registry.PositiveInteger(10, """Seconds between mtgox site polls."""))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2010, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot import ircmsgs

import threading
import time
import json

class MtgoxMonitor(callbacks.Plugin):
    """This plugin monitors the Mtgox marketplace for activity.

    Use 'start' command to start monitoring, 'stop' command to stop.
    """

    def __init__(self, irc):
        self.__parent = super(MtgoxMonitor, self)
        self.__parent.__init__(irc)
        self.last_checked = time.time()
        #self.depth_dict = {}
        self.e = threading.Event()
        self.started = threading.Event()

    def _monitorMtgoxTrades(self, irc):
        while not self.e.isSet():
            try:
                new_trades = utils.web.getUrl('http://mtgox.com/code/data/getTrades.php')
                new_trades = json.loads(new_trades, parse_float=str, parse_int=str)
            except:
                continue # let's just try again.
            checked = self.last_checked
            #new_depth = utils.web.getUrl('http://mtgox.com/code/getDepth.php')
            #new_depth = json.loads(new_depth, parse_float=str, parse_int=str)
            # ticker: https://mtgox.com/code/ticker.php
            for trade in new_trades:
                if float(trade['date']) > checked:
                    checked = float(trade['date'])
                if float(trade['date']) > self.last_checked:
                    out = "MTG|%10s|%27s @ %s" % \
                          ('TRADE',
                           trade['amount'],
                           '$' + trade['price'])
                    out = ircutils.bold(out)
                    for chan in self.registryValue('channels'):
                        irc.queueMsg(ircmsgs.privmsg(chan, out))
            self.last_checked = checked
            time.sleep(self.registryValue('pollinterval'))
        self.started.clear()

    def start(self, irc, msg, args):
        """Start monitoring MtGox data."""
        if not self.started.isSet():
            self.e.clear()
            self.started.set()
            t = threading.Thread(target=self._monitorMtgoxTrades,
                                 kwargs={'irc':irc})
            t.start()
            irc.reply("Monitoring start successful. Now reporting Mtgox trades.")
        else:
            irc.error("Monitoring already started.")
    start = wrap(thread(start))

    def stop(self, irc, msg, args):
        irc.reply("Stopping Mtgox monitoring.")
        self.e.set()
    stop = wrap(stop)

    def die(self):
        self.e.set()
        self.__parent.die()



Class = MtgoxMonitor


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2010, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

class MtgoxMonitorTestCase(PluginTestCase):
    plugins = ('MtgoxMonitor',)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2010, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('OTCOrderBook', True)


OTCOrderBook = conf.registerPlugin('OTCOrderBook')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(OTCOrderBook, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))

conf.registerGlobalValue(OTCOrderBook, 'orderExpiry',
    registry.NonNegativeInteger(604800, """Time until order expiry. Unless a user
    calls 'refresh', orders will expire after this many seconds. Set to 0 for no
    expiry. It's a good idea to have this set to avoid seeing your database
    overgrow with old cruft."""))

conf.registerGlobalValue(OTCOrderBook, 'minTrustForLongOrders',
    registry.NonNegativeInteger(15, """Minimum total level 1 and level 2
    trust from nanotube to be able to place long duration orders."""))

conf.registerGlobalValue(OTCOrderBook, 'longOrderDuration',
    registry.NonNegativeInteger(7776000, """Extra time on top of standard
    order expiry, allotted to long-duration orders. Time in seconds."""))

conf.registerGlobalValue(OTCOrderBook, 'maxUserOpenOrders',
    registry.NonNegativeInteger(4, """Only allow this many open orders per user.
    It's a good idea to have this on, to avoid order flooding from a rogue
    user."""))

conf.registerGlobalValue(OTCOrderBook, 'maxOrdersInBookList',
    registry.NonNegativeInteger(4, """Only allow this many orders in a currency
    order book to be spit out to channel. If more than that exist, suggest to
    visit the nice website."""))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# OTCOrderBook - supybot plugin to keep an order book from irc
# Copyright (C) 2010, Daniel Folkinshteyn <nanotube@users.sourceforge.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot import ircmsgs
from supybot import conf
from supybot import ircdb
from supybot import world

import sqlite3
import time
import os.path
import re
import json
import traceback

class OTCOrderDB(object):
    def __init__(self, filename):
        self.filename = filename
        self.db = None

    def _commit(self):
        '''a commit wrapper to give it another few tries if it errors.
        
        which sometimes happens due to:
        OperationalError: database is locked'''
        for i in xrange(10):
            try:
                self.db.commit()
            except:
                time.sleep(1)

    def open(self):
        if os.path.exists(self.filename):
            db = sqlite3.connect(self.filename, check_same_thread = False)
            db.text_factory = str
            self.db = db
            return
        
        db = sqlite3.connect(self.filename, check_same_thread = False)
        db.text_factory = str
        self.db = db
        cursor = self.db.cursor()
        cursor.execute("""CREATE TABLE orders (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          created_at INTEGER,
                          refreshed_at INTEGER,
                          buysell TEXT,
                          nick TEXT,
                          host TEXT,
                          amount REAL,
                          thing TEXT,
                          price TEXT,
                          otherthing TEXT,
                          notes TEXT)
                          """)
        self._commit()
        return

    def close(self):
        self.db.close()

    def get(self, nick=None, id=None):
        cursor = self.db.cursor()
        sql = "SELECT * FROM orders WHERE"
        joiner = ""
        vars = []
        if id is None and nick is None:
            return []
        if nick is not None:
            sql += " nick LIKE ?"
            vars.append(nick)
            joiner = " AND"
        if id is not None:
            sql += joiner + " id=?"
            vars.append(id)
        cursor.execute(sql, tuple(vars))
        return cursor.fetchall()

    def getByNick(self, nick):
        cursor = self.db.cursor()
        cursor.execute("""SELECT * FROM orders WHERE nick LIKE ?""", (nick,))
        return cursor.fetchall()

    def getById(self, id):
        cursor = self.db.cursor()
        cursor.execute("""SELECT * FROM orders WHERE id=?""", (id,))
        return cursor.fetchall()

    def deleteExpired(self, expiry):
        cursor = self.db.cursor()
        timestamp = time.time()
        cursor.execute("""DELETE FROM orders WHERE refreshed_at + ? < ?""",
                       (expiry, timestamp))
        self._commit()

    def getCurrencyBook(self, thing):
        cursor = self.db.cursor()
        cursor.execute("""SELECT * FROM orders WHERE thing LIKE ?
                       OR otherthing LIKE ?
                       ORDER BY price""",
                       (thing, thing))
        return cursor.fetchall()

    def buy(self, nick, host, amount, thing, price, otherthing, notes, extratime=0):
        cursor = self.db.cursor()
        timestamp = time.time()
        cursor.execute("""INSERT INTO orders VALUES
                       (NULL, ?, ?, "BUY", ?, ?, ?, ?, ?, ?, ?)""",
                       (timestamp, timestamp+extratime, nick, host, amount, thing, price,
                        otherthing, notes))
        self._commit()
        return cursor.lastrowid

    def sell(self, nick, host, amount, thing, price, otherthing, notes, extratime=0):
        cursor = self.db.cursor()
        timestamp = time.time()
        cursor.execute("""INSERT INTO orders VALUES
                       (NULL, ?, ?, "SELL", ?, ?, ?, ?, ?, ?, ?)""",
                       (timestamp, timestamp+extratime, nick, host, amount, thing, price,
                        otherthing, notes))
        self._commit()
        return cursor.lastrowid

    def refresh(self, nick, id=None, extratime=0):
        results = self.get(nick, id)
        if len(results) != 0:
            cursor = self.db.cursor()
            timestamp = time.time()
            for row in results:
                cursor.execute("""UPDATE orders SET refreshed_at=?
                               WHERE id=?""", (timestamp+extratime, row[0]))
            self._commit()
            return len(results)
        return False

    def remove(self, nick, id=None):
        results = self.get(nick, id)
        if len(results) != 0:
            cursor = self.db.cursor()
            for row in results:
                cursor.execute("""DELETE FROM orders where id=?""",
                               (row[0],))
            self._commit()
            return len(results)
        return False
    
def getAt(irc, msg, args, state):
    if args[0].lower() in ['at', '@']:
        args.pop(0)

#def getBTC(irc, msg, args, state):
#    if args[0].lower() in ['btc','bitcoin','bitcoins']:
#        args.pop(0)

def getIndexedPrice(irc, msg, args, state, type='price input'):
    """Indexed price can contain one or more of {mtgoxask}, {mtgoxbid},
    {mtgoxlast}, {mtgoxhigh}, {mtgoxlow}, {mtgoxavg}, included in 
    an arithmetical expression.
    It can also contain one expression of the form {XXX in YYY} which
    queries google for currency conversion rate from XXX to YYY."""
    try:
        v = args[0]
        v = re.sub(r'{mtgox(ask|bid|last|high|low|avg)}', '1', v)
        v = re.sub(r'{bitstamp(ask|bid|last|high|low|avg)}', '1', v)
        v = re.sub(r'{... in ...}', '1', v, 1)
        if not set(v).issubset(set('1234567890*-+./() ')) or '**' in v:
            raise ValueError, "only {mtgox(ask|bid|last|high|low|avg)}, {bitstamp(ask|bid|last|high|low|avg)}, one {... in ...}, and arithmetic allowed."
        eval(v)
        state.args.append(args[0])
        del args[0]
    except:
        state.errorInvalid(type, args[0])

def getPositiveFloat(irc, msg, args, state, type='positive floating point number'):
    try:
        v = float(args[0])
        if v <= 0:
            raise ValueError, "only positive numbers allowed."
        state.args.append(v)
        del args[0]
    except ValueError:
        state.errorInvalid(type, args[0])

def getNonNegativeFloat(irc, msg, args, state, type=' floating point number'):
    try:
        v = float(args[0])
        if v < 0:
            raise ValueError, "only non-negative numbers allowed."
        state.args.append(v)
        del args[0]
    except ValueError:
        state.errorInvalid(type, args[0])

addConverter('at', getAt)
addConverter('positiveFloat', getPositiveFloat)
addConverter('nonNegativeFloat', getNonNegativeFloat)
addConverter('indexedPrice', getIndexedPrice)
#addConverter('btc', getBTC)

class OTCOrderBook(callbacks.Plugin):
    """This plugin maintains an order book for order entry over irc.
    Use commands 'buy' and 'sell' to enter orders.
    Use command 'renew' to renew your open orders.
    Use command 'remove' to cancel open orders.
    """
    threaded = True

    def __init__(self, irc):
        self.__parent = super(OTCOrderBook, self)
        self.__parent.__init__(irc)
        self.filename = conf.supybot.directories.data.dirize('OTCOrderBook.db')
        self.db = OTCOrderDB(self.filename)
        self.db.open()
        self.irc = irc
        self.currency_cache = {}

    def die(self):
        self.__parent.die()
        self.db.close()

    def _checkGPGAuth(self, irc, prefix):
        return irc.getCallback('GPG')._ident(prefix)

    def _getTrust(self, irc, sourcenick, destnick):
        return irc.getCallback('RatingSystem')._gettrust(sourcenick, destnick)

    def _getMtgoxQuote(self):
        try:
            ticker = utils.web.getUrl('https://data.mtgox.com/api/2/BTCUSD/money/ticker')
            self.ticker = json.loads(ticker, parse_float=str, parse_int=str)
            self.ticker = self.ticker['data']
        except:
            pass # don't want to die on failure of mtgox

    def _getCurrencyConversion(self, rawprice):
        conv = re.search(r'{(...) in (...)}', rawprice)
        if conv is None:
            return rawprice
        yahoorate = self._queryYahooRate(conv.group(1), conv.group(2))
        indexedprice = re.sub(r'{... in ...}', yahoorate, rawprice)
        return indexedprice

    def _queryYahooRate(self, cur1, cur2):
        try:
            cachedvalue = self.currency_cache[cur1+cur2]
            if time.time() - cachedvalue['time'] < 60:
                return cachedvalue['rate']
        except KeyError:
            pass
        queryurl = "http://query.yahooapis.com/v1/public/yql?q=select%%20*%%20from%%20yahoo.finance.xchange%%20where%%20pair=%%22%s%s%%22&env=store://datatables.org/alltableswithkeys&format=json"
        yahoorate = utils.web.getUrl(queryurl % (cur1, cur2,))
        yahoorate = json.loads(yahoorate, parse_float=str, parse_int=str)
        rate = yahoorate['query']['results']['rate']['Rate']
        if float(rate) == 0:
            raise ValueError, "no data"
        self.currency_cache[cur1 + cur2] = {'time':time.time(), 'rate':rate}
        return rate

    def _getIndexedValue(self, rawprice):
        try:
            goxtic = self.irc.getCallback('Market')._getMtgoxTicker('USD')
            btsptic = self.irc.getCallback('Market')._getBtspTicker('USD')
            indexedprice = rawprice
            if re.search('mtgox', rawprice):
                indexedprice = re.sub(r'{mtgoxask}', str(goxtic['ask']), indexedprice)
                indexedprice = re.sub(r'{mtgoxbid}', str(goxtic['bid']), indexedprice)
                indexedprice = re.sub(r'{mtgoxlast}', str(goxtic['last']), indexedprice)
                indexedprice = re.sub(r'{mtgoxhigh}', str(goxtic['high']), indexedprice)
                indexedprice = re.sub(r'{mtgoxlow}', str(goxtic['low']), indexedprice)
                indexedprice = re.sub(r'{mtgoxavg}', str(goxtic['avg']), indexedprice)
            if re.search('bitstamp', rawprice):
                indexedprice = re.sub(r'{bitstampask}', str(btsptic['ask']), indexedprice)
                indexedprice = re.sub(r'{bitstampbid}', str(btsptic['bid']), indexedprice)
                indexedprice = re.sub(r'{bitstamplast}', str(btsptic['last']), indexedprice)
                indexedprice = re.sub(r'{bitstamphigh}', str(btsptic['high']), indexedprice)
                indexedprice = re.sub(r'{bitstamplow}', str(btsptic['low']), indexedprice)
                indexedprice = re.sub(r'{bitstampavg}', str(btsptic['avg']), indexedprice)
            indexedprice = self._getCurrencyConversion(indexedprice)
            return "%.5g" % eval(indexedprice)
        except:
            return '"' + rawprice + '"'

    def buy(self, irc, msg, args, optlist, amount, thing, price, otherthing, notes):
        """[--long] <amount> <thing> [at|@] <priceperunit> <otherthing> [<notes>]

        Logs a buy order for <amount> units of <thing>, at a price of <price>
        per unit, in units of <otherthing>. Use the optional <notes> field to
        put in any special notes. <price> may include an arithmetical expression,
        and {(mtgox|bitstamp)(ask|bid|last|high|low|avg)} to index price to mtgox ask, bid, last,
        high, low, or avg price.
        May also include expression of the form {... in ...} which queries google
        for a currency conversion rate between two currencies.
        If '--long' option is given, puts in a longer-duration order, but this is only
        allowed if you have a sufficient trust rating.
        """
        self.db.deleteExpired(self.registryValue('orderExpiry'))
        gpgauth = self._checkGPGAuth(irc, msg.prefix)
        if gpgauth is None:
            irc.error("For identification purposes, you must be identified via GPG "
                      "to use the order book.")
            return
        results = self.db.getByNick(gpgauth['nick'])
        if len(results) >= self.registryValue('maxUserOpenOrders'):
            irc.error("You may not have more than %s outstanding open orders." % \
                      self.registryValue('maxUserOpenOrders'))
            return
        extratime = 0
        if dict(optlist).has_key('long'):
            extratime = self.registryValue('longOrderDuration')
            trust = self._getTrust(irc, 'nanotube', gpgauth['nick'])
            sumtrust = sum([t for t,n in trust])
            if sumtrust < self.registryValue('minTrustForLongOrders'):
                irc.error("You must have a minimum of %s cumulative trust at "
                        "level 1 and level 2 from nanotube to "
                        "to place long orders." % (self.registryValue('minTrustForLongOrders'),))
                return
        orderid = self.db.buy(gpgauth['nick'], msg.host, amount, thing, price, otherthing, notes, extratime)
        irc.reply("Order id %s created." % (orderid,))
        if not world.testing:
            irc.queueMsg(ircmsgs.privmsg("#bitcoin-otc-ticker",
                    "#%s || %s || BUY %s %s @ %s %s || %s" % (orderid,
                            gpgauth['nick'],
                            amount,
                            thing,
                            self._getIndexedValue(price),
                            otherthing,
                            notes,)))
    buy = wrap(buy, [getopts({'long': '',}), 'positiveFloat', 'something',
            'at', 'indexedPrice', 'something', optional('text')])

    def sell(self, irc, msg, args, optlist, amount, thing, price, otherthing, notes):
        """<amount> <thing> [at|@] <priceperunit> <otherthing> [<notes>]

        Logs a sell order for <amount> units of <thing, at a price of <price>
        per unit, in units of <otherthing>. Use the optional <notes> field to
        put in any special notes. <price> may include an arithmetical expression,
        and {(mtgox|bitstamp)(ask|bid|last|high|low|avg)} to index price to mtgox ask, bid, last,
        high, low, or avg price.
        May also include expression of the form {... in ...} which queries google
        for a currency conversion rate between two currencies.
        If '--long' option is given, puts in a longer-duration order, but this is only
        allowed if you have a sufficient trust rating.
        """
        self.db.deleteExpired(self.registryValue('orderExpiry'))
        gpgauth = self._checkGPGAuth(irc, msg.prefix)
        if gpgauth is None:
            irc.error("For identification purposes, you must be identified via GPG "
                      "to use the order book.")
            return
        results = self.db.getByNick(gpgauth['nick'])
        if len(results) >= self.registryValue('maxUserOpenOrders'):
            irc.error("You may not have more than %s outstanding open orders." % \
                      self.registryValue('maxUserOpenOrders'))
            return
        extratime = 0
        if dict(optlist).has_key('long'):
            extratime = self.registryValue('longOrderDuration')
            trust = self._getTrust(irc, 'nanotube', gpgauth['nick'])
            sumtrust = sum([t for t,n in trust])
            if sumtrust < self.registryValue('minTrustForLongOrders'):
                irc.error("You must have a minimum of %s cumulative trust at "
                        "level 1 and level 2 from nanotube to "
                        "to place long orders." % (self.registryValue('minTrustForLongOrders'),))
                return
        orderid = self.db.sell(gpgauth['nick'], msg.host, amount, thing, price, otherthing, notes, extratime)
        irc.reply("Order id %s created." % (orderid,))
        if not world.testing:
            irc.queueMsg(ircmsgs.privmsg("#bitcoin-otc-ticker",
                    "#%s || %s || SELL %s %s @ %s %s || %s" % (orderid,
                            gpgauth['nick'],
                            amount,
                            thing,
                            self._getIndexedValue(price),
                            otherthing,
                            notes,)))
    sell = wrap(sell, [getopts({'long': '',}), 'positiveFloat', 'something',
            'at', 'indexedPrice', 'something', optional('text')])

    def refresh(self, irc, msg, args, optlist, orderid):
        """[<orderid>]

        Refresh the timestamps on your outstanding orders. If optional
        <orderid> argument present, only refreshes that particular order.
        If '--long' option is given, refreshes for a longer duration, but this is only
        allowed if you have a sufficient trust rating.
        """
        self.db.deleteExpired(self.registryValue('orderExpiry'))
        gpgauth = self._checkGPGAuth(irc, msg.prefix)
        if gpgauth is None:
            irc.error("For identification purposes, you must be identified via GPG "
                      "to use the order book.")
            return
        extratime = 0
        if dict(optlist).has_key('long'):
            extratime = self.registryValue('longOrderDuration')
            trust = self._getTrust(irc, 'nanotube', gpgauth['nick'])
            sumtrust = sum([t for t,n in trust])
            if sumtrust < self.registryValue('minTrustForLongOrders'):
                irc.error("You must have a minimum of %s cumulative trust at "
                        "level 1 and level 2 from nanotube to "
                        "to place long orders." % (self.registryValue('minTrustForLongOrders'),))
                return
        rv = self.db.refresh(gpgauth['nick'], orderid, extratime)
        if rv is not False:
            irc.reply("Order refresh successful, %s orders refreshed." % rv)
        else:
            irc.error("No orders found to refresh. Try the 'view' command to "
                      "view your open orders.")
    refresh = wrap(refresh, [getopts({'long': '',}), optional('int')])

    def remove(self, irc, msg, args, orderid):
        """<orderid>

        Remove an outstanding order by <orderid>.
        """
        self.db.deleteExpired(self.registryValue('orderExpiry'))
        gpgauth = self._checkGPGAuth(irc, msg.prefix)
        if gpgauth is None:
            irc.error("For identification purposes, you must be identified via GPG "
                      "to use the order book.")
            return
        rv = self.db.remove(gpgauth['nick'], orderid)
        if rv is False:
            irc.error("No orders found to remove. Try the 'view' command to "
                      "view your open orders.")
            return
        irc.reply("Order %s removed." % orderid)
        if not world.testing:
            irc.queueMsg(ircmsgs.privmsg("#bitcoin-otc-ticker",
                    "Removed #%s || %s" % (orderid,
                            gpgauth['nick'],)))
    remove = wrap(remove, ['int',])

    def view(self, irc, msg, args, optlist, query):
        """[--raw] [<orderid>|<nick>]

        View information about your outstanding orders. If optional <orderid>
        or <nick> argument is present, only show orders with that id or nick.
        If '--raw' option is given, show raw price input, rather than the
        resulting indexed value.
        """
        self.db.deleteExpired(self.registryValue('orderExpiry'))
        gpgauth = self._checkGPGAuth(irc, msg.prefix)
        raw = False
        for (option, arg) in optlist:
            if option == 'raw':
                raw = True
        if raw:
            f = lambda x: '"%s"' % x
        else:
            f = self._getIndexedValue
        if query is None:
            if gpgauth is None:
                nick = msg.nick
            else:
                nick = gpgauth['nick']
            results = self.db.getByNick(nick)
        elif isinstance(query, int):
            results = self.db.getById(query)
        else:
            nick = query
            results = self.db.getByNick(nick)
        if len(results) == 0:
            irc.error("No orders found matching these criteria.")
            return
        if len(results) > self.registryValue('maxOrdersInBookList'):
            irc.error("Too many orders to list on IRC. Visit "
                    "http://bitcoin-otc.com/vieworderbook.php?nick=%s "
                    "to see the list of matching orders." % (nick,))
            return
        L = ["#%s %s %s %s %s %s @ %s %s (%s)" % (id,
                                                   time.ctime(refreshed_at),
                                                   nick,
                                                   buysell,
                                                   amount,
                                                   thing,
                                                   f(price),
                                                   otherthing,
                                                   notes) \
             for (id,
                  created_at,
                  refreshed_at,
                  buysell,
                  nick,
                  host,
                  amount,
                  thing,
                  price,
                  otherthing,
                  notes) in results]

        irc.replies(L, joiner=" || ")
    view = wrap(view, [getopts({'raw': '',}), optional(first('int','something'))])
    
    def book(self, irc, msg, args, thing):
        """<thing>

        Get a list of open orders for <thing>.
        Web view: http://bitcoin-otc.com/vieworderbook.php
        """
        self.db.deleteExpired(self.registryValue('orderExpiry'))
        results = self.db.getCurrencyBook(thing)
        if len(results) == 0:
            irc.error("No orders for this currency present in database.")
            return
        if len(results) > self.registryValue('maxOrdersInBookList'):
            irc.error("Too many orders to list on IRC. Visit the web "
                      "order book, http://bitcoin-otc.com/vieworderbook.php?eitherthing=%s "
                      "to see list of orders for this item." % (thing,))
            return
        L = ["#%s %s %s %s %s %s @ %s %s (%s)" % (id,
                                                      time.ctime(refreshed_at),
                                                      nick,
                                                      buysell,
                                                      amount,
                                                      thing,
                                                      self._getIndexedValue(price),
                                                      otherthing,
                                                      notes) \
             for (id,
                  created_at,
                  refreshed_at,
                  buysell,
                  nick,
                  host,
                  amount,
                  thing,
                  price,
                  otherthing,
                  notes) in results]
        irc.replies(L, joiner=" || ")
    book = wrap(book, ['something'])

Class = OTCOrderBook


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2010, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *
import unittest

import sqlite3

class OTCOrderBookTestCase(PluginTestCase):
    plugins = ('OTCOrderBook','GPG','RatingSystem','Market')

    def setUp(self):
        PluginTestCase.setUp(self)

        #preseed the GPG db with a GPG registration and auth for nanotube
        gpg = self.irc.getCallback('GPG')
        gpg.db.register('AAAAAAAAAAAAAAA1', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA1',
                    '1somestuff', time.time(), 'nanotube')
        gpg.authed_users['nanotube!stuff@stuff/somecloak'] = {'nick':'nanotube'}
        gpg.db.register('AAAAAAAAAAAAAAA2', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA2',
                   '1somestuff',  time.time(), 'registeredguy')
        gpg.db.register('AAAAAAAAAAAAAAA3', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA3',
                    '1somestuff', time.time(), 'authedguy')
        gpg.authed_users['authedguy!stuff@123.345.234.34'] = {'nick':'authedguy'}
        gpg.db.register('AAAAAAAAAAAAAAA4', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA4',
                    '1somestuff', time.time(), 'authedguy2')
        gpg.authed_users['authedguy2!stuff@123.345.234.34'] = {'nick':'authedguy2'}

        # pre-seed the rating db with some ratings, for testing long orders
        cb = self.irc.getCallback('RatingSystem')
        cursor = cb.db.db.cursor()
        cursor.execute("""INSERT INTO users VALUES
                          (NULL, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (10, time.time(), 1, 0, 0, 0, 'nanotube','stuff/somecloak'))
        cursor.execute("""INSERT INTO users VALUES
                          (NULL, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (10, time.time(), 1, 0, 0, 0, 'authedguy','stuff/somecloak'))
        cursor.execute("""INSERT INTO users VALUES
                          (NULL, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (10, time.time(), 1, 0, 0, 0, 'authedguy2','stuff/somecloak'))
        cursor.execute("""INSERT INTO ratings VALUES
                          (NULL, ?, ?, ?, ?, ?)""",
                       (2,1, time.time(), 10, 'great guy'))
        cursor.execute("""INSERT INTO ratings VALUES
                          (NULL, ?, ?, ?, ?, ?)""",
                       (3,2, time.time(), 10, 'great guy'))
        cursor.execute("""INSERT INTO ratings VALUES
                          (NULL, ?, ?, ?, ?, ?)""",
                       (3,1, time.time(), 10, 'great guy'))
        cb.db.db.commit()
    
    def testBuy(self):
        # no gpg auth
        self.assertError('otcorderbook buy 1000 btc at 0.06 LRUSD really nice offer!')
        try:
            origuser = self.prefix
            self.prefix = 'nanotube!stuff@stuff/somecloak'
            self.assertRegexp('otcorderbook buy 1000 btc at 0.06 LRUSD really nice offer!', 'Order id \d+ created')
            self.assertNotError('otcorderbook buy 2000 bitcoins @ 0.06 LRUSD')
            self.assertNotError('otcorderbook buy 3000 bitcoin at 0.07 PPUSD really nice offer!')
            self.assertNotError('otcorderbook buy 4000 btc at 10 LRUSD some text')
            self.assertNotError('view')
            self.assertRegexp('view 1', 'buy 1000')
            self.assertError('otcorderbook buy 5000 btc at 0.06 LRUSD mooo') # max orders
            self.assertRegexp('view', '1000.*2000')
            self.assertError('otcorderbook buy --long 5000 btc at 0.06 USD this is a long order') #not enough trust
            self.prefix = 'authedguy2!stuff@123.345.234.34'
            self.assertNotError('otcorderbook buy --long 5000 btc at 0.06 USD this is a long order') #now we have 20 total trust
            self.assertRegexp('view', '5000')
        finally:
            self.prefix = origuser

    def testSell(self):
        # no gpg auth
        self.assertError('otcorderbook buy 1000 btc at 0.06 LRUSD really nice offer!')
        try:
            origuser = self.prefix
            self.prefix = 'nanotube!stuff@stuff/somecloak'
            self.assertRegexp('otcorderbook sell 1000 btc at 0.06 LRUSD really nice offer!', 'Order id \d+ created')
            self.assertNotError('otcorderbook sell 2000 bitcoins @ 0.06 LRUSD')
            self.assertNotError('otcorderbook sell 3000 bitcoin at 0.07 PPUSD really nice offer!')
            self.assertNotError('otcorderbook sell 4000 btc at 10 LRUSD some text')
            self.assertNotError('view')
            self.assertError('otcorderbook sell 5000 btc at 0.06 LRUSD mooo') # max orders
            self.assertRegexp('view', '1000.*2000')
            self.assertError('otcorderbook sell --long 5000 btc at 0.06 USD this is a long order') #not enough trust
            self.prefix = 'authedguy2!stuff@123.345.234.34'
            self.assertNotError('otcorderbook sell --long 5000 btc at 0.06 USD this is a long order') #now we have 20 total trust
            self.assertRegexp('view', '5000')
        finally:
            self.prefix = origuser

    def testRefresh(self):
        try:
            origuser = self.prefix
            self.prefix = 'nanotube!stuff@stuff/somecloak'
            self.assertNotError('otcorderbook buy 1000 btc at 0.06 LRUSD really nice offer!')
            self.assertNotError('refresh')
            self.assertNotError('refresh 1')
            self.assertRegexp('view', '1000')
            self.assertError('refresh --long') #not enough trust
            self.prefix = 'authedguy2!stuff@123.345.234.34' #now we have 20 total trust
            self.assertNotError('otcorderbook buy 5000 btc at 0.06 USD this is a long order') 
            self.assertNotError('refresh --long')
        finally:
            self.prefix = origuser

    def testRemove(self):
        try:
            origuser = self.prefix
            self.prefix = 'nanotube!stuff@stuff/somecloak'
            self.assertNotError('otcorderbook buy 1000 btc at 0.06 LRUSD really nice offer!')
            self.assertNotError('otcorderbook sell 2000 btc at 0.06 LRUSD really nice offer!')
            self.assertRegexp('view', '1000.*2000')
            self.assertNotError('remove 1')
            self.assertNotRegexp('view', '1000.*2000')
            self.assertRegexp('view', '2000')
            self.assertNotError('otcorderbook buy 1000 btc at 0.06 LRUSD really nice offer!')
            self.assertNotError('remove 2')
            self.assertNotError('remove 3')
            self.assertError('view')
        finally:
            self.prefix = origuser

    def testBook(self):
        try:
            origuser = self.prefix
            self.prefix = 'nanotube!stuff@stuff/somecloak'
            self.assertNotError('otcorderbook buy 1000 btc at 0.06 LRUSD really nice offer!')
            self.assertNotError('otcorderbook sell 2000 btc at 0.07 LRUSD really nice offer!')
            self.assertNotError('otcorderbook buy 3000 btc at 0.06 PPUSD really nice offer!')
            self.assertNotError('otcorderbook sell 4000 btc at 0.06 PPUSD really nice offer!')
            self.assertRegexp('view', '1000.*2000.*3000.*4000')
            self.assertNotRegexp('book LRUSD', '1000.*2000.*3000.*4000')
            self.assertRegexp('book LRUSD', '1000.*2000')
            self.assertNotError('remove 4')
            self.assertNotError('otcorderbook buy 5000 btc at 0.05 LRUSD')
            self.assertRegexp('book LRUSD', '5000.*1000.*2000')
        finally:
            self.prefix = origuser

    def testIndexing(self):
        try:
            origuser = self.prefix
            self.prefix = 'nanotube!stuff@stuff/somecloak'
            self.assertNotError('otcorderbook buy 1000 btc at "{mtgoxbid} - 0.03" ppusd')
            self.assertRegexp('view', 'buy 1000.0 btc @ \d')
            self.assertRegexp('view --raw', 'buy 1000.0 btc @ "{mtgoxbid}')
            self.assertNotError('remove 1')
            self.assertNotError('otcorderbook sell 1000 btc at "{mtgoxask} + 0.03" ppusd')
            self.assertRegexp('view', 'sell 1000.0 btc @ \d')
            self.assertRegexp('view --raw', 'sell 1000.0 btc @ "{mtgoxask}')
            self.assertNotError('remove 2')
            self.assertNotError('otcorderbook buy 1000 btc at "0.5*({mtgoxask} + {mtgoxbid})" ppusd split the spread')
            self.assertRegexp('view', 'buy 1000.0 btc @ \d')
            self.assertNotError('remove 3')
            self.assertNotError('otcorderbook buy 1000 btc at "{mtgoxlast} - 0.03" ppusd')
            self.assertRegexp('view', 'buy 1000.0 btc @ \d')
            self.assertRegexp('view --raw', 'buy 1000.0 btc @ "{mtgoxlast}')
            self.assertRegexp('book ppusd', 'buy 1000.0 btc @ \d')
            self.assertNotError('remove 4')
            self.assertNotError('otcorderbook buy 1000 btc at "({mtgoxlast} - 0.03) * {usd in eur}" ppeur')
            self.assertRegexp('view', 'buy 1000.0 btc @ \d')
            self.assertRegexp('view --raw', 'buy 1000.0 btc @ "\({mtgoxlast}')
            self.assertNotError('remove 5')
            self.assertNotError('otcorderbook buy 1000 btc at "0.5*({mtgoxlast} + {bitstamplast})" ppusd average the markets')
            self.assertRegexp('view', 'buy 1000.0 btc @ \d')
            self.assertError('otcorderbook buy 1000 btc at "{zomg} + 1" ppusd');
        finally:
            self.prefix = origuser

    def testView(self):
        try:
            origuser = self.prefix
            self.prefix = 'nanotube!stuff@stuff/somecloak'
            self.assertNotError('otcorderbook buy 1000 btc at .8 usd')
            self.assertNotError('otcorderbook sell 2000 btc at .9 usd')
            self.assertRegexp('view', '1000.*2000')
            self.assertRegexp('view 1', '1000')
            self.assertRegexp('view nanotube', '1000.*2000')
            self.prefix = 'authedguy!stuff@123.345.234.34'
            self.assertNotError('otcorderbook buy 3000 btc at .7 eur')
            self.assertNotError('otcorderbook sell 4000 btc at .8 eur')
            self.assertRegexp('view 2', '2000')
            self.assertRegexp('view', '3000.*4000')
            self.assertRegexp('view nanotube', '1000.*2000')
            self.assertRegexp('view naNOtuBe', '1000.*2000')
        finally:
            self.prefix = origuser

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = createticker
###
# Parse the OTC Order Book to create the inside quote ticker data.
# Copyright (C) 2010, Daniel Folkinshteyn <nanotube@users.sourceforge.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###

import sqlite3
import urllib2
import re
import json
import os
import time

class Quote:
    def __init__(self, rawbids, rawasks, btcbidsinverse, btcasksinverse, currency, mtgox_ticker):
        self.currency = currency
        self.ticker = mtgox_ticker
        self.bids = []
        self.asks = []
        self.bestbid = None
        self.bestask = None
        self.currency_rates = {}
        for item in rawbids:
            bid = self._getIndexedValue(item[0])
            if bid is not None:
                self.bids.append(bid)
        for item in rawasks:
            ask = self._getIndexedValue(item[0])
            if ask is not None:
                self.asks.append(ask)
        for item in btcbidsinverse:
            bid = self._getIndexedValue(item[0], inverse=True)
            if bid is not None:
                self.bids.append(bid)
        for item in btcasksinverse:
            ask = self._getIndexedValue(item[0], inverse=True)
            if ask is not None:
                self.asks.append(ask)

        if len(self.bids) > 0:
            self.bestbid = max(self.bids)
        if len(self.asks) > 0:
            self.bestask = min(self.asks)

    def _getCurrencyConversion(self, rawprice):
        conv = re.search(r'{(...) in (...)}', rawprice)
        if conv is None:
            return rawprice
        if conv.group(0).lower() not in self.currency_rates.keys():
            googlerate = self._queryGoogleRate(conv.group(1), conv.group(2))
            self.currency_rates[conv.group(0).lower()] = googlerate
        indexedprice = re.sub(r'{... in ...}', self.currency_rates[conv.group(0)], rawprice)
        return indexedprice

    def _queryGoogleRate(self, cur1, cur2):
        googlerate =urllib2.urlopen('http://www.google.com/ig/calculator?hl=en&q=1%s=?%s' % \
                (cur1, cur2,)).read()
        googlerate = re.sub(r'(\w+):', r'"\1":', googlerate) # badly formed json, missing quotes
        googlerate = json.loads(googlerate, parse_float=str, parse_int=str)
        if googlerate['error']:
            raise ValueError, googlerate['error']
        return googlerate['rhs'].split()[0]

    def _getIndexedValue(self, rawprice, inverse=False):
        try:
            if self.ticker is not None:
                indexedprice = re.sub(r'{mtgoxask}', self.ticker['sell']['value'], rawprice)
                indexedprice = re.sub(r'{mtgoxbid}', self.ticker['buy']['value'], indexedprice)
                indexedprice = re.sub(r'{mtgoxlast}', self.ticker['last']['value'], indexedprice)
            else:
                indexedprice = rawprice
            indexedprice = self._getCurrencyConversion(indexedprice)
            if inverse:
                indexedprice = 1. / indexedprice
            return "%.5g" % eval(indexedprice)
        except:
            return None

    def json(self):
        js = {self.currency: {'bid': self.bestbid, 'ask': self.bestask}}
        return js

    def sql(self):
        sql = "INSERT INTO quotes VALUES (NULL, '%s', '%s', '%s')" %\
                (self.currency, self.bestbid, self.bestask,)
        return sql

class QuoteCreator:
    def __init__(self, orderbook_db_path, quote_db_path, json_path):
        self.json_path = json_path
        self.quote_db_path = quote_db_path
        self.quotes = []
        self.currency_codes = \
            ['AED', 'ANG', 'ARS', 'AUD', 'BDT', 'BGN', 'BHD', 'BND', 'BOB',
            'BRL', 'BWP', 'CAD', 'CHF', 'CLP', 'CNY', 'COP', 'CRC', 'CZK',
            'DKK', 'DOP', 'DZD', 'EEK', 'EGP', 'EUR', 'FJD', 'GBP', 'HKD',
            'HNL', 'HRK', 'HUF', 'IDR', 'ILS', 'INR', 'ISK', 'JMD', 'JOD',
            'JPY', 'KES', 'KRW', 'KWD', 'KYD', 'KZT', 'LBP', 'LKR', 'LTL',
            'LVL', 'MAD', 'MDL', 'MKD', 'MUR', 'MVR', 'MXN', 'MYR', 'NAD',
            'NGN', 'NIO', 'NOK', 'NPR', 'NZD', 'OMR', 'PEN', 'PGK', 'PHP',
            'PKR', 'PLN', 'PYG', 'QAR', 'RON', 'RSD', 'RUB', 'SAR', 'SCR',
            'SEK', 'SGD', 'SKK', 'SLL', 'SVC', 'THB', 'TND', 'TRY', 'TTD',
            'TWD', 'TZS', 'UAH', 'UGX', 'USD', 'UYU', 'UZS', 'VEF', 'VND',
            'XOF', 'YER', 'ZAR', 'ZMK', 'ZWR',]
        self.db1 = sqlite3.connect(orderbook_db_path)

    def run(self):
        try:
            self.get_mtgox_quote()
        except:
            self.mtgox_ticker = None
        self.create_quotes()
        self.write_quotedb()
        self.write_json()

    def get_mtgox_quote(self):
        mtgox_ticker = urllib2.urlopen('https://data.mtgox.com/api/2/BTCUSD/money/ticker').read()
        self.mtgox_ticker = json.loads(mtgox_ticker, parse_float=str, parse_int=str)
        self.mtgox_ticker = self.mtgox_ticker['data']

    def create_quotes(self):
        cursor = self.db1.cursor()
        for code in self.currency_codes:
            sql = """SELECT price FROM orders WHERE
                    (buysell = 'BUY' AND thing LIKE 'BTC' AND otherthing LIKE ?)"""
            cursor.execute(sql, (code,))
            btcbids = cursor.fetchall()
            sql = """SELECT price FROM orders WHERE
                    (buysell = 'SELL' AND thing LIKE ? AND otherthing LIKE 'BTC')"""
            cursor.execute(sql, (code,))
            btcbidsinverse = cursor.fetchall()

            sql = """SELECT price FROM orders WHERE
                    (buysell = 'SELL' AND thing LIKE 'BTC' AND otherthing LIKE ?)"""
            cursor.execute(sql, (code,))
            btcasks = cursor.fetchall()
            sql = """SELECT price FROM orders WHERE
                    (buysell = 'BUY' AND thing LIKE ? AND otherthing LIKE 'BTC')"""
            cursor.execute(sql, (code,))
            btcasksinverse = cursor.fetchall()

            if len(btcasks) != 0 or len(btcbids) != 0:
                quote = Quote(btcbids, btcasks, btcbidsinverse, btcasksinverse, code, self.mtgox_ticker)
                self.quotes.append(quote)

    def write_quotedb(self):
        try:
            os.remove(self.quote_db_path)
        except OSError:
            pass
        db2 = sqlite3.connect(self.quote_db_path)
        cursor = db2.cursor()
        cursor.execute("""CREATE TABLE quotes (
                          id INTEGER PRIMARY KEY,
                          currency TEXT,
                          bid TEXT,
                          ask TEXT)
                          """)
        db2.commit()
        for quote in self.quotes:
            cursor.execute(quote.sql())
        db2.commit()

    def write_json(self):
        json_dict = {}
        [json_dict.update(quote.json()) for quote in self.quotes]
        json_dict = {'ticker': json_dict, 'timestamp': time.time()}
        f = open(self.json_path, 'w')
        f.write(json.dumps(json_dict))
        f.close()

if __name__ == '__main__':
    qc = QuoteCreator('otc/OTCOrderBook.db', 'OTCQuotes.db', 'quotes.json')
    qc.run()

########NEW FILE########
__FILENAME__ = getexchangerates
import re
import json
import urllib2
import sqlite3

class ExchangeRates:
    def __init__(self, orderbook_db_path, json_path):
        self.json_path = json_path
        self.currency_rates = {}
        self.db = sqlite3.connect(orderbook_db_path)

    def _getCurrencyConversion(self, rawprice):
        conv = re.search(r'{(...) in (...)}', rawprice)
        if (conv is not None) and (conv.group(0).lower() not in self.currency_rates.keys()):
            yahoorate = self._queryYahooRate(conv.group(1), conv.group(2))
            self.currency_rates[conv.group(0).lower()] = yahoorate

    def _queryYahooRate(self, cur1, cur2):
        queryurl = "http://query.yahooapis.com/v1/public/yql?q=select%%20*%%20from%%20yahoo.finance.xchange%%20where%%20pair=%%22%s%s%%22&env=store://datatables.org/alltableswithkeys&format=json"
        yahoorate = urllib2.urlopen(queryurl % (cur1, cur2,)).read()
        yahoorate = json.loads(yahoorate, parse_float=str, parse_int=str)
        rate = yahoorate['query']['results']['rate']['Rate']
        if float(rate) == 0:
            raise ValueError, "no data"
        return rate

    def write_json(self):
        f = open(self.json_path, 'w')
        f.write(json.dumps(self.currency_rates))
        f.close()

    def run(self):
        cursor = self.db.cursor()
        cursor.execute("""SELECT price FROM orders WHERE price LIKE ?""", ("%{___ in ___}%", ))
        result = cursor.fetchall()
        for item in result:
            self._getCurrencyConversion(item[0])
        self.write_json()

if __name__ == '__main__':
    er = ExchangeRates( 'otc/OTCOrderBook.db', 'exchangerates.json')
    er.run()
########NEW FILE########
__FILENAME__ = grabexternaltickers
###
# Retrieve ticker data from external sources and write in standardized format.
# Copyright (C) 2013, Daniel Folkinshteyn <nanotube@users.sourceforge.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###

import urllib2
import json

opener = urllib2.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0 (X11; Linux x86_64; rv:22.0) Gecko/20100101 Firefox/22.0')]
urllib2.install_opener(opener)

def get_bitstamp_ticker():
    try:
        json_data = urllib2.urlopen("https://www.bitstamp.net/api/ticker/").read()
        ticker = json.loads(json_data)
        bcharts = json.loads(urllib2.urlopen("http://api.bitcoincharts.com/v1/markets.json").read())
        bcharts = filter(lambda x: x['symbol'] == 'bitstampUSD', bcharts)[0]
        stdticker = {'bid': ticker['bid'],
                            'ask': ticker['ask'],
                            'last': ticker['last'],
                            'vol': ticker['volume'],
                            'low': ticker['low'],
                            'high': ticker['high'],
                            'avg': str(bcharts['avg'])}
    except:
        stdticker = {'error':'something failed'}
    return stdticker

def get_mtgox_ticker():
    try:
        json_data = urllib2.urlopen("https://data.mtgox.com/api/2/BTC%s/money/ticker" % ('USD',)).read()
        ticker = json.loads(json_data)
        ftj = urllib2.urlopen("http://data.mtgox.com/api/2/BTC%s/money/ticker_fast" % ('USD',)).read()
        tf = json.loads(ftj)
        if ticker['result'] != 'error' and tf['result'] != 'error': # use fast ticker where available
            ticker['data']['buy']['value'] = tf['data']['buy']['value']
            ticker['data']['sell']['value'] = tf['data']['sell']['value']
            ticker['data']['last']['value'] = tf['data']['last']['value']
        if ticker['result'] == 'error':
             stdticker = {'error':ticker['error']}
        else:
            stdticker = {'bid': ticker['data']['buy']['value'],
                                'ask': ticker['data']['sell']['value'],
                                'last': ticker['data']['last']['value'],
                                'vol': ticker['data']['vol']['value'],
                                'low': ticker['data']['low']['value'],
                                'high': ticker['data']['high']['value'],
                                'avg': ticker['data']['vwap']['value']}
    except:
        stdticker = {'error':'something failed'}
    return stdticker

def write_json(data, fname):
    f = open(fname, 'w')
    f.write(json.dumps(data))
    f.close()

if __name__ == '__main__':
    goxtic = get_mtgox_ticker()
    write_json(goxtic, 'mtgox.json')
    btsptic = get_bitstamp_ticker()
    write_json(btsptic, 'bitstamp.json')

########NEW FILE########
__FILENAME__ = jsonifyorderbook
import json
import sqlite3

class JsonifyOrderBook:
    def __init__(self, orderbook_db_path, json_path):
        self.json_path = json_path
        self.db = sqlite3.connect(orderbook_db_path)
        self.db.text_factory = str

    def run(self):
        i = True
        f = open(self.json_path, 'w')
        f.write('[')
        cursor = self.db.cursor()
        cursor.execute("""SELECT id,created_at,refreshed_at,buysell,nick,amount,thing,price,otherthing,notes FROM orders""")
        for row in cursor:
            d = dict(zip(['id','created_at','refreshed_at','buysell','nick','amount','thing','price','otherthing','notes'],row))
            if not i:
                f.write(',')
            try:
                f.write(json.dumps(d, encoding='latin1'))
            except:
                pass # if it's not decodable, skip it without further ado.
            i = False
        f.write(']')

if __name__ == '__main__':
    job = JsonifyOrderBook( 'otc/OTCOrderBook.db', 'orderbook.json')
    job.run()

########NEW FILE########
__FILENAME__ = config
###
# Copyright (c) 2010, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('RatingSystem', True)


RatingSystem = conf.registerPlugin('RatingSystem')

conf.registerGlobalValue(RatingSystem, 'requirePositiveRating',
    registry.Boolean(True, """Only allow users with a positive rating to enter
    ratings."""))

conf.registerGlobalValue(RatingSystem, 'ratingMax',
    registry.PositiveInteger(10, """Maximum possible trust rating that can be
    given to a user."""))

conf.registerGlobalValue(RatingSystem, 'ratingMin',
    registry.Integer(-10, """Minimum possible trust rating that can be
    given to a user."""))

conf.registerGlobalValue(RatingSystem, 'blockedNicks',
    registry.SpaceSeparatedListOfStrings([], """Nicks that do not take
    any incoming ratings. Uppercased.""", private=True))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# OTCOrderBook - supybot plugin to keep an order book from irc
# Copyright (C) 2010, Daniel Folkinshteyn <nanotube@users.sourceforge.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot import conf
from supybot import ircdb
from supybot import world
from supybot import ircmsgs

import sqlite3
import time
import os.path
import re

class RatingSystemDB(object):
    def __init__(self, filename):
        self.filename = filename
        self.db = None

    def _commit(self):
        '''a commit wrapper to give it another few tries if it errors.
        
        which sometimes happens due to:
        OperationalError: database is locked'''
        for i in xrange(10):
            try:
                self.db.commit()
            except:
                time.sleep(1)

    def open(self):
        if os.path.exists(self.filename):
            db = sqlite3.connect(self.filename, check_same_thread = False)
            db.text_factory = str
            self.db = db
            return
        
        db = sqlite3.connect(self.filename, check_same_thread = False)
        db.text_factory = str
        self.db = db
        cursor = self.db.cursor()
        cursor.execute("""CREATE TABLE users (
                          id INTEGER PRIMARY KEY,
                          total_rating INTEGER,
                          created_at INTEGER,
                          pos_rating_recv_count INTEGER,
                          neg_rating_recv_count INTEGER,
                          pos_rating_sent_count INTEGER,
                          neg_rating_sent_count INTEGER,
                          nick TEXT UNIQUE ON CONFLICT REPLACE,
                          host TEXT)
                           """)
        cursor.execute("""CREATE TABLE ratings (
                          id INTEGER PRIMARY KEY,
                          rated_user_id INTEGER,
                          rater_user_id INTEGER,
                          created_at INTEGER,
                          rating INTEGER,
                          notes TEXT)
                          """)
        self._commit()
        return

    def close(self):
        self.db.close()

    def get(self, nick):
        cursor = self.db.cursor()
        nick = nick.replace('|','||').replace('_','|_').replace('%','|%')
        cursor.execute("""SELECT * FROM users WHERE nick LIKE ? ESCAPE '|'""", (nick,))
        return cursor.fetchall()

    def getReceivedRatings(self, nick, sign=None):
        # sign can be "> 0" or "< 0", None means all
        cursor = self.db.cursor()
        nick = nick.replace('|','||').replace('_','|_').replace('%','|%')
        if sign is None:
            cursor.execute("""SELECT * FROM users, ratings WHERE users.nick LIKE ? ESCAPE '|'
                              AND ratings.rated_user_id = users.id""",
                           (nick,))
        else:
            cursor.execute("""SELECT * FROM users, ratings WHERE users.nick LIKE ? ESCAPE '|'
                              AND ratings.rated_user_id = users.id AND
                              ratings.rating %s""" % sign,
                           (nick,))
        return cursor.fetchall()

    def getSentRatings(self, nick, sign=None):
        # sign can be "> 0" or "< 0", None means all
        cursor = self.db.cursor()
        nick = nick.replace('|','||').replace('_','|_').replace('%','|%')
        if sign is None:
            cursor.execute("""SELECT * FROM users, ratings WHERE users.nick LIKE ? ESCAPE '|'
                              AND ratings.rater_user_id = users.id""",
                           (nick,))
        else:
            cursor.execute("""SELECT * FROM users, ratings WHERE users.nick LIKE ? ESCAPE '|'
                              AND ratings.rater_user_id = users.id AND
                              ratings.rating %s""" % sign,
                           (nick,))
        return cursor.fetchall()

    def getLevel2Ratings(self, sourcenick, destnick):
        cursor = self.db.cursor()
        sourcenick = sourcenick.replace('|','||').replace('_','|_').replace('%','|%')
        destnick = destnick.replace('|','||').replace('_','|_').replace('%','|%')
        cursor.execute("""SELECT ratings1.rating, ratings2.rating
                    FROM users as users1, users as users2, ratings as ratings1, ratings as ratings2 WHERE
                    users1.nick LIKE ? ESCAPE '|' AND
                    ratings1.rater_user_id = users1.id AND
                    users2.nick LIKE ? ESCAPE '|' AND
                    ratings2.rated_user_id = users2.id AND
                    ratings2.rater_user_id = ratings1.rated_user_id""", (sourcenick,destnick,))
        l2ratings = cursor.fetchall()
        if len(l2ratings) == 0:
            return (0,0,)
        trustlinks = []
        for row in l2ratings:
            if row[0] > 0 and row[1] > 0:
                trustlinks.append(min(row))
            elif row[0] > 0 and row[1] < 0:
                trustlinks.append(-min(row[0],abs(row[1])))
            elif row[0] < 0:
                trustlinks.append(0)
        return (sum(trustlinks), len(trustlinks),)

    def getExistingRating(self, sourceid, targetid):
        cursor = self.db.cursor()
        cursor.execute("""SELECT * from ratings WHERE
                          rater_user_id = ? AND
                          rated_user_id = ?""",
                       (sourceid, targetid))
        return cursor.fetchall()

    def getRatingDetail(self, sourcenick, targetnick):
        cursor = self.db.cursor()
        sourcenick = sourcenick.replace('|','||').replace('_','|_').replace('%','|%')
        targetnick = targetnick.replace('|','||').replace('_','|_').replace('%','|%')
        cursor.execute("""SELECT ratings.created_at, ratings.rating, ratings.notes
                          FROM ratings, users, users as users2 WHERE
                          users.nick LIKE ? ESCAPE '|' AND
                          users2.nick LIKE ? ESCAPE '|' AND
                          ratings.rater_user_id = users.id AND
                          ratings.rated_user_id = users2.id""",
                       (sourcenick, targetnick))
        return cursor.fetchall()

    def getConnections(self, nick):
        cursor = self.db.cursor()
        nick = nick.replace('|','||').replace('_','|_').replace('%','|%')
        cursor.execute("""SELECT * FROM users, ratings
                          WHERE users.nick LIKE ? ESCAPE '|' AND
                          (ratings.rater_user_id = users.id OR
                          ratings.rated_user_id = users.id)""",
                       (nick,))
        return cursor.fetchall()

    def update_counts(self, sourcenick, sourceid, targetnick, targetid):
        """update rating counts here.
        called after every rate/unrate, to generate totals/counts.

        we need to update target's totalrating, and recv counts,
        and source's sent counts"""
        cursor = self.db.cursor()
        cursor.execute("""SELECT sum(rating) FROM ratings WHERE
                          rated_user_id = ?""",
                       (targetid,))
        target_total = cursor.fetchall()[0][0]
        target_pos_count = len(self.getReceivedRatings(targetnick, sign="> 0"))
        target_neg_count = len(self.getReceivedRatings(targetnick, sign="< 0"))

        source_pos_count = len(self.getSentRatings(sourcenick, sign="> 0"))
        source_neg_count = len(self.getSentRatings(sourcenick, sign="< 0"))

        cursor.execute("""UPDATE users SET total_rating = ?,
                          pos_rating_recv_count = ?,
                          neg_rating_recv_count = ? WHERE
                          id = ?""",
                       (target_total, target_pos_count, target_neg_count,
                        targetid))
        cursor.execute("""UPDATE users SET pos_rating_sent_count = ?,
                          neg_rating_sent_count = ? WHERE
                          id = ?""",
                       (source_pos_count, source_neg_count, sourceid))
        self._commit()

    def rate(self, sourcenick, sourceid, targetnick, targetid,
             rating, replacementflag, notes, targethost=None):
        """targetid is none if target user is new
        oldtotal is none if target user is new
        replacementflag is true if this user is updating a preexisting rating of his
        """
        targetnick_escaped = targetnick.replace('|','||').replace('_','|_').replace('%','|%')
        cursor = self.db.cursor()
        timestamp = time.time()
        if targetid is None:
            cursor.execute("""INSERT INTO users VALUES
                              (NULL, ?, ?, ?, ?, ?, ?, ?, ?)""",
                           (rating, timestamp, 0, 0, 0, 0, targetnick, targethost))
            self._commit()
            cursor.execute("""SELECT id FROM users
                              WHERE nick LIKE ? ESCAPE '|'""", (targetnick_escaped,))
            targetid = cursor.fetchall()[0][0]
        if not replacementflag:
            cursor.execute("""INSERT INTO ratings VALUES
                              (NULL, ?, ?, ?, ?, ?)""",
                           (targetid, sourceid, timestamp, rating, notes))
        else:
            cursor.execute("""UPDATE ratings SET rating = ?, notes = ?, created_at = ?
                              WHERE rated_user_id = ? AND
                              rater_user_id = ?""",
                           (rating, notes, timestamp, targetid, sourceid))
        self._commit()
        self.update_counts(sourcenick, sourceid, targetnick, targetid)

    def unrate(self, sourcenick, sourceid, targetnick, targetid):
        targetnick_escaped = targetnick.replace('|','||').replace('_','|_').replace('%','|%')
        cursor = self.db.cursor()
        cursor.execute("""DELETE FROM ratings
                          WHERE rated_user_id = ? AND
                          rater_user_id = ?""",
                       (targetid, sourceid))
        self._commit()
        connections = self.getConnections(targetnick)
        if len(connections) == 0:
            cursor.execute("""DELETE FROM users
                              WHERE nick LIKE ? ESCAPE '|'""", (targetnick_escaped,))
            self._commit()
        self.update_counts(sourcenick, sourceid, targetnick, targetid)

    def deleteuser(self, userid):
        cursor = self.db.cursor()
        cursor.execute("""DELETE FROM users
                            WHERE id = ?""",
                            (userid,))
        cursor.execute("""DELETE FROM ratings
                            WHERE rated_user_id = ? OR
                            rater_user_id = ?""",
                            (userid, userid,))
        self._commit()

class RatingSystem(callbacks.Plugin):
    """This plugin maintains a rating system among IRC users.
    Use commands 'rate' and 'unrate' to enter/remove your ratings.
    Use command 'getrating' to view a user's total rating and other details.
    """
    threaded = True

    def __init__(self, irc):
        self.__parent = super(RatingSystem, self)
        self.__parent.__init__(irc)
        self.filename = conf.supybot.directories.data.dirize('RatingSystem.db')
        self.db = RatingSystemDB(self.filename)
        self.db.open()

    def die(self):
        self.__parent.die()
        self.db.close()

    def _checkGPGAuth(self, irc, prefix):
        return irc.getCallback('GPG')._ident(prefix)

    def _checkGPGAuthByNick(self, irc, nick):
        return irc.getCallback('GPG')._identByNick(nick)

    def _ratingBoundsCheck(self, rating):
        if rating >= self.registryValue('ratingMin') and \
           rating <= self.registryValue('ratingMax'):
            return True
        return False

    def rate(self, irc, msg, args, nick, rating, notes):
        """<nick> <rating> [<notes>]

        Enters a rating for <nick> in the amount of <rating>. Use optional
        <notes> field to enter any notes you have about this user. <nick>
        must be the user's GPG-registered username, Your previously existing rating,
        if any, will be overwritten.
        """
        if nick.upper() in self.registryValue('blockedNicks'):
            irc.noReply()
            return
        if irc.nested:
            irc.error("This command cannot be used in a nested context.")
            return
        gpgauth = self._checkGPGAuth(irc, msg.prefix)
        if gpgauth is None:
            irc.error("For identification purposes, you must be authenticated "
                      "to use the rating system.")
            return
        userrating = self.db.get(gpgauth['nick'])
        if len(userrating) == 0:
            irc.error("You have to have received some ratings in order to rate "
                      "other users.")
            return
        trust = self._gettrust('nanotube', gpgauth['nick'])
        sumtrust = sum([t for t,n in trust])
        if self.registryValue('requirePositiveRating') and sumtrust < 0:
            irc.error("You do not meet qualifications for entering ratings.")
            return
        if gpgauth['nick'].lower() == nick.lower():
            irc.error("You cannot rate yourself.")
            return
        validratings = range(self.registryValue('ratingMin'),
                             self.registryValue('ratingMax')+1)
        validratings.remove(0)
        if rating not in validratings:
            irc.error("Rating must be in the interval [%s, %s] and cannot be zero." % \
                      (min(validratings), max(validratings)))
            return

        result = "Your rating of %s for user %s has been recorded." % (rating, nick,)

        sourceid = userrating[0][0]
        targetuserdata = self.db.get(nick)
        if len(targetuserdata) == 0:
            targetgpgdata = irc.getCallback('GPG').db.getByNick(nick)
            if len(targetgpgdata) == 0:
                irc.error("User doesn't exist in the Rating or GPG databases. User must be "
                                "GPG-registered to receive ratings.")
                return
            targetid = None
            replacementflag = False
        else:
            targetid = targetuserdata[0][0]
            priorrating = self.db.getExistingRating(sourceid, targetid)
            if len(priorrating) == 0:
                replacementflag = False
            else:
                replacementflag = True
                result = "Your rating for user %s has changed from %s to %s." % \
                        (nick, priorrating[0][4], rating,)
        self.db.rate(gpgauth['nick'], sourceid, nick, targetid, rating,
                     replacementflag, notes)
        if not world.testing:
            if not replacementflag:
                logmsg = "New rating | %s > %s > %s | %s" % (gpgauth['nick'],
                        rating, nick, notes)
            else:
                logmsg = "Rating change | Old rating %s | New rating: %s > %s > %s | %s" % \
                        (priorrating[0][4], gpgauth['nick'], rating, nick, notes,)
            irc.queueMsg(ircmsgs.privmsg("#bitcoin-otc-ratings", logmsg))
        irc.reply("Rating entry successful. %s" % (result,))
    rate = wrap(rate, ['something', 'int', optional('text')])

    def rated(self, irc, msg, args, nick):
        """<nick>

        Get the details about the rating you gave to <nick>, if any.
        """
        gpgauth = self._checkGPGAuth(irc, msg.prefix)
        if gpgauth is not None:
            sourcenick = gpgauth['nick']
        else:
            sourcenick = msg.nick
        data = self.db.getRatingDetail(sourcenick, nick)
        if len(data) == 0:
            irc.reply("You have not yet rated user %s" % (nick,))
            return
        data = data[0]
        irc.reply("You rated user %s on %s, with a rating of %s, and "
                  "supplied these additional notes: %s." % \
                  (nick,
                   time.ctime(data[0]),
                   data[1],
                   data[2]))
    rated = wrap(rated, ['something'])

    def unrate(self, irc, msg, args, nick):
        """<nick>

        Remove your rating for <nick> from the database.
        """
        gpgauth = self._checkGPGAuth(irc, msg.prefix)
        if gpgauth is None:
            irc.error("You must be authenticated to perform this operation.")
            return
        userrating = self.db.get(gpgauth['nick'])
        if len(userrating) == 0:
            irc.error("Your nick does not exist in the Rating database.")
            return
        sourceid = userrating[0][0]
        targetuserdata = self.db.get(nick)
        if len(targetuserdata) == 0:
            irc.error("The target nick does not exist in the database.")
            return
        targetid = targetuserdata[0][0]
        priorrating = self.db.getExistingRating(sourceid, targetid)
        if len(priorrating) == 0:
            irc.error("You have not given this nick a rating previously.")
            return
        self.db.unrate(gpgauth['nick'], sourceid, nick, targetid)
        if not world.testing:
            logmsg = "Rating removed | %s > %s > %s | %s" % (gpgauth['nick'],
                    priorrating[0][4], nick, priorrating[0][5])
            irc.queueMsg(ircmsgs.privmsg("#bitcoin-otc-ratings", logmsg))
        irc.reply("Successfully removed your rating for %s." % nick)
    unrate = wrap(unrate, ['something'])

    def _getrating(self, nick):
        """Get cumulative rating for user. For use from other plugins."""
        data = self.db.get(nick)
        if len(data) == 0:
            return None
        data = data[0]
        return data

    def getrating(self, irc, msg, args, nick):
        """<nick>

        Get rating information for <nick>.
        """
        authhost = self._checkGPGAuthByNick(irc, nick)
        if authhost is not None:
            authstatus = "Currently authenticated from hostmask %s ." % (authhost,)
        else:
            authstatus = "\x02WARNING: Currently not authenticated.\x02"
        data = self.db.get(nick)
        if len(data) == 0:
            irc.reply("This user has not yet been rated. " + authstatus)
            return
        data = data[0]
        
        if authhost is not None and authhost.split('!')[0].upper() != data[7].upper():
            authstatus += " CAUTION: irc nick differs from otc registered nick."

        irc.reply("%s User %s, rated since %s. "
                  "Cumulative rating %s, from %s total ratings. "
                  "Received ratings: %s positive, %s negative. "
                  "Sent ratings: %s positive, %s negative. "
                  "Details: %s" % \
                  (authstatus,
                   data[7],
                   time.ctime(data[2]),
                   data[1],
                   int(data[3]) + int(data[4]),
                   data[3],
                   data[4],
                   data[5],
                   data[6],
                   "http://b-otc.com/vrd?nick=%s" % (utils.web.urlquote(data[7]),)))
    getrating = wrap(getrating, ['something'])

    def _gettrust(self, sourcenick, destnick):
        """Get a list of tuples for l1,l2... trust levels and number of associated
        connections. To be used from other plugins for trust checks.
        """
        result = []
        l1 = self.db.getRatingDetail(sourcenick, destnick)
        if len(l1) > 0:
            result.append((l1[0][1], 1,))
        else:
            result.append((0, 0,))
        l2 = self.db.getLevel2Ratings(sourcenick, destnick)
        if l2[0] is None:
            result.append((0,0,))
        else:
            result.append(l2)
        return result

    def gettrust(self, irc, msg, args, sourcenick, destnick):
        """[<sourcenick>] <destnick>
        
        Get trust paths for <destnick>, starting from <sourcenick>.
        If <sourcenick> is not supplied, your own nick is used as the source.
        See http://wiki.bitcoin-otc.com/wiki/OTC_Rating_System#Notes_about_gettrust
        """
        if sourcenick == '' or destnick == '':
			cmd = str(msg).rstrip('\r\n')
			cmd = re.sub(r':.*?:', '', cmd)
			irc.error("You provided an empty string as argument. Your command: %s." % (cmd,))
			return
        gpgauth = self._checkGPGAuth(irc, msg.prefix)
        if gpgauth is not None:
            sn = gpgauth['nick']
        else:
            sn = msg.nick
        if destnick is None:
            destnick = sourcenick
            sourcenick = sn

        authhost = self._checkGPGAuthByNick(irc, destnick)
        if authhost is not None:
            authstatus = "Currently authenticated from hostmask %s." % (authhost,)
        else:
            authstatus = "\x02WARNING: Currently not authenticated.\x02"
        if authhost is not None and authhost.split('!')[0].upper() != destnick.upper():
            authstatus += " \x02CAUTION: irc nick differs from otc registered nick.\x02"

        rs = self._getrating(destnick)
        if rs is not None:
            rs = time.ctime(rs[2])
        else:
            rs = 'never'
        trust = self._gettrust(sourcenick, destnick)
        irc.reply("%s Trust relationship from user %s to user %s: "
                        "Level 1: %s, Level 2: %s via %s connections. "
                        "Graph: http://b-otc.com/stg?source=%s&dest=%s | "
                        "WoT data: http://b-otc.com/vrd?nick=%s | "
                        "Rated since: %s" % \
                        (authstatus, sourcenick, destnick,
                        trust[0][0], trust[1][0], trust[1][1],
                        utils.web.urlquote(sourcenick), utils.web.urlquote(destnick),
                        utils.web.urlquote(destnick), rs))
    gettrust = wrap(gettrust, ['anything', optional('anything')])

    def deleteuser(self, irc, msg, args, nick):
        """<nick>
        
        Delete user, and all his sent/received ratings, from the database.
        
        Requires owner privileges.
        """
        data = self.db.get(nick)
        if len(data) == 0:
            irc.error("No such user in the database.")
            return
        self.db.deleteuser(data[0][0])
        irc.reply("Successfully deleted user %s, id %s" % (nick, data[0][0],))
    deleteuser = wrap(deleteuser, ['owner','something'])


Class = RatingSystem


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
###
# Copyright (c) 2010, Daniel Folkinshteyn
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.test import *

import sqlite3
import time

class RatingSystemTestCase(PluginTestCase):
    plugins = ('RatingSystem','GPG')

    def setUp(self):
        PluginTestCase.setUp(self)
        # pre-seed the db with a rating for nanotube
        cb = self.irc.getCallback('RatingSystem')
        cursor = cb.db.db.cursor()
        cursor.execute("""INSERT INTO users VALUES
                          (NULL, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (10, time.time(), 1, 0, 0, 0, 'nanotube','stuff/somecloak'))
        cb.db.db.commit()

        #preseed the GPG db with a GPG registration and auth for nanotube
        gpg = self.irc.getCallback('GPG')
        gpg.db.register('AAAAAAAAAAAAAAA1', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA1', None,
                    time.time(), 'nanotube')
        gpg.authed_users['nanotube!stuff@stuff/somecloak'] = {'nick':'nanotube'}
        gpg.db.register('AAAAAAAAAAAAAAA2', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA2', None,
                    time.time(), 'registeredguy')
        gpg.db.register('AAAAAAAAAAAAAAA3', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA3', None,
                    time.time(), 'authedguy')
        gpg.authed_users['authedguy!stuff@123.345.234.34'] = {'nick':'authedguy'}
        gpg.db.register('AAAAAAAAAAAAAAA4', 'AAAAAAAAAAAAAAAAAAA1AAAAAAAAAAAAAAA4', None,
                    time.time(), 'authedguy2')
        gpg.authed_users['authedguy2!stuff@123.345.234.34'] = {'nick':'authedguy2'}

    def testRate(self):
        self.assertError('rate someguy 4') # not authenticated
        try:
            origuser = self.prefix
            self.prefix = 'nanotube!stuff@stuff/somecloak'
            self.assertError('rate nanotube 10') #can't self-rate
            self.assertError('rate nanOtube 10') #can't self-rate
            self.assertError('rate unknownguy 4') #user not in db and not authed
            self.assertRegexp('rate registeredguy 4', 'rating of 4 for user registeredguy has been recorded')
            self.assertRegexp('getrating registeredguy', 'Cumulative rating 4.*vrd\?nick=registeredguy')
            self.assertRegexp('getrating registeredguy', '1 total ratings')
            self.assertRegexp('rate registeredguy 6', 'changed from 4 to 6')
            self.assertRegexp('getrating registeredguy', 'Currently not authenticated.*Cumulative rating 6')
            self.assertRegexp('getrating registeredguy', '1 total ratings')
            self.assertRegexp('getrating nanotube', 'Sent ratings: 1 positive')
            self.assertError('rate registeredguy 0') # rating must be in bounds, and no zeros
            self.assertError('rate registeredguy -20')
            self.assertError('rate registeredguy 30')
            self.assertNotError('rate registeredguy -10')
            self.assertNotError('rate authedguy 5')
            self.assertRegexp('getrating autheDguy', 'Currently authenticated.*Cumulative rating 5')
            self.assertNotError('rate authedguy2 -1')
            self.assertRegexp('getrating nanotube', 'Sent ratings: 1 positive, 2 negative')
            self.assertRegexp('getrating registeredguy', 'Cumulative rating -10')
            self.prefix = 'authedguy!stuff@123.345.234.34'
            self.assertNotError('rate registeredguy 9')
            self.assertRegexp('getrating registeredguy', 'Cumulative rating -1')
            self.prefix = 'registeredguy!stuff@stuff/somecloak'
            self.assertError('rate nanotube 2') # unauthed, can't rate
            self.prefix = 'authedguy2!stuff@123.345.234.34'
            self.assertError('rate nanotube 2') # rated -1, can't rate
            self.prefix = 'nanotube!stuff@stuff/somecloak'
            self.assertNotError('unrate registeredguy')
            self.assertRegexp('getrating registeredguy', 'Cumulative rating 9')
            self.assertRegexp('getrating nanotube', 'Sent ratings.*1 negative')
            self.assertNotError('rate registeredGUY 5')
            self.assertRegexp('getrating registeredguy', 'Cumulative rating 14')
            self.assertRegexp('rated nobody', 'not yet rated')
            self.assertRegexp('rated registeredguy', 'You rated user registeredguy .* with a rating of 5')
        finally:
            self.prefix = origuser

    def testUnrate(self):
        try:
            origuser = self.prefix
            self.prefix = 'nanotube!stuff@stuff/somecloak'
            self.assertError('unrate someguy') #haven't rated him before
            self.assertError('unrate registeredguy') #haven't rated him before
            self.assertNotError('rate registeredguy 4')
            self.assertRegexp('getrating registeredguy', 'Cumulative rating 4')
            self.assertNotError('unrate regISTEredguy')
            self.assertRegexp('getrating registeredguy', 'not yet been rated') # guy should be gone, having no connections.
        finally:
            self.prefix = origuser

    def testGetTrust(self):
        try:
            origuser = self.prefix
            self.prefix = 'nanotube!stuff@stuff/somecloak'
            self.assertNotError('rate authedguy 5')
            self.prefix = 'authedguy!stuff@123.345.234.34'
            self.assertNotError('rate authedguy2 3')
            self.assertRegexp('gettrust nanotube authedguy2', 
                        'Level 2: 3 via 1 connections')
            self.assertNotError('rate authedguy2 7')
            self.assertRegexp('gettrust nanotube authedguy2', 
                        'Level 2: 5 via 1 connections')
            self.prefix = 'nanotube!stuff@stuff/somecloak'
            self.assertRegexp('gettrust authedguy2', 
                        'Level 1: 0, Level 2: 5 via 1 connections')
            self.assertNotError('rate authedguy -1')
            self.assertNotError('rate authedguy2 7')
            self.assertRegexp('gettrust authedguy2', 
                        'Level 1: 7, Level 2: 0 via 1 connections')
            self.assertNotError('rate authedguy 3')
            self.prefix = 'authedguy!stuff@123.345.234.34'
            self.assertNotError('rate authedguy2 -10')
            self.assertRegexp('gettrust nanotube authedguy2', 
                        'Level 2: -3 via 1 connections')
            self.assertRegexp('gettrust nobody nobody2', 'Level 1: 0, Level 2: 0 via 0 connections')
            self.prefix = 'randomguy!stuff@stuff/somecloak'
            self.assertRegexp('gettrust authedguy2', 'Level 1: 0, Level 2: 0 via 0 connections')
        finally:
            self.prefix = origuser

    def testDeleteUser(self):
        try:
            origuser = self.prefix
            self.prefix = 'nanotube!stuff@stuff/somecloak'
            self.assertNotError('rate registeredguy 4')
            self.assertRegexp('getrating registeredguy', 'Cumulative rating 4')
            self.assertNotError('deleteuser registeredGUy')
            self.assertRegexp('getrating registeredguy', 'not yet been rated') # guy should be gone
        finally:
            self.prefix = origuser


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
