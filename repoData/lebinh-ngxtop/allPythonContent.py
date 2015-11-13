__FILENAME__ = config_parser
"""
Nginx config parser and pattern builder.
"""
import os
import re
import subprocess

from pyparsing import Literal, Word, ZeroOrMore, OneOrMore, Group, \
    printables, quotedString, pythonStyleComment, removeQuotes

from .utils import choose_one, error_exit


REGEX_SPECIAL_CHARS = r'([\.\*\+\?\|\(\)\{\}\[\]])'
REGEX_LOG_FORMAT_VARIABLE = r'\$([a-z0-9\_]+)'
LOG_FORMAT_COMBINED = '$remote_addr - $remote_user [$time_local] ' \
                      '"$request" $status $body_bytes_sent ' \
                      '"$http_referer" "$http_user_agent"'
LOG_FORMAT_COMMON   = '$remote_addr - $remote_user [$time_local] ' \
                      '"$request" $status $body_bytes_sent ' \
                      '"$http_x_forwarded_for"'

# common parser element
semicolon = Literal(';').suppress()
# nginx string parameter can contain any character except: { ; " '
parameter = Word(''.join(c for c in printables if c not in set('{;"\'')))
# which can also be quoted
parameter = parameter | quotedString.setParseAction(removeQuotes)


def detect_config_path():
    """
    Get nginx configuration file path based on `nginx -V` output
    :return: detected nginx configuration file path
    """
    try:
        proc = subprocess.Popen(['nginx', '-V'], stderr=subprocess.PIPE)
    except OSError:
        error_exit('Access log file or format was not set and nginx config file cannot be detected. ' +
                   'Perhaps nginx is not in your PATH?')

    stdout, stderr = proc.communicate()
    version_output = stderr.decode('utf-8')
    conf_path_match = re.search(r'--conf-path=(\S*)', version_output)
    if conf_path_match is not None:
        return conf_path_match.group(1)

    prefix_match = re.search(r'--prefix=(\S*)', version_output)
    if prefix_match is not None:
        return prefix_match.group(1) + '/conf/nginx.conf'
    return '/etc/nginx/nginx.conf'


def get_access_logs(config):
    """
    Parse config for access_log directives
    :return: iterator over ('path', 'format name') tuple of found directives
    """
    access_log = Literal("access_log") + ZeroOrMore(parameter) + semicolon
    access_log.ignore(pythonStyleComment)

    for directive in access_log.searchString(config).asList():
        path = directive[1]
        if path == 'off' or path.startswith('syslog:'):
            # nothing to process here
            continue

        format_name = 'combined'
        if len(directive) > 2 and '=' not in directive[2]:
            format_name = directive[2]

        yield path, format_name


def get_log_formats(config):
    """
    Parse config for log_format directives
    :return: iterator over ('format name', 'format string') tuple of found directives
    """
    # log_format name [params]
    log_format = Literal('log_format') + parameter + Group(OneOrMore(parameter)) + semicolon
    log_format.ignore(pythonStyleComment)

    for directive in log_format.searchString(config).asList():
        name = directive[1]
        format_string = ''.join(directive[2])
        yield name, format_string


def detect_log_config(arguments):
    """
    Detect access log config (path and format) of nginx. Offer user to select if multiple access logs are detected.
    :return: path and format of detected / selected access log
    """
    config = arguments['--config']
    if config is None:
        config = detect_config_path()
    if not os.path.exists(config):
        error_exit('Nginx config file not found: %s' % config)

    with open(config) as f:
        config_str = f.read()
    access_logs = dict(get_access_logs(config_str))
    if not access_logs:
        error_exit('Access log file is not provided and ngxtop cannot detect it from your config file (%s).' % config)

    log_formats = dict(get_log_formats(config_str))
    if len(access_logs) == 1:
        log_path, format_name = access_logs.items()[0]
        if format_name == 'combined':
            return log_path, LOG_FORMAT_COMBINED
        if format_name not in log_formats:
            error_exit('Incorrect format name set in config for access log file "%s"' % log_path)
        return log_path, log_formats[format_name]

    # multiple access logs configured, offer to select one
    print('Multiple access logs detected in configuration:')
    log_path = choose_one(access_logs.keys(), 'Select access log file to process: ')
    format_name = access_logs[log_path]
    if format_name not in log_formats:
        error_exit('Incorrect format name set in config for access log file "%s"' % log_path)
    return log_path, log_formats[format_name]


