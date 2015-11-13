__FILENAME__ = client
import sys
import gevent
import time
from gevent import monkey
monkey.patch_all()
import urllib2


def fetch_url(url):
    """ Fetch a URL and return the total amount of time required.
    """
    t0 = time.time()
    try:
        resp = urllib2.urlopen(url)
        resp_code = resp.code
    except urllib2.HTTPError, e:
        resp_code = e.code

    t1 = time.time()
    print("\t@ %5.2fs got response [%d]" % (t1 - t0, resp_code))
    return t1 - t0


def time_fetch_urls(url, num_jobs):
    """ Fetch a URL `num_jobs` times in parallel and return the
        total amount of time required.
    """
    print("Sending %d requests for %s..." % (num_jobs, url))
    t0 = time.time()
    jobs = [gevent.spawn(fetch_url, url) for i in range(num_jobs)]
    gevent.joinall(jobs)
    t1 = time.time()
    print("\t= %5.2fs TOTAL" % (t1 - t0))
    return t1 - t0


if __name__ == '__main__':

    try:
        num_requests = int(sys.argv[1])
    except IndexError:
        num_requests = 5

    # Fetch the URL that blocks with a `time.sleep`
    t0 = time_fetch_urls("http://localhost:8000/sleep/python/", num_requests)

    # Fetch the URL that blocks with a `pg_sleep`
    t1 = time_fetch_urls("http://localhost:8000/sleep/postgres/", num_requests)

    print("------------------------------------------")
    print("SUM TOTAL = %.2fs" % (t0 + t1))

########NEW FILE########
__FILENAME__ = config
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://localhost/fsppgg_test'
SQLALCHEMY_ECHO = False
SECRET_KEY = '\xfb\x12\xdf\xa1@i\xd6>V\xc0\xbb\x8fp\x16#Z\x0b\x81\xeb\x16'
DEBUG = True

########NEW FILE########
__FILENAME__ = server
import sys
import os
import time
from flask import Flask, jsonify
from flask.ext.sqlalchemy import SQLAlchemy


# Optionally, set up psycopg2 & SQLAlchemy to be greenlet-friendly.
# Note: psycogreen does not really monkey patch psycopg2 in the
# manner that gevent monkey patches socket.
#
if "PSYCOGREEN" in os.environ:

    # Do our monkey patching
    #
    from gevent.monkey import patch_all
    patch_all()
    from psycogreen.gevent import patch_psycopg
    patch_psycopg()

    using_gevent = True
else:
    using_gevent = False


# Create our Flask app
#
app = Flask(__name__)
app.config.from_pyfile('config.py')


# Create our Flask-SQLAlchemy instance
#
db = SQLAlchemy(app)
if using_gevent:

    # Assuming that gevent monkey patched the builtin
    # threading library, we're likely good to use
    # SQLAlchemy's QueuePool, which is the default
    # pool class.  However, we need to make it use
    # threadlocal connections
    #
    #
    db.engine.pool._use_threadlocal = True


class Todo(db.Model):
    """ Small example model just to show you that SQLAlchemy is
        doing everything it should be doing.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(60))
    done = db.Column(db.Boolean)
    priority = db.Column(db.Integer)

    def as_dict(self):
        """ Return an individual Todo as a dictionary.
        """
        return {
            'id': self.id,
            'title': self.title,
            'done': self.done,
            'priority': self.priority
        }

    @classmethod
    def jsonify_all(cls):
        """ Returns all Todo instances in a JSON
            Flask response.
        """
        return jsonify(todos=[todo.as_dict() for todo in cls.query.all()])


@app.route('/sleep/postgres/')
def sleep_postgres():
    """ This handler asks Postgres to sleep for 5s and will
        block for 5s unless psycopg2 is set up (above) to be
        gevent-friendly.
    """
    db.session.execute('SELECT pg_sleep(5)')
    return Todo.jsonify_all()


@app.route('/sleep/python/')
def sleep_python():
    """ This handler sleeps for 5s and will block for 5s unless
        gunicorn is using the gevent worker class.
    """
    time.sleep(5)
    return Todo.jsonify_all()


# Create the tables and populate it with some dummy data
#
def create_data():
    """ A helper function to create our tables and some Todo objects.
    """
    db.create_all()
    todos = []
    for i in range(50):
        todo = Todo(
            title="Slave for the man {0}".format(i),
            done=(i % 2 == 0),
            priority=(i % 5)
        )
        todos.append(todo)
    db.session.add_all(todos)
    db.session.commit()


if __name__ == '__main__':

    if '-c' in sys.argv:
        create_data()
    else:
        app.run()

########NEW FILE########
