__FILENAME__ = celery
from __future__ import absolute_import

from celery import Celery
from ConfigParser import ConfigParser
from datetime import timedelta
from os import environ
from os import path


def load_ini():
    selected_ini = environ.get('BOOKIE_INI', 'bookie.ini')
    if selected_ini is None:
        msg = "Please set the BOOKIE_INI env variable!"
        raise Exception(msg)

    cfg = ConfigParser()
    ini_path = path.join(
        path.dirname(
            path.dirname(
                path.dirname(__file__)
            )
        ),
        selected_ini
    )
    cfg.readfp(open(ini_path))

    # Hold onto the ini config.
    return dict(cfg.items('app:bookie', raw=True))


INI = load_ini()


celery = Celery(
    'bookie.bcelery',
    broker=INI.get('celery_broker'),
    include=['bookie.bcelery.tasks'])

# Optional configuration, see the application user guide.
celery.conf.update(
    CELERY_TASK_RESULT_EXPIRES=3600,
    CELERY_RESULT_BACKEND=INI.get('celery_broker'),
    CELERYBEAT_SCHEDULE={
        'daily_stats': {
            'task': 'bookie.bcelery.tasks.daily_stats',
            'schedule': timedelta(seconds=24*60*60),
        },
        'hourly_stats': {
            'task': 'bookie.bcelery.tasks.hourly_stats',
            'schedule': timedelta(seconds=60*60),
        },
        'fetch_unfetched': {
            'task': 'bookie.bcelery.tasks.fetch_unfetched_bmark_content',
            'schedule': timedelta(seconds=60),
        },
    }
)

if __name__ == '__main__':
    celery.start()

########NEW FILE########
__FILENAME__ = tasks
from __future__ import absolute_import
from celery.utils.log import get_task_logger

from bookie.bcelery.celery import celery


import transaction
try:
    from whoosh.store import LockError
except ImportError:
    from whoosh.index import LockError
from whoosh.writing import IndexingError

from bookie.lib.importer import Importer
from bookie.lib.readable import ReadUrl
from bookie.models import initialize_sql
from bookie.models import Bmark
from bookie.models import BmarkMgr
from bookie.models import Readable
from bookie.models.auth import UserMgr
from bookie.models.stats import StatBookmarkMgr
from bookie.models.queue import ImportQueueMgr

from .celery import load_ini

INI = load_ini()
initialize_sql(INI)

logger = get_task_logger(__name__)


@celery.task(ignore_result=True)
def hourly_stats():
    """Hourly we want to run a series of numbers to track

    Currently we're monitoring:
    - Total number of bookmarks in the system
    - Unique number of urls in the system
    - Total number of tags in the system

    """
    count_total.delay()
    count_unique.delay()
    count_tags.delay()


@celery.task(ignore_result=True)
def daily_stats():
    """Daily we want to run a series of numbers to track

    Currently we're monitoring:
    - Total number of bookmarks for each user in the system

    """
    count_total_each_user.delay()
    delete_non_activated_account.delay()


@celery.task(ignore_result=True)
def delete_non_activated_account():
    """Delete user accounts which are not verified since
    30 days of signup"""
    trans = transaction.begin()
    UserMgr.delete_non_activated_account()
    trans.commit()


@celery.task(ignore_result=True)
def count_total():
    """Count the total number of bookmarks in the system"""
    trans = transaction.begin()
    StatBookmarkMgr.count_total_bookmarks()
    trans.commit()


@celery.task(ignore_result=True)
def count_total_each_user():
    """Count the total number of bookmarks for each user in the system"""
    trans = transaction.begin()
    user_list = UserMgr.get_list(active=True)
    for user in user_list:
        StatBookmarkMgr.count_user_bookmarks(user.username)
    trans.commit()


@celery.task(ignore_result=True)
def count_unique():
    """Count the unique number of bookmarks/urls in the system"""
    trans = transaction.begin()
    StatBookmarkMgr.count_unique_bookmarks()
    trans.commit()


@celery.task(ignore_result=True)
def count_tags():
    """Count the total number of tags in the system"""
    trans = transaction.begin()
    StatBookmarkMgr.count_total_tags()
    trans.commit()


@celery.task(ignore_result=True)
def delete_all_bookmarks(username):
    """ Deletes all bookmarks for the current user"""
    trans = transaction.begin()
    BmarkMgr.delete_all_bookmarks(username)
    trans.commit()


@celery.task()
def importer_process(import_id):
    """Start the process of running the import.

    We load it, mark it as running, and begin begin a task to process.

    :param import_id: import id we need to pull and work on

    """
    trans = transaction.begin()
    imp = ImportQueueMgr.get(import_id)
    import_id = imp.id

    # Log that we've scheduled it
    logger.info("IMPORT: SCHEDULED for {0}.".format(imp.username))
    # We need to mark that it's running to prevent it getting picked up
    # again.
    imp.mark_running()
    trans.commit()
    importer_process_worker.delay(import_id)


@celery.task()
def importer_process_worker(import_id):
    """Do the real import work

    :param import_id: import id we need to pull and work on

    """
    trans = transaction.begin()
    import_job = ImportQueueMgr.get(import_id)
    logger.info("IMPORT: RUNNING for {username}".format(**dict(import_job)))

    try:
        # process the file using the import script
        import_file = open(import_job.file_path)
        importer = Importer(
            import_file,
            import_job.username)
        importer.process()

        # Processing kills off our transaction so we need to start a new one
        # to update that our import is complete.
        trans = transaction.begin()
        import_job = ImportQueueMgr.get(import_id)
        import_job.mark_done()
        user = UserMgr.get(username=import_job.username)
        from bookie.lib.message import UserImportSuccessMessage
        msg = UserImportSuccessMessage(
            user.email,
            'Bookie: Your requested import has completed.',
            INI)
        msg.send({
            'username': import_job.username,
        })

        logger.info(
            "IMPORT: COMPLETE for {username}".format(**dict(import_job)))
        trans.commit()

    except Exception, exc:
        # We need to log this and probably send an error email to the
        # admin
        from bookie.lib.message import ImportFailureMessage
        from bookie.lib.message import UserImportFailureMessage

        trans = transaction.begin()
        import_job = ImportQueueMgr.get(import_id)
        user = UserMgr.get(username=import_job.username)

        msg = ImportFailureMessage(
            INI.get('email.from'),
            'Import failure!',
            INI)
        msg.send({
            'username': import_job.username,
            'file_path': import_job.file_path,
            'exc': str(exc)
        })

        # Also send an email to the user that their import failed.
        msg = UserImportFailureMessage(
            user.email,
            'Bookie: We are sorry, your import failed.',
            INI)
        msg.send({
            'username': import_job.username,
            'exc': str(exc)
        })

        logger.error(exc)
        logger.error(str(exc))
        import_job.mark_error()
        logger.info(
            "IMPORT: ERROR for {username}".format(**dict(import_job)))
        logger.info(exc)
        trans.commit()


@celery.task(ignore_result=True)
def email_signup_user(email, msg, settings, message_data):
    """Do the real import work

    :param iid: import id we need to pull and work on

    """
    from bookie.lib.message import ActivationMsg
    msg = ActivationMsg(email, msg, settings)
    status = msg.send(message_data)
    if status == 4:
        from bookie.lib.applog import SignupLog
        trans = transaction.begin()
        SignupLog(SignupLog.ERROR,
                  'Could not send smtp email to signup: ' + email)
        trans.commit()


class BookmarkNotFoundException(Exception):
    pass


@celery.task(ignore_result=True, default_retry_delay=30)
def fulltext_index_bookmark(bid, content):
    """Insert bookmark data into the fulltext index."""
    b = Bmark.query.get(bid)

    if not b:
        logger.error('Could not load bookmark to fulltext index: ' + str(bid))
        fulltext_index_bookmark.retry(exc=BookmarkNotFoundException())
    else:
        from bookie.models.fulltext import get_writer
        logger.debug('getting writer')
        writer = get_writer()

        if content:
            found_content = content
        elif b.readable:
            found_content = b.readable.clean_content
        else:
            found_content = u""

        try:
            writer.update_document(
                bid=unicode(b.bid),
                description=b.description if b.description else u"",
                extended=b.extended if b.extended else u"",
                tags=b.tag_str if b.tag_str else u"",
                readable=found_content,
            )
            writer.commit()
            logger.debug('writer commit')
        except (IndexingError, LockError), exc:
            # There was an issue saving into the index.
            logger.error(exc)
            logger.warning('sending back to the queue')
            # This should send the work over to a celery task that will try
            # again in that space.
            writer.cancel()
            fulltext_index_bookmark.retry(exc=exc, countdown=60)


@celery.task(ignore_result=True)
def reindex_fulltext_allbookmarks(sync=False):
    """Rebuild the fulltext index with all bookmarks."""
    logger.debug("Starting freshen of fulltext index.")

    bookmarks = Bmark.query.all()

    for b in bookmarks:
        if sync:
            fulltext_index_bookmark(b.bid, None)
        else:
            fulltext_index_bookmark.delay(b.bid, None)


@celery.task(ignore_result=True)
def fetch_unfetched_bmark_content(ignore_result=True):
    """Check the db for any unfetched content. Fetch and index."""
    logger.info("Checking for unfetched bookmarks")

    url_list = Bmark.query.outerjoin(
        Readable, Bmark.readable).\
        filter(Readable.imported.is_(None)).all()

    for bmark in url_list:
        fetch_bmark_content.delay(bmark.bid)


@celery.task(ignore_result=True)
def fetch_bmark_content(bid):
    """Given a bookmark, fetch its content and index it."""
    trans = transaction.begin()

    if not bid:
        raise Exception('missing bookmark id')
    bmark = Bmark.query.get(bid)
    if not bmark:
        raise Exception('Bookmark not found: ' + str(bid))
    hashed = bmark.hashed

    try:
        read = ReadUrl.parse(hashed.url)
    except ValueError:
        # We hit this where urllib2 choked trying to get the protocol type of
        # this url to fetch it.
        logger.error('Could not parse url: ' + hashed.url)
        logger.error('exc')
        read = None

    if read:
        logger.debug(read)
        logger.debug(read.content)

        logger.debug("%s: %s %d %s %s" % (
            hashed.hash_id,
            read.url,
            len(read.content) if read.content else -1,
            read.is_error(),
            read.status_message))

        if not read.is_image():
            if not bmark.readable:
                bmark.readable = Readable()

            bmark.readable.content = read.content
        else:
            if not bmark.readable:
                bmark.readable = Readable()
            bmark.readable.content = None

        # set some of the extra metadata
        bmark.readable.content_type = read.content_type
        bmark.readable.status_code = read.status
        bmark.readable.status_message = read.status_message
        trans.commit()
        fulltext_index_bookmark.delay(
            bid,
            read.content if read else None)
    else:
        logger.error(
            'No readable record for bookmark: ',
            str(bid), str(bmark.hashed.url))

        # There was a failure reading the thing.
        bmark.readable = Readable()
        bmark.readable.status = '900'
        bmark.readable.status_message = (
            'No readable record '
            'during existing processing')
        trans.commit()

########NEW FILE########
__FILENAME__ = access
"""Handle auth and authz activities in bookie"""
import logging

from decorator import decorator
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.request import Request
from pyramid.security import unauthenticated_userid

from bookie.models.auth import UserMgr

LOG = logging.getLogger(__name__)


class AuthHelper(object):
    """Manage the inner workings of authorizing things"""

    @staticmethod
    def check_api(submitted_key, users_key):
        """Verify the api key is valid"""
        if users_key != submitted_key:
            return False
        else:
            return True

    @staticmethod
    def check_login(request, username=None):
        """Check that the user is logged in correctly

        :param username: a username to make sure the current user is in fact

        """
        if request.user is None:
            return False

        # if we have a username we're told to check against, make sure the
        # username matches
        if username is not None and username != request.user.username:
            return False

        return True

    @staticmethod
    def not_valid(request, redirect=None):
        """Handle the Forbidden exception unless redirect is there

        The idea is that if there's a redirect we shoot them to the login form
        instead

        """
        if redirect is None:
            raise HTTPForbidden('Deactivated Account')
        else:
            raise HTTPFound(location=request.route_url(redirect))


class ReqOrApiAuthorize(object):
    """A context manager that works with either Api key or logged in user"""

    def __init__(self, request, api_key, user_acct, username=None,
                 redirect=None):
        self.request = request
        self.api_key = api_key
        self.user_acct = user_acct
        self.username = username

        if redirect:
            self.redirect = redirect

    def __enter__(self):
        """Handle the verification side

        Logged in user checked first, then api matching

        """

        # if the user account is not activated then no go
        if not self.user_acct.activated:
            raise HTTPForbidden('Deactivated Account')

        if AuthHelper.check_login(self.request, username=self.username):
            return True

        if AuthHelper.check_api(self.api_key, self.user_acct.api_key):
            return True

        raise HTTPForbidden('Invalid Authorization')

    def __exit__(self, exc_type, exc_value, traceback):
        """No cleanup to do here"""
        pass


class ApiAuthorize(object):
    """Context manager to check if the user is authorized

    use:
        with ApiAuthorize(some_key):
            # do work

    Will return NotAuthorized if it fails

    """

    def __init__(self, user, submitted_key, redirect=None):
        """Create the context manager"""
        self.user = user


class RequestWithUserAttribute(Request):
    @reify
    def user(self):
        # <your database connection, however you get it, the below line
        # is just an example>
        # dbconn = self.registry.settings['dbconn']
        user_id = unauthenticated_userid(self)
        if user_id is not None:
            # this should return None if the user doesn't exist
            # in the database
            user = UserMgr.get(user_id=user_id)
            return user

    def __enter__(self):
        """Verify api key set in constructor"""
        # if the user account is not activated then no go
        if not self.user.activated:
            raise HTTPForbidden('Deactivated Account')

        if not AuthHelper.check_api(self.check_key, self.user.api_key):
            raise HTTPForbidden('Invalid Authorization')

    def __exit__(self, exc_type, exc_value, traceback):
        """No cleanup work to do after usage"""
        pass


class ReqAuthorize(object):
    """Context manager to check if the user is logged in

    use:
        with ReqAuthorize(request):
            # do work

    Will return NotAuthorized if it fails

    """

    def __init__(self, request, username=None, redirect=None):
        """Create the context manager"""
        self.request = request
        self.username = username
        self.redirect = redirect

    def __enter__(self):
        """Verify api key set in constructor"""
        if not AuthHelper.check_login(self.request, self.username):
            raise HTTPForbidden('Invalid Authorization')

    def __exit__(self, exc_type, exc_value, traceback):
        """No cleanup work to do after usage"""
        pass


class api_auth():
    """View decorator to set check the client is permitted

    Since api calls can come from the api via a api_key or a logged in user via
    the website, we need to check/authorize both

    If this is an api call and the api key is valid, stick the user object
    found onto the request.user so that the view can find it there in one
    place.

    """

    def __init__(self, api_field, user_fetcher, admin_only=False, anon=False):
        """
        :param api_field: the name of the data in the request.params and the
                          User object we compare to make sure they match
        :param user_fetcher: a callable that I can give a username to and
                             get back the user object

        :sample: @ApiAuth('api_key', UserMgr.get)

        """
        self.api_field = api_field
        self.user_fetcher = user_fetcher
        self.admin_only = admin_only
        self.anon = anon

    def __call__(self, action_):
        """ Return :meth:`wrap_action` as the decorator for ``action_``. """
        return decorator(self.wrap_action, action_)

    def _check_admin_only(self, request):
        """If admin only, verify current api belongs to an admin user"""
        api_key = request.params.get(self.api_field, None)

        if request.user is None:
            user = self.user_fetcher(api_key=api_key)
        else:
            user = request.user

        if user is not None and user.is_admin:
            request.user = user
            return True

    def wrap_action(self, action_, *args, **kwargs):
        """
        Wrap the controller action ``action_``.

        :param action_: The controller action to be wrapped.

        ``args`` and ``kwargs`` are the positional and named arguments which
        will be passed to ``action_`` when called.

        """
        # check request.user to see if this is a logged in user
        # if so, then make sure it matches the matchdict user

        # request should be the one and only arg to the view function
        request = args[0]
        username = request.matchdict.get('username', None)
        api_key = None

        # if this is admin only, you're either an admin or not
        if self.admin_only:
            if self._check_admin_only(request):
                return action_(*args, **kwargs)
            else:
                request.response.status_int = 403
                return {'error': "Not authorized for request."}

        if request.user is not None:
            if AuthHelper.check_login(request, username):
                # then we're good, this is a valid user for this url
                return action_(*args, **kwargs)

        # get the user the api key belongs to
        if self.api_field in request.params:
            # we've got a request with url params
            api_key = request.params.get(self.api_field, None)
            username = request.params.get('username', username)

        def is_json_auth_request(request):
            if hasattr(request, 'json_body'):
                if self.api_field in request.json_body:
                    return True
            return False

        if is_json_auth_request(request):
            # we've got a ajax request with post data
            api_key = request.json_body.get(self.api_field, None)
            username = request.json_body.get('username', None)

        if username is not None and api_key is not None:
            # now get what this user should be based on the api_key
            request.user = self.user_fetcher(api_key=api_key)

            # if there's a username in the url (rdict) then make sure the user
            # the api belongs to is the same as the url. You can't currently
            # use the api to get info for other users.
            if request.user and request.user.username == username:
                return action_(*args, **kwargs)

        # if this api call accepts anon requests then let it through
        if self.anon:
            return action_(*args, **kwargs)

        # otherwise, we're done, you're not allowed
        request.response.status_int = 403
        return {'error': "Not authorized for request."}

########NEW FILE########
__FILENAME__ = applog
"""
Handle application logging items

Current db model:

id, user, component, status, message, payload, tstamp

"""
import json
import logging
from bookie.models.applog import AppLogMgr

LOG = logging.getLogger(__name__)


class Log(object):
    """Log handler"""

    # status levels
    ERROR = 0
    WARNING = 1
    INFO = 2
    DEBUG = 3

    @staticmethod
    def store(status, message, **kwargs):
        """Store a log item"""
        LogRecord(status, message, **kwargs)


class AuthLog(Log):
    """Store auth specific log items"""
    component = u"AUTH"

    @staticmethod
    def login(username, success, password=None):
        """Store that a user logged into the system"""
        get_status = lambda x: Log.INFO if x else Log.ERROR
        passwd = lambda x: None if password is None else {'password': password}

        status = get_status(success)
        message = u"User {0} attempted to login {1}".format(username,
                                                            success)
        data = {
            'user': username,
            'component': AuthLog.component,
            'payload': passwd(password)
        }

        AuthLog.store(status, message, **data)

    @staticmethod
    def disabled(username):
        """Attempt to log into a disabled account"""
        msg = u"{0} is a disabled user account".format(username)

        data = {
            'user': username,
            'component': AuthLog.component
        }

        AuthLog.store(Log.INFO, msg, **data)

    @staticmethod
    def reactivate(username, success=True, code=None):
        """The account was marked for reactivation"""
        if success:
            msg = u"{0} was reactivated".format(username)
        else:
            msg = u"{0} attempted to reactivate with invalid credentials"
            msg = msg.format(username)

        LOG.debug(msg)
        data = {
            'user': username,
            'component': AuthLog.component,
            'payload': {
                'success': success,
                'code': code,
            }
        }

        AuthLog.store(Log.INFO, msg, **data)


class BmarkLog(Log):
    """Bookmark specific log items"""
    component = u"BMARKS"

    @staticmethod
    def export(for_user, current_user):
        """Note that a user has exported their bookmarks"""
        get_status = lambda x: Log.WARNING if x else Log.INFO

        your_export = False
        if current_user and current_user == for_user:
            your_export = True

        elif current_user is None:
            current_user = "None"

        status = get_status(your_export)
        message = u"User {0} exported the bookmarks for {1}".format(
            current_user, for_user)

        data = {
            'user': current_user,
            'component': BmarkLog.component,
        }

        BmarkLog.store(status, message, **data)


class LogRecord(object):
    """A record in the log"""

    def __init__(self, status, message, **kwargs):
        """A record in the log"""
        kwargs['status'] = status
        kwargs['message'] = message

        # we need to hash down the payload if there is one
        if 'payload' in kwargs and kwargs['payload'] is not None:
            kwargs['payload'] = unicode(
                json.dumps(dict(kwargs.get('payload')))
            )

        AppLogMgr.store(**kwargs)


class SignupLog(object):
    """Signup Log records."""

    def __init__(self, status, message, **kwargs):
        """A record in the log"""
        kwargs['status'] = status
        kwargs['message'] = message

        # we need to hash down the payload if there is one
        if 'payload' in kwargs and kwargs['payload'] is not None:
            kwargs['payload'] = json.dumps(dict(kwargs.get('payload')))

        AppLogMgr.store(**kwargs)

########NEW FILE########
__FILENAME__ = importer
"""Importers for bookmarks"""
import json
import os
import random
import string
import time
import transaction
from datetime import datetime
from dateutil import parser as dateparser
from BeautifulSoup import BeautifulSoup
from lxml import etree
from lxml.etree import XMLSyntaxError

from bookie.lib.urlhash import generate_hash
from bookie.models import (
    BmarkMgr,
    DBSession,
    InvalidBookmark,
)


IMPORTED = u"importer"
COMMIT_SIZE = 25


def store_import_file(storage_dir, username, files):
    # save the file off to the temp storage
    out_dir = "{storage_dir}/{randdir}".format(
        storage_dir=storage_dir,
        randdir=random.choice(string.letters),
    )

    # make sure the directory exists
    # we create it with parents as well just in case
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    out_fname = "{0}/{1}.{2}".format(
        out_dir, username, files.filename)
    out = open(out_fname, 'w')
    out.write(files.file.read())
    out.close()

    return out_fname


class Importer(object):
    """The actual factory object we use for handling imports"""

    def __init__(self, import_io, username=None):
        """work on getting an importer instance"""
        self.file_handle = import_io
        self.username = username

        # we need to get our list of hashes to make sure we check for dupes
        self.hash_list = set([b[0] for b in
                             BmarkMgr.hash_list(username=username)])

    def __new__(cls, *args, **kwargs):
        """Overriding new we return a subclass based on the file content"""
        if DelImporter.can_handle(args[0]):
            return super(Importer, cls).__new__(DelImporter)

        if DelXMLImporter.can_handle(args[0]):
            return super(Importer, cls).__new__(DelXMLImporter)

        if GBookmarkImporter.can_handle(args[0]):
            return super(Importer, cls).__new__(GBookmarkImporter)

        if FBookmarkImporter.can_handle(args[0]):
            return super(Importer, cls).__new__(FBookmarkImporter)

        return super(Importer, cls).__new__(Importer)

    @staticmethod
    def can_handle(file_io):
        """This is meant to be implemented in subclasses"""
        raise NotImplementedError("Please implement this in your importer")

    def process(self, fulltext=None):
        """Meant to be implemented in subclasses"""
        raise NotImplementedError("Please implement this in your importer")

    def save_bookmark(self, url, desc, ext, tags, dt=None):
        """Save the bookmark to the db

        :param url: bookmark url
        :param desc: one line description
        :param ext: extended description/notes
        :param tags: The string of tags to store with this bmark
        :param mark: Instance of Bmark that we're storing to db

        """
        # If a bookmark has the tag "private" then we ignore it to prevent
        # leaking user data.
        if tags and 'private' in tags.lower().split(' '):
            return None

        check_hash = generate_hash(url)

        # We should make sure that this url isn't already bookmarked before
        # adding it...if the hash matches, you must skip!
        if check_hash not in self.hash_list:
            bmark = BmarkMgr.store(
                url,
                self.username,
                desc,
                ext,
                tags,
                dt=dt,
                inserted_by=IMPORTED
            )

            # Add this hash to the list so that we can skip dupes in the
            # same import set.
            self.hash_list.add(check_hash)
            return bmark

        # If we don't store a bookmark then just return None back to the
        # importer.
        return None


class DelImporter(Importer):
    """Process a delicious html file"""

    @staticmethod
    def _is_delicious_format(soup, can_handle, delicious_doctype):
        """A check for if this import files is a delicious format compat file

        Very fragile currently, it makes sure the first line is the doctype.
        Any blank lines before it will cause it to fail

        """
        if (soup.contents and
                soup.contents[0] == delicious_doctype and
                not soup.find('h3')):
            can_handle = True

        return can_handle

    @staticmethod
    def can_handle(file_io):
        """Check if this file is a google bookmarks format file

        In order to check the file we have to read it and check it's content
        type.

        Google Bookmarks and Delicious both have the same content type, but
        they use different formats. We use the fact that Google Bookmarks
        uses <h3> tags and Delicious does not in order to differentiate these
        two formats.
        """
        delicious_doctype = u'DOCTYPE NETSCAPE-Bookmark-file-1'

        soup = BeautifulSoup(file_io)
        can_handle = False
        can_handle = DelImporter._is_delicious_format(soup,
                                                      can_handle,
                                                      delicious_doctype)

        # make sure we reset the file_io object so that we can use it again
        file_io.seek(0)
        return can_handle

    def process(self):
        """Given a file, process it"""
        soup = BeautifulSoup(self.file_handle)
        count = 0

        ids = []
        for tag in soup.findAll('dt'):
            if 'javascript:' in str(tag):
                continue

            # if we have a dd as next sibling, get it's content
            if tag.nextSibling and tag.nextSibling.name == 'dd':
                extended = tag.nextSibling.text
            else:
                extended = u""

            link = tag.a

            # Skip any bookmarks with an attribute of PRIVATE.
            if link.has_key('PRIVATE'):  # noqa
                continue

            import_add_date = float(link['add_date'])

            if import_add_date > 9999999999:
                # Remove microseconds from the timestamp
                import_add_date = import_add_date / 1000
            add_date = datetime.fromtimestamp(import_add_date)

            try:
                bmark = self.save_bookmark(
                    unicode(link['href']),
                    unicode(link.text),
                    unicode(extended),
                    u" ".join(unicode(link.get('tags', '')).split(u',')),
                    dt=add_date)
                count = count + 1
                DBSession.flush()
            except InvalidBookmark:
                bmark = None

            if bmark:
                ids.append(bmark.bid)

            if count % COMMIT_SIZE == 0:
                transaction.commit()

        # Commit any that are left since the last commit performed.
        transaction.commit()

        from bookie.bcelery import tasks
        # For each bookmark in this set that we saved, sign up to
        # fetch its content.
        for bid in ids:
            tasks.fetch_bmark_content.delay(bid)

        # Start a new transaction for the next grouping.
        transaction.begin()


class DelXMLImporter(Importer):
    """Process a delicious xml export file"""

    @staticmethod
    def _is_delicious_format(parsed, can_handle):
        """A check for if this import files is a delicious xml format compat

        The root xml element will be 'posts' if this is the case.

        """
        if parsed.docinfo and parsed.docinfo.root_name == 'posts':
            can_handle = True
        return can_handle

    @staticmethod
    def can_handle(file_io):
        """Check if this file is a google bookmarks format file

        In order to check the file we have to read it and check it's content
        type.

        Google Bookmarks and Delicious both have the same content type, but
        they use different formats. We use the fact that Google Bookmarks
        uses <h3> tags and Delicious does not in order to differentiate these
        two formats.
        """

        try:
            file_io.seek(0)
            parsed = etree.parse(file_io)
        except XMLSyntaxError:
            # IF etree can't parse it, it's not our file.
            return False
        can_handle = False
        can_handle = DelXMLImporter._is_delicious_format(parsed,
                                                         can_handle)

        # make sure we reset the file_io object so that we can use it again
        return can_handle

    def process(self):
        """Given a file, process it"""
        if self.file_handle.closed:
            self.file_handle = open(self.file_handle.name)

        self.file_handle.seek(0)
        parsed = etree.parse(self.file_handle)
        count = 0

        ids = []
        for post in parsed.findall('post'):
            if 'javascript:' in post.get('href'):
                continue

            add_date = dateparser.parse(post.get('time'))

            try:
                bmark = self.save_bookmark(
                    unicode(post.get('href')),
                    unicode(post.get('description')),
                    unicode(post.get('extended')),
                    unicode(post.get('tag')),
                    dt=add_date)
                count = count + 1
                if bmark:
                    bmark.stored = bmark.stored.replace(tzinfo=None)
                    DBSession.flush()
            except InvalidBookmark:
                bmark = None

            if bmark:
                ids.append(bmark.bid)

            if count % COMMIT_SIZE == 0:
                transaction.commit()

        # Commit any that are left since the last commit performed.
        transaction.commit()

        from bookie.bcelery import tasks
        # For each bookmark in this set that we saved, sign up to
        # fetch its content.
        for bid in ids:
            tasks.fetch_bmark_content.delay(bid)

        # Start a new transaction for the next grouping.
        transaction.begin()


class GBookmarkImporter(Importer):
    """Process a Google Bookmark export html file"""

    @staticmethod
    def _is_google_format(soup, gbookmark_doctype, can_handle):
        """Verify that this import file is in the google export format

        Google only puts one tag at a time and needs to be looped through to
        get them all. See the sample files in the test_importer directory

        """
        if (soup.contents and
                soup.contents[0] == gbookmark_doctype and
                soup.find('h3')):
            can_handle = True

        return can_handle

    @staticmethod
    def can_handle(file_io):
        """Check if this file is a google bookmarks format file

        In order to check the file we have to read it and check it's content
        type

        Google Bookmarks and Delicious both have the same content type, but
        they use different formats. We use the fact that Google Bookmarks
        uses <h3> tags and Delicious does not in order to differentiate these
        two formats.
        """
        if (file_io.closed):
            file_io = open(file_io.name)
        file_io.seek(0)
        soup = BeautifulSoup(file_io)
        can_handle = False
        gbookmark_doctype = "DOCTYPE NETSCAPE-Bookmark-file-1"
        can_handle = GBookmarkImporter._is_google_format(soup,
                                                         gbookmark_doctype,
                                                         can_handle)

        # make sure we reset the file_io object so that we can use it again
        file_io.seek(0)
        return can_handle

    def process(self):
        """Process an html google bookmarks export and import them into bookie
        The export format is a tag as a heading, with urls that have that tag
        under that heading. If a url has N tags, it will appear N times, once
        under each heading.
        """
        count = 0
        if (self.file_handle.closed):
            self.file_handle = open(self.file_handle.name)
        soup = BeautifulSoup(self.file_handle)
        if not soup.contents[0] == "DOCTYPE NETSCAPE-Bookmark-file-1":
            raise Exception("File is not a google bookmarks file")

        urls = dict()  # url:url_metadata

        # we don't want to just import all the available urls, since each url
        # occurs once per tag. loop through and aggregate the tags for each url
        for tag in soup.findAll('h3'):
            links = tag.findNextSibling('dl')

            if links is not None:
                links = links.findAll("a")

                for link in links:
                    url = link["href"]
                    if url.startswith('javascript:'):
                        continue
                    tag_text = tag.text.replace(" ", "-")
                    if url in urls:
                        urls[url]['tags'].append(tag_text)
                    else:
                        tags = [tag_text] if tag_text != 'Unlabeled' else []

                        # get extended description
                        has_extended = (
                            link.parent.nextSibling and
                            link.parent.nextSibling.name == 'dd')
                        if has_extended:
                            extended = link.parent.nextSibling.text
                        else:
                            extended = ""

                        # Must use has_key here due to the link coming from
                        # the parser and it's not a true dict.
                        if link.has_key('add_date'):  # noqa
                            if int(link['add_date']) < 9999999999:
                                timestamp_added = int(link['add_date'])
                            else:
                                timestamp_added = float(link['add_date']) / 1e6
                        else:
                            link['add_date'] = time.time()

                        urls[url] = {
                            'description': link.text,
                            'tags': tags,
                            'extended': extended,
                            'date_added': datetime.fromtimestamp(
                                timestamp_added),
                        }

        # save the bookmarks
        ids = []
        for url, metadata in urls.items():
            try:
                bmark = self.save_bookmark(
                    unicode(url),
                    unicode(metadata['description']),
                    unicode(metadata['extended']),
                    u" ".join(metadata['tags']),
                    dt=metadata['date_added'])
                DBSession.flush()
            except InvalidBookmark:
                bmark = None
            if bmark:
                ids.append(bmark.bid)
            if count % COMMIT_SIZE == 0:
                transaction.commit()
                # Start a new transaction for the next grouping.
                transaction.begin()

        # Commit any that are left since the last commit performed.
        transaction.commit()

        from bookie.bcelery import tasks
        # For each bookmark in this set that we saved, sign up to
        # fetch its content.
        for bid in ids:
            tasks.fetch_bmark_content.delay(bid)


class FBookmarkImporter(Importer):
    """Process a FireFox backup export json file"""
    MOZ_CONTAINER = "text/x-moz-place-container"

    @staticmethod
    def _is_firefox_format(json, can_handle):
        """Verify that this import file is in the firefox backup
        export format

        Firefox json file has a variable "type" which is equal to
        "text/x-moz-place-container"
        """
        if json['type'] == FBookmarkImporter.MOZ_CONTAINER:
            can_handle = True

        return can_handle

    @staticmethod
    def can_handle(file_io):
        """Check if this file is a Firefox bookmarks format file

        In order to check the file we have to read it and check it's content
        has a variable "type" which is equal to "text/x-moz-place-container"
        """
        if (file_io.closed):
            file_io = open(file_io.name)
        file_io.seek(0)
        can_handle = False
        try:
            backup_json = json.load(file_io)
        except:
            file_io.seek(0)
            return can_handle

        can_handle = FBookmarkImporter._is_firefox_format(backup_json,
                                                          can_handle)

        # make sure we reset the file_io object so that we can use it again
        file_io.seek(0)
        return can_handle

    def bmap_add(self, bmark, bmap):
        if bmark["uri"] not in bmap:
            bmap[bmark["uri"]] = bmark

    def process(self):
        """Process an json firefox bookmarks export and import them into bookie
        """
        MOZ_PLACE = "text/x-moz-place"
        UNWANTED_SCHEME = ("data", "place", "javascript")

        count = 0
        if (self.file_handle.closed):
            self.file_handle = open(self.file_handle.name)

        content = self.file_handle.read().decode("UTF-8")
        # HACK: Firefox' JSON writer leaves a trailing comma
        # HACK: at the end of the array, which no parser accepts
        if content.endswith(u"}]},]}"):
            content = content[:-6] + u"}]}]}"
        root = json.loads(content)

        # make a dictionary of unique bookmarks
        bmap = {}

        # check if uri of child starts with "data", "place", "javascript"
        def is_good(child):
            return not child["uri"].split(":", 1)[0] in UNWANTED_SCHEME

        # find toplevel subfolders and tag folders
        folders = []
        tagfolders = []
        for child in root["children"]:
            if child.get("root") == "tagsFolder":
                tagfolders.extend(child["children"])
            elif child.get("root"):
                folders.append(child)

        # visit all subfolders recursively
        visited = set()
        while folders:
            next = folders.pop()
            if next["id"] in visited:
                continue
            for child in next["children"]:
                if child["type"] == self.MOZ_CONTAINER:
                    folders.append(child)
                    tagfolders.append(child)
                elif child["type"] == MOZ_PLACE and \
                        child.get("uri") and \
                        is_good(child):
                    self.bmap_add(child, bmap)
            visited.add(next["id"])

        # visit all tag folders
        for tag in tagfolders:
            for bmark in tag["children"]:
                if bmark["type"] == MOZ_PLACE and \
                        bmark.get("uri") and \
                        is_good(bmark):
                    self.bmap_add(bmark, bmap)
                    if "tags" not in bmap[bmark["uri"]]:
                        bmap[bmark["uri"]]["tags"] = []
                    bmap[bmark["uri"]]["tags"].append(
                        tag["title"].replace(" ", "-"))

        # save the bookmarks
        # annos has the information about the url like name, flags, expires,
        # value, type etc
        ids = []
        for url, metadata in bmap.items():
            if metadata.get('annos') is not None:
                if metadata.get('annos')[0].get('value') is None:
                    metadata['annos'][0]['value'] = ''
            else:
                metadata['annos'] = [{}]
                metadata['annos'][0]['value'] = ''
            if metadata.get('tags') is None:
                metadata['tags'] = ''
            try:
                bookmark = self.save_bookmark(
                    unicode(url),
                    unicode(metadata['title']),
                    unicode(metadata['annos'][0]['value']),
                    u" ".join(metadata['tags']),
                    dt=datetime.fromtimestamp(
                        metadata['dateAdded']/1e6))
                DBSession.flush()
            except InvalidBookmark:
                bookmark = None
            if bookmark:
                ids.append(bookmark.bid)
            if count % COMMIT_SIZE == 0:
                transaction.commit()
                # Start a new transaction for the next grouping.
                transaction.begin()

        # Commit any that are left since the last commit performed.
        transaction.commit()

        from bookie.bcelery import tasks
        # For each bookmark in this set that we saved, sign up to
        # fetch its content.
        for bid in ids:
            tasks.fetch_bmark_content.delay(bid)

