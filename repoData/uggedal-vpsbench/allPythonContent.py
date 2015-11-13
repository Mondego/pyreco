__FILENAME__ = bencher
#!/usr/bin/env python
from __future__ import with_statement

import os
import time
import subprocess

from datetime import datetime as dt
from datetime import timedelta
from socket import gethostname

HOST = gethostname()

def run(command):
    proc = subprocess.Popen(command,
                            shell=True,
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE)
    return "\n".join(proc.communicate())

def write_log(fname, data, number):
    if not os.path.isdir("logs"):
        os.mkdir("logs")
    path = "logs/%s-%s.log" % (HOST, fname)
    with open(path, 'a') as f:
        f.write("\n\nRun: %s\nDate: %s\n\n" % (number, dt.now()))
        f.write(data)
    os.system("git add %s" % path)


if __name__ == "__main__":
    test_dir = './django/tests'
    python_path = "export PYTHONPATH=django:."
    d_cmd_template = "%s && time %s/runtests.py --settings=" % (python_path,
                                                               test_dir)
    d_cmd = lambda setting: "%s%s" % (d_cmd_template, setting)

    usr = "testuser"
    pwd = "n0ns3curepWd"
    tests = "time ./run-all-tests --silent " + \
            "--server=Pg --user=%s --password=%s" % (usr, pwd)
    p_cmd = "cd mysql-5.1.34/sql-bench && %s" % tests

    u_cmd = "cd unixbench-5.1.2 && time ./Run"

    start = dt.now()
    for i in range(1, 10000):
        print "Running %s" % i

        write_log('django_sqlite3_test', run(d_cmd("sqlite3conf")), i)
        time.sleep(60*5)
        write_log('django_pgsql_test', run(d_cmd("pgsqlconf")), i)
        time.sleep(60*5)
        write_log('pgsql_mysql_benchmark', run(p_cmd), i)
        time.sleep(60*5)
        write_log('unix_benchmark', run(u_cmd), i)

        os.system('git pull')
        os.system('git commit -m "Logging run %s (%s)"' % (i, HOST))
        os.system('git push')

        while dt.now() - start < timedelta(hours=3):
            time.sleep(10)
        start = dt.now()

########NEW FILE########
__FILENAME__ = bootstrap
#!/usr/bin/env python
import os
import sys

"""
Installing PostgreSQL for running the MySQL benchmarks
and Django test suite:

    apt-get install postgresql libdbd-pg-perl python-psycopg2 libreadline5-dev python-scipy

    su postgres -c "createuser -P testuser"

    su postgres -c psql template1
        CREATE DATABASE test OWNER testuser ENCODING 'UTF8';

    vi /etc/postgresql/8.3/main/pg_hba.conf
        local    all    testuser    md5

    /etc/init.d/postgresql-8.3 restart

"""

if __name__ == "__main__":
    if "--all" in sys.argv:
        d_dir = "django"
        if not os.path.isdir(d_dir):
            u = " http://code.djangoproject.com/svn/django/trunk/@10680"
            os.system("svn co %s %s" % (u, d_dir))

        m_dir = "mysql-5.1.34"
        if not os.path.isdir(m_dir):
            u = "http://downloads.mysql.com/archives/mysql-5.1/mysql-5.1.34.tar.gz"
            cmd = "wget %s && tar xzf %s.tar.gz && cd %s && ./configure " + \
                  "&& make && cd .. && patch -p0 -i %s.patch"
            os.system(cmd % (u, m_dir, m_dir, m_dir))

        u_dir = "unixbench-5.1.2"
        if not os.path.isdir(u_dir):
            u = "http://www.hermit.org/Linux/Benchmarking/unixbench-5.1.2.tar.gz"
            cmd = "wget %s && tar xzf %s.tar.gz && " + \
                  "patch -p0 -i %s.patch && cd %s && make all"
            os.system(cmd % (u, u_dir, u_dir, u_dir))

    g_dir = "GChartWrapper"
    if not os.path.isdir(g_dir):
        u = "http://google-chartwrapper.googlecode.com/svn/trunk/%s" % g_dir
        os.system("svn co %s" % u)

