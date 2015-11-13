__FILENAME__ = api_daemon
#!/usr/bin/python2.7
import os
import sys
import time
from email import utils
import logging

import redis
import simplejson as json

import bitcoinaverage as ba
import bitcoinaverage.server
from bitcoinaverage import api_custom_writers
from bitcoinaverage.config import API_WRITE_FREQUENCY, FIAT_RATES_QUERY_FREQUENCY
import bitcoinaverage.helpers as helpers
from bitcoinaverage.api_calculations import calculateTotalVolumes, calculateRelativeVolumes, calculateAverageRates, formatDataForAPI, writeAPIFiles, calculateAllGlobalAverages

logger = logging.getLogger("api_daemon")

logger.info("script started")
helpers.write_js_config()
helpers.write_fiat_rates_config()
last_fiat_exchange_rate_update = time.time()
helpers.write_api_index_files()

red = redis.StrictRedis(host="localhost", port=6379, db=0)

while True:
    if last_fiat_exchange_rate_update < int(time.time())-FIAT_RATES_QUERY_FREQUENCY:
        helpers.write_fiat_rates_config()

    start_time = int(time.time())

    if not red.exists("ba:exchanges"):
        logger.warning("database is empty")
        time.sleep(API_WRITE_FREQUENCY)
        continue
    exchanges_rates = []
    exchanges_ignored = {}
    for exchange_data in red.hgetall("ba:exchanges").itervalues():
        exchanges_rates.append(json.loads(exchange_data, use_decimal=True))
    for exchange_name, exchange_ignore_reason in red.hgetall("ba:exchanges_ignored").iteritems():
        exchanges_ignored[exchange_name] = exchange_ignore_reason

    total_currency_volumes, total_currency_volumes_ask, total_currency_volumes_bid = calculateTotalVolumes(exchanges_rates)
    calculated_volumes = calculateRelativeVolumes(exchanges_rates,
                                                  total_currency_volumes,
                                                  total_currency_volumes_ask,
                                                  total_currency_volumes_bid)
    calculated_average_rates = calculateAverageRates(exchanges_rates, calculated_volumes)

    calculated_global_average_rates, calculated_global_volume_percents = calculateAllGlobalAverages(calculated_average_rates,
                                                                                                    total_currency_volumes)

    (calculated_average_rates_formatted,
     calculated_volumes_formatted,
     calculated_global_average_rates_formatted) = formatDataForAPI(calculated_average_rates,
                                                                   calculated_volumes,
                                                                   total_currency_volumes,
                                                                   calculated_global_average_rates,
                                                                   calculated_global_volume_percents)

    human_timestamp = utils.formatdate(time.time())
    writeAPIFiles(ba.server.API_DOCUMENT_ROOT,
                  human_timestamp,
                  calculated_average_rates_formatted,
                  calculated_volumes_formatted,
                  calculated_global_average_rates_formatted,
                  exchanges_ignored)

    api_custom_writers.createCustomAPIs(ba.server.API_DOCUMENT_ROOT,
                                        human_timestamp,
                                        calculated_average_rates_formatted,
                                        calculated_volumes_formatted,
                                        calculated_global_average_rates_formatted,
                                        exchanges_ignored)


    if last_fiat_exchange_rate_update < int(time.time())-FIAT_RATES_QUERY_FREQUENCY:
        helpers.write_sitemap()
        last_fiat_exchange_rate_update = int(time.time())

    cycle_time = int(time.time()) - start_time
    sleep_time = max(0, API_WRITE_FREQUENCY - cycle_time)
    logger.info("{timestamp}, spent {spent}s, sleeping {sleep}s - api daemon".format(
        timestamp=human_timestamp,
        spent=cycle_time,
        sleep=str(sleep_time)))

    time.sleep(sleep_time)

########NEW FILE########
__FILENAME__ = api_calculations
import os
import subprocess
import sys
import csv
from copy import deepcopy
import StringIO
from decimal import Decimal, InvalidOperation
import simplejson
from eventlet.green import urllib2
from eventlet.green import httplib
from eventlet.timeout import Timeout
import socket
import json
import logging

import bitcoinaverage as ba
import bitcoinaverage.server as server
from bitcoinaverage.config import DEC_PLACES, API_CALL_TIMEOUT_THRESHOLD, API_REQUEST_HEADERS, CURRENCY_LIST, API_FILES, EXCHANGE_LIST, INDEX_DOCUMENT_NAME
from bitcoinaverage.exceptions import CallTimeoutException
import bitcoinaverage.helpers as helpers

logger = logging.getLogger(__name__)


def get24hAverage(currency_code):
    history_currency_API_24h_path = "{0}/per_minute_24h_sliding_window.csv".format(
        getattr(server, "API_INDEX_URL_HISTORY_OVERRIDE", server.API_INDEX_URL_HISTORY) + currency_code)

    try:
        with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
            csv_result = urllib2.urlopen(urllib2.Request(url=history_currency_API_24h_path, headers=API_REQUEST_HEADERS)).read()
    except (
            KeyError,
            ValueError,
            socket.error,
            simplejson.decoder.JSONDecodeError,
            urllib2.URLError,
            httplib.BadStatusLine,
            CallTimeoutException) as error:
        logger.error("can not get history data from {0}: {1}".format(
            history_currency_API_24h_path,
            str(error)))
        return DEC_PLACES

    csvfile = StringIO.StringIO(csv_result)
    csvreader = csv.reader(csvfile, delimiter=',')
    price_sum = DEC_PLACES
    index = 0
    header_passed = False
    for row in csvreader:
        if not header_passed:
            header_passed = True
            continue
        try:
            price_sum = price_sum + Decimal(row[1])
            index = index + 1
        except (IndexError, InvalidOperation):
            continue
    try:
        average_price = (price_sum / Decimal(index)).quantize(DEC_PLACES)
    except InvalidOperation:
        average_price = DEC_PLACES

    return average_price

def get24hGlobalAverage(currency_code):

    if currency_code not in CURRENCY_LIST:
        return DEC_PLACES

    history_currency_API_24h_path = "{0}/per_minute_24h_global_average_sliding_window.csv".format(
        getattr(server, "API_INDEX_URL_HISTORY_OVERRIDE", server.API_INDEX_URL_HISTORY) + currency_code)

    try:
        with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
            csv_result = urllib2.urlopen(urllib2.Request(url=history_currency_API_24h_path, headers=API_REQUEST_HEADERS)).read()
    except (
            KeyError,
            ValueError,
            socket.error,
            simplejson.decoder.JSONDecodeError,
            urllib2.URLError,
            httplib.BadStatusLine,
            CallTimeoutException) as error:
        logger.error("can not get history data from {0}: {1}".format(
            history_currency_API_24h_path,
            str(error)))
        return DEC_PLACES

    csvfile = StringIO.StringIO(csv_result)
    csvreader = csv.reader(csvfile, delimiter=',')
    price_sum = DEC_PLACES
    index = 0
    header_passed = False
    for row in csvreader:
        if not header_passed:
            header_passed = True
            continue
        try:
            price_sum = price_sum + Decimal(row[len(row)-1])
            index = index + 1
        except (IndexError, InvalidOperation):
            continue
    try:
        average_price = (price_sum / Decimal(index)).quantize(DEC_PLACES)
    except InvalidOperation:
        average_price = DEC_PLACES

    return average_price

#calculates global average for all possible currencies
def calculateAllGlobalAverages(calculated_average_rates, total_currency_volumes):
    def getCurrencyCrossRate(currency_from, currency_to):
        if currency_from == currency_to:
            return Decimal(1)

        rate_from = Decimal(fiat_currencies_list[currency_from]['rate'])
        rate_to = Decimal(fiat_currencies_list[currency_to]['rate'])
        return (rate_from / rate_to)

    fiat_exchange_rates_url = server.API_INDEX_URL + 'fiat_data'
    try:
        with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
            result = urllib2.urlopen(urllib2.Request(url=fiat_exchange_rates_url, headers=API_REQUEST_HEADERS)).read()
            fiat_currencies_list = json.loads(result)
    except (KeyError,ValueError,socket.error,simplejson.decoder.JSONDecodeError,urllib2.URLError,httplib.BadStatusLine,CallTimeoutException):
        return {}, {}

    global_volume = DEC_PLACES
    for currency in CURRENCY_LIST:
        global_volume = global_volume + total_currency_volumes[currency]

    global_volume_percents = {}
    for currency in CURRENCY_LIST:
        global_volume_percents[currency] = (total_currency_volumes[currency] / global_volume * Decimal(100)).quantize(DEC_PLACES)

    global_averages = {}
    for currency_local in fiat_currencies_list:
        global_averages[currency_local] = {'last': DEC_PLACES,
                                           'ask': DEC_PLACES,
                                           'bid': DEC_PLACES,
                                            }
        for currency_to_convert in CURRENCY_LIST:
            global_averages[currency_local]['last'] = ( global_averages[currency_local]['last']
                                                + (calculated_average_rates[currency_to_convert]['last']
                                                   * global_volume_percents[currency_to_convert] / Decimal(100)
                                                   * getCurrencyCrossRate(currency_local, currency_to_convert) )
                                                        )
            global_averages[currency_local]['bid'] = ( global_averages[currency_local]['bid']
                                                + (calculated_average_rates[currency_to_convert]['bid']
                                                   * global_volume_percents[currency_to_convert] / Decimal(100)
                                                   * getCurrencyCrossRate(currency_local, currency_to_convert) )
                                                        )
            global_averages[currency_local]['ask'] = ( global_averages[currency_local]['ask']
                                                + (calculated_average_rates[currency_to_convert]['ask']
                                                   * global_volume_percents[currency_to_convert] / Decimal(100)
                                                   * getCurrencyCrossRate(currency_local, currency_to_convert) )
                                                        )
        global_averages[currency_local]['last'] = global_averages[currency_local]['last'].quantize(DEC_PLACES)
        global_averages[currency_local]['bid'] = global_averages[currency_local]['bid'].quantize(DEC_PLACES)
        global_averages[currency_local]['ask'] = global_averages[currency_local]['ask'].quantize(DEC_PLACES)
        currency_local_24h_avg = get24hGlobalAverage(currency_local)
        if currency_local_24h_avg > DEC_PLACES:
            global_averages[currency_local]['24h_avg'] = currency_local_24h_avg

    return global_averages, global_volume_percents


def calculateTotalVolumes(exchanges_rates):
    total_currency_volumes = {}
    total_currency_volumes_ask = {}
    total_currency_volumes_bid = {}
    for currency in CURRENCY_LIST:
        total_currency_volumes[currency] = DEC_PLACES
        total_currency_volumes_ask[currency] = DEC_PLACES
        total_currency_volumes_bid[currency] = DEC_PLACES

    for i, rate in enumerate(exchanges_rates):
        for currency in CURRENCY_LIST:
            if currency in rate:
                if rate[currency]['volume'] is not None and rate[currency]['volume'] > 0:
                    total_currency_volumes[currency] = total_currency_volumes[currency] + rate[currency]['volume']
                    if rate[currency]['ask'] is not None:
                        total_currency_volumes_ask[currency] = total_currency_volumes_ask[currency] + rate[currency]['volume']
                    if rate[currency]['bid'] is not None:
                        total_currency_volumes_bid[currency] = total_currency_volumes_bid[currency] + rate[currency]['volume']
                else:
                    pass
                    # del exchanges_rates[i][currency]
                    # i think we should not hide exchanges with 0 volume, it should be just zeroed, but still shown. @AlexyKot

    for currency in CURRENCY_LIST:
        total_currency_volumes[currency] = total_currency_volumes[currency].quantize(DEC_PLACES)
        total_currency_volumes_ask[currency] = total_currency_volumes_ask[currency].quantize(DEC_PLACES)
        total_currency_volumes_bid[currency] = total_currency_volumes_bid[currency].quantize(DEC_PLACES)

    return total_currency_volumes, total_currency_volumes_ask, total_currency_volumes_bid


def calculateRelativeVolumes(exchanges_rates, total_currency_volumes, total_currency_volumes_ask, total_currency_volumes_bid):
    calculated_volumes = {}
    for currency in CURRENCY_LIST:
        calculated_volumes[currency] = {}

    for rate in exchanges_rates:
        for currency in CURRENCY_LIST:
            if currency in rate:
                calculated_volumes[currency][rate['exchange_name']] = {}
                calculated_volumes[currency][rate['exchange_name']]['rates'] = {'ask': rate[currency]['ask'],
                                                                                'bid': rate[currency]['bid'],
                                                                                'last': rate[currency]['last'],
                                                                                    }
                calculated_volumes[currency][rate['exchange_name']]['source'] = rate['data_source']
                calculated_volumes[currency][rate['exchange_name']]['display_name'] = rate['exchange_display_name']
                try:
                    calculated_volumes[currency][rate['exchange_name']]['display_URL'] = rate['exchange_display_URL']
                except KeyError:
                    pass
                if calculated_volumes[currency][rate['exchange_name']]['rates']['last'] is not None:
                    calculated_volumes[currency][rate['exchange_name']]['rates']['last'].quantize(DEC_PLACES)

                if rate[currency]['volume'] is None:
                    rate[currency]['volume'] = DEC_PLACES
                calculated_volumes[currency][rate['exchange_name']]['volume_btc'] = rate[currency]['volume'].quantize(DEC_PLACES)

                if total_currency_volumes[currency] > 0:
                    calculated_volumes[currency][rate['exchange_name']]['volume_percent'] = (rate[currency]['volume']
                        / total_currency_volumes[currency] * Decimal(100) ).quantize(DEC_PLACES)
                else:
                    calculated_volumes[currency][rate['exchange_name']]['volume_percent'] = Decimal(0).quantize(DEC_PLACES)

                if calculated_volumes[currency][rate['exchange_name']]['rates']['ask'] is not None:
                    calculated_volumes[currency][rate['exchange_name']]['rates']['ask'].quantize(DEC_PLACES)
                    if total_currency_volumes[currency] > 0:
                        calculated_volumes[currency][rate['exchange_name']]['volume_percent_ask'] = (rate[currency]['volume']
                            / total_currency_volumes_ask[currency] * Decimal(100) ).quantize(DEC_PLACES)
                    else:
                        calculated_volumes[currency][rate['exchange_name']]['volume_percent_ask'] = Decimal(0).quantize(DEC_PLACES)

                if calculated_volumes[currency][rate['exchange_name']]['rates']['bid'] is not None:
                    calculated_volumes[currency][rate['exchange_name']]['rates']['bid'].quantize(DEC_PLACES)
                    if total_currency_volumes[currency] > 0:
                        calculated_volumes[currency][rate['exchange_name']]['volume_percent_bid'] = (rate[currency]['volume']
                            / total_currency_volumes_bid[currency] * Decimal(100) ).quantize(DEC_PLACES)
                    else:
                        calculated_volumes[currency][rate['exchange_name']]['volume_percent_bid'] = Decimal(0).quantize(DEC_PLACES)

    return calculated_volumes


def calculateAverageRates(exchanges_rates, calculated_volumes):
    calculated_average_rates = {}
    for currency in CURRENCY_LIST:
        calculated_average_rates[currency] = {'last': DEC_PLACES,
                                               'ask': DEC_PLACES,
                                               'bid': DEC_PLACES,
                                                }

    for rate in exchanges_rates:
        for currency in CURRENCY_LIST:
            if currency in rate:
                if rate[currency]['last'] is not None:
                    calculated_average_rates[currency]['last'] = ( calculated_average_rates[currency]['last']
                                                            + rate[currency]['last'] * calculated_volumes[currency][rate['exchange_name']]['volume_percent'] / Decimal(100) )
                if rate[currency]['ask'] is not None:
                    calculated_average_rates[currency]['ask'] = ( calculated_average_rates[currency]['ask']
                                                            + rate[currency]['ask'] * calculated_volumes[currency][rate['exchange_name']]['volume_percent_ask'] / Decimal(100) )
                if rate[currency]['bid'] is not None:
                    calculated_average_rates[currency]['bid'] = ( calculated_average_rates[currency]['bid']
                                                            + rate[currency]['bid'] * calculated_volumes[currency][rate['exchange_name']]['volume_percent_bid'] / Decimal(100) )

                calculated_average_rates[currency]['last'] = calculated_average_rates[currency]['last'].quantize(DEC_PLACES)
                calculated_average_rates[currency]['ask'] = calculated_average_rates[currency]['ask'].quantize(DEC_PLACES)
                calculated_average_rates[currency]['bid'] = calculated_average_rates[currency]['bid'].quantize(DEC_PLACES)

    return calculated_average_rates


