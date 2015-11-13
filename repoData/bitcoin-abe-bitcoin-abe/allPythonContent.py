__FILENAME__ = abe
#!/usr/bin/env python
# Copyright(C) 2011,2012,2013,2014 by Abe developers.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

import sys
import os
import optparse
import re
from cgi import escape
import posixpath
import wsgiref.util
import time
import calendar
import math
import logging
import json

import version
import DataStore
import readconf

# bitcointools -- modified deserialize.py to return raw transaction
import deserialize
import util  # Added functions.
import base58

__version__ = version.__version__

ABE_APPNAME = "Abe"
ABE_VERSION = __version__
ABE_URL = 'https://github.com/bitcoin-abe/bitcoin-abe'

COPYRIGHT_YEARS = '2011'
COPYRIGHT = "Abe developers"
COPYRIGHT_URL = 'https://github.com/bitcoin-abe'

DONATIONS_BTC = '1PWC7PNHL1SgvZaN7xEtygenKjWobWsCuf'
DONATIONS_NMC = 'NJ3MSELK1cWnqUa6xhF2wUYAnz3RSrWXcK'

TIME1970 = time.strptime('1970-01-01','%Y-%m-%d')
EPOCH1970 = calendar.timegm(TIME1970)

# Abe-generated content should all be valid HTML and XHTML fragments.
# Configurable templates may contain either.  HTML seems better supported
# under Internet Explorer.
DEFAULT_CONTENT_TYPE = "text/html; charset=utf-8"
DEFAULT_HOMEPAGE = "chains";
DEFAULT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <link rel="stylesheet" type="text/css"
     href="%(dotdot)s%(STATIC_PATH)sabe.css" />
    <link rel="shortcut icon" href="%(dotdot)s%(STATIC_PATH)sfavicon.ico" />
    <title>%(title)s</title>
</head>
<body>
    <h1><a href="%(dotdot)s%(HOMEPAGE)s"><img
     src="%(dotdot)s%(STATIC_PATH)slogo32.png" alt="Abe logo" /></a> %(h1)s
    </h1>
    %(body)s
    <p><a href="%(dotdot)sq">API</a> (machine-readable pages)</p>
    <p style="font-size: smaller">
        <span style="font-style: italic">
            Powered by <a href="%(ABE_URL)s">%(APPNAME)s</a>
        </span>
        %(download)s
        Tips appreciated!
        <a href="%(dotdot)saddress/%(DONATIONS_BTC)s">BTC</a>
        <a href="%(dotdot)saddress/%(DONATIONS_NMC)s">NMC</a>
    </p>
</body>
</html>
"""

DEFAULT_LOG_FORMAT = "%(message)s"

DEFAULT_DECIMALS = 8

# It is fun to change "6" to "3" and search lots of addresses.
ADDR_PREFIX_RE = re.compile('[1-9A-HJ-NP-Za-km-z]{6,}\\Z')
HEIGHT_RE = re.compile('(?:0|[1-9][0-9]*)\\Z')
HASH_PREFIX_RE = re.compile('[0-9a-fA-F]{0,64}\\Z')
HASH_PREFIX_MIN = 6

NETHASH_HEADER = """\
blockNumber:          height of last block in interval + 1
time:                 block time in seconds since 0h00 1 Jan 1970 UTC
target:               decimal target at blockNumber
avgTargetSinceLast:   harmonic mean of target over interval
difficulty:           difficulty at blockNumber
hashesToWin:          expected number of hashes needed to solve a block at this difficulty
avgIntervalSinceLast: interval seconds divided by blocks
netHashPerSecond:     estimated network hash rate over interval

Statistical values are approximate and differ slightly from http://blockexplorer.com/q/nethash.

/chain/CHAIN/q/nethash[/INTERVAL[/START[/STOP]]]
Default INTERVAL=144, START=0, STOP=infinity.
Negative values back from the last block.
Append ?format=json to URL for headerless, JSON output.

blockNumber,time,target,avgTargetSinceLast,difficulty,hashesToWin,avgIntervalSinceLast,netHashPerSecond
START DATA
"""

NETHASH_SVG_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:abe="http://abe.bit/abe"
     viewBox="0 0 300 200"
     preserveAspectRatio="none"
     onload="Abe.draw(this)">

  <style>
    #chart polyline {
        stroke-width: 0.1%%;
        fill-opacity: 0;
        stroke-opacity: 0.5;
  </style>

  <script type="application/ecmascript"
          xlink:href="%(dotdot)s%(STATIC_PATH)snethash.js"/>

  <g id="chart">
    <polyline abe:window="1d" style="stroke: red;"/>
    <polyline abe:window="3d" style="stroke: orange;"/>
    <polyline abe:window="7d" style="stroke: yellow;"/>
    <polyline abe:window="14d" style="stroke: green;"/>
    <polyline abe:window="30d" style="stroke: blue;"/>

%(body)s

  </g>
</svg>
"""

# How many addresses to accept in /unspent/ADDR|ADDR|...
MAX_UNSPENT_ADDRESSES = 200

def make_store(args):
    store = DataStore.new(args)
    if (not args.no_load):
        store.catch_up()
    return store

class NoSuchChainError(Exception):
    """Thrown when a chain lookup fails"""

class PageNotFound(Exception):
    """Thrown when code wants to return 404 Not Found"""

class Redirect(Exception):
    """Thrown when code wants to redirect the request"""

class Streamed(Exception):
    """Thrown when code has written the document to the callable
    returned by start_response."""

class Abe:
    def __init__(abe, store, args):
        abe.store = store
        abe.args = args
        abe.htdocs = args.document_root or find_htdocs()
        abe.static_path = '' if args.static_path is None else args.static_path
        abe.template_vars = args.template_vars.copy()
        abe.template_vars['STATIC_PATH'] = (
            abe.template_vars.get('STATIC_PATH', abe.static_path))
        abe.template = flatten(args.template)
        abe.debug = args.debug
        abe.log = logging.getLogger(__name__)
        abe.log.info('Abe initialized.')
        abe.home = str(abe.template_vars.get("HOMEPAGE", DEFAULT_HOMEPAGE))
        if not args.auto_agpl:
            abe.template_vars['download'] = (
                abe.template_vars.get('download', ''))
        abe.base_url = args.base_url
        abe.address_history_rows_max = int(
            args.address_history_rows_max or 1000)

        if args.shortlink_type is None:
            abe.shortlink_type = ("firstbits" if store.use_firstbits else
                                  "non-firstbits")
        else:
            abe.shortlink_type = args.shortlink_type
            if abe.shortlink_type != "firstbits":
                abe.shortlink_type = int(abe.shortlink_type)
                if abe.shortlink_type < 2:
                    raise ValueError("shortlink-type: 2 character minimum")
            elif not store.use_firstbits:
                abe.shortlink_type = "non-firstbits"
                abe.log.warning("Ignoring shortlink-type=firstbits since" +
                                " the database does not support it.")
        if abe.shortlink_type == "non-firstbits":
            abe.shortlink_type = 10

    def __call__(abe, env, start_response):
        import urlparse

        status = '200 OK'
        page = {
            "title": [escape(ABE_APPNAME), " ", ABE_VERSION],
            "body": [],
            "env": env,
            "params": {},
            "dotdot": "../" * (env['PATH_INFO'].count('/') - 1),
            "start_response": start_response,
            "content_type": str(abe.template_vars['CONTENT_TYPE']),
            "template": abe.template,
            "chain": None,
            }
        if 'QUERY_STRING' in env:
            page['params'] = urlparse.parse_qs(env['QUERY_STRING'])

        if abe.fix_path_info(env):
            abe.log.debug("fixed path_info")
            return redirect(page)

        cmd = wsgiref.util.shift_path_info(env)
        handler = abe.get_handler(cmd)

        tvars = abe.template_vars.copy()
        tvars['dotdot'] = page['dotdot']
        page['template_vars'] = tvars

        try:
            if handler is None:
                return abe.serve_static(cmd + env['PATH_INFO'], start_response)

            if (not abe.args.no_load):
                # Always be up-to-date, even if we means having to wait
                # for a response!  XXX Could use threads, timers, or a
                # cron job.
                abe.store.catch_up()

            handler(page)
        except PageNotFound:
            status = '404 Not Found'
            page['body'] = ['<p class="error">Sorry, ', env['SCRIPT_NAME'],
                            env['PATH_INFO'],
                            ' does not exist on this server.</p>']
        except NoSuchChainError, e:
            page['body'] += [
                '<p class="error">'
                'Sorry, I don\'t know about that chain!</p>\n']
        except Redirect:
            return redirect(page)
        except Streamed:
            return ''
        except Exception:
            abe.store.rollback()
            raise

        abe.store.rollback()  # Close implicitly opened transaction.

        start_response(status, [('Content-type', page['content_type']),
                                ('Cache-Control', 'max-age=30')])

        tvars['title'] = flatten(page['title'])
        tvars['h1'] = flatten(page.get('h1') or page['title'])
        tvars['body'] = flatten(page['body'])
        if abe.args.auto_agpl:
            tvars['download'] = (
                ' <a href="' + page['dotdot'] + 'download">Source</a>')

        content = page['template'] % tvars
        if isinstance(content, unicode):
            content = content.encode('UTF-8')
        return content

    def get_handler(abe, cmd):
        return getattr(abe, 'handle_' + cmd, None)

    def handle_chains(abe, page):
        page['title'] = ABE_APPNAME + ' Search'
        body = page['body']
        body += [
            abe.search_form(page),
            '<table>\n',
            '<tr><th>Currency</th><th>Code</th><th>Block</th><th>Time</th>',
            '<th>Started</th><th>Age (days)</th><th>Coins Created</th>',
            '<th>Avg Coin Age</th><th>',
            '% <a href="https://en.bitcoin.it/wiki/Bitcoin_Days_Destroyed">',
            'CoinDD</a></th>',
            '</tr>\n']
        now = time.time() - EPOCH1970

        rows = abe.store.selectall("""
            SELECT c.chain_name, b.block_height, b.block_nTime, b.block_hash,
                   b.block_total_seconds, b.block_total_satoshis,
                   b.block_satoshi_seconds,
                   b.block_total_ss
              FROM chain c
              JOIN block b ON (c.chain_last_block_id = b.block_id)
             ORDER BY c.chain_name
        """)
        for row in rows:
            name = row[0]
            chain = abe.store.get_chain_by_name(name)
            if chain is None:
                abe.log.warning("Store does not know chain: %s", name)
                continue

            body += [
                '<tr><td><a href="chain/', escape(name), '">',
                escape(name), '</a></td><td>', escape(chain.code3), '</td>']

            if row[1] is not None:
                (height, nTime, hash) = (
                    int(row[1]), int(row[2]), abe.store.hashout_hex(row[3]))

                body += [
                    '<td><a href="block/', hash, '">', height, '</a></td>',
                    '<td>', format_time(nTime), '</td>']

                if row[6] is not None and row[7] is not None:
                    (seconds, satoshis, ss, total_ss) = (
                        int(row[4]), int(row[5]), int(row[6]), int(row[7]))

                    started = nTime - seconds
                    chain_age = now - started
                    since_block = now - nTime

                    if satoshis == 0:
                        avg_age = '&nbsp;'
                    else:
                        avg_age = '%5g' % ((float(ss) / satoshis + since_block)
                                           / 86400.0)

                    if chain_age <= 0:
                        percent_destroyed = '&nbsp;'
                    else:
                        more = since_block * satoshis
                        denominator = total_ss + more
                        if denominator <= 0:
                            percent_destroyed = '&nbsp;'
                        else:
                            percent_destroyed = '%5g%%' % (
                                100.0 - (100.0 * (ss + more) / denominator))

                    body += [
                        '<td>', format_time(started)[:10], '</td>',
                        '<td>', '%5g' % (chain_age / 86400.0), '</td>',
                        '<td>', format_satoshis(satoshis, chain), '</td>',
                        '<td>', avg_age, '</td>',
                        '<td>', percent_destroyed, '</td>']

            body += ['</tr>\n']
        body += ['</table>\n']
        if len(rows) == 0:
            body += ['<p>No block data found.</p>\n']

    def chain_lookup_by_name(abe, symbol):
        if symbol is None:
            ret = abe.get_default_chain()
        else:
            ret = abe.store.get_chain_by_name(symbol)
        if ret is None:
            raise NoSuchChainError()
        return ret

    def get_default_chain(abe):
        return abe.store.get_default_chain()

    def format_addresses(abe, data, dotdot, chain):
        if data['binaddr'] is None:
            return 'Unknown'
        if 'subbinaddr' in data:
            # Multisig or known P2SH.
            ret = [hash_to_address_link(chain.script_addr_vers, data['binaddr'], dotdot, text='Escrow'),
                   ' ', data['required_signatures'], ' of']
            for binaddr in data['subbinaddr']:
                ret += [' ', hash_to_address_link(data['address_version'], binaddr, dotdot, 10)]
            return ret
        return hash_to_address_link(data['address_version'], data['binaddr'], dotdot)

    def call_handler(abe, page, cmd):
        handler = abe.get_handler(cmd)
        if handler is None:
            raise PageNotFound()
        handler(page)

    def handle_chain(abe, page):
        symbol = wsgiref.util.shift_path_info(page['env'])
        chain = abe.chain_lookup_by_name(symbol)
        page['chain'] = chain

        cmd = wsgiref.util.shift_path_info(page['env'])
        if cmd == '':
            page['env']['SCRIPT_NAME'] = page['env']['SCRIPT_NAME'][:-1]
            raise Redirect()
        if cmd == 'chain' or cmd == 'chains':
            raise PageNotFound()
        if cmd is not None:
            abe.call_handler(page, cmd)
            return

        page['title'] = chain.name

        body = page['body']
        body += abe.search_form(page)

        count = get_int_param(page, 'count') or 20
        hi = get_int_param(page, 'hi')
        orig_hi = hi

        if hi is None:
            row = abe.store.selectrow("""
                SELECT b.block_height
                  FROM block b
                  JOIN chain c ON (c.chain_last_block_id = b.block_id)
                 WHERE c.chain_id = ?
            """, (chain.id,))
            if row:
                hi = row[0]
        if hi is None:
            if orig_hi is None and count > 0:
                body += ['<p>I have no blocks in this chain.</p>']
            else:
                body += ['<p class="error">'
                         'The requested range contains no blocks.</p>\n']
            return

        rows = abe.store.selectall("""
            SELECT b.block_hash, b.block_height, b.block_nTime, b.block_num_tx,
                   b.block_nBits, b.block_value_out,
                   b.block_total_seconds, b.block_satoshi_seconds,
                   b.block_total_satoshis, b.block_ss_destroyed,
                   b.block_total_ss
              FROM block b
              JOIN chain_candidate cc ON (b.block_id = cc.block_id)
             WHERE cc.chain_id = ?
               AND cc.block_height BETWEEN ? AND ?
               AND cc.in_longest = 1
             ORDER BY cc.block_height DESC LIMIT ?
        """, (chain.id, hi - count + 1, hi, count))

        if hi is None:
            hi = int(rows[0][1])
        basename = os.path.basename(page['env']['PATH_INFO'])

        nav = ['<a href="',
               basename, '?count=', str(count), '">&lt;&lt;</a>']
        nav += [' <a href="', basename, '?hi=', str(hi + count),
                 '&amp;count=', str(count), '">&lt;</a>']
        nav += [' ', '&gt;']
        if hi >= count:
            nav[-1] = ['<a href="', basename, '?hi=', str(hi - count),
                        '&amp;count=', str(count), '">', nav[-1], '</a>']
        nav += [' ', '&gt;&gt;']
        if hi != count - 1:
            nav[-1] = ['<a href="', basename, '?hi=', str(count - 1),
                        '&amp;count=', str(count), '">', nav[-1], '</a>']
        for c in (20, 50, 100, 500, 2016):
            nav += [' ']
            if c != count:
                nav += ['<a href="', basename, '?count=', str(c)]
                if hi is not None:
                    nav += ['&amp;hi=', str(max(hi, c - 1))]
                nav += ['">']
            nav += [' ', str(c)]
            if c != count:
                nav += ['</a>']

        nav += [' <a href="', page['dotdot'], '">Search</a>']

        extra = False
        #extra = True
        body += ['<p>', nav, '</p>\n',
                 '<table><tr><th>Block</th><th>Approx. Time</th>',
                 '<th>Transactions</th><th>Value Out</th>',
                 '<th>Difficulty</th><th>Outstanding</th>',
                 '<th>Average Age</th><th>Chain Age</th>',
                 '<th>% ',
                 '<a href="https://en.bitcoin.it/wiki/Bitcoin_Days_Destroyed">',
                 'CoinDD</a></th>',
                 ['<th>Satoshi-seconds</th>',
                  '<th>Total ss</th>']
                 if extra else '',
                 '</tr>\n']
        for row in rows:
            (hash, height, nTime, num_tx, nBits, value_out,
             seconds, ss, satoshis, destroyed, total_ss) = row
            nTime = int(nTime)
            value_out = int(value_out)
            seconds = int(seconds)
            satoshis = int(satoshis)
            ss = int(ss)
            total_ss = int(total_ss)

            if satoshis == 0:
                avg_age = '&nbsp;'
            else:
                avg_age = '%5g' % (ss / satoshis / 86400.0)

            if total_ss <= 0:
                percent_destroyed = '&nbsp;'
            else:
                percent_destroyed = '%5g%%' % (100.0 - (100.0 * ss / total_ss))

            body += [
                '<tr><td><a href="', page['dotdot'], 'block/',
                abe.store.hashout_hex(hash),
                '">', height, '</a>'
                '</td><td>', format_time(int(nTime)),
                '</td><td>', num_tx,
                '</td><td>', format_satoshis(value_out, chain),
                '</td><td>', util.calculate_difficulty(int(nBits)),
                '</td><td>', format_satoshis(satoshis, chain),
                '</td><td>', avg_age,
                '</td><td>', '%5g' % (seconds / 86400.0),
                '</td><td>', percent_destroyed,
                ['</td><td>', '%8g' % ss,
                 '</td><td>', '%8g' % total_ss] if extra else '',
                '</td></tr>\n']

        body += ['</table>\n<p>', nav, '</p>\n']

    def _show_block(abe, page, dotdotblock, chain, **kwargs):
        body = page['body']

        try:
            b = abe.store.export_block(chain, **kwargs)
        except DataStore.MalformedHash:
            body += ['<p class="error">Not in correct format.</p>']
            return

        if b is None:
            body += ['<p class="error">Block not found.</p>']
            return

        in_longest = False
        for cc in b['chain_candidates']:
            if chain is None:
                chain = cc['chain']
            if chain.id == cc['chain'].id:
                in_longest = cc['in_longest']

        if in_longest:
            page['title'] = [escape(chain.name), ' ', b['height']]
            page['h1'] = ['<a href="', page['dotdot'], 'chain/',
                          escape(chain.name), '?hi=', b['height'], '">',
                          escape(chain.name), '</a> ', b['height']]
        else:
            page['title'] = ['Block ', b['hash'][:4], '...', b['hash'][-10:]]

        body += abe.short_link(page, 'b/' + block_shortlink(b['hash']))

        is_stake_chain = chain.has_feature('nvc_proof_of_stake')
        is_stake_block = is_stake_chain and b['is_proof_of_stake']

        body += ['<p>']
        if is_stake_chain:
            body += [
                'Proof of Stake' if is_stake_block else 'Proof of Work',
                ': ',
                format_satoshis(b['generated'], chain), ' coins generated<br />\n']
        body += ['Hash: ', b['hash'], '<br />\n']

        if b['hashPrev'] is not None:
            body += ['Previous Block: <a href="', dotdotblock,
                     b['hashPrev'], '">', b['hashPrev'], '</a><br />\n']
        if b['next_block_hashes']:
            body += ['Next Block: ']
        for hash in b['next_block_hashes']:
            body += ['<a href="', dotdotblock, hash, '">', hash, '</a><br />\n']

        body += [
            ['Height: ', b['height'], '<br />\n']
            if b['height'] is not None else '',

            'Version: ', b['version'], '<br />\n',
            'Transaction Merkle Root: ', b['hashMerkleRoot'], '<br />\n',
            'Time: ', b['nTime'], ' (', format_time(b['nTime']), ')<br />\n',
            'Difficulty: ', format_difficulty(util.calculate_difficulty(b['nBits'])),
            ' (Bits: %x)' % (b['nBits'],), '<br />\n',

            ['Cumulative Difficulty: ', format_difficulty(
                    util.work_to_difficulty(b['chain_work'])), '<br />\n']
            if b['chain_work'] is not None else '',

            'Nonce: ', b['nNonce'], '<br />\n',
            'Transactions: ', len(b['transactions']), '<br />\n',
            'Value out: ', format_satoshis(b['value_out'], chain), '<br />\n',
            'Transaction Fees: ', format_satoshis(b['fees'], chain), '<br />\n',

            ['Average Coin Age: %6g' % (b['satoshi_seconds'] / 86400.0 / b['chain_satoshis'],),
             ' days<br />\n']
            if b['chain_satoshis'] and (b['satoshi_seconds'] is not None) else '',

            '' if b['satoshis_destroyed'] is None else
            ['Coin-days Destroyed: ',
             format_satoshis(b['satoshis_destroyed'] / 86400.0, chain), '<br />\n'],

            ['Cumulative Coin-days Destroyed: %6g%%<br />\n' %
             (100 * (1 - float(b['satoshi_seconds']) / b['chain_satoshi_seconds']),)]
            if b['chain_satoshi_seconds'] else '',

            ['sat=',b['chain_satoshis'],';sec=',seconds,';ss=',b['satoshi_seconds'],
             ';total_ss=',b['chain_satoshi_seconds'],';destroyed=',b['satoshis_destroyed']]
            if abe.debug else '',

            '</p>\n']

        body += ['<h3>Transactions</h3>\n']

        body += ['<table><tr><th>Transaction</th><th>Fee</th>'
                 '<th>Size (kB)</th><th>From (amount)</th><th>To (amount)</th>'
                 '</tr>\n']

        for tx in b['transactions']:
            body += ['<tr><td><a href="../tx/' + tx['hash'] + '">',
                     tx['hash'][:10], '...</a>'
                     '</td><td>', format_satoshis(tx['fees'], chain),
                     '</td><td>', tx['size'] / 1000.0,
                     '</td><td>']

            if tx is b['transactions'][0]:
                body += [
                    'POS ' if is_stake_block else '',
                    'Generation: ', format_satoshis(b['generated'], chain), ' + ',
                    format_satoshis(b['fees'], chain), ' total fees']
            else:
                for txin in tx['in']:
                    body += [abe.format_addresses(txin, page['dotdot'], chain), ': ',
                             format_satoshis(txin['value'], chain), '<br />']

            body += ['</td><td>']
            for txout in tx['out']:
                if is_stake_block:
                    if tx is b['transactions'][0]:
                        assert txout['value'] == 0
                        assert len(tx['out']) == 1
                        body += [
                            format_satoshis(b['proof_of_stake_generated'], chain),
                            ' included in the following transaction']
                        continue
                    if txout['value'] == 0:
                        continue

                body += [abe.format_addresses(txout, page['dotdot'], chain), ': ',
                         format_satoshis(txout['value'], chain), '<br />']

            body += ['</td></tr>\n']
        body += '</table>\n'

    def handle_block(abe, page):
        block_hash = wsgiref.util.shift_path_info(page['env'])
        if block_hash in (None, '') or page['env']['PATH_INFO'] != '':
            raise PageNotFound()

        block_hash = block_hash.lower()  # Case-insensitive, BBE compatible
        page['title'] = 'Block'

        if not is_hash_prefix(block_hash):
            page['body'] += ['<p class="error">Not a valid block hash.</p>']
            return

        abe._show_block(page, '', None, block_hash=block_hash)

    def handle_tx(abe, page):
        tx_hash = wsgiref.util.shift_path_info(page['env'])
        if tx_hash in (None, '') or page['env']['PATH_INFO'] != '':
            raise PageNotFound()

        tx_hash = tx_hash.lower()  # Case-insensitive, BBE compatible
        page['title'] = ['Transaction ', tx_hash[:10], '...', tx_hash[-4:]]
        body = page['body']

        if not is_hash_prefix(tx_hash):
            body += ['<p class="error">Not a valid transaction hash.</p>']
            return

        try:
            # XXX Should pass chain to export_tx to help parse scripts.
            tx = abe.store.export_tx(tx_hash = tx_hash, format = 'browser')
        except DataStore.MalformedHash:
            body += ['<p class="error">Not in correct format.</p>']
            return

        if tx is None:
            body += ['<p class="error">Transaction not found.</p>']
            return

        return abe.show_tx(page, tx)

    def show_tx(abe, page, tx):
        body = page['body']

        def row_to_html(row, this_ch, other_ch, no_link_text):
            body = page['body']
            body += [
                '<tr>\n',
                '<td><a name="', this_ch, row['pos'], '">', row['pos'],
                '</a></td>\n<td>']
            if row['o_hash'] is None:
                body += [no_link_text]
            else:
                body += [
                    '<a href="', row['o_hash'], '#', other_ch, row['o_pos'],
                    '">', row['o_hash'][:10], '...:', row['o_pos'], '</a>']
            body += [
                '</td>\n',
                '<td>', format_satoshis(row['value'], chain), '</td>\n',
                '<td>', abe.format_addresses(row, '../', chain), '</td>\n']
            if row['binscript'] is not None:
                body += ['<td>', escape(decode_script(row['binscript'])), '</td>\n']
            body += ['</tr>\n']

        body += abe.short_link(page, 't/' + hexb58(tx['hash'][:14]))
        body += ['<p>Hash: ', tx['hash'], '<br />\n']
        chain = None
        is_coinbase = None

        for tx_cc in tx['chain_candidates']:
            if chain is None:
                chain = tx_cc['chain']
                is_coinbase = (tx_cc['tx_pos'] == 0)
            elif tx_cc['chain'].id != chain.id:
                abe.log.warning('Transaction ' + tx['hash'] + ' in multiple chains: '
                             + tx_cc['chain'].id + ', ' + chain.id)

            blk_hash = tx_cc['block_hash']
            body += [
                'Appeared in <a href="../block/', blk_hash, '">',
                escape(tx_cc['chain'].name), ' ',
                tx_cc['block_height'] if tx_cc['in_longest'] else [blk_hash[:10], '...', blk_hash[-4:]],
                '</a> (', format_time(tx_cc['block_nTime']), ')<br />\n']

        if chain is None:
            abe.log.warning('Assuming default chain for Transaction ' + tx['hash'])
            chain = abe.get_default_chain()

        body += [
            'Number of inputs: ', len(tx['in']),
            ' (<a href="#inputs">Jump to inputs</a>)<br />\n',
            'Total in: ', format_satoshis(tx['value_in'], chain), '<br />\n',
            'Number of outputs: ', len(tx['out']),
            ' (<a href="#outputs">Jump to outputs</a>)<br />\n',
            'Total out: ', format_satoshis(tx['value_out'], chain), '<br />\n',
            'Size: ', tx['size'], ' bytes<br />\n',
            'Fee: ', format_satoshis(0 if is_coinbase else
                                     (tx['value_in'] and tx['value_out'] and
                                      tx['value_in'] - tx['value_out']), chain),
            '<br />\n',
            '<a href="../rawtx/', tx['hash'], '">Raw transaction</a><br />\n']
        body += ['</p>\n',
                 '<a name="inputs"><h3>Inputs</h3></a>\n<table>\n',
                 '<tr><th>Index</th><th>Previous output</th><th>Amount</th>',
                 '<th>From address</th>']
        if abe.store.keep_scriptsig:
            body += ['<th>ScriptSig</th>']
        body += ['</tr>\n']
        for txin in tx['in']:
            row_to_html(txin, 'i', 'o',
                        'Generation' if is_coinbase else 'Unknown')
        body += ['</table>\n',
                 '<a name="outputs"><h3>Outputs</h3></a>\n<table>\n',
                 '<tr><th>Index</th><th>Redeemed at input</th><th>Amount</th>',
                 '<th>To address</th><th>ScriptPubKey</th></tr>\n']
        for txout in tx['out']:
            row_to_html(txout, 'o', 'i', 'Not yet redeemed')

        body += ['</table>\n']

    def handle_rawtx(abe, page):
        abe.do_raw(page, abe.do_rawtx)

    def do_rawtx(abe, page, chain):
        tx_hash = wsgiref.util.shift_path_info(page['env'])
        if tx_hash in (None, '') or page['env']['PATH_INFO'] != '' \
                or not is_hash_prefix(tx_hash):
            return 'ERROR: Not in correct format'  # BBE compatible

        tx = abe.store.export_tx(tx_hash=tx_hash.lower())
        if tx is None:
            return 'ERROR: Transaction does not exist.'  # BBE compatible
        return json.dumps(tx, sort_keys=True, indent=2)

    def handle_address(abe, page):
        address = wsgiref.util.shift_path_info(page['env'])
        if address in (None, '') or page['env']['PATH_INFO'] != '':
            raise PageNotFound()

        body = page['body']
        page['title'] = 'Address ' + escape(address)

        try:
            history = abe.store.export_address_history(
                address, chain=page['chain'], max_rows=abe.address_history_rows_max)
        except DataStore.MalformedAddress:
            body += ['<p>Not a valid address.</p>']
            return

        if history is None:
            body += ["<p>I'm sorry, this address has too many records"
                     " to display.</p>"]
            return

        binaddr  = history['binaddr']
        version  = history['version']
        chains   = history['chains']
        txpoints = history['txpoints']
        balance  = history['balance']
        sent     = history['sent']
        received = history['received']
        counts   = history['counts']

        if (not chains):
            body += ['<p>Address not seen on the network.</p>']
            return

        def format_amounts(amounts, link):
            ret = []
            for chain in chains:
                if ret:
                    ret += [', ']
                ret += [format_satoshis(amounts[chain.id], chain),
                        ' ', escape(chain.code3)]
                if link:
                    vers = chain.address_version
                    if page['chain'] is not None and version == page['chain'].script_addr_vers:
                        vers = chain.script_addr_vers or vers
                    other = util.hash_to_address(vers, binaddr)
                    if other != address:
                        ret[-1] = ['<a href="', page['dotdot'],
                                   'address/', other,
                                   '">', ret[-1], '</a>']
            return ret

        if abe.shortlink_type == "firstbits":
            link = abe.store.get_firstbits(
                address_version=version, db_pubkey_hash=abe.store.binin(binaddr),
                chain_id = (page['chain'] and page['chain'].id))
            if link:
                link = link.replace('l', 'L')
            else:
                link = address
        else:
            link = address[0 : abe.shortlink_type]
        body += abe.short_link(page, 'a/' + link)

        body += ['<p>Balance: '] + format_amounts(balance, True)

        if 'subbinaddr' in history:
            chain = page['chain']

            if chain is None:
                for c in chains:
                    if c.script_addr_vers == version:
                        chain = c
                        break
                if chain is None:
                    chain = chains[0]

            body += ['<br />\nEscrow']
            for subbinaddr in history['subbinaddr']:
                body += [' ', hash_to_address_link(chain.address_version, subbinaddr, page['dotdot'], 10) ]

        for chain in chains:
            balance[chain.id] = 0  # Reset for history traversal.

        body += ['<br />\n',
                 'Transactions in: ', counts[0], '<br />\n',
                 'Received: ', format_amounts(received, False), '<br />\n',
                 'Transactions out: ', counts[1], '<br />\n',
                 'Sent: ', format_amounts(sent, False), '<br />\n']

        body += ['</p>\n'
                 '<h3>Transactions</h3>\n'
                 '<table class="addrhist">\n<tr><th>Transaction</th><th>Block</th>'
                 '<th>Approx. Time</th><th>Amount</th><th>Balance</th>'
                 '<th>Currency</th></tr>\n']

        for elt in txpoints:
            chain = elt['chain']
            type = elt['type']

            if type == 'direct':
                balance[chain.id] += elt['value']

            body += ['<tr class="', type, '"><td class="tx"><a href="../tx/', elt['tx_hash'],
                     '#', 'i' if elt['is_out'] else 'o', elt['pos'],
                     '">', elt['tx_hash'][:10], '...</a>',
                     '</td><td class="block"><a href="../block/', elt['blk_hash'],
                     '">', elt['height'], '</a></td><td class="time">',
                     format_time(elt['nTime']), '</td><td class="amount">']

            if elt['value'] < 0:
                value = '(' + format_satoshis(-elt['value'], chain) + ')'
            else:
                value = format_satoshis(elt['value'], chain)

            if 'binaddr' in elt:
                value = hash_to_address_link(chain.script_addr_vers, elt['binaddr'], page['dotdot'], text=value)

            body += [value, '</td><td class="balance">',
                     format_satoshis(balance[chain.id], chain),
                     '</td><td class="currency">', escape(chain.code3),
                     '</td></tr>\n']
        body += ['</table>\n']

    def search_form(abe, page):
        q = (page['params'].get('q') or [''])[0]
        return [
            '<p>Search by address, block number or hash, transaction or'
            ' public key hash, or chain name:</p>\n'
            '<form action="', page['dotdot'], 'search"><p>\n'
            '<input name="q" size="64" value="', escape(q), '" />'
            '<button type="submit">Search</button>\n'
            '<br />Address or hash search requires at least the first ',
            HASH_PREFIX_MIN, ' characters.</p></form>\n']

    def handle_search(abe, page):
        page['title'] = 'Search'
        q = (page['params'].get('q') or [''])[0]
        if q == '':
            page['body'] = [
                '<p>Please enter search terms.</p>\n', abe.search_form(page)]
            return

        found = []
        if HEIGHT_RE.match(q):      found += abe.search_number(int(q))
        if util.possible_address(q):found += abe.search_address(q)
        elif ADDR_PREFIX_RE.match(q):found += abe.search_address_prefix(q)
        if is_hash_prefix(q):       found += abe.search_hash_prefix(q)
        found += abe.search_general(q)
        abe.show_search_results(page, found)

    def show_search_results(abe, page, found):
        if not found:
            page['body'] = [
                '<p>No results found.</p>\n', abe.search_form(page)]
            return

        if len(found) == 1:
            # Undo shift_path_info.
            sn = posixpath.dirname(page['env']['SCRIPT_NAME'])
            if sn == '/': sn = ''
            page['env']['SCRIPT_NAME'] = sn
            page['env']['PATH_INFO'] = '/' + page['dotdot'] + found[0]['uri']
            del(page['env']['QUERY_STRING'])
            raise Redirect()

        body = page['body']
        body += ['<h3>Search Results</h3>\n<ul>\n']
        for result in found:
            body += [
                '<li><a href="', page['dotdot'], escape(result['uri']), '">',
                escape(result['name']), '</a></li>\n']
        body += ['</ul>\n']

    def search_number(abe, n):
        def process(row):
            (chain_name, dbhash, in_longest) = row
            hexhash = abe.store.hashout_hex(dbhash)
            if in_longest == 1:
                name = str(n)
            else:
                name = hexhash
            return {
                'name': chain_name + ' ' + name,
                'uri': 'block/' + hexhash,
                }

        return map(process, abe.store.selectall("""
            SELECT c.chain_name, b.block_hash, cc.in_longest
              FROM chain c
              JOIN chain_candidate cc ON (cc.chain_id = c.chain_id)
              JOIN block b ON (b.block_id = cc.block_id)
             WHERE cc.block_height = ?
             ORDER BY c.chain_name, cc.in_longest DESC
        """, (n,)))

    def search_hash_prefix(abe, q, types = ('tx', 'block', 'pubkey')):
        q = q.lower()
        ret = []
        for t in types:
            def process(row):
                if   t == 'tx':    name = 'Transaction'
                elif t == 'block': name = 'Block'
                else:
                    # XXX Use Bitcoin address version until we implement
                    # /pubkey/... for this to link to.
                    return abe._found_address(
                        util.hash_to_address('\0', abe.store.binout(row[0])))
                hash = abe.store.hashout_hex(row[0])
                return {
                    'name': name + ' ' + hash,
                    'uri': t + '/' + hash,
                    }

            if t == 'pubkey':
                if len(q) > 40:
                    continue
                lo = abe.store.binin_hex(q + '0' * (40 - len(q)))
                hi = abe.store.binin_hex(q + 'f' * (40 - len(q)))
            else:
                lo = abe.store.hashin_hex(q + '0' * (64 - len(q)))
                hi = abe.store.hashin_hex(q + 'f' * (64 - len(q)))

            ret += map(process, abe.store.selectall(
                "SELECT " + t + "_hash FROM " + t + " WHERE " + t +
                # XXX hardcoded limit.
                "_hash BETWEEN ? AND ? LIMIT 100",
                (lo, hi)))
        return ret

    def _found_address(abe, address):
        return { 'name': 'Address ' + address, 'uri': 'address/' + address }

    def search_address(abe, address):
        try:
            binaddr = base58.bc_address_to_hash_160(address)
        except Exception:
            return abe.search_address_prefix(address)
        return [abe._found_address(address)]

    def search_address_prefix(abe, ap):
        ret = []
        ones = 0
        for c in ap:
            if c != '1':
                break
            ones += 1
        all_ones = (ones == len(ap))
        minlen = max(len(ap), 24)
        l = max(35, len(ap))  # XXX Increase "35" to support multibyte
                              # address versions.
        al = ap + ('1' * (l - len(ap)))
        ah = ap + ('z' * (l - len(ap)))

        def incr_str(s):
            for i in range(len(s)-1, -1, -1):
                if s[i] != '\xff':
                    return s[:i] + chr(ord(s[i])+1) + ('\0' * (len(s) - i - 1))
            return '\1' + ('\0' * len(s))

        def process(row):
            hash = abe.store.binout(row[0])
            address = util.hash_to_address(vl, hash)
            if address.startswith(ap):
                v = vl
            else:
                if vh != vl:
                    address = util.hash_to_address(vh, hash)
                    if not address.startswith(ap):
                        return None
                    v = vh
            if abe.is_address_version(v):
                return abe._found_address(address)

        while l >= minlen:
            vl, hl = util.decode_address(al)
            vh, hh = util.decode_address(ah)
            if ones:
                if not all_ones and \
                        util.hash_to_address('\0', hh)[ones:][:1] == '1':
                    break
            elif vh == '\0':
                break
            elif vh != vl and vh != incr_str(vl):
                continue
            if hl <= hh:
                neg = ""
            else:
                neg = " NOT"
                hl, hh = hh, hl
            bl = abe.store.binin(hl)
            bh = abe.store.binin(hh)
            ret += filter(None, map(process, abe.store.selectall(
                "SELECT pubkey_hash FROM pubkey WHERE pubkey_hash" +
                # XXX hardcoded limit.
                neg + " BETWEEN ? AND ? LIMIT 100", (bl, bh))))
            l -= 1
            al = al[:-1]
            ah = ah[:-1]

        return ret

    def search_general(abe, q):
        """Search for something that is not an address, hash, or block number.
        Currently, this is limited to chain names and currency codes."""
        def process(row):
            (name, code3) = row
            return { 'name': name + ' (' + code3 + ')',
                     'uri': 'chain/' + str(name) }
        ret = map(process, abe.store.selectall("""
            SELECT chain_name, chain_code3
              FROM chain
             WHERE UPPER(chain_name) LIKE '%' || ? || '%'
                OR UPPER(chain_code3) LIKE '%' || ? || '%'
        """, (q.upper(), q.upper())))
        return ret

    def handle_t(abe, page):
        abe.show_search_results(
            page,
            abe.search_hash_prefix(
                b58hex(wsgiref.util.shift_path_info(page['env'])),
                ('tx',)))

    def handle_b(abe, page):
        if page.get('chain') is not None:
            chain = page['chain']
            height = wsgiref.util.shift_path_info(page['env'])
            try:
                height = int(height)
            except Exception:
                raise PageNotFound()
            if height < 0 or page['env']['PATH_INFO'] != '':
                raise PageNotFound()

            cmd = wsgiref.util.shift_path_info(page['env'])
            if cmd is not None:
                raise PageNotFound()  # XXX want to support /a/...

            page['title'] = [escape(chain.name), ' ', height]
            abe._show_block(page, page['dotdot'] + 'block/', chain, block_number=height)
            return

        abe.show_search_results(
            page,
            abe.search_hash_prefix(
                shortlink_block(wsgiref.util.shift_path_info(page['env'])),
                ('block',)))

    def handle_a(abe, page):
        arg = wsgiref.util.shift_path_info(page['env'])
        if abe.shortlink_type == "firstbits":
            addrs = map(
                abe._found_address,
                abe.store.firstbits_to_addresses(
                    arg.lower(),
                    chain_id = page['chain'] and page['chain'].id))
        else:
            addrs = abe.search_address_prefix(arg)
        abe.show_search_results(page, addrs)

    def handle_unspent(abe, page):
        abe.do_raw(page, abe.do_unspent)

    def do_unspent(abe, page, chain):
        addrs = wsgiref.util.shift_path_info(page['env'])
        if addrs is None:
            addrs = []
        else:
            addrs = addrs.split("|");
        if len(addrs) < 1 or len(addrs) > MAX_UNSPENT_ADDRESSES:
            return 'Number of addresses must be between 1 and ' + \
                str(MAX_UNSPENT_ADDRESSES)

        if chain:
            chain_id = chain.id
            bind = [chain_id]
        else:
            chain_id = None
            bind = []

        hashes = []
        good_addrs = []
        for address in addrs:
            try:
                hashes.append(abe.store.binin(
                        base58.bc_address_to_hash_160(address)))
                good_addrs.append(address)
            except Exception:
                pass
        addrs = good_addrs
        bind += hashes

        if len(hashes) == 0:  # Address(es) are invalid.
            return 'Error getting unspent outputs'  # blockchain.info compatible

        placeholders = "?" + (",?" * (len(hashes)-1))

        max_rows = abe.address_history_rows_max
        if max_rows >= 0:
            bind += [max_rows + 1]

        spent = set()
        for txout_id, spent_chain_id in abe.store.selectall("""
            SELECT txin.txout_id, cc.chain_id
              FROM chain_candidate cc
              JOIN block_tx ON (block_tx.block_id = cc.block_id)
              JOIN txin ON (txin.tx_id = block_tx.tx_id)
              JOIN txout prevout ON (txin.txout_id = prevout.txout_id)
              JOIN pubkey ON (pubkey.pubkey_id = prevout.pubkey_id)
             WHERE cc.in_longest = 1""" + ("" if chain_id is None else """
               AND cc.chain_id = ?""") + """
               AND pubkey.pubkey_hash IN (""" + placeholders + """)""" + (
                "" if max_rows < 0 else """
             LIMIT ?"""), bind):
            spent.add((int(txout_id), int(spent_chain_id)))

        abe.log.debug('spent: %s', spent)

        received_rows = abe.store.selectall("""
            SELECT
                txout.txout_id,
                cc.chain_id,
                tx.tx_hash,
                txout.txout_pos,
                txout.txout_scriptPubKey,
                txout.txout_value,
                cc.block_height
              FROM chain_candidate cc
              JOIN block_tx ON (block_tx.block_id = cc.block_id)
              JOIN tx ON (tx.tx_id = block_tx.tx_id)
              JOIN txout ON (txout.tx_id = tx.tx_id)
              JOIN pubkey ON (pubkey.pubkey_id = txout.pubkey_id)
             WHERE cc.in_longest = 1""" + ("" if chain_id is None else """
               AND cc.chain_id = ?""") + """
               AND pubkey.pubkey_hash IN (""" + placeholders + """)""" + (
                "" if max_rows < 0 else """
             ORDER BY cc.block_height,
                   block_tx.tx_pos,
                   txout.txout_pos
             LIMIT ?"""), bind)

        if max_rows >= 0 and len(received_rows) > max_rows:
            return "ERROR: too many records to process"

        rows = []
        for row in received_rows:
            key = (int(row[0]), int(row[1]))
            if key in spent:
                continue
            rows.append(row[2:])

        if len(rows) == 0:
            return 'No free outputs to spend [' + '|'.join(addrs) + ']'

        out = []
        for row in rows:
            tx_hash, out_pos, script, value, height = row
            tx_hash = abe.store.hashout_hex(tx_hash)
            out_pos = None if out_pos is None else int(out_pos)
            script = abe.store.binout_hex(script)
            value = None if value is None else int(value)
            height = None if height is None else int(height)
            out.append({
                    'tx_hash': tx_hash,
                    'tx_output_n': out_pos,
                    'script': script,
                    'value': value,
                    'value_hex': None if value is None else "%x" % value,
                    'block_number': height})

        return json.dumps({ 'unspent_outputs': out }, sort_keys=True, indent=2)

    def do_raw(abe, page, func):
        page['content_type'] = 'text/plain'
        page['template'] = '%(body)s'
        page['body'] = func(page, page['chain'])

    def handle_q(abe, page):
        cmd = wsgiref.util.shift_path_info(page['env'])
        if cmd is None:
            return abe.q(page)

        func = getattr(abe, 'q_' + cmd, None)
        if func is None:
            raise PageNotFound()

        abe.do_raw(page, func)

        if page['content_type'] == 'text/plain':
            jsonp = page['params'].get('jsonp', [None])[0]
            fmt = page['params'].get('format', ["jsonp" if jsonp else "csv"])[0]

            if fmt in ("json", "jsonp"):
                page['body'] = json.dumps([page['body']])

                if fmt == "jsonp":
                    page['body'] = (jsonp or "jsonp") + "(" + page['body'] + ")"
                    page['content_type'] = 'application/javascript'
                else:
                    page['content_type'] = 'application/json'

    def q(abe, page):
        page['body'] = ['<p>Supported APIs:</p>\n<ul>\n']
        for name in dir(abe):
            if not name.startswith("q_"):
                continue
            cmd = name[2:]
            page['body'] += ['<li><a href="q/', cmd, '">', cmd, '</a>']
            val = getattr(abe, name)
            if val.__doc__ is not None:
                page['body'] += [' - ', escape(val.__doc__)]
            page['body'] += ['</li>\n']
        page['body'] += ['</ul>\n']

    def get_max_block_height(abe, chain):
        # "getblockcount" traditionally returns max(block_height),
        # which is one less than the actual block count.
        return abe.store.get_block_number(chain.id)

    def q_getblockcount(abe, page, chain):
        """shows the current block number."""
        if chain is None:
            return 'Shows the greatest block height in CHAIN.\n' \
                '/chain/CHAIN/q/getblockcount\n'
        return abe.get_max_block_height(chain)

    def q_getdifficulty(abe, page, chain):
        """shows the last solved block's difficulty."""
        if chain is None:
            return 'Shows the difficulty of the last block in CHAIN.\n' \
                '/chain/CHAIN/q/getdifficulty\n'
        target = abe.store.get_target(chain.id)
        return "" if target is None else util.target_to_difficulty(target)

    def q_translate_address(abe, page, chain):
        """shows the address in a given chain with a given address's hash."""
        addr = wsgiref.util.shift_path_info(page['env'])
        if chain is None or addr is None:
            return 'Translates ADDRESS for use in CHAIN.\n' \
                '/chain/CHAIN/q/translate_address/ADDRESS\n'
        version, hash = util.decode_check_address(addr)
        if hash is None:
            return addr + " (INVALID ADDRESS)"
        return util.hash_to_address(chain.address_version, hash)

    def q_decode_address(abe, page, chain):
        """shows the version prefix and hash encoded in an address."""
        addr = wsgiref.util.shift_path_info(page['env'])
        if addr is None:
            return "Shows ADDRESS's version byte(s) and public key hash" \
                ' as hex strings separated by colon (":").\n' \
                '/q/decode_address/ADDRESS\n'
        # XXX error check?
        version, hash = util.decode_address(addr)
        ret = version.encode('hex') + ":" + hash.encode('hex')
        if util.hash_to_address(version, hash) != addr:
            ret = "INVALID(" + ret + ")"
        return ret

    def q_addresstohash(abe, page, chain):
        """shows the public key hash encoded in an address."""
        addr = wsgiref.util.shift_path_info(page['env'])
        if addr is None:
            return 'Shows the 160-bit hash encoded in ADDRESS.\n' \
                'For BBE compatibility, the address is not checked for' \
                ' validity.  See also /q/decode_address.\n' \
                '/q/addresstohash/ADDRESS\n'
        version, hash = util.decode_address(addr)
        return hash.encode('hex').upper()

    def q_hashtoaddress(abe, page, chain):
        """shows the address with the given version prefix and hash."""
        arg1 = wsgiref.util.shift_path_info(page['env'])
        arg2 = wsgiref.util.shift_path_info(page['env'])
        if arg1 is None:
            return \
                'Converts a 160-bit hash and address version to an address.\n' \
                '/q/hashtoaddress/HASH[/VERSION]\n'

        if page['env']['PATH_INFO']:
            return "ERROR: Too many arguments"

        if arg2 is not None:
            # BBE-compatible HASH/VERSION
            version, hash = arg2, arg1

        elif arg1.find(":") >= 0:
            # VERSION:HASH as returned by /q/decode_address.
            version, hash = arg1.split(":", 1)

        elif chain:
            version, hash = chain.address_version.encode('hex'), arg1

        else:
            # Default: Bitcoin address starting with "1".
            version, hash = '00', arg1

        try:
            hash = hash.decode('hex')
            version = version.decode('hex')
        except Exception:
            return 'ERROR: Arguments must be hexadecimal strings of even length'
        return util.hash_to_address(version, hash)

    def q_hashpubkey(abe, page, chain):
        """shows the 160-bit hash of the given public key."""
        pubkey = wsgiref.util.shift_path_info(page['env'])
        if pubkey is None:
            return \
                "Returns the 160-bit hash of PUBKEY.\n" \
                "For example, the Bitcoin genesis block's output public key," \
                " seen in its transaction output scriptPubKey, starts with\n" \
                "04678afdb0fe..., and its hash is" \
                " 62E907B15CBF27D5425399EBF6F0FB50EBB88F18, corresponding" \
                " to address 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa.\n" \
                "/q/hashpubkey/PUBKEY\n"
        try:
            pubkey = pubkey.decode('hex')
        except Exception:
            return 'ERROR: invalid hexadecimal byte string.'
        return util.pubkey_to_hash(pubkey).encode('hex').upper()

    def q_checkaddress(abe, page, chain):
        """checks an address for validity."""
        addr = wsgiref.util.shift_path_info(page['env'])
        if addr is None:
            return \
                "Returns the version encoded in ADDRESS as a hex string.\n" \
                "If ADDRESS is invalid, returns either X5, SZ, or CK for" \
                " BBE compatibility.\n" \
                "/q/checkaddress/ADDRESS\n"
        if util.possible_address(addr):
            version, hash = util.decode_address(addr)
            if util.hash_to_address(version, hash) == addr:
                return version.encode('hex').upper()
            return 'CK'
        if len(addr) >= 26:
            return 'X5'
        return 'SZ'

    def q_nethash(abe, page, chain):
        """shows statistics about difficulty and network power."""
        if chain is None:
            return 'Shows statistics every INTERVAL blocks.\n' \
                'Negative values count back from the last block.\n' \
                '/chain/CHAIN/q/nethash[/INTERVAL[/START[/STOP]]]\n'

        jsonp = page['params'].get('jsonp', [None])[0]
        fmt = page['params'].get('format', ["jsonp" if jsonp else "csv"])[0]
        interval = path_info_int(page, 144)
        start = path_info_int(page, 0)
        stop = path_info_int(page, None)

        if stop == 0:
            stop = None

        if interval < 0 and start != 0:
            return 'ERROR: Negative INTERVAL requires 0 START.'

        if interval < 0 or start < 0 or (stop is not None and stop < 0):
            count = abe.get_max_block_height(chain)
            if start < 0:
                start += count
            if stop is not None and stop < 0:
                stop += count
            if interval < 0:
                interval = -interval
                start = count - (count / interval) * interval

        # Select every INTERVAL blocks from START to STOP.
        # Standard SQL lacks an "every Nth row" feature, so we
        # provide it with the help of a table containing the integers.
        # We don't need all integers, only as many as rows we want to
        # fetch.  We happen to have a table with the desired integers,
        # namely chain_candidate; its block_height column covers the
        # required range without duplicates if properly constrained.
        # That is the story of the second JOIN.

        if stop is not None:
            stop_ix = (stop - start) / interval

        rows = abe.store.selectall("""
            SELECT b.block_height,
                   b.block_nTime,
                   b.block_chain_work,
                   b.block_nBits
              FROM block b
              JOIN chain_candidate cc ON (cc.block_id = b.block_id)
              JOIN chain_candidate ints ON (
                       ints.chain_id = cc.chain_id
                   AND ints.in_longest = 1
                   AND ints.block_height * ? + ? = cc.block_height)
             WHERE cc.in_longest = 1
               AND cc.chain_id = ?""" + (
                "" if stop is None else """
               AND ints.block_height <= ?""") + """
             ORDER BY cc.block_height""",
                                   (interval, start, chain.id)
                                   if stop is None else
                                   (interval, start, chain.id, stop_ix))
        if fmt == "csv":
            ret = NETHASH_HEADER

        elif fmt in ("json", "jsonp"):
            ret = []

        elif fmt == "svg":
            page['template'] = NETHASH_SVG_TEMPLATE
            page['template_vars']['block_time'] = 600;  # XXX BTC-specific
            ret = ""

        else:
            return "ERROR: unknown format: " + fmt

        prev_nTime, prev_chain_work = 0, -1

        for row in rows:
            height, nTime, chain_work, nBits = row
            nTime            = float(nTime)
            nBits            = int(nBits)
            target           = util.calculate_target(nBits)
            difficulty       = util.target_to_difficulty(target)
            work             = util.target_to_work(target)
            chain_work       = abe.store.binout_int(chain_work) - work

            if row is not rows[0] or fmt == "svg":
                height           = int(height)
                interval_work    = chain_work - prev_chain_work
                avg_target       = util.work_to_target(
                    interval_work / float(interval))
                #if avg_target == target - 1:
                #    avg_target = target
                interval_seconds = nTime - prev_nTime
                if interval_seconds <= 0:
                    nethash = 'Infinity'
                else:
                    nethash = "%.0f" % (interval_work / interval_seconds,)

                if fmt == "csv":
                    ret += "%d,%d,%d,%d,%.3f,%d,%.0f,%s\n" % (
                        height, nTime, target, avg_target, difficulty, work,
                        interval_seconds / interval, nethash)

                elif fmt in ("json", "jsonp"):
                    ret.append([
                            height, int(nTime), target, avg_target,
                            difficulty, work, chain_work])

                elif fmt == "svg":
                    ret += '<abe:nethash t="%d" d="%d"' \
                        ' w="%d"/>\n' % (nTime, work, interval_work)

            prev_nTime, prev_chain_work = nTime, chain_work

        if fmt == "csv":
            return ret

        elif fmt == "json":
            page['content_type'] = 'application/json'
            return json.dumps(ret)

        elif fmt == "jsonp":
            page['content_type'] = 'application/javascript'
            return (jsonp or "jsonp") + "(" + json.dumps(ret) + ")"

        elif fmt == "svg":
            page['content_type'] = 'image/svg+xml'
            return ret

    def q_totalbc(abe, page, chain):
        """shows the amount of currency ever mined."""
        if chain is None:
            return 'Shows the amount of currency ever mined.\n' \
                'This differs from the amount in circulation when' \
                ' coins are destroyed, as happens frequently in Namecoin.\n' \
                'Unlike http://blockexplorer.com/q/totalbc, this does not' \
                ' support future block numbers, and it returns a sum of' \
                ' observed generations rather than a calculated value.\n' \
                '/chain/CHAIN/q/totalbc[/HEIGHT]\n'
        height = path_info_uint(page, None)
        if height is None:
            row = abe.store.selectrow("""
                SELECT b.block_total_satoshis
                  FROM chain c
                  LEFT JOIN block b ON (c.chain_last_block_id = b.block_id)
                 WHERE c.chain_id = ?
            """, (chain.id,))
        else:
            row = abe.store.selectrow("""
                SELECT b.block_total_satoshis
                  FROM chain_candidate cc
                  LEFT JOIN block b ON (b.block_id = cc.block_id)
                 WHERE cc.chain_id = ?
                   AND cc.block_height = ?
                   AND cc.in_longest = 1
            """, (chain.id, height))
            if not row:
                return 'ERROR: block %d not seen yet' % (height,)
        return format_satoshis(row[0], chain) if row else 0

    def q_getreceivedbyaddress(abe, page, chain):
        """shows the amount ever received by a given address."""
        addr = wsgiref.util.shift_path_info(page['env'])
        if chain is None or addr is None:
            return 'returns amount of money received by given address (not balance, sends are not subtracted)\n' \
                '/chain/CHAIN/q/getreceivedbyaddress/ADDRESS\n'

        if not util.possible_address(addr):
            return 'ERROR: address invalid'

        version, hash = util.decode_address(addr)
        return format_satoshis(abe.store.get_received(chain.id, hash), chain)

    def q_getsentbyaddress(abe, page, chain):
        """shows the amount ever sent from a given address."""
        addr = wsgiref.util.shift_path_info(page['env'])
        if chain is None or addr is None:
            return 'returns amount of money sent from given address\n' \
                '/chain/CHAIN/q/getsentbyaddress/ADDRESS\n'

        if not util.possible_address(addr):
            return 'ERROR: address invalid'

        version, hash = util.decode_address(addr)
        return format_satoshis(abe.store.get_sent(chain.id, hash), chain)

    def q_addressbalance(abe, page, chain):
        """amount ever received minus amount ever sent by a given address."""
        addr = wsgiref.util.shift_path_info(page['env'])
        if chain is None or addr is None:
            return 'returns amount of money at the given address\n' \
                '/chain/CHAIN/q/addressbalance/ADDRESS\n'

        if not util.possible_address(addr):
            return 'ERROR: address invalid'

        version, hash = util.decode_address(addr)
        total = abe.store.get_balance(chain.id, hash)

        return ("ERROR: please try again" if total is None else
                format_satoshis(total, chain))

    def q_fb(abe, page, chain):
        """returns an address's firstbits."""

        if not abe.store.use_firstbits:
            raise PageNotFound()

        addr = wsgiref.util.shift_path_info(page['env'])
        if addr is None:
            return 'Shows ADDRESS\'s firstbits:' \
                ' the shortest initial substring that uniquely and' \
                ' case-insensitively distinguishes ADDRESS from all' \
                ' others first appearing before it or in the same block.\n' \
                'See http://firstbits.com/.\n' \
                'Returns empty if ADDRESS has no firstbits.\n' \
                '/chain/CHAIN/q/fb/ADDRESS\n' \
                '/q/fb/ADDRESS\n'

        if not util.possible_address(addr):
            return 'ERROR: address invalid'

        version, dbhash = util.decode_address(addr)
        ret = abe.store.get_firstbits(
            address_version = version,
            db_pubkey_hash = abe.store.binin(dbhash),
            chain_id = (chain and chain.id))

        if ret is None:
            return 'ERROR: address not in the chain.'

        return ret

    def q_addr(abe, page, chain):
        """returns the full address having the given firstbits."""

        if not abe.store.use_firstbits:
            raise PageNotFound()

        fb = wsgiref.util.shift_path_info(page['env'])
        if fb is None:
            return 'Shows the address identified by FIRSTBITS:' \
                ' the first address in CHAIN to start with FIRSTBITS,' \
                ' where the comparison is case-insensitive.\n' \
                'See http://firstbits.com/.\n' \
                'Returns the argument if none matches.\n' \
                '/chain/CHAIN/q/addr/FIRSTBITS\n' \
                '/q/addr/FIRSTBITS\n'

        return "\n".join(abe.store.firstbits_to_addresses(
                fb, chain_id = (chain and chain.id)))

    def handle_download(abe, page):
        name = abe.args.download_name
        if name is None:
            name = re.sub(r'\W+', '-', ABE_APPNAME.lower()) + '-' + ABE_VERSION
        fileobj = lambda: None
        fileobj.func_dict['write'] = page['start_response'](
            '200 OK',
            [('Content-type', 'application/x-gtar-compressed'),
             ('Content-disposition', 'filename=' + name + '.tar.gz')])
        import tarfile
        with tarfile.TarFile.open(fileobj=fileobj, mode='w|gz',
                                  format=tarfile.PAX_FORMAT) as tar:
            tar.add(os.path.split(__file__)[0], name)
        raise Streamed()

    def serve_static(abe, path, start_response):
        slen = len(abe.static_path)
        if path[:slen] != abe.static_path:
            raise PageNotFound()
        path = path[slen:]
        try:
            # Serve static content.
            # XXX Should check file modification time and handle HTTP
            # if-modified-since.  Or just hope serious users will map
            # our htdocs as static in their web server.
            # XXX is "+ '/' + path" adequate for non-POSIX systems?
            found = open(abe.htdocs + '/' + path, "rb")
            import mimetypes
            type, enc = mimetypes.guess_type(path)
            # XXX Should do something with enc if not None.
            # XXX Should set Content-length.
            start_response('200 OK', [('Content-type', type or 'text/plain')])
            return found
        except IOError:
            raise PageNotFound()

    # Change this if you want empty or multi-byte address versions.
    def is_address_version(abe, v):
        return len(v) == 1

    def short_link(abe, page, link):
        base = abe.base_url
        if base is None:
            env = page['env'].copy()
            env['SCRIPT_NAME'] = posixpath.normpath(
                posixpath.dirname(env['SCRIPT_NAME'] + env['PATH_INFO'])
                + '/' + page['dotdot'])
            env['PATH_INFO'] = link
            full = wsgiref.util.request_uri(env)
        else:
            full = base + link

        return ['<p class="shortlink">Short Link: <a href="',
                page['dotdot'], link, '">', full, '</a></p>\n']

    def fix_path_info(abe, env):
        ret = True
        pi = env['PATH_INFO']
        pi = posixpath.normpath(pi)
        if pi[-1] != '/' and env['PATH_INFO'][-1:] == '/':
            pi += '/'
        if pi == '/':
            pi += abe.home
            if not '/' in abe.home:
                ret = False
        if pi == env['PATH_INFO']:
            ret = False
        else:
            env['PATH_INFO'] = pi
        return ret

def find_htdocs():
    return os.path.join(os.path.split(__file__)[0], 'htdocs')

def get_int_param(page, name):
    vals = page['params'].get(name)
    return vals and int(vals[0])

def path_info_uint(page, default):
    ret = path_info_int(page, None)
    if ret is None or ret < 0:
        return default
    return ret

def path_info_int(page, default):
    s = wsgiref.util.shift_path_info(page['env'])
    if s is None:
        return default
    try:
        return int(s)
    except ValueError:
        return default

def format_time(nTime):
    import time
    return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(nTime)))

def format_satoshis(satoshis, chain):
    decimals = DEFAULT_DECIMALS if chain.decimals is None else chain.decimals
    coin = 10 ** decimals

    if satoshis is None:
        return ''
    if satoshis < 0:
        return '-' + format_satoshis(-satoshis, chain)
    satoshis = int(satoshis)
    integer = satoshis / coin
    frac = satoshis % coin
    return (str(integer) +
            ('.' + (('0' * decimals) + str(frac))[-decimals:])
            .rstrip('0').rstrip('.'))

def format_difficulty(diff):
    idiff = int(diff)
    ret = '.%03d' % (int(round((diff - idiff) * 1000)),)
    while idiff > 999:
        ret = (' %03d' % (idiff % 1000,)) + ret
        idiff = idiff / 1000
    return str(idiff) + ret

def hash_to_address_link(version, hash, dotdot, truncate_to=None, text=None):
    if hash == DataStore.NULL_PUBKEY_HASH:
        return 'Destroyed'
    if hash is None:
        return 'UNKNOWN'
    addr = util.hash_to_address(version, hash)

    if text is not None:
        visible = text
    elif truncate_to is None:
        visible = addr
    else:
        visible = addr[:truncate_to] + '...'

    return ['<a href="', dotdot, 'address/', addr, '">', visible, '</a>']

def decode_script(script):
    if script is None:
        return ''
    try:
        return deserialize.decode_script(script)
    except KeyError, e:
        return 'Nonstandard script'

def b58hex(b58):
    try:
        return base58.b58decode(b58, None).encode('hex_codec')
    except Exception:
        raise PageNotFound()

def hexb58(hex):
    return base58.b58encode(hex.decode('hex_codec'))

def block_shortlink(block_hash):
    zeroes = 0
    for c in block_hash:
        if c == '0':
            zeroes += 1
        else:
            break
    zeroes &= ~1
    return hexb58("%02x%s" % (zeroes / 2, block_hash[zeroes : zeroes+12]))

def shortlink_block(link):
    try:
        data = base58.b58decode(link, None)
    except Exception:
        raise PageNotFound()
    return ('00' * ord(data[0])) + data[1:].encode('hex_codec')

def is_hash_prefix(s):
    return HASH_PREFIX_RE.match(s) and len(s) >= HASH_PREFIX_MIN

def flatten(l):
    if isinstance(l, list):
        return ''.join(map(flatten, l))
    if l is None:
        raise Exception('NoneType in HTML conversion')
    if isinstance(l, unicode):
        return l
    return str(l)

def redirect(page):
    uri = wsgiref.util.request_uri(page['env'])
    page['start_response'](
        '301 Moved Permanently',
        [('Location', uri),
         ('Content-Type', 'text/html')])
    return ('<html><head><title>Moved</title></head>\n'
            '<body><h1>Moved</h1><p>This page has moved to '
            '<a href="' + uri + '">' + uri + '</a></body></html>')

def serve(store):
    args = store.args
    abe = Abe(store, args)

    if args.query is not None:
        def start_response(status, headers):
            pass
        import urlparse
        parsed = urlparse.urlparse(args.query)
        print abe({
                'SCRIPT_NAME':  '',
                'PATH_INFO':    parsed.path,
                'QUERY_STRING': parsed.query
                }, start_response)
    elif args.host or args.port:
        # HTTP server.
        if args.host is None:
            args.host = "localhost"
        from wsgiref.simple_server import make_server
        port = int(args.port or 80)
        httpd = make_server(args.host, port, abe)
        abe.log.warning("Listening on http://%s:%d", args.host, port)
        # httpd.shutdown() sometimes hangs, so don't call it.  XXX
        httpd.serve_forever()
    else:
        # FastCGI server.
        from flup.server.fcgi import WSGIServer

        # In the case where the web server starts Abe but can't signal
        # it on server shutdown (because Abe runs as a different user)
        # we arrange the following.  FastCGI script passes its pid as
        # --watch-pid=PID and enters an infinite loop.  We check every
        # minute whether it has terminated and exit when it has.
        wpid = args.watch_pid
        if wpid is not None:
            wpid = int(wpid)
            interval = 60.0  # XXX should be configurable.
            from threading import Timer
            import signal
            def watch():
                if not process_is_alive(wpid):
                    abe.log.warning("process %d terminated, exiting", wpid)
                    #os._exit(0)  # sys.exit merely raises an exception.
                    os.kill(os.getpid(), signal.SIGTERM)
                    return
                abe.log.log(0, "process %d found alive", wpid)
                Timer(interval, watch).start()
            Timer(interval, watch).start()
        WSGIServer(abe).run()

def process_is_alive(pid):
    # XXX probably fails spectacularly on Windows.
    import errno
    try:
        os.kill(pid, 0)
        return True
    except OSError, e:
        if e.errno == errno.EPERM:
            return True  # process exists, but we can't send it signals.
        if e.errno == errno.ESRCH:
            return False # no such process.
        raise

def create_conf():
    conf = {
        "port":                     None,
        "host":                     None,
        "query":                    None,
        "no_serve":                 None,
        "no_load":                  None,
        "debug":                    None,
        "static_path":              None,
        "document_root":            None,
        "auto_agpl":                None,
        "download_name":            None,
        "watch_pid":                None,
        "base_url":                 None,
        "logging":                  None,
        "address_history_rows_max": None,
        "shortlink_type":           None,

        "template":     DEFAULT_TEMPLATE,
        "template_vars": {
            "ABE_URL": ABE_URL,
            "APPNAME": ABE_APPNAME,
            "VERSION": ABE_VERSION,
            "COPYRIGHT": COPYRIGHT,
            "COPYRIGHT_YEARS": COPYRIGHT_YEARS,
            "COPYRIGHT_URL": COPYRIGHT_URL,
            "DONATIONS_BTC": DONATIONS_BTC,
            "DONATIONS_NMC": DONATIONS_NMC,
            "CONTENT_TYPE": DEFAULT_CONTENT_TYPE,
            "HOMEPAGE": DEFAULT_HOMEPAGE,
            },
        }
    conf.update(DataStore.CONFIG_DEFAULTS)
    return conf

def main(argv):
    args, argv = readconf.parse_argv(argv, create_conf())

    if not argv:
        pass
    elif argv[0] in ('-h', '--help'):
        print ("""Usage: python -m Abe.abe [-h] [--config=FILE] [--CONFIGVAR=VALUE]...

A Bitcoin block chain browser.

  --help                    Show this help message and exit.
  --version                 Show the program version and exit.
  --print-htdocs-directory  Show the static content directory name and exit.
  --query /q/COMMAND        Show the given URI content and exit.
  --config FILE             Read options from FILE.

All configuration variables may be given as command arguments.
See abe.conf for commented examples.""")
        return 0
    elif argv[0] in ('-v', '--version'):
        print ABE_APPNAME, ABE_VERSION
        print "Schema version", DataStore.SCHEMA_VERSION
        return 0
    elif argv[0] == '--print-htdocs-directory':
        print find_htdocs()
        return 0
    else:
        sys.stderr.write(
            "Error: unknown option `%s'\n"
            "See `python -m Abe.abe --help' for more information.\n"
            % (argv[0],))
        return 1

    logging.basicConfig(
        stream=sys.stdout,
        level = logging.DEBUG if args.query is None else logging.ERROR,
        format=DEFAULT_LOG_FORMAT)
    if args.logging is not None:
        import logging.config as logging_config
        logging_config.dictConfig(args.logging)

    if args.auto_agpl:
        import tarfile

    store = make_store(args)
    if (not args.no_serve):
        serve(store)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

########NEW FILE########
__FILENAME__ = admin
#!/usr/bin/env python
# Copyright(C) 2012,2013,2014 by Abe developers.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

"""Delete a chain from the database, etc."""

import sys
import logging

import util

def commit(store):
    store.commit()
    store.log.info("Commit.")

def log_rowcount(store, msg):
    store.log.info(msg, store.rowcount())

def link_txin(store):
    store.log.info(
        "Linking missed transaction inputs to their previous outputs.")

    store.sql("""
        UPDATE txin SET txout_id = (
            SELECT txout_id
              FROM unlinked_txin JOIN txout JOIN tx ON (txout.tx_id = tx.tx_id)
             WHERE txin.txin_id = unlinked_txin.txin_id
               AND tx.tx_hash = unlinked_txin.txout_tx_hash
               AND txout.txout_pos = unlinked_txin.txout_pos)
         WHERE txout_id IS NULL""")
    log_rowcount(store, "Updated %d txout_id.")
    commit(store)

    store.sql("""
        DELETE FROM unlinked_txin
         WHERE (SELECT txout_id FROM txin
                 WHERE txin.txin_id = unlinked_txin.txin_id) IS NOT NULL""")
    log_rowcount(store, "Deleted %d unlinked_txin.")
    commit(store)

def delete_tx(store, id_or_hash):
    try:
        tx_id = int(id_or_hash)
    except ValueError:
        (tx_id,) = store.selectrow(
            "SELECT tx_id FROM tx WHERE tx_hash = ?",
            (store.hashin_hex(id_or_hash),))
    store.log.info("Deleting transaction with tx_id=%d", tx_id)

    store.sql("""
        DELETE FROM unlinked_txin WHERE txin_id IN (
            SELECT txin_id FROM txin WHERE tx_id = ?)""",
              (tx_id,))
    log_rowcount(store, "Deleted %d from unlinked_txin.")

    store.sql("DELETE FROM txin WHERE tx_id = ?", (tx_id,))
    log_rowcount(store, "Deleted %d from txin.")

    store.sql("DELETE FROM txout WHERE tx_id = ?", (tx_id,))
    log_rowcount(store, "Deleted %d from txout.")

    store.sql("DELETE FROM tx WHERE tx_id = ?", (tx_id,))
    log_rowcount(store, "Deleted %d from tx.")

    commit(store)

def rewind_datadir(store, dirname):
    store.sql("""
        UPDATE datadir
           SET blkfile_number = 1, blkfile_offset = 0
         WHERE dirname = ?
           AND (blkfile_number > 1 OR blkfile_offset > 0)""",
              (dirname,))
    log_rowcount(store, "Datadir blockfile pointers rewound: %d")
    commit(store)

def rewind_chain_blockfile(store, name, chain_id):
    store.sql("""
        UPDATE datadir
           SET blkfile_number = 1, blkfile_offset = 0
         WHERE chain_id = ?
           AND (blkfile_number > 1 OR blkfile_offset > 0)""",
              (chain_id,))
    log_rowcount(store, "Datadir blockfile pointers rewound: %d")

def chain_name_to_id(store, name):
    (chain_id,) = store.selectrow(
        "SELECT chain_id FROM chain WHERE chain_name = ?", (name,))
    return chain_id

def del_chain_blocks_1(store, name, chain_id):
    store.sql("UPDATE chain SET chain_last_block_id = NULL WHERE chain_id = ?",
              (chain_id,))
    store.log.info("Nulled %s chain_last_block_id.", name)

    store.sql("""
        UPDATE block
           SET prev_block_id = NULL,
               search_block_id = NULL
         WHERE block_id IN (
            SELECT block_id FROM chain_candidate WHERE chain_id = ?)""",
                        (chain_id,))
    log_rowcount(store, "Disconnected %d blocks from chain.")
    commit(store)

    store.sql("""
        DELETE FROM orphan_block WHERE block_id IN (
            SELECT block_id FROM chain_candidate WHERE chain_id = ?)""",
                        (chain_id,))
    log_rowcount(store, "Deleted %d from orphan_block.")
    commit(store)

    store.sql("""
        DELETE FROM block_next WHERE block_id IN (
            SELECT block_id FROM chain_candidate WHERE chain_id = ?)""",
                        (chain_id,))
    log_rowcount(store, "Deleted %d from block_next.")
    commit(store)

    store.sql("""
        DELETE FROM block_txin WHERE block_id IN (
            SELECT block_id FROM chain_candidate WHERE chain_id = ?)""",
                        (chain_id,))
    log_rowcount(store, "Deleted %d from block_txin.")
    commit(store)

    if store.use_firstbits:
        store.sql("""
            DELETE FROM abe_firstbits WHERE block_id IN (
                SELECT block_id FROM chain_candidate WHERE chain_id = ?)""",
                            (chain_id,))
        log_rowcount(store, "Deleted %d from abe_firstbits.")
        commit(store)

def del_chain_block_tx(store, name, chain_id):
    store.sql("""
        DELETE FROM block_tx WHERE block_id IN (
            SELECT block_id FROM chain_candidate WHERE chain_id = ?)""",
                        (chain_id,))
    log_rowcount(store, "Deleted %d from block_tx.")
    commit(store)

def delete_chain_blocks(store, name, chain_id = None):
    if chain_id is None:
        chain_id = chain_name_to_id(store, name)

    store.log.info("Deleting blocks in chain %s", name)
    del_chain_blocks_1(store, name, chain_id)
    del_chain_block_tx(store, name, chain_id)
    del_chain_blocks_2(store, name, chain_id)

def delete_chain_transactions(store, name, chain_id = None):
    if chain_id is None:
        chain_id = chain_name_to_id(store, name)

    store.log.info("Deleting transactions and blocks in chain %s", name)
    del_chain_blocks_1(store, name, chain_id)

    store.sql("""
        DELETE FROM unlinked_txin WHERE txin_id IN (
            SELECT txin.txin_id
              FROM chain_candidate cc
              JOIN block_tx bt ON (cc.block_id = bt.block_id)
              JOIN txin ON (bt.tx_id = txin.tx_id)
             WHERE cc.chain_id = ?)""", (chain_id,))
    log_rowcount(store, "Deleted %d from unlinked_txin.")

    store.sql("""
        DELETE FROM txin WHERE tx_id IN (
            SELECT bt.tx_id
              FROM chain_candidate cc
              JOIN block_tx bt ON (cc.block_id = bt.block_id)
             WHERE cc.chain_id = ?)""", (chain_id,))
    log_rowcount(store, "Deleted %d from txin.")
    commit(store)

    store.sql("""
        DELETE FROM txout WHERE tx_id IN (
            SELECT bt.tx_id
              FROM chain_candidate cc
              JOIN block_tx bt ON (cc.block_id = bt.block_id)
             WHERE cc.chain_id = ?)""", (chain_id,))
    log_rowcount(store, "Deleted %d from txout.")
    commit(store)

    tx_ids = []
    for row in store.selectall("""
        SELECT tx_id
          FROM chain_candidate cc
          JOIN block_tx bt ON (cc.block_id = bt.block_id)
         WHERE cc.chain_id = ?""", (chain_id,)):
        tx_ids.append(int(row[0]))

    del_chain_block_tx(store, name, chain_id)

    deleted = 0
    store.log.info("Deleting from tx...")

    for tx_id in tx_ids:
        store.sql("DELETE FROM tx WHERE tx_id = ?", (tx_id,))
        cnt = store.rowcount()

        if cnt > 0:
            deleted += 1
            if deleted % 10000 == 0:
                store.log.info("Deleting tx: %d", deleted)
                commit(store)

    store.log.info("Deleted %d from tx.", deleted)
    commit(store)

    del_chain_blocks_2(store, name, chain_id)

def del_chain_blocks_2(store, name, chain_id):
    block_ids = []
    for row in store.selectall(
        "SELECT block_id FROM chain_candidate WHERE chain_id = ?", (chain_id,)):
        block_ids.append(int(row[0]))

    store.sql("""
        DELETE FROM chain_candidate WHERE chain_id = ?""",
                        (chain_id,))
    log_rowcount(store, "Deleted %d from chain_candidate.")

    deleted = 0
    for block_id in block_ids:
        store.sql("DELETE FROM block WHERE block_id = ?", (block_id,))
        deleted += store.rowcount()
    store.log.info("Deleted %d from block.", deleted)

    rewind_chain_blockfile(store, name, chain_id)
    commit(store)

def main(argv):
    cmdline = util.CmdLine(argv)
    cmdline.usage = lambda: \
        """Usage: python -m Abe.admin [-h] [--config=FILE] COMMAND...

Options:

  --help                    Show this help message and exit.
  --config FILE             Abe configuration file.

Commands:

  delete-chain-blocks NAME  Delete all blocks in the specified chain
                            from the database.

  delete-chain-transactions NAME  Delete all blocks and transactions in
                            the specified chain.

  delete-tx TX_ID           Delete the specified transaction.
  delete-tx TX_HASH

  link-txin                 Link transaction inputs to previous outputs.

  rewind-datadir DIRNAME    Reset the pointer to force a rescan of
                            blockfiles in DIRNAME."""

    store, argv = cmdline.init()
    if store is None:
        return 0

    while len(argv) != 0:
        command = argv.pop(0)
        if command == 'delete-chain-blocks':
            delete_chain_blocks(store, argv.pop(0))
        elif command == 'delete-chain-transactions':
            delete_chain_transactions(store, argv.pop(0))
        elif command == 'delete-tx':
            delete_tx(store, argv.pop(0))
        elif command == 'rewind-datadir':
            rewind_datadir(store, argv.pop(0))
        elif command == 'link-txin':
            link_txin(store)
        else:
            raise ValueError("Unknown command: " + command)

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

########NEW FILE########
__FILENAME__ = base58
#!/usr/bin/env python

"""encode/decode base58 in the same way that Bitcoin does"""

import math

__b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
__b58base = len(__b58chars)

def b58encode(v):
  """ encode v, which is a string of bytes, to base58.    
  """

  long_value = 0L
  for (i, c) in enumerate(v[::-1]):
    long_value += ord(c) << (8*i) # 2x speedup vs. exponentiation

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

try:
  # Python Crypto library is at: http://www.dlitz.net/software/pycrypto/
  # Needed for RIPEMD160 hash function, used to compute
  # Bitcoin addresses from internal public keys.
  import Crypto.Hash.SHA256 as SHA256
  import Crypto.Hash.RIPEMD160 as RIPEMD160
  have_crypto = True
except ImportError:
  have_crypto = False

def hash_160(public_key):
  if not have_crypto:
    return ''
  h1 = SHA256.new(public_key).digest()
  h2 = RIPEMD160.new(h1).digest()
  return h2

def public_key_to_bc_address(public_key, version="\x00"):
  if not have_crypto or public_key is None:
    return ''
  h160 = hash_160(public_key)
  return hash_160_to_bc_address(h160, version=version)

def hash_160_to_bc_address(h160, version="\x00"):
  if not have_crypto:
    return ''
  vh160 = version+h160
  h3=SHA256.new(SHA256.new(vh160).digest()).digest()
  addr=vh160+h3[0:4]
  return b58encode(addr)

def bc_address_to_hash_160(addr):
  bytes = b58decode(addr, 25)
  return bytes[1:21]

if __name__ == '__main__':
    x = '005cc87f4a3fdfe3a2346b6953267ca867282630d3f9b78e64'.decode('hex_codec')
    encoded = b58encode(x)
    print encoded, '19TbMSWwHvnxAKy12iNm3KdbGfzfaMFViT'
    print b58decode(encoded, len(x)).encode('hex_codec'), x.encode('hex_codec')

########NEW FILE########
__FILENAME__ = BCDataStream
#
# Workalike python implementation of Bitcoin's CDataStream class.
#
import struct
import StringIO
import mmap

class SerializationError(Exception):
  """ Thrown when there's a problem deserializing or serializing """

class BCDataStream(object):
  def __init__(self):
    self.input = None
    self.read_cursor = 0

  def clear(self):
    self.input = None
    self.read_cursor = 0

  def write(self, bytes):  # Initialize with string of bytes
    if self.input is None:
      self.input = bytes
    else:
      self.input += bytes

  def map_file(self, file, start):  # Initialize with bytes from file
    self.input = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
    self.read_cursor = start
  def seek_file(self, position):
    self.read_cursor = position
  def close_file(self):
    self.input.close()

  def read_string(self):
    # Strings are encoded depending on length:
    # 0 to 252 :  1-byte-length followed by bytes (if any)
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
  def read_int16  (self): return self._read_num('<h')
  def read_uint16 (self): return self._read_num('<H')
  def read_int32  (self): return self._read_num('<i')
  def read_uint32 (self): return self._read_num('<I')
  def read_int64  (self): return self._read_num('<q')
  def read_uint64 (self): return self._read_num('<Q')

  def write_boolean(self, val): return self.write(chr(1) if val else chr(0))
  def write_int16  (self, val): return self._write_num('<h', val)
  def write_uint16 (self, val): return self._write_num('<H', val)
  def write_int32  (self, val): return self._write_num('<i', val)
  def write_uint32 (self, val): return self._write_num('<I', val)
  def write_int64  (self, val): return self._write_num('<q', val)
  def write_uint64 (self, val): return self._write_num('<Q', val)

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

########NEW FILE########
__FILENAME__ = Chain
# Copyright(C) 2014 by Abe developers.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

import deserialize
from deserialize import opcodes
import BCDataStream
import util

def create(policy, **kwargs):
    # XXX It's about time to interpret policy as a module name.
    if policy in [None, "Bitcoin"]: return Bitcoin(**kwargs)
    if policy == "Testnet":         return Testnet(**kwargs)
    if policy == "Namecoin":        return Namecoin(**kwargs)
    if policy == "LegacyNoBit8":    return Sha256Chain(**kwargs)
    if policy == "NovaCoin":        return NovaCoin(**kwargs)
    if policy == "CryptoCash":      return CryptoCash(**kwargs)
    if policy == "Hirocoin":        return Hirocoin(**kwargs)
    if policy == "X11":             return X11Chain(**kwargs)
    if policy == "X11Pos":          return X11PosChain(**kwargs)
    if policy == "Bitleu":          return Bitleu(**kwargs)
    if policy == "Keccak":          return KeccakChain(**kwargs)
    if policy == "Maxcoin":         return Maxcoin(**kwargs)
    return Sha256NmcAuxPowChain(**kwargs)


PUBKEY_HASH_LENGTH = 20
MAX_MULTISIG_KEYS = 3

# Template to match a pubkey hash ("Bitcoin address transaction") in
# txout_scriptPubKey.  OP_PUSHDATA4 matches any data push.
SCRIPT_ADDRESS_TEMPLATE = [
    opcodes.OP_DUP, opcodes.OP_HASH160, opcodes.OP_PUSHDATA4, opcodes.OP_EQUALVERIFY, opcodes.OP_CHECKSIG ]

# Template to match a pubkey ("IP address transaction") in txout_scriptPubKey.
SCRIPT_PUBKEY_TEMPLATE = [ opcodes.OP_PUSHDATA4, opcodes.OP_CHECKSIG ]

# Template to match a BIP16 pay-to-script-hash (P2SH) output script.
SCRIPT_P2SH_TEMPLATE = [ opcodes.OP_HASH160, PUBKEY_HASH_LENGTH, opcodes.OP_EQUAL ]

# Template to match a script that can never be redeemed, used in Namecoin.
SCRIPT_BURN_TEMPLATE = [ opcodes.OP_RETURN ]

SCRIPT_TYPE_INVALID = 0
SCRIPT_TYPE_UNKNOWN = 1
SCRIPT_TYPE_PUBKEY = 2
SCRIPT_TYPE_ADDRESS = 3
SCRIPT_TYPE_BURN = 4
SCRIPT_TYPE_MULTISIG = 5
SCRIPT_TYPE_P2SH = 6


class Chain(object):
    def __init__(chain, src=None, **kwargs):
        for attr in [
            'id', 'magic', 'name', 'code3', 'address_version', 'decimals', 'script_addr_vers']:

            if attr in kwargs:
                val = kwargs.get(attr)
            elif hasattr(chain, attr):
                continue
            elif src is not None:
                val = getattr(src, attr)
            else:
                val = None
            setattr(chain, attr, val)

    def has_feature(chain, feature):
        return False

    def ds_parse_block_header(chain, ds):
        return deserialize.parse_BlockHeader(ds)

    def ds_parse_transaction(chain, ds):
        return deserialize.parse_Transaction(ds)

    def ds_parse_block(chain, ds):
        d = chain.ds_parse_block_header(ds)
        d['transactions'] = []
        nTransactions = ds.read_compact_size()
        for i in xrange(nTransactions):
            d['transactions'].append(chain.ds_parse_transaction(ds))
        return d

    def ds_serialize_block(chain, ds, block):
        chain.ds_serialize_block_header(ds, block)
        ds.write_compact_size(len(block['transactions']))
        for tx in block['transactions']:
            chain.ds_serialize_transaction(ds, tx)

    def ds_serialize_block_header(chain, ds, block):
        ds.write_int32(block['version'])
        ds.write(block['hashPrev'])
        ds.write(block['hashMerkleRoot'])
        ds.write_uint32(block['nTime'])
        ds.write_uint32(block['nBits'])
        ds.write_uint32(block['nNonce'])

    def ds_serialize_transaction(chain, ds, tx):
        ds.write_int32(tx['version'])
        ds.write_compact_size(len(tx['txIn']))
        for txin in tx['txIn']:
            chain.ds_serialize_txin(ds, txin)
        ds.write_compact_size(len(tx['txOut']))
        for txout in tx['txOut']:
            chain.ds_serialize_txout(ds, txout)
        ds.write_uint32(tx['lockTime'])

    def ds_serialize_txin(chain, ds, txin):
        ds.write(txin['prevout_hash'])
        ds.write_uint32(txin['prevout_n'])
        ds.write_string(txin['scriptSig'])
        ds.write_uint32(txin['sequence'])

    def ds_serialize_txout(chain, ds, txout):
        ds.write_int64(txout['value'])
        ds.write_string(txout['scriptPubKey'])

    def serialize_block(chain, block):
        ds = BCDataStream.BCDataStream()
        chain.ds_serialize_block(ds, block)
        return ds.input

    def serialize_block_header(chain, block):
        ds = BCDataStream.BCDataStream()
        chain.ds_serialize_block_header(ds, block)
        return ds.input

    def serialize_transaction(chain, tx):
        ds = BCDataStream.BCDataStream()
        chain.ds_serialize_transaction(ds, tx)
        return ds.input

    def ds_block_header_hash(chain, ds):
        return chain.block_header_hash(
            ds.input[ds.read_cursor : ds.read_cursor + 80])

    def transaction_hash(chain, binary_tx):
        return util.double_sha256(binary_tx)

    def merkle_hash(chain, hashes):
        return util.double_sha256(hashes)

    # Based on CBlock::BuildMerkleTree().
    def merkle_root(chain, hashes):
        while len(hashes) > 1:
            size = len(hashes)
            out = []
            for i in xrange(0, size, 2):
                i2 = min(i + 1, size - 1)
                out.append(chain.merkle_hash(hashes[i] + hashes[i2]))
            hashes = out
        return hashes and hashes[0]

    def parse_block_header(chain, header):
        return chain.ds_parse_block_header(util.str_to_ds(header))

    def parse_transaction(chain, binary_tx):
        return chain.ds_parse_transaction(util.str_to_ds(binary_tx))

    def is_coinbase_tx(chain, tx):
        return len(tx['txIn']) == 1 and tx['txIn'][0]['prevout_hash'] == chain.coinbase_prevout_hash

    coinbase_prevout_hash = util.NULL_HASH
    coinbase_prevout_n = 0xffffffff
    genesis_hash_prev = util.GENESIS_HASH_PREV

    def parse_txout_script(chain, script):
        """
        Return TYPE, DATA where the format of DATA depends on TYPE.

        * SCRIPT_TYPE_INVALID  - DATA is the raw script
        * SCRIPT_TYPE_UNKNOWN  - DATA is the decoded script
        * SCRIPT_TYPE_PUBKEY   - DATA is the binary public key
        * SCRIPT_TYPE_ADDRESS  - DATA is the binary public key hash
        * SCRIPT_TYPE_BURN     - DATA is None
        * SCRIPT_TYPE_MULTISIG - DATA is {"m":M, "pubkeys":list_of_pubkeys}
        * SCRIPT_TYPE_P2SH     - DATA is the binary script hash
        """
        if script is None:
            raise ValueError()
        try:
            decoded = [ x for x in deserialize.script_GetOp(script) ]
        except Exception:
            return SCRIPT_TYPE_INVALID, script
        return chain.parse_decoded_txout_script(decoded)

    def parse_decoded_txout_script(chain, decoded):
        if deserialize.match_decoded(decoded, SCRIPT_ADDRESS_TEMPLATE):
            pubkey_hash = decoded[2][1]
            if len(pubkey_hash) == PUBKEY_HASH_LENGTH:
                return SCRIPT_TYPE_ADDRESS, pubkey_hash

        elif deserialize.match_decoded(decoded, SCRIPT_PUBKEY_TEMPLATE):
            pubkey = decoded[0][1]
            return SCRIPT_TYPE_PUBKEY, pubkey

        elif deserialize.match_decoded(decoded, SCRIPT_P2SH_TEMPLATE):
            script_hash = decoded[1][1]
            assert len(script_hash) == PUBKEY_HASH_LENGTH
            return SCRIPT_TYPE_P2SH, script_hash

        elif deserialize.match_decoded(decoded, SCRIPT_BURN_TEMPLATE):
            return SCRIPT_TYPE_BURN, None

        elif len(decoded) >= 4 and decoded[-1][0] == opcodes.OP_CHECKMULTISIG:
            # cf. bitcoin/src/script.cpp:Solver
            n = decoded[-2][0] + 1 - opcodes.OP_1
            m = decoded[0][0] + 1 - opcodes.OP_1
            if 1 <= m <= n <= MAX_MULTISIG_KEYS and len(decoded) == 3 + n and \
                    all([ decoded[i][0] <= opcodes.OP_PUSHDATA4 for i in range(1, 1+n) ]):
                return SCRIPT_TYPE_MULTISIG, \
                    { "m": m, "pubkeys": [ decoded[i][1] for i in range(1, 1+n) ] }

        # Namecoin overrides this to accept name operations.
        return SCRIPT_TYPE_UNKNOWN, decoded

    def pubkey_hash(chain, pubkey):
        return util.pubkey_to_hash(pubkey)

    def script_hash(chain, script):
        return chain.pubkey_hash(script)

    datadir_conf_file_name = "bitcoin.conf"
    datadir_rpcport = 8332

class Sha256Chain(Chain):
    def block_header_hash(chain, header):
        return util.double_sha256(header)

class Bitcoin(Sha256Chain):
    def __init__(chain, **kwargs):
        chain.name = 'Bitcoin'
        chain.code3 = 'BTC'
        chain.address_version = '\x00'
        chain.script_addr_vers = '\x05'
        chain.magic = '\xf9\xbe\xb4\xd9'
        Chain.__init__(chain, **kwargs)

class Testnet(Sha256Chain):
    def __init__(chain, **kwargs):
        chain.name = 'Testnet'
        chain.code3 = 'BC0'
        chain.address_version = '\x6f'
        chain.script_addr_vers = '\xc4'
        chain.magic = '\xfa\xbf\xb5\xda'
        Chain.__init__(chain, **kwargs)

    # XXX
    #datadir_conf_file_name = "bitcoin.conf"
    #datadir_rpcport = 8332

class NmcAuxPowChain(Chain):
    def __init__(chain, **kwargs):
        chain.block_version_bit_merge_mine = 8
        Chain.__init__(chain, **kwargs)

    def ds_parse_block_header(chain, ds):
        d = Chain.ds_parse_block_header(chain, ds)
        if d['version'] & (1 << 8):
            d['auxpow'] = deserialize.parse_AuxPow(ds)
        return d

    def has_feature(chain, feature):
        return feature == 'block_version_bit8_merge_mine'

class Sha256NmcAuxPowChain(Sha256Chain, NmcAuxPowChain):
    pass

class Namecoin(Sha256NmcAuxPowChain):
    def __init__(chain, **kwargs):
        chain.name = 'Namecoin'
        chain.code3 = 'NMC'
        chain.address_version = '\x34'
        chain.magic = '\xf9\xbe\xb4\xfe'
        Chain.__init__(chain, **kwargs)

    _drops = (opcodes.OP_NOP, opcodes.OP_DROP, opcodes.OP_2DROP)

    def parse_decoded_txout_script(chain, decoded):
        start = 0
        pushed = 0

        # Tolerate (but ignore for now) name operations.
        for i in xrange(len(decoded)):
            opcode = decoded[i][0]

            if decoded[i][1] is not None or \
                    opcode == opcodes.OP_0 or \
                    opcode == opcodes.OP_1NEGATE or \
                    (opcode >= opcodes.OP_1 and opcode <= opcodes.OP_16):
                pushed += 1
            elif opcode in chain._drops:
                to_drop = chain._drops.index(opcode)
                if pushed < to_drop:
                    break
                pushed -= to_drop
                start = i + 1
            else:
                return Chain.parse_decoded_txout_script(chain, decoded[start:])

        return SCRIPT_TYPE_UNKNOWN, decoded


    datadir_conf_file_name = "namecoin.conf"
    datadir_rpcport = 8336

class LtcScryptChain(Chain):
    def block_header_hash(chain, header):
        import ltc_scrypt
        return ltc_scrypt.getPoWHash(header)

class PpcPosChain(Chain):
    def ds_parse_transaction(chain, ds):
        return deserialize.parse_Transaction(ds, has_nTime=True)

    def ds_parse_block(chain, ds):
        d = Chain.ds_parse_block(chain, ds)
        d['block_sig'] = ds.read_bytes(ds.read_compact_size())
        return d

class NvcChain(LtcScryptChain, PpcPosChain):
    def has_feature(chain, feature):
        return feature == 'nvc_proof_of_stake'

class NovaCoin(NvcChain):
    def __init__(chain, **kwargs):
        chain.name = 'NovaCoin'
        chain.code3 = 'NVC'
        chain.address_version = "\x08"
        chain.magic = "\xe4\xe8\xe9\xe5"
        chain.decimals = 6
        Chain.__init__(chain, **kwargs)

    datadir_conf_file_name = "novacoin.conf"
    datadir_rpcport = 8344

class CryptoCash(NvcChain):
    def __init__(chain, **kwargs):
        chain.name = 'Cash'
        chain.code3 = 'CAS'
        chain.address_version = "\x22"
        chain.magic = "\xe4\xc6\xfe\xe7"
        Chain.__init__(chain, **kwargs)

    datadir_conf_file_name = "Cash.conf"
    datadir_rpcport = 3941

class X11Chain(Chain):
    def block_header_hash(chain, header):
        import xcoin_hash
        return xcoin_hash.getPoWHash(header)

class X11PosChain(X11Chain, PpcPosChain):
    pass

class Hirocoin(X11Chain):
    def __init__(chain, **kwargs):
        chain.name = 'Hirocoin'
        chain.code3 = 'HIRO'
        chain.address_version = '\x28'
        chain.script_addr_vers = '\x05'
        chain.magic = '\xfe\xc4\xb9\xde'
        Chain.__init__(chain, **kwargs)

    datadir_conf_file_name = 'hirocoin.conf'
    datadir_rpcport = 9347
    datadir_p2pport = 9348

YAC_START_TIME = 1377557832

class ScryptJaneChain(Chain):
    def block_header_hash(chain, header):
        import yac_scrypt
        b = chain.parse_block_header(header)
        return yac_scrypt.getPoWHash(header, b['nTime'] + YAC_START_TIME - chain.start_time)

class Bitleu(ScryptJaneChain, PpcPosChain):
    def __init__(chain, **kwargs):
        chain.name = 'Bitleu'
        chain.code3 = 'BTL'
        chain.address_version = "\x30"
        chain.script_addr_vers = '\x1b'
        chain.magic = "\xd9\xe6\xe7\xe5"
        chain.decimals = 6
        Chain.__init__(chain, **kwargs)

    datadir_conf_file_name = "Bitleu.conf"
    datadir_rpcport = 7997
    start_time = 1394480376

class KeccakChain(Chain):
    def block_header_hash(chain, header):
        return util.sha3_256(header)

class Maxcoin(KeccakChain):
    def __init__(chain, **kwargs):
        chain.name = 'Maxcoin'
        chain.code3 = 'MAX'
        chain.address_version = '\x6e'
        chain.script_addr_vers = '\x70'
        chain.magic = "\xf9\xbe\xbb\xd2"
        Chain.__init__(chain, **kwargs)

    def transaction_hash(chain, binary_tx):
        return util.sha256(binary_tx)

    datadir_conf_file_name = 'maxcoin.conf'
    datadir_rpcport = 8669

########NEW FILE########
__FILENAME__ = DataStore
# Copyright(C) 2011,2012,2013,2014 by Abe developers.

# DataStore.py: back end database access for Abe.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

# This module combines three functions that might be better split up:
# 1. Abe's schema
# 2. Abstraction over the schema for importing blocks, etc.
# 3. Code to load data by scanning blockfiles or using JSON-RPC.

import os
import re
import errno
import logging

import SqlAbstraction

import Chain

# bitcointools -- modified deserialize.py to return raw transaction
import BCDataStream
import deserialize
import util
import base58

SCHEMA_TYPE = "Abe"
SCHEMA_VERSION = SCHEMA_TYPE + "39"

CONFIG_DEFAULTS = {
    "dbtype":             None,
    "connect_args":       None,
    "binary_type":        None,
    "int_type":           None,
    "upgrade":            None,
    "rescan":             None,
    "commit_bytes":       None,
    "log_sql":            None,
    "log_rpc":            None,
    "datadir":            None,
    "ignore_bit8_chains": None,
    "use_firstbits":      False,
    "keep_scriptsig":     True,
    "import_tx":          [],
    "default_loader":     "default",
}

WORK_BITS = 304  # XXX more than necessary.

CHAIN_CONFIG = [
    {"chain":"Bitcoin"},
    {"chain":"Testnet"},
    {"chain":"Namecoin"},
    {"chain":"Weeds", "network":"Weedsnet",
     "code3":"WDS", "address_version":"\xf3", "magic":"\xf8\xbf\xb5\xda"},
    {"chain":"BeerTokens",
     "code3":"BER", "address_version":"\xf2", "magic":"\xf7\xbf\xb5\xdb"},
    {"chain":"SolidCoin",
     "code3":"SCN", "address_version":"\x7d", "magic":"\xde\xad\xba\xbe"},
    {"chain":"ScTestnet",
     "code3":"SC0", "address_version":"\x6f", "magic":"\xca\xfe\xba\xbe"},
    {"chain":"Worldcoin",
     "code3":"WDC", "address_version":"\x49", "magic":"\xfb\xc0\xb6\xdb"},
    {"chain":"NovaCoin"},
    {"chain":"CryptoCash"},
    {"chain":"Anoncoin","code3":"ANC", "address_version":"\u0017", "magic":"\xFA\xCA\xBA\xDA" },
    {"chain":"Hirocoin"},
    {"chain":"Bitleu"},
    {"chain":"Maxcoin"},
    #{"chain":"",
    # "code3":"", "address_version":"\x", "magic":""},
    ]

NULL_PUBKEY_HASH = "\0" * Chain.PUBKEY_HASH_LENGTH
NULL_PUBKEY_ID = 0
PUBKEY_ID_NETWORK_FEE = NULL_PUBKEY_ID

# Size of the script and pubkey columns in bytes.
MAX_SCRIPT = 1000000
MAX_PUBKEY = 65

NO_CLOB = 'BUG_NO_CLOB'

# XXX This belongs in another module.
class InvalidBlock(Exception):
    pass
class MerkleRootMismatch(InvalidBlock):
    def __init__(ex, block_hash, tx_hashes):
        ex.block_hash = block_hash
        ex.tx_hashes = tx_hashes
    def __str__(ex):
        return 'Block header Merkle root does not match its transactions. ' \
            'block hash=%s' % (ex.block_hash[::-1].encode('hex'),)

class MalformedHash(ValueError):
    pass

class MalformedAddress(ValueError):
    pass

class DataStore(object):

    """
    Bitcoin data storage class based on DB-API 2 and standard SQL with
    workarounds to support SQLite3, PostgreSQL/psycopg2, MySQL,
    Oracle, ODBC, and IBM DB2.
    """

    def __init__(store, args):
        """
        Open and store a connection to the SQL database.

        args.dbtype should name a DB-API 2 driver module, e.g.,
        "sqlite3".

        args.connect_args should be an argument to the module's
        connect() method, or None for no argument, or a list of
        arguments, or a dictionary of named arguments.

        args.datadir names Bitcoin data directories containing
        blk0001.dat to scan for new blocks.
        """
        if args.datadir is None:
            args.datadir = util.determine_db_dir()
        if isinstance(args.datadir, str):
            args.datadir = [args.datadir]

        store.args = args
        store.log = logging.getLogger(__name__)

        store.rpclog = logging.getLogger(__name__ + ".rpc")
        if not args.log_rpc:
            store.rpclog.setLevel(logging.ERROR)

        if args.dbtype is None:
            store.log.warn("dbtype not configured, see abe.conf for examples");
            store.dbmodule = None
            store.config = CONFIG_DEFAULTS.copy()
            store.datadirs = []
            store.use_firstbits = CONFIG_DEFAULTS['use_firstbits']
            store._sql = None
            return
        store.dbmodule = __import__(args.dbtype)

        sql_args = lambda: 1
        sql_args.module = store.dbmodule
        sql_args.connect_args = args.connect_args
        sql_args.binary_type = args.binary_type
        sql_args.int_type = args.int_type
        sql_args.log_sql = args.log_sql
        sql_args.prefix = "abe_"
        sql_args.config = {}
        store.sql_args = sql_args
        store.set_db(None)
        store.init_sql()

        store._blocks = {}

        # Read the CONFIG and CONFIGVAR tables if present.
        store.config = store._read_config()

        if store.config is None:
            store.keep_scriptsig = args.keep_scriptsig
        elif 'keep_scriptsig' in store.config:
            store.keep_scriptsig = store.config.get('keep_scriptsig') == "true"
        else:
            store.keep_scriptsig = CONFIG_DEFAULTS['keep_scriptsig']

        store.refresh_ddl()

        if store.config is None:
            store.initialize()
        else:
            store.init_sql()

            if store.config['schema_version'] == SCHEMA_VERSION:
                pass
            elif args.upgrade:
                import upgrade
                upgrade.upgrade_schema(store)
            else:
                raise Exception(
                    "Database schema version (%s) does not match software"
                    " (%s).  Please run with --upgrade to convert database."
                    % (store.config['schema_version'], SCHEMA_VERSION))
        store._sql.auto_reconnect = True

        if args.rescan:
            store.sql("UPDATE datadir SET blkfile_number=1, blkfile_offset=0")

        store._init_datadirs()
        store.init_chains()

        store.commit_bytes = args.commit_bytes
        if store.commit_bytes is None:
            store.commit_bytes = 0  # Commit whenever possible.
        else:
            store.commit_bytes = int(store.commit_bytes)
        store.bytes_since_commit = 0

        store.use_firstbits = (store.config['use_firstbits'] == "true")

        for hex_tx in args.import_tx:
            chain_name = None
            if isinstance(hex_tx, dict):
                chain_name = hex_tx.get("chain")
                hex_tx = hex_tx.get("tx")
            store.maybe_import_binary_tx(chain_name, str(hex_tx).decode('hex'))

        store.default_loader = args.default_loader

        store.commit()

    def set_db(store, db):
        store._sql = db

    def get_db(store):
        return store._sql

    def connect(store):
        return store._sql.connect()

    def reconnect(store):
        return store._sql.reconnect()

    def close(store):
        store._sql.close()

    def commit(store):
        store._sql.commit()

    def rollback(store):
        if store._sql is not None:
            store._sql.rollback()

    def sql(store, stmt, params=()):
        store._sql.sql(stmt, params)

    def ddl(store, stmt):
        store._sql.ddl(stmt)

    def selectrow(store, stmt, params=()):
        return store._sql.selectrow(stmt, params)

    def selectall(store, stmt, params=()):
        return store._sql.selectall(stmt, params)

    def rowcount(store):
        return store._sql.rowcount()

    def create_sequence(store, key):
        store._sql.create_sequence(key)

    def drop_sequence(store, key):
        store._sql.drop_sequence(key)

    def new_id(store, key):
        return store._sql.new_id(key)

    def init_sql(store):
        sql_args = store.sql_args
        if hasattr(store, 'config'):
            for name in store.config.keys():
                if name.startswith('sql.'):
                    sql_args.config[name[len('sql.'):]] = store.config[name]
        if store._sql:
            store._sql.close()  # XXX Could just set_flavour.
        store.set_db(SqlAbstraction.SqlAbstraction(sql_args))
        store.init_binfuncs()

    def init_binfuncs(store):
        store.binin       = store._sql.binin
        store.binin_hex   = store._sql.binin_hex
        store.binin_int   = store._sql.binin_int
        store.binout      = store._sql.binout
        store.binout_hex  = store._sql.binout_hex
        store.binout_int  = store._sql.binout_int
        store.intin       = store._sql.intin
        store.hashin      = store._sql.revin
        store.hashin_hex  = store._sql.revin_hex
        store.hashout     = store._sql.revout
        store.hashout_hex = store._sql.revout_hex

    def _read_config(store):
        # Read table CONFIGVAR if it exists.
        config = {}
        try:
            for name, value in store.selectall("""
                SELECT configvar_name, configvar_value
                  FROM configvar"""):
                config[name] = '' if value is None else value
            if config:
                return config

        except store.dbmodule.DatabaseError:
            try:
                store.rollback()
            except Exception:
                pass

        # Read legacy table CONFIG if it exists.
        try:
            row = store.selectrow("""
                SELECT schema_version, binary_type
                  FROM config
                 WHERE config_id = 1""")
            sv, btype = row
            return { 'schema_version': sv, 'binary_type': btype }
        except Exception:
            try:
                store.rollback()
            except Exception:
                pass

        # Return None to indicate no schema found.
        return None

    def _init_datadirs(store):
        """Parse store.args.datadir, create store.datadirs."""
        if store.args.datadir == []:
            store.datadirs = []
            return

        datadirs = {}
        for row in store.selectall("""
            SELECT datadir_id, dirname, blkfile_number, blkfile_offset,
                   chain_id
              FROM datadir"""):
            id, dir, num, offs, chain_id = row
            datadirs[dir] = {
                "id": id,
                "dirname": dir,
                "blkfile_number": int(num),
                "blkfile_offset": int(offs),
                "chain_id": None if chain_id is None else int(chain_id),
                "loader": None}

        #print("datadirs: %r" % datadirs)

        # By default, scan every dir we know.  This doesn't happen in
        # practise, because abe.py sets ~/.bitcoin as default datadir.
        if store.args.datadir is None:
            store.datadirs = datadirs.values()
            return

        def lookup_chain_id(name):
            row = store.selectrow(
                "SELECT chain_id FROM chain WHERE chain_name = ?",
                (name,))
            return None if row is None else int(row[0])

        store.datadirs = []
        for dircfg in store.args.datadir:
            loader = None
            conf = None

            if isinstance(dircfg, dict):
                #print("dircfg is dict: %r" % dircfg)  # XXX
                dirname = dircfg.get('dirname')
                if dirname is None:
                    raise ValueError(
                        'Missing dirname in datadir configuration: '
                        + str(dircfg))
                if dirname in datadirs:
                    d = datadirs[dirname]
                    d['loader'] = dircfg.get('loader')
                    d['conf'] = dircfg.get('conf')
                    if d['chain_id'] is None and 'chain' in dircfg:
                        d['chain_id'] = lookup_chain_id(dircfg['chain'])
                    store.datadirs.append(d)
                    continue

                loader = dircfg.get('loader')
                conf = dircfg.get('conf')
                chain_id = dircfg.get('chain_id')
                if chain_id is None:
                    chain_name = dircfg.get('chain')
                    chain_id = lookup_chain_id(chain_name)

                    if chain_id is None and chain_name is not None:
                        chain_id = store.new_id('chain')

                        code3 = dircfg.get('code3')
                        if code3 is None:
                            # XXX Should default via policy.
                            code3 = '000' if chain_id > 999 else "%03d" % (
                                chain_id,)

                        addr_vers = dircfg.get('address_version')
                        if addr_vers is None:
                            addr_vers = "\0"
                        elif isinstance(addr_vers, unicode):
                            addr_vers = addr_vers.encode('latin_1')

                        script_addr_vers = dircfg.get('script_addr_vers')
                        if script_addr_vers is None:
                            script_addr_vers = "\x05"
                        elif isinstance(script_addr_vers, unicode):
                            script_addr_vers = script_addr_vers.encode('latin_1')

                        decimals = dircfg.get('decimals')
                        if decimals is not None:
                            decimals = int(decimals)

                        # XXX Could do chain_magic, but this datadir won't
                        # use it, because it knows its chain.

                        store.sql("""
                            INSERT INTO chain (
                                chain_id, chain_name, chain_code3,
                                chain_address_version, chain_script_addr_vers, chain_policy,
                                chain_decimals
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                  (chain_id, chain_name, code3,
                                   store.binin(addr_vers), store.binin(script_addr_vers),
                                   dircfg.get('policy', chain_name), decimals))
                        store.commit()
                        store.log.warning("Assigned chain_id %d to %s",
                                          chain_id, chain_name)

            elif dircfg in datadirs:
                store.datadirs.append(datadirs[dircfg])
                continue
            else:
                # Not a dict.  A string naming a directory holding
                # standard chains.
                dirname = dircfg
                chain_id = None

            d = {
                "id": store.new_id("datadir"),
                "dirname": dirname,
                "blkfile_number": 1,
                "blkfile_offset": 0,
                "chain_id": chain_id,
                "loader": loader,
                "conf": conf,
                }
            store.datadirs.append(d)

    def init_chains(store):
        store.chains_by = lambda: 0
        store.chains_by.id = {}
        store.chains_by.name = {}
        store.chains_by.magic = {}

        # Legacy config option.
        no_bit8_chains = store.args.ignore_bit8_chains or []
        if isinstance(no_bit8_chains, str):
            no_bit8_chains = [no_bit8_chains]

        for chain_id, magic, chain_name, chain_code3, address_version, script_addr_vers, \
                chain_policy, chain_decimals in \
                store.selectall("""
                    SELECT chain_id, chain_magic, chain_name, chain_code3,
                           chain_address_version, chain_script_addr_vers, chain_policy, chain_decimals
                      FROM chain
                """):
            chain = Chain.create(
                id              = int(chain_id),
                magic           = store.binout(magic),
                name            = unicode(chain_name),
                code3           = chain_code3 and unicode(chain_code3),
                address_version = store.binout(address_version),
                script_addr_vers = store.binout(script_addr_vers),
                policy          = unicode(chain_policy),
                decimals        = None if chain_decimals is None else \
                    int(chain_decimals))

            # Legacy config option.
            if chain.name in no_bit8_chains and \
                    chain.has_feature('block_version_bit8_merge_mine'):
                chain = Chain.create(src=chain, policy="LegacyNoBit8")

            store.chains_by.id[chain.id] = chain
            store.chains_by.name[chain.name] = chain
            store.chains_by.magic[bytes(chain.magic)] = chain

    def get_chain_by_id(store, chain_id):
        return store.chains_by.id[int(chain_id)]

    def get_chain_by_name(store, name):
        return store.chains_by.name.get(name, None)

    def get_default_chain(store):
        store.log.debug("Falling back to default (Bitcoin) policy.")
        return Chain.create(None)

    def get_ddl(store, key):
        return store._ddl[key]

    def refresh_ddl(store):
        store._ddl = {
            "chain_summary":
# XXX I could do a lot with MATERIALIZED views.
"""CREATE VIEW chain_summary AS SELECT
    cc.chain_id,
    cc.in_longest,
    b.block_id,
    b.block_hash,
    b.block_version,
    b.block_hashMerkleRoot,
    b.block_nTime,
    b.block_nBits,
    b.block_nNonce,
    cc.block_height,
    b.prev_block_id,
    prev.block_hash prev_block_hash,
    b.block_chain_work,
    b.block_num_tx,
    b.block_value_in,
    b.block_value_out,
    b.block_total_satoshis,
    b.block_total_seconds,
    b.block_satoshi_seconds,
    b.block_total_ss,
    b.block_ss_destroyed
FROM chain_candidate cc
JOIN block b ON (cc.block_id = b.block_id)
LEFT JOIN block prev ON (b.prev_block_id = prev.block_id)""",

            "txout_detail":
"""CREATE VIEW txout_detail AS SELECT
    cc.chain_id,
    cc.in_longest,
    cc.block_id,
    b.block_hash,
    b.block_height,
    block_tx.tx_pos,
    tx.tx_id,
    tx.tx_hash,
    tx.tx_lockTime,
    tx.tx_version,
    tx.tx_size,
    txout.txout_id,
    txout.txout_pos,
    txout.txout_value,
    txout.txout_scriptPubKey,
    pubkey.pubkey_id,
    pubkey.pubkey_hash,
    pubkey.pubkey
  FROM chain_candidate cc
  JOIN block b ON (cc.block_id = b.block_id)
  JOIN block_tx ON (b.block_id = block_tx.block_id)
  JOIN tx    ON (tx.tx_id = block_tx.tx_id)
  JOIN txout ON (tx.tx_id = txout.tx_id)
  LEFT JOIN pubkey ON (txout.pubkey_id = pubkey.pubkey_id)""",

            "txin_detail":
"""CREATE VIEW txin_detail AS SELECT
    cc.chain_id,
    cc.in_longest,
    cc.block_id,
    b.block_hash,
    b.block_height,
    block_tx.tx_pos,
    tx.tx_id,
    tx.tx_hash,
    tx.tx_lockTime,
    tx.tx_version,
    tx.tx_size,
    txin.txin_id,
    txin.txin_pos,
    txin.txout_id prevout_id""" + (""",
    txin.txin_scriptSig,
    txin.txin_sequence""" if store.keep_scriptsig else """,
    NULL txin_scriptSig,
    NULL txin_sequence""") + """,
    prevout.txout_value txin_value,
    prevout.txout_scriptPubKey txin_scriptPubKey,
    pubkey.pubkey_id,
    pubkey.pubkey_hash,
    pubkey.pubkey
  FROM chain_candidate cc
  JOIN block b ON (cc.block_id = b.block_id)
  JOIN block_tx ON (b.block_id = block_tx.block_id)
  JOIN tx    ON (tx.tx_id = block_tx.tx_id)
  JOIN txin  ON (tx.tx_id = txin.tx_id)
  LEFT JOIN txout prevout ON (txin.txout_id = prevout.txout_id)
  LEFT JOIN pubkey
      ON (prevout.pubkey_id = pubkey.pubkey_id)""",

            "txout_approx":
# View of txout for drivers like sqlite3 that can not handle large
# integer arithmetic.  For them, we transform the definition of
# txout_approx_value to DOUBLE PRECISION (approximate) by a CAST.
"""CREATE VIEW txout_approx AS SELECT
    txout_id,
    tx_id,
    txout_value txout_approx_value
  FROM txout""",

            "configvar":
# ABE accounting.  This table is read without knowledge of the
# database's SQL quirks, so it must use only the most widely supported
# features.
"""CREATE TABLE configvar (
    configvar_name  VARCHAR(100) NOT NULL PRIMARY KEY,
    configvar_value VARCHAR(255)
)""",

            "abe_sequences":
"""CREATE TABLE abe_sequences (
    sequence_key VARCHAR(100) NOT NULL PRIMARY KEY,
    nextid NUMERIC(30)
)""",
            }

    def initialize(store):
        """
        Create the database schema.
        """
        store.config = {}
        store.configure()

        for stmt in (

store._ddl['configvar'],

"""CREATE TABLE datadir (
    datadir_id  NUMERIC(10) NOT NULL PRIMARY KEY,
    dirname     VARCHAR(2000) NOT NULL,
    blkfile_number NUMERIC(8) NULL,
    blkfile_offset NUMERIC(20) NULL,
    chain_id    NUMERIC(10) NULL
)""",

# A block of the type used by Bitcoin.
"""CREATE TABLE block (
    block_id      NUMERIC(14) NOT NULL PRIMARY KEY,
    block_hash    BINARY(32)  UNIQUE NOT NULL,
    block_version NUMERIC(10),
    block_hashMerkleRoot BINARY(32),
    block_nTime   NUMERIC(20),
    block_nBits   NUMERIC(10),
    block_nNonce  NUMERIC(10),
    block_height  NUMERIC(14) NULL,
    prev_block_id NUMERIC(14) NULL,
    search_block_id NUMERIC(14) NULL,
    block_chain_work BINARY(""" + str(WORK_BITS / 8) + """),
    block_value_in NUMERIC(30) NULL,
    block_value_out NUMERIC(30),
    block_total_satoshis NUMERIC(26) NULL,
    block_total_seconds NUMERIC(20) NULL,
    block_satoshi_seconds NUMERIC(28) NULL,
    block_total_ss NUMERIC(28) NULL,
    block_num_tx  NUMERIC(10) NOT NULL,
    block_ss_destroyed NUMERIC(28) NULL,
    FOREIGN KEY (prev_block_id)
        REFERENCES block (block_id),
    FOREIGN KEY (search_block_id)
        REFERENCES block (block_id)
)""",

# CHAIN comprises a magic number, a policy, and (indirectly via
# CHAIN_LAST_BLOCK_ID and the referenced block's ancestors) a genesis
# block, possibly null.  A chain may have a currency code.
"""CREATE TABLE chain (
    chain_id    NUMERIC(10) NOT NULL PRIMARY KEY,
    chain_name  VARCHAR(100) UNIQUE NOT NULL,
    chain_code3 VARCHAR(4)  NULL,
    chain_address_version VARBINARY(100) NOT NULL,
    chain_script_addr_vers VARBINARY(100) NULL,
    chain_magic BINARY(4)     NULL,
    chain_policy VARCHAR(255) NOT NULL,
    chain_decimals NUMERIC(2) NULL,
    chain_last_block_id NUMERIC(14) NULL,
    FOREIGN KEY (chain_last_block_id)
        REFERENCES block (block_id)
)""",

# CHAIN_CANDIDATE lists blocks that are, or might become, part of the
# given chain.  IN_LONGEST is 1 when the block is in the chain, else 0.
# IN_LONGEST denormalizes information stored canonically in
# CHAIN.CHAIN_LAST_BLOCK_ID and BLOCK.PREV_BLOCK_ID.
"""CREATE TABLE chain_candidate (
    chain_id      NUMERIC(10) NOT NULL,
    block_id      NUMERIC(14) NOT NULL,
    in_longest    NUMERIC(1),
    block_height  NUMERIC(14),
    PRIMARY KEY (chain_id, block_id),
    FOREIGN KEY (block_id) REFERENCES block (block_id)
)""",
"""CREATE INDEX x_cc_block ON chain_candidate (block_id)""",
"""CREATE INDEX x_cc_chain_block_height
    ON chain_candidate (chain_id, block_height)""",
"""CREATE INDEX x_cc_block_height ON chain_candidate (block_height)""",

# An orphan block must remember its hashPrev.
"""CREATE TABLE orphan_block (
    block_id      NUMERIC(14) NOT NULL PRIMARY KEY,
    block_hashPrev BINARY(32) NOT NULL,
    FOREIGN KEY (block_id) REFERENCES block (block_id)
)""",
"""CREATE INDEX x_orphan_block_hashPrev ON orphan_block (block_hashPrev)""",

# Denormalize the relationship inverse to BLOCK.PREV_BLOCK_ID.
"""CREATE TABLE block_next (
    block_id      NUMERIC(14) NOT NULL,
    next_block_id NUMERIC(14) NOT NULL,
    PRIMARY KEY (block_id, next_block_id),
    FOREIGN KEY (block_id) REFERENCES block (block_id),
    FOREIGN KEY (next_block_id) REFERENCES block (block_id)
)""",

# A transaction of the type used by Bitcoin.
"""CREATE TABLE tx (
    tx_id         NUMERIC(26) NOT NULL PRIMARY KEY,
    tx_hash       BINARY(32)  UNIQUE NOT NULL,
    tx_version    NUMERIC(10),
    tx_lockTime   NUMERIC(10),
    tx_size       NUMERIC(10)
)""",

# Presence of transactions in blocks is many-to-many.
"""CREATE TABLE block_tx (
    block_id      NUMERIC(14) NOT NULL,
    tx_id         NUMERIC(26) NOT NULL,
    tx_pos        NUMERIC(10) NOT NULL,
    PRIMARY KEY (block_id, tx_id),
    UNIQUE (block_id, tx_pos),
    FOREIGN KEY (block_id)
        REFERENCES block (block_id),
    FOREIGN KEY (tx_id)
        REFERENCES tx (tx_id)
)""",
"""CREATE INDEX x_block_tx_tx ON block_tx (tx_id)""",

# A public key for sending bitcoins.  PUBKEY_HASH is derivable from a
# Bitcoin or Testnet address.
"""CREATE TABLE pubkey (
    pubkey_id     NUMERIC(26) NOT NULL PRIMARY KEY,
    pubkey_hash   BINARY(20)  UNIQUE NOT NULL,
    pubkey        VARBINARY(""" + str(MAX_PUBKEY) + """) NULL
)""",

"""CREATE TABLE multisig_pubkey (
    multisig_id   NUMERIC(26) NOT NULL,
    pubkey_id     NUMERIC(26) NOT NULL,
    PRIMARY KEY (multisig_id, pubkey_id),
    FOREIGN KEY (multisig_id) REFERENCES pubkey (pubkey_id),
    FOREIGN KEY (pubkey_id) REFERENCES pubkey (pubkey_id)
)""",
"""CREATE INDEX x_multisig_pubkey_pubkey ON multisig_pubkey (pubkey_id)""",

# A transaction out-point.
"""CREATE TABLE txout (
    txout_id      NUMERIC(26) NOT NULL PRIMARY KEY,
    tx_id         NUMERIC(26) NOT NULL,
    txout_pos     NUMERIC(10) NOT NULL,
    txout_value   NUMERIC(30) NOT NULL,
    txout_scriptPubKey VARBINARY(""" + str(MAX_SCRIPT) + """),
    pubkey_id     NUMERIC(26),
    UNIQUE (tx_id, txout_pos),
    FOREIGN KEY (pubkey_id)
        REFERENCES pubkey (pubkey_id)
)""",
"""CREATE INDEX x_txout_pubkey ON txout (pubkey_id)""",

# A transaction in-point.
"""CREATE TABLE txin (
    txin_id       NUMERIC(26) NOT NULL PRIMARY KEY,
    tx_id         NUMERIC(26) NOT NULL,
    txin_pos      NUMERIC(10) NOT NULL,
    txout_id      NUMERIC(26)""" + (""",
    txin_scriptSig VARBINARY(""" + str(MAX_SCRIPT) + """),
    txin_sequence NUMERIC(10)""" if store.keep_scriptsig else "") + """,
    UNIQUE (tx_id, txin_pos),
    FOREIGN KEY (tx_id)
        REFERENCES tx (tx_id)
)""",
"""CREATE INDEX x_txin_txout ON txin (txout_id)""",

# While TXIN.TXOUT_ID can not be found, we must remember TXOUT_POS,
# a.k.a. PREVOUT_N.
"""CREATE TABLE unlinked_txin (
    txin_id       NUMERIC(26) NOT NULL PRIMARY KEY,
    txout_tx_hash BINARY(32)  NOT NULL,
    txout_pos     NUMERIC(10) NOT NULL,
    FOREIGN KEY (txin_id) REFERENCES txin (txin_id)
)""",
"""CREATE INDEX x_unlinked_txin_outpoint
    ON unlinked_txin (txout_tx_hash, txout_pos)""",

"""CREATE TABLE block_txin (
    block_id      NUMERIC(14) NOT NULL,
    txin_id       NUMERIC(26) NOT NULL,
    out_block_id  NUMERIC(14) NOT NULL,
    PRIMARY KEY (block_id, txin_id),
    FOREIGN KEY (block_id) REFERENCES block (block_id),
    FOREIGN KEY (txin_id) REFERENCES txin (txin_id),
    FOREIGN KEY (out_block_id) REFERENCES block (block_id)
)""",

store._ddl['chain_summary'],
store._ddl['txout_detail'],
store._ddl['txin_detail'],
store._ddl['txout_approx'],

"""CREATE TABLE abe_lock (
    lock_id       NUMERIC(10) NOT NULL PRIMARY KEY,
    pid           VARCHAR(255) NULL
)""",
):
            try:
                store.ddl(stmt)
            except Exception:
                store.log.error("Failed: %s", stmt)
                raise

        for key in ['chain', 'datadir',
                    'tx', 'txout', 'pubkey', 'txin', 'block']:
            store.create_sequence(key)

        store.sql("INSERT INTO abe_lock (lock_id) VALUES (1)")

        # Insert some well-known chain metadata.
        for conf in CHAIN_CONFIG:
            conf = conf.copy()
            conf["name"] = conf.pop("chain")

            chain = Chain.create(policy=conf["name"], **conf)
            store.insert_chain(chain)

        store.sql("""
            INSERT INTO pubkey (pubkey_id, pubkey_hash) VALUES (?, ?)""",
                  (NULL_PUBKEY_ID, store.binin(NULL_PUBKEY_HASH)))

        if store.args.use_firstbits:
            store.config['use_firstbits'] = "true"
            store.ddl(
                """CREATE TABLE abe_firstbits (
                    pubkey_id       NUMERIC(26) NOT NULL,
                    block_id        NUMERIC(14) NOT NULL,
                    address_version VARBINARY(10) NOT NULL,
                    firstbits       VARCHAR(50) NOT NULL,
                    PRIMARY KEY (address_version, pubkey_id, block_id),
                    FOREIGN KEY (pubkey_id) REFERENCES pubkey (pubkey_id),
                    FOREIGN KEY (block_id) REFERENCES block (block_id)
                )""")
            store.ddl(
                """CREATE INDEX x_abe_firstbits
                    ON abe_firstbits (address_version, firstbits)""")
        else:
            store.config['use_firstbits'] = "false"

        store.config['keep_scriptsig'] = \
            "true" if store.args.keep_scriptsig else "false"

        store.save_config()
        store.commit()

    def insert_chain(store, chain):
        chain.id = store.new_id("chain")
        store.sql("""
            INSERT INTO chain (
                chain_id, chain_magic, chain_name, chain_code3,
                chain_address_version, chain_script_addr_vers, chain_policy, chain_decimals
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (chain.id, store.binin(chain.magic), chain.name,
                   chain.code3, store.binin(chain.address_version), store.binin(chain.script_addr_vers),
                   chain.name, chain.decimals))

    def get_lock(store):
        if store.version_below('Abe26'):
            return None
        conn = store.connect()
        cur = conn.cursor()
        cur.execute("UPDATE abe_lock SET pid = %d WHERE lock_id = 1"
                    % (os.getpid(),))
        if cur.rowcount != 1:
            raise Exception("unexpected rowcount")
        cur.close()

        # Check whether database supports concurrent updates.  Where it
        # doesn't (SQLite) we get exclusive access automatically.
        try:
            import random
            letters = "".join([chr(random.randint(65, 90)) for x in xrange(10)])
            store.sql("""
                INSERT INTO configvar (configvar_name, configvar_value)
                VALUES (?, ?)""",
                      ("upgrade-lock-" + letters, 'x'))
        except Exception:
            store.release_lock(conn)
            conn = None

        store.rollback()

        # XXX Should reread config.

        return conn

    def release_lock(store, conn):
        if conn:
            conn.rollback()
            conn.close()

    def version_below(store, vers):
        try:
            sv = float(store.config['schema_version'].replace(SCHEMA_TYPE, ''))
        except ValueError:
            return False
        vers = float(vers.replace(SCHEMA_TYPE, ''))
        return sv < vers

    def configure(store):
        config = store._sql.configure()
        store.init_binfuncs()
        for name in config.keys():
            store.config['sql.' + name] = config[name]

    def save_config(store):
        store.config['schema_version'] = SCHEMA_VERSION
        for name in store.config.keys():
            store.save_configvar(name)

    def save_configvar(store, name):
        store.sql("UPDATE configvar SET configvar_value = ?"
                  " WHERE configvar_name = ?", (store.config[name], name))
        if store.rowcount() == 0:
            store.sql("INSERT INTO configvar (configvar_name, configvar_value)"
                      " VALUES (?, ?)", (name, store.config[name]))

    def set_configvar(store, name, value):
        store.config[name] = value
        store.save_configvar(name)

    def cache_block(store, block_id, height, prev_id, search_id):
        assert isinstance(block_id, int), block_id
        assert isinstance(height, int), height
        assert prev_id is None or isinstance(prev_id, int)
        assert search_id is None or isinstance(search_id, int)
        block = {
            'height':    height,
            'prev_id':   prev_id,
            'search_id': search_id}
        store._blocks[block_id] = block
        return block

    def _load_block(store, block_id):
        block = store._blocks.get(block_id)
        if block is None:
            row = store.selectrow("""
                SELECT block_height, prev_block_id, search_block_id
                  FROM block
                 WHERE block_id = ?""", (block_id,))
            if row is None:
                return None
            height, prev_id, search_id = row
            block = store.cache_block(
                block_id, int(height),
                None if prev_id is None else int(prev_id),
                None if search_id is None else int(search_id))
        return block

    def get_block_id_at_height(store, height, descendant_id):
        if height is None:
            return None
        while True:
            block = store._load_block(descendant_id)
            if block['height'] == height:
                return descendant_id
            descendant_id = block[
                'search_id'
                if util.get_search_height(block['height']) >= height else
                'prev_id']

    def is_descended_from(store, block_id, ancestor_id):
#        ret = store._is_descended_from(block_id, ancestor_id)
#        store.log.debug("%d is%s descended from %d", block_id, '' if ret else ' NOT', ancestor_id)
#        return ret
#    def _is_descended_from(store, block_id, ancestor_id):
        block = store._load_block(block_id)
        ancestor = store._load_block(ancestor_id)
        height = ancestor['height']
        return block['height'] >= height and \
            store.get_block_id_at_height(height, block_id) == ancestor_id

    def get_block_height(store, block_id):
        return store._load_block(int(block_id))['height']

    def find_prev(store, hash):
        row = store.selectrow("""
            SELECT block_id, block_height, block_chain_work,
                   block_total_satoshis, block_total_seconds,
                   block_satoshi_seconds, block_total_ss, block_nTime
              FROM block
             WHERE block_hash=?""", (store.hashin(hash),))
        if row is None:
            return (None, None, None, None, None, None, None, None)
        (id, height, chain_work, satoshis, seconds, satoshi_seconds,
         total_ss, nTime) = row
        return (id, None if height is None else int(height),
                store.binout_int(chain_work),
                None if satoshis is None else int(satoshis),
                None if seconds is None else int(seconds),
                None if satoshi_seconds is None else int(satoshi_seconds),
                None if total_ss is None else int(total_ss),
                int(nTime))

    def import_block(store, b, chain_ids=None, chain=None):

        # Import new transactions.

        if chain_ids is None:
            chain_ids = frozenset() if chain is None else frozenset([chain.id])

        b['value_in'] = 0
        b['value_out'] = 0
        b['value_destroyed'] = 0
        tx_hash_array = []

        # In the common case, all the block's txins _are_ linked, and we
        # can avoid a query if we notice this.
        all_txins_linked = True

        for pos in xrange(len(b['transactions'])):
            tx = b['transactions'][pos]

            if 'hash' not in tx:
                if chain is None:
                    store.log.debug("Falling back to SHA256 transaction hash")
                    tx['hash'] = util.double_sha256(tx['__data__'])
                else:
                    tx['hash'] = chain.transaction_hash(tx['__data__'])

            tx_hash_array.append(tx['hash'])
            tx['tx_id'] = store.tx_find_id_and_value(tx, pos == 0)

            if tx['tx_id']:
                all_txins_linked = False
            else:
                if store.commit_bytes == 0:
                    tx['tx_id'] = store.import_and_commit_tx(tx, pos == 0, chain)
                else:
                    tx['tx_id'] = store.import_tx(tx, pos == 0, chain)
                if tx.get('unlinked_count', 1) > 0:
                    all_txins_linked = False

            if tx['value_in'] is None:
                b['value_in'] = None
            elif b['value_in'] is not None:
                b['value_in'] += tx['value_in']
            b['value_out'] += tx['value_out']
            b['value_destroyed'] += tx['value_destroyed']

        # Get a new block ID.
        block_id = int(store.new_id("block"))
        b['block_id'] = block_id

        if chain is not None:
            # Verify Merkle root.
            if b['hashMerkleRoot'] != chain.merkle_root(tx_hash_array):
                raise MerkleRootMismatch(b['hash'], tx_hash_array)

        # Look for the parent block.
        hashPrev = b['hashPrev']
        if chain is None:
            # XXX No longer used.
            is_genesis = hashPrev == util.GENESIS_HASH_PREV
        else:
            is_genesis = hashPrev == chain.genesis_hash_prev

        (prev_block_id, prev_height, prev_work, prev_satoshis,
         prev_seconds, prev_ss, prev_total_ss, prev_nTime) = (
            (None, -1, 0, 0, 0, 0, 0, b['nTime'])
            if is_genesis else
            store.find_prev(hashPrev))

        b['prev_block_id'] = prev_block_id
        b['height'] = None if prev_height is None else prev_height + 1
        b['chain_work'] = util.calculate_work(prev_work, b['nBits'])

        if prev_seconds is None:
            b['seconds'] = None
        else:
            b['seconds'] = prev_seconds + b['nTime'] - prev_nTime
        if prev_satoshis is None or prev_satoshis < 0 or b['value_in'] is None:
            # XXX Abuse this field to save work in adopt_orphans.
            b['satoshis'] = -1 - b['value_destroyed']
        else:
            b['satoshis'] = prev_satoshis + b['value_out'] - b['value_in'] \
                - b['value_destroyed']

        if prev_satoshis is None or prev_satoshis < 0:
            ss_created = None
            b['total_ss'] = None
        else:
            ss_created = prev_satoshis * (b['nTime'] - prev_nTime)
            b['total_ss'] = prev_total_ss + ss_created

        if b['height'] is None or b['height'] < 2:
            b['search_block_id'] = None
        else:
            b['search_block_id'] = store.get_block_id_at_height(
                util.get_search_height(int(b['height'])),
                None if prev_block_id is None else int(prev_block_id))

        # Insert the block table row.
        try:
            store.sql(
                """INSERT INTO block (
                    block_id, block_hash, block_version, block_hashMerkleRoot,
                    block_nTime, block_nBits, block_nNonce, block_height,
                    prev_block_id, block_chain_work, block_value_in,
                    block_value_out, block_total_satoshis,
                    block_total_seconds, block_total_ss, block_num_tx,
                    search_block_id
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )""",
                (block_id, store.hashin(b['hash']), store.intin(b['version']),
                 store.hashin(b['hashMerkleRoot']), store.intin(b['nTime']),
                 store.intin(b['nBits']), store.intin(b['nNonce']),
                 b['height'], prev_block_id,
                 store.binin_int(b['chain_work'], WORK_BITS),
                 store.intin(b['value_in']), store.intin(b['value_out']),
                 store.intin(b['satoshis']), store.intin(b['seconds']),
                 store.intin(b['total_ss']),
                 len(b['transactions']), b['search_block_id']))

        except store.dbmodule.DatabaseError:

            if store.commit_bytes == 0:
                # Rollback won't undo any previous changes, since we
                # always commit.
                store.rollback()
                # If the exception is due to another process having
                # inserted the same block, it is okay.
                row = store.selectrow("""
                    SELECT block_id, block_satoshi_seconds
                      FROM block
                     WHERE block_hash = ?""",
                    (store.hashin(b['hash']),))
                if row:
                    store.log.info("Block already inserted; block_id %d unsued",
                                   block_id)
                    b['block_id'] = int(row[0])
                    b['ss'] = None if row[1] is None else int(row[1])
                    store.offer_block_to_chains(b, chain_ids)
                    return

            # This is not an expected error, or our caller may have to
            # rewind a block file.  Let them deal with it.
            raise

        # List the block's transactions in block_tx.
        for tx_pos in xrange(len(b['transactions'])):
            tx = b['transactions'][tx_pos]
            store.sql("""
                INSERT INTO block_tx
                    (block_id, tx_id, tx_pos)
                VALUES (?, ?, ?)""",
                      (block_id, tx['tx_id'], tx_pos))
            store.log.info("block_tx %d %d", block_id, tx['tx_id'])

        if b['height'] is not None:
            store._populate_block_txin(block_id)

            if all_txins_linked or not store._has_unlinked_txins(block_id):
                b['ss_destroyed'] = store._get_block_ss_destroyed(
                    block_id, b['nTime'],
                    map(lambda tx: tx['tx_id'], b['transactions']))
                if ss_created is None or prev_ss is None:
                    b['ss'] = None
                else:
                    b['ss'] = prev_ss + ss_created - b['ss_destroyed']

                store.sql("""
                    UPDATE block
                       SET block_satoshi_seconds = ?,
                           block_ss_destroyed = ?
                     WHERE block_id = ?""",
                          (store.intin(b['ss']),
                           store.intin(b['ss_destroyed']),
                           block_id))
            else:
                b['ss_destroyed'] = None
                b['ss'] = None

        # Store the inverse hashPrev relationship or mark the block as
        # an orphan.
        if prev_block_id:
            store.sql("""
                INSERT INTO block_next (block_id, next_block_id)
                VALUES (?, ?)""", (prev_block_id, block_id))
        elif not is_genesis:
            store.sql("INSERT INTO orphan_block (block_id, block_hashPrev)" +
                      " VALUES (?, ?)", (block_id, store.hashin(b['hashPrev'])))

        for row in store.selectall("""
            SELECT block_id FROM orphan_block WHERE block_hashPrev = ?""",
                                   (store.hashin(b['hash']),)):
            (orphan_id,) = row
            store.sql("UPDATE block SET prev_block_id = ? WHERE block_id = ?",
                      (block_id, orphan_id))
            store.sql("""
                INSERT INTO block_next (block_id, next_block_id)
                VALUES (?, ?)""", (block_id, orphan_id))
            store.sql("DELETE FROM orphan_block WHERE block_id = ?",
                      (orphan_id,))

        # offer_block_to_chains calls adopt_orphans, which propagates
        # block_height and other cumulative data to the blocks
        # attached above.
        store.offer_block_to_chains(b, chain_ids)

        return block_id

    def _populate_block_txin(store, block_id):
        # Create rows in block_txin.  In case of duplicate transactions,
        # choose the one with the lowest block ID.  XXX For consistency,
        # it should be the lowest height instead of block ID.
        for row in store.selectall("""
            SELECT txin.txin_id, MIN(obt.block_id)
              FROM block_tx bt
              JOIN txin ON (txin.tx_id = bt.tx_id)
              JOIN txout ON (txin.txout_id = txout.txout_id)
              JOIN block_tx obt ON (txout.tx_id = obt.tx_id)
             WHERE bt.block_id = ?
             GROUP BY txin.txin_id""", (block_id,)):
            (txin_id, oblock_id) = row
            if store.is_descended_from(block_id, int(oblock_id)):
                store.sql("""
                    INSERT INTO block_txin (block_id, txin_id, out_block_id)
                    VALUES (?, ?, ?)""",
                          (block_id, txin_id, oblock_id))

    def _has_unlinked_txins(store, block_id):
        (unlinked_count,) = store.selectrow("""
            SELECT COUNT(1)
              FROM block_tx bt
              JOIN txin ON (bt.tx_id = txin.tx_id)
              JOIN unlinked_txin u ON (txin.txin_id = u.txin_id)
             WHERE bt.block_id = ?""", (block_id,))
        return unlinked_count > 0

    def _get_block_ss_destroyed(store, block_id, nTime, tx_ids):
        block_ss_destroyed = 0
        for tx_id in tx_ids:
            destroyed = int(store.selectrow("""
                SELECT COALESCE(SUM(txout_approx.txout_approx_value *
                                    (? - b.block_nTime)), 0)
                  FROM block_txin bti
                  JOIN txin ON (bti.txin_id = txin.txin_id)
                  JOIN txout_approx ON (txin.txout_id = txout_approx.txout_id)
                  JOIN block_tx obt ON (txout_approx.tx_id = obt.tx_id)
                  JOIN block b ON (obt.block_id = b.block_id)
                 WHERE bti.block_id = ? AND txin.tx_id = ?""",
                                            (nTime, block_id, tx_id))[0])
            block_ss_destroyed += destroyed
        return block_ss_destroyed

    # Propagate cumulative values to descendant blocks.  Return info
    # about the longest chains containing b.  The returned dictionary
    # is keyed by the chain_id of a chain whose validation policy b
    # satisfies.  Each value is a pair (block, work) where block is
    # the best block descended from b in the given chain, and work is
    # the sum of orphan_work and the work between b and block.  Only
    # chains in chain_mask are considered.  Even if no known chain
    # contains b, this routine populates any descendant blocks'
    # cumulative statistics that are known for b and returns an empty
    # dictionary.
    def adopt_orphans(store, b, orphan_work, chain_ids, chain_mask):

        # XXX As originally written, this function occasionally hit
        # Python's recursion limit.  I am rewriting it iteratively
        # with minimal changes, hence the odd style.  Guido is
        # particularly unhelpful here, rejecting even labeled loops.

        ret = [None]
        def receive(x):
            ret[0] = x
        def doit():
            store._adopt_orphans_1(stack)
        stack = [receive, chain_mask, chain_ids, orphan_work, b, doit]
        while stack:
            stack.pop()()
        return ret[0]

    def _adopt_orphans_1(store, stack):
        def doit():
            store._adopt_orphans_1(stack)
        def continuation(x):
            store._adopt_orphans_2(stack, x)
        def didit():
            ret = stack.pop()
            stack.pop()(ret)

        b = stack.pop()
        orphan_work = stack.pop()
        chain_ids = stack.pop()
        chain_mask = stack.pop()
        ret = {}
        stack += [ ret, didit ]

        block_id = b['block_id']
        height = None if b['height'] is None else int(b['height'] + 1)

        # If adding block b, b will not yet be in chain_candidate, so
        # we rely on the chain_ids argument.  If called recursively,
        # look up chain_ids in chain_candidate.
        if not chain_ids:
            if chain_mask:
                chain_mask = chain_mask.intersection(
                    store.find_chains_containing_block(block_id))
            chain_ids = chain_mask

        for chain_id in chain_ids:
            ret[chain_id] = (b, orphan_work)

        for row in store.selectall("""
            SELECT bn.next_block_id, b.block_nBits,
                   b.block_value_out, b.block_value_in, b.block_nTime,
                   b.block_total_satoshis
              FROM block_next bn
              JOIN block b ON (bn.next_block_id = b.block_id)
             WHERE bn.block_id = ?""", (block_id,)):
            next_id, nBits, value_out, value_in, nTime, satoshis = row
            nBits = int(nBits)
            nTime = int(nTime)
            satoshis = None if satoshis is None else int(satoshis)
            new_work = util.calculate_work(orphan_work, nBits)

            if b['chain_work'] is None:
                chain_work = None
            else:
                chain_work = b['chain_work'] + new_work - orphan_work

            if value_in is None:
                value, count1, count2 = store.selectrow("""
                    SELECT SUM(txout.txout_value),
                           COUNT(1),
                           COUNT(txout.txout_value)
                      FROM block_tx bt
                      JOIN txin ON (bt.tx_id = txin.tx_id)
                      LEFT JOIN txout ON (txout.txout_id = txin.txout_id)
                     WHERE bt.block_id = ?""", (next_id,))
                if count1 == count2 + 1:
                    value_in = int(value)
                else:
                    store.log.warning(
                        "not updating block %d value_in: %s != %s + 1",
                        next_id, repr(count1), repr(count2))
            else:
                value_in = int(value_in)
            generated = None if value_in is None else int(value_out - value_in)

            if b['seconds'] is None:
                seconds = None
                total_ss = None
            else:
                new_seconds = nTime - b['nTime']
                seconds = b['seconds'] + new_seconds
                if b['total_ss'] is None or b['satoshis'] is None:
                    total_ss = None
                else:
                    total_ss = b['total_ss'] + new_seconds * b['satoshis']

            if satoshis < 0 and b['satoshis'] is not None and \
                    b['satoshis'] >= 0 and generated is not None:
                satoshis += 1 + b['satoshis'] + generated

            if height is None or height < 2:
                search_block_id = None
            else:
                search_block_id = store.get_block_id_at_height(
                    util.get_search_height(height), int(block_id))

            store.sql("""
                UPDATE block
                   SET block_height = ?,
                       block_chain_work = ?,
                       block_value_in = ?,
                       block_total_seconds = ?,
                       block_total_satoshis = ?,
                       block_total_ss = ?,
                       search_block_id = ?
                 WHERE block_id = ?""",
                      (height, store.binin_int(chain_work, WORK_BITS),
                       store.intin(value_in),
                       store.intin(seconds), store.intin(satoshis),
                       store.intin(total_ss), search_block_id,
                       next_id))

            ss = None

            if height is not None:
                store.sql("""
                    UPDATE chain_candidate SET block_height = ?
                     WHERE block_id = ?""",
                    (height, next_id))

                store._populate_block_txin(int(next_id))

                if b['ss'] is None or store._has_unlinked_txins(next_id):
                    pass
                else:
                    tx_ids = map(
                        lambda row: row[0],
                        store.selectall("""
                            SELECT tx_id
                              FROM block_tx
                             WHERE block_id = ?""", (next_id,)))
                    destroyed = store._get_block_ss_destroyed(
                        next_id, nTime, tx_ids)
                    ss = b['ss'] + b['satoshis'] * (nTime - b['nTime']) \
                        - destroyed

                    store.sql("""
                        UPDATE block
                           SET block_satoshi_seconds = ?,
                               block_ss_destroyed = ?
                         WHERE block_id = ?""",
                              (store.intin(ss),
                               store.intin(destroyed),
                               next_id))

                if store.use_firstbits:
                    for (addr_vers,) in store.selectall("""
                        SELECT c.chain_address_version
                          FROM chain c
                          JOIN chain_candidate cc ON (c.chain_id = cc.chain_id)
                         WHERE cc.block_id = ?""", (next_id,)):
                        store.do_vers_firstbits(addr_vers, int(next_id))

            nb = {
                "block_id": next_id,
                "height": height,
                "chain_work": chain_work,
                "nTime": nTime,
                "seconds": seconds,
                "satoshis": satoshis,
                "total_ss": total_ss,
                "ss": ss}

            stack += [ret, continuation,
                      chain_mask, None, new_work, nb, doit]

    def _adopt_orphans_2(store, stack, next_ret):
        ret = stack.pop()
        for chain_id in ret.keys():
            pair = next_ret[chain_id]
            if pair and pair[1] > ret[chain_id][1]:
                ret[chain_id] = pair

    def _export_scriptPubKey(store, txout, chain, scriptPubKey):
        """In txout, set script_type, address_version, binaddr, and for multisig, required_signatures."""

        if scriptPubKey is None:
            txout['script_type'] = None
            txout['binaddr'] = None
            return

        script_type, data = chain.parse_txout_script(scriptPubKey)
        txout['script_type'] = script_type
        txout['address_version'] = chain.address_version

        if script_type == Chain.SCRIPT_TYPE_PUBKEY:
            txout['binaddr'] = chain.pubkey_hash(data)
        elif script_type == Chain.SCRIPT_TYPE_ADDRESS:
            txout['binaddr'] = data
        elif script_type == Chain.SCRIPT_TYPE_P2SH:
            txout['address_version'] = chain.script_addr_vers
            txout['binaddr'] = data
        elif script_type == Chain.SCRIPT_TYPE_MULTISIG:
            txout['required_signatures'] = data['m']
            txout['binaddr'] = chain.pubkey_hash(scriptPubKey)
            txout['subbinaddr'] = [
                chain.pubkey_hash(pubkey)
                for pubkey in data['pubkeys']
                ]
        elif script_type == Chain.SCRIPT_TYPE_BURN:
            txout['binaddr'] = NULL_PUBKEY_HASH
        else:
            txout['binaddr'] = None

    def export_block(store, chain=None, block_hash=None, block_number=None):
        """
        Return a dict with the following:

        * chain_candidates[]
            * chain
            * in_longest
        * chain_satoshis
        * chain_satoshi_seconds
        * chain_work
        * fees
        * generated
        * hash
        * hashMerkleRoot
        * hashPrev
        * height
        * nBits
        * next_block_hashes
        * nNonce
        * nTime
        * satoshis_destroyed
        * satoshi_seconds
        * transactions[]
            * fees
            * hash
            * in[]
                * address_version
                * binaddr
                * value
            * out[]
                * address_version
                * binaddr
                * value
            * size
        * value_out
        * version

        Additionally, for multisig inputs and outputs:

        * subbinaddr[]
        * required_signatures

        Additionally, for proof-of-stake chains:

        * is_proof_of_stake
        * proof_of_stake_generated
        """

        if block_number is None and block_hash is None:
            raise ValueError("export_block requires either block_hash or block_number")

        where = []
        bind = []

        if chain is not None:
            where.append('chain_id = ?')
            bind.append(chain.id)

        if block_hash is not None:
            where.append('block_hash = ?')
            bind.append(store.hashin_hex(block_hash))

        if block_number is not None:
            where.append('block_height = ? AND in_longest = 1')
            bind.append(block_number)

        sql = """
            SELECT
                chain_id,
                in_longest,
                block_id,
                block_hash,
                block_version,
                block_hashMerkleRoot,
                block_nTime,
                block_nBits,
                block_nNonce,
                block_height,
                prev_block_hash,
                block_chain_work,
                block_value_in,
                block_value_out,
                block_total_satoshis,
                block_total_seconds,
                block_satoshi_seconds,
                block_total_ss,
                block_ss_destroyed,
                block_num_tx
              FROM chain_summary
             WHERE """ + ' AND '.join(where) + """
             ORDER BY
                in_longest DESC,
                chain_id DESC"""
        rows = store.selectall(sql, bind)

        if len(rows) == 0:
            return None

        row = rows[0][2:]
        def parse_cc(row):
            chain_id, in_longest = row[:2]
            return { "chain": store.get_chain_by_id(chain_id), "in_longest": in_longest }

        # Absent the chain argument, default to highest chain_id, preferring to avoid side chains.
        cc = map(parse_cc, rows)

        # "chain" may be None, but "found_chain" will not.
        found_chain = chain
        if found_chain is None:
            if len(cc) > 0:
                found_chain = cc[0]['chain']
            else:
                # Should not normally get here.
                found_chain = store.get_default_chain()

        (block_id, block_hash, block_version, hashMerkleRoot,
         nTime, nBits, nNonce, height,
         prev_block_hash, block_chain_work, value_in, value_out,
         satoshis, seconds, ss, total_ss, destroyed, num_tx) = (
            row[0], store.hashout_hex(row[1]), row[2],
            store.hashout_hex(row[3]), row[4], int(row[5]), row[6],
            row[7], store.hashout_hex(row[8]),
            store.binout_int(row[9]), int(row[10]), int(row[11]),
            None if row[12] is None else int(row[12]),
            None if row[13] is None else int(row[13]),
            None if row[14] is None else int(row[14]),
            None if row[15] is None else int(row[15]),
            None if row[16] is None else int(row[16]),
            int(row[17]),
            )

        next_hashes = [
            store.hashout_hex(hash) for hash, il in
            store.selectall("""
            SELECT DISTINCT n.block_hash, cc.in_longest
              FROM block_next bn
              JOIN block n ON (bn.next_block_id = n.block_id)
              JOIN chain_candidate cc ON (n.block_id = cc.block_id)
             WHERE bn.block_id = ?
             ORDER BY cc.in_longest DESC""",
                            (block_id,)) ]

        tx_ids = []
        txs = {}
        block_out = 0
        block_in = 0

        for row in store.selectall("""
            SELECT tx_id, tx_hash, tx_size, txout_value, txout_scriptPubKey
              FROM txout_detail
             WHERE block_id = ?
             ORDER BY tx_pos, txout_pos
        """, (block_id,)):
            tx_id, tx_hash, tx_size, txout_value, scriptPubKey = (
                row[0], row[1], row[2], int(row[3]), store.binout(row[4]))
            tx = txs.get(tx_id)
            if tx is None:
                tx_ids.append(tx_id)
                txs[tx_id] = {
                    "hash": store.hashout_hex(tx_hash),
                    "total_out": 0,
                    "total_in": 0,
                    "out": [],
                    "in": [],
                    "size": int(tx_size),
                    }
                tx = txs[tx_id]
            tx['total_out'] += txout_value
            block_out += txout_value

            txout = { 'value': txout_value }
            store._export_scriptPubKey(txout, found_chain, scriptPubKey)
            tx['out'].append(txout)

        for row in store.selectall("""
            SELECT tx_id, txin_value, txin_scriptPubKey
              FROM txin_detail
             WHERE block_id = ?
             ORDER BY tx_pos, txin_pos
        """, (block_id,)):
            tx_id, txin_value, scriptPubKey = (
                row[0], 0 if row[1] is None else int(row[1]),
                store.binout(row[2]))
            tx = txs.get(tx_id)
            if tx is None:
                # Strange, inputs but no outputs?
                tx_ids.append(tx_id)
                tx_hash, tx_size = store.selectrow("""
                    SELECT tx_hash, tx_size FROM tx WHERE tx_id = ?""",
                                           (tx_id,))
                txs[tx_id] = {
                    "hash": store.hashout_hex(tx_hash),
                    "total_out": 0,
                    "total_in": 0,
                    "out": [],
                    "in": [],
                    "size": int(tx_size),
                    }
                tx = txs[tx_id]
            tx['total_in'] += txin_value
            block_in += txin_value

            txin = { 'value': txin_value }
            store._export_scriptPubKey(txin, found_chain, scriptPubKey)
            tx['in'].append(txin)

        generated = block_out - block_in
        coinbase_tx = txs[tx_ids[0]]
        coinbase_tx['fees'] = 0
        block_fees = coinbase_tx['total_out'] - generated

        b = {
            'chain_candidates':      cc,
            'chain_satoshis':        satoshis,
            'chain_satoshi_seconds': total_ss,
            'chain_work':            block_chain_work,
            'fees':                  block_fees,
            'generated':             generated,
            'hash':                  block_hash,
            'hashMerkleRoot':        hashMerkleRoot,
            'hashPrev':              prev_block_hash,
            'height':                height,
            'nBits':                 nBits,
            'next_block_hashes':     next_hashes,
            'nNonce':                nNonce,
            'nTime':                 nTime,
            'satoshis_destroyed':    destroyed,
            'satoshi_seconds':       ss,
            'transactions':          [txs[tx_id] for tx_id in tx_ids],
            'value_out':             block_out,
            'version':               block_version,
            }

        is_stake_chain = chain is not None and chain.has_feature('nvc_proof_of_stake')
        if is_stake_chain:
            # Proof-of-stake display based loosely on CryptoManiac/novacoin and
            # http://nvc.cryptocoinexplorer.com.
            b['is_proof_of_stake'] = len(tx_ids) > 1 and coinbase_tx['total_out'] == 0

        for tx_id in tx_ids[1:]:
            tx = txs[tx_id]
            tx['fees'] = tx['total_in'] - tx['total_out']

        if is_stake_chain and b['is_proof_of_stake']:
            b['proof_of_stake_generated'] = -txs[tx_ids[1]]['fees']
            txs[tx_ids[1]]['fees'] = 0
            b['fees'] += b['proof_of_stake_generated']

        return b

    def tx_find_id_and_value(store, tx, is_coinbase):
        row = store.selectrow("""
            SELECT tx.tx_id, SUM(txout.txout_value), SUM(
                       CASE WHEN txout.pubkey_id > 0 THEN txout.txout_value
                            ELSE 0 END)
              FROM tx
              LEFT JOIN txout ON (tx.tx_id = txout.tx_id)
             WHERE tx_hash = ?
             GROUP BY tx.tx_id""",
                              (store.hashin(tx['hash']),))
        if row:
            tx_id, value_out, undestroyed = row
            value_out = 0 if value_out is None else int(value_out)
            undestroyed = 0 if undestroyed is None else int(undestroyed)
            count_in, value_in = store.selectrow("""
                SELECT COUNT(1), SUM(prevout.txout_value)
                  FROM txin
                  JOIN txout prevout ON (txin.txout_id = prevout.txout_id)
                 WHERE txin.tx_id = ?""", (tx_id,))
            if (count_in or 0) < len(tx['txIn']):
                value_in = 0 if is_coinbase else None
            tx['value_in'] = None if value_in is None else int(value_in)
            tx['value_out'] = value_out
            tx['value_destroyed'] = value_out - undestroyed
            return tx_id

        return None

    def import_tx(store, tx, is_coinbase, chain):
        tx_id = store.new_id("tx")
        dbhash = store.hashin(tx['hash'])

        if 'size' not in tx:
            tx['size'] = len(tx['__data__'])

        store.sql("""
            INSERT INTO tx (tx_id, tx_hash, tx_version, tx_lockTime, tx_size)
            VALUES (?, ?, ?, ?, ?)""",
                  (tx_id, dbhash, store.intin(tx['version']),
                   store.intin(tx['lockTime']), tx['size']))

        # Import transaction outputs.
        tx['value_out'] = 0
        tx['value_destroyed'] = 0
        for pos in xrange(len(tx['txOut'])):
            txout = tx['txOut'][pos]
            tx['value_out'] += txout['value']
            txout_id = store.new_id("txout")

            pubkey_id = store.script_to_pubkey_id(chain, txout['scriptPubKey'])
            if pubkey_id is not None and pubkey_id <= 0:
                tx['value_destroyed'] += txout['value']

            store.sql("""
                INSERT INTO txout (
                    txout_id, tx_id, txout_pos, txout_value,
                    txout_scriptPubKey, pubkey_id
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                      (txout_id, tx_id, pos, store.intin(txout['value']),
                       store.binin(txout['scriptPubKey']), pubkey_id))
            for row in store.selectall("""
                SELECT txin_id
                  FROM unlinked_txin
                 WHERE txout_tx_hash = ?
                   AND txout_pos = ?""", (dbhash, pos)):
                (txin_id,) = row
                store.sql("UPDATE txin SET txout_id = ? WHERE txin_id = ?",
                          (txout_id, txin_id))
                store.sql("DELETE FROM unlinked_txin WHERE txin_id = ?",
                          (txin_id,))

        # Import transaction inputs.
        tx['value_in'] = 0
        tx['unlinked_count'] = 0
        for pos in xrange(len(tx['txIn'])):
            txin = tx['txIn'][pos]
            txin_id = store.new_id("txin")

            if is_coinbase:
                txout_id = None
            else:
                txout_id, value = store.lookup_txout(
                    txin['prevout_hash'], txin['prevout_n'])
                if value is None:
                    tx['value_in'] = None
                elif tx['value_in'] is not None:
                    tx['value_in'] += value

            store.sql("""
                INSERT INTO txin (
                    txin_id, tx_id, txin_pos, txout_id""" + (""",
                    txin_scriptSig, txin_sequence""" if store.keep_scriptsig
                                                             else "") + """
                ) VALUES (?, ?, ?, ?""" + (", ?, ?" if store.keep_scriptsig
                                           else "") + """)""",
                      (txin_id, tx_id, pos, txout_id,
                       store.binin(txin['scriptSig']),
                       store.intin(txin['sequence'])) if store.keep_scriptsig
                      else (txin_id, tx_id, pos, txout_id))
            if not is_coinbase and txout_id is None:
                tx['unlinked_count'] += 1
                store.sql("""
                    INSERT INTO unlinked_txin (
                        txin_id, txout_tx_hash, txout_pos
                    ) VALUES (?, ?, ?)""",
                          (txin_id, store.hashin(txin['prevout_hash']),
                           store.intin(txin['prevout_n'])))

        # XXX Could populate PUBKEY.PUBKEY with txin scripts...
        # or leave that to an offline process.  Nothing in this program
        # requires them.
        return tx_id

    def import_and_commit_tx(store, tx, is_coinbase, chain):
        try:
            tx_id = store.import_tx(tx, is_coinbase, chain)
            store.commit()

        except store.dbmodule.DatabaseError:
            store.rollback()
            # Violation of tx_hash uniqueness?
            tx_id = store.tx_find_id_and_value(tx, is_coinbase)
            if not tx_id:
                raise

        return tx_id

    def maybe_import_binary_tx(store, chain_name, binary_tx):
        if chain_name is None:
            chain = store.get_default_chain()
        else:
            chain = store.get_chain_by_name(chain_name)

        tx_hash = chain.transaction_hash(binary_tx)

        (count,) = store.selectrow(
            "SELECT COUNT(1) FROM tx WHERE tx_hash = ?",
            (store.hashin(tx_hash),))

        if count == 0:
            tx = chain.parse_transaction(binary_tx)
            tx['hash'] = tx_hash
            store.import_tx(tx, chain.is_coinbase_tx(tx), chain)
            store.imported_bytes(tx['size'])

    def export_tx(store, tx_id=None, tx_hash=None, decimals=8, format="api", chain=None):
        """Return a dict as seen by /rawtx or None if not found."""

        # TODO: merge _export_tx_detail with export_tx.
        if format == 'browser':
            return store._export_tx_detail(tx_hash, chain=chain)

        tx = {}
        is_bin = format == "binary"

        if tx_id is not None:
            row = store.selectrow("""
                SELECT tx_hash, tx_version, tx_lockTime, tx_size
                  FROM tx
                 WHERE tx_id = ?
            """, (tx_id,))
            if row is None:
                return None
            tx['hash'] = store.hashout_hex(row[0])

        elif tx_hash is not None:
            row = store.selectrow("""
                SELECT tx_id, tx_version, tx_lockTime, tx_size
                  FROM tx
                 WHERE tx_hash = ?
            """, (store.hashin_hex(tx_hash),))
            if row is None:
                return None
            tx['hash'] = tx_hash.decode('hex')[::-1] if is_bin else tx_hash
            tx_id = row[0]

        else:
            raise ValueError("export_tx requires either tx_id or tx_hash.")

        tx['version' if is_bin else 'ver']        = int(row[1])
        tx['lockTime' if is_bin else 'lock_time'] = int(row[2])
        tx['size'] = int(row[3])

        txins = []
        tx['txIn' if is_bin else 'in'] = txins
        for row in store.selectall("""
            SELECT
                COALESCE(tx.tx_hash, uti.txout_tx_hash),
                COALESCE(txout.txout_pos, uti.txout_pos)""" + (""",
                txin_scriptSig,
                txin_sequence""" if store.keep_scriptsig else "") + """
            FROM txin
            LEFT JOIN txout ON (txin.txout_id = txout.txout_id)
            LEFT JOIN tx ON (txout.tx_id = tx.tx_id)
            LEFT JOIN unlinked_txin uti ON (txin.txin_id = uti.txin_id)
            WHERE txin.tx_id = ?
            ORDER BY txin.txin_pos""", (tx_id,)):
            prevout_hash = row[0]
            prevout_n = None if row[1] is None else int(row[1])
            if is_bin:
                txin = {
                    'prevout_hash': store.hashout(prevout_hash),
                    'prevout_n': prevout_n}
            else:
                if prevout_hash is None:
                    prev_out = {
                        'hash': "0" * 64,  # XXX should store this?
                        'n': 0xffffffff}   # XXX should store this?
                else:
                    prev_out = {
                        'hash': store.hashout_hex(prevout_hash),
                        'n': prevout_n}
                txin = {'prev_out': prev_out}
            if store.keep_scriptsig:
                scriptSig = row[2]
                sequence = row[3]
                if is_bin:
                    txin['scriptSig'] = store.binout(scriptSig)
                else:
                    txin['raw_scriptSig'] = store.binout_hex(scriptSig)
                txin['sequence'] = None if sequence is None else int(sequence)
            txins.append(txin)

        txouts = []
        tx['txOut' if is_bin else 'out'] = txouts
        for satoshis, scriptPubKey in store.selectall("""
            SELECT txout_value, txout_scriptPubKey
              FROM txout
             WHERE tx_id = ?
            ORDER BY txout_pos""", (tx_id,)):

            if is_bin:
                txout = {
                    'value': int(satoshis),
                    'scriptPubKey': store.binout(scriptPubKey)}
            else:
                coin = 10 ** decimals
                satoshis = int(satoshis)
                integer = satoshis / coin
                frac = satoshis % coin
                txout = {
                    'value': ("%%d.%%0%dd" % (decimals,)) % (integer, frac),
                    'raw_scriptPubKey': store.binout_hex(scriptPubKey)}
            txouts.append(txout)

        if not is_bin:
            tx['vin_sz'] = len(txins)
            tx['vout_sz'] = len(txouts)

        return tx

    def _export_tx_detail(store, tx_hash, chain):
        try:
            dbhash = store.hashin_hex(tx_hash)
        except TypeError:
            raise MalformedHash()

        row = store.selectrow("""
            SELECT tx_id, tx_version, tx_lockTime, tx_size
              FROM tx
             WHERE tx_hash = ?
        """, (dbhash,))
        if row is None:
            return None

        tx_id = int(row[0])
        tx = {
            'hash': tx_hash,
            'version': int(row[1]),
            'lockTime': int(row[2]),
            'size': int(row[3]),
            }

        def parse_tx_cc(row):
            return {
                'chain': store.get_chain_by_id(row[0]),
                'in_longest': int(row[1]),
                'block_nTime': int(row[2]),
                'block_height': None if row[3] is None else int(row[3]),
                'block_hash': store.hashout_hex(row[4]),
                'tx_pos': int(row[5])
                }

        tx['chain_candidates'] = map(parse_tx_cc, store.selectall("""
            SELECT cc.chain_id, cc.in_longest,
                   b.block_nTime, b.block_height, b.block_hash,
                   block_tx.tx_pos
              FROM chain_candidate cc
              JOIN block b ON (b.block_id = cc.block_id)
              JOIN block_tx ON (block_tx.block_id = b.block_id)
             WHERE block_tx.tx_id = ?
             ORDER BY cc.chain_id, cc.in_longest DESC, b.block_hash
        """, (tx_id,)))

        if chain is None:
            if len(tx['chain_candidates']) > 0:
                chain = tx['chain_candidates'][0]['chain']
            else:
                chain = store.get_default_chain()

        def parse_row(row):
            pos, script, value, o_hash, o_pos = row[:5]
            script = store.binout(script)
            scriptPubKey = store.binout(row[5]) if len(row) >5 else script

            ret = {
                "pos": int(pos),
                "binscript": script,
                "value": None if value is None else int(value),
                "o_hash": store.hashout_hex(o_hash),
                "o_pos": None if o_pos is None else int(o_pos),
                }
            store._export_scriptPubKey(ret, chain, scriptPubKey)

            return ret

        # XXX Unneeded outer join.
        tx['in'] = map(parse_row, store.selectall("""
            SELECT
                txin.txin_pos""" + (""",
                txin.txin_scriptSig""" if store.keep_scriptsig else """,
                NULL""") + """,
                txout.txout_value,
                COALESCE(prevtx.tx_hash, u.txout_tx_hash),
                COALESCE(txout.txout_pos, u.txout_pos),
                txout.txout_scriptPubKey
              FROM txin
              LEFT JOIN txout ON (txout.txout_id = txin.txout_id)
              LEFT JOIN tx prevtx ON (txout.tx_id = prevtx.tx_id)
              LEFT JOIN unlinked_txin u ON (u.txin_id = txin.txin_id)
             WHERE txin.tx_id = ?
             ORDER BY txin.txin_pos
        """, (tx_id,)))

        # XXX Only one outer join needed.
        tx['out'] = map(parse_row, store.selectall("""
            SELECT
                txout.txout_pos,
                txout.txout_scriptPubKey,
                txout.txout_value,
                nexttx.tx_hash,
                txin.txin_pos
              FROM txout
              LEFT JOIN txin ON (txin.txout_id = txout.txout_id)
              LEFT JOIN tx nexttx ON (txin.tx_id = nexttx.tx_id)
             WHERE txout.tx_id = ?
             ORDER BY txout.txout_pos
        """, (tx_id,)))

        def sum_values(rows):
            ret = 0
            for row in rows:
                if row['value'] is None:
                    return None
                ret += row['value']
            return ret

        tx['value_in'] = sum_values(tx['in'])
        tx['value_out'] = sum_values(tx['out'])

        return tx

    def export_address_history(store, address, chain=None, max_rows=-1, types=frozenset(['direct', 'escrow'])):
        version, binaddr = util.decode_check_address(address)
        if binaddr is None:
            raise MalformedAddress("Invalid address")

        balance = {}
        received = {}
        sent = {}
        counts = [0, 0]
        chains = []

        def adj_balance(txpoint):
            chain = txpoint['chain']

            if chain.id not in balance:
                chains.append(chain)
                balance[chain.id] = 0
                received[chain.id] = 0
                sent[chain.id] = 0

            if txpoint['type'] == 'direct':
                value = txpoint['value']
                balance[chain.id] += value
                if txpoint['is_out']:
                    sent[chain.id] -= value
                else:
                    received[chain.id] += value
                counts[txpoint['is_out']] += 1

        dbhash = store.binin(binaddr)
        txpoints = []

        def parse_row(is_out, row_type, nTime, chain_id, height, blk_hash, tx_hash, pos, value, script=None):
            chain = store.get_chain_by_id(chain_id)
            txpoint = {
                'type':     row_type,
                'is_out':   int(is_out),
                'nTime':    int(nTime),
                'chain':    chain,
                'height':   int(height),
                'blk_hash': store.hashout_hex(blk_hash),
                'tx_hash':  store.hashout_hex(tx_hash),
                'pos':      int(pos),
                'value':    int(value),
                }
            if script is not None:
                store._export_scriptPubKey(txpoint, chain, store.binout(script))

            return txpoint

        def parse_direct_in(row):  return parse_row(True, 'direct', *row)
        def parse_direct_out(row): return parse_row(False, 'direct', *row)
        def parse_escrow_in(row):  return parse_row(True, 'escrow', *row)
        def parse_escrow_out(row): return parse_row(False, 'escrow', *row)

        def get_received(escrow):
            return store.selectall("""
                SELECT
                    b.block_nTime,
                    cc.chain_id,
                    b.block_height,
                    b.block_hash,
                    tx.tx_hash,
                    txin.txin_pos,
                    -prevout.txout_value""" + (""",
                    prevout.txout_scriptPubKey""" if escrow else "") + """
                  FROM chain_candidate cc
                  JOIN block b ON (b.block_id = cc.block_id)
                  JOIN block_tx ON (block_tx.block_id = b.block_id)
                  JOIN tx ON (tx.tx_id = block_tx.tx_id)
                  JOIN txin ON (txin.tx_id = tx.tx_id)
                  JOIN txout prevout ON (txin.txout_id = prevout.txout_id)""" + ("""
                  JOIN multisig_pubkey mp ON (mp.multisig_id = prevout.pubkey_id)""" if escrow else "") + """
                  JOIN pubkey ON (pubkey.pubkey_id = """ + ("mp" if escrow else "prevout") + """.pubkey_id)
                 WHERE pubkey.pubkey_hash = ?
                   AND cc.in_longest = 1""" + ("" if max_rows < 0 else """
                 LIMIT ?"""),
                          (dbhash,)
                          if max_rows < 0 else
                          (dbhash, max_rows + 1))

        def get_sent(escrow):
            return store.selectall("""
                SELECT
                    b.block_nTime,
                    cc.chain_id,
                    b.block_height,
                    b.block_hash,
                    tx.tx_hash,
                    txout.txout_pos,
                    txout.txout_value""" + (""",
                    txout.txout_scriptPubKey""" if escrow else "") + """
                  FROM chain_candidate cc
                  JOIN block b ON (b.block_id = cc.block_id)
                  JOIN block_tx ON (block_tx.block_id = b.block_id)
                  JOIN tx ON (tx.tx_id = block_tx.tx_id)
                  JOIN txout ON (txout.tx_id = tx.tx_id)""" + ("""
                  JOIN multisig_pubkey mp ON (mp.multisig_id = txout.pubkey_id)""" if escrow else "") + """
                  JOIN pubkey ON (pubkey.pubkey_id = """ + ("mp" if escrow else "txout") + """.pubkey_id)
                 WHERE pubkey.pubkey_hash = ?
                   AND cc.in_longest = 1""" + ("" if max_rows < 0 else """
                 LIMIT ?"""),
                          (dbhash, max_rows + 1)
                          if max_rows >= 0 else
                          (dbhash,))

        if 'direct' in types:
            in_rows = get_received(False)
            if len(in_rows) > max_rows >= 0:
                return None  # XXX Could still show address basic data.
            txpoints += map(parse_direct_in, in_rows)

            out_rows = get_sent(False)
            if len(out_rows) > max_rows >= 0:
                return None
            txpoints += map(parse_direct_out, out_rows)

        if 'escrow' in types:
            in_rows = get_received(True)
            if len(in_rows) > max_rows >= 0:
                return None
            txpoints += map(parse_escrow_in, in_rows)

            out_rows = get_sent(True)
            if len(out_rows) > max_rows >= 0:
                return None
            txpoints += map(parse_escrow_out, out_rows)

        def cmp_txpoint(p1, p2):
            return cmp(p1['nTime'], p2['nTime']) \
                or cmp(p1['is_out'], p2['is_out']) \
                or cmp(p1['height'], p2['height']) \
                or cmp(p1['chain'].name, p2['chain'].name)

        txpoints.sort(cmp_txpoint)

        for txpoint in txpoints:
            adj_balance(txpoint)

        hist = {
            'binaddr':  binaddr,
            'version':  version,
            'chains':   chains,
            'txpoints': txpoints,
            'balance':  balance,
            'sent':     sent,
            'received': received,
            'counts':   counts
            }

        # Show P2SH address components, if known.
        # XXX With some more work, we could find required_signatures.
        for (subbinaddr,) in store.selectall("""
            SELECT sub.pubkey_hash
              FROM multisig_pubkey mp
              JOIN pubkey top ON (mp.multisig_id = top.pubkey_id)
              JOIN pubkey sub ON (mp.pubkey_id = sub.pubkey_id)
             WHERE top.pubkey_hash = ?""", (dbhash,)):
            if 'subbinaddr' not in hist:
                hist['subbinaddr'] = []
            hist['subbinaddr'].append(store.binout(subbinaddr))

        return hist

    # Called to indicate that the given block has the correct magic
    # number and policy for the given chains.  Updates CHAIN_CANDIDATE
    # and CHAIN.CHAIN_LAST_BLOCK_ID as appropriate.
    def offer_block_to_chains(store, b, chain_ids):
        b['top'] = store.adopt_orphans(b, 0, chain_ids, chain_ids)
        for chain_id in chain_ids:
            store._offer_block_to_chain(b, chain_id)

    def _offer_block_to_chain(store, b, chain_id):
        if b['chain_work'] is None:
            in_longest = 0
        else:
            # Do we produce a chain longer than the current chain?
            # Query whether the new block (or its tallest descendant)
            # beats the current chain_last_block_id.  Also check
            # whether the current best is our top, which indicates
            # this block is in longest; this can happen in database
            # repair scenarios.
            top = b['top'][chain_id][0]
            row = store.selectrow("""
                SELECT b.block_id, b.block_height, b.block_chain_work
                  FROM block b, chain c
                 WHERE c.chain_id = ?
                   AND b.block_id = c.chain_last_block_id""", (chain_id,))
            if row:
                loser_id, loser_height, loser_work = row
                if loser_id != top['block_id'] and \
                        store.binout_int(loser_work) >= top['chain_work']:
                    row = None
            if row:
                # New longest chain.
                in_longest = 1
                to_connect = []
                to_disconnect = []
                winner_id = top['block_id']
                winner_height = top['height']
                while loser_height > winner_height:
                    to_disconnect.insert(0, loser_id)
                    loser_id = store.get_prev_block_id(loser_id)
                    loser_height -= 1
                while winner_height > loser_height:
                    to_connect.insert(0, winner_id)
                    winner_id = store.get_prev_block_id(winner_id)
                    winner_height -= 1
                loser_height = None
                while loser_id != winner_id:
                    to_disconnect.insert(0, loser_id)
                    loser_id = store.get_prev_block_id(loser_id)
                    to_connect.insert(0, winner_id)
                    winner_id = store.get_prev_block_id(winner_id)
                    winner_height -= 1
                for block_id in to_disconnect:
                    store.disconnect_block(block_id, chain_id)
                for block_id in to_connect:
                    store.connect_block(block_id, chain_id)

            elif b['hashPrev'] == store.get_chain_by_id(chain_id).genesis_hash_prev:
                in_longest = 1  # Assume only one genesis block per chain.  XXX
            else:
                in_longest = 0

        store.sql("""
            INSERT INTO chain_candidate (
                chain_id, block_id, in_longest, block_height
            ) VALUES (?, ?, ?, ?)""",
                  (chain_id, b['block_id'], in_longest, b['height']))

        if in_longest > 0:
            store.sql("""
                UPDATE chain
                   SET chain_last_block_id = ?
                 WHERE chain_id = ?""", (top['block_id'], chain_id))

        if store.use_firstbits and b['height'] is not None:
            (addr_vers,) = store.selectrow("""
                SELECT chain_address_version
                  FROM chain
                 WHERE chain_id = ?""", (chain_id,))
            store.do_vers_firstbits(addr_vers, b['block_id'])

    def offer_existing_block(store, hash, chain_id):
        block_row = store.selectrow("""
            SELECT block_id, block_height, block_chain_work,
                   block_nTime, block_total_seconds,
                   block_total_satoshis, block_satoshi_seconds,
                   block_total_ss
              FROM block
             WHERE block_hash = ?
        """, (store.hashin(hash),))

        if not block_row:
            return False

        if chain_id is None:
            return True

        # Block header already seen.  Don't import the block,
        # but try to add it to the chain.

        b = {
            "block_id":   block_row[0],
            "height":     block_row[1],
            "chain_work": store.binout_int(block_row[2]),
            "nTime":      block_row[3],
            "seconds":    block_row[4],
            "satoshis":   block_row[5],
            "ss":         block_row[6],
            "total_ss":   block_row[7]}

        if store.selectrow("""
            SELECT 1
              FROM chain_candidate
             WHERE block_id = ?
               AND chain_id = ?""",
                        (b['block_id'], chain_id)):
            store.log.info("block %d already in chain %d",
                           b['block_id'], chain_id)
        else:
            if b['height'] == 0:
                b['hashPrev'] = store.get_chain_by_id(chain_id).genesis_hash_prev
            else:
                b['hashPrev'] = 'dummy'  # Fool adopt_orphans.
            store.offer_block_to_chains(b, frozenset([chain_id]))

        return True

    def find_next_blocks(store, block_id):
        ret = []
        for row in store.selectall(
            "SELECT next_block_id FROM block_next WHERE block_id = ?",
            (block_id,)):
            ret.append(row[0])
        return ret

    def find_chains_containing_block(store, block_id):
        ret = []
        for row in store.selectall(
            "SELECT chain_id FROM chain_candidate WHERE block_id = ?",
            (block_id,)):
            ret.append(row[0])
        return frozenset(ret)

    def get_prev_block_id(store, block_id):
        return store.selectrow(
            "SELECT prev_block_id FROM block WHERE block_id = ?",
            (block_id,))[0]

    def disconnect_block(store, block_id, chain_id):
        store.sql("""
            UPDATE chain_candidate
               SET in_longest = 0
             WHERE block_id = ? AND chain_id = ?""",
                  (block_id, chain_id))

    def connect_block(store, block_id, chain_id):
        store.sql("""
            UPDATE chain_candidate
               SET in_longest = 1
             WHERE block_id = ? AND chain_id = ?""",
                  (block_id, chain_id))

    def lookup_txout(store, tx_hash, txout_pos):
        row = store.selectrow("""
            SELECT txout.txout_id, txout.txout_value
              FROM txout, tx
             WHERE txout.tx_id = tx.tx_id
               AND tx.tx_hash = ?
               AND txout.txout_pos = ?""",
                  (store.hashin(tx_hash), txout_pos))
        return (None, None) if row is None else (row[0], int(row[1]))

    def script_to_pubkey_id(store, chain, script):
        """Extract address and script type from transaction output script."""
        script_type, data = chain.parse_txout_script(script)

        if script_type in (Chain.SCRIPT_TYPE_ADDRESS, Chain.SCRIPT_TYPE_P2SH):
            return store.pubkey_hash_to_id(data)

        if script_type == Chain.SCRIPT_TYPE_PUBKEY:
            return store.pubkey_to_id(chain, data)

        if script_type == Chain.SCRIPT_TYPE_MULTISIG:
            script_hash = chain.script_hash(script)
            multisig_id = store._pubkey_id(script_hash, script)

            if not store.selectrow("SELECT 1 FROM multisig_pubkey WHERE multisig_id = ?", (multisig_id,)):
                for pubkey in set(data['pubkeys']):
                    pubkey_id = store.pubkey_to_id(chain, pubkey)
                    store.sql("""
                        INSERT INTO multisig_pubkey (multisig_id, pubkey_id)
                        VALUES (?, ?)""", (multisig_id, pubkey_id))
            return multisig_id

        if script_type == Chain.SCRIPT_TYPE_BURN:
            return PUBKEY_ID_NETWORK_FEE

        return None

    def pubkey_hash_to_id(store, pubkey_hash):
        return store._pubkey_id(pubkey_hash, None)

    def pubkey_to_id(store, chain, pubkey):
        pubkey_hash = chain.pubkey_hash(pubkey)
        return store._pubkey_id(pubkey_hash, pubkey)

    def _pubkey_id(store, pubkey_hash, pubkey):
        dbhash = store.binin(pubkey_hash)  # binin, not hashin for 160-bit
        row = store.selectrow("""
            SELECT pubkey_id
              FROM pubkey
             WHERE pubkey_hash = ?""", (dbhash,))
        if row:
            return row[0]
        pubkey_id = store.new_id("pubkey")

        if pubkey is not None and len(pubkey) > MAX_PUBKEY:
            pubkey = None

        store.sql("""
            INSERT INTO pubkey (pubkey_id, pubkey_hash, pubkey)
            VALUES (?, ?, ?)""",
                  (pubkey_id, dbhash, store.binin(pubkey)))
        return pubkey_id

    def flush(store):
        if store.bytes_since_commit > 0:
            store.commit()
            store.log.debug("commit")
            store.bytes_since_commit = 0

    def imported_bytes(store, size):
        store.bytes_since_commit += size
        if store.bytes_since_commit >= store.commit_bytes:
            store.flush()

    def catch_up(store):
        for dircfg in store.datadirs:
            try:
                loader = dircfg['loader'] or store.default_loader
                if loader == "blkfile":
                    store.catch_up_dir(dircfg)
                elif loader in ("rpc", "rpc,blkfile", "default"):
                    if not store.catch_up_rpc(dircfg):
                        if loader == "rpc":
                            raise Exception("RPC load failed")
                        store.log.debug("catch_up_rpc: abort")
                        store.catch_up_dir(dircfg)
                else:
                    raise Exception("Unknown datadir loader: %s" % loader)

                store.flush()

            except Exception, e:
                store.log.exception("Failed to catch up %s", dircfg)
                store.rollback()

    def catch_up_rpc(store, dircfg):
        """
        Load new blocks using RPC.  Requires running *coind supporting
        getblockhash, getblock, and getrawtransaction.  Bitcoind v0.8
        requires the txindex configuration option.  Requires chain_id
        in the datadir table.
        """
        chain_id = dircfg['chain_id']
        if chain_id is None:
            store.log.debug("no chain_id")
            return False
        chain = store.chains_by.id[chain_id]

        conffile = dircfg.get('conf') or chain.datadir_conf_file_name
        conffile = os.path.join(dircfg['dirname'], conffile)
        try:
            conf = dict([line.strip().split("=", 1)
                         if "=" in line
                         else (line.strip(), True)
                         for line in open(conffile)
                         if line != "" and line[0] not in "#\r\n"])
        except Exception, e:
            store.log.debug("failed to load %s: %s", conffile, e)
            return False

        rpcuser     = conf.get("rpcuser", "")
        rpcpassword = conf["rpcpassword"]
        rpcconnect  = conf.get("rpcconnect", "127.0.0.1")
        rpcport     = conf.get("rpcport", chain.datadir_rpcport)
        url = "http://" + rpcuser + ":" + rpcpassword + "@" + rpcconnect \
            + ":" + str(rpcport)

        def rpc(func, *params):
            store.rpclog.info("RPC>> %s %s", func, params)
            ret = util.jsonrpc(url, func, *params)

            if (store.rpclog.isEnabledFor(logging.INFO)):
                store.rpclog.info("RPC<< %s",
                                  re.sub(r'\[[^\]]{100,}\]', '[...]', str(ret)))
            return ret

        def get_blockhash(height):
            try:
                return rpc("getblockhash", height)
            except util.JsonrpcException, e:
                if e.code == -1:  # Block number out of range.
                    return None
                raise

        (max_height,) = store.selectrow("""
            SELECT MAX(block_height)
              FROM chain_candidate
             WHERE chain_id = ?""", (chain.id,))
        height = 0 if max_height is None else int(max_height) + 1

        def get_tx(rpc_tx_hash):
            try:
                rpc_tx_hex = rpc("getrawtransaction", rpc_tx_hash)

            except util.JsonrpcException, e:
                if e.code != -5:  # -5: transaction not in index.
                    raise
                if height != 0:
                    store.log.debug("RPC service lacks full txindex")
                    return None

                # The genesis transaction is unavailable.  This is
                # normal.
                import genesis_tx
                rpc_tx_hex = genesis_tx.get(rpc_tx_hash)
                if rpc_tx_hex is None:
                    store.log.debug("genesis transaction unavailable via RPC;"
                                    " see import-tx in abe.conf")
                    return None

            rpc_tx = rpc_tx_hex.decode('hex')
            tx_hash = rpc_tx_hash.decode('hex')[::-1]

            computed_tx_hash = chain.transaction_hash(rpc_tx)
            if tx_hash != computed_tx_hash:
                #raise InvalidBlock('transaction hash mismatch')
                store.log.debug('transaction hash mismatch: %r != %r', tx_hash, computed_tx_hash)

            tx = chain.parse_transaction(rpc_tx)
            tx['hash'] = tx_hash
            return tx

        try:

            # Get block hash at height, and at the same time, test
            # bitcoind connectivity.
            try:
                next_hash = get_blockhash(height)
            except util.JsonrpcException, e:
                raise
            except Exception, e:
                # Connectivity failure.
                store.log.debug("RPC failed: %s", e)
                return False

            # Find the first new block.
            while height > 0:
                hash = get_blockhash(height - 1)

                if hash is not None and (1,) == store.selectrow("""
                    SELECT 1
                      FROM chain_candidate cc
                      JOIN block b ON (cc.block_id = b.block_id)
                     WHERE b.block_hash = ?
                       AND b.block_height IS NOT NULL
                       AND cc.chain_id = ?""", (
                        store.hashin_hex(str(hash)), chain.id)):
                    break

                next_hash = hash
                height -= 1

            # Import new blocks.
            rpc_hash = next_hash or get_blockhash(height)
            while rpc_hash is not None:
                hash = rpc_hash.decode('hex')[::-1]

                if store.offer_existing_block(hash, chain.id):
                    rpc_hash = get_blockhash(height + 1)
                else:
                    rpc_block = rpc("getblock", rpc_hash)
                    assert rpc_hash == rpc_block['hash']

                    prev_hash = \
                        rpc_block['previousblockhash'].decode('hex')[::-1] \
                        if 'previousblockhash' in rpc_block \
                        else chain.genesis_hash_prev

                    block = {
                        'hash':     hash,
                        'version':  int(rpc_block['version']),
                        'hashPrev': prev_hash,
                        'hashMerkleRoot':
                            rpc_block['merkleroot'].decode('hex')[::-1],
                        'nTime':    int(rpc_block['time']),
                        'nBits':    int(rpc_block['bits'], 16),
                        'nNonce':   int(rpc_block['nonce']),
                        'transactions': [],
                        'size':     int(rpc_block['size']),
                        'height':   height,
                        }

                    if chain.block_header_hash(chain.serialize_block_header(
                            block)) != hash:
                        raise InvalidBlock('block hash mismatch')

                    for rpc_tx_hash in rpc_block['tx']:
                        tx = store.export_tx(tx_hash = str(rpc_tx_hash),
                                             format = "binary")
                        if tx is None:
                            tx = get_tx(rpc_tx_hash)
                            if tx is None:
                                return False

                        block['transactions'].append(tx)

                    store.import_block(block, chain = chain)
                    store.imported_bytes(block['size'])
                    rpc_hash = rpc_block.get('nextblockhash')

                height += 1

            # Import the memory pool.
            for rpc_tx_hash in rpc("getrawmempool"):
                tx = get_tx(rpc_tx_hash)
                if tx is None:
                    return False

                # XXX Race condition in low isolation levels.
                tx_id = store.tx_find_id_and_value(tx, False)
                if tx_id is None:
                    tx_id = store.import_tx(tx, False, chain)
                    store.log.info("mempool tx %d", tx_id)
                    store.imported_bytes(tx['size'])

        except util.JsonrpcMethodNotFound, e:
            store.log.debug("bitcoind %s not supported", e.method)
            return False

        except InvalidBlock, e:
            store.log.debug("RPC data not understood: %s", e)
            return False

        return True

    # Load all blocks starting at the current file and offset.
    def catch_up_dir(store, dircfg):
        def open_blkfile(number):
            store._refresh_dircfg(dircfg)
            blkfile = {
                'stream': BCDataStream.BCDataStream(),
                'name': store.blkfile_name(dircfg, number),
                'number': number
                }

            try:
                file = open(blkfile['name'], "rb")
            except IOError, e:
                # Early bitcoind used blk0001.dat to blk9999.dat.
                # Now it uses blocks/blk00000.dat to blocks/blk99999.dat.
                # Abe starts by assuming the former scheme.  If we don't
                # find the expected file but do see blocks/blk00000.dat,
                # switch to the new scheme.  Record the switch by adding
                # 100000 to each file number, so for example, 100123 means
                # blocks/blk00123.dat but 123 still means blk0123.dat.
                if blkfile['number'] > 9999 or e.errno != errno.ENOENT:
                    raise
                new_number = 100000
                blkfile['name'] = store.blkfile_name(dircfg, new_number)
                file = open(blkfile['name'], "rb")
                blkfile['number'] = new_number

            try:
                blkfile['stream'].map_file(file, 0)
            except Exception:
                # mmap can fail on an empty file, but empty files are okay.
                file.seek(0, os.SEEK_END)
                if file.tell() == 0:
                    blkfile['stream'].input = ""
                    blkfile['stream'].read_cursor = 0
                else:
                    blkfile['stream'].map_file(file, 0)
            finally:
                file.close()
            store.log.info("Opened %s", blkfile['name'])
            return blkfile

        def try_close_file(ds):
            try:
                ds.close_file()
            except Exception, e:
                store.log.info("BCDataStream: close_file: %s", e)

        try:
            blkfile = open_blkfile(dircfg['blkfile_number'])
        except IOError, e:
            store.log.warning("Skipping datadir %s: %s", dircfg['dirname'], e)
            return

        while True:
            dircfg['blkfile_number'] = blkfile['number']
            ds = blkfile['stream']
            next_blkfile = None

            try:
                store.import_blkdat(dircfg, ds, blkfile['name'])
            except Exception:
                store.log.warning("Exception at %d" % ds.read_cursor)
                try_close_file(ds)
                raise

            if next_blkfile is None:
                # Try another file.
                try:
                    next_blkfile = open_blkfile(dircfg['blkfile_number'] + 1)
                except IOError, e:
                    if e.errno != errno.ENOENT:
                        raise
                    # No more block files.
                    return
                except Exception, e:
                    if getattr(e, 'errno', None) == errno.ENOMEM:
                        # Assume 32-bit address space exhaustion.
                        store.log.warning(
                            "Cannot allocate memory for next blockfile: "
                            "skipping safety check")
                        try_close_file(ds)
                        blkfile = open_blkfile(dircfg['blkfile_number'] + 1)
                        dircfg['blkfile_offset'] = 0
                        continue
                    raise
                finally:
                    if next_blkfile is None:
                        try_close_file(ds)

                # Load any data written to the last file since we checked.
                store.import_blkdat(dircfg, ds, blkfile['name'])

                # Continue with the new file.
                blkfile = next_blkfile

            try_close_file(ds)
            dircfg['blkfile_offset'] = 0

    # Load all blocks from the given data stream.
    def import_blkdat(store, dircfg, ds, filename="[unknown]"):
        filenum = dircfg['blkfile_number']
        ds.read_cursor = dircfg['blkfile_offset']

        while filenum == dircfg['blkfile_number']:
            if ds.read_cursor + 8 > len(ds.input):
                break

            offset = ds.read_cursor
            magic = ds.read_bytes(4)

            # Assume no real magic number starts with a NUL.
            if magic[0] == "\0":
                if filenum > 99999 and magic == "\0\0\0\0":
                    # As of Bitcoin 0.8, files often end with a NUL span.
                    ds.read_cursor = offset
                    break
                # Skip NUL bytes at block end.
                ds.read_cursor = offset
                while ds.read_cursor < len(ds.input):
                    size = min(len(ds.input) - ds.read_cursor, 1000)
                    data = ds.read_bytes(size).lstrip("\0")
                    if (data != ""):
                        ds.read_cursor -= len(data)
                        break
                store.log.info("Skipped %d NUL bytes at block end",
                               ds.read_cursor - offset)
                continue

            # Assume blocks obey the respective policy if they get here.
            chain_id = dircfg['chain_id']
            chain = store.chains_by.id.get(chain_id, None)

            if chain is None:
                chain = store.chains_by.magic.get(magic, None)

            if chain is None:
                store.log.warning(
                    "Chain not found for magic number %s in block file %s at"
                    " offset %d.", magic.encode('hex'), filename, offset)

                not_magic = magic
                # Read this file's initial magic number.
                magic = ds.input[0:4]

                if magic == not_magic:
                    ds.read_cursor = offset
                    break

                store.log.info(
                    "Scanning for initial magic number %s.",
                    magic.encode('hex'))

                ds.read_cursor = offset
                offset = ds.input.find(magic, offset)
                if offset == -1:
                    store.log.info("Magic number scan unsuccessful.")
                    break

                store.log.info(
                    "Skipped %d bytes in block file %s at offset %d.",
                    offset - ds.read_cursor, filename, ds.read_cursor)

                ds.read_cursor = offset
                continue

            length = ds.read_int32()
            if ds.read_cursor + length > len(ds.input):
                store.log.debug("incomplete block of length %d chain %d",
                                length, chain.id)
                ds.read_cursor = offset
                break
            end = ds.read_cursor + length

            hash = chain.ds_block_header_hash(ds)

            # XXX should decode target and check hash against it to
            # avoid loading garbage data.  But not for merged-mined or
            # CPU-mined chains that use different proof-of-work
            # algorithms.

            if not store.offer_existing_block(hash, chain.id):
                b = chain.ds_parse_block(ds)
                b["hash"] = hash

                if (store.log.isEnabledFor(logging.DEBUG) and b["hashPrev"] == chain.genesis_hash_prev):
                    try:
                        store.log.debug("Chain %d genesis tx: %s", chain.id,
                                        b['transactions'][0]['__data__'].encode('hex'))
                    except Exception:
                        pass

                store.import_block(b, chain = chain)
                if ds.read_cursor != end:
                    store.log.debug("Skipped %d bytes at block end",
                                    end - ds.read_cursor)

            ds.read_cursor = end

            store.bytes_since_commit += length
            if store.bytes_since_commit >= store.commit_bytes:
                store.save_blkfile_offset(dircfg, ds.read_cursor)
                store.flush()
                store._refresh_dircfg(dircfg)

        if ds.read_cursor != dircfg['blkfile_offset']:
            store.save_blkfile_offset(dircfg, ds.read_cursor)

    def blkfile_name(store, dircfg, number=None):
        if number is None:
            number = dircfg['blkfile_number']
        if number > 9999:
            return os.path.join(dircfg['dirname'], "blocks", "blk%05d.dat"
                                % (number - 100000,))
        return os.path.join(dircfg['dirname'], "blk%04d.dat" % (number,))

    def save_blkfile_offset(store, dircfg, offset):
        store.sql("""
            UPDATE datadir
               SET blkfile_number = ?,
                   blkfile_offset = ?
             WHERE datadir_id = ?""",
                  (dircfg['blkfile_number'], store.intin(offset),
                   dircfg['id']))
        if store.rowcount() == 0:
            store.sql("""
                INSERT INTO datadir (datadir_id, dirname, blkfile_number,
                    blkfile_offset, chain_id)
                VALUES (?, ?, ?, ?, ?)""",
                      (dircfg['id'], dircfg['dirname'],
                       dircfg['blkfile_number'],
                       store.intin(offset), dircfg['chain_id']))
        dircfg['blkfile_offset'] = offset

    def _refresh_dircfg(store, dircfg):
        row = store.selectrow("""
            SELECT blkfile_number, blkfile_offset
              FROM datadir
             WHERE dirname = ?""", (dircfg['dirname'],))
        if row:
            number, offset = map(int, row)
            if (number > dircfg['blkfile_number'] or
                (number == dircfg['blkfile_number'] and
                 offset > dircfg['blkfile_offset'])):
                dircfg['blkfile_number'] = number
                dircfg['blkfile_offset'] = offset

    def get_block_number(store, chain_id):
        (height,) = store.selectrow("""
            SELECT MAX(block_height)
              FROM chain_candidate
             WHERE chain_id = ?
               AND in_longest = 1""", (chain_id,))
        return -1 if height is None else int(height)

    def get_target(store, chain_id):
        rows = store.selectall("""
            SELECT b.block_nBits
              FROM block b
              JOIN chain c ON (b.block_id = c.chain_last_block_id)
             WHERE c.chain_id = ?""", (chain_id,))
        return util.calculate_target(int(rows[0][0])) if rows else None

    def get_received_and_last_block_id(store, chain_id, pubkey_hash,
                                       block_height = None):
        sql = """
            SELECT COALESCE(value_sum, 0), c.chain_last_block_id
              FROM chain c LEFT JOIN (
              SELECT cc.chain_id, SUM(txout.txout_value) value_sum
              FROM pubkey
              JOIN txout              ON (txout.pubkey_id = pubkey.pubkey_id)
              JOIN block_tx           ON (block_tx.tx_id = txout.tx_id)
              JOIN block b            ON (b.block_id = block_tx.block_id)
              JOIN chain_candidate cc ON (cc.block_id = b.block_id)
              WHERE
                  pubkey.pubkey_hash = ? AND
                  cc.chain_id = ? AND
                  cc.in_longest = 1""" + (
                  "" if block_height is None else """ AND
                  cc.block_height <= ?""") + """
              GROUP BY cc.chain_id
              ) a ON (c.chain_id = a.chain_id)
              WHERE c.chain_id = ?"""
        dbhash = store.binin(pubkey_hash)

        return store.selectrow(sql,
                               (dbhash, chain_id, chain_id)
                               if block_height is None else
                               (dbhash, chain_id, block_height, chain_id))

    def get_received(store, chain_id, pubkey_hash, block_height = None):
        return store.get_received_and_last_block_id(
            chain_id, pubkey_hash, block_height)[0]

    def get_sent_and_last_block_id(store, chain_id, pubkey_hash,
                                   block_height = None):
        sql = """
            SELECT COALESCE(value_sum, 0), c.chain_last_block_id
              FROM chain c LEFT JOIN (
              SELECT cc.chain_id, SUM(txout.txout_value) value_sum
              FROM pubkey
              JOIN txout              ON (txout.pubkey_id = pubkey.pubkey_id)
              JOIN txin               ON (txin.txout_id = txout.txout_id)
              JOIN block_tx           ON (block_tx.tx_id = txin.tx_id)
              JOIN block b            ON (b.block_id = block_tx.block_id)
              JOIN chain_candidate cc ON (cc.block_id = b.block_id)
              WHERE
                  pubkey.pubkey_hash = ? AND
                  cc.chain_id = ? AND
                  cc.in_longest = 1""" + (
                  "" if block_height is None else """ AND
                  cc.block_height <= ?""") + """
              GROUP BY cc.chain_id
              ) a ON (c.chain_id = a.chain_id)
              WHERE c.chain_id = ?"""
        dbhash = store.binin(pubkey_hash)

        return store.selectrow(sql,
                               (dbhash, chain_id, chain_id)
                               if block_height is None else
                               (dbhash, chain_id, block_height, chain_id))

    def get_sent(store, chain_id, pubkey_hash, block_height = None):
        return store.get_sent_and_last_block_id(
            chain_id, pubkey_hash, block_height)[0]

    def get_balance(store, chain_id, pubkey_hash):
        sent, last_block_id = store.get_sent_and_last_block_id(
            chain_id, pubkey_hash)
        received, last_block_id_2 = store.get_received_and_last_block_id(
            chain_id, pubkey_hash)

        # Deal with the race condition.
        for i in xrange(2):
            if last_block_id == last_block_id_2:
                break

            store.log.debug("Requerying balance: %d != %d",
                          last_block_id, last_block_id_2)

            received, last_block_id_2 = store.get_received(
                chain_id, pubkey_hash, store.get_block_height(last_block_id))

            if last_block_id == last_block_id_2:
                break

            store.log.info("Balance query affected by reorg? %d != %d",
                           last_block_id, last_block_id_2)

            sent, last_block_id = store.get_sent(
                chain_id, pubkey_hash, store.get_block_height(last_block_id_2))

        if last_block_id != last_block_id_2:
            store.log.warning("Balance query failed due to loader activity.")
            return None

        return received - sent


    def firstbits_full(store, version, hash):
        """
        Return the address in lowercase.  An initial substring of this
        will become the firstbits.
        """
        return util.hash_to_address(version, hash).lower()

    def insert_firstbits(store, pubkey_id, block_id, addr_vers, fb):
        store.sql("""
            INSERT INTO abe_firstbits (
                pubkey_id, block_id, address_version, firstbits
            )
            VALUES (?, ?, ?, ?)""",
                  (pubkey_id, block_id, addr_vers, fb))

    def cant_do_firstbits(store, addr_vers, block_id, pubkey_id):
        store.log.info(
            "No firstbits for pubkey_id %d, block_id %d, version '%s'",
            pubkey_id, block_id, store.binout_hex(addr_vers))
        store.insert_firstbits(pubkey_id, block_id, addr_vers, '')

    def do_firstbits(store, addr_vers, block_id, fb, ids, full):
        """
        Insert the firstbits that start with fb using addr_vers and
        are first seen in block_id.  Return the count of rows
        inserted.

        fb -- string, not a firstbits using addr_vers in any ancestor
        of block_id
        ids -- set of ids of all pubkeys first seen in block_id whose
        firstbits start with fb
        full -- map from pubkey_id to full firstbits
        """

        if len(ids) <= 1:
            for pubkey_id in ids:
                store.insert_firstbits(pubkey_id, block_id, addr_vers, fb)
            return len(ids)

        pubkeys = {}
        for pubkey_id in ids:
            s = full[pubkey_id]
            if s == fb:
                store.cant_do_firstbits(addr_vers, block_id, pubkey_id)
                continue
            fb1 = fb + s[len(fb)]
            ids1 = pubkeys.get(fb1)
            if ids1 is None:
                ids1 = set()
                pubkeys[fb1] = ids1
            ids1.add(pubkey_id)

        count = 0
        for fb1, ids1 in pubkeys.iteritems():
            count += store.do_firstbits(addr_vers, block_id, fb1, ids1, full)
        return count

    def do_vers_firstbits(store, addr_vers, block_id):
        """
        Create new firstbits records for block and addr_vers.  All
        ancestor blocks must have their firstbits already recorded.
        """

        address_version = store.binout(addr_vers)
        pubkeys = {}  # firstbits to set of pubkey_id
        full    = {}  # pubkey_id to full firstbits, or None if old

        for pubkey_id, pubkey_hash, oblock_id in store.selectall("""
            SELECT DISTINCT
                   pubkey.pubkey_id,
                   pubkey.pubkey_hash,
                   fb.block_id
              FROM block b
              JOIN block_tx bt ON (b.block_id = bt.block_id)
              JOIN txout ON (bt.tx_id = txout.tx_id)
              JOIN pubkey ON (txout.pubkey_id = pubkey.pubkey_id)
              LEFT JOIN abe_firstbits fb ON (
                       fb.address_version = ?
                   AND fb.pubkey_id = pubkey.pubkey_id)
             WHERE b.block_id = ?""", (addr_vers, block_id)):

            pubkey_id = int(pubkey_id)

            if (oblock_id is not None and
                store.is_descended_from(block_id, int(oblock_id))):
                full[pubkey_id] = None

            if pubkey_id in full:
                continue

            full[pubkey_id] = store.firstbits_full(address_version,
                                                   store.binout(pubkey_hash))

        for pubkey_id, s in full.iteritems():
            if s is None:
                continue

            # This is the pubkey's first appearance in the chain.
            # Find the longest match among earlier firstbits.
            longest, longest_id = 0, None
            substrs = [s[0:(i+1)] for i in xrange(len(s))]
            for ancestor_id, fblen, o_pubkey_id in store.selectall("""
                SELECT block_id, LENGTH(firstbits), pubkey_id
                  FROM abe_firstbits fb
                 WHERE address_version = ?
                   AND firstbits IN (?""" + (",?" * (len(s)-1)) + """
                       )""", tuple([addr_vers] + substrs)):
                if fblen > longest and store.is_descended_from(
                    block_id, int(ancestor_id)):
                    longest, longest_id = fblen, o_pubkey_id

            # If necessary, extend the new fb to distinguish it from
            # the longest match.
            if longest_id is not None:
                (o_hash,) = store.selectrow(
                    "SELECT pubkey_hash FROM pubkey WHERE pubkey_id = ?",
                    (longest_id,))
                o_fb = store.firstbits_full(
                    address_version, store.binout(o_hash))
                max_len = min(len(s), len(o_fb))
                while longest < max_len and s[longest] == o_fb[longest]:
                    longest += 1

            if longest == len(s):
                store.cant_do_firstbits(addr_vers, block_id, pubkey_id)
                continue

            fb = s[0 : (longest + 1)]
            ids = pubkeys.get(fb)
            if ids is None:
                ids = set()
                pubkeys[fb] = ids
            ids.add(pubkey_id)

        count = 0
        for fb, ids in pubkeys.iteritems():
            count += store.do_firstbits(addr_vers, block_id, fb, ids, full)
        return count

    def firstbits_to_addresses(store, fb, chain_id=None):
        dbfb = fb.lower()
        ret = []
        bind = [fb[0:(i+1)] for i in xrange(len(fb))]
        if chain_id is not None:
            bind.append(chain_id)

        for dbhash, vers in store.selectall("""
            SELECT pubkey.pubkey_hash,
                   fb.address_version
              FROM abe_firstbits fb
              JOIN pubkey ON (fb.pubkey_id = pubkey.pubkey_id)
              JOIN chain_candidate cc ON (cc.block_id = fb.block_id)
             WHERE fb.firstbits IN (?""" + (",?" * (len(fb)-1)) + """)""" + ( \
                "" if chain_id is None else """
               AND cc.chain_id = ?"""), tuple(bind)):
            address = util.hash_to_address(store.binout(vers),
                                           store.binout(dbhash))
            if address.lower().startswith(dbfb):
                ret.append(address)

        if len(ret) == 0 or (len(ret) > 1 and fb in ret):
            ret = [fb]  # assume exact address match

        return ret

    def get_firstbits(store, address_version=None, db_pubkey_hash=None,
                      chain_id=None):
        """
        Return address's firstbits, or the longest of multiple
        firstbits values if chain_id is not given, or None if address
        has not appeared, or the empty string if address has appeared
        but has no firstbits.
        """
        vers, dbhash = store.binin(address_version), db_pubkey_hash
        rows = store.selectall("""
            SELECT fb.firstbits
              FROM abe_firstbits fb
              JOIN pubkey ON (fb.pubkey_id = pubkey.pubkey_id)
              JOIN chain_candidate cc ON (fb.block_id = cc.block_id)
             WHERE cc.in_longest = 1
               AND fb.address_version = ?
               AND pubkey.pubkey_hash = ?""" + (
                "" if chain_id is None else """
               AND cc.chain_id = ?"""),
                               (vers, dbhash) if chain_id is None else
                               (vers, dbhash, chain_id))
        if not rows:
            return None

        ret = ""
        for (fb,) in rows:
            if len(fb) > len(ret):
                ret = fb
        return ret

def new(args):
    return DataStore(args)

########NEW FILE########
__FILENAME__ = deserialize
#
#
#

from BCDataStream import *
from enumeration import Enumeration
from base58 import public_key_to_bc_address, hash_160_to_bc_address
import logging
import socket
import time
from util import short_hex, long_hex
import struct

def parse_CAddress(vds):
  d = {}
  d['nVersion'] = vds.read_int32()
  d['nTime'] = vds.read_uint32()
  d['nServices'] = vds.read_uint64()
  d['pchReserved'] = vds.read_bytes(12)
  d['ip'] = socket.inet_ntoa(vds.read_bytes(4))
  d['port'] = socket.htons(vds.read_uint16())
  return d

def deserialize_CAddress(d):
  return d['ip']+":"+str(d['port'])+" (lastseen: %s)"%(time.ctime(d['nTime']),)

def parse_setting(setting, vds):
  if setting[0] == "f":  # flag (boolean) settings
    return str(vds.read_boolean())
  elif setting == "addrIncoming":
    return "" # bitcoin 0.4 purposely breaks addrIncoming setting in encrypted wallets.
  elif setting[0:4] == "addr": # CAddress
    d = parse_CAddress(vds)
    return deserialize_CAddress(d)
  elif setting == "nTransactionFee":
    return vds.read_int64()
  elif setting == "nLimitProcessors":
    return vds.read_int32()
  return 'unknown setting'

def parse_TxIn(vds):
  d = {}
  d['prevout_hash'] = vds.read_bytes(32)
  d['prevout_n'] = vds.read_uint32()
  d['scriptSig'] = vds.read_bytes(vds.read_compact_size())
  d['sequence'] = vds.read_uint32()
  return d

def deserialize_TxIn(d, transaction_index=None, owner_keys=None):
  if d['prevout_hash'] == "\x00"*32:
    result = "TxIn: COIN GENERATED"
    result += " coinbase:"+d['scriptSig'].encode('hex_codec')
  elif transaction_index is not None and d['prevout_hash'] in transaction_index:
    p = transaction_index[d['prevout_hash']]['txOut'][d['prevout_n']]
    result = "TxIn: value: %f"%(p['value']/1.0e8,)
    result += " prev("+long_hex(d['prevout_hash'][::-1])+":"+str(d['prevout_n'])+")"
  else:
    result = "TxIn: prev("+long_hex(d['prevout_hash'][::-1])+":"+str(d['prevout_n'])+")"
    pk = extract_public_key(d['scriptSig'])
    result += " pubkey: "+pk
    result += " sig: "+decode_script(d['scriptSig'])
  if d['sequence'] < 0xffffffff: result += " sequence: "+hex(d['sequence'])
  return result

def parse_TxOut(vds):
  d = {}
  d['value'] = vds.read_int64()
  d['scriptPubKey'] = vds.read_bytes(vds.read_compact_size())
  return d

def deserialize_TxOut(d, owner_keys=None):
  result =  "TxOut: value: %f"%(d['value']/1.0e8,)
  pk = extract_public_key(d['scriptPubKey'])
  result += " pubkey: "+pk
  result += " Script: "+decode_script(d['scriptPubKey'])
  if owner_keys is not None:
    if pk in owner_keys: result += " Own: True"
    else: result += " Own: False"
  return result

def parse_Transaction(vds, has_nTime=False):
  d = {}
  start_pos = vds.read_cursor
  d['version'] = vds.read_int32()
  if has_nTime:
    d['nTime'] = vds.read_uint32()
  n_vin = vds.read_compact_size()
  d['txIn'] = []
  for i in xrange(n_vin):
    d['txIn'].append(parse_TxIn(vds))
  n_vout = vds.read_compact_size()
  d['txOut'] = []
  for i in xrange(n_vout):
    d['txOut'].append(parse_TxOut(vds))
  d['lockTime'] = vds.read_uint32()
  d['__data__'] = vds.input[start_pos:vds.read_cursor]
  return d

def deserialize_Transaction(d, transaction_index=None, owner_keys=None, print_raw_tx=False):
  result = "%d tx in, %d out\n"%(len(d['txIn']), len(d['txOut']))
  for txIn in d['txIn']:
    result += deserialize_TxIn(txIn, transaction_index) + "\n"
  for txOut in d['txOut']:
    result += deserialize_TxOut(txOut, owner_keys) + "\n"
  if print_raw_tx == True:
      result += "Transaction hex value: " + d['__data__'].encode('hex') + "\n"
  
  return result

def parse_MerkleTx(vds):
  d = parse_Transaction(vds)
  d['hashBlock'] = vds.read_bytes(32)
  n_merkleBranch = vds.read_compact_size()
  d['merkleBranch'] = vds.read_bytes(32*n_merkleBranch)
  d['nIndex'] = vds.read_int32()
  return d

def deserialize_MerkleTx(d, transaction_index=None, owner_keys=None):
  tx = deserialize_Transaction(d, transaction_index, owner_keys)
  result = "block: "+(d['hashBlock'][::-1]).encode('hex_codec')
  result += " %d hashes in merkle branch\n"%(len(d['merkleBranch'])/32,)
  return result+tx

def parse_WalletTx(vds):
  d = parse_MerkleTx(vds)
  n_vtxPrev = vds.read_compact_size()
  d['vtxPrev'] = []
  for i in xrange(n_vtxPrev):
    d['vtxPrev'].append(parse_MerkleTx(vds))

  d['mapValue'] = {}
  n_mapValue = vds.read_compact_size()
  for i in xrange(n_mapValue):
    key = vds.read_string()
    value = vds.read_string()
    d['mapValue'][key] = value
  n_orderForm = vds.read_compact_size()
  d['orderForm'] = []
  for i in xrange(n_orderForm):
    first = vds.read_string()
    second = vds.read_string()
    d['orderForm'].append( (first, second) )
  d['fTimeReceivedIsTxTime'] = vds.read_uint32()
  d['timeReceived'] = vds.read_uint32()
  d['fromMe'] = vds.read_boolean()
  d['spent'] = vds.read_boolean()

  return d

def deserialize_WalletTx(d, transaction_index=None, owner_keys=None):
  result = deserialize_MerkleTx(d, transaction_index, owner_keys)
  result += "%d vtxPrev txns\n"%(len(d['vtxPrev']),)
  result += "mapValue:"+str(d['mapValue'])
  if len(d['orderForm']) > 0:
    result += "\n"+" orderForm:"+str(d['orderForm'])
  result += "\n"+"timeReceived:"+time.ctime(d['timeReceived'])
  result += " fromMe:"+str(d['fromMe'])+" spent:"+str(d['spent'])
  return result

# The CAuxPow (auxiliary proof of work) structure supports merged mining.
# A flag in the block version field indicates the structure's presence.
# As of 8/2011, the Original Bitcoin Client does not use it.  CAuxPow
# originated in Namecoin; see
# https://github.com/vinced/namecoin/blob/mergedmine/doc/README_merged-mining.md.
def parse_AuxPow(vds):
  d = parse_MerkleTx(vds)
  n_chainMerkleBranch = vds.read_compact_size()
  d['chainMerkleBranch'] = vds.read_bytes(32*n_chainMerkleBranch)
  d['chainIndex'] = vds.read_int32()
  d['parentBlock'] = parse_BlockHeader(vds)
  return d

def parse_BlockHeader(vds):
  d = {}
  header_start = vds.read_cursor
  d['version'] = vds.read_int32()
  d['hashPrev'] = vds.read_bytes(32)
  d['hashMerkleRoot'] = vds.read_bytes(32)
  d['nTime'] = vds.read_uint32()
  d['nBits'] = vds.read_uint32()
  d['nNonce'] = vds.read_uint32()
  header_end = vds.read_cursor
  d['__header__'] = vds.input[header_start:header_end]
  return d

def parse_Block(vds):
  d = parse_BlockHeader(vds)
  d['transactions'] = []
#  if d['version'] & (1 << 8):
#    d['auxpow'] = parse_AuxPow(vds)
  nTransactions = vds.read_compact_size()
  for i in xrange(nTransactions):
    d['transactions'].append(parse_Transaction(vds))

  return d
  
def deserialize_Block(d, print_raw_tx=False):
  result = "Time: "+time.ctime(d['nTime'])+" Nonce: "+str(d['nNonce'])
  result += "\nnBits: 0x"+hex(d['nBits'])
  result += "\nhashMerkleRoot: 0x"+d['hashMerkleRoot'][::-1].encode('hex_codec')
  result += "\nPrevious block: "+d['hashPrev'][::-1].encode('hex_codec')
  result += "\n%d transactions:\n"%len(d['transactions'])
  for t in d['transactions']:
    result += deserialize_Transaction(t, print_raw_tx=print_raw_tx)+"\n"
  result += "\nRaw block header: "+d['__header__'].encode('hex_codec')
  return result

def parse_BlockLocator(vds):
  d = { 'hashes' : [] }
  nHashes = vds.read_compact_size()
  for i in xrange(nHashes):
    d['hashes'].append(vds.read_bytes(32))
  return d

def deserialize_BlockLocator(d):
  result = "Block Locator top: "+d['hashes'][0][::-1].encode('hex_codec')
  return result

opcodes = Enumeration("Opcodes", [
    ("OP_0", 0), ("OP_PUSHDATA1",76), "OP_PUSHDATA2", "OP_PUSHDATA4", "OP_1NEGATE", "OP_RESERVED",
    "OP_1", "OP_2", "OP_3", "OP_4", "OP_5", "OP_6", "OP_7",
    "OP_8", "OP_9", "OP_10", "OP_11", "OP_12", "OP_13", "OP_14", "OP_15", "OP_16",
    "OP_NOP", "OP_VER", "OP_IF", "OP_NOTIF", "OP_VERIF", "OP_VERNOTIF", "OP_ELSE", "OP_ENDIF", "OP_VERIFY",
    "OP_RETURN", "OP_TOALTSTACK", "OP_FROMALTSTACK", "OP_2DROP", "OP_2DUP", "OP_3DUP", "OP_2OVER", "OP_2ROT", "OP_2SWAP",
    "OP_IFDUP", "OP_DEPTH", "OP_DROP", "OP_DUP", "OP_NIP", "OP_OVER", "OP_PICK", "OP_ROLL", "OP_ROT",
    "OP_SWAP", "OP_TUCK", "OP_CAT", "OP_SUBSTR", "OP_LEFT", "OP_RIGHT", "OP_SIZE", "OP_INVERT", "OP_AND",
    "OP_OR", "OP_XOR", "OP_EQUAL", "OP_EQUALVERIFY", "OP_RESERVED1", "OP_RESERVED2", "OP_1ADD", "OP_1SUB", "OP_2MUL",
    "OP_2DIV", "OP_NEGATE", "OP_ABS", "OP_NOT", "OP_0NOTEQUAL", "OP_ADD", "OP_SUB", "OP_MUL", "OP_DIV",
    "OP_MOD", "OP_LSHIFT", "OP_RSHIFT", "OP_BOOLAND", "OP_BOOLOR",
    "OP_NUMEQUAL", "OP_NUMEQUALVERIFY", "OP_NUMNOTEQUAL", "OP_LESSTHAN",
    "OP_GREATERTHAN", "OP_LESSTHANOREQUAL", "OP_GREATERTHANOREQUAL", "OP_MIN", "OP_MAX",
    "OP_WITHIN", "OP_RIPEMD160", "OP_SHA1", "OP_SHA256", "OP_HASH160",
    "OP_HASH256", "OP_CODESEPARATOR", "OP_CHECKSIG", "OP_CHECKSIGVERIFY", "OP_CHECKMULTISIG",
    "OP_CHECKMULTISIGVERIFY",
    "OP_NOP1", "OP_NOP2", "OP_NOP3", "OP_NOP4", "OP_NOP5", "OP_NOP6", "OP_NOP7", "OP_NOP8", "OP_NOP9", "OP_NOP10",
    ("OP_INVALIDOPCODE", 0xFF),
])

def script_GetOp(bytes):
  i = 0
  while i < len(bytes):
    vch = None
    opcode = ord(bytes[i])
    i += 1

    if opcode <= opcodes.OP_PUSHDATA4:
      nSize = opcode
      if opcode == opcodes.OP_PUSHDATA1:
        if i + 1 > len(bytes):
          vch = "_INVALID_NULL"
          i = len(bytes)
        else:
          nSize = ord(bytes[i])
          i += 1
      elif opcode == opcodes.OP_PUSHDATA2:
        if i + 2 > len(bytes):
          vch = "_INVALID_NULL"
          i = len(bytes)
        else:
          (nSize,) = struct.unpack_from('<H', bytes, i)
          i += 2
      elif opcode == opcodes.OP_PUSHDATA4:
        if i + 4 > len(bytes):
          vch = "_INVALID_NULL"
          i = len(bytes)
        else:
          (nSize,) = struct.unpack_from('<I', bytes, i)
          i += 4
      if i+nSize > len(bytes):
        vch = "_INVALID_"+bytes[i:]
        i = len(bytes)
      else:
        vch = bytes[i:i+nSize]
        i += nSize
    elif opcodes.OP_1 <= opcode <= opcodes.OP_16:
      vch = chr(opcode - opcodes.OP_1 + 1)
    elif opcode == opcodes.OP_1NEGATE:
      vch = chr(255)

    yield (opcode, vch)

def script_GetOpName(opcode):
  try:
    return (opcodes.whatis(opcode)).replace("OP_", "")
  except KeyError:
    return "InvalidOp_"+str(opcode)

def decode_script(bytes):
  result = ''
  for (opcode, vch) in script_GetOp(bytes):
    if len(result) > 0: result += " "
    if opcode <= opcodes.OP_PUSHDATA4:
      result += "%d:"%(opcode,)
      result += short_hex(vch)
    else:
      result += script_GetOpName(opcode)
  return result

def match_decoded(decoded, to_match):
  if len(decoded) != len(to_match):
    return False;
  for i in range(len(decoded)):
    if to_match[i] == opcodes.OP_PUSHDATA4 and decoded[i][0] <= opcodes.OP_PUSHDATA4:
      continue  # Opcodes below OP_PUSHDATA4 all just push data onto stack, and are equivalent.
    if to_match[i] != decoded[i][0]:
      return False
  return True

def extract_public_key(bytes, version='\x00'):
  try:
    decoded = [ x for x in script_GetOp(bytes) ]
  except struct.error:
    return "(None)"

  # non-generated TxIn transactions push a signature
  # (seventy-something bytes) and then their public key
  # (33 or 65 bytes) onto the stack:
  match = [ opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4 ]
  if match_decoded(decoded, match):
    return public_key_to_bc_address(decoded[1][1], version=version)

  # The Genesis Block, self-payments, and pay-by-IP-address payments look like:
  # 65 BYTES:... CHECKSIG
  match = [ opcodes.OP_PUSHDATA4, opcodes.OP_CHECKSIG ]
  if match_decoded(decoded, match):
    return public_key_to_bc_address(decoded[0][1], version=version)

  # Pay-by-Bitcoin-address TxOuts look like:
  # DUP HASH160 20 BYTES:... EQUALVERIFY CHECKSIG
  match = [ opcodes.OP_DUP, opcodes.OP_HASH160, opcodes.OP_PUSHDATA4, opcodes.OP_EQUALVERIFY, opcodes.OP_CHECKSIG ]
  if match_decoded(decoded, match):
    return hash_160_to_bc_address(decoded[2][1], version=version)

  # BIP11 TxOuts look like one of these:
  multisigs = [
    [ opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_1, opcodes.OP_CHECKMULTISIG ],
    [ opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_2, opcodes.OP_CHECKMULTISIG ],
    [ opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_3, opcodes.OP_CHECKMULTISIG ]
  ]
  for match in multisigs:
    if match_decoded(decoded, match):
      return "["+','.join([public_key_to_bc_address(decoded[i][1]) for i in range(1,len(decoded)-1)])+"]"

  # BIP16 TxOuts look like:
  # HASH160 20 BYTES:... EQUAL
  match = [ opcodes.OP_HASH160, 0x14, opcodes.OP_EQUAL ]
  if match_decoded(decoded, match):
    return hash_160_to_bc_address(decoded[1][1], version="\x05")

  return "(None)"

########NEW FILE########
__FILENAME__ = enumeration
#
# enum-like type
# From the Python Cookbook, downloaded from http://code.activestate.com/recipes/67107/
#
import types, string, exceptions

class EnumException(exceptions.Exception):
    pass

class Enumeration:
    def __init__(self, name, enumList):
        self.__doc__ = name
        lookup = { }
        reverseLookup = { }
        i = 0
        uniqueNames = [ ]
        uniqueValues = [ ]
        for x in enumList:
            if type(x) == types.TupleType:
                x, i = x
            if type(x) != types.StringType:
                raise EnumException, "enum name is not a string: " + x
            if type(i) != types.IntType:
                raise EnumException, "enum value is not an integer: " + i
            if x in uniqueNames:
                raise EnumException, "enum name is not unique: " + x
            if i in uniqueValues:
                raise EnumException, "enum value is not unique for " + x
            uniqueNames.append(x)
            uniqueValues.append(i)
            lookup[x] = i
            reverseLookup[i] = x
            i = i + 1
        self.lookup = lookup
        self.reverseLookup = reverseLookup
    def __getattr__(self, attr):
        if not self.lookup.has_key(attr):
            raise AttributeError
        return self.lookup[attr]
    def whatis(self, value):
        return self.reverseLookup[value]

########NEW FILE########
__FILENAME__ = firstbits
#!/usr/bin/env python
# Copyright(C) 2011,2012 by Abe developers.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

"""Reconfigure an Abe instance to use or not use Firstbits."""

def populate_firstbits(store):
    blocks, fbs = 0, 0
    log_incr = 1000

    for addr_vers, block_id in store.selectall("""
        SELECT c.chain_address_version,
               cc.block_id
          FROM chain c
          JOIN chain_candidate cc ON (c.chain_id = cc.chain_id)
         WHERE cc.block_height IS NOT NULL
         ORDER BY cc.chain_id, cc.block_height"""):
        fbs += store.do_vers_firstbits(addr_vers, int(block_id))
        blocks += 1
        if blocks % log_incr == 0:
            store.commit()
            store.log.info("%d firstbits in %d blocks" % (fbs, blocks))

    if blocks % log_incr > 0:
        store.commit()
        store.log.info("%d firstbits in %d blocks" % (fbs, blocks))

def create_firstbits(store):
    store.log.info("Creating firstbits table.")
    store.ddl(
        """CREATE TABLE abe_firstbits (
            pubkey_id       NUMERIC(26) NOT NULL,
            block_id        NUMERIC(14) NOT NULL,
            address_version BIT VARYING(80) NOT NULL,
            firstbits       VARCHAR(50) NOT NULL,
            PRIMARY KEY (address_version, pubkey_id, block_id),
            FOREIGN KEY (pubkey_id) REFERENCES pubkey (pubkey_id),
            FOREIGN KEY (block_id) REFERENCES block (block_id)
        )""")
    store.ddl(
        """CREATE INDEX x_abe_firstbits
            ON abe_firstbits (address_version, firstbits)""")

def drop_firstbits(store):
    store.log.info("Dropping firstbits table.")
    store.ddl("DROP TABLE abe_firstbits")

def reconfigure(store, args):
    have = store.config['use_firstbits'] == "true"
    want = args.use_firstbits
    if have == want:
        return
    lock = store.get_lock()
    try:
        # XXX Should temporarily store a new schema_version.
        if want:
            create_firstbits(store)
            populate_firstbits(store)
            store.config['use_firstbits'] = "true"
        else:
            drop_firstbits(store)
            store.config['use_firstbits'] = "false"

        store.use_firstbits = want
        store.save_configvar("use_firstbits")
        store.commit()

    finally:
        store.release_lock(lock)

########NEW FILE########
__FILENAME__ = genesis_tx
# Copyright(C) 2013 by Abe developers.

# genesis_tx.py: known transactions unavailable through RPC for
# historical reasons: https://bitcointalk.org/index.php?topic=119530.0

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

def get(tx_hash_hex):
    """
    Given the hexadecimal hash of the genesis transaction (as shown
    by, e.g., "bitcoind getblock 0") return the hexadecimal raw
    transaction.  This works around a Bitcoind limitation described at
    https://bitcointalk.org/index.php?topic=119530.0
    """

    # Main Bitcoin chain:
    if tx_hash_hex == "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b":
        return "01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff4d04ffff001d0104455468652054696d65732030332f4a616e2f32303039204368616e63656c6c6f72206f6e206272696e6b206f66207365636f6e64206261696c6f757420666f722062616e6b73ffffffff0100f2052a01000000434104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac00000000"

    # NovaCoin:
    if tx_hash_hex == "4cb33b3b6a861dcbc685d3e614a9cafb945738d6833f182855679f2fad02057b":
        return "01000000398e1151010000000000000000000000000000000000000000000000000000000000000000ffffffff4d04ffff001d020f274468747470733a2f2f626974636f696e74616c6b2e6f72672f696e6465782e7068703f746f7069633d3133343137392e6d736731353032313936236d736731353032313936ffffffff0100000000000000000000000000"

    # CryptoCash / CashCoin:
    if tx_hash_hex == "c7e715851ef2eebd4a881c48f0d6140e187d8e8f417eaacb6c6e7ed6c462dbde":
        return "010000006eb7dc52010000000000000000000000000000000000000000000000000000000000000000ffffffff7604ffff001d020f274c6c4a616e2032302c20323031342031323a3430616d204544542e204e65776567672074656173657220737567676573747320746865205553206f6e6c696e652072657461696c206769616e74206d617920626567696e20616363657074696e6720626974636f696e20736f6f6effffffff0100000000000000000000000000"

    # Hirocoin
    if tx_hash_hex == "b0019d92bc054f7418960c91e252e7d24c77719c7a30128c5f6a827c73095d2a":
        return "01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff4f04ffff001d0104474a6170616e546f6461792031332f4d61722f323031342057617973206579656420746f206d616b6520706c616e65732065617369657220746f2066696e6420696e206f6365616effffffff0100902f50090000004341040184710fa689ad5023690c80f3a49c8f13f8d45b8c857fbcbc8bc4a8e4d3eb4b10f4d4604fa08dce601aaf0f470216fe1b51850b4acf21b179c45070ac7b03a9ac00000000"

    # Bitleu
    if tx_hash_hex == "30cbad942f9fe09d06cabc91773860a827f3625a72eb2ae830c2c8844ffb6de2":
        return "01000000f8141e53010000000000000000000000000000000000000000000000000000000000000000ffffffff1904ffff001d020f27104269746c65752072656c61756e63682effffffff0100000000000000000000000000"

    # Maxcoin
    if tx_hash_hex == "f8cc3b46c273a488c318dc7d98cc053494af2871e495e17f5c7c246055e46af3":  # XXX not sure that's right
        return "01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff3c04ffff001d01043453686170652d7368696674696e6720736f66747761726520646566656e647320616761696e737420626f746e6574206861636b73ffffffff010065cd1d00000000434104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac00000000"

    # Extract your chain's genesis transaction data from the first
    # block file and add it here, or better yet, patch your coin's
    # getrawtransaction to return it on request:
    #if tx_hash_hex == "<HASH>"
    #    return "<DATA>"

    return None

########NEW FILE########
__FILENAME__ = mixup
#!/usr/bin/env python

# Copyright(C) 2012,2014 by Abe developers.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

"""Load blocks in different order for testing."""

import sys
import logging

import BCDataStream, util

def mixup_blocks(store, ds, count, datadir_chain = None, seed = None):
    bytes_done = 0
    offsets = []

    for i in xrange(count):
        if ds.read_cursor + 8 <= len(ds.input):
            offsets.append(ds.read_cursor)
            magic = ds.read_bytes(4)
            length = ds.read_int32()
            ds.read_cursor += length
            if ds.read_cursor <= len(ds.input):
                continue
        raise IOError("End of input after %d blocks" % i)

    if seed > 1 and seed <= count:
        for i in xrange(0, seed * int(count/seed), seed):
            offsets[i : i + seed] = offsets[i : i + seed][::-1]
    elif seed == -3:
        for i in xrange(0, 3 * int(count/3), 3):
            offsets[i : i + 3] = offsets[i+1 : i + 3] + [offsets[i]]
        print offsets
    elif seed:
        offsets = offsets[::-1]  # XXX want random

    for offset in offsets:
        ds.read_cursor = offset
        magic = ds.read_bytes(4)
        length = ds.read_int32()

        # Assume blocks obey the respective policy if they get here.
        chain = datadir_chain
        if chain is None:
            chain = store.chains_by.magic.get(magic)
        if chain is None:
            ds.read_cursor = offset
            raise ValueError(
                "Chain not found for magic number %s in block file at"
                " offset %d.", repr(magic), offset)
            break

        # XXX pasted out of DataStore.import_blkdat, which has since undergone
        # considerable changes.
        end = ds.read_cursor + length

        hash = util.double_sha256(
            ds.input[ds.read_cursor : ds.read_cursor + 80])
        # XXX should decode target and check hash against it to
        # avoid loading garbage data.  But not for merged-mined or
        # CPU-mined chains that use different proof-of-work
        # algorithms.  Time to resurrect policy_id?

        block_row = store.selectrow("""
            SELECT block_id, block_height, block_chain_work,
                   block_nTime, block_total_seconds,
                   block_total_satoshis, block_satoshi_seconds
              FROM block
             WHERE block_hash = ?
        """, (store.hashin(hash),))

        if block_row:
            # Block header already seen.  Don't import the block,
            # but try to add it to the chain.
            if chain is not None:
                b = {
                    "block_id":   block_row[0],
                    "height":     block_row[1],
                    "chain_work": store.binout_int(block_row[2]),
                    "nTime":      block_row[3],
                    "seconds":    block_row[4],
                    "satoshis":   block_row[5],
                    "ss":         block_row[6]}
                if store.selectrow("""
                    SELECT 1
                      FROM chain_candidate
                     WHERE block_id = ?
                       AND chain_id = ?""",
                                (b['block_id'], chain.id)):
                    store.log.info("block %d already in chain %d",
                                   b['block_id'], chain.id)
                    b = None
                else:
                    if b['height'] == 0:
                        b['hashPrev'] = GENESIS_HASH_PREV
                    else:
                        b['hashPrev'] = 'dummy'  # Fool adopt_orphans.
                    store.offer_block_to_chains(b, frozenset([chain.id]))
        else:
            b = chain.ds_parse_block(ds)
            b["hash"] = hash
            chain_ids = frozenset([] if chain is None else [chain.id])
            store.import_block(b, chain_ids = chain_ids)
            if ds.read_cursor != end:
                store.log.debug("Skipped %d bytes at block end",
                                end - ds.read_cursor)

        bytes_done += length
        if bytes_done >= store.commit_bytes:
            store.log.debug("commit")
            store.commit()
            bytes_done = 0

    if bytes_done > 0:
        store.commit()

def main(argv):
    conf = {
        "count":                    200,
        "seed":                     1,
        "blkfile":                  None,
        }
    cmdline = util.CmdLine(argv, conf)
    cmdline.usage = lambda: \
        """Usage: python -m Abe.mixup [-h] [--config=FILE] [--CONFIGVAR=VALUE]...

Load blocks out of order.

  --help                    Show this help message and exit.
  --config FILE             Read options from FILE.
  --count NUMBER            Load COUNT blocks.
  --blkfile FILE            Load the first COUNT blocks from FILE.
  --seed NUMBER             Random seed (not implemented; 0=file order).

All configuration variables may be given as command arguments."""

    store, argv = cmdline.init()
    if store is None:
        return 0
    args = store.args

    if args.blkfile is None:
        raise ValueError("--blkfile is required.")

    ds = BCDataStream.BCDataStream()
    file = open(args.blkfile, "rb")
    ds.map_file(file, 0)
    file.close()
    mixup_blocks(store, ds, int(args.count), None, int(args.seed or 0))
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

########NEW FILE########
__FILENAME__ = readconf
# Copyright(C) 2011,2012,2013 by Abe developers.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see
# <http://www.gnu.org/licenses/gpl.html>.

def looks_like_json(val):
    return val[:1] in ('"', '[', '{') or val in ('true', 'false', 'null')

def parse_argv(argv, conf={}, config_name='config', strict=False):
    arg_dict = conf.copy()
    args = lambda var: arg_dict[var]
    args.func_dict = arg_dict

    i = 0
    while i < len(argv):
        arg = argv[i]

        if arg == '--':
            i += 1
            break
        if arg[:2] != '--':
            break

        # Strip leading "--" to form a config variable.
        # --var=val and --var val are the same.  --var+=val is different.
        split = arg[2:].split('=', 1)
        adding = False
        if len(split) == 1:
            var = split[0]
            if i + 1 < len(argv) and argv[i + 1][:2] != '--':
                i += 1
                val = argv[i]
            else:
                val = True
        else:
            var, val = split
            if var[-1:] == '+':
                var = var[:-1]
                adding = True

        if val is not True and looks_like_json(val):
            val = parse_json(val)

        var = var.replace('-', '_')
        if var == config_name:
            _include(set(), val, arg_dict, config_name, strict)
        elif var not in conf:
            break
        elif adding:
            add(arg_dict, var, val)
        else:
            arg_dict[var] = val
        i += 1

    return args, argv[i:]

def include(filename, conf={}, config_name='config', strict=False):
    _include(set(), filename, conf, config_name, strict)
    return conf

class _Reader:
    __slots__ = ['fp', 'lineno', 'line']
    def __init__(rdr, fp):
        rdr.fp = fp
        rdr.lineno = 1
        rdr.line = rdr.fp.read(1)
    def eof(rdr):
        return rdr.line == ''
    def getc(rdr):
        if rdr.eof():
            return ''
        ret = rdr.line[-1]
        if ret == '\n':
            rdr.lineno += 1
            rdr.line = ''
        c = rdr.fp.read(1)
        if c == '':
            rdr.line = ''
        rdr.line += c
        return ret
    def peek(rdr):
        if rdr.eof():
            return ''
        return rdr.line[-1]
    def _readline(rdr):
        ret = rdr.fp.readline()
        rdr.line += ret
        return ret
    def readline(rdr):
        ret = rdr.peek() + rdr._readline()
        rdr.getc()  # Consume the newline if not at EOF.
        return ret
    def get_error_context(rdr, e):
        e.lineno = rdr.lineno
        if not rdr.eof():
            e.offset = len(rdr.line)
            if rdr.peek() != '\n':
                rdr._readline()
            e.text = rdr.line

def _include(seen, filename, conf, config_name, strict):
    if filename in seen:
        raise Exception('Config file recursion')

    with open(filename) as fp:
        rdr = _Reader(fp)
        try:
            entries = read(rdr)
        except SyntaxError, e:
            if e.filename is None:
                e.filename = filename
            if e.lineno is None:
                rdr.get_error_context(e)
            raise
    for var, val, additive in entries:
        var = var.replace('-', '_')
        if var == config_name:
            import os
            _include(seen | set(filename),
                     os.path.join(os.path.dirname(filename), val), conf,
                     config_name, strict)
        elif var not in conf:
            if strict:
                raise ValueError(
                    "Unknown parameter `%s' in %s" % (var, filename))
        elif additive and conf[var] is not None:
            add(conf, var, val)
        else:
            conf[var] = val
    return

def read(rdr):
    """
    Read name-value pairs from file and return the results as a list
    of triples: (name, value, additive) where "additive" is true if
    "+=" occurred between name and value.

    "NAME=VALUE" and "NAME VALUE" are equivalent.  Whitespace around
    names and values is ignored, as are lines starting with '#' and
    empty lines.  Values may be JSON strings, arrays, or objects.  A
    value that does not start with '"' or '{' or '[' and is not a
    boolean is read as a one-line string.  A line with just "NAME"
    stores True as the value.
    """
    entries = []
    def store(name, value, additive):
        entries.append((name, value, additive))

    def skipspace(rdr):
        while rdr.peek() in (' ', '\t', '\r'):
            rdr.getc()

    while True:
        skipspace(rdr)
        if rdr.eof():
            break
        if rdr.peek() == '\n':
            rdr.getc()
            continue
        if rdr.peek() == '#':
            rdr.readline()
            continue

        name = ''
        while rdr.peek() not in (' ', '\t', '\r', '\n', '=', '+', ''):
            name += rdr.getc()

        if rdr.peek() not in ('=', '+'):
            skipspace(rdr)

        if rdr.peek() in ('\n', ''):
            store(name, True, False)
            continue

        additive = False

        if rdr.peek() in ('=', '+'):
            if rdr.peek() == '+':
                rdr.getc()
                if rdr.peek() != '=':
                    raise SyntaxError("'+' without '='")
                additive = True
            rdr.getc()
            skipspace(rdr)

        if rdr.peek() in ('"', '[', '{'):
            js = scan_json(rdr)
            try:
                store(name, parse_json(js), additive)
            except ValueError, e:
                raise wrap_json_error(rdr, js, e)
            continue

        # Unquoted, one-line string.
        value = ''
        while rdr.peek() not in ('\n', ''):
            value += rdr.getc()
        value = value.strip()

        # Booleans and null.
        if value == 'true':
            value = True
        elif value == 'false':
            value = False
        elif value == 'null':
            value = None

        store(name, value, additive)

    return entries

def add(conf, var, val):
    if var not in conf:
        conf[var] = val
        return

    if isinstance(val, dict) and isinstance(conf[var], dict):
        conf[var].update(val)
        return

    if not isinstance(conf[var], list):
        conf[var] = [conf[var]]
    if isinstance(val, list):
        conf[var] += val
    else:
        conf[var].append(val)

# Scan to end of JSON object.  Grrr, why can't json.py do this without
# reading all of fp?

def _scan_json_string(rdr):
    ret = rdr.getc()  # '"'
    while True:
        c = rdr.getc()
        if c == '':
            raise SyntaxError('End of file in JSON string')

        # Accept raw control characters for readability.
        if c == '\n':
            c = '\\n'
        if c == '\r':
            c = '\\r'
        if c == '\t':
            c = '\\t'

        ret += c
        if c == '"':
            return ret
        if c == '\\':
            ret += rdr.getc()

def _scan_json_nonstring(rdr):
    # Assume we are at a number or true|false|null.
    # Scan the token.
    ret = ''
    while rdr.peek() != '' and rdr.peek() in '-+0123456789.eEtrufalsn':
        ret += rdr.getc()
    return ret

def _scan_json_space(rdr):
    # Scan whitespace including "," and ":".  Strip comments for good measure.
    ret = ''
    while not rdr.eof() and rdr.peek() in ' \t\r\n,:#':
        c = rdr.getc()
        if c == '#':
            c = rdr.readline() and '\n'
        ret += c
    return ret

def _scan_json_compound(rdr):
    # Scan a JSON array or object.
    ret = rdr.getc()
    if ret == '{': end = '}'
    if ret == '[': end = ']'
    ret += _scan_json_space(rdr)
    if rdr.peek() == end:
        return ret + rdr.getc()
    while True:
        if rdr.eof():
            raise SyntaxError('End of file in JSON value')
        ret += scan_json(rdr)
        ret += _scan_json_space(rdr)
        if rdr.peek() == end:
            return ret + rdr.getc()

def scan_json(rdr):
    # Scan a JSON value.
    c = rdr.peek()
    if c == '"':
        return _scan_json_string(rdr)
    if c in ('[', '{'):
        return _scan_json_compound(rdr)
    ret = _scan_json_nonstring(rdr)
    if ret == '':
        raise SyntaxError('Invalid JSON')
    return ret

def parse_json(js):
    import json
    return json.loads(js)

def wrap_json_error(rdr, js, e):
    import re
    match = re.search(r'(.*): line (\d+) column (\d+)', e.message, re.DOTALL)
    if match:
        e = SyntaxError(match.group(1))
        json_lineno = int(match.group(2))
        e.lineno = rdr.lineno - js.count('\n') + json_lineno - 1
        e.text = js.split('\n')[json_lineno - 1]
        e.offset = int(match.group(3))
        if json_lineno == 1 and json_line1_column_bug():
            e.offset += 1
    return e

def json_line1_column_bug():
    ret = False
    try:
        parse_json("{:")
    except ValueError, e:
        if "column 1" in e.message:
            ret = True
    finally:
        return ret

########NEW FILE########
__FILENAME__ = reconfigure
#!/usr/bin/env python
# Copyright(C) 2012,2014 by Abe developers.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

"""Reconfigure an Abe instance."""

import sys
import logging

import util
import firstbits

def keep_scriptsig_reconfigure(store, args):
    have = store.keep_scriptsig
    want = args.keep_scriptsig
    if have == want:
        return
    if want:
        store.log.warn("Can not turn on keep-scriptsig: unimplemented")
        return
    lock = store.get_lock()
    try:
        # XXX Should use a temporary schema_version.
        store.drop_view_if_exists("txin_detail")

        store.drop_column_if_exists("txin", "txin_scriptSig")
        store.drop_column_if_exists("txin", "txin_sequence")
        store.config['keep_scriptsig'] = "false"

        store.keep_scriptsig = want
        store.refresh_ddl()
        store.ddl(store.get_ddl("txin_detail"))
        store.save_configvar("keep_scriptsig")
        store.commit()
    finally:
        store.release_lock(lock)

def main(argv):
    cmdline = util.CmdLine(argv)
    cmdline.usage = lambda: \
        """Usage: python -m Abe.reconfigure [-h] [--config=FILE] [--CONFIGVAR=VALUE]...

Apply configuration changes to an existing Abe database, if possible.

  --help                    Show this help message and exit.
  --config FILE             Read options from FILE.
  --use-firstbits {true|false}
                            Turn Firstbits support on or off.
  --keep-scriptsig false    Remove input validation scripts from the database.

All configuration variables may be given as command arguments."""

    store, argv = cmdline.init()
    if store is None:
        return 0

    firstbits.reconfigure(store, args)
    keep_scriptsig_reconfigure(store, args)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

########NEW FILE########
__FILENAME__ = ripemd_via_hashlib
# RIPEMD hash interface via hashlib for those who don't have
# Crypto.Hash.RIPEMD.

import hashlib

def new(data=''):
    h = hashlib.new('ripemd160')
    h.update(data)
    return h

########NEW FILE########
__FILENAME__ = SqlAbstraction
# Copyright(C) 2011,2012,2013 by John Tobey <jtobey@john-edwin-tobey.org>

# sql.py: feature-detecting, SQL-transforming database abstraction layer

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

import re
import logging

NO_CLOB = 'BUG_NO_CLOB'
STMT_RE = re.compile(r"([^']+)((?:'[^']*')?)")

class SqlAbstraction(object):

    """
    Database abstraction class based on DB-API 2 and standard SQL with
    workarounds to support SQLite3, PostgreSQL/psycopg2, MySQL,
    Oracle, ODBC, and IBM DB2.
    """

    def __init__(sql, args):
        sql.module = args.module
        sql.connect_args = args.connect_args
        sql.prefix = args.prefix
        sql.config = args.config

        sql.log    = logging.getLogger(__name__)
        sql.sqllog = logging.getLogger(__name__ + ".sql")
        if not args.log_sql:
            sql.sqllog.setLevel(logging.WARNING)

        sql._conn = None
        sql._cursor = None
        sql.auto_reconnect = False
        sql.in_transaction = False
        sql._set_flavour()

    def _set_flavour(sql):
        def identity(x):
            return x
        transform = identity
        transform_stmt = sql._transform_stmt
        selectall = sql._selectall

        if sql.module.paramstyle in ('format', 'pyformat'):
            transform_stmt = sql._qmark_to_format(transform_stmt)
        elif sql.module.paramstyle == 'named':
            transform_stmt = sql._qmark_to_named(transform_stmt)
        elif sql.module.paramstyle != 'qmark':
            sql.log.warning("Database parameter style is "
                            "%s, trying qmark", sql.module.paramstyle)
            pass

        # Binary I/O with the database.
        # Reversed versions exist for Bitcoin hashes; since the
        # protocol treats them as 256-bit integers and represents them
        # as little endian, we have to reverse them in hex to satisfy
        # human expectations.
        def rev(x):
            return None if x is None else x[::-1]
        def to_hex(x):
            return None if x is None else str(x).encode('hex')
        def from_hex(x):
            return None if x is None else x.decode('hex')
        def to_hex_rev(x):
            return None if x is None else str(x)[::-1].encode('hex')
        def from_hex_rev(x):
            return None if x is None else x.decode('hex')[::-1]

        val = sql.config.get('binary_type')

        if val in (None, 'str', "binary"):
            binin       = identity
            binin_hex   = from_hex
            binout      = identity
            binout_hex  = to_hex
            revin       = rev
            revin_hex   = from_hex
            revout      = rev
            revout_hex  = to_hex

        elif val in ("buffer", "bytearray", "pg-bytea"):
            if val == "bytearray":
                def to_btype(x):
                    return None if x is None else bytearray(x)
            else:
                def to_btype(x):
                    return None if x is None else buffer(x)

            def to_str(x):
                return None if x is None else str(x)

            binin       = to_btype
            binin_hex   = lambda x: to_btype(from_hex(x))
            binout      = to_str
            binout_hex  = to_hex
            revin       = lambda x: to_btype(rev(x))
            revin_hex   = lambda x: to_btype(from_hex(x))
            revout      = rev
            revout_hex  = to_hex

            if val == "pg-bytea":
                transform_stmt = sql._binary_as_bytea(transform_stmt)

        elif val == "hex":
            transform = sql._binary_as_hex(transform)
            binin       = to_hex
            binin_hex   = identity
            binout      = from_hex
            binout_hex  = identity
            revin       = to_hex_rev
            revin_hex   = identity
            revout      = from_hex_rev
            revout_hex  = identity

        else:
            raise Exception("Unsupported binary-type %s" % (val,))

        val = sql.config.get('int_type')
        if val in (None, 'int'):
            intin = identity

        elif val == 'decimal':
            import decimal
            def _intin(x):
                return None if x is None else decimal.Decimal(x)
            intin = _intin

        elif val == 'str':
            def _intin(x):
                return None if x is None else str(x)
            intin = _intin
            # Work around sqlite3's integer overflow.
            transform = sql._approximate(transform)

        else:
            raise Exception("Unsupported int-type %s" % (val,))

        val = sql.config.get('sequence_type')
        if val in (None, 'update'):
            new_id = lambda key: sql._new_id_update(key)
            create_sequence = lambda key: sql._create_sequence_update(key)
            drop_sequence = lambda key: sql._drop_sequence_update(key)

        elif val == 'mysql':
            new_id = lambda key: sql._new_id_mysql(key)
            create_sequence = lambda key: sql._create_sequence_mysql(key)
            drop_sequence = lambda key: sql._drop_sequence_mysql(key)

        else:
            create_sequence = lambda key: sql._create_sequence(key)
            drop_sequence = lambda key: sql._drop_sequence(key)

            if val == 'oracle':
                new_id = lambda key: sql._new_id_oracle(key)
            elif val == 'nvf':
                new_id = lambda key: sql._new_id_nvf(key)
            elif val == 'postgres':
                new_id = lambda key: sql._new_id_postgres(key)
            elif val == 'db2':
                new_id = lambda key: sql._new_id_db2(key)
                create_sequence = lambda key: sql._create_sequence_db2(key)
            else:
                raise Exception("Unsupported sequence-type %s" % (val,))

        # Convert Oracle LOB to str.
        if hasattr(sql.module, "LOB") and isinstance(sql.module.LOB, type):
            def fix_lob(fn):
                def ret(x):
                    return None if x is None else fn(str(x))
                return ret
            binout = fix_lob(binout)
            binout_hex = fix_lob(binout_hex)

        val = sql.config.get('limit_style')
        if val in (None, 'native'):
            pass
        elif val == 'emulated':
            selectall = sql.emulate_limit(selectall)

        transform_stmt = sql._append_table_epilogue(transform_stmt)

        transform = sql._fallback_to_lob(transform)
        transform = sql._fallback_to_approximate(transform)

        sql.transform_chunk = transform
        sql.transform_stmt = transform_stmt
        sql.selectall = selectall
        sql._cache = {}

        sql.binin       = binin
        sql.binin_hex   = binin_hex
        sql.binout      = binout
        sql.binout_hex  = binout_hex
        sql.revin       = revin
        sql.revin_hex   = revin_hex
        sql.revout      = revout
        sql.revout_hex  = revout_hex

        # Might reimplement these someday...
        def binout_int(x):
            if x is None:
                return None
            return int(binout_hex(x), 16)
        def binin_int(x, bits):
            if x is None:
                return None
            return binin_hex(("%%0%dx" % (bits / 4)) % x)
        sql.binout_int  = binout_int
        sql.binin_int   = binin_int

        sql.intin       = intin
        sql.new_id      = new_id
        sql.create_sequence = create_sequence
        sql.drop_sequence = drop_sequence

    def connect(sql):
        cargs = sql.connect_args

        if cargs is None:
            conn = sql.module.connect()
        else:
            try:
                conn = sql._connect(cargs)
            except UnicodeError:
                # Perhaps this driver needs its strings encoded.
                # Python's default is ASCII.  Let's try UTF-8, which
                # should be the default anyway.
                #import locale
                #enc = locale.getlocale()[1] or locale.getdefaultlocale()[1]
                enc = 'UTF-8'
                def to_utf8(obj):
                    if isinstance(obj, dict):
                        for k in obj.keys():
                            obj[k] = to_utf8(obj[k])
                    if isinstance(obj, list):
                        return map(to_utf8, obj)
                    if isinstance(obj, unicode):
                        return obj.encode(enc)
                    return obj
                conn = sql._connect(to_utf8(cargs))
                sql.log.info("Connection required conversion to UTF-8")

        return conn

    def _connect(sql, cargs):
        if isinstance(cargs, dict):
            if ""  in cargs:
                cargs = cargs.copy()
                nkwargs = cargs[""]
                del(cargs[""])
                if isinstance(nkwargs, list):
                    return sql.module.connect(*nkwargs, **cargs)
                return sql.module.connect(nkwargs, **cargs)
            else:
                return sql.module.connect(**cargs)
        if isinstance(cargs, list):
            return sql.module.connect(*cargs)
        return sql.module.connect(cargs)

    def conn(sql):
        if sql._conn is None:
            sql._conn = sql.connect()
        return sql._conn

    def cursor(sql):
        if sql._cursor is None:
            sql._cursor = sql.conn().cursor()
        return sql._cursor

    def rowcount(sql):
        return sql.cursor().rowcount

    def reconnect(sql):
        sql.log.info("Reconnecting to database.")
        try:
            sql.close()
        except Exception:
            pass
        return sql.conn()

    # Run transform_chunk on each chunk between string literals.
    def _transform_stmt(sql, stmt):
        def transform_chunk(match):
            return sql.transform_chunk(match.group(1)) + match.group(2)
        return STMT_RE.sub(transform_chunk, stmt)

    # Convert standard placeholders to Python "format" style.
    def _qmark_to_format(sql, fn):
        def ret(stmt):
            return fn(stmt.replace('%', '%%').replace("?", "%s"))
        return ret

    # Convert standard placeholders to Python "named" style.
    def _qmark_to_named(sql, fn):
        patt = re.compile(r"\?")
        def ret(stmt):
            i = [0]
            def newname(match):
                i[0] += 1
                return ":p%d" % (i[0],)
            def transform_chunk(match):
                return patt.sub(newname, match.group(1)) + match.group(2)
            return fn(STMT_RE.sub(transform_chunk, stmt))
        return ret

    # Convert the standard BINARY type to a hex string for databases
    # and drivers that don't support BINARY.
    def _binary_as_hex(sql, fn):
        patt = re.compile(r"\b((?:VAR)?)BINARY\s*\(\s*([0-9]+)\s*\)")
        x_patt = re.compile(r"X\z")
        def fixup(match):
            return (match.group(1) + "CHAR(" +
                    str(int(match.group(2)) * 2) + ")")
        def ret(chunk):
            return fn(x_patt.sub("", patt.sub(fixup, chunk)))
        return ret

    # Convert the standard BINARY type to the PostgreSQL BYTEA type.
    def _binary_as_bytea(sql, fn):
        type_patt = re.compile("((?:VAR)?)BINARY\\(([0-9]+)\\)")
        lit_patt = re.compile("X'((?:[0-9a-fA-F][0-9a-fA-F])*)'")
        def ret(stmt):
            def transform_chunk(match):
                ret = type_patt.sub("BYTEA", match.group(1))
                if match.group(1).endswith('X') and match.group(2) != '':
                    ret = ret[:-1] + "'"
                    for i in match.group(2)[1:-1].decode('hex'):
                        ret += r'\\%03o' % ord(i)
                    ret += "'::bytea"
                else:
                    ret += match.group(2)
                return ret
            return fn(STMT_RE.sub(transform_chunk, stmt))
        return ret

    # Converts VARCHAR types that are too long to CLOB or similar.
    def _fallback_to_lob(sql, fn):
        if sql.config.get('max_varchar') is None:
            return fn
        max_varchar = int(sql.config['max_varchar'])

        if sql.config.get('clob_type') is None:
            return fn
        clob_type = sql.config['clob_type']

        patt = re.compile("VARCHAR\\(([0-9]+)\\)")

        def fixup(match):
            width = int(match.group(1))
            if width > max_varchar and clob_type != NO_CLOB:
                return clob_type
            return match.group()

        def ret(stmt):
            return fn(patt.sub(fixup, stmt))

        return ret

    # Convert high-precision NUMERIC and DECIMAL types to DOUBLE PRECISION
    # to avoid integer overflow with SQLite.
    def _fallback_to_approximate(sql, fn):
        if sql.config.get('max_precision', "") == "":
            return fn

        max_precision = int(sql.config['max_precision'])
        patt = re.compile(
            r"\b(?:NUMERIC|DECIMAL)\s*\(\s*([0-9]+)\s*(?:,.*?)?\)")

        def fixup(match):
            precision = int(match.group(1))
            if precision > max_precision:
                return "DOUBLE PRECISION"
            return match.group()

        def ret(stmt):
            return fn(patt.sub(fixup, stmt))

        return ret

    def _approximate(store, fn):
        def repl(match):
            return 'CAST(' + match.group(1) + match.group(2) + ' AS DOUBLE PRECISION) ' \
                + match.group(1) + '_approx' + match.group(2)
        def ret(stmt):
            return fn(re.sub(r'\b(\w+)(\w*) \1_approx\2\b', repl, stmt))
        return ret

    def emulate_limit(sql, selectall):
        limit_re = re.compile(r"(.*)\bLIMIT\s+(\?|\d+)\s*\Z", re.DOTALL)
        def ret(stmt, params=()):
            match = limit_re.match(sql.transform_stmt_cached(stmt))
            if match:
                if match.group(2) == '?':
                    n = params[-1]
                    params = params[:-1]
                else:
                    n = int(match.group(2))
                sql.cursor().execute(match.group(1), params)
                return [ sql.cursor().fetchone() for i in xrange(n) ]
            return selectall(stmt, params)
        return ret

    def _append_table_epilogue(sql, fn):
        epilogue = sql.config.get('create_table_epilogue', "")
        if epilogue == "":
            return fn

        patt = re.compile(r"\s*CREATE\s+TABLE\b")

        def ret(stmt):
            if patt.match(stmt):
                stmt += epilogue
            return fn(stmt)
        return ret

    def transform_stmt_cached(sql, stmt):
        cached = sql._cache.get(stmt)
        if cached is None:
            cached = sql.transform_stmt(stmt)
            sql._cache[stmt] = cached
        return cached

    def _execute(sql, stmt, params):
        try:
            sql.cursor().execute(stmt, params)
        except (sql.module.OperationalError, sql.module.InternalError, sql.module.ProgrammingError) as e:
            if sql.in_transaction or not sql.auto_reconnect:
                raise

            sql.log.warning("Replacing possible stale cursor: %s", e)

            try:
                sql.reconnect()
            except Exception:
                sql.log.exception("Failed to reconnect")
                raise e

            sql.cursor().execute(stmt, params)

    def sql(sql, stmt, params=()):
        cached = sql.transform_stmt_cached(stmt)
        sql.sqllog.info("EXEC: %s %r", cached, params)
        try:
            sql._execute(cached, params)
        except Exception as e:
            sql.sqllog.info("EXCEPTION: %s", e)
            raise
        finally:
            sql.in_transaction = True

    def ddl(sql, stmt):
        stmt = sql.transform_stmt(stmt)
        sql.sqllog.info("DDL: %s", stmt)
        try:
            sql.cursor().execute(stmt)
        except Exception as e:
            sql.sqllog.info("EXCEPTION: %s", e)
            raise
        if sql.config.get('ddl_implicit_commit') == 'false':
            sql.commit()
        else:
            sql.in_transaction = False

    def selectrow(sql, stmt, params=()):
        sql.sql(stmt, params)
        ret = sql.cursor().fetchone()
        sql.sqllog.debug("FETCH: %s", ret)
        return ret

    def _selectall(sql, stmt, params=()):
        sql.sql(stmt, params)
        ret = sql.cursor().fetchall()
        sql.sqllog.debug("FETCHALL: %s", ret)
        return ret

    def _new_id_update(sql, key):
        """
        Allocate a synthetic identifier by updating a table.
        """
        while True:
            row = sql.selectrow("SELECT nextid FROM %ssequences WHERE sequence_key = ?" % (sql.prefix), (key,))
            if row is None:
                raise Exception("Sequence %s does not exist" % key)

            ret = row[0]
            sql.sql("UPDATE %ssequences SET nextid = nextid + 1"
                    " WHERE sequence_key = ? AND nextid = ?" % sql.prefix,
                    (key, ret))
            if sql.cursor().rowcount == 1:
                return ret
            sql.log.info('Contention on %ssequences %s:%d' % sql.prefix, key, ret)

    def _get_sequence_initial_value(sql, key):
        (ret,) = sql.selectrow("SELECT MAX(" + key + "_id) FROM " + key)
        ret = 1 if ret is None else ret + 1
        return ret

    def _create_sequence_update(sql, key):
        sql.commit()
        ret = sql._get_sequence_initial_value(key)
        try:
            sql.sql("INSERT INTO %ssequences (sequence_key, nextid)"
                    " VALUES (?, ?)" % sql.prefix, (key, ret))
        except sql.module.DatabaseError as e:
            sql.rollback()
            try:
                sql.ddl("""CREATE TABLE %ssequences (
                    sequence_key VARCHAR(100) NOT NULL PRIMARY KEY,
                    nextid NUMERIC(30)
                )""" % sql.prefix)
            except Exception:
                sql.rollback()
                raise e
            sql.sql("INSERT INTO %ssequences (sequence_key, nextid)"
                    " VALUES (?, ?)" % sql.prefix, (key, ret))

    def _drop_sequence_update(sql, key):
        sql.commit()
        sql.sql("DELETE FROM %ssequences WHERE sequence_key = ?" % sql.prefix,
                (key,))
        sql.commit()

    def _new_id_oracle(sql, key):
        (ret,) = sql.selectrow("SELECT " + key + "_seq.NEXTVAL FROM DUAL")
        return ret

    def _create_sequence(sql, key):
        sql.ddl("CREATE SEQUENCE %s_seq START WITH %d"
                % (key, sql._get_sequence_initial_value(key)))

    def _drop_sequence(sql, key):
        sql.ddl("DROP SEQUENCE %s_seq" % (key,))

    def _new_id_nvf(sql, key):
        (ret,) = sql.selectrow("SELECT NEXT VALUE FOR " + key + "_seq")
        return ret

    def _new_id_postgres(sql, key):
        (ret,) = sql.selectrow("SELECT NEXTVAL('" + key + "_seq')")
        return ret

    def _create_sequence_db2(sql, key):
        sql.commit()
        try:
            rows = sql.selectall("SELECT 1 FROM %sdual" % sql.prefix)
            if len(rows) != 1:
                sql.sql("INSERT INTO %sdual(x) VALUES ('X')" % sql.prefix)
        except sql.module.DatabaseError as e:
            sql.rollback()
            sql.drop_table_if_exists('%sdual' % sql.prefix)
            sql.ddl("CREATE TABLE %sdual (x CHAR(1))" % sql.prefix)
            sql.sql("INSERT INTO %sdual(x) VALUES ('X')" % sql.prefix)
            sql.log.info("Created silly table %sdual" % sql.prefix)
        sql._create_sequence(key)

    def _new_id_db2(sql, key):
        (ret,) = sql.selectrow("SELECT NEXTVAL FOR " + key + "_seq"
                               " FROM %sdual" % sql.prefix)
        return ret

    def _create_sequence_mysql(sql, key):
        sql.ddl("CREATE TABLE %s_seq (id BIGINT AUTO_INCREMENT PRIMARY KEY)"
                " AUTO_INCREMENT=%d"
                % (key, sql._get_sequence_initial_value(key)))

    def _drop_sequence_mysql(sql, key):
        sql.ddl("DROP TABLE %s_seq" % (key,))

    def _new_id_mysql(sql, key):
        sql.sql("INSERT INTO " + key + "_seq () VALUES ()")
        (ret,) = sql.selectrow("SELECT LAST_INSERT_ID()")
        if ret % 1000 == 0:
            sql.sql("DELETE FROM " + key + "_seq WHERE id < ?", (ret,))
        return ret

    def commit(sql):
        sql.sqllog.info("COMMIT")
        sql.conn().commit()
        sql.in_transaction = False

    def rollback(sql):
        if sql.module is None:
            return
        sql.sqllog.info("ROLLBACK")
        try:
            sql.conn().rollback()
            sql.in_transaction = False
        except sql.module.OperationalError as e:
            sql.log.warning("Reconnecting after rollback error: %s", e)
            sql.reconnect()

    def close(sql):
        conn = sql._conn
        if conn is not None:
            sql.sqllog.info("CLOSE")
            conn.close()
            sql._conn = None
            sql._cursor = None

    def configure(sql):
        sql.configure_ddl_implicit_commit()
        sql.configure_create_table_epilogue()
        sql.configure_max_varchar()
        sql.configure_max_precision()
        sql.configure_clob_type()
        sql.configure_binary_type()
        sql.configure_int_type()
        sql.configure_sequence_type()
        sql.configure_limit_style()

        return sql.config

    def configure_binary_type(sql):
        defaults = ['binary', 'bytearray', 'buffer', 'hex', 'pg-bytea']
        tests = (defaults
                 if sql.config.get('binary_type') is None else
                 [ sql.config['binary_type'] ])

        for val in tests:
            sql.config['binary_type'] = val
            sql._set_flavour()
            if sql._test_binary_type():
                sql.log.info("binary_type=%s", val)
                return

        raise Exception(
            "No known binary data representation works"
            if len(tests) > 1 else
            "Binary type " + tests[0] + " fails test")

    def configure_int_type(sql):
        defaults = ['int', 'decimal', 'str']
        tests = (defaults if sql.config.get('int_type') is None else
                 [ sql.config['int_type'] ])

        for val in tests:
            sql.config['int_type'] = val
            sql._set_flavour()
            if sql._test_int_type():
                sql.log.info("int_type=%s", val)
                return
        raise Exception(
            "No known large integer representation works"
            if len(tests) > 1 else
            "Integer type " + tests[0] + " fails test")

    def configure_sequence_type(sql):
        for val in ['nvf', 'oracle', 'postgres', 'mysql', 'db2', 'update']:
            sql.config['sequence_type'] = val
            sql._set_flavour()
            if sql._test_sequence_type():
                sql.log.info("sequence_type=%s", val)
                return
        raise Exception("No known sequence type works")

    def _drop_if_exists(sql, otype, name):
        try:
            sql.sql("DROP " + otype + " " + name)
            sql.commit()
        except sql.module.DatabaseError:
            sql.rollback()

    def drop_table_if_exists(sql, obj):
        sql._drop_if_exists("TABLE", obj)
    def drop_view_if_exists(sql, obj):
        sql._drop_if_exists("VIEW", obj)

    def drop_sequence_if_exists(sql, key):
        try:
            sql.drop_sequence(key)
        except sql.module.DatabaseError:
            sql.rollback()

    def drop_column_if_exists(sql, table, column):
        try:
            sql.ddl("ALTER TABLE " + table + " DROP COLUMN " + column)
        except sql.module.DatabaseError:
            sql.rollback()

    def configure_ddl_implicit_commit(sql):
        if 'create_table_epilogue' not in sql.config:
            sql.config['create_table_epilogue'] = ''
        for val in ['true', 'false']:
            sql.config['ddl_implicit_commit'] = val
            sql._set_flavour()
            if sql._test_ddl():
                sql.log.info("ddl_implicit_commit=%s", val)
                return
        raise Exception("Can not test for DDL implicit commit.")

    def _test_ddl(sql):
        """Test whether DDL performs implicit commit."""
        sql.drop_table_if_exists("%stest_1" % sql.prefix)
        try:
            sql.ddl(
                "CREATE TABLE %stest_1 ("
                " %stest_1_id NUMERIC(12) NOT NULL PRIMARY KEY,"
                " foo VARCHAR(10))" % (sql.prefix, sql.prefix))
            sql.rollback()
            sql.selectall("SELECT MAX(%stest_1_id) FROM %stest_1"
                          % (sql.prefix, sql.prefix))
            return True
        except sql.module.DatabaseError as e:
            sql.rollback()
            return False
        except Exception:
            sql.rollback()
            return False
        finally:
            sql.drop_table_if_exists("%stest_1" % sql.prefix)

    def configure_create_table_epilogue(sql):
        for val in ['', ' ENGINE=InnoDB']:
            sql.config['create_table_epilogue'] = val
            sql._set_flavour()
            if sql._test_transaction():
                sql.log.info("create_table_epilogue='%s'", val)
                return
        raise Exception("Can not create a transactional table.")

    def _test_transaction(sql):
        """Test whether CREATE TABLE needs ENGINE=InnoDB for rollback."""
        sql.drop_table_if_exists("%stest_1" % sql.prefix)
        try:
            sql.ddl("CREATE TABLE %stest_1 (a NUMERIC(12))" % sql.prefix)
            sql.sql("INSERT INTO %stest_1 (a) VALUES (4)" % sql.prefix)
            sql.commit()
            sql.sql("INSERT INTO %stest_1 (a) VALUES (5)" % sql.prefix)
            sql.rollback()
            data = [int(row[0]) for row in sql.selectall(
                    "SELECT a FROM %stest_1" % sql.prefix)]
            return data == [4]
        except sql.module.DatabaseError as e:
            sql.rollback()
            return False
        except Exception as e:
            sql.rollback()
            return False
        finally:
            sql.drop_table_if_exists("%stest_1" % sql.prefix)

    def configure_max_varchar(sql):
        """Find the maximum VARCHAR width, up to 0xffffffff"""
        lo = 0
        hi = 1 << 32
        mid = hi - 1
        sql.config['max_varchar'] = str(mid)
        sql.drop_table_if_exists("%stest_1" % sql.prefix)
        while True:
            sql.drop_table_if_exists("%stest_1" % sql.prefix)
            try:
                sql.ddl("""CREATE TABLE %stest_1
                           (a VARCHAR(%d), b VARCHAR(%d))"""
                        % (sql.prefix, mid, mid))
                sql.sql("INSERT INTO %stest_1 (a, b) VALUES ('x', 'y')"
                        % sql.prefix)
                row = sql.selectrow("SELECT a, b FROM %stest_1"
                                    % sql.prefix)
                if [x for x in row] == ['x', 'y']:
                    lo = mid
                else:
                    hi = mid
            except sql.module.DatabaseError as e:
                sql.rollback()
                hi = mid
            except Exception as e:
                sql.rollback()
                hi = mid
            if lo + 1 == hi:
                sql.config['max_varchar'] = str(lo)
                sql.log.info("max_varchar=%s", sql.config['max_varchar'])
                break
            mid = (lo + hi) / 2
        sql.drop_table_if_exists("%stest_1" % sql.prefix)

    def configure_max_precision(sql):
        sql.config['max_precision'] = ""  # XXX

    def configure_clob_type(sql):
        """Find the name of the CLOB type, if any."""
        long_str = 'x' * 10000
        sql.drop_table_if_exists("%stest_1" % sql.prefix)
        for val in ['CLOB', 'LONGTEXT', 'TEXT', 'LONG']:
            try:
                sql.ddl("CREATE TABLE %stest_1 (a %s)" % (sql.prefix, val))
                sql.sql("INSERT INTO %stest_1 (a) VALUES (?)", (sql.prefix, sql.binin(long_str)))
                out = sql.selectrow("SELECT a FROM %stest_1" % sql.prefix)[0]
                if sql.binout(out) == long_str:
                    sql.config['clob_type'] = val
                    sql.log.info("clob_type=%s", val)
                    return
                else:
                    sql.log.debug("out=%s", repr(out))
            except sql.module.DatabaseError as e:
                sql.rollback()
            except Exception as e:
                try:
                    sql.rollback()
                except Exception:
                    # Fetching a CLOB really messes up Easysoft ODBC Oracle.
                    sql.reconnect()
                    raise
            finally:
                sql.drop_table_if_exists("%stest_1" % sql.prefix)
        sql.log.info("No native type found for CLOB.")
        sql.config['clob_type'] = NO_CLOB

    def _test_binary_type(sql):
        sql.drop_table_if_exists("%stest_1" % sql.prefix)
        try:
            # XXX The 10000 should be configurable: max_desired_binary?
            sql.ddl("""
                CREATE TABLE %stest_1 (
                    test_id NUMERIC(2) NOT NULL PRIMARY KEY,
                    test_bit BINARY(32),
                    test_varbit VARBINARY(10000))""" % sql.prefix)
            val = str(''.join(map(chr, range(0, 256, 8))))
            sql.sql("INSERT INTO %stest_1 (test_id, test_bit, test_varbit)"
                    " VALUES (?, ?, ?)" % sql.prefix,
                    (1, sql.revin(val), sql.binin(val)))
            (bit, vbit) = sql.selectrow("SELECT test_bit, test_varbit FROM %stest_1" % sql.prefix)
            if sql.revout(bit) != val:
                return False
            if sql.binout(vbit) != val:
                return False
            return True
        except sql.module.DatabaseError as e:
            sql.rollback()
            return False
        except Exception as e:
            sql.rollback()
            return False
        finally:
            sql.drop_table_if_exists("%stest_1" % sql.prefix)

    def _test_int_type(sql):
        sql.drop_view_if_exists("%stest_v1" % sql.prefix)
        sql.drop_table_if_exists("%stest_1" % sql.prefix)
        try:
            sql.ddl("""
                CREATE TABLE %stest_1 (
                    test_id NUMERIC(2) NOT NULL PRIMARY KEY,
                    i1 NUMERIC(30), i2 NUMERIC(20))""" % sql.prefix)
            # XXX No longer needed?
            sql.ddl("""
                CREATE VIEW %stest_v1 AS
                SELECT test_id,
                       i1 i1_approx,
                       i1,
                       i2
                  FROM %stest_1""" % (sql.prefix, sql.prefix))
            v1 = 2099999999999999
            v2 = 1234567890
            sql.sql("INSERT INTO %stest_1 (test_id, i1, i2)"
                    " VALUES (?, ?, ?)" % sql.prefix,
                    (1, sql.intin(v1), v2))
            sql.commit()
            prod, o1 = sql.selectrow("SELECT i1_approx * i2, i1 FROM %stest_v1" % sql.prefix)
            prod = int(prod)
            o1 = int(o1)
            if prod < v1 * v2 * 1.0001 and prod > v1 * v2 * 0.9999 and o1 == v1:
                return True
            return False
        except sql.module.DatabaseError as e:
            sql.rollback()
            return False
        except Exception as e:
            sql.rollback()
            return False
        finally:
            sql.drop_view_if_exists("%stest_v1" % sql.prefix)
            sql.drop_table_if_exists("%stest_1" % sql.prefix)

    def _test_sequence_type(sql):
        sql.drop_table_if_exists("%stest_1" % sql.prefix)
        sql.drop_sequence_if_exists("%stest_1" % sql.prefix)

        try:
            sql.ddl("""
                CREATE TABLE %stest_1 (
                    %stest_1_id NUMERIC(12) NOT NULL PRIMARY KEY,
                    foo VARCHAR(10)
                )""" % (sql.prefix, sql.prefix))
            sql.create_sequence('%stest_1' % sql.prefix)
            id1 = sql.new_id('%stest_1' % sql.prefix)
            id2 = sql.new_id('%stest_1' % sql.prefix)
            if int(id1) != int(id2):
                return True
            return False
        except sql.module.DatabaseError as e:
            sql.rollback()
            return False
        except Exception as e:
            sql.rollback()
            return False
        finally:
            sql.drop_table_if_exists("%stest_1" % sql.prefix)
            try:
                sql.drop_sequence("%stest_1" % sql.prefix)
            except sql.module.DatabaseError:
                sql.rollback()

    def configure_limit_style(sql):
        for val in ['native', 'emulated']:
            sql.config['limit_style'] = val
            sql._set_flavour()
            if sql._test_limit_style():
                sql.log.info("limit_style=%s", val)
                return
        raise Exception("Can not emulate LIMIT.")

    def _test_limit_style(sql):
        sql.drop_table_if_exists("%stest_1" % sql.prefix)
        try:
            sql.ddl("""
                CREATE TABLE %stest_1 (
                    %stest_1_id NUMERIC(12) NOT NULL PRIMARY KEY
                )""" % (sql.prefix, sql.prefix))
            for id in (2, 4, 6, 8):
                sql.sql("INSERT INTO %stest_1 (%stest_1_id) VALUES (?)"
                        % (sql.prefix, sql.prefix),
                        (id,))
            rows = sql.selectall("""
                SELECT %stest_1_id FROM %stest_1 ORDER BY %stest_1_id
                 LIMIT 3""" % (sql.prefix, sql.prefix, sql.prefix))
            return [int(row[0]) for row in rows] == [2, 4, 6]
        except sql.module.DatabaseError as e:
            sql.rollback()
            return False
        except Exception as e:
            sql.rollback()
            return False
        finally:
            sql.drop_table_if_exists("%stest_1" % sql.prefix)

########NEW FILE########
__FILENAME__ = upgrade
#!/usr/bin/env python
# Copyright(C) 2011,2012,2013,2014 by Abe developers.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

"""Upgrade to the current database schema."""

import os
import sys
import DataStore
import util

def run_upgrades_locked(store, upgrades):
    for i in xrange(len(upgrades) - 1):
        vers, func = upgrades[i]
        if store.config['schema_version'] == vers:
            sv = upgrades[i+1][0]
            store.log.warning("Upgrading schema to version: %s", sv)
            func(store)
            if sv[:3] == 'Abe':
                store.sql(
                    "UPDATE configvar SET configvar_value = ?"
                    " WHERE configvar_name = 'schema_version'",
                    (sv,))
                if store.rowcount() != 1:
                    raise Exception("Failed to update schema_version");
            else:
                store.sql(
                    "UPDATE config SET schema_version = ? WHERE config_id = 1",
                    (sv,))
            store.commit()
            store.config['schema_version'] = sv

def run_upgrades(store, upgrades):
    """Guard against concurrent upgrades."""
    lock = store.get_lock()
    try:
        run_upgrades_locked(store, upgrades)
    finally:
        store.release_lock(lock)

def add_block_value_in(store):
    store.sql("ALTER TABLE block ADD block_value_in NUMERIC(30)")
def add_block_value_out(store):
    store.sql("ALTER TABLE block ADD block_value_out NUMERIC(30)")
def add_block_total_satoshis(store):
    store.sql("ALTER TABLE block ADD block_total_satoshis NUMERIC(26)")
def add_block_total_seconds(store):
    store.sql("ALTER TABLE block ADD block_total_seconds NUMERIC(20)")
def add_block_satoshi_seconds(store):
    store.sql("ALTER TABLE block ADD block_satoshi_seconds NUMERIC(28)")
def add_block_total_ss(store):
    store.sql("ALTER TABLE block ADD block_total_ss NUMERIC(28)")
def add_satoshi_seconds_destroyed(store):
    store.sql("ALTER TABLE block_tx ADD satoshi_seconds_destroyed NUMERIC(28)")
def add_cc_block_height(store):
    store.sql("ALTER TABLE chain_candidate ADD block_height NUMERIC(14)")

def init_cc_block_height(store):
    store.sql(
"""UPDATE chain_candidate cc
    SET block_height = (
        SELECT block_height
          FROM block b
         WHERE b.block_id = cc.block_id)
""")

def index_cc_block_height(store):
    store.sql(
"""CREATE INDEX x_cc_chain_block_height
    ON chain_candidate (chain_id, block_height)""")

def index_cc_block(store):
    store.sql(
"""CREATE INDEX x_cc_block ON chain_candidate (block_id)""")

def create_block_txin(store):
    store.sql(
"""CREATE TABLE block_txin (
    block_id      NUMERIC(14),
    txin_id       NUMERIC(26),
    out_block_id  NUMERIC(14),
    PRIMARY KEY (block_id, txin_id)
)""")

def index_block_tx_tx(store):
    try:
        store.sql("DROP INDEX x_block_tx_tx")
    except Exception:
        store.rollback()
    store.sql("CREATE INDEX x_block_tx_tx ON block_tx (tx_id)")

def init_block_txin(store):
    store.log.info("Initializing block_txin.")
    count = int(store.selectrow("SELECT COUNT(1) FROM block_txin")[0] or 0)
    tried = 0
    added = 0
    seen = set()

    store.log.info("...loading existing keys")
    # XXX store.conn and store.sql_transform no longer exist.
    cur = store.conn.cursor()
    cur.execute(store.sql_transform("""
        SELECT block_id, txin_id FROM block_txin"""))
    for row in cur:
        seen.add(row)

    store.log.info("...finding output blocks")
    cur.execute(store.sql_transform("""
        SELECT bt.block_id, txin.txin_id, obt.block_id
          FROM block_tx bt
          JOIN txin USING (tx_id)
          JOIN txout USING (txout_id)
          JOIN block_tx obt ON (txout.tx_id = obt.tx_id)"""))
    for row in cur:
        (block_id, txin_id, oblock_id) = row

        if (block_id, txin_id) not in seen:
            # If oblock is an ancestor of block, insert into block_txin.
            if store.is_descended_from(block_id, oblock_id):
                store.sql("""
                    INSERT INTO block_txin (block_id, txin_id, out_block_id)
                    VALUES (?, ?, ?)""",
                          (block_id, txin_id, oblock_id))
                count += 1
                added += 1
                if count % 1000 == 0:
                    store.commit()
                    store.log.info("commit %d", count)
        tried += 1
        if tried % 1000 == 0:
            sys.stdout.write('\r%d/%d ' % (added, tried))
            sys.stdout.flush()

    store.log.info('done.')

def init_block_value_in(store):
    store.log.info("Calculating block_value_in.")
    for row in store.selectall("""
        SELECT b.block_id, SUM(txout.txout_value)
          FROM block b
          JOIN block_tx USING (block_id)
          JOIN txin USING (tx_id)
          LEFT JOIN txout USING (txout_id)
         GROUP BY b.block_id
    """):
        store.sql("UPDATE block SET block_value_in = ? WHERE block_id = ?",
                  (int(row[1] or 0), row[0]))

def init_block_value_out(store):
    store.log.info("Calculating block_value_out.")
    for row in store.selectall("""
        SELECT b.block_id, SUM(txout.txout_value)
          FROM block b
          JOIN block_tx USING (block_id)
          JOIN txout USING (tx_id)
         GROUP BY b.block_id
    """):
        store.sql("UPDATE block SET block_value_out = ? WHERE block_id = ?",
                  (int(row[1]), row[0]))

def init_block_totals(store):
    store.log.info("Calculating block total generated and age.")
    last_chain_id = None
    stats = None
    for row in store.selectall("""
        SELECT cc.chain_id, b.prev_block_id, b.block_id,
               b.block_value_out - b.block_value_in, b.block_nTime
          FROM chain_candidate cc
          JOIN block b USING (block_id)
         WHERE cc.block_height IS NOT NULL
         ORDER BY cc.chain_id, cc.block_height"""):

        chain_id, prev_id, block_id, generated, nTime = row
        generated = int(generated)
        nTime = int(nTime)

        if chain_id != last_chain_id:
            stats = {}
            last_chain_id = chain_id

        if prev_id is None:
            stats[block_id] = {
                "chain_start": nTime,
                "satoshis": generated}
        else:
            stats[block_id] = {
                "chain_start": stats[prev_id]['chain_start'],
                "satoshis": generated + stats[prev_id]['satoshis']}

        store.sql("UPDATE block SET block_total_seconds = ?,"
                  " block_total_satoshis = ?"
                  " WHERE block_id = ?",
                  (nTime - stats[block_id]['chain_start'],
                   stats[block_id]['satoshis'], block_id))

def init_satoshi_seconds_destroyed(store):
    store.log.info("Calculating satoshi-seconds destroyed.")
    count = 0
    step = 100
    start = 1
    stop = int(store.selectrow("SELECT MAX(block_id) FROM block_tx")[0])
    # XXX store.conn and store.sql_transform no longer exist.
    cur = store.conn.cursor()
    while start <= stop:
        cur.execute(store.sql_transform("""
            SELECT bt.block_id, bt.tx_id,
                   SUM(txout.txout_value * (b.block_nTime - ob.block_nTime))
              FROM block b
              JOIN block_tx bt USING (block_id)
              JOIN txin USING (tx_id)
              JOIN txout USING (txout_id)
              JOIN block_tx obt ON (txout.tx_id = obt.tx_id)
              JOIN block_txin bti ON (
                       bti.block_id = bt.block_id AND
                       bti.txin_id = txin.txin_id AND
                       obt.block_id = bti.out_block_id)
              JOIN block ob ON (bti.out_block_id = ob.block_id)
             WHERE bt.block_id >= ?
               AND bt.block_id < ?
             GROUP BY bt.block_id, bt.tx_id"""), (start, start + step))
        for row in cur:
            block_id, tx_id, destroyed = row
            sys.stdout.write("\rssd: " + str(count) + "   ")
            count += 1
            store.sql("UPDATE block_tx SET satoshi_seconds_destroyed = ?"
                      " WHERE block_id = ? AND tx_id = ?",
                      (destroyed, block_id, tx_id))
        start += step
    store.log.info("done.")

def set_0_satoshi_seconds_destroyed(store):
    store.log.info("Setting NULL to 0 in satoshi_seconds_destroyed.")
    # XXX store.conn and store.sql_transform no longer exist.
    cur = store.conn.cursor()
    cur.execute(store.sql_transform("""
        SELECT bt.block_id, bt.tx_id
          FROM block_tx bt
          JOIN block b USING (block_id)
         WHERE b.block_height IS NOT NULL
           AND bt.satoshi_seconds_destroyed IS NULL"""))
    for row in cur:
        store.sql("""
            UPDATE block_tx bt SET satoshi_seconds_destroyed = 0
             WHERE block_id = ? AND tx_id = ?""", row)

def init_block_satoshi_seconds(store, ):
    store.log.info("Calculating satoshi-seconds.")
    # XXX store.conn and store.sql_transform no longer exist.
    cur = store.conn.cursor()
    stats = {}
    cur.execute(store.sql_transform("""
        SELECT b.block_id, b.block_total_satoshis, b.block_nTime,
               b.prev_block_id, SUM(bt.satoshi_seconds_destroyed),
               b.block_height
          FROM block b
          JOIN block_tx bt ON (b.block_id = bt.block_id)
         GROUP BY b.block_id, b.block_total_satoshis, b.block_nTime,
               b.prev_block_id, b.block_height
         ORDER BY b.block_height"""))
    count = 0
    while True:
        row = cur.fetchone()
        if row is None:
            break
        block_id, satoshis, nTime, prev_id, destroyed, height = row
        satoshis = int(satoshis)
        destroyed = int(destroyed)
        if height is None:
            continue
        if prev_id is None:
            stats[block_id] = {
                "satoshis": satoshis,
                "ss": 0,
                "total_ss": 0,
                "nTime": nTime}
        else:
            created = (stats[prev_id]['satoshis']
                       * (nTime - stats[prev_id]['nTime']))
            stats[block_id] = {
                "satoshis": satoshis,
                "ss": stats[prev_id]['ss'] + created - destroyed,
                "total_ss": stats[prev_id]['total_ss'] + created,
                "nTime": nTime}
        store.sql("""
            UPDATE block
               SET block_satoshi_seconds = ?,
                   block_total_ss = ?,
                   block_ss_destroyed = ?
             WHERE block_id = ?""",
                  (store.intin(stats[block_id]['ss']),
                   store.intin(stats[block_id]['total_ss']),
                   store.intin(destroyed),
                   block_id))
        count += 1
        if count % 1000 == 0:
            store.commit()
            store.log.info("Updated %d blocks", count)
    if count % 1000 != 0:
        store.log.info("Updated %d blocks", count)

def index_block_nTime(store):
    store.log.info("Indexing block_nTime.")
    store.sql("CREATE INDEX x_block_nTime ON block (block_nTime)")

def replace_chain_summary(store):
    store.sql("DROP VIEW chain_summary")
    store.sql("""
        CREATE VIEW chain_summary AS SELECT
            cc.chain_id,
            cc.in_longest,
            b.block_id,
            b.block_hash,
            b.block_version,
            b.block_hashMerkleRoot,
            b.block_nTime,
            b.block_nBits,
            b.block_nNonce,
            cc.block_height,
            b.prev_block_id,
            prev.block_hash prev_block_hash,
            b.block_chain_work,
            b.block_num_tx,
            b.block_value_in,
            b.block_value_out,
            b.block_total_satoshis,
            b.block_total_seconds,
            b.block_satoshi_seconds,
            b.block_total_ss,
            b.block_ss_destroyed
        FROM chain_candidate cc
        JOIN block b ON (cc.block_id = b.block_id)
        LEFT JOIN block prev ON (b.prev_block_id = prev.block_id)""")

def drop_block_ss_columns(store):
    """Drop columns that may have been added in error."""
    for c in ['created', 'destroyed']:
        try:
            store.sql("ALTER TABLE block DROP COLUMN block_ss_" + c)
        except Exception:
            store.rollback()

def add_constraint(store, table, name, constraint):
    try:
        store.sql("ALTER TABLE " + table + " ADD CONSTRAINT " + name +
                  " " + constraint)
    except Exception:
        store.log.exception(
            "Failed to create constraint on table " + table + ": " +
            constraint + "; ignoring error.")
        store.rollback()

def add_fk_block_txin_block_id(store):
    add_constraint(store, "block_txin", "fk1_block_txin",
                   "FOREIGN KEY (block_id) REFERENCES block (block_id)")

def add_fk_block_txin_tx_id(store):
    add_constraint(store, "block_txin", "fk2_block_txin",
                   "FOREIGN KEY (txin_id) REFERENCES txin (txin_id)")

def add_fk_block_txin_out_block_id(store):
    add_constraint(store, "block_txin", "fk3_block_txin",
                   "FOREIGN KEY (out_block_id) REFERENCES block (block_id)")

def add_chk_block_txin_out_block_id_nn(store):
    add_constraint(store, "block_txin", "chk3_block_txin",
                   "CHECK (out_block_id IS NOT NULL)")

def create_x_cc_block_id(store):
    store.sql("CREATE INDEX x_cc_block_id ON chain_candidate (block_id)")

def reverse_binary_hashes(store):
    if store.config['binary_type'] != 'hex':
        raise Error(
            'To support search by hash prefix, we have to reverse all values'
            ' in block.block_hash, block.block_hashMerkleRoot, tx.tx_hash,'
            ' orphan_block.block_hashPrev, and unlinked_txin.txout_tx_hash.'
            ' This has not been automated. You may perform this step manually,'
            ' then issue "UPDATE config SET schema_version = \'9.1\'" and'
            ' rerun this program.')

def drop_x_cc_block_id(store):
    """Redundant with x_cc_block"""
    store.sql("DROP INDEX x_cc_block_id")

def create_x_cc_block_height(store):
    store.sql(
        "CREATE INDEX x_cc_block_height ON chain_candidate (block_height)")

def create_txout_approx(store):
    store.sql("""
        CREATE VIEW txout_approx AS SELECT
            txout_id,
            tx_id,
            txout_value txout_approx_value
          FROM txout""")

def add_fk_chain_candidate_block_id(store):
    add_constraint(store, "chain_candidate", "fk1_chain_candidate",
                   "FOREIGN KEY (block_id) REFERENCES block (block_id)")

def create_configvar(store):
    store.sql("""
        CREATE TABLE configvar (
            configvar_name  VARCHAR(100) NOT NULL PRIMARY KEY,
            configvar_value VARCHAR(255)
        )""")

def configure(store):
    # XXX This won't work anymore.
    store.args.binary_type = store.config['binary_type']
    store.configure()
    store.save_config()

def populate_abe_sequences(store):
    if store.config['sql.sequence_type'] == 'update':
        try:
            store.sql("""CREATE TABLE abe_sequences (
                             key VARCHAR(100) NOT NULL PRIMARY KEY,
                             nextid NUMERIC(30)
                         )""")
        except Exception:
            store.rollback()
        for t in ['block', 'tx', 'txin', 'txout', 'pubkey',
                  'chain', 'magic', 'policy']:
            (last_id,) = store.selectrow("SELECT MAX(" + t + "_id) FROM " + t)
            if last_id is None:
                continue
            store.sql("UPDATE abe_sequences SET nextid = ? WHERE key = ?"
                      " AND nextid <= ?",
                      (last_id + 1, t, last_id))
            if store.rowcount() < 1:
                store.sql("INSERT INTO abe_sequences (key, nextid)"
                          " VALUES (?, ?)", (t, last_id + 1))

def add_datadir_chain_id(store):
    store.sql("ALTER TABLE datadir ADD chain_id NUMERIC(10) NULL")

def noop(store):
    pass

def rescan_if_missed_blocks(store):
    """
    Due to a bug, some blocks may have been loaded but not placed in
    a chain.  If so, reset all datadir offsets to 0 to force a rescan.
    """
    (bad,) = store.selectrow("""
        SELECT COUNT(1)
          FROM block
          LEFT JOIN chain_candidate USING (block_id)
         WHERE chain_id IS NULL
    """)
    if bad > 0:
        store.sql(
            "UPDATE datadir SET blkfile_number = 1, blkfile_offset = 0")

def insert_missed_blocks(store):
    """
    Rescanning doesn't always work due to timeouts and resource
    constraints.  This may help.
    """
    missed = []
    for row in store.selectall("""
        SELECT b.block_id
          FROM block b
          LEFT JOIN chain_candidate cc ON (b.block_id = cc.block_id)
         WHERE chain_id IS NULL
         ORDER BY b.block_height
    """):
        missed.append(row[0])
    if not missed:
        return
    store.log.info("Attempting to repair %d missed blocks.", len(missed))
    inserted = 0
    for block_id in missed:
        # Insert block if its previous block is in the chain.
        # XXX This won't work if we want to support forks.
        # XXX This doesn't work for unattached blocks.
        store.sql("""
            INSERT INTO chain_candidate (
                chain_id, block_id, block_height, in_longest)
            SELECT cc.chain_id, b.block_id, b.block_height, 0
              FROM chain_candidate cc
              JOIN block prev ON (cc.block_id = prev.block_id)
              JOIN block b ON (b.prev_block_id = prev.block_id)
             WHERE b.block_id = ?""", (block_id,))
        inserted += store.rowcount()
        store.commit()  # XXX not sure why PostgreSQL needs this.
    store.log.info("Inserted %d rows into chain_candidate.", inserted)

def repair_missed_blocks(store):
    store.log.info("Finding longest chains.")
    best_work = []
    for row in store.selectall("""
        SELECT cc.chain_id, MAX(b.block_chain_work)
          FROM chain_candidate cc
          JOIN block b USING (block_id)
         GROUP BY cc.chain_id"""):
        best_work.append(row)
    best = []
    for row in best_work:
        chain_id, bcw = row
        (block_id,) = store.selectrow("""
            SELECT MIN(block_id)
              FROM block b
              JOIN chain_candidate cc USING (block_id)
             WHERE cc.chain_id = ?
               AND b.block_chain_work = ?
        """, (chain_id, bcw))
        (in_longest,) = store.selectrow("""
            SELECT in_longest
              FROM chain_candidate
             WHERE chain_id = ?
               AND block_id = ?
        """, (chain_id, block_id))
        if in_longest == 1:
            store.log.info("Chain %d already has the block of greatest work.",
                           chain_id)
            continue
        best.append([chain_id, block_id])
        store.sql("""
            UPDATE chain
               SET chain_last_block_id = ?
             WHERE chain_id = ?""",
                  (block_id, chain_id))
        if store.rowcount() == 1:
            store.log.info("Chain %d block %d", chain_id, block_id)
        else:
            raise Exception("Wrong rowcount updating chain " + str(chain_id))
    if not best:
        return
    store.log.info("Marking blocks in longest chains.")
    for elt in best:
        chain_id, block_id = elt
        count = 0
        while True:
            store.sql("""
                UPDATE chain_candidate
                   SET in_longest = 1
                 WHERE chain_id = ?
                   AND block_id = ?""",
                      (chain_id, block_id))
            if store.rowcount() != 1:
                raise Exception("Wrong rowcount updating chain_candidate ("
                                + str(chain_id) + ", " + str(block_id) + ")")
            count += 1
            row = store.selectrow("""
                SELECT b.prev_block_id, cc.in_longest
                  FROM block b
                  JOIN chain_candidate cc ON (b.prev_block_id = cc.block_id)
                 WHERE cc.chain_id = ?
                   AND b.block_id = ?""",
                                  (chain_id, block_id))
            if row is None:
                break  # genesis block?
            block_id, in_longest = row
            if in_longest == 1:
                break
        store.log.info("Processed %d in chain %d", count, chain_id)
    store.log.info("Repair successful.")

def add_block_num_tx(store):
    store.sql("ALTER TABLE block ADD block_num_tx NUMERIC(10)")

def add_block_ss_destroyed(store):
    store.sql("ALTER TABLE block ADD block_ss_destroyed NUMERIC(28)")

def init_block_tx_sums(store):
    store.log.info("Calculating block_num_tx and block_ss_destroyed.")
    rows = store.selectall("""
        SELECT block_id,
               COUNT(1),
               COUNT(satoshi_seconds_destroyed),
               SUM(satoshi_seconds_destroyed)
          FROM block
          JOIN block_tx USING (block_id)
         GROUP BY block_id""")
    count = 0
    store.log.info("Storing block_num_tx and block_ss_destroyed.")
    for row in rows:
        block_id, num_tx, num_ssd, ssd = row
        if num_ssd < num_tx:
            ssd = None
        store.sql("""
            UPDATE block
               SET block_num_tx = ?,
                   block_ss_destroyed = ?
             WHERE block_id = ?""",
                  (num_tx, ssd, block_id))
        count += 1
        if count % 1000 == 0:
            store.commit()
    # XXX would like to set NOT NULL on block_num_tx.

def config_ddl(store):
    # XXX This won't work anymore.
    store.configure_ddl_implicit_commit()
    store.save_configvar("ddl_implicit_commit")

def config_create_table_epilogue(store):
    # XXX This won't work anymore.
    store.configure_create_table_epilogue()
    store.save_configvar("create_table_epilogue")

def rename_abe_sequences_key(store):
    """Drop and recreate abe_sequences with key renamed to sequence_key."""
    # Renaming a column is horribly unportable.
    try:
        data = store.selectall("""
            SELECT DISTINCT key, nextid
              FROM abe_sequences""")
    except Exception:
        store.rollback()
        return
    store.log.info("copying sequence positions: %s", data)
    store.ddl("DROP TABLE abe_sequences")
    store.ddl("""CREATE TABLE abe_sequences (
        sequence_key VARCHAR(100) PRIMARY KEY,
        nextid NUMERIC(30)
    )""")
    for row in data:
        store.sql("INSERT INTO abe_sequences (sequence_key, nextid)"
                  " VALUES (?, ?)", row)

def create_x_txin_txout(store):
    store.sql("CREATE INDEX x_txin_txout ON txin (txout_id)")

def save_datadir(store):
    """Copy the datadir table to recreate it with a new column."""
    store.sql("CREATE TABLE abe_tmp_datadir AS SELECT * FROM datadir")

def add_datadir_id(store):
    data = store.selectall("""
        SELECT dirname, blkfile_number, blkfile_offset, chain_id
          FROM abe_tmp_datadir""")
    try:
        store.ddl("DROP TABLE datadir")
    except Exception:
        store.rollback()  # Assume already dropped.

    store.ddl("""CREATE TABLE datadir (
        datadir_id  NUMERIC(10) PRIMARY KEY,
        dirname     VARCHAR(2000) NOT NULL,
        blkfile_number NUMERIC(4) NULL,
        blkfile_offset NUMERIC(20) NULL,
        chain_id    NUMERIC(10) NULL
    )""")
    store.create_sequence("datadir")
    for row in data:
        new_row = [store.new_id("datadir")]
        new_row += row
        store.sql("""
            INSERT INTO datadir (
                datadir_id, dirname, blkfile_number, blkfile_offset, chain_id
            ) VALUES (?, ?, ?, ?, ?)""", new_row)

def drop_tmp_datadir(store):
    store.ddl("DROP TABLE abe_tmp_datadir")

def config_clob(store):
    # This won't work anymore.
    store.configure_max_varchar()
    store.save_configvar("max_varchar")
    store.configure_clob_type()
    store.save_configvar("clob_type")

def clear_bad_addresses(store):
    """Set address=Unknown for the bogus outputs in Bitcoin 71036."""
    bad_tx = [
        'a288fec5559c3f73fd3d93db8e8460562ebfe2fcf04a5114e8d0f2920a6270dc',
        '2a0597e665ac3d1cabeede95cedf907934db7f639e477b3c77b242140d8cf728',
        'e411dbebd2f7d64dafeef9b14b5c59ec60c36779d43f850e5e347abee1e1a455']
    for tx_hash in bad_tx:
        row = store.selectrow("""
            SELECT tx_id FROM tx WHERE tx_hash = ?""",
                              (store.hashin_hex(tx_hash),))
        if row:
            store.sql("""
                UPDATE txout SET pubkey_id = NULL
                 WHERE tx_id = ? AND txout_pos = 1 AND pubkey_id IS NOT NULL""",
                      (row[0],))
            if store.rowcount():
                store.log.info("Cleared txout %s", tx_hash)

def find_namecoin_addresses(store):
    updated = 0
    for tx_id, txout_pos, script in store.selectall("""
        SELECT tx_id, txout_pos, txout_scriptPubKey
          FROM txout
         WHERE pubkey_id IS NULL"""):
        pubkey_id = store.script_to_pubkey_id(store.binout(script))
        if pubkey_id is not None:
            store.sql("""
                UPDATE txout
                   SET pubkey_id = ?
                 WHERE tx_id = ?
                   AND txout_pos = ?""", (pubkey_id, tx_id, txout_pos))
            updated += 1
            if updated % 1000 == 0:
                store.commit()
                store.log.info("Found %d addresses", updated)
    if updated % 1000 > 0:
        store.commit()
        store.log.info("Found %d addresses", updated)

def create_abe_lock(store):
    store.ddl("""CREATE TABLE abe_lock (
        lock_id       NUMERIC(10) NOT NULL PRIMARY KEY,
        pid           VARCHAR(255) NULL
    )""")

def create_abe_lock_row(store):
    store.sql("INSERT INTO abe_lock (lock_id) VALUES (1)")

def insert_null_pubkey(store):
    dbnull = store.binin(DataStore.NULL_PUBKEY_HASH)
    row = store.selectrow("SELECT pubkey_id FROM pubkey WHERE pubkey_hash = ?",
                          (dbnull,))
    if row:
        # Null hash seen in a transaction.  Go to some trouble to
        # set its pubkey_id = 0 without violating constraints.
        old_id = row[0]
        import random  # No need for cryptographic strength here.
        temp_hash = "".join([chr(random.randint(0, 255)) for x in xrange(20)])
        store.sql("INSERT INTO pubkey (pubkey_id, pubkey_hash) VALUES (?, ?)",
                  (DataStore.NULL_PUBKEY_ID, store.binin(temp_hash)))
        store.sql("UPDATE txout SET pubkey_id = ? WHERE pubkey_id = ?",
                  (DataStore.NULL_PUBKEY_ID, old_id))
        store.sql("DELETE FROM pubkey WHERE pubkey_id = ?", (old_id,))
        store.sql("UPDATE pubkey SET pubkey_hash = ? WHERE pubkey_id = ?",
                  (dbnull, DataStore.NULL_PUBKEY_ID))
    else:
        store.sql("""
            INSERT INTO pubkey (pubkey_id, pubkey_hash) VALUES (?, ?)""",
                  (DataStore.NULL_PUBKEY_ID, dbnull))

def set_netfee_pubkey_id(store):
    store.log.info("Updating network fee output address to 'Destroyed'...")
    # XXX This doesn't work for Oracle because of LOB weirdness.
    # There, you could probably get away with:
    # UPDATE txout SET pubkey_id = 0 WHERE txout_scriptPubKey BETWEEN 1 AND 2;
    # UPDATE configvar SET configvar_value = 'Abe26' WHERE configvar_name =
    #     'schema_version' AND configvar_value = 'Abe25.3';
    # COMMIT;
    store.sql("""
        UPDATE txout
           SET pubkey_id = ?
         WHERE txout_scriptPubKey = ?""",
              (DataStore.NULL_PUBKEY_ID,
               store.binin(DataStore.SCRIPT_NETWORK_FEE)))
    store.log.info("...rows updated: %d", store.rowcount())

def adjust_block_total_satoshis(store):
    store.log.info("Adjusting value outstanding for lost coins.")
    block = {}
    block_ids = []

    store.log.info("...getting block relationships.")
    for block_id, prev_id in store.selectall("""
        SELECT block_id, prev_block_id
          FROM block
         WHERE block_height IS NOT NULL
         ORDER BY block_height"""):
        block[block_id] = {"prev_id": prev_id}
        block_ids.append(block_id)

    store.log.info("...getting lossage per block.")
    for block_id, lost in store.selectall("""
        SELECT block_tx.block_id, SUM(txout.txout_value)
          FROM block_tx
          JOIN txout ON (block_tx.tx_id = txout.tx_id)
         WHERE txout.pubkey_id <= 0
         GROUP BY block_tx.block_id"""):
        if block_id in block:
            block[block_id]["lost"] = lost

    store.log.info("...calculating adjustments.")
    for block_id in block_ids:
        b = block[block_id]
        prev_id = b["prev_id"]
        prev_lost = 0 if prev_id is None else block[prev_id]["cum_lost"]
        b["cum_lost"] = b.get("lost", 0) + prev_lost

    store.log.info("...applying adjustments.")
    count = 0
    for block_id in block_ids:
        adj = block[block_id]["cum_lost"]
        if adj != 0:
            store.sql("""
                UPDATE block
                  SET block_total_satoshis = block_total_satoshis - ?
                WHERE block_id = ?""",
                      (adj, block_id))
        count += 1
        if count % 1000 == 0:
            store.log.info("Adjusted %d of %d blocks.", count, len(block_ids))
    if count % 1000 != 0:
        store.log.info("Adjusted %d of %d blocks.", count, len(block_ids))

def config_limit_style(store):
    # XXX This won't work anymore.
    store.configure_limit_style()
    store.save_configvar("limit_style")

def config_sequence_type(store):
    # XXX This won't work anymore.
    if store.config['sequence_type'] != "update":
        return
    store.configure_sequence_type()
    if store.config['sequence_type'] != "update":
        store.log.info("Creating native sequences.")
        for name in ['magic', 'policy', 'chain', 'datadir',
                     'tx', 'txout', 'pubkey', 'txin', 'block']:
            store.get_db().drop_sequence_if_exists(name)
            store.create_sequence(name)
    store.save_configvar("sequence_type")

def add_search_block_id(store):
    store.log.info("Creating block.search_block_id")
    store.sql("ALTER TABLE block ADD search_block_id NUMERIC(14) NULL")

def populate_search_block_id(store):
    store.log.info("Calculating block.search_block_id")

    for block_id, height, prev_id in store.selectall("""
        SELECT block_id, block_height, prev_block_id
          FROM block
         WHERE block_height IS NOT NULL
         ORDER BY block_height"""):
        height = int(height)

        search_id = None
        if prev_id is not None:
            prev_id = int(prev_id)
            search_height = util.get_search_height(height)
            if search_height is not None:
                search_id = store.get_block_id_at_height(search_height, prev_id)
            store.sql("UPDATE block SET search_block_id = ? WHERE block_id = ?",
                      (search_id, block_id))
        store.cache_block(int(block_id), height, prev_id, search_id)
    store.commit()

def add_fk_search_block_id(store):
    add_constraint(store, "block", "fk1_search_block_id",
                   "FOREIGN KEY (search_block_id) REFERENCES block (block_id)")

def create_firstbits(store):
    flag = store.config.get('use_firstbits')

    if flag is None:
        if store.args.use_firstbits is None:
            store.log.info("use_firstbits not found, defaulting to false.")
            store.config['use_firstbits'] = "false"
            store.save_configvar("use_firstbits")
            return
        flag = "true" if store.args.use_firstbits else "false"
        store.config['use_firstbits'] = flag
        store.save_configvar("use_firstbits")

    if flag == "true":
        import firstbits
        firstbits.create_firstbits(store)

def populate_firstbits(store):
    if store.config['use_firstbits'] == "true":
        import firstbits
        firstbits.populate_firstbits(store)

def add_keep_scriptsig(store):
    store.config['keep_scriptsig'] = "true"
    store.save_configvar("keep_scriptsig")

def drop_satoshi_seconds_destroyed(store):
    store.get_db().drop_column_if_exists("block_txin", "satoshi_seconds_destroyed")

def widen_blkfile_number(store):
    data = store.selectall("""
        SELECT datadir_id, dirname, blkfile_number, blkfile_offset, chain_id
          FROM abe_tmp_datadir""")
    store.get_db().drop_table_if_exists("datadir")

    store.ddl("""CREATE TABLE datadir (
        datadir_id  NUMERIC(10) NOT NULL PRIMARY KEY,
        dirname     VARCHAR(2000) NOT NULL,
        blkfile_number NUMERIC(8) NULL,
        blkfile_offset NUMERIC(20) NULL,
        chain_id    NUMERIC(10) NULL
    )""")
    for row in data:
        store.sql("""
            INSERT INTO datadir (
                datadir_id, dirname, blkfile_number, blkfile_offset, chain_id
            ) VALUES (?, ?, ?, ?, ?)""", row)

def add_datadir_loader(store):
    store.sql("ALTER TABLE datadir ADD datadir_loader VARCHAR(100) NULL")

def add_chain_policy(store):
    store.ddl("ALTER TABLE chain ADD chain_policy VARCHAR(255)")

def populate_chain_policy(store):
    store.sql("UPDATE chain SET chain_policy = chain_name")

def add_chain_magic(store):
    store.ddl("ALTER TABLE chain ADD chain_magic BINARY(4)")

def populate_chain_magic(store):
    for chain_id, magic in store.selectall("""
        SELECT chain.chain_id, magic.magic
          FROM chain
          JOIN magic ON (chain.magic_id = magic.magic_id)"""):
        store.sql("UPDATE chain SET chain_magic = ? WHERE chain_id = ?",
                  (magic, chain_id))

def drop_policy(store):
    for stmt in [
        "ALTER TABLE chain DROP COLUMN policy_id",
        "DROP TABLE policy"]:
        try:
            store.ddl(stmt)
        except store.dbmodule.DatabaseError, e:
            store.log.warning("Cleanup failed, ignoring: %s", stmt)

def drop_magic(store):
    for stmt in [
        "ALTER TABLE chain DROP COLUMN magic_id",
        "DROP TABLE magic"]:
        try:
            store.ddl(stmt)
        except store.dbmodule.DatabaseError, e:
            store.log.warning("Cleanup failed, ignoring: %s", stmt)

def add_chain_decimals(store):
    store.ddl("ALTER TABLE chain ADD chain_decimals NUMERIC(2)")

def insert_chain_novacoin(store):
    import Chain
    try:
        store.insert_chain(Chain.create("NovaCoin"))
    except Exception:
        pass

def txin_detail_multisig(store):
    store.get_db().drop_view_if_exists('txin_detail')
    store.ddl("""
        CREATE VIEW txin_detail AS SELECT
            cc.chain_id,
            cc.in_longest,
            cc.block_id,
            b.block_hash,
            b.block_height,
            block_tx.tx_pos,
            tx.tx_id,
            tx.tx_hash,
            tx.tx_lockTime,
            tx.tx_version,
            tx.tx_size,
            txin.txin_id,
            txin.txin_pos,
            txin.txout_id prevout_id""" + (""",
            txin.txin_scriptSig,
            txin.txin_sequence""" if store.keep_scriptsig else """,
            NULL txin_scriptSig,
            NULL txin_sequence""") + """,
            prevout.txout_value txin_value,
            prevout.txout_scriptPubKey txin_scriptPubKey,
            pubkey.pubkey_id,
            pubkey.pubkey_hash,
            pubkey.pubkey
          FROM chain_candidate cc
          JOIN block b ON (cc.block_id = b.block_id)
          JOIN block_tx ON (b.block_id = block_tx.block_id)
          JOIN tx    ON (tx.tx_id = block_tx.tx_id)
          JOIN txin  ON (tx.tx_id = txin.tx_id)
          LEFT JOIN txout prevout ON (txin.txout_id = prevout.txout_id)
          LEFT JOIN pubkey
              ON (prevout.pubkey_id = pubkey.pubkey_id)""")

def add_chain_script_addr_vers(store):
    store.ddl("ALTER TABLE chain ADD chain_script_addr_vers VARBINARY(100) NULL")

def populate_chain_script_addr_vers(store):
    def update(addr_vers, script_vers):
        store.sql("UPDATE chain SET chain_script_addr_vers=? WHERE chain_address_version=?",
                  (store.binin(script_vers), store.binin(addr_vers)))
    update('\x00', '\x05')
    update('\x6f', '\xc4')

def create_multisig_pubkey(store):
    store.ddl("""
        CREATE TABLE multisig_pubkey (
            multisig_id   NUMERIC(26) NOT NULL,
            pubkey_id     NUMERIC(26) NOT NULL,
            PRIMARY KEY (multisig_id, pubkey_id),
            FOREIGN KEY (multisig_id) REFERENCES pubkey (pubkey_id),
            FOREIGN KEY (pubkey_id) REFERENCES pubkey (pubkey_id)
        )""")

def create_x_multisig_pubkey_multisig(store):
    store.ddl("CREATE INDEX x_multisig_pubkey_pubkey ON multisig_pubkey (pubkey_id)")

def populate_multisig_pubkey(store):
    store.init_chains()
    store.log.info("Finding new address types.")

    rows = store.selectall("""
        SELECT txout_id, chain_id, txout_scriptPubKey
          FROM txout_detail
         WHERE pubkey_id IS NULL""")

    count = 0
    for txout_id, chain_id, db_script in rows:
        script = store.binout(db_script)
        pubkey_id = store.script_to_pubkey_id(store.get_chain_by_id(chain_id), script)
        if pubkey_id > 0:
            store.sql("UPDATE txout SET pubkey_id = ? WHERE txout_id = ?",
                      (pubkey_id, txout_id))
            count += 1
    store.commit()
    store.log.info("Found %d", count)

sql_arg_names = (
    'binary_type', 'max_varchar', 'ddl_implicit_commit',
    'create_table_epilogue', 'sequence_type', 'limit_style',
    'int_type', 'clob_type')

def abstract_sql(store):
    for name in sql_arg_names:
        store.sql("""
            UPDATE configvar
               SET configvar_name = ?
             WHERE configvar_name = ?""", ('sql.' + name, name))
    store.commit()

upgrades = [
    ('6',    add_block_value_in),
    ('6.1',  add_block_value_out),
    ('6.2',  add_block_total_satoshis),
    ('6.3',  add_block_total_seconds),
    ('6.4',  add_block_satoshi_seconds),
    ('6.5',  add_block_total_ss),
    ('6.6',  add_satoshi_seconds_destroyed),
    ('6.7',  add_cc_block_height),
    ('6.8',  init_cc_block_height),
    ('6.9',  index_cc_block_height),
    ('6.10', index_cc_block),
    ('6.11', create_block_txin),
    ('6.12', index_block_tx_tx),
    ('6.13', init_block_txin),
    ('6.14', init_block_value_in),
    ('6.15', init_block_value_out),
    ('6.16', init_block_totals),
    ('6.17', init_satoshi_seconds_destroyed),
    ('6.18', set_0_satoshi_seconds_destroyed),
    ('6.19', noop),
    ('6.20', index_block_nTime),
    ('6.21', replace_chain_summary),
    ('7',    replace_chain_summary),
    ('7.1',  index_block_tx_tx),  # forgot to put in abe.py
    ('7.2',  init_block_txin),    # abe.py put bad data there.
    ('7.3',  init_satoshi_seconds_destroyed),
    ('7.4',  set_0_satoshi_seconds_destroyed),
    ('7.5',  noop),
    ('7.6',  drop_block_ss_columns),
    ('8',    add_fk_block_txin_block_id),
    ('8.1',  add_fk_block_txin_tx_id),
    ('8.2',  add_fk_block_txin_out_block_id),
    ('8.3',  add_chk_block_txin_out_block_id_nn),
    ('8.4',  create_x_cc_block_id),
    ('9',    reverse_binary_hashes),
    ('9.1',  drop_x_cc_block_id),
    ('9.2',  create_x_cc_block_height),
    ('10',   create_txout_approx),
    ('11',   add_fk_chain_candidate_block_id),
    ('12',   create_configvar),
    ('12.1', configure),
    ('Abe13', populate_abe_sequences),
    ('Abe14', add_datadir_chain_id),
    ('Abe15', noop),
    ('Abe16', rescan_if_missed_blocks),  # May be slow.
    ('Abe17',   insert_missed_blocks),
    ('Abe17.1', repair_missed_blocks),
    ('Abe18',   add_block_num_tx),       # Seconds
    ('Abe18.1', add_block_ss_destroyed), # Seconds
    ('Abe18.2', init_block_tx_sums),     # 5 minutes
    ('Abe18.3', replace_chain_summary),  # Fast
    ('Abe19',   config_ddl),             # Fast
    ('Abe20',   config_create_table_epilogue), # Fast
    ('Abe20.1', rename_abe_sequences_key), # Fast
    ('Abe21',   create_x_txin_txout),    # 25 seconds
    ('Abe22',   save_datadir),           # Fast
    ('Abe22.1', add_datadir_id),         # Fast
    ('Abe22.2', drop_tmp_datadir),       # Fast
    ('Abe23',   config_clob),            # Fast
    ('Abe24',   clear_bad_addresses),    # Fast
    ('Abe24.1', find_namecoin_addresses), # 2 minutes if you have Namecoin
    ('Abe25',   create_abe_lock),        # Fast
    ('Abe25.1', create_abe_lock_row),    # Fast
    ('Abe25.2', insert_null_pubkey),     # 1 second
    ('Abe25.3', set_netfee_pubkey_id),   # Seconds
    ('Abe26',   adjust_block_total_satoshis), # 1-3 minutes
    ('Abe26.1', init_block_satoshi_seconds), # 3-10 minutes
    ('Abe27',   config_limit_style),     # Fast
    ('Abe28',   config_sequence_type),   # Fast
    # Should be okay back to here.
    ('Abe29',   add_search_block_id),    # Seconds
    ('Abe29.1', populate_search_block_id), # 1-2 minutes if using firstbits
    ('Abe29.2', add_fk_search_block_id), # Seconds
    ('Abe29.3', create_firstbits),       # Fast
    ('Abe29.4', populate_firstbits),     # Slow if config use_firstbits=true
    ('Abe30',   add_keep_scriptsig),     # Fast
    ('Abe31',   drop_satoshi_seconds_destroyed), # Seconds
    ('Abe32',   save_datadir),           # Fast
    ('Abe32.1', widen_blkfile_number),   # Fast
    ('Abe32.2', drop_tmp_datadir),       # Fast
    ('Abe33',   add_datadir_loader),     # Fast
    ('Abe34',   noop),                   # Fast
    ('Abe35',   add_chain_policy),       # Fast
    ('Abe35.1', populate_chain_policy),  # Fast
    ('Abe35.2', add_chain_magic),        # Fast
    ('Abe35.3', populate_chain_magic),   # Fast
    ('Abe35.4', drop_policy),            # Fast
    ('Abe35.5', drop_magic),             # Fast
    ('Abe36',   add_chain_decimals),     # Fast
    ('Abe36.1', insert_chain_novacoin),  # Fast
    ('Abe37',   txin_detail_multisig),   # Fast
    ('Abe37.1', add_chain_script_addr_vers), # Fast
    ('Abe37.2', populate_chain_script_addr_vers), # Fast
    ('Abe37.3', create_multisig_pubkey), # Fast
    ('Abe37.4', create_x_multisig_pubkey_multisig), # Fast
    ('Abe37.5', populate_multisig_pubkey), # Minutes-hours
    ('Abe38',   abstract_sql),           # Fast
    ('Abe39', None)
]

def upgrade_schema(store):
    if 'sql.binary_type' not in store.config:
        for name in sql_arg_names:
            store.config['sql.' + name] = store.config[name]
            del store.config[name]
        store.init_sql()

    run_upgrades(store, upgrades)
    sv = store.config['schema_version']
    curr = upgrades[-1][0]
    if sv != curr:
        raise Exception('Can not upgrade from schema version %s to %s\n'
                        % (sv, curr))
    store.log.warning("Upgrade complete.")

if __name__ == '__main__':
    print "Run Abe with --upgrade added to the usual arguments."
    sys.exit(2)

########NEW FILE########
__FILENAME__ = util
# Copyright(C) 2011,2012,2013,2014 by Abe developers.
# Copyright (c) 2010 Gavin Andresen

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

#
# Misc util routines
#

import re
import base58
import Crypto.Hash.SHA256 as SHA256

try:
    import Crypto.Hash.RIPEMD160 as RIPEMD160
except Exception:
    import ripemd_via_hashlib as RIPEMD160

# This function comes from bitcointools, bct-LICENSE.txt.
def determine_db_dir():
    import os
    import os.path
    import platform
    if platform.system() == "Darwin":
        return os.path.expanduser("~/Library/Application Support/Bitcoin/")
    elif platform.system() == "Windows":
        return os.path.join(os.environ['APPDATA'], "Bitcoin")
    return os.path.expanduser("~/.bitcoin")

# This function comes from bitcointools, bct-LICENSE.txt.
def long_hex(bytes):
    return bytes.encode('hex_codec')

# This function comes from bitcointools, bct-LICENSE.txt.
def short_hex(bytes):
    t = bytes.encode('hex_codec')
    if len(t) < 11:
        return t
    return t[0:4]+"..."+t[-4:]

NULL_HASH = "\0" * 32
GENESIS_HASH_PREV = NULL_HASH

def sha256(s):
    return SHA256.new(s).digest()

def double_sha256(s):
    return sha256(sha256(s))

def sha3_256(s):
    import hashlib
    import sys
    if sys.version_info < (3, 4):
        import sha3
    return hashlib.sha3_256(s).digest()

def pubkey_to_hash(pubkey):
    return RIPEMD160.new(SHA256.new(pubkey).digest()).digest()

def calculate_target(nBits):
    # cf. CBigNum::SetCompact in bignum.h
    shift = 8 * (((nBits >> 24) & 0xff) - 3)
    bits = nBits & 0x7fffff
    sign = -1 if (nBits & 0x800000) else 1
    return sign * (bits << shift if shift >= 0 else bits >> -shift)

def target_to_difficulty(target):
    return ((1 << 224) - 1) * 1000 / (target + 1) / 1000.0

def calculate_difficulty(nBits):
    return target_to_difficulty(calculate_target(nBits))

def work_to_difficulty(work):
    return work * ((1 << 224) - 1) * 1000 / (1 << 256) / 1000.0

def target_to_work(target):
    # XXX will this round using the same rules as C++ Bitcoin?
    return int((1 << 256) / (target + 1))

def calculate_work(prev_work, nBits):
    if prev_work is None:
        return None
    return prev_work + target_to_work(calculate_target(nBits))

def work_to_target(work):
    return int((1 << 256) / work) - 1

def get_search_height(n):
    if n < 2:
        return None
    if n & 1:
        return n >> 1 if n & 2 else n - (n >> 2)
    bit = 2
    while (n & bit) == 0:
        bit <<= 1
    return n - bit

ADDRESS_RE = re.compile('[1-9A-HJ-NP-Za-km-z]{26,}\\Z')

def possible_address(string):
    return ADDRESS_RE.match(string)

def hash_to_address(version, hash):
    vh = version + hash
    return base58.b58encode(vh + double_sha256(vh)[:4])

def decode_check_address(address):
    if possible_address(address):
        version, hash = decode_address(address)
        if hash_to_address(version, hash) == address:
            return version, hash
    return None, None

def decode_address(addr):
    bytes = base58.b58decode(addr, None)
    if len(bytes) < 25:
        bytes = ('\0' * (25 - len(bytes))) + bytes
    return bytes[:-24], bytes[-24:-4]

class JsonrpcException(Exception):
    def __init__(ex, error, method, params):
        Exception.__init__(ex)
        ex.code = error['code']
        ex.message = error['message']
        ex.data = error.get('data')
        ex.method = method
        ex.params = params
    def __str__(ex):
        return ex.method + ": " + ex.message + " (code " + str(ex.code) + ")"

class JsonrpcMethodNotFound(JsonrpcException):
    pass

def jsonrpc(url, method, *params):
    import json, urllib
    postdata = json.dumps({"jsonrpc": "2.0",
                           "method": method, "params": params, "id": "x"})
    respdata = urllib.urlopen(url, postdata).read()
    resp = json.loads(respdata)
    if resp.get('error') is not None:
        if resp['error']['code'] == -32601:
            raise JsonrpcMethodNotFound(resp['error'], method, params)
        raise JsonrpcException(resp['error'], method, params)
    return resp['result']

def str_to_ds(s):
    import BCDataStream
    ds = BCDataStream.BCDataStream()
    ds.write(s)
    return ds

class CmdLine(object):
    def __init__(self, argv, conf=None):
        self.argv = argv
        if conf is None:
            self.conf = {}
        else:
            self.conf = conf.copy()

    def usage(self):
        return "Sorry, no help is available."

    def init(self):
        import DataStore, readconf, logging, sys
        self.conf.update({ "debug": None, "logging": None })
        self.conf.update(DataStore.CONFIG_DEFAULTS)

        args, argv = readconf.parse_argv(self.argv, self.conf, strict=False)
        if argv and argv[0] in ('-h', '--help'):
            print self.usage()
            return None, []

        logging.basicConfig(
            stream=sys.stdout, level=logging.DEBUG, format="%(message)s")
        if args.logging is not None:
            import logging.config as logging_config
            logging_config.dictConfig(args.logging)

        store = DataStore.new(args)

        return store, argv

########NEW FILE########
__FILENAME__ = verify
#!/usr/bin/env python
# Prototype database validation script.  Same args as abe.py.

# Copyright(C) 2011,2014 by Abe developers.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

import sys
import DataStore
import util
import logging

def verify_tx_merkle_hashes(store, logger, chain_id):
    checked, bad = 0, 0
    for block_id, merkle_root, num_tx in store.selectall("""
        SELECT b.block_id, b.block_hashMerkleRoot, b.block_num_tx
          FROM block b
          JOIN chain_candidate cc ON (b.block_id = cc.block_id)
         WHERE cc.chain_id = ?""", (chain_id,)):
        merkle_root = store.hashout(merkle_root)
        tree = []
        for (tx_hash,) in store.selectall("""
            SELECT tx.tx_hash
              FROM block_tx bt
              JOIN tx ON (bt.tx_id = tx.tx_id)
             WHERE bt.block_id = ?
             ORDER BY bt.tx_pos""", (block_id,)):
            tree.append(store.hashout(tx_hash))
        if len(tree) != num_tx:
            logger.warning("block %d: block_num_tx=%d but found %d",
                           block_id, num_tx, len(tree))
        root = util.merkle(tree) or DataStore.NULL_HASH
        if root != merkle_root:
            logger.error("block %d: block_hashMerkleRoot mismatch.",
                         block_id)
            bad += 1
        checked += 1
        if checked % 1000 == 0:
            logger.info("%d Merkle trees, %d bad", checked, bad)
    if checked % 1000 > 0:
        logger.info("%d Merkle trees, %d bad", checked, bad)
    return checked, bad

def main(argv):
    cmdline = util.CmdLine(argv)
    cmdline.usage = lambda: \
        "Usage: verify.py --dbtype=MODULE --connect-args=ARGS"

    store, argv = cmdline.init()
    if store is None:
        return 0

    logger = logging.getLogger("verify")
    checked, bad = 0, 0
    for (chain_id,) in store.selectall("""
        SELECT chain_id FROM chain"""):
        logger.info("checking chain %d", chain_id)
        checked1, bad1 = verify_tx_merkle_hashes(store, logger, chain_id)
        checked += checked1
        bad += bad1
    logger.info("All chains: %d Merkle trees, %d bad", checked, bad)
    return bad and 1

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

########NEW FILE########
__FILENAME__ = version
__version__ = '0.8pre'

########NEW FILE########
__FILENAME__ = ecdsa
#!/usr/bin/env python

# Retrieved from http://ecdsa.org/ecdsa.py on 2011-10-17.
# Thanks to ThomasV.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.


import sys
import os
import warnings
import optparse
import re
from cgi import escape
import posixpath
import wsgiref.util
import time
import binascii
import daemon

import Abe.DataStore
import Abe.readconf
import operator

# bitcointools -- modified deserialize.py to return raw transaction
import Abe.deserialize
import Abe.util  # Added functions.
import Abe.base58
from Abe.abe import *

AML_APPNAME = "Bitcoin ecdsa.org"

AML_TEMPLATE = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
    <link rel="stylesheet" type="text/css" href="http://s3.ecdsa.org/style.css" />
    <link rel="shortcut icon" href="http://s3.ecdsa.org/favicon.ico" />
    <title>%(title)s</title>
</head>
<body>
  <div id="logo">
   <a href="%(dotdot)s/">
    <img src="http://s3.ecdsa.org/bc_logo.png" alt="Bitcoin logo" border="none" />
   </a> 
  </div>
  <div id="navigation">
    <ul>
    <li><a href="%(dotdot)shome">Home</a> </li>
    <li><a href="%(dotdot)ssearch">Search</a> </li>
    <li><a href="%(dotdot)sannotate">Annotations</a> </li>
    <li><a href="%(dotdot)swidgets">Widgets</a></li>
    <li><a href="%(dotdot)sthresholdRelease">Threshold release</a></li>
    <li><a href="%(dotdot)sstats.html">Statistics</a></li>
    </ul>
  </div>
  <div id=\"content\">
    <h1>%(h1)s</h1>
    %(body)s
  </div>
</body>
</html>
"""



class Aml(Abe):
    def __init__(abe, store, args):
        abe.store = store
        abe.args = args
        abe.htdocs = args.document_root or find_htdocs()
        abe.static_path = '' if args.static_path is None else args.static_path
        abe.template_vars = args.template_vars.copy()
        abe.template_vars['STATIC_PATH'] = (
            abe.template_vars.get('STATIC_PATH', abe.static_path))
        abe.template = flatten(args.template)
        abe.debug = args.debug
        import logging
        abe.log = logging
        abe.log.info('Abe initialized.')
        abe.home = "home"
        if not args.auto_agpl:
            abe.template_vars['download'] = (
                abe.template_vars.get('download', ''))
        abe.base_url = args.base_url

        abe.reports = abe.get_reports()


    


    def handle_home(abe, page):
        page['title'] = 'Bitcoin Web Services'
        body = page['body']
        body += [  """
<p>This website allows you to :
<ul>
<li>Annotate transactions in the blockchain (signature requested)</li>
<li>Use fundraiser widgets (counters, progress bars, javascript)</li>
<li>Release data when donations to an address reach a given threshold.</li>
</ul>
<br/><br/>
<p style="font-size: smaller">
This site is powered by <span style="font-style: italic"> <a href="https://github.com/bitcoin-abe/bitcoin-abe">bitcoin-ABE</a></span>
&nbsp;&nbsp;source:<a href="ecdsa.py">[1]</a>&nbsp;<a href="abe.diff">[2]</a>
</p>"""
                   ]

         
        return




    def get_sender_comment(abe, tx_id):
        r = abe.store.selectrow("SELECT c_text, c_pubkey, c_sig FROM comments WHERE c_tx = ?""", (tx_id,))
        if r:
            return r[0]
        else:
            return ""

    def get_address_comment(abe, address):
        #rename this column in sql
        r = abe.store.selectrow("SELECT text FROM addr_comments WHERE address = '%s'"""%(address))
        if r:
            return r[0]
        else:
            return ""


    def get_tx(abe, tx_hash ):
        row = abe.store.selectrow("""
        SELECT tx_id, tx_version, tx_lockTime, tx_size
        FROM tx
        WHERE tx_hash = ?
        """, (abe.store.hashin_hex(tx_hash),))
        if row is None: return None, None, None, None
        tx_id, tx_version, tx_lockTime, tx_size = (int(row[0]), int(row[1]), int(row[2]), int(row[3]))
        return tx_id, tx_version, tx_lockTime, tx_size
    

    def get_tx_inputs(abe, tx_id):
        return abe.store.selectall("""
            SELECT
                txin.txin_pos,
                txin.txin_scriptSig,
                txout.txout_value,
                COALESCE(prevtx.tx_hash, u.txout_tx_hash),
                prevtx.tx_id,
                COALESCE(txout.txout_pos, u.txout_pos),
                pubkey.pubkey_hash
              FROM txin
              LEFT JOIN txout ON (txout.txout_id = txin.txout_id)
              LEFT JOIN pubkey ON (pubkey.pubkey_id = txout.pubkey_id)
              LEFT JOIN tx prevtx ON (txout.tx_id = prevtx.tx_id)
              LEFT JOIN unlinked_txin u ON (u.txin_id = txin.txin_id)
             WHERE txin.tx_id = ?
             ORDER BY txin.txin_pos
             """, (tx_id,))

    def get_tx_outputs(abe, tx_id):
        return abe.store.selectall("""
            SELECT
                txout.txout_pos,
                txout.txout_scriptPubKey,
                txout.txout_value,
                nexttx.tx_hash,
                nexttx.tx_id,
                txin.txin_pos,
                pubkey.pubkey_hash
              FROM txout
              LEFT JOIN txin ON (txin.txout_id = txout.txout_id)
              LEFT JOIN pubkey ON (pubkey.pubkey_id = txout.pubkey_id)
              LEFT JOIN tx nexttx ON (txin.tx_id = nexttx.tx_id)
             WHERE txout.tx_id = ?
             ORDER BY txout.txout_pos
        """, (tx_id,))


    def handle_tx(abe, page):

        tx_hash = wsgiref.util.shift_path_info(page['env'])
        if tx_hash in (None, '') or page['env']['PATH_INFO'] != '':
            raise PageNotFound()

        page['title'] = ['Transaction ', tx_hash[:10], '...', tx_hash[-4:]]
        body = page['body']

        if not HASH_PREFIX_RE.match(tx_hash):
            body += ['<p class="error">Not a valid transaction hash.</p>']
            return

        tx_id, tx_version, tx_lockTime, tx_size = abe.get_tx( tx_hash )
        if tx_id is None:
            body += ['<p class="error">Transaction not found.</p>']
            return

        block_rows = abe.store.selectall("""
            SELECT c.chain_name, cc.in_longest,
                   b.block_nTime, b.block_height, b.block_hash,
                   block_tx.tx_pos
              FROM chain c
              JOIN chain_candidate cc ON (cc.chain_id = c.chain_id)
              JOIN block b ON (b.block_id = cc.block_id)
              JOIN block_tx ON (block_tx.block_id = b.block_id)
             WHERE block_tx.tx_id = ?
             ORDER BY c.chain_id, cc.in_longest DESC, b.block_hash
        """, (tx_id,))

        def parse_row(row):
            pos, script, value, o_hash, o_id, o_pos, binaddr = row

            chain = abe.get_default_chain()
            hash = abe.store.binout(binaddr)
            address = hash_to_address(chain['address_version'], hash)

            return {
                "pos": int(pos),
                "script": abe.store.binout(script),
                "value": None if value is None else int(value),
                "o_hash": abe.store.hashout_hex(o_hash),
                "o_id": o_id,
                "o_pos": None if o_pos is None else int(o_pos),
                "binaddr": abe.store.binout(binaddr),
                }

        def row_to_html(row, this_ch, other_ch, no_link_text):
            body = []
            body += [
                '<tr>\n',
                '<td><a name="', this_ch, row['pos'], '">', row['pos'],
                '</a></td>\n<td>']
            if row['o_hash'] is None:
                body += [no_link_text]
            else:
                body += [
                    '<a href="', row['o_hash'], '#', other_ch, row['o_pos'],
                    '">', row['o_hash'][:10], '...:', row['o_pos'], '</a>']
            body += [
                '</td>\n',
                '<td>', format_satoshis(row['value'], chain), '</td>\n',
                ]
            if row['binaddr'] is None:
                body += ['Unknown', '</td><td></td>']
            else:
                link = hash_to_address_link(chain['address_version'], row['binaddr'], '../')
                addr = hash_to_address(chain['address_version'], row['binaddr'])
                comment = abe.get_address_comment(addr)
                comment += " <a title=\"add comment\" href=\"http://ecdsa.org/annotate?address="+addr+"\">[+]</a>"
                body += [ '<td>', link, '</td><td>', comment, '</td>']
            body += ['</tr>\n']
            return body

        in_rows = map(parse_row, abe.get_tx_inputs(tx_id))
        out_rows = map(parse_row, abe.get_tx_outputs(tx_id))

            

        def sum_values(rows):
            ret = 0
            for row in rows:
                if row['value'] is None:
                    return None
                ret += row['value']
            return ret

        value_in = sum_values(in_rows)
        value_out = sum_values(out_rows)
        is_coinbase = None

        body += abe.short_link(page, 't/' + hexb58(tx_hash[:14]))
        body += ['<p>Hash: ', tx_hash, '<br />\n']
        chain = None
        for row in block_rows:
            (name, in_longest, nTime, height, blk_hash, tx_pos) = (
                row[0], int(row[1]), int(row[2]), int(row[3]),
                abe.store.hashout_hex(row[4]), int(row[5]))
            if chain is None:
                chain = abe.chain_lookup_by_name(name)
                is_coinbase = (tx_pos == 0)
            elif name <> chain['name']:
                abe.log.warn('Transaction ' + tx_hash + ' in multiple chains: '
                             + name + ', ' + chain['name'])
            body += [
                'Appeared in <a href="../block/', blk_hash, '">',
                escape(name), ' ',
                height if in_longest else [blk_hash[:10], '...', blk_hash[-4:]],
                '</a> (', format_time(nTime), ')<br />\n']

        if chain is None:
            abe.log.warn('Assuming default chain for Transaction ' + tx_hash)
            chain = abe.get_default_chain()


        sender_comment = abe.get_sender_comment(tx_id)
        sender_comment += " <a href=\"http://ecdsa.org/annotate?tx="+tx_hash+"\">[+]</a>"

        fee = format_satoshis(0 if is_coinbase else (value_in and value_out and value_in - value_out), chain)
        body += [
            len(in_rows),' inputs, ', len(out_rows),' outputs.<br/>\n'
            'Amounts: ', format_satoshis(value_in, chain), ' --> ', format_satoshis(value_out, chain), ' + ',fee,' fee.<br/>\n',
            'Size: ', tx_size, ' bytes<br /><br/>\n',
            '<b>Comment from sender:</b><br/>', sender_comment,  '<br/>\n',
            ]

        body += ['</p>\n',
                 '<a name="inputs"><h3>Inputs</h3></a>\n<table>\n',
                 '<tr><th>Index</th><th>Previous output</th><th>Amount</th>',
                 '<th>From address</th><th>Comment</th></tr>\n']
        for row in in_rows:
            page['body'] += row_to_html(row, 'i', 'o', 'Generation' if is_coinbase else 'Unknown')
        body += ['</table>\n',
                 '<a name="outputs"><h3>Outputs</h3></a>\n<table>\n',
                 '<tr><th>Index</th><th>Redeemed at</th><th>Amount</th>',
                 '<th>To address</th><th>Comment</th></tr>\n']
        for row in out_rows:
            page['body'] += row_to_html(row, 'o', 'i', 'Not yet redeemed')

        body += ['</table>\n']



        def trackrow_to_html(row, report_name):
            line = [ '<tr>\n<td>' ]
            if row['o_hash'] is None:
                line += ['Generation' if is_coinbase else 'Unknown']
            else:
                line += [
                    '<a href="', row['o_hash'], '">', row['o_hash'][:10], '...:', row['o_pos'], '</a>']
                line += [
                    '</td>\n',
                    '<td>', format_satoshis(row['value'], chain), '</td>\n',
                    '<td>']
                if row['binaddr'] is None:
                    line += ['Unknown']
                else:
                    line += hash_to_address_link(chain['address_version'], row['binaddr'], '../')
                    line += [
                        '</td>\n',
                        '<td>', row['dist'].get(report_name),'</td>\n',
                        '<td>', row['comment'],'</td>\n',
                        '</tr>\n']
            return line



    def get_address_out_rows(abe, dbhash):
        return abe.store.selectall("""
            SELECT
                b.block_nTime,
                cc.chain_id,
                b.block_height,
                1,
                b.block_hash,
                tx.tx_hash,
                tx.tx_id,
                txin.txin_pos,
                -prevout.txout_value
              FROM chain_candidate cc
              JOIN block b ON (b.block_id = cc.block_id)
              JOIN block_tx ON (block_tx.block_id = b.block_id)
              JOIN tx ON (tx.tx_id = block_tx.tx_id)
              JOIN txin ON (txin.tx_id = tx.tx_id)
              JOIN txout prevout ON (txin.txout_id = prevout.txout_id)
              JOIN pubkey ON (pubkey.pubkey_id = prevout.pubkey_id)
             WHERE pubkey.pubkey_hash = ?
               AND cc.in_longest = 1""",
                      (dbhash,))

    def get_address_in_rows(abe, dbhash):
        return abe.store.selectall("""
            SELECT
                b.block_nTime,
                cc.chain_id,
                b.block_height,
                0,
                b.block_hash,
                tx.tx_hash,
                tx.tx_id,
                txout.txout_pos,
                txout.txout_value
              FROM chain_candidate cc
              JOIN block b ON (b.block_id = cc.block_id)
              JOIN block_tx ON (block_tx.block_id = b.block_id)
              JOIN tx ON (tx.tx_id = block_tx.tx_id)
              JOIN txout ON (txout.tx_id = tx.tx_id)
              JOIN pubkey ON (pubkey.pubkey_id = txout.pubkey_id)
             WHERE pubkey.pubkey_hash = ?
               AND cc.in_longest = 1""",
                      (dbhash,))

    def handle_qr(abe,page):
        address = wsgiref.util.shift_path_info(page['env'])
        if address in (None, '') or page['env']['PATH_INFO'] != '':
            raise PageNotFound()

        body = page['body']
        page['title'] = 'Address ' + escape(address)
        version, binaddr = decode_check_address(address)
        if binaddr is None:
            body += ['<p>Not a valid address.</p>']
            return

        ret = """<html><body>
               <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.5.2/jquery.min.js"></script>
               <script type="text/javascript" src="http://ecdsa.org/jquery.qrcode.min.js"></script>
               <div id="qrcode"></div>
               <script>jQuery('#qrcode').qrcode("bitcoin:%s");</script>  
               </body></html>"""%address

        abe.do_raw(page, ret)
        page['content_type']='text/html'
        

    def handle_address(abe, page):
        #action = abe.get_param( page, 'action', '')

        address = wsgiref.util.shift_path_info(page['env'])
        if address in (None, '') or page['env']['PATH_INFO'] != '':
            raise PageNotFound()

        body = page['body']
        page['title'] = 'Address ' + escape(address)
        version, binaddr = decode_check_address(address)
        if binaddr is None:
            body += ['<p>Not a valid address.</p>']
            return

        txpoints = []
        chains = {}
        balance = {}
        received = {}
        sent = {}
        count = [0, 0]
        chain_ids = []
        def adj_balance(txpoint):
            chain_id = txpoint['chain_id']
            value = txpoint['value']
            if chain_id not in balance:
                chain_ids.append(chain_id)
                chains[chain_id] = abe.chain_lookup_by_id(chain_id)
                balance[chain_id] = 0
                received[chain_id] = 0
                sent[chain_id] = 0
            balance[chain_id] += value
            if value > 0:
                received[chain_id] += value
            else:
                sent[chain_id] -= value
            count[txpoint['is_in']] += 1

        dbhash = abe.store.binin(binaddr)
        rows = []
        rows += abe.get_address_out_rows( dbhash )
        rows += abe.get_address_in_rows( dbhash )
        #rows.sort()

        for row in rows:
            nTime, chain_id, height, is_in, blk_hash, tx_hash, tx_id, pos, value = row
            txpoint = {
                    "nTime":    int(nTime),
                    "chain_id": int(chain_id),
                    "height":   int(height),
                    "is_in":    int(is_in),
                    "blk_hash": abe.store.hashout_hex(blk_hash),
                    "tx_hash":  abe.store.hashout_hex(tx_hash),
                    "tx_id":    int(tx_id),
                    "pos":      int(pos),
                    "value":    int(value),
                    }
            adj_balance(txpoint)
            txpoints.append(txpoint)

        #txpoints.sort( lambda a,b: a['tx_id']<b['tx_id'])
        txpoints = sorted(txpoints, key=operator.itemgetter("tx_id"))

        if (not chain_ids):
            body += ['<p>Address not seen on the network.</p>']
            return

        def format_amounts(amounts, link):
            ret = []
            for chain_id in chain_ids:
                chain = chains[chain_id]
                if chain_id != chain_ids[0]:
                    ret += [', ']
                ret += [format_satoshis(amounts[chain_id], chain),
                        ' ', escape(chain['code3'])]
                if link:
                    other = hash_to_address(chain['address_version'], binaddr)
                    if other != address:
                        ret[-1] = ['<a href="', page['dotdot'],
                                   'address/', other,
                                   '">', ret[-1], '</a>']
            return ret


        comment = abe.get_address_comment(address)
        comment += " <a title=\"add comment\" href=\"http://ecdsa.org/annotate?address="+address+"\">[+]</a>"
            
        body += [ '<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.5.2/jquery.min.js"></script>',
                  '<script type="text/javascript" src="http://ecdsa.org/jquery.qrcode.min.js"></script>',
                  '<div style="float:right;" id="qrcode"></div>',
                  "<script>jQuery('#qrcode').qrcode(\"bitcoin:"+address+"\");</script>"  ]


        body += abe.short_link(page, 'a/' + address[:10])
        body += ['<p>Balance: '] + format_amounts(balance, True)

        for chain_id in chain_ids:
            balance[chain_id] = 0  # Reset for history traversal.

        body += ['<br />\n',
                 'Transactions in: ', count[0], '<br />\n',
                 'Received: ', format_amounts(received, False), '<br />\n',
                 'Transactions out: ', count[1], '<br />\n',
                 'Sent: ', format_amounts(sent, False), '<br/>'
                 'Comment: ', comment, '<br/>'
                 ]

        body += ['</p>\n'
                 '<h3>Transactions</h3>\n'
                 '<table>\n<tr><th>Transaction</th><th>Block</th>'
                 '<th>Approx. Time</th><th>Amount</th><th>Balance</th>'
                 '<th>Comment</th>'
                 '</tr>\n']

        for elt in txpoints:
            chain = chains[elt['chain_id']]
            balance[elt['chain_id']] += elt['value']
            body += ['<tr><td><a href="../tx/', elt['tx_hash'],
                     '#', 'i' if elt['is_in'] else 'o', elt['pos'],
                     '">', elt['tx_hash'][:10], '...</a>',
                     '</td><td><a href="../block/', elt['blk_hash'],
                     '">', elt['height'], '</a></td><td>',
                     format_time(elt['nTime']), '</td><td>']
            if elt['value'] < 0:
                body += ['<span style="color:red;">-', format_satoshis(-elt['value'], chain), "</span>" ]
            else:
                body += ['+', format_satoshis(elt['value'], chain)]

            # get sender comment 
            comment = abe.get_sender_comment(elt['tx_id'])
            comment += " <a href=\"http://ecdsa.org/annotate?tx="+elt['tx_hash']+"\">[+]</a>"

            body += ['</td><td>',
                     format_satoshis(balance[elt['chain_id']], chain),
                     '</td><td>', comment,
                     '</td></tr>\n']
        body += ['</table>\n']


    def search_form(abe, page):
        q = (page['params'].get('q') or [''])[0]
        return [
            '<p>Search by address, block number, block or transaction hash,'
            ' or chain name:</p>\n'
            '<form action="', page['dotdot'], 'search"><p>\n'
            '<input name="q" size="64" value="', escape(q), '" />'
            '<button type="submit">Search</button>\n'
            '<br />Address or hash search requires at least the first six'
            ' characters.</p></form>\n']

    def get_reports(abe):
        rows = abe.store.selectall("select reports.report_id, tx.tx_id, tx.tx_hash, name from reports left join tx on tx.tx_id=reports.tx_id" )
        return map(lambda x: { 'report_id':int(x[0]), 'tx_id':int(x[1]), 'tx_hash':x[2], 'name':x[3] }, rows)

    def handle_reports(abe, page):
        page['title'] =  'Fraud reports'
        page['body'] += [ 'List of transactions that have been reported as fraudulent.', '<br/><br/>']
        page['body'] += [ '<table><tr><th>name</th><th>transaction</th></tr>']
        for item in abe.reports:
            link = '<a href="tx/' + item['tx_hash'] + '">'+ item['tx_hash'] + '</a>'
            page['body'] += ['<tr><td>'+item['name']+'</td><td>'+link+'</td></tr>']
        page['body'] += [ '</table>']

    def handle_annotate(abe, page):
        tx_hash = (page['params'].get('tx') or [''])[0]
        address = (page['params'].get('address') or [''])[0]
        message = (page['params'].get('comment') or [''])[0]
        signature = (page['params'].get('signature') or [''])[0]

        if not tx_hash and not address:
            page['title'] =  'Annotations'
            page['body'] += [ 'This website allows you to annotate the Bitcoin blockchain.<br/><br/>',
                              'You will need a version of bitcoind that has the "signmessage" command.<br/>'
                              'In order to annotate an address or transaction, first <a href="search">find</a> the corresponding page, then follow the "[+]" link. <a href="http://ecdsa.org/annotate?tx=e357fece18a4191be8236570c7dc309ec6ac04473317320b5e8b9ab7cd023549">(example here)</a><br/><br/>']
            
            page['body'] += [ '<h3>Annotated addresses.</h3>']
            rows = abe.store.selectall("""select text, address from addr_comments limit 100""" )
            page['body'] += [ '<table>']
            page['body'] += [ '<tr><th>Address</th><th>Comment</th></tr>']
            for row in rows:
                link = '<a href="address/' + row[1]+ '">'+ row[1] + '</a>'
                page['body'] += ['<tr><td>'+link+'</td><td>'+row[0]+'</td></tr>']
            page['body'] += [ '</table>']


            page['body'] += [ '<h3>Annotated transactions.</h3>']
            rows = abe.store.selectall("""select tx.tx_id, tx.tx_hash, comments.c_text 
                                          from comments left join tx on tx.tx_id = comments.c_tx where c_sig != '' limit 100""" )
            page['body'] += [ '<table>']
            page['body'] += [ '<tr><th>Transaction</th><th>Comment</th></tr>']
            for row in rows:
                link = '<a href="tx/' + row[1]+ '">'+ row[1] + '</a>'
                page['body'] += ['<tr><td>'+link+'</td><td>'+row[2]+'</td></tr>']
            page['body'] += [ '</table>']
            return

        if tx_hash:

            page['title'] =  'Annotate transaction'
            tx_id, b, c, d = abe.get_tx( tx_hash )
            chain = abe.get_default_chain()

            in_addresses = []
            for row in abe.get_tx_inputs( tx_id ):
                addr =  abe.store.binout(row[6])
                addr = hash_to_address_link(chain['address_version'], addr, '../')
                in_addresses.append( addr[3] )
            if not address:
                address = in_addresses[0]

            out_addresses = []
            for row in abe.get_tx_outputs( tx_id ):
                addr =  abe.store.binout(row[6])
                addr = hash_to_address_link(chain['address_version'], addr, '../')
                out_addresses.append( addr[3] )

            if message or signature:
                # check address
                #if address not in in_addresses and address not in out_addresses:
                if address not in in_addresses:
                    page['title'] = 'Error'
                    page['body'] = ['<p>wrong address for this transaction.</p>\n']
                    print address, in_addresses
                    return

                # check signature
                import bitcoinrpc
                conn = bitcoinrpc.connect_to_local()
                message = message.replace("\r\n","\\n").replace("!","\\!").replace("$","\\$")
                print "verifymessage:", address, signature, repr(message)
                try:
                    v = conn.verifymessage(address,signature, tx_hash+":"+message)
                except:
                    v = False
                if not v:
                    page['title'] = 'Error'
                    page['body'] = ['<p>Invalid signature.</p>']
                    return

                # little bobby tables
                message = message.replace('"', '\\"').replace("'", "\\'")
                # escape html 
                message = escape( message )
                message = message[:1024]

                row = abe.store.selectrow("select c_tx from comments where c_tx=%d "%(tx_id ) )
                if not row:
                    abe.store.sql("insert into comments (c_tx, c_text, c_pubkey, c_sig) VALUES (%d, '%s', '%s', '%s')"%( tx_id, message, address, signature) )
                    abe.store.commit()
                    page['body'] = ['<p>Your comment was added successfully.</p>\n']
                else:
                    if not message:
                        abe.store.sql("delete from comments where c_tx=%d "%( tx_id ) )
                        abe.store.commit()
                        page['body'] = ['<p>Your comment was deleted.</p>\n']
                    else:
                        abe.store.sql("update comments set c_text='%s', c_sig='%s', c_pubkey='%s' where c_tx=%d "%( message, signature, address, tx_id ) )
                        abe.store.commit()
                        page['body'] = ['<p>Your comment was updated.</p>\n']
                return
            else:
                select = "<select id=\"address\" onkeyup=\"change_address(this.value);\" onchange=\"change_address(this.value);\" name='address'>" \
                    + "\n".join( map( lambda addr: "<option value=\""+addr+"\">"+addr+"</option>", in_addresses ) ) \
                    +"</select>"
                select = select.replace("<option value=\""+address+"\">","<option value=\""+address+"\" selected>")
                tx_link = '<a href="tx/' + tx_hash + '">'+ tx_hash + '</a>'

                javascript = """
            <script>
               function change_address(x){ 
                 document.getElementById("saddress").innerHTML=x;
               }
               function change_text(x){ 
                 x = x.replace(/!/g,"\\\\!");
                 x = x.replace(/\\n/g,"\\\\n");
                 x = x.replace(/\\$/g,"\\\\$");
                 document.getElementById("stext").innerHTML = x; 
               }
               function onload(){
                 change_text(document.getElementById("text").value);
                 //change_address(document.getElementById("address").value);
               }
            </script>
            """

                page['title'] = 'Annotate transaction'
                page['body'] = [
                    javascript,
                    '<form id="form" action="', page['dotdot'], 'annotate">\n'
                    'Transaction: ',tx_link,'<br/>'
                    'Address:', select,'<br/><br/>\n'
                    'Message:<br/><textarea id="text" onkeyup="change_text(this.value);" name="comment" cols="80" value=""></textarea><br/><br/>\n'
                    'You must sign your message with one of the input addresses of involved in the transaction.<br/>\n'
                    'The signature will be returned by the following command line:<br/>\n'
                    '<pre>bitcoind signmessage <span id="saddress">'+in_addresses[0]+'</span> "'+tx_hash+':<span id="stext">your text</span>"</pre>\n'
                    'Signature:<br/><input name="signature" value="" style="width:500px;"/><br/>'
                    '<input name="tx" type="hidden" value="'+tx_hash+'" />'
                    '<button type="submit">Submit</button>\n'
                    '</form>\n']
            return
        

    
        if address:
            page['title'] =  'Annotate address'

            if message or signature:
                # check signature
                import bitcoinrpc
                conn = bitcoinrpc.connect_to_local()
                message = message.replace("\n","\\n").replace("!","\\!").replace("$","\\$")
                print "verifymessage:", address, signature, message
                try:
                    v = conn.verifymessage(address,signature, message)
                except:
                    v = False
                if not v:
                    page['title'] = 'Error'
                    page['body'] = ['<p>Invalid signature.</p>']
                    return

                # little bobby tables
                message = message.replace('"', '\\"').replace("'", "\\'")
                # escape html 
                message = escape( message )
                message = message[:1024]

                row = abe.store.selectrow("select address from addr_comments where address='%s' "%(address ) )
                if not row:
                    abe.store.sql("insert into addr_comments (address, text) VALUES ('%s', '%s')"%( address, message) )
                    abe.store.commit()
                    page['body'] = ['<p>Your comment was added successfully.</p>\n']
                else:
                    if not message:
                        abe.store.sql("delete from addr_comments where address='%s' "%( message ) )
                        abe.store.commit()
                        page['body'] = ['<p>Your comment was deleted.</p>\n']
                    else:
                        abe.store.sql("update addr_comments set text='%s' where address='%s' "%( message, address ) )
                        abe.store.commit()
                        page['body'] = ['<p>Your comment was updated.</p>\n']
                return
            else:
                javascript = """
            <script>
               function change_text(x){ 
                 x = x.replace(/!/g,"\\\\!");
                 x = x.replace(/\\n/g,"\\\\n");
                 x = x.replace(/\\$/g,"\\\\$");
                 document.getElementById("stext").innerHTML=x; 
               }
               function onload(){
                 change_text(document.getElementById("text").value);
               }
            </script>
            """

                page['title'] = 'Annotate address'
                page['body'] = [
                    javascript,
                    '<form id="form" action="', page['dotdot'], 'annotate">\n'
                    'Address:', address,'<br/><br/>\n'
                    'Message:<br/><textarea id="text" onkeyup="change_text(this.value);" name="comment" cols="80" value=""></textarea><br/><br/>\n'
                    'You must sign your message with the addresses.<br/>\n'
                    'The signature will be returned by the following command line:<br/>\n'
                    '<pre>bitcoind signmessage <span id="saddress">'+address+'</span> "<span id="stext">your text</span>"</pre>\n'
                    'Signature:<br/><input name="signature" value="" style="width:500px;"/><br/>'
                    '<input name="address" type="hidden" value="'+address+'" />'
                    '<button type="submit">Submit</button>\n'
                    '</form>\n']



    def handle_thresholdRelease(abe, page):
        page['title'] =  'Threshold Release'
        chain = abe.get_default_chain()

        target = (page['params'].get('target') or [''])[0]
        address = (page['params'].get('address') or [''])[0]
        secret   = (page['params'].get('secret') or [''])[0]
        signature = (page['params'].get('signature') or [''])[0]
        
        if address:
            # check if address is valid
            version, binaddr = decode_check_address(address)
            if binaddr is None:
                page['body'] = ['<p>Not a valid address.</p>']
                return
            # check amount
            try:
                target = float(target)
            except:
                page['body'] = ['<p>Not a valid amount.</p>']
                return
            # check signature
            import bitcoinrpc
            conn = bitcoinrpc.connect_to_local()
            print address, signature
            try:
                v = conn.verifymessage(address,signature, "fundraiser")
            except:
                v = False
            if not v:
                page['body'] = ['<p>Invalid signature.</p>']
                return

            # little bobby tables
            secret = secret.replace('"', '\\"').replace("'", "\\'")
            # escape html 
            #message = escape( message )
            #
            secret = secret[:1024]

            row = abe.store.selectrow("select address from fundraisers where address='%s'"%(address ) )
            if not row:
                abe.store.sql("insert into fundraisers (address, target, secret) VALUES ('%s', %d, '%s')"%( address, target, secret) )
                abe.store.commit()
                page['body'] = ['<p>Your fundraiser was added successfully.</p>\n']
            else:
                if not secret:
                    abe.store.sql("delete from fundraisers where address='%s'"%( address ) )
                    abe.store.commit()
                    page['body'] = ['<p>Fundraiser entry was deleted.</p>\n']
                else:
                    abe.store.sql("update fundraisers set target=%d, secret='%s' where address='%s'"%( target, secret, address ) )
                    abe.store.commit()
                    page['body'] = ['<p>Your fundraiser data was updated.</p>\n']

            msg = "<object data=\"http://ecdsa.org/fundraiser/"+address+"?width=400\" height=\"60\" width=\"400\">Donate to "+address+"</object/>"

            page['body'] += "Sample code:<br/><pre>"+escape(msg)+"</pre><br/><br/>"+msg
            return
        else:
            javascript = """
            <script>
               function change_address(x){ 
                 //check validity here
                 document.getElementById("saddress").innerHTML=x;
               }
               function onload(){
                 change_address(document.getElementById("address").value);
               }
            </script>
            """
            msg= """
This service allows you to release digital content when a requested amount of Bitcoin donations has been reached.<br/>
<br/>
For example, you may want to publish a low quality version of a music file, and release a high quality version only if donations reach the price you want.<br/>
<br/>
There are various ways to use this service:
<ul>
<li>You may upload your content at a private URL; we will disclose the URL once the amount is reached.</li>
<li>You may encrypt your content and upload it to a public server; we will publish the encryption password only when the target amount is reached.</li>
</ul>
Once the threshold is reached, the content is displayed in place of the donation progress bar.<br/>
<br/>
"""

            page['title'] = 'Threshold Release'
            page['body'] = [
                javascript, msg,
                '<form id="form" action="', page['dotdot'], 'thresholdRelease">\n'
                'Address:<br/><input name="address" value="" style="width:500px;" onkeyup="change_address(this.value);"/><br/><br/>'
                'Target amount:<br/><input name="target" value="" style="width:500px;"/><br/><br/>'
                'Secret (will be displayed in place of the widget when the donation target is reached. Html, max. 1024 bytes):<br/>'
                '<textarea name="secret" value="" style="width:500px;"></textarea><br/><br/>'
                'You must provide a signature in order to demonstrate that you own the bitcoin address of the fundraiser.<br/>'
                'The signature will be returned by the following command line:<br/>\n'
                '<pre>bitcoind signmessage <span id="saddress"></span> <span id="stext">fundraiser</span></pre>\n'
                'Signature:<br/><input name="signature" value="" style="width:500px;"/><br/>'
                '<button type="submit">Submit</button>\n'
                '</form>\n'
                ]
    # check and display html as it is typed


    def get_fundraiser(abe,page):
        address = page['env'].get('PATH_INFO')[1:]
        if not address: return None,None,None,None
        chain = abe.get_default_chain()
        # get donations
        donations = abe.q_getreceivedbyaddress(page,chain)
        try:
            donations = float(donations)
        except:
            donations = 0
        # check if address is in the database
        row = abe.store.selectrow("select target, secret from fundraisers where address='%s'"%address ) 
        secret = None
        target = None
        if row: 
            target, secret = row
            if donations < target: secret = None
            target = float(target)

        #priority
        try:
            target = float( page['params'].get('target')[0] )
        except:
            pass

        return address, donations, target, secret


    def handle_fundraiser_js(abe,page):
        """ return a scriptlet"""
        address,donations,target,secret = abe.get_fundraiser(page)
        if secret:
            secret = escape( secret )
        ret = "var fundraiser_address = \"%s\";\nvar fundraiser_secret='%s';\nvar fundraiser_received = %f;\nfundraiser_callback();\n"%(address,secret,donations)
        abe.do_raw(page, ret)
        page['content_type']='text/javascript'


    def handle_fundraiser_img(abe,page):
        return abe.handle_counter(page)        

    def handle_counter(abe,page):
        """ return a png with percentage"""
        address, donations, target, secret = abe.get_fundraiser(page)
        if target:

            progress = int(100 * donations/target)
            progress = max(0, min( progress, 100 ))
            return abe.serve_static("percent/%dpercent.png"%progress, page['start_response'])

        else:
            donations = "%.2f"%donations
            path = "/img/" + donations + ".png"
            cpath = abe.htdocs + path
            if not os.path.exists(cpath):
                s = donations+ " BTC"
                length = 13*len(s)
                cmd = "echo \"%s\" | convert -page %dx20+0+0 -font Helvetica -style Normal -background none -undercolor none -fill black -pointsize 22 text:- +repage -background none -flatten %s"%(s, length, cpath)
                print cmd
                os.system(cmd)

            return abe.serve_static(path, page['start_response'])




    def get_param(abe,page,name,default):
        try:
            return page['params'].get(name)[0] 
        except:
            return default


    def handle_fundraiser(abe, page):
        abe.handle_widgets(page)

    def handle_widgets(abe, page):
        """ return embedded html"""
        address, donations, target, secret = abe.get_fundraiser(page)
        if not address:
            f = open(abe.htdocs + '/widgets.html', "rb")
            s = f.read()
            f.close()
            page['body'] = s
            page['title'] = "Bitcoin Widgets"
            return

        if secret: 
            abe.do_raw(page, secret)
            page['content_type']='text/html'
            return

        try:
            width = int(page['params'].get('width')[0])
        except:
            width = 400
        try:
            bg = page['params'].get('bg')[0] 
        except:
            bg = "#000000"
        try:
            lc = page['params'].get('leftcolor')[0] 
        except:
            lc = "#dddddd"
        try:
            rc = page['params'].get('rightcolor')[0] 
        except:
            rc = "#ffaa44"
        try:
            padding = page['params'].get('padding')[0] 
        except:
            padding = "3"
        try:
            radius = page['params'].get('radius')[0] 
        except:
            radius = "1em"
        try:
            textcolor = page['params'].get('textcolor')[0] 
        except:
            textcolor = "#000000"

        leftwidth = width - 120

        if target:
            progress = min( width, max( 1, int( leftwidth * donations/target ) ))
            percent = min( 100, max( 0, int( 100 * donations/target ) ))
            title = "%d"%percent + " percent of %.2f BTC"%target
        else:
            title = ""
            progress = leftwidth

        outer_style = "border-radius:%s; -moz-border-radius:%s; padding:%s; color:%s; background-color: %s;"%(radius,radius,padding,textcolor,bg)
        left_style  = "border-radius:%s; -moz-border-radius:%s; padding:%s; background-color: %s;"%(radius,radius,padding,lc)
        right_style = "border-radius:%s; -moz-border-radius:%s; padding:%s; background-color: %s; width:80px; text-align:center;"%(radius,radius,padding,rc)

        count = "%.2f&nbsp;BTC"%donations
        link_count = "<a style=\"text-decoration:none;color:"+textcolor + "\" title=\""+ title + "\" href=\"http://ecdsa.org/address/"+address+"\" target=\"_blank\">"+count+"</a>"

        text = "Donate"
        link_text  = "<a style=\"text-decoration:none;color:"+textcolor+"\" href=\"javascript:alert('Donate to this Bitcoin address:\\n"+address+"');\">"+text+"</a>"
        ret = """<table style="border-width:0px;"><tr><td>
 <table style="%s width:%dpx;">
  <tr><td style="%s width:%dpx; text-align:center;">%s</td><td></td></tr>
 </table>
</td>
<td>
 <table style="%s width:100px;">
   <tr><td style="%s">%s</td></tr>
 </table>
</td></tr></table>"""%(outer_style,leftwidth,left_style,progress,link_count,outer_style,right_style,link_text)

        abe.do_raw(page, ret)
        page['content_type']='text/html'




def serve(store):
    args = store.args
    abe = Aml(store, args)

    if args.host or args.port:
        # HTTP server.
        if args.host is None:
            args.host = "localhost"
        from wsgiref.simple_server import make_server
        port = int(args.port or 80)
        httpd = make_server(args.host, port, abe )
        print "Listening on http://" + args.host + ":" + str(port)
        try:
            httpd.serve_forever()
        except:
            httpd.shutdown()
            raise



from daemon import Daemon

class MyDaemon(Daemon):
    def __init__(self,args):
        self.args = args
        Daemon.__init__(self, self.args.pidfile, stderr=self.args.error_log, stdout=self.args.access_log )

    def run(self):
        store = make_store(self.args)
        serve(store)


if __name__ == '__main__':

    cmd = sys.argv[1]
    if cmd not in ['start','stop','restart','run']:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)

    argv = sys.argv[2:]

    conf = {
        "port": 80,
        "host": '',
        "no_serve":     None,
        "debug":        None,
        "static_path":  None,
        "auto_agpl":    None,
        "download_name":None,
        "watch_pid":    None,
        "base_url":     None,
        "no_update":    None,
        "pidfile":      '',
        "access_log":   '',
        "error_log":    '',
        "document_root":'',
        "template":     AML_TEMPLATE,
        "template_vars": {
            "APPNAME": AML_APPNAME,
            "CONTENT_TYPE": 'text/html',
            },
        }

    conf.update(DataStore.CONFIG_DEFAULTS)
    argv.append('--config=/etc/abe.conf')
    args, argv = readconf.parse_argv(argv, conf)
    if argv:
        sys.stderr.write("Error: unknown option `%s'\n" % (argv[0],))
        sys.exit(1)

    daemon = MyDaemon(args)
    if cmd == 'start' :
        daemon.start()
    elif cmd == 'stop' :
        daemon.stop()
    elif cmd == 'restart' :
        daemon.restart()
    elif cmd=='run':
        daemon.stop()
        daemon.run()

    sys.exit(0)

########NEW FILE########
__FILENAME__ = conftest
# Copyright(C) 2014 by Abe developers.

# conftest.py: pytest session-scoped objects

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

from __future__ import print_function
import pytest
import db

@pytest.fixture(scope="session", params=db.testdb_params())
def db_server(request):
    server = db.create_server(request.param)
    request.addfinalizer(server.delete)
    return server

########NEW FILE########
__FILENAME__ = datagen
# Copyright(C) 2014 by Abe developers.

# datagen.py: test data generation

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

import Abe.Chain
import Abe.BCDataStream
import Abe.util

from Abe.deserialize import opcodes

class Gen(object):
    def __init__(gen, rng=1, chain=None, **kwargs):
        if not hasattr(rng, 'randrange'):
            import random
            rng = random.Random(rng)
        if chain is None:
            chain = Abe.Chain.create("Testnet")

        gen._rng = rng
        gen.chain = chain

        for attr, val in kwargs.items():
            setattr(gen, attr, val)

    def random_bytes(gen, num_bytes):
        return ''.join(chr(gen._rng.randrange(256)) for _ in xrange(num_bytes))

    def random_addr_hash(gen):
        return gen.random_bytes(20)

    def encode_script(gen, *ops):
        ds = Abe.BCDataStream.BCDataStream()
        for op in ops:
            if isinstance(op, int):
                ds.write(chr(op))
            elif isinstance(op, str):
                ds.write_string(op)
            else:
                raise ValueError(op)
        return ds.input

    def op(gen, d):
        if isinstance(d, int):
            if d == 0:
                return opcodes.OP_0
            if d == -1 or 1 <= d <= 16:
                return d + opcodes.OP_1 - 1
            # Hmm, maybe time to switch to Python 3 with int.from_bytes?
            h = "00%x" % (d if d >= 0 else -1-d)
            if len(h) % 2:
                h = h[1:]
            elif h[2] < '8':
                h = h[2:]
            if d < 0:
                import string
                h = h.translate(string.maketrans('0123456789abcdef', 'fedcba9876543210'))
            return h.decode('hex')
        raise ValueError(n)

    def address_scriptPubKey(gen, hash):
        return gen.encode_script(opcodes.OP_DUP, opcodes.OP_HASH160, hash, opcodes.OP_EQUALVERIFY, opcodes.OP_CHECKSIG)

    def pubkey_scriptPubKey(gen, pubkey):
        return gen.encode_script(pubkey, opcodes.OP_CHECKSIG)

    def multisig_scriptPubKey(gen, m, pubkeys):
        ops = [ gen.op(m) ] + pubkeys + [ gen.op(len(pubkeys)), opcodes.OP_CHECKMULTISIG ]
        return gen.encode_script(*ops)

    def p2sh_scriptPubKey(gen, hash):
        return gen.encode_script(opcodes.OP_HASH160, hash, opcodes.OP_EQUAL)

    def txin(gen, **kwargs):
        txin = { 'sequence': 0xffffffff, 'pos': 0 }
        txin.update(kwargs)
        if 'prevout' in txin:
            txin['prevout_hash'] = txin['prevout']['hash']
            txin['prevout_n'] = txin['prevout']['pos']
        return txin

    def coinbase_txin(gen, **kwargs):
        chain = gen.chain
        args = {
            'prevout_hash': chain.coinbase_prevout_hash,
            'prevout_n':    chain.coinbase_prevout_n,
            'scriptSig': '04ffff001d0101'.decode('hex'),
            }
        args.update(kwargs)
        return gen.txin(**args)

    def txout(gen, **kwargs):
        txout = { 'value': 1, 'pos': 0 }
        txout.update(kwargs)

        if 'scriptPubKey' in txout:
            pass
        elif 'multisig' in txout:
            txout['scriptPubKey'] = gen.multisig_scriptPubKey(txout['multisig']['m'], txout['multisig']['pubkeys'])
        elif 'pubkey' in txout:
            txout['scriptPubKey'] = gen.pubkey_scriptPubKey(txout['pubkey'])
        elif 'addr' in txout:
            version, hash = Abe.util.decode_check_address(txout['addr'])
            if version == gen.chain.address_version:
                txout['scriptPubKey'] = gen.address_scriptPubKey(hash)
            elif version == gen.chain.script_addr_vers:
                txout['scriptPubKey'] = gen.p2sh_scriptPubKey(hash)
            else:
                raise ValueError('Invalid address version %r not in (%r, %r)' % (version, gen.chain.address_version, gen.chain.script_addr_vers))
        else:
            txout['scriptPubKey'] = gen.address_scriptPubKey(gen.random_addr_hash())

        return txout

    def tx(gen, txIn, txOut, version=1, lockTime=0, **kwargs):
        chain = gen.chain

        def parse_txin(i, arg):
            arg['pos'] = i
            return gen.txin(**arg)

        def parse_txout(i, arg):
            arg['pos'] = i
            return gen.txout(**arg)

        tx = {
            'version': version,
            'txIn': [parse_txin(i, arg) for i, arg in enumerate(txIn)],
            'txOut': [parse_txout(i, arg) for i, arg in enumerate(txOut)],
            'lockTime': lockTime,
            }
        tx['__data__'] = chain.serialize_transaction(tx)
        tx['hash'] = chain.transaction_hash(tx['__data__'])

        for txout in tx['txOut']:
            txout['hash'] = tx['hash']

        return tx

    def coinbase(gen, txOut=None, value=50e8, **kwargs):
        if txOut is None:
            txOut = [ gen.txout(value=value) ]
        return gen.tx([ gen.coinbase_txin(**kwargs) ], txOut, **kwargs)

    def block(gen, prev=None, transactions=None, version=1, nTime=1231006506, nBits=0x1d00ffff, nNonce=253):
        chain = gen.chain

        if prev is None:
            prev = chain.genesis_hash_prev
        elif isinstance(prev, dict):
            prev = prev['hash']

        if transactions is None:
            transactions = [gen.coinbase()]

        block = {
            'version':  version,
            'hashPrev': prev,
            'hashMerkleRoot': chain.merkle_root([ tx['hash'] for tx in transactions ]),
            'nTime':    nTime,
            'nBits':    nBits,
            'nNonce':   nNonce,
            'transactions': transactions,
            }
        block['hash'] = chain.block_header_hash(chain.serialize_block_header(block))

        return block

    def save_blkfile(gen, blkfile, blocks):
        import struct
        with open(blkfile, 'wb') as f:
            for bobj in blocks:
                f.write(gen.chain.magic)
                bstr = gen.chain.serialize_block(bobj)
                f.write(struct.pack('<i', len(bstr)))
                f.write(bstr)

########NEW FILE########
__FILENAME__ = db
# Copyright(C) 2014 by Abe developers.

# db.py: temporary database for automated testing

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

from __future__ import print_function
import pytest
import py.path
import json
import contextlib
import os
import subprocess
import Abe.util

def testdb_params():
    dbs = os.environ.get('ABE_TEST_DB')
    if dbs is not None:
        return dbs.split()
    if os.environ.get('ABE_TEST') == 'quick':
        return ['sqlite']
    return ['sqlite', 'mysql', 'postgres']

# XXX
def ignore_errors(thunk):
    def doit():
        try:
            thunk()
        except Exception:
            pass
    return doit

@pytest.fixture(scope="module")
def testdb(request, db_server):
    request.addfinalizer(ignore_errors(db_server.dropdb))
    return db_server

def create_server(dbtype=None):
    if dbtype in (None, 'sqlite3', 'sqlite'):
        return SqliteMemoryDB()
    if dbtype in ('mysql', 'MySQLdb'):
        return MysqlDB()
    if dbtype in ('psycopg2', 'postgres'):
        return PostgresDB()
    pytest.skip('Unknown dbtype: %s' % dbtype)

class DB(object):
    def __init__(db, dbtype, connect_args):
        db.dbtype = dbtype
        db.connect_args = connect_args
        db.cmdline = ('--dbtype', dbtype, '--connect-args', json.dumps(connect_args))
        db.store = None

    def createdb(db):
        pass

    def load(db, *args):
        db.createdb()
        db.store, argv = Abe.util.CmdLine(db.cmdline + args).init()
        assert len(argv) == 0
        db.store.catch_up()
        return db.store

    def dropdb(db):
        if db.store:
            db.store.close()

    def delete(db):
        pass

class SqliteDB(DB):
    def __init__(db, connect_args):
        DB.__init__(db, 'sqlite3', connect_args)

    def delete(db):
        DB.delete(db)
        os.unlink(db.connect_args)

class SqliteMemoryDB(SqliteDB):
    def __init__(db):
        #print("SqliteMemoryDB.__init__")
        SqliteDB.__init__(db, ':memory:')

    def delete(db):
        DB.delete(db)
        #print("SqliteMemoryDB.delete")

class ServerDB(DB):
    def __init__(db, dbtype):
        pytest.importorskip(dbtype)
        import tempfile
        db.installation_dir = py.path.local(tempfile.mkdtemp(prefix='abe-test-'))
        print("Created temporary directory %s" % db.installation_dir)
        try:
            db.server = db.install_server()
        except Exception as e:
            #print("EXCEPTION %s" % e)
            db._delete_tmpdir()
            pytest.skip(e)
            raise
        DB.__init__(db, dbtype, db.get_connect_args())

    def install_server(db):
        pass

    @contextlib.contextmanager
    def root(db):
        conn = db.connect_as_root()
        cur = conn.cursor()
        try:
            yield cur
        except:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    def delete(db):
        try:
            db.shutdown()
            db.server.wait()
        finally:
            db._delete_tmpdir()
            pass

    def _delete_tmpdir(db):
        if os.environ.get('ABE_TEST_KEEP_TMPDIR', '') == '':
            db.installation_dir.remove()
            print("Deleted temporary directory %s" % db.installation_dir)

class MysqlDB(ServerDB):
    def __init__(db):
        ServerDB.__init__(db, 'MySQLdb')

    def get_connect_args(db):
        return {'user': 'abe', 'passwd': 'Bitcoin', 'db': 'abe', 'unix_socket': db.socket}

    def install_server(db):
        db.socket = str(db.installation_dir.join('mysql.sock'))
        db.installation_dir.ensure_dir('tmp')
        mycnf = db.installation_dir.join('my.cnf')
        mycnf.write('[mysqld]\n'
                    'datadir=%(installation_dir)s\n'
                    #'log\n'
                    #'log-error\n'
                    'skip-networking\n'
                    'socket=mysql.sock\n'
                    'pid-file=mysqld.pid\n'
                    'tmpdir=tmp\n' % { 'installation_dir': db.installation_dir })
        subprocess.check_call(['mysql_install_db', '--defaults-file=' + str(mycnf)])
        server = subprocess.Popen(['mysqld', '--defaults-file=' + str(mycnf)])
        import time, MySQLdb
        tries = 30
        for t in range(tries):
            try:
                with db.root() as cur:
                    cur.execute("CREATE USER 'abe'@'localhost' IDENTIFIED BY 'Bitcoin'")
                    return server
            except MySQLdb.OperationalError as e:
                if t+1 == tries:
                    raise e
            time.sleep(1)

    def connect_as_root(db):
        import MySQLdb
        conn = MySQLdb.connect(unix_socket=db.socket, user='root')
        return conn

    def createdb(db):
        with db.root() as cur:
            cur.execute('CREATE DATABASE abe')
            cur.execute("GRANT ALL ON abe.* TO 'abe'@'localhost'")
        DB.createdb(db)

    def dropdb(db):
        DB.dropdb(db)
        with db.root() as cur:
            cur.execute('DROP DATABASE abe')

    def shutdown(db):
        subprocess.check_call(['mysqladmin', '-S', db.socket, '-u', 'root', 'shutdown'])

class PostgresDB(ServerDB):
    def __init__(db):
        ServerDB.__init__(db, 'psycopg2')

    def get_connect_args(db):
        return {'user': 'abe', 'password': 'Bitcoin', 'database': 'abe', 'host': str(db.installation_dir)}

    def install_server(db):
        db.bindir = subprocess.Popen(['pg_config', '--bindir'], stdout=subprocess.PIPE).communicate()[0].rstrip()
        subprocess.check_call([
                os.path.join(db.bindir, 'initdb'),
                '-D', str(db.installation_dir),
                '-U', 'postgres'])
        server = subprocess.Popen([
                os.path.join(db.bindir, 'postgres'),
                '-D', str(db.installation_dir),
                '-c', 'listen_addresses=',
                '-c', 'unix_socket_directory=.'])

        import time, psycopg2
        tries = 30
        for t in range(tries):
            try:
                with db.root() as cur:
                    cur.execute("COMMIT")  # XXX
                    cur.execute("CREATE USER abe UNENCRYPTED PASSWORD 'Bitcoin'")
                    cur.execute("COMMIT")
                return server
            except psycopg2.OperationalError as e:
                if t+1 == tries:
                    raise e
            time.sleep(1)

    def connect_as_root(db):
        import psycopg2
        conn = psycopg2.connect(host=str(db.installation_dir), user='postgres')
        return conn

    def createdb(db):
        with db.root() as cur:
            cur.execute("COMMIT")  # XXX
            cur.execute('CREATE DATABASE abe')
            cur.execute("GRANT ALL ON DATABASE abe TO abe")
            cur.execute("COMMIT")
        DB.createdb(db)

    def dropdb(db):
        DB.dropdb(db)
        with db.root() as cur:
            cur.execute("COMMIT")  # XXX
            cur.execute('DROP DATABASE abe')
            cur.execute("COMMIT")

    def shutdown(db):
        subprocess.check_call([
                os.path.join(db.bindir, 'pg_ctl'), 'stop',
                '-D', str(db.installation_dir),
                '-m', 'immediate'])

########NEW FILE########
__FILENAME__ = test_btc200
# Copyright(C) 2014 by Abe developers.

# test_btc200.py: test Abe loading through Bitcoin Block 200.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

import pytest

from db import testdb
import os
import Abe.util
import Abe.Chain

@pytest.fixture(scope="module")
def btc200(testdb):
    dirname = os.path.join(os.path.split(__file__)[0], 'btc200')
    store = testdb.load('--datadir', dirname)
    return store

def test_block_number(btc200):
    assert btc200.get_block_number(1) == 200

@pytest.fixture(scope="module")
def coinbase_200(btc200):
    return btc200.export_tx(tx_hash = '2b1f06c2401d3b49a33c3f5ad5864c0bc70044c4068f9174546f3cfc1887d5ba')

def test_coinbase_hash(coinbase_200):
    assert coinbase_200['hash'] == '2b1f06c2401d3b49a33c3f5ad5864c0bc70044c4068f9174546f3cfc1887d5ba'

def test_coinbase_in(coinbase_200):
    assert len(coinbase_200['in']) == 1
    assert coinbase_200['vin_sz'] == 1

def test_coinbase_lock_time(coinbase_200):
    assert coinbase_200['lock_time'] == 0

def test_coinbase_prev_out(coinbase_200):
    assert coinbase_200['in'][0]['prev_out'] == {
        "hash": "0000000000000000000000000000000000000000000000000000000000000000", 
        "n": 4294967295
        }

def test_coinbase_raw_scriptSig(coinbase_200):
    assert coinbase_200['in'][0]['raw_scriptSig'] == "04ffff001d0138"

def test_coinbase_out(coinbase_200):
    assert len(coinbase_200['out']) == 1
    assert coinbase_200['vout_sz'] == 1

def test_coinbase_raw_scriptPubKey(coinbase_200):
    assert coinbase_200['out'][0]['raw_scriptPubKey'] == \
        "41045e071dedd1ed03721c6e9bba28fc276795421a378637fb41090192bb9f208630dcbac5862a3baeb9df3ca6e4e256b7fd2404824c20198ca1b004ee2197866433ac"

def test_coinbase_value(coinbase_200):
    assert coinbase_200['out'][0]['value'] == "50.00000000"

def test_coinbase_size(coinbase_200):
    assert coinbase_200['size'] == 134

def test_coinbase_ver(coinbase_200):
    assert coinbase_200['ver'] == 1

@pytest.fixture(scope="module")
def b182t1(btc200):
    return btc200.export_tx(
        tx_hash = '591e91f809d716912ca1d4a9295e70c3e78bab077683f79350f101da64588073',
        format = 'browser')

def test_tx_hash(b182t1):
    assert b182t1['hash'] == '591e91f809d716912ca1d4a9295e70c3e78bab077683f79350f101da64588073'

def test_tx_version(b182t1):
    assert b182t1['version'] == 1

def test_tx_lockTime(b182t1):
    assert b182t1['lockTime'] == 0

def test_tx_size(b182t1):
    assert b182t1['size'] == 275

def test_tx_cc(b182t1):
    assert len(b182t1['chain_candidates']) == 1

def test_tx_chain_name(b182t1):
    assert b182t1['chain_candidates'][0]['chain'].name == 'Bitcoin'

def test_tx_in_longest(b182t1):
    assert b182t1['chain_candidates'][0]['in_longest']

def test_tx_block_nTime(b182t1):
    assert b182t1['chain_candidates'][0]['block_nTime'] == 1231740736

def test_tx_block_height(b182t1):
    assert b182t1['chain_candidates'][0]['block_height'] == 182

def test_tx_block_hash(b182t1):
    assert b182t1['chain_candidates'][0]['block_hash'] == \
        '0000000054487811fc4ff7a95be738aa5ad9320c394c482b27c0da28b227ad5d'

def test_tx_tx_pos(b182t1):
    assert b182t1['chain_candidates'][0]['tx_pos'] == 1

def test_tx_in(b182t1):
    assert len(b182t1['in']) == 1

def test_tx_in_pos(b182t1):
    assert b182t1['in'][0]['pos'] == 0

def test_tx_in_binscript(b182t1):
    assert b182t1['in'][0]['binscript'] == '47304402201f27e51caeb9a0988a1e50799ff0af94a3902403c3ad4068b063e7b4d1b0a76702206713f69bd344058b0dee55a9798759092d0916dbbc3e592fee43060005ddc17401'.decode('hex')

def test_tx_in_value(b182t1):
    assert b182t1['in'][0]['value'] == 3000000000

def test_tx_in_prev_out(b182t1):
    assert b182t1['in'][0]['o_hash'] == 'a16f3ce4dd5deb92d98ef5cf8afeaf0775ebca408f708b2146c4fb42b41e14be'
    assert b182t1['in'][0]['o_pos'] == 1

def test_tx_in_script_type(b182t1):
    assert b182t1['in'][0]['script_type'] == Abe.Chain.SCRIPT_TYPE_PUBKEY

def test_tx_in_binaddr(b182t1):
    assert b182t1['in'][0]['binaddr'] == '11b366edfc0a8b66feebae5c2e25a7b6a5d1cf31'.decode('hex')

def test_tx_out(b182t1):
    assert len(b182t1['out']) == 2

def test_tx_out_pos(b182t1):
    assert b182t1['out'][0]['pos'] == 0
    assert b182t1['out'][1]['pos'] == 1

def test_tx_out_binscript(b182t1):
    assert b182t1['out'][0]['binscript'] == '410401518fa1d1e1e3e162852d68d9be1c0abad5e3d6297ec95f1f91b909dc1afe616d6876f92918451ca387c4387609ae1a895007096195a824baf9c38ea98c09c3ac'.decode('hex')
    assert b182t1['out'][1]['binscript'] == '410411db93e1dcdb8a016b49840f8c53bc1eb68a382e97b1482ecad7b148a6909a5cb2e0eaddfb84ccf9744464f82e160bfa9b8b64f9d4c03f999b8643f656b412a3ac'.decode('hex')

def test_tx_out_value(b182t1):
    assert b182t1['out'][0]['value'] == 100000000
    assert b182t1['out'][1]['value'] == 2900000000

def test_tx_out_redeemed(b182t1):
    assert b182t1['out'][0]['o_hash'] is None
    assert b182t1['out'][0]['o_pos'] is None
    assert b182t1['out'][1]['o_hash'] == '12b5633bad1f9c167d523ad1aa1947b2732a865bf5414eab2f9e5ae5d5c191ba'
    assert b182t1['out'][1]['o_pos'] == 0

def test_tx_out_binaddr(b182t1):
    assert b182t1['out'][0]['binaddr'] == 'db3b465a2b678e0bdc3e4944bb41abb5a795ae04'.decode('hex')
    assert b182t1['out'][1]['binaddr'] == '11b366edfc0a8b66feebae5c2e25a7b6a5d1cf31'.decode('hex')

def test_tx_value_in(b182t1):
    assert b182t1['value_in'] == 3000000000

def test_tx_value_out(b182t1):
    assert b182t1['value_out'] == 3000000000

########NEW FILE########
__FILENAME__ = test_max200
# Copyright(C) 2014 by Abe developers.

# test_max200.py: test Abe loading through Maxcoin Block 200.
# This test exercises SHA3 block hashes and an unusual Merkle root algorithm.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

import pytest

from db import testdb
import os
import Abe.util
import Abe.Chain

@pytest.fixture(scope="module")
def max200(testdb):
    try:
        Abe.util.sha3_256('x')
    except Exception as e:
        pytest.skip('SHA3 not working: e')
    dirname = os.path.join(os.path.split(__file__)[0], 'max200')
    store = testdb.load('--datadir', dirname)
    return store

def test_block_number(max200):
    assert max200.get_block_number(max200.get_chain_by_name('Maxcoin').id) == 200

########NEW FILE########
__FILENAME__ = test_std_tx
# Copyright(C) 2014 by Abe developers.

# test_std_tx.py: test Abe importing standard Bitcoin transaction types.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

import pytest

import os
import json
import tempfile
import py.path

from db import testdb
import datagen
import Abe.Chain
from Abe.deserialize import opcodes

PUBKEYS = [
    x.decode('hex') for x in [
        # Satoshi's genesis pubkey.
        '04678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5f',

        # Testnet Block 1 pubkey.
        '021aeaf2f8638a129a3156fbe7e5ef635226b0bafd495ff03afe2c843d7e3a4b51',

        # Some test pubkeys.
        '0269184483e5494727d2dec54da85db9b18bee827bb3d1eee23b122edf810b8262',
        '0217819b778f0bcfee53bbed495ca20fdc828f40ffd6d9481fe4c0d091b1486f69',
        '022820a6eb4e6817bf68301856e0803e05d19f54714006f2088e74103be396eb5a',
        ]]

@pytest.fixture(scope="module")
def gen(testdb, request):
    chain = Abe.Chain.create('Testnet')
    blocks = []
    gen = datagen.Gen(chain=chain, db=testdb, blocks=blocks)

    # The Bitcoin/Testnet genesis transaction.
    genesis_coinbase = gen.coinbase(
        scriptSig=gen.encode_script(
            '\xff\xff\x00\x1d', '\x04', 'The Times 03/Jan/2009 Chancellor on brink of second bailout for banks'),
        txOut=[gen.txout(pubkey=PUBKEYS[0], value=50*10**8)])

    # Testnet Blocks 0 and 1.
    blocks.append(gen.block(transactions=[genesis_coinbase], nTime=1296688602, nNonce=414098458))

    blocks.append( gen.block(prev=blocks[-1], nTime=1296688928, nNonce=1924588547,
                             transactions=[gen.coinbase(scriptSig='0420e7494d017f062f503253482f'.decode('hex'),
                                                        txOut=[gen.txout(pubkey=PUBKEYS[1], value=50*10**8)])]) )

    # Test blocks with random coinbase addresses and bogus proof-of-work.
    for i in xrange(12):
        blocks.append( gen.block(prev=blocks[-1]) )

    # Test block with an interesting transaction.
    blocks.append(
        gen.block(
            prev=blocks[-1],
            transactions=[
                gen.coinbase(value=50.01e8),
                gen.tx(txIn=[gen.txin(prevout=blocks[1]['transactions'][0]['txOut'][0], scriptSig='XXX')],
                       txOut=[gen.txout(addr='n1pTUVnjZ6GHxujaoJ62P9NBMNjLr5N2EQ', value=9.99e8),
                              gen.txout(addr='2NFTctsgcAmrgtiboLJUx9q8qu5H1qVpcAb', value=20e8),
                              gen.txout(multisig={"m":2, "pubkeys":PUBKEYS[2:5]}, value=20e8)])]) )

    if 'ABE_TEST_SAVE_BLKFILE' in os.environ:
        gen.save_blkfile(os.environ['ABE_TEST_SAVE_BLKFILE'], blocks)

    datadir = py.path.local(tempfile.mkdtemp(prefix='abe-test-'))
    request.addfinalizer(datadir.remove)
    gen.save_blkfile(str(datadir.join('blk0001.dat')), blocks)

    gen.store = testdb.load('--datadir', json.dumps([{
                    'dirname': str(datadir),
                    'chain': chain.name,
                    'loader': 'blkfile'}]))
    gen.chain = gen.store.get_chain_by_name(chain.name)

    return gen

def test_b0_hash(gen):
    # Testnet Block 0 hash.
    block_0_hash = '000000000933ea01ad0ee984209779baaec3ced90fa3f408719526f8d77f4943'.decode('hex')[::-1]
    assert gen.blocks[0]['hash'] == block_0_hash

def test_b1_hash(gen):
    # Testnet Block 1 hash.
    block_1_hash = '00000000b873e79784647a6c82962c70d228557d24a747ea4d1b8bbe878e1206'.decode('hex')[::-1]
    assert gen.blocks[1]['hash'] == block_1_hash

def ah(gen, addr):
    return gen.store.export_address_history(addr, chain=gen.chain)

@pytest.fixture(scope="module")
def ahn1p(gen):
    return ah(gen, 'n1pTUVnjZ6GHxujaoJ62P9NBMNjLr5N2EQ')

def test_ahn1p_binaddr(ahn1p):
    assert ahn1p['binaddr'] == 'deb1f1ffbef6061a0b8f6d23b4e72164b4678253'.decode('hex')

def test_ahn1p_subbinaddr(ahn1p):
    assert 'subbinaddr' not in ahn1p

def test_ahn1p_version(ahn1p):
    assert ahn1p['version'] == '\x6f'

def test_ahn1p_chains(ahn1p):
    assert len(ahn1p['chains']) == 1

def test_ahn1p_c0_name(ahn1p):
    assert ahn1p['chains'][0].name == 'Testnet'

def test_ahn1p_balance(ahn1p, gen):
    assert ahn1p['balance'] == { gen.chain.id: 9.99e8 }

def test_ahn1p_txpoints(ahn1p):
    assert len(ahn1p['txpoints']) == 1

def test_ahn1p_p0_type(ahn1p):
    assert ahn1p['txpoints'][0]['type'] == 'direct'

def test_ahn1p_p0_is_out(ahn1p):
    assert not ahn1p['txpoints'][0]['is_out']

def test_ahn1p_p0_nTime(ahn1p):
    assert ahn1p['txpoints'][0]['nTime'] == 1231006506

def test_ahn1p_p0_chain(ahn1p):
    assert ahn1p['txpoints'][0]['chain'].name == 'Testnet'

def test_ahn1p_p0_height(ahn1p):
    assert ahn1p['txpoints'][0]['height'] == 14

def test_ahn1p_p0_blk_hash(ahn1p):
    assert ahn1p['txpoints'][0]['blk_hash'] == '0c2d2879773626a081d74e73b3dcb9276e2a366e4571b2de6d90c2a67295382e'

def test_ahn1p_p0_tx_hash(ahn1p):
    assert ahn1p['txpoints'][0]['tx_hash'] == 'dd5e827c88eb24502cb74670fa58430e8c51fa6a514c46451829c1896438ce52'

def test_ahn1p_p0_pos(ahn1p):
    assert ahn1p['txpoints'][0]['pos'] == 0

def test_ahn1p_p0_value(ahn1p):
    assert ahn1p['txpoints'][0]['value'] == 9.99e8

def test_ahn1p_sent(ahn1p, gen):
    assert ahn1p['sent'] == { gen.chain.id: 0 }

def test_ahn1p_received(ahn1p, gen):
    assert ahn1p['received'] == { gen.chain.id: 9.99e8 }

def test_ahn1p_counts(ahn1p):
    assert ahn1p['counts'] == [1, 0]

@pytest.fixture(scope="module")
def a2NFT(gen):
    return ah(gen, '2NFTctsgcAmrgtiboLJUx9q8qu5H1qVpcAb')

def test_a2NFT_binaddr(a2NFT):
    assert a2NFT['binaddr'] == 'f3aae15f9b92a094bb4e01afe99f99ab4135f362'.decode('hex')

def test_a2NFT_subbinaddr(a2NFT):
    assert 'subbinaddr' not in a2NFT

def test_a2NFT_version(a2NFT):
    assert a2NFT['version'] == '\xc4'

def test_a2NFT_chains(a2NFT):
    assert len(a2NFT['chains']) == 1

def test_a2NFT_c0_name(a2NFT):
    assert a2NFT['chains'][0].name == 'Testnet'

def test_a2NFT_balance(a2NFT, gen):
    assert a2NFT['balance'] == { gen.chain.id: 20e8 }

def test_a2NFT_txpoints(a2NFT):
    assert len(a2NFT['txpoints']) == 1

def test_a2NFT_p0_type(a2NFT):
    assert a2NFT['txpoints'][0]['type'] == 'direct'

def test_a2NFT_p0_is_out(a2NFT):
    assert not a2NFT['txpoints'][0]['is_out']

def test_a2NFT_p0_nTime(a2NFT):
    assert a2NFT['txpoints'][0]['nTime'] == 1231006506

def test_a2NFT_p0_chain(a2NFT):
    assert a2NFT['txpoints'][0]['chain'].name == 'Testnet'

def test_a2NFT_p0_height(a2NFT):
    assert a2NFT['txpoints'][0]['height'] == 14

def test_a2NFT_p0_blk_hash(a2NFT):
    assert a2NFT['txpoints'][0]['blk_hash'] == '0c2d2879773626a081d74e73b3dcb9276e2a366e4571b2de6d90c2a67295382e'

def test_a2NFT_p0_tx_hash(a2NFT):
    assert a2NFT['txpoints'][0]['tx_hash'] == 'dd5e827c88eb24502cb74670fa58430e8c51fa6a514c46451829c1896438ce52'

def test_a2NFT_p0_pos(a2NFT):
    assert a2NFT['txpoints'][0]['pos'] == 1

def test_a2NFT_p0_value(a2NFT):
    assert a2NFT['txpoints'][0]['value'] == 20e8

def test_a2NFT_sent(a2NFT, gen):
    assert a2NFT['sent'] == { gen.chain.id: 0 }

def test_a2NFT_received(a2NFT, gen):
    assert a2NFT['received'] == { gen.chain.id: 20e8 }

def test_a2NFT_counts(a2NFT):
    assert a2NFT['counts'] == [1, 0]

@pytest.fixture(scope="module")
def an3j4(gen):
    return ah(gen, 'n3j41Rkn51bdfh3NgyaA7x2JKEsfuvq888')

def test_an3j4_binaddr(an3j4, gen):
    assert an3j4['binaddr'] == gen.chain.pubkey_hash(PUBKEYS[3])

def test_an3j4_subbinaddr(an3j4, gen):
    assert 'subbinaddr' not in an3j4

def test_an3j4_version(an3j4):
    assert an3j4['version'] == '\x6f'

def test_an3j4_chains(an3j4):
    assert len(an3j4['chains']) == 1

def test_an3j4_c0_name(an3j4):
    assert an3j4['chains'][0].name == 'Testnet'

def test_an3j4_balance(an3j4, gen):
    assert an3j4['balance'] == { gen.chain.id: 0 }

def test_an3j4_txpoints(an3j4):
    assert len(an3j4['txpoints']) == 1

def test_an3j4_p0_type(an3j4):
    assert an3j4['txpoints'][0]['type'] == 'escrow'

def test_an3j4_p0_is_out(an3j4):
    assert not an3j4['txpoints'][0]['is_out']

def test_an3j4_p0_nTime(an3j4):
    assert an3j4['txpoints'][0]['nTime'] == 1231006506

def test_an3j4_p0_chain(an3j4):
    assert an3j4['txpoints'][0]['chain'].name == 'Testnet'

def test_an3j4_p0_height(an3j4):
    assert an3j4['txpoints'][0]['height'] == 14

def test_an3j4_p0_blk_hash(an3j4):
    assert an3j4['txpoints'][0]['blk_hash'] == '0c2d2879773626a081d74e73b3dcb9276e2a366e4571b2de6d90c2a67295382e'

def test_an3j4_p0_tx_hash(an3j4):
    assert an3j4['txpoints'][0]['tx_hash'] == 'dd5e827c88eb24502cb74670fa58430e8c51fa6a514c46451829c1896438ce52'

def test_an3j4_p0_pos(an3j4):
    assert an3j4['txpoints'][0]['pos'] == 2

def test_an3j4_p0_value(an3j4):
    assert an3j4['txpoints'][0]['value'] == 20e8

def test_an3j4_sent(an3j4, gen):
    assert an3j4['sent'] == { gen.chain.id: 0 }

def test_an3j4_received(an3j4, gen):
    assert an3j4['received'] == { gen.chain.id: 0 }

def test_an3j4_counts(an3j4):
    assert an3j4['counts'] == [0, 0]

# TODO: look up multisig by its P2SH address, check subbinaddr.
# TODO: test different types of redeemed outputs.

def b(gen, b):
    return gen.store.export_block(chain=gen.chain, block_number=b)

@pytest.fixture(scope="module")
def b14(gen):
    return b(gen, 14)

def test_b14_chain_candidates(b14):
    assert len(b14['chain_candidates']) == 1

def test_b14cc0_chain_name(b14):
    assert b14['chain_candidates'][0]['chain'].name == 'Testnet'

def test_b14cc0_in_longest(b14):
    assert b14['chain_candidates'][0]['in_longest']

def test_b14_chain_satoshis(b14):
    assert b14['chain_satoshis'] == 750*10**8

def test_b14_chain_satoshi_seconds(b14):
    assert b14['chain_satoshi_seconds'] == -656822590000000000

def test_b14_chain_work(b14):
    assert b14['chain_work'] == 64425492495

def test_b14_fees(b14):
    assert b14['fees'] == 0.01e8

def test_b14_generated(b14):
    assert b14['generated'] == 50e8

def test_b14_hash(b14):
    assert b14['hash'] == '0c2d2879773626a081d74e73b3dcb9276e2a366e4571b2de6d90c2a67295382e'

def test_b14_hashMerkleRoot(b14):
    assert b14['hashMerkleRoot'] == '93f17b59330df6c97f8d305572b0b98608b34a2f4fa235e6ff69bbe343e3a764'

def test_b14_hashPrev(b14):
    assert b14['hashPrev'] == '2155786533653694385a772e33d9547848c809b1d1bce3500a377fe37ad3d250'

def test_b14_height(b14):
    assert b14['height'] == 14

def test_b14_nBits(b14):
    assert b14['nBits'] == 0x1d00ffff

def test_b14_next_block_hashes(b14):
    assert b14['next_block_hashes'] == []

def test_b14_nNonce(b14):
    assert b14['nNonce'] == 253

def test_b14_nTime(b14):
    assert b14['nTime'] == 1231006506

@pytest.mark.xfail
def test_b14_satoshis_destroyed(b14):
    # XXX Is this value right?
    assert b14['satoshis_destroyed'] == -328412110000000000

@pytest.mark.xfail
def test_b14_satoshi_seconds(b14):
    # XXX Is this value right?
    assert b14['satoshi_seconds'] == -328410480000000000

def test_b14_transactions(b14):
    assert len(b14['transactions']) == 2

def test_b14_t1_fees(b14):
    assert b14['transactions'][1]['fees'] == 0.01e8

def test_b14_t1_hash(b14):
    assert b14['transactions'][1]['hash'] == 'dd5e827c88eb24502cb74670fa58430e8c51fa6a514c46451829c1896438ce52'

def test_b14_t1_in(b14):
    assert len(b14['transactions'][1]['in']) == 1

def test_b14_t1i0_address_version(b14):
    assert b14['transactions'][1]['in'][0]['address_version'] == '\x6f'

def test_b14_t1i0_binaddr(b14, gen):
    assert b14['transactions'][1]['in'][0]['binaddr'] == gen.chain.pubkey_hash(PUBKEYS[1])

def test_b14_t1i0_value(b14):
    assert b14['transactions'][1]['in'][0]['value'] == 50e8

def test_b14_t1_out(b14):
    assert len(b14['transactions'][1]['out']) == 3

def test_b14_t1o0_address_version(b14):
    assert b14['transactions'][1]['out'][0]['address_version'] == '\x6f'

def test_b14_t1o0_binaddr(b14, gen):
    assert b14['transactions'][1]['out'][0]['binaddr'] == 'deb1f1ffbef6061a0b8f6d23b4e72164b4678253'.decode('hex')

def test_b14_t1o0_value(b14):
    assert b14['transactions'][1]['out'][0]['value'] == 9.99e8

def test_b14_t1o1_address_version(b14):
    assert b14['transactions'][1]['out'][1]['address_version'] == '\xc4'

def test_b14_t1o1_binaddr(b14, gen):
    assert b14['transactions'][1]['out'][1]['binaddr'] == 'f3aae15f9b92a094bb4e01afe99f99ab4135f362'.decode('hex')

def test_b14_t1o1_value(b14):
    assert b14['transactions'][1]['out'][1]['value'] == 20e8

def test_b14_t1o2_address_version(b14):
    assert b14['transactions'][1]['out'][2]['address_version'] == '\x6f'

def test_b14_t1o2_binaddr(b14, gen):
    assert b14['transactions'][1]['out'][2]['binaddr'] == 'b8bcada90d0992bdc64188d6a0ac3f9fd200d1d1'.decode('hex')

def test_b14_t1o2_subbinaddr(b14, gen):
    assert len(b14['transactions'][1]['out'][2]['subbinaddr']) == 3

def test_b14_t1o2k0(b14, gen):
    assert b14['transactions'][1]['out'][2]['subbinaddr'][0] == gen.chain.pubkey_hash(PUBKEYS[2])

def test_b14_t1o2k1(b14, gen):
    assert b14['transactions'][1]['out'][2]['subbinaddr'][1] == gen.chain.pubkey_hash(PUBKEYS[3])

def test_b14_t1o2k2(b14, gen):
    assert b14['transactions'][1]['out'][2]['subbinaddr'][2] == gen.chain.pubkey_hash(PUBKEYS[4])

def test_b14_t1o2_required_signatures(b14):
    assert b14['transactions'][1]['out'][2]['required_signatures'] == 2

def test_b14_t1o2_value(b14):
    assert b14['transactions'][1]['out'][2]['value'] == 20e8

def test_b14_value_out(b14):
    assert b14['value_out'] == 100e8

def test_b14_version(b14):
    assert b14['version'] == 1

def bt(gen, b, t):
    return gen.store.export_tx(tx_hash=gen.blocks[b]['transactions'][t]['hash'][::-1].encode('hex'), format='browser')

@pytest.fixture(scope="module")
def b14t1(gen):
    return bt(gen, 14, 1)

def test_b14t1o0_script_type(b14t1):
    assert b14t1['out'][0]['script_type'] == Abe.Chain.SCRIPT_TYPE_ADDRESS

def test_b14t1o0_binaddr(b14t1):
    assert b14t1['out'][0]['binaddr'] == Abe.util.decode_address('n1pTUVnjZ6GHxujaoJ62P9NBMNjLr5N2EQ')[1]
    assert b14t1['out'][0]['binaddr'] == 'deb1f1ffbef6061a0b8f6d23b4e72164b4678253'.decode('hex')

def test_b14t1o0_value(b14t1):
    assert b14t1['out'][0]['value'] == 9.99e8

def test_b14t1o1_script_type(b14t1):
    assert b14t1['out'][1]['script_type'] == Abe.Chain.SCRIPT_TYPE_P2SH

def test_b14t1o1_binaddr(b14t1):
    assert b14t1['out'][1]['binaddr'] == Abe.util.decode_address('2NFTctsgcAmrgtiboLJUx9q8qu5H1qVpcAb')[1]

def test_b14t1o1_value(b14t1):
    assert b14t1['out'][1]['value'] == 20e8

def test_b14t1o2_script_type(b14t1):
    assert b14t1['out'][2]['script_type'] == Abe.Chain.SCRIPT_TYPE_MULTISIG

def test_b14t1o2_required_signatures(b14t1):
    assert b14t1['out'][2]['required_signatures'] == 2

def test_b14t1o2_binaddr(b14t1, gen):
    assert b14t1['out'][2]['binaddr'] == 'b8bcada90d0992bdc64188d6a0ac3f9fd200d1d1'.decode('hex')

def test_b14t1o2_subbinaddr(b14t1, gen):
    assert b14t1['out'][2]['subbinaddr'] == [ gen.chain.pubkey_hash(pubkey) for pubkey in PUBKEYS[2:5] ]

def test_b14t1o2_value(b14t1):
    assert b14t1['out'][2]['value'] == 20e8

########NEW FILE########
__FILENAME__ = test_util
# Copyright(C) 2014 by Abe developers.

# test_util.py: test Abe utility functions

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

import pytest

import Abe.util as util

def test_calculate_target_004c792d():
    assert util.calculate_target(0x004c792d) == 0

def test_calculate_target_1d00ffff():
    assert util.calculate_target(0x1d00ffff) == 0xffff0000000000000000000000000000000000000000000000000000

def test_calculate_target_1c00800e():
    assert util.calculate_target(0x1c00800e) == 0x800e00000000000000000000000000000000000000000000000000

def test_calculate_target_1b0e7256():
    assert util.calculate_target(0x1b0e7256) == 0xe7256000000000000000000000000000000000000000000000000

def test_calculate_target_1b0098fa():
    assert util.calculate_target(0x1b0098fa) == 0x98fa000000000000000000000000000000000000000000000000

def test_calculate_target_1a6a93b3():
    assert util.calculate_target(0x1a6a93b3) == 0x6a93b30000000000000000000000000000000000000000000000

def test_calculate_target_1a022fbe():
    assert util.calculate_target(0x1a022fbe) == 0x22fbe0000000000000000000000000000000000000000000000

def test_calculate_target_1900896c():
    assert util.calculate_target(0x1900896c) == 0x896c00000000000000000000000000000000000000000000

def test_calculate_target_1e0fffff():
    assert util.calculate_target(0x1e0fffff) == 0xfffff000000000000000000000000000000000000000000000000000000

def test_calculate_target_1f123456():
    assert util.calculate_target(0x1f123456) == 0x12345600000000000000000000000000000000000000000000000000000000

def test_calculate_target_80555555():
    assert util.calculate_target(0x80555555) == 0x5555550000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

def test_calculate_target_00777777():
    assert util.calculate_target(0x00777777) == 0x0

def test_calculate_target_01cccccc():
    assert util.calculate_target(0x01cccccc) == -0x4c

def test_calculate_target_02666666():
    assert util.calculate_target(0x02666666) == 0x6666

def test_calculate_target_03aaaaaa():
    assert util.calculate_target(0x03aaaaaa) == -0x2aaaaa

########NEW FILE########
__FILENAME__ = namecoin_dump
#!/usr/bin/env python
# Dump the Namecoin name data to standard output.

# Copyright(C) 2011 by Abe developers.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/agpl.html>.

import sys
import logging

import Abe.DataStore
import Abe.readconf
from Abe.deserialize import script_GetOp, opcodes

NAME_NEW         = opcodes.OP_1
NAME_FIRSTUPDATE = opcodes.OP_2
NAME_UPDATE      = opcodes.OP_3
NAME_SCRIPT_MIN = '\x51'
NAME_SCRIPT_MAX = '\x54'
BLOCKS_TO_EXPIRE = 12000

def iterate_name_updates(store, logger, chain_id):
    for height, tx_pos, txout_pos, script in store.selectall("""
        SELECT cc.block_height, bt.tx_pos, txout.txout_pos,
               txout.txout_scriptPubKey
          FROM chain_candidate cc
          JOIN block_tx bt ON (cc.block_id = bt.block_id)
          JOIN txout ON (bt.tx_id = txout.tx_id)
         WHERE cc.chain_id = ?
           AND txout_scriptPubKey >= ? AND txout_scriptPubKey < ?
         ORDER BY cc.block_height, bt.tx_pos, txout.txout_pos""",
                                     (chain_id, store.binin(NAME_SCRIPT_MIN),
                                      store.binin(NAME_SCRIPT_MAX))):
        height = int(height)
        tx_pos = int(tx_pos)
        txout_pos = int(txout_pos)

        i = script_GetOp(store.binout(script))
        try:
            name_op = i.next()[0]
            if name_op == NAME_NEW:
                continue  # no effect on name map
            elif name_op == NAME_FIRSTUPDATE:
                
                is_first = True
                name = i.next()[1]
                newtx_hash = i.next()[1]
                #rand = i.next()[1]  # XXX documented as optional; is it?
                value = i.next()[1]
            elif name_op == NAME_UPDATE:
                is_first = False
                name = i.next()[1]
                value = i.next()[1]
            else:
                logger.warning("Unexpected first op: %s", repr(name_op))
                continue
        except StopIteration:
            logger.warning("Strange script at %d:%d:%d",
                           height, tx_pos, txout_pos)
            continue
        yield (height, tx_pos, txout_pos, is_first, name, value)

def get_expiration_depth(height):
    if height < 24000:
        return 12000
    if height < 48000:
        return height - 12000
    return 36000

def dump(store, logger, chain_id):
    from collections import deque
    top = store.get_block_number(chain_id)
    expires = {}
    expiry_queue = deque()  # XXX unneeded synchronization

    for x in iterate_name_updates(store, logger, chain_id):
        height, tx_pos, txout_pos, is_first, name, value = x
        while expiry_queue and expiry_queue[0]['block_id'] < height:
            e = expiry_queue.popleft()
            dead = e['name']
            if expires[dead] == e['block_id']:
                print repr((e['block_id'], 'Expired', dead, None))
        if expires.get(name, height) < height:
            type = 'Resurrected'
        elif is_first:
            type = 'First'
        else:
            type = 'Renewed'
        print repr((height, type, name, value))
        expiry = height + get_expiration_depth(height)
        expires[name] = expiry
        expiry_queue.append({'block_id': expiry, 'name': name, 'value': value})

    for e in expiry_queue:
        if expires[e['name']] > e['block_id']:
            pass
        elif e['block_id'] <= top:
            print repr((e['block_id'], 'Expired', e['name'], None))
        else:
            print repr((e['block_id'], 'Until', e['name'], e['value']))

def main(argv):
    logging.basicConfig(level=logging.DEBUG)
    conf = {
        'chain_id': None,
        }
    conf.update(Abe.DataStore.CONFIG_DEFAULTS)
    args, argv = Abe.readconf.parse_argv(argv, conf, strict=False)

    if argv and argv[0] in ('-h', '--help'):
        print "Usage: namecoin_dump.py --dbtype=MODULE --connect-args=ARGS"
        return 0
    elif argv:
        sys.stderr.write(
            "Error: unknown option `%s'\n"
            "See `namecoin_dump.py --help' for more information.\n"
            % (argv[0],))
        return 1

    store = Abe.DataStore.new(args)
    logger = logging.getLogger(__name__)
    if args.chain_id is None:
        row = store.selectrow(
            "SELECT chain_id FROM chain WHERE chain_name = 'Namecoin'")
        if row is None:
            raise Exception("Can not find Namecoin chain in database.")
        args.chain_id = row[0]

    dump(store, logger, args.chain_id)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

########NEW FILE########
