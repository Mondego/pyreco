__FILENAME__ = api
from slugify import slugify
import gevent
import json
import logging
import os
import pwd
import subprocess

from ajenti.api import *
from ajenti.profiler import profile_start, profile_end


class Config (object):
    def __init__(self, j):
        self.websites = [Website(_) for _ in j['websites']]

    @staticmethod
    def create():
        return Config({
            'websites': []
        })

    def save(self):
        return {
            'websites': [_.save() for _ in self.websites],
        }


class Website (object):
    def __init__(self, j):
        self.name = j['name']
        self.owner = j.get('owner', 'root')
        self.ssl_cert_path = j.get('ssl_cert_path', '')
        self.ssl_key_path = j.get('ssl_key_path', '')
        self.domains = [WebsiteDomain(_) for _ in j['domains']]
        self.ports = [WebsitePort(_) for _ in j.get('ports', [])]
        self.locations = [WebsiteLocation(self, _) for _ in j.get('locations', [])]
        self.enabled = j.get('enabled', True)
        self.maintenance_mode = j.get('maintenance_mode', True)
        self.root = j.get('root', '/srv/new-website')
        self.extension_configs = j.get('extensions', {})
        self.custom_conf = j.get('custom_conf', '')
        self.slug = j.get('slug', slugify(self.name))

    @staticmethod
    def create(name):
        return Website({
            'name': name,
            'domains': [],
            'ports': [WebsitePort.create(80).save()],
        })

    def save(self):
        return {
            'name': self.name,
            'owner': self.owner,
            'domains': [_.save() for _ in self.domains],
            'ports': [_.save() for _ in self.ports],
            'locations': [_.save() for _ in self.locations],
            'enabled': self.enabled,
            'maintenance_mode': self.maintenance_mode,
            'root': self.root,
            'extensions': self.extension_configs,
            'custom_conf': self.custom_conf,
            'ssl_cert_path': self.ssl_cert_path,
            'ssl_key_path': self.ssl_key_path,
        }


class WebsiteDomain (object):
    def __init__(self, j):
        self.domain = j['domain']

    @staticmethod
    def create(domain):
        return WebsiteDomain({
            'domain': domain,
        })

    def save(self):
        return {
            'domain': self.domain,
        }


class WebsitePort (object):
    def __init__(self, j):
        self.host = j.get('host', '*')
        self.port = j['port']
        self.ssl = j.get('ssl', False)
        self.spdy = j.get('spdy', False)
        self.default = j.get('default', False)

    @staticmethod
    def create(port):
        return WebsitePort({
            'port': port,
        })

    def save(self):
        return {
            'host': self.host,
            'port': self.port,
            'ssl': self.ssl,
            'spdy': self.spdy,
            'default': self.default,
        }


class WebsiteLocation (object):
    def __init__(self, website, j):
        self.pattern = j['pattern']
        self.match = j['match']
        self.backend = Backend(self, j['backend'])
        self.custom_conf = j.get('custom_conf', '')
        self.custom_conf_override = j.get('custom_conf_override', False)
        self.path = j.get('path', '')
        self.path_append_pattern = j.get('path_append_pattern', True)
        self.website = website

    @staticmethod
    def create(website, template=None):
        templates = {
            'php-fcgi': {
                'pattern': r'[^/]\.php(/|$)',
                'path_append_pattern': False,
                'match': 'regex',
                'backend': Backend.create(None).save(),
            },
        }

        default_template = {
            'pattern': '/',
            'path_append_pattern': False,
            'match': 'exact',
            'backend': Backend.create(None).save(),
        }

        return WebsiteLocation(website, templates[template] if template in templates else default_template)

    def save(self):
        return {
            'pattern': self.pattern,
            'match': self.match,
            'backend': self.backend.save(),
            'custom_conf': self.custom_conf,
            'custom_conf_override': self.custom_conf_override,
            'path': self.path,
            'path_append_pattern': self.path_append_pattern,
        }


class Backend (object):
    def __init__(self, location, j):
        self.type = j['type']
        self.params = j.get('params', {})
        self.location = location

    @staticmethod
    def create(l):
        return Backend(l, {
            'type': 'static',
            'params': {}
        })

    @property
    def id(self):
        return '%s-%s-%s' % (self.location.website.slug, self.type, self.location.website.locations.index(self.location))

    @property
    def typename(self):
        for cls in ApplicationGatewayComponent.get_classes():
            if cls.id == self.type:
                return cls.title

    def save(self):
        return {
            'type': self.type,
            'params': self.params,
        }


class SanityCheck (object):
    def __init__(self):
        self.name = ''
        self.type = ''
        self.message = ''

    def check(self):
        return False


@interface
class Component (object):
    def create_configuration(self, config):
        pass

    def apply_configuration(self):
        pass

    def get_checks(self):
        return []


@interface
class WebserverComponent (Component):
    pass


@interface
class ApplicationGatewayComponent (Component):
    id = None
    title = None


@interface
class MiscComponent (Component):
    pass


@interface
@persistent
@rootcontext
class Restartable (BasePlugin):
    def init(self):
        self.scheduled = False

    def restart(self):
        pass

    def schedule(self):
        logging.debug('%s scheduled' % self.classname)
        self.scheduled = True

    def process(self):
        if self.scheduled:
            logging.debug('%s restarting' % self.classname)
            self.scheduled = False
            self.restart()
            logging.debug('%s restarted' % self.classname)


@plugin
@persistent
@rootcontext
class VHManager (object):
    config_path = '/etc/ajenti/vh.json'
    www_user = 'www-data'

    def init(self):
        try:
            pwd.getpwnam(self.www_user)
        except KeyError:
            subprocess.call(['useradd', self.www_user])
            subprocess.call(['groupadd', self.www_user])

        self.reload()
        self.components = ApplicationGatewayComponent.get_all()
        self.components += MiscComponent.get_all()
        self.restartables = [x.get() for x in Restartable.get_classes()]  # get() ensures rootcontext
        self.webserver = WebserverComponent.get()
        self.checks = []

    def reload(self):
        if os.path.exists(self.config_path):
            self.is_configured = True
            self.config = Config(json.load(open(self.config_path)))
        else:
            self.is_configured = False
            self.config = Config.create()

    def __handle_exceptions(self, greenlets):
        for g in greenlets:
            if g.exception:
                raise g.exception

    def update_configuration(self):
        profile_start('V: creating configuration')
        greenlets = [gevent.spawn(c.create_configuration, self.config) for c in self.components]
        gevent.joinall(greenlets)
        self.__handle_exceptions(greenlets)
        self.webserver.create_configuration(self.config)
        profile_end()

        profile_start('V: applying configuration')
        greenlets = [gevent.spawn(c.apply_configuration) for c in self.components]
        gevent.joinall(greenlets)
        self.__handle_exceptions(greenlets)
        self.webserver.apply_configuration()
        profile_end()

    def restart_services(self):
        profile_start('V: restarting services')
        greenlets = [gevent.spawn(r.process) for r in self.restartables]
        gevent.joinall(greenlets)
        self.__handle_exceptions(greenlets)
        profile_end()

    def run_checks(self):
        self.checks = []
        for c in self.components:
            self.checks += c.get_checks()
        self.checks += self.webserver.get_checks()

        profile_start('V: running checks')

        def run_check(c):
            c.satisfied = c.check()

        greenlets = [gevent.spawn(run_check, c) for c in self.checks]
        gevent.joinall(greenlets)
        self.__handle_exceptions(greenlets)
        profile_end()

    def save(self):
        j = json.dumps(self.config.save(), indent=4)
        open(self.config_path, 'w').write(j)
        self.is_configured = True

########NEW FILE########
__FILENAME__ = extensions
from ajenti.api import *
from ajenti.ui import UIElement


@interface
class BaseExtension (UIElement):
    typeid = 'vh:extension'
    default_config = None

    def __init__(self, ui, website, config=None):
        UIElement.__init__(self, ui)
        self.website = website
        self.config = config or self.default_config.copy()

    @staticmethod
    def selftest():
        pass

    def update(self):
        pass

    def on_destroy(self):
        pass

########NEW FILE########
__FILENAME__ = gate_fcgi
from ajenti.api import plugin
from ajenti.plugins.vh.api import ApplicationGatewayComponent


@plugin
class FCGIPass (ApplicationGatewayComponent):
    id = 'fcgi'
    title = _('Custom FCGI')
########NEW FILE########
__FILENAME__ = gate_proxy
from ajenti.api import plugin
from ajenti.plugins.vh.api import ApplicationGatewayComponent


@plugin
class ProxyPass (ApplicationGatewayComponent):
    id = 'proxy'
    title = _('Reverse proxy')
########NEW FILE########
__FILENAME__ = gate_static
from ajenti.api import plugin
from ajenti.plugins.vh.api import ApplicationGatewayComponent


@plugin
class Static (ApplicationGatewayComponent):
    id = 'static'
    title = _('Static files')
########NEW FILE########
__FILENAME__ = ipc
import json
import os

from ajenti.api import *
from ajenti.ipc import IPCHandler
from ajenti.plugins import manager

from api import VHManager


@plugin
class VIPC (IPCHandler):
    def init(self):
        self.manager = VHManager.get()

    def get_name(self):
        return 'v'

    def handle(self, args):
        command = args[0]
        if command in ['import', 'export']:
            config = json.load(open(self.manager.config_path))

            if command == 'export':
                if len(args) == 1:
                    raise Exception('Usage: v export <website name>')
                matching = [
                    x for x in config['websites']
                    if x['name'] == args[1]
                ]
                if len(matching) == 0:
                    raise Exception('Website not found')
                return json.dumps(matching[0], indent=4)

            if command == 'import':
                if len(args) == 1:
                    raise Exception('Usage: v import <website config file>')
                path = args[1]
                if not os.path.exists(path):
                    raise Exception('Config does not exist')
                website_config = json.load(open(path))
                websites = [
                    x for x in config['websites']
                    if x['name'] != website_config['name']
                ]
                websites.append(website_config)
                config['websites'] = websites
                with open(self.manager.config_path, 'w') as f:
                    json.dump(config, f)
                self.manager.reload()
                return 'OK'

        if command == 'check':
            self.manager.run_checks()
            for c in self.manager.checks:
                if not c.satisfied:
                    raise Exception('Check failed: %s - %s: %s' % (c.type, c.name, c.message))
            return 'OK'

        if command == 'maintenance':
            if len(args) != 3:
                raise Exception('Usage: v maintenance <website name> on|off')
            for ws in self.manager.config.websites:
                if ws.name == args[1]:
                    ws.maintenance_mode = args[2] == 'on'
                    break
            else:
                raise Exception('Website not found')
            self.manager.save()
            self.manager.update_configuration()
            self.manager.restart_services()
            return 'OK'

        if command == 'apply':
            self.manager.save()
            self.manager.update_configuration()
            self.manager.restart_services()
            return 'OK'

########NEW FILE########
__FILENAME__ = main
import gevent
import logging
import os
import subprocess
from slugify import slugify

from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin, intent
from ajenti.ui import on
from ajenti.ui.binder import Binder

from api import VHManager, Website, WebsiteDomain, WebsitePort, WebsiteLocation, ApplicationGatewayComponent
from extensions import BaseExtension


