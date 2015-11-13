__FILENAME__ = dt.distance_of_time_in_words
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import time
from pytils import dt

def print_(s):
    # pytils всегда возвращает юникод (строка в Py3.x)
    # обычно это ОК выводить юникод в терминал
    # но если это неинтерактивный вывод
    # (например, использования модуля subprocess)
    # то для Py2.x нужно использовать перекодировку в utf-8
    from pytils.third import six
    if six.PY3:
        out = s
    else:
        out = s.encode('UTF-8')
    print(out)

# поддерживаются оба модуля работы со временем:
# time
current_time = time.time()
in_past = current_time - 100000
in_future = current_time + 100000
# и datetime.datetime
dt_current_time = datetime.datetime.now()
dt_in_past = dt_current_time - datetime.timedelta(0, 100000)
dt_in_future = dt_current_time + datetime.timedelta(0, 100000)

#
# У distance_of_time_in_words три параметра:
# 1) from_time, время от которого считать
# 2) accuracy, точность, по умолчанию -- 1
# 3) to_time, до которого времени считать, по умолчанию - сейчас
#

# если to_time не передано, считается от "сейчас",
# и тогда -1 день -> "вчера", а +1 день -> "завтра"
print_(dt.distance_of_time_in_words(in_past))
#-> вчера
print_(dt.distance_of_time_in_words(dt_in_future))
#-> завтра


# а вот если передано to_time, то нельзя говорить "вчера",
# потому что to_time не обязательно "сейчас",
# поэтому -1 день -> "1 день назад"
print_(dt.distance_of_time_in_words(in_past, to_time=current_time))
#-> 1 день назад

# увеличение точности отражается на результате
print_(dt.distance_of_time_in_words(in_past, accuracy=2))
#-> 1 день 3 часа назад
print_(dt.distance_of_time_in_words(in_past, accuracy=3))
#-> 1 день 3 часа 46 минут назад

# аналогично и с будущим временем:
print_(dt.distance_of_time_in_words(in_future))
#-> завтра
print_(dt.distance_of_time_in_words(in_future, to_time=current_time))
#-> через 1 день
print_(dt.distance_of_time_in_words(in_future, accuracy=2))
#-> через 1 день 3 часа
print_(dt.distance_of_time_in_words(in_future, accuracy=3))
#-> через 1 день 3 часа 46 минут

########NEW FILE########
__FILENAME__ = dt.ru_strftime
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
from pytils import dt

def print_(s):
    # pytils всегда возвращает юникод (строка в Py3.x)
    # обычно это ОК выводить юникод в терминал
    # но если это неинтерактивный вывод
    # (например, использования модуля subprocess)
    # то для Py2.x нужно использовать перекодировку в utf-8
    from pytils.third import six
    if six.PY3:
        out = s
    else:
        out = s.encode('UTF-8')
    print(out)


# действие ru_strftime аналогично оригинальному strftime
# только в %a, %A, %b и %B вместо английских названий будут русские

d = datetime.date(2006, 9, 15)

# оригинал
print_(d.strftime("%d.%m.%Y (%a)"))
# -> 15.09.2006 (Fri)

# теперь на русском
# (единственно, что нужно формат строки передавать в unicode
# в то время, как в оригинальном strftime это обязательно str)
print_(dt.ru_strftime(u"%d.%m.%Y (%a)", d))
# -> 15.09.2006 (пт)

# %A дает полное название дня недели
print_(dt.ru_strftime(u"%d.%m.%Y (%A)", d))
# -> 15.09.2006 (пятница)

# %B -- название месяца
print_(dt.ru_strftime(u"%d %B %Y", d))
# -> 15 сентябрь 2006

# ru_strftime умеет правильно склонять месяц (опция inflected)
print_(dt.ru_strftime(u"%d %B %Y", d, inflected=True))
# -> 15 сентября 2006

# ... и день (опция inflected_day)
print_(dt.ru_strftime(u"%d.%m.%Y, в %A", d, inflected_day=True))
# -> 15.09.2006, в пятницу

# ... и добавлять правильный предлог (опция preposition)
print_(dt.ru_strftime(u"%d.%m.%Y, %A", d, preposition=True))
# -> 15.09.2006, в пятницу

# второй параметр можно не передавать, будет использована текущая дата
print_(dt.ru_strftime(u"%d %B %Y", inflected=True))
# ->> 1 декабря 2013
########NEW FILE########
__FILENAME__ = numeral.choose_plural
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pytils import numeral

def print_(s):
    # pytils всегда возвращает юникод (строка в Py3.x)
    # обычно это ОК выводить юникод в терминал
    # но если это неинтерактивный вывод
    # (например, использования модуля subprocess)
    # то для Py2.x нужно использовать перекодировку в utf-8
    from pytils.third import six
    if six.PY3:
        out = s
    else:
        out = s.encode('UTF-8')
    print(out)


# choose_plural нужен для выбора правильной формы
# существительного

# у choose_plural два параметра:
# 1) amount, количество
# 2) variants, варианты
# варианты - это кортеж из вариантов склонения
# его легко составить по мнемоническому правилу:
# (один, два, пять)
# т.е. для 1, 2 и 5 объектов, например для слова "пример"
# (пример, примера, примеров)
print_(numeral.choose_plural(21, (u"пример", u"примера", u"примеров")))
#-> пример
print_(numeral.choose_plural(12, (u"пример", u"примера", u"примеров")))
#-> примеров
print_(numeral.choose_plural(32, (u"пример", u"примера", u"примеров")))
#-> примера

# также можно задавать варианты в одну строку, разделенные запятой
print_(numeral.choose_plural(32, u"пример,примера, примеров"))
#-> примера

# если в варианте используется запятая, она экранируется слешем
print_(numeral.choose_plural(35, u"гвоздь, гвоздя, гвоздей\, шпунтов"))
#-> гвоздей, шпунтов

# зачастую требуется не просто вариант, а вместе с числительным
# в этом случае следует использовать get_plural
print_(numeral.get_plural(32, u"пример,примера, примеров"))
#-> 32 примера

# часто хочется, чтобы в случае отсутсвия значения (т.е. количество равно нулю)
# выводилось не "0 примеров", а "примеров нет"
# в этом случае используйте третий параметр get_plural:
print_(numeral.get_plural(0, u"пример,примера, примеров", u"без примеров"))
# -> без примеров
########NEW FILE########
__FILENAME__ = numeral.in_words
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pytils import numeral

def print_(s):
    # pytils всегда возвращает юникод (строка в Py3.x)
    # обычно это ОК выводить юникод в терминал
    # но если это неинтерактивный вывод
    # (например, использования модуля subprocess)
    # то для Py2.x нужно использовать перекодировку в utf-8
    from pytils.third import six
    if six.PY3:
        out = s
    else:
        out = s.encode('UTF-8')
    print(out)


# in_words нужен для представления цифр словами

print_(numeral.in_words(12))
#-> двенадцать

# вторым параметром можно задать пол:
# мужской=numeral.MALE, женский=numeral.FEMALE, срелний=numeral.NEUTER (по умолчанию -- мужской)
print_(numeral.in_words(21))
#-> двадцать один

# можно передавать неименованным параметром:
print_(numeral.in_words(21, numeral.FEMALE))
#-> двадцать одна

# можно именованным
print_(numeral.in_words(21, gender=numeral.FEMALE))
#-> двадцать одна
print_(numeral.in_words(21, gender=numeral.NEUTER))
#-> двадцать одно

# можно и дробные
print_(numeral.in_words(12.5))
#-> двенадцать целых пять десятых

# причем "пишутся" только значимые цифры
print_(numeral.in_words(5.30000))
#-> пять целых три десятых

########NEW FILE########
__FILENAME__ = numeral.rubles
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pytils import numeral

def print_(s):
    # pytils всегда возвращает юникод (строка в Py3.x)
    # обычно это ОК выводить юникод в терминал
    # но если это неинтерактивный вывод
    # (например, использования модуля subprocess)
    # то для Py2.x нужно использовать перекодировку в utf-8
    from pytils.third import six
    if six.PY3:
        out = s
    else:
        out = s.encode('UTF-8')
    print(out)


# rubles служит для формирования строк с деньгами

print_(numeral.rubles(10))
#-> десять рублей

# если нужно, то даже 0 копеек можно записать словами
print_(numeral.rubles(10, zero_for_kopeck=True))
#-> десять рублей ноль копеек

print_(numeral.rubles(2.35))
#-> два рубля тридцать пять копеек

# в случае чего, копейки округляются
print_(numeral.rubles(3.95754))
#-> три рубля девяносто шесть копеек

########NEW FILE########
__FILENAME__ = numeral.sum_string
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pytils import numeral

def print_(s):
    # pytils всегда возвращает юникод (строка в Py3.x)
    # обычно это ОК выводить юникод в терминал
    # но если это неинтерактивный вывод
    # (например, использования модуля subprocess)
    # то для Py2.x нужно использовать перекодировку в utf-8
    from pytils.third import six
    if six.PY3:
        out = s
    else:
        out = s.encode('UTF-8')
    print(out)


# sum_string объединяет в себе choose_plural и in_words
# т.е. передаются и количество, и варианты названия объекта
# а на выходе получаем количество объектов в правильной форме

# параметры:
# 1) amount, количество (только целое)
# 2) gender, пол (1=мужской, 2=женский, 3=средний)
# 3) items, варианты названий объекта (необязательно),
#    правила аналогичны таковым у choose_plural

print_(numeral.sum_string(3, numeral.MALE, (u"носок", u"носка", u"носков")))
#-> три носка

print_(numeral.sum_string(5, numeral.FEMALE, (u"коробка", u"коробки", u"коробок")))
#-> пять коробок

print_(numeral.sum_string(21, numeral.NEUTER, (u"очко", u"очка", u"очков")))
#-> двадцать одно очко

# если варианты не указывать, то действие функции аналогично дейтсвию in_words
print_(numeral.sum_string(21, gender=numeral.NEUTER))
#-> двадцать одно



########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import sys
import os
from pytils.third import six

EXAMPLES = [
    'dt.distance_of_time_in_words.py',
    'dt.ru_strftime.py',
    'numeral.choose_plural.py',
    'numeral.in_words.py',
    'numeral.rubles.py',
    'numeral.sum_string.py',
    'translit.py',
]

name_to_path = lambda x: os.path.join(os.path.normpath(os.path.abspath(os.path.dirname(__file__))), x)
sanitize_output = lambda x: x.replace('#->', '').replace('# ->', '').strip()

def safe_file_iterator(fh, encoding='UTF-8'):
    # Py2.x file iterator returns strings, not unicode
    # Py3 file iterator returns not a bytestrings but string
    # therefore we should decode for Py2.x and leave as is for Py3
    for line in fh:
        if six.PY3:
            yield line
        else:
            yield line.decode(encoding)


def grab_expected_output(name):
    with open(name_to_path(name)) as fh:
        return [sanitize_output(x) for x in safe_file_iterator(fh)
            if x.replace(' ', '').startswith('#->')]


def run_example_and_collect_output(name):
    return [
    x.decode('UTF-8') for x in
    subprocess.check_output(
        ['python', name_to_path(name)], stderr=subprocess.STDOUT).strip().splitlines()]



class ExampleFileTestSuite(object):
    def __init__(self, name):
        self.name = name
        self.expected_output = list(grab_expected_output(name))
        self.real_output = list(run_example_and_collect_output(name))
        assert len(self.real_output) == len(self.expected_output), \
            "Mismatch in number of real (%s) and expected (%s) strings" % (len(self.real_output), len(self.expected_output))
        assert len(self.real_output) > 0
        assert isinstance(self.real_output[0], six.text_type), \
            "%r is not text type (not a unicode for Py2.x, not a str for Py3.x" % self.real_output[0]
        assert isinstance(self.expected_output[0], six.text_type), \
            "%r is not text type (not a unicode for Py2.x, not a str for Py3.x" % self.expected_output[0]
 
    def test_cases(self):
        return range(len(self.real_output))

    def run_test(self, name, i):
        assert name == self.name
        assert isinstance(self.real_output[i], six.text_type)
        assert isinstance(self.expected_output[i], six.text_type)
        # ignore real output if in example line marked with ->>
        if self.expected_output[i].startswith('>'):
            return
        assert self.real_output[i] == self.expected_output[i], \
            "Real output %r doesn't match to expected %r for example #%s" % (self.real_output[i], self.expected_output[i], i)


def test_example():
    for example in EXAMPLES:
        runner = ExampleFileTestSuite(example)
        # we want to have granular test, one test case per line
        # nose show each test as "executable, arg1, arg2", that's
        # why we want pass example name again, even test runner already knows it
        for i in runner.test_cases():
            yield runner.run_test, example, i

def assert_python_version(current_version):
    exec_version = subprocess.check_output(
        ['python', '-c', 'import sys; print(sys.version_info)'], stderr=subprocess.STDOUT).strip()
    assert current_version == exec_version.decode('utf-8')


def test_python_version():
    # check that `python something.py` will run the same version interepreter as it is running
    import sys
    current_version = str(sys.version_info)
    # do a yield to show in the test output the python version
    yield assert_python_version, current_version


if __name__ == '__main__':
    import nose, sys
    if not nose.runmodule():
        sys.exit(1)
########NEW FILE########
__FILENAME__ = translit
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pytils import translit

def print_(s):
    # pytils всегда возвращает юникод (строка в Py3.x)
    # обычно это ОК выводить юникод в терминал
    # но если это неинтерактивный вывод
    # (например, использования модуля subprocess)
    # то для Py2.x нужно использовать перекодировку в utf-8
    from pytils.third import six
    if six.PY3:
        out = s
    else:
        out = s.encode('UTF-8')
    print(out)

# простая траслитерация/детранслитерация
# обратите внимание на то, что при транслитерации вход - unicode,
# выход - str, а в детранслитерации -- наоборот
#

print_(translit.translify(u"Это тест и ничего более"))
#-> Eto test i nichego bolee

print_(translit.translify(u"Традиционно сложные для транслитерации буквы - подъезд, щука"))
#-> Traditsionno slozhnyie dlya transliteratsii bukvyi - pod`ezd, schuka

# и теперь пытаемся вернуть назад... (понятно, что Э и Е получаются одинаково)
print_(translit.detranslify("Eto test i nichego bolee"))
#-> Ето тест и ничего более

print_(translit.detranslify("Traditsionno slozhnyie dlya transliteratsii bukvyi - pod`ezd, schuka"))
#-> Традиционно сложные для транслитерации буквы – подЪезд, щука


# и пригодные для url и названий каталогов/файлов транслиты
# dirify и slugify -- синонимы, действия абсолютно идентичны
print_(translit.slugify(u"Традиционно сложные для транслитерации буквы - подъезд, щука"))
#-> traditsionno-slozhnyie-dlya-transliteratsii-bukvyi-podezd-schuka

# обратного преобразования, понятно, нет :)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
########NEW FILE########
__FILENAME__ = settings
# Django settings for pytilsex project.

# find current path
import os
CURRPATH = os.path.dirname(os.path.normpath(os.path.abspath(__file__)))

DEBUG = True
TEMPLATE_DEBUG = DEBUG
DEFAULT_CHARSET='utf-8'

ADMINS = (
     ('Pythy', 'the.pythy@gmail.com'),
)

DATABASES = {
    'default': {
        'NAME': 'pytils_example',
        'ENGINE': 'django.db.backends.sqlite3'
    }
}

MANAGERS = ADMINS

# Local time zone for this installation. All choices can be found here:
# http://www.postgresql.org/docs/current/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'ru-ru'

SITE_ID = 1

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(CURRPATH, 'static')

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

STATICFILES_DIRS = (
	MEDIA_ROOT,
)

STATIC_URL = '/static/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '-)^ay7gz76#9!j=ssycphb7*(gg74zhx9h-(j_1k7!wfr7j(o^'


MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates".
    # Always use forward slashes, even on Windows.
    os.path.join(CURRPATH, 'templates'),
)


TEMPLATE_CONTEXT_PROCESSORS = []

INSTALLED_APPS = (
    'django_nose',
# -- install pytils
    'pytils',
)

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

# is value will shown at error in pytils (default - False)
# PYTILS_SHOW_VALUES_ON_ERROR = True

########NEW FILE########
__FILENAME__ = tests
# -*- encoding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from pytils import VERSION as pytils_version

class ExamplesTestCase(TestCase):

    def setUp(self):
        self.c = Client()

    def testIndex(self):
        resp = self.c.get(reverse('pytils_example'))
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode('utf-8')
        self.assertTrue('pytils %s' % pytils_version in body)
        self.assertTrue(reverse('pytils_dt_example') in body)
        self.assertTrue(reverse('pytils_numeral_example') in body)
        self.assertTrue(reverse('pytils_translit_example') in body)

    def testDt(self):
        resp = self.c.get(reverse('pytils_dt_example'))
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode('utf-8')
        self.assertTrue('distance_of_time' in body)
        self.assertTrue('ru_strftime' in body)
        self.assertTrue('ru_strftime_inflected' in body)
        self.assertTrue('ru_strftime_preposition' in body)
        self.assertTrue(u'вчера' in body)
        self.assertTrue(u'завтра' in body)

    def testNumeral(self):
        resp = self.c.get(reverse('pytils_numeral_example'))
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode('utf-8')
        self.assertTrue('choose_plural' in body)
        self.assertTrue('get_plural' in body)
        self.assertTrue('rubles' in body)
        self.assertTrue('in_words' in body)
        self.assertTrue('sum_string' in body)
        self.assertTrue(u'комментарий' in body)
        self.assertTrue(u'без примеров' in body)
        self.assertTrue(u'двадцать три рубля пятнадцать копеек' in body)
        self.assertTrue(u'двенадцать рублей' in body)
        self.assertTrue(u'двадцать один' in body)
        self.assertTrue(u'тридцать одна целая триста восемьдесят пять тысячных' in body)
        self.assertTrue(u'двадцать один комментарий' in body)

    def testTranslit(self):
        resp = self.c.get(reverse('pytils_translit_example'))
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode('utf-8')
        self.assertTrue('translify' in body)
        self.assertTrue('detranslify' in body)
        self.assertTrue('slugify' in body)
        self.assertTrue('Primer trasliteratsii sredstvami pytils' in body)
        self.assertTrue('primer-trasliteratsii-sredstvami-pytils' in body)
        self.assertTrue('primer-obratnoj-transliteratsii' in body)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-

