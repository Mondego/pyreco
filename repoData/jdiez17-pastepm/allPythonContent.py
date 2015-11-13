__FILENAME__ = app
from flask import Flask, render_template, request, flash, redirect, url_for, send_from_directory
from flask.ext.sqlalchemy import SQLAlchemy

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

from pastepm.database import db_session
from pastepm.views import PastePost, PasteViewWithExtension, PasteViewWithoutExtension, RawView, ForkView
from pastepm.views import RegisterView
from pastepm.views import PayPalStart, PayPalConfirm, PayPalDo, PayPalStatus
from pastepm.config import config

import os

app = Flask(__name__)

@app.context_processor
def utility_processor():
    def do_highlight(language, code, lines=True):
        lex = get_lexer_by_name(language, stripall=False)
        formatter = HtmlFormatter(linenos=lines, cssclass="source")
        code = highlight(code, lex, formatter)

        return code 

    def get_style(style="default"):
        return HtmlFormatter(style=style).get_style_defs('.highlight')

    return {'highlight': do_highlight, 'get_style': get_style}

@app.teardown_request
def shutdown_session(exception=None):
    db_session.remove()

@app.route("/")
def index():
    return render_template("index.html") 

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
        'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.errorhandler(404)
def notfound(e):
    return redirect('/')

@app.errorhandler(500)
def internal_server_error(e):
    return redirect('/')

url_mapping = {
    'post': {
        'url': '/post', 
        'cls': PastePost
    },
    'view': {
        'url': '/<string:id>.<string:extension>', 
        'cls': PasteViewWithExtension
    },
    'raw': {
        'url': '/raw/<string:id>',
        'cls': RawView
    },
    'fork': {
        'url': '/fork/<string:id>',
        'cls': ForkView 
    },
    'view2': {
        'url': '/<string:id>',
        'cls': PasteViewWithoutExtension
    },
    'register': {
        'url': '/register',
        'cls': RegisterView
    },
    'paypal_start': {
        'url': '/paypal/start',
        'cls': PayPalStart
    },
    'paypal_confirm': {
        'url': '/paypal/confirm',
        'cls': PayPalConfirm
    },
    'paypal_do': {
        'url': '/paypal/do/<string:token>',
        'cls': PayPalDo
    },
    'paypal_status': {
        'url': '/paypal/status/<string:token>',
        'cls': PayPalStatus
    }

}

for view in url_mapping:
    mapping = url_mapping[view]
    app.add_url_rule(mapping['url'], view_func=mapping['cls'].as_view(view))

app.secret_key = config.get('security', 'secret_key')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8123, debug=True)


########NEW FILE########
__FILENAME__ = create-db
from pastepm.database import init_db

init_db()

########NEW FILE########
__FILENAME__ = cache
from pastepm.database import using_redis, r
from functools import wraps, partial
import hashlib

def memoize(f=None, time=0):
    if f == None:
        return partial(memoize, time=time)

    @wraps(f)
    def wrap(*args, **kwargs):
        if using_redis:
            h = hashlib.sha1()
            h.update(str(type(args[0])) + str(kwargs))
            key = "pastepm.cache.%s" % h.hexdigest()

            if r.exists(key):
                return r.get(key)
            else:
                result = f(*args, **kwargs)
                if time > 0:
                    r.setex(key, time, result)
                else:
                    r.set(key, result)

                return result
        else:
            return f(*args, **kwargs)

    return wrap

########NEW FILE########
__FILENAME__ = config
from ConfigParser import ConfigParser

config = ConfigParser()
config.readfp(open('config.ini'))

########NEW FILE########
__FILENAME__ = database
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from config import config

user, password, host, database = config.get('database', 'user'), config.get('database', 'password'), config.get('database', 'host'), config.get('database', 'database')

engine = create_engine('mysql://' + user + ':' + password + '@' + host + '/' + database, convert_unicode=True)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

using_redis = config.has_section("redis")
r = None
if using_redis:
    import redis
    r = redis.StrictRedis(config.get('redis', 'host'), int(config.get('redis', 'port')))

def init_db():
    import pastepm.models
    Base.metadata.create_all(bind=engine)

def db_unique(model, **kwargs):
    instance = db_session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        db_session.add(instance)
        db_session.commit()
        return instance

########NEW FILE########
__FILENAME__ = detection
from pastepm.config import config
from pastepm.lib.pyclassifier import Classifier

c = Classifier.from_data(open(config.get('pyclassifier', 'file')))
language_ext_pairs = c.get_classes()

def language_detect(code):
    return c.identify(code)

def get_language_from_extension(extension):
    for language, ext in language_ext_pairs:
        if ext == extension: return language.lower()

########NEW FILE########
__FILENAME__ = classifier
from collections import Counter, defaultdict
from operator import itemgetter
import cPickle
import re
import math

class Classifier(object):
    _training_items = Counter() 
    _data = defaultdict(dict) 

    def __init__(self):
        pass
    
    def _words(self, source):
        #return [filter(str.isalpha, s) for s in source.split()]
        return re.findall('\w+', source)

    def train(self, text, identifier):
        self._training_items[identifier] += 1
        if identifier not in self._data:
            self._data[identifier] = defaultdict(int)

        for w in self._words(text):
            self._data[identifier][w] += 1

        return self._training_items, self._data
    
    def identify(self, text):
        probabilities = dict()
        ws = self._words(text)

        for language in self._training_items:
            # Calculate probabilities for each language

            matches = 0
            for w in ws:
                occurences = self._data[language][w] 
                matches += math.log(self._data[language][w]) if occurences else 0

            probabilities[language] = math.log(self._training_items[language]) + matches
       
        return max(probabilities.iteritems(), key=itemgetter(1))[0]
   
    def export(self, fp):
        cPickle.dump(self, fp, 2)
    
    @classmethod
    def from_data(cls, fp):
        return cPickle.load(fp) 

    def __getstate__(self):
        return {
            'training_items': self._training_items,
            'data': self._data
        }
    
    def __setstate__(self, state):
        self._training_items = state['training_items']
        self._data = state['data']

    def get_classes(self):
        return self._training_items.keys()

########NEW FILE########
__FILENAME__ = models
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref
from pastepm.database import Base, using_redis, r
from pastepm.config import config

import hashlib

class Paste(Base):
    __tablename__ = 'pastes'
    id = Column(Integer, primary_key=True)
    content = Column(Text)

    def __init__(self, content):
        self.content = content

    def __repr__(self):
        return '<Paste id %d: "%s">' % (self.id, self.content)

    def __str__(self):
        return self.content

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(30), unique=True)
    pwdhash = Column(String(40))
    activated = Column(Boolean)

    @staticmethod
    def _get_hash(plain):
        h = hashlib.sha1()
        h.update(plain)

        return h.hexdigest()

    def __init__(self, username, password, payment_enabled=False):
        self.username = username
        self.pwdhash = self._get_hash(password) 
        self.activated = not payment_enabled
       
    def check_password(self, password):
        return self._get_hash(password) == self.pwdhash

class Purchase(Base):
    __tablename__ = 'purchases'
    id = Column(Integer, primary_key=True)
    uid = Column(Integer)
    token = Column(String(40))
    completed = Column(Boolean)
    status = Column(String(20))
    amount = Column(String(10))

    def __init__(self, uid, token, amount):
        self.uid = uid
        self.token = token
        self.amount = amount

        self.completed = False
        self.status = "pending"
    
    def confirm_payment(self):
        self.completed = True
        self.status = "paid"
         

########NEW FILE########
__FILENAME__ = payment
from paypal import PayPalConfig, PayPalInterface

from config import config

using_paypal = config.has_section('paypal')
paypal = None

if using_paypal:
    paypal_config = PayPalConfig(
        API_USERNAME=config.get('paypal', 'username'),
        API_PASSWORD=config.get('paypal', 'password'),
        API_SIGNATURE=config.get('paypal', 'signature')
    )

    paypal = PayPalInterface(config=paypal_config) 

########NEW FILE########
__FILENAME__ = utils
BASE = 24

def encode_id(num):
    def encode_digit(d):
        if d < 10:
            return chr(ord('0') + d)
        else:
            return chr(ord('a') + d - 10)

    (d, m) = divmod(num, BASE)
    if d:
        return encode_id(d) + encode_digit(m)
    else:
        return encode_digit(m)

