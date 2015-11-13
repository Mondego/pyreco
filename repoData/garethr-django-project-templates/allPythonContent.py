__FILENAME__ = pastertemplates
from paste.script.templates import Template
from paste.script.templates import var
from random import choice

class DjangoTemplate(Template):

    vars = [
    ]

    use_cheetah = True
    required_templates = []

    def check_vars(self, vars, command):
        if not command.options.no_interactive and \
           not hasattr(command, '_deleted_once'):
            del vars['package']
            command._deleted_once = True
        return super(DjangoTemplate, self).check_vars(vars, command)

def append_secret_key(vars):
    default_key = ''.join([choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])
    vars.append(
        var('secret_key', 'Secret key', default=default_key)
    )
    
def append_db_password(vars):
    default_key = ''.join([choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for i in range(10)])
    vars.append(
        var('db_password', 'DB Password', default=default_key)
)

class DjangoProjectTemplate(DjangoTemplate):
    _template_dir = 'templates/django_project'
    summary = 'Template for a Django project'
    
    def __init__(self, name):
        append_secret_key(self.vars)
        super(DjangoProjectTemplate, self).__init__(name)
        
class DjangoCruiseControlTemplate(Template):
    _template_dir = 'templates/django_cruisecontrol_project'
    summary = 'CruiseControl Template for a Django project'

class NewsAppsProjectTemplate(DjangoTemplate):
    _template_dir = 'templates/newsapps_project'
    summary = 'Template for a News Applications Django project'
    
    vars = [
        var('staging_domain',
            'Parent domain for your staging site.',
            default="beta.example.com"),
        var('production_domain',
            'Parent domain for your production site.',
            default="example.com"),
        var('repository_url',
            'Git repo where your project will be deployed from.',
            default="git@git.example.com:example/project_name.git"),
    ]
    
    def __init__(self, name):
        append_secret_key(self.vars)
        append_db_password(self.vars)
        super(NewsAppsProjectTemplate, self).__init__(name)

########NEW FILE########
__FILENAME__ = local_settings

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

import os
import sys

# we want a few paths on the python path
# first up we add the root above the application so
# we can have absolute paths everywhere
python_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../../'
)
# we have have a local apps directory
apps_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../apps'
)
# we have have a local externals directory
# which saves you having to install a load of
# python modules locally and get into a versioning
# issue
ext_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../../ext'
)

# we add them first to avoid any collisions
sys.path.insert(0, python_path)
sys.path.insert(0, apps_path)
sys.path.insert(0, ext_path)

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
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/(.*)', admin.site.root),
    
    (r'^assets/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT
    }),
)
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

import os
import sys

from django.core.management import execute_manager

# we want a few paths on the python path
# first up we add the root above the application so
# we can have absolute paths everywhere
python_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../../'
)
# we have have a local apps directory
apps_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../apps'
)

# we add them first to avoid any collisions
sys.path.insert(0, python_path)
sys.path.insert(0, apps_path)

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/(.*)', admin.site.root),
    
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT
    }),
)
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

import os
import sys

from django.core.management import execute_manager

# we want a few paths on the python path
# first up we add the root above the application so
# we can have absolute paths everywhere
python_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../../'
)
# we have have a local apps directory
apps_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../apps'
)

# we add them first to avoid any collisions
sys.path.insert(0, python_path)
sys.path.insert(0, apps_path)

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

import os
import sys

from django.core.management import execute_manager

# we want a few paths on the python path
# first up we add the root above the application so
# we can have absolute paths everywhere
python_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../../'
)
# we have have a local apps directory
apps_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../../apps'
)

# we add them first to avoid any collisions
sys.path.insert(0, python_path)
sys.path.insert(0, apps_path)

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
