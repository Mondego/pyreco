__FILENAME__ = application
# -*- coding: utf-8 -*-


import os
import logging
from flask import Flask

from basesite import configs

from basesite.views import test_view as test
# add some other view

__all__ = ['create_app']


DEFAULT_APP_NAME = 'basesite'

REGISTER_BLUE_PRINTS = (
        (test.instance,''),
        # add your blue print here
        )

def create_app(config=None,app_name=None):
    
    if app_name is None:
        app_name = DEFAULT_APP_NAME
    
    app = Flask(app_name)

    configure_app(app,config)
    #configure_db(app)
    configure_blueprints(app)
    #configure_cache(app)
    return app

def configure_app(app,config):
    app.config.from_object(configs.DefaultConfig())

    if config is not None:
        app.config.from_object(config)

    app.config.from_envvar('APP_CONFIG',silent=True)

def configure_db(app):
    pass

def configure_blueprints(app):
    for blue,url_prefix in REGISTER_BLUE_PRINTS:
        #app.register_blueprint(blue)
        app.register_blueprint(blue,url_prefix=url_prefix)

    

########NEW FILE########
__FILENAME__ = configs
# -*- coding: utf-8 -*-

import datetime

class DefaultConfig(object):

    DEBUG = True
    SECRET_KEY = ''
    SESSION_COOKIE_PATH='/'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_NAME = 'Ssession'
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(31)
    SQLALCHEMY_DATABASE_URL = 'postgresql+psycopg2://xxxxxxxxxxxxx'
    SQLALCHEMY_ECHO = False

class TestConfig(object):
    SQLALCHEMY_DATABASE_URL = 'postgresql+psycopg2://xxxxxxxxxxxxxxxxx'
    SQLALCHEMY_ECHO = False

class ProductionConfig(object):
    SQLALCHEMY_ECHO = False
    DEBUG = False


########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-


# author: notedit <notedit@gmail.com>

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-


# add your models here

########NEW FILE########
__FILENAME__ = test_view
# -*- coding: utf-8 -*-

# author: notedit <notedit@gmail.com>
# date: 2012/12/01  morning

import sys 
import time
import flask
from flask import Blueprint
from flask import request
from flask import g
from flask import Response
from flask import current_app
from flask import session
from flask import jsonify
from flask.views import MethodView
from flask.views import View


instance = Blueprint('index',__name__)

class TestView(MethodView):
    def get(self):
        return jsonify(hello="""do not panic""")

instance.add_url_rule('/test',view_func=TestView.as_view('test'),methods=['GET',])

########NEW FILE########
__FILENAME__ = manage
# -*- coding: utf-8 -*-
# author: notedit<notedit@gmail.com>

import os
import sys
from flask import current_app
from flask.ext.script import Manager,prompt,prompt_pass,\
        prompt_bool,prompt_choices
from flask.ext.script import Server

from basesite import create_app

manager = Manager(create_app)
app = create_app

@manager.command
def initdb():
    if prompt_bool("Are you sure? You will init your database"):
        pass

@manager.command
def dropdb():
    if prompt_bool("Are you sure? You will lose all your data!"):
        pass

@manager.option('-u','--username',dest='username',required=True)
@manager.option('-p','--password',dest='password',required=True)
@manager.option('-e','--email',dest='email',required=True)
def createuser(username=None,password=None,email=None):
    pass

manager.add_command('runserver',Server())

if __name__ == '__main__':
    manager.run()

########NEW FILE########
__FILENAME__ = test_site
# -*- coding: utf-8 -*-

import json
from tests import TestCase


class TestSite(TestCase):

    def test_site(self):

        resp = self.client.get('/test')
        res = json.loads(resp.data)
        assert res['hello'] == """do not panic"""





########NEW FILE########