import time
import datetime
import sys

try:
    from django.conf.urls import patterns, url
except ImportError:
    # Django 1.3
    from django.conf.urls.defaults import patterns, url

from django.views.generic.base import TemplateView
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from pytils import VERSION as pytils_version
from django import VERSION as _django_version

def get_python_version():
    return '.'.join(str(v) for v in sys.version_info[:3])

def get_django_version(_ver):
    ver = '.'.join([str(x) for x in _ver[:-2]])
    return ver

class DtView(TemplateView):
    template_name = 'dt.html'

    def get_context_data(self, **kwargs):
        context = super(DtView, self).get_context_data(**kwargs)
        context.update({
          'ctime': time.time(),
          'otime': time.time() - 100000,
          'ftime': time.time() + 100000,
          'cdate': datetime.datetime.now(),
          'odate': datetime.datetime.now() - datetime.timedelta(0, 100000),
          'fdate': datetime.datetime.now() + datetime.timedelta(0, 100000),
         })
        return context


class NumeralView(TemplateView):
    template_name = 'numeral.html'

    def get_context_data(self, **kwargs):
        context = super(NumeralView, self).get_context_data(**kwargs)
        context.update({
          'comment_variants': ('комментарий', 'комментария', 'комментариев'),
          'comment_number': 21,
          'zero': 0,
          'comment_gender': 'MALE',
          'rubles_value': 23.152,
          'rubles_value2': 12,
          'int_value': 21,
          'float_value': 31.385,
        })
        return context


class TranslitView(TemplateView):
    template_name = 'translit.html'

    def get_context_data(self, **kwargs):
        context = super(TranslitView, self).get_context_data(**kwargs)
        context.update({
          'text': 'Пример траслитерации средствами pytils',
          'translit': 'Primer obratnoj transliteratsii',
        })
        return context

class IndexView(TemplateView):
    template_name = 'base.html'

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context.update({
          'pytils_version': pytils_version,
          'django_version': get_django_version(_django_version),
          'python_version': get_python_version(),
        })
        return context

urlpatterns = patterns('',
    url(r'^dt/', DtView.as_view(), name='pytils_dt_example'),
    url(r'^numeral/', NumeralView.as_view(), name='pytils_numeral_example'),
    url(r'^translit/', TranslitView.as_view(), name='pytils_translit_example'),
    url(r'^$', IndexView.as_view(), name='pytils_example'),
)

urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
__FILENAME__ = dt
# -*- coding: utf-8 -*-
# -*- test-case-name: pytils.test.test_dt -*-
"""
Russian dates without locales
"""

import datetime

from pytils import numeral
from pytils.utils import check_positive
from pytils.third import six

DAY_ALTERNATIVES = {
    1: (u"вчера", u"завтра"),
    2: (u"позавчера", u"послезавтра")
    }  #: Day alternatives (i.e. one day ago -> yesterday)

DAY_VARIANTS = (
    u"день",
    u"дня",
    u"дней",
    )  #: Forms (1, 2, 5) for noun 'day'

HOUR_VARIANTS = (
    u"час",
    u"часа",
    u"часов",
    )  #: Forms (1, 2, 5) for noun 'hour'

MINUTE_VARIANTS = (
    u"минуту",
    u"минуты",
    u"минут",
    )  #: Forms (1, 2, 5) for noun 'minute'

PREFIX_IN = u"через"  #: Prefix 'in' (i.e. B{in} three hours)
SUFFIX_AGO = u"назад"  #: Prefix 'ago' (i.e. three hours B{ago})

MONTH_NAMES = (
    (u"янв", u"январь", u"января"),
    (u"фев", u"февраль", u"февраля"),
    (u"мар", u"март", u"марта"),
    (u"апр", u"апрель", u"апреля"),
    (u"май", u"май", u"мая"),
    (u"июн", u"июнь", u"июня"),
    (u"июл", u"июль", u"июля"),
    (u"авг", u"август", u"августа"),
    (u"сен", u"сентябрь", u"сентября"),
    (u"окт", u"октябрь", u"октября"),
    (u"ноя", u"ноябрь", u"ноября"),
    (u"дек", u"декабрь", u"декабря"),
    )  #: Month names (abbreviated, full, inflected)

DAY_NAMES = (
    (u"пн", u"понедельник", u"понедельник", u"в\xa0"),
    (u"вт", u"вторник", u"вторник", u"во\xa0"),
    (u"ср", u"среда", u"среду", u"в\xa0"),
    (u"чт", u"четверг", u"четверг", u"в\xa0"),
    (u"пт", u"пятница", u"пятницу", u"в\xa0"),
    (u"сб", u"суббота", u"субботу", u"в\xa0"),
    (u"вск", u"воскресенье", u"воскресенье", u"в\xa0")
    )  #: Day names (abbreviated, full, inflected, preposition)


def distance_of_time_in_words(from_time, accuracy=1, to_time=None):
    """
    Represents distance of time in words

    @param from_time: source time (in seconds from epoch)
    @type from_time: C{int}, C{float} or C{datetime.datetime}

    @param accuracy: level of accuracy (1..3), default=1
    @type accuracy: C{int}

    @param to_time: target time (in seconds from epoch),
        default=None translates to current time
    @type to_time: C{int}, C{float} or C{datetime.datetime}

    @return: distance of time in words
    @rtype: unicode

    @raise ValueError: accuracy is lesser or equal zero
    """
    current = False

    if to_time is None:
        current = True
        to_time = datetime.datetime.now()

    check_positive(accuracy, strict=True)

    if not isinstance(from_time, datetime.datetime):
        from_time = datetime.datetime.fromtimestamp(from_time)

    if not isinstance(to_time, datetime.datetime):
        to_time = datetime.datetime.fromtimestamp(to_time)

    dt_delta = to_time - from_time
    difference = dt_delta.days*86400 + dt_delta.seconds

    minutes_orig = int(abs(difference)/60.0)
    hours_orig = int(abs(difference)/3600.0)
    days_orig = int(abs(difference)/86400.0)
    in_future = from_time > to_time

    words = []
    values = []
    alternatives = []

    days = days_orig
    hours = hours_orig - days_orig*24

    words.append(u"%d %s" % (days, numeral.choose_plural(days, DAY_VARIANTS)))
    values.append(days)

    words.append(u"%d %s" % \
                  (hours, numeral.choose_plural(hours, HOUR_VARIANTS)))
    values.append(hours)

    days == 0 and hours == 1 and current and alternatives.append(u"час")

    minutes = minutes_orig - hours_orig*60

    words.append(u"%d %s" % (minutes,
                              numeral.choose_plural(minutes, MINUTE_VARIANTS)))
    values.append(minutes)

    days == 0 and hours == 0 and minutes == 1 and current and \
        alternatives.append(u"минуту")


    # убираем из values и words конечные нули
    while values and not values[-1]:
        values.pop()
        words.pop()
    # убираем из values и words начальные нули
    while values and not values[0]:
        values.pop(0)
        words.pop(0)
    limit = min(accuracy, len(words))
    real_words = words[:limit]
    real_values = values[:limit]
    # снова убираем конечные нули
    while real_values and not real_values[-1]:
        real_values.pop()
        real_words.pop()
        limit -= 1

    real_str = u" ".join(real_words)

    # альтернативные варианты нужны только если в real_words одно значение
    # и, вдобавок, если используется текущее время
    alter_str = limit == 1 and current and alternatives and \
                           alternatives[0]
    _result_str = alter_str or real_str
    result_str = in_future and u"%s %s" % (PREFIX_IN, _result_str) \
                           or u"%s %s" % (_result_str, SUFFIX_AGO)

    # если же прошло менее минуты, то real_words -- пустой, и поэтому
    # нужно брать alternatives[0], а не result_str
    zero_str = minutes == 0 and not real_words and \
            (in_future and u"менее чем через минуту" \
                        or u"менее минуты назад")

    # нужно использовать вчера/позавчера/завтра/послезавтра
    # если days 1..2 и в real_words одно значение
    day_alternatives = DAY_ALTERNATIVES.get(days, False)
    alternate_day = day_alternatives and current and limit == 1 and \
                    ((in_future and day_alternatives[1]) \
                                 or day_alternatives[0])

    final_str = not real_words and zero_str or alternate_day or result_str

    return final_str


def ru_strftime(format=u"%d.%m.%Y", date=None, inflected=False, inflected_day=False, preposition=False):
    """
    Russian strftime without locale

    @param format: strftime format, default=u'%d.%m.%Y'
    @type format: C{unicode}

    @param date: date value, default=None translates to today
    @type date: C{datetime.date} or C{datetime.datetime}
    
    @param inflected: is month inflected, default False
    @type inflected: C{bool}
    
    @param inflected_day: is day inflected, default False
    @type inflected: C{bool}
    
    @param preposition: is preposition used, default False
        preposition=True automatically implies inflected_day=True
    @type preposition: C{bool}

    @return: strftime string
    @rtype: unicode
    """
    if date is None:
        date = datetime.datetime.today()

    weekday = date.weekday()
    
    prepos = preposition and DAY_NAMES[weekday][3] or u""
    
    month_idx = inflected and 2 or 1
    day_idx = (inflected_day or preposition) and 2 or 1
    
    # for russian typography standard,
    # 1 April 2007, but 01.04.2007
    if u'%b' in format or u'%B' in format:
        format = format.replace(u'%d', six.text_type(date.day))

    format = format.replace(u'%a', prepos+DAY_NAMES[weekday][0])
    format = format.replace(u'%A', prepos+DAY_NAMES[weekday][day_idx])
    format = format.replace(u'%b', MONTH_NAMES[date.month-1][0])
    format = format.replace(u'%B', MONTH_NAMES[date.month-1][month_idx])

    # Python 2: strftime's argument must be str
    # Python 3: strftime's argument str, not a bitestring
    if six.PY2:
        # strftime must be str, so encode it to utf8:
        s_format = format.encode("utf-8")
        s_res = date.strftime(s_format)
        # and back to unicode
        u_res = s_res.decode("utf-8")
    else:
        u_res = date.strftime(format)
    return u_res

########NEW FILE########
__FILENAME__ = numeral
# -*- coding: utf-8 -*-
# -*- test-case-name: pytils.test.test_numeral -*-
"""
Plural forms and in-word representation for numerals.
"""
from __future__ import division
from decimal import Decimal
from pytils.utils import check_positive, check_length, split_values
from pytils.third import six

FRACTIONS = (
    (u"десятая", u"десятых", u"десятых"),
    (u"сотая", u"сотых", u"сотых"),
    (u"тысячная", u"тысячных", u"тысячных"),
    (u"десятитысячная", u"десятитысячных", u"десятитысячных"),
    (u"стотысячная", u"стотысячных", u"стотысячных"),
    (u"миллионная", u"милллионных", u"милллионных"),
    (u"десятимиллионная", u"десятимилллионных", u"десятимиллионных"),
    (u"стомиллионная", u"стомилллионных", u"стомиллионных"),
    (u"миллиардная", u"миллиардных", u"миллиардных"),
    )  #: Forms (1, 2, 5) for fractions

ONES = {
    0: (u"",       u"",       u""),
    1: (u"один",   u"одна",   u"одно"),
    2: (u"два",    u"две",    u"два"),
    3: (u"три",    u"три",    u"три"),
    4: (u"четыре", u"четыре", u"четыре"),
    5: (u"пять",   u"пять",   u"пять"),
    6: (u"шесть",  u"шесть",  u"шесть"),
    7: (u"семь",   u"семь",   u"семь"),
    8: (u"восемь", u"восемь", u"восемь"),
    9: (u"девять", u"девять", u"девять"),
    }  #: Forms (MALE, FEMALE, NEUTER) for ones

TENS = {
    0: u"",
    # 1 - особый случай
    10: u"десять",
    11: u"одиннадцать",
    12: u"двенадцать",
    13: u"тринадцать",
    14: u"четырнадцать",
    15: u"пятнадцать",
    16: u"шестнадцать",
    17: u"семнадцать",
    18: u"восемнадцать",
    19: u"девятнадцать",
    2: u"двадцать",
    3: u"тридцать",
    4: u"сорок",
    5: u"пятьдесят",
    6: u"шестьдесят",
    7: u"семьдесят",
    8: u"восемьдесят",
    9: u"девяносто",
    }  #: Tens

HUNDREDS = {
    0: u"",
    1: u"сто",
    2: u"двести",
    3: u"триста",
    4: u"четыреста",
    5: u"пятьсот",
    6: u"шестьсот",
    7: u"семьсот",
    8: u"восемьсот",
    9: u"девятьсот",
    }  #: Hundreds

MALE = 1    #: sex - male
FEMALE = 2  #: sex - female
NEUTER = 3  #: sex - neuter


def _get_float_remainder(fvalue, signs=9):
    """
    Get remainder of float, i.e. 2.05 -> '05'

    @param fvalue: input value
    @type fvalue: C{integer types}, C{float} or C{Decimal}

    @param signs: maximum number of signs
    @type signs: C{integer types}

    @return: remainder
    @rtype: C{str}

    @raise ValueError: fvalue is negative
    @raise ValueError: signs overflow
    """
    check_positive(fvalue)
    if isinstance(fvalue, six.integer_types):
        return "0"
    if isinstance(fvalue, Decimal) and fvalue.as_tuple()[2] == 0:
        # Decimal.as_tuple() -> (sign, digit_tuple, exponent)
        # если экспонента "0" -- значит дробной части нет
        return "0"

    signs = min(signs, len(FRACTIONS))

    # нужно remainder в строке, потому что дробные X.0Y
    # будут "ломаться" до X.Y
    remainder = str(fvalue).split('.')[1]
    iremainder = int(remainder)
    orig_remainder = remainder
    factor = len(str(remainder)) - signs

    if factor > 0:
        # после запятой цифр больше чем signs, округляем
        iremainder = int(round(iremainder / (10.0**factor)))
    format = "%%0%dd" % min(len(remainder), signs)

    remainder = format % iremainder

    if len(remainder) > signs:
        # при округлении цифр вида 0.998 ругаться
        raise ValueError("Signs overflow: I can't round only fractional part \
                          of %s to fit %s in %d signs" % \
                         (str(fvalue), orig_remainder, signs))

    return remainder


def choose_plural(amount, variants):
    """
    Choose proper case depending on amount

    @param amount: amount of objects
    @type amount: C{integer types}

    @param variants: variants (forms) of object in such form:
        (1 object, 2 objects, 5 objects).
    @type variants: 3-element C{sequence} of C{unicode}
        or C{unicode} (three variants with delimeter ',')

    @return: proper variant
    @rtype: C{unicode}

    @raise ValueError: variants' length lesser than 3
    """
    
    if isinstance(variants, six.text_type):
        variants = split_values(variants)
    check_length(variants, 3)
    amount = abs(amount)
    
    if amount % 10 == 1 and amount % 100 != 11:
        variant = 0
    elif amount % 10 >= 2 and amount % 10 <= 4 and \
         (amount % 100 < 10 or amount % 100 >= 20):
        variant = 1
    else:
        variant = 2
    
    return variants[variant]


def get_plural(amount, variants, absence=None):
    """
    Get proper case with value

    @param amount: amount of objects
    @type amount: C{integer types}

    @param variants: variants (forms) of object in such form:
        (1 object, 2 objects, 5 objects).
    @type variants: 3-element C{sequence} of C{unicode}
        or C{unicode} (three variants with delimeter ',')

    @param absence: if amount is zero will return it
    @type absence: C{unicode}

    @return: amount with proper variant
    @rtype: C{unicode}
    """
    if amount or absence is None:
        return u"%d %s" % (amount, choose_plural(amount, variants))
    else:
        return absence


def _get_plural_legacy(amount, extra_variants):
    """
    Get proper case with value (legacy variant, without absence)

    @param amount: amount of objects
    @type amount: C{integer types}

    @param variants: variants (forms) of object in such form:
        (1 object, 2 objects, 5 objects, 0-object variant).
        0-object variant is similar to C{absence} in C{get_plural}
    @type variants: 3-element C{sequence} of C{unicode}
        or C{unicode} (three variants with delimeter ',')

    @return: amount with proper variant
    @rtype: C{unicode}
    """
    absence = None
    if isinstance(extra_variants, six.text_type):
        extra_variants = split_values(extra_variants)
    if len(extra_variants) == 4:
        variants = extra_variants[:3]
        absence = extra_variants[3]
    else:
        variants = extra_variants
    return get_plural(amount, variants, absence)