########NEW FILE########
__FILENAME__ = grapher
#!/usr/bin/env python
from __future__ import with_statement

import re
from datetime import datetime, timedelta

import numpy
from glob import glob
from GChartWrapper import Line

HOSTS = (
    ('opal.redflavor.com', 'Slicehost'),
    ('garnet.redflavor.com', 'Prgmr'),
    ('topaz.redflavor.com', 'Linode x86_64'),
    ('amethyst.redflavor.com', 'Linode i686'),
    ('onyx.redflavor.com', 'Amazon'),
    ('beryl.redflavor.com', 'Rackspace'),
)

def parse_benchmark_logs():
    results = {}
    date_format = "%Y-%m-%d %H:%M:%S"
    date_re = re.compile("^Date: (.+)$")
    host_re = re.compile("logs/([a-z.]+)-")
    django_re = re.compile("^Ran \d{3} tests in ([\d.]+)s")

    tests = [
        ('django_sqlite3_test', django_re),
        ('django_pgsql_test', django_re),
        ('pgsql_mysql_benchmark', re.compile("^TOTALS\s+([\d.]+)")),
        ('unix_benchmark', re.compile("Index Score\s+([\d.]+)")),
    ]

    for test in tests:
        test_name, test_re = test
        results[test_name] = {}
        for fname in sorted(glob("logs/*-%s.log" % test_name)):
            host = host_re.search(fname).group(1)
            results[test_name][host] = []
            with open(fname) as file:
                previous_date = None
                for line in file:
                    date_match = date_re.search(line)
                    if date_match:
                        date_str = date_match.group(1).split(".")[0]
                        previous_date = datetime.strptime(date_str,
                                                          date_format)
                    else:
                        match = test_re.search(line)
                        if match:
                            vals = (float(match.group(1)), previous_date,)
                            results[test_name][host].append(vals)

    results['unix_benchmark_single'] = {}
    results['unix_benchmark_multiple'] = {}
    for host, host_results in results['unix_benchmark'].items():
        results['unix_benchmark_single'][host] = []
        results['unix_benchmark_multiple'][host] = []
        for index, result in enumerate(host_results):
            if index % 2 == 0:
                results['unix_benchmark_single'][host].append(result)
            else:
                results['unix_benchmark_multiple'][host].append(result)
    
    del results['unix_benchmark']
    results['unix_benchmark_single']

    return results

def graph(results):
    output = []
    sorted_keys = results.keys()
    sorted_keys.sort()
    for test in sorted_keys:
        data = results[test]
        datalist = [data[host[0]] for host in HOSTS]

        plots = []
        dates = []
        max_points = max([len(d) for d in datalist])
        for hostlist in datalist:
            hostplots = []
            hostdates = []
            for hostitem in hostlist:
                hostplots.append(hostitem[0])
                hostdates.append(hostitem[1])
            if len(hostplots) < max_points:
                hostplots.extend([hostlist[-1][0] for i in xrange(max_points-len(hostplots))])
            plots.append(hostplots)
            dates.append(hostdates)
        first_day = dates[0][0]
        last_day = dates[0][-1]
        delta = last_day - first_day
        diff = delta.days*60*60*24 + delta.seconds

        days = []
        days.append(first_day.strftime("%a"))
        days.append((first_day+timedelta(seconds=int(diff*0.2))).strftime("%a"))
        days.append((first_day+timedelta(seconds=int(diff*0.4))).strftime("%a"))
        days.append((first_day+timedelta(seconds=int(diff*0.6))).strftime("%a"))
        days.append((first_day+timedelta(seconds=int(diff*0.8))).strftime("%a"))
        days.append(last_day.strftime("%a"))

        maximum = max([max(d) for d in plots])
        minimum = min([min(d) for d in plots])

        def scale(value, scale=4095):
            return (value - minimum) * scale / abs(maximum - minimum)

        scaled_plots = []
        for hostplots in plots:
            scaled_plots.append([scale(v) for v in hostplots])

        g = Line(scaled_plots, encoding='extended')
        g.legend(*[host[1] for host in HOSTS])
        g.legend_pos('b')
        g.color("edc240", "afd8f8", "cb4b4b", "4da74d", "f8afe8", "4066ed", )
        for i in range(3):
            g.line(2.5, 1, 0)
        g.size(500, 300)
        #g.scale(minimum, maximum)
        g.axes.type('xy')
        labels = range(minimum, maximum, (maximum-minimum)/5)
        g.axes.label(0, *days)
        g.axes.label(1, *labels)
        #g.show()
        print test
        print g
        output.append("%s" % g)
    #print ", ".join(output)

