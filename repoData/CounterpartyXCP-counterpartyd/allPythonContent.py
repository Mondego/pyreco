__FILENAME__ = counterpartyd
#! /usr/bin/env python3
import os
import argparse
import json
import decimal
import sys
import logging
import unicodedata
import time
import dateutil.parser
import calendar
import configparser
from threading import Thread
import binascii

import requests
import appdirs
from prettytable import PrettyTable

from lib import (config, api, util, exceptions, bitcoin, blocks)
if os.name == 'nt':
    from lib import util_windows

D = decimal.Decimal
json_print = lambda x: print(json.dumps(x, sort_keys=True, indent=4))

def get_address (db, address, start_block=None, end_block=None):
    address_dict = {}
    address_dict['balances'] = util.get_balances(db, address=address)

    address_dict['debits'] = util.get_debits(db, address=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['credits'] = util.get_credits(db, address=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['burns'] = util.get_burns(db, source=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['sends'] = util.get_sends(db, source=address, destination=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block, filterop='or')
    #^ with filterop == 'or', we get all sends where this address was the source OR destination 

    address_dict['orders'] = util.get_orders(db, source=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['order_matches'] = util.get_order_matches(db, address=address,
        order_by='tx0_block_index', order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['btcpays'] = util.get_btcpays(db,
        filters=[{'field': 'source', 'op': '==', 'value': address}, {'field': 'destination', 'op': '==', 'value': address}],
        filterop='or', order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['issuances'] = util.get_issuances(db, issuer=address,
        order_by='block_index', order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['broadcasts'] = util.get_broadcasts(db, source=address,
        order_by='block_index', order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['bets'] = util.get_bets(db, source=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['bet_matches'] = util.get_bet_matches(db, address=address,
        order_by='tx0_block_index', order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['dividends'] = util.get_dividends(db, source=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['cancels'] = util.get_cancels(db, source=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['callbacks'] = util.get_callbacks(db, source=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['bet_expirations'] = util.get_bet_expirations(db, source=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['order_expirations'] = util.get_order_expirations(db, source=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['bet_match_expirations'] = util.get_bet_match_expirations(db, address=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['order_match_expirations'] = util.get_order_match_expirations(db, address=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    return address_dict


def format_order (order):
    give_quantity = util.devise(db, D(order['give_quantity']), order['give_asset'], 'output')
    get_quantity = util.devise(db, D(order['get_quantity']), order['get_asset'], 'output')
    give_remaining = util.devise(db, D(order['give_remaining']), order['give_asset'], 'output')
    get_remaining = util.devise(db, D(order['get_remaining']), order['get_asset'], 'output')
    give_asset = order['give_asset']
    get_asset = order['get_asset']

    if get_asset < give_asset:
        price = util.devise(db, D(order['get_quantity']) / D(order['give_quantity']), 'price', 'output')
        price_assets = get_asset + '/' + give_asset + ' ask'
    else:
        price = util.devise(db, D(order['give_quantity']) / D(order['get_quantity']), 'price', 'output')
        price_assets = give_asset + '/' + get_asset + ' bid'

    return [D(give_remaining), give_asset, price, price_assets, str(order['fee_required'] / config.UNIT), str(order['fee_provided'] / config.UNIT), order['expire_index'] - util.last_block(db)['block_index'], order['tx_hash']]

def format_bet (bet):
    odds = D(bet['counterwager_quantity']) / D(bet['wager_quantity'])

    if not bet['target_value']: target_value = None
    else: target_value = bet['target_value']
    if not bet['leverage']: leverage = None
    else: leverage = util.devise(db, D(bet['leverage']) / 5040, 'leverage', 'output')

    return [util.BET_TYPE_NAME[bet['bet_type']], bet['feed_address'], util.isodt(bet['deadline']), target_value, leverage, str(bet['wager_remaining'] / config.UNIT) + ' XCP', util.devise(db, odds, 'odds', 'output'), bet['expire_index'] - util.last_block(db)['block_index'], bet['tx_hash']]

def format_order_match (db, order_match):
    order_match_id = order_match['tx0_hash'] + order_match['tx1_hash']
    order_match_time_left = order_match['match_expire_index'] - util.last_block(db)['block_index']
    return [order_match_id, order_match_time_left]

def format_feed (feed):
    timestamp = util.isodt(feed['timestamp'])
    if not feed['text']:
        text = '<Locked>'
    else:
        text = feed['text']
    return [feed['source'], timestamp, text, feed['value'], D(feed['fee_fraction_int']) / D(1e8)]

def market (give_asset, get_asset):

    # Your Pending Orders Matches.
    awaiting_btcs = util.get_order_matches(db, status='pending', is_mine=True)
    table = PrettyTable(['Matched Order ID', 'Time Left'])
    for order_match in awaiting_btcs:
        order_match = format_order_match(db, order_match)
        table.add_row(order_match)
    print('Your Pending Order Matches')
    print(table)
    print('\n')

    # Open orders.
    orders = util.get_orders(db, status='open', show_expired=False)
    table = PrettyTable(['Give Quantity', 'Give Asset', 'Price', 'Price Assets', 'Required BTC Fee', 'Provided BTC Fee', 'Time Left', 'Tx Hash'])
    for order in orders:
        if give_asset and order['give_asset'] != give_asset: continue
        if get_asset and order['get_asset'] != get_asset: continue
        order = format_order(order)
        table.add_row(order)
    print('Open Orders')
    table = table.get_string(sortby='Price')
    print(table)
    print('\n')

    # Open bets.
    bets = util.get_bets(db, status='open')
    table = PrettyTable(['Bet Type', 'Feed Address', 'Deadline', 'Target Value', 'Leverage', 'Wager', 'Odds', 'Time Left', 'Tx Hash'])
    for bet in bets:
        bet = format_bet(bet)
        table.add_row(bet)
    print('Open Bets')
    print(table)
    print('\n')

    # Feeds
    broadcasts = util.get_broadcasts(db, status='valid', order_by='timestamp', order_dir='desc')
    table = PrettyTable(['Feed Address', 'Timestamp', 'Text', 'Value', 'Fee Fraction'])
    seen_addresses = []
    for broadcast in broadcasts:
        # Only show feeds with broadcasts in the last two weeks.
        last_block_time = util.last_block(db)['block_time']
        if broadcast['timestamp'] + config.TWO_WEEKS < last_block_time:
            continue
        # Always show only the latest broadcast from a feed address.
        if broadcast['source'] not in seen_addresses:
            feed = format_feed(broadcast)
            table.add_row(feed)
            seen_addresses.append(broadcast['source'])
        else:
            continue
    print('Feeds')
    print(table)


def cli(method, params, unsigned):

    # Get unsigned transaction serialisation.
    if bitcoin.is_valid(params['source']):
        if bitcoin.is_mine(params['source']):
            bitcoin.wallet_unlock()
        else:
            print('Source not in Bitcoind wallet.')
            answer = input('Public key (hexadecimal) or Private key (Wallet Import Format): ')

            # Public key or private key?
            try:
                binascii.unhexlify(answer)  # Check if hex.
                params['pubkey'] = answer   # If hex, assume public key.
                private_key_wif = None
            except binascii.Error:
                private_key_wif = answer    # Else, assume private key.
                params['pubkey'] = bitcoin.private_key_to_public_key(private_key_wif)
    else:
        raise exceptions.AddressError('Invalid address.')

    unsigned_tx_hex = util.api(method, params)
    print('Transaction (unsigned):', unsigned_tx_hex)

    # Ask to sign and broadcast.
    if not unsigned and input('Sign and broadcast? (y/N) ') == 'y':
        if bitcoin.is_mine(params['source']):
            private_key_wif = None
        elif not private_key_wif:   # If private key was not given earlier.
            private_key_wif = input('Private key (Wallet Import Format): ')

        # Sign and broadcast.
        signed_tx_hex = bitcoin.sign_tx(unsigned_tx_hex, private_key_wif=private_key_wif)
        print('Transaction (signed):', signed_tx_hex)
        print('Hash of transaction (broadcasted):', bitcoin.broadcast_tx(signed_tx_hex))


def set_options (data_dir=None,
                 bitcoind_rpc_connect=None, bitcoind_rpc_port=None,
                 bitcoind_rpc_user=None, bitcoind_rpc_password=None,
                 insight_enable=None, insight_connect=None, insight_port=None,
                 rpc_host=None, rpc_port=None, rpc_user=None, rpc_password=None,
                 log_file=None, pid_file=None, api_num_threads=None, api_request_queue_size=None,
                 database_file=None, testnet=False, testcoin=False, unittest=False, carefulness=0, force=False):

    # Unittests always run on testnet.
    if unittest and not testnet:
        raise Exception # TODO

    if force:
        config.FORCE = force
    else:
        config.FORCE = False

    # Data directory
    if not data_dir:
        config.DATA_DIR = appdirs.user_data_dir(appauthor='Counterparty', appname='counterpartyd', roaming=True)
    else:
        config.DATA_DIR = os.path.expanduser(data_dir)
    if not os.path.isdir(config.DATA_DIR): os.mkdir(config.DATA_DIR)

    # Configuration file
    configfile = configparser.ConfigParser()
    config_path = os.path.join(config.DATA_DIR, 'counterpartyd.conf')
    configfile.read(config_path)
    has_config = 'Default' in configfile
    #logging.debug("Config file: %s; Exists: %s" % (config_path, "Yes" if has_config else "No"))

    # testnet
    if testnet:
        config.TESTNET = testnet
    elif has_config and 'testnet' in configfile['Default']:
        config.TESTNET = configfile['Default'].getboolean('testnet')
    else:
        config.TESTNET = False

    # testcoin
    if testcoin:
        config.TESTCOIN = testcoin
    elif has_config and 'testcoin' in configfile['Default']:
        config.TESTCOIN = configfile['Default'].getboolean('testcoin')
    else:
        config.TESTCOIN = False

    # carefulness (check conservation of assets)
    if carefulness:
        config.CAREFULNESS = carefulness
    elif has_config and 'carefulness' in configfile['Default']:
        config.CAREFULNESS = configfile['Default'].getboolean('carefulness')
    else:
        config.CAREFULNESS = 0

    ##############
    # THINGS WE CONNECT TO

    # Bitcoind RPC host
    if bitcoind_rpc_connect:
        config.BITCOIND_RPC_CONNECT = bitcoind_rpc_connect
    elif has_config and 'bitcoind-rpc-connect' in configfile['Default'] and configfile['Default']['bitcoind-rpc-connect']:
        config.BITCOIND_RPC_CONNECT = configfile['Default']['bitcoind-rpc-connect']
    else:
        config.BITCOIND_RPC_CONNECT = 'localhost'

    # Bitcoind RPC port
    if bitcoind_rpc_port:
        config.BITCOIND_RPC_PORT = bitcoind_rpc_port
    elif has_config and 'bitcoind-rpc-port' in configfile['Default'] and configfile['Default']['bitcoind-rpc-port']:
        config.BITCOIND_RPC_PORT = configfile['Default']['bitcoind-rpc-port']
    else:
        if config.TESTNET:
            config.BITCOIND_RPC_PORT = 18332
        else:
            config.BITCOIND_RPC_PORT = 8332
    try:
        config.BITCOIND_RPC_PORT = int(config.BITCOIND_RPC_PORT)
        assert int(config.BITCOIND_RPC_PORT) > 1 and int(config.BITCOIND_RPC_PORT) < 65535
    except:
        raise Exception("Please specific a valid port number bitcoind-rpc-port configuration parameter")

    # Bitcoind RPC user
    if bitcoind_rpc_user:
        config.BITCOIND_RPC_USER = bitcoind_rpc_user
    elif has_config and 'bitcoind-rpc-user' in configfile['Default'] and configfile['Default']['bitcoind-rpc-user']:
        config.BITCOIND_RPC_USER = configfile['Default']['bitcoind-rpc-user']
    else:
        config.BITCOIND_RPC_USER = 'bitcoinrpc'

    # Bitcoind RPC password
    if bitcoind_rpc_password:
        config.BITCOIND_RPC_PASSWORD = bitcoind_rpc_password
    elif has_config and 'bitcoind-rpc-password' in configfile['Default'] and configfile['Default']['bitcoind-rpc-password']:
        config.BITCOIND_RPC_PASSWORD = configfile['Default']['bitcoind-rpc-password']
    else:
        raise exceptions.ConfigurationError('bitcoind RPC password not set. (Use configuration file or --bitcoind-rpc-password=PASSWORD)')

    config.BITCOIND_RPC = 'http://' + config.BITCOIND_RPC_USER + ':' + config.BITCOIND_RPC_PASSWORD + '@' + config.BITCOIND_RPC_CONNECT + ':' + str(config.BITCOIND_RPC_PORT)

    # insight enable
    if insight_enable:
        config.INSIGHT_ENABLE = insight_enable
    elif has_config and 'insight-enable' in configfile['Default']:
        config.INSIGHT_ENABLE = configfile['Default'].getboolean('insight-enable')
    else:
        config.INSIGHT_ENABLE = False
    
    if unittest:
        config.INSIGHT_ENABLE = True #override when running test suite
    if config.TESTNET:
        config.INSIGHT_ENABLE = True

    # insight API host
    if insight_connect:
        config.INSIGHT_CONNECT = insight_connect
    elif has_config and 'insight-connect' in configfile['Default'] and configfile['Default']['insight-connect']:
        config.INSIGHT_CONNECT = configfile['Default']['insight-connect']
    elif config.TESTNET:
        config.INSIGHT_CONNECT = 'test.insight.is'
    else:
        config.INSIGHT_CONNECT = 'live.insight.is'

    # insight API port
    if insight_port:
        config.INSIGHT_PORT = insight_port
    elif has_config and 'insight-port' in configfile['Default'] and configfile['Default']['insight-port']:
        config.INSIGHT_PORT = configfile['Default']['insight-port']
    else:
        if config.TESTNET:
            config.INSIGHT_PORT = 3001
        else:
            config.INSIGHT_PORT = 3000
    try:
        config.INSIGHT_PORT = int(config.INSIGHT_PORT)
        assert int(config.INSIGHT_PORT) > 1 and int(config.INSIGHT_PORT) < 65535
    except:
        raise Exception("Please specific a valid port number insight-port configuration parameter")

    config.INSIGHT = 'http://' + config.INSIGHT_CONNECT + ':' + str(config.INSIGHT_PORT)

    ##############
    # THINGS WE SERVE

    # counterpartyd API RPC host
    if rpc_host:
        config.RPC_HOST = rpc_host
    elif has_config and 'rpc-host' in configfile['Default'] and configfile['Default']['rpc-host']:
        config.RPC_HOST = configfile['Default']['rpc-host']
    else:
        config.RPC_HOST = 'localhost'

    #  counterpartyd API RPC port
    if rpc_port:
        config.RPC_PORT = rpc_port
    elif has_config and 'rpc-port' in configfile['Default'] and configfile['Default']['rpc-port']:
        config.RPC_PORT = configfile['Default']['rpc-port']
    else:
        if config.TESTNET:
            if config.TESTCOIN:
                config.RPC_PORT = 14001
            else:
                config.RPC_PORT = 14000
        else:
            if config.TESTCOIN:
                config.RPC_PORT = 4001
            else:
                config.RPC_PORT = 4000
    try:
        config.RPC_PORT = int(config.RPC_PORT)
        assert int(config.RPC_PORT) > 1 and int(config.RPC_PORT) < 65535
    except:
        raise Exception("Please specific a valid port number rpc-port configuration parameter")

    #  counterpartyd API RPC user
    if rpc_user:
        config.RPC_USER = rpc_user
    elif has_config and 'rpc-user' in configfile['Default'] and configfile['Default']['rpc-user']:
        config.RPC_USER = configfile['Default']['rpc-user']
    else:
        config.RPC_USER = 'rpc'

    #  counterpartyd API RPC password
    if rpc_password:
        config.RPC_PASSWORD = rpc_password
    elif has_config and 'rpc-password' in configfile['Default'] and configfile['Default']['rpc-password']:
        config.RPC_PASSWORD = configfile['Default']['rpc-password']
    else:
        raise exceptions.ConfigurationError('RPC password not set. (Use configuration file or --rpc-password=PASSWORD)')

    config.RPC = 'http://' + config.RPC_USER + ':' + config.RPC_PASSWORD + '@' + config.RPC_HOST + ':' + str(config.RPC_PORT)

    ##############
    # OTHER SETTINGS

    # Log
    if log_file:
        config.LOG = log_file
    elif has_config and 'log-file' in configfile['Default']:
        config.LOG = configfile['Default']['log-file']
    else:
        string = 'counterpartyd'
        if config.TESTNET:
            string += '.testnet'
        if config.TESTCOIN:
            string += '.testcoin'
        config.LOG = os.path.join(config.DATA_DIR, string + '.log')

    # PID file
    if pid_file:
        config.PID = pid_file
    elif has_config and 'pid-file' in configfile['Default']:
        config.PID = configfile['Default']['pid-file']
    else:
        config.PID = os.path.join(config.DATA_DIR, 'counterpartyd.pid')

    if not unittest:
        if config.TESTCOIN:
            config.PREFIX = b'XX'                   # 2 bytes (possibly accidentally created)
        else:
            config.PREFIX = b'CNTRPRTY'             # 8 bytes
    else:
        config.PREFIX = config.UNITTEST_PREFIX
        
    if api_num_threads:
        config.API_NUM_THREADS = int(api_num_threads)
    elif has_config and 'api-num-threads' in configfile['Default']:
        config.API_NUM_THREADS = int(configfile['Default']['api-num-threads'])
    else:
        config.API_NUM_THREADS = 15 #(not suitable for multiuser, high-performance production)

    if api_request_queue_size:
        config.API_REQUEST_QUEUE_SIZE = int(api_request_queue_size)
    elif has_config and 'api-request-queue-size' in configfile['Default']:
        config.API_REQUEST_QUEUE_SIZE = int(configfile['Default']['api-request-queue-size'])
    else:
        config.API_REQUEST_QUEUE_SIZE = 20 #(not suitable for multiuser, high-performance production)

    # Database
    if database_file:
        config.DATABASE = database_file
    else:
        string = 'counterpartyd.' + str(config.VERSION_MAJOR)
        if config.TESTNET:
            string += '.testnet'
        if config.TESTCOIN:
            string += '.testcoin'
        config.DATABASE = os.path.join(config.DATA_DIR, string + '.db')

    # (more) Testnet
    if config.TESTNET:
        if config.TESTCOIN:
            config.ADDRESSVERSION = b'\x6f'
            config.BLOCK_FIRST = 154908
            config.BURN_START = 154908
            config.BURN_END = 4017708   # Fifty years, at ten minutes per block.
            config.UNSPENDABLE = 'mvCounterpartyXXXXXXXXXXXXXXW24Hef'
        else:
            config.ADDRESSVERSION = b'\x6f'
            config.BLOCK_FIRST = 154908
            config.BURN_START = 154908
            config.BURN_END = 4017708   # Fifty years, at ten minutes per block.
            config.UNSPENDABLE = 'mvCounterpartyXXXXXXXXXXXXXXW24Hef'
    else:
        if config.TESTCOIN:
            config.ADDRESSVERSION = b'\x00'
            config.BLOCK_FIRST = 278270
            config.BURN_START = 278310
            config.BURN_END = 2500000   # A long time.
            config.UNSPENDABLE = '1CounterpartyXXXXXXXXXXXXXXXUWLpVr'
        else:
            config.ADDRESSVERSION = b'\x00'
            config.BLOCK_FIRST = 278270
            config.BURN_START = 278310
            config.BURN_END = 283810
            config.UNSPENDABLE = '1CounterpartyXXXXXXXXXXXXXXXUWLpVr'

def balances (address):
    if not bitcoin.base58_decode(address, config.ADDRESSVERSION):
        raise exceptions.AddressError('Not a valid Bitcoin address:',
                                             address)
    address_data = get_address(db, address=address)
    balances = address_data['balances']
    table = PrettyTable(['Asset', 'Amount'])
    table.add_row(['BTC', bitcoin.get_btc_balance(address, normalize=True)])  # BTC
    for balance in balances:
        asset = balance['asset']
        quantity = util.devise(db, balance['quantity'], balance['asset'], 'output')
        table.add_row([asset, quantity])
    print('Balances')
    print(table.get_string())


if __name__ == '__main__':
    if os.name == 'nt':
        #patch up cmd.exe's "challenged" (i.e. broken/non-existent) UTF-8 logging
        util_windows.fix_win32_unicode()
    
    # Parse command-line arguments.
    parser = argparse.ArgumentParser(prog='counterpartyd', description='the reference implementation of the Counterparty protocol')
    parser.add_argument('-V', '--version', action='version', version="counterpartyd v%s" % config.VERSION_STRING)

    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='sets log level to DEBUG instead of WARNING')
    parser.add_argument('--force', action='store_true', help='don\'t check whether Bitcoind is caught up')
    parser.add_argument('--testnet', action='store_true', help='use Bitcoin testnet addresses and block numbers')
    parser.add_argument('--testcoin', action='store_true', help='use the test Counterparty network on every blockchain')
    parser.add_argument('--unsigned', action='store_true', help='print out unsigned hex of transaction; do not sign or broadcast')
    parser.add_argument('--carefulness', type=int, default=0, help='check conservation of assets after every CAREFULNESS transactions (potentially slow)')
    parser.add_argument('--unconfirmed', action='store_true', help='allow the spending of unconfirmed transaction outputs')

    parser.add_argument('--data-dir', help='the directory in which to keep the database, config file and log file, by default')
    parser.add_argument('--database-file', help='the location of the SQLite3 database')
    parser.add_argument('--config-file', help='the location of the configuration file')
    parser.add_argument('--log-file', help='the location of the log file')
    parser.add_argument('--pid-file', help='the location of the pid file')
    parser.add_argument('--api-num-threads', help='the number of threads created for API request processing (CherryPy WSGI, default 10)')
    parser.add_argument('--api-request-queue-size', help='the size of the API request queue (CherryPY WSGI, default 5)')

    parser.add_argument('--bitcoind-rpc-connect', help='the hostname or IP of the bitcoind JSON-RPC server')
    parser.add_argument('--bitcoind-rpc-port', type=int, help='the bitcoind JSON-RPC port to connect to')
    parser.add_argument('--bitcoind-rpc-user', help='the username used to communicate with Bitcoind over JSON-RPC')
    parser.add_argument('--bitcoind-rpc-password', help='the password used to communicate with Bitcoind over JSON-RPC')

    parser.add_argument('--insight-enable', action='store_true', default=False, help='enable the use of insight, instead of blockchain.info')
    parser.add_argument('--insight-connect', help='the insight server hostname or IP to connect to')
    parser.add_argument('--insight-port', type=int, help='the insight server port to connect to')

    parser.add_argument('--rpc-host', help='the IP of the interface to bind to for providing JSON-RPC API access (0.0.0.0 for all interfaces)')
    parser.add_argument('--rpc-port', type=int, help='port on which to provide the counterpartyd JSON-RPC API')
    parser.add_argument('--rpc-user', help='required username to use the counterpartyd JSON-RPC API (via HTTP basic auth)')
    parser.add_argument('--rpc-password', help='required password (for rpc-user) to use the counterpartyd JSON-RPC API (via HTTP basic auth)')

    subparsers = parser.add_subparsers(dest='action', help='the action to be taken')

    parser_server = subparsers.add_parser('server', help='run the server (WARNING: not thread‐safe)')

    parser_send = subparsers.add_parser('send', help='create and broadcast a *send* message')
    parser_send.add_argument('--source', required=True, help='the source address')
    parser_send.add_argument('--destination', required=True, help='the destination address')
    parser_send.add_argument('--quantity', required=True, help='the quantity of ASSET to send')
    parser_send.add_argument('--asset', required=True, help='the ASSET of which you would like to send QUANTITY')
    parser_send.add_argument('--fee', help='the exact BTC fee to be paid to miners')

    parser_order = subparsers.add_parser('order', help='create and broadcast an *order* message')
    parser_order.add_argument('--source', required=True, help='the source address')
    parser_order.add_argument('--get-quantity', required=True, help='the quantity of GET_ASSET that you would like to receive')
    parser_order.add_argument('--get-asset', required=True, help='the asset that you would like to buy')
    parser_order.add_argument('--give-quantity', required=True, help='the quantity of GIVE_ASSET that you are willing to give')
    parser_order.add_argument('--give-asset', required=True, help='the asset that you would like to sell')
    parser_order.add_argument('--expiration', type=int, required=True, help='the number of blocks for which the order should be valid')
    parser_order.add_argument('--fee-fraction-required', default=config.FEE_FRACTION_REQUIRED_DEFAULT, help='the miners’ fee required for an order to match this one, as a fraction of the BTC to be bought')
    parser_order_fees = parser_order.add_mutually_exclusive_group()
    parser_order_fees.add_argument('--fee-fraction-provided', default=config.FEE_FRACTION_PROVIDED_DEFAULT, help='the miners’ fee provided, as a fraction of the BTC to be sold')
    parser_order_fees.add_argument('--fee', help='the exact BTC fee to be paid to miners')

    parser_btcpay= subparsers.add_parser('btcpay', help='create and broadcast a *BTCpay* message, to settle an Order Match for which you owe BTC')
    parser_btcpay.add_argument('--source', required=True, help='the source address')
    parser_btcpay.add_argument('--order-match-id', required=True, help='the concatenation of the hashes of the two transactions which compose the order match')
    parser_btcpay.add_argument('--fee', help='the exact BTC fee to be paid to miners')

    parser_issuance = subparsers.add_parser('issuance', help='issue a new asset, issue more of an existing asset or transfer the ownership of an asset')
    parser_issuance.add_argument('--source', required=True, help='the source address')
    parser_issuance.add_argument('--transfer-destination', help='for transfer of ownership of asset issuance rights')
    parser_issuance.add_argument('--quantity', default=0, help='the quantity of ASSET to be issued')
    parser_issuance.add_argument('--asset', required=True, help='the name of the asset to be issued (if it’s available)')
    parser_issuance.add_argument('--divisible', action='store_true', help='whether or not the asset is divisible (must agree with previous issuances)')
    parser_issuance.add_argument('--callable', dest='callable_', action='store_true', help='whether or not the asset is callable (must agree with previous issuances)')
    parser_issuance.add_argument('--call-date', help='the date from which a callable asset may be called back (must agree with previous issuances)')
    parser_issuance.add_argument('--call-price', help='the price, in XCP per whole unit, at which a callable asset may be called back (must agree with previous issuances)')
    parser_issuance.add_argument('--description', type=str, required=True, help='a description of the asset (set to ‘LOCK’ to lock against further issuances with non‐zero quantitys)')
    parser_issuance.add_argument('--fee', help='the exact BTC fee to be paid to miners')

    parser_broadcast = subparsers.add_parser('broadcast', help='broadcast textual and numerical information to the network')
    parser_broadcast.add_argument('--source', required=True, help='the source address')
    parser_broadcast.add_argument('--text', type=str, required=True, help='the textual part of the broadcast (set to ‘LOCK’ to lock feed)')
    parser_broadcast.add_argument('--value', type=float, default=-1, help='numerical value of the broadcast')
    parser_broadcast.add_argument('--fee-fraction', default=0, help='the fraction of bets on this feed that go to its operator')
    parser_broadcast.add_argument('--fee', help='the exact BTC fee to be paid to miners')

    parser_bet = subparsers.add_parser('bet', help='offer to make a bet on the value of a feed')
    parser_bet.add_argument('--source', required=True, help='the source address')
    parser_bet.add_argument('--feed-address', required=True, help='the address which publishes the feed to bet on')
    parser_bet.add_argument('--bet-type', choices=list(util.BET_TYPE_NAME.values()), required=True, help='choices: {}'.format(list(util.BET_TYPE_NAME.values())))
    parser_bet.add_argument('--deadline', required=True, help='the date and time at which the bet should be decided/settled')
    parser_bet.add_argument('--wager', required=True, help='the quantity of XCP to wager')
    parser_bet.add_argument('--counterwager', required=True, help='the minimum quantity of XCP to be wagered by the user to bet against you, if he were to accept the whole thing')
    parser_bet.add_argument('--target-value', default=0.0, help='target value for Equal/NotEqual bet')
    parser_bet.add_argument('--leverage', type=int, default=5040, help='leverage, as a fraction of 5040')
    parser_bet.add_argument('--expiration', type=int, required=True, help='the number of blocks for which the bet should be valid')
    parser_bet.add_argument('--fee', help='the exact BTC fee to be paid to miners')

    parser_dividend = subparsers.add_parser('dividend', help='pay dividends to the holders of an asset (in proportion to their stake in it)')
    parser_dividend.add_argument('--source', required=True, help='the source address')
    parser_dividend.add_argument('--quantity-per-unit', required=True, help='the quantity of XCP to be paid per whole unit held of ASSET')
    parser_dividend.add_argument('--asset', required=True, help='the asset to which pay dividends')
    parser_dividend.add_argument('--dividend-asset', required=True, help='asset in which to pay the dividends')
    parser_dividend.add_argument('--fee', help='the exact BTC fee to be paid to miners')

    parser_burn = subparsers.add_parser('burn', help='destroy bitcoins to earn XCP, during an initial period of time')
    parser_burn.add_argument('--source', required=True, help='the source address')
    parser_burn.add_argument('--quantity', required=True, help='quantity of BTC to be destroyed')
    parser_burn.add_argument('--fee', help='the exact BTC fee to be paid to miners')

    parser_cancel= subparsers.add_parser('cancel', help='cancel an open order or bet you created')
    parser_cancel.add_argument('--source', required=True, help='the source address')
    parser_cancel.add_argument('--offer-hash', required=True, help='the transaction hash of the order or bet')
    parser_cancel.add_argument('--fee', help='the exact BTC fee to be paid to miners')

    parser_callback = subparsers.add_parser('callback', help='callback a fraction of an asset')
    parser_callback.add_argument('--source', required=True, help='the source address')
    parser_callback.add_argument('--fraction', required=True, help='the fraction of ASSET to call back')
    parser_callback.add_argument('--asset', required=True, help='the asset to callback')
    parser_callback.add_argument('--fee', help='the exact BTC fee to be paid to miners')

    parser_address = subparsers.add_parser('balances', help='display the balances of a Counterparty address')
    parser_address.add_argument('address', help='the address you are interested in')

    parser_asset = subparsers.add_parser('asset', help='display the basic properties of a Counterparty asset')
    parser_asset.add_argument('asset', help='the asset you are interested in')

    parser_wallet = subparsers.add_parser('wallet', help='list the addresses in your Bitcoind wallet along with their balances in all Counterparty assets')

    parser_pending= subparsers.add_parser('pending', help='list pending order matches awaiting BTCpayment from you')

    parser_reparse = subparsers.add_parser('reparse', help='reparse all transactions in the database (WARNING: not thread‐safe)')

    parser_rollback = subparsers.add_parser('rollback', help='rollback database (WARNING: not thread‐safe)')
    parser_rollback.add_argument('block_index', type=int, help='the index of the last known good block')

    parser_market = subparsers.add_parser('market', help='fill the screen with an always up-to-date summary of the Counterparty market')
    parser_market.add_argument('--give-asset', help='only show orders offering to sell GIVE_ASSET')
    parser_market.add_argument('--get-asset', help='only show orders offering to buy GET_ASSET')

    args = parser.parse_args()

    # Configuration
    set_options(data_dir=args.data_dir,
                bitcoind_rpc_connect=args.bitcoind_rpc_connect, bitcoind_rpc_port=args.bitcoind_rpc_port,
                bitcoind_rpc_user=args.bitcoind_rpc_user, bitcoind_rpc_password=args.bitcoind_rpc_password,
                insight_enable=args.insight_enable, insight_connect=args.insight_connect, insight_port=args.insight_port,
                rpc_host=args.rpc_host, rpc_port=args.rpc_port, rpc_user=args.rpc_user, rpc_password=args.rpc_password,
                log_file=args.log_file, pid_file=args.pid_file, api_num_threads=args.api_num_threads,
                api_request_queue_size=args.api_request_queue_size, database_file=args.database_file, testnet=args.testnet,
                testcoin=args.testcoin, unittest=False, carefulness=args.carefulness, force=args.force)

    #Create/update pid file
    pid = str(os.getpid())
    pidf = open(config.PID, 'w')
    pidf.write(pid)
    pidf.close()    

    # Database
    db = util.connect_to_db()

    # Logging (to file and console).
    logger = logging.getLogger() #get root logger
    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    #Console logging
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)
    #File logging (rotated)
    max_log_size = 20 * 1024 * 1024 #max log size of 20 MB before rotation (make configurable later)
    if os.name == 'nt':
        fileh = util_windows.SanitizedRotatingFileHandler(config.LOG, maxBytes=max_log_size, backupCount=5)
    else:
        fileh = logging.handlers.RotatingFileHandler(config.LOG, maxBytes=max_log_size, backupCount=5)
    fileh.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(message)s', '%Y-%m-%d-T%H:%M:%S%z')
    fileh.setFormatter(formatter)
    logger.addHandler(fileh)
    #API requests logging (don't show on console in normal operation)
    requests_log = logging.getLogger("requests")
    requests_log.setLevel(logging.DEBUG if args.verbose else logging.WARNING)
    requests_log.propagate = False
    urllib3_log = logging.getLogger('urllib3')
    urllib3_log.setLevel(logging.DEBUG if args.verbose else logging.WARNING)
    urllib3_log.propagate = False

    if args.action == None: args.action = 'server'
    
    # TODO: Keep around only as long as reparse and rollback don’t use API.
    if not config.FORCE and args.action in ('reparse', 'rollback'):
        util.version_check(db)
        bitcoin.bitcoind_check(db)

    # MESSAGE CREATION
    if args.action == 'send':
        if args.fee: args.fee = util.devise(db, args.fee, 'BTC', 'input')
        quantity = util.devise(db, args.quantity, args.asset, 'input')
        cli('create_send', {'source': args.source, 'destination': args.destination, 'asset': args.asset,
                           'quantity': quantity, 'fee': args.fee, 'allow_unconfirmed_inputs': args.unconfirmed},
            args.unsigned)

    elif args.action == 'order':
        if args.fee: args.fee = util.devise(db, args.fee, 'BTC', 'input')
        fee_required, fee_fraction_provided = D(args.fee_fraction_required), D(args.fee_fraction_provided)
        give_quantity, get_quantity = D(args.give_quantity), D(args.get_quantity)

        # Fee argument is either fee_required or fee_provided, as necessary.
        if args.give_asset == 'BTC':
            fee_required = 0
            fee_fraction_provided = util.devise(db, fee_fraction_provided, 'fraction', 'input')
            fee_provided = round(D(fee_fraction_provided) * D(give_quantity) * D(config.UNIT))
            print('Fee provided: {} BTC'.format(util.devise(db, fee_provided, 'BTC', 'output')))
        elif args.get_asset == 'BTC':
            fee_provided = 0
            fee_fraction_required = util.devise(db, args.fee_fraction_required, 'fraction', 'input')
            fee_required = round(D(fee_fraction_required) * D(get_quantity) * D(config.UNIT))
            print('Fee required: {} BTC'.format(util.devise(db, fee_required, 'BTC', 'output')))
        else:
            fee_required = 0
            fee_provided = 0

        give_quantity = util.devise(db, give_quantity, args.give_asset, 'input')
        get_quantity = util.devise(db, get_quantity, args.get_asset, 'input')

        cli('create_order', {'source': args.source, 'give_asset': args.give_asset, 'give_quantity': give_quantity,
                            'get_asset': args.get_asset, 'get_quantity': get_quantity, 'expiration': args.expiration,
                            'fee_required': fee_required, 'fee_provided': fee_provided, 'fee': args.fee, 'allow_unconfirmed_inputs': args.unconfirmed},
           args.unsigned)

    elif args.action == 'btcpay':
        if args.fee: args.fee = util.devise(db, args.fee, 'BTC', 'input')
        cli('create_btcpay', {'source': args.source, 'order_match_id': args.order_match_id, 'fee': args.fee, 'allow_unconfirmed_inputs': args.unconfirmed}, args.unsigned)

    elif args.action == 'issuance':
        if args.fee: args.fee = util.devise(db, args.fee, 'BTC', 'input')
        quantity = util.devise(db, args.quantity, None, 'input',
                               divisible=args.divisible)
        if args.callable_:
            if not args.call_date:
                parser.error('must specify call date of callable asset', )
            if not args.call_price:
                parser.error('must specify call price of callable asset')
            call_date = calendar.timegm(dateutil.parser.parse(args.call_date).utctimetuple())
            call_price = float(args.call_price)
        else:
            call_date, call_price = 0, 0

        cli('create_issuance', {'source': args.source, 'asset': args.asset, 'quantity': quantity,
                                'divisible': args.divisible, 'description': args.description,
                                'callable_': args.callable_, 'call_date': call_date, 'call_price': call_price,
                                'transfer_destination': args.transfer_destination, 'fee': args.fee, 'allow_unconfirmed_inputs': args.unconfirmed},
           args.unsigned)

    elif args.action == 'broadcast':
        if args.fee: args.fee = util.devise(db, args.fee, 'BTC', 'input')
        value = util.devise(db, args.value, 'value', 'input')
        fee_fraction = util.devise(db, args.fee_fraction, 'fraction', 'input')

        cli('create_broadcast', {'source': args.source, 'fee_fraction': fee_fraction, 'text': args.text,
                                 'timestamp': int(time.time()), 'value': value, 'fee': args.fee, 'allow_unconfirmed_inputs': args.unconfirmed},
           args.unsigned)

    elif args.action == 'bet':
        if args.fee: args.fee = util.devise(db, args.fee, 'BTC', 'input')
        deadline = calendar.timegm(dateutil.parser.parse(args.deadline).utctimetuple())
        wager = util.devise(db, args.wager, 'XCP', 'input')
        counterwager = util.devise(db, args.counterwager, 'XCP', 'input')
        target_value = util.devise(db, args.target_value, 'value', 'input')
        leverage = util.devise(db, args.leverage, 'leverage', 'input')

        cli('create_bet', {'source': args.source, 'feed_address': args.feed_address, 'bet_type': args.bet_type,
                           'deadline': deadline, 'wager': wager, 'counterwager': counterwager, 'expiration': args.expiration,
                           'target_value': target_value, 'leverage': leverage, 'fee': args.fee, 'allow_unconfirmed_inputs': args.unconfirmed},
            args.unsigned)

    elif args.action == 'dividend':
        if args.fee: args.fee = util.devise(db, args.fee, 'BTC', 'input')
        quantity_per_unit = util.devise(db, args.quantity_per_unit, 'XCP', 'input')
        cli('create_dividend', {'source': args.source, 'quantity_per_unit': quantity_per_unit, 'asset': args.asset, 'dividend_asset': args.dividend_asset, 'fee': args.fee, 'allow_unconfirmed_inputs': args.unconfirmed},
           args.unsigned)

    elif args.action == 'burn':
        if args.fee: args.fee = util.devise(db, args.fee, 'BTC', 'input')
        quantity = util.devise(db, args.quantity, 'BTC', 'input')
        cli('create_burn', {'source': args.source, 'quantity': quantity, 'fee': args.fee, 'allow_unconfirmed_inputs': args.unconfirmed}, args.unsigned)

    elif args.action == 'cancel':
        if args.fee: args.fee = util.devise(db, args.fee, 'BTC', 'input')
        cli('create_cancel', {'source': args.source, 'offer_hash': args.offer_hash, 'fee': args.fee, 'allow_unconfirmed_inputs': args.unconfirmed}, args.unsigned)

    elif args.action == 'callback':
        if args.fee: args.fee = util.devise(db, args.fee, 'BTC', 'input')
        cli('create_callback', {'source': args.source, 'fraction': util.devise(db, args.fraction,
                                'fraction', 'input'), 'asset': args.asset, 'fee': args.fee, 'allow_unconfirmed_inputs': args.unconfirmed},
           args.unsigned)


    # VIEWING (temporary)
    elif args.action == 'balances':
        try:
            bitcoin.base58_decode(args.address, config.ADDRESSVERSION)
        except Exception:
            raise exceptions.AddressError('Invalid Bitcoin address:',
                                                  args.address)
        balances(args.address)

    elif args.action == 'asset':
        results = util.api('get_asset_info', ([args.asset],))
        if results:
            results = results[0]    # HACK
        else:
            print('Asset ‘{}’ not found.'.format(args.asset))
            exit(0)
        
        asset_id = util.get_asset_id(args.asset)
        divisible = results['divisible']
        supply = util.devise(db, results['supply'], args.asset, dest='output')
        call_date = util.isodt(results['call_date']) if results['call_date'] else results['call_date']
        call_price = str(results['call_price']) + ' XCP' if results['call_price'] else results['call_price']

        print('Asset Name:', args.asset)
        print('Asset ID:', asset_id)
        print('Divisible:', divisible)
        print('Supply:', supply)
        print('Issuer:', results['issuer'])
        print('Callable:', results['callable'])
        print('Call Date:', call_date)
        print('Call Price:', call_price)
        print('Description:', '‘' + results['description'] + '’')

        if args.asset != 'BTC':
            print('Shareholders:')
            balances = util.get_balances(db, asset=args.asset)
            print('\taddress, quantity, escrow')
            for holder in util.get_holders(db, args.asset):
                quantity = holder['address_quantity']
                if not quantity: continue
                quantity = util.devise(db, quantity, args.asset, 'output')
                if holder['escrow']: escrow = holder['escrow']
                else: escrow = 'None'
                print('\t' + str(holder['address']) + ',' + str(quantity) + ',' + escrow)


    elif args.action == 'wallet':
        total_table = PrettyTable(['Asset', 'Balance'])
        totals = {}

        print()
        for bunch in bitcoin.get_wallet():
            address, btc_balance = bunch[:2]
            address_data = get_address(db, address=address)
            balances = address_data['balances']
            table = PrettyTable(['Asset', 'Balance'])
            empty = True
            if btc_balance:
                table.add_row(['BTC', btc_balance])  # BTC
                if 'BTC' in totals.keys(): totals['BTC'] += btc_balance
                else: totals['BTC'] = btc_balance
                empty = False            
            for balance in balances:
                asset = balance['asset']
                try:
                    balance = D(util.devise(db, balance['quantity'], balance['asset'], 'output'))
                except:
                    balance = None
                if balance:
                    if asset in totals.keys(): totals[asset] += balance
                    else: totals[asset] = balance
                    table.add_row([asset, balance])
                    empty = False
            if not empty:
                print(address)
                print(table.get_string())
                print()
        for asset in totals.keys():
            balance = totals[asset]
            total_table.add_row([asset, round(balance, 8)])
        print('TOTAL')
        print(total_table.get_string())
        print()

    elif args.action == 'pending':
        awaiting_btcs = util.get_order_matches(db, status='pending', is_mine=True)
        table = PrettyTable(['Matched Order ID', 'Time Left'])
        for order_match in awaiting_btcs:
            order_match = format_order_match(db, order_match)
            table.add_row(order_match)
        print(table)

    elif args.action == 'market':
        market(args.give_asset, args.get_asset)


    # PARSING
    elif args.action == 'reparse':
        blocks.reparse(db)

    elif args.action == 'rollback':
        blocks.reparse(db, block_index=args.block_index)

    elif args.action == 'server':
        api_server = api.APIServer()
        api_server.daemon = True
        api_server.start()

        # Check that Insight works if enabled.
        if config.INSIGHT_ENABLE and not config.FORCE:
            try:
                r = requests.get(config.INSIGHT + '/api/sync/')
                if r.status_code != 200:
                    raise ValueError("Bad status code returned from insight: %s" % r.status_code)
                result = r.json()
                if result['status'] == 'error':
                    raise exceptions.InsightError('Insight reports error: %s' % result['error'])
                if result['status'] == 'syncing':
                    logging.warning("WARNING: Insight is not fully synced to the blockchain: %s%% complete" % result['syncPercentage'])
            except Exception as e:
                raise exceptions.InsightError('Could not connect to Insight server: %s' % e)

        blocks.follow(db)

    else:
        parser.print_help()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# counterpartyd documentation build configuration file, created by
# sphinx-quickstart on Mon Jan 20 15:45:40 2014.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'counterpartyd'
copyright = u'2014, Counterparty Team'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1.0'
# The full version, including alpha/beta/rc tags.
release = '0.1.0'

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
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
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


# -- Options for HTML output ---------------------------------------------------

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
htmlhelp_basename = 'counterpartyddoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'counterpartyd.tex', u'counterpartyd Documentation',
   u'Counterparty Team', 'manual'),
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


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'counterpartyd', u'counterpartyd Documentation',
     [u'Counterparty Team'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'counterpartyd', u'counterpartyd Documentation',
   u'Counterparty Team', 'counterpartyd', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = api
#! /usr/bin/python3

import sys
import os
import threading
import decimal
import time
import json
import logging
from logging import handlers as logging_handlers
D = decimal.Decimal

import apsw
import cherrypy
from cherrypy import wsgiserver
import jsonrpc
from jsonrpc import dispatcher

from . import (config, bitcoin, exceptions, util)
from . import (send, order, btcpay, issuance, broadcast, bet, dividend, burn, cancel, callback)

class APIServer(threading.Thread):

    def __init__ (self):
        threading.Thread.__init__(self)

    def run (self):
        db = util.connect_to_db(flags='SQLITE_OPEN_READONLY')

        ######################
        #READ API
        # TODO: Move all of these functions from util.py here (and use native SQLite queries internally).
        # TODO: Migrate away from the filters entirely?! (That is, always use sql method when not creating a new transaction?!)

        @dispatcher.add_method
        def sql(query):
            cursor = db.cursor()
            results = list(cursor.execute(query))
            cursor.close()
            return results

        @dispatcher.add_method
        def get_balances(filters=None, order_by=None, order_dir=None, filterop="and"):
            return util.get_balances(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                filterop=filterop)

        @dispatcher.add_method
        def get_bets(filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_bets(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_bet_matches(filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_bet_matches(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_broadcasts(filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_broadcasts(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_btcpays(filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_btcpays(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_burns(filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_burns(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_callbacks(filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_callbacks(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_cancels(filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_cancels(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_credits (filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_credits(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_debits (filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_debits(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_dividends(filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_dividends(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_issuances(filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_issuances(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_orders (filters=None, show_expired=True, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            results = util.get_orders(db,
                filters=filters,
                show_expired=show_expired,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)
            return results

        @dispatcher.add_method
        def get_order_matches (filters=None, post_filter_status=None, is_mine=False, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            assert post_filter_status in (None, 'completed', 'pending')
            return util.get_order_matches(db,
                filters=filters,
                post_filter_status=post_filter_status,
                is_mine=is_mine,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_sends (filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_sends(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_bet_expirations (filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_bet_expirations(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_order_expirations (filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_order_expirations(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_bet_match_expirations (filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_bet_match_expirations(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_order_match_expirations (filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_order_match_expirations(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)
        
        @dispatcher.add_method
        def get_messages(block_index):
            if not isinstance(block_index, int):
                raise Exception("block_index must be an integer.")
            
            cursor = db.cursor()
            cursor.execute('select * from messages where block_index = ? order by message_index asc', (block_index,))
            messages = cursor.fetchall()
            cursor.close()
            return messages

        @dispatcher.add_method
        def get_messages_by_index(message_indexes):
            """Get specific messages from the feed, based on the message_index.
            
            @param message_index: A single index, or a list of one or more message indexes to retrieve.
            """
            if not isinstance(message_indexes, list):
                message_indexes = [message_indexes,]
            for idx in message_indexes:  #make sure the data is clean
                if not isinstance(idx, int):
                    raise Exception("All items in message_indexes are not integers")
                
            cursor = db.cursor()
            cursor.execute('SELECT * FROM messages WHERE message_index IN (%s) ORDER BY message_index ASC'
                % (','.join([str(x) for x in message_indexes]),))
            messages = cursor.fetchall()
            cursor.close()
            return messages

        @dispatcher.add_method
        def get_xcp_supply():
            return util.xcp_supply(db)

        @dispatcher.add_method
        def get_asset_info(assets):
            if not isinstance(assets, list):
                raise Exception("assets must be a list of asset names, even if it just contains one entry")
            assetsInfo = []
            for asset in assets:

                # BTC and XCP.
                if asset in ['BTC', 'XCP']:
                    if asset == 'BTC':
                        supply = bitcoin.get_btc_supply(normalize=False)
                    else:
                        supply = util.xcp_supply(db)
                    
                    assetsInfo.append({
                        'asset': asset,
                        'owner': None,
                        'divisible': True,
                        'locked': False,
                        'supply': supply,
                        'callable': False,
                        'call_date': None,
                        'call_price': None,
                        'description': '',
                        'issuer': None
                    })
                    continue
                
                # User‐created asset.
                issuances = util.get_issuances(db,
                    filters={'field': 'asset', 'op': '==', 'value': asset},
                    status='valid',
                    order_by='block_index',
                    order_dir='asc')
                if not issuances: break #asset not found, most likely
                else: last_issuance = issuances[-1]
                supply = 0
                locked = False
                for e in issuances:
                    if e['locked']: locked = True
                    supply += e['quantity']
                assetsInfo.append({
                    'asset': asset,
                    'owner': last_issuance['issuer'],
                    'divisible': bool(last_issuance['divisible']),
                    'locked': locked,
                    'supply': supply,
                    'callable': bool(last_issuance['callable']),
                    'call_date': last_issuance['call_date'],
                    'call_price': last_issuance['call_price'],
                    'description': last_issuance['description'],
                    'issuer': last_issuance['issuer']})
            return assetsInfo

        @dispatcher.add_method
        def get_block_info(block_index):
            assert isinstance(block_index, int) 
            cursor = db.cursor()
            cursor.execute('''SELECT * FROM blocks WHERE block_index = ?''', (block_index,))
            try:
                blocks = list(cursor)
                assert len(blocks) == 1
                block = blocks[0]
            except IndexError:
                raise exceptions.DatabaseError('No blocks found.')
            cursor.close()
            return block
            
        @dispatcher.add_method
        def get_running_info():
            latestBlockIndex = bitcoin.get_block_count()
            
            try:
                util.database_check(db, latestBlockIndex)
            except:
                caught_up = False
            else:
                caught_up = True

            try:
                last_block = util.last_block(db)
            except:
                last_block = {'block_index': None, 'block_hash': None, 'block_time': None}
            
            try:
                last_message = util.last_message(db)
            except:
                last_message = None
            
            return {
                'db_caught_up': caught_up,
                'bitcoin_block_count': latestBlockIndex,
                'last_block': last_block,
                'last_message_index': last_message['message_index'] if last_message else -1,
                'running_testnet': config.TESTNET,
                'running_testcoin': config.TESTCOIN,
                'version_major': config.VERSION_MAJOR,
                'version_minor': config.VERSION_MINOR,
                'version_revision': config.VERSION_REVISION
            }

        @dispatcher.add_method
        def get_asset_names():
            cursor = db.cursor()
            names = [row['asset'] for row in cursor.execute("SELECT DISTINCT asset FROM issuances WHERE status = 'valid' ORDER BY asset ASC")]
            cursor.close()
            return names

        @dispatcher.add_method
        def get_element_counts():
            counts = {}
            cursor = db.cursor()
            for element in ['transactions', 'blocks', 'debits', 'credits', 'balances', 'sends', 'orders',
                'order_matches', 'btcpays', 'issuances', 'broadcasts', 'bets', 'bet_matches', 'dividends',
                'burns', 'cancels', 'callbacks', 'order_expirations', 'bet_expirations', 'order_match_expirations',
                'bet_match_expirations', 'messages']:
                cursor.execute("SELECT COUNT(*) AS count FROM %s" % element)
                count_list = cursor.fetchall()
                assert len(count_list) == 1
                counts[element] = count_list[0]['count']
            cursor.close()
            return counts

        ######################
        #WRITE/ACTION API
        @dispatcher.add_method
        def create_bet(source, feed_address, bet_type, deadline, wager, counterwager, expiration, target_value=0.0,
        leverage=5040, encoding='multisig', pubkey=None, allow_unconfirmed_inputs=False, fee=None):
            try:
                bet_type_id = util.BET_TYPE_ID[bet_type]
            except KeyError:
                raise exceptions.BetError('Unknown bet type.')
            tx_info = bet.compose(db, source, feed_address,
                              bet_type_id, deadline, wager,
                              counterwager, target_value,
                              leverage, expiration)
            return bitcoin.transaction(tx_info, encoding=encoding, exact_fee=fee, public_key_hex=pubkey, allow_unconfirmed_inputs=allow_unconfirmed_inputs)

        @dispatcher.add_method
        def create_broadcast(source, fee_fraction, text, timestamp, value=-1, encoding='multisig', pubkey=None, allow_unconfirmed_inputs=False, fee=None):
            tx_info = broadcast.compose(db, source, timestamp,
                                    value, fee_fraction, text)
            return bitcoin.transaction(tx_info, encoding=encoding, exact_fee=fee, public_key_hex=pubkey, allow_unconfirmed_inputs=allow_unconfirmed_inputs)

        @dispatcher.add_method
        def create_btcpay(source, order_match_id, encoding='multisig', pubkey=None, allow_unconfirmed_inputs=False, fee=None):
            tx_info = btcpay.compose(db, source, order_match_id)
            return bitcoin.transaction(tx_info, encoding=encoding, exact_fee=fee, public_key_hex=pubkey, allow_unconfirmed_inputs=allow_unconfirmed_inputs)

        @dispatcher.add_method
        def create_burn(source, quantity, encoding='multisig', pubkey=None, allow_unconfirmed_inputs=False, fee=None):
            tx_info = burn.compose(db, source, quantity)
            return bitcoin.transaction(tx_info, encoding=encoding, exact_fee=fee, public_key_hex=pubkey, allow_unconfirmed_inputs=allow_unconfirmed_inputs)

        @dispatcher.add_method
        def create_cancel(source, offer_hash, encoding='multisig', pubkey=None, allow_unconfirmed_inputs=False, fee=None):
            tx_info = cancel.compose(db, source, offer_hash)
            return bitcoin.transaction(tx_info, encoding=encoding, exact_fee=fee, public_key_hex=pubkey, allow_unconfirmed_inputs=allow_unconfirmed_inputs)

        @dispatcher.add_method
        def create_callback(source, fraction, asset, encoding='multisig', pubkey=None, allow_unconfirmed_inputs=False, fee=None):
            tx_info = callback.compose(db, source, fraction, asset)
            return bitcoin.transaction(tx_info, encoding=encoding, exact_fee=fee, public_key_hex=pubkey, allow_unconfirmed_inputs=allow_unconfirmed_inputs)

        @dispatcher.add_method
        def create_dividend(source, quantity_per_unit, asset, dividend_asset, encoding='multisig', pubkey=None, allow_unconfirmed_inputs=False, fee=None):
            tx_info = dividend.compose(db, source, quantity_per_unit, asset, dividend_asset)
            return bitcoin.transaction(tx_info, encoding=encoding, exact_fee=fee, public_key_hex=pubkey, allow_unconfirmed_inputs=allow_unconfirmed_inputs)

        @dispatcher.add_method
        def create_issuance(source, asset, quantity, divisible, description, callable_=None, call_date=None,
        call_price=None, transfer_destination=None, lock=False, encoding='multisig', pubkey=None, allow_unconfirmed_inputs=False, fee=None):
            try:
                quantity = int(quantity)
            except ValueError:
                raise Exception("Invalid quantity")
            if lock:
                description = "LOCK"
            tx_info = issuance.compose(db, source, transfer_destination,
                                   asset, quantity, divisible, callable_,
                                   call_date, call_price, description)
            return bitcoin.transaction(tx_info, encoding=encoding, exact_fee=fee, public_key_hex=pubkey, allow_unconfirmed_inputs=allow_unconfirmed_inputs)

        @dispatcher.add_method
        def create_order(source, give_asset, give_quantity, get_asset, get_quantity, expiration, fee_required,
                         fee_provided, encoding='multisig', pubkey=None, allow_unconfirmed_inputs=False, fee=None):
            tx_info = order.compose(db, source, give_asset, give_quantity,
                                    get_asset, get_quantity, expiration,
                                    fee_required)
            return bitcoin.transaction(tx_info, encoding=encoding, exact_fee=fee, fee_provided=fee_provided, public_key_hex=pubkey, allow_unconfirmed_inputs=allow_unconfirmed_inputs)

        @dispatcher.add_method
        def create_send(source, destination, asset, quantity, encoding='multisig', pubkey=None, allow_unconfirmed_inputs=False, fee=None):
            tx_info = send.compose(db, source, destination, asset, quantity)
            return bitcoin.transaction(tx_info, encoding=encoding, exact_fee=fee, public_key_hex=pubkey, allow_unconfirmed_inputs=allow_unconfirmed_inputs)

        @dispatcher.add_method
        def sign_tx(unsigned_tx_hex, privkey=None):
            return bitcoin.sign_tx(unsigned_tx_hex, private_key_wif=privkey)
                
        @dispatcher.add_method
        def broadcast_tx(signed_tx_hex):
            return bitcoin.broadcast_tx(signed_tx_hex)

        class API(object):
            @cherrypy.expose
            def index(self):
                try:
                    data = cherrypy.request.body.read().decode('utf-8')
                except ValueError:
                    raise cherrypy.HTTPError(400, 'Invalid JSON document')

                cherrypy.response.headers["Content-Type"] = "application/json"
                #CORS logic is handled in the nginx config

                # Check version.
                # Check that bitcoind is running, communicable, and caught up with the blockchain.
                # Check that the database has caught up with bitcoind.
                if not config.FORCE:
                    try: self.last_check
                    except: self.last_check = 0
                    try:
                        if time.time() - self.last_check >= 4 * 3600: # Four hours since last check.
                            code = 10
                            util.version_check(db)
                        if time.time() - self.last_check > 10 * 60: # Ten minutes since last check.
                            code = 11
                            bitcoin.bitcoind_check(db)
                            code = 12
                            util.database_check(db, bitcoin.get_block_count())  # TODO: If not reparse or rollback, once those use API.
                        self.last_check = time.time()
                    except Exception as e:
                        exception_name = e.__class__.__name__
                        exception_text = str(e)
                        response = jsonrpc.exceptions.JSONRPCError(code=code, message=exception_name, data=exception_text)
                        return response.json.encode()

                response = jsonrpc.JSONRPCResponseManager.handle(data, dispatcher)
                return response.json.encode()

        cherrypy.config.update({
            'log.screen': False,
            "environment": "embedded",
            'log.error_log.propagate': False,
            'log.access_log.propagate': False,
            "server.logToScreen" : False
        })
        checkpassword = cherrypy.lib.auth_basic.checkpassword_dict(
            {config.RPC_USER: config.RPC_PASSWORD})
        app_config = {
            '/': {
                'tools.trailing_slash.on': False,
                'tools.auth_basic.on': True,
                'tools.auth_basic.realm': 'counterpartyd',
                'tools.auth_basic.checkpassword': checkpassword,
            },
        }
        application = cherrypy.Application(API(), script_name="/api", config=app_config)

        #disable logging of the access and error logs to the screen
        application.log.access_log.propagate = False
        application.log.error_log.propagate = False

        if config.PREFIX != config.UNITTEST_PREFIX:  #skip setting up logs when for the test suite
            #set up a rotating log handler for this application
            # Remove the default FileHandlers if present.
            application.log.error_file = ""
            application.log.access_file = ""
            maxBytes = getattr(application.log, "rot_maxBytes", 10000000)
            backupCount = getattr(application.log, "rot_backupCount", 1000)
            # Make a new RotatingFileHandler for the error log.
            fname = getattr(application.log, "rot_error_file", os.path.join(config.DATA_DIR, "api.error.log"))
            h = logging_handlers.RotatingFileHandler(fname, 'a', maxBytes, backupCount)
            h.setLevel(logging.DEBUG)
            h.setFormatter(cherrypy._cplogging.logfmt)
            application.log.error_log.addHandler(h)
            # Make a new RotatingFileHandler for the access log.
            fname = getattr(application.log, "rot_access_file", os.path.join(config.DATA_DIR, "api.access.log"))
            h = logging_handlers.RotatingFileHandler(fname, 'a', maxBytes, backupCount)
            h.setLevel(logging.DEBUG)
            h.setFormatter(cherrypy._cplogging.logfmt)
            application.log.access_log.addHandler(h)

        #start up the API listener/handler
        server = wsgiserver.CherryPyWSGIServer((config.RPC_HOST, config.RPC_PORT), application,
            numthreads=config.API_NUM_THREADS, request_queue_size=config.API_REQUEST_QUEUE_SIZE)
        #logging.debug("Initializing API interface…")
        try:
            server.start()
        except OSError:
            raise Exception("Cannot start the API subsystem. Is counterpartyd"
                " already running, or is something else listening on port %s?" % config.RPC_PORT)

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

########NEW FILE########
__FILENAME__ = bet
#! /usr/bin/python3

"""
Datastreams are identified by the address that publishes them, and referenced
in transaction outputs.

For CFD leverage, 1x = 5040, 2x = 10080, etc.: 5040 is a superior highly
composite number and a colossally abundant number, and has 1-10, 12 as factors.

All wagers are in XCP.

Expiring a bet match doesn’t re‐open the constituent bets. (So all bets may be ‘filled’.)
"""

import struct
import decimal
D = decimal.Decimal
import time

from . import (util, config, bitcoin, exceptions, util)

FORMAT = '>HIQQdII'
LENGTH = 2 + 4 + 8 + 8 + 8 + 4 + 4
ID = 40

def cancel_bet (db, bet, status, block_index):
    cursor = db.cursor()

    # Update status of bet.
    bindings = {
        'status': status,
        'tx_hash': bet['tx_hash']
    }
    sql='update bets set status = :status where tx_hash = :tx_hash'
    cursor.execute(sql, bindings)
    util.message(db, block_index, 'update', 'bets', bindings)

    util.credit(db, block_index, bet['source'], 'XCP', bet['wager_remaining'], action='recredit wager remaining', event=bet['tx_hash'])

    cursor = db.cursor()

def cancel_bet_match (db, bet_match, status, block_index):
    # Does not re‐open, re‐fill, etc. constituent bets.

    cursor = db.cursor()

    # Recredit tx0 address.
    util.credit(db, block_index, bet_match['tx0_address'], 'XCP',
                bet_match['forward_quantity'], action='recredit forward quantity', event=bet_match['id'])

    # Recredit tx1 address.
    util.credit(db, block_index, bet_match['tx1_address'], 'XCP',
                bet_match['backward_quantity'], action='recredit backward quantity', event=bet_match['id'])

    # Update status of bet match.
    bindings = {
        'status': status,
        'bet_match_id': bet_match['id']
    }
    sql='update bet_matches set status = :status where id = :bet_match_id'
    cursor.execute(sql, bindings)
    util.message(db, block_index, 'update', 'bet_matches', bindings)

    cursor.close()


def get_fee_fraction (db, feed_address):
    '''Get fee fraction from the last broadcast from the feed_address address.
    '''
    broadcasts = util.get_broadcasts(db, source=feed_address)
    if broadcasts:
        last_broadcast = broadcasts[-1]
        fee_fraction_int = last_broadcast['fee_fraction_int']
        if fee_fraction_int: return fee_fraction_int / 1e8
        else: return 0
    else:
        return 0

def validate (db, source, feed_address, bet_type, deadline, wager_quantity,
              counterwager_quantity, target_value, leverage, expiration):
    problems = []

    # Look at feed to be bet on.
    broadcasts = util.get_broadcasts(db, status='valid', source=feed_address)
    if not broadcasts:
        problems.append('feed doesn’t exist')
    elif not broadcasts[-1]['text']:
        problems.append('feed is locked')
    elif broadcasts[-1]['timestamp'] >= deadline:
        problems.append('deadline in that feed’s past')

    if not bet_type in (0, 1, 2, 3):
        problems.append('unknown bet type')

    # Valid leverage level?
    if leverage != 5040 and bet_type in (2,3):   # Equal, NotEqual
        problems.append('leverage used with Equal or NotEqual')
    if leverage < 5040 and not bet_type in (0,1):   # BullCFD, BearCFD (fractional leverage makes sense precisely with CFDs)
        problems.append('leverage level too low')

    if not isinstance(wager_quantity, int):
        problems.append('wager_quantity must be in satoshis')
        return problems
    if not isinstance(counterwager_quantity, int):
        problems.append('counterwager_quantity must be in satoshis')
        return problems
    if not isinstance(expiration, int):
        problems.append('expiration must be expressed as an integer block delta')
        return problems

    if wager_quantity <= 0: problems.append('non‐positive wager')
    if counterwager_quantity <= 0: problems.append('non‐positive counterwager')
    if target_value < 0: problems.append('negative target value')
    if deadline < 0: problems.append('negative deadline')
    if expiration <= 0: problems.append('non‐positive expiration')

    if target_value and bet_type in (0,1):   # BullCFD, BearCFD
        problems.append('CFDs have no target value')

    if expiration > config.MAX_EXPIRATION:
        problems.append('expiration overflow')

    # For SQLite3
    if wager_quantity > config.MAX_INT or counterwager_quantity > config.MAX_INT or bet_type > config.MAX_INT or deadline > config.MAX_INT or leverage > config.MAX_INT:
        problems.append('integer overflow')

    return problems

def compose (db, source, feed_address, bet_type, deadline, wager_quantity,
            counterwager_quantity, target_value, leverage, expiration):

    problems = validate(db, source, feed_address, bet_type, deadline, wager_quantity,
                        counterwager_quantity, target_value, leverage, expiration)
    if deadline <= time.time() and config.PREFIX != config.UNITTEST_PREFIX:
        problems.append('deadline passed')
    if problems: raise exceptions.BetError(problems)

    data = config.PREFIX + struct.pack(config.TXTYPE_FORMAT, ID)
    data += struct.pack(FORMAT, bet_type, deadline,
                        wager_quantity, counterwager_quantity, target_value,
                        leverage, expiration)
    return (source, [(feed_address, None)], data)

def parse (db, tx, message):
    bet_parse_cursor = db.cursor()

    # Unpack message.
    try:
        assert len(message) == LENGTH
        (bet_type, deadline, wager_quantity,
         counterwager_quantity, target_value, leverage,
         expiration) = struct.unpack(FORMAT, message)
        status = 'open'
    except (AssertionError, struct.error) as e:
        (bet_type, deadline, wager_quantity,
         counterwager_quantity, target_value, leverage,
         expiration) = 0, 0, 0, 0, 0, 0, 0
        status = 'invalid: could not unpack'

    odds, fee_fraction = 0, 0
    feed_address = tx['destination']
    if status == 'open':
        try: odds = util.price(wager_quantity, counterwager_quantity, tx['block_index'])
        except Exception as e: pass

        fee_fraction = get_fee_fraction(db, feed_address)

        # Overbet
        bet_parse_cursor.execute('''SELECT * FROM balances \
                                    WHERE (address = ? AND asset = ?)''', (tx['source'], 'XCP'))
        balances = list(bet_parse_cursor)
        if not balances:
            wager_quantity = 0
        else:
            balance = balances[0]['quantity']
            if balance < wager_quantity:
                wager_quantity = balance
                counterwager_quantity = int(util.price(wager_quantity, odds, tx['block_index']))

        problems = validate(db, tx['source'], feed_address, bet_type, deadline, wager_quantity,
                            counterwager_quantity, target_value, leverage, expiration)
        if problems: status = 'invalid: ' + '; '.join(problems)

    # Debit quantity wagered. (Escrow.)
    if status == 'open':
        util.debit(db, tx['block_index'], tx['source'], 'XCP', wager_quantity)

    # Add parsed transaction to message-type–specific table.
    bindings = {
        'tx_index': tx['tx_index'],
        'tx_hash': tx['tx_hash'],
        'block_index': tx['block_index'],
        'source': tx['source'],
        'feed_address': feed_address,
        'bet_type': bet_type,
        'deadline': deadline,
        'wager_quantity': wager_quantity,
        'wager_remaining': wager_quantity,
        'counterwager_quantity': counterwager_quantity,
        'counterwager_remaining': counterwager_quantity,
        'target_value': target_value,
        'leverage': leverage,
        'expiration': expiration,
        'expire_index': tx['block_index'] + expiration,
        'fee_fraction_int': fee_fraction * 1e8,
        'status': status,
    }
    sql='insert into bets values(:tx_index, :tx_hash, :block_index, :source, :feed_address, :bet_type, :deadline, :wager_quantity, :wager_remaining, :counterwager_quantity, :counterwager_remaining, :target_value, :leverage, :expiration, :expire_index, :fee_fraction_int, :status)'
    bet_parse_cursor.execute(sql, bindings)

    # Match.
    if status == 'open':
        match(db, tx)

    bet_parse_cursor.close()

def match (db, tx):
    cursor = db.cursor()

    # Get bet in question.
    bets = list(cursor.execute('''SELECT * FROM bets\
                                WHERE tx_index=?''', (tx['tx_index'],)))
    assert len(bets) == 1
    tx1 = bets[0]

    # Get counterbet_type.
    if tx1['bet_type'] % 2: counterbet_type = tx1['bet_type'] - 1
    else: counterbet_type = tx1['bet_type'] + 1

    feed_address = tx1['feed_address']

    cursor.execute('''SELECT * FROM bets\
                             WHERE (feed_address=? AND status=? AND bet_type=?)''',
                             (tx1['feed_address'], 'open', counterbet_type))
    tx1_wager_remaining = tx1['wager_remaining']
    tx1_counterwager_remaining = tx1['counterwager_remaining']
    bet_matches = cursor.fetchall()
    if tx['block_index'] > 284500 or config.TESTNET:  # Protocol change.
        sorted(bet_matches, key=lambda x: x['tx_index'])                                        # Sort by tx index second.
        sorted(bet_matches, key=lambda x: util.price(x['wager_quantity'], x['counterwager_quantity'], tx1['block_index']))   # Sort by price first.

    tx1_status = 'open'
    for tx0 in bet_matches:
        if tx1_status != 'open': break

        # Bet types must be opposite.
        if not counterbet_type == tx0['bet_type']: continue
        if tx0['leverage'] == tx1['leverage']:
            leverage = tx0['leverage']
        else:
            continue

        # Target values must agree exactly.
        if tx0['target_value'] == tx1['target_value']:
            target_value = tx0['target_value']
        else:
            continue

        # Fee fractions must agree exactly.
        if tx0['fee_fraction_int'] != tx1['fee_fraction_int']:
            continue
        else:
            fee_fraction_int = tx0['fee_fraction_int']

        # Deadlines must agree exactly.
        if tx0['deadline'] != tx1['deadline']:
            continue

        # If the odds agree, make the trade. The found order sets the odds,
        # and they trade as much as they can.
        tx0_odds = util.price(tx0['wager_quantity'], tx0['counterwager_quantity'], tx1['block_index'])
        tx0_inverse_odds = util.price(tx0['counterwager_quantity'], tx0['wager_quantity'], tx1['block_index'])
        tx1_odds = util.price(tx1['wager_quantity'], tx1['counterwager_quantity'], tx1['block_index'])

        if tx['block_index'] < 286000: tx0_inverse_odds = util.price(1, tx0_odds, tx1['block_index']) # Protocol change.

        if tx0_inverse_odds <= tx1_odds:
            forward_quantity = int(min(tx0['wager_remaining'], int(util.price(tx1_wager_remaining, tx1_odds, tx1['block_index']))))
            backward_quantity = round(forward_quantity / tx0_odds)

            if not forward_quantity: continue
            if tx1['block_index'] >= 286500 or config.TESTNET:    # Protocol change.
                if not backward_quantity: continue

            bet_match_id = tx0['tx_hash'] + tx1['tx_hash']

            # Debit the order.
            # Counterwager remainings may be negative.
            tx0_wager_remaining = tx0['wager_remaining'] - forward_quantity
            tx0_counterwager_remaining = tx0['counterwager_remaining'] - backward_quantity
            tx1_wager_remaining = tx1_wager_remaining - backward_quantity
            tx1_counterwager_remaining = tx1_counterwager_remaining - forward_quantity

            # tx0
            tx0_status = 'open'
            if tx0_wager_remaining <= 0 or tx0_counterwager_remaining <= 0:
                # Fill order, and recredit give_remaining.
                tx0_status = 'filled'
                util.credit(db, tx1['block_index'], tx0['source'], 'XCP', tx0_wager_remaining, event=tx1['tx_hash'], action='filled')
            bindings = {
                'wager_remaining': tx0_wager_remaining,
                'counterwager_remaining': tx0_counterwager_remaining,
                'status': tx0_status,
                'tx_hash': tx0['tx_hash']
            }
            sql='update bets set wager_remaining = :wager_remaining, counterwager_remaining = :counterwager_remaining, status = :status where tx_hash = :tx_hash'
            cursor.execute(sql, bindings)
            util.message(db, tx1['block_index'], 'update', 'bets', bindings)

            if tx1['block_index'] >= 292000 or config.TESTNET:  # Protocol change
                if tx1_wager_remaining <= 0 or tx1_counterwager_remaining <= 0:
                    # Fill order, and recredit give_remaining.
                    tx1_status = 'filled'
                    util.credit(db, tx1['block_index'], tx1['source'], 'XCP', tx1_wager_remaining, event=tx1['tx_hash'], action='filled')
            # tx1
            bindings = {
                'wager_remaining': tx1_wager_remaining,
                'counterwager_remaining': tx1_counterwager_remaining,
                'status': tx1_status,
                'tx_hash': tx1['tx_hash']
            }
            sql='update bets set wager_remaining = :wager_remaining, counterwager_remaining = :counterwager_remaining, status = :status where tx_hash = :tx_hash'
            cursor.execute(sql, bindings)
            util.message(db, tx1['block_index'], 'update', 'bets', bindings)

            # Get last value of feed.
            initial_value = util.get_broadcasts(db, status='valid', source=tx1['feed_address'])[-1]['value']

            # Record bet fulfillment.
            bindings = {
                'id': tx0['tx_hash'] + tx['tx_hash'],
                'tx0_index': tx0['tx_index'],
                'tx0_hash': tx0['tx_hash'],
                'tx0_address': tx0['source'],
                'tx1_index': tx1['tx_index'],
                'tx1_hash': tx1['tx_hash'],
                'tx1_address': tx1['source'],
                'tx0_bet_type': tx0['bet_type'],
                'tx1_bet_type': tx1['bet_type'],
                'feed_address': tx1['feed_address'],
                'initial_value': initial_value,
                'deadline': tx1['deadline'],
                'target_value': tx1['target_value'],
                'leverage': tx1['leverage'],
                'forward_quantity': forward_quantity,
                'backward_quantity': backward_quantity,
                'tx0_block_index': tx0['block_index'],
                'tx1_block_index': tx1['block_index'],
                'tx0_expiration': tx0['expiration'],
                'tx1_expiration': tx1['expiration'],
                'match_expire_index': min(tx0['expire_index'], tx1['expire_index']),
                'fee_fraction_int': fee_fraction_int,
                'status': 'pending',
            }
            sql='insert into bet_matches values(:id, :tx0_index, :tx0_hash, :tx0_address, :tx1_index, :tx1_hash, :tx1_address, :tx0_bet_type, :tx1_bet_type, :feed_address, :initial_value, :deadline, :target_value, :leverage, :forward_quantity, :backward_quantity, :tx0_block_index, :tx1_block_index, :tx0_expiration, :tx1_expiration, :match_expire_index, :fee_fraction_int, :status)'
            cursor.execute(sql, bindings)

    cursor.close()

def expire (db, block_index, block_time):
    cursor = db.cursor()

    # Expire bets and give refunds for the quantity wager_remaining.
    cursor.execute('''SELECT * FROM bets \
                      WHERE (status = ? AND expire_index < ?)''', ('open', block_index))
    for bet in cursor.fetchall():
        cancel_bet(db, bet, 'expired', block_index)

        # Record bet expiration.
        bindings = {
            'bet_index': bet['tx_index'],
            'bet_hash': bet['tx_hash'],
            'source': bet['source'],
            'block_index': block_index
        }
        sql='insert into bet_expirations values(:bet_index, :bet_hash, :source, :block_index)'
        cursor.execute(sql, bindings)

    # Expire bet matches whose deadline is more than two weeks before the current block time.
    cursor.execute('''SELECT * FROM bet_matches \
                      WHERE (status = ? AND deadline < ?)''', ('pending', block_time - config.TWO_WEEKS))
    for bet_match in cursor.fetchall():
        cancel_bet_match(db, bet_match, 'expired', block_index)

        # Record bet match expiration.
        bindings = {
            'bet_match_id': bet_match['id'],
            'tx0_address': bet_match['tx0_address'],
            'tx1_address': bet_match['tx1_address'],
            'block_index': block_index
        }
        sql='insert into bet_match_expirations values(:bet_match_id, :tx0_address, :tx1_address, :block_index)'
        cursor.execute(sql, bindings)

    cursor.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

########NEW FILE########
__FILENAME__ = bitcoin
"""
Craft, sign and broadcast Bitcoin transactions.
Interface with Bitcoind.
"""

import os
import sys
import binascii
import json
import hashlib
import re
import time
import getpass
import decimal
import logging

import requests
from pycoin.ecdsa import generator_secp256k1, public_pair_for_secret_exponent
from pycoin.encoding import wif_to_tuple_of_secret_exponent_compressed, public_pair_to_sec
from pycoin.scripts import bitcoin_utils
from Crypto.Cipher import ARC4

from . import (config, exceptions, util)

# Constants
OP_RETURN = b'\x6a'
OP_PUSHDATA1 = b'\x4c'
OP_DUP = b'\x76'
OP_HASH160 = b'\xa9'
OP_EQUALVERIFY = b'\x88'
OP_CHECKSIG = b'\xac'
OP_1 = b'\x51'
OP_2 = b'\x52'
OP_CHECKMULTISIG = b'\xae'
b58_digits = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

D = decimal.Decimal
dhash = lambda x: hashlib.sha256(hashlib.sha256(x).digest()).digest()
bitcoin_rpc_session = None


def get_block_count():
    return int(rpc('getblockcount', []))
    
def get_block_hash(block_index):
    return rpc('getblockhash', [block_index])

def is_valid (address):
    return rpc('validateaddress', [address])['isvalid']

def is_mine (address):
    return rpc('validateaddress', [address])['ismine']

def send_raw_transaction (tx_hex):
    return rpc('sendrawtransaction', [tx_hex])

def get_raw_transaction (tx_hash):
    return rpc('getrawtransaction', [tx_hash, 1])

def get_block (block_hash):
    return rpc('getblock', [block_hash])

def get_block_hash (block_index):
    return rpc('getblockhash', [block_index])

def decode_raw_transaction (unsigned_tx_hex):
    return rpc('decoderawtransaction', [unsigned_tx_hex])

def get_wallet ():
    for group in rpc('listaddressgroupings', []):
        for bunch in group:
            yield bunch


def bitcoind_check (db):
    """Checks blocktime of last block to see if Bitcoind is running behind."""
    block_count = rpc('getblockcount', [])
    block_hash = rpc('getblockhash', [block_count])
    block = rpc('getblock', [block_hash])
    time_behind = time.time() - block['time']   # How reliable is the block time?!
    if time_behind > 60 * 60 * 2:   # Two hours.
        raise exceptions.BitcoindError('Bitcoind is running about {} seconds behind.'.format(round(time_behind)))

def connect (host, payload, headers):
    global bitcoin_rpc_session
    if not bitcoin_rpc_session: bitcoin_rpc_session = requests.Session()
    TRIES = 12
    for i in range(TRIES):
        try:
            response = bitcoin_rpc_session.post(host, data=json.dumps(payload), headers=headers)
            if i > 0: print('Successfully connected.', file=sys.stderr)
            return response
        except requests.exceptions.ConnectionError:
            print('Could not connect to Bitcoind. Sleeping for five seconds. (Try {}/{})'.format(i+1, TRIES), file=sys.stderr)
            time.sleep(5)
    return None

def wallet_unlock ():
    getinfo = rpc('getinfo', [])
    if 'unlocked_until' in getinfo:
        if getinfo['unlocked_until'] >= 60:
            return True # Wallet is unlocked for at least the next 60 seconds.
        else:
            passphrase = getpass.getpass('Enter your Bitcoind[‐Qt] wallet passhrase: ')
            print('Unlocking wallet for 60 (more) seconds.')
            rpc('walletpassphrase', [passphrase, 60])
    else:
        return True    # Wallet is unencrypted.

def rpc (method, params):
    headers = {'content-type': 'application/json'}
    payload = {
        "method": method,
        "params": params,
        "jsonrpc": "2.0",
        "id": 0,
    }

    '''
    if config.PREFIX == config.UNITTEST_PREFIX:
        CURR_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
        CURR_DIR += '/../test/'
        open(CURR_DIR + '/rpc.new', 'a') as f
        f.write(payload)
    '''

    response = connect(config.BITCOIND_RPC, payload, headers)
    if response == None:
        if config.TESTNET: network = 'testnet'
        else: network = 'mainnet'
        raise exceptions.BitcoindRPCError('Cannot communicate with Bitcoind. (counterpartyd is set to run on {}, is Bitcoind?)'.format(network))
    elif response.status_code not in (200, 500):
        raise exceptions.BitcoindRPCError(str(response.status_code) + ' ' + response.reason)

    '''
    if config.PREFIX == config.UNITTEST_PREFIX:
        print(response)
        f.close()
    '''

    # Return result, with error handling.
    response_json = response.json()
    if 'error' not in response_json.keys() or response_json['error'] == None:
        return response_json['result']
    elif response_json['error']['code'] == -5:   # RPC_INVALID_ADDRESS_OR_KEY
        raise exceptions.BitcoindError('{} Is txindex enabled in Bitcoind?'.format(response_json['error']))
    elif response_json['error']['code'] == -4:   # Unknown private key (locked wallet?)
        # If address in wallet, attempt to unlock.
        address = params[0]
        validate_address = rpc('validateaddress', [address])
        if validate_address['isvalid']:
            if validate_address['ismine']:
                raise exceptions.BitcoindError('Wallet is locked.')
            else:   # When will this happen?
                raise exceptions.BitcoindError('Source address not in wallet.')
        else:
            raise exceptions.AddressError('Invalid address.')
    elif response_json['error']['code'] == -1 and response_json['message'] == 'Block number out of range.':
        time.sleep(10)
        return rpc('getblockhash', [block_index])
        
    # elif config.PREFIX == config.UNITTEST_PREFIX:
    #     print(method)
    else:
        raise exceptions.BitcoindError('{}'.format(response_json['error']))

def base58_check_encode(b, version):
    b = binascii.unhexlify(bytes(b, 'utf-8'))
    d = version + b   # mainnet

    address_hex = d + dhash(d)[:4]

    # Convert big‐endian bytes to integer
    n = int('0x0' + binascii.hexlify(address_hex).decode('utf8'), 16)

    # Divide that integer into base58
    res = []
    while n > 0:
        n, r = divmod (n, 58)
        res.append(b58_digits[r])
    res = ''.join(res[::-1])

    # Encode leading zeros as base58 zeros
    czero = 0
    pad = 0
    for c in d:
        if c == czero: pad += 1
        else: break
    return b58_digits[0] * pad + res

def base58_decode (s, version):
    # Convert the string to an integer
    n = 0
    for c in s:
        n *= 58
        if c not in b58_digits:
            raise exceptions.InvalidBase58Error('Not a valid base58 character:', c)
        digit = b58_digits.index(c)
        n += digit

    # Convert the integer to bytes
    h = '%x' % n
    if len(h) % 2:
        h = '0' + h
    res = binascii.unhexlify(h.encode('utf8'))

    # Add padding back.
    pad = 0
    for c in s[:-1]:
        if c == b58_digits[0]: pad += 1
        else: break
    k = version * pad + res

    addrbyte, data, chk0 = k[0:1], k[1:-4], k[-4:]
    if addrbyte != version:
        raise exceptions.VersionByteError('incorrect version byte')
    chk1 = dhash(addrbyte + data)[:4]
    if chk0 != chk1:
        raise exceptions.Base58ChecksumError('Checksum mismatch: %r ≠ %r' % (chk0, chk1))
    return data

def var_int (i):
    if i < 0xfd:
        return (i).to_bytes(1, byteorder='little')
    elif i <= 0xffff:
        return b'\xfd' + (i).to_bytes(2, byteorder='little')
    elif i <= 0xffffffff:
        return b'\xfe' + (i).to_bytes(4, byteorder='little')
    else:
        return b'\xff' + (i).to_bytes(8, byteorder='little')

def op_push (i):
    if i < 0x4c:
        return (i).to_bytes(1, byteorder='little')              # Push i bytes.
    elif i <= 0xff:
        return b'\x4c' + (i).to_bytes(1, byteorder='little')    # OP_PUSHDATA1
    elif i <= 0xffff:
        return b'\x4d' + (i).to_bytes(2, byteorder='little')    # OP_PUSHDATA2
    else:
        return b'\x4e' + (i).to_bytes(4, byteorder='little')    # OP_PUSHDATA4

def serialise (encoding, inputs, destination_outputs, data_output=None, change_output=None, source=None, public_key=None):
    s  = (1).to_bytes(4, byteorder='little')                # Version

    # Number of inputs.
    s += var_int(int(len(inputs)))

    # List of Inputs.
    for i in range(len(inputs)):
        txin = inputs[i]
        s += binascii.unhexlify(bytes(txin['txid'], 'utf-8'))[::-1]         # TxOutHash
        s += txin['vout'].to_bytes(4, byteorder='little')   # TxOutIndex

        script = binascii.unhexlify(bytes(txin['scriptPubKey'], 'utf-8'))
        s += var_int(int(len(script)))                      # Script length
        s += script                                         # Script
        s += b'\xff' * 4                                    # Sequence

    # Number of outputs.
    n = 0
    n += len(destination_outputs)
    if data_output:
        data_array, value = data_output
        for data_chunk in data_array: n += 1
    else:
        data_array = []
    if change_output: n += 1
    s += var_int(n)

    # Destination output.
    for address, value in destination_outputs:
        pubkeyhash = base58_decode(address, config.ADDRESSVERSION)
        s += value.to_bytes(8, byteorder='little')          # Value
        script = OP_DUP                                     # OP_DUP
        script += OP_HASH160                                # OP_HASH160
        script += op_push(20)                               # Push 0x14 bytes
        script += pubkeyhash                                # pubKeyHash
        script += OP_EQUALVERIFY                            # OP_EQUALVERIFY
        script += OP_CHECKSIG                               # OP_CHECKSIG
        s += var_int(int(len(script)))                      # Script length
        s += script

    # Data output.
    for data_chunk in data_array:
        data_array, value = data_output # DUPE
        s += value.to_bytes(8, byteorder='little')        # Value

        if encoding == 'multisig':
            # Get data (fake) public key.
            pad_length = 33 - 1 - len(data_chunk)
            assert pad_length >= 0
            data_pubkey = bytes([len(data_chunk)]) + data_chunk + (pad_length * b'\x00')
            # Construct script.
            script = OP_1                                   # OP_1
            script += op_push(len(public_key))              # Push bytes of source public key
            script += public_key                            # Source public key
            script += op_push(len(data_pubkey))             # Push bytes of data chunk (fake) public key
            script += data_pubkey                           # Data chunk (fake) public key
            script += OP_2                                  # OP_2
            script += OP_CHECKMULTISIG                      # OP_CHECKMULTISIG
        elif encoding == 'opreturn':
            script = OP_RETURN                              # OP_RETURN
            script += op_push(len(data_chunk))              # Push bytes of data chunk (NOTE: OP_SMALLDATA?)
            script += data_chunk                            # Data chunk
        elif encoding == 'pubkeyhash':
            pad_length = 20 - 1 - len(data_chunk)
            assert pad_length >= 0
            obj1 = ARC4.new(binascii.unhexlify(inputs[0]['txid']))  # Arbitrary, easy‐to‐find, unique key.
            pubkeyhash = bytes([len(data_chunk)]) + data_chunk + (pad_length * b'\x00')
            pubkeyhash_encrypted = obj1.encrypt(pubkeyhash)
            # Construct script.
            script = OP_DUP                                     # OP_DUP
            script += OP_HASH160                                # OP_HASH160
            script += op_push(20)                               # Push 0x14 bytes
            script += pubkeyhash_encrypted                      # pubKeyHash
            script += OP_EQUALVERIFY                            # OP_EQUALVERIFY
            script += OP_CHECKSIG                               # OP_CHECKSIG
        else:
            raise exceptions.TransactionError('Unknown encoding‐scheme.')

        s += var_int(int(len(script)))                      # Script length
        s += script

    # Change output.
    if change_output:
        address, value = change_output
        pubkeyhash = base58_decode(address, config.ADDRESSVERSION)
        s += value.to_bytes(8, byteorder='little')          # Value
        script = OP_DUP                                     # OP_DUP
        script += OP_HASH160                                # OP_HASH160
        script += op_push(20)                               # Push 0x14 bytes
        script += pubkeyhash                                # pubKeyHash
        script += OP_EQUALVERIFY                            # OP_EQUALVERIFY
        script += OP_CHECKSIG                               # OP_CHECKSIG
        s += var_int(int(len(script)))                      # Script length
        s += script

    s += (0).to_bytes(4, byteorder='little')                # LockTime
    return s

def input_value_weight(amount):
    # Prefer outputs less than dust size, then bigger is better.
    if amount * config.UNIT <= config.REGULAR_DUST_SIZE:
        return 0
    else:
        return 1 / amount

def sort_unspent_txouts(unspent, allow_unconfirmed_inputs):
    # Get deterministic results (for multiAPIConsensus type requirements), sort by timestamp and vout index.
    # (Oldest to newest so the nodes don’t have to be exactly caught up to each other for consensus to be achieved.)
    try:
        unspent = sorted(unspent, key=util.sortkeypicker(['ts', 'vout']))
    except KeyError: # If timestamp isn’t given.
        pass

    # Sort by amount.
    unspent = sorted(unspent,key=lambda x:input_value_weight(x['amount']))

    # Remove unconfirmed txouts, if desired.
    if allow_unconfirmed_inputs:
        # Hackish: Allow only inputs which are either already confirmed or were seen only recently. (Skip outputs from slow‐to‐confirm transanctions.)
        try:
            unspent = [coin for coin in unspent if (coin['confirmations'] > 0 or (time.time() - coin['ts']) < 6 * 3600)] # Cutoff: six hours
        except (KeyError, TypeError):
            pass
    else:
        unspent = [coin for coin in unspent if coin['confirmations'] > 0]

    return unspent

def private_key_to_public_key (private_key_wif):
    secret_exponent, compressed = wif_to_tuple_of_secret_exponent_compressed(private_key_wif, is_test=config.TESTNET)
    public_pair = public_pair_for_secret_exponent(generator_secp256k1, secret_exponent)
    public_key = public_pair_to_sec(public_pair, compressed=compressed)
    public_key_hex = binascii.hexlify(public_key).decode('utf-8')
    return public_key_hex

# Replace unittest flag with fake bitcoind JSON-RPC server.
def transaction (tx_info, encoding, exact_fee=None, fee_provided=0, unittest=False, public_key_hex=None, allow_unconfirmed_inputs=False):

    (source, destination_outputs, data) = tx_info

    if exact_fee and not isinstance(exact_fee, int):
        raise exceptions.TransactionError('Exact fees must be in satoshis.')
    if not isinstance(fee_provided, int):
        raise exceptions.TransactionError('Fee provided must be in satoshis.')
    if encoding not in ('pubkeyhash', 'multisig', 'opreturn'):
        raise exceptions.TransactionError('Unknown encoding‐scheme.')

    # If public key is necessary for construction of (unsigned) transaction,
    # either use the public key provided, or derive it from a private key
    # retrieved from wallet.
    public_key = None
    if encoding in ('multisig', 'pubkeyhash'):
        # If no public key was provided, derive from private key.
        if not public_key_hex:
            # Get private key.
            if unittest:
                private_key_wif = 'cPdUqd5EbBWsjcG9xiL1hz8bEyGFiz4SW99maU9JgpL9TEcxUf3j'
            else:
                private_key_wif = rpc('dumpprivkey', [source])

            # Derive public key.
            public_key_hex = private_key_to_public_key(private_key_wif)
            
        pubkeypair = bitcoin_utils.parse_as_public_pair(public_key_hex)
        if not pubkeypair:
            raise exceptions.InputError('Invalid private key.')
        public_key = public_pair_to_sec(pubkeypair, compressed=True)

    # Protocol change.
    if encoding == 'pubkeyhash' and get_block_count() < 293000 and not config.TESTNET:
        raise exceptions.TransactionError('pubkeyhash encoding unsupported before block 293000')
    
    if config.PREFIX == config.UNITTEST_PREFIX: unittest = True

    # Validate source and all destination addresses.
    destinations = [address for address, value in destination_outputs]
    for address in destinations + [source]:
        if address:
            try:
                base58_decode(address, config.ADDRESSVERSION)
            except Exception:   # TODO
                raise exceptions.AddressError('Invalid Bitcoin address:', address)

    # Check that the source is in wallet.
    if not unittest and encoding in ('multisig') and not public_key:
        if not rpc('validateaddress', [source])['ismine']:
            raise exceptions.AddressError('Not one of your Bitcoin addresses:', source)

    # Check that the destination output isn't a dust output.
    # Set null values to dust size.
    new_destination_outputs = []
    for address, value in destination_outputs:
        if encoding == 'multisig':
            if value == None: value = config.MULTISIG_DUST_SIZE
            if not value >= config.MULTISIG_DUST_SIZE:
                raise exceptions.TransactionError('Destination output is below the dust target value.')
        else:
            if value == None: value = config.REGULAR_DUST_SIZE
            if not value >= config.REGULAR_DUST_SIZE:
                raise exceptions.TransactionError('Destination output is below the dust target value.')
        new_destination_outputs.append((address, value))
    destination_outputs = new_destination_outputs

    # Divide data into chunks.
    if data:
        def chunks(l, n):
            """ Yield successive n‐sized chunks from l.
            """
            for i in range(0, len(l), n): yield l[i:i+n]
        if encoding == 'pubkeyhash':
            data_array = list(chunks(data + config.PREFIX, 20 - 1)) # Prefix is also a suffix here.
        elif encoding == 'multisig':
            data_array = list(chunks(data, 33 - 1))
        elif encoding == 'opreturn':
            data_array = list(chunks(data, 80))
            assert len(data_array) == 1 # Only one OP_RETURN output currently supported (messages should all be shorter than 80 bytes, at the moment).
    else:
        data_array = []

    # Calculate total BTC to be sent.
    btc_out = 0
    if encoding == 'multisig': data_value = config.MULTISIG_DUST_SIZE
    elif encoding == 'opreturn': data_value = config.OP_RETURN_VALUE
    else: data_value = config.REGULAR_DUST_SIZE # Pay‐to‐PubKeyHash
    btc_out = sum([data_value for data_chunk in data_array])
    btc_out += sum([value for address, value in destination_outputs])

    # Get size of outputs.
    if encoding == 'multisig': data_output_size = 81        # 71 for the data
    elif encoding == 'opreturn': data_output_size = 90      # 80 for the data
    else: data_output_size = 25 + 9                         # Pay‐to‐PubKeyHash (25 for the data?)
    outputs_size = ((25 + 9) * len(destination_outputs)) + (len(data_array) * data_output_size)

    # Get inputs.
    unspent = get_unspent_txouts(source, normalize=True, unittest=unittest)
    unspent = sort_unspent_txouts(unspent, allow_unconfirmed_inputs)

    inputs, btc_in = [], 0
    change_quantity = 0
    sufficient_funds = False
    final_fee = config.FEE_PER_KB
    for coin in unspent:
        inputs.append(coin)
        btc_in += round(coin['amount'] * config.UNIT)

        # If exact fee is specified, use that. Otherwise, calculate size of tx and base fee on that (plus provide a minimum fee for selling BTC).
        if exact_fee:
            final_fee = exact_fee
        else:
            size = 181 * len(inputs) + outputs_size + 10
            necessary_fee = (int(size / 10000) + 1) * config.FEE_PER_KB
            final_fee = max(fee_provided, necessary_fee)
            assert final_fee >= 1 * config.FEE_PER_KB

        # Check if good.
        change_quantity = btc_in - (btc_out + final_fee)
        if change_quantity == 0 or change_quantity >= config.REGULAR_DUST_SIZE: # If change is necessary, must not be a dust output.
            sufficient_funds = True
            break
    if not sufficient_funds:
        # Approximate needed change, fee by with most recently calculated quantities.
        total_btc_out = btc_out + max(change_quantity, 0) + final_fee
        raise exceptions.BalanceError('Insufficient bitcoins at address {}. (Need approximately {} BTC.)'.format(source, total_btc_out / config.UNIT))

    # Construct outputs.
    if data: data_output = (data_array, data_value)
    else: data_output = None
    if change_quantity: change_output = (source, change_quantity)
    else: change_output = None

    # Serialise inputs and outputs.
    transaction = serialise(encoding, inputs, destination_outputs, data_output, change_output, source=source, public_key=public_key)
    unsigned_tx_hex = binascii.hexlify(transaction).decode('utf-8')
    return unsigned_tx_hex

def sign_tx (unsigned_tx_hex, private_key_wif=None):
    """Sign unsigned transaction serialisation."""

    if private_key_wif:
        # TODO: Hack! (pybitcointools is Python 2 only)
        import subprocess
        i = 0
        tx_hex = unsigned_tx_hex
        while True: # pybtctool doesn’t implement `signall`
            try:
                tx_hex = subprocess.check_output(['pybtctool', 'sign', tx_hex, str(i), private_key_wif], stderr=subprocess.DEVNULL)
            except Exception as e:
                break
        if tx_hex != unsigned_tx_hex:
            signed_tx_hex = tx_hex.decode('utf-8')
            return signed_tx_hex[:-1]   # Get rid of newline.
        else:
            raise exceptions.TransactionError('Could not sign transaction with pybtctool.')

    else:   # Assume source is in wallet and wallet is unlocked.
        result = rpc('signrawtransaction', [unsigned_tx_hex])
        if result['complete']:
            signed_tx_hex = result['hex']
        else:
            raise exceptions.TransactionError('Could not sign transaction with Bitcoin Core.')

    return signed_tx_hex

def broadcast_tx (signed_tx_hex):
    return send_raw_transaction(signed_tx_hex)

def normalize_quantity(quantity, divisible=True):
    if divisible:
        return float((D(quantity) / D(config.UNIT)).quantize(D('.00000000'), rounding=decimal.ROUND_HALF_EVEN)) 
    else: return quantity

def get_btc_balance(address, normalize=False):
    # TODO: shows unconfirmed BTC balance, while counterpartyd shows only confirmed balances for all other assets.
    """returns the BTC balance for a specific address"""
    if config.INSIGHT_ENABLE:
        r = requests.get(config.INSIGHT + '/api/addr/' + address)
        if r.status_code != 200:
            return "???"
        else:
            data = r.json()
            return data['balance'] if normalize else data['balanceSat']
    else: #use blockchain
        r = requests.get("https://blockchain.info/q/addressbalance/" + address)
        # ^any other services that provide this?? (blockexplorer.com doesn't...)
        if r.status_code != 200:
            return "???"
        else:
            return normalize_quantity(int(r.text)) if normalize else int(r.text)

def get_btc_supply(normalize=False):
    """returns the total supply of BTC (based on what bitcoind says the current block height is)"""
    block_count = get_block_count()
    blocks_remaining = block_count
    total_supply = 0 
    reward = 50.0
    while blocks_remaining > 0:
        if blocks_remaining >= 210000:
            blocks_remaining -= 210000
            total_supply += 210000 * reward
            reward /= 2
        else:
            total_supply += (blocks_remaining * reward)
            blocks_remaining = 0
    return total_supply if normalize else int(total_supply * config.UNIT)

def get_unspent_txouts(address, normalize=False, unittest=False):
    """returns a list of unspent outputs for a specific address
    @return: A list of dicts, with each entry in the dict having the following keys:
        * 
    """

    # Unittest
    if unittest:
        CURR_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
        with open(CURR_DIR + '/../test/listunspent.test.json', 'r') as listunspent_test_file:   # HACK
            wallet_unspent = json.load(listunspent_test_file)
            return [output for output in wallet_unspent if output['address'] == address]

    if rpc('validateaddress', [address])['ismine']:
        wallet_unspent = rpc('listunspent', [0, 999999])
        return [output for output in wallet_unspent if output['address'] == address]
    else:
        if config.INSIGHT_ENABLE:
            r = requests.get(config.INSIGHT + '/api/addr/' + address + '/utxo')
            if r.status_code != 200:
                raise Exception("Can't get unspent txouts: insight returned bad status code: %s" % r.status_code)

            outputs = r.json()
            if not normalize: #listed normalized by default out of insight...we need to take to satoshi
                for d in outputs:
                    d['quantity'] = int(d['quantity'] * config.UNIT)
            return outputs

        else: #use blockchain
            r = requests.get("https://blockchain.info/unspent?active=" + address)
            if r.status_code == 500 and r.text.lower() == "no free outputs to spend":
                return []
            elif r.status_code != 200:
                raise Exception("Bad status code returned from blockchain.info: %s" % r.status_code)
            data = r.json()['unspent_outputs']
            outputs = []
            for d in data:
                #blockchain.info lists the txhash in some weird reversed string notation with character pairs fipped...fun
                d['tx_hash'] = d['tx_hash'][::-1] #reverse string
                d['tx_hash'] = ''.join([d['tx_hash'][i:i+2][::-1] for i in range(0, len(d['tx_hash']), 2)]) #flip the character pairs within the string
                outputs.append({
                    'account': "",
                    'address': address,
                    'txid': d['tx_hash'],
                    'vout': d['tx_output_n'],
                    'ts': None,
                    'scriptPubKey': d['script'],
                    'amount': normalize_quantity(d['value']) if normalize else d['value'],  # This is what Bitcoin uses for a field name.
                    'confirmations': d['confirmations'],
                })
            return outputs


# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

########NEW FILE########
__FILENAME__ = blocks
"""
Initialise database.

Sieve blockchain for Counterparty transactions, and add them to the database.
"""

import os
import time
import binascii
import struct
import decimal
D = decimal.Decimal
import logging
from Crypto.Cipher import ARC4

from . import (config, exceptions, util, bitcoin)
from . import (send, order, btcpay, issuance, broadcast, bet, dividend, burn, cancel, callback)

def check_conservation (db):
    logging.debug('Status: Checking for conservation of assets.')

    supplies = util.get_supplies(db)
    for asset in supplies.keys():

        issued = supplies[asset]
        held = sum([holder['address_quantity'] for holder in util.get_holders(db, asset)])
        # import json
        # json_print = lambda x: print(json.dumps(x, sort_keys=True, indent=4))
        # json_print(util.get_holders(db, asset))
        if held != issued:
            raise exceptions.SanityError('{} {} issued ≠ {} {} held'.format(util.devise(db, issued, asset, 'output'), asset, util.devise(db, held, asset, 'output'), asset))
        logging.debug('Status: {} has been conserved ({} {} both issued and held)'.format(asset, util.devise(db, issued, asset, 'output'), asset))

def parse_tx (db, tx):
    parse_tx_cursor = db.cursor()
    # Burns.
    if tx['destination'] == config.UNSPENDABLE:
        burn.parse(db, tx)
        return

    try:
        message_type_id = struct.unpack(config.TXTYPE_FORMAT, tx['data'][:4])[0]
    except:
        # Mark transaction as of unsupported type.
        message_type_id = None

    message = tx['data'][4:]
    if message_type_id == send.ID:
        send.parse(db, tx, message)
    elif message_type_id == order.ID:
        order.parse(db, tx, message)
    elif message_type_id == btcpay.ID:
        btcpay.parse(db, tx, message)
    elif message_type_id == issuance.ID:
        issuance.parse(db, tx, message)
    elif message_type_id == broadcast.ID:
        broadcast.parse(db, tx, message)
    elif message_type_id == bet.ID:
        bet.parse(db, tx, message)
    elif message_type_id == dividend.ID:
        dividend.parse(db, tx, message)
    elif message_type_id == cancel.ID:
        cancel.parse(db, tx, message)
    elif message_type_id == callback.ID:
        callback.parse(db, tx, message)
    else:
        parse_tx_cursor.execute('''UPDATE transactions \
                                   SET supported=? \
                                   WHERE tx_hash=?''',
                                (False, tx['tx_hash']))
        logging.info('Unsupported transaction: hash {}; data {}'.format(tx['tx_hash'], tx['data']))

    # Check for conservation of assets every CAREFULNESS transactions.
    if config.CAREFULNESS and not tx['tx_index'] % config.CAREFULNESS:
        check_conservation(db)

    parse_tx_cursor.close()

def parse_block (db, block_index, block_time):
    """This is a separate function from follow() so that changing the parsing
    rules doesn't require a full database rebuild. If parsing rules are changed
    (but not data identification), then just restart `counterparty.py follow`.

    """
    parse_block_cursor = db.cursor()

    # Expire orders and bets.
    order.expire(db, block_index)
    bet.expire(db, block_index, block_time)

    # Parse transactions, sorting them by type.
    parse_block_cursor.execute('''SELECT * FROM transactions \
                                  WHERE block_index=? ORDER BY tx_index''',
                               (block_index,))
    transactions = parse_block_cursor.fetchall()
    for tx in transactions:
        parse_tx(db, tx)

    parse_block_cursor.close()

def initialise(db):
    cursor = db.cursor()

    # Blocks
    cursor.execute('''CREATE TABLE IF NOT EXISTS blocks(
                      block_index INTEGER UNIQUE,
                      block_hash TEXT UNIQUE,
                      block_time INTEGER,
                      PRIMARY KEY (block_index, block_hash))
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      block_index_idx ON blocks (block_index)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      index_hash_idx ON blocks (block_index, block_hash)
                   ''')

    # Transactions
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions(
                      tx_index INTEGER UNIQUE,
                      tx_hash TEXT UNIQUE,
                      block_index INTEGER,
                      block_hash TEXT,
                      block_time INTEGER,
                      source TEXT,
                      destination TEXT,
                      btc_amount INTEGER,
                      fee INTEGER,
                      data BLOB,
                      supported BOOL DEFAULT 1,
                      FOREIGN KEY (block_index, block_hash) REFERENCES blocks(block_index, block_hash),
                      PRIMARY KEY (tx_index, tx_hash, block_index))
                    ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      block_index_idx ON transactions (block_index)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      tx_index_idx ON transactions (tx_index)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      tx_hash_idx ON transactions (tx_hash)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      index_hash_index_idx ON transactions (tx_index, tx_hash, block_index)
                   ''')

    # Purge database of blocks, transactions from before BLOCK_FIRST.
    cursor.execute('''DELETE FROM blocks WHERE block_index < ?''', (config.BLOCK_FIRST,))
    cursor.execute('''DELETE FROM transactions WHERE block_index < ?''', (config.BLOCK_FIRST,))


    # (Valid) debits
    cursor.execute('''CREATE TABLE IF NOT EXISTS debits(
                      block_index INTEGER,
                      address TEXT,
                      asset TEXT,
                      quantity INTEGER,
                      action TEXT,
                      event TEXT,
                      FOREIGN KEY (block_index) REFERENCES blocks(block_index))
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      debits_address_idx ON debits (address)
                   ''')

    # (Valid) credits
    cursor.execute('''CREATE TABLE IF NOT EXISTS credits(
                      block_index INTEGER,
                      address TEXT,
                      asset TEXT,
                      quantity INTEGER,
                      calling_function TEXT,
                      event TEXT,
                      FOREIGN KEY (block_index) REFERENCES blocks(block_index))
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      address_idx ON credits (address)
                   ''')

    # Balances
    cursor.execute('''CREATE TABLE IF NOT EXISTS balances(
                      address TEXT,
                      asset TEXT,
                      quantity INTEGER)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      address_asset_idx ON balances (address, asset)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      asset_idx ON balances (asset)
                   ''')

    # Sends
    cursor.execute('''CREATE TABLE IF NOT EXISTS sends(
                      tx_index INTEGER PRIMARY KEY,
                      tx_hash TEXT UNIQUE,
                      block_index INTEGER,
                      source TEXT,
                      destination TEXT,
                      asset TEXT,
                      quantity INTEGER,
                      status TEXT,
                      FOREIGN KEY (tx_index, tx_hash, block_index) REFERENCES transactions(tx_index, tx_hash, block_index))
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      block_index_idx ON sends (block_index)
                   ''')

    # Orders
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders(
                      tx_index INTEGER UNIQUE,
                      tx_hash TEXT UNIQUE,
                      block_index INTEGER,
                      source TEXT,
                      give_asset TEXT,
                      give_quantity INTEGER,
                      give_remaining INTEGER,
                      get_asset TEXT,
                      get_quantity INTEGER,
                      get_remaining INTEGER,
                      expiration INTEGER,
                      expire_index INTEGER,
                      fee_required INTEGER,
                      fee_required_remaining INTEGER,
                      fee_provided INTEGER,
                      fee_provided_remaining INTEGER,
                      status TEXT,
                      FOREIGN KEY (tx_index, tx_hash, block_index) REFERENCES transactions(tx_index, tx_hash, block_index),
                      PRIMARY KEY (tx_index, tx_hash))
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      block_index_idx ON orders (block_index)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      index_hash_idx ON orders (tx_index, tx_hash)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      expire_idx ON orders (status, expire_index)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      give_status_idx ON orders (give_asset, status)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      give_get_status_idx ON orders (give_asset, get_asset, status)
                   ''')

    # Order Matches
    cursor.execute('''CREATE TABLE IF NOT EXISTS order_matches(
                      id TEXT PRIMARY KEY,
                      tx0_index INTEGER,
                      tx0_hash TEXT,
                      tx0_address TEXT,
                      tx1_index INTEGER,
                      tx1_hash TEXT,
                      tx1_address TEXT,
                      forward_asset TEXT,
                      forward_quantity INTEGER,
                      backward_asset TEXT,
                      backward_quantity INTEGER,
                      tx0_block_index INTEGER,
                      tx1_block_index INTEGER,
                      tx0_expiration INTEGER,
                      tx1_expiration INTEGER,
                      match_expire_index INTEGER,
                      fee_paid INTEGER,
                      status TEXT,
                      FOREIGN KEY (tx0_index, tx0_hash, tx0_block_index) REFERENCES transactions(tx_index, tx_hash, block_index),
                      FOREIGN KEY (tx1_index, tx1_hash, tx1_block_index) REFERENCES transactions(tx_index, tx_hash, block_index))
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      match_expire_idx ON order_matches (status, match_expire_index)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      forward_status_idx ON order_matches (forward_asset, status)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      backward_status_idx ON order_matches (backward_asset, status)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      id_idx ON order_matches (id)
                   ''')

    # BTCpays
    cursor.execute('''CREATE TABLE IF NOT EXISTS btcpays(
                      tx_index INTEGER PRIMARY KEY,
                      tx_hash TEXT UNIQUE,
                      block_index INTEGER,
                      source TEXT,
                      destination TEXT,
                      btc_amount INTEGER,
                      order_match_id TEXT,
                      status TEXT,
                      FOREIGN KEY (tx_index, tx_hash, block_index) REFERENCES transactions(tx_index, tx_hash, block_index))
                   ''')
                      # Disallows invalids: FOREIGN KEY (order_match_id) REFERENCES order_matches(id))
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      block_index_idx ON btcpays (block_index)
                   ''')

    # Issuances
    cursor.execute('''CREATE TABLE IF NOT EXISTS issuances(
                      tx_index INTEGER PRIMARY KEY,
                      tx_hash TEXT UNIQUE,
                      block_index INTEGER,
                      asset TEXT,
                      quantity INTEGER,
                      divisible BOOL,
                      source TEXT,
                      issuer TEXT,
                      transfer BOOL,
                      callable BOOL,
                      call_date INTEGER,
                      call_price REAL,
                      description TEXT,
                      fee_paid INTEGER,
                      locked BOOL,
                      status TEXT,
                      FOREIGN KEY (tx_index, tx_hash, block_index) REFERENCES transactions(tx_index, tx_hash, block_index))
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      block_index_idx ON issuances (block_index)
                    ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      valid_asset_idx ON issuances (status, asset)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      status_idx ON issuances (status)
                   ''')

    # Broadcasts
    cursor.execute('''CREATE TABLE IF NOT EXISTS broadcasts(
                      tx_index INTEGER PRIMARY KEY,
                      tx_hash TEXT UNIQUE,
                      block_index INTEGER,
                      source TEXT,
                      timestamp INTEGER,
                      value REAL,
                      fee_fraction_int INTEGER,
                      text TEXT,
                      locked BOOL,
                      status TEXT,
                      FOREIGN KEY (tx_index, tx_hash, block_index) REFERENCES transactions(tx_index, tx_hash, block_index))
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      block_index_idx ON broadcasts (block_index)
                   ''')

    # Bets.
    cursor.execute('''CREATE TABLE IF NOT EXISTS bets(
                      tx_index INTEGER UNIQUE,
                      tx_hash TEXT UNIQUE,
                      block_index INTEGER,
                      source TEXT,
                      feed_address TEXT,
                      bet_type INTEGER,
                      deadline INTEGER,
                      wager_quantity INTEGER,
                      wager_remaining INTEGER,
                      counterwager_quantity INTEGER,
                      counterwager_remaining INTEGER,
                      target_value REAL,
                      leverage INTEGER,
                      expiration INTEGER,
                      expire_index INTEGER,
                      fee_fraction_int INTEGER,
                      status TEXT,
                      FOREIGN KEY (tx_index, tx_hash, block_index) REFERENCES transactions(tx_index, tx_hash, block_index),
                      PRIMARY KEY (tx_index, tx_hash))
                  ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      block_index_idx ON bets (block_index)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      index_hash_idx ON bets (tx_index, tx_hash)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      expire_idx ON bets (status, expire_index)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      feed_valid_bettype_idx ON bets (feed_address, status, bet_type)
                   ''')

    # Bet Matches
    cursor.execute('''CREATE TABLE IF NOT EXISTS bet_matches(
                      id TEXT PRIMARY KEY,
                      tx0_index INTEGER,
                      tx0_hash TEXT,
                      tx0_address TEXT,
                      tx1_index INTEGER,
                      tx1_hash TEXT,
                      tx1_address TEXT,
                      tx0_bet_type INTEGER,
                      tx1_bet_type INTEGER,
                      feed_address TEXT,
                      initial_value INTEGER,
                      deadline INTEGER,
                      target_value REAL,
                      leverage INTEGER,
                      forward_quantity INTEGER,
                      backward_quantity INTEGER,
                      tx0_block_index INTEGER,
                      tx1_block_index INTEGER,
                      tx0_expiration INTEGER,
                      tx1_expiration INTEGER,
                      match_expire_index INTEGER,
                      fee_fraction_int INTEGER,
                      status TEXT,
                      FOREIGN KEY (tx0_index, tx0_hash, tx0_block_index) REFERENCES transactions(tx_index, tx_hash, block_index),
                      FOREIGN KEY (tx1_index, tx1_hash, tx1_block_index) REFERENCES transactions(tx_index, tx_hash, block_index))
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      match_expire_idx ON bet_matches (status, match_expire_index)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      valid_feed_idx ON bet_matches (status, feed_address)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      id_idx ON bet_matches (id)
                   ''')

    # Dividends
    cursor.execute('''CREATE TABLE IF NOT EXISTS dividends(
                      tx_index INTEGER PRIMARY KEY,
                      tx_hash TEXT UNIQUE,
                      block_index INTEGER,
                      source TEXT,
                      asset TEXT,
                      dividend_asset TEXT,
                      quantity_per_unit INTEGER,
                      status TEXT,
                      FOREIGN KEY (tx_index, tx_hash, block_index) REFERENCES transactions(tx_index, tx_hash, block_index))
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      block_index_idx ON dividends (block_index)
                   ''')

    # Burns
    cursor.execute('''CREATE TABLE IF NOT EXISTS burns(
                      tx_index INTEGER PRIMARY KEY,
                      tx_hash TEXT UNIQUE,
                      block_index INTEGER,
                      source TEXT,
                      burned INTEGER,
                      earned INTEGER,
                      status TEXT,
                      FOREIGN KEY (tx_index, tx_hash, block_index) REFERENCES transactions(tx_index, tx_hash, block_index))
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      status_idx ON burns (status)
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      address_idx ON burns (source)
                   ''')

    # Cancels
    cursor.execute('''CREATE TABLE IF NOT EXISTS cancels(
                      tx_index INTEGER PRIMARY KEY,
                      tx_hash TEXT UNIQUE,
                      block_index INTEGER,
                      source TEXT,
                      offer_hash TEXT,
                      status TEXT,
                      FOREIGN KEY (tx_index, tx_hash, block_index) REFERENCES transactions(tx_index, tx_hash, block_index))
                   ''')
                      # Offer hash is not a foreign key. (And it cannot be, because of some invalid cancels.)
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      cancels_block_index_idx ON cancels (block_index)
                   ''')

    # Callbacks
    cursor.execute('''CREATE TABLE IF NOT EXISTS callbacks(
                      tx_index INTEGER PRIMARY KEY,
                      tx_hash TEXT UNIQUE,
                      block_index INTEGER,
                      source TEXT,
                      fraction TEXT,
                      asset TEXT,
                      status TEXT,
                      FOREIGN KEY (tx_index, tx_hash, block_index) REFERENCES transactions(tx_index, tx_hash, block_index))
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      block_index_idx ON callbacks (block_index)
                   ''')

    # Order Expirations
    cursor.execute('''CREATE TABLE IF NOT EXISTS order_expirations(
                      order_index INTEGER PRIMARY KEY,
                      order_hash TEXT UNIQUE,
                      source TEXT,
                      block_index INTEGER,
                      FOREIGN KEY (block_index) REFERENCES blocks(block_index),
                      FOREIGN KEY (order_index, order_hash) REFERENCES orders(tx_index, tx_hash))
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      block_index_idx ON order_expirations (block_index)
                   ''')

    # Bet Expirations
    cursor.execute('''CREATE TABLE IF NOT EXISTS bet_expirations(
                      bet_index INTEGER PRIMARY KEY,
                      bet_hash TEXT UNIQUE,
                      source TEXT,
                      block_index INTEGER,
                      FOREIGN KEY (block_index) REFERENCES blocks(block_index),
                      FOREIGN KEY (bet_index, bet_hash) REFERENCES bets(tx_index, tx_hash))
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      block_index_idx ON bet_expirations (block_index)
                   ''')

    # Order Match Expirations
    cursor.execute('''CREATE TABLE IF NOT EXISTS order_match_expirations(
                      order_match_id TEXT PRIMARY KEY,
                      tx0_address TEXT,
                      tx1_address TEXT,
                      block_index INTEGER,
                      FOREIGN KEY (order_match_id) REFERENCES order_matches(id),
                      FOREIGN KEY (block_index) REFERENCES blocks(block_index))
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      block_index_idx ON order_match_expirations (block_index)
                   ''')

    # Bet Match Expirations
    cursor.execute('''CREATE TABLE IF NOT EXISTS bet_match_expirations(
                      bet_match_id TEXT PRIMARY KEY,
                      tx0_address TEXT,
                      tx1_address TEXT,
                      block_index INTEGER,
                      FOREIGN KEY (bet_match_id) REFERENCES bet_matches(id),
                      FOREIGN KEY (block_index) REFERENCES blocks(block_index))
                   ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      block_index_idx ON bet_match_expirations (block_index)
                   ''')

    # Messages
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages(
                      message_index INTEGER PRIMARY KEY,
                      block_index INTEGER,
                      command TEXT,
                      category TEXT,
                      bindings TEXT)
                  ''')
                      # TODO: FOREIGN KEY (block_index) REFERENCES blocks(block_index) DEFERRABLE INITIALLY DEFERRED)
    cursor.execute('''CREATE INDEX IF NOT EXISTS
                      block_index_idx ON messages (block_index)
                   ''')

    cursor.close()

def get_pubkeyhash (scriptpubkey):
    asm = scriptpubkey['asm'].split(' ')
    if len(asm) != 5 or asm[0] != 'OP_DUP' or asm[1] != 'OP_HASH160' or asm[3] != 'OP_EQUALVERIFY' or asm[4] != 'OP_CHECKSIG':
        return False
    return asm[2]

def get_address (scriptpubkey):
    pubkeyhash = get_pubkeyhash(scriptpubkey)
    if not pubkeyhash: return False

    address = bitcoin.base58_check_encode(pubkeyhash, config.ADDRESSVERSION)

    # Test decoding of address.
    if address != config.UNSPENDABLE and binascii.unhexlify(bytes(pubkeyhash, 'utf-8')) != bitcoin.base58_decode(address, config.ADDRESSVERSION):
        return False

    return address

def get_tx_info (tx, block_index):
    """
    The destination, if it exists, always comes before the data output; the
    change, if it exists, always comes after.
    """

    # Fee is the input values minus output values.
    fee = 0

    # Get destination output and data output.
    destination, btc_amount, data = None, None, b''
    pubkeyhash_encoding = False
    for vout in tx['vout']:
        fee -= vout['value'] * config.UNIT

        # Sum data chunks to get data. (Can mix OP_RETURN and multi-sig.)
        asm = vout['scriptPubKey']['asm'].split(' ')
        if len(asm) == 2 and asm[0] == 'OP_RETURN':                                                 # OP_RETURN
            try: data_chunk = binascii.unhexlify(bytes(asm[1], 'utf-8'))
            except binascii.Error: continue
            data += data_chunk
        elif len(asm) == 5 and asm[0] == '1' and asm[3] == '2' and asm[4] == 'OP_CHECKMULTISIG':    # Multi-sig
            try: data_pubkey = binascii.unhexlify(bytes(asm[2], 'utf-8'))
            except binascii.Error: continue
            data_chunk_length = data_pubkey[0]  # No ord() necessary.
            data_chunk = data_pubkey[1:data_chunk_length + 1]
            data += data_chunk
        elif len(asm) == 5 and (block_index >= 293000 or config.TESTNET):    # Protocol change.
            # Be strict.
            pubkeyhash_string = get_pubkeyhash(vout['scriptPubKey'])
            try: pubkeyhash = binascii.unhexlify(bytes(pubkeyhash_string, 'utf-8'))
            except binascii.Error: continue

            if 'coinbase' in tx['vin'][0]: return b'', None, None, None, None
            obj1 = ARC4.new(binascii.unhexlify(bytes(tx['vin'][0]['txid'], 'utf-8')))
            data_pubkey = obj1.decrypt(pubkeyhash)
            if data_pubkey[1:9] == config.PREFIX or pubkeyhash_encoding:
                pubkeyhash_encoding = True
                data_chunk_length = data_pubkey[0]  # No ord() necessary.
                data_chunk = data_pubkey[1:data_chunk_length + 1]
                if data_chunk[-8:] == config.PREFIX:
                    data += data_chunk[:-8]
                    break
                else:
                    data += data_chunk

        # Destination is the first output before the data.
        if not destination and not btc_amount and not data:
            address = get_address(vout['scriptPubKey'])
            if address:
                destination = address
                btc_amount = round(vout['value'] * config.UNIT) # Floats are awful.

    # Check for, and strip away, prefix (except for burns).
    if destination == config.UNSPENDABLE:
        pass
    elif data[:len(config.PREFIX)] == config.PREFIX:
        data = data[len(config.PREFIX):]
    else:
        return b'', None, None, None, None

    # Only look for source if data were found or destination is UNSPENDABLE, for speed.
    if not data and destination != config.UNSPENDABLE:
        return b'', None, None, None, None

    # Collect all possible source addresses; ignore coinbase transactions and anything but the simplest Pay‐to‐PubkeyHash inputs.
    source_list = []
    for vin in tx['vin']:                                               # Loop through input transactions.
        if 'coinbase' in vin: return b'', None, None, None, None
        vin_tx = bitcoin.get_raw_transaction(vin['txid'])     # Get the full transaction data for this input transaction.
        vout = vin_tx['vout'][vin['vout']]
        fee += vout['value'] * config.UNIT

        address = get_address(vout['scriptPubKey'])
        if not address: return b'', None, None, None, None
        else: source_list.append(address)

    # Require that all possible source addresses be the same.
    if all(x == source_list[0] for x in source_list): source = source_list[0]
    else: source = None

    return source, destination, btc_amount, round(fee), data

def reparse (db, block_index=None, quiet=False):
    """Reparse all transactions (atomically). If block_index is set, rollback
    to the end of that block.
    """
    # TODO: This is not thread-safe!
    logging.warning('Status: Reparsing all transactions.')
    cursor = db.cursor()

    with db:

        # Delete all of the results of parsing.
        cursor.execute('''DROP TABLE IF EXISTS order_expirations''')
        cursor.execute('''DROP TABLE IF EXISTS bet_expirations''')
        cursor.execute('''DROP TABLE IF EXISTS order_match_expirations''')
        cursor.execute('''DROP TABLE IF EXISTS bet_match_expirations''')
        cursor.execute('''DROP TABLE IF EXISTS debits''')
        cursor.execute('''DROP TABLE IF EXISTS credits''')
        cursor.execute('''DROP TABLE IF EXISTS balances''')
        cursor.execute('''DROP TABLE IF EXISTS sends''')
        cursor.execute('''DROP TABLE IF EXISTS orders''')
        cursor.execute('''DROP TABLE IF EXISTS order_matches''')
        cursor.execute('''DROP TABLE IF EXISTS btcpays''')
        cursor.execute('''DROP TABLE IF EXISTS issuances''')
        cursor.execute('''DROP TABLE IF EXISTS broadcasts''')
        cursor.execute('''DROP TABLE IF EXISTS bets''')
        cursor.execute('''DROP TABLE IF EXISTS bet_matches''')
        cursor.execute('''DROP TABLE IF EXISTS dividends''')
        cursor.execute('''DROP TABLE IF EXISTS burns''')
        cursor.execute('''DROP TABLE IF EXISTS cancels''')
        cursor.execute('''DROP TABLE IF EXISTS callbacks''')
        cursor.execute('''DROP TABLE IF EXISTS messages''')

        # For rollbacks, just delete new blocks and then reparse what’s left.
        if block_index:
            cursor.execute('''DELETE FROM transactions WHERE block_index > ?''', (block_index,))
            cursor.execute('''DELETE FROM blocks WHERE block_index > ?''', (block_index,))

        # Reparse all blocks, transactions.
        if quiet:
            log = logging.getLogger('')
            log.setLevel(logging.WARNING)
        initialise(db)
        cursor.execute('''SELECT * FROM blocks ORDER BY block_index''')
        for block in cursor.fetchall():
            logging.info('Block (re-parse): {}'.format(str(block['block_index'])))
            parse_block(db, block['block_index'], block['block_time'])
        if quiet:
            log.setLevel(logging.INFO)

        # Check for conservation of assets.
        check_conservation(db)

        # Update minor version number.
        minor_version = cursor.execute('PRAGMA user_version = {}'.format(int(config.VERSION_MINOR))) # Syntax?!
        logging.info('Status: Database minor version number updated.')

    cursor.close()
    return


def follow (db):
    # TODO: This is not thread-safe!
    follow_cursor = db.cursor()

    logging.info('Status: RESTART')

    # Initialise.
    initialise(db)

    # Get index of last block.
    try:
        block_index = util.last_block(db)['block_index'] + 1

        # Reparse all transactions if minor version has changed.
        minor_version = follow_cursor.execute('PRAGMA user_version').fetchall()[0]['user_version']
        if minor_version != config.VERSION_MINOR:
            logging.info('Status: client minor version number mismatch ({} ≠ {}).'.format(minor_version, config.VERSION_MINOR))
            reparse(db, quiet=False)

    except exceptions.DatabaseError:
        logging.warning('Status: NEW DATABASE')
        block_index = config.BLOCK_FIRST

    # Get index of last transaction.
    txes = list(follow_cursor.execute('''SELECT * FROM transactions WHERE tx_index = (SELECT MAX(tx_index) from transactions)'''))
    if txes:
        assert len(txes) == 1
        tx_index = txes[0]['tx_index'] + 1
    else:
        tx_index = 0

    while True:

        # Get new blocks.
        if block_index <= bitcoin.get_block_count():
            logging.info('Block: {}'.format(str(block_index)))

            # Backwards check for incorrect blocks due to chain reorganisation, and stop when a common parent is found.
            c = block_index
            requires_rollback = False
            while True:
                if c == config.BLOCK_FIRST: break

                # Bitcoind parent hash.
                c_hash = bitcoin.get_block_hash(c)
                c_block = bitcoin.get_block(c_hash)
                bitcoind_parent = c_block['previousblockhash']

                # DB parent hash.
                blocks = list(follow_cursor.execute('''SELECT * FROM blocks
                                                       WHERE block_index = ?''', (c - 1,)))
                if len(blocks) != 1: break  # For empty DB.
                db_parent = blocks[0]['block_hash']

                # Compare.
                if db_parent == bitcoind_parent:
                    break
                else:
                    c -= 1
                    requires_rollback = True

            # Rollback for reorganisation.
            if requires_rollback:
                # Record reorganisation.
                logging.warning('Status: Blockchain reorganisation at block {}.'.format(c))
                util.message(db, block_index, 'reorg', None, {'block_index': c})

                # Rollback the DB.
                reparse(db, block_index=c-1, quiet=True)
                block_index = c
                continue

            # Get and parse transactions in this block (atomically).
            block_hash = bitcoin.get_block_hash(block_index)
            block = bitcoin.get_block(block_hash)
            block_time = block['time']
            tx_hash_list = block['tx']
            with db:
                # List the block.
                follow_cursor.execute('''INSERT INTO blocks(
                                    block_index,
                                    block_hash,
                                    block_time) VALUES(?,?,?)''',
                                    (block_index,
                                    block_hash,
                                    block_time)
                              )

                # List the transactions in the block.
                for tx_hash in tx_hash_list:
                    # Skip duplicate transaction entries.
                    follow_cursor.execute('''SELECT * FROM transactions WHERE tx_hash=?''', (tx_hash,))
                    blocks = follow_cursor.fetchall()
                    if blocks:
                        tx_index += 1
                        continue
                    # Get the important details about each transaction.
                    tx = bitcoin.get_raw_transaction(tx_hash)
                    logging.debug('Status: examining transaction {}'.format(tx_hash))
                    source, destination, btc_amount, fee, data = get_tx_info(tx, block_index)
                    if source and (data or destination == config.UNSPENDABLE):
                        follow_cursor.execute('''INSERT INTO transactions(
                                            tx_index,
                                            tx_hash,
                                            block_index,
                                            block_hash,
                                            block_time,
                                            source,
                                            destination,
                                            btc_amount,
                                            fee,
                                            data) VALUES(?,?,?,?,?,?,?,?,?,?)''',
                                            (tx_index,
                                             tx_hash,
                                             block_index,
                                             block_hash,
                                             block_time,
                                             source,
                                             destination,
                                             btc_amount,
                                             fee,
                                             data)
                                      )
                        tx_index += 1

                # Parse the transactions in the block.
                parse_block(db, block_index, block_time)

            # Increment block index.
            block_count = bitcoin.get_block_count()
            block_index +=1

        else:
            # Check for conservation of assets.
            check_conservation(db)
            time.sleep(2)

    follow_cursor.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

########NEW FILE########
__FILENAME__ = broadcast
#! /usr/bin/python3

"""
Broadcast a message, with or without a price.

Multiple messages per block are allowed. Bets are be made on the 'timestamp'
field, and not the block index.

An address is a feed of broadcasts. Feeds may be locked with a broadcast whose
text field is identical to ‘lock’ (case insensitive). Bets on a feed reference
the address that is the source of the feed in an output which includes the
(latest) required fee.

Broadcasts without a price may not be used for betting. Broadcasts about events
with a small number of possible outcomes (e.g. sports games), should be
written, for example, such that a price of 1 XCP means one outcome, 2 XCP means
another, etc., which schema should be described in the 'text' field.

fee_fraction: .05 XCP means 5%. It may be greater than 1, however; but
because it is stored as a four‐byte integer, it may not be greater than about
42.
"""

import struct
import decimal
D = decimal.Decimal
from fractions import Fraction
import logging

from . import (util, exceptions, config, bitcoin)
from . import (bet)

FORMAT = '>IdI52p'
LENGTH = 4 + 8 + 4 + 52
ID = 30


def validate (db, source, timestamp, value, fee_fraction_int, text):
    problems = []

    if fee_fraction_int > 4294967295:
        problems.append('fee fraction greater than 42.94967295')

    if timestamp < 0: problems.append('negative timestamp')

    if not source:
        problems.append('null source address')
    # Check previous broadcast in this feed.
    broadcasts = util.get_broadcasts(db, status='valid', source=source, order_by='tx_index', order_dir='asc')
    if broadcasts:
        last_broadcast = broadcasts[-1]
        if last_broadcast['locked']:
            problems.append('locked feed')
        elif timestamp <= last_broadcast['timestamp']:
            problems.append('feed timestamps not monotonically increasing')

    return problems

def compose (db, source, timestamp, value, fee_fraction, text):

    # Store the fee fraction as an integer.
    fee_fraction_int = int(fee_fraction * 1e8)

    problems = validate(db, source, timestamp, value, fee_fraction_int, text)
    if problems: raise exceptions.BroadcastError(problems)

    data = config.PREFIX + struct.pack(config.TXTYPE_FORMAT, ID)
    data += struct.pack(FORMAT, timestamp, value, fee_fraction_int,
                        text.encode('utf-8'))
    if len(data) > 80:
        raise exceptions.BroadcastError('Text is greater than 52 bytes.')
    return (source, [], data)

def parse (db, tx, message):
    cursor = db.cursor()

    # Unpack message.
    try:
        assert len(message) == LENGTH
        timestamp, value, fee_fraction_int, text = struct.unpack(FORMAT, message)
        text = text.decode('utf-8')
        status = 'valid'
    except (AssertionError, struct.error) as e:
        timestamp, value, fee_fraction_int, text = None, None, None, None
        status = 'invalid: could not unpack'

    if status == 'valid':
        # For SQLite3
        timestamp = min(timestamp, config.MAX_INT)
        value = min(value, config.MAX_INT)

        problems = validate(db, tx['source'], timestamp, value, fee_fraction_int, text)
        if problems: status = 'invalid: ' + '; '.join(problems)

    # Lock?
    lock = False
    if text and text.lower() == 'lock':
        lock = True
        timestamp, value, fee_fraction_int, text = None, None, None, None
    else:
        lock = False

    # Add parsed transaction to message-type–specific table.
    bindings = {
        'tx_index': tx['tx_index'],
        'tx_hash': tx['tx_hash'],
        'block_index': tx['block_index'],
        'source': tx['source'],
        'timestamp': timestamp,
        'value': value,
        'fee_fraction_int': fee_fraction_int,
        'text': text,
        'locked': lock,
        'status': status,
    }
    sql='insert into broadcasts values(:tx_index, :tx_hash, :block_index, :source, :timestamp, :value, :fee_fraction_int, :text, :locked, :status)'
    cursor.execute(sql, bindings)

    # Negative values (default to ignore).
    if value < 0 or value == None:
        # Cancel Open Bets?
        if value == -2:
            cursor.execute('''SELECT * FROM bet \
                              WHERE (status = ? AND feed_address = ?)''',
                           ('open', tx['source']))
            for bet in list(cursor):
                bet.cancel_bet(db, bet, 'dropped', tx['block_index'])
        # Cancel Pending Bet Matches?
        if value == -3:
            cursor.execute('''SELECT * FROM bet_matches \
                              WHERE (status = ? AND feed_address = ?)''',
                           ('pending', tx['source']))
            for bet_match in list(cursor):
                bet.cancel_bet_match(db, bet_match, 'dropped', tx['block_index'])
        cursor.close()
        return

    # Handle bet matches that use this feed.
    cursor.execute('''SELECT * FROM bet_matches \
                      WHERE (status=? AND feed_address=?)
                      ORDER BY tx1_index ASC, tx0_index ASC''',
                   ('pending', tx['source']))
    for bet_match in cursor.fetchall():
        broadcast_bet_match_cursor = db.cursor()
        bet_match_id = bet_match['tx0_hash'] + bet_match['tx1_hash']
        bet_match_status = None

        # Calculate total funds held in escrow and total fee to be paid if
        # the bet match is settled. Escrow less fee is amount to be paid back
        # to betters.
        total_escrow = bet_match['forward_quantity'] + bet_match['backward_quantity']
        fee_fraction = fee_fraction_int / config.UNIT
        fee = int(fee_fraction * total_escrow)              # Truncate.
        escrow_less_fee = total_escrow - fee

        # Get known bet match type IDs.
        cfd_type_id = util.BET_TYPE_ID['BullCFD'] + util.BET_TYPE_ID['BearCFD']
        equal_type_id = util.BET_TYPE_ID['Equal'] + util.BET_TYPE_ID['NotEqual']

        # Get the bet match type ID of this bet match.
        bet_match_type_id = bet_match['tx0_bet_type'] + bet_match['tx1_bet_type']

        # Contract for difference, with determinate settlement date.
        if bet_match_type_id == cfd_type_id:

            # Recognise tx0, tx1 as the bull, bear (in the right direction).
            if bet_match['tx0_bet_type'] < bet_match['tx1_bet_type']:
                bull_address = bet_match['tx0_address']
                bear_address = bet_match['tx1_address']
                bull_escrow = bet_match['forward_quantity']
                bear_escrow = bet_match['backward_quantity']
            else:
                bull_address = bet_match['tx1_address']
                bear_address = bet_match['tx0_address']
                bull_escrow = bet_match['backward_quantity']
                bear_escrow = bet_match['forward_quantity']

            leverage = Fraction(bet_match['leverage'], 5040)
            initial_value = bet_match['initial_value']

            bear_credit = bear_escrow - (value - initial_value) * leverage * config.UNIT
            bull_credit = escrow_less_fee - bear_credit
            bear_credit = round(bear_credit)
            bull_credit = round(bull_credit)

            # Liquidate, as necessary.
            if bull_credit >= escrow_less_fee or bull_credit <= 0:
                if bull_credit >= escrow_less_fee:
                    bull_credit = escrow_less_fee
                    bear_credit = 0
                    util.credit(db, tx['block_index'], bull_address, 'XCP', bull_credit)
                    bet_match_status = 'settled: liquidated for bear'
                elif bull_credit <= 0:
                    bull_credit = 0
                    bear_credit = escrow_less_fee
                    util.credit(db, tx['block_index'], bear_address, 'XCP', bear_credit)
                    bet_match_status = 'settled: liquidated for bull'

                # Pay fee to feed.
                util.credit(db, tx['block_index'], bet_match['feed_address'], 'XCP', fee)

                logging.info('Contract Force‐Liquidated: {} XCP credited to the bull, {} XCP credited to the bear, and {} XCP credited to the feed address ({})'.format(util.devise(db, bull_credit, 'XCP', 'output'), util.devise(db, bear_credit, 'XCP', 'output'), util.devise(db, fee, 'XCP', 'output'), bet_match_id))

            # Settle (if not liquidated).
            elif timestamp >= bet_match['deadline']:
                bet_match_status = 'settled'

                util.credit(db, tx['block_index'], bull_address, 'XCP', bull_credit)
                util.credit(db, tx['block_index'], bear_address, 'XCP', bear_credit)

                # Pay fee to feed.
                util.credit(db, tx['block_index'], bet_match['feed_address'], 'XCP', fee)

                logging.info('Contract Settled: {} XCP credited to the bull, {} XCP credited to the bear, and {} XCP credited to the feed address ({})'.format(util.devise(db, bull_credit, 'XCP', 'output'), util.devise(db, bear_credit, 'XCP', 'output'), util.devise(db, fee, 'XCP', 'output'), bet_match_id))

        # Equal[/NotEqual] bet.
        elif bet_match_type_id == equal_type_id and timestamp >= bet_match['deadline']:

            # Recognise tx0, tx1 as the bull, bear (in the right direction).
            if bet_match['tx0_bet_type'] < bet_match['tx1_bet_type']:
                equal_address = bet_match['tx0_address']
                notequal_address = bet_match['tx1_address']
            else:
                equal_address = bet_match['tx1_address']
                notequal_address = bet_match['tx0_address']

            # Decide who won, and credit appropriately.
            if value == bet_match['target_value']:
                winner = 'Equal'
                util.credit(db, tx['block_index'], equal_address, 'XCP', escrow_less_fee)
                bet_match_status = 'settled: for equal'
            else:
                winner = 'NotEqual'
                util.credit(db, tx['block_index'], notequal_address, 'XCP', escrow_less_fee)
                bet_match_status = 'settled: for notequal'

            # Pay fee to feed.
            util.credit(db, tx['block_index'], bet_match['feed_address'], 'XCP', fee)

            logging.info('Contract Settled: {} won the pot of {} XCP; {} XCP credited to the feed address ({})'.format(winner, util.devise(db, escrow_less_fee, 'XCP', 'output'), util.devise(db, fee, 'XCP', 'output'), bet_match_id))

        # Update the bet match’s status.
        if bet_match_status:
            bindings = {
                'status': bet_match_status,
                'bet_match_id': bet_match['tx0_hash'] + bet_match['tx1_hash']
            }
            sql='update bet_matches set status = :status where id = :bet_match_id'
            cursor.execute(sql, bindings)
            util.message(db, tx['block_index'], 'update', 'bet_matches', bindings)

        broadcast_bet_match_cursor.close()

    cursor.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

########NEW FILE########
__FILENAME__ = btcpay
#! /usr/bin/python3

import binascii
import struct

from . import (util, config, exceptions, bitcoin, util)

FORMAT = '>32s32s'
LENGTH = 32 + 32
ID = 11


def validate (db, source, order_match_id):
    problems = []
    order_match = None

    cursor = db.cursor()
    cursor.execute('''SELECT * FROM order_matches \
                      WHERE id = ?''', (order_match_id,))
    order_matches = cursor.fetchall()
    cursor.close()
    if len(order_matches) == 0:
        problems.append('no such order match')
        return None, None, None, None, order_match, problems
    elif len(order_matches) > 1:
        assert False
    else:
        order_match = order_matches[0]

        if order_match['status'] == 'expired':
            problems.append('order match expired')
        elif order_match['status'] == 'completed':
            problems.append('order match completed')
        elif order_match['status'].startswith('invalid'):
            problems.append('order match invalid')
        elif order_match['status'] != 'pending':
            raise exceptions.OrderError('unrecognised order match status')

    # Figure out to which address the BTC are being paid.
    # Check that source address is correct.
    if order_match['backward_asset'] == 'BTC':
        if source != order_match['tx1_address']:
            problems.append('incorrect source address')
        destination = order_match['tx0_address']
        btc_quantity = order_match['backward_quantity']
        escrowed_asset  = order_match['forward_asset']
        escrowed_quantity = order_match['forward_quantity']
    elif order_match['forward_asset'] == 'BTC':
        if source != order_match['tx0_address']:
            problems.append('incorrect source address')
        destination = order_match['tx1_address']
        btc_quantity = order_match['forward_quantity']
        escrowed_asset  = order_match['backward_asset']
        escrowed_quantity = order_match['backward_quantity']
    else:
        assert False

    return destination, btc_quantity, escrowed_asset, escrowed_quantity, order_match, problems

def compose (db, source, order_match_id):
    tx0_hash, tx1_hash = order_match_id[:64], order_match_id[64:] # UTF-8 encoding means that the indices are doubled.

    destination, btc_quantity, escrowed_asset, escrowed_quantity, order_match, problems = validate(db, source, order_match_id)
    if problems: raise exceptions.BTCPayError(problems)

    # Warn if down to the wire.
    time_left = order_match['match_expire_index'] - util.last_block(db)['block_index']
    if time_left < 4:
        print('WARNING: Only {} blocks until that order match expires. The payment might not make into the blockchain in time.'.format(time_left))
    if 10 - time_left < 4:
        print('WARNING: Order match has only {} confirmation(s).'.format(10 - time_left))

    tx0_hash_bytes, tx1_hash_bytes = binascii.unhexlify(bytes(tx0_hash, 'utf-8')), binascii.unhexlify(bytes(tx1_hash, 'utf-8'))
    data = config.PREFIX + struct.pack(config.TXTYPE_FORMAT, ID)
    data += struct.pack(FORMAT, tx0_hash_bytes, tx1_hash_bytes)
    return (source, [(destination, btc_quantity)], data)

def parse (db, tx, message):
    cursor = db.cursor()

    # Unpack message.
    try:
        assert len(message) == LENGTH
        tx0_hash_bytes, tx1_hash_bytes = struct.unpack(FORMAT, message)
        tx0_hash, tx1_hash = binascii.hexlify(tx0_hash_bytes).decode('utf-8'), binascii.hexlify(tx1_hash_bytes).decode('utf-8')
        order_match_id = tx0_hash + tx1_hash
        status = 'valid'
    except (AssertionError, struct.error) as e:
        tx0_hash, tx1_hash = None, None
        status = 'invalid: could not unpack'

    if status == 'valid':
        destination, btc_quantity, escrowed_asset, escrowed_quantity, order_match, problems = validate(db, tx['source'], order_match_id)
        if problems:
            order_match = None
            status = 'invalid: ' + '; '.join(problems)

    if status == 'valid':
        # BTC must be paid all at once.
        if tx['btc_amount'] >= btc_quantity:

            # Credit source address for the currency that he bought with the bitcoins.
            util.credit(db, tx['block_index'], tx['source'], escrowed_asset, escrowed_quantity)
            status = 'valid'

            # Update order match.
            bindings = {
                'status': 'completed',
                'order_match_id': order_match_id
            }
            sql='update order_matches set status = :status where id = :order_match_id'
            cursor.execute(sql, bindings)
            util.message(db, tx['block_index'], 'update', 'order_matches', bindings)

    # Add parsed transaction to message-type–specific table.
    bindings = {
        'tx_index': tx['tx_index'],
        'tx_hash': tx['tx_hash'],
        'block_index': tx['block_index'],
        'source': tx['source'],
        'destination': tx['destination'],
        'btc_amount': tx['btc_amount'],
        'order_match_id': order_match_id,
        'status': status,
    }
    sql='insert into btcpays values(:tx_index, :tx_hash, :block_index, :source, :destination, :btc_amount, :order_match_id, :status)'
    cursor.execute(sql, bindings)


    cursor.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

########NEW FILE########
__FILENAME__ = burn
#! /usr/bin/python3

"""Burn BTC to earn XCP during a special period of time."""

import struct
import decimal
D = decimal.Decimal
from fractions import Fraction

from . import (util, config, exceptions, bitcoin, util)

ID = 60


def validate (db, source, destination, quantity, block_index, overburn=False):
    problems = []

    # Check destination address.
    if destination != config.UNSPENDABLE:
        problems.append('wrong destination address')

    if not isinstance(quantity, int):
        problems.append('quantity must be in satoshis')
        return problems

    if quantity < 0: problems.append('negative quantity')

    # Try to make sure that the burned funds won't go to waste.
    if block_index < config.BURN_START - 1:
        problems.append('too early')
    elif block_index > config.BURN_END:
        problems.append('too late')

    return problems

def compose (db, source, quantity, overburn=False):
    destination = config.UNSPENDABLE
    problems = validate(db, source, destination, quantity, util.last_block(db)['block_index'], overburn=overburn)
    if problems: raise exceptions.BurnError(problems)

    # Check that a maximum of 1 BTC total is burned per address.
    burns = util.get_burns(db, source=source, status='valid')
    already_burned = sum([burn['burned'] for burn in burns])
    if quantity > (1 * config.UNIT - already_burned) and not overburn:
        raise exceptions.BurnError('1 BTC may be burned per address')

    return (source, [(destination, quantity)], None)

def parse (db, tx, message=None):
    burn_parse_cursor = db.cursor()
    status = 'valid'

    if status == 'valid':
        problems = validate(db, tx['source'], tx['destination'], tx['btc_amount'], tx['block_index'], overburn=False)
        if problems: status = 'invalid: ' + '; '.join(problems)

        if tx['btc_amount'] != None:
            sent = tx['btc_amount']
        else:
            sent = 0

    if status == 'valid':
        # Calculate quantity of XCP earned. (Maximum 1 BTC in total, ever.)
        cursor = db.cursor()
        cursor.execute('''SELECT * FROM burns WHERE (status = ? AND source = ?)''', ('valid', tx['source']))
        burns = cursor.fetchall()
        already_burned = sum([burn['burned'] for burn in burns])
        ONE_BTC = 1 * config.UNIT
        max_burn = ONE_BTC - already_burned
        if sent > max_burn: burned = max_burn   # Exceeded maximum burn; earn what you can.
        else: burned = sent

        total_time = config.BURN_END - config.BURN_START
        partial_time = config.BURN_END - tx['block_index']
        multiplier = 1000 * (1 + (.5 * Fraction(partial_time, total_time)))
        earned = round(burned * multiplier)

        # Credit source address with earned XCP.
        util.credit(db, tx['block_index'], tx['source'], 'XCP', earned, event=tx['tx_hash'])
    else:
        burned = 0
        earned = 0

    # Add parsed transaction to message-type–specific table.
    # TODO: store sent in table
    bindings = {
        'tx_index': tx['tx_index'],
        'tx_hash': tx['tx_hash'],
        'block_index': tx['block_index'],
        'source': tx['source'],
        'burned': burned,
        'earned': earned,
        'status': status,
    }
    sql='insert into burns values(:tx_index, :tx_hash, :block_index, :source, :burned, :earned, :status)'
    burn_parse_cursor.execute(sql, bindings)


    burn_parse_cursor.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

########NEW FILE########
__FILENAME__ = callback
#! /usr/bin/python3

"""Callback a callable asset."""

import struct
import decimal
D = decimal.Decimal

from . import (util, config, exceptions, bitcoin, util)
from . import order

FORMAT = '>dQ'
LENGTH = 8 + 8
ID = 21


def validate (db, source, fraction, asset, block_time, block_index, parse):
    problems = []

    # TODO
    if not config.TESTNET: 
        problems.append('callbacks are currently disabled on mainnet')
        return None, None, None, problems
    # TODO

    if fraction > 1:
        problems.append('fraction greater than one')
    elif fraction <= 0:
        problems.append('non‐positive fraction')

    issuances = util.get_issuances(db, status='valid', asset=asset)
    if not issuances:
        problems.append('no such asset, {}.'.format(asset))
        return None, None, None, problems
    else:
        last_issuance = issuances[-1]

        if last_issuance['issuer'] != source:
            problems.append('not asset owner')
            return None, None, None, problems

        if not last_issuance['callable']:
            problems.append('uncallable asset')
            return None, None, None, problems
        elif last_issuance['call_date'] > block_time: problems.append('before call date')

        call_price = round(last_issuance['call_price'], 6)  # TODO: arbitrary
        divisible = last_issuance['divisible']

    if not divisible:   # Pay per output unit.
        call_price *= config.UNIT

    # If parsing, unescrow all funds of asset. (Order of operations is
    # important here.)
    if parse:
        cursor = db.cursor()

        # Cancel pending order matches involving asset.
        cursor.execute('''SELECT * from order_matches \
                          WHERE status = ? AND (forward_asset = ? OR backward_asset = ?)''', ('pending', asset, asset))
        for order_match in list(cursor):
            order.cancel_order_match(db, order_match, 'cancelled', block_index)

        # Cancel open orders involving asset.
        cursor.execute('''SELECT * from orders \
                          WHERE status = ? AND (give_asset = ? OR get_asset = ?)''', ('open', asset, asset))
        for order_element in list(cursor):
            order.cancel_order(db, order_element, 'cancelled', block_index)

        cursor.close()

    # Calculate callback quantities.
    holders = util.get_holders(db, asset)
    outputs = []
    for holder in holders:

        # If composing (and not parsing), predict funds to be returned from
        # escrow (instead of cancelling open offers, etc.), by *not* skipping
        # listing escrowed funds here.
        if parse and holder['escrow']:
            continue

        address = holder['address']
        address_quantity = holder['address_quantity']
        if address == source or address_quantity == 0: continue

        callback_quantity = int(address_quantity * fraction)   # Round down.
        fraction_actual = callback_quantity / address_quantity

        outputs.append({'address': address, 'address_quantity': address_quantity, 'callback_quantity': callback_quantity, 'fraction_actual': fraction_actual})

    callback_total = sum([output['callback_quantity'] for output in outputs])
    if not callback_total: problems.append('nothing called back')

    balances = util.get_balances(db, address=source, asset='XCP')
    if not balances or balances[0]['quantity'] < (call_price * callback_total):
        problems.append('insufficient funds')

    return call_price, callback_total, outputs, problems

def compose (db, source, fraction, asset):
    call_price, callback_total, outputs, problems = validate(db, source, fraction, asset, util.last_block(db)['block_time'], util.last_block(db)['block_index'], parse=False)
    if problems: raise exceptions.CallbackError(problems)
    print('Total quantity to be called back:', util.devise(db, callback_total, asset, 'output'), asset)

    asset_id = util.get_asset_id(asset)
    data = config.PREFIX + struct.pack(config.TXTYPE_FORMAT, ID)
    data += struct.pack(FORMAT, fraction, asset_id)
    return (source, [], data)

def parse (db, tx, message):
    callback_parse_cursor = db.cursor()

    # Unpack message.
    try:
        assert len(message) == LENGTH
        fraction, asset_id = struct.unpack(FORMAT, message)
        asset = util.get_asset_name(asset_id)
        status = 'valid'
    except (AssertionError, struct.error) as e:
        fraction, asset = None, None
        status = 'invalid: could not unpack'

    if status == 'valid':
        call_price, callback_total, outputs, problems = validate(db, tx['source'], fraction, asset, tx['block_time'], tx['block_index'], parse=True)
        if problems: status = 'invalid: ' + '; '.join(problems)

    if status == 'valid':
        # Issuer.
        assert call_price * callback_total == int(call_price * callback_total)
        util.debit(db, tx['block_index'], tx['source'], 'XCP', int(call_price * callback_total))
        util.credit(db, tx['block_index'], tx['source'], asset, callback_total)

        # Holders.
        for output in outputs:
            assert call_price * output['callback_quantity'] == int(call_price * output['callback_quantity'])
            util.debit(db, tx['block_index'], output['address'], asset, output['callback_quantity'])
            util.credit(db, tx['block_index'], output['address'], 'XCP', int(call_price * output['callback_quantity']))

    # Add parsed transaction to message-type–specific table.
    bindings = {
        'tx_index': tx['tx_index'],
        'tx_hash': tx['tx_hash'],
        'block_index': tx['block_index'],
        'source': tx['source'],
        'fraction': fraction,
        'asset': asset,
        'status': status,
    }
    sql='insert into callbacks values(:tx_index, :tx_hash, :block_index, :source, :fraction, :asset, :status)'
    callback_parse_cursor.execute(sql, bindings)

    callback_parse_cursor.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

########NEW FILE########
__FILENAME__ = cancel
#! /usr/bin/python3

"""
offer_hash is the hash of either a bet or an order.
"""

import binascii
import struct

from . import (util, config, exceptions, bitcoin, util)
from . import (order, bet)

FORMAT = '>32s'
LENGTH = 32
ID = 70

def validate (db, source, offer_hash):
    problems = []

    cursor = db.cursor()
    cursor.execute('''SELECT * from orders WHERE tx_hash = ?''', (offer_hash,))
    orders = list(cursor)
    cursor.execute('''SELECT * from bets WHERE tx_hash = ?''', (offer_hash,))
    bets = list(cursor)
    cursor.close()

    offer_type = None
    if orders: offer_type = 'order'
    elif bets: offer_type = 'bet'
    else: problems = ['no open offer with that hash']

    offer = None
    if offer_type:
        offers = orders + bets
        offer = offers[0]
        if offer['source'] != source:
            problems.append('incorrect source address')
        if offer['status'] != 'open':
            problems.append('offer not open')

    return offer, offer_type, problems

def compose (db, source, offer_hash):

    # Check that offer exists.
    offer, offer_type, problems = validate(db, source, offer_hash)
    if problems: raise exceptions.CancelError(problems)

    offer_hash_bytes = binascii.unhexlify(bytes(offer_hash, 'utf-8'))
    data = config.PREFIX + struct.pack(config.TXTYPE_FORMAT, ID)
    data += struct.pack(FORMAT, offer_hash_bytes)
    return (source, [], data)

def parse (db, tx, message):
    cursor = db.cursor()

    # Unpack message.
    try:
        assert len(message) == LENGTH
        offer_hash_bytes = struct.unpack(FORMAT, message)[0]
        offer_hash = binascii.hexlify(offer_hash_bytes).decode('utf-8')
        status = 'valid'
    except (AssertionError, struct.error) as e:
        offer_hash = None
        status = 'invalid: could not unpack'

    if status == 'valid':
        offer, offer_type, problems = validate(db, tx['source'], offer_hash)
        if problems:
            status = 'invalid: ' + '; '.join(problems)

    if status == 'valid':
        # Cancel if order.
        if offer_type == 'order':
            order.cancel_order(db, offer, 'cancelled', tx['block_index'])
        # Cancel if bet.
        elif offer_type == 'bet':
            bet.cancel_bet(db, offer, 'cancelled', tx['block_index'])
        # If neither order or bet, mark as invalid.
        else:
            assert False

    # Add parsed transaction to message-type–specific table.
    bindings = {
        'tx_index': tx['tx_index'],
        'tx_hash': tx['tx_hash'],
        'block_index': tx['block_index'],
        'source': tx['source'],
        'offer_hash': offer_hash,
        'status': status,
    }
    sql='insert into cancels values(:tx_index, :tx_hash, :block_index, :source, :offer_hash, :status)'
    cursor.execute(sql, bindings)

    cursor.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

########NEW FILE########
__FILENAME__ = config
import sys
import os

UNIT = 100000000        # The same across currencies.

UNITTEST_PREFIX = b'TESTXXXX'

# Versions
VERSION_MAJOR = 9
VERSION_MINOR = 24
VERSION_REVISION = 0
VERSION_STRING = str(VERSION_MAJOR) + '.' + str(VERSION_MINOR) + '.' + str(VERSION_REVISION)

# Bitcoin protocol
# NOTE: If the DUST_SIZE constants are changed, they MUST also be changed in counterblockd/lib/config.py as well
MULTISIG = True
REGULAR_DUST_SIZE = 5430        # TODO: This is just a guess. I got it down to 5530 satoshis.
MULTISIG_DUST_SIZE = 5430 * 2   # TODO: This is just a guess. I did it down to 1.4x. (Used for regular outputs in multi‐sig transactions, too.)
OP_RETURN_VALUE = 0
FEE_PER_KB = 20000              # Bitcoin Core default is 10000.

# Counterparty protocol
TXTYPE_FORMAT = '>I'

TWO_WEEKS = 2 * 7 * 24 * 3600
MAX_EXPIRATION = 4 * 2016   # Two months

# SQLite3
MAX_INT = 2**63 - 1

# Order fees (UI)
FEE_FRACTION_REQUIRED_DEFAULT = .009   # 0.90%
FEE_FRACTION_PROVIDED_DEFAULT = .01    # 1.00%

########NEW FILE########
__FILENAME__ = dividend
#! /usr/bin/python3

"""Pay out dividends."""

import struct
import decimal
D = decimal.Decimal

from . import (util, config, exceptions, bitcoin, util)

FORMAT_1 = '>QQ'
LENGTH_1 = 8 + 8
FORMAT_2 = '>QQQ'
LENGTH_2 = 8 + 8 + 8
ID = 50


def validate (db, source, quantity_per_unit, asset, dividend_asset, block_index):
    problems = []

    if asset in ('BTC', 'XCP'):
        problems.append('cannot pay dividends to holders of BTC or XCP')

    if quantity_per_unit <= 0: problems.append('non‐positive quantity per unit')

    # Examine asset.
    issuances = util.get_issuances(db, status='valid', asset=asset)
    if not issuances:
        problems.append('no such asset, {}.'.format(asset))
        return None, None, problems
    divisible = issuances[0]['divisible']

    # Examine dividend asset.
    if dividend_asset in ('BTC', 'XCP'):
        dividend_divisible = True
    else:
        issuances = util.get_issuances(db, status='valid', asset=dividend_asset)
        if not issuances:
            problems.append('no such dividend asset, {}.'.format(dividend_asset))
            return None, None, problems
        dividend_divisible = issuances[0]['divisible']

    # Calculate dividend quantities.
    holders = util.get_holders(db, asset)
    outputs = []
    for holder in holders:

        if block_index < 294500 and not config.TESTNET: # Protocol change.
            if holder['escrow']: continue
            
        address = holder['address']
        address_quantity = holder['address_quantity']
        if block_index >= 296000 or config.TESTNET: # Protocol change.
            if address == source: continue

        dividend_quantity = address_quantity * quantity_per_unit
        if divisible: dividend_quantity /= config.UNIT
        if not dividend_divisible: dividend_quantity /= config.UNIT
        if dividend_asset == 'BTC' and dividend_quantity < config.MULTISIG_DUST_SIZE: continue    # A bit hackish.
        dividend_quantity = int(dividend_quantity)

        outputs.append({'address': address, 'address_quantity': address_quantity, 'dividend_quantity': dividend_quantity})

    dividend_total = sum([output['dividend_quantity'] for output in outputs])
    if not dividend_total: problems.append('zero dividend')

    if dividend_asset != 'BTC':
        balances = util.get_balances(db, address=source, asset=dividend_asset)
        if not balances or balances[0]['quantity'] < dividend_total:
            problems.append('insufficient funds')

    return dividend_total, outputs, problems

def compose (db, source, quantity_per_unit, asset, dividend_asset):

    dividend_total, outputs, problems = validate(db, source, quantity_per_unit, asset, dividend_asset, util.last_block(db)['block_index'])
    if problems: raise exceptions.DividendError(problems)
    print('Total quantity to be distributed in dividends:', util.devise(db, dividend_total, dividend_asset, 'output'), dividend_asset)

    if dividend_asset == 'BTC':
        return (source, [(output['address'], output['dividend_quantity']) for output in outputs], None)

    asset_id = util.get_asset_id(asset)
    dividend_asset_id = util.get_asset_id(dividend_asset)
    data = config.PREFIX + struct.pack(config.TXTYPE_FORMAT, ID)
    data += struct.pack(FORMAT_2, quantity_per_unit, asset_id, dividend_asset_id)
    return (source, [], data)

def parse (db, tx, message):
    dividend_parse_cursor = db.cursor()

    # Unpack message.
    try:
        if (tx['block_index'] > 288150 or config.TESTNET) and len(message) == LENGTH_2:
            quantity_per_unit, asset_id, dividend_asset_id = struct.unpack(FORMAT_2, message)
            asset = util.get_asset_name(asset_id)
            dividend_asset = util.get_asset_name(dividend_asset_id)
            status = 'valid'
        elif len(message) == LENGTH_1:
            quantity_per_unit, asset_id = struct.unpack(FORMAT_1, message)
            asset = util.get_asset_name(asset_id)
            dividend_asset = 'XCP'
            status = 'valid'
        else:
            raise Exception
    except (AssertionError, struct.error) as e:
        quantity_per_unit, asset = None, None
        status = 'invalid: could not unpack'

    if dividend_asset == 'BTC':
        status = 'invalid: cannot pay BTC dividends within protocol'

    if status == 'valid':
        # For SQLite3
        quantity_per_unit = min(quantity_per_unit, config.MAX_INT)

        dividend_total, outputs, problems = validate(db, tx['source'], quantity_per_unit, asset, dividend_asset, block_index=tx['block_index'])
        if problems: status = 'invalid: ' + '; '.join(problems)

    if status == 'valid':
        # Debit.
        util.debit(db, tx['block_index'], tx['source'], dividend_asset, dividend_total)

        # Credit.
        for output in outputs:
            util.credit(db, tx['block_index'], output['address'], dividend_asset, output['dividend_quantity'])

    # Add parsed transaction to message-type–specific table.
    bindings = {
        'tx_index': tx['tx_index'],
        'tx_hash': tx['tx_hash'],
        'block_index': tx['block_index'],
        'source': tx['source'],
        'asset': asset,
        'dividend_asset': dividend_asset,
        'quantity_per_unit': quantity_per_unit,
        'status': status,
    }
    sql='insert into dividends values(:tx_index, :tx_hash, :block_index, :source, :asset, :dividend_asset, :quantity_per_unit, :status)'
    dividend_parse_cursor.execute(sql, bindings)

    dividend_parse_cursor.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

########NEW FILE########
__FILENAME__ = exceptions
#! /usr/bin/python3

class SanityError (Exception):
    pass

class ConfigurationError (Exception):
    pass
class DatabaseError (Exception):
    pass
class VersionError (Exception):
    pass

class TransactionError(Exception):
    pass
class InputError(Exception):
    pass

class RPCError (Exception):
    pass

class BitcoindError (Exception):
    pass
class BitcoindRPCError (BitcoindError):
    pass
class InsightError (Exception):
    pass

class FeeError (Exception):
    pass
class BalanceError (Exception):
    pass
class QuantityError(Exception):
    pass

class AddressError (Exception):
    pass
class VersionByteError (AddressError):
    pass
class Base58Error (AddressError):
    pass
class InvalidBase58Error (Base58Error):
    pass
class Base58ChecksumError (Base58Error):
    pass

class AssetError (Exception):
    pass
class AssetNameError (AssetError):
    pass
class AssetIDError (AssetError):
    pass

class MessageError (Exception):
    pass
class BurnError (MessageError):
    pass
class SendError (MessageError):
    pass
class OrderError (MessageError):
    pass
class BroadcastError (MessageError):
    pass
class BetError (MessageError):
    pass
class IssuanceError (MessageError):
    pass
class DividendError (MessageError):
    pass
class BTCPayError (MessageError):
    pass
class CancelError (MessageError):
    pass
class CallbackError (MessageError):
    pass

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

########NEW FILE########
__FILENAME__ = issuance
#! /usr/bin/python3

"""
Allow simultaneous lock and transfer.
"""

import struct
import decimal
D = decimal.Decimal

from . import (config, util, exceptions, bitcoin, util)

FORMAT_1 = '>QQ?'
LENGTH_1 = 8 + 8 + 1
FORMAT_2 = '>QQ??If42p'
LENGTH_2 = 8 + 8 + 1 + 1 + 4 + 4 + 42
ID = 20


def validate (db, source, destination, asset, quantity, divisible, callable_, call_date, call_price, description, block_index):
    problems = []
    fee = 0

    if asset in ('BTC', 'XCP'):
        problems.append('cannot issue BTC or XCP')

    if call_date is None: call_date = 0
    if call_price is None: call_price = 0.0
    
    if isinstance(call_price, int): call_price = float(call_price)
    #^ helps especially with calls from JS-based clients, where parseFloat(15) returns 15 (not 15.0), which json takes as an int

    if not isinstance(quantity, int):
        problems.append('quantity must be in satoshis')
        return problems, fee
    if call_date and not isinstance(call_date, int):
        problems.append('call_date must be epoch integer')
        return problems, fee
    if call_price and not isinstance(call_price, float):
        problems.append('call_price must be a float')
        return problems, fee

    if quantity < 0: problems.append('negative quantity')
    if call_price < 0: problems.append('negative call_price')
    if call_date < 0: problems.append('negative call_date')

    # Valid re-issuance?
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM issuances \
                      WHERE (status = ? AND asset = ?)
                      ORDER BY tx_index ASC''', ('valid', asset))
    issuances = cursor.fetchall()
    cursor.close()
    if issuances:
        last_issuance = issuances[-1]
        if call_date is None: call_date = 0
        if call_price is None: call_price = 0.0
        
        if last_issuance['issuer'] != source:
            problems.append('asset exists and was not issued by this address')
        elif bool(last_issuance['divisible']) != bool(divisible):
            problems.append('asset exists with a different divisibility')
        elif bool(last_issuance['callable']) != bool(callable_) or last_issuance['call_date'] != call_date or last_issuance['call_price'] != call_price:
            problems.append('asset exists with a different callability, call date or call price')
        elif last_issuance['locked'] and quantity:
            problems.append('locked asset and non‐zero quantity')
    elif description.lower() == 'lock':
        problems.append('cannot lock a nonexistent asset')
    elif destination:
        problems.append('cannot transfer a nonexistent asset')

    # Check for existence of fee funds.
    if quantity:
        cursor = db.cursor()
        cursor.execute('''SELECT * FROM balances \
                          WHERE (address = ? AND asset = ?)''', (source, 'XCP'))
        balances = cursor.fetchall()
        cursor.close()
        if block_index >= 291700 or config.TESTNET:     # Protocol change.
            fee = int(0.5 * config.UNIT)
        elif block_index >= 286000 or config.TESTNET:   # Protocol change.
            fee = 5 * config.UNIT
        elif block_index > 281236 or config.TESTNET:    # Protocol change.
            fee = 5
        if fee and (not balances or balances[0]['quantity'] < fee):
            problems.append('insufficient funds')

    # For SQLite3
    call_date = min(call_date, config.MAX_INT)
    total = sum([issuance['quantity'] for issuance in issuances])
    assert isinstance(quantity, int)
    if total + quantity > config.MAX_INT:
        problems.append('total quantity overflow')

    if destination and quantity:
        problems.append('cannot issue and transfer simultaneously')

    return problems, fee

def compose (db, source, destination, asset, quantity, divisible, callable_, call_date, call_price, description):
    problems, fee = validate(db, source, destination, asset, quantity, divisible, callable_, call_date, call_price, description, util.last_block(db)['block_index'])
    if problems: raise exceptions.IssuanceError(problems)

    asset_id = util.get_asset_id(asset)
    data = config.PREFIX + struct.pack(config.TXTYPE_FORMAT, ID)
    data += struct.pack(FORMAT_2, asset_id, quantity, 1 if divisible else 0, 1 if callable_ else 0, 
        call_date or 0, call_price or 0.0, description.encode('utf-8'))
    if len(data) > 80:
        raise exceptions.IssuanceError('Description is greater than 52 bytes.')
    if destination:
        destination_outputs = [(destination, None)]
    else:
        destination_outputs = []
    return (source, destination_outputs, data)

def parse (db, tx, message):
    issuance_parse_cursor = db.cursor()

    # Unpack message.
    try:
        if (tx['block_index'] > 283271 or config.TESTNET) and len(message) == LENGTH_2: # Protocol change.
            asset_id, quantity, divisible, callable_, call_date, call_price, description = struct.unpack(FORMAT_2, message)
            call_price = round(call_price, 6) # TODO: arbitrary
            try:
                description = description.decode('utf-8')
            except UnicodeDecodeError:
                description = ''
        else:
            asset_id, quantity, divisible = struct.unpack(FORMAT_1, message)
            callable_, call_date, call_price, description = False, 0, 0.0, ''
        try:
            asset = util.get_asset_name(asset_id)
        except:
            asset = None
            status = 'invalid: bad asset name'
        status = 'valid'
    except (AssertionError, struct.error) as e:
        asset, quantity, divisible, callable_, call_date, call_price, description = None, None, None, None, None, None, None
        status = 'invalid: could not unpack'

    fee = 0
    if status == 'valid':
        if not callable_: calldate, call_price = 0, 0.0
        problems, fee = validate(db, tx['source'], tx['destination'], asset, quantity, divisible, callable_, call_date, call_price, description, block_index=tx['block_index'])
        if problems: status = 'invalid: ' + '; '.join(problems)
        if 'total quantity overflow' in problems:
            quantity = 0

    if tx['destination']:
        issuer = tx['destination']
        transfer = True
        quantity = 0
    else:
        issuer = tx['source']
        transfer = False

    # Debit fee.
    if status == 'valid':
        util.debit(db, tx['block_index'], tx['source'], 'XCP', fee)

    # Lock?
    lock = False
    if description and description.lower() == 'lock':
        lock = True
        cursor = db.cursor()
        issuances = list(cursor.execute('''SELECT * FROM issuances \
                                           WHERE (status = ? AND asset = ?)
                                           ORDER BY tx_index ASC''', ('valid', asset)))
        cursor.close()
        description = issuances[-1]['description']  # Use last description.
        timestamp, value_int, fee_fraction_int = None, None, None

    # Add parsed transaction to message-type–specific table.
    bindings= {
        'tx_index': tx['tx_index'],
        'tx_hash': tx['tx_hash'],
        'block_index': tx['block_index'],
        'asset': asset,
        'quantity': quantity,
        'divisible': divisible,
        'source': tx['source'],
        'issuer': issuer,
        'transfer': transfer,
        'callable': callable_,
        'call_date': call_date,
        'call_price': call_price,
        'description': description,
        'fee_paid': fee,
        'locked': lock,
        'status': status,
    }
    sql='insert into issuances values(:tx_index, :tx_hash, :block_index, :asset, :quantity, :divisible, :source, :issuer, :transfer, :callable, :call_date, :call_price, :description, :fee_paid, :locked, :status)'
    issuance_parse_cursor.execute(sql, bindings)

    # Credit.
    if status == 'valid' and quantity:
        util.credit(db, tx['block_index'], tx['source'], asset, quantity)

    issuance_parse_cursor.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

########NEW FILE########
__FILENAME__ = order
#! /usr/bin/python3

# Filled orders may not be re‐opened, so only orders not involving BTC (and so
# which cannot have expired order matches) may be filled.

import struct
import decimal
D = decimal.Decimal
import logging

from . import (util, config, exceptions, bitcoin, util)

FORMAT = '>QQQQHQ'
LENGTH = 8 + 8 + 8 + 8 + 2 + 8
ID = 10

def cancel_order (db, order, status, block_index):
    cursor = db.cursor()

    # Update status of order.
    bindings = {
        'status': status,
        'tx_hash': order['tx_hash']
    }
    sql='update orders set status = :status where tx_hash = :tx_hash'
    cursor.execute(sql, bindings)
    util.message(db, block_index, 'update', 'orders', bindings)

    if order['give_asset'] != 'BTC':    # Can’t credit BTC.
        util.credit(db, block_index, order['source'], order['give_asset'], order['give_remaining'], event=order['tx_hash'])

    cursor.close()

def cancel_order_match (db, order_match, status, block_index):
    '''
    May only be cancelled by callbacks.'''

    cursor = db.cursor()

    # Update status of order match.
    bindings = {
        'status': status,
        'order_match_id': order_match['id']
    }
    sql='update order_matches set status = :status where id = :order_match_id'
    cursor.execute(sql, bindings)
    util.message(db, block_index, 'update', 'order_matches', bindings)

    order_match_id = order_match['tx0_hash'] + order_match['tx1_hash']

    # If tx0 is dead, credit address directly; if not, replenish give remaining, get remaining, and fee required remaining.
    orders = list(cursor.execute('''SELECT * FROM orders \
                                    WHERE tx_index = ?''',
                                 (order_match['tx0_index'],)))
    assert len(orders) == 1
    tx0_order = orders[0]
    if tx0_order['status'] in ('expired', 'cancelled'):
        tx0_order_status = tx0_order['status']
        if order_match['forward_asset'] != 'BTC':
            util.credit(db, block_index, order_match['tx0_address'],
                        order_match['forward_asset'],
                        order_match['forward_quantity'], event=order_match['id'])
    else:
        tx0_give_remaining = tx0_order['give_remaining'] + order_match['forward_quantity']
        tx0_get_remaining = tx0_order['get_remaining'] + order_match['backward_quantity']
        if tx0_order['get_asset'] == 'BTC' and (block_index >= 297000 or config.TESTNET):    # Protocol change.
            tx0_fee_required_remaining = tx0_order['fee_required_remaining'] + order_match['fee_paid']
        else:
            tx0_fee_required_remaining = tx0_order['fee_required_remaining']
        tx0_order_status = tx0_order['status']
        bindings = {
            'give_remaining': tx0_give_remaining,
            'get_remaining': tx0_get_remaining,
            'status': tx0_order_status,
            'fee_required_remaining': tx0_fee_required_remaining,
            'tx_hash': order_match['tx0_hash']
        }
        sql='update orders set give_remaining = :give_remaining, get_remaining = :get_remaining, fee_required_remaining = :fee_required_remaining where tx_hash = :tx_hash'
        cursor.execute(sql, bindings)
        util.message(db, block_index, 'update', 'orders', bindings)

    # If tx1 is dead, credit address directly; if not, replenish give remaining, get remaining, and fee required remaining.
    orders = list(cursor.execute('''SELECT * FROM orders \
                                    WHERE tx_index = ?''',
                                 (order_match['tx1_index'],)))
    assert len(orders) == 1
    tx1_order = orders[0]
    if tx1_order['status'] in ('expired', 'cancelled'):
        tx1_order_status = tx1_order['status']
        if order_match['backward_asset'] != 'BTC':
            util.credit(db, block_index, order_match['tx1_address'],
                        order_match['backward_asset'],
                        order_match['backward_quantity'], event=order_match['id'])
    else:
        tx1_give_remaining = tx1_order['give_remaining'] + order_match['backward_quantity']
        tx1_get_remaining = tx1_order['get_remaining'] + order_match['forward_quantity']
        if tx1_order['get_asset'] == 'BTC' and (block_index >= 297000 or config.TESTNET):    # Protocol change.
            tx1_fee_required_remaining = tx1_order['fee_required_remaining'] + order_match['fee_paid']
        else:
            tx1_fee_required_remaining = tx1_order['fee_required_remaining']
        tx1_order_status = tx1_order['status']
        bindings = {
            'give_remaining': tx1_give_remaining,
            'get_remaining': tx1_get_remaining,
            'status': tx1_order_status,
            'fee_required_remaining': tx1_fee_required_remaining,
            'tx_hash': order_match['tx1_hash']
        }
        sql='update orders set give_remaining = :give_remaining, get_remaining = :get_remaining, fee_required_remaining = :fee_required_remaining where tx_hash = :tx_hash'
        cursor.execute(sql, bindings)
        util.message(db, block_index, 'update', 'orders', bindings)

    if block_index < 286500:    # Protocol change.
        # Sanity check: one of the two must have expired.
        tx0_order_time_left = tx0_order['expire_index'] - block_index
        tx1_order_time_left = tx1_order['expire_index'] - block_index
        assert tx0_order_time_left or tx1_order_time_left

    cursor.close()


def validate (db, source, give_asset, give_quantity, get_asset, get_quantity, expiration, fee_required):
    problems = []
    cursor = db.cursor()

    if give_asset == 'BTC' and get_asset == 'BTC':
        problems.append('cannot trade BTC for itself')

    if not isinstance(give_quantity, int):
        problems.append('give_quantity must be in satoshis')
        return problems
    if not isinstance(get_quantity, int):
        problems.append('get_quantity must be in satoshis')
        return problems
    if not isinstance(fee_required, int):
        problems.append('fee_required must be in satoshis')
        return problems
    if not isinstance(expiration, int):
        problems.append('expiration must be expressed as an integer block delta')
        return problems

    if give_quantity <= 0: problems.append('non‐positive give quantity')
    if get_quantity <= 0: problems.append('non‐positive get quantity')
    if fee_required < 0: problems.append('negative fee_required')
    if expiration <= 0: problems.append('non‐positive expiration')

    if not give_quantity or not get_quantity:
        problems.append('zero give or zero get')
    cursor.execute('select * from issuances where (status = ? and asset = ?)', ('valid', give_asset))
    if give_asset not in ('BTC', 'XCP') and not cursor.fetchall():
        problems.append('no such asset to give ({})'.format(give_asset))
    cursor.execute('select * from issuances where (status = ? and asset = ?)', ('valid', get_asset))
    if get_asset not in ('BTC', 'XCP') and not cursor.fetchall():
        problems.append('no such asset to get ({})'.format(get_asset))
    if expiration > config.MAX_EXPIRATION:
        problems.append('expiration overflow')

    # For SQLite3
    if give_quantity > config.MAX_INT or get_quantity > config.MAX_INT or fee_required > config.MAX_INT:
        problems.append('integer overflow')

    cursor.close()
    return problems

def compose (db, source, give_asset, give_quantity, get_asset, get_quantity, expiration, fee_required):
    balances = util.get_balances(db, address=source, asset=give_asset)
    if give_asset != 'BTC' and (not balances or balances[0]['quantity'] < give_quantity):
        raise exceptions.OrderError('insufficient funds')

    problems = validate(db, source, give_asset, give_quantity, get_asset, get_quantity, expiration, fee_required)
    if problems: raise exceptions.OrderError(problems)

    give_id = util.get_asset_id(give_asset)
    get_id = util.get_asset_id(get_asset)
    data = config.PREFIX + struct.pack(config.TXTYPE_FORMAT, ID)
    data += struct.pack(FORMAT, give_id, give_quantity, get_id, get_quantity,
                        expiration, fee_required)
    return (source, [], data)

def parse (db, tx, message):
    order_parse_cursor = db.cursor()

    # Unpack message.
    try:
        assert len(message) == LENGTH
        give_id, give_quantity, get_id, get_quantity, expiration, fee_required = struct.unpack(FORMAT, message)
        give_asset = util.get_asset_name(give_id)
        get_asset = util.get_asset_name(get_id)
        status = 'open'
    except (AssertionError, struct.error) as e:
        give_asset, give_quantity, get_asset, get_quantity, expiration, fee_required = 0, 0, 0, 0, 0, 0
        status = 'invalid: could not unpack'

    price = 0
    if status == 'open':
        try: price = util.price(get_quantity, give_quantity, tx['block_index'])
        except Exception as e: pass

        # Overorder
        order_parse_cursor.execute('''SELECT * FROM balances \
                                      WHERE (address = ? AND asset = ?)''', (tx['source'], give_asset))
        balances = list(order_parse_cursor)
        if give_asset != 'BTC':
            if not balances:
                give_quantity = 0
            else:
                balance = balances[0]['quantity']
                if balance < give_quantity:
                    give_quantity = balance
                    get_quantity = int(price * give_quantity)

        problems = validate(db, tx['source'], give_asset, give_quantity, get_asset, get_quantity, expiration, fee_required)
        if problems: status = 'invalid: ' + '; '.join(problems)

    # Debit give quantity. (Escrow.)
    if status == 'open':
        if give_asset != 'BTC':  # No need (or way) to debit BTC.
            util.debit(db, tx['block_index'], tx['source'], give_asset, give_quantity, event=tx['tx_hash'])

    # Add parsed transaction to message-type–specific table.
    bindings = {
        'tx_index': tx['tx_index'],
        'tx_hash': tx['tx_hash'],
        'block_index': tx['block_index'],
        'source': tx['source'],
        'give_asset': give_asset,
        'give_quantity': give_quantity,
        'give_remaining': give_quantity,
        'get_asset': get_asset,
        'get_quantity': get_quantity,
        'get_remaining': get_quantity,
        'expiration': expiration,
        'expire_index': tx['block_index'] + expiration,
        'fee_required': fee_required,
        'fee_required_remaining': fee_required,
        'fee_provided': tx['fee'],
        'fee_provided_remaining': tx['fee'],
        'status': status,
    }
    sql='insert into orders values(:tx_index, :tx_hash, :block_index, :source, :give_asset, :give_quantity, :give_remaining, :get_asset, :get_quantity, :get_remaining, :expiration, :expire_index, :fee_required, :fee_required_remaining, :fee_provided, :fee_provided_remaining, :status)'
    order_parse_cursor.execute(sql, bindings)

    # Match.
    if status == 'open':
        match(db, tx)

    order_parse_cursor.close()

def match (db, tx):
    cursor = db.cursor()

    # Get order in question.
    orders = list(cursor.execute('''SELECT * FROM orders\
                                    WHERE tx_index=?''', (tx['tx_index'],)))
    assert len(orders) == 1
    tx1 = orders[0]

    cursor.execute('''SELECT * FROM orders \
                      WHERE (give_asset=? AND get_asset=? AND status=? AND tx_hash != ?)''',
                   (tx1['get_asset'], tx1['give_asset'], 'open', tx1['tx_hash']))

    tx1_give_remaining = tx1['give_remaining']
    tx1_get_remaining = tx1['get_remaining']

    order_matches = cursor.fetchall()
    if tx['block_index'] > 284500 or config.TESTNET:  # Protocol change.
        order_matches = sorted(order_matches, key=lambda x: x['tx_index'])                              # Sort by tx index second.
        order_matches = sorted(order_matches, key=lambda x: util.price(x['get_quantity'], x['give_quantity'], tx1['block_index']))   # Sort by price first.

    # Get fee remaining.
    tx1_fee_required_remaining = tx1['fee_required_remaining']
    tx1_fee_provided_remaining = tx1['fee_provided_remaining']

    tx1_status = 'open'
    for tx0 in order_matches:
        if tx1_status != 'open': break

        logging.debug('Considering: ' + tx0['tx_hash'])
        tx0_give_remaining = tx0['give_remaining']
        tx0_get_remaining = tx0['get_remaining']

        # Get fee provided remaining.
        tx0_fee_required_remaining = tx0['fee_required_remaining']
        tx0_fee_provided_remaining = tx0['fee_provided_remaining']

        # Make sure that that both orders still have funds remaining (if order involves BTC, and so cannot be ‘filled’).
        if tx0['give_asset'] == 'BTC' or tx0['get_asset'] == 'BTC': # Gratuitous
            if tx0_give_remaining <= 0 or tx1_give_remaining <= 0:
                logging.debug('Negative give remaining.')
                continue
            if tx1['block_index'] >= 292000 or config.TESTNET:  # Protocol change
                if tx0_get_remaining <= 0 or tx1_get_remaining <= 0:
                    logging.debug('Negative get remaining.')
                    continue

            if tx1['block_index'] >= 294000 or config.TESTNET:  # Protocol change.
                if tx0['fee_required_remaining'] < 0:
                    logging.debug('Negative tx0 fee required remaining.')
                    continue
                if tx0['fee_provided_remaining'] < 0:
                    logging.debug('Negative tx0 fee provided remaining.')
                    continue
                if tx1_fee_provided_remaining < 0:
                    logging.debug('Negative tx1 fee provided remaining.')
                    continue
                if tx1_fee_required_remaining < 0:
                    logging.debug('Negative tx1 fee required remaining.')
                    continue

        # If the prices agree, make the trade. The found order sets the price,
        # and they trade as much as they can.
        tx0_price = util.price(tx0['get_quantity'], tx0['give_quantity'], tx1['block_index'])
        tx1_price = util.price(tx1['get_quantity'], tx1['give_quantity'], tx1['block_index'])
        tx1_inverse_price = util.price(tx1['give_quantity'], tx1['get_quantity'], tx1['block_index'])

        # Protocol change.
        if tx['block_index'] < 286000: tx1_inverse_price = util.price(1, tx1_price, tx1['block_index'])

        logging.debug('Tx0 Price: {}; Tx1 Inverse Price: {}'.format(float(tx0_price), float(tx1_inverse_price)))
        if tx0_price <= tx1_inverse_price:
            logging.debug('Potential forward quantities: {}, {}'.format(tx0_give_remaining, int(util.price(tx1_give_remaining, tx0_price, tx1['block_index']))))
            forward_quantity = int(min(tx0_give_remaining, int(util.price(tx1_give_remaining, tx0_price, tx1['block_index']))))
            logging.debug('Forward Quantity: {}'.format(forward_quantity))
            backward_quantity = round(forward_quantity * tx0_price)

            if not forward_quantity:
                logging.debug('Zero forward quantity.')
                continue
            if tx1['block_index'] >= 286500 or config.TESTNET:    # Protocol change.
                if not backward_quantity:
                    logging.debug('Zero backward quantity.')
                    continue
            logging.debug('Backward Quantity: {}'.format(backward_quantity))

            # Check and update fee remainings.
            fee = 0
            if tx1['block_index'] >= 286500 or config.TESTNET: # Protocol change. Deduct fee_required from fee_provided_remaining, etc., if possible (else don’t match).
                if tx1['get_asset'] == 'BTC':
                    fee = int(tx1['fee_required_remaining'] * util.price(forward_quantity, tx1_get_remaining, tx1['block_index']))
                    if tx0_fee_provided_remaining < fee:
                        logging.debug('Tx0 fee provided remaining: {}; Fee: {}'.format(tx0_fee_provided_remaining, fee))
                        continue
                    else:
                        tx0_fee_provided_remaining -= fee
                        if tx1['block_index'] >= 287800 or config.TESTNET:  # Protocol change.
                            tx1_fee_required_remaining -= fee
                elif tx1['give_asset'] == 'BTC':
                    fee = int(tx0['fee_required_remaining'] * util.price(backward_quantity, tx0_get_remaining, tx1['block_index']))
                    if tx1_fee_provided_remaining < fee:
                        logging.debug('Tx1 fee provided remaining: {}; Fee: {}'.format(tx1_fee_provided_remaining, fee))
                        continue
                    else:
                        tx1_fee_provided_remaining -= fee 
                        if tx1['block_index'] >= 287800 or config.TESTNET:  # Protocol change.
                            tx0_fee_required_remaining -= fee
            else:   # Don’t deduct.
                if tx1['get_asset'] == 'BTC':
                    if tx0_fee_provided_remaining < tx1['fee_required']: continue
                elif tx1['give_asset'] == 'BTC':
                    if tx1_fee_provided_remaining < tx0['fee_required']: continue

            forward_asset, backward_asset = tx1['get_asset'], tx1['give_asset']
            order_match_id = tx0['tx_hash'] + tx1['tx_hash']

            if 'BTC' in (tx1['give_asset'], tx1['get_asset']):
                status = 'pending'
            else:
                status = 'completed'
                # Credit.
                util.credit(db, tx['block_index'], tx1['source'], tx1['get_asset'],
                                    forward_quantity, event=order_match_id)
                util.credit(db, tx['block_index'], tx0['source'], tx0['get_asset'],
                                    backward_quantity, event=order_match_id)

            # Debit the order, even if it involves giving bitcoins, and so one
            # can't debit the sending account.
            # Get remainings may be negative.
            tx0_give_remaining -= forward_quantity
            tx0_get_remaining -= backward_quantity
            tx1_give_remaining -= backward_quantity
            tx1_get_remaining -= forward_quantity

            # Update give_remaining, get_remaining.
            # tx0
            tx0_status = 'open'
            if tx0_give_remaining <= 0 or (tx0_get_remaining <= 0 and (tx1['block_index'] >= 292000 or config.TESTNET)):    # Protocol change
                if tx0['give_asset'] != 'BTC' and tx0['get_asset'] != 'BTC':
                    # Fill order, and recredit give_remaining.
                    tx0_status = 'filled'
                    util.credit(db, tx1['block_index'], tx0['source'], tx0['give_asset'], tx0_give_remaining, event=tx1['tx_hash'], action='filled')
            bindings = {
                'give_remaining': tx0_give_remaining,
                'get_remaining': tx0_get_remaining,
                'fee_required_remaining': tx0_fee_required_remaining,
                'fee_provided_remaining': tx0_fee_provided_remaining,
                'status': tx0_status,
                'tx_hash': tx0['tx_hash']
            }
            sql='update orders set give_remaining = :give_remaining, get_remaining = :get_remaining, fee_required_remaining = :fee_required_remaining, fee_provided_remaining = :fee_provided_remaining, status = :status where tx_hash = :tx_hash'
            cursor.execute(sql, bindings)
            util.message(db, tx1['block_index'], 'update', 'orders', bindings)
            # tx1
            if tx1_give_remaining <= 0 or (tx1_get_remaining <= 0 and (tx1['block_index'] >= 292000 or config.TESTNET)):    # Protocol change
                if tx1['give_asset'] != 'BTC' and tx1['get_asset'] != 'BTC':
                    # Fill order, and recredit give_remaining.
                    tx1_status = 'filled'
                    util.credit(db, tx1['block_index'], tx1['source'], tx1['give_asset'], tx1_give_remaining, event=tx0['tx_hash'], action='filled')
            bindings = {
                'give_remaining': tx1_give_remaining,
                'get_remaining': tx1_get_remaining,
                'fee_required_remaining': tx1_fee_required_remaining,
                'fee_provided_remaining': tx1_fee_provided_remaining,
                'status': tx1_status,
                'tx_hash': tx1['tx_hash']
            }
            sql='update orders set give_remaining = :give_remaining, get_remaining = :get_remaining, fee_required_remaining = :fee_required_remaining, fee_provided_remaining = :fee_provided_remaining, status = :status where tx_hash = :tx_hash'
            cursor.execute(sql, bindings)
            util.message(db, tx1['block_index'], 'update', 'orders', bindings)

            # Calculate when the match will expire.
            if tx1['block_index'] >= 286500 or config.TESTNET:    # Protocol change.
                match_expire_index = tx1['block_index'] + 10
            else:
                match_expire_index = min(tx0['expire_index'], tx1['expire_index'])

            # Record order match.
            bindings = {
                'id': tx0['tx_hash'] + tx['tx_hash'],
                'tx0_index': tx0['tx_index'],
                'tx0_hash': tx0['tx_hash'],
                'tx0_address': tx0['source'],
                'tx1_index': tx1['tx_index'],
                'tx1_hash': tx1['tx_hash'],
                'tx1_address': tx1['source'],
                'forward_asset': forward_asset,
                'forward_quantity': forward_quantity,
                'backward_asset': backward_asset,
                'backward_quantity': backward_quantity,
                'tx0_block_index': tx0['block_index'],
                'tx1_block_index': tx1['block_index'],
                'tx0_expiration': tx0['expiration'],
                'tx1_expiration': tx1['expiration'],
                'match_expire_index': match_expire_index,
                'fee_paid': fee,
                'status': status,
            }
            sql='insert into order_matches values(:id, :tx0_index, :tx0_hash, :tx0_address, :tx1_index, :tx1_hash, :tx1_address, :forward_asset, :forward_quantity, :backward_asset, :backward_quantity, :tx0_block_index, :tx1_block_index, :tx0_expiration, :tx1_expiration, :match_expire_index, :fee_paid, :status)'
            cursor.execute(sql, bindings)

            if tx1_status == 'filled':
                break

    cursor.close()

def expire (db, block_index):
    cursor = db.cursor()

    # Expire orders and give refunds for the quantity give_remaining (if non-zero; if not BTC).
    cursor.execute('''SELECT * FROM orders \
                      WHERE (status = ? AND expire_index < ?)''', ('open', block_index))
    for order in cursor.fetchall():
        cancel_order(db, order, 'expired', block_index)

        # Record offer expiration.
        bindings = {
            'order_index': order['tx_index'],
            'order_hash': order['tx_hash'],
            'source': order['source'],
            'block_index': block_index
        }
        sql='insert into order_expirations values(:order_index, :order_hash, :source, :block_index)'
        cursor.execute(sql, bindings)


    # Expire order_matches for BTC with no BTC.
    cursor.execute('''SELECT * FROM order_matches \
                      WHERE (status = ? and match_expire_index < ?)''', ('pending', block_index))
    for order_match in cursor.fetchall():
        cancel_order_match(db, order_match, 'expired', block_index)

        # Record order match expiration.
        bindings = {
            'order_match_id': order_match['id'],
            'tx0_address': order_match['tx0_address'],
            'tx1_address': order_match['tx1_address'],
            'block_index': block_index
        }
        sql='insert into order_match_expirations values(:order_match_id, :tx0_address, :tx1_address, :block_index)'
        cursor.execute(sql, bindings)

    cursor.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

########NEW FILE########
__FILENAME__ = send
#! /usr/bin/python3

"""Create and parse 'send'-type messages."""

import struct

from . import (util, config, exceptions, bitcoin, util)

FORMAT = '>QQ'
LENGTH = 8 + 8
ID = 0


def validate (db, source, destination, asset, quantity):
    problems = []

    if asset == 'BTC': problems.append('cannot send bitcoins')  # Only for parsing.
    
    if not isinstance(quantity, int):
        problems.append('quantity must be in satoshis')
        return problems
    
    if quantity < 0: problems.append('negative quantity')

    return problems

def compose (db, source, destination, asset, quantity):

    # Just send BTC?
    if asset == 'BTC':
        return (source, [(destination, quantity)], None)
    
    #quantity must be in int satoshi (not float, string, etc)
    if not isinstance(quantity, int):
        raise exceptions.SendError('quantity must be an int (in satoshi)')

    # Only for outgoing (incoming will overburn).
    balances = util.get_balances(db, address=source, asset=asset)
    if not balances or balances[0]['quantity'] < quantity:
        raise exceptions.SendError('insufficient funds')

    problems = validate(db, source, destination, asset, quantity)
    if problems: raise exceptions.SendError(problems)

    asset_id = util.get_asset_id(asset)
    data = config.PREFIX + struct.pack(config.TXTYPE_FORMAT, ID)
    data += struct.pack(FORMAT, asset_id, quantity)

    return (source, [(destination, None)], data)

def parse (db, tx, message):
    cursor = db.cursor()

    # Unpack message.
    try:
        assert len(message) == LENGTH
        asset_id, quantity = struct.unpack(FORMAT, message)
        asset = util.get_asset_name(asset_id)
        status = 'valid'
    except (AssertionError, struct.error) as e:
        asset, quantity = None, None
        status = 'invalid: could not unpack'

    if status == 'valid':
        # Oversend
        cursor.execute('''SELECT * FROM balances \
                                     WHERE (address = ? AND asset = ?)''', (tx['source'], asset))
        balances = cursor.fetchall()
        if not balances:  quantity = 0
        elif balances[0]['quantity'] < quantity:
            quantity = min(balances[0]['quantity'], quantity)
        # For SQLite3
        quantity = min(quantity, config.MAX_INT)
        problems = validate(db, tx['source'], tx['destination'], asset, quantity)
        if problems: status = 'invalid: ' + '; '.join(problems)

    if status == 'valid':
        util.debit(db, tx['block_index'], tx['source'], asset, quantity, event=tx['tx_hash'])
        util.credit(db, tx['block_index'], tx['destination'], asset, quantity, event=tx['tx_hash'])

    # Add parsed transaction to message-type–specific table.
    bindings = {
        'tx_index': tx['tx_index'],
        'tx_hash': tx['tx_hash'],
        'block_index': tx['block_index'],
        'source': tx['source'],
        'destination': tx['destination'],
        'asset': asset,
        'quantity': quantity,
        'status': status,
    }
    sql='insert into sends values(:tx_index, :tx_hash, :block_index, :source, :destination, :asset, :quantity, :status)'
    cursor.execute(sql, bindings)


    cursor.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

########NEW FILE########
__FILENAME__ = util
import time
import decimal
import sys
import json
import logging
import operator
import apsw
import collections
import inspect
import requests
from datetime import datetime
from dateutil.tz import tzlocal
from operator import itemgetter
import fractions

from . import (config, exceptions)

D = decimal.Decimal
b26_digits = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

# Obsolete in Python 3.4, with enum module.
BET_TYPE_NAME = {0: 'BullCFD', 1: 'BearCFD', 2: 'Equal', 3: 'NotEqual'}
BET_TYPE_ID = {'BullCFD': 0, 'BearCFD': 1, 'Equal': 2, 'NotEqual': 3}


def api (method, params):
    headers = {'content-type': 'application/json'}
    payload = {
        "method": method,
        "params": params,
        "jsonrpc": "2.0",
        "id": 0,
    }
    response = requests.post(config.RPC, data=json.dumps(payload), headers=headers)
    if response == None:
        raise exceptions.RPCError('Cannot communicate with counterpartyd server.')
    elif response.status_code != 200:
        if response.status_code == 500:
            raise exceptions.RPCError('Malformed API call.')
        else:
            raise exceptions.RPCError(str(response.status_code) + ' ' + response.reason)

    response_json = response.json()
    if 'error' not in response_json.keys() or response_json['error'] == None:
        try:
            return response_json['result']
        except KeyError:
            raise Exception(response_json)
    else:
        raise exceptions.RPCError('{}'.format(response_json['error']))

def price (numerator, denominator, block_index):
    if block_index >= 294500 or config.TESTNET: # Protocol change.
        return fractions.Fraction(numerator, denominator)
    else:
        numerator = D(numerator)
        denominator = D(denominator)
        return D(numerator / denominator)

def log (db, command, category, bindings):

    # Slow?!
    def output (quantity, asset):
        try:
            if asset not in ('fraction', 'leverage'):
                return str(devise(db, quantity, asset, 'output')) + ' ' + asset
            else:
                return str(devise(db, quantity, asset, 'output'))
        except exceptions.AssetError:
            return '<AssetError>'
        except decimal.DivisionByZero:
            return '<DivisionByZero>'

    if command == 'update':
        if category == 'order':
            logging.debug('Database: set status of order {} to {}.'.format(bindings['tx_hash'], bindings['status']))
        elif category == 'bet':
            logging.debug('Database: set status of bet {} to {}.'.format(bindings['tx_hash'], bindings['status']))
        elif category == 'order_matches':
            logging.debug('Database: set status of order_match {} to {}.'.format(bindings['order_match_id'], bindings['status']))
        elif category == 'bet_matches':
            logging.debug('Database: set status of bet_match {} to {}.'.format(bindings['bet_match_id'], bindings['status']))
        # TODO: elif category == 'balances':
            # logging.debug('Database: set balance of {} in {} to {}.'.format(bindings['address'], bindings['asset'], output(bindings['quantity'], bindings['asset']).split(' ')[0]))

    elif command == 'insert':

        if category == 'credits':
            logging.debug('Credit: {} to {} #{}# <{}>'.format(output(bindings['quantity'], bindings['asset']), bindings['address'], bindings['action'], bindings['event']))

        elif category == 'debits':
            logging.debug('Debit: {} from {} #{}# <{}>'.format(output(bindings['quantity'], bindings['asset']), bindings['address'], bindings['action'], bindings['event']))

        elif category == 'sends':
            logging.info('Send: {} from {} to {} ({}) [{}]'.format(output(bindings['quantity'], bindings['asset']), bindings['source'], bindings['destination'], bindings['tx_hash'], bindings['status']))

        elif category == 'orders':
            logging.info('Order: give {} for {} in {} blocks, with a provided fee of {} BTC and a required fee of {} BTC ({}) [{}]'.format(output(bindings['give_quantity'], bindings['give_asset']), output(bindings['get_quantity'], bindings['get_asset']), bindings['expiration'], bindings['fee_provided'] / config.UNIT, bindings['fee_required'] / config.UNIT, bindings['tx_hash'], bindings['status']))

        elif category == 'order_matches':
            logging.info('Order Match: {} for {} ({}) [{}]'.format(output(bindings['forward_quantity'], bindings['forward_asset']), output(bindings['backward_quantity'], bindings['backward_asset']), bindings['id'], bindings['status']))

        elif category == 'btcpays':
            logging.info('BTC Payment: {} paid {} to {} for order match {} ({}) [{}]'.format(bindings['source'], output(bindings['btc_amount'], 'BTC'), bindings['destination'], bindings['order_match_id'], bindings['tx_hash'], bindings['status']))

        elif category == 'issuances':
            if bindings['transfer']:
                logging.info('Issuance: {} transfered asset {} to {} ({}) [{}]'.format(bindings['source'], bindings['asset'], bindings['issuer'], bindings['tx_hash'], bindings['status']))
            elif bindings['locked']:
                logging.info('Issuance: {} locked asset {} ({}) [{}]'.format(bindings['issuer'], bindings['asset'], bindings['tx_hash'], bindings['status']))
            else:
                if bindings['divisible']:
                    divisibility = 'divisible'
                    unit = config.UNIT
                else:
                    divisibility = 'indivisible'
                    unit = 1
                if bindings['callable'] and (bindings['block_index'] > 283271 or config.TESTNET):   # Protocol change.
                    callability = 'callable from {} for {} XCP/{}'.format(isodt(bindings['call_date']), bindings['call_price'], bindings['asset'])
                else:
                    callability = 'uncallable'
                try:
                    quantity = devise(db, bindings['quantity'], None, dest='output', divisible=bindings['divisible'])
                except:
                    quantity = '?'
                logging.info('Issuance: {} created {} of asset {}, which is {} and {}, with description ‘{}’ ({}) [{}]'.format(bindings['issuer'], quantity, bindings['asset'], divisibility, callability, bindings['description'], bindings['tx_hash'], bindings['status']))

        elif category == 'broadcasts':
            if bindings['locked']:
                logging.info('Broadcast: {} locked his feed ({}) [{}]'.format(bindings['source'], bindings['tx_hash'], bindings['status']))
            else:
                if not bindings['value']: infix = '‘{}’'.format(bindings['text'])
                else: infix = '‘{}’ = {}'.format(bindings['text'], bindings['value'])
                suffix = ' from ' + bindings['source'] + ' at ' + isodt(bindings['timestamp']) + ' with a fee of {}%'.format(output(D(bindings['fee_fraction_int'] / 1e8) * D(100), 'fraction')) + ' (' + bindings['tx_hash'] + ')' + ' [{}]'.format(bindings['status'])
                logging.info('Broadcast: {}'.format(infix + suffix))

        elif category == 'bets':
            # Last text
            broadcasts = get_broadcasts(db, status='valid', source=bindings['feed_address'], order_by='tx_index', order_dir='asc')
            try:
                last_broadcast = broadcasts[-1]
                text = last_broadcast['text']
            except IndexError:
                text = '<Text>'

            # Suffix
            end = 'in {} blocks ({}) [{}]'.format(bindings['expiration'], bindings['tx_hash'], bindings['status'])

            if 'CFD' not in BET_TYPE_NAME[bindings['bet_type']]:
                log_message = 'Bet: {} against {}, by {}, on {} that ‘{}’ will {} {} at {}, {}'.format(output(bindings['wager_quantity'], 'XCP'), output(bindings['counterwager_quantity'], 'XCP'), bindings['source'], bindings['feed_address'], text, BET_TYPE_NAME[bindings['bet_type']], str(output(bindings['target_value'], 'value').split(' ')[0]), isodt(bindings['deadline']), end)
            else:
                log_message = 'Bet: {}, by {}, on {} for {} against {}, leveraged {}x, {}'.format(BET_TYPE_NAME[bindings['bet_type']], bindings['source'], bindings['feed_address'],output(bindings['wager_quantity'], 'XCP'), output(bindings['counterwager_quantity'], 'XCP'), output(bindings['leverage']/ 5040, 'leverage'), end)

            logging.info(log_message)

        elif category == 'bet_matches':
            placeholder = ''
            if bindings['target_value'] >= 0:    # Only non‐negative values are valid.
                placeholder = ' that ' + str(output(bindings['target_value'], 'value'))
            if bindings['leverage']:
                placeholder += ', leveraged {}x'.format(output(bindings['leverage'] / 5040, 'leverage'))
            logging.info('Bet Match: {} for {} against {} for {} on {} at {}{} ({}) [{}]'.format(BET_TYPE_NAME[bindings['tx0_bet_type']], output(bindings['forward_quantity'], 'XCP'), BET_TYPE_NAME[bindings['tx1_bet_type']], output(bindings['backward_quantity'], 'XCP'), bindings['feed_address'], isodt(bindings['deadline']), placeholder, bindings['id'], bindings['status']))

        elif category == 'dividends':
            logging.info('Dividend: {} paid {} per unit of {} ({}) [{}]'.format(bindings['source'], output(bindings['quantity_per_unit'], bindings['dividend_asset']), bindings['asset'], bindings['tx_hash'], bindings['status']))

        elif category == 'burns':
            logging.info('Burn: {} burned {} for {} ({}) [{}]'.format(bindings['source'], output(bindings['burned'], 'BTC'), output(bindings['earned'], 'XCP'), bindings['tx_hash'], bindings['status']))

        elif category == 'cancels':
            logging.info('Cancel: {} ({}) [{}]'.format(bindings['offer_hash'], bindings['tx_hash'], bindings['status']))

        elif category == 'callbacks':
            logging.info('Callback: {} called back {}% of {} ({}) [{}]'.format(bindings['source'], float(D(bindings['fraction']) * D(100)), bindings['asset'], bindings['tx_hash'], bindings['status']))

        elif category == 'order_expirations':
            logging.info('Expired order: {}'.format(bindings['order_hash']))

        elif category == 'order_match_expirations':
            logging.info('Expired Order Match awaiting payment: {}'.format(bindings['order_match_id']))

        elif category == 'bet_expirations':
            logging.info('Expired bet: {}'.format(bindings['bet_hash']))

        elif category == 'bet_match_expirations':
            logging.info('Expired Bet Match: {}'.format(bindings['bet_match_id']))

def message (db, block_index, command, category, bindings):
    cursor = db.cursor()

    # Get last message index.
    messages = list(cursor.execute('''SELECT * FROM messages
                                      WHERE message_index = (SELECT MAX(message_index) from messages)'''))
    if messages:
        assert len(messages) == 1
        message_index = messages[0]['message_index'] + 1
    else:
        message_index = 0

    bindings_string = json.dumps(collections.OrderedDict(sorted(bindings.items())))
    cursor.execute('insert into messages values(:message_index, :block_index, :command, :category, :bindings)',
                   (message_index, block_index, command, category, bindings_string))

    cursor.close()

       
def rowtracer(cursor, sql):
    """Converts fetched SQL data into dict-style"""
    dictionary = {}
    for index, (name, type_) in enumerate(cursor.getdescription()):
        dictionary[name] = sql[index]
    return dictionary

def exectracer(cursor, sql, bindings):
    # This means that all changes to database must use a very simple syntax.
        # TODO: Need sanity checks here.
    sql = sql.lower()

    # Parse SQL.
    array = sql.split('(')[0].split(' ')
    if 'insert' in sql:
        command, category = array[0], array[2]
    elif 'update' in sql:
        command, category = array[0], array[1]
    else:
        return True

    db = cursor.getconnection()
    dictionary = {'command': command, 'category': category, 'bindings': bindings}

    # Skip blocks, transactions.
    if 'blocks' in sql or 'transactions' in sql: return True

    # Record alteration in database.
    if category not in ('balances', 'messages'):
        if not (command in ('update') and category in ('orders', 'bets', 'order_matches', 'bet_matches')):    # List message manually.
            try:
                block_index = bindings['block_index']
            except KeyError:
                block_index = bindings['tx1_block_index']
            message(db, block_index, command, category, bindings)

    # Log.
    log(db, command, category, bindings)

    return True

def connect_to_db(flags=None):
    """Connects to the SQLite database, returning a db Connection object"""

    if flags == None:
        db = apsw.Connection(config.DATABASE)
    elif flags == 'SQLITE_OPEN_READONLY':
        db = apsw.Connection(config.DATABASE, flags=0x00000001)
    else:
        raise Exception # TODO

    cursor = db.cursor()

    # For speed.
    cursor.execute('''PRAGMA count_changes = OFF''')

    # For integrity, security.
    cursor.execute('''PRAGMA foreign_keys = ON''')
    cursor.execute('''PRAGMA defer_foreign_keys = ON''')

    # So that writers don’t block readers.
    cursor.execute('''PRAGMA journal_mode = WAL''')

    rows = list(cursor.execute('''PRAGMA foreign_key_check'''))
    if rows: raise exceptions.DatabaseError('Foreign key check failed.')

    # Integrity check
    integral = False
    for i in range(10): # DUPE
        try:
            cursor.execute('''PRAGMA integrity_check''')
            rows = cursor.fetchall()
            if not (len(rows) == 1 and rows[0][0] == 'ok'):
                raise exceptions.DatabaseError('Integrity check failed.')
            integral = True
            break
        except Exception:
            time.sleep(1)
            continue
    if not integral:
        raise exceptions.DatabaseError('Could not perform integrity check.')

    cursor.close()

    db.setrowtrace(rowtracer)
    db.setexectrace(exectracer)

    return db

def version_check (db):
    try:
        host = 'https://raw2.github.com/CounterpartyXCP/counterpartyd/master/version.json'
        response = requests.get(host, headers={'cache-control': 'no-cache'})
        versions = json.loads(response.text)
    except Exception as e:
        raise exceptions.VersionError('Unable to check version. How’s your Internet access?')
 
    # Check client version.
    if config.VERSION_MAJOR < versions['minimum_version_major']:
        if config.VERSION_MINOR < versions['minimum_version_minor']:
            if config.VERSION_REVISION < versions['minimum_version_revision']:
                raise exceptions.VersionError('Please upgrade counterpartyd to the latest version and restart the server.')

    logging.debug('Status: Version check passed.')
    return

def database_check (db, blockcount):
    """Checks Counterparty database to see if the counterpartyd server has caught up with Bitcoind."""
    cursor = db.cursor()
    TRIES = 14
    for i in range(TRIES):
        block_index = last_block(db)['block_index']
        if block_index == blockcount:
            cursor.close()
            return
        print('Database not up‐to‐date. Sleeping for one second. (Try {}/{})'.format(i+1, TRIES), file=sys.stderr)
        time.sleep(1)
    raise exceptions.DatabaseError('Counterparty database is behind Bitcoind. Is the counterpartyd server running?')


def isodt (epoch_time):
    return datetime.fromtimestamp(epoch_time, tzlocal()).isoformat()

def sortkeypicker(keynames):
    """http://stackoverflow.com/a/1143719"""
    negate = set()
    for i, k in enumerate(keynames):
        if k[:1] == '-':
            keynames[i] = k[1:]
            negate.add(k[1:])
    def getit(adict):
       composite = [adict[k] for k in keynames]
       for i, (k, v) in enumerate(zip(keynames, composite)):
           if k in negate:
               composite[i] = -v
       return composite
    return getit

def last_block (db):
    cursor = db.cursor()
    blocks = list(cursor.execute('''SELECT * FROM blocks WHERE block_index = (SELECT MAX(block_index) from blocks)'''))
    if blocks:
        assert len(blocks) == 1
        last_block = blocks[0]
    else:
        raise exceptions.DatabaseError('No blocks found.')
    cursor.close()
    return last_block

def last_message (db):
    cursor = db.cursor()
    messages = list(cursor.execute('''SELECT * FROM messages WHERE message_index = (SELECT MAX(message_index) from messages)'''))
    if messages:
        assert len(messages) == 1
        last_message = messages[0]
    else:
        raise exceptions.DatabaseError('No messages found.')
    cursor.close()
    return last_message

def get_asset_id (asset):
    # Special cases.
    if asset == 'BTC': return 0
    elif asset == 'XCP': return 1

    if asset[0] == 'A': raise exceptions.AssetNameError('starts with ‘A’')

    # Checksum
    """
    if not checksum.verify(asset):
        raise exceptions.AssetNameError('invalid checksum')
    else:
        asset = asset[:-1]  # Strip checksum character.
    """

    # Convert the Base 26 string to an integer.
    n = 0
    for c in asset:
        n *= 26
        if c not in b26_digits:
            raise exceptions.AssetNameError('invalid character:', c)
        digit = b26_digits.index(c)
        n += digit

    if n < 26**3:
        raise exceptions.AssetNameError('too short')

    return n

def get_asset_name (asset_id):
    if asset_id == 0: return 'BTC'
    elif asset_id == 1: return 'XCP'

    if asset_id < 26**3:
        raise exceptions.AssetIDError('too low')

    # Divide that integer into Base 26 string.
    res = []
    n = asset_id
    while n > 0:
        n, r = divmod (n, 26)
        res.append(b26_digits[r])
    asset_name = ''.join(res[::-1])

    """
    return asset_name + checksum.compute(asset_name)
    """
    return asset_name


def debit (db, block_index, address, asset, quantity, action=None, event=None):
    debit_cursor = db.cursor()
    assert asset != 'BTC' # Never BTC.
    assert type(quantity) == int
    assert quantity >= 0

    if asset == 'BTC':
        raise exceptions.BalanceError('Cannot debit bitcoins from a Counterparty address!')

    debit_cursor.execute('''SELECT * FROM balances \
                            WHERE (address = ? AND asset = ?)''', (address, asset))
    balances = debit_cursor.fetchall()
    if not len(balances) == 1: old_balance = 0
    else: old_balance = balances[0]['quantity']

    if old_balance < quantity:
        raise exceptions.BalanceError('Insufficient funds.')

    balance = round(old_balance - quantity)
    balance = min(balance, config.MAX_INT)
    assert balance >= 0

    bindings = {
        'quantity': balance,
        'address': address,
        'asset': asset
    }
    sql='update balances set quantity = :quantity where (address = :address and asset = :asset)'
    debit_cursor.execute(sql, bindings)

    # Record debit.
    bindings = {
        'block_index': block_index,
        'address': address,
        'asset': asset,
        'quantity': quantity,
        'action': action,
        'event': event
    }
    sql='insert into debits values(:block_index, :address, :asset, :quantity, :action, :event)'
    debit_cursor.execute(sql, bindings)

    debit_cursor.close()

def credit (db, block_index, address, asset, quantity, action=None, event=None):
    credit_cursor = db.cursor()
    assert asset != 'BTC' # Never BTC.
    assert type(quantity) == int
    assert quantity >= 0

    credit_cursor.execute('''SELECT * FROM balances \
                             WHERE (address = ? AND asset = ?)''', (address, asset))
    balances = credit_cursor.fetchall()
    if len(balances) == 0:
        assert balances == []

        #update balances table with new balance
        bindings = {
            'address': address,
            'asset': asset,
            'quantity': quantity,
        }
        sql='insert into balances values(:address, :asset, :quantity)'
        credit_cursor.execute(sql, bindings)
    elif len(balances) > 1:
        raise Exception
    else:
        old_balance = balances[0]['quantity']
        assert type(old_balance) == int
        balance = round(old_balance + quantity)
        balance = min(balance, config.MAX_INT)

        bindings = {
            'quantity': balance,
            'address': address,
            'asset': asset
        }
        sql='update balances set quantity = :quantity where (address = :address and asset = :asset)'
        credit_cursor.execute(sql, bindings)

    # Record credit.
    bindings = {
        'block_index': block_index,
        'address': address,
        'asset': asset,
        'quantity': quantity,
        'action': action,
        'event': event
    }
    sql='insert into credits values(:block_index, :address, :asset, :quantity, :action, :event)'
    credit_cursor.execute(sql, bindings)
    credit_cursor.close()

def devise (db, quantity, asset, dest, divisible=None):

    # For output only.
    def norm(num, places):
        # Round only if necessary.
        num = round(num, places)

        fmt = '{:.' + str(places) + 'f}'
        num = fmt.format(num)
        return num.rstrip('0')+'0' if num.rstrip('0')[-1] == '.' else num.rstrip('0')

    # TODO: remove price, odds
    if asset in ('leverage', 'value', 'fraction', 'price', 'odds'):
        if dest == 'output':
            return norm(quantity, 6)
        elif dest == 'input':
            # Hackish
            if asset == 'leverage':
                return round(quantity)
            else:
                return float(quantity)  # TODO: Float?!

    if asset in ('fraction',):
        return norm(fraction(quantity, 1e8), 6)

    if divisible == None:
        if asset in ('BTC', 'XCP'):
            divisible = True
        else:
            cursor = db.cursor()
            cursor.execute('''SELECT * FROM issuances \
                              WHERE (status = ? AND asset = ?)''', ('valid', asset))
            issuances = cursor.fetchall()
            cursor.close()
            if not issuances: raise exceptions.AssetError('No such asset: {}'.format(asset))
            divisible = issuances[0]['divisible']

    if divisible:
        if dest == 'output':
            quantity = D(quantity) / D(config.UNIT)
            if quantity == quantity.to_integral():
                return str(quantity) + '.0'  # For divisible assets, display the decimal point.
            else:
                return norm(quantity, 8)
        elif dest == 'input':
            quantity = D(quantity) * config.UNIT
            if quantity == quantity.to_integral():
                return int(quantity)
            else:
                raise exceptions.QuantityError('Divisible assets have only eight decimal places of precision.')
        else:
            return quantity
    else:
        quantity = D(quantity)
        if quantity != round(quantity):
            raise exceptions.QuantityError('Fractional quantities of indivisible assets.')
        return round(quantity)







DO_FILTER_OPERATORS = {
    '==': operator.eq,
    '!=': operator.ne,
    '<': operator.lt,
    '>': operator.gt,
    '<=': operator.le,
    '>=': operator.ge,
}

def do_filter(results, filters, filterop):
    """Filters results based on a filter data structure (as used by the API)"""
    if not len(results) or not filters: #empty results, or not filtering
        return results
    if isinstance(filters, dict): #single filter entry, convert to a one entry list
        filters = [filters,]
    #validate filter(s)
    required_fields = ['field', 'op', 'value']
    for filter in filters:
        for field in required_fields: #should have all fields
            if field not in filter:
                raise Exception("A specified filter is missing the '%s' field" % field)
        if filterop not in ('and', 'or'):
            raise Exception("Invalid filterop setting. Must be either 'and' or 'or'.")
        if filter['op'] not in DO_FILTER_OPERATORS.keys():
            raise Exception("A specified filter op is invalid or not recognized: '%s'" % filter['op'])
        if filter['field'] == 'block_index':
            raise Exception("For performance reasons, please use the start_block and end_block API arguments to do block_index filtering")
        if filter['field'] not in results[0]:
            raise Exception("A specified filter field is invalid or not recognized for the given object type: '%s'" % filter['field'])
        if type(filter['value']) not in (str, int, float, bool):
            raise Exception("Value specified for filter field '%s' is not one of the supported value types (str, int, float, bool)" % (
                filter['field']))
        if results[0][filter['field']] != None and filter['value'] != None and type(filter['value']) != type(results[0][filter['field']]):
            # field is None when it does not matter.
            raise Exception("Value specified for filter field '%s' does not match the data type of that field (value: %s, field: %s) and neither is None" % (
                filter['field'], type(filter['value']), type(results[0][filter['field']])))
    #filter data
    if filterop == 'and':
        for filter in filters:
            results = [e for e in results if DO_FILTER_OPERATORS[filter['op']](e[filter['field']], filter['value'])]
        return results
    else: #or
        combined_results = []
        for filter in filters:
            if filter['field'] == 'status': continue #don't filter status as an OR requirement
            combined_results += [e for e in results if DO_FILTER_OPERATORS[filter['op']](e[filter['field']], filter['value'])]
        
        status_filter = next((f for f in filters if f['field'] == 'status'), None)
        if status_filter: #filter out invalid results as an AND requirement
            combined_results = [e for e in combined_results if DO_FILTER_OPERATORS[status_filter['op']](
                e[status_filter['field']], status_filter['value'])]
        return combined_results

def do_order_by(results, order_by, order_dir):
    if not len(results) or not order_by: #empty results, or not ordering
        return results
    assert isinstance(results, list) and isinstance(results[0], dict)

    if order_by not in results[0]:
        raise KeyError("Specified order_by property '%s' does not exist in returned data" % order_by)
    if order_dir not in ('asc', 'desc'):
        raise Exception("Invalid order_dir: '%s'. Must be 'asc' or 'desc'" % order_dir)
    return sorted(results, key=itemgetter(order_by), reverse=order_dir=='desc')

def get_limit_to_blocks(start_block, end_block, col_names=['block_index',]):
    if    (start_block is not None and not isinstance(start_block, int)) \
       or (end_block is not None and not isinstance(end_block, int)):
        raise ValueError("start_block and end_block must be either an integer, or None")
    assert isinstance(col_names, list) and len(col_names) in [1, 2]

    if start_block is None and end_block is None:
        return ''
    elif len(col_names) == 1:
        col_name = col_names[0]
        if start_block and end_block:
            block_limit_clause = " WHERE %s >= %s AND %s <= %s" % (col_name, start_block, col_name, end_block)
        elif start_block:
            block_limit_clause = " WHERE %s >= %s" % (col_name, start_block)
        elif end_block:
            block_limit_clause = " WHERE %s <= %s" % (col_name, end_block)
    else: #length of 2
        if start_block and end_block:
            block_limit_clause = " WHERE (%s >= %s OR %s >= %s) AND (%s <= %s OR %s <= %s)" % (
                col_names[0], start_block, col_names[1], start_block,
                col_names[0], end_block, col_names[1], end_block)
        elif start_block:
            block_limit_clause = " WHERE %s >= %s OR %s >= %s" % (
                col_names[0], start_block, col_names[1], start_block)
        elif end_block:
            block_limit_clause = " WHERE %s >= %s OR %s >= %s" % (
                col_names[0], end_block, col_names[1], end_block)
    return block_limit_clause


def get_holders(db, asset):
    holders = []
    cursor = db.cursor()
    # Balances
    cursor.execute('''SELECT * FROM balances \
                      WHERE asset = ?''', (asset,))
    for balance in list(cursor):
        holders.append({'address': balance['address'], 'address_quantity': balance['quantity'], 'escrow': None})
    # Funds escrowed in orders. (Protocol change.)
    cursor.execute('''SELECT * FROM orders \
                      WHERE give_asset = ? AND status = ?''', (asset, 'open'))
    for order in list(cursor):
        holders.append({'address': order['source'], 'address_quantity': order['give_remaining'], 'escrow': order['tx_hash']})
    # Funds escrowed in pending order matches. (Protocol change.)
    cursor.execute('''SELECT * FROM order_matches \
                      WHERE (forward_asset = ? AND status = ?)''', (asset, 'pending'))
    for order_match in list(cursor):
        holders.append({'address': order_match['tx0_address'], 'address_quantity': order_match['forward_quantity'], 'escrow': order_match['id']})
    cursor.execute('''SELECT * FROM order_matches \
                      WHERE (backward_asset = ? AND status = ?)''', (asset, 'pending'))
    for order_match in list(cursor):
        holders.append({'address': order_match['tx1_address'], 'address_quantity': order_match['backward_quantity'], 'escrow': order_match['id']})

    # Bets (and bet matches) only escrow XCP.
    if asset == 'XCP':
        cursor.execute('''SELECT * FROM bets \
                          WHERE status = ?''', ('open',))
        for bet in list(cursor):
            holders.append({'address': bet['source'], 'address_quantity': bet['wager_remaining'], 'escrow': bet['tx_hash']})
        cursor.execute('''SELECT * FROM bet_matches \
                          WHERE status = ?''', ('pending',))
        for bet_match in list(cursor):
            holders.append({'address': bet_match['tx0_address'], 'address_quantity': bet_match['forward_quantity'], 'escrow': bet_match['id']})
            holders.append({'address': bet_match['tx1_address'], 'address_quantity': bet_match['backward_quantity'], 'escrow': bet_match['id']})

    cursor.close()
    return holders

def xcp_supply (db):
    cursor = db.cursor()

    # Add burns.
    cursor.execute('''SELECT * FROM burns \
                      WHERE status = ?''', ('valid',))
    burn_total = sum([burn['earned'] for burn in cursor.fetchall()])

    # Subtract issuance fees.
    cursor.execute('''SELECT * FROM issuances\
                      WHERE status = ?''', ('valid',))
    fee_total = sum([issuance['fee_paid'] for issuance in cursor.fetchall()])

    cursor.close()
    return burn_total - fee_total

def get_supplies (db):
    cursor = db.cursor()
    supplies = {'XCP': xcp_supply(db)}
    cursor.execute('''SELECT * from issuances \
                      WHERE status = ?''', ('valid',))
    for issuance in list(cursor):
        asset = issuance['asset']
        quantity = issuance['quantity']
        if asset in supplies.keys():
            supplies[asset] += quantity
        else:
            supplies[asset] = quantity

    cursor.close()
    return supplies 

def get_debits (db, address=None, asset=None, filters=None, order_by=None, order_dir='asc', start_block=None, end_block=None, filterop='and'):
    """This does not include BTC."""
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if address: filters.append({'field': 'address', 'op': '==', 'value': address})
    if asset: filters.append({'field': 'asset', 'op': '==', 'value': asset})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM debits%s'''
        % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_credits (db, address=None, asset=None, filters=None, order_by=None, order_dir='asc', start_block=None, end_block=None, filterop='and'):
    """This does not include BTC."""
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if address: filters.append({'field': 'address', 'op': '==', 'value': address})
    if asset: filters.append({'field': 'asset', 'op': '==', 'value': asset})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM credits%s'''
        % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_balances (db, address=None, asset=None, filters=None, order_by=None, order_dir='asc', filterop='and'):
    """This should never be used to check Bitcoin balances."""
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if address:
        from . import bitcoin   # HACK
        if not bitcoin.base58_decode(address, config.ADDRESSVERSION):
            raise exceptions.AddressError('Not a valid Bitcoin address:',
                                                 address)
        filters.append({'field': 'address', 'op': '==', 'value': address})
    if asset: filters.append({'field': 'asset', 'op': '==', 'value': asset})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM balances''')
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_sends (db, status=None, source=None, destination=None, filters=None, order_by='tx_index', order_dir='asc', start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if status: filters.append({'field': 'status', 'op': '==', 'value': status})
    if source: filters.append({'field': 'source', 'op': '==', 'value': source})
    if destination: filters.append({'field': 'destination', 'op': '==', 'value': destination})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM sends%s'''
        % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_orders (db, status=None, source=None, show_expired=True, filters=None, order_by=None, order_dir='asc', start_block=None, end_block=None, filterop='and'):
    def filter_expired(e, cur_block_index):
        #Ignore BTC orders one block early. (This is why we need show_expired.)
        #function returns True if the element is NOT expired
        time_left = e['expire_index'] - cur_block_index
        if e['give_asset'] == 'BTC': time_left -= 1
        return False if time_left < 0 else True

    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if status: filters.append({'field': 'status', 'op': '==', 'value': status})
    if source: filters.append({'field': 'source', 'op': '==', 'value': source})
    cur_block_index = last_block(db)['block_index']
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM orders%s'''
        % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    if not show_expired: results = [e for e in results if filter_expired(e, cur_block_index)]
    return do_order_by(results, order_by, order_dir)

def get_order_matches (db, status=None, post_filter_status=None, is_mine=False, address=None, tx0_hash=None, tx1_hash=None, filters=None, order_by='tx1_index', order_dir='asc', start_block=None, end_block=None, filterop='and'):
    from . import bitcoin   # HACK

    def filter_is_mine(e):
        if ((not bitcoin.is_mine(e['tx0_address']) or
                 e['forward_asset'] != 'BTC')
            and (not bitcoin.is_mine(e['tx1_address']) or
                 e['backward_asset'] != 'BTC')):
            return False #is not mine
        return True #is mine

    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if status: filters.append({'field': 'status', 'op': '==', 'value': status})
    if tx0_hash: filters.append({'field': 'tx0_hash', 'op': '==', 'value': tx0_hash})
    if tx1_hash: filters.append({'field': 'tx1_hash', 'op': '==', 'value': tx1_hash})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM order_matches%s'''
        % get_limit_to_blocks(start_block, end_block,
            col_names=['tx0_block_index', 'tx1_block_index']))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()

    filtered_results = []
    for e in results:
        if e in filtered_results: 
            continue
        include = True
        if is_mine:
            include = filter_is_mine(e)
        if include and address:
            include = e['tx0_address'] == address or e['tx1_address'] == address
        if include and post_filter_status:
            include = e['status'] == post_filter_status
        if include:
            filtered_results.append(e)

    return do_order_by(filtered_results, order_by, order_dir)

def get_btcpays (db, status=None, filters=None, order_by='tx_index', order_dir='asc', start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if status: filters.append({'field': 'status', 'op': '==', 'value': status})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM btcpays%s'''
        % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_issuances (db, status=None, asset=None, issuer=None, filters=None, order_by='tx_index', order_dir='asc', start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if status: filters.append({'field': 'status', 'op': '==', 'value': status})
    if asset: filters.append({'field': 'asset', 'op': '==', 'value': asset})
    if issuer: filters.append({'field': 'issuer', 'op': '==', 'value': issuer})
    # TODO: callable, call_date (range?), call_price (range?)
    # TODO: description search
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM issuances%s'''
         % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_broadcasts (db, status=None, source=None, filters=None, order_by='tx_index', order_dir='asc', start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if status: filters.append({'field': 'status', 'op': '==', 'value': status})
    if source: filters.append({'field': 'source', 'op': '==', 'value': source})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM broadcasts%s'''
         % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_bets (db, status=None, source=None, filters=None, order_by=None, order_dir='desc', start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if status: filters.append({'field': 'status', 'op': '==', 'value': status})
    if source: filters.append({'field': 'source', 'op': '==', 'value': source})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM bets%s'''
        % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_bet_matches (db, status=None, address=None, tx0_hash=None, tx1_hash=None, filters=None, order_by='tx1_index', order_dir='asc', start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if status: filters.append({'field': 'status', 'op': '==', 'value': status})
    if tx0_hash: filters.append({'field': 'tx0_hash', 'op': '==', 'value': tx0_hash})
    if tx1_hash: filters.append({'field': 'tx1_hash', 'op': '==', 'value': tx1_hash})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM bet_matches%s'''
         % get_limit_to_blocks(start_block, end_block,
             col_names=['tx0_block_index', 'tx1_block_index']))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    if address: results = [e for e in results if e['tx0_address'] == address or e['tx1_address'] == address]
    return do_order_by(results, order_by, order_dir)

def get_dividends (db, status=None, source=None, asset=None, filters=None, order_by='tx_index', order_dir='asc', start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if status: filters.append({'field': 'status', 'op': '==', 'value': status})
    if source: filters.append({'field': 'source', 'op': '==', 'value': source})
    if asset: filters.append({'field': 'asset', 'op': '==', 'value': asset})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM dividends%s'''
         % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_burns (db, status=None, source=None, filters=None, order_by='tx_index', order_dir='asc', start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if status: filters.append({'field': 'status', 'op': '==', 'value': status})
    if source: filters.append({'field': 'source', 'op': '==', 'value': source})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM burns%s'''
         % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_cancels (db, status=None, source=None, filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if status: filters.append({'field': 'status', 'op': '==', 'value': status})
    if source: filters.append({'field': 'source', 'op': '==', 'value': source})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM cancels%s'''
         % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_callbacks (db, status=None, source=None, filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if status: filters.append({'field': 'status', 'op': '==', 'value': status})
    if source: filters.append({'field': 'source', 'op': '==', 'value': source})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM callbacks%s'''
         % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_bet_expirations (db, source=None, filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if source: filters.append({'field': 'source', 'op': '==', 'value': source})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM bet_expirations%s'''
         % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_order_expirations (db, source=None, filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if source: filters.append({'field': 'source', 'op': '==', 'value': source})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM order_expirations%s'''
         % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_bet_match_expirations (db, address=None, filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM bet_match_expirations%s'''
         % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    if address: results = [e for e in results if e['tx0_address'] == address or e['tx1_address'] == address]
    return do_order_by(results, order_by, order_dir)

def get_order_match_expirations (db, address=None, filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM order_match_expirations%s'''
         % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    if address: results = [e for e in results if e['tx0_address'] == address or e['tx1_address'] == address]
    return do_order_by(results, order_by, order_dir)

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

########NEW FILE########
__FILENAME__ = util_windows
import sys
import copy
import logging
import unicodedata
import codecs
from ctypes import WINFUNCTYPE, windll, POINTER, byref, c_int
from ctypes.wintypes import BOOL, HANDLE, DWORD, LPWSTR, LPCWSTR, LPVOID

class SanitizedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    def emit(self, record):
        # If the message doesn't need to be rendered we take a shortcut.
        if record.levelno < self.level:
            return
        # Make sure the message is a string.
        message = record.msg
        #Sanitize and clean up the message
        message = unicodedata.normalize('NFKD', message).encode('ascii', 'ignore').decode()
        # Copy the original record so we don't break other handlers.
        record = copy.copy(record)
        record.msg = message
        # Use the built-in stream handler to handle output.
        logging.handlers.RotatingFileHandler.emit(self, record)

def fix_win32_unicode():
    """Thanks to http://stackoverflow.com/a/3259271 ! (converted to python3)"""
    if sys.platform != "win32":
        return

    original_stderr = sys.stderr

    # If any exception occurs in this code, we'll probably try to print it on stderr,
    # which makes for frustrating debugging if stderr is directed to our wrapper.
    # So be paranoid about catching errors and reporting them to original_stderr,
    # so that we can at least see them.
    def _complain(message):
        print(message if isinstance(message, str) else repr(message), file=original_stderr)

    # Work around <http://bugs.python.org/issue6058>.
    codecs.register(lambda name: codecs.lookup('utf-8') if name == 'cp65001' else None)

    # Make Unicode console output work independently of the current code page.
    # This also fixes <http://bugs.python.org/issue1602>.
    # Credit to Michael Kaplan <http://blogs.msdn.com/b/michkap/archive/2010/04/07/9989346.aspx>
    # and TZOmegaTZIOY
    # <http://stackoverflow.com/questions/878972/windows-cmd-encoding-change-causes-python-crash/1432462#1432462>.
    try:
        # <http://msdn.microsoft.com/en-us/library/ms683231(VS.85).aspx>
        # HANDLE WINAPI GetStdHandle(DWORD nStdHandle);
        # returns INVALID_HANDLE_VALUE, NULL, or a valid handle
        #
        # <http://msdn.microsoft.com/en-us/library/aa364960(VS.85).aspx>
        # DWORD WINAPI GetFileType(DWORD hFile);
        #
        # <http://msdn.microsoft.com/en-us/library/ms683167(VS.85).aspx>
        # BOOL WINAPI GetConsoleMode(HANDLE hConsole, LPDWORD lpMode);

        GetStdHandle = WINFUNCTYPE(HANDLE, DWORD)(("GetStdHandle", windll.kernel32))
        STD_OUTPUT_HANDLE = DWORD(-11)
        STD_ERROR_HANDLE = DWORD(-12)
        GetFileType = WINFUNCTYPE(DWORD, DWORD)(("GetFileType", windll.kernel32))
        FILE_TYPE_CHAR = 0x0002
        FILE_TYPE_REMOTE = 0x8000
        GetConsoleMode = WINFUNCTYPE(BOOL, HANDLE, POINTER(DWORD))(("GetConsoleMode", windll.kernel32))
        INVALID_HANDLE_VALUE = DWORD(-1).value

        def not_a_console(handle):
            if handle == INVALID_HANDLE_VALUE or handle is None:
                return True
            return ((GetFileType(handle) & ~FILE_TYPE_REMOTE) != FILE_TYPE_CHAR
                    or GetConsoleMode(handle, byref(DWORD())) == 0)

        old_stdout_fileno = None
        old_stderr_fileno = None
        if hasattr(sys.stdout, 'fileno'):
            old_stdout_fileno = sys.stdout.fileno()
        if hasattr(sys.stderr, 'fileno'):
            old_stderr_fileno = sys.stderr.fileno()

        STDOUT_FILENO = 1
        STDERR_FILENO = 2
        real_stdout = (old_stdout_fileno == STDOUT_FILENO)
        real_stderr = (old_stderr_fileno == STDERR_FILENO)

        if real_stdout:
            hStdout = GetStdHandle(STD_OUTPUT_HANDLE)
            if not_a_console(hStdout):
                real_stdout = False

        if real_stderr:
            hStderr = GetStdHandle(STD_ERROR_HANDLE)
            if not_a_console(hStderr):
                real_stderr = False

        if real_stdout or real_stderr:
            # BOOL WINAPI WriteConsoleW(HANDLE hOutput, LPWSTR lpBuffer, DWORD nChars,
            #                           LPDWORD lpCharsWritten, LPVOID lpReserved);

            WriteConsoleW = WINFUNCTYPE(BOOL, HANDLE, LPWSTR, DWORD, POINTER(DWORD), LPVOID)(("WriteConsoleW", windll.kernel32))

            class UnicodeOutput:
                def __init__(self, hConsole, stream, fileno, name):
                    self._hConsole = hConsole
                    self._stream = stream
                    self._fileno = fileno
                    self.closed = False
                    self.softspace = False
                    self.mode = 'w'
                    self.encoding = 'utf-8'
                    self.name = name
                    self.errors = ''
                    self.flush()

                def isatty(self):
                    return False

                def close(self):
                    # don't really close the handle, that would only cause problems
                    self.closed = True

                def fileno(self):
                    return self._fileno

                def flush(self):
                    if self._hConsole is None:
                        try:
                            self._stream.flush()
                        except Exception as e:
                            _complain("%s.flush: %r from %r" % (self.name, e, self._stream))
                            raise

                def write(self, text):
                    try:
                        if self._hConsole is None:
                            if isinstance(text, str):
                                text = text.encode('utf-8')
                            self._stream.write(text)
                        else:
                            if not isinstance(text, str):
                                text = str(text).decode('utf-8')
                            remaining = len(text)
                            while remaining:
                                n = DWORD(0)
                                # There is a shorter-than-documented limitation on the
                                # length of the string passed to WriteConsoleW (see
                                # <http://tahoe-lafs.org/trac/tahoe-lafs/ticket/1232>.
                                retval = WriteConsoleW(self._hConsole, text, min(remaining, 10000), byref(n), None)
                                if retval == 0 or n.value == 0:
                                    raise IOError("WriteConsoleW returned %r, n.value = %r" % (retval, n.value))
                                remaining -= n.value
                                if not remaining:
                                    break
                                text = text[n.value:]
                    except Exception as e:
                        _complain("%s.write: %r" % (self.name, e))
                        raise

                def writelines(self, lines):
                    try:
                        for line in lines:
                            self.write(line)
                    except Exception as e:
                        _complain("%s.writelines: %r" % (self.name, e))
                        raise

            if real_stdout:
                sys.stdout = UnicodeOutput(hStdout, None, STDOUT_FILENO, '<Unicode console stdout>')
            else:
                sys.stdout = UnicodeOutput(None, sys.stdout, old_stdout_fileno, '<Unicode redirected stdout>')

            if real_stderr:
                sys.stderr = UnicodeOutput(hStderr, None, STDERR_FILENO, '<Unicode console stderr>')
            else:
                sys.stderr = UnicodeOutput(None, sys.stderr, old_stderr_fileno, '<Unicode redirected stderr>')
    except Exception as e:
        _complain("exception %r while fixing up sys.stdout and sys.stderr" % (e,))


    # While we're at it, let's unmangle the command-line arguments:

    # This works around <http://bugs.python.org/issue2128>.
    GetCommandLineW = WINFUNCTYPE(LPWSTR)(("GetCommandLineW", windll.kernel32))
    CommandLineToArgvW = WINFUNCTYPE(POINTER(LPWSTR), LPCWSTR, POINTER(c_int))(("CommandLineToArgvW", windll.shell32))

    argc = c_int(0)
    argv_unicode = CommandLineToArgvW(GetCommandLineW(), byref(argc))

    argv = [argv_unicode[i].encode('utf-8').decode('utf-8') for i in range(0, argc.value)]

    if not hasattr(sys, 'frozen'):
        # If this is an executable produced by py2exe or bbfreeze, then it will
        # have been invoked directly. Otherwise, unicode_argv[0] is the Python
        # interpreter, so skip that.
        argv = argv[1:]

        # Also skip option arguments to the Python interpreter.
        while len(argv) > 0:
            arg = argv[0]
            if not arg.startswith("-") or arg == "-":
                break
            argv = argv[1:]
            if arg == '-m':
                # sys.argv[0] should really be the absolute path of the module source,
                # but never mind
                break
            if arg == '-c':
                argv[0] = '-c'
                break

    # if you like:
    sys.argv = argv

########NEW FILE########
__FILENAME__ = test_
#! /usr/bin/python3

import os
import sys
import hashlib
import binascii
import time
import apsw
import decimal
D = decimal.Decimal
import difflib
import json
import inspect
import requests
from requests.auth import HTTPBasicAuth
import logging
import tempfile
import shutil
import locale
import re

# Set test environment
os.environ['TZ'] = 'EST'
time.tzset()
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

CURR_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(CURR_DIR, '..')))

from lib import (config, api, util, exceptions, bitcoin, blocks)
from lib import (send, order, btcpay, issuance, broadcast, bet, dividend, burn, cancel, callback)
import counterpartyd

# config.BLOCK_FIRST = 0
# config.BURN_START = 0
# config.BURN_END = 9999999
counterpartyd.set_options(rpc_port=9999, database_file=CURR_DIR+'/counterpartyd.unittest.db', testnet=True, testcoin=False, unittest=True)

# Connect to database.
try: os.remove(config.DATABASE)
except: pass
db = util.connect_to_db()
cursor = db.cursor()

# Each tx has a block_index equal to its tx_index
tx_index = 0

source_default = 'mn6q3dS2EnDUx3bmyWc6D4szJNVGtaR7zc'
destination_default = 'n3BrDB6zDiEPWEE6wLxywFb4Yp9ZY5fHM7'
quantity = config.UNIT
small = round(quantity / 2)
expiration = 10
fee_required = 900000
fee_provided = 1000000
fee_multiplier_default = .05

def parse_hex (unsigned_tx_hex):

    tx = bitcoin.decode_raw_transaction(unsigned_tx_hex)

    cursor = db.cursor()
    tx_hash = hashlib.sha256(chr(tx_index).encode('utf-8')).hexdigest()
    global tx_index
    block_index = config.BURN_START + tx_index
    block_hash = hashlib.sha512(chr(block_index).encode('utf-8')).hexdigest()
    block_time = block_index * 10000000

    source, destination, btc_amount, fee, data = blocks.get_tx_info(tx, block_index)

    cursor.execute('''INSERT INTO blocks(
                        block_index,
                        block_hash,
                        block_time) VALUES(?,?,?)''',
                        (block_index,
                        block_hash,
                        block_time)
                  )

    cursor.execute('''INSERT INTO transactions(
                        tx_index,
                        tx_hash,
                        block_index,
                        block_time,
                        source,
                        destination,
                        btc_amount,
                        fee,
                        data) VALUES(?,?,?,?,?,?,?,?,?)''',
                        (tx_index,
                         tx_hash,
                         block_index,
                         tx_index,
                         source,
                         destination,
                         btc_amount,
                         fee,
                         data)
                  )

    txes = list(cursor.execute('''SELECT * FROM transactions \
                                  WHERE tx_index=?''', (tx_index,)))
    assert len(txes) == 1
    tx = txes[0]
    blocks.parse_tx(db, tx)

    # After parsing every transaction, check that the credits, debits sum properly.
    cursor.execute('''SELECT * FROM balances''')
    for balance in cursor.fetchall():
        quantity = 0
        cursor.execute('''SELECT * FROM debits \
                          WHERE (address = ? AND asset = ?)''', (balance['address'], balance['asset']))
        for debit in cursor.fetchall():
            quantity -= debit['quantity']
        cursor.execute('''SELECT * FROM credits \
                          WHERE (address = ? AND asset = ?)''', (balance['address'], balance['asset']))
        for credit in cursor.fetchall():
            quantity += credit['quantity']
        assert quantity == balance['quantity']

    tx_index += 1
    cursor.close()

# https://github.com/CounterpartyXCP/counterpartyd/blob/develop/test/db.dump#L23
# some sqlite version generates spaces and line breaks too.
def clean_sqlite_dump(dump):
    dump = "\n".join(dump)
    dump = re.sub('\)[\n\s]+;', ');', dump)
    return dump.split("\n")

def compare(filename):
    old = CURR_DIR + '/' + filename
    new = old + '.new'

    with open(old, 'r') as f:
        old_lines = f.readlines()
    with open(new, 'r') as f:
        new_lines = f.readlines()

    if (filename == 'db.dump'):
        old_lines = clean_sqlite_dump(old_lines)
        new_lines = clean_sqlite_dump(new_lines)

    diff = list(difflib.unified_diff(old_lines, new_lines, n=0))
    if len(diff):
        print(diff)
    assert not len(diff)

def summarise (ebit):
    return (ebit['block_index'], ebit['address'], ebit['asset'], ebit['quantity'])


def setup_function(function):
    global db
    global cursor
    cursor.execute('''BEGIN''')

def teardown_function(function):
    cursor.execute('''END''')

# Logs.
try: os.remove(CURR_DIR + '/log.new')
except: pass
logging.basicConfig(filename=CURR_DIR + '/log.new', level=logging.DEBUG, format='%(message)s')
requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)

# Output.
output_new = {}
with open(CURR_DIR + '/output.json', 'r') as output_file:
    output = json.load(output_file)

# TODO: replace inspect.stack()[0][3] with inspect.currentframe().f_code.co_name?

def test_start ():
    logging.info('START TEST')

def test_initialise ():
    blocks.initialise(db)

    # First block (for burn.create sanity check).
    cursor = db.cursor()
    cursor.execute('''INSERT INTO blocks(
                        block_index,
                        block_hash,
                        block_time) VALUES(?,?,?)''',
                        (config.BURN_START - 1,
                        'foobar',
                        1337)
                  )
    cursor.close()

def test_burn ():
    unsigned_tx_hex = bitcoin.transaction(burn.compose(db, source_default, int(.62 * quantity)), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_send ():
    unsigned_tx_hex = bitcoin.transaction(send.compose(db, source_default, destination_default, 'XCP', small), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_order_buy_xcp ():
    unsigned_tx_hex = bitcoin.transaction(order.compose(db, source_default, 'BTC', small, 'XCP', small * 2, expiration, 0), encoding='multisig', fee_provided=fee_provided)

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_order_sell_xcp ():
    unsigned_tx_hex = bitcoin.transaction(order.compose(db, source_default, 'XCP', round(small * 2.1), 'BTC', small, expiration, fee_required), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_btcpay ():
    order_match_id = 'dbc1b4c900ffe48d575b5da5c638040125f65db0fe3e24494b76ea986457d986084fed08b978af4d7d196a7446a86b58009e636b611db16211b65a9aadff29c5'
    unsigned_tx_hex = bitcoin.transaction(btcpay.compose(db, source_default, order_match_id), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_issuance_divisible ():
    unsigned_tx_hex = bitcoin.transaction(issuance.compose(db, source_default, None, 'BBBB', quantity * 10, True, False, 0, 0.0, ''), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_issuance_indivisible_callable ():
    unsigned_tx_hex = bitcoin.transaction(issuance.compose(db, source_default, None, 'BBBC', round(quantity / 1000), False, True, 17, 0.015, 'foobar'), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_send_divisible ():
    unsigned_tx_hex = bitcoin.transaction(send.compose(db, source_default, destination_default, 'BBBB', round(quantity / 25)), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_send_indivisible ():
    unsigned_tx_hex = bitcoin.transaction(send.compose(db, source_default, destination_default, 'BBBC', round(quantity / 190000)), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_dividend_divisible ():
    unsigned_tx_hex = bitcoin.transaction(dividend.compose(db, source_default, 600, 'BBBB', 'XCP'), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_dividend_indivisible ():
    unsigned_tx_hex = bitcoin.transaction(dividend.compose(db, source_default, 800, 'BBBC', 'XCP'), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_broadcast_initial ():
    unsigned_tx_hex = bitcoin.transaction(broadcast.compose(db, source_default, 1388000000, 100, fee_multiplier_default, 'Unit Test'), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_bet_bullcfd_to_be_liquidated ():
    unsigned_tx_hex = bitcoin.transaction(bet.compose(db, source_default, source_default, 0, 1388000100, small, round(small / 2), 0.0, 15120, expiration), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_bet_bearcfd_to_be_liquidated ():
    unsigned_tx_hex = bitcoin.transaction(bet.compose(db, source_default, source_default, 1, 1388000100, round(small / 2), round(small * .83), 0.0, 15120, expiration), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_bet_bullcfd_to_be_settled ():
    unsigned_tx_hex = bitcoin.transaction(bet.compose(db, source_default, source_default, 0, 1388000100, small * 3, small * 7, 0.0, 5040, expiration), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_bet_bearcfd_to_be_settled ():
    unsigned_tx_hex = bitcoin.transaction(bet.compose(db, source_default, source_default, 1, 1388000100, small * 7, small * 3, 0.0, 5040, expiration), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_bet_equal ():
    unsigned_tx_hex = bitcoin.transaction(bet.compose(db, source_default, source_default, 2, 1388000200, small * 15, small * 13, 1, 5040, expiration), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_bet_notequal ():
    unsigned_tx_hex = bitcoin.transaction(bet.compose(db, source_default, source_default, 3, 1388000200, small * 13, small * 15, 1, 5040, expiration), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_broadcast_liquidate ():
    unsigned_tx_hex = bitcoin.transaction(broadcast.compose(db, source_default, 1388000050, round(100 - (.415/3) - .00001, 5), fee_multiplier_default, 'Unit Test'), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_broadcast_settle ():
    unsigned_tx_hex = bitcoin.transaction(broadcast.compose(db, source_default, 1388000101, 100.343, fee_multiplier_default, 'Unit Test'), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_broadcast_equal ():
    unsigned_tx_hex = bitcoin.transaction(broadcast.compose(db, source_default, 1388000201, 2, fee_multiplier_default, 'Unit Test'), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_order_to_be_cancelled ():
    unsigned_tx_hex = bitcoin.transaction(order.compose(db, source_default, 'BBBB', small, 'XCP', small, expiration, 0), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_cancel ():
    unsigned_tx_hex = bitcoin.transaction(cancel.compose(db, source_default, '2f0fd1e89b8de1d57292742ec380ea47066e307ad645f5bc3adad8a06ff58608'), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_overburn ():
    unsigned_tx_hex = bitcoin.transaction(burn.compose(db, source_default, (1 * config.UNIT), overburn=True), encoding='multisig')  # Try to burn a whole 'nother BTC.

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_send_callable ():
    unsigned_tx_hex = bitcoin.transaction(send.compose(db, source_default, destination_default, 'BBBC', 10000), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_callback ():
    unsigned_tx_hex = bitcoin.transaction(callback.compose(db, source_default, .3, 'BBBC'), encoding='multisig')

    parse_hex(unsigned_tx_hex)

    output_new[inspect.stack()[0][3]] = unsigned_tx_hex

def test_json_rpc():

    # TODO: Broken
    api_server = api.APIServer()
    api_server.daemon = True
    api_server.start()
    url = 'http://' + str(config.RPC_USER) + ':' + config.RPC_PASSWORD + '@localhost:' + str(config.RPC_PORT)

    # TEMP: Use external server.
    url = 'http://' + str(config.RPC_USER) + ':' + config.RPC_PASSWORD + '@localhost:' + '14000'

    headers = {'content-type': 'application/json'}
    payloads = []
    payloads.append({
        "method": "get_balances",
        "params": {"filters": {'field': 'address', 'op': '==', 'value': 'mtQheFaSfWELRB2MyMBaiWjdDm6ux9Ezns'}},
        "jsonrpc": "2.0",
        "id": 0,
    })
    payloads.append({
        "method": "create_send",
        "params": {'source': 'mtQheFaSfWELRB2MyMBaiWjdDm6ux9Ezns', 'destination': destination_default, 'asset': 'XCP', 'quantity': 1, 'encoding': 'pubkeyhash', 'pubkey': '0319f6e07b0b8d756156394b9dcf3b011fe9ac19f2700bd6b69a6a1783dbb8b977'},
        "jsonrpc": "2.0",
        "id": 0,
    })

    for payload in payloads:
        for attempt in range(100):  # Try until server is ready.
            try:
                response = requests.post(url, data=json.dumps(payload), headers=headers).json()
                # print('\npayload', payload)
                # print('response', response, '\n')
                if not response['result']:
                    raise Exception('null result')
                    assert False
                assert response['jsonrpc'] == '2.0'
                assert response['id'] == 0
                output_new['rpc.' + payload['method']] = response['result']
                break
            except requests.exceptions.ConnectionError:
                time.sleep(.05)
        if attempt == 99: exit(1)   # Fail

def test_get_address():
    get_address = counterpartyd.get_address(db, source_default)
    for field in get_address:
        output_new['get_address_' + field] = get_address[field]

def test_stop():
    logging.info('STOP TEST')


def test_db():
    GOOD = CURR_DIR + '/db.dump'
    NEW = CURR_DIR + '/db.dump.new'

    with open(GOOD, 'r') as f:
        good_data = f.readlines()

    import io
    output=io.StringIO()
    shell=apsw.Shell(stdout=output, args=(config.DATABASE,))
    shell.process_command(".dump")
    with open(NEW, 'w') as f:
        lines = output.getvalue().split('\n')[8:]
        new_data = '\n'.join(lines)
        f.writelines(new_data)

    compare('db.dump')

def test_output():
    with open(CURR_DIR + '/output.json.new', 'w') as output_new_file:
        json.dump(output_new, output_new_file, sort_keys=True, indent=4)

    for key in output_new.keys():
        try:
            assert output[key] == output_new[key]
        except Exception as e:
            print('Key:', key)
            print('Old output:')
            print(output[key])
            print('New output:')
            print(output_new[key])
            raise e

def test_log():
    compare('log')

def test_base58_decode():
    """
    mainnet addresses here

    The leading zeros are not included in the pubkeyhash: see
    <http://www.bitcoinsecurity.org/wp-content/uploads/2012/07/tx_binary_map.png>.
    """
    address = '16UwLL9Risc3QfPqBUvKofHmBQ7wMtjvM'
    pubkeyhash = bitcoin.base58_decode(address, b'\x00')
    assert binascii.hexlify(pubkeyhash).decode('utf-8') == '010966776006953D5567439E5E39F86A0D273BEE'.lower()
    assert len(pubkeyhash) == 20

def do_book(testnet):
    # Filenames.
    if testnet:
        filename = 'book.testnet'
    else:
        filename = 'book.mainnet'
    old = CURR_DIR + '/' + filename
    new = old + '.new'

    # Get last block_index of old book.
    with open(old, 'r') as f:
        block_index = int(f.readlines()[-1][7:13])

    # Use temporary DB.
    counterpartyd.set_options(testnet=testnet)
    default_db = config.DATABASE
    temp_db = tempfile.gettempdir() + '/' + os.path.basename(config.DATABASE)
    shutil.copyfile(default_db, temp_db)
    counterpartyd.set_options(database_file=temp_db, testnet=testnet)
    db = util.connect_to_db()
    cursor = db.cursor()

    # TODO: USE API
    import subprocess
    if testnet:
        subprocess.check_call(['./counterpartyd.py', '--database-file=' + temp_db, '--testnet', '--force', 'reparse'])
    else:
        subprocess.check_call(['./counterpartyd.py', '--database-file=' + temp_db, 'reparse'])

    # Get new book.
    with open(new, 'w') as f:
        # Credits.
        cursor.execute('select * from credits where block_index <= ? order by block_index, address, asset', (block_index,))
        for credit in list(cursor):
            f.write('credit ' + str(summarise(credit)) + '\n')
        # Debits.
        cursor.execute('select * from debits where block_index <= ? order by block_index, address, asset', (block_index,))
        for debit in cursor.fetchall():
            f.write('debit ' + str(summarise(debit)) + '\n')

    # Compare books.
    compare(filename)

    # Clean up.
    cursor.close()
    os.remove(temp_db)

def test_book_testnet():
    do_book(True)

def test_book_mainnet():
    do_book(False)

########NEW FILE########
