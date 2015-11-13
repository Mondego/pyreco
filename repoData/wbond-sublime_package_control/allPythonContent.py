__FILENAME__ = Package Control
import sublime
import sys
import os
import locale


st_version = 2

# Warn about out-dated versions of ST3
if sublime.version() == '':
    st_version = 3
    print('Package Control: Please upgrade to Sublime Text 3 build 3012 or newer')

elif int(sublime.version()) > 3000:
    st_version = 3


if st_version == 3:
    installed_dir, _ = __name__.split('.')
elif st_version == 2:
    installed_dir = os.path.basename(os.getcwd())


# Ensure the user has installed Package Control properly
if installed_dir != 'Package Control':
    message = (u"Package Control\n\nThis package appears to be installed " +
        u"incorrectly.\n\nIt should be installed as \"Package Control\", " +
        u"but seems to be installed as \"%s\".\n\n" % installed_dir)
    # If installed unpacked
    if os.path.exists(os.path.join(sublime.packages_path(), installed_dir)):
        message += (u"Please use the Preferences > Browse Packages... menu " +
            u"entry to open the \"Packages/\" folder and rename" +
            u"\"%s/\" to \"Package Control/\" " % installed_dir)
    # If installed as a .sublime-package file
    else:
        message += (u"Please use the Preferences > Browse Packages... menu " +
            u"entry to open the \"Packages/\" folder, then browse up a " +
            u"folder and into the \"Installed Packages/\" folder.\n\n" +
            u"Inside of \"Installed Packages/\", rename " +
            u"\"%s.sublime-package\" to " % installed_dir +
            u"\"Package Control.sublime-package\" ")
    message += u"and restart Sublime Text."
    sublime.error_message(message)

# Normal execution will finish setting up the package
else:
    reloader_name = 'package_control.reloader'

    # ST3 loads each package as a module, so it needs an extra prefix
    if st_version == 3:
        reloader_name = 'Package Control.' + reloader_name
        from imp import reload

    # Make sure all dependencies are reloaded on upgrade
    if reloader_name in sys.modules:
        reload(sys.modules[reloader_name])


    try:
        # Python 3
        from .package_control import reloader

        from .package_control.commands import *
        from .package_control.package_cleanup import PackageCleanup

    except (ValueError):
        # Python 2
        from package_control import reloader
        from package_control import sys_path

        from package_control.commands import *
        from package_control.package_cleanup import PackageCleanup


    def plugin_loaded():
        # Make sure the user's locale can handle non-ASCII. A whole bunch of
        # work was done to try and make Package Control work even if the locale
        # was poorly set, by manually encoding all file paths, but it ended up
        # being a fool's errand since the package loading code built into
        # Sublime Text is not written to work that way, and although packages
        # could be installed, they could not be loaded properly.
        try:
            os.path.exists(os.path.join(sublime.packages_path(), u"fran\u00e7ais"))
        except (UnicodeEncodeError) as e:
            message = (u"Package Control\n\nYour system's locale is set to a " +
                u"value that can not handle non-ASCII characters. Package " +
                u"Control can not properly work unless this is fixed.\n\n" +
                u"On Linux, please reference your distribution's docs for " +
                u"information on properly setting the LANG environmental " +
                u"variable. As a temporary work-around, you can launch " +
                u"Sublime Text from the terminal with:\n\n" +
                u"LANG=en_US.UTF-8 sublime_text")
            sublime.error_message(message)
            return

        # Start shortly after Sublime starts so package renames don't cause errors
        # with keybindings, settings, etc disappearing in the middle of parsing
        sublime.set_timeout(lambda: PackageCleanup().start(), 2000)

    if st_version == 2:
        plugin_loaded()

########NEW FILE########
__FILENAME__ = automatic_upgrader
import threading
import re
import os
import datetime
import time

import sublime

from .console_write import console_write
from .package_installer import PackageInstaller
from .package_renamer import PackageRenamer
from .open_compat import open_compat, read_compat


class AutomaticUpgrader(threading.Thread):
    """
    Automatically checks for updated packages and installs them. controlled
    by the `auto_upgrade`, `auto_upgrade_ignore`, and `auto_upgrade_frequency`
    settings.
    """

    def __init__(self, found_packages):
        """
        :param found_packages:
            A list of package names for the packages that were found to be
            installed on the machine.
        """

        self.installer = PackageInstaller()
        self.manager = self.installer.manager

        self.load_settings()

        self.package_renamer = PackageRenamer()
        self.package_renamer.load_settings()

        self.auto_upgrade = self.settings.get('auto_upgrade')
        self.auto_upgrade_ignore = self.settings.get('auto_upgrade_ignore')

        self.load_last_run()
        self.determine_next_run()

        # Detect if a package is missing that should be installed
        self.missing_packages = list(set(self.installed_packages) -
            set(found_packages))

        if self.auto_upgrade and self.next_run <= time.time():
            self.save_last_run(time.time())

        threading.Thread.__init__(self)

    def load_last_run(self):
        """
        Loads the last run time from disk into memory
        """

        self.last_run = None

        self.last_run_file = os.path.join(sublime.packages_path(), 'User',
            'Package Control.last-run')

        if os.path.isfile(self.last_run_file):
            with open_compat(self.last_run_file) as fobj:
                try:
                    self.last_run = int(read_compat(fobj))
                except ValueError:
                    pass

    def determine_next_run(self):
        """
        Figure out when the next run should happen
        """

        self.next_run = int(time.time())

        frequency = self.settings.get('auto_upgrade_frequency')
        if frequency:
            if self.last_run:
                self.next_run = int(self.last_run) + (frequency * 60 * 60)
            else:
                self.next_run = time.time()

    def save_last_run(self, last_run):
        """
        Saves a record of when the last run was

        :param last_run:
            The unix timestamp of when to record the last run as
        """

        with open_compat(self.last_run_file, 'w') as fobj:
            fobj.write(str(int(last_run)))


    def load_settings(self):
        """
        Loads the list of installed packages from the
        Package Control.sublime-settings file
        """

        self.settings_file = 'Package Control.sublime-settings'
        self.settings = sublime.load_settings(self.settings_file)
        self.installed_packages = self.settings.get('installed_packages', [])
        self.should_install_missing = self.settings.get('install_missing')
        if not isinstance(self.installed_packages, list):
            self.installed_packages = []

    def run(self):
        self.install_missing()

        if self.next_run > time.time():
            self.print_skip()
            return

        self.upgrade_packages()

    def install_missing(self):
        """
        Installs all packages that were listed in the list of
        `installed_packages` from Package Control.sublime-settings but were not
        found on the filesystem and passed as `found_packages`.
        """

        if not self.missing_packages or not self.should_install_missing:
            return

        console_write(u'Installing %s missing packages' % len(self.missing_packages), True)
        for package in self.missing_packages:
            if self.installer.manager.install_package(package):
                console_write(u'Installed missing package %s' % package, True)

    def print_skip(self):
        """
        Prints a notice in the console if the automatic upgrade is skipped
        due to already having been run in the last `auto_upgrade_frequency`
        hours.
        """

        last_run = datetime.datetime.fromtimestamp(self.last_run)
        next_run = datetime.datetime.fromtimestamp(self.next_run)
        date_format = '%Y-%m-%d %H:%M:%S'
        message_string = u'Skipping automatic upgrade, last run at %s, next run at %s or after' % (
            last_run.strftime(date_format), next_run.strftime(date_format))
        console_write(message_string, True)

    def upgrade_packages(self):
        """
        Upgrades all packages that are not currently upgraded to the lastest
        version. Also renames any installed packages to their new names.
        """

        if not self.auto_upgrade:
            return

        self.package_renamer.rename_packages(self.installer)

        package_list = self.installer.make_package_list(['install',
            'reinstall', 'downgrade', 'overwrite', 'none'],
            ignore_packages=self.auto_upgrade_ignore)

        # If Package Control is being upgraded, just do that and restart
        for package in package_list:
            if package[0] != 'Package Control':
                continue

            def reset_last_run():
                # Re-save the last run time so it runs again after PC has
                # been updated
                self.save_last_run(self.last_run)
            sublime.set_timeout(reset_last_run, 1)
            package_list = [package]
            break

        if not package_list:
            console_write(u'No updated packages', True)
            return

        console_write(u'Installing %s upgrades' % len(package_list), True)

        disabled_packages = []

        def do_upgrades():
            # Wait so that the ignored packages can be "unloaded"
            time.sleep(0.5)

            # We use a function to generate the on-complete lambda because if
            # we don't, the lambda will bind to info at the current scope, and
            # thus use the last value of info from the loop
            def make_on_complete(name):
                return lambda: self.installer.reenable_package(name)

            for info in package_list:
                if info[0] in disabled_packages:
                    on_complete = make_on_complete(info[0])
                else:
                    on_complete = None

                self.installer.manager.install_package(info[0])

                version = re.sub('^.*?(v[\d\.]+).*?$', '\\1', info[2])
                if version == info[2] and version.find('pull with') != -1:
                    vcs = re.sub('^pull with (\w+).*?$', '\\1', version)
                    version = 'latest %s commit' % vcs
                message_string = u'Upgraded %s to %s' % (info[0], version)
                console_write(message_string, True)
                if on_complete:
                    sublime.set_timeout(on_complete, 1)

        # Disabling a package means changing settings, which can only be done
        # in the main thread. We then create a new background thread so that
        # the upgrade process does not block the UI.
        def disable_packages():
            disabled_packages.extend(self.installer.disable_packages([info[0] for info in package_list]))
            threading.Thread(target=do_upgrades).start()
        sublime.set_timeout(disable_packages, 1)

########NEW FILE########
__FILENAME__ = cache
import time


# A cache of channel and repository info to allow users to install multiple
# packages without having to wait for the metadata to be downloaded more
# than once. The keys are managed locally by the utilizing code.
_channel_repository_cache = {}


def clear_cache():
    global _channel_repository_cache
    _channel_repository_cache = {}


def get_cache(key, default=None):
    """
    Gets an in-memory cache value

    :param key:
        The string key

    :param default:
        The value to return if the key has not been set, or the ttl expired

    :return:
        The cached value, or default
    """

    struct = _channel_repository_cache.get(key, {})
    expires = struct.get('expires')
    if expires and expires > time.time():
        return struct.get('data')
    return default


def merge_cache_over_settings(destination, setting, key_prefix):
    """
    Take the cached value of `key` and put it into the key `setting` of
    the destination.settings dict. Merge the values by overlaying the
    cached setting over the existing info.

    :param destination:
        An object that has a `.settings` attribute that is a dict

    :param setting:
        The dict key to use when pushing the value into the settings dict

    :param key_prefix:
        The string to prefix to `setting` to make the cache key
    """

    existing = destination.settings.get(setting, {})
    value = get_cache(key_prefix + '.' + setting, {})
    if value:
        existing.update(value)
        destination.settings[setting] = existing


def merge_cache_under_settings(destination, setting, key_prefix, list_=False):
    """
    Take the cached value of `key` and put it into the key `setting` of
    the destination.settings dict. Merge the values by overlaying the
    existing setting value over the cached info.

    :param destination:
        An object that has a `.settings` attribute that is a dict

    :param setting:
        The dict key to use when pushing the value into the settings dict

    :param key_prefix:
        The string to prefix to `setting` to make the cache key

    :param list_:
        If a list should be used instead of a dict
    """

    default = {} if not list_ else []
    existing = destination.settings.get(setting)
    value = get_cache(key_prefix + '.' + setting, default)
    if value:
        if existing:
            if list_:
                # Prevent duplicate values
                base = dict(zip(value, [None]*len(value)))
                for val in existing:
                    if val in base:
                        continue
                    value.append(val)
            else:
                value.update(existing)
        destination.settings[setting] = value


def set_cache(key, data, ttl=300):
    """
    Sets an in-memory cache value

    :param key:
        The string key

    :param data:
        The data to cache

    :param ttl:
        The integer number of second to cache the data for
    """

    _channel_repository_cache[key] = {
        'data': data,
        'expires': time.time() + ttl
    }


def set_cache_over_settings(destination, setting, key_prefix, value, ttl):
    """
    Take the value passed, and merge it over the current `setting`. Once
    complete, take the value and set the cache `key` and destination.settings
    `setting` to that value, using the `ttl` for set_cache().

    :param destination:
        An object that has a `.settings` attribute that is a dict

    :param setting:
        The dict key to use when pushing the value into the settings dict

    :param key_prefix:
        The string to prefix to `setting` to make the cache key

    :param value:
        The value to set

    :param ttl:
        The cache ttl to use
    """

    existing = destination.settings.get(setting, {})
    existing.update(value)
    set_cache(key_prefix + '.' + setting, value, ttl)
    destination.settings[setting] = value


def set_cache_under_settings(destination, setting, key_prefix, value, ttl, list_=False):
    """
    Take the value passed, and merge the current `setting` over it. Once
    complete, take the value and set the cache `key` and destination.settings
    `setting` to that value, using the `ttl` for set_cache().

    :param destination:
        An object that has a `.settings` attribute that is a dict

    :param setting:
        The dict key to use when pushing the value into the settings dict

    :param key_prefix:
        The string to prefix to `setting` to make the cache key

    :param value:
        The value to set

    :param ttl:
        The cache ttl to use
    """

    default = {} if not list_ else []
    existing = destination.settings.get(setting, default)
    if value:
        if list_:
            value.extend(existing)
        else:
            value.update(existing)
        set_cache(key_prefix + '.' + setting, value, ttl)
        destination.settings[setting] = value

########NEW FILE########
__FILENAME__ = ca_certs
import hashlib
import os
import re
import time
import sys

from .cmd import Cli
from .console_write import console_write
from .open_compat import open_compat, read_compat


# Have somewhere to store the CA bundle, even when not running in Sublime Text
try:
    import sublime
    ca_bundle_dir = None
except (ImportError):
    ca_bundle_dir = os.path.join(os.path.expanduser('~'), '.package_control')
    if not os.path.exists(ca_bundle_dir):
        os.mkdir(ca_bundle_dir)


def find_root_ca_cert(settings, domain):
    runner = OpensslCli(settings.get('openssl_binary'), settings.get('debug'))
    binary = runner.retrieve_binary()

    args = [binary, 's_client', '-showcerts', '-connect', domain + ':443']
    result = runner.execute(args, os.path.dirname(binary))

    certs = []
    temp = []

    in_block = False
    for line in result.splitlines():
        if line.find('BEGIN CERTIFICATE') != -1:
            in_block = True
        if in_block:
            temp.append(line)
        if line.find('END CERTIFICATE') != -1:
            in_block = False
            certs.append(u"\n".join(temp))
            temp = []

    # Grabbing the certs for the domain failed, most likely because it is down
    if not certs:
        return [False, False]

    # Remove the cert for the domain itself, just leaving the
    # chain cert and the CA cert
    certs.pop(0)

    # Look for the "parent" root CA cert
    subject = openssl_get_cert_subject(settings, certs[-1])
    issuer = openssl_get_cert_issuer(settings, certs[-1])

    cert = get_ca_cert_by_subject(settings, issuer)
    cert_hash = hashlib.md5(cert.encode('utf-8')).hexdigest()

    return [cert, cert_hash]



def get_system_ca_bundle_path(settings):
    """
    Get the filesystem path to the system CA bundle. On Linux it looks in a
    number of predefined places, however on OS X it has to be programatically
    exported from the SystemRootCertificates.keychain. Windows does not ship
    with a CA bundle, but also we use WinINet on Windows, so we don't need to
    worry about CA certs.

    :param settings:
        A dict to look in for `debug` and `openssl_binary` keys

    :return:
        The full filesystem path to the .ca-bundle file, or False on error
    """

    # If the sublime module is available, we bind this value at run time
    # since the sublime.packages_path() is not available at import time
    global ca_bundle_dir

    platform = sys.platform
    debug = settings.get('debug')

    ca_path = False

    if platform == 'win32':
        console_write(u"Unable to get system CA cert path since Windows does not ship with them", True)
        return False

    # OS X
    if platform == 'darwin':
        if not ca_bundle_dir:
            ca_bundle_dir = os.path.join(sublime.packages_path(), 'User')
        ca_path = os.path.join(ca_bundle_dir, 'Package Control.system-ca-bundle')

        exists = os.path.exists(ca_path)
        # The bundle is old if it is a week or more out of date
        is_old = exists and os.stat(ca_path).st_mtime < time.time() - 604800

        if not exists or is_old:
            if debug:
                console_write(u"Generating new CA bundle from system keychain", True)
            _osx_create_ca_bundle(settings, ca_path)
            if debug:
                console_write(u"Finished generating new CA bundle at %s" % ca_path, True)
        elif debug:
            console_write(u"Found previously exported CA bundle at %s" % ca_path, True)

    # Linux
    else:
        # Common CA cert paths
        paths = [
            '/usr/lib/ssl/certs/ca-certificates.crt',
            '/etc/ssl/certs/ca-certificates.crt',
            '/etc/pki/tls/certs/ca-bundle.crt',
            '/etc/ssl/ca-bundle.pem'
        ]
        for path in paths:
            if os.path.exists(path):
                ca_path = path
                break

        if debug and ca_path:
            console_write(u"Found system CA bundle at %s" % ca_path, True)

    return ca_path


def get_ca_cert_by_subject(settings, subject):
    bundle_path = get_system_ca_bundle_path(settings)

    with open_compat(bundle_path, 'r') as f:
        contents = read_compat(f)

    temp = []

    in_block = False
    for line in contents.splitlines():
        if line.find('BEGIN CERTIFICATE') != -1:
            in_block = True

        if in_block:
            temp.append(line)

        if line.find('END CERTIFICATE') != -1:
            in_block = False
            cert = u"\n".join(temp)
            temp = []

            if openssl_get_cert_subject(settings, cert) == subject:
                return cert

    return False


def openssl_get_cert_issuer(settings, cert):
    """
    Uses the openssl command line client to extract the issuer of an x509
    certificate.

    :param settings:
        A dict to look in for `debug` and `openssl_binary` keys

    :param cert:
        A string containing the PEM-encoded x509 certificate to extract the
        issuer from

    :return:
        The cert issuer
    """

    runner = OpensslCli(settings.get('openssl_binary'), settings.get('debug'))
    binary = runner.retrieve_binary()
    args = [binary, 'x509', '-noout', '-issuer']
    output = runner.execute(args, os.path.dirname(binary), cert)
    return re.sub('^issuer=\s*', '', output)


def openssl_get_cert_name(settings, cert):
    """
    Uses the openssl command line client to extract the name of an x509
    certificate. If the commonName is set, that is used, otherwise the first
    organizationalUnitName is used. This mirrors what OS X uses for storing
    trust preferences.

    :param settings:
        A dict to look in for `debug` and `openssl_binary` keys

    :param cert:
        A string containing the PEM-encoded x509 certificate to extract the
        name from

    :return:
        The cert subject name, which is the commonName (if available), or the
        first organizationalUnitName
    """

    runner = OpensslCli(settings.get('openssl_binary'), settings.get('debug'))

    binary = runner.retrieve_binary()

    args = [binary, 'x509', '-noout', '-subject', '-nameopt',
        'sep_multiline,lname,utf8']
    result = runner.execute(args, os.path.dirname(binary), cert)

    # First look for the common name
    cn = None
    # If there is no common name for the cert, the trust prefs use the first
    # orginizational unit name
    first_ou = None

    for line in result.splitlines():
        match = re.match('^\s+commonName=(.*)$', line)
        if match:
            cn = match.group(1)
            break
        match = re.match('^\s+organizationalUnitName=(.*)$', line)
        if first_ou is None and match:
            first_ou = match.group(1)
            continue

    # This is the name of the cert that would be used in the trust prefs
    return cn or first_ou


def openssl_get_cert_subject(settings, cert):
    """
    Uses the openssl command line client to extract the subject of an x509
    certificate.

    :param settings:
        A dict to look in for `debug` and `openssl_binary` keys

    :param cert:
        A string containing the PEM-encoded x509 certificate to extract the
        subject from

    :return:
        The cert subject
    """

    runner = OpensslCli(settings.get('openssl_binary'), settings.get('debug'))
    binary = runner.retrieve_binary()
    args = [binary, 'x509', '-noout', '-subject']
    output = runner.execute(args, os.path.dirname(binary), cert)
    return re.sub('^subject=\s*', '', output)


def _osx_create_ca_bundle(settings, destination):
    """
    Uses the OS X `security` command line tool to export the system's list of
    CA certs from /System/Library/Keychains/SystemRootCertificates.keychain.
    Checks the cert names against the trust preferences, ensuring that
    distrusted certs are not exported.

    :param settings:
        A dict to look in for `debug` and `openssl_binary` keys

    :param destination:
        The full filesystem path to the destination .ca-bundle file
    """

    distrusted_certs = _osx_get_distrusted_certs(settings)

    # Export the root certs
    args = ['/usr/bin/security', 'export', '-k',
        '/System/Library/Keychains/SystemRootCertificates.keychain', '-t',
        'certs', '-p']
    result = Cli(None, settings.get('debug')).execute(args, '/usr/bin')

    certs = []
    temp = []

    in_block = False
    for line in result.splitlines():
        if line.find('BEGIN CERTIFICATE') != -1:
            in_block = True

        if in_block:
            temp.append(line)

        if line.find('END CERTIFICATE') != -1:
            in_block = False
            cert = u"\n".join(temp)
            temp = []

            if distrusted_certs:
                # If it is a distrusted cert, we move on to the next
                cert_name = openssl_get_cert_name(settings, cert)
                if cert_name in distrusted_certs:
                    if settings.get('debug'):
                        console_write(u'Skipping root certficate %s because it is distrusted' % cert_name, True)
                    continue

            certs.append(cert)

    with open_compat(destination, 'w') as f:
        f.write(u"\n".join(certs))


def _osx_get_distrusted_certs(settings):
    """
    Uses the OS X `security` binary to get a list of admin trust settings,
    which is what is set when a user changes the trust setting on a root
    certificate. By looking at the SSL policy, we can properly exclude
    distrusted certs from out export.

    Tested on OS X 10.6 and 10.8

    :param settings:
        A dict to look in for `debug` key

    :return:
        A list of CA cert names, where the name is the commonName (if
        available), or the first organizationalUnitName
    """

    args = ['/usr/bin/security', 'dump-trust-settings', '-d']
    result = Cli(None, settings.get('debug')).execute(args, '/usr/bin')

    distrusted_certs = []
    cert_name = None
    ssl_policy = False
    for line in result.splitlines():
        if line == '':
            continue

        # Reset for each cert
        match = re.match('Cert\s+\d+:\s+(.*)$', line)
        if match:
            cert_name = match.group(1)
            continue

        # Reset for each trust setting
        if re.match('^\s+Trust\s+Setting\s+\d+:', line):
            ssl_policy = False
            continue

        # We are only interested in SSL policies
        if re.match('^\s+Policy\s+OID\s+:\s+SSL', line):
            ssl_policy = True
            continue

        distrusted = re.match('^\s+Result\s+Type\s+:\s+kSecTrustSettingsResultDeny', line)
        if ssl_policy and distrusted and cert_name not in distrusted_certs:
            if settings.get('debug'):
                console_write(u'Found SSL distrust setting for root certificate %s' % cert_name, True)
            distrusted_certs.append(cert_name)

    return distrusted_certs


class OpensslCli(Cli):

    cli_name = 'openssl'

    def retrieve_binary(self):
        """
        Returns the path to the openssl executable

        :return: The string path to the executable or False on error
        """

        name = 'openssl'
        if os.name == 'nt':
            name += '.exe'

        binary = self.find_binary(name)
        if binary and os.path.isdir(binary):
            full_path = os.path.join(binary, name)
            if os.path.exists(full_path):
                binary = full_path

        if not binary:
            show_error((u'Unable to find %s. Please set the openssl_binary ' +
                u'setting by accessing the Preferences > Package Settings > ' +
                u'Package Control > Settings \u2013 User menu entry. The ' +
                u'Settings \u2013 Default entry can be used for reference, ' +
                u'but changes to that will be overwritten upon next upgrade.') % name)
            return False

        return binary

########NEW FILE########
__FILENAME__ = clear_directory
import os


def clear_directory(directory, ignore_paths=None):
    """
    Tries to delete all files and folders from a directory

    :param directory:
        The string directory path

    :param ignore_paths:
        An array of paths to ignore while deleting files

    :return:
        If all of the files and folders were successfully deleted
    """

    was_exception = False
    for root, dirs, files in os.walk(directory, topdown=False):
        paths = [os.path.join(root, f) for f in files]
        paths.extend([os.path.join(root, d) for d in dirs])

        for path in paths:
            try:
                # Don't delete the metadata file, that way we have it
                # when the reinstall happens, and the appropriate
                # usage info can be sent back to the server
                if ignore_paths and path in ignore_paths:
                    continue
                if os.path.isdir(path):
                    os.rmdir(path)
                else:
                    os.remove(path)
            except (OSError, IOError):
                was_exception = True

    return not was_exception

########NEW FILE########
__FILENAME__ = bitbucket_client
import re

from ..versions import version_sort, version_filter
from .json_api_client import JSONApiClient


# A predefined list of readme filenames to look for
_readme_filenames = [
    'readme',
    'readme.txt',
    'readme.md',
    'readme.mkd',
    'readme.mdown',
    'readme.markdown',
    'readme.textile',
    'readme.creole',
    'readme.rst'
]


class BitBucketClient(JSONApiClient):

    def download_info(self, url):
        """
        Retrieve information about downloading a package

        :param url:
            The URL of the repository, in one of the forms:
              https://bitbucket.org/{user}/{repo}
              https://bitbucket.org/{user}/{repo}/src/{branch}
              https://bitbucket.org/{user}/{repo}/#tags
            If the last option, grabs the info from the newest
            tag that is a valid semver version.

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            None if no match, False if no commit, or a dict with the following keys:
              `version` - the version number of the download
              `url` - the download URL of a zip file of the package
              `date` - the ISO-8601 timestamp string when the version was published
        """

        commit_info = self._commit_info(url)
        if not commit_info:
            return commit_info

        return {
            'version': commit_info['version'],
            'url': 'https://bitbucket.org/%s/get/%s.zip' % (commit_info['user_repo'], commit_info['commit']),
            'date': commit_info['timestamp']
        }

    def repo_info(self, url):
        """
        Retrieve general information about a repository

        :param url:
            The URL to the repository, in one of the forms:
              https://bitbucket.org/{user}/{repo}
              https://bitbucket.org/{user}/{repo}/src/{branch}

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            None if no match, or a dict with the following keys:
              `name`
              `description`
              `homepage` - URL of the homepage
              `author`
              `readme` - URL of the readme
              `issues` - URL of bug tracker
              `donate` - URL of a donate page
        """

        user_repo, branch = self._user_repo_branch(url)
        if not user_repo:
            return user_repo

        api_url = self._make_api_url(user_repo)

        info = self.fetch_json(api_url)

        issues_url = u'https://bitbucket.org/%s/issues' % user_repo

        return {
            'name': info['name'],
            'description': info['description'] or 'No description provided',
            'homepage': info['website'] or url,
            'author': info['owner'],
            'donate': u'https://www.gittip.com/on/bitbucket/%s/' % info['owner'],
            'readme': self._readme_url(user_repo, branch),
            'issues': issues_url if info['has_issues'] else None
        }

    def _commit_info(self, url):
        """
        Fetches info about the latest commit to a repository

        :param url:
            The URL to the repository, in one of the forms:
              https://bitbucket.org/{user}/{repo}
              https://bitbucket.org/{user}/{repo}/src/{branch}
              https://bitbucket.org/{user}/{repo}/#tags
            If the last option, grabs the info from the newest
            tag that is a valid semver version.

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            None if no match, False if no commit, or a dict with the following keys:
              `user_repo` - the user/repo name
              `timestamp` - the ISO-8601 UTC timestamp string
              `commit` - the branch or tag name
              `version` - the extracted version number
        """

        tags_match = re.match('https?://bitbucket.org/([^/]+/[^#/]+)/?#tags$', url)

        version = None

        if tags_match:
            user_repo = tags_match.group(1)
            tags_url = self._make_api_url(user_repo, '/tags')
            tags_list = self.fetch_json(tags_url)
            tags = version_filter(tags_list.keys(), self.settings.get('install_prereleases'))
            tags = version_sort(tags, reverse=True)
            if not tags:
                return False
            commit = tags[0]
            version = re.sub('^v', '', commit)

        else:
            user_repo, commit = self._user_repo_branch(url)
            if not user_repo:
                return user_repo

        changeset_url = self._make_api_url(user_repo, '/changesets/%s' % commit)
        commit_info = self.fetch_json(changeset_url)

        commit_date = commit_info['timestamp'][0:19]

        if not version:
            version = re.sub('[\-: ]', '.', commit_date)

        return {
            'user_repo': user_repo,
            'timestamp': commit_date,
            'commit': commit,
            'version': version
        }

    def _main_branch_name(self, user_repo):
        """
        Fetch the name of the default branch

        :param user_repo:
            The user/repo name to get the main branch for

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            The name of the main branch - `master` or `default`
        """

        main_branch_url = self._make_api_url(user_repo, '/main-branch')
        main_branch_info = self.fetch_json(main_branch_url, True)
        return main_branch_info['name']

    def _make_api_url(self, user_repo, suffix=''):
        """
        Generate a URL for the BitBucket API

        :param user_repo:
            The user/repo of the repository

        :param suffix:
            The extra API path info to add to the URL

        :return:
            The API URL
        """

        return 'https://api.bitbucket.org/1.0/repositories/%s%s' % (user_repo, suffix)

    def _readme_url(self, user_repo, branch, prefer_cached=False):
        """
        Parse the root directory listing for the repo and return the URL
        to any file that looks like a readme

        :param user_repo:
            The user/repo string

        :param branch:
            The branch to fetch the readme from

        :param prefer_cached:
            If a cached directory listing should be used instead of a new HTTP request

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            The URL to the readme file, or None
        """

        listing_url = self._make_api_url(user_repo, '/src/%s/' % branch)
        root_dir_info = self.fetch_json(listing_url, prefer_cached)

        for entry in root_dir_info['files']:
            if entry['path'].lower() in _readme_filenames:
                return 'https://bitbucket.org/%s/raw/%s/%s' % (user_repo,
                    branch, entry['path'])

        return None

    def _user_repo_branch(self, url):
        """
        Extract the username/repo and branch name from the URL

        :param url:
            The URL to extract the info from, in one of the forms:
              https://bitbucket.org/{user}/{repo}
              https://bitbucket.org/{user}/{repo}/src/{branch}

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            A tuple of (user/repo, branch name) or (None, None) if not matching
        """

        repo_match = re.match('https?://bitbucket.org/([^/]+/[^/]+)/?$', url)
        branch_match = re.match('https?://bitbucket.org/([^/]+/[^/]+)/src/([^/]+)/?$', url)

        if repo_match:
            user_repo = repo_match.group(1)
            branch = self._main_branch_name(user_repo)

        elif branch_match:
            user_repo = branch_match.group(1)
            branch = branch_match.group(2)

        else:
            return (None, None)

        return (user_repo, branch)

########NEW FILE########
__FILENAME__ = client_exception
class ClientException(Exception):
    """If a client could not fetch information"""

    def __str__(self):
        return self.args[0]

########NEW FILE########
__FILENAME__ = github_client
import re

try:
    # Python 3
    from urllib.parse import urlencode, quote
except (ImportError):
    # Python 2
    from urllib import urlencode, quote

from ..versions import version_sort, version_filter
from .json_api_client import JSONApiClient
from ..downloaders.downloader_exception import DownloaderException


class GitHubClient(JSONApiClient):

    def download_info(self, url):
        """
        Retrieve information about downloading a package

        :param url:
            The URL of the repository, in one of the forms:
              https://github.com/{user}/{repo}
              https://github.com/{user}/{repo}/tree/{branch}
              https://github.com/{user}/{repo}/tags
            If the last option, grabs the info from the newest
            tag that is a valid semver version.

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            None if no match, False if no commit, or a dict with the following keys:
              `version` - the version number of the download
              `url` - the download URL of a zip file of the package
              `date` - the ISO-8601 timestamp string when the version was published
        """

        commit_info = self._commit_info(url)
        if not commit_info:
            return commit_info

        return {
            'version': commit_info['version'],
            # We specifically use codeload.github.com here because the download
            # URLs all redirect there, and some of the downloaders don't follow
            # HTTP redirect headers
            'url': 'https://codeload.github.com/%s/zip/%s' % (commit_info['user_repo'], quote(commit_info['commit'])),
            'date': commit_info['timestamp']
        }

    def repo_info(self, url):
        """
        Retrieve general information about a repository

        :param url:
            The URL to the repository, in one of the forms:
              https://github.com/{user}/{repo}
              https://github.com/{user}/{repo}/tree/{branch}

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            None if no match, or a dict with the following keys:
              `name`
              `description`
              `homepage` - URL of the homepage
              `author`
              `readme` - URL of the readme
              `issues` - URL of bug tracker
              `donate` - URL of a donate page
        """

        user_repo, branch = self._user_repo_branch(url)
        if not user_repo:
            return user_repo

        api_url = self._make_api_url(user_repo)

        info = self.fetch_json(api_url)

        output = self._extract_repo_info(info)
        output['readme'] = None

        readme_info = self._readme_info(user_repo, branch)
        if not readme_info:
            return output

        output['readme'] = 'https://raw.github.com/%s/%s/%s' % (user_repo,
            branch, readme_info['path'])
        return output

    def user_info(self, url):
        """
        Retrieve general information about all repositories that are
        part of a user/organization.

        :param url:
            The URL to the user/organization, in the following form:
              https://github.com/{user}

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            None if no match, or am list of dicts with the following keys:
              `name`
              `description`
              `homepage` - URL of the homepage
              `author`
              `readme` - URL of the readme
              `issues` - URL of bug tracker
              `donate` - URL of a donate page
        """

        user_match = re.match('https?://github.com/([^/]+)/?$', url)
        if user_match == None:
            return None

        user = user_match.group(1)
        api_url = self._make_api_url(user)

        repos_info = self.fetch_json(api_url)

        output = []
        for info in repos_info:
            output.append(self._extract_repo_info(info))
        return output

    def _commit_info(self, url):
        """
        Fetches info about the latest commit to a repository

        :param url:
            The URL to the repository, in one of the forms:
              https://github.com/{user}/{repo}
              https://github.com/{user}/{repo}/tree/{branch}
              https://github.com/{user}/{repo}/tags
            If the last option, grabs the info from the newest
            tag that is a valid semver version.

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            None if no match, False is no commit, or a dict with the following keys:
              `user_repo` - the user/repo name
              `timestamp` - the ISO-8601 UTC timestamp string
              `commit` - the branch or tag name
              `version` - the extracted version number
        """

        tags_match = re.match('https?://github.com/([^/]+/[^/]+)/tags/?$', url)

        version = None

        if tags_match:
            user_repo = tags_match.group(1)
            tags_url = self._make_api_url(user_repo, '/tags')
            tags_list = self.fetch_json(tags_url)
            tags = [tag['name'] for tag in tags_list]
            tags = version_filter(tags, self.settings.get('install_prereleases'))
            tags = version_sort(tags, reverse=True)
            if not tags:
                return False
            commit = tags[0]
            version = re.sub('^v', '', commit)

        else:
            user_repo, commit = self._user_repo_branch(url)
            if not user_repo:
                return user_repo

        query_string = urlencode({'sha': commit, 'per_page': 1})
        commit_url = self._make_api_url(user_repo, '/commits?%s' % query_string)
        commit_info = self.fetch_json(commit_url)

        commit_date = commit_info[0]['commit']['committer']['date'][0:19].replace('T', ' ')

        if not version:
            version = re.sub('[\-: ]', '.', commit_date)

        return {
            'user_repo': user_repo,
            'timestamp': commit_date,
            'commit': commit,
            'version': version
        }

    def _extract_repo_info(self, result):
        """
        Extracts information about a repository from the API result

        :param result:
            A dict representing the data returned from the GitHub API

        :return:
            A dict with the following keys:
              `name`
              `description`
              `homepage` - URL of the homepage
              `author`
              `issues` - URL of bug tracker
              `donate` - URL of a donate page
        """

        issues_url = u'https://github.com/%s/%s/issues' % (result['owner']['login'], result['name'])

        return {
            'name': result['name'],
            'description': result['description'] or 'No description provided',
            'homepage': result['homepage'] or result['html_url'],
            'author': result['owner']['login'],
            'issues': issues_url if result['has_issues'] else None,
            'donate': u'https://www.gittip.com/on/github/%s/' % result['owner']['login']
        }

    def _make_api_url(self, user_repo, suffix=''):
        """
        Generate a URL for the BitBucket API

        :param user_repo:
            The user/repo of the repository

        :param suffix:
            The extra API path info to add to the URL

        :return:
            The API URL
        """

        return 'https://api.github.com/repos/%s%s' % (user_repo, suffix)

    def _readme_info(self, user_repo, branch, prefer_cached=False):
        """
        Fetches the raw GitHub API information about a readme

        :param user_repo:
            The user/repo of the repository

        :param branch:
            The branch to pull the readme from

        :param prefer_cached:
            If a cached version of the info should be returned instead of making a new HTTP request

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            A dict containing all of the info from the GitHub API, or None if no readme exists
        """

        query_string = urlencode({'ref': branch})
        readme_url = self._make_api_url(user_repo, '/readme?%s' % query_string)
        try:
            return self.fetch_json(readme_url, prefer_cached)
        except (DownloaderException) as e:
            if str(e).find('HTTP error 404') != -1:
                return None
            raise

    def _user_repo_branch(self, url):
        """
        Extract the username/repo and branch name from the URL

        :param url:
            The URL to extract the info from, in one of the forms:
              https://github.com/{user}/{repo}
              https://github.com/{user}/{repo}/tree/{branch}

        :return:
            A tuple of (user/repo, branch name) or (None, None) if no match
        """

        branch = 'master'
        branch_match = re.match('https?://github.com/[^/]+/[^/]+/tree/([^/]+)/?$', url)
        if branch_match != None:
            branch = branch_match.group(1)

        repo_match = re.match('https?://github.com/([^/]+/[^/]+)($|/.*$)', url)
        if repo_match == None:
            return (None, None)

        user_repo = repo_match.group(1)
        return (user_repo, branch)