def formatDataForAPI(calculated_average_rates, calculated_volumes, total_currency_volumes,
                     calculated_global_average_rates, calculated_global_volume_percents):
    for currency in CURRENCY_LIST:
        if currency in calculated_average_rates:
            try:
                calculated_average_rates[currency]['last'] = float(calculated_average_rates[currency]['last'])
            except TypeError:
                calculated_average_rates[currency]['last'] = str(calculated_average_rates[currency]['last'])
            try:
                calculated_average_rates[currency]['ask'] = float(calculated_average_rates[currency]['ask'])
            except TypeError:
                calculated_average_rates[currency]['ask'] = str(calculated_average_rates[currency]['ask'])
            try:
                calculated_average_rates[currency]['bid'] = float(calculated_average_rates[currency]['bid'])
            except TypeError:
                calculated_average_rates[currency]['bid'] = str(calculated_average_rates[currency]['bid'])
            try:
                calculated_average_rates[currency]['total_vol'] = float(total_currency_volumes[currency])
            except TypeError:
                calculated_average_rates[currency]['total_vol'] = str(total_currency_volumes[currency])
            try:
                calculated_average_rates[currency]['24h_avg'] = float(get24hAverage(currency))
            except TypeError:
                calculated_average_rates[currency]['24h_avg'] = str(get24hAverage(currency))

        for exchange_name in EXCHANGE_LIST:
            if currency in calculated_volumes and exchange_name in calculated_volumes[currency]:
                calculated_volumes[currency][exchange_name]['display_name'] = calculated_volumes[currency][exchange_name]['display_name']
                try:
                    calculated_volumes[currency][exchange_name]['rates']['last'] = float(calculated_volumes[currency][exchange_name]['rates']['last'])
                except TypeError:
                    calculated_volumes[currency][exchange_name]['rates']['last'] = str(calculated_volumes[currency][exchange_name]['rates']['last'])
                try:
                    calculated_volumes[currency][exchange_name]['rates']['ask'] = float(calculated_volumes[currency][exchange_name]['rates']['ask'])
                except TypeError:
                    calculated_volumes[currency][exchange_name]['rates']['ask'] = str(calculated_volumes[currency][exchange_name]['rates']['ask'])
                try:
                    calculated_volumes[currency][exchange_name]['rates']['bid'] = float(calculated_volumes[currency][exchange_name]['rates']['bid'])
                except TypeError:
                    calculated_volumes[currency][exchange_name]['rates']['bid'] = str(calculated_volumes[currency][exchange_name]['rates']['bid'])
                try:
                    calculated_volumes[currency][exchange_name]['volume_btc'] = float(calculated_volumes[currency][exchange_name]['volume_btc'])
                except TypeError:
                    calculated_volumes[currency][exchange_name]['volume_btc'] = str(calculated_volumes[currency][exchange_name]['volume_btc'])
                try:
                    calculated_volumes[currency][exchange_name]['volume_percent'] = float(calculated_volumes[currency][exchange_name]['volume_percent'])
                except TypeError:
                    calculated_volumes[currency][exchange_name]['volume_percent'] = str(calculated_volumes[currency][exchange_name]['volume_percent'])

                if 'volume_percent_ask' in calculated_volumes[currency][exchange_name]:
                    del calculated_volumes[currency][exchange_name]['volume_percent_ask']
                if 'volume_percent_bid' in calculated_volumes[currency][exchange_name]:
                    del calculated_volumes[currency][exchange_name]['volume_percent_bid']

    for currency in calculated_global_average_rates:
        try:
            calculated_global_average_rates[currency]['last'] = float(calculated_global_average_rates[currency]['last'])
        except TypeError:
            calculated_global_average_rates[currency]['last'] = str(calculated_global_average_rates[currency]['last'])
        try:
            calculated_global_average_rates[currency]['ask'] = float(calculated_global_average_rates[currency]['ask'])
        except TypeError:
            calculated_global_average_rates[currency]['ask'] = str(calculated_global_average_rates[currency]['ask'])
        try:
            calculated_global_average_rates[currency]['bid'] = float(calculated_global_average_rates[currency]['bid'])
        except TypeError:
            calculated_global_average_rates[currency]['bid'] = str(calculated_global_average_rates[currency]['bid'])
        try:
            calculated_global_average_rates[currency]['24h_avg'] = float(calculated_global_average_rates[currency]['24h_avg'])
        except TypeError:
            calculated_global_average_rates[currency]['24h_avg'] = str(calculated_global_average_rates[currency]['24h_avg'])
        except KeyError:
            pass

        if currency in CURRENCY_LIST:
            try:
                calculated_global_average_rates[currency]['volume_btc'] = float(total_currency_volumes[currency])
            except TypeError:
                calculated_global_average_rates[currency]['volume_btc'] = str(total_currency_volumes[currency])
            try:
                calculated_global_average_rates[currency]['volume_percent'] = float(calculated_global_volume_percents[currency])
            except TypeError:
                calculated_global_average_rates[currency]['volume_percent'] = str(calculated_global_volume_percents[currency])
        else:
            calculated_global_average_rates[currency]['volume_btc'] = 0.0
            calculated_global_average_rates[currency]['volume_percent'] = 0.0
    return calculated_average_rates, calculated_volumes, calculated_global_average_rates


def writeAPIFiles(api_path, timestamp, calculated_average_rates_formatted, calculated_volumes_formatted,
                  calculated_global_average_rates_formatted, exchanges_ignored):
    try:
        # /all
        all_data = {}
        all_data['timestamp'] = timestamp
        all_data['ignored_exchanges'] = exchanges_ignored
        for currency in CURRENCY_LIST:
            if (currency in calculated_volumes_formatted
            and currency in calculated_average_rates_formatted
            and currency in calculated_global_average_rates_formatted):
                cur_data = {'exchanges': calculated_volumes_formatted[currency],
                            'averages': calculated_average_rates_formatted[currency],
                            'global_averages': calculated_global_average_rates_formatted[currency],
                            }
                all_data[currency] = cur_data

        helpers.write_api_file(
            os.path.join(api_path, API_FILES['ALL_FILE']),
            json.dumps(all_data,  indent=2, sort_keys=True, separators=(',', ': ')))

        # /ticker/*
        for currency in CURRENCY_LIST:
            if (currency in calculated_volumes_formatted and currency in calculated_average_rates_formatted
            and currency in calculated_global_average_rates_formatted):
                ticker_cur = calculated_average_rates_formatted[currency]
                ticker_cur['timestamp'] = timestamp
                ticker_currency_path = os.path.join(api_path, API_FILES['TICKER_PATH'], currency)
                helpers.write_api_file(
                    os.path.join(ticker_currency_path, INDEX_DOCUMENT_NAME),
                    json.dumps(ticker_cur, indent=2, sort_keys=True, separators=(',', ': ')))
                for key in ticker_cur:
                    helpers.write_api_file(
                        os.path.join(ticker_currency_path, key),
                        str(ticker_cur[key]),
                        compress=False)

        # /ticker/all
        rates_all = calculated_average_rates_formatted
        rates_all['timestamp'] = timestamp
        helpers.write_api_file(
            os.path.join(api_path, API_FILES['TICKER_PATH'], 'all'),
            json.dumps(rates_all, indent=2, sort_keys=True, separators=(',', ': ')))

        # /ticker/global/*
        for currency in calculated_global_average_rates_formatted:
            ticker_cur = calculated_global_average_rates_formatted[currency]
            ticker_cur['timestamp'] = timestamp
            ticker_currency_path = os.path.join(api_path, API_FILES['GLOBAL_TICKER_PATH'], currency)
            helpers.write_api_file(
                os.path.join(ticker_currency_path, INDEX_DOCUMENT_NAME),
                json.dumps(ticker_cur, indent=2, sort_keys=True, separators=(',', ': ')))
            for key in ticker_cur:
                helpers.write_api_file(
                    os.path.join(ticker_currency_path, key),
                    str(ticker_cur[key]),
                    compress=False)

        # /ticker/global/all
        rates_all = calculated_global_average_rates_formatted
        rates_all['timestamp'] = timestamp
        try:
            helpers.write_api_file(
                os.path.join(api_path, API_FILES['GLOBAL_TICKER_PATH'], 'all'),
                json.dumps(rates_all, indent=2, sort_keys=True, separators=(',', ': ')))
        except IOError as error:
            #pass on Windows if there is currency with code ALL and it will interfer with file called 'all'
            pass

        # /exchanges/all
        volumes_all = calculated_volumes_formatted
        volumes_all['timestamp'] = timestamp
        helpers.write_api_file(
            os.path.join(api_path, API_FILES['EXCHANGES_PATH'], 'all'),
            json.dumps(volumes_all, indent=2, sort_keys=True, separators=(',', ': ')))

        # /exchanges/*
        for currency in CURRENCY_LIST:
            if (currency in calculated_volumes_formatted and currency in calculated_average_rates_formatted
                and currency in calculated_global_average_rates_formatted):
                volume_cur = calculated_volumes_formatted[currency]
                volume_cur['timestamp'] = timestamp
                helpers.write_api_file(
                    os.path.join(api_path, API_FILES['EXCHANGES_PATH'], currency),
                    json.dumps(volume_cur,  indent=2, sort_keys=True, separators=(',', ': ')))

        # /ignored
        helpers.write_api_file(
            os.path.join(api_path, API_FILES['IGNORED_FILE']),
            json.dumps(exchanges_ignored,  indent=2, sort_keys=True, separators=(',', ': ')))

    except IOError as error:
        error_text = '%s, %s ' % (sys.exc_info()[0], error)
        logger.error(error_text)
        raise error

########NEW FILE########
__FILENAME__ = api_custom_writers
import os
import subprocess
import sys
import csv
from copy import deepcopy
import StringIO
from decimal import Decimal, InvalidOperation
import simplejson
from eventlet.green import urllib2
from eventlet.green import httplib
from eventlet.timeout import Timeout
import socket
import json

import bitcoinaverage as ba
import bitcoinaverage.server as server
from bitcoinaverage.config import DEC_PLACES, FRONTEND_MAJOR_CURRENCIES, CURRENCY_LIST, API_FILES, CUSTOM_API_FILES
from bitcoinaverage.exceptions import CallTimeoutException
import bitcoinaverage.helpers as helpers


def createCustomAPIs(api_document_root,
                     human_timestamp,
                     calculated_average_rates_formatted,
                     calculated_volumes_formatted,
                     calculated_global_average_rates_formatted,
                     exchanges_ignored):

    if not os.path.exists(os.path.join(api_document_root, API_FILES['CUSTOM_API'])):
        os.makedirs(os.path.join(api_document_root, API_FILES['CUSTOM_API']))

    globals_list = globals()
    for globals_item in globals_list:
        for custom_api_name in CUSTOM_API_FILES:
            if globals_item == '_writeCustomAPI_{}'.format(custom_api_name):
                globals()[globals_item](api_document_root,
                                         CUSTOM_API_FILES[custom_api_name],
                                         human_timestamp,
                                         calculated_average_rates_formatted,
                                         calculated_volumes_formatted,
                                         calculated_global_average_rates_formatted,
                                         exchanges_ignored)

def _writeCustomAPI_AndroidBitcoinWallet(api_path, api_file_name, human_timestamp, calculated_average_rates_formatted,
                                         calculated_volumes_formatted, calculated_global_average_rates_formatted,
                                         exchanges_ignored):

    result = {}
    major_currencies = []
    index = 0
    for currency_code in CURRENCY_LIST:
        major_currencies.append(currency_code)
        index = index + 1
        if index == FRONTEND_MAJOR_CURRENCIES:
            break

    for currency_code in calculated_global_average_rates_formatted:
        if "24h_avg" in calculated_global_average_rates_formatted[currency_code]:
            result[currency_code] = {'24h_avg': calculated_global_average_rates_formatted[currency_code]['24h_avg']}
        elif "last" in calculated_global_average_rates_formatted[currency_code]:
            result[currency_code] = {'last': calculated_global_average_rates_formatted[currency_code]['last']}

    helpers.write_api_file(
        os.path.join(api_path, API_FILES['CUSTOM_API'], api_file_name),
        json.dumps(result))

def _writeCustomAPI_HiveMacDesktopWallet(api_path, api_file_name, human_timestamp, calculated_average_rates_formatted,
                                         calculated_volumes_formatted, calculated_global_average_rates_formatted,
                                         exchanges_ignored):

    result = {}
    major_currencies = []
    index = 0
    for currency_code in CURRENCY_LIST:
        major_currencies.append(currency_code)
        index = index + 1
        if index == FRONTEND_MAJOR_CURRENCIES:
            break

    for currency_code in calculated_global_average_rates_formatted:
        if "24h_avg" in calculated_global_average_rates_formatted[currency_code]:
            result[currency_code] = {'24h_avg': calculated_global_average_rates_formatted[currency_code]['24h_avg']}
        elif "last" in calculated_global_average_rates_formatted[currency_code]:
            result[currency_code] = {'last': calculated_global_average_rates_formatted[currency_code]['last']}

    helpers.write_api_file(
        os.path.join(api_path, API_FILES['CUSTOM_API'], api_file_name),
        json.dumps(result))

def _writeCustomAPI_HiveAndroidWallet(api_path, api_file_name, human_timestamp, calculated_average_rates_formatted,
                                         calculated_volumes_formatted, calculated_global_average_rates_formatted,
                                         exchanges_ignored):

    result = {}
    major_currencies = []
    index = 0
    for currency_code in CURRENCY_LIST:
        major_currencies.append(currency_code)
        index = index + 1
        if index == FRONTEND_MAJOR_CURRENCIES:
            break

    for currency_code in calculated_global_average_rates_formatted:
        if "24h_avg" in calculated_global_average_rates_formatted[currency_code]:
            result[currency_code] = {'24h_avg': calculated_global_average_rates_formatted[currency_code]['24h_avg']}
        elif "last" in calculated_global_average_rates_formatted[currency_code]:
            result[currency_code] = {'last': calculated_global_average_rates_formatted[currency_code]['last']}

    helpers.write_api_file(
        os.path.join(api_path, API_FILES['CUSTOM_API'], api_file_name),
        json.dumps(result))

########NEW FILE########
__FILENAME__ = api_parsers
import email.utils
import json
import time
from decimal import Decimal, DivisionByZero
import datetime
import eventlet
from eventlet.green import urllib2
from eventlet.green import httplib
from eventlet.timeout import Timeout
import simplejson
import socket
import logging

from bitcoinaverage.bitcoinchart_fallback import getData
from bitcoinaverage.config import DEC_PLACES, API_QUERY_FREQUENCY, API_IGNORE_TIMEOUT, API_REQUEST_HEADERS, EXCHANGE_LIST, API_CALL_TIMEOUT_THRESHOLD, CURRENCY_LIST
from bitcoinaverage.exceptions import CallTimeoutException, NoApiException, CacheTimeoutException
from bitcoinaverage.server import BITCOIN_DE_API_KEY

logger = logging.getLogger(__name__)

API_QUERY_CACHE = {} #holds last calls to APIs and last received data between calls


def callAll():
    """
    Concurrently collects data from exchanges 
    """
    pool = eventlet.GreenPool()

    exchanges_rates = []
    exchanges_ignored = {}

    for exchange_name, exchange_data, exchange_ignore_reason in pool.imap(callAPI, EXCHANGE_LIST):
        if exchange_ignore_reason is None:
            if exchange_data is not None:
                exchanges_rates.append(exchange_data)
        else:
            exchanges_ignored[exchange_name] = exchange_ignore_reason
    return exchanges_rates, exchanges_ignored


def callAPI(exchange_name):
    global API_QUERY_CACHE, API_QUERY_FREQUENCY, API_IGNORE_TIMEOUT, EXCHANGE_LIST

    current_timestamp = int(time.time())
    exchange_config = EXCHANGE_LIST[exchange_name]
    result = None
    exchange_ignore_reason = None

    if exchange_config.get('ignored') and 'ignore_reason' in exchange_config:
        exchange_ignore_reason = exchange_config['ignore_reason']
    else:

        if exchange_name not in API_QUERY_CACHE:
            API_QUERY_CACHE[exchange_name] = {
                'last_call': 0,
                'last_successful_call': 0,
                'result': None,
                'ignore_reason': None,
                'call_fail_count': 0,
            }

        exchange_query_frequency = API_QUERY_FREQUENCY.get(
            exchange_name,
            API_QUERY_FREQUENCY['_default'])
        if API_QUERY_CACHE[exchange_name]['last_call'] + exchange_query_frequency > current_timestamp:
            # Retrieve data from cache
            result = API_QUERY_CACHE[exchange_name]['result']
            if result is not None:
                result['data_source'] = 'cache'
            exchange_ignore_reason = API_QUERY_CACHE[exchange_name]['ignore_reason']

        else:
            # Call parser
            try:
                api_parser = globals().get('_{}ApiCall'.format(exchange_name))
                if api_parser is not None:
                    try:
                        result = api_parser(**exchange_config)
                        result['data_source'] = 'api'
                    except (
                            KeyError,
                            TypeError,
                            ValueError,
                            DivisionByZero,
                            simplejson.decoder.JSONDecodeError,
                            socket.error,
                            urllib2.URLError,
                            httplib.BadStatusLine,
                            httplib.IncompleteRead,
                            CallTimeoutException) as error:
                        if 'bitcoincharts_symbols' in exchange_config:
                            result = getData(exchange_config['bitcoincharts_symbols'])
                            result['data_source'] = 'bitcoincharts'
                        else:
                            raise error
                elif 'bitcoincharts_symbols' in exchange_config:
                    result = getData(exchange_config['bitcoincharts_symbols'])
                    result['data_source'] = 'bitcoincharts'
                else:
                    raise NoApiException
                # Update cache
                API_QUERY_CACHE[exchange_name] = {
                    'last_call': current_timestamp,
                    'last_successful_call': current_timestamp,
                    'result': result,
                    'ignore_reason': None,
                    'call_fail_count': 0,
                }
            except (
                    KeyError,
                    TypeError,
                    ValueError,
                    DivisionByZero,
                    socket.error,
                    simplejson.decoder.JSONDecodeError,
                    urllib2.URLError,
                    httplib.IncompleteRead,
                    httplib.BadStatusLine,
                    CallTimeoutException,
                    NoApiException) as error:
                API_QUERY_CACHE[exchange_name]['last_call'] = current_timestamp
                API_QUERY_CACHE[exchange_name]['call_fail_count'] = API_QUERY_CACHE[exchange_name]['call_fail_count'] + 1
                if (API_QUERY_CACHE[exchange_name]['last_successful_call'] + API_IGNORE_TIMEOUT > current_timestamp):
                    # Retrieve data from cache
                    result = API_QUERY_CACHE[exchange_name]['result']
                    result['data_source'] = 'cache'
                    log_message = "{0} call failed, {1}, {2} fails in a row, using cache, cache age {3}s".format(
                        exchange_name,
                        type(error).__name__,
                        str(API_QUERY_CACHE[exchange_name]['call_fail_count']),
                        str(current_timestamp - API_QUERY_CACHE[exchange_name]['last_successful_call']))
                    logger.warning(log_message)
                else:
                    # Ignore
                    last_successful_call = API_QUERY_CACHE[exchange_name]['last_successful_call']
                    if last_successful_call == 0:
                        last_successful_call_strdate = 'never'
                    else:
                        last_successful_call_strdate = email.utils.formatdate(last_successful_call)

                    log_message = "{0} call failed, {1}, {2} fails in a row, last successful call - {3}, cache timeout, exchange ignored".format(
                        exchange_name,
                        type(error).__name__,
                        str(API_QUERY_CACHE[exchange_name]['call_fail_count']),
                        last_successful_call_strdate)
                    logger.error(log_message)

                    last_successful_call_datetime = datetime.datetime.fromtimestamp(last_successful_call)
                    today = datetime.datetime.now()
                    if last_successful_call == 0:
                        last_successful_call_datetime_str = today.strftime('%H:%M')
                    elif (
                        last_successful_call_datetime.day == today.day
                        and last_successful_call_datetime.month == today.month
                    ):
                        last_successful_call_datetime_str = last_successful_call_datetime.strftime('%H:%M')
                    else:
                        last_successful_call_datetime_str = last_successful_call_datetime.strftime('%d %b, %H:%M')
                    exchange_ignore_reason = CacheTimeoutException.strerror % last_successful_call_datetime_str
                    API_QUERY_CACHE[exchange_name]['result'] = None
                    API_QUERY_CACHE[exchange_name]['ignore_reason'] = exchange_ignore_reason

    if result is not None:
        result['exchange_name'] = exchange_name
        result['exchange_display_name'] = exchange_config.get('display_name', exchange_name)
        try:
            result['exchange_display_URL'] = exchange_config['URL']
        except KeyError:
            pass

    return exchange_name, result, exchange_ignore_reason


