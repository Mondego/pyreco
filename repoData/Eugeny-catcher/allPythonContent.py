__FILENAME__ = collector
from collections import namedtuple
import sys
import time
import inspect

Report = namedtuple('Report', ['timestamp', 'exception', 'traceback'])
Frame = namedtuple('Frame', ['file', 'line', 'code', 'locals'])


def __collect_frame(frame):
    return Frame(
        file=inspect.getfile(frame),
        line=frame.f_lineno,
        locals=frame.f_locals,
        code=inspect.getsourcelines(frame),
    )


def backup(exception):
    exception.traceback_backup = sys.exc_info()[2]


def collect(exception):
    traceback = []

    if hasattr(exception, 'traceback_backup'):
        tb = exception.traceback_backup
    else:
        exc_info = sys.exc_info()
        tb = exc_info[2]

    while tb:
        frame = tb.tb_frame
        traceback.append(__collect_frame(frame))
        tb = tb.tb_next

    return Report(
        timestamp=time.time(),
        exception=exception,
        traceback=traceback,
    )

########NEW FILE########
__FILENAME__ = html
from mako.template import Template
from datetime import datetime


_template = Template("""<!doctype html>
<html>
    <head>
        <meta charset="utf-8">
        <title>Error report</title>

        <script src="http://ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js"></script>
        <script src="http://netdna.bootstrapcdn.com/bootstrap/3.0.0-rc1/js/bootstrap.min.js"></script>

        <link href="http://netdna.bootstrapcdn.com/bootstrap/3.0.0-rc1/css/bootstrap.min.css" rel="stylesheet">
        <link href="http://netdna.bootstrapcdn.com/font-awesome/3.2.1/css/font-awesome.min.css" rel="stylesheet">
        <style>
            a {
                cursor: pointer;
            }

            .codebox {
                font-family: monospace;
            }

            .codebox .line.current {
                background: rgba(0,0,255,.1);
            }

            .codebox .lineno {
                text-align: right;
                display: inline-block;
                width: 100px;
                opacity: .5;
            }

            .codebox .code {
                white-space: pre;
            }

            .object-link {
                font-family: monospace;
                white-space: pre;
            }
        </style>
    </head>

    <%
        def id():
            id._last_id += 1
            return id._last_id

        id._last_id = 0

        def extract_attrs(object):
            r = {}
            for k in dir(object):
                if not k.startswith('__') and hasattr(object, k):
                    v = getattr(object, k)
                    if not type(v).__name__.endswith('method'):
                        r[k] = v
            return r
    %>

    <%def name="object(x, depth=0)" buffered="True">
        % if depth > maxdepth:
            <% return "[too deep]" %>
        % endif
        <% objid = id() %>
        % if type(x) in [str, int, long, float, set] or x is None:
            <code>${repr(x) | h}</code>
        % elif type(x) == dict:
            <table class="table">
                % for key, value in x.items():
                    <tr>
                        <td><code>${key | h}</code></td>
                        <td><span class="badge">${type(value).__name__ | h}</span></td>
                        <td width="100%">${object(value, depth + 1)}</td>
                    </tr>
                % endfor
            </table>
        % elif type(x) == list:
            <span class="badge">${len(x)} items</span>
            <table class="table">
                % for value in x:
                    <tr>
                        <td><span class="badge">${type(value).__name__ | h}</span></td>
                        <td>${object(value, depth + 1)}</td>
                    </tr>
                % endfor
            </table>
        % else:
            % if hasattr(x, '__dict__'):
                <a class="object-link" data-toggle="collapse" data-target="#${objid}-content">${repr(x) | h}</a>
                <div id="${objid}-content" class="collapse">
                    ${object(extract_attrs(x), depth + 1)}
                </div>
            % else:
                <code> ${repr(x) | h} </code>
            % endif
        % endif
    </%def>

    <body>
        <div class="container">
            <h3>Error report</h3>
            <dl>
                <dt>Timestamp</dt>
                <dd>${ datetime.fromtimestamp(report.timestamp) }</dd>
            </dl>

            <h3>Exception</h3>
            ${object(report.exception)}

            <h3>Traceback</h3>
            % for frame in report.traceback:
                <% frameid = id() %>
                <p>
                    <i class="icon-file"></i> <code>${ frame.file } : ${ frame.line }</code>


                    <div class="row">
                        <div class="col-lg-10">

                            <div class="codebox">
                                % for index, line in enumerate(frame.code[0]):
                                    <div class="line ${'current' if frame.code[1] + index == frame.line else ''}">
                                        <span class="lineno">
                                            ${ frame.code[1] + index }
                                        </span>
                                        <span class="code">${ line | h}</span>
                                    </div>
                                % endfor
                            </div>

                        </div>
                        <div class="col-lg-2">
                            <a class="btn btn-default" data-toggle="collapse" data-target="#${frameid}-locals">
                                <i class="icon-list-ul"></i> Locals
                            </a>
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-lg-1">
                        </div>
                        <div>
                            <div id="${frameid}-locals" class="collapse">
                                <h4>Locals</h4>
                                ${object(frame.locals)}
                            </div>
                        </div>
                    </div>
                </p>
            % endfor
        </div>
    </body>
</html>
""", default_filters=['decode.utf8'], input_encoding='utf-8', output_encoding='utf-8')


class HTMLFormatter:
    def format(self, report, maxdepth=5):
        return _template.render(maxdepth=maxdepth, report=report, datetime=datetime)

########NEW FILE########
__FILENAME__ = text
from datetime import datetime


class TextFormatter:
    def __format_frame(self, frame):
        lines, current_line = frame.code
        code = ''.join(
            '    ' +
            ('>>' if lines.index(line) == frame.line - current_line else '  ') +
            ' ' + line
            for line in lines
        )

        return """
    %(file)s:%(line)s
%(code)s
        """ % {
            'file': frame.file,
            'line': frame.line,
            'code': code,
        }

    def format(self, report):
        traceback = '\n'.join(self.__format_frame(frame) for frame in report.traceback)
        return """
Error report at %(timestamp)s

Traceback:
%(traceback)s
        """ % {
            'timestamp': datetime.fromtimestamp(int(report.timestamp)),
            'traceback': traceback,
        }

########NEW FILE########
__FILENAME__ = tests
from __future__ import print_function
import unittest
import catcher


class CollectorTest (unittest.TestCase):
    class Tester:
        def divide(self, a, b):
            return a / b

        def inner(self):
            self.divide(2, 0)

        def test(self):
            self.inner()

    def test_collection(self):
        try:
            CollectorTest.Tester().test()
        except Exception as e:
            report = catcher.collect(e)
        html = catcher.formatters.HTMLFormatter().format(report)
        print(catcher.uploaders.AjentiOrgUploader().upload(html))

########NEW FILE########
__FILENAME__ = ajentiorg
from base64 import b64encode
import requests
import zlib


class AjentiOrgUploader:
    def upload(self, data):
        return requests.post(
            'http://ajenti.org/catcher/submit',
            data={'text': b64encode(zlib.compress(data.encode('utf-8')))}
        ).text

########NEW FILE########
__FILENAME__ = pastehtml
import requests


class PasteHTMLUploader:
    def upload(self, data):
        return requests.post(
            'http://pastehtml.com/upload/create?input_type=html&result=address',
            data={'txt': data}
        ).text

########NEW FILE########
__FILENAME__ = _version
__version__ = '0.1.7'

########NEW FILE########
