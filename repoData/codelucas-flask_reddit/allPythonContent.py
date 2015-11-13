__FILENAME__ = app_config
#!/usr/bin/env python2.7
"""
app_config.py will be storing all the module configs.
Here the db uses mysql.
"""

import os
_basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = False

ADMINS = frozenset(['your_email_here@email.com'])
SECRET_KEY = ''

SQLALCHEMY_DATABASE_URI = 'DATABASE://USERNAME:PASSWORD@localhost/YOUR_DB_NAME'
DATABASE_CONNECT_OPTIONS = {}

CSRF_ENABLED = True
CSRF_SESSION_KEY = ""

# customize and add the blow if you'd like to use recaptcha
RECAPTCHA_USE_SSL = False
RECAPTCHA_PUBLIC_KEY = ''
RECAPTCHA_PRIVATE_KEY = ''
RECAPTCHA_OPTIONS = {'theme': 'white'}

BRAND = "reddit"
DOMAIN = "YOUR_DOMAIN_HERE"
ROOT_URL = "http://YOUR_URL_HERE"

STATIC_ROOT = "/path/to/your/static/root/"
STATIC_URL = ROOT_URL + "/static/"

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
"""
All view code for async get/post calls towards the server
must be contained in this file.
"""
from flask import (Blueprint, request, render_template, flash, g,
        session, redirect, url_for, jsonify, abort)
from werkzeug import check_password_hash, generate_password_hash

from flask_reddit import db
from flask_reddit.users.models import User
from flask_reddit.threads.models import Thread, Comment
from flask_reddit.users.decorators import requires_login

mod = Blueprint('apis', __name__, url_prefix='/apis')

@mod.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])

@mod.route('/comments/submit/', methods=['POST'])
@requires_login
def submit_comment():
    """
    Submit comments via ajax
    """
    thread_id = int(request.form['thread_id'])
    comment_text = request.form['comment_text']
    comment_parent_id = request.form['parent_id'] # empty means none

    if not comment_text:
        abort(404)

    thread = Thread.query.get_or_404(int(thread_id))
    comment = thread.add_comment(comment_text, comment_parent_id,
            g.user.id)

    return jsonify(comment_text=comment.text, date=comment.pretty_date(),
            username=g.user.username, comment_id=comment.id,
            margin_left=comment.get_margin_left())

@mod.route('/threads/vote/', methods=['POST'])
@requires_login
def vote_thread():
    """
    Submit votes via ajax
    """
    thread_id = int(request.form['thread_id'])
    user_id = g.user.id

    if not thread_id:
        abort(404)

    thread = Thread.query.get_or_404(int(thread_id))
    vote_status = thread.vote(user_id=user_id)
    return jsonify(new_votes=thread.votes, vote_status=vote_status)

@mod.route('/comments/vote/', methods=['POST'])
@requires_login
def vote_comment():
    """
    Submit votes via ajax
    """
    comment_id = int(request.form['comment_id'])
    user_id = g.user.id

    if not comment_id:
        abort(404)

    comment = Comment.query.get_or_404(int(comment_id))
    comment.vote(user_id=user_id)
    return jsonify(new_votes=comment.get_votes())


########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
"""
"""
from flask import (Blueprint, request, render_template, flash,
    g, session, redirect, url_for)
from werkzeug import check_password_hash, generate_password_hash

from flask_reddit import db
from flask_reddit import search as search_module # don't override function name
from flask_reddit.users.forms import RegisterForm, LoginForm
from flask_reddit.users.models import User
from flask_reddit.threads.models import Thread
from flask_reddit.subreddits.models import Subreddit
from flask_reddit.users.decorators import requires_login

mod = Blueprint('frontends', __name__, url_prefix='')

@mod.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])

def home_subreddit():
    return Subreddit.query.get_or_404(1)

def get_subreddits():
    """
    important and widely imported method because a list of
    the top 30 subreddits are present on every page in the sidebar
    """
    subreddits = Subreddit.query.filter(Subreddit.id != 1)[:25]
    return subreddits

def process_thread_paginator(trending=False, rs=None, subreddit=None):
    """
    abstracted because many sources pull from a thread listing
    source (subreddit permalink, homepage, etc)
    """
    threads_per_page = 15
    cur_page = request.args.get('page') or 1
    cur_page = int(cur_page)
    thread_paginator = None

    # if we are passing in a resultset, that means we are just looking to
    # quickly paginate some arbitrary data, no sorting
    if rs:
        thread_paginator = rs.paginate(cur_page, per_page=threads_per_page,
            error_out=True)
        return thread_paginator

    # sexy line of code :)
    base_query = subreddit.threads if subreddit else Thread.query

    if trending:
        thread_paginator = base_query.order_by(db.desc(Thread.votes)).\
        paginate(cur_page, per_page=threads_per_page, error_out=True)
    else:
        thread_paginator = base_query.order_by(db.desc(Thread.hotness)).\
                paginate(cur_page, per_page=threads_per_page, error_out=True)
    return thread_paginator

