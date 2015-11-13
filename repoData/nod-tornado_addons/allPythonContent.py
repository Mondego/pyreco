__FILENAME__ = test_async_yield

from ..tornado_addons.async_yield import async_yield, AsyncYieldMixin

import tornado
from random import randint

from tornado.testing import AsyncTestCase


class AYHandler(AsyncYieldMixin, tornado.web.RequestHandler):
    """
    very basic handler for writing async yield tests on a RequestHandler
    """

    def __init__(self):
        """
        fake this to make it easier to instantiate
        """
        self.application = tornado.web.Application([], {})

    def prepare(self):
        super(AYHandler, self).prepare()

    def async_assign(self, newdata, callback):
        """
        totally contrived async function
        """
        self.test_ioloop.add_callback(lambda: callback(newdata))

    @async_yield
    def embedded_async(self, callback):
        xx = yield self.async_assign('me', self.yield_cb)
        callback(xx)

    @async_yield
    def some_async_func(self, ioloop, val, callback):
        self.test_ioloop = ioloop # we have to fake this for tests
        results = yield self.async_assign(val, self.yield_cb)
        callback(results)

    @async_yield
    def call_other_async(self, ioloop, val, callback):
        cb = self.yield_cb
        self.test_ioloop = ioloop # we have to fake this for tests
        yield self.embedded_async(cb)
        results = yield self.async_assign(val, cb)
        callback(results)


class AYHandlerTests(AsyncTestCase):

    def setUp(self):
        AsyncTestCase.setUp(self)
        self.handler = AYHandler()
        self.handler.prepare()

    def tearDown(self):
        del self.handler

    def test_async_func(self):
        self.handler.some_async_func(self.io_loop, 'xyzzy', self.stop)
        retval = self.wait()
        self.assertTrue('xyzzy' == retval)

    def test_async_func_return_more(self):
        self.handler.some_async_func(self.io_loop, [1,2,3], self.stop)
        retval = self.wait()
        self.assertTrue(len(retval) == 3 and retval[1] == 2)

    def test_call_other_async_yield(self):
        self.handler.call_other_async(self.io_loop, [1,2,3], self.stop)
        retval = self.wait()
        self.assertTrue(len(retval) == 3 and retval[1] == 2)


########NEW FILE########
__FILENAME__ = test_cushion

"""
Tests the base cushion class. Gets skipped if trombi doesn't import.
"""

try:
    import trombi
    no_trombi = False
except:
    no_trombi = True

from unittest import skipIf
from random import randint
from tornado.testing import AsyncTestCase
from ..tornado_addons.cushion import Cushion, CushionException, CushionDBNotReady

baseurl = 'http://localhost:5984'

