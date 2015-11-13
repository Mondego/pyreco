__FILENAME__ = commands
#!/usr/bin/env python
from optparse import OptionParser
import hipsaint
from ..messages import HipchatMessage


def main():
    usage = "Usage: %prog [options] [action]..."

    parser = OptionParser(usage, version="%%prog v%s" % hipsaint.__version__)

    parser.add_option("-r", "--room",
                      dest="room_id",
                      default="",
                      help="HipChat room id deliver message to")

    parser.add_option("-u", "--user",
                      dest="user",
                      default="Nagios",
                      help="Username to deliver message as")

    parser.add_option("-t", "--token",
                      dest="token",
                      default="",
                      help="HipChat API token to use")

    parser.add_option("-i", "--inputs",
                      dest="inputs",
                      default="",
                      help="Input variables from Nagios separated by |")

    parser.add_option("-T", "--type",
                      dest="msg_type",
                      default="",
                      help="Mark if notification is from host group or service group, "
                           "host|service|short-host|short-service")

    parser.add_option("-n", "--notify",
                      action="store_true",
                      default=False,
                      dest="notify",
                      help="Whether or not this message should trigger a "
                           "notification for people in the room")

    ### Parse command line
    (options, args) = parser.parse_args()
    ### Validate required input
    if not options.token:
        parser.error('--token is required')
    if not options.inputs:
        parser.error('--inputs is required')
    if not options.room_id:
        parser.error('--room is required')
    if not options.msg_type:
        parser.error('--type is required')
    msg = HipchatMessage(**vars(options))
    msg.deliver_payload()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = messages
try:
    # For Python 3.0 and later
    from urllib.request import urlopen
    from urllib.parse import urlencode
except ImportError as e:
    # Fall back to Python 2 urllib2
    from urllib2 import urlopen
    from urllib import urlencode
import logging
import socket
import json
from .options import COLORS
from .templates import templates

logging.basicConfig()
log = logging.getLogger(__name__)


class HipchatMessage(object):
    url = "https://api.hipchat.com/v1/rooms/message"
    default_color = 'red'

    def __init__(self, msg_type, inputs, token, user, room_id, notify):
        self.type = msg_type
        self.inputs = inputs
        self.inputs_list = [input.strip() for input in self.inputs.split('|')]
        self.token = token
        self.user = user
        self.room_id = room_id
        self.notify = notify
        self.message_color = 'gray'

    def deliver_payload(self, **kwargs):
        """
        Makes HTTP GET request to HipChat containing the message from nagios
        according to API Documentation https://www.hipchat.com/docs/api/method/rooms/message
        """
        message_body = self.render_message()
        message = {'room_id': self.room_id,
                   'from': self.user,
                   'message': message_body,
                   'color': self.message_color,
                   'notify': int(self.notify),
                   'auth_token': self.token}
        message.update(kwargs)
        message_params = urlencode(message)
        message_params = message_params.encode('utf-8')
        raw_response = urlopen(self.url, message_params)
        response_data = json.load(raw_response)
        if 'error' in response_data:
            error_message = response_data['error'].get('message')
            error_type = response_data['error'].get('type')
            error_code = response_data['error'].get('code')
            log.error('%s - %s: %s', error_code, error_type, error_message)
        elif not 'status' in response_data:
            log.error('Unexpected response')
        return raw_response

    def get_host_context(self):
        hostname, timestamp, ntype, hostaddress, state, hostoutput = self.inputs_list
        return {'hostname': hostname, 'timestamp': timestamp, 'ntype': ntype,
                'hostaddress': hostaddress, 'state': state, 'hostoutput': hostoutput}

    def get_service_context(self):
        servicedesc, hostalias, timestamp, ntype, hostaddress, state, serviceoutput = self.inputs_list
        return {'servicedesc': servicedesc, 'hostalias': hostalias, 'timestamp': timestamp,
                'ntype': ntype, 'hostaddress': hostaddress, 'state': state,
                'serviceoutput': serviceoutput}

    def render_message(self):
        """
        Unpacks Nagios inputs and renders the appropriate template depending
        on the notification type.
        """
        template_type = self.type
        if template_type in ('host', 'short-host'):
            template_context = self.get_host_context()
        elif template_type in ('service', 'short-service'):
            template_context = self.get_service_context()
        else:
            raise Exception('Invalid notification type')

        ntype = template_context['ntype']
        state = template_context['state']
        if ntype != 'PROBLEM':
            self.message_color = COLORS.get(ntype, self.default_color)
        else:
            self.message_color = COLORS.get(state, self.default_color)
        nagios_host = socket.gethostname().split('.')[0]

        template_context.update(nagios_host=nagios_host)
        template = templates[template_type]
        return template.format(**template_context)

