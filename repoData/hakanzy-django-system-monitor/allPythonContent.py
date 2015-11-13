__FILENAME__ = admin
from django.contrib import admin

admin.site.index_template = 'sysmon/index.html'

########NEW FILE########
__FILENAME__ = sysmon_tags
from collections import namedtuple

from django import template

from psutil import AccessDenied


cpuTuple = namedtuple('cpuTuple',
                      'core, used')

memTuple = namedtuple('memTuple',
                      'total, used')

diskPartTuple = namedtuple('diskPartTuple',
                           'device, mountpoint, fstype, total, percent')

networkTuple = namedtuple('networkTuple',
                          'device, sent, recv, pkg_sent, pkg_recv')

processTuple = namedtuple('processTuple',
                          'pid, name, status, user, memory')


def bytes2human(num):
    for x in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')


register = template.Library()


class SysMon(template.Node):
    def render(self, context):
        try:
            import psutil as pu
        except:
            context['error_psutil'] = 'not_found'
            return ''

        # cpu
        cpu_info = cpuTuple(
            core=pu.NUM_CPUS,
            used=pu.cpu_percent())

        # memory
        mem_info = memTuple(
            total=bytes2human(pu.TOTAL_PHYMEM),
            used=pu.virtual_memory().percent)

        # disk
        partitions = list()
        for part in pu.disk_partitions():
            partitions.append(
                diskPartTuple(
                    device=part.device,
                    mountpoint=part.mountpoint,
                    fstype=part.fstype,
                    total=bytes2human(
                        pu.disk_usage(part.mountpoint).total),
                    percent=pu.disk_usage(part.mountpoint).percent))

        # network
        networks = list()
        for k, v in pu.net_io_counters(pernic=True).items():
            # Skip loopback interface
            if k == 'lo':
                continue

            networks.append(
                networkTuple(
                    device=k,
                    sent=bytes2human(v.bytes_sent),
                    recv=bytes2human(v.bytes_recv),
                    pkg_sent=v.packets_sent,
                    pkg_recv=v.packets_recv))

        # processes
        processes = list()
        for process in pu.process_iter():

            try:
                percent = process.get_memory_percent()
            except AccessDenied:
                percent = "Access Denied"
            else:
                percent = int(percent)

            processes.append(processTuple(
                pid=process.pid,
                name=process.name,
                status=process.status,
                user=process.username,
                memory=percent))

        processes_sorted = sorted(
            processes, key=lambda p: p.memory, reverse=True)

        all_stats = {
            'cpu_info': cpu_info,
            'mem_info': mem_info,
            'partitions': partitions,
            'networks': networks,
            'processes': processes_sorted[:10],
        }

        context.update(all_stats)

        return ''


@register.tag
def get_system_stats(parser, token):
    return SysMon()

########NEW FILE########
__FILENAME__ = test_bytes2human
from sysmon.templatetags.sysmon_tags import bytes2human


def kbyte(quantity):
    return 1024. * quantity


def mega(quantity):
    return kbyte(1024.) * quantity


def giga(quantity):
    return mega(1024) * quantity


def tera(quantity):
    return giga(1024) * quantity


def test_bytes():
    assert bytes2human(0.) == '0.0bytes'
    assert bytes2human(0.1) == '0.1bytes'
    assert bytes2human(1.) == '1.0bytes'
    assert bytes2human(100.) == '100.0bytes'
    assert bytes2human(1023.9) == '1023.9bytes'


def test_kb():
    assert bytes2human(kbyte(1)) == '1.0KB'
    assert bytes2human(kbyte(2)) == '2.0KB'
    assert bytes2human(kbyte(1023.9)) == '1023.9KB'


def test_mb():
    assert bytes2human(mega(1.)) == '1.0MB'
    assert bytes2human(mega(123.)) == '123.0MB'
    assert bytes2human(mega(1023.9)) == '1023.9MB'


def test_giga():
    assert bytes2human(giga(1.)) == '1.0GB'
    assert bytes2human(giga(999.2)) == '999.2GB'
    assert bytes2human(giga(1023.9)) == '1023.9GB'


def test_tera():
    assert bytes2human(tera(1.)) == '1.0TB'
    assert bytes2human(tera(999.)) == '999.0TB'

########NEW FILE########
__FILENAME__ = test_sysmon_tags
from sysmon.templatetags.sysmon_tags import SysMon


def test_cpu_info_in_context():
    context = {}
    SysMon().render(context)
    assert context.get('cpu_info', None)
    cpu_info = context['cpu_info']
    assert hasattr(cpu_info, 'core')
    assert hasattr(cpu_info, 'used')


def test_mem_info_in_context():
    context = {}
    SysMon().render(context)
    assert context.get('mem_info', None)
    mem_info = context['mem_info']
    assert hasattr(mem_info, 'total')
    assert hasattr(mem_info, 'used')


def test_disk_partitions_in_context():
    context = {}
    SysMon().render(context)
    assert context.get('partitions', None)
    partitions = context['partitions']
    assert type(partitions) == list
    first_partition = partitions[0]
    assert hasattr(first_partition, 'device')
    assert hasattr(first_partition, 'mountpoint')
    assert hasattr(first_partition, 'fstype')
    assert hasattr(first_partition, 'total')
    assert hasattr(first_partition, 'percent')


def test_networks_in_context():
    context = {}
    SysMon().render(context)
    assert context.get('networks', None)
    networks = context['networks']
    assert type(networks) == list
    first_network = networks[0]
    assert hasattr(first_network, 'device')
    assert hasattr(first_network, 'sent')
    assert hasattr(first_network, 'recv')
    assert hasattr(first_network, 'pkg_sent')
    assert hasattr(first_network, 'pkg_recv')


def test_processes_in_context():
    context = {}
    SysMon().render(context)
    assert context.get('processes', None)
    processes = context['processes']
    assert type(processes) == list
    first_process = processes[0]
    assert hasattr(first_process, 'pid')
    assert hasattr(first_process, 'name')
    assert hasattr(first_process, 'status')
    assert hasattr(first_process, 'user')
    assert hasattr(first_process, 'memory')

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testproject.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
"""
Django settings for testproject project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'q@x05k=(lyob=mox$vpl!3t_&rld9utdmu##=5_nh=pj3u&7dw'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'sysmon',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'testproject.urls'

WSGI_APPLICATION = 'testproject.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testproject.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for testproject project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testproject.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