########NEW FILE########
__FILENAME__ = message
"""Create and send messages to users

"""
import logging
import os
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pyramid.settings import asbool


LOG = logging.getLogger(__name__)
# notification statuses
# might have pending, sent, failed
MSG_STATUS = {
    'pending': 0,
    'sent': 1,
    'failed': 2,
    'not_sent': 3,
    'error': 4,
}


def sendmail(to, from_addr, subject, body):
    sendmail_location = "/usr/sbin/sendmail"
    p = os.popen("{0} -t".format(sendmail_location), "w")
    p.write("From: {0}\n".format(from_addr))
    p.write("To: {0}\n".format(to))
    p.write("Subject: {0}\n".format(subject))
    p.write("\n")  # blank line separating headers from body
    p.write(body)
    status = p.close()
    if status != 0:
        LOG.debug("SENDMAIL FAIL: " + str(status))
        return False
    else:
        return True


class Message(object):
    """This is a base email message we can then tweak"""

    def __init__(self, to, subject, settings):
        """Start up a basic message"""
        self.to = to
        self.subject = subject
        self.settings = settings

        self.from_addr = settings.get('email.from', None)

        # need ot setup/override in the extending classes
        self.message_file = None

    def _get_message_body(self, template_file, message_data):
        """Return the completed message template body

        """
        return "Test email message from bookie"
        # lookup = config['pylons.app_globals'].mako_lookup
        # template = lookup.get_template(template_file)

        # # template vars are a combo of the obj dict and the extra dict
        # template_vars = {'data': message_data}
        # return template.render(**template_vars)

    def send(self, message_data=None):
        """Send the message with the given subject

        body can be sent as part of send() or it can be set to the object as
        msg.body = "xxx"

        """
        self.body = self._get_message_body(self.message_file, message_data)

        msg = MIMEMultipart('related')
        msg['Subject'] = self.subject
        msg['From'] = self.from_addr

        msg['To'] = self.to

        plain_text = MIMEText(self.body, 'plain', _charset="UTF-8")
        msg.attach(plain_text)

        is_live = asbool(self.settings.get('email.enable', False))
        is_live = True

        if not is_live:
            print msg.as_string()
            return MSG_STATUS['sent']
        else:
            try:
                all_emails = msg['To']
                smtp_server = self.settings.get('email.host')

                if smtp_server == 'sendmail':
                    sendmail(msg['To'], msg['From'], msg['Subject'], self.body)
                else:
                    mail_server = smtplib.SMTP(smtp_server)
                    mail_server.sendmail(msg['From'],
                                         all_emails,
                                         msg.as_string())
                    mail_server.quit()
                return MSG_STATUS['sent']

            except smtplib.SMTPException:
                LOG.error(
                    "SMTP Error sending notice for: {0} ".format(
                        str(msg)))
                return MSG_STATUS['error']


class ReactivateMsg(Message):
    """Send an email for a reactivation email"""

    def _get_message_body(self, template_file, message_data):
        """Return the completed message template body

        """
        return """
Hello {username}:

Please activate your Bookie account by clicking on the following url:

{url}

---
The Bookie Team""".format(**message_data)
        # lookup = config['pylons.app_globals'].mako_lookup
        # template = lookup.get_template(template_file)

        # # template vars are a combo of the obj dict and the extra dict
        # template_vars = {'data': message_data}
        # return template.render(**template_vars)


class ActivationMsg(Message):
    """Send an email that you've been invited to the system"""
    def _get_message_body(self, template_file, message_data):
        """Return the completed message template body

        """
        return """
Please click the link below to activate your account.

{0}

We currently support importing from Google Bookmarks and Delicious exports.
Importing from a Chrome or Firefox export does work, however it reads the
folder names in as tags. So be aware of that.

Get the Chrome extension from the Chrome web store:
https://chrome.google.com/webstore/detail/knnbmilfpmbmlglpeemajjkelcbaaega

If you have any issues feel free to join #bookie on freenode.net or report
the issue or idea on https://github.com/bookieio/Bookie/issues.

We also encourage you to sign up for our mailing list at:
https://groups.google.com/forum/#!forum/bookie_bookmarks

and our Twitter account:
http://twitter.com/BookieBmarks

Bookie is open source. Check out the source at:
https://github.com/bookieio/Bookie

---
The Bookie Team""".format(message_data)


class ImportFailureMessage(Message):
    """Send an email that the import has failed."""

    def _get_message_body(self, template_file, message_data):
        """Build the email message body."""

        msg = """
The import for user {username} has failed to import. The path to the import
is:

{file_path}

Error:

{exc}

""".format(**message_data)
        return msg


class UserImportFailureMessage(Message):
    """Send an email to the user their import has failed."""

    def _get_message_body(self, template_file, message_data):
        """Build the email message body."""

        msg = """
Your import has failed. The error is listed below. Please file a bug at
https://github.com/bookieio/bookie/issues if this error continues. You may
also join #bookie on freenode irc if you wish to aid in debugging the issue.
If the error pertains to a specific bookmark in your import file you might try
removing it and importing the file again.

Error
----------

{exc}

A copy of this error has been logged and will be looked at.

---
The Bookie Team""".format(**message_data)
        return msg


class UserImportSuccessMessage(Message):
    """Send an email to the user after a successful import."""

    def _get_message_body(self, template_file, message_data):
        """Build the email message body."""

        msg = """
Your bookmark import is complete! We've begun processing your bookmarks to
load their page contents and fulltext index them. This process might take a
while if you have a large number of bookmarks. Check out your imported
bookmarks at https://bmark.us/{username}/recent.

---
The Bookie Team""".format(**message_data)
        return msg

########NEW FILE########
__FILENAME__ = readable
"""Handle processing and setting web content into Readability/cleaned

"""
import httplib
import logging
import lxml
import socket
import urllib2

from BaseHTTPServer import BaseHTTPRequestHandler as HTTPH
from breadability.readable import Article
from urlparse import urlparse

LOG = logging.getLogger(__name__)


class DictObj(dict):
    def __getattr__(self, name):
        try:
            return self.__getitem__(name)
        except KeyError:
            return super(DictObj, self).__getattr__(name)


USER_AGENT = 'bookie / ({url})'.format(
    url="https://github.com/bookieio/bookie",
)


STATUS_CODES = DictObj({
    '1': 1,    # used for manual parsed
    '200': 200,
    '404': 404,
    '403': 403,
    '429': 429,   # wtf, 429 doesn't exist...

    # errors like 9's
    '900': 900,   # used for unparseable
    '901': 901,   # url is not parseable/usable
    '902': 902,   # socket.error during download
    '903': 903,   # httplib.IncompleteRead error
    '904': 904,   # lxml error about document is empty
    '905': 905,   # httplib.BadStatusLine
})

IMAGE_TYPES = DictObj({
    'png': 'image/png',
    'jpeg': 'image/jpeg',
    'jpg': 'image/jpg',
    'gif': 'image/gif',
})


class Readable(object):
    """Understand the base concept of making readable"""
    is_error = False
    content = None
    content_type = None
    headers = None
    status_message = None
    status = None
    url = None

    def error(self, code, msg):
        """This readable request was an error, assign it so"""
        self.status = code
        self.status_message = str(msg)

    def is_error(self):
        """Check if this is indeed an error or not"""
        if self.status not in [STATUS_CODES['200'], ]:
            return True
        else:
            return False

    def is_image(self):
        """Check if the current object is an image"""
        # we can only get this if we have headers
        LOG.debug('content type')
        LOG.debug(self.content_type)
        if (self.content_type is not None and
                self.content_type.lower() in IMAGE_TYPES.values()):
            return True
        else:
            return False

    def set_content(self, content, content_type=None):
        """assign the content and potentially content type header"""
        self.content = content
        if content_type:
            self.content_type = content_type


class ReadContent(object):
    """Handle some given content and parse the readable out of it"""

    @staticmethod
    def parse(content, content_type=None, url=None):
        """Handle the parsing out of the html content given"""
        read = Readable()
        document = Article(content.read(), url=url)

        if not document.readable:
            read.error(STATUS_CODES['900'], "Could not parse content.")
        else:
            read.set_content(document.readable,
                             content_type=content_type)
            read.status = STATUS_CODES['1']
        return read


class ReadUrl(object):
    """Fetch a url and read some content out of it"""

    @staticmethod
    def parse(url):
        """Fetch the given url and parse out a Readable Obj for the content"""
        read = Readable()

        if not isinstance(url, unicode):
            url = url.decode('utf-8')

        # first check if we have a special url with the #! content in it
        if u'#!' in url:
            # rewrite it with _escaped_fragment_=xxx
            # we should be doing with this some regex, but cheating for now
            idx = url.index(u'#')
            fragment = url[idx:]
            clean_url = u"{0}?_escaped_fragment_={1}".format(url[0:idx],
                                                             fragment)
        else:
            # we need to clean up the url first, we can't have any anchor tag
            # on the url or urllib2 gets cranky
            parsed = urlparse(url)

            # We cannot parse urls that aren't http, https, or ftp://
            if (parsed.scheme not in (u'http', u'https', u'ftp')):
                read.error(
                    STATUS_CODES['901'],
                    'Invalid url scheme for readable content')
                return read

            if parsed.query is not None and parsed.query != '':
                query = u'?'
            else:
                query = u''

            clean_url = u"{0}://{1}{2}{query}{3}".format(
                parsed[0],
                parsed[1],
                parsed[2],
                parsed[4],
                query=query)

        try:
            LOG.debug('Readable Parsed: ' + clean_url)
            request = urllib2.Request(clean_url.encode('utf-8'))
            request.add_header('User-Agent', USER_AGENT)
            opener = urllib2.build_opener()
            fh = opener.open(request)

            # if it works, then we default to a 200 request
            # it's ok, promise :)
            read.status = 200
            read.headers = fh.info()
            read.content_type = read.headers.gettype()

        except urllib2.HTTPError, exc:
            # for some reason getting a code 429 from a server
            if exc.code not in [429]:
                read.error(exc.code, HTTPH.responses[exc.code])
            else:
                read.error(exc.code, unicode(exc.code) + ': ' + clean_url)

        except httplib.InvalidURL, exc:
            read.error(STATUS_CODES['901'], str(exc))

        except urllib2.URLError, exc:
            read.error(STATUS_CODES['901'], str(exc))

        except httplib.BadStatusLine, exc:
            read.error(STATUS_CODES['905'], str(exc))

        except socket.error, exc:
            read.error(STATUS_CODES['902'], str(exc))

        LOG.debug('is error?')
        LOG.debug(read.status)

        # let's check to make sure we should be parsing this
        # for example: don't parse images
        if not read.is_error() and not read.is_image():
            try:
                document = Article(fh.read(), url=clean_url)
                if not document.readable:
                    read.error(STATUS_CODES['900'],
                               "Could not parse document.")
                else:
                    read.set_content(document.readable)

            except socket.error, exc:
                read.error(STATUS_CODES['902'], str(exc))
            except httplib.IncompleteRead, exc:
                read.error(STATUS_CODES['903'], str(exc))
            except lxml.etree.ParserError, exc:
                read.error(STATUS_CODES['904'], str(exc))

        return read

########NEW FILE########
__FILENAME__ = tagcommands
"""Allow for tag based commands to act upon the bookmarks in the system

"""
import logging
from bookie.models import TagMgr

LOG = logging.getLogger(__name__)
COMMANDLIST = {}


class Commander(object):

    def __init__(self, bmark):
        self.commands = []
        self.bmark = bmark

    @staticmethod
    def check_commands(tags):
        """Pretend to build up a list of commands based on the tags passed"""
        return [tag for tag in tags.keys() if tag in COMMANDLIST]

    def build_commands(self):
        """See if we ehave any commands to apply to this bookmark"""
        for tag in self.bmark.tags.keys():
            # if this tag is a command then return true
            if tag in COMMANDLIST:
                self.commands.append(tag)

    def process(self):
        """see if there are any known commands and process them"""
        self.build_commands()

        for cmd in self.commands:
            # remove the tag from the bookmark
            del(self.bmark.tags[cmd])

            # run the command given the current state of the bookmark
            self.bmark = COMMANDLIST[cmd].run(self.bmark)

        return self.bmark


class Command(object):
    """Base of a command

    api is basically a run() method that accepts the bookmark in question

    """

    def run(bmark):
        """Run the command with the given Bmark object"""
        raise Exception("Not implemented")


class ToRead(Command):
    """Command to mark a bookmark as toread"""
    command_tag = u"!toread"
    read_tag = u"toread"

    @staticmethod
    def run(bmark):
        """Update this bookmark to toread status"""
        if ToRead.read_tag not in bmark.tags:
            res = TagMgr.find(tags=[ToRead.read_tag])
            if res:
                bmark.tags[ToRead.read_tag] = res[0]

        return bmark

# add our command to the list of those available
COMMANDLIST[ToRead.command_tag] = ToRead


class IsRead(Command):
    """Command to mark a bookmark as read

    This is basically just removing to toread tag from the bookmark
    It's just doing it as a command vs a manual edit to the tags

    """
    command_tag = "!read"
    read_tag = "toread"

    @staticmethod
    def run(bmark):
        """Make sure we remove the toread tag"""
        if IsRead.read_tag in bmark.tags:
            del(bmark.tags[IsRead.read_tag])

        return bmark

# add our command to the list of those available
COMMANDLIST[IsRead.command_tag] = IsRead

########NEW FILE########
__FILENAME__ = urlhash
"""Urls are hashed with a sha256 string"""
import hashlib


def generate_hash(url_string):
    m = hashlib.sha256()
    m.update(url_string.encode('utf-8'))
    return unicode(m.hexdigest()[:14])

########NEW FILE########
__FILENAME__ = utils
"""Generic and small utilities that are used in Bookie"""
import re
from urlparse import urlparse
from textblob import TextBlob


def _generate_nouns_from_url(string):
    res = set()
    if string:
        string = string.replace('_', ' ')
        words = re.findall(r"[\w]+", string)

        clean_path = " ".join(words)
        path_tokens = TextBlob(clean_path)
        title_nouns = path_tokens.noun_phrases
        for result in title_nouns:
            # If result has spaces split it to match our tag system.
            nouns = result.split()
            res.update(nouns)
    return res


def suggest_tags(data):
    """Suggest tags based on the content string `data`"""
    tag_set = set()
    if not data:
        return tag_set

    # The string might be a url that needs some cleanup before we parse for
    # suggestions
    parsed = urlparse(data)

    # Check if title is url. If title is not a string, url, and title will be
    # the same so no need to consider tags from url.
    if parsed.hostname:
        tag_set.update(_generate_nouns_from_url(parsed.path))
    else:
        # If the title is not a url extract nouns from title and the url.
        tag_set.update(_generate_nouns_from_url(data))

    return tag_set

########NEW FILE########
__FILENAME__ = applog
"""
Handle logging of the application stuff to the database

This will be replaced by something outside the app at some point, so the realy
code should all be in /lib/applogging.py vs in here. This is only the db store
side

"""
from datetime import datetime
from datetime import timedelta

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import func
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import UnicodeText

from bookie.models import Base
from bookie.models import DBSession


class AppLogMgr(object):

    @staticmethod
    def store(**kwargs):
        """Store a new log record to the db"""
        stored = AppLog(**kwargs)
        DBSession.add(stored)

    @staticmethod
    def find(days=1, message_filter=None, status=None):
        """Find a set of app log records based on predefined filters."""
        qry = AppLog.query
        if status is not None:
            qry = qry.filter(AppLog.status == status)

        if message_filter:
            mfilter = '%{0}%'.format(message_filter)
            qry = qry.filter(func.lower(AppLog.message).like(mfilter))

        now = datetime.utcnow()
        limit = now - timedelta(days=days)
        qry = qry.filter(AppLog.tstamp > limit)

        return qry.order_by(AppLog.tstamp.desc()).all()


class AppLog(Base):
    __tablename__ = 'logging'

    id = Column(Integer, autoincrement=True, primary_key=True)
    user = Column(Unicode(255), nullable=False)
    component = Column(Unicode(50), nullable=False)
    status = Column(Unicode(10), nullable=False)
    message = Column(Unicode(255), nullable=False)
    payload = Column(UnicodeText)
    tstamp = Column(DateTime, default=datetime.utcnow)

########NEW FILE########
__FILENAME__ = auth
"""
Sample SQLAlchemy-powered model definition for the repoze.what SQL plugin.

This model definition has been taken from a quickstarted TurboGears 2 project,
but it's absolutely independent of TurboGears.

"""

import bcrypt
import hashlib
import logging
import random

from datetime import (
    datetime,
    timedelta,
)

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import Boolean

from sqlalchemy.orm import relation
from sqlalchemy.orm import synonym

from bookie.models import Base
from bookie.models import DBSession


LOG = logging.getLogger(__name__)
GROUPS = ['admin', 'user']
ACTIVATION_AGE = timedelta(days=3)
NON_ACTIVATION_AGE = timedelta(days=30)


def get_random_word(wordLen):
    word = ''
    for i in xrange(wordLen):
        word += random.choice(('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrs'
                               'tuvwxyz0123456789/&='))
    return word


class ActivationMgr(object):

    @staticmethod
    def count():
        """Count how many activations are in the system."""
        return Activation.query.count()

    @staticmethod
    def get_user(username, code):
        """Get the user for this code"""
        qry = Activation.query.\
            filter(Activation.code == code).\
            filter(User.username == username)

        res = qry.first()

        if res is not None:
            return res.user
        else:
            return None

    @staticmethod
    def activate_user(username, code, new_pass):
        """Given this code get the user with this code make sure they exist"""

        qry = Activation.query.\
            filter(Activation.code == code).\
            filter(User.username == username)

        res = qry.first()

        if UserMgr.acceptable_password(new_pass) and res is not None:
            user = res.user
            user.activated = True
            user.password = new_pass
            res.activate()

            LOG.debug(dict(user))

            return True
        else:
            return None


class Activation(Base):
    """Handle activations/password reset items for users

    The id is the user's id. Each user can only have one valid activation in
    process at a time

    The code should be a random hash that is valid only one time
    After that hash is used to access the site it'll be removed

    The created by is a system: new user registration, password reset, forgot
    password, etc.

    """
    __tablename__ = u'activations'

    id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    code = Column(Unicode(60))
    valid_until = Column(
        DateTime,
        default=lambda: datetime.utcnow + ACTIVATION_AGE)
    created_by = Column('created_by', Unicode(255))

    def __init__(self, created_system):
        """Create a new activation"""
        self.code = Activation._gen_activation_hash()
        self.created_by = created_system
        self.valid_until = datetime.utcnow() + ACTIVATION_AGE

    @staticmethod
    def _gen_activation_hash():
        """Generate a random activation hash for this user account"""
        # for now just cheat and generate an api key, that'll work for now
        return User.gen_api_key()

    def activate(self):
        """Remove this activation"""
        DBSession.delete(self)


class UserMgr(object):
    """ Wrapper for static/combined operations of User object"""

    @staticmethod
    def count():
        """Number of users in the system."""
        return User.query.count()

    @staticmethod
    def non_activated_account(delete=False):
        """Get a list of  user accounts which are not verified since
        30 days of signup"""
        test_date = datetime.utcnow() - NON_ACTIVATION_AGE
        query = DBSession.query(Activation.id).\
            filter(Activation.valid_until < test_date).\
            subquery(name="query")
        qry = DBSession.query(User).\
            filter(User.activated.is_(False)).\
            filter(User.last_login.is_(None)).\
            filter(User.id.in_(query))
        # Delete the non activated accounts only if it is asked to.
        if delete:
            for user in qry.all():
                DBSession.delete(user)
        # If the non activated accounts are not asked to be deleted,
        # return their details.
        else:
            return qry.all()

    @staticmethod
    def get_list(active=None, order=None, limit=None):
        """Get a list of all of the user accounts"""
        user_query = User.query.order_by(User.username)

        if active is not None:
            user_query = user_query.filter(User.activated == active)

        if order:
            user_query = user_query.order_by(getattr(User, order))
        else:
            user_query = user_query.order_by(User.signup)

        if limit:
            user_query = user_query.limit(limit)

        return user_query.all()

    @staticmethod
    def get(user_id=None, username=None, email=None, api_key=None):
        """Get the user instance for this information

        :param user_id: integer id of the user in db
        :param username: string user's name
        :param inactive: default to only get activated true

        """
        user_query = User.query

        if username is not None:
            return user_query.filter(User.username == username).first()

        if user_id is not None:
            return user_query.filter(User.id == user_id).first()

        if email is not None:
            return user_query.filter(User.email == email).first()

        if api_key is not None:
            return user_query.filter(User.api_key == api_key).first()

        return None

    @staticmethod
    def auth_groupfinder(userid, request):
        """Pyramid wants to know what groups a user is in

        We need to pull this from the User object that we've stashed in the
        request object

        """
        user = request.user
        if user is not None:
            if user.is_admin:
                return 'admin'
            else:
                return 'user'
        return None

    @staticmethod
    def acceptable_password(password):
        """Verify that the password is acceptable

        Basically not empty, has more than 3 chars...

        """
        LOG.debug("PASS")
        LOG.debug(password)

        if password is not None:
            LOG.debug(len(password))

        if password is None:
            return False

        if len(password) < 3:
            return False

        return True

    @staticmethod
    def signup_user(email, signup_method):
        # Get this invite party started, create a new user acct.
        new_user = User()
        new_user.email = email.lower()
        new_user.username = email.lower()
        new_user.invited_by = signup_method
        new_user.api_key = User.gen_api_key()

        # they need to be deactivated
        new_user.reactivate(u'invite')

        # decrement the invite counter
        DBSession.add(new_user)
        return new_user


class User(Base):
    """Basic User def"""
    __tablename__ = 'users'

    id = Column(Integer, autoincrement=True, primary_key=True)
    username = Column(Unicode(255), unique=True)
    name = Column(Unicode(255))
    _password = Column('password', Unicode(60))
    email = Column(Unicode(255), unique=True)
    activated = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    last_login = Column(DateTime)
    signup = Column(DateTime, default=datetime.utcnow)
    api_key = Column(Unicode(12))
    invite_ct = Column(Integer, default=0)
    invited_by = Column('invited_by', Unicode(255))

    activation = relation(
        Activation,
        cascade="all, delete, delete-orphan",
        uselist=False,
        backref='user')

    def __init__(self):
        """By default a user starts out deactivated"""
        self.activation = Activation(u'signup')
        self.activated = False

    def _set_password(self, password):
        """Hash password on the fly."""
        hashed_password = password

        if isinstance(password, unicode):
            password_8bit = password.encode('UTF-8')
        else:
            password_8bit = password

        # Hash a password for the first time, with a randomly-generated salt
        salt = bcrypt.gensalt(10)
        hashed_password = bcrypt.hashpw(password_8bit, salt)

        # Make sure the hased password is an UTF-8 object at the end of the
        # process because SQLAlchemy _wants_ a unicode object for Unicode
        # fields
        if not isinstance(hashed_password, unicode):
            hashed_password = hashed_password.decode('UTF-8')

        self._password = hashed_password

    def _get_password(self):
        """Return the password hashed"""
        return self._password

    password = synonym('_password', descriptor=property(_get_password,
                                                        _set_password))

    def validate_password(self, password):
        """
        Check the password against existing credentials.

        :param password: the password that was provided by the user to
            try and authenticate. This is the clear text version that we will
            need to match against the hashed one in the database.
        :type password: unicode object.
        :return: Whether the password is valid.

        """
        # the password might be null as in the case of morpace employees
        # logging in via ldap. We check for that here and return them as an
        # incorrect login
        if self.password:
            salt = self.password[:29]
            return self.password == bcrypt.hashpw(password, salt)
        else:
            return False

    def safe_data(self):
        """Return safe data to be sharing around"""
        hide = ['_password', 'password', 'is_admin', 'api_key']
        return dict(
            [(k, v) for k, v in dict(self).iteritems() if k not in hide]
        )

    def deactivate(self):
        """In case we need to disable the login"""
        self.activated = False

    def reactivate(self, creator):
        """Put the account through the reactivation process

        This can come about via a signup or from forgotten password link

        """
        # if we reactivate then reinit this
        self.activation = Activation(creator)
        self.activated = False

    def has_invites(self):
        """Does the user have any invitations left"""
        return self.invite_ct > 0

    def invite(self, email):
        """Invite a user"""
        if not self.has_invites():
            return False
        if not email:
            raise ValueError('You must supply an email address to invite')
        else:
            # get this invite party started, create a new useracct
            new_user = UserMgr.signup_user(email, self.username)

            # decrement the invite counter
            self.invite_ct = self.invite_ct - 1
            DBSession.add(new_user)
            return new_user

    @staticmethod
    def gen_api_key():
        """Generate a 12 char api key for the user to use"""
        m = hashlib.sha256()
        m.update(get_random_word(12))
        return unicode(m.hexdigest()[:12])

########NEW FILE########
__FILENAME__ = fulltext
"""Handle performaing fulltext searches against the database.

This is going to be dependant on the db model found so we'll setup a factory
and API as we did in the importer

"""
import logging
import os

from sqlalchemy.orm import joinedload

from whoosh import qparser
from whoosh.fields import SchemaClass, TEXT, KEYWORD, ID
from whoosh.analysis import StemmingAnalyzer
from whoosh.index import create_in
from whoosh.index import open_dir
from whoosh.writing import AsyncWriter

from bookie.models import Bmark


LOG = logging.getLogger(__name__)
INDEX_NAME = None
INDEX_TYPE = None
WIX = None


def _reset_index():
    """Used by the test suite to reset the fulltext index."""
    WIX = create_in(INDEX_NAME, BmarkSchema)  # noqa


def set_index(index_type, index_path):
    global INDEX_NAME
    global INDEX_TYPE
    global WIX

    INDEX_TYPE = index_type
    INDEX_NAME = index_path

    cur_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    INDEX_NAME = os.path.join(cur_path, INDEX_NAME)

    if not os.path.exists(INDEX_NAME):
        os.mkdir(INDEX_NAME)
        WIX = create_in(INDEX_NAME, BmarkSchema)
    else:
        WIX = open_dir(INDEX_NAME)


class BmarkSchema(SchemaClass):
    bid = ID(unique=True, stored=True)
    description = TEXT
    extended = TEXT
    tags = KEYWORD
    readable = TEXT(analyzer=StemmingAnalyzer())


def get_fulltext_handler(engine):
    """Based on the engine, figure out the type of fulltext interface"""
    global INDEX_TYPE
    if INDEX_TYPE == 'whoosh':
        return WhooshFulltext()


def get_writer():
    global WIX
    writer = AsyncWriter(WIX)
    return writer


class WhooshFulltext(object):
    """Implement the fulltext api using whoosh as a storage backend

    """
    global WIX

    def search(self, phrase, content=False, username=None, ct=10, page=0):
        """Implement the search, returning a list of bookmarks"""
        page = int(page) + 1

        with WIX.searcher() as search:
            fields = ['description', 'extended', 'tags']

            if content:
                fields.append('readable')

            parser = qparser.MultifieldParser(fields,
                                              schema=WIX.schema,
                                              group=qparser.OrGroup)
            qry = parser.parse(phrase)

            try:
                res = search.search_page(qry, page, pagelen=int(ct))
            except ValueError, exc:
                raise(exc)

            if res:
                qry = Bmark.query.filter(
                    Bmark.bid.in_([r['bid'] for r in res])
                )

                if username:
                    qry = qry.filter(Bmark.username == username)

                qry = qry.options(joinedload('hashed'))

                return qry.all()
            else:
                return []

########NEW FILE########
__FILENAME__ = queue
import logging
from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import or_
from sqlalchemy import Unicode

from bookie.models import Base

LOG = logging.getLogger(__name__)

NEW = 0
RUNNING = 1
COMPLETE = 2
ERROR = 3


class ImportQueueMgr(object):
    """All the static methods for ImportQueue"""

    @staticmethod
    def get(id=None, username=None, status=None):
        """Get the import item"""
        if (id):
            qry = ImportQueue.query.filter(ImportQueue.id == id)
        elif (username):
            qry = ImportQueue.query.filter(ImportQueue.username == username)

        if status is not None:
            qry = qry.filter(ImportQueue.status == status)

        return qry.first()

    @staticmethod
    def get_details(id=None, username=None):
        """Get some details about a import

        We want to offer things like where they are in queue and maybe the
        import record itself

        """
        your_import = ImportQueueMgr.get(id=id, username=username)
        place_qry = ImportQueue.query.filter(ImportQueue.status == NEW)
        place_qry = place_qry.filter(ImportQueue.id < your_import.id)

        return {
            'place': place_qry.count(),
            'import': your_import
        }

    @staticmethod
    def get_ready(limit=10):
        """Get a list of imports that need to be processed"""
        qry = ImportQueue.query.filter(ImportQueue.status == 0)
        return qry.limit(limit).all()

    @staticmethod
    def size():
        """How deep is the queue at the moment"""
        qry = ImportQueue.query.filter(or_(
            ImportQueue.status != COMPLETE,
            ImportQueue.status != ERROR))
        return qry.count()

    @staticmethod
    def get_list():
        """Searching for records and all that.

        """
        qry = ImportQueue.query
        qry = qry.order_by(ImportQueue.id)
        return qry.all()


class ImportQueue(Base):
    """Track imports we need to do"""
    __tablename__ = 'import_queue'

    id = Column(Integer, autoincrement=True, primary_key=True)
    username = Column(Unicode(255))
    file_path = Column(Unicode(100), nullable=False)
    tstamp = Column(DateTime, default=datetime.utcnow)
    status = Column(Integer, default=NEW)
    completed = Column(DateTime)

    def __init__(self, username, file_path):
        """Start up an import queue"""
        self.username = username
        self.file_path = file_path

    def mark_error(self):
        """Mark that this failed and was an error"""
        self.status = ERROR

    def mark_running(self):
        """Mark that we're processing this"""
        self.status = RUNNING

    def mark_done(self):
        """Mark it complete"""
        self.completed = datetime.utcnow()
        self.status = COMPLETE

########NEW FILE########
__FILENAME__ = stats
"""Generate some stats on the bookmarks in the syste

Stats we want to track

- total bookmarks per day
- total # of tags in the system per day
- unique...not sure

- per user - number of bookmarks they have that day

- the popularity tracking numbers...let's show most popular by clicks? not
really stats

- outstanding invites
- invites sent but not accepted

# do the users thing as an hourly job, but assign a letter per hour of the day
# and run it that way. on hour 0 run A users, on hour 1 run B users, on hour
# 23 run xzy users.

"""
from calendar import monthrange
from datetime import (
    datetime,
    timedelta,
)

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import Unicode

from bookie.models import Base
from bookie.models import DBSession
from bookie.models import BmarkMgr
from bookie.models import TagMgr
from bookie.models.queue import ImportQueueMgr


IMPORTER_CT = u'importer_queue'
TOTAL_CT = u'user_bookmarks'
UNIQUE_CT = u'unique_bookmarks'
TAG_CT = u'total_tags'
USER_CT = u'user_bookmarks_{0}'
STATS_WINDOW = 30


class StatBookmarkMgr(object):
    """Handle our agg stuff for the stats on bookmarks"""

    @staticmethod
    def get_stat(start, end, *stats):
        """Fetch the records from the stats table for these guys"""
        qry = StatBookmark.query
        qry = qry.filter(StatBookmark.tstamp > start)
        qry = qry.filter(StatBookmark.tstamp <= end)

        if stats:
            qry = qry.filter(StatBookmark.attrib.in_(stats))

        # order things up by their date so they're grouped together
        qry.order_by(StatBookmark.tstamp)
        return qry.all()

    @staticmethod
    def get_user_bmark_count(username, start_date, end_date):
        """Fetch the bookmark count for the user from the stats table"""
        qry = (StatBookmark.query.
               filter(StatBookmark.attrib == USER_CT.format(username)).
               filter(StatBookmark.tstamp >= start_date).
               filter(StatBookmark.tstamp <= end_date))

        # Order the result by their timestamp.
        qry = qry.order_by(StatBookmark.tstamp)
        return qry.all()

    @staticmethod
    def count_unique_bookmarks():
        """Count the unique number of bookmarks in the system"""
        total = BmarkMgr.count(distinct=True)
        stat = StatBookmark(attrib=UNIQUE_CT, data=total)
        DBSession.add(stat)

    @staticmethod
    def count_total_bookmarks():
        """Count the total number of bookmarks in the system"""
        total = BmarkMgr.count()
        stat = StatBookmark(attrib=TOTAL_CT, data=total)
        DBSession.add(stat)

    @staticmethod
    def count_total_tags():
        """Count the total number of tags in the system"""
        total = TagMgr.count()
        stat = StatBookmark(attrib=TAG_CT, data=total)
        DBSession.add(stat)

    @staticmethod
    def count_importer_depth():
        """Mark how deep the importer queue is at the moment"""
        total = ImportQueueMgr.size()
        stat = StatBookmark(attrib=IMPORTER_CT, data=total)
        DBSession.add(stat)

    @staticmethod
    def count_user_bookmarks(username):
        """Count the total number of bookmarks for the user in the system"""
        total = BmarkMgr.count(username)
        stat = StatBookmark(
            attrib=USER_CT.format(username),
            data=total
        )
        DBSession.add(stat)

    @staticmethod
    def count_user_bmarks(username, start_date=None, end_date=None):
        """Get a list of user bookmark count"""
        if start_date:
            start_date = start_date.split(' ')
            start_date = datetime.strptime(start_date[0], '%Y-%m-%d')
        if end_date:
            end_date = end_date.split(' ')
            end_date = datetime.strptime(end_date[0], '%Y-%m-%d')
        if not start_date:
            if not end_date:
                # If both start_date and end_date are None,
                # end_date will be the current date
                end_date = datetime.utcnow()

            # Otherwise if there's no start_date but we have an end_date,
            # assume that the user wants the STATS_WINDOW worth of stats.
            start_date = end_date - timedelta(days=STATS_WINDOW)
        elif start_date and not end_date:
            if start_date.day == 1:
                # If the starting day is 1, stats of the month is returned
                days = monthrange(start_date.year, start_date.day)[1] - 2
                end_date = start_date + timedelta(days=days)
            else:
                end_date = start_date + timedelta(days=STATS_WINDOW)
        # Since we're comparing dates with 00:00:00 we need to add one day and
        # do <=.
        return [
            StatBookmarkMgr.get_user_bmark_count(
                username, start_date, end_date + timedelta(days=1)),
            start_date,
            end_date
        ]


