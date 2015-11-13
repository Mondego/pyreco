__FILENAME__ = dpms
from os import system


class Py3status:
    """
    This module allows activation and deactivation
    of DPMS (Display Power Management Signaling)
    by clicking on 'DPMS' in the status bar.

    Written and contributed by @tasse:
        Andre Doser <dosera AT tf.uni-freiburg.de>
    """
    def __init__(self):
        """
        Detect current state on start.
        """
        self.run = system('xset -q | grep -iq "DPMS is enabled"') == 0

    def dpms(self, i3status_output_json, i3status_config):
        """
        Display a colorful state of DPMS.
        """
        result = {
            'full_text': 'DPMS',
            'name': 'dpms'
        }
        if self.run:
            result['color'] = i3status_config['color_good']
        else:
            result['color'] = i3status_config['color_bad']
        return (0, result)

    def on_click(self, json, i3status_config, event):
        """
        Enable/Disable DPMS on left click.
        """
        if event['button'] == 1:
            if self.run:
                self.run = False
                system("xset -dpms")
            else:
                self.run = True
                system("xset +dpms")
            system("killall -USR1 py3status")

########NEW FILE########
__FILENAME__ = empty_class
class Py3status:
    """
    Empty and basic py3status class.

    NOTE: py3status will NOT execute:
        - methods starting with '_'
        - methods decorated by @property and @staticmethod

    NOTE: reserved method names:
        - 'kill' method for py3status exit notification
        - 'on_click' method for click events from i3bar
    """
    def kill(self, i3status_output_json, i3status_config):
        """
        This method will be called upon py3status exit.
        """
        pass

    def on_click(self, i3status_output_json, i3status_config, event):
        """
        This method will be called when a click event occurs on this module's
        output on the i3bar.

        Example 'event' json object:
        {'y': 13, 'x': 1737, 'button': 1, 'name': 'empty', 'instance': 'first'}
        """
        pass

    def empty(self, i3status_output_json, i3status_config):
        """
        This method will return an empty text message
        so it will NOT be displayed on your i3bar.

        If you want something displayed you should write something
        in the 'full_text' key of your response.

        See the i3bar protocol spec for more information:
        http://i3wm.org/docs/i3bar-protocol.html
        """
        response = {'full_text': '', 'name': 'empty', 'instance': 'first'}
        return (0, response)

########NEW FILE########
__FILENAME__ = glpi
# You need MySQL-python from http://pypi.python.org/pypi/MySQL-python
import MySQLdb


class Py3status:
    """
    This example class demonstrates how to display the current total number of
    open tickets from GLPI in your i3bar.

    It features thresholds to colorize the output and forces a low timeout to
    limit the impact of a server connectivity problem on your i3bar freshness.

    Note that we don't have to implement a cache layer as it is handled by
    py3status automagically.
    """
    def count_glpi_open_tickets(self, json, i3status_config):
        response = {'full_text': '', 'name': 'glpi_tickets'}

        # user-defined variables
        CRIT_THRESHOLD = 20
        WARN_THRESHOLD = 15
        MYSQL_DB = ''
        MYSQL_HOST = ''
        MYSQL_PASSWD = ''
        MYSQL_USER = ''
        POSITION = 0

        mydb = MySQLdb.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            passwd=MYSQL_PASSWD,
            db=MYSQL_DB,
            connect_timeout=5,
            )
        mycr = mydb.cursor()
        mycr.execute('''select count(*)
                        from glpi_tickets
                        where closedate is NULL and solvedate is NULL;''')
        row = mycr.fetchone()
        if row:
            open_tickets = int(row[0])
            if i3status_config['colors']:
                if open_tickets > CRIT_THRESHOLD:
                    response.update({'color': i3status_config['color_bad']})
                elif open_tickets > WARN_THRESHOLD:
                    response.update(
                        {'color': i3status_config['color_degraded']}
                    )
            response['full_text'] = '%s tickets' % open_tickets
        mydb.close()

        return (POSITION, response)

########NEW FILE########
__FILENAME__ = i3bar_click_events
from subprocess import Popen
from time import time