def build_pattern(log_format):
    """
    Build regular expression to parse given format.
    :param log_format: format string to parse
    :return: regular expression to parse given format
    """
    if log_format == 'combined':
        log_format = LOG_FORMAT_COMBINED
    elif log_format == 'common':
        log_format = LOG_FORMAT_COMMON
    pattern = re.sub(REGEX_SPECIAL_CHARS, r'\\\1', log_format)
    pattern = re.sub(REGEX_LOG_FORMAT_VARIABLE, '(?P<\\1>.*)', pattern)
    return re.compile(pattern)


def extract_variables(log_format):
    """
    Extract all variables from a log format string.
    :param log_format: format string to extract
    :return: iterator over all variables in given format string
    """
    if log_format == 'combined':
        log_format = LOG_FORMAT_COMBINED
    for match in re.findall(REGEX_LOG_FORMAT_VARIABLE, log_format):
        yield match


########NEW FILE########
__FILENAME__ = ngxtop
"""ngxtop - ad-hoc query for nginx access log.

Usage:
    ngxtop [options]
    ngxtop [options] (print|top|avg|sum) <var> ...
    ngxtop info
    ngxtop [options] query <query> ...

Options:
    -l <file>, --access-log <file>  access log file to parse.
    -f <format>, --log-format <format>  log format as specify in log_format directive. [default: combined]
    --no-follow  ngxtop default behavior is to ignore current lines in log
                     and only watch for new lines as they are written to the access log.
                     Use this flag to tell ngxtop to process the current content of the access log instead.
    -t <seconds>, --interval <seconds>  report interval when running in follow mode [default: 2.0]

    -g <var>, --group-by <var>  group by variable [default: request_path]
    -w <var>, --having <expr>  having clause [default: 1]
    -o <var>, --order-by <var>  order of output for default query [default: count]
    -n <number>, --limit <number>  limit the number of records included in report for top command [default: 10]
    -a <exp> ..., --a <exp> ...  add exp (must be aggregation exp: sum, avg, min, max, etc.) into output

    -v, --verbose  more verbose output
    -d, --debug  print every line and parsed record
    -h, --help  print this help message.
    --version  print version information.

    Advanced / experimental options:
    -c <file>, --config <file>  allow ngxtop to parse nginx config file for log format and location.
    -i <filter-expression>, --filter <filter-expression>  filter in, records satisfied given expression are processed.
    -p <filter-expression>, --pre-filter <filter-expression> in-filter expression to check in pre-parsing phase.

Examples:
    All examples read nginx config file for access log location and format.
    If you want to specify the access log file and / or log format, use the -f and -a options.

    "top" like view of nginx requests
    $ ngxtop

    Top 10 requested path with status 404:
    $ ngxtop top request_path --filter 'status == 404'

    Top 10 requests with highest total bytes sent
    $ ngxtop --order-by 'avg(bytes_sent) * count'

    Top 10 remote address, e.g., who's hitting you the most
    $ ngxtop --group-by remote_addr

    Print requests with 4xx or 5xx status, together with status and http referer
    $ ngxtop -i 'status >= 400' print request status http_referer

    Average body bytes sent of 200 responses of requested path begin with 'foo':
    $ ngxtop avg bytes_sent --filter 'status == 200 and request_path.startswith("foo")'

    Analyze apache access log from remote machine using 'common' log format
    $ ssh remote tail -f /var/log/apache2/access.log | ngxtop -f common
"""
from __future__ import print_function
import atexit
from contextlib import closing
import curses
import logging
import os
import sqlite3
import time
import sys
import signal

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from docopt import docopt
import tabulate

