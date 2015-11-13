__FILENAME__ = app
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jun 30, 2012
#


import os
import platform
import sys

if platform.system() == "Linux":
    os.environ["PYTHON_EGG_CACHE"] = "/tmp/egg"
_root = os.path.dirname(os.path.abspath(__file__))
# append tasks directory for celeryconfig.py
sys.path.append(os.path.join(_root, "tasks"))
# chdir to current directory
# workaround for d3status-redis27 server which raise exception(celeryd use os.getcwd())
# when using supervisor to run app.py
os.chdir(_root)

from tornado import web
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.options import options
from tornado.database import Connection

try:
    import d3status
except ImportError:
    import sys
    sys.path.append(os.path.join(_root, ".."))

from d3status.libs.options import parse_options


class Application(web.Application):
    def __init__(self):
        from d3status.urls import handlers, ui_modules
        from d3status.db import Model

        settings = dict(debug=options.debug,
                        template_path=os.path.join(os.path.dirname(__file__),
                                                   "templates"),
                        static_path=os.path.join(os.path.dirname(__file__),
                                                 "static"),
                        login_url=options.login_url,
                        xsrf_cookies=options.xsrf_cookies,
                        cookie_secret=options.cookie_secret,
                        ui_modules=ui_modules,
                        #autoescape=None,
                        )

        # d3status db connection
        self.db = Connection(host=options.mysql["host"] + ":" +
                                options.mysql["port"],
                             database=options.mysql["database"],
                             user=options.mysql["user"],
                             password=options.mysql["password"],
                             )

        Model.setup_dbs({"db": self.db})

        super(Application, self).__init__(handlers, **settings)

    def reverse_api(self, request):
        """Returns a URL name for a request"""
        handlers = self._get_host_handlers(request)

        for spec in handlers:
            match = spec.regex.match(request.path)
            if match:
                return spec.name

        return None


def main():
    parse_options()

    http_server = HTTPServer(Application(),
                             xheaders=True)
    http_server.bind(int(options.port), "127.0.0.1")  # listen local only
    http_server.start(1)

    IOLoop.instance().start()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = consts
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on Jul 1, 2012
#

CATEGORY_AMERICAS = "Americas"
CATEGORY_EUROPE = "Europe"
CATEGORY_ASIA = "Asia"
CATEGORYS = (CATEGORY_AMERICAS, CATEGORY_EUROPE, CATEGORY_ASIA)

SUBSCRIBE_STATUS_ON = "on"
SUBSCRIBE_STATUS_OFF = "off"

LOCALES = ("en", "zh_CN", "zh_TW")

########NEW FILE########
__FILENAME__ = d3_server_status
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jul 2, 2012
#

import os
import platform
import sys
import logging
from pyquery import PyQuery as pq
from lxml import etree

from tornado.httpclient import HTTPRequest, HTTPClient
from tornado.options import options

_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.join(_dir, "..")
# append tasks directory for celeryconfig.py
sys.path.append(os.path.join(_root, "tasks"))

try:
    # tornado process
    import d3status
except ImportError:
    # celeryd process runtime env
    if platform.system() == "Linux":
        os.environ["PYTHON_EGG_CACHE"] = "/tmp/egg"
    sys.path.append(os.path.join(_root, ".."))

from tornado.options import options
from tornado.database import Connection

from d3status.libs.options import parse_options
parse_options()

from d3status.db import Model
from d3status.db import load_model
from d3status.mail import send_email
from d3status.tasks import status_tasks

# db connection
db = Connection(host=options.mysql["host"] + ":" +
                        options.mysql["port"],
                     database=options.mysql["database"],
                     user=options.mysql["user"],
                     password=options.mysql["password"],
                     )

Model.setup_dbs({"db": db})


def update_server_status():
    url = options.d3_server_status_url
    req = HTTPRequest(url=url)

    client = HTTPClient()
    response = client.fetch(req)
    if response.code == 200:
        status = _parse_server_status(response.body)
        changed_status = load_model("status").update_status(status)
        if changed_status:
            status_tasks.status_notification_task.delay(changed_status)
    else:
        err = "GET_D3_SERVER_STAUTS_ERROR: %s\n%s" (response.code, response)
        logging.error(err)

        # send email
        subject = "[%s]Get D3 server status error" % options.sitename
        body = err
        if options.send_error_email:
            send_email(options.email_from, options.admins, subject, body)