class Py3status:
    """
    This module allows you to take actions based on click events made on
    the i3status modules. For example, thanks to this module you could
    launch the wicd GUI when clicking on the ethernet or wireless module
    of your i3status output !

    IMPORTANT:
        This module file name is reserved and should NOT be changed if you
        want py3status to handle your i3status modules click events !

        The behavior described above will only work if this file is named
        'i3bar_click_events.py' !
    """
    def __init__(self):
        """
        This is where you setup your actions based on your i3status config.

        Configuration:
        --------------
        self.actions = {
            "<module name and instance>": {
                <button number>: [<function to run>, <arg1>, <arg2>],
            }
        }

        Variables:
        ----------
        <button number> is an integer from 1 to 3:
            1 : left click
            2 : middle click
            3 : right click

        <function to run> is a python function written in this module.
            The 'external_command' function is provided for convenience if
            you want to call an external program from this module.
            You can of course write your own functions and have them executed
            on a click event at will with possible arguments <arg1>, <arg2>...

        <module name and instance> is a string made from the module
        attribute 'name' and 'instance' using a space as separator:
            For i3status modules, it's simply the name of the module as it
            appears in the 'order' instruction of your i3status.conf.
            Example:
                in i3status.conf -> order += "wireless wlan0"
                self.actions key -> "wireless wlan0"

        Usage example:
        --------------
            - Open the wicd-gtk GUI when we LEFT click on the ethernet
            module of i3status.
            - Open emelfm2 to /home when we LEFT click on
            the /home instance of disk_info
            - Open emelfm2 to / when we LEFT click on
            the / instance of disk_info

            The related i3status.conf looks like:
                order += "disk /home"
                order += "disk /"
                order += "ethernet eth0"

            The resulting self.actions should be:
                self.actions = {
                    "ethernet eth0": {
                        1: [external_command, 'wicd-gtk', '-n'],
                    },
                    "disk_info /home": {
                        1: [external_command, 'emelfm2', '-1', '~'],
                    },
                    "disk_info /": {
                        1: [external_command, 'emelfm2', '-1', '/'],
                    },
                }
        """
        # CONFIGURE ME PLEASE, LOVE YOU BIG TIME !
        self.actions = {
        }

    def on_click(self, i3status_output_json, i3status_config, event):
        """
        If an action is configured for the given i3status module 'name' and
        'instance' (if present), then we'll execute the given function with
        its arguments (if present).

        Usually you SHOULD NOT modify this part of the code.
        """
        button = event['button']
        key_name = '{} {}'.format(
            event['name'],
            event.get('instance', '')
        ).strip()
        if key_name in self.actions and button in self.actions[key_name]:
            # get the function to run
            func = self.actions[key_name][button][0]
            assert hasattr(func, '__call__'), \
                'first element of the action list must be a function'

            # run the function with the possibly given arguments
            func(*self.actions[key_name][button][1:])

    def i3bar_click_events(self, i3status_output_json, i3status_config):
        """
        Cached empty output, this module doesn't show anything.
        """
        response = {'full_text': '', 'name': 'i3bar_click_events'}
        response['cached_until'] = time() + 3600
        return (-1, response)


def external_command(*cmd):
    """
    This convenience function lets you call an external program at will.

    NOTE:
        The stdout and stderr MUST be suppressed as shown here to avoid any
        output from being caught by the i3bar (this would freeze it).
        See issue #20 for more info.
    """
    Popen(
        cmd,
        stdout=open('/dev/null', 'w'),
        stderr=open('/dev/null', 'w')
    )

########NEW FILE########
__FILENAME__ = netdata
# -*- coding: utf-8 -*-

# netdata

# Netdata is a module uses great Py3status (i3status wrapper) to
# display network information (Linux systems) in i3bar.
# For more information read:
# i3wm homepage: http://i3wm.org
# py3status homepage: https://github.com/ultrabug/py3status

# Copyright (C) <2013> <Shahin Azad [ishahinism at Gmail]>

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

# ----------------------------------------------------------------- #
# Notes:
# 1. netdata will check 'eth0' interface by default. You can
# change it by changing 'self.net_interface' variable in 'GetData'
# class.
# 2. Colors are depended on strict specification in traffic/netspeed methods.
# You can change them by manipulating conditions.

import subprocess
from time import time

# Method 'netSpeed' will use this variables to calculate downloaded
# bytes in last second.  Initializing this variables globally is
# necessary since we can't use __init__ method in Py3Status class.
old_transmitted, old_received = 0, 0