class StatBookmark(Base):
    """First stats we track are the counts of things.

    """
    __tablename__ = 'stats_bookmarks'

    id = Column(Integer, autoincrement=True, primary_key=True)
    tstamp = Column(DateTime, default=datetime.utcnow)
    attrib = Column(Unicode(100), nullable=False)
    data = Column(Integer, nullable=False, default=0)

    def __init__(self, **kwargs):
        self.attrib = kwargs.get('attrib', 'unknown')
        self.data = kwargs.get('data', 0)
        self.tstamp = kwargs.get('tstamp', datetime.utcnow())

########NEW FILE########
__FILENAME__ = routes
"""Create routes here and gets returned into __init__ main()"""
from convoy.combo import combo_app
from pyramid.wsgi import wsgiapp2


def build_routes(config):
    """Add any routes to the config"""

    config.add_route("home", "/")
    config.add_route("dashboard", "/dashboard")

    # Add routes for the combo loader to match up to static file requests.
    config.add_route('convoy', '/combo')

    JS_FILES = config.get_settings()['app_root'] + '/bookie/static/js/build'
    application = combo_app(JS_FILES)
    config.add_view(
        wsgiapp2(application),
        route_name='convoy')

    # auth routes
    config.add_route("login", "login")
    config.add_route("logout", "logout")
    config.add_route("reset", "{username}/reset/{reset_key}")
    config.add_route("signup", "signup")
    config.add_route("signup_process", "signup_process")

    # celery routes
    config.add_route("celery_hourly_stats", "jobhourly")

    # bmark routes
    config.add_route("bmark_recent", "recent")
    config.add_route("bmark_recent_tags", "recent/*tags")

    config.add_route("bmark_recent_rss", "rss")
    config.add_route("bmark_recent_rss_tags", "rss/*tags")

    config.add_route("bmark_readable", "bmark/readable/{hash_id}")

    # user based bmark routes
    config.add_route("user_bmark_recent", "{username}/recent")
    config.add_route("user_bmark_recent_tags", "{username}/recent/*tags")

    config.add_route("user_bmark_rss", "{username}/rss")
    config.add_route("user_bmark_rss_tags", "{username}/rss/*tags")

    config.add_route("user_bmark_edit", "{username}/edit/{hash_id}")
    config.add_route("user_bmark_edit_error",
                     "{username}/edit_error/{hash_id}")
    config.add_route("user_bmark_new", "{username}/new")
    config.add_route("user_bmark_new_error", "{username}/new_error")
    config.add_route(
        "user_delete_all_bookmarks",
        "{username}/account/delete_all_bookmarks")

    # config.add_route("bmark_delete", "/bmark/delete")
    # config.add_route("bmark_confirm_delete", "/bmark/confirm/delete/{bid}")

    # tag related routes
    config.add_route("tag_list", "tags")
    config.add_route("tag_bmarks", "tags/*tags")

    # user tag related
    config.add_route("user_tag_list", "{username}/tags")
    config.add_route("user_tag_bmarks", "{username}/tags/*tags")

    config.add_route("user_import", "{username}/import")
    config.add_route("search", "search")
    config.add_route("user_search", "{username}/search")

    config.add_route("search_results", "results")
    config.add_route("user_search_results", "{username}/results")

    # matches based on the header
    # HTTP_X_REQUESTED_WITH
    # ajax versions are used in the mobile search interface
    config.add_route("search_results_ajax", "results/*terms", xhr=True)
    config.add_route("search_results_rest", "results/*terms")
    config.add_route("user_search_results_ajax",
                     "{username}/results*terms",
                     xhr=True)
    config.add_route("user_search_results_rest", "{username}/results*terms")

    config.add_route("redirect", "redirect/{hash_id}")
    config.add_route("user_redirect", "{username}/redirect/{hash_id}")

    config.add_route("user_account", "{username}/account")
    config.add_route("user_export", "{username}/export")
    config.add_route("user_stats", "{username}/stats")

    #
    # NEW API
    #

    # stats
    config.add_route('api_bookmark_stats',
                     '/api/v1/stats/bookmarks',
                     request_method='GET')
    config.add_route('api_user_stats',
                     '/api/v1/stats/users',
                     request_method='GET')

    # ping checks
    config.add_route('api_ping',
                     '/api/v1/{username}/ping',
                     request_method='GET')
    config.add_route('api_ping_missing_user',
                     '/api/v1/ping',
                     request_method='GET')
    config.add_route('api_ping_missing_api',
                     '/ping',
                     request_method='GET')

    # auth related
    config.add_route("api_user_account",
                     "/api/v1/{username}/account",
                     request_method="GET")
    config.add_route("api_user_account_update",
                     "/api/v1/{username}/account",
                     request_method="POST")
    config.add_route("api_user_api_key",
                     "/api/v1/{username}/api_key",
                     request_method="GET")
    config.add_route("api_reset_api_key",
                     "/api/v1/{username}/api_key",
                     request_method="POST")
    config.add_route("api_user_reset_password",
                     "/api/v1/{username}/password",
                     request_method="POST")

    config.add_route("api_user_suspend_remove",
                     "api/v1/suspend",
                     request_method="DELETE")
    config.add_route("api_user_suspend",
                     "api/v1/suspend",
                     request_method="POST")
    config.add_route("api_user_invite",
                     "api/v1/{username}/invite",
                     request_method="POST")

    # many bookmark api calls
    config.add_route("api_bmarks_export", "api/v1/{username}/bmarks/export")

    # we have to search before we hit the bmarks keys so that it doesn't think
    # the tag is "search"
    config.add_route("api_bmark_search", "api/v1/bmarks/search/*terms")
    config.add_route("api_bmark_search_user",
                     "/api/v1/{username}/bmarks/search/*terms")

    config.add_route('api_bmarks', 'api/v1/bmarks')
    config.add_route('api_bmarks_tags', 'api/v1/bmarks/*tags')
    config.add_route('api_bmarks_user', 'api/v1/{username}/bmarks')
    config.add_route('api_bmarks_user_tags', 'api/v1/{username}/bmarks/*tags')
    config.add_route('api_count_bmarks_user',
                     'api/v1/{username}/stats/bmarkcount')

    # user bookmark api calls
    config.add_route("api_bmark_add",
                     "/api/v1/{username}/bmark",
                     request_method="POST")
    config.add_route("api_bmark_update",
                     "/api/v1/{username}/bmark/{hash_id}",
                     request_method="POST")
    config.add_route("api_extension_sync", "/api/v1/{username}/extension/sync")

    config.add_route("api_bmark_hash",
                     "/api/v1/{username}/bmark/{hash_id}",
                     request_method="GET")
    config.add_route("api_bmark_remove",
                     "/api/v1/{username}/bmark/{hash_id}",
                     request_method="DELETE")

    config.add_route("api_tag_complete_user",
                     "/api/v1/{username}/tags/complete")
    config.add_route("api_tag_complete",
                     "/api/v1/tags/complete")

    # admin api calls
    config.add_route("api_admin_readable_todo", "/api/v1/a/readable/todo")
    config.add_route(
        "api_admin_readable_reindex",
        "/api/v1/a/readable/reindex")
    config.add_route(
        "api_admin_accounts_inactive",
        "/api/v1/a/accounts/inactive")
    config.add_route(
        "api_admin_accounts_invites_add",
        "/api/v1/a/accounts/invites/{username}/{count}",
        request_method="POST")
    config.add_route(
        "api_admin_accounts_invites",
        "/api/v1/a/accounts/invites",
        request_method="GET")
    config.add_route(
        "api_admin_imports_list",
        "/api/v1/a/imports/list",
        request_method="GET")
    config.add_route(
        "api_admin_imports_reset",
        "/api/v1/a/imports/reset/{id}",
        request_method="POST")

    config.add_route(
        "api_admin_users_list",
        "/api/v1/a/users/list",
        request_method="GET")
    config.add_route(
        "api_admin_new_user",
        "/api/v1/a/users/add",
        request_method="POST")
    config.add_route(
        "api_admin_del_user",
        "/api/v1/a/users/delete/{username}",
        request_method="DELETE")
    config.add_route(
        "api_admin_bmark_remove",
        "/api/v1/a/bmark/{username}/{hash_id}",
        request_method="DELETE")

    config.add_route(
        "api_admin_applog",
        "/api/v1/a/applog/list",
        request_method="GET")

    config.add_route(
        "api_admin_non_activated",
        "/api/v1/a/nonactivated",
        request_method="GET")

    config.add_route(
        "api_admin_delete_non_activated",
        "/api/v1/a/nonactivated",
        request_method="DELETE")

    # these are single word matching, they must be after /recent /popular etc
    config.add_route("user_home", "{username}")

    return config

########NEW FILE########
__FILENAME__ = factory
"""Provide tools for generating objects for testing purposes."""
from datetime import datetime
from random import randint
import random
import string

from bookie.models import DBSession
from bookie.models import Bmark
from bookie.models import Tag
from bookie.models.applog import AppLog
from bookie.models.auth import User
from bookie.models.stats import (
    StatBookmark,
    USER_CT,
)


def random_int(max=1000):
    """Generate a random integer value

    :param max: Maximum value to hit.
    """
    return randint(0, max)


def random_string(length=None):
    """Generates a random string from urandom.

    :param length: Specify the number of chars in the generated string.
    """
    chars = string.ascii_uppercase + string.digits
    str_length = length if length is not None else random_int()
    return unicode(u''.join(random.choice(chars) for x in range(str_length)))


def random_url():
    """Generate a random url that is totally bogus."""
    url = u"http://{0}.com".format(random_string())
    return url


def make_applog(message=None, status=None):
    """Generate applog instances."""
    if status is None:
        status = random_int(max=3)

    if message is None:
        message = random_string(100)

    alog = AppLog(**{
        'user': random_string(10),
        'component': random_string(10),
        'status': status,
        'message': message,
        'payload': u'',
    })
    return alog


def make_tag(name=None):
    if not name:
        name = random_string(255)

    return Tag(name)


def make_bookmark(user=None):
    """Generate a fake bookmark for testing use."""
    bmark = Bmark(random_url(),
                  username=u"admin",
                  desc=random_string(),
                  ext=random_string(),
                  tags=u"bookmarks")

    if user:
        bmark.username = user.username
        bmark.user = user

    DBSession.add(bmark)
    DBSession.flush()
    return bmark


def make_user_bookmark_count(username, data, tstamp=None):
    """Generate a fake user bookmark count for testing use"""
    if tstamp is None:
        tstamp = datetime.utcnow()
    bmark_count = StatBookmark(tstamp=tstamp,
                               attrib=USER_CT.format(username),
                               data=data)
    DBSession.add(bmark_count)
    DBSession.flush()
    return [bmark_count.attrib, bmark_count.data, bmark_count.tstamp]


def make_user(username=None):
    """Generate a fake user to test against."""
    user = User()

    if not username:
        username = random_string(10)

    user.username = username

    DBSession.add(user)
    DBSession.flush()
    return user

########NEW FILE########
__FILENAME__ = test_admin
"""Test that we're meeting delicious API specifications"""
import logging
import json
import transaction
import unittest
from pyramid import testing

from bookie.models import Bmark
from bookie.models import DBSession
from bookie.models.auth import Activation
from bookie.models.queue import ImportQueue
from bookie.tests import BOOKIE_TEST_INI
from bookie.tests import empty_db
from bookie.tests import factory

LOG = logging.getLogger(__name__)


class AdminApiTest(unittest.TestCase):
    """Test the bookie admin api calls."""
    _api_key = None

    @property
    def api_key(self):
        """Cache the api key for all calls."""
        if not self._api_key:
            res = DBSession.execute(
                "SELECT api_key FROM users WHERE username='admin'").fetchone()
            self._api_key = res['api_key']
        return self._api_key

    def setUp(self):
        from pyramid.paster import get_app
        app = get_app(BOOKIE_TEST_INI, 'bookie')
        from webtest import TestApp
        self.testapp = TestApp(app)
        testing.setUp()

    def tearDown(self):
        """We need to empty the bmarks table on each run"""
        testing.tearDown()
        empty_db()

    def _add_demo_import(self):
        """DB Needs some imports to be able to query."""
        # add out completed one
        q = ImportQueue(
            username=u'admin',
            file_path=u'testing.txt'
        )
        DBSession.add(q)
        transaction.commit()
        return

    def test_list_inactive_users(self):
        """Test that we can fetch the inactive users."""
        # for now just make sure we can get a 200 call on it.
        params = {
            'api_key': self.api_key
        }
        res = self.testapp.get('/api/v1/a/accounts/inactive',
                               params=params,
                               status=200)
        # by default we shouldn't have any inactive users
        data = json.loads(res.body)
        users = [u for u in data['users']]
        for u in users:
            self.assertEqual(0, u['invite_ct'], "Count should be 0 to start.")

    def test_non_activated_accounts(self):
        """Test that we can fetch the non activated accounts"""
        params = {
            'api_key': self.api_key
        }
        res = self.testapp.get('/api/v1/a/nonactivated',
                               params=params,
                               status=200)
        # By default, we should not have any non activated accounts.
        data = json.loads(res.body)
        self.assertEqual(True, data['status'], "Status should be True")
        self.assertEqual(0, len(data['data']), "Count should be 0 to start.")

    def test_delete_non_activated_accounts(self):
        """Test that we can delete non activated accounts"""
        res = self.testapp.delete(
            '/api/v1/a/nonactivated?api_key={0}'.format(
                self.api_key),
            status=200)
        data = json.loads(res.body)
        self.assertEqual(True, data['status'], "Status should be True")
        self.assertEqual(u'Removed non activated accounts', data['message'])

    def test_invite_ct(self):
        """Test we can call and get the invite counts."""
        # for now just make sure we can get a 200 call on it.
        params = {
            'api_key': self.api_key
        }
        res = self.testapp.get('/api/v1/a/accounts/invites',
                               params=params,
                               status=200)
        # we should get back tuples of username/count
        data = json.loads(res.body)['users']
        found = False
        invite_count = None
        for user, count in data:
            if user == u'admin':
                found = True
                invite_count = count

        self.assertTrue(found, "There should be the admin user." + res.body)
        self.assertEqual(
            0,
            invite_count,
            "The admin user shouldn't have any invites." + res.body)

    def test_set_invite_ct(self):
        """Test we can set the invite count for the user"""
        # for now just make sure we can get a 200 call on it.
        params = {
            'api_key': self.api_key
        }
        res = self.testapp.post('/api/v1/a/accounts/invites/admin/10',
                                params=params,
                                status=200)
        # we should get back tuples of username/count
        data = json.loads(res.body)
        self.assertEqual(
            'admin',
            data.get('username'),
            "The admin user data is returned to us." + res.body)
        self.assertEqual(
            10,
            int(data.get('invite_ct')),
            "The admin user now has 10 invites." + res.body)

        # and of course when we're done we need to unset it back to 0 or else
        # the test above blows up...sigh.
        res = self.testapp.post('/api/v1/a/accounts/invites/admin/0',
                                params=params,
                                status=200)

    def test_import_info(self):
        """Test that we can get a count of the imports in the system."""
        self._add_demo_import()
        params = {
            'api_key': self.api_key
        }
        res = self.testapp.get('/api/v1/a/imports/list',
                               params=params,
                               status=200)

        # we should get back tuples of username/count
        data = json.loads(res.body)

        self.assertEqual(
            1, data.get('count'), "There are none by default. " + res.body)

        self.assertEqual(
            'admin',
            data.get('imports')[0]['username'],
            "The first import is from admin " + res.body)
        self.assertEqual(
            0,
            data.get('imports')[0]['status'],
            "And it has a status of 0 " + res.body)

    def test_user_list(self):
        """Test that we can hit the api and get the list of users."""
        self._add_demo_import()
        params = {
            'api_key': self.api_key
        }
        res = self.testapp.get('/api/v1/a/users/list',
                               params=params,
                               status=200)

        # we should get back dict of count, users.
        data = json.loads(res.body)

        self.assertEqual(
            1, data.get('count'), "There are none by default. " + res.body)
        self.assertEqual(
            'admin',
            data.get('users')[0]['username'],
            "The first user is from admin " + res.body)
        self.assertEqual(
            'testing@dummy.com',
            data.get('users')[0]['email'],
            "The first user is from testing@dummy.com " + res.body)

    def test_user_delete(self):
        """Verify we can remove a user and their bookmarks via api."""
        bob = factory.make_user(username=u'bob')
        bob.activation = Activation(u'signup')

        factory.make_bookmark(user=bob)
        transaction.commit()

        res = self.testapp.delete(
            '/api/v1/a/users/delete/{0}?api_key={1}'.format(
                'bob',
                self.api_key),
            )

        # we should get back dict of count, users.
        data = json.loads(res.body)

        self.assertTrue(data.get('success'))

        # Verify that we have no bookmark for the user any longer.
        bmarks = Bmark.query.filter(Bmark.username == u'bob').all()
        self.assertEqual(0, len(bmarks))

########NEW FILE########
__FILENAME__ = test_base_api
"""Test that we're meeting delicious API specifications"""
# Need to create a new renderer that wraps the jsonp renderer and adds these
# heads to all responses. Then the api needs to be adjusted to use this new
# renderer type vs jsonp.
import logging
import json
import transaction
import unittest
from pyramid import testing

from bookie.models import DBSession
from bookie.models.auth import Activation
from bookie.tests import BOOKIE_TEST_INI
from bookie.tests import empty_db
from bookie.tests import factory

from datetime import datetime


GOOGLE_HASH = u'aa2239c17609b2'
BMARKUS_HASH = u'c5c21717c99797'
LOG = logging.getLogger(__name__)

API_KEY = None


class BookieAPITest(unittest.TestCase):
    """Test the Bookie API"""

    def setUp(self):
        from pyramid.paster import get_app
        app = get_app(BOOKIE_TEST_INI, 'bookie')
        from webtest import TestApp
        self.testapp = TestApp(app)
        testing.setUp()

        global API_KEY
        res = DBSession.execute(
            "SELECT api_key FROM users WHERE username = 'admin'").fetchone()
        API_KEY = res['api_key']

    def tearDown(self):
        """We need to empty the bmarks table on each run"""
        testing.tearDown()
        empty_db()

    def _check_cors_headers(self, res):
        """ Make sure that the request has proper CORS headers."""
        self.assertEqual(res.headers['access-control-allow-origin'], '*')
        self.assertEqual(
            res.headers['access-control-allow-headers'], 'X-Requested-With')

    def _get_good_request(self, content=False, second_bmark=False):
        """Return the basics for a good add bookmark request"""
        session = DBSession()

        # the main bookmark, added second to prove popular will sort correctly
        prms = {
            'url': u'http://google.com',
            'description': u'This is my google desc',
            'extended': u'And some extended notes about it in full form',
            'tags': u'python search',
            'api_key': API_KEY,
            'username': u'admin',
            'inserted_by': u'chrome_ext',
        }

        # if we want to test the readable fulltext side we want to make sure we
        # pass content into the new bookmark
        if content:
            prms['content'] = u"<p>There's some content in here dude</p>"

        # rself.assertEqualparams = urllib.urlencode(prms)
        res = self.testapp.post(
            '/api/v1/admin/bmark?',
            content_type='application/json',
            params=json.dumps(prms),
        )

        if second_bmark:
            prms = {
                'url': u'http://bmark.us',
                'description': u'Bookie',
                'extended': u'Exteded notes',
                'tags': u'bookmarks',
                'api_key': API_KEY,
                'username': u'admin',
                'inserted_by': u'chrome_ext',
            }

            # if we want to test the readable fulltext side we want to make
            # sure we pass content into the new bookmark
            prms['content'] = u"<h1>Second bookmark man</h1>"

            # rself.assertEqualparams = urllib.urlencode(prms)
            res = self.testapp.post(
                '/api/v1/admin/bmark?',
                content_type='application/json',
                params=json.dumps(prms)
            )

        session.flush()
        transaction.commit()
        # Run the celery task for indexing this bookmark.
        from bookie.bcelery import tasks
        tasks.reindex_fulltext_allbookmarks(sync=True)
        return res

    def _setup_user_bookmark_count(self):
        """Fake user bookmark counts are inserted into the database"""
        test_date_1 = datetime(2013, 11, 25)
        stat1 = factory.make_user_bookmark_count(username=u'admin',
                                                 data=20,
                                                 tstamp=test_date_1)
        test_date_2 = datetime(2013, 11, 15)
        stat2 = factory.make_user_bookmark_count(username=u'admin',
                                                 data=30,
                                                 tstamp=test_date_2)
        test_date_3 = datetime(2013, 12, 28)
        stat3 = factory.make_user_bookmark_count(username=u'admin',
                                                 data=15,
                                                 tstamp=test_date_3)
        transaction.commit()
        return [stat1, stat2, stat3]

    def test_add_bookmark(self):
        """We should be able to add a new bookmark to the system"""
        # we need to know what the current admin's api key is so we can try to
        # add
        res = DBSession.execute(
            "SELECT api_key FROM users WHERE username = 'admin'").fetchone()
        key = res['api_key']

        test_bmark = {
            'url': u'http://bmark.us',
            'description': u'Bookie',
            'extended': u'Extended notes',
            'tags': u'bookmarks',
            'api_key': key,
        }

        res = self.testapp.post('/api/v1/admin/bmark',
                                params=test_bmark,
                                status=200)

        self.assertTrue(
            '"location":' in res.body,
            "Should have a location result: " + res.body)
        self.assertTrue(
            'description": "Bookie"' in res.body,
            "Should have Bookie in description: " + res.body)
        self._check_cors_headers(res)

    def test_add_bookmark_empty_body(self):
        """When missing a POST body we get an error response."""
        res = DBSession.execute(
            "SELECT api_key FROM users WHERE username = 'admin'").fetchone()
        key = res['api_key']

        res = self.testapp.post(
            str('/api/v1/admin/bmark?api_key={0}'.format(key)),
            params={},
            status=400)

        data = json.loads(res.body)
        self.assertTrue('error' in data)
        self.assertEqual(data['error'], 'Bad Request: No url provided')

    def test_add_bookmark_missing_url_in_JSON(self):
        """When missing the url in the JSON POST we get an error response."""
        res = DBSession.execute(
            "SELECT api_key FROM users WHERE username = 'admin'").fetchone()
        key = res['api_key']

        params = {
            'description': u'This is my test desc',
        }

        res = self.testapp.post(
            str('/api/v1/admin/bmark?api_key={0}'.format(key)),
            content_type='application/json',
            params=json.dumps(params),
            status=400)

        data = json.loads(res.body)
        self.assertTrue('error' in data)
        self.assertEqual(data['error'], 'Bad Request: No url provided')

    def test_bookmark_fetch(self):
        """Test that we can get a bookmark and it's details"""
        self._get_good_request(content=True)
        res = self.testapp.get('/api/v1/admin/bmark/{0}?api_key={1}'.format(
                               GOOGLE_HASH,
                               API_KEY),
                               status=200)

        # make sure we can decode the body
        bmark = json.loads(res.body)['bmark']
        self.assertEqual(
            GOOGLE_HASH,
            bmark[u'hash_id'],
            "The hash_id should match: " + str(bmark[u'hash_id']))

        self.assertTrue(
            u'tags' in bmark,
            "We should have a list of tags in the bmark returned")

        self.assertTrue(
            bmark[u'tags'][0][u'name'] in [u'python', u'search'],
            "Tag should be either python or search:" +
            str(bmark[u'tags'][0][u'name']))

        self.assertTrue(
            u'readable' not in bmark,
            "We should not have readable content")

        self.assertEqual(
            u'python search', bmark[u'tag_str'],
            "tag_str should be populated: " + str(dict(bmark)))

        # to get readble content we need to pass the flash with_content
        res = self.testapp.get(
            '/api/v1/admin/bmark/{0}?api_key={1}&with_content=true'.format(
                GOOGLE_HASH,
                API_KEY),
            status=200)

        # make sure we can decode the body
        bmark = json.loads(res.body)['bmark']

        self.assertTrue(
            u'readable' in bmark,
            "We should have readable content")

        self.assertTrue(
            'dude' in bmark['readable']['content'],
            "We should have 'dude' in our content: " +
            bmark['readable']['content'])
        self._check_cors_headers(res)

    def test_bookmark_fetch_with_suggestions(self):
        """When a very recent bookmark is present return it."""
        self._get_good_request(content=True, second_bmark=True)
        res = self.testapp.get(
            '/api/v1/admin/bmark/{0}'.format(GOOGLE_HASH),
            {
                'api_key': API_KEY,
                'url': 'http://google.com',
                'description': 'The best search engine for Python things.'
            },
            status=200)

        # make sure we can decode the body
        bmark = json.loads(res.body)
        self.assertIn('tag_suggestions', bmark)
        self.assertIn('search', bmark['tag_suggestions'])
        self._check_cors_headers(res)

    def test_no_bookmark_fetch_with_suggestions(self):
        """When a very recent bookmark is present return it."""
        res = self.testapp.get(
            '/api/v1/admin/bmark/{0}'.format(GOOGLE_HASH),
            {
                'api_key': API_KEY,
                'url': 'http://google.com',
                'description': 'The best search engine for Python things.'
            },
            status=404)

        # make sure we can decode the body
        bmark = json.loads(res.body)
        self.assertIn('tag_suggestions', bmark)
        self.assertIn('search', bmark['tag_suggestions'])
        self._check_cors_headers(res)

    def test_bookmark_fetch_fail(self):
        """Verify we get a failed response when wrong bookmark"""
        self._get_good_request()

        # test that we get a 404
        res = self.testapp.get(
            '/api/v1/admin/bmark/{0}?api_key={1}'.format(BMARKUS_HASH,
                                                         API_KEY),
            status=404)
        self._check_cors_headers(res)

    def test_bookmark_diff_user(self):
        """Verify that anon users can access the bookmark"""
        self._get_good_request()

        # test that we get a 404
        res = self.testapp.get(
            '/api/v1/admin/bmark/{0}'.format(GOOGLE_HASH),
            status=200)
        self._check_cors_headers(res)

    def test_bookmark_diff_user_authed(self):
        """Verify an auth'd user can fetch another's bookmark"""
        self._get_good_request()

        # test that we get a 404
        res = self.testapp.get(
            '/api/v1/admin/bmark/{0}'.format(GOOGLE_HASH, 'invalid'),
            status=200)
        self._check_cors_headers(res)

    def test_bookmark_remove(self):
        """A delete call should remove the bookmark from the system"""
        self._get_good_request(content=True, second_bmark=True)

        # now let's delete the google bookmark
        res = self.testapp.delete(
            '/api/v1/admin/bmark/{0}?api_key={1}'.format(
                GOOGLE_HASH,
                API_KEY),
            status=200)

        self.assertTrue(
            'message": "done"' in res.body,
            "Should have a message of done: " + res.body)

        # we're going to cheat like mad, use the sync call to get the hash_ids
        # of bookmarks in the system and verify that only the bmark.us hash_id
        # is in the response body
        res = self.testapp.get('/api/v1/admin/extension/sync',
                               params={'api_key': API_KEY},
                               status=200)

        self.assertTrue(
            GOOGLE_HASH not in res.body,
            "Should not have the google hash: " + res.body)
        self.assertTrue(
            BMARKUS_HASH in res.body,
            "Should have the bmark.us hash: " + res.body)
        self._check_cors_headers(res)

    def test_bookmark_recent_user(self):
        """Test that we can get list of bookmarks with details"""
        self._get_good_request(content=True)
        res = self.testapp.get('/api/v1/admin/bmarks?api_key=' + API_KEY,
                               status=200)

        # make sure we can decode the body
        bmark = json.loads(res.body)['bmarks'][0]
        self.assertEqual(
            GOOGLE_HASH,
            bmark[u'hash_id'],
            "The hash_id should match: " + str(bmark[u'hash_id']))

        self.assertTrue(
            u'tags' in bmark,
            "We should have a list of tags in the bmark returned")

        self.assertTrue(
            bmark[u'tags'][0][u'name'] in [u'python', u'search'],
            "Tag should be either python or search:" +
            str(bmark[u'tags'][0][u'name']))

        res = self.testapp.get(
            '/api/v1/admin/bmarks?with_content=true&api_key=' + API_KEY,
            status=200)
        self._check_cors_headers(res)

        # make sure we can decode the body
        # @todo this is out because of the issue noted in the code. We'll
        # clean this up at some point.
        # bmark = json.loads(res.body)['bmarks'][0]
        # self.assertTrue('here dude' in bmark[u'readable']['content'],
        #     "There should be content: " + str(bmark))

    def test_bookmark_recent(self):
        """Test that we can get list of bookmarks with details"""
        self._get_good_request(content=True)
        res = self.testapp.get('/api/v1/bmarks?api_key=' + API_KEY,
                               status=200)

        # make sure we can decode the body
        bmark = json.loads(res.body)['bmarks'][0]
        self.assertEqual(
            GOOGLE_HASH,
            bmark[u'hash_id'],
            "The hash_id should match: " + str(bmark[u'hash_id']))

        self.assertTrue(
            u'tags' in bmark,
            "We should have a list of tags in the bmark returned")

        self.assertTrue(
            bmark[u'tags'][0][u'name'] in [u'python', u'search'],
            "Tag should be either python or search:" +
            str(bmark[u'tags'][0][u'name']))

        res = self.testapp.get(
            '/api/v1/admin/bmarks?with_content=true&api_key=' + API_KEY,
            status=200)
        self._check_cors_headers(res)

        # make sure we can decode the body
        # @todo this is out because of the issue noted in the code. We'll
        # clean this up at some point.
        # bmark = json.loads(res.body)['bmarks'][0]
        # self.assertTrue('here dude' in bmark[u'readable']['content'],
        #     "There should be content: " + str(bmark))

    def test_bookmark_sync(self):
        """Test that we can get the sync list from the server"""
        self._get_good_request(content=True, second_bmark=True)

        # test that we only get one resultback
        res = self.testapp.get('/api/v1/admin/extension/sync',
                               params={'api_key': API_KEY},
                               status=200)

        self.assertEqual(
            res.status, "200 OK",
            msg='Get status is 200, ' + res.status)

        self.assertTrue(
            GOOGLE_HASH in res.body,
            "The google hash id should be in the json: " + res.body)
        self.assertTrue(
            BMARKUS_HASH in res.body,
            "The bmark.us hash id should be in the json: " + res.body)
        self._check_cors_headers(res)

    def test_search_api(self):
        """Test that we can get list of bookmarks ordered by clicks"""
        self._get_good_request(content=True, second_bmark=True)

        res = self.testapp.get('/api/v1/bmarks/search/google', status=200)

        # make sure we can decode the body
        bmark_list = json.loads(res.body)
        results = bmark_list['search_results']
        self.assertEqual(
            len(results),
            1,
            "We should have one result coming back: {0}".format(len(results)))

        bmark = results[0]

        self.assertEqual(
            GOOGLE_HASH,
            bmark[u'hash_id'],
            "The hash_id {0} should match: {1} ".format(
                str(GOOGLE_HASH),
                str(bmark[u'hash_id'])))

        self.assertTrue(
            'clicks' in bmark,
            "The clicks field should be in there")
        self._check_cors_headers(res)

    def test_search_api_fail(self):
        """Test that request to an out of bound page returns error message"""
        self._get_good_request(content=True, second_bmark=False)

        res = self.testapp.get(
            '/api/v1/bmarks/search/google?page=10',
            status=404
        )
        # make sure we can decode the body
        bmark_list = json.loads(res.body)

        self.assertTrue(
            'error' in bmark_list,
            "The error field should be in there")
        self.assertEqual(
            bmark_list['error'],
            "Bad Request: Page number out of bound",
            "We should have the error message: {0}".format(bmark_list['error'])
        )

        self._check_cors_headers(res)

    def test_bookmark_tag_complete(self):
        """Test we can complete tags in the system

        By default we should have tags for python, search, bookmarks

        """
        self._get_good_request(second_bmark=True)

        res = self.testapp.get(
            '/api/v1/admin/tags/complete',
            params={
                'tag': 'py',
                'api_key': API_KEY},
            status=200)

        self.assertTrue(
            'python' in res.body,
            "Should have python as a tag completion: " + res.body)

        # we shouldn't get python as an option if we supply bookmarks as the
        # current tag. No bookmarks have both bookmarks & python as tags
        res = self.testapp.get(
            '/api/v1/admin/tags/complete',
            params={
                'tag': u'py',
                'current': u'bookmarks',
                'api_key': API_KEY
            },
            status=200)

        self.assertTrue(
            'python' not in res.body,
            "Should not have python as a tag completion: " + res.body)
        self._check_cors_headers(res)

    def test_start_defined_end(self):
        """Test getting a user's bookmark count over a period of time when
        only start_date is defined and end_date is None"""
        test_dates = self._setup_user_bookmark_count()
        res = self.testapp.get(u'/api/v1/admin/stats/bmarkcount',
                               params={u'api_key': API_KEY,
                                       u'start_date': u'2013-11-16'},
                               status=200)
        data = json.loads(res.body)
        count = data['count'][0]
        self.assertEqual(
            count['attrib'], test_dates[0][0])
        self.assertEqual(
            count['data'], test_dates[0][1])
        self.assertEqual(
            count['tstamp'], str(test_dates[0][2]))
        # Test start_date and end_date.
        self.assertEqual(
            data['start_date'], u'2013-11-16 00:00:00')
        self.assertEqual(
            data['end_date'], u'2013-12-16 00:00:00')

    def test_start_defined_end_defined(self):
        """Test getting a user's bookmark count over a period of time when both
        start_date and end_date are defined"""
        test_dates = self._setup_user_bookmark_count()
        res = self.testapp.get(u'/api/v1/admin/stats/bmarkcount',
                               params={u'api_key': API_KEY,
                                       u'start_date': u'2013-11-14',
                                       u'end_date': u'2013-11-16'},
                               status=200)
        data = json.loads(res.body)
        count = data['count'][0]
        self.assertEqual(
            count['attrib'], test_dates[1][0])
        self.assertEqual(
            count['data'], test_dates[1][1])
        self.assertEqual(
            count['tstamp'], str(test_dates[1][2]))
        # Test start_date and end_date.
        self.assertEqual(
            data['start_date'], u'2013-11-14 00:00:00')
        self.assertEqual(
            data['end_date'], u'2013-11-16 00:00:00')

    def test_start_end_defined(self):
        """Test getting a user's bookmark count over a period of time when
        start_date is None and end_date is defined"""
        test_dates = self._setup_user_bookmark_count()
        res = self.testapp.get(u'/api/v1/admin/stats/bmarkcount',
                               params={u'api_key': API_KEY,
                                       u'end_date': u'2013-12-29'},
                               status=200)
        data = json.loads(res.body)
        count = data['count'][0]
        self.assertEqual(
            count['attrib'], test_dates[2][0])
        self.assertEqual(
            count['data'], test_dates[2][1])
        self.assertEqual(
            count['tstamp'], str(test_dates[2][2]))
        # Test start_date and end_date.
        self.assertEqual(
            data['start_date'], u'2013-11-29 00:00:00')
        self.assertEqual(
            data['end_date'], u'2013-12-29 00:00:00')

    def test_start_of_month(self):
        """Test getting a user's bookmark count when start_date is the
        first day of the month"""
        test_dates = self._setup_user_bookmark_count()
        res = self.testapp.get(u'/api/v1/admin/stats/bmarkcount',
                               params={u'api_key': API_KEY,
                                       u'start_date': u'2013-11-1'},
                               status=200)
        data = json.loads(res.body)
        count = data['count']
        self.assertEqual(
            count[0]['attrib'], test_dates[1][0])
        self.assertEqual(
            count[0]['data'], test_dates[1][1])
        self.assertEqual(
            count[0]['tstamp'], str(test_dates[1][2]))
        self.assertEqual(
            count[1]['attrib'], test_dates[0][0])
        self.assertEqual(
            count[1]['data'], test_dates[0][1])
        self.assertEqual(
            count[1]['tstamp'], str(test_dates[0][2]))
        # Test start_date and end_date.
        self.assertEqual(
            data['start_date'], u'2013-11-01 00:00:00')
        self.assertEqual(
            data['end_date'], u'2013-11-30 00:00:00')

    def user_bookmark_count_authorization(self):
        """If no API_KEY is present, it is unauthorized request"""
        self.testapp.get(u'/api/v1/admin/stats/bmarkcount',
                         status=403)

    def test_account_information(self):
        """Test getting a user's account information"""
        res = self.testapp.get(u'/api/v1/admin/account?api_key=' + API_KEY,
                               status=200)

        # make sure we can decode the body
        user = json.loads(res.body)

        self.assertEqual(
            user['username'], 'admin',
            "Should have a username of admin {0}".format(user))

        self.assertTrue(
            'password' not in user,
            'Should not have a field password {0}'.format(user))
        self.assertTrue(
            '_password' not in user,
            'Should not have a field password {0}'.format(user))
        self.assertTrue(
            'api_key' not in user,
            'Should not have a field password {0}'.format(user))
        self._check_cors_headers(res)

    def test_account_update(self):
        """Test updating a user's account information"""
        params = {
            'name': u'Test Admin'
        }
        res = self.testapp.post(
            str(u"/api/v1/admin/account?api_key=" + str(API_KEY)),
            content_type='application/json',
            params=json.dumps(params),
            status=200)

        # make sure we can decode the body
        user = json.loads(res.body)

        self.assertEqual(
            user['username'], 'admin',
            "Should have a username of admin {0}".format(user))
        self.assertEqual(
            user['name'], 'Test Admin',
            "Should have a new name of Test Admin {0}".format(user))

        self.assertTrue(
            'password' not in user,
            "Should not have a field password {0}".format(user))
        self.assertTrue(
            '_password' not in user,
            "Should not have a field password {0}".format(user))
        self.assertTrue(
            'api_key' not in user,
            "Should not have a field password {0}".format(user))
        self._check_cors_headers(res)

    def test_account_apikey(self):
        """Fetching a user's api key"""
        res = self.testapp.get(
            u"/api/v1/admin/api_key?api_key=" + str(API_KEY),
            status=200)

        # make sure we can decode the body
        user = json.loads(res.body)

        self.assertEqual(
            user['username'], 'admin',
            "Should have a username of admin {0}".format(user))
        self.assertTrue(
            'api_key' in user,
            "Should have an api key in there: {0}".format(user))
        self._check_cors_headers(res)

    def test_account_reset_apikey(self):
        """Reset User's api key"""

        # Create a fake user
        test_user = factory.make_user(username='test_user')
        # Set and Get the current api key
        # make_user doesn't set the api key of user so set it explicitly
        current_apikey = test_user.api_key = "random_key"
        test_user.activation = Activation(u'signup')
        transaction.commit()

        # send a request to reset the api key
        res = self.testapp.post(
            "/api/v1/test_user/api_key?api_key=" + current_apikey,
            content_type='application/json',
            params={u'username': 'test_user',
                    u'api_key': current_apikey},
            status=200)

        # Get the user's api key from db
        fetch_api = DBSession.execute(
            "SELECT api_key FROM users WHERE username='test_user'").fetchone()
        new_apikey = fetch_api['api_key']

        # make sure we can decode the body
        response = json.loads(res.body)

        # old and new api keys must not be the same
        self.assertNotEqual(
            current_apikey, new_apikey,
            "Api key must be changed after reset request")
        self.assertTrue(
            'api_key' in response,
            "Should have an api key in there: {0}".format(response))

        # Api key in response must be the new one
        self.assertEqual(
            response['api_key'], new_apikey,
            "Should have a api key of user {0}".format(response))

        self._check_cors_headers(res)

    def test_account_password_change(self):
        """Change a user's password"""
        params = {
            'current_password': 'admin',
            'new_password': 'not_testing'
        }

        res = self.testapp.post(
            "/api/v1/admin/password?api_key=" + str(API_KEY),
            params=params,
            status=200)

        # make sure we can decode the body
        user = json.loads(res.body)

        self.assertEqual(
            user['username'], 'admin',
            "Should have a username of admin {0}".format(user))
        self.assertTrue(
            'message' in user,
            "Should have a message key in there: {0}".format(user))

        params = {
            'current_password': 'not_testing',
            'new_password': 'admin'
        }
        res = self.testapp.post(
            "/api/v1/admin/password?api_key=" + str(API_KEY),
            params=params,
            status=200)

        self._check_cors_headers(res)

    def test_account_password_failure(self):
        """Change a user's password, in bad ways"""
        params = {
            'current_password': 'test',
            'new_password': 'not_testing'
        }

        res = self.testapp.post(
            "/api/v1/admin/password?api_key=" + str(API_KEY),
            params=params,
            status=403)

        # make sure we can decode the body
        user = json.loads(res.body)

        self.assertEqual(
            user['username'], 'admin',
            "Should have a username of admin {0}".format(user))
        self.assertTrue(
            'error' in user,
            "Should have a error key in there: {0}".format(user))
        self.assertTrue(
            'typo' in user['error'],
            "Should have a error key in there: {0}".format(user))
        self._check_cors_headers(res)

    def test_api_ping_success(self):
        """We should be able to ping and make sure we auth'd and are ok"""
        res = self.testapp.get('/api/v1/admin/ping?api_key=' + API_KEY,
                               status=200)
        ping = json.loads(res.body)

        self.assertTrue(ping['success'])

        self._check_cors_headers(res)

    def test_api_ping_failed_invalid_api(self):
        """If you don't supply a valid api key, you've failed the ping"""

        # Login a user and then test the validation of api key

        user_data = {'login': u'admin',
                     'password': u'admin',
                     'form.submitted': u'true'}

        # Assuming user logged in without errors
        self.testapp.post('/login', params=user_data)

        # Check for authentication of api key

        res = self.testapp.get('/api/v1/admin/ping?api_key=' + 'invalid',
                               status=200)
        ping = json.loads(res.body)

        self.assertFalse(ping['success'])
        self.assertEqual(ping['message'], "API key is invalid.")
        self._check_cors_headers(res)

    def test_api_ping_failed_nouser(self):
        """If you don't supply a username, you've failed the ping"""
        res = self.testapp.get('/api/v1/ping?api_key=' + API_KEY,
                               status=200)
        ping = json.loads(res.body)

        self.assertTrue(not ping['success'])
        self.assertEqual(ping['message'], "Missing username in your api url.")
        self._check_cors_headers(res)

    def test_api_ping_failed_missing_api(self):
        """If you don't supply a username, you've failed the ping"""
        res = self.testapp.get('/ping?api_key=' + API_KEY,
                               status=200)
        ping = json.loads(res.body)

        self.assertTrue(not ping['success'])
        self.assertEqual(ping['message'], "The API url should be /api/v1")
        self._check_cors_headers(res)

    def test_bookmarks_stats(self):
        """Test the bookmark stats"""
        res = self.testapp.get(u'/api/v1/stats/bookmarks',
                               status=200)
        data = json.loads(res.body)
        self.assertTrue(
            'count' in data,
            "Should have bookmark count: " + str(data))
        self.assertTrue(
            'unique_count' in data,
            "Should have unique bookmark count: " + str(data))

    def test_user_stats(self):
        """Test the user stats"""
        res = self.testapp.get(u'/api/v1/stats/users',
                               status=200)
        data = json.loads(res.body)
        self.assertTrue(
            'count' in data,
            "Should have user count: " + str(data))
        self.assertTrue(
            'activations' in data,
            "Should have pending user activations: " + str(data))
        self.assertTrue(
            'with_bookmarks' in data,
            "Should have count of users with bookmarks: " + str(data))