def _bitstampApiCall(api_ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=api_ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    result = {}
    result['USD'] = {'ask': Decimal(ticker['ask']).quantize(DEC_PLACES),
                    'bid': Decimal(ticker['bid']).quantize(DEC_PLACES),
                    'last': Decimal(ticker['last']).quantize(DEC_PLACES),
                    'volume': Decimal(ticker['volume']).quantize(DEC_PLACES),
    }

    return result


def _campbxApiCall(api_ticker_url, api_trades_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=api_ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    last_24h_timestamp = int(time.time()-86400)
    api_trades_url = api_trades_url.format(timestamp_since=last_24h_timestamp)
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=api_trades_url, headers=API_REQUEST_HEADERS)).read()
        trades = json.loads(response)

    volume = Decimal(0)
    for trade in trades:
        try:
            if trade['date'] > last_24h_timestamp:
                volume = volume + Decimal(trade['amount'])
        except TypeError as error:
            logger.error("CampBX error: {0}".format(trade))
            raise error

    result = {}
    result['USD'] = {'ask': Decimal(ticker['Best Ask']).quantize(DEC_PLACES),
                     'bid': Decimal(ticker['Best Bid']).quantize(DEC_PLACES),
                     'last': Decimal(ticker['Last Trade']).quantize(DEC_PLACES),
                     'volume': Decimal(volume).quantize(DEC_PLACES),
                      }
    return result


def _btceApiCall(usd_api_url, eur_api_url, rur_api_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=usd_api_url, headers=API_REQUEST_HEADERS)).read()
        usd_result = json.loads(response)
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=eur_api_url, headers=API_REQUEST_HEADERS)).read()
        eur_result = json.loads(response)
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=rur_api_url, headers=API_REQUEST_HEADERS)).read()
        rur_result = json.loads(response)

    #dirty hack, BTC-e has a bug in their APIs - buy/sell prices mixed up
    if usd_result['ticker']['sell'] < usd_result['ticker']['buy']:
        temp = usd_result['ticker']['buy']
        usd_result['ticker']['buy'] = usd_result['ticker']['sell']
        usd_result['ticker']['sell'] = temp

    if eur_result['ticker']['sell'] < eur_result['ticker']['buy']:
        temp = eur_result['ticker']['buy']
        eur_result['ticker']['buy'] = eur_result['ticker']['sell']
        eur_result['ticker']['sell'] = temp

    if rur_result['ticker']['sell'] < rur_result['ticker']['buy']:
        temp = rur_result['ticker']['buy']
        rur_result['ticker']['buy'] = rur_result['ticker']['sell']
        rur_result['ticker']['sell'] = temp

    return {'USD': {'ask': Decimal(usd_result['ticker']['sell']).quantize(DEC_PLACES),
                    'bid': Decimal(usd_result['ticker']['buy']).quantize(DEC_PLACES),
                    'last': Decimal(usd_result['ticker']['last']).quantize(DEC_PLACES),
                    'volume': Decimal(usd_result['ticker']['vol_cur']).quantize(DEC_PLACES),
                    },
            'EUR': {'ask': Decimal(eur_result['ticker']['sell']).quantize(DEC_PLACES),
                    'bid': Decimal(eur_result['ticker']['buy']).quantize(DEC_PLACES),
                    'last': Decimal(eur_result['ticker']['last']).quantize(DEC_PLACES),
                    'volume': Decimal(eur_result['ticker']['vol_cur']).quantize(DEC_PLACES),
            },
            'RUB': {'ask': Decimal(rur_result['ticker']['sell']).quantize(DEC_PLACES),
                    'bid': Decimal(rur_result['ticker']['buy']).quantize(DEC_PLACES),
                    'last': Decimal(rur_result['ticker']['last']).quantize(DEC_PLACES),
                    'volume': Decimal(rur_result['ticker']['vol_cur']).quantize(DEC_PLACES),
            }}


def _bitcurexApiCall(eur_ticker_url, eur_trades_url, pln_ticker_url, pln_trades_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=eur_ticker_url, headers=API_REQUEST_HEADERS)).read()
        eur_result = json.loads(response)
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=pln_ticker_url, headers=API_REQUEST_HEADERS)).read()
        pln_result = json.loads(response)

    last24h_time = int(time.time())-86400  #86400s in 24h
    eur_vol = 0.0

    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=eur_trades_url, headers=API_REQUEST_HEADERS)).read()
        eur_volume_result = json.loads(response)
    for trade in eur_volume_result:
        if trade['date'] > last24h_time:
            eur_vol = eur_vol + float(trade['amount'])

    pln_vol = 0.0
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=pln_trades_url, headers=API_REQUEST_HEADERS)).read()
        pln_volume_result = json.loads(response)
    for trade in pln_volume_result:
        if trade['date'] > last24h_time:
            pln_vol = pln_vol + float(trade['amount'])

    return {'EUR': {'ask': Decimal(eur_result['sell']).quantize(DEC_PLACES),
                    'bid': Decimal(eur_result['buy']).quantize(DEC_PLACES),
                    'last': Decimal(eur_result['last']).quantize(DEC_PLACES),
                    'volume': Decimal(eur_vol).quantize(DEC_PLACES),
                    },
            'PLN': {'ask': Decimal(pln_result['sell']).quantize(DEC_PLACES),
                    'bid': Decimal(pln_result['buy']).quantize(DEC_PLACES),
                    'last': Decimal(pln_result['last']).quantize(DEC_PLACES),
                    'volume': Decimal(pln_vol).quantize(DEC_PLACES),
                    },
            }


def _vircurexApiCall(usd_api_url, eur_api_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=usd_api_url, headers=API_REQUEST_HEADERS)).read()
        usd_result = json.loads(response)

    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=eur_api_url, headers=API_REQUEST_HEADERS)).read()
        eur_result = json.loads(response)

    return {'USD': {'ask': Decimal(usd_result['lowest_ask']).quantize(DEC_PLACES),
                    'bid': Decimal(usd_result['highest_bid']).quantize(DEC_PLACES),
                    'last': Decimal(usd_result['last_trade']).quantize(DEC_PLACES),
                    'volume': Decimal(usd_result['volume']).quantize(DEC_PLACES),
                    },
            'EUR': {'ask': Decimal(eur_result['lowest_ask']).quantize(DEC_PLACES),
                    'bid': Decimal(eur_result['highest_bid']).quantize(DEC_PLACES),
                    'last': Decimal(eur_result['last_trade']).quantize(DEC_PLACES),
                    'volume': Decimal(eur_result['volume']).quantize(DEC_PLACES),
            },
    }


def _bitbargainApiCall(volume_api_url, ticker_api_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=volume_api_url, headers=API_REQUEST_HEADERS)).read()
        volume_data = json.loads(response)
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_api_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    if volume_data['response']['vol_24h'] is not None:
        average_btc = Decimal(ticker['response']['GBP']['avg_6h'])
        volume_btc = (Decimal(volume_data['response']['vol_24h']) / average_btc)
    else:
        average_btc = DEC_PLACES
        volume_btc = DEC_PLACES

    return {'GBP': {'ask': average_btc.quantize(DEC_PLACES), #bitbargain is an OTC trader, so ask == last == bid
                    'bid': average_btc.quantize(DEC_PLACES), #bitbargain is an OTC trader, so ask == last == bid
                    'last': average_btc.quantize(DEC_PLACES),
                    'volume': volume_btc.quantize(DEC_PLACES),
                    },
    }


def _localbitcoinsApiCall(api_url, *args, **kwargs):
    def _lbcParseCurrency(result, ticker, currency_code):
        try:
            volume = Decimal(ticker[currency_code]['volume_btc']).quantize(DEC_PLACES)
            if 'avg_3h' in ticker[currency_code] and ticker[currency_code]['avg_3h'] is not None:
                rate = Decimal(ticker[currency_code]['avg_3h']).quantize(DEC_PLACES)
            elif 'avg_12h' in ticker[currency_code] and ticker[currency_code]['avg_12h'] is not None:
                rate = Decimal(ticker[currency_code]['avg_12h']).quantize(DEC_PLACES)
            elif 'avg_24h' in ticker[currency_code] and ticker[currency_code]['avg_24h'] is not None:
                rate = Decimal(ticker[currency_code]['avg_24h']).quantize(DEC_PLACES)
            else:
                rate = None
                volume = None

            result[currency_code]= {'ask': rate,
                                    'bid': rate,
                                    'last': rate,
                                    'volume': volume,
                                    }
        except KeyError as error:
            pass

        return result

    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=api_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    result = {}
    for currencyCode in CURRENCY_LIST:
        result = _lbcParseCurrency(result, ticker, currencyCode)

    return result


def _cryptotradeApiCall(usd_api_url, #eur_api_url,
                        *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=usd_api_url, headers=API_REQUEST_HEADERS)).read()
        usd_result = json.loads(response)
    # with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
    #     response = urllib2.urlopen(urllib2.Request(url=eur_api_url, headers=API_REQUEST_HEADERS)).read()
    #     eur_result = json.loads(response)


    return {'USD': {'ask': Decimal(usd_result['data']['min_ask']).quantize(DEC_PLACES),
                    'bid': Decimal(usd_result['data']['max_bid']).quantize(DEC_PLACES),
                    'last': Decimal(usd_result['data']['last']).quantize(DEC_PLACES),
                    'volume': Decimal(usd_result['data']['vol_btc']).quantize(DEC_PLACES),
                                    },
            # 'EUR': {'ask': Decimal(eur_result['data']['min_ask']).quantize(DEC_PLACES),
            #         'bid': Decimal(eur_result['data']['max_bid']).quantize(DEC_PLACES),
            #         'last': Decimal(eur_result['data']['last']).quantize(DEC_PLACES),
            #         'volume': Decimal(eur_result['data']['vol_btc']).quantize(DEC_PLACES),
            #                         },
            }


def _rocktradingApiCall(usd_ticker_url, usd_trades_url,
                        eur_ticker_url, eur_trades_url, *args, **kwargs):
    last24h_time = int(time.time())-86400  #86400s in 24h

    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=usd_ticker_url, headers=API_REQUEST_HEADERS)).read()
        usd_ticker_result = json.loads(response)
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=usd_trades_url, headers=API_REQUEST_HEADERS)).read()
        usd_volume_result = json.loads(response)
    usd_last = 0.0
    usd_vol = 0.0
    for trade in usd_volume_result:
        if trade['date'] > last24h_time:
            usd_vol = usd_vol + float(trade['amount'])
            usd_last = float(trade['price'])

    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=eur_ticker_url, headers=API_REQUEST_HEADERS)).read()
        eur_ticker_result = json.loads(response)
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=eur_trades_url, headers=API_REQUEST_HEADERS)).read()
        eur_volume_result = json.loads(response)
    eur_last = 0.0
    eur_vol = 0.0
    for trade in eur_volume_result:
        if trade['date'] > last24h_time:
            eur_vol = eur_vol + float(trade['amount'])
            eur_last = float(trade['price'])

    return {
            'USD': {'ask': Decimal(usd_ticker_result['result'][0]['ask']).quantize(DEC_PLACES),
                    'bid': Decimal(usd_ticker_result['result'][0]['bid']).quantize(DEC_PLACES),
                    'last': Decimal(usd_last).quantize(DEC_PLACES),
                    'volume': Decimal(usd_vol).quantize(DEC_PLACES),
                                    },
            'EUR': {'ask': Decimal(eur_ticker_result['result'][0]['ask']).quantize(DEC_PLACES) if eur_ticker_result['result'][0]['ask'] is not None else None,
                    'bid': Decimal(eur_ticker_result['result'][0]['bid']).quantize(DEC_PLACES) if eur_ticker_result['result'][0]['bid'] is not None else None,
                    'last': Decimal(eur_last).quantize(DEC_PLACES),
                    'volume': Decimal(eur_vol).quantize(DEC_PLACES),
                                    },
            }



def _intersangoApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        result = json.loads(response)

    #'2' in here is ID for EUR in intersango terms
    return {'EUR': {'ask': Decimal(result['2']['sell']).quantize(DEC_PLACES) if result['2']['sell'] is not None else None,
                    'bid': Decimal(result['2']['buy']).quantize(DEC_PLACES) if result['2']['buy'] is not None else None,
                    'last': Decimal(result['2']['last']).quantize(DEC_PLACES) if result['2']['last'] is not None else None,
                    'volume': Decimal(result['2']['vol']).quantize(DEC_PLACES) if result['2']['vol'] is not None else DEC_PLACES,
                    },
            }


def _bit2cApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    result = {}
    try:
        result['ILS'] = {'ask': Decimal(ticker['l']).quantize(DEC_PLACES),
                         'bid': Decimal(ticker['h']).quantize(DEC_PLACES),
                         'last': Decimal(ticker['ll']).quantize(DEC_PLACES),
                         'volume': Decimal(ticker['a']).quantize(DEC_PLACES),
                        }

    except KeyError as error:
        pass

    return result

def _kapitonApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    return {'SEK': {'ask': Decimal(ticker['ask']).quantize(DEC_PLACES),
                    'bid': Decimal(ticker['bid']).quantize(DEC_PLACES),
                    'last': Decimal(ticker['price']).quantize(DEC_PLACES),
                    'volume': Decimal(ticker['vol']).quantize(DEC_PLACES),
                    },
            }


def _rmbtbApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    result = {}
    try:
        result['CNY'] = {'ask': Decimal(ticker['ticker']['sell']).quantize(DEC_PLACES),
                        'bid': Decimal(ticker['ticker']['buy']).quantize(DEC_PLACES),
                        'last': Decimal(ticker['ticker']['last']).quantize(DEC_PLACES),
                        'volume': Decimal(ticker['ticker']['vol']).quantize(DEC_PLACES),
                        }
    except KeyError as e:
        pass
    return result


def _btcchinaApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    return {'CNY': {'ask': Decimal(ticker['ticker']['sell']).quantize(DEC_PLACES),
                    'bid': Decimal(ticker['ticker']['buy']).quantize(DEC_PLACES),
                    'last': Decimal(ticker['ticker']['last']).quantize(DEC_PLACES),
                    'volume': Decimal(ticker['ticker']['vol']).quantize(DEC_PLACES),
                    },
            }