class GetData:
    """Get system status

    """
    def __init__(self):
        # You can change it to another interface.
        # It'll be used for grabbing net interface data.
        self.net_interface = 'eth0'

    def execCMD(self, cmd, arg):
        """Take a system command and its argument, then return the result.

        Arguments:
        - `cmd`: system command.
        - `arg`: argument.
        """
        result = subprocess.check_output([cmd, arg])
        return result

    def netBytes(self):
        """Execute 'cat /proc/net/dev', find the interface line (Default
        'eth0') and grab received/transmitted bytes.

        """
        net_data = self.execCMD('cat', '/proc/net/dev').decode('utf-8').split()
        interface_index = net_data.index(self.net_interface + ':')
        received_bytes = int(net_data[interface_index + 1])
        transmitted_bytes = int(net_data[interface_index + 9])

        return received_bytes, transmitted_bytes


class Py3status:
    """
    System status in i3bar
    """
    def netSpeed(self, json, i3status_config):
        """Calculate network speed ('eth0' interface) and return it.  You can
        change the interface using 'self.net_interface' variable in
        'GetData' class.

        """
        data = GetData()
        response = {'full_text': '', 'name': 'net_speed'}

        global old_received
        global old_transmitted

        received_bytes, transmitted_bytes = data.netBytes()
        dl_speed = (received_bytes - old_received) / 1024.
        up_speed = (transmitted_bytes - old_transmitted) / 1024.

        if dl_speed < 30:
            response['color'] = i3status_config['color_bad']
        elif dl_speed < 60:
            response['color'] = i3status_config['color_degraded']
        else:
            response['color'] = i3status_config['color_good']

        response['full_text'] = "LAN(Kb): {:5.1f}↓ {:5.1f}↑"\
            .format(dl_speed, up_speed)
        response['cached_until'] = time()

        old_received, old_transmitted = received_bytes, transmitted_bytes
        return (0, response)

    def traffic(self, json, i3status_config):
        """Calculate networks used traffic. Same as 'netSpeed' method you can
        change the interface.

        """
        data = GetData()
        response = {'full_text': '', 'name': 'traffic'}

        received_bytes, transmitted_bytes = data.netBytes()
        download = received_bytes / 1024 / 1024.
        upload = transmitted_bytes / 1024 / 1024.
        total = download + upload

        if total < 400:
            response['color'] = i3status_config['color_good']
        elif total < 700:
            response['color'] = i3status_config['color_degraded']
        else:
            response['color'] = i3status_config['color_bad']

        response['full_text'] = "T(Mb): {:3.0f}↓ {:3.0f}↑ {:3.0f}↕"\
            .format(download, upload, total)

        return (1, response)

########NEW FILE########
__FILENAME__ = ns_checker
import dns.resolver
import socket


class Py3status:
    """
    This module launch a simple query on each nameservers for the specified domain.
    Nameservers are dynamically retrieved. The FQDN is the only one mandatory parameter.
    It's also possible to add additional nameservers by appending them in nameservers list.

    The default resolver can be overwritten with my_resolver.nameservers parameter.

    Written and contributed by @nawadanp
    """
    def __init__(self):
        self.domain = 'google.com'
        self.lifetime = 0.3
        self.resolver = []
        self.nameservers = []

    def ns_checker(self, i3status_output_json, i3status_config):
        response = {'full_text': '', 'name': 'ns_checker'}
        position = 0
        counter = 0
        error = False
        nameservers = []

        my_resolver = dns.resolver.Resolver()
        my_resolver.lifetime = self.lifetime
        if self.resolver:
            my_resolver.nameservers = self.resolver

        my_ns = my_resolver.query(self.domain, 'NS')

        # Insert each NS ip address in nameservers
        for ns in my_ns:
            nameservers.append(str(socket.gethostbyname(str(ns))))
        for ns in self.nameservers:
            nameservers.append(str(ns))

        # Perform a simple DNS query, for each NS servers
        for ns in nameservers:
            my_resolver.nameservers = [ns]
            counter += 1
            try:
                my_resolver.query(self.domain, 'A')
            except:
                error = True

        if error:
            response['full_text'] = str(counter) + ' NS NOK'
            response['color'] = i3status_config['color_bad']
        else:
            response['full_text'] = str(counter) + ' NS OK'
            response['color'] = i3status_config['color_good']

        return (position, response)

