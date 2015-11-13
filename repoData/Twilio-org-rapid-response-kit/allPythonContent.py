__FILENAME__ = install
from clint.textui import colored
import os

print
print
print colored.red(" --- Enter your Twilio information below to complete install --- ")
print
print

account_sid = raw_input('Twilio Account Sid: ')
auth_token = raw_input('Twilio Auth Token: ')

config = """# Configuration Auto-generated during installation
SECRET_KEY = {}
TWILIO_ACCOUNT_SID = '{}'
TWILIO_AUTH_TOKEN = '{}'""".format(repr(os.urandom(20)), account_sid, auth_token)

f = open('rapid_response_kit/utils/config.py', 'w')
f.write(config)
f.close()
########NEW FILE########
__FILENAME__ = app
import argparse

from flask import Flask, render_template
from rapid_response_kit.utils.registry import Registry
from rapid_response_kit.tools import autorespond
from rapid_response_kit.tools import broadcast
from rapid_response_kit.tools import conference_line
from rapid_response_kit.tools import forward
from rapid_response_kit.tools import ringdown
from rapid_response_kit.tools import simplehelp
from rapid_response_kit.tools import survey
from rapid_response_kit.tools import town_hall

app = Flask(__name__)
app.config.from_object('rapid_response_kit.utils.config')

app.config.apps = Registry()

autorespond.install(app)
broadcast.install(app)
conference_line.install(app)
forward.install(app)
ringdown.install(app)
simplehelp.install(app)
survey.install(app)
town_hall.install(app)

@app.route('/')
def home():
    return render_template('home.html')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', default=5000, action="store",
                        help="The port to run the Twilio Toolkit on")
    parser.add_argument('--debug', default=False, action="store_true",
                        help="Turn on debug mode")
    args = parser.parse_args()
    app.run(debug=args.debug, port=args.port)
########NEW FILE########
__FILENAME__ = autorespond
from rapid_response_kit.utils.clients import twilio
from flask import render_template, request, redirect, flash
from rapid_response_kit.utils.helpers import echo_twimlet, twilio_numbers


def install(app):
    app.config.apps.register('autorespond', 'Auto Respond', '/auto-respond')

    @app.route('/auto-respond', methods=['GET'])
    def show_auto_respond():
        numbers = twilio_numbers()
        return render_template("auto-respond.html", numbers=numbers)

    @app.route('/auto-respond', methods=['POST'])
    def do_auto_respond():
        sms_message = request.form.get('sms-message', '')
        voice_message = request.form.get('voice-message', '')

        if len(sms_message) == 0 and len(voice_message) == 0:
            flash('Please provide a message', 'danger')
            return redirect('/auto-respond')

        sms_url = ''
        voice_url = ''

        if len(sms_message) > 0:
            twiml = '<Response><Sms>{}</Sms></Response>'.format(sms_message)
            sms_url = echo_twimlet(twiml)

        if len(voice_message) > 0:
            twiml = '<Response><Say>{}</Say></Response>'.format(voice_message)
            voice_url = echo_twimlet(twiml)

        try:
            client = twilio()
            client.phone_numbers.update(request.form['twilio_number'],
                                        friendly_name='[RRKit] Auto-Respond',
                                        voice_url=voice_url,
                                        voice_method='GET',
                                        sms_url=sms_url,
                                        sms_method='GET')

            flash('Auto-Respond has been configured', 'success')
        except Exception:
            flash('Error configuring number', 'danger')

        return redirect('/auto-respond')
########NEW FILE########
__FILENAME__ = broadcast
from rapid_response_kit.utils.clients import twilio

from flask import render_template, request, flash, redirect
from rapid_response_kit.utils.helpers import parse_numbers, echo_twimlet, twilio_numbers


def install(app):
    app.config.apps.register('broadcast', 'Broadcast', '/broadcast')

    @app.route('/broadcast', methods=['GET'])
    def show_broadcast():
        numbers = twilio_numbers('phone_number')
        return render_template("broadcast.html", numbers=numbers)


    @app.route('/broadcast', methods=['POST'])
    def do_broadcast():
        numbers = parse_numbers(request.form.get('numbers', ''))
        twiml = "<Response><Say>{}</Say></Response>"
        url = echo_twimlet(twiml.format(request.form.get('message', '')))

        client = twilio()

        for number in numbers:
            try:
                if request.form['method'] == 'sms':
                    client.messages.create(
                        body=request.form['message'],
                        to=number,
                        from_=request.form['twilio_number']
                    )
                else:
                    client.calls.create(
                        url=url,
                        to=number,
                        from_=request.form['twilio_number']
                    )
                flash("Sent {} the message".format(number), 'success')
            except Exception:
                flash("Failed to send to {}".format(number), 'danger')

        return redirect('/broadcast')