########NEW FILE########
__FILENAME__ = json_api_client
import json

try:
    # Python 3
    from urllib.parse import urlencode, urlparse
except (ImportError):
    # Python 2
    from urllib import urlencode
    from urlparse import urlparse

from .client_exception import ClientException
from ..download_manager import downloader


class JSONApiClient():
    def __init__(self, settings):
        self.settings = settings

    def fetch(self, url, prefer_cached=False):
        """
        Retrieves the contents of a URL

        :param url:
            The URL to download the content from

        :param prefer_cached:
            If a cached copy of the content is preferred

        :return: The bytes/string
        """

        # If there are extra params for the domain name, add them
        extra_params = self.settings.get('query_string_params')
        domain_name = urlparse(url).netloc
        if extra_params and domain_name in extra_params:
            params = urlencode(extra_params[domain_name])
            joiner = '?%s' if url.find('?') == -1 else '&%s'
            url += joiner % params

        with downloader(url, self.settings) as manager:
            content = manager.fetch(url, 'Error downloading repository.',
                prefer_cached)
        return content

    def fetch_json(self, url, prefer_cached=False):
        """
        Retrieves and parses the JSON from a URL

        :param url:
            The URL to download the JSON from

        :param prefer_cached:
            If a cached copy of the JSON is preferred

        :return: A dict or list from the JSON
        """

        repository_json = self.fetch(url, prefer_cached)

        try:
            return json.loads(repository_json.decode('utf-8'))
        except (ValueError):
            error_string = u'Error parsing JSON from URL %s.' % url
            raise ClientException(error_string)

########NEW FILE########
__FILENAME__ = readme_client
import re
import os
import base64

try:
    # Python 3
    from urllib.parse import urlencode
except (ImportError):
    # Python 2
    from urllib import urlencode

from .json_api_client import JSONApiClient
from ..downloaders.downloader_exception import DownloaderException


# Used to map file extensions to formats
_readme_formats = {
    '.md': 'markdown',
    '.mkd': 'markdown',
    '.mdown': 'markdown',
    '.markdown': 'markdown',
    '.textile': 'textile',
    '.creole': 'creole',
    '.rst': 'rst'
}


class ReadmeClient(JSONApiClient):

    def readme_info(self, url):
        """
        Retrieve the readme and info about it

        :param url:
            The URL of the readme file

        :raises:
            DownloaderException: if there is an error downloading the readme
            ClientException: if there is an error parsing the response

        :return:
            A dict with the following keys:
              `filename`
              `format` - `markdown`, `textile`, `creole`, `rst` or `txt`
              `contents` - contents of the readme as str/unicode
        """

        contents = None

        # Try to grab the contents of a GitHub-based readme by grabbing the cached
        # content of the readme API call
        github_match = re.match('https://raw.github.com/([^/]+/[^/]+)/([^/]+)/readme(\.(md|mkd|mdown|markdown|textile|creole|rst|txt))?$', url, re.I)
        if github_match:
            user_repo = github_match.group(1)
            branch = github_match.group(2)

            query_string = urlencode({'ref': branch})
            readme_json_url = 'https://api.github.com/repos/%s/readme?%s' % (user_repo, query_string)
            try:
                info = self.fetch_json(readme_json_url, prefer_cached=True)
                contents = base64.b64decode(info['content'])
            except (ValueError) as e:
                pass

        if not contents:
            contents = self.fetch(url)

        basename, ext = os.path.splitext(url)
        format = 'txt'
        ext = ext.lower()
        if ext in _readme_formats:
            format = _readme_formats[ext]

        try:
            contents = contents.decode('utf-8')
        except (UnicodeDecodeError) as e:
            contents = contents.decode('cp1252', errors='replace')

        return {
            'filename': os.path.basename(url),
            'format': format,
            'contents': contents
        }

########NEW FILE########
__FILENAME__ = cmd
import os
import subprocess
import re

if os.name == 'nt':
    from ctypes import windll, create_unicode_buffer

from .console_write import console_write
from .unicode import unicode_from_os
from .show_error import show_error

try:
    # Python 2
    str_cls = unicode
except (NameError):
    # Python 3
    str_cls = str


def create_cmd(args, basename_binary=False):
    """
    Takes an array of strings to be passed to subprocess.Popen and creates
    a string that can be pasted into a terminal

    :param args:
        The array containing the binary name/path and all arguments

    :param basename_binary:
        If only the basename of the binary should be disabled instead of the full path

    :return:
        The command string
    """

    if basename_binary:
        args[0] = os.path.basename(args[0])

    if os.name == 'nt':
        return subprocess.list2cmdline(args)
    else:
        escaped_args = []
        for arg in args:
            if re.search('^[a-zA-Z0-9/_^\\-\\.:=]+$', arg) == None:
                arg = u"'" + arg.replace(u"'", u"'\\''") + u"'"
            escaped_args.append(arg)
        return u' '.join(escaped_args)


class Cli(object):
    """
    Base class for running command line apps

    :param binary:
        The full filesystem path to the executable for the version control
        system. May be set to None to allow the code to try and find it.
    """

    cli_name = None

    def __init__(self, binary, debug):
        self.binary = binary
        self.debug = debug

    def execute(self, args, cwd, input=None):
        """
        Creates a subprocess with the executable/args

        :param args:
            A list of the executable path and all arguments to it

        :param cwd:
            The directory in which to run the executable

        :param input:
            The input text to send to the program

        :return: A string of the executable output
        """

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            # Make sure the cwd is ascii
            try:
                cwd.encode('ascii')
            except UnicodeEncodeError:
                buf = create_unicode_buffer(512)
                if windll.kernel32.GetShortPathNameW(cwd, buf, len(buf)):
                    cwd = buf.value

        if self.debug:
            console_write(u"Trying to execute command %s" % create_cmd(args), True)

        try:
            proc = subprocess.Popen(args, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                startupinfo=startupinfo, cwd=cwd)

            if input and isinstance(input, str_cls):
                input = input.encode('utf-8')
            output, _ = proc.communicate(input)
            output = output.decode('utf-8')
            output = output.replace('\r\n', '\n').rstrip(' \n\r')

            return output

        except (OSError) as e:
            cmd = create_cmd(args)
            error = unicode_from_os(e)
            message = u"Error executing: %s\n%s\n\nTry checking your \"%s_binary\" setting?" % (cmd, error, self.cli_name)
            show_error(message)
            return False

    def find_binary(self, name):
        """
        Locates the executable by looking in the PATH and well-known directories

        :param name:
            The string filename of the executable

        :return: The filesystem path to the executable, or None if not found
        """

        if self.binary:
            if self.debug:
                error_string = u"Using \"%s_binary\" from settings \"%s\"" % (
                    self.cli_name, self.binary)
                console_write(error_string, True)
            return self.binary

        # Try the path first
        for dir_ in os.environ['PATH'].split(os.pathsep):
            path = os.path.join(dir_, name)
            if os.path.exists(path):
                if self.debug:
                    console_write(u"Found %s at \"%s\"" % (self.cli_name, path), True)
                return path

        # This is left in for backwards compatibility and for windows
        # users who may have the binary, albeit in a common dir that may
        # not be part of the PATH
        if os.name == 'nt':
            dirs = ['C:\\Program Files\\Git\\bin',
                'C:\\Program Files (x86)\\Git\\bin',
                'C:\\Program Files\\TortoiseGit\\bin',
                'C:\\Program Files\\Mercurial',
                'C:\\Program Files (x86)\\Mercurial',
                'C:\\Program Files (x86)\\TortoiseHg',
                'C:\\Program Files\\TortoiseHg',
                'C:\\cygwin\\bin']
        else:
            # ST seems to launch with a minimal set of environmental variables
            # on OS X, so we add some common paths for it
            dirs = ['/usr/local/git/bin', '/usr/local/bin']

        for dir_ in dirs:
            path = os.path.join(dir_, name)
            if os.path.exists(path):
                if self.debug:
                    console_write(u"Found %s at \"%s\"" % (self.cli_name, path), True)
                return path

        if self.debug:
            console_write(u"Could not find %s on your machine" % self.cli_name, True)
        return None

########NEW FILE########
__FILENAME__ = add_channel_command
import re

import sublime
import sublime_plugin

from ..show_error import show_error


class AddChannelCommand(sublime_plugin.WindowCommand):
    """
    A command to add a new channel (list of repositories) to the user's machine
    """

    def run(self):
        self.window.show_input_panel('Channel JSON URL', '',
            self.on_done, self.on_change, self.on_cancel)

    def on_done(self, input):
        """
        Input panel handler - adds the provided URL as a channel

        :param input:
            A string of the URL to the new channel
        """

        input = input.strip()

        if re.match('https?://', input, re.I) == None:
            show_error(u"Unable to add the channel \"%s\" since it does not appear to be served via HTTP (http:// or https://)." % input)
            return

        settings = sublime.load_settings('Package Control.sublime-settings')
        channels = settings.get('channels', [])
        if not channels:
            channels = []
        channels.append(input)
        settings.set('channels', channels)
        sublime.save_settings('Package Control.sublime-settings')
        sublime.status_message(('Channel %s successfully ' +
            'added') % input)

    def on_change(self, input):
        pass

    def on_cancel(self):
        pass

########NEW FILE########
__FILENAME__ = add_repository_command
import re

import sublime
import sublime_plugin

from ..show_error import show_error


class AddRepositoryCommand(sublime_plugin.WindowCommand):
    """
    A command to add a new repository to the user's machine
    """

    def run(self):
        self.window.show_input_panel('GitHub or BitBucket Web URL, or Custom' +
                ' JSON Repository URL', '', self.on_done,
            self.on_change, self.on_cancel)

    def on_done(self, input):
        """
        Input panel handler - adds the provided URL as a repository

        :param input:
            A string of the URL to the new repository
        """
        
        input = input.strip()
        
        if re.match('https?://', input, re.I) == None:
            show_error(u"Unable to add the repository \"%s\" since it does not appear to be served via HTTP (http:// or https://)." % input)
            return

        settings = sublime.load_settings('Package Control.sublime-settings')
        repositories = settings.get('repositories', [])
        if not repositories:
            repositories = []
        repositories.append(input)
        settings.set('repositories', repositories)
        sublime.save_settings('Package Control.sublime-settings')
        sublime.status_message('Repository %s successfully added' % input)

    def on_change(self, input):
        pass

    def on_cancel(self):
        pass

########NEW FILE########
__FILENAME__ = create_package_command
import sublime_plugin

from ..package_creator import PackageCreator


class CreatePackageCommand(sublime_plugin.WindowCommand, PackageCreator):
    """
    Command to create a regular .sublime-package file
    """

    def run(self):
        self.show_panel()

########NEW FILE########
__FILENAME__ = disable_package_command
import sublime
import sublime_plugin

from ..show_error import show_error
from ..package_manager import PackageManager
from ..preferences_filename import preferences_filename


class DisablePackageCommand(sublime_plugin.WindowCommand):
    """
    A command that adds a package to Sublime Text's ignored packages list
    """

    def run(self):
        manager = PackageManager()
        packages = manager.list_all_packages()
        self.settings = sublime.load_settings(preferences_filename())
        ignored = self.settings.get('ignored_packages')
        if not ignored:
            ignored = []
        self.package_list = list(set(packages) - set(ignored))
        self.package_list.sort()
        if not self.package_list:
            show_error('There are no enabled packages to disable.')
            return
        self.window.show_quick_panel(self.package_list, self.on_done)

    def on_done(self, picked):
        """
        Quick panel user selection handler - disables the selected package

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return
        package = self.package_list[picked]
        ignored = self.settings.get('ignored_packages')
        if not ignored:
            ignored = []
        ignored.append(package)
        self.settings.set('ignored_packages', ignored)
        sublime.save_settings(preferences_filename())
        sublime.status_message(('Package %s successfully added to list of ' +
            'disabled packages - restarting Sublime Text may be required') %
            package)

########NEW FILE########
__FILENAME__ = discover_packages_command
import sublime_plugin


class DiscoverPackagesCommand(sublime_plugin.WindowCommand):
    """
    A command that opens the community package list webpage
    """

    def run(self):
        self.window.run_command('open_url',
            {'url': 'http://wbond.net/sublime_packages/community'})

########NEW FILE########
__FILENAME__ = enable_package_command
import sublime
import sublime_plugin

from ..show_error import show_error
from ..preferences_filename import preferences_filename


class EnablePackageCommand(sublime_plugin.WindowCommand):
    """
    A command that removes a package from Sublime Text's ignored packages list
    """

    def run(self):
        self.settings = sublime.load_settings(preferences_filename())
        self.disabled_packages = self.settings.get('ignored_packages')
        self.disabled_packages.sort()
        if not self.disabled_packages:
            show_error('There are no disabled packages to enable.')
            return
        self.window.show_quick_panel(self.disabled_packages, self.on_done)

    def on_done(self, picked):
        """
        Quick panel user selection handler - enables the selected package

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return
        package = self.disabled_packages[picked]
        ignored = self.settings.get('ignored_packages')
        self.settings.set('ignored_packages',
            list(set(ignored) - set([package])))
        sublime.save_settings(preferences_filename())
        sublime.status_message(('Package %s successfully removed from list ' +
            'of disabled packages - restarting Sublime Text may be required') %
            package)

########NEW FILE########
__FILENAME__ = existing_packages_command
import os
import re

import sublime

from ..package_manager import PackageManager


class ExistingPackagesCommand():
    """
    Allows listing installed packages and their current version
    """

    def __init__(self):
        self.manager = PackageManager()

    def make_package_list(self, action=''):
        """
        Returns a list of installed packages suitable for displaying in the
        quick panel.

        :param action:
            An action to display at the beginning of the third element of the
            list returned for each package

        :return:
            A list of lists, each containing three strings:
              0 - package name
              1 - package description
              2 - [action] installed version; package url
        """

        packages = self.manager.list_packages()

        if action:
            action += ' '

        package_list = []
        for package in sorted(packages, key=lambda s: s.lower()):
            package_entry = [package]
            metadata = self.manager.get_metadata(package)
            package_dir = os.path.join(sublime.packages_path(), package)

            description = metadata.get('description')
            if not description:
                description = 'No description provided'
            package_entry.append(description)

            version = metadata.get('version')
            if not version and os.path.exists(os.path.join(package_dir,
                    '.git')):
                installed_version = 'git repository'
            elif not version and os.path.exists(os.path.join(package_dir,
                    '.hg')):
                installed_version = 'hg repository'
            else:
                installed_version = 'v' + version if version else \
                    'unknown version'

            url = metadata.get('url')
            if url:
                url = '; ' + re.sub('^https?://', '', url)
            else:
                url = ''

            package_entry.append(action + installed_version + url)
            package_list.append(package_entry)

        return package_list

########NEW FILE########
__FILENAME__ = grab_certs_command
import os
import re
import socket
import threading

try:
    # Python 3
    from urllib.parse import urlparse
except (ImportError):
    # Python 2
    from urlparse import urlparse

import sublime
import sublime_plugin

from ..show_error import show_error
from ..open_compat import open_compat
from ..ca_certs import find_root_ca_cert
from ..thread_progress import ThreadProgress
from ..package_manager import PackageManager


class GrabCertsCommand(sublime_plugin.WindowCommand):
    """
    A command that extracts the CA certs for a domain name, allowing a user to
    fetch packages from sources other than those used by the default channel
    """

    def run(self):
        panel = self.window.show_input_panel('Domain Name', 'example.com', self.on_done,
            None, None)
        panel.sel().add(sublime.Region(0, panel.size()))

    def on_done(self, domain):
        """
        Input panel handler - grabs the CA certs for the domain name presented

        :param domain:
            A string of the domain name
        """

        domain = domain.strip()

        # Make sure the user enters something
        if domain == '':
            show_error(u"Please enter a domain name, or press cancel")
            self.run()
            return

        # If the user inputs a URL, extract the domain name
        if domain.find('/') != -1:
            parts = urlparse(domain)
            if parts.hostname:
                domain = parts.hostname

        # Allow _ even though it technically isn't valid, this is really
        # just to try and prevent people from typing in gibberish
        if re.match('^(?:[a-zA-Z0-9]+(?:[\-_]*[a-zA-Z0-9]+)*\.)+[a-zA-Z]{2,6}$', domain, re.I) == None:
            show_error(u"Unable to get the CA certs for \"%s\" since it does not appear to be a validly formed domain name" % domain)
            return

        # Make sure it is a real domain
        try:
            socket.gethostbyname(domain)
        except (socket.gaierror) as e:
            error = unicode_from_os(e)
            show_error(u"Error trying to lookup \"%s\":\n\n%s" % (domain, error))
            return

        manager = PackageManager()

        thread = GrabCertsThread(manager.settings, domain)
        thread.start()
        ThreadProgress(thread, 'Grabbing CA certs for %s' % domain,
            'CA certs for %s added to settings' % domain)


class GrabCertsThread(threading.Thread):
    """
    A thread to run openssl so that the Sublime Text UI does not become frozen
    """

    def __init__(self, settings, domain):
        self.settings = settings
        self.domain = domain
        threading.Thread.__init__(self)

    def run(self):
        cert, cert_hash = find_root_ca_cert(self.settings, self.domain)

        certs_dir = os.path.join(sublime.packages_path(), 'User',
            'Package Control.ca-certs')
        if not os.path.exists(certs_dir):
            os.mkdir(certs_dir)

        cert_path = os.path.join(certs_dir, self.domain + '-ca.crt')
        with open_compat(cert_path, 'w') as f:
            f.write(cert)

        def save_certs():
            settings = sublime.load_settings('Package Control.sublime-settings')
            certs = settings.get('certs', {})
            if not certs:
                certs = {}
            certs[self.domain] = [cert_hash, cert_path]
            settings.set('certs', certs)
            sublime.save_settings('Package Control.sublime-settings')

        sublime.set_timeout(save_certs, 10)

########NEW FILE########
__FILENAME__ = install_package_command
import threading

import sublime
import sublime_plugin

from ..show_error import show_error
from ..package_installer import PackageInstaller
from ..thread_progress import ThreadProgress


class InstallPackageCommand(sublime_plugin.WindowCommand):
    """
    A command that presents the list of available packages and allows the
    user to pick one to install.
    """

    def run(self):
        thread = InstallPackageThread(self.window)
        thread.start()
        ThreadProgress(thread, 'Loading repositories', '')


