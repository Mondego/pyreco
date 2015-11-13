__FILENAME__ = auth
"""Authentication functions are offered here in three groups.

    1. The mechanics of auth, like generating a hex digest or assembling the
       data.

    2. Tools for applying auth requirements to functions, eg. decorators.

    3. Mixins for adding authenticaiton handling to MessageHandler's and
       Document classes
"""

import bcrypt
import functools
import logging


###
### Password Helpers
###

BCRYPT = 'bcrypt'
PASSWD_DELIM = '|||'


def gen_hexdigest(raw_password, algorithm=BCRYPT, salt=None):
    """Takes the algorithm, salt and password and uses Python's
    hashlib to produce the hash. Currently only supports bcrypt.
    """
    if raw_password is None:
        raise ValueError('No empty passwords, fool')
    if algorithm == BCRYPT:
        # bcrypt has a special salt
        if salt is None:
            salt = bcrypt.gensalt()
        return (algorithm, salt, bcrypt.hashpw(raw_password, salt))
    raise ValueError('Unknown password algorithm')


def build_passwd_line(algorithm, salt, digest):
    """Simply takes the inputs for a passwd entry and puts them
    into the convention for storage
    """
    return PASSWD_DELIM.join([algorithm, salt, digest])


def split_passwd_line(password_line):
    """Takes a password line and returns the line split by PASSWD_DELIM
    """
    return password_line.split(PASSWD_DELIM)


###
### Authentication decorators
###

def authenticated(method):
    """Decorate request handler methods with this to require that the user be
    logged in. Works by checking for the existence of self.current_user as set
    by a RequestHandler's prepare() function.
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            return self.render_error(self._AUTH_FAILURE, self.auth_error)
        return method(self, *args, **kwargs)
    return wrapper


def web_authenticated(method):
    """Same as `authenticated` except it redirects a user to the login page
    specified by self.application.login_url
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            has_login_url = hasattr(self.application, 'login_url')
            if has_login_url and self.application.login_url is not None:
                return self.redirect(self.application.login_url)
            else:
                error = 'web_authentication called with undefined <login_url>'
                logging.error(error)
                return self.render_error(self._AUTH_FAILURE)
        return method(self, *args, **kwargs)
    return wrapper


###
### Mixins to extend MessageHandlers with auth funcitons
###

class UserHandlingMixin(object):
    """A request handler that uses this mixin can also use the decorators
    above. This mixin is intended to make the interaction with authentication
    generic without insisting on a particular strategy.
    """

    @property
    def current_user(self):
        """The authenticated user for this message.

        Determined by either get_current_user, which you can override to
        set the user based on, e.g., a cookie. If that method is not

        overridden, this method always returns None.

        We lazy-load the current user the first time this method is called
        and cache the result after that.
        """
        if not hasattr(self, "_current_user"):
            self._current_user = self.get_current_user()
        return self._current_user

    def get_current_user(self):
        """Override to determine the current user from, e.g., a cookie.
        """
        return None

    @property
    def current_userprofile(self):
        """Same idea for the user's profile
        """
        if not hasattr(self, "_current_userprofile"):
            self._current_userprofile = self.get_current_userprofile()
        return self._current_userprofile

    def get_current_userprofile(self):
        """Override to determine the current user
        """
        return None

    def auth_error(self):
        """Override with actions to perform before rendering the error output.
        """
        pass

########NEW FILE########
__FILENAME__ = autoapi
from request_handling import JSONMessageHandler, FourOhFourException
from schematics.serialize import to_json, make_safe_json

import ujson as json


class AutoAPIBase(JSONMessageHandler):
    """AutoAPIBase generates a JSON REST API for you. *high five!*
    I also read this link for help in propertly defining the behavior of HTTP
    PUT and POST: http://stackoverflow.com/questions/630453/put-vs-post-in-rest
    """
    
    model = None
    queries = None

    _PAYLOAD_DATA = 'data'

    ###
    ### Input Handling
    ###

    def _get_body_as_data(self):
        """Returns the body data based on the content_type requested by the
        client.
        """
        ### Locate body data by content type
        if self.message.content_type == 'application/json':
            body = self.message.body
        else:
            body = self.get_argument('data')

        ### Load found JSON into Python structure
        if body:
            body = json.loads(body)

        return body

    def _convert_to_id(self, datum):
        """`datum` in this function is an id that needs to be validated and
        converted to it's native type.
        """
        try:
            converted = self.model.id.validate(datum)  # interface might change
            return (True, converted)
        except Exception, e:
            return (False, e)

    def _convert_to_model(self, datum):
        """Handles the details of converting some data into a model or
        information about why data was invalid.
        """
        try:
            converted = self.model(**datum)
            converted.validate()
            return (True, converted)
        except Exception, e:
            return (False, e)

    def _convert_item_or_list(self, body_data, is_list, converter):
        """This function takes the output of a _get_body* function and checks
        it against the model for inputs.

        In some cases this is a list of IDs or in others it's a complete
        document. The details of this are controlled by the `converter`
        function, provided as the last argument.

        If a list is provided, the output is a boolean and a list of
        two-tuples, each containing a boolean and the converted datum, as
        provided by the `converter` function.

        If a single item is provided as input the converter function is called
        and the output is returned.
        """
        if not body_data:
            return (True, None)

        if is_list:
            results = list()
            all_valid = True
            for idd in body_data:
                (is_valid, data) = converter(idd)
                if not is_valid:
                    all_valid = False
                results.append((is_valid, data))
            return (all_valid, results)
        else:
            (is_valid, data) = converter(body_data)
            return (is_valid, data)
    
    ###
    ### Output Processing
    ###

    def _crud_to_http(self, crud_status):
        """Translates the crud status returned by a `QuerySet` into the status
        used for HTTP.
        """
        if self.queries.MSG_FAILED == crud_status:
            return self._FAILED_CODE
        
        elif self.queries.MSG_CREATED == crud_status:
            return self._CREATED_CODE
        
        elif self.queries.MSG_UPDATED == crud_status:
            return self._UPDATED_CODE
        
        elif self.queries.MSG_OK == crud_status:
            return self._SUCCESS_CODE
        
        elif len(crud_status) == 0:
            return self._SUCCESS_CODE
        
        else:
            return self._SERVER_ERROR

    def _make_presentable(self, datum):
        """This function takes either a model instance or a dictionary
        representation of some model and returns a dictionary one safe for
        transmitting as payload.
        """
        if isinstance(datum, dict):
            iid = str(datum.get('id'))
            model_instance = self.model(**datum)
            instance = to_json(model_instance, encode=False)
        else:
            iid = str(datum.id)
            instance = to_json(datum, encode=False)

        data = make_safe_json(self.model, instance, 'owner', encode=False)

        return data

    def _add_status(self, datum, status_code):
        """Passed a status tuples of the form (status code, processed model),
        it generates the status structure to carry info about the processing.
        """
        datum[self._STATUS_CODE] = status_code
        status_msg = self._response_codes.get(status_code,
                                              str(status_code))
        datum[self._STATUS_MSG] = status_msg
        return datum

    def _parse_crud_datum(self, crud_datum):
        """Parses the result of some crud operation into an HTTP-ready
        datum instead.
        """
        (crud_status, datum) = crud_datum
        data = self._make_presentable(datum)
        http_status_code = self._crud_to_http(crud_status)
        data = self._add_status(data, http_status_code)
        return (http_status_code, data)

    def _generate_response(self, status_data):
        """Parses crud data and generates the full HTTP response. The idea here
        is to translate the results of some crud operation into something
        appropriate for HTTP.

        `status_data` is ambiguously named because it might be a list and it
        might be a single item. This will likely be altered when the crud
        interface's ambiguous functions go away too.
        """
        ### Case 1: `status_data` is a list
        if isinstance(status_data, list):
            ### Aggregate all the statuses and collect the data items in a list
            statuses = set()
            data_list = list()
            for status_datum in status_data:
                (http_status_code, data) = self._parse_crud_datum(status_datum)
                data_list.append(data)
                statuses.add(http_status_code)

            ### If no statuses are found, just use 200
            if len(statuses) == 0:
                http_status_code = self._SUCCESS_CODE
            ### If more than one status, use HTTP 207
            elif len(statuses) > 1:
                http_status_code = self._MULTI_CODE
            ### If only one status is there, use it for the HTTP status
            else:
                http_status_code = statuses.pop()

            ### Store accumulated data to payload
            self.add_to_payload(self._PAYLOAD_DATA, data_list)

            ### Return full HTTP response
            return self.render(status_code=http_status_code)
        
        ### Case 2: `status_data` is a single item
        else:
            ### Extract datum
            (http_status_code, data) = self._parse_crud_datum(status_data)

            ### Store datum as data on payload
            self.add_to_payload(self._PAYLOAD_DATA, data)

            ### Return full HTTP response
            return self.render(status_code=http_status_code)

    ###
    ### Validation
    ###

    def url_matches_body(self, ids, shields):
        """ We want to make sure that if the request asks for a specific few
        resources, those resources and only those resources are in the body
        """
        if not ids:
            return True

        if isinstance(shields, list):
            for item_id, shield in zip(ids, shields):
                if item_id != str(shield.id):  # enforce a good request
                    return False
        else:
            return ids != str(shields)

        return True

    ###
    ### HTTP methods
    ###

    ### There is a pattern that is used in each of the calls. The basic idea is
    ### to handle three cases in an appropriate way. These three cases apply to
    ### input provided in the URL, such as document ids, or data provided via
    ### an HTTP method, like POST.
    ###
    ### For URLs we handle 0 IDs, 1 ID, and N IDs. Zero, One, Infinity.
    ### For data we handle 0 datums, 1 datum and N datums. ZOI, again.
    ###
    ### Paging and authentication will be offered soon.

    def get(self, ids=""):
        """HTTP GET implementation.

        IDs:
          * 0 IDs: produces a list of items presented. Paging will be available
            soon.
          * 1 ID: This produces the corresponding document.
          * N IDs: This produces a list of corresponding documents.

        Data: N/A
        """
        
        try:
            ### Setup environment
            is_list = isinstance(ids, list)
            
            # Convert arguments
            (valid, data) = self._convert_item_or_list(ids, is_list,
                                                       self._convert_to_id)

            # CRUD stuff
            if is_list:
                valid_ids = list()
                errors_ids = list()
                for status in data:
                    (is_valid, idd) = status
                    if is_valid:
                        valid_ids.append(idd)
                    else:
                        error_ids.append(idd)
                models = self.queries.read(valid_ids)
                response_data = models
            else:
                datum_tuple = self.queries.read(data)
                response_data = datum_tuple
            # Handle status update
            return self._generate_response(response_data)
        
        except FourOhFourException:
            return self.render(status_code=self._NOT_FOUND)
        
    def post(self, ids=""):
        """HTTP POST implementation.

        The opinion of this `post()` implementation is that POST is ideally
        suited for saving documents for the first time. Using POST triggers the
        ID generation system and the document is saved with an ID. The ID is
        then returned as part of the generated response.

        We are aware there is sometimes some controversy over what POST and PUT
        mean. You can please some of the people, some of the time...

        Data:
          * 0 Data: This case isn't useful so it throws an error.
          * 1 Data: Writes a single document to queryset.
          * N Datas: Attempts to write each document to queryset.
        """
        body_data = self._get_body_as_data()
        is_list = isinstance(body_data, list)

        # Convert arguments
        (valid, data) = self._convert_item_or_list(body_data, is_list,
                                                   self._convert_to_model)

        if not valid:
            return self.render(status_code=self._FAILED_CODE)

        ### If no ids, we attempt to create the data
        if ids == "":
            statuses = self.queries.create(data)
            return self._generate_response(statuses)
        else:
            if isinstance(ids, list):
                items = ids
            else:
                items = ids.split(self.application.MULTIPLE_ITEM_SEP)

            ### TODO: add informative error message
            if not self.url_matches_body(items, data):
                return self.render(status_code=self._FAILED_CODE)

            statuses = self.queries.update(data)
            return self._generate_response(statuses)

    def put(self, ids=""):
        """HTTP PUT implementation.

        The opinion of this `put()` implementation is that PUT is ideally
        suited for saving documents that have been saved at least once before,
        signaled by the presence of an id. This call will write the entire
        input on top of any data previously there, rendering it idempotent, but
        also destructive.
        
        IDs: 
          * 0 IDs: Generates IDs for each item of input and saves to QuerySet.
          * 1 ID: Attempts to map one document from input to the provided ID.
          * N IDs: Attempts to one-to-one map documents from input to IDs.

        Data:
          * 0 Data: This case isn't useful so it throws an error.
          * 1 Data: Writes a single document to queryset.
          * N Datas: Attempts to write each document to queryset.
        """
        body_data = self._get_body_as_data()
        is_list = isinstance(body_data, list)

        # Convert arguments
        (valid, data) = self._convert_item_or_list(body_data, is_list,
                                                   self._convert_to_model)

        if not valid:
            return self.render(status_code=self._FAILED_CODE)

        ### TODO: add informative error message
        items = ids.split(self.application.MULTIPLE_ITEM_SEP)

        if not self.url_matches_body(items, data):
            return self.render(status_code=self._FAILED_CODE)

        crud_statuses = self.queries.update(data)
        return self._generate_response(crud_statuses)

    def delete(self, ids=""):
        """HTTP DELETE implementation.

        Basically just attempts to delete documents by the provided ID.
        
        IDs: 
          * 0 IDs: Returns a 400 error
          * 1 ID: Attempts to delete a single document by ID
          * N IDs: Attempts to delete many documents by ID.

        Data: N/A
        """
        body_data = self._get_body_as_data()
        is_list = isinstance(body_data, list)
        crud_statuses = list()

        # Convert arguments
        (valid, data) = self._convert_item_or_list(body_data, is_list,
                                                   self._convert_to_model)

        if not valid:
            return self.render(status_code=400)

        if ids:
            item_ids = ids.split(self.application.MULTIPLE_ITEM_SEP)
            try:
                crud_statuses = self.queries.destroy(item_ids)
            except FourOhFourException:
                return self.render(status_code=self._NOT_FOUND)
            
        return self._generate_response(crud_statuses)
        

########NEW FILE########
__FILENAME__ = caching
import os
import time
from exceptions import NotImplementedError


###
### Sessions are basically caches
###

def generate_session_id():
    """Returns random 32 bit string for cache id
    """
    return os.urandom(32).encode('hex')


###
### Cache storage
###

class BaseCacheStore(object):
    """Ram based cache storage. Essentially uses a dictionary stored in
    the app to store cache id => serialized cache data
    """
    def __init__(self, **kwargs):
        super(BaseCacheStore, self).__init__(**kwargs)
        self._cache_store = dict()

    def save(self, key, data, expire=None):
        """Save the cache data and metadata to the backend storage
        if necessary, as defined by self.dirty == True. On successful
        save set dirty to False.
        """
        cache_item = {
            'data': data,
            'expire': expire,
        }
        self._cache_store[key] = cache_item

    def load(self, key):
        """Load the stored data from storage backend or return None if the
        session was not found. Stale cookies are treated as empty.
        """
        try:
            if key in self._cache_store:
                data = self._cache_store[key]

                # It's an in memory cache, so we must manage
                if not data.get('expire', None) or data['expire'] > time.time():
                    return data['data']
            return None
        except:
            return None

    def delete(self, key):
        """Remove all data for the `key` from storage.
        """
        if key in self._cache_store:
            del self._cache_store[key]

    def delete_expired(self):
        """Deletes sessions with timestamps in the past from storage.
        """
        del_keys = list()
        for key, data in self._cache_store.items():
            if data.get('expire', None) and data['expire'] < time.time():
                del_keys.append(key)
        map(self.delete, del_keys)