def rubles(amount, zero_for_kopeck=False):
    """
    Get string for money

    @param amount: amount of money
    @type amount: C{integer types}, C{float} or C{Decimal}

    @param zero_for_kopeck: If false, then zero kopecks ignored
    @type zero_for_kopeck: C{bool}

    @return: in-words representation of money's amount
    @rtype: C{unicode}

    @raise ValueError: amount is negative
    """
    check_positive(amount)

    pts = []
    amount = round(amount, 2)
    pts.append(sum_string(int(amount), 1, (u"рубль", u"рубля", u"рублей")))
    remainder = _get_float_remainder(amount, 2)
    iremainder = int(remainder)

    if iremainder != 0 or zero_for_kopeck:
        # если 3.1, то это 10 копеек, а не одна
        if iremainder < 10 and len(remainder) == 1:
            iremainder *= 10
        pts.append(sum_string(iremainder, 2,
                              (u"копейка", u"копейки", u"копеек")))

    return u" ".join(pts)


def in_words_int(amount, gender=MALE):
    """
    Integer in words

    @param amount: numeral
    @type amount: C{integer types}

    @param gender: gender (MALE, FEMALE or NEUTER)
    @type gender: C{int}

    @return: in-words reprsentation of numeral
    @rtype: C{unicode}

    @raise ValueError: amount is negative
    """
    check_positive(amount)

    return sum_string(amount, gender)

def in_words_float(amount, _gender=FEMALE):
    """
    Float in words

    @param amount: float numeral
    @type amount: C{float} or C{Decimal}

    @return: in-words reprsentation of float numeral
    @rtype: C{unicode}

    @raise ValueError: when ammount is negative
    """
    check_positive(amount)

    pts = []
    # преобразуем целую часть
    pts.append(sum_string(int(amount), 2,
                          (u"целая", u"целых", u"целых")))
    # теперь то, что после запятой
    remainder = _get_float_remainder(amount)
    signs = len(str(remainder)) - 1
    pts.append(sum_string(int(remainder), 2, FRACTIONS[signs]))

    return u" ".join(pts)


def in_words(amount, gender=None):
    """
    Numeral in words

    @param amount: numeral
    @type amount: C{integer types}, C{float} or C{Decimal}

    @param gender: gender (MALE, FEMALE or NEUTER)
    @type gender: C{int}

    @return: in-words reprsentation of numeral
    @rtype: C{unicode}

    raise ValueError: when amount is negative
    """
    check_positive(amount)
    if isinstance(amount, Decimal) and amount.as_tuple()[2] == 0:
        # если целое,
        # т.е. Decimal.as_tuple -> (sign, digits tuple, exponent), exponent=0
        # то как целое
        amount = int(amount)
    if gender is None:
        args = (amount,)
    else:
        args = (amount, gender)
    # если целое
    if isinstance(amount, six.integer_types):
        return in_words_int(*args)
    # если дробное
    elif isinstance(amount, (float, Decimal)):
        return in_words_float(*args)
    # ни float, ни int, ни Decimal
    else:
        # до сюда не должно дойти
        raise TypeError(
            "amount should be number type (int, long, float, Decimal), got %s"
            % type(amount))


def sum_string(amount, gender, items=None):
    """
    Get sum in words

    @param amount: amount of objects
    @type amount: C{integer types}

    @param gender: gender of object (MALE, FEMALE or NEUTER)
    @type gender: C{int}

    @param items: variants of object in three forms:
        for one object, for two objects and for five objects
    @type items: 3-element C{sequence} of C{unicode} or
        just C{unicode} (three variants with delimeter ',')

    @return: in-words representation objects' amount
    @rtype: C{unicode}

    @raise ValueError: items isn't 3-element C{sequence} or C{unicode}
    @raise ValueError: amount bigger than 10**11
    @raise ValueError: amount is negative
    """
    if isinstance(items, six.text_type):
        items = split_values(items)
    if items is None:
        items = (u"", u"", u"")

    try:
        one_item, two_items, five_items = items
    except ValueError:
        raise ValueError("Items must be 3-element sequence")

    check_positive(amount)

    if amount == 0:
        return u"ноль %s" % five_items

    into = u''
    tmp_val = amount

    # единицы
    into, tmp_val = _sum_string_fn(into, tmp_val, gender, items)
    # тысячи
    into, tmp_val = _sum_string_fn(into, tmp_val, FEMALE,
                                    (u"тысяча", u"тысячи", u"тысяч"))
    # миллионы
    into, tmp_val = _sum_string_fn(into, tmp_val, MALE,
                                    (u"миллион", u"миллиона", u"миллионов"))
    # миллиарды
    into, tmp_val = _sum_string_fn(into, tmp_val, MALE,
                                    (u"миллиард", u"миллиарда", u"миллиардов"))
    if tmp_val == 0:
        return into
    else:
        raise ValueError("Cannot operand with numbers bigger than 10**11")