def _fxbtcApiCall(ticker_url, trades_url_template, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    timestamp_24h = int(time.time() - 86400)
    current_timestamp = timestamp_24h
    volume = DEC_PLACES
    index = 0
    while index < 20: #just for safety
        trades_url = trades_url_template.format(timestamp_sec=current_timestamp)
        with Timeout(5, CallTimeoutException):
            response = urllib2.urlopen(urllib2.Request(url=trades_url, headers=API_REQUEST_HEADERS)).read()
            trades = json.loads(response)

        for trade in trades['datas']:
            if timestamp_24h < int(trade['date']):
                volume = volume + Decimal(trade['vol'])
            if current_timestamp < int(trade['date']):
                current_timestamp = int(trade['date'])

        if len(trades['datas']) == 0:
            break

        index = index + 1

    return {'CNY': {'ask': Decimal(ticker['ticker']['ask']).quantize(DEC_PLACES),
                    'bid': Decimal(ticker['ticker']['bid']).quantize(DEC_PLACES),
                    'last': Decimal(ticker['ticker']['last_rate']).quantize(DEC_PLACES),
                    'volume': Decimal(volume).quantize(DEC_PLACES),
                    },
            }


def _bterApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    return {'CNY': {'ask': Decimal(ticker['sell']).quantize(DEC_PLACES),
                    'bid': Decimal(ticker['buy']).quantize(DEC_PLACES),
                    'last': Decimal(ticker['last']).quantize(DEC_PLACES),
                    'volume': Decimal(ticker['vol_btc']).quantize(DEC_PLACES),
                    },
            }


def _goxbtcApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    return {'CNY': {'ask': Decimal(ticker['sell']).quantize(DEC_PLACES),
                    'bid': Decimal(ticker['buy']).quantize(DEC_PLACES),
                    'last': Decimal(ticker['last']).quantize(DEC_PLACES),
                    'volume': Decimal(ticker['vol']).quantize(DEC_PLACES),
                    },
            }


def _okcoinApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    return {'CNY': {'ask': Decimal(ticker['ticker']['sell']).quantize(DEC_PLACES),
                    'bid': Decimal(ticker['ticker']['buy']).quantize(DEC_PLACES),
                    'last': Decimal(ticker['ticker']['last']).quantize(DEC_PLACES),
                    'volume': Decimal(ticker['ticker']['vol']).quantize(DEC_PLACES),
                    },
            }


def _mercadoApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    return {'BRL': {'ask': Decimal(ticker['ticker']['sell']).quantize(DEC_PLACES),
                    'bid': Decimal(ticker['ticker']['buy']).quantize(DEC_PLACES),
                    'last': Decimal(ticker['ticker']['last']).quantize(DEC_PLACES),
                    'volume': Decimal(ticker['ticker']['vol']).quantize(DEC_PLACES),
                    },
            }


def _bitxApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    return {'ZAR': {'ask': Decimal(ticker['ask']).quantize(DEC_PLACES),
                    'bid': Decimal(ticker['bid']).quantize(DEC_PLACES),
                    'last': Decimal(ticker['last_trade']).quantize(DEC_PLACES),
                    'volume': Decimal(ticker['rolling_24_hour_volume']).quantize(DEC_PLACES),
                    },
            }


def _btctradeApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    return {'CNY': {'ask': Decimal(ticker['sell']).quantize(DEC_PLACES),
                    'bid': Decimal(ticker['buy']).quantize(DEC_PLACES),
                    'last': Decimal(ticker['last']).quantize(DEC_PLACES),
                    'volume': Decimal(ticker['vol']).quantize(DEC_PLACES),
                    },
            }


def _justcoinApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    result = {}
    for currency_data in ticker:
        if currency_data['id'] == 'BTCUSD':
            result['USD'] = {'ask': Decimal(currency_data['ask']).quantize(DEC_PLACES) if currency_data['ask'] is not None else None,
                             'bid': Decimal(currency_data['bid']).quantize(DEC_PLACES) if currency_data['bid'] is not None else None,
                             'last': Decimal(currency_data['last']).quantize(DEC_PLACES) if currency_data['last'] is not None else None,
                             'volume': Decimal(currency_data['volume']).quantize(DEC_PLACES) if currency_data['volume'] is not None else DEC_PLACES,
                             }
        if currency_data['id'] == 'BTCEUR':
            result['EUR'] = {'ask': Decimal(currency_data['ask']).quantize(DEC_PLACES) if currency_data['ask'] is not None else None,
                             'bid': Decimal(currency_data['bid']).quantize(DEC_PLACES) if currency_data['bid'] is not None else None,
                             'last': Decimal(currency_data['last']).quantize(DEC_PLACES) if currency_data['last'] is not None else None,
                             'volume': Decimal(currency_data['volume']).quantize(DEC_PLACES) if currency_data['volume'] is not None else DEC_PLACES,
                             }
        if currency_data['id'] == 'BTCNOK':
            result['NOK'] = {'ask': Decimal(currency_data['ask']).quantize(DEC_PLACES) if currency_data['ask'] is not None else None,
                             'bid': Decimal(currency_data['bid']).quantize(DEC_PLACES) if currency_data['bid'] is not None else None,
                             'last': Decimal(currency_data['last']).quantize(DEC_PLACES) if currency_data['last'] is not None else None,
                             'volume': Decimal(currency_data['volume']).quantize(DEC_PLACES) if currency_data['volume'] is not None else DEC_PLACES,
                             }

    return result


def _krakenApiCall(usd_ticker_url, eur_ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        usd_response = urllib2.urlopen(urllib2.Request(url=usd_ticker_url, headers=API_REQUEST_HEADERS)).read()
        usd_ticker = json.loads(usd_response)
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        eur_response = urllib2.urlopen(urllib2.Request(url=eur_ticker_url, headers=API_REQUEST_HEADERS)).read()
        eur_ticker = json.loads(eur_response)

    result = {}
    result['USD'] = {'ask': Decimal(usd_ticker['result']['XXBTZUSD']['a'][0]).quantize(DEC_PLACES),
                     'bid': Decimal(usd_ticker['result']['XXBTZUSD']['b'][0]).quantize(DEC_PLACES),
                     'last': Decimal(usd_ticker['result']['XXBTZUSD']['c'][0]).quantize(DEC_PLACES),
                     'volume': Decimal(usd_ticker['result']['XXBTZUSD']['v'][1]).quantize(DEC_PLACES),
                     }
    result['EUR'] = {'ask': Decimal(eur_ticker['result']['XXBTZEUR']['a'][0]).quantize(DEC_PLACES),
                     'bid': Decimal(eur_ticker['result']['XXBTZEUR']['b'][0]).quantize(DEC_PLACES),
                     'last': Decimal(eur_ticker['result']['XXBTZEUR']['c'][0]).quantize(DEC_PLACES),
                     'volume': Decimal(eur_ticker['result']['XXBTZEUR']['v'][1]).quantize(DEC_PLACES),
                     }
    return result


def _bitkonanApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    result = {}
    result['USD'] = {'ask': Decimal(ticker['ask']).quantize(DEC_PLACES),
                     'bid': Decimal(ticker['bid']).quantize(DEC_PLACES),
                     'last': Decimal(ticker['last']).quantize(DEC_PLACES),
                     'volume': Decimal(ticker['volume']).quantize(DEC_PLACES),
                     }
    return result


def _bittyliciousApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    result = {}
    try:
        volume = Decimal(ticker['GBPBTC']['volume_24h']).quantize(DEC_PLACES)
        if ticker['GBPBTC']['avg_6h'] is not None:
            rate = Decimal(ticker['GBPBTC']['avg_6h']).quantize(DEC_PLACES)
        elif ticker['GBPBTC']['avg_12h'] is not None:
            rate = Decimal(ticker['GBPBTC']['avg_12h']).quantize(DEC_PLACES)
        elif ticker['GBPBTC']['avg_24h'] is not None:
            rate = Decimal(ticker['GBPBTC']['avg_24h']).quantize(DEC_PLACES)
        else:
            rate = None
            volume = None
        result['GBP']= {'ask': rate,
                        'bid': rate,
                        'last': rate,
                        'volume': volume,
                        }
    except KeyError as error:
        pass

    try:
        volume = Decimal(ticker['EURBTC']['volume_24h']).quantize(DEC_PLACES)
        if ticker['EURBTC']['avg_6h'] is not None:
            rate = Decimal(ticker['EURBTC']['avg_6h']).quantize(DEC_PLACES)
        elif ticker['EURBTC']['avg_12h'] is not None:
            rate = Decimal(ticker['EURBTC']['avg_12h']).quantize(DEC_PLACES)
        elif ticker['EURBTC']['avg_24h'] is not None:
            rate = Decimal(ticker['EURBTC']['avg_24h']).quantize(DEC_PLACES)
        else:
            rate = None
            volume = None
        if volume is not None and volume > 0:
            result['EUR']= {'ask': rate,
                            'bid': rate,
                            'last': rate,
                            'volume': volume,
                            }
    except KeyError as error:
        pass

    return result


def _bitxfApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    result = {}
    result['CNY'] = {'ask': Decimal(ticker['sell']).quantize(DEC_PLACES),
                     'bid': Decimal(ticker['buy']).quantize(DEC_PLACES),
                     'last': Decimal(ticker['last_trade']['price']).quantize(DEC_PLACES),
                     'volume': Decimal(ticker['volume']).quantize(DEC_PLACES),
                     }

    return result


def _cavirtexApiCall(ticker_url, orderbook_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=orderbook_url, headers=API_REQUEST_HEADERS)).read()
        orderbook = json.loads(response)


    bid = 0
    for bid_order in orderbook['bids']:
        if bid < bid_order[0] or bid == 0:
            bid = bid_order[0]

    ask = 0
    for ask_order in orderbook['asks']:
        if ask > ask_order[0] or ask == 0:
            ask = ask_order[0]

    bid = Decimal(bid).quantize(DEC_PLACES)
    ask = Decimal(ask).quantize(DEC_PLACES)
    result = {}
    result['CAD'] = {'ask': ask,
                     'bid': bid,
                     'last': Decimal(ticker['last']).quantize(DEC_PLACES),
                     'volume': Decimal(ticker['volume']).quantize(DEC_PLACES),
                     }

    return result


def _bitfinexApiCall(ticker_url, today_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=today_url, headers=API_REQUEST_HEADERS)).read()
        today = json.loads(response)

    result = {}
    result['USD'] = {'ask': Decimal(ticker['ask']).quantize(DEC_PLACES),
                     'bid': Decimal(ticker['bid']).quantize(DEC_PLACES),
                     'last': Decimal(ticker['last_price']).quantize(DEC_PLACES),
                     'volume': Decimal(today['volume']).quantize(DEC_PLACES),
                     }

    return result


def _fybsgApiCall(ticker_url, trades_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=trades_url, headers=API_REQUEST_HEADERS)).read()
        trades = json.loads(response)

    ask = Decimal(ticker['ask']).quantize(DEC_PLACES)
    bid = Decimal(ticker['bid']).quantize(DEC_PLACES)

    volume = DEC_PLACES
    last24h_timestamp = time.time() - 86400
    last_price = 0
    last_trade_timestamp = 0
    for trade in trades:
        if trade['date'] >= last24h_timestamp:
            volume = volume + Decimal(trade['amount'])
        if trade['date'] > last_trade_timestamp:
            last_trade_timestamp = trade['date']
            last_price = trade['price']
    last_price = Decimal(last_price).quantize(DEC_PLACES)

    result = {}
    result['SGD'] = {'ask': ask,
                     'bid': bid,
                     'last': last_price,
                     'volume': volume,
                     }

    return result


def _fybseApiCall(ticker_url, trades_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=trades_url, headers=API_REQUEST_HEADERS)).read()
        trades = json.loads(response)

    ask = Decimal(ticker['ask']).quantize(DEC_PLACES)
    bid = Decimal(ticker['bid']).quantize(DEC_PLACES)

    volume = DEC_PLACES
    last24h_timestamp = time.time() - 86400
    last_price = 0
    last_trade_timestamp = 0
    for trade in trades:
        if trade['date'] >= last24h_timestamp:
            volume = volume + Decimal(trade['amount'])
        if trade['date'] > last_trade_timestamp:
            last_trade_timestamp = trade['date']
            last_price = trade['price']
    last_price = Decimal(last_price).quantize(DEC_PLACES)

    result = {}
    result['SEK'] = {'ask': ask,
                     'bid': bid,
                     'last': last_price,
                     'volume': volume,
                     }
    return result


def _bitcoin_deApiCall(rates_url, trades_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        rates_url = rates_url.format(api_key=BITCOIN_DE_API_KEY)
        response = urllib2.urlopen(urllib2.Request(url=rates_url, headers=API_REQUEST_HEADERS)).read()
        rates = json.loads(response)
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        trades_url = trades_url.format(api_key=BITCOIN_DE_API_KEY)
        response = urllib2.urlopen(urllib2.Request(url=trades_url, headers=API_REQUEST_HEADERS)).read()
        trades = json.loads(response)

    result = {}
    if 'rate_weighted_3h' in rates:
        last_avg_price = Decimal(rates['rate_weighted_3h']).quantize(DEC_PLACES)
    elif 'rate_weighted_12h' in rates:
        last_avg_price = Decimal(rates['rate_weighted_12h']).quantize(DEC_PLACES)
    else:
        return result


    volume = DEC_PLACES
    last24h_timestamp = time.time() - 86400
    for trade in trades:
        if trade['date'] >= last24h_timestamp:
            volume = volume + Decimal(trade['amount'])

    result['EUR'] = {'ask': last_avg_price,
                     'bid': last_avg_price,
                     'last': last_avg_price,
                     'volume': volume,
                     }

    return result


def _bitcoin_centralApiCall(ticker_url, depth_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    result = {}
    result['EUR'] = {'ask': Decimal(ticker['ask']).quantize(DEC_PLACES),
                     'bid': Decimal(ticker['bid']).quantize(DEC_PLACES),
                     'last': Decimal(ticker['price']).quantize(DEC_PLACES),
                     'volume': Decimal(ticker['volume']).quantize(DEC_PLACES),
                     }
    return result


def _btcturkApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    result = {}
    result['TRY'] = {'ask': Decimal(ticker['ask']).quantize(DEC_PLACES),
                     'bid': Decimal(ticker['bid']).quantize(DEC_PLACES),
                     'last': Decimal(ticker['last']).quantize(DEC_PLACES),
                     'volume': Decimal(ticker['volume']).quantize(DEC_PLACES),
                     }
    return result


def _bitonicApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    result = {}
    result['EUR'] = {'ask': Decimal(ticker['price']).quantize(DEC_PLACES),
                     'bid': Decimal(ticker['price']).quantize(DEC_PLACES),
                     'last': Decimal(ticker['price']).quantize(DEC_PLACES),
                     'volume': Decimal(ticker['volume']).quantize(DEC_PLACES),
                     }
    return result


def _itbitApiCall(usd_orders_url, usd_trades_url,
                  sgd_orders_url, sgd_trades_url,
                  eur_orders_url, eur_trades_url,
                  since_trade_id, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=usd_orders_url, headers=API_REQUEST_HEADERS)).read()
        usd_orders = json.loads(response)
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=sgd_orders_url, headers=API_REQUEST_HEADERS)).read()
        sgd_orders = json.loads(response)
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=eur_orders_url, headers=API_REQUEST_HEADERS)).read()
        eur_orders = json.loads(response)

    def _get_all_trades(trades_url, since_trade_id):
        trades_url = trades_url.format(trade_id=since_trade_id)
        with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
            response = urllib2.urlopen(urllib2.Request(url=trades_url, headers=API_REQUEST_HEADERS)).read()
            new_trades = json.loads(response)

        last_24h_timestamp = int(time.time())-86400
        last_trade_id = since_trade_id
        trades_list = []
        for trade in new_trades:
            if int(trade['date']) > last_24h_timestamp:
                trades_list.append(trade)
            if last_trade_id < int(trade['tid']):
                last_trade_id = int(trade['tid'])
        return trades_list, last_trade_id

    def __calculate(trades_url, since_trade_id, orders):
        volume = DEC_PLACES
        last_24h_timestamp = int(time.time())-86400
        last_trade_timestamp = 0
        last_trade_price = DEC_PLACES

        trades = []
        for i in range(10): #no more than ten requests to API, random "magic" figure
            new_trades, last_trade_id = _get_all_trades(trades_url, since_trade_id)
            if len(new_trades) == 0:
                break

            trades = trades + new_trades
            since_trade_id = last_trade_id

        for trade in trades:
            if int(trade['date']) > last_24h_timestamp:
                volume = volume + Decimal(trade['amount'])
            if int(trade['date']) > last_trade_timestamp:
                last_trade_price = trade['price']

        bid = 0.0
        for bid_order in orders['bids']:
            if bid < float(bid_order[0]) or bid == 0.0:
                bid = float(bid_order[0])

        ask = 0.0
        for ask_order in orders['asks']:
            if ask > float(ask_order[0]) or ask == 0.0:
                ask = float(ask_order[0])


        return {'ask': Decimal(ask).quantize(DEC_PLACES),
                'bid': Decimal(bid).quantize(DEC_PLACES),
                'last': Decimal(last_trade_price).quantize(DEC_PLACES),
                'volume': Decimal(volume).quantize(DEC_PLACES),
                     }

    result = {}
    result['USD']= __calculate(usd_trades_url, since_trade_id, usd_orders)
    result['SGD']= __calculate(sgd_trades_url, since_trade_id, sgd_orders)
    result['EUR']= __calculate(eur_trades_url, since_trade_id, eur_orders)
    return result


def _vaultofsatoshiApiCall(usd_ticker_url, eur_ticker_url, cad_ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=usd_ticker_url, headers=API_REQUEST_HEADERS)).read()
        usd_ticker = json.loads(response)
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=eur_ticker_url, headers=API_REQUEST_HEADERS)).read()
        eur_ticker = json.loads(response)
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=cad_ticker_url, headers=API_REQUEST_HEADERS)).read()
        cad_ticker = json.loads(response)


    result = {}
    if float(usd_ticker['data']['volume_1day']['value']) > 0:
        result['USD'] = {'ask': Decimal(usd_ticker['data']['closing_price']['value']).quantize(DEC_PLACES),
                         'bid': Decimal(usd_ticker['data']['closing_price']['value']).quantize(DEC_PLACES),
                         'last': Decimal(usd_ticker['data']['closing_price']['value']).quantize(DEC_PLACES),
                         'volume': Decimal(usd_ticker['data']['volume_1day']['value']).quantize(DEC_PLACES),
                         }
    if float(eur_ticker['data']['volume_1day']['value']) > 0:
        result['EUR'] = {'ask': Decimal(eur_ticker['data']['closing_price']['value']).quantize(DEC_PLACES),
                         'bid': Decimal(eur_ticker['data']['closing_price']['value']).quantize(DEC_PLACES),
                         'last': Decimal(eur_ticker['data']['closing_price']['value']).quantize(DEC_PLACES),
                         'volume': Decimal(eur_ticker['data']['volume_1day']['value']).quantize(DEC_PLACES),
                         }
    if float(cad_ticker['data']['volume_1day']['value']) > 0:
        result['CAD'] = {'ask': Decimal(cad_ticker['data']['closing_price']['value']).quantize(DEC_PLACES),
                         'bid': Decimal(cad_ticker['data']['closing_price']['value']).quantize(DEC_PLACES),
                         'last': Decimal(cad_ticker['data']['closing_price']['value']).quantize(DEC_PLACES),
                         'volume': Decimal(cad_ticker['data']['volume_1day']['value']).quantize(DEC_PLACES),
                         }
    return result


def _quickbitcoinApiCall(gbp_ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=gbp_ticker_url, headers=API_REQUEST_HEADERS)).read()
        gbp_ticker = json.loads(response)

    result = {}
    result['GBP'] = {'ask': Decimal(gbp_ticker['sell']).quantize(DEC_PLACES),
                     'bid': Decimal(gbp_ticker['sell']).quantize(DEC_PLACES),
                     'last': Decimal(gbp_ticker['sell']).quantize(DEC_PLACES),
                     'volume': Decimal(gbp_ticker['volume24']).quantize(DEC_PLACES),
                     }
    return result


def _quadrigacxApiCall(cad_ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=cad_ticker_url, headers=API_REQUEST_HEADERS)).read()
        cad_ticker = json.loads(response)

    result = {}
    result['CAD'] = {'ask': Decimal(cad_ticker['btc_cad']['sell']).quantize(DEC_PLACES),
                     'bid': Decimal(cad_ticker['btc_cad']['buy']).quantize(DEC_PLACES),
                     'last': Decimal(cad_ticker['btc_cad']['rate']).quantize(DEC_PLACES),
                     'volume': Decimal(cad_ticker['btc_cad']['volume']).quantize(DEC_PLACES),
                     }
    return result


def _btcmarkets_coApiCall(ticker_url, trades_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=trades_url, headers=API_REQUEST_HEADERS)).read()
        trades_list = json.loads(response)

    last24h_timestamp = time.time() - 86400
    volume = Decimal(0)
    for trade in trades_list:
        if trade['date'] > last24h_timestamp:
            volume = volume + Decimal(trade['amount'])


    result = {}
    result['AUD'] = {'ask': Decimal(ticker['bestAsk']).quantize(DEC_PLACES),
                    'bid': Decimal(ticker['bestBid']).quantize(DEC_PLACES),
                    'last': Decimal(ticker['lastPrice']).quantize(DEC_PLACES),
                    'volume': Decimal(volume).quantize(DEC_PLACES),
                        }
    return result


def _btc38ApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    result = {}
    result['CNY'] = {'ask': Decimal(ticker['ticker']['sell']).quantize(DEC_PLACES),
                     'bid': Decimal(ticker['ticker']['buy']).quantize(DEC_PLACES),
                     'last': Decimal(ticker['ticker']['last']).quantize(DEC_PLACES),
                     'volume': Decimal(ticker['ticker']['vol']).quantize(DEC_PLACES),
                        }
    return result


def _cointraderApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    result = {}
    result['USD'] = {'ask': Decimal(ticker['data']['USD']['offer']).quantize(DEC_PLACES),
                     'bid': Decimal(ticker['data']['USD']['bid']).quantize(DEC_PLACES),
                     'last': Decimal(ticker['data']['USD']['lastTradePrice']).quantize(DEC_PLACES),
                     'volume': Decimal(ticker['data']['USD']['volume']).quantize(DEC_PLACES),
                     }
    return result