########NEW FILE########
__FILENAME__ = conference_line
from urllib import urlencode

from rapid_response_kit.utils.clients import twilio
from flask import render_template, request, redirect, flash
from rapid_response_kit.utils.helpers import twilio_numbers, parse_numbers, fallback
from twilio.twiml import Response


def install(app):
    app.config.apps.register('conference-line', 'Conference Line',
                             '/conference-line')

    @app.route('/conference-line', methods=['GET'])
    def show_conference_line():
        numbers = twilio_numbers()
        return render_template("conference-line.html", numbers=numbers)


    @app.route('/conference-line', methods=['POST'])
    def do_conference_line():
        whitelist = parse_numbers(request.form.get('whitelist', ''))
        room = request.form.get('room', '')

        data = {}

        if len(whitelist):
            data['whitelist'] = whitelist

        if len(room):
            data['room'] = room

        qs = urlencode(data, True)
        url = "{}/handle?{}".format(request.base_url, qs)

        try:
            client = twilio()
            client.phone_numbers.update(request.form['twilio_number'],
                                        friendly_name='[RRKit] Conference Line',
                                        voice_url=url,
                                        voice_method='GET',
                                        fallback_voice_url=fallback(),
                                        fallback_voice_method='GET')

            flash('Conference Line configured', 'success')
        except Exception:
            flash('Error configuring number', 'danger')

        return redirect('/conference-line')

    @app.route('/conference-line/handle')
    def handle_conference_line():
        whitelist = request.args.getlist('whitelist')

        if len(whitelist) > 0:
            if request.args['From'] not in whitelist:
                resp = Response()
                resp.say('Sorry, you are not authorized to call this number')
                return str(resp)

        room = request.args.get('room', False)

        if room:
            resp = Response()
            with resp.dial() as d:
                d.conference(room)
            return str(resp)

        # Gather the room code
        resp = Response()
        with resp.gather(numDigits=3, action='/conference-line/connect',
                         method='GET') as g:
            g.say("Enter a 3-digit room code")

        return str(resp)

    @app.route('/conference-line/connect')
    def connect_conference_line():
        resp = Response()
        with resp.dial() as d:
            d.conference(request.args['Digits'])
        return str(resp)
########NEW FILE########
__FILENAME__ = forward
from rapid_response_kit.utils.clients import twilio
from flask import render_template, request, redirect, flash
from rapid_response_kit.utils.helpers import echo_twimlet, convert_to_e164, twilio_numbers


def install(app):
    app.config.apps.register('forwarder', 'Forwarder', '/forwarder')

    @app.route('/forwarder', methods=['GET'])
    def show_forwarder():
        numbers = twilio_numbers()
        return render_template("forwarder.html", numbers=numbers)


    @app.route('/forwarder', methods=['POST'])
    def do_forwarder():
        normalized = convert_to_e164(request.form.get('number', ''))

        if not normalized:
            flash('Phone number is invalid, please try again', 'danger')
            return redirect('/forwarder')

        twiml = '<Response><Dial>{}</Dial></Response>'.format(normalized)
        url = echo_twimlet(twiml)

        try:
            client = twilio()
            client.phone_numbers.update(request.form['twilio_number'],
                                        friendly_name='[RRKit] Forwarder',
                                        voice_url=url,
                                        voice_method='GET')

            flash('Number configured', 'success')
        except Exception:
            flash('Error configuring number', 'danger')

        return redirect('/forwarder')
########NEW FILE########
__FILENAME__ = ringdown
from urllib import urlencode

from rapid_response_kit.utils.clients import twilio
from flask import render_template, request, redirect, flash
from rapid_response_kit.utils.helpers import parse_numbers, echo_twimlet, twilio_numbers
from twilio.twiml import Response


