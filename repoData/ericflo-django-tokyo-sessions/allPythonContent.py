__FILENAME__ = cabinet
# This is where the implementation based directly on Tokyo Cabinet DBs will go.
########NEW FILE########
__FILENAME__ = settings
ROOT_URLCONF = ''
DATABASE_ENGINE = 'sqlite3'
TT_HOST = '127.0.0.1'
TT_PORT = 1978
########NEW FILE########
__FILENAME__ = tests
r"""
>>> from django.conf import settings
>>> from tokyo_sessions.tyrant import SessionStore as TokyoSession

>>> tokyo_session = TokyoSession()
>>> tokyo_session.modified
False
>>> tokyo_session.get('cat')
>>> tokyo_session['cat'] = "dog"
>>> tokyo_session.modified
True
>>> tokyo_session.pop('cat')
'dog'
>>> tokyo_session.pop('some key', 'does not exist')
'does not exist'
>>> tokyo_session.save()
>>> tokyo_session.exists(tokyo_session.session_key)
True
>>> tokyo_session.delete(tokyo_session.session_key)
>>> tokyo_session.exists(tokyo_session.session_key)
False

>>> tokyo_session['foo'] = 'bar'
>>> tokyo_session.save()
>>> tokyo_session.exists(tokyo_session.session_key)
True
>>> prev_key = tokyo_session.session_key
>>> tokyo_session.flush()
>>> tokyo_session.exists(prev_key)
False
>>> tokyo_session.session_key == prev_key
False
>>> tokyo_session.modified, tokyo_session.accessed
(True, True)
>>> tokyo_session['a'], tokyo_session['b'] = 'c', 'd'
>>> tokyo_session.save()
>>> prev_key = tokyo_session.session_key
>>> prev_data = tokyo_session.items()
>>> tokyo_session.cycle_key()
>>> tokyo_session.session_key == prev_key
False
>>> tokyo_session.items() == prev_data
True
"""

if __name__ == '__main__':
    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = tyrant
import pytyrant
import time

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_unicode
from django.contrib.sessions.backends.base import SessionBase, CreateError

TT_HOST = getattr(settings, 'TT_HOST', None)
TT_PORT = getattr(settings, 'TT_PORT', None)

if TT_HOST is None or TT_PORT is None:
    raise ImproperlyConfigured(u'To use django-tokyo-sessions, you must ' + 
        'first set the TT_HOST and TT_PORT settings in your settings.py')
else:
    def get_server():
        return pytyrant.PyTyrant.open(TT_HOST, TT_PORT)

class SessionStore(SessionBase):
    """
    A Tokyo Cabinet-based session store.
    """
    def load(self):
        session_data = get_server().get(self.session_key)
        if session_data is not None:
            expiry, data = int(session_data[:15]), session_data[15:]
            if expiry < time.time():
                return {}
            else:
                return self.decode(force_unicode(data))
        self.create()
        return {}
    
    def create(self):
        while True:
            self.session_key = self._get_new_session_key()
            try:
                self.save(must_create=True)
            except CreateError:
                continue
            self.modified = True
            return
    
    def save(self, must_create=False):
        if must_create and self.exists(self.session_key):
            raise CreateError
        data = self.encode(self._get_session(no_load=must_create))
        encoded = '%15d%s' % (int(time.time()) + self.get_expiry_age(), data)
        get_server()[self.session_key] = encoded
    
    def exists(self, session_key):
        retrieved = get_server().get(session_key)
        if retrieved is None:
            return False
        expiry, data = int(retrieved[:15]), retrieved[15:]
        if expiry < time.time():
            return False
        return True
    
    def delete(self, session_key=None):
        if session_key is None:
            if self._session_key is None:
                return
            session_key = self._session_key
        del get_server()[session_key]
########NEW FILE########
