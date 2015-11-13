__FILENAME__ = lib
import fileinput
from re import compile
from django.conf import settings

from texttable import Texttable
from progressbar import ProgressBar, Percentage, Bar

from django.core.urlresolvers import resolve, Resolver404

PATTERN = r"""^([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9:]{8},[0-9]{3}) (GET|POST|PUT|DELETE|HEAD) "(.*)" \((.*)\) (.*?) \((\d+)q, (.*?)\)"""

CACHED_VIEWS = {}

IGNORE_PATHS = getattr(settings, 'TIMELOG_IGNORE_URIS', ())

def count_lines_in(filename):
    "Count lines in a file"
    f = open(filename)                  
    lines = 0
    buf_size = 1024 * 1024
    read_f = f.read # loop optimization
    
    buf = read_f(buf_size)
    while buf:
        lines += buf.count('\n')
        buf = read_f(buf_size)
    
    return lines

def view_name_from(path):
    "Resolve a path to the full python module name of the related view function"
    try:
        return CACHED_VIEWS[path]
        
    except KeyError:
        view = resolve(path)
        module = path
        name = ''
        if hasattr(view.func, '__module__'):
            module = resolve(path).func.__module__
        if hasattr(view.func, '__name__'):
            name = resolve(path).func.__name__
        
        view =  "%s.%s" % (module, name)
        CACHED_VIEWS[path] = view
        return view

def generate_table_from(data):
    "Output a nicely formatted ascii table"
    table = Texttable(max_width=120)
    table.add_row(["view", "method", "status", "count", "minimum", "maximum", "mean", "stdev", "queries", "querytime"]) 
    table.set_cols_align(["l", "l", "l", "r", "r", "r", "r", "r", "r", "r"])

    for item in sorted(data):
        mean = round(sum(data[item]['times'])/data[item]['count'], 3)

        mean_sql = round(sum(data[item]['sql'])/data[item]['count'], 3)
        mean_sqltime = round(sum(data[item]['sqltime'])/data[item]['count'], 3)
        
        sdsq = sum([(i - mean) ** 2 for i in data[item]['times']])
        try:
            stdev = '%.2f' % ((sdsq / (len(data[item]['times']) - 1)) ** .5)
        except ZeroDivisionError:
            stdev = '0.00'

        minimum = "%.2f" % min(data[item]['times'])
        maximum = "%.2f" % max(data[item]['times'])
        table.add_row([data[item]['view'], data[item]['method'], data[item]['status'], data[item]['count'], minimum, maximum, '%.3f' % mean, stdev, mean_sql, mean_sqltime])

    return table.draw()

def analyze_log_file(logfile, pattern, reverse_paths=True, progress=True):
    "Given a log file and regex group and extract the performance data"
    if progress:
        lines = count_lines_in(logfile)
        pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=lines+1).start()
        counter = 0
    
    data = {}
    
    compiled_pattern = compile(pattern)
    for line in fileinput.input([logfile]):
        
        if progress:
            counter = counter + 1
        
        parsed = compiled_pattern.findall(line)[0]
        date = parsed[0]
        method = parsed[1]
        path = parsed[2]
        status = parsed[3]
        time = parsed[4]
        sql = parsed[5]
        sqltime = parsed[6]

        try:
            ignore = False
            for ignored_path in IGNORE_PATHS:
                compiled_path = compile(ignored_path)
                if compiled_path.match(path):
                    ignore = True
            if not ignore:
                if reverse_paths:
                    view = view_name_from(path)
                else:
                    view = path
                key = "%s-%s-%s" % (view, status, method)
                try:
                    data[key]['count'] = data[key]['count'] + 1
                    data[key]['times'].append(float(time))
                    data[key]['sql'].append(int(sql))
                    data[key]['sqltime'].append(float(sqltime))
                except KeyError:
                    data[key] = {
                        'count': 1,
                        'status': status,
                        'view': view,
                        'method': method,
                        'times': [float(time)],
                        'sql': [int(sql)],
                        'sqltime': [float(sqltime)],
                    }
        except Resolver404:
            pass
        
        if progress:
            pbar.update(counter)
    
    if progress:
        pbar.finish()
    
    return data

########NEW FILE########
__FILENAME__ = analyze_timelog
from optparse import make_option

from django.core.management.base import BaseCommand
from django.conf import settings

from timelog.lib import generate_table_from, analyze_log_file, PATTERN


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--file',
            dest='file',
            default=settings.TIMELOG_LOG,
            help='Specify file to use'),
        make_option('--noreverse',
            dest='reverse',
            action='store_false',
            default=True,
            help='Show paths instead of views'),
        )

    def handle(self, *args, **options):
        # --date-from YY-MM-DD
        #   specify a date filter start
        #   default to first date in file
        # --date-to YY-MM-DD
        #   specify a date filter end
        #   default to now

        LOGFILE = options.get('file')

        try:
            data = analyze_log_file(LOGFILE, PATTERN, reverse_paths=options.get('reverse'))
        except IOError:
            print "File not found"
            exit(2)

        print generate_table_from(data)

########NEW FILE########
__FILENAME__ = middleware
import time
import logging
from django.db import connection
from django.utils.encoding import smart_str

logger = logging.getLogger(__name__)


class TimeLogMiddleware(object):

    def process_request(self, request):
        request._start = time.time()

    def process_response(self, request, response):
        # if an exception is occured in a middleware listed
        # before TimeLogMiddleware then request won't have '_start' attribute
        # and the original traceback will be lost (original exception will be
        # replaced with AttributeError)

        sqltime = 0.0

        for q in connection.queries:
            sqltime += float(getattr(q, 'time', 0.0))

        if hasattr(request, '_start'):
            d = {
                'method': request.method,
                'time': time.time() - request._start,
                'code': response.status_code,
                'url': smart_str(request.path_info),
                'sql': len(connection.queries),
                'sqltime': sqltime,
            }
            msg = '%(method)s "%(url)s" (%(code)s) %(time).2f (%(sql)dq, %(sqltime).4f)' % d
            logger.info(msg)
        return response

########NEW FILE########