decode_id = lambda id: int(id, BASE)

########NEW FILE########
__FILENAME__ = views
from flask.views import MethodView
from flask import redirect, url_for, request, render_template, flash, abort, session
from pygments.lexers import guess_lexer, get_lexer_for_filename
from pygments.util import ClassNotFound

from pastepm.models import Paste, User, Purchase
from pastepm.utils import decode_id, encode_id
from pastepm.database import db_session
from pastepm.cache import memoize
from pastepm.payment import using_paypal, paypal

from pastepm.detection import language_detect, get_language_from_extension
import sqlalchemy

class PastePost(MethodView):
    def post(self):
        if "content" not in request.form.keys():
            return redirect(url_for('index')) 

        content = request.form['content']

        p = Paste(content)
        db_session.add(p)
        db_session.commit()

        extension = language_detect(content)[1]

        return url_for('view', id=encode_id(p.id), extension=extension)

class PasteView(MethodView):
    def _get_content(self, id):
        id = decode_id(id)
        paste = Paste.query.get(id)

        return paste

    def _get_lexer(self, filename):
        try:
            lexer = get_lexer_for_filename(filename)
        except ClassNotFound:
            raise

        return lexer

    def _fix_language(self, old_l):
        return {
            'js': 'javascript',
            'c': 'c_cpp',
            'cpp': 'c_cpp',
            'go': 'golang',
            'minid': 'markdown',
            'bash': 'sh'
        }.get(old_l, old_l)

    @memoize(time=3600)
    def get(self, id, extension="txt"):
        paste = self._get_content(id)

        if paste == None:
            abort(404)

        try:
            language = self.get_language(id, paste, extension)
            language = self._fix_language(language)
        except ClassNotFound:
            return redirect(url_for('view', id=id, extension="txt"))

        return render_template("index.html", paste=paste, language=language, id=id)

class ForkView(PasteView):
    @memoize(time=3600)
    def get(self, id, extension="txt"):
        paste = self._get_content(id)
        return render_template("index.html", paste=paste, fork=True)

class RawView(PasteView):
    @memoize(time=3600)
    def get(self, id, extension="txt"):
        paste = self._get_content(id)
        return render_template("raw.html", paste=paste) 

class PasteViewWithExtension(PasteView):
    def get_language(self, id, content, extension="txt"):
        return get_language_from_extension(extension)

class PasteViewWithoutExtension(PasteView):
    def get_language(self, id, content, extension="txt"):
        extension = language_detect(str(content))[1]
        return get_language_from_extension(extension) 

class RegisterView(MethodView):
    def get(self):
        return render_template("register.html", payment=using_paypal)

    def post(self):
        if "username" not in request.form or "password" not in request.form:
            return redirect(url_for('register'))

        username = request.form['username']
        password = request.form['password']

        if len(password) < 4:
            flash("Password must be greater than 4 characters", "error")
            return redirect(url_for('register'))

        try:
            u = User(username, password, using_paypal)
            db_session.add(u)
            db_session.commit()
        except sqlalchemy.exc.IntegrityError:
            flash("Username taken", "error")
            return redirect(url_for('register'))

        if using_paypal:
            session['payment_target_id'] = u.id
            return render_template("checkout.html")
        else:
            return render_template("confirm.html") 

class PayPalStart(MethodView):
    def post(self):
        if not "amt" in request.form:
            flash("You must specify the amount to pay", "error")
            return render_template("checkout.html")

        kw = {
            'amt': request.form['amt'], 
            'currencycode': 'USD',
            'returnurl': url_for('paypal_confirm', _external=True), 
            'cancelurl': url_for('index', _external=True),
            'paymentaction': 'Sale'
        }

        setexp_response = paypal.set_express_checkout(**kw)
        if setexp_response['ACK'] == 'Success':
            p = Purchase(session['payment_target_id'], setexp_response.token, kw['amt'])
            db_session.add(p)
            db_session.commit()

            return redirect(paypal.generate_express_checkout_redirect_url(setexp_response.token))
        else:
            flash("Sorry, something went wrong. Try again.", "error")
            return render_template("checkout.html")

class PayPalConfirm(MethodView):
    def get(self):
       getexp_response = paypal.get_express_checkout_details(token=request.args.get('token', ''))
       
       if getexp_response['ACK'] == 'Success':
           return render_template("confirm_payment.html", token=getexp_response['TOKEN']) 
       else:
           return render_template("paypal_error.html", message=getexp_response['ACK'])

class PayPalDo(MethodView):
    def get(self, token):
        getexp_response = paypal.get_express_checkout_details(token=token)
        kw = {
            'amt': getexp_response['AMT'],
            'currencycode': getexp_response['CURRENCYCODE'],
            'paymentaction': 'Sale',
            'token': token,
            'payerid': getexp_response['PAYERID']
        }
        paypal.do_express_checkout_payment(**kw)

        return redirect(url_for('paypal_status', token=kw['token']))

class PayPalStatus(MethodView):
    def get(self, token):
        checkout_response = paypal.get_express_checkout_details(token=token)

        if checkout_response['CHECKOUTSTATUS'] == 'PaymentActionCompleted':
            p = Purchase.query.filter_by(token=token).one()
            u = User.query.get(p.uid)
            p.confirm_payment()
            u.activated = True
            db_session.commit()

            return render_template("confirm.html")
        else:
            return render_template("paypal_error.html", message=checkout_response['CHECKOUTSTATUS'])


########NEW FILE########
__FILENAME__ = train
from pastepm.lib.pyclassifier import Classifier
import os

c = Classifier()

for dirname, dirnames, filenames in os.walk('training'):
    if os.sep not in dirname: continue

    language = dirname.split(os.sep)[1]
    for f in filenames:
        try:
            extension = f.split(".")[1]
        except IndexError:
            extension = f

        full_path = os.path.join(dirname, f)
        c.train(open(full_path).read(), (language, extension))

output = open('training.pckl', 'w+')
c.export(output)

########NEW FILE########
__FILENAME__ = django-models-base
from __future__ import unicode_literals

import copy
import sys
from functools import update_wrapper
from future_builtins import zip

import django.db.models.manager     # Imported to register signal handler.
from django.conf import settings
from django.core.exceptions import (ObjectDoesNotExist,
    MultipleObjectsReturned, FieldError, ValidationError, NON_FIELD_ERRORS)
from django.core import validators
from django.db.models.fields import AutoField, FieldDoesNotExist
from django.db.models.fields.related import (ManyToOneRel,
    OneToOneField, add_lazy_relation)
from django.db import (router, transaction, DatabaseError,
    DEFAULT_DB_ALIAS)
from django.db.models.query import Q
from django.db.models.query_utils import DeferredAttribute
from django.db.models.deletion import Collector
from django.db.models.options import Options
from django.db.models import signals
from django.db.models.loading import register_models, get_model
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import curry
from django.utils.encoding import smart_str, force_unicode
from django.utils.text import get_text_list, capfirst