def install(app):
    app.config.apps.register('ringdown', 'Ringdown', '/ringdown')

    @app.route('/ringdown', methods=['GET'])
    def show_ringdown():
        numbers = twilio_numbers()
        return render_template("ringdown.html", numbers=numbers)


    @app.route('/ringdown', methods=['POST'])
    def do_ringdown():
        numbers = parse_numbers(request.form.get('numbers', ''))
        data = {
            'stack': numbers,
            'sorry': request.form.get('sorry', '')
        }

        url = "{}/handle?{}".format(request.base_url, urlencode(data, True))

        twiml = '<Response><Say>System is down for maintenance</Say></Response>'
        fallback_url = echo_twimlet(twiml)

        try:
            client = twilio()
            client.phone_numbers.update(request.form['twilio_number'],
                                        friendly_name='[RRKit] Ringdown',
                                        voice_url=url,
                                        voice_method='GET',
                                        voice_fallback_url=fallback_url,
                                        voice_fallback_method='GET')

            flash('Number configured', 'success')
        except Exception:
            flash('Error configuring number', 'danger')

        return redirect('/ringdown')

    @app.route('/ringdown/handle')
    def handle_ringdown():
        stack = request.args.getlist('stack')
        sorry = request.args.get('sorry', 'Sorry, no one answered')

        if len(stack) == 0:
            # Nothing else to ringdown
            resp = Response()
            resp.say(sorry)

            return str(resp)

        top = stack.pop(0)

        data = {
            'stack': stack,
            'sorry': sorry
        }

        qs = urlencode(data, True)

        resp = Response()
        resp.dial(top, timeout=10, action="/ringdown/handle?{}".format(qs),
                  method='GET')

        return str(resp)
########NEW FILE########
__FILENAME__ = simplehelp
from urllib import urlencode

from rapid_response_kit.utils.clients import twilio
from flask import render_template, request, redirect, flash
from rapid_response_kit.utils.helpers import echo_twimlet
from twilio.twiml import Response
from rapid_response_kit.utils.helpers import twilio_numbers


keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#']
start_menu = "Thank you for calling {}."
opt_say = "{}, press {}."
err_say = "Sorry, that's not a valid choice."
end_say = "Thank you for calling, goodbye."
voice = 'alice'


def install(app):
    app.config.apps.register('simplehelp', 'Simple Help Line', '/simplehelp')

    @app.route('/simplehelp', methods=['GET'])
    def show_simplehelp():
        numbers = twilio_numbers()
        return render_template("simplehelp.html", keys=keys, numbers=numbers)


    @app.route('/simplehelp', methods=['POST'])
    def do_simplehelp():

        data = parse_form(request.form)
        url = "{}/handle?{}".format(request.base_url, urlencode(data, True))
        twiml = '<Response><Say>System is down for maintenance</Say></Response>'
        fallback_url = echo_twimlet(twiml)

        try:
            client = twilio()
            client.phone_numbers.update(request.form['twilio_number'],
                                        friendly_name='[RRKit] Simple Help Line',
                                        voice_url=url,
                                        voice_method='GET',
                                        voice_fallback_url=fallback_url,
                                        voice_fallback_method='GET')

            flash('Help menu configured', 'success')
        except Exception as e:
            print(e)
            flash('Error configuring help menu', 'danger')

        return redirect('/simplehelp')

    @app.route('/simplehelp/handle', methods=['GET'])
    def handle_menu():

        url = "{}?{}".format(request.base_url, request.query_string)

        response = Response()
        response.say(start_menu.format(request.args.get('name')), voice=voice)
        gather = response.gather(numDigits=1, action=url, method='POST')

        for key in keys:
            opt = request.args.get('opt_' + key)

            if opt is None:
                continue

            opt_args = opt.split(':')
            gather.say(opt_say.format(opt_args[1], key), voice=voice)

        return str(response)

    @app.route('/simplehelp/handle', methods=['POST'])
    def handle_opt():
        response = Response()

        digit = request.form['Digits']
        opt = request.args.get('opt_' + digit, None)

        if opt is None:
            response.say(err_say)
            response.redirect(
                "{}?{}".format(request.base_url, request.query_string))
            return str(response)

        opt_args = opt.split(':')

        if opt_args[0] == 'Call':
            response.dial(opt_args[2])
        elif opt_args[0] == 'Info':
            response.say(opt_args[2], voice=voice)
            response.say(end_say, voice=voice)

        return str(response)


