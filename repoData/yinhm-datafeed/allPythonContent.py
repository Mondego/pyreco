__FILENAME__ = config_example

# Server address
# Used for WJF client.
SERVER_ADDR = '10.0.0.2'

# Set password to enable authtication
# Default to None, no auth needed.
# AUTH_PASSWORD = 'YourPassword'
AUTH_PASSWORD = None

########NEW FILE########
__FILENAME__ = bidict
#!/usr/bin/env python
"""A bidirectional dict.
"""
import itertools

class Bidict(dict):
    def __init__(self, iterable=(), **kwargs):
        self.update(iterable, **kwargs)

    def update(self, iterable=(), **kwargs):
        if hasattr(iterable, 'iteritems'):
            iterable = iterable.iteritems()
        for (key, value) in itertools.chain(iterable, kwargs.iteritems()):
            self[key] = value

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        if value in self:
            del self[value]
        dict.__setitem__(self, key, value)
        dict.__setitem__(self, value, key)

    def __delitem__(self, key):
        value = self[key]
        dict.__delitem__(self, key)
        dict.__delitem__(self, value)

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, dict.__repr__(self))

########NEW FILE########
__FILENAME__ = client
import errno
import marshal
import socket
import zlib

import numpy as np

from cStringIO import StringIO

from datafeed.utils import json_decode


__all__ = ['Client', 'ConnectionError']


class ConnectionError(Exception):
    pass


class Client(object):
    """Manages Tcp communication to and from a datafeed server.
    """

    def __init__(self, host='localhost', port=8082,
                 password=None, socket_timeout=None):
        self._host = host
        self._port = port
        self._password = password
        self._socket_timeout = socket_timeout

        self._sock = None
        self._fp = None

    def connect(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self._host, self._port))
        except socket.error, e:
            # args for socket.error can either be (errno, "message")
            # or just "message"
            if len(e.args) == 1:
                error_message = "Error connecting to %s:%s. %s." % \
                    (self.host, self.port, e.args[0])
            else:
                error_message = "Error %s connecting %s:%s. %s." % \
                    (e.args[0], self._host, self._port, e.args[1])
            raise ConnectionError(error_message)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(self._socket_timeout)
        self._sock = sock
        self._fp = sock.makefile('rb')

        if self._password:
            self.auth()

    @property
    def connected(self):
        return self._sock

    def close(self):
        self.disconnect()

    def disconnect(self):
        if not self.connected:
            return
        try:
            self._sock.close()
        except socket.error:
            pass
        self._sock = None
        self._fp = None

    def reconnect(self):
        self.disconnect()
        self.connect()

    def ensure_connected(self):
        '''TODO: move to a closure?'''
        if not self.connected:
            self.connect()

    def read(self, length=None):
        self.ensure_connected()
        try:
            if length is not None:
                return self._fp.read(length)
            return self._fp.readline()
        except socket.error, e:
            self.disconnect()
            if e.args and e.args[0] == errno.EAGAIN:
                raise StandardError("Error while reading from socket: %s" % \
                                        e.args[1])
        return ''


    #### COMMAND EXECUTION AND PROTOCOL PARSING ####
    def execute_command(self, *args):
        """Sends the command to the server and returns it's response.

        *<number of arguments> CR LF
        $<number of bytes of argument 1> CR LF
        <argument data> CR LF
        ...
        $<number of bytes of argument N> CR LF
        <argument data> CR LF


        See the following example:
        
        *3
        $3
        SET
        $5
        mykey
        $7
        myvalue
        """
        return self._execute_command(args[0], args[-1], self._build_data(*args))

    def _build_data(self, *args):
        cmds = ('$%s\r\n%s\r\n' % (len(arg), arg) for arg in args)
        return '*%s\r\n%s' % (len(args), ''.join(cmds))

    def _execute_command(self, command, format, data):
        self.send(data)
        return self._parse_response(command, format)
    
    def send(self, data):
        self.ensure_connected()
        try:
            self._sock.sendall(data)
        except socket.error, e:
            if self.reconnect():
                self._sock.sendall(data)
            else:
                raise StandardError("Error %s while writing to socket. %s." % \
                                        e.args)

    def _parse_response(self, command, format):
        response = self.read()[:-2]  # strip last two characters (\r\n)
        if not response:
            self.disconnect()
            raise StandardError("Socket closed on remote end")

        # server returned a null value
        if response in ('$-1', '*-1'):
            return None
        reply_type, response = response[0], response[1:]

        # server returned an error
        if reply_type == '-':
            if response.startswith('ERR '):
                response = response[4:]
            raise Exception(response)
        # single value
        elif reply_type == '+':
            return response
        # integer value
        elif reply_type == ':':
            return int(response)
        # bulk response
        elif reply_type == '$':
            length = int(response)
            response = length and self.read(length) or ''
            self.read(2) # read the \r\n delimiter

            if format == 'json':
                return json_decode(response)
            elif format == 'npy':
                qdata = StringIO(response)
                return np.load(qdata)
            else:
                return response

        raise Exception("Unknown response type for: %s" % command)

    def auth(self):
        self.execute_command('AUTH', self._password, 'plain')

    def get_mtime(self):
        return self.execute_command('GET_MTIME', 'plain')

    def get_list(self, match='', format='json'):
        return self.execute_command('GET_LIST', match, format)

    def get_report(self, symbol, format='json'):
        return self.execute_command('GET_REPORT', symbol, format)

    def get_reports(self, *args, **kwargs):
        format = 'json'
        if 'format' in kwargs:
            format = kwargs['format']
        args = args + (format,)
        return self.execute_command('GET_REPORTS', *args)

    def get_minute(self, symbol, timestamp=0, format='npy'):
        """Get minute history data.

        timestamp: 0 for last day data.
        """
        assert isinstance(timestamp, int)
        return self.execute_command('GET_MINUTE', symbol, str(timestamp), format)

    def get_1minute(self, symbol, date, format='npy'):
        """Get minute history data.

        date: specific day to retrieve.
        """
        return self.execute_command('GET_1MINUTE', symbol, date, format)

    def get_5minute(self, symbol, date, format='npy'):
        """Get minute history data.

        date: specific day to retrieve.
        """
        return self.execute_command('GET_5MINUTE', symbol, date, format)

    def get_day(self, symbol, length_or_date, format='npy'):
        assert isinstance(length_or_date, int) or len(length_or_date) == 8
        return self.execute_command('GET_DAY', symbol, str(length_or_date), format)

    def get_dividend(self, symbol, format='npy'):
        return self.execute_command('GET_DIVIDEND', symbol, format)

    def get_fin(self, symbol, format='npy'):
        return self.execute_command('GET_FIN', symbol, format)

    def get_sector(self, name, format='json'):
        return self.execute_command('GET_SECTOR', name, format)

    def get_stats(self):
        return self.execute_command('GET_STATS', 'json')

    def put_reports(self, adict):
        assert isinstance(adict, dict)
        data = zlib.compress(marshal.dumps(adict))
        return self.execute_command('PUT_REPORTS', data, 'zip')

    def put_minute(self, symbol, rawdata):
        memfile = StringIO()
        np.save(memfile, rawdata)
        return self.execute_command('PUT_MINUTE', symbol, memfile.getvalue(), 'npy')

    def put_1minute(self, symbol, rawdata):
        memfile = StringIO()
        np.save(memfile, rawdata)
        return self.execute_command('PUT_1MINUTE', symbol, memfile.getvalue(), 'npy')

    def put_5minute(self, symbol, rawdata):
        memfile = StringIO()
        np.save(memfile, rawdata)
        return self.execute_command('PUT_5MINUTE', symbol, memfile.getvalue(), 'npy')

    def put_day(self, symbol, rawdata):
        memfile = StringIO()
        np.save(memfile, rawdata)
        return self.execute_command('PUT_DAY', symbol, memfile.getvalue(), 'npy')

    def archive_minute(self):
        return self.execute_command('ARCHIVE_MINUTE')

########NEW FILE########
__FILENAME__ = datastore
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010 yinhm

'''A datastore for quotes data management.

Datastore manager two types of data, one is archived data, they are stored at
one HDF5 file.

 * Day 1day OHLC
 * OneMinute: 1minute OHLC
 * FiveMinute: 5minute OHLC
 * HDF5 Minute: minute snapshot

Another type is data that has high update frequency, are stored at DictStore:

 * Report: snapshot of current price
 * MinuteSnapshotCache Minute: In session minute snapshots

There are two other stores: Dividend, Sector, we storing them to DictStore for
convenience.


Notice
======
Every market has diffrenct open/close time, etc. For now, datastore only
support one market, or several markets that have the same open/close time, then
you could distinguish them by prefix.
'''

import atexit
import datetime
import h5py
import logging
import marshal
import os
import time

import UserDict

import cPickle as pickle
import numpy as np


from datafeed.utils import *


__all__ = ['Manager', 'Minute', 'Day', 'OneMinute', 'FiveMinute',
           'DictStore', 'DictStoreNamespace', 'Report', 'MinuteSnapshotCache']

def date2key(date):
    '''Return formatted key from date.'''
    return date.strftime('%Y%m%d')


class Manager(object):
    '''Manager of datastores.

    It responsible for:
      * Managing different stores.
      * Dispatching read/write dataflows(this may change).
      * Rotating daily minutes snapshot.
   '''
    def __init__(self, datadir, exchange):
        self.datadir = datadir
        self.exchange = exchange

        logging.debug("Loading h5file and memory store...")
        self._store = h5py.File(os.path.join(self.datadir, 'data.h5'))
        self._dstore = DictStore.open(os.path.join(self.datadir, 'dstore.dump'))

        # Dict Store
        self._reportstore = None
        self._sectorstore = None
        self._divstore = None
        self._minutestore = None

        # HDF5 Store
        self._daystore = None
        self._1minstore = None
        self._5minstore = None

        self._mtime = None

        atexit.register(self.close)

    @property
    def divstore(self):
        '''Get dividend store instance or initialize if not present.
        '''
        if not self._divstore:
            self._divstore = Dividend(self._dstore)

        return self._divstore

    @property
    def reportstore(self):
        '''Get report instance or initialize if not present.

        :returns:
            Report instance.
        '''
        if not self._reportstore:
            logging.debug("Loading reports...")
            self._reportstore = Report(self._dstore)

        return self._reportstore

    @property
    def sectorstore(self):
        '''Get sector instance or initialize if not present.

        :returns:
            Report instance.
        '''
        if not self._sectorstore:
            logging.debug("Loading sectors...")
            self._sectorstore = Sector(self._dstore)

        return self._sectorstore

    @property
    def daystore(self):
        '''Get day instance or initialize if not present.

        :returns:
            Day instance.
        '''
        if not self._daystore:
            logging.info("Loading ohlcs...")
            self._daystore = Day(self._store)

        return self._daystore

    @property
    def minutestore(self):
        '''Return instance of last minutestore which should contains minute
        historical data.

        :returns:
            Minute instance.
        '''
        if not self._minutestore:
            logging.info("Loading minutestore at %d...", self.mtime)
            self._minutestore = self.get_minutestore_at(self.mtime,
                                                        memory=True)

        return self._minutestore

    def get_minutestore_at(self, timestamp, memory=None):
        """Get minutestore at given timestamp.

        If memory was not specified:

            * default to memory store for current date;
            * to file store for old date;
        """
        date = datetime.datetime.fromtimestamp(timestamp).date()
        if self._minutestore and \
                self._minutestore.date == date and \
                memory != False:
            return self._minutestore
        else:
            return self._minutestore_at(date, memory=memory)

    def _minutestore_at(self, date, memory=None):
        '''Return minute store at the given date.'''
        today = datetime.date.today()
        if memory or (memory == None and date == today):
            # Known issue:
            # Suppose server crashes, we restart it after couple of hours, then
            # we supply snapshots data, since minute store havn't rotated yet,
            # we may ends up with junk data, eg: SH600000 got suspended,
            # no fresh data for today, so minute store will holding some old
            # snapshots.
            f = MinuteSnapshotCache(self._dstore, date)
        else:
            f = self._store
        return Minute(f, date, self.exchange.market_minutes)

    @property
    def oneminstore(self):
        '''Get 1min ohlcs store instance or initialize if not present.

        :returns:
            OneMinute instance.
        '''
        if not self._1minstore:
            self._1minstore = OneMinute(self._store, self.exchange.market_minutes)

        return self._1minstore

    @property
    def fiveminstore(self):
        '''Get 5min ohlcs store instance or initialize if not present.

        :returns:
            FiveMinute instance.
        '''
        if not self._5minstore:
            self._5minstore = FiveMinute(self._store, self.exchange.market_minutes)

        return self._5minstore

    def rotate_minute_store(self):
        ''' Rotate minute store when new trading day data flowed in.
        '''
        date = datetime.datetime.fromtimestamp(self.mtime).date()
        if self._minutestore and date != self._minutestore.date:
            logging.info("==> Ratate minute store...")
            # _minutestore was always stored in cache,
            # we need to rewrite it to Minute store for persistent.
            tostore = self._minutestore_at(self._minutestore.date, memory=False)
            self._minutestore.store.rotate(tostore)
            self._minutestore = None

        return self.minutestore

    @property
    def mtime(self):
        "Modify time, updated we report data received."
        return self._mtime

    def set_mtime(self, ts):
        if ts > self.mtime:
            self._mtime = ts
    
    @property
    def last_quote_time(self):
        logging.warning("Deprecated, using mtime instead.")
        return self.mtime
    
    def get_report(self, symbol):
        """Get report by symbol."""
        return self.reportstore[symbol]
        
    def get_reports(self, *args):
        """Get reports by symbols.

        Return:
          dict iterator
        """
        if len(args) > 0:
            store = self.reportstore
            ret = dict([(symbol, store.get(symbol)) for symbol in args if store.has_key(symbol) ])
        else:
            ret = self.reportstore.iteritems()
            
        return ret

    def update_reports(self, data):
        if len(data) == 0:
            return
        time = data[data.keys()[0]]['timestamp']
        self.set_mtime(time)
        self.reportstore.update(data)

    def update_minute(self, symbol, data):
        # determine datastore first
        for minute in data:
            timestamp = minute['time']
            break
        store = self.get_minutestore_at(timestamp)
        store.update(symbol, data)
    
    def update_day(self, symbol, data):
        self.daystore.update(symbol, data)

    def update_dividend(self, symbol, data):
        if len(data) == 0:
            return
        
        try:
            self.divstore[symbol] = data
        except ValueError:
            del self.divstore[symbol]
            self.divstore[symbol] = data

    def close(self):
        logging.debug("datastore shutdown, saving data.")
        self._dstore.close()


class DictStore(dict):

    def __init__(self, filename, odict):
        self.filename = filename
        self.closed = False
        super(DictStore, self).__init__(odict)

    def require_group(self, key):
        if not self.has_key(key):
            self.__setitem__(key, dict())
        return self.__getitem__(key)

    @classmethod
    def open(cls, filename):
        data = {}
        if os.path.exists(filename):
            data = pickle.load(open(filename, 'rb'))
        return cls(filename, data)

    def close(self):
        self.flush()
        self.closed = True

    def flush(self):
        pickle.dump(self.items(), open(self.filename, 'wb+'), -1)


class DictStoreNamespace(object, UserDict.DictMixin):
    def __init__(self, store):
        self.store = store
        klass = self.__class__.__name__
        if klass == 'DictStoreNamespace':
            raise StandardError("Can not initialize directly.")
        self.handle = store.require_group(klass.lower())

    def __repr__(self):
        return '%s(...)' % self.__class__.__name__

    def to_dict(self):
        return self.handle

    def flush(self):
        self.store.flush()

    def keys(self):
        assert not self.store.closed
        return self.handle.keys()

    def __len__(self):
        assert not self.store.closed
        return len(self.handle)

    def __nonzero__(self):
        "Truth value testing, always return True."
        assert not self.store.closed
        return True

    def has_key(self, key):
        assert not self.store.closed
        return key in self.handle

    def set(self, key, value):
        self.__setitem__(key, value)

    def get(self, key):
        return self.__getitem__(key)

    def __setitem__(self, key, value):
        assert not self.store.closed
        self.handle.__setitem__(key, value)

    def __getitem__(self, key):
        assert not self.store.closed
        return self.handle.__getitem__(key)

    def __delitem__(self, key):
        assert not self.store.closed
        return self.handle.__delitem__(key)

class Report(DictStoreNamespace):
    pass

class Sector(DictStoreNamespace):
    pass

class Dividend(DictStoreNamespace):
    pass


class OHLC(object):
    '''OHLC data archive.'''

    DTYPE = np.dtype({'names': ('time', 'open', 'high', 'low', 'close', 'volume', 'amount'),
                      'formats': ('i4', 'f4', 'f4', 'f4', 'f4', 'f4', 'f4')})

    time_interval = 60 # default to 60 seconds(1min)
    _handle = None

    def __init__(self, store, market_minutes=None):
        '''Init day store from handle.

        Handle should be in each implementors namespace, eg:

          day: /day
          1min: /1min
          5min: /5min
        '''
        self.store = store

        self.shape_x = None
        if market_minutes:
            self.shape_x = market_minutes / (self.time_interval / 60)

    def __nonzero__(self):
        "Truth value testing."
        return True

    @property
    def handle(self):
        raise StandardError("No implementation.")

    def flush(self):
        self.handle.file.flush()

    def get(self, symbol, date):
        """Get minute history quote data for a symbol.

        Raise:
          KeyError: if symbol not exists.

        Return:
          numpy data
        """
        key = self._key(symbol, date)
        return self.handle[key][:]

    def update(self, symbol, quotes):
        """Archive daily ohlcs, override if datasets exists."""
        assert quotes['time'][0] < quotes['time'][1], \
            'Data are not chronological ordered.'

        if self.shape_x:
            self._update_multi(symbol, quotes)
        else:
            self._update(symbol, quotes)

    def _update(self, symbol, quotes):
        """Archive daily ohlcs, override if datasets exists.

        Arguments:
          symbol: Stock instrument.
          quotes: numpy quotes data.
        """
        i = 0
        pre_ts = 0
        indexes = []
        for q in quotes:
            # 2 hours interval should be safe for seperate daily quotes
            if pre_ts and (q['time'] - pre_ts) > 7200:
                indexes.append(i)
            pre_ts = q['time']
            i += 1
        indexes.append(i)

        pre_index = 0
        for i in indexes:
            sliced_qs = quotes[pre_index:i]
            date = datetime.datetime.fromtimestamp(sliced_qs[0]['time']).date()
            try:
                ds = self._require_dataset(symbol, date, sliced_qs.shape)
            except TypeError, e:
                if e.message.startswith('Shapes do not match'):
                    self._drop_dataset(symbol, date)
                    ds = self._require_dataset(symbol, date, sliced_qs.shape)
                else:
                    raise e
            ds[:] = sliced_qs
            pre_index = i

    def _update_multi(self, symbol, quotes):
        """Archive multiday ohlcs, override if datasets exists.

        Arguments:
          symbol: Stock instrument.
          quotes: numpy quotes data.
        """
        i = 0
        pre_day = None
        indexes = []
        indexes.append([0, len(quotes)])
        for row in quotes:
            day = datetime.datetime.fromtimestamp(row['time']).day
            if pre_day and pre_day != day:
                # found next day boundary
                indexes[-1][1] = i
                indexes.append([i, len(quotes)])
            i += 1
            pre_day = day

        for i0, i1 in indexes:
            t0, t1 = quotes[i0]['time'], quotes[i1-1]['time']
            dt = datetime.datetime.fromtimestamp(t0)
            dsi0, dsi1 = self.timestamp_to_index(dt, t0), self.timestamp_to_index(dt, t1)

            sliced = quotes[i0:i1]
            ds = self._require_dataset(symbol, dt.date(), sliced.shape)

            if dsi0 != 0:
                dsi1 = dsi1 + 1
            logging.debug("ds[%d:%d] = quotes[%d:%d]" % (dsi0, dsi1, i0, i1))
            try:
                ds[dsi0:dsi1] = sliced
            except TypeError:
                logging.debug("data may have holes")
                for row in sliced:
                    r_dsi = self.timestamp_to_index(dt, row['time'])
                    # logging.debug("r_dsi: %d" % r_dsi)
                    ds[r_dsi] = row

    def timestamp_to_index(self, dt, ts):
        day_start = time.mktime((dt.year, dt.month, dt.day,
                                 0, 0, 0, 0, 0, 0))
        return int((ts - day_start) / self.time_interval)

    def _require_dataset(self, symbol, date, shape=None):
        '''Require dateset for a specific symbol on the given date.'''
        assert self.shape_x or shape

        key = self._key(symbol, date)
        if self.shape_x:
            shape = (self.shape_x, )
        return self.handle.require_dataset(key,
                                           shape,
                                           dtype=self.DTYPE)

    def _drop_dataset(self, symbol, date):
        '''Require dateset for a specific symbol on the given date.'''
        key = self._key(symbol, date)
        del(self.handle[key])


    def _key(self, symbol, date):
        '''Format key path.'''
        # datetime.datetime.fromtimestamp(timestamp).date()
        return "%s/%s" % (symbol, date2key(date))


class Day(OHLC):
    '''Archive of daily OHLCs data.

    OHLCs are grouped by symbol and year:

        SH000001/2009
        SH000001/2010
        SH000002/2009
        SH000002/2010
    '''

    # ISO 8601 year consists of 52 or 53 full weeks.
    # See: http://en.wikipedia.org/wiki/ISO_8601
    WORKING_DAYS_OF_YEAR = 53 * 5
    
    @property
    def handle(self):
        if not self._handle:
            self._handle = self.store.require_group('day')
        return self._handle

    def get(self, symbol, length):
        year = datetime.datetime.today().isocalendar()[0]
        try:
            data = self._get_year_data(symbol, year)
        except KeyError:
            self.handle[symbol] # test symbol existence
            data = []

        while True:
            if len(data) >= length:
                break
            
            year = year - 1
            try:
                ydata = self._get_year_data(symbol, year)
            except KeyError:
                # wrong length
                return data
            
            if len(ydata) == 0:
                break

            if len(data) == 0:
                data = ydata
            else:
                data = np.append(ydata, data)
        return data[-length:]

    def get_by_date(self, symbol, date):
        year = date.isocalendar()[0]
        ds = self._dataset(symbol, year)
        index = self._index_of_day(date)
        return ds[index]

    def update(self, symbol, data):
        """append daily history data to daily archive.

        Arguments
        =========
        - `symbol`: symbol.
        - `npydata`: data of npy file.
        """
        prev_year = None
        ds = None
        newdata = None

        for row in data:
            day = datetime.datetime.fromtimestamp(row['time'])
            isoyear = day.isocalendar()[0]

            if prev_year != isoyear:
                if prev_year:
                    # ds will be changed, save prev ds first
                    ds[:] = newdata
                ds = self._require_dataset(symbol, isoyear)
                newdata = ds[:]
            index = self._index_of_day(day)
            try:
                newdata[index] = row
            except IndexError, e:
                logging.error("IndexError on: %s, %s, %s" % (symbol, isoyear, day))
            prev_year = isoyear

        if ds != None and newdata != None:
            ds[:] = newdata

        self.flush()
        return True
    
    def _get_year_data(self, symbol, year):
        ds = self._dataset(symbol, year)
        data = ds[:]
        return data[data.nonzero()]

    def _index_of_day(self, day):
        '''Determing index by day from a dataset.

        We index and store market data by each working day.
        '''
        year, isoweekday, weekday = day.isocalendar()
        return (isoweekday - 1) * 5 + weekday - 1

    def _dataset(self, symbol, year):
        '''We store year of full iso weeks OHLCs in a dataset.

        eg, 2008-12-29 is iso 8061 "2009-W01-1",
        the OHLC data are stored in "symbol/2009/[index_of_0]"
        '''
        return self.handle[self._key(symbol, year)]

    def _require_dataset(self, symbol, year):
        '''Like _dataset, but create on KeyError.'''
        key = self._key(symbol, year)
        return self.handle.require_dataset(key,
                                           (self.WORKING_DAYS_OF_YEAR, ),
                                           dtype=self.DTYPE)

    def _key(self, symbol, year):
        return '%s/%s' % (symbol, str(year))