#@mod.route('/<regex("trending"):trending>/')
@mod.route('/')
def home(trending=False):
    """
    If not trending we order by creation date
    """
    trending = True if request.args.get('trending') else False
    subreddits = get_subreddits()
    thread_paginator = process_thread_paginator(trending)

    return render_template('home.html', user=g.user,
            subreddits=subreddits, cur_subreddit=home_subreddit(),
            thread_paginator=thread_paginator)

@mod.route('/search/', methods=['GET'])
def search():
    """
    Allows users to search threads and comments
    """
    query = request.args.get('query')
    rs = search_module.search(query, orderby='creation', search_title=True,
            search_text=True, limit=100)

    thread_paginator = process_thread_paginator(rs=rs)
    rs = rs.all()
    num_searches = len(rs)
    subreddits = get_subreddits()

    return render_template('home.html', user=g.user,
            subreddits=subreddits, cur_subreddit=home_subreddit(),
            thread_paginator=thread_paginator, num_searches=num_searches)

@mod.route('/login/', methods=['GET', 'POST'])
def login():
    """
    We had to do some extra work to route the user back to
    his or her original place before logging in
    """
    if g.user:
        return redirect(url_for('frontends.home'))

    next = ''
    if request.method == 'GET':
        if 'next' in request.args:
            next = request.args['next']

    form = LoginForm(request.form)
    # make sure data is valid, but doesn't validate password is right
    if form.validate_on_submit():
        # continue where we left off if so
        user = User.query.filter_by(email=form.email.data).first()
        # we use werzeug to validate user's password
        if user and check_password_hash(user.password, form.password.data):
            # the session can't be modified as it's signed,
            # it's a safe place to store the user id
            session['user_id'] = user.id

            if 'next' in request.form and request.form['next']:
                return redirect(request.form['next'])
            return redirect(url_for('frontends.home'))

        flash('Wrong email or password', 'danger')
    return render_template("login.html", form=form, next=next)

@mod.route('/logout/', methods=['GET', 'POST'])
@requires_login
def logout():
    session.pop('user_id', None)
    return redirect(url_for('frontends.home'))

@mod.route('/register/', methods=['GET', 'POST'])
def register():
    """
    """
    next = ''
    if request.method == 'GET':
        if 'next' in request.args:
            next = request.args['next']

    form = RegisterForm(request.form)
    if form.validate_on_submit():
        # create an user instance not yet stored in the database
        user = User(username=form.username.data, email=form.email.data, \
                password=generate_password_hash(form.password.data))
        # Insert the record in our database and commit it
        db.session.add(user)
        db.session.commit()
        # Log the user in, as he now has an id
        session['user_id'] = user.id

        flash('thanks for signing up!', 'success')
        if 'next' in request.form and request.form['next']:
            return redirect(request.form['next'])
        return redirect(url_for('frontends.home'))

    return render_template("register.html", form=form, next=next)


########NEW FILE########
__FILENAME__ = media
# -*- coding: utf-8 -*-
"""
All code for scraping images and videos from posted
links go in this file.
"""
import BeautifulSoup
import requests
from urlparse import urlparse, urlunparse, urljoin

img_extensions = ['jpg', 'jpeg', 'gif', 'png', 'bmp']

def make_abs(url, img_src):
    domain = urlparse(url).netloc
    scheme = urlparse(url).scheme
    baseurl = scheme + '://' + domain
    return urljoin(baseurl, img_src)

def clean_url(url):
    frag = urlparse(url)
    frag = frag._replace(query='', fragment='')
    return urlunparse(frag)

def get_top_img(url, timeout=4):
    """
    Nothing fancy here, we merely check if the page author
    set a designated image or if the url itself is an image.

    This method could be mutch better but we are favoring ease
    of installation and simplicity of speed.
    """
    if not url:
        return None

    url = clean_url(url)

    # if the url is referencing an img itself, return it
    if url.split('.')[-1].lower() in img_extensions:
        return url
    try:
        html = requests.get(url, timeout=timeout).text
        soup = BeautifulSoup.BeautifulSoup(html)

        og_image = (soup.find('meta', property='og:image') or
                    soup.find('meta', attrs={'name': 'og:image'}))

        if og_image and og_image['content']:
            src_url = og_image['content']
            return make_abs(url, src_url)

        # <link rel="image_src" href="http://...">
        thumbnail_spec = soup.find('link', rel='image_src')
        if thumbnail_spec and thumbnail_spec['href']:
            src_url = thumbnail_spec['href']
            return make_abs(url, src_url)

    except Exception, e:
        print 'FAILED WHILE EXTRACTING THREAD IMG', str(e)
        return None

    return None

########NEW FILE########
__FILENAME__ = search
# -*- coding: utf-8 -*-
"""
Simple module for searching the sql-alchemy database based
on user queries.
"""
from flask_reddit.threads.models import Thread, Comment
from flask_reddit import db