def _parse_server_status(body):
    status = {}

    q = pq(etree.fromstring(body))
    boxes = q(".box")  # category box
    for box in boxes:
        box_q = pq(etree.fromstring(etree.tostring(box)))
        category = box_q(".category")[0].text.strip()
        status[category] = {}
        servers = box_q(".server")
        for server in servers:
            server_q = pq(etree.fromstring(etree.tostring(server)))
            server_name = server_q(".server-name")[0].text.strip().replace(" ", "")
            if server_name:
                status_icon = server_q(".status-icon")[0]
                class_ = status_icon.get("class")
                if class_:
                    st = 0
                    if "up" in class_:
                        st = 1
                    status[category][server_name] = st

    return status


if __name__ == "__main__":
    update_server_status()

########NEW FILE########
__FILENAME__ = status
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jun 30, 2012
#

from d3status.db import Model


class StatusModel(Model):
    def get_status(self):
        status = {"status": {"items": []}}
        items = status["status"]["items"]
        categorys = {}

        rows = self.db.query("select * from status")
        for row in rows:
            categorys.setdefault(row.category, {})[row.service] = row.status

        for category, services in categorys.iteritems():
            items.append({"category": category,
                          "services": services})

        if rows:
            status["count"] = len(items)
            return status
        else:
            return {}

    def update_status(self, status):
        changed_status = {}

        old_status = self.get_status()
        old_status_ = {}
        if old_status:
            for item in old_status["status"]["items"]:
                old_status_[item["category"]] = item["services"]

        for category, services in status.iteritems():
            for name, st in services.iteritems():
                old_st = old_status_[category].get(name, None)
                if old_st is not None and old_st != st:
                    changed_status.setdefault(category, {})[name] = st
                self._update_status(category, name, st)

        return changed_status

    def _update_status(self, category, server_name, status):
        row = self.db.get("select * from status where category=%s and service=%s",
                          category, server_name)
        if not row:
            self.db.execute("insert into status (category, service, status) "
                            "values (%s, %s, %s)",
                            category, server_name, status)
        else:
            self.db.execute("update status set status=%s where id=%s",
                            status, row.id)

########NEW FILE########
__FILENAME__ = subscribers
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jun 30, 2012
#

from d3status.db import Model
from d3status import consts


class SubscribersModel(Model):
    def subscribe(self, token, categorys, locale="en"):
        row = self.db.get("select * from subscribers where token=%s", token)
        if not row:
            sql = "insert into subscribers (token, categorys, status, locale) " \
            "values (%s, %s, %s, %s)"
            self.db.execute(sql, token, categorys, consts.SUBSCRIBE_STATUS_ON,
                            locale)
        else:
            sql = "update subscribers set categorys=%s, locale=%s where token=%s"
            self.db.execute(sql, categorys, locale, token)

    def unsubscribe(self, token):
        sql = "update subscribers set status=%s where token=%s"
        self.db.execute(sql, consts.SUBSCRIBE_STATUS_OFF, token)

    def get_subscribers(self, limit=200, offset=0):
        return self.db.query("select * from subscribers where status='on' "
                             "limit %s offset %s",
                             limit, offset)

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jun 30, 2012
#

from tornado import escape
from tornado.web import HTTPError


class HTTPAPIError(HTTPError):
    """API error handling exception

    API server always returns formatted JSON to client even there is
    an internal server error.
    """
    def __init__(self, status_code=400, error_detail="", error_type="",
                 notification="", response="", log_message=None, *args):

        super(HTTPAPIError, self).__init__(int(status_code), log_message, *args)

        self.error_type = error_type if error_type else \
            _error_types.get(self.status_code, "unknow_error")
        self.error_detail = error_detail
        self.notification = {"message": notification} if notification else {}
        self.response = response if response else {}

    def __str__(self):
        err = {"meta": {"code": self.status_code, "errorType": self.error_type}}
        self._set_err(err, ["notification", "response"])

        if self.error_detail:
            err["meta"]["errorDetail"] = self.error_detail

        return escape.json_encode(err)

    def _set_err(self, err, names):
        for name in names:
            v = getattr(self, name)
            if v:
                err[name] = v