def parse_form(form):
    data = {'name': form.get('menu_name', '')}

    for key in keys:
        if form.get('type_' + key, 'Inactive') == "Inactive":
            continue

        data['opt_' + key] = "{}:{}:{}".format(form['type_' + key],
                                               form['desc_' + key],
                                               form['value_' + key])

    return data
########NEW FILE########
__FILENAME__ = survey
import uuid

from rapid_response_kit.utils.clients import parse_connect, twilio
from clint.textui import colored
from flask import render_template, request, flash, redirect
from rapid_response_kit.utils.helpers import twilio_numbers, parse_numbers
from parse_rest.datatypes import Object as pObject
from twilio.twiml import Response


class SurveyResult(pObject):
    pass


def install(app):
    if not parse_connect(app.config):
        print colored.red(
            'Survey requires Parse, please add PARSE_APP_ID and PARSE_REST_KEY to your config.py')
        return

    app.config.apps.register('survey', 'Survey', '/survey')

    @app.route('/survey', methods=['GET'])
    def show_survey():
        numbers = twilio_numbers()
        return render_template('survey.html', numbers=numbers)

    @app.route('/survey', methods=['POST'])
    def do_survey():
        numbers = parse_numbers(request.form['numbers'])

        survey = uuid.uuid4()

        url = "{}/handle?survey={}".format(request.base_url, survey)

        client = twilio()

        try:
            client.phone_numbers.update(request.form['twilio_number'],
                                        sms_url=url,
                                        sms_method='GET',
                                        friendly_name='[RRKit] Survey')
        except:
            flash('Unable to update number', 'danger')
            return redirect('/survey')

        from_number = client.phone_numbers.get(request.form['twilio_number'])

        flash('Survey is now running as {}'.format(survey), 'info')

        body = "{} Reply YES / NO".format(request.form['question'])

        for number in numbers:
            try:
                client.messages.create(
                    body=body,
                    to=number,
                    from_=from_number.phone_number
                )
                flash('Sent {} the survey'.format(number), 'success')
            except Exception as e:
                flash("Failed to send to {}".format(number), 'danger')

        return redirect('/survey')

    @app.route('/survey/handle')
    def handle_survey():
        body = request.args['Body']
        normalized = body.strip().lower()

        result = SurveyResult.Query.filter(number=request.args['From'],
                                           survey_id=request.args['survey'])

        if result.count() > 0:
            resp = Response()
            resp.sms('Your response has been recorded')
            return str(resp)

        normalized = normalized if normalized in ['yes', 'no'] else 'N/A'

        result = SurveyResult(raw=body, normalized=normalized,
                              number=request.args['From'],
                              survey_id=request.args['survey'])

        result.save()

        resp = Response()
        resp.sms('Thanks for answering our survey')
        return str(resp)

########NEW FILE########
__FILENAME__ = town_hall
from rapid_response_kit.utils.clients import twilio
from flask import render_template, request, redirect, flash
from rapid_response_kit.utils.helpers import parse_numbers, echo_twimlet, twilio_numbers


def install(app):
    app.config.apps.register('town-hall', 'Town Hall', '/town-hall')

    @app.route('/town-hall', methods=['GET'])
    def show_town_hall():
        numbers = twilio_numbers('phone_number')
        return render_template("town-hall.html", numbers=numbers)


    @app.route('/town-hall', methods=['POST'])
    def do_town_hall():
        numbers = parse_numbers(request.form.get('numbers', ''))
        twiml = '<Response><Dial><Conference>{}</Conference></Dial></Response>'
        room = request.form.get('room', 'town-hall')
        url = echo_twimlet(twiml.format(room))

        client = twilio()

        for number in numbers:
            try:
                client.calls.create(
                    url=url,
                    to=number,
                    from_=request.form['twilio_number']
                )
                flash('{} contacted to join {}'.format(number, room), 'success')
            except Exception:
                flash('Unable to contact {}'.format(number))

        return redirect('/town-hall')
########NEW FILE########
__FILENAME__ = clients
from flask import current_app as app
from parse_rest.connection import register
from twilio.rest import TwilioRestClient