###
### Redis Cache Store
###

class RedisCacheStore(BaseCacheStore):
    """Redis cache using Redis' EXPIRE command to set 
    expiration time. `delete_expired` raises NotImplementedError.
    Pass the Redis connection instance as `db_conn`.

    ##################
    IMPORTANT NOTE:

    This caching store uses a flat namespace for storing keys since
    we cannot set an EXPIRE for a hash `field`. Use different
    Redis databases to keep applications from overwriting 
    keys of other applications.

    ##################
    
    The Redis connection uses the redis-py api located here:
    https://github.com/andymccurdy/redis-py
    """
    
    def __init__(self, redis_connection=None, **kwargs):
        super(RedisCacheStore, self).__init__(**kwargs)
        self._cache_store = redis_connection

    def save(self, key, data, expire=None):
        """expire will be a Unix timestamp
        from time.time() + <value> which is 
        a value in seconds."""

        pipe = self._cache_store.pipeline()
        pipe.set(key, data)
        if expire:
            expire_seconds = expire - time.time()
            assert(expire_seconds > 0)
            pipe.expire(key, int(expire_seconds))
        pipe.execute()
        
    def load(self, key):
        """return the value of `key`. If key
        does not exist or has expired, `hget` will
        return None"""

        return self._cache_store.get(key)
    
    def delete(self, key):
        self._cache_store.delete(key)
        
    def delete_expired(self):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = connections
import ujson as json
from uuid import uuid4
import cgi
import re
import logging
import Cookie

from request import to_bytes, to_unicode, parse_netstring, Request
from request_handling import http_response, coro_spawn


###
### Connection Classes
###

class Connection(object):
    """This class is an abstraction for how Brubeck sends and receives
    messages. The idea is that Brubeck waits to receive messages for some work
    and then it responds. Therefore each connection should essentially be a
    mechanism for reading a message and a mechanism for responding, if a
    response is necessary.
    """

    def __init__(self, incoming=None, outgoing=None):
        """The base `__init__()` function configures a unique ID and assigns
        the incoming and outgoing mechanisms to a name.

        `in_sock` and `out_sock` feel like misnomers at this time but they are
        preserved for a transition period.
        """
        self.sender_id = uuid4().hex
        self.in_sock = incoming
        self.out_sock = outgoing

    def _unsupported(self, name):
        """Simple function that raises an exception.
        """
        error_msg = 'Subclass of Connection has not implemented `%s()`' % name
        raise NotImplementedError(error_msg)


    def recv(self):
        """Receives a raw mongrel2.handler.Request object that you
        can then work with.
        """
        self._unsupported('recv')

    def _recv_forever_ever(self, fun_forever):
        """Calls a handler function that runs forever. The handler can be
        interrupted with a ctrl-c, though.
        """
        try:
            fun_forever()
        except KeyboardInterrupt, ki:
            # Put a newline after ^C
            print '\nBrubeck going down...'

    def send(self, uuid, conn_id, msg):
        """Function for sending a single message.
        """
        self._unsupported('send')

    def reply(self, req, msg):
        """Does a reply based on the given Request object and message.
        """
        self.send(req.sender, req.conn_id, msg)

    def reply_bulk(self, uuid, idents, data):
        """This lets you send a single message to many currently
        connected clients.  There's a MAX_IDENTS that you should
        not exceed, so chunk your targets as needed.  Each target
        will receive the message once by Mongrel2, but you don't have
        to loop which cuts down on reply volume.
        """
        self._unsupported('reply_bulk')
        self.send(uuid, ' '.join(idents), data)

    def close(self):
        """Close the connection.
        """
        self._unsupported('close')

    def close_bulk(self, uuid, idents):
        """Same as close but does it to a whole bunch of idents at a time.
        """
        self._unsupported('close_bulk')
        self.reply_bulk(uuid, idents, "")


###
### ZeroMQ
###

def load_zmq():
    """This function exists to determine where zmq should come from and then
    cache that decision at the module level.
    """
    if not hasattr(load_zmq, '_zmq'):
        from request_handling import CORO_LIBRARY
        if CORO_LIBRARY == 'gevent':
            from zmq import green as zmq
        elif CORO_LIBRARY == 'eventlet':
            from eventlet.green import zmq
        load_zmq._zmq = zmq

    return load_zmq._zmq


def load_zmq_ctx():
    """This function exists to contain the namespace requirements of generating
    a zeromq context, while keeping the context at the module level. If other
    parts of the system need zeromq, they should use this function for access
    to the existing context.
    """
    if not hasattr(load_zmq_ctx, '_zmq_ctx'):
        zmq = load_zmq()
        zmq_ctx = zmq.Context()
        load_zmq_ctx._zmq_ctx = zmq_ctx

    return load_zmq_ctx._zmq_ctx


###
### Mongrel2
###

class Mongrel2Connection(Connection):
    """This class is an abstraction for how Brubeck sends and receives
    messages. This abstraction makes it possible for something other than
    Mongrel2 to be used easily.
    """
    MAX_IDENTS = 100

    def __init__(self, pull_addr, pub_addr):
        """sender_id = uuid.uuid4() or anything unique
        pull_addr = pull socket used for incoming messages
        pub_addr = publish socket used for outgoing messages

        The class encapsulates socket type by referring to it's pull socket
        as in_sock and it's publish socket as out_sock.
        """
        zmq = load_zmq()
        ctx = load_zmq_ctx()

        in_sock = ctx.socket(zmq.PULL)
        out_sock = ctx.socket(zmq.PUB)

        super(Mongrel2Connection, self).__init__(in_sock, out_sock)
        self.in_addr = pull_addr
        self.out_addr = pub_addr

        in_sock.connect(pull_addr)
        out_sock.setsockopt(zmq.IDENTITY, self.sender_id)
        out_sock.connect(pub_addr)

    def process_message(self, application, message):
        """This coroutine looks at the message, determines which handler will
        be used to process it, and then begins processing.

        The application is responsible for handling misconfigured routes.
        """
        request = Request.parse_msg(message)
        if request.is_disconnect():
            return  # Ignore disconnect msgs. Dont have areason to do otherwise
        handler = application.route_message(request)
        result = handler()

        if result:
            http_content = http_response(result['body'], result['status_code'],
                                         result['status_msg'], result['headers'])

            application.msg_conn.reply(request, http_content)

    def recv(self):
        """Receives a raw mongrel2.handler.Request object that you from the
        zeromq socket and return whatever is found.
        """
        zmq_msg = self.in_sock.recv()
        return zmq_msg

    def recv_forever_ever(self, application):
        """Defines a function that will run the primary connection Brubeck uses
        for incoming jobs. This function should then call super which runs the
        function in a try-except that can be ctrl-c'd.
        """
        def fun_forever():
            while True:
                request = self.recv()
                coro_spawn(self.process_message, application, request)
        self._recv_forever_ever(fun_forever)

    def send(self, uuid, conn_id, msg):
        """Raw send to the given connection ID at the given uuid, mostly used
        internally.
        """
        header = "%s %d:%s," % (uuid, len(str(conn_id)), str(conn_id))
        self.out_sock.send(header + ' ' + to_bytes(msg))

    def reply(self, req, msg):
        """Does a reply based on the given Request object and message.
        """
        self.send(req.sender, req.conn_id, msg)

    def reply_bulk(self, uuid, idents, data):
        """This lets you send a single message to many currently
        connected clients.  There's a MAX_IDENTS that you should
        not exceed, so chunk your targets as needed.  Each target
        will receive the message once by Mongrel2, but you don't have
        to loop which cuts down on reply volume.
        """
        self.send(uuid, ' '.join(idents), data)

    def close(self):
        """Tells mongrel2 to explicitly close the HTTP connection.
        """
        pass

    def close_bulk(self, uuid, idents):
        """Same as close but does it to a whole bunch of idents at a time.
        """
        self.reply_bulk(uuid, idents, "")


###
### WSGI
###

class WSGIConnection(Connection):
    """
    """

    def __init__(self, port=6767):
        super(WSGIConnection, self).__init__()
        self.port = port

    def process_message(self, application, environ, callback):
        request = Request.parse_wsgi_request(environ)
        handler = application.route_message(request)
        result = handler()

        wsgi_status = ' '.join([str(result['status_code']), result['status_msg']])
        headers = [(k, v) for k,v in result['headers'].items()]
        callback(str(wsgi_status), headers)

        return [to_bytes(result['body'])]

    def recv_forever_ever(self, application):
        """Defines a function that will run the primary connection Brubeck uses
        for incoming jobs. This function should then call super which runs the
        function in a try-except that can be ctrl-c'd.
        """
        def fun_forever():
            from brubeck.request_handling import CORO_LIBRARY
            print "Serving on port %s..." % (self.port)

            def proc_msg(environ, callback):
                return self.process_message(application, environ, callback)

            if CORO_LIBRARY == 'gevent':
                from gevent import wsgi
                server = wsgi.WSGIServer(('', self.port), proc_msg)
                server.serve_forever()

            elif CORO_LIBRARY == 'eventlet':
                import eventlet.wsgi
                server = eventlet.wsgi.server(eventlet.listen(('', self.port)),
                                              proc_msg)

        self._recv_forever_ever(fun_forever)

########NEW FILE########
__FILENAME__ = datamosh
from schematics.models import Model
from schematics.types.base import UUIDType, StringType


from brubeck.timekeeping import MillisecondType


"""The purpose of the datamosh model is to provide Mixins for building data
models and data handlers.  In it's current state, it provides some helpers
for handling HTTP request arguments that map members of a data model.

I wanted the name of this module to indicate that it's a place to put request
handling code alongside the models they're intended for handling.  It's a mosh
pit of data handling logic.
"""


###
### Helper Functions
###

def get_typed_argument(arg_name, default, handler, type_fun):
    """Simple short hand for handling type detection of arguments.
    """
    value = handler.get_argument(arg_name, default)
    try:
        value = type_fun(value)
    except:
        value = default
    return value


###
### Ownable Data Mixins
###

class OwnedModelMixin(Model):
    """This class standardizes the approach to expressing ownership of data
    """
    owner_id = UUIDType(required=True)
    owner_username = StringType(max_length=30, required=True)


class OwnedHandlerMixin:
    """This mixin supports receiving an argument called `owner`, intended to
    map to the `owner_username` field in the Model above.
    """
    def get_owner_username(self, default_usernam=None):
        owner_username = get_typed_argument('owner', default_username, self,
                                            str)
        return owner_username


###
### Streamable Data Handling
###

class StreamedModelMixin(Model):
    """This class standardizes the way streaming data is handled by adding two
    fields that can be used to sort the list.
    """
    created_at = MillisecondType(default=0)
    updated_at = MillisecondType(default=0)


class StreamedHandlerMixin:
    """Provides standard definitions for paging arguments
    """
    def get_stream_offset(self, default_since=0):
        """This function returns some offset for use with either `created_at`
        or `updated_at` as provided by `StreamModelMixin`.
        """
        since = get_typed_argument('since', default_since, self, long)
        return since

    def get_paging_arguments(self, default_page=0, default_count=25,
                             max_count=25):
        """This function checks for arguments called `page` and `count`. It
        returns a tuple either with their value or default values.

        `max_count` may be used to put a limit on the number of items in each
        page. It defaults to 25, but you can use `max_count=None` for no limit.
        """
        page = get_typed_argument('page', default_page, self, int)
        count = get_typed_argument('count', default_count, self, int)
        if max_count and count > max_count:
            count = max_count

        default_skip = page * count
        skip = get_typed_argument('skip', default_skip, self, int)

        return (page, count, skip)

########NEW FILE########
__FILENAME__ = models
###
### DictShield documents
###

from schematics.models import Model
from schematics.types import (StringType,
                              BooleanType,
                              URLType,
                              EmailType,
                              LongType)


import auth
from timekeeping import curtime
from datamosh import OwnedModelMixin, StreamedModelMixin

import re


###
### User Document
###

class User(Model):
    """Bare minimum to have the concept of a User.
    """
    username = StringType(max_length=30, required=True)
    password = StringType(max_length=128)

    is_active = BooleanType(default=False)
    last_login = LongType(default=curtime)
    date_joined = LongType(default=curtime)

    username_regex = re.compile('^[A-Za-z0-9._]+$')
    username_min_length = 2

    class Options:
        roles = {
            'owner': blacklist('password', 'is_active'),
        }

    def __unicode__(self):
        return u'%s' % (self.username)

    def set_password(self, raw_passwd):
        """Generates bcrypt hash and salt for storing a user's password. With
        bcrypt, the salt is kind of redundant, but this format stays friendly
        to other algorithms.
        """
        (algorithm, salt, digest) = auth.gen_hexdigest(raw_passwd)
        self.password = auth.build_passwd_line(algorithm, salt, digest)

    def check_password(self, raw_password):
        """Compares raw_password to password stored for user. Updates
        self.last_login on success.
        """
        algorithm, salt, hash = auth.split_passwd_line(self.password)
        (_, _, user_hash) = auth.gen_hexdigest(raw_password,
                                               algorithm=algorithm, salt=salt)
        if hash == user_hash:
            self.last_login = curtime()
            return True
        else:
            return False

    @classmethod
    def create_user(cls, username, password, email=str()):
        """Creates a user document with given username and password
        and saves it.

        Validation occurs only for email argument. It makes no assumptions
        about password format.
        """
        now = curtime()

        username = username.lower()
        email = email.strip()
        email = email.lower()

        # Username must pass valid character range check.
        if not cls.username_regex.match(username):
            warning = 'Username failed character validation - username_regex'
            raise ValueError(warning)

        # Caller should handle validation exceptions
        cls.validate_class_partial(dict(email=email))

        user = cls(username=username, email=email, date_joined=now)
        user.set_password(password)
        return user


###
### UserProfile
###