########NEW FILE########
__FILENAME__ = pingdom
# -*- coding: utf-8 -*-

import requests
from time import time


class Py3status:
    """
    Dynamically display the latest response time of the configured checks using
    the Pingdom API.
    We also verify the status of the checks and colorize if needed.
    Pingdom API doc : https://www.pingdom.com/services/api-documentation-rest/

    #NOTE: This module needs the 'requests' python module from pypi
        https://pypi.python.org/pypi/requests
    """
    def pingdom_checks(self, json, i3status_config):
        response = {'full_text': '', 'name': 'pingdom_checks'}

        #NOTE: configure me !
        APP_KEY = ''             # create an APP KEY on pingdom first
        CACHE_TIMEOUT = 600      # recheck every 10 mins
        CHECKS = []              # checks' names you want added to your bar
        LATENCY_THRESHOLD = 500  # when to colorize the output
        LOGIN = ''               # pingdom login
        PASSWORD = ''            # pingdom password
        TIMEOUT = 15
        POSITION = 0

        r = requests.get(
            'https://api.pingdom.com/api/2.0/checks',
            auth=(LOGIN, PASSWORD),
            headers={'App-Key': APP_KEY},
            timeout=TIMEOUT,
        )
        result = r.json()
        if 'checks' in result:
            for check in [
                ck for ck in result['checks'] if ck['name'] in CHECKS
            ]:
                if check['status'] == 'up':
                    response['full_text'] += '{}: {}ms, '.format(
                        check['name'],
                        check['lastresponsetime']
                    )
                    if check['lastresponsetime'] > LATENCY_THRESHOLD:
                        response.update(
                            {'color': i3status_config['color_degraded']}
                        )
                else:
                    response['full_text'] += '{}: DOWN'.format(
                        check['name'],
                        check['lastresponsetime']
                    )
                    response.update({'color': i3status_config['color_bad']})
            response['full_text'] = response['full_text'].strip(', ')
            response['cached_until'] = time() + CACHE_TIMEOUT

        return (POSITION, response)

########NEW FILE########
__FILENAME__ = pomodoro
"""
Pomodoro countdown on i3bar originally written by @Fandekasp (Adrien Lemaire)
"""
from subprocess import call
from time import time

MAX_BREAKS = 4
POSITION = 0
TIMER_POMODORO = 25 * 60
TIMER_BREAK = 5 * 60
TIMER_LONG_BREAK = 15 * 60


class Py3status:
    """
    """
    def __init__(self):
        self.__setup('stop')
        self.alert = False
        self.run = False

    def on_click(self, json, i3status_config, event):
        """
        Handles click events
        """
        if event['button'] == 1:
            if self.status == 'stop':
                self.status = 'start'
            self.run = True

        elif event['button'] == 2:
            self.__setup('stop')
            self.run = False

        elif event['button'] == 3:
            self.__setup('pause')
            self.run = False

    @property
    def response(self):
        """
        Return the response full_text string
        """
        return {
            'full_text': '{} ({})'.format(self.prefix, self.timer),
            'name': 'pomodoro'
        }

    def __setup(self, status):
        """
        Setup a step
        """
        self.status = status
        if status == 'stop':
            self.prefix = 'Pomodoro'
            self.status = 'stop'
            self.timer = TIMER_POMODORO
            self.breaks = 1

        elif status == 'start':
            self.prefix = 'Pomodoro'
            self.timer = TIMER_POMODORO

        elif status == 'pause':
            self.prefix = 'Break #%d' % self.breaks
            if self.breaks > MAX_BREAKS:
                self.timer = TIMER_LONG_BREAK
                self.breaks = 1
            else:
                self.breaks += 1
                self.timer = TIMER_BREAK

    def __decrement(self):
        """
        Countdown handler
        """
        self.timer -= 1
        if self.timer < 0:
            self.alert = True
            self.run = False
            self.__i3_nagbar()
            if self.status == 'start':
                self.__setup('pause')
                self.status = 'pause'
            elif self.status == 'pause':
                self.__setup('start')
                self.status = 'start'

    def __i3_nagbar(self, level='warning'):
        """
        Make use of i3-nagbar to display warnings to the user.
        """
        msg = '{} time is up !'.format(self.prefix)
        try:
            call(
                ['i3-nagbar', '-m', msg, '-t', level],
                stdout=open('/dev/null', 'w'),
                stderr=open('/dev/null', 'w')
            )
        except:
            pass

    def pomodoro(self, json, i3status_config):
        """
        Pomodoro response handling and countdown
        """
        if self.run:
            self.__decrement()

        response = self.response
        if self.alert:
            response['urgent'] = True
            self.alert = False

        if self.status == 'start':
            response['color'] = i3status_config['color_good']
        elif self.status == 'pause':
            response['color'] = i3status_config['color_degraded']
        else:
            response['color'] = i3status_config['color_bad']

        response['cached_until'] = time()
        return (POSITION, response)