@skipIf(no_trombi, "not testing Cushion, trombi failed to import")
class CushionTests(AsyncTestCase):

    def setUp(self):
        AsyncTestCase.setUp(self)

        # now create our test cushion object
        self.cushion = Cushion(baseurl, io_loop=self.io_loop)
        assert isinstance(self.cushion._server, trombi.Server)

        # create a test db
        self.dbname = 'test_db' + str(randint(100, 100000))
        # connect to our database
        # this tests our open(..) method on cushion. I'd rather have it
        # in a separate test, but we need this database and if open fails here,
        # everything else should tank, so setUp is as good a place as any.
        self.cushion.create(self.dbname, self.stop)
        self.wait()
        self.cushion.open(self.dbname, self.stop)
        self.wait()
        # we're after the db has been added
        assert isinstance(self.cushion._pool[self.dbname], trombi.Database)

    def tearDown(self):
        # just blow away our test database using standard trombi fare
        self.cushion._server.delete(self.dbname, self.stop)
        self.wait()

    def test_db_open_with_callback(self):
        # note, this creates and deletes a bogus db
        bogus_db = 'test_db_trash_' + str(randint(10,99))
        self.cushion.create(bogus_db, self.stop)
        self.wait()
        self.cushion.open(bogus_db, self.stop)
        self.wait()
        self.assertTrue(bogus_db in self.cushion)
        self.cushion._server.delete(self.dbname, self.stop)
        self.wait()

    def test_db_not_exists(self):
        # note, this creates and deletes a bogus db
        bogus_db = 'test_db_not_exists_' + str(randint(10,99))
        self.cushion.exists(bogus_db, self.stop)
        is_there = self.wait()
        self.assertTrue( not is_there )

    def test_db_exists(self):
        # note, this creates and deletes a bogus db
        self.cushion.exists(self.dbname, self.stop)
        is_there = self.wait()
        self.assertTrue( is_there )

    def test_db_exists_make_one(self):
        # note, this creates and deletes a bogus db
        bogus_db = 'test_db_exists_' + str(randint(10,99))
        self.cushion.create(bogus_db, self.stop)
        self.wait()
        self.cushion.exists(bogus_db, self.stop)
        is_there = self.wait()
        self.assertTrue( is_there )

    def test_db_get(self):
        # check for a bogus database first
        self.assertRaises(
            CushionDBNotReady,
            self.cushion.get, 'bogus-not-there' )

        # now check for a good one
        self.assertTrue(
            isinstance(
                self.cushion.get(self.dbname),
                trombi.Database
                )
            )

    def test_db_ready(self):
        self.assertTrue( self.cushion.ready(self.dbname) )

    def test_db_shorthand_in(self):
        self.assertTrue( self.dbname in self.cushion )

    def _save_some_data(self, data):
        self.cushion.save( self.dbname, data, self.stop)
        return self.wait()

    def test_save(self):
        data = {'shoesize': 11}
        doc = self._save_some_data(data)
        self.assertTrue( '_id' in doc.raw() )
        self.saving_data = doc.raw()

    def test_delete(self):

        # try to delete bogus data
        try:
            self.cushion.delete(self.dbname, {'bogus':'yep'}, self.stop)
            self.wait()
        except Exception, e:
            self.assertTrue(isinstance(e, CushionException))

        # delete real data
        data = {'shoesize': 11}
        doc = self._save_some_data(data)
        self.cushion.delete(self.dbname, doc.raw(), self.stop)
        retval = self.wait()
        self.assertFalse(retval.error)

    def test_one(self):
        doc = self._save_some_data({'shoes':11, 'hat':'fitted'}).raw()
        self.cushion.one(self.dbname, doc['_id'], self.stop )
        retval = self.wait()
        self.assertEqual(retval['shoes'], doc['shoes'])

    def test_one_fail(self):
        self.cushion.one(self.dbname, 'just_not_there', self.stop )
        self.assertTrue( not self.wait() )

    def test_one_return_type(self):
        doc = self._save_some_data({'shoes':11, 'hat':'fitted'}).raw()
        self.cushion.one(self.dbname, doc['_id'], self.stop )
        retval = self.wait()
        # should be a dict
        self.assertTrue( type({}) == type(retval) )

    def test_view(self):
        # This test does quite a bit.  First, create 4 test records.
        # Then, create a view that will emit those records and insert that into
        # the db.  Finally, call our cushion.view object and compare results.

        self._save_some_data({'foo': 1, 'bar': 'a'})
        self._save_some_data({'foo': 2, 'bar': 'a'})
        self._save_some_data({'foo': 3, 'bar': 'b'})
        self._save_some_data({'foo': 4, 'bar': 'b'})

        fake_map = """ function (doc) { emit(doc['bar'], doc); } """

        # we're going to use python-couchdb's dynamic view loader stuff here
        from couchdb.design import ViewDefinition
        from couchdb.client import Server
        global baseurl
        cdb = Server(baseurl)
        couchdb = cdb[self.dbname]

        view_defn = ViewDefinition(
            'test', 'view',
            map_fun = fake_map,
            language = 'javascript' )
        view_defn.sync(couchdb)

        self.cushion.view(self.dbname, 'test/view', self.stop, key='b')
        records = self.wait()

        self.assertTrue(len(records) == 2)

        # OPTIMIZE: do more to ensure we're getting back what we want


########NEW FILE########
__FILENAME__ = test_cushion_mixin

"""
test the CushionDBMixin on RequestHandlers

NOTE - CushionDBMIxin lacks FULL TEST COVERAGE! FIXME
"""

try:
    import trombi
    no_trombi = False
except:
    no_trombi = True

from unittest import skipIf
from random import randint
from ..tornado_addons.cushion import Cushion, CushionException, CushionDBNotReady

baseurl = 'http://localhost:5984'

from ..tornado_addons.async_yield import AsyncYieldMixin
from ..tornado_addons.cushion import CushionDBMixin

import tornado
from random import randint

from tornado.testing import AsyncTestCase


class CushionHandler(CushionDBMixin, AsyncYieldMixin, tornado.web.RequestHandler):
    """
    very basic handler for writing async yield tests on a RequestHandler
    """
    def __init__(self):
        # we need this to avoid RequestHandler's gross __init__ requirements
        pass

    def prepare(self):
        super(CushionHandler,self).prepare()