class InstallPackageThread(threading.Thread, PackageInstaller):
    """
    A thread to run the action of retrieving available packages in. Uses the
    default PackageInstaller.on_done quick panel handler.
    """

    def __init__(self, window):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the available package list in.
        """

        self.window = window
        self.completion_type = 'installed'
        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        self.package_list = self.make_package_list(['upgrade', 'downgrade',
            'reinstall', 'pull', 'none'])

        def show_quick_panel():
            if not self.package_list:
                show_error('There are no packages available for installation')
                return
            self.window.show_quick_panel(self.package_list, self.on_done)
        sublime.set_timeout(show_quick_panel, 10)

########NEW FILE########
__FILENAME__ = list_packages_command
import threading
import os

import sublime
import sublime_plugin

from ..show_error import show_error
from .existing_packages_command import ExistingPackagesCommand


class ListPackagesCommand(sublime_plugin.WindowCommand):
    """
    A command that shows a list of all installed packages in the quick panel
    """

    def run(self):
        ListPackagesThread(self.window).start()


class ListPackagesThread(threading.Thread, ExistingPackagesCommand):
    """
    A thread to prevent the listing of existing packages from freezing the UI
    """

    def __init__(self, window):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the list of installed packages in.
        """

        self.window = window
        threading.Thread.__init__(self)
        ExistingPackagesCommand.__init__(self)

    def run(self):
        self.package_list = self.make_package_list()

        def show_quick_panel():
            if not self.package_list:
                show_error('There are no packages to list')
                return
            self.window.show_quick_panel(self.package_list, self.on_done)
        sublime.set_timeout(show_quick_panel, 10)

    def on_done(self, picked):
        """
        Quick panel user selection handler - opens the homepage for any
        selected package in the user's browser

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return
        package_name = self.package_list[picked][0]

        def open_dir():
            self.window.run_command('open_dir',
                {"dir": os.path.join(sublime.packages_path(), package_name)})
        sublime.set_timeout(open_dir, 10)

########NEW FILE########
__FILENAME__ = package_message_command
import sublime
import sublime_plugin


class PackageMessageCommand(sublime_plugin.TextCommand):
    """
    A command to write a package message to the Package Control messaging buffer
    """

    def run(self, edit, string=''):
        self.view.insert(edit, self.view.size(), string)

########NEW FILE########
__FILENAME__ = remove_package_command
import threading

import sublime
import sublime_plugin

from ..show_error import show_error
from .existing_packages_command import ExistingPackagesCommand
from ..preferences_filename import preferences_filename
from ..thread_progress import ThreadProgress
from ..package_io import package_file_exists


class RemovePackageCommand(sublime_plugin.WindowCommand,
        ExistingPackagesCommand):
    """
    A command that presents a list of installed packages, allowing the user to
    select one to remove
    """

    def __init__(self, window):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the list of installed packages in.
        """

        self.window = window
        ExistingPackagesCommand.__init__(self)

    def run(self):
        self.package_list = self.make_package_list('remove')
        if not self.package_list:
            show_error('There are no packages that can be removed.')
            return
        self.window.show_quick_panel(self.package_list, self.on_done)

    def on_done(self, picked):
        """
        Quick panel user selection handler - deletes the selected package

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return
        package = self.package_list[picked][0]

        settings = sublime.load_settings(preferences_filename())

        # Change the color scheme before removing the package containing it
        if settings.get('color_scheme').find('Packages/' + package + '/') != -1:
            settings.set('color_scheme', 'Packages/Color Scheme - Default/Monokai.tmTheme')
            sublime.save_settings(preferences_filename())

        # Change the theme before removing the package containing it
        if package_file_exists(package, settings.get('theme')):
            settings.set('theme', 'Default.sublime-theme')
            sublime.save_settings(preferences_filename())

        ignored = settings.get('ignored_packages')
        if not ignored:
            ignored = []

        # Don't disable Package Control so it does not get stuck disabled
        if package != 'Package Control':
            if not package in ignored:
                ignored.append(package)
                settings.set('ignored_packages', ignored)
                sublime.save_settings(preferences_filename())
            ignored.remove(package)

        thread = RemovePackageThread(self.manager, package,
            ignored)
        thread.start()
        ThreadProgress(thread, 'Removing package %s' % package,
            'Package %s successfully removed' % package)


class RemovePackageThread(threading.Thread):
    """
    A thread to run the remove package operation in so that the Sublime Text
    UI does not become frozen
    """

    def __init__(self, manager, package, ignored):
        self.manager = manager
        self.package = package
        self.ignored = ignored
        threading.Thread.__init__(self)

    def run(self):
        self.result = self.manager.remove_package(self.package)

        def unignore_package():
            settings = sublime.load_settings(preferences_filename())
            settings.set('ignored_packages', self.ignored)
            sublime.save_settings(preferences_filename())
        sublime.set_timeout(unignore_package, 10)

########NEW FILE########
__FILENAME__ = upgrade_all_packages_command
import time
import threading

import sublime
import sublime_plugin

from ..thread_progress import ThreadProgress
from ..package_installer import PackageInstaller, PackageInstallerThread
from ..package_renamer import PackageRenamer


class UpgradeAllPackagesCommand(sublime_plugin.WindowCommand):
    """
    A command to automatically upgrade all installed packages that are
    upgradable.
    """

    def run(self):
        package_renamer = PackageRenamer()
        package_renamer.load_settings()

        thread = UpgradeAllPackagesThread(self.window, package_renamer)
        thread.start()
        ThreadProgress(thread, 'Loading repositories', '')


class UpgradeAllPackagesThread(threading.Thread, PackageInstaller):
    """
    A thread to run the action of retrieving upgradable packages in.
    """

    def __init__(self, window, package_renamer):
        self.window = window
        self.package_renamer = package_renamer
        self.completion_type = 'upgraded'
        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        self.package_renamer.rename_packages(self)
        package_list = self.make_package_list(['install', 'reinstall', 'none'])

        disabled_packages = []

        def do_upgrades():
            # Pause so packages can be disabled
            time.sleep(0.5)

            # We use a function to generate the on-complete lambda because if
            # we don't, the lambda will bind to info at the current scope, and
            # thus use the last value of info from the loop
            def make_on_complete(name):
                return lambda: self.reenable_package(name)

            for info in package_list:
                if info[0] in disabled_packages:
                    on_complete = make_on_complete(info[0])
                else:
                    on_complete = None
                thread = PackageInstallerThread(self.manager, info[0],
                    on_complete)
                thread.start()
                ThreadProgress(thread, 'Upgrading package %s' % info[0],
                    'Package %s successfully %s' % (info[0],
                    self.completion_type))

        # Disabling a package means changing settings, which can only be done
        # in the main thread. We then create a new background thread so that
        # the upgrade process does not block the UI.
        def disable_packages():
            package_names = []
            for info in package_list:
                package_names.append(info[0])
            disabled_packages.extend(self.disable_packages(package_names))
            threading.Thread(target=do_upgrades).start()

        sublime.set_timeout(disable_packages, 1)

########NEW FILE########
__FILENAME__ = upgrade_package_command
import threading

import sublime
import sublime_plugin

from ..show_error import show_error
from ..thread_progress import ThreadProgress
from ..package_installer import PackageInstaller, PackageInstallerThread
from ..package_renamer import PackageRenamer


class UpgradePackageCommand(sublime_plugin.WindowCommand):
    """
    A command that presents the list of installed packages that can be upgraded
    """

    def run(self):
        package_renamer = PackageRenamer()
        package_renamer.load_settings()

        thread = UpgradePackageThread(self.window, package_renamer)
        thread.start()
        ThreadProgress(thread, 'Loading repositories', '')


class UpgradePackageThread(threading.Thread, PackageInstaller):
    """
    A thread to run the action of retrieving upgradable packages in.
    """

    def __init__(self, window, package_renamer):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the list of upgradable packages in.

        :param package_renamer:
            An instance of :class:`PackageRenamer`
        """
        self.window = window
        self.package_renamer = package_renamer
        self.completion_type = 'upgraded'
        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        self.package_renamer.rename_packages(self)

        self.package_list = self.make_package_list(['install', 'reinstall',
            'none'])

        def show_quick_panel():
            if not self.package_list:
                show_error('There are no packages ready for upgrade')
                return
            self.window.show_quick_panel(self.package_list, self.on_done)
        sublime.set_timeout(show_quick_panel, 10)

    def on_done(self, picked):
        """
        Quick panel user selection handler - disables a package, upgrades it,
        then re-enables the package

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return
        name = self.package_list[picked][0]

        if name in self.disable_packages(name):
            on_complete = lambda: self.reenable_package(name)
        else:
            on_complete = None

        thread = PackageInstallerThread(self.manager, name, on_complete)
        thread.start()
        ThreadProgress(thread, 'Upgrading package %s' % name,
            'Package %s successfully %s' % (name, self.completion_type))

########NEW FILE########
__FILENAME__ = console_write
import sys


def console_write(string, prefix=False):
    """
    Writes a value to the Sublime Text console, encoding unicode to utf-8 first

    :param string:
        The value to write

    :param prefix:
        If the string "Package Control: " should be prefixed to the string
    """

    if sys.version_info < (3,):
        if isinstance(string, unicode):
            string = string.encode('UTF-8')
    if prefix:
        sys.stdout.write('Package Control: ')
    print(string)

########NEW FILE########
__FILENAME__ = background_downloader
import threading


class BackgroundDownloader(threading.Thread):
    """
    Downloads information from one or more URLs in the background.
    Normal usage is to use one BackgroundDownloader per domain name.

    :param settings:
        A dict containing at least the following fields:
          `cache_length`,
          `debug`,
          `timeout`,
          `user_agent`,
          `http_proxy`,
          `https_proxy`,
          `proxy_username`,
          `proxy_password`

    :param providers:
        An array of providers that can download the URLs
    """

    def __init__(self, settings, providers):
        self.settings = settings
        self.urls = []
        self.providers = providers
        self.used_providers = {}
        threading.Thread.__init__(self)

    def add_url(self, url):
        """
        Adds a URL to the list to download

        :param url:
            The URL to download info about
        """

        self.urls.append(url)

    def get_provider(self, url):
        """
        Returns the provider for the URL specified

        :param url:
            The URL to return the provider for

        :return:
            The provider object for the URL
        """

        return self.used_providers[url]

    def run(self):
        for url in self.urls:
            for provider_class in self.providers:
                if provider_class.match_url(url):
                    provider = provider_class(url, self.settings)
                    break

            provider.prefetch()
            self.used_providers[url] = provider

########NEW FILE########
__FILENAME__ = binary_not_found_error
class BinaryNotFoundError(Exception):
    """If a necessary executable is not found in the PATH on the system"""

    pass

########NEW FILE########
__FILENAME__ = caching_downloader
import sys
import re
import json
import hashlib

from ..console_write import console_write


class CachingDownloader(object):
    """
    A base downloader that will use a caching backend to cache HTTP requests
    and make conditional requests.
    """

    def add_conditional_headers(self, url, headers):
        """
        Add `If-Modified-Since` and `If-None-Match` headers to a request if a
        cached copy exists

        :param headers:
            A dict with the request headers

        :return:
            The request headers dict, possibly with new headers added
        """

        if not self.settings.get('cache'):
            return headers

        info_key = self.generate_key(url, '.info')
        info_json = self.settings['cache'].get(info_key)

        if not info_json:
            return headers

        # Make sure we have the cached content to use if we get a 304
        key = self.generate_key(url)
        if not self.settings['cache'].has(key):
            return headers

        try:
            info = json.loads(info_json.decode('utf-8'))
        except ValueError:
            return headers

        etag = info.get('etag')
        if etag:
            headers['If-None-Match'] = etag

        last_modified = info.get('last-modified')
        if last_modified:
            headers['If-Modified-Since'] = last_modified

        return headers

    def cache_result(self, method, url, status, headers, content):
        """
        Processes a request result, either caching the result, or returning
        the cached version of the url.

        :param method:
            The HTTP method used for the request

        :param url:
            The url of the request

        :param status:
            The numeric response status of the request

        :param headers:
            A dict of reponse headers, with keys being lowercase

        :param content:
            The response content

        :return:
            The response content
        """

        debug = self.settings.get('debug', False)

        if not self.settings.get('cache'):
            if debug:
                console_write(u"Skipping cache since there is no cache object", True)
            return content

        if method.lower() != 'get':
            if debug:
                console_write(u"Skipping cache since the HTTP method != GET", True)
            return content

        status = int(status)

        # Don't do anything unless it was successful or not modified
        if status not in [200, 304]:
            if debug:
                console_write(u"Skipping cache since the HTTP status code not one of: 200, 304", True)
            return content

        key = self.generate_key(url)

        if status == 304:
            cached_content = self.settings['cache'].get(key)
            if cached_content:
                if debug:
                    console_write(u"Using cached content for %s" % url, True)
                return cached_content

            # If we got a 304, but did not have the cached content
            # stop here so we don't cache an empty response
            return content

        # If we got here, the status is 200

        # Respect some basic cache control headers
        cache_control = headers.get('cache-control', '')
        if cache_control:
            fields = re.split(',\s*', cache_control)
            for field in fields:
                if field == 'no-store':
                    return content

        # Don't ever cache zip/binary files for the sake of hard drive space
        if headers.get('content-type') in ['application/zip', 'application/octet-stream']:
            if debug:
                console_write(u"Skipping cache since the response is a zip file", True)
            return content

        etag = headers.get('etag')
        last_modified = headers.get('last-modified')

        if not etag and not last_modified:
            return content

        struct = {'etag': etag, 'last-modified': last_modified}
        struct_json = json.dumps(struct, indent=4)

        info_key = self.generate_key(url, '.info')
        if debug:
            console_write(u"Caching %s in %s" % (url, key), True)

        self.settings['cache'].set(info_key, struct_json.encode('utf-8'))
        self.settings['cache'].set(key, content)

        return content

    def generate_key(self, url, suffix=''):
        """
        Generates a key to store the cache under

        :param url:
            The URL being cached

        :param suffix:
            A string to append to the key

        :return:
            A string key for the URL
        """

        if sys.version_info >= (3,) or isinstance(url, unicode):
            url = url.encode('utf-8')

        key = hashlib.md5(url).hexdigest()
        return key + suffix

    def retrieve_cached(self, url):
        """
        Tries to return the cached content for a URL

        :param url:
            The URL to get the cached content for

        :return:
            The cached content
        """

        key = self.generate_key(url)
        if not self.settings['cache'].has(key):
            return False

        if self.settings.get('debug'):
            console_write(u"Using cached content for %s" % url, True)

        return self.settings['cache'].get(key)

########NEW FILE########
__FILENAME__ = cert_provider
import os
import re
import json

import sublime

from ..console_write import console_write
from ..open_compat import open_compat, read_compat
from ..package_io import read_package_file
from ..cache import get_cache
from ..ca_certs import get_system_ca_bundle_path
from .no_ca_cert_exception import NoCaCertException
from .downloader_exception import DownloaderException


class CertProvider(object):
    """
    A base downloader that provides access to a ca-bundle for validating
    SSL certificates.
    """

    def check_certs(self, domain, timeout):
        """
        Ensures that the SSL CA cert for a domain is present on the machine

        :param domain:
            The domain to ensure there is a CA cert for

        :param timeout:
            The int timeout for downloading the CA cert from the channel

        :raises:
            NoCaCertException: when a suitable CA cert could not be found

        :return:
            The CA cert bundle path
        """

        # Try to use the system CA bundle
        ca_bundle_path = get_system_ca_bundle_path(self.settings)
        if ca_bundle_path:
            return ca_bundle_path

        # If the system bundle did not work, fall back to our CA distribution
        # system. Hopefully this will be going away soon.
        if self.settings.get('debug'):
            console_write(u'Unable to find system CA cert bundle, falling back to certs provided by Package Control')

        cert_match = False

        certs_list = get_cache('*.certs', self.settings.get('certs', {}))

        ca_bundle_path = os.path.join(sublime.packages_path(), 'User', 'Package Control.ca-bundle')
        if not os.path.exists(ca_bundle_path) or os.stat(ca_bundle_path).st_size == 0:
            bundle_contents = read_package_file('Package Control', 'Package Control.ca-bundle', True)
            if not bundle_contents:
                raise NoCaCertException(u'Unable to copy distributed Package Control.ca-bundle', domain)
            with open_compat(ca_bundle_path, 'wb') as f:
                f.write(bundle_contents)

        cert_info = certs_list.get(domain)
        if cert_info:
            cert_match = self.locate_cert(cert_info[0],
                cert_info[1], domain, timeout)

        wildcard_info = certs_list.get('*')
        if wildcard_info:
            cert_match = self.locate_cert(wildcard_info[0],
                wildcard_info[1], domain, timeout) or cert_match

        if not cert_match:
            raise NoCaCertException(u'No CA certs available for %s' % domain, domain)

        return ca_bundle_path

    def locate_cert(self, cert_id, location, domain, timeout):
        """
        Makes sure the SSL cert specified has been added to the CA cert
        bundle that is present on the machine

        :param cert_id:
            The identifier for CA cert(s). For those provided by the channel
            system, this will be an md5 of the contents of the cert(s). For
            user-provided certs, this is something they provide.

        :param location:
            An http(s) URL, or absolute filesystem path to the CA cert(s)

        :param domain:
            The domain to ensure there is a CA cert for

        :param timeout:
            The int timeout for downloading the CA cert from the channel

        :return:
            If the cert specified (by cert_id) is present on the machine and
            part of the Package Control.ca-bundle file in the User package folder
        """

        ca_list_path = os.path.join(sublime.packages_path(), 'User', 'Package Control.ca-list')
        if not os.path.exists(ca_list_path) or os.stat(ca_list_path).st_size == 0:
            list_contents = read_package_file('Package Control', 'Package Control.ca-list')
            if not list_contents:
                raise NoCaCertException(u'Unable to copy distributed Package Control.ca-list', domain)
            with open_compat(ca_list_path, 'w') as f:
                f.write(list_contents)

        ca_certs = []
        with open_compat(ca_list_path, 'r') as f:
            ca_certs = json.loads(read_compat(f))

        if not cert_id in ca_certs:
            if str(location) != '':
                if re.match('^https?://', location):
                    contents = self.download_cert(cert_id, location, domain,
                        timeout)
                else:
                    contents = self.load_cert(cert_id, location, domain)
                if contents:
                    self.save_cert(cert_id, contents)
                    return True
            return False
        return True

    def download_cert(self, cert_id, url, domain, timeout):
        """
        Downloads CA cert(s) from a URL

        :param cert_id:
            The identifier for CA cert(s). For those provided by the channel
            system, this will be an md5 of the contents of the cert(s). For
            user-provided certs, this is something they provide.

        :param url:
            An http(s) URL to the CA cert(s)

        :param domain:
            The domain to ensure there is a CA cert for

        :param timeout:
            The int timeout for downloading the CA cert from the channel

        :return:
            The contents of the CA cert(s)
        """

        cert_downloader = self.__class__(self.settings)
        if self.settings.get('debug'):
            console_write(u"Downloading CA cert for %s from \"%s\"" % (domain, url), True)
        return cert_downloader.download(url,
            'Error downloading CA certs for %s.' % domain, timeout, 1)

    def load_cert(self, cert_id, path, domain):
        """
        Copies CA cert(s) from a file path

        :param cert_id:
            The identifier for CA cert(s). For those provided by the channel
            system, this will be an md5 of the contents of the cert(s). For
            user-provided certs, this is something they provide.

        :param path:
            The absolute filesystem path to a file containing the CA cert(s)

        :param domain:
            The domain name the cert is for

        :return:
            The contents of the CA cert(s)
        """

        if os.path.exists(path):
            if self.settings.get('debug'):
                console_write(u"Copying CA cert for %s from \"%s\"" % (domain, path), True)
            with open_compat(path, 'rb') as f:
                return f.read()
        else:
            raise NoCaCertException(u"Unable to find CA cert for %s at \"%s\"" % (domain, path), domain)

    def save_cert(self, cert_id, contents):
        """
        Saves CA cert(s) to the Package Control.ca-bundle

        :param cert_id:
            The identifier for CA cert(s). For those provided by the channel
            system, this will be an md5 of the contents of the cert(s). For
            user-provided certs, this is something they provide.

        :param contents:
            The contents of the CA cert(s)
        """


        ca_bundle_path = os.path.join(sublime.packages_path(), 'User', 'Package Control.ca-bundle')
        with open_compat(ca_bundle_path, 'ab') as f:
            f.write(b"\n" + contents)

        ca_list_path = os.path.join(sublime.packages_path(), 'User', 'Package Control.ca-list')
        with open_compat(ca_list_path, 'r') as f:
            ca_certs = json.loads(read_compat(f))
        ca_certs.append(cert_id)
        with open_compat(ca_list_path, 'w') as f:
            f.write(json.dumps(ca_certs, indent=4))

########NEW FILE########
__FILENAME__ = cli_downloader
import os
import subprocess

from ..console_write import console_write
from ..cmd import create_cmd
from .non_clean_exit_error import NonCleanExitError
from .binary_not_found_error import BinaryNotFoundError


class CliDownloader(object):
    """
    Base for downloaders that use a command line program

    :param settings:
        A dict of the various Package Control settings. The Sublime Text
        Settings API is not used because this code is run in a thread.
    """

    def __init__(self, settings):
        self.settings = settings

    def clean_tmp_file(self):
        if os.path.exists(self.tmp_file):
            os.remove(self.tmp_file)

    def find_binary(self, name):
        """
        Finds the given executable name in the system PATH

        :param name:
            The exact name of the executable to find

        :return:
            The absolute path to the executable

        :raises:
            BinaryNotFoundError when the executable can not be found
        """

        dirs = os.environ['PATH'].split(os.pathsep)
        if os.name != 'nt':
            # This is mostly for OS X, which seems to launch ST with a
            # minimal set of environmental variables
            dirs.append('/usr/local/bin')

        for dir_ in dirs:
            path = os.path.join(dir_, name)
            if os.path.exists(path):
                return path

        raise BinaryNotFoundError('The binary %s could not be located' % name)

    def execute(self, args):
        """
        Runs the executable and args and returns the result

        :param args:
            A list of the executable path and all arguments to be passed to it

        :return:
            The text output of the executable

        :raises:
            NonCleanExitError when the executable exits with an error
        """

        if self.settings.get('debug'):
            console_write(u"Trying to execute command %s" % create_cmd(args), True)

        proc = subprocess.Popen(args, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        output = proc.stdout.read()
        self.stderr = proc.stderr.read()
        returncode = proc.wait()
        if returncode != 0:
            error = NonCleanExitError(returncode)
            error.stderr = self.stderr
            error.stdout = output
            raise error
        return output

########NEW FILE########
__FILENAME__ = curl_downloader
import tempfile
import re
import os

from ..console_write import console_write
from ..open_compat import open_compat, read_compat
from .cli_downloader import CliDownloader
from .non_clean_exit_error import NonCleanExitError
from .rate_limit_exception import RateLimitException
from .downloader_exception import DownloaderException
from .cert_provider import CertProvider
from .limiting_downloader import LimitingDownloader
from .caching_downloader import CachingDownloader


class CurlDownloader(CliDownloader, CertProvider, LimitingDownloader, CachingDownloader):
    """
    A downloader that uses the command line program curl

    :param settings:
        A dict of the various Package Control settings. The Sublime Text
        Settings API is not used because this code is run in a thread.

    :raises:
        BinaryNotFoundError: when curl can not be found
    """

    def __init__(self, settings):
        self.settings = settings
        self.curl = self.find_binary('curl')

    def close(self):
        """
        No-op for compatibility with UrllibDownloader and WinINetDownloader
        """

        pass

    def download(self, url, error_message, timeout, tries, prefer_cached=False):
        """
        Downloads a URL and returns the contents

        :param url:
            The URL to download

        :param error_message:
            A string to include in the console error that is printed
            when an error occurs

        :param timeout:
            The int number of seconds to set the timeout to

        :param tries:
            The int number of times to try and download the URL in the case of
            a timeout or HTTP 503 error

        :param prefer_cached:
            If a cached version should be returned instead of trying a new request

        :raises:
            NoCaCertException: when no CA certs can be found for the url
            RateLimitException: when a rate limit is hit
            DownloaderException: when any other download error occurs

        :return:
            The string contents of the URL
        """

        if prefer_cached:
            cached = self.retrieve_cached(url)
            if cached:
                return cached

        self.tmp_file = tempfile.NamedTemporaryFile().name
        command = [self.curl, '--user-agent', self.settings.get('user_agent'),
            '--connect-timeout', str(int(timeout)), '-sSL',
            # Don't be alarmed if the response from the server does not select
            # one of these since the server runs a relatively new version of
            # OpenSSL which supports compression on the SSL layer, and Apache
            # will use that instead of HTTP-level encoding.
            '--compressed',
            # We have to capture the headers to check for rate limit info
            '--dump-header', self.tmp_file]

        request_headers = self.add_conditional_headers(url, {})

        for name, value in request_headers.items():
            command.extend(['--header', "%s: %s" % (name, value)])

        secure_url_match = re.match('^https://([^/]+)', url)
        if secure_url_match != None:
            secure_domain = secure_url_match.group(1)
            bundle_path = self.check_certs(secure_domain, timeout)
            command.extend(['--cacert', bundle_path])

        debug = self.settings.get('debug')
        if debug:
            command.append('-v')

        http_proxy = self.settings.get('http_proxy')
        https_proxy = self.settings.get('https_proxy')
        proxy_username = self.settings.get('proxy_username')
        proxy_password = self.settings.get('proxy_password')

        if debug:
            console_write(u"Curl Debug Proxy", True)
            console_write(u"  http_proxy: %s" % http_proxy)
            console_write(u"  https_proxy: %s" % https_proxy)
            console_write(u"  proxy_username: %s" % proxy_username)
            console_write(u"  proxy_password: %s" % proxy_password)

        if http_proxy or https_proxy:
            command.append('--proxy-anyauth')

        if proxy_username or proxy_password:
            command.extend(['-U', u"%s:%s" % (proxy_username, proxy_password)])

        if http_proxy:
            os.putenv('http_proxy', http_proxy)
        if https_proxy:
            os.putenv('HTTPS_PROXY', https_proxy)

        command.append(url)

        error_string = None
        while tries > 0:
            tries -= 1
            try:
                output = self.execute(command)

                with open_compat(self.tmp_file, 'r') as f:
                    headers_str = read_compat(f)
                self.clean_tmp_file()

                message = 'OK'
                status = 200
                headers = {}
                for header in headers_str.splitlines():
                    if header[0:5] == 'HTTP/':
                        message = re.sub('^HTTP/\d\.\d\s+\d+\s*', '', header)
                        status = int(re.sub('^HTTP/\d\.\d\s+(\d+)(\s+.*)?$', '\\1', header))
                        continue
                    if header.strip() == '':
                        continue
                    name, value = header.split(':', 1)
                    headers[name.lower()] = value.strip()

                if debug:
                    self.print_debug(self.stderr.decode('utf-8'))

                self.handle_rate_limit(headers, url)

                if status not in [200, 304]:
                    e = NonCleanExitError(22)
                    e.stderr = "%s %s" % (status, message)
                    raise e

                output = self.cache_result('get', url, status, headers, output)

                return output

            except (NonCleanExitError) as e:
                # Stderr is used for both the error message and the debug info
                # so we need to process it to extra the debug info
                if self.settings.get('debug'):
                    if hasattr(e.stderr, 'decode'):
                        e.stderr = e.stderr.decode('utf-8')
                    e.stderr = self.print_debug(e.stderr)

                self.clean_tmp_file()

                if e.returncode == 22:
                    code = re.sub('^.*?(\d+)([\w\s]+)?$', '\\1', e.stderr)
                    if code == '503' and tries != 0:
                        # GitHub and BitBucket seem to rate limit via 503
                        error_string = u'Downloading %s was rate limited' % url
                        if tries:
                            error_string += ', trying again'
                            if debug:
                                console_write(error_string, True)
                        continue

                    download_error = u'HTTP error ' + code

                elif e.returncode == 6:
                    download_error = u'URL error host not found'

                elif e.returncode == 28:
                    # GitHub and BitBucket seem to time out a lot
                    error_string = u'Downloading %s timed out' % url
                    if tries:
                        error_string += ', trying again'
                        if debug:
                            console_write(error_string, True)
                    continue

                else:
                    download_error = e.stderr.rstrip()

                error_string = u'%s %s downloading %s.' % (error_message, download_error, url)

            break

        raise DownloaderException(error_string)

    def supports_ssl(self):
        """
        Indicates if the object can handle HTTPS requests

        :return:
            If the object supports HTTPS requests
        """

        return True

    def print_debug(self, string):
        """
        Takes debug output from curl and groups and prints it

        :param string:
            The complete debug output from curl

        :return:
            A string containing any stderr output
        """

        section = 'General'
        last_section = None

        output = ''

        for line in string.splitlines():
            # Placeholder for body of request
            if line and line[0:2] == '{ ':
                continue
            if line and line[0:18] == '} [data not shown]':
                continue

            if len(line) > 1:
                subtract = 0
                if line[0:2] == '* ':
                    section = 'General'
                    subtract = 2
                elif line[0:2] == '> ':
                    section = 'Write'
                    subtract = 2
                elif line[0:2] == '< ':
                    section = 'Read'
                    subtract = 2
                line = line[subtract:]

                # If the line does not start with "* ", "< ", "> " or "  "
                # then it is a real stderr message
                if subtract == 0 and line[0:2] != '  ':
                    output += line.rstrip() + ' '
                    continue

            if line.strip() == '':
                continue

            if section != last_section:
                console_write(u"Curl HTTP Debug %s" % section, True)

            console_write(u'  ' + line)
            last_section = section

        return output.rstrip()

########NEW FILE########
__FILENAME__ = decoding_downloader
import gzip
import zlib

try:
    # Python 3
    from io import BytesIO as StringIO
except (ImportError):
    # Python 2
    from StringIO import StringIO


class DecodingDownloader(object):
    """
    A base for downloaders that provides the ability to decode gzipped
    or deflated content.
    """

    def decode_response(self, encoding, response):
        if encoding == 'gzip':
            return gzip.GzipFile(fileobj=StringIO(response)).read()
        elif encoding == 'deflate':
            decompresser = zlib.decompressobj(-zlib.MAX_WBITS)
            return decompresser.decompress(response) + decompresser.flush()
        return response

########NEW FILE########
__FILENAME__ = downloader_exception
class DownloaderException(Exception):
    """If a downloader could not download a URL"""

    def __str__(self):
        return self.args[0]

########NEW FILE########
__FILENAME__ = http_error
class HttpError(Exception):
    """If a downloader was able to download a URL, but the result was not a 200 or 304"""

    def __init__(self, message, code):
        self.code = code
        super(HttpError, self).__init__(message)

    def __str__(self):
        return self.args[0]

########NEW FILE########
__FILENAME__ = limiting_downloader
try:
    # Python 3
    from urllib.parse import urlparse
except (ImportError):
    # Python 2
    from urlparse import urlparse

from .rate_limit_exception import RateLimitException


class LimitingDownloader(object):
    """
    A base for downloaders that checks for rate limiting headers.
    """

    def handle_rate_limit(self, headers, url):
        """
        Checks the headers of a response object to make sure we are obeying the
        rate limit

        :param headers:
            The dict-like object that contains lower-cased headers

        :param url:
            The URL that was requested

        :raises:
            RateLimitException when the rate limit has been hit
        """

        limit_remaining = headers.get('x-ratelimit-remaining', '1')
        limit = headers.get('x-ratelimit-limit', '1')

        if str(limit_remaining) == '0':
            hostname = urlparse(url).hostname
            raise RateLimitException(hostname, limit)

########NEW FILE########
__FILENAME__ = non_clean_exit_error
class NonCleanExitError(Exception):
    """
    When an subprocess does not exit cleanly

    :param returncode:
        The command line integer return code of the subprocess
    """

    def __init__(self, returncode):
        self.returncode = returncode

    def __str__(self):
        return repr(self.returncode)

########NEW FILE########
__FILENAME__ = non_http_error
class NonHttpError(Exception):
    """If a downloader had a non-clean exit, but it was not due to an HTTP error"""

    def __str__(self):
        return self.args[0]

########NEW FILE########
__FILENAME__ = no_ca_cert_exception
from .downloader_exception import DownloaderException


class NoCaCertException(DownloaderException):
    """
    An exception for when there is no CA cert for a domain name
    """

    def __init__(self, message, domain):
        self.domain = domain
        super(NoCaCertException, self).__init__(message)

########NEW FILE########
__FILENAME__ = rate_limit_exception
from .downloader_exception import DownloaderException


class RateLimitException(DownloaderException):
    """
    An exception for when the rate limit of an API has been exceeded.
    """

    def __init__(self, domain, limit):
        self.domain = domain
        self.limit = limit
        message = u'Rate limit of %s exceeded for %s' % (limit, domain)
        super(RateLimitException, self).__init__(message)

########NEW FILE########
__FILENAME__ = urllib_downloader
import re
import os
import sys

from .. import http

try:
    # Python 3
    from http.client import HTTPException, BadStatusLine
    from urllib.request import ProxyHandler, HTTPPasswordMgrWithDefaultRealm, ProxyBasicAuthHandler, ProxyDigestAuthHandler, build_opener, Request
    from urllib.error import HTTPError, URLError
    import urllib.request as urllib_compat
except (ImportError):
    # Python 2
    from httplib import HTTPException, BadStatusLine
    from urllib2 import ProxyHandler, HTTPPasswordMgrWithDefaultRealm, ProxyBasicAuthHandler, ProxyDigestAuthHandler, build_opener, Request
    from urllib2 import HTTPError, URLError
    import urllib2 as urllib_compat

try:
    # Python 3.3
    import ConnectionError
except (ImportError):
    # Python 2.6-3.2
    from socket import error as ConnectionError

from ..console_write import console_write
from ..unicode import unicode_from_os
from ..http.validating_https_handler import ValidatingHTTPSHandler
from ..http.debuggable_http_handler import DebuggableHTTPHandler
from .rate_limit_exception import RateLimitException
from .downloader_exception import DownloaderException
from .cert_provider import CertProvider
from .decoding_downloader import DecodingDownloader
from .limiting_downloader import LimitingDownloader
from .caching_downloader import CachingDownloader


class UrlLibDownloader(CertProvider, DecodingDownloader, LimitingDownloader, CachingDownloader):
    """
    A downloader that uses the Python urllib module

    :param settings:
        A dict of the various Package Control settings. The Sublime Text
        Settings API is not used because this code is run in a thread.
    """

    def __init__(self, settings):
        self.opener = None
        self.settings = settings

    def close(self):
        """
        Closes any persistent/open connections
        """

        if not self.opener:
            return
        handler = self.get_handler()
        if handler:
            handler.close()
        self.opener = None

    def download(self, url, error_message, timeout, tries, prefer_cached=False):
        """
        Downloads a URL and returns the contents

        Uses the proxy settings from the Package Control.sublime-settings file,
        however there seem to be a decent number of proxies that this code
        does not work with. Patches welcome!

        :param url:
            The URL to download

        :param error_message:
            A string to include in the console error that is printed
            when an error occurs

        :param timeout:
            The int number of seconds to set the timeout to

        :param tries:
            The int number of times to try and download the URL in the case of
            a timeout or HTTP 503 error

        :param prefer_cached:
            If a cached version should be returned instead of trying a new request

        :raises:
            NoCaCertException: when no CA certs can be found for the url
            RateLimitException: when a rate limit is hit
            DownloaderException: when any other download error occurs

        :return:
            The string contents of the URL
        """

        if prefer_cached:
            cached = self.retrieve_cached(url)
            if cached:
                return cached

        self.setup_opener(url, timeout)

        debug = self.settings.get('debug')
        error_string = None
        while tries > 0:
            tries -= 1
            try:
                request_headers = {
                    "User-Agent": self.settings.get('user_agent'),
                    # Don't be alarmed if the response from the server does not
                    # select one of these since the server runs a relatively new
                    # version of OpenSSL which supports compression on the SSL
                    # layer, and Apache will use that instead of HTTP-level
                    # encoding.
                    "Accept-Encoding": "gzip,deflate"
                }
                request_headers = self.add_conditional_headers(url, request_headers)
                request = Request(url, headers=request_headers)
                http_file = self.opener.open(request, timeout=timeout)
                self.handle_rate_limit(http_file.headers, url)

                result = http_file.read()
                # Make sure the response is closed so we can re-use the connection
                http_file.close()

                encoding = http_file.headers.get('content-encoding')
                result = self.decode_response(encoding, result)

                return self.cache_result('get', url, http_file.getcode(),
                    http_file.headers, result)

            except (HTTPException) as e:
                # Since we use keep-alives, it is possible the other end closed
                # the connection, and we may just need to re-open
                if isinstance(e, BadStatusLine):
                    handler = self.get_handler()
                    if handler and handler.use_count > 1:
                        self.close()
                        self.setup_opener(url, timeout)
                        tries += 1
                        continue

                error_string = u'%s HTTP exception %s (%s) downloading %s.' % (
                    error_message, e.__class__.__name__, unicode_from_os(e), url)

            except (HTTPError) as e:
                # Make sure the response is closed so we can re-use the connection
                e.read()
                e.close()

                # Make sure we obey Github's rate limiting headers
                self.handle_rate_limit(e.headers, url)

                # Handle cached responses
                if unicode_from_os(e.code) == '304':
                    return self.cache_result('get', url, int(e.code), e.headers, b'')

                # Bitbucket and Github return 503 a decent amount
                if unicode_from_os(e.code) == '503' and tries != 0:
                    error_string = u'Downloading %s was rate limited' % url
                    if tries:
                        error_string += ', trying again'
                        if debug:
                            console_write(error_string, True)
                    continue

                error_string = u'%s HTTP error %s downloading %s.' % (
                    error_message, unicode_from_os(e.code), url)

            except (URLError) as e:

                # Bitbucket and Github timeout a decent amount
                if unicode_from_os(e.reason) == 'The read operation timed out' \
                        or unicode_from_os(e.reason) == 'timed out':
                    error_string = u'Downloading %s timed out' % url
                    if tries:
                        error_string += ', trying again'
                        if debug:
                            console_write(error_string, True)
                    continue

                error_string = u'%s URL error %s downloading %s.' % (
                    error_message, unicode_from_os(e.reason), url)

            except (ConnectionError):
                # Handle broken pipes/reset connections by creating a new opener, and
                # thus getting new handlers and a new connection
                error_string = u'Connection went away while trying to download %s, trying again' % url
                if debug:
                    console_write(error_string, True)

                self.opener = None
                self.setup_opener(url, timeout)
                tries += 1

                continue

            break

        raise DownloaderException(error_string)

    def get_handler(self):
        """
        Get the HTTPHandler object for the current connection
        """

        if not self.opener:
            return None

        for handler in self.opener.handlers:
            if isinstance(handler, ValidatingHTTPSHandler) or isinstance(handler, DebuggableHTTPHandler):
                return handler

    def setup_opener(self, url, timeout):
        """
        Sets up a urllib OpenerDirector to be used for requests. There is a
        fair amount of custom urllib code in Package Control, and part of it
        is to handle proxies and keep-alives. Creating an opener the way
        below is because the handlers have been customized to send the
        "Connection: Keep-Alive" header and hold onto connections so they
        can be re-used.

        :param url:
            The URL to download

        :param timeout:
            The int number of seconds to set the timeout to
        """

        if not self.opener:
            http_proxy = self.settings.get('http_proxy')
            https_proxy = self.settings.get('https_proxy')
            if http_proxy or https_proxy:
                proxies = {}
                if http_proxy:
                    proxies['http'] = http_proxy
                if https_proxy:
                    proxies['https'] = https_proxy
                proxy_handler = ProxyHandler(proxies)
            else:
                proxy_handler = ProxyHandler()

            password_manager = HTTPPasswordMgrWithDefaultRealm()
            proxy_username = self.settings.get('proxy_username')
            proxy_password = self.settings.get('proxy_password')
            if proxy_username and proxy_password:
                if http_proxy:
                    password_manager.add_password(None, http_proxy, proxy_username,
                        proxy_password)
                if https_proxy:
                    password_manager.add_password(None, https_proxy, proxy_username,
                        proxy_password)

            handlers = [proxy_handler]

            basic_auth_handler = ProxyBasicAuthHandler(password_manager)
            digest_auth_handler = ProxyDigestAuthHandler(password_manager)
            handlers.extend([digest_auth_handler, basic_auth_handler])

            debug = self.settings.get('debug')

            if debug:
                console_write(u"Urllib Debug Proxy", True)
                console_write(u"  http_proxy: %s" % http_proxy)
                console_write(u"  https_proxy: %s" % https_proxy)
                console_write(u"  proxy_username: %s" % proxy_username)
                console_write(u"  proxy_password: %s" % proxy_password)

            secure_url_match = re.match('^https://([^/]+)', url)
            if secure_url_match != None:
                secure_domain = secure_url_match.group(1)
                bundle_path = self.check_certs(secure_domain, timeout)
                bundle_path = bundle_path.encode(sys.getfilesystemencoding())
                handlers.append(ValidatingHTTPSHandler(ca_certs=bundle_path,
                    debug=debug, passwd=password_manager,
                    user_agent=self.settings.get('user_agent')))
            else:
                handlers.append(DebuggableHTTPHandler(debug=debug,
                    passwd=password_manager))
            self.opener = build_opener(*handlers)

    def supports_ssl(self):
        """
        Indicates if the object can handle HTTPS requests

        :return:
            If the object supports HTTPS requests
        """
        return 'ssl' in sys.modules and hasattr(urllib_compat, 'HTTPSHandler')

########NEW FILE########
__FILENAME__ = wget_downloader
import tempfile
import re
import os

from ..console_write import console_write
from ..unicode import unicode_from_os
from ..open_compat import open_compat, read_compat
from .cli_downloader import CliDownloader
from .non_http_error import NonHttpError
from .non_clean_exit_error import NonCleanExitError
from .rate_limit_exception import RateLimitException
from .downloader_exception import DownloaderException
from .cert_provider import CertProvider
from .decoding_downloader import DecodingDownloader
from .limiting_downloader import LimitingDownloader
from .caching_downloader import CachingDownloader


class WgetDownloader(CliDownloader, CertProvider, DecodingDownloader, LimitingDownloader, CachingDownloader):
    """
    A downloader that uses the command line program wget

    :param settings:
        A dict of the various Package Control settings. The Sublime Text
        Settings API is not used because this code is run in a thread.

    :raises:
        BinaryNotFoundError: when wget can not be found
    """

    def __init__(self, settings):
        self.settings = settings
        self.debug = settings.get('debug')
        self.wget = self.find_binary('wget')

    def close(self):
        """
        No-op for compatibility with UrllibDownloader and WinINetDownloader
        """

        pass

    def download(self, url, error_message, timeout, tries, prefer_cached=False):
        """
        Downloads a URL and returns the contents

        :param url:
            The URL to download

        :param error_message:
            A string to include in the console error that is printed
            when an error occurs

        :param timeout:
            The int number of seconds to set the timeout to

        :param tries:
            The int number of times to try and download the URL in the case of
            a timeout or HTTP 503 error

        :param prefer_cached:
            If a cached version should be returned instead of trying a new request

        :raises:
            NoCaCertException: when no CA certs can be found for the url
            RateLimitException: when a rate limit is hit
            DownloaderException: when any other download error occurs

        :return:
            The string contents of the URL
        """

        if prefer_cached:
            cached = self.retrieve_cached(url)
            if cached:
                return cached

        self.tmp_file = tempfile.NamedTemporaryFile().name
        command = [self.wget, '--connect-timeout=' + str(int(timeout)), '-o',
            self.tmp_file, '-O', '-', '-U', self.settings.get('user_agent')]

        request_headers = {
            # Don't be alarmed if the response from the server does not select
            # one of these since the server runs a relatively new version of
            # OpenSSL which supports compression on the SSL layer, and Apache
            # will use that instead of HTTP-level encoding.
            'Accept-Encoding': 'gzip,deflate'
        }
        request_headers = self.add_conditional_headers(url, request_headers)

        for name, value in request_headers.items():
            command.extend(['--header', "%s: %s" % (name, value)])

        secure_url_match = re.match('^https://([^/]+)', url)
        if secure_url_match != None:
            secure_domain = secure_url_match.group(1)
            bundle_path = self.check_certs(secure_domain, timeout)
            command.append(u'--ca-certificate=' + bundle_path)

        if self.debug:
            command.append('-d')
        else:
            command.append('-S')

        http_proxy = self.settings.get('http_proxy')
        https_proxy = self.settings.get('https_proxy')
        proxy_username = self.settings.get('proxy_username')
        proxy_password = self.settings.get('proxy_password')

        if proxy_username:
            command.append(u"--proxy-user=%s" % proxy_username)
        if proxy_password:
            command.append(u"--proxy-password=%s" % proxy_password)

        if self.debug:
            console_write(u"Wget Debug Proxy", True)
            console_write(u"  http_proxy: %s" % http_proxy)
            console_write(u"  https_proxy: %s" % https_proxy)
            console_write(u"  proxy_username: %s" % proxy_username)
            console_write(u"  proxy_password: %s" % proxy_password)

        command.append(url)

        if http_proxy:
            os.putenv('http_proxy', http_proxy)
        if https_proxy:
            os.putenv('https_proxy', https_proxy)

        error_string = None
        while tries > 0:
            tries -= 1
            try:
                result = self.execute(command)

                general, headers = self.parse_output()
                encoding = headers.get('content-encoding')
                if encoding:
                    result = self.decode_response(encoding, result)

                result = self.cache_result('get', url, general['status'],
                    headers, result)

                return result

            except (NonCleanExitError) as e:

                try:
                    general, headers = self.parse_output()
                    self.handle_rate_limit(headers, url)

                    if general['status'] == 304:
                        return self.cache_result('get', url, general['status'],
                            headers, None)

                    if general['status'] == 503 and tries != 0:
                        # GitHub and BitBucket seem to rate limit via 503
                        error_string = u'Downloading %s was rate limited' % url
                        if tries:
                            error_string += ', trying again'
                            if self.debug:
                                console_write(error_string, True)
                        continue

                    download_error = 'HTTP error %s' % general['status']

                except (NonHttpError) as e:

                    download_error = unicode_from_os(e)

                    # GitHub and BitBucket seem to time out a lot
                    if download_error.find('timed out') != -1:
                        error_string = u'Downloading %s timed out' % url
                        if tries:
                            error_string += ', trying again'
                            if self.debug:
                                console_write(error_string, True)
                        continue

                error_string = u'%s %s downloading %s.' % (error_message, download_error, url)

            break

        raise DownloaderException(error_string)

    def supports_ssl(self):
        """
        Indicates if the object can handle HTTPS requests

        :return:
            If the object supports HTTPS requests
        """

        return True

    def parse_output(self):
        """
        Parses the wget output file, prints debug information and returns headers

        :return:
            A tuple of (general, headers) where general is a dict with the keys:
              `version` - HTTP version number (string)
              `status` - HTTP status code (integer)
              `message` - HTTP status message (string)
            And headers is a dict with the keys being lower-case version of the
            HTTP header names.
        """

        with open_compat(self.tmp_file, 'r') as f:
            output = read_compat(f).splitlines()
        self.clean_tmp_file()

        error = None
        header_lines = []
        if self.debug:
            section = 'General'
            last_section = None
            for line in output:
                if section == 'General':
                    if self.skippable_line(line):
                        continue

                # Skip blank lines
                if line.strip() == '':
                    continue

                # Error lines
                if line[0:5] == 'wget:':
                    error = line[5:].strip()
                if line[0:7] == 'failed:':
                    error = line[7:].strip()

                if line == '---request begin---':
                    section = 'Write'
                    continue
                elif line == '---request end---':
                    section = 'General'
                    continue
                elif line == '---response begin---':
                    section = 'Read'
                    continue
                elif line == '---response end---':
                    section = 'General'
                    continue

                if section != last_section:
                    console_write(u"Wget HTTP Debug %s" % section, True)

                if section == 'Read':
                    header_lines.append(line)

                console_write(u'  ' + line)
                last_section = section

        else:
            for line in output:
                if self.skippable_line(line):
                    continue

                # Check the resolving and connecting to lines for errors
                if re.match('(Resolving |Connecting to )', line):
                    failed_match = re.search(' failed: (.*)$', line)
                    if failed_match:
                        error = failed_match.group(1).strip()

                # Error lines
                if line[0:5] == 'wget:':
                    error = line[5:].strip()
                if line[0:7] == 'failed:':
                    error = line[7:].strip()

                if line[0:2] == '  ':
                    header_lines.append(line.lstrip())

        if error:
            raise NonHttpError(error)

        return self.parse_headers(header_lines)

    def skippable_line(self, line):
        """
        Determines if a debug line is skippable - usually because of extraneous
        or duplicate information.

        :param line:
            The debug line to check

        :return:
            True if the line is skippable, otherwise None
        """

        # Skip date lines
        if re.match('--\d{4}-\d{2}-\d{2}', line):
            return True
        if re.match('\d{4}-\d{2}-\d{2}', line):
            return True
        # Skip HTTP status code lines since we already have that info
        if re.match('\d{3} ', line):
            return True
        # Skip Saving to and progress lines
        if re.match('(Saving to:|\s*\d+K)', line):
            return True
        # Skip notice about ignoring body on HTTP error
        if re.match('Skipping \d+ byte', line):
            return True

    def parse_headers(self, output=None):
        """
        Parses HTTP headers into two dict objects

        :param output:
            An array of header lines, if None, loads from temp output file

        :return:
            A tuple of (general, headers) where general is a dict with the keys:
              `version` - HTTP version number (string)
              `status` - HTTP status code (integer)
              `message` - HTTP status message (string)
            And headers is a dict with the keys being lower-case version of the
            HTTP header names.
        """

        if not output:
            with open_compat(self.tmp_file, 'r') as f:
                output = read_compat(f).splitlines()
            self.clean_tmp_file()

        general = {
            'version': '0.9',
            'status':  200,
            'message': 'OK'
        }
        headers = {}
        for line in output:
            # When using the -S option, headers have two spaces before them,
            # additionally, valid headers won't have spaces, so this is always
            # a safe operation to perform
            line = line.lstrip()
            if line.find('HTTP/') == 0:
                match = re.match('HTTP/(\d\.\d)\s+(\d+)(?:\s+(.*))?$', line)
                general['version'] = match.group(1)
                general['status'] = int(match.group(2))
                general['message'] = match.group(3) or ''
            else:
                name, value = line.split(':', 1)
                headers[name.lower()] = value.strip()

        return (general, headers)

########NEW FILE########
__FILENAME__ = wininet_downloader
from ctypes import windll, wintypes
import ctypes
import time
import re
import datetime
import struct
import locale

wininet = windll.wininet

try:
    # Python 3
    from urllib.parse import urlparse
except (ImportError):
    # Python 2
    from urlparse import urlparse

from ..console_write import console_write
from ..unicode import unicode_from_os
from .non_http_error import NonHttpError
from .http_error import HttpError
from .rate_limit_exception import RateLimitException
from .downloader_exception import DownloaderException
from .decoding_downloader import DecodingDownloader
from .limiting_downloader import LimitingDownloader
from .caching_downloader import CachingDownloader


class WinINetDownloader(DecodingDownloader, LimitingDownloader, CachingDownloader):
    """
    A downloader that uses the Windows WinINet DLL to perform downloads. This
    has the benefit of utilizing system-level proxy configuration and CA certs.

    :param settings:
        A dict of the various Package Control settings. The Sublime Text
        Settings API is not used because this code is run in a thread.
    """

    # General constants
    ERROR_INSUFFICIENT_BUFFER = 122

    # InternetOpen constants
    INTERNET_OPEN_TYPE_PRECONFIG = 0

    # InternetConnect constants
    INTERNET_SERVICE_HTTP = 3
    INTERNET_FLAG_EXISTING_CONNECT = 0x20000000
    INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTPS = 0x00004000

    # InternetSetOption constants
    INTERNET_OPTION_CONNECT_TIMEOUT = 2
    INTERNET_OPTION_SEND_TIMEOUT = 5
    INTERNET_OPTION_RECEIVE_TIMEOUT = 6

    # InternetQueryOption constants
    INTERNET_OPTION_SECURITY_CERTIFICATE_STRUCT = 32
    INTERNET_OPTION_PROXY = 38
    INTERNET_OPTION_PROXY_USERNAME = 43
    INTERNET_OPTION_PROXY_PASSWORD = 44
    INTERNET_OPTION_CONNECTED_STATE = 50

    # HttpOpenRequest constants
    INTERNET_FLAG_KEEP_CONNECTION = 0x00400000
    INTERNET_FLAG_RELOAD = 0x80000000
    INTERNET_FLAG_NO_CACHE_WRITE = 0x04000000
    INTERNET_FLAG_PRAGMA_NOCACHE = 0x00000100
    INTERNET_FLAG_SECURE = 0x00800000

    # HttpQueryInfo constants
    HTTP_QUERY_RAW_HEADERS_CRLF = 22

    # InternetConnectedState constants
    INTERNET_STATE_CONNECTED = 1
    INTERNET_STATE_DISCONNECTED = 2
    INTERNET_STATE_DISCONNECTED_BY_USER = 0x10
    INTERNET_STATE_IDLE = 0x100
    INTERNET_STATE_BUSY = 0x200

    HTTP_STATUS_MESSAGES = {
        100: "Continue",
        101: "Switching Protocols",
        102: "Processing",
        200: "OK",
        201: "Created",
        202: "Accepted",
        203: "Non-Authoritative Information",
        204: "No Content",
        205: "Reset Content",
        206: "Partial Content",
        207: "Multi-Status",
        208: "Already Reported",
        226: "IM Used",
        300: "Multiple Choices",
        301: "Moved Permanently",
        302: "Found",
        303: "See Other",
        304: "Not Modified",
        305: "Use Proxy",
        306: "Switch Proxy",
        307: "Temporary Redirect",
        308: "Permanent Redirect",
        400: "Bad Request",
        401: "Unauthorized",
        402: "Payment Required",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        406: "Not Acceptable",
        407: "Proxy Authentication Required",
        408: "Request Timeout",
        409: "Conflict",
        410: "Gone",
        411: "Length Required",
        412: "Precondition Failed",
        413: "Request Entity Too Large",
        414: "Request-URI Too Long",
        415: "Unsupported Media Type",
        416: "Requested Range Not Satisfiable",
        417: "Expectation Failed",
        418: "I'm a teapot",
        419: "Authentication Timeout",
        420: "Enhance Your Calm",
        422: "Unprocessable Entity",
        423: "Locked",
        424: "Failed Dependency",
        424: "Method Failure",
        425: "Unordered Collection",
        426: "Upgrade Required",
        428: "Precondition Required",
        429: "Too Many Requests",
        431: "Request Header Fields Too Large",
        440: "Login Timeout",
        449: "Retry With",
        450: "Blocked by Windows Parental Controls",
        451: "Redirect",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
        505: "HTTP Version Not Supported",
        506: "Variant Also Negotiates",
        507: "Insufficient Storage",
        508: "Loop Detected",
        509: "Bandwidth Limit Exceeded",
        510: "Not Extended",
        511: "Network Authentication Required",
        520: "Origin Error",
        522: "Connection Timed Out",
        523: "Proxy Declined Request",
        524: "A Timeout Occurred",
        598: "Network Read Timeout Error",
        599: "Network Connect Timeout Error"
    }


    def __init__(self, settings):
        self.settings = settings
        self.debug = settings.get('debug')
        self.network_connection = None
        self.tcp_connection = None
        self.use_count = 0
        self.hostname = None
        self.port = None
        self.scheme = None
        self.was_offline = None

    def close(self):
        """
        Closes any persistent/open connections
        """

        closed = False
        changed_state_back = False

        if self.tcp_connection:
            wininet.InternetCloseHandle(self.tcp_connection)
            self.tcp_connection = None
            closed = True

        if self.network_connection:
            wininet.InternetCloseHandle(self.network_connection)
            self.network_connection = None
            closed = True

        if self.was_offline:
            dw_connected_state = wintypes.DWORD(self.INTERNET_STATE_DISCONNECTED_BY_USER)
            dw_flags = wintypes.DWORD(0)
            connected_info = InternetConnectedInfo(dw_connected_state, dw_flags)
            wininet.InternetSetOptionA(None,
                self.INTERNET_OPTION_CONNECTED_STATE, ctypes.byref(connected_info), ctypes.sizeof(connected_info))
            changed_state_back = True

        if self.debug:
            s = '' if self.use_count == 1 else 's'
            console_write(u"WinINet %s Debug General" % self.scheme.upper(), True)
            console_write(u"  Closing connection to %s on port %s after %s request%s" % (
                self.hostname, self.port, self.use_count, s))
            if changed_state_back:
                console_write(u"  Changed Internet Explorer back to Work Offline")

        self.hostname = None
        self.port = None
        self.scheme = None
        self.use_count = 0
        self.was_offline = None

    def download(self, url, error_message, timeout, tries, prefer_cached=False):
        """
        Downloads a URL and returns the contents

        :param url:
            The URL to download

        :param error_message:
            A string to include in the console error that is printed
            when an error occurs

        :param timeout:
            The int number of seconds to set the timeout to

        :param tries:
            The int number of times to try and download the URL in the case of
            a timeout or HTTP 503 error

        :param prefer_cached:
            If a cached version should be returned instead of trying a new request

        :raises:
            RateLimitException: when a rate limit is hit
            DownloaderException: when any other download error occurs

        :return:
            The string contents of the URL
        """

        if prefer_cached:
            cached = self.retrieve_cached(url)
            if cached:
                return cached

        url_info = urlparse(url)

        if not url_info.port:
            port = 443 if url_info.scheme == 'https' else 80
            hostname = url_info.netloc
        else:
            port = url_info.port
            hostname = url_info.hostname

        path = url_info.path
        if url_info.params:
            path += ';' + url_info.params
        if url_info.query:
            path += '?' + url_info.query

        request_headers = {
            'Accept-Encoding': 'gzip,deflate'
        }
        request_headers = self.add_conditional_headers(url, request_headers)

        created_connection = False
        # If we switched Internet Explorer out of "Work Offline" mode
        changed_to_online = False

        # If the user is requesting a connection to another server, close the connection
        if (self.hostname and self.hostname != hostname) or (self.port and self.port != port):
            self.close()

        # Reset the error info to a known clean state
        ctypes.windll.kernel32.SetLastError(0)

        # Save the internet setup in the class for re-use
        if not self.tcp_connection:
            created_connection = True

            # Connect to the internet if necessary
            state = self.read_option(None, self.INTERNET_OPTION_CONNECTED_STATE)
            state = ord(state)
            if state & self.INTERNET_STATE_DISCONNECTED or state & self.INTERNET_STATE_DISCONNECTED_BY_USER:
                # Track the previous state so we can go back once complete
                self.was_offline = True

                dw_connected_state = wintypes.DWORD(self.INTERNET_STATE_CONNECTED)
                dw_flags = wintypes.DWORD(0)
                connected_info = InternetConnectedInfo(dw_connected_state, dw_flags)
                wininet.InternetSetOptionA(None,
                    self.INTERNET_OPTION_CONNECTED_STATE, ctypes.byref(connected_info), ctypes.sizeof(connected_info))
                changed_to_online = True

            self.network_connection = wininet.InternetOpenW(self.settings.get('user_agent'),
                self.INTERNET_OPEN_TYPE_PRECONFIG, None, None, 0)

            if not self.network_connection:
                error_string = u'%s %s during network phase of downloading %s.' % (error_message, self.extract_error(), url)
                raise DownloaderException(error_string)

            win_timeout = wintypes.DWORD(int(timeout) * 1000)
            # Apparently INTERNET_OPTION_CONNECT_TIMEOUT just doesn't work, leaving it in hoping they may fix in the future
            wininet.InternetSetOptionA(self.network_connection,
                self.INTERNET_OPTION_CONNECT_TIMEOUT, win_timeout, ctypes.sizeof(win_timeout))
            wininet.InternetSetOptionA(self.network_connection,
                self.INTERNET_OPTION_SEND_TIMEOUT, win_timeout, ctypes.sizeof(win_timeout))
            wininet.InternetSetOptionA(self.network_connection,
                self.INTERNET_OPTION_RECEIVE_TIMEOUT, win_timeout, ctypes.sizeof(win_timeout))

            # Don't allow HTTPS sites to redirect to HTTP sites
            tcp_flags  = self.INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTPS
            # Try to re-use an existing connection to the server
            tcp_flags |= self.INTERNET_FLAG_EXISTING_CONNECT
            self.tcp_connection = wininet.InternetConnectW(self.network_connection,
                hostname, port, None, None, self.INTERNET_SERVICE_HTTP, tcp_flags, 0)

            if not self.tcp_connection:
                error_string = u'%s %s during connection phase of downloading %s.' % (error_message, self.extract_error(), url)
                raise DownloaderException(error_string)

            # Normally the proxy info would come from IE, but this allows storing it in
            # the Package Control settings file.
            proxy_username = self.settings.get('proxy_username')
            proxy_password = self.settings.get('proxy_password')
            if proxy_username and proxy_password:
                username = ctypes.c_wchar_p(proxy_username)
                password = ctypes.c_wchar_p(proxy_password)
                wininet.InternetSetOptionW(self.tcp_connection,
                    self.INTERNET_OPTION_PROXY_USERNAME, ctypes.cast(username, ctypes.c_void_p), len(proxy_username))
                wininet.InternetSetOptionW(self.tcp_connection,
                    self.INTERNET_OPTION_PROXY_PASSWORD, ctypes.cast(password, ctypes.c_void_p), len(proxy_password))

            self.hostname = hostname
            self.port = port
            self.scheme = url_info.scheme

        else:
            if self.debug:
                console_write(u"WinINet %s Debug General" % self.scheme.upper(), True)
                console_write(u"  Re-using connection to %s on port %s for request #%s" % (
                    self.hostname, self.port, self.use_count))

        error_string = None
        while tries > 0:
            tries -= 1
            try:
                http_connection = None

                # Keep-alive for better performance
                http_flags  = self.INTERNET_FLAG_KEEP_CONNECTION
                # Prevent caching/retrieving from cache
                http_flags |= self.INTERNET_FLAG_RELOAD
                http_flags |= self.INTERNET_FLAG_NO_CACHE_WRITE
                http_flags |= self.INTERNET_FLAG_PRAGMA_NOCACHE
                # Use SSL
                if self.scheme == 'https':
                    http_flags |= self.INTERNET_FLAG_SECURE

                http_connection = wininet.HttpOpenRequestW(self.tcp_connection, u'GET', path, u'HTTP/1.1', None, None, http_flags, 0)
                if not http_connection:
                    error_string = u'%s %s during HTTP connection phase of downloading %s.' % (error_message, self.extract_error(), url)
                    raise DownloaderException(error_string)

                request_header_lines = []
                for header, value in request_headers.items():
                    request_header_lines.append(u"%s: %s" % (header, value))
                request_header_lines = u"\r\n".join(request_header_lines)

                success = wininet.HttpSendRequestW(http_connection, request_header_lines, len(request_header_lines), None, 0)

                if not success:
                    error_string = u'%s %s during HTTP write phase of downloading %s.' % (error_message, self.extract_error(), url)
                    raise DownloaderException(error_string)

                # If we try to query before here, the proxy info will not be available to the first request
                if self.debug:
                    proxy_struct = self.read_option(self.network_connection, self.INTERNET_OPTION_PROXY)
                    proxy = ''
                    if proxy_struct.lpszProxy:
                        proxy = proxy_struct.lpszProxy.decode('cp1252')
                    proxy_bypass = ''
                    if proxy_struct.lpszProxyBypass:
                        proxy_bypass = proxy_struct.lpszProxyBypass.decode('cp1252')

                    proxy_username = self.read_option(self.tcp_connection, self.INTERNET_OPTION_PROXY_USERNAME)
                    proxy_password = self.read_option(self.tcp_connection, self.INTERNET_OPTION_PROXY_PASSWORD)

                    console_write(u"WinINet Debug Proxy", True)
                    console_write(u"  proxy: %s" % proxy)
                    console_write(u"  proxy bypass: %s" % proxy_bypass)
                    console_write(u"  proxy username: %s" % proxy_username)
                    console_write(u"  proxy password: %s" % proxy_password)

                self.use_count += 1

                if self.debug and created_connection:
                    if self.scheme == 'https':
                        cert_struct = self.read_option(http_connection, self.INTERNET_OPTION_SECURITY_CERTIFICATE_STRUCT)

                        if cert_struct.lpszIssuerInfo:
                            issuer_info = cert_struct.lpszIssuerInfo.decode('cp1252')
                            issuer_parts = issuer_info.split("\r\n")
                        else:
                            issuer_parts = ['No issuer info']

                        if cert_struct.lpszSubjectInfo:
                            subject_info = cert_struct.lpszSubjectInfo.decode('cp1252')
                            subject_parts = subject_info.split("\r\n")
                        else:
                            subject_parts = ["No subject info"]

                        common_name = subject_parts[-1]

                        if cert_struct.ftStart.dwLowDateTime != 0 and cert_struct.ftStart.dwHighDateTime != 0:
                            issue_date = self.convert_filetime_to_datetime(cert_struct.ftStart)
                            issue_date = issue_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
                        else:
                            issue_date = u"No issue date"

                        if cert_struct.ftExpiry.dwLowDateTime != 0 and cert_struct.ftExpiry.dwHighDateTime != 0:
                            expiration_date = self.convert_filetime_to_datetime(cert_struct.ftExpiry)
                            expiration_date = expiration_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
                        else:
                            expiration_date = u"No expiration date"

                        console_write(u"WinINet HTTPS Debug General", True)
                        if changed_to_online:
                            console_write(u"  Internet Explorer was set to Work Offline, temporarily going online")
                        console_write(u"  Server SSL Certificate:")
                        console_write(u"    subject: %s" % ", ".join(subject_parts))
                        console_write(u"    issuer: %s" % ", ".join(issuer_parts))
                        console_write(u"    common name: %s" % common_name)
                        console_write(u"    issue date: %s" % issue_date)
                        console_write(u"    expire date: %s" % expiration_date)

                    elif changed_to_online:
                        console_write(u"WinINet HTTP Debug General", True)
                        console_write(u"  Internet Explorer was set to Work Offline, temporarily going online")

                if self.debug:
                    console_write(u"WinINet %s Debug Write" % self.scheme.upper(), True)
                    # Add in some known headers that WinINet sends since we can't get the real list
                    console_write(u"  GET %s HTTP/1.1" % path)
                    for header, value in request_headers.items():
                        console_write(u"  %s: %s" % (header, value))
                    console_write(u"  User-Agent: %s" % self.settings.get('user_agent'))
                    console_write(u"  Host: %s" % hostname)
                    console_write(u"  Connection: Keep-Alive")
                    console_write(u"  Cache-Control: no-cache")

                header_buffer_size = 8192

                try_again = True
                while try_again:
                    try_again = False

                    to_read_was_read = wintypes.DWORD(header_buffer_size)
                    headers_buffer = ctypes.create_string_buffer(header_buffer_size)

                    success = wininet.HttpQueryInfoA(http_connection, self.HTTP_QUERY_RAW_HEADERS_CRLF, ctypes.byref(headers_buffer), ctypes.byref(to_read_was_read), None)
                    if not success:
                        if ctypes.GetLastError() != self.ERROR_INSUFFICIENT_BUFFER:
                            error_string = u'%s %s during header read phase of downloading %s.' % (error_message, self.extract_error(), url)
                            raise DownloaderException(error_string)
                        # The error was a buffer that was too small, so try again
                        header_buffer_size = to_read_was_read.value
                        try_again = True
                        continue

                    headers = b''
                    if to_read_was_read.value > 0:
                        headers += headers_buffer.raw[:to_read_was_read.value]
                    headers = headers.decode('iso-8859-1').rstrip("\r\n").split("\r\n")

                    if self.debug:
                        console_write(u"WinINet %s Debug Read" % self.scheme.upper(), True)
                        for header in headers:
                            console_write(u"  %s" % header)

                buffer_length = 65536
                output_buffer = ctypes.create_string_buffer(buffer_length)
                bytes_read = wintypes.DWORD()

                result = b''
                try_again = True
                while try_again:
                    try_again = False
                    wininet.InternetReadFile(http_connection, output_buffer, buffer_length, ctypes.byref(bytes_read))
                    if bytes_read.value > 0:
                        result += output_buffer.raw[:bytes_read.value]
                        try_again = True

                general, headers = self.parse_headers(headers)
                self.handle_rate_limit(headers, url)

                if general['status'] == 503 and tries != 0:
                    # GitHub and BitBucket seem to rate limit via 503
                    error_string = u'Downloading %s was rate limited' % url
                    if tries:
                        error_string += ', trying again'
                        if self.debug:
                            console_write(error_string, True)
                    continue

                encoding = headers.get('content-encoding')
                if encoding:
                    result = self.decode_response(encoding, result)

                result = self.cache_result('get', url, general['status'],
                    headers, result)

                if general['status'] not in [200, 304]:
                    raise HttpError("HTTP error %s" % general['status'], general['status'])

                return result

            except (NonHttpError, HttpError) as e:

                # GitHub and BitBucket seem to time out a lot
                if str(e).find('timed out') != -1:
                    error_string = u'Downloading %s timed out' % url
                    if tries:
                        error_string += ', trying again'
                        if self.debug:
                            console_write(error_string, True)
                    continue

                error_string = u'%s %s downloading %s.' % (error_message, e, url)

            finally:
                if http_connection:
                    wininet.InternetCloseHandle(http_connection)

            break

        raise DownloaderException(error_string)

    def convert_filetime_to_datetime(self, filetime):
        """
        Windows returns times as 64-bit unsigned longs that are the number
        of hundreds of nanoseconds since Jan 1 1601. This converts it to
        a datetime object.

        :param filetime:
            A FileTime struct object

        :return:
            A (UTC) datetime object
        """

        hundreds_nano_seconds = struct.unpack('>Q', struct.pack('>LL', filetime.dwHighDateTime, filetime.dwLowDateTime))[0]
        seconds_since_1601 = hundreds_nano_seconds / 10000000
        epoch_seconds = seconds_since_1601 - 11644473600 # Seconds from Jan 1 1601 to Jan 1 1970
        return datetime.datetime.fromtimestamp(epoch_seconds)

    def extract_error(self):
        """
        Retrieves and formats an error from WinINet

        :return:
            A string with a nice description of the error
        """

        error_num = ctypes.GetLastError()
        raw_error_string = ctypes.FormatError(error_num)

        error_string = unicode_from_os(raw_error_string)

        # Try to fill in some known errors
        if error_string == u"<no description>":
            error_lookup = {
                12007: u'host not found',
                12029: u'connection refused',
                12057: u'error checking for server certificate revocation',
                12169: u'invalid secure certificate',
                12157: u'secure channel error, server not providing SSL',
                12002: u'operation timed out'
            }
            if error_num in error_lookup:
                error_string = error_lookup[error_num]

        if error_string == u"<no description>":
            return u"(errno %s)" % error_num

        error_string = error_string[0].upper() + error_string[1:]
        return u"%s (errno %s)" % (error_string, error_num)

    def supports_ssl(self):
        """
        Indicates if the object can handle HTTPS requests

        :return:
            If the object supports HTTPS requests
        """

        return True

    def read_option(self, handle, option):
        """
        Reads information about the internet connection, which may be a string or struct

        :param handle:
            The handle to query for the info

        :param option:
            The (int) option to get

        :return:
            A string, or one of the InternetCertificateInfo or InternetProxyInfo structs
        """

        option_buffer_size = 8192
        try_again = True

        while try_again:
            try_again = False

            to_read_was_read = wintypes.DWORD(option_buffer_size)
            option_buffer = ctypes.create_string_buffer(option_buffer_size)
            ref = ctypes.byref(option_buffer)

            success = wininet.InternetQueryOptionA(handle, option, ref, ctypes.byref(to_read_was_read))
            if not success:
                if ctypes.GetLastError() != self.ERROR_INSUFFICIENT_BUFFER:
                    raise NonHttpError(self.extract_error())
                # The error was a buffer that was too small, so try again
                option_buffer_size = to_read_was_read.value
                try_again = True
                continue

            if option == self.INTERNET_OPTION_SECURITY_CERTIFICATE_STRUCT:
                length = min(len(option_buffer), ctypes.sizeof(InternetCertificateInfo))
                cert_info = InternetCertificateInfo()
                ctypes.memmove(ctypes.addressof(cert_info), option_buffer, length)
                return cert_info
            elif option == self.INTERNET_OPTION_PROXY:
                length = min(len(option_buffer), ctypes.sizeof(InternetProxyInfo))
                proxy_info = InternetProxyInfo()
                ctypes.memmove(ctypes.addressof(proxy_info), option_buffer, length)
                return proxy_info
            else:
                option = b''
                if to_read_was_read.value > 0:
                    option += option_buffer.raw[:to_read_was_read.value]
                return option.decode('cp1252').rstrip("\x00")

    def parse_headers(self, output):
        """
        Parses HTTP headers into two dict objects

        :param output:
            An array of header lines

        :return:
            A tuple of (general, headers) where general is a dict with the keys:
              `version` - HTTP version number (string)
              `status` - HTTP status code (integer)
              `message` - HTTP status message (string)
            And headers is a dict with the keys being lower-case version of the
            HTTP header names.
        """

        general = {
            'version': '0.9',
            'status':  200,
            'message': 'OK'
        }
        headers = {}
        for line in output:
            line = line.lstrip()
            if line.find('HTTP/') == 0:
                match = re.match('HTTP/(\d\.\d)\s+(\d+)\s+(.*)$', line)
                if match:
                    general['version'] = match.group(1)
                    general['status'] = int(match.group(2))
                    general['message'] = match.group(3)
                # The user‘s proxy is sending bad HTTP headers :-(
                else:
                    match = re.match('HTTP/(\d\.\d)\s+(\d+)$', line)
                    general['version'] = match.group(1)
                    general['status'] = int(match.group(2))
                    # Since the header didn‘t include the message, use our copy
                    message = self.HTTP_STATUS_MESSAGES[general['status']]
                    general['message'] = message
            else:
                name, value = line.split(':', 1)
                headers[name.lower()] = value.strip()

        return (general, headers)


class FileTime(ctypes.Structure):
    """
    A Windows struct used by InternetCertificateInfo for certificate
    date information
    """

    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD)
    ]


class InternetCertificateInfo(ctypes.Structure):
    """
    A Windows struct used to store information about an SSL certificate
    """

    _fields_ = [
        ("ftExpiry", FileTime),
        ("ftStart", FileTime),
        ("lpszSubjectInfo", ctypes.c_char_p),
        ("lpszIssuerInfo", ctypes.c_char_p),
        ("lpszProtocolName", ctypes.c_char_p),
        ("lpszSignatureAlgName", ctypes.c_char_p),
        ("lpszEncryptionAlgName", ctypes.c_char_p),
        ("dwKeySize", wintypes.DWORD)
    ]


class InternetProxyInfo(ctypes.Structure):
    """
    A Windows struct usd to store information about the configured proxy server
    """

    _fields_ = [
        ("dwAccessType", wintypes.DWORD),
        ("lpszProxy", ctypes.c_char_p),
        ("lpszProxyBypass", ctypes.c_char_p)
    ]


class InternetConnectedInfo(ctypes.Structure):
    """
    A Windows struct usd to store information about the global internet connection state
    """

    _fields_ = [
        ("dwConnectedState", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD)
    ]

########NEW FILE########
__FILENAME__ = download_manager
import sys
import re
import socket
from threading import Lock, Timer
from contextlib import contextmanager

try:
    # Python 3
    from urllib.parse import urlparse
except (ImportError):
    # Python 2
    from urlparse import urlparse

from . import __version__

from .show_error import show_error
from .console_write import console_write
from .cache import set_cache, get_cache
from .unicode import unicode_from_os

from .downloaders import DOWNLOADERS
from .downloaders.binary_not_found_error import BinaryNotFoundError
from .downloaders.rate_limit_exception import RateLimitException
from .downloaders.no_ca_cert_exception import NoCaCertException
from .downloaders.downloader_exception import DownloaderException
from .http_cache import HttpCache


# A dict of domains - each points to a list of downloaders
_managers = {}

# How many managers are currently checked out
_in_use = 0

# Make sure connection management doesn't run into threading issues
_lock = Lock()

# A timer used to disconnect all managers after a period of no usage
_timer = None


@contextmanager
def downloader(url, settings):
    try:
        manager = None
        manager = _grab(url, settings)
        yield manager

    finally:
        if manager:
            _release(url, manager)


def _grab(url, settings):
    global _managers, _lock, _in_use, _timer

    _lock.acquire()
    try:
        if _timer:
            _timer.cancel()
            _timer = None

        parsed = urlparse(url)
        if not parsed or not parsed.hostname:
            raise DownloaderException(u'The URL "%s" is malformed' % url)
        hostname = parsed.hostname.lower()
        if hostname not in _managers:
            _managers[hostname] = []

        if not _managers[hostname]:
            _managers[hostname].append(DownloadManager(settings))

        _in_use += 1

        return _managers[hostname].pop()

    finally:
        _lock.release()


def _release(url, manager):
    global _managers, _lock, _in_use, _timer

    _lock.acquire()
    try:
        hostname = urlparse(url).hostname.lower()
        _managers[hostname].insert(0, manager)

        _in_use -= 1

        if _timer:
            _timer.cancel()
            _timer = None

        if _in_use == 0:
            _timer = Timer(5.0, close_all_connections)
            _timer.start()

    finally:
        _lock.release()


def close_all_connections():
    global _managers, _lock, _in_use, _timer

    _lock.acquire()
    try:
        if _timer:
            _timer.cancel()
            _timer = None

        for domain, managers in _managers.items():
            for manager in managers:
                manager.close()
        _managers = {}

    finally:
        _lock.release()


class DownloadManager(object):
    def __init__(self, settings):
        # Cache the downloader for re-use
        self.downloader = None

        user_agent = settings.get('user_agent')
        if user_agent and user_agent.find('%s') != -1:
            settings['user_agent'] = user_agent % __version__

        self.settings = settings
        if settings.get('http_cache'):
            cache_length = settings.get('http_cache_length', 604800)
            self.settings['cache'] = HttpCache(cache_length)

    def close(self):
        if self.downloader:
            self.downloader.close()
            self.downloader = None

    def fetch(self, url, error_message, prefer_cached=False):
        """
        Downloads a URL and returns the contents

        :param url:
            The string URL to download

        :param error_message:
            The error message to include if the download fails

        :param prefer_cached:
            If cached version of the URL content is preferred over a new request

        :raises:
            DownloaderException: if there was an error downloading the URL

        :return:
            The string contents of the URL
        """

        is_ssl = re.search('^https://', url) != None

        # Make sure we have a downloader, and it supports SSL if we need it
        if not self.downloader or (is_ssl and not self.downloader.supports_ssl()):
            for downloader_class in DOWNLOADERS:
                try:
                    downloader = downloader_class(self.settings)
                    if is_ssl and not downloader.supports_ssl():
                        continue
                    self.downloader = downloader
                    break
                except (BinaryNotFoundError):
                    pass

        if not self.downloader:
            error_string = u'Unable to download %s due to no ssl module available and no capable program found. Please install curl or wget.' % url
            show_error(error_string)
            raise DownloaderException(error_string)

        url = url.replace(' ', '%20')
        hostname = urlparse(url).hostname
        if hostname:
            hostname = hostname.lower()
        timeout = self.settings.get('timeout', 3)

        rate_limited_domains = get_cache('rate_limited_domains', [])
        no_ca_cert_domains = get_cache('no_ca_cert_domains', [])

        if self.settings.get('debug'):
            try:
                ip = socket.gethostbyname(hostname)
            except (socket.gaierror) as e:
                ip = unicode_from_os(e)
            except (TypeError) as e:
                ip = None

            console_write(u"Download Debug", True)
            console_write(u"  URL: %s" % url)
            console_write(u"  Resolved IP: %s" % ip)
            console_write(u"  Timeout: %s" % str(timeout))

        if hostname in rate_limited_domains:
            error_string = u"Skipping due to hitting rate limit for %s" % hostname
            if self.settings.get('debug'):
                console_write(u"  %s" % error_string)
            raise DownloaderException(error_string)

        if hostname in no_ca_cert_domains:
            error_string = u"  Skipping since there are no CA certs for %s" % hostname
            if self.settings.get('debug'):
                console_write(u"  %s" % error_string)
            raise DownloaderException(error_string)

        try:
            return self.downloader.download(url, error_message, timeout, 3, prefer_cached)

        except (RateLimitException) as e:

            rate_limited_domains.append(hostname)
            set_cache('rate_limited_domains', rate_limited_domains, self.settings.get('cache_length'))

            error_string = (u'Hit rate limit of %s for %s, skipping all futher ' +
                u'download requests for this domain') % (e.limit, e.domain)
            console_write(error_string, True)
            raise

        except (NoCaCertException) as e:

            no_ca_cert_domains.append(hostname)
            set_cache('no_ca_cert_domains', no_ca_cert_domains, self.settings.get('cache_length'))

            error_string = (u'No CA certs available for %s, skipping all futher ' +
                u'download requests for this domain. If you are on a trusted ' +
                u'network, you can add the CA certs by running the "Grab ' +
                u'CA Certs" command from the command palette.') % e.domain
            console_write(error_string, True)
            raise

########NEW FILE########
__FILENAME__ = file_not_found_error
class FileNotFoundError(Exception):
    """If a file is not found"""

    pass

########NEW FILE########
__FILENAME__ = debuggable_https_response
from .debuggable_http_response import DebuggableHTTPResponse


class DebuggableHTTPSResponse(DebuggableHTTPResponse):
    """
    A version of DebuggableHTTPResponse that sets the debug protocol to HTTPS
    """

    _debug_protocol = 'HTTPS'

########NEW FILE########
__FILENAME__ = debuggable_http_connection
import os
import re
import socket

try:
    # Python 3
    from http.client import HTTPConnection
    from urllib.error import URLError
except (ImportError):
    # Python 2
    from httplib import HTTPConnection
    from urllib2 import URLError

from ..console_write import console_write
from .debuggable_http_response import DebuggableHTTPResponse


class DebuggableHTTPConnection(HTTPConnection):
    """
    A custom HTTPConnection that formats debugging info for Sublime Text
    """

    response_class = DebuggableHTTPResponse
    _debug_protocol = 'HTTP'

    def __init__(self, host, port=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
            **kwargs):
        self.passwd = kwargs.get('passwd')

        # Python 2.6.1 on OS X 10.6 does not include these
        self._tunnel_host = None
        self._tunnel_port = None
        self._tunnel_headers = {}
        if 'debug' in kwargs and kwargs['debug']:
            self.debuglevel = 5
        elif 'debuglevel' in kwargs:
            self.debuglevel = kwargs['debuglevel']

        HTTPConnection.__init__(self, host, port=port, timeout=timeout)

    def connect(self):
        if self.debuglevel == -1:
            console_write(u'Urllib %s Debug General' % self._debug_protocol, True)
            console_write(u"  Connecting to %s on port %s" % (self.host, self.port))
        HTTPConnection.connect(self)

    def send(self, string):
        # We have to use a positive debuglevel to get it passed to the
        # HTTPResponse object, however we don't want to use it because by
        # default debugging prints to the stdout and we can't capture it, so
        # we temporarily set it to -1 for the standard httplib code
        reset_debug = False
        if self.debuglevel == 5:
            reset_debug = 5
            self.debuglevel = -1
        HTTPConnection.send(self, string)
        if reset_debug or self.debuglevel == -1:
            if len(string.strip()) > 0:
                console_write(u'Urllib %s Debug Write' % self._debug_protocol, True)
                for line in string.strip().splitlines():
                    console_write(u'  ' + line.decode('iso-8859-1'))
            if reset_debug:
                self.debuglevel = reset_debug

    def request(self, method, url, body=None, headers={}):
        original_headers = headers.copy()

        # By default urllib2 and urllib.request override the Connection header,
        # however, it is preferred to be able to re-use it
        original_headers['Connection'] = 'Keep-Alive'

        HTTPConnection.request(self, method, url, body, original_headers)

########NEW FILE########
__FILENAME__ = debuggable_http_handler
import sys

try:
    # Python 3
    from urllib.request import HTTPHandler
except (ImportError):
    # Python 2
    from urllib2 import HTTPHandler

from .debuggable_http_connection import DebuggableHTTPConnection
from .persistent_handler import PersistentHandler


class DebuggableHTTPHandler(PersistentHandler, HTTPHandler):
    """
    A custom HTTPHandler that formats debugging info for Sublime Text
    """

    def __init__(self, debuglevel=0, debug=False, **kwargs):
        # This is a special value that will not trigger the standard debug
        # functionality, but custom code where we can format the output
        if debug:
            self._debuglevel = 5
        else:
            self._debuglevel = debuglevel
        self.passwd = kwargs.get('passwd')

    def http_open(self, req):
        def http_class_wrapper(host, **kwargs):
            kwargs['passwd'] = self.passwd
            if 'debuglevel' not in kwargs:
                kwargs['debuglevel'] = self._debuglevel
            return DebuggableHTTPConnection(host, **kwargs)

        return self.do_open(http_class_wrapper, req)

########NEW FILE########
__FILENAME__ = debuggable_http_response
try:
    # Python 3
    from http.client import HTTPResponse, IncompleteRead
except (ImportError):
    # Python 2
    from httplib import HTTPResponse, IncompleteRead

from ..console_write import console_write


class DebuggableHTTPResponse(HTTPResponse):
    """
    A custom HTTPResponse that formats debugging info for Sublime Text
    """

    _debug_protocol = 'HTTP'

    def __init__(self, sock, debuglevel=0, method=None, **kwargs):
        # We have to use a positive debuglevel to get it passed to here,
        # however we don't want to use it because by default debugging prints
        # to the stdout and we can't capture it, so we use a special -1 value
        if debuglevel == 5:
            debuglevel = -1
        HTTPResponse.__init__(self, sock, debuglevel=debuglevel, method=method)

    def begin(self):
        return_value = HTTPResponse.begin(self)
        if self.debuglevel == -1:
            console_write(u'Urllib %s Debug Read' % self._debug_protocol, True)

            # Python 2
            if hasattr(self.msg, 'headers'):
                headers = self.msg.headers
            # Python 3
            else:
                headers = []
                for header in self.msg:
                    headers.append("%s: %s" % (header, self.msg[header]))

            versions = {
                9: 'HTTP/0.9',
                10: 'HTTP/1.0',
                11: 'HTTP/1.1'
            }
            status_line = versions[self.version] + ' ' + str(self.status) + ' ' + self.reason
            headers.insert(0, status_line)
            for line in headers:
                console_write(u"  %s" % line.rstrip())
        return return_value

    def is_keep_alive(self):
        # Python 2
        if hasattr(self.msg, 'headers'):
            connection = self.msg.getheader('connection')
        # Python 3
        else:
            connection = self.msg['connection']
        if connection and connection.lower() == 'keep-alive':
            return True
        return False

    def read(self, *args):
        try:
            return HTTPResponse.read(self, *args)
        except (IncompleteRead) as e:
            return e.partial

########NEW FILE########
__FILENAME__ = invalid_certificate_exception
try:
    # Python 3
    from http.client import HTTPException
    from urllib.error import URLError
except (ImportError):
    # Python 2
    from httplib import HTTPException
    from urllib2 import URLError


class InvalidCertificateException(HTTPException, URLError):
    """
    An exception for when an SSL certification is not valid for the URL
    it was presented for.
    """

    def __init__(self, host, cert, reason):
        HTTPException.__init__(self)
        self.host = host
        self.cert = cert
        self.reason = reason

    def __str__(self):
        return ('Host %s returned an invalid certificate (%s) %s\n' %
            (self.host, self.reason, self.cert))

########NEW FILE########
__FILENAME__ = persistent_handler
import sys
import socket

try:
    # Python 3
    from urllib.error import URLError
except ImportError:
    # Python 2
    from urllib2 import URLError
    from urllib import addinfourl

from ..console_write import console_write


class PersistentHandler:
    connection = None
    use_count = 0

    def close(self):
        if self.connection:
            if self._debuglevel == 5:
                s = '' if self.use_count == 1 else 's'
                console_write(u"Urllib %s Debug General" % self.connection._debug_protocol, True)
                console_write(u"  Closing connection to %s on port %s after %s request%s" % (
                    self.connection.host, self.connection.port, self.use_count, s))
            self.connection.close()
            self.connection = None
            self.use_count = 0

    def do_open(self, http_class, req):
        # Large portions from Python 3.3 Lib/urllib/request.py and
        # Python 2.6 Lib/urllib2.py

        if sys.version_info >= (3,):
            host = req.host
        else:
            host = req.get_host()

        if not host:
            raise URLError('no host given')

        if self.connection and self.connection.host != host:
            self.close()

        # Re-use the connection if possible
        self.use_count += 1
        if not self.connection:
            h = http_class(host, timeout=req.timeout)
        else:
            h = self.connection
            if self._debuglevel == 5:
                console_write(u"Urllib %s Debug General" % h._debug_protocol, True)
                console_write(u"  Re-using connection to %s on port %s for request #%s" % (
                    h.host, h.port, self.use_count))

        if sys.version_info >= (3,):
            headers = dict(req.unredirected_hdrs)
            headers.update(dict((k, v) for k, v in req.headers.items()
                                if k not in headers))
            headers = dict((name.title(), val) for name, val in headers.items())

        else:
            h.set_debuglevel(self._debuglevel)

            headers = dict(req.headers)
            headers.update(req.unredirected_hdrs)
            headers = dict(
                (name.title(), val) for name, val in headers.items())

        if req._tunnel_host and not self.connection:
            tunnel_headers = {}
            proxy_auth_hdr = "Proxy-Authorization"
            if proxy_auth_hdr in headers:
                tunnel_headers[proxy_auth_hdr] = headers[proxy_auth_hdr]
                del headers[proxy_auth_hdr]

            if sys.version_info >= (3,):
                h.set_tunnel(req._tunnel_host, headers=tunnel_headers)
            else:
                h._set_tunnel(req._tunnel_host, headers=tunnel_headers)

        try:
            if sys.version_info >= (3,):
                h.request(req.get_method(), req.selector, req.data, headers)
            else:
                h.request(req.get_method(), req.get_selector(), req.data, headers)
        except socket.error as err: # timeout error
            h.close()
            raise URLError(err)
        else:
            r = h.getresponse()

        # Keep the connection around for re-use
        if r.is_keep_alive():
            self.connection = h
        else:
            if self._debuglevel == 5:
                s = '' if self.use_count == 1 else 's'
                console_write(u"Urllib %s Debug General" % h._debug_protocol, True)
                console_write(u"  Closing connection to %s on port %s after %s request%s" % (
                    h.host, h.port, self.use_count, s))
            self.use_count = 0
            self.connection = None

        if sys.version_info >= (3,):
            r.url = req.get_full_url()
            r.msg = r.reason
            return r

        r.recv = r.read
        fp = socket._fileobject(r, close=True)

        resp = addinfourl(fp, r.msg, req.get_full_url())
        resp.code = r.status
        resp.msg = r.reason
        return resp

########NEW FILE########
__FILENAME__ = validating_https_connection
import re
import socket
import base64
import hashlib
import os
import sys

try:
    # Python 3
    from http.client import HTTPS_PORT
    from urllib.request import parse_keqv_list, parse_http_list
except (ImportError):
    # Python 2
    from httplib import HTTPS_PORT
    from urllib2 import parse_keqv_list, parse_http_list

from ..console_write import console_write
from .debuggable_https_response import DebuggableHTTPSResponse
from .debuggable_http_connection import DebuggableHTTPConnection
from .invalid_certificate_exception import InvalidCertificateException


# The following code is wrapped in a try because the Linux versions of Sublime
# Text do not include the ssl module due to the fact that different distros
# have different versions
try:
    import ssl

    class ValidatingHTTPSConnection(DebuggableHTTPConnection):
        """
        A custom HTTPConnection class that validates SSL certificates, and
        allows proxy authentication for HTTPS connections.
        """

        default_port = HTTPS_PORT

        response_class = DebuggableHTTPSResponse
        _debug_protocol = 'HTTPS'

        def __init__(self, host, port=None, key_file=None, cert_file=None,
                ca_certs=None, **kwargs):
            passed_args = {}
            if 'timeout' in kwargs:
                passed_args['timeout'] = kwargs['timeout']
            if 'debug' in kwargs:
                passed_args['debug'] = kwargs['debug']
            DebuggableHTTPConnection.__init__(self, host, port, **passed_args)

            self.passwd = kwargs.get('passwd')
            self.key_file = key_file
            self.cert_file = cert_file
            self.ca_certs = ca_certs
            if 'user_agent' in kwargs:
                self.user_agent = kwargs['user_agent']
            if self.ca_certs:
                self.cert_reqs = ssl.CERT_REQUIRED
            else:
                self.cert_reqs = ssl.CERT_NONE

        def get_valid_hosts_for_cert(self, cert):
            """
            Returns a list of valid hostnames for an SSL certificate

            :param cert: A dict from SSLSocket.getpeercert()

            :return: An array of hostnames
            """

            if 'subjectAltName' in cert:
                return [x[1] for x in cert['subjectAltName']
                             if x[0].lower() == 'dns']
            else:
                return [x[0][1] for x in cert['subject']
                                if x[0][0].lower() == 'commonname']

        def validate_cert_host(self, cert, hostname):
            """
            Checks if the cert is valid for the hostname

            :param cert: A dict from SSLSocket.getpeercert()

            :param hostname: A string hostname to check

            :return: A boolean if the cert is valid for the hostname
            """

            hosts = self.get_valid_hosts_for_cert(cert)
            for host in hosts:
                host_re = host.replace('.', '\.').replace('*', '[^.]*')
                if re.search('^%s$' % (host_re,), hostname, re.I):
                    return True
            return False

        def _tunnel(self):
            """
            This custom _tunnel method allows us to read and print the debug
            log for the whole response before throwing an error, and adds
            support for proxy authentication
            """

            self._proxy_host = self.host
            self._proxy_port = self.port
            self._set_hostport(self._tunnel_host, self._tunnel_port)

            self._tunnel_headers['Host'] = u"%s:%s" % (self.host, self.port)
            self._tunnel_headers['User-Agent'] = self.user_agent
            self._tunnel_headers['Proxy-Connection'] = 'Keep-Alive'

            request = "CONNECT %s:%d HTTP/1.1\r\n" % (self.host, self.port)
            for header, value in self._tunnel_headers.items():
                request += "%s: %s\r\n" % (header, value)
            request += "\r\n"

            if sys.version_info >= (3,):
                request = bytes(request, 'iso-8859-1')

            self.send(request)

            response = self.response_class(self.sock, method=self._method)
            (version, code, message) = response._read_status()

            status_line = u"%s %s %s" % (version, code, message.rstrip())
            headers = [status_line]

            if self.debuglevel in [-1, 5]:
                console_write(u'Urllib %s Debug Read' % self._debug_protocol, True)
                console_write(u"  %s" % status_line)

            content_length = 0
            close_connection = False
            while True:
                line = response.fp.readline()

                if sys.version_info >= (3,):
                    line = str(line, encoding='iso-8859-1')

                if line == '\r\n':
                    break

                headers.append(line.rstrip())

                parts = line.rstrip().split(': ', 1)
                name = parts[0].lower()
                value = parts[1].lower().strip()
                if name == 'content-length':
                    content_length = int(value)

                if name in ['connection', 'proxy-connection'] and value == 'close':
                    close_connection = True

                if self.debuglevel in [-1, 5]:
                    console_write(u"  %s" % line.rstrip())

            # Handle proxy auth for SSL connections since regular urllib punts on this
            if code == 407 and self.passwd and 'Proxy-Authorization' not in self._tunnel_headers:
                if content_length:
                    response._safe_read(content_length)

                supported_auth_methods = {}
                for line in headers:
                    parts = line.split(': ', 1)
                    if parts[0].lower() != 'proxy-authenticate':
                        continue
                    details = parts[1].split(' ', 1)
                    supported_auth_methods[details[0].lower()] = details[1] if len(details) > 1 else ''

                username, password = self.passwd.find_user_password(None, "%s:%s" % (
                    self._proxy_host, self._proxy_port))

                if 'digest' in supported_auth_methods:
                    response_value = self.build_digest_response(
                        supported_auth_methods['digest'], username, password)
                    if response_value:
                        self._tunnel_headers['Proxy-Authorization'] = u"Digest %s" % response_value

                elif 'basic' in supported_auth_methods:
                    response_value = u"%s:%s" % (username, password)
                    response_value = base64.b64encode(response_value).strip()
                    self._tunnel_headers['Proxy-Authorization'] = u"Basic %s" % response_value

                if 'Proxy-Authorization' in self._tunnel_headers:
                    self.host = self._proxy_host
                    self.port = self._proxy_port

                    # If the proxy wanted the connection closed, we need to make a new connection
                    if close_connection:
                        self.sock.close()
                        self.sock = socket.create_connection((self.host, self.port), self.timeout)

                    return self._tunnel()

            if code != 200:
                self.close()
                raise socket.error("Tunnel connection failed: %d %s" % (code,
                    message.strip()))

        def build_digest_response(self, fields, username, password):
            """
            Takes a Proxy-Authenticate: Digest header and creates a response
            header

            :param fields:
                The string portion of the Proxy-Authenticate header after
                "Digest "

            :param username:
                The username to use for the response

            :param password:
                The password to use for the response

            :return:
                None if invalid Proxy-Authenticate header, otherwise the
                string of fields for the Proxy-Authorization: Digest header
            """

            fields = parse_keqv_list(parse_http_list(fields))

            realm = fields.get('realm')
            nonce = fields.get('nonce')
            qop = fields.get('qop')
            algorithm = fields.get('algorithm')
            if algorithm:
                algorithm = algorithm.lower()
            opaque = fields.get('opaque')

            if algorithm in ['md5', None]:
                def md5hash(string):
                    return hashlib.md5(string).hexdigest()
                hash = md5hash

            elif algorithm == 'sha':
                def sha1hash(string):
                    return hashlib.sha1(string).hexdigest()
                hash = sha1hash

            else:
                return None

            host_port = u"%s:%s" % (self.host, self.port)

            a1 = "%s:%s:%s" % (username, realm, password)
            a2 = "CONNECT:%s" % host_port
            ha1 = hash(a1)
            ha2 = hash(a2)

            if qop == None:
                response = hash(u"%s:%s:%s" % (ha1, nonce, ha2))
            elif qop == 'auth':
                nc = '00000001'
                cnonce = hash(os.urandom(8))[:8]
                response = hash(u"%s:%s:%s:%s:%s:%s" % (ha1, nonce, nc, cnonce, qop, ha2))
            else:
                return None

            response_fields = {
                'username': username,
                'realm': realm,
                'nonce': nonce,
                'response': response,
                'uri': host_port
            }
            if algorithm:
                response_fields['algorithm'] = algorithm
            if qop == 'auth':
                response_fields['nc'] = nc
                response_fields['cnonce'] = cnonce
                response_fields['qop'] = qop
            if opaque:
                response_fields['opaque'] = opaque

            return ', '.join([u"%s=\"%s\"" % (field, response_fields[field]) for field in response_fields])

        def connect(self):
            """
            Adds debugging and SSL certification validation
            """

            if self.debuglevel == -1:
                console_write(u"Urllib HTTPS Debug General", True)
                console_write(u"  Connecting to %s on port %s" % (self.host, self.port))

            self.sock = socket.create_connection((self.host, self.port), self.timeout)
            if self._tunnel_host:
                self._tunnel()

            if self.debuglevel == -1:
                console_write(u"Urllib HTTPS Debug General", True)
                console_write(u"  Connecting to %s on port %s" % (self.host, self.port))
                console_write(u"  CA certs file at %s" % (self.ca_certs.decode(sys.getfilesystemencoding())))

            self.sock = ssl.wrap_socket(self.sock, keyfile=self.key_file,
                certfile=self.cert_file, cert_reqs=self.cert_reqs,
                ca_certs=self.ca_certs)

            if self.debuglevel == -1:
                console_write(u"  Successfully upgraded connection to %s:%s with SSL" % (
                    self.host, self.port))

            # This debugs and validates the SSL certificate
            if self.cert_reqs & ssl.CERT_REQUIRED:
                cert = self.sock.getpeercert()

                if self.debuglevel == -1:
                    subjectMap = {
                        'organizationName': 'O',
                        'commonName': 'CN',
                        'organizationalUnitName': 'OU',
                        'countryName': 'C',
                        'serialNumber': 'serialNumber',
                        'commonName': 'CN',
                        'localityName': 'L',
                        'stateOrProvinceName': 'S'
                    }
                    subject_list = list(cert['subject'])
                    subject_list.reverse()
                    subject_parts = []
                    for pair in subject_list:
                        if pair[0][0] in subjectMap:
                            field_name = subjectMap[pair[0][0]]
                        else:
                            field_name = pair[0][0]
                        subject_parts.append(field_name + '=' + pair[0][1])

                    console_write(u"  Server SSL certificate:")
                    console_write(u"    subject: " + ','.join(subject_parts))
                    if 'subjectAltName' in cert:
                        console_write(u"    common name: " + cert['subjectAltName'][0][1])
                    if 'notAfter' in cert:
                        console_write(u"    expire date: " + cert['notAfter'])

                hostname = self.host.split(':', 0)[0]

                if not self.validate_cert_host(cert, hostname):
                    if self.debuglevel == -1:
                        console_write(u"  Certificate INVALID")

                    raise InvalidCertificateException(hostname, cert,
                        'hostname mismatch')

                if self.debuglevel == -1:
                    console_write(u"  Certificate validated for %s" % hostname)

except (ImportError):
    pass

########NEW FILE########
__FILENAME__ = validating_https_handler
try:
    # Python 3
    from urllib.error import URLError
    import urllib.request as urllib_compat
except (ImportError):
    # Python 2
    from urllib2 import URLError
    import urllib2 as urllib_compat


# The following code is wrapped in a try because the Linux versions of Sublime
# Text do not include the ssl module due to the fact that different distros
# have different versions
try:
    import ssl

    from .validating_https_connection import ValidatingHTTPSConnection
    from .invalid_certificate_exception import InvalidCertificateException
    from .persistent_handler import PersistentHandler

    if hasattr(urllib_compat, 'HTTPSHandler'):
        class ValidatingHTTPSHandler(PersistentHandler, urllib_compat.HTTPSHandler):
            """
            A urllib handler that validates SSL certificates for HTTPS requests
            """

            def __init__(self, **kwargs):
                # This is a special value that will not trigger the standard debug
                # functionality, but custom code where we can format the output
                self._debuglevel = 0
                if 'debug' in kwargs and kwargs['debug']:
                    self._debuglevel = 5
                elif 'debuglevel' in kwargs:
                    self._debuglevel = kwargs['debuglevel']
                self._connection_args = kwargs

            def https_open(self, req):
                def http_class_wrapper(host, **kwargs):
                    full_kwargs = dict(self._connection_args)
                    full_kwargs.update(kwargs)
                    return ValidatingHTTPSConnection(host, **full_kwargs)

                try:
                    return self.do_open(http_class_wrapper, req)
                except URLError as e:
                    if type(e.reason) == ssl.SSLError and e.reason.args[0] == 1:
                        raise InvalidCertificateException(req.host, '',
                                                          e.reason.args[1])
                    raise

            https_request = urllib_compat.AbstractHTTPHandler.do_request_
    else:
        raise ImportError()

except (ImportError) as e:

    class ValidatingHTTPSHandler():
        def __init__(self, **kwargs):
            raise e

########NEW FILE########
__FILENAME__ = http_cache
import os
import time

import sublime

from .open_compat import open_compat, read_compat


class HttpCache(object):
    """
    A data store for caching HTTP response data.
    """

    def __init__(self, ttl):
        self.base_path = os.path.join(sublime.packages_path(), 'User', 'Package Control.cache')
        if not os.path.exists(self.base_path):
            os.mkdir(self.base_path)
        self.clear(int(ttl))

    def clear(self, ttl):
        """
        Removes all cache entries older than the TTL

        :param ttl:
            The number of seconds a cache entry should be valid for
        """

        ttl = int(ttl)

        for filename in os.listdir(self.base_path):
            path = os.path.join(self.base_path, filename)
            # There should not be any folders in the cache dir, but we
            # ignore to prevent an exception
            if os.path.isdir(path):
                continue
            mtime = os.stat(path).st_mtime
            if mtime < time.time() - ttl:
                os.unlink(path)

    def get(self, key):
        """
        Returns a cached value

        :param key:
            The key to fetch the cache for

        :return:
            The (binary) cached value, or False
        """

        cache_file = os.path.join(self.base_path, key)
        if not os.path.exists(cache_file):
            return False

        with open_compat(cache_file, 'rb') as f:
            return read_compat(f)

    def has(self, key):
        cache_file = os.path.join(self.base_path, key)
        return os.path.exists(cache_file)

    def set(self, key, content):
        """
        Saves a value in the cache

        :param key:
            The key to save the cache with

        :param content:
            The (binary) content to cache
        """

        cache_file = os.path.join(self.base_path, key)
        with open_compat(cache_file, 'wb') as f:
            f.write(content)

########NEW FILE########
__FILENAME__ = open_compat
import os
import sys

from .file_not_found_error import FileNotFoundError


def open_compat(path, mode='r'):
    if mode in ['r', 'rb'] and not os.path.exists(path):
        raise FileNotFoundError(u"The file \"%s\" could not be found" % path)

    if sys.version_info >= (3,):
        encoding = 'utf-8'
        errors = 'replace'
        if mode in ['rb', 'wb', 'ab']:
            encoding = None
            errors = None
        return open(path, mode, encoding=encoding, errors=errors)

    else:
        return open(path, mode)


def read_compat(file_obj):
    if sys.version_info >= (3,):
        return file_obj.read()
    else:
        return unicode(file_obj.read(), 'utf-8', errors='replace')

########NEW FILE########
__FILENAME__ = package_cleanup
import threading
import os

import sublime

from .show_error import show_error
from .console_write import console_write
from .unicode import unicode_from_os
from .rmtree import rmtree
from .clear_directory import clear_directory
from .automatic_upgrader import AutomaticUpgrader
from .package_manager import PackageManager
from .package_renamer import PackageRenamer
from .open_compat import open_compat
from .package_io import package_file_exists


class PackageCleanup(threading.Thread, PackageRenamer):
    """
    Cleans up folders for packages that were removed, but that still have files
    in use.
    """

    def __init__(self):
        self.manager = PackageManager()
        self.load_settings()
        threading.Thread.__init__(self)

    def run(self):
        found_pkgs = []
        installed_pkgs = list(self.installed_packages)
        for package_name in os.listdir(sublime.packages_path()):
            package_dir = os.path.join(sublime.packages_path(), package_name)

            # Cleanup packages that could not be removed due to in-use files
            cleanup_file = os.path.join(package_dir, 'package-control.cleanup')
            if os.path.exists(cleanup_file):
                try:
                    rmtree(package_dir)
                    console_write(u'Removed old directory for package %s' % package_name, True)

                except (OSError) as e:
                    if not os.path.exists(cleanup_file):
                        open_compat(cleanup_file, 'w').close()

                    error_string = (u'Unable to remove old directory for package ' +
                        u'%s - deferring until next start: %s') % (
                        package_name, unicode_from_os(e))
                    console_write(error_string, True)

            # Finish reinstalling packages that could not be upgraded due to
            # in-use files
            reinstall = os.path.join(package_dir, 'package-control.reinstall')
            if os.path.exists(reinstall):
                metadata_path = os.path.join(package_dir, 'package-metadata.json')
                if not clear_directory(package_dir, [metadata_path]):
                    if not os.path.exists(reinstall):
                        open_compat(reinstall, 'w').close()
                    # Assigning this here prevents the callback from referencing the value
                    # of the "package_name" variable when it is executed
                    restart_message = (u'An error occurred while trying to ' +
                        u'finish the upgrade of %s. You will most likely need to ' +
                        u'restart your computer to complete the upgrade.') % package_name

                    def show_still_locked():
                        show_error(restart_message)
                    sublime.set_timeout(show_still_locked, 10)
                else:
                    self.manager.install_package(package_name)

            # This adds previously installed packages from old versions of PC
            if package_file_exists(package_name, 'package-metadata.json') and \
                    package_name not in self.installed_packages:
                installed_pkgs.append(package_name)
                params = {
                    'package': package_name,
                    'operation': 'install',
                    'version': \
                        self.manager.get_metadata(package_name).get('version')
                }
                self.manager.record_usage(params)

            found_pkgs.append(package_name)

        if int(sublime.version()) >= 3000:
            package_files = os.listdir(sublime.installed_packages_path())
            found_pkgs += [file.replace('.sublime-package', '') for file in package_files]

        sublime.set_timeout(lambda: self.finish(installed_pkgs, found_pkgs), 10)

    def finish(self, installed_pkgs, found_pkgs):
        """
        A callback that can be run the main UI thread to perform saving of the
        Package Control.sublime-settings file. Also fires off the
        :class:`AutomaticUpgrader`.

        :param installed_pkgs:
            A list of the string package names of all "installed" packages,
            even ones that do not appear to be in the filesystem.

        :param found_pkgs:
            A list of the string package names of all packages that are
            currently installed on the filesystem.
        """

        self.save_packages(installed_pkgs)
        AutomaticUpgrader(found_pkgs).start()

########NEW FILE########
__FILENAME__ = package_creator
import os

import sublime

from .show_error import show_error
from .package_manager import PackageManager


class PackageCreator():
    """
    Abstract class for commands that create .sublime-package files
    """

    def show_panel(self):
        """
        Shows a list of packages that can be turned into a .sublime-package file
        """

        self.manager = PackageManager()
        self.packages = self.manager.list_packages(unpacked_only=True)
        if not self.packages:
            show_error('There are no packages available to be packaged')
            return
        self.window.show_quick_panel(self.packages, self.on_done)

    def on_done(self, picked):
        """
        Quick panel user selection handler - processes the user package
        selection and prompts the user to pick a profile, or just creates the
        package file if there are no profiles

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        self.profile = None

        if picked == -1:
            return
        self.package_name = self.packages[picked]

        rules = self.manager.settings.get('package_profiles')
        if not rules:
            self.do_create_package()
            return

        self.profiles = ['Default']
        for key in rules.keys():
            self.profiles.append(key)

        def show_panel():
            self.window.show_quick_panel(self.profiles, self.on_done_profile)
        sublime.set_timeout(show_panel, 50)

    def on_done_profile(self, picked):
        """
        Quick panel user selection handler - processes the package profile
        selection and creates the package file

        :param picked:
            An integer of the 0-based profile name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return

        # If the user picks a profile
        if picked > 0:
            self.profile = self.profiles[picked]

        self.do_create_package()

    def do_create_package(self):
        """
        Calls into the PackageManager to actually create the package file
        """

        destination = self.get_package_destination()
        if self.manager.create_package(self.package_name, destination,
                profile=self.profile):
            self.window.run_command('open_dir', {"dir":
                destination, "file": self.package_name +
                '.sublime-package'})

    def get_package_destination(self):
        """
        Retrieves the destination for .sublime-package files

        :return:
            A string - the path to the folder to save .sublime-package files in
        """

        destination = None
        if self.profile:
            profiles = self.manager.settings.get('package_profiles', {})
            if self.profile in profiles:
                profile_settings = profiles[self.profile]
                destination = profile_settings.get('package_destination')

        if not destination:
            destination = self.manager.settings.get('package_destination')

        # We check destination via an if statement instead of using
        # the dict.get() method since the key may be set, but to a blank value
        if not destination:
            destination = os.path.join(os.path.expanduser('~'), 'Desktop')

        return destination

########NEW FILE########
__FILENAME__ = package_installer
import os
import re
import threading

import sublime

from .preferences_filename import preferences_filename
from .thread_progress import ThreadProgress
from .package_manager import PackageManager
from .upgraders.git_upgrader import GitUpgrader
from .upgraders.hg_upgrader import HgUpgrader
from .versions import version_comparable
from .package_io import package_file_exists


class PackageInstaller():
    """
    Provides helper functionality related to installing packages
    """

    def __init__(self):
        self.manager = PackageManager()
        # Track what the color scheme was before upgrade so we can restore it
        self.old_color_scheme_package = None
        self.old_color_scheme = None
        # Track what the theme was before upgrade so we can restore it
        self.old_theme_package = None
        self.old_theme = None

    def make_package_list(self, ignore_actions=[], override_action=None,
            ignore_packages=[]):
        """
        Creates a list of packages and what operation would be performed for
        each. Allows filtering by the applicable action or package name.
        Returns the information in a format suitable for displaying in the
        quick panel.

        :param ignore_actions:
            A list of actions to ignore packages by. Valid actions include:
            `install`, `upgrade`, `downgrade`, `reinstall`, `overwrite`,
            `pull` and `none`. `pull` andd `none` are for Git and Hg
            repositories. `pull` is present when incoming changes are detected,
            where as `none` is selected if no commits are available. `overwrite`
            is for packages that do not include version information via the
            `package-metadata.json` file.

        :param override_action:
            A string action name to override the displayed action for all listed
            packages.

        :param ignore_packages:
            A list of packages names that should not be returned in the list

        :return:
            A list of lists, each containing three strings:
              0 - package name
              1 - package description
              2 - action; [extra info;] package url
        """

        packages = self.manager.list_available_packages()
        installed_packages = self.manager.list_packages()

        package_list = []
        for package in sorted(iter(packages.keys()), key=lambda s: s.lower()):
            if ignore_packages and package in ignore_packages:
                continue
            package_entry = [package]
            info = packages[package]
            download = info['download']

            if package in installed_packages:
                installed = True
                metadata = self.manager.get_metadata(package)
                if metadata.get('version'):
                    installed_version = metadata['version']
                else:
                    installed_version = None
            else:
                installed = False

            installed_version_name = 'v' + installed_version if \
                installed and installed_version else 'unknown version'
            new_version = 'v' + download['version']

            vcs = None
            package_dir = self.manager.get_package_dir(package)
            settings = self.manager.settings

            if override_action:
                action = override_action
                extra = ''

            else:
                if os.path.exists(os.path.join(package_dir, '.git')):
                    if settings.get('ignore_vcs_packages'):
                        continue
                    vcs = 'git'
                    incoming = GitUpgrader(settings.get('git_binary'),
                        settings.get('git_update_command'), package_dir,
                        settings.get('cache_length'), settings.get('debug')
                        ).incoming()
                elif os.path.exists(os.path.join(package_dir, '.hg')):
                    if settings.get('ignore_vcs_packages'):
                        continue
                    vcs = 'hg'
                    incoming = HgUpgrader(settings.get('hg_binary'),
                        settings.get('hg_update_command'), package_dir,
                        settings.get('cache_length'), settings.get('debug')
                        ).incoming()

                if installed:
                    if vcs:
                        if incoming:
                            action = 'pull'
                            extra = ' with ' + vcs
                        else:
                            action = 'none'
                            extra = ''
                    elif not installed_version:
                        action = 'overwrite'
                        extra = ' %s with %s' % (installed_version_name,
                            new_version)
                    else:
                        installed_version = version_comparable(installed_version)
                        download_version = version_comparable(download['version'])
                        if download_version > installed_version:
                            action = 'upgrade'
                            extra = ' to %s from %s' % (new_version,
                                installed_version_name)
                        elif download_version < installed_version:
                            action = 'downgrade'
                            extra = ' to %s from %s' % (new_version,
                                installed_version_name)
                        else:
                            action = 'reinstall'
                            extra = ' %s' % new_version
                else:
                    action = 'install'
                    extra = ' %s' % new_version
                extra += ';'

                if action in ignore_actions:
                    continue

            description = info.get('description')
            if not description:
                description = 'No description provided'
            package_entry.append(description)
            package_entry.append(action + extra + ' ' +
                re.sub('^https?://', '', info['homepage']))
            package_list.append(package_entry)
        return package_list

    def disable_packages(self, packages):
        """
        Disables one or more packages before installing or upgrading to prevent
        errors where Sublime Text tries to read files that no longer exist, or
        read a half-written file.

        :param packages: The string package name, or an array of strings
        """

        if not isinstance(packages, list):
            packages = [packages]

        # Don't disable Package Control so it does not get stuck disabled
        if 'Package Control' in packages:
            packages.remove('Package Control')

        disabled = []

        settings = sublime.load_settings(preferences_filename())
        ignored = settings.get('ignored_packages')
        if not ignored:
            ignored = []

        for package in packages:
            if not package in ignored:
                ignored.append(package)
                disabled.append(package)

            # Change the color scheme before disabling the package containing it
            if settings.get('color_scheme').find('Packages/' + package + '/') != -1:
                self.old_color_scheme_package = package
                self.old_color_scheme = settings.get('color_scheme')
                settings.set('color_scheme', 'Packages/Color Scheme - Default/Monokai.tmTheme')

            # Change the theme before disabling the package containing it
            if package_file_exists(package, settings.get('theme')):
                self.old_theme_package = package
                self.old_theme = settings.get('theme')
                settings.set('theme', 'Default.sublime-theme')

        settings.set('ignored_packages', ignored)
        sublime.save_settings(preferences_filename())
        return disabled

    def reenable_package(self, package):
        """
        Re-enables a package after it has been installed or upgraded

        :param package: The string package name
        """

        settings = sublime.load_settings(preferences_filename())
        ignored = settings.get('ignored_packages')
        if not ignored:
            return

        if package in ignored:
            settings.set('ignored_packages',
                list(set(ignored) - set([package])))

            if self.old_theme_package == package:
                settings.set('theme', self.old_theme)
                sublime.message_dialog(u"Package Control\n\n" +
                    u"Your active theme was just upgraded. You may see some " +
                    u"graphical corruption until you restart Sublime Text.")

            if self.old_color_scheme_package == package:
                settings.set('color_scheme', self.old_color_scheme)

            sublime.save_settings(preferences_filename())

    def on_done(self, picked):
        """
        Quick panel user selection handler - disables a package, installs or
        upgrades it, then re-enables the package

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return
        name = self.package_list[picked][0]

        if name in self.disable_packages(name):
            on_complete = lambda: self.reenable_package(name)
        else:
            on_complete = None

        thread = PackageInstallerThread(self.manager, name, on_complete)
        thread.start()
        ThreadProgress(thread, 'Installing package %s' % name,
            'Package %s successfully %s' % (name, self.completion_type))