class OneMinute(OHLC):
    '''Archive of daily 1 minute ohlcs.

    Grouped by symbol and date:

        1min/SH000001/20090101
        1min/SH000001/20090102
    '''

    @property
    def handle(self):
        if not self._handle:
            self._handle = self.store.require_group('1min')
        return self._handle
        

class FiveMinute(OHLC):
    '''Archive of daily 5 minute ohlcs.

    Grouped by symbol and date:

        5min/SH000001/20090101
        5min/SH000001/20090102
    '''
    time_interval = 5 * 60

    @property
    def handle(self):
        if not self._handle:
            self._handle = self.store.require_group('5min')
        return self._handle


class Minute(object):
    '''Snapshot of daily minute quotes history.
    '''
    DTYPE = np.dtype({'names': ('time', 'price', 'volume', 'amount'),
                      'formats': ('i4', 'f4', 'f4', 'f4')})

    def __init__(self, store, date, shape_x):
        assert isinstance(date, datetime.date)
        logging.info("==> Load %s at %s" % (str(store), str(date)))
        self.store = store
        self.date = date
        # TBD: minsnap/date will created on init, this may end with junk datasets
        self.handle = self.store.require_group('minsnap/%s' % date2key(date))
        self.shape_x = shape_x

    @property
    def filename(self):
        return self.handle.filename

    @property
    def pathname(self):
        return self.handle.name

    def flush(self):
        self.handle.file.flush()

    def keys(self):
        "Return a list of keys in archive."
        return self.handle.keys()
        
    def values(self):
        "Return a list of objects in archive."
        return self.handle.values()
        
    def items(self):
        "Return a list of all (key, value) pairs."
        return self.handle.items()

    def iterkeys(self):
        "An iterator over the keys."
        return self.handle.itemkeys()

    def itervalues(self):
        "An iterator over the values."
        return self.handle.itemvalues()

    def iteritems(self):
        "An iterator over (key, value) items."
        return self.handle.iteritems()

    def has_key(self, key):
        "True if key is in archive, False otherwise."
        return key in self.handle

    def get(self, symbol):
        """Get minute history quote data for a symbol.

        Raise:
          KeyError: if symbol not exists.

        Return:
          numpy data
        """
        return self[symbol]

    def set(self, symbol, index, data):
        """Set minute history quote data for a symbol.
        """
        ds = self._require_dataset(symbol)
        ds[index] = data

    def update(self, symbol, data):
        """Update minute snapshots.
        
        Arguments:
          symbol`: Stock instrument.
          data`: numpy quotes data.
        """
        day = datetime.datetime.fromtimestamp(data[0]['time']).date()
        assert day == self.date
        self[symbol] = data

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return len(self.keys())

    def __nonzero__(self):
        "Truth value testing, always return True."
        return True

    def __getitem__(self, key):
        ds = self._dataset(key)
        return ds[:]

    def __setitem__(self, key, value):
        ds = self._require_dataset(key)
        if len(value) > self.shape_x:
            # TODO: filter data before exchange open time.
            # @FIXME seems data begin from 9:15, so we have 253 instead of 242
            # this breaks datastore cause we assuming day data length should be
            # 242
            value = value[-self.shape_x:]
            ds[:] = value
        elif len(value) < self.shape_x:
            ds[:len(value)] = value
        else:
            ds[:] = value
        return True

    def __delitem__(self, key):
        ds = self._dataset(key)
        del self.handle[ds.name]

    def _dataset(self, symbol):
        return self.handle[symbol]

    def _require_dataset(self, symbol):
        try:
            return self._dataset(symbol)
        except KeyError:
            return self.handle.create_dataset(symbol,
                                              (self.shape_x, ),
                                              self.DTYPE)


class MinuteSnapshotCache(DictStoreNamespace):
    '''Mock for basic h5py interface.

    This is only used to enhance performance of minute store.
    '''
    def __init__(self, store, date):
        assert isinstance(store, DictStore)
        assert isinstance(date, datetime.date)

        super(MinuteSnapshotCache, self).__init__(store)
        self.date = date


    def __repr__(self):
        return self.__class__.__name__

    def __str__(self):
        return self.__repr__()

    @property
    def name(self):
        '''Compatible with hdf5 for tests.'''
        return '/minsnap/%s' % self.pathname

    @property
    def filename(self):
        return self.store.filename

    @property
    def pathname(self):
        return date2key(self.date)

    @property
    def file(self):
        return self

    def require_group(self, gid):
        """Cache dict store act as one group.
        """
        return self

    def create_dataset(self, symbol, shape, dtype):
        self.__setitem__(symbol, np.zeros(shape, dtype))
        return self.__getitem__(symbol)

    def rotate(self, tostore):
        assert not isinstance(tostore.store, MinuteSnapshotCache)
        assert tostore.date == self.date

        logging.info("==> Rotating %s min snapshots." % self.pathname)
        self._rewrite(tostore)

    def _rewrite(self, tostore):
        if self.__len__() > 0:
            for key in self.keys():
                try:
                    tostore.update(key, self.__getitem__(key))
                except AssertionError:
                    logging.error("Inconsistent data for %s, ignoring." % key)
                self.__delitem__(key)
            tostore.flush()

########NEW FILE########
__FILENAME__ = dividend
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2011 yinhm

import datetime
import numpy as np

from pandas import DataFrame
from pandas import TimeSeries
from pandas import DatetimeIndex

    
class Dividend(object):

    def __init__(self, div):
        """
        Paramaters:
          div: numpy dividend data.
        """
        assert div['time'] > 0
        assert abs(div['split']) > 0 or \
            abs(div['purchase']) > 0 or \
            abs(div['dividend']) > 0

        self._npd = div

    def adjust(self, frame):
        '''Adjust price, volume of quotes data.
    
        Paramaters
        ----------
        frame: DataFrame of OHLCs.
        '''
        if self.ex_date <= frame.index[0].date(): # no adjustment needed
            return True

        if self.ex_date > datetime.date.today(): # not mature
            return True

        self._divide(frame)
        self._split(frame)

    def _divide(self, frame):
        """divided close price to adjclose column

        WARNING
        =======
        frame should be chronological ordered otherwise wrong backfill.
        """
        if self.cash_afterward == 0:
            return

        cashes = [self.cash_afterward, 0.0]
        adj_day = self.ex_date - datetime.timedelta(days=1)
        indexes = []
        indexes.append(self.d2t(adj_day))
        indexes.append(self.d2t(datetime.date.today()))
        
        cashes = TimeSeries(cashes, index=indexes)
        ri_cashes = cashes.reindex(frame.index, method='backfill')

        frame['adjclose'] = frame['adjclose'] - ri_cashes

    def _split(self, frame):
        if self.share_afterward == 1:
            return

        splits = [self.share_afterward, 1.0]
        adj_day = self.ex_date - datetime.timedelta(days=1)
        indexes = []
        indexes.append(self.d2t(adj_day))
        indexes.append(self.d2t(datetime.date.today()))
        
        splits = TimeSeries(splits, index=indexes)
        ri_splits = splits.reindex(frame.index, method='backfill')

        frame['adjclose'] = frame['adjclose'] / ri_splits

    @property
    def ex_date(self):
        return datetime.date.fromtimestamp(self._npd['time'])

    @property
    def cash_afterward(self):
        return self._npd['dividend'] - self._npd['purchase'] * self._npd['purchase_price']
        
    @property
    def share_afterward(self):
        return 1 + self._npd['purchase'] + self._npd['split']

    def d2t(self, date):
        return datetime.datetime.combine(date, datetime.time())


def adjust(y, divs, capitalize=False):
    """Return fully adjusted OHLCs data base on dividends

    Paramaters:
    y: numpy
    divs: numpy of dividends

    Return:
    DataFrame objects
    """
    index = DatetimeIndex([datetime.datetime.fromtimestamp(v) for v in y['time']])
    y = DataFrame.from_records(y, index=index, exclude=['time'])
    y['adjclose'] = y['close']

    for div in divs:
        if div['split'] + div['purchase'] + div['dividend'] == 0:
            continue
        d = Dividend(div)
        d.adjust(y)

    factor = y['adjclose'] / y['close']
    frame = y.copy()
    frame['open'] = frame['open'] * factor
    frame['high'] = frame['high'] * factor
    frame['low'] = frame['low'] * factor
    frame['close'] = frame['close'] * factor
    frame['volume'] = frame['volume'] * (1 / factor)

    if capitalize:
        columns = [k.capitalize() for k in frame.columns]
        columns[-1] = 'Adjusted'
        frame.columns = columns
        del(frame['Amount'])
    return frame

########NEW FILE########
__FILENAME__ = exchange
# -*- coding: utf-8 -*-
'''Basic market infos.

#TBD: extract currency from major exchanges.
'''
import sys
import time

from datetime import datetime


__all__ = ['StockExchange',
           'AMEX', 'LON', 'NASDAQ',
           'NYSE', 'HK', 'SH', 'SZ', 'TYO',
           'YahooNA', 'Security']


class StockExchange(object):
    '''Major stock exchanges, see:
    - http://en.wikipedia.org/wiki/Stock_exchange
    - http://www.wikinvest.com/wiki/List_of_Stock_Exchanges
    '''
    _pre_market_session = None
    _market_session = None
    _market_break_session = None
    
    _instances = dict()
    
    def __new__(cls, *args, **kwargs):
        klass = cls.__name__
        if not cls._instances.has_key(klass):
            cls._instances[klass] = super(StockExchange, cls).__new__(
                cls, *args, **kwargs)
        return cls._instances[klass]
    
    @classmethod
    def change_time(cls, hour, minute, day=None, now=None):
        if now:
            day = datetime.fromtimestamp(now)
        if not day:
            day = datetime.today()
        t = time.mktime((day.year, day.month, day.day,
                         hour, minute, 0, 0, 0, 0))

        return t
    
    @classmethod
    def pre_open_time(cls, **kwargs):
        return cls.change_time(cls._pre_market_session[0][0],
                               cls._pre_market_session[0][1],
                               **kwargs)

    @classmethod
    def open_time(cls, **kwargs):
        return cls.change_time(cls._market_session[0][0],
                               cls._market_session[0][1],
                               **kwargs)

    @classmethod
    def break_time(cls, **kwargs):
        return cls.change_time(cls._market_break_session[0][0],
                               cls._market_break_session[0][1],
                               **kwargs)

    @classmethod
    def close_time(cls, **kwargs):
        return cls.change_time(cls._market_session[1][0],
                               cls._market_session[1][1],
                               **kwargs)

    def __repr__(self):
        return self.__class__.__name__
    __str__ = __repr__


class AMEX(StockExchange):
    name = 'American Stock Exchange' # NYSE Amex Equities
    currency = ('$', 'USD')
    timezone = 'US/Eastern'
    _market_session = ((9, 30), (16, 0))


class HK(StockExchange):
    name = 'Hong Kong Stock Exchange'
    currency = ('$', 'HKD')
    timezone = 'Asia/Shanghai'
    _pre_market_session = ((9, 30), (9, 50))
    _market_session = ((10, 0), (16, 0))
    _market_break_session = ((12, 0), (13, 30))


class LON(StockExchange):
    name = 'London Stock Exchange'
    currency = ('$', 'GBX')
    timezone = 'Europe/London'
    _market_session = ((9, 0), (17, 0))


class NASDAQ(StockExchange):
    name = 'NASDAQ Stock Exchange'
    currency = ('$', 'USD')
    timezone = 'US/Eastern'
    _market_session = ((9, 30), (16, 0))


class NYSE(StockExchange):
    name = 'New York Stock Exchange'
    currency = ('$', 'USD')
    timezone = 'US/Eastern'
    _market_session = ((9, 30), (16, 0))


class NYSEARCA(NYSE):
    pass


class SH(StockExchange):
    name = 'Shanghai Stock Exchange'
    currency = ('¥', 'CNY')
    timezone = 'Asia/Shanghai'
    _pre_market_session = ((9, 15), (9, 25))
    _market_session = ((9, 30), (15, 0))
    _market_break_session = ((11, 30), (13, 0))

    # Daily minute data count.
    market_minutes = 242


class SZ(SH):
    timezone = 'Asia/Shanghai'
    name = 'Shenzhen Stock Exchange'


class TYO(StockExchange):
    name = 'Tokyo Stock Exchange'
    currency = ('¥', 'JPY')
    timezone = 'Asia/Tokyo'
    _market_session = ((9, 0), (15, 0))
    

class YahooNA(StockExchange):
    name = 'Exchange N/A for Yahoo!'
    currency = ('$', 'USD') #default to usd
    timezone = "GMT" #default to GMT

    def __str__(self):
        return ""
    
class Security(object):
    """Finance securities includes:
    - stocks
    - stock indexes
    - funds/mutual funds
    - options
    - bonds
    """
    modules = sys.modules[__name__]

    __slots__ = ['exchange', 'symbol', 'name']

    def __init__(self, exchange, symbol, name=None):
        assert isinstance(exchange, StockExchange), "Wrong exchange."
        self.exchange = exchange
        self.symbol = symbol
        self.name = name

    def __eq__(self, other):
        return self.exchange == other.exchange and \
            self.symbol == other.symbol

    def __getstate__(self):
        return self.exchange, self.symbol

    def __setstate__(self, state):
        self.exchange, self.symbol = state

    def __repr__(self):
        args = []
        args.append("%s()" % self.exchange)
        args.append("'%s'" % self.symbol)
        if self.name:
            args.append("'%s'" % self.name)
        return "%s(%s)" % (self.__class__.__name__,
                           ', '.join(args))

    def __str__(self):
        """Symbol with exchange abbr (pre)suffix.
        """
        return "%s:%s" % (self._abbr, self.symbol)

    @classmethod
    def from_security(cls, security):
        """Helper method for convert from different services adapter."""
        assert isinstance(security, Security)
        return cls(security.exchange,
                   security.symbol,
                   security.name)

    @classmethod
    def from_abbr(cls, abbr, symbol, name=None):
        ex = getattr(cls.modules, abbr)
        return cls(ex(), symbol, name)
        
    @property
    def _abbr(self):
        """Symbol with exchange abbr suffix.
        """
        return str(self.exchange)

########NEW FILE########
__FILENAME__ = imiguserver
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2011 yinhm

'''Imigu.com specific datafeed server implementation.
'''

import datetime
import logging
import time

import numpy as np

from datafeed.providers.dzh import DzhDividend, DzhSector
from datafeed.server import *
from datafeed.utils import *


__all__ = ['ImiguApplication', 'ImiguHandler']


class SnapshotIndexError(KeyError):
    pass



class ImiguApplication(Application):

    def __init__(self, datadir, exchange):
        self.archive_minute_time = 0
        self.archive_day_time = 0
        self.crontab_time = 0
        
        self._tasks = []
        
        super(ImiguApplication, self).__init__(datadir, exchange, handler=ImiguHandler)

        # last quote time reset to SH000001's timestamp
        try:
            r = self.dbm.get_report("SH000001")
            self.dbm.set_mtime(r['timestamp'])
        except KeyError:
            self.dbm.set_mtime(time.time())

    def periodic_job(self):
        today = datetime.datetime.today()

        if self.scheduled_archive_minute(today):
            request = Request(None, 'archive_minute')
            self.__call__(request)

        if self.scheduled_archive_day(today):
            request = Request(None, 'archive_day')
            self.__call__(request)

        if self.scheduled_crontab_daily(today):
            request = Request(None, 'crontab_daily')
            self.__call__(request)

        if len(self._tasks) > 0:
            logging.info("tasks left: %s" % len(self._tasks))
            request = Request(None, 'run_task')
            self.__call__(request)

    def scheduled_archive_minute(self, today):
        """Test is archive minute scheduled.
        """
        now = time.time()

        market_open_at = self.exchange.open_time(now=now)
        if now < market_open_at:
            # Should not archive any data if market not open yet.
            logging.debug("market not open yet")
            return False        

        market_closing_at = self.exchange.close_time(now=now)
        if now > (market_closing_at + 60 * 5):
            # Do not archive if time passed 15:05.
            # Should be archived already. If not, something is broken.
            logging.debug("market closed more than 5 minutes")
            return False

        # quote_time = self.dbm.mtime
        # if (now - quote_time) > 60:
        #     return False

        # in session, we run it every 60 sec or greater
        if today.second == 0 or (now - self.archive_minute_time) > 60:
            return True

        return False

    def scheduled_archive_day(self, today):
        """Test is daily archive scheduled.
        """
        now = time.time()
        close_time = self.exchange.close_time(now=now)

        if now < close_time:
            logging.debug("market not closed yet.")
            return False

        if self.dbm.mtime < close_time:
            logging.debug("No market data: Weekday or holiday or datafeed receiver broken.")
            return False

        if self.dbm.mtime < self.archive_day_time:
            logging.debug("Already archived.")
            return False

        # skip 60 * 3 sec make sure we got the last data
        if now > (close_time + 60 * 3):
            return True

        return False

    def scheduled_crontab_daily(self, today):
        """Test is daily crontab scheduled.
        """
        if today.hour == 8:
            if today.minute == 0 and today.second == 0:
                return True
            
            now = time.time()
            if today.minute == 0 and (now - self.crontab_time) > 86400:
                # not runned before
                return True

        return False

    def task_add(self, task):
        self._tasks.append(task)
    
    def task_reserve(self):
        return self._tasks.pop(0)
    
class ImiguHandler(Handler):

    SUPPORTED_METHODS = Handler.SUPPORTED_METHODS + \
        ('archive_day',
         'archive_minute',
         'crontab_daily',
         'sync_dividend',
         'sync_sector',
         'run_task')


    ###### periodic jobs ######
    
    def archive_day(self, *args):
        """Archive daily data from report datastore.
        """
        dt = datetime.datetime.fromtimestamp(self.dbm.mtime).date()

        store = self.dbm.daystore
        reports = self.dbm.get_reports()
        for symbol, report in reports:
            if 'timestamp' not in report:
                continue

            d = datetime.datetime.fromtimestamp(report['timestamp'])

            if dt != d.date():
                # skip instruments which no recent report data
                continue
            
            t = int(time.mktime(d.date().timetuple()))

            row = (t, report['open'], report['high'], report['low'],
                   report['close'], report['volume'], report['amount'])
            
            data = np.array([row], dtype=store.DTYPE)
            store.update(symbol, data)
        
        self.application.archive_day_time = time.time()
        logging.info("daily data archived.")

        if self.request.connection:
            self.request.write("+OK\r\n")

    def archive_minute(self, *args):
        '''Archive minute data from report datastore.
        '''
        logging.info("starting archive minute...")
        self.application.archive_minute_time = time.time()

        dbm = self.dbm
        pre_open_time = dbm.exchange.pre_open_time(now=dbm.mtime)
        open_time = dbm.exchange.open_time(now=dbm.mtime)
        break_time = dbm.exchange.break_time(now=dbm.mtime)
        close_time = dbm.exchange.close_time(now=dbm.mtime)

        try:
            report = dbm.get_report('SH000001')
            rts = report['timestamp']
        except KeyError:
            logging.error("No SH000001 data.")
            if not self.request.connection:
                return
            return self.request.write("-ERR No data yet.\r\n")

        if rts < pre_open_time:
            logging.error("wrong report time: %s." % \
                              (datetime.datetime.fromtimestamp(rts), ))
            if not self.request.connection:
                return
            return self.request.write("-ERR No data yet.\r\n")

        mintime, index = ImiguHandler.get_snapshot_index(open_time, rts)

        if index < 0:
            raise SnapshotIndexError

        # Rotate when we sure there is new data coming in.
        dbm.rotate_minute_store()
        store = dbm.minutestore

        snapshot_time = mintime
        cleanup_callback = lambda r: r
        if index > 120 and index < 210:
            # sometimes we received report within 11:31 - 12:59
            # reset to 11:30
            snapshot_time = break_time
            def cleanup_callback(r):
                r['timestamp'] = break_time
                r['time'] = str(datetime.datetime.fromtimestamp(break_time))

            index = 120
        elif index >= 210 and index <= 330:
            index = index - 89  # subtract 11:31 - 12:59
        elif index > 330:
            # sometimes we received report after 15:00
            # reset to 15:00
            snapshot_time = close_time
            def cleanup_callback(r):
                r['timestamp'] = close_time
                r['time'] = str(datetime.datetime.fromtimestamp(close_time))

            index = 241

        reports = dbm.get_reports()
        for key, report in reports:
            if 'timestamp' not in report:
                # Wrong data
                continue

            if mintime - report['timestamp'] > 1800:
                # no new data in 30 mins, something broken
                # skip this symbol when unknown
                continue

            cleanup_callback(report)
            
            mindata = (snapshot_time, report['price'], report['volume'], report['amount'])
            y = np.array(mindata, dtype=store.DTYPE)

            store.set(key, index, y)

        #store.flush()

        logging.info("snapshot to %i (index of %i)." % (mintime, index))
        self.request.write_ok()

    @classmethod
    def get_snapshot_index(cls, open_time, report_time):
        ts = time.time()
        d = datetime.datetime.fromtimestamp(ts)
        mintime = time.mktime((d.year, d.month, d.day,
                               d.hour, d.minute,
                               0, 0, 0, 0))
        index = int((mintime - open_time) / 60)
        logging.info("minute data at %i (index of %i)." % (mintime, index))
        return (int(mintime), index)
                          
    def crontab_daily(self, *args):
        self.application.crontab_time = time.time()
        self.sync_dividend()
        self.sync_sector()

    def sync_dividend(self, *args):
        io = DzhDividend()
        for symbol, data in io.read():
            self.dbm.update_dividend(symbol, data)
        self.dbm.divstore.flush()
        self.request.write_ok()

    def sync_sector(self, *args):
        io = DzhSector()
        for sector, options in io.read():
            self.dbm.sectorstore[sector] = options
        self.request.write_ok()

    def run_task(self):
        for i in xrange(300):
            try:
                task = self.application.task_reserve()
            except IndexError:
                break
            task.run()
        

class Task(object):
    __slots__ = ['store', 'key', 'index', 'data']
    
    def __init__(self, store, key, index, data):
        self.store = store
        self.key = key
        self.index = index
        self.data = data

    def run(self):
        self.store.set(self.key, self.index, self.data)

########NEW FILE########
__FILENAME__ = dzh
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010 yinhm

"""大智慧日线数据抓换

大智慧数据格式分析：
http://hi.baidu.com/wu988/blog/item/9321c4036917a30f728da55d.html

文件路径
-------
$DZH/data/sh/day.dat

文件头
-----
起止地址   数据内容                 数据含义       数据类型
00 - 03   F4 9B 13 FC             文件标志 int
04 - 07   00 06 00 00             未知           int
08 - 0B   00 00 00 00             保留           int
0C - 0F   97 04 00 00             证券总数       int
10 - 13   00 18 00 00             未知           int 需添加之起始块号
14 - 17   DB 17 00 00             未知           int 当前最后空块号

记录块号为FFFF表示未分配.从41000h开始的8KB为第0号数据存储块.

"""

import os
import ConfigParser
import urllib2

from collections import OrderedDict
from cStringIO import StringIO
from struct import *

import h5py
import numpy as np


__all__ = ['DzhDay', 'DzhDividend',
           'DzhMinute', 'DzhFiveMinute',
           'DzhSector']


class EndOfIndexError(StandardError):
    pass

class FileNotFoundError(StandardError):
    pass


def gb2utf(value, ignore=True):
    if ignore:
        return unicode(value, 'gb18030', 'ignore').encode('utf-8', 'ignore')
    else:
        return unicode(value, 'gb18030').encode('utf-8')

    
