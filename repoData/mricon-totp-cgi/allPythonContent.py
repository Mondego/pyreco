__FILENAME__ = command
#!/usr/bin/python -tt
__author__ = 'mricon'

import logging
import os
import sys
import anyjson

import totpcgi
import totpcgi.backends
import totpcgi.backends.file
import totpcgi.utils

import datetime
import dateutil
import dateutil.parser
import dateutil.tz

from string import Template

import syslog

#--------------- CHANGE ME TO REFLECT YOUR ENVIRONMENT -------------------

# You need to change this to reflect your environment
GL_2FA_COMMAND = 'ssh git@example.com 2fa'
HELP_DOC_LINK = 'https://example.com'

# Set to False to disallow yubikey (HOTP) enrolment
ALLOW_YUBIKEY = True

# This will allow anyone to use "override" as the 2-factor token
# Obviously, this should only be used during initial debugging
# and testing and then set to false.
ALLOW_BYPASS_OVERRIDE = False

# In the TOTP case, the window size is the time drift between the user's device
# and the server. A window size of 17 means 17*10 seconds, or in other words,
# we'll accept any tokencodes that were valid within 170 seconds before now, and
# 170 seconds after now.
# In the HOTP case, discrepancy between the counter on the device and the counter
# on the server is virtually guaranteed (accidental button presses on the yubikey,
# authentication failures, etc), so the window size indicates how many tokens we will
# try in addition to the current one. The setting of 30 is sane and is not likely to
# lock someone out.
TOTP_WINDOW_SIZE = 17
HOTP_WINDOW_SIZE = 30

# First value is the number of times. Second value is the number of seconds.
# So, "3, 30" means "3 falures within 30 seconds"
RATE_LIMIT = (3, 30)

# Google Authenticator and other devices default to key length of 80 bits, while
# for yubikeys the length must be 160 bits. I suggest you leave these as-is.
TOTP_KEY_LENGTH = 80
HOTP_KEY_LENGTH = 160

# This identifies the token in the user's TOTP app
TOTP_USER_MASK = '$username@example.com'

# GeoIP-city database location.
# This is only currently used as a sort of a reminder to the users, so when they list
# their current validations using list-val, it can help them figure out where they
# previously authorized from.
# You can download the City database from
# http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.xz and put
# into GL_ADMIN_BASE/2fa/ (uncompress first). If the code doesn't find it, it'll
# try to use the basic GeoIP country information. If that fails, it'll just
# quitely omit GeoIP data.
GEOIP_CITY_DB = os.path.join(os.environ['GL_ADMIN_BASE'], '2fa/GeoLiteCity.dat')

# Identify ourselves in syslog as "gl-2fa"
syslog.openlog('gl-2fa', syslog.LOG_PID, syslog.LOG_AUTH)

#-------------------------------------------------------------------------

# default basic logger. We override it later.
logger = logging.getLogger(__name__)


def print_help_link():
    print('')
    print('If you need more help, please see the following link:')
    print('    %s' % HELP_DOC_LINK)
    print('')


def get_geoip_crc(ipaddr):
    import GeoIP

    if os.path.exists(GEOIP_CITY_DB):
        logger.debug('Opening geoip db in %s' % GEOIP_CITY_DB)
        gi = GeoIP.open(GEOIP_CITY_DB, GeoIP.GEOIP_STANDARD)
    else:
        logger.debug('%s does not exist, using basic geoip db' % GEOIP_CITY_DB)
        gi = GeoIP.new(GeoIP.GEOIP_MEMORY_CACHE)

    ginfo = gi.record_by_addr(ipaddr)

    if ginfo is not None:
        city = region_name = country_code = 'Unknown'

        if ginfo['city'] is not None:
            city = unicode(ginfo['city'], 'iso-8859-1')
        if ginfo['region_name'] is not None:
            region_name = unicode(ginfo['region_name'], 'iso-8859-1')
        if ginfo['country_code'] is not None:
            country_code = unicode(ginfo['country_code'], 'iso-8859-1')

        crc = u'%s, %s, %s' % (city, region_name, country_code)

    else:
        # try just the country code, then
        crc = gi.country_code_by_addr(ipaddr)
        if not crc:
            return None
        crc = unicode(crc, 'iso-8859-1')

    return crc


def load_authorized_ips():
    # The authorized ips file has the following structure:
    # {
    #   'IP_ADDR': {
    #       'added': RFC_8601_DATETIME,
    #       'expires': RFC_8601_DATETIME,
    #       'whois': whois information about the IP at the time of recording,
    #       'geoip': geoip information about the IP at the time of recording,
    #  }
    #
    # It is stored in GL_ADMIN_BASE/2fa/validations/GL_USER.js

    user = os.environ['GL_USER']
    val_dir = os.path.join(os.environ['GL_ADMIN_BASE'], '2fa/validations')
    if not os.path.exists(val_dir):
        os.makedirs(val_dir, 0700)
        logger.debug('Created val_dir in %s' % val_dir)

    valfile = os.path.join(val_dir, '%s.js' % user)

    logger.debug('Loading authorized ips from %s' % valfile)
    valdata = {}
    if os.access(valfile, os.R_OK):
        try:
            fh = open(valfile, 'r')
            jdata = fh.read()
            fh.close()
            valdata = anyjson.deserialize(jdata)
        except:
            logger.critical('Validations file exists, but could not be parsed!')
            logger.critical('All previous validations have been lost, starting fresh.')
    return valdata


def store_authorized_ips(valdata):
    user = os.environ['GL_USER']
    val_dir = os.path.join(os.environ['GL_ADMIN_BASE'], '2fa/validations')
    valfile = os.path.join(val_dir, '%s.js' % user)
    jdata = anyjson.serialize(valdata)
    fh = open(valfile, 'w')
    fh.write(jdata)
    fh.close()
    logger.debug('Wrote new validations file in %s' % valfile)


def store_validation(remote_ip, hours):
    valdata = load_authorized_ips()

    utc = dateutil.tz.tzutc()
    now_time = datetime.datetime.now(utc).replace(microsecond=0)
    expires = now_time + datetime.timedelta(hours=hours)

    logger.info('Adding IP address %s until %s' % (remote_ip, expires.strftime('%c %Z')))
    valdata[remote_ip] = {
        'added': now_time.isoformat(sep=' '),
        'expires': expires.isoformat(sep=' '),
    }

    # Try to lookup whois info if cymruwhois is available
    try:
        import cymruwhois
        cym = cymruwhois.Client()
        res = cym.lookup(remote_ip)
        if res.owner and res.cc:
            whois = "%s/%s\n" % (res.owner, res.cc)
            valdata[remote_ip]['whois'] = whois
            logger.info('Whois information for %s: %s' % (remote_ip, whois))
    except:
        pass

    try:
        geoip = get_geoip_crc(remote_ip)
        if geoip is not None:
            valdata[remote_ip]['geoip'] = geoip
            logger.info('GeoIP information for %s: %s' % (remote_ip, geoip))
    except:
        pass

    store_authorized_ips(valdata)


def generate_user_token(backends, mode):
    if mode == 'totp':
        gaus = totpcgi.utils.generate_secret(
            RATE_LIMIT, TOTP_WINDOW_SIZE, 5, bs=TOTP_KEY_LENGTH)

    else:
        gaus = totpcgi.utils.generate_secret(
            RATE_LIMIT, HOTP_WINDOW_SIZE, 5, bs=HOTP_KEY_LENGTH)
        gaus.set_hotp(0)

    user = os.environ['GL_USER']
    backends.secret_backend.save_user_secret(user, gaus, None)
    # purge all old state, as it's now obsolete
    backends.state_backend.delete_user_state(user)

    logger.info('New token generated for user %s' % user)
    remote_ip = os.environ['SSH_CONNECTION'].split()[0]
    syslog.syslog(
        syslog.LOG_NOTICE,
        'Enrolled: user=%s, host=%s, mode=%s' % (user, remote_ip, mode)
    )

    if mode == 'totp':
        # generate provisioning URI
        tpt = Template(TOTP_USER_MASK)
        totp_user = tpt.safe_substitute(username=user)
        qr_uri = gaus.otp.provisioning_uri(totp_user)
        import urllib
        print('')
        print('Please make sure "qrencode" is installed.')
        print('Run the following commands to display your QR code:')
        print('    unset HISTFILE')
        print('    qrencode -tANSI -m1 -o- "%s"' % qr_uri)
        print('')
        print('If that does not work or if you do not have access to')
        print('qrencode or a similar QR encoding tool, then you may')
        print('open an INCOGNITO/PRIVATE MODE window in your browser')
        print('and paste the following URL:')
        print(
            'https://www.google.com/chart?chs=200x200&chld=M|0&cht=qr&chl=%s' %
            urllib.quote_plus(qr_uri))
        print('')
        print('Scan the resulting QR code with your TOTP app, such as')
        print('FreeOTP (recommended), Google Authenticator, Authy, or others.')

    else:
        import binascii
        import base64
        keyhex = binascii.hexlify(base64.b32decode(gaus.otp.secret))
        print('')
        print('Please make sure "ykpersonalize" has been installed.')
        print('Insert your yubikey and, as root, run the following command')
        print('to provision the secret into slot 1 (use -2 for slot 2):')
        print('    unset HISTFILE')
        print('    ykpersonalize -1 -ooath-hotp -oappend-cr -a%s' % keyhex)
        print('')

    if gaus.scratch_tokens:
        print('Please write down/print the following 8-digit scratch tokens.')
        print('If you lose your device or temporarily have no access to it, you')
        print('will be able to use these tokens for one-time bypass.')
        print('')
        print('Scratch tokens:')
        print('\n'.join(gaus.scratch_tokens))

    print

    print('Now run the following command to verify that all went well')

    if mode == 'totp':
        print('    %s val [token]' % GL_2FA_COMMAND)
    else:
        print('    %s val [yubkey button press]' % GL_2FA_COMMAND)

    print_help_link()


def enroll(backends):
    proceed = False
    mode = 'totp'

    if ALLOW_YUBIKEY and len(sys.argv) <= 2:
        logger.critical('Enrolment mode not specified.')
    elif ALLOW_YUBIKEY:
        if sys.argv[2] not in ('totp', 'yubikey'):
            logger.critical('%s is not a valid enrollment mode' % sys.argv[2])
        else:
            mode = sys.argv[2]
            proceed = True
    else:
        proceed = True

    if not proceed:
        print('Please specify whether you are enrolling a yubikey or a TOTP phone app')
        print('Examples:')
        print('    %s enroll yubikey' % GL_2FA_COMMAND)
        print('    %s enroll totp' % GL_2FA_COMMAND)
        print_help_link()
        sys.exit(1)

    logger.info('%s enrollment mode selected' % mode)

    user = os.environ['GL_USER']

    try:
        try:
            backends.secret_backend.get_user_secret(user)
        except totpcgi.UserSecretError:
            pass

        logger.critical('User %s already enrolled' % user)
        print('Looks like you are already enrolled. If you want to re-issue your token,')
        print('you will first need to remove your currently active one.')
        print('')
        print('If you have access to your current device or 8-digit scratch codes, run:')
        print('    unenroll [token]')
        print_help_link()
        sys.exit(1)

    except totpcgi.UserNotFound:
        pass

    generate_user_token(backends, mode)


def unenroll(backends):
    token = sys.argv[2]
    user = os.environ['GL_USER']
    remote_ip = os.environ['SSH_CONNECTION'].split()[0]

    ga = totpcgi.GoogleAuthenticator(backends)

    try:
        status = ga.verify_user_token(user, token)
    except Exception, ex:
        if ALLOW_BYPASS_OVERRIDE and token == 'override':
            status = "%s uses 'override'. It's super effective!" % user
            syslog.syslog(
                syslog.LOG_NOTICE, 'OVERRIDE USED: user=%s, host=%s'
            )
        else:
            logger.critical('Failed to validate token.')
            print('If using a phone app, please wait for token to change before trying again.')
            syslog.syslog(
                syslog.LOG_NOTICE,
                'Failure: user=%s, host=%s, message=%s' % (user, remote_ip, str(ex))
            )
            print_help_link()
            sys.exit(1)

    syslog.syslog(
        syslog.LOG_NOTICE,
        'Success: user=%s, host=%s, message=%s' % (user, remote_ip, status)
    )
    logger.info(status)

    # Okay, deleting
    logger.info('Removing the secrets file.')
    backends.secret_backend.delete_user_secret(user)
    # purge all old state, as it's now obsolete
    logger.info('Cleaning up state files.')
    backends.state_backend.delete_user_state(user)
    logger.info('Expiring all validations.')
    inval(expire_all=True)

    logger.info('You have been successfully unenrolled.')