class PackageInstallerThread(threading.Thread):
    """
    A thread to run package install/upgrade operations in so that the main
    Sublime Text thread does not get blocked and freeze the UI
    """

    def __init__(self, manager, package, on_complete):
        """
        :param manager:
            An instance of :class:`PackageManager`

        :param package:
            The string package name to install/upgrade

        :param on_complete:
            A callback to run after installing/upgrading the package
        """

        self.package = package
        self.manager = manager
        self.on_complete = on_complete
        threading.Thread.__init__(self)

    def run(self):
        try:
            self.result = self.manager.install_package(self.package)
        finally:
            if self.on_complete:
                sublime.set_timeout(self.on_complete, 1)

########NEW FILE########
__FILENAME__ = package_io
import os
import zipfile

import sublime

from .console_write import console_write
from .open_compat import open_compat, read_compat
from .unicode import unicode_from_os
from .file_not_found_error import FileNotFoundError


def read_package_file(package, relative_path, binary=False, debug=False):
    package_dir = _get_package_dir(package)
    file_path = os.path.join(package_dir, relative_path)

    if os.path.exists(package_dir):
        result = _read_regular_file(package, relative_path, binary, debug)
        if result != False:
            return result

    if int(sublime.version()) >= 3000:
        result = _read_zip_file(package, relative_path, binary, debug)
        if result != False:
            return result

    if debug:
        console_write(u"Unable to find file %s in the package %s" % (relative_path, package), True)
    return False