def _sum_string_fn(into, tmp_val, gender, items=None):
    """
    Make in-words representation of single order

    @param into: in-words representation of lower orders
    @type into: C{unicode}

    @param tmp_val: temporary value without lower orders
    @type tmp_val: C{integer types}

    @param gender: gender (MALE, FEMALE or NEUTER)
    @type gender: C{int}

    @param items: variants of objects
    @type items: 3-element C{sequence} of C{unicode}

    @return: new into and tmp_val
    @rtype: C{tuple}

    @raise ValueError: tmp_val is negative
    """
    if items is None:
        items = (u"", u"", u"")
    one_item, two_items, five_items = items
    
    check_positive(tmp_val)

    if tmp_val == 0:
        return into, tmp_val

    words = []

    rest = tmp_val % 1000
    tmp_val = tmp_val // 1000
    if rest == 0:
        # последние три знака нулевые
        if into == u"":
            into = u"%s " % five_items
        return into, tmp_val

    # начинаем подсчет с rest
    end_word = five_items

    # сотни
    words.append(HUNDREDS[rest // 100])

    # десятки
    rest = rest % 100
    rest1 = rest // 10
    # особый случай -- tens=1
    tens = rest1 == 1 and TENS[rest] or TENS[rest1]
    words.append(tens)

    # единицы
    if rest1 < 1 or rest1 > 1:
        amount = rest % 10
        end_word = choose_plural(amount, items)
        words.append(ONES[amount][gender-1])
    words.append(end_word)

    # добавляем то, что уже было
    words.append(into)

    # убираем пустые подстроки
    words = filter(lambda x: len(x) > 0, words)

    # склеиваем и отдаем
    return u" ".join(words).strip(), tmp_val

########NEW FILE########
__FILENAME__ = pytils_dt
# -*- coding: utf-8 -*-
# -*- test-case-name: pytils.test.templatetags.test_dt -*-
"""
pytils.dt templatetags for Django web-framework
"""

import time
from django import template, conf
from pytils import dt
from pytils.templatetags import init_defaults

register = template.Library()  #: Django template tag/filter registrator
debug = conf.settings.DEBUG  #: Debug mode (sets in Django project's settings)
show_value = getattr(conf.settings, 'PYTILS_SHOW_VALUES_ON_ERROR', False)  #: Show values on errors (sets in Django project's settings)

default_value, default_uvalue = init_defaults(debug, show_value)

# -- filters --

def distance_of_time(from_time, accuracy=1):
    """
    Display distance of time from current time.

    Parameter is an accuracy level (deafult is 1).
    Value must be numeral (i.e. time.time() result) or
    datetime.datetime (i.e. datetime.datetime.now()
    result).

    Examples::
        {{ some_time|distance_of_time }}
        {{ some_dtime|distance_of_time:2 }}
    """
    try:
        res = dt.distance_of_time_in_words(from_time, accuracy)
    except Exception as err:
        # because filter must die silently
        try:
            default_distance = "%s seconds" % str(int(time.time() - from_time))
        except Exception:
            default_distance = ""
        res = default_value % {'error': err, 'value': default_distance}
    return res

def ru_strftime(date, format="%d.%m.%Y", inflected_day=False, preposition=False):
    """
    Russian strftime, formats date with given format.

    Value is a date (supports datetime.date and datetime.datetime),
    parameter is a format (string). For explainings about format,
    see documentation for original strftime:
    http://docs.python.org/lib/module-time.html

    Examples::
        {{ some_date|ru_strftime:"%d %B %Y, %A" }}
    """
    try:
        res = dt.ru_strftime(format,
                             date,
                             inflected=True,
                             inflected_day=inflected_day,
                             preposition=preposition)
    except Exception as err:
        # because filter must die silently
        try:
            default_date = date.strftime(format)
        except Exception:
            default_date = str(date)
        res = default_value % {'error': err, 'value': default_date}
    return res

def ru_strftime_inflected(date, format="%d.%m.%Y"):
    """
    Russian strftime with inflected day, formats date
    with given format (similar to ru_strftime),
    also inflects day in proper form.

    Examples::
        {{ some_date|ru_strftime_inflected:"in %A (%d %B %Y)"
    """
    return ru_strftime(date, format, inflected_day=True)

def ru_strftime_preposition(date, format="%d.%m.%Y"):
    """
    Russian strftime with inflected day and correct preposition,
    formats date with given format (similar to ru_strftime),
    also inflects day in proper form and inserts correct
    preposition.

    Examples::
        {{ some_date|ru_strftime_prepoisiton:"%A (%d %B %Y)"
    """
    return ru_strftime(date, format, preposition=True)


# -- register filters
register.filter('distance_of_time', distance_of_time)
register.filter('ru_strftime', ru_strftime)
register.filter('ru_strftime_inflected', ru_strftime_inflected)
register.filter('ru_strftime_preposition', ru_strftime_preposition)

########NEW FILE########
__FILENAME__ = pytils_numeral
# -*- coding: utf-8 -*-
# -*- test-case-name: pytils.test.templatetags.test_numeral -*-
"""
pytils.numeral templatetags for Django web-framework
"""

from django import template, conf

from pytils import numeral
from pytils.templatetags import init_defaults
from pytils.third import six

try:
    # Django 1.4+
    from django.utils.encoding import smart_text
except ImportError:
    from django.utils.encoding import smart_unicode
    smart_text = smart_unicode

register = template.Library()  #: Django template tag/filter registrator
encoding = conf.settings.DEFAULT_CHARSET  #: Current charset (sets in Django project's settings)
debug = conf.settings.DEBUG  #: Debug mode (sets in Django project's settings)
show_value = getattr(conf.settings, 'PYTILS_SHOW_VALUES_ON_ERROR', False)  #: Show values on errors (sets in Django project's settings)

default_value, default_uvalue = init_defaults(debug, show_value)

# -- filters

def choose_plural(amount, variants):
    """
    Choose proper form for plural.

    Value is a amount, parameters are forms of noun.
    Forms are variants for 1, 2, 5 nouns. It may be tuple
    of elements, or string where variants separates each other
    by comma.

    Examples::
        {{ some_int|choose_plural:"пример,примера,примеров" }}
    """
    try:
        if isinstance(variants, six.string_types):
            uvariants = smart_text(variants, encoding)
        else:
            uvariants = [smart_text(v, encoding) for v in variants]
        res = numeral.choose_plural(amount, uvariants)
    except Exception as err:
        # because filter must die silently
        try:
            default_variant = variants
        except Exception:
            default_variant = ""
        res = default_value % {'error': err, 'value': default_variant}
    return res

def get_plural(amount, variants):
    """
    Get proper form for plural and it value.

    Value is a amount, parameters are forms of noun.
    Forms are variants for 1, 2, 5 nouns. It may be tuple
    of elements, or string where variants separates each other
    by comma. You can append 'absence variant' after all over variants

    Examples::
        {{ some_int|get_plural:"пример,примера,примеров,нет примеров" }}
    """
    try:
        if isinstance(variants, six.string_types):
            uvariants = smart_text(variants, encoding)
        else:
            uvariants = [smart_text(v, encoding) for v in variants]
        res = numeral._get_plural_legacy(amount, uvariants)
    except Exception as err:
        # because filter must die silently
        try:
            default_variant = variants
        except Exception:
            default_variant = ""
        res = default_value % {'error': err, 'value': default_variant}
    return res

def rubles(amount, zero_for_kopeck=False):
    """Converts float value to in-words representation (for money)"""
    try:
        res = numeral.rubles(amount, zero_for_kopeck)
    except Exception as err:
        # because filter must die silently
        res = default_value % {'error': err, 'value': str(amount)}
    return res

def in_words(amount, gender=None):
    """
    In-words representation of amount.

    Parameter is a gender: MALE, FEMALE or NEUTER

    Examples::
        {{ some_int|in_words }}
        {{ some_other_int|in_words:FEMALE }}
    """
    try:
        res = numeral.in_words(amount, getattr(numeral, str(gender), None))
    except Exception as err:
        # because filter must die silently
        res = default_value % {'error': err, 'value': str(amount)}
    return res

# -- register filters

register.filter('choose_plural', choose_plural)
register.filter('get_plural', get_plural)
register.filter('rubles', rubles)
register.filter('in_words', in_words)

# -- tags

def sum_string(amount, gender, items):
    """
    in_words and choose_plural in a one flask
    Makes in-words representation of value with
    choosing correct form of noun.

    First parameter is an amount of objects. Second is a
    gender (MALE, FEMALE, NEUTER). Third is a variants
    of forms for object name.

    Examples::
        {% sum_string some_int MALE "пример,примера,примеров" %}
        {% sum_string some_other_int FEMALE "задача,задачи,задач" %}
    """
    try:
        if isinstance(items, six.string_types):
            uitems = smart_text(items, encoding, default_uvalue)
        else:
            uitems = [smart_text(i, encoding) for i in items]
        res = numeral.sum_string(amount, getattr(numeral, str(gender), None), uitems)
    except Exception as err:
        # because tag's renderer must die silently
        res = default_value % {'error': err, 'value': str(amount)}
    return res

# -- register tags

register.simple_tag(sum_string)

########NEW FILE########
__FILENAME__ = pytils_translit
# -*- coding: utf-8 -*-
# -*- test-case-name: pytils.test.templatetags.test_translit -*-
"""
pytils.translit templatetags for Django web-framework
"""

from django import template, conf
from pytils import translit
from pytils.templatetags import init_defaults

try:
    # Django 1.4+
    from django.utils.encoding import smart_text
except ImportError:
    from django.utils.encoding import smart_unicode
    smart_text = smart_unicode

register = template.Library()  #: Django template tag/filter registrator
debug = conf.settings.DEBUG  #: Debug mode (sets in Django project's settings)
encoding = conf.settings.DEFAULT_CHARSET  #: Current charset (sets in Django project's settings)
show_value = getattr(conf.settings, 'PYTILS_SHOW_VALUES_ON_ERROR', False)  #: Show values on errors (sets in Django project's settings)

default_value, default_uvalue = init_defaults(debug, show_value)

# -- filters --

def translify(text):
    """Translify russian text"""
    try:
        res = translit.translify(smart_text(text, encoding))
    except Exception as err:
        # because filter must die silently
        res = default_value % {'error': err, 'value': text}
    return res

def detranslify(text):
    """Detranslify russian text"""
    try:
        res = translit.detranslify(text)
    except Exception as err:
        # because filter must die silently
        res = default_value % {'error': err, 'value': text}
    return res

def slugify(text):
    """Make slug from (russian) text"""
    try:
        res = translit.slugify(smart_text(text, encoding))
    except Exception as err:
        # because filter must die silently
        res = default_value % {'error': err, 'value': text}
    return res

# -- register filters
register.filter('translify', translify)
register.filter('detranslify', detranslify)
register.filter('slugify', slugify)

########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-
"""
Helpers for templatetags' unit tests in Django webframework
"""

from django.conf import settings
from django.utils.encoding import smart_str

encoding = 'utf-8'

settings.configure(
    TEMPLATE_DIRS=(),
    TEMPLATE_CONTEXT_PROCESSORS=(),
    TEMPLATE_LOADERS=(),
    INSTALLED_APPS=('pytils',),
    DEFAULT_CHARSET=encoding,
)

from django import template
from django.template import loader

import unittest




class TemplateTagTestCase(unittest.TestCase):
    """
    TestCase for testing template tags and filters
    """
    def check_template_tag(self, template_name, template_string, context, result_string):
        """
        Method validates output of template tag or filter
        
        @param template_name: name of template
        @type template_name: C{str}
        
        @param template_string: contents of template
        @type template_string: C{str} or C{unicode}

        @param context: rendering context
        @type context: C{dict}

        @param result_string: reference output
        @type result_string: C{str} or C{unicode}
        """
        
        def test_template_loader(template_name, template_dirs=None):
            return smart_str(template_string), template_name
        
        loader.template_source_loaders = [test_template_loader,]
        
        output = loader.get_template(template_name).render(template.Context(context))
        self.assertEquals(output, result_string)


########NEW FILE########
__FILENAME__ = test_common
# -*- coding: utf-8 -*-
"""
Unit tests for pytils' templatetags common things
"""

import unittest

from pytils import templatetags as tt

class TemplateTagsCommonsTestCase(unittest.TestCase):
    
    def testInitDefaults(self):
        """
        Unit-tests for pytils.templatetags.init_defaults
        """
        self.assertEquals(tt.init_defaults(debug=False, show_value=False), ('', u''))
        self.assertEquals(tt.init_defaults(debug=False, show_value=True), ('%(value)s', u'%(value)s'))
        self.assertEquals(tt.init_defaults(debug=True, show_value=False), ('unknown: %(error)s', u'unknown: %(error)s'))
        self.assertEquals(tt.init_defaults(debug=True, show_value=True), ('unknown: %(error)s', u'unknown: %(error)s'))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_dt
# -*- coding: utf-8 -*-
"""
Unit tests for pytils' dt templatetags for Django web framework
"""

import datetime
from pytils.test.templatetags import helpers

class DtDefaultTestCase(helpers.TemplateTagTestCase):
    
    def setUp(self):
        self.date = datetime.datetime(2007, 1, 26, 15, 50)
        self.date_before = datetime.datetime.now() - datetime.timedelta(1, 2000)
    
    def testLoad(self):
        self.check_template_tag('load_tag', u'{% load pytils_dt %}', {}, u'')
    
    def testRuStrftimeFilter(self):
        self.check_template_tag('ru_strftime_filter',
            u'{% load pytils_dt %}{{ val|ru_strftime:"%d %B %Y, %A" }}',
            {'val': self.date},
            u'26 января 2007, пятница')
    
    def testRuStrftimeInflectedFilter(self):
        self.check_template_tag('ru_strftime_inflected_filter',
            u'{% load pytils_dt %}{{ val|ru_strftime_inflected:"в %A, %d %B %Y" }}',
            {'val': self.date},
            u'в пятницу, 26 января 2007')
    
    def testRuStrftimePrepositionFilter(self):
        self.check_template_tag('ru_strftime_preposition_filter',
            u'{% load pytils_dt %}{{ val|ru_strftime_preposition:"%A, %d %B %Y" }}',
            {'val': self.date},
            u'в\xa0пятницу, 26 января 2007')
    
    def testDistanceFilter(self):
        self.check_template_tag('distance_filter',
            u'{% load pytils_dt %}{{ val|distance_of_time }}',
            {'val': self.date_before},
            u'вчера')
        
        self.check_template_tag('distance_filter',
            u'{% load pytils_dt %}{{ val|distance_of_time:3 }}',
            {'val': self.date_before},
            u'1 день 0 часов 33 минуты назад')
    
    # без отладки, если ошибка -- по умолчанию пустая строка
    def testRuStrftimeError(self):
        self.check_template_tag('ru_strftime_error',
            u'{% load pytils_dt %}{{ val|ru_strftime:"%d %B %Y" }}',
            {'val': 1},
            u'')

if __name__ == '__main__':
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_numeral
# -*- coding: utf-8 -*-
"""
Unit tests for pytils' numeral templatetags for Django web framework
"""

from pytils.test.templatetags import helpers


class NumeralDefaultTestCase(helpers.TemplateTagTestCase):

    def testLoad(self):
        self.check_template_tag('load_tag', u'{% load pytils_numeral %}', {}, u'')
    
    def testChoosePluralFilter(self):
        self.check_template_tag('choose_plural',
            u'{% load pytils_numeral %}{{ val|choose_plural:"гвоздь,гвоздя,гвоздей" }}',
            {'val': 10},
            u'гвоздей')

    def testGetPluralFilter(self):
        self.check_template_tag('get_plural',
            u'{% load pytils_numeral %}{{ val|get_plural:"гвоздь,гвоздя,гвоздей" }}',
            {'val': 10},
            u'10 гвоздей')
        self.check_template_tag('get_plural',
            u'{% load pytils_numeral %}{{ val|get_plural:"гвоздь,гвоздя,гвоздей" }}',
            {'val': 0},
            u'0 гвоздей')
        self.check_template_tag('get_plural',
            u'{% load pytils_numeral %}{{ val|get_plural:"гвоздь,гвоздя,гвоздей,нет гвоздей" }}',
            {'val': 0},
            u'нет гвоздей')
    
    def testRublesFilter(self):
        self.check_template_tag('rubles',
            u'{% load pytils_numeral %}{{ val|rubles }}',
            {'val': 10.1},
            u'десять рублей десять копеек')
    
    def testInWordsFilter(self):
        self.check_template_tag('in_words',
            u'{% load pytils_numeral %}{{ val|in_words }}',
            {'val': 21},
            u'двадцать один')

        self.check_template_tag('in_words',
            u'{% load pytils_numeral %}{{ val|in_words:"NEUTER" }}',
            {'val': 21},
            u'двадцать одно')
    
    def testSumStringTag(self):
        self.check_template_tag('sum_string',
            u'{% load pytils_numeral %}{% sum_string val "MALE" "пример,пример,примеров" %}',
            {'val': 21},
            u'двадцать один пример')
        
        self.check_template_tag('sum_string_w_gender',
            u'{% load pytils_numeral %}{% sum_string val male variants %}',
            {
             'val': 21,
             'male':'MALE',
             'variants': ('пример','пример','примеров')
             },
            u'двадцать один пример')

    # без отладки, если ошибка -- по умолчанию пустая строка
    def testChoosePluralError(self):
        self.check_template_tag('choose_plural_error',
            u'{% load pytils_numeral %}{{ val|choose_plural:"вариант" }}',
            {'val': 1},
            u'')


if __name__ == '__main__':
    import unittest
    unittest.main()


########NEW FILE########
__FILENAME__ = test_translit
# -*- coding: utf-8 -*-
"""
Unit tests for pytils' translit templatetags for Django web framework
"""

from pytils.test.templatetags import helpers

class TranslitDefaultTestCase(helpers.TemplateTagTestCase):
    
    def testLoad(self):
        self.check_template_tag('load_tag', u'{% load pytils_translit %}', {}, u'')
    
    def testTranslifyFilter(self):
        self.check_template_tag('translify_filter',
            u'{% load pytils_translit %}{{ val|translify }}',
            {'val': 'проверка'},
            u'proverka')
    
    def testDetranslifyFilter(self):
        self.check_template_tag('detranslify_filter',
            u'{% load pytils_translit %}{{ val|detranslify }}',
            {'val': 'proverka'},
            u'проверка')

    def testSlugifyFilter(self):
        self.check_template_tag('slugify_filter',
            u'{% load pytils_translit %}{{ val|slugify }}',
            {'val': 'Проверка связи'},
            u'proverka-svyazi')


if __name__ == '__main__':
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_dt
# -*- coding: utf-8 -*-
"""
Unit-tests for pytils.dt
"""

import datetime
import time
import unittest

import pytils

class DistanceOfTimeInWordsTestCase(unittest.TestCase):
    """
    Test case for pytils.dt.distance_of_time_in_words
    """

    def setUp(self):
        """
        Setting up environment for tests
        """
        self.time = 1156862275.7711999
        self.dtime = {}
        self.updateTime(self.time)

    def updateTime(self, _time):
        """Update all time-related values for current time """
        self.dtime['10sec_ago'] = _time - 10
        self.dtime['1min_ago'] = _time - 60
        self.dtime['10min_ago'] = _time - 600
        self.dtime['59min_ago'] = _time - 3540
        self.dtime['59min59sec_ago'] = _time - 3599
        self.dtime['1hr_ago'] = _time - 3600
        self.dtime['1hr1sec_ago'] = _time - 3601
        self.dtime['1hr59sec_ago'] = _time - 3659
        self.dtime['1hr1min_ago'] = _time - 3660
        self.dtime['1hr2min_ago'] = _time - 3720
        self.dtime['10hr_ago'] = _time - 36600
        self.dtime['1day_ago'] = _time - 87600
        self.dtime['1day1hr_ago'] = _time - 90600
        self.dtime['2day_ago'] = _time - 87600*2
        self.dtime['4day1min_ago'] = _time - 87600*4 - 60

        self.dtime['in_10sec'] = _time + 10
        self.dtime['in_1min'] = _time + 61
        self.dtime['in_10min'] = _time + 601
        self.dtime['in_1hr'] = _time + 3721
        self.dtime['in_10hr'] = _time + 36601
        self.dtime['in_1day'] = _time + 87601
        self.dtime['in_1day1hr'] = _time + 90601
        self.dtime['in_2day'] = _time + 87600*2 + 1

    def ckDefaultAccuracy(self, typ, estimated):
        """
        Checks with default value for accuracy
        """
        t0 = time.time()
        # --- change state !!! attention
        self.updateTime(t0)
        # ---
        t1 = self.dtime[typ]
        res = pytils.dt.distance_of_time_in_words(from_time=t1, to_time=t0)
        # --- revert state to original value
        self.updateTime(self.time)
        # ---
        self.assertEquals(res, estimated)

    def ckDefaultTimeAndAccuracy(self, typ, estimated):
        """
        Checks with default accuracy and default time
        """
        t0 = time.time()
        # --- change state !!! attention
        self.updateTime(t0)
        # ---
        t1 = self.dtime[typ]
        res = pytils.dt.distance_of_time_in_words(t1)
        # --- revert state to original value
        self.updateTime(self.time)
        # ---
        self.assertEquals(res, estimated)

    def ckDefaultToTime(self, typ, accuracy, estimated):
        """
        Checks with default value of time
        """
        t0 = time.time()
        # --- change state !!! attention
        self.updateTime(t0)
        # ---
        t1 = self.dtime[typ]
        res = pytils.dt.distance_of_time_in_words(t1, accuracy)
        # --- revert state to original value
        self.updateTime(self.time)
        # ---
        self.assertEquals(res, estimated)

    def testDOTIWDefaultAccuracy(self):
        """
        Unit-test for distance_of_time_in_words with default accuracy
        """
        self.ckDefaultAccuracy("10sec_ago", u"менее минуты назад")
        self.ckDefaultAccuracy("1min_ago", u"1 минуту назад")
        self.ckDefaultAccuracy("10min_ago", u"10 минут назад")
        self.ckDefaultAccuracy("59min_ago", u"59 минут назад")
        self.ckDefaultAccuracy("59min59sec_ago", u"59 минут назад")
        self.ckDefaultAccuracy("1hr_ago", u"1 час назад")
        self.ckDefaultAccuracy("1hr1sec_ago", u"1 час назад")
        self.ckDefaultAccuracy("1hr59sec_ago", u"1 час назад")
        self.ckDefaultAccuracy("1hr1min_ago", u"1 час назад")
        self.ckDefaultAccuracy("1hr2min_ago", u"1 час назад")
        self.ckDefaultAccuracy("10hr_ago", u"10 часов назад")
        self.ckDefaultAccuracy("1day_ago", u"1 день назад")
        self.ckDefaultAccuracy("1day1hr_ago", u"1 день назад")
        self.ckDefaultAccuracy("2day_ago", u"2 дня назад")

        self.ckDefaultAccuracy("in_10sec", u"менее чем через минуту")
        self.ckDefaultAccuracy("in_1min", u"через 1 минуту")
        self.ckDefaultAccuracy("in_10min", u"через 10 минут")
        self.ckDefaultAccuracy("in_1hr", u"через 1 час")
        self.ckDefaultAccuracy("in_10hr", u"через 10 часов")
        self.ckDefaultAccuracy("in_1day", u"через 1 день")
        self.ckDefaultAccuracy("in_1day1hr", u"через 1 день")
        self.ckDefaultAccuracy("in_2day", u"через 2 дня")

    def testDOTIWDefaultAccuracyDayAndMinute(self):
        """
        Unit-tests for distance_of_time_in_words with default accuracy and to_time
        """
        self.ckDefaultTimeAndAccuracy("4day1min_ago", u"4 дня назад")

        self.ckDefaultTimeAndAccuracy("10sec_ago", u"менее минуты назад")
        self.ckDefaultTimeAndAccuracy("1min_ago", u"минуту назад")
        self.ckDefaultTimeAndAccuracy("10min_ago", u"10 минут назад")
        self.ckDefaultTimeAndAccuracy("59min_ago", u"59 минут назад")
        self.ckDefaultTimeAndAccuracy("59min59sec_ago", u"59 минут назад")
        self.ckDefaultTimeAndAccuracy("1hr_ago", u"час назад")
        self.ckDefaultTimeAndAccuracy("1hr1sec_ago", u"час назад")
        self.ckDefaultTimeAndAccuracy("1hr59sec_ago", u"час назад")
        self.ckDefaultTimeAndAccuracy("1hr1min_ago", u"час назад")
        self.ckDefaultTimeAndAccuracy("1hr2min_ago", u"час назад")
        self.ckDefaultTimeAndAccuracy("10hr_ago", u"10 часов назад")
        self.ckDefaultTimeAndAccuracy("1day_ago", u"вчера")
        self.ckDefaultTimeAndAccuracy("1day1hr_ago", u"вчера")
        self.ckDefaultTimeAndAccuracy("2day_ago", u"позавчера")

        self.ckDefaultTimeAndAccuracy("in_10sec", u"менее чем через минуту")
        self.ckDefaultTimeAndAccuracy("in_1min", u"через минуту")
        self.ckDefaultTimeAndAccuracy("in_10min", u"через 10 минут")
        self.ckDefaultTimeAndAccuracy("in_1hr", u"через час")
        self.ckDefaultTimeAndAccuracy("in_10hr", u"через 10 часов")
        self.ckDefaultTimeAndAccuracy("in_1day", u"завтра")
        self.ckDefaultTimeAndAccuracy("in_1day1hr", u"завтра")
        self.ckDefaultTimeAndAccuracy("in_2day", u"послезавтра")

    def test4Days1MinuteDaytimeBug2(self):
        from_time = datetime.datetime.now() - \
            datetime.timedelta(days=4, minutes=1)
        res = pytils.dt.distance_of_time_in_words(from_time)
        self.assertEquals(
            res,
            u"4 дня назад")


    def testDOTIWDefaultToTimeAcc1(self):
        """
        Unit-tests for distance_of_time_in_words with default to_time and accuracy=1
        """
        # accuracy = 1
        self.ckDefaultToTime("10sec_ago", 1, u"менее минуты назад")
        self.ckDefaultToTime("1min_ago", 1, u"минуту назад")
        self.ckDefaultToTime("10min_ago", 1,  u"10 минут назад")
        self.ckDefaultToTime("59min_ago", 1, u"59 минут назад")
        self.ckDefaultToTime("59min59sec_ago", 1, u"59 минут назад")
        self.ckDefaultToTime("1hr_ago", 1, u"час назад")
        self.ckDefaultToTime("1hr1sec_ago", 1, u"час назад")
        self.ckDefaultToTime("1hr59sec_ago", 1, u"час назад")
        self.ckDefaultToTime("1hr1min_ago", 1, u"час назад")
        self.ckDefaultToTime("1hr2min_ago", 1, u"час назад")
        self.ckDefaultToTime("10hr_ago", 1, u"10 часов назад")
        self.ckDefaultToTime("1day_ago", 1, u"вчера")
        self.ckDefaultToTime("1day1hr_ago", 1, u"вчера")
        self.ckDefaultToTime("2day_ago", 1, u"позавчера")

        self.ckDefaultToTime("in_10sec", 1, u"менее чем через минуту")
        self.ckDefaultToTime("in_1min", 1, u"через минуту")
        self.ckDefaultToTime("in_10min", 1, u"через 10 минут")
        self.ckDefaultToTime("in_1hr", 1, u"через час")
        self.ckDefaultToTime("in_10hr", 1, u"через 10 часов")
        self.ckDefaultToTime("in_1day", 1, u"завтра")
        self.ckDefaultToTime("in_1day1hr", 1, u"завтра")
        self.ckDefaultToTime("in_2day", 1, u"послезавтра")
        
    def testDOTIWDefaultToTimeAcc2(self):
        """
        Unit-tests for distance_of_time_in_words with default to_time and accuracy=2
        """
        # accuracy = 2
        self.ckDefaultToTime("10sec_ago", 2, u"менее минуты назад")
        self.ckDefaultToTime("1min_ago", 2, u"минуту назад")
        self.ckDefaultToTime("10min_ago", 2,  u"10 минут назад")
        self.ckDefaultToTime("59min_ago", 2, u"59 минут назад")
        self.ckDefaultToTime("59min59sec_ago", 2, u"59 минут назад")
        self.ckDefaultToTime("1hr_ago", 2, u"час назад")
        self.ckDefaultToTime("1hr1sec_ago", 2, u"час назад")
        self.ckDefaultToTime("1hr59sec_ago", 2, u"час назад")
        self.ckDefaultToTime("1hr1min_ago", 2, u"1 час 1 минуту назад")
        self.ckDefaultToTime("1hr2min_ago", 2, u"1 час 2 минуты назад")
        self.ckDefaultToTime("10hr_ago", 2, u"10 часов 10 минут назад")
        self.ckDefaultToTime("1day_ago", 2, u"вчера")
        self.ckDefaultToTime("1day1hr_ago", 2, u"1 день 1 час назад")
        self.ckDefaultToTime("2day_ago", 2, u"позавчера")

        self.ckDefaultToTime("in_10sec", 2, u"менее чем через минуту")
        self.ckDefaultToTime("in_1min", 2, u"через минуту")
        self.ckDefaultToTime("in_10min", 2, u"через 10 минут")
        self.ckDefaultToTime("in_1hr", 2, u"через 1 час 2 минуты")
        self.ckDefaultToTime("in_10hr", 2, u"через 10 часов 10 минут")
        self.ckDefaultToTime("in_1day", 2, u"завтра")
        self.ckDefaultToTime("in_1day1hr", 2, u"через 1 день 1 час")
        self.ckDefaultToTime("in_2day", 2, u"послезавтра")
        
    def testDOTIWDefaultToTimeAcc3(self):
        """
        Unit-tests for distance_of_time_in_words with default to_time and accuracy=3
        """
        # accuracy = 3
        self.ckDefaultToTime("10sec_ago", 3, u"менее минуты назад")
        self.ckDefaultToTime("1min_ago", 3, u"минуту назад")
        self.ckDefaultToTime("10min_ago", 3,  u"10 минут назад")
        self.ckDefaultToTime("59min_ago", 3, u"59 минут назад")
        self.ckDefaultToTime("59min59sec_ago", 3, u"59 минут назад")
        self.ckDefaultToTime("1hr_ago", 3, u"час назад")
        self.ckDefaultToTime("1hr1sec_ago", 3, u"час назад")
        self.ckDefaultToTime("1hr59sec_ago", 3, u"час назад")
        self.ckDefaultToTime("1hr1min_ago", 3, u"1 час 1 минуту назад")
        self.ckDefaultToTime("1hr2min_ago", 3, u"1 час 2 минуты назад")
        self.ckDefaultToTime("10hr_ago", 3, u"10 часов 10 минут назад")
        self.ckDefaultToTime("1day_ago", 3,
                                u"1 день 0 часов 20 минут назад")
        self.ckDefaultToTime("1day1hr_ago", 3,
                                u"1 день 1 час 10 минут назад")
        self.ckDefaultToTime("2day_ago", 3,
                                u"2 дня 0 часов 40 минут назад")

        self.ckDefaultToTime("in_10sec", 3, u"менее чем через минуту")
        self.ckDefaultToTime("in_1min", 3, u"через минуту")
        self.ckDefaultToTime("in_10min", 3, u"через 10 минут")
        self.ckDefaultToTime("in_1hr", 3, u"через 1 час 2 минуты")
        self.ckDefaultToTime("in_10hr", 3, u"через 10 часов 10 минут")
        self.ckDefaultToTime("in_1day", 3,
                                u"через 1 день 0 часов 20 минут")
        self.ckDefaultToTime("in_1day1hr", 3,
                                u"через 1 день 1 час 10 минут")
        self.ckDefaultToTime("in_2day", 3,
                                u"через 2 дня 0 часов 40 минут")

    def testDOTWDatetimeType(self):
        """
        Unit-tests for testing datetime.datetime as input values
        """
        first_time = datetime.datetime.now()
        second_time = first_time + datetime.timedelta(0, 1000)
        self.assertEquals(pytils.dt.distance_of_time_in_words(
            from_time=first_time,
            accuracy=1,
            to_time=second_time),
                          u"16 минут назад")

    def testDOTIWExceptions(self):
        """
        Unit-tests for testings distance_of_time_in_words' exceptions
        """
        self.assertRaises(ValueError, pytils.dt.distance_of_time_in_words, time.time(), 0)
    
    def testIssue25DaysFixed(self):
        """
        Unit-test for testing that Issue#25 is fixed (err when accuracy==1, days<>0, hours==1)
        """
        d_days = datetime.datetime.now() - datetime.timedelta(13, 3620)
        self.assertEquals(pytils.dt.distance_of_time_in_words(d_days),
                          u"13 дней назад")

    def testIssue25HoursFixed(self):
        """
        Unit-test for testing that Issue#25 is fixed (err when accuracy==1, hours<>0, minutes==1)
        """
        d_hours = datetime.datetime.now() - datetime.timedelta(0, 46865)
        self.assertEquals(pytils.dt.distance_of_time_in_words(d_hours),
                          u"13 часов назад")
        

class RuStrftimeTestCase(unittest.TestCase):
    """
    Test case for pytils.dt.ru_strftime
    """

    def setUp(self):
        """
        Setting up environment for tests
        """
        self.date = datetime.date(2006, 8, 25)
    
    def ck(self, format, estimates, date=None):
        """
        Checks w/o inflected
        """
        if date is None:
            date = self.date
        res = pytils.dt.ru_strftime(format, date)
        self.assertEquals(res, estimates)

    def ckInflected(self, format, estimates, date=None):
        """
        Checks with inflected
        """
        if date is None:
            date = self.date
        res = pytils.dt.ru_strftime(format, date, True)
        self.assertEquals(res, estimates)

    def ckInflectedDay(self, format, estimates, date=None):
        """
        Checks with inflected day
        """
        if date is None:
            date = self.date
        res = pytils.dt.ru_strftime(format, date, inflected_day=True)
        self.assertEquals(res, estimates)

    def ckPreposition(self, format, estimates, date=None):
        """
        Checks with inflected day
        """
        if date is None:
            date = self.date
        res = pytils.dt.ru_strftime(format, date, preposition=True)
        self.assertEquals(res, estimates)

    def testRuStrftime(self):
        """
        Unit-tests for pytils.dt.ru_strftime
        """
        self.ck(u"тест %a", u"тест пт")
        self.ck(u"тест %A", u"тест пятница")
        self.ck(u"тест %b", u"тест авг")
        self.ck(u"тест %B", u"тест август")
        self.ckInflected(u"тест %B", u"тест августа")
        self.ckInflected(u"тест выполнен %d %B %Y года",
                          u"тест выполнен 25 августа 2006 года")
        self.ckInflectedDay(u"тест выполнен в %A", u"тест выполнен в пятницу")
    
    def testRuStrftimeWithPreposition(self):
        """
        Unit-tests for pytils.dt.ru_strftime with preposition option
        """
        self.ckPreposition(u"тест %a", u"тест в\xa0пт")
        self.ckPreposition(u"тест %A", u"тест в\xa0пятницу")
        self.ckPreposition(u"тест %A", u"тест во\xa0вторник", datetime.date(2007, 6, 5))
    
    def testRuStrftimeZeros(self):
        """
        Unit-test for testing that Issue#24 is correctly implemented
        
        It means, 1 April 2007, but 01.04.2007
        """
        self.ck(u"%d.%m.%Y", u"01.04.2007", datetime.date(2007, 4, 1))
        self.ckInflected(u"%d %B %Y", u"1 апреля 2007", datetime.date(2007, 4, 1))


    def testIssue20Fixed(self):
        """
        Unit-test for testing that Issue#20 is fixed (typo)
        """
        self.assertEquals(u"воскресенье",
                          pytils.dt.ru_strftime(
                              u"%A",
                              datetime.date(2007,3,18),
                              inflected_day=True)
                         )
        

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_numeral
# -*- coding: utf-8 -*-
"""
Unit-tests for pytils.numeral
"""

import unittest
import decimal
import pytils

# Python3 doesn't have long type
# it has only int
from pytils.third import six

if six.PY3:
    long = int


class ChoosePluralTestCase(unittest.TestCase):
    """
    Test case for pytils.numeral.choose_plural
    """

    def setUp(self):
        """
        Setting up environment for tests
        """
        self.variants = (u"гвоздь", u"гвоздя", u"гвоздей")

    def checkChoosePlural(self, amount, estimated):
        """
        Checks choose_plural
        """
        self.assertEquals(pytils.numeral.choose_plural(amount, self.variants),
                          estimated)
    
    def testChoosePlural(self):
        """
        Unit-test for choose_plural
        """
        self.checkChoosePlural(1, u"гвоздь")
        self.checkChoosePlural(2, u"гвоздя")
        self.checkChoosePlural(3, u"гвоздя")
        self.checkChoosePlural(5, u"гвоздей")
        self.checkChoosePlural(11, u"гвоздей")
        self.checkChoosePlural(109, u"гвоздей")
        self.checkChoosePlural(long(109), u"гвоздей")

    def testChoosePluralNegativeBug9(self):
        """
        Test handling of negative numbers
        """
        self.checkChoosePlural(-5, u"гвоздей")
        self.checkChoosePlural(-2, u"гвоздя")

    def testChoosePluralExceptions(self):
        """
        Unit-test for testing choos_plural's exceptions
        """
        self.assertRaises(ValueError, pytils.numeral.choose_plural,
                          25, u"any,bene")

    def testChoosePluralVariantsInStr(self):
        """
        Tests new-style variants
        """
        self.assertEquals(
            pytils.numeral.choose_plural(1,u"гвоздь,гвоздя, гвоздей"),
            u"гвоздь")
        self.assertEquals(
            pytils.numeral.choose_plural(5,u"гвоздь, гвоздя, гвоздей\, шпунтов"),
            u"гвоздей, шпунтов")

class GetPluralTestCase(unittest.TestCase):
    """
    Test case for get_plural
    """
    def testGetPlural(self):
        """
        Test regular get_plural
        """
        self.assertEquals(
            pytils.numeral.get_plural(1, u"комментарий, комментария, комментариев"),
            u"1 комментарий")
        self.assertEquals(
            pytils.numeral.get_plural(0, u"комментарий, комментария, комментариев"),
            u"0 комментариев")
        
    def testGetPluralAbsence(self):
        """
        Test get_plural with absence
        """
        self.assertEquals(
            pytils.numeral.get_plural(1, u"комментарий, комментария, комментариев",
                                      u"без комментариев"),
            u"1 комментарий")
        self.assertEquals(
            pytils.numeral.get_plural(0, u"комментарий, комментария, комментариев",
                                      u"без комментариев"),
            u"без комментариев")

    def testGetPluralLegacy(self):
        """
        Test _get_plural_legacy
        """
        self.assertEquals(
            pytils.numeral._get_plural_legacy(1, u"комментарий, комментария, комментариев"),
            u"1 комментарий")
        self.assertEquals(
            pytils.numeral._get_plural_legacy(0, u"комментарий, комментария, комментариев"),
            u"0 комментариев")
        self.assertEquals(
            pytils.numeral._get_plural_legacy(1, u"комментарий, комментария, комментариев, без комментариев"),
            u"1 комментарий")
        self.assertEquals(
            pytils.numeral._get_plural_legacy(0, u"комментарий, комментария, комментариев, без комментариев"),
            u"без комментариев")
        

class GetFloatRemainderTestCase(unittest.TestCase):
    """
    Test case for pytils.numeral._get_float_remainder
    """

    def testFloatRemainder(self):
        """
        Unit-test for _get_float_remainder
        """
        self.assertEquals(pytils.numeral._get_float_remainder(1.3),
                          '3')
        self.assertEquals(pytils.numeral._get_float_remainder(2.35, 1),
                          '4')
        self.assertEquals(pytils.numeral._get_float_remainder(123.1234567891),
                          '123456789')
        self.assertEquals(pytils.numeral._get_float_remainder(2.353, 2),
                          '35')
        self.assertEquals(pytils.numeral._get_float_remainder(0.01),
                          '01')
        self.assertEquals(pytils.numeral._get_float_remainder(5),
                          '0')

    def testFloatRemainderDecimal(self):
        """
        Unit-test for _get_float_remainder with decimal type
        """
        D = decimal.Decimal
        self.assertEquals(pytils.numeral._get_float_remainder(D("1.3")),
                          '3')
        self.assertEquals(pytils.numeral._get_float_remainder(D("2.35"), 1),
                          '4')
        self.assertEquals(pytils.numeral._get_float_remainder(D("123.1234567891")),
                          '123456789')
        self.assertEquals(pytils.numeral._get_float_remainder(D("2.353"), 2),
                          '35')
        self.assertEquals(pytils.numeral._get_float_remainder(D("0.01")),
                          '01')
        self.assertEquals(pytils.numeral._get_float_remainder(D("5")),
                          '0')

    def testFloatRemainderExceptions(self):
        """
        Unit-test for testing _get_float_remainder's exceptions
        """
        self.assertRaises(ValueError, pytils.numeral._get_float_remainder,
                          2.998, 2)
        self.assertRaises(ValueError, pytils.numeral._get_float_remainder, -1.23)

class RublesTestCase(unittest.TestCase):
    """
    Test case for pytils.numeral.rubles
    """

    def testRubles(self):
        """
        Unit-test for rubles
        """
        self.assertEquals(pytils.numeral.rubles(10.01),
                          u"десять рублей одна копейка")
        self.assertEquals(pytils.numeral.rubles(10.10),
                          u"десять рублей десять копеек")
        self.assertEquals(pytils.numeral.rubles(2.353),
                          u"два рубля тридцать пять копеек")
        self.assertEquals(pytils.numeral.rubles(2.998),
                          u"три рубля")
        self.assertEquals(pytils.numeral.rubles(3),
                          u"три рубля")
        self.assertEquals(pytils.numeral.rubles(3, True),
                          u"три рубля ноль копеек")
        self.assertEquals(pytils.numeral.rubles(long(3)),
                          u"три рубля")

    def testRublesDecimal(self):
        """
        Test for rubles with decimal instead of float/integer
        """
        D = decimal.Decimal
        self.assertEquals(pytils.numeral.rubles(D("10.01")),
                          u"десять рублей одна копейка")
        self.assertEquals(pytils.numeral.rubles(D("10.10")),
                          u"десять рублей десять копеек")
        self.assertEquals(pytils.numeral.rubles(D("2.35")),
                          u"два рубля тридцать пять копеек")
        self.assertEquals(pytils.numeral.rubles(D(3)),
                          u"три рубля")
        self.assertEquals(pytils.numeral.rubles(D(3), True),
                          u"три рубля ноль копеек")

    def testRublesExceptions(self):
        """
        Unit-test for testing rubles' exceptions
        """
        self.assertRaises(ValueError, pytils.numeral.rubles, -15)
        

class InWordsTestCase(unittest.TestCase):
    """
    Test case for pytils.numeral.in_words
    """

    def testInt(self):
        """
        Unit-test for in_words_int
        """
        self.assertEquals(pytils.numeral.in_words_int(10), u"десять")
        self.assertEquals(pytils.numeral.in_words_int(5), u"пять")
        self.assertEquals(pytils.numeral.in_words_int(102), u"сто два")
        self.assertEquals(pytils.numeral.in_words_int(3521),
                          u"три тысячи пятьсот двадцать один")
        self.assertEquals(pytils.numeral.in_words_int(3500),
                          u"три тысячи пятьсот")
        self.assertEquals(pytils.numeral.in_words_int(5231000),
                          u"пять миллионов двести тридцать одна тысяча")
        self.assertEquals(pytils.numeral.in_words_int(long(10)), u"десять")

    def testIntExceptions(self):
        """
        Unit-test for testing in_words_int's exceptions
        """
        self.assertRaises(ValueError, pytils.numeral.in_words_int, -3)

    def testFloat(self):
        """
        Unit-test for in_words_float
        """
        self.assertEquals(pytils.numeral.in_words_float(10.0),
                          u"десять целых ноль десятых")
        self.assertEquals(pytils.numeral.in_words_float(2.25),
                          u"две целых двадцать пять сотых")
        self.assertEquals(pytils.numeral.in_words_float(0.01),
                          u"ноль целых одна сотая")
        self.assertEquals(pytils.numeral.in_words_float(0.10),
                          u"ноль целых одна десятая")

    def testDecimal(self):
        """
        Unit-test for in_words_float with decimal type
        """
        D = decimal.Decimal
        self.assertEquals(pytils.numeral.in_words_float(D("10.0")),
                          u"десять целых ноль десятых")
        self.assertEquals(pytils.numeral.in_words_float(D("2.25")),
                          u"две целых двадцать пять сотых")
        self.assertEquals(pytils.numeral.in_words_float(D("0.01")),
                          u"ноль целых одна сотая")
        # поскольку это Decimal, то здесь нет незначащих нулей
        # т.е. нули определяют точность, поэтому десять сотых,
        # а не одна десятая
        self.assertEquals(pytils.numeral.in_words_float(D("0.10")),
                          u"ноль целых десять сотых")

    def testFloatExceptions(self):
        """
        Unit-test for testing in_words_float's exceptions
        """
        self.assertRaises(ValueError, pytils.numeral.in_words_float, -2.3)

    def testWithGenderOldStyle(self):
        """
        Unit-test for in_words_float with gender (old-style, i.e. ints)
        """
        self.assertEquals(pytils.numeral.in_words(21, 1),
                          u"двадцать один")
        self.assertEquals(pytils.numeral.in_words(21, 2),
                          u"двадцать одна")
        self.assertEquals(pytils.numeral.in_words(21, 3),
                          u"двадцать одно")
        # на дробные пол не должен влиять - всегда в женском роде
        self.assertEquals(pytils.numeral.in_words(21.0, 1),
                          u"двадцать одна целая ноль десятых")
        self.assertEquals(pytils.numeral.in_words(21.0, 2),
                          u"двадцать одна целая ноль десятых")
        self.assertEquals(pytils.numeral.in_words(21.0, 3),
                          u"двадцать одна целая ноль десятых")
        self.assertEquals(pytils.numeral.in_words(long(21), 1),
                          u"двадцать один")

    def testWithGender(self):
        """
        Unit-test for in_words_float with gender (old-style, i.e. ints)
        """
        self.assertEquals(pytils.numeral.in_words(21, pytils.numeral.MALE),
                          u"двадцать один")
        self.assertEquals(pytils.numeral.in_words(21, pytils.numeral.FEMALE),
                          u"двадцать одна")
        self.assertEquals(pytils.numeral.in_words(21, pytils.numeral.NEUTER),
                          u"двадцать одно")
        # на дробные пол не должен влиять - всегда в женском роде
        self.assertEquals(pytils.numeral.in_words(21.0, pytils.numeral.MALE),
                          u"двадцать одна целая ноль десятых")
        self.assertEquals(pytils.numeral.in_words(21.0, pytils.numeral.FEMALE),
                          u"двадцать одна целая ноль десятых")
        self.assertEquals(pytils.numeral.in_words(21.0, pytils.numeral.NEUTER),
                          u"двадцать одна целая ноль десятых")
        self.assertEquals(pytils.numeral.in_words(long(21), pytils.numeral.MALE),
                          u"двадцать один")


    def testCommon(self):
        """
        Unit-test for general in_words
        """
        D = decimal.Decimal
        self.assertEquals(pytils.numeral.in_words(10), u"десять")
        self.assertEquals(pytils.numeral.in_words(5), u"пять")
        self.assertEquals(pytils.numeral.in_words(102), u"сто два")
        self.assertEquals(pytils.numeral.in_words(3521),
                          u"три тысячи пятьсот двадцать один")
        self.assertEquals(pytils.numeral.in_words(3500),
                          u"три тысячи пятьсот")
        self.assertEquals(pytils.numeral.in_words(5231000),
                          u"пять миллионов двести тридцать одна тысяча")
        self.assertEquals(pytils.numeral.in_words(10.0),
                          u"десять целых ноль десятых")
        self.assertEquals(pytils.numeral.in_words(2.25),
                          u"две целых двадцать пять сотых")
        self.assertEquals(pytils.numeral.in_words(0.01),
                          u"ноль целых одна сотая")
        self.assertEquals(pytils.numeral.in_words(0.10),
                          u"ноль целых одна десятая")
        self.assertEquals(pytils.numeral.in_words(long(10)), u"десять")
        self.assertEquals(pytils.numeral.in_words(D("2.25")),
                          u"две целых двадцать пять сотых")
        self.assertEquals(pytils.numeral.in_words(D("0.01")),
                          u"ноль целых одна сотая")
        self.assertEquals(pytils.numeral.in_words(D("0.10")),
                          u"ноль целых десять сотых")
        self.assertEquals(pytils.numeral.in_words(D("10")), u"десять")

    def testCommonExceptions(self):
        """
        Unit-test for testing in_words' exceptions
        """
        self.assertRaises(ValueError, pytils.numeral.in_words, -2)
        self.assertRaises(ValueError, pytils.numeral.in_words, -2.5)


class SumStringTestCase(unittest.TestCase):
    """
    Test case for pytils.numeral.sum_string
    """
    
    def setUp(self):
        """
        Setting up environment for tests
        """
        self.variants_male = (u"гвоздь", u"гвоздя", u"гвоздей")
        self.variants_female = (u"шляпка", u"шляпки", u"шляпок")

    def ckMaleOldStyle(self, amount, estimated):
        """
        Checks sum_string with male gender with old-style genders (i.e. ints)
        """
        self.assertEquals(pytils.numeral.sum_string(amount,
                                                    1,
                                                    self.variants_male),
                          estimated)

    def ckMale(self, amount, estimated):
        """
        Checks sum_string with male gender
        """
        self.assertEquals(pytils.numeral.sum_string(amount,
                                                    pytils.numeral.MALE,
                                                    self.variants_male),
                          estimated)


    def ckFemaleOldStyle(self, amount, estimated):
        """
        Checks sum_string with female gender wuth old-style genders (i.e. ints)
        """
        self.assertEquals(pytils.numeral.sum_string(amount,
                                                    2,
                                                    self.variants_female),
                          estimated)

    def ckFemale(self, amount, estimated):
        """
        Checks sum_string with female gender
        """
        self.assertEquals(pytils.numeral.sum_string(amount,
                                                    pytils.numeral.FEMALE,
                                                    self.variants_female),
                          estimated)

    def testSumStringOldStyleGender(self):
        """
        Unit-test for sum_string with old-style genders
        """
        self.ckMaleOldStyle(10, u"десять гвоздей")
        self.ckMaleOldStyle(2, u"два гвоздя")
        self.ckMaleOldStyle(31, u"тридцать один гвоздь")
        self.ckFemaleOldStyle(10, u"десять шляпок")
        self.ckFemaleOldStyle(2, u"две шляпки")
        self.ckFemaleOldStyle(31, u"тридцать одна шляпка")
        
        self.ckFemaleOldStyle(long(31), u"тридцать одна шляпка")

        self.assertEquals(u"одиннадцать негритят",
                          pytils.numeral.sum_string(
                              11,
                              1,
                              u"негритенок,негритенка,негритят"
                              ))

    def testSumString(self):
        """
        Unit-test for sum_string
        """
        self.ckMale(10, u"десять гвоздей")
        self.ckMale(2, u"два гвоздя")
        self.ckMale(31, u"тридцать один гвоздь")
        self.ckFemale(10, u"десять шляпок")
        self.ckFemale(2, u"две шляпки")
        self.ckFemale(31, u"тридцать одна шляпка")
        
        self.ckFemale(long(31), u"тридцать одна шляпка")

        self.assertEquals(u"одиннадцать негритят",
                          pytils.numeral.sum_string(
                              11,
                              pytils.numeral.MALE,
                              u"негритенок,негритенка,негритят"
                              ))

    def testSumStringExceptions(self):
        """
        Unit-test for testing sum_string's exceptions
        """
        self.assertRaises(ValueError, pytils.numeral.sum_string,
                                      -1, pytils.numeral.MALE, u"any,bene,raba")

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_translit
# -*- coding: utf-8 -*-
"""
Unit-tests for pytils.translit
"""

import unittest
import pytils
from pytils.third import six

class TranslitTestCase(unittest.TestCase):
    """
    Test case for pytils.translit
    """

    def ckTransl(self, in_, out_):
        """
        Checks translify
        """
        self.assertEquals(pytils.translit.translify(in_), out_)

    def ckDetransl(self, in_, out_):
        """
        Checks detranslify
        """
        self.assertEquals(pytils.translit.detranslify(in_), out_)

    def ckSlug(self, in_, out_):
        """
        Checks slugify
        """
        self.assertEquals(pytils.translit.slugify(in_), out_)

    def testTransliteration(self):
        """
        Unit-test for transliterations
        """
        self.ckTransl(u"тест", 'test')
        self.ckTransl(u"проверка", 'proverka')
        self.ckTransl(u"транслит", 'translit')
        self.ckTransl(u"правда ли это", 'pravda li eto')
        self.ckTransl(u"Щука", 'Schuka')

    def testTransliterationExceptions(self):
        """
        Unit-test for testing translify's exceptions
        """
        self.assertRaises(ValueError, pytils.translit.translify, u'\u00bfHabla espa\u00f1ol?')

    def testDetransliteration(self):
        """
        Unit-test for detransliterations
        """
        self.ckDetransl('test', u"тест")
        self.ckDetransl('proverka', u"проверка")
        self.ckDetransl('translit', u"транслит")
        self.ckDetransl('SCHuka', u"Щука")
        self.ckDetransl('Schuka', u"Щука")

    def testDetransliterationExceptions(self):
        """
        Unit-test for testing detranslify's exceptions
        """
        # for Python 2.x non-unicode detranslify should raise exception
        if six.PY2:
            self.assertRaises(ValueError, pytils.translit.detranslify, "тест")

    def testSlug(self):
        """
        Unit-test for slugs
        """
        self.ckSlug(u"ТеСт", 'test')
        self.ckSlug(u"Проверка связи", 'proverka-svyazi')
        self.ckSlug(u"me&you", 'me-and-you')
        self.ckSlug(u"и еще один тест", 'i-esche-odin-test')

    def testSlugExceptions(self):
        """
        Unit-test for testing slugify's exceptions
        """
        # for Python 2.x non-unicode slugify should raise exception
        if six.PY2:
            self.assertRaises(ValueError, pytils.translit.slugify, "тест")

    def testTranslifyAdditionalUnicodeSymbols(self):
        """
        Unit-test for testing additional unicode symbols
        """
        self.ckTransl(u"«Вот так вот»", '"Vot tak vot"')
        self.ckTransl(u"‘Или вот так’", "'Ili vot tak'")
        self.ckTransl(u"– Да…", "- Da...")

    def testSlugifyIssue10(self):
        """
        Unit-test for testing that bug#10 fixed
        """
        self.ckSlug(u"Проверка связи…", 'proverka-svyazi')
        self.ckSlug(u"Проверка\x0aсвязи 2", 'proverka-svyazi-2')
        self.ckSlug(u"Проверка\201связи 3", 'proverkasvyazi-3')

    def testSlugifyIssue15(self):
        """
        Unit-test for testing that bug#15 fixed
        """
        self.ckSlug(u"World of Warcraft", "world-of-warcraft")

    def testAdditionalDashesAndQuotes(self):
        """
        Unit-test for testing additional dashes (figure and em-dash)
        and quotes
        """
        self.ckSlug(u"Юнит-тесты — наше всё", 'yunit-testyi---nashe-vsyo')
        self.ckSlug(u"Юнит-тесты ‒ наше всё", 'yunit-testyi---nashe-vsyo')
        self.ckSlug(u"95−34", '95-34')
        self.ckTransl(u"Двигатель “Pratt&Whitney”", 'Dvigatel\' "Pratt&Whitney"')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_typo
# -*- coding: utf-8 -*-
"""
Unit-tests for pytils.typo
"""

import unittest
import os
from pytils import typo

def cb_testrule(x):
    return x

class HelpersTestCase(unittest.TestCase):
    """
    Test case for pytils.typo helpers
    """
    def testGetRuleByName(self):
        """
        unit-test for pytils.typo._get_rule_by_name
        """
        self.assert_(
            callable(
                typo._get_rule_by_name('testrule')
        ))
        self.assertEquals(
            'rl_testrule',
            typo._get_rule_by_name('testrule').__name__
        )
    
    def testResolveRule(self):
        """
        unit-test for pytils.typo._resolve_rule
        """
        self.assert_(
            callable(
                typo._resolve_rule_name('testrule')[1]
        ))
        self.assert_(
            callable(
                typo._resolve_rule_name(cb_testrule)[1]
        ))
        self.assertEquals(
            'testrule',
            typo._resolve_rule_name('testrule')[0]
        )
        self.assertEquals(
            'cb_testrule',
            typo._resolve_rule_name(cb_testrule)[0]
        )

    def testResolveRuleWithForcedName(self):
        """
        unit-test for pytils.typo._resolve_rule with forced_name arg
        """
        self.assert_(
            callable(typo._resolve_rule_name('testrule', 'newrule')[1]
        ))
        self.assert_(
            callable(typo._resolve_rule_name(cb_testrule, 'newrule')[1]
        ))
        self.assertEquals(
            'newrule',
            typo._resolve_rule_name('testrule', 'newrule')[0]
        )
        self.assertEquals(
            'newrule',
            typo._resolve_rule_name(cb_testrule, 'newrule')[0]
        )

class TypographyApplierTestCase(unittest.TestCase):
    """
    Test case for typography rule applier pytils.typo.Typography
    """
    def testExpandEmptyArgs(self):
        self.assertEquals(
            {},
            typo.Typography().rules
        )
        self.assertEquals(
            [],
            typo.Typography().rules_names
        )
    
    def testExpandSimpleStrArgs(self):
        self.assertEquals(
            {'testrule': typo.rl_testrule},
            typo.Typography('testrule').rules
        )
        self.assertEquals(
            ['testrule'],
            typo.Typography('testrule').rules_names
        )
    
    def testExpandDictStrArgs(self):
        self.assertEquals(
            {
                'testrule': typo.rl_testrule,
                'newrule':  typo.rl_testrule
            },
            typo.Typography('testrule', {'newrule': 'testrule'}).rules
        )
        self.assertEquals(
            ['testrule', 'newrule'],
            typo.Typography('testrule', {'newrule': 'testrule'}).rules_names
        )

    def testExpandSimpleCallableArgs(self):
        self.assertEquals(
            {'cb_testrule': cb_testrule},
            typo.Typography(cb_testrule).rules
        )
        self.assertEquals(
            ['cb_testrule'],
            typo.Typography(cb_testrule).rules_names
        )
    
    def testExpandDictCallableArgs(self):
        self.assertEquals(
            {
                'cb_testrule': cb_testrule,
                'newrule': cb_testrule
            },
            typo.Typography(cb_testrule, {'newrule': cb_testrule}).rules
        )
        self.assertEquals(
            ['cb_testrule', 'newrule'],
            typo.Typography(cb_testrule, {'newrule': cb_testrule}).rules_names
        )

    def testExpandMixedArgs(self):
        self.assertEquals(
            {
                'cb_testrule': cb_testrule,
                'newrule': typo.rl_testrule
            },
            typo.Typography(cb_testrule, newrule='testrule').rules
        )
        self.assertEquals(
            ['cb_testrule', 'newrule'],
            typo.Typography(cb_testrule, newrule='testrule').rules_names
        )
        self.assertEquals(
            {
                'cb_testrule': cb_testrule,
                'testrule': typo.rl_testrule
            },
            typo.Typography(cb_testrule, 'testrule').rules
        )
        self.assertEquals(
            ['cb_testrule', 'testrule'],
            typo.Typography(cb_testrule, 'testrule').rules_names
        )

    def testRecommendedArgsStyle(self):
        lambdarule = lambda x: x
        self.assertEquals(
            {
                'cb_testrule': cb_testrule,
                'testrule': typo.rl_testrule,
                'newrule': lambdarule
            },
            typo.Typography([cb_testrule], ['testrule'], {'newrule': lambdarule}).rules
        )
        self.assertEquals(
            ['cb_testrule', 'testrule', 'newrule'],
            typo.Typography([cb_testrule], ['testrule'], {'newrule': lambdarule}).rules_names
        )

class RulesTestCase(unittest.TestCase):

    def checkRule(self, name, input_value, expected_result):
        """
        Check how rule is acted on input_value with expected_result
        """
        self.assertEquals(
            expected_result,
            typo._get_rule_by_name(name)(input_value)
        )
    
    def testCleanspaces(self):
        """
        Unit-test for cleanspaces rule
        """
        self.checkRule(
            'cleanspaces',
            u" Точка ,точка , запятая, вышла рожица  кривая . ",
            u"Точка, точка, запятая, вышла рожица кривая."
        )
        self.checkRule(
            'cleanspaces',
            u" Точка ,точка , %(n)sзапятая,%(n)s вышла рожица  кривая . " % {'n': os.linesep},
            u"Точка, точка,%(n)sзапятая,%(n)sвышла рожица кривая." % {'n': os.linesep}
        )
        self.checkRule(
            'cleanspaces',
            u"Газета ( ее принес мальчишка утром ) всё еще лежала на столе.",
            u"Газета (ее принес мальчишка утром) всё еще лежала на столе.",
        )
        self.checkRule(
            'cleanspaces',
            u"Газета, утром принесенная мальчишкой ( это был сосед, подзарабатывающий летом ) , всё еще лежала на столе.",
            u"Газета, утром принесенная мальчишкой (это был сосед, подзарабатывающий летом), всё еще лежала на столе.",
        )
        self.checkRule(
            'cleanspaces',
            u"Что это?!?!",
            u"Что это?!?!",
        )

    def testEllipsis(self):
        """
        Unit-test for ellipsis rule
        """
        self.checkRule(
            'ellipsis',
            u"Быть или не быть, вот в чем вопрос...%(n)s%(n)sШекспир" % {'n': os.linesep},
            u"Быть или не быть, вот в чем вопрос…%(n)s%(n)sШекспир" % {'n': os.linesep}
        )
        self.checkRule(
            'ellipsis',
            u"Мдя..... могло быть лучше",
            u"Мдя..... могло быть лучше"
        )
        self.checkRule(
            'ellipsis',
            u"...Дааааа",
            u"…Дааааа"
        )
        self.checkRule(
            'ellipsis',
            u"... Дааааа",
            u"…Дааааа"
        )
        
    
    def testInitials(self):
        """
        Unit-test for initials rule
        """
        self.checkRule(
            'initials',
            u'Председатель В.И.Иванов выступил на собрании',
            u'Председатель В.И.\u2009Иванов выступил на собрании',
        )
        self.checkRule(
            'initials',
            u'Председатель В.И. Иванов выступил на собрании',
            u'Председатель В.И.\u2009Иванов выступил на собрании',
        )
        self.checkRule(
            'initials',
            u'1. В.И.Иванов%(n)s2. С.П.Васечкин'% {'n': os.linesep},
            u'1. В.И.\u2009Иванов%(n)s2. С.П.\u2009Васечкин' % {'n': os.linesep}
        )
        self.checkRule(
            'initials',
            u'Комиссия в составе директора В.И.Иванова и главного бухгалтера С.П.Васечкина постановила',
            u'Комиссия в составе директора В.И.\u2009Иванова и главного бухгалтера С.П.\u2009Васечкина постановила'
        )

    def testDashes(self):
        """
        Unit-test for dashes rule
        """
        self.checkRule(
            'dashes',
            u'- Я пошел домой... - Может останешься? - Нет, ухожу.',
            u'\u2014 Я пошел домой... \u2014 Может останешься? \u2014 Нет, ухожу.'
        )
        self.checkRule(
            'dashes',
            u'-- Я пошел домой... -- Может останешься? -- Нет, ухожу.',
            u'\u2014 Я пошел домой... \u2014 Может останешься? \u2014 Нет, ухожу.'
        )
        self.checkRule(
            'dashes',
            u'-- Я\u202fпошел домой…\u202f-- Может останешься?\u202f-- Нет,\u202fухожу.',
            u'\u2014 Я\u202fпошел домой…\u202f\u2014 Может останешься?\u202f\u2014 Нет,\u202fухожу.'
        )
        self.checkRule(
            'dashes',
            u'Ползать по-пластунски',
            u'Ползать по-пластунски',
        )
        self.checkRule(
            'dashes',
            u'Диапазон: 9-15',
            u'Диапазон: 9\u201315',
        )

    def testWordglue(self):
        """
        Unit-test for wordglue rule
        """
        self.checkRule(
            'wordglue',
            u'Вроде бы он согласен',
            u'Вроде\u202fбы\u202fон\u202fсогласен',
        )
        self.checkRule(
            'wordglue',
            u'Он не поверил своим глазам',
            u'Он\u202fне\u202fповерил своим\u202fглазам',
        )
        self.checkRule(
            'wordglue',
            u'Это - великий и ужасный Гудвин',
            u'Это\u202f- великий и\u202fужасный\u202fГудвин',
        )
        self.checkRule(
            'wordglue',
            u'Это \u2014 великий и ужасный Гудвин',
            u'Это\u202f\u2014 великий и\u202fужасный\u202fГудвин',
        )
        self.checkRule(
            'wordglue',
            u'-- Я пошел домой… -- Может останешься? -- Нет, ухожу.',
            u'-- Я\u202fпошел домой…\u202f-- Может останешься?\u202f-- Нет,\u202fухожу.'
        )
        self.checkRule(
            'wordglue',
            u'увидел в газете (это была "Сермяжная правда" № 45) рубрику Weather Forecast',
            u'увидел в\u202fгазете (это\u202fбыла "Сермяжная правда" № 45) рубрику Weather\u202fForecast',
        )
        

    def testMarks(self):
        """
        Unit-test for marks rule
        """
        self.checkRule(
            'marks',
            u"Когда В. И. Пупкин увидел в газете рубрику Weather Forecast(r), он не поверил своим глазам \u2014 температуру обещали +-451F.",
            u"Когда В. И. Пупкин увидел в газете рубрику Weather Forecast®, он не поверил своим глазам \u2014 температуру обещали ±451\u202f°F."
        )
        self.checkRule(
            'marks',
            u"14 Foo",
            u"14 Foo"
        )
        self.checkRule(
            'marks',
            u"Coca-cola(tm)",
            u"Coca-cola™"
        )
        self.checkRule(
            'marks',
            u'(c) 2008 Юрий Юревич',
            u'©\u202f2008 Юрий Юревич'
        )
        self.checkRule(
            'marks',
            u"Microsoft (R) Windows (tm)",
            u"Microsoft® Windows™"
        )
        self.checkRule(
            'marks',
            u"Школа-гимназия No 3",
            u"Школа-гимназия №\u20093",
        )
        self.checkRule(
            'marks',
            u"Школа-гимназия No3",
            u"Школа-гимназия №\u20093",
        )
        self.checkRule(
            'marks',
            u"Школа-гимназия №3",
            u"Школа-гимназия №\u20093",
        )

    def testQuotes(self):
        """
        Unit-test for quotes rule
        """
        self.checkRule(
            'quotes',
            u"ООО \"МСК \"Аско-Забота\"",
            u"ООО «МСК «Аско-Забота»"
        )
        self.checkRule(
            'quotes',
            u"ООО\u202f\"МСК\u202f\"Аско-Забота\"",
            u"ООО\u202f«МСК\u202f«Аско-Забота»"
        )
        self.checkRule(
            'quotes',
            u"Двигатели 'Pratt&Whitney'",
            u"Двигатели “Pratt&Whitney”"
        )
        self.checkRule(
            'quotes',
            u"\"Вложенные \"кавычки\" - бич всех типографик\", не правда ли",
            u"«Вложенные «кавычки» - бич всех типографик», не правда ли",
        )
        self.checkRule(
            'quotes',
            u"Двигатели 'Pratt&Whitney' никогда не использовались на самолетах \"Аэрофлота\"",
            u"Двигатели “Pratt&Whitney” никогда не использовались на самолетах «Аэрофлота»"
        )

class TypographyTestCase(unittest.TestCase):
    """
    Tests for pytils.typo.typography
    """
    def checkTypo(self, input_value, expected_value):
        """
        Helper for checking typo.typography
        """
        self.assertEquals(expected_value, typo.typography(input_value))
    
    def testPupkin(self):
        """
        Unit-test on pupkin-text
        """
        self.checkTypo(
        u"""...Когда В. И. Пупкин увидел в газете ( это была "Сермяжная правда" № 45) рубрику Weather Forecast(r), он не поверил своим глазам - температуру обещали +-451F.""",
        u"""…Когда В.И.\u2009Пупкин увидел в\u202fгазете (это\u202fбыла «Сермяжная правда» №\u200945) рубрику Weather Forecast®, он\u202fне\u202fповерил своим глазам\u202f\u2014 температуру обещали ±451\u202f°F.""")

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_utils
# -*- coding: utf-8 -*-
"""
Unit-tests for pytils.utils
"""

import unittest
import pytils
import decimal

    

class ChecksTestCase(unittest.TestCase):
    """
    Test case for check_* utils
    """
        
    def testCheckLength(self):
        """
        Unit-test for pytils.utils.check_length
        """
        self.assertEquals(pytils.utils.check_length("var", 3), None)
        
        self.assertRaises(ValueError, pytils.utils.check_length, "var", 4)
        self.assertRaises(ValueError, pytils.utils.check_length, "var", 2)
        self.assertRaises(ValueError, pytils.utils.check_length, (1,2), 3)

    def testCheckPositive(self):
        """
        Unit-test for pytils.utils.check_positive
        """
        self.assertEquals(pytils.utils.check_positive(0), None)
        self.assertEquals(pytils.utils.check_positive(1), None)
        self.assertEquals(pytils.utils.check_positive(1, False), None)
        self.assertEquals(pytils.utils.check_positive(1, strict=False), None)
        self.assertEquals(pytils.utils.check_positive(1, True), None)
        self.assertEquals(pytils.utils.check_positive(1, strict=True), None)
        self.assertEquals(pytils.utils.check_positive(decimal.Decimal("2.0")), None)
        self.assertEquals(pytils.utils.check_positive(2.0), None)
        
        self.assertRaises(ValueError, pytils.utils.check_positive, -2)
        self.assertRaises(ValueError, pytils.utils.check_positive, -2.0)
        self.assertRaises(ValueError, pytils.utils.check_positive, decimal.Decimal("-2.0"))
        self.assertRaises(ValueError, pytils.utils.check_positive, 0, True)


class SplitValuesTestCase(unittest.TestCase):
    
    def testClassicSplit(self):
        """
        Unit-test for pytils.utils.split_values, classic split
        """
        self.assertEquals((u"Раз", u"Два", u"Три"), pytils.utils.split_values(u"Раз,Два,Три"))
        self.assertEquals((u"Раз", u"Два", u"Три"), pytils.utils.split_values(u"Раз, Два,Три"))
        self.assertEquals((u"Раз", u"Два", u"Три"), pytils.utils.split_values(u" Раз,   Два, Три  "))
        self.assertEquals((u"Раз", u"Два", u"Три"), pytils.utils.split_values(u" Раз, \nДва,\n Три  "))
    
    def testEscapedSplit(self):
        """
        Unit-test for pytils.utils.split_values, split with escaping
        """
        self.assertEquals((u"Раз,Два", u"Три,Четыре", u"Пять,Шесть"), pytils.utils.split_values(u"Раз\,Два,Три\,Четыре,Пять\,Шесть"))
        self.assertEquals((u"Раз, Два", u"Три", u"Четыре"), pytils.utils.split_values(u"Раз\, Два, Три, Четыре"))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

# Copyright (c) 2010-2013 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.4.1"


# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform.startswith("java"):
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
        del X


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        result = self._resolve()
        setattr(obj, self.name, result)
        # This is a bit ugly, but it avoids running this again.
        delattr(tp, self.name)
        return result


class MovedModule(_LazyDescr):

    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)


class MovedAttribute(_LazyDescr):

    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)