_error_types = {400: "param_error",
                401: "invalid_auth",
                403: "not_authorized",
                404: "endpoint_error",
                405: "method_not_allowed",
                500: "server_error"}

########NEW FILE########
__FILENAME__ = handler
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jun 30, 2012
#

import traceback
import logging

from tornado import escape
from tornado.options import options
from tornado.web import RequestHandler as BaseRequestHandler, HTTPError
from d3status import exceptions
from d3status.tasks import email_tasks


class BaseHandler(BaseRequestHandler):
    def get(self, *args, **kwargs):
        # enable GET request when enable delegate get to post
        if options.app_get_to_post:
            self.post(*args, **kwargs)
        else:
            raise exceptions.HTTPAPIError(405)

    def prepare(self):
        self.traffic_control()
        pass

    def traffic_control(self):
        # traffic control hooks for api call etc
        self.log_apicall()
        pass

    def log_apicall(self):
        pass


class RequestHandler(BaseHandler):
    pass


class APIHandler(BaseHandler):
    def get_current_user(self):
        pass

    def finish(self, chunk=None, notification=None):
        if chunk is None:
            chunk = {}

        if isinstance(chunk, dict):
            chunk = {"meta": {"code": 200}, "response": chunk}

            if notification:
                chunk["notification"] = {"message": notification}

        callback = escape.utf8(self.get_argument("callback", None))
        if callback:
            self.set_header("Content-Type", "application/x-javascript")

            if isinstance(chunk, dict):
                chunk = escape.json_encode(chunk)

            self._write_buffer = [callback, "(", chunk, ")"] if chunk else []
            super(APIHandler, self).finish()
        else:
            self.set_header("Content-Type", "application/json; charset=UTF-8")
            super(APIHandler, self).finish(chunk)

    def write_error(self, status_code, **kwargs):
        """Override to implement custom error pages."""
        debug = self.settings.get("debug", False)
        try:
            exc_info = kwargs.pop('exc_info')
            e = exc_info[1]

            if isinstance(e, exceptions.HTTPAPIError):
                pass
            elif isinstance(e, HTTPError):
                e = exceptions.HTTPAPIError(e.status_code)
            else:
                e = exceptions.HTTPAPIError(500)

            exception = "".join([ln for ln in traceback.format_exception(*exc_info)])

            if status_code == 500 and not debug:
                self._send_error_email(exception)

            if debug:
                e.response["exception"] = exception

            self.clear()
            self.set_status(200)  # always return 200 OK for API errors
            self.set_header("Content-Type", "application/json; charset=UTF-8")
            self.finish(str(e))
        except Exception:
            logging.error(traceback.format_exc())
            return super(APIHandler, self).write_error(status_code, **kwargs)

    def _send_error_email(self, exception):
        try:
            # send email
            subject = "[%s]Internal Server Error" % options.sitename
            body = self.render_string("errors/500_email.html",
                                      exception=exception)
            if options.send_error_email:
                email_tasks.send_email_task.delay(options.email_from,
                                                  options.admins, subject, body)
        except Exception:
            logging.error(traceback.format_exc())


class ErrorHandler(RequestHandler):
    """Default 404: Not Found handler."""
    def prepare(self):
        super(ErrorHandler, self).prepare()
        raise HTTPError(404)


class APIErrorHandler(APIHandler):
    """Default API 404: Not Found handler."""
    def prepare(self):
        super(APIErrorHandler, self).prepare()
        raise exceptions.HTTPAPIError(404)

########NEW FILE########
__FILENAME__ = status
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jun 30, 2012
#

from d3status.handler import APIHandler
from d3status.db import load_model
from d3status import consts
from d3status.tasks import status_tasks


class StatusIndexHandler(APIHandler):
    def get(self):
        self.finish(load_model('status').get_status())


class StatusSubscribeHandler(APIHandler):
    def post(self):
        token = self.get_argument("deviceToken", "")
        categorys = self.get_argument("categorys", "").split(",")
        categorys = [c for c in categorys if c in consts.CATEGORYS]
        categorys = ",".join(categorys)
        locale = self.get_argument("locale", "en")
        if locale not in consts.LOCALES:
            locale = "en"

        if token:
            load_model("subscribers").subscribe(token, categorys, locale)