########NEW FILE########
__FILENAME__ = options
COLORS = {
    'PROBLEM': 'red',
    'RECOVERY': 'green',
    'ACKNOWLEDGEMENT': 'purple',
    'FLAPPINGSTART': 'yellow',
    'WARNING': 'yellow',
    'UNKNOWN': 'gray',
    'CRITICAL': 'red',
    'FLAPPINGSTOP': 'green',
    'FLAPPINGDISABLED': 'purple',
    'DOWNTIMESTART': 'red',
    'DOWNTIMESTOP': 'green'
}

########NEW FILE########
__FILENAME__ = templates
"""
Templates used to build hipchat api payloads
"""

host_template = """
<strong>{timestamp} - {hostname}  (nagios@{nagios_host})</strong><br/>
<strong>Type:</strong> {ntype}<br/>
<strong>Host:</strong> {hostname} (<a href="{hostaddress}">{hostaddress}</a>)<br/>
<strong>State:</strong> {state}<br>
<strong>Info:</strong>
<pre>{hostoutput}</pre>
"""

host_short_template = """[{ntype}] {hostname}: {hostoutput}"""

service_template = """
<strong>{timestamp} - {servicedesc} on {hostalias} (nagios@{nagios_host})</strong><br/>
<strong>Type:</strong> {ntype}<br/>
<strong>Host:</strong> {hostalias} (<a href="{hostaddress}">{hostaddress}</a>)<br/>
<strong>State:</strong> {state}<br/>
<strong>Info:</strong>
<pre>{serviceoutput}</pre>
"""

service_short_template = "[{ntype}] {hostalias} {servicedesc}: {serviceoutput}"


templates = {'host': host_template, 'short-host': host_short_template,
             'service': service_template, 'short-service': service_short_template}

########NEW FILE########
__FILENAME__ = tests
import unittest
import mock
from datetime import datetime
import json
from .messages import HipchatMessage


def setup_mock_request(mock_method, status_code, json_data):
    mock_response = mock.Mock()
    mock_response.read.return_value = json.dumps(json_data)
    mock_response.getcode.return_value = status_code
    mock_method.return_value = mock_response


def mock_hipchat_ok_request(mock_method):
    data = {'status': 'sent'}
    return setup_mock_request(mock_method, 200, data)


def mock_hipchat_error_request(mock_method):
    data = {'error': {'message': 'some test error', 'type': 'Unauthorized', 'code': 401}}
    return setup_mock_request(mock_method, 401, data)