class _MovedItems(types.ModuleType):
    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute("filterfalse", "itertools", "itertools", "ifilterfalse", "filterfalse"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("range", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("UserString", "UserString", "collections"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),
    MovedAttribute("zip_longest", "itertools", "itertools", "izip_longest", "zip_longest"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("email_mime_multipart", "email.MIMEMultipart", "email.mime.multipart"),
    MovedModule("email_mime_text", "email.MIMEText", "email.mime.text"),
    MovedModule("email_mime_base", "email.MIMEBase", "email.mime.base"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_parse", __name__ + ".moves.urllib_parse", "urllib.parse"),
    MovedModule("urllib_error", __name__ + ".moves.urllib_error", "urllib.error"),
    MovedModule("urllib", __name__ + ".moves.urllib", __name__ + ".moves.urllib"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
del attr

moves = sys.modules[__name__ + ".moves"] = _MovedItems(__name__ + ".moves")



class Module_six_moves_urllib_parse(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_parse"""


_urllib_parse_moved_attributes = [
    MovedAttribute("ParseResult", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qs", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qsl", "urlparse", "urllib.parse"),
    MovedAttribute("urldefrag", "urlparse", "urllib.parse"),
    MovedAttribute("urljoin", "urlparse", "urllib.parse"),
    MovedAttribute("urlparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlsplit", "urlparse", "urllib.parse"),
    MovedAttribute("urlunparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlunsplit", "urlparse", "urllib.parse"),
    MovedAttribute("quote", "urllib", "urllib.parse"),
    MovedAttribute("quote_plus", "urllib", "urllib.parse"),
    MovedAttribute("unquote", "urllib", "urllib.parse"),
    MovedAttribute("unquote_plus", "urllib", "urllib.parse"),
    MovedAttribute("urlencode", "urllib", "urllib.parse"),
]
for attr in _urllib_parse_moved_attributes:
    setattr(Module_six_moves_urllib_parse, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_parse"] = Module_six_moves_urllib_parse(__name__ + ".moves.urllib_parse")
sys.modules[__name__ + ".moves.urllib.parse"] = Module_six_moves_urllib_parse(__name__ + ".moves.urllib.parse")


class Module_six_moves_urllib_error(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_error"""


_urllib_error_moved_attributes = [
    MovedAttribute("URLError", "urllib2", "urllib.error"),
    MovedAttribute("HTTPError", "urllib2", "urllib.error"),
    MovedAttribute("ContentTooShortError", "urllib", "urllib.error"),
]
for attr in _urllib_error_moved_attributes:
    setattr(Module_six_moves_urllib_error, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_error"] = Module_six_moves_urllib_error(__name__ + ".moves.urllib_error")
sys.modules[__name__ + ".moves.urllib.error"] = Module_six_moves_urllib_error(__name__ + ".moves.urllib.error")


class Module_six_moves_urllib_request(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_request"""


_urllib_request_moved_attributes = [
    MovedAttribute("urlopen", "urllib2", "urllib.request"),
    MovedAttribute("install_opener", "urllib2", "urllib.request"),
    MovedAttribute("build_opener", "urllib2", "urllib.request"),
    MovedAttribute("pathname2url", "urllib", "urllib.request"),
    MovedAttribute("url2pathname", "urllib", "urllib.request"),
    MovedAttribute("getproxies", "urllib", "urllib.request"),
    MovedAttribute("Request", "urllib2", "urllib.request"),
    MovedAttribute("OpenerDirector", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDefaultErrorHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPRedirectHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPCookieProcessor", "urllib2", "urllib.request"),
    MovedAttribute("ProxyHandler", "urllib2", "urllib.request"),
    MovedAttribute("BaseHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgr", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgrWithDefaultRealm", "urllib2", "urllib.request"),
    MovedAttribute("AbstractBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("AbstractDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPSHandler", "urllib2", "urllib.request"),
    MovedAttribute("FileHandler", "urllib2", "urllib.request"),
    MovedAttribute("FTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("CacheFTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("UnknownHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPErrorProcessor", "urllib2", "urllib.request"),
    MovedAttribute("urlretrieve", "urllib", "urllib.request"),
    MovedAttribute("urlcleanup", "urllib", "urllib.request"),
    MovedAttribute("URLopener", "urllib", "urllib.request"),
    MovedAttribute("FancyURLopener", "urllib", "urllib.request"),
]
for attr in _urllib_request_moved_attributes:
    setattr(Module_six_moves_urllib_request, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_request"] = Module_six_moves_urllib_request(__name__ + ".moves.urllib_request")
sys.modules[__name__ + ".moves.urllib.request"] = Module_six_moves_urllib_request(__name__ + ".moves.urllib.request")


class Module_six_moves_urllib_response(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_response"""


_urllib_response_moved_attributes = [
    MovedAttribute("addbase", "urllib", "urllib.response"),
    MovedAttribute("addclosehook", "urllib", "urllib.response"),
    MovedAttribute("addinfo", "urllib", "urllib.response"),
    MovedAttribute("addinfourl", "urllib", "urllib.response"),
]
for attr in _urllib_response_moved_attributes:
    setattr(Module_six_moves_urllib_response, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_response"] = Module_six_moves_urllib_response(__name__ + ".moves.urllib_response")
sys.modules[__name__ + ".moves.urllib.response"] = Module_six_moves_urllib_response(__name__ + ".moves.urllib.response")


class Module_six_moves_urllib_robotparser(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_robotparser"""


_urllib_robotparser_moved_attributes = [
    MovedAttribute("RobotFileParser", "robotparser", "urllib.robotparser"),
]
for attr in _urllib_robotparser_moved_attributes:
    setattr(Module_six_moves_urllib_robotparser, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_robotparser"] = Module_six_moves_urllib_robotparser(__name__ + ".moves.urllib_robotparser")
sys.modules[__name__ + ".moves.urllib.robotparser"] = Module_six_moves_urllib_robotparser(__name__ + ".moves.urllib.robotparser")


class Module_six_moves_urllib(types.ModuleType):
    """Create a six.moves.urllib namespace that resembles the Python 3 namespace"""
    parse = sys.modules[__name__ + ".moves.urllib_parse"]
    error = sys.modules[__name__ + ".moves.urllib_error"]
    request = sys.modules[__name__ + ".moves.urllib_request"]
    response = sys.modules[__name__ + ".moves.urllib_response"]
    robotparser = sys.modules[__name__ + ".moves.urllib_robotparser"]


sys.modules[__name__ + ".moves.urllib"] = Module_six_moves_urllib(__name__ + ".moves.urllib")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_closure = "__closure__"
    _func_code = "__code__"
    _func_defaults = "__defaults__"
    _func_globals = "__globals__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
    _iterlists = "lists"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_closure = "func_closure"
    _func_code = "func_code"
    _func_defaults = "func_defaults"
    _func_globals = "func_globals"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"
    _iterlists = "iterlists"


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator


try:
    callable = callable
except NameError:
    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)


if PY3:
    def get_unbound_function(unbound):
        return unbound

    create_bound_method = types.MethodType

    Iterator = object
else:
    def get_unbound_function(unbound):
        return unbound.im_func

    def create_bound_method(func, obj):
        return types.MethodType(func, obj, obj.__class__)

    class Iterator(object):

        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_closure = operator.attrgetter(_func_closure)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)
get_function_globals = operator.attrgetter(_func_globals)


def iterkeys(d, **kw):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)(**kw))

def itervalues(d, **kw):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)(**kw))

def iteritems(d, **kw):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)(**kw))

def iterlists(d, **kw):
    """Return an iterator over the (key, [values]) pairs of a dictionary."""
    return iter(getattr(d, _iterlists)(**kw))


if PY3:
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s
    unichr = chr
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    byte2int = operator.itemgetter(0)
    indexbytes = operator.getitem
    iterbytes = iter
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    def u(s):
        return unicode(s, "unicode_escape")
    unichr = unichr
    int2byte = chr
    def byte2int(bs):
        return ord(bs[0])
    def indexbytes(buf, i):
        return ord(buf[i])
    def iterbytes(buf):
        return (ord(byte) for byte in buf)
    import StringIO
    StringIO = BytesIO = StringIO.StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


if PY3:
    import builtins
    exec_ = getattr(builtins, "exec")


    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value


    print_ = getattr(builtins, "print")
    del builtins

else:
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")


    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")


    def print_(*args, **kwargs):
        """The new-style print function."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return
        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    return meta("NewBase", bases, {})

def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        for slots_var in orig_vars.get('__slots__', ()):
            orig_vars.pop(slots_var)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper

########NEW FILE########
__FILENAME__ = translit
# -*- coding: utf-8 -*-
# -*- test-case-name: pytils.test.test_translit -*-
"""
Simple transliteration
"""

import re
from pytils.third import six

TRANSTABLE = (
        (u"'", u"'"),
        (u'"', u'"'),
        (u"‘", u"'"),
        (u"’", u"'"),
        (u"«", u'"'),
        (u"»", u'"'),
        (u"“", u'"'),
        (u"”", u'"'),
        (u"–", u"-"),  # en dash
        (u"—", u"-"),  # em dash
        (u"‒", u"-"),  # figure dash
        (u"−", u"-"),  # minus
        (u"…", u"..."),
        (u"№", u"#"),
        ## upper
        # three-symbols replacements
        (u"Щ", u"Sch"),
        # on russian->english translation only first replacement will be done
        # i.e. Sch
        # but on english->russian translation both variants (Sch and SCH) will play
        (u"Щ", u"SCH"),
        # two-symbol replacements
        (u"Ё", u"Yo"),
        (u"Ё", u"YO"),
        (u"Ж", u"Zh"),
        (u"Ж", u"ZH"),
        (u"Ц", u"Ts"),
        (u"Ц", u"TS"),
        (u"Ч", u"Ch"),
        (u"Ч", u"CH"),
        (u"Ш", u"Sh"),
        (u"Ш", u"SH"),
        (u"Ы", u"Yi"),
        (u"Ы", u"YI"),
        (u"Ю", u"Yu"),
        (u"Ю", u"YU"),
        (u"Я", u"Ya"),
        (u"Я", u"YA"),
        # one-symbol replacements
        (u"А", u"A"),
        (u"Б", u"B"),
        (u"В", u"V"),
        (u"Г", u"G"),
        (u"Д", u"D"),
        (u"Е", u"E"),
        (u"З", u"Z"),
        (u"И", u"I"),
        (u"Й", u"J"),
        (u"К", u"K"),
        (u"Л", u"L"),
        (u"М", u"M"),
        (u"Н", u"N"),
        (u"О", u"O"),
        (u"П", u"P"),
        (u"Р", u"R"),
        (u"С", u"S"),
        (u"Т", u"T"),
        (u"У", u"U"),
        (u"Ф", u"F"),
        (u"Х", u"H"),
        (u"Э", u"E"),
        (u"Ъ", u"`"),
        (u"Ь", u"'"),
        ## lower
        # three-symbols replacements
        (u"щ", u"sch"),
        # two-symbols replacements
        (u"ё", u"yo"),
        (u"ж", u"zh"),
        (u"ц", u"ts"),
        (u"ч", u"ch"),
        (u"ш", u"sh"),
        (u"ы", u"yi"),
        (u"ю", u"yu"),
        (u"я", u"ya"),
        # one-symbol replacements
        (u"а", u"a"),
        (u"б", u"b"),
        (u"в", u"v"),
        (u"г", u"g"),
        (u"д", u"d"),
        (u"е", u"e"),
        (u"з", u"z"),
        (u"и", u"i"),
        (u"й", u"j"),
        (u"к", u"k"),
        (u"л", u"l"),
        (u"м", u"m"),
        (u"н", u"n"),
        (u"о", u"o"),
        (u"п", u"p"),
        (u"р", u"r"),
        (u"с", u"s"),
        (u"т", u"t"),
        (u"у", u"u"),
        (u"ф", u"f"),
        (u"х", u"h"),
        (u"э", u"e"),
        (u"ъ", u"`"),
        (u"ь", u"'"),
        # Make english alphabet full: append english-english pairs
        # for symbols which is not used in russian-english
        # translations. Used in slugify.
        (u"c", u"c"),
        (u"q", u"q"),
        (u"y", u"y"),
        (u"x", u"x"),
        (u"w", u"w"),
        (u"1", u"1"),
        (u"2", u"2"),
        (u"3", u"3"),
        (u"4", u"4"),
        (u"5", u"5"),
        (u"6", u"6"),
        (u"7", u"7"),
        (u"8", u"8"),
        (u"9", u"9"),
        (u"0", u"0"),
        )  #: Translation table

RU_ALPHABET = [x[0] for x in TRANSTABLE] #: Russian alphabet that we can translate
EN_ALPHABET = [x[1] for x in TRANSTABLE] #: English alphabet that we can detransliterate
ALPHABET = RU_ALPHABET + EN_ALPHABET #: Alphabet that we can (de)transliterate


def translify(in_string, strict=True):
    """
    Translify russian text

    @param in_string: input string
    @type in_string: C{unicode}

    @param strict: raise error if transliteration is incomplete.
        (True by default)
    @type strict: C{bool}

    @return: transliterated string
    @rtype: C{str}

    @raise ValueError: when string doesn't transliterate completely.
        Raised only if strict=True
    """
    translit = in_string
    for symb_in, symb_out in TRANSTABLE:
        translit = translit.replace(symb_in, symb_out)

    if strict and any(ord(symb) > 128 for symb in translit):
        raise ValueError("Unicode string doesn't transliterate completely, " + \
                         "is it russian?")

    return translit

def detranslify(in_string):
    """
    Detranslify

    @param in_string: input string
    @type in_string: C{basestring}

    @return: detransliterated string
    @rtype: C{unicode}

    @raise ValueError: if in_string is C{str}, but it isn't ascii
    """
    try:
        russian = six.text_type(in_string)
    except UnicodeDecodeError:
        raise ValueError("We expects if in_string is 8-bit string," + \
                         "then it consists only ASCII chars, but now it doesn't. " + \
                         "Use unicode in this case.")

    for symb_out, symb_in in TRANSTABLE:
        russian = russian.replace(symb_in, symb_out)

    # TODO: выбрать правильный регистр для ь и ъ
    # твердый и мягкий знак в dentranslify всегда будут в верхнем регистре
    # потому что ` и ' не несут информацию о регистре
    return russian

def slugify(in_string):
    """
    Prepare string for slug (i.e. URL or file/dir name)

    @param in_string: input string
    @type in_string: C{basestring}

    @return: slug-string
    @rtype: C{str}

    @raise ValueError: if in_string is C{str}, but it isn't ascii
    """
    try:
        u_in_string = six.text_type(in_string).lower()
    except UnicodeDecodeError:
        raise ValueError("We expects when in_string is str type," + \
                         "it is an ascii, but now it isn't. Use unicode " + \
                         "in this case.")
    # convert & to "and"
    u_in_string = re.sub('\&amp\;|\&', ' and ', u_in_string)
    # replace spaces by hyphen
    u_in_string = re.sub('[-\s]+', '-', u_in_string)
    # remove symbols that not in alphabet
    u_in_string = u''.join([symb for symb in u_in_string if symb in ALPHABET])
    # translify it
    out_string = translify(u_in_string)
    # remove non-alpha
    return re.sub('[^\w\s-]', '', out_string).strip().lower()


def dirify(in_string):
    """
    Alias for L{slugify}
    """
    slugify(in_string)

########NEW FILE########
__FILENAME__ = typo
# -*- coding: utf-8 -*-
# -*- test-case-name: pytils.test.test_typo -*-
"""
Russian typography
"""
import re
import os

def _sub_patterns(patterns, text):
    """
    Apply re.sub to bunch of (pattern, repl)
    """
    for pattern, repl in patterns:
        text = re.sub(pattern, repl, text)
    return text

## ---------- rules -------------
# rules is a regular function,
# name convention is rl_RULENAME
def rl_testrule(x):
    """
    Rule for tests. Do nothing.
    """
    return x

def rl_cleanspaces(x):
    """
    Clean double spaces, trailing spaces, heading spaces,
    spaces before punctuations
    """
    patterns = (
        # arguments for re.sub: pattern and repl
        # удаляем пробел перед знаками препинания
        (r' +([\.,?!\)]+)', r'\1'),
        # добавляем пробел после знака препинания, если только за ним нет другого
        (r'([\.,?!\)]+)([^\.!,?\)]+)', r'\1 \2'),
        # убираем пробел после открывающей скобки
        (r'(\S+)\s*(\()\s*(\S+)', r'\1 (\3'),
    )
    # удаляем двойные, начальные и конечные пробелы
    return os.linesep.join(
        ' '.join(part for part in line.split(' ') if part)
        for line in _sub_patterns(patterns, x).split(os.linesep)
    )

def rl_ellipsis(x):
    """
    Replace three dots to ellipsis
    """

    patterns = (
        # если больше трех точек, то не заменяем на троеточие
        # чтобы не было глупых .....->…..
        (r'([^\.]|^)\.\.\.([^\.]|$)', u'\\1\u2026\\2'),
        # если троеточие в начале строки или возле кавычки --
        # это цитата, пробел между троеточием и первым
        # словом нужно убрать
        (re.compile(u'(^|\\"|\u201c|\xab)\\s*\u2026\\s*([А-Яа-яA-Za-z])', re.UNICODE), u'\\1\u2026\\2'),
        
    )
    return _sub_patterns(patterns, x)

def rl_initials(x):
    """
    Replace space between initials and surname by thin space
    """
    return re.sub(
        re.compile(u'([А-Я])\\.\\s*([А-Я])\\.\\s*([А-Я][а-я]+)', re.UNICODE),
        u'\\1.\\2.\u2009\\3',
        x
    )

def rl_dashes(x):
    """
    Replace dash to long/medium dashes
    """
    patterns = (
        # тире
        (re.compile(u'(^|(.\\s))\\-\\-?(([\\s\u202f].)|$)', re.MULTILINE|re.UNICODE), u'\\1\u2014\\3'),
        # диапазоны между цифрами - en dash
        (re.compile(u'(\\d[\\s\u2009]*)\\-([\\s\u2009]*\d)', re.MULTILINE|re.UNICODE), u'\\1\u2013\\2'),
        # TODO: а что с минусом?
    )
    return _sub_patterns(patterns, x)

def rl_wordglue(x):
    """
    Glue (set nonbreakable space) short words with word before/after
    """
    patterns = (
        # частицы склеиваем с предыдущим словом
        (re.compile(u'(\\s+)(же|ли|ль|бы|б|ж|ка)([\\.,!\\?:;]?\\s+)', re.UNICODE), u'\u202f\\2\\3'),
        # склеиваем короткие слова со следующим словом
        (re.compile(u'\\b([a-zA-ZА-Яа-я]{1,3})(\\s+)', re.UNICODE), u'\\1\u202f'),
        # склеиваем тире с предыдущим словом
        (re.compile(u'(\\s+)([\u2014\\-]+)(\\s+)', re.UNICODE), u'\u202f\\2\\3'),
        # склеиваем два последних слова в абзаце между собой
        # полагается, что абзацы будут передаваться отдельной строкой
        (re.compile(u'([^\\s]+)\\s+([^\\s]+)$', re.UNICODE), u'\\1\u202f\\2'),
    )
    return _sub_patterns(patterns, x)

def rl_marks(x):
    """
    Replace +-, (c), (tm), (r), (p), etc by its typographic eqivalents
    """
    # простые замены, можно без регулярок
    replacements = (
        (u'(r)', u'\u00ae'), # ®
        (u'(R)', u'\u00ae'), # ®
        (u'(p)', u'\u00a7'), # §
        (u'(P)', u'\u00a7'), # §
        (u'(tm)', u'\u2122'), # ™
        (u'(TM)', u'\u2122'), # ™
    )
    patterns = (
        # копирайт ставится до года: © 2008 Юрий Юревич
        (re.compile(u'\\([cCсС]\\)\\s*(\\d+)', re.UNICODE), u'\u00a9\u202f\\1'),
        (r'([^+])(\+\-|\-\+)', u'\\1\u00b1'), # ±
        # градусы с минусом
        (u'\\-(\\d+)[\\s]*([FCС][^\\w])', u'\u2212\\1\202f\u00b0\\2'), # −12 °C, −53 °F
        # градусы без минуса
        (u'(\\d+)[\\s]*([FCС][^\\w])', u'\\1\u202f\u00b0\\2'), # 12 °C, 53 °F
        # ® и ™ приклеиваются к предыдущему слову, без пробела
        (re.compile(u'([A-Za-zА-Яа-я\\!\\?])\\s*(\xae|\u2122)', re.UNICODE), u'\\1\\2'),
        # No5 -> № 5
        (re.compile(u'(\\s)(No|no|NO|\u2116)[\\s\u2009]*(\\d+)', re.UNICODE), u'\\1\u2116\u2009\\3'),
    )

    for what, to in replacements:
        x = x.replace(what, to)
    return _sub_patterns(patterns, x)

def rl_quotes(x):
    """
    Replace quotes by typographic quotes
    """
    
    patterns = (
        # открывающие кавычки ставятся обычно вплотную к слову слева
        # а закрывающие -- вплотную справа
        # открывающие русские кавычки-ёлочки
        (re.compile(r'((?:^|\s))(")((?u))', re.UNICODE), u'\\1\xab\\3'),
        # закрывающие русские кавычки-ёлочки
        (re.compile(r'(\S)(")((?u))', re.UNICODE), u'\\1\xbb\\3'),
        # открывающие кавычки-лапки, вместо одинарных кавычек
        (re.compile(r'((?:^|\s))(\')((?u))', re.UNICODE), u'\\1\u201c\\3'),
        # закрывающие кавычки-лапки
	(re.compile(r'(\S)(\')((?u))', re.UNICODE), u'\\1\u201d\\3'),
    )
    return _sub_patterns(patterns, x)
    

## -------- rules end ----------
STANDARD_RULES = ('cleanspaces', 'ellipsis', 'initials', 'marks', 'dashes', 'wordglue', 'quotes')

def _get_rule_by_name(name):

    rule = globals().get('rl_%s' % name)
    if rule is None:
        raise ValueError("Rule %s is not found" % name)
    if not callable(rule):
        raise ValueError("Rule with name %s is not callable" % name)
    return rule

def _resolve_rule_name(rule_or_name, forced_name=None):
    if isinstance(rule_or_name, str):
        # got name
        name = rule_or_name
        rule = _get_rule_by_name(name)
    elif callable(rule_or_name):
        # got rule
        name = rule_or_name.__name__
        if name.startswith('rl_'):
            # by rule name convention
            # rule is a function with name rl_RULENAME
            name = name[3:]
        rule = rule_or_name
    else:
        raise ValueError(
            "Cannot resolve %r: neither rule, nor name" %
            rule_or_name)
    if forced_name is not None:
        name = forced_name
    return name, rule

class Typography(object):
    """
    Russian typography rules applier
    """
    def __init__(self, *args, **kwargs):
        """
        Typography applier constructor:
        
        possible variations of constructing rules chain:
            rules by it's names:
                Typography('first_rule', 'second_rule')
            rules callables as is:
                Typography(cb_first_rule, cb_second_rule)
            mixed:
                Typography('first_rule', cb_second_rule)
            as list:
                Typography(['first_rule', cb_second_rule])
            as keyword args:
                Typography(rule_name='first_rule',
                           another_rule=cb_second_rule)
            as dict (order of rule execution is not the same):
                Typography({'rule name': 'first_rule',
                            'another_rule': cb_second_rule})
        
        For standard rules it is recommended to use list of rules
        names.
            Typography(['first_rule', 'second_rule'])
        
        For custom rules which are named functions,
        it is recommended to use list of callables:
            Typography([cb_first_rule, cb_second_rule])
        
        For custom rules which are lambda-functions,
        it is recommended to use dict:
            Typography({'rule_name': lambda x: x})
            
        I.e. the recommended usage is:
            Typography(['standard_rule_1', 'standard_rule_2'],
                       [cb_custom_rule1, cb_custom_rule_2],
                       {'custom_lambda_rule': lambda x: x})
        """
        self.rules = {}
        self.rules_names = []
        # first of all, expand args-lists and args-dicts
        expanded_args = []
        expanded_kwargs = {}
        for arg in args:
            if isinstance(arg, (tuple, list)):
                expanded_args += list(arg)
            elif isinstance(arg, dict):
                expanded_kwargs.update(arg)
            elif isinstance(arg, str) or callable(arg):
                expanded_args.append(arg)
            else:
                raise TypeError(
                    "Cannot expand arg %r, must be tuple, list,"\
                    " dict, str or callable, not" %
                    (arg, type(arg).__name__))
        for kw, arg in kwargs.items():
            if isinstance(arg, str) or callable(arg):
                expanded_kwargs[kw] = arg
            else:
                raise TypeError(
                    "Cannot expand kwarg %r, must be str or "\
                    "callable, not" % (arg, type(arg).__name__))
        # next, resolve rule names to callables
        for name, rule in (_resolve_rule_name(a) for a in expanded_args):
            self.rules[name] = rule
            self.rules_names.append(name)
        for name, rule in (_resolve_rule_name(a, k) for k, a in expanded_kwargs.items()):
            self.rules[name] = rule
            self.rules_names.append(name)
        
    def apply_single_rule(self, rulename, text):
        if rulename not in self.rules:
            raise ValueError("Rule %s is not found in active rules" % rulename)
        try:
            res = self.rules[rulename](text)
        except ValueError as e:
            raise ValueError("Rule %s failed to apply: %s" % (rulename, e))
        return res
    
    def apply(self, text):
        for rule in self.rules_names:
            text = self.apply_single_rule(rule, text)
        return text
        
    def __call__(self, text):
        return self.apply(text)

def typography(text):
    t = Typography(STANDARD_RULES)
    return t.apply(text)

if __name__ == '__main__':
    from pytils.test import run_tests_from_module, test_typo
    run_tests_from_module(test_typo, verbosity=2)
    

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
# -*- test-case-name: pytils.test.test_utils -*-
"""
Misc utils for internal use
"""

from pytils.third import six


def check_length(value, length):
    """
    Checks length of value

    @param value: value to check
    @type value: C{str}

    @param length: length checking for
    @type length: C{int}

    @return: None when check successful

    @raise ValueError: check failed
    """
    _length = len(value)
    if _length != length:
        raise ValueError("length must be %d, not %d" % \
                         (length, _length))


def check_positive(value, strict=False):
    """
    Checks if variable is positive

    @param value: value to check
    @type value: C{integer types}, C{float} or C{Decimal}

    @return: None when check successful

    @raise ValueError: check failed
    """
    if not strict and value < 0:
        raise ValueError("Value must be positive or zero, not %s" % str(value))
    if strict and value <= 0:
        raise ValueError("Value must be positive, not %s" % str(value))


def split_values(ustring, sep=u','):
    """
    Splits unicode string with separator C{sep},
    but skips escaped separator.
    
    @param ustring: string to split
    @type ustring: C{unicode}
    
    @param sep: separator (default to u',')
    @type sep: C{unicode}
    
    @return: tuple of splitted elements
    """
    assert isinstance(ustring, six.text_type), "uvalue must be unicode, not %s" % type(ustring)
    # unicode have special mark symbol 0xffff which cannot be used in a regular text,
    # so we use it to mark a place where escaped column was
    ustring_marked = ustring.replace(u'\,', u'\uffff')
    items = tuple([i.strip().replace(u'\uffff', u',') for i in ustring_marked.split(sep)])
    return items

########NEW FILE########