class UserProfile(Model, OwnedModelMixin, StreamedModelMixin):
    """The basic things a user profile tends to carry. Isolated in separate
    class to keep separate from private data.
    """
    # Provided by OwnedModelMixin
    #owner_id = ObjectIdField(required=True)
    #owner_username = StringField(max_length=30, required=True)

    # streamable # provided by StreamedModelMixin now
    #created_at = MillisecondField()
    #updated_at = MillisecondField()

    # identity info
    name = StringType(max_length=255)
    email = EmailType(max_length=100)
    website = URLType(max_length=255)
    bio = StringType(max_length=100)
    location_text = StringType(max_length=100)
    avatar_url = URLType(max_length=255)

    class Options:
        roles = {
            'owner': blacklist('owner_id'),
        }

    def __init__(self, *args, **kwargs):
        super(UserProfile, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return u'%s' % (self.name)

########NEW FILE########
__FILENAME__ = base
from brubeck.request_handling import FourOhFourException

class AbstractQueryset(object):
    """The design of the `AbstractQueryset` attempts to map RESTful calls
    directly to CRUD calls. It also attempts to be compatible with a single
    item of a list of items, handling multiple statuses gracefully if
    necessary.

    The querysets then must allow for calls to perform typical CRUD operations
    on individual items or a list of items.

    By nature of being dependent on complete data models or ids, the system
    suggests users follow a key-value methodology. Brubeck believes this is
    what we scale into over time and should just build to this model from the
    start.

    Implementing the details of particular databases is then to implement the
    `create_one`, `create_many`, ..., for all the CRUD operations. MySQL,
    Mongo, Redis, etc should be easy to implement while providing everything
    necessary for a proper REST API.
    """

    MSG_OK = 'OK'
    MSG_UPDATED = 'Updated'
    MSG_CREATED = 'Created'
    MSG_NOTFOUND = 'Not Found'
    MSG_FAILED = 'Failed'

    def __init__(self, db_conn=None, api_id='id'):
        self.db_conn = db_conn
        self.api_id = api_id

    ###
    ### CRUD Operations
    ###

    ### Section TODO:
    ### * Pagination
    ### * Hook in authentication
    ### * Key filtering (owner / public)
    ### * Make model instantiation an option

    def create(self, shields):
        """Commits a list of new shields to the database
        """
        if isinstance(shields, list):
            return self.create_many(shields)
        else:
            return self.create_one(shields)

    def read(self, ids):
        """Returns a list of items that match ids
        """
        if not ids:
            return self.read_all()
        elif isinstance(ids, list):
            return self.read_many(ids)
        else:
            return self.read_one(ids)

    def update(self, shields):
        if isinstance(shields, list):
            return self.update_many(shields)
        else:
            return self.update_one(shields)

    def destroy(self, item_ids):
        """ Removes items from the datastore
        """
        if isinstance(item_ids, list):
            return self.destroy_many(item_ids)
        else:
            return self.destroy_one(item_ids)

    ###
    ### CRUD Implementations
    ###

    ### Create Functions

    def create_one(self, shield):
        raise NotImplementedError

    def create_many(self, shields):
        raise NotImplementedError

    ### Read Functions

    def read_all(self):
        """Returns a list of objects in the db
        """
        raise NotImplementedError

    def read_one(self, iid):
        """Returns a single item from the db
        """
        raise NotImplementedError

    def read_many(self, ids):
        """Returns a list of objects matching ids from the db
        """
        raise NotImplementedError

    ### Update Functions

    def update_one(self, shield):
        raise NotImplementedError

    def update_many(self, shields):
        raise NotImplementedError

    ### Destroy Functions

    def destroy_one(self, iid):
        raise NotImplementedError

    def destroy_many(self, ids):
        raise NotImplementedError


########NEW FILE########
__FILENAME__ = dict
from brubeck.queryset.base import AbstractQueryset
from schematics.serialize import to_python

class DictQueryset(AbstractQueryset):
    """This class exists as an example of how one could implement a Queryset.
    This model is an in-memory dictionary and uses the model's id as the key.

    The data stored is the result of calling `to_python()` on the model.
    """
    def __init__(self, **kw):
        """Set the db_conn to a dictionary.
        """
        super(DictQueryset, self).__init__(db_conn=dict(), **kw)

    ### Create Functions

    def create_one(self, shield):
        if shield.id in self.db_conn:
            status = self.MSG_UPDATED
        else:
            status = self.MSG_CREATED

        shield_key = str(getattr(shield, self.api_id))
        self.db_conn[shield_key] = to_python(shield)
        return (status, shield)

    def create_many(self, shields):
        statuses = [self.create_one(shield) for shield in shields]
        return statuses

    ### Read Functions

    def read_all(self):
        return [(self.MSG_OK, datum) for datum in self.db_conn.values()]


    def read_one(self, iid):
        iid = str(iid)  # TODO Should be cleaner
        if iid in self.db_conn:
            return (self.MSG_OK, self.db_conn[iid])
        else:
            return (self.MSG_FAILED, iid)

    def read_many(self, ids):
        return [self.read_one(iid) for iid in ids]

    ### Update Functions
    def update_one(self, shield):
        shield_key = str(getattr(shield, self.api_id))
        self.db_conn[shield_key] = to_python(shield)
        return (self.MSG_UPDATED, shield)

    def update_many(self, shields):
        statuses = [self.update_one(shield) for shield in shields]
        return statuses

    ### Destroy Functions

    def destroy_one(self, item_id):
        try:
            datum = self.db_conn[item_id]
            del self.db_conn[item_id]
        except KeyError:
            raise FourOhFourException
        return (self.MSG_UPDATED, datum)

    def destroy_many(self, ids):
        statuses = [self.destroy_one(iid) for iid in ids]
        return statuses


########NEW FILE########
__FILENAME__ = redis
from brubeck.queryset.base import AbstractQueryset
from itertools import imap
import ujson as json
import zlib
try:
    import redis
except ImportError:
    pass

class RedisQueryset(AbstractQueryset):
    """This class uses redis to store the DictShield after 
    calling it's `to_json()` method. Upon reading from the Redis
    store, the object is deserialized using json.loads().

    Redis connection uses the redis-py api located here:
    https://github.com/andymccurdy/redis-py
    """
    # TODO: - catch connection exceptions?
    #       - set Redis EXPIRE and self.expires
    #       - confirm that the correct status is being returned in 
    #         each circumstance
    def __init__(self, compress=False, compress_level=1, **kw):
        """The Redis connection wiil be passed in **kw and is used below
        as self.db_conn.
        """
        super(RedisQueryset, self).__init__(**kw)
        self.compress = compress
        self.compress_level = compress_level
        
    def _setvalue(self, shield):
        if self.compress:
            return zlib.compress(shield.to_json(), self.compress_level)
        return shield.to_json()

    def _readvalue(self, value):
        if self.compress:
            try:
                compressed_value = zlib.decompress(value)
                return json.loads(zlib.decompress(value))
            except Exception as e:
                # value is 0 or None from a Redis return value
                return value
        if value:
            return json.loads(value)
        return None

    def _message_factory(self, fail_status, success_status):
        """A Redis command often returns some value or 0 after the
        operation has returned.
        """
        return lambda x: success_status if x else fail_status

    ### Create Functions

    def create_one(self, shield):
        shield_value = self._setvalue(shield)
        shield_key = str(getattr(shield, self.api_id))        
        result = self.db_conn.hset(self.api_id, shield_key, shield_value)
        if result:
            return (self.MSG_CREATED, shield)
        return (self.MSG_UPDATED, shield)

    def create_many(self, shields):
        message_handler = self._message_factory(self.MSG_UPDATED, self.MSG_CREATED)
        pipe = self.db_conn.pipeline()
        for shield in shields:
            pipe.hset(self.api_id, str(getattr(shield, self.api_id)), self._setvalue(shield))
        results = zip(imap(message_handler, pipe.execute()), shields)
        pipe.reset()
        return results
        
    ### Read Functions

    def read_all(self):
        return [(self.MSG_OK, self._readvalue(datum)) for datum in self.db_conn.hvals(self.api_id)]

    def read_one(self, shield_id):
        result = self.db_conn.hget(self.api_id, shield_id)
        if result:
            return (self.MSG_OK, self._readvalue(result))
        return (self.MSG_FAILED, shield_id)

    def read_many(self, shield_ids):
        message_handler = self._message_factory(self.MSG_FAILED, self.MSG_OK)
        pipe = self.db_conn.pipeline()
        for shield_id in shield_ids:
            pipe.hget(self.api_id, str(shield_id))
        results = pipe.execute()
        pipe.reset()
        return zip(imap(message_handler, results), map(self._readvalue, results))

    ### Update Functions

    def update_one(self, shield):
        shield_key = str(getattr(shield, self.api_id))
        message_handler = self._message_factory(self.MSG_UPDATED, self.MSG_CREATED)
        status = message_handler(self.db_conn.hset(self.api_id, shield_key, self._setvalue(shield)))
        return (status, shield)

    def update_many(self, shields):
        message_handler = self._message_factory(self.MSG_UPDATED, self.MSG_CREATED)
        pipe = self.db_conn.pipeline()
        for shield in shields:
            pipe.hset(self.api_id, str(getattr(shield, self.api_id)), self._setvalue(shield))
        results = pipe.execute()
        pipe.reset()
        return zip(imap(message_handler, results), shields)

    ### Destroy Functions

    def destroy_one(self, shield_id):
        pipe = self.db_conn.pipeline()
        pipe.hget(self.api_id, shield_id)
        pipe.hdel(self.api_id, shield_id)
        result = pipe.execute()
        pipe.reset()
        if result[1]:
            return (self.MSG_UPDATED, self._readvalue(result[0]))
        return self.MSG_NOTFOUND

    def destroy_many(self, ids):
        # TODO: how to handle missing fields, currently returning self.MSG_FAILED
        message_handler = self._message_factory(self.MSG_FAILED, self.MSG_UPDATED)
        pipe = self.db_conn.pipeline()
        for _id in ids:
            pipe.hget(self.api_id, _id)
        values_results = pipe.execute()
        for _id in ids:
            pipe.hdel(self.api_id, _id)
        delete_results = pipe.execute()
        pipe.reset()
        return zip(imap(message_handler, delete_results), map(self._readvalue, values_results))


########NEW FILE########
__FILENAME__ = request
import cgi
import json
import Cookie
import logging
import urlparse
import re

def parse_netstring(ns):
    length, rest = ns.split(':', 1)
    length = int(length)
    assert rest[length] == ',', "Netstring did not end in ','"
    return rest[:length], rest[length + 1:]

def to_bytes(data, enc='utf8'):
    """Convert anything to bytes
    """
    return data.encode(enc) if isinstance(data, unicode) else bytes(data)


def to_unicode(s, enc='utf8'):
    """Convert anything to unicode
    """
    return s if isinstance(s, unicode) else unicode(str(s), encoding=enc)


class Request(object):
    """Word.
    """
    def __init__(self, sender, conn_id, path, headers, body, url, *args, **kwargs):
        self.sender = sender
        self.path = path
        self.conn_id = conn_id
        self.headers = headers
        self.body = body
        self.url_parts = urlparse.urlsplit(url) if isinstance(url, basestring) else url

        if self.method == 'JSON':
            self.data = json.loads(body)
        else:
            self.data = {}

        ### populate arguments with QUERY string
        self.arguments = {}
        if 'QUERY' in self.headers:
            query = self.headers['QUERY']
            arguments = cgi.parse_qs(query.encode("utf-8"))
            for name, values in arguments.iteritems():
                values = [v for v in values if v]
                if values:
                    self.arguments[name] = values

        ### handle data, multipart or not
        if self.method in ("POST", "PUT") and self.content_type:
            form_encoding = "application/x-www-form-urlencoded"
            if self.content_type.startswith(form_encoding):
                arguments = cgi.parse_qs(self.body)
                for name, values in arguments.iteritems():
                    values = [v for v in values if v]
                    if values:
                        self.arguments.setdefault(name, []).extend(values)
            # Not ready for this, but soon
            elif self.content_type.startswith("multipart/form-data"):
                fields = self.content_type.split(";")
                for field in fields:
                    k, sep, v = field.strip().partition("=")
                    if k == "boundary" and v:
                        self.arguments = {}
                        self.files = {}
                        self._parse_mime_body(v, self.body, self.arguments,
                                              self.files)
                        break
                else:
                    logging.warning("Invalid multipart/form-data")

    def _parse_mime_body(self, boundary, data, arguments, files):
        if boundary.startswith('"') and boundary.endswith('"'):
            boundary = boundary[1:-1]
        if data.endswith("\r\n"):
            footer_length = len(boundary) + 6 
        else:
            footer_length = len(boundary) + 4
        data = str(data)
        parts = data[:-footer_length].split("--" + str(boundary) + "\r\n")
        for part in parts:
            if not part:
                continue
            eoh = part.find("\r\n\r\n")
            if eoh == -1: 
                logging.warning("multipart/form-data missing headers")
                continue
            #headers = HTTPHeaders.parse(part[:eoh].decode("utf-8"))
            header_string = part[:eoh].decode("utf-8")
            headers = dict()
            last_key = ''
            for line in header_string.splitlines():
                if line[0].isspace():
                    # continuation of a multi-line header
                    new_part = ' ' + line.lstrip()
                    headers[last_key] += new_part
                else:
                    name, value = line.split(":", 1)
                    last_key = "-".join([w.capitalize() for w in name.split("-")])
                    headers[name] = value.strip()
    
            disp_header = headers.get("Content-Disposition", "") 
            disposition, disp_params = self._parse_header(disp_header)
            if disposition != "form-data" or not part.endswith("\r\n"):
                logging.warning("Invalid multipart/form-data")
                continue
            value = part[eoh + 4:-2]
            if not disp_params.get("name"):
                logging.warning("multipart/form-data value missing name")
                continue
            name = disp_params["name"]
            if disp_params.get("filename"):
                ctype = headers.get("Content-Type", "application/unknown")
                files.setdefault(name, []).append(dict(
                    filename=disp_params["filename"], body=value,
                    content_type=ctype))
            else:
                arguments.setdefault(name, []).append(value)

    def _parseparam(self, s):
        while s[:1] == ';':
            s = s[1:]
            end = s.find(';')
            while end > 0 and (s.count('"', 0, end) - s.count('\\"', 0, end)) % 2:
                end = s.find(';', end + 1)
            if end < 0:
                end = len(s)
            f = s[:end]
            yield f.strip()
            s = s[end:]

    def _parse_header(self, line):
        """Parse a Content-type like header.
            
        Return the main content-type and a dictionary of options.
        """
        parts = self._parseparam(';' + line)
        key = parts.next()
        pdict = {}
        for p in parts:
            i = p.find('=')
            if i >= 0:
                name = p[:i].strip().lower()
                value = p[i + 1:].strip()
                if len(value) >= 2 and value[0] == value[-1] == '"':
                    value = value[1:-1]
                    value = value.replace('\\\\', '\\').replace('\\"', '"')
                pdict[name] = value
        return key, pdict    

    @property
    def method(self):
        return self.headers.get('METHOD')

    @property
    def content_type(self):
        return self.headers.get("content-type")

    @property
    def version(self):
        return self.headers.get('VERSION')

    @property
    def remote_addr(self):
        return self.headers.get('x-forwarded-for')

    @property
    def cookies(self):
        """Lazy generation of cookies from request headers."""
        if not hasattr(self, "_cookies"):
            self._cookies = Cookie.SimpleCookie()
            if "cookie" in self.headers:
                try:
                    cookies = self.headers['cookie']
                    self._cookies.load(to_bytes(cookies))
                except Exception, e:
                    logging.error('Failed to load cookies')
                    self.clear_all_cookies()
        return self._cookies

    @property
    def url(self):
        return self.url_parts.geturl()

    @staticmethod
    def parse_msg(msg):
        """Static method for constructing a Request instance out of a
        message read straight off a zmq socket.
        """
        sender, conn_id, path, rest = msg.split(' ', 3)
        headers, rest = parse_netstring(rest)
        body, _ = parse_netstring(rest)
        headers = json.loads(headers)
        # construct url from request
        scheme = headers.get('URL_SCHEME', 'http')
        netloc = headers.get('host')
        path = headers.get('PATH')
        query = headers.get('QUERY')
        url = urlparse.SplitResult(scheme, netloc, path, query, None)
        r = Request(sender, conn_id, path, headers, body, url)
        r.is_wsgi = False
        return r

    @staticmethod
    def parse_wsgi_request(environ):
        """Static method for constructing Request instance out of environ
        dict from wsgi server."""
        conn_id = None
        sender = "WSGI_server"
        path = environ['PATH_INFO']
        body = ""
        if "CONTENT_LENGTH" in environ and environ["CONTENT_LENGTH"]:
            body = environ["wsgi.input"].read(int(environ['CONTENT_LENGTH']))
            del environ["CONTENT_LENGTH"]
            del environ["wsgi.input"]
        #setting headers to environ dict with no manipulation
        headers = environ
        # normalize request dict
        if 'REQUEST_METHOD' in headers:
            headers['METHOD'] = headers['REQUEST_METHOD']
        if 'QUERY_STRING' in headers:
            headers['QUERY'] = headers['QUERY_STRING']
        if 'CONTENT_TYPE' in headers:
            headers['content-type'] = headers['CONTENT_TYPE']
        headers['version'] = 1.1  #TODO: hardcoded!
        if 'HTTP_COOKIE' in headers:
            headers['cookie'] = headers['HTTP_COOKIE']
        if 'HTTP_CONNECTION' in headers:
            headers['connection'] = headers['HTTP_CONNECTION']
        # construct url from request
        scheme = headers['wsgi.url_scheme']
        netloc = headers.get('HTTP_HOST')
        if not netloc:
            netloc = headers['SERVER_NAME']
            port = headers['SERVER_PORT']
            if ((scheme == 'https' and port != '443') or
                (scheme == 'http' and port != '80')):
                netloc += ':' + port
        path = headers.get('SCRIPT_NAME', '')
        path += headers.get('PATH_INFO', '')
        query = headers.get('QUERY_STRING', None)
        url = urlparse.SplitResult(scheme, netloc, path, query, None)
        r = Request(sender, conn_id, path, headers, body, url)
        r.is_wsgi = True
        return r

    def is_disconnect(self):
        if self.headers.get('METHOD') == 'JSON':
            logging.error('DISCONNECT')
            return self.data.get('type') == 'disconnect'

    def should_close(self):
        """Determines if Request data matches criteria for closing request"""
        if self.headers.get('connection') == 'close':
            return True
        elif self.headers.get('VERSION') == 'HTTP/1.0':
            return True
        else:
            return False

    def get_arguments(self, name, strip=True):
        """Returns a list of the arguments with the given name. If the argument
        is not present, returns a None. The returned values are always unicode.
        """
        values = self.arguments.get(name, None)
        if values is None:
            return None

        # Get the stripper ready
        if strip:
            stripper = lambda v: v.strip()
        else:
            stripper = lambda v: v

        def clean_value(v):
            v = re.sub(r"[\x00-\x08\x0e-\x1f]", " ", v)
            v = to_unicode(v)
            v = stripper(v)
            return v

        values = [clean_value(v) for v in values]
        return values

    def get_argument(self, name, default=None, strip=True):
        """Returns the value of the argument with the given name.

        If the argument appears in the url more than once, we return the
        last value.
        """
        args = self.get_arguments(name, strip=strip)
        if not args:
            return default
        return args[-1]

########NEW FILE########
__FILENAME__ = request_handling
#!/usr/bin/env python


"""Brubeck is a coroutine oriented zmq message handling framework. I learn by
doing and this code base represents where my mind has wandered with regard to
concurrency.

If you are building a message handling system you should import this class
before anything else to guarantee the eventlet code is run first.

See github.com/j2labs/brubeck for more information.
"""

### Attempt to setup gevent
try:
    from gevent import monkey
    monkey.patch_all()
    from gevent import pool

    coro_pool = pool.Pool

    def coro_spawn(function, app, message, *a, **kw):
        app.pool.spawn(function, app, message, *a, **kw)

    CORO_LIBRARY = 'gevent'

### Fallback to eventlet
except ImportError:
    try:
        import eventlet
        eventlet.patcher.monkey_patch(all=True)

        coro_pool = eventlet.GreenPool

        def coro_spawn(function, app, message, *a, **kw):
            app.pool.spawn_n(function, app, message, *a, **kw)

        CORO_LIBRARY = 'eventlet'

    except ImportError:
        raise EnvironmentError('You need to install eventlet or gevent')


from . import version

import re
import time
import logging
import inspect
import Cookie
import base64
import hmac
import cPickle as pickle
from itertools import chain
import os, sys
from request import Request, to_bytes, to_unicode

from schematics.serialize import for_jsonschema, from_jsonschema

import ujson as json

###
### Common helpers
###

HTTP_METHODS = ['get', 'post', 'put', 'delete',
                'head', 'options', 'trace', 'connect']

HTTP_FORMAT = "HTTP/1.1 %(code)s %(status)s\r\n%(headers)s\r\n\r\n%(body)s"


class FourOhFourException(Exception):
    pass


###
### Result Processing
###

def render(body, status_code, status_msg, headers):
    payload = {
        'body': body,
        'status_code': status_code,
        'status_msg': status_msg,
        'headers': headers,
    }
    return payload


def http_response(body, code, status, headers):
    """Renders arguments into an HTTP response.
    """
    payload = {'code': code, 'status': status, 'body': body}
    content_length = 0
    if body is not None:
        content_length = len(to_bytes(body))

    headers['Content-Length'] = content_length
    payload['headers'] = "\r\n".join('%s: %s' % (k, v)
                                     for k, v in headers.items())

    return HTTP_FORMAT % payload

def _lscmp(a, b):
    """Compares two strings in a cryptographically safe way
    """
    return not sum(0 if x == y else 1
                   for x, y in zip(a, b)) and len(a) == len(b)


###
### Me not *take* cookies, me *eat* the cookies.
###

def cookie_encode(data, key):
    """Encode and sign a pickle-able object. Return a (byte) string
    """
    msg = base64.b64encode(pickle.dumps(data, -1))
    sig = base64.b64encode(hmac.new(key, msg).digest())
    return to_bytes('!') + sig + to_bytes('?') + msg


def cookie_decode(data, key):
    ''' Verify and decode an encoded string. Return an object or None.'''
    data = to_bytes(data)
    if cookie_is_encoded(data):
        sig, msg = data.split(to_bytes('?'), 1)
        if _lscmp(sig[1:], base64.b64encode(hmac.new(key, msg).digest())):
            return pickle.loads(base64.b64decode(msg))
    return None


def cookie_is_encoded(data):
    ''' Return True if the argument looks like a encoded cookie.'''
    return bool(data.startswith(to_bytes('!')) and to_bytes('?') in data)


###
### Message handling
###

class MessageHandler(object):
    """The base class for request handling. It's functionality consists
    primarily of a payload system and a way to store some state for
    the duration of processing the message.

    Mixins are provided in Brubeck's modules for extending these handlers.
    Mixins provide a simple way to add functions to a MessageHandler that are
    unique to the message our handler is designed for. Mix in logic as you
    realize you need it. Or rip it out. Keep your handlers lean.

    Two callbacks are offered for state preparation.

    The `initialize` function allows users to add steps to object
    initialization. A mixin, however, should never use this. You could hook
    the request handler up to a database connection pool, for example.

    The `prepare` function is called just before any decorators are called.
    The idea here is to give Mixin creators a chance to build decorators that
    depend on post-initialization processing to have taken place. You could use
    that database connection we created in `initialize` to check the username
    and password from a user.
    """
    _STATUS_CODE = 'status_code'
    _STATUS_MSG = 'status_msg'
    _TIMESTAMP = 'timestamp'
    _DEFAULT_STATUS = -1  # default to error, earn success
    _SUCCESS_CODE = 0
    _AUTH_FAILURE = -2
    _SERVER_ERROR = -5

    _response_codes = {
        0: 'OK',
        -1: 'Bad request',
        -2: 'Authentication failed',
        -3: 'Not found',
        -4: 'Method not allowed',
        -5: 'Server error',
    }

    def __init__(self, application, message, *args, **kwargs):
        """A MessageHandler is called at two major points, with regard to the
        eventlet scheduler. __init__ is the first point, which is responsible
        for bootstrapping the state of a single handler.

        __call__ is the second major point.
        """
        self.application = application
        self.message = message
        self._payload = dict()
        self._finished = False
        self.set_status(self._DEFAULT_STATUS)
        self.set_timestamp(int(time.time() * 1000))
        self.initialize()

    def initialize(self):
        """Hook for subclass. Implementers should be aware that this class's
        __init__ calls initialize.
        """
        pass

    def prepare(self):
        """Called before the message handling method. Code here runs prior to
        decorators, so any setup required for decorators to work should happen
        here.
        """
        pass

    def on_finish(self):
        """Called after the message handling method. Counterpart to prepare
        """
        pass

    @property
    def db_conn(self):
        """Short hand to put database connection in easy reach of handlers
        """
        return self.application.db_conn

    @property
    def supported_methods(self):
        """List all the HTTP methods you have defined.
        """
        supported_methods = []
        for mef in HTTP_METHODS:
            if callable(getattr(self, mef, False)):
                supported_methods.append(mef)
        return supported_methods

    def unsupported(self):
        """Called anytime an unsupported request is made.
        """
        return self.render_error(-1)

    def error(self, err):
        return self.unsupported()

    def add_to_payload(self, key, value):
        """Upserts key-value pair into payload.
        """
        self._payload[key] = value

    def clear_payload(self):
        """Resets the payload but preserves the current status_code.
        """
        status_code = self.status_code
        self._payload = dict()
        self.set_status(status_code)
        self.initialize()

    def set_status(self, status_code, status_msg=None, extra_txt=None):
        """Sets the status code of the payload to <status_code> and sets
        status msg to the the relevant msg as defined in _response_codes.
        """
        if status_msg is None:
            status_msg = self._response_codes.get(status_code,
                                                  str(status_code))
        if extra_txt:
            status_msg = '%s - %s' % (status_msg, extra_txt)
        self.add_to_payload(self._STATUS_CODE, status_code)
        self.add_to_payload(self._STATUS_MSG, status_msg)

    @property
    def status_code(self):
        return self._payload[self._STATUS_CODE]

    @property
    def status_msg(self):
        return self._payload[self._STATUS_MSG]

    @property
    def current_time(self):
        return self._payload[self._TIMESTAMP]

    def set_timestamp(self, timestamp):
        """Sets the timestamp to given timestamp.
        """
        self.add_to_payload(self._TIMESTAMP, timestamp)
        self.timestamp = timestamp

    def render(self, status_code=None, hide_status=False, **kwargs):
        """Renders entire payload as json dump. Subclass and overwrite this
        function if a different output format is needed. See WebMessageHandler
        as an example.
        """
        if not status_code:
            status_code = self.status_code
        self.set_status(status_code)
        rendered = json.dumps(self._payload)
        return rendered

    def render_error(self, status_code, error_handler=None, **kwargs):
        """Clears the payload before rendering the error status.
        Takes a callable to perform customization before rendering the output.
        """
        self.clear_payload()
        if error_handler:
            error_handler()
        self._finished = True
        return self.render(status_code=status_code)

    def __call__(self):
        """This function handles mapping the request type to a function on
        the request handler.

        It requires a method attribute to indicate which function on the
        handler should be called. If that function is not supported, call the
        handlers unsupported function.

        In the event that an error has already occurred, _finished will be
        set to true before this function call indicating we should render
        the handler and nothing else.

        In all cases, generating a response for mongrel2 is attempted.
        """
        try:
            self.prepare()
            if not self._finished:
                mef = self.message.method.lower()  # M-E-T-H-O-D man!

                # Find function mapped to method on self
                if mef in HTTP_METHODS:
                    fun = getattr(self, mef, self.unsupported)
                else:
                    fun = self.unsupported

                # Call the function we settled on
                try:
                    if not hasattr(self, '_url_args') or self._url_args is None:
                        self._url_args = []

                    if isinstance(self._url_args, dict):
                        ### if the value was optional and not included, filter it
                        ### out so the functions default takes priority
                        kwargs = dict((k, v)
                                      for k, v in self._url_args.items() if v)
                        rendered = fun(**kwargs)
                    else:
                        rendered = fun(*self._url_args)

                    if rendered is None:
                        logging.debug('Handler had no return value: %s' % fun)
                        return ''
                except Exception, e:
                    logging.error(e, exc_info=True)
                    rendered = self.error(e)

                self._finished = True
                return rendered
            else:
                return self.render()
        finally:
            self.on_finish()


class WebMessageHandler(MessageHandler):
    """A base class for common functionality in a request handler.

    Tornado's design inspired this design.
    """
    _DEFAULT_STATUS = 500  # default to server error
    _SUCCESS_CODE = 200
    _UPDATED_CODE = 200
    _CREATED_CODE = 201
    _MULTI_CODE = 207
    _FAILED_CODE = 400
    _AUTH_FAILURE = 401
    _FORBIDDEN = 403
    _NOT_FOUND = 404
    _NOT_ALLOWED = 405
    _SERVER_ERROR = 500

    _response_codes = {
        200: 'OK',
        400: 'Bad request',
        401: 'Authentication failed',
        403: 'Forbidden',
        404: 'Not found',
        405: 'Method not allowed',
        500: 'Server error',
    }

    ###
    ### Payload extension
    ###

    _HEADERS = 'headers'

    def initialize(self):
        """WebMessageHandler extends the payload for body and headers. It
        also provides both fields as properties to mask storage in payload
        """
        self.body = ''
        self.headers = dict()

    def set_body(self, body, headers=None, status_code=_SUCCESS_CODE):
        """
        """
        self.body = body
        self.set_status(status_code)
        if headers is not None:
            self.headers = headers

    ###
    ### Supported HTTP request methods are mapped to these functions
    ###

    def options(self, *args, **kwargs):
        """Default to allowing all of the methods you have defined and public
        """
        self.headers["Access-Control-Allow-Methods"] = self.supported_methods
        self.set_status(200)
        return self.render()

    def unsupported(self, *args, **kwargs):
        def allow_header():
            methods = str.join(', ', map(str.upper, self.supported_methods))
            self.headers['Allow'] = methods
        return self.render_error(self._NOT_ALLOWED, error_handler=allow_header)

    def error(self, err):
        self.render_error(self._SERVER_ERROR)

    def redirect(self, url):
        """Clears the payload before rendering the error status
        """
        logging.debug('Redirecting to url: %s' % url)
        self.clear_payload()
        self._finished = True
        msg = 'Page has moved to %s' % url
        self.set_status(302, status_msg=msg)
        self.headers['Location'] = '%s' % url
        return self.render()

    ###
    ### Helpers for accessing request variables
    ###

    def get_argument(self, name, default=None, strip=True):
        """Returns the value of the argument with the given name.

        If the argument appears in the url more than once, we return the
        last value.
        """
        return self.message.get_argument(name, default=default, strip=strip)

    def get_arguments(self, name, strip=True):
        """Returns a list of the arguments with the given name.
        """
        return self.message.get_arguments(name, strip=strip)

    ###
    ### Cookies
    ###

    ### Incoming cookie functions

    def get_cookie(self, key, default=None, secret=None):
        """Retrieve a cookie from message, if present, else fallback to
        `default` keyword. Accepts a secret key to validate signed cookies.
        """
        value = default
        if key in self.message.cookies:
            value = self.message.cookies[key].value
        if secret and value:
            dec = cookie_decode(value, secret)
            return dec[1] if dec and dec[0] == key else None
        return value

    ### Outgoing cookie functions

    @property
    def cookies(self):
        """Lazy creation of response cookies."""
        if not hasattr(self, "_cookies"):
            self._cookies = Cookie.SimpleCookie()
        return self._cookies

    def set_cookie(self, key, value, secret=None, **kwargs):
        """Add a cookie or overwrite an old one. If the `secret` parameter is
        set, create a `Signed Cookie` (described below).

        `key`: the name of the cookie.
        `value`: the value of the cookie.
        `secret`: required for signed cookies.

        params passed to as keywords:
          `max_age`: maximum age in seconds.
          `expires`: a datetime object or UNIX timestamp.
          `domain`: the domain that is allowed to read the cookie.
          `path`: limits the cookie to a given path

        If neither `expires` nor `max_age` are set (default), the cookie
        lasts only as long as the browser is not closed.
        """
        if secret:
            value = cookie_encode((key, value), secret)
        elif not isinstance(value, basestring):
            raise TypeError('Secret missing for non-string Cookie.')

        # Set cookie value
        self.cookies[key] = value

        # handle keywords
        for k, v in kwargs.iteritems():
            self.cookies[key][k.replace('_', '-')] = v

    def delete_cookie(self, key, **kwargs):
        """Delete a cookie. Be sure to use the same `domain` and `path`
        parameters as used to create the cookie.
        """
        kwargs['max_age'] = -1
        kwargs['expires'] = 0
        self.set_cookie(key, '', **kwargs)

    def delete_cookies(self):
        """Deletes every cookie received from the user.
        """
        for key in self.message.cookies.iterkeys():
            self.delete_cookie(key)

    ###
    ### Output generation
    ###

    def convert_cookies(self):
        """ Resolves cookies into multiline values.
        """
        cookie_vals = [c.OutputString() for c in self.cookies.values()]
        if len(cookie_vals) > 0:
            cookie_str = '\nSet-Cookie: '.join(cookie_vals)
            self.headers['Set-Cookie'] = cookie_str

    def render(self, status_code=None, http_200=False, **kwargs):
        """Renders payload and prepares the payload for a successful HTTP
        response.

        Allows forcing HTTP status to be 200 regardless of request status
        for cases where payload contains status information.
        """
        if status_code:
            self.set_status(status_code)

        # Some API's send error messages in the payload rather than over
        # HTTP. Not necessarily ideal, but supported.
        status_code = self.status_code
        if http_200:
            status_code = 200

        self.convert_cookies()

        response = render(self.body, status_code, self.status_msg, self.headers)

        logging.info('%s %s %s (%s)' % (status_code, self.message.method,
                                        self.message.path,
                                        self.message.remote_addr))
        return response


class JSONMessageHandler(WebMessageHandler):
    """This class is virtually the same as the WebMessageHandler with a slight
    change to how payloads are handled to make them more appropriate for
    representing JSON transmissions.

    The `hide_status` flag is used to reduce the payload down to just the data.
    """
    def render(self, status_code=None, hide_status=False, **kwargs):
        if status_code:
            self.set_status(status_code)

        self.convert_cookies()

        self.headers['Content-Type'] = 'application/json'

        if hide_status and 'data' in self._payload:
            body = json.dumps(self._payload['data'])
        else:
            body = json.dumps(self._payload)

        response = render(body, self.status_code, self.status_msg,
                          self.headers)

        logging.info('%s %s %s (%s)' % (self.status_code, self.message.method,
                                        self.message.path,
                                        self.message.remote_addr))
        return response


class JsonSchemaMessageHandler(WebMessageHandler):
    manifest = {}

    @classmethod
    def add_model(self, model):
        self.manifest[model.__name__.lower()] = for_jsonschema(model)

    def get(self):
        self.set_body(json.dumps(self.manifest.values()))
        return self.render(status_code=200)

    def render(self, status_code=None, **kwargs):
        if status_code:
            self.set_status(status_code)

        self.convert_cookies()
        self.headers['Content-Type'] = "application/schema+json"

        response = render(self.body, status_code, self.status_msg,
                          self.headers)

        return response

###
### Application logic
###

class Brubeck(object):

    MULTIPLE_ITEM_SEP = ','

    def __init__(self, msg_conn=None, handler_tuples=None, pool=None,
                 no_handler=None, base_handler=None, template_loader=None,
                 log_level=logging.INFO, login_url=None, db_conn=None,
                 cookie_secret=None, api_base_url=None,
                 *args, **kwargs):
        """Brubeck is a class for managing connections to webservers. It
        supports Mongrel2 and WSGI while providing an asynchronous system for
        managing message handling.

        `msg_conn` should be a `connections.Connection` instance.

        `handler_tuples` is a list of two-tuples. The first item is a regex
        for matching the URL requested. The second is the class instantiated
        to handle the message.

        `pool` can be an existing coroutine pool, but one will be generated if
        one isn't provided.

        `base_handler` is a class that Brubeck can rely on for implementing
        error handling functions.

        `template_loader` is a function that builds the template loading
        environment.

        `log_level` is a log level mapping to Python's `logging` module's
        levels.

        `login_url` is the default URL for a login screen.

        `db_conn` is a database connection to be shared in this process

        `cookie_secret` is a string to use for signing secure cookies.
        """
        # All output is sent via logging
        # (while i figure out how to do a good abstraction via zmq)
        logging.basicConfig(level=log_level)

        # Log whether we're using eventlet or gevent.
        logging.info('Using coroutine library: %s' % CORO_LIBRARY)

        # Attach the web server connection
        if msg_conn is not None:
            self.msg_conn = msg_conn
        else:
            raise ValueError('No web server connection provided.')

        # Class based route lists should be handled this way.
        # It is also possible to use `add_route`, a decorator provided by a
        # brubeck instance, that can extend routing tables.
        self.handler_tuples = handler_tuples
        if self.handler_tuples is not None:
            self.init_routes(handler_tuples)

        # We can accept an existing pool or initialize a new pool
        if pool is None:
            self.pool = coro_pool()
        elif callable(pool):
            self.pool = pool()
        else:
            raise ValueError('Unable to initialize coroutine pool')

        # Set a base_handler for handling errors (eg. 404 handler)
        self.base_handler = base_handler
        if self.base_handler is None:
            self.base_handler = WebMessageHandler

        # A database connection is optional. The var name is now in place
        self.db_conn = db_conn

        # Login url is optional
        self.login_url = login_url

        # API base url is optional
        if api_base_url is None:
            self.api_base_url = '/'
        else:
            self.api_base_url = api_base_url

        # This must be set to use secure cookies
        self.cookie_secret = cookie_secret

        # Any template engine can be used. Brubeck just needs a function that
        # loads the environment without arguments.
        #
        # It then creates a function that renders templates with the given
        # environment and attaches it to self.
        if callable(template_loader):
            loaded_env = template_loader()
            if loaded_env:
                self.template_env = loaded_env

                # Create template rendering function
                def render_template(template_file, **context):
                    """Renders template using provided template environment.
                    """
                    if hasattr(self, 'template_env'):
                        t_env = self.template_env
                        template = t_env.get_template(template_file)
                        body = template.render(**context or {})
                    return body

                # Attach it to brubeck app (self)
                setattr(self, 'render_template', render_template)
            else:
                raise ValueError('template_env failed to load.')

    ###
    ### Message routing functions
    ###

    def init_routes(self, handler_tuples):
        """Loops over a list of (pattern, handler) tuples and adds them
        to the routing table.
        """
        for ht in handler_tuples:
            (pattern, kallable) = ht
            self.add_route_rule(pattern, kallable)

    def add_route_rule(self, pattern, kallable):
        """Takes a string pattern and callable and adds them to URL routing.
        The pattern should be compilable as a regular expression with `re`.
        The kallable argument should be a handler.
        """
        if not hasattr(self, '_routes'):
            self._routes = list()
        regex = re.compile(pattern, re.UNICODE)
        self._routes.append((regex, kallable))

    def add_route(self, url_pattern, method=None):
        """A decorator to facilitate building routes wth callables. Can be
        used as alternative method for constructing routing tables.
        """
        if method is None:
            method = list()
        elif not hasattr(method, '__iter__'):
            method = [method]

        def decorator(kallable):
            """Decorates a function by adding it to the routing table and
            adding code to check the HTTP Method used.
            """
            def check_method(app, msg, *args):
                """Create new method which checks the HTTP request type.
                If URL matches, but unsupported request type is used an
                unsupported error is thrown.

                def one_more_layer():
                    INCEPTION
                """
                if msg.method not in method:
                    return self.base_handler(app, msg).unsupported()
                else:
                    return kallable(app, msg, *args)

            self.add_route_rule(url_pattern, check_method)
            return check_method
        return decorator

    def route_message(self, message):
        """Factory function that instantiates a request handler based on
        path requested.

        If a class that implements `__call__` is used, the class should
        implement an `__init__` that receives two arguments: a brubeck instance
        and the message to be handled. The return value of this call is a
        callable class that is ready to be executed in a follow up coroutine.

        If a function is used (eg with the decorating routing pattern) a
        closure is created around the two arguments. The return value of this
        call is a function ready to be executed in a follow up coroutine.
        """
        handler = None
        for (regex, kallable) in self._routes:
            url_check = regex.match(message.path)

            if url_check:
                ### `None` will fail, so we have to use at least an empty list
                ### We should try to use named arguments first, and if they're
                ### not present fall back to positional arguments
                url_args = url_check.groupdict() or url_check.groups() or []

                if inspect.isclass(kallable):
                    ### Handler classes must be instantiated
                    handler = kallable(self, message)
                    ### Attach url args to handler
                    handler._url_args = url_args
                    return handler
                else:
                    ### Can't instantiate a function
                    if isinstance(url_args, dict):
                        ### if the value was optional and not included, filter
                        ### it out so the functions default takes priority
                        kwargs = dict((k, v) for k, v in url_args.items() if v)

                        handler = lambda: kallable(self, message, **kwargs)
                    else:
                        handler = lambda: kallable(self, message, *url_args)
                    return handler

        if handler is None:
            handler = self.base_handler(self, message)

        return handler

    def register_api(self, APIClass, prefix=None):
        model, model_name = APIClass.model, APIClass.model.__name__.lower()

        if not JsonSchemaMessageHandler.manifest:
            manifest_pattern = "/manifest.json"
            self.add_route_rule(manifest_pattern, JsonSchemaMessageHandler)

        if prefix is None:
            url_prefix = self.api_base_url + model_name
        else:
            url_prefix = prefix

        # TODO inspect url pattern for holes
        pattern = "/((?P<ids>[-\w\d%s]+)(/)*|$)" % self.MULTIPLE_ITEM_SEP
        api_url = ''.join([url_prefix, pattern])

        self.add_route_rule(api_url, APIClass)
        JsonSchemaMessageHandler.add_model(model)


    ###
    ### Application running functions
    ###

    def recv_forever_ever(self):
        """Helper function for starting the link between Brubeck and the
        message processing provided by `msg_conn`.
        """
        mc = self.msg_conn
        mc.recv_forever_ever(self)

    def run(self):
        """This method turns on the message handling system and puts Brubeck
        in a never ending loop waiting for messages.

        The loop is actually the eventlet scheduler. A goal of Brubeck is to
        help users avoid thinking about complex things like an event loop while
        still getting the goodness of asynchronous and nonblocking I/O.
        """
        greeting = 'Brubeck v%s online ]-----------------------------------'
        print greeting % version

        self.recv_forever_ever()

########NEW FILE########
__FILENAME__ = templating
from request_handling import WebMessageHandler


###
### Mako templates
###

def load_mako_env(template_dir, *args, **kwargs):
    """Returns a function which loads a Mako templates environment.
    """
    def loader():
        from mako.lookup import TemplateLookup
        if template_dir is not None:
            return TemplateLookup(directories=[template_dir or '.'],
                                  *args, **kwargs)
        else:
            return None
    return loader


class MakoRendering(WebMessageHandler):
    def render_template(self, template_file,
                        _status_code=WebMessageHandler._SUCCESS_CODE,
                        **context):
        body = self.application.render_template(template_file, **context or {})
        self.set_body(body, status_code=_status_code)
        return self.render()

    def render_error(self, error_code):
        return self.render_template('errors.html', _status_code=error_code,
                                    **{'error_code': error_code})


###
### Jinja2
###

def load_jinja2_env(template_dir, *args, **kwargs):
    """Returns a function that loads a jinja template environment. Uses a
    closure to provide a namespace around module loading without loading
    anything until the caller is ready.
    """
    def loader():
        from jinja2 import Environment, FileSystemLoader
        if template_dir is not None:
            return Environment(loader=FileSystemLoader(template_dir or '.'),
                               *args, **kwargs)
        else:
            return None
    return loader


class Jinja2Rendering(WebMessageHandler):
    """Jinja2Rendering is a mixin for for loading a Jinja2 rendering
    environment.

    Render success is transmitted via http 200. Rendering failures result in
    http 500 errors.
    """
    def render_template(self, template_file,
                        _status_code=WebMessageHandler._SUCCESS_CODE,
                        **context):
        """Renders payload as a jinja template
        """
        body = self.application.render_template(template_file, **context or {})
        self.set_body(body, status_code=_status_code)
        return self.render()

    def render_error(self, error_code):
        """Receives error calls and sends them through a templated renderer
        call.
        """
        return self.render_template('errors.html', _status_code=error_code,
                                    **{'error_code': error_code})


###
### Tornado
###

def load_tornado_env(template_dir, *args, **kwargs):
    """Returns a function that loads the Tornado template environment.
    """
    def loader():
        from tornado.template import Loader
        if template_dir is not None:
            return Loader(template_dir or '.', *args, **kwargs)
        else:
            return None
    return loader


class TornadoRendering(WebMessageHandler):
    """TornadoRendering is a mixin for for loading a Tornado rendering
    environment.

    Follows usual convention: 200 => success and 500 => failure

    The unusual convention of an underscore in front of a variable is used
    to avoid conflict with **context. '_status_code', for now, is a reserved
    word.
    """
    def render_template(self, template_file,
                        _status_code=WebMessageHandler._SUCCESS_CODE,
                        **context):
        """Renders payload as a tornado template
        """
        body = self.application.render_template(template_file, **context or {})
        self.set_body(body, status_code=_status_code)
        return self.render()

    def render_error(self, error_code):
        """Receives error calls and sends them through a templated renderer
        call.
        """
        return self.render_template('errors.html', _status_code=error_code,
                                    **{'error_code': error_code})

###
### Mustache
###

def load_mustache_env(template_dir, *args, **kwargs):
    """
    Returns a function that loads a mustache template environment. Uses a
    closure to provide a namespace around module loading without loading
    anything until the caller is ready.
    """
    def loader():
        import pystache

        return pystache.Renderer(search_dirs=[template_dir])

    return loader


class MustacheRendering(WebMessageHandler):
    """
    MustacheRendering is a mixin for for loading a Mustache rendering
    environment.

    Render success is transmitted via http 200. Rendering failures result in
    http 500 errors.
    """
    def render_template(self, template_file,
                        _status_code=WebMessageHandler._SUCCESS_CODE,
                        **context):
        """
        Renders payload as a mustache template
        """
        mustache_env = self.application.template_env

        template = mustache_env.load_template(template_file)
        body = mustache_env.render(template, context or {})

        self.set_body(body, status_code=_status_code)
        return self.render()

    def render_error(self, error_code):
        """Receives error calls and sends them through a templated renderer
        call.
        """
        return self.render_template('errors', _status_code=error_code,
                                    **{'error_code': error_code})

########NEW FILE########
__FILENAME__ = timekeeping
import time
from datetime import datetime
from dateutil.parser import parse

from schematics.types import LongType


###
### Main Time Function
###

def curtime():
    """This funciton is the central method for getting the current time. It
    represents the time in milliseconds and the timezone is UTC.
    """
    return long(time.time() * 1000)


###
### Converstion Helpers
###

def datestring_to_millis(ds):
    """Takes a string representing the date and converts it to milliseconds
    since epoch.
    """
    dt = parse(ds)
    return datetime_to_millis(dt)


def datetime_to_millis(dt):
    """Takes a datetime instances and converts it to milliseconds since epoch.
    """
    seconds = dt.timetuple()
    seconds_from_epoch = time.mktime(seconds)
    return seconds_from_epoch * 1000  # milliseconds


def millis_to_datetime(ms):
    """Converts milliseconds into it's datetime equivalent
    """
    seconds = ms / 1000.0
    return datetime.fromtimestamp(seconds)


###
### Neckbeard date parsing (fuzzy!)
###

def prettydate(d):
    """I <3 U, StackOverflow.

    http://stackoverflow.com/questions/410221/natural-relative-days-in-python
    """
    diff = datetime.utcnow() - d
    s = diff.seconds
    if diff.days > 7 or diff.days < 0:
        return d.strftime('%d %b %y')
    elif diff.days == 1:
        return '1 day ago'
    elif diff.days > 1:
        return '{0} days ago'.format(diff.days)
    elif s <= 1:
        return 'just now'
    elif s < 60:
        return '{0} seconds ago'.format(s)
    elif s < 120:
        return '1 minute ago'
    elif s < 3600:
        return '{0} minutes ago'.format(s / 60)
    elif s < 7200:
        return '1 hour ago'
    else:
        return '{0} hours ago'.format(s / 3600)


###
### Custom Schematics Type
###

class MillisecondType(LongType):
    """High precision time field.
    """
    def __set__(self, instance, value):
        """__set__ is overriden to allow accepting date strings as input.
        dateutil is used to parse strings into milliseconds.
        """
        if isinstance(value, (str, unicode)):
            value = datestring_to_millis(value)
        instance._data[self.field_name] = value

########NEW FILE########
__FILENAME__ = demo_auth
#!/usr/bin/env python

from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.connections import Mongrel2Connection
from brubeck.models import User
from brubeck.auth import authenticated, UserHandlingMixin
import sys
import logging

### Hardcode a user for the demo
demo_user = User.create_user('jd', 'foo')

class DemoHandler(WebMessageHandler, UserHandlingMixin):
    def get_current_user(self):
        """Attempts to load authentication credentials from a request and validate
        them. Returns an instantiated User if credentials were good.

        `get_current_user` is a callback triggered by decorating a function
        with @authenticated.
        """
        username = self.get_argument('username')
        password = self.get_argument('password')

        if demo_user.username != username:
            logging.error('Auth fail: username incorrect')
            return
        
        if not demo_user.check_password(password):
            logging.error('Auth fail: password incorrect')
            return
        
        logging.info('Access granted for user: %s' % username)
        return demo_user
    
    @authenticated
    def post(self):
        """Requires username and password."""
        self.set_body('%s logged in successfully!' % (self.current_user.username))
        return self.render()


config = {
    'msg_conn': Mongrel2Connection('tcp://127.0.0.1:9999', 'tcp://127.0.0.1:9998'),
    'handler_tuples': [(r'^/brubeck', DemoHandler)],
}

app = Brubeck(**config)
app.run()

########NEW FILE########
__FILENAME__ = demo_autoapi
#!/usr/bin/env python

"""To use this demo, try entering the following commands in a terminal:

    curl http://localhost:6767/todo/ | python -mjson.tool
    
    curl -H "content-type: application/json" -f -X POST -d '{"id": "111b4bb7-55f5-441b-ba25-c7a4fd99442c", "text": "Watch more bsg", "order": 1}' http://localhost:6767/todo/111b4bb7-55f5-441b-ba25-c7a4fd99442c/ | python -m json.tool
    
    curl -H "content-type: application/json" -f -X POST -d '{"id": "222b4bb7-55f5-441b-ba25-c7a4fd994421", "text": "Watch Blade Runner", "order": 2}' http://localhost:6767/todo/222b4bb7-55f5-441b-ba25-c7a4fd994421/ | python -m json.tool
    
    curl http://localhost:6767/todo/ | python -mjson.tool
    
    curl http://localhost:6767/todo/222b4bb7-55f5-441b-ba25-c7a4fd994421/ | python -mjson.tool
    
    curl -H "content-type: application/json" -f -X DELETE http://localhost:6767/todo/222b4bb7-55f5-441b-ba25-c7a4fd994421/ 
    
    curl http://localhost:6767/todo/ | python -mjson.tool
    
    curl -H "content-type: application/json" -f -X POST -d '[{"id": "333b4bb7-55f5-441b-ba25-c7a4fd99442c", "text": "Write more Brubeck code", "order": 3},{"id": "444b4bb7-55f5-441b-ba25-c7a4fd994421", "text": "Drink coffee", "order": 4}]' http://localhost:6767/todo/ | python -m json.tool
    
    curl http://localhost:6767/todo/ | python -mjson.tool
    
    curl -H "content-type: application/json" -f -X POST -d '{"id": "b4bb7-55f5-441b-ba25-c7a4fd994421", "text": "Watch Blade Runner", "order": 2}' http://localhost:6767/todo/222b4bb7-55f5-441b-ba25-c7a4fd994421/ | python -m json.tool
    
    curl -H "content-type: application/json" -f -X POST -d '{"id": "b4bb7-55f5-441b-ba25-c7a4fd994421", "text": "Watch Blade Runner", "order": 2}' http://localhost:6767/todo/b4bb7-55f5-441b-ba25-c7a4fd994421/ | python -m json.tool
"""

from brubeck.request_handling import Brubeck
from brubeck.autoapi import AutoAPIBase
from brubeck.queryset import DictQueryset
from brubeck.templating import Jinja2Rendering, load_jinja2_env
from brubeck.connections import Mongrel2Connection

from schematics.models import Model
from schematics.types import (UUIDType,
                              StringType,
                              BooleanType)
from schematics.serialize import wholelist


### Todo Model
class Todo(Model):
    # status fields
    id = UUIDType(auto_fill=True)
    completed = BooleanType(default=False)
    deleted = BooleanType(default=False)
    archived = BooleanType(default=False)
    title = StringType(required=True)

    class Options:
        roles = {
            'owner': wholelist(),
        }


### Todo API
class TodosAPI(AutoAPIBase):
    queries = DictQueryset()
    model = Todo
    def render(self, **kwargs):
        return super(TodosAPI, self).render(hide_status=True, **kwargs)


### Flat page handler
class TodosHandler(Jinja2Rendering):
    def get(self):
        """A list display matching the parameters of a user's dashboard. The
        parameters essentially map to the variation in how `load_listitems` is
        called.
        """
        return self.render_template('todos.html')


###
### Configuration
###

# Routing config
handler_tuples = [
    (r'^/$', TodosHandler),
]

# Application config
config = {
    'msg_conn': Mongrel2Connection('tcp://127.0.0.1:9999', 'tcp://127.0.0.1:9998'),
    'handler_tuples': handler_tuples,
    'template_loader': load_jinja2_env('./templates/autoapi'),
}

# Instantiate app instance
app = Brubeck(**config)
app.register_api(TodosAPI)
app.run()


########NEW FILE########
__FILENAME__ = demo_jinja2
#!/usr/bin/env python

from brubeck.request_handling import Brubeck
from brubeck.templating import Jinja2Rendering, load_jinja2_env
from brubeck.connections import Mongrel2Connection
import sys

class DemoHandler(Jinja2Rendering):
    def get(self):
        name = self.get_argument('name', 'dude')
        context = {
            'name': name,
        }
        return self.render_template('success.html', **context)

app = Brubeck(msg_conn=Mongrel2Connection('tcp://127.0.0.1:9999', 'tcp://127.0.0.1:9998'),
              handler_tuples=[(r'^/brubeck', DemoHandler)],
              template_loader=load_jinja2_env('./templates/jinja2'))
app.run()

########NEW FILE########
__FILENAME__ = demo_jinja2_noclasses
#! /usr/bin/env python


from brubeck.request_handling import Brubeck, render
from brubeck.connections import Mongrel2Connection
from brubeck.templating import  load_jinja2_env, Jinja2Rendering


app = Brubeck(msg_conn=Mongrel2Connection('tcp://127.0.0.1:9999',
                                          'tcp://127.0.0.1:9998'),
              template_loader=load_jinja2_env('./templates/jinja2'))


@app.add_route('^/', method=['GET', 'POST'])
def index(application, message):
    name = message.get_argument('name', 'dude')
    context = {
        'name': name,
    }
    body = application.render_template('success.html', **context)
    return render(body, 200, 'OK', {})


app.run()

########NEW FILE########
__FILENAME__ = demo_login
#!/usr/bin/env python

from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.models import User
from brubeck.auth import web_authenticated, UserHandlingMixin
from brubeck.templating import Jinja2Rendering, load_jinja2_env
from brubeck.connections import Mongrel2Connection
import sys
import logging

###
### Hardcoded authentication
###

demo_user = User.create_user('jd', 'foo')

class CustomAuthMixin(WebMessageHandler, UserHandlingMixin):
    """This Mixin provides a `get_current_user` implementation that
    validates auth against our hardcoded user: `demo_user`
    """
    def get_current_user(self):
        """Attempts to load user information from cookie. If that
        fails, it looks for credentials as arguments.

        If then attempts auth with the found credentials.
        """
        # Try loading credentials from cookie
        username = self.get_cookie('username')
        password = self.get_cookie('password')

        # Fall back to args if cookie isn't provided
        if username is None or password is None:
            username = self.get_argument('username')
            password = self.get_argument('password')

        if demo_user.username != username:
            logging.error('Auth fail: bad username')
            return
            
        if not demo_user.check_password(password):
            logging.error('Auth fail: bad password')
            return
        
        logging.debug('Access granted for user: %s' % username)
        self.set_cookie('username', username) # DEMO: Don't actually put a
        self.set_cookie('password', password) # password in a cookie...
        
        return demo_user


###
### Handlers
###

class LandingHandler(CustomAuthMixin, Jinja2Rendering):
    @web_authenticated
    def get(self):
        """Landing page. Forbids access without authentication
        """
        return self.render_template('landing.html')


class LoginHandler(CustomAuthMixin, Jinja2Rendering):
    def get(self):
        """Offers login form to user
        """
        return self.render_template('login.html')
    
    @web_authenticated
    def post(self):
        """Checks credentials with decorator and sends user authenticated
        users to the landing page.
        """
        return self.redirect('/')


class LogoutHandler(CustomAuthMixin, Jinja2Rendering):
    def get(self):
        """Clears cookie and sends user to login page
        """
        self.delete_cookies()
        return self.redirect('/login')


###
### Configuration
###
    
handler_tuples = [
    (r'^/login', LoginHandler),
    (r'^/logout', LogoutHandler),
    (r'^/', LandingHandler),
]

config = {
    'msg_conn': Mongrel2Connection('tcp://127.0.0.1:9999', 'tcp://127.0.0.1:9998'),
    'handler_tuples': handler_tuples,
    'template_loader': load_jinja2_env('./templates/login'),
    'login_url': '/login',
}

app = Brubeck(**config)
app.run()

########NEW FILE########
__FILENAME__ = demo_longpolling
#!/usr/bin/env python


from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.templating import load_jinja2_env, Jinja2Rendering
from brubeck.connections import Mongrel2Connection
import sys
import datetime
import time

try:
    import eventlet
except:
    import gevent

class DemoHandler(Jinja2Rendering):
    def get(self):
        name = self.get_argument('name', 'dude')
        self.set_body('Take five, %s!' % name)
        return self.render_template('base.html')


class FeedHandler(WebMessageHandler):
    def get(self):
        try:
            eventlet.sleep(2) # simple way to demo long polling :)
        except:
            gevent.sleep(2)
        self.set_body('The current time is: %s' % datetime.datetime.now(),
                      headers={'Content-Type': 'text/plain'})
        return self.render()


config = {
    'msg_conn': Mongrel2Connection('tcp://127.0.0.1:9999', 'tcp://127.0.0.1:9998'),
    'handler_tuples': [(r'^/$', DemoHandler),
                       (r'^/feed', FeedHandler)],
    'template_loader': load_jinja2_env('./templates/longpolling'),
}


app = Brubeck(**config)
app.run()

########NEW FILE########
__FILENAME__ = demo_mako
#!/usr/bin/env python

from brubeck.request_handling import Brubeck
from brubeck.templating import MakoRendering, load_mako_env
from brubeck.connections import Mongrel2Connection
import sys


class DemoHandler(MakoRendering):
    def get(self):
        name = self.get_argument('name', 'dude')
        context = {
            'name': name
        }
        return self.render_template('success.html', **context)

app = Brubeck(msg_conn=Mongrel2Connection('tcp://127.0.0.1:9999', 'tcp://127.0.0.1:9998'),
              handler_tuples=[(r'^/brubeck', DemoHandler)],
              template_loader=load_mako_env('./templates/mako'))
app.run()

########NEW FILE########
__FILENAME__ = demo_minimal
#!/usr/bin/env python

from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.connections import Mongrel2Connection
import sys

class DemoHandler(WebMessageHandler):
    def get(self):
        name = self.get_argument('name', 'dude')
        self.set_body('Take five, %s!' % name)
        return self.render()

config = {
    'msg_conn': Mongrel2Connection('tcp://127.0.0.1:9999',
                                   'tcp://127.0.0.1:9998'),
    'handler_tuples': [(r'^/brubeck', DemoHandler)],
}
app = Brubeck(**config)
app.run()

########NEW FILE########
__FILENAME__ = demo_multipart
#!/usr/bin/env python


from brubeck.request_handling import Brubeck
from brubeck.models import User
from brubeck.templating import Jinja2Rendering, load_jinja2_env
from brubeck.connections import WSGIConnection, Mongrel2Connection
import sys
import logging
import Image
import StringIO


###
### Handlers
###

class UploadHandler(Jinja2Rendering):
    def get(self):
        """Offers login form to user
        """
        return self.render_template('landing.html')
    
    def post(self):
        """Checks credentials with decorator and sends user authenticated
        users to the landing page.
        """
        if hasattr(self.message, 'files'):
            print 'FILES:', self.message.files['data'][0]['body']
            im = Image.open(StringIO.StringIO(self.message.files['data'][0]['body']))
            im.save('word.png')
        return self.redirect('/')


###
### Configuration
###
    
config = {
    'msg_conn': Mongrel2Connection("tcp://127.0.0.1:9999", "tcp://127.0.0.1:9998"),
    'handler_tuples': [(r'^/add_file', UploadHandler)],
    'template_loader': load_jinja2_env('./templates/multipart'),
}

app = Brubeck(**config)
app.run()

########NEW FILE########
__FILENAME__ = demo_mustache
#!/usr/bin/env python

from brubeck.request_handling import Brubeck
from brubeck.templating import MustacheRendering, load_mustache_env
from brubeck.connections import Mongrel2Connection

class DemoHandler(MustacheRendering):
    def get(self):
        name = self.get_argument('name', 'dude')
        context = {
            'name': name,
        }
        return self.render_template('success', **context)

app = Brubeck(msg_conn=Mongrel2Connection('tcp://127.0.0.1:9999', 'tcp://127.0.0.1:9998'),
              handler_tuples=[(r'^/brubeck', DemoHandler)],
              template_loader=load_mustache_env('./templates/mustache'))
app.run()

########NEW FILE########
__FILENAME__ = demo_noclasses
#!/usr/bin/env python

from brubeck.request_handling import Brubeck, render
from brubeck.connections import Mongrel2Connection

app = Brubeck(msg_conn=Mongrel2Connection('tcp://127.0.0.1:9999',
                                          'tcp://127.0.0.1:9998'))

@app.add_route('^/brubeck', method='GET')
def foo(application, message):
    name = message.get_argument('name', 'dude')
    body = 'Take five, %s!' % name
    return render(body, 200, 'OK', {})
        
app.run()

########NEW FILE########
__FILENAME__ = demo_tornado
#!/usr/bin/env python

from brubeck.request_handling import Brubeck
from brubeck.templating import TornadoRendering, load_tornado_env
from brubeck.connections import Mongrel2Connection
import sys

class DemoHandler(TornadoRendering):
    def get(self):
        name = self.get_argument('name', 'dude')
        context = {
            'name': name,
        }
        return self.render_template('success.html', **context)

app = Brubeck(msg_conn=Mongrel2Connection('tcp://127.0.0.1:9999', 'tcp://127.0.0.1:9998'),
              handler_tuples=[(r'^/brubeck', DemoHandler)],
              template_loader=load_tornado_env('./templates/tornado'))
app.run()

########NEW FILE########
__FILENAME__ = demo_urlargs
#!/usr/bin/env python


from brubeck.request_handling import Brubeck, WebMessageHandler, render
from brubeck.connections import Mongrel2Connection
import sys


class IndexHandler(WebMessageHandler):
    def get(self):
        self.set_body('Take five!')
        return self.render()

class NameHandler(WebMessageHandler):
    def get(self, name):
        self.set_body('Take five, %s!' % (name))
        return self.render()

def name_handler(application, message, name):
    return render('Take five, %s!' % (name), 200, 'OK', {})


urls = [(r'^/class/(\w+)$', NameHandler),
        (r'^/fun/(?P<name>\w+)$', name_handler),
        (r'^/$', IndexHandler)]

config = {
    'msg_conn': Mongrel2Connection('tcp://127.0.0.1:9999', 'tcp://127.0.0.1:9998'),
    'handler_tuples': urls,
}

app = Brubeck(**config)


@app.add_route('^/deco/(?P<name>\w+)$', method='GET')
def new_name_handler(application, message, name):
    return render('Take five, %s!' % (name), 200, 'OK', {})


app.run()

########NEW FILE########
__FILENAME__ = demo_wsgi
#!/usr/bin/env python

import sys
import os
from brubeck.request_handling import Brubeck, WebMessageHandler
from brubeck.connections import WSGIConnection

class DemoHandler(WebMessageHandler):
    def get(self):
        name = self.get_argument('name', 'dude')
        self.set_body('Take five, %s!' % name)
        return self.render()

config = {
    'msg_conn': WSGIConnection(),
    'handler_tuples': [(r'^/brubeck', DemoHandler)],
}

app = Brubeck(**config)
app.run()

########NEW FILE########
__FILENAME__ = m2reader
#!/usr/bin/env python

import zmq

ctx = zmq.Context()
s = ctx.socket(zmq.PULL)
s.connect("ipc://127.0.0.1:9999")

while True:
    msg = s.recv()
    print msg

########NEW FILE########
__FILENAME__ = upupdowndown
### Could live in settings
src_dir = './'
html_dir = '../../brubeck.io/'
header_file = '%s%s' % (html_dir + 'media/', 'header.html')
footer_file = '%s%s' % (html_dir + 'media/', 'footer.html')

########NEW FILE########
__FILENAME__ = request_handler_fixtures
import os
##
## setup our simple messages for testing """
##
dir = os.path.abspath(__file__)[0:len(os.path.abspath(__file__))-28] + '/'

HTTP_REQUEST_BRUBECK = file( dir + 'http_request_brubeck.txt','r').read()

HTTP_REQUEST_ROOT = file(dir + 'http_request_root.txt','r').read()

HTTP_REQUEST_ROOT_WITH_COOKIE = file(dir + 'http_request_root_with_cookie.txt','r').read()

##
## our test body text
##
TEST_BODY_METHOD_HANDLER = file(dir + 'test_body_method_handler.txt','r').read().rstrip('\n')
TEST_BODY_OBJECT_HANDLER = file(dir + 'test_body_object_handler.txt','r').read().rstrip('\n')

##
##  setup our expected reponses
##
HTTP_RESPONSE_OBJECT_ROOT =      'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(TEST_BODY_OBJECT_HANDLER)) + '\r\n\r\n' + TEST_BODY_OBJECT_HANDLER
HTTP_RESPONSE_METHOD_ROOT =      'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(TEST_BODY_METHOD_HANDLER)) + '\r\n\r\n' + TEST_BODY_METHOD_HANDLER
HTTP_RESPONSE_JSON_OBJECT_ROOT = 'HTTP/1.1 200 OK\r\nContent-Length: 90\r\nContent-Type: application/json\r\n\r\n{"status_code":200,"status_msg":"OK","message":"Take five dude","timestamp":1320456118809}'

HTTP_RESPONSE_OBJECT_ROOT_WITH_COOKIE = 'HTTP/1.1 200 OK\r\nSet-Cookie: key=value\r\nContent-Length: ' + str(len(TEST_BODY_OBJECT_HANDLER)) + '\r\n\r\n' + TEST_BODY_OBJECT_HANDLER


########NEW FILE########
__FILENAME__ = method_handlers
from brubeck.request_handling import http_response

def simple_handler_method(self, application, *args):
    """" dummy request action """
    return http_response(file('./fixtures/test_body_method_handler.txt','r').read().rstrip('\n'), 200, 'OK', dict())


########NEW FILE########
__FILENAME__ = object_handlers
from brubeck.request_handling import Brubeck, WebMessageHandler, JSONMessageHandler

from tests.fixtures import request_handler_fixtures as FIXTURES



class SimpleWebHandlerObject(WebMessageHandler):
    def get(self):
        self.set_body(FIXTURES.TEST_BODY_OBJECT_HANDLER)
        return self.render()

class CookieWebHandlerObject(WebMessageHandler):
    def get(self):
        self.set_cookie("key", self.get_cookie("key"));
        self.set_body(FIXTURES.TEST_BODY_OBJECT_HANDLER)
        return self.render()

class SimpleJSONHandlerObject(JSONMessageHandler):
    def get(self):
        self.add_to_payload('message', 'Take five dude')
        self.set_status(200)
        """ we only set time so it matches our expected response """
        self.add_to_payload("timestamp",1320456118809)
        return self.render()

class CookieAddWebHandlerObject(WebMessageHandler):
    def get(self):
        self.set_cookie("key", "value");
        self.set_body(FIXTURES.TEST_BODY_OBJECT_HANDLER)
        return self.render()

class PrepareHookWebHandlerObject(WebMessageHandler):
    def get(self):
        return self.render()

    def prepare(self):
        self.set_body(FIXTURES.TEST_BODY_OBJECT_HANDLER)

class InitializeHookWebHandlerObject(WebMessageHandler):
    def get(self):
        return self.render()

    def initialize(self):
        self.headers = dict()
        self.set_body(FIXTURES.TEST_BODY_OBJECT_HANDLER)


########NEW FILE########
__FILENAME__ = test_queryset
#!/usr/bin/env python

import unittest

import mock

import brubeck
from handlers.method_handlers import simple_handler_method
from brubeck.request_handling import Brubeck, WebMessageHandler, JSONMessageHandler
from brubeck.connections import to_bytes, Request
from brubeck.request_handling import(
    cookie_encode, cookie_decode,
    cookie_is_encoded, http_response
)
from handlers.object_handlers import(
    SimpleWebHandlerObject, CookieWebHandlerObject,
    SimpleJSONHandlerObject, CookieAddWebHandlerObject,
    PrepareHookWebHandlerObject, InitializeHookWebHandlerObject
)
from fixtures import request_handler_fixtures as FIXTURES

from brubeck.autoapi import AutoAPIBase
from brubeck.queryset import DictQueryset, AbstractQueryset, RedisQueryset

from dictshield.document import Document
from dictshield.fields import StringField
from brubeck.request_handling import FourOhFourException

##TestDocument
class TestDoc(Document):
    data = StringField()
    class Meta:
        id_field = StringField

###
### Tests for ensuring that the autoapi returns good data
###
class TestQuerySetPrimitives(unittest.TestCase):
    """
    a test class for brubeck's queryset objects' core operations.
    """

    def setUp(self):
        self.queryset = AbstractQueryset()

    def create(self):
        pass

    def read(self):
        pass

    def update(self):
        pass

    def destroy(self):
       pass


class TestDictQueryset(unittest.TestCase):
    """
    a test class for brubeck's dictqueryset's operations.
    """


    def setUp(self):
        self.queryset = DictQueryset()

    def seed_reads(self):
        shields = [TestDoc(id="foo"), TestDoc(id="bar"), TestDoc(id="baz")]
        self.queryset.create_many(shields)
        return shields


    def test__create_one(self):
        shield = TestDoc(id="foo")
        status, return_shield = self.queryset.create_one(shield)
        self.assertEqual(self.queryset.MSG_CREATED, status)
        self.assertEqual(shield, return_shield)

        status, return_shield = self.queryset.create_one(shield)
        self.assertEqual(self.queryset.MSG_UPDATED, status)


    def test__create_many(self):
        shield0 = TestDoc(id="foo")
        shield1 = TestDoc(id="bar")
        shield2 = TestDoc(id="baz")
        statuses = self.queryset.create_many([shield0, shield1, shield2])
        for status, datum in statuses:
            self.assertEqual(self.queryset.MSG_CREATED, status)

        shield3 = TestDoc(id="bloop")
        statuses = self.queryset.create_many([shield0, shield3, shield2])
        status, datum = statuses[1]
        self.assertEqual(self.queryset.MSG_CREATED, status)
        status, datum = statuses[0]
        self.assertEqual(self.queryset.MSG_UPDATED, status)

    def test__read_all(self):
        shields = self.seed_reads()
        statuses = self.queryset.read_all()

        for status, datum in statuses:
            self.assertEqual(self.queryset.MSG_OK, status)

        actual = sorted([datum for trash, datum in statuses])
        expected = sorted([shield.to_python() for shield in shields])
        self.assertEqual(expected, actual)

    def test__read_one(self):
        shields = self.seed_reads()
        for shield in shields:
            status, datum = self.queryset.read_one(shield.id)
            self.assertEqual(self.queryset.MSG_OK, status)
            self.assertEqual(datum, shield.to_python())
        bad_key = 'DOESNTEXISIT'
        status, datum = self.queryset.read(bad_key)
        self.assertEqual(bad_key, datum)
        self.assertEqual(self.queryset.MSG_FAILED, status)

    def test__read_many(self):
        shields = self.seed_reads()
        expected = [shield.to_python() for shield in shields]
        responses = self.queryset.read_many([s.id for s in shields])
        for status, datum in responses:
            self.assertEqual(self.queryset.MSG_OK, status)
            self.assertTrue(datum in expected)

        bad_ids = [s.id for s in shields]
        bad_ids.append('DOESNTEXISIT')
        status, iid = self.queryset.read_many(bad_ids)[-1]
        self.assertEqual(self.queryset.MSG_FAILED, status)


    def test_update_one(self):
        shields = self.seed_reads()
        test_shield = shields[0]
        test_shield.data = "foob"
        status, datum = self.queryset.update_one(test_shield)

        self.assertEqual(self.queryset.MSG_UPDATED, status)
        self.assertEqual('foob', datum['data'])

        status, datum =  self.queryset.read_one(test_shield.id)
        self.assertEqual('foob', datum['data'])


    def test_update_many(self):
        shields = self.seed_reads()
        for shield in shields:
            shield.data = "foob"
        responses = self.queryset.update_many(shields)
        for status, datum in responses:
            self.assertEqual(self.queryset.MSG_UPDATED, status)
            self.assertEqual('foob', datum['data'])
        for status, datum in self.queryset.read_all():
            self.assertEqual('foob', datum['data'])


    def test_destroy_one(self):
        shields = self.seed_reads()
        test_shield = shields[0]
        status, datum = self.queryset.destroy_one(test_shield.id)
        self.assertEqual(self.queryset.MSG_UPDATED, status)

        status, datum = self.queryset.read_one(test_shield.id)
        self.assertEqual(test_shield.id, datum)
        self.assertEqual(self.queryset.MSG_FAILED, status)


    def test_destroy_many(self):
        shields = self.seed_reads()
        shield_to_keep = shields.pop()
        responses = self.queryset.destroy_many([shield.id for shield in shields])
        for status, datum in responses:
            self.assertEqual(self.queryset.MSG_UPDATED, status)

        responses = self.queryset.read_many([shield.id for shield in shields])
        for status, datum in responses:
            self.assertEqual(self.queryset.MSG_FAILED, status)

        status, datum = self.queryset.read_one(shield_to_keep.id)
        self.assertEqual(self.queryset.MSG_OK, status)
        self.assertEqual(shield_to_keep.to_python(), datum)


class TestRedisQueryset(TestQuerySetPrimitives):
    """
    Test RedisQueryset operations.
    """
    def setUp(self):
        pass

    def seed_reads(self):
        shields = [TestDoc(id="foo"), TestDoc(id="bar"), TestDoc(id="baz")]
        return shields

    def test__create_one(self):
        with mock.patch('redis.StrictRedis') as patchedRedis:
            redis_connection = patchedRedis(host='localhost', port=6379, db=0)
            queryset = RedisQueryset(db_conn=redis_connection)
            
            shield = TestDoc(id="foo")
            queryset.create_one(shield)
            
            name, args, kwargs = redis_connection.mock_calls[0]
            self.assertEqual(name, 'hset')
            self.assertEqual(args, (queryset.api_id, 'foo', '{"_types": ["TestDoc"], "id": "foo", "_cls": "TestDoc"}'))
            
    def test__create_many(self):
        with mock.patch('redis.StrictRedis') as patchedRedis:
            redis_connection = patchedRedis(host='localhost', port=6379, db=0)
            queryset = RedisQueryset(db_conn=redis_connection)
            queryset.create_many(self.seed_reads())
            expected = [
                ('pipeline', (), {}),
                ('pipeline().hset', (queryset.api_id, 'foo', '{"_types": ["TestDoc"], "id": "foo", "_cls": "TestDoc"}'), {}),
                ('pipeline().hset', (queryset.api_id, 'bar', '{"_types": ["TestDoc"], "id": "bar", "_cls": "TestDoc"}'), {}),
                ('pipeline().hset', (queryset.api_id, 'baz', '{"_types": ["TestDoc"], "id": "baz", "_cls": "TestDoc"}'), {}),
                ('pipeline().execute', (), {}),
                ('pipeline().execute().__iter__', (), {}),
                ('pipeline().reset', (), {})
                ]
            for call in zip(expected, redis_connection.mock_calls):
                self.assertEqual(call[0], call[1])

    def test__read_all(self):
        with mock.patch('redis.StrictRedis') as patchedRedis:
            redis_connection = patchedRedis(host='localhost', port=6379, db=0)
            queryset = RedisQueryset(db_conn=redis_connection)
            statuses = queryset.read_all()
            
            name, args, kwargs = redis_connection.mock_calls[0]
            self.assertEqual(name, 'hvals')
            self.assertEqual(args, (queryset.api_id,))
            
            name, args, kwargs = redis_connection.mock_calls[1]
            self.assertEqual(name, 'hvals().__iter__')
            self.assertEqual(args, ())

    def test__read_one(self):
        for _id in ['foo', 'bar', 'baz']:
            with mock.patch('redis.StrictRedis') as patchedRedis:
                instance = patchedRedis.return_value
                instance.hget.return_value = '{"called": "hget"}'
                redis_connection = patchedRedis(host='localhost', port=6379, db=0)
                queryset = RedisQueryset(db_conn=redis_connection)

                msg, result = queryset.read_one(_id)
                assert (RedisQueryset.MSG_OK, {'called': 'hget'}) == (msg, result)

                name, args, kwargs = redis_connection.mock_calls[0]
                self.assertEqual(name, 'hget')
                self.assertEqual(args, (queryset.api_id, _id))
                self.assertEqual(kwargs, {})
                
    def test__read_many(self):
        with mock.patch('redis.StrictRedis') as patchedRedis:
            redis_connection = patchedRedis(host='localhost', port=6379, db=0)
            queryset = RedisQueryset(db_conn=redis_connection)
            queryset.read_many(['foo', 'bar', 'baz', 'laser', 'beams'])
            expected = [('pipeline', (), {}),
                        ('pipeline().hget', (queryset.api_id, 'foo'), {}),
                        ('pipeline().hget', (queryset.api_id, 'bar'), {}),
                        ('pipeline().hget', (queryset.api_id, 'baz'), {}),
                        ('pipeline().hget', (queryset.api_id, 'laser'), {}),
                        ('pipeline().hget', (queryset.api_id, 'beams'), {}),
                        ('pipeline().execute', (), {}),
                        ('pipeline().reset', (), {}),
                        ('pipeline().execute().__iter__', (), {}),
                        ('pipeline().execute().__iter__', (), {}),
                        ('pipeline().execute().__len__', (), {}),
                        ]
            for call in zip(expected, redis_connection.mock_calls):
                assert call[0] == call[1]

    def test_update_one(self):
        with mock.patch('redis.StrictRedis') as patchedRedis:
            instance = patchedRedis.return_value
            redis_connection = patchedRedis(host='localhost', port=6379, db=0)
            queryset = RedisQueryset(db_conn=redis_connection)

            original = mock.Mock()
            doc_instance = original.return_value
            doc_instance.id = 'foo'
            doc_instance.to_json.return_value = '{"to": "json"}'

            queryset.update_one(doc_instance)

            expected = ('hset', ('id', 'foo', '{"to": "json"}'), {})

            self.assertEqual(expected, redis_connection.mock_calls[0])


    def test_update_many(self):
        with mock.patch('redis.StrictRedis') as patchedRedis:
            redis_connection = patchedRedis(host='localhost', port=6379, db=0)
            queryset = RedisQueryset(db_conn=redis_connection)
            queryset.update_many(self.seed_reads())
            expected = [
                ('pipeline', (), {}),
                ('pipeline().hset', (queryset.api_id, 'foo', '{"_types": ["TestDoc"], "id": "foo", "_cls": "TestDoc"}'), {}),
                ('pipeline().hset', (queryset.api_id, 'bar', '{"_types": ["TestDoc"], "id": "bar", "_cls": "TestDoc"}'), {}),
                ('pipeline().hset', (queryset.api_id, 'baz', '{"_types": ["TestDoc"], "id": "baz", "_cls": "TestDoc"}'), {}),
                ('pipeline().execute', (), {}),
                ('pipeline().reset', (), {}),
                ('pipeline().execute().__iter__', (), {}),
                ]

            for call in zip(expected, redis_connection.mock_calls):
                self.assertEqual(call[0], call[1])

    def test_destroy_one(self):
        with mock.patch('redis.StrictRedis') as patchedRedis:
            instance = patchedRedis.return_value
            instance.pipeline = mock.Mock()
            pipe_instance = instance.pipeline.return_value
            pipe_instance.execute.return_value = ('{"success": "hget"}', 1)

            redis_connection = patchedRedis(host='localhost', port=6379, db=0)
            queryset = RedisQueryset(db_conn=redis_connection)
            queryset.destroy_one('bar')

            expected = [
                ('pipeline', (), {}),
                ('pipeline().hget', ('id', 'bar'), {}),
                ('pipeline().hdel', ('id', 'bar'), {}),
                ('pipeline().execute', (), {})
                ]
            for call in zip(expected, redis_connection.mock_calls):
                self.assertEqual(call[0], call[1])

    def test_destroy_many(self):
        with mock.patch('redis.StrictRedis') as patchedRedis:
            instance = patchedRedis.return_value
            instance.pipeline = mock.Mock()
            pipe_instance = instance.pipeline.return_value
            shields = self.seed_reads()
            json_shields = [shield.to_json() for shield in shields]
            results = json_shields
            pipe_instance.execute.return_value = results
            
            redis_connection = patchedRedis(host='localhost', port=6379, db=0)
            
            queryset = RedisQueryset(db_conn=redis_connection)

            queryset.destroy_many([shield.id for shield in shields])

            expected = [('pipeline', (), {}),
                        ('pipeline().hget', (queryset.api_id, 'foo'), {}),
                        ('pipeline().hget', (queryset.api_id, 'bar'), {}),
                        ('pipeline().hget', (queryset.api_id, 'baz'), {}),
                        ('pipeline().execute', (), {}),
                        ('pipeline().hdel', (queryset.api_id, 'foo'), {}),
                        ('pipeline().hdel', (queryset.api_id, 'bar'), {}),
                        ('pipeline().hdel', (queryset.api_id, 'baz'), {}),
                        ('pipeline().execute', (), {}),
                        ('pipeline().reset', (), {})
                        ]
            for call in zip(expected, redis_connection.mock_calls):
                self.assertEqual(call[0], call[1])

##
## This will run our tests
##
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_request_handling
#!/usr/bin/env python

import unittest
import sys
import brubeck
from handlers.method_handlers import simple_handler_method
from brubeck.request_handling import Brubeck, WebMessageHandler, JSONMessageHandler
from brubeck.connections import to_bytes, Request, WSGIConnection
from brubeck.request_handling import(
    cookie_encode, cookie_decode,
    cookie_is_encoded, http_response
)
from handlers.object_handlers import(
    SimpleWebHandlerObject, CookieWebHandlerObject,
    SimpleJSONHandlerObject, CookieAddWebHandlerObject,
    PrepareHookWebHandlerObject, InitializeHookWebHandlerObject
)
from fixtures import request_handler_fixtures as FIXTURES

###
### Message handling (non)coroutines for testing
###
def route_message(application, message):
    handler = application.route_message(message)
    return request_handler(application, message, handler)

def request_handler(application, message, handler):
    if callable(handler):
        return handler()

class MockMessage(object):
    """ we are enough of a message to test routing rules message """
    def __init__(self, path = '/', msg = FIXTURES.HTTP_REQUEST_ROOT):
        self.path = path
        self.msg = msg

    def get(self):
       return self.msg
        
class TestRequestHandling(unittest.TestCase):
    """
    a test class for brubeck's request_handler
    """

    def setUp(self):
        """ will get run for each test """
        config = {
            'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
            'msg_conn': WSGIConnection()
        }
        self.app = Brubeck(**config)
    ##
    ## our actual tests( test _xxxx_xxxx(self) ) 
    ##
    def test_add_route_rule_method(self):
	# Make sure we have no routes
        self.assertEqual(hasattr(self.app,'_routes'),False)

        # setup a route
        self.setup_route_with_method()

        # Make sure we have some routes
        self.assertEqual(hasattr(self.app,'_routes'),True)

        # Make sure we have exactly one route
        self.assertEqual(len(self.app._routes),1)

    def test_init_routes_with_methods(self):
        # Make sure we have no routes
        self.assertEqual(hasattr(self.app, '_routes'), False)

        # Create a tuple with routes with method handlers
        routes = [ (r'^/', simple_handler_method), (r'^/brubeck', simple_handler_method) ]
        # init our routes
        self.app.init_routes( routes )

        # Make sure we have two routes
        self.assertEqual(len(self.app._routes), 2)

    def test_init_routes_with_objects(self):
        # Make sure we have no routes
        self.assertEqual(hasattr(self.app, '_routes'), False)

        # Create a tuple of routes with object handlers
        routes = [(r'^/', SimpleWebHandlerObject), (r'^/brubeck', SimpleWebHandlerObject)]
        self.app.init_routes( routes )

        # Make sure we have two routes
        self.assertEqual(len(self.app._routes), 2)

    def test_init_routes_with_objects_and_methods(self):
        # Make sure we have no routes
        self.assertEqual(hasattr(self.app, '_routes'), False)

        # Create a tuple of routes with a method handler and an object handler
        routes = [(r'^/', SimpleWebHandlerObject), (r'^/brubeck', simple_handler_method)]
        self.app.init_routes( routes )

        # Make sure we have two routes
        self.assertEqual(len(self.app._routes), 2)

    def test_add_route_rule_object(self):
        # Make sure we have no routes
        self.assertEqual(hasattr(self.app,'_routes'),False)
        self.setup_route_with_object()

        # Make sure we have some routes
        self.assertEqual(hasattr(self.app,'_routes'),True)

        # Make sure we have exactly one route
        self.assertEqual(len(self.app._routes),1)

    def test_brubeck_handle_request_with_object(self):
        # set up our route
        self.setup_route_with_object()

        # Make sure we get a handler back when we request one
        message = MockMessage(path='/')
        handler = self.app.route_message(message)
        self.assertNotEqual(handler,None)

    def test_brubeck_handle_request_with_method(self):
        # We ran tests on this already, so assume it works
        self.setup_route_with_method()

        # Make sure we get a handler back when we request one
        message = MockMessage(path='/')
        handler = self.app.route_message(message)
        self.assertNotEqual(handler,None)

    def test_cookie_handling(self):
        # set our cookie key and values
        cookie_key = 'my_key'
        cookie_value = 'my_secret'

        # encode our cookie
        encoded_cookie = cookie_encode(cookie_value, cookie_key)

        # Make sure we do not contain our value (i.e. we are really encrypting)
        self.assertEqual(encoded_cookie.find(cookie_value) == -1, True)

        # Make sure we are an encoded cookie using the function
        self.assertEqual(cookie_is_encoded(encoded_cookie), True)

        # Make sure after decoding our cookie we are the same as the unencoded cookie
        decoded_cookie_value = cookie_decode(encoded_cookie, cookie_key)
        self.assertEqual(decoded_cookie_value, cookie_value)
    
    ##
    ## test a bunch of very simple requests making sure we get the expected results
    ##
    def test_web_request_handling_with_object(self):
        self.setup_route_with_object()
        result = route_message(self.app, Request.parse_msg(FIXTURES.HTTP_REQUEST_ROOT))
        response = http_response(result['body'], result['status_code'], result['status_msg'], result['headers'])
        self.assertEqual(FIXTURES.HTTP_RESPONSE_OBJECT_ROOT, response)

    def test_web_request_handling_with_method(self):
        self.setup_route_with_method()
        response = route_message(self.app, Request.parse_msg(FIXTURES.HTTP_REQUEST_ROOT))
        self.assertEqual(FIXTURES.HTTP_RESPONSE_METHOD_ROOT, response)

    def test_json_request_handling_with_object(self):
        self.app.add_route_rule(r'^/$',SimpleJSONHandlerObject)
        result = route_message(self.app, Request.parse_msg(FIXTURES.HTTP_REQUEST_ROOT))
        response = http_response(result['body'], result['status_code'], result['status_msg'], result['headers'])
        self.assertEqual(FIXTURES.HTTP_RESPONSE_JSON_OBJECT_ROOT, response)

    def test_request_with_cookie_handling_with_object(self):
        self.app.add_route_rule(r'^/$',CookieWebHandlerObject)
        result = route_message(self.app, Request.parse_msg(FIXTURES.HTTP_REQUEST_ROOT_WITH_COOKIE))
        response = http_response(result['body'], result['status_code'], result['status_msg'], result['headers'])
        self.assertEqual(FIXTURES.HTTP_RESPONSE_OBJECT_ROOT_WITH_COOKIE, response)

    def test_request_with_cookie_response_with_cookie_handling_with_object(self):
        self.app.add_route_rule(r'^/$',CookieWebHandlerObject)
        result = route_message(self.app, Request.parse_msg(FIXTURES.HTTP_REQUEST_ROOT_WITH_COOKIE))
        response = http_response(result['body'], result['status_code'], result['status_msg'], result['headers'])
        self.assertEqual(FIXTURES.HTTP_RESPONSE_OBJECT_ROOT_WITH_COOKIE, response)

    def test_request_without_cookie_response_with_cookie_handling_with_object(self):
        self.app.add_route_rule(r'^/$',CookieAddWebHandlerObject)
        result = route_message(self.app, Request.parse_msg(FIXTURES.HTTP_REQUEST_ROOT))
        response = http_response(result['body'], result['status_code'], result['status_msg'], result['headers'])
        self.assertEqual(FIXTURES.HTTP_RESPONSE_OBJECT_ROOT_WITH_COOKIE, response)

    def test_build_http_response(self):
        response = http_response(FIXTURES.TEST_BODY_OBJECT_HANDLER, 200, 'OK', dict())
        self.assertEqual(FIXTURES.HTTP_RESPONSE_OBJECT_ROOT, response)

    def test_handler_initialize_hook(self):
        ## create a handler that sets the expected body(and headers) in the initialize hook
        handler = InitializeHookWebHandlerObject(self.app, Request.parse_msg(FIXTURES.HTTP_REQUEST_ROOT))
        result = handler()
        response = http_response(result['body'], result['status_code'], result['status_msg'], result['headers'])
        self.assertEqual(response, FIXTURES.HTTP_RESPONSE_OBJECT_ROOT)

    def test_handler_prepare_hook(self):
        # create a handler that sets the expected body in the prepare hook
        handler = PrepareHookWebHandlerObject(self.app, Request.parse_msg(FIXTURES.HTTP_REQUEST_ROOT))
        result = handler()
        response = http_response(result['body'], result['status_code'], result['status_msg'], result['headers'])
        self.assertEqual(response, FIXTURES.HTTP_RESPONSE_OBJECT_ROOT)

    ##
    ## some simple helper functions to setup a route """
    ##
    def setup_route_with_object(self, url_pattern='^/$'):
        self.app.add_route_rule(url_pattern,SimpleWebHandlerObject)

    def setup_route_with_method(self, url_pattern='^/$'):
        method = simple_handler_method
        self.app.add_route_rule(url_pattern, method)

##
## This will run our tests
##
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = wsgi
from brubeck.request import Request
from brubeck.request_handling import coro_spawn, route_message


def receive_wsgi_req(environ, start_response):
    request = Request.parse_wsgi_request(environ)
    coro_spawn(route_message, self, request)

class WSGIConnection(object):
    """This class defines request handling methods for wsgi implimentations."""

    def __init__(self):
        pass

    def recv(self):
        """Receives the request from the wsgi server."""
        pass

if __name__ == "__main__":
    from wsgiref.util import setup_testing_defaults
    from wsgiref.simple_server import make_server
    def simple_app(environ, start_response):
        setup_testing_defaults(environ)

        status = '200 OK'
        headers = [('Content-type', 'text/plain')]

        start_response(status, headers)

        ret = ["%s: %s\n" % (key, value)
               for key, value in environ.iteritems()]
        return ret

    httpd = make_server('', 8000, receive_wsgi_req)
    print "Serving on port 8000..."
    httpd.serve_forever()

########NEW FILE########
