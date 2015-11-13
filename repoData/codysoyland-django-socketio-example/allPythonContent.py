__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = run_example
#!/usr/bin/env python

PORT = 9000

import os

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

from socketio import SocketIOServer

if __name__ == '__main__':
    print 'Listening on port %s and on port 843 (flash policy server)' % PORT
    SocketIOServer(('', PORT), application, resource="socket.io").serve_forever()

########NEW FILE########
__FILENAME__ = settings
import os

BASE_PATH = os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True
MEDIA_ROOT = ''
MEDIA_URL = ''
ADMIN_MEDIA_PREFIX = '/media/'
SECRET_KEY = 'aysxjo#0vhu3=%(49r_3xri@hv3y8tk_2s4jnhowp-9u7eo+tl'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    os.path.join(BASE_PATH, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
)


TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request',
)



########NEW FILE########
__FILENAME__ = urls
import os
from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns('',
    (r'^$', 'django.views.generic.simple.direct_to_template', {'template': 'chat.html'}),
    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
                {'document_root': os.path.join(settings.BASE_PATH, 'media')}),
)

urlpatterns += patterns('views',
    (r'^socket\.io', 'socketio'),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse

buffer = []

def socketio(request):
    socketio = request.environ['socketio']
    if socketio.on_connect():
        socketio.send({'buffer': buffer})
        socketio.broadcast({'announcement': socketio.session.session_id + ' connected'})

    while True:
        message = socketio.recv()

        if len(message) == 1:
            message = message[0]
            message = {'message': [socketio.session.session_id, message]}
            buffer.append(message)
            if len(buffer) > 15:
                del buffer[0]
            socketio.broadcast(message)
        else:
            if not socketio.connected():
                socketio.broadcast({'announcement': socketio.session.session_id + ' disconnected'})
                break

    return HttpResponse()

########NEW FILE########