class DzhDay(object):
    """大智慧日线数据"""

    _COUNT_SDTART = int('0x0c', 16)
    _INDEX_START  = int('0x18', 16)
    _BLOCK_START  = int('0x41000', 16) # OHLCs
    _BLOCK_SIZE   = 256 * 32

    _DTYPE = [('time', '<i4'),
              ('open', '<f4'),
              ('high', '<f4'),
              ('low', '<f4'),
              ('close', '<f4'),
              ('volume', '<f4'),
              ('amount', '<f4')]
    
    
    def read(self, filename, market):
        """Generator of 日线数据读取

        Block read each symbols data.

        Parameters
        ----------
        store : hdf5 store
        """
        self.f = open(filename, 'r')
        
        try:
            i = 0
            while True:
                self.f.seek(self._INDEX_START + 64 * i, 0)
                index = self.read_index()

                symbol = market + index[0]

                timestamps = []
                ohlcs = []
                for block in index[2]:
                    self.read_block(block=block, timestamps=timestamps, ohlcs=ohlcs)

                ohlcs = np.array(ohlcs)
                ohlcs = np.rec.fromarrays([timestamps,
                                           ohlcs[:, 0],
                                           ohlcs[:, 1],
                                           ohlcs[:, 2],
                                           ohlcs[:, 3],
                                           ohlcs[:, 4],
                                           ohlcs[:, 5]],
                                          dtype=self._DTYPE)

                yield symbol, ohlcs
            
                i += 1
        except (EOFError, EndOfIndexError):
            raise StopIteration
        # except Exception as e:
        #     '''locks like we got some duplicated data, eg:

        #     sz399004
        #     --------

        #     block 8846 has 4 of those:
        #     2010-05-10
        #     2010-05-11
        #     2010-05-12
        #     2010-05-13

        #     How do we fix this?
        #     '''
        finally:
            self.f.close()
        
    def read_index(self):
        """索引记录格式

        数据块大小
        ---------
        0x18起每64byte为一组索引数据

        数据库结构
        ---------
        18 - 21   31 41 30 30 30...FF     证券代码       byte[10]
        22 - 25   B0 09 00 00             ohlc记录数     int
        26 - 27   05 00                   第一个记录块号short
        28 - 29   06 00                   第二个记录块号 short
        56 - 57                           第25个记录块号short

        Return tuple of index

        Examples
        --------
        >>> index = read_index(f)
        >>> index
        ('000001', 4767, [0, 1132, 1135])
        
        """
        symbol = unpack('10s', self.f.read(10))[0].replace('\x00', '')

        if symbol == '':
            raise EOFError
        
        count =  unpack('i', self.f.read(4))[0]

        blocks = []

        for i in range(25):
            block_id = unpack('h',  self.f.read(2))[0]
            if block_id != -1: # 0xff 0xff
                blocks.append(block_id)
            
        return (symbol, count, blocks)

    def read_block(self, block, timestamps, ohlcs):
        """read ohlc data rows for a symbol

        data length
        -----------
        8KB each symbol, 256 * 32bytes

        ohlc记录格式
        -----------
        41000 - 41003 80 47 B2 2B         日期           int
        41004 - 41007 B9 1E 25 41         开盘价         float
        41008 - 4100B CD CC 4C 41         最高价         float
        4100C - 4100F EC 51 18 41         最低价         float
        41010 - 41013 9A 99 41 41         收盘价         float
        41014 - 41017 80 06 B2 47         成交量         float
        41018 - 4101B 40 1C BC 4C         成交金额       float
        4101C - 4101D 00 00               上涨家数       short
        4101E - 4101F 00 00               下跌家数       short
        日期为unixtime.

        Returns
        -------
        True on success or Error raised
        """
        try:
            self.f.seek(self._BLOCK_START + self._BLOCK_SIZE * block, 0) # reseek to block head
        except:
            print "wrong block size? %d" % block

        for i in range(256):
            rawdata = self.f.read(4)

            if rawdata == '':
                raise EOFError
            
            timestamp = unpack('i', rawdata)[0]
            if timestamp <= 0:
                # invalid: \x00 * 4 || \xff * 4
                self.f.seek(24, 1)
            else:
                ohlc = np.frombuffer(self.f.read(24), dtype=np.float32)

                timestamps.append(timestamp)
                ohlcs.append(ohlc)

            self.f.seek(4, 1) # skip 2*2short for rasie/up count

        return True


class DzhMinute(DzhDay):
    """大智慧1分钟数据"""
    _BLOCK_START  = int('0x41000', 16)
    _BLOCK_SIZE   = 384 * 32


class DzhFiveMinute(DzhDay):
    """大智慧5分钟数据

    IMPORTANT:

    大智慧五分钟数据时区处理有误，导致time数据相差8小时。
    数据读取未对原始数据做任何改动，实际使用中，需手工修正，eg:

        for symbol, ohlcs in io.read('MIN1.DAT', 'SH'):
            for ohlc in ohlcs:
                ohlc['time'] = ohlc['time'] - 8 * 3600
    """
    #_BLOCK_START  = int('0x41000', 16)
    #_BLOCK_SIZE   = 384 * 32


class DzhFetcher(object):
    _IPS = ('222.73.103.181', '222.73.103.183')
    _PATH = None
    
    def __init__(self):
        self.ips = list(self._IPS)
        self._fetched = False

    def fetch_next_server(self):
        self.ips.pop
        if len(self.ips) == 0:
            raise FileNotFoundError
        return self.fetch()
        
    def fetch(self):
        try:
            r = urllib2.urlopen(self.data_url())
            data = r.read()
            self.f = StringIO(data)
            self._fetched = True
        except URLError:
            return self.fetch_next_server()
    
    def data_url(self):
        assert self._PATH, "No file path."
        
        if len(self.ips) == 0:
            return None
        
        return "http://" + self.ips[-1] + self._PATH

    
class DzhDividend(DzhFetcher):
    '''大智慧除权数据'''
    _PATH = '/platform/download/PWR/full.PWR'

    def read(self):
        """Generator of 大智慧除权数据
        
        Example of yield data:
    
        symbol: 'SZ000001'
        dividends: [{ :date_ex_dividend => '1992-03-23',
                      :split => 0.500,
                      :purchase => 0.000,
                      :purchase_price => 0.000,
                      :dividend => 0.200 }... ]
        """
        if self._fetched == False:
            self.fetch()
        
        # skip head
        self.f.seek(12, 0)

        try:
            while True:
                yield self._read_symbol()
        except EOFError:
            raise StopIteration
        finally:
            self.f.close()
        #except Exception as e:
        #    print(e)

    def _read_symbol(self):
        dividends = []

        rawsymbol = self.f.read(16)
        if rawsymbol == '':
            raise EOFError
        
        symbol = unpack('16s', rawsymbol)[0].replace('\x00', '')

        rawdate = self.f.read(4)

        dt = np.dtype([('time', np.int32),
                       ('split', np.float32),
                       ('purchase', np.float32),
                       ('purchase_price', np.float32),
                       ('dividend', np.float32)])
        while (rawdate) != "\xff" * 4:
            dividend = np.frombuffer(rawdate + self.f.read(16), dtype=dt)
            dividends.append(dividend)
            
            rawdate = self.f.read(4)
            if rawdate == '':
                break

        return (symbol, np.fromiter(dividends, dtype=dt))



_SECTORS = ('行业', '概念', '地域',
            '证监会行业', '指数板块')
class DzhSector(DzhFetcher):
    '''大智慧板块数据'''
    
    _PATH = '/platform/download/ABK/full.ABK'

    def read(self):
        """Generator of 大智慧板块数据
        """
        if self._fetched == False:
            self.fetch()
        
        content = self.f.read()
        file = StringIO()
        file.write(gb2utf(content))
        file.seek(0)

        config = ConfigParser.ConfigParser()
        config.readfp(file)

        for sector in _SECTORS:
            options = OrderedDict()
            for name, value in config.items(sector):
                options[name] = value.split(' ')
            yield sector, options

        self.f.close()
        file.close


if __name__ == '__main__':
    from cStringIO import StringIO
    from datafeed.client import Client

    client = Client()

    # path = os.path.join(os.path.realpath(os.path.dirname(__file__)),
    #                     '../../var')

    # filename = os.path.join(path, "/dzh/sh/DAY.DAT")
    # io = DzhDay()
    # for symbol, ohlcs in io.read(filename, 'SH') :
    #     memfile = StringIO()
    #     np.save(memfile, ohlcs)
    #     client.put('DayHistory', symbol, memfile.getvalue())
        

    io = DzhDividend()
    for data in io.read():
        memfile = StringIO()
        np.save(memfile, data[1])
        client.put('dividend', data[0], memfile.getvalue())

########NEW FILE########
__FILENAME__ = google
# -*- coding: utf-8 -*-

import sys
import functools
import logging

from datetime import timedelta
from dateutil import parser

from datafeed.bidict import Bidict
from datafeed.exchange import *
from datafeed.quote import *
from datafeed.providers.http_fetcher import *
from datafeed.utils import json_decode

__all__ = ['GoogleSecurity', 'currency2float',
           'GoogleReport', 'GoogleReportFetcher',
           'GoogleDay', 'GoogleDayFetcher',
           'GoogleNewsFetcher']

# See: http://www.google.com/intl/en-US/help/stock_disclaimer.html
# Google finance support more exchanges, adding here if you need it.
_EXCHANGES = Bidict({
        "HK": 'HGK',  #Hongkong
        "SH": "SHA",  #Shanghai
        "SZ": "SHE",  #ShenZhen
        "NASDAQ": "NASDAQ",
        "NYSE": "NYSE",
        "NYSEARCA": "NYSEARCA",
        "AMEX": "AMEX",
        })


def currency2float(currency):
    """convert currency to float

    >>> currency2float("10.08")
    10.08
    >>> currency2float("12,313.66")
    12313.66
    >>> currency2float("102.5M")
    102500000
    """
    if currency == '':
        return ''
    if currency[-1:] == "M":
        currency = currency[:-1]
        return currency2float(currency) * 10**6
    return float(currency.replace(",", ""))


class GoogleSecurity(Security):
    @property
    def _abbr(self):
        """Google finance specific exchange abbr."""
        return _EXCHANGES[str(self.exchange)]

    @classmethod
    def from_string(cls, idstr):
        """Parse a google symbol(eg: NASDAQ:GOOG) string."""
        abbr, symbol = idstr.split(':')
        return cls.from_abbr(abbr, symbol)

    @classmethod
    def from_abbr(cls, abbr, symbol):
        """Create from exchange abbr and symbol."""
        exchange = cls.get_exchange_from_abbr(abbr)
        return cls(exchange, symbol)

    @classmethod
    def get_exchange_from_abbr(cls, abbr):
        """get exchange from google abbr."""
        ex = _EXCHANGES[abbr]
        ex_cls = getattr(sys.modules[__name__], ex)
        return ex_cls()
        

class GoogleReport(Report):

    # This only contains common tags.
    # You could retrieve special tag data from self._raw_data.
    _TAGS_DEFINITION = {
        't': ("symbol", str),
        "e": ("abbr", str),
        'op': ("open", currency2float),
        'hi': ("high", currency2float),
        'lo': ("low", currency2float),
        'lt': ("time", parser.parse),
        'l':  ("price", currency2float),
        'c':  ("change", currency2float),
        'vo': ("volume", currency2float)
        }

    _raw_data = {}
        
    def __init__(self, raw_data):
        self.assert_raw(raw_data)
        self._raw_data = raw_data

        data = {}
        for key, value in self._TAGS_DEFINITION.iteritems():
            data[value[0]] = value[1](raw_data[key])
        security = GoogleSecurity.from_abbr(data.pop('abbr'),
                                            data.pop('symbol'))

        super(GoogleReport, self).__init__(security, data)

    def assert_raw(self, raw_data):
        assert isinstance(raw_data['t'], basestring)
        assert isinstance(raw_data['e'], basestring)
        assert isinstance(raw_data['l'], basestring)
        assert isinstance(raw_data['lt'], basestring)
        assert isinstance(raw_data['vo'], basestring)

    def __getitem__(self, key):
        """Proxy to untouched raw data."""
        return self._raw_data[key]

    @property
    def preclose(self):
        return self.price - self.change

    @staticmethod
    def parse(rawdata):
        # don't known why & escaped.
        data = rawdata.strip()[3:].replace('\\x', '')
        parsed = json_decode(data)
        return (GoogleReport(x) for x in parsed)


class GoogleDay(Day):

    _DEFINITIONS = (
        ("date", lambda x: parser.parse(x).date()),
        ("open", currency2float),
        ("high", currency2float),
        ("low", currency2float),
        ("close", currency2float),
        ("volume", currency2float))

    def __init__(self, security, raw_data):
        assert len(raw_data) == 6

        data = {}
        i = 0
        for conf in self._DEFINITIONS:
            data[conf[0]] = conf[1](raw_data[i])
            i += 1

        super(GoogleDay, self).__init__(security, data)

    @staticmethod
    def parse(security, rawdata):
        import csv
        from cStringIO import StringIO
        
        f = StringIO(rawdata)
        r = csv.reader(f)
        r.next() # skip header
        return (GoogleDay(security, line) for line in r)


class GoogleReportFetcher(Fetcher):

    # Maximum number of stocks we'll batch fetch.
    _MAX_REQUEST_SIZE = 100
    
    def __init__(self, base_url='http://www.google.com/finance/info',
                 time_out=20, max_clients=10, request_size=100):
        assert request_size <= self._MAX_REQUEST_SIZE
        
        super(GoogleReportFetcher, self).__init__(base_url, time_out, max_clients)
        self._request_size = request_size

    def _fetching_urls(self, *args, **kwargs):
        gids = (str(s) for s in args)
        gids = self._slice(gids)

        return (self._make_url(filter(lambda x: x != None, i)) for i in gids)

    def _make_url(self, ids):
        """Make url to fetch.

        example:        
        http://www.google.com/finance/info?q=SHA:000001,NASDAQ:GOOG&infotype=infoquoteall
        """
        return "%s?q=%s&infotype=infoquoteall" % (self._base_url,
                                                  ','.join(ids))

    def _callback(self, security, **kwargs):
        if 'callback' in kwargs:
            callback = kwargs['callback']
        else:
            callback = None
        return functools.partial(self._handle_request, callback)

    def _handle_request(self, callback, response):
        try:
            self.queue_len = self.queue_len - 1

            if response.error:
                logging.error(response.error)
            else:
                callback(response.body)
        finally:
            self.stop()


class GoogleDayFetcher(DayFetcher):

    def __init__(self, base_url='http://www.google.com/finance/historical',
                 time_out=20, max_clients=10):
        super(GoogleDayFetcher, self).__init__(base_url, time_out, max_clients)

    def _make_url(self, security, **kwargs):
        """Generate url to fetch.

        example:
        
        http://www.google.com/finance/historical?q=NASDAQ:GOOG&startdate=2011-04-01&enddate=2011-04-28&output=csv

        Google finance return one day more data, typically this isn't a
        problem, we decrease the enddate by one day for passing tests.
        """
        url_format = "%s?q=%s&startdate=%s&enddate=%s&output=csv"
        return url_format % (self._base_url,
                             str(security),
                             kwargs['start_date'],
                             kwargs['end_date'] -  timedelta(days=1))


class GoogleNewsFetcher(Fetcher):
    _BASE_URL = "http://www.google.com/finance/company_news?q=%s&output=rss"

    # Maximum number of stocks we'll batch fetch.
    _MAX_REQUEST_SIZE = 100
    
    def __init__(self, base_url=_BASE_URL, time_out=10, max_clients=5):
        super(GoogleNewsFetcher, self).__init__(base_url, time_out, max_clients)

    def _fetching_urls(self, *args, **kwargs):
        return (self._make_url(str(security)) for security in args)

    def _make_url(self, symbol):
        """Make url to fetch.

        example:
        http://www.google.com/finance/company_news?q=NASDAQ:GOOG&output=rss
        """
        return self._base_url % symbol

    def _callback(self, security, **kwargs):
        if 'callback' in kwargs:
            callback = kwargs['callback']
        else:
            callback = None
        return functools.partial(self._handle_request,
                                 callback,
                                 security)

    def _handle_request(self, callback, security, response):
        try:
            self.queue_len = self.queue_len - 1

            if response.error:
                logging.error(response.error)
            else:
                callback(security, response)
        finally:
            self.stop()

########NEW FILE########
__FILENAME__ = http_fetcher
# -*- coding: utf-8 -*-

import functools
import logging
import sys

from tornado.curl_httpclient import CurlAsyncHTTPClient as AsyncHTTPClient 
from tornado import ioloop

 
try:
    from itertools import izip_longest
except ImportError:
    """Python 2.5 support"""
    from itertools import izip, chain, repeat
    if sys.version_info[:2] < (2,6):
        def izip_longest(*args, **kwds):
            # izip_longest('ABCD', 'xy', fillvalue='-') --> Ax By C- D-
            fillvalue = kwds.get('fillvalue')
            def sentinel(counter = ([fillvalue]*(len(args)-1)).pop):
                yield counter()         # yields the fillvalue, or raises IndexError
            fillers = repeat(fillvalue)
            iters = [chain(it, sentinel(), fillers) for it in args]
            try:
                for tup in izip(*iters):
                    yield tup
            except IndexError:
                pass


__all__ = ['Fetcher', 'DayFetcher', 'zip_slice']


class Fetcher(object):
    _MAX_CLIENTS = 10

    def __init__(self, base_url=None, time_out=20, max_clients=10):
        assert isinstance(base_url, basestring)
        assert isinstance(time_out, int)
        assert isinstance(max_clients, int)
        assert max_clients <= self._MAX_CLIENTS
        
        self._base_url = base_url
        self._time_out = time_out
        self._max_clients = max_clients

        self._io_loop = ioloop.IOLoop()

        self.queue_len = 0

    def fetch(self, *args, **kwargs):
        ret = []
        if not len(args) > 0:
            return ret
        
        urls = self._fetching_urls(*args, **kwargs)

        http = AsyncHTTPClient(self._io_loop)
        i = 0
        for url in urls:
            callback = self._callback(args[i], **kwargs)
            logging.info("start urlfetch %s" % url)
            http.fetch(url, callback)
            self.queue_len = self.queue_len + 1
            i += 1

        self._io_loop.start()
        return ret

    def _fetching_urls(self, *args, **kwargs):
        raise NotImplementedError()

    def _slice(self, iterable, fillvalue=None):
        return zip_slice(self._request_size, iterable, fillvalue)

    def _callback(self, security, **kwargs):
        pass

    def stop(self):
        if self.queue_len == 0:
            self._io_loop.stop()


class DayFetcher(Fetcher):

    def _fetching_urls(self, *args, **kwargs):
        assert 'start_date' in kwargs
        assert 'end_date' in kwargs
        
        urls = (self._make_url(s, **kwargs) for s in args)
        return urls

    def _make_url(self, security, **kwargs):
        raise NotImplementedError()

    def _callback(self, security, **kwargs):
        if 'callback' in kwargs:
            callback = kwargs['callback']
        else:
            callback = None
        
        return functools.partial(self._handle_request,
                                 callback,
                                 security)

    def _handle_request(self, callback, security, response):
        try:
            self.queue_len = self.queue_len - 1

            if response.error:
                logging.error(response.error)
            else:
                callback(security, response.body)
        except StandardError:
            logging.error("Wrong data format.")
        finally:
            self.stop()


def zip_slice(len_each, iterable, fillvalue=None):
    "zip_slice(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    assert isinstance(len_each, int)
    args = [iter(iterable)] * len_each
    return izip_longest(fillvalue=fillvalue, *args)

########NEW FILE########
__FILENAME__ = nasdaq
# -*- coding: utf-8 -*-

"""
NASDAQ && NYSE stocks list.
http://www.nasdaq.com/screening/companies-by-industry.aspx
"""
import csv
import functools
import logging
import sys

from cStringIO import StringIO

from tornado import httpclient
from tornado import ioloop

from datafeed.exchange import *
from datafeed.quote import *
from datafeed.providers.http_fetcher import *
from datafeed.utils import json_decode

__all__ = ['NasdaqSecurity',
           'NasdaqList', 'NasdaqListFetcher']


class NasdaqSecurity(Security):
    pass

class NasdaqList(SecurityList):

    # Tags format defined by NasdaqReportFetcher which is:
    # "sl1d1t1c1ohgv"
    # FIXME: Nasdaq quotes became N/A during session after hours.
    _DEFINITIONS = (
        ("symbol", lambda x: x.strip()),
        ("name", str),
        ("price", float),
        ("market_cap", str),
        ("ipo_year", str),
        ("sector", str),
        ("industry", str),
        ("summary", str)
        )

    def __init__(self, exchange, raw_data):
        raw_data.pop()
        assert len(raw_data) == len(self._DEFINITIONS)

        i = 0
        data = {}
        for conf in self._DEFINITIONS:
            key, callback = conf
            data[key] = callback(raw_data[i])
            i += 1

        security = NasdaqSecurity(exchange, data.pop('symbol'), data['name'])
        super(NasdaqList, self).__init__(security, data)

    def __repr__(self):
        return "%s\r\n%s" % (self.security, self.name)

    def __str__(self):
        return "%s" % (self.security, )

    @staticmethod
    def parse(exchange, rawdata):
        """Parse security list for specific exchange.
        """
        f = StringIO(rawdata)
        r = csv.reader(f)
        r.next()
        return (NasdaqList(exchange, line) for line in r)


class NasdaqListFetcher(Fetcher):

    # Maximum number of stocks we'll batch fetch.
    _MAX_REQUEST_SIZE = 100
    _BASE_URL = "http://www.nasdaq.com/screening/companies-by-industry.aspx"
    
    def __init__(self, base_url=_BASE_URL,
                 time_out=20, max_clients=10, request_size=100):
        assert request_size <= self._MAX_REQUEST_SIZE
        
        super(NasdaqListFetcher, self).__init__(base_url, time_out, max_clients)
        self._request_size = request_size

    def _fetching_urls(self, *args, **kwargs):
        """Making list of fetching urls from exchanges.
        """
        for arg in args:
            assert isinstance(arg, NYSE) \
                or isinstance(arg, NASDAQ) \
                or isinstance(arg, AMEX)
        return (self._make_url(arg) for arg in args)

    def _make_url(self, exchange):
        """Make url to fetch.

        example:
        http://www.nasdaq.com/screening/companies-by-industry.aspx?exchange=NYSE&render=download
        """
        return "%s?exchange=%s&render=download" % (self._base_url, exchange)

    def _callback(self, security, **kwargs):
        if 'callback' in kwargs:
            callback = kwargs['callback']
        else:
            callback = None
        return functools.partial(self._handle_request,
                                 callback,
                                 security)

    def _handle_request(self, callback, exchange, response):
        try:
            self.queue_len = self.queue_len - 1

            if response.error:
                logging.error(response.error)
            else:
                callback(exchange, response.body)
        except StandardError:
            logging.error("Wrong data format.")
        finally:
            self.stop()

########NEW FILE########
__FILENAME__ = sina
# -*- coding: utf-8 -*-

"""
Stocks:
http://hq.sinajs.cn/list=sh600028,sz000100


Indexes:
http://hq.sinajs.cn/list=s_sh000001


Charts:
http://image.sinajs.cn/newchart/min/n/sh000001.gif
http://image.sinajs.cn/newchart/daily/n/sh000001.gif
"""

import functools
import logging
import sys

from dateutil import parser

from datafeed.exchange import *
from datafeed.quote import *
from datafeed.providers.http_fetcher import Fetcher
from tornado.escape import json_decode

__all__ = ['SinaSecurity', 'SinaReport', 'SinaReportFetcher']

# Sina finance 
_EXCHANGES = {
        "HK": 'HGK',  #Hongkong
        "SH": "SHA",  #Shanghai
        "SZ": "SHE",  #ShenZhen
        "NASDAQ": "NASDAQ", # NASDAQ
        }


class SinaSecurity(Security):
    def __str__(self):
        """Symbol with exchange abbr suffix"""
        return "%s%s" % (self._abbr, self.symbol)

    @property
    def _abbr(self):
        """Sina finance specific exchange abbr."""
        return str(self.exchange).lower()

    @classmethod
    def from_string(cls, idstr):
        abbr = idstr[:2]
        symbol = idstr[2:]
        exchange = cls.get_exchange_from_abbr(abbr)
        return cls(exchange, symbol)

    @classmethod
    def get_exchange_from_abbr(cls, abbr):
        """Get exchange from sina abbr."""
        klass = getattr(sys.modules[__name__], abbr.upper())
        return klass()
        