class ModelBase(type):
    """
    Metaclass for all models.
    """
    def __new__(cls, name, bases, attrs):
        super_new = super(ModelBase, cls).__new__
        parents = [b for b in bases if isinstance(b, ModelBase)]
        if not parents:
            # If this isn't a subclass of Model, don't do anything special.
            return super_new(cls, name, bases, attrs)

        # Create the class.
        module = attrs.pop('__module__')
        new_class = super_new(cls, name, bases, {'__module__': module})
        attr_meta = attrs.pop('Meta', None)
        abstract = getattr(attr_meta, 'abstract', False)
        if not attr_meta:
            meta = getattr(new_class, 'Meta', None)
        else:
            meta = attr_meta
        base_meta = getattr(new_class, '_meta', None)

        if getattr(meta, 'app_label', None) is None:
            # Figure out the app_label by looking one level up.
            # For 'django.contrib.sites.models', this would be 'sites'.
            model_module = sys.modules[new_class.__module__]
            kwargs = {"app_label": model_module.__name__.split('.')[-2]}
        else:
            kwargs = {}

        new_class.add_to_class('_meta', Options(meta, **kwargs))
        if not abstract:
            new_class.add_to_class('DoesNotExist', subclass_exception(b'DoesNotExist',
                    tuple(x.DoesNotExist
                            for x in parents if hasattr(x, '_meta') and not x._meta.abstract)
                                    or (ObjectDoesNotExist,), module))
            new_class.add_to_class('MultipleObjectsReturned', subclass_exception(b'MultipleObjectsReturned',
                    tuple(x.MultipleObjectsReturned
                            for x in parents if hasattr(x, '_meta') and not x._meta.abstract)
                                    or (MultipleObjectsReturned,), module))
            if base_meta and not base_meta.abstract:
                # Non-abstract child classes inherit some attributes from their
                # non-abstract parent (unless an ABC comes before it in the
                # method resolution order).
                if not hasattr(meta, 'ordering'):
                    new_class._meta.ordering = base_meta.ordering
                if not hasattr(meta, 'get_latest_by'):
                    new_class._meta.get_latest_by = base_meta.get_latest_by

        is_proxy = new_class._meta.proxy

        if getattr(new_class, '_default_manager', None):
            if not is_proxy:
                # Multi-table inheritance doesn't inherit default manager from
                # parents.
                new_class._default_manager = None
                new_class._base_manager = None
            else:
                # Proxy classes do inherit parent's default manager, if none is
                # set explicitly.
                new_class._default_manager = new_class._default_manager._copy_to_model(new_class)
                new_class._base_manager = new_class._base_manager._copy_to_model(new_class)

        # Bail out early if we have already created this class.
        m = get_model(new_class._meta.app_label, name,
                      seed_cache=False, only_installed=False)
        if m is not None:
            return m

        # Add all attributes to the class.
        for obj_name, obj in attrs.items():
            new_class.add_to_class(obj_name, obj)

        # All the fields of any type declared on this model
        new_fields = new_class._meta.local_fields + \
                     new_class._meta.local_many_to_many + \
                     new_class._meta.virtual_fields
        field_names = set([f.name for f in new_fields])

        # Basic setup for proxy models.
        if is_proxy:
            base = None
            for parent in [cls for cls in parents if hasattr(cls, '_meta')]:
                if parent._meta.abstract:
                    if parent._meta.fields:
                        raise TypeError("Abstract base class containing model fields not permitted for proxy model '%s'." % name)
                    else:
                        continue
                if base is not None:
                    raise TypeError("Proxy model '%s' has more than one non-abstract model base class." % name)
                else:
                    base = parent
            if base is None:
                    raise TypeError("Proxy model '%s' has no non-abstract model base class." % name)
            if (new_class._meta.local_fields or
                    new_class._meta.local_many_to_many):
                raise FieldError("Proxy model '%s' contains model fields." % name)
            new_class._meta.setup_proxy(base)
            new_class._meta.concrete_model = base._meta.concrete_model
        else:
            new_class._meta.concrete_model = new_class

        # Do the appropriate setup for any model parents.
        o2o_map = dict([(f.rel.to, f) for f in new_class._meta.local_fields
                if isinstance(f, OneToOneField)])

        for base in parents:
            original_base = base
            if not hasattr(base, '_meta'):
                # Things without _meta aren't functional models, so they're
                # uninteresting parents.
                continue

            parent_fields = base._meta.local_fields + base._meta.local_many_to_many
            # Check for clashes between locally declared fields and those
            # on the base classes (we cannot handle shadowed fields at the
            # moment).
            for field in parent_fields:
                if field.name in field_names:
                    raise FieldError('Local field %r in class %r clashes '
                                     'with field of similar name from '
                                     'base class %r' %
                                        (field.name, name, base.__name__))
            if not base._meta.abstract:
                # Concrete classes...
                base = base._meta.concrete_model
                if base in o2o_map:
                    field = o2o_map[base]
                elif not is_proxy:
                    attr_name = '%s_ptr' % base._meta.module_name
                    field = OneToOneField(base, name=attr_name,
                            auto_created=True, parent_link=True)
                    new_class.add_to_class(attr_name, field)
                else:
                    field = None
                new_class._meta.parents[base] = field
            else:
                # .. and abstract ones.
                for field in parent_fields:
                    new_class.add_to_class(field.name, copy.deepcopy(field))

                # Pass any non-abstract parent classes onto child.
                new_class._meta.parents.update(base._meta.parents)

            # Inherit managers from the abstract base classes.
            new_class.copy_managers(base._meta.abstract_managers)

            # Proxy models inherit the non-abstract managers from their base,
            # unless they have redefined any of them.
            if is_proxy:
                new_class.copy_managers(original_base._meta.concrete_managers)

            # Inherit virtual fields (like GenericForeignKey) from the parent
            # class
            for field in base._meta.virtual_fields:
                if base._meta.abstract and field.name in field_names:
                    raise FieldError('Local field %r in class %r clashes '\
                                     'with field of similar name from '\
                                     'abstract base class %r' % \
                                        (field.name, name, base.__name__))
                new_class.add_to_class(field.name, copy.deepcopy(field))

        if abstract:
            # Abstract base models can't be instantiated and don't appear in
            # the list of models for an app. We do the final setup for them a
            # little differently from normal models.
            attr_meta.abstract = False
            new_class.Meta = attr_meta
            return new_class

        new_class._prepare()
        register_models(new_class._meta.app_label, new_class)

        # Because of the way imports happen (recursively), we may or may not be
        # the first time this model tries to register with the framework. There
        # should only be one class for each model, so we always return the
        # registered version.
        return get_model(new_class._meta.app_label, name,
                         seed_cache=False, only_installed=False)

    def copy_managers(cls, base_managers):
        # This is in-place sorting of an Options attribute, but that's fine.
        base_managers.sort()
        for _, mgr_name, manager in base_managers:
            val = getattr(cls, mgr_name, None)
            if not val or val is manager:
                new_manager = manager._copy_to_model(cls)
                cls.add_to_class(mgr_name, new_manager)

    def add_to_class(cls, name, value):
        if hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)

    def _prepare(cls):
        """
        Creates some methods once self._meta has been populated.
        """
        opts = cls._meta
        opts._prepare(cls)

        if opts.order_with_respect_to:
            cls.get_next_in_order = curry(cls._get_next_or_previous_in_order, is_next=True)
            cls.get_previous_in_order = curry(cls._get_next_or_previous_in_order, is_next=False)
            # defer creating accessors on the foreign class until we are
            # certain it has been created
            def make_foreign_order_accessors(field, model, cls):
                setattr(
                    field.rel.to,
                    'get_%s_order' % cls.__name__.lower(),
                    curry(method_get_order, cls)
                )
                setattr(
                    field.rel.to,
                    'set_%s_order' % cls.__name__.lower(),
                    curry(method_set_order, cls)
                )
            add_lazy_relation(
                cls,
                opts.order_with_respect_to,
                opts.order_with_respect_to.rel.to,
                make_foreign_order_accessors
            )

        # Give the class a docstring -- its definition.
        if cls.__doc__ is None:
            cls.__doc__ = "%s(%s)" % (cls.__name__, ", ".join([f.attname for f in opts.fields]))

        if hasattr(cls, 'get_absolute_url'):
            cls.get_absolute_url = update_wrapper(curry(get_absolute_url, opts, cls.get_absolute_url),
                                                  cls.get_absolute_url)

        signals.class_prepared.send(sender=cls)

class ModelState(object):
    """
    A class for storing instance state
    """
    def __init__(self, db=None):
        self.db = db
        # If true, uniqueness validation checks will consider this a new, as-yet-unsaved object.
        # Necessary for correct validation of new instances of objects with explicit (non-auto) PKs.
        # This impacts validation only; it has no effect on the actual save.
        self.adding = True