def search(query, orderby='creation', filter_user=None, search_title=True,
            search_text=True, subreddit=None, limit=100):
    """
    search for threads (and maybe comments in the future)
    """
    if not query:
        return []
    query = query.strip()
    base_query = '%' + query + '%'

    base_qs = Thread.query

    title_clause = Thread.title.like(base_query) if search_title else False
    text_clause = Thread.text.like(base_query) if search_text else False
    # TODO: Searching by subreddit requires joining, leave out for now.
    # subreddit_clause = Thread.subreddit.name.like(subreddit.name) if subreddit else False

    or_clause = db.or_(title_clause, text_clause)

    base_qs = base_qs.filter(or_clause)

    if orderby == 'creation':
        base_qs = base_qs.order_by(db.desc(Thread.created_on))
    elif orderby == 'title':
        base_qs = base_qs.order_by(Thread.title)
    elif orderby == 'numb_comments':
        pass

    base_qs = base_qs.limit(limit)
    return base_qs

########NEW FILE########
__FILENAME__ = constants
# -*- coding: utf-8 -*-

# For simplicity, these values are shared among both threads and comments.
MAX_THREADS = 1000
MAX_NAME = 50
MAX_DESCRIPTION = 3000
MAX_ADMINS = 2

# status
DEAD = 0
ALIVE = 1

STATUS = {
    DEAD: 'dead',
    ALIVE: 'alive',
}


########NEW FILE########
__FILENAME__ = decorators
# -*- coding: utf-8 -*-

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
"""
"""
from flask_reddit.threads import constants as THREAD
from flask.ext.wtf import Form
from wtforms import TextField, TextAreaField
from wtforms.validators import Required, URL, Length

class SubmitForm(Form):
    name = TextField('Name your community!', [Required()])
    desc = TextAreaField('Description of subreddit!', [Required()])

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
"""
All database abstractions for subreddits go in this file.

I had to add the Subreddit model in manually via SQL, here were
my commands:

CREATE TABLE `subreddits_subreddit` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) DEFAULT NULL,
  `desc` varchar(3000) DEFAULT NULL,
  `admin_id` int(11) DEFAULT NULL,
  `created_on` datetime DEFAULT NULL,
  `updated_on` datetime DEFAULT NULL,
  `status` smallint(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`admin_id`),
  UNIQUE KEY `name` (`name`),
  CONSTRAINT `subreddits_subreddit_ibfk_1` FOREIGN KEY (`admin_id`) REFERENCES `users_user` (`id`)
);

ALTER TABLE threads_thread ADD subreddit_id INT(11) DEFAULT 0;
alter table threads_thread drop subreddit_id;
alter table threads_thread add subreddit_id int(11) not null default 0;
insert into subreddits_subreddit (name, `desc`, admin_id) values('first_subreddit',
    'This is to get the sql up and running', 1);

ALTER TABLE threads_thread ADD CONSTRAINT threads_thread_ibfk_2 FOREIGN KEY (subreddit_id)
    references subreddits_subreddit(id);
"""
from flask_reddit import db
from flask_reddit.subreddits import constants as SUBREDDIT
from flask_reddit.threads.models import Thread
from flask_reddit import utils
import datetime

class Subreddit(db.Model):
    """
    """
    __tablename__ = 'subreddits_subreddit'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(SUBREDDIT.MAX_NAME), unique=True)
    desc = db.Column(db.String(SUBREDDIT.MAX_DESCRIPTION))

    admin_id = db.Column(db.Integer, db.ForeignKey('users_user.id'))

    created_on = db.Column(db.DateTime, default=db.func.now())
    updated_on = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    threads = db.relationship('Thread', backref='subreddit', lazy='dynamic')
    status = db.Column(db.SmallInteger, default=SUBREDDIT.ALIVE)

    def __init__(self, name, desc, admin_id):
        self.name = name
        self.desc = desc
        self.admin_id = admin_id

    def __repr__(self):
        return '<Subreddit %r>' % (self.name)

    def get_threads(self, order_by='timestamp'):
        """
        default order by timestamp
        """
        if order_by == 'timestamp':
            return self.threads.order_by(db.desc(Thread.created_on)).\
                all()[:SUBREDDIT.MAX_THREADS]
        else:
            return self.threads.order_by(db.desc(Thread.created_on)).\
                all()[:SUBREDDIT.MAX_THREADS]

    def get_status(self):
        """
        returns string form of status, 0 = 'dead', 1 = 'alive'
        """
        return SUBREDDIT.STATUS[self.status]

    def get_age(self):
        """
        returns the raw age of this subreddit in seconds
        """
        return (self.created_on - datetime.datetime(1970, 1, 1)).total_seconds()

    def pretty_date(self, typeof='created'):
        """
        returns a humanized version of the raw age of this subreddit,
        eg: 34 minutes ago versus 2040 seconds ago.
        """
        if typeof == 'created':
            return utils.pretty_date(self.created_on)
        elif typeof == 'updated':
            return utils.pretty_date(self.updated_on)
    """
    def add_thread(self, comment_text, comment_parent_id, user_id):
        if len(comment_parent_id) > 0:
            comment_parent_id = int(comment_parent_id)
            comment = Comment(thread_id=self.id, user_id=user_id,
                    text=comment_text, parent_id=comment_parent_id)
        else:
            comment = Comment(thread_id=self.id, user_id=user_id,
                    text=comment_text)

        db.session.add(comment)
        db.session.commit()
        comment.set_depth()
        return comment
    """

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
"""
"""
from flask import (Blueprint, request, render_template, flash, g,
        session, redirect, url_for, abort)