class SinaReport(Report):

    # Data example:
    # var hq_str_sh600028="中国石化,8.64,8.64,8.68,8.71,8.58,8.68,8.69,
    #   27761321,240634267,11289,8.68,759700,8.67,556338,8.66,455296,8.65,
    #   56600,8.64,143671,8.69,341859,8.70,361255,8.71,314051,8.72,342155,8.73,
    #   2011-05-03,15:03:11";'''
    _DEFINITIONS = (
        ("name", str),
        ("open", float),
        ("preclose", float),
        ("price", float),
        ("high", float),
        ("low", float),
        ("bid", float),
        ("ask", float),
        ("volume", int),
        ("amount", float),
        ("bid1", int),
        ("bidp1", float),
        ("bid2", int),
        ("bidp2", float),
        ("bid3", int),
        ("bidp3", float),
        ("bid4", int),
        ("bidp4", float),
        ("bid5", int),
        ("bidp5", float),
        ("ask1", int),
        ("askp1", float),
        ("ask2", int),
        ("askp2", float),
        ("ask3", int),
        ("askp3", float),
        ("ask4", int),
        ("askp4", float),
        ("ask5", int),
        ("askp5", float),
        ("date", lambda x: parser.parse(x).date()),
        ("time", lambda x: parser.parse(x))
        )
    
    def __init__(self, security, raw_data):
        assert len(raw_data) == 32

        data = {}
        i = 0
        for conf in self._DEFINITIONS:
            key, callback = conf
            data[key] = callback(raw_data[i])
            i += 1
        
        super(SinaReport, self).__init__(security, data)

    @staticmethod
    def parse(rawdata):
        from cStringIO import StringIO
        
        f = StringIO(rawdata)
        return (SinaReport.parse_line(line) for line in f)

    @staticmethod
    def parse_line(line):
        splited = line.split('"')
        idstr = splited[0].split('_').pop()[:-1]
        s = SinaSecurity.from_string(idstr)
        return SinaReport(s, splited[1].split(','))


class SinaReportFetcher(Fetcher):

    # Maximum number of stocks we'll batch fetch.
    _MAX_REQUEST_SIZE = 100
    
    def __init__(self, base_url='http://hq.sinajs.cn',
                 time_out=20, max_clients=10, request_size=100):
        assert request_size <= self._MAX_REQUEST_SIZE
        
        super(SinaReportFetcher, self).__init__(base_url, time_out, max_clients)
        self._request_size = request_size

    def _fetching_urls(self, *args, **kwargs):
        ids = (str(s) for s in args)
        ids = self._slice(ids)

        return (self._make_url(filter(lambda x: x != None, i)) for i in ids)

    def _make_url(self, ids):
        return "%s/list=%s" % (self._base_url, ','.join(ids))

    def _callback(self, security, **kwargs):
        if 'callback' in kwargs:
            callback = kwargs['callback']
        else:
            callback = None
        return functools.partial(self._handle_request, callback)

    def _handle_request(self, callback, response):
        try:
            self.queue_len = self.queue_len - 1

            if response.error:
                logging.error(response.error)
            else:
                callback(response.body)
        except StandardError:
            logging.error("Wrong data format.")
        finally:
            self.stop()

########NEW FILE########
__FILENAME__ = test_dzh
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import with_statement

import os
import unittest
from cStringIO import StringIO

from datafeed.providers.dzh import *

class DzhDayTest(unittest.TestCase):

    def assertFloatEqual(self, actual, expt):
        if abs(actual - expt) < 0.1 ** 5:
            return True
        return False

    def test_read_generator(self):
        path = os.path.join(os.path.realpath(os.path.dirname(__file__)),
                            '../../../var')

        filename = os.path.join(path, "dzh/sh/DAY.DAT")
        io = DzhDay()
        f = io.read(filename, 'SH')
        symbol, ohlcs = f.next()

        self.assertEqual(symbol, "SH000001")

        ohlc = ohlcs[0]
        
        self.assertEqual(ohlc['time'], 661564800)
        self.assertFloatEqual(ohlc['open'], 96.05)
        self.assertFloatEqual(ohlc['close'], 99.98)
        self.assertFloatEqual(ohlc['volume'], 1260.0)
        self.assertFloatEqual(ohlc['amount'], 494000.0)


class DzhDividendTest(unittest.TestCase):

    def test_read_generator(self):
        io = DzhDividend()
        r = io.read()
        data = r.next()
        
        self.assertEqual(data[0], "SZ000001")
        
        divs = data[1]
        self.assertEqual(divs[0]['time'], 701308800)
        self.assertEqual(divs[0]['split'], 0.5)
        self.assertTrue(abs(divs[0]['dividend'] - 0.20) < 0.000001)
        


class DzhSectorTest(unittest.TestCase):

    def test_read_generator(self):
        io = DzhSector()
        r = io.read()
        sector, options = r.next()

        self.assertEqual(sector, "行业")
        self.assertTrue(options.has_key("工程建筑"))
        self.assertTrue(len(options["工程建筑"]) > 0)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_google
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import with_statement

import os
import unittest

from datetime import datetime, date
from datafeed.exchange import *
from datafeed.providers.http_fetcher import *
from datafeed.providers.google import *


class GoogleSecurityTest(unittest.TestCase):

    def test_abbr_sha(self):
        s = GoogleSecurity(SH(), '600028')
        self.assertEqual(s._abbr, 'SHA')

    def test_abbr_she(self):
        s = GoogleSecurity(SZ(), '000001')
        self.assertEqual(s._abbr, 'SHE')

    def test_abbr_hgk(self):
        s = GoogleSecurity(HK(), '000001')
        self.assertEqual(str(s._abbr), 'HGK')

    def test_google_id(self):
        s = GoogleSecurity(SH(), '600028')
        self.assertEqual(str(s), 'SHA:600028')

    def test_abbr_to_exchange(self):
        ex = GoogleSecurity.get_exchange_from_abbr("SHA")
        self.assertEqual(ex, SH())

    def test_ss_abbr(self):
        ret = GoogleSecurity.from_string('SHA:600028')
        self.assertEqual(ret.exchange, SH())
        self.assertEqual(ret.symbol, '600028')
        self.assertEqual(str(ret), 'SHA:600028')
    
    def test_zip_slice(self):
        ret = [r for r in zip_slice(3, 'ABCED')]
        self.assertEqual(ret, [('A', 'B', 'C'), ('E', 'D', None)])


class GoogleReportTest(unittest.TestCase):
    _RAW_DATA = '// [ { "id": "7521596" ,"t" : "000001" ,"e" : "SHA" ,"l" : "2,925.53" ,"l_cur" : "CN¥2,925.53" ,"s": "0" ,"ltt":"3:00PM CST" ,"lt" : "Apr 27, 3:00PM CST" ,"c" : "-13.46" ,"cp" : "-0.46" ,"ccol" : "chr" ,"eo" : "" ,"delay": "" ,"op" : "2,946.33" ,"hi" : "2,961.13" ,"lo" : "2,907.66" ,"vo" : "105.49M" ,"avvo" : "" ,"hi52" : "3,478.01" ,"lo52" : "1,844.09" ,"mc" : "" ,"pe" : "" ,"fwpe" : "" ,"beta" : "" ,"eps" : "" ,"name" : "SSE Composite Index" ,"type" : "Company" } ,{ "id": "697073" ,"t" : "600028" ,"e" : "SHA" ,"l" : "8.64" ,"l_cur" : "CN¥8.64" ,"s": "0" ,"ltt":"3:00PM CST" ,"lt" : "Apr 29, 3:00PM CST" ,"c" : "+0.12" ,"cp" : "1.41" ,"ccol" : "chg" ,"eo" : "" ,"delay": "" ,"op" : "8.57" ,"hi" : "8.66" ,"lo" : "8.53" ,"vo" : "42.28M" ,"avvo" : "" ,"hi52" : "10.09" ,"lo52" : "7.67" ,"mc" : "749.11B" ,"pe" : "10.70" ,"fwpe" : "" ,"beta" : "" ,"eps" : "0.81" ,"name" : "China Petroleum \x26 Chemical Corporation" ,"type" : "Company" } ,{ "id": "694653" ,"t" : "GOOG" ,"e" : "NASDAQ" ,"l" : "532.82" ,"l_cur" : "532.82" ,"s": "1" ,"ltt":"4:00PM EDT" ,"lt" : "Apr 26, 4:00PM EDT" ,"c" : "+7.77" ,"cp" : "1.48" ,"ccol" : "chg" ,"el": "535.97" ,"el_cur": "535.97" ,"elt" : "Apr 27, 4:15AM EDT" ,"ec" : "+3.15" ,"ecp" : "0.59" ,"eccol" : "chg" ,"div" : "" ,"yld" : "" ,"eo" : "" ,"delay": "" ,"op" : "526.52" ,"hi" : "537.44" ,"lo" : "525.21" ,"vo" : "100.00" ,"avvo" : "2.80M" ,"hi52" : "642.96" ,"lo52" : "433.63" ,"mc" : "171.31B" ,"pe" : "19.53" ,"fwpe" : "" ,"beta" : "1.19" ,"eps" : "27.28" ,"name" : "Google Inc." ,"type" : "Company" } ]'


    def test_currenct_to_float(self):
        self.assertEqual(currency2float("10.08"), 10.08)
        self.assertEqual(currency2float("12,313.66"), 12313.66)
        self.assertEqual(currency2float("102.5M"), 102500000)
    
    def test_google_report(self):
        ret = GoogleReport.parse(self._RAW_DATA)
        i = 0
        for r in ret:
            if i == 0:
                self.assertEqual(r.security.exchange, SH())
                self.assertEqual(r.security.symbol, '000001')
                self.assertEqual(r.price, 2925.53)
                self.assertEqual(r.open, 2946.33)
                self.assertEqual(r.high, 2961.13)
                self.assertEqual(r.low, 2907.66)
                self.assertEqual(r.change, -13.46)

                diff = r.preclose - 2938.99
                self.assertTrue(abs(diff) < 0.000001)
                self.assertTrue(isinstance(r.time, datetime))
                self.assertEqual(r.time.hour, 15)
            if i == 2:
                self.assertEqual(r.security.exchange, NASDAQ())
                self.assertEqual(r.security.symbol, 'GOOG')
                self.assertTrue(r.time.hour, 16)

                self.assertEqual(r['el'], "535.97")
                

            i += 1

    def test_google_report_parse_with_excption(self):
        data = '// [ { "id": "694653" ,"t" : "GOOG" ,"e" : "NASDAQ" ,"l" : "520.90" ,"l_cur" : "520.90" ,"s": "0" ,"ltt":"4:00PM EDT" ,"lt" : "May 27, 4:00PM EDT" ,"c" : "+2.77" ,"cp" : "0.53" ,"ccol" : "chg" ,"eo" : "" ,"delay": "" ,"op" : "518.48" ,"hi" : "521.79" ,"lo" : "516.30" ,"vo" : "1.75M" ,"avvo" : "2.91M" ,"hi52" : "642.96" ,"lo52" : "433.63" ,"mc" : "167.86B" ,"pe" : "20.23" ,"fwpe" : "" ,"beta" : "1.17" ,"eps" : "25.75" ,"name" : "Google Inc." ,"type" : "Company" } ,{ "id": "697227" ,"t" : "FRCMQ" ,"e" : "PINK" ,"l" : "0.0045" ,"l_cur" : "0.00" ,"s": "0" ,"ltt":"2:13PM EST" ,"lt" : "Jan 24, 2:13PM EST" ,"c" : "0.0000" ,"cp" : "0.00" ,"ccol" : "chb" ,"eo" : "" ,"delay": "15" ,"op" : "" ,"hi" : "" ,"lo" : "" ,"vo" : "0.00" ,"avvo" : "1.17M" ,"hi52" : "0.14" ,"lo52" : "0.00" ,"mc" : "404,839.00" ,"pe" : "0.00" ,"fwpe" : "" ,"beta" : "1.30" ,"eps" : "7.57" ,"name" : "Fairpoint Communications, Inc." ,"type" : "Company" } ,{ "id": "5521731" ,"t" : "APPL" ,"e" : "PINK" ,"l" : "0.0000" ,"l_cur" : "0.00" ,"s": "0" ,"ltt":"" ,"lt" : "" ,"c" : "" ,"cp" : "" ,"ccol" : "" ,"eo" : "" ,"delay": "15" ,"op" : "" ,"hi" : "" ,"lo" : "" ,"vo" : "0.00" ,"avvo" : "" ,"hi52" : "" ,"lo52" : "" ,"mc" : "" ,"pe" : "" ,"fwpe" : "" ,"beta" : "" ,"eps" : "" ,"name" : "APPELL PETE CORP" ,"type" : "Company" } ]'

        iterable = GoogleReport.parse(data)

        i = 0
        while 1:
            try:
                i += 1
                r = iterable.next()
            except ValueError:
                continue
            except KeyError:
                continue
            except StopIteration:
                break

            if i == 1:
                self.assertEqual(r.security.symbol, 'GOOG')
            if i == 3:
                self.assertEqual(r.security.symbol, 'APPL')


class GoogleDayTest(unittest.TestCase):
    def test_parse_day(self):
        path = os.path.dirname(os.path.realpath(__file__))
        f = open(os.path.join(path, 'google_data.csv'), 'r')
        data = f.read()
        f.close()

        security = GoogleSecurity(NASDAQ(), 'GOOG')
        iters = GoogleDay.parse(security, data)
        i = 0
        for ohlc in iters:
            if i == 0:
                # 2011-04-28,538.06,539.25,534.08,537.97,2037378
                self.assertTrue(isinstance(ohlc.date, date))
                self.assertEqual(ohlc.open, 538.06)
                self.assertEqual(ohlc.high, 539.25)
                self.assertEqual(ohlc.low, 534.08)
                self.assertEqual(ohlc.close, 537.97)
                self.assertEqual(ohlc.volume, 2037378.0)
            i += 1


class GoogleReportFetcherTest(unittest.TestCase):

    def test_init(self):
        f = GoogleReportFetcher()
        self.assertEqual(f._base_url, 'http://www.google.com/finance/info')
        self.assertEqual(f._time_out, 20)
        self.assertEqual(f._request_size, 100)

    def test_init_with_arguments(self):
        f = GoogleReportFetcher(base_url='http://www.google.com.hk/finance/info',
                                time_out=10,
                                request_size=50)
        self.assertEqual(f._base_url, 'http://www.google.com.hk/finance/info')
        self.assertEqual(f._time_out, 10)
        self.assertEqual(f._request_size, 50)
        
    def test_init_with_wrong_arguments(self):
        self.assertRaises(AssertionError,
                          GoogleReportFetcher,
                          request_size=200)
        
    def test_fetch(self):
        f = GoogleReportFetcher(request_size=2)
        s1 = GoogleSecurity(SH(), '000001')
        s2 = GoogleSecurity(SH(), '600028')
        s3 = GoogleSecurity(NASDAQ(), 'GOOG')

        def callback(body):
            qs = GoogleReport.parse(body)
            for quote in qs:
                if quote.security == s1:
                    # something must wrong if SSE Composite Index goes down to 100
                    self.assertTrue(quote.price > 100)
        
        f.fetch(s1, s2, s3,
                callback=callback)

    def test_fetch_nyse(self):
        symbols = "NYSE:MMM,NYSE:SVN,NYSE:NDN,NYSE:AHC,NYSE:AIR,NYSE:AAN,NYSE:ABB,NYSE:ABT,NYSE:ANF,NYSE:ABH,NYSE:ABM,NYSE:ABVT,NYSE:AKR,NYSE:ACN,NYSE:ABD,NYSE:AH,NYSE:ACW,NYSE:ACE,NYSE:ATV,NYSE:ATU,NYSE:AYI,NYSE:ADX,NYSE:AGRO,NYSE:PVD,NYSE:AEA,NYSE:AAP,NYSE:AMD,NYSE:ASX,NYSE:AAV,NYSE:ATE,NYSE:AGC,NYSE:AVK,NYSE:LCM,NYSE:ACM,NYSE:ANW,NYSE:AEB,NYSE:AED,NYSE:AEF,NYSE:AEG,NYSE:AEH,NYSE:AEV,NYSE:AER,NYSE:ARX,NYSE:ARO,NYSE:AET,NYSE:AMG,NYSE:AFL,NYSE:AGCO,NYSE:NCV,NYSE:NCZ,NYSE:NIE,NYSE:NGZ,NYSE:NAI,NYSE:A,NYSE:AGL,NYSE:AEM,NYSE:ADC,NYSE:GRO,NYSE:AGU,NYSE:AL,NYSE:APD,NYSE:AYR,NYSE:ARG,NYSE:AKS,NYSE:ABA/CL,NYSE:ALM,NYSE:ALP^N,NYSE:ALP^O,NYSE:ALP^P,NYSE:ALQ/CL,NYSE:ALZ/CL,NYSE:ALG,NYSE:ALK,NYSE:AIN,NYSE:ALB,NYSE:ALU,NYSE:AA,NYSE:ALR,NYSE:ALR^B,NYSE:ALEX,NYSE:ALX,NYSE:ARE,NYSE:ARE^C,NYSE:Y,NYSE:ATI,NYSE:AGN,NYSE:ALE,NYSE:AKP,NYSE:AB,NYSE:ADS,NYSE:AIQ,NYSE:AFB,NYSE:AYN,NYSE:AOI,NYSE:AWF,NYSE:ACG,NYSE:LNT,NYSE:ATK,NYSE:AFC,NYSE:AIB"
        symbols = symbols.split(',')

        symbols = [GoogleSecurity.from_string(s) for s in symbols]

        f = GoogleReportFetcher()

        def callback(body):
            rs = GoogleReport.parse(body)
            for r in rs:
                pass

        f.fetch(*symbols, callback=callback)


class GoogleDayFetcherTest(unittest.TestCase):

    def test_init(self):
        f = GoogleDayFetcher()
        self.assertEqual(f._base_url, 'http://www.google.com/finance/historical')
        self.assertEqual(f._time_out, 20)
        self.assertEqual(f._max_clients, 10)

    def test_init_with_wrong_arguments(self):
        self.assertRaises(AssertionError,
                          GoogleReportFetcher,
                          max_clients=20)
        
    def test_fetch(self):
        f = GoogleDayFetcher()
        s1 = GoogleSecurity(NASDAQ(), 'GOOG')
        s2 = GoogleSecurity(NASDAQ(), 'AAPL')

        def callback(security, body):
            iters = GoogleDay.parse(security, body)
            i = 0
            for ohlc in iters:
                self.assertTrue(ohlc.security in (s1, s2))
                if i == 0 and ohlc.security == s1:
                    self.assertEqual(str(ohlc.date), "2011-04-28")
                    self.assertEqual(ohlc.open, 538.06)
                    self.assertEqual(ohlc.high, 539.25)
                    self.assertEqual(ohlc.low, 534.08)
                    self.assertEqual(ohlc.close, 537.97)
                    self.assertEqual(ohlc.volume, 2037378.0)
                    
                i += 1

        start_date = datetime.strptime("2011-04-01", "%Y-%m-%d").date()
        end_date = datetime.strptime("2011-04-28", "%Y-%m-%d").date()
        f.fetch(s1, s2,
                callback=callback,
                start_date=start_date,
                end_date=end_date)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_nasdaq
from __future__ import with_statement

import datetime
import os
import unittest

from datafeed.exchange import *
from datafeed.providers.nasdaq import *


class NasdaqSecurityTest(unittest.TestCase):

    def test_str(self):
        s = NasdaqSecurity(NYSE(), 'MMM')
        self.assertEqual(str(s), 'NYSE:MMM')
    

class NasdaqListTest(unittest.TestCase):
    _RAW_DATA = '''"Symbol","Name","LastSale","MarketCap","IPOyear","Sector","Industry","Summary Quote",
"MMM","3M Company","91.97","65351766690","n/a","Health Care","Medical/Dental Instruments","http://quotes.nasdaq.com/asp/SummaryQuote.asp?symbol=MMM&selected=MMM",
"SVN","7 Days Group Holdings Limited","18.6","345048600","2009","Consumer Services","Hotels/Resorts","http://quotes.nasdaq.com/asp/SummaryQuote.asp?symbol=SVN&selected=SVN",
"NDN","99 Cents Only Stores","20.2","1415515000","1996","Consumer Services","Department/Specialty Retail Stores","http://quotes.nasdaq.com/asp/SummaryQuote.asp?symbol=NDN&selected=NDN",
"AHC","A.H. Belo Corporation","6.83","130575940","n/a","Consumer Services","Newspapers/Magazines","http://quotes.nasdaq.com/asp/SummaryQuote.asp?symbol=AHC&selected=AHC",'''


    def test_nasdaq_report(self):
        ret = NasdaqList.parse(NYSE(), self._RAW_DATA)
        i = 0
        for r in ret:
            if i == 0:
                self.assertEqual(r.security.exchange, NYSE())
                self.assertEqual(r.security.symbol, 'MMM')
                self.assertEqual(r.name, "3M Company")
                self.assertEqual(r.price, 91.97)

            if i == 1:
                self.assertEqual(r.security.exchange, NYSE())
                self.assertEqual(r.security.symbol, 'SVN')

            i += 1

        self.assertEqual(i, 4)


class NasdaqListFetcherTest(unittest.TestCase):

    def test_init(self):
        f = NasdaqListFetcher()
        self.assertEqual(f._base_url,
                         'http://www.nasdaq.com/screening/companies-by-industry.aspx')

    def test_fetch_with_wrong_arguments(self):
        f = NasdaqListFetcher()
        self.assertRaises(AssertionError, f.fetch, SH())


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_sina
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import with_statement

import os
import unittest

from datetime import datetime, date
from datafeed.exchange import *
from datafeed.providers.sina import *


class SinaSecurityTest(unittest.TestCase):

    def test_abbr_sh(self):
        s = SinaSecurity(SH(), '600028')
        self.assertEqual(s._abbr, 'sh')

    def test_abbr_sz(self):
        s = SinaSecurity(SZ(), '000001')
        self.assertEqual(s._abbr, 'sz')

    def test_sina_id(self):
        s = SinaSecurity(SH(), '600028')
        self.assertEqual(str(s), 'sh600028')

    def test_abbr_to_exchange(self):
        ex = SinaSecurity.get_exchange_from_abbr("sh")
        self.assertEqual(ex, SH())

    def test_ss_abbr(self):
        ret = SinaSecurity.from_string('sh600028')
        self.assertEqual(ret.exchange, SH())
        self.assertEqual(ret.symbol, '600028')
    

class SinaReportTest(unittest.TestCase):
    _RAW_DATA = '''var hq_str_sh000001="上证指数,2911.510,2911.511,2932.188,2933.460,2890.225,0,0,96402722,102708976572,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2011-05-03,15:03:11";
var hq_str_sh600028="中国石化,8.64,8.64,8.68,8.71,8.58,8.68,8.69,27761321,240634267,11289,8.68,759700,8.67,556338,8.66,455296,8.65,56600,8.64,143671,8.69,341859,8.70,361255,8.71,314051,8.72,342155,8.73,2011-05-03,15:03:11";'''

    def test_sina_report(self):
        ret = SinaReport.parse(self._RAW_DATA)
        i = 0
        for r in ret:
            if i == 1:
                self.assertEqual(r.security.exchange, SH())
                self.assertEqual(r.security.symbol, '600028')
                self.assertEqual(r.name, '中国石化')
                self.assertEqual(r.open, 8.64)
                self.assertEqual(r.preclose, 8.64)
                self.assertEqual(str(r.date), "2011-05-03")

            i += 1


class SinaReportFetcherTest(unittest.TestCase):

    def test_init(self):
        f = SinaReportFetcher()
        self.assertEqual(f._base_url, 'http://hq.sinajs.cn')
        self.assertEqual(f._time_out, 20)
        self.assertEqual(f._request_size, 100)

    def test_init_with_wrong_arguments(self):
        self.assertRaises(AssertionError,
                          SinaReportFetcher,
                          request_size=200)
        
    def test_fetch(self):
        f = SinaReportFetcher(request_size=2)
        s1 = SinaSecurity(SH(), '000001')
        s2 = SinaSecurity(SH(), '600028')
        s3 = SinaSecurity(SZ(), '000976')

        def callback(body):
            qs = SinaReport.parse(body)
            for quote in qs:
                if quote.security == s1:
                    # something must wrong if SSE Composite Index goes down to 100
                    self.assertTrue(quote.price > 100)
        
        f.fetch(s1, s2, s3,
                callback=callback)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_yahoo
from __future__ import with_statement

import datetime
import os
import unittest