########NEW FILE########
__FILENAME__ = sysdata
# -*- coding: utf-8 -*-

# sysdata

# Sysdata is a module uses great Py3status (i3status wrapper) to
# display system information (RAM usage) in i3bar (Linux systems).
# For more information read:
# i3wm homepage: http://i3wm.org
# py3status homepage: https://github.com/ultrabug/py3status

# NOTE: If you want py3status to show you your CPU temperature, change value of CPUTEMP into True
# in Py3status class - CPUInfo function 
# and REMEMBER that you must install lm_sensors if you want CPU temp!

# Copyright (C) <2013> <Shahin Azad [ishahinism at Gmail]>

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

import subprocess
from time import time


class GetData:
    """Get system status

    """
    def execCMD(self, cmd, arg):
        """Take a system command and its argument, then return the result.

        Arguments:
        - `cmd`: system command.
        - `arg`: argument.
        """
        result = subprocess.check_output([cmd, arg])
        return result

    def cpu(self):
        """Get the cpu usage data from /proc/stat :
        cpu  2255 34 2290 22625563 6290 127 456 0 0
        - user: normal processes executing in user mode
        - nice: niced processes executing in user mode
        - system: processes executing in kernel mode
        - idle: twiddling thumbs
        - iowait: waiting for I/O to complete
        - irq: servicing interrupts
        - softirq: servicing softirqs
        - steal: involuntary wait
        - guest: running a normal guest
        - guest_nice: running a niced guest
        These numbers identify the amount of time the CPU has spent performing
        different kinds of work.  Time units are in USER_HZ (typically hundredths of a
        second)
        """
        with open('/proc/stat', 'r') as fd:
            line = fd.readline()
        cpu_data = line.split()
        total_cpu_time = sum(map(int, cpu_data[1:]))
        cpu_idle_time = int(cpu_data[4])

        #return the cpu total&idle time
        return total_cpu_time, cpu_idle_time

    def memory(self):
        """Execute 'free -m' command, grab the memory capacity and used size
        then return; Memory size 'total_mem', Used_mem, and percentage
        of used memory.

        """
        # Run 'free -m' command and make a list from output.
        mem_data = self.execCMD('free', '-m').split()
        total_mem = int(mem_data[7]) / 1024.
        used_mem = int(mem_data[15]) / 1024.
        # Caculate percentage
        used_mem_percent = int(used_mem / (total_mem / 100))

        # Results are in kilobyte.
        return total_mem, used_mem, used_mem_percent


class Py3status:
    """
    System status in i3bar
    """
    def __init__(self):
        self.data = GetData()
        self.cpu_total = 0
        self.cpu_idle = 0

    def cpuInfo(self, json, i3status_config):
        """calculate the CPU status and return it.

        """
        response = {'full_text': '', 'name': 'cpu_usage'}
        cpu_total, cpu_idle = self.data.cpu()
        used_cpu_percent = 1 - float(cpu_idle-self.cpu_idle)/float(cpu_total-self.cpu_total)
        self.cpu_total = cpu_total
        self.cpu_idle = cpu_idle

        if used_cpu_percent <= 40:
            response['color'] = i3status_config['color_good']
        elif used_cpu_percent <= 75:
            response['color'] = i3status_config['color_degraded']
        else:
            response['color'] = i3status_config['color_bad']
        #cpu temp
        CPUTEMP=False
        if CPUTEMP:
                cputemp=subprocess.check_output('sensors | grep "CPU Temp" | cut -f 2 -d "+" | cut -f 1 -d " "',shell=True)
                cputemp=cputemp[:-1].decode('utf-8')
                response['full_text'] = "CPU: %.2f%%" % (used_cpu_percent*100) +" "+cputemp
        else:
             	response['full_text'] = "CPU: %.2f%%" % (used_cpu_percent*100)

        #cache the status for 10 seconds
        response['cached_until'] = time() + 10

        return (0, response)

    def ramInfo(self, json, i3status_config):
        """calculate the memory (RAM) status and return it.

        """
        response = {'full_text': '', 'name': 'ram_info'}
        total_mem, used_mem, used_mem_percent = self.data.memory()

        if used_mem_percent <= 40:
            response['color'] = i3status_config['color_good']
        elif used_mem_percent <= 75:
            response['color'] = i3status_config['color_degraded']
        else:
            response['color'] = i3status_config['color_bad']

        response['full_text'] = "RAM: %.2f/%.2f GB (%d%%)" % \
                                (used_mem, total_mem, used_mem_percent)
        response['cached_until'] = time()

        return (0, response)