def val(backends, hours=24):
    if len(sys.argv) <= 2:
        logger.critical('Missing tokencode.')
        print('You need to pass the token code as the last argument. E.g.:')
        print('    %s val [token]' % GL_2FA_COMMAND)
        print_help_link()
        sys.exit(1)

    token = sys.argv[2]
    user = os.environ['GL_USER']
    remote_ip = os.environ['SSH_CONNECTION'].split()[0]

    ga = totpcgi.GoogleAuthenticator(backends)

    try:
        status = ga.verify_user_token(user, token)
    except Exception, ex:
        if ALLOW_BYPASS_OVERRIDE and token == 'override':
            status = "%s uses 'override'. It's super effective!" % user
            syslog.syslog(
                syslog.LOG_NOTICE, 'OVERRIDE USED: user=%s, host=%s'
            )
        else:
            logger.critical('Failed to validate token.')
            print('If using a phone app, please wait for token to change before trying again.')
            syslog.syslog(
                syslog.LOG_NOTICE,
                'Failure: user=%s, host=%s, message=%s' % (user, remote_ip, str(ex))
            )
            print_help_link()
            sys.exit(1)

    syslog.syslog(
        syslog.LOG_NOTICE,
        'Success: user=%s, host=%s, message=%s' % (user, remote_ip, status)
    )
    logger.info(status)

    store_validation(remote_ip, hours)


def list_val(active_only=True):
    valdata = load_authorized_ips()
    if active_only:
        utc = dateutil.tz.tzutc()
        now_time = datetime.datetime.now(utc)

        for authorized_ip in valdata.keys():
            exp_time = dateutil.parser.parse(valdata[authorized_ip]['expires'])

            if now_time > exp_time:
                del valdata[authorized_ip]

    if valdata:
        # anyjson doesn't let us indent
        import json
        print(json.dumps(valdata, indent=4))
        if active_only:
            print('Listed non-expired entries only. Run "list-val all" to list all.')


def inval(expire_all=False):
    valdata = load_authorized_ips()
    utc = dateutil.tz.tzutc()
    now_time = datetime.datetime.now(utc).replace(microsecond=0)
    new_exp_time = now_time - datetime.timedelta(seconds=1)

    to_expire = []

    if sys.argv[2] == 'myip':
        inval_ip = os.environ['SSH_CONNECTION'].split()[0]
    elif sys.argv[2] == 'all':
        expire_all = True
    else:
        inval_ip = sys.argv[2]

    if expire_all:
        for authorized_ip in valdata:
            exp_time = dateutil.parser.parse(valdata[authorized_ip]['expires'])

            if exp_time > now_time:
                to_expire.append(authorized_ip)

    else:
        if inval_ip not in valdata.keys():
            logger.info('Did not find %s in the list of authorized IPs.' % inval_ip)
        else:
            to_expire.append(inval_ip)

    if to_expire:
        for inval_ip in to_expire:
            exp_time = dateutil.parser.parse(valdata[inval_ip]['expires'])

            if exp_time > now_time:
                logger.info('Force-expired %s.' % inval_ip)
                valdata[inval_ip]['expires'] = new_exp_time.isoformat(sep=' ')
            else:
                logger.info('%s was already expired.' % inval_ip)

        store_authorized_ips(valdata)

    list_val(active_only=True)


def main():
    global logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "[%s] " % os.environ['GL_USER'] + "%(asctime)s - %(levelname)s - %(message)s")

    # We log alongside GL_LOGFILE and follow Gitolite's log structure
    (logdir, logname) = os.path.split(os.environ['GL_LOGFILE'])
    logfile = os.path.join(logdir, '2fa-command-%s' % logname)
    ch = logging.FileHandler(logfile)
    ch.setFormatter(formatter)

    if '2FA_LOG_DEBUG' in os.environ.keys():
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    ch.setLevel(loglevel)
    logger.addHandler(ch)

    # Only CRITICAL goes to console
    ch = logging.StreamHandler()

    formatter = logging.Formatter('%(message)s')
    ch.setFormatter(formatter)
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    backends = totpcgi.backends.Backends()

    # We only use file backends
    secrets_dir = os.path.join(os.environ['GL_ADMIN_BASE'], '2fa/secrets')
    state_dir = os.path.join(os.environ['GL_ADMIN_BASE'], '2fa/state')
    logger.debug('secrets_dir=%s' % secrets_dir)
    logger.debug('state_dir=%s' % state_dir)

    # Create those two dirs if they don't exist
    if not os.path.exists(secrets_dir):
        os.makedirs(secrets_dir, 0700)
        logger.info('Created %s' % secrets_dir)
    if not os.path.exists(state_dir):
        os.makedirs(state_dir, 0700)
        logger.info('Created %s' % state_dir)

    backends.secret_backend = totpcgi.backends.file.GASecretBackend(secrets_dir)
    backends.state_backend = totpcgi.backends.file.GAStateBackend(state_dir)

    if len(sys.argv) < 2:
        logger.critical('Incomplete command specified.')
        print_help_link()
        sys.exit(1)
    command = sys.argv[1]

    if command == 'enroll':
        enroll(backends)
    elif command == 'unenroll':
        if len(sys.argv) <= 2:
            logger.critical('Missing authorization token.')
            print('Please use your current token code to unenroll.')
            print('You may also use a one-time 8-digit code for the same purpose.')
            print('E.g.: %s unenroll [token]' % GL_2FA_COMMAND)
            sys.exit(1)
        unenroll(backends)

    elif command == 'val':
        val(backends)
    elif command == 'val-for-days':
        if len(sys.argv) <= 2:
            logger.critical('Missing number of days to keep the validation.')
            sys.exit(1)
        try:
            days = int(sys.argv[2])
        except ValueError:
            logger.critical('The number of days should be an integer.')
            sys.exit(1)

        if days > 30 or days < 1:
            logger.critical('The number of days must be a number between 1 and 30.')
            sys.exit(1)

        hours = days * 24

        # shift token into 2nd position
        del sys.argv[2]
        val(backends, hours=hours)
    elif command == 'list-val':
        if len(sys.argv) > 2 and sys.argv[2] == 'all':
            list_val(active_only=False)
        else:
            list_val(active_only=True)
    elif command == 'inval':
        if len(sys.argv) <= 2:
            logger.critical('You need to provide an IP address to invalidate.')
            logger.critical('You may use "myip" to invalidate your current IP address.')
            logger.critical('You may also use "all" to invalidate ALL currently active IP addresses.')
            sys.exit(1)
        inval()


if __name__ == '__main__':
    if 'GL_USER' not in os.environ:
        sys.stderr.write('Please run me from gitolite hooks')
        sys.exit(1)

    if 'SSH_CONNECTION' not in os.environ:
        sys.stderr.write('This only works when accessed over SSH')
        sys.exit(1)

    main()

########NEW FILE########
__FILENAME__ = vref
#!/usr/bin/python -tt
__author__ = 'mricon'

import logging
import os
import sys
import anyjson

#--------------- CHANGE ME TO REFLECT YOUR ENVIRONMENT -------------------

# What should people run to invoke the 2fa command?
GL_2FA_COMMAND = 'ssh git@example.com 2fa'
# Where does helpful documentation live?
HELP_DOC_LINK = 'https://example.com'

#-------------------------------------------------------------------------

# default basic logger. We override it later.
logger = logging.getLogger(__name__)


def gl_fail_exit():
    sys.stdout.write('%s: 2-factor verification failed\n' % sys.argv[7])
    sys.exit(1)


def print_help_link():
    print
    print('If you need more help, please see the following link:')
    print('    %s' % HELP_DOC_LINK)
    print


def how_to_enroll():
    print('You will need to enroll with 2-factor authentication')
    print('before you can push to this repository.')
    print_help_link()


def how_to_validate():
    print('Please get your 2-factor authentication token and run:')
    print('    %s val [token]' % GL_2FA_COMMAND)
    print_help_link()


def load_authorized_ips():
    # The authorized ips file has the following structure:
    # {
    #   'IP_ADDR': {
    #       'added': RFC_8601_DATETIME,
    #       'expires': RFC_8601_DATETIME,
    #       'whois': whois information about the IP at the time of recording,
    #       'geoip': geoip information about the IP at the time of recording,
    #  }
    #
    # It is stored in GL_ADMIN_BASE/2fa/validations/GL_USER.js
    valfile = os.path.join(
        os.environ['GL_ADMIN_BASE'], '2fa/validations', '%s.js' % os.environ['GL_USER'])

    logger.debug('Loading authorized ips from %s' % valfile)
    valdata = {}
    if os.access(valfile, os.R_OK):
        try:
            fh = open(valfile, 'r')
            jdata = fh.read()
            fh.close()
            valdata = anyjson.deserialize(jdata)
        except:
            logger.critical('Validations file exists, but could not be parsed!')
            logger.critical('Please rerun "2fa val" to create a new file!')
            gl_fail_exit()

    return valdata


def vref_verify():
    global logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "[%s] " % os.environ['GL_USER'] + "%(asctime)s - %(levelname)s - %(message)s")

    # We log alongside GL_LOGFILE and follow Gitolite's log structure
    (logdir, logname) = os.path.split(os.environ['GL_LOGFILE'])
    logfile = os.path.join(logdir, '2fa-vref-%s' % logname)
    ch = logging.FileHandler(logfile)
    ch.setFormatter(formatter)

    if '2FA_LOG_DEBUG' in os.environ.keys():
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    ch.setLevel(loglevel)
    logger.addHandler(ch)

    # only critical notices to the console
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(message)s')
    ch.setFormatter(formatter)
    ch.setLevel(logging.CRITICAL)
    logger.addHandler(ch)

    # Check if this person has a token issued
    # The token files are stored in GL_ADMIN_BASE/2fa/secrets/GL_USER.totp
    secret_file = os.path.join(
        os.environ['GL_ADMIN_BASE'], '2fa/secrets',
        '%s.totp' % os.environ['GL_USER'])

    if not os.path.exists(secret_file):
        # See if we were called as "VREF/2fa/optin"
        if sys.argv[7][-6:] == '/optin':
            logger.info('User not enrolled with 2fa, but /optin is set. Allowing the push.')
            sys.exit(0)
        else:
            logger.critical('User not enrolled with 2-factor authentication.')
            how_to_enroll()
            gl_fail_exit()

    # SSH_CONNECTION format is: "REMOTE_IP REMOTE_PORT LOCAL_IP LOCAL_PORT"
    # We only care about the first entry
    chunks = os.environ['SSH_CONNECTION'].split()

    remote_ip = chunks[0]
    authorized_ips = load_authorized_ips()

    logger.info('Checking if %s has been previously validated' % remote_ip)

    # First compare as strings, as this is much faster
    matching = None
    if remote_ip not in authorized_ips.keys():
        import netaddr
        # We can't rely on strings, as ipv6 has more than one way to represent the same IP address, e.g.:
        # 2001:4f8:1:10:0:1991:8:25 and 2001:4f8:1:10::1991:8:25
        for authorized_ip in authorized_ips.keys():
            if netaddr.IPAddress(remote_ip) == netaddr.IPAddress(authorized_ip):
                # Found it
                matching = authorized_ip
                break
    else:
        matching = remote_ip

    if matching is None:
        logger.critical('IP address "%s" has not been validated.' % remote_ip)
        how_to_validate()
        gl_fail_exit()

    # Okay, but is it still valid?
    expires = authorized_ips[matching]['expires']
    logger.debug('Validation for %s expires on %s' % (matching, expires))
    import datetime
    import dateutil
    import dateutil.parser
    import dateutil.tz

    exp_time = dateutil.parser.parse(expires)
    utc = dateutil.tz.tzutc()
    now_time = datetime.datetime.now(utc)
    logger.debug('exp_time: %s' % exp_time)
    logger.debug('now_time: %s' % now_time)

    if now_time > exp_time:
        logger.critical('Validation for IP address %s has expired.' % matching)
        how_to_validate()
        gl_fail_exit()

    logger.info('Successfully validated remote IP %s' % matching)