@skipIf(no_trombi, "not testing Cushion, trombi failed to import")
class CushionMixinTests(AsyncTestCase):

    def setUp(self):
        AsyncTestCase.setUp(self)
        dbname =  'test_db' + str(randint(100, 100000))
        self.handler = CushionHandler()
        self.handler.prepare()
        # typically, this would be called in the Handler.prepare()
        self.handler.db_setup(
            dbname, baseurl,
            io_loop=self.io_loop, callback=self.stop, create=True )
        self.wait()

        # create one test record
        self.handler.cushion.save(self.handler.db_default, {'fake':'data'}, callback=self.stop)
        rec = self.wait()
        self.record = rec.raw()

    def tearDown(self):
        self.handler.cushion._server.delete(self.handler.db_default, self.stop)
        self.wait()
        del self.handler

    def test_db_one(self):
        self.handler.db_one(self.record['_id'], self.stop)
        rec = self.wait()
        self.assertTrue(self.record['fake'] == rec['fake'])


########NEW FILE########
__FILENAME__ = test_routes
import unittest
import tornado.web

from ..tornado_addons.route import route, route_redirect

# NOTE - right now, the route_redirect function is not tested.

class RouteTests(unittest.TestCase):

    def setUp(self):
        @route('/xyz')
        class XyzFake(object):
            pass

        route_redirect('/redir_elsewhere', '/abc')

        @route('/abc', name='abc')
        class AbcFake(object):
            pass

        route_redirect('/other_redir', '/abc', name='other')


    def test_num_routes(self):
        self.assertTrue( len(route.get_routes()) == 4 ) # 2 routes + 2 redir

    def test_routes_ordering(self):
        # our third handler's url route should be '/abc'
        self.assertTrue( route.get_routes()[2].reverse() == '/abc' )

    def test_routes_name(self):
        # our first handler's url route should be '/xyz'
        t = tornado.web.Application(route.get_routes(), {})
        self.assertTrue( t.reverse_url('abc') )
        self.assertTrue( t.reverse_url('other') )



########NEW FILE########
__FILENAME__ = async_yield
from types import GeneratorType
import tornado.web

class WrappedCall(object):
    def __init__(self, func, *a, **ka):
        self.func = func
        self.a = a
        self.ka = ka
        self.yielding = None

    def _yield_continue(self, response=None):
        try: self.yielding.send(response)
        except StopIteration: pass

    def yield_cb(self, *args, **ka):
        """
        A generic callback for yielded async calls that just captures all args
        and kwargs then continues execution.

        Notes about retval
        ------------------
        If a single value is returned into the callback, that value is returned
        as the value of a yield expression.

        i.e.: x = yield http.fetch(uri, self.mycb)

        The response from the fetch will be returned to x.

        If more than one value is returned, but no kwargs, the retval is the
        args tuple.  If there are kwargs but no args, then retval is kwargs.
        If there are both args and kwargs, retval = (args, kwargs).  If none,
        retval is None.

        It's a little gross but works for a large majority of the cases.
        """
        if args and ka:
            self._yield_continue((args, ka))
        elif ka and not args:
            self._yield_continue(ka)
        elif args and not ka:
            if len(args) == 1:
                # flatten it
                self._yield_continue(args[0])
            else:
                self._yield_continue(args)
        else:
            self._yield_continue()

    def __enter__(self):
        # munge this instance's yield_cb to map to THIS instance of a context
        obj = self.a[0]
        self.old_yield_cb = obj.yield_cb
        obj.yield_cb = self.yield_cb
        print "enter", self.func
        self.yielding = self.func(*self.a, **self.ka)
        return self.yielding

    def __exit__(self, exc_type, exc_value, traceback):
        obj = self.a[0]
        print "exit", obj, self.func
        # obj.yield_cb = self.old_yield_cb


def async_yield(f):
    def yielding_(*a, **ka):
        with WrappedCall(f, *a, **ka) as f_:
            if type(f_) is not GeneratorType:
                print "F_ not a generator", f_
                return f_

            print "F_ gen", f_
            try: 
                f_.next() # kickstart it
                print "f_ went", f_
            except StopIteration:
                print "STOP ITER", f_
                pass

    return yielding_


class AsyncYieldMixin(tornado.web.RequestHandler):

    yield_cb = lambda *a, **ka: None

    def prepare(self):
        self._yield_callbacks = {}
        super(AsyncYieldMixin, self).prepare()

    def add_func_callback(self, _id, cb):
        self._yield_callbacks[_id] = cb
        print "adding", _id, cb

    def rm_func_callback(self, _id):
        del self._yield_callbacks[_id]



########NEW FILE########
__FILENAME__ = cushion
import logging
import trombi

import tornado.ioloop


class CushionException(Exception):
    """
    Generic Cushion Exception
    """
    pass