@plugin
class WebsitesPlugin (SectionPlugin):
    def init(self):
        self.title = _('Websites')
        self.icon = 'globe'
        self.category = 'Web'

        self.manager = VHManager.get()

        if not self.manager.is_configured:
            from ajenti.plugins.vh import destroyed_configs
            self.append(self.ui.inflate('vh:not-configured'))
            self.find('destroyed-configs').text = ', '.join(destroyed_configs)
        else:
            self.post_init()

    @on('initial-enable', 'click')
    def on_initial_enable(self):
        self.post_init()
        self.manager.save()
        self.refresh()

    def post_init(self):
        self.empty()
        self.append(self.ui.inflate('vh:main'))

        self.binder = Binder(None, self)

        def post_ws_bind(object, collection, item, ui):
            def manage():
                self.context.launch('v:manage-website', website=item)
            ui.find('manage').on('click', manage)

        self.find('websites').post_item_bind = post_ws_bind
        self.find('websites').filter = lambda ws: self.context.session.identity in ['root', ws.owner]

        self.binder.setup(self.manager)

    @on('new-website', 'click')
    def on_new_website(self):
        self.binder.update()
        name = self.find('new-website-name').value
        self.find('new-website-name').value = ''
        if not name:
            name = '_'

        slug = slugify(name)
        slugs = [x.slug for x in self.manager.config.websites]
        while slug in slugs:
            slug += '_'

        w = Website.create(name)
        w.slug = slug
        w.owner = self.context.session.identity
        self.manager.config.websites.append(w)
        self.manager.save()
        self.binder.populate()

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        if self.manager.is_configured:
            self.manager.config.websites = sorted(self.manager.config.websites, key=lambda x: x.name)
            self.binder.setup().populate()

    @on('recheck', 'click')
    def on_recheck(self):
        self.binder.update()
        self.context.endpoint.send_progress(_('Testing configuration'))
        try:
            self.manager.run_checks()
        finally:
            self.context.endpoint.send_progress(None)
            self.refresh()

    @on('save', 'click')
    def save(self):
        self.context.endpoint.send_progress(_('Saving changes'))
        self.binder.update()
        self.manager.save()
        self.context.endpoint.send_progress(_('Applying changes'))
        self.manager.update_configuration()
        self.context.endpoint.send_progress(_('Restarting web services'))
        self.manager.restart_services()
        gevent.spawn(self.on_recheck)
        self.refresh()
        self.context.notify('info', _('Saved'))


@plugin
class WebsiteEditorPlugin (SectionPlugin):
    def init(self):
        self.title = 'Website editor'
        self.icon = 'globe'
        self.category = 'Web'
        self.hidden = True

        self.manager = VHManager.get()
        self.binder = Binder(None, self)

        self.append(self.ui.inflate('vh:main-website'))
        self.find('domains').new_item = lambda c: WebsiteDomain.create('example.com')
        self.find('ports').new_item = lambda c: WebsitePort.create(80)

        def post_location_bind(object, collection, item, ui):
            ui.find('backend-params').empty()
            ui.find('backend-params').append(self.ui.inflate('vh:main-backend-params-%s' % item.backend.type))
            item.backend.__binder = Binder(item.backend, ui.find('backend-params'))
            item.backend.__binder.populate()

        def post_location_update(object, collection, item, ui):
            item.backend.__binder.update()

        self.find('locations').post_item_bind = post_location_bind
        self.find('locations').post_item_update = post_location_update

        self.find('create-location-type').labels = []
        self.find('create-location-type').values = []
        for g in sorted(ApplicationGatewayComponent.get_classes(), key=lambda x: x.title):
            self.find('create-location-type').labels.append(g.title)
            self.find('create-location-type').values.append(g.id)

    @intent('v:manage-website')
    def on_launch(self, website=None):
        self.activate()
        self.website = website
        self.binder.setup(self.website)
        self.binder.populate()

        for ext in BaseExtension.get_classes():
            ext.selftest()

        extensions = BaseExtension.get_classes()

        def create_location():
            self.binder.update()
            t = self.find('create-location-type').value
            l = WebsiteLocation.create(self.website, template=t)
            l.backend.type = t
            self.website.locations.append(l)
            self.refresh()
        self.find('create-location').on('click', create_location)

        # Extensions
        for tab in list(self.find('tabs').children):
            if hasattr(tab, '-is-extension'):
                tab.delete()

        self.website.extensions = []
        for ext in extensions:
            ext = ext.new(self.ui, self.website, config=self.website.extension_configs.get(ext.classname, None))
            ext._ui_container = self.ui.create('tab', children=[ext], title=ext.name)
            setattr(ext._ui_container, '-is-extension', True)
            self.website.extensions.append(ext)
            self.find('tabs').append(ext._ui_container)

        # Root creator
        self.find('root-not-created').visible = not os.path.exists(self.website.root)

        def create_root():
            self.binder.update()
            if not os.path.exists(self.website.root):
                os.makedirs(self.website.root)
            subprocess.call(['chown', 'www-data', self.website.root])
            self.save()

        self.find('create-root-directory').on('click', create_root)
        self.find('set-path').on('click', self.save)

        # Downloader

        def download():
            url = self.find('download-url').value
            self.save()
            tmppath = '/tmp/ajenti-v-download'
            script = 'wget "%s" -O "%s" ' % (url, tmppath)
            if url.lower().endswith('.tar.gz') or url.lower().endswith('.tgz'):
                script += '&& tar xf "%s" -C "%s"' % (tmppath, self.website.root)
            elif url.lower().endswith('.zip'):
                script += '&& unzip "%s" -d "%s"' % (tmppath, self.website.root)

            script += ' && chown www-data -R "%s"' % self.website.root
            script += ' && find "%s" -type d -exec chmod 775 {} ";"' % self.website.root
            script += ' && find "%s" -type f -exec chmod 644 {} ";"' % self.website.root

            def callback():
                self.save()
                self.activate()
                if os.path.exists(tmppath):
                    os.unlink(tmppath)
                self.context.notify('info', _('Download complete'))

            self.context.launch('terminal', command=script, callback=callback)

        self.find('download').on('click', download)

    @on('go-back', 'click')
    def on_go_back(self):
        WebsitesPlugin.get().activate()

    @on('destroy', 'click')
    def on_destroy(self):
        for ext in self.website.extensions:
            try:
                ext.on_destroy()
            except Exception, e:
                logging.error(str(e))
        self.manager.config.websites.remove(self.website)
        self.save()
        self.on_go_back()

    def refresh(self):
        self.binder.unpopulate().populate()

    def run_checks(self):
        self.context.endpoint.send_progress(_('Testing configuration'))
        try:
            self.manager.run_checks()
        finally:
            self.context.endpoint.send_progress(None)
            self.refresh()

    @on('save', 'click')
    def save(self):
        self.binder.update()

        for ext in self.website.extensions:
            ext.update()
            self.website.extension_configs[ext.classname] = ext.config

        self.context.endpoint.send_progress(_('Saving changes'))
        self.manager.save()
        self.context.endpoint.send_progress(_('Applying changes'))
        self.manager.update_configuration()
        self.context.endpoint.send_progress(_('Restarting web services'))
        self.manager.restart_services()
        gevent.spawn(self.run_checks)
        self.refresh()
        self.context.notify('info', _('Saved'))

########NEW FILE########
__FILENAME__ = processes
import gevent
import os
import subprocess

from ajenti.api import *
from ajenti.api.helpers import subprocess_call_background
from ajenti.ui.binder import Binder
from ajenti.util import platform_select

from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.supervisor.client import SupervisorServiceManager
from ajenti.plugins.vh.api import MiscComponent, Restartable, SanityCheck
from ajenti.plugins.vh.extensions import BaseExtension

from reconfigure.configs import SupervisorConfig
from reconfigure.items.supervisor import ProgramData


class WebsiteProcess (object):
    def __init__(self, j={}):
        self.name = j.get('name', 'service')
        self.command = j.get('command', '')
        self.directory = j.get('directory', '')
        self.user = j.get('user', '')
        self.environment = j.get('environment', '')

    def save(self):
        return {
            'name': self.name,
            'command': self.command,
            'directory': self.directory,
            'user': self.user,
            'environment': self.environment,
        }


class ProcessTest (SanityCheck):
    def __init__(self, pid):
        SanityCheck.__init__(self)
        self.pid = pid
        self.type = _('Process')
        self.name = pid

    def check(self):
        s = SupervisorServiceManager.get().get_one(self.pid)
        if s:
            self.message = s.status
        return s and s.running


@plugin
class ProcessesExtension (BaseExtension):
    default_config = {
        'processes': [],
    }
    name = _('Processes')

    def init(self):
        self.append(self.ui.inflate('vh:ext-processes'))
        self.binder = Binder(self, self)
        self.find('processes').new_item = lambda c: WebsiteProcess()
        self.refresh()

    def refresh(self):
        self.processes = [WebsiteProcess(x) for x in self.config['processes']]
        self.binder.setup().populate()

    def update(self):
        self.binder.update()
        self.config['processes'] = [x.save() for x in self.processes]


@plugin
class Processes (MiscComponent):
    COMMENT = 'Autogenerated Ajenti V process'

    def init(self):
        self.checks = []
        
    def create_configuration(self, config):
        self.checks = []

        sup = SupervisorConfig(path=platform_select(
            debian='/etc/supervisor/supervisord.conf',
            centos='/etc/supervisord.conf',
        ))
        sup.load()
        for p in sup.tree.programs:
            if p.comment and p.comment == self.COMMENT:
                sup.tree.programs.remove(p)

        for website in config.websites:
            if website.enabled:
                cfg = website.extension_configs.get(ProcessesExtension.classname) or {}
                for process in cfg.get('processes', []):
                    p = ProgramData()
                    p.comment = self.COMMENT
                    p.name = '%s-%s' % (website.slug, process['name'])
                    p.command = process['command']
                    p.environment = process['environment']
                    p.directory = process['directory'] or website.root
                    p.user = process['user'] or 'www-data'
                    sup.tree.programs.append(p)
                    self.checks.append(ProcessTest(p.name))

        sup.save()

    def apply_configuration(self):
        SupervisorRestartable.get().schedule()

    def get_checks(self):
        return self.checks


@plugin
class SupervisorRestartable (Restartable):
    def restart(self):
        s = ServiceMultiplexor.get().get_one(platform_select(
            debian='supervisor',
            default='supervisord',
        ))
        if not s.running:
            s.start()
        else:
            subprocess_call_background(['supervisorctl', 'reload'])

        # Await restart
        retries = 10
        while retries:
            retries -= 1
            if subprocess_call_background(['supervisorctl', 'status']) == 0:
                break
            gevent.sleep(1)

########NEW FILE########
__FILENAME__ = slugify
import re
import unicodedata

_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_hyphenate_re = re.compile(r'[-\s]+')


def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    
    From Django's "django/template/defaultfilters.py".
    """
    import unicodedata
    if not isinstance(value, unicode):
        value = unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(_slugify_strip_re.sub('', value).strip().lower())
    return _slugify_hyphenate_re.sub('-', value)
########NEW FILE########
__FILENAME__ = gunicorn
import os
import shutil

from ajenti.api import *
from ajenti.plugins.supervisor.client import SupervisorServiceManager
from ajenti.plugins.vh.api import ApplicationGatewayComponent, SanityCheck
from ajenti.plugins.vh.processes import SupervisorRestartable
from ajenti.util import platform_select

from reconfigure.configs import SupervisorConfig
from reconfigure.items.supervisor import ProgramData


TEMPLATE_PROCESS = """
import multiprocessing