class Model(object):
    __metaclass__ = ModelBase
    _deferred = False

    def __init__(self, *args, **kwargs):
        signals.pre_init.send(sender=self.__class__, args=args, kwargs=kwargs)

        # Set up the storage for instance state
        self._state = ModelState()

        # There is a rather weird disparity here; if kwargs, it's set, then args
        # overrides it. It should be one or the other; don't duplicate the work
        # The reason for the kwargs check is that standard iterator passes in by
        # args, and instantiation for iteration is 33% faster.
        args_len = len(args)
        if args_len > len(self._meta.fields):
            # Daft, but matches old exception sans the err msg.
            raise IndexError("Number of args exceeds number of fields")

        fields_iter = iter(self._meta.fields)
        if not kwargs:
            # The ordering of the zip calls matter - zip throws StopIteration
            # when an iter throws it. So if the first iter throws it, the second
            # is *not* consumed. We rely on this, so don't change the order
            # without changing the logic.
            for val, field in zip(args, fields_iter):
                setattr(self, field.attname, val)
        else:
            # Slower, kwargs-ready version.
            for val, field in zip(args, fields_iter):
                setattr(self, field.attname, val)
                kwargs.pop(field.name, None)
                # Maintain compatibility with existing calls.
                if isinstance(field.rel, ManyToOneRel):
                    kwargs.pop(field.attname, None)

        # Now we're left with the unprocessed fields that *must* come from
        # keywords, or default.

        for field in fields_iter:
            is_related_object = False
            # This slightly odd construct is so that we can access any
            # data-descriptor object (DeferredAttribute) without triggering its
            # __get__ method.
            if (field.attname not in kwargs and
                    isinstance(self.__class__.__dict__.get(field.attname), DeferredAttribute)):
                # This field will be populated on request.
                continue
            if kwargs:
                if isinstance(field.rel, ManyToOneRel):
                    try:
                        # Assume object instance was passed in.
                        rel_obj = kwargs.pop(field.name)
                        is_related_object = True
                    except KeyError:
                        try:
                            # Object instance wasn't passed in -- must be an ID.
                            val = kwargs.pop(field.attname)
                        except KeyError:
                            val = field.get_default()
                    else:
                        # Object instance was passed in. Special case: You can
                        # pass in "None" for related objects if it's allowed.
                        if rel_obj is None and field.null:
                            val = None
                else:
                    try:
                        val = kwargs.pop(field.attname)
                    except KeyError:
                        # This is done with an exception rather than the
                        # default argument on pop because we don't want
                        # get_default() to be evaluated, and then not used.
                        # Refs #12057.
                        val = field.get_default()
            else:
                val = field.get_default()
            if is_related_object:
                # If we are passed a related instance, set it using the
                # field.name instead of field.attname (e.g. "user" instead of
                # "user_id") so that the object gets properly cached (and type
                # checked) by the RelatedObjectDescriptor.
                setattr(self, field.name, rel_obj)
            else:
                setattr(self, field.attname, val)

        if kwargs:
            for prop in kwargs.keys():
                try:
                    if isinstance(getattr(self.__class__, prop), property):
                        setattr(self, prop, kwargs.pop(prop))
                except AttributeError:
                    pass
            if kwargs:
                raise TypeError("'%s' is an invalid keyword argument for this function" % kwargs.keys()[0])
        super(Model, self).__init__()
        signals.post_init.send(sender=self.__class__, instance=self)

    def __repr__(self):
        try:
            u = unicode(self)
        except (UnicodeEncodeError, UnicodeDecodeError):
            u = '[Bad Unicode data]'
        return smart_str('<%s: %s>' % (self.__class__.__name__, u))

    def __str__(self):
        if hasattr(self, '__unicode__'):
            return force_unicode(self).encode('utf-8')
        return '%s object' % self.__class__.__name__

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self._get_pk_val() == other._get_pk_val()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._get_pk_val())

    def __reduce__(self):
        """
        Provides pickling support. Normally, this just dispatches to Python's
        standard handling. However, for models with deferred field loading, we
        need to do things manually, as they're dynamically created classes and
        only module-level classes can be pickled by the default path.
        """
        data = self.__dict__
        model = self.__class__
        # The obvious thing to do here is to invoke super().__reduce__()
        # for the non-deferred case. Don't do that.
        # On Python 2.4, there is something weird with __reduce__,
        # and as a result, the super call will cause an infinite recursion.
        # See #10547 and #12121.
        defers = []
        if self._deferred:
            from django.db.models.query_utils import deferred_class_factory
            factory = deferred_class_factory
            for field in self._meta.fields:
                if isinstance(self.__class__.__dict__.get(field.attname),
                        DeferredAttribute):
                    defers.append(field.attname)
            model = self._meta.proxy_for_model
        else:
            factory = simple_class_factory
        return (model_unpickle, (model, defers, factory), data)

    def _get_pk_val(self, meta=None):
        if not meta:
            meta = self._meta
        return getattr(self, meta.pk.attname)

    def _set_pk_val(self, value):
        return setattr(self, self._meta.pk.attname, value)

    pk = property(_get_pk_val, _set_pk_val)

    def serializable_value(self, field_name):
        """
        Returns the value of the field name for this instance. If the field is
        a foreign key, returns the id value, instead of the object. If there's
        no Field object with this name on the model, the model attribute's
        value is returned directly.

        Used to serialize a field's value (in the serializer, or form output,
        for example). Normally, you would just access the attribute directly
        and not use this method.
        """
        try:
            field = self._meta.get_field_by_name(field_name)[0]
        except FieldDoesNotExist:
            return getattr(self, field_name)
        return getattr(self, field.attname)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        """
        Saves the current instance. Override this in a subclass if you want to
        control the saving process.

        The 'force_insert' and 'force_update' parameters can be used to insist
        that the "save" must be an SQL insert or update (or equivalent for
        non-SQL backends), respectively. Normally, they should not be set.
        """
        if force_insert and (force_update or update_fields):
            raise ValueError("Cannot force both insert and updating in model saving.")

        if update_fields is not None:
            # If update_fields is empty, skip the save. We do also check for
            # no-op saves later on for inheritance cases. This bailout is
            # still needed for skipping signal sending.
            if len(update_fields) == 0:
                return

            update_fields = frozenset(update_fields)
            field_names = set([field.name for field in self._meta.fields
                               if not field.primary_key])
            non_model_fields = update_fields.difference(field_names)

            if non_model_fields:
                raise ValueError("The following fields do not exist in this "
                                 "model or are m2m fields: %s"
                                 % ', '.join(non_model_fields))

        self.save_base(using=using, force_insert=force_insert,
                       force_update=force_update, update_fields=update_fields)
    save.alters_data = True

    def save_base(self, raw=False, cls=None, origin=None, force_insert=False,
                  force_update=False, using=None, update_fields=None):
        """
        Does the heavy-lifting involved in saving. Subclasses shouldn't need to
        override this method. It's separate from save() in order to hide the
        need for overrides of save() to pass around internal-only parameters
        ('raw', 'cls', and 'origin').
        """
        using = using or router.db_for_write(self.__class__, instance=self)
        assert not (force_insert and (force_update or update_fields))
        assert update_fields is None or len(update_fields) > 0
        if cls is None:
            cls = self.__class__
            meta = cls._meta
            if not meta.proxy:
                origin = cls
        else:
            meta = cls._meta

        if origin and not meta.auto_created:
            signals.pre_save.send(sender=origin, instance=self, raw=raw, using=using,
                                  update_fields=update_fields)

        # If we are in a raw save, save the object exactly as presented.
        # That means that we don't try to be smart about saving attributes
        # that might have come from the parent class - we just save the
        # attributes we have been given to the class we have been given.
        # We also go through this process to defer the save of proxy objects
        # to their actual underlying model.
        if not raw or meta.proxy:
            if meta.proxy:
                org = cls
            else:
                org = None
            for parent, field in meta.parents.items():
                # At this point, parent's primary key field may be unknown
                # (for example, from administration form which doesn't fill
                # this field). If so, fill it.
                if field and getattr(self, parent._meta.pk.attname) is None and getattr(self, field.attname) is not None:
                    setattr(self, parent._meta.pk.attname, getattr(self, field.attname))

                self.save_base(cls=parent, origin=org, using=using,
                               update_fields=update_fields)

                if field:
                    setattr(self, field.attname, self._get_pk_val(parent._meta))
            if meta.proxy:
                return

        if not meta.proxy:
            non_pks = [f for f in meta.local_fields if not f.primary_key]

            if update_fields:
                non_pks = [f for f in non_pks if f.name in update_fields]

            # First, try an UPDATE. If that doesn't update anything, do an INSERT.
            pk_val = self._get_pk_val(meta)
            pk_set = pk_val is not None
            record_exists = True
            manager = cls._base_manager
            if pk_set:
                # Determine if we should do an update (pk already exists, forced update,
                # no force_insert)
                if ((force_update or update_fields) or (not force_insert and
                        manager.using(using).filter(pk=pk_val).exists())):
                    if force_update or non_pks:
                        values = [(f, None, (raw and getattr(self, f.attname) or f.pre_save(self, False))) for f in non_pks]
                        if values:
                            rows = manager.using(using).filter(pk=pk_val)._update(values)
                            if force_update and not rows:
                                raise DatabaseError("Forced update did not affect any rows.")
                            if update_fields and not rows:
                                raise DatabaseError("Save with update_fields did not affect any rows.")
                else:
                    record_exists = False
            if not pk_set or not record_exists:
                if meta.order_with_respect_to:
                    # If this is a model with an order_with_respect_to
                    # autopopulate the _order field
                    field = meta.order_with_respect_to
                    order_value = manager.using(using).filter(**{field.name: getattr(self, field.attname)}).count()
                    self._order = order_value

                fields = meta.local_fields
                if not pk_set:
                    if force_update or update_fields:
                        raise ValueError("Cannot force an update in save() with no primary key.")
                    fields = [f for f in fields if not isinstance(f, AutoField)]

                record_exists = False

                update_pk = bool(meta.has_auto_field and not pk_set)
                result = manager._insert([self], fields=fields, return_id=update_pk, using=using, raw=raw)

                if update_pk:
                    setattr(self, meta.pk.attname, result)
            transaction.commit_unless_managed(using=using)

        # Store the database on which the object was saved
        self._state.db = using
        # Once saved, this is no longer a to-be-added instance.
        self._state.adding = False

        # Signal that the save is complete
        if origin and not meta.auto_created:
            signals.post_save.send(sender=origin, instance=self, created=(not record_exists),
                                   update_fields=update_fields, raw=raw, using=using)


    save_base.alters_data = True

    def delete(self, using=None):
        using = using or router.db_for_write(self.__class__, instance=self)
        assert self._get_pk_val() is not None, "%s object can't be deleted because its %s attribute is set to None." % (self._meta.object_name, self._meta.pk.attname)

        collector = Collector(using=using)
        collector.collect([self])
        collector.delete()

    delete.alters_data = True

    def _get_FIELD_display(self, field):
        value = getattr(self, field.attname)
        return force_unicode(dict(field.flatchoices).get(value, value), strings_only=True)

    def _get_next_or_previous_by_FIELD(self, field, is_next, **kwargs):
        if not self.pk:
            raise ValueError("get_next/get_previous cannot be used on unsaved objects.")
        op = is_next and 'gt' or 'lt'
        order = not is_next and '-' or ''
        param = smart_str(getattr(self, field.attname))
        q = Q(**{'%s__%s' % (field.name, op): param})
        q = q|Q(**{field.name: param, 'pk__%s' % op: self.pk})
        qs = self.__class__._default_manager.using(self._state.db).filter(**kwargs).filter(q).order_by('%s%s' % (order, field.name), '%spk' % order)
        try:
            return qs[0]
        except IndexError:
            raise self.DoesNotExist("%s matching query does not exist." % self.__class__._meta.object_name)

    def _get_next_or_previous_in_order(self, is_next):
        cachename = "__%s_order_cache" % is_next
        if not hasattr(self, cachename):
            op = is_next and 'gt' or 'lt'
            order = not is_next and '-_order' or '_order'
            order_field = self._meta.order_with_respect_to
            obj = self._default_manager.filter(**{
                order_field.name: getattr(self, order_field.attname)
            }).filter(**{
                '_order__%s' % op: self._default_manager.values('_order').filter(**{
                    self._meta.pk.name: self.pk
                })
            }).order_by(order)[:1].get()
            setattr(self, cachename, obj)
        return getattr(self, cachename)

    def prepare_database_save(self, unused):
        return self.pk

    def clean(self):
        """
        Hook for doing any extra model-wide validation after clean() has been
        called on every field by self.clean_fields. Any ValidationError raised
        by this method will not be associated with a particular field; it will
        have a special-case association with the field defined by NON_FIELD_ERRORS.
        """
        pass

    def validate_unique(self, exclude=None):
        """
        Checks unique constraints on the model and raises ``ValidationError``
        if any failed.
        """
        unique_checks, date_checks = self._get_unique_checks(exclude=exclude)

        errors = self._perform_unique_checks(unique_checks)
        date_errors = self._perform_date_checks(date_checks)

        for k, v in date_errors.items():
            errors.setdefault(k, []).extend(v)

        if errors:
            raise ValidationError(errors)

    def _get_unique_checks(self, exclude=None):
        """
        Gather a list of checks to perform. Since validate_unique could be
        called from a ModelForm, some fields may have been excluded; we can't
        perform a unique check on a model that is missing fields involved
        in that check.
        Fields that did not validate should also be excluded, but they need
        to be passed in via the exclude argument.
        """
        if exclude is None:
            exclude = []
        unique_checks = []

        unique_togethers = [(self.__class__, self._meta.unique_together)]
        for parent_class in self._meta.parents.keys():
            if parent_class._meta.unique_together:
                unique_togethers.append((parent_class, parent_class._meta.unique_together))

        for model_class, unique_together in unique_togethers:
            for check in unique_together:
                for name in check:
                    # If this is an excluded field, don't add this check.
                    if name in exclude:
                        break
                else:
                    unique_checks.append((model_class, tuple(check)))

        # These are checks for the unique_for_<date/year/month>.
        date_checks = []

        # Gather a list of checks for fields declared as unique and add them to
        # the list of checks.

        fields_with_class = [(self.__class__, self._meta.local_fields)]
        for parent_class in self._meta.parents.keys():
            fields_with_class.append((parent_class, parent_class._meta.local_fields))

        for model_class, fields in fields_with_class:
            for f in fields:
                name = f.name
                if name in exclude:
                    continue
                if f.unique:
                    unique_checks.append((model_class, (name,)))
                if f.unique_for_date and f.unique_for_date not in exclude:
                    date_checks.append((model_class, 'date', name, f.unique_for_date))
                if f.unique_for_year and f.unique_for_year not in exclude:
                    date_checks.append((model_class, 'year', name, f.unique_for_year))
                if f.unique_for_month and f.unique_for_month not in exclude:
                    date_checks.append((model_class, 'month', name, f.unique_for_month))
        return unique_checks, date_checks

    def _perform_unique_checks(self, unique_checks):
        errors = {}

        for model_class, unique_check in unique_checks:
            # Try to look up an existing object with the same values as this
            # object's values for all the unique field.

            lookup_kwargs = {}
            for field_name in unique_check:
                f = self._meta.get_field(field_name)
                lookup_value = getattr(self, f.attname)
                if lookup_value is None:
                    # no value, skip the lookup
                    continue
                if f.primary_key and not self._state.adding:
                    # no need to check for unique primary key when editing
                    continue
                lookup_kwargs[str(field_name)] = lookup_value

            # some fields were skipped, no reason to do the check
            if len(unique_check) != len(lookup_kwargs.keys()):
                continue

            qs = model_class._default_manager.filter(**lookup_kwargs)

            # Exclude the current object from the query if we are editing an
            # instance (as opposed to creating a new one)
            # Note that we need to use the pk as defined by model_class, not
            # self.pk. These can be different fields because model inheritance
            # allows single model to have effectively multiple primary keys.
            # Refs #17615.
            model_class_pk = self._get_pk_val(model_class._meta)
            if not self._state.adding and model_class_pk is not None:
                qs = qs.exclude(pk=model_class_pk)
            if qs.exists():
                if len(unique_check) == 1:
                    key = unique_check[0]
                else:
                    key = NON_FIELD_ERRORS
                errors.setdefault(key, []).append(self.unique_error_message(model_class, unique_check))

        return errors

    def _perform_date_checks(self, date_checks):
        errors = {}
        for model_class, lookup_type, field, unique_for in date_checks:
            lookup_kwargs = {}
            # there's a ticket to add a date lookup, we can remove this special
            # case if that makes it's way in
            date = getattr(self, unique_for)
            if date is None:
                continue
            if lookup_type == 'date':
                lookup_kwargs['%s__day' % unique_for] = date.day
                lookup_kwargs['%s__month' % unique_for] = date.month
                lookup_kwargs['%s__year' % unique_for] = date.year
            else:
                lookup_kwargs['%s__%s' % (unique_for, lookup_type)] = getattr(date, lookup_type)
            lookup_kwargs[field] = getattr(self, field)

            qs = model_class._default_manager.filter(**lookup_kwargs)
            # Exclude the current object from the query if we are editing an
            # instance (as opposed to creating a new one)
            if not self._state.adding and self.pk is not None:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                errors.setdefault(field, []).append(
                    self.date_error_message(lookup_type, field, unique_for)
                )
        return errors

    def date_error_message(self, lookup_type, field, unique_for):
        opts = self._meta
        return _("%(field_name)s must be unique for %(date_field)s %(lookup)s.") % {
            'field_name': unicode(capfirst(opts.get_field(field).verbose_name)),
            'date_field': unicode(capfirst(opts.get_field(unique_for).verbose_name)),
            'lookup': lookup_type,
        }

    def unique_error_message(self, model_class, unique_check):
        opts = model_class._meta
        model_name = capfirst(opts.verbose_name)

        # A unique field
        if len(unique_check) == 1:
            field_name = unique_check[0]
            field = opts.get_field(field_name)
            field_label = capfirst(field.verbose_name)
            # Insert the error into the error dict, very sneaky
            return field.error_messages['unique'] %  {
                'model_name': unicode(model_name),
                'field_label': unicode(field_label)
            }
        # unique_together
        else:
            field_labels = map(lambda f: capfirst(opts.get_field(f).verbose_name), unique_check)
            field_labels = get_text_list(field_labels, _('and'))
            return _("%(model_name)s with this %(field_label)s already exists.") %  {
                'model_name': unicode(model_name),
                'field_label': unicode(field_labels)
            }

    def full_clean(self, exclude=None):
        """
        Calls clean_fields, clean, and validate_unique, on the model,
        and raises a ``ValidationError`` for any errors that occured.
        """
        errors = {}
        if exclude is None:
            exclude = []

        try:
            self.clean_fields(exclude=exclude)
        except ValidationError as e:
            errors = e.update_error_dict(errors)

        # Form.clean() is run even if other validation fails, so do the
        # same with Model.clean() for consistency.
        try:
            self.clean()
        except ValidationError as e:
            errors = e.update_error_dict(errors)

        # Run unique checks, but only for fields that passed validation.
        for name in errors.keys():
            if name != NON_FIELD_ERRORS and name not in exclude:
                exclude.append(name)
        try:
            self.validate_unique(exclude=exclude)
        except ValidationError as e:
            errors = e.update_error_dict(errors)

        if errors:
            raise ValidationError(errors)

    def clean_fields(self, exclude=None):
        """
        Cleans all fields and raises a ValidationError containing message_dict
        of all validation errors if any occur.
        """
        if exclude is None:
            exclude = []

        errors = {}
        for f in self._meta.fields:
            if f.name in exclude:
                continue
            # Skip validation for empty fields with blank=True. The developer
            # is responsible for making sure they have a valid value.
            raw_value = getattr(self, f.attname)
            if f.blank and raw_value in validators.EMPTY_VALUES:
                continue
            try:
                setattr(self, f.attname, f.clean(raw_value, self))
            except ValidationError as e:
                errors[f.name] = e.messages

        if errors:
            raise ValidationError(errors)