class CushionDBNotReady(Exception):
    """
    This Exception will be tossed when a database hasn't been connected yet.
    """
    pass


pincushion = None

class Cushion(object):
    """
    Captures a pool of db connections here since each account can have their
    own connection.
    """
    _pool = {}
    _server = None

    @classmethod
    def new(self, uri, user=None, password=None, **ka):
        global pincushion
        if not pincushion:
            pincushion = Cushion(uri, user, password, **ka)
        return pincushion

    def __init__(self, uri, user=None, password=None, **ka):
        self._server = trombi.Server(
            uri,
            fetch_args=dict(auth_username=user, auth_password=password),
            **ka)

    def create(self, dbname, callback):
        """
        Attempt to create a database. If it exists, an exception will be
        thrown.
        """
        self._server.create(
            name=dbname,
            callback=callback )

    def exists(self, dbname, callback):
        """
        Attempt to get a connection to the specified database but don't add it
        to our pool if it's there.  You should use open(..) if you intend to
        use the database in the near future.
        """
        if dbname in self:
            # short circuit the whole mess if it's in "us"
            callback(True)
            return

        callback_ = callback

        def cb_(db):
            if db.error: callback_(False)
            else: callback_(True)

        self._server.get(
            name=dbname,
            callback=cb_,
            create=False )

    def open(self, dbname, callback, create=False):
        """
        Open a connection to a specific database instance.  If the database
        doesn't exist, an exception will be thrown unless create=True
        """
        if dbname in self:
            callback(self.get(dbname))
        else:
            def cb_wrapper(db):
                self._cb_add_db(db)
                callback(db)
            self._server.get(
                name=dbname,
                callback=cb_wrapper,
                create=create )

    def _cb_add_db(self, db):
        if db.error:
            logging.critical("ERROR WITH COUCHDB "+db.msg)
            raise CushionException(db.msg)
        else:
            logging.info("couchdb initialized "+str(db))
            self._pool[db.name] = db

    def get(self, dbname):
        if not self._pool.has_key(dbname):
            raise CushionDBNotReady(dbname + ' not open yet')
        return self._pool[dbname]

    def ready(self, dbname):
        """
        check that a database is actually connected.
        """
        return dbname in self

    def __contains__(self, dbname):
        return dbname in self._pool

    def one(self, db, _id, cb, **ka):
        """
        Convenience method to fetch one object by id from the specified
        database.

        Parameters
        ==========
        db -> db name as str
        _id -> key of document to fetch as str
        cb -> function ptr to callback
        ka -> keyword arguments
        """
        def _cb(doc):
            cb(doc.raw() if doc else None)
        # note, this is calling the .get method on a trombi Database obj
        self.get(db).get(_id, _cb, **ka)

    def view(self, db, resource, cb, **ka):
        """
        Convenience method to fetch the results of a view from a specific
        database.
        Parameters
        ==========
        db -> db name as str
        resource -> string of the resource 'designDocName/resourceName'
            or '/resourceName' to hit the special view '_alldocs'
        cb -> function ptr to callback
        ka -> keyword arguments
        """
        des, res = resource.split('/')
        # note, this is calling the .view method on a trombi Database obj
        self.get(db).view(des, res, cb, **ka)

    def save(self, db, data, callback=None):
        """saves dict to couchdb"""
        if not callback: callback = self._generic_cb
        # FIXME: should this look for _rev also?
        if '_id' in data: 
            self.get(db).set(data['_id'], data, callback)
        else: 
            self.get(db).set(data, callback)

    def _generic_cb(self, doc):
        if doc.error:
            logging.error("ERROR:" + doc.msg)

    def delete(self, db, data, callback=None):
        """
        Remove doc from database.

        data requires an _id and _rev or an exception is thrown.
        """
        if not callback: callback = self._generic_cb
        if '_id' in data and '_rev' in data:
            self.get(db).delete(data, callback)
        else: raise CushionException(
                "record missing _id and _rev, can't delete"
                )


