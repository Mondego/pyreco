__FILENAME__ = mini_django
'''
Run this with $ python ./micro_django.py and go to http://localhost:8000/Foo
'''

import os, sys
from django.conf.urls.defaults import patterns
from django.template.response import TemplateResponse

# this module
me = os.path.splitext(os.path.split(__file__)[1])[0]
# helper function to locate this dir
here = lambda x: os.path.join(os.path.abspath(os.path.dirname(__file__)), x)

# SETTINGS
DEBUG=TEMPLATE_DEBUG=True
ROOT_URLCONF = me
DATABASES = { 'default': {} } #required regardless of actual usage
TEMPLATE_DIRS = (here('.'), )

# VIEW
def index(request, name):
    return TemplateResponse(request, 'index.html', {'name': name})

# URLS
urlpatterns = patterns('', (r'^(?P<name>\w+)?$', index))

if __name__=='__main__':
    # set the ENV
    os.environ['DJANGO_SETTINGS_MODULE'] = me
    sys.path += (here('.'),)
    # run the development server
    from django.core import management
    management.execute_from_command_line() 

########NEW FILE########
__FILENAME__ = pico_django
from django.http import HttpResponse
from django.conf.urls import url

DEBUG=True
ROOT_URLCONF = 'pico_django'
DATABASES = { 'default': {} }

def index(request, name):
    return HttpResponse('Hello {name}!'.format(name=(name or 'World')))

urlpatterns = [
        url(r'^(?P<name>\w+)?$', index)
        ]

SECRET_KEY="notsosecret"

# run with djagno dev server
# $ PYTHONPATH=. django-admin.py runserver 0.0.0.0:8000 --settings=pico_django

# for example run with uwsgi
# $ uwsgi -s 127.0.0.1:3031 -M --pythonpath=/path/to/this/dir --env DJANGO_SETTINGS_MODULE=pico_django -w "django.core.handlers.wsgi:WSGIHandler()"

########NEW FILE########