########NEW FILE########
__FILENAME__ = test_popular_api
import logging
import json
import pytest
import transaction
import unittest
from pyramid import testing

from bookie.models import DBSession
from bookie.models import Bmark
from bookie.models.auth import User
from bookie.tests import BOOKIE_TEST_INI
from bookie.tests import empty_db
from bookie.tests import gen_random_word
from random import randint

LOG = logging.getLogger(__name__)

API_KEY = None
MAX_CLICKS = 60


class BookiePopularAPITest(unittest.TestCase):
    """Test the Bookie API for retreiving popular bookmarks"""

    def setUp(self):
        from pyramid.paster import get_app
        app = get_app(BOOKIE_TEST_INI, 'bookie')
        from webtest import TestApp
        self.testapp = TestApp(app)
        testing.setUp()

        global API_KEY
        res = DBSession.execute(
            "SELECT api_key FROM users WHERE username = 'admin'").fetchone()
        API_KEY = res['api_key']

    def tearDown(self):
        """We need to empty the bmarks table on each run"""
        testing.tearDown()
        empty_db()

    def _check_cors_headers(self, res):
        """ Make sure that the request has proper CORS headers."""
        self.assertEqual(res.headers['access-control-allow-origin'], '*')
        self.assertEqual(
            res.headers['access-control-allow-headers'], 'X-Requested-With')

    def _add_bookmark(self, user=None):
        """Add a bookmark for a particular user
           with random click count.
           If no user is specified, then admin is used
           for the username"""
        if user:
            DBSession.add(user)
            username = user.username
        else:
            username = u'admin'

        b = Bmark(
            url=gen_random_word(12),
            username=username,
            tags=gen_random_word(4),
        )

        b.clicks = randint(0, MAX_CLICKS)
        b.hash_id = gen_random_word(5)

        DBSession.add(b)
        DBSession.flush()
        b.hashed.clicks = b.clicks
        DBSession.flush()
        transaction.commit()

    def test_bookmark_popular_user(self):
        """Test that we can get a list of bookmarks
           added by admin and sorted by popularity."""

        # Populating DB with some bookmarks of random users.
        user_bmark_count = randint(1, 5)
        for i in range(user_bmark_count):
            user = User()
            user.username = gen_random_word(10)
            self._add_bookmark(user)

        admin_bmark_count = randint(1, 5)
        # Populating DB with some bookmarks of admin.
        for i in range(admin_bmark_count):
            self._add_bookmark()

        res = self.testapp.get('/api/v1/admin/bmarks?sort=popular&api_key=' +
                               API_KEY,
                               status=200)

        # make sure we can decode the body
        bmarks = json.loads(res.body)['bmarks']

        self.assertEqual(
            len(bmarks),
            admin_bmark_count,
            "All admin bookmarks are retreived"
        )

        # Initializing number of clicks
        previous_clicks = MAX_CLICKS
        for bmark in bmarks:
            self.assertEqual(
                bmark[u'username'],
                u'admin',
                "Only bookmarks by admin must be displayed")
            self.assertTrue(
                bmark['clicks'] <= previous_clicks,
                '{0} < {1}'.format(bmark['clicks'], previous_clicks))
            previous_clicks = bmark[u'clicks']

        self._check_cors_headers(res)
        empty_db()

    @pytest.mark.skipif(
        True,
        reason=('Work in progress fixing queries to work in postgresql and'
                'sqlite.'))
    def test_bookmark_popular(self):
        """Test that we can get a list of all bookmarks
           added by random users and sorted by popularity."""
        # Populating DB with some bookmarks of random users.
        user_bmark_count = randint(1, 5)
        for i in range(user_bmark_count):
            user = User()
            user.username = gen_random_word(10)
            self._add_bookmark(user)

        admin_bmark_count = randint(1, 5)
        # Populating DB with some bookmarks of admin.
        for i in range(admin_bmark_count):
            self._add_bookmark()

        res = self.testapp.get('/api/v1/bmarks?sort=popular&api_key='
                               + API_KEY,
                               status=200)

        # make sure we can decode the body
        bmarks = json.loads(res.body)['bmarks']

        self.assertEqual(
            len(bmarks),
            admin_bmark_count + user_bmark_count,
            "All bookmarks are retrieved"
        )

        # Initializing number of clicks
        previous_clicks = MAX_CLICKS
        for bmark in bmarks:
            self.assertTrue(
                bmark['total_clicks'] <= previous_clicks,
                '{0} <= {1}'.format(bmark['total_clicks'], previous_clicks))
            previous_clicks = bmark[u'total_clicks']

        self._check_cors_headers(res)
        empty_db()

########NEW FILE########
__FILENAME__ = test_api_base
"""Test the auth related web calls"""
import logging

from pyramid import testing
from unittest import TestCase


LOG = logging.getLogger(__name__)


class TestAuthWeb(TestCase):
    """Testing web calls"""

    def setUp(self):
        from pyramid.paster import get_app
        from bookie.tests import BOOKIE_TEST_INI
        app = get_app(BOOKIE_TEST_INI, 'bookie')
        from webtest import TestApp
        self.testapp = TestApp(app)
        testing.setUp()

    def tearDown(self):
        """We need to empty the bmarks table on each run"""
        testing.tearDown()

    def test_login_url(self):
        """Verify we get the login form"""
        res = self.testapp.get('/login', status=200)

        body_str = u"Log In"
        form_str = u'name="login"'

        self.assertTrue(
            body_str in res.body,
            msg="Request should contain Log In: " + res.body)

        # There should be a login form on there.
        self.assertTrue(
            form_str in res.body,
            msg="The login input should be visible in the body:" + res.body)

    def test_login_success(self):
        """Verify a good login"""

        # the migrations add a default admin account
        user_data = {'login': u'admin',
                     'password': u'admin',
                     'form.submitted': u'true'}

        res = self.testapp.post('/login',
                                params=user_data)
        self.assertEqual(
            res.status,
            "302 Found",
            msg='status is 302 Found, ' + res.status)

        # should end up back at the recent page
        res = res.follow()
        self.assertTrue(
            'recent' in str(res),
            "Should have 'recent' in the resp: " + str(res))

    def test_login_success_username_case_insensitive(self):
        """Verify a good login"""

        # the migrations add a default admin account
        user_data = {'login': u'ADMIN',
                     'password': u'admin',
                     'form.submitted': u'true'}

        res = self.testapp.post('/login',
                                params=user_data)
        self.assertEqual(
            res.status,
            "302 Found",
            msg='status is 302 Found, ' + res.status)

        # should end up back at the recent page
        res = res.follow()
        self.assertTrue(
            'recent' in str(res),
            "Should have 'recent' in the resp: " + str(res))

    def test_login_failure(self):
        """Verify a bad login"""

        # the migrations add a default admin account
        user_data = {'login': u'admin',
                     'password': u'wrongpass',
                     'form.submitted': u'true'}

        res = self.testapp.post('/login',
                                params=user_data)

        self.assertEqual(
            res.status,
            "200 OK",
            msg='status is 200 OK, ' + res.status)

        # should end up back at login with an error message
        self.assertTrue(
            'has failed' in str(res),
            "Should have 'Failed login' in the resp: " + str(res))

    def test_login_null(self):
        """Verify null login form submission fails"""

        user_data = {
            'login': u'',
            'password': u'',
            'form.submitted': u'true'
        }

        res = self.testapp.post('/login',
                                params=user_data)

        self.assertEqual(
            res.status,
            "200 OK",
            msg='status is 200 OK, ' + res.status)

        # should end up back at login with an error message
        self.assertTrue(
            'Failed login' in str(res),
            "Should have 'Failed login' in the resp: " + str(res))

########NEW FILE########
__FILENAME__ = test_model
"""Test the Auth model setup"""
from unittest import TestCase
from pyramid import testing

from datetime import (
    datetime,
    timedelta,
)

from bookie.models import DBSession
from bookie.models.auth import Activation
from bookie.models.auth import User
from bookie.models.auth import UserMgr

from bookie.tests import empty_db
from bookie.tests import gen_random_word
from bookie.tests import TestDBBase


class TestPassword(TestCase):
    """Test password checks"""
    pass


class TestAuthUser(TestCase):
    """Test User Model"""
    test_hash = '$2a$10$FMFKEYqC7kifFTm05iag7etE17Q0AyKvtX88XUdUcM7rvpz48He92'
    test_password = 'testing'

    def test_password_set(self):
        """Make sure we get the proper hashed password"""
        tst = User()
        tst.password = self.test_password

        self.assertEqual(
            len(tst.password),
            60,
            "Hashed should be 60 char long: " + tst.password)
        self.assertEqual(
            '$2a$',
            tst.password[:4],
            "Hash should start with the right complexity: " + tst.password[:4])

    def test_password_match(self):
        """Try to match a given hash"""

        tst = User()
        tst._password = self.test_hash

        self.assertTrue(
            tst._password == self.test_hash, "Setting should have hash")
        self.assertTrue(
            tst.password == self.test_hash, "Getting should have hash")
        self.assertTrue(
            tst.validate_password(self.test_password),
            "The password should pass against the given hash: " + tst.password)


class TestAuthUserDB(TestDBBase):
    def setUp(self):
        """Setup Tests"""
        from pyramid.paster import get_app
        from bookie.tests import BOOKIE_TEST_INI
        app = get_app(BOOKIE_TEST_INI, 'bookie')
        from webtest import TestApp
        self.testapp = TestApp(app)
        testing.setUp()

    def tearDown(self):
        """Tear down each test"""
        testing.tearDown()
        empty_db()

    def test_activation_delete(self):
        """Make sure removing an activation does not remove a user."""
        tst = User()
        tst.username = gen_random_word(10)
        tst.activation = Activation(u'signup')
        DBSession.add(tst)
        DBSession.flush()

        DBSession.delete(tst.activation)

        users = UserMgr.get_list()

        # We still have the admin user as well so the count is two.
        self.assertEqual(
            2,
            len(users),
            'We should have a total of 2 users still: ' + str(len(users)))

    def test_activation_cascade(self):
        """Removing a user cascades the activations as well."""
        tst = User()
        tst.username = gen_random_word(10)
        tst.activation = Activation(u'signup')
        DBSession.add(tst)
        DBSession.flush()

        DBSession.delete(tst)

        users = UserMgr.get_list()

        # We still have the admin user as well so the count is one.
        self.assertEqual(
            1,
            len(users),
            'We should have a total of 1 user still: ' + str(len(users)))

        activations = DBSession.query(Activation).all()
        self.assertEqual(
            0, len(activations), 'There should be no activations left')

    def test_non_activated_account(self):
        """Removing a non activated account"""
        # When all the conditions are satisfied, the account should be deleted.
        email = u'testingdelete@gmail.com'
        UserMgr.signup_user(email, u'testcase')
        activations = Activation.query.all()
        users = User.query.all()
        self.assertEqual(
            1,
            len(activations),
            'We should have a total of 1 activation: ' + str(len(activations)))
        self.assertEqual(
            2,
            len(users),
            'We should have a total of 2 users: ' + str(len(users)))
        activations[0].valid_until = datetime.utcnow() - timedelta(days=35)
        UserMgr.non_activated_account(delete=True)
        activations = Activation.query.all()
        users = User.query.all()
        self.assertEqual(
            0,
            len(activations),
            'There should be no activations left')
        self.assertEqual(
            1,
            len(users),
            'We should have a total of 1 user still: ' + str(len(users)))
        # When the account is activated, it should not be deleted.
        email = u'testingactivated@gmail.com'
        UserMgr.signup_user(email, u'testcase')
        activations = Activation.query.all()
        users = User.query.all()
        self.assertEqual(
            1,
            len(activations),
            'We should have a total of 1 activation: ' + str(len(activations)))
        self.assertEqual(
            2,
            len(users),
            'We should have a total of 2 users: ' + str(len(users)))
        users[1].activated = True
        UserMgr.non_activated_account(delete=True)
        activations = Activation.query.all()
        users = User.query.all()
        self.assertEqual(
            1,
            len(activations),
            'We should have a total of 1 activation still')
        self.assertEqual(
            2,
            len(users),
            'We should have a total of 2 users still: ' + str(len(users)))
        # When the account last login is not None, it should not be deleted.
        # This happens when a user forgets his/her password.
        email = u'testinglastlogin@gmail.com'
        UserMgr.signup_user(email, u'testcase')
        activations = Activation.query.all()
        users = User.query.all()
        self.assertEqual(
            2,
            len(activations),
            'We should have a total of 2 activations')
        self.assertEqual(
            3,
            len(users),
            'We should have a total of 3 users: ' + str(len(users)))
        users[2].last_login = datetime.utcnow()
        UserMgr.non_activated_account(delete=True)
        activations = Activation.query.all()
        users = User.query.all()
        self.assertEqual(
            2,
            len(activations),
            'We should have a total of 2 activations still')
        self.assertEqual(
            3,
            len(users),
            'We should have a total of 3 users still: ' + str(len(users)))
        # The account should not be deleted before 30 days since signup.
        email = u'testingdays@gmail.com'
        UserMgr.signup_user(email, u'testcase')
        activations = Activation.query.all()
        users = User.query.all()
        self.assertEqual(
            3,
            len(activations),
            'We should have a total of 3 activations')
        self.assertEqual(
            4,
            len(users),
            'We should have a total of 4 users: ' + str(len(users)))
        UserMgr.non_activated_account(delete=True)
        activations = Activation.query.all()
        users = User.query.all()
        self.assertEqual(
            3,
            len(activations),
            'We should have a total of 3 activations still')
        self.assertEqual(
            4,
            len(users),
            'We should have a total of 4 users still')
        # The account details should be shown if it is not asked to delete.
        email = u'testingdetails@gmail.com'
        UserMgr.signup_user(email, u'testcase')
        activations = Activation.query.all()
        users = User.query.all()
        self.assertEqual(
            4,
            len(activations),
            'We should have a total of 4 activations')
        self.assertEqual(
            5,
            len(users),
            'We should have a total of 5 users: ' + str(len(users)))
        account_signup = datetime.utcnow() - timedelta(days=35)
        activations[3].valid_until = account_signup
        account_details = UserMgr.non_activated_account(delete=False)
        self.assertEqual(
            email,
            account_details[0].email)
        self.assertEqual(
            False,
            account_details[0].activated)
        self.assertEqual(
            u'testcase',
            account_details[0].invited_by)


class TestAuthMgr(TestCase):
    """Test User Manager"""

    def test_get_id(self):
        """Fetching user by the id"""
        # the migration adds an initial admin user to the system
        user = UserMgr.get(user_id=1)
        self.assertEqual(
            user.id,
            1,
            "Should have a user id of 1: " + str(user.id))
        self.assertEqual(
            user.username,
            'admin',
            "Should have a username of admin: " + user.username)

    def test_get_username(self):
        """Fetching the user by the username"""
        user = UserMgr.get(username=u'admin')
        self.assertEqual(
            user.id,
            1,
            "Should have a user id of 1: " + str(user.id))
        self.assertEqual(
            user.username,
            'admin',
            "Should have a username of admin: " + user.username)

    def test_get_bad_user(self):
        """We shouldn't get a hit if the user is inactive"""
        user = UserMgr.get(username=u'noexist')

        self.assertEqual(
            user,
            None,
            "Should not find a non-existant user: " + str(user))

########NEW FILE########
__FILENAME__ = test_reset
"""Test the password reset step process


- You've forgotten your password
- You enter your email into the forgotten password ui
    - Your account gets a activation record
    - Your account is deactivated
    - An email with the activation url is emailed to you
- You cannot re-enter the account for activation until the previous one is
  expired/or a successful reset has occurred
- While the account is deactivated you cannot make api calls or view login-only
  urls
- You follow the activation link and can reset your password
- At this point you can log in with the new password
- api and other calls now function

"""
import json
import logging
import transaction

from mock import patch
from pyramid import testing
from unittest import TestCase

from bookie.models import DBSession
from bookie.models.auth import Activation

LOG = logging.getLogger(__name__)


class TestReactivateFunctional(TestCase):

    def _reset_admin(self):
        """Reset the admin account"""
        DBSession.execute(
            "UPDATE users SET activated='1' WHERE username='admin';")
        Activation.query.delete()
        transaction.commit()

    def setUp(self):
        from pyramid.paster import get_app
        from bookie.tests import BOOKIE_TEST_INI
        app = get_app(BOOKIE_TEST_INI, 'bookie')
        from webtest import TestApp
        self.testapp = TestApp(app)
        testing.setUp()

    def tearDown(self):
        self._reset_admin()
        testing.tearDown()

    def test_activate_form_bad(self):
        """Test bad call to reset"""
        res = self.testapp.post(
            '/api/v1/suspend',
            content_type='application/json',
            status=406)
        success = json.loads(res.body)['error']
        self.assertTrue(
            success is not None,
            "Should not be successful with no email address: " + str(res))

        res = self.testapp.post('/api/v1/suspend',
                                params={'email': 'notexist@gmail.com'},
                                status=404)
        success = json.loads(res.body)
        self.assertTrue(
            'error' in success,
            "Should not be successful with invalid email address: " + str(res))

    @patch('bookie.lib.message.sendmail')
    def test_activate_form(self, mock_sendmail):
        """ Functional test to see if we can submit the api to reset an account

        Now by doing this we end up marking the account deactivated which
        causes other tests to 403 it up. Need to reinstate the admin account on
        tearDown

        """
        res = self.testapp.post('/api/v1/suspend',
                                params={'email': u'testing@dummy.com'},
                                status=200)

        success = json.loads(res.body)
        self.assertTrue(
            'message' in success,
            "Should be successful with admin email address: " + str(res))
        self.assertTrue(mock_sendmail.called)

    @patch('bookie.lib.message.sendmail')
    def test_activate_form_dual(self, mock_sendmail):
        """Test that we can't resubmit for reset, get prompted to email

        If we reset and then try to say "I've forgotten" a second time, we
        should get a nice message. And that message should allow us to get a
        second copy of the email sent.

        """
        res = self.testapp.post('/api/v1/suspend',
                                params={'email': u'testing@dummy.com'},
                                status=200)
        self.assertTrue(mock_sendmail.called)

        success = json.loads(res.body)
        self.assertTrue(
            'message' in success,
            "Should be successful with admin email address")

        res = self.testapp.post('/api/v1/suspend',
                                params={'email': u'testing@dummy.com'},
                                status=406)

        success = json.loads(res.body)
        self.assertTrue(
            'error' in success,
            "Should not be successful on second try: " + str(res))

        self.assertTrue(
            'already' in str(res),
            "Should find 'already' in the response: " + str(res))

    @patch('bookie.lib.message.sendmail')
    def test_reactivate_process(self, mock_sendmail):
        """Walk through all of the steps at a time

        - First we mark that we've forgotten
        - Then use make sure we get a 403 accessing something
        - Then we go back through our activation using our code
        - Finally verify we can access the earlier item

        """
        res = self.testapp.post('/api/v1/suspend',
                                params={'email': u'testing@dummy.com'},
                                status=200)
        self.assertTrue(mock_sendmail.called)

        success = json.loads(res.body)
        self.assertTrue(
            'message' in success,
            "Should be successful with admin email address")

        # now let's try to login
        # the migrations add a default admin account
        user_data = {'login': 'admin',
                     'password': 'admin',
                     'form.submitted': 'true'}

        res = self.testapp.post('/login',
                                params=user_data,
                                status=200)

        self.assertTrue(
            'account deactivated' in str(res),
            "Login should have failed since we're not active: " + str(res))

        act = Activation.query.first()
        self.testapp.delete(
            "/api/v1/suspend?username={0}&code={1}&password={2}".format(
                user_data['login'],
                act.code,
                'admin'),
            status=200)

        self.assertTrue(
            'activated' in str(res),
            "Should be prompted to login now: " + str(res))

        user_data = {'login': 'admin',
                     'password': 'admin',
                     'form.submitted': 'true'}

        res = self.testapp.post('/login',
                                params=user_data,
                                status=302)

########NEW FILE########
__FILENAME__ = test_signup
"""Test the limited signup process

"""
import logging
from urllib import (
    quote,
    urlencode,
)
import transaction

from bookie.models import DBSession
from bookie.models.auth import Activation
from bookie.models.auth import User
from bookie.models.auth import UserMgr

from bookie.tests import gen_random_word
from bookie.tests import TestDBBase
from bookie.tests import TestViewBase


LOG = logging.getLogger(__name__)


class TestInviteSetup(TestDBBase):
    """Verify we have/can work with the invite numbers"""

    def testHasNoInvites(self):
        """Verify that if the user has no invites, they can't invite"""
        u = User()
        u.invite_ct = 0
        self.assertFalse(u.has_invites(), 'User should have no invites')
        self.assertFalse(
            u.invite('me@you.com'), 'Should not be able to invite a user')

    def testInviteCreatesUser(self):
        """We should get a new user when inviting something"""
        me = User()
        me.username = u'me'
        me.email = u'me.com'
        me.invite_ct = 2
        you = me.invite(u'you.com')

        self.assertEqual(
            'you.com',
            you.username,
            'The email should be the username')
        self.assertEqual(
            'you.com',
            you.email,
            'The email should be the email')
        self.assertTrue(
            len(you.api_key),
            'The api key should be generated for the user')
        self.assertFalse(
            you.activated,
            'The new user should not be activated')
        self.assertEqual(
            1,
            me.invite_ct,
            'My invite count should be deprecated')


class TestSigningUpUser(TestDBBase):
    """Start out by verifying a user starts out in the right state"""

    def testInitialUserInactivated(self):
        """A new user signup should be a deactivated user"""
        u = User()
        u.email = gen_random_word(10)
        DBSession.add(u)

        self.assertEqual(
            False,
            u.activated,
            'A new signup should start out deactivated by default')
        self.assertTrue(
            u.activation.code is not None,
            'A new signup should start out as deactivated')
        self.assertEqual(
            'signup',
            u.activation.created_by,
            'This is a new signup, so mark is as thus')


class TestOpenSignup(TestViewBase):
    """New users can request a signup for an account."""

    def tearDown(self):
        super(TestOpenSignup, self).tearDown()
        User.query.filter(User.email == u'testing@newuser.com').delete()

    def testSignupRenders(self):
        """A signup form is kind of required."""
        res = self.app.get('/signup')

        self.assertIn('Sign up for Bookie', res.body)
        self.assertNotIn('class="error"', res.body)

    def testEmailRequired(self):
        """Signup requires an email entry."""
        res = self.app.post('/signup_process')
        self.assertIn('Please supply', res.body)

    def testEmailAlreadyThere(self):
        """Signup requires an email entry."""
        res = self.app.post(
            '/signup_process',
            params={
                'email': 'testing@dummy.com'
            }
        )
        self.assertIn('already signed up', res.body)

    def testEmailIsLowercase(self):
        """Signup saves email as all lowercase"""
        res = self.app.post(
            '/signup_process',
            params={
                'email': 'CAPITALTesting@Dummy.cOm'
            }
        )
        self.assertIn('capitaltesting@dummy.com', res.body)

    def testUsernameAlreadyThere(self):
        """Signup requires an unique username entry."""
        email = 'testing@gmail.com'
        new_user = UserMgr.signup_user(email, u'invite')
        DBSession.add(new_user)

        transaction.commit()

        user = DBSession.query(User).filter(User.username == email).one()

        url = quote('/{0}/reset/{1}'.format(
            user.email,
            user.activation.code
        ))

        res = self.app.post(
            url,
            params={
                'password': u'testing',
                'username': user.username,
                'code': user.activation.code,
                'new_username': u'admin',
            })
        self.assertIn('Username already', res.body)

    def testResetFormDisplay(self):
        """Make sure you can GET the reset form."""
        email = 'testing@gmail.com'
        new_user = UserMgr.signup_user(email, u'invite')
        DBSession.add(new_user)

        transaction.commit()

        user = DBSession.query(User).filter(User.username == email).one()

        url = quote('/{0}/reset/{1}'.format(
            user.email,
            user.activation.code
        ))

        res = self.app.get(url)
        self.assertIn('Activate', res.body)

    def testUsernameIsLowercase(self):
        """Signup saves username as all lowercase"""
        email = 'TestingUsername@test.com'
        new_user = UserMgr.signup_user(email, u'testcase')
        DBSession.add(new_user)

        transaction.commit()

        user = DBSession.query(User).filter(
            User.username == email.lower()).one()

        params = {
            'password': u'testing',
            'username': user.username,
            'code': user.activation.code,
            'new_username': 'TESTLowercase'
        }
        url = '/api/v1/suspend?' + urlencode(params, True)

        # Activate the user, setting their new username which we want to
        # verify does get lower cased during this process.
        self.app.delete(url)

        user = DBSession.query(User).filter(User.email == email.lower()).one()
        self.assertIn('testlowercase', user.username)

    def testSignupWorks(self):
        """Signing up stores an activation."""
        email = u'testing@newuser.com'
        UserMgr.signup_user(email, u'testcase')

        activations = Activation.query.all()

        self.assertTrue(len(activations) == 1)
        act = activations[0]

        self.assertEqual(
            email,
            act.user.email,
            "The activation email is the correct one.")

########NEW FILE########
__FILENAME__ = test_bcelery
import transaction

from bookie.bcelery import tasks
from bookie.models import Bmark
from bookie.models import DBSession
from bookie.models import Tag
from bookie.models import stats
from bookie.models.auth import User
from bookie.models.stats import StatBookmark

from bookie.tests import empty_db
from bookie.tests import gen_random_word
from bookie.tests import TestDBBase