from flask_reddit.frontends.views import get_subreddits, process_thread_paginator
from flask_reddit.subreddits.forms import SubmitForm
from flask_reddit.subreddits.models import Subreddit
from flask_reddit.threads.models import Thread
from flask_reddit.users.models import User
from flask_reddit import db

mod = Blueprint('subreddits', __name__, url_prefix='/r')

#######################
### Subreddit Views ###
#######################

@mod.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])

def meets_subreddit_criterea(subreddit):
    return True

@mod.route('/subreddits/submit/', methods=['GET', 'POST'])
def submit():
    """
    """
    if g.user is None:
        flash('You must be logged in to submit subreddits!', 'danger')
        return redirect(url_for('frontends.login', next=request.path))

    form = SubmitForm(request.form)
    user_id = g.user.id

    if form.validate_on_submit():
        name = form.name.data.strip()
        desc = form.desc.data.strip()

        subreddit = Subreddit.query.filter_by(name=name).first()
        if subreddit:
            flash('subreddit already exists!', 'danger')
            return render_template('subreddits/submit.html', form=form, user=g.user,
                subreddits=get_subreddits())
        new_subreddit = Subreddit(name=name, desc=desc, admin_id=user_id)

        if not meets_subreddit_criterea(subreddit):
            return render_template('subreddits/submit.html', form=form, user=g.user,
                subreddits=get_subreddits())

        db.session.add(new_subreddit)
        db.session.commit()

        flash('Thanks for starting a community! Begin adding posts to your community\
                by clicking the red button to the right.', 'success')
        return redirect(url_for('subreddits.permalink', subreddit_name=new_subreddit.name))
    return render_template('subreddits/submit.html', form=form, user=g.user,
            subreddits=get_subreddits())

@mod.route('/delete/', methods=['GET', 'POST'])
def delete():
    """
    """
    pass

@mod.route('/subreddits/view_all/', methods=['GET'])
def view_all():
    """
    """
    return render_template('subreddits/all.html', user=g.user,
            subreddits=Subreddit.query.all())

@mod.route('/<subreddit_name>/', methods=['GET'])
def permalink(subreddit_name=""):
    """
    """
    subreddit = Subreddit.query.filter_by(name=subreddit_name).first()
    if not subreddit:
        abort(404)

    trending = True if request.args.get('trending') else False
    thread_paginator = process_thread_paginator(trending=trending, subreddit=subreddit)
    subreddits = get_subreddits()

    return render_template('home.html', user=g.user, thread_paginator=thread_paginator,
        subreddits=subreddits, cur_subreddit=subreddit)


########NEW FILE########
__FILENAME__ = constants
# -*- coding: utf-8 -*-

# For simplicity, these values are shared among both threads and comments.
MAX_TITLE = 300
MAX_BODY = 3000
MAX_LINK = 250

MAX_COMMENTS = 500
MAX_DEPTH = 10

# thread & comment status
DEAD = 0
ALIVE = 1

STATUS = {
    DEAD: 'dead',
    ALIVE: 'alive',
}


########NEW FILE########
__FILENAME__ = decorators
# -*- coding: utf-8 -*-

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
"""
"""
from flask_reddit.threads import constants as THREAD
from flask.ext.wtf import Form
from wtforms import TextField, TextAreaField
from wtforms.validators import Required, URL, Length

class SubmitForm(Form):
    title = TextField('Title', [Required()])
    text = TextAreaField('Body text') # [Length(min=5, max=THREAD.MAX_BODY)]
    link = TextField('Link', [URL(require_tld=True,
        message="That is not a valid link url!")])

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
"""
All database abstractions for threads and comments
go in this file.

CREATE TABLE `thread_upvotes` (
  `user_id` int(11) DEFAULT NULL,
  `thread_id` int(11) DEFAULT NULL,
  KEY `user_id` (`user_id`),
  KEY `thread_id` (`thread_id`),
  CONSTRAINT `thread_upvotes_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users_user` (`id`),
  CONSTRAINT `thread_upvotes_ibfk_2` FOREIGN KEY (`thread_id`) REFERENCES `threads_thread` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1

CREATE TABLE `comment_upvotes` (
  `user_id` int(11) DEFAULT NULL,
  `comment_id` int(11) DEFAULT NULL,
  KEY `user_id` (`user_id`),
  KEY `comment_id` (`comment_id`),
  CONSTRAINT `comment_upvotes_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users_user` (`id`),
  CONSTRAINT `comment_upvotes_ibfk_2` FOREIGN KEY (`comment_id`) REFERENCES `threads_comment` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 |
"""
from flask_reddit import db
from flask_reddit.threads import constants as THREAD
from flask_reddit import utils
from flask_reddit import media
from math import log
import datetime

thread_upvotes = db.Table('thread_upvotes',
    db.Column('user_id', db.Integer, db.ForeignKey('users_user.id')),
    db.Column('thread_id', db.Integer, db.ForeignKey('threads_thread.id'))
)