def package_file_exists(package, relative_path):
    package_dir = _get_package_dir(package)
    file_path = os.path.join(package_dir, relative_path)

    if os.path.exists(package_dir):
        result = _regular_file_exists(package, relative_path)
        if result:
            return result

    if int(sublime.version()) >= 3000:
        return _zip_file_exists(package, relative_path)

    return False


def _get_package_dir(package):
    """:return: The full filesystem path to the package directory"""

    return os.path.join(sublime.packages_path(), package)


def _read_regular_file(package, relative_path, binary=False, debug=False):
    package_dir = _get_package_dir(package)
    file_path = os.path.join(package_dir, relative_path)
    try:
        with open_compat(file_path, ('rb' if binary else 'r')) as f:
            return read_compat(f)

    except (FileNotFoundError) as e:
        if debug:
            console_write(u"Unable to find file %s in the package folder for %s" % (relative_path, package), True)
        return False


def _read_zip_file(package, relative_path, binary=False, debug=False):
    zip_path = os.path.join(sublime.installed_packages_path(),
        package + '.sublime-package')

    if not os.path.exists(zip_path):
        if debug:
            console_write(u"Unable to find a sublime-package file for %s" % package, True)
        return False

    try:
        package_zip = zipfile.ZipFile(zip_path, 'r')

    except (zipfile.BadZipfile):
        console_write(u'An error occurred while trying to unzip the sublime-package file for %s.' % package, True)
        return False

    try:
        contents = package_zip.read(relative_path)
        if not binary:
            contents = contents.decode('utf-8')
        return contents

    except (KeyError) as e:
        if debug:
            console_write(u"Unable to find file %s in the sublime-package file for %s" % (relative_path, package), True)

    except (IOError) as e:
        message = unicode_from_os(e)
        console_write(u'Unable to read file from sublime-package file for %s due to an invalid filename' % package, True)

    except (UnicodeDecodeError):
        console_write(u'Unable to read file from sublime-package file for %s due to an invalid filename or character encoding issue' % package, True)

    return False


def _regular_file_exists(package, relative_path):
    package_dir = _get_package_dir(package)
    file_path = os.path.join(package_dir, relative_path)
    return os.path.exists(file_path)


def _zip_file_exists(package, relative_path):
    zip_path = os.path.join(sublime.installed_packages_path(),
        package + '.sublime-package')

    if not os.path.exists(zip_path):
        return False

    try:
        package_zip = zipfile.ZipFile(zip_path, 'r')

    except (zipfile.BadZipfile):
        console_write(u'An error occurred while trying to unzip the sublime-package file for %s.' % package_name, True)
        return False

    try:
        package_zip.getinfo(relative_path)
        return True

    except (KeyError) as e:
        return False

########NEW FILE########
__FILENAME__ = package_manager
import sys
import os
import re
import socket
import json
import time
import zipfile
import shutil
from fnmatch import fnmatch
import datetime
import tempfile
import locale

try:
    # Python 3
    from urllib.parse import urlencode, urlparse
    import compileall
    str_cls = str
except (ImportError):
    # Python 2
    from urllib import urlencode
    from urlparse import urlparse
    str_cls = unicode

import sublime

from .show_error import show_error
from .console_write import console_write
from .open_compat import open_compat, read_compat
from .unicode import unicode_from_os
from .rmtree import rmtree
from .clear_directory import clear_directory
from .cache import (clear_cache, set_cache, get_cache, merge_cache_under_settings,
    merge_cache_over_settings, set_cache_under_settings, set_cache_over_settings)
from .versions import version_comparable, version_sort
from .downloaders.background_downloader import BackgroundDownloader
from .downloaders.downloader_exception import DownloaderException
from .providers.provider_exception import ProviderException
from .clients.client_exception import ClientException
from .download_manager import downloader
from .providers.channel_provider import ChannelProvider
from .upgraders.git_upgrader import GitUpgrader
from .upgraders.hg_upgrader import HgUpgrader
from .package_io import read_package_file
from .providers import CHANNEL_PROVIDERS, REPOSITORY_PROVIDERS
from . import __version__