def _btcxchangeApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    result = {}
    result['RON'] = {'ask': Decimal(ticker['ask']).quantize(DEC_PLACES),
                     'bid': Decimal(ticker['bid']).quantize(DEC_PLACES),
                     'last': Decimal(ticker['last']).quantize(DEC_PLACES),
                     'volume': Decimal(ticker['volume']).quantize(DEC_PLACES),
                     }
    return result


def _bitsoApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    result = {}
    result['MXN'] = {'ask': Decimal(ticker['btc_mxn']['sell']).quantize(DEC_PLACES),
                     'bid': Decimal(ticker['btc_mxn']['buy']).quantize(DEC_PLACES),
                     'last': Decimal(ticker['btc_mxn']['rate']).quantize(DEC_PLACES),
                     'volume': Decimal(ticker['btc_mxn']['volume']).quantize(DEC_PLACES),
                     }
    return result


def _coinfloorApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    result = {}
    result['GBP'] = {'ask': Decimal(ticker[0]['ask']/100.0).quantize(DEC_PLACES),
                     'bid': Decimal(ticker[0]['bid']/100.0).quantize(DEC_PLACES),
                     'last': Decimal(ticker[0]['last']/100.0).quantize(DEC_PLACES),
                     'volume': Decimal(ticker[0]['volume']/10000.0).quantize(DEC_PLACES),
                     }
    return result


def _bitcoin_co_idApiCall(ticker_url, *args, **kwargs):
    with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
        response = urllib2.urlopen(urllib2.Request(url=ticker_url, headers=API_REQUEST_HEADERS)).read()
        ticker = json.loads(response)

    result = {}
    result['IDR'] = {'ask': Decimal(ticker['ticker']['sell']).quantize(DEC_PLACES),
                     'bid': Decimal(ticker['ticker']['buy']).quantize(DEC_PLACES),
                     'last': Decimal(ticker['ticker']['last']).quantize(DEC_PLACES),
                     'volume': Decimal(ticker['ticker']['vol_btc']).quantize(DEC_PLACES),
                     }
    return result
########NEW FILE########
__FILENAME__ = bitcoinchart_fallback
import json
import time
from decimal import Decimal
from eventlet.green import urllib2
from eventlet.timeout import Timeout

import bitcoinaverage as ba
from bitcoinaverage.config import BITCOIN_CHARTS_API_URL, DEC_PLACES, API_REQUEST_HEADERS, API_CALL_TIMEOUT_THRESHOLD
from bitcoinaverage.exceptions import CallTimeoutException


def fetchBitcoinChartsData():
    global ba

    if 'bitcoincharts' not in ba.api_parsers.API_QUERY_CACHE:
        ba.api_parsers.API_QUERY_CACHE['bitcoincharts'] = {'last_call_timestamp': 0,
                                                            'result': None,
                                                            'call_fail_count': 0,
                                                               }

    current_timestamp = int(time.time())
    if (ba.api_parsers.API_QUERY_CACHE['bitcoincharts']['last_call_timestamp']+ba.api_parsers.API_QUERY_FREQUENCY['bitcoincharts'] > current_timestamp):
        result = ba.api_parsers.API_QUERY_CACHE['bitcoincharts']['result']
    else:
        with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
            response = urllib2.urlopen(urllib2.Request(url=BITCOIN_CHARTS_API_URL, headers=API_REQUEST_HEADERS)).read()
            result = json.loads(response)

        ba.api_parsers.API_QUERY_CACHE['bitcoincharts'] = {'last_call_timestamp': current_timestamp,
                                                           'result':result,
                                                           'call_fail_count':0,
                                                               }

    return result

def getData(bitcoincharts_symbols):
    bitcoincharts_data = fetchBitcoinChartsData()

    return_result = {}
    return_result['data_source'] = 'bitcoincharts'
    for api in bitcoincharts_data:
        for currency_code in bitcoincharts_symbols:
            if api['symbol'] == bitcoincharts_symbols[currency_code]:
                try:
                    return_result[currency_code] = {'ask': Decimal(api['ask']).quantize(DEC_PLACES),
                                                    'bid': Decimal(float(api['bid'])).quantize(DEC_PLACES),
                                                    'last': Decimal(float(api['close'])).quantize(DEC_PLACES),
                                                    'volume': Decimal(float(api['volume'])).quantize(DEC_PLACES),
                                                       }
                except TypeError:
                    pass

    return return_result



########NEW FILE########
__FILENAME__ = config
from decimal import Decimal

import bitcoinaverage.server

INDEX_DOCUMENT_NAME = 'default'  # directory index document name, needs to match webserver setting
CURRENCY_DUMMY_PAGES_SUBFOLDER_NAME = 'currencies'
CHARTS_DUMMY_PAGES_SUBFOLDER_NAME = 'charts'

FRONTEND_LEGEND_SLOTS = 20
FRONTEND_MAJOR_CURRENCIES = 5
FRONTEND_SCALE_DIVIZER = 1  # 1000 for millibitcoins
FRONTEND_PRECISION = 2  # Digits after dot; 3 for millibitcoins
FRONTEND_CHART_TYPE = 'linear'

API_FILES = {'TICKER_PATH': 'ticker/',
             'GLOBAL_TICKER_PATH': 'ticker/global/',
             'EXCHANGES_PATH': 'exchanges/',
             'ALL_FILE': 'all',
             'IGNORED_FILE': 'ignored',
             'CUSTOM_API': 'custom/'
             }

CUSTOM_API_FILES = {'AndroidBitcoinWallet': 'abw',
                    'HiveMacDesktopWallet': 'hive_mac',
                    'HiveAndroidWallet': 'hive_android',
                    }

API_REQUEST_HEADERS = {'User-Agent': 'bitcoinaverage.com query bot',
                       'Origin': 'bitcoinaverage.com'}

if hasattr(bitcoinaverage.server, 'DEFAULT_API_QUERY_REQUEST_HEADER_USER_AGENT_OVERRIDE'):
    API_REQUEST_HEADERS['User-Agent'] = bitcoinaverage.server.DEFAULT_API_QUERY_REQUEST_HEADER_USER_AGENT_OVERRIDE

FRONTEND_QUERY_FREQUENCY = 15  # seconds between AJAX requests from frontend to our API
HISTORY_QUERY_FREQUENCY = 30  # seconds between history_daemon requests
FIAT_RATES_QUERY_FREQUENCY = 3600  # seconds between requests for fiat exchange rates, must be not less than an hour,
                                  # as total API queries amount limited at 1000/month
API_CALL_TIMEOUT_THRESHOLD = 15  # seconds before exchange API call timeout. exchange may have multiple calls
                                #and total time spent querying one exchange will be threshold * number of calls

#seconds between calls to various exchanges APIs
API_QUERY_FREQUENCY = {
    '_all': 10,  # parser daemon cycle duration
    '_default': 60,
    'bitcoincharts': 900,
    'bitstamp': 30,
}

if hasattr(bitcoinaverage.server, 'DEFAULT_API_QUERY_FREQUENCY_OVERRIDE'):
    API_QUERY_FREQUENCY['_default'] = bitcoinaverage.server.DEFAULT_API_QUERY_FREQUENCY_OVERRIDE

#seconds before a consequently failing API will be put into ignored list (in the mean time data will be taken from cache)
API_IGNORE_TIMEOUT = 1800

# API daemon write frequency
API_WRITE_FREQUENCY = 10

DEC_PLACES = Decimal('0.00')

CURRENCY_LIST = (
    'USD',
    'EUR',
    'CNY',
    'GBP',
    'CAD',
    'PLN',
    'RUB',
    'AUD',
    'SEK',
    'BRL',
    'NZD',
    'SGD',
    'ZAR',
    'NOK',
    'ILS',
    'CHF',
    'TRY',
    'HKD',
    'RON',
    'MXN',
    'IDR',
    #'JPY',
    #'CZK',
    #'DKK',
    #'THB',
)

# http://www.currencysymbols.in/
FRONTEND_CURRENCY_SYMBOLS = {
    'USD': ['0024'],
    'EUR': ['20ac'],
    'CNY': ['00a5'],
    'GBP': ['00a3'],
    'CAD': ['0024'],
    'PLN': ['007a', '0142'],
    'RUB': [],
    'AUD': ['0024'],
    'SEK': ['006b', '0072'],
    'BRL': ['0052', '0024'],
    'NZD': ['0024'],
    'SGD': ['0024'],
    'ZAR': ['0052'],
    'NOK': ['006b', '0072'],
    'ILS': ['20aa'],
    'CHF': [],
    'TRY': [],
    'HKD': ['0024'],
    'RON': [],
    'MXN': [],
    'IDR': [],
    #'JPY': ['00a5'],
}

BITCOIN_CHARTS_API_URL = 'https://api.bitcoincharts.com/v1/markets.json'

EXCHANGE_LIST = {
    #EXCHANGES WITH DIRECT INTEGRATION
    'bitstamp': {'api_ticker_url': 'https://www.bitstamp.net/api/ticker/',
                 'display_name': 'Bitstamp',
                 'URL': 'https://bitstamp.net/',
                 'bitcoincharts_symbols': {'USD': 'bitstampUSD', },
                 },
    'btce': {'usd_api_url': 'https://btc-e.com/api/2/btc_usd/ticker',
             'eur_api_url': 'https://btc-e.com/api/2/btc_eur/ticker',
             'rur_api_url': 'https://btc-e.com/api/2/btc_rur/ticker',
             'display_name': 'BTC-e',
             'URL': 'https://btc-e.com/',
             'bitcoincharts_symbols': {'USD': 'btceUSD',
                                       },
             },
    'bitcurex': {'eur_ticker_url': 'https://eur.bitcurex.com/data/ticker.json',
                 'eur_trades_url': 'https://eur.bitcurex.com/data/trades.json',
                 'pln_ticker_url': 'https://pln.bitcurex.com/data/ticker.json',
                 'pln_trades_url': 'https://pln.bitcurex.com/data/trades.json',
                 'URL': 'https://bitcurex.com/',
                 'display_name': 'Bitcurex',
                 },
    'vircurex': {'usd_api_url': 'https://api.vircurex.com/api/get_info_for_1_currency.json?base=BTC&alt=USD',
                 'eur_api_url': 'https://api.vircurex.com/api/get_info_for_1_currency.json?base=BTC&alt=EUR',
                 'URL': 'https://vircurex.com/',
                 'display_name': 'Vircurex',
                 },
    'bitbargain': {'volume_api_url': 'https://bitbargain.co.uk/api/bbticker',
                   'ticker_api_url': 'https://bitbargain.co.uk/api/btcavg',
                   'URL': 'https://bitbargain.co.uk/',
                   'display_name': 'BitBargain',
                   },
    'localbitcoins': {'api_url': 'https://localbitcoins.com/bitcoinaverage/ticker-all-currencies/',
                      'URL': 'https://localbitcoins.com/?ch=22yh',
                      'display_name': 'LocalBitcoins',
                      },
    'cryptotrade': {'usd_api_url': 'https://crypto-trade.com/api/1/ticker/btc_usd',
                    'URL': 'https://crypto-trade.com/',
                    'display_name': 'Crypto-Trade',
                    'bitcoincharts_symbols': {'USD': 'crytrUSD', },
                    },
    'rocktrading': {'usd_ticker_url': 'https://www.therocktrading.com/api/ticker/BTCUSD',
                    'usd_trades_url': 'https://www.therocktrading.com/api/trades/BTCUSD',
                    'eur_ticker_url': 'https://www.therocktrading.com/api/ticker/BTCEUR',
                    'eur_trades_url': 'https://www.therocktrading.com/api/trades/BTCEUR',
                    'URL': 'https://therocktrading.com/',
                    'display_name': 'Rock Trading',
                    },
    'bit2c': {'ticker_url': 'https://www.bit2c.co.il/Exchanges/BtcNis/Ticker.json',
              'URL': 'https://www.bit2c.co.il/',
              'display_name': 'Bit2C',
              },
    'kapiton': {'ticker_url': 'https://kapiton.se/api/0/ticker',
                'URL': 'https://kapiton.se/',
                'display_name': 'Kapiton',
                },
    'btcchina': {'ticker_url': 'https://data.btcchina.com/data/ticker',
                 'URL': 'https://btcchina.com/',
                 'display_name': 'BTC China',
                 },
    #'fxbtc': {'ticker_url': 'https://data.fxbtc.com/api?op=query_ticker&symbol=btc_cny',
    #          'trades_url_template': 'https://data.fxbtc.com/api?op=query_history_trades&symbol=btc_cny&since={timestamp_sec}000000', #zeroes for millisec
    #          'URL': 'https://fxbtc.com/',
    #          'display_name': 'FXBTC',
    #          },
    'bter': {'ticker_url': 'https://bter.com/api/1/ticker/btc_cny',
             'URL': 'https://bter.com/',
             'display_name': 'Bter',
             },
    'mercado':  {'ticker_url': 'https://www.mercadobitcoin.com.br/api/ticker/',
                 'display_name': 'Mercado Bitcoin',
                 'URL': 'https://www.mercadobitcoin.com.br/',
                 'bitcoincharts_symbols': {'BRL': 'mrcdBRL',
                                           },
                 },
    'bitx':  {'ticker_url': 'https://bitx.co.za/api/1/ticker?pair=XBTZAR',
              'URL': 'https://bitx.co.za/',
              'display_name': 'BitX',
              },
    #'justcoin':  {'ticker_url': 'https://justcoin.com/api/v1/markets',
    #              'URL': 'https://justcoin.com/',
    #              'display_name': 'Justcoin',
    #               },
    'kraken':  {'usd_ticker_url': 'https://api.kraken.com/0/public/Ticker?pair=XBTUSD',
                'eur_ticker_url': 'https://api.kraken.com/0/public/Ticker?pair=XBTEUR',
                'URL': 'https://kraken.com/',
                'display_name': 'Kraken',
                },
    'bitkonan': {'ticker_url': 'https://bitkonan.com/api/ticker',
                 'display_name': 'BitKonan',
                 'URL': 'https://bitkonan.com/',
                 'bitcoincharts_symbols': {'USD': 'bitkonanUSD',
                                           },
                 },
    'bittylicious': {'ticker_url': 'https://bittylicious.com/api/v1/ticker',
                     'URL': 'https://bittylicious.com/',
                     'display_name': 'Bittylicious',
                     },
    'cavirtex': {'ticker_url': 'https://www.cavirtex.com/api/CAD/ticker.json',
                 'orderbook_url': 'https://www.cavirtex.com/api/CAD/orderbook.json',
                 'display_name': 'VirtEx',
                 'URL': 'https://www.cavirtex.com/',
                 'bitcoincharts_symbols': {'CAD': 'virtexCAD',
                                           },
                 },
    'bitfinex': {'ticker_url': 'https://api.bitfinex.com/v1/ticker/btcusd',
                 'today_url': 'https://api.bitfinex.com/v1/today/btcusd',  # limit_trades might need increase if daily trading will go above it
                 'URL': 'https://bitfinex.com',
                 'display_name': 'Bitfinex',
                 },
    'fybsg': {'ticker_url': 'https://www.fybsg.com/api/SGD/ticker.json',
              'trades_url': 'https://www.fybsg.com/api/SGD/trades.json',  # this URL queries all trades for this exchange since beginning of time, this is not effective, ideally they should allow API to query by date.
              'URL': 'https://www.fybsg.com',
              'display_name': 'FYB-SG',
              'bitcoincharts_symbols': {'SGD': 'fybsgSGD'
                                        },
              },
    'fybse':  {'ticker_url': 'https://www.fybse.se/api/SEK/ticker.json',
               'trades_url': 'https://www.fybse.se/api/SEK/trades.json',  # this URL queries all trades for this exchange since beginning of time, this is not effective, ideally they should allow API to query by date.
               'URL': 'https://www.fybse.se',
               'display_name': 'FYB-SE',
               'bitcoincharts_symbols': {'SEK': 'fybseSEK',
                                         },
               },
    'bitcoin_de': {'rates_url': 'https://bitcoinapi.de/v1/{api_key}/rate.json',
                   'trades_url': 'https://bitcoinapi.de/v1/{api_key}/trades.json',
                   'URL': 'https://bitcoin.de',
                   'display_name': 'Bitcoin.de',
                   },
    'bitcoin_central': {'ticker_url': 'https://bitcoin-central.net/api/data/eur/ticker',
                        'depth_url': 'https://bitcoin-central.net/api/data/eur/depth',
                        'URL': 'https://bitcoin-central.net',
                        'display_name': 'Bitcoin Central',
                        },
    'btcturk': {'ticker_url': 'https://www.btcturk.com/api/ticker',
                'URL': 'https://btcturk.com',
                'display_name': 'BTCTurk',
                },
    'bitonic': {'ticker_url': 'https://bitonic.nl/api/price',
                'URL': 'https://bitonic.nl',
                'display_name': 'Bitonic',
                },
    'itbit':  {'usd_orders_url': 'https://www.itbit.com/api/v2/markets/XBTUSD/orders',
               'usd_trades_url': 'https://www.itbit.com/api/v2/markets/XBTUSD/trades?since={trade_id}',
               'sgd_orders_url': 'https://www.itbit.com/api/v2/markets/XBTSGD/orders',
               'sgd_trades_url': 'https://www.itbit.com/api/v2/markets/XBTSGD/trades?since={trade_id}',
               'eur_orders_url': 'https://www.itbit.com/api/v2/markets/XBTEUR/orders',
               'eur_trades_url': 'https://www.itbit.com/api/v2/markets/XBTEUR/trades?since={trade_id}',
               'since_trade_id': 10262,
               'URL': 'https://www.itbit.com',
               'display_name': 'itBit',
               },
    'vaultofsatoshi': {'usd_ticker_url': 'https://api.vaultofsatoshi.com/public/ticker?order_currency=BTC&payment_currency=USD',
                       'eur_ticker_url': 'https://api.vaultofsatoshi.com/public/ticker?order_currency=BTC&payment_currency=EUR',
                       'cad_ticker_url': 'https://api.vaultofsatoshi.com/public/ticker?order_currency=BTC&payment_currency=CAD',
                       'URL': 'https://vaultofsatoshi.com',
                       'display_name': 'Vault of Satoshi',
                       },
    'quickbitcoin': {'gbp_ticker_url': 'https://quickbitcoin.co.uk/ticker',
                     'URL': 'https://quickbitcoin.co.uk',
                     'display_name': 'QuickBitcoin',
                     },
    'quadrigacx': {'cad_ticker_url': 'http://api.quadrigacx.com/public/info',
                   'URL': 'https://quadrigacx.com',
                   'display_name': 'QuadrigaCX',
                   },
    'campbx': {'api_ticker_url': 'https://campbx.com/api/xticker.php',
               'api_trades_url': 'https://campbx.com/bc/ac2.php?Unixtime={timestamp_since}',
               'URL': 'https://campbx.com',
               'display_name': 'CampBX',
               'bitcoincharts_symbols': {'USD': 'cbxUSD',
                                         },
               },
    'btcmarkets': {'ticker_url': 'https://api.btcmarkets.net/market/BTC/AUD/tick',
                   'trades_url': 'https://api.btcmarkets.net/market/BTC/AUD/trades',
                   'bitcoincharts_symbols': {'AUD': 'btcmarketsAUD',
                                             },
                   'URL': 'https://btcmarkets.net/',
                   'display_name': 'BTC Markets',
                   },
    'btc38':      {'ticker_url': 'http://api.btc38.com/v1/ticker.php?c=btc',
                   'URL': 'http://btc38.com/',
                   'display_name': 'BTC38',
                   },

    'cointrader':  {'ticker_url': 'https://www.cointrader.net/api/stats/daily',
                    'URL': 'https://www.cointrader.net/',
                    'display_name': 'Cointrader'
                    },
    'btcxchange': {'ticker_url': 'https://api.btcxchange.ro/ticker',
                   'URL': 'https://www.btcxchange.ro/',
                   'display_name': 'BTCXchange',
                   },
    'bitso': {'ticker_url': 'https://api.bitso.com/public/info',
              'URL': 'https://bitso.com/',
              'display_name': 'Bitso',
              },
    'coinfloor': {'ticker_url': 'https://webapi.coinfloor.co.uk:8443/XBT/GBP/ticker',
                  'URL': 'https://coinfloor.co.uk/',
                  'display_name': 'Coinfloor',
                  },
    'bitcoin_co_id': {'ticker_url': 'https://vip.bitcoin.co.id/api/btc_idr/ticker',
                      'URL': 'https://bitcoin.co.id/',
                      'display_name': 'Bitcoin.co.in',
                      },


    #EXCHANGES RECEIVED THROUGH BITCOINCHARTS
    'btceur': {'bitcoincharts_symbols': {'EUR': 'btceurEUR',
                                         },
               'URL': 'http://www.btceur.eu/',
               'display_name': 'Bitcoin Euro Exchange',
               },
    'bitnz':  {'bitcoincharts_symbols': {'NZD': 'bitnzNZD',
                                         },
               'URL': 'https://bitnz.com/',
               'display_name': 'bitNZ',
               },
    'anx_hk':  {'bitcoincharts_symbols': {'USD': 'anxhkUSD',
                                          'HKD': 'anxhkHKD',
                                          'CNY': 'anxhkCNY',
                                          },
                'URL': 'https://anxbtc.com/',
                'display_name': 'ANXBTC',
                },


    #EXCHANGES IGNORED
    'okcoin':  {'ticker_url': 'https://www.okcoin.com/api/ticker.do',
                'display_name': 'OKCoin',
                'ignored': True,
                'ignore_reason': '0% trading fee',
                },
    'btctrade':  {'ticker_url': 'http://www.btctrade.com/api/ticker',
                  'display_name': 'btctrade',
                  'ignored': True,
                  'ignore_reason': '0% trading fee',
                   },
    'huobi':  {'display_name': 'Huobi',
               'ignored': True,
               'ignore_reason': '0% trading fee',
               },
    # 'coinmkt':  {'display_name': 'CoinMKT',
    #              'ignored': True,
    #              'ignore_reason': 'no API available',
    #              },
    'coinbase':  {'display_name': 'Coinbase',
                  'ignored': True,
                  'ignore_reason': 'volume data not published',
                  },
    #'bitxf': {'ticker_url': 'https://bitxf.com/api/v0/CNY/ticker.json',
    #          'URL': 'https://bitxf.com/',
    #          'display_name': 'BitXF',
    #          'ignored': True,
    #          'ignore_reason': 'unavailable'
    #            },


    #EXCHANGES DEAD AND BURIED
    #'bit121': {'bitcoincharts_symbols': {'GBP': 'bit121GBP',
    #                                         },
    #            'URL': 'https://bit121.co.uk/',
    #            'display_name': 'bit121',
    #              },
    #'weex':  {'bitcoincharts_symbols': {'AUD': 'weexAUD',
    #                                     #'CAD': 'weexCAD',
    #                                     #'USD': 'weexUSD',
    #                                        },
    #           'display_name': 'Weex',
    #              },
    #'bitbox': {'bitcoincharts_symbols': {'USD': 'bitboxUSD',
    #                                      },
    #              },
    #'fbtc': {'bitcoincharts_symbols':  {'EUR': 'fbtcEUR',
    #                                    'USD': 'fbtcUSD',
    #                                       },
    #             },
    #'icbit': {'bitcoincharts_symbols': {'USD': 'icbitUSD',
    #                                       },
    #             },
    # 'goxbtc':  {'ticker_url': 'https://goxbtc.com/api/btc_cny/ticker.htm',
    #             'display_name': 'GoXBTC',
    #                 },
    # 'rmbtb': {'ticker_url': 'https://www.rmbtb.com/api/thirdparty/ticker/',
    #           'display_name': 'RMBTB',
    #             },
    # 'bitcash': {'czk_api_url': 'https://bitcash.cz/market/api/BTCCZK/ticker.json',
    #             'bitcoincharts_symbols': {'CZK': 'bitcashCZK',
    #                                        },
    #               },
    # 'mtgox': {'usd_api_url': 'https://data.mtgox.com/api/2/BTCUSD/money/ticker',
    #           'eur_api_url': 'https://data.mtgox.com/api/2/BTCEUR/money/ticker',
    #           'gbp_api_url': 'https://data.mtgox.com/api/2/BTCGBP/money/ticker',
    #           'cad_api_url': 'https://data.mtgox.com/api/2/BTCCAD/money/ticker',
    #           'pln_api_url': 'https://data.mtgox.com/api/2/BTCPLN/money/ticker',
    #           'rub_api_url': 'https://data.mtgox.com/api/2/BTCRUB/money/ticker',
    #           'aud_api_url': 'https://data.mtgox.com/api/2/BTCAUD/money/ticker',
    #           'chf_api_url': 'https://data.mtgox.com/api/2/BTCCHF/money/ticker',
    #           'cny_api_url': 'https://data.mtgox.com/api/2/BTCCNY/money/ticker',
    #           'dkk_api_url': 'https://data.mtgox.com/api/2/BTCDKK/money/ticker',
    #           'hkd_api_url': 'https://data.mtgox.com/api/2/BTCHKD/money/ticker',
    #           'jpy_api_url': 'https://data.mtgox.com/api/2/BTCJPY/money/ticker',
    #           'nzd_api_url': 'https://data.mtgox.com/api/2/BTCNZD/money/ticker',
    #           'sgd_api_url': 'https://data.mtgox.com/api/2/BTCSGD/money/ticker',
    #           'sek_api_url': 'https://data.mtgox.com/api/2/BTCSEK/money/ticker',
    #           'display_name': 'MtGox',
    #           'bitcoincharts_symbols': {'USD': 'mtgoxUSD',
    #                                     'EUR': 'mtgoxEUR',
    #                                     'GBP': 'mtgoxGBP',
    #                                     'CAD': 'mtgoxCAD',
    #                                     'PLN': 'mtgoxPLN',
    #                                     'RUB': 'mtgoxRUB',
    #                                     'AUD': 'mtgoxAUD',
    #                                     'CHF': 'mtgoxCHF',
    #                                     'CNY': 'mtgoxCNY',
    #                                     'DKK': 'mtgoxDKK',
    #                                     'HKD': 'mtgoxHKD',
    #                                     'JPY': 'mtgoxJPY',
    #                                     'NZD': 'mtgoxNZD',
    #                                     'SGD': 'mtgoxSGD',
    #                                     'SEK': 'mtgoxSEK',
    #                                     },
    #
    #           'ignored': True,
    #           'ignore_reason': 'withdrawals blocked',
    #               },
    # 'intersango': {'ticker_url': 'https://intersango.com/api/ticker.php',
    #                'URL': 'https://intersango.com/',
    #                'display_name': 'Intersango',
    #                },
}

