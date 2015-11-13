__FILENAME__ = settings
GEVENT_CHECKS = True

THROTTLE_SECONDS = 60 * 60
THROTTLE_LIMIT = 1800

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0


try:
    from settings_local import *
except ImportError:
    pass

import redis
cache = redis.StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB)
########NEW FILE########
__FILENAME__ = spelling
import re, collections

__doc__ = """

Peter Norvig's famous spell checker.

"""

def words(text): return re.findall('[a-z]+', text.lower()) 

def train(features):
    model = collections.defaultdict(lambda: 1)
    for f in features:
        model[f] += 1
    return model

NWORDS = train(['gmail', 'yahoo', 'aol', 'hotmail', 'msn', 'sbcglobal', 'bellsouth', 'earthlink', 'com', 'net', 'org'])

alphabet = 'abcdefghijklmnopqrstuvwxyz'

def edits1(word):
   splits     = [(word[:i], word[i:]) for i in range(len(word) + 1)]
   deletes    = [a + b[1:] for a, b in splits if b]
   transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b)>1]
   replaces   = [a + c + b[1:] for a, b in splits for c in alphabet if b]
   inserts    = [a + c + b     for a, b in splits for c in alphabet]
   return set(deletes + transposes + replaces + inserts)

def known_edits2(word):
    return set(e2 for e1 in edits1(word) for e2 in edits1(e1) if e2 in NWORDS)

def known(words): return set(w for w in words if w in NWORDS)

def correct(word):
    candidates = known([word]) or known(edits1(word)) or known_edits2(word) or [word]
    return max(candidates, key=NWORDS.get)

########NEW FILE########
__FILENAME__ = throttle
from hashlib import md5
import time
import simplejson

from emailpie import settings
cache = settings.cache


def should_be_throttled(identifier, SECONDS=settings.THROTTLE_SECONDS,
                                    LIMIT=settings.THROTTLE_LIMIT):
    """
    Maintains a list of timestamps when the user accessed the api within
    the cache.

    Returns `False` if the user should NOT be throttled or `True` if
    the user should be throttled.
    """
    key = 'throttle-' + md5(identifier).hexdigest()

    # Make sure something is there.
    cache.setnx(key, '[]')

    # eed out anything older than the timeframe.
    minimum_time = int(time.time()) - SECONDS
    times = simplejson.loads(cache.get(key))
    times_accessed = [access for access in times if access >= minimum_time]

    # Check times accessed count.
    if len(times_accessed) >= LIMIT:
        return True

    # update times accessed
    times_accessed.append(int(time.time()))
    cache.set(key, simplejson.dumps(times_accessed))
    cache.expire(key, SECONDS)

    return False

def reset_throttle(identifier):
    key = 'throttle-' + md5(identifier).hexdigest()
    cache.delete(key)

########NEW FILE########
__FILENAME__ = utils
import re

import gevent

from DNS.Base import ServerError

from emailpie import settings


def mxlookup(domain):
    from DNS import Base

    def dnslookup(name, qtype):
        """convenience routine to return just answer data for any query type"""
        if Base.defaults['server'] == []: Base.DiscoverNameServers()
        result = Base.DnsRequest(name=name, qtype=qtype, timout=5).req()
        if result.header['status'] != 'NOERROR':
            raise ServerError("DNS query status: %s" % result.header['status'],
                result.header['rcode'])
        elif len(result.answers) == 0 and Base.defaults['server_rotate']:
            # check with next DNS server
            result = Base.DnsRequest(name=name, qtype=qtype, timout=5).req()
        if result.header['status'] != 'NOERROR':
            raise ServerError("DNS query status: %s" % result.header['status'],
                result.header['rcode'])
        return [x['data'] for x in result.answers]

    def _mxlookup(name):
        """
        convenience routine for doing an MX lookup of a name. returns a
        sorted list of (preference, mail exchanger) records
        """
        l = dnslookup(name, qtype='mx')
        l.sort()
        return l

    return _mxlookup(domain)