class CushionDBMixin(object):

    def prepare(self):
        super(CushionDBMixin, self).prepare()

    def db_setup(self, dbname, uri, callback, **kwa):
        self.db_default = dbname
        self.cushion = Cushion.new(uri, io_loop=kwa.get('io_loop'))
        self.cushion.open(
            dbname,
            callback=callback,
            create=kwa.get('create') )

    def db_ignored_cb(self, *a, **ka):
        """
        do as much nothing as possible
        """
        pass

    def _db_cb_get(self, callback=None, ignore_cb=False):
        # we should never have a callback AND ignore_cb
        assert(bool(callback) ^ bool(ignore_cb)) # logical xor

        if ignore_cb: callback = self.db_ignored_cb
        return callback

    def db_save(self, data, callback=None, db=None, ignore_cb=False):
        # default to the account database
        if not db: db = self.db_default

        callback = self._db_cb_get(callback, ignore_cb)

        cush = self.cushion
        # if the db's not open, we're going to open the db with the callback
        # being the same way we were called
        if db not in cush: # db's not ready...
            cush.open( db, lambda *a: self.db_save(data, db, callback))
        else:
            cush.save(db, data, callback)

    def db_delete(self, obj, callback, db=None, ignore_cb=False):
        if not db: db = self.db_default

        callback = self._db_cb_get(callback, ignore_cb)

        cush = self.cushion
        if db not in cush: # db's not ready...
            # open the db then call ourselves once it's ready to go
            cush.open(
                db,
                lambda *a: self.db_delete(
                            obj,
                            db,
                            callback=callback,
                            ignore_cb=ignore_cb )
                )
        else: cush.delete(db, obj, callback)

    def db_one(self, key, callback, db=None, **kwargs):
        """
        Retrieve a particular document from couchdb.

          x = yield self.db_one(key, cb, dbname)

        Parameters:
        db <-   name of the db to hit.  If this db isn't in our cushion, we'll
                block until we get that connection.
        key <-  the key of our document, a string.
        callback <- None or a function to call upon completion.
        **  any other remaining kwargs will be passed through to cushion's .one
            call, which passes them to trombi.
        """
        logging.debug("------------- couch 1 -------------")

        # default to the account db
        if not db: db = self.db_default

        cush = self.cushion
        # if the db's not open, we're going to open the db with the callback
        # being the same way we were called
        cush.one(db, key, callback, **kwargs)

    def db_view(self, resource, callback, db=None, **kwargs):
        """
        see comments for db_one
        """
        logging.debug("------------- couch * -------------")

        # default to the account db
        if not db: db = self.db_default

        cush = self.cushion
        # if the db's not open, we're going to open the db with the callback
        # being the same way we were called
        if db not in cush: # db's not ready...
            # open the db then call ourselves once it's ready to go
            cush.open(
                db,
                lambda *a: self.db_view(
                    resource, db, callback, **kwargs )
                )
        else:
            cush.view(db, resource, callback, **kwargs)


########NEW FILE########
__FILENAME__ = route
import tornado.web

class route(object):
    """
    decorates RequestHandlers and builds up a list of routables handlers

    Tech Notes (or "What the *@# is really happening here?")
    --------------------------------------------------------

    Everytime @route('...') is called, we instantiate a new route object which
    saves off the passed in URI.  Then, since it's a decorator, the function is
    passed to the route.__call__ method as an argument.  We save a reference to
    that handler with our uri in our class level routes list then return that
    class to be instantiated as normal.

    Later, we can call the classmethod route.get_routes to return that list of
    tuples which can be handed directly to the tornado.web.Application
    instantiation.

    Example
    -------

    @route('/some/path')
    class SomeRequestHandler(RequestHandler):
        def get(self):
            goto = self.reverse_url('other')
            self.redirect(goto)

    # so you can do myapp.reverse_url('other')
    @route('/some/other/path', name='other')
    class SomeOtherRequestHandler(RequestHandler):
        def get(self):
            goto = self.reverse_url('SomeRequestHandler')
            self.redirect(goto)

    my_routes = route.get_routes()

    Credit
    -------
    Jeremy Kelley - initial work
    Peter Bengtsson - redirects, named routes and improved comments
    Ben Darnell - general awesomeness
    """

    _routes = []

    def __init__(self, uri, name=None):
        self._uri = uri
        self.name = name

    def __call__(self, _handler):
        """gets called when we class decorate"""
        name = self.name or _handler.__name__
        self._routes.append(tornado.web.url(self._uri, _handler, name=name))
        return _handler

    @classmethod
    def get_routes(self):
        return self._routes

# route_redirect provided by Peter Bengtsson via the Tornado mailing list
# and then improved by Ben Darnell.
# Use it as follows to redirect other paths into your decorated handler.
#
#   from routes import route, route_redirect
#   route_redirect('/smartphone$', '/smartphone/')
#   route_redirect('/iphone/$', '/smartphone/iphone/', name='iphone_shortcut')
#   @route('/smartphone/$')
#   class SmartphoneHandler(RequestHandler):
#        def get(self):
#            ...
def route_redirect(from_, to, name=None):
    route._routes.append(tornado.web.url(
        from_,
        tornado.web.RedirectHandler,
        dict(url=to),
        name=name ))


########NEW FILE########