from .config_parser import detect_log_config, detect_config_path, extract_variables, build_pattern
from .utils import error_exit


DEFAULT_QUERIES = [
    ('Summary:',
     '''SELECT
       count(1)                                    AS count,
       avg(bytes_sent)                             AS avg_bytes_sent,
       count(CASE WHEN status_type = 2 THEN 1 END) AS '2xx',
       count(CASE WHEN status_type = 3 THEN 1 END) AS '3xx',
       count(CASE WHEN status_type = 4 THEN 1 END) AS '4xx',
       count(CASE WHEN status_type = 5 THEN 1 END) AS '5xx'
     FROM log
     ORDER BY %(--order-by)s DESC
     LIMIT %(--limit)s'''),

    ('Detailed:',
     '''SELECT
       %(--group-by)s,
       count(1)                                    AS count,
       avg(bytes_sent)                             AS avg_bytes_sent,
       count(CASE WHEN status_type = 2 THEN 1 END) AS '2xx',
       count(CASE WHEN status_type = 3 THEN 1 END) AS '3xx',
       count(CASE WHEN status_type = 4 THEN 1 END) AS '4xx',
       count(CASE WHEN status_type = 5 THEN 1 END) AS '5xx'
     FROM log
     GROUP BY %(--group-by)s
     HAVING %(--having)s
     ORDER BY %(--order-by)s DESC
     LIMIT %(--limit)s''')
]

DEFAULT_FIELDS = set(['status_type', 'bytes_sent'])


# ======================
# generator utilities
# ======================
def follow(the_file):
    """
    Follow a given file and yield new lines when they are available, like `tail -f`.
    """
    with open(the_file) as f:
        f.seek(0, 2)  # seek to eof
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)  # sleep briefly before trying again
                continue
            yield line


def map_field(field, func, dict_sequence):
    """
    Apply given function to value of given key in every dictionary in sequence and
    set the result as new value for that key.
    """
    for item in dict_sequence:
        try:
            item[field] = func(item.get(field, None))
            yield item
        except ValueError:
            pass


def add_field(field, func, dict_sequence):
    """
    Apply given function to the record and store result in given field of current record.
    Do nothing if record already contains given field.
    """
    for item in dict_sequence:
        if field not in item:
            item[field] = func(item)
        yield item


def trace(sequence, phase=''):
    for item in sequence:
        logging.debug('%s:\n%s', phase, item)
        yield item


# ======================
# Access log parsing
# ======================
def parse_request_path(record):
    if 'request_uri' in record:
        uri = record['request_uri']
    elif 'request' in record:
        uri = ' '.join(record['request'].split(' ')[1:-1])
    else:
        uri = None
    return urlparse.urlparse(uri).path if uri else None


def parse_status_type(record):
    return record['status'] // 100 if 'status' in record else None


def to_int(value):
    return int(value) if value and value != '-' else 0


def to_float(value):
    return float(value) if value and value != '-' else 0.0


def parse_log(lines, pattern):
    matches = (pattern.match(l) for l in lines)
    records = (m.groupdict() for m in matches if m is not None)
    records = map_field('status', to_int, records)
    records = add_field('status_type', parse_status_type, records)
    records = add_field('bytes_sent', lambda r: r['body_bytes_sent'], records)
    records = map_field('bytes_sent', to_int, records)
    records = map_field('request_time', to_float, records)
    records = add_field('request_path', parse_request_path, records)
    return records


