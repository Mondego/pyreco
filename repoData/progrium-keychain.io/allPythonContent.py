__FILENAME__ = app
import collections
import base64
import uuid
import hashlib
import os

import eventlet
import requests
import boto
import boto.s3.key

from flask import Flask
from flask import request
from flask import redirect
from flask import render_template

app = Flask('keychain')
app.config['DEBUG'] = True

bucket_name = os.environ.get('KEYCHAIN_BUCKET_NAME')
action_expiry = 3600
pending_actions = {}

s3 = None

def s3key(email, name):
    global s3
    if not s3:
        s3 = boto.connect_s3()
    k = boto.s3.key.Key(s3.lookup(bucket_name))
    k.key = '{}.{}'.format(email, name)
    return k

def s3keys(email):
    global s3
    if not s3:
        s3 = boto.connect_s3()
    b = s3.get_bucket(bucket_name)
    return b.list(prefix=email)

def lookup_key(email, name=None):
    name = name or 'default'
    k = s3key(email, name)
    try:
        return k.get_contents_as_string()
    except:
        return None

def lookup_keys(email):
    keys = s3keys(email)
    try:
        return [k.get_contents_as_string() for k in keys]
    except Exception, e:
        return None

def upload_key(email, name, key):
    k = s3key(email, name)
    k.set_contents_from_string(key.strip())

def delete_key(email, name):
    k = s3key(email, name)
    k.delete()

def fingerprint(keystring):
    key = base64.b64decode(keystring.split(' ')[1])
    fp = hashlib.md5(key).hexdigest()
    return ':'.join(a+b for a,b in zip(fp[::2], fp[1::2]))

def confirm_key_upload(email, keyname, key):
    token = str(uuid.uuid4())
    pending_actions[token] = (upload_key, (email, keyname, key))
    schedule_action_expiration(token)
    send_confirmation('upload', token, email)

def confirm_key_delete(email, keyname):
    token = str(uuid.uuid4())
    pending_actions[token] = (delete_key, (email, keyname))
    schedule_action_expiration(token)
    send_confirmation('delete', token, email)

def schedule_action_expiration(token):
    eventlet.spawn_after(action_expiry, lambda: pending_actions.pop(token, None))

def send_confirmation(action, token, email):
    if 'SENDGRID_USERNAME' in os.environ:
        requests.post("https://sendgrid.com/api/mail.send.json",
            data={
                'api_user':os.environ.get('SENDGRID_USERNAME'),
                'api_key':os.environ.get('SENDGRID_PASSWORD'),
                'to':email,
                'subject':"Keychain.io {} Confirmation".format(action.capitalize()),
                'from':"robot@keychain.io",
                'text':"Click this link to confirm {}:\n{}{}/confirm/{}".format(
                    action, request.url_root, email, token)})
    else:
        print("Email to {} for {}: {}{}/confirm/{}".format(
            email, action, request.url_root, email, token))

@app.route('/')
def index():
    return redirect("http://github.com/progrium/keychain.io")

@app.route('/<email>/confirm/<token>')
def confirm_action(email, token):
    if token not in pending_actions:
        return "Action expired\n"
    else:
        action = pending_actions.pop(token)
        action[0](*action[1])
        return "Action completed\n"

@app.route('/<email>', methods=['GET', 'PUT', 'DELETE'])
def default_key(email):
    return named_key(email, 'default')

@app.route('/<email>/upload')
def default_upload(email):
    return named_key_action(email, 'default', 'upload')

@app.route('/<email>/install')
def default_install(email):
    return named_key_action(email, 'default', 'install')

@app.route('/<email>/fingerprint')
def default_fingerprint(email):
    return named_key_action(email, 'default', 'fingerprint')

@app.route('/<email>/all')
def all_keys(email):
    keys_ = lookup_keys(email)
    return "{0}\n".format('\n'.join(keys_))

@app.route('/<email>/all/install')
def all_install(email):
    keys_ = lookup_keys(email)
    return render_template('install.sh', keys=keys_)

@app.route('/<email>/<keyname>', methods=['GET', 'PUT', 'DELETE'])
def named_key(email, keyname):
    if request.method == 'PUT':
        key = request.files.get('key')
        if key:
            confirm_key_upload(email, keyname, key.read())
            return "Key received, check email to confirm upload.\n"
        else:
            return "No key specified\n", 400

    elif request.method == 'GET':
        key = lookup_key(email, keyname)
        if key:
            return "{0}\n".format(key)
        else:
            return "Key not found\n", 404

    elif request.method == 'DELETE':
        key = lookup_key(email, keyname)
        if key:
            confirm_key_delete(email, keyname)
            return "Check your email to confirm key deletion.\n"
        else:
            return "Key not found\n", 404