############################################
# HELPER FUNCTIONS (CURRIED MODEL METHODS) #
############################################

# ORDERING METHODS #########################

def method_set_order(ordered_obj, self, id_list, using=None):
    if using is None:
        using = DEFAULT_DB_ALIAS
    rel_val = getattr(self, ordered_obj._meta.order_with_respect_to.rel.field_name)
    order_name = ordered_obj._meta.order_with_respect_to.name
    # FIXME: It would be nice if there was an "update many" version of update
    # for situations like this.
    for i, j in enumerate(id_list):
        ordered_obj.objects.filter(**{'pk': j, order_name: rel_val}).update(_order=i)
    transaction.commit_unless_managed(using=using)


def method_get_order(ordered_obj, self):
    rel_val = getattr(self, ordered_obj._meta.order_with_respect_to.rel.field_name)
    order_name = ordered_obj._meta.order_with_respect_to.name
    pk_name = ordered_obj._meta.pk.name
    return [r[pk_name] for r in
            ordered_obj.objects.filter(**{order_name: rel_val}).values(pk_name)]


##############################################
# HELPER FUNCTIONS (CURRIED MODEL FUNCTIONS) #
##############################################

def get_absolute_url(opts, func, self, *args, **kwargs):
    return settings.ABSOLUTE_URL_OVERRIDES.get('%s.%s' % (opts.app_label, opts.module_name), func)(self, *args, **kwargs)