class StatusUnsubscribeHandler(APIHandler):
    def post(self):
        token = self.get_argument("deviceToken", "")
        if token:
            load_model("subscribers").unsubscribe(token)


handlers = [(r"/status", StatusIndexHandler),
            (r"/status/subscribe", StatusSubscribeHandler),
            (r"/status/unsubscribe", StatusUnsubscribeHandler),
            ]

########NEW FILE########
__FILENAME__ = apnswrapper
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jun 30, 2012
#

import time
import traceback
import logging
from apns import APNs, Payload

_ignored_content_keys = ("message",)  # maybe more keys later


class APNsWrapper(APNs):
    def __init__(self, use_sandbox=False, cert_file=None, key_file=None):
        super(APNsWrapper, self).__init__(use_sandbox, cert_file, key_file)
        self._payloads = []

    def append(self, token, notification, alert=None, badge=None, sound=None):
        if not alert:
            alert = notification.get("message", None)

        if alert and isinstance(alert, dict):
            alert = alert.get("message", None)

        for key in _ignored_content_keys:
            try:
                del notification[key]
            except KeyError:
                pass

        payload = Payload(alert, badge, sound, custom=notification)
        self._payloads.append((token, payload))

    def flush(self):
        if self._payloads:
            for token, payload in self._payloads:
                try:
                    self.gateway_server.write(self.gateway_server._get_notification(token, payload))
                except:
                    logging.error(traceback.format_exc())
                    # trigger reconnect
                    self._gateway_connection = None

            self._payloads = []

########NEW FILE########
__FILENAME__ = importlib
# License for code in this file that was taken from Python 2.7.

# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2
# --------------------------------------------
#
# 1. This LICENSE AGREEMENT is between the Python Software Foundation
# ("PSF"), and the Individual or Organization ("Licensee") accessing and
# otherwise using this software ("Python") in source or binary form and
# its associated documentation.
#
# 2. Subject to the terms and conditions of this License Agreement, PSF
# hereby grants Licensee a nonexclusive, royalty-free, world-wide
# license to reproduce, analyze, test, perform and/or display publicly,
# prepare derivative works, distribute, and otherwise use Python
# alone or in any derivative version, provided, however, that PSF's
# License Agreement and PSF's notice of copyright, i.e., "Copyright (c)
# 2001, 2002, 2003, 2004, 2005, 2006, 2007 Python Software Foundation;
# All Rights Reserved" are retained in Python alone or in any derivative
# version prepared by Licensee.
#
# 3. In the event Licensee prepares a derivative work that is based on
# or incorporates Python or any part thereof, and wants to make
# the derivative work available to others as provided herein, then
# Licensee hereby agrees to include in any such work a brief summary of
# the changes made to Python.
#
# 4. PSF is making Python available to Licensee on an "AS IS"
# basis.  PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
# IMPLIED.  BY WAY OF EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND
# DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS
# FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON WILL NOT
# INFRINGE ANY THIRD PARTY RIGHTS.
#
# 5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON
# FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS
# A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON,
# OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.
#
# 6. This License Agreement will automatically terminate upon a material
# breach of its terms and conditions.
#
# 7. Nothing in this License Agreement shall be deemed to create any
# relationship of agency, partnership, or joint venture between PSF and
# Licensee.  This License Agreement does not grant permission to use PSF
# trademarks or trade name in a trademark sense to endorse or promote
# products or services of Licensee, or any third party.
#
# 8. By copying, installing or otherwise using Python, Licensee
# agrees to be bound by the terms and conditions of this License
# Agreement.
import sys


def _resolve_name(name, package, level):
    """Return the absolute name of the module to be imported."""
    if not hasattr(package, 'rindex'):
        raise ValueError("'package' not set to a string")
    dot = len(package)
    for x in xrange(level, 1, -1):
        try:
            dot = package.rindex('.', 0, dot)
        except ValueError:
            raise ValueError("attempted relative import beyond top-level "
                              "package")
    return "%s.%s" % (package[:dot], name)


def import_module(name, package=None):
    """Import a module.

    The 'package' argument is required when performing a relative import. It
    specifies the package to use as the anchor point from which to resolve the
    relative import to an absolute import.

    """
    if name.startswith('.'):
        if not package:
            raise TypeError("relative imports require the 'package' argument")
        level = 0
        for character in name:
            if character != '.':
                break
            level += 1
        name = _resolve_name(name[level:], package, level)
    __import__(name)
    return sys.modules[name]