if __name__ == '__main__':
    if 'GL_USER' not in os.environ:
        sys.stderr.write('Please run me from gitolite hooks')
        sys.exit(1)

    if 'SSH_CONNECTION' not in os.environ:
        sys.stderr.write('This only works when accessed over SSH')
        sys.exit(1)

    vref_verify()
    sys.exit(0)
########NEW FILE########
__FILENAME__ = totpprov
#!/usr/bin/python -tt
##
# Copyright (C) 2012 by Konstantin Ryabitsev and contributors
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#

import sys

from optparse import OptionParser
import ConfigParser

import totpcgi
import totpcgi.backends
import totpcgi.utils

import getpass

import syslog
syslog.openlog('totpprov', syslog.LOG_PID, syslog.LOG_AUTH)

from string import Template


def ays():
    inp = raw_input('Are you sure [y/N]: ')
    if inp != 'y':
        print 'Exiting on user command'
        sys.exit(0)


def ask_for_new_pincode():
    pincode = None
    while pincode is None:
        pincode = getpass.getpass('Pincode: ')
        if pincode != getpass.getpass('Verify: '):
            print 'Pincodes did not match'
            pincode = None

    return pincode


def ask_for_user_pincode(backends, user):
    pincode = None
    while pincode is None:
        pincode = getpass.getpass('Pincode for user %s: ' % user)
        try:
            backends.pincode_backend.verify_user_pincode(user, pincode)
        except totpcgi.UserPincodeError:
            print 'Pincode failed to verify.'
            pincode = None

    return pincode


def generate_secret(config):
    encrypt_secret = config.getboolean('secret', 'encrypt_secret')
    window_size = config.getint('secret', 'window_size')
    rate_limit = config.get('secret', 'rate_limit')
    try:
        secret_bits = config.getint('secret', 'bits')
    except:
        secret_bits = 80

    # scratch tokens don't make any sense with encrypted secret
    if not encrypt_secret:
        scratch_tokens_n = config.getint('secret', 'scratch_tokens_n')
    else:
        scratch_tokens_n = 0

    (times, secs) = rate_limit.split(',')
    rate_limit = (int(times), int(secs))

    gaus = totpcgi.utils.generate_secret(rate_limit, window_size,
        scratch_tokens_n, bs=secret_bits)

    return gaus


def delete_user(backends, config, args):
    backends.secret_backend.delete_user_secret(args[1])
    backends.pincode_backend.delete_user_hashcode(args[1])
    backends.state_backend.delete_user_state(args[1])

    print 'User %s deleted' % args[1]


def delete_user_state(backends, config, args):
    backends.state_backend.delete_user_state(args[1])
    print 'State data for user %s deleted' % args[1]


def delete_user_pincode(backends, config, args):
    backends.pincode_backend.delete_user_hashcode(args[1])
    print 'Pincode for user %s deleted' % args[1]


def delete_user_secret(backends, config, args):
    backends.secret_backend.delete_user_secret(args[1])
    print 'Google authenticator token for user %s deleted' % args[1]


def set_user_pincode(backends, config, args):
    usehash = config.get('pincode', 'usehash')
    makedb  = config.getboolean('pincode', 'makedb')

    pincode  = ask_for_new_pincode()
    hashcode = totpcgi.utils.hash_pincode(pincode, usehash)

    backends.pincode_backend.save_user_hashcode(args[1], hashcode, makedb)
    print 'Pincode for user %s set, verifying.' % args[1]

    backends.pincode_backend.verify_user_pincode(args[1], pincode)
    print 'Verified successfully.'

    return pincode


def encrypt_user_token(backends, config, args):
    user = args[1]
    # see if it's already encrypted
    try:
        gaus = backends.secret_backend.get_user_secret(user)
    except totpcgi.UserNotFound, ex:
        print 'Error: No existing tokens found for user %s' % user
        sys.exit(1)
    except totpcgi.UserSecretError, ex:
        print 'Error: the token for user %s is already encrypted' % user
        sys.exit(1)

    pincode = ask_for_user_pincode(backends, user)

    backends.secret_backend.save_user_secret(user, gaus, pincode)
    print 'Successfully encrypted user secret'


def decrypt_user_token(backends, config, args):
    user = args[1]
    pincode = getpass.getpass('Pincode for user %s: ' % user)

    # Try getting the user secret
    try:
        gaus = backends.secret_backend.get_user_secret(user, pincode)
    except totpcgi.UserNotFound, ex:
        print 'Error: No existing tokens found for user %s' % user
        sys.exit(1)
    except totpcgi.UserSecretError, ex:
        print 'Error: Could not decrypt the secret for user %s' % user
        sys.exit(1)

    backends.secret_backend.save_user_secret(user, gaus, None)
    print 'Successfully decrypted user secret'


def generate_user_token(backends, config, args, pincode=None):
    user = args[1]
    
    try:
        try:
            gaus = backends.secret_backend.get_user_secret(user)
        except totpcgi.UserSecretError:
            pass

        print 'Existing token found for user %s. Delete it first.' % user
        sys.exit(1)

    except totpcgi.UserNotFound, ex:
        pass

    gaus = generate_secret(config)

    if config.hotp:
        gaus.set_hotp(0)

    # if we don't need to encrypt the secret, set pincode to None
    encrypt_secret = config.getboolean('secret', 'encrypt_secret')
    if encrypt_secret:
        if pincode is None:
            pincode = ask_for_user_pincode(backends, user)

    backends.secret_backend.save_user_secret(user, gaus, pincode)

    # purge all old state, as it's now obsolete
    backends.state_backend.delete_user_state(user)

    print 'New token generated for user %s' % user
    # generate provisioning URI
    tpt = Template(config.get('secret', 'totp_user_mask'))
    totp_user = tpt.safe_substitute(username=user)
    qr_uri = gaus.otp.provisioning_uri(totp_user)

    print 'OTP URI: %s' % qr_uri
    if gaus.is_hotp():
        import binascii
        import base64
        keyhex = binascii.hexlify(base64.b32decode(gaus.otp.secret))
        print 'YK commands:'
        print '(slot 1): ykpersonalize -1 -ooath-hotp -oappend-cr -a%s' % keyhex
        print '(slot 2): ykpersonalize -2 -ooath-hotp -oappend-cr -a%s' % keyhex

    if gaus.scratch_tokens:
        print 'Scratch tokens:'
        print '\n'.join(gaus.scratch_tokens)


def provision_user(backends, config, args):
    user = args[1]

    try:
        try:
            gaus = backends.secret_backend.get_user_secret(user)
        except totpcgi.UserSecretError:
            pass

        print 'Existing data found for user %s. Delete it first.' % user
        sys.exit(1)

    except totpcgi.UserNotFound:
        pass

    pincode = set_user_pincode(backends, config, args)
    encrypt_secret = config.getboolean('secret', 'encrypt_secret')
    if not encrypt_secret:
        pincode = None

    generate_user_token(backends, config, args, pincode)

if __name__ == '__main__':
    usage = '''usage: %prog [-c provisioning.conf] command username
    Use this tool to provision totpcgi users and tokens. See manpage
    for more info on commands.
    '''

    parser = OptionParser(usage=usage, version='0.1')
    parser.add_option('-c', '--config', dest='config_file', 
                      default='/etc/totpcgi/provisioning.conf',
                      help='Path to provisioning.conf (%default)')
    parser.add_option('', '--hotp', dest='hotp', action='store_true',
                      default=False,
                      help='Generate HOTP tokens (default=%default)')

    (opts, args) = parser.parse_args()

    config = ConfigParser.RawConfigParser()
    config.read(opts.config_file)

    # it's dirty, but stick hotp switch into the config object
    config.hotp = opts.hotp

    backends = totpcgi.backends.Backends()

    try:
        backends.load_from_config(config)
    except totpcgi.backends.BackendNotSupported, ex:
        syslog.syslog(syslog.LOG_CRIT, 
                'Backend engine not supported: %s' % ex)
        sys.exit(1)
    
    if not args:
        parser.error('Must specify command')

    command = args[0]

    if command == 'delete-user':
        print 'Deleting user %s' % args[1]
        ays()
        delete_user(backends, config, args)

    elif command == 'delete-user-state':
        print 'Deleting state data for user %s' % args[1]
        ays()
        delete_user_state(backends, config, args)

    elif command == 'delete-user-pincode':
        print 'Deleting pincode for user %s' % args[1]
        ays()
        delete_user_pincode(backends, config, args)

    elif command == 'delete-user-token':
        print 'Deleting token data for user %s' % args[1]
        ays()
        delete_user_secret(backends, config, args)

    elif command == 'set-user-pincode':
        print 'Setting pincode for user %s' % args[1]
        ays()
        set_user_pincode(backends, config, args)

    elif command == 'encrypt-user-token':
        print 'Encrypting user token for %s' % args[1]
        ays()
        encrypt_user_token(backends, config, args)

    elif command == 'decrypt-user-token':
        print 'Decrypting user token for %s' % args[1]
        ays()
        decrypt_user_token(backends, config, args)

    elif command == 'generate-user-token':
        print 'Generating new token for user %s' % args[1]
        ays()
        generate_user_token(backends, config, args)

    elif command == 'provision-user':
        print 'Provisioning new TOTP user %s' % args[1]
        ays()
        provision_user(backends, config, args)

    else:
        parser.error('Unknown command: %s' % command)


########NEW FILE########
__FILENAME__ = test
#!/usr/bin/python -tt
##
# Copyright (C) 2012 by Konstantin Ryabitsev and contributors
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
import unittest

import pyotp
import time
import logging

import totpcgi
import totpcgi.backends

import sys
import os
import subprocess

import bcrypt
import crypt

import anydbm

secrets_dir = 'test/'
pincode_file = 'test/pincodes'
state_dir = 'test/state'

pg_connect_string = ''
ldap_dn = ''
ldap_url = ''
ldap_cacert = ''
mysql_connect_host = ''
mysql_connect_user = ''
mysql_connect_password = ''
mysql_connect_db = ''

SECRET_BACKEND = 'File'
PINCODE_BACKEND = 'File'
STATE_BACKEND = 'File'

logger = logging.getLogger('totpcgi')
logger.setLevel(logging.DEBUG)