class BCeleryTaskTest(TestDBBase):
    """ Test the celery task runner """

    def setUp(self):
        """Populate the DB with a couple of testing records"""
        trans = transaction.begin()
        user = User()
        user.username = gen_random_word(10)
        self.username = user.username
        DBSession.add(user)

        for i in range(3):
            url = gen_random_word(12)
            b = self.__create_bookmark(url, user.username)
            DBSession.add(b)

        # add bookmark with duplicate url
        new_user = User()
        new_user.username = gen_random_word(10)
        self.new_username = new_user.username
        DBSession.add(new_user)

        b = self.__create_bookmark(url, new_user.username)
        DBSession.add(b)

        trans.commit()

    def __create_bookmark(self, url, username):
        """Helper that creates a bookmark object with a random tag"""
        b = Bmark(
            url=url,
            username=username
        )
        tagname = gen_random_word(5)
        b.tags[tagname] = Tag(tagname)
        return b

    def tearDown(self):
        """clear out all the testing DB data"""
        empty_db()

    def test_task_unique_total(self):
        """The task should generate a unique count stat record"""
        # from bookie.bcelery import tasks
        tasks.count_unique()

        stat = StatBookmark.query.first()
        self.assertEqual(stat.attrib, stats.UNIQUE_CT)
        self.assertEqual(stat.data, 3)

    def test_task_count_total(self):
        """The task should generate a total count stat record"""
        tasks.count_total()

        stat = StatBookmark.query.first()
        self.assertEqual(stat.attrib, stats.TOTAL_CT)
        self.assertEqual(stat.data, 4)

    def test_task_count_tags(self):
        """The task should generate a tag count stat record"""
        tasks.count_tags()

        stat = StatBookmark.query.first()
        self.assertEqual(stat.attrib, stats.TAG_CT)
        self.assertEqual(stat.data, 4)

    def test_task_count_user_total(self):
        """The task should generate a total count stat record of a user"""
        tasks.count_total_each_user()

        stats = StatBookmark.query.all()

        expected = {
            'admin': 0,
            self.username: 4,
            self.new_username: 3,
        }

        for stat in stats:
            user_key = stat.attrib.split('_')
            username = user_key[2]
            self.assertTrue(username in expected)
            self.assertEqual(expected[username], stat.data)

########NEW FILE########
__FILENAME__ = test_tagcommands
"""Test the tag commands system"""
from unittest import TestCase
from bookie.lib.tagcommands import COMMANDLIST
from bookie.lib.tagcommands import Commander
from bookie.lib.tagcommands import IsRead
from bookie.lib.tagcommands import ToRead
from bookie.models import DBSession

from bookie.tests import empty_db


# tags act as a dict on the Bmark object, so we're just mocking things
# out a bit simpler using that metaphor.
class BmarkMock(object):

    def __init__(self):
        self.tags = {}


class CommandMock(object):

    @staticmethod
    def run(bmark):
        return bmark


class TestTagCommander(TestCase):
    """Commander system"""

    def setUp(self):
        """Store off the commands so we can return them"""
        self.saved_commandlist = COMMANDLIST
        for key in COMMANDLIST.keys():
            del(COMMANDLIST[key])
        DBSession.execute("INSERT INTO tags (name) VALUES ('toread')")

    def tearDown(self):
        """Make sure we clear the commands we put in there"""
        for key in self.saved_commandlist:
            COMMANDLIST[key] = self.saved_commandlist[key]
        empty_db()

    def test_command_finds_commands(self):
        """Verify we find commands that we know about"""
        COMMANDLIST['!toread'] = lambda bmark: bmark

        bm = BmarkMock()
        bm.tags['!toread'] = True
        commander = Commander(bm)
        commander.build_commands()

        self.assertTrue(
            '!toread' in commander.commands,
            "Our commander should find !toread command to run")

    def test_command_tags_removed(self):
        """Test that the command tags are not left over in bmark object"""

        COMMANDLIST['!toread'] = CommandMock

        bm = BmarkMock()
        bm.tags['!toread'] = True
        commander = Commander(bm)
        updated = commander.process()

        self.assertTrue(
            '!toread' not in updated.tags,
            "Our commander should find !toread command to run")


class TestToRead(TestCase):
    """Test the ToRead Command"""

    def setUp(self):
        """Store off the commands so we can return them"""
        self.saved_commandlist = COMMANDLIST
        for key in COMMANDLIST.keys():
            del(COMMANDLIST[key])
        DBSession.execute("INSERT INTO tags (name) VALUES ('toread')")

    def tearDown(self):
        """Make sure we clear the commands we put in there"""
        for key in self.saved_commandlist:
            COMMANDLIST[key] = self.saved_commandlist[key]
        empty_db()

    def test_toread_command(self):
        """If marked toread, then should end up with tag 'toread' on it"""
        bm = BmarkMock()
        updated = ToRead.run(bm)
        self.assertTrue(
            'toread' in updated.tags,
            "Updated bmark should have 'toread' tag set")

    def test_toread_in_commandset(self):
        """Make sure we can process this command through the commander"""
        COMMANDLIST['!toread'] = ToRead

        bm = BmarkMock()
        bm.tags['!toread'] = True
        commander = Commander(bm)
        updated = commander.process()

        self.assertTrue(
            'toread' in updated.tags,
            "Should have the toread tag in the updated bookmark")
        self.assertTrue(
            '!toread' not in updated.tags,
            "Should not have the !toread tag in the updated bookmark")


class TestIsRead(TestCase):
    """Test the IsRead Command"""

    def setUp(self):
        """Store off the commands so we can return them"""
        self.saved_commandlist = COMMANDLIST
        for key in COMMANDLIST.keys():
            del(COMMANDLIST[key])

    def tearDown(self):
        """Make sure we clear the commands we put in there"""
        for key in self.saved_commandlist:
            COMMANDLIST[key] = self.saved_commandlist[key]

    def test_isread_command(self):
        """Should remove the toread tag on a bookmark"""
        bm = BmarkMock()
        bm.tags['toread'] = True
        updated = IsRead.run(bm)
        self.assertTrue(
            'toread' not in updated.tags,
            "Updated bmark should not have 'toread' tag set")

########NEW FILE########
__FILENAME__ = test_readable
"""Test the function of the readable library."""
from unittest import TestCase

from bookie.lib import readable


class TestReadUrl(TestCase):
    """Verify ReadUrl functions"""

    def setUp(self):
        """Setup Tests"""
        pass

    def tearDown(self):
        """Tear down each test"""
        pass

    def test_parse_malformed_url(self):
        """Properly error on an unparseable url."""
        url = u'http://whttp://lucumr.pocoo.org/2012/8/5/stateless-and-proud/'
        read = readable.ReadUrl.parse(url)
        self.assertEqual(read.status, 901)

    def test_unfetchable_url(self):
        """Cannot fetch content for unreadable urls.

        Urls that are with:

            chrome://
            file://

        etc, cannot have their content fetched so don't bother.

        """
        url = u'file://test.html'
        read = readable.ReadUrl.parse(url)
        self.assertEqual(read.status, 901)

########NEW FILE########
__FILENAME__ = test_urlhash
"""Test the function of the url hash helpers."""
from unittest import TestCase

from bookie.lib.urlhash import generate_hash


class TestUrlHashing(TestCase):
    """Verify UrlHashing works properly"""

    def test_hash_url(self):
        """Hashes base url correctly"""
        url = u'http://google.com'
        hashed = generate_hash(url)
        self.assertEqual('aa2239c17609b2', hashed)

    def test_unicode_url(self):
        """Hashes with unicode correctly"""
        url = u'http://www.bizrevolution.com.br/bizrevolution/2011/02/somos-t\xe3o-jovens-no-campus-party-.html'  # noqa
        hashed = generate_hash(url)
        self.assertEqual('bd846e7222adf2', hashed)

########NEW FILE########
__FILENAME__ = test_bmarkmgr
"""Test the basics including the bmark and tags"""

from random import randint
from pyramid import testing

from bookie.models import (
    DBSession,
    Bmark,
    BmarkMgr,
    TagMgr,
)
from bookie.models.auth import User

from bookie.tests import empty_db
from bookie.tests import gen_random_word
from bookie.tests import TestDBBase


class TestBmarkMgrStats(TestDBBase):
    """Handle some bmarkmgr stats checks"""

    def setUp(self):
        """Setup Tests"""
        from pyramid.paster import get_app
        from bookie.tests import BOOKIE_TEST_INI
        app = get_app(BOOKIE_TEST_INI, 'bookie')
        from webtest import TestApp
        self.testapp = TestApp(app)
        testing.setUp()

    def tearDown(self):
        """Tear down each test"""
        testing.tearDown()
        empty_db()

    def test_total_ct(self):
        """Verify that our total count method is working"""
        ct = 5
        user = User()
        user.username = gen_random_word(10)
        DBSession.add(user)
        for i in range(ct):
            b = Bmark(
                url=gen_random_word(12),
                username=user.username
            )
            b.hash_id = gen_random_word(3)
            DBSession.add(b)

        ct = BmarkMgr.count()
        self.assertEqual(5, ct, 'We should have a total of 5: ' + str(ct))

    def test_unique_ct(self):
        """Verify that our unique count method is working"""
        ct = 5
        common = u'testing.com'
        users = []
        for i in range(ct):
            user = User()
            user.username = gen_random_word(10)
            DBSession.add(user)
            users.append(user)

        for i in range(ct - 2):
            b = Bmark(
                url=gen_random_word(12),
                username=users[i].username
            )
            DBSession.add(b)

        # Add in our dupes
        c = Bmark(
            url=common,
            username=users[3].username
        )
        DBSession.add(c)
        DBSession.flush()

        d = Bmark(
            url=common,
            username=users[4].username
        )
        DBSession.add(d)
        DBSession.flush()

        ct = BmarkMgr.count(distinct=True)
        self.assertEqual(4, ct, 'We should have a total of 4: ' + str(ct))

    def test_per_user(self):
        """We should only get a pair of results for this single user"""
        ct = 5
        common = u'testing.com'
        user = User()
        user.username = gen_random_word(10)
        DBSession.add(user)

        usercommon = User()
        usercommon.username = common
        DBSession.add(usercommon)

        for i in range(ct - 2):
            b = Bmark(
                url=gen_random_word(12),
                username=user.username
            )
            DBSession.add(b)

        # add in our dupes
        c = Bmark(
            url=gen_random_word(10),
            username=usercommon.username,
        )
        DBSession.add(c)
        DBSession.flush()

        d = Bmark(
            url=gen_random_word(10),
            username=usercommon.username,
        )
        DBSession.add(d)
        DBSession.flush()

        ct = BmarkMgr.count(username=usercommon.username)
        self.assertEqual(2, ct, 'We should have a total of 2: ' + str(ct))

    def test_delete_all_bookmarks(self):
        """Testing working of delete all bookmarks
                Case 1: No bookmark present
                Case 2: One bookmark present
                Case 3: Multiple bookmarks present"""

        bmark_counts = [0, 1]
        for i in range(10):
            bmark_counts.append(randint(10, 100))

        users = []
        for i in range(len(bmark_counts)):
            user = User()
            user.username = gen_random_word(10)
            users.append(user)

            DBSession.add(user)
            for j in range(i):
                b = Bmark(
                    url=gen_random_word(12),
                    username=user.username,
                    tags=gen_random_word(4),
                )
                b.hash_id = gen_random_word(3)
                DBSession.add(b)

        DBSession.flush()

        for user in users:
            BmarkMgr.delete_all_bookmarks(user.username)
            ct = BmarkMgr.count(user.username)
            self.assertEqual(ct, 0, 'All the bookmarks should be deleted')
            tags = TagMgr.find(username=user.username)
            self.assertEqual(
                len(tags),
                0,
                'There should be no tags left: ' + str(len(tags))
            )
            DBSession.flush()

########NEW FILE########
__FILENAME__ = test_privatebmark
"""Test private bookmark support"""

from pyramid import testing

from bookie.models import Bmark
from bookie.models.auth import User

from bookie.tests import empty_db
from bookie.tests import gen_random_word
from bookie.tests import TestDBBase


class TestPrivateBmark(TestDBBase):
    """Handle private bookmark checks"""

    def setUp(self):
        """Setup Tests"""
        from pyramid.paster import get_app
        from bookie.tests import BOOKIE_TEST_INI
        app = get_app(BOOKIE_TEST_INI, 'bookie')
        from webtest import TestApp
        self.testapp = TestApp(app)
        testing.setUp()

    def tearDown(self):
        """Tear down each test"""
        testing.tearDown()
        empty_db()

    def test_is_private_default(self):
        """Verify the default value of is_private"""
        user = User()
        user.username = gen_random_word(10)
        bmark = Bmark(
            url=gen_random_word(12),
            username=user.username
        )
        self.assertEqual(
            True,
            bmark.is_private,
            'Default value of is_private should be True')

    def test_is_private_true(self):
        """Verify the value of is_private is True"""
        user = User()
        user.username = gen_random_word(10)
        bmark = Bmark(
            url=gen_random_word(12),
            username=user.username,
            is_private=True
        )
        self.assertEqual(
            True,
            bmark.is_private)

    def test_is_private_false(self):
        """Verify the value of is_private is False"""
        user = User()
        user.username = gen_random_word(10)
        bmark = Bmark(
            url=gen_random_word(12),
            username=user.username,
            is_private=False
        )
        self.assertEqual(
            False,
            bmark.is_private)

########NEW FILE########
__FILENAME__ = test_tagmgr
"""Test the basics including the bmark and tags"""
import transaction
from pyramid import testing

from bookie.models import (
    Readable,
    DBSession,
    Tag,
    TagMgr,
    BmarkMgr,
)

from bookie.tests import empty_db
from bookie.tests import gen_random_word
from bookie.tests import TestDBBase
from bookie.tests.factory import (
    make_bookmark,
    make_tag,
)

import os


class TestTagMgrStats(TestDBBase):
    """Handle some TagMgr stats checks"""

    def setUp(self):
        """Setup Tests"""
        from pyramid.paster import get_app
        from bookie.tests import BOOKIE_TEST_INI
        app = get_app(BOOKIE_TEST_INI, 'bookie')
        from webtest import TestApp
        self.testapp = TestApp(app)
        testing.setUp()

    def tearDown(self):
        """Tear down each test"""
        testing.tearDown()
        empty_db()

    def test_total_ct(self):
        """Verify that our total count method is working"""
        ct = 5
        for i in range(ct):
            t = Tag(gen_random_word(10))
            DBSession.add(t)

        ct = TagMgr.count()
        self.assertEqual(5, ct, 'We should have a total of 5: ' + str(ct))

    def test_basic_complete(self):
        """Tags should provide completion options."""
        # Generate demo tag into the system
        tags = [make_tag() for i in range(5)]
        [DBSession.add(t) for t in tags]

        test_str = tags[0].name[0:2]
        suggestions = TagMgr.complete(test_str)

        self.assertTrue(
            tags[0] in suggestions,
            "The sample tag was found in the completion set")

    def test_case_insensitive(self):
        """Suggestion does not care about case of the prefix."""
        # Generate demo tag into the system
        tags = [make_tag() for i in range(5)]
        [DBSession.add(t) for t in tags]

        test_str = tags[0].name[0:4].upper()
        suggestions = TagMgr.complete(test_str)
        self.assertTrue(
            tags[0] in suggestions,
            "The sample tag was found in the completion set")

    def test_suggested_tags(self):
        """Suggestions based on the content of the bookmarked page"""
        # login into bookie
        user_data = {'login': u'admin',
                     'password': u'admin',
                     'form.submitted': u'true'}
        res = self.testapp.post('/login',
                                params=user_data)
        # Add a bookmark
        res = DBSession.execute(
            "SELECT api_key FROM users WHERE username = 'admin'").fetchone()
        key = res['api_key']
        url = u'http://testing_tags.com'
        # set the readable content for the bookmark
        path = os.getcwd()+"/bookie/tests/test_models/tag_test.txt"
        content = open(path, 'r').read()
        test_bmark = {
            'url': url,
            'description': u'Bookie',
            'extended': u'',
            'tags': u'',
            'api_key': key,
            'content': content,
        }
        res = self.testapp.post('/api/v1/admin/bmark',
                                params=test_bmark,
                                status=200)

        bmark = BmarkMgr.get_by_url(url)
        hash_id = bmark.hash_id
        tags_expected = ['network', 'new', 'simulator', 'user']
        edit_bmark = {
            'hash_id': hash_id,
            'username': 'admin',
            'url': url
        }
        hash_id = str(hash_id)
        res = self.testapp.post('/admin/edit/' + hash_id,
                                params=edit_bmark,
                                status=200)
        # pure numbers are eliminated
        self.assertNotIn('2014', res.body)
        # tags with length less than 3 are omitted
        self.assertNotIn('NS', res.body)
        # all tags are lower cased
        self.assertNotIn('NEW', res.body)
        for tag in tags_expected:
                self.assertIn(tag, res.body)

    def test_suggested_tags_for_unparsed_bookmark(self):
        """Suggested tags for a bookmarked page whose readable is None"""
        # Login into bookie
        user_data = {'login': u'admin',
                     'password': u'admin',
                     'form.submitted': u'true'}
        self.testapp.post('/login',
                          params=user_data)
        # Add a bookmark
        test_bmark = make_bookmark()
        test_bmark.url = u'http://testing_tags.com'
        test_bmark.description = u'Bookie'
        path = os.getcwd() + "/bookie/tests/test_models/tag_test.txt"
        content = open(path, 'r').read()
        test_bmark.readable = Readable(content=content)

        # Add another bookmark with readable as None
        new_url = u'http://testing_readable_none.com'
        no_readable_bmark = make_bookmark()
        no_readable_bmark.url = new_url
        no_readable_bmark.description = u'Readable of this bookmark is None'

        DBSession.add(test_bmark)
        DBSession.add(no_readable_bmark)
        DBSession.flush()
        no_readable_hash = no_readable_bmark.hash_id

        transaction.commit()

        edit_bmark = {
            'hash_id': no_readable_hash,
            'username': 'admin',
        }

        # As the Bookmark's readable is None the page should load without
        # error.
        self.testapp.post(
            u'/admin/edit/' + no_readable_hash,
            params=edit_bmark,
            status=200)

########NEW FILE########
__FILENAME__ = test_export
"""Tests that we make sure our export functions work"""
import json
import logging

import urllib

from bookie.tests import TestViewBase


LOG = logging.getLogger(__name__)
API_KEY = None


class TestExport(TestViewBase):
    """Test the web export"""

    def _get_good_request(self):
        """Return the basics for a good add bookmark request"""
        prms = {
            'url': u'http://google.com',
            'description': u'This is my google desc',
            'extended': u'And some extended notes about it in full form',
            'tags': u'python search',
        }

        req_params = urllib.urlencode(prms)
        res = self.app.post(
            '/api/v1/admin/bmark?api_key={0}'.format(self.api_key),
            params=req_params,
        )
        return res

    def _get_good_request_wo_tags(self):
        """Return the basics for a good add bookmark request
            without any tags"""
        prms = {
            'url': u'http://bmark.us',
            'description': u'This is my bmark desc',
            'extended': u'And some extended notes about it in full form',
            'tags': u'',
        }

        req_params = urllib.urlencode(prms)
        res = self.app.post(
            '/api/v1/admin/bmark?api_key={0}'.format(self.api_key),
            params=req_params,
        )
        return res

    def test_export(self):
        """Test that we can upload/import our test file"""
        self._get_good_request()

        res = self.app.get(
            '/api/v1/admin/bmarks/export?api_key={0}'.format(
                self.api_key),
            status=200)

        self.assertTrue(
            "google.com" in res.body,
            msg='Google is in the exported body: ' + res.body)
        data = json.loads(res.body)

        self.assertEqual(
            1,
            data['count'],
            "Should be one result: " + str(data['count']))

    def test_export_wo_tags(self):
        """Test that we can upload/import our test file"""
        self._get_good_request_wo_tags()

        res = self.app.get(
            '/api/v1/admin/bmarks/export?api_key={0}'.format(
                self.api_key),
            status=200)

        self.assertTrue(
            "bmark.us" in res.body,
            msg='Bmark is in the exported body: ' + res.body)
        data = json.loads(res.body)

        self.assertEqual(
            1,
            data['count'],
            "Should be one result: " + str(data['count']))

########NEW FILE########
__FILENAME__ = test_fulltext
"""Test the fulltext implementation"""
import transaction
import urllib

from pyramid import testing
from unittest import TestCase

from bookie.models import DBSession
from bookie.models.fulltext import WhooshFulltext
from bookie.models.fulltext import get_fulltext_handler
from bookie.tests import empty_db

API_KEY = None


class TestFulltext(TestCase):
    """Test that our fulltext classes function"""

    def setUp(self):
        """Setup Tests"""
        from pyramid.paster import get_app
        from bookie.tests import BOOKIE_TEST_INI
        app = get_app(BOOKIE_TEST_INI, 'bookie')
        from webtest import TestApp
        self.testapp = TestApp(app)
        testing.setUp()
        global API_KEY
        if API_KEY is None:
            res = DBSession.execute(
                "SELECT api_key FROM users WHERE username = 'admin'").\
                fetchone()
            API_KEY = res['api_key']

    def tearDown(self):
        """Tear down each test"""
        testing.tearDown()
        empty_db()

    def _get_good_request(self, new_tags=None):
        """Return the basics for a good add bookmark request"""
        session = DBSession()
        prms = {
            'url': u'http://google.com',
            'description': u'This is my google desc SEE',
            'extended': u'And some extended notes about it in full form',
            'tags': u'python search',
            'api_key': API_KEY,
        }

        if new_tags:
            prms['tags'] = new_tags

        req_params = urllib.urlencode(prms)
        res = self.testapp.post('/api/v1/admin/bmark',
                                params=req_params)

        session.flush()
        transaction.commit()
        from bookie.bcelery import tasks
        tasks.reindex_fulltext_allbookmarks(sync=True)
        return res

    def test_get_handler(self):
        """Verify we get the right type of full text store object"""
        handler = get_fulltext_handler("")

        self.assertTrue(
            isinstance(handler, WhooshFulltext),
            "Should get a whoosh fulltext by default")

    def test_sqlite_save(self):
        """Verify that if we store a bookmark we get the fulltext storage"""
        # first let's add a bookmark we can search on
        self._get_good_request()

        search_res = self.testapp.get('/api/v1/admin/bmarks/search/google')
        self.assertTrue(
            search_res.status == '200 OK',
            "Status is 200: " + search_res.status)
        self.assertTrue(
            'my google desc' in search_res.body,
            "We should find our description on the page: " + search_res.body)

        search_res = self.testapp.get('/api/v1/admin/bmarks/search/python')
        self.assertTrue(
            search_res.status == '200 OK',
            "Status is 200: " + search_res.status)

        self.assertTrue(
            'my google desc' in search_res.body,
            "Tag search should find our description on the page: " +
            search_res.body)

        search_res = self.testapp.get(
            '/api/v1/admin/bmarks/search/extended%20notes')
        self.assertTrue(
            search_res.status == '200 OK',
            "Status is 200: " + search_res.status)
        self.assertTrue(
            'extended notes' in search_res.body,
            "Extended search should find our description on the page: " +
            search_res.body)

    def test_sqlite_update(self):
        """Verify that if we update a bookmark, fulltext is updated

        We need to make sure that updates to the record get cascaded into the
        fulltext table indexes

        """
        self._get_good_request()

        # now we need to do another request with updated tag string
        self._get_good_request(new_tags=u"google books icons")

        search_res = self.testapp.get('/admin/results?search=icon')
        self.assertTrue(
            search_res.status == '200 OK',
            "Status is 200: " + search_res.status)

        self.assertTrue(
            'icon' in search_res.body,
            "We should find the new tag icon on the page: " + search_res.body)

    def test_ajax_search(self):
        """Verify that we can get a json MorJSON response when ajax search"""
        # first let's add a bookmark we can search on
        self._get_good_request()
        search_res = self.testapp.get(
            '/admin/results/google',
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            }
        )

        self.assertTrue(
            search_res.status == '200 OK',
            "Status is 200: " + search_res.status)

        self.assertTrue(
            'my google desc' in search_res.body,
            "We should find our description on the page: " + search_res.body)

        # also check for our specific json bits
        self.assertTrue(
            'success' in search_res.body,
            "We should see a success bit in the json: " + search_res.body)

        self.assertTrue(
            'payload' in search_res.body,
            "We should see a payload bit in the json: " + search_res.body)

        self.assertTrue(
            'message' in search_res.body,
            "We should see a message bit in the json: " + search_res.body)

########NEW FILE########
__FILENAME__ = test_imports
"""Test that we're meeting delicious API specifications"""
import logging
import os
import StringIO
import transaction
import unittest

from datetime import datetime

from bookie.models import DBSession
from bookie.models import Bmark
from bookie.models.queue import ImportQueue
from bookie.models.queue import ImportQueueMgr
from bookie.lib.urlhash import generate_hash

from bookie.lib.importer import Importer
from bookie.lib.importer import DelImporter
from bookie.lib.importer import DelXMLImporter
from bookie.lib.importer import GBookmarkImporter
from bookie.lib.importer import FBookmarkImporter

from bookie.tests import TestViewBase
from bookie.tests import empty_db


LOG = logging.getLogger(__name__)

API_KEY = None


class TestImports(unittest.TestCase):

    def _delicious_data_test(self):
        """Test that we find the correct set of declicious data after import"""
        # Blatant copy/paste, but I'm on a plane right now so oh well.
        # Now let's do some db sanity checks.
        res = Bmark.query.all()
        self.assertEqual(
            len(res),
            19,
            "We should have 19 results, we got: " + str(len(res)))

        # verify we can find a bookmark by url and check tags, etc
        check_url = u'http://www.ndftz.com/nickelanddime.png'
        check_url_hashed = generate_hash(check_url)
        found = Bmark.query.filter(Bmark.hash_id == check_url_hashed).one()

        self.assertTrue(
            found.hashed.url == check_url, "The url should match our search")
        self.assertEqual(
            len(found.tags),
            7,
            "We should have gotten 7 tags, got: " + str(len(found.tags)))
        self.assertEqual(
            'importer',
            found.inserted_by,
            "The bookmark should have imported: " + found.inserted_by)

        # and check we have a right tag or two
        self.assertTrue(
            'canonical' in found.tag_string(),
            'Canonical should be a valid tag in the bookmark')

        # and check the long description field
        self.assertTrue(
            "description" in found.extended,
            "The extended attrib should have a nice long string in it")

    def _delicious_xml_data_test(self):
        """Test that we find the correct google bmark data after import"""
        res = Bmark.query.all()
        self.assertEqual(
            len(res),
            25,
            "We should have 25 results, we got: " + str(len(res)))

        # verify we can find a bookmark by url and check tags, etc
        check_url = 'http://jekyllrb.com/'
        check_url_hashed = generate_hash(check_url)
        found = Bmark.query.filter(Bmark.hash_id == check_url_hashed).one()

        self.assertTrue(
            found.hashed.url == check_url, "The url should match our search")
        self.assertEqual(
            len(found.tags), 6,
            "We should have gotten 6 tags, got: " + str(len(found.tags)))

        # and check we have a right tag or two
        self.assertTrue(
            'ruby' in found.tag_string(),
            'ruby should be a valid tag in the bookmark')

        # and check the long description field
        self.assertTrue(
            'added for test' in found.extended,
            "'added for test' should be in the extended description")

    def _google_data_test(self):
        """Test that we find the correct google bmark data after import"""
        res = Bmark.query.all()
        self.assertEqual(
            len(res),
            9,
            "We should have 9 results, we got: " + str(len(res)))

        # verify we can find a bookmark by url and check tags, etc
        check_url = 'http://www.alistapart.com/'
        check_url_hashed = generate_hash(check_url)
        found = Bmark.query.filter(Bmark.hash_id == check_url_hashed).one()

        self.assertTrue(
            found.hashed.url == check_url, "The url should match our search")
        self.assertEqual(
            len(found.tags),
            4,
            "We should have gotten 4 tags, got: " + str(len(found.tags)))

        # and check we have a right tag or two
        self.assertTrue(
            'html' in found.tag_string(),
            'html should be a valid tag in the bookmark')

        # and check the long description field
        self.assertTrue(
            "make websites" in found.extended,
            "'make websites' should be in the extended description")

    def _chrome_data_test(self):
        """Test that we find the correct Chrome bmark data after import"""
        res = Bmark.query.all()
        self.assertEqual(
            len(res),
            4,
            "We should have 4 results, we got: " + str(len(res)))

        # Verify we can find a bookmark by url and check tags, etc
        check_url = 'https://addons.mozilla.org/en-US/firefox/bookmarks/'
        check_url_hashed = generate_hash(check_url)
        found = Bmark.query.filter(Bmark.hash_id == check_url_hashed).one()

        self.assertTrue(
            found.hashed.url == check_url, "The url should match our search")
        self.assertEqual(
            len(found.tags),
            2,
            "We should have gotten 2 tags, got: " + str(len(found.tags)))

        # and check we have a right tag or two
        self.assertTrue(
            'imported-from-firefox' in found.tag_string(),
            'imported-from-firefox should be a valid tag in the bookmark')

        # and check the timestamp is correct
        # relative to user's timezone
        date_should_be = datetime.fromtimestamp(1350353334)
        self.assertEqual(date_should_be, found.stored)

    def _firefox_data_test(self):
        """Verify we find the correct firefox backup bmark data after import"""
        res = Bmark.query.all()
        self.assertEqual(
            len(res),
            13,
            "We should have 13 results, we got: " + str(len(res)))

        # Verify we can find a bookmark by url and check tags, etc
        check_url = 'https://github.com/bookieio/Bookie'
        check_url_hashed = generate_hash(check_url)
        found = Bmark.query.filter(Bmark.hash_id == check_url_hashed).one()

        self.assertTrue(
            found.hashed.url == check_url, "The url should match our search")
        self.assertEqual(
            len(found.tags),
            2,
            "We should have gotten 2 tags, got: " + str(len(found.tags)))

        # and check we have a right tag or two
        self.assertTrue(
            'myfav' in found.tag_string(),
            'myfav should be a valid tag in the bookmark')

        # and check the timestamp is correct
        # relative to user's timezone
        date_should_be = datetime.fromtimestamp(1394649032847102/1e6)
        self.assertEqual(date_should_be, found.stored)


class ImporterBaseTest(TestImports):
    """Verify the base import class is working"""

    def test_doesnt_implement_can_handle(self):
        """Verify we get the exception expected when running can_handle"""
        self.assertRaises(NotImplementedError, Importer.can_handle, "")

    def test_doesnt_implement_process(self):
        """Verify we get the exception expected when running process"""
        some_io = StringIO.StringIO()
        imp = Importer(some_io)
        self.assertRaises(NotImplementedError, imp.process)

    def test_factory_gives_delicious(self):
        """"Verify that the base importer will give DelImporter"""
        loc = os.path.dirname(__file__)
        del_file = os.path.join(loc, 'delicious.html')

        with open(del_file) as del_io:
            imp = Importer(del_io, username=u"admin")

            self.assertTrue(
                isinstance(imp, DelImporter),
                "Instance should be a delimporter instance")

    def test_factory_gives_google(self):
        """"Verify that the base importer will give GBookmarkImporter"""
        loc = os.path.dirname(__file__)
        google_file = os.path.join(loc, 'googlebookmarks.html')

        with open(google_file) as google_io:
            imp = Importer(google_io, username=u"admin")

            self.assertTrue(
                isinstance(imp, GBookmarkImporter),
                "Instance should be a GBookmarkImporter instance")


class ImportDeliciousTest(TestImports):
    """Test the Bookie importer for delicious"""

    def _get_del_file(self):
        """We need to get the locally found delicious.html file for tests"""
        loc = os.path.dirname(__file__)
        del_file = os.path.join(loc, 'delicious.html')

        return open(del_file)

    def setUp(self):
        """Regular setup hooks"""
        pass

    def tearDown(self):
        """Regular tear down method"""
        empty_db()

    def test_is_delicious_file(self):
        """Verify that this is a delicious file"""
        good_file = self._get_del_file()

        self.assertTrue(
            DelImporter.can_handle(good_file),
            "DelImporter should handle this file")

        good_file.close()

    def test_is_not_delicious_file(self):
        """And that it returns false when it should"""
        bad_file = StringIO.StringIO()
        bad_file.write('failing tests please')
        bad_file.seek(0)

        self.assertTrue(
            not DelImporter.can_handle(bad_file),
            "DelImporter cannot handle this file")

        bad_file.close()

    def test_import_process(self):
        """Verify importer inserts the correct records"""
        good_file = self._get_del_file()
        imp = Importer(good_file, username=u"admin")
        imp.process()

        # now let's do some db sanity checks
        self._delicious_data_test()

    def test_dupe_imports(self):
        """If we import twice, we shouldn't end up with duplicate bmarks"""
        good_file = self._get_del_file()
        imp = Importer(good_file, username=u"admin")
        imp.process()

        good_file = self._get_del_file()
        imp = Importer(good_file, username=u"admin")
        imp.process()

        # now let's do some db sanity checks
        self._delicious_data_test()


class ImportDeliciousXMLTest(TestImports):
    """Test the Bookie XML version importer for delicious"""

    def _get_del_file(self):
        """We need to get the locally found delicious.html file for tests"""
        loc = os.path.dirname(__file__)
        del_file = os.path.join(loc, 'newdelicious.xml')
        return open(del_file)

    def tearDown(self):
        """Regular tear down method"""
        empty_db()

    def test_is_delicious_file(self):
        """Verify that this is a delicious file"""
        good_file = self._get_del_file()
        self.assertTrue(
            DelXMLImporter.can_handle(good_file),
            "DelXMLImporter should handle this file")
        good_file.close()

    def test_is_not_delicious_file(self):
        """And that it returns false when it should"""
        bad_file = StringIO.StringIO()
        bad_file.write('failing tests please')
        bad_file.seek(0)

        self.assertTrue(
            not DelXMLImporter.can_handle(bad_file),
            "DelXMLImporter cannot handle this file")

        bad_file.close()

    def test_import_process(self):
        """Verify importer inserts the correct records"""
        good_file = self._get_del_file()
        imp = Importer(good_file, username=u"admin")
        imp.process()

        # now let's do some db sanity checks
        self._delicious_xml_data_test()

    def test_dupe_imports(self):
        """If we import twice, we shouldn't end up with duplicate bmarks"""
        good_file = self._get_del_file()
        imp = Importer(good_file, username=u"admin")
        imp.process()

        good_file = self._get_del_file()
        imp = Importer(good_file, username=u"admin")
        imp.process()

        # Now let's do some db sanity checks.
        self._delicious_xml_data_test()


class ImportGoogleTest(TestImports):
    """Test the Bookie importer for google bookmarks"""

    def _get_google_file(self):
        """We need to get the locally found delicious.html file for tests"""
        loc = os.path.dirname(__file__)
        del_file = os.path.join(loc, 'googlebookmarks.html')

        return open(del_file)

    def tearDown(self):
        """Regular tear down method"""
        empty_db()

    def test_is_google_file(self):
        """Verify that this is a delicious file"""
        good_file = self._get_google_file()

        self.assertTrue(
            GBookmarkImporter.can_handle(good_file),
            "GBookmarkImporter should handle this file")

        good_file.close()

    def test_is_not_google_file(self):
        """And that it returns false when it should"""
        bad_file = StringIO.StringIO()
        bad_file.write('failing tests please')

    def test_import_process(self):
        """Verify importer inserts the correct google bookmarks"""
        good_file = self._get_google_file()
        imp = Importer(good_file, username=u"admin")
        imp.process()

        # now let's do some db sanity checks
        self._google_data_test()

    def test_bookmarklet_file(self):
        """Verify we can import a file with a bookmarklet in it."""
        loc = os.path.dirname(__file__)
        bmarklet_file = os.path.join(loc, 'bookmarklet_error.htm')
        fh = open(bmarklet_file)

        imp = Importer(fh, username=u"admin")
        imp.process()

        res = Bmark.query.all()
        self.assertEqual(len(res), 3)


