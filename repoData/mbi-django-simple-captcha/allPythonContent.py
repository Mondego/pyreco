__FILENAME__ = settings
﻿import os
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

CAPTCHA_FONT_PATH = getattr(settings, 'CAPTCHA_FONT_PATH', os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'fonts/Vera.ttf')))
CAPTCHA_FONT_SIZE = getattr(settings, 'CAPTCHA_FONT_SIZE', 22)
CAPTCHA_LETTER_ROTATION = getattr(settings, 'CAPTCHA_LETTER_ROTATION', (-35, 35))
CAPTCHA_BACKGROUND_COLOR = getattr(settings, 'CAPTCHA_BACKGROUND_COLOR', '#ffffff')
CAPTCHA_FOREGROUND_COLOR = getattr(settings, 'CAPTCHA_FOREGROUND_COLOR', '#001100')
CAPTCHA_CHALLENGE_FUNCT = getattr(settings, 'CAPTCHA_CHALLENGE_FUNCT', 'captcha.helpers.random_char_challenge')
CAPTCHA_NOISE_FUNCTIONS = getattr(settings, 'CAPTCHA_NOISE_FUNCTIONS', ('captcha.helpers.noise_arcs', 'captcha.helpers.noise_dots',))
CAPTCHA_FILTER_FUNCTIONS = getattr(settings, 'CAPTCHA_FILTER_FUNCTIONS', ('captcha.helpers.post_smooth',))
CAPTCHA_WORDS_DICTIONARY = getattr(settings, 'CAPTCHA_WORDS_DICTIONARY', '/usr/share/dict/words')
CAPTCHA_PUNCTUATION = getattr(settings, 'CAPTCHA_PUNCTUATION', '''_"',.;:-''')
CAPTCHA_FLITE_PATH = getattr(settings, 'CAPTCHA_FLITE_PATH', None)
CAPTCHA_TIMEOUT = getattr(settings, 'CAPTCHA_TIMEOUT', 5)  # Minutes
CAPTCHA_LENGTH = int(getattr(settings, 'CAPTCHA_LENGTH', 4))  # Chars
CAPTCHA_IMAGE_BEFORE_FIELD = getattr(settings, 'CAPTCHA_IMAGE_BEFORE_FIELD', True)
CAPTCHA_DICTIONARY_MIN_LENGTH = getattr(settings, 'CAPTCHA_DICTIONARY_MIN_LENGTH', 0)
CAPTCHA_DICTIONARY_MAX_LENGTH = getattr(settings, 'CAPTCHA_DICTIONARY_MAX_LENGTH', 99)
if CAPTCHA_IMAGE_BEFORE_FIELD:
    CAPTCHA_OUTPUT_FORMAT = getattr(settings, 'CAPTCHA_OUTPUT_FORMAT', '%(image)s %(hidden_field)s %(text_field)s')
else:
    CAPTCHA_OUTPUT_FORMAT = getattr(settings, 'CAPTCHA_OUTPUT_FORMAT', '%(hidden_field)s %(text_field)s %(image)s')

CAPTCHA_TEST_MODE = getattr(settings, 'CAPTCHA_TEST_MODE', getattr(settings, 'CATPCHA_TEST_MODE', False))

# Failsafe
if CAPTCHA_DICTIONARY_MIN_LENGTH > CAPTCHA_DICTIONARY_MAX_LENGTH:
    CAPTCHA_DICTIONARY_MIN_LENGTH, CAPTCHA_DICTIONARY_MAX_LENGTH = CAPTCHA_DICTIONARY_MAX_LENGTH, CAPTCHA_DICTIONARY_MIN_LENGTH


def _callable_from_string(string_or_callable):
    if callable(string_or_callable):
        return string_or_callable
    else:
        return getattr(__import__('.'.join(string_or_callable.split('.')[:-1]), {}, {}, ['']), string_or_callable.split('.')[-1])


def get_challenge():
    return _callable_from_string(CAPTCHA_CHALLENGE_FUNCT)


def noise_functions():
    if CAPTCHA_NOISE_FUNCTIONS:
        return map(_callable_from_string, CAPTCHA_NOISE_FUNCTIONS)
    return []


def filter_functions():
    if CAPTCHA_FILTER_FUNCTIONS:
        return map(_callable_from_string, CAPTCHA_FILTER_FUNCTIONS)
    return []

########NEW FILE########
__FILENAME__ = fields
﻿from captcha.conf import settings
from django.conf import settings as django_settings
from captcha.models import CaptchaStore, get_safe_now
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse,  NoReverseMatch
from django.forms import ValidationError
from django.forms.fields import CharField, MultiValueField
from django.forms.widgets import TextInput, MultiWidget, HiddenInput
from django.utils.translation import ugettext, ugettext_lazy
from six import u