########
# MISC #
########

class Empty(object):
    pass

def simple_class_factory(model, attrs):
    """Used to unpickle Models without deferred fields.

    We need to do this the hard way, rather than just using
    the default __reduce__ implementation, because of a
    __deepcopy__ problem in Python 2.4
    """
    return model

def model_unpickle(model, attrs, factory):
    """
    Used to unpickle Model subclasses with deferred fields.
    """
    cls = factory(model, attrs)
    return cls.__new__(cls)
model_unpickle.__safe_for_unpickle__ = True

def subclass_exception(name, parents, module):
    return type(name, parents, {'__module__': module})

########NEW FILE########
__FILENAME__ = flask-view
# -*- coding: utf-8 -*-
"""
    flask.views
    ~~~~~~~~~~~

    This module provides class-based views inspired by the ones in Django.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from .globals import request


http_method_funcs = frozenset(['get', 'post', 'head', 'options',
                               'delete', 'put', 'trace', 'patch'])


class View(object):
    """Alternative way to use view functions.  A subclass has to implement
    :meth:`dispatch_request` which is called with the view arguments from
    the URL routing system.  If :attr:`methods` is provided the methods
    do not have to be passed to the :meth:`~flask.Flask.add_url_rule`
    method explicitly::

        class MyView(View):
            methods = ['GET']

            def dispatch_request(self, name):
                return 'Hello %s!' % name

        app.add_url_rule('/hello/<name>', view_func=MyView.as_view('myview'))

    When you want to decorate a pluggable view you will have to either do that
    when the view function is created (by wrapping the return value of
    :meth:`as_view`) or you can use the :attr:`decorators` attribute::

        class SecretView(View):
            methods = ['GET']
            decorators = [superuser_required]

            def dispatch_request(self):
                ...

    The decorators stored in the decorators list are applied one after another
    when the view function is created.  Note that you can *not* use the class
    based decorators since those would decorate the view class and not the
    generated view function!
    """

    #: A for which methods this pluggable view can handle.
    methods = None

    #: The canonical way to decorate class-based views is to decorate the
    #: return value of as_view().  However since this moves parts of the
    #: logic from the class declaration to the place where it's hooked
    #: into the routing system.
    #:
    #: You can place one or more decorators in this list and whenever the
    #: view function is created the result is automatically decorated.
    #:
    #: .. versionadded:: 0.8
    decorators = []

    def dispatch_request(self):
        """Subclasses have to override this method to implement the
        actual view function code.  This method is called with all
        the arguments from the URL rule.
        """
        raise NotImplementedError()

    @classmethod
    def as_view(cls, name, *class_args, **class_kwargs):
        """Converts the class into an actual view function that can be used
        with the routing system.  Internally this generates a function on the
        fly which will instantiate the :class:`View` on each request and call
        the :meth:`dispatch_request` method on it.

        The arguments passed to :meth:`as_view` are forwarded to the
        constructor of the class.
        """
        def view(*args, **kwargs):
            self = view.view_class(*class_args, **class_kwargs)
            return self.dispatch_request(*args, **kwargs)

        if cls.decorators:
            view.__name__ = name
            view.__module__ = cls.__module__
            for decorator in cls.decorators:
                view = decorator(view)

        # we attach the view class to the view function for two reasons:
        # first of all it allows us to easily figure out what class-based
        # view this thing came from, secondly it's also used for instantiating
        # the view class so you can actually replace it with something else
        # for testing purposes and debugging.
        view.view_class = cls
        view.__name__ = name
        view.__doc__ = cls.__doc__
        view.__module__ = cls.__module__
        view.methods = cls.methods
        return view


class MethodViewType(type):

    def __new__(cls, name, bases, d):
        rv = type.__new__(cls, name, bases, d)
        if 'methods' not in d:
            methods = set(rv.methods or [])
            for key in d:
                if key in http_method_funcs:
                    methods.add(key.upper())
            # if we have no method at all in there we don't want to
            # add a method list.  (This is for instance the case for
            # the baseclass or another subclass of a base method view
            # that does not introduce new methods).
            if methods:
                rv.methods = sorted(methods)
        return rv


class MethodView(View):
    """Like a regular class-based view but that dispatches requests to
    particular methods.  For instance if you implement a method called
    :meth:`get` it means you will response to ``'GET'`` requests and
    the :meth:`dispatch_request` implementation will automatically
    forward your request to that.  Also :attr:`options` is set for you
    automatically::

        class CounterAPI(MethodView):

            def get(self):
                return session.get('counter', 0)

            def post(self):
                session['counter'] = session.get('counter', 0) + 1
                return 'OK'

        app.add_url_rule('/counter', view_func=CounterAPI.as_view('counter'))
    """
    __metaclass__ = MethodViewType

    def dispatch_request(self, *args, **kwargs):
        meth = getattr(self, request.method.lower(), None)
        # if the request method is HEAD and we don't have a handler for it
        # retry with GET
        if meth is None and request.method == 'HEAD':
            meth = getattr(self, 'get', None)
        assert meth is not None, 'Unimplemented method %r' % request.method
        return meth(*args, **kwargs)

########NEW FILE########
__FILENAME__ = tornado-httpserver
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A non-blocking, single-threaded HTTP server.

Typical applications have little direct interaction with the `HTTPServer`
class except to start a server at the beginning of the process
(and even that is often done indirectly via `tornado.web.Application.listen`).

This module also defines the `HTTPRequest` class which is exposed via
`tornado.web.RequestHandler.request`.
"""