# =================================
# Records and statistic processor
# =================================
class SQLProcessor(object):
    def __init__(self, report_queries, fields, index_fields=None):
        self.begin = False
        self.report_queries = report_queries
        self.index_fields = index_fields if index_fields is not None else []
        self.column_list = ','.join(fields)
        self.holder_list = ','.join(':%s' % var for var in fields)
        self.conn = sqlite3.connect(':memory:')
        self.init_db()

    def process(self, records):
        self.begin = time.time()
        insert = 'insert into log (%s) values (%s)' % (self.column_list, self.holder_list)
        logging.info('sqlite insert: %s', insert)
        with closing(self.conn.cursor()) as cursor:
            for r in records:
                cursor.execute(insert, r)

    def report(self):
        if not self.begin:
            return ''
        count = self.count()
        duration = time.time() - self.begin
        status = 'running for %.0f seconds, %d records processed: %.2f req/sec'
        output = [status % (duration, count, count / duration)]
        with closing(self.conn.cursor()) as cursor:
            for query in self.report_queries:
                if isinstance(query, tuple):
                    label, query = query
                else:
                    label = ''
                cursor.execute(query)
                columns = (d[0] for d in cursor.description)
                result = tabulate.tabulate(cursor.fetchall(), headers=columns, tablefmt='orgtbl', floatfmt='.3f')
                output.append('%s\n%s' % (label, result))
        return '\n\n'.join(output)

    def init_db(self):
        create_table = 'create table log (%s)' % self.column_list
        with closing(self.conn.cursor()) as cursor:
            logging.info('sqlite init: %s', create_table)
            cursor.execute(create_table)
            for idx, field in enumerate(self.index_fields):
                sql = 'create index log_idx%d on log (%s)' % (idx, field)
                logging.info('sqlite init: %s', sql)
                cursor.execute(sql)

    def count(self):
        with closing(self.conn.cursor()) as cursor:
            cursor.execute('select count(1) from log')
            return cursor.fetchone()[0]


# ===============
# Log processing
# ===============
def process_log(lines, pattern, processor, arguments):
    pre_filer_exp = arguments['--pre-filter']
    if pre_filer_exp:
        lines = (line for line in lines if eval(pre_filer_exp, {}, dict(line=line)))

    records = parse_log(lines, pattern)

    filter_exp = arguments['--filter']
    if filter_exp:
        records = (r for r in records if eval(filter_exp, {}, r))

    processor.process(records)
    print(processor.report())  # this will only run when start in --no-follow mode


def build_processor(arguments):
    fields = arguments['<var>']
    if arguments['print']:
        label = ', '.join(fields) + ':'
        selections = ', '.join(fields)
        query = 'select %s from log group by %s' % (selections, selections)
        report_queries = [(label, query)]
    elif arguments['top']:
        limit = int(arguments['--limit'])
        report_queries = []
        for var in fields:
            label = 'top %s' % var
            query = 'select %s, count(1) as count from log group by %s order by count desc limit %d' % (var, var, limit)
            report_queries.append((label, query))
    elif arguments['avg']:
        label = 'average %s' % fields
        selections = ', '.join('avg(%s)' % var for var in fields)
        query = 'select %s from log' % selections
        report_queries = [(label, query)]
    elif arguments['sum']:
        label = 'sum %s' % fields
        selections = ', '.join('sum(%s)' % var for var in fields)
        query = 'select %s from log' % selections
        report_queries = [(label, query)]
    elif arguments['query']:
        report_queries = arguments['<query>']
        fields = arguments['<fields>']
    else:
        report_queries = [(name, query % arguments) for name, query in DEFAULT_QUERIES]
        fields = DEFAULT_FIELDS.union(set([arguments['--group-by']]))

    for label, query in report_queries:
        logging.info('query for "%s":\n %s', label, query)

    processor_fields = []
    for field in fields:
        processor_fields.extend(field.split(','))

    processor = SQLProcessor(report_queries, processor_fields)
    return processor


def build_source(access_log, arguments):
    # constructing log source
    if access_log == 'stdin':
        lines = sys.stdin
    elif arguments['--no-follow']:
        lines = open(access_log)
    else:
        lines = follow(access_log)
    return lines


