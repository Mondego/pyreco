__FILENAME__ = installtasks
from optparse import make_option

from django.core.management.base import NoArgsCommand, CommandError
from django.conf import settings

from kronos import tasks, reinstall, printtasks

class Command(NoArgsCommand):
    help = 'Register tasks with cron'

    def handle_noargs(self, **options):
        reinstall()
        print "Installed %s tasks." % len(tasks)

########NEW FILE########
__FILENAME__ = runtask
from django.core.management.base import BaseCommand, CommandError

import kronos

class Command(BaseCommand):
    args = '<task>'
    help = 'Run the given task'

    def handle(self, task_name, **options):
        kronos.load()

        for task in kronos.tasks:
            if task.__name__ == task_name:
                return task()

        raise CommandError('Task \'%s\' not found' % task_name)

########NEW FILE########
__FILENAME__ = uninstalltasks
import sys
import os

from subprocess import Popen as run
from subprocess import PIPE

from django.core.management.base import NoArgsCommand, CommandError
from django.conf import settings

from kronos import uninstall

class Command(NoArgsCommand):
    help = 'Remove tasks from cron'

    def handle_noargs(self, **options):
        uninstall()

########NEW FILE########
__FILENAME__ = settings
import os
import sys

from django.conf import settings

KRONOS_PYTHON = getattr(settings, 'KRONOS_PYTHON', sys.executable)
KRONOS_MANAGE = getattr(settings, 'KRONOS_MANAGE', '%s/manage.py' % os.getcwd())
KRONOS_PYTHONPATH = getattr(settings, 'KRONOS_PYTHONPATH', None)
PROJECT_MODULE = sys.modules['.'.join(settings.SETTINGS_MODULE.split('.')[:-1])]
KRONOS_POSTFIX = getattr(settings, 'KRONOS_POSTFIX', '')

########NEW FILE########
__FILENAME__ = utils
import sys
import os

import subprocess

from django.conf import settings

import kronos

def read_crontab():
    """
    Read the crontab.
    """
    command = subprocess.Popen(
        args = 'crontab -l',
        shell = True,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE
    )

    stdout, stderr = command.stdout.read(), command.stderr.read()

    if stderr and 'no crontab for' not in stderr:
        raise ValueError('Could not read from crontab: \'%s\'' % stderr)

    return stdout

def write_crontab(string):
    """
    Write the given string to the crontab.
    """
    command = subprocess.Popen(
        args = 'printf \'%s\' | crontab' % string.replace("'", "'\\''"),
        shell = True,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE
    )

    stdout, stderr = command.stdout.read(), command.stderr.read()

    if stderr:
        raise ValueError('Could not write to crontab: \'%s\'' % stderr)

def delete_crontab():
    """
    Delete the crontab.
    """
    command = subprocess.Popen(
        args = 'crontab -r',
        shell = True,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE
    )

    stdout, stderr = command.stdout.read(), command.stderr.read()

    if stderr and 'no crontab' not in stderr:
        raise ValueError('Could not delete crontab: \'%s\'' % stderr)

########NEW FILE########
__FILENAME__ = version
__version__ = '0.4'

########NEW FILE########
__FILENAME__ = cron
import random

import kronos

@kronos.register('0 0 * * *')
def complain():
    complaints = [
        "I forgot to migrate our applications's cron jobs to our new server! Darn!",
        "I'm out of complaints! Damnit!"
    ]

    print random.choice(complaints)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from views import home

urlpatterns = patterns('',
    url(r'^$', home, name='home'),

    url('fandjango/', include('fandjango.urls'))
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse

from fandjango.decorators import facebook_authorization_required

@facebook_authorization_required()
def home(request):
    return HttpResponse()
########NEW FILE########
__FILENAME__ = cron
import kronos

@kronos.register('0 0 * * *')
def praise():
    print "Kronos makes it really easy to define and schedule tasks with cron!"
########NEW FILE########
__FILENAME__ = settings
DATABASES = {
    'default': {
        'ENGINE': 'sqlite3',
        'NAME': ':memory:'
    }
}

INSTALLED_APPS = [
    'kronos',
    'tests.project.app'
]

ROOT_URLCONF = 'urls'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns += patterns('',
    (r'^', include('app.urls'))
)
########NEW FILE########
__FILENAME__ = tests
from nose.tools import with_setup

from django.test.client import Client
from django.core.management import call_command

from subprocess import PIPE
from StringIO import StringIO

from nose.tools import *

from kronos import tasks, load
from kronos.utils import read_crontab, write_crontab, delete_crontab

from mock import Mock, patch

import project.cron
import project.app

load()

@patch('subprocess.Popen')
def test_read_crontab(mock):
    """Test reading from the crontab."""
    mock.return_value = Mock(
        stdout = StringIO('crontab: installing new crontab'),
        stderr = StringIO('')
    )

    read_crontab()

    mock.assert_called_with(
        args = 'crontab -l',
        shell = True,
        stdout = PIPE,
        stderr = PIPE
    )

@patch('subprocess.Popen')
def test_read_empty_crontab(mock):
    """Test reading from an empty crontab."""
    mock.return_value = Mock(
        stdout = StringIO(''),
        stderr = StringIO('crontab: no crontab for <user>')
    )

    read_crontab()

@patch('subprocess.Popen')
def test_read_crontab_with_errors(mock):
    """Test reading from the crontab."""
    mock.return_value = Mock(
        stdout = StringIO(''),
        stderr = StringIO('bash: crontal: command not found')
    )

    assert_raises(ValueError, read_crontab)

@patch('subprocess.Popen')
def test_write_crontab(mock):
    """Test writing to the crontab."""
    mock.return_value = Mock(
        stdout = StringIO('crontab: installing new crontab'),
        stderr = StringIO('')
    )

    write_crontab("* * * * * echo\n")

    mock.assert_called_with(
        args = 'printf \'* * * * * echo\n\' | crontab',
        shell = True,
        stdout = PIPE,
        stderr = PIPE
    )

def test_task_collection():
    """Test task collection."""
    assert project.app.cron.complain.__name__ in [task.__name__ for task in tasks]
    assert project.cron.praise.__name__ in [task.__name__ for task in tasks]

def test_runtask():
    """Test running tasks via the ``runtask`` command."""
    call_command('runtask', 'complain')
    call_command('runtask', 'praise')

@patch('subprocess.Popen')
def test_installtasks(mock):
    """Test installing tasks with the ``installtasks`` command."""
    mock.return_value = Mock(
        stdout = StringIO('crontab: installing new crontab'),
        stderr = StringIO('')
    )

    call_command('installtasks')

    assert mock.called

@patch('subprocess.Popen')
def test_unintalltasks(mock):
    """Test uninstalling tasks with the ``uninstalltasks`` command."""
    mock.return_value = Mock(
        stdout = StringIO('crontab: installing new crontab'),
        stderr = StringIO('')
    )

    call_command('uninstalltasks')

    assert mock.called

########NEW FILE########