comment_upvotes = db.Table('comment_upvotes',
    db.Column('user_id', db.Integer, db.ForeignKey('users_user.id')),
    db.Column('comment_id', db.Integer, db.ForeignKey('threads_comment.id'))
)

class Thread(db.Model):
    """
    We will mimic reddit, with votable threads. Each thread may have either
    a body text or a link, but not both.
    """
    __tablename__ = 'threads_thread'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(THREAD.MAX_TITLE))
    text = db.Column(db.String(THREAD.MAX_BODY), default=None)
    link = db.Column(db.String(THREAD.MAX_LINK), default=None)
    thumbnail = db.Column(db.String(THREAD.MAX_LINK), default=None)

    user_id = db.Column(db.Integer, db.ForeignKey('users_user.id'))
    subreddit_id = db.Column(db.Integer, db.ForeignKey('subreddits_subreddit.id'))

    created_on = db.Column(db.DateTime, default=db.func.now())
    updated_on = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    comments = db.relationship('Comment', backref='thread', lazy='dynamic')

    status = db.Column(db.SmallInteger, default=THREAD.ALIVE)

    votes = db.Column(db.Integer, default=1)
    hotness = db.Column(db.Float(15,6), default=0.00)

    def __init__(self, title, text, link, user_id, subreddit_id):
        self.title = title
        self.text = text
        self.link = link
        self.user_id = user_id
        self.subreddit_id = subreddit_id
        self.extract_thumbnail()

    def __repr__(self):
        return '<Thread %r>' % (self.title)

    def get_comments(self, order_by='timestamp'):
        """
        default order by timestamp
        return only top levels!
        """
        if order_by == 'timestamp':
            return self.comments.filter_by(depth=1).\
                order_by(db.desc(Comment.created_on)).all()[:THREAD.MAX_COMMENTS]
        else:
            return self.comments.filter_by(depth=1).\
                order_by(db.desc(Comment.created_on)).all()[:THREAD.MAX_COMMENTS]

    def get_status(self):
        """
        returns string form of status, 0 = 'dead', 1 = 'alive'
        """
        return THREAD.STATUS[self.status]

    def get_age(self):
        """
        returns the raw age of this thread in seconds
        """
        return (self.created_on - datetime.datetime(1970, 1, 1)).total_seconds()

    def get_hotness(self):
        """
        returns the reddit hotness algorithm (votes/(age^1.5))
        """
        order = log(max(abs(self.votes), 1), 10) # Max/abs are not needed in our case
        seconds = self.get_age() - 1134028003
        return round(order + seconds / 45000, 6)

    def set_hotness(self):
        """
        returns the reddit hotness algorithm (votes/(age^1.5))
        """
        self.hotness = self.get_hotness()
        db.session.commit()

    def pretty_date(self, typeof='created'):
        """
        returns a humanized version of the raw age of this thread,
        eg: 34 minutes ago versus 2040 seconds ago.
        """
        if typeof == 'created':
            return utils.pretty_date(self.created_on)
        elif typeof == 'updated':
            return utils.pretty_date(self.updated_on)

    def add_comment(self, comment_text, comment_parent_id, user_id):
        """
        add a comment to this particular thread
        """
        if len(comment_parent_id) > 0:
            # parent_comment = Comment.query.get_or_404(comment_parent_id)
            # if parent_comment.depth + 1 > THREAD.MAX_COMMENT_DEPTH:
            #    flash('You have exceeded the maximum comment depth')
            comment_parent_id = int(comment_parent_id)
            comment = Comment(thread_id=self.id, user_id=user_id,
                    text=comment_text, parent_id=comment_parent_id)
        else:
            comment = Comment(thread_id=self.id, user_id=user_id,
                    text=comment_text)

        db.session.add(comment)
        db.session.commit()
        comment.set_depth()
        return comment

    def get_voter_ids(self):
        """
        return ids of users who voted this thread up
        """
        select = thread_upvotes.select(thread_upvotes.c.thread_id==self.id)
        rs = db.engine.execute(select)
        ids = rs.fetchall() # list of tuples
        return ids

    def has_voted(self, user_id):
        """
        did the user vote already
        """
        select_votes = thread_upvotes.select(
                db.and_(
                    thread_upvotes.c.user_id == user_id,
                    thread_upvotes.c.thread_id == self.id
                )
        )
        rs = db.engine.execute(select_votes)
        return False if rs.rowcount == 0 else True

    def vote(self, user_id):
        """
        allow a user to vote on a thread. if we have voted already
        (and they are clicking again), this means that they are trying
        to unvote the thread, return status of the vote for that user
        """
        already_voted = self.has_voted(user_id)
        vote_status = None
        if not already_voted:
            # vote up the thread
            db.engine.execute(
                thread_upvotes.insert(),
                user_id   = user_id,
                thread_id = self.id
            )
            self.votes = self.votes + 1
            vote_status = True
        else:
            # unvote the thread
            db.engine.execute(
                thread_upvotes.delete(
                    db.and_(
                        thread_upvotes.c.user_id == user_id,
                        thread_upvotes.c.thread_id == self.id
                    )
                )
            )
            self.votes = self.votes - 1
            vote_status = False
        db.session.commit() # for the vote count
        return vote_status

    def extract_thumbnail(self):
        """
        ideally this type of heavy content fetching should be put on a
        celery background task manager or at least a crontab.. instead of
        setting it to run literally as someone posts a thread. but once again,
        this repo is just a simple example of a reddit-like crud application!
        """
        DEFAULT_THUMBNAIL = 'http://reddit.lucasou.com/static/imgs/reddit-camera.png'
        if self.link:
            thumbnail = media.get_top_img(self.link)
        if not thumbnail:
            thumbnail = DEFAULT_THUMBNAIL
        self.thumbnail = thumbnail
        db.session.commit()