from datafeed.exchange import *
from datafeed.providers.yahoo import *


class YahooSecurityTest(unittest.TestCase):

    def test_abbr_sha(self):
        s = YahooSecurity(SH(), '600028')
        self.assertEqual(s._abbr, 'SS')

    def test_abbr_she(self):
        s = YahooSecurity(SZ(), '000001')
        self.assertEqual(s._abbr, 'SZ')

    def test_yahoo_id(self):
        s = YahooSecurity(SH(), '600028')
        self.assertEqual(str(s), '600028.SS')

    def test_abbr_to_exchange(self):
        ex = YahooSecurity.get_exchange_from_abbr("SS")
        self.assertEqual(ex, SH())

    def test_ss_abbr(self):
        ret = YahooSecurity.from_string('600028.SS')
        self.assertEqual(ret.exchange, SH())
        self.assertEqual(ret.symbol, '600028')
        self.assertEqual(str(ret), '600028.SS')
    

class YahooReportTest(unittest.TestCase):
    _RAW_DATA = '''"GOOG",533.89,"5/3/2011","4:00pm",-4.67,537.13,542.01,529.63,2081574
"AAPL",348.20,"5/3/2011","4:00pm",+1.92,347.91,349.89,345.62,11198607
"600028.SS",8.58,"5/4/2011","1:47am",-0.10,8.64,8.67,8.55,23045288'''


    def test_yahoo_report(self):
        ret = YahooReport.parse(self._RAW_DATA)
        i = 0
        for r in ret:
            if i == 0:
                self.assertEqual(r.security.exchange, YahooNA())
                self.assertEqual(r.security.symbol, 'GOOG')
                self.assertEqual(str(r.date), "2011-05-03")
                self.assertEqual(r.time.hour, 16)
                self.assertEqual(r.time.minute, 0)
                self.assertEqual(r.price, 533.89)
                self.assertEqual(r.change, -4.67)
                self.assertEqual(r.open, 537.13)
                self.assertEqual(r.high, 542.01)
                self.assertEqual(r.low, 529.63)
                self.assertEqual(r.volume, 2081574)

            if i == 2:
                self.assertEqual(r.security.exchange, SH())
                self.assertEqual(r.security.symbol, '600028')

            i += 1

        self.assertEqual(i, 3)


class YahooDayTest(unittest.TestCase):
    def test_parse_day(self):
        path = os.path.dirname(os.path.realpath(__file__))
        f = open(os.path.join(path, 'yahoo_tables.csv'), 'r')
        data = f.read()
        f.close()

        security = YahooSecurity(YahooNA(), 'GOOG')
        iters = YahooDay.parse(security, data)
        i = 0
        for ohlc in iters:
            if i == 0:
                # 2011-05-03,537.13,542.01,529.63,533.89,2081500,533.89
                self.assertEqual(str(ohlc.date), "2011-05-03")
                self.assertEqual(ohlc.open, 537.13)
                self.assertEqual(ohlc.high, 542.01)
                self.assertEqual(ohlc.low, 529.63)
                self.assertEqual(ohlc.close, 533.89)
                self.assertEqual(ohlc.volume, 2081500)
                self.assertEqual(ohlc.adjclose, 533.89)
            i += 1


class YahooReportFetcherTest(unittest.TestCase):

    def test_init(self):
        f = YahooReportFetcher()
        self.assertEqual(f._base_url, 'http://download.finance.yahoo.com/d/quotes.csv')

    def test_init_with_arguments(self):
        f = YahooReportFetcher(time_out=10, request_size=50)
        self.assertEqual(f._time_out, 10)
        self.assertEqual(f._request_size, 50)
        
    def test_init_with_wrong_arguments(self):
        self.assertRaises(AssertionError,
                          YahooReportFetcher,
                          request_size=200)
        
    def test_fetch(self):
        f = YahooReportFetcher(request_size=2)
        s1 = YahooSecurity(YahooNA(), 'GOOG')
        s2 = YahooSecurity(YahooNA(), 'AAPL')
        s3 = YahooSecurity(SH(), '000001')

        def callback(body):
            qs = YahooReport.parse(body)
            for quote in qs:
                if quote.security == s3:
                    # something must wrong if SSE Composite Index goes down to 100
                    self.assertTrue(quote.price > 100)
        
        f.fetch(s1, s2, s3,
                callback=callback)