ch = logging.FileHandler('test.log')
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("[%(levelname)s:%(funcName)s:"
                              "%(lineno)s] %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

VALID_SECRET = None
VALID_SCRATCH_TOKENS = []


def db_connect():
    import psycopg2
    conn = psycopg2.connect(pg_connect_string)
    return conn


def getBackends():
    import totpcgi
    import totpcgi.backends
    backends = totpcgi.backends.Backends()

    import totpcgi.backends.file
    if STATE_BACKEND == 'File':
        backends.state_backend = totpcgi.backends.file.GAStateBackend(state_dir)
    elif STATE_BACKEND == 'pgsql':
        import totpcgi.backends.pgsql
        backends.state_backend = totpcgi.backends.pgsql.GAStateBackend(pg_connect_string)
    elif STATE_BACKEND == 'mysql':
        import totpcgi.backends.mysql
        backends.state_backend = totpcgi.backends.mysql.GAStateBackend(mysql_connect_host, mysql_connect_user,
                                                                       mysql_connect_password, mysql_connect_db)

    if SECRET_BACKEND == 'File':
        backends.secret_backend = totpcgi.backends.file.GASecretBackend(secrets_dir)
    elif SECRET_BACKEND == 'pgsql':
        backends.secret_backend = totpcgi.backends.pgsql.GASecretBackend(pg_connect_string)
    elif SECRET_BACKEND == 'mysql':
        backends.secret_backend = totpcgi.backends.mysql.GASecretBackend(mysql_connect_host, mysql_connect_user,
                                                                         mysql_connect_password, mysql_connect_db)

    if PINCODE_BACKEND == 'File':
        backends.pincode_backend = totpcgi.backends.file.GAPincodeBackend(pincode_file)
    elif PINCODE_BACKEND == 'pgsql':
        backends.pincode_backend = totpcgi.backends.pgsql.GAPincodeBackend(pg_connect_string)
    elif PINCODE_BACKEND == 'mysql':
        backends.pincode_backend = totpcgi.backends.mysql.GAPincodeBackend(mysql_connect_host, mysql_connect_user,
                                                                           mysql_connect_password, mysql_connect_db)
    elif PINCODE_BACKEND == 'ldap':
        import totpcgi.backends.ldap
        backends.pincode_backend = totpcgi.backends.ldap.GAPincodeBackend(ldap_url, ldap_dn, ldap_cacert)

    return backends


def setCustomPincode(pincode, algo='sha256', user='valid', makedb=True, addjunk=False):
    hashcode = totpcgi.utils.hash_pincode(pincode, algo=algo)
    logger.debug('generated hashcode=%s' % hashcode)

    if not makedb and addjunk:
        hashcode += ':junk'

    backends = getBackends()

    if PINCODE_BACKEND == 'File':
        backends.pincode_backend.save_user_hashcode(user, hashcode, makedb=makedb)

    elif PINCODE_BACKEND in ('pgsql', 'mysql'):
        backends.pincode_backend.save_user_hashcode(user, hashcode)

    
def cleanState(user='valid'):
    logger.debug('Cleaning state for user %s' % user)
    backends = getBackends()
    backends.state_backend.delete_user_state(user)


def setCustomState(state, user='valid'):
    logger.debug('Setting custom state for user %s' % user)
    backends = getBackends()
    backends.state_backend.get_user_state(user)
    backends.state_backend.update_user_state(user, state)


def getValidUser():
    backends = getBackends()
    return totpcgi.GAUser('valid', backends)


class GATest(unittest.TestCase):
    def setUp(self):
        # Remove any existing state files for user "valid"
        cleanState()

    def tearDown(self):
        cleanState()
        if os.access(pincode_file, os.W_OK):
            os.unlink(pincode_file)
        if os.access(pincode_file + '.db', os.W_OK):
            os.unlink(pincode_file + '.db')

    def testValidSecretParsing(self):
        logger.debug('Running testValidSecretParsing')

        gau = getValidUser()

        backends = getBackends()
        secret = backends.secret_backend.get_user_secret(gau.user)

        self.assertEqual(secret.otp.secret, VALID_SECRET,
                         'Secret read from valid.totp did not match')
        self.assertEqual(gau.user, 'valid', 
                         'User did not match')
        self.assertEqual(secret.rate_limit, (4, 30),
                         'RATE_LIMIT did not parse correctly')
        self.assertEqual(secret.window_size, 3,
                         'WINDOW_SIZE did not parse correctly')

        compare_tokens = []
        for token in VALID_SCRATCH_TOKENS:
            compare_tokens.append(int(token))

        self.assertItemsEqual(compare_tokens, secret.scratch_tokens)

    def testInvalidSecretParsing(self):
        logger.debug('Running testInvalidSecretParsing')

        backends = getBackends()

        gau = totpcgi.GAUser('invalid', backends)
        with self.assertRaises(totpcgi.UserSecretError):
            gau.verify_token(555555)

    def testInvalidUsername(self):
        logger.debug('Running testInvalidUsername')
        
        backends = getBackends()

        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 
                'invalid characters'):
            gau = totpcgi.GAUser('../../etc/passwd', backends)

    def testNonExistentValidUser(self):
        logger.debug('Running testNonExistentValidUser')

        backends = getBackends()
        
        gau = totpcgi.GAUser('bob@example.com', backends)
        with self.assertRaises(totpcgi.UserNotFound):
            gau.verify_token(555555)
    
    def testValidToken(self):
        logger.debug('Running testValidToken')

        gau = getValidUser()
        backends = getBackends()
        secret = backends.secret_backend.get_user_secret(gau.user)

        totp = pyotp.TOTP(secret.otp.secret)
        token = totp.now()
        self.assertEqual(gau.verify_token(token), 'Valid TOTP token used')

        # try using it again
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'been used once'):
            gau.verify_token(token)

        # and again, to make sure it is preserved in state
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'been used once'):
            gau.verify_token(token)

        gau = totpcgi.GAUser('hotp', backends)
        # Save custom state for HOTP user, as some backends rely on it to trigger HOTP mode
        state = totpcgi.GAUserState()
        state.counter = 0
        setCustomState(state, 'hotp')

        hotp = pyotp.HOTP(secret.otp.secret)
        token = hotp.at(0)
        self.assertEqual(gau.verify_token(token), 'Valid HOTP token used')

        # make sure the counter now validates at 1 and 2
        self.assertEqual(gau.verify_token(hotp.at(1)), 'Valid HOTP token used')
        self.assertEqual(gau.verify_token(hotp.at(2)), 'Valid HOTP token used')

        # make sure trying "1" or "2" fails now
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'HOTP token failed to verify'):
            gau.verify_token(hotp.at(1))
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'HOTP token failed to verify'):
            gau.verify_token(hotp.at(2))

        # but we're good to go at 3
        self.assertEqual(gau.verify_token(hotp.at(3)), 'Valid HOTP token used')

        # and we're good to go with 7, which is max window size
        self.assertEqual(gau.verify_token(hotp.at(7)), 'Valid HOTP token within window size used')

        # Trying with "5" should fail now
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'HOTP token failed to verify'):
            gau.verify_token(hotp.at(5))

        # but we're good to go at 8
        self.assertEqual(gau.verify_token(hotp.at(8)), 'Valid HOTP token used')

        # should fail with 13, which is beyond window size of 9+3
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'HOTP token failed to verify'):
            gau.verify_token(hotp.at(13))

        cleanState('hotp')


    def testTOTPWindowSize(self):
        logger.debug('Running testWindowSize')
        gau = getValidUser()
        backends = getBackends()
        secret = backends.secret_backend.get_user_secret(gau.user)
        totp = pyotp.TOTP(secret.otp.secret)

        # go back until we get the previous token
        timestamp = int(time.time())
        token = totp.at(timestamp)

        past_token = future_token = None
        past_timestamp = future_timestamp = timestamp

        while past_token is None or past_token == token:
            past_timestamp -= 10
            past_token = totp.at(past_timestamp)

        while future_token is None or future_token == token:
            future_timestamp += 10
            future_token = totp.at(future_timestamp)

        logger.debug('past_token=%s' % past_token)
        logger.debug('token=%s' % token)
        logger.debug('future_token=%s' % future_token)

        # this should work
        self.assertEqual(gau.verify_token(past_token), 
                'Valid TOTP token within window size used')
        self.assertEqual(gau.verify_token(future_token), 
                'Valid TOTP token within window size used')

        # trying to reuse them should fail
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'been used once'):
            gau.verify_token(past_token)
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'been used once'):
            gau.verify_token(future_token)

        # get some tokens from +/- 600 seconds
        past_token = totp.at(int(time.time())-600)
        future_token = totp.at(int(time.time())+600)
        logger.debug('past_token=%s' % past_token)
        logger.debug('future_token=%s' % future_token)
        # this should fail
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'TOTP token failed to verify'):
            gau.verify_token(past_token)
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'TOTP token failed to verify'):
            gau.verify_token(future_token)

    def testTOTPRateLimit(self):
        logger.debug('Running testTOTPRateLimit')
        
        gau = getValidUser()

        backends = getBackends()
        secret = backends.secret_backend.get_user_secret(gau.user)
        token  = '555555'

        # We now fail 4 times consecutively
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'TOTP token failed to verify'):
            gau.verify_token(token)
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'TOTP token failed to verify'):
            gau.verify_token(token)
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'TOTP token failed to verify'):
            gau.verify_token(token)
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'TOTP token failed to verify'):
            gau.verify_token(token)

        # We should now get a rate-limited error
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'Rate-limit'):
            gau.verify_token(token)

        # Same with a valid token
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'Rate-limit'):
            gau.verify_token(secret.get_totp_token())

        # Make sure we recover from rate-limiting correctly
        old_timestamp = secret.timestamp-(31+(secret.rate_limit[1]*10))
        state = totpcgi.GAUserState()
        state.fail_timestamps = [
            old_timestamp,
            old_timestamp,
            old_timestamp,
            old_timestamp
        ]
        setCustomState(state)

        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'TOTP token failed to verify'):
            gau.verify_token(token)

        # Valid token should work, too
        setCustomState(state)
        self.assertEqual(gau.verify_token(secret.get_totp_token()), 'Valid TOTP token used')

    def testHOTPRateLimit(self):
        logger.debug('Running testHOTPRateLimit')

        backends = getBackends()
        # Save custom state for HOTP user, as some backends rely on it to trigger HOTP mode
        state = totpcgi.GAUserState()
        state.counter = 1
        setCustomState(state, 'hotp')

        gau = totpcgi.GAUser('hotp', backends)
        secret = backends.secret_backend.get_user_secret(gau.user)

        hotp = pyotp.HOTP(secret.otp.secret)
        token = hotp.at(1)
        self.assertEqual(gau.verify_token(token), 'Valid HOTP token used')
        # counter is now at 2

        token = '555555'

        # We now fail 4 times consecutively
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'HOTP token failed to verify'):
            gau.verify_token(token)
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'HOTP token failed to verify'):
            gau.verify_token(token)
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'HOTP token failed to verify'):
            gau.verify_token(token)
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'HOTP token failed to verify'):
            gau.verify_token(token)

        # We should now get a rate-limited error
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'Rate-limit'):
            gau.verify_token(token)

        # Same with a valid token
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'Rate-limit'):
            gau.verify_token(hotp.at(2))

        # Make sure we recover from rate-limiting correctly
        old_timestamp = secret.timestamp-(31+(secret.rate_limit[1]*10))
        state = totpcgi.GAUserState()
        state.fail_timestamps = [
            old_timestamp,
            old_timestamp,
            old_timestamp,
            old_timestamp
        ]
        state.counter = 2
        setCustomState(state, 'hotp')

        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'HOTP token failed to verify'):
            gau.verify_token(token)

        # Valid token should work, too
        setCustomState(state, 'hotp')
        self.assertEqual(gau.verify_token(hotp.at(2)), 'Valid HOTP token used')
        cleanState('hotp')
        
    def testInvalidToken(self):
        logger.debug('Running testInvalidToken')

        gau = getValidUser()
        token = '555555'

        logger.debug('Testing with an invalid 6-digit token')
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'TOTP token failed to verify'):
            gau.verify_token(token)

        logger.debug('Test right away with a valid token')
        backends = getBackends()
        secret = backends.secret_backend.get_user_secret(gau.user)

        totp = pyotp.TOTP(secret.otp.secret)
        validtoken = totp.now()
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'been used once'):
            gau.verify_token(validtoken)

        logger.debug('Testing with a token that is too long')
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'too long'):
            cleanState()
            gau.verify_token('12345678910')

        logger.debug('Testing with a non-integer token')
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'not an integer'):
            cleanState()
            gau.verify_token('WAKKA')

        logger.debug('Testing with an invalid 8-digit scratch-token')
        with self.assertRaisesRegexp(totpcgi.VerifyFailed,
                'Not a valid scratch-token'):
            gau.verify_token('11112222')

    def testScratchTokens(self):
        gau = getValidUser()

        ret = gau.verify_token(VALID_SCRATCH_TOKENS[0])
        self.assertEqual(ret, 'Scratch-token used')

        # try using it again
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 
                'Scratch-token already used once'):
            gau.verify_token(VALID_SCRATCH_TOKENS[0])

        # try using another token
        ret = gau.verify_token(VALID_SCRATCH_TOKENS[1])
        self.assertEqual(ret, 'Scratch-token used')

        # use first one again to make sure it's preserved in the state file
        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 
                'Scratch-token already used once'):
            gau.verify_token(VALID_SCRATCH_TOKENS[0])

    def testTotpCGI(self):
        # Very basic test -- it should return 'user not found'
        os.environ['REMOTE_ADDR'] = '127.0.0.1'
        os.environ['QUERY_STRING'] = 'user=bupkis&token=555555&mode=PAM_SM_AUTH'
        os.environ['PYTHONPATH'] = '.'

        command = ['env', 'python', 'cgi/totp.cgi', 'conf/totpcgi.conf']

        ret = subprocess.check_output(command)

        self.assertRegexpMatches(ret, 'bupkis.totp does not exist')

    def testPincodes(self):
        logger.debug('Running testPincodes')

        logger.debug('Testing in non-required mode')

        backends = getBackends()

        ga = totpcgi.GoogleAuthenticator(backends)
        gau = getValidUser()

        pincode   = 'wakkawakka'
        secret    = backends.secret_backend.get_user_secret(gau.user)
        tokencode = str(secret.get_totp_token()).zfill(6)

        token = pincode + tokencode

        if PINCODE_BACKEND == 'File':
            logger.debug('Testing without pincodes file')
            with self.assertRaisesRegexp(totpcgi.UserNotFound, 
                    'pincodes file not found'):
                ga.verify_user_token('valid', token)

            logger.debug('Testing with pincodes.db older than pincodes')
            setCustomPincode(pincode)
            setCustomPincode('blarg', makedb=False)

            with self.assertRaisesRegexp(totpcgi.UserPincodeError,
                'Pincode did not match'):
                ga.verify_user_token('valid', token)

            cleanState()

            logger.debug('Testing with fallback to pincodes')
            pincode_db_file = pincode_file + '.db'
            os.unlink(pincode_db_file)
            os.unlink(pincode_file)
            setCustomPincode('blarg', user='donotwant')
            os.unlink(pincode_file)
            setCustomPincode(pincode, user='valid', makedb=False)
            # Touch it, so it's newer than pincodes 
            os.utime(pincode_db_file, None)

            ret = ga.verify_user_token('valid', token)
            self.assertEqual(ret, 'Valid TOTP token used')

            cleanState()

            logger.debug('Testing with junk at the end')
            setCustomPincode(pincode, makedb=False, addjunk=True)
            ret = ga.verify_user_token('valid', token)
            self.assertEqual(ret, 'Valid TOTP token used')

            cleanState()

        if PINCODE_BACKEND in ('pgsql', 'mysql'):
            backends.pincode_backend.delete_user_hashcode('valid')
            logger.debug('Testing without a user pincode record present')
            with self.assertRaisesRegexp(totpcgi.UserNotFound, 
                    'no pincodes record'):
                ga.verify_user_token('valid', token)


        if PINCODE_BACKEND in ('pgsql', 'mysql', 'File'):
            logger.debug('Testing with 1-digit long pincode')
            setCustomPincode('1')
            ret = ga.verify_user_token('valid', '1'+tokencode)
            self.assertEqual(ret, 'Valid TOTP token used')

            cleanState()

            logger.debug('Testing with 2-digit long pincode + valid tokencode')
            setCustomPincode('99')
            ret = ga.verify_user_token('valid', '99'+tokencode)
            self.assertEqual(ret, 'Valid TOTP token used')

            cleanState()

            logger.debug('Testing with 2-digit long pincode + invalid tokencode')
            setCustomPincode('99')
            with self.assertRaisesRegexp(totpcgi.VerifyFailed,
                'TOTP token failed to verify'):
                ret = ga.verify_user_token('valid', '99'+'000000')

            cleanState()

            logger.debug('Testing with bcrypt')
            setCustomPincode(pincode, algo='bcrypt')
            ret = ga.verify_user_token('valid', token)
            self.assertEqual(ret, 'Valid TOTP token used')

            cleanState()

            logger.debug('Testing with md5')
            setCustomPincode(pincode, algo='md5')
            ret = ga.verify_user_token('valid', token)
            self.assertEqual(ret, 'Valid TOTP token used')

            cleanState()

            setCustomPincode(pincode)

        if PINCODE_BACKEND == 'ldap':
            valid_user = os.environ['ldap_user']
            pincode    = os.environ['ldap_password']
            token      = pincode + tokencode
        else:
            valid_user = 'valid'
            pincode = 'wakkawakka'
            setCustomPincode(pincode)

        logger.debug('Testing with pincode+scratch-code')
        ret = ga.verify_user_token(valid_user, pincode+VALID_SCRATCH_TOKENS[0])
        self.assertEqual(ret, 'Scratch-token used')

        logger.debug('Testing with pincode+invalid-scratch-code')
        if PINCODE_BACKEND == 'ldap':
            raisedmsg = 'LDAP bind failed'
        else:
            raisedmsg = 'Pincode did not match'

        with self.assertRaisesRegexp(totpcgi.VerifyFailed, 'TOTP token failed to verify'):
            ret = ga.verify_user_token(valid_user, pincode+'00000000')

        cleanState()

        logger.debug('Turning on pincode enforcing')
        ga = totpcgi.GoogleAuthenticator(backends, require_pincode=True)

        logger.debug('Trying valid token without pincode')
        with self.assertRaisesRegexp(totpcgi.UserPincodeError,
            'Pincode is required'):
            ga.verify_user_token(valid_user, tokencode)

        cleanState()

        logger.debug('Trying valid scratch token without pincode')
        with self.assertRaisesRegexp(totpcgi.UserPincodeError,
            'Pincode is required'):
            ga.verify_user_token(valid_user, VALID_SCRATCH_TOKENS[0])

        cleanState()

        logger.debug('Trying valid token with pincode in enforcing')
        ret = ga.verify_user_token(valid_user, token)
        self.assertEqual(ret, 'Valid TOTP token used')
        
        cleanState()

        logger.debug('Testing valid pincode+scratch-code in enforcing')
        ret = ga.verify_user_token(valid_user, pincode+VALID_SCRATCH_TOKENS[0])
        self.assertEqual(ret, 'Scratch-token used')

        cleanState()

        logger.debug('Testing with valid token but invalid pincode')
        with self.assertRaisesRegexp(totpcgi.UserPincodeError, raisedmsg):
            ga.verify_user_token(valid_user, 'blarg'+tokencode)

        logger.debug('Testing again with valid token and valid pincode')
        with self.assertRaisesRegexp(totpcgi.VerifyFailed,
                'already been used'):
            ga.verify_user_token(valid_user, token)

        cleanState()

        logger.debug('Testing with valid pincode but invalid token')
        with self.assertRaisesRegexp(totpcgi.VerifyFailed,
            'TOTP token failed to verify'):
            ga.verify_user_token(valid_user, pincode+'555555')

    def testEncryptedSecret(self):
        logger.debug('Running testEncryptedSecret')

        backends = getBackends()
        ga = totpcgi.GoogleAuthenticator(backends)

        pincode = 'wakkawakka'
        setCustomPincode(pincode, user='encrypted')

        totp = pyotp.TOTP(VALID_SECRET)
        token = str(totp.now()).zfill(6)

        ga.verify_user_token('encrypted', pincode+token)

        # This should fail, as we ignore scratch tokens with encrypted secrets
        with self.assertRaisesRegexp(totpcgi.VerifyFailed,
                'Not a valid scratch-token'):
            ga.verify_user_token('encrypted', pincode+'12345678')

        cleanState(user='encrypted')

        setCustomPincode(pincode, user='encrypted-bad')
        with self.assertRaisesRegexp(totpcgi.UserSecretError,
                'Failed to'):
            ga.verify_user_token('encrypted-bad', pincode+token)

        cleanState(user='encrypted-bad')