def setup_reporter(processor, arguments):
    if arguments['--no-follow']:
        return

    scr = curses.initscr()
    atexit.register(curses.endwin)

    def print_report(sig, frame):
        output = processor.report()
        scr.erase()
        try:
            scr.addstr(output)
        except curses.error:
            pass
        scr.refresh()

    signal.signal(signal.SIGALRM, print_report)
    interval = float(arguments['--interval'])
    signal.setitimer(signal.ITIMER_REAL, 0.1, interval)


def process(arguments):
    access_log = arguments['--access-log']
    log_format = arguments['--log-format']
    if access_log is None and not sys.stdin.isatty():
        # assume logs can be fetched directly from stdin when piped
        access_log = 'stdin'
    if access_log is None:
        access_log, log_format = detect_log_config(arguments)

    logging.info('access_log: %s', access_log)
    logging.info('log_format: %s', log_format)
    if access_log != 'stdin' and not os.path.exists(access_log):
        error_exit('access log file "%s" does not exist' % access_log)

    if arguments['info']:
        print('nginx configuration file:\n ', detect_config_path())
        print('access log file:\n ', access_log)
        print('access log format:\n ', log_format)
        print('available variables:\n ', ', '.join(sorted(extract_variables(log_format))))
        return

    source = build_source(access_log, arguments)
    pattern = build_pattern(log_format)
    processor = build_processor(arguments)
    setup_reporter(processor, arguments)
    process_log(source, pattern, processor, arguments)


def main():
    args = docopt(__doc__, version='xstat 0.1')

    log_level = logging.WARNING
    if args['--verbose']:
        log_level = logging.INFO
    if args['--debug']:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    logging.debug('arguments:\n%s', args)

    try:
        process(args)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = utils
import sys


def choose_one(choices, prompt):
    for idx, choice in enumerate(choices):
        print('%d. %s' % (idx + 1, choice))
    selected = None
    while not selected or selected <= 0 or selected > len(choices):
        selected = raw_input(prompt)
        try:
            selected = int(selected)
        except ValueError:
            selected = None
    return choices[selected - 1]


def error_exit(msg, status=1):
    sys.stderr.write('Error: %s\n' % msg)
    sys.exit(status)
########NEW FILE########
__FILENAME__ = test_config_parser
from ngxtop import config_parser


def test_get_log_formats():
    config = '''
        http {
            # ubuntu default, log_format on multiple lines
            log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                              "$status $body_bytes_sent '$http_referer' "
                              '"$http_user_agent" "$http_x_forwarded_for"';

            # name can also be quoted, and format don't always have to
            log_format  'te st'  $remote_addr;
        }
    '''
    formats = dict(config_parser.get_log_formats(config))
    assert 'main' in formats
    assert "'$http_referer'" in formats['main']
    assert 'te st' in formats


def test_get_access_logs_no_format():
    config = '''
        http {
            # ubuntu default
            access_log /var/log/nginx/access.log;

            # syslog is a valid access log, but we can't follow it
            access_log syslog:server=address combined;

            # commented
            # access_log commented;

            server {
                location / {
                    # has parameter with default format
                    access_log /path/to/log gzip=1;
                }
            }
        }
    '''
    logs = dict(config_parser.get_access_logs(config))
    assert len(logs) == 2
    assert logs['/var/log/nginx/access.log'] == 'combined'
    assert logs['/path/to/log'] == 'combined'


def test_access_logs_with_format_name():
    config = '''
        http {
            access_log /path/to/main.log main gzip=5 buffer=32k flush=1m;
            server {
                access_log /path/to/test.log 'te st';
            }
        }
    '''
    logs = dict(config_parser.get_access_logs(config))
    assert len(logs) == 2
    assert logs['/path/to/main.log'] == 'main'
    assert logs['/path/to/test.log'] == 'te st'

########NEW FILE########