########NEW FILE########
__FILENAME__ = loader
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jun 30, 2012
#

import importlib

_module_instances = {}


def load(root_module, suffix):
    def load_(name):
        name = name.lower()
        key = "%s.%s" % (root_module, name)
        if key not in _module_instances:
            try:
                module = importlib.import_module(".%s" % name, root_module)
            except ImportError:
                module = importlib.import_module(".%s" % name[:-1], root_module)

            # load("breeze.db", "users", "Model") will return UsersModel class obj
            cls = getattr(module,
                          "%s%s%s%s" % (name[0].upper(), name[1:],
                                        suffix[0].upper(), suffix[1:]))
            _module_instances[key] = cls()

        return _module_instances[key]

    return load_

########NEW FILE########
__FILENAME__ = options
## -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jun 30, 2012
#

import logging
import os

from tornado.options import parse_command_line, options, define


def parse_config_file(path):
    """Rewrite tornado default parse_config_file.

    Parses and loads the Python config file at the given path.

    This version allow customize new options which are not defined before
    from a configuration file.
    """
    config = {}
    execfile(path, config, config)
    for name in config:
        if name in options:
            options[name].set(config[name])
        else:
            define(name, config[name])


def parse_options():
    _root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    _settings = os.path.join(_root, "settings.py")
    _settings_local = os.path.join(_root, "settings_local.py")

    try:
        parse_config_file(_settings)
        logging.info("Using settings.py as default settings.")
    except Exception, e:
        logging.error("No any default settings, are you sure? Exception: %s" % e)

    try:
        parse_config_file(_settings_local)
        logging.info("Override some settings with local settings.")
    except Exception, e:
        logging.error("No local settings. Exception: %s" % e)

    parse_command_line()

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jun 30, 2012
#

import os
import mimetypes


def find_modules(modules_dir):
    try:
        return [f[:-3] for f in os.listdir(modules_dir)
                if not f.startswith('_') and f.endswith('.py')]
    except OSError:
        return []

########NEW FILE########
__FILENAME__ = mail
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jun 30, 2012
#

import re
import logging
import smtplib
import time
from datetime import datetime, timedelta
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import COMMASPACE
from email.utils import formatdate

from tornado.escape import utf8
from tornado.options import options

__all__ = ("send_email", "EmailAddress")

# borrow email re pattern from django
_email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"'  # quoted-string
    r')@(?:[A-Z0-9]+(?:-*[A-Z0-9]+)*\.)+[A-Z]{2,6}$', re.IGNORECASE)  # domain


def send_email(fr, to, subject, body, html=None, attachments=[]):
    """Send an email.

    If an HTML string is given, a mulitpart message will be generated with
    plain text and HTML parts. Attachments can be added by providing as a
    list of (filename, data) tuples.
    """
    # convert EmailAddress to pure string
    if isinstance(fr, EmailAddress):
        fr = str(fr)
    else:
        fr = utf8(fr)
    to = [utf8(t) for t in to]

    if html:
        # Multipart HTML and plain text
        message = MIMEMultipart("alternative")
        message.attach(MIMEText(body, "plain"))
        message.attach(MIMEText(html, "html"))
    else:
        # Plain text
        message = MIMEText(body)
    if attachments:
        part = message
        message = MIMEMultipart("mixed")
        message.attach(part)
        for filename, data in attachments:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(data)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment",
                filename=filename)
            message.attach(part)

    message["Date"] = formatdate(time.time())
    message["From"] = fr
    message["To"] = COMMASPACE.join(to)
    message["Subject"] = utf8(subject)

    _get_session().send_mail(fr, to, utf8(message.as_string()))


class EmailAddress(object):
    def __init__(self, addr, name=""):
        assert _email_re.match(addr), "Email address(%s) is invalid." % addr

        self.addr = addr
        if name:
            self.name = name
        else:
            self.name = addr.split("@")[0]

    def __str__(self):
        return '%s <%s>' % (utf8(self.name), utf8(self.addr))