class ImportChromeTest(TestImports):
    """Test the Bookie importer for Chrome export"""

    def _get_file(self):
        loc = os.path.dirname(__file__)
        del_file = os.path.join(loc, 'chrome.html')

        return open(del_file)

    def tearDown(self):
        """Regular tear down method"""
        empty_db()

    def test_is_google_file(self):
        """Verify that this is a delicious file"""
        good_file = self._get_file()

        self.assertTrue(
            GBookmarkImporter.can_handle(good_file),
            "GBookmarkImporter should handle this file")

        good_file.close()

    def test_is_not_google_file(self):
        """And that it returns false when it should"""
        bad_file = StringIO.StringIO()
        bad_file.write('failing tests please')
        bad_file.seek(0)

        self.assertTrue(
            not GBookmarkImporter.can_handle(bad_file),
            "GBookmarkImporter cannot handle this file")

        bad_file.close()

    def test_import_process(self):
        """Verify importer inserts the correct google bookmarks"""
        good_file = self._get_file()
        imp = Importer(good_file, username=u"admin")
        imp.process()

        # now let's do some db sanity checks
        self._chrome_data_test()


class ImportFirefoxTest(TestImports):
    """Test the Bookie importer for Firefox backup export"""

    def _get_file(self):
        loc = os.path.dirname(__file__)
        del_file = os.path.join(loc, 'firefox_backup.json')

        return open(del_file)

    def tearDown(self):
        """Regular tear down method"""
        empty_db()

    def test_is_firefox_file(self):
        """Verify that this is a firefox json file"""
        good_file = self._get_file()

        self.assertTrue(
            FBookmarkImporter.can_handle(good_file),
            "FBookmarkImporter should handle this file")

        good_file.close()

    def test_is_not_firefox_file(self):
        """And that it returns false when it should"""
        bad_file = StringIO.StringIO()
        bad_file.write('failing tests please')
        bad_file.seek(0)

        self.assertTrue(
            not FBookmarkImporter.can_handle(bad_file),
            "FBookmarkImporter cannot handle this file")

        bad_file.close()

    def test_import_process(self):
        """Verify importer inserts the correct firefox bookmarks"""
        good_file = self._get_file()
        imp = Importer(good_file, username=u"admin")
        imp.process()

        # now let's do some db sanity checks
        self._firefox_data_test()

    def test_nested_folder(self):
        """Verify if bookmarks in nested folders are imported"""
        good_file = self._get_file()
        imp = Importer(good_file, username=u"admin")
        imp.process()

        check_url = 'https://github.com/bookieio/Bookie/issues/71'
        check_url_hashed = generate_hash(check_url)
        found = Bmark.query.filter(Bmark.hash_id == check_url_hashed).one()

        self.assertTrue(
            found.hashed.url == check_url, "The url should match our search")


class ImportViews(TestViewBase):
    """Test the web import"""

    def _upload(self):
        """Make an upload to the importer"""
        loc = os.path.dirname(__file__)
        del_file = open(os.path.join(loc, 'delicious.html'))
        res = self.app.post(
            '/admin/import',
            params={'api_key': self.api_key},
            upload_files=[('import_file',
                           'delicious.html',
                           del_file.read())],
        )
        return res

    def test_import_upload(self):
        """After we upload a file, we should have an importer queue."""
        self._login_admin()

        # verify we get the form
        res = self.app.get('/admin/import')
        self.assertTrue(
            '<form' in res.body,
            'Should have a form in the body for submitting the upload')

        res = self._upload()

        self.assertEqual(
            res.status,
            "302 Found",
            msg='Import status is 302 redirect by home, ' + res.status)

        # now verify that we've got our record
        imp = ImportQueueMgr.get_ready()
        imp = imp[0]
        self.assertTrue(imp, 'We should have a record')
        self.assertTrue(imp.file_path.endswith('admin.delicious.html'))
        self.assertEqual(imp.status, 0, 'start out as default status of 0')

    def test_skip_running(self):
        """Verify that if running, it won't get returned again"""
        self._login_admin()
        res = self._upload()

        self.assertEqual(
            res.status,
            "302 Found",
            msg='Import status is 302 redirect by home, ' + res.status)

        # now verify that we've got our record
        imp = ImportQueueMgr.get_ready()
        imp = imp[0]
        imp.status = 2
        DBSession.flush()

        imp = ImportQueueMgr.get_ready()
        self.assertTrue(not imp, 'We should get no results back')

    def test_one_import(self):
        """You should be able to only get one import running at a time"""
        self._login_admin()

        # Prep the db with 2 other imports ahead of this user's.
        # We have to commit these since the request takes place in a new
        # session/transaction.
        DBSession.add(ImportQueue(username=u'testing',
                                  file_path=u'testing.txt'))
        DBSession.add(ImportQueue(username=u'testing2',
                                  file_path=u'testing2.txt'))
        DBSession.flush()
        transaction.commit()

        res = self._upload()
        res.follow()

        # now let's hit the import page, we shouldn't get a form, but instead a
        # message about our import
        res = self.app.get('/admin/import')

        self.assertTrue('<form' not in res.body, "We shouldn't have a form")
        self.assertTrue(
            'waiting in the queue' in res.body,
            "We want to display a waiting message.")
        self.assertTrue(
            '2 other imports' in res.body,
            "We want to display a count message." + res.body)

    def test_completed_dont_count(self):
        """Once completed, we should get the form again"""
        self._login_admin()

        # add out completed one
        q = ImportQueue(
            username=u'admin',
            file_path=u'testing.txt'
        )
        q.completed = datetime.now()
        q.status = 2
        DBSession.add(q)
        transaction.commit()

        # now let's hit the import page, we shouldn't get a form, but instead a
        # message about our import
        res = self.app.get('/admin/import')

        self.assertTrue('<form' in res.body, "We should have a form")

    def test_empty_upload(self):
        """Verify if error message is shown if no file is tried to upload"""
        self._login_admin()

        res = self.app.post(
            '/admin/import',
            params={'api_key': self.api_key},
            upload_files=[],
        )
        self.assertTrue(
            'Please provide a file to import' in res.body,
            "Error message should be present")

########NEW FILE########
__FILENAME__ = test_readable
"""Test the fulltext implementation"""
import logging
import os
import transaction
import urllib

from pyramid import testing
from unittest import TestCase

from bookie.lib.readable import ReadContent
from bookie.lib.readable import ReadUrl

from bookie.models import DBSession
from bookie.tests import empty_db


LOG = logging.getLogger(__file__)
API_KEY = None


class TestReadable(TestCase):
    """Test that our fulltext classes function"""

    def test_url_content(self):
        """Test that we set the correct status"""

        url = 'http://lococast.net/archives/475'
        read = ReadUrl.parse(url)

        self.assertTrue(
            read.status == 200, "The status is 200" + str(read.status))
        self.assertTrue(not read.is_image(), "The content is not an image")
        self.assertTrue(read.content is not None, "Content should not be none")
        self.assertTrue(
            'Lococast' in read.content,
            "The word Lococast is in the content: " + str(read.content))

    def test_404_url(self):
        """Test that we get the proper errors in a missing url"""
        url = 'http://lococast.net/archives/001'
        read = ReadUrl.parse(url)

        self.assertTrue(
            read.status == 404, "The status is 404: " + str(read.status))
        self.assertTrue(
            not read.is_image(), "The content is not an image")
        self.assertTrue(
            read.content is None, "Content should be none")

    def test_given_content(self):
        """Test that we can parse out given html content ahead of time"""

        file_path = os.path.dirname(__file__)
        html_content = open(os.path.join(file_path, 'readable_sample.html'))

        read = ReadContent.parse(html_content)

        self.assertTrue(
            read.status == 1, "The status is 1: " + str(read.status))
        self.assertTrue(not read.is_image(), "The content is not an image")
        self.assertTrue(read.content is not None, "Content should not be none")
        self.assertTrue(
            'Bookie' in read.content,
            u"The word Bookie is in the content: " + unicode(read.content))

    def test_non_net_url(self):
        """I might be bookmarking something internal bookie can't access"""
        test_url = "http://r2"
        read = ReadUrl.parse(test_url)

        self.assertTrue(
            read.status == 901,
            "The status is 901: " + str(read.status))
        self.assertTrue(not read.is_image(), "The content is not an image")
        self.assertTrue(
            read.content is None,
            "Content should be none: " + str(read.content))

    def test_image_url(self):
        """Verify we don't store, but just tag an image url"""
        img_url = 'http://www.ndftz.com/nickelanddime.png'
        read = ReadUrl.parse(img_url)

        self.assertTrue(
            read.status == 200, "The status is 200: " + str(read.status))
        self.assertTrue(
            read.content is None, "Content should be none: ")

    def test_nonworking_url(self):
        """Testing some urls we know we had issues with initially"""
        urls = {
            'CouchSurfing': ('http://allthatiswrong.wordpress.com/2010/01'
                             '/24/a-criticism-of-couchsurfing-and-review-o'
                             'f-alternatives/#problems'),
            # 'Electronic': ('https://www.fbo.gov/index?s=opportunity&mode='
            #                'form&tab=core&id=dd11f27254c796f80f2aadcbe415'
            #                '8407'),
        }

        for key, url in urls.iteritems():
            read = ReadUrl.parse(url)

            self.assertTrue(
                read.status == 200, "The status is 200: " + str(read.status))
            self.assertTrue(
                read.content is not None, "Content should not be none: ")


class TestReadableFulltext(TestCase):
    """Test that our fulltext index function"""

    def setUp(self):
        """Setup Tests"""
        from pyramid.paster import get_app
        from bookie.tests import BOOKIE_TEST_INI
        app = get_app(BOOKIE_TEST_INI, 'bookie')
        from webtest import TestApp
        self.testapp = TestApp(app)
        testing.setUp()
        global API_KEY
        if API_KEY is None:
            res = DBSession.execute(
                "SELECT api_key FROM users WHERE username = 'admin'").\
                fetchone()
            API_KEY = res['api_key']

    def tearDown(self):
        """Tear down each test"""
        testing.tearDown()
        empty_db()

    def _get_good_request(self):
        """Return the basics for a good add bookmark request"""
        session = DBSession()
        prms = {
            'url': u'http://google.com',
            'description': u'This is my google desc',
            'extended': u'And some extended notes about it in full form',
            'tags': u'python search',
            'api_key': API_KEY,
            'content': 'bmark content is the best kind of content man',
        }

        req_params = urllib.urlencode(prms)
        res = self.testapp.post('/api/v1/admin/bmark',
                                params=req_params)
        session.flush()
        transaction.commit()
        from bookie.bcelery import tasks
        tasks.reindex_fulltext_allbookmarks(sync=True)
        return res

    def test_restlike_search(self):
        """Verify that our search still works in a restful url method"""
        # first let's add a bookmark we can search on
        self._get_good_request()

        search_res = self.testapp.get(
            '/api/v1/admin/bmarks/search/search?search_content=True')

        self.assertTrue(
            search_res.status == '200 OK',
            "Status is 200: " + search_res.status)
        self.assertTrue(
            'python' in search_res.body,
            "We should find the python tag in the results: " + search_res.body)

########NEW FILE########
__FILENAME__ = test_search
"""Test if correct arguments are passed to Whoosh to search
indexed content

"""
from mock import patch
from pyramid import testing
from unittest import TestCase


class TestSearchAttr(TestCase):

    attr = []

    def _return_attr(self, *args, **kwargs):
        """Saves arguments passed to WhooshFulltext
        search function to attr

        """
        self.attr = [args, kwargs]
        return []

    def setUp(self):
        from pyramid.paster import get_app
        from bookie.tests import BOOKIE_TEST_INI
        app = get_app(BOOKIE_TEST_INI, 'bookie')
        from webtest import TestApp
        self.testapp = TestApp(app)
        testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @patch('bookie.models.fulltext.WhooshFulltext')
    def test_search_content(self, mock_search):
        """Test if correct arguments are passed to WhooshFulltext if
        searched through webui"""
        mock_search().search.side_effect = self._return_attr
        self.testapp.get('/results/bookie')

        self.assertTrue(mock_search.called)
        self.assertEqual(self.attr[0][0],
                         'bookie',
                         'search term should be bookie')
        self.assertTrue(self.attr[1]['content'])

    @patch('bookie.models.fulltext.WhooshFulltext')
    def test_search_content_ajax(self, mock_search):
        """Test if correct arguments are passed to WhooshFulltext
        with ajax request"""
        mock_search().search.side_effect = self._return_attr
        self.testapp.get(url='/results/ajax', xhr=True)

        self.assertTrue(mock_search.called)
        self.assertEqual(self.attr[0][0],
                         'ajax',
                         'search term should be ajax')
        self.assertTrue(self.attr[1]['content'])

########NEW FILE########
__FILENAME__ = test_utils
from unittest import TestCase

from bookie.lib.utils import suggest_tags


class TestSuggestTags(TestCase):
    """Verify we can suggest tags for content."""

    def test_avoids_bombing_on_none(self):
        """It should not bomb when passed None"""
        test_value = None
        self.assertEqual(set(), suggest_tags(test_value))

    def test_returns_nouns_for_string(self):
        """It returns only nouns from the strings."""
        test_value = 'google drives autonomous cars'
        self.assertEqual(
            set([u'cars', u'autonomous']),
            suggest_tags(test_value))

    def test_splits_urls_for_nouns(self):
        """It pulls nouns from a url string."""
        test_value = "http://google.com/drives/autonomous/cars"
        self.assertEqual(
            set([u'cars', u'autonomous']),
            suggest_tags(test_value))

    def test_splits_url_parts(self):
        """- and _ should be good split points"""
        test_value = "http://google.com/drives-autonomous_cars"
        self.assertEqual(
            set([u'cars', u'autonomous']),
            suggest_tags(test_value))

########NEW FILE########
__FILENAME__ = test_account
"""Tests for the account views"""

import logging
from bookie.tests import TestViewBase
from bookie.tests import gen_random_word

LOG = logging.getLogger(__name__)


class AccountViewsTest(TestViewBase):

    """Test the account web views for a user when deleting all bookmarks"""

    def test_delete_all_bookmarks_with_correct_confirmation(self):
        """Verify the workflow with correct confirmation."""
        self._login_admin()
        res = self.app.post(
            '/admin/account/delete_all_bookmarks',
            params={
                'username': 'admin',
                'delete': 'Delete',
            })

        self.assertEqual(
            res.status,
            "200 OK",
            msg='recent status is 200, ' + res.status)
        self.assertTrue(
            "The delete request has been queued" +
            " and will be acted upon shortly." in res.body,
            msg="Request should contain the appropriate message.")

    def test_delete_all_bookmarks_with_wong_confirmation(self):
        """Verify the workflow with wrong confirmation."""
        self._login_admin()
        res = self.app.post(
            '/admin/account/delete_all_bookmarks',
            params={
                'username': 'admin',
                'delete': gen_random_word(10),
            })

        self.assertEqual(
            res.status,
            "200 OK",
            msg='recent status is 200, ' + res.status)
        self.assertTrue(
            "Delete request not confirmed. Please make sure" +
            " to enter &#39;Delete&#39; to confirm." in res.body,
            msg="Request should contain the appropriate message.")

    def test_delete_all_bookmarks_without_confirmation(self):
        """Verify the workflow without any confirmation."""
        self._login_admin()
        res = self.app.post(
            '/admin/account/delete_all_bookmarks',
            params={
                'username': 'admin',
                'delete': '',
            })

        self.assertEqual(
            res.status,
            "200 OK",
            msg='recent status is 200, ' + res.status)
        self.assertTrue(
            "Delete request not confirmed. Please make sure" +
            " to enter &#39;Delete&#39; to confirm." in res.body,
            msg="Request should contain the appropriate message.")

########NEW FILE########
__FILENAME__ = test_webviews
"""Test that we're meeting delicious API specifications"""
import feedparser
import logging
import time
import transaction
from datetime import datetime
from bookie.models import DBSession
from bookie.models import Bmark
from bookie.tests import TestViewBase
from bookie.tests.factory import make_bookmark

GOOGLE_HASH = u'aa2239c17609b2'
BMARKUS_HASH = u'c5c21717c99797'

LOG = logging.getLogger(__name__)


class BookieViewsTest(TestViewBase):
    """Test the normal web views user's user"""

    def _add_bmark(self):
        # setup the default bookie bookmark
        bmark_us = Bmark(u'http://bmark.us',
                         username=u"admin",
                         desc=u"Bookie Website",
                         ext=u"Bookie Documentation Home",
                         tags=u"bookmarks")

        bmark_us.stored = datetime.now()
        bmark_us.updated = datetime.now()
        transaction.commit()

    def test_bookmark_recent(self):
        """Verify we can call the /recent url """
        self._add_bmark()
        body_str = "Recent Bookmarks"

        res = self.app.get('/recent')

        self.assertEqual(
            res.status,
            "200 OK",
            msg='recent status is 200, ' + res.status)
        self.assertTrue(
            body_str in res.body,
            msg="Request should contain body_str: " + res.body)

    def test_recent_page(self):
        """We should be able to page through the list"""
        body_str = u"Prev"
        res = self.app.get('/recent?page=1')
        self.assertEqual(
            res.status,
            "200 OK",
            msg='recent page 1 status is 200, ' + res.status)
        self.assertTrue(
            body_str in res.body,
            msg="Page 1 should contain body_str: " + res.body)

    def test_import_auth_failed(self):
        """Veryify that without the right API key we get forbidden"""
        post = {
            'api_key': 'wrong_key'
        }

        res = self.app.post('/admin/import', params=post, status=403)

        self.assertEqual(
            res.status, "403 Forbidden",
            msg='Import status is 403, ' + res.status)

    def test_changes_link_in_footer(self):
        """Changes link should go to the bookie commits github page."""
        changes_link = "https://github.com/bookieio/Bookie/commits/develop"
        res = self.app.get('/')

        self.assertEqual(
            res.status,
            "200 OK",
            msg='recent status is 200, ' + res.status)
        self.assertTrue(
            changes_link in res.body,
            msg="Changes link should appear: " + res.body)


class TestNewBookmark(TestViewBase):
    """Test the new bookmark real views"""

    def test_renders(self):
        """Verify that we can call the /new url"""
        self._login_admin()
        res = self.app.get('/admin/new')
        self.assertTrue(
            'Add Bookmark' in res.body,
            "Should see the add bookmark title")

    def test_manual_entry_error(self):
        """Use can manually submit a bookmark."""
        self._login_admin()
        # no url entered
        res = self.app.post(
            '/admin/new_error',
            params={
                'url': '',
                'description': '',
                'extended': '',
                'tags': ''
            })
        self.assertIn('not valid', res.body)

    def test_existing_url_entry_error(self):
        """ Verify the User has received error message that URL exists"""
        self._login_admin()

        test_url = u"http://bmark.us/test"
        existing_url_message = "URL already Exists"

        # Add The Bookmark Once
        res = self.app.post(
            '/admin/new_error',
            params={
                'url': test_url,
                'description': '',
                'extended': '',
                'tags': ''
            })
        self.assertEqual(
            res.status,
            "302 Found",
            msg='recent status is 302 Found, ' + res.status)

        # Add the Bookmark Again
        res = self.app.post(
            '/admin/new_error',
            params={
                'url': test_url,
                'description': '',
                'extended': '',
                'tags': ''
            })
        self.assertIn(existing_url_message, res.body)


class TestRSSFeeds(TestViewBase):
    """Verify the RSS feeds function correctly."""

    def test_rss_added(self):
        """Viewing /recent should have a rss url in the content."""
        body_str = "application/rss+xml"
        res = self.app.get('/recent')

        self.assertEqual(
            res.status,
            "200 OK",
            msg='recent status is 200, ' + res.status)
        self.assertTrue(
            body_str in res.body,
            msg="Request should contain rss str: " + res.body)

    def test_rss_matches_request(self):
        """The url should match the /recent request with tags."""
        body_str = "rss/ubuntu"
        res = self.app.get('/recent/ubuntu')

        self.assertEqual(
            res.status,
            "200 OK",
            msg='recent status is 200, ' + res.status)
        self.assertTrue(
            body_str in res.body,
            msg="Request should contain rss url: " + res.body)

    def test_rss_is_parseable(self):
        """The rss feed should be a parseable feed."""
        [make_bookmark() for i in range(10)]
        transaction.commit()

        res = self.app.get('/rss')

        self.assertEqual(
            res.status,
            "200 OK",
            msg='recent status is 200, ' + res.status)

        # http://packages.python.org/feedparser/
        # introduction.html#parsing-a-feed-from-a-string
        parsed = feedparser.parse(res.body)
        links = []
        for entry in parsed.entries:
            links.append({
                'title': entry.title,
                'category': entry.category,
                'date': time.strftime('%d %b %Y', entry.updated_parsed),
                'description': entry.description,
                'link': entry.link,
            })

        self.assertTrue(links, 'The feed should have a list of links.')
        self.assertEqual(10, len(links), 'There are 10 links in the feed.')

        sample_item = links[0]
        self.assertTrue(sample_item['title'], 'Items have a title.')
        self.assertTrue(
            sample_item['link'],
            'Items have a link to reach things.')
        self.assertTrue(
            'description' in sample_item,
            'Items have a description string.')


class ReadableTest(TestViewBase):
    def _add_bmark_w_desc(self):
        # setup the default bookie bookmark
        bmark_us = Bmark(u'http://bmark.us',
                         username=u"admin",
                         desc=u"Bookie Website",
                         ext=u"Bookie Documentation Home",
                         tags=u"bookmarks")

        bmark_us.stored = datetime.now()
        bmark_us.updated = datetime.now()
        DBSession.add(bmark_us)
        transaction.commit()

    def _add_bmark_wt_desc(self):
        # Setup the default google bookmark.
        bmark_us = Bmark(u'http://google.com',
                         username=u"admin",
                         desc=u"",
                         ext=u"Google Search Engine",
                         tags=u"bookmarks")

        bmark_us.stored = datetime.now()
        bmark_us.updated = datetime.now()
        DBSession.add(bmark_us)
        transaction.commit()

    def test_readable_w_title(self):
        self._add_bmark_w_desc()
        body_str = "Bookie Website"

        res = self.app.get("/bmark/readable/"+BMARKUS_HASH)

        self.assertEqual(
            res.status,
            "200 OK",
            msg='recent status is 200, ' + res.status)
        self.assertTrue(
            body_str in res.body,
            msg="Request should contain body_str: " + res.body)

    def test_readable_title_wt_desc(self):
        self._add_bmark_wt_desc()
        body_str = "http://google.com"

        res = self.app.get("/bmark/readable/"+GOOGLE_HASH)

        self.assertEqual(
            res.status,
            "200 OK",
            msg='recent status is 200, ' + res.status)
        self.assertTrue(
            body_str in res.body,
            msg="Request should contain body_str: " + res.body)

########NEW FILE########
__FILENAME__ = accounts
import logging

from pyramid.view import view_config

from bookie.lib.access import ReqAuthorize
from bookie.models.auth import UserMgr

LOG = logging.getLogger(__name__)


@view_config(route_name="user_account", renderer="/accounts/index.mako")
def account(request):
    """Index of account page

    You can only load your own account page. If you try to view someone else's
    you'll just end up with your own.

    """
    # if auth fails, it'll raise an HTTPForbidden exception
    with ReqAuthorize(request):
        user = UserMgr.get(username=request.user.username)

        return {
            'user': user,
            'username': user.username,
        }

########NEW FILE########
__FILENAME__ = api
"""Controllers related to viewing lists of bookmarks"""
import logging

from datetime import datetime
from pyramid.settings import asbool
from pyramid.view import view_config
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import contains_eager
from StringIO import StringIO

from bookie.bcelery import tasks
from bookie.lib.access import api_auth
from bookie.lib.applog import AuthLog
from bookie.lib.applog import BmarkLog
from bookie.lib.message import ReactivateMsg
from bookie.lib.message import ActivationMsg
from bookie.lib.readable import ReadContent
from bookie.lib.tagcommands import Commander
from bookie.lib.utils import suggest_tags

from bookie.models import (
    bmarks_tags,
    Bmark,
    BmarkMgr,
    DBSession,
    Hashed,
    NoResultFound,
    Readable,
    TagMgr,
)
from bookie.models.applog import AppLogMgr
from bookie.models.auth import ActivationMgr
from bookie.models.auth import get_random_word
from bookie.models.auth import User
from bookie.models.auth import UserMgr
from bookie.models.stats import StatBookmarkMgr
from bookie.models.queue import ImportQueueMgr

from bookie.models.fulltext import get_fulltext_handler

LOG = logging.getLogger(__name__)
RESULTS_MAX = 10
HARD_MAX = 100


def _check_with_content(params):
    """Verify that we should be checking with content"""
    if 'with_content' in params and params['with_content'] != 'false':
        return True
    else:
        return False


def _api_response(request, data):
    """Perform common operations on the response."""
    # Wrap the data response with CORS headers for cross domain JS clients.
    request.response.headers.extend([
        ('Access-Control-Allow-Origin', '*'),
        ('Access-Control-Allow-Headers', 'X-Requested-With')
    ])

    return data


@view_config(route_name="api_user_stats", renderer="jsonp")
def user_stats(request):
    """Return all the user stats"""
    user_count = UserMgr.count()
    pending_activations = ActivationMgr.count()
    users_with_bookmarks = BmarkMgr.count(distinct_users=True)
    return _api_response(request, {
        'count': user_count,
        'activations': pending_activations,
        'with_bookmarks': users_with_bookmarks
    })


@view_config(route_name="api_bookmark_stats", renderer="jsonp")
def bookmark_stats(request):
    """Return all the bookmark stats"""
    bookmark_count = BmarkMgr.count()
    unique_url_count = BmarkMgr.count(distinct=True)
    return _api_response(request, {
        'count': bookmark_count,
        'unique_count': unique_url_count
    })


@view_config(route_name="api_ping", renderer="jsonp")
@api_auth('api_key', UserMgr.get)
def ping(request):
    """Verify that you've setup your api correctly and verified

    """
    rdict = request.matchdict
    params = request.params
    username = rdict.get('username', None)
    api_key = params.get('api_key', None)
    user = UserMgr.get(username=username)
    # Check if user provided the correct api_key
    if api_key == user.api_key:
        return _api_response(request, {
            'success': True,
            'message': 'Looks good'
        })
    else:
        return _api_response(request, {
            'success': False,
            'message': 'API key is invalid.'
        })


@view_config(route_name="api_ping_missing_user", renderer="jsonp")
def ping_missing_user(request):
    """You ping'd but were missing the username in the url for some reason.

    """
    return _api_response(request, {
        'success': False,
        'message': 'Missing username in your api url.'
    })


@view_config(route_name="api_ping_missing_api", renderer="jsonp")
def ping_missing_api(request):
    """You ping'd but didn't specify the actual api url.

    """
    return _api_response(request, {
        'success': False,
        'message': 'The API url should be /api/v1'
    })


@view_config(route_name="api_bmark_hash", renderer="jsonp")
@api_auth('api_key', UserMgr.get, anon=True)
def bmark_get(request):
    """Return a bookmark requested via hash_id

    We need to return a nested object with parts
        bmark
            - readable
    """
    rdict = request.matchdict
    params = request.params
    hash_id = rdict.get('hash_id', None)
    username = rdict.get('username', None)
    title = params.get('description', None)
    url = params.get('url', None)
    if username:
        username = username.lower()

    # The hash id will always be there or the route won't match.
    bookmark = BmarkMgr.get_by_hash(hash_id, username=username)

    # tag_list is a set - no duplicates
    tag_list = set()

    if title or url:
        suggested_tags = suggest_tags(url)
        suggested_tags.update(suggest_tags(title))
        tag_list.update(suggested_tags)

    if bookmark is None:
        request.response.status_int = 404
        ret = {'error': "Bookmark for hash id {0} not found".format(hash_id)}
        # Pack the response with Suggested Tags.
        resp_tags = {'tag_suggestions': list(tag_list)}
        ret.update(resp_tags)
        return _api_response(request, ret)
    else:
        return_obj = dict(bookmark)
        return_obj['tags'] = [dict(tag[1]) for tag in bookmark.tags.items()]

        if 'with_content' in params and params['with_content'] != 'false':
            if bookmark.readable:
                return_obj['readable'] = dict(bookmark.readable)
        # Pack the response with Suggested Tags.
        ret = {
            'bmark': return_obj,
            'tag_suggestions': list(tag_list)
        }
        return _api_response(request, ret)


def _update_mark(mark, params):
    """Update the bookmark found with settings passed in"""
    mark.description = params.get('description', mark.description)
    mark.extended = params.get('extended', mark.extended)

    new_tag_str = params.get('tags', None)

    # if the only new tags are commands, then don't erase the
    # existing tags
    # we need to process any commands associated as well
    new_tags = TagMgr.from_string(new_tag_str)
    found_cmds = Commander.check_commands(new_tags)

    if new_tag_str and len(new_tags) == len(found_cmds):
        # the all the new tags are command tags, just tack them on
        # for processing, but don't touch existing tags
        for command_tag in new_tags.values():
            mark.tags[command_tag.name] = command_tag
    else:
        if new_tag_str:
            # in this case, rewrite the tags wit the new ones
            mark.update_tags(new_tag_str)

    return mark


@view_config(route_name="api_bmark_add", renderer="jsonp")
@view_config(route_name="api_bmark_update", renderer="jsonp")
@api_auth('api_key', UserMgr.get)
def bmark_add(request):
    """Add a new bookmark to the system"""
    rdict = request.matchdict
    try:
        if 'url' in request.params or 'hash_id' in request.params:
            params = request.params
        elif 'url' in request.json_body or 'hash_id' in request.json_body:
            params = request.json_body
        else:
            raise ValueError('No url provided')
    except ValueError:
        request.response.status_int = 400
        return _api_response(request, {
            'error': 'Bad Request: No url provided'
        })

    user = request.user

    if 'url' not in params and 'hash_id' not in rdict:
        request.response.status_int = 400
        return _api_response(request, {
            'error': 'Bad Request: missing url',
        })

    elif 'hash_id' in rdict:
        try:
            mark = BmarkMgr.get_by_hash(
                rdict['hash_id'],
                username=user.username
            )
            mark = _update_mark(mark, params)

        except NoResultFound:
            request.response.status_code = 404
            return _api_response(request, {
                'error': 'Bookmark with hash id {0} not found.'.format(
                         rdict['hash_id'])
            })

    else:
        # check if we already have this
        try:
            mark = BmarkMgr.get_by_url(params['url'],
                                       username=user.username)
            mark = _update_mark(mark, params)

        except NoResultFound:
            # then let's store this thing
            # if we have a dt param then set the date to be that manual
            # date
            if 'dt' in request.params:
                # date format by delapi specs:
                # CCYY-MM-DDThh:mm:ssZ
                fmt = "%Y-%m-%dT%H:%M:%SZ"
                stored_time = datetime.strptime(request.params['dt'], fmt)
            else:
                stored_time = None

            # check to see if we know where this is coming from
            inserted_by = params.get('inserted_by', u'unknown_api')

            mark = BmarkMgr.store(
                params['url'],
                user.username,
                params.get('description', u''),
                params.get('extended', u''),
                params.get('tags', u''),
                dt=stored_time,
                inserted_by=inserted_by,
            )

        # we need to process any commands associated as well
        commander = Commander(mark)
        mark = commander.process()

        # if we have content, stick it on the object here
        if 'content' in params:
            content = StringIO(params['content'])
            content.seek(0)
            parsed = ReadContent.parse(content,
                                       content_type=u"text/html",
                                       url=mark.hashed.url)

            mark.readable = Readable()
            mark.readable.content = parsed.content
            mark.readable.content_type = parsed.content_type
            mark.readable.status_code = parsed.status
            mark.readable.status_message = parsed.status_message

        # we need to flush here for new tag ids, etc
        DBSession.flush()

        mark_data = dict(mark)
        mark_data['tags'] = [dict(mark.tags[tag]) for tag in mark.tags.keys()]

        return _api_response(request, {
            'bmark': mark_data,
            'location': request.route_url('bmark_readable',
                                          hash_id=mark.hash_id,
                                          username=user.username),
        })


@view_config(route_name="api_bmark_remove", renderer="jsonp")
@api_auth('api_key', UserMgr.get)
def bmark_remove(request):
    """Remove this bookmark from the system"""
    rdict = request.matchdict
    user = request.user

    try:
        bmark = BmarkMgr.get_by_hash(rdict['hash_id'],
                                     username=user.username)
        DBSession.delete(bmark)
        return _api_response(request, {
            'message': "done",
        })

    except NoResultFound:
        request.response.status_code = 404
        return _api_response(request, {
            'error': 'Bookmark with hash id {0} not found.'.format(
                     rdict['hash_id'])
        })


@view_config(route_name="api_bmarks", renderer="jsonp")
@view_config(route_name="api_bmarks_user", renderer="jsonp")
@view_config(route_name="api_bmarks_tags", renderer="jsonp")
@view_config(route_name="api_bmarks_user_tags", renderer="jsonp")
@api_auth('api_key', UserMgr.get, anon=True)
def bmark_recent(request, with_content=False):
    """Get a list of the bmarks for the api call"""
    rdict = request.matchdict
    params = request.params

    # check if we have a page count submitted
    page = int(params.get('page', '0'))
    count = int(params.get('count', RESULTS_MAX))

    # we only want to do the username if the username is in the url
    username = rdict.get('username', None)
    if username:
        username = username.lower()

    # We need to check if we have an ordering crtieria specified.
    order_by = params.get('sort', None)
    if order_by == "popular":
        if username:
            order_by = Bmark.clicks.desc()
        else:
            order_by = Hashed.clicks.desc()

    else:
        order_by = Bmark.stored.desc()

    # thou shalt not have more then the HARD MAX
    # @todo move this to the .ini as a setting
    if count > HARD_MAX:
        count = HARD_MAX

    # do we have any tags to filter upon
    tags = rdict.get('tags', None)

    if isinstance(tags, str):
        tags = [tags]

    # if we don't have tags, we might have them sent by a non-js browser as a
    # string in a query string
    if not tags and 'tag_filter' in params:
        tags = params.get('tag_filter').split()

    # @todo fix this!
    # if we allow showing of content the query hangs and fails on the
    # postgres side. Need to check the query and figure out what's up.
    # see bug #142
    # We don't allow with_content by default because of this bug.
    recent_list = BmarkMgr.find(
        limit=count,
        order_by=order_by,
        page=page,
        tags=tags,
        username=username,
        with_tags=True,
    )

    result_set = []

    for res in recent_list:
        return_obj = dict(res)
        return_obj['tags'] = [dict(tag[1]) for tag in res.tags.items()]

        # we should have the hashed information, we need the url and clicks as
        # total clicks to send back
        return_obj['url'] = res.hashed.url
        return_obj['total_clicks'] = res.hashed.clicks

        if with_content:
            return_obj['readable'] = dict(res.readable) if res.readable else {}

        result_set.append(return_obj)

    return _api_response(request, {
        'bmarks': result_set,
        'max_count': RESULTS_MAX,
        'count': len(recent_list),
        'page': page,
        'tag_filter': tags,
    })