class MessageTest(unittest.TestCase):
    def setUp(self):
        #"$HOSTNAME$|$LONGDATETIME$|$NOTIFICATIONTYPE$|$HOSTADDRESS$|$HOSTSTATE$|$HOSTOUTPUT$"
        self.host_inputs = 'hostname|%(longdatetime)s|%(notificationtype)s|127.0.0.1|' \
                           '%(hoststate)s|NAGIOS_OUTPUT'
        #"$SERVICEDESC$|$HOSTALIAS$|$LONGDATETIME$|$NOTIFICATIONTYPE$|$HOSTADDRESS$|$SERVICESTATE$
        # |$SERVICEOUTPUT$"
        self.service_inputs = 'servicedesc|hostalias|%(longdatetime)s|%(notificationtype)s|' \
                              '127.0.0.1|%(servicestate)s|NAGIOS_OUTPUT'

    @mock.patch('hipsaint.messages.urlopen')
    def test_ok_payload_delivery(self, mock_get):
        mock_hipchat_ok_request(mock_get)
        msg_inputs = self.host_inputs % {'longdatetime': datetime.now(),
                                         'notificationtype': 'PROBLEM',
                                         'hoststate': 'DOWN'}
        problem_msg = HipchatMessage('host', msg_inputs, None, None, None, False)
        response = problem_msg.deliver_payload()
        self.assertEqual(response.getcode(), 200)
        response_data = json.load(response)
        self.assertEqual(response_data['status'], 'sent')

    @mock.patch('hipsaint.messages.urlopen')
    def test_error_payload_delivery(self, mock_get):
        mock_hipchat_error_request(mock_get)
        msg_inputs = self.host_inputs % {'longdatetime': datetime.now(),
                                         'notificationtype': 'PROBLEM',
                                         'hoststate': 'DOWN'}
        problem_msg = HipchatMessage('host', msg_inputs, None, None, None, False)
        response = problem_msg.deliver_payload()
        response_data = json.load(response)
        self.assertEqual(response.getcode(), 401)
        self.assertTrue('error' in response_data)

    def test_render_host(self):
        message_type = 'host'
        msg_inputs = self.host_inputs % {'longdatetime': datetime.now(),
                                         'notificationtype': 'PROBLEM',
                                         'hoststate': 'DOWN'}
        problem_msg = HipchatMessage(message_type, msg_inputs, None, None, None, False)
        problem_msg.render_message()
        self.assertEqual(problem_msg.message_color, 'red')

        # Test short host
        problem_msg = HipchatMessage('short-host', msg_inputs, None, None, None, False)
        problem_msg.render_message()
        self.assertEqual(problem_msg.message_color, 'red')

        msg_inputs = self.host_inputs % {'longdatetime': datetime.now(),
                                         'notificationtype': 'RECOVERY',
                                         'hoststate': 'UP'}
        problem_msg = HipchatMessage(message_type, msg_inputs, None, None, None, False)
        problem_msg.render_message()
        self.assertEqual(problem_msg.message_color, 'green')

        msg_inputs = self.host_inputs % {'longdatetime': datetime.now(),
                                         'notificationtype': 'UNREACHABLE',
                                         'hoststate': 'UKNOWN'}
        problem_msg = HipchatMessage(message_type, msg_inputs, None, None, None, False)
        problem_msg.render_message()
        self.assertEqual(problem_msg.message_color, 'red')

        msg_inputs = self.host_inputs % {'longdatetime': datetime.now(),
                                         'notificationtype': 'ACKNOWLEDGEMENT',
                                         'hoststate': 'DOWN'}
        problem_msg = HipchatMessage(message_type, msg_inputs, None, None, None, False)
        problem_msg.render_message()
        self.assertEqual(problem_msg.message_color, 'purple')

    def test_render_service(self):
        message_type = 'service'
        msg_inputs = self.service_inputs % {'longdatetime': datetime.now(),
                                            'notificationtype': 'PROBLEM',
                                            'servicestate': 'WARNING'}
        problem_msg = HipchatMessage(message_type, msg_inputs, None, None, None, False)
        problem_msg.render_message()
        self.assertEqual(problem_msg.message_color, 'yellow')

        msg_inputs = self.service_inputs % {'longdatetime': datetime.now(),
                                            'notificationtype': 'PROBLEM',
                                            'servicestate': 'CRITICAL'}
        problem_msg = HipchatMessage(message_type, msg_inputs, None, None, None, False)
        problem_msg.render_message()
        self.assertEqual(problem_msg.message_color, 'red')

        # Test short service
        problem_msg = HipchatMessage('short-service', msg_inputs, None, None, None, False)
        problem_msg.render_message()
        self.assertEqual(problem_msg.message_color, 'red')

        msg_inputs = self.service_inputs % {'longdatetime': datetime.now(),
                                            'notificationtype': 'PROBLEM',
                                            'servicestate': 'UNKNOWN'}
        problem_msg = HipchatMessage(message_type, msg_inputs, None, None, None, False)
        problem_msg.render_message()
        self.assertEqual(problem_msg.message_color, 'gray')

        msg_inputs = self.service_inputs % {'longdatetime': datetime.now(),
                                            'notificationtype': 'RECOVERY',
                                            'servicestate': 'OK'}
        problem_msg = HipchatMessage(message_type, msg_inputs, None, None, None, False)
        problem_msg.render_message()
        self.assertEqual(problem_msg.message_color, 'green')

        msg_inputs = self.service_inputs % {'longdatetime': datetime.now(),
                                            'notificationtype': 'ACKNOWLEDGEMENT',
                                            'servicestate': 'CRITICAL'}
        problem_msg = HipchatMessage(message_type, msg_inputs, None, None, None, False)
        problem_msg.render_message()
        self.assertEqual(problem_msg.message_color, 'purple')

########NEW FILE########