@app.route('/<email>/<keyname>/<action>')
def named_key_action(email, keyname, action):
    if action == 'fingerprint':
        key = lookup_key(email, keyname)
        if key:
            return fingerprint(key)
        else:
            return "Key not found\n", 404

    elif action == 'upload':
        keypath = request.args.get('keypath', '')
        url_root = request.url_root
        return render_template('upload.sh', email=email,
                keyname=keyname, keypath=keypath, url_root=url_root)

    elif action == 'install':
        key = lookup_key(email, keyname)
        if key:
            return render_template('install.sh', keys=[key])
        else:
            return 'echo "No key to install."'



########NEW FILE########
__FILENAME__ = __main__
import os

from eventlet import wsgi
import eventlet

from keychain.app import app

if __name__ == "__main__":
  eventlet.monkey_patch()
  wsgi.server(eventlet.listen(
      ('', int(os.environ.get("PORT", 5000)))), app)

########NEW FILE########
__FILENAME__ = test_keychain
from StringIO import StringIO
import unittest

from keychain.app import app
from keychain.app import keys

TEST_KEY = """ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC1sUFNQQj51hKbKcAkEd/FmWvk8Hao+YHFLWX9iDTbwFUX6zZjjiTScoOpzsjHiN8tY4sOcBWcFGctPlLfGGkcD6gxdvUtOiU4/kyJ0RG1Pz2HcUz4wqWzWpXqH1q/sAujxZDV3iRzl6U5KwqrVLUuHp1C+TZGMFzvEdsSy2ISQmRY09wNH7km7TxOz9w9iRrfk49BVv8hGr2/VU2U+34u1n7Ebusp5JaLlJM6AqhlvFaHhuiNG4+7dhKLzLMb9A6+BEKMMEKARxHckFRhH7DhnDaz1UH84dXex+Cq/+z6bDeHWvs5mAG+6ET7qz8sRxWpQGupOqV/lMo58Mw22ZBL test@example.com"""

class KeychainTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        keys.clear()

    def test_root(self):
        rv = self.app.get('/')
        assert rv.status_code == 302

    def test_default_key_get(self):
        rv = self.app.get('/nobody@example.com')
        assert rv.status_code == 404

        keys['test@example.com']['default'] = TEST_KEY
        rv = self.app.get('/test@example.com')
        assert TEST_KEY in rv.data

    def test_default_key_put(self):
        rv = self.app.put('/test@example.com', data={
            'key': (StringIO(TEST_KEY), 'id_rsa.pub'),})
        assert rv.status_code == 200
        assert TEST_KEY in keys['test@example.com']['default']
        
    def test_default_key_delete(self):
        keys['test@example.com']['default'] = TEST_KEY
        rv = self.app.delete('/test@example.com')
        assert rv.status_code == 200

        rv = self.app.get('/test@example.com')
        assert rv.status_code == 404

    def test_default_actions(self):
        rv1 = self.app.get('/test@example.com/upload')
        rv2 = self.app.get('/test@example.com/default/upload')
        assert rv1.data == rv2.data
    
        rv1 = self.app.get('/test@example.com/install')
        rv2 = self.app.get('/test@example.com/default/install')
        assert rv1.data == rv2.data

        keys['test@example.com']['default'] = TEST_KEY
        rv1 = self.app.get('/test@example.com/fingerprint')
        rv2 = self.app.get('/test@example.com/default/fingerprint')
        assert rv1.data == rv2.data

    def test_all_get(self):
        test_key1 = TEST_KEY.replace('test@example.com', 'testkey1')
        test_key2 = TEST_KEY.replace('test@example.com', 'testkey2')
        keys['test@example.com']['a'] = test_key1
        keys['test@example.com']['b'] = test_key2
        rv = self.app.get('/test@example.com/all')
        assert test_key1 in rv.data
        assert test_key2 in rv.data

    def test_all_install(self):
        test_key1 = TEST_KEY.replace('test@example.com', 'testkey1')
        test_key2 = TEST_KEY.replace('test@example.com', 'testkey2')
        keys['test@example.com']['a'] = test_key1
        keys['test@example.com']['b'] = test_key2
        rv = self.app.get('/test@example.com/all/install')
        assert test_key1 in rv.data
        assert test_key2 in rv.data

    def test_named_key_get(self):
        rv = self.app.get('/nobody@example.com/github')
        assert rv.status_code == 404

        keys['test@example.com']['github'] = TEST_KEY
        rv = self.app.get('/test@example.com/github')
        assert TEST_KEY in rv.data

    def test_named_key_put(self):
        rv = self.app.put('/test@example.com/github', data={
            'key': (StringIO(TEST_KEY), 'id_rsa.pub'),})
        assert rv.status_code == 200
        assert TEST_KEY in keys['test@example.com']['github']
        
    def test_named_key_delete(self):
        keys['test@example.com']['github'] = TEST_KEY
        rv = self.app.delete('/test@example.com/github')
        assert rv.status_code == 200

        rv = self.app.get('/test@example.com/github')
        assert rv.status_code == 404

########NEW FILE########