if __name__ == '__main__':
    assert sys.version_info[0] >= 2 and sys.version_info[1] >= 7, \
        'Test suite requires python >= 2.7'

    # To test postgresql backend, do:
    # export pg_connect_string='blah blah'
    if 'pg_connect_string' in os.environ.keys():
        STATE_BACKEND = SECRET_BACKEND = PINCODE_BACKEND = 'pgsql'
        pg_connect_string = os.environ['pg_connect_string']
    
    # To test ldap backend, set env vars for
    # ldap_url, ldap_dn, ldap_cacert, ldap_user and ldap_password
    if 'ldap_url' in os.environ.keys():
        PINCODE_BACKEND = 'ldap'
        ldap_url = os.environ['ldap_url']
        ldap_dn = os.environ['ldap_dn']
        ldap_cacert = os.environ['ldap_cacert']

    if 'mysql_connect_host' in os.environ.keys():
        STATE_BACKEND = SECRET_BACKEND = PINCODE_BACKEND = 'mysql'
        mysql_connect_host = os.environ['mysql_connect_host']
        mysql_connect_user = os.environ['mysql_connect_user']
        mysql_connect_password = os.environ['mysql_connect_password']
        mysql_connect_db = os.environ['mysql_connect_db']

    backends = getBackends()

    # valid user
    gaus = totpcgi.utils.generate_secret(rate_limit=(4, 30))
    backends.secret_backend.save_user_secret('valid', gaus)

    VALID_SECRET = gaus.otp.secret
    VALID_SCRATCH_TOKENS = gaus.scratch_tokens

    # hotp is using HOTP mode
    gaus.set_hotp(0)
    backends.secret_backend.save_user_secret('hotp', gaus)

    # switch back to totp for the rest
    gaus.counter = -1
    gaus.otp = pyotp.TOTP(VALID_SECRET)

    # encrypted-secret user is same as valid, just encrypted
    backends.secret_backend.save_user_secret('encrypted', gaus, 'wakkawakka')

    # invalid user (bad secret)
    gaus = totpcgi.utils.generate_secret()
    gaus.otp.secret = 'WAKKAWAKKA'
    backends.secret_backend.save_user_secret('invalid', gaus)

    # encrypted-bad (bad encryption)
    gaus.otp.secret = 'aes256+hmac256$WAKKAWAKKA$WAKKAWAKKA'
    backends.secret_backend.save_user_secret('encrypted-bad', gaus)

    try:
        unittest.main()
    finally:
        for username in ('valid', 'invalid', 'encrypted', 'encrypted-bad', 'hotp'):
            backends.state_backend.delete_user_state(username)
            backends.secret_backend.delete_user_secret(username)
            pass

########NEW FILE########
__FILENAME__ = file
##
# Copyright (C) 2012 by Konstantin Ryabitsev and contributors
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
from __future__ import absolute_import

import logging
import totpcgi
import totpcgi.backends
import totpcgi.utils

logger = logging.getLogger('totpcgi')

import os
from fcntl import lockf, LOCK_EX, LOCK_UN, LOCK_SH

import anydbm


class GAPincodeBackend(totpcgi.backends.GAPincodeBackend):
    def __init__(self, pincode_file):
        totpcgi.backends.GAPincodeBackend.__init__(self)
        logger.debug('Using FILE Pincode backend')

        self.pincode_file = pincode_file

    def _get_all_hashcodes(self):
        hashcodes = {}

        try:
            fh = open(self.pincode_file, 'r')
            lockf(fh, LOCK_SH)

            while True:
                line = fh.readline()
                if not line:
                    break

                if line.find(':') == -1:
                    continue

                line = line.strip()

                parts = line.split(':')
                logger.debug('user=%s, hashcode=%s' % (parts[0], parts[1]))
                hashcodes[parts[0]] = parts[1]

            logger.debug('Read %s entries from %s' % 
                         (len(hashcodes), self.pincode_file))

            lockf(fh, LOCK_UN)
            fh.close()

        except IOError:
            logger.debug('%s could not be open for reading' % self.pincode_file)

        return hashcodes

    def verify_user_pincode(self, user, pincode):
        # The format is basically /etc/shadow, except we ignore anything
        # past the first 2 entries. We return the hashed code that we'll need
        # to compare.
        if not os.access(self.pincode_file, os.R_OK):
            raise totpcgi.UserNotFound('pincodes file not found!')

        # Check if we have a compiled version first
        logger.debug('Checking if there is a pincodes.db')
        pincode_db_file = self.pincode_file + '.db'

        hashcode = None

        if os.access(pincode_db_file, os.R_OK):
            logger.debug('Found pincodes.db. Comparing mtime with pincodes')
            dbmtime = os.stat(pincode_db_file).st_mtime
            ptmtime = os.stat(self.pincode_file).st_mtime

            logger.debug('dbmtime=%s' % dbmtime)
            logger.debug('ptmtime=%s' % ptmtime)

            if dbmtime >= ptmtime:
                logger.debug('.db mtime greater, will use the db')

                db = anydbm.open(pincode_db_file, 'r')

                if user in db.keys():
                    logger.debug('Found %s in the .db' % user)
                    hashcode = db[user]
                    db.close()

                logger.debug('%s not in .db. Falling back to plaintext.' % user)
            else:
                logger.debug('.db is stale! Falling back to plaintext.')

        if hashcode is None:
            logger.debug('Reading pincode file: %s' % self.pincode_file)

            hashcodes = self._get_all_hashcodes()

            try:
                hashcode = hashcodes[user]
            except KeyError:
                raise totpcgi.UserPincodeError('Pincode not found for user %s' % user)

        return self._verify_by_hashcode(pincode, hashcode)

    def save_user_hashcode(self, user, hashcode, makedb=True):
        hashcodes = self._get_all_hashcodes()

        if hashcode is None:
            logger.debug('Hashcode is None, deleting %s' % user)
            try:
                hashcodes.pop(user)
            except KeyError:
                # wasn't there anyway
                pass

        else:
            logger.debug('Setting new hashcode: %s:%s' % (user, hashcode))
            hashcodes[user] = hashcode

        # Bubble up any write errors up the chain
        fh = open(self.pincode_file, 'w')
        lockf(fh, LOCK_EX)

        for user, hashcode in hashcodes.iteritems():
            fh.write('%s:%s\n' % (user, hashcode))

        lockf(fh, LOCK_UN)
        fh.close()

        if makedb:
            # We always overwrite the db file to avoid any discrepancies with
            # the text file.
            pincode_db_file = self.pincode_file + '.db'
            logger.debug('Compiling the db in %s' % pincode_db_file)

            db = anydbm.open(pincode_db_file, 'n')
            db.update(hashcodes)
            db.close()

    def delete_user_hashcode(self, user):
        self.save_user_hashcode(user, None)