class BaseCaptchaTextInput(MultiWidget):
    """
    Base class for Captcha widgets
    """
    def __init__(self, attrs=None):
        widgets = (
            HiddenInput(attrs),
            TextInput(attrs),
        )
        super(BaseCaptchaTextInput, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return value.split(',')
        return [None, None]

    def fetch_captcha_store(self, name, value, attrs=None):
        """
        Fetches a new CaptchaStore
        This has to be called inside render
        """
        try:
            reverse('captcha-image', args=('dummy',))
        except NoReverseMatch:
            raise ImproperlyConfigured('Make sure you\'ve included captcha.urls as explained in the INSTALLATION section on http://readthedocs.org/docs/django-simple-captcha/en/latest/usage.html#installation')

        key = CaptchaStore.generate_key()

        # these can be used by format_output and render
        self._value = [key, u('')]
        self._key = key
        self.id_ = self.build_attrs(attrs).get('id', None)

    def render(self, name, value, attrs=None):
        #self.fetch_captcha_store(name, value, attrs)
        attrs.update(dict(autocomplete='off'))
        return super(BaseCaptchaTextInput, self).render(name, self._value, attrs=attrs)

    def id_for_label(self, id_):
        if id_:
            return id_ + '_1'
        return id_

    def image_url(self):
        return reverse('captcha-image', kwargs={'key': self._key})

    def audio_url(self):
        return reverse('captcha-audio', kwargs={'key': self._key}) if settings.CAPTCHA_FLITE_PATH else None

    def refresh_url(self):
        return reverse('captcha-refresh')


class CaptchaTextInput(BaseCaptchaTextInput):
    def __init__(self, attrs=None, **kwargs):
        self._args = kwargs
        self._args['output_format'] = self._args.get('output_format') or settings.CAPTCHA_OUTPUT_FORMAT

        for key in ('image', 'hidden_field', 'text_field'):
            if '%%(%s)s' % key not in self._args['output_format']:
                raise ImproperlyConfigured('All of %s must be present in your CAPTCHA_OUTPUT_FORMAT setting. Could not find %s' % (
                    ', '.join(['%%(%s)s' % k for k in ('image', 'hidden_field', 'text_field')]),
                    '%%(%s)s' % key
                ))
        super(CaptchaTextInput, self).__init__(attrs)

    def format_output(self, rendered_widgets):
        hidden_field, text_field = rendered_widgets
        return self._args['output_format'] % {
            'image': self.image_and_audio,
            'hidden_field': hidden_field,
            'text_field': text_field
        }

    def render(self, name, value, attrs=None):
        self.fetch_captcha_store(name, value, attrs)

        self.image_and_audio = '<img src="%s" alt="captcha" class="captcha" />' % self.image_url()
        if settings.CAPTCHA_FLITE_PATH:
            self.image_and_audio = '<a href="%s" title="%s">%s</a>' % (self.audio_url(), ugettext('Play CAPTCHA as audio file'), self.image_and_audio)


        return super(CaptchaTextInput, self).render(name, self._value, attrs=attrs)


class CaptchaField(MultiValueField):
    def __init__(self, *args, **kwargs):
        fields = (
            CharField(show_hidden_initial=True),
            CharField(),
        )
        if 'error_messages' not in kwargs or 'invalid' not in kwargs.get('error_messages'):
            if 'error_messages' not in kwargs:
                kwargs['error_messages'] = {}
            kwargs['error_messages'].update({'invalid': ugettext_lazy('Invalid CAPTCHA')})

        kwargs['widget'] = kwargs.pop('widget', CaptchaTextInput(output_format=kwargs.pop('output_format', None)))

        super(CaptchaField, self).__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        if data_list:
            return ','.join(data_list)
        return None

    def clean(self, value):
        super(CaptchaField, self).clean(value)
        response, value[1] = (value[1] or '').strip().lower(), ''
        CaptchaStore.remove_expired()
        if settings.CAPTCHA_TEST_MODE and response.lower() == 'passed':
            # automatically pass the test
            try:
                # try to delete the captcha based on its hash
                CaptchaStore.objects.get(hashkey=value[0]).delete()
            except CaptchaStore.DoesNotExist:
                # ignore errors
                pass
        elif not self.required and not response:
            pass
        else:
            try:
                CaptchaStore.objects.get(response=response, hashkey=value[0], expiration__gt=get_safe_now()).delete()
            except CaptchaStore.DoesNotExist:
                raise ValidationError(getattr(self, 'error_messages', {}).get('invalid', ugettext_lazy('Invalid CAPTCHA')))
        return value

########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-
import random
from captcha.conf import settings
from django.core.urlresolvers import reverse
from six import u

def math_challenge():
    operators = ('+', '*', '-',)
    operands = (random.randint(1, 10), random.randint(1, 10))
    operator = random.choice(operators)
    if operands[0] < operands[1] and '-' == operator:
        operands = (operands[1], operands[0])
    challenge = '%d%s%d' % (operands[0], operator, operands[1])
    return '%s=' % (challenge), eval(challenge)


def random_char_challenge():
    chars, ret = u('abcdefghijklmnopqrstuvwxyz'), u('')
    for i in range(settings.CAPTCHA_LENGTH):
        ret += random.choice(chars)
    return ret.upper(), ret


def unicode_challenge():
    chars, ret = u('äàáëéèïíîöóòüúù'), u('')
    for i in range(settings.CAPTCHA_LENGTH):
        ret += random.choice(chars)
    return ret.upper(), ret


def word_challenge():
    fd = open(settings.CAPTCHA_WORDS_DICTIONARY, 'rb')
    l = fd.readlines()
    fd.close()
    while True:
        word = random.choice(l).strip()
        if len(word) >= settings.CAPTCHA_DICTIONARY_MIN_LENGTH and len(word) <= settings.CAPTCHA_DICTIONARY_MAX_LENGTH:
            break
    return word.upper(), word.lower()


def huge_words_and_punctuation_challenge():
    "Yay, undocumneted. Mostly used to test Issue 39 - http://code.google.com/p/django-simple-captcha/issues/detail?id=39"
    fd = open(settings.CAPTCHA_WORDS_DICTIONARY, 'rb')
    l = fd.readlines()
    fd.close()
    word = ''
    while True:
        word1 = random.choice(l).strip()
        word2 = random.choice(l).strip()
        punct = random.choice(settings.CAPTCHA_PUNCTUATION)
        word = '%s%s%s' % (word1, punct, word2)
        if len(word) >= settings.CAPTCHA_DICTIONARY_MIN_LENGTH and len(word) <= settings.CAPTCHA_DICTIONARY_MAX_LENGTH:
            break
    return word.upper(), word.lower()


def noise_arcs(draw, image):
    size = image.size
    draw.arc([-20, -20, size[0], 20], 0, 295, fill=settings.CAPTCHA_FOREGROUND_COLOR)
    draw.line([-20, 20, size[0] + 20, size[1] - 20], fill=settings.CAPTCHA_FOREGROUND_COLOR)
    draw.line([-20, 0, size[0] + 20, size[1]], fill=settings.CAPTCHA_FOREGROUND_COLOR)
    return draw


def noise_dots(draw, image):
    size = image.size
    for p in range(int(size[0] * size[1] * 0.1)):
        draw.point((random.randint(0, size[0]), random.randint(0, size[1])), fill=settings.CAPTCHA_FOREGROUND_COLOR)
    return draw


def post_smooth(image):
    try:
        import ImageFilter
    except ImportError:
        from PIL import ImageFilter
    return image.filter(ImageFilter.SMOOTH)


def captcha_image_url(key):
    """ Return url to image. Need for ajax refresh and, etc"""
    return reverse('captcha-image', args=[key])

########NEW FILE########
__FILENAME__ = captcha_clean
from django.core.management.base import BaseCommand
from captcha.models import get_safe_now
import sys


class Command(BaseCommand):
    help = "Clean up expired captcha hashkeys."

    def handle(self, **options):
        from captcha.models import CaptchaStore
        verbose = int(options.get('verbosity'))
        expired_keys = CaptchaStore.objects.filter(expiration__lte=get_safe_now()).count()
        if verbose >= 1:
            print("Currently %d expired hashkeys" % expired_keys)
        try:
            CaptchaStore.remove_expired()
        except:
            if verbose >= 1:
                print("Unable to delete expired hashkeys.")
            sys.exit(1)
        if verbose >= 1:
            if expired_keys > 0:
                print("%d expired hashkeys removed." % expired_keys)
            else:
                print("No keys to remove.")

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'CaptchaStore'
        db.create_table('captcha_captchastore', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('challenge', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('response', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('hashkey', self.gf('django.db.models.fields.CharField')(unique=True, max_length=40)),
            ('expiration', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('captcha', ['CaptchaStore'])


    def backwards(self, orm):
        
        # Deleting model 'CaptchaStore'
        db.delete_table('captcha_captchastore')


    models = {
        'captcha.captchastore': {
            'Meta': {'object_name': 'CaptchaStore'},
            'challenge': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'expiration': ('django.db.models.fields.DateTimeField', [], {}),
            'hashkey': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'response': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        }
    }

    complete_apps = ['captcha']

########NEW FILE########
__FILENAME__ = models
from captcha.conf import settings as captcha_settings
from django.db import models
from django.conf import settings
import datetime
import random
import time
import unicodedata
import six

# Heavily based on session key generation in Django
# Use the system (hardware-based) random number generator if it exists.
if hasattr(random, 'SystemRandom'):
    randrange = random.SystemRandom().randrange
else:
    randrange = random.randrange
MAX_RANDOM_KEY = 18446744073709551616     # 2 << 63


try:
    import hashlib  # sha for Python 2.5+
except ImportError:
    import sha  # sha for Python 2.4 (deprecated in Python 2.6)
    hashlib = False


def get_safe_now():
    try:
        from django.utils.timezone import utc
        if settings.USE_TZ:
            return datetime.datetime.utcnow().replace(tzinfo=utc)
    except:
        pass
    return datetime.datetime.now()


class CaptchaStore(models.Model):
    challenge = models.CharField(blank=False, max_length=32)
    response = models.CharField(blank=False, max_length=32)
    hashkey = models.CharField(blank=False, max_length=40, unique=True)
    expiration = models.DateTimeField(blank=False)

    def save(self, *args, **kwargs):
        #import ipdb; ipdb.set_trace()
        self.response = six.text_type(self.response).lower()
        if not self.expiration:
            #self.expiration = datetime.datetime.now() + datetime.timedelta(minutes=int(captcha_settings.CAPTCHA_TIMEOUT))
            self.expiration = get_safe_now() + datetime.timedelta(minutes=int(captcha_settings.CAPTCHA_TIMEOUT))
        if not self.hashkey:
            key_ = unicodedata.normalize('NFKD', str(randrange(0, MAX_RANDOM_KEY)) + str(time.time()) + six.text_type(self.challenge)).encode('ascii', 'ignore') + unicodedata.normalize('NFKD', six.text_type(self.response)).encode('ascii', 'ignore')
            if hashlib:
                self.hashkey = hashlib.sha1(key_).hexdigest()
            else:
                self.hashkey = sha.new(key_).hexdigest()
            del(key_)
        super(CaptchaStore, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.challenge

    def remove_expired(cls):
        cls.objects.filter(expiration__lte=get_safe_now()).delete()
    remove_expired = classmethod(remove_expired)

    @classmethod
    def generate_key(cls):
        challenge, response = captcha_settings.get_challenge()()
        store = cls.objects.create(challenge=challenge, response=response)

        return store.hashkey

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from captcha.conf import settings
from captcha.fields import CaptchaField, CaptchaTextInput
from captcha.models import CaptchaStore, get_safe_now
from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.translation import ugettext_lazy
import datetime
import json
import re
import six
import os
from six import u

class CaptchaCase(TestCase):
    urls = 'captcha.tests.urls'

    def setUp(self):

        self.stores = {}
        self.__current_settings_output_format = settings.CAPTCHA_OUTPUT_FORMAT
        self.__current_settings_dictionary = settings.CAPTCHA_WORDS_DICTIONARY
        self.__current_settings_punctuation = settings.CAPTCHA_PUNCTUATION

        tested_helpers = ['captcha.helpers.math_challenge', 'captcha.helpers.random_char_challenge', 'captcha.helpers.unicode_challenge']
        if os.path.exists('/usr/share/dict/words'):
            settings.CAPTCHA_WORDS_DICTIONARY = '/usr/share/dict/words'
            settings.CAPTCHA_PUNCTUATION = ';-,.'
            tested_helpers.append('captcha.helpers.word_challenge')
            tested_helpers.append('captcha.helpers.huge_words_and_punctuation_challenge')
        for helper in tested_helpers:
            challenge, response = settings._callable_from_string(helper)()
            self.stores[helper.rsplit('.', 1)[-1].replace('_challenge', '_store')], _ = CaptchaStore.objects.get_or_create(challenge=challenge, response=response)
        challenge, response = settings.get_challenge()()
        self.stores['default_store'], _ = CaptchaStore.objects.get_or_create(challenge=challenge, response=response)
        self.default_store = self.stores['default_store']

    def tearDown(self):
        settings.CAPTCHA_OUTPUT_FORMAT = self.__current_settings_output_format
        settings.CAPTCHA_WORDS_DICTIONARY = self.__current_settings_dictionary
        settings.CAPTCHA_PUNCTUATION = self.__current_settings_punctuation


    def __extract_hash_and_response(self, r):
        hash_ = re.findall(r'value="([0-9a-f]+)"', str(r.content))[0]
        response = CaptchaStore.objects.get(hashkey=hash_).response
        return hash_, response

    def testImages(self):
        for key in [store.hashkey for store in six.itervalues(self.stores)]:
            response = self.client.get(reverse('captcha-image', kwargs=dict(key=key)))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.has_header('content-type'))
            self.assertEqual(response._headers.get('content-type'), ('Content-Type', 'image/png'))

    def testAudio(self):
        if not settings.CAPTCHA_FLITE_PATH:
            return
        for key in (self.stores.get('math_store').hashkey, self.stores.get('math_store').hashkey, self.default_store.hashkey):
            response = self.client.get(reverse('captcha-audio', kwargs=dict(key=key)))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(len(response.content) > 1024)
            self.assertTrue(response.has_header('content-type'))
            self.assertEqual(response._headers.get('content-type'), ('Content-Type', 'audio/x-wav'))

    def testFormSubmit(self):
        r = self.client.get(reverse('captcha-test'))
        self.assertEqual(r.status_code, 200)
        hash_, response = self.__extract_hash_and_response(r)

        r = self.client.post(reverse('captcha-test'), dict(captcha_0=hash_, captcha_1=response, subject='xxx', sender='asasd@asdasd.com'))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(str(r.content).find('Form validated') > 0)

        r = self.client.post(reverse('captcha-test'), dict(captcha_0=hash_, captcha_1=response, subject='xxx', sender='asasd@asdasd.com'))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(str(r.content).find('Form validated') > 0)

    def testFormModelForm(self):
        r = self.client.get(reverse('captcha-test-model-form'))
        self.assertEqual(r.status_code, 200)
        hash_, response = self.__extract_hash_and_response(r)

        r = self.client.post(reverse('captcha-test-model-form'), dict(captcha_0=hash_, captcha_1=response, subject='xxx', sender='asasd@asdasd.com'))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(str(r.content).find('Form validated') > 0)

        r = self.client.post(reverse('captcha-test-model-form'), dict(captcha_0=hash_, captcha_1=response, subject='xxx', sender='asasd@asdasd.com'))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(str(r.content).find('Form validated') > 0)

    def testWrongSubmit(self):
        for urlname in ('captcha-test', 'captcha-test-model-form'):
            r = self.client.get(reverse(urlname))
            self.assertEqual(r.status_code, 200)
            r = self.client.post(reverse(urlname), dict(captcha_0='abc', captcha_1='wrong response', subject='xxx', sender='asasd@asdasd.com'))
            self.assertFormError(r, 'form', 'captcha', ugettext_lazy('Invalid CAPTCHA'))

    def testDeleteExpired(self):
        self.default_store.expiration = get_safe_now() - datetime.timedelta(minutes=5)
        self.default_store.save()
        hash_ = self.default_store.hashkey
        r = self.client.post(reverse('captcha-test'), dict(captcha_0=hash_, captcha_1=self.default_store.response, subject='xxx', sender='asasd@asdasd.com'))

        self.assertEqual(r.status_code, 200)
        self.assertFalse('Form validated' in str(r.content))

        # expired -> deleted
        try:
            CaptchaStore.objects.get(hashkey=hash_)
            self.fail()
        except:
            pass

    def testCustomErrorMessage(self):
        r = self.client.get(reverse('captcha-test-custom-error-message'))
        self.assertEqual(r.status_code, 200)
        # Wrong answer
        r = self.client.post(reverse('captcha-test-custom-error-message'), dict(captcha_0='abc', captcha_1='wrong response'))
        self.assertFormError(r, 'form', 'captcha', 'TEST CUSTOM ERROR MESSAGE')
        # empty answer
        r = self.client.post(reverse('captcha-test-custom-error-message'), dict(captcha_0='abc', captcha_1=''))
        self.assertFormError(r, 'form', 'captcha', ugettext_lazy('This field is required.'))

    def testRepeatedChallenge(self):
        CaptchaStore.objects.create(challenge='xxx', response='xxx')
        try:
            CaptchaStore.objects.create(challenge='xxx', response='xxx')
        except Exception:
            self.fail()

    def testRepeatedChallengeFormSubmit(self):
        __current_challange_function = settings.CAPTCHA_CHALLENGE_FUNCT
        for urlname in ('captcha-test', 'captcha-test-model-form'):
            settings.CAPTCHA_CHALLENGE_FUNCT = 'captcha.tests.trivial_challenge'

            r1 = self.client.get(reverse(urlname))
            r2 = self.client.get(reverse(urlname))
            self.assertEqual(r1.status_code, 200)
            self.assertEqual(r2.status_code, 200)
            if re.findall(r'value="([0-9a-f]+)"', str(r1.content)):
                hash_1 = re.findall(r'value="([0-9a-f]+)"', str(r1.content))[0]
            else:
                self.fail()

            if re.findall(r'value="([0-9a-f]+)"', str(r2.content)):
                hash_2 = re.findall(r'value="([0-9a-f]+)"', str(r2.content))[0]
            else:
                self.fail()
            try:
                store_1 = CaptchaStore.objects.get(hashkey=hash_1)
                store_2 = CaptchaStore.objects.get(hashkey=hash_2)
            except:
                self.fail()

            self.assertTrue(store_1.pk != store_2.pk)
            self.assertTrue(store_1.response == store_2.response)
            self.assertTrue(hash_1 != hash_2)

            r1 = self.client.post(reverse(urlname), dict(captcha_0=hash_1, captcha_1=store_1.response, subject='xxx', sender='asasd@asdasd.com'))
            self.assertEqual(r1.status_code, 200)
            self.assertTrue(str(r1.content).find('Form validated') > 0)

            try:
                store_2 = CaptchaStore.objects.get(hashkey=hash_2)
            except:
                self.fail()

            r2 = self.client.post(reverse(urlname), dict(captcha_0=hash_2, captcha_1=store_2.response, subject='xxx', sender='asasd@asdasd.com'))
            self.assertEqual(r2.status_code, 200)
            self.assertTrue(str(r2.content).find('Form validated') > 0)
        settings.CAPTCHA_CHALLENGE_FUNCT = __current_challange_function

    def testOutputFormat(self):
        for urlname in ('captcha-test', 'captcha-test-model-form'):
            settings.CAPTCHA_OUTPUT_FORMAT = u('%(image)s<p>Hello, captcha world</p>%(hidden_field)s%(text_field)s')
            r = self.client.get(reverse(urlname))
            self.assertEqual(r.status_code, 200)
            self.assertTrue('<p>Hello, captcha world</p>' in str(r.content))

    def testInvalidOutputFormat(self):
        __current_settings_debug = django_settings.DEBUG
        for urlname in ('captcha-test', 'captcha-test-model-form'):
            # we turn on DEBUG because CAPTCHA_OUTPUT_FORMAT is only checked debug

            django_settings.DEBUG = True
            settings.CAPTCHA_OUTPUT_FORMAT = u('%(image)s')
            try:
                self.client.get(reverse(urlname))
                self.fail()
            except ImproperlyConfigured as e:
                self.assertTrue('CAPTCHA_OUTPUT_FORMAT' in str(e))
        django_settings.DEBUG = __current_settings_debug

    def testPerFormFormat(self):
        settings.CAPTCHA_OUTPUT_FORMAT = u('%(image)s testCustomFormatString %(hidden_field)s %(text_field)s')
        r = self.client.get(reverse('captcha-test'))
        self.assertTrue('testCustomFormatString' in str(r.content))
        r = self.client.get(reverse('test_per_form_format'))
        self.assertTrue('testPerFieldCustomFormatString' in str(r.content))

    def testIssue31ProperLabel(self):
        settings.CAPTCHA_OUTPUT_FORMAT = u('%(image)s %(hidden_field)s %(text_field)s')
        r = self.client.get(reverse('captcha-test'))
        self.assertTrue('<label for="id_captcha_1"' in str(r.content))

    def testRefreshView(self):
        r = self.client.get(reverse('captcha-refresh'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        try:
            new_data = json.loads(six.text_type(r.content, encoding='ascii'))
            self.assertTrue('image_url' in new_data)
        except:
            self.fail()

    def testContentLength(self):
        for key in [store.hashkey for store in six.itervalues(self.stores)]:
            response = self.client.get(reverse('captcha-image', kwargs=dict(key=key)))
            self.assertTrue(response.has_header('content-length'))
            self.assertTrue(response['content-length'].isdigit())
            self.assertTrue(int(response['content-length']))

    def testIssue12ProperInstantiation(self):
        """
        This test covers a default django field and widget behavior
        It not assert anything. If something is wrong it will raise a error!
        """
        settings.CAPTCHA_OUTPUT_FORMAT = u('%(image)s %(hidden_field)s %(text_field)s')
        widget = CaptchaTextInput(attrs={'class': 'required'})
        CaptchaField(widget=widget)

    def testTestMode_Issue15(self):
        __current_test_mode_setting  = settings.CAPTCHA_TEST_MODE
        settings.CAPTCHA_TEST_MODE = False
        r = self.client.get(reverse('captcha-test'))
        self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse('captcha-test'), dict(captcha_0='abc', captcha_1='wrong response', subject='xxx', sender='asasd@asdasd.com'))
        self.assertFormError(r, 'form', 'captcha', ugettext_lazy('Invalid CAPTCHA'))

        settings.CAPTCHA_TEST_MODE = True
        # Test mode, only 'PASSED' is accepted
        r = self.client.get(reverse('captcha-test'))
        self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse('captcha-test'), dict(captcha_0='abc', captcha_1='wrong response', subject='xxx', sender='asasd@asdasd.com'))
        self.assertFormError(r, 'form', 'captcha', ugettext_lazy('Invalid CAPTCHA'))

        r = self.client.get(reverse('captcha-test'))
        self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse('captcha-test'), dict(captcha_0='abc', captcha_1='passed', subject='xxx', sender='asasd@asdasd.com'))
        self.assertTrue(str(r.content).find('Form validated') > 0)
        settings.CAPTCHA_TEST_MODE = __current_test_mode_setting

    def test_get_version(self):
        import captcha
        captcha.get_version(True)

    def test_missing_value(self):
        r = self.client.get(reverse('captcha-test-non-required'))
        self.assertEqual(r.status_code, 200)
        hash_, response = self.__extract_hash_and_response(r)

        # Empty response is okay when required is False
        r = self.client.post(reverse('captcha-test-non-required'), dict(subject='xxx', sender='asasd@asdasd.com'))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(str(r.content).find('Form validated') > 0)

        # But a valid response is okay, too
        r = self.client.get(reverse('captcha-test-non-required'))
        self.assertEqual(r.status_code, 200)
        hash_, response = self.__extract_hash_and_response(r)

        r = self.client.post(reverse('captcha-test-non-required'), dict(captcha_0=hash_, captcha_1=response, subject='xxx', sender='asasd@asdasd.com'))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(str(r.content).find('Form validated') > 0)

    def test_autocomplete_off(self):
        r = self.client.get(reverse('captcha-test'))
        self.assertTrue('autocomplete="off"' in six.text_type(r.content))


def trivial_challenge():
    return 'trivial', 'trivial'

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import url, patterns, include
except ImportError:
    from django.conf.urls.defaults import url, patterns, include

urlpatterns = patterns('',
    url(r'test/$', 'captcha.tests.views.test', name='captcha-test'),
    url(r'test-modelform/$', 'captcha.tests.views.test_model_form', name='captcha-test-model-form'),
    url(r'test2/$', 'captcha.tests.views.test_custom_error_message', name='captcha-test-custom-error-message'),
    url(r'test3/$', 'captcha.tests.views.test_per_form_format', name='test_per_form_format'),
    url(r'test-non-required/$', 'captcha.tests.views.test_non_required', name='captcha-test-non-required'),
    url(r'', include('captcha.urls')),
)

########NEW FILE########
__FILENAME__ = views
from django import forms
from captcha.fields import CaptchaField
from django.template import RequestContext, loader
from django.http import HttpResponse
from django.contrib.auth.models import User
from six import u

TEST_TEMPLATE = r'''
{% load url from future %}
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html>
    <head>
        <meta http-equiv="Content-type" content="text/html; charset=utf-8">
        <title>captcha test</title>
    </head>
    <body>
        {% if passed %}
        <p style="color:green">Form validated</p>
        {% endif %}
        {% if form.errors %}
        {{form.errors}}
        {% endif %}

        <form action="{% url 'captcha-test' %}" method="post">
            {{form.as_p}}
            <p><input type="submit" value="Continue &rarr;"></p>
        </form>
    </body>
</html>
'''

def _test(request, form_class):
    passed = False
    if request.POST:
        form = form_class(request.POST)
        if form.is_valid():
            passed = True
    else:
        form = form_class()

    t = loader.get_template_from_string(TEST_TEMPLATE)
    return HttpResponse(
        t.render(RequestContext(request, dict(passed=passed, form=form))))


def test(request):
    class CaptchaTestForm(forms.Form):
        subject = forms.CharField(max_length=100)
        sender = forms.EmailField()
        captcha = CaptchaField(help_text='asdasd')
    return _test(request, CaptchaTestForm)


def test_model_form(request):
    class CaptchaTestModelForm(forms.ModelForm):
        subject = forms.CharField(max_length=100)
        sender = forms.EmailField()
        captcha = CaptchaField(help_text='asdasd')

        class Meta:
            model = User
            fields = ('subject', 'sender', 'captcha', )

    return _test(request, CaptchaTestModelForm)


def test_custom_error_message(request):
    class CaptchaTestErrorMessageForm(forms.Form):
        captcha = CaptchaField(
            help_text='asdasd',
            error_messages=dict(invalid='TEST CUSTOM ERROR MESSAGE')
        )
    return _test(request, CaptchaTestErrorMessageForm)


def test_per_form_format(request):
    class CaptchaTestFormatForm(forms.Form):
        captcha = CaptchaField(
            help_text='asdasd',
            error_messages=dict(invalid='TEST CUSTOM ERROR MESSAGE'),
            output_format=(
                u('%(image)s testPerFieldCustomFormatString '
                '%(hidden_field)s %(text_field)s')
            )
        )
    return _test(request, CaptchaTestFormatForm)


def test_non_required(request):
    class CaptchaTestForm(forms.Form):
        sender = forms.EmailField()
        subject = forms.CharField(max_length=100)
        captcha = CaptchaField(help_text='asdasd', required=False)
    return _test(request, CaptchaTestForm)

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('captcha.views',
    url(r'image/(?P<key>\w+)/$', 'captcha_image', name='captcha-image', kwargs={'scale': 1}),
    url(r'image/(?P<key>\w+)@2/$', 'captcha_image', name='captcha-image-2x', kwargs={'scale': 2}),
    url(r'audio/(?P<key>\w+)/$', 'captcha_audio', name='captcha-audio'),
    url(r'refresh/$', 'captcha_refresh', name='captcha-refresh'),
)

########NEW FILE########
__FILENAME__ = views
from captcha.conf import settings
from captcha.helpers import captcha_image_url
from captcha.models import CaptchaStore
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
import random
import re
import tempfile
import os
import subprocess

try:
    from cStringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    import Image
    import ImageDraw
    import ImageFont

try:
    import json
except ImportError:
    from django.utils import simplejson as json

NON_DIGITS_RX = re.compile('[^\d]')
# Distance of the drawn text from the top of the captcha image
from_top = 4


def getsize(font, text):
    if hasattr(font, 'getoffset'):
        return [x + y for x, y in zip(font.getsize(text), font.getoffset(text))]
    else:
        return font.getsize(text)


def captcha_image(request, key, scale=1):
    store = get_object_or_404(CaptchaStore, hashkey=key)
    text = store.challenge

    if settings.CAPTCHA_FONT_PATH.lower().strip().endswith('ttf'):
        font = ImageFont.truetype(settings.CAPTCHA_FONT_PATH, settings.CAPTCHA_FONT_SIZE * scale)
    else:
        font = ImageFont.load(settings.CAPTCHA_FONT_PATH)

    size = getsize(font, text)
    size = (size[0] * 2, int(size[1] * 1.4))
    image = Image.new('RGB', size, settings.CAPTCHA_BACKGROUND_COLOR)

    try:
        PIL_VERSION = int(NON_DIGITS_RX.sub('', Image.VERSION))
    except:
        PIL_VERSION = 116
    xpos = 2

    charlist = []
    for char in text:
        if char in settings.CAPTCHA_PUNCTUATION and len(charlist) >= 1:
            charlist[-1] += char
        else:
            charlist.append(char)
    for char in charlist:
        fgimage = Image.new('RGB', size, settings.CAPTCHA_FOREGROUND_COLOR)
        charimage = Image.new('L', getsize(font, ' %s ' % char), '#000000')
        chardraw = ImageDraw.Draw(charimage)
        chardraw.text((0, 0), ' %s ' % char, font=font, fill='#ffffff')
        if settings.CAPTCHA_LETTER_ROTATION:
            if PIL_VERSION >= 116:
                charimage = charimage.rotate(random.randrange(*settings.CAPTCHA_LETTER_ROTATION), expand=0, resample=Image.BICUBIC)
            else:
                charimage = charimage.rotate(random.randrange(*settings.CAPTCHA_LETTER_ROTATION), resample=Image.BICUBIC)
        charimage = charimage.crop(charimage.getbbox())
        maskimage = Image.new('L', size)

        maskimage.paste(charimage, (xpos, from_top, xpos + charimage.size[0], from_top + charimage.size[1]))
        size = maskimage.size
        image = Image.composite(fgimage, image, maskimage)
        xpos = xpos + 2 + charimage.size[0]

    image = image.crop((0, 0, xpos + 1, size[1]))
    draw = ImageDraw.Draw(image)

    for f in settings.noise_functions():
        draw = f(draw, image)
    for f in settings.filter_functions():
        image = f(image)

    out = StringIO()
    image.save(out, "PNG")
    out.seek(0)

    response = HttpResponse(content_type='image/png')
    response.write(out.read())
    response['Content-length'] = out.tell()

    return response


def captcha_audio(request, key):
    if settings.CAPTCHA_FLITE_PATH:
        store = get_object_or_404(CaptchaStore, hashkey=key)
        text = store.challenge
        if 'captcha.helpers.math_challenge' == settings.CAPTCHA_CHALLENGE_FUNCT:
            text = text.replace('*', 'times').replace('-', 'minus')
        else:
            text = ', '.join(list(text))
        path = str(os.path.join(tempfile.gettempdir(), '%s.wav' % key))
        subprocess.call([settings.CAPTCHA_FLITE_PATH, "-t", text, "-o", path])
        if os.path.isfile(path):
            response = HttpResponse()
            f = open(path, 'rb')
            response['Content-Type'] = 'audio/x-wav'
            response.write(f.read())
            f.close()
            os.unlink(path)
            return response
    raise Http404


def captcha_refresh(request):
    """  Return json with new captcha for ajax refresh request """
    if not request.is_ajax():
        raise Http404

    new_key = CaptchaStore.generate_key()
    to_json_response = {
        'key': new_key,
        'image_url': captcha_image_url(new_key),
    }
    return HttpResponse(json.dumps(to_json_response), content_type='application/json')

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Django Simple Captcha documentation build configuration file, created by
# sphinx-quickstart on Sun Jul 10 12:35:54 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
from six import u
#sys.path.insert(0, '..')
#import captcha
#print captcha.get_version()

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u('Django Simple Captcha')
copyright = u('2011-2014 Marco Bonetti')

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.4.2'
# The full version, including alpha/beta/rc tags.
release = '0.4.2'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'DjangoSimpleCaptchadoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'DjangoSimpleCaptcha.tex', u('Django Simple Captcha Documentation'),
   u('Marco Bonetti', 'manual')),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = forms
from django import forms
from captcha.fields  import CaptchaField

class CaptchaForm(forms.Form):
    captcha = CaptchaField()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import sys
import os
try:
    from django.core.management import execute_manager
    OLD_DJANGO = True
except ImportError:
    from django.core.management import execute_from_command_line
    OLD_DJANGO = False

if OLD_DJANGO:
    try:
        import settings  # Assumed to be in the same directory.
    except ImportError:
        sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
        sys.exit(1)

BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASEDIR)

if __name__ == "__main__":
    os.environ["DJANGO_SETTINGS_MODULE"] = "testproject.settings"
    if OLD_DJANGO:
        execute_manager(settings)
    else:
        execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
import django
import os
import sys
from six import u

SITE_ID = 1

PROJECT_PATH = os.path.abspath(os.path.dirname(__file__))

PYTHON_VERSION = '%s.%s' % sys.version_info[:2]
DJANGO_VERSION = django.get_version()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_PATH, 'django-simple-captcha.db')
    }
}