@view_config(route_name="api_count_bmarks_user", renderer="jsonp")
@api_auth('api_key', UserMgr.get, anon=False)
def user_bmark_count(request):
    """Get the user's daily bookmark total for the given time window"""
    params = request.params

    username = request.user.username
    start_date = params.get('start_date', None)
    end_date = params.get('end_date', None)
    bmark_count_list = StatBookmarkMgr.count_user_bmarks(
        username=username,
        start_date=start_date,
        end_date=end_date
    )

    result_set = []
    for res in bmark_count_list[0]:
        return_obj = dict(res)

        result_set.append(return_obj)
    return _api_response(request, {
        'count': result_set,
        'start_date': str(bmark_count_list[1]),
        'end_date': str(bmark_count_list[2])
    })


@view_config(route_name="api_bmarks_export", renderer="jsonp")
@api_auth('api_key', UserMgr.get)
def bmark_export(request):
    """Export via the api call to json dump

    """
    username = request.user.username

    bmark_list = BmarkMgr.user_dump(username)
    # log that the user exported this
    BmarkLog.export(username, username)

    def build_bmark(bmark):
        d = dict(bmark)
        d['hashed'] = dict(bmark.hashed)
        return _api_response(request, d)

    return _api_response(request, {
        'bmarks': [build_bmark(bmark) for bmark in bmark_list],
        'count': len(bmark_list),
        'date': str(datetime.utcnow())
    })


@view_config(route_name="api_extension_sync", renderer="jsonp")
@api_auth('api_key', UserMgr.get)
def extension_sync(request):
    """Return a list of the bookmarks we know of in the system

    For right now, send down a list of hash_ids

    """
    username = request.user.username

    hash_list = BmarkMgr.hash_list(username=username)
    return _api_response(request, {
        'hash_list': [hash[0] for hash in hash_list]
    })


@view_config(route_name="api_bmark_search", renderer="jsonp")
@view_config(route_name="api_bmark_search_user", renderer="jsonp")
@api_auth('api_key', UserMgr.get, anon=True)
def search_results(request):
    """Search for the query terms in the matchdict/GET params

    The ones in the matchdict win in the case that they both exist
    but we'll fall back to query string search=XXX

    with_content
        is always GET and specifies if we're searching the fulltext of pages

    """
    mdict = request.matchdict
    rdict = request.GET

    if 'terms' in mdict:
        phrase = " ".join(mdict['terms'])
    else:
        phrase = rdict.get('search', '')

    if rdict.get('search_mine') or 'username' in mdict:
        with_user = True
    else:
        with_user = False

    username = None
    if with_user:
        if 'username' in mdict:
            username = mdict.get('username')
        elif request.user and request.user.username:
            username = request.user.username

    # with content is always in the get string
    search_content = asbool(rdict.get('with_content', False))

    conn_str = request.registry.settings.get('sqlalchemy.url', False)
    searcher = get_fulltext_handler(conn_str)

    # check if we have a page count submitted
    page = rdict.get('page', 0)
    count = rdict.get('count', 10)

    try:
        res_list = searcher.search(
            phrase,
            content=search_content,
            username=username if with_user else None,
            ct=count,
            page=page
        )
    except ValueError:
        request.response.status_int = 404
        ret = {'error': "Bad Request: Page number out of bound"}
        return _api_response(request, ret)

    constructed_results = []
    for res in res_list:
        return_obj = dict(res)
        return_obj['tags'] = [dict(tag[1]) for tag in res.tags.items()]

        # the hashed object is there as well, we need to pull the url and
        # clicks from it as total_clicks
        return_obj['url'] = res.hashed.url
        return_obj['total_clicks'] = res.hashed.clicks

        constructed_results.append(return_obj)

    return _api_response(request, {
        'search_results': constructed_results,
        'result_count': len(constructed_results),
        'phrase': phrase,
        'page': page,
        'with_content': search_content,
        'username': username,
    })


@view_config(route_name="api_tag_complete", renderer="jsonp")
@view_config(route_name="api_tag_complete_user", renderer="jsonp")
@api_auth('api_key', UserMgr.get, anon=True)
def tag_complete(request):
    """Complete a tag based on the given text

    :@param tag: GET string, tag=sqlalchemy
    :@param current: GET string of tags we already have python+database

    """
    params = request.GET

    if request.user:
        username = request.user.username
    else:
        username = None

    if 'current' in params and params['current'] != "":
        current_tags = params['current'].split()
    else:
        current_tags = None

    if 'tag' in params and params['tag']:
        tag = params['tag']

        tags = TagMgr.complete(tag,
                               current=current_tags,
                               username=username)
    else:
        tags = []

    # reset this for the payload join operation
    if current_tags is None:
        current_tags = []

    return _api_response(request, {
        'current': ",".join(current_tags),
        'tags': [t.name for t in tags]
    })


# USER ACCOUNT INFORMATION CALLS
@view_config(route_name="api_user_account", renderer="jsonp")
@api_auth('api_key', UserMgr.get)
def account_info(request):
    """Return the details of the user account specifed

    expecting username in matchdict
    We only return a subset of data. We're not sharing keys such as api_key,
    password hash, etc.

    """
    user = request.user

    return _api_response(request, user.safe_data())


@view_config(route_name="api_user_account_update", renderer="jsonp")
@api_auth('api_key', UserMgr.get)
def account_update(request):
    """Update the account information for a user

    :params name:
    :params email:

    Callable by either a logged in user or the api key for mobile apps/etc

    """
    params = request.params
    json_body = request.json_body
    user_acct = request.user

    if 'name' in params and params['name'] is not None:
        name = params.get('name')
        user_acct.name = name

    if 'name' in json_body and json_body['name'] is not None:
        name = json_body.get('name')
        user_acct.name = name

    if 'email' in params and params['email'] is not None:
        email = params.get('email')
        user_acct.email = email.lower()

    if 'email' in json_body and json_body['email'] is not None:
        email = json_body.get('email')
        user_acct.email = email.lower()

    return _api_response(request, user_acct.safe_data())


@view_config(route_name="api_reset_api_key", renderer="jsonp")
@api_auth('api_key', UserMgr.get)
def reset_api_key(request):
    """Generate and Return the currently logged in user's new api key

       Callable by either a logged in user or the api key for mobile apps/etc

    """
    user = request.user
    # Generate new api key and assign it to user's api key
    user.api_key = User.gen_api_key()
    return _api_response(request, {
        'api_key': user.api_key,
        'message': 'Api Key was successfully changed',
    })


@view_config(route_name="api_user_api_key", renderer="jsonp")
@api_auth('api_key', UserMgr.get)
def api_key(request):
    """Return the currently logged in user's api key

    This api call is available both on the website via a currently logged in
    user and via a valid api key passed into the request. In this way we should
    be able to add this to the mobile view with an ajax call as well as we do
    into the account information on the main site.

    """
    user_acct = request.user
    return _api_response(request, {
        'api_key': user_acct.api_key,
        'username': user_acct.username
    })


@view_config(route_name="api_user_reset_password", renderer="jsonp")
@api_auth('api_key', UserMgr.get)
def reset_password(request):
    """Change a user's password from the current string

    :params current_password:
    :params new_password:

    Callable by either a logged in user or the api key for mobile apps/etc

    """
    params = request.params

    # now also load the password info
    current = params.get('current_password', None)
    new = params.get('new_password', None)

    # if we don't have any password info, try a json_body in case it's a json
    # POST
    if current is None and new is None:
        params = request.json_body
        current = params.get('current_password', None)
        new = params.get('new_password', None)

    user_acct = request.user

    if not UserMgr.acceptable_password(new):
        request.response.status_int = 406
        return _api_response(request, {
            'username': user_acct.username,
            'error': "Come on, let's try a real password this time"
        })

    # before we change the password, let's verify it
    if user_acct.validate_password(current):
        # we're good to change it
        user_acct.password = new
        return _api_response(request, {
            'username': user_acct.username,
            'message': "Password changed",
        })
    else:
        request.response.status_int = 403
        return _api_response(request, {
            'username': user_acct.username,
            'error': "There was a typo somewhere. Please check your request"
        })


@view_config(route_name="api_user_suspend", renderer="jsonp")
def suspend_acct(request):
    """Reset a user account to enable them to change their password"""
    params = request.params
    user = request.user

    # we need to get the user from the email
    email = params.get('email', None)

    if email is None and hasattr(request, 'json_body'):
        # try the json body
        email = request.json_body.get('email', None)

    if user is None and email is None:
        request.response.status_int = 406
        return _api_response(request, {
            'error': "Please submit an email address",
        })

    if user is None and email is not None:
        user = UserMgr.get(email=email)

    if user is None:
        request.response.status_int = 404
        return _api_response(request, {
            'error': "Please submit a valid address",
            'email': email
        })

    # check if we've already gotten an activation for this user
    if user.activation is not None:
        request.response.status_int = 406
        return _api_response(request, {
            'error': """You've already marked your account for reactivation.
Please check your email for the reactivation link. Make sure to
check your spam folder.""",
            'username': user.username,
        })

    # mark them for reactivation
    user.reactivate(u"FORGOTTEN")

    # log it
    AuthLog.reactivate(user.username)

    # and then send an email notification
    # @todo the email side of things
    settings = request.registry.settings
    msg = ReactivateMsg(user.email,
                        "Activate your Bookie account",
                        settings)

    msg.send({
        'url': request.route_url(
            'reset',
            username=user.username,
            reset_key=user.activation.code),
        'username': user.username
    })

    return _api_response(request, {
        'message': """Your account has been marked for reactivation. Please
                    check your email for instructions to reset your
                    password""",
    })


@view_config(route_name="api_user_suspend_remove", renderer="jsonp")
def account_activate(request):
    """Reset a user after being suspended

    :param username: required to know what user we're resetting
    :param activation: code needed to activate
    :param password: new password to use for the user

    """
    params = request.params

    username = params.get('username', None)
    activation = params.get('code', None)
    password = params.get('password', None)
    new_username = params.get('new_username', None)

    if username is None and activation is None and password is None:
        # then try to get the same fields out of a json body
        json_body = request.json_body
        username = json_body.get('username', None)
        activation = json_body.get('code', None)
        password = json_body.get('password', None)
        new_username = json_body.get('new_username', None)

    if not UserMgr.acceptable_password(password):
        request.response.status_int = 406
        return _api_response(request, {
            'error': "Come on, pick a real password please",
        })

    username = username.lower()
    new_username = new_username.lower() if new_username else None
    res = ActivationMgr.activate_user(
        username,
        activation,
        password)

    if res:
        # success so respond nicely
        AuthLog.reactivate(username, success=True, code=activation)

        # if there's a new username and it's not the same as our current
        # username, update it
        if new_username and new_username != username:
            try:
                user = UserMgr.get(username=username)
                user.username = new_username
            except IntegrityError, exc:
                request.response.status_int = 500
                return _api_response(request, {
                    'error': 'There was an issue setting your new username',
                    'exc': str(exc)
                })

        return _api_response(request, {
            'message': "Account activated, please log in.",
            'username': username,
        })
    else:
        AuthLog.reactivate(username, success=False, code=activation)
        request.response.status_int = 500
        return _api_response(request, {
            'error': "There was an issue attempting to activate this account.",
        })


@view_config(route_name="api_user_invite", renderer="jsonp")
@api_auth('api_key', UserMgr.get)
def invite_user(request):
    """Invite a new user into the system.

    :param username: user that is requested we invite someone
    :param email: email address of the new user

    """
    params = request.params

    email = params.get('email', None)
    user = request.user

    if not email:
        # try to get it from the json body
        email = request.json_body.get('email', None)

    if not email:
        # if still no email, I give up!
        request.response.status_int = 406
        return _api_response(request, {
            'username': user.username,
            'error': "Please submit an email address"
        })

    email = email.lower()
    # first see if the user is already in the system
    exists = UserMgr.get(email=email.lower())
    if exists:
        request.response.status_int = 406
        return _api_response(request, {
            'username': exists.username,
            'error': "This user is already a Bookie user!"
        })

    new_user = user.invite(email.lower())
    if new_user:
        LOG.debug(new_user.username)
        # then this user is able to invite someone
        # log it
        AuthLog.reactivate(new_user.username)

        # and then send an email notification
        # @todo the email side of things
        settings = request.registry.settings
        msg = ActivationMsg(new_user.email,
                            "Enable your Bookie account",
                            settings)

        msg.send(
            request.route_url(
                'reset',
                username=new_user.username,
                reset_key=new_user.activation.code))
        return _api_response(request, {
            'message': 'You have invited: ' + new_user.email
        })
    else:
        # you have no invites
        request.response.status_int = 406
        return _api_response(request, {
            'username': user.username,
            'error': "You have no invites left at this time."
        })


@view_config(route_name="api_admin_readable_todo", renderer="jsonp")
@api_auth('api_key', UserMgr.get, admin_only=True)
def to_readable(request):
    """Get a list of urls, hash_ids we need to readable parse"""
    url_list = Bmark.query.outerjoin(Readable, Readable.bid == Bmark.bid).\
        join(Bmark.hashed).\
        options(contains_eager(Bmark.hashed)).\
        filter(Readable.imported.is_(None)).all()

    def data(urls):
        """Yield out the results with the url in the data streamed."""
        for url in urls:
            d = dict(url)
            d['url'] = url.hashed.url
            yield d

    return _api_response(request, {
        'urls': [u for u in data(url_list)]
    })


@view_config(route_name="api_admin_readable_reindex", renderer="jsonp")
@api_auth('api_key', UserMgr.get, admin_only=True)
def readable_reindex(request):
    """Force the fulltext index to rebuild

    This loops through ALL bookmarks and might take a while to complete.

    """
    tasks.reindex_fulltext_allbookmarks.delay()
    return _api_response(request, {
        'success': True
    })


@view_config(route_name="api_admin_accounts_inactive", renderer="jsonp")
@api_auth('api_key', UserMgr.get, admin_only=True)
def accounts_inactive(request):
    """Return a list of the accounts that aren't activated."""
    user_list = UserMgr.get_list(active=False)
    ret = {
        'count': len(user_list),
        'users': [dict(h) for h in user_list],
    }
    return _api_response(request, ret)


@view_config(route_name="api_admin_accounts_invites", renderer="jsonp")
@api_auth('api_key', UserMgr.get, admin_only=True)
def accounts_invites(request):
    """Return a list of the accounts that aren't activated."""
    user_list = UserMgr.get_list()
    ret = {
        'users': [(u.username, u.invite_ct) for u in user_list],
    }
    return _api_response(request, ret)


@view_config(route_name="api_admin_accounts_invites_add", renderer="jsonp")
@api_auth('api_key', UserMgr.get, admin_only=True)
def accounts_invites_add(request):
    """Set the number of invites a user has available.

    :matchdict username: The user to give these invites to.
    :matchdict count: The number of invites to give them.
    """
    rdict = request.matchdict
    username = rdict.get('username', None)
    if username:
        username = username.lower()
    count = rdict.get('count', None)

    if username is not None and count is not None:
        user = UserMgr.get(username=username)

        if user:
            user.invite_ct = count
            return _api_response(request, dict(user))
        else:
            request.response.status_int = 404
            ret = {'error': "Invalid user account."}
            return _api_response(request, ret)
    else:
        request.response.status_int = 400
        ret = {'error': "Bad request, missing parameters"}
        return _api_response(request, ret)


@view_config(route_name="api_admin_imports_list", renderer="jsonp")
@api_auth('api_key', UserMgr.get, admin_only=True)
def import_list(request):
    """Provide some import related data."""
    import_list = ImportQueueMgr.get_list()
    ret = {
        'count': len(import_list),
        'imports': [dict(h) for h in import_list],
    }
    return _api_response(request, ret)


@view_config(route_name="api_admin_imports_reset", renderer="jsonp")
@api_auth('api_key', UserMgr.get, admin_only=True)
def import_reset(request):
    """Reset an import to try again"""
    rdict = request.matchdict
    import_id = rdict.get('id', None)

    if not id:
        request.response.status_int = 400
        ret = {'error': "Bad request, missing parameters"}
        return _api_response(request, ret)

    imp = ImportQueueMgr.get(int(import_id))
    imp.status = 0
    tasks.importer_process.delay(imp.id)

    ret = {
        'import': dict(imp)
    }
    return _api_response(request, ret)


@view_config(route_name="api_admin_users_list", renderer="jsonp")
@api_auth('api_key', UserMgr.get, admin_only=True)
def user_list(request):
    """Provide list of users in the system.

    Supported Query params: order, limit
    """
    params = request.params
    order = params.get('order', None)
    limit = params.get('limit', None)
    user_list = UserMgr.get_list(order=order, limit=limit)
    ret = {
        'count': len(user_list),
        'users': [dict(h) for h in user_list],
    }
    return _api_response(request, ret)


@view_config(route_name="api_admin_new_user", renderer="jsonp")
@api_auth('api_key', UserMgr.get, admin_only=True)
def new_user(request):
    """Add a new user to the system manually."""
    rdict = request.params

    u = User()

    u.username = unicode(rdict.get('username'))
    if u.username:
        u.username = u.username.lower()
    u.email = unicode(rdict.get('email')).lower()
    passwd = get_random_word(8)
    u.password = passwd
    u.activated = True
    u.is_admin = False
    u.api_key = User.gen_api_key()

    try:
        DBSession.add(u)
        DBSession.flush()
        # We need to return the password since the admin added the user
        # manually.  This is only time we should have/give the original
        # password.
        ret = dict(u)
        ret['random_pass'] = passwd
        return _api_response(request, ret)

    except IntegrityError, exc:
        # We might try to add a user that already exists.
        LOG.error(exc)
        request.response.status_int = 400
        return _api_response(request, {
            'error': 'Bad Request: User exists.',
        })


@view_config(route_name="api_admin_del_user", renderer="jsonp")
@api_auth('api_key', UserMgr.get, admin_only=True)
def del_user(request):
    """Remove a bad user from the system via the api.

    For admin use only.

    Removes all of a user's bookmarks before removing the user.

    """
    mdict = request.matchdict

    # Submit a username.
    del_username = mdict.get('username', None)

    if del_username is None:
        LOG.error('No username to remove.')
        request.response.status_int = 400
        return _api_response(request, {
            'error': 'Bad Request: No username to remove.',
        })

    u = UserMgr.get(username=del_username)

    if not u:
        LOG.error('Username not found.')
        request.response.status_int = 404
        return _api_response(request, {
            'error': 'User not found.',
        })

    try:
        # First delete all the tag references for this user's bookmarks.
        res = DBSession.query(Bmark.bid).filter(Bmark.username == u.username)
        bids = [b[0] for b in res]

        qry = bmarks_tags.delete(bmarks_tags.c.bmark_id.in_(bids))
        qry.execute()

        # Delete all of the bmarks for this year.
        Bmark.query.filter(Bmark.username == u.username).delete()
        DBSession.delete(u)
        return _api_response(request, {
            'success': True,
            'message': 'Removed user: ' + del_username
        })
    except Exception, exc:
        # There might be cascade issues or something that causes us to fail in
        # removing.
        LOG.error(exc)
        request.response.status_int = 500
        return _api_response(request, {
            'error': 'Bad Request: ' + str(exc)
        })


@view_config(route_name="api_admin_bmark_remove", renderer="jsonp")
@api_auth('api_key', UserMgr.get, admin_only=True)
def admin_bmark_remove(request):
    """Remove this bookmark from the system"""
    rdict = request.matchdict
    username = rdict.get('username')
    if username:
        username = username.lower()
    hash_id = rdict.get('hash_id')

    try:
        bmark = BmarkMgr.get_by_hash(hash_id,
                                     username=username)
        print bmark
        if bmark:
            DBSession.delete(bmark)
            return _api_response(request, {
                'message': "done",
            })
        else:
            return _api_response(request, {
                'error': 'Bookmark not found.',
            })

    except NoResultFound:
        request.response.status_code = 404
        return _api_response(request, {
            'error': 'Bookmark with hash id {0} not found.'.format(
                rdict['hash_id'])
        })


@view_config(route_name="api_admin_applog", renderer="jsonp")
@api_auth('api_key', UserMgr.get, admin_only=True)
def admin_applog(request):
    """Return applog data for admin use."""
    rdict = request.GET

    # Support optional filter parameters
    days = int(rdict.get('days', 1))
    status = rdict.get('status', None)
    message = rdict.get('message', None)

    log_list = AppLogMgr.find(
        days=days,
        message_filter=message,
        status=status,
    )

    ret = {
        'count': len(log_list),
        'logs': [dict(l) for l in log_list],
    }
    return _api_response(request, ret)


@view_config(route_name="api_admin_non_activated", renderer="jsonp")
@api_auth('api_key', UserMgr.get, admin_only=True)
def admin_non_activated(request):
    """Return non activated account details"""
    ret = []
    res = UserMgr.non_activated_account()
    if res:
        ret = [u.username for u in res]

    return _api_response(request, {
        'count': len(ret),
        'status': True,
        'data': ret,
    })


@view_config(route_name="api_admin_delete_non_activated", renderer="jsonp")
@api_auth('api_key', UserMgr.get, admin_only=True)
def admin_delete_non_activated(request):
    """Delete non activated accounts"""
    UserMgr.non_activated_account(delete=True)
    return _api_response(request, {
        'status': True,
        'message': 'Removed non activated accounts'
    })

########NEW FILE########
__FILENAME__ = auth
import logging

from datetime import datetime
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotFound
from pyramid.renderers import render_to_response
from pyramid.security import remember
from pyramid.security import forget
from pyramid.url import route_url
from pyramid.view import view_config

from bookie.bcelery import tasks
from bookie.lib.applog import AuthLog
from bookie.models import IntegrityError
from bookie.models.auth import UserMgr
from bookie.models.auth import ActivationMgr

LOG = logging.getLogger(__name__)


@view_config(route_name="login", renderer="/auth/login.mako")
def login(request):
    """Login the user to the system

    If not POSTed then show the form
    If error, display the form with the error message
    If successful, forward the user to their /recent

    Note: the came_from stuff we're not using atm. We'll clean out if we keep
    things this way

    """
    login_url = route_url('login', request)
    referrer = request.url
    if referrer == login_url:
        referrer = u'/'  # never use the login form itself as came_from

    came_from = request.params.get('came_from', referrer)

    message = u''
    login = u''
    password = u''

    if 'form.submitted' in request.params:
        login = request.params['login'].lower()
        password = request.params['password']

        LOG.debug(login)
        auth = UserMgr.get(username=login)
        LOG.debug(auth)
        LOG.debug(UserMgr.get_list())

        if auth and auth.validate_password(password) and auth.activated:
            # We use the Primary Key as our identifier once someone has
            # authenticated rather than the username.  You can change what is
            # returned as the userid by altering what is passed to remember.
            headers = remember(request, auth.id, max_age=60 * 60 * 24 * 30)
            auth.last_login = datetime.utcnow()

            # log the successful login
            AuthLog.login(login, True)

            # we're always going to return a user to their own /recent after a
            # login
            return HTTPFound(
                location=request.route_url(
                    'user_bmark_recent',
                    username=auth.username),
                headers=headers)

        # log the right level of problem
        if auth and not auth.validate_password(password):
            message = "Your login attempt has failed."
            AuthLog.login(login, False, password=password)

        elif auth and not auth.activated:
            message = "User account deactivated. Please check your email."
            AuthLog.login(login, False, password=password)
            AuthLog.disabled(login)

        elif auth is None:
            message = "Failed login"
            AuthLog.login(login, False, password=password)

    return {
        'message': message,
        'came_from': came_from,
        'login': login,
        'password': password,
    }


@view_config(route_name="logout", renderer="/auth/login.mako")
def logout(request):
    headers = forget(request)
    return HTTPFound(location=route_url('home', request),
                     headers=headers)


@view_config(route_name="signup", renderer="/auth/signup.mako")
def signup(request):
    """Signup merely shows the signup for to users.

    We always take their signup even if we don't send out the email/invite at
    this time so that we can stage invites across a specific number in waves.

    """
    return {}


@view_config(route_name="signup_process", renderer="/auth/signup.mako")
def signup_process(request):
    """Process the signup request

    If there are any errors drop to the same template with the error
    information.

    """
    params = request.params
    email = params.get('email', None)

    if not email:
        # if still no email, I give up!
        return {
            'errors': {
                'email': 'Please supply an email address to sign up.'
            }
        }
    else:
        email = email.lower()

    # first see if the user is already in the system
    exists = UserMgr.get(email=email)
    if exists:
        return {
            'errors': {
                'email': 'The user has already signed up.'
            }
        }

    new_user = UserMgr.signup_user(email, 'signup')
    if new_user:
        # then this user is able to invite someone
        # log it
        AuthLog.reactivate(new_user.username)

        # and then send an email notification
        # @todo the email side of things
        settings = request.registry.settings

        # Add a queue job to send the user a notification email.
        tasks.email_signup_user.delay(
            new_user.email,
            "Enable your Bookie account",
            settings,
            request.route_url(
                'reset',
                username=new_user.username,
                reset_key=new_user.activation.code
            )
        )

        # And let the user know they're signed up.
        return {
            'message': 'Thank you for signing up from: ' + new_user.email
        }
    else:
        return {
            'errors': {
                'email': 'There was an unknown error signing up.'
            }
        }


@view_config(route_name="reset", renderer="/auth/reset.mako")
def reset(request):
    """Once deactivated, allow for changing the password via activation key"""
    rdict = request.matchdict
    params = request.params

    # This is an initial request to show the activation form.
    username = rdict.get('username', None)
    activation_key = rdict.get('reset_key', None)
    user = ActivationMgr.get_user(username, activation_key)
    new_username = None

    if user is None:
        # just 404 if we don't have an activation code for this user
        raise HTTPNotFound()

    if 'code' in params:
        # This is a posted form with the activation, attempt to unlock the
        # user's account.
        username = params.get('username', None)
        activation = params.get('code', None)
        password = params.get('new_password', None)
        new_username = params.get('new_username', None)
        error = None

        if new_username:
            new_username = new_username.lower()

        # Check whether username exists or not.  During signup request , a
        # record of current user is created with username as his email id
        # which is already checked for uniqueness. So when new_username is
        # equal to username ie the email id then no need to check for
        # uniqueness , but if new_username is something else it has to be
        # verified

        if username != new_username and \
                UserMgr.get(username=new_username) is not None:
            # Set an error message to the template.
            error = "Username already exists."
        elif not UserMgr.acceptable_password(password):
            # Set an error message to the template.
            error = "Come on, pick a real password please."
        else:
            res = ActivationMgr.activate_user(username, activation, password)
            if res:
                # success so respond nicely
                AuthLog.reactivate(username, success=True, code=activation)

                # if there's a new username and it's not the same as our
                # current username, update it
                if new_username and new_username != username:
                    try:
                        user = UserMgr.get(username=username)
                        user.username = new_username
                    except IntegrityError:
                        error = 'There was an issue setting your new username'
            else:
                AuthLog.reactivate(username, success=False, code=activation)
                error = ('There was an issue attempting to activate'
                         'this account.')

        if error:
            return {
                'message': error,
                'user': user
            }
        else:
            # Log the user in and move along.
            headers = remember(request, user.id, max_age=60 * 60 * 24 * 30)
            user.last_login = datetime.utcnow()

            # log the successful login
            AuthLog.login(user.username, True)

            # we're always going to return a user to their own /recent after a
            # login
            return HTTPFound(
                location=request.route_url(
                    'user_bmark_recent',
                    username=user.username),
                headers=headers)

    else:
        LOG.error("CHECKING")
        LOG.error(username)

        if user is None:
            # just 404 if we don't have an activation code for this user
            raise HTTPNotFound()

        LOG.error(user.username)
        LOG.error(user.email)
        return {
            'user': user,
        }


def forbidden_view(request):
    login_url = route_url('login', request)
    referrer = request.url
    if referrer == login_url:
        referrer = '/'  # never use the login form itself as came_from
    came_from = request.params.get('came_from', referrer)
    return render_to_response(
        '/auth/login.mako',
        dict(
            message='',
            url=request.application_url + '/login',
            came_from=came_from,
            login='',
            password='',
        ),
        request=request)

########NEW FILE########
__FILENAME__ = bmarks
"""Controllers related to viewing lists of bookmarks"""
import logging

from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotFound
from pyramid.view import view_config

from bookie.bcelery import tasks
from bookie.lib.access import ReqAuthorize
from bookie.lib.utils import suggest_tags
from bookie.lib.urlhash import generate_hash
from bookie.models import (
    Bmark,
    BmarkMgr,
    DBSession,
    InvalidBookmark,
    NoResultFound,
    TagMgr,
)
from bookie.views import api

LOG = logging.getLogger(__name__)
RESULTS_MAX = 50


@view_config(
    route_name="bmark_recent",
    renderer="/bmark/recent.mako")
@view_config(
    route_name="bmark_recent_tags",
    renderer="/bmark/recent.mako")
@view_config(
    route_name="user_bmark_recent",
    renderer="/bmark/recent.mako")
@view_config(
    route_name="user_bmark_recent_tags",
    renderer="/bmark/recent.mako")
def recent(request):
    """Testing a JS driven ui with backbone/etc"""
    rdict = request.matchdict
    params = request.params

    # Make sure we generate a url to feed our rss link.
    current_route = request.current_route_url()

    # check for auth related stuff
    # are we looking for a specific user
    username = rdict.get('username', None)
    if username:
        username = username.lower()

    # do we have any tags to filter upon
    tags = rdict.get('tags', None)

    if isinstance(tags, str):
        tags = [tags]

    ret = {
        'username': username,
        'tags': tags,
        'rss_url': current_route.replace('recent', 'rss')
    }

    # if we've got url parameters for the page/count then use those to help
    # feed the init of the ajax script
    ret['count'] = params.get('count') if 'count' in params else RESULTS_MAX
    ret['page'] = params.get('page') if 'page' in params else 0

    # Do we have any sorting criteria?
    ret['sort'] = params.get('sort') if 'sort' in params else None

    return ret


@view_config(
    route_name="bmark_recent_rss",
    renderer="/bmark/rss.mako")
@view_config(
    route_name="bmark_recent_rss_tags",
    renderer="/bmark/rss.mako")
@view_config(
    route_name="user_bmark_rss",
    renderer="/bmark/rss.mako")
@view_config(
    route_name="user_bmark_rss_tags",
    renderer="/bmark/rss.mako")
def recent_rss(request):
    rdict = request.matchdict
    request.response.content_type = 'application/atom+xml; charset=UTF-8'

    tags = rdict.get('tags', None)
    username = rdict.get('username', None)
    if username:
        username = username.lower()

    ret = api.bmark_recent(request, with_content=True)
    ret['username'] = username
    ret['tags'] = tags
    return ret


@view_config(
    route_name="user_bmark_edit",
    renderer="/bmark/edit.mako")
@view_config(
    route_name="user_bmark_new",
    renderer="/bmark/edit.mako")
def edit(request):
    """Manual add a bookmark to the user account

    Can pass in params (say from a magic bookmarklet later)
    url
    description
    extended
    tags

    """
    rdict = request.matchdict
    params = request.params
    url = params.get('url', u"")
    title = params.get('description', None)
    new = False
    MAX_TAGS = 10
    tag_suggest = []
    base_tags = set()

    with ReqAuthorize(request, username=rdict['username'].lower()):

        if 'hash_id' in rdict:
            hash_id = rdict['hash_id']
        elif 'hash_id' in params:
            hash_id = params['hash_id']
        else:
            hash_id = None

        if hash_id:
            bmark = BmarkMgr.get_by_hash(hash_id, request.user.username)
            if bmark is None:
                return HTTPNotFound()
            else:
                title = bmark.description
                url = bmark.hashed.url
        else:
            # Hash the url and make sure that it doesn't exist
            if url != u"":
                new_url_hash = generate_hash(url)

                test_exists = BmarkMgr.get_by_hash(
                    new_url_hash,
                    request.user.username)

                if test_exists:
                    location = request.route_url(
                        'user_bmark_edit',
                        hash_id=new_url_hash,
                        username=request.user.username)
                    return HTTPFound(location)

            # No url info given so shown the form to the user.
            new = True
            # Setup a dummy bookmark so the template can operate
            # correctly.
            bmark = Bmark(url, request.user.username, desc=title)

        # Title and url will be in params for new bookmark and
        # fetched from database if it is an edit request
        if title or url:
            suggested_tags = suggest_tags(url)
            suggested_tags.update(suggest_tags(title))
            base_tags.update(suggested_tags)

        # If user is editing a bookmark, suggested tags will include tags
        # based on readable content also
        if not new:
            tag_suggest = TagMgr.suggestions(
                bmark=bmark,
                url=bmark.hashed.url,
                username=request.user.username
            )
        # tags based on url and title will always be there
        # order of tags is important so convert set to list
        tag_suggest.extend(list(base_tags))
        tag_suggest = (tag_suggest[0:MAX_TAGS],
                       tag_suggest)[len(tag_suggest) < MAX_TAGS]
        return {
            'new': new,
            'bmark': bmark,
            'user': request.user,
            'tag_suggest': list(set(tag_suggest)),
        }


@view_config(route_name="user_bmark_edit_error", renderer="/bmark/edit.mako")
@view_config(route_name="user_bmark_new_error", renderer="/bmark/edit.mako")
def edit_error(request):
    rdict = request.matchdict
    params = request.params
    post = request.POST

    with ReqAuthorize(request, username=rdict['username'].lower()):
        if 'new' in request.url:
            try:
                try:
                    bmark = BmarkMgr.get_by_url(
                        post['url'],
                        username=request.user.username)
                except NoResultFound:
                    bmark = None
                if bmark:
                    return {
                        'new': False,
                        'bmark': bmark,
                        'message': "URL already Exists",
                        'user': request.user,
                    }
                else:
                    bmark = BmarkMgr.store(
                        post['url'],
                        request.user.username,
                        post['description'],
                        post['extended'],
                        post['tags'])

                    # Assign a task to fetch this pages content and parse it
                    # out for storage and indexing.
                    DBSession.flush()
                    tasks.fetch_bmark_content.delay(bmark.bid)

            except InvalidBookmark, exc:
                # There was an issue using the supplied data to create a new
                # bookmark. Send the data back to the user with the error
                # message.
                bmark = Bmark(
                    post['url'],
                    request.user.username,
                    desc=post['description'],
                    ext=post['extended'],
                    tags=post['tags'])

                return {
                    'new': True,
                    'bmark': bmark,
                    'message': exc.message,
                    'user': request.user,
                }

        else:
            if 'hash_id' in rdict:
                hash_id = rdict['hash_id']
            elif 'hash_id' in params:
                hash_id = params['hash_id']

            bmark = BmarkMgr.get_by_hash(hash_id, request.user.username)
            if bmark is None:
                return HTTPNotFound()

            bmark.fromdict(post)
            bmark.update_tags(post['tags'])

        # if this is a new bookmark from a url, offer to go back to that url
        # for the user.
        if 'go_back' in params and params['comes_from'] != "":
            return HTTPFound(location=params['comes_from'])
        else:
            return HTTPFound(
                location=request.route_url('user_bmark_recent',
                                           username=request.user.username))


@view_config(
    route_name="bmark_readable",
    renderer="/bmark/readable.mako")
def readable(request):
    """Display a readable version of this url if we can"""
    rdict = request.matchdict
    bid = rdict.get('hash_id', None)
    username = rdict.get('username', None)
    if username:
        username = username.lower()

    if bid:
        found = BmarkMgr.get_by_hash(bid, username=username)
        if found:
            return {
                'bmark': found,
                'username': username,
            }
        else:
            return HTTPNotFound()