class YahooDayFetcherTest(unittest.TestCase):

    def test_init(self):
        f = YahooDayFetcher()
        self.assertEqual(f._base_url, 'http://ichart.finance.yahoo.com/table.csv')
        self.assertEqual(f._time_out, 20)
        self.assertEqual(f._max_clients, 10)

    def test_init_with_wrong_arguments(self):
        self.assertRaises(AssertionError,
                          YahooReportFetcher,
                          max_clients=20)
        
    def test_fetch(self):
        f = YahooDayFetcher()
        s1 = YahooSecurity(YahooNA(), 'GOOG')
        s2 = YahooSecurity(YahooNA(), 'AAPL')

        def callback(security, body):
            iters = YahooDay.parse(security, body)
            i = 0
            for ohlc in iters:
                self.assertTrue(ohlc.security in (s1, s2))
                if i == 0 and ohlc.security == s1:
                    self.assertEqual(str(ohlc.date), "2011-04-28")
                    self.assertEqual(ohlc.open, 538.06)
                    self.assertEqual(ohlc.high, 539.25)
                    self.assertEqual(ohlc.low, 534.08)
                    self.assertEqual(ohlc.close, 537.97)
                    self.assertEqual(ohlc.volume, 2037400.0)
                    
                i += 1

        start_date = datetime.datetime.strptime("2011-04-01", "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime("2011-04-28", "%Y-%m-%d").date()
        f.fetch(s1, s2,
                callback=callback,
                start_date=start_date,
                end_date=end_date)

class YahooNewsFetcherTest(unittest.TestCase):
    def test_fetch(self):
        f = YahooNewsFetcher()
        s1 = YahooSecurity(YahooNA(), 'GOOG')
        s2 = YahooSecurity(YahooNA(), 'AAPL')
        s3 = YahooSecurity(SH(), '000001')

        def callback(security, response):
            self.assertTrue(response.body.startswith('<?xml'))

        f.fetch(s1, callback=callback)



if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = tongshi
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010 yinhm

'''网际风数据接口实现

接口
===
网际风接口兼容通视协议，通视协议是一个企业规范，因为出现的最早且使用广泛，逐渐
成为默认的行业标准。

通视协议是点播方式，网际风数据源与此不同，采用了全推方式。全推方式接更适合大量
数据更新。

网际风协议在通视基础上增加了盘口，除权，财务等数据。

接口调用方式参考文档：
分析家通视规范： http://www.51wjf.com/stkdrv.txt
网际风规范： http://www.51wjf.com/wjffun.txt

实现
===
网际风分客户端和stock.dll两部分，使用python ctypes加载stock.dll触发网际风客户端
自动运行，登陆服务器，接收数据。网际风数据采用推送方式返回给
stock.dll，stock.dll接收到数据后使用windows message通知监听程序（如本脚本），监
听程序根据message中的信息不同处理相应数据。
'''

import os
import sys
import thread
import time

import win32api
import win32con
import win32gui
import winerror

from ctypes import *
from ctypes.wintypes import *

from datetime import datetime

import numpy as np

from datafeed.client import Client


RCV_WORK_SENDMSG = 4

RCV_REPORT = 0x3f001234
RCV_FILEDATA = 0x3f001235

STKLABEL_LEN = 10  # 股号数据长度,国内市场股号编码兼容钱龙
STKNAME_LEN = 32   # 股名长度
MAX_PATH = 260     # http://msdn.microsoft.com/en-us/library/aa365247(VS.85).aspx#maxpath


FILE_HISTORY_EX = 2  # 补日线数据
FILE_MINUTE_EX = 4   # 补分钟线数据
FILE_POWER_EX = 6    # 补充除权数据


# 下列2条补数据类型为网际风新增的扩充类型，通视协议中并未包含下述类型：
FILE_5MINUTE_EX=0x51  # 补5分钟K线  数据格式与日线完全相同 仅仅参数不同而已
FILE_1MINUTE_EX=0x52  # 补1分钟K线  数据格式与日线完全相同 仅仅参数不同而已

FILE_BASE_EX = 0x1000  # 钱龙兼容基本资料文件,m_szFileName仅包含文件名
FILE_NEWS_EX = 0x1002  # 新闻类,其类型由m_szFileName中子目录名来定
FILE_HTML_EX = 0x1004  # HTML文件,m_szFileName为URL

FILE_SOFTWARE_EX = 0x2000  # 升级软件

# 上海市场
MARKET_SH = 18515
# 深圳市场
MARKET_SZ = 23123


def format_market(value):
    if value == MARKET_SH:
        return 'SH'
    elif value == MARKET_SZ:
        return 'SZ'
    else:
        raise Exception('Unknown market.')


class Report(Structure):
    '''tagRCV_REPORT_STRUCTExV3 data structure
    '''
    _pack_ = 1
    _fields_ = [('m_cbSize', WORD),
                ('m_time', c_int),  # time_t结构
                ('m_wMarket', WORD),
                ('m_szLabel', c_char * STKLABEL_LEN),  # 股票代码,以'\0'结尾
                ('m_szName', c_char * STKNAME_LEN),    # 股票名称,以'\0'结尾

                ('m_fLastClose', c_float),
                ('m_fOpen', c_float),
                ('m_fHigh', c_float),
                ('m_fLow', c_float),
                ('m_fNewPrice', c_float),
                ('m_fVolume', c_float),
                ('m_fAmount', c_float),

                ('m_fBuyPrice', c_float * 3),
                ('m_fBuyVolume', c_float * 3),
                ('m_fSellPrice', c_float * 3),
                ('m_fSellVolume', c_float * 3),

                ('m_fBuyPrice4', c_float),
                ('m_fBuyVolume4', c_float),
                ('m_fSellPrice4', c_float),
                ('m_fSellVolume4', c_float),

                ('m_fBuyPrice5', c_float),
                ('m_fBuyVolume5', c_float),
                ('m_fSellPrice5', c_float),
                ('m_fSellVolume5', c_float)]


    @property
    def symbol(self):
        return format_market(self.m_wMarket) + self.m_szLabel

    def is_valid(self):
        """Is this report data valid?

        We seems get data full of zero if stock got suspended.
        Use this method to detect is the data valid so you can filter it.
        """
        return self.m_fNewPrice > 0

    def to_dict(self):
        '''Convert to dict object.
        '''
        t = datetime.fromtimestamp(self.m_time)
        t = t.strftime('%Y-%m-%d %H:%M:%S')

        quote = {
            'time'     : t,
            'timestamp': self.m_time,
            'price'    : self.m_fNewPrice,
            'amount'   : self.m_fAmount,
            'volume'   : self.m_fVolume,
            'symbol'   : self.symbol,
            'name'     : self.m_szName.decode('gbk'),
            'open'     : self.m_fOpen,
            'high'     : self.m_fHigh,
            'low'      : self.m_fLow,
            'close'    : self.m_fNewPrice,
            'preclose' : self.m_fLastClose
            }
        return quote


class Head(Structure):
    '''头数据'''
    _fields_ = [('m_dwHeadTag', DWORD),
                ('m_wMarket', WORD),
                ('m_szLabel', c_char * STKLABEL_LEN)]


class History(Structure):
    '''补充日线数据'''

    _fields_ = [('m_time', c_int),
                ('m_fOpen', c_float),
                ('m_fHigh', c_float),
                ('m_fLow', c_float),
                ('m_fClose', c_float),
                ('m_fVolume', c_float),
                ('m_fAmount', c_float),
                ('m_wAdvance', WORD),
                ('m_wDecline', WORD)]

    def to_tuple(self):
        """Convert ohlc to tuple.

        Returns
        -------
        tuple
        """
        return (self.m_time,
                self.m_fOpen,
                self.m_fHigh,
                self.m_fLow,
                self.m_fClose,
                self.m_fVolume,
                self.m_fAmount)


class HistoryUnion(Union):
    '''日线数据头 or 日线数据'''

    _fields_ = [('data', History),
                ('head', Head)]

    DTYPE = [('time', '<i4'),
             ('open', '<f4'),
             ('high', '<f4'),
             ('low', '<f4'),
             ('close', '<f4'),
             ('volume', '<f4'),
             ('amount', '<f4')]

    def market(self):
        return format_market(self.head.m_wMarket)

    def symbol(self):
        return self.head.m_szLabel


class Minute(Structure):
    _fields_ = [('m_time', c_int),
                ('m_fPrice', c_float),
                ('m_fVolume', c_float),
                ('m_fAmount', c_float)]

    def to_tuple(self):
        """Convert Minute to tuple.

        Returns
        -------
        tuple
        """
        return (self.m_time,
                self.m_fPrice,
                self.m_fVolume,
                self.m_fAmount)


class MinuteUnion(Union):
    '''补充分时数据'''

    _fields_ = [('data', Minute),
                ('head', Head)]

    DTYPE = [('time', '<i4'),
             ('price', '<f4'),
             ('volume', '<f4'),
             ('amount', '<f4')]

    def market(self):
        return format_market(self.head.m_wMarket)

    def symbol(self):
        return self.head.m_szLabel


class Dividend(Union):
    pass


class FileHead(Structure):
    _fields_ = [('m_dwAttrib', DWORD),
                ('m_dwLen', DWORD),
                ('m_dwSerialNo', DWORD),
                ('m_szFileName', c_char * MAX_PATH)]


class ReceiveDataUnion(Union):
    _fields_ = [('m_pReportV3', Report),
                ('m_pDay', HistoryUnion),
                ('m_pMinute', MinuteUnion),
                ('m_pPower', Dividend),
                ('m_pData', c_void_p)]


class ReceiveData(Structure):
    _fields_ = [('m_wDataType', c_int),
                ('m_nPacketNum', c_int),
                ('m_File', FileHead),
                ('m_bDISK', c_bool),
                ('ptr', c_int)]


class MainWindow(object):
    _WM_USER_STOCK_DATA = win32con.WM_USER + 10

    def __init__(self, host='localhost', password=None):
        self.client = Client(host=host, password=password, socket_timeout=10)

        msg_task_bar_restart = win32gui.RegisterWindowMessage("TaskbarCreated")
        message_map = {
            msg_task_bar_restart: self._on_restart,
            win32con.WM_DESTROY: self._on_destroy,
            win32con.WM_COMMAND: self._on_command,
            self._WM_USER_STOCK_DATA: self._on_data_receive,
            win32con.WM_USER+20: self._on_taskbar_notify
            }
        # Register the Window class.
        wc = win32gui.WNDCLASS()
        hinst = wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = "StockTaskBar"
        wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
        wc.hCursor = win32api.LoadCursor(0, win32con.IDC_ARROW)
        wc.hbrBackground = win32con.COLOR_WINDOW
        wc.lpfnWndProc = message_map  # could also specify a wndproc.

        # Don't blow up if class already registered to make testing easier
        try:
            classAtom = win32gui.RegisterClass(wc)
        except win32gui.error, err_info:
            if err_info.winerror!=winerror.ERROR_CLASS_ALREADY_EXISTS:
                raise

        # Create the Window.
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = win32gui.CreateWindow(wc.lpszClassName, "WJF Data Processer", style,
                                          0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT,
                                          0, 0, hinst, None)
        win32gui.UpdateWindow(self.hwnd)
        self._do_create_icons()
        self._do_stock_quote()

        self.periodic_wrapper(30)

    def Timer(self, timeout):
        time.sleep(timeout)
        self._on_time()
        self.periodic_wrapper(timeout)

    def periodic_wrapper(self, timeout):
        # Thread needed because win32gui does not expose SetTimer API
        thread.start_new_thread(self.Timer, (timeout, ))

    def _on_time(self):
        d = datetime.today()
        if d.hour == 15 and d.minute == 3:
            # make sure we are not receiving reporting data after market closed.
            print("Market closed, exit on %d:%d." % (d.hour, d.minute))
            win32gui.PostMessage(self.hwnd, win32con.WM_COMMAND, 1025, 0)

    def _do_stock_quote(self):
        self.stockdll = windll.LoadLibrary('C:\Windows\System32\Stock.dll')

        ret = self.stockdll.Stock_Init(self.hwnd,
                                       self._WM_USER_STOCK_DATA,
                                       RCV_WORK_SENDMSG)

        if ret != 1:
            raise Exception("Stock Init failed.")

    def _do_create_icons(self):
        # Try and find a custom icon
        hinst = win32api.GetModuleHandle(None)
        iconPathName = os.path.abspath(os.path.join(
                os.path.split(sys.executable)[0], "pyc.ico"))
        if not os.path.isfile(iconPathName):
            # Look in DLLs dir, a-la py 2.5
            iconPathName = os.path.abspath(os.path.join(
                    os.path.split(sys.executable)[0], "DLLs", "pyc.ico" ))

        if not os.path.isfile(iconPathName):
            # Look in the source tree.
            iconPathName = os.path.abspath(os.path.join(
                    os.path.split(sys.executable)[0], "..\\PC\\pyc.ico" ))

        if os.path.isfile(iconPathName):
            icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
            hicon = win32gui.LoadImage(hinst, iconPathName, win32con.IMAGE_ICON, 0, 0, icon_flags)
        else:
            print "Can't find a Python icon file - using default"
            hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (self.hwnd, 0, flags, win32con.WM_USER+20, hicon, "Python Demo")
        try:
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        except win32gui.error:
            # This is common when windows is starting, and this code is hit
            # before the taskbar has been created.
            print "Failed to add the taskbar icon - is explorer running?"
            # but keep running anyway - when explorer starts, we get the
            # TaskbarCreated message.

    def _on_restart(self, hwnd, msg, wparam, lparam):
        self._do_create_icons()

    def _on_destroy(self, hwnd, msg, wparam, lparam):
        nid = (self.hwnd, 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        win32gui.PostQuitMessage(0)  # Terminate the app.

    def _on_data_receive(self, hwnd, msg, wparam, lparam):
        header = ReceiveData.from_address(lparam)

        if wparam == RCV_REPORT:
            # Report
            records = {}
            for i in xrange(header.m_nPacketNum):
                r = Report.from_address(header.ptr + sizeof(Report) * i)
                if r.is_valid():
                    records[r.symbol] = r.to_dict()

            self.client.put_reports(records)
            print "%d report data sended" % header.m_nPacketNum
        elif wparam == RCV_FILEDATA:
            if header.m_wDataType in (FILE_HISTORY_EX, FILE_5MINUTE_EX, FILE_1MINUTE_EX):
                # Daily history
                history_head = HistoryUnion.from_address(header.ptr)

                records = []
                key = history_head.market() + history_head.symbol()
                for i in xrange(header.m_nPacketNum - 1):
                    # start from ptr + sizeof(History), first one was the header
                    q = History.from_address(header.ptr + sizeof(History) * (i+1))
                    records.append(q.to_tuple())

                rec = np.array(records, dtype=HistoryUnion.DTYPE)

                if header.m_wDataType == FILE_HISTORY_EX:
                    self.client.put_day(key, rec)
                elif header.m_wDataType == FILE_5MINUTE_EX:
                    self.client.put_5minute(key, rec)
                elif header.m_wDataType == FILE_1MINUTE_EX:
                    self.client.put_1minute(key, rec) # no implementation
            elif header.m_wDataType == FILE_MINUTE_EX:
                # Minute
                minute_head = MinuteUnion.from_address(header.ptr)

                records = []
                key = minute_head.market() + minute_head.symbol()
                for i in xrange(header.m_nPacketNum - 1):
                    # start from ptr + sizeof(Minute), first one was the header
                    q = Minute.from_address(header.ptr + sizeof(Minute) * (i+1))
                    records.append(q.to_tuple())

                rec = np.array(records, dtype=MinuteUnion.DTYPE)
                self.client.put_minute(key, rec)
            elif header.m_wDataType == FILE_POWER_EX:
                print "power ex"
            elif header.m_wDataType == FILE_BASE_EX:
                print "base ex"
            elif header.m_wDataType == FILE_NEWS_EX:
                print "news ex"
            elif header.m_wDataType == FILE_HTML_EX:
                print "html ex"
            elif header.m_wDataType == FILE_SOFTWARE_EX:
                print "software ex"
            else:
                print "Unknown file data."
        else:
            print "Unknown data type."
        return 1

    def _on_taskbar_notify(self, hwnd, msg, wparam, lparam):
        if lparam == win32con.WM_LBUTTONUP or lparam == win32con.WM_RBUTTONUP:
            print "You right clicked me."
            menu = win32gui.CreatePopupMenu()
            win32gui.AppendMenu(menu, win32con.MF_STRING, 1023, "Display Dialog")
            win32gui.AppendMenu(menu, win32con.MF_STRING, 1025, "Exit program" )
            pos = win32gui.GetCursorPos()
            # See http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winui/menus_0hdi.asp
            win32gui.SetForegroundWindow(self.hwnd)
            win32gui.TrackPopupMenu(menu, win32con.TPM_LEFTALIGN, pos[0], pos[1], 0, self.hwnd, None)
            win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)
        return 1

    def _on_command(self, hwnd, msg, wparam, lparam):
        id = win32api.LOWORD(wparam)
        if id == 1023:
            print "Goodbye"
        elif id == 1025:
            print "Goodbye"
            win32gui.DestroyWindow(self.hwnd)
        else:
            print "Unknown command -", id


def program_running():
    '''Check if tongshi client is running.

    python has no method to change windows procname,
    so we check python and double check if WJFMain running too, since WJFMain
    auto exit when client exit.
    '''
    cmd = os.popen('tasklist')
    x = cmd.readlines()
    for y in x:
        p = y.find('WJFMain')
        if p >= 0:
            return True
    return False


def run_tongshi_win(server_addr='localhost', server_password=None):
    if program_running():
        print "already running"
        exit(0)

    w=MainWindow(host=server_addr, password=server_password)
    win32gui.PumpMessages()

if __name__=='__main__':
    run_tongshi_win()

########NEW FILE########
__FILENAME__ = yahoo
# -*- coding: utf-8 -*-

"""
Yahoo Finance API tags:
http://www.gummy-stuff.org/Yahoo-data.htm

See also:
https://github.com/yql/yql-tables/blob/master/yahoo/finance/

Yahoo! Finance news headlines:
http://developer.yahoo.com/finance/
"""
import csv
import functools
import logging
import sys

from cStringIO import StringIO

from dateutil import parser
from tornado import httpclient
from tornado import ioloop

from datafeed.bidict import Bidict
from datafeed.exchange import *
from datafeed.quote import *
from datafeed.providers.http_fetcher import *
from datafeed.utils import json_decode

__all__ = ['YahooSecurity',
           'YahooReport', 'YahooReportFetcher',
           'YahooDay', 'YahooDayFetcher',
           'YahooNewsFetcher']


# See full list of exchangs on Yahoo! finance:
# http://finance.yahoo.com/exchanges
_EXCHANGES = Bidict({
        "HK": "HK",
        "LON": "L",
        "SH": "SS",
        "SZ": "SZ",
        })


class YahooSecurity(Security):
    SUFFIX_NA = (NASDAQ(), NYSE(), AMEX())

    def __init__(self, exchange, *args, **kwds):
        if exchange in (self.SUFFIX_NA):
            exchange = YahooNA()
        super(YahooSecurity, self).__init__(exchange, *args, **kwds)

    def __str__(self):
        """symbol with exchange abbr suffix"""
        if self.exchange == YahooNA():
            ret = self.symbol
        else:
            ret = "%s.%s" % (self.symbol, self._abbr)
        return ret

    @property
    def _abbr(self):
        """Yahoo finance specific exchange abbr."""
        return _EXCHANGES[str(self.exchange)]

    @classmethod
    def from_string(cls, idstr):
        if idstr.find('.') > 0:
            symbol, abbr = idstr.split('.')
            exchange = cls.get_exchange_from_abbr(abbr)
        else:
            symbol = idstr
            # US, Japan, Lodon exchnages on Yahoo! finance have no suffix
            exchange = YahooNA()
        return cls(exchange, symbol)

    @classmethod
    def get_exchange_from_abbr(cls, abbr):
        """get exchange from yahoo abbr"""
        ex = _EXCHANGES[abbr]
        ex_cls = getattr(sys.modules[__name__], ex)
        return ex_cls()
        

class YahooReport(Report):

    # Tags format defined by YahooReportFetcher which is:
    # "sl1d1t1c1ohgv"
    # FIXME: Yahoo quotes became N/A during session after hours.
    _DEFINITIONS = (
        ("symbol", str),
        ("price", float),
        ("date", lambda x: parser.parse(x).date()),
        ("time", parser.parse),
        ("change", float),
        ("open", float),
        ("high", float),
        ("low", float),
        ("volume", float),
        )

    def __init__(self, raw_data):
        assert len(raw_data) == len(self._DEFINITIONS)

        i = 0
        data = {}
        for conf in self._DEFINITIONS:
            key, callback = conf
            data[key] = callback(raw_data[i])
            i += 1

        security = YahooSecurity.from_string(data.pop('symbol'))
        super(YahooReport, self).__init__(security, data)

    @staticmethod
    def parse(rawdata):        
        f = StringIO(rawdata)
        r = csv.reader(f)
        return (YahooReport(line) for line in r)


class YahooDay(Day):

    _DEFINITIONS = (
        ("date", lambda x: parser.parse(x).date()),
        ("open", float),
        ("high", float),
        ("low", float),
        ("close", float),
        ("volume", float),
        ("adjclose", float))

    def __init__(self, security, raw_data):
        assert len(raw_data) == len(self._DEFINITIONS)

        data = {}
        i = 0
        for conf in self._DEFINITIONS:
            data[conf[0]] = conf[1](raw_data[i])
            i += 1

        super(YahooDay, self).__init__(security, data)

    @staticmethod
    def parse(security, rawdata):
        f = StringIO(rawdata)
        r = csv.reader(f)
        r.next() # skip header
        return (YahooDay(security, line) for line in r)


class YahooReportFetcher(Fetcher):

    # Live quotes tags format,
    # consistent with downloads link on the web page.
    _FORMAT = "sl1d1t1c1ohgv"
    
    # Maximum number of stocks we'll batch fetch.
    _MAX_REQUEST_SIZE = 100
    
    def __init__(self, base_url='http://download.finance.yahoo.com/d/quotes.csv',
                 time_out=20, max_clients=10, request_size=100):
        assert request_size <= self._MAX_REQUEST_SIZE
        
        super(YahooReportFetcher, self).__init__(base_url, time_out, max_clients)
        self._request_size = request_size

    def _fetching_urls(self, *args, **kwargs):
        ids = (str(s) for s in args)
        ids = self._slice(ids)

        return (self._make_url(filter(lambda x: x != None, i)) for i in ids)

    def _make_url(self, ids):
        """Make url to fetch.

        example:
        http://download.finance.yahoo.com/d/quotes.csv?s=GOOG+AAPL+600028.SS&f=sl1d1t1c1ohgv&e=.csv
        """
        return "%s?s=%s&f=%s&e=.csv" % (self._base_url, '+'.join(ids), self._FORMAT)

    def _callback(self, security, **kwargs):
        if 'callback' in kwargs:
            callback = kwargs['callback']
        else:
            callback = None
        return functools.partial(self._handle_request, callback)

    def _handle_request(self, callback, response):
        try:
            self.queue_len = self.queue_len - 1

            if response.error:
                logging.error(response.error)
            else:
                callback(response.body)
        except StandardError:
            logging.error("Wrong data format.")
        finally:
            self.stop()


class YahooDayFetcher(DayFetcher):

    def __init__(self, base_url='http://ichart.finance.yahoo.com/table.csv',
                 time_out=20, max_clients=10):
        super(YahooDayFetcher, self).__init__(base_url, time_out, max_clients)

    def _make_url(self, security, **kwargs):
        """Make url to fetch.

        Parameters:
        s  Stock Ticker (for example, MSFT)  
        a  Start Month (0-based; 0=January, 11=December)  
        b  Start Day  
        c  Start Year  
        d  End Month (0-based; 0=January, 11=December)  
        e  End Day  
        f  End Year  
        g  Always use the letter d  

        example:
        http://ichart.finance.yahoo.com/table.csv?s=GOOG&d=4&e=4&f=2011&g=d&a=7&b=19&c=2004&ignore=.csv
        """
        url_format = "%s?s=%s&g=d&a=%s&b=%s&c=%s"
        url_format += "&d=%s&e=%s&f=%s"

        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        url = url_format % (self._base_url, str(security),
                            start_date.month - 1, start_date.day, start_date.year,
                            end_date.month - 1, end_date.day, end_date.year)
        return url


class YahooNewsFetcher(Fetcher):
    _BASE_URL = "http://feeds.finance.yahoo.com/rss/2.0/headline"
    
    # Maximum number of stocks we'll batch fetch.
    _MAX_REQUEST_SIZE = 100
    
    def __init__(self, base_url=_BASE_URL, time_out=10, max_clients=5):
        super(YahooNewsFetcher, self).__init__(base_url, time_out, max_clients)

    def _fetching_urls(self, *args, **kwargs):
        return (self._make_url(str(security)) for security in args)

    def _make_url(self, symbol):
        """Make url to fetch.

        example:
        http://feeds.finance.yahoo.com/rss/2.0/headline?s=yhoo&region=US&lang=en-US
        """
        return "%s?s=%s&region=US&lang=en-US" % (self._base_url, symbol)

    def _callback(self, security, **kwargs):
        if 'callback' in kwargs:
            callback = kwargs['callback']
        else:
            callback = None
        return functools.partial(self._handle_request,
                                 callback,
                                 security)

    def _handle_request(self, callback, security, response):
        try:
            self.queue_len = self.queue_len - 1

            if response.error:
                logging.error(response.error)
            else:
                callback(security, response)
        finally:
            self.stop()

########NEW FILE########
__FILENAME__ = quote
# -*- coding: utf-8 -*-

from datetime import datetime
from datafeed.exchange import Security

__all__ = ['Report', 'Day', 'Minute', 'SecurityList']


class _Struct(object):

    def __init__(self, security, adict):
        assert isinstance(security, Security)

        self.__dict__.update(adict)
        self.security = security

    def assert_data(self):
        pass

    def __getstate__(self):
        odict = self.__dict__.copy()
        odict.pop('_raw_data', None)
        return odict

    def __setstate__(self, state):
        self.__dict__.update(state)

    def todict(self):
        return self.__getstate__()

class Report(_Struct):

    def __init__(self, security, adict):    
        assert isinstance(adict['price'], float)
        assert isinstance(adict['time'], datetime)
        
        super(Report, self).__init__(security, adict)

    def __str__(self):
        return "%s, %s, %s" % (self.security, self.price, self.time)


class Day(_Struct):
    pass


class Minute(_Struct):
    pass

class SecurityList(_Struct):
    pass

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010 yinhm

'''A datafeed server.

All datefeed R/W IO should delegate to this.


Supported commands
==================

    auth
    get_mtime
    get_list
    get_report
    get_reports
    get_minute
    get_1minute
    get_5minute
    get_day
    get_dividend
    get_sector
    get_stats
    get_report
    put_reports
    put_minute
    put_1minute
    put_5minute
    put_day

    
Client Protocol
===============

A redis like protocol which is using plain text and binary safe.

Requests

This is the general form:

    *<number of arguments> CR LF
    $<number of bytes of argument 1> CR LF
    <argument data> CR LF
    ...
    $<number of bytes of argument N> CR LF
    <argument data> CR LF

See the following example:

    *3
    $3
    SET
    $5
    mykey
    $7
    myvalue
    $3
    npy
    
This is how the above command looks as a quoted string, so that it is possible
to see the exact value of every byte in the query:

    "*3\r\n$3\r\nSET\r\n$5\r\nmykey\r\n$7\r\nmyvalue\r\n$3\r\nnpy\r\n"

The last argument always be format type, format should be one of:

    npy, zip, json

Resoponse:

Datafeed server will reply to commands with different kinds of replies. It is
possible to check the kind of reply from the first byte sent by the server:
    
    With a single line reply the first byte of the reply will be "+"
    With an error message the first byte of the reply will be "-"
    With bulk reply the first byte of the reply will be "$"
    

Notice
======
We do not support redis like multi gets or multi bulk replies.
For more details: http://redis.io/topics/protocol
'''
import datetime
import errno
import logging
import marshal
import os
import re
import sys
import time
import zlib

from cStringIO import StringIO

import numpy as np

from tornado import iostream
from tornado import stack_context
try:
    from tornado.tcpserver import TCPServer # tornado 3.x
except ImportError:
    from tornado.netutil import TCPServer # tornado 2.x

from datafeed import datastore
from datafeed.utils import json_encode


__all__ = ['Server', 'Connection', 'Application', 'Request', 'Handler']

class Server(TCPServer):
    def __init__(self, request_callback, io_loop=None, auth_password=None, **kwargs):
        self.request_callback = request_callback
        self.stats = Stats()
        self.auth_password = auth_password
        self.require_auth = False
        if self.auth_password:
            self.require_auth = True
        TCPServer.__init__(self, io_loop=io_loop, **kwargs)

    def start(self):
        """Start a single process."""
        super(Server, self).start(num_processes=1)

    def handle_stream(self, stream, address):
        Connection(stream, address, self.stats,
                   self.require_auth, self.auth_password, self.request_callback)

    def log_stats(self):
        self.stats.log()


class Stats(dict):
    def record(self, method, time):
        if not self.has_key(method):
            self.__setitem__(method, {'min':time, 'max':time, 'total':0, 'count':0})

        item = self.__getitem__(method)
        if time < item['min']:
            item['min'] = time
        if time > item['max']:
            item['max'] = time
        item['total'] += time
        item['count'] += 1

    def log(self):
        msg = ["\nmethod\tmin\tmax\ttotal\tcount"]
        for method, item in self.iteritems():
            msg.append("%s\t\t%.2f\t%.2f\t%.2f\t%d" % \
                           (method, item['min'], item['max'], item['total'], item['count']))
        logging.info("\n".join(msg))


class Connection(object):

    def __init__(self, stream, address, stats, require_auth, auth_password, request_callback=None):
        self.stream = stream
        self.address = address
        self.stats = stats
        self.require_auth = require_auth
        self.auth_password = auth_password
        self.authenticated = False
        self.request_callback = request_callback
        self._request = Request(connection=self)
        self._request_finished = False

        # Save stack context here, outside of any request.  This keeps
        # contexts from one request from leaking into the next.
        self._on_request_wrap = stack_context.wrap(self._on_request)
        self.stream.read_until('\r\n', self._on_request_wrap)

    def write(self, chunk):
        assert self._request, "Request closed"
        if not self.stream.closed():
            self.stream.write(chunk, self._on_write_complete)

    def finish(self):
        assert self._request, "Request closed"
        self._request_finished = True
        if not self.stream.writing():
            self._finish_request()

    def disconnect(self):
        self.stream.close()

    def auth(self, password):
        '''Verify password and set authenticated if match.'''
        if not self.require_auth:
            return True

        if password == self.auth_password:
            self.authenticated = True
        else:
            self.authenticated = False
        return self.authenticated

    def _on_write_complete(self):
        if self._request_finished:
            self._finish_request()

    def _finish_request(self):
        self._request = None
        self._request_finished = False
        self.stream.read_until("\r\n", self._on_request_wrap)

    def _on_request(self, data):
        self._request = Request(connection=self)

        request_type = data[0]
        if request_type != '*':
            if data.strip() == 'quit':
                return self.disconnect()
            else:
                return self._on_request_error(data)
            
        # *<number of arguments> CR LF
        try:
            self._args_count = int(data[1:-2])
            self.stream.read_until("\r\n", self._on_argument_head)
        except ValueError:
            return self._on_request_error(data)

    def _on_request_error(self, data=None):
        self.write("-ERR unknown command %s\r\n" % data)

    def _on_argument_head(self, data):
        request_type = data[0]
        if request_type != '$':
            return self._on_request_error()

        # $<number of bytes of argument N> CR LF
        # <argument data> CR LF
        bytes = int(data[1:-2])
        self.stream.read_bytes(bytes + 2, self._on_argument_data)
        
    def _on_argument_data(self, data):
        self._request.args.append(data[:-2])
        self._args_count = self._args_count - 1

        if self._args_count > 0:
            self.stream.read_until("\r\n", self._on_argument_head)
        else:
            self.request_callback(self._request)
        

class Request(object):
    def __init__(self, connection, *args):
        self.connection = connection
        self._start_time = time.time()
        self._finish_time = None
        self.args = list(args)

        self.response_message = ""

    @property
    def method(self):
        return self.args[0].lower()

    def write(self, chunk):
        """Writes the given chunk to the response stream."""
        assert isinstance(chunk, str)
        if self.connection:
            self.connection.write(chunk)

    def write_ok(self):
        """Shortcut of write OK."""
        self.write("+OK\r\n")

    def write_error(self, msg=''):
        """Shortcut of write OK."""
        self.write("-ERR %s\r\n" % msg)

    def finish(self):
        """Finishes this HTTP request on the open connection."""
        if self.connection:
            self.connection.finish()
        self._finish_time = time.time()

    def record_stats(self):
        if self.connection:
            self.connection.stats.record(self.method, self.request_time())

    def request_time(self):
        """Returns the amount of time it took for this request to execute."""
        if self._finish_time is None:
            return time.time() - self._start_time
        else:
            return self._finish_time - self._start_time


class Application(object):

    def __init__(self, datadir, exchange, **kwargs):
        self.dbm = datastore.Manager(datadir, exchange)
        self.exchange = exchange

        if 'handler' in kwargs:
            self._handler = kwargs['handler']
        else:
            self._handler = Handler

    def __call__(self, request):
        handler = self._handler(self, request)
        handler._execute()
        return handler


class Handler(object):

    SUPPORTED_METHODS = ('auth',
                         'get_last_quote_time',
                         'get_mtime',
                         'get_list',
                         'get_report',
                         'get_reports',
                         'get_minute',
                         'get_1minute',
                         'get_5minute',
                         'get_day',
                         'get_dividend',
                         'get_sector',
                         'get_stats',
                         'get_report',
                         'put_reports',
                         'put_minute',
                         'put_1minute',
                         'put_5minute',
                         'put_day')

    def __init__(self, application, request, **kwargs):
        self.application = application
        self.request = request
        self.dbm = application.dbm

        self._finished = False
    
    def auth(self, password, format='plain'):
        """Authticate.
        """
        ret = self.request.connection.auth(password)
        if ret:
            self.request.write_ok()
        else:
            self.request.write_error("invalid password")
            if not self._finished:
                self.finish()

    def get_mtime(self, *args, **kwds):
        """Return last quote timestamp.
        """
        self.request.write(":%d\r\n" % self.dbm.mtime)

    def get_last_quote_time(self, *args, **kwds):
        """Return last quote timestamp.
        """
        logging.warning("Deprecated, using get_mtime instead.")
        self.get_mtime()

    def get_list(self, match=None, format='json'):
        assert format == 'json'

        if match != '':
            _re = re.compile('^(%s)' % match, re.I)
            ret = dict([(r, v) for r, v in self.dbm.reportstore.iteritems() \
                            if _re.search(r)])
        else:
            ret = self.dbm.reportstore.to_dict()

        return self._write_response(json_encode(ret))

    def get_report(self, symbol, format):
        try:
            data = self.dbm.get_report(symbol)
            if format == 'json':
                data = json_encode(data)
            self._write_response(data)
        except KeyError:
            self.request.write("-ERR Symbol %s not exists.\r\n" % symbol)

    def get_reports(self, *args):
        assert len(args) > 1
        format = args[-1]
        data = self.dbm.get_reports(*args[:-1])

        if format == 'json':
            data = json_encode(data)
            
        self._write_response(data)

    def get_minute(self, symbol, timestamp, format='npy'):
        """Get daily minutes history.

        Arguments:
        symbol: String of security.
        timestamp: Which day data to get.
        format: npy or json
        """
        try:
            ts = int(timestamp)
            if ts > 0:
                store = self.dbm.get_minutestore_at(ts)
            else:
                store = self.dbm.minutestore
                
            y = store.get(symbol)

            if format == 'npy':
                memfile = StringIO()
                np.save(memfile, y)
                data = memfile.getvalue()
                del(y)
            else:
                data = json_encode(y.tolist())
            self._write_response(data)
        except KeyError:
            self.request.write("-ERR Symbol %s not exists.\r\n" % symbol)

    def get_1minute(self, symbol, date, format='npy'):
        """Get 5min historical quotes.

        Arguments:
          symbol: String of security.
          date: Which day data to get.
          format: npy or json
        """
        try:
            if isinstance(date, str):
                date = datetime.datetime.strptime(date, '%Y%m%d').date()

            y = self.dbm.oneminstore.get(symbol, date)

            if format == 'npy':
                memfile = StringIO()
                np.save(memfile, y)
                data = memfile.getvalue()
                del(y)
            else:
                data = json_encode(y.tolist())
            self._write_response(data)
        except KeyError:
            self.request.write("-ERR No data.\r\n")

    def get_5minute(self, symbol, date, format='npy'):
        """Get 5min historical quotes.

        Arguments:
          symbol: String of security.
          date: Which day data to get.
          format: npy or json
        """
        try:
            if isinstance(date, str):
                date = datetime.datetime.strptime(date, '%Y%m%d').date()

            y = self.dbm.fiveminstore.get(symbol, date)

            if format == 'npy':
                memfile = StringIO()
                np.save(memfile, y)
                data = memfile.getvalue()
                del(y)
            else:
                data = json_encode(y.tolist())
            self._write_response(data)
        except KeyError:
            self.request.write("-ERR No data.\r\n")

    def get_dividend(self, symbol, format='npy'):
        try:
            try:
                y = self.dbm.divstore.get(symbol)[:]
            except TypeError:
                y = np.zeros(0)

            if format == 'npy':
                memfile = StringIO()
                np.save(memfile, y)
                data = memfile.getvalue()
                del(y)
            else:
                data = json_encode(y.tolist())
            self._write_response(data)
        except KeyError:
            self.request.write("-ERR Symbol %s not exists.\r\n" % symbol)

    def get_sector(self, name, format='json'):
        try:
            data = self.dbm.sectorstore[name]
            if format == 'json':
                data = json_encode(data)
            self._write_response(data)
        except KeyError:
            self.request.write("-ERR Sector %s not exists.\r\n" % name)

    def get_stats(self, name, format='json'):
        stats = self.request.connection.stats
        self._write_response(json_encode(stats))

    def get_day(self, symbol, length_or_date, format='npy'):
        """Get OHLCs quotes.

        Return chronicle ordered quotes.
        """
        try:
            if len(length_or_date) == 8: # eg: 20101209
                date = datetime.datetime.strptime(length_or_date, '%Y%m%d').date()
                y = self.dbm.daystore.get_by_date(symbol, date)
            else:
                length = length_or_date
                y = self.dbm.daystore.get(symbol, int(length))
                if length == 1:
                    y = y[0]

            if format == 'npy':
                memfile = StringIO()
                np.save(memfile, y)
                data = memfile.getvalue()
                del(y)
            else:
                data = json_encode(y.tolist())
            self._write_response(data)
        except KeyError:
            self.request.write("-ERR Symbol %s not exists.\r\n" % symbol)

    def _write_response(self, ret):
        self.request.write("$%s\r\n%s\r\n" % (len(ret), ret))
        
    def put_reports(self, data, format='zip'):
        """Update reports from data.

        Data Format:

        data should be zlib compressed python dicts serializing by marshal.
        """
        assert format == 'zip'

        try:
            data = marshal.loads(zlib.decompress(data))
            assert isinstance(data, dict)
        except StandardError:
            return self.request.write("-ERR wrong data format\r\n")
        self.dbm.update_reports(data)
        self.request.write_ok()
        
    def put_minute(self, symbol, data, format='npy'):
        func = getattr(self.dbm, "update_minute")
        self._put(func, symbol, data, format)
        
    def put_1minute(self, symbol, data, format='npy'):
        self.dbm.oneminstore.update(symbol, np.load(StringIO(data)))
        self.request.write_ok()

    def put_5minute(self, symbol, data, format='npy'):
        self.dbm.fiveminstore.update(symbol, np.load(StringIO(data)))
        self.request.write_ok()

    def put_day(self, symbol, data, format='npy'):
        func = getattr(self.dbm, "update_day")
        self._put(func, symbol, data, format)
        
    def _put(self, func, symbol, data, format):
        assert format == 'npy'
        
        start_time = time.time()

        try:
            data = np.load(StringIO(data))
        except StandardError:
            return self.request.write("-ERR wrong data format\r\n")
        
        end_time = time.time()
        parse_time = 1000.0 * (end_time - start_time)
        logging.info("proto parse: %.2fms", parse_time)
        
        if data != None:
            func(symbol, data)

        self.request.write("+OK\r\n")

    def finish(self):
        """Finishes this response, ending the HTTP request."""
        assert not self._finished
        self.request.finish()
        self._log()
        self._finished = True

    def _execute(self):
        conn = self.request.connection
        # Check if the user is authenticated
        if conn and conn.require_auth and not \
                conn.authenticated and \
                self.request.method != 'auth':
            self.request.write("-ERR operation not permitted\r\n")
            if not self._finished:
                self.finish()

        if self.request.method not in self.SUPPORTED_METHODS:
            logging.error("Unknown command %s" % self.request.method)
            self.request.write("-ERR UNKNOWN COMMAND\r\n")
            if not self._finished:
                self.finish()

        if not self._finished:
            arguments = self.request.args[1:] 
            getattr(self, self.request.method)(*arguments)
            if not self._finished:
                self.finish()

    def _log(self):
        self.request.record_stats()
        request_time = 1000.0 * self.request.request_time()
        logging.info("%s %.2fms", self._request_summary(), request_time)

    def _request_summary(self):
        return "%s %s" % (self.request.method, self.request.response_message)

########NEW FILE########
__FILENAME__ = helper
import datetime
import numpy
import os
import time

datadir ='/tmp/datafeed-%d' % int(time.time())
os.mkdir(datadir)

def sample_key():
    return 'SH000001'

def sample():
    dt = datetime.datetime.now()
    timestamp = int(time.time())

    d = {
        'SH000001' : {
            'amount': 84596203520.0,
            'close': 2856.9899999999998,
            'high': 2880.5599999999999,
            'low': 2851.9499999999998,
            'name': u'\u4e0a\u8bc1\u6307\u6570',
            'open': 2868.73,
            'preclose': 2875.8600000000001,
            'price': 2856.9899999999998,
            'symbol': u'SH000001',
            'time': str(dt),
            'timestamp': timestamp,
            'volume': 75147848.0
            }
        }
    return d

def sample_minutes():
    path = os.path.dirname(os.path.realpath(__file__))
    data = numpy.load(os.path.join(path, 'minute.npy'))

    today = datetime.datetime.today()
    for row in data:
        day = datetime.datetime.fromtimestamp(int(row['time']))
        t = time.mktime((today.year, today.month, today.day,
                         day.hour, day.minute, 0, 0, 0, 0))
        row['time'] = int(t)

    return data

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import unittest

TEST_MODULES = [
    'datafeed.tests.test_client',
    'datafeed.tests.test_datastore',
    'datafeed.tests.test_exchange',
    'datafeed.tests.test_imiguserver',
    'datafeed.tests.test_server',
]

def all():
    return unittest.defaultTestLoader.loadTestsFromNames(TEST_MODULES)

if __name__ == '__main__':
    import tornado.testing
    tornado.testing.main()

########NEW FILE########
__FILENAME__ = test_client
'''
@FIXME
======
due to client not async we need to start a real server in terminal to perform
this tests.
'''

from __future__ import with_statement

import marshal
import os
import sys
import time
import numpy
import socket
import unittest

import numpy as np

from cStringIO import StringIO

from datetime import datetime
from datafeed.client import Client

class ClientTest(unittest.TestCase):

    def setUp(self):
        self.client = Client()

        today = datetime.today()
        timestamp = int(time.mktime((today.year, today.month, today.day,
                                      10, 30, 0, 0, 0, 0)))
        dt = datetime.fromtimestamp(timestamp)
        
        d = {
            'SH000001' : {
                'amount': 84596203520.0,
                'close': 2856.9899999999998,
                'high': 2880.5599999999999,
                'low': 2851.9499999999998,
                'name': u'\u4e0a\u8bc1\u6307\u6570',
                'open': 2868.73,
                'preclose': 2875.8600000000001,
                'price': 2856.9899999999998,
                'symbol': u'SH000001',
                'time': str(dt),
                'timestamp': timestamp,
                'volume': 75147848.0
                }
            }
        self.client.put_reports(d)

    def test_connect(self):
        self.client.connect()
        self.assertTrue(isinstance(self.client._sock, socket._socketobject))

    def test_put_reports(self):
        path = os.path.dirname(os.path.realpath(__file__))
        r = self.client.get_report('SH000001')
        f = open(os.path.join(path, 'reports.dump'), 'r')
        data = marshal.load(f)
        for v in data.itervalues():
            if 'amount' not in v:
                continue
            v['time'] = r['time']
            v['timestamp'] = r['timestamp']

        ret = self.client.put_reports(data)
        self.assertEqual(ret, 'OK')

    def test_put_empty_reports(self):
        ret = self.client.put_reports({})
        self.assertEqual(ret, 'OK')

    def test_get_list(self):
        stocks = self.client.get_list()
        self.assertTrue(isinstance(stocks, dict))
        self.assertTrue('SH000001' in stocks)

    def test_get_report(self):
        quote = self.client.get_report('SH000001')
        self.assertTrue(isinstance(quote, dict))
        self.assertTrue(isinstance(quote['price'], float))

    def test_get_reports(self):
        stocks = self.client.get_reports('SH000001', 'KeyError')
        self.assertTrue(isinstance(stocks, dict))
        self.assertTrue('SH000001' in stocks)
        self.assertFalse('KeyError' in stocks)

    def test_put_then_get_minute(self):
        path = os.path.dirname(os.path.realpath(__file__))
        data = numpy.load(os.path.join(path, 'minute.npy'))

        symbol = 'SH999999'

        today = datetime.today()
        for row in data:
            day = datetime.fromtimestamp(int(row['time']))
            t = time.mktime((today.year, today.month, today.day,
                             day.hour, day.minute, 0, 0, 0, 0))
            
            row['time'] = int(t)

        self.client.put_minute(symbol, data)

        ret = self.client.get_minute(symbol, int(time.time()))
        self.assertEqual(data['price'].tolist(), ret['price'].tolist())


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_datastore
from __future__ import with_statement

import h5py
import os
import re
import time
import unittest

import numpy as np

from datetime import datetime

from mock import Mock, patch

from datafeed.exchange import SH
from datafeed.datastore import *
from datafeed.tests import helper


class ManagerTest(unittest.TestCase):

    def setUp(self):
        self.manager = Manager(helper.datadir, SH())

    def test_store_filename(self):
        ret = self.manager._store
        self.assertEqual(ret.filename, '%s/data.h5' % helper.datadir)
        self.assertTrue(isinstance(ret, h5py.File))

    def test_daystore(self):
        ret = self.manager.daystore
        self.assertTrue(isinstance(ret, Day))

    def test_not_inited_minutestore(self):
        ret = self.manager._minutestore
        self.assertEqual(ret, None)

    def test_init_manager_with_minute_store(self):
        self.manager.set_mtime(1291341180)
        self.assertTrue(isinstance(self.manager.minutestore, Minute))
        self.assertTrue(isinstance(self.manager.minutestore.handle, MinuteSnapshotCache))

    def test_minute_filename_market_not_open(self):
        # not open yet
        ts = 1291312380
        self.manager.set_mtime(ts)
        date = datetime.fromtimestamp(ts).date()
        self.assertEqual(date, self.manager.minutestore.date)
        self.assertEqual('/minsnap/20101203', self.manager.minutestore.pathname)
    
    def test_minute_filename_opened(self):
        # in session
        ts = 1291341180
        date = datetime.fromtimestamp(ts).date()
        self.manager.set_mtime(ts)
        self.assertEqual(date, self.manager.minutestore.date)
        self.assertEqual('/minsnap/20101203', self.manager.minutestore.pathname)
 
    def test_rotate_minute_store(self):
        dbm = self.manager
        dbm.set_mtime(1291341180)
        self.assertTrue(isinstance(dbm.minutestore.handle, MinuteSnapshotCache))

        dbm.set_mtime(1291341180 + 86400)
        dbm.rotate_minute_store()
        self.assertEqual('/minsnap/20101204', dbm.minutestore.pathname)

    def test_get_minutestore(self):
        store = self.manager.get_minutestore_at(1291341180)
        self.assertTrue(isinstance(store, Minute))
        self.assertEqual('/minsnap/20101203', store.pathname)

    def test_update_day_should_call_to_correctly_store(self):
        p1 = {'time': int(time.time())}
        data = [p1]
        store = Mock()

        self.manager.get_minutestore_at = Mock(return_value=store)
        self.manager.update_minute("SH000001", data)
        self.manager.get_minutestore_at.assert_called_with(p1['time'])
    
    def test_get_minutestore_force_cache(self):
        store = self.manager.get_minutestore_at(1291341180, memory=True)
        self.assertTrue(isinstance(store.handle, MinuteSnapshotCache))

    def test_get_minutestore_force_no_cache(self):
        ts = int(time.time())
        store = self.manager.get_minutestore_at(ts, memory=False)
        self.assertTrue(isinstance(store.handle, h5py.Group))

    def test_get_minutestore_default_cache(self):
        ts = int(time.time())
        store = self.manager.get_minutestore_at(ts)
        self.assertTrue(isinstance(store.handle, MinuteSnapshotCache))

    def test_5minstore(self):
        ret = self.manager.fiveminstore
        self.assertTrue(isinstance(ret, FiveMinute))


class DictStoreTest(unittest.TestCase):

    def test_init_store(self):
        filename = '%s/dstore_init.dump' % helper.datadir
        data = {'r1': 'v1'}
        ds = DictStore(filename, data)
        r1 = ds['r1']
        self.assertTrue(r1, 'v1')

    def test_reopen_file(self):
        filename = '%s/dstore_reopen.dump' % helper.datadir

        data = {'r1': 'v1'}
        ds = DictStore(filename, data)
        ds.close()

        ds = DictStore.open(filename)
        r1 = ds['r1']
        self.assertTrue(r1, 'v1')


class DictStoreNamespaceTest(unittest.TestCase):

    def setUp(self):
        class Impl(DictStoreNamespace):
            pass
        filename = '%s/dsn_impl.dump' % helper.datadir
        self.store = DictStore(filename, {})
        self.impl = Impl(self.store)

    def test_inited_impl(self):
        self.assertTrue(self.store.has_key('impl'))
        self.assertEqual(self.impl.keys(), [])

    def test_set_and_get_item(self):
        self.impl['k12'] = 'v21'
        self.assertEqual(self.impl['k12'], 'v21')

    def test_set_and_get_item2(self):
        self.impl['k12'] = 'v21'
        self.assertEqual(self.impl.get('k12'), 'v21')


class ReportTest(unittest.TestCase):

    def test_init_store(self):
        filename = '%s/dstore.dump' % helper.datadir
        store = DictStore.open(filename)
        rstore = Report(store)
        sample = helper.sample()

        rstore.update(sample)
        key = 'SH000001'
        self.assertEqual(rstore[key], sample[key])

        store.close()
        self.assertRaises(AssertionError, rstore.set, key, sample)
        self.assertRaises(AssertionError, rstore.get, key)

        store = DictStore.open(filename)
        rstore = Report(store)
        self.assertEqual(rstore[key], sample[key])


class DayTest(unittest.TestCase):

    def setUp(self):
        self.store = Day(h5py.File('%s/data.h5' % helper.datadir))

    def test_namespace(self):
        h = self.store.handle
        self.assertTrue(isinstance(h, h5py.Group))
        self.assertEqual(h.name, '/day')

    def test_get_from_not_exist_symbol(self):
        key = 'SH987654'
        self.assertRaises(KeyError, self.store.get, symbol=key, length=1)


class MinuteTest(unittest.TestCase):

    def setUp(self):
        ts = int(time.mktime((2011, 1, 1, 1, 1, 0, 0, 0, 0)))
        date = datetime.fromtimestamp(ts).date()
        self.store = Minute(h5py.File('%s/data.h5' % helper.datadir),
                            date,
                            SH().market_minutes)

    def test_namespace(self):
        h = self.store.handle
        self.assertTrue(isinstance(h, h5py.Group))
        self.assertEqual(h.name, '/minsnap/20110101')

    def test_get_from_not_exist_symbol(self):
        key = 'SH987654'
        self.assertRaises(KeyError, self.store.get, symbol=key)


class OneMinuteTest(unittest.TestCase):

    def setUp(self):
        self.store = OneMinute(h5py.File('%s/data.h5' % helper.datadir))

    def test_namespace(self):
        h = self.store.handle
        self.assertTrue(isinstance(h, h5py.Group))
        self.assertEqual(h.name, '/1min')

    def test_get_from_not_exist_symbol(self):
        key = 'SH987654'
        self.assertRaises(KeyError, self.store.get, symbol=key, date=datetime.today())

    def test_get_after_update(self):
        key = 'SH000001'
        date = datetime.fromtimestamp(1316588100)
        x = np.array([
                (1316588100, 3210.860107421875, 3215.239990234375, 3208.43994140625,
                 3212.919921875, 62756.0, 49122656.0),
                (1316588400, 3213.43994140625, 3214.47998046875, 3206.800048828125,
                 3206.840087890625, 81252.0, 55866096.0)
                ], dtype=FiveMinute.DTYPE)
        self.store.update(key, x)

        y = self.store.get(key, date)
        np.testing.assert_array_equal(y, x)

    def test_update_multi_days(self):
        key = 'SH000001'
        x = np.array([
                (1316501700, 3130.8701171875, 3137.739990234375, 3128.81005859375,
                 3132.580078125, 30530.0, 20179424.0),
                (1316502000, 3132.68994140625, 3142.75, 3129.8798828125,
                 3141.5400390625, 57703.0, 41456768.0),
                (1316588100, 3210.860107421875, 3215.239990234375, 3208.43994140625,
                 3212.919921875, 62756.0, 49122656.0),
                (1316588400, 3213.43994140625, 3214.47998046875, 3206.800048828125,
                 3206.840087890625, 81252.0, 55866096.0)
                ], dtype=FiveMinute.DTYPE)
        self.store.update(key, x)

        date = datetime.fromtimestamp(1316501700).date()
        y = self.store.get(key, date)
        np.testing.assert_array_equal(y, x[:2])

        date = datetime.fromtimestamp(1316588400).date()
        y = self.store.get(key, date)
        np.testing.assert_array_equal(y, x[2:])

    def test_update_partial_data(self):
        market_minutes = 60 * 24 # assume 1min data
        store = OneMinute(h5py.File('%s/data.h5' % helper.datadir),
                          market_minutes)
        self.assertEqual(store.time_interval, 60)
        self.assertEqual(store.shape_x, 1440)

        key = '999'
        path = os.path.dirname(os.path.realpath(__file__))
        data = np.load(os.path.join(path, '001.npy'))

        store.update(key, data)

        date = datetime.fromtimestamp(1397621820).date()
        y = store.get(key, date)
        row1, row2 = y[737], y[1036]
        np.testing.assert_array_equal(row1, data[0])
        np.testing.assert_array_equal(row2, data[-1])


class FiveMinuteTest(unittest.TestCase):

    def setUp(self):
        self.store = FiveMinute(h5py.File('%s/data.h5' % helper.datadir))

    def test_namespace(self):
        h = self.store.handle
        self.assertTrue(isinstance(h, h5py.Group))
        self.assertEqual(h.name, '/5min')

    def test_get_from_not_exist_symbol(self):
        key = 'SH987654'
        self.assertRaises(KeyError, self.store.get, symbol=key, date=datetime.today())

    def test_get_after_update(self):
        key = 'SH000001'
        date = datetime.fromtimestamp(1316588100)
        x = np.array([
                (1316588100, 3210.860107421875, 3215.239990234375, 3208.43994140625,
                 3212.919921875, 62756.0, 49122656.0),
                (1316588400, 3213.43994140625, 3214.47998046875, 3206.800048828125,
                 3206.840087890625, 81252.0, 55866096.0)
                ], dtype=FiveMinute.DTYPE)
        self.store.update(key, x)

        y = self.store.get(key, date)
        np.testing.assert_array_equal(y, x)

    def test_update_multi_days(self):
        key = 'SH000001'
        x = np.array([
                (1316501700, 3130.8701171875, 3137.739990234375, 3128.81005859375,
                 3132.580078125, 30530.0, 20179424.0),
                (1316502000, 3132.68994140625, 3142.75, 3129.8798828125,
                 3141.5400390625, 57703.0, 41456768.0),
                (1316588100, 3210.860107421875, 3215.239990234375, 3208.43994140625,
                 3212.919921875, 62756.0, 49122656.0),
                (1316588400, 3213.43994140625, 3214.47998046875, 3206.800048828125,
                 3206.840087890625, 81252.0, 55866096.0)
                ], dtype=FiveMinute.DTYPE)
        self.store.update(key, x)

        date = datetime.fromtimestamp(1316501700).date()
        y = self.store.get(key, date)
        np.testing.assert_array_equal(y, x[:2])

        date = datetime.fromtimestamp(1316588400).date()
        y = self.store.get(key, date)
        np.testing.assert_array_equal(y, x[2:])

    def test_update_multi_partial_days_data(self):
        market_minutes = 1440 # 5min data
        store = FiveMinute(h5py.File('%s/data.h5' % helper.datadir),
                           market_minutes)
        self.assertEqual(store.time_interval, 300)
        self.assertEqual(store.shape_x, 288)

        key = '9991'
        path = os.path.dirname(os.path.realpath(__file__))
        data = np.load(os.path.join(path, '005.npy'))

        store.update(key, data)

        date = datetime.fromtimestamp(data[0]['time']).date()
        y1 = store.get(key, date)
        np.testing.assert_array_equal(y1[196], data[0])

        date = datetime.fromtimestamp(data[-1]['time']).date()
        y2 = store.get(key, date)
        np.testing.assert_array_equal(y2[206], data[-1])

    def test_update_multi_hold_data(self):
        market_minutes = 1440 # 5min data
        store = FiveMinute(h5py.File('%s/data.h5' % helper.datadir),
                           market_minutes)
        key = '9992'
        path = os.path.dirname(os.path.realpath(__file__))
        data = np.load(os.path.join(path, '005_na.npy'))

        store.update(key, data)

        date = datetime.fromtimestamp(data[-1]['time']).date()
        y2 = store.get(key, date)

        # Data has holes between index 171 and index 172.
        np.testing.assert_array_equal(y2[0], data[132])
        np.testing.assert_array_equal(y2[167], data[-1])
        np.testing.assert_array_equal(y2[39], data[171])
        np.testing.assert_array_equal(y2[43], data[172])


class MinuteSnapshotCacheTest(unittest.TestCase):

    def setUp(self):
        self.filename = '%s/dstore_mincache.dump' % helper.datadir
        self.date = datetime.today().date()
        self.store = DictStore.open(self.filename)
        self.mstore = MinuteSnapshotCache(self.store, self.date)

    def test_inited_date(self):
        self.assertEqual(self.mstore.date, datetime.today().date())

    def test_true_of_store(self):
        ms = Minute(self.mstore, datetime.today().date(), SH().market_minutes)
        self.assertTrue(ms)

    def test_set_get(self):
        x = helper.sample_minutes()

        symbol = 'TS123456'
        self.mstore[symbol] = x
        y = self.mstore[symbol]
        np.testing.assert_array_equal(y, x)

    def test_reopen(self):
        x = helper.sample_minutes()

        symbol = 'TS123456'
        self.mstore[symbol] = x

        # closed
        self.store.close()
        self.assertRaises(AssertionError, self.mstore.get, symbol)

        # reopen
        store = DictStore.open(self.filename)
        mstore = MinuteSnapshotCache(store, self.date)

        # testing reopen data
        y = mstore[symbol]
        np.testing.assert_array_equal(y, x)

    def test_rotate(self):
        x = helper.sample_minutes()

        symbol = 'TS123456'
        self.mstore[symbol] = x

        dbm = Manager(helper.datadir, SH())
        tostore = dbm._minutestore_at(self.date, memory=False)

        # rewrite
        self.mstore.rotate(tostore)

        # cache cleaned after rotate
        self.assertRaises(KeyError, self.mstore.get, symbol)

        # testing persistent data
        y = tostore[symbol]
        np.testing.assert_array_equal(y, x)

        # reopen
        mstore = MinuteSnapshotCache(self.store, self.date)

        # testing reopen data
        self.assertRaises(KeyError, mstore.get, symbol)


if __name__ == '__main__':
    unittest.main()
    import shutil
    shutil.rmtree(helper.datadir)

########NEW FILE########
__FILENAME__ = test_dividend
from __future__ import with_statement

import unittest

import datetime
import numpy as np
import time

from pandas import DataFrame, lib
from pandas import TimeSeries

from datafeed.datastore import Day
from datafeed.dividend import Dividend, adjust


def date2unixtime(date):
    return int(time.mktime(date.timetuple()))


class DividendTest(unittest.TestCase):
    dtype = [('time', '<i4'),
             ('split', '<f4'),
             ('purchase', '<f4'),
             ('purchase_price', '<f4'),
             ('dividend', '<f4')]

    def floatEqual(self, x, y):
        if (x - y) < 0.05:
            return True
        else:
            return False

    def test_adjust_divide_or_split(self):
        #http://help.yahoo.com/kb/index?locale=en_US&page=content&y=PROD_FIN&id=SLN2311

        ohlcs = np.array([
                (date2unixtime(datetime.date(2003, 2, 13)),
                 46.99, 46.99, 46.99, 46.99, 675114.0, 758148608.0),
                (date2unixtime(datetime.date(2003, 2, 14)),
                 48.30, 48.30, 48.30, 48.30, 675114.0, 758148608.0),
                (date2unixtime(datetime.date(2003, 2, 18)),
                 24.96, 24.96, 24.96, 24.96, 675114.0, 758148608.0),
                (date2unixtime(datetime.date(2003, 2, 19)),
                 24.53, 24.53, 24.53, 24.53, 675114.0, 758148608.0),
                ], dtype=Day.DTYPE)

        dividends = np.array([
                (date2unixtime(datetime.date(2003, 2, 18)),
                 1.0, 0.0, 0.0, 0.0), # Split 2:1
                (date2unixtime(datetime.date(2003, 2, 19)),
                 0.0, 0.0, 0.0, 0.08), # 0.08 cash dividend
                ], dtype=self.dtype)


        index = np.array([datetime.datetime.fromtimestamp(v) for v in ohlcs['time']],
                         dtype=object)
        y = DataFrame.from_records(ohlcs, index=index, exclude=['time'])
        y['adjclose'] = y['close']

        for div in dividends:
            d = Dividend(div)
            d.adjust(y)

        adjclose = y.xs(datetime.datetime(2003, 2, 13))['adjclose']
        self.assertTrue(self.floatEqual(adjclose, 23.42))

        adjclose = y.xs(datetime.datetime(2003, 2, 14))['adjclose']
        self.assertTrue(self.floatEqual(adjclose, 24.07))
        
        adjclose = y.xs(datetime.datetime(2003, 2, 18))['adjclose']
        self.assertTrue(self.floatEqual(adjclose, 24.88))
        
        adjclose = y.xs(datetime.datetime(2003, 2, 19))['adjclose']
        self.assertTrue(self.floatEqual(adjclose, 24.53))

    def test_adjust_divide_and_split(self):
        ohlcs = np.array([
            (1277222400, 20.739999771118164, 21.139999389648438, 20.68000030517578,
             20.860000610351562, 506320.0, 1058136640.0),
            (1277308800, 13.5, 13.880000114440918, 13.5,
             13.609999656677246, 372504.0, 509364896.0),
            (1277740800, 12.869999885559082, 12.970000267028809, 12.0,
             12.010000228881836, 785225.0, 971340736.0)
        ], dtype=Day.DTYPE)

        dividends = np.array([
                (1062028800, 0.0, 0.0, 0.0, 0.003700000001117587),
                (1086912000, 0.0, 0.0, 0.0, 0.10999999940395355),
                (1121385600, 0.0, 0.0, 0.0, 0.05000000074505806),
                (1151971200, 0.0, 0.0, 0.0, 0.11999999731779099),
                (1179705600, 0.0, 0.0, 0.0, 0.20000000298023224),
                (1208995200, 1.0, 0.0, 0.0, 0.5),
                (1244678400, 0.0, 0.0, 0.0, 0.5),
                (1277337600, 0.5, 0.0, 0.0, 0.5),
                (1308182400, 0.0, 0.0, 0.0, 0.5)                
                ], dtype=self.dtype)

        index = np.array([datetime.datetime.fromtimestamp(v) for v in ohlcs['time']],
                         dtype=object)
        y = DataFrame.from_records(ohlcs, index=index, exclude=['time'])
        y['adjclose'] = y['close']

        for div in dividends:
            d = Dividend(div)
            d.adjust(y)

        adjclose = y.xs(datetime.datetime(2010, 6, 29))['adjclose']
        self.assertTrue(self.floatEqual(adjclose, 11.51))

        adjclose = y.xs(datetime.datetime(2010, 6, 24))['adjclose']
        self.assertTrue(self.floatEqual(adjclose, 13.11))

        adjclose = y.xs(datetime.datetime(2010, 6, 24))['adjclose']
        self.assertTrue(self.floatEqual(adjclose, 13.07))

    def test_adjust_purchase(self):
        ohlcs = np.array([
                (1216915200, 24.889999389648438, 25.450000762939453,
                 24.709999084472656, 25.0, 486284.0, 1216462208.0)
                ], dtype=Day.DTYPE)

        dividends = np.array([
                (1058313600, 0.0, 0.0, 0.0, 0.11999999731779099),
                (1084233600, 0.20000000298023224, 0.0, 0.0, 0.09200000017881393),
                (1119225600, 0.5, 0.0, 0.0, 0.10999999940395355),
                (1140739200, 0.08589000254869461, 0.0, 0.0, 0.0),
                (1150416000, 0.0, 0.0, 0.0, 0.07999999821186066),
                (1158796800, 0.0, 0.0, 0.0, 0.18000000715255737),
                (1183507200, 0.0, 0.0, 0.0, 0.11999999731779099),
                (1217203200, 0.0, 0.0, 0.0, 0.2800000011920929),
                (1246579200, 0.30000001192092896, 0.0, 0.0, 0.10000000149011612),
                (1268611200, 0.0, 0.12999999523162842, 8.850000381469727, 0.0),
                (1277942400, 0.0, 0.0, 0.0, 0.20999999344348907),
                (1307664000, 0.0, 0.0, 0.0, 0.28999999165534973)                
                ], dtype=self.dtype)

        index = np.array([datetime.datetime.fromtimestamp(v) for v in ohlcs['time']],
                         dtype=object)
        y = DataFrame.from_records(ohlcs, index=index, exclude=['time'])
        y['adjclose'] = y['close']

        for div in dividends:
            d = Dividend(div)
            d.adjust(y)

        adjclose = y.xs(datetime.datetime(2008, 7, 25))['adjclose']
        self.assertTrue(self.floatEqual(adjclose, 17.28))


    def test_adjust_func(self):
        """Fix for pandas 0.8 release which upgrade datetime
        handling.
        """
        ohlcs = np.array([
                (date2unixtime(datetime.date(2003, 2, 13)),
                 46.99, 46.99, 46.99, 46.99, 675114.0, 758148608.0),
                (date2unixtime(datetime.date(2003, 2, 14)),
                 48.30, 48.30, 48.30, 48.30, 675114.0, 758148608.0),
                (date2unixtime(datetime.date(2003, 2, 18)),
                 24.96, 24.96, 24.96, 24.96, 675114.0, 758148608.0),
                (date2unixtime(datetime.date(2003, 2, 19)),
                 24.53, 24.53, 24.53, 24.53, 675114.0, 758148608.0),
                ], dtype=Day.DTYPE)

        dividends = np.array([
                (date2unixtime(datetime.date(2003, 2, 18)),
                 1.0, 0.0, 0.0, 0.0), # Split 2:1
                (date2unixtime(datetime.date(2003, 2, 19)),
                 0.0, 0.0, 0.0, 0.08), # 0.08 cash dividend
                ], dtype=self.dtype)


        frame = adjust(ohlcs, dividends)
        self.assertEqual(frame.index[0].date(), datetime.date(2003, 2, 13))

        expected = ['open', 'high', 'low', 'close',
                    'volume', 'amount', 'adjclose']
        self.assert_(np.array_equal(frame.columns, expected))

        day = frame.ix[datetime.datetime(2003, 2, 13)]
        self.assertTrue(self.floatEqual(day['adjclose'], 23.415))

        expected = ['Open', 'High', 'Low', 'Close',
                    'Volume', 'Adjusted']
        frame = adjust(ohlcs, [], capitalize=True)
        self.assert_(np.array_equal(frame.columns, expected))

    def test_adjust_func_should_not_skipped(self):
        y = np.array([
            (1326643200, 22.50, 22.91, 20.65, 20.71, 4551.0, 9873878.0),
            (1326729600, 21.75, 22.78, 21.40, 22.78, 6053.0, 13547097.0),
            (1326816000, 23.90, 24.77, 22.0, 22.5, 11126.0, 26537980.0),
            (1326902400, 22.5, 23.98, 22.05, 23.55, 5983.0, 13886342.0),
            (1326988800, 23.56, 23.90, 23.35, 23.70, 3832.0, 9089978.0)
          ], dtype=Day.DTYPE)

        dividends = np.array([
            (1369008000, 0.5, 0.0, 0.0, 0.15),
            (1340064000, 1.0, 0.0, 0.0, 0.20)
        ], dtype=self.dtype)

        frame = adjust(y, dividends)

        day = frame.ix[datetime.datetime(2012, 1, 20)]
        self.assertTrue(self.floatEqual(day['close'], 7.75))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_exchange
from __future__ import with_statement

import unittest

from datetime import datetime
from datafeed.exchange import *

class ExchangeTest(unittest.TestCase):

    def test_NYSE(self):
        nyse = NYSE()
        self.assertEqual(str(nyse), 'NYSE')

    def test_singleton(self):
        lon_1 = LON()
        lon_2 = LON()
        self.assertEqual(lon_1, lon_2)

    def test_security(self):
        stock = Security(SH(), '600123')
        self.assertEqual('SH:600123', str(stock))

    def test_security_init_from_abbr(self):
        stock = Security.from_abbr('SH', '600123')
        self.assertEqual('SH:600123', str(stock))

    def test_shanghai_exchange_pre_open_time(self):
        today = datetime.today()
        sh = SH()
        pre_open_time = SH.pre_open_time(day=today)
        ret = datetime.fromtimestamp(pre_open_time)
        self.assertEqual(ret.hour, 9)
        self.assertEqual(ret.minute, 15)

    def test_shanghai_exchange_open_time(self):
        today = datetime.today()
        sh = SH()
        open_time = SH.open_time(day=today)
        ret = datetime.fromtimestamp(open_time)
        self.assertEqual(ret.hour, 9)
        self.assertEqual(ret.minute, 30)

    def test_shanghai_exchange_open_time(self):
        today = datetime.today()
        sh = SH()
        break_time = SH.break_time(day=today)
        ret = datetime.fromtimestamp(break_time)
        self.assertEqual(ret.hour, 11)
        self.assertEqual(ret.minute, 30)

    def test_shanghai_exchange_open_time(self):
        today = datetime.today()
        sh = SH()
        close_time = SZ.close_time(day=today)
        ret = datetime.fromtimestamp(close_time)
        self.assertEqual(ret.hour, 15)
        self.assertEqual(ret.minute, 0)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_imiguserver
from __future__ import with_statement

import datetime
import re
import time
import unittest

from datafeed.exchange import SH
from datafeed.imiguserver import ImiguApplication, ImiguHandler, SnapshotIndexError
from datafeed.server import Request
from datafeed.tests import helper

from mock import Mock, patch


class ImiguApplicationTest(unittest.TestCase):

    def setUp(self):
        self.application = ImiguApplication(helper.datadir, SH())
        self.application.dbm._mtime = 1291167000
        self.open_time = 1291167000
        self.close_time = 1291186800

        key = helper.sample_key()
        sample = helper.sample()
        sample[key]['timestamp'] = 1291167000
        self.application.dbm.reportstore.update(sample)


    @patch.object(time, 'time')
    def test_archive_day_09_29(self, mock_time):
        mock_time.return_value = self.open_time - 1 # not open

        today = datetime.datetime.today()
        ret = self.application.scheduled_archive_day(today)
        self.assertFalse(ret)

    @patch.object(time, 'time')
    def test_archive_day_15_05_no_data(self, mock_time):
        mock_time.return_value = self.close_time + 300
        
        self.application.dbm._mtime = self.close_time - 86400

        today = datetime.datetime.today()
        ret = self.application.scheduled_archive_day(today)
        self.assertFalse(ret)

    @patch.object(time, 'time')
    def test_archive_day_15_05_01(self, mock_time):
        mock_time.return_value = self.close_time + 181 # closed more than 3 minutes

        self.application.dbm._mtime = self.close_time + 180 + 1

        today = datetime.datetime.today()
        ret = self.application.scheduled_archive_day(today)
        self.assertTrue(ret)

    @patch.object(time, 'time')
    def test_archive_day_15_05_01_archived_before(self, mock_time):
        mock_time.return_value = self.close_time + 181 # closed more than 3 minutes

        self.application.archive_day_time = self.close_time + 180

        today = datetime.datetime.today()
        ret = self.application.scheduled_archive_day(today)
        self.assertFalse(ret)

    @patch.object(time, 'time')
    def test_archive_minute_09_29(self, mock_time):
        mock_time.return_value = self.open_time - 1 # before open

        today = datetime.datetime.today()
        ret = self.application.scheduled_archive_minute(today)
        self.assertFalse(ret)

    @patch.object(time, 'time')
    def test_archive_minute_09_30(self, mock_time):
        mock_time.return_value = self.open_time

        today = datetime.datetime.today()
        ret = self.application.scheduled_archive_minute(today)
        self.assertTrue(ret)

    @patch.object(time, 'time')
    def test_archive_minute_14_30(self, mock_time):
        mock_time.return_value = self.close_time - 1800 # in session

        today = datetime.datetime.today()
        ret = self.application.scheduled_archive_minute(today)
        self.assertTrue(ret)

    @patch.object(time, 'time')
    def test_archive_minute_14_30_05_if_not_archived(self, mock_time):
        mock_time.return_value = self.close_time - 1795 # in session

        self.application.archive_minute_time = self.close_time - 1860

        today = datetime.datetime.today()
        ret = self.application.scheduled_archive_minute(today)
        self.assertTrue(ret)

    @patch.object(time, 'time')
    def test_archive_minute_14_30_05_if_archived(self, mock_time):
        mock_time.return_value = self.close_time - 1795 # in session

        self.application.archive_minute_time = self.close_time - 1800

        today = datetime.datetime.today()
        ret = self.application.scheduled_archive_minute(today)
        self.assertFalse(ret)

    @patch.object(time, 'time')
    def test_archive_minute_15_00(self, mock_time):
        mock_time.return_value = self.close_time

        today = datetime.datetime.today()
        ret = self.application.scheduled_archive_minute(today)
        self.assertTrue(ret)

    @patch.object(time, 'time')
    def test_archive_minute_15_03(self, mock_time):
        mock_time.return_value = self.close_time + 180

        today = datetime.datetime.today()
        ret = self.application.scheduled_archive_minute(today)
        self.assertTrue(ret)

    @patch.object(time, 'time')
    def test_archive_minute_15_05_01(self, mock_time): 
        mock_time.return_value = self.close_time + 300 + 1 # closed

        today = datetime.datetime.today()
        ret = self.application.scheduled_archive_minute(today)
        self.assertFalse(ret)

    @patch.object(time, 'time')
    def test_crontab_08_00_00(self, mock_time): 
        mock_time.return_value = self.open_time - 3600 - 1800

        today = datetime.datetime.fromtimestamp(time.time())
        ret = self.application.scheduled_crontab_daily(today)
        self.assertTrue(ret)

    @patch.object(time, 'time')
    def test_crontab_08_00_01_if_not_running(self, mock_time): 
        mock_time.return_value = self.open_time - 3600 - 1799

        self.application.crontab_time = self.open_time - 86400 - 7200
        today = datetime.datetime.fromtimestamp(time.time())
        ret = self.application.scheduled_crontab_daily(today)
        self.assertTrue(ret)

    @patch.object(time, 'time')
    def test_crontab_09_30(self, mock_time): 
        mock_time.return_value = self.open_time

        today = datetime.datetime.fromtimestamp(time.time())
        ret = self.application.scheduled_crontab_daily(today)
        self.assertFalse(ret)

    def test_archive_day(self):
        r = {
            'amount': 84596203520.0,
            'close': 2856.9899999999998,
            'high': 2880.5599999999999,
            'low': 2851.9499999999998,
            'name': u'\u4e0a\u8bc1\u6307\u6570',
            'open': 2868.73,
            'preclose': 2875.8600000000001,
            'price': 2856.9899999999998,
            'symbol': 'SH000001',
            'volume': 75147848.0
            }
        
        day = datetime.datetime.today()
        ts = time.mktime((day.year, day.month, day.day,
                          15, 0, 0, 0, 0, 0))
        day_ts = time.mktime((day.year, day.month, day.day,
                              0, 0, 0, 0, 0, 0))
        r['timestamp'] = ts
        r['time'] = str(datetime.datetime.fromtimestamp(ts))

        data = {'SH000001': r}

        import zlib
        import marshal
        data = zlib.compress(marshal.dumps(data))
        
        request = Request(None, 'put_reports', data)
        self.application(request)

        request = Request(None, 'archive_day')
        self.application(request)
        
        y = self.application.dbm.daystore.get('SH000001', 1)
        self.assertEqual(y[0]['time'], day_ts)
        self.assertTrue((y[0]['open'] - 2868.73) < 0.1 ** 6)

    @patch.object(ImiguHandler, 'get_snapshot_index')
    def test_fix_report_when_archive(self, mock_index):
        # set to after hours: 15:30 implicates error data
        # some datafeed still sending data even market was closed.
        day = datetime.datetime.today()
        ts = time.mktime((day.year, day.month, day.day,
                          15, 30, 0, 0, 0, 0))
        mock_index.return_value = (ts, 360)
        
        r = {
            'amount': 84596203520.0,
            'close': 2856.9899999999998,
            'high': 2880.5599999999999,
            'low': 2851.9499999999998,
            'name': u'\u4e0a\u8bc1\u6307\u6570',
            'open': 2868.73,
            'preclose': 2875.8600000000001,
            'price': 2856.9899999999998,
            'symbol': 'SH000001',
            'time': '2010-12-08 14:02:57',
            'timestamp': 1291788177,
            'volume': 75147848.0
            }
        

        r['timestamp'] = ts
        r['time'] = str(datetime.datetime.fromtimestamp(ts))

        data = {'SH000001': r}

        import zlib
        import marshal
        data = zlib.compress(marshal.dumps(data))
        
        request = Request(None, 'put_reports', data)
        self.application(request)

        close_time = time.mktime((day.year, day.month, day.day,
                                  15, 0, 0, 0, 0, 0))
        
        request = Request(None, 'archive_minute', data)
        self.application(request)
        
        r = self.application.dbm.get_report('SH000001')
        self.assertEqual(r['timestamp'], close_time)
        self.assertEqual(r['open'], 2868.73)

    @patch.object(ImiguHandler, 'get_snapshot_index')
    def test_archive_minute_at_open_time(self, mock_index):
        # set data time to pre-market(centralized competitive pricing)
        day = datetime.datetime.today()
        t1 = time.mktime((day.year, day.month, day.day,
                          9, 26, 0, 0, 0, 0))
        open_time = time.mktime((day.year, day.month, day.day,
                                 9, 30, 0, 0, 0, 0))
        mock_index.return_value = (open_time, 0)
        
        r = {
            'amount': 10000.0,
            'close': 0.0,
            'high': 3000.0,
            'low': 3000.0,
            'name': u'\u4e0a\u8bc1\u6307\u6570',
            'open': 3000.0,
            'preclose': 2875.0,
            'price': 3000.0,
            'symbol': 'SH000001',
            'volume': 900000.0
            }
        
        r['timestamp'] = t1
        r['time'] = str(datetime.datetime.fromtimestamp(t1))

        data = {'SH000001': r}

        import zlib
        import marshal
        data = zlib.compress(marshal.dumps(data))
        
        request = Request(None, 'put_reports', data)
        self.application(request)

        self.assertEqual(self.application.dbm.mtime, t1)
        
        request = Request(None, 'archive_minute')
        self.application(request)
        
        y = self.application.dbm.minutestore.get('SH000001')
        self.assertEqual(y[0]['time'], open_time)
        self.assertEqual(y[0]['price'], 3000.0)

    @patch.object(ImiguHandler, 'get_snapshot_index')
    def test_archive_minute_raise_at_wrong_index(self, mock_index):
        # set data time to pre-market(centralized competitive pricing)
        day = datetime.datetime.today()
        t1 = time.mktime((day.year, day.month, day.day,
                          9, 26, 0, 0, 0, 0))
        mock_index.return_value = (t1, -4)

        request = Request(None, 'archive_minute')
        self.assertRaises(SnapshotIndexError,
                          self.application,
                          request)

    @patch.object(time, 'time')
    def test_get_snapshot_index(self, mock_time):
        mock_time.return_value = 1309829400
        report_time = 1309829160

        mintime, index = ImiguHandler.get_snapshot_index(1309829400, report_time)

        self.assertEqual(mintime, 1309829400)
        self.assertEqual(index, 0)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_server
from __future__ import with_statement

import re
import time
import unittest

from datafeed.client import Client
from datafeed.server import Server, Application, Request, Handler

from mock import Mock, patch


class HandlerTest(unittest.TestCase):
    pass

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010 yinhm

import datetime
import json

import numpy as np

from json import encoder
encoder.FLOAT_REPR = lambda f: format(f, '.2f')


__all__ = ['print2f', 'json_encode', 'json_decode']


class print2f(float):
    def __repr__(self):
        return "%0.2f" % self


def json_encode(value):
    """JSON-encodes the given Python object."""
    # JSON permits but does not require forward slashes to be escaped.
    # This is useful when json data is emitted in a <script> tag
    # in HTML, as it prevents </script> tags from prematurely terminating
    # the javscript.  Some json libraries do this escaping by default,
    # although python's standard library does not, so we do it here.
    # http://stackoverflow.com/questions/1580647/json-why-are-forward-slashes-escaped
    return json.dumps(value).replace("</", "<\\/")


def json_decode(value):
    """Returns Python objects for the given JSON string."""
    return json.loads(value)

########NEW FILE########
__FILENAME__ = adjust
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2011 yinhm
import datetime
import os
import sys

import numpy as np


ROOT_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), '..')
sys.path[0:0] = [ROOT_PATH]