class GASecretBackend(totpcgi.backends.GASecretBackend):
    def __init__(self, secrets_dir):
        totpcgi.backends.GASecretBackend.__init__(self)
        logger.debug('Using FILE Secret backend')

        self.secrets_dir = secrets_dir

    def get_user_secret(self, user, pincode=None):

        totp_file = os.path.join(self.secrets_dir, user) + '.totp'
        logger.debug('Examining user secret file: %s' % totp_file)

        if not os.access(totp_file, os.R_OK):
            raise totpcgi.UserNotFound('%s.totp does not exist or is not readable' % user)

        fh = open(totp_file, 'r')
        lockf(fh, LOCK_SH)

        # secret is always the first entry
        secret = fh.readline()
        secret = secret.strip()

        using_encrypted_secret = False
        if secret.find('aes256+hmac256') == 0:
            using_encrypted_secret = True
            if pincode is not None:
                secret = totpcgi.utils.decrypt_secret(secret, pincode)
            else:
                raise totpcgi.UserSecretError('Secret is encrypted, but no pincode provided')

        gaus = totpcgi.GAUserSecret(secret)

        while True:
            line = fh.readline()

            if line == '':
                break

            line = line.strip()

            if len(line) and line[0] == '"':
                if line[2:12] == 'RATE_LIMIT':
                    (tries, seconds) = line[13:].split(' ')
                    gaus.rate_limit = (int(tries), int(seconds))
                    logger.debug('rate_limit=%s' % str(gaus.rate_limit))

                elif line[2:13] == 'WINDOW_SIZE':
                    window_size = int(line[14:])
                    if 0 < window_size < 3:
                        window_size = 3
                    gaus.window_size = window_size
                    logger.debug('window_size=%s' % window_size)

                elif line[2:14] == 'HOTP_COUNTER':
                    # This will most likely be overriden by user state, but load it up anyway,
                    # as this will trigger HOTP mode.
                    try:
                        gaus.set_hotp(int(line[15:]))
                    except ValueError:
                        gaus.set_hotp(0)

                    logger.debug('hotp_counter=%s' % gaus.counter)

            # Scratch code tokens are 8-digit
            # We ignore scratch tokens if we're using encrypted secret
            elif len(line) == 8 and not using_encrypted_secret:
                try:
                    gaus.scratch_tokens.append(int(line))
                    logger.debug('Found a scratch-code token, adding it')
                except ValueError:
                    logger.debug('Non-numeric scratch token found')
                    # don't fail, just pretend we didn't see it
                    continue

        lockf(fh, LOCK_UN)
        fh.close()

        # Make sure that we have a window_size defined
        # The topt configuration many not have had one, if not we need
        # to make sure we set it to the default of 3
        if not hasattr(gaus, 'window_size'):
                gaus.window_size = 3

        return gaus

    def save_user_secret(self, user, gaus, pincode=None):
        totp_file = os.path.join(self.secrets_dir, user) + '.totp'

        try:
            fh = open(totp_file, 'w')
        except IOError as e:
            raise totpcgi.SaveFailed('%s could not be saved: %s' % 
                                     (totp_file, e))

        lockf(fh, LOCK_EX)
        secret = gaus.otp.secret

        if pincode is not None:
            secret = totpcgi.utils.encrypt_secret(secret, pincode)

        fh.write('%s\n' % secret)
        fh.write('" RATE_LIMIT %s %s\n' % gaus.rate_limit)
        fh.write('" WINDOW_SIZE %s\n' % gaus.window_size)
        if gaus.is_hotp():
            fh.write('" HOTP_COUNTER %s\n' % gaus.counter)
        else:
            fh.write('" DISALLOW_REUSE\n')
            fh.write('" TOTP_AUTH\n')

        if pincode is None:
            fh.write('\n'.join(gaus.scratch_tokens))

        lockf(fh, LOCK_UN)
        fh.close()

        logger.debug('Wrote %s' % totp_file)

    def delete_user_secret(self, user):
        totp_file = os.path.join(self.secrets_dir, user) + '.totp'

        try:
            os.unlink(totp_file)
        except (OSError, IOError) as e:
            raise totpcgi.DeleteFailed('%s could not be deleted: %s' %
                                       (totp_file, e))


class GAStateBackend(totpcgi.backends.GAStateBackend):
    def __init__(self, state_dir):
        totpcgi.backends.GAStateBackend.__init__(self)
        logger.debug('Using FILE State backend')

        self.state_dir = state_dir
        self.fhs = {}

    def get_user_state(self, user):
        state = totpcgi.GAUserState()

        import json

        # load the state file and keep it locked while we do verification
        state_file = os.path.join(self.state_dir, user) + '.json'
        logger.debug('Loading user state from: %s' % state_file)
        
        # For totpcgiprov and totpcgi to be able to write to the same state
        # file, we have to create it world-writable. Since we have restricted
        # permissions on the parent directory (totpcgi:totpcgiprov), plus
        # selinux labels in place, this should keep this safe from tampering.
        os.umask(0000)

        # we exclusive-lock the file to prevent race conditions resulting
        # in potential token reuse.
        if os.access(state_file, os.W_OK):
            logger.debug('%s exists, opening r+' % state_file)
            fh = open(state_file, 'r+')
            logger.debug('Locking state file for user %s' % user)
            lockf(fh, LOCK_EX)
            try:
                js = json.load(fh)

                logger.debug('loaded state=%s' % js)

                state.fail_timestamps = js['fail_timestamps']
                state.success_timestamps = js['success_timestamps']
                state.used_scratch_tokens = js['used_scratch_tokens']

                if 'counter' in js:
                    state.counter = js['counter']

            except Exception, ex:
                # We fail out of caution, though if someone wanted to 
                # screw things up, they could have done so without making
                # the file un-parseable by json -- all they need to do is to
                # erase the file.
                logger.debug('Parsing json failed with: %s' % ex)
                logger.debug('Unlocking state file for user %s' % user)
                lockf(fh, LOCK_UN)
                raise totpcgi.UserStateError(
                    'Error parsing the state file for: %s' % user)

            fh.seek(0)
        else:
            logger.debug('%s does not exist, opening w' % state_file)
            try:
                fh = open(state_file, 'w')
            except IOError:
                raise totpcgi.UserStateError(
                    'Cannot write user state for %s, exiting.' % user)
            logger.debug('Locking state file for user %s' % user)
            lockf(fh, LOCK_EX)

        # The following condition should never happen, in theory,
        # because we have an exclusive lock on that file. If it does, 
        # things have broken somewhere (probably locking is broken).
        if user not in self.fhs.keys():
            self.fhs[user] = fh

        return state

    def update_user_state(self, user, state):
        if user not in self.fhs.keys():
            raise totpcgi.UserStateError("%s's state FH has gone away!" % user)

        import json

        fh = self.fhs[user]

        logger.debug('fh.name=%s' % fh.name)

        js = {
            'fail_timestamps': state.fail_timestamps,
            'success_timestamps': state.success_timestamps,
            'used_scratch_tokens': state.used_scratch_tokens,
            'counter': state.counter
        }

        logger.debug('saving state=%s' % js)

        logger.debug('Saving new state for user %s' % user)
        json.dump(js, fh, indent=4)
        fh.truncate()

        logger.debug('Unlocking state file for user %s' % user)
        lockf(fh, LOCK_UN)
        fh.close()

        del self.fhs[user]

        logger.debug('fhs=%s' % self.fhs)

    def delete_user_state(self, user):
        # this should ONLY be used by test.py
        state_file = os.path.join(self.state_dir, '%s.json' % user)
        if os.access(state_file, os.W_OK):
            os.unlink(state_file)
            logger.debug('Removed user state file: %s' % state_file)

########NEW FILE########
__FILENAME__ = ldap
##
# Copyright (C) 2012 by Konstantin Ryabitsev and contributors
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
from __future__ import absolute_import

import logging
import totpcgi
import totpcgi.backends

import ldap
from string import Template

logger = logging.getLogger('totpcgi')

class GASecretBackend:
    def __init__(self):
        raise totpcgi.backends.BackendNotSupported(
            'Secret backend not (yet?) supported by ldap backend engine')

    def get_user_secret(self, user):
        pass


class GAPincodeBackend(totpcgi.backends.GAPincodeBackend):
    """ This verifies the pincode by trying to bind to ldap using the 
        username and pincode passed for verification"""

    def __init__(self, ldap_url, ldap_dn, ldap_cacert):
        totpcgi.backends.GAPincodeBackend.__init__(self)

        logger.debug('Using LDAP Pincode backend')

        self.ldap_url = ldap_url
        self.ldap_dn = ldap_dn
        self.ldap_cacert = ldap_cacert

    def verify_user_pincode(self, user, pincode):
        if len(self.ldap_cacert):
            ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, self.ldap_cacert)

        lconn = ldap.initialize(self.ldap_url)
        lconn.protocol_version = 3
        lconn.set_option(ldap.OPT_REFERRALS, 0)

        tpt = Template(self.ldap_dn)
        dn = tpt.safe_substitute(username=user)
        
        try:
            lconn.simple_bind_s(dn, pincode)

        except Exception, ex:
            raise totpcgi.UserPincodeError('LDAP bind failed: %s' % ex)

    def save_user_hashcode(self, user, pincode, makedb=True):
        raise totpcgi.backends.BackendNotSupported(
            'LDAP backend does not support saving pincodes.')

    def delete_user_hashcode(self, user):
        raise totpcgi.backends.BackendNotSupported(
            'LDAP backend does not support deleting pincodes.')


class GAStateBackend:
    def __init__(self):
        raise totpcgi.backends.BackendNotSupported(
            'State backend not supported by ldap backend engine')
########NEW FILE########
__FILENAME__ = mysql
##
# Copyright (C) 2012 by Konstantin Ryabitsev and contributors
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
from __future__ import absolute_import

import logging
import totpcgi
import totpcgi.backends
import totpcgi.utils

import MySQLdb

logger = logging.getLogger('totpcgi')

# Globally track the database connections
dbconn = {}
userids = {}


def db_connect(connect_host, connect_user, connect_password, connect_db):
    global dbconn

    if connect_host not in dbconn or not dbconn[connect_host].open:
        dbconn[connect_host] = MySQLdb.connect(host=connect_host, user=connect_user,
                                               passwd=connect_password, db=connect_db)

    return dbconn[connect_host]


def get_user_id(conn, user):
    global userids

    if user in userids.keys():
        return userids[user]

    cur = conn.cursor()
    logger.debug('Checking users record for %s' % user)

    cur.execute('SELECT userid FROM users WHERE username = %s', (user,))
    row = cur.fetchone()

    if row is None:
        logger.debug('No existing record for user=%s, creating' % user)
        cur.execute('INSERT INTO users (username) VALUES (%s)', (user,))
        cur.execute('SELECT userid FROM users WHERE username = %s', (user,))
        row = cur.fetchone()

    userids[user] = row[0]
    return userids[user]


