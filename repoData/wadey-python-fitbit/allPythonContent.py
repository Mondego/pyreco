__FILENAME__ = dump
#!/usr/bin/env python
"""
This is an example script to dump the fitbit data for the previous day.
This can be set up in a cronjob to dump data daily.

Create a config file at ~/.fitbit.conf with the following:

[fitbit]
user_id: 12XXX 
sid: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
uid: 123456
uis: XXX%3D
dump_dir: ~/Dropbox/fitbit
"""
import time
import os
import ConfigParser

import fitbit

CONFIG = ConfigParser.ConfigParser()
CONFIG.read(["fitbit.conf", os.path.expanduser("~/.fitbit.conf")])

DUMP_DIR=os.path.expanduser(CONFIG.get('fitbit', 'dump_dir'))

def client():
    return fitbit.Client(CONFIG.get('fitbit', 'user_id'), CONFIG.get('fitbit', 'sid'), CONFIG.get('fitbit', 'uid'), CONFIG.get('fitbit', 'uis'))

def dump_to_str(data):
    return "\n".join(["%s,%s" % (str(ts), v) for ts, v in data])

def dump_to_file(data_type, date, data):
    directory = "%s/%s" % (DUMP_DIR, data_type)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    with open("%s/%s.csv" % (directory, str(date)), "w") as f:
        f.write(dump_to_str(data))

def dump_day(date):
    c = client()

    dump_to_file("steps", date, c.intraday_steps(date))
    time.sleep(5)    
    dump_to_file("calories", date, c.intraday_calories_burned(date))
    time.sleep(5)
    dump_to_file("active_score", date, c.intraday_active_score(date))
    time.sleep(5)
    dump_to_file("sleep", date, c.intraday_sleep(date))
    time.sleep(5)

if __name__ == '__main__':
    #import logging
    #logging.basicConfig(level=logging.DEBUG)
    import datetime
    dump_day((datetime.datetime.now().date() - datetime.timedelta(days=1)))

########NEW FILE########
__FILENAME__ = dump2sqlite
#!/usr/bin/env python
"""
This is an example script to dump the fitbit data for the previous day into a sqlite database.
This can be set up in a cronjob to dump data daily.

Create a config file at ~/.fitbit.conf with the following:

[fitbit]
user_id: 12XXX
sid: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
uid: 123456
uis: XXX%3D
dump_dir: ~/Dropbox/fitbit
db_file: ~/data/nameofdbfile.sqlite

The database has a table for each of steps, calories, active_score, and sleep. There is also a table with extension _daily for each that contains accumulated data per day.

The timestamp in the table is a unix timestamp. Tables are set up so that the script can be run repeatedly for the same day. Newer data replaces older data for the same timestamp. This is so data can be caught up if the fitbit does not sync every day.
"""

from time import mktime, sleep
from datetime import datetime, timedelta
from os import path
import ConfigParser
import sqlite3

import fitbit

CONFIG = ConfigParser.ConfigParser()
CONFIG.read(["fitbit.conf", path.expanduser("~/.fitbit.conf")])

DB_FILE = path.expanduser(CONFIG.get('fitbit', 'db_file'))

def client():
	return fitbit.Client(CONFIG.get('fitbit', 'user_id'), CONFIG.get('fitbit', 'sid'), CONFIG.get('fitbit', 'uid'), CONFIG.get('fitbit', 'uis'))

def create_table(table, db):
	db.execute("create table %s (datetime integer PRIMARY KEY ON CONFLICT REPLACE, %s integer)" % (table, table))
	db.execute("create table %s_daily (date integer PRIMARY KEY ON CONFLICT REPLACE, %s integer)" % (table, table))

""" Connects to the DB, creates it if it doesn't exist. Returns the connection.
"""
def connect_db(filename):
	if path.isfile(filename):
		return sqlite3.connect(filename)
	else:
		db = sqlite3.connect(filename)
		create_table("steps", db)
		create_table("calories", db)
		create_table("active_score", db)
		create_table("sleep", db)
		return db

def dump_to_db(db, data_type, date, data):
	insertString = "insert into %s values (?, ?)" % data_type
	sum = 0
	for row in data:
		db.execute(insertString, (mktime(row[0].timetuple()), row[1]))
		sum += row[1]
	db.execute("insert into %s_daily values (?, ?)" % data_type, (mktime(date.timetuple()), sum))
	db.commit()

def dump_day(db, date):
	c = client()

	dump_to_db(db, "steps", date, c.intraday_steps(date))
	sleep(1)
	dump_to_db(db, "calories", date, c.intraday_calories_burned(date))
	sleep(1)
	dump_to_db(db, "active_score", date, c.intraday_active_score(date))
	sleep(1)
	dump_to_db(db, "sleep", date, c.intraday_sleep(date))
	sleep(1)