TEST_DATABASE_CHARSET = "utf8"
TEST_DATABASE_COLLATION = "utf8_general_ci"

DATABASE_SUPPORTS_TRANSACTIONS = True

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',

    'captcha',
]

LANGUAGE_CODE = "en"

LANGUAGES = (
    ('en', 'English'),
    ('ja', u('日本語')),
)

SOUTH_TESTS_MIGRATE = False

FIXTURE_DIRS = (
    os.path.join(PROJECT_PATH, 'fixtures'),
)

ROOT_URLCONF = 'testproject.urls'

DEBUG = True
TEMPLATE_DEBUG = True
TEMPLATE_DIRS = ('templates',)

# Django 1.4 TZ support
USE_TZ = True
SECRET_KEY = 'empty'


CAPTCHA_FLITE_PATH = os.environ.get('CAPTCHA_FLITE_PATH', None)

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, include, url
except ImportError:
    from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testproject.views.home', name='home'),
    # url(r'^testproject/', include('testproject.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

urlpatterns += patterns('',
    url(r'^$', 'views.home'),
    url(r'^captcha/', include('captcha.urls')),
)


########NEW FILE########
__FILENAME__ = views
from django import forms
from captcha.fields import CaptchaField
from django.template import RequestContext
from django.http import HttpResponseRedirect
from forms import CaptchaForm
from django.shortcuts import render_to_response


def home(request):
    if request.POST:
        form = CaptchaForm(request.POST)
        if form.is_valid():
            return HttpResponseRedirect(request.path + '?ok')
    else:
        form = CaptchaForm()

    return render_to_response('home.html', dict(
        form=form
    ) , context_instance=RequestContext(request))

########NEW FILE########