class EmailChecker(object):
    """
    Given an email address, run a variety of checks on that email address.

    A check is any method starting with `check_` that returns a list of errors.
    Errors are dictionaries with a message (str) and severity (int) key.
    """

    def __init__(self, email, _gevent=settings.GEVENT_CHECKS):
        self.email = email
        self.errors = []
        self.mx_records = None

        self._gevent = _gevent

    @property
    def username(self):
        return self.email.split('@')[0]

    @property
    def domain(self):
        try:
            return self.email.split('@')[1]
        except IndexError:
            return None

    def didyoumean(self):
        from emailpie.spelling import correct

        if self.domain:
            items = self.domain.split('.')

            suggestion = '{0}@{1}'.format(
                self.username,
                '.'.join(map(correct, items))
            )

            if suggestion == self.email:
                return None
            return suggestion

        return None

    @property
    def checks(self):
        """
        Collects all functions that start with `check_`.
        """
        out = []
        for name in dir(self):
            if name.startswith('check_'):
                out.append(getattr(self, name))
        return out

    def validate(self):
        """
            1. Run each check, fill up self.jobs.
            2. Join all jobs together.
            3. Each job returns a list of errors.
            4. Condense and return each error.
        """
        if self._gevent:
            results = [gevent.spawn(check) for check in self.checks]
            gevent.joinall(results, timeout=7)

            for result in results:
                if result.value:
                    self.errors += result.value
        else:
            for result in [check() for check in self.checks]:
                self.errors += result

        return self.errors


    ############
    ## CHECKS ##
    ############
    
    def check_valid_email_string(self):
        """
        A simple regex based checker.

        Yeah, yeah. Using Django's validator. This needs to be
        fixed and the django dep removed.
        """
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError

        try:
            validate_email(self.email)
            return []
        except:
            return [dict(
                severity=10,
                message='Invalid email address.'
            )]

    def check_valid_mx_records(self):
        """
        Ensures that there are MX records for this domain.
        """
        error = dict(
            severity=7,
            message='No MX records found for the domain.'
        )

        if not self.domain:
            return [error]

        try:
            self.mx_records = mxlookup(self.domain)
            if len(self.mx_records) == 0:
                return [error]
        except ServerError:
            return [error]

        return []

    def check_nothing(self):
        return []
########NEW FILE########
__FILENAME__ = views
import simplejson

from emailpie import app
from emailpie.utils import EmailChecker
from emailpie.throttle import should_be_throttled

from flask import request, render_template, Response


@app.route('/', methods=['GET'])
def docs():
    return render_template('index.html')


@app.route('/v1/check', methods=['GET'])
def check():
    email = request.args.get('email', None)

    response = dict(success=True, errors=[], didyoumean=None)

    if should_be_throttled(request.remote_addr):
        return Response(simplejson.dumps(['throttled']),
            status_code=403,
            mimetype='application/json')

    if not email:
        response['errors'] += [dict(
                    severity=10,
                    message='Please provide an email address.')]
    else:
        validator = EmailChecker(email)
        response['errors'] = validator.validate()
        response['didyoumean'] = validator.didyoumean()

    for error in response['errors']:
        if error['severity'] > 5:
            response['success'] = False

    return Response(simplejson.dumps(response, indent=2),
        mimetype='application/json')

########NEW FILE########
__FILENAME__ = rundev
from gevent import monkey
monkey.patch_all()


from emailpie import app
app.run(debug=True)

########NEW FILE########
__FILENAME__ = tests
from gevent import monkey
monkey.patch_all()

import unittest

from emailpie import utils
from emailpie.spelling import correct
from emailpie.throttle import should_be_throttled, reset_throttle

class TestParse(unittest.TestCase):
    def test_good_email(self):
        validator = utils.EmailChecker('bryan@bryanhelmig.com')
        errors = validator.validate()

        self.assertFalse(errors)

    def test_good_plus_email(self):
        validator = utils.EmailChecker('bryan+merica@bryanhelmig.com')
        errors = validator.validate()

        self.assertFalse(errors)

    def test_invalid_email(self):
        validator = utils.EmailChecker('sdahjsdfh.asdofh')
        errors = validator.validate()

        self.assertTrue(errors)

    def test_double_invalid_email(self):
        validator = utils.EmailChecker('sdahjsdfh@@sssss')
        errors = validator.validate()

        self.assertTrue(errors)

    def test_invalid_mx_email(self):
        validator = utils.EmailChecker('bryan@example.com')
        errors = validator.validate()

        self.assertTrue(errors)

    def test_invalid_domain(self):
        validator = utils.EmailChecker('bryan@asdahsdfgasdfgyadfiuyadsfguy.com')
        errors = validator.validate()

        self.assertTrue(errors)

    def test_mispelled_domain(self):
        validator = utils.EmailChecker('bryan@gnail.con')
        self.assertEquals('bryan@gmail.com', validator.didyoumean())


class SpellingTest(unittest.TestCase):
    def test_simple_mispell(self):
        self.assertEquals('gmail', correct('gnail'))
        self.assertEquals('yahoo', correct('uahoo'))
        self.assertEquals('sakjfh', correct('sakjfh'))
        self.assertEquals('guess', correct('guess'))


class ThrottleTest(unittest.TestCase):
    def test_throttle(self):
        for x in range(100):
            self.assertFalse(should_be_throttled('mykey'))

        self.assertTrue(should_be_throttled('mykey', LIMIT=50))

        reset_throttle('mykey')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