API_USERS = [
    {
        'name': 'Bitcoin Wallet',
        'image': 'https://lh4.ggpht.com/mkAOtT2IYdrrFPql95BqirLG1dtApT5Z8eEq5Q4clQHvZTBVZCb5FKPARyH7cFAvkA=w300',
        'href': 'https://play.google.com/store/apps/details?id=de.schildbach.wallet'
    },
    {
        'name': 'Mycelium',
        'image': 'https://lh5.ggpht.com/9pS6MKseKSl06PwreFjZ4RnVuf0wCy_pBk00ZpHWXKNzY4N0otRm6OFMXjiCCpPJDGHq=w300',
        'href': 'https://play.google.com/store/apps/details?id=com.mycelium.wallet'
    },
    {
        'name': 'Localbitcoins',
        'image': 'https://bitcoinaverage.com/img/localbitcoins.png',
        'href': 'https://localbitcoins.com/?ch=22yh',
    },
    {
        'name': 'KryptoKit',
        'image': './img/kryptokit.png',
        'href': 'http://www.kryptokit.com/',
    },
    {
        'name': 'Lamassu',
        'image': 'https://bitcoinaverage.com/img/lamassu.png',
        'href': 'https://lamassu.is/',
    },
    {
        'name': 'Hive Wallet',
        'image': 'https://bitcoinaverage.com/img/hive.png',
        'href': 'https://www.hivewallet.com',
    },
    {
        'name': 'GreenAddress',
        'image': 'https://greenaddress.it/static/img/logos/logo-greenaddress.png',
        'href': 'https://greenaddress.it',
    },
    {
        'name': 'Kitco',
        'image': 'https://bitcoinaverage.com/img/kitco.jpg',
        'href': 'http://www.kitco.com/finance/bitcoin/',
    },
]

########NEW FILE########
__FILENAME__ = exceptions
class NoVolumeException(Exception):
    exchange_name = None
    strerror = u'volume data not available'

class NoApiException(Exception):
    exchange_name = None
    strerror = u'API not available'

class CallTimeoutException(Exception):
    exchange_name = None
    strerror = u'unreachable since %s UTC'

    def __str__(self):
        return "CallTimeoutException"

class CacheTimeoutException(Exception):
    exchange_name = None
    strerror = u'unreachable since %s UTC'

########NEW FILE########
__FILENAME__ = helpers
from decimal import Decimal
import os
from shutil import copyfile
import time
import json
from email import utils
import datetime
import socket
from lxml import etree
from eventlet.green import urllib2
from eventlet.timeout import Timeout
from eventlet.green import httplib
import simplejson
import hashlib
import gzip

import bitcoinaverage as ba
from bitcoinaverage.config import API_CALL_TIMEOUT_THRESHOLD, API_REQUEST_HEADERS, API_FILES
from bitcoinaverage.server import OPENEXCHANGERATES_APP_ID
from bitcoinaverage.exceptions import CallTimeoutException


def write_js_config():
    global ba

    js_config_template = 'var config = $CONFIG_DATA;'

    exchange_color = lambda name: "#" + hashlib.md5(name.encode()).hexdigest()[:6]

    config_data = {}
    config_data['apiIndexUrl'] = ba.server.API_INDEX_URL
    config_data['apiHistoryIndexUrl'] = ba.server.API_INDEX_URL_HISTORY
    config_data['refreshRate'] = str(ba.config.FRONTEND_QUERY_FREQUENCY*1000) #JS requires value in milliseconds
    config_data['currencyOrder'] = ba.config.CURRENCY_LIST
    config_data['legendSlots'] = ba.config.FRONTEND_LEGEND_SLOTS
    config_data['majorCurrencies'] = ba.config.FRONTEND_MAJOR_CURRENCIES
    config_data['scaleDivizer'] = ba.config.FRONTEND_SCALE_DIVIZER
    config_data['precision'] = ba.config.FRONTEND_PRECISION
    config_data['chartType'] = ba.config.FRONTEND_CHART_TYPE
    config_data['exchangesColors'] = {ex: exchange_color(ex) for ex in ba.config.EXCHANGE_LIST.keys()}
    config_data['currencySymbols'] = ba.config.FRONTEND_CURRENCY_SYMBOLS
    config_data['apiUsers'] = ba.config.API_USERS
    config_string = js_config_template.replace('$CONFIG_DATA',
            json.dumps(config_data, ensure_ascii=False).encode('utf8'))

    with open(os.path.join(ba.server.WWW_DOCUMENT_ROOT, 'js', 'config.js'), 'w') as config_file:
        config_file.write(config_string)


def write_fiat_rates_config():
    global ba
    js_config_template = "var fiatCurrencies = $FIAT_CURRENCIES_DATA$;"

    currencies_names_URL = 'http://openexchangerates.org/api/currencies.json'
    currencies_rates_URL = 'http://openexchangerates.org/api/latest.json?app_id={app_id}'.format(app_id=OPENEXCHANGERATES_APP_ID)

    currency_data_list = {}

    try:
        with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
            response = urllib2.urlopen(urllib2.Request(url=currencies_names_URL, headers=API_REQUEST_HEADERS)).read()
            currencies_names = json.loads(response)

        with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
            response = urllib2.urlopen(urllib2.Request(url=currencies_rates_URL, headers=API_REQUEST_HEADERS)).read()
            currencies_rates = json.loads(response)
    except (CallTimeoutException,
            socket.error,
            urllib2.URLError,
            httplib.BadStatusLine,
            ValueError):
        return None

    for currency_code in currencies_names:
        try:
            currency_data_list[currency_code] = {'name': currencies_names[currency_code],
                                                 'rate': str(currencies_rates['rates'][currency_code]),
                                                 }
        except (KeyError, TypeError):
            return None

    config_string = js_config_template
    config_string = config_string.replace('$FIAT_CURRENCIES_DATA$', json.dumps(currency_data_list))

    with open(os.path.join(ba.server.WWW_DOCUMENT_ROOT, 'js', 'fiat_data.js'), 'w') as fiat_exchange_config_file:
        fiat_exchange_config_file.write(config_string)

    with open(os.path.join(ba.server.API_DOCUMENT_ROOT, 'fiat_data'), 'w') as fiat_exchange_api_file:
        fiat_exchange_api_file.write(json.dumps(currency_data_list))


def write_html_currency_pages():
    global ba
    today = datetime.datetime.today()

    template_file_path = os.path.join(ba.server.WWW_DOCUMENT_ROOT, '_currency_page_template.htm')
    with open(template_file_path, 'r') as template_file:
        template = template_file.read()

    api_all_url = '{}ticker/all'.format(ba.server.API_INDEX_URL)

    try:
        with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
            response = urllib2.urlopen(urllib2.Request(url=api_all_url, headers=API_REQUEST_HEADERS)).read()
            all_rates = json.loads(response)
    except (CallTimeoutException,
            socket.error,
            urllib2.URLError,
            httplib.BadStatusLine,
            simplejson.decoder.JSONDecodeError):
        return None

    if not os.path.exists(os.path.join(ba.server.WWW_DOCUMENT_ROOT, ba.config.CURRENCY_DUMMY_PAGES_SUBFOLDER_NAME)):
        os.makedirs(os.path.join(ba.server.WWW_DOCUMENT_ROOT, ba.config.CURRENCY_DUMMY_PAGES_SUBFOLDER_NAME))

    for currency_code in ba.config.CURRENCY_LIST:
        currency_rate = all_rates[currency_code]['last']
        currency_page_contents = template
        currency_page_contents = currency_page_contents.replace('$RATE$', str(Decimal(currency_rate).quantize(ba.config.DEC_PLACES)))
        currency_page_contents = currency_page_contents.replace('$CURRENCY_CODE$', currency_code)
        currency_page_contents = currency_page_contents.replace('$GENERATION_DATETIME$', today.strftime('%Y-%m-%dT%H:%M'))

        with open(os.path.join(ba.server.WWW_DOCUMENT_ROOT,
                               ba.config.CURRENCY_DUMMY_PAGES_SUBFOLDER_NAME,
                               ('%s.htm' % currency_code.lower())), 'w') as currency_page_file:
            currency_page_file.write(currency_page_contents)

    template_file_path = os.path.join(ba.server.WWW_DOCUMENT_ROOT, '_charts_page_template.htm')
    with open(template_file_path, 'r') as template_file:
        template = template_file.read()

    if not os.path.exists(os.path.join(ba.server.WWW_DOCUMENT_ROOT, ba.config.CHARTS_DUMMY_PAGES_SUBFOLDER_NAME)):
        os.makedirs(os.path.join(ba.server.WWW_DOCUMENT_ROOT, ba.config.CHARTS_DUMMY_PAGES_SUBFOLDER_NAME))

    index = 0
    for currency_code in ba.config.CURRENCY_LIST:
        currency_rate = all_rates[currency_code]['last']
        chart_page_contents = template
        chart_page_contents = chart_page_contents.replace('$RATE$', str(Decimal(currency_rate).quantize(ba.config.DEC_PLACES)))
        chart_page_contents = chart_page_contents.replace('$CURRENCY_CODE$', currency_code)
        chart_page_contents = chart_page_contents.replace('$GENERATION_DATETIME$', today.strftime('%Y-%m-%dT%H:%M'))
        with open(os.path.join(ba.server.WWW_DOCUMENT_ROOT,
                               ba.config.CHARTS_DUMMY_PAGES_SUBFOLDER_NAME,
                               ('%s.htm' % currency_code.lower())), 'w') as chart_page_file:
            chart_page_file.write(chart_page_contents)


        index = index + 1
        if index == ba.config.FRONTEND_MAJOR_CURRENCIES:
            break