class Comment(db.Model):
    """
    This class is here because comments can only be made on threads,
    so it is contained completly in the threads module.

    Note the parent_id and children values. A comment can be commented
    on, so a comment has a one to many relationship with itself.

    Backrefs:
        A comment can refer to its parent thread with 'thread'
        A comment can refer to its parent comment (if exists) with 'parent'
    """
    __tablename__ = 'threads_comment'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(THREAD.MAX_BODY), default=None)

    user_id = db.Column(db.Integer, db.ForeignKey('users_user.id'))
    thread_id = db.Column(db.Integer, db.ForeignKey('threads_thread.id'))

    parent_id = db.Column(db.Integer, db.ForeignKey('threads_comment.id'))
    children = db.relationship('Comment', backref=db.backref('parent',
            remote_side=[id]), lazy='dynamic')

    depth = db.Column(db.Integer, default=1) # start at depth 1

    created_on = db.Column(db.DateTime, default=db.func.now())
    updated_on = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    votes = db.Column(db.Integer, default=1)

    def __repr__(self):
        return '<Comment %r>' % (self.text[:25])

    def __init__(self, thread_id, user_id, text, parent_id=None):
        self.thread_id = thread_id
        self.user_id = user_id
        self.text = text
        self.parent_id = parent_id

    def set_depth(self):
        """
        call after initializing
        """
        if self.parent:
            self.depth = self.parent.depth + 1
            db.session.commit()

    def get_comments(self, order_by='timestamp'):
        """
        default order by timestamp
        """
        if order_by == 'timestamp':
            return self.children.order_by(db.desc(Comment.created_on)).\
                all()[:THREAD.MAX_COMMENTS]
        else:
            return self.comments.order_by(db.desc(Comment.created_on)).\
                all()[:THREAD.MAX_COMMENTS]

    def get_margin_left(self):
        """
        nested comments are pushed right on a page
        -15px is our default margin for top level comments
        """
        margin_left = 15 + ((self.depth-1) * 32)
        margin_left = min(margin_left, 680)
        return str(margin_left) + "px"

    def get_age(self):
        """
        returns the raw age of this thread in seconds
        """
        return (self.created_on - datetime.datetime(1970,1,1)).total_seconds()

    def pretty_date(self, typeof='created'):
        """
        returns a humanized version of the raw age of this thread,
        eg: 34 minutes ago versus 2040 seconds ago.
        """
        if typeof == 'created':
            return utils.pretty_date(self.created_on)
        elif typeof == 'updated':
            return utils.pretty_date(self.updated_on)

    def vote(self, direction):
        """
        """
        pass

    def comment_on(self):
        """
        when someone comments on this particular comment
        """
        pass

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
"""
"""
from flask import (Blueprint, request, render_template, flash, g, session,
    redirect, url_for, abort)
from flask_reddit.threads.forms import SubmitForm
from flask_reddit.threads.models import Thread
from flask_reddit.users.models import User
from flask_reddit.subreddits.models import Subreddit
from flask_reddit.frontends.views import get_subreddits
from flask_reddit import db

mod = Blueprint('threads', __name__, url_prefix='/threads')

#######################
#### Threads Views ####
#######################

@mod.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])

def meets_thread_criterea(thread):
    """
    """
    if not thread.title:
        flash('You must include a title!', 'danger')
        return False
    if not thread.text and not thread.link:
        flash('You must post either body text or a link!', 'danger')
        return False

    dup_link = Thread.query.filter_by(link=thread.link).first()
    if not thread.text and dup_link:
        flash('someone has already posted the same link as you!', 'danger')
        return False

    return True

@mod.route('/<subreddit_name>/submit/', methods=['GET', 'POST'])
def submit(subreddit_name=None):
    """
    """
    if g.user is None:
        flash('You must be logged in to submit posts!', 'danger')
        return redirect(url_for('frontends.login', next=request.path))
    user_id = g.user.id

    subreddit = Subreddit.query.filter_by(name=subreddit_name).first()
    if not subreddit:
        abort(404)

    form = SubmitForm(request.form)
    if form.validate_on_submit():
        title = form.title.data.strip()
        link = form.link.data.strip()
        text = form.text.data.strip()
        thread = Thread(title=title, link=link, text=text,
                user_id=user_id, subreddit_id=subreddit.id)

        if not meets_thread_criterea(thread):
            return render_template('threads/submit.html', form=form, user=g.user,
                cur_subreddit=subreddit.name)

        db.session.add(thread)
        db.session.commit()
        thread.set_hotness()

        flash('thanks for submitting!', 'success')
        return redirect(url_for('subreddits.permalink', subreddit_name=subreddit.name))
    return render_template('threads/submit.html', form=form, user=g.user,
            cur_subreddit=subreddit, subreddits=get_subreddits())