bind = 'unix:/var/run/gunicorn-%(id)s.sock'
chdir = '%(root)s'
workers = %(workers)s or (multiprocessing.cpu_count() * 2 + 1)
"""


class GUnicornServerTest (SanityCheck):
    def __init__(self, backend):
        SanityCheck.__init__(self)
        self.backend = backend
        self.type = _('GUnicorn service')
        self.name = backend.id

    def check(self):
        s = SupervisorServiceManager.get().get_one(self.backend.id)
        if s:
            self.message = s.status
        return s and s.running


@plugin
class Gunicorn (ApplicationGatewayComponent):
    id = 'python-wsgi'
    title = 'Python WSGI'

    def init(self):
        self.config_dir = '/etc/gunicorn.ajenti.d/'
        self.checks = []

    def __generate_website(self, website):
        for location in website.locations:
            if location.backend.type == 'python-wsgi':
                c = TEMPLATE_PROCESS % {
                    'id': location.backend.id,
                    'root': location.path or website.root,
                    'workers': location.backend.params.get('workers', None),
                }
                open(os.path.join(self.config_dir, location.backend.id), 'w').write(c)

    def create_configuration(self, config):
        self.checks = []
        if os.path.exists(self.config_dir):
            shutil.rmtree(self.config_dir)
        os.mkdir(self.config_dir)

        for website in config.websites:
            if website.enabled:
                self.__generate_website(website)

        sup = SupervisorConfig(path=platform_select(
            debian='/etc/supervisor/supervisord.conf',
            centos='/etc/supervisord.conf',
        ))
        sup.load()

        COMMENT = 'Generated by Ajenti-V'

        for p in sup.tree.programs:
            if p.comment == COMMENT:
                sup.tree.programs.remove(p)

        for website in config.websites:
            if website.enabled:
                for location in website.locations:
                    if location.backend.type == 'python-wsgi':
                        self.checks.append(GUnicornServerTest(location.backend))
                        self.__generate_website(website)
                        p = ProgramData()
                        p.name = location.backend.id
                        p.comment = COMMENT
                        p.command = 'gunicorn -c %s/%s "%s"' % (self.config_dir, location.backend.id, location.backend.params['module'])
                        p.directory = location.path or website.root
                        virtualenv = location.backend.params.get('venv', None)
                        if virtualenv:
                            p.environment = 'PATH="%s"' % os.path.join(virtualenv, 'bin')
                            p.command = os.path.join(virtualenv, 'bin') + '/' + p.command

                        sup.tree.programs.append(p)

        sup.save()

    def apply_configuration(self):
        SupervisorRestartable.get().schedule()

    def get_checks(self):
        return self.checks

########NEW FILE########
__FILENAME__ = api
import grp
import json
import os
import pwd
import shutil
import subprocess

import ajenti
from ajenti.api import *
from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.vh.api import Restartable
from ajenti.plugins.vh.processes import SupervisorRestartable
from ajenti.util import platform_select

import templates


class Config (object):
    def __init__(self, j):
        self.mailboxes = [Mailbox(_) for _ in j.get('mailboxes', [])]
        self.forwarding_mailboxes = [
            ForwardingMailbox(_)
            for _ in j.get('forwarding_mailboxes', [])
        ]
        self.mailroot = j.get('mailroot', '/var/vmail')
        self.custom_mta_config = j.get('custom_mta_config', '')
        self.custom_mta_acl = j.get('custom_mta_acl', '')
        self.custom_mta_routers = j.get('custom_mta_routers', '')
        self.custom_mta_transports = j.get('custom_mta_transports', '')
        self.dkim_enable = j.get('dkim_enable', False)
        self.dkim_selector = j.get('dkim_selector', 'x')
        self.dkim_private_key = j.get('dkim_private_key', '')
        self.tls_enable = j.get('tls_enable', False)
        self.tls_certificate = j.get('tls_certificate', '')
        self.tls_privatekey = j.get('tls_privatekey', '')

    @staticmethod
    def create():
        return Config({})

    def save(self):
        return {
            'mailboxes': [_.save() for _ in self.mailboxes],
            'forwarding_mailboxes': [
                _.save()
                for _ in self.forwarding_mailboxes
            ],
            'custom_mta_acl': self.custom_mta_acl,
            'custom_mta_routers': self.custom_mta_routers,
            'custom_mta_config': self.custom_mta_config,
            'custom_mta_transports': self.custom_mta_transports,
            'dkim_enable': self.dkim_enable,
            'dkim_selector': self.dkim_selector,
            'dkim_private_key': self.dkim_private_key,
            'tls_enable': self.tls_enable,
            'tls_certificate': self.tls_certificate,
            'tls_privatekey': self.tls_privatekey,
        }


class Mailbox (object):
    def __init__(self, j):
        self.local = j.get('local', 'someone')
        self.domain = j.get('domain', 'example.com')
        self.password = j.get('password', 'example.com')
        self.owner = j.get('owner', 'root')

    @property
    def name(self):
        return '%s@%s' % (self.local, self.domain)

    @staticmethod
    def create():
        return Mailbox({})

    def save(self):
        return {
            'local': self.local,
            'domain': self.domain,
            'password': self.password,
            'owner': self.owner,
        }


class ForwardingMailbox (object):
    def __init__(self, j):
        self.targets = [ForwardingTarget(_) for _ in j.get('targets', [])]
        self.local = j.get('local', 'someone')
        self.domain = j.get('domain', 'example.com')
        self.owner = j.get('owner', 'root')

    @property
    def name(self):
        return '%s@%s' % (self.local, self.domain)

    @staticmethod
    def create():
        return ForwardingMailbox({})

    def save(self):
        return {
            'targets': [_.save() for _ in self.targets],
            'local': self.local,
            'domain': self.domain,
            'owner': self.owner,
        }


class ForwardingTarget (object):
    def __init__(self, j):
        self.email = j.get('email', 'someone@example.com')

    @staticmethod
    def create():
        return ForwardingTarget({})

    def save(self):
        return {
            'email': self.email,
        }


@interface
class MailBackend (object):
    pass


@plugin
class MailEximCourierBackend (MailBackend):
    def init(self):
        self.exim_cfg_path = platform_select(
            debian='/etc/exim4/exim4.conf',
            centos='/etc/exim/exim.conf',
            arch='/etc/mail/exim.conf',
        )

        for d in ['/etc/courier', '/var/run/courier']:
            if not os.path.exists(d):
                os.makedirs(d)

        self.courier_authdaemonrc = platform_select(
            debian='/etc/courier/authdaemonrc',
            centos='/etc/authlib/authdaemonrc',
            arch='/etc/authlib/authdaemonrc',
        )
        self.courier_imaprc = platform_select(
            debian='/etc/courier/imapd',
            centos='/usr/lib/courier-imap/etc/imapd',
            arch='/etc/courier-imap/imapd',
        )
        self.courier_imapsrc = platform_select(
            debian='/etc/courier/imapd-ssl',
            centos='/usr/lib/courier-imap/etc/imapd-ssl',
            arch='/etc/courier-imap/imapd-ssl',
        )
        self.courier_userdb = platform_select(
            debian='/etc/courier/userdb',
            centos='/etc/authlib/userdb',
            arch='/etc/authlib/userdb',
        )
        self.courier_authsocket = platform_select(
            debian='/var/run/courier/authdaemon/socket',
            centos='/var/spool/authdaemon/socket',
            arch='/var/run/authdaemon/socket',
        )

        self.maildomains = '/etc/exim.domains'
        self.mailforward = '/etc/exim.forward'
        self.mailuid = pwd.getpwnam('mail').pw_uid
        self.mailgid = grp.getgrnam('mail').gr_gid

    def configure(self, config):
        try:
            mailname = open('/etc/mailname').read().strip()
        except:
            mailname = 'localhost'

        domains = [x.domain for x in config.mailboxes]
        domains += [x.domain for x in config.forwarding_mailboxes]
        domains = list(set(domains))
        if not mailname in domains:
            domains.append(mailname)
        if not 'localhost' in domains:
            domains.append('localhost')

        pem_path = os.path.join('/etc/courier/mail.pem')
        pem = ''
        if os.path.exists(config.tls_certificate):
            pem += open(config.tls_certificate).read()
        if os.path.exists(config.tls_privatekey):
            pem += open(config.tls_privatekey).read()
        with open(pem_path, 'w') as f:
            f.write(pem)

        open(self.exim_cfg_path, 'w').write(templates.EXIM_CONFIG % {
            'local_domains': ' : '.join(domains),
            'mailname': mailname,
            'maildomains': self.maildomains,
            'mailforward': self.mailforward,
            'mailroot': config.mailroot,
            'custom_mta_acl': config.custom_mta_acl,
            'custom_mta_routers': config.custom_mta_routers,
            'custom_mta_config': config.custom_mta_config,
            'custom_mta_transports': config.custom_mta_transports,
            'dkim_enable': 'DKIM_ENABLE=1' if config.dkim_enable else '',
            'dkim_selector': config.dkim_selector,
            'dkim_private_key': config.dkim_private_key,
            'tls_enable': 'TLS_ENABLE=1' if config.tls_enable else '',
            'tls_certificate': config.tls_certificate,
            'tls_privatekey': config.tls_privatekey,
            'courier_authsocket': self.courier_authsocket,
        })
        open(self.courier_authdaemonrc, 'w').write(templates.COURIER_AUTHRC % {
            'courier_authsocket': self.courier_authsocket,
        })
        open(self.courier_imaprc, 'w').write(templates.COURIER_IMAP % {
        })
        open(self.courier_imapsrc, 'w').write(templates.COURIER_IMAPS % {
            'tls_pem': pem_path,
        })

        socketdir = os.path.split(self.courier_authsocket)[0]
        if os.path.exists(socketdir):
            os.chmod(socketdir, 0755)

        # Domain entries ----------------------------

        if os.path.exists(self.maildomains):
            shutil.rmtree(self.maildomains)
        os.makedirs(self.maildomains)
        os.chmod(self.maildomains, 0755)

        for mb in config.mailboxes:
            root = os.path.join(config.mailroot, mb.name)
            if not os.path.exists(root):
                os.makedirs(root)
                os.chown(root, self.mailuid, self.mailgid)

            with open(os.path.join(self.maildomains, mb.domain), 'a+') as f:
                f.write(mb.local + '\n')
            os.chmod(os.path.join(self.maildomains, mb.domain), 0755)

        # Forwarding entries ----------------------------

        if os.path.exists(self.mailforward):
            shutil.rmtree(self.mailforward)
        os.makedirs(self.mailforward)
        os.chmod(self.mailforward, 0755)

        for mb in config.forwarding_mailboxes:
            fpath = os.path.join(
                self.mailforward,
                '%s@%s' % (mb.local, mb.domain)
            )
            with open(fpath, 'a+') as f:
                for target in mb.targets:
                    f.write(target.email + ',')
                if any(x.local == mb.local and x.domain == mb.domain for x in config.mailboxes):
                    f.write(mb.local + '@' + mb.domain)
            os.chmod(fpath, 0755)

        # UserDB ------------------------------------

        if os.path.exists(self.courier_userdb):
            os.unlink(self.courier_userdb)

        for mb in config.mailboxes:
            root = os.path.join(config.mailroot, mb.name)
            subprocess.call([
                'userdb',
                mb.name,
                'set',
                'uid=%s' % self.mailuid,
                'gid=%s' % self.mailgid,
                'home=%s' % root,
                'mail=%s' % root,
            ])

            udbpw = subprocess.Popen(
                ['userdbpw', '-md5'],
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE
            )
            o, e = udbpw.communicate(
                '%s\n%s\n' % (mb.password, mb.password)
            )
            md5pw = o

            udb = subprocess.Popen(
                ['userdb', mb.name, 'set', 'systempw'],
                stdin=subprocess.PIPE
            )
            udb.communicate(md5pw)

        subprocess.call(['makeuserdb'])

        EximRestartable.get().restart()
        CourierIMAPRestartable.get().restart()
        CourierAuthRestartable.get().restart()


@plugin
class MailManager (BasePlugin):
    config_path = '/etc/ajenti/mail.json'
    dkim_path = platform_select(
        debian='/etc/exim4/dkim/',
        centos='/etc/exim/dkim/',
    )
    tls_path = platform_select(
        debian='/etc/exim4/tls/',
        centos='/etc/exim/tls/',
    )

    def init(self):
        self.backend = MailBackend.get()

        if os.path.exists(self.config_path):
            self.is_configured = True
            self.config = Config(json.load(open(self.config_path)))
        else:
            self.is_configured = False
            self.config = Config.create()

    def get_usage(self, mb):
        return int(subprocess.check_output(
            ['du', '-sb', os.path.join(self.config.mailroot, mb.name)]
        ).split()[0])

    def save(self):
        j = json.dumps(self.config.save(), indent=4)
        with open(self.config_path, 'w') as f:
            f.write(j)
        os.chmod(self.config_path, 0600)
        self.is_configured = True

        self.backend.configure(self.config)

    def generate_tls_cert(self):
        if not os.path.exists(self.tls_path):
            os.makedirs(self.tls_path)
        key_path = os.path.join(self.tls_path, 'mail.key')
        cert_path = os.path.join(self.tls_path, 'mail.crt')
        openssl = subprocess.Popen([
            'openssl', 'req', '-x509', '-newkey', 'rsa:1024',
            '-keyout', key_path, '-out', cert_path, '-days', '4096',
            '-nodes'
        ])
        openssl.communicate('\n\n\n\n\n\n\n\n\n\n\n\n')
        self.config.tls_enable = True
        self.config.tls_certificate = cert_path
        self.config.tls_privatekey = key_path

    def generate_dkim_key(self):
        if not os.path.exists(self.dkim_path):
            os.makedirs(self.dkim_path)

        privkey_path = os.path.join(self.dkim_path, 'private.key')

        subprocess.call([
            'openssl', 'genrsa', '-out', privkey_path, '2048'
        ])

        self.config.dkim_enable = True
        self.config.dkim_private_key = privkey_path


@plugin
class EximRestartable (Restartable):
    def restart(self):
        ServiceMultiplexor.get().get_one(platform_select(
            debian='exim4',
            default='exim',
        )).command('restart')


@plugin
class CourierIMAPRestartable (Restartable):
    def restart(self):
        ServiceMultiplexor.get().get_one(platform_select(
            debian='courier-imap',
            centos='courier-imap',
            default='courier-imapd',
        )).restart()
        if ajenti.platform != 'centos':  # centos runs both
            ServiceMultiplexor.get().get_one(platform_select(
                debian='courier-imap-ssl',
                default='courier-imapd-ssl',
            )).restart()


@plugin
class CourierAuthRestartable (Restartable):
    def restart(self):
        ServiceMultiplexor.get().get_one(platform_select(
            debian='courier-authdaemon',
            centos='courier-authlib',
        )).restart()

########NEW FILE########
__FILENAME__ = main
import os
import subprocess

from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder
from ajenti.util import str_fsize

from ajenti.plugins.vh.api import VHManager

from api import MailManager, ForwardingMailbox, ForwardingTarget, Mailbox


@plugin
class MailPlugin (SectionPlugin):
    def init(self):
        self.title = _('Mail')
        self.icon = 'envelope'
        self.category = 'Web'

        self.manager = MailManager.get()

        if not self.manager.is_configured:
            self.append(self.ui.inflate('vh-mail:not-configured'))
        else:
            self.post_init()

    @on('initial-enable', 'click')
    def on_initial_enable(self):
        self.post_init()
        self.manager.save()
        self.refresh()

    def post_init(self):
        self.empty()
        self.append(self.ui.inflate('vh-mail:main'))

        self.binder = Binder(None, self)

        def post_mb_bind(object, collection, item, ui):
            ui.find('size').text = str_fsize(self.manager.get_usage(item))

        def post_mb_update(object, collection, item, ui):
            if ui.find('password').value:
                item.password = ui.find('password').value

        self.find('mailboxes').post_item_bind = post_mb_bind
        self.find('mailboxes').post_item_update = post_mb_update
        self.find('mailboxes').filter = \
            lambda mb: self.context.session.identity in ['root', mb.owner]
        self.find('targets').new_item = lambda c: ForwardingTarget.create()

        self.binder.setup(self.manager.config)

    def _fetch_new_mailbox_name(self, cls):
        mb = cls.create()
        mb.local = self.find('new-mailbox-local').value
        mb.domain = self.find('new-mailbox-domain').value or \
            self.find('new-mailbox-domain-custom').value

        if not mb.local:
            self.context.notify('error', _('Invalid mailbox name'))
            return

        if not mb.domain:
            self.context.notify('error', _('Invalid mailbox domain'))
            return

        if cls == ForwardingMailbox:
            for existing in self.manager.config.forwarding_mailboxes:
                if existing.name == mb.name:
                    self.context.notify(
                        'error',
                        _('This address is already taken')
                    )
                    return
        else:
            for existing in self.manager.config.mailboxes:
                if existing.name == mb.name:
                    self.context.notify(
                        'error',
                        _('This address is already taken')
                    )
                    return

        self.find('new-mailbox-local').value = ''
        return mb

    @on('new-mailbox', 'click')
    def on_new_mailbox(self):
        self.binder.update()
        mb = self._fetch_new_mailbox_name(Mailbox)
        if not mb:
            return
        mb.owner = self.context.session.identity
        mb.password = ''
        self.manager.config.mailboxes.append(mb)
        self.manager.save()
        self.binder.populate()

    @on('new-forwarding-mailbox', 'click')
    def on_new_forwarding_mailbox(self):
        self.binder.update()
        mb = self._fetch_new_mailbox_name(ForwardingMailbox)
        if not mb:
            return
        mb.owner = self.context.session.identity
        self.manager.config.forwarding_mailboxes.append(mb)
        self.manager.save()
        self.binder.populate()

    def on_page_load(self):
        self.refresh()

    def refresh(self):
        if not self.manager.is_configured:
            return

        domains = []
        for ws in VHManager.get().config.websites:
            if self.context.session.identity in ['root', ws.owner]:
                domains += [d.domain for d in ws.domains]
        domains = sorted(list(set(domains)))

        if self.find('new-mailbox-domain'):
            self.find('new-mailbox-domain').labels = \
                domains + [_('Custom domain')]
            self.find('new-mailbox-domain').values = domains + [None]

            if self.manager.is_configured:
                self.binder.unpopulate().populate()

        if os.path.exists(self.manager.config.dkim_private_key):
            pubkey = subprocess.check_output([
                'openssl', 'rsa', '-in', self.manager.config.dkim_private_key,
                '-pubout'
            ])
            pubkey = filter(None, pubkey.split('-'))[1].replace('\n', '')
            dns = '@\t\t\t\t10800 IN TXT "v=spf1 a -all"\n'
            dns += '_domainkey\t\t10800 IN TXT "o=~; r=postmaster@<domain>"\n'
            dns += '%s._domainkey\t10800 IN TXT "v=DKIM1; k=rsa; p="%s"\n' % (
                self.manager.config.dkim_selector,
                pubkey
            )
            dns += '_dmarc\t\t\t10800 IN TXT "v=DMARC1; p=quarantine; sp=r"\n'

            self.find('dkim-domain-entry').value = dns
        else:
            self.find('dkim-domain-entry').value = _('No valid key exists')

    @on('generate-dkim-key', 'click')
    def on_generate_dkim_key(self):
        self.binder.update()
        self.manager.generate_dkim_key()
        self.binder.populate()
        self.save()

    @on('generate-tls-cert', 'click')
    def on_generate_tls_cert(self):
        self.binder.update()
        self.manager.generate_tls_cert()
        self.binder.populate()
        self.save()

    @on('save', 'click')
    def save(self):
        self.binder.update()
        self.manager.save()
        self.refresh()
        self.context.notify('info', _('Saved'))

########NEW FILE########
__FILENAME__ = templates
EXIM_CONFIG = r"""
#--AUTOMATICALLY GENERATED - DO NO EDIT!

