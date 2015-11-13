__FILENAME__ = 011_to_012
#!/usr/bin/env python

"Converts a timed-0.11-style log file to a timed-0.12-style log file."

import timed
import yaml

def read():
  data = open(timed.log_file).read()
  if not data:
    return []
  
  return yaml.safe_load(data)
 
logs = read()

timed.save(logs)
########NEW FILE########
__FILENAME__ = client
"Timed: a command-line time tracker."

__name__ = 'client'

import sys
import os.path
import datetime
from termcolor import colored

from timed import server
from timed import cmdapp

now = datetime.datetime.now

def main():
  cmdapp.main(name='timed', desc=__doc__, config={
    'logfile': os.path.expanduser('~/.timed'),
    'time_format': '%H:%M on %d %b %Y'})

@cmdapp.cmd
def summary(logfile, time_format):
  "show a summary of all projects"

  def output(summary):
    width = max([len(p[0]) for p in summary]) + 3
    print '\n'.join([
      "%s%s%s" % (p[0], ' ' * (width - len(p[0])),
        colored(minutes_to_txt(p[1]), 'red')) for p in summary])

  output(server.summarize(read(logfile, time_format, only_elapsed=True)))

@cmdapp.cmd
@cmdapp.default
def status(logfile, time_format):
  "show current status"

  try:
    r = read(logfile, time_format)[-1]
    if r[1][1]:
      return summary(logfile, time_format)
    else:
      print "working on %s" % colored(r[0], attrs=['bold'])
      print "  since    %s" % colored(
        server.date_to_txt(r[1][0], time_format), 'green')
      print "  to now,  %s" % colored(
        server.date_to_txt(now(), time_format), 'green')
      print "        => %s elapsed" % colored(time_elapsed(r[1][0]), 'red')
  except IndexError:
    return cmdapp.help()

@cmdapp.cmd
def start(project, logfile, time_format):
  "start tracking for <project>"

  records = read(logfile, time_format)
  if records and not records[-1][1][1]:
    print "error: there is a project already active"
    return

  write(server.start(project, records), logfile, time_format)

  print "starting work on %s" % colored(project, attrs=['bold'])
  print "  at %s" % colored(server.date_to_txt(now(), time_format), 'green')

@cmdapp.cmd
def stop(logfile, time_format):
  "stop tracking for the active project"

  def save_and_output(records):
    records = server.stop(records)
    write(records, logfile, time_format)

    def output(r):
      print "worked on %s" % colored(r[0], attrs=['bold'])
      print "  from    %s" % colored(
        server.date_to_txt(r[1][0], time_format), 'green')
      print "  to now, %s" % colored(
        server.date_to_txt(r[1][1], time_format), 'green')
      print "       => %s elapsed" % colored(
        time_elapsed(r[1][0], r[1][1]), 'red')

    output(records[-1])

  save_and_output(read(logfile, time_format))

@cmdapp.cmd
def parse(logfile, time_format):
  "parses a stream with text formatted as a Timed logfile and shows a summary"

  records = [server.record_from_txt(line, only_elapsed=True,
    time_format=time_format) for line in sys.stdin.readlines()]

  # TODO: make this code better.
  def output(summary):
    width = max([len(p[0]) for p in summary]) + 3
    print '\n'.join([
      "%s%s%s" % (p[0], ' ' * (width - len(p[0])),
        colored(minutes_to_txt(p[1]), 'red')) for p in summary])

  output(server.summarize(records))

@cmdapp.cmd
def projects(logfile, time_format):
  "prints a newline-separated list of all projects"

  print '\n'.join(server.list_projects(read(logfile, time_format)))

def read(logfile, time_format, only_elapsed=False):
  return [server.record_from_txt(line, only_elapsed=only_elapsed,
    time_format=time_format) for line in open(
      os.path.expanduser(logfile) ,'a+').readlines()]

def write(records, logfile, time_format):
  try:
    open(logfile, 'w').write('\n'.join(
      [server.record_to_txt(record, time_format) for record in records]))
  except IOError:
    print "error: could not open log file for writing: %s" % logfile

def time_elapsed(start, end=None):
  return minutes_to_txt(server.minutes_elapsed(start, end))

def minutes_to_txt(delta):
  hour = delta / 60
  min = delta - 60 * hour
  return "%sh%sm" % (hour, min)

########NEW FILE########
__FILENAME__ = cmdapp
import sys

program = {}
handlers = {}

def main(name, desc, config={}):
  program['name'] = name
  program['desc'] = desc
  
  if len(sys.argv) < 2:
    command, args = '', []
  else:
    command, args = sys.argv[1], sys.argv[2:]
  
  options = config
  for i, arg in enumerate(args):
    if arg.startswith('--'):
      opt = arg.lstrip('--')
      try:
        key, val = opt.split('=')
      except ValueError:
        key = opt.split('=')
        val = True
      options[key] = val
      del args[i]

  if command in handlers:
    handler = handlers[command]
  else:
    handler = help

  try:
    handler(*args, **options)
  except Exception as e:
    print "error: %s" % str(e)

def cmd(handler):
  handlers[handler.__name__] = handler
  return handler

def default(handler):
  handlers[''] = handler
  return handler

def help(**options):
  subcmds = []
  for name, handler in handlers.items():
    syntax = (program['name'] + ' ' + name).strip()
    usage = '  %s: %s' % (syntax, handler.__doc__)
    subcmds.append(usage)
  subcmds = '\n'.join(subcmds)
  
  doc = """%s

Usage:
%s""" % (program['desc'], subcmds)
  
  print doc

########NEW FILE########
__FILENAME__ = server
import datetime
import itertools
from operator import itemgetter

def summarize(records):
  return [(r[0], sum(s[1] for s in r[1])) for r in
    itertools.groupby(sorted(records, key=itemgetter(0)), itemgetter(0))]

def start(project, records):
  if records and not records[-1][1][1]:
    return records
  return records + [(project, (datetime.datetime.now(), None))]

def stop(records):
  if records and not records[-1][1][1]:
    return records[:-1] + \
      [(lambda r: (r[0], (r[1][0], datetime.datetime.now())))(records[-1])]
  return records

def list_projects(records):
  return [r[0] for r in
    itertools.groupby(sorted(records, key=itemgetter(0)), itemgetter(0))]

def record_from_txt(line, only_elapsed=False, time_format='%H:%M on %d %b %Y'):
  try:
    def transform(record):
      if only_elapsed:
        return (record[0], minutes_elapsed(
          date_from_txt(record[1][0], time_format),
          date_from_txt(record[1][1], time_format)))
      else:
        return (record[0], (date_from_txt(record[1][0], time_format),
                            date_from_txt(record[1][1], time_format)))

    return transform((lambda project, times: (project.strip(), (
      lambda start, end: (start.strip(), end.strip()))(
        *times.split(' - '))))(*line.split(':', 1)))

  except ValueError:
    raise SyntaxError(line)

def record_to_txt(record, time_format):
  return "%s: %s - %s" % (record[0],
    date_to_txt(record[1][0], time_format),
    date_to_txt(record[1][1], time_format))

def date_from_txt(date, time_format):
  if not date:
    return None
  return datetime.datetime.strptime(date, time_format)

def date_to_txt(date, time_format):
  if not date:
    return ''
  return date.strftime(time_format)

def minutes_elapsed(start, end=None):
  if not end:
    end = datetime.datetime.now()
  return (end - start).seconds / 60

class SyntaxError(Exception):
  def __init__(self, line):
    self.line = line

  def __str__(self):
    return "syntax error on this line:\n  %s" % repr(self.line)

########NEW FILE########