@mod.route('/delete/', methods=['GET', 'POST'])
def delete():
    """
    """
    pass

@mod.route('/edit/', methods=['GET', 'POST'])
def edit():
    """
    """
    pass

@mod.route('/<subreddit_name>/<thread_id>/<path:title>/', methods=['GET', 'POST'])
def thread_permalink(subreddit_name=None, thread_id=None, title=None):
    """
    """
    thread_id = thread_id or -99
    thread = Thread.query.get_or_404(int(thread_id))
    subreddit = Subreddit.query.filter_by(name=subreddit_name).first()
    subreddits = get_subreddits()
    return render_template('threads/permalink.html', user=g.user, thread=thread,
            cur_subreddit=subreddit, subreddits=subreddits)

##########################
##### Comments Views #####
##########################

@mod.route('/comments/submit/', methods=['GET', 'POST'])
def submit_comment():
    """
    """
    pass

@mod.route('/comments/delete/', methods=['GET', 'POST'])
def delete_comment():
    """
    """
    pass

@mod.route('/comments/<comment_id>/', methods=['GET', 'POST'])
def comment_permalink():
    """
    """
    pass


########NEW FILE########
__FILENAME__ = constants
# -*- coding: utf-8 -*-

MAX_THREADS_PER_DAY = 100
MAX_COMMENTS_PER_DAY = 500
MAX_VOTES_PER_DAY = 2000

MAX_USERNAME = 80
MAX_EMAIL = 200
MAX_PASSW = 200

# User status
DEAD = 0
ALIVE = 1

STATUS = {
    DEAD: 'dead',
    ALIVE: 'alive',
}

# User role
ADMIN = 2
STAFF = 1
USER = 0

ROLE = {
    ADMIN: 'admin',
    STAFF: 'staff',
    USER: 'user',
}

########NEW FILE########
__FILENAME__ = decorators
# -*- coding: utf-8 -*-
"""
"""
from functools import wraps
from flask import g, flash, redirect, url_for, request

def requires_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            flash(u'You need to be signed in for this page.')
            return redirect(url_for('frontends.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
"""
"""
from flask.ext.wtf import Form, RecaptchaField
from wtforms import TextField, PasswordField, BooleanField
from wtforms.validators import Required, EqualTo, Email

class LoginForm(Form):
    email = TextField('Email address', [Required(), Email()])
    password = PasswordField('Password', [Required()])

class RegisterForm(Form):
    username = TextField('NickName', [Required()])
    email = TextField('Email address', [Required(), Email()])
    password = PasswordField('Password', [Required()])
    confirm = PasswordField('Repeat Password', [
        Required(),
        EqualTo('password', message='Passwords must match')
    ])
    accept_tos = BooleanField('I accept the Terms of Service.', [Required()])
    recaptcha = RecaptchaField()


########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
"""
"""
from flask_reddit import db
from flask_reddit.users import constants as USER
from flask_reddit.threads.models import thread_upvotes, comment_upvotes

class User(db.Model):
    """
    """
    __tablename__ = 'users_user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(USER.MAX_USERNAME), unique=True)
    email = db.Column(db.String(USER.MAX_EMAIL), unique=True)
    password = db.Column(db.String(USER.MAX_PASSW))
    created_on = db.Column(db.DateTime, default=db.func.now())

    threads = db.relationship('Thread', backref='user', lazy='dynamic')
    comments = db.relationship('Comment', backref='user', lazy='dynamic')
    subreddits = db.relationship('Subreddit', backref='user', lazy='dynamic')

    status = db.Column(db.SmallInteger, default=USER.ALIVE)
    role = db.Column(db.SmallInteger, default=USER.USER)

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password

    def __repr__(self):
        return '<User %r>' % (self.username)

    def get_status(self):
        """
        returns string form of status, 0 = 'dead', 1 = 'alive'
        """
        return USER.STATUS[self.status]

    def get_role(self):
        """
        analogous to above but for roles
        """
        return USER.ROLE[self.role]

    def get_thread_karma(self):
        """
        fetch the number of votes this user has had on his/her threads

        1.) Get id's of all threads by this user

        2.) See how many of those threads also were upvoted but not by
        the person him/her self.
        """
        thread_ids = [t.id for t in self.threads]
        select = thread_upvotes.select(db.and_(
                thread_upvotes.c.thread_id.in_(thread_ids),
                thread_upvotes.c.user_id != self.id
            )
        )
        rs = db.engine.execute(select)
        return rs.rowcount

    def get_comment_karma(self):
        """
        fetch the number of votes this user has had on his/her comments
        """
        comment_ids = [c.id for c in self.comments]
        select = comment_upvotes.select(db.and_(
                comment_upvotes.c.comment_id.in_(comment_ids),
                comment_upvotes.c.user_id != self.id
            )
        )
        rs = db.engine.execute(select)
        return rs.rowcount


########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
"""
"""
from flask import (Blueprint, request, render_template, flash, g, session,
    redirect, url_for, abort)

from flask_reddit import db
from flask_reddit.users.models import User
from flask_reddit.frontends.views import get_subreddits
from flask_reddit.users.decorators import requires_login

mod = Blueprint('users', __name__, url_prefix='/users')

@mod.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])