def style(index, value, test, dataset):
    values = []
    for host in HOSTS:
        hostkey, hostname = host
        values.append(dataset[hostkey][test][index])
    maxmatch = max(values) == value
    minmatch = min(values) == value
    if index == 0:
        if "unix_" in test:
            if maxmatch:
                return "background: #e6efc2;"
            if minmatch:
                return "background: #fbe3e4;"
        else:
            if maxmatch:
                return "background: #fbe3e4;"
            if minmatch:
                return "background: #e6efc2;"
    if index == 1:
        if maxmatch:
            return "background: #fbe3e4;"
        if minmatch:
            return "background: #e6efc2;"
    return ""


def table(results):
    sorted_tests = [
        'unix_benchmark_single',
        'unix_benchmark_multiple',
        'pgsql_mysql_benchmark',
        'django_pgsql_test',
        'django_sqlite3_test',
    ]
    output = []
    output.append("  <tr>")
    output.append("    <th>&nbsp;</th>")
    for i, test in enumerate(sorted_tests):
        output.append("    <th title=\"%s\">%s <span style=\"text-decoration:overline;\">x</span></th>" % (test, i+1))
        output.append("    <th title=\"%s\">%s &sigma;</th>" % (test, i+1))
    output.append("  </tr>")

    calculations = {}

    for host in HOSTS:
        hostkey, hostname = host
        calculations[hostkey] = {}
        for test in sorted_tests:
            scores_and_times = results[test][hostkey]
            scores = [s[0] for s in scores_and_times]
            avg = sum(scores, 0.0) / len(scores)
            std = numpy.std(scores)
            calculations[hostkey][test] = (avg, std)

    for host in HOSTS:
        hostkey, hostname = host
        output.append("  <tr>")
        output.append("    <td>%s</td>" % hostname)
        for test in sorted_tests:
            avg, std = calculations[hostkey][test]
            avg_style = style(0, avg, test, calculations)
            std_style = style(1, std, test, calculations)
            output.append("    <td style=\"text-align: right; %s\">%s</td>" % (avg_style, int(round(avg))))
            output.append("    <td style=\"text-align: right; %s\">%s</td>" % (std_style, round(std, 2)))
        output.append("  </tr>")

    print "\n".join(output)



if __name__ == "__main__":
    results = parse_benchmark_logs()
    #graph(results)
    table(results)

########NEW FILE########
__FILENAME__ = pgsqlconf
DATABASE_ENGINE = 'postgresql_psycopg2'
DATABASE_NAME = 'test'
DATABASE_USER = 'testuser'
DATABASE_PASSWORD = 'n0ns3curepWd'

########NEW FILE########
__FILENAME__ = pings
import re

def parse(str):
    values = []
    p = re.compile("\s*([\w ,.]+):\s+\w+\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)")

    for line in [l for l in str.split("\n") if len(l)]:
        matches = p.search(line)
        city = matches.group(1)
        avg_ms = float(matches.group(3).replace(",", ""))
        values.append((city, avg_ms,))
    return values