class GAStateBackend(totpcgi.backends.GAStateBackend):
    def __init__(self, connect_host, connect_user, connect_password, connect_db):
        totpcgi.backends.GAStateBackend.__init__(self)
        logger.debug('Using MySQL State backend')

        logger.debug('Establishing connection to the database')
        self.conn = db_connect(connect_host, connect_user, connect_password, connect_db)

        logger.debug('Checking if we have the counters table')
        cur = self.conn.cursor()
        cur.execute("SELECT exists(SELECT * FROM information_schema.tables WHERE table_name=%s)", ('counters',))
        self.has_counters = cur.fetchone()[0]

        if not self.has_counters:
            logger.info('Counters table not found, assuming pre-0.6 database schema (no HOTP support)')

        self.locks = {}

    def get_user_state(self, user):

        userid = get_user_id(self.conn, user)

        state = totpcgi.GAUserState()

        logger.debug('Acquiring lock for userid=%s' % userid)

        cur = self.conn.cursor()
        cur.execute('SELECT GET_LOCK(%s,180)', (userid,))
        self.locks[user] = userid 

        cur.execute('''
            SELECT timestamp, success
              FROM timestamps
             WHERE userid = %s''', (userid,))

        for (timestamp, success) in cur.fetchall():
            if success:
                state.success_timestamps.append(timestamp)
            else:
                state.fail_timestamps.append(timestamp)

        cur.execute('''
            SELECT token
              FROM used_scratch_tokens
             WHERE userid = %s''', (userid,))

        for (token,) in cur.fetchall():
            state.used_scratch_tokens.append(token)

        # Now try to load counter info, if we have that table
        if self.has_counters:
            cur.execute('''
                SELECT counter
                  FROM counters
                 WHERE userid = %s''', (userid,))

            row = cur.fetchone()
            if row and row[0] >= 0:
                state.counter = row[0]

        return state

    def update_user_state(self, user, state):
        logger.debug('Writing new state for user %s' % user)

        if user not in self.locks.keys():
            raise totpcgi.UserStateError("%s's MySQL lock has gone away!" % user)

        userid = self.locks[user]

        cur = self.conn.cursor()

        cur.execute('DELETE FROM timestamps WHERE userid=%s', (userid,))
        cur.execute('DELETE FROM used_scratch_tokens WHERE userid=%s', (userid,))

        for timestamp in state.fail_timestamps:
            cur.execute('''
                INSERT INTO timestamps (userid, success, timestamp)
                     VALUES (%s, %s, %s)''', (userid, False, timestamp))

        for timestamp in state.success_timestamps:
            cur.execute('''
                INSERT INTO timestamps (userid, success, timestamp)
                     VALUES (%s, %s, %s)''', (userid, True, timestamp))

        for token in state.used_scratch_tokens:
            cur.execute('''
                INSERT INTO used_scratch_tokens (userid, token)
                     VALUES (%s, %s)''', (userid, token))

        if state.counter >= 0 and self.has_counters:
            cur.execute('DELETE FROM counters WHERE userid=%s', (userid,))
            cur.execute('''
                INSERT INTO counters (userid, counter)
                     VALUES (%s, %s)''', (userid, state.counter))

        logger.debug('Releasing lock for userid=%s' % userid)
        cur.execute('SELECT RELEASE_LOCK(%s)', (userid,))

        self.conn.commit()

        del self.locks[user]

    def delete_user_state(self, user):
        cur = self.conn.cursor()
        logger.debug('Deleting state records for user=%s' % user)

        userid = get_user_id(self.conn, user)

        cur.execute('''
            DELETE FROM timestamps
                  WHERE userid=%s''' % (userid,))
        cur.execute('''
            DELETE FROM used_scratch_tokens
                  WHERE userid=%s''' % (userid,))

        if self.has_counters:
            cur.execute('''
                DELETE FROM counters
                      WHERE userid=%s''' % (userid,))

        # If there are no pincodes or secrets entries, then we may as well
        # delete the user record.
        cur.execute('SELECT True FROM pincodes WHERE userid=%s', (userid,))
        if not cur.fetchone():
            cur.execute('SELECT True FROM secrets WHERE userid=%s', (userid,))
            if not cur.fetchone():
                logger.debug('No entries left for user=%s, deleting' % user)
                cur.execute('DELETE FROM users WHERE userid=%s', (userid,))

        self.conn.commit()


class GASecretBackend(totpcgi.backends.GASecretBackend):
    def __init__(self, connect_host, connect_user, connect_password, connect_db):
        totpcgi.backends.GASecretBackend.__init__(self)
        logger.debug('Using MySQL Secrets backend')

        logger.debug('Establishing connection to the database')
        self.conn = db_connect(connect_host, connect_user, connect_password, connect_db)

        logger.debug('Checking if we have the counters table')
        cur = self.conn.cursor()
        cur.execute("SELECT exists(SELECT * FROM information_schema.tables WHERE table_name=%s)", ('counters',))
        self.has_counters = cur.fetchone()[0]

        if not self.has_counters:
            logger.info('Counters table not found, assuming pre-0.6 database schema (no HOTP support)')

    def get_user_secret(self, user, pincode=None):
        cur = self.conn.cursor()

        logger.debug('Querying DB for user %s' % user)

        cur.execute('''
            SELECT s.secret, 
                   s.rate_limit_times, 
                   s.rate_limit_seconds, 
                   s.window_size
              FROM secrets AS s 
              JOIN users AS u USING (userid)
             WHERE u.username = %s''', (user,))
        row = cur.fetchone()

        if not row:
            raise totpcgi.UserNotFound('no secrets record for %s' % user)

        (secret, rate_limit_times, rate_limit_seconds, window_size) = row

        using_encrypted_secret = False
        if secret.find('aes256+hmac256') == 0 and pincode is not None:
            secret = totpcgi.utils.decrypt_secret(secret, pincode)
            using_encrypted_secret = True
        
        gaus = totpcgi.GAUserSecret(secret)
        if rate_limit_times is not None and rate_limit_seconds is not None:
            gaus.rate_limit = (rate_limit_times, rate_limit_seconds)

        if window_size is not None:
            gaus.window_size = window_size

        logger.debug('Querying DB for counter info for %s' % user)
        # Now try to load counter info, if we have that table
        if self.has_counters:
            cur.execute('''
                SELECT c.counter
                  FROM counters AS c
                  JOIN users AS u USING (userid)
                 WHERE u.username = %s''', (user,))

            row = cur.fetchone()
            if row:
                gaus.set_hotp(row[0])

        # Not loading scratch tokens if using encrypted secret
        if using_encrypted_secret:
            return gaus

        logger.debug('Querying DB for scratch tokens for %s' % user)

        cur.execute('''
            SELECT st.token
              FROM scratch_tokens AS st
              JOIN users AS u USING (userid)
             WHERE u.username = %s''', (user,))
        
        for (token,) in cur.fetchall():
            gaus.scratch_tokens.append(token)

        return gaus

    def save_user_secret(self, user, gaus, pincode=None):
        cur = self.conn.cursor()

        self._delete_user_secret(user)

        userid = get_user_id(self.conn, user)

        secret = gaus.otp.secret

        if pincode is not None:
            secret = totpcgi.utils.encrypt_secret(secret, pincode)

        cur.execute('''
            INSERT INTO secrets 
                        (userid, secret, rate_limit_times,
                         rate_limit_seconds, window_size)
                 VALUES (%s, %s, %s, %s, %s)''', 
                    (userid, secret, gaus.rate_limit[0], gaus.rate_limit[1], gaus.window_size))

        for token in gaus.scratch_tokens:
            cur.execute('''
                    INSERT INTO scratch_tokens
                                (userid, token)
                         VALUES (%s, %s)''', (userid, token,))

        self.conn.commit()

    def _delete_user_secret(self, user):
        userid = get_user_id(self.conn, user)

        cur = self.conn.cursor()
        cur.execute('''
            DELETE FROM secrets
                  WHERE userid=%s''', (userid,))
        cur.execute('''
            DELETE FROM scratch_tokens
                  WHERE userid=%s''', (userid,))

    def delete_user_secret(self, user):
        self._delete_user_secret(user)
        self.conn.commit()


class GAPincodeBackend(totpcgi.backends.GAPincodeBackend):
    def __init__(self, connect_host, connect_user, connect_password, connect_db):
        totpcgi.backends.GAPincodeBackend.__init__(self)
        logger.debug('Using MySQL Pincodes backend')

        logger.debug('Establishing connection to the database')
        self.conn = db_connect(connect_host, connect_user, connect_password, connect_db)
        
    def verify_user_pincode(self, user, pincode):
        cur = self.conn.cursor()

        logger.debug('Querying DB for user %s' % user)

        cur.execute('''
            SELECT p.pincode
              FROM pincodes AS p
              JOIN users AS u USING (userid)
             WHERE u.username = %s''', (user,))

        row = cur.fetchone()

        if not row:
            raise totpcgi.UserNotFound('no pincodes record for user %s' % user)

        (hashcode,) = row

        return self._verify_by_hashcode(pincode, hashcode)

    def _delete_user_hashcode(self, user):
        userid = get_user_id(self.conn, user)

        cur = self.conn.cursor()
        cur.execute('''
            DELETE FROM pincodes 
                  WHERE userid=%s''', (userid,))
        
    def save_user_hashcode(self, user, hashcode, makedb=False):
        self._delete_user_hashcode(user)

        userid = get_user_id(self.conn, user)

        cur = self.conn.cursor()

        cur.execute('''
            INSERT INTO pincodes
                        (userid, pincode)
                 VALUES (%s, %s)''', (userid, hashcode,))

        self.conn.commit()

    def delete_user_hashcode(self, user):
        self._delete_user_hashcode(user)
        self.conn.commit()


########NEW FILE########
__FILENAME__ = pgsql
##
# Copyright (C) 2012 by Konstantin Ryabitsev and contributors
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
from __future__ import absolute_import

import logging
import totpcgi
import totpcgi.backends
import totpcgi.utils

import psycopg2

logger = logging.getLogger('totpcgi')

# Globally track the database connections
dbconn = {}
userids = {}


def db_connect(connect_string):
    global dbconn

    if connect_string not in dbconn or dbconn[connect_string].closed:
        dbconn[connect_string] = psycopg2.connect(connect_string)

    return dbconn[connect_string]


def get_user_id(conn, user):
    global userids

    if user in userids.keys():
        return userids[user]

    cur = conn.cursor()
    logger.debug('Checking users record for %s' % user)

    cur.execute('SELECT userid FROM users WHERE username = %s', (user,))
    row = cur.fetchone()

    if row is None:
        logger.debug('No existing record for user=%s, creating' % user)
        cur.execute('INSERT INTO users (username) VALUES (%s)', (user,))
        cur.execute('SELECT userid FROM users WHERE username = %s', (user,))
        row = cur.fetchone()

    userids[user] = row[0]
    return userids[user]