def write_sitemap():
    global ba

    def _sitemap_append_url(url_str, lastmod_date=None, changefreq_str=None, priority_str=None):
        url = etree.Element('url')
        loc = etree.Element('loc')
        loc.text = url_str
        url.append(loc)
        if lastmod_date is not None:
            lastmod = etree.Element('lastmod')
            lastmod.text = lastmod_date.strftime('%Y-%m-%d')
            url.append(lastmod)
        if changefreq_str is not None:
            changefreq = etree.Element('changefreq')
            changefreq.text = changefreq_str
            url.append(changefreq)
        if priority_str is not None:
            priority = etree.Element('priority')
            priority.text = priority_str
            url.append(priority)
        return url

    urlset = etree.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')

    index_url = '%s%s' % (ba.server.FRONTEND_INDEX_URL, 'index.htm')
    today = datetime.datetime.today()
    urlset.append(_sitemap_append_url('%s%s' % (ba.server.FRONTEND_INDEX_URL, 'index.htm'), today, 'hourly', '1.0'))
    urlset.append(_sitemap_append_url('%s%s' % (ba.server.FRONTEND_INDEX_URL, 'faq.htm'), today, 'monthly', '0.5'))
    urlset.append(_sitemap_append_url('%s%s' % (ba.server.FRONTEND_INDEX_URL, 'api.htm'), today, 'monthly', '0.5'))
    urlset.append(_sitemap_append_url('%s%s' % (ba.server.FRONTEND_INDEX_URL, 'blog.htm'), today, 'weekly', '1.0'))
    urlset.append(_sitemap_append_url('%s%s' % (ba.server.FRONTEND_INDEX_URL, 'charts.htm'), today, 'hourly', '0.8'))

    currency_static_seo_pages_dir = os.path.join(ba.server.WWW_DOCUMENT_ROOT, ba.config.CURRENCY_DUMMY_PAGES_SUBFOLDER_NAME)
    for dirname, dirnames, filenames in os.walk(currency_static_seo_pages_dir):
        for filename in filenames:
            urlset.append(_sitemap_append_url('%s%s/%s' % (ba.server.FRONTEND_INDEX_URL,
                                                        ba.config.CURRENCY_DUMMY_PAGES_SUBFOLDER_NAME,
                                                        filename), today, 'hourly', '1.0'))
    #charts_static_seo_pages_dir = os.path.join(ba.server.WWW_DOCUMENT_ROOT, ba.config.CHARTS_DUMMY_PAGES_SUBFOLDER_NAME)
    #index = 0
    #for dirname, dirnames, filenames in os.walk(currency_static_seo_pages_dir):
    #    for filename in filenames:
    #        urlset.append(_sitemap_append_url('%s%s/%s' % (ba.server.FRONTEND_INDEX_URL,
    #                                                    ba.config.CHARTS_DUMMY_PAGES_SUBFOLDER_NAME,
    #                                                    filename), today, 'hourly', '0.8'))
    #        index = index + 1
    #        if index == ba.config.FRONTEND_MAJOR_CURRENCIES:
    #            break
    #    break

    xml_sitemap_contents = '<?xml version="1.0" encoding="UTF-8"?>\n' + etree.tostring(urlset, pretty_print=True)
    with open(os.path.join(ba.server.WWW_DOCUMENT_ROOT, 'sitemap.xml'), 'w') as sitemap_file:
        sitemap_file.write(xml_sitemap_contents)


def write_api_index_files():
    def _write_history_index_file(currency_code):
        global ba
        if not os.path.exists(os.path.join(ba.server.HISTORY_DOCUMENT_ROOT, currency_code)):
            os.makedirs(os.path.join(ba.server.HISTORY_DOCUMENT_ROOT, currency_code))

        current_index_file_path = os.path.join(ba.server.HISTORY_DOCUMENT_ROOT, currency_code, ba.config.INDEX_DOCUMENT_NAME)

        index_contents = {}
        index_contents['24h_sliding'] = '%s%s/per_minute_24h_sliding_window.csv' % (ba.server.API_INDEX_URL_HISTORY, currency_code)
        index_contents['monthly_sliding'] = '%s%s/per_hour_monthly_sliding_window.csv' % (ba.server.API_INDEX_URL_HISTORY, currency_code)
        index_contents['all_time'] = '%s%s/per_day_all_time_history.csv' % (ba.server.API_INDEX_URL_HISTORY, currency_code)
        index_contents['volumes'] = '%s%s/volumes.csv' % (ba.server.API_INDEX_URL_HISTORY, currency_code)
        index_contents['global_24h_sliding'] = '%s%s/per_minute_24h_global_average_sliding_window.csv' % (ba.server.API_INDEX_URL_HISTORY, currency_code)

        write_api_file(
            current_index_file_path,
            json.dumps(index_contents, indent=2, sort_keys=True, separators=(',', ': ')))

    global ba

    if not os.path.exists(os.path.join(ba.server.API_DOCUMENT_ROOT, 'favicon.ico')):
        try:
            copyfile(os.path.join(ba.server.WWW_DOCUMENT_ROOT, 'favicon.ico'),
                     os.path.join(ba.server.API_DOCUMENT_ROOT, 'favicon.ico'))
        except IOError:
            pass

    #api root index
    api_index = {}
    api_index['tickers'] = ba.server.API_INDEX_URL + API_FILES['TICKER_PATH']
    api_index['global_tickers'] = ba.server.API_INDEX_URL + API_FILES['GLOBAL_TICKER_PATH']
    api_index['exchanges'] = ba.server.API_INDEX_URL + API_FILES['EXCHANGES_PATH']
    api_index['all'] = ba.server.API_INDEX_URL + API_FILES['ALL_FILE']
    api_index['ignored'] = ba.server.API_INDEX_URL + API_FILES['IGNORED_FILE']
    api_index['history'] = ba.server.API_INDEX_URL_HISTORY
    write_api_file(
        os.path.join(ba.server.API_DOCUMENT_ROOT, ba.config.INDEX_DOCUMENT_NAME),
        json.dumps(api_index, indent=2, sort_keys=True, separators=(',', ': ')))

    #api tickers index
    if not os.path.exists(os.path.join(ba.server.API_DOCUMENT_ROOT, API_FILES['TICKER_PATH'])):
        os.makedirs(os.path.join(ba.server.API_DOCUMENT_ROOT, API_FILES['TICKER_PATH']))

    api_ticker_index = {}
    api_ticker_index['all'] = ba.server.API_INDEX_URL + API_FILES['TICKER_PATH'] + API_FILES['ALL_FILE']
    api_ticker_folder_path = os.path.join(ba.server.API_DOCUMENT_ROOT, API_FILES['TICKER_PATH'])
    for currency_code in ba.config.CURRENCY_LIST:
        api_ticker_index[currency_code] = ba.server.API_INDEX_URL + API_FILES['TICKER_PATH'] + currency_code
        if not os.path.exists(os.path.join(api_ticker_folder_path, currency_code)):
            os.makedirs(os.path.join(api_ticker_folder_path, currency_code))
    write_api_file(
        os.path.join(ba.server.API_DOCUMENT_ROOT, API_FILES['TICKER_PATH'], ba.config.INDEX_DOCUMENT_NAME),
        json.dumps(api_ticker_index, indent=2, sort_keys=True, separators=(',', ': ')))

    #api global tickers index
    if not os.path.exists(os.path.join(ba.server.API_DOCUMENT_ROOT, API_FILES['GLOBAL_TICKER_PATH'])):
        os.makedirs(os.path.join(ba.server.API_DOCUMENT_ROOT, API_FILES['GLOBAL_TICKER_PATH']))

    api_ticker_index = {}
    api_ticker_index['all'] = ba.server.API_INDEX_URL + API_FILES['GLOBAL_TICKER_PATH'] + API_FILES['ALL_FILE']
    api_ticker_folder_path = os.path.join(ba.server.API_DOCUMENT_ROOT, API_FILES['GLOBAL_TICKER_PATH'])

    try:
        fiat_exchange_rates_url = ba.server.API_INDEX_URL + 'fiat_data'
        with Timeout(API_CALL_TIMEOUT_THRESHOLD, CallTimeoutException):
            result = urllib2.urlopen(urllib2.Request(url=fiat_exchange_rates_url, headers=API_REQUEST_HEADERS)).read()
            fiat_currencies_list = json.loads(result)

        for currency_code in fiat_currencies_list:
            api_ticker_index[currency_code] = ba.server.API_INDEX_URL + API_FILES['GLOBAL_TICKER_PATH'] + currency_code
            if not os.path.exists(os.path.join(api_ticker_folder_path, currency_code)):
                os.makedirs(os.path.join(api_ticker_folder_path, currency_code))
        write_api_file(
            os.path.join(ba.server.API_DOCUMENT_ROOT, API_FILES['GLOBAL_TICKER_PATH'], ba.config.INDEX_DOCUMENT_NAME),
            json.dumps(api_ticker_index, indent=2, sort_keys=True, separators=(',', ': ')))
    except (KeyError,ValueError,socket.error,simplejson.decoder.JSONDecodeError,urllib2.URLError,httplib.BadStatusLine,CallTimeoutException):
        pass

    #api exchanges index
    if not os.path.exists(os.path.join(ba.server.API_DOCUMENT_ROOT, API_FILES['EXCHANGES_PATH'])):
        os.makedirs(os.path.join(ba.server.API_DOCUMENT_ROOT, API_FILES['EXCHANGES_PATH']))

    api_exchanges_index = {}
    api_exchanges_index['all'] = ba.server.API_INDEX_URL + API_FILES['EXCHANGES_PATH'] + API_FILES['ALL_FILE']
    for currency_code in ba.config.CURRENCY_LIST:
        api_exchanges_index[currency_code] = ba.server.API_INDEX_URL + API_FILES['EXCHANGES_PATH'] + currency_code
    write_api_file(
        os.path.join(ba.server.API_DOCUMENT_ROOT, API_FILES['EXCHANGES_PATH'], ba.config.INDEX_DOCUMENT_NAME),
        json.dumps(api_exchanges_index, indent=2, sort_keys=True, separators=(',', ': ')))


    #api history index files
    if not os.path.exists(os.path.join(ba.server.HISTORY_DOCUMENT_ROOT)):
        os.makedirs(os.path.join(ba.server.HISTORY_DOCUMENT_ROOT))

    currency_history_links_list = {}
    for currency_code in ba.config.CURRENCY_LIST:
        _write_history_index_file(currency_code)
        currency_history_links_list[currency_code] = '%s%s/' % (ba.server.API_INDEX_URL_HISTORY, currency_code)

    general_index_file_path = os.path.join(ba.server.HISTORY_DOCUMENT_ROOT, ba.config.INDEX_DOCUMENT_NAME)
    write_api_file(
        general_index_file_path,
        json.dumps(currency_history_links_list, indent=2, sort_keys=True, separators=(',', ': ')))


def write_api_file(api_file_name, content, compress=True):
    with open(api_file_name, 'w') as api_file:
        api_file.write(content)
    if compress:
        with open(api_file_name, 'rb') as api_file:
            with gzip.open(api_file_name + '.gz', 'wb') as api_gzipped_file:
                api_gzipped_file.writelines(api_file)


def gzip_history_file(history_file_name):
    with open(history_file_name, 'rb') as history_file:
        with gzip.open(history_file_name + '.gz', 'wb') as history_gzipped_file:
            history_gzipped_file.writelines(history_file)

########NEW FILE########
__FILENAME__ = history_writers
import os
import time
import datetime
from decimal import Decimal
import csv
import json
import logging

import bitcoinaverage as ba
import bitcoinaverage.server
from bitcoinaverage import helpers
from bitcoinaverage.config import DEC_PLACES, CURRENCY_LIST

logger = logging.getLogger(__name__)


def write_24h_csv(currency_code, current_data, current_timestamp):
    current_24h_sliding_file_path = os.path.join(ba.server.HISTORY_DOCUMENT_ROOT, currency_code, 'per_minute_24h_sliding_window.csv')

    current_24h_sliding_data = []

    #to create file if not exists
    with open(current_24h_sliding_file_path, 'a') as csvfile:
        pass

    #read file
    with open(current_24h_sliding_file_path, 'rb') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        header_passed = False
        for row in csvreader:
            if not header_passed:
                header_passed = True
                continue
            last_recorded_timestamp = time.mktime(datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S').timetuple())
            if current_timestamp - last_recorded_timestamp < 86400: #60*60*24
                current_24h_sliding_data.append(row)

    last_recorded_timestamp = 0
    if len(current_24h_sliding_data) > 0:
        last_recorded_timestamp = time.mktime(datetime.datetime.strptime(current_24h_sliding_data[len(current_24h_sliding_data)-1][0],
                                                           '%Y-%m-%d %H:%M:%S').timetuple())
    else:
        logger.warning("{0} is empty".format(current_24h_sliding_file_path))

    if current_timestamp - last_recorded_timestamp > 60*2:
        #-60 added because otherwise the timestamp will point to the the beginning of next period and not current
        current_24h_sliding_data.append([datetime.datetime.strftime(datetime.datetime.fromtimestamp(current_timestamp-60), '%Y-%m-%d %H:%M:%S'),
                                         current_data['last']])

    with open(current_24h_sliding_file_path, 'wb') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',')
        csvwriter.writerow(['datetime','average'])
        for row in current_24h_sliding_data:
            csvwriter.writerow(row)


def write_24h_global_average_csv(fiat_data_all , currency_data_all, currency_code,  current_timestamp):
    current_24h_sliding_file_path = os.path.join(ba.server.HISTORY_DOCUMENT_ROOT, currency_code, 'per_minute_24h_global_average_sliding_window.csv')
    current_24h_sliding_data = []

    #to create file if not exists
    with open(current_24h_sliding_file_path, 'a') as csvfile:
        pass

    with open(current_24h_sliding_file_path, 'rb') as csvfile:
        csvreader = csv.DictReader(csvfile, delimiter=',')
        for row in csvreader:
            last_recorded_timestamp = time.mktime(datetime.datetime.strptime(row['datetime'], '%Y-%m-%d %H:%M:%S').timetuple())
            if current_timestamp - last_recorded_timestamp < 86400: #60*60*24
                current_24h_sliding_data.append(row)

    last_recorded_timestamp = 0
    if len(current_24h_sliding_data) > 0:
        last_recorded_timestamp = time.mktime(datetime.datetime.strptime(current_24h_sliding_data[len(current_24h_sliding_data)-1]['datetime'],
                                                          '%Y-%m-%d %H:%M:%S').timetuple())
    else:
        logger.warning("{0} is empty".format(current_24h_sliding_file_path))

    if current_timestamp - last_recorded_timestamp > 60*2:
        new_row = {}
        #-60 added because otherwise the timestamp will point to the the beginning of next period and not current
        timestamp = datetime.datetime.strftime(datetime.datetime.fromtimestamp(current_timestamp-60), '%Y-%m-%d %H:%M:%S')
        new_row['datetime'] = timestamp

        cross_rate_divisor = float(fiat_data_all[currency_code]['rate'])

        for currency in CURRENCY_LIST:
            cross_rate_dividend = float(fiat_data_all[currency]['rate'])
            currency_volume = currency_data_all[currency]['averages']['total_vol']
            currency_average = currency_data_all[currency]['averages']['last']
            currency_rate = cross_rate_dividend / cross_rate_divisor #this is cross rate in USD
            new_row[currency + ' volume'] = currency_volume
            new_row[currency + ' average'] = currency_average
            new_row[currency + ' rate'] = currency_rate

        currency_global_average = currency_data_all[currency_code]['global_averages']['last']
        new_row[currency_code + ' global average'] = currency_global_average
        current_24h_sliding_data.append(new_row)

    csv_currency_titles = []

    csv_currency_titles.append('datetime')

    for currency in CURRENCY_LIST:
        csv_currency_titles.append(currency + ' ' + 'volume')
        csv_currency_titles.append(currency + ' ' + 'average')
        csv_currency_titles.append(currency + ' ' + 'rate')

    csv_currency_titles.append(currency_code + ' ' + 'global average')

    with open(current_24h_sliding_file_path, 'wb') as csvfile:
        csvwriter = csv.DictWriter(csvfile, csv_currency_titles, restval=0, extrasaction='ignore', delimiter=',')
        csvwriter.writeheader()
        for row in current_24h_sliding_data:
            csvwriter.writerow(row)


def write_24h_global_average_short_csv(currency_data_all, currency_code,  current_timestamp):
    current_24h_sliding_file_path = os.path.join(ba.server.HISTORY_DOCUMENT_ROOT, currency_code, 'per_minute_24h_global_average_sliding_window_short.csv')
    current_24h_sliding_data = []

    #to create file if not exists
    with open(current_24h_sliding_file_path, 'a') as csvfile:
        pass

    with open(current_24h_sliding_file_path, 'rb') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        header_passed = False
        for row in csvreader:
            if not header_passed:
                header_passed = True
                continue
            last_recorded_timestamp = time.mktime(datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S').timetuple())
            if current_timestamp - last_recorded_timestamp < 86400: #60*60*24
                current_24h_sliding_data.append(row)

    last_recorded_timestamp = 0
    if len(current_24h_sliding_data) > 0:
        last_recorded_timestamp = time.mktime(datetime.datetime.strptime(current_24h_sliding_data[len(current_24h_sliding_data)-1][0],
                                                          '%Y-%m-%d %H:%M:%S').timetuple())
    else:
        logger.warning("{0} is empty".format(current_24h_sliding_file_path))

    if current_timestamp - last_recorded_timestamp > 60*2:
        row = []
        #-60 added because otherwise the timestamp will point to the the beginning of next period and not current
        timestamp = datetime.datetime.strftime(datetime.datetime.fromtimestamp(current_timestamp-60), '%Y-%m-%d %H:%M:%S')
        currency_global_average = currency_data_all[currency_code]['global_averages']['last']
        row.append(timestamp)
        row.append(currency_global_average)
        current_24h_sliding_data.append(row)

    csv_currency_titles = []

    csv_currency_titles.append('datetime')
    csv_currency_titles.append(currency_code + ' ' + 'global average')

    with open(current_24h_sliding_file_path, 'wb') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',')
        csvwriter.writerow( csv_currency_titles )
        for row in current_24h_sliding_data:
            csvwriter.writerow(row)