prgmr = parse("""
 Florida, U.S.A.:       Okay    89.5    89.8    90.0
 Hong Kong, China:      Okay    228.3   228.5   228.8
 Sydney, Australia:     Okay    162.9   167.1   192.3
 New York, U.S.A.:      Okay    80.9    81.1    81.3
 Stockholm, Sweden:     Okay    175.6   178.2   182.5
 Santa Clara, U.S.A.:   Okay    5.3     5.6     5.9
 Vancouver, Canada:     Okay    23.3    23.6    24.7
 Krakow, Poland:        Okay    189.6   190.7   191.8
 London, United Kingdom:        Okay    149.6   150.1   150.4
 Madrid, Spain:         Okay    173.4   174.3   178.6
 Cagliari, Italy:       Okay    219.4   221.2   222.1
 Singapore, Singapore:  Okay    179.4   180.4   181.0
 Austin, U.S.A.:        Okay    201.1   201.3   201.5
 Cologne, Germany:      Okay    177.4   177.5   177.8
 Munchen, Germany:      Okay    180.1   180.5   180.9
 Amsterdam, Netherlands:        Okay    165.4   165.5   165.6
 Paris, France:         Okay    156.7   156.8   156.9
 Shanghai, China:       Okay    207.1   208.0   209.0
 Melbourne, Australia:  Okay    168.4   171.8   176.8
 Copenhagen, Denmark:   Okay    191.3   191.6   192.1
 Lille, France:         Okay    157.7   158.7   165.8
 San Francisco, U.S.A.:         Okay    2.6     2.8     3.0
 Chicago, U.S.A.:       Okay    55.3    55.9    57.4
 Zurich, Switzerland:   Okay    173.4   173.8   175.1
 Johannesburg, South Africa:    Okay    770.5   838.6   885.1
 Mumbai, India:         Okay    249.8   251.4   255.9
 Nagano, Japan:         Okay    116.7   117.1   117.4
 Haifa, Israel:         Okay    227.7   236.3   241.8
 Auckland, New Zealand:         Okay    245.2   247.5   248.8
 Groningen, Netherlands:        Okay    169.1   169.5   170.0
 Antwerp, Belgium:      Okay    163.7   164.2   164.6
 Dublin, Ireland:       Okay    158.3   158.7   159.0
 Moscow, Russia:        Okay    227.7   228.0   228.4
 Oslo, Norway:  Okay    200.1   200.4   201.1
""")

linode = parse("""
 Florida, U.S.A.:       Okay    33.0    34.0    37.2
 Hong Kong, China:      Okay    288.2   288.4   288.9
 Sydney, Australia:     Okay    236.8   237.6   238.9
 New York, U.S.A.:      Okay    10.3    10.7    11.5
 Stockholm, Sweden:     Okay    118.3   118.8   119.5
 Santa Clara, U.S.A.:   Okay    72.9    73.3    73.6
 Vancouver, Canada:     Okay    76.2    76.4    76.7
 Krakow, Poland:        Okay    108.8   109.5   110.8
 London, United Kingdom:        Okay    76.9    77.4    77.8
 Madrid, Spain:         Okay    94.7    95.4    95.8
 Cagliari, Italy:       Okay    131.5   134.7   136.6
 Singapore, Singapore:  Okay    265.4   266.4   267.3
 Austin, U.S.A.:        Okay    131.8   131.9   132.1
 Cologne, Germany:      Okay    97.9    98.0    98.2
 Munchen, Germany:      Okay    102.1   102.3   102.7
 Amsterdam, Netherlands:        Okay    85.5    85.7    85.9
 Paris, France:         Okay    84.4    84.6    84.8
 Shanghai, China:       Okay    275.2   276.4   278.0
 Melbourne, Australia:  Okay    242.0   243.3   245.8
 Copenhagen, Denmark:   Okay    92.6    92.8    93.0
 Lille, France:         Okay    91.5    93.7    102.6
 San Francisco, U.S.A.:         Okay    77.2    77.5    77.9
 Chicago, U.S.A.:       Okay    21.7    22.1    22.8
 Zurich, Switzerland:   Okay    100.3   101.6   103.6
 Johannesburg, South Africa:    Okay    1,071.6         1,157.3         1,200.6
 Mumbai, India:         Okay    197.3   198.5   201.2
 Nagano, Japan:         Okay    200.1   208.9   211.7
 Haifa, Israel:         Okay    154.8   156.5   158.2
 Auckland, New Zealand:         Okay    206.8   208.5   212.5
 Groningen, Netherlands:        Okay    95.3    95.7    96.2
 Antwerp, Belgium:      Okay    93.0    93.2    93.6
 Dublin, Ireland:       Okay    82.4    82.8    83.0
 Moscow, Russia:        Okay    152.6   152.8   153.1
 Oslo, Norway:  Okay    100.1   100.3   100.7

""")