@view_config(route_name="user_delete_all_bookmarks",
             renderer="/accounts/index.mako")
def delete_all_bookmarks(request):
    """Delete all bookmarks of the current user"""
    rdict = request.matchdict
    post = request.POST
    with ReqAuthorize(request, username=rdict['username'].lower()):
        username = request.user.username
        if username:
            if post['delete'] == 'Delete':
                from bookie.bcelery import tasks
                tasks.delete_all_bookmarks.delay(username)
                return {
                    'user': request.user,
                    'message': 'The delete request has been queued' +
                               ' and will be acted upon shortly.',
                }
            else:
                return {
                    'user': request.user,
                    'message': 'Delete request not confirmed. ' +
                               'Please make sure to enter' +
                               ' \'Delete\' to confirm.',
                }
        else:
            return HTTPNotFound()

########NEW FILE########
__FILENAME__ = exceptions
"""Custom methods to handle 404 and 403 exceptions

These are hooked into the routes and provide a means for displaying a custom
handler that runs through a mako template. It should allow us to have pretty
themed 404/403 pages

"""


def resource_not_found(exc, request):
    """Display a custom 404 page when the HTTPNotFound fired"""
    request.response_status = "404 Not Found"
    return {'message': str(exc)}


def resource_forbidden(exc, request):
    """Display a custom 403 page when the HTTPForbidden fired"""
    request.response_status = "403 Forbidden"
    return {'message': str(exc)}

########NEW FILE########
__FILENAME__ = stats
"""Basic views with no home"""
import logging
from pyramid.view import view_config

from bookie.lib.access import ReqAuthorize
from bookie.models.auth import UserMgr


LOG = logging.getLogger(__name__)


@view_config(route_name="dashboard",
             renderer="/stats/dashboard.mako")
def dashboard(self):
    """A public dashboard of the system"""
    return {}


@view_config(route_name="user_stats", renderer="/stats/userstats.mako")
def userstats(request):
    """Stats for an individual user"""
    with ReqAuthorize(request):
        user = UserMgr.get(username=request.user.username)
    return {
        'user': user,
        'username': user.username,
    }

########NEW FILE########
__FILENAME__ = tags
"""Controllers related to viewing Tag information"""
import logging
from pyramid.view import view_config

from bookie.models import TagMgr
from bookie.views import bmarks

LOG = logging.getLogger(__name__)
RESULTS_MAX = 50


@view_config(route_name="tag_list", renderer="/tag/list.mako")
@view_config(route_name="user_tag_list", renderer="/tag/list.mako")
def tag_list(request):
    """Display a list of your tags"""
    rdict = request.matchdict
    username = rdict.get("username", None)
    if username:
        username = username.lower()

    tags_found = TagMgr.find(username=username)

    return {
        'tag_list': tags_found,
        'tag_count': len(tags_found),
        'username': username,
    }


@view_config(route_name="tag_bmarks", renderer="/bmark/recent.mako")
@view_config(route_name="user_tag_bmarks", renderer="/bmark/recent.mako")
def bmark_list(request):
    """Display the list of bookmarks for this tag"""
    # Removed because view was deprecated
    return bmarks.recent(request)

########NEW FILE########
__FILENAME__ = utils
"""View callables for utilities like bookmark imports, etc"""

import logging
from pyramid.httpexceptions import (
    HTTPFound,
    HTTPNotFound,
)
from pyramid.view import view_config

from bookie.lib.access import ReqAuthorize
from bookie.lib.applog import BmarkLog
from bookie.lib.importer import store_import_file

from bookie.bcelery import tasks
from bookie.models import (
    Bmark,
    BmarkMgr,
    DBSession,
    Hashed,
)
from bookie.models.fulltext import get_fulltext_handler
from bookie.models.queue import (
    NEW,
    ImportQueue,
    ImportQueueMgr,
)
from bookie.views import BookieView


LOG = logging.getLogger(__name__)


class ImportViews(BookieView):

    @view_config(route_name="user_import", renderer="/utils/import.mako")
    def import_bmarks(self):
        """Allow users to upload a bookmark export file for processing"""
        username = self.matchdict.get('username')

        # if auth fails, it'll raise an HTTPForbidden exception
        with ReqAuthorize(self.request):
            data = {}
            post = self.POST

            # We can't let them submit multiple times, check if this user has
            # an import in process.
            if ImportQueueMgr.get(username=username, status=NEW):
                # They have an import, get the information about it and shoot
                # to the template.
                return {
                    'existing': True,
                    'import_stats': ImportQueueMgr.get_details(
                        username=username)
                }

            if post:
                # we have some posted values
                files = post.get('import_file', None)

                if hasattr(files, 'filename'):
                    storage_dir_tpl = self.settings.get('import_files',
                                                        '/tmp/bookie')
                    storage_dir = storage_dir_tpl.format(
                        here=self.settings.get('app_root'))

                    out_fname = store_import_file(storage_dir, username, files)

                    # Mark the system that there's a pending import that needs
                    # to be completed
                    q = ImportQueue(username, unicode(out_fname))
                    DBSession.add(q)
                    DBSession.flush()
                    # Schedule a task to start this import job.
                    tasks.importer_process.delay(q.id)

                    return HTTPFound(
                        location=self.request.route_url('user_import',
                                                        username=username))
                else:
                    data['error'] = ["Please provide a file to import"]

                return data
            else:
                # we need to see if they've got
                # just display the form
                return {
                    'existing': False
                }

    @view_config(route_name="search", renderer="/utils/search.mako")
    @view_config(route_name="user_search", renderer="/utils/search.mako")
    def search(self):
        """Display the search form to the user"""
        # If this is a url /username/search then we need to update the search
        # form action to /username/results
        mdict = self.matchdict
        username = mdict.get('username', None)
        return {'username': username}

    @view_config(route_name="search_results",
                 renderer="/utils/results_wrap.mako")
    @view_config(route_name="user_search_results",
                 renderer="/utils/results_wrap.mako")
    @view_config(route_name="search_results_ajax", renderer="json")
    @view_config(route_name="user_search_results_ajax", renderer="json")
    @view_config(route_name="search_results_rest",
                 renderer="/utils/results_wrap.mako")
    @view_config(route_name="user_search_results_rest",
                 renderer="/utils/results_wrap.mako")
    def search_results(self):
        """Search for the query terms in the matchdict/GET params

        The ones in the matchdict win in the case that they both exist
        but we'll fall back to query string search=XXX

        """
        route_name = self.request.matched_route.name
        mdict = self.matchdict
        rdict = self.GET

        if 'terms' in mdict:
            phrase = " ".join(mdict['terms'])
        else:
            phrase = rdict.get('search', '')

        # Always search the fulltext content
        with_content = True

        conn_str = self.settings.get('sqlalchemy.url', False)
        searcher = get_fulltext_handler(conn_str)

        # check if we have a page count submitted
        params = self.params
        page = params.get('page', 0)
        count = params.get('count', 50)

        if rdict.get('search_mine') or 'username' in mdict:
            with_user = True
        else:
            with_user = False

        username = None
        if with_user:
            if 'username' in mdict:
                username = mdict.get('username')
            elif self.request.user and self.request.user.username:
                username = self.request.user.username

        res_list = searcher.search(
            phrase,
            content=with_content,
            username=username if with_user else None,
            ct=count,
            page=page,
        )

        # if the route name is search_ajax we want a json response
        # else we just want to return the payload data to the mako template
        if 'ajax' in route_name or 'api' in route_name:
            return {
                'success': True,
                'message': "",
                'payload': {
                    'search_results': [dict(res) for res in res_list],
                    'result_count': len(res_list),
                    'phrase': phrase,
                    'page': page,
                    'username': username,
                }
            }
        else:
            return {
                'search_results': res_list,
                'count': len(res_list),
                'max_count': 50,
                'phrase': phrase,
                'page': page,
                'username': username,
            }

    @view_config(route_name="user_export", renderer="/utils/export.mako")
    def export(self):
        """Handle exporting a user's bookmarks to file"""
        mdict = self.matchdict
        username = mdict.get('username')

        if self.request.user is not None:
            current_user = self.request.user.username
        else:
            current_user = None

        bmark_list = BmarkMgr.user_dump(username)
        BmarkLog.export(username, current_user)

        self.request.response_content_type = 'text/html'

        headers = [('Content-Disposition',
                    'attachment; filename="bookie_export.html"')]
        setattr(self.request, 'response_headerlist', headers)

        return {
            'bmark_list': bmark_list,
        }

    @view_config(route_name="redirect", renderer="/utils/redirect.mako")
    @view_config(route_name="user_redirect", renderer="/utils/redirect.mako")
    def redirect(self):
        """Handle redirecting to the selected url

        We want to increment the clicks counter on the bookmark url here

        """
        mdict = self.matchdict
        hash_id = mdict.get('hash_id', None)
        username = mdict.get('username', None)

        hashed = Hashed.query.get(hash_id)

        if not hashed:
            # for some reason bad link, 404
            return HTTPNotFound()

        hashed.clicks = hashed.clicks + 1

        if username is not None:
            bookmark = Bmark.query.\
                filter(Bmark.hash_id == hash_id).\
                filter(Bmark.username == username).one()
            bookmark.clicks = bookmark.clicks + 1

        return HTTPFound(location=hashed.url)

########NEW FILE########
__FILENAME__ = combo
"""WSGI file to serve the combo JS out of convoy"""
import os
from convoy.combo import combo_app

root_dir = os.path.dirname(__file__)
JS_FILES = root_dir + '/bookie/static/js/build'
application = combo_app(JS_FILES)

########NEW FILE########
__FILENAME__ = env
from __future__ import with_statement
from alembic import context
from ConfigParser import ConfigParser
from os import path
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

from bookie.models import Base
from bookie.models import initialize_sql


def load_bookie_ini(ini_file):
    """Load the settings for the bookie.ini file."""
    ini = ConfigParser()
    ini_path = path.join(path.dirname(path.dirname(__file__)), ini_file)
    ini.readfp(open(ini_path))
    here = path.abspath(path.join(path.dirname(__file__), '../'))
    ini.set('app:bookie', 'here', here)
    initialize_sql(dict(ini.items("app:bookie")))
    return ini

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

bookie_ini = config.get_main_option('app.ini', 'bookie.ini')
bookie_config = load_bookie_ini(bookie_ini)
sa_url = bookie_config.get('app:bookie', 'sqlalchemy.url')
config.set_main_option('sqlalchemy.url', sa_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    engine = engine_from_config(
                config.get_section(config.config_ini_section),
                prefix='sqlalchemy.',
                poolclass=pool.NullPool)

    connection = engine.connect()
    context.configure(
                connection=connection,
                target_metadata=target_metadata
                )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

########NEW FILE########
__FILENAME__ = 11087341e403_add_private_bookmark_support_to_bmarks_
"""add private bookmark support to bmarks table

Revision ID: 11087341e403
Revises: 44dccb7b8b82
Create Date: 2014-05-23 07:18:38.743431

"""

# revision identifiers, used by Alembic.
revision = '11087341e403'
down_revision = '44dccb7b8b82'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('bmarks', sa.Column('is_private', sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()))
    # Update the existing bookmarks to be public.
    connection = op.get_bind()
    current_context = op.get_context()
    meta = current_context.opts['target_metadata']
    bmarks = sa.Table('bmarks', meta, autoload=True)
    sel = sa.select([bmarks])
    stmt = bmarks.update().\
        values(is_private=False)
    connection.execute(stmt)


def downgrade():
    try:
        op.drop_column('bmarks', 'is_private')
    except sa.exc.OperationalError as exc:
        pass

########NEW FILE########
__FILENAME__ = 44dccb7b8b82_update_username_to_l
"""update username to lowercase

Revision ID: 44dccb7b8b82
Revises: 9f274a38d84
Create Date: 2014-02-27 00:55:59.913206

"""

# revision identifiers, used by Alembic.
revision = '44dccb7b8b82'
down_revision = '9f274a38d84'

from alembic import op
import sqlalchemy as sa


def upgrade():
    connection = op.get_bind()
    current_context = op.get_context()
    meta = current_context.opts['target_metadata']
    users = sa.Table('users', meta, autoload=True)
    bmarks = sa.Table('bmarks', meta, autoload=True)

    try:
        op.drop_constraint("bmarks_username_fkey", "bmarks")
        print 'dropped constraint'
    except (sa.exc.OperationalError, NotImplementedError) as exc:
        # If it's not supported then pass
        pass

    sel = sa.select([users])
    for user in connection.execute(sel):
        print 'updating for user: ' + user['username']
        lowered = sa.func.lower(user['username'])

        stmt = users.update().\
            where(users.c.username == user['username']).\
            values(username=lowered)
        connection.execute(stmt)

        stmt = bmarks.update().\
            where(bmarks.c.username == user['username']).\
            values(username=lowered)
        connection.execute(stmt)
        print 'done user: ' + user['username']

    try:
        op.create_foreign_key(
            "bmarks_username_fkey", "bmarks",
            "users", ["username"], ["username"])

        print 'added constraint'
    except (sa.exc.OperationalError, NotImplementedError) as exc:
        # If it's not supported then pass
        pass


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 5920b225d05d_load_up_to_date
"""load up to date

Revision ID: 5920b225d05d
Revises: None
Create Date: 2012-06-17 21:26:51.865959

"""

# revision identifiers, used by Alembic.
revision = '5920b225d05d'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.Unicode(length=255), nullable=True),
        sa.Column('name', sa.Unicode(length=255), nullable=True),
        # The password field is really a mapped _password field. Think this is
        # where the CheckConstraints come from.
        sa.Column('password', sa.Unicode(length=60), nullable=True),
        sa.Column('email', sa.Unicode(length=255), nullable=True),
        sa.Column('activated', sa.Boolean(), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('signup', sa.DateTime(), nullable=True),
        sa.Column('api_key', sa.Unicode(length=12), nullable=True),
        sa.Column('invite_ct', sa.Integer(), nullable=True),
        sa.Column('invited_by', sa.Unicode(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )

    op.create_table('tags',
        sa.Column('tid', sa.Integer(), nullable=False),
        sa.Column('name', sa.Unicode(length=255), nullable=True),
        sa.PrimaryKeyConstraint('tid'),
        sa.UniqueConstraint('name')
    )

    op.create_table('url_hash',
        sa.Column('hash_id', sa.Unicode(length=22), nullable=False),
        sa.Column('url', sa.UnicodeText(), nullable=True),
        sa.Column('clicks', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('hash_id')
    )

    op.create_table('bmarks',
        sa.Column('bid', sa.Integer(), nullable=False),
        sa.Column('hash_id', sa.Unicode(length=22), nullable=True),
        sa.Column('description', sa.UnicodeText(), nullable=True),
        sa.Column('extended', sa.UnicodeText(), nullable=True),
        sa.Column('stored', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('clicks', sa.Integer(), nullable=True),
        sa.Column('inserted_by', sa.Unicode(length=255), nullable=True),
        sa.Column('username', sa.Unicode(length=255), nullable=False),
        sa.Column('tag_str', sa.UnicodeText(), nullable=True),
        sa.ForeignKeyConstraint(['hash_id'], ['url_hash.hash_id'], ),
        sa.ForeignKeyConstraint(['username'], ['users.username'], ),
        sa.UniqueConstraint('username', 'hash_id'),
        sa.PrimaryKeyConstraint('bid'),
    )

    op.create_table(u'activations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.Unicode(length=60), nullable=True),
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Unicode(length=255), nullable=True),
        sa.ForeignKeyConstraint(['id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('bmark_tags',
        sa.Column('bmark_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['bmark_id'], ['bmarks.bid'], ),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.tid'], ),
        sa.PrimaryKeyConstraint('bmark_id', 'tag_id')
    )

    op.create_table('logging',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user', sa.Unicode(255), nullable=False),
        sa.Column('component', sa.Unicode(50), nullable=False),
        sa.Column('status', sa.Unicode(10), nullable=False),
        sa.Column('message', sa.Unicode(255), nullable=False),
        sa.Column('payload', sa.UnicodeText),
        sa.Column('tstamp', sa.DateTime),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('import_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.Unicode(255)),
        sa.Column('file_path', sa.Unicode(100), nullable=False),
        sa.Column('tstamp', sa.DateTime),
        sa.Column('status', sa.Integer),
        sa.Column('completed', sa.DateTime),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('stats_bookmarks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tstamp', sa.DateTime),
        sa.Column('attrib', sa.Unicode(100), nullable=False),
        sa.Column('data', sa.Integer),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('bmark_readable',
        sa.Column('bid', sa.Integer(), nullable=False, index=True),
        sa.Column('hash_id', sa.Unicode(length=22), nullable=True),
        sa.Column('content', sa.UnicodeText(), nullable=True),
        sa.Column('clean_content', sa.UnicodeText(), nullable=True),
        sa.Column('imported', sa.DateTime(), nullable=True),
        sa.Column('content_type', sa.Unicode(length=255), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('status_message', sa.Unicode(length=255), nullable=True),
        sa.ForeignKeyConstraint(['bid'], ['bmarks.bid'], ),
        sa.PrimaryKeyConstraint('bid')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('bmark_readable')
    op.drop_table('bmark_tags')
    op.drop_table(u'activations')
    op.drop_table('bmarks')
    op.drop_table('url_hash')
    op.drop_table('tags')
    op.drop_table('users')
    op.drop_table('logging')
    op.drop_table('import_queue')
    op.drop_table('stats_bookmarks')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 9f274a38d84_sample_data
"""

Revision ID: 9f274a38d84
Revises: 5920b225d05d
Create Date: 2012-06-19 21:02:38.320088

"""

# revision identifiers, used by Alembic.
revision = '9f274a38d84'
down_revision = '5920b225d05d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    """Preseed data into the system."""
    current_context = op.get_context()
    meta = current_context.opts['target_metadata']
    user = sa.Table('users', meta, autoload=True)

    # Add the initial admin user account.
    op.bulk_insert(user, [{
        'username': u'admin',
        'password': u'$2a$10$LoSEVbN6833RtwbGQlMhJOROgkjHNH4gjmzkLrIxOX1xLXNvaKFyW',
        'email': u'testing@dummy.com',
        'activated': True,
        'is_admin': True,
        'api_key': u'123456',
        }
    ])


def downgrade():
    current_context = op.get_context()
    meta = current_context.opts['target_metadata']
    user = sa.Table('users', meta, autoload=True)

    # remove all records to undo the preseed.
    op.execute(user.delete())

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Bookie documentation build configuration file, created by
# sphinx-quickstart on Fri Feb  4 23:04:10 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Bookie'
copyright = u'2011, Rick Harding'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.5.0'
# The full version, including alpha/beta/rc tags.
release = '0.5.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# html_theme = 'default'
html_theme = 'nature'

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
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Bookiedoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Bookie.tex', u'Bookie Documentation',
   u'Rick Harding', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'bookie', u'Bookie Documentation',
     [u'Rick Harding'], 1)
]

########NEW FILE########
__FILENAME__ = deduper
#!/usr/bin/env python
"""We weren't good and got duplicate bookmarks for users.

This will go through and find bookmarks, per user, with the same hash_id,
combine the tags from one onto the other, and then remove the dupe.

"""
import transaction

from collections import defaultdict
from ConfigParser import ConfigParser
from os import path
from bookie.models import initialize_sql


if __name__ == "__main__":
    ini = ConfigParser()
    ini_path = path.join(path.dirname(path.dirname(path.dirname(__file__))),
        'bookie.ini')

    ini.readfp(open(ini_path))
    initialize_sql(dict(ini.items("app:bookie")))

    from bookie.models import DBSession
    from bookie.models import Bmark

    bookmarks = Bmark.query.all()
    index = defaultdict(list)
    to_delete = []
    for b in bookmarks:
        key = (b.username, b.hash_id)
        index[key].append(b)

    for k, v in index.iteritems():
        if len(v) > 1:
            first = v[0]
            second = v[1]

            print first.hash_id
            to_delete.append(first)
            for name, tag in first.tags.items():
                if name in second.tags:
                    print "HAS IT"
                else:
                    print "ADDING" + name
                    second.tags[name] = tag

            assert len(first.tags) <= len(second.tags)

    print to_delete
    print len(to_delete)
    for b in to_delete:
        DBSession.delete(b)

    DBSession.flush()
    transaction.commit()

########NEW FILE########
__FILENAME__ = first_bookmark
#!/usr/bin/env python
"""Handle bookmark management tasks from the cmd line for this Bookie instance

    bookmarkmgr.py --add rharding --email rharding@mitechie.com

"""
import transaction

from datetime import datetime
from ConfigParser import ConfigParser
from os import path
import sys

from bookie.models import initialize_sql


if __name__ == "__main__":
    ini = ConfigParser()
    ini_path = path.join(path.dirname(path.dirname(path.dirname(__file__))),
                         'bookie.ini')

    ini.readfp(open(ini_path))
    initialize_sql(dict(ini.items("app:bookie")))

    from bookie.models import DBSession
    from bookie.models import Bmark, BmarkMgr
    url = u'http://bmark.us'

    # Make sure the bookmark isn't already there.
    if (BmarkMgr.find()):
        sys.exit(0)

    bmark_us = Bmark(url,
                     u'admin',
                     desc=u'Bookie Website',
                     ext=u'Bookie Documentation Home',
                     tags=u'bookmarks',
                     is_private=False)

    bmark_us.stored = datetime.now()
    bmark_us.updated = datetime.now()
    DBSession.add(bmark_us)
    DBSession.flush()
    transaction.commit()

########NEW FILE########
__FILENAME__ = fulltext_index_reload
#!/usr/bin/env python
"""Force the system to refresh the fulltext index.

This is useful because we've had lockup issues with Whoosh and in case we need
to reset, this will force it through celery.

"""
import argparse

from ConfigParser import ConfigParser

# TODO

########NEW FILE########
__FILENAME__ = timing
#!/bin/env python

"""Process request times from nginx access lines

The access log has been tweaked to add a request time to the end of the line

This doesn't take into account any network traffic back to the user, so only
server side request time.

We want to grab the top 10 urls and see what's the longest stuff going on

:requires: apachelog but I don't want to make it a full requirement for the
application

"""
import apachelog
import argparse

from collections import defaultdict
from operator import itemgetter

LOG_FMT = """%h %z %z %t \\"%r\\" %>s %b \\"%{Referer}i\\" \\"%{User-Agent}i\\" %x"""


def parse_args():
    """Go through the command line options

    """
    desc = "Check for the longest running requests in bookie"
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('-l', '--log', dest='log',
                            action='store',
                            default=None,
                            required=True,
                            help="log file we're reading requests from")

    parser.add_argument('-n', '--number', dest='count',
                            action='store',
                            default=10,
                            type=int,
                            required=False,
                            help="how many urls do we wish to see, default 10")


    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    parse = apachelog.parser(LOG_FMT)
    res = []

    with open(args.log) as log:
        for l in log:
            try:
                l = parse.parse(l.strip())
                rtime, url = l['%x'], l['%r']
                res.append((url, rtime))
            except Exception, exc:
                print str(exc)

    for r in sorted(res, key=itemgetter(1), reverse=True)[0:args.count]:
        print "{1} - {0}".format(*r)

########NEW FILE########
__FILENAME__ = autojsbuild
#!/usr/bin/env python
import argparse
import os
import pyinotify
import re
import subprocess

BUILDDIR = '/tmp'
REJS = re.compile('\.js$')
TEST_INDICATOR = 'test'


def parse_args():
    """Go through the command line options

    """
    desc = "Run a file watcher to auto build JS files as they're changed"
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('-w', '--watch-dir', dest='watch_dir',
                            action='store',
                            default=os.getcwd(),
                            help="What directory are we watching for changes, defaults to cwd")

    parser.add_argument('-b', '--build-dir', dest='build_dir',
                            action='store',
                            required=True,
                            help="Where are we building files to?")

    args = parser.parse_args()
    return args


class event_handler(pyinotify.ProcessEvent):
    def process_IN_CREATE(self, event):
        dispatch(event.pathname)

    def process_IN_MODIFY(self, event):
        dispatch(event.pathname)


def dispatch(fname):
    """Based on the file that's fired, process its build step

    """
    if is_js_file(fname) and BUILDDIR not in fname:
        process_js_file(fname)


def is_js_file(fname):
    """Check if this file is a .js file that needs to be built"""
    return REJS.search(fname) and \
        TEST_INDICATOR not in fname


def process_js_file(fname):
    """Build a JS file

        - should we keep the path/home with it
        - copy the file to the right place in the build dir
        - create a .min version of the file in that same place
    """
    subprocess.call('make js', shell=True)


def main(watch_dir, build_dir):
    # watch manager
    wm = pyinotify.WatchManager()
    wm.add_watch(watch_dir, pyinotify.ALL_EVENTS, rec=True)

    # event handler
    eh = event_handler()

    # notifier
    notifier = pyinotify.Notifier(wm, eh)
    notifier.loop()

if __name__ == '__main__':
    args = parse_args()

    if os.path.isdir(args.build_dir):
        BUILD_DIR = args.build_dir
    else:
        raise Exception("Cannot find dir: " + args.build_dir)


    # check the dir exists
    if os.path.isdir(args.watch_dir):
        main(args.watch_dir, args.build_dir)
    else:
        raise Exception("Cannot find dir: " + args.watch_dir)

########NEW FILE########
__FILENAME__ = generate_meta
#!/usr/bin/env python
from convoy.meta import main

main()


########NEW FILE########
__FILENAME__ = jsmin
#!/usr/bin/python

# This code is original from jsmin by Douglas Crockford, it was translated to
# Python by Baruch Even. The original code had the following copyright and
# license.
#
# /* jsmin.c
#    2007-05-22
#
# Copyright (c) 2002 Douglas Crockford  (www.crockford.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# The Software shall be used for Good, not Evil.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# */

from StringIO import StringIO


def jsmin(js):
    ins = StringIO(js)
    outs = StringIO()
    JavascriptMinify().minify(ins, outs)
    str = outs.getvalue()
    if len(str) > 0 and str[0] == '\n':
        str = str[1:]
    return str

def isAlphanum(c):
    """return true if the character is a letter, digit, underscore,
           dollar sign, or non-ASCII character.
    """
    return ((c >= 'a' and c <= 'z') or (c >= '0' and c <= '9') or
            (c >= 'A' and c <= 'Z') or c == '_' or c == '$' or c == '\\' or (c is not None and ord(c) > 126));

class UnterminatedComment(Exception):
    pass

class UnterminatedStringLiteral(Exception):
    pass

class UnterminatedRegularExpression(Exception):
    pass

class JavascriptMinify(object):

    def _outA(self):
        self.outstream.write(self.theA)
    def _outB(self):
        self.outstream.write(self.theB)

    def _get(self):
        """return the next character from stdin. Watch out for lookahead. If
           the character is a control character, translate it to a space or
           linefeed.
        """
        c = self.theLookahead
        self.theLookahead = None
        if c == None:
            c = self.instream.read(1)
        if c >= ' ' or c == '\n':
            return c
        if c == '': # EOF
            return '\000'
        if c == '\r':
            return '\n'
        return ' '

    def _peek(self):
        self.theLookahead = self._get()
        return self.theLookahead

    def _next(self):
        """get the next character, excluding comments. peek() is used to see
           if an unescaped '/' is followed by a '/' or '*'.
        """
        c = self._get()
        if c == '/' and self.theA != '\\':
            p = self._peek()
            if p == '/':
                c = self._get()
                while c > '\n':
                    c = self._get()
                return c
            if p == '*':
                c = self._get()
                while 1:
                    c = self._get()
                    if c == '*':
                        if self._peek() == '/':
                            self._get()
                            return ' '
                    if c == '\000':
                        raise UnterminatedComment()

        return c

    def _action(self, action):
        """do something! What you do is determined by the argument:
           1   Output A. Copy B to A. Get the next B.
           2   Copy B to A. Get the next B. (Delete A).
           3   Get the next B. (Delete B).
           action treats a string as a single character. Wow!
           action recognizes a regular expression if it is preceded by ( or , or =.
        """
        if action <= 1:
            self._outA()

        if action <= 2:
            self.theA = self.theB
            if self.theA == "'" or self.theA == '"':
                while 1:
                    self._outA()
                    self.theA = self._get()
                    if self.theA == self.theB:
                        break
                    if self.theA <= '\n':
                        raise UnterminatedStringLiteral()
                    if self.theA == '\\':
                        self._outA()
                        self.theA = self._get()


        if action <= 3:
            self.theB = self._next()
            if self.theB == '/' and (self.theA == '(' or self.theA == ',' or
                                     self.theA == '=' or self.theA == ':' or
                                     self.theA == '[' or self.theA == '?' or
                                     self.theA == '!' or self.theA == '&' or
                                     self.theA == '|' or self.theA == ';' or
                                     self.theA == '{' or self.theA == '}' or
                                     self.theA == '\n'):
                self._outA()
                self._outB()
                while 1:
                    self.theA = self._get()
                    if self.theA == '/':
                        break
                    elif self.theA == '\\':
                        self._outA()
                        self.theA = self._get()
                    elif self.theA <= '\n':
                        raise UnterminatedRegularExpression()
                    self._outA()
                self.theB = self._next()


    def _jsmin(self):
        """Copy the input to the output, deleting the characters which are
           insignificant to JavaScript. Comments will be removed. Tabs will be
           replaced with spaces. Carriage returns will be replaced with linefeeds.
           Most spaces and linefeeds will be removed.
        """
        self.theA = '\n'
        self._action(3)

        while self.theA != '\000':
            if self.theA == ' ':
                if isAlphanum(self.theB):
                    self._action(1)
                else:
                    self._action(2)
            elif self.theA == '\n':
                if self.theB in ['{', '[', '(', '+', '-']:
                    self._action(1)
                elif self.theB == ' ':
                    self._action(3)
                else:
                    if isAlphanum(self.theB):
                        self._action(1)
                    else:
                        self._action(2)
            else:
                if self.theB == ' ':
                    if isAlphanum(self.theA):
                        self._action(1)
                    else:
                        self._action(3)
                elif self.theB == '\n':
                    if self.theA in ['}', ']', ')', '+', '-', '"', '\'']:
                        self._action(1)
                    else:
                        if isAlphanum(self.theA):
                            self._action(1)
                        else:
                            self._action(3)
                else:
                    self._action(1)

    def minify(self, instream, outstream):
        self.instream = instream
        self.outstream = outstream
        self.theA = '\n'
        self.theB = None
        self.theLookahead = None

        self._jsmin()
        self.instream.close()

if __name__ == '__main__':
    import sys
    jsm = JavascriptMinify()
    jsm.minify(sys.stdin, sys.stdout)

########NEW FILE########
__FILENAME__ = jsmin_all
#!/usr/bin/env python2

"""Handle minifying all javascript files in the build directory by walking

$ jsmin_all.py $lp_js_root

"""
import os
import re
import sys
from jsmin import JavascriptMinify


def dirwalk(dir):
    "walk a directory tree, using a generator"
    for f in os.listdir(dir):
        fullpath = os.path.join(dir,f)
        if os.path.isdir(fullpath) and not os.path.islink(fullpath):
            for x in dirwalk(fullpath):  # recurse into subdir
                yield x
        else:
            yield fullpath


def is_min(filename):
    """Check if this file is alrady a minified file"""
    return re.search("min.js$", filename)

def minify(filename):
    """Given a filename, handle minifying it as -min.js"""
    if not is_min(filename):
        new_filename = re.sub(".js$", "-min.js", filename)

        with open(filename) as shrink_me:
            with open(new_filename, 'w') as tobemin:
                jsm = JavascriptMinify()
                jsm.minify(shrink_me, tobemin)


if __name__ == '__main__':
    root = sys.argv[1]

    if os.path.isfile(root):
        minify(root)
    else:
        [minify(f) for f in dirwalk(root)]

########NEW FILE########
__FILENAME__ = backup
#!/usr/bin/env python
import gzip
import logging
import os
import urllib
from datetime import date


EXPORT_URL = "http://rick.bmark.us/export"
BACKUP_DIR = '/home/rharding/bookie'
LOG = logging.getLogger(__name__)
BACKUP_FILE = "bookie_export_{0}".format(date.today().strftime('%Y_%m_%d'))


if __name__ == "__main__":
    export = urllib.urlopen(EXPORT_URL)
    backup = gzip.open(os.path.join(BACKUP_DIR, BACKUP_FILE + '.gz'), 'w')
    backup.write(export.read())
    export.close()
    backup.close()
########NEW FILE########
__FILENAME__ = smtpsink
#!/usr/bin/env python

"""
Need to install Logbook and inbox to get the smtpsink to work

"""


from inbox import Inbox

PORT = 4467
ADDR = '0.0.0.0'
inbox = Inbox()


@inbox.collate
def handle(*args, **kwargs):
    outfile = open('email_log', 'a')
    for arg in args:
        outfile.write(arg + "\n")

    for key, arg in kwargs.items():
        outfile.write("{0}: {1}".format(key, arg))

    outfile.write('*' * 30)

# Bind directly.
inbox.serve(address=ADDR, port=PORT)
print "serving on {0}:{1}".format(ADDR, PORT)

########NEW FILE########
__FILENAME__ = readable_consumer
import beanstalkc
import json
import urllib
import urllib2

SERVER = '127.0.0.5'
PORT = 11300

# setup connection
bean = beanstalkc.Connection(host="localhost",
                             port=11300,
                             parse_yaml=lambda x: x.split("\n"))

def post_readable(data):
    """Send off the parsing request to the web server"""
    url = 'http://127.0.0.1:6543/api/v1/bmarks/readable'

    if 'content' in data:
        data['content'] = data['content'].encode('utf-8')

    http_data = urllib.urlencode(data)

    try:
        req = urllib2.Request(url, http_data)
        response = urllib2.urlopen(req)
        res = response.read()
        assert "true" in str(res)
    except Exception, exc:
        print "FAILED: " + data['hash_id']
        print str(exc)

bean.watch('default')

while True:
    job = bean.reserve()
    j = json.loads(urllib.unquote(job.body))
    if 'hash_id' in j:
        print j['hash_id']
        post_readable(j)
    else:
        print "ERROR: missing fields -- " + str(j['hash_id'])
    job.delete()


########NEW FILE########
__FILENAME__ = readable_index_update
#!/usr/bin/env python

from ConfigParser import ConfigParser
from os import path
from bookie.models import initialize_sql

if __name__ == "__main__":
    ini = ConfigParser()
    ini_path = path.join(
        path.dirname(path.dirname(path.dirname(__file__))),
        'bookie.ini')

    ini.readfp(open(ini_path))
    initialize_sql(dict(ini.items("app:bookie")))

    from bookie.models import Readable
    from bookie.models import Bmark
    from bookie.models.fulltext import get_writer

    writer = get_writer()

    readable_bmarks = Readable.query.all()
    for bmark in readable_bmarks:
        b = Bmark.query.get(bmark.bid)

        if b:
            writer.update_document(
                bid=unicode(b.bid),
                description=b.description if b.description else u"",
                extended=b.extended if b.extended else u"",
                tags=b.tag_str if b.tag_str else u"",
                readable=b.readable.content,
            )
    writer.commit()

########NEW FILE########