@mod.route('/<username>/')
def home_page(username=None):
    if not username:
        abort(404)
    user = User.query.filter_by(username=username).first()
    if not user:
        abort(404)
    return render_template('users/profile.html', user=g.user, current_user=user,
            subreddits = get_subreddits())


########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
"""
Utilities for our views and models.
"""
import string
import random
import os
from datetime import datetime

# Instance folder path, make it independent.
INSTANCE_FOLDER_PATH = os.path.join('/tmp', 'instance')

ALLOWED_AVATAR_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

def get_current_time():
    return datetime.utcnow()

def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return  "a minute ago"
        if second_diff < 3600:
            return str( second_diff / 60 ) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str( second_diff / 3600 ) + " hours ago"

    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff/7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff/30) + " months ago"

    return str(day_diff/365) + " years ago"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_AVATAR_EXTENSIONS

def id_generator(size=10, chars=string.ascii_letters + string.digits):
    #return base64.urlsafe_b64encode(os.urandom(size))
    return ''.join(random.choice(chars) for x in range(size))

def make_dir(dir_path):
    try:
        if not os.path.exists(dir_path):
            os.mkdir(dir_path)
    except Exception, e:
        raise e


########NEW FILE########
__FILENAME__ = wsgi
#!/usr/bin/env python
"""
"""
import sys
sys.path.insert(0, '/home/lucas/www/reddit.lucasou.com/reddit-env')

from werkzeug.contrib.fixers import ProxyFix # needed for http server proxies
from werkzeug.debug import DebuggedApplication

from flask_reddit import app # as application

app.wsgi_app = ProxyFix(app.wsgi_app) # needed for http server proxies
application = DebuggedApplication(app, True)


########NEW FILE########
__FILENAME__ = kickstart
#!/usr/bin/env python2.7
"""
This script instantiates critical components of our webapps.
We need at least one home subreddit to get things going.
We also need a first user to admin our first subreddit.
"""
import os
import sys
import readline
from pprint import pprint

from flask import *
from werkzeug import check_password_hash, generate_password_hash

sys.path.insert(0, '/home/lucas/www/reddit.lucasou.com/reddit-env/flask_reddit')
from flask_reddit import *
from flask_reddit.users.models import *
from flask_reddit.threads.models import *
from flask_reddit.subreddits.models import *

db.drop_all()
db.create_all()

first_user = User(username='root', email='your_email@gmail.com', \
        password=generate_password_hash('347895237408927419471483204721'))

#db.session.add(first_user)
db.session.commit()

first_subreddit = Subreddit(name='frontpage', desc='Welcome to Reddit! Here is our homepage.',
        admin_id=first_user.id)

db.session.add(first_subreddit)
db.session.commit()

########NEW FILE########
__FILENAME__ = set_hotness_all
#!/usr/bin/env python2.7
"""
"""
import os
import sys
sys.path.insert(0, '/home/lucas/www/reddit.lucasou.com/reddit-env/flask_reddit')
import readline
from pprint import pprint

from flask import *
from flask_reddit import *

from flask_reddit.users.models import *
from flask_reddit.threads.models import *
from flask_reddit.subreddits.models import *
from flask_reddit.threads.models import thread_upvotes, comment_upvotes

threads = Thread.query.all()
for thread in threads:
    thread.set_hotness()

import time
print 'Hotness values have been computed for all threads without error on', \
    time.strftime("%H:%M:%S"), \
    time.strftime("%d/%m/%Y")

########NEW FILE########
__FILENAME__ = shell
#!/usr/bin/env python2.7
"""
/shell.py will allow you to get a console and enter commands within your flask environment.
"""
import os
import sys
import readline
from pprint import pprint

from flask import *

sys.path.insert(0, '/home/lucas/www/reddit.lucasou.com/reddit-env/flask_reddit')
from flask_reddit import *
from flask_reddit.users.models import *
from flask_reddit.threads.models import *
from flask_reddit.subreddits.models import *
from flask_reddit.threads.models import thread_upvotes, comment_upvotes

os.environ['PYTHONINSPECT'] = 'True'

########NEW FILE########
__FILENAME__ = gunicorn_config
# Refer to the following link for help:
# http://docs.gunicorn.org/en/latest/settings.html
command = '/home/lucas/www/reddit.lucasou.com/reddit-env/bin/gunicorn'
pythonpath = '/home/lucas/www/reddit.lucasou.com/reddit-env/flask_reddit'
bind = '127.0.0.1:8040'
workers = 1
user = 'lucas'
accesslog = '/home/lucas/logs/reddit.lucasou.com/gunicorn-access.log'
errorlog = '/home/lucas/logs/reddit.lucasou.com/gunicorn-error.log'

########NEW FILE########