########NEW FILE########
__FILENAME__ = weather_yahoo
# -*- coding: utf-8 -*-
from time import time
import requests


class Py3status:
    """
    Display current day + 3 days weather forecast as icons on your i3bar
    Based on Yahoo! Weather. forecast, thanks guys !
    See: http://developer.yahoo.com/weather/
    """
    def __init__(self):
        """
        Basic configuration
        Find your city code using:
            http://answers.yahoo.com/question/index?qid=20091216132708AAf7o0g
        The city_code in this example is for Paris, France
        """
        self.cache_timeout = 1800
        self.city_code = 'FRXX0076'
        self.request_timeout = 10

    def _get_forecast(self):
        """
        Ask Yahoo! Weather. for a forecast
        """
        r = requests.get(
            'http://query.yahooapis.com/v1/public/yql?q=select item from weather.forecast where location="%s"&format=json' % self.city_code,
            timeout=self.request_timeout
        )

        result = r.json()
        status = r.status_code
        forecasts = []

        if status == 200:
            forecasts = result['query']['results']['channel']['item']['forecast']
            # reset today
            forecasts[0] = result['query']['results']['channel']['item']['condition']
        else:
            raise Exception('got status {}'.format(status))

        # return current today + 3 days forecast
        return forecasts[:4]

    def _get_icon(self, forecast):
        """
        Return an unicode icon based on the forecast code and text
        See: http://developer.yahoo.com/weather/#codes
        """
        icons = ['☀', '☁', '☂', '☃', '?']
        code = int(forecast['code'])
        text = forecast['text'].lower()

        # sun
        if 'sun' in text or code in [31, 32, 33, 34, 36]:
            code = 0

        # cloud / early rain
        elif 'cloud' in text or code in [
                19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
                44
                ]:
            code = 1

        # rain
        elif 'rain' in text or code in [
                0, 1, 2, 3, 4, 5, 6, 9,
                11, 12,
                37, 38, 39,
                40, 45, 47
                ]:
            code = 2

        # snow
        elif 'snow' in text or code in [
                7, 8,
                10, 13, 14, 15, 16, 17, 18,
                35,
                41, 42, 43, 46
                ]:
            code = 3

        # dunno
        else:
            code = -1

        return icons[code]

    def weather_yahoo(self, json, i3status_config):
        """
        This method gets executed by py3status
        """
        response = {
            'cached_until': time() + self.cache_timeout,
            'full_text': '',
            'name': 'weather_yahoo'
            }

        forecasts = self._get_forecast()
        for forecast in forecasts:
            icon = self._get_icon(forecast)
            response['full_text'] += '{} '.format(icon)
        response['full_text'] = response['full_text'].strip()

        return (0, response)

########NEW FILE########
__FILENAME__ = whoami
from getpass import getuser
from time import time


class Py3status:
    """
    Simply output the currently logged in user in i3bar.

    Inspired by i3 FAQ:
        https://faq.i3wm.org/question/1618/add-user-name-to-status-bar/
    """
    def whoami(self, i3status_output_json, i3status_config):
        """
        We use the getpass module to get the current user.
        """
        # the current user doesnt change so much, cache it good
        CACHE_TIMEOUT = 600

        # here you can change the format of the output
        # default is just to show the username
        username = '{}'.format(getuser())

        # set, cache and return the output
        response = {'full_text': username, 'name': 'whoami'}
        response['cached_until'] = time() + CACHE_TIMEOUT
        return (0, response)

########NEW FILE########