from __future__ import absolute_import, division, with_statement

import Cookie
import logging
import socket
import time

from tornado.escape import utf8, native_str, parse_qs_bytes
from tornado import httputil
from tornado import iostream
from tornado.netutil import TCPServer
from tornado import stack_context
from tornado.util import b, bytes_type

try:
    import ssl  # Python 2.6+
except ImportError:
    ssl = None


class HTTPServer(TCPServer):
    r"""A non-blocking, single-threaded HTTP server.

    A server is defined by a request callback that takes an HTTPRequest
    instance as an argument and writes a valid HTTP response with
    `HTTPRequest.write`. `HTTPRequest.finish` finishes the request (but does
    not necessarily close the connection in the case of HTTP/1.1 keep-alive
    requests). A simple example server that echoes back the URI you
    requested::

        import httpserver
        import ioloop

        def handle_request(request):
           message = "You requested %s\n" % request.uri
           request.write("HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n%s" % (
                         len(message), message))
           request.finish()

        http_server = httpserver.HTTPServer(handle_request)
        http_server.listen(8888)
        ioloop.IOLoop.instance().start()

    `HTTPServer` is a very basic connection handler. Beyond parsing the
    HTTP request body and headers, the only HTTP semantics implemented
    in `HTTPServer` is HTTP/1.1 keep-alive connections. We do not, however,
    implement chunked encoding, so the request callback must provide a
    ``Content-Length`` header or implement chunked encoding for HTTP/1.1
    requests for the server to run correctly for HTTP/1.1 clients. If
    the request handler is unable to do this, you can provide the
    ``no_keep_alive`` argument to the `HTTPServer` constructor, which will
    ensure the connection is closed on every request no matter what HTTP
    version the client is using.

    If ``xheaders`` is ``True``, we support the ``X-Real-Ip`` and ``X-Scheme``
    headers, which override the remote IP and HTTP scheme for all requests.
    These headers are useful when running Tornado behind a reverse proxy or
    load balancer.

    `HTTPServer` can serve SSL traffic with Python 2.6+ and OpenSSL.
    To make this server serve SSL traffic, send the ssl_options dictionary
    argument with the arguments required for the `ssl.wrap_socket` method,
    including "certfile" and "keyfile"::

       HTTPServer(applicaton, ssl_options={
           "certfile": os.path.join(data_dir, "mydomain.crt"),
           "keyfile": os.path.join(data_dir, "mydomain.key"),
       })

    `HTTPServer` initialization follows one of three patterns (the
    initialization methods are defined on `tornado.netutil.TCPServer`):

    1. `~tornado.netutil.TCPServer.listen`: simple single-process::

            server = HTTPServer(app)
            server.listen(8888)
            IOLoop.instance().start()

       In many cases, `tornado.web.Application.listen` can be used to avoid
       the need to explicitly create the `HTTPServer`.

    2. `~tornado.netutil.TCPServer.bind`/`~tornado.netutil.TCPServer.start`:
       simple multi-process::

            server = HTTPServer(app)
            server.bind(8888)
            server.start(0)  # Forks multiple sub-processes
            IOLoop.instance().start()

       When using this interface, an `IOLoop` must *not* be passed
       to the `HTTPServer` constructor.  `start` will always start
       the server on the default singleton `IOLoop`.

    3. `~tornado.netutil.TCPServer.add_sockets`: advanced multi-process::

            sockets = tornado.netutil.bind_sockets(8888)
            tornado.process.fork_processes(0)
            server = HTTPServer(app)
            server.add_sockets(sockets)
            IOLoop.instance().start()

       The `add_sockets` interface is more complicated, but it can be
       used with `tornado.process.fork_processes` to give you more
       flexibility in when the fork happens.  `add_sockets` can
       also be used in single-process servers if you want to create
       your listening sockets in some way other than
       `tornado.netutil.bind_sockets`.

    """
    def __init__(self, request_callback, no_keep_alive=False, io_loop=None,
                 xheaders=False, ssl_options=None, **kwargs):
        self.request_callback = request_callback
        self.no_keep_alive = no_keep_alive
        self.xheaders = xheaders
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options,
                           **kwargs)

    def handle_stream(self, stream, address):
        HTTPConnection(stream, address, self.request_callback,
                       self.no_keep_alive, self.xheaders)


class _BadRequestException(Exception):
    """Exception class for malformed HTTP requests."""
    pass