#--MACROS

SMTP_PORT = 25
LOCAL_INTERFACES = <; 0.0.0.0.25 ; 0.0.0.0.465 ; [::0]:25 ; [::0]:465
CONFDIR = /etc/exim4

LOCAL_DOMAINS = %(local_domains)s
ETC_MAILNAME = %(mailname)s
LOCAL_DELIVERY = mail_spool
CHECK_RCPT_LOCAL_LOCALPARTS = ^[.] : ^.*[@%%!/|`#&?]
CHECK_RCPT_REMOTE_LOCALPARTS = ^[./|] : ^.*[@%%!`#&?] : ^.*/\\.\\./

%(dkim_enable)s
DKIM_SELECTOR = %(dkim_selector)s
DKIM_PRIVATE_KEY = %(dkim_private_key)s
DKIM_CANON = relaxed
DKIM_STRICT = 1

%(tls_enable)s
TLS_ADVERTISE_HOSTS = *
TLS_CERTIFICATE = %(tls_certificate)s
TLS_PRIVATEKEY = %(tls_privatekey)s
TLS_VERIFY_CERTIFICATES = ${if exists{/etc/ssl/certs/ca-certificates.crt} {/etc/ssl/certs/ca-certificates.crt} {/dev/null}}

COURIERSOCKET = %(courier_authsocket)s

#--CONFIGURATION

%(custom_mta_config)s

daemon_smtp_ports = SMTP_PORT
local_interfaces = LOCAL_INTERFACES
domainlist local_domains = LOCAL_DOMAINS
qualify_domain = ETC_MAILNAME

gecos_pattern = ^([^,:]*)
gecos_name = $1

acl_smtp_mail = acl_check_mail
acl_smtp_rcpt = acl_check_rcpt
acl_smtp_data = acl_check_data

# spamd_address = 127.0.0.1 783

local_from_check = false
local_sender_retain = true
untrusted_set_sender = *

ignore_bounce_errors_after = 2d
timeout_frozen_after = 7d
freeze_tell = postmaster
spool_directory = /var/spool/exim4

trusted_users = uucp

.ifdef TLS_ENABLE
tls_on_connect_ports = 465
tls_advertise_hosts = TLS_ADVERTISE_HOSTS
tls_certificate = TLS_CERTIFICATE
tls_privatekey = TLS_PRIVATEKEY
tls_verify_certificates = TLS_VERIFY_CERTIFICATES
.endif


begin acl

%(custom_mta_acl)s

acl_check_mail:
  .ifdef CHECK_MAIL_HELO_ISSUED
  deny
    message = no HELO given before MAIL command
    condition = ${if def:sender_helo_name {no}{yes}}
  .endif

  accept

acl_check_rcpt:
  accept
    hosts = :
    control = dkim_disable_verify

  .ifdef CHECK_RCPT_LOCAL_LOCALPARTS
  deny
    domains = +local_domains
    local_parts = CHECK_RCPT_LOCAL_LOCALPARTS
    message = restricted characters in address
  .endif

  .ifdef CHECK_RCPT_REMOTE_LOCALPARTS
  deny
    domains = !+local_domains
    local_parts = CHECK_RCPT_REMOTE_LOCALPARTS
    message = restricted characters in address
  .endif

  accept
    .ifndef CHECK_RCPT_POSTMASTER
    local_parts = postmaster
    .else
    local_parts = CHECK_RCPT_POSTMASTER
    .endif
    domains = +local_domains

  .ifdef CHECK_RCPT_VERIFY_SENDER
  deny
    message = Sender verification failed
    !verify = sender
  .endif

  accept
    authenticated = *
    control = submission/sender_retain
    control = dkim_disable_verify

  require
    message = relay not permitted
    domains = +local_domains

  require
    verify = recipient

  .ifdef CHECK_RCPT_SPF
  deny
    message = [SPF] $sender_host_address is not allowed to send mail from \
              ${if def:sender_address_domain {$sender_address_domain}{$sender_helo_name}}.  \
              Please see \
          http://www.openspf.org/Why?scope=${if def:sender_address_domain \
              {mfrom}{helo}};identity=${if def:sender_address_domain \
              {$sender_address}{$sender_helo_name}};ip=$sender_host_address
    log_message = SPF check failed.
    condition = ${run{/usr/bin/spfquery.mail-spf-perl --ip \
                   \"$sender_host_address\" --identity \
                   ${if def:sender_address_domain \
                       {--scope mfrom  --identity \"$sender_address\"}\
                       {--scope helo --identity  \"$sender_helo_name\"}}}\
                   {no}{${if eq {$runrc}{1}{yes}{no}}}}

  defer
    message = Temporary DNS error while checking SPF record.  Try again later.
    condition = ${if eq {$runrc}{5}{yes}{no}}

  warn
    condition = ${if <={$runrc}{6}{yes}{no}}
    add_header = Received-SPF: ${if eq {$runrc}{0}{pass}\
                                {${if eq {$runrc}{2}{softfail}\
                                 {${if eq {$runrc}{3}{neutral}\
                  {${if eq {$runrc}{4}{permerror}\
                   {${if eq {$runrc}{6}{none}{error}}}}}}}}}\
                } client-ip=$sender_host_address; \
                ${if def:sender_address_domain \
                   {envelope-from=${sender_address}; }{}}\
                helo=$sender_helo_name

  warn
    log_message = Unexpected error in SPF check.
    condition = ${if >{$runrc}{6}{yes}{no}}
  .endif


  .ifdef CHECK_RCPT_IP_DNSBLS
  warn
    dnslists = CHECK_RCPT_IP_DNSBLS
    add_header = X-Warning: $sender_host_address is listed at $dnslist_domain ($dnslist_value: $dnslist_text)
    log_message = $sender_host_address is listed at $dnslist_domain ($dnslist_value: $dnslist_text)
  .endif

  .ifdef CHECK_RCPT_DOMAIN_DNSBLS
  warn
    !senders = ${if exists{CONFDIR/local_domain_dnsbl_whitelist}\
                    {CONFDIR/local_domain_dnsbl_whitelist}\
                    {}}
    dnslists = CHECK_RCPT_DOMAIN_DNSBLS
    add_header = X-Warning: $sender_address_domain is listed at $dnslist_domain ($dnslist_value: $dnslist_text)
    log_message = $sender_address_domain is listed at $dnslist_domain ($dnslist_value: $dnslist_text)
  .endif

  accept


acl_check_data:

  deny
    message = Message headers fail syntax check
    !verify = header_syntax

  accept

begin routers

%(custom_mta_routers)s

vforward:
  debug_print = "R: vforward for $local_part@$domain"
  driver = redirect
  allow_defer
  allow_fail
  no_verify
  domains = +local_domains
  file = %(mailforward)s/$local_part@$domain
  file_transport = address_file
  pipe_transport = address_pipe

vdomain:
  debug_print = "R: vdomain for $local_part@$domain"
  driver = accept
  domains = dsearch;%(maildomains)s
  local_parts = lsearch;%(maildomains)s/$domain
  transport = vmail


dnslookup:
  debug_print = "R: dnslookup for $local_part@$domain"
  driver = dnslookup
  domains = ! +local_domains
  transport = remote_smtp
  headers_remove = received
  same_domain_copy_routing = yes
  ignore_target_hosts = 0.0.0.0 : 127.0.0.0/8 : 192.168.0.0/16 :\
                        172.16.0.0/12 : 10.0.0.0/8 : 169.254.0.0/16
  no_more

nonlocal:
  debug_print = "R: nonlocal for $local_part@$domain"
  driver = redirect
  domains = ! +local_domains
  allow_fail
  data = :fail: Mailing to remote domains not supported
  no_more


COND_LOCAL_SUBMITTER = "\
               ${if match_ip{$sender_host_address}{:@[]}\
                    {1}{0}\
        }"

real_local:
  debug_print = "R: real_local for $local_part@$domain"
  driver = accept
  domains = +local_domains
  condition = COND_LOCAL_SUBMITTER
  local_part_prefix = real-
  check_local_user
  transport = LOCAL_DELIVERY

procmail:
  debug_print = "R: procmail for $local_part@$domain"
  driver = accept
  domains = +local_domains
  check_local_user
  transport = procmail_pipe
  # emulate OR with "if exists"-expansion
  require_files = ${local_part}:\
                  ${if exists{/etc/procmailrc}\
                    {/etc/procmailrc}{${home}/.procmailrc}}:\
                  +/usr/bin/procmail
  no_verify
  no_expn

maildrop:
  debug_print = "R: maildrop for $local_part@$domain"
  driver = accept
  domains = +local_domains
  check_local_user
  transport = maildrop_pipe
  require_files = ${local_part}:${home}/.mailfilter:+/usr/bin/maildrop
  no_verify
  no_expn


local_user:
  debug_print = "R: local_user for $local_part@$domain"
  driver = accept
  domains = +local_domains
  check_local_user
  local_parts = ! root
  transport = LOCAL_DELIVERY
  cannot_route_message = Unknown user

mail4root:
  debug_print = "R: mail4root for $local_part@$domain"
  driver = redirect
  domains = +local_domains
  data = /var/mail/mail
  file_transport = address_file
  local_parts = root
  user = mail
  group = mail


begin transports

%(custom_mta_transports)s


vmail:
  debug_print = "T: vmail for $local_part@$domain"
  driver = appendfile
  user = mail
  maildir_format = true
  directory = %(mailroot)s/$local_part@$domain
  create_directory
  delivery_date_add
  envelope_to_add
  return_path_add
  group = mail
  mode = 0600

mail_spool:
  debug_print = "T: appendfile for $local_part@$domain"
  driver = appendfile
  file = /var/mail/$local_part
  delivery_date_add
  envelope_to_add
  return_path_add
  group = mail
  mode = 0660
  mode_fail_narrower = false

maildir_home:
  debug_print = "T: maildir_home for $local_part@$domain"
  driver = appendfile
  .ifdef MAILDIR_HOME_MAILDIR_LOCATION
  directory = MAILDIR_HOME_MAILDIR_LOCATION
  .else
  directory = $home/Maildir
  .endif
  .ifdef MAILDIR_HOME_CREATE_DIRECTORY
  create_directory
  .endif
  .ifdef MAILDIR_HOME_CREATE_FILE
  create_file = MAILDIR_HOME_CREATE_FILE
  .endif
  delivery_date_add
  envelope_to_add
  return_path_add
  maildir_format
  .ifdef MAILDIR_HOME_DIRECTORY_MODE
  directory_mode = MAILDIR_HOME_DIRECTORY_MODE
  .else
  directory_mode = 0700
  .endif
  .ifdef MAILDIR_HOME_MODE
  mode = MAILDIR_HOME_MODE
  .else
  mode = 0600
  .endif
  mode_fail_narrower = false

maildrop_pipe:
  debug_print = "T: maildrop_pipe for $local_part@$domain"
  driver = pipe
  path = "/bin:/usr/bin:/usr/local/bin"
  command = "/usr/bin/maildrop"
  return_path_add
  delivery_date_add
  envelope_to_add

procmail_pipe:
  debug_print = "T: procmail_pipe for $local_part@$domain"
  driver = pipe
  path = "/bin:/usr/bin:/usr/local/bin"
  command = "/usr/bin/procmail"
  return_path_add
  delivery_date_add
  envelope_to_add

remote_smtp:
  debug_print = "T: remote_smtp for $local_part@$domain"
  driver = smtp
  .ifdef DKIM_ENABLE
    dkim_domain = $sender_address_domain
    .ifdef DKIM_SELECTOR
    dkim_selector = DKIM_SELECTOR
    .endif
    .ifdef DKIM_PRIVATE_KEY
    dkim_private_key = DKIM_PRIVATE_KEY
    .endif
    .ifdef DKIM_CANON
    dkim_canon = DKIM_CANON
    .endif
    .ifdef DKIM_STRICT
    dkim_strict = DKIM_STRICT
    .endif
    .ifdef DKIM_SIGN_HEADERS
    dkim_sign_headers = DKIM_SIGN_HEADERS
    .endif
  .endif

address_file:
  debug_print = "T: address_file for $local_part@$domain"
  driver = appendfile
  delivery_date_add
  envelope_to_add
  return_path_add

address_pipe:
  debug_print = "T: address_pipe for $local_part@$domain"
  driver = pipe
  return_fail_output

address_reply:
  debug_print = "T: autoreply for $local_part@$domain"
  driver = autoreply



begin retry
*                      *           F,2h,15m; G,16h,1h,1.5; F,4d,6h


begin rewrite

begin authenticators

login:
  driver = plaintext
  public_name = LOGIN
  server_prompts = Username:: : Password::
  server_condition = ${extract {address} {${readsocket{COURIERSOCKET} \
      {AUTH ${strlen:exim\nlogin\n$1\n$2\n}\nexim\nlogin\n$1\n$2\n} }} {yes} fail}
  server_set_id = $1

plain:
  driver = plaintext
  public_name = PLAIN
  server_prompts = :
  server_condition = ${extract {address} {${readsocket{COURIERSOCKET} \
      {AUTH ${strlen:exim\nlogin\n$2\n$3\n}\nexim\nlogin\n$2\n$3\n} }} {yes} fail}
  server_set_id = $2
  server_advertise_condition = ${if eq{$tls_cipher}{} {no} {yes}}
"""

COURIER_AUTHRC = """
authmodulelist="authuserdb authpam"
daemons=5
authdaemonvar=%(courier_authsocket)s
DEBUG_LOGIN=0
DEFAULTOPTIONS=""
LOGGEROPTS=""
"""

COURIER_IMAP = """
ADDRESS=0
PORT=143
MAXDAEMONS=40
MAXPERIP=20
PIDFILE=/var/run/courier/imapd.pid
TCPDOPTS="-nodnslookup -noidentlookup"
LOGGEROPTS="-name=imapd"
IMAP_CAPABILITY="IMAP4rev1 UIDPLUS CHILDREN NAMESPACE THREAD=ORDEREDSUBJECT THREAD=REFERENCES SORT QUOTA IDLE"
IMAP_KEYWORDS=1
IMAP_ACL=1
IMAP_CAPABILITY_ORIG="IMAP4rev1 UIDPLUS CHILDREN NAMESPACE THREAD=ORDEREDSUBJECT THREAD=REFERENCES SORT QUOTA AUTH=CRAM-MD5 AUTH=CRAM-SHA1 AUTH=CRAM-SHA256 IDLE"
IMAP_PROXY=0
IMAP_IDLE_TIMEOUT=60
IMAP_MAILBOX_SANITY_CHECK=1
IMAP_CAPABILITY_TLS="$IMAP_CAPABILITY AUTH=PLAIN"
IMAP_CAPABILITY_TLS_ORIG="$IMAP_CAPABILITY_ORIG AUTH=PLAIN"
IMAP_DISABLETHREADSORT=0
IMAP_CHECK_ALL_FOLDERS=0
IMAP_OBSOLETE_CLIENT=0
IMAP_UMASK=022
IMAP_ULIMITD=131072
IMAP_USELOCKS=1
IMAP_SHAREDINDEXFILE=/etc/courier/shared/index
IMAP_ENHANCEDIDLE=0
IMAP_TRASHFOLDERNAME=Trash
IMAP_EMPTYTRASH=Trash:7
IMAP_MOVE_EXPUNGE_TO_TRASH=0
SENDMAIL=/usr/sbin/sendmail
HEADERFROM=X-IMAP-Sender
IMAPDSTART=YES
MAILDIRPATH=Maildir
"""

COURIER_IMAPS = """
SSLPORT=993
SSLADDRESS=0
SSLPIDFILE=/var/run/courier/imapd-ssl.pid
SSLLOGGEROPTS="-name=imapd-ssl"
IMAPDSSLSTART=YES
IMAPDSTARTTLS=YES
IMAP_TLS_REQUIRED=0
COURIERTLS=/usr/bin/couriertls
TLS_KX_LIST=ALL
TLS_COMPRESSION=ALL
TLS_CERTS=X509
TLS_CERTFILE=%(tls_pem)s
TLS_TRUSTCERTS=/etc/ssl/certs
TLS_VERIFYPEER=NONE
TLS_CACHEFILE=/var/lib/courier/couriersslcache
TLS_CACHESIZE=524288
MAILDIRPATH=Maildir
"""

########NEW FILE########
__FILENAME__ = mysql
import uuid

from ajenti.api import *
from ajenti.ui import on
from ajenti.ui.binder import Binder

from ajenti.plugins.mysql.api import MySQLDB
from ajenti.plugins.db_common.api import Database, User
from ajenti.plugins.vh.extensions import BaseExtension


@plugin
class MySQLExtension (BaseExtension):
    default_config = {
        'created': False,
        'name': None,
        'user': None,
        'password': None,
    }
    name = 'MySQL'

    def init(self):
        self.append(self.ui.inflate('vh-mysql:ext'))
        self.binder = Binder(self, self)
        self.refresh()
        self.db = MySQLDB.get()

    @staticmethod
    def selftest():
        try:
            MySQLDB.get().query_databases()
        except:
            pass

    def refresh(self):
        self.binder.setup().populate()
        self.find('db-name').value = self.website.slug
        self.find('db-username').value = self.website.slug
        
    def update(self):
        self.binder.update()

    def on_destroy(self):
        if self.config['created']:
            self.on_delete()

    @on('create', 'click')
    def on_create(self):
        try:
            self.db.query_databases()
        except Exception, e:
            self.context.notify('error', str(e))
            self.context.launch('configure-plugin', plugin=self.db)
            return

        dbname = self.find('db-name').value
        username = self.find('db-username').value

        for db in self.db.query_databases():
            if db.name == dbname:
                self.context.notify('error', _('This database name is already used'))
                return
        
        for user in self.db.query_users():
            if user.name == username:
                self.context.notify('error', _('This username is already used'))
                return

        self.config['name'] = dbname
        self.config['username'] = username
        self.config['password'] = str(uuid.uuid4())
        
        try:
            self.db.query_create(self.config['name'])
        except Exception, e:
            self.context.notify('error', str(e))
            return

        self.config['created'] = True

        db = Database()
        db.name = self.config['name']

        user = User()
        user.name = self.config['username']
        user.password = self.config['password']
        user.host = 'localhost'
        try:
            self.db.query_create_user(user)
        except Exception, e:
            self.db.query_drop(db)
            self.context.notify('error', str(e))
            return

        self.db.query_grant(user, db)
        self.refresh()

    @on('delete', 'click')
    def on_delete(self):
        db = Database()
        db.name = self.config['name']
        try:
            self.db.query_drop(db)
        except Exception, e:
            # I'm gonna burn in hell for this...
            if not 'ERROR 1008' in e:
                raise e
        
        user = User()
        user.name = self.config['username']
        user.host = 'localhost'
        
        try:
            self.db.query_drop_user(user)
        except Exception, e:
            if not 'ERROR 1008' in e:
                raise e
        self.config['created'] = False
        self.refresh()

########NEW FILE########
__FILENAME__ = nginx
import os
import shutil
import subprocess

from ajenti.api import *
from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.vh.api import WebserverComponent, SanityCheck, Restartable

from nginx_templates import *


@plugin
class NginxConfigTest (SanityCheck):
    def init(self):
        self.type = _('NGINX config test')

    def check(self):
        p = subprocess.Popen(['nginx', '-t'], stderr=subprocess.PIPE)
        o, self.message = p.communicate()
        return p.returncode == 0


@plugin
class NginxServiceTest (SanityCheck):
    def init(self):
        self.type = _('NGINX service')

    def check(self):
        return ServiceMultiplexor.get().get_one('nginx').running


@plugin
class NginxWebserver (WebserverComponent):
    def init(self):
        self.config_root = '/etc/nginx'
        self.config_file = '/etc/nginx/nginx.conf'
        self.config_file_mime = '/etc/nginx/mime.conf'
        self.config_file_fastcgi = '/etc/nginx/fcgi.conf'
        self.config_file_proxy = '/etc/nginx/proxy.conf'
        self.config_vhost_root = '/etc/nginx/conf.d'
        self.config_custom_root = '/etc/nginx.custom.d'

    def __generate_website_location(self, ws, location):
        params = location.backend.params

        if location.backend.type == 'static':
            content = TEMPLATE_LOCATION_CONTENT_STATIC % {
                'autoindex': 'autoindex on;' if params['autoindex'] else '',
            }

        if location.backend.type == 'proxy':
            content = TEMPLATE_LOCATION_CONTENT_PROXY % {
                'url': params.get('url', 'http://127.0.0.1/'),
            }

        if location.backend.type == 'fcgi':
            content = TEMPLATE_LOCATION_CONTENT_FCGI % {
                'url': params.get('url', '127.0.0.1:9000'),
            }

        if location.backend.type == 'php-fcgi':
            content = TEMPLATE_LOCATION_CONTENT_PHP_FCGI % {
                'id': location.backend.id,
            }

        if location.backend.type == 'python-wsgi':
            content = TEMPLATE_LOCATION_CONTENT_PYTHON_WSGI % {
                'id': location.backend.id,
            }

        if location.backend.type == 'ruby-unicorn':
            content = TEMPLATE_LOCATION_CONTENT_RUBY_UNICORN % {
                'id': location.backend.id,
            }

        if location.backend.type == 'ruby-puma':
            content = TEMPLATE_LOCATION_CONTENT_RUBY_PUMA % {
                'id': location.backend.id,
            }

        if location.backend.type == 'nodejs':
            content = TEMPLATE_LOCATION_CONTENT_NODEJS % {
                'port': location.backend.params.get('port', 8000),
            }

        if location.custom_conf_override:
            content = ''

        path_spec = ''
        if location.path:
            if location.path_append_pattern:
                path_spec = 'root %s;' % location.path
            else:
                path_spec = 'alias %s;' % location.path

        return TEMPLATE_LOCATION % {
            'pattern': location.pattern,
            'custom_conf': location.custom_conf,
            'path': path_spec,
            'match': {
                'exact': '',
                'regex': '~',
                'force-regex': '^~',
            }[location.match],
            'content': content,
        }

    def __generate_website_config(self, website):
        params = {
            'slug': website.slug,
            'server_name': (
                'server_name %s;' % (' '.join(domain.domain for domain in website.domains))
            ) if website.domains else '',
            'ports': (
                '\n'.join(
                    'listen %s:%s%s%s%s;' % (
                        x.host, x.port,
                        ' ssl' if x.ssl else '',
                        ' spdy' if x.spdy else '',
                        ' default' if x.default else '',
                    )
                    for x in website.ports
                )
            ),
            'ssl_cert': 'ssl_certificate %s;' % website.ssl_cert_path if website.ssl_cert_path else '',
            'ssl_key': 'ssl_certificate_key %s;' % website.ssl_key_path if website.ssl_key_path else '',
            'maintenance': TEMPLATE_MAINTENANCE if website.maintenance_mode else '',
            'root': website.root,
            'custom_conf': website.custom_conf,
            'locations': (
                '\n'.join(self.__generate_website_location(website, location) for location in website.locations)
            ) if not website.maintenance_mode else '',
        }
        return TEMPLATE_WEBSITE % params

    def create_configuration(self, config):
        shutil.rmtree(self.config_root)
        os.mkdir(self.config_root)
        os.mkdir(self.config_vhost_root)

        if not os.path.exists(self.config_custom_root):
            os.mkdir(self.config_custom_root)

        open(self.config_file, 'w').write(TEMPLATE_CONFIG_FILE)
        open(self.config_file_mime, 'w').write(TEMPLATE_CONFIG_MIME)
        open(self.config_file_fastcgi, 'w').write(TEMPLATE_CONFIG_FCGI)
        open(self.config_file_proxy, 'w').write(TEMPLATE_CONFIG_PROXY)

        for website in config.websites:
            if website.enabled:
                open(os.path.join(self.config_vhost_root, website.slug + '.conf'), 'w')\
                    .write(self.__generate_website_config(website))

    def apply_configuration(self):
        NGINXRestartable.get().schedule()

    def get_checks(self):
        return [NginxConfigTest.new(), NginxServiceTest.new()]


@plugin
class NGINXRestartable (Restartable):
    def restart(self):
        s = ServiceMultiplexor.get().get_one('nginx')
        if not s.running:
            s.start()
        else:
            s.command('reload')

########NEW FILE########
__FILENAME__ = nginx_templates
import multiprocessing


TEMPLATE_CONFIG_FILE = """
#AUTOMATICALLY GENERATED - DO NO EDIT!

user %(user)s %(user)s;
pid /var/run/nginx.pid;
worker_processes %(workers)s;
worker_rlimit_nofile 100000;

events {
    worker_connections  4096;
    multi_accept on;
}

http {
    default_type application/octet-stream;

    access_log off;
    error_log  %(log_root)s/error.log crit;

    sendfile on;
    tcp_nopush on;

    keepalive_timeout 20;
    client_header_timeout 20;
    client_body_timeout 20;
    reset_timedout_connection on;
    send_timeout 20;

    types_hash_max_size 2048;

    gzip on;
    gzip_disable "msie6";
    gzip_proxied any;
    gzip_min_length 256;
    gzip_comp_level 4;
    gzip_types text/plain text/css application/json application/x-javascript text/xml application/xml application/xml+rss text/javascript application/javascript text/x-js;

    server_names_hash_bucket_size 128;

    include mime.conf;
    charset UTF-8;

    open_file_cache max=100000 inactive=20s;
    open_file_cache_valid 30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;

    server_tokens off;

    include proxy.conf;
    include fcgi.conf;

    include conf.d/*.conf;
    include /etc/nginx.custom.d/*.conf;
}
""" % {
    'workers': multiprocessing.cpu_count(),
    'log_root': '/var/log/nginx',
    'user': 'www-data',
}

TEMPLATE_CONFIG_PROXY = """
proxy_redirect          off;
proxy_set_header        Host            $host;
proxy_set_header        X-Real-IP       $remote_addr;
proxy_set_header        X-Forwarded-For $proxy_add_x_forwarded_for;
client_max_body_size    10m;
client_body_buffer_size 128k;
proxy_connect_timeout   90;
proxy_send_timeout      90;
proxy_read_timeout      90;
proxy_buffers           32 4k;
"""

TEMPLATE_CONFIG_FCGI = """
fastcgi_param   QUERY_STRING            $query_string;
fastcgi_param   REQUEST_METHOD          $request_method;
fastcgi_param   CONTENT_TYPE            $content_type;
fastcgi_param   CONTENT_LENGTH          $content_length;

fastcgi_param   SCRIPT_FILENAME         $document_root$fastcgi_script_name;
fastcgi_param   SCRIPT_NAME             $fastcgi_script_name;
fastcgi_param   PATH_INFO               $fastcgi_path_info;
fastcgi_param   REQUEST_URI             $request_uri;
fastcgi_param   DOCUMENT_URI            $document_uri;
fastcgi_param   DOCUMENT_ROOT           $document_root;
fastcgi_param   SERVER_PROTOCOL         $server_protocol;

fastcgi_param   GATEWAY_INTERFACE       CGI/1.1;
fastcgi_param   SERVER_SOFTWARE         nginx/$nginx_version;

fastcgi_param   REMOTE_ADDR             $remote_addr;
fastcgi_param   REMOTE_PORT             $remote_port;
fastcgi_param   SERVER_ADDR             $server_addr;
fastcgi_param   SERVER_PORT             $server_port;
fastcgi_param   SERVER_NAME             $server_name;

fastcgi_param   HTTPS                   $https;

fastcgi_param   REDIRECT_STATUS         200;
"""

TEMPLATE_CONFIG_MIME = """
types {
    text/html                             html htm shtml;
    text/css                              css;
    text/xml                              xml rss;
    image/gif                             gif;
    image/jpeg                            jpeg jpg;
    application/x-javascript              js;
    text/plain                            txt;
    text/x-component                      htc;
    text/mathml                           mml;
    image/png                             png;
    image/x-icon                          ico;
    image/x-jng                           jng;
    image/vnd.wap.wbmp                    wbmp;
    application/java-archive              jar war ear;
    application/mac-binhex40              hqx;
    application/pdf                       pdf;
    application/x-cocoa                   cco;
    application/x-java-archive-diff       jardiff;
    application/x-java-jnlp-file          jnlp;
    application/x-makeself                run;
    application/x-perl                    pl pm;
    application/x-pilot                   prc pdb;
    application/x-rar-compressed          rar;
    application/x-redhat-package-manager  rpm;
    application/x-sea                     sea;
    application/x-shockwave-flash         swf;
    application/x-stuffit                 sit;
    application/x-tcl                     tcl tk;
    application/x-x509-ca-cert            der pem crt;
    application/x-xpinstall               xpi;
    application/zip                       zip;
    application/octet-stream              deb;
    application/octet-stream              bin exe dll;
    application/octet-stream              dmg;
    application/octet-stream              eot;
    application/octet-stream              iso img;
    application/octet-stream              msi msp msm;
    audio/mpeg                            mp3;
    audio/x-realaudio                     ra;
    video/mpeg                            mpeg mpg;
    video/quicktime                       mov;
    video/x-flv                           flv;
    video/x-msvideo                       avi;
    video/x-ms-wmv                        wmv;
    video/x-ms-asf                        asx asf;
    video/x-mng                           mng;
}
"""

TEMPLATE_WEBSITE = """
#AUTOMATICALLY GENERATED - DO NO EDIT!

server {
    %(ports)s
    %(ssl_cert)s
    %(ssl_key)s
    %(server_name)s

    access_log /var/log/nginx/%(slug)s.access.log;
    error_log /var/log/nginx/%(slug)s.error.log;

    root %(root)s;
    index index.html index.htm index.php;

    %(custom_conf)s

    %(maintenance)s
    %(locations)s
}
"""

TEMPLATE_MAINTENANCE = """
    location / {
        return 503;
        error_page 503 @maintenance;
    }

    location @maintenance {
        root /var/lib/ajenti/plugins/vh/extras;
        rewrite ^(.*)$ /maintenance.html break;
    }
"""

TEMPLATE_LOCATION = """
    location %(match)s %(pattern)s {
        %(path)s
        %(custom_conf)s
        %(content)s
    }
"""

TEMPLATE_LOCATION_CONTENT_STATIC = """
        %(autoindex)s
"""

TEMPLATE_LOCATION_CONTENT_PROXY = """
        proxy_pass %(url)s;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
"""

TEMPLATE_LOCATION_CONTENT_FCGI = """
        include fcgi.conf;
        fastcgi_pass %(url)s;
"""

TEMPLATE_LOCATION_CONTENT_PHP_FCGI = """
        fastcgi_index index.php;
        include fcgi.conf;
        fastcgi_pass unix:/var/run/php-fcgi-%(id)s.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
"""

TEMPLATE_LOCATION_CONTENT_PYTHON_WSGI = """
        proxy_pass http://unix:/var/run/gunicorn-%(id)s.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
"""

TEMPLATE_LOCATION_CONTENT_RUBY_UNICORN = """
        proxy_pass http://unix:/var/run/unicorn-%(id)s.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
"""

TEMPLATE_LOCATION_CONTENT_RUBY_PUMA = """
        proxy_pass http://unix:/var/run/puma-%(id)s.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
"""


TEMPLATE_LOCATION_CONTENT_NODEJS = """
        proxy_pass http://127.0.0.1:%(port)i;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
"""

########NEW FILE########
__FILENAME__ = nodejs
import subprocess

from ajenti.api import *
from ajenti.util import platform_select

from ajenti.plugins.supervisor.client import SupervisorServiceManager
from ajenti.plugins.vh.api import ApplicationGatewayComponent, SanityCheck
from ajenti.plugins.vh.processes import SupervisorRestartable

from reconfigure.configs import SupervisorConfig
from reconfigure.items.supervisor import ProgramData


class NodeServerTest (SanityCheck):
    def __init__(self, backend):
        SanityCheck.__init__(self)
        self.backend = backend
        self.type = _('Node.js service')
        self.name = backend.id

    def check(self):
        s = SupervisorServiceManager.get().get_one(self.backend.id)
        if s:
            self.message = s.status
        return s and s.running


@plugin
class NodeJS (ApplicationGatewayComponent):
    id = 'nodejs'
    title = 'Node.JS'

    def init(self):
        self.checks = []

    def create_configuration(self, config):
        self.checks = []

        node_bin = 'node'
        try:
            subprocess.call(['which', 'node'])
        except:
            node_bin = 'nodejs'

        sup = SupervisorConfig(path=platform_select(
            debian='/etc/supervisor/supervisord.conf',
            centos='/etc/supervisord.conf',
        ))
        sup.load()
        for p in sup.tree.programs:
            if p.command and p.command.startswith('node '):
                sup.tree.programs.remove(p)

        for website in config.websites:
            if website.enabled:
                for location in website.locations:
                    if location.backend.type == 'nodejs':
                        self.checks.append(NodeServerTest(location.backend))
                        p = ProgramData()
                        p.name = location.backend.id
                        p.command = '%s %s' % (
                            node_bin,
                            location.backend.params.get('script', None) or '.'
                        )
                        p.directory = location.path or website.root
                        sup.tree.programs.append(p)

        sup.save()

    def apply_configuration(self):
        SupervisorRestartable.get().schedule()

    def get_checks(self):
        return self.checks

########NEW FILE########
__FILENAME__ = phpfpm
import os

from ajenti.api import *
from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.vh.api import ApplicationGatewayComponent, SanityCheck, Restartable
from ajenti.plugins.vh.processes import SupervisorRestartable
from ajenti.util import platform_select


TEMPLATE_CONFIG_FILE = """
[global]
pid = %(pidfile)s
error_log = /var/log/php5-fpm.log

[global-pool]
user = www-data
group = www-data

listen = /var/run/php-fcgi.sock
listen.owner = www-data
listen.group = www-data
listen.mode = 0660

pm = dynamic
pm.start_servers = 1
pm.max_children = 5
pm.min_spare_servers = 1
pm.max_spare_servers = 5

%(pools)s
"""

TEMPLATE_POOL = """
[%(name)s]
user = www-data
group = www-data

listen = /var/run/php-fcgi-%(name)s.sock
listen.owner = www-data
listen.group = www-data
listen.mode = 0660

pm = dynamic
pm.max_children = %(max)s
pm.start_servers = %(min)s
pm.min_spare_servers = %(sp_min)s
pm.max_spare_servers = %(sp_max)s

php_admin_value[open_basedir] = %(php_open_basedir)s

%(php_extras)s
"""


fpm_service_name = platform_select(
    debian='php5-fpm',
    default='php-fpm',
)


@plugin
class FPMServiceTest (SanityCheck):
    def __init__(self):
        self.type = _('PHP-FPM service')

    def check(self):
        return ServiceMultiplexor.get().get_one(fpm_service_name).running


@plugin
class PHPFPM (ApplicationGatewayComponent):
    id = 'php-fcgi'
    title = 'PHP FastCGI'

    def init(self):
        self.config_file = platform_select(
            debian='/etc/php5/fpm/php-fpm.conf',
            centos='/etc/php-fpm.conf',
            arch='/etc/php/php-fpm.conf',
        )

    def __generate_pool(self, location, backend, name):
        pm_min = backend.params.get('pm_min', 1) or 1
        pm_max = backend.params.get('pm_max', 5) or 5

        extras = ''

        for l in (backend.params.get('php_admin_values', None) or '').splitlines():
            if '=' in l:
                k, v = l.split('=', 1)
                extras += 'php_admin_value[%s] = %s\n' % (k.strip(), v.strip())

        for l in (backend.params.get('php_flags', None) or '').splitlines():
            if '=' in l:
                k, v = l.split('=', 1)
                extras += 'php_flag[%s] = %s\n' % (k.strip(), v.strip())

        open_basedir = '%s:/tmp' % (location.path or location.website.root)
        if backend.params.get('php_open_basedir', None):
            open_basedir = backend.params.get('php_open_basedir', None)

        return TEMPLATE_POOL % {
            'name': name,
            'min': pm_min,
            'max': pm_max,
            'sp_min': min(2, pm_min),
            'sp_max': min(6, pm_max),
            'php_open_basedir': open_basedir,
            'php_extras': extras,
        }

    def __generate_website(self, website):
        r = ''
        for location in website.locations:
            if location.backend.type == 'php-fcgi':
                r += self.__generate_pool(location, location.backend, location.backend.id)
        return r

    def create_configuration(self, config):
        if os.path.exists(self.config_file):
            os.unlink(self.config_file)
        cfg = TEMPLATE_CONFIG_FILE % {
            'pidfile': platform_select(
                debian='/var/run/php5-fpm.pid',
                arch='/var/run/php-fpm.pid',
                centos='/var/run/php-fpm/php-fpm.pid',
            ),
            'pools': '\n'.join(self.__generate_website(_) for _ in config.websites if _.enabled)
        }
        open(self.config_file, 'w').write(cfg)

    def apply_configuration(self):
        PHPFPMRestartable.get().schedule()

    def get_checks(self):
        return [FPMServiceTest.new()]


@plugin
class PHPFPMRestartable (Restartable):
    def restart(self):
        s = ServiceMultiplexor.get().get_one(fpm_service_name)
        if not s.running:
            s.start()
        else:
            s.command('reload')

########NEW FILE########
__FILENAME__ = puma
import os

from ajenti.api import *
from ajenti.plugins.supervisor.client import SupervisorServiceManager
from ajenti.plugins.vh.api import ApplicationGatewayComponent, SanityCheck
from ajenti.plugins.vh.processes import SupervisorRestartable
from ajenti.util import platform_select

from reconfigure.configs import SupervisorConfig
from reconfigure.items.supervisor import ProgramData


class PumaServerTest (SanityCheck):
    def __init__(self, backend):
        SanityCheck.__init__(self)
        self.backend = backend
        self.type = _('PUMA service')
        self.name = backend.id

    def check(self):
        s = SupervisorServiceManager.get().get_one(self.backend.id)
        if s:
            self.message = s.status
        return s and s.running


@plugin
class Puma (ApplicationGatewayComponent):
    id = 'ruby-puma'
    title = 'Ruby Puma'

    def init(self):
        self.checks = []

    def __generate_website(self, website):
        pass

    def create_configuration(self, config):
        self.checks = []
        sup = SupervisorConfig(path=platform_select(
            debian='/etc/supervisor/supervisord.conf',
            centos='/etc/supervisord.conf',
        ))
        sup.load()
        for p in sup.tree.programs:
            if p.command.startswith('puma') or p.command.startswith('bundle exec puma'):
                sup.tree.programs.remove(p)

        for website in config.websites:
            if website.enabled:
                for location in website.locations:
                    if location.backend.type == 'ruby-puma':
                        self.checks.append(PumaServerTest(location.backend))
                        p = ProgramData()
                        p.name = location.backend.id
                        bundler = location.backend.params.get('bundler', True)
                        workers = location.backend.params.get('workers', 4)
                        environment = location.backend.params.get('environment', 4)
                        p.command = 'puma -e %s -t %i -b unix:///var/run/puma-%s.sock' % (
                            environment, workers or 4, location.backend.id
                        )
                        if bundler:
                            p.command = 'bundle exec ' + p.command
                        p.environment = 'HOME="%s"' % website.root
                        p.directory = website.root
                        sup.tree.programs.append(p)

        sup.save()

    def apply_configuration(self):
        SupervisorRestartable.get().schedule()

    def get_checks(self):
        return self.checks

########NEW FILE########
__FILENAME__ = pureftpd
import os
import subprocess
import uuid

import ajenti
from ajenti.api import *
from ajenti.ui.binder import Binder
from ajenti.util import platform_select

from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.vh.api import MiscComponent
from ajenti.plugins.vh.extensions import BaseExtension


@plugin
class PureFTPDExtension (BaseExtension):
    default_config = {
        'created': False,
        'user': None,
        'password': None,
    }
    name = 'FTP'

    def init(self):
        self.append(self.ui.inflate('vh-pureftpd:ext'))
        self.binder = Binder(self, self)

        self.config['username'] = self.website.slug

        if not self.config['created']:
            self.config['password'] = str(uuid.uuid4())
            self.config['created'] = True

        self.refresh()

    def refresh(self):
        self.binder.setup().populate()

    def update(self):
        pass



CENTOS_CONFIG = """
ChrootEveryone              yes
BrokenClientsCompatibility  no
MaxClientsNumber            50
Daemonize                   yes
MaxClientsPerIP             8
VerboseLog                  no
DisplayDotFiles             yes
AnonymousOnly               no
NoAnonymous                 yes
SyslogFacility              ftp
DontResolve                 yes
MaxIdleTime                 15
PureDB                      /etc/pure-ftpd/pureftpd.pdb
PAMAuthentication             yes
LimitRecursion              10000 8
Umask                       133:022
MinUID                      1
UseFtpUsers                 no
AllowUserFXP                yes
ProhibitDotFilesWrite       no
ProhibitDotFilesRead        no
AutoRename                  no
AltLog                     clf:/var/log/pureftpd.log
"""


@plugin
class PureFTPD (MiscComponent):
    userdb_path = '/etc/pure-ftpd/pureftpd.passwd'
    config_path = platform_select(
        centos='/etc/pure-ftpd/pure-ftpd.conf',
        arch='/etc/pure-ftpd.conf',
    )

    def create_configuration(self, config):
        open(self.userdb_path, 'w').close()
        for website in config.websites:
            if website.enabled:
                cfg = website.extension_configs.get(PureFTPDExtension.classname)
                if cfg and cfg['created']:
                    p = subprocess.Popen(
                        [
                            'pure-pw', 'useradd', cfg['username'], '-u', 'www-data',
                            '-d', website.root,
                        ],
                        stdin=subprocess.PIPE
                    )
                    p.communicate('%s\n%s\n' % (cfg['password'], cfg['password']))

        subprocess.call(['pure-pw', 'mkdb'])

        if ajenti.platform == 'debian':
            open('/etc/pure-ftpd/conf/MinUID', 'w').write('1')
            authfile = '/etc/pure-ftpd/auth/00puredb'
            if not os.path.exists(authfile):
                os.symlink('/etc/pure-ftpd/conf/PureDB', authfile)
        if ajenti.platform in ['arch', 'centos']:
            open(self.config_path, 'w').write(CENTOS_CONFIG)

    def apply_configuration(self):
        ServiceMultiplexor.get().get_one('pure-ftpd').restart()

########NEW FILE########
__FILENAME__ = unicorn
import os
import shutil

from ajenti.api import *
from ajenti.plugins.vh.api import ApplicationGatewayComponent
from ajenti.plugins.vh.processes import SupervisorRestartable
from ajenti.util import platform_select

from reconfigure.configs import SupervisorConfig
from reconfigure.items.supervisor import ProgramData


TEMPLATE_PROCESS = """
worker_processes %(workers)s
working_directory "%(root)s"
listen "unix:/var/run/unicorn-%(id)s.sock", :backlog => 64
preload_app true

stderr_path "/var/log/unicorn/%(id)s.stderr.log"
stdout_path "/var/log/unicorn/%(id)s.stderr.log"

before_fork do |server, worker|
  defined?(ActiveRecord::Base) and
    ActiveRecord::Base.connection.disconnect!
end

after_fork do |server, worker|
  defined?(ActiveRecord::Base) and
    ActiveRecord::Base.establish_connection
end
"""


@plugin
class Gunicorn (ApplicationGatewayComponent):
    id = 'ruby-unicorn'
    title = 'Ruby Unicorn'

    def init(self):
        self.config_dir = '/etc/unicorn.d'

    def __generate_website(self, website):
        for location in website.locations:
            if location.backend.type == 'ruby-unicorn':
                c = TEMPLATE_PROCESS % {
                    'id': location.backend.id,
                    'workers': location.backend.params.get('workers', 4),
                    'root': website.root,
                }
                open(os.path.join(self.config_dir, location.backend.id + '.rb'), 'w').write(c)

    def create_configuration(self, config):
        if os.path.exists(self.config_dir):
            shutil.rmtree(self.config_dir)
        os.mkdir(self.config_dir)

        sup = SupervisorConfig(path=platform_select(
            debian='/etc/supervisor/supervisord.conf',
            centos='/etc/supervisord.conf',
        ))
        sup.load()
        for p in sup.tree.programs:
            if p.command and p.command.startswith('unicorn'):
                sup.tree.programs.remove(p)

        for website in config.websites:
            if website.enabled:
                for location in website.locations:
                    if location.backend.type == 'ruby-unicorn':
                        self.__generate_website(website)
                        p = ProgramData()
                        p.name = location.backend.id
                        p.command = 'unicorn_rails -E production -c %s/%s.rb' % (self.config_dir, location.backend.id)
                        sup.tree.programs.append(p)

        sup.save()

    def apply_configuration(self):
        log_dir = '/var/log/unicorn'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        SupervisorRestartable.get().schedule()

########NEW FILE########
__FILENAME__ = vsftpd
import os
import subprocess
import shutil
import tempfile
import uuid

from ajenti.api import *
from ajenti.ui.binder import Binder
from ajenti.util import platform_select

from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.vh.api import MiscComponent
from ajenti.plugins.vh.extensions import BaseExtension


@plugin
class VSFTPDExtension (BaseExtension):
    default_config = {
        'created': False,
        'user': None,
        'password': None,
    }
    name = 'FTP'

    def init(self):
        self.append(self.ui.inflate('vh-vsftpd:ext'))
        self.binder = Binder(self, self)

        self.config['username'] = self.website.slug

        if not self.config['created']:
            self.config['password'] = str(uuid.uuid4())
            self.config['created'] = True

        self.refresh()

    def refresh(self):
        self.binder.setup().populate()

    def update(self):
        pass


TEMPLATE_CONFIG = """
listen=YES
anonymous_enable=NO
local_enable=YES
guest_enable=YES
guest_username=www-data
nopriv_user=www-data
anon_root=/
xferlog_enable=YES
virtual_use_local_privs=YES
pam_service_name=vsftpd_virtual
user_config_dir=%s
chroot_local_user=YES
hide_ids=YES

force_dot_files=YES
local_umask=002
chmod_enable=YES
file_open_mode=0755

seccomp_sandbox=NO

"""

TEMPLATE_PAM = """#%%PAM-1.0
auth    required        pam_userdb.so   db=/etc/vsftpd/users
account required        pam_userdb.so   db=/etc/vsftpd/users
session required        pam_loginuid.so
"""

TEMPLATE_USER = """
local_root=%(root)s
allow_writeable_chroot=YES
write_enable=YES
"""


@plugin
class VSFTPD (MiscComponent):
    config_root = '/etc/vsftpd'
    config_root_users = '/etc/vsftpd.users.d'
    config_file = platform_select(
        debian='/etc/vsftpd.conf',
        arch='/etc/vsftpd.conf',
        centos='/etc/vsftpd/vsftpd.conf',
    )
    userdb_path = '/etc/vsftpd/users.db'
    pam_path = '/etc/pam.d/vsftpd_virtual'

    def create_configuration(self, config):
        if not os.path.exists(self.config_root):
            os.mkdir(self.config_root)
        if os.path.exists(self.config_root_users):
            shutil.rmtree(self.config_root_users)
        os.mkdir(self.config_root_users)

        pwfile = tempfile.NamedTemporaryFile(delete=False)
        pwpath = pwfile.name
        for website in config.websites:
            subprocess.call(['chgrp', 'ftp', website.root])
            subprocess.call(['chmod', 'g+w', website.root])
            if website.enabled:
                cfg = website.extension_configs.get(VSFTPDExtension.classname)
                if cfg and cfg['created']:
                    pwfile.write('%s\n%s\n' % (cfg['username'], cfg['password']))
                    open(os.path.join(self.config_root_users, cfg['username']), 'w').write(
                        TEMPLATE_USER % {
                            'root': website.root,
                        }
                    )
        pwfile.close()

        subprocess.call(['db_load', '-T', '-t', 'hash', '-f', pwpath, self.userdb_path])
        os.unlink(pwpath)
        open(self.pam_path, 'w').write(TEMPLATE_PAM)
        open(self.config_file, 'w').write(TEMPLATE_CONFIG % self.config_root_users)

        if not os.path.exists('/var/www'):
            os.mkdir('/var/www')
        subprocess.call(['chown', 'www-data:', '/var/www'])

    def apply_configuration(self):
        ServiceMultiplexor.get().get_one('vsftpd').restart()

########NEW FILE########
