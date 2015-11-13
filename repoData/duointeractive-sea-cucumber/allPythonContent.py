__FILENAME__ = backend
"""
This module contains the SESBackend class, which is what you'll want to set in
your settings.py::

    EMAIL_BACKEND = 'seacucumber.backend.SESBackend'
"""

from django.core.mail.backends.base import BaseEmailBackend
from seacucumber.tasks import SendEmailTask


class SESBackend(BaseEmailBackend):
    """
    A Django Email backend that uses Amazon's Simple Email Service.
    """

    def send_messages(self, email_messages):
        """
        Sends one or more EmailMessage objects and returns the number of
        email messages sent.

        :param EmailMessage email_messages: A list of Django's EmailMessage
            object instances.
        :rtype: int
        :returns: The number of EmailMessage objects that were successfully
            queued up. Note that these are not in a state where we can
            guarantee delivery just yet.
        """

        num_sent = 0
        for message in email_messages:
            # Hand this off to a celery task.
            SendEmailTask.delay(
                message.from_email,
                message.recipients(),
                message.message().as_string().decode('utf8'),
            )
            num_sent += 1
        return num_sent

########NEW FILE########
__FILENAME__ = ses_address
"""
Handles management of SES email addresses.
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from seacucumber.util import get_boto_ses_connection

class Command(BaseCommand):
    """
    This is a completely optional command used to manage the user's SES
    email addresses. Make sure to have 'seacucumber' in INSTALLED_APPS, or this
    won't be available.
    """
    args = "<action> [<email address>]"
    help = "Manages SES emails. <action> may be one of the following:\n"\
           "  verify <email>   Sends a verification request for an address.\n"\
           "  list             Lists all fully verified addresses.\n"\
           "  delete <email>   Deletes an address from your SES account.\n\n"\
           "Examples:\n"\
           "  ./manage.py ses_address verify some@addres.com\n"\
           "  ./manage.py ses_address list\n"\
           "  ./manage.py ses_address delete some@address.com"

    # <action> must be one of the following.
    valid_actions = ['verify', 'list', 'delete']

    def handle(self, *args, **options):
        """
        Parses/validates, and breaks off into actions.
        """
        if len(args) < 1:
            raise CommandError("Please specify an action. See --help.")

        action = args[0]
        email = None

        if action not in self.valid_actions:
            message = "Invalid action: %s" % action
            raise CommandError(message)

        if action in ['verify', 'delete']:
            if len(args) < 2:
                message = "Please specify an email address to %s." % action
                raise CommandError(message)

            email = args[1]

            if not email or not self._is_valid_email(email):
                message = "Invalid email address provided: %s" % email
                raise CommandError(message)

        # Hand this off to the action routing method.
        self._route_action(action, email)

    def _route_action(self, action, email):
        """
        Given an action and an email (can be None), figure out what to do
        with the validated inputs.

        :param str action: The action. Must be one of self.valid_actions.
        :type email: str or None
        :param email: Either an email address, or None if the action doesn't
            need an email address.
        """
        connection = self._get_ses_connection()
        if action == "verify":
            connection.verify_email_address(email)
            print("A verification email has been sent to %s." % email)
        elif action == "delete":
            connection.delete_verified_email_address(email)
            print("You have deleted %s from your SES account." % email)
        elif action == "list":
            verified_result = connection.list_verified_email_addresses()
            if len(verified_result.VerifiedEmailAddresses) > 0:
                print("The following emails have been fully verified on your "\
                      "Amazon SES account:")
                for vemail in verified_result.VerifiedEmailAddresses:
                    print ("  %s" % vemail)
            else:
                print("Your account has no fully verified email addresses yet.")

    def _get_ses_connection(self):
        """
        Convenience method for returning a SES connection, and handling any
        errors that may appear.

        :rtype: boto.ses.SESConnection
        """
        try:
            connection = get_boto_ses_connection()
            return connection
        except:
            raise Exception("Could not connect to Amazon SES service")

    def _is_valid_email(self, email):
        """
        Given an email address, make sure that it is well-formed.

        :param str email: The email address to validate.
        :rtype: bool
        :returns: True if the email address is valid, False if not.
        """
        try:
            validate_email(email)
            return True
        except ValidationError:
            return False

########NEW FILE########
__FILENAME__ = ses_usage
"""
Shows some usage levels and limits for the last and previous 24 hours.
"""
import datetime
from django.core.management.base import BaseCommand
from seacucumber.util import get_boto_ses_connection

class Command(BaseCommand):
    """
    This command shows some really vague usage and quota stats from SES.
    """
    help = "Shows SES usage and quota limits."

    def handle(self, *args, **options):
        """
        Renders the output by piecing together a few methods that do the
        dirty work.
        """
        # AWS SES connection, which can be re-used for each query needed.
        conn = get_boto_ses_connection()
        self._print_quota(conn)
        self._print_daily_stats(conn)
           
    def _print_quota(self, conn):
        """
        Prints some basic quota statistics.
        """
        quota = conn.get_send_quota()
        quota = quota['GetSendQuotaResponse']['GetSendQuotaResult']
        
        print "--- SES Quota ---"
        print "  24 Hour Quota: %s" % quota['Max24HourSend']
        print "  Sent (Last 24 hours): %s" % quota['SentLast24Hours']
        print "  Max sending rate: %s/sec" % quota['MaxSendRate']
        
    def _print_daily_stats(self, conn):
        """
        Prints a Today/Last 24 hour stats section.
        """
        stats = conn.get_send_statistics()
        stats = stats['GetSendStatisticsResponse']['GetSendStatisticsResult']
        stats = stats['SendDataPoints']
        
        today = datetime.date.today()
        current_day = {'HeaderName': 'Current Day: %s/%s' % (today.month, 
                                                             today.day)}
        prev_day = {'HeaderName': 'Past two weeks'}
        
        for data_point in stats:
            if self._is_data_from_today(data_point):
                day_dict = current_day
            else:
                day_dict = prev_day
                
            self._update_day_dict(data_point, day_dict)      

        for day in [current_day, prev_day]:
            print "--- %s ---" % day.get('HeaderName', 0)
            print "  Delivery attempts: %s" % day.get('DeliveryAttempts', 0)
            print "  Bounces: %s" % day.get('Bounces', 0)
            print "  Rejects: %s" % day.get('Rejects', 0)
            print "  Complaints: %s" % day.get('Complaints', 0)
        
    def _is_data_from_today(self, data_point):
        """
        Takes a DataPoint from SESConnection.get_send_statistics() and returns
        True if it is talking about the current date, False if not.
        
        :param dict data_point: The data point to consider.
        :rtype: bool
        :returns: True if this data_point is for today, False if not (probably
            yesterday).
        """
        today = datetime.date.today()
        
        raw_timestr = data_point['Timestamp']
        dtime = datetime.datetime.strptime(raw_timestr, '%Y-%m-%dT%H:%M:%SZ')
        return today.day == dtime.day
    
    def _update_day_dict(self, data_point, day_dict):
        """
        Helper method for :meth:`_print_daily_stats`. Given a data point and
        the correct day dict, update attribs on the dict with the contents
        of the data point.
        
        :param dict data_point: The data point to add to the day's stats dict.
        :param dict day_dict: A stats-tracking dict for a 24 hour period.
        """
        for topic in ['Bounces', 'Complaints', 'DeliveryAttempts', 'Rejects']:
            day_dict[topic] = day_dict.get(topic, 0) + int(data_point[topic])
########NEW FILE########
__FILENAME__ = models
"""
Need this here to make Django happy, even if we don't have any models.
"""

########NEW FILE########
__FILENAME__ = tasks
"""
Supporting celery tasks go in this module. The primarily interesting one is
SendEmailTask, which handles sending a single Django EmailMessage object.
"""

import logging

from django.conf import settings
from celery.task import Task
from boto.ses.exceptions import SESAddressBlacklistedError, SESDomainEndsWithDotError, SESLocalAddressCharacterError, SESIllegalAddressError

from seacucumber.util import get_boto_ses_connection, dkim_sign

logger = logging.getLogger(__name__)


class SendEmailTask(Task):
    """
    Sends an email through Boto's SES API module.
    """
    def __init__(self):
        self.max_retries = getattr(settings, 'CUCUMBER_MAX_RETRIES', 60)
        self.default_retry_delay = getattr(settings, 'CUCUMBER_RETRY_DELAY', 60)
        self.rate_limit = getattr(settings, 'CUCUMBER_RATE_LIMIT', 1)
        # A boto.ses.SESConnection object, after running _open_ses_conn().
        self.connection = None

    def run(self, from_email, recipients, message):
        """
        This does the dirty work. Connects to Amazon SES via boto and fires
        off the message.

        :param str from_email: The email address the message will show as
            originating from.
        :param list recipients: A list of email addresses to send the
            message to.
        :param str message: The body of the message.
        """
        self._open_ses_conn()
        try:
            # We use the send_raw_email func here because the Django
            # EmailMessage object we got these values from constructs all of
            # the headers and such.
            self.connection.send_raw_email(
                source=from_email,
                destinations=recipients,
                raw_message=dkim_sign(message),
            )
        except SESAddressBlacklistedError, exc:
            # Blacklisted users are those which delivery failed for in the
            # last 24 hours. They'll eventually be automatically removed from
            # the blacklist, but for now, this address is marked as
            # undeliverable to.
            logger.warning(
                'Attempted to email a blacklisted user: %s' % recipients,
                exc_info=exc,
                extra={'trace': True}
            )
            return False
        except SESDomainEndsWithDotError, exc:
            # Domains ending in a dot are simply invalid.
            logger.warning(
                'Invalid recipient, ending in dot: %s' % recipients,
                exc_info=exc,
                extra={'trace': True}
            )
            return False
        except SESLocalAddressCharacterError, exc:
            # Invalid character, usually in the sender "name".
            logger.warning(
                'Local address contains control or whitespace: %s' % recipients,
                exc_info=exc,
                extra={'trace': True}
            )
            return False
        except SESIllegalAddressError, exc:
            # A clearly mal-formed address.
            logger.warning(
                'Illegal address: %s' % recipients,
                exc_info=exc,
                extra={'trace': True}
            )
            return False
        except Exception, exc:
            # Something else happened that we haven't explicitly forbade
            # retry attempts for.
            #noinspection PyUnresolvedReferences
            logger.error(
                'Something went wrong; retrying: %s' % recipients,
                exc_info=exc,
                extra={'trace': True}
            )
            self.retry(exc=exc)
        else:
            logger.info('An email has been successfully sent: %s' % recipients)

        # We shouldn't ever block long enough to see this, but here it is
        # just in case (for debugging?).
        return True

    def _open_ses_conn(self):
        """
        Create a connection to the AWS API server. This can be reused for
        sending multiple emails.
        """
        if self.connection:
            return

        self.connection = get_boto_ses_connection()

########NEW FILE########
__FILENAME__ = util
"""
Various utility functions.
"""

from django.conf import settings
import boto

# dkim isn't required, but we'll use it if we have it.
try:
    import dkim
    HAS_DKIM = True
except ImportError:
    HAS_DKIM = False

DKIM_DOMAIN = getattr(settings, "DKIM_DOMAIN", None)
DKIM_PRIVATE_KEY = getattr(settings, 'DKIM_PRIVATE_KEY', None)
DKIM_SELECTOR = getattr(settings, 'DKIM_SELECTOR', 'ses')
DKIM_HEADERS = getattr(settings, 'DKIM_HEADERS', ('From', 'To', 'Cc', 'Subject'))


def get_boto_ses_connection():
    """
    Shortcut for instantiating and returning a boto SESConnection object.

    :rtype: boto.ses.SESConnection
    :returns: A boto SESConnection object, from which email sending is done.
    """

    access_key_id = getattr(
        settings, 'CUCUMBER_SES_ACCESS_KEY_ID',
        getattr(settings, 'AWS_ACCESS_KEY_ID', None))
    access_key = getattr(
        settings, 'CUCUMBER_SES_SECRET_ACCESS_KEY',
        getattr(settings, 'AWS_SECRET_ACCESS_KEY', None))

    return boto.connect_ses(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=access_key,
    )


def dkim_sign(message):
    """
    :returns: A signed email message if dkim package and settings are available.
    """

    if not HAS_DKIM:
        return message

    if not (DKIM_DOMAIN and DKIM_PRIVATE_KEY):
        return message

    sig = dkim.sign(
        message,
        DKIM_SELECTOR,
        DKIM_DOMAIN,
        DKIM_PRIVATE_KEY,
        include_headers=DKIM_HEADERS)
    return sig + message

########NEW FILE########