class HTTPConnection(object):
    """Handles a connection to an HTTP client, executing HTTP requests.

    We parse HTTP headers and bodies, and execute the request callback
    until the HTTP conection is closed.
    """
    def __init__(self, stream, address, request_callback, no_keep_alive=False,
                 xheaders=False):
        self.stream = stream
        self.address = address
        self.request_callback = request_callback
        self.no_keep_alive = no_keep_alive
        self.xheaders = xheaders
        self._request = None
        self._request_finished = False
        # Save stack context here, outside of any request.  This keeps
        # contexts from one request from leaking into the next.
        self._header_callback = stack_context.wrap(self._on_headers)
        self.stream.read_until(b("\r\n\r\n"), self._header_callback)
        self._write_callback = None

    def write(self, chunk, callback=None):
        """Writes a chunk of output to the stream."""
        assert self._request, "Request closed"
        if not self.stream.closed():
            self._write_callback = stack_context.wrap(callback)
            self.stream.write(chunk, self._on_write_complete)

    def finish(self):
        """Finishes the request."""
        assert self._request, "Request closed"
        self._request_finished = True
        if not self.stream.writing():
            self._finish_request()

    def _on_write_complete(self):
        if self._write_callback is not None:
            callback = self._write_callback
            self._write_callback = None
            callback()
        # _on_write_complete is enqueued on the IOLoop whenever the
        # IOStream's write buffer becomes empty, but it's possible for
        # another callback that runs on the IOLoop before it to
        # simultaneously write more data and finish the request.  If
        # there is still data in the IOStream, a future
        # _on_write_complete will be responsible for calling
        # _finish_request.
        if self._request_finished and not self.stream.writing():
            self._finish_request()

    def _finish_request(self):
        if self.no_keep_alive:
            disconnect = True
        else:
            connection_header = self._request.headers.get("Connection")
            if connection_header is not None:
                connection_header = connection_header.lower()
            if self._request.supports_http_1_1():
                disconnect = connection_header == "close"
            elif ("Content-Length" in self._request.headers
                    or self._request.method in ("HEAD", "GET")):
                disconnect = connection_header != "keep-alive"
            else:
                disconnect = True
        self._request = None
        self._request_finished = False
        if disconnect:
            self.stream.close()
            return
        self.stream.read_until(b("\r\n\r\n"), self._header_callback)

    def _on_headers(self, data):
        try:
            data = native_str(data.decode('latin1'))
            eol = data.find("\r\n")
            start_line = data[:eol]
            try:
                method, uri, version = start_line.split(" ")
            except ValueError:
                raise _BadRequestException("Malformed HTTP request line")
            if not version.startswith("HTTP/"):
                raise _BadRequestException("Malformed HTTP version in HTTP Request-Line")
            headers = httputil.HTTPHeaders.parse(data[eol:])

            # HTTPRequest wants an IP, not a full socket address
            if getattr(self.stream.socket, 'family', socket.AF_INET) in (
                socket.AF_INET, socket.AF_INET6):
                # Jython 2.5.2 doesn't have the socket.family attribute,
                # so just assume IP in that case.
                remote_ip = self.address[0]
            else:
                # Unix (or other) socket; fake the remote address
                remote_ip = '0.0.0.0'

            self._request = HTTPRequest(
                connection=self, method=method, uri=uri, version=version,
                headers=headers, remote_ip=remote_ip)

            content_length = headers.get("Content-Length")
            if content_length:
                content_length = int(content_length)
                if content_length > self.stream.max_buffer_size:
                    raise _BadRequestException("Content-Length too long")
                if headers.get("Expect") == "100-continue":
                    self.stream.write(b("HTTP/1.1 100 (Continue)\r\n\r\n"))
                self.stream.read_bytes(content_length, self._on_request_body)
                return

            self.request_callback(self._request)
        except _BadRequestException, e:
            logging.info("Malformed HTTP request from %s: %s",
                         self.address[0], e)
            self.stream.close()
            return

    def _on_request_body(self, data):
        self._request.body = data
        content_type = self._request.headers.get("Content-Type", "")
        if self._request.method in ("POST", "PATCH", "PUT"):
            if content_type.startswith("application/x-www-form-urlencoded"):
                arguments = parse_qs_bytes(native_str(self._request.body))
                for name, values in arguments.iteritems():
                    values = [v for v in values if v]
                    if values:
                        self._request.arguments.setdefault(name, []).extend(
                            values)
            elif content_type.startswith("multipart/form-data"):
                fields = content_type.split(";")
                for field in fields:
                    k, sep, v = field.strip().partition("=")
                    if k == "boundary" and v:
                        httputil.parse_multipart_form_data(
                            utf8(v), data,
                            self._request.arguments,
                            self._request.files)
                        break
                else:
                    logging.warning("Invalid multipart/form-data")
        self.request_callback(self._request)


class HTTPRequest(object):
    """A single HTTP request.

    All attributes are type `str` unless otherwise noted.

    .. attribute:: method

       HTTP request method, e.g. "GET" or "POST"

    .. attribute:: uri

       The requested uri.

    .. attribute:: path

       The path portion of `uri`

    .. attribute:: query

       The query portion of `uri`

    .. attribute:: version

       HTTP version specified in request, e.g. "HTTP/1.1"

    .. attribute:: headers

       `HTTPHeader` dictionary-like object for request headers.  Acts like
       a case-insensitive dictionary with additional methods for repeated
       headers.

    .. attribute:: body

       Request body, if present, as a byte string.

    .. attribute:: remote_ip

       Client's IP address as a string.  If `HTTPServer.xheaders` is set,
       will pass along the real IP address provided by a load balancer
       in the ``X-Real-Ip`` header

    .. attribute:: protocol

       The protocol used, either "http" or "https".  If `HTTPServer.xheaders`
       is set, will pass along the protocol used by a load balancer if
       reported via an ``X-Scheme`` header.

    .. attribute:: host

       The requested hostname, usually taken from the ``Host`` header.

    .. attribute:: arguments

       GET/POST arguments are available in the arguments property, which
       maps arguments names to lists of values (to support multiple values
       for individual names). Names are of type `str`, while arguments
       are byte strings.  Note that this is different from
       `RequestHandler.get_argument`, which returns argument values as
       unicode strings.

    .. attribute:: files

       File uploads are available in the files property, which maps file
       names to lists of :class:`HTTPFile`.

    .. attribute:: connection

       An HTTP request is attached to a single HTTP connection, which can
       be accessed through the "connection" attribute. Since connections
       are typically kept open in HTTP/1.1, multiple requests can be handled
       sequentially on a single connection.
    """
    def __init__(self, method, uri, version="HTTP/1.0", headers=None,
                 body=None, remote_ip=None, protocol=None, host=None,
                 files=None, connection=None):
        self.method = method
        self.uri = uri
        self.version = version
        self.headers = headers or httputil.HTTPHeaders()
        self.body = body or ""
        if connection and connection.xheaders:
            # Squid uses X-Forwarded-For, others use X-Real-Ip
            self.remote_ip = self.headers.get(
                "X-Real-Ip", self.headers.get("X-Forwarded-For", remote_ip))
            if not self._valid_ip(self.remote_ip):
                self.remote_ip = remote_ip
            # AWS uses X-Forwarded-Proto
            self.protocol = self.headers.get(
                "X-Scheme", self.headers.get("X-Forwarded-Proto", protocol))
            if self.protocol not in ("http", "https"):
                self.protocol = "http"
        else:
            self.remote_ip = remote_ip
            if protocol:
                self.protocol = protocol
            elif connection and isinstance(connection.stream,
                                           iostream.SSLIOStream):
                self.protocol = "https"
            else:
                self.protocol = "http"
        self.host = host or self.headers.get("Host") or "127.0.0.1"
        self.files = files or {}
        self.connection = connection
        self._start_time = time.time()
        self._finish_time = None

        self.path, sep, self.query = uri.partition('?')
        arguments = parse_qs_bytes(self.query)
        self.arguments = {}
        for name, values in arguments.iteritems():
            values = [v for v in values if v]
            if values:
                self.arguments[name] = values

    def supports_http_1_1(self):
        """Returns True if this request supports HTTP/1.1 semantics"""
        return self.version == "HTTP/1.1"

    @property
    def cookies(self):
        """A dictionary of Cookie.Morsel objects."""
        if not hasattr(self, "_cookies"):
            self._cookies = Cookie.SimpleCookie()
            if "Cookie" in self.headers:
                try:
                    self._cookies.load(
                        native_str(self.headers["Cookie"]))
                except Exception:
                    self._cookies = {}
        return self._cookies

    def write(self, chunk, callback=None):
        """Writes the given chunk to the response stream."""
        assert isinstance(chunk, bytes_type)
        self.connection.write(chunk, callback=callback)

    def finish(self):
        """Finishes this HTTP request on the open connection."""
        self.connection.finish()
        self._finish_time = time.time()

    def full_url(self):
        """Reconstructs the full URL for this request."""
        return self.protocol + "://" + self.host + self.uri

    def request_time(self):
        """Returns the amount of time it took for this request to execute."""
        if self._finish_time is None:
            return time.time() - self._start_time
        else:
            return self._finish_time - self._start_time

    def get_ssl_certificate(self):
        """Returns the client's SSL certificate, if any.

        To use client certificates, the HTTPServer must have been constructed
        with cert_reqs set in ssl_options, e.g.::

            server = HTTPServer(app,
                ssl_options=dict(
                    certfile="foo.crt",
                    keyfile="foo.key",
                    cert_reqs=ssl.CERT_REQUIRED,
                    ca_certs="cacert.crt"))

        The return value is a dictionary, see SSLSocket.getpeercert() in
        the standard library for more details.
        http://docs.python.org/library/ssl.html#sslsocket-objects
        """
        try:
            return self.connection.stream.socket.getpeercert()
        except ssl.SSLError:
            return None

    def __repr__(self):
        attrs = ("protocol", "host", "method", "uri", "version", "remote_ip",
                 "body")
        args = ", ".join(["%s=%r" % (n, getattr(self, n)) for n in attrs])
        return "%s(%s, headers=%s)" % (
            self.__class__.__name__, args, dict(self.headers))

    def _valid_ip(self, ip):
        try:
            res = socket.getaddrinfo(ip, 0, socket.AF_UNSPEC,
                                     socket.SOCK_STREAM,
                                     0, socket.AI_NUMERICHOST)
            return bool(res)
        except socket.gaierror, e:
            if e.args[0] == socket.EAI_NONAME:
                return False
            raise
        return True

########NEW FILE########