def write_1mon_csv(currency_code, current_timestamp):
    current_1h_1mon_sliding_file_path = os.path.join(ba.server.HISTORY_DOCUMENT_ROOT, currency_code, 'per_hour_monthly_sliding_window.csv')

    current_1mon_sliding_data = []
    with open(current_1h_1mon_sliding_file_path, 'a') as csvfile: #to create file if not exists
        pass

    with open(current_1h_1mon_sliding_file_path, 'rb') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',', )
        header_passed = False
        for row in csvreader:
            if not header_passed:
                header_passed = True
                continue
            timestamp = time.mktime(datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S').timetuple())
            if current_timestamp - timestamp < 2592000: #60*60*24*30
                current_1mon_sliding_data.append(row)

    last_recorded_timestamp = 0
    if len(current_1mon_sliding_data) > 0:
        last_recorded_timestamp = time.mktime(datetime.datetime.strptime(current_1mon_sliding_data[len(current_1mon_sliding_data)-1][0],
                                                           '%Y-%m-%d %H:%M:%S').timetuple())
    else:
        logger.warning("{0} is empty".format(current_1h_1mon_sliding_file_path))

    if int(time.time())-last_recorded_timestamp > 3600*2:
        current_24h_sliding_file_path = os.path.join(ba.server.HISTORY_DOCUMENT_ROOT, currency_code, 'per_minute_24h_sliding_window.csv')
        price_high = 0.0
        price_low = 0.0
        price_sum = Decimal(DEC_PLACES)
        index = 0
        with open(current_24h_sliding_file_path, 'rb') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',')
            header_passed = False
            for row in csvreader:
                if not header_passed:
                    header_passed = True
                    continue
                timestamp = time.mktime(datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S').timetuple())
                if current_timestamp - timestamp < 3600: #60*60
                    index = index + 1
                    price = float(row[1])
                    price_sum = price_sum + Decimal(price)
                    if price_high < price:
                        price_high = price
                    if price_low == 0 or price_low > price:
                        price_low = price
            try:
                price_avg = (price_sum / Decimal(index)).quantize(DEC_PLACES)
            except(ZeroDivisionError):
                price_avg = DEC_PLACES
        #-3600 added because otherwise the timestamp will point to the the beginning of next period and not current
        current_1mon_sliding_data.append([datetime.datetime.strftime(datetime.datetime.fromtimestamp(current_timestamp-3600), '%Y-%m-%d %H:%M:%S'),
                                          price_high,
                                          price_low,
                                          price_avg,
                                          ])

        with open(current_1h_1mon_sliding_file_path, 'wb') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')
            csvwriter.writerow(['datetime','high','low','average'])
            for row in current_1mon_sliding_data:
                csvwriter.writerow(row)


def write_forever_csv(currency_code, total_sliding_volume, current_timestamp):
    current_forever_file_path = os.path.join(ba.server.HISTORY_DOCUMENT_ROOT, currency_code, 'per_day_all_time_history.csv')

    if not os.path.exists(os.path.join(current_forever_file_path)) or os.path.getsize(current_forever_file_path) == 0:
        with open(current_forever_file_path, 'wb') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')
            csvwriter.writerow(['datetime','high','low','average','volume'])

    last_recorded_timestamp = 0
    with open(current_forever_file_path, 'rb') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        header_passed = False
        for row in csvreader:
            if not header_passed:
                header_passed = True
                continue
            # Last timestamp from the file points to the beginning of previous period
            last_recorded_timestamp = time.mktime(datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S').timetuple())

    timestamp_delta = datetime.timedelta(seconds=(current_timestamp - last_recorded_timestamp))
    if timestamp_delta >= datetime.timedelta(days=2):
        current_24h_sliding_file_path = os.path.join(ba.server.HISTORY_DOCUMENT_ROOT, currency_code, 'per_minute_24h_sliding_window.csv')
        price_high = 0.0
        price_low = 0.0
        price_sum = Decimal(DEC_PLACES)
        index = 0
        with open(current_24h_sliding_file_path, 'rb') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',')
            header_passed = False
            for row in csvreader:
                if not header_passed:
                    header_passed = True
                    continue
                timestamp = time.mktime(datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S').timetuple())
                if current_timestamp - timestamp < 86400:  # 1 day
                    index = index + 1
                    price = float(row[1])
                    price_sum = price_sum + Decimal(price)
                    if price_high < price:
                        price_high = price
                    if price_low == 0 or price_low > price:
                        price_low = price
            try:
                price_avg = (price_sum / Decimal(index)).quantize(DEC_PLACES)
            except(ZeroDivisionError):
                price_avg = DEC_PLACES

        with open(current_forever_file_path, 'ab') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')
            #-86400 added because otherwise the timestamp will point to the the beginning of next period and not current
            new_data_row = [datetime.datetime.strftime(
                                datetime.datetime.fromtimestamp(current_timestamp - 86400),
                                '%Y-%m-%d 00:00:00'),
                            price_high,
                            price_low,
                            price_avg,
                            total_sliding_volume,
                            ]
            csvwriter.writerow(new_data_row)


def write_volumes_csv(currency_code, currency_data, current_timestamp):
    current_volumes_file_path = os.path.join(ba.server.HISTORY_DOCUMENT_ROOT, currency_code, 'volumes.csv')

    with open(current_volumes_file_path, 'a') as csvfile: #to create file if not exists
        pass

    current_volumes_data = []
    exchanges_order = []
    headers = ['datetime', 'total_vol']
    with open(current_volumes_file_path, 'rb') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        header_passed = False
        for row in csvreader:
            if not header_passed:
                for header in row:
                    if header == 'datetime' or header == 'total_vol':
                        continue
                    headers.append(header)
                    header = header.replace(' BTC', '')
                    header = header.replace(' %', '')
                    if header not in exchanges_order:
                        exchanges_order.append(header)


                header_passed = True
                continue
            current_volumes_data.append(row)

    last_recorded_timestamp = 0
    if len(current_volumes_data) > 0:
        # Last timestamp from the file points to the beginning of previous period
        try:
            last_recorded_timestamp = time.mktime(datetime.datetime.strptime(current_volumes_data[len(current_volumes_data)-1][0],
                                                               '%Y-%m-%d %H:%M:%S').timetuple())
        except ValueError:
            last_recorded_timestamp = time.mktime(datetime.datetime.strptime(current_volumes_data[len(current_volumes_data)-1][0],
                                                               '%Y-%m-%d').timetuple())
    else:
        logger.warning("{0} is empty".format(current_volumes_file_path))

    timestamp_delta = datetime.timedelta(seconds=(current_timestamp - last_recorded_timestamp))
    if timestamp_delta >= datetime.timedelta(days=2):
        for exchange in currency_data['exchanges']:
            if exchange not in exchanges_order:
                exchanges_order.append(exchange)
                headers.append('%s BTC' % exchange)
                headers.append('%s %%' % exchange)

        new_data_row = []
        new_data_row.append(datetime.datetime.strftime(
            datetime.datetime.fromtimestamp(current_timestamp - 86400),
            '%Y-%m-%d 00:00:00'))
        new_data_row.append(currency_data['averages']['total_vol'])

        for exchange in exchanges_order:
            if exchange in currency_data['exchanges']:
                new_data_row.append(currency_data['exchanges'][exchange]['volume_btc'])
                new_data_row.append(currency_data['exchanges'][exchange]['volume_percent'])
            else:
                new_data_row.append(0)
                new_data_row.append(0)

        with open(current_volumes_file_path, 'wb') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')
            csvwriter.writerow(headers)
            for row in current_volumes_data:
                csvwriter.writerow(row)

            csvwriter.writerow(new_data_row)

########NEW FILE########
__FILENAME__ = history_daemon
#!/usr/bin/python2.7
import os
import sys

import time
import requests
import simplejson
import json
import datetime
import email
import logging

import bitcoinaverage as ba
from bitcoinaverage.config import HISTORY_QUERY_FREQUENCY, CURRENCY_LIST
from bitcoinaverage import history_writers

logger = logging.getLogger("history_daemon")
logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.WARNING)
logger.info("script started")


for currency_code in CURRENCY_LIST:
    if not os.path.exists(os.path.join(ba.server.HISTORY_DOCUMENT_ROOT, currency_code)):
        os.makedirs(os.path.join(ba.server.HISTORY_DOCUMENT_ROOT, currency_code))

while True:
    ticker_url = ba.server.API_INDEX_URL+'all'
    fiat_data_url = ba.server.API_INDEX_URL+'fiat_data'
    try:
        current_data_all = requests.get(ticker_url, headers=ba.config.API_REQUEST_HEADERS).json()
        fiat_data_all = requests.get(fiat_data_url, headers=ba.config.API_REQUEST_HEADERS).json()
    except (simplejson.decoder.JSONDecodeError, requests.exceptions.ConnectionError), err:
        logger.warning("can not get API data: {0}".format(str(err)))
        time.sleep(10)
        continue

    current_data_datetime = current_data_all['timestamp']
    current_data_datetime = current_data_datetime[:-6] #prior to python 3.2 strptime doesnt work properly with numeric timezone offsets.
    current_data_datetime = datetime.datetime.strptime(current_data_datetime, '%a, %d %b %Y %H:%M:%S')
    current_data_timestamp = int((current_data_datetime - datetime.datetime(1970, 1, 1)).total_seconds())

    for currency_code in CURRENCY_LIST:
        try:
            history_writers.write_24h_csv(currency_code, current_data_all[currency_code]['averages'], current_data_timestamp)
            history_writers.write_1mon_csv(currency_code, current_data_timestamp)
            history_writers.write_forever_csv(currency_code, current_data_all[currency_code]['averages']['total_vol'], current_data_timestamp)
            history_writers.write_volumes_csv(currency_code, current_data_all[currency_code], current_data_timestamp)

            history_writers.write_24h_global_average_csv(fiat_data_all, current_data_all,  currency_code, current_data_timestamp)
            history_writers.write_24h_global_average_short_csv(current_data_all,  currency_code, current_data_timestamp)
        except KeyError, err:
            logger.warning(str(err))

    current_time = time.time()
    timestamp = email.utils.formatdate(current_time)
    sleep_time = HISTORY_QUERY_FREQUENCY - (current_time % HISTORY_QUERY_FREQUENCY)
    sleep_time = min(HISTORY_QUERY_FREQUENCY, sleep_time)

    logger.info("{0}, sleeping {1}s - history daemon".format(timestamp, str(sleep_time)))

    time.sleep(sleep_time)



########NEW FILE########
__FILENAME__ = image_daemon
# Script to create dynamic PNG to include live price

import os
import sys
import requests
import time
from PIL import Image, ImageDraw, ImageFont
from bitcoinaverage.server import FONT_PATH, WWW_DOCUMENT_ROOT
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO


# config locations
base_url = "https://api.bitcoinaverage.com/ticker/"
base = WWW_DOCUMENT_ROOT + "/img/" + "logo_xsmall.png"
font_loc = FONT_PATH + "arialbd.ttf"


def filename(cur):
    filename = WWW_DOCUMENT_ROOT + "/img/" + "price_small_" + cur + ".png"
    return filename

def pil_image(cur):

    white = (255,255,255) # colour of background
    grey = (79,79,79)
    light_grey = (247,247,247)
    blue = (66,139,202)
    light_blue = (139,182,220)

    base_im = Image.open(base, 'r') # open base image
    im = Image.new("RGB", [180,55], light_grey)
    draw = ImageDraw.Draw(im)   # create a drawing object that is used to draw on the new image

    rate_text = get_rate(cur) # text to draw
    domain_text = "BitcoinAverage.com"

    # drawing
    draw.text((65,5), rate_text, fill=grey, font=ImageFont.truetype(font_loc, 24))
    draw.text((55,35), domain_text, fill=light_blue, font=ImageFont.truetype(font_loc, 12))
    im.paste(base_im, (2,12))

    # save open image as PNG
    im.save(filename(cur), 'PNG')

    return filename # and we're done!

def get_rate(cur):

    if cur is "usd":
        url = base_url + "USD"
        r = requests.get(url).json()
        rate = "$" + str(r['last'])
    elif cur is "eur":
        url = base_url + "EUR"
        r = requests.get(url).json()
        rate = u"\u20AC" + str(r['last'])
    elif cur is "gbp":
        url = base_url + "GBP"
        r = requests.get(url).json()
        rate = u"\u00A3" + str(r['last'])

    return rate


while True:

    pil_image("usd")
    pil_image("eur")
    pil_image("gbp")

    time.sleep(60*5)
########NEW FILE########
__FILENAME__ = monitor_daemon
#!/usr/bin/env python

import os
import simplejson
import subprocess
import re
import time
import requests
import datetime
import csv
import StringIO
from email import Utils

ticker_URL = "http://api.bitcoinaverage.com/ticker/USD"
history_URL = "http://api.bitcoinaverage.com/history/USD/per_minute_24h_sliding_window.csv"

# email address to use in the to field
recipient = 'bitcoinaverage@gmail.com'

# email address to use in the from field
sender = 'bitcoinaverage@gmail.com'

# email body
message = '''To: %s
From: %s
Subject: The %s Daemon is Down!

It seems that the %s daemon may have died '''


def process_exists(proc_name):
    ps = subprocess.Popen("ps ax -o pid= -o args= ", shell=True, stdout=subprocess.PIPE)
    ps_pid = ps.pid
    output = ps.stdout.read()
    ps.stdout.close()
    ps.wait()

    for line in output.split("\n"):
        res = re.findall("(\d+) (.*)", line)
        if res:
            pid = int(res[0][0])
            if proc_name in res[0][1] and pid != os.getpid() and pid != ps_pid:
                return True
    return False

def api_time_diff():
    try:
        r = requests.get(ticker_URL).json()
    except(simplejson.decoder.JSONDecodeError, requests.exceptions.ConnectionError):
        return None

    current_data_datetime = r['timestamp']
    current_time = time.time()
    
    current_data_datetime = current_data_datetime[:-6] #prior to python 3.2 strptime doesnt work properly with numeric timezone offsets.
    current_data_datetime = datetime.datetime.strptime(current_data_datetime, '%a, %d %b %Y %H:%M:%S')
    current_data_timestamp = int((current_data_datetime - datetime.datetime(1970, 1, 1)).total_seconds())
    
    diff = current_time - current_data_timestamp
    return diff

def history_time_diff():
    try:
        csv_result = requests.get(history_URL).text
    except(simplejson.decoder.JSONDecodeError, requests.exceptions.ConnectionError):
        return None

    csvfile = StringIO.StringIO(csv_result)
    csvreader = csv.reader(csvfile, delimiter=',')
    
    history_list = []
    
    for row in csvreader:
        history_list.append(row)
        last_log = history_list[-1]
    
    current_data_datetime = last_log[0]
    current_time = time.time()

    try:
        current_data_datetime = datetime.datetime.strptime(current_data_datetime, '%Y-%m-%d %H:%M:%S')
        current_data_timestamp = int((current_data_datetime - datetime.datetime(1970, 1, 1)).total_seconds())
    except ValueError:
        return None

    diff = (current_time - current_data_timestamp)
    return diff

def send_email(daemon):
    try:
        ssmtp = subprocess.Popen(('/usr/sbin/ssmtp', recipient), stdin=subprocess.PIPE)
    except OSError:
        print 'could not start sSMTP, email not sent'
    # pass the email contents to sSMTP over stdin
    ssmtp.communicate(message % (recipient, sender, daemon, daemon))
    # wait until the email has finished sending
    ssmtp.wait()

while True:
    api_time_difference = api_time_diff()
    if api_time_difference is None or api_time_difference > float(5*60):
        print "api_daemon.py - Frozen"
        send_email("API")
	
    history_time_difference = history_time_diff()
    if history_time_difference is None or history_time_difference > float(5*60):
        print "history_daemon.py - Frozen"
        send_email("History")
	

#    if process_exists('api_daemon.py') == False:
#	print("api_daemon.py - Not running")
#	#os.system(mailApi)
#	send_email("API")
#	
#    if process_exists('history_daemon.py') == False:
#	print("history_daemon.py - Not Running")
#	#os.system(mailHistory)
#	send_email("History")

    timestamp = Utils.formatdate(time.time())
    print timestamp + " - monitor_daemon.py"

    time.sleep(120)
    
########NEW FILE########
__FILENAME__ = parser_daemon
#!/usr/bin/python2.7
import time
import logging

import redis
import simplejson as json
import eventlet

from bitcoinaverage import api_parsers
from bitcoinaverage.config import API_QUERY_FREQUENCY, EXCHANGE_LIST

logger = logging.getLogger("parser_daemon")

logger.info("started API parser daemon")

red = redis.StrictRedis(host="localhost", port=6379, db=0)
red.delete("ba:exchanges", "ba:exchanges_ignored")  # Reset

pool = eventlet.GreenPool()
queue = eventlet.Queue()

def worker(exchange_name, q):
    result = api_parsers.callAPI(exchange_name)
    q.put(result)

for exchange_name in EXCHANGE_LIST:
    pool.spawn_n(worker, exchange_name, queue)

while True:
    start_time = time.time()

    results = []
    while not queue.empty():
        results.append(queue.get())

    for exchange_name, exchange_data, exchange_ignore_reason in results:
        if exchange_ignore_reason is None:
            red.hset("ba:exchanges",
                     exchange_name,
                     json.dumps(exchange_data, use_decimal=True))
            red.hdel("ba:exchanges_ignored", exchange_name)
        else:
            red.hset("ba:exchanges_ignored",
                     exchange_name,
                     exchange_ignore_reason)
            red.hdel("ba:exchanges", exchange_name)
        pool.spawn_n(worker, exchange_name, queue)
    logger.info("saved {0} results".format(len(results)))

    cycle_time = time.time() - start_time
    sleep_time = max(0, API_QUERY_FREQUENCY['_all'] - cycle_time)
    logger.info("spent {0}, sleeping {1}".format(cycle_time, sleep_time))
    eventlet.sleep(sleep_time)

########NEW FILE########
__FILENAME__ = twitter_daemon
#!/usr/bin/env python

import time
import logging

import twitter
import simplejson
import requests

from bitcoinaverage.twitter_config import api

logger = logging.getLogger("twitter_daemon")

URL = "https://api.bitcoinaverage.com/ticker/global/USD"

change = 0
oldprice = 0
perc = 0
direction = ""

while True:
    try:
        r = requests.get(URL).json()
    except(simplejson.decoder.JSONDecodeError, requests.exceptions.ConnectionError):
        time.sleep(2)
        continue

    newprice = r['last']
    
    if oldprice > newprice:
        b = oldprice - newprice
        change = round(b, 2)
        direction = "down"
        if oldprice != 0:
            a = (change / oldprice)*100
            perc = round(a, 2)
    elif oldprice < newprice:
        b = newprice - oldprice
        change = round(b, 2)
        direction = "up"
        if oldprice != 0:
            a = (change / oldprice)*100
            perc = round(a, 2)
            
    if perc != 0 and change != 0 and direction != "":
        status = "BitcoinAverage price index: ${0} ({1} ${2}) - https://BitcoinAverage.com".format(newprice,direction,change)
    else:
        status = "BitcoinAverage price index: ${0} - https://BitcoinAverage.com".format(newprice)

    try:
        result = api.PostUpdate(status)
    except twitter.TwitterError, err:
        logger.error("Twitter error: {0}".format(str(err)))
    else:
        oldprice = newprice

    time.sleep(3600)

########NEW FILE########