if __name__ == '__main__':
	db = connect_db(DB_FILE)

	#oneday = timedelta(days=1)
	#day = datetime(2009, 10, 18).date()
	#while day < datetime.now().date():
	#	print day
	#	dump_day(db, day)
	#	day += oneday

	dump_day(db, (datetime.now().date() - timedelta(days=1)))

	db.close()

########NEW FILE########
__FILENAME__ = client
import xml.etree.ElementTree as ET
import datetime
import urllib, urllib2
import logging

_log = logging.getLogger("fitbit")

class Client(object):
    """A simple API client for the www.fitbit.com website.
    see README for more details
    """
    
    def __init__(self, user_id, sid, uid, uis, url_base="http://www.fitbit.com"):
        self.user_id = user_id
        self.sid = sid
        self.uid = uid
        self.uis = uis
        self.url_base = url_base
        self._request_cookie = "sid=%s; uid=%s; uis=%s" % (sid, uid, uis)
    
    def intraday_calories_burned(self, date):
        """Retrieve the calories burned every 5 minutes
        the format is: [(datetime.datetime, calories_burned), ...]
        """
        return self._graphdata_intraday_request("intradayCaloriesBurned", date)
    
    def intraday_active_score(self, date):
        """Retrieve the active score for every 5 minutes
        the format is: [(datetime.datetime, active_score), ...]
        """
        return self._graphdata_intraday_request("intradayActiveScore", date)

    def intraday_steps(self, date):
        """Retrieve the steps for every 5 minutes
        the format is: [(datetime.datetime, steps), ...]
        """
        return self._graphdata_intraday_request("intradaySteps", date)
    
    def intraday_sleep(self, date, sleep_id=None):
        """Retrieve the sleep status for every 1 minute interval
        the format is: [(datetime.datetime, sleep_value), ...]
        The statuses are:
            0: no sleep data
            1: asleep
            2: awake
            3: very awake
        For days with multiple sleeps, you need to provide the sleep_id
        or you will just get the first sleep of the day
        """
        return self._graphdata_intraday_sleep_request("intradaySleep", date, sleep_id=sleep_id)
    
    def _request(self, path, parameters):
        # Throw out parameters where the value is not None
        parameters = dict([(k,v) for k,v in parameters.items() if v])
        
        query_str = urllib.urlencode(parameters)

        request = urllib2.Request("%s%s?%s" % (self.url_base, path, query_str), headers={"Cookie": self._request_cookie})
        _log.debug("requesting: %s", request.get_full_url())

        data = None
        try:
            response = urllib2.urlopen(request)
            data = response.read()
            response.close()
        except urllib2.HTTPError as httperror:
            data = httperror.read()
            httperror.close()

        #_log.debug("response: %s", data)

        return ET.fromstring(data.strip())

    def _graphdata_intraday_xml_request(self, graph_type, date, data_version=2108, **kwargs):
        params = dict(
            userId=self.user_id,
            type=graph_type,
            version="amchart",
            dataVersion=data_version,
            chart_Type="column2d",
            period="1d",
            dateTo=str(date)
        )
        
        if kwargs:
            params.update(kwargs)

        return self._request("/graph/getGraphData", params)

    def _graphdata_intraday_request(self, graph_type, date):
        # This method used for the standard case for most intraday calls (data for each 5 minute range)
        xml = self._graphdata_intraday_xml_request(graph_type, date)
        
        base_time = datetime.datetime.combine(date, datetime.time())
        timestamps = [base_time + datetime.timedelta(minutes=m) for m in xrange(0, 288*5, 5)]
        values = [int(float(v.text)) for v in xml.findall("data/chart/graphs/graph/value")]
        return zip(timestamps, values)
    
    def _graphdata_intraday_sleep_request(self, graph_type, date, sleep_id=None):
        # Sleep data comes back a little differently
        xml = self._graphdata_intraday_xml_request(graph_type, date, data_version=2112, arg=sleep_id)
        
        
        elements = xml.findall("data/chart/graphs/graph/value")
        timestamps = [datetime.datetime.strptime(e.attrib['description'].split(' ')[-1], "%I:%M%p") for e in elements]
        
        # TODO: better way to figure this out?
        # Check if the timestamp cross two different days
        last_stamp = None
        datetimes = []
        base_date = date
        for timestamp in timestamps:
            if last_stamp and last_stamp > timestamp:
                base_date -= datetime.timedelta(days=1)
            last_stamp = timestamp
        
        last_stamp = None
        for timestamp in timestamps:
            if last_stamp and last_stamp > timestamp:
                base_date += datetime.timedelta(days=1)
            datetimes.append(datetime.datetime.combine(base_date, timestamp.time()))
            last_stamp = timestamp
        
        values = [int(float(v.text)) for v in xml.findall("data/chart/graphs/graph/value")]
        return zip(datetimes, values)
########NEW FILE########