class GAStateBackend(totpcgi.backends.GAStateBackend):
    def __init__(self, connect_string):
        totpcgi.backends.GAStateBackend.__init__(self)
        logger.debug('Using PGSQL State backend')

        logger.debug('Establishing connection to the database')
        self.conn = db_connect(connect_string)

        logger.debug('Checking if we have the counters table')
        cur = self.conn.cursor()
        cur.execute("select exists(select * from information_schema.tables where table_name=%s)", ('counters',))
        self.has_counters = cur.fetchone()[0]

        if not self.has_counters:
            logger.info('Counters table not found, assuming pre-0.6 database schema (no HOTP support)')

        self.locks = {}

    def get_user_state(self, user):

        userid = get_user_id(self.conn, user)

        state = totpcgi.GAUserState()

        logger.debug('Creating advisory lock for userid=%s' % userid)
        
        cur = self.conn.cursor()
        cur.execute('SELECT pg_advisory_lock(%s)', (userid,))
        self.locks[user] = userid 

        cur.execute('''
            SELECT timestamp, success
              FROM timestamps
             WHERE userid = %s''', (userid,))

        for (timestamp, success) in cur.fetchall():
            if success:
                state.success_timestamps.append(timestamp)
            else:
                state.fail_timestamps.append(timestamp)

        cur.execute('''
            SELECT token
              FROM used_scratch_tokens
             WHERE userid = %s''', (userid,))

        for (token,) in cur.fetchall():
            state.used_scratch_tokens.append(token)

        # Now try to load counter info, if we have that table
        if self.has_counters:
            cur.execute('''
                SELECT counter
                  FROM counters
                 WHERE userid = %s''', (userid,))

            row = cur.fetchone()
            if row and row[0] >= 0:
                state.counter = row[0]

        return state

    def update_user_state(self, user, state):
        logger.debug('Writing new state for user %s' % user)

        if user not in self.locks.keys():
            raise totpcgi.UserStateError("%s's pg lock has gone away!" % user)

        userid = self.locks[user]

        cur = self.conn.cursor()

        cur.execute('DELETE FROM timestamps WHERE userid=%s', (userid,))
        cur.execute('DELETE FROM used_scratch_tokens WHERE userid=%s', (userid,))

        for timestamp in state.fail_timestamps:
            cur.execute('''
                INSERT INTO timestamps (userid, success, timestamp)
                     VALUES (%s, %s, %s)''', (userid, False, timestamp))

        for timestamp in state.success_timestamps:
            cur.execute('''
                INSERT INTO timestamps (userid, success, timestamp)
                     VALUES (%s, %s, %s)''', (userid, True, timestamp))

        for token in state.used_scratch_tokens:
            cur.execute('''
                INSERT INTO used_scratch_tokens (userid, token)
                     VALUES (%s, %s)''', (userid, token))

        if state.counter >= 0 and self.has_counters:
            cur.execute('DELETE FROM counters WHERE userid=%s', (userid,))
            cur.execute('''
                INSERT INTO counters (userid, counter)
                     VALUES (%s, %s)''', (userid, state.counter))

        logger.debug('Unlocking advisory lock for userid=%s' % userid)
        cur.execute('SELECT pg_advisory_unlock(%s)', (userid,))

        self.conn.commit()

        del self.locks[user]

    def delete_user_state(self, user):
        cur = self.conn.cursor()
        logger.debug('Deleting state records for user=%s' % user)

        userid = get_user_id(self.conn, user)

        cur.execute('''
            DELETE FROM timestamps
                  WHERE userid=%s''' % (userid,))
        cur.execute('''
            DELETE FROM used_scratch_tokens
                  WHERE userid=%s''' % (userid,))

        if self.has_counters:
            cur.execute('''
                DELETE FROM counters
                      WHERE userid=%s''' % (userid,))

        # If there are no pincodes or secrets entries, then we may as well
        # delete the user record.
        cur.execute('SELECT True FROM pincodes WHERE userid=%s', (userid,))
        if not cur.fetchone():
            cur.execute('SELECT True FROM secrets WHERE userid=%s', (userid,))
            if not cur.fetchone():
                logger.debug('No entries left for user=%s, deleting' % user)
                try:
                    cur.execute('DELETE FROM users WHERE userid=%s', (userid,))
                except psycopg2.ProgrammingError:
                    # we may not have permissions, so ignore this failure.
                    pass

        self.conn.commit()


class GASecretBackend(totpcgi.backends.GASecretBackend):
    def __init__(self, connect_string):
        totpcgi.backends.GASecretBackend.__init__(self)
        logger.debug('Using PGSQL Secrets backend')

        logger.debug('Establishing connection to the database')
        self.conn = db_connect(connect_string)

        logger.debug('Checking if we have the counters table')
        cur = self.conn.cursor()
        cur.execute("select exists(select * from information_schema.tables where table_name=%s)", ('counters',))
        self.has_counters = cur.fetchone()[0]

        if not self.has_counters:
            logger.info('Counters table not found, assuming pre-0.6 database schema (no HOTP support)')

    def get_user_secret(self, user, pincode=None):
        cur = self.conn.cursor()

        logger.debug('Querying DB for user %s' % user)

        cur.execute('''
            SELECT s.secret, 
                   s.rate_limit_times, 
                   s.rate_limit_seconds, 
                   s.window_size
              FROM secrets AS s 
              JOIN users AS u USING (userid)
             WHERE u.username = %s''', (user,))
        row = cur.fetchone()

        if not row:
            raise totpcgi.UserNotFound('no secrets record for %s' % user)

        (secret, rate_limit_times, rate_limit_seconds, window_size) = row

        using_encrypted_secret = False
        if secret.find('aes256+hmac256') == 0 and pincode is not None:
            secret = totpcgi.utils.decrypt_secret(secret, pincode)
            using_encrypted_secret = True
        
        gaus = totpcgi.GAUserSecret(secret)
        if rate_limit_times is not None and rate_limit_seconds is not None:
            gaus.rate_limit = (rate_limit_times, rate_limit_seconds)

        if window_size is not None:
            gaus.window_size = window_size

        logger.debug('Querying DB for counter info for %s' % user)
        # Now try to load counter info, if we have that table
        if self.has_counters:
            cur.execute('''
                SELECT c.counter
                  FROM counters AS c
                  JOIN users AS u USING (userid)
                 WHERE u.username = %s''', (user,))

            row = cur.fetchone()
            if row:
                gaus.set_hotp(row[0])

        # Not loading scratch tokens if using encrypted secret
        if using_encrypted_secret:
            return gaus

        logger.debug('Querying DB for scratch tokens for %s' % user)

        cur.execute('''
            SELECT st.token
              FROM scratch_tokens AS st
              JOIN users AS u USING (userid)
             WHERE u.username = %s''', (user,))
        
        for (token,) in cur.fetchall():
            gaus.scratch_tokens.append(token)

        return gaus

    def save_user_secret(self, user, gaus, pincode=None):
        cur = self.conn.cursor()

        self._delete_user_secret(user)

        userid = get_user_id(self.conn, user)

        secret = gaus.otp.secret

        if pincode is not None:
            secret = totpcgi.utils.encrypt_secret(secret, pincode)

        cur.execute('''
            INSERT INTO secrets 
                        (userid, secret, rate_limit_times,
                         rate_limit_seconds, window_size)
                 VALUES (%s, %s, %s, %s, %s)''', 
                    (userid, secret, gaus.rate_limit[0], gaus.rate_limit[1], gaus.window_size))

        for token in gaus.scratch_tokens:
            cur.execute('''
                    INSERT INTO scratch_tokens
                                (userid, token)
                         VALUES (%s, %s)''', (userid, token,))

        self.conn.commit()

    def _delete_user_secret(self, user):
        userid = get_user_id(self.conn, user)

        cur = self.conn.cursor()
        cur.execute('''
            DELETE FROM secrets
                  WHERE userid=%s''', (userid,))
        cur.execute('''
            DELETE FROM scratch_tokens
                  WHERE userid=%s''', (userid,))

    def delete_user_secret(self, user):
        self._delete_user_secret(user)
        self.conn.commit()


class GAPincodeBackend(totpcgi.backends.GAPincodeBackend):
    def __init__(self, connect_string):
        totpcgi.backends.GAPincodeBackend.__init__(self)
        logger.debug('Using PGSQL Pincodes backend')

        logger.debug('Establishing connection to the database')
        self.conn = db_connect(connect_string)
        
    def verify_user_pincode(self, user, pincode):
        cur = self.conn.cursor()

        logger.debug('Querying DB for user %s' % user)

        cur.execute('''
            SELECT p.pincode
              FROM pincodes AS p
              JOIN users AS u USING (userid)
             WHERE u.username = %s''', (user,))

        row = cur.fetchone()

        if not row:
            raise totpcgi.UserNotFound('no pincodes record for user %s' % user)

        (hashcode,) = row

        return self._verify_by_hashcode(pincode, hashcode)

    def _delete_user_hashcode(self, user):
        userid = get_user_id(self.conn, user)

        cur = self.conn.cursor()
        cur.execute('''
            DELETE FROM pincodes 
                  WHERE userid=%s''', (userid,))
        
    def save_user_hashcode(self, user, hashcode, makedb=False):
        self._delete_user_hashcode(user)

        userid = get_user_id(self.conn, user)

        cur = self.conn.cursor()

        cur.execute('''
            INSERT INTO pincodes
                        (userid, pincode)
                 VALUES (%s, %s)''', (userid, hashcode,))

        self.conn.commit()

    def delete_user_hashcode(self, user):
        self._delete_user_hashcode(user)
        self.conn.commit()
########NEW FILE########
__FILENAME__ = utils
##
# Copyright (C) 2012 by Konstantin Ryabitsev and contributors
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#

import os
import base64
import hashlib
import hmac
import logging

import string
import struct

import totpcgi

logger = logging.getLogger('totpcgi')

from Crypto.Cipher import AES
from passlib.utils.pbkdf2 import pbkdf2

AES_BLOCK_SIZE = 16
KDF_ITER = 2000
SALT_SIZE = 32
KEY_SIZE = 32


def hash_pincode(pincode, algo='bcrypt'):
    if algo not in ('bcrypt', 'sha256', 'sha512', 'md5'):
        raise ValueError('Unsupported algorithm: %s' % algo)

    import passlib.hash

    # we stick to 5000 rounds for uniform compatibility
    # if you want higher computational cost, just use bcrypt
    if algo == 'sha256':
        return passlib.hash.sha256_crypt.encrypt(pincode, rounds=5000)

    if algo == 'sha512':
        return passlib.hash.sha512_crypt.encrypt(pincode, rounds=5000)

    if algo == 'md5':
        # really? Okay.
        return passlib.hash.md5_crypt.encrypt(pincode)

    return passlib.hash.bcrypt.encrypt(pincode)


def generate_secret(rate_limit=(3, 30), window_size=3, scratch_tokens=5, bs=80):
    # os.urandom expects bytes, so we divide by 8
    secret = base64.b32encode(os.urandom(bs/8))

    gaus = totpcgi.GAUserSecret(secret)

    gaus.rate_limit = rate_limit
    gaus.window_size = window_size

    for i in xrange(scratch_tokens):
        token = string.zfill(struct.unpack('I', os.urandom(4))[0], 8)[-8:]
        gaus.scratch_tokens.append(token)

    return gaus


def encrypt_secret(data, pincode):
    salt = os.urandom(SALT_SIZE)

    # derive a twice-long key from pincode
    key = pbkdf2(pincode, salt, KDF_ITER, KEY_SIZE*2, prf='hmac-sha256')

    # split the key in two, one used for AES, another for HMAC
    aes_key = key[:KEY_SIZE]
    hmac_key = key[KEY_SIZE:]

    pad = AES_BLOCK_SIZE - len(data) % AES_BLOCK_SIZE
    data += pad * chr(pad)
    iv_bytes = os.urandom(AES_BLOCK_SIZE)
    cypher = AES.new(aes_key, AES.MODE_CBC, iv_bytes)
    data = iv_bytes + cypher.encrypt(data)
    sig = hmac.new(hmac_key, data, hashlib.sha256).digest()

    # jab it all together in a base64-encrypted format
    b64str = ('aes256+hmac256$' 
              + base64.b64encode(salt).replace('\n', '') + '$'
              + base64.b64encode(data+sig).replace('\n', ''))

    logger.debug('Encrypted secret: %s' % b64str)

    return b64str


def decrypt_secret(b64str, pincode):
    # split the secret into components
    try:
        (scheme, salt, ciphertext) = b64str.split('$')

        salt = base64.b64decode(salt)
        ciphertext = base64.b64decode(ciphertext)

    except (ValueError, TypeError):
        raise totpcgi.UserSecretError('Failed to parse encrypted secret')

    key = pbkdf2(pincode, salt, KDF_ITER, KEY_SIZE*2, prf='hmac-sha256')

    aes_key = key[:KEY_SIZE]
    hmac_key = key[KEY_SIZE:]

    sig_size = hashlib.sha256().digest_size
    sig = ciphertext[-sig_size:]
    data = ciphertext[:-sig_size]

    # verify hmac sig first
    if hmac.new(hmac_key, data, hashlib.sha256).digest() != sig:
        raise totpcgi.UserSecretError('Failed to verify hmac!')

    iv_bytes = data[:AES_BLOCK_SIZE]
    data = data[AES_BLOCK_SIZE:]

    cypher = AES.new(aes_key, AES.MODE_CBC, iv_bytes)
    data = cypher.decrypt(data)
    secret = data[:-ord(data[-1])]

    logger.debug('Decryption successful')

    return secret

########NEW FILE########
