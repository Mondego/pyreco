__FILENAME__ = middleware
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
import pytz
import pygeoip

from .signals import detected_timezone
from .utils import get_ip_address_from_request


GEOIP_DATABASE = getattr(settings, 'GEOIP_DATABASE', None)

if not GEOIP_DATABASE:
    raise ImproperlyConfigured("GEOIP_DATABASE setting has not been defined.")


db_loaded = False
db = None


def load_db():
    global db
    db = pygeoip.GeoIP(GEOIP_DATABASE, pygeoip.MEMORY_CACHE)

    global db_loaded
    db_loaded = True


class EasyTimezoneMiddleware(object):
    def process_request(self, request):
        if not db_loaded:
            load_db()

        tz = request.session.get('django_timezone')

        if not tz:
            # use the default timezone (settings.TIME_ZONE) for localhost
            tz = timezone.get_default_timezone()

            ip = get_ip_address_from_request(request)
            if ip != '127.0.0.1':
                # if not local, fetch the timezone from pygeoip
                tz = db.time_zone_by_addr(ip)

        if tz:
            timezone.activate(tz)
            detected_timezone.send(sender=get_user_model(), instance=request.user, timezone=tz)
        else:
            timezone.deactivate()

########NEW FILE########
__FILENAME__ = signals
# Django
import django.dispatch

detected_timezone = django.dispatch.Signal(providing_args=["instance", "timezone"])

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

import socket


def is_valid_ip(ip_address):
    """ Check Validity of an IP address """
    valid = True
    try:
        socket.inet_aton(ip_address.strip())
    except:
        valid = False
    return valid


def get_ip_address_from_request(request):
    """ Makes the best attempt to get the client's real IP or return the loopback """
    PRIVATE_IPS_PREFIX = ('10.', '172.', '192.', '127.')
    ip_address = ''
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if x_forwarded_for and ',' not in x_forwarded_for:
        if not x_forwarded_for.startswith(PRIVATE_IPS_PREFIX) and is_valid_ip(x_forwarded_for):
            ip_address = x_forwarded_for.strip()
    else:
        ips = [ip.strip() for ip in x_forwarded_for.split(',')]
        for ip in ips:
            if ip.startswith(PRIVATE_IPS_PREFIX):
                continue
            elif not is_valid_ip(ip):
                continue
            else:
                ip_address = ip
                break
    if not ip_address:
        x_real_ip = request.META.get('HTTP_X_REAL_IP', '')
        if x_real_ip:
            if not x_real_ip.startswith(PRIVATE_IPS_PREFIX) and is_valid_ip(x_real_ip):
                ip_address = x_real_ip.strip()
    if not ip_address:
        remote_addr = request.META.get('REMOTE_ADDR', '')
        if remote_addr:
            if not remote_addr.startswith(PRIVATE_IPS_PREFIX) and is_valid_ip(remote_addr):
                ip_address = remote_addr.strip()
    if not ip_address:
        ip_address = '127.0.0.1'
    return ip_address

########NEW FILE########