from cStringIO import StringIO
from pandas import DataFrame

from datafeed.client import Client
from  datafeed.dividend import Dividend

client = Client()
symbol = 'SH600036'

y = client.get_day(symbol, 1000)
dividends = client.get_dividend(symbol)

index = np.array([datetime.date.fromtimestamp(v) for v in y['time']],
                 dtype=object)
y = DataFrame.from_records(y, index=index, exclude=['time'])

print dividends

for div in dividends:
    d = Dividend(div)
    d.adjust(y)

day = '20080725'
print datetime.datetime.fromtimestamp(client.get_day(symbol, day)['time'])

d1 = client.get_day(symbol, day)
print d1


########NEW FILE########
__FILENAME__ = bench
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010 yinhm

'''A datafeed server daemon.
'''

import datetime
import logging
import marshal
import os
import sys
import time
import tornado

from tornado import ioloop
from tornado.options import define, options


sys.path[0:0] = ['..']


from datafeed.exchange import SH
from datafeed.imiguserver import ImiguApplication
from datafeed.server import Server, Request


tornado.options.parse_command_line()
app = ImiguApplication('/tmp/df', SH())


today = datetime.datetime.today()
timestamp = int(time.mktime((today.year, today.month, today.day,
                             15, 0, 0, 0, 0, 0)))