def twilio():
    return TwilioRestClient(app.config['TWILIO_ACCOUNT_SID'],
                            app.config['TWILIO_AUTH_TOKEN'])


def parse_connect(config=None):
    if config is None:
        config = app.config

    app_id = config.get('PARSE_APP_ID', None)
    rest_key = config.get('PARSE_REST_KEY', None)

    if not (app_id and rest_key):
        return False

    try:
        register(app_id, rest_key)
        return True
    except:
        return False
########NEW FILE########
__FILENAME__ = helpers
from urllib import urlencode
from urlparse import urlunparse

from rapid_response_kit.utils.clients import twilio
import phonenumbers


def parse_numbers(raw):
    numbers = raw.split("\n")
    result = []
    for number in numbers:
        converted = convert_to_e164(number)
        if converted and converted not in result:
            result.append(converted)

    return result


def convert_to_e164(raw_phone):
    if not raw_phone:
        return

    if raw_phone[0] == '+':
        # Phone number may already be in E.164 format.
        parse_type = None
    else:
        # If no country code information present, assume it's a US number
        parse_type = "US"

    try:
        phone_representation = phonenumbers.parse(raw_phone, parse_type)
    except phonenumbers.NumberParseException:
        return None

    return phonenumbers.format_number(phone_representation,
                                      phonenumbers.PhoneNumberFormat.E164)


def echo_twimlet(twiml):
    params = {'Twiml': twiml}
    qs = urlencode(params)
    return urlunparse(('http', 'twimlets.com', 'echo', '', qs, ''))


def fallback(message='Sorry the service is down for maintenance'):
    twiml = '<Response><Say>{}</Say></Response>'.format(message)
    return echo_twimlet(twiml)


def twilio_numbers(id_field='sid'):
    client = twilio()

    numbers = client.phone_numbers.list()

    result = []
    for number in numbers:
        if number.friendly_name.startswith('[RRKit]'):
            display_name = '[{}] {}'.format(number.friendly_name[len('[RRKit]') + 1:], number.phone_number)
        else:
            display_name = number.phone_number

        result.append((getattr(number, id_field), display_name))

    return result


########NEW FILE########
__FILENAME__ = registry
from collections import OrderedDict
from clint.textui import colored


class AlreadyRegistered(Exception):
    pass


class Registry(object):
    def __init__(self):
        self.registry = OrderedDict()

    def register(self, app_id, name, link):
        if app_id in self.registry:
            raise AlreadyRegistered

        print "Registering {} at {}".format(colored.cyan(name), colored.cyan(link))
        self.registry[app_id] = {
            'name': name,
            'link': link,
        }
########NEW FILE########
__FILENAME__ = base
from unittest import TestCase
from mock import patch, Mock


class KitTestCase(TestCase):
    def start_patch(self, tool):
         # Patch all requests to twilio_numbers()
        self.twilio_numbers_patcher = patch('rapid_response_kit.tools.{}.twilio_numbers'.format(tool))
        self.twilio_numbers_patch = self.twilio_numbers_patcher.start()
        self.twilio_numbers_patch.return_value = []

        # Patch all requests to twilio()
        self.twilio_patcher = patch('rapid_response_kit.tools.{}.twilio'.format(tool))
        self.twilio_patch = self.twilio_patcher.start()
        self.patchio = Mock()
        self.twilio_patch.return_value = self.patchio

    def stop_patch(self):
        self.twilio_numbers_patcher.stop()
        self.twilio_patcher.stop()

########NEW FILE########
__FILENAME__ = test_autorespond
from nose.tools import assert_equal
from rapid_response_kit.app import app
from tests.base import KitTestCase


