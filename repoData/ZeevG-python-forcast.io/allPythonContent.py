__FILENAME__ = example
import forecastio
import datetime


def main():


    api_key = "YOUR API KEY"
    lat = -31.967819
    lng = 115.87718

    forecast = forecastio.load_forecast(api_key, lat, lng)

    print forecast.hourly().data[0].temperature
    print "===========Hourly Data========="
    by_hour = forecast.hourly()
    print "Hourly Summary: %s" % (by_hour.summary)

    for hourly_data_point in by_hour.data:
        print hourly_data_point

    print "===========Daily Data========="
    by_day = forecast.daily()
    print "Daily Summary: %s" % (by_day.summary)

    for daily_data_point in by_day.data:
        print daily_data_point


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = api
import requests
import time as Time
import threading

from models import Forecast


def load_forecast(key, inLat, inLong, time=None, units="auto", lazy=False,
                  callback=None):

    """
        This function builds the request url and loads some or all of the
        needed json depending on lazy is True

        inLat:  The latitude of the forecast
        inLong: The longitude of the forecast
        time:   A datetime.datetime object representing the desired time of
                the forecast
        units:  A string of the preferred units of measurement, "auto" id
                default. also us,ca,uk,si is available
        lazy:   Defaults to false.  The function will only request the json
                data as it is needed. Results in more requests, but
                probably a faster response time (I haven't checked)
    """

    lat = inLat
    lng = inLong
    time = time

    if time is None:
        url = 'https://api.forecast.io/forecast/%s/%s,%s' \
              '?units=%s' % (key, lat, lng, units,)
    else:
        url_time = str(int(Time.mktime(time.timetuple())))
        url = 'https://api.forecast.io/forecast/%s/%s,%s,%s' \
              '?units=%s' % (key, lat, lng, url_time,
              units,)

    if lazy is True:
        baseURL = "%s&exclude=%s" % (url,
                                     'minutely,currently,hourly,'
                                     'daily,alerts,flags')
    else:
        baseURL = url

    if callback is None:
        return make_forecast(make_request(baseURL))
    else:
        thr = threading.Thread(target=load_async, args=(baseURL,),
                               kwargs={'callback': callback})
        thr.start()


def make_forecast(response):
    return Forecast(response.json(), response, response.headers)


def make_request(url):
    return requests.get(url)


def load_async(url, callback):
    callback(make_forecast(make_request(url)))

########NEW FILE########
__FILENAME__ = models
import datetime
import requests


class Forecast():
    def __init__(self, data, response, headers):
        self.response = response
        self.http_headers = headers
        self.json = data

    def update(self):
        r = requests.get(self.response.url)
        self.json = r.json()
        self.response = r

    def currently(self):
        return self._forcastio_data('currently')

    def minutely(self):
        return self._forcastio_data('minutely')

    def hourly(self):
        return self._forcastio_data('hourly')

    def daily(self):
        return self._forcastio_data('daily')
        
    def offset(self):
        return self.json['offset']

    def _forcastio_data(self, key):
        keys = ['minutely', 'currently', 'hourly', 'daily']
        try:
            if key not in self.json:
                keys.remove(key)
                url = "%s&exclude=%s%s" % (self.response.url.split('&')[0],
                      ','.join(keys), ',alerts,flags')

                response = requests.get(url).json()
                self.json[key] = response[key]

            if key == 'currently':
                return ForecastioDataPoint(self.json[key])
            else:
                return ForecastioDataBlock(self.json[key])
        except:
            if key == 'currently':
                return ForecastioDataPoint()
            else:
                return ForecastioDataBlock()

class ForecastioDataBlock():
    def __init__(self, d=None):
        d = d or {}
        self.summary = d.get('summary')
        self.icon = d.get('icon')

        self.data = [ForecastioDataPoint(datapoint) 
                     for datapoint in d.get('data', [])]

    def __unicode__(self):
        return '<ForecastioDataBlock instance: ' \
               '%s with %d ForecastioDataPoints>' % (self.summary,
                                                     len(self.data),)

    def __str__(self):
        return unicode(self).encode('utf-8')


class ForecastioDataPoint():
    def __init__(self, d=None):
        d = d or {}

        try:
            self.time = datetime.datetime.fromtimestamp(int(d['time']))
        except:
            self.time = None

        self.utime = d.get('time')
        self.icon = d.get('icon')
        self.summary = d.get('summary')

        try:
            sr_time = int(d['sunriseTime'])
            self.sunriseTime = datetime.datetime.fromtimestamp(sr_time)
        except:
            self.sunriseTime = None

        try:
            ss_time = int(d['sunsetTime'])
            self.sunsetTime = datetime.datetime.fromtimestamp(ss_time)
        except:
            self.sunsetTime = None

        self.precipIntensity = d.get('precipIntensity')
        self.precipIntensityMax = d.get('precipIntensityMax')
        self.precipIntensityMaxTime = d.get('precipIntensityMaxTime')
        self.precipProbability = d.get('precipProbability')
        self.precipType = d.get('precipType')
        self.precipAccumulation = d.get('precipAccumulation')
        self.temperature = d.get('temperature')
        self.temperatureMin = d.get('temperatureMin')
        self.temperatureMinTime = d.get('temperatureMinTime')
        self.temperatureMax = d.get('temperatureMax')
        self.temperatureMaxTime = d.get('temperatureMaxTime')
        self.dewPoint = d.get('dewPoint')
        self.windspeed = d.get('windSpeed')
        self.windbearing = d.get('windBearing')
        self.cloudcover = d.get('cloudCover')
        self.humidity = d.get('humidity')
        self.pressure = d.get('pressure')
        self.visibility = d.get('visibility')
        self.ozone = d.get('ozone')

    def __unicode__(self):
        return '<ForecastioDataPoint instance: ' \
               '%s at %s>' % (self.summary, self.time,)

    def __str__(self):
        return unicode(self).encode('utf-8')

########NEW FILE########