class _SMTPSession(object):
    def __init__(self, host, user='', password='', duration=30, tls=False):
        self.host = host
        self.user = user
        self.password = password
        self.duration = duration
        self.tls = tls
        self.session = None
        self.deadline = datetime.now()
        self.renew()

    def send_mail(self, fr, to, message):
        if self.timeout:
            self.renew()

        try:
            self.session.sendmail(fr, to, message)
        except Exception, e:
            err = "Send email from %s to %s failed!\n Exception: %s!" \
                % (fr, to, e)
            logging.error(err)
            self.renew()

    @property
    def timeout(self):
        if datetime.now() < self.deadline:
            return False
        else:
            return True

    def renew(self):
        try:
            if self.session:
                self.session.quit()
        except Exception:
            pass

        self.session = smtplib.SMTP(self.host)
        if self.user and self.password:
            if self.tls:
                self.session.starttls()

            self.session.login(self.user, self.password)

        self.deadline = datetime.now() + timedelta(seconds=self.duration * 60)


def _get_session():
    global _session
    if _session is None:
        _session = _SMTPSession(options.smtp['host'],
                                options.smtp['user'],
                                options.smtp['password'],
                                options.smtp['duration'],
                                options.smtp['tls'])

    return _session

_session = None

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jun 30, 2012
#
"""Project settings"""

import platform
import os

# can't use __file__ directly here because it's parsed by tornado.options
import d3status
root_dir = os.path.dirname(os.path.abspath(d3status.__file__))

if platform.node() == "FELINX":  # FELINX is the hosting server name.
    debug = False
else:
    debug = True

loglevel = "INFO"  # for celeryd
port = 8888

d3_server_status_url = "http://us.battle.net/d3/en/status"

sitename = "D3 Status"
domain = "api.feilong.me"
home_url = "http://%s/d3" % domain
login_url = "http://%s/login" % home_url
app_url_prefix = "/d3/v1"
email_from = "%s <noreply@%s>" % (sitename, domain)
admins = ("Felinx <felinx.lee@gmail.com>",)
send_error_email = True
cookie_secret = "d1d87395-8272-4749-b2f2-dcabd3903a1c"
xsrf_cookies = False

# Apple push notification settings
apns_sandbox = debug
apns_certificate = "d3status_apns_dev.pem"
apns_certificate_key = None

mysql = {"host": "localhost",
         "port": "3306",
         "database": "d3status",
         "user": "felinx",
         "password": "felinx"
         }

smtp = {"host": "localhost",
        "user": "",
        "password": "",
        "duration": 30,
        "tls": False
        }

########NEW FILE########
__FILENAME__ = settings_local
debug = True
apns_sandbox = True

########NEW FILE########
__FILENAME__ = apns_tasks
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  May 30, 2012
#

import os

from celery.task import task
from tornado.options import options

from d3status.libs.apnswrapper import APNsWrapper

_root = os.path.join(os.path.dirname(__file__), "..")
_apns = None


@task
def apns_push_task(tokens, notification, alert=None, badge=None, sound=None):
    apns_push(tokens, notification, alert, badge, sound)


def apns_push(tokens, notification, alert=None, badge=None, sound=None):
    _setup_apns()
    if isinstance(tokens, basestring):
        tokens = [tokens, ]

    for token in tokens:
        _apns.append(token, notification, alert, badge, sound)

    _apns.flush()


def _setup_apns():
    global _apns

    if not _apns:
        cert_file = os.path.join(_root, options.apns_certificate)
        if not options.apns_certificate_key:
            key_file = None
        else:
            key_file = os.path.join(_root, options.apns_certificate_key)

        _apns = APNsWrapper(use_sandbox=options.apns_sandbox,
                            cert_file=cert_file,
                            key_file=key_file)

########NEW FILE########
__FILENAME__ = celeryconfig
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jun 30, 2012


CELERY_IMPORTS = ("tasks", )

CELERY_RESULT_BACKEND = "redis"
CELERY_REDIS_HOST = "localhost"
CELERY_REDIS_PORT = 6379
CELERY_REDIS_DB = 0

BROKER_URL = "redis://%s:%s/%s" % (CELERY_REDIS_HOST, CELERY_REDIS_PORT,
                                   CELERY_REDIS_DB)

########NEW FILE########
__FILENAME__ = email_tasks
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jun 30, 2012
#

from celery.task import task
from d3status.mail import send_email