slicehost = parse("""
 Florida, U.S.A.:       Okay    44.3    44.5    44.6
 Hong Kong, China:      Okay    211.8   212.1   213.0
 Sydney, Australia:     Okay    209.0   209.3   210.6
 New York, U.S.A.:      Okay    42.6    43.4    47.0
 Stockholm, Sweden:     Okay    140.8   140.9   141.0
 Santa Clara, U.S.A.:   Okay    47.2    48.4    55.0
 Vancouver, Canada:     Okay    50.8    51.1    51.3
 Krakow, Poland:        Okay    139.4   140.7   143.9
 London, United Kingdom:        Okay    96.3    97.1    97.8
 Madrid, Spain:         Okay    133.6   134.3   135.4
 Cagliari, Italy:       Okay    166.7   167.6   168.6
 Singapore, Singapore:  Okay    240.2   240.4   240.9
 Austin, U.S.A.:        Okay    36.3    36.5    36.7
 Cologne, Germany:      Okay    119.7   119.8   120.0
 Munchen, Germany:      Okay    122.1   122.4   122.8
 Amsterdam, Netherlands:        Okay    109.3   111.0   113.7
 Paris, France:         Okay    114.8   114.9   115.1
 Shanghai, China:       Okay    325.3   389.8   433.5
 Melbourne, Australia:  Okay    209.9   212.0   216.9
 Copenhagen, Denmark:   Okay    127.4   127.6   128.0
 Lille, France:         Okay    121.1   122.6   127.7
 San Francisco, U.S.A.:         Okay    45.6    45.9    46.1
 Chicago, U.S.A.:       Okay    6.2     6.6     6.9
 Zurich, Switzerland:   Okay    136.8   137.4   138.7
 Johannesburg, South Africa:    Okay    996.1   1,074.2         1,126.0
 Mumbai, India:         Okay    242.1   243.0   245.2
 Nagano, Japan:         Okay    184.3   189.4   200.6
 Haifa, Israel:         Okay    166.5   171.7   179.1
 Auckland, New Zealand:         Okay    179.2   179.7   180.3
 Groningen, Netherlands:        Okay    111.4   111.9   112.3
 Antwerp, Belgium:      Okay    109.4   109.6   109.9
 Dublin, Ireland:       Okay    107.7   108.2   108.7
 Moscow, Russia:        Okay    167.1   167.3   167.7
 Oslo, Norway:  Okay    145.7   145.9   146.4
""")

########NEW FILE########
__FILENAME__ = sqlite3conf
DATABASE_ENGINE = 'sqlite3'

########NEW FILE########
__FILENAME__ = sysinfo
#!/usr/bin/env python
import os

def echo_and_run(cmd):
    print "# %s" % cmd
    os.system(cmd)
    print ""

echo_and_run('uname -nrmo')
echo_and_run('grep "MemTotal" /proc/meminfo')
echo_and_run('grep -m 4 -e "model name" -e "MHz" -e "cache size" -e "bogomips" /proc/cpuinfo')
echo_and_run('grep "processor" /proc/cpuinfo | wc -l')

########NEW FILE########