class PackageManager():
    """
    Allows downloading, creating, installing, upgrading, and deleting packages

    Delegates metadata retrieval to the CHANNEL_PROVIDERS classes.
    Uses VcsUpgrader-based classes for handling git and hg repositories in the
    Packages folder. Downloader classes are utilized to fetch contents of URLs.

    Also handles displaying package messaging, and sending usage information to
    the usage server.
    """

    def __init__(self):
        # Here we manually copy the settings since sublime doesn't like
        # code accessing settings from threads
        self.settings = {}
        settings = sublime.load_settings('Package Control.sublime-settings')
        setting_names = [
            'auto_upgrade',
            'auto_upgrade_frequency',
            'auto_upgrade_ignore',
            'cache_length',
            'certs',
            'channels',
            'debug',
            'dirs_to_ignore',
            'files_to_ignore',
            'files_to_include',
            'git_binary',
            'git_update_command',
            'hg_binary',
            'hg_update_command',
            'http_cache',
            'http_cache_length',
            'http_proxy',
            'https_proxy',
            'ignore_vcs_packages',
            'install_prereleases',
            'openssl_binary',
            'package_destination',
            'package_name_map',
            'package_profiles',
            'proxy_password',
            'proxy_username',
            'renamed_packages',
            'repositories',
            'submit_url',
            'submit_usage',
            'timeout',
            'user_agent'
        ]
        for setting in setting_names:
            if settings.get(setting) == None:
                continue
            self.settings[setting] = settings.get(setting)

        # https_proxy will inherit from http_proxy unless it is set to a
        # string value or false
        no_https_proxy = self.settings.get('https_proxy') in ["", None]
        if no_https_proxy and self.settings.get('http_proxy'):
            self.settings['https_proxy'] = self.settings.get('http_proxy')
        if self.settings.get('https_proxy') == False:
            self.settings['https_proxy'] = ''

        self.settings['platform'] = sublime.platform()
        self.settings['version'] = sublime.version()

        # Use the cache to see if settings have changed since the last
        # time the package manager was created, and clearing any cached
        # values if they have.
        previous_settings = get_cache('filtered_settings', {})

        # Reduce the settings down to exclude channel info since that will
        # make the settings always different
        filtered_settings = self.settings.copy()
        for key in ['repositories', 'channels', 'package_name_map', 'cache']:
            if key in filtered_settings:
                del filtered_settings[key]

        if filtered_settings != previous_settings and previous_settings != {}:
            console_write(u'Settings change detected, clearing cache', True)
            clear_cache()
        set_cache('filtered_settings', filtered_settings)

    def get_metadata(self, package):
        """
        Returns the package metadata for an installed package

        :return:
            A dict with the keys:
                version
                url
                description
            or an empty dict on error
        """

        try:
            debug = self.settings.get('debug')
            metadata_json = read_package_file(package, 'package-metadata.json', debug=debug)
            if metadata_json:
                return json.loads(metadata_json)

        except (IOError, ValueError) as e:
            pass

        return {}

    def list_repositories(self):
        """
        Returns a master list of all repositories pulled from all sources

        These repositories come from the channels specified in the
        "channels" setting, plus any repositories listed in the
        "repositories" setting.

        :return:
            A list of all available repositories
        """

        cache_ttl = self.settings.get('cache_length')

        repositories = self.settings.get('repositories')[:]
        channels = self.settings.get('channels')
        for channel in channels:
            channel = channel.strip()

            # Caches various info from channels for performance
            cache_key = channel + '.repositories'
            channel_repositories = get_cache(cache_key)

            merge_cache_under_settings(self, 'package_name_map', channel)
            merge_cache_under_settings(self, 'renamed_packages', channel)
            merge_cache_under_settings(self, 'unavailable_packages', channel, list_=True)

            # If any of the info was not retrieved from the cache, we need to
            # grab the channel to get it
            if channel_repositories == None:

                for provider_class in CHANNEL_PROVIDERS:
                    if provider_class.match_url(channel):
                        provider = provider_class(channel, self.settings)
                        break

                try:
                    channel_repositories = provider.get_repositories()
                    set_cache(cache_key, channel_repositories, cache_ttl)

                    for repo in channel_repositories:
                        repo_packages = provider.get_packages(repo)
                        packages_cache_key = repo + '.packages'
                        set_cache(packages_cache_key, repo_packages, cache_ttl)

                    # Have the local name map override the one from the channel
                    name_map = provider.get_name_map()
                    set_cache_under_settings(self, 'package_name_map', channel, name_map, cache_ttl)

                    renamed_packages = provider.get_renamed_packages()
                    set_cache_under_settings(self, 'renamed_packages', channel, renamed_packages, cache_ttl)

                    unavailable_packages = provider.get_unavailable_packages()
                    set_cache_under_settings(self, 'unavailable_packages', channel, unavailable_packages, cache_ttl, list_=True)

                    provider_certs = provider.get_certs()
                    certs = self.settings.get('certs', {}).copy()
                    certs.update(provider_certs)
                    # Save the master list of certs, used by downloaders/cert_provider.py
                    set_cache('*.certs', certs, cache_ttl)

                except (DownloaderException, ClientException, ProviderException) as e:
                    console_write(e, True)
                    continue

            repositories.extend(channel_repositories)
        return [repo.strip() for repo in repositories]

    def list_available_packages(self):
        """
        Returns a master list of every available package from all sources

        :return:
            A dict in the format:
            {
                'Package Name': {
                    # Package details - see example-packages.json for format
                },
                ...
            }
        """

        if self.settings.get('debug'):
            console_write(u"Fetching list of available packages", True)
            console_write(u"  Platform: %s-%s" % (sublime.platform(),sublime.arch()))
            console_write(u"  Sublime Text Version: %s" % sublime.version())
            console_write(u"  Package Control Version: %s" % __version__)

        cache_ttl = self.settings.get('cache_length')
        repositories = self.list_repositories()
        packages = {}
        bg_downloaders = {}
        active = []
        repos_to_download = []
        name_map = self.settings.get('package_name_map', {})

        # Repositories are run in reverse order so that the ones first
        # on the list will overwrite those last on the list
        for repo in repositories[::-1]:
            cache_key = repo + '.packages'
            repository_packages = get_cache(cache_key)

            if repository_packages != None:
                packages.update(repository_packages)

            else:
                domain = urlparse(repo).hostname
                if domain not in bg_downloaders:
                    bg_downloaders[domain] = BackgroundDownloader(
                        self.settings, REPOSITORY_PROVIDERS)
                bg_downloaders[domain].add_url(repo)
                repos_to_download.append(repo)

        for bg_downloader in list(bg_downloaders.values()):
            bg_downloader.start()
            active.append(bg_downloader)

        # Wait for all of the downloaders to finish
        while active:
            bg_downloader = active.pop()
            bg_downloader.join()

        # Grabs the results and stuff it all in the cache
        for repo in repos_to_download:
            domain = urlparse(repo).hostname
            bg_downloader = bg_downloaders[domain]
            provider = bg_downloader.get_provider(repo)

            # Allow name mapping of packages for schema version < 2.0
            repository_packages = {}
            for name, info in provider.get_packages():
                name = name_map.get(name, name)
                info['name'] = name
                repository_packages[name] = info

            # Display errors we encountered while fetching package info
            for url, exception in provider.get_failed_sources():
                console_write(exception, True)
            for name, exception in provider.get_broken_packages():
                console_write(exception, True)

            cache_key = repo + '.packages'
            set_cache(cache_key, repository_packages, cache_ttl)
            packages.update(repository_packages)

            renamed_packages = provider.get_renamed_packages()
            set_cache_under_settings(self, 'renamed_packages', repo, renamed_packages, cache_ttl)

            unavailable_packages = provider.get_unavailable_packages()
            set_cache_under_settings(self, 'unavailable_packages', repo, unavailable_packages, cache_ttl, list_=True)

        return packages

    def list_packages(self, unpacked_only=False):
        """
        :param unpacked_only:
            Only list packages that are not inside of .sublime-package files

        :return: A list of all installed, non-default, package names
        """

        package_names = os.listdir(sublime.packages_path())
        package_names = [path for path in package_names if path[0] != '.' and
            os.path.isdir(os.path.join(sublime.packages_path(), path))]

        if int(sublime.version()) > 3000 and unpacked_only == False:
            package_files = os.listdir(sublime.installed_packages_path())
            package_names += [f.replace('.sublime-package', '') for f in package_files if re.search('\.sublime-package$', f) != None]

        # Ignore things to be deleted
        ignored = ['User']
        for package in package_names:
            cleanup_file = os.path.join(sublime.packages_path(), package,
                'package-control.cleanup')
            if os.path.exists(cleanup_file):
                ignored.append(package)

        packages = list(set(package_names) - set(ignored) -
            set(self.list_default_packages()))
        packages = sorted(packages, key=lambda s: s.lower())

        return packages

    def list_all_packages(self):
        """ :return: A list of all installed package names, including default packages"""

        packages = self.list_default_packages() + self.list_packages()
        packages = sorted(packages, key=lambda s: s.lower())
        return packages

    def list_default_packages(self):
        """ :return: A list of all default package names"""

        if int(sublime.version()) > 3000:
            bundled_packages_path = os.path.join(os.path.dirname(sublime.executable_path()),
                'Packages')
            files = os.listdir(bundled_packages_path)

        else:
            files = os.listdir(os.path.join(os.path.dirname(
                sublime.packages_path()), 'Pristine Packages'))
            files = list(set(files) - set(os.listdir(
                sublime.installed_packages_path())))
        packages = [file.replace('.sublime-package', '') for file in files]
        packages = sorted(packages, key=lambda s: s.lower())
        return packages

    def get_package_dir(self, package):
        """:return: The full filesystem path to the package directory"""

        return os.path.join(sublime.packages_path(), package)

    def get_mapped_name(self, package):
        """:return: The name of the package after passing through mapping rules"""

        return self.settings.get('package_name_map', {}).get(package, package)

    def create_package(self, package_name, package_destination, profile=None):
        """
        Creates a .sublime-package file from the running Packages directory

        :param package_name:
            The package to create a .sublime-package file for

        :param package_destination:
            The full filesystem path of the directory to save the new
            .sublime-package file in.

        :param profile:
            If None, the "dirs_to_ignore", "files_to_ignore", "files_to_include"
            and "package_destination" settings will be used when creating the
            package. If a string, will look in the "package_profiles" setting
            and use the profile name to select a sub-dictionary which may
            contain all of the ignore/include settings.

        :return: bool if the package file was successfully created
        """

        package_dir = self.get_package_dir(package_name)

        if not os.path.exists(package_dir):
            show_error(u'The folder for the package name specified, %s, does not exist in %s' % (
                package_name, sublime.packages_path()))
            return False

        package_filename = package_name + '.sublime-package'
        package_path = os.path.join(package_destination,
            package_filename)

        if not os.path.exists(sublime.installed_packages_path()):
            os.mkdir(sublime.installed_packages_path())

        if os.path.exists(package_path):
            os.remove(package_path)

        try:
            package_file = zipfile.ZipFile(package_path, "w",
                compression=zipfile.ZIP_DEFLATED)
        except (OSError, IOError) as e:
            show_error(u'An error occurred creating the package file %s in %s.\n\n%s' % (
                package_filename, package_destination, unicode_from_os(e)))
            return False

        if int(sublime.version()) >= 3000:
            compileall.compile_dir(package_dir, quiet=True, legacy=True, optimize=2)

        if profile:
            profile_settings = self.settings.get('package_profiles').get(profile)
        def get_profile_setting(setting, default):
            if profile:
                profile_value = profile_settings.get(setting)
                if profile_value is not None:
                    return profile_value
            return self.settings.get(setting, default)

        dirs_to_ignore = get_profile_setting('dirs_to_ignore', [])
        files_to_ignore = get_profile_setting('files_to_ignore', [])
        files_to_include = get_profile_setting('files_to_include', [])

        slash = '\\' if os.name == 'nt' else '/'
        trailing_package_dir = package_dir + slash if package_dir[-1] != slash else package_dir
        package_dir_regex = re.compile('^' + re.escape(trailing_package_dir))
        for root, dirs, files in os.walk(package_dir):
            [dirs.remove(dir_) for dir_ in dirs if dir_ in dirs_to_ignore]
            paths = dirs
            paths.extend(files)
            for path in paths:
                full_path = os.path.join(root, path)
                relative_path = re.sub(package_dir_regex, '', full_path)

                ignore_matches = [fnmatch(relative_path, p) for p in files_to_ignore]
                include_matches = [fnmatch(relative_path, p) for p in files_to_include]
                if any(ignore_matches) and not any(include_matches):
                    continue

                if os.path.isdir(full_path):
                    continue
                package_file.write(full_path, relative_path)

        package_file.close()

        return True

    def install_package(self, package_name):
        """
        Downloads and installs (or upgrades) a package

        Uses the self.list_available_packages() method to determine where to
        retrieve the package file from.

        The install process consists of:

        1. Finding the package
        2. Downloading the .sublime-package/.zip file
        3. Extracting the package file
        4. Showing install/upgrade messaging
        5. Submitting usage info
        6. Recording that the package is installed

        :param package_name:
            The package to download and install

        :return: bool if the package was successfully installed
        """

        packages = self.list_available_packages()

        is_available = package_name in list(packages.keys())
        is_unavailable = package_name in self.settings.get('unavailable_packages', [])

        if is_unavailable and not is_available:
            console_write(u'The package "%s" is not available on this platform.' % package_name, True)
            return False

        if not is_available:
            show_error(u'The package specified, %s, is not available' % package_name)
            return False

        url = packages[package_name]['download']['url']
        package_filename = package_name + '.sublime-package'

        tmp_dir = tempfile.mkdtemp(u'')

        try:
            # This is refers to the zipfile later on, so we define it here so we can
            # close the zip file if set during the finally clause
            package_zip = None

            tmp_package_path = os.path.join(tmp_dir, package_filename)

            unpacked_package_dir = self.get_package_dir(package_name)
            package_path = os.path.join(sublime.installed_packages_path(),
                package_filename)
            pristine_package_path = os.path.join(os.path.dirname(
                sublime.packages_path()), 'Pristine Packages', package_filename)

            if os.path.exists(os.path.join(unpacked_package_dir, '.git')):
                if self.settings.get('ignore_vcs_packages'):
                    show_error(u'Skipping git package %s since the setting ignore_vcs_packages is set to true' % package_name)
                    return False
                return GitUpgrader(self.settings['git_binary'],
                    self.settings['git_update_command'], unpacked_package_dir,
                    self.settings['cache_length'], self.settings['debug']).run()
            elif os.path.exists(os.path.join(unpacked_package_dir, '.hg')):
                if self.settings.get('ignore_vcs_packages'):
                    show_error(u'Skipping hg package %s since the setting ignore_vcs_packages is set to true' % package_name)
                    return False
                return HgUpgrader(self.settings['hg_binary'],
                    self.settings['hg_update_command'], unpacked_package_dir,
                    self.settings['cache_length'], self.settings['debug']).run()

            old_version = self.get_metadata(package_name).get('version')
            is_upgrade = old_version != None

            # Download the sublime-package or zip file
            try:
                with downloader(url, self.settings) as manager:
                    package_bytes = manager.fetch(url, 'Error downloading package.')
            except (DownloaderException) as e:
                console_write(e, True)
                show_error(u'Unable to download %s. Please view the console for more details.' % package_name)
                return False

            with open_compat(tmp_package_path, "wb") as package_file:
                package_file.write(package_bytes)

            # Try to open it as a zip file
            try:
                package_zip = zipfile.ZipFile(tmp_package_path, 'r')
            except (zipfile.BadZipfile):
                show_error(u'An error occurred while trying to unzip the package file for %s. Please try installing the package again.' % package_name)
                return False

            # Scan through the root level of the zip file to gather some info
            root_level_paths = []
            last_path = None
            for path in package_zip.namelist():
                try:
                    if not isinstance(path, str_cls):
                        path = path.decode('utf-8', 'strict')
                except (UnicodeDecodeError):
                    console_write(u'One or more of the zip file entries in %s is not encoded using UTF-8, aborting' % package_name, True)
                    return False

                last_path = path

                if path.find('/') in [len(path) - 1, -1]:
                    root_level_paths.append(path)
                # Make sure there are no paths that look like security vulnerabilities
                if path[0] == '/' or path.find('../') != -1 or path.find('..\\') != -1:
                    show_error(u'The package specified, %s, contains files outside of the package dir and cannot be safely installed.' % package_name)
                    return False

            if last_path and len(root_level_paths) == 0:
                root_level_paths.append(last_path[0:last_path.find('/') + 1])

            # If there is only a single directory at the top leve, the file
            # is most likely a zip from BitBucket or GitHub and we need
            # to skip the top-level dir when extracting
            skip_root_dir = len(root_level_paths) == 1 and \
                root_level_paths[0].endswith('/')

            no_package_file_zip_path = '.no-sublime-package'
            if skip_root_dir:
                no_package_file_zip_path = root_level_paths[0] + no_package_file_zip_path

            # If we should extract unpacked or as a .sublime-package file
            unpack = True

            # By default, ST3 prefers .sublime-package files since this allows
            # overriding files in the Packages/{package_name}/ folder
            if int(sublime.version()) >= 3000:
                unpack = False

            # If the package maintainer doesn't want a .sublime-package
            try:
                package_zip.getinfo(no_package_file_zip_path)
                unpack = True
            except (KeyError):
                pass

            # If we already have a package-metadata.json file in
            # Packages/{package_name}/, the only way to successfully upgrade
            # will be to unpack
            unpacked_metadata_file = os.path.join(unpacked_package_dir,
                'package-metadata.json')
            if os.path.exists(unpacked_metadata_file):
                unpack = True

            # If we determined it should be unpacked, we extract directly
            # into the Packages/{package_name}/ folder
            if unpack:
                self.backup_package_dir(package_name)
                package_dir = unpacked_package_dir

            # Otherwise we go into a temp dir since we will be creating a
            # new .sublime-package file later
            else:
                tmp_working_dir = os.path.join(tmp_dir, 'working')
                os.mkdir(tmp_working_dir)
                package_dir = tmp_working_dir

            package_metadata_file = os.path.join(package_dir,
                'package-metadata.json')

            if not os.path.exists(package_dir):
                os.mkdir(package_dir)

            os.chdir(package_dir)

            # Here we don't use .extractall() since it was having issues on OS X
            overwrite_failed = False
            extracted_paths = []
            for path in package_zip.namelist():
                dest = path

                try:
                    if not isinstance(dest, str_cls):
                        dest = dest.decode('utf-8', 'strict')
                except (UnicodeDecodeError):
                    console_write(u'One or more of the zip file entries in %s is not encoded using UTF-8, aborting' % package_name, True)
                    return False

                if os.name == 'nt':
                    regex = ':|\*|\?|"|<|>|\|'
                    if re.search(regex, dest) != None:
                        console_write(u'Skipping file from package named %s due to an invalid filename' % package_name, True)
                        continue

                # If there was only a single directory in the package, we remove
                # that folder name from the paths as we extract entries
                if skip_root_dir:
                    dest = dest[len(root_level_paths[0]):]

                if os.name == 'nt':
                    dest = dest.replace('/', '\\')
                else:
                    dest = dest.replace('\\', '/')

                dest = os.path.join(package_dir, dest)

                def add_extracted_dirs(dir_):
                    while dir_ not in extracted_paths:
                        extracted_paths.append(dir_)
                        dir_ = os.path.dirname(dir_)
                        if dir_ == package_dir:
                            break

                if path.endswith('/'):
                    if not os.path.exists(dest):
                        os.makedirs(dest)
                    add_extracted_dirs(dest)
                else:
                    dest_dir = os.path.dirname(dest)
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)
                    add_extracted_dirs(dest_dir)
                    extracted_paths.append(dest)
                    try:
                        open_compat(dest, 'wb').write(package_zip.read(path))
                    except (IOError) as e:
                        message = unicode_from_os(e)
                        if re.search('[Ee]rrno 13', message):
                            overwrite_failed = True
                            break
                        console_write(u'Skipping file from package named %s due to an invalid filename' % package_name, True)

                    except (UnicodeDecodeError):
                        console_write(u'Skipping file from package named %s due to an invalid filename' % package_name, True)

            package_zip.close()
            package_zip = None

            # If upgrading failed, queue the package to upgrade upon next start
            if overwrite_failed:
                reinstall_file = os.path.join(package_dir, 'package-control.reinstall')
                open_compat(reinstall_file, 'w').close()

                # Don't delete the metadata file, that way we have it
                # when the reinstall happens, and the appropriate
                # usage info can be sent back to the server
                clear_directory(package_dir, [reinstall_file, package_metadata_file])

                show_error(u'An error occurred while trying to upgrade %s. Please restart Sublime Text to finish the upgrade.' % package_name)
                return False

            # Here we clean out any files that were not just overwritten. It is ok
            # if there is an error removing a file. The next time there is an
            # upgrade, it should be cleaned out successfully then.
            clear_directory(package_dir, extracted_paths)

            self.print_messages(package_name, package_dir, is_upgrade, old_version)

            with open_compat(package_metadata_file, 'w') as f:
                metadata = {
                    "version": packages[package_name]['download']['version'],
                    "url": packages[package_name]['homepage'],
                    "description": packages[package_name]['description']
                }
                json.dump(metadata, f)

            # Submit install and upgrade info
            if is_upgrade:
                params = {
                    'package': package_name,
                    'operation': 'upgrade',
                    'version': packages[package_name]['download']['version'],
                    'old_version': old_version
                }
            else:
                params = {
                    'package': package_name,
                    'operation': 'install',
                    'version': packages[package_name]['download']['version']
                }
            self.record_usage(params)

            # Record the install in the settings file so that you can move
            # settings across computers and have the same packages installed
            def save_package():
                settings = sublime.load_settings('Package Control.sublime-settings')
                installed_packages = settings.get('installed_packages', [])
                if not installed_packages:
                    installed_packages = []
                installed_packages.append(package_name)
                installed_packages = list(set(installed_packages))
                installed_packages = sorted(installed_packages,
                    key=lambda s: s.lower())
                settings.set('installed_packages', installed_packages)
                sublime.save_settings('Package Control.sublime-settings')
            sublime.set_timeout(save_package, 1)

            # If we didn't extract directly into the Packages/{package_name}/
            # folder, we need to create a .sublime-package file and install it
            if not unpack:
                try:
                    # Remove the downloaded file since we are going to overwrite it
                    os.remove(tmp_package_path)
                    package_zip = zipfile.ZipFile(tmp_package_path, "w",
                        compression=zipfile.ZIP_DEFLATED)
                except (OSError, IOError) as e:
                    show_error(u'An error occurred creating the package file %s in %s.\n\n%s' % (
                        package_filename, tmp_dir, unicode_from_os(e)))
                    return False

                package_dir_regex = re.compile('^' + re.escape(package_dir))
                for root, dirs, files in os.walk(package_dir):
                    paths = dirs
                    paths.extend(files)
                    for path in paths:
                        full_path = os.path.join(root, path)
                        relative_path = re.sub(package_dir_regex, '', full_path)
                        if os.path.isdir(full_path):
                            continue
                        package_zip.write(full_path, relative_path)

                package_zip.close()
                package_zip = None

                if os.path.exists(package_path):
                    os.remove(package_path)
                shutil.move(tmp_package_path, package_path)

            # We have to remove the pristine package too or else Sublime Text 2
            # will silently delete the package
            if os.path.exists(pristine_package_path):
                os.remove(pristine_package_path)

            os.chdir(sublime.packages_path())
            return True

        finally:
            # We need to make sure the zipfile is closed to
            # help prevent permissions errors on Windows
            if package_zip:
                package_zip.close()

            # Try to remove the tmp dir after a second to make sure
            # a virus scanner is holding a reference to the zipfile
            # after we close it.
            def remove_tmp_dir():
                try:
                    rmtree(tmp_dir)
                except (PermissionError):
                    # If we can't remove the tmp dir, don't let an uncaught exception
                    # fall through and break the install process
                    pass
            sublime.set_timeout(remove_tmp_dir, 1000)

    def backup_package_dir(self, package_name):
        """
        Does a full backup of the Packages/{package}/ dir to Backup/

        :param package_name:
            The name of the package to back up

        :return:
            If the backup succeeded
        """

        package_dir = os.path.join(sublime.packages_path(), package_name)
        if not os.path.exists(package_dir):
            return True

        try:
            backup_dir = os.path.join(os.path.dirname(
                sublime.packages_path()), 'Backup',
                datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            package_backup_dir = os.path.join(backup_dir, package_name)
            if os.path.exists(package_backup_dir):
                console_write(u"FOLDER %s ALREADY EXISTS!" % package_backup_dir)
            shutil.copytree(package_dir, package_backup_dir)
            return True

        except (OSError, IOError) as e:
            show_error(u'An error occurred while trying to backup the package directory for %s.\n\n%s' % (
                package_name, unicode_from_os(e)))
            if os.path.exists(package_backup_dir):
                rmtree(package_backup_dir)
            return False

    def print_messages(self, package, package_dir, is_upgrade, old_version):
        """
        Prints out package install and upgrade messages

        The functionality provided by this allows package maintainers to
        show messages to the user when a package is installed, or when
        certain version upgrade occur.

        :param package:
            The name of the package the message is for

        :param package_dir:
            The full filesystem path to the package directory

        :param is_upgrade:
            If the install was actually an upgrade

        :param old_version:
            The string version of the package before the upgrade occurred
        """

        messages_file = os.path.join(package_dir, 'messages.json')
        if not os.path.exists(messages_file):
            return

        messages_fp = open_compat(messages_file, 'r')
        try:
            message_info = json.loads(read_compat(messages_fp))
        except (ValueError):
            console_write(u'Error parsing messages.json for %s' % package, True)
            return
        messages_fp.close()

        output = ''
        if not is_upgrade and message_info.get('install'):
            install_messages = os.path.join(package_dir,
                message_info.get('install'))
            message = '\n\n%s:\n%s\n\n  ' % (package,
                        ('-' * len(package)))
            with open_compat(install_messages, 'r') as f:
                message += read_compat(f).replace('\n', '\n  ')
            output += message + '\n'

        elif is_upgrade and old_version:
            upgrade_messages = list(set(message_info.keys()) -
                set(['install']))
            upgrade_messages = version_sort(upgrade_messages, reverse=True)
            old_version_cmp = version_comparable(old_version)

            for version in upgrade_messages:
                if version_comparable(version) <= old_version_cmp:
                    break
                if not output:
                    message = '\n\n%s:\n%s\n' % (package,
                        ('-' * len(package)))
                    output += message
                upgrade_message_path = os.path.join(package_dir,
                    message_info.get(version))
                message = '\n  '
                with open_compat(upgrade_message_path, 'r') as f:
                    message += read_compat(f).replace('\n', '\n  ')
                output += message + '\n'

        if not output:
            return

        def print_to_panel():
            window = sublime.active_window()

            views = window.views()
            view = None
            for _view in views:
                if _view.name() == 'Package Control Messages':
                    view = _view
                    break

            if not view:
                view = window.new_file()
                view.set_name('Package Control Messages')
                view.set_scratch(True)

            def write(string):
                view.run_command('package_message', {'string': string})

            if not view.size():
                view.settings().set("word_wrap", True)
                write('Package Control Messages\n' +
                    '========================')

            write(output)
        sublime.set_timeout(print_to_panel, 1)

    def remove_package(self, package_name):
        """
        Deletes a package

        The deletion process consists of:

        1. Deleting the directory (or marking it for deletion if deletion fails)
        2. Submitting usage info
        3. Removing the package from the list of installed packages

        :param package_name:
            The package to delete

        :return: bool if the package was successfully deleted
        """

        installed_packages = self.list_packages()

        if package_name not in installed_packages:
            show_error(u'The package specified, %s, is not installed' % package_name)
            return False

        os.chdir(sublime.packages_path())

        # Give Sublime Text some time to ignore the package
        time.sleep(1)

        package_filename = package_name + '.sublime-package'
        installed_package_path = os.path.join(sublime.installed_packages_path(),
            package_filename)
        pristine_package_path = os.path.join(os.path.dirname(
            sublime.packages_path()), 'Pristine Packages', package_filename)
        package_dir = self.get_package_dir(package_name)

        version = self.get_metadata(package_name).get('version')

        try:
            if os.path.exists(installed_package_path):
                os.remove(installed_package_path)
        except (OSError, IOError) as e:
            show_error(u'An error occurred while trying to remove the installed package file for %s.\n\n%s' % (
                package_name, unicode_from_os(e)))
            return False

        try:
            if os.path.exists(pristine_package_path):
                os.remove(pristine_package_path)
        except (OSError, IOError) as e:
            show_error(u'An error occurred while trying to remove the pristine package file for %s.\n\n%s' % (
                package_name, unicode_from_os(e)))
            return False

        # We don't delete the actual package dir immediately due to a bug
        # in sublime_plugin.py
        can_delete_dir = True
        if not clear_directory(package_dir):
            # If there is an error deleting now, we will mark it for
            # cleanup the next time Sublime Text starts
            open_compat(os.path.join(package_dir, 'package-control.cleanup'),
                'w').close()
            can_delete_dir = False

        params = {
            'package': package_name,
            'operation': 'remove',
            'version': version
        }
        self.record_usage(params)

        # Remove the package from the installed packages list
        def clear_package():
            settings = sublime.load_settings('Package Control.sublime-settings')
            installed_packages = settings.get('installed_packages', [])
            if not installed_packages:
                installed_packages = []
            installed_packages.remove(package_name)
            settings.set('installed_packages', installed_packages)
            sublime.save_settings('Package Control.sublime-settings')
        sublime.set_timeout(clear_package, 1)

        if can_delete_dir and os.path.exists(package_dir):
            os.rmdir(package_dir)

        return True

    def record_usage(self, params):
        """
        Submits install, upgrade and delete actions to a usage server

        The usage information is currently displayed on the Package Control
        community package list at http://wbond.net/sublime_packages/community

        :param params:
            A dict of the information to submit
        """

        if not self.settings.get('submit_usage'):
            return
        params['package_control_version'] = \
            self.get_metadata('Package Control').get('version')
        params['sublime_platform'] = self.settings.get('platform')
        params['sublime_version'] = self.settings.get('version')

        # For Python 2, we need to explicitly encoding the params
        for param in params:
            if isinstance(params[param], str_cls):
                params[param] = params[param].encode('utf-8')

        url = self.settings.get('submit_url') + '?' + urlencode(params)

        try:
            with downloader(url, self.settings) as manager:
                result = manager.fetch(url, 'Error submitting usage information.')
        except (DownloaderException) as e:
            console_write(e, True)
            return

        try:
            result = json.loads(result.decode('utf-8'))
            if result['result'] != 'success':
                raise ValueError()
        except (ValueError):
            console_write(u'Error submitting usage information for %s' % params['package'], True)

########NEW FILE########
__FILENAME__ = package_renamer
import os

import sublime

from .console_write import console_write


class PackageRenamer():
    """
    Class to handle renaming packages via the renamed_packages setting
    gathered from channels and repositories.
    """

    def load_settings(self):
        """
        Loads the list of installed packages from the
        Package Control.sublime-settings file.
        """

        self.settings_file = 'Package Control.sublime-settings'
        self.settings = sublime.load_settings(self.settings_file)
        self.installed_packages = self.settings.get('installed_packages', [])
        if not isinstance(self.installed_packages, list):
            self.installed_packages = []

    def rename_packages(self, installer):
        """
        Renames any installed packages that the user has installed.

        :param installer:
            An instance of :class:`PackageInstaller`
        """

        # Fetch the packages since that will pull in the renamed packages list
        installer.manager.list_available_packages()
        renamed_packages = installer.manager.settings.get('renamed_packages', {})

        if not renamed_packages:
            renamed_packages = {}

        # These are packages that have been tracked as installed
        installed_pkgs = self.installed_packages
        # There are the packages actually present on the filesystem
        present_packages = installer.manager.list_packages()

        case_insensitive_fs = sublime.platform() in ['windows', 'osx']

        # Rename directories for packages that have changed names
        for package_name in renamed_packages:
            new_package_name = renamed_packages[package_name]
            changing_case = package_name.lower() == new_package_name.lower()

            # Since Windows and OSX use case-insensitive filesystems, we have to
            # scan through the list of installed packages if the rename of the
            # package is just changing the case of it. If we don't find the old
            # name for it, we continue the loop since os.path.exists() will return
            # true due to the case-insensitive nature of the filesystems.
            has_old = False
            if case_insensitive_fs and changing_case:
                for present_package_name in present_packages:
                    if present_package_name == package_name:
                        has_old = True
                        break
                if not has_old:
                    continue

            # For handling .sublime-package files
            package_file = os.path.join(sublime.installed_packages_path(),
                package_name + '.sublime-package')
            # For handling unpacked packages
            package_dir = os.path.join(sublime.packages_path(), package_name)

            if os.path.exists(package_file):
                new_package_path = os.path.join(sublime.installed_packages_path(),
                    new_package_name + '.sublime-package')
                package_path = package_file
            elif os.path.exists(os.path.join(package_dir, 'package-metadata.json')):
                new_package_path = os.path.join(sublime.packages_path(),
                    new_package_name)
                package_path = package_dir
            else:
                continue

            if not os.path.exists(new_package_path) or (case_insensitive_fs and changing_case):
                # Windows will not allow you to rename to the same name with
                # a different case, so we work around that with a temporary name
                if os.name == 'nt' and changing_case:
                    temp_package_name = '__' + new_package_name
                    temp_package_path = os.path.join(sublime.packages_path(),
                        temp_package_name)
                    os.rename(package_path, temp_package_path)
                    package_path = temp_package_path

                os.rename(package_path, new_package_path)
                installed_pkgs.append(new_package_name)

                console_write(u'Renamed %s to %s' % (package_name, new_package_name), True)
            else:
                installer.manager.remove_package(package_name)
                message_string = u'Removed %s since package with new name (%s) already exists' % (
                    package_name, new_package_name)
                console_write(message_string, True)

            try:
                installed_pkgs.remove(package_name)
            except (ValueError):
                pass

        sublime.set_timeout(lambda: self.save_packages(installed_pkgs), 10)

    def save_packages(self, installed_packages):
        """
        Saves the list of installed packages (after having been appropriately
        renamed)

        :param installed_packages:
            The new list of installed packages
        """

        installed_packages = list(set(installed_packages))
        installed_packages = sorted(installed_packages,
            key=lambda s: s.lower())

        if installed_packages != self.installed_packages:
            self.settings.set('installed_packages', installed_packages)
            sublime.save_settings(self.settings_file)

########NEW FILE########
__FILENAME__ = preferences_filename
import sublime


def preferences_filename():
    """
    :return: The appropriate settings filename based on the version of Sublime Text
    """

    if int(sublime.version()) >= 2174:
        return 'Preferences.sublime-settings'
    return 'Global.sublime-settings'

########NEW FILE########
__FILENAME__ = bitbucket_repository_provider
import re

from ..clients.bitbucket_client import BitBucketClient
from ..downloaders.downloader_exception import DownloaderException
from ..clients.client_exception import ClientException
from .provider_exception import ProviderException


class BitBucketRepositoryProvider():
    """
    Allows using a public BitBucket repository as the source for a single package.
    For legacy purposes, this can also be treated as the source for a Package
    Control "repository".

    :param repo:
        The public web URL to the BitBucket repository. Should be in the format
        `https://bitbucket.org/user/package`.

    :param settings:
        A dict containing at least the following fields:
          `cache_length`,
          `debug`,
          `timeout`,
          `user_agent`
        Optional fields:
          `http_proxy`,
          `https_proxy`,
          `proxy_username`,
          `proxy_password`,
          `query_string_params`
          `install_prereleases`
    """

    def __init__(self, repo, settings):
        self.cache = {}
        self.repo = repo
        self.settings = settings
        self.failed_sources = {}

    @classmethod
    def match_url(cls, repo):
        """Indicates if this provider can handle the provided repo"""

        return re.search('^https?://bitbucket.org/([^/]+/[^/]+)/?$', repo) != None

    def prefetch(self):
        """
        Go out and perform HTTP operations, caching the result

        :raises:
            DownloaderException: when there is an issue download package info
            ClientException: when there is an issue parsing package info
        """

        [name for name, info in self.get_packages()]

    def get_failed_sources(self):
        """
        List of any URLs that could not be accessed while accessing this repository

        :return:
            A generator of ("https://bitbucket.org/user/repo", Exception()) tuples
        """

        return self.failed_sources.items()

    def get_broken_packages(self):
        """
        For API-compatibility with RepositoryProvider
        """

        return {}.items()

    def get_packages(self, invalid_sources=None):
        """
        Uses the BitBucket API to construct necessary info for a package

        :param invalid_sources:
            A list of URLs that should be ignored

        :raises:
            DownloaderException: when there is an issue download package info
            ClientException: when there is an issue parsing package info

        :return:
            A generator of
            (
                'Package Name',
                {
                    'name': name,
                    'description': description,
                    'author': author,
                    'homepage': homepage,
                    'last_modified': last modified date,
                    'download': {
                        'url': url,
                        'date': date,
                        'version': version
                    },
                    'previous_names': [],
                    'labels': [],
                    'sources': [the repo URL],
                    'readme': url,
                    'issues': url,
                    'donate': url,
                    'buy': None
                }
            )
            tuples
        """

        if 'get_packages' in self.cache:
            for key, value in self.cache['get_packages'].items():
                yield (key, value)
            return

        client = BitBucketClient(self.settings)

        if invalid_sources != None and self.repo in invalid_sources:
            raise StopIteration()

        try:
            repo_info = client.repo_info(self.repo)
            download = client.download_info(self.repo)

            name = repo_info['name']
            details = {
                'name': name,
                'description': repo_info['description'],
                'homepage': repo_info['homepage'],
                'author': repo_info['author'],
                'last_modified': download.get('date'),
                'download': download,
                'previous_names': [],
                'labels': [],
                'sources': [self.repo],
                'readme': repo_info['readme'],
                'issues': repo_info['issues'],
                'donate': repo_info['donate'],
                'buy': None
            }
            self.cache['get_packages'] = {name: details}
            yield (name, details)

        except (DownloaderException, ClientException, ProviderException) as e:
            self.failed_sources[self.repo] = e
            self.cache['get_packages'] = {}
            raise StopIteration()

    def get_renamed_packages(self):
        """For API-compatibility with RepositoryProvider"""

        return {}

    def get_unavailable_packages(self):
        """
        Method for compatibility with RepositoryProvider class. These providers
        are based on API calls, and thus do not support different platform
        downloads, making it impossible for there to be unavailable packages.

        :return: An empty list
        """
        return []

########NEW FILE########
__FILENAME__ = channel_provider
import json
import os
import re

try:
    # Python 3
    from urllib.parse import urljoin
except (ImportError):
    # Python 2
    from urlparse import urljoin

from ..console_write import console_write
from .release_selector import ReleaseSelector
from .provider_exception import ProviderException
from ..downloaders.downloader_exception import DownloaderException
from ..clients.client_exception import ClientException
from ..download_manager import downloader


class ChannelProvider(ReleaseSelector):
    """
    Retrieves a channel and provides an API into the information

    The current channel/repository infrastructure caches repository info into
    the channel to improve the Package Control client performance. This also
    has the side effect of lessening the load on the GitHub and BitBucket APIs
    and getting around not-infrequent HTTP 503 errors from those APIs.

    :param channel:
        The URL of the channel

    :param settings:
        A dict containing at least the following fields:
          `cache_length`,
          `debug`,
          `timeout`,
          `user_agent`
        Optional fields:
          `http_proxy`,
          `https_proxy`,
          `proxy_username`,
          `proxy_password`,
          `query_string_params`
          `install_prereleases`
    """

    def __init__(self, channel, settings):
        self.channel_info = None
        self.schema_version = 0.0
        self.channel = channel
        self.settings = settings
        self.unavailable_packages = []

    @classmethod
    def match_url(cls, channel):
        """Indicates if this provider can handle the provided channel"""

        return True

    def prefetch(self):
        """
        Go out and perform HTTP operations, caching the result

        :raises:
            ProviderException: when an error occurs trying to open a file
            DownloaderException: when an error occurs trying to open a URL
        """

        self.fetch()

    def fetch(self):
        """
        Retrieves and loads the JSON for other methods to use

        :raises:
            ProviderException: when an error occurs with the channel contents
            DownloaderException: when an error occurs trying to open a URL
        """

        if self.channel_info != None:
            return

        if re.match('https?://', self.channel, re.I):
            with downloader(self.channel, self.settings) as manager:
                channel_json = manager.fetch(self.channel,
                    'Error downloading channel.')

        # All other channels are expected to be filesystem paths
        else:
            if not os.path.exists(self.channel):
                raise ProviderException(u'Error, file %s does not exist' % self.channel)

            if self.settings.get('debug'):
                console_write(u'Loading %s as a channel' % self.channel, True)

            # We open as binary so we get bytes like the DownloadManager
            with open(self.channel, 'rb') as f:
                channel_json = f.read()

        try:
            channel_info = json.loads(channel_json.decode('utf-8'))
        except (ValueError):
            raise ProviderException(u'Error parsing JSON from channel %s.' % self.channel)

        schema_error = u'Channel %s does not appear to be a valid channel file because ' % self.channel

        if 'schema_version' not in channel_info:
            raise ProviderException(u'%s the "schema_version" JSON key is missing.' % schema_error)

        try:
            self.schema_version = float(channel_info.get('schema_version'))
        except (ValueError):
            raise ProviderException(u'%s the "schema_version" is not a valid number.' % schema_error)

        if self.schema_version not in [1.0, 1.1, 1.2, 2.0]:
            raise ProviderException(u'%s the "schema_version" is not recognized. Must be one of: 1.0, 1.1, 1.2 or 2.0.' % schema_error)

        self.channel_info = channel_info

    def get_name_map(self):
        """
        :raises:
            ProviderException: when an error occurs with the channel contents
            DownloaderException: when an error occurs trying to open a URL

        :return:
            A dict of the mapping for URL slug -> package name
        """

        self.fetch()

        if self.schema_version >= 2.0:
            return {}

        return self.channel_info.get('package_name_map', {})

    def get_renamed_packages(self):
        """
        :raises:
            ProviderException: when an error occurs with the channel contents
            DownloaderException: when an error occurs trying to open a URL

        :return:
            A dict of the packages that have been renamed
        """

        self.fetch()

        if self.schema_version >= 2.0:
            output = {}
            for repo in self.channel_info['packages_cache']:
                for package in self.channel_info['packages_cache'][repo]:
                    previous_names = package.get('previous_names', [])
                    if not isinstance(previous_names, list):
                        previous_names = [previous_names]
                    for previous_name in previous_names:
                        output[previous_name] = package['name']
            return output

        return self.channel_info.get('renamed_packages', {})

    def get_repositories(self):
        """
        :raises:
            ProviderException: when an error occurs with the channel contents
            DownloaderException: when an error occurs trying to open a URL

        :return:
            A list of the repository URLs
        """

        self.fetch()

        if 'repositories' not in self.channel_info:
            raise ProviderException(u'Channel %s does not appear to be a valid channel file because the "repositories" JSON key is missing.' % self.channel)

        # Determine a relative root so repositories can be defined
        # relative to the location of the channel file.
        if re.match('https?://', self.channel, re.I) is None:
            relative_base = os.path.dirname(self.channel)
            is_http = False
        else:
            is_http = True

        output = []
        repositories = self.channel_info.get('repositories', [])
        for repository in repositories:
            if re.match('^\./|\.\./', repository):
                if is_http:
                    repository = urljoin(self.channel, repository)
                else:
                    repository = os.path.join(relative_base, repository)
                    repository = os.path.normpath(repository)
            output.append(repository)

        return output

    def get_certs(self):
        """
        Provides a secure way for distribution of SSL CA certificates

        Unfortunately Python does not include a bundle of CA certs with urllib
        to perform SSL certificate validation. To circumvent this issue,
        Package Control acts as a distributor of the CA certs for all HTTPS
        URLs of package downloads.

        The default channel scrapes and caches info about all packages
        periodically, and in the process it checks the CA certs for all of
        the HTTPS URLs listed in the repositories. The contents of the CA cert
        files are then hashed, and the CA cert is stored in a filename with
        that hash. This is a fingerprint to ensure that Package Control has
        the appropriate CA cert for a domain name.

        Next, the default channel file serves up a JSON object of the domain
        names and the hashes of their current CA cert files. If Package Control
        does not have the appropriate hash for a domain, it may retrieve it
        from the channel server. To ensure that Package Control is talking to
        a trusted authority to get the CA certs from, the CA cert for
        sublime.wbond.net is bundled with Package Control. Then when downloading
        the channel file, Package Control can ensure that the channel file's
        SSL certificate is valid, thus ensuring the resulting CA certs are
        legitimate.

        As a matter of optimization, the distribution of Package Control also
        includes the current CA certs for all known HTTPS domains that are
        included in the channel, as of the time when Package Control was
        last released.

        :raises:
            ProviderException: when an error occurs with the channel contents
            DownloaderException: when an error occurs trying to open a URL

        :return:
            A dict of {'Domain Name': ['cert_file_hash', 'cert_file_download_url']}
        """

        self.fetch()

        return self.channel_info.get('certs', {})

    def get_packages(self, repo):
        """
        Provides access to the repository info that is cached in a channel

        :param repo:
            The URL of the repository to get the cached info of

        :raises:
            ProviderException: when an error occurs with the channel contents
            DownloaderException: when an error occurs trying to open a URL

        :return:
            A dict in the format:
            {
                'Package Name': {
                    'name': name,
                    'description': description,
                    'author': author,
                    'homepage': homepage,
                    'last_modified': last modified date,
                    'download': {
                        'url': url,
                        'date': date,
                        'version': version
                    },
                    'previous_names': [old_name, ...],
                    'labels': [label, ...],
                    'readme': url,
                    'issues': url,
                    'donate': url,
                    'buy': url
                },
                ...
            }
        """

        self.fetch()

        # The 2.0 channel schema renamed the key cached package info was
        # stored under in order to be more clear to new users.
        packages_key = 'packages_cache' if self.schema_version >= 2.0 else 'packages'

        if self.channel_info.get(packages_key, False) == False:
            return {}

        if self.channel_info[packages_key].get(repo, False) == False:
            return {}

        output = {}
        for package in self.channel_info[packages_key][repo]:
            copy = package.copy()

            # In schema version 2.0, we store a list of dicts containing info
            # about all available releases. These include "version" and
            # "platforms" keys that are used to pick the download for the
            # current machine.
            if self.schema_version >= 2.0:
                copy = self.select_release(copy)
            else:
                copy = self.select_platform(copy)

            if not copy:
                self.unavailable_packages.append(package['name'])
                continue

            output[copy['name']] = copy

        return output

    def get_unavailable_packages(self):
        """
        Provides a list of packages that are unavailable for the current
        platform/architecture that Sublime Text is running on.

        This list will be empty unless get_packages() is called first.

        :return: A list of package names
        """

        return self.unavailable_packages

########NEW FILE########
__FILENAME__ = github_repository_provider
import re

from ..clients.github_client import GitHubClient
from ..downloaders.downloader_exception import DownloaderException
from ..clients.client_exception import ClientException
from .provider_exception import ProviderException


class GitHubRepositoryProvider():
    """
    Allows using a public GitHub repository as the source for a single package.
    For legacy purposes, this can also be treated as the source for a Package
    Control "repository".

    :param repo:
        The public web URL to the GitHub repository. Should be in the format
        `https://github.com/user/package` for the master branch, or
        `https://github.com/user/package/tree/{branch_name}` for any other
        branch.

    :param settings:
        A dict containing at least the following fields:
          `cache_length`,
          `debug`,
          `timeout`,
          `user_agent`
        Optional fields:
          `http_proxy`,
          `https_proxy`,
          `proxy_username`,
          `proxy_password`,
          `query_string_params`
          `install_prereleases`
    """

    def __init__(self, repo, settings):
        self.cache = {}
        # Clean off the trailing .git to be more forgiving
        self.repo = re.sub('\.git$', '', repo)
        self.settings = settings
        self.failed_sources = {}

    @classmethod
    def match_url(cls, repo):
        """Indicates if this provider can handle the provided repo"""

        master = re.search('^https?://github.com/[^/]+/[^/]+/?$', repo)
        branch = re.search('^https?://github.com/[^/]+/[^/]+/tree/[^/]+/?$',
            repo)
        return master != None or branch != None

    def prefetch(self):
        """
        Go out and perform HTTP operations, caching the result

        :raises:
            DownloaderException: when there is an issue download package info
            ClientException: when there is an issue parsing package info
        """

        [name for name, info in self.get_packages()]

    def get_failed_sources(self):
        """
        List of any URLs that could not be accessed while accessing this repository

        :return:
            A generator of ("https://github.com/user/repo", Exception()) tuples
        """

        return self.failed_sources.items()

    def get_broken_packages(self):
        """
        For API-compatibility with RepositoryProvider
        """

        return {}.items()

    def get_packages(self, invalid_sources=None):
        """
        Uses the GitHub API to construct necessary info for a package

        :param invalid_sources:
            A list of URLs that should be ignored

        :raises:
            DownloaderException: when there is an issue download package info
            ClientException: when there is an issue parsing package info

        :return:
            A generator of
            (
                'Package Name',
                {
                    'name': name,
                    'description': description,
                    'author': author,
                    'homepage': homepage,
                    'last_modified': last modified date,
                    'download': {
                        'url': url,
                        'date': date,
                        'version': version
                    },
                    'previous_names': [],
                    'labels': [],
                    'sources': [the repo URL],
                    'readme': url,
                    'issues': url,
                    'donate': url,
                    'buy': None
                }
            )
            tuples
        """

        if 'get_packages' in self.cache:
            for key, value in self.cache['get_packages'].items():
                yield (key, value)
            return

        client = GitHubClient(self.settings)

        if invalid_sources != None and self.repo in invalid_sources:
            raise StopIteration()

        try:
            repo_info = client.repo_info(self.repo)
            download = client.download_info(self.repo)

            name = repo_info['name']
            details = {
                'name': name,
                'description': repo_info['description'],
                'homepage': repo_info['homepage'],
                'author': repo_info['author'],
                'last_modified': download.get('date'),
                'download': download,
                'previous_names': [],
                'labels': [],
                'sources': [self.repo],
                'readme': repo_info['readme'],
                'issues': repo_info['issues'],
                'donate': repo_info['donate'],
                'buy': None
            }
            self.cache['get_packages'] = {name: details}
            yield (name, details)

        except (DownloaderException, ClientException, ProviderException) as e:
            self.failed_sources[self.repo] = e
            self.cache['get_packages'] = {}
            raise StopIteration()

    def get_renamed_packages(self):
        """For API-compatibility with RepositoryProvider"""

        return {}

    def get_unavailable_packages(self):
        """
        Method for compatibility with RepositoryProvider class. These providers
        are based on API calls, and thus do not support different platform
        downloads, making it impossible for there to be unavailable packages.

        :return: An empty list
        """
        return []

########NEW FILE########
__FILENAME__ = github_user_provider
import re

from ..clients.github_client import GitHubClient
from ..downloaders.downloader_exception import DownloaderException
from ..clients.client_exception import ClientException
from .provider_exception import ProviderException


class GitHubUserProvider():
    """
    Allows using a GitHub user/organization as the source for multiple packages,
    or in Package Control terminology, a "repository".

    :param repo:
        The public web URL to the GitHub user/org. Should be in the format
        `https://github.com/user`.

    :param settings:
        A dict containing at least the following fields:
          `cache_length`,
          `debug`,
          `timeout`,
          `user_agent`,
        Optional fields:
          `http_proxy`,
          `https_proxy`,
          `proxy_username`,
          `proxy_password`,
          `query_string_params`
          `install_prereleases`
    """

    def __init__(self, repo, settings):
        self.cache = {}
        self.repo = repo
        self.settings = settings
        self.failed_sources = {}

    @classmethod
    def match_url(cls, repo):
        """Indicates if this provider can handle the provided repo"""

        return re.search('^https?://github.com/[^/]+/?$', repo) != None

    def prefetch(self):
        """
        Go out and perform HTTP operations, caching the result
        """

        [name for name, info in self.get_packages()]

    def get_failed_sources(self):
        """
        List of any URLs that could not be accessed while accessing this repository

        :raises:
            DownloaderException: when there is an issue download package info
            ClientException: when there is an issue parsing package info

        :return:
            A generator of ("https://github.com/user/repo", Exception()) tuples
        """

        return self.failed_sources.items()

    def get_broken_packages(self):
        """
        For API-compatibility with RepositoryProvider
        """

        return {}.items()

    def get_packages(self, invalid_sources=None):
        """
        Uses the GitHub API to construct necessary info for all packages

        :param invalid_sources:
            A list of URLs that should be ignored

        :raises:
            DownloaderException: when there is an issue download package info
            ClientException: when there is an issue parsing package info

        :return:
            A generator of
            (
                'Package Name',
                {
                    'name': name,
                    'description': description,
                    'author': author,
                    'homepage': homepage,
                    'last_modified': last modified date,
                    'download': {
                        'url': url,
                        'date': date,
                        'version': version
                    },
                    'previous_names': [],
                    'labels': [],
                    'sources': [the user URL],
                    'readme': url,
                    'issues': url,
                    'donate': url,
                    'buy': None
                }
            )
            tuples
        """

        if 'get_packages' in self.cache:
            for key, value in self.cache['get_packages'].items():
                yield (key, value)
            return

        client = GitHubClient(self.settings)

        if invalid_sources != None and self.repo in invalid_sources:
            raise StopIteration()

        try:
            user_repos = client.user_info(self.repo)
        except (DownloaderException, ClientException, ProviderException) as e:
            self.failed_sources = [self.repo]
            self.cache['get_packages'] = e
            raise e

        output = {}
        for repo_info in user_repos:
            try:
                name = repo_info['name']
                repo_url = 'https://github.com/' + repo_info['user_repo']

                download = client.download_info(repo_url)

                details = {
                    'name': name,
                    'description': repo_info['description'],
                    'homepage': repo_info['homepage'],
                    'author': repo_info['author'],
                    'last_modified': download.get('date'),
                    'download': download,
                    'previous_names': [],
                    'labels': [],
                    'sources': [self.repo],
                    'readme': repo_info['readme'],
                    'issues': repo_info['issues'],
                    'donate': repo_info['donate'],
                    'buy': None
                }
                output[name] = details
                yield (name, details)

            except (DownloaderException, ClientException, ProviderException) as e:
                self.failed_sources[repo_url] = e

        self.cache['get_packages'] = output

    def get_renamed_packages(self):
        """For API-compatibility with RepositoryProvider"""

        return {}

    def get_unavailable_packages(self):
        """
        Method for compatibility with RepositoryProvider class. These providers
        are based on API calls, and thus do not support different platform
        downloads, making it impossible for there to be unavailable packages.

        :return: An empty list
        """
        return []

########NEW FILE########
__FILENAME__ = provider_exception
class ProviderException(Exception):
    """If a provider could not return information"""

    def __str__(self):
        return self.args[0]

########NEW FILE########
__FILENAME__ = release_selector
import re
import sublime

from ..versions import version_sort, version_exclude_prerelease


class ReleaseSelector():
    """
    A base class for finding the best version of a package for the current machine
    """

    def select_release(self, package_info):
        """
        Returns a modified package info dict for package from package schema version 2.0

        :param package_info:
            A package info dict with a "releases" key

        :return:
            The package info dict with the "releases" key deleted, and a
            "download" key added that contains a dict with "version", "url" and
            "date" keys.
            None if no compatible relases are available.
        """

        releases = version_sort(package_info['releases'])
        if not self.settings.get('install_prereleases'):
            releases = version_exclude_prerelease(releases)

        for release in releases:
            platforms = release.get('platforms', '*')
            if not isinstance(platforms, list):
                platforms = [platforms]

            best_platform = self.get_best_platform(platforms)
            if not best_platform:
                continue

            # Default to '*' (for legacy reasons), see #604
            if not self.is_compatible_version(release.get('sublime_text', '*')):
                continue

            package_info['download'] = release
            package_info['last_modified'] = release.get('date')
            del package_info['releases']

            return package_info

        return None

    def select_platform(self, package_info):
        """
        Returns a modified package info dict for package from package schema version <= 1.2

        :param package_info:
            A package info dict with a "platforms" key

        :return:
            The package info dict with the "platforms" key deleted, and a
            "download" key added that contains a dict with "version" and "url"
            keys.
            None if no compatible platforms.
        """
        platforms = list(package_info['platforms'].keys())
        best_platform = self.get_best_platform(platforms)
        if not best_platform:
            return None

        package_info['download'] = package_info['platforms'][best_platform][0]
        package_info['download']['date'] = package_info.get('last_modified')
        del package_info['platforms']

        return package_info

    def get_best_platform(self, platforms):
        """
        Returns the most specific platform that matches the current machine

        :param platforms:
            An array of platform names for a package. E.g. ['*', 'windows', 'linux-x64']

        :return: A string reprenting the most specific matching platform
        """

        ids = [sublime.platform() + '-' + sublime.arch(), sublime.platform(),
            '*']

        for id in ids:
            if id in platforms:
                return id

        return None

    def is_compatible_version(self, version_range):
        min_version = float("-inf")
        max_version = float("inf")

        if version_range == '*':
            return True

        gt_match = re.match('>(\d+)$', version_range)
        ge_match = re.match('>=(\d+)$', version_range)
        lt_match = re.match('<(\d+)$', version_range)
        le_match = re.match('<=(\d+)$', version_range)
        range_match = re.match('(\d+) - (\d+)$', version_range)

        if gt_match:
            min_version = int(gt_match.group(1)) + 1
        elif ge_match:
            min_version = int(ge_match.group(1))
        elif lt_match:
            max_version = int(lt_match.group(1)) - 1
        elif le_match:
            max_version = int(le_match.group(1))
        elif range_match:
            min_version = int(range_match.group(1))
            max_version = int(range_match.group(2))
        else:
            return None

        if min_version > int(sublime.version()):
            return False
        if max_version < int(sublime.version()):
            return False

        return True

########NEW FILE########
__FILENAME__ = repository_provider
import json
import re
import os
from itertools import chain

try:
    # Python 3
    from urllib.parse import urljoin
except (ImportError):
    # Python 2
    from urlparse import urljoin

from ..console_write import console_write
from .release_selector import ReleaseSelector
from .provider_exception import ProviderException
from ..downloaders.downloader_exception import DownloaderException
from ..clients.client_exception import ClientException
from ..clients.github_client import GitHubClient
from ..clients.bitbucket_client import BitBucketClient
from ..download_manager import downloader


class RepositoryProvider(ReleaseSelector):
    """
    Generic repository downloader that fetches package info

    With the current channel/repository architecture where the channel file
    caches info from all includes repositories, these package providers just
    serve the purpose of downloading packages not in the default channel.

    The structure of the JSON a repository should contain is located in
    example-packages.json.

    :param repo:
        The URL of the package repository

    :param settings:
        A dict containing at least the following fields:
          `cache_length`,
          `debug`,
          `timeout`,
          `user_agent`
        Optional fields:
          `http_proxy`,
          `https_proxy`,
          `proxy_username`,
          `proxy_password`,
          `query_string_params`
          `install_prereleases`
    """

    def __init__(self, repo, settings):
        self.cache = {}
        self.repo_info = None
        self.schema_version = 0.0
        self.repo = repo
        self.settings = settings
        self.unavailable_packages = []
        self.failed_sources = {}
        self.broken_packages = {}

    @classmethod
    def match_url(cls, repo):
        """Indicates if this provider can handle the provided repo"""

        return True

    def prefetch(self):
        """
        Go out and perform HTTP operations, caching the result

        :raises:
            DownloaderException: when there is an issue download package info
            ClientException: when there is an issue parsing package info
        """

        [name for name, info in self.get_packages()]

    def get_failed_sources(self):
        """
        List of any URLs that could not be accessed while accessing this repository

        :return:
            A generator of ("https://example.com", Exception()) tuples
        """

        return self.failed_sources.items()

    def get_broken_packages(self):
        """
        List of package names for packages that are missing information

        :return:
            A generator of ("Package Name", Exception()) tuples
        """

        return self.broken_packages.items()

    def fetch(self):
        """
        Retrieves and loads the JSON for other methods to use

        :raises:
            ProviderException: when an error occurs trying to open a file
            DownloaderException: when an error occurs trying to open a URL
        """

        if self.repo_info != None:
            return

        self.repo_info = self.fetch_location(self.repo)

        if 'includes' not in self.repo_info:
            return

        # Allow repositories to include other repositories
        if re.match('https?://', self.repo, re.I) is None:
            relative_base = os.path.dirname(self.repo)
            is_http = False
        else:
            is_http = True

        includes = self.repo_info.get('includes', [])
        del self.repo_info['includes']
        for include in includes:
            if re.match('^\./|\.\./', include):
                if is_http:
                    include = urljoin(self.repo, include)
                else:
                    include = os.path.join(relative_base, include)
                    include = os.path.normpath(include)
            include_info = self.fetch_location(include)
            included_packages = include_info.get('packages', [])
            self.repo_info['packages'].extend(included_packages)

    def fetch_location(self, location):
        """
        Fetches the contents of a URL of file path

        :param location:
            The URL or file path

        :raises:
            ProviderException: when an error occurs trying to open a file
            DownloaderException: when an error occurs trying to open a URL

        :return:
            A dict of the parsed JSON
        """

        if re.match('https?://', self.repo, re.I):
            with downloader(location, self.settings) as manager:
                json_string = manager.fetch(location, 'Error downloading repository.')

        # Anything that is not a URL is expected to be a filesystem path
        else:
            if not os.path.exists(location):
                raise ProviderException(u'Error, file %s does not exist' % location)

            if self.settings.get('debug'):
                console_write(u'Loading %s as a repository' % location, True)

            # We open as binary so we get bytes like the DownloadManager
            with open(location, 'rb') as f:
                json_string = f.read()

        try:
            return json.loads(json_string.decode('utf-8'))
        except (ValueError):
            raise ProviderException(u'Error parsing JSON from repository %s.' % location)

    def get_packages(self, invalid_sources=None):
        """
        Provides access to the packages in this repository

        :param invalid_sources:
            A list of URLs that are permissible to fetch data from

        :raises:
            ProviderException: when an error occurs trying to open a file
            DownloaderException: when there is an issue download package info
            ClientException: when there is an issue parsing package info

        :return:
            A generator of
            (
                'Package Name',
                {
                    'name': name,
                    'description': description,
                    'author': author,
                    'homepage': homepage,
                    'last_modified': last modified date,
                    'download': {
                        'url': url,
                        'date': date,
                        'version': version
                    },
                    'previous_names': [old_name, ...],
                    'labels': [label, ...],
                    'sources': [url, ...],
                    'readme': url,
                    'issues': url,
                    'donate': url,
                    'buy': url
                }
            )
            tuples
        """

        if 'get_packages' in self.cache:
            for key, value in self.cache['get_packages'].items():
                yield (key, value)
            return

        if invalid_sources != None and self.repo in invalid_sources:
            raise StopIteration()

        try:
            self.fetch()
        except (DownloaderException, ProviderException) as e:
            self.failed_sources[self.repo] = e
            self.cache['get_packages'] = {}
            return

        def fail(message):
            exception = ProviderException(message)
            self.failed_sources[self.repo] = exception
            self.cache['get_packages'] = {}
            return
        schema_error = u'Repository %s does not appear to be a valid repository file because ' % self.repo

        if 'schema_version' not in self.repo_info:
            error_string = u'%s the "schema_version" JSON key is missing.' % schema_error
            fail(error_string)
            return

        try:
            self.schema_version = float(self.repo_info.get('schema_version'))
        except (ValueError):
            error_string = u'%s the "schema_version" is not a valid number.' % schema_error
            fail(error_string)
            return

        if self.schema_version not in [1.0, 1.1, 1.2, 2.0]:
            error_string = u'%s the "schema_version" is not recognized. Must be one of: 1.0, 1.1, 1.2 or 2.0.' % schema_error
            fail(error_string)
            return

        if 'packages' not in self.repo_info:
            error_string = u'%s the "packages" JSON key is missing.' % schema_error
            fail(error_string)
            return

        github_client = GitHubClient(self.settings)
        bitbucket_client = BitBucketClient(self.settings)

        # Backfill the "previous_names" keys for old schemas
        previous_names = {}
        if self.schema_version < 2.0:
            renamed = self.get_renamed_packages()
            for old_name in renamed:
                new_name = renamed[old_name]
                if new_name not in previous_names:
                    previous_names[new_name] = []
                previous_names[new_name].append(old_name)

        output = {}
        for package in self.repo_info['packages']:
            info = {
                'sources': [self.repo]
            }

            for field in ['name', 'description', 'author', 'last_modified', 'previous_names',
                    'labels', 'homepage', 'readme', 'issues', 'donate', 'buy']:
                if package.get(field):
                    info[field] = package.get(field)

            # Schema version 2.0 allows for grabbing details about a pacakge, or its
            # download from "details" urls. See the GitHubClient and BitBucketClient
            # classes for valid URLs.
            if self.schema_version >= 2.0:
                details = package.get('details')
                releases = package.get('releases')

                # Try to grab package-level details from GitHub or BitBucket
                if details:
                    if invalid_sources != None and details in invalid_sources:
                        continue

                    info['sources'].append(details)

                    try:
                        github_repo_info = github_client.repo_info(details)
                        bitbucket_repo_info = bitbucket_client.repo_info(details)

                        # When grabbing details, prefer explicit field values over the values
                        # from the GitHub or BitBucket API
                        if github_repo_info:
                            info = dict(chain(github_repo_info.items(), info.items()))
                        elif bitbucket_repo_info:
                            info = dict(chain(bitbucket_repo_info.items(), info.items()))
                        else:
                            raise ProviderException(u'Invalid "details" value "%s" for one of the packages in the repository %s.' % (details, self.repo))

                    except (DownloaderException, ClientException, ProviderException) as e:
                        if 'name' in info:
                            self.broken_packages[info['name']] = e
                        self.failed_sources[details] = e
                        continue

            if 'name' not in info:
                self.failed_sources[self.repo] = ProviderException(u'No "name" value for one of the packages in the repository %s.' % self.repo)
                continue

            if self.schema_version >= 2.0:
                # If no releases info was specified, also grab the download info from GH or BB
                if not releases and details:
                    releases = [{'details': details}]

                if not releases:
                    e = ProviderException(u'No "releases" value for the package "%s" in the repository %s.' % (info['name'], self.repo))
                    self.broken_packages[info['name']] = e
                    continue

                if not isinstance(releases, list):
                    e = ProviderException(u'The "releases" value is not an array or the package "%s" in the repository %s.' % (info['name'], self.repo))
                    self.broken_packages[info['name']] = e
                    continue

                # This allows developers to specify a GH or BB location to get releases from,
                # especially tags URLs (https://github.com/user/repo/tags or
                # https://bitbucket.org/user/repo#tags)
                info['releases'] = []
                for release in releases:
                    download_details = None
                    download_info = {}

                    # Make sure that explicit fields are copied over
                    for field in ['platforms', 'sublime_text', 'version', 'url', 'date']:
                        if field in release:
                            download_info[field] = release[field]

                    if 'details' in release:
                        download_details = release['details']

                        try:
                            github_download = github_client.download_info(download_details)
                            bitbucket_download = bitbucket_client.download_info(download_details)

                            # Overlay the explicit field values over values fetched from the APIs
                            if github_download:
                                download_info = dict(chain(github_download.items(), download_info.items()))
                            # No matching tags
                            elif github_download == False:
                                download_info = {}
                            elif bitbucket_download:
                                download_info = dict(chain(bitbucket_download.items(), download_info.items()))
                            # No matching tags
                            elif bitbucket_download == False:
                                download_info = {}
                            else:
                                raise ProviderException(u'Invalid "details" value "%s" under the "releases" key for the package "%s" in the repository %s.' % (download_details, info['name'], self.repo))

                        except (DownloaderException, ClientException, ProviderException) as e:
                            self.broken_packages[info['name']] = e
                            continue

                    if download_info:
                        info['releases'].append(download_info)
                    else:
                        self.broken_packages[info['name']] = ProviderException(u'No valid semver tags found at %s for the package "%s" in the repository %s.' % (download_details, info['name'], self.repo))
                        continue

                info = self.select_release(info)

            # Schema version 1.0, 1.1 and 1.2 just require that all values be
            # explicitly specified in the package JSON
            else:
                info['platforms'] = package.get('platforms')
                info = self.select_platform(info)

            if not info:
                self.unavailable_packages.append(package['name'])
                continue

            if 'author' not in info:
                self.broken_packages[info['name']] = ProviderException(u'No "author" key for the package "%s" in the repository %s.' % (info['name'], self.repo))
                continue

            if 'download' not in info and 'releases' not in info:
                self.broken_packages[info['name']] = ProviderException(u'No "releases" key for the package "%s" in the repository %s.' % (info['name'], self.repo))
                continue

            # Make sure the single download, or all releases, have the appropriate keys.
            # We use a function here so that we can break out of multiple loops.
            def has_broken_release():
                download = info.get('download')
                download_list = [download] if download else []
                for release in info.get('releases', download_list):
                    for key in ['version', 'date', 'url']:
                        if key not in release:
                            self.broken_packages[info['name']] = ProviderException(u'Missing "%s" key for one of the releases of the package "%s" in the repository %s.' % (key, info['name'], self.repo))
                            return True
                return False

            if has_broken_release():
                continue

            for field in ['previous_names', 'labels']:
                if field not in info:
                    info[field] = []

            for field in ['description', 'readme', 'issues', 'donate', 'buy']:
                if field not in info:
                    info[field] = None

            if 'homepage' not in info:
                info['homepage'] = self.repo

            if 'download' in info:
                # Rewrites the legacy "zipball" URLs to the new "zip" format
                info['download']['url'] = re.sub(
                    '^(https://nodeload.github.com/[^/]+/[^/]+/)zipball(/.*)$',
                    '\\1zip\\2', info['download']['url'])

                # Rewrites the legacy "nodeload" URLs to the new "codeload" subdomain
                info['download']['url'] = info['download']['url'].replace(
                    'nodeload.github.com', 'codeload.github.com')

                # Extract the date from the download
                if 'last_modified' not in info:
                    info['last_modified'] = info['download']['date']

            elif 'releases' in info and 'last_modified' not in info:
                # Extract a date from the newest download
                date = '1970-01-01 00:00:00'
                for release in info['releases']:
                    if 'date' in release and release['date'] > date:
                        date = release['date']
                info['last_modified'] = date

            if info['name'] in previous_names:
                info['previous_names'].extend(previous_names[info['name']])

            output[info['name']] = info
            yield (info['name'], info)

        self.cache['get_packages'] = output

    def get_renamed_packages(self):
        """:return: A dict of the packages that have been renamed"""

        if self.schema_version < 2.0:
            return self.repo_info.get('renamed_packages', {})

        output = {}
        for package in self.repo_info['packages']:
            if 'previous_names' not in package:
                continue

            previous_names = package['previous_names']
            if not isinstance(previous_names, list):
                previous_names = [previous_names]

            for previous_name in previous_names:
                output[previous_name] = package['name']

        return output

    def get_unavailable_packages(self):
        """
        Provides a list of packages that are unavailable for the current
        platform/architecture that Sublime Text is running on.

        This list will be empty unless get_packages() is called first.

        :return: A list of package names
        """

        return self.unavailable_packages

########NEW FILE########
__FILENAME__ = reloader
import sys

import sublime


st_version = 2
# With the way ST3 works, the sublime module is not "available" at startup
# which results in an empty version number
if sublime.version() == '' or int(sublime.version()) > 3000:
    st_version = 3
    from imp import reload


# Python allows reloading modules on the fly, which allows us to do live upgrades.
# The only caveat to this is that you have to reload in the dependency order.
#
# Thus is module A depends on B and we don't reload B before A, when A is reloaded
# it will still have a reference to the old B. Thus we hard-code the dependency
# order of the various Package Control modules so they get reloaded properly.
#
# There are solutions for doing this all programatically, but this is much easier
# to understand.

reload_mods = []
for mod in sys.modules:
    if mod[0:15].lower().replace(' ', '_') == 'package_control' and sys.modules[mod] != None:
        reload_mods.append(mod)

mod_prefix = 'package_control'
if st_version == 3:
    mod_prefix = 'Package Control.' + mod_prefix

mods_load_order = [
    '',

    '.sys_path',
    '.cache',
    '.http_cache',
    '.ca_certs',
    '.clear_directory',
    '.cmd',
    '.console_write',
    '.rmtree',
    '.preferences_filename',
    '.show_error',
    '.unicode',
    '.thread_progress',
    '.package_io',
    '.semver',
    '.versions',

    '.http',
    '.http.invalid_certificate_exception',
    '.http.debuggable_http_response',
    '.http.debuggable_https_response',
    '.http.debuggable_http_connection',
    '.http.persistent_handler',
    '.http.debuggable_http_handler',
    '.http.validating_https_connection',
    '.http.validating_https_handler',

    '.clients',
    '.clients.client_exception',
    '.clients.bitbucket_client',
    '.clients.github_client',
    '.clients.readme_client',
    '.clients.json_api_client',

    '.providers',
    '.providers.provider_exception',
    '.providers.bitbucket_repository_provider',
    '.providers.channel_provider',
    '.providers.github_repository_provider',
    '.providers.github_user_provider',
    '.providers.repository_provider',
    '.providers.release_selector',

    '.download_manager',

    '.downloaders',
    '.downloaders.downloader_exception',
    '.downloaders.rate_limit_exception',
    '.downloaders.binary_not_found_error',
    '.downloaders.non_clean_exit_error',
    '.downloaders.non_http_error',
    '.downloaders.caching_downloader',
    '.downloaders.decoding_downloader',
    '.downloaders.limiting_downloader',
    '.downloaders.cert_provider',
    '.downloaders.urllib_downloader',
    '.downloaders.cli_downloader',
    '.downloaders.curl_downloader',
    '.downloaders.wget_downloader',
    '.downloaders.wininet_downloader',
    '.downloaders.background_downloader',

    '.upgraders',
    '.upgraders.vcs_upgrader',
    '.upgraders.git_upgrader',
    '.upgraders.hg_upgrader',

    '.package_manager',
    '.package_creator',
    '.package_installer',
    '.package_renamer',

    '.commands',
    '.commands.add_channel_command',
    '.commands.add_repository_command',
    '.commands.create_package_command',
    '.commands.disable_package_command',
    '.commands.discover_packages_command',
    '.commands.enable_package_command',
    '.commands.existing_packages_command',
    '.commands.grab_certs_command',
    '.commands.install_package_command',
    '.commands.list_packages_command',
    '.commands.package_message_command',
    '.commands.remove_package_command',
    '.commands.upgrade_all_packages_command',
    '.commands.upgrade_package_command',

    '.package_cleanup',
    '.automatic_upgrader'
]

for suffix in mods_load_order:
    mod = mod_prefix + suffix
    if mod in reload_mods:
        reload(sys.modules[mod])

########NEW FILE########
__FILENAME__ = rmtree
import os
import shutil
import stat



def _on_error(function, path, excinfo):
    """
    Error handler for shutil.rmtree that tries to add write privileges

    :param func:
        The function that raised the error

    :param path:
        The full filesystem path to the file

    :param excinfo:
        The exception information
    """
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        function(path)
    else:
        raise


def rmtree(path):
    """
    Tries to delete a folder, changing files from read-only if such files
    are encountered

    :param path:
        The path to the folder to be deleted
    """
    shutil.rmtree(path, onerror=_on_error)

########NEW FILE########
__FILENAME__ = semver
"""pysemver: Semantic Version comparing for Python.

Provides comparing of semantic versions by using SemVer objects using rich comperations plus the
possibility to match a selector string against versions. Interesting for version dependencies.
Versions look like: "1.7.12+b.133"
Selectors look like: ">1.7.0 || 1.6.9+b.111 - 1.6.9+b.113"

Example usages:
    >>> SemVer(1, 2, 3, build=13)
    SemVer("1.2.3+13")
    >>> SemVer.valid("1.2.3.4")
    False
    >>> SemVer.clean("this is unimportant text 1.2.3-2 and will be stripped")
    "1.2.3-2"
    >>> SemVer("1.7.12+b.133").satisfies(">1.7.0 || 1.6.9+b.111 - 1.6.9+b.113")
    True
    >>> SemSel(">1.7.0 || 1.6.9+b.111 - 1.6.9+b.113").matches(SemVer("1.7.12+b.133"),
    ... SemVer("1.6.9+b.112"), SemVer("1.6.10"))
    [SemVer("1.7.12+b.133"), SemVer("1.6.9+b.112")]
    >>> min(_)
    SemVer("1.6.9+b.112")
    >>> _.patch
    9

Exported classes:
    * SemVer(collections.namedtuple())
        Parses semantic versions and defines methods for them. Supports rich comparisons.
    * SemSel(tuple)
        Parses semantic version selector strings and defines methods for them.
    * SelParseError(Exception)
        An error among others raised when parsing a semantic version selector failed.

Other classes:
    * SemComparator(object)
    * SemSelAndChunk(list)
    * SemSelOrChunk(list)

Functions/Variables/Constants:
    none


Copyright (c) 2013 Zachary King, FichteFoll

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions: The above copyright notice and this
permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import re
import sys
from collections import namedtuple  # Python >=2.6


__all__ = ('SemVer', 'SemSel', 'SelParseError')


if sys.version_info[0] == 3:
    basestring = str
    cmp = lambda a, b: (a > b) - (a < b)


# @functools.total_ordering would be nice here but was added in 2.7, __cmp__ is not Py3
class SemVer(namedtuple("_SemVer", 'major, minor, patch, prerelease, build')):
    """Semantic Version, consists of 3 to 5 components defining the version's adicity.

    See http://semver.org/ (2.0.0-rc.1) for the standard mainly used for this implementation, few
    changes have been made.

    Information on this particular class and their instances:
        - Immutable and hashable.
        - Subclasses `collections.namedtuple`.
        - Always `True` in boolean context.
        - len() returns an int between 3 and 5; 4 when a pre-release is set and 5 when a build is
          set. Note: Still returns 5 when build is set but not pre-release.
        - Parts of the semantic version can be accessed by integer indexing, key (string) indexing,
          slicing and getting an attribute. Returned slices are tuple. Leading '-' and '+' of
          optional components are not stripped. Supported keys/attributes:
          major, minor, patch, prerelease, build.

          Examples:
            s = SemVer("1.2.3-4.5+6")
            s[2] == 3
            s[:3] == (1, 2, 3)
            s['build'] == '-4.5'
            s.major == 1

    Short information on semantic version structure:

    Semantic versions consist of:
        * a major component (numeric)
        * a minor component (numeric)
        * a patch component (numeric)
        * a pre-release component [optional]
        * a build component [optional]

    The pre-release component is indicated by a hyphen '-' and followed by alphanumeric[1] sequences
    separated by dots '.'. Sequences are compared numerically if applicable (both sequences of two
    versions are numeric) or lexicographically. May also include hyphens. The existence of a
    pre-release component lowers the actual version; the shorter pre-release component is considered
    lower. An 'empty' pre-release component is considered to be the least version for this
    major-minor-patch combination (e.g. "1.0.0-").

    The build component may follow the optional pre-release component and is indicated by a plus '+'
    followed by sequences, just as the pre-release component. Comparing works similarly. However the
    existence of a build component raises the actual version and may also raise a pre-release. An
    'empty' build component is considered to be the highest version for this
    major-minor-patch-prerelease combination (e.g. "1.2.3+").


    [1]: Regexp for a sequence: r'[0-9A-Za-z-]+'.
    """

    # Static class variables
    _base_regex = r'''(?x)
        (?P<major>[0-9]+)
        \.(?P<minor>[0-9]+)
        \.(?P<patch>[0-9]+)
        (?:\-(?P<prerelease>(?:[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?))?
        (?:\+(?P<build>(?:[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?))?'''
    _search_regex = re.compile(_base_regex)
    _match_regex  = re.compile('^%s$' % _base_regex)  # required because of $ anchor

    # "Constructor"
    def __new__(cls, *args, **kwargs):
        """There are two different constructor styles that are allowed:
        - Option 1 allows specification of a semantic version as a string and the option to "clean"
          the string before parsing it.
        - Option 2 allows specification of each component separately as one parameter.

        Note that all the parameters specified in the following sections can be passed either as
        positional or as named parameters while considering the usual Python rules for this. As
        such, `SemVer(1, 2, minor=1)` will result in an exception and not in `SemVer("1.1.2")`.

        Option 1:
            Constructor examples:
                SemVer("1.0.1")
                SemVer("this version 1.0.1-pre.1 here", True)
                SemVer(ver="0.0.9-pre-alpha+34", clean=False)

            Parameters:
                * ver (str)
                    The string containing the version.
                * clean = `False` (bool; optional)
                    If this is true in boolean context, `SemVer.clean(ver)` is called before
                    parsing.

        Option 2:
            Constructor examples:
                SemVer(1, 0, 1)
                SemVer(1, '0', prerelease='pre-alpha', patch=1, build=34)
                SemVer(**dict(minor=2, major=1, patch=3))

            Parameters:
                * major (int, str, float ...)
                * minor (...)
                * patch (...)
                    Major to patch components must be an integer or convertable to an int (e.g. a
                    string or another number type).

                * prerelease = `None` (str, int, float ...; optional)
                * build = `None` (...; optional)
                    Pre-release and build components should be a string (or number) type.
                    Will be passed to `str()` if not already a string but the final string must
                    match '^[0-9A-Za-z.-]*$'

        Raises:
            * TypeError
                Invalid parameter type(s) or combination (e.g. option 1 and 2).
            * ValueError
                Invalid semantic version or option 2 parameters unconvertable.
        """
        ver, clean, comps = None, False, None
        kw, l = kwargs.copy(), len(args) + len(kwargs)

        def inv():
            raise TypeError("Invalid parameter combination: args=%s; kwargs=%s" % (args, kwargs))

        # Do validation and parse the parameters
        if l == 0 or l > 5:
            raise TypeError("SemVer accepts at least 1 and at most 5 arguments (%d given)" % l)

        elif l < 3:
            if len(args) == 2:
                ver, clean = args
            else:
                ver = args[0] if args else kw.pop('ver', None)
                clean = kw.pop('clean', clean)
                if kw:
                    inv()

        else:
            comps = list(args) + [kw.pop(cls._fields[k], None) for k in range(len(args), 5)]
            if kw or any(comps[i] is None for i in range(3)):
                inv()

            typecheck = (int,) * 3 + (basestring,) * 2
            for i, (v, t) in enumerate(zip(comps, typecheck)):
                if v is None:
                    continue
                elif not isinstance(v, t):
                    try:
                        if i < 3:
                            v = typecheck[i](v)
                        else:  # The real `basestring` can not be instatiated (Py2)
                            v = str(v)
                    except ValueError as e:
                        # Modify the exception message. I can't believe this actually works
                        e.args = ("Parameter #%d must be of type %s or convertable"
                                  % (i, t.__name__),)
                        raise
                    else:
                        comps[i] = v
                if t is basestring and not re.match(r"^[0-9A-Za-z.-]*$", v):
                    raise ValueError("Build and pre-release strings must match '^[0-9A-Za-z.-]*$'")

        # Final adjustments
        if not comps:
            if ver is None or clean is None:
                inv()
            ver = clean and cls.clean(ver) or ver
            comps = cls._parse(ver)

        # Create the obj
        return super(SemVer, cls).__new__(cls, *comps)

    # Magic methods
    def __str__(self):
        return ('.'.join(map(str, self[:3]))
                + ('-' + self.prerelease if self.prerelease is not None else '')
                + ('+' + self.build if self.build is not None else ''))

    def __repr__(self):
        # Use the shortest representation - what would you prefer?
        return 'SemVer("%s")' % str(self)
        # return 'SemVer(%s)' % ', '.join('%s=%r' % (k, getattr(self, k)) for k in self._fields)

    def __len__(self):
        return 3 + (self.build is not None and 2 or self.prerelease is not None)

    # Magic rich comparing methods
    def __gt__(self, other):
        return self._compare(other) == 1 if isinstance(other, SemVer) else NotImplemented

    def __eq__(self, other):
        return self._compare(other) == 0 if isinstance(other, SemVer) else NotImplemented

    def __lt__(self, other):
        return not (self > other or self == other)

    def __ge__(self, other):
        return not (self < other)

    def __le__(self, other):
        return not (self > other)

    def __ne__(self, other):
        return not (self == other)

    # Utility (class-)methods
    def satisfies(self, sel):
        """Alias for `bool(sel.matches(self))` or `bool(SemSel(sel).matches(self))`.

        See `SemSel.__init__()` and `SemSel.matches(*vers)` for possible exceptions.

        Returns:
            * bool: `True` if the version matches the passed selector, `False` otherwise.
        """
        if not isinstance(sel, SemSel):
            sel = SemSel(sel)  # just "re-raise" exceptions

        return bool(sel.matches(self))

    @classmethod
    def valid(cls, ver):
        """Check if `ver` is a valid semantic version. Classmethod.

        Parameters:
            * ver (str)
                The string that should be stripped.

        Raises:
            * TypeError
                Invalid parameter type.

        Returns:
            * bool: `True` if it is valid, `False` otherwise.
        """
        if not isinstance(ver, basestring):
            raise TypeError("%r is not a string" % ver)

        if cls._match_regex.match(ver):
            return True
        else:
            return False

    @classmethod
    def clean(cls, vers):
        """Remove everything before and after a valid version string. Classmethod.

        Parameters:
            * vers (str)
                The string that should be stripped.

        Raises:
            * TypeError
                Invalid parameter type.

        Returns:
            * str:  The stripped version string. Only the first version is matched.
            * None: No version found in the string.
        """
        if not isinstance(vers, basestring):
            raise TypeError("%r is not a string" % vers)
        m = cls._search_regex.search(vers)
        if m:
            return vers[m.start():m.end()]
        else:
            return None

    # Private (class-)methods
    @classmethod
    def _parse(cls, ver):
        """Private. Do not touch. Classmethod.
        """
        if not isinstance(ver, basestring):
            raise TypeError("%r is not a string" % ver)

        match = cls._match_regex.match(ver)

        if match is None:
            raise ValueError("'%s' is not a valid SemVer string" % ver)

        g = list(match.groups())
        for i in range(3):
            g[i] = int(g[i])

        return g  # Will be passed as namedtuple(...)(*g)

    def _compare(self, other):
        """Private. Do not touch.
        self > other: 1
        self = other: 0
        self < other: -1
        """
        # Shorthand lambdas
        cp_len = lambda t, i=0: cmp(len(t[i]), len(t[not i]))

        for i, (x1, x2) in enumerate(zip(self, other)):
            if i > 2:
                if x1 is None and x2 is None:
                    continue

                # self is greater when other has a prerelease but self doesn't
                # self is less    when other has a build      but self doesn't
                if x1 is None or x2 is None:
                    return int(2 * (i - 3.5)) * (1 - 2 * (x1 is None))

                # self is less when other's build is empty
                if i == 4 and (not x1 or not x2) and x1 != x2:
                    return 1 - 2 * bool(x1)

                # Split by '.' and use numeric comp or lexicographical order
                t2 = [x1.split('.'), x2.split('.')]
                for y1, y2 in zip(*t2):
                    if y1.isdigit() and y2.isdigit():
                        y1 = int(y1)
                        y2 = int(y2)
                    if y1 > y2:
                        return 1
                    elif y1 < y2:
                        return -1

                # The "longer" sub-version is greater
                d = cp_len(t2)
                if d:
                    return d
            else:
                if x1 > x2:
                    return 1
                elif x1 < x2:
                    return -1

        # The versions equal
        return 0


class SemComparator(object):
    """Holds a SemVer object and a comparing operator and can match these against a given version.

    Constructor: SemComparator('<=', SemVer("1.2.3"))

    Methods:
        * matches(ver)
    """
    # Private properties
    _ops = {
        '>=': '__ge__',
        '<=': '__le__',
        '>':  '__gt__',
        '<':  '__lt__',
        '=':  '__eq__',
        '!=': '__ne__'
    }
    _ops_satisfy = ('~', '!')

    # Constructor
    def __init__(self, op, ver):
        """Constructor examples:
        SemComparator('<=', SemVer("1.2.3"))
        SemComparator('!=', SemVer("2.3.4"))

        Parameters:
            * op (str, False, None)
                One of [>=, <=, >, <, =, !=, !, ~] or evaluates to `False` which defaults to '~'.
                '~' means a "satisfy" operation where pre-releases and builds are ignored.
                '!' is a negative "~".
            * ver (SemVer)
                Holds the version to compare with.

        Raises:
            * ValueError
                Invalid `op` parameter.
            * TypeError
                Invalid `ver` parameter.
        """
        super(SemComparator, self).__init__()

        if op and op not in self._ops_satisfy and op not in self._ops:
            raise ValueError("Invalid value for `op` parameter.")
        if not isinstance(ver, SemVer):
            raise TypeError("`ver` parameter is not instance of SemVer.")

        # Default to '~' for versions with no build or pre-release
        op = op or '~'
        # Fallback to '=' and '!=' if len > 3
        if len(ver) != 3:
            if op == '~':
                op = '='
            if op == '!':
                op = '!='

        self.op  = op
        self.ver = ver

    # Magic methods
    def __str__(self):
        return (self.op or "") + str(self.ver)

    # Utility methods
    def matches(self, ver):
        """Match the internal version (constructor) against `ver`.

        Parameters:
            * ver (SemVer)

        Raises:
            * TypeError
                Could not compare `ver` against the version passed in the constructor with the
                passed operator.

        Returns:
            * bool
                `True` if the version matched the specified operator and internal version, `False`
                otherwise.
        """
        if self.op in self._ops_satisfy:
            # Compare only the first three parts (which are tuples) and directly
            return bool((self.ver[:3] == ver[:3]) + (self.op == '!') * -1)
        ret = getattr(ver, self._ops[self.op])(self.ver)
        if ret == NotImplemented:
            raise TypeError("Unable to compare %r with operator '%s'" % (ver, self.op))
        return ret


class SemSelAndChunk(list):
    """Extends list and defines a few methods used for matching versions.

    New elements should be added by calling `.add_child(op, ver)` which creates a SemComparator
    instance and adds that to itself.

    Methods:
        * matches(ver)
        * add_child(op, ver)
    """
    # Magic methods
    def __str__(self):
        return ' '.join(map(str, self))

    # Utitlity methods
    def matches(self, ver):
        """Match all of the added children against `ver`.

        Parameters:
            * ver (SemVer)

        Raises:
            * TypeError
                Invalid `ver` parameter.

        Returns:
            * bool:
                `True` if *all* of the SemComparator children match `ver`, `False` otherwise.
        """
        if not isinstance(ver, SemVer):
            raise TypeError("`ver` parameter is not instance of SemVer.")
        return all(cp.matches(ver) for cp in self)

    def add_child(self, op, ver):
        """Create a SemComparator instance with the given parameters and appends that to self.

        Parameters:
            * op (str)
            * ver (SemVer)
        Both parameters are forwarded to `SemComparator.__init__`, see there for a more detailed
        description.

        Raises:
            Exceptions raised by `SemComparator.__init__`.
        """
        self.append(SemComparator(op, SemVer(ver)))


class SemSelOrChunk(list):
    """Extends list and defines a few methods used for matching versions.

    New elements should be added by calling `.new_child()` which returns a SemSelAndChunk
    instance.

    Methods:
        * matches(ver)
        * new_child()
    """
    # Magic methods
    def __str__(self):
        return ' || '.join(map(str, self))

    # Utility methods
    def matches(self, ver):
        """Match all of the added children against `ver`.

        Parameters:
            * ver (SemVer)

        Raises:
            * TypeError
                Invalid `ver` parameter.

        Returns:
            * bool
                `True` if *any* of the SemSelAndChunk children matches `ver`.
                `False` otherwise.
        """
        if not isinstance(ver, SemVer):
            raise TypeError("`ver` parameter is not instance of SemVer.")
        return any(ch.matches(ver) for ch in self)

    def new_child(self):
        """Creates a new SemSelAndChunk instance, appends it to self and returns it.

        Returns:
            * SemSelAndChunk: An empty instance.
        """
        ch = SemSelAndChunk()
        self.append(ch)
        return ch


class SelParseError(Exception):
    """An Exception raised when parsing a semantic selector failed.
    """
    pass


# Subclass `tuple` because this is a somewhat simple method to make this immutable
class SemSel(tuple):
    """A Semantic Version Selector, holds a selector and can match it against semantic versions.

    Information on this particular class and their instances:
        - Immutable but not hashable because the content within might have changed.
        - Subclasses `tuple` but does not behave like one.
        - Always `True` in boolean context.
        - len() returns the number of containing *and chunks* (see below).
        - Iterable, iterates over containing *and chunks*.

    When talking about "versions" it refers to a semantic version (SemVer). For information on how
    versions compare to one another, see SemVer's doc string.

    List for **comparators**:
        "1.0.0"            matches the version 1.0.0 and all its pre-release and build variants
        "!1.0.0"           matches any version that is not 1.0.0 or any of its variants
        "=1.0.0"           matches only the version 1.0.0
        "!=1.0.0"          matches any version that is not 1.0.0
        ">=1.0.0"          matches versions greater than or equal 1.0.0
        "<1.0.0"           matches versions smaller than 1.0.0
        "1.0.0 - 1.0.3"    matches versions greater than or equal 1.0.0 thru 1.0.3
        "~1.0"             matches versions greater than or equal 1.0.0 thru 1.0.9999 (and more)
        "~1", "1.x", "1.*" match versions greater than or equal 1.0.0 thru 1.9999.9999 (and more)
        "~1.1.2"           matches versions greater than or equal 1.1.2 thru 1.1.9999 (and more)
        "~1.1.2+any"       matches versions greater than or equal 1.1.2+any thru 1.1.9999 (and more)
        "*", "~", "~x"     match any version

    Multiple comparators can be combined by using ' ' spaces and every comparator must match to make
    the **and chunk** match a version.
    Multiple and chunks can be combined to **or chunks** using ' || ' and match if any of the and
    chunks split by these matches.

    A complete example would look like:
        ~1 || 0.0.3 || <0.0.2 >0.0.1+b.1337 || 2.0.x || 2.1.0 - 2.1.0+b.12 !=2.1.0+b.9

    Methods:
        * matches(*vers)
    """
    # Private properties
    _fuzzy_regex = re.compile(r'''(?x)^
        (?P<op>[<>]=?|~>?=?)?
        (?:(?P<major>\d+)
         (?:\.(?P<minor>\d+)
          (?:\.(?P<patch>\d+)
           (?P<other>[-+][a-zA-Z0-9-+.]*)?
          )?
         )?
        )?$''')
    _xrange_regex = re.compile(r'''(?x)^
        (?P<op>[<>]=?|~>?=?)?
        (?:(?P<major>\d+|[xX*])
         (?:\.(?P<minor>\d+|[xX*])
          (?:\.(?P<patch>\d+|[xX*]))?
         )?
        )
        (?P<other>.*)$''')
    _split_op_regex = re.compile(r'^(?P<op>=|[<>!]=?)?(?P<ver>.*)$')

    # "Constructor"
    def __new__(cls, sel):
        """Constructor examples:
            SemSel(">1.0.0")
            SemSel("~1.2.9 !=1.2.12")

        Parameters:
            * sel (str)
                A version selector string.

        Raises:
            * TypeError
                `sel` parameter is not a string.
            * ValueError
                A version in the selector could not be matched as a SemVer.
            * SemParseError
                The version selector's syntax is unparsable; invalid ranges (fuzzy, xrange or
                explicit range) or invalid '||'
        """
        chunk = cls._parse(sel)
        return super(SemSel, cls).__new__(cls, (chunk,))

    # Magic methods
    def __str__(self):
        return str(self._chunk)

    def __repr__(self):
        return 'SemSel("%s")' % self._chunk

    def __len__(self):
        # What would you expect?
        return len(self._chunk)

    def __iter__(self):
        return iter(self._chunk)

    # Read-only (private) attributes
    @property
    def _chunk(self):
        return self[0]

    # Utility methods
    def matches(self, *vers):
        """Match the selector against a selection of versions.

        Parameters:
            * *vers (str, SemVer)
                Versions can be passed as strings and SemVer objects will be created with them.
                May also be a mixed list.

        Raises:
            * TypeError
                A version is not an instance of str (basestring) or SemVer.
            * ValueError
                A string version could not be parsed as a SemVer.

        Returns:
            * list
                A list with all the versions that matched, may be empty. Use `max()` to determine
                the highest matching version, or `min()` for the lowest.
        """
        ret = []
        for v in vers:
            if isinstance(v, str):
                t = self._chunk.matches(SemVer(v))
            elif isinstance(v, SemVer):
                t = self._chunk.matches(v)
            else:
                raise TypeError("Invalid parameter type '%s': %s" % (v, type(v)))
            if t:
                ret.append(v)

        return ret

    # Private methods
    @classmethod
    def _parse(cls, sel):
        """Private. Do not touch.

        1. split by whitespace into tokens
            a. start new and_chunk on ' || '
            b. parse " - " ranges
            c. replace "xX*" ranges with "~" equivalent
            d. parse "~" ranges
            e. parse unmatched token as comparator
            ~. append to current and_chunk
        2. return SemSelOrChunk

        Raises TypeError, ValueError or SelParseError.
        """
        if not isinstance(sel, basestring):
            raise TypeError("Selector must be a string")
        if not sel:
            raise ValueError("String must not be empty")

        # Split selector by spaces and crawl the tokens
        tokens = sel.split()
        i = -1
        or_chunk = SemSelOrChunk()
        and_chunk = or_chunk.new_child()

        while i + 1 < len(tokens):
            i += 1
            t = tokens[i]

            # Replace x ranges with ~ selector
            m = cls._xrange_regex.match(t)
            m = m and m.groups('')
            if m and any(not x.isdigit() for x in m[1:4]) and not m[0].startswith('>'):
                # (do not match '>1.0' or '>*')
                if m[4]:
                    raise SelParseError("XRanges do not allow pre-release or build components")

                # Only use digit parts and fail if digit found after non-digit
                mm, xran = [], False
                for x in m[1:4]:
                    if x.isdigit():
                        if xran:
                            raise SelParseError("Invalid fuzzy range or XRange '%s'" % tokens[i])
                        mm.append(x)
                    else:
                        xran = True
                t = m[0] + '.'.join(mm)  # x for x in m[1:4] if x.isdigit())
                # Append "~" if not already present
                if not t.startswith('~'):
                    t = '~' + t

            # switch t:
            if t == '||':
                if i == 0 or tokens[i - 1] == '||' or i + 1 == len(tokens):
                    raise SelParseError("OR range must not be empty")
                # Start a new and_chunk
                and_chunk = or_chunk.new_child()

            elif t == '-':
                # ' - ' range
                i += 1
                invalid = False
                try:
                    # If these result in exceptions, you know you're doing it wrong
                    t = tokens[i]
                    c = and_chunk[-1]
                except:
                    raise SelParseError("Invalid ' - ' range position")

                # If there is an op in front of one of the bound versions
                invalid = (c.op not in ('=', '~')
                           or cls._split_op_regex.match(t).group(1) not in (None, '='))
                if invalid:
                    raise SelParseError("Invalid ' - ' range '%s - %s'"
                                        % (tokens[i - 2], tokens[i]))

                c.op = ">="
                and_chunk.add_child('<=', t)

            elif t == '':
                # Multiple spaces
                pass

            elif t.startswith('~'):
                m = cls._fuzzy_regex.match(t)
                if not m:
                    raise SelParseError("Invalid fuzzy range or XRange '%s'" % tokens[i])

                mm, m = m.groups('')[1:4], m.groupdict('')  # mm: major to patch

                # Minimum requirement
                min_ver = ('.'.join(x or '0' for x in mm) + '-'
                           if not m['other']
                           else cls._split_op_regex(t[1:]).group('ver'))
                and_chunk.add_child('>=', min_ver)

                if m['major']:
                    # Increase version before none (or second to last if '~1.2.3')
                    e = [0, 0, 0]
                    for j, d in enumerate(mm):
                        if not d or j == len(mm) - 1:
                            e[j - 1] = e[j - 1] + 1
                            break
                        e[j] = int(d)

                    and_chunk.add_child('<', '.'.join(str(x) for x in e) + '-')

                # else: just plain '~' or '*', or '~>X' which are already handled

            else:
                # A normal comparator
                m = cls._split_op_regex.match(t).groupdict()  # this regex can't fail
                and_chunk.add_child(**m)

        # Finally return the or_chunk
        return or_chunk
########NEW FILE########
__FILENAME__ = show_error
import sublime


def show_error(string):
    """
    Displays an error message with a standard "Package Control" header

    :param string:
        The error to display
    """

    sublime.error_message(u'Package Control\n\n%s' % string)

########NEW FILE########
__FILENAME__ = sys_path
import sys
import os

if os.name == 'nt':
    from ctypes import windll, create_unicode_buffer

import sublime


def add_to_path(path):
    # Python 2.x on Windows can't properly import from non-ASCII paths, so
    # this code added the DOC 8.3 version of the lib folder to the path in
    # case the user's username includes non-ASCII characters
    if os.name == 'nt':
        buf = create_unicode_buffer(512)
        if windll.kernel32.GetShortPathNameW(path, buf, len(buf)):
            path = buf.value

    if path not in sys.path:
        sys.path.append(path)


lib_folder = os.path.join(sublime.packages_path(), 'Package Control', 'lib')
add_to_path(os.path.join(lib_folder, 'all'))

if os.name == 'nt':
    add_to_path(os.path.join(lib_folder, 'windows'))

########NEW FILE########
__FILENAME__ = thread_progress
import sublime


class ThreadProgress():
    """
    Animates an indicator, [=   ], in the status area while a thread runs

    :param thread:
        The thread to track for activity

    :param message:
        The message to display next to the activity indicator

    :param success_message:
        The message to display once the thread is complete
    """

    def __init__(self, thread, message, success_message):
        self.thread = thread
        self.message = message
        self.success_message = success_message
        self.addend = 1
        self.size = 8
        sublime.set_timeout(lambda: self.run(0), 100)

    def run(self, i):
        if not self.thread.is_alive():
            if hasattr(self.thread, 'result') and not self.thread.result:
                sublime.status_message('')
                return
            sublime.status_message(self.success_message)
            return

        before = i % self.size
        after = (self.size - 1) - before

        sublime.status_message('%s [%s=%s]' % \
            (self.message, ' ' * before, ' ' * after))

        if not after:
            self.addend = -1
        if not before:
            self.addend = 1
        i += self.addend

        sublime.set_timeout(lambda: self.run(i), 100)

########NEW FILE########
__FILENAME__ = unicode
import os
import locale
import sys


# Sublime Text on OS X does not seem to report the correct encoding
# so we hard-code that to UTF-8
_encoding = 'utf-8' if sys.platform == 'darwin' else locale.getpreferredencoding()

_fallback_encodings = ['utf-8', 'cp1252']


def unicode_from_os(e):
    """
    This is needed as some exceptions coming from the OS are
    already encoded and so just calling unicode(e) will result
    in an UnicodeDecodeError as the string isn't in ascii form.

    :param e:
        The exception to get the value of

    :return:
        The unicode version of the exception message
    """

    if sys.version_info >= (3,):
        return str(e)

    try:
        if isinstance(e, Exception):
            e = e.message

        if isinstance(e, unicode):
            return e

        if isinstance(e, int):
            e = str(e)

        return unicode(e, _encoding)

    # If the "correct" encoding did not work, try some defaults, and then just
    # obliterate characters that we can't seen to decode properly
    except UnicodeDecodeError:
        for encoding in _fallback_encodings:
            try:
                return unicode(e, encoding, errors='strict')
            except:
                pass
    return unicode(e, errors='replace')

########NEW FILE########
__FILENAME__ = git_upgrader
import os

from ..cache import set_cache, get_cache
from ..show_error import show_error
from .vcs_upgrader import VcsUpgrader


class GitUpgrader(VcsUpgrader):
    """
    Allows upgrading a local git-repository-based package
    """

    cli_name = 'git'

    def retrieve_binary(self):
        """
        Returns the path to the git executable

        :return: The string path to the executable or False on error
        """

        name = 'git'
        if os.name == 'nt':
            name += '.exe'
        binary = self.find_binary(name)
        if binary and os.path.isdir(binary):
            full_path = os.path.join(binary, name)
            if os.path.exists(full_path):
                binary = full_path
        if not binary:
            show_error((u'Unable to find %s. Please set the git_binary setting by accessing the ' +
                u'Preferences > Package Settings > Package Control > Settings \u2013 User menu entry. ' +
                u'The Settings \u2013 Default entry can be used for reference, but changes to that will be ' +
                u'overwritten upon next upgrade.') % name)
            return False

        if os.name == 'nt':
            tortoise_plink = self.find_binary('TortoisePlink.exe')
            if tortoise_plink:
                os.environ.setdefault('GIT_SSH', tortoise_plink)
        return binary

    def get_working_copy_info(self):
        binary = self.retrieve_binary()
        if not binary:
            return False

        # Get the current branch name
        res = self.execute([binary, 'symbolic-ref', '-q', 'HEAD'], self.working_copy)
        branch = res.replace('refs/heads/', '')

        # Figure out the remote and the branch name on the remote
        remote = self.execute([binary, 'config', '--get', 'branch.%s.remote' % branch], self.working_copy)
        res = self.execute([binary, 'config', '--get', 'branch.%s.merge' % branch], self.working_copy)
        remote_branch = res.replace('refs/heads/', '')

        return {
            'branch': branch,
            'remote': remote,
            'remote_branch': remote_branch
        }

    def run(self):
        """
        Updates the repository with remote changes

        :return: False or error, or True on success
        """

        binary = self.retrieve_binary()
        if not binary:
            return False

        info = self.get_working_copy_info()

        args = [binary]
        args.extend(self.update_command)
        args.extend([info['remote'], info['remote_branch']])
        self.execute(args, self.working_copy)
        return True

    def incoming(self):
        """:return: bool if remote revisions are available"""

        cache_key = self.working_copy + '.incoming'
        incoming = get_cache(cache_key)
        if incoming != None:
            return incoming

        binary = self.retrieve_binary()
        if not binary:
            return False

        info = self.get_working_copy_info()

        res = self.execute([binary, 'fetch', info['remote']], self.working_copy)
        if res == False:
            return False

        args = [binary, 'log']
        args.append('..%s/%s' % (info['remote'], info['remote_branch']))
        output = self.execute(args, self.working_copy)
        incoming = len(output) > 0

        set_cache(cache_key, incoming, self.cache_length)
        return incoming

########NEW FILE########
__FILENAME__ = hg_upgrader
import os

from ..cache import set_cache, get_cache
from ..show_error import show_error
from .vcs_upgrader import VcsUpgrader


class HgUpgrader(VcsUpgrader):
    """
    Allows upgrading a local mercurial-repository-based package
    """

    cli_name = 'hg'

    def retrieve_binary(self):
        """
        Returns the path to the hg executable

        :return: The string path to the executable or False on error
        """

        name = 'hg'
        if os.name == 'nt':
            name += '.exe'
        binary = self.find_binary(name)
        if binary and os.path.isdir(binary):
            full_path = os.path.join(binary, name)
            if os.path.exists(full_path):
                binary = full_path
        if not binary:
            show_error((u'Unable to find %s. Please set the hg_binary setting by accessing the ' +
                u'Preferences > Package Settings > Package Control > Settings \u2013 User menu entry. ' +
                u'The Settings \u2013 Default entry can be used for reference, but changes to that will be ' +
                u'overwritten upon next upgrade.') % name)
            return False
        return binary

    def run(self):
        """
        Updates the repository with remote changes

        :return: False or error, or True on success
        """

        binary = self.retrieve_binary()
        if not binary:
            return False
        args = [binary]
        args.extend(self.update_command)
        args.append('default')
        self.execute(args, self.working_copy)
        return True

    def incoming(self):
        """:return: bool if remote revisions are available"""

        cache_key = self.working_copy + '.incoming'
        incoming = get_cache(cache_key)
        if incoming != None:
            return incoming

        binary = self.retrieve_binary()
        if not binary:
            return False

        args = [binary, 'in', '-q', 'default']
        output = self.execute(args, self.working_copy)
        if output == False:
            return False

        incoming = len(output) > 0

        set_cache(cache_key, incoming, self.cache_length)
        return incoming

########NEW FILE########
__FILENAME__ = vcs_upgrader
from ..cmd import create_cmd, Cli


class VcsUpgrader(Cli):
    """
    Base class for updating packages that are a version control repository on local disk

    :param vcs_binary:
        The full filesystem path to the executable for the version control
        system. May be set to None to allow the code to try and find it.

    :param update_command:
        The command to pass to the version control executable to update the
        repository.

    :param working_copy:
        The local path to the working copy/package directory

    :param cache_length:
        The lenth of time to cache if incoming changesets are available
    """

    def __init__(self, vcs_binary, update_command, working_copy, cache_length, debug):
        self.update_command = update_command
        self.working_copy = working_copy
        self.cache_length = cache_length
        super(VcsUpgrader, self).__init__(vcs_binary, debug)

########NEW FILE########
__FILENAME__ = versions
import re

from .semver import SemVer
from .console_write import console_write


def semver_compat(v):
    if isinstance(v, SemVer):
        return str(v)

    # Allowing passing in a dict containing info about a package
    if isinstance(v, dict):
        if 'version' not in v:
            return '0'
        v = v['version']

    # Trim v off of the front
    v = re.sub('^v', '', v)

    # We prepend 0 to all date-based version numbers so that developers
    # may switch to explicit versioning from GitHub/BitBucket
    # versioning based on commit dates.
    #
    # When translating dates into semver, the way to get each date
    # segment into the version is to treat the year and month as
    # minor and patch, and then the rest as a numeric build version
    # with four different parts. The result looks like:
    # 0.2012.11+10.31.23.59
    date_match = re.match('(\d{4})\.(\d{2})\.(\d{2})\.(\d{2})\.(\d{2})\.(\d{2})$', v)
    if date_match:
        v = '0.%s.%s+%s.%s.%s.%s' % date_match.groups()

    # This handles version that were valid pre-semver with 4+ dotted
    # groups, such as 1.6.9.0
    four_plus_match = re.match('(\d+\.\d+\.\d+)[T\.](\d+(\.\d+)*)$', v)
    if four_plus_match:
        v = '%s+%s' % (four_plus_match.group(1), four_plus_match.group(2))

    # Semver must have major, minor, patch
    elif re.match('^\d+$', v):
        v += '.0.0'
    elif re.match('^\d+\.\d+$', v):
        v += '.0'
    return v


def version_comparable(string):
    return SemVer(semver_compat(string))


def version_exclude_prerelease(versions):
    output = []
    for version in versions:
        if SemVer(semver_compat(version)).prerelease != None:
            continue
        output.append(version)
    return output


def version_filter(versions, allow_prerelease=False):
    output = []
    for version in versions:
        no_v_version = re.sub('^v', '', version)
        if not SemVer.valid(no_v_version):
            continue
        if not allow_prerelease and SemVer(no_v_version).prerelease != None:
            continue
        output.append(version)
    return output


def _version_sort_key(item):
    return SemVer(semver_compat(item))


def version_sort(sortable, **kwargs):
    try:
        return sorted(sortable, key=_version_sort_key, **kwargs)
    except (ValueError) as e:
        console_write(u"Error sorting versions - %s" % e, True)
        return []

########NEW FILE########