@task
def send_email_task(fr, to, subject, body, html=None, attachments=[]):
    send_email(fr, to, subject, body, html, attachments)

########NEW FILE########
__FILENAME__ = status_tasks
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jul 2, 2012
#

import os
import tornado.locale

from celery.task import task
from tornado.options import options
from d3status.db import load_model
from d3status.tasks import apns_tasks


@task
def status_notification_task(changed_status):
    status_notifciation(changed_status)


def status_notifciation(changed_status):
    notifications = {}
    for category, services in changed_status.iteritems():
        for name, st in services.iteritems():
            # just push notification about game server now
            if name == "GameServer":
                notifications[category] = st

    for category, st in notifications.iteritems():
        status = "Available" if st else "Unavailable"

        offset = 0
        limit = 200
        while True:
            subscribers = load_model("subscribers").get_subscribers(limit, offset)
            if not subscribers:
                break

            for subscribe in subscribers:
                if category in subscribe.categorys:
                    alert = _trans_alert("Diablo3 %s server status has changed to %s",
                                         category, status, subscribe.locale)
                    apns_tasks.apns_push_task.delay(subscribe.token, {},
                                                    alert=alert, badge=1,
                                                    sound="default")
            offset += len(subscribers)


def _trans(s, locale):
    locale = tornado.locale.get(locale)
    s = locale.translate(s).strip("\"")

    return s


def _trans_alert(alert, category, status, locale):
    def _(s):
        return _trans(s, locale)

    return _(alert) % (_(category), _(status))


_i18n_dir = os.path.join(os.path.join(os.path.dirname(__file__), ".."), 'i18n')
tornado.locale.load_translations(_i18n_dir)

########NEW FILE########
__FILENAME__ = tasks
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jun 30, 2012
#

"""Celery tasks center

Setup env for celery tasks and import them.
"""

import os
import platform
import sys

_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.join(_dir, "..")

try:
    # tornado process
    import d3status
except ImportError:
    # celeryd process runtime env
    if platform.system() == "Linux":
        os.environ["PYTHON_EGG_CACHE"] = "/tmp/egg"
    sys.path.append(os.path.join(_root, ".."))
    # append current directory for celeryconfig.py
    sys.path.append(_dir)

    from tornado.options import options
    from tornado.database import Connection

    from d3status.libs.options import parse_options
    parse_options()

    from d3status.db import Model

    # db connection
    db = Connection(host=options.mysql["host"] + ":" +
                            options.mysql["port"],
                         database=options.mysql["database"],
                         user=options.mysql["user"],
                         password=options.mysql["password"],
                         )

    Model.setup_dbs({"db": db})


from d3status.libs.importlib import import_module
from d3status.libs.utils import find_modules


def _load_tasks():
    _current_module = sys.modules[__name__]
    for m in find_modules(os.path.dirname(__file__)):
        if m.endswith("_tasks"):  # xxx_tasks.py
            try:
                mod = import_module("." + m, package="d3status.tasks")
                for func in dir(mod):
                    if func.endswith("_task"):
                        setattr(_current_module, func, getattr(mod, func))
            except ImportError:
                pass

_load_tasks()


########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 feilong.me. All rights reserved.
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on  Jun 30, 2012
#

try:
    import importlib
except:
    from d3status.libs import importlib

from tornado.options import options
from tornado.web import url
from d3status.handler import APIErrorHandler

handlers = []
ui_modules = {}

# the module names in handlers folder
handler_names = ["status", ]


def _generate_handler_patterns(root_module, handler_names, prefix=options.app_url_prefix):
    for name in handler_names:
        module = importlib.import_module(".%s" % name, root_module)
        module_hanlders = getattr(module, "handlers", None)
        if module_hanlders:
            _handlers = []
            for handler in module_hanlders:
                try:
                    patten = r"%s%s" % (prefix, handler[0])
                    if len(handler) == 2:
                        _handlers.append((patten,
                                          handler[1]))
                    elif len(handler) == 3:
                        _handlers.append(url(patten,
                                             handler[1],
                                             name=handler[2])
                                         )
                    else:
                        pass
                except IndexError:
                    pass

            handlers.extend(_handlers)

_generate_handler_patterns("d3status.handlers", handler_names)

# Override Tornado default ErrorHandler
handlers.append((r".*", APIErrorHandler))

########NEW FILE########