class AutorespondTestCase(KitTestCase):

    def setUp(self):
        self.app = app.test_client()
        self.start_patch('autorespond')

    def tearDown(self):
        self.stop_patch()

    def test_get(self):
        response = self.app.get('/auto-respond')
        assert_equal(response.status_code, 200)

    def test_post_invalid(self):
        response = self.app.post('/auto-respond', data={},
                                 follow_redirects=True)
        assert 'Please provide a message' in response.data

    def test_post_valid_sms(self):
        self.app.post('/auto-respond', data={'sms-message': 'Test Message',
                                             'twilio_number': 'PNSid'})

        expected_url = 'http://twimlets.com/echo?Twiml=%3CResponse%3E%3CSms%3ETest+Message%3C%2FSms%3E%3C%2FResponse%3E'

        self.patchio.phone_numbers.update.assert_called_with(
            'PNSid',
            friendly_name='[RRKit] Auto-Respond',
            voice_url='',
            voice_method='GET',
            sms_method='GET',
            sms_url=expected_url)

    def test_post_valid_voice(self):
        self.app.post('/auto-respond', data={'voice-message': 'Test Message',
                                             'twilio_number': 'PNSid'})

        expected_url = 'http://twimlets.com/echo?Twiml=%3CResponse%3E%3CSay%3ETest+Message%3C%2FSay%3E%3C%2FResponse%3E'

        self.patchio.phone_numbers.update.assert_called_with(
            'PNSid',
            friendly_name='[RRKit] Auto-Respond',
            voice_url=expected_url,
            voice_method='GET',
            sms_method='GET',
            sms_url='')




########NEW FILE########
__FILENAME__ = test_broadcast
from mock import patch, Mock, call
from nose.tools import assert_equal
from rapid_response_kit.app import app
from tests.base import KitTestCase


class BroadcastTestCase(KitTestCase):

    def setUp(self):
        self.app = app.test_client()
        self.start_patch('broadcast')

    def tearDown(self):
        self.stop_patch()

    def test_get(self):
        response = self.app.get('/broadcast')
        assert_equal(response.status_code, 200)

    def test_post_sms(self):
        self.app.post('/broadcast', data={'method': 'sms',
                                          'twilio_number': '1415TWILIO',
                                          'numbers': '14158675309',
                                          'message': 'Test Broadcast'})

        self.patchio.messages.create.assert_called_with(
            body='Test Broadcast',
            to='+14158675309',
            from_='1415TWILIO')

    def test_post_sms_multi(self):
        self.app.post('/broadcast', data={'method': 'sms',
                                          'twilio_number': '1415TWILIO',
                                          'numbers': '14158675309\n14158675310',
                                          'message': 'Test Broadcast'})

        self.patchio.messages.create.assert_has_calls([
            call(
                body='Test Broadcast',
                to='+14158675309',
                from_='1415TWILIO'
            ),
            call(
                body='Test Broadcast',
                to='+14158675310',
                from_='1415TWILIO'
            ),
        ])

    def test_post_call(self):
        self.app.post('/broadcast', data={'method': 'voice',
                                          'twilio_number': '1415TWILIO',
                                          'numbers': '14158675309',
                                          'message': 'Test Broadcast'})

        self.patchio.calls.create.assert_called_with(
            url='http://twimlets.com/echo?Twiml=%3CResponse%3E%3CSay%3ETest+Broadcast%3C%2FSay%3E%3C%2FResponse%3E',
            to='+14158675309',
            from_='1415TWILIO')

    def test_post_call_multi(self):
        self.app.post('/broadcast', data={'method': 'voice',
                                          'twilio_number': '1415TWILIO',
                                          'numbers': '14158675309\n14158675310',
                                          'message': 'Test Broadcast'})

        self.patchio.calls.create.assert_has_calls([
            call(
                url='http://twimlets.com/echo?Twiml=%3CResponse%3E%3CSay%3ETest+Broadcast%3C%2FSay%3E%3C%2FResponse%3E',
                to='+14158675309',
                from_='1415TWILIO'
            ),
            call(
                url='http://twimlets.com/echo?Twiml=%3CResponse%3E%3CSay%3ETest+Broadcast%3C%2FSay%3E%3C%2FResponse%3E',
                to='+14158675310',
                from_='1415TWILIO'
            ),
        ])




########NEW FILE########
__FILENAME__ = test_conference_line
from nose.tools import assert_equal
from rapid_response_kit.app import app
from tests.base import KitTestCase