dt = datetime.datetime.fromtimestamp(timestamp)
        
d = {
    'SH000001' : {
        'amount': 84596203520.0,
        'close': 2856.9899999999998,
        'high': 2880.5599999999999,
        'low': 2851.9499999999998,
        'name': u'\u4e0a\u8bc1\u6307\u6570',
        'open': 2868.73,
        'preclose': 2875.8600000000001,
        'price': 2856.9899999999998,
        'symbol': u'SH000001',
        'time': str(dt),
        'timestamp': timestamp,
        'volume': 75147848.0
        }
    }

app.dbm.update_reports(d)

path = os.path.dirname(os.path.realpath(__file__))
f = open(path + '/../datafeed/tests/reports.dump', 'r')
data = marshal.load(f)
for v in data.itervalues():
    if 'amount' not in v:
        continue
    v['time'] = str(dt)
    v['timestamp'] = timestamp
app.dbm.update_reports(data)

request = Request(None, 'archive_minute')
app(request)
    

def main():
    request = Request(None, 'archive_minute')
    app(request)

if __name__ == "__main__":
    import cProfile
    cProfile.run('main()', '/tmp/fooprof')

########NEW FILE########
__FILENAME__ = bench_dataset
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2011 yinhm
import datetime
import h5py
import os
import random
import sys
import time
import timeit

import numpy as np

DTYPE = np.dtype({'names': ('time', 'price', 'volume', 'amount'),
                  'formats': ('i4', 'f4', 'f4', 'f4')})


def bench_ds():
    filename = '/tmp/bench-%d.h5' % int(time.time())

    symbols = ["SH%.6d" % i for i in xrange(10000)]

    f = h5py.File(filename)
    for symbol in symbols:
        f.create_dataset(symbol, (240, ), DTYPE)
    f.close()
    
    for x in xrange(10):
        # open for bench again
        f = h5py.File(filename)
        random.shuffle(symbols)
        for symbol in symbols:
            ds = f[symbol]
        f.close()
    

def require_dataset(handle, symbol):
    gid = symbol[:3]
    group = handle.require_group(gid)
    try:
        ds = group[symbol]
    except KeyError:
        ds = group.create_dataset(symbol, (240, ), DTYPE)
    return ds

def dataset(handle, symbol):
    path = "%s/%s" % (symbol[:3], symbol)
    return handle[path]


def bench_grouped_ds():
    filename = '/tmp/bench-%d.h5' % int(time.time())

    symbols = ["SH%.6d" % i for i in xrange(10000)]

    f = h5py.File(filename)
    for symbol in symbols:
        require_dataset(f, symbol)
    f.close()

    for x in xrange(10):
        # open for bench again
        f = h5py.File(filename)
        random.shuffle(symbols)
        for symbol in symbols:
            ds = dataset(f, symbol)
        f.close()


if __name__ == '__main__':
    d = 1
    
    ds_timer = timeit.Timer(stmt='bench_ds()',
                            setup="from __main__ import bench_ds")
    ds_result = ds_timer.timeit(number=d)
    print ds_result

    grouped_ds_timer = timeit.Timer(stmt='bench_grouped_ds()',
                                    setup="from __main__ import bench_grouped_ds")
    grouped_ds_result = grouped_ds_timer.timeit(number=d)
    print grouped_ds_result

########NEW FILE########
__FILENAME__ = bench_dump
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2011 yinhm
import datetime
import h5py
import os
import shelve
import sys
import timeit

import cPickle as pickle
import numpy as np

ROOT_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), '..')
sys.path[0:0] = [ROOT_PATH]

from cStringIO import StringIO
from datafeed.client import Client
from datafeed.datastore import *
from datafeed.exchange import *
from datafeed.providers.dzh import *

var_path = os.path.join(ROOT_PATH, 'var')
store = Manager('/tmp/df', SH())
filename = os.path.join(var_path, "20101202.h5")
date = datetime.datetime.strptime('20101202', '%Y%m%d').date()

hdf_store = h5py.File(filename)
f1 = NumpyFile(hdf_store, date, SH().market_minutes)
f2 = shelve.open('/tmp/dump.shelve')

def f1_bench_read():
    for k, v in hdf_store.iteritems():
        if isinstance(v, h5py.Group):
            continue
        f1[str(k)] = v[:]

def f1_bench_dump():
    pickle.dump(f1, open('/tmp/dump.pickle', 'wb'), -1)


def f2_bench_read():
    for k, v in hdf_store.iteritems():
        if isinstance(v, h5py.Group):
            continue
        f2[str(k)] = v[:]

def f2_bench_dump():
    f2.close()


if __name__ == '__main__':
    d = 1

    timer = timeit.Timer(stmt='f1_bench_read()',
                         setup="from __main__ import f1_bench_read")
    result = timer.timeit(number=d)
    print result

    timer = timeit.Timer(stmt='f1_bench_dump()',
                         setup="from __main__ import f1_bench_dump")
    result = timer.timeit(number=d)
    print result

    timer = timeit.Timer(stmt='f2_bench_read()',
                         setup="from __main__ import f2_bench_read")
    result = timer.timeit(number=d)
    print result

    timer = timeit.Timer(stmt='f2_bench_dump()',
                         setup="from __main__ import f2_bench_dump")
    result = timer.timeit(number=d)
    print result


########NEW FILE########
__FILENAME__ = dzh
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2011 yinhm
import datetime
import os
import sys

import numpy as np

ROOT_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), '..')
sys.path[0:0] = [ROOT_PATH]

from cStringIO import StringIO
from datafeed.client import Client
from datafeed.datastore import Manager
from datafeed.exchange import *
from datafeed.providers.dzh import *

var_path = os.path.join(ROOT_PATH, 'var')

client = Client()
store = Manager('/tmp/df', SH())

filename = os.path.join(var_path, "dzh/sh/MIN1.DAT")
io = DzhMinute()
for symbol, ohlcs in io.read(filename, 'SH'):
    client.put_minute(symbol, ohlcs)

filename = os.path.join(var_path, "dzh/sh/MIN1.DAT")
io = DzhMinute()
for symbol, ohlcs in io.read(filename, 'SH'):
    for ohlc in ohlcs:
        ohlc['time'] = ohlc['time'] - 8 * 3600
    print symbol
    #client.put_1minute(symbol, ohlcs)
    store.oneminstore.update(symbol, ohlcs)


filename = os.path.join(var_path, "dzh/sh/MIN.DAT")
io = DzhFiveMinute()
for symbol, ohlcs in io.read(filename, 'SH'):
    for ohlc in ohlcs:
        ohlc['time'] = ohlc['time'] - 8 * 3600
    print symbol
    client.put_5minute(symbol, ohlcs)
    # store.fiveminstore.update(symbol, ohlcs)

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010 yinhm

'''A datafeed server daemon.
'''
import config
import logging
import os
import signal
import sys
import tornado

from tornado import ioloop
from tornado.options import define, options

from datafeed.exchange import SH
from datafeed.imiguserver import ImiguApplication
from datafeed.server import Server


DATA_DIR = os.path.join(os.path.realpath(os.path.dirname(__file__)),
                        'var')

define("port", default=8082, help="run on the given port", type=int)
define("datadir", default=DATA_DIR, help="default data dir", type=str)


def main():
    tornado.options.parse_command_line()

    app = ImiguApplication(options.datadir, SH())
    server = Server(app, auth_password=config.AUTH_PASSWORD)
    server.listen(options.port)
    io_loop = tornado.ioloop.IOLoop.instance()

    check_time = 1 * 1000  # every second
    scheduler = ioloop.PeriodicCallback(app.periodic_job,
                                        check_time,
                                        io_loop=io_loop)

    def shutdown(signum, frame):
        print 'Signal handler called with signal', signum
        io_loop.stop()
        scheduler.stop()
        server.log_stats()
        logging.info("==> Exiting datafeed.")

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    scheduler.start()
    io_loop.start()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = wjf
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2011 yinhm

import config

from datafeed.providers.tongshi import run_tongshi_win


if __name__=='__main__':
    run_tongshi_win(config.SERVER_ADDR, config.AUTH_PASSWORD)

########NEW FILE########