class ConferenceLineTestCase(KitTestCase):

    def setUp(self):
        self.app = app.test_client()
        self.start_patch('conference_line')

    def tearDown(self):
        self.stop_patch()

    def test_get(self):
        response = self.app.get('/conference-line')
        assert_equal(response.status_code, 200)

    def test_post(self):
        self.app.post('/conference-line', data={'whitelist': '14158675309\n14158675310',
                                                'room': '1234',
                                                'twilio_number': 'PNSid'})

        expected_fallback_url = 'http://twimlets.com/echo?Twiml=%3CResponse%3E%3CSay%3ESorry+the+service+is+down+for+maintenance%3C%2FSay%3E%3C%2FResponse%3E'
        expected_voice_url = 'http://localhost/conference-line/handle?whitelist=%2B14158675309&whitelist=%2B14158675310&room=1234'

        self.patchio.phone_numbers.update.assert_called_with(
            'PNSid',
            fallback_voice_url=expected_fallback_url,
            friendly_name='[RRKit] Conference Line',
            voice_method='GET',
            fallback_voice_method='GET',
            voice_url=expected_voice_url)

    def test_handle_not_in_whitelist(self):
        response = self.app.get('/conference-line/handle?whitelist=%2B14158675309&whitelist=%2B14158675310&room=1234&From=%2B14155551234')
        assert 'Sorry, you are not authorized to call this number' in response.data

    def test_handle_fully_qualifed(self):
        response = self.app.get('/conference-line/handle?whitelist=%2B14158675309&whitelist=%2B14158675310&room=1234&From=%2B14158675309')
        assert '<Conference>1234</Conference>' in response.data

    def test_handle_partially_qualified(self):
        response = self.app.get('/conference-line/handle?whitelist=%2B14158675309&whitelist=%2B14158675310&From=%2B14158675309')
        print response.data
        assert '<Gather action="/conference-line/connect" method="GET" numDigits="3">' in response.data

    def test_connect(self):
        response = self.app.get('/conference-line/connect?Digits=1234')
        assert '<Conference>1234</Conference>' in response.data
########NEW FILE########
__FILENAME__ = test_forward
from nose.tools import assert_equal
from rapid_response_kit.app import app
from tests.base import KitTestCase


class ForwardTestCase(KitTestCase):

    def setUp(self):
        self.app = app.test_client()
        self.start_patch('forward')

    def tearDown(self):
        self.stop_patch()

    def test_get(self):
        response = self.app.get('/forwarder')
        assert_equal(response.status_code, 200)

    def test_post(self):
        self.app.post('/forwarder', data={'number': '4158675309',
                                          'twilio_number': 'PNSid'})

        expected_url = 'http://twimlets.com/echo?Twiml=%3CResponse%3E%3CDial%3E%2B14158675309%3C%2FDial%3E%3C%2FResponse%3E'

        self.patchio.phone_numbers.update.assert_called_with(
            'PNSid',
            voice_url=expected_url,
            friendly_name='[RRKit] Forwarder',
            voice_method='GET')
########NEW FILE########
__FILENAME__ = test_ringdown
from nose.tools import assert_equal
from rapid_response_kit.app import app
from tests.base import KitTestCase


class RingdownTestCase(KitTestCase):

    def setUp(self):
        self.app = app.test_client()
        self.start_patch('ringdown')

    def tearDown(self):
        self.stop_patch()

    def test_get(self):
        response = self.app.get('/ringdown')
        assert_equal(response.status_code, 200)

    def test_post(self):
        self.app.post('/ringdown', data={'numbers': '4158675309\n4158675310',
                                         'twilio_number': 'PNSid'})

        expected_voice_url = 'http://localhost/ringdown/handle?sorry=&stack=%2B14158675309&stack=%2B14158675310'
        expected_fallback_url = 'http://twimlets.com/echo?Twiml=%3CResponse%3E%3CSay%3ESystem+is+down+for+maintenance%3C%2FSay%3E%3C%2FResponse%3E'

        self.patchio.phone_numbers.update.assert_called_with(
            'PNSid',
            voice_url=expected_voice_url,
            voice_fallback_method='GET',
            friendly_name='[RRKit] Ringdown',
            voice_method='GET',
            voice_fallback_url=expected_fallback_url)

    def test_handle_remaining_stack(self):
        response = self.app.get('/ringdown/handle?stack=%2B14158675309')
        assert '<Dial' in response.data
        assert '+14158675309' in response.data

    def test_handle_exhausted_stack(self):
        response = self.app.get('/ringdown/handle')
        assert 'Sorry, no one answered' in response.data

    def test_handle_exhausted_stack_custom(self):
        response = self.app.get('/ringdown/handle?sorry=Custom+Message')
        assert 'Custom Message' in response.data

########NEW FILE########
__FILENAME__ = test_simplehelp
from nose.tools import assert_equal
from rapid_response_kit.app import app
from tests.base import KitTestCase


class SimpleHelpTestCase(KitTestCase):

    def setUp(self):
        self.app = app.test_client()
        self.start_patch('simplehelp')

    def tearDown(self):
        self.stop_patch()

    def test_get(self):
        response = self.app.get('/simplehelp')
        assert_equal(response.status_code, 200)

    def test_post(self):
        self.app.post('/simplehelp', data={'menu_name': 'Tommy Tutone',
                                           'type_1': 'Call',
                                           'desc_1': 'Call Jenny',
                                           'value_1': '4158675309',
                                           'type_2': 'Info',
                                           'desc_2': 'Lost and Found',
                                           'value_2': 'I got your number',
                                           'twilio_number': 'PNSid'})

        expected_voice_url = 'http://localhost/simplehelp/handle?name=Tommy+Tutone&opt_1=Call%3ACall+Jenny%3A4158675309&opt_2=Info%3ALost+and+Found%3AI+got+your+number'
        expected_fallback_url = 'http://twimlets.com/echo?Twiml=%3CResponse%3E%3CSay%3ESystem+is+down+for+maintenance%3C%2FSay%3E%3C%2FResponse%3E'

        self.patchio.phone_numbers.update.assert_called_with(
            'PNSid',
            voice_url=expected_voice_url,
            voice_fallback_method='GET',
            friendly_name='[RRKit] Simple Help Line',
            voice_method='GET',
            voice_fallback_url=expected_fallback_url)

    def test_handle(self):
        response = self.app.get('/simplehelp/handle?name=Tommy+Tutone&opt_1=Call%3ACall+Jenny%3A4158675309&opt_2=Info%3ALost+and+Found%3AI+got+your+number')
        assert 'Thank you for calling Tommy Tutone' in response.data
        assert 'Call Jenny, press 1' in response.data
        assert 'Lost and Found, press 2' in response.data

    def test_handle_call(self):
        response = self.app.post('/simplehelp/handle?name=Tommy+Tutone&opt_1=Call%3ACall+Jenny%3A4158675309&opt_2=Info%3ALost+and+Found%3AI+got+your+number', data={'Digits': '1'})
        assert '<Dial>4158675309</Dial>' in response.data

    def test_handle_info(self):
        response = self.app.post('/simplehelp/handle?name=Tommy+Tutone&opt_1=Call%3ACall+Jenny%3A4158675309&opt_2=Info%3ALost+and+Found%3AI+got+your+number', data={'Digits': '2'})
        assert 'I got your number' in response.data

    def test_handle_invalid(self):
        response = self.app.post('/simplehelp/handle?name=Tommy+Tutone&opt_1=Call%3ACall+Jenny%3A4158675309&opt_2=Info%3ALost+and+Found%3AI+got+your+number', data={'Digits': '3'})
        assert "Sorry, that's not a valid choice" in response.data

########NEW FILE########
__FILENAME__ = test_town_hall
from mock import call
from nose.tools import assert_equal
from rapid_response_kit.app import app
from tests.base import KitTestCase


class TownHallTestCase(KitTestCase):

    def setUp(self):
        self.app = app.test_client()
        self.start_patch('town_hall')

    def tearDown(self):
        self.stop_patch()

    def test_get(self):
        response = self.app.get('/town-hall')
        assert_equal(response.status_code, 200)

    def test_post(self):
        self.app.post('/town-hall', data={'numbers': '4158675309\n4158675310',
                                          'twilio_number': '1415TWILIO'})

        join_url = 'http://twimlets.com/echo?Twiml=%3CResponse%3E%3CDial%3E%3CConference%3Etown-hall%3C%2FConference%3E%3C%2FDial%3E%3C%2FResponse%3E'

        self.patchio.calls.create.assert_has_calls([
            call(
                url=join_url,
                to='+14158675309',
                from_='1415TWILIO'
            ),
            call(
                url=join_url,
                to='+14158675310',
                from_='1415TWILIO'
            )
        ])


########NEW FILE########
