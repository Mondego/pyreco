__FILENAME__ = apidefinitions
# API method definitions. Used to create MendeleyRemoteMethod instances
methods = {
    ######## Public Resources ########
    'details': {
        'required': ['id'],
        'optional': ['type'],
        'url': '/oapi/documents/details/%(id)s/',
        },
    'categories': {
        'url': '/oapi/documents/categories/',    
        },
    'subcategories': {
        'url': '/oapi/documents/subcategories/%(id)s/',
        'required': ['id'],
        },
    'search': {
        'url': '/oapi/documents/search/%(query)s/',
        'required': ['query'],
        'optional': ['page', 'items'],
        },
    'tagged': {
        'url': '/oapi/documents/tagged/%(tag)s/',
        'required': ['tag'],
        'optional': ['cat', 'subcat', 'page', 'items'],
        },
    'related': {
        'url': '/oapi/documents/related/%(id)s/', 
        'required': ['id'],
        'optional': ['page', 'items'],
        },
    'authored': {
        'url': '/oapi/documents/authored/%(author)s/',
        'required': ['author'],
        'optional': ['page', 'items'],
        },
    'public_groups': {
        'url': '/oapi/documents/groups/',
        'optional': ['page', 'items', 'cat']
        },
    'public_group_details': {
        'url': '/oapi/documents/groups/%(id)s/',
        'required': ['id'],
        },
    'public_group_docs': {
        'url': '/oapi/documents/groups/%(id)s/docs/',
        'required': ['id'],
        'optional': ['details', 'page', 'items'],
        },
    'public_group_people': {
        'url': '/oapi/documents/groups/%(id)s/people/',
        'required': ['id'],
        },
    'author_stats': {
        'url': '/oapi/stats/authors/',
        'optional': ['discipline', 'upandcoming'],
        },
    'paper_stats': {
        'url': '/oapi/stats/papers/',
        'optional': ['discipline', 'upandcoming'],
        },
    'publication_stats': {
        'url': '/oapi/stats/publications/',
        'optional': ['discipline', 'upandcoming'],
        },
    'tag_stats': {
        'url': '/oapi/stats/tags/%(discipline)s/',
        'required': ['discipline'],
        'optional': ['upandcoming'],
        },
    ######## User Specific Resources ########
    'library_author_stats': {
        'url': '/oapi/library/authors/',
        'access_token_required': True,
        },
    'library_tag_stats': {
        'url': '/oapi/library/tags/',
        'access_token_required': True,
        },
    'library_publication_stats': {
        'url': '/oapi/library/publications/',
        'access_token_required': True,
        },
    'library': {
        'url': '/oapi/library/',
        'optional': ['page', 'items'],
        'access_token_required': True,
        },
    'create_document': {
        'url': '/oapi/library/documents/',
        # HACK: 'document' is required, but by making it optional here it'll get POSTed
        # Unfortunately that means it needs to be a named param when calling this method
        'optional': ['document'],
        'access_token_required': True,
        'method': 'post',
        },
    'create_document_from_canonical': {
        'url': '/oapi/library/documents/',
        'optional': ['canonical_id'],
        'access_token_required': True,
        'method': 'post',
        },
    'update_document': {
        'url': '/oapi/library/documents/%(id)s',
        'required': ['id'],
        # HACK: 'document' is required, but by making it optional here it'll get POSTed
        # Unfortunately that means it needs to be a named param when calling this method
        'optional': ['document'],
        'access_token_required': True,
        'method': 'post',
        },
    '_upload_pdf': {
        'url': '/oapi/library/documents/%(id)s/',
        'required': ['id'],
        'optional': ['data', 'file_name', 'oauth_body_hash', 'sha1_hash'],
        'access_token_required': True,
        'method': 'put'
	},
    'download_file': {
        'url': '/oapi/library/documents/%(id)s/file/%(hash)s/',
        'required': ['id', 'hash'],
        'optional' : ['with_redirect'],
        'access_token_required': True,
        'method': 'get'
        },
    'download_file_group': {
        'url': '/oapi/library/documents/%(id)s/file/%(hash)s/%(group)s/',
        'required': ['id', 'hash', 'group'],
        'optional' : ['with_redirect'],
        'access_token_required': True,
        'method': 'get'
        },
    'document_details': {
        'url': '/oapi/library/documents/%(id)s/',
        'required': ['id'],
        'access_token_required': True,
        },
    'documents_authored': {
        'url': '/oapi/library/documents/authored/',
        'access_token_required': True,
        },
    'documents_starred': {
        'url': '/oapi/library/documents/starred/',
        'access_token_required': True,
    },
    'delete_library_document': {
        'url': '/oapi/library/documents/%(id)s/',
        'required': ['id'],
        'access_token_required': True,
        'method': 'delete',
        'expected_status':204,
        },
    'contacts': {
        'url': '/oapi/profiles/contacts/',
        'access_token_required': True,
        'method': 'get',    
        }, 
    'contacts_of_contact': {
        'url': '/oapi/profiles/contacts/%(id)s/', 
        'required': ['id'],
        'access_token_required': True, 
        'method': 'get',
        },
    'add_contact': {
        'url': '/oapi/profiles/contacts/%(id)s/',
        'required': ['id'],
        'access_token_required': True,
        'method': 'post',
        },
    # Folders methods #
    'folders': {
        'url': '/oapi/library/folders/',
        'access_token_required': True,
        },
    'folder_documents': {
        'url': '/oapi/library/folders/%(id)s/',
        'required': ['id'],
        'optional': ['page', 'items'],
        'access_token_required': True,
        },
    'create_folder': {
        'url': '/oapi/library/folders/',
        # HACK: 'folder' is required, but by making it optional here it'll get POSTed
        # Unfortunately that means it needs to be a named param when calling this method
        'optional': ['folder'],
        'access_token_required': True,
        'method': 'post',
        },
    'delete_folder': {
        'url': '/oapi/library/folders/%(id)s/',
        'required': ['id'],
        'access_token_required': True,
        'method': 'delete',
        'expected_status':204,
        },
    'add_document_to_folder': {
        'url': '/oapi/library/folders/%(folder_id)s/%(document_id)s/',
        'required': ['folder_id', 'document_id'],
        'access_token_required': True,
        'method': 'post',
        },
    'delete_document_from_folder': {
        'url': '/oapi/library/folders/%(folder_id)s/%(document_id)s/',
        'required': ['folder_id', 'document_id'],
        'access_token_required': True,
        'method': 'delete',
        'expected_status':204,
        },
    # Groups methods #
    'groups': {
        'url': '/oapi/library/groups/',
        'access_token_required': True,
        },
    'group_documents': {
        'url': '/oapi/library/groups/%(id)s/',
        'required': ['id'],
        'optional': ['page', 'items'],
        'access_token_required': True,
        },
    'group_doc_details': {
        'url': '/oapi/library/groups/%(group_id)s/%(doc_id)s/',
        'required': ['group_id', 'doc_id'],
        'access_token_required': True,
        },
    'group_people': {
        'url': '/oapi/library/groups/%(id)s/people/', 
        'required': ['id'],
        'access_token_required': True,
        },        
    'create_group': {
        'url': '/oapi/library/groups/',
        'optional': ['group'],
        'access_token_required': True,
        'method': 'post',
        },
    'delete_group': {
        'url': '/oapi/library/groups/%(id)s/',
        'required': ['id'],
        'access_token_required': True,
        'method': 'delete',
        'expected_status':204,
        },
    'leave_group': {
        'url': '/oapi/library/groups/%(id)s/leave/', 
        'required': ['id'],
        'access_token_required': True, 
        'method': 'delete',
        },
    'unfollow_group': {
        'url': '/oapi/library/groups/%(id)s/unfollow/', 
        'required': ['id'],
        'access_token_required': True, 
        'method': 'delete',
        },
    'delete_group_document': {
        'url': '/oapi/library/groups/%(group_id)s/%(document_id)s/',
        'required': ['group_id', 'document_id'],
        'access_token_required': True,
        'method': 'delete',
        'expected_status':204,
        },
    # Group Folders methods #
    'group_folders': {
        'url': '/oapi/library/groups/%(group_id)s/folders/',
        'required': ['group_id'],
        'access_token_required': True,
        },
    'group_folder_documents': {
        'url': '/oapi/library/groups/%(group_id)s/folders/%(id)s/',
        'required': ['group_id', 'id'],
        'optional': ['page', 'items'],
        'access_token_required': True,
        },
    'create_group_folder': {
        'url': '/oapi/library/groups/%(group_id)s/folders/',
        'required': ['group_id'],
        # HACK: 'folder' is required, but by making it optional here it'll get POSTed
        # Unfortunately that means it needs to be a named param when calling this method
        'optional': ['folder'],
        'access_token_required': True,
        'method': 'post',
        },
    'delete_group_folder': {
        'url': '/oapi/library/groups/%(group_id)s/folders/%(id)s/',
        'required': ['group_id', 'id'],
        'access_token_required': True,
        'method': 'delete',
        'expected_status':204,
        },
    'add_document_to_group_folder': {
        'url': '/oapi/library/groups/%(group_id)s/folders/%(folder_id)s/%(document_id)s/',
        'required': ['group_id', 'folder_id', 'document_id'],
        'access_token_required': True,
        'method': 'post',
        },
    'delete_document_from_group_folder': {
        'url': '/oapi/library/groups/%(group_id)s/folders/%(folder_id)s/%(document_id)s/',
        'required': ['group_id', 'folder_id', 'document_id'],
        'access_token_required': True,
        'method': 'delete',
        'expected_status':204,
        },
    'profile_info': {
        'url': '/oapi/profiles/info/%(id)s/',
        'required': ['id'],
        'access_token_required': True,
        'method': 'get',    
        }, 

    'my_profile_info': {
        'url': '/oapi/profiles/info/me/',
        'access_token_required': True,
        'method': 'get'
        },
    }

########NEW FILE########
__FILENAME__ = example
#!/usr/bin/env python

"""
Mendeley Open API Example Client

Copyright (c) 2010, Mendeley Ltd. <copyright@mendeley.com>

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

For details of the Mendeley Open API see http://dev.mendeley.com/

Example usage:

python example.py

"""

from pprint import pprint
from mendeley_client import *
import os
import sys

# edit config.json first
mendeley = create_client()

########################################
######## Public Resources Tests ########
########################################

print """

-----------------------------------------------------
Canonical document details
-----------------------------------------------------"""
response = mendeley.details('cbcca150-6cff-11df-a2b2-0026b95e3eb7')
pprint(response)

print """

-----------------------------------------------------
Canonical document details DOI look up
-----------------------------------------------------"""
response = mendeley.details('10.1371%2Fjournal.ppat.1000281', type='doi')
pprint(response)

print """

-----------------------------------------------------
Canonical document details PubMed Id look up
-----------------------------------------------------"""
response = mendeley.details('19910365', type='pmid')
pprint(response)

print """

-----------------------------------------------------
Categories
-----------------------------------------------------"""
response = mendeley.categories()
pprint(response)

print """

-----------------------------------------------------
Subcategories
-----------------------------------------------------"""
response = mendeley.subcategories(3)
pprint(response)

print """

-----------------------------------------------------
Search
-----------------------------------------------------"""
response = mendeley.search('phiC31', items=10)
pprint(response)

print """

-----------------------------------------------------
Tagged 'modularity'
-----------------------------------------------------"""
response = mendeley.tagged('modularity', items=5)
pprint(response)

print """

-----------------------------------------------------
Tagged 'test' in category 14
-----------------------------------------------------"""
response = mendeley.tagged('test', cat=14)
pprint(response)

print """

-----------------------------------------------------
Tagged 'modularity' in subcategory 'Bioinformatics'
-----------------------------------------------------"""
response = mendeley.tagged('modularity', subcat=455)
pprint(response)

print """

-----------------------------------------------------
Related
-----------------------------------------------------"""
response = mendeley.related('91df2740-6d01-11df-a2b2-0026b95e3eb7')
pprint(response)

print """

-----------------------------------------------------
Authored by 'Ann Cowan'
-----------------------------------------------------"""
response = mendeley.authored('Ann Cowan', items=5)
pprint(response)


print """

-----------------------------------------------------
Public groups
-----------------------------------------------------"""
response = mendeley.public_groups()
pprint(response)

groupId = '536181'
print """

-----------------------------------------------------
Public group details
-----------------------------------------------------"""
response = mendeley.public_group_details(groupId)
pprint(response)


print """

-----------------------------------------------------
Public group documents
-----------------------------------------------------"""
response = mendeley.public_group_docs(groupId)
pprint(response)


print """

-----------------------------------------------------
Public group people
-----------------------------------------------------"""
response = mendeley.public_group_people(groupId)
pprint(response)

print """

-----------------------------------------------------
Author statistics
-----------------------------------------------------"""
response = mendeley.author_stats()
pprint(response)


print """

-----------------------------------------------------
Papers statistics
-----------------------------------------------------"""
response = mendeley.paper_stats()
pprint(response)

print """

-----------------------------------------------------
Publications outlets statistics
-----------------------------------------------------"""
response = mendeley.publication_stats()
pprint(response)

###############################################
######## User Specific Resources Tests ########
###############################################

print """

-----------------------------------------------------
My Library authors statistics
-----------------------------------------------------"""
response = mendeley.library_author_stats()
pprint(response)

print """

-----------------------------------------------------
My Library tag statistics
-----------------------------------------------------"""
response = mendeley.library_tag_stats()
pprint(response)

print """

-----------------------------------------------------
My Library publication statistics
-----------------------------------------------------"""
response = mendeley.library_publication_stats()
pprint(response)

### Library ###
print 'Library'
print """

-----------------------------------------------------
My Library documents
-----------------------------------------------------"""
documents = mendeley.library()
pprint(documents)

print """

-----------------------------------------------------
Create a new library document
-----------------------------------------------------"""
response = mendeley.create_document(document={'type' : 'Book','title': 'Document creation test', 'year': 2008})
pprint(response)
documentId = response['document_id']

print """

-----------------------------------------------------
Document details
-----------------------------------------------------"""
response = mendeley.document_details(documentId)
pprint(response)

print """

-----------------------------------------------------
Delete library document
-----------------------------------------------------"""
response = mendeley.delete_library_document(documentId)
pprint(response)

print """

-----------------------------------------------------
Documents authored
-----------------------------------------------------"""
response = mendeley.documents_authored()
pprint(response)

print """

-----------------------------------------------------
Create new folder
-----------------------------------------------------"""
response = mendeley.create_folder(folder={'name': 'Test folder creation'})
pprint(response)
folderId = response['folder_id']

print """

-----------------------------------------------------
Create new child folder
-----------------------------------------------------"""
response = mendeley.create_folder(folder={'name': 'Test child folder creation', 'parent':folderId})
pprint(response)

print """

-----------------------------------------------------
List folders
-----------------------------------------------------"""
folders = mendeley.folders()
pprint(folders)

print """

-----------------------------------------------------
Delete folder
-----------------------------------------------------"""
response = mendeley.delete_folder(folderId)
pprint(response)

print """

-----------------------------------------------------
Create public open group
-----------------------------------------------------"""
response = mendeley.create_group(group={'name':'My awesome public group', 'type': 'open'})
pprint(response)
groupId = response["group_id"]

print """

-----------------------------------------------------
Delete public group
-----------------------------------------------------"""
response = mendeley.delete_group(groupId)
pprint(response)

print """

-----------------------------------------------------
Create private group
-----------------------------------------------------"""
response = mendeley.create_group(group={'name':'Private group test', 'type': 'private'})
pprint(response)
groupId = response['group_id']

print """

-----------------------------------------------------
Create new group folder
-----------------------------------------------------"""
response = mendeley.create_group_folder(groupId, folder={'name': 'Test folder creation'})
pprint(response)
folderId = response['folder_id']

print """

-----------------------------------------------------
Create new child group folder
-----------------------------------------------------"""
response = mendeley.create_group_folder(groupId, folder={'name': 'Test child folder creation', 'parent':folderId})
pprint(response)

print """

-----------------------------------------------------
List group folders
-----------------------------------------------------"""
folders = mendeley.group_folders(groupId)
pprint(folders)

print """

-----------------------------------------------------
Delete group folder
-----------------------------------------------------"""
response = mendeley.delete_group_folder(groupId, folderId)
pprint(response)

print """

-----------------------------------------------------
Delete private group
-----------------------------------------------------"""
response = mendeley.delete_group(groupId)
pprint(response)



print """

-----------------------------------------------------
Current user's profile info
-----------------------------------------------------"""

response = mendeley.my_profile_info()
pprint(response)


print """

-----------------------------------------------------
Current user's contacts
-----------------------------------------------------"""
response = mendeley.contacts()
pprint(response)


########NEW FILE########
__FILENAME__ = mendeley_client
"""
Mendeley Open API Example Client

Copyright (c) 2010, Mendeley Ltd. <copyright@mendeley.com>

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

For details of the Mendeley Open API see http://dev.mendeley.com/

See test.py and the tests in unit-tests/

"""

import hashlib
import json
from rauth import OAuth2Service
import os
import pickle
import requests
import sys
import urllib
import mimetypes

import apidefinitions


def resolve_http_redirect(url):
    # this function is needed to make sure oauth headers are not sent
    # when following redirections. requests only removes the cookies
    # as of 4889adce4e7ea6b9e89fd6059cda2dc7cdf53be8

    # see https://github.com/kennethreitz/requests/blob/develop/requests/models.py#L228
    # for a smarter implementation

    # same as chrome and firefox
    max_redirects = 20

    redirections = 0
    while True:
        redirections += 1
        if redirections > max_redirects:
            raise Exception("Too many redirects (%d)"%redirections)

        response = requests.head(url)
        if "location" in response.headers:
            new_url = response.headers["location"]
            if new_url != url:
                continue
        break
    return url

class OAuthClient(object):
    """General purpose OAuth client"""
    def __init__(self, client_id, client_secret, options=None):
        if options == None: options = {}
        # Set values based on provided options, or revert to defaults
        self.access_token_url = options.get('access_token_url', 'https://api-oauth2.mendeley.com/oauth/token')
        self.authorize_url = options.get('access_token_url', 'https://api-oauth2.mendeley.com/oauth/authorize')
        self.name = options.get('name', 'Example app')
        self.base_url = options.get('base_url', 'https://api-oauth2.mendeley.com')

        self.consumer = OAuth2Service(client_id=client_id,
                client_secret=client_secret,
                name=self.name,
                authorize_url=self.authorize_url,
                access_token_url=self.access_token_url,
                base_url=self.base_url)

    def get_authorize_url(self, redirect_uri="http://localhost"):
        params = {'redirect_uri': redirect_uri,
                'response_type': 'code',
                'scope':'all'}
        return self.consumer.get_authorize_url(**params)

    def get_access_token(self, code, redirect_uri):
        data = {'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri}

        return self.consumer.get_access_token(data=data, decoder=json.loads)

    def get_session(self, access_token):
        return self.consumer.get_session(token=access_token)

    def get(self, path, token=None):
        request = { "method": "GET", "url": path}
        return self._send_request(request, token)

    def post(self, path, post_params, token=None):
        request = { "method": "POST", "url": path}
        return self._send_request(request, token, post_params)

    def delete(self, path, token=None):
        request = { "method": "DELETE", "url": path}
        return self._send_request(request, token)

    def put(self, path, token=None, body=None, headers=None):
        request = { "method": "PUT", "url": path}
        return self._send_request(request, token, body, headers)

    def _send_request(self, request, token=None, body=None, extra_headers=None):
        session = self.get_session(token)

        # common arguments for the requests call
        # disables automatic redirections following as requests
        # to use resolve_http_redirect(..) above
        requests_args = {"allow_redirects":False}
        method = request.get("method")
        url = request.get("url")

        if method == 'GET':
            return session.get(url, **requests_args)

        if method == 'POST':
            return session.post(url, data=body, headers={"Content-type": "application/x-www-form-urlencoded"},**requests_args )

        elif method == 'DELETE':
            return session.delete(url, **requests_args)

        elif method == 'PUT':
            return session.put(url, data=body, headers=extra_headers, **requests_args)

        assert False

class MendeleyRemoteMethod(object):
    """Call a Mendeley OpenAPI method and parse and handle the response"""
    def __init__(self, details, callback):
        self.details = details # Argument, URL and additional details.
        self.callback = callback # Callback to actually do the remote call

    def serialize(self, obj):
        if isinstance(obj,dict):
            return json.dumps(obj)
        return obj

    def __call__(self, *args, **kwargs):
        url = self.details['url']
        # Get the required arguments
        if self.details.get('required'):
            required_args = dict(zip(self.details.get('required'), args))
            if len(required_args) < len(self.details.get('required')):
                raise ValueError('Missing required args')

            for (key, value) in required_args.items():
                required_args[key] = urllib.quote_plus(str(value))

            url = url % required_args

        # Optional arguments must be provided as keyword args
        optional_args = {}
        for optional in self.details.get('optional', []):
            if kwargs.has_key(optional):
                optional_args[optional] = self.serialize(kwargs[optional])

        # Do the callback - will return a HTTPResponse object
        response = self.callback(url, self.details.get('access_token_required', True), self.details.get('method', 'get'), optional_args)

        # basic redirection following
        if response.status_code in [301, 302, 303]:
            url = resolve_http_redirect(response.headers["location"])
            response = requests.get(url)

        # if we expect something else than 200 with no content, just check
        # that the status code is as expected
        status = response.status_code
        expected_status = self.details.get("expected_status",200)
        if expected_status != 200:
            return status == expected_status

        # if the request failed, return all the request instead of just the body
        if status == 401:
            print 'Access token expired, please remove the .pkl file and try again.'
            print response.content
            return response

        if status in [400, 403, 404, 405]:
            return response

        content_type = response.headers["Content-Type"]
        ct = content_type.split("; ")
        mime = ct[0]
        attached = None
        try:
            content_disposition = response.headers["Content-Disposition"]
            cd = content_disposition.split("; ")
            attached = cd[0]
            filename = cd[1].split("=")
            filename = filename[1].strip('"')
        except:
            pass

        if mime == 'application/json':
            return json.loads(response.text)
        elif attached == 'attachment':
            return {'filename': filename, 'data': response.content}
        else:
            return response

class MendeleyAccount:

    def __init__(self, access_token):
        self.access_token = access_token

class MendeleyTokensStore:

    def __init__(self, filename='mendeley_api_keys.pkl'):
        self.filename = filename
        self.accounts = {}

        if self.filename:
            self.load()

    def __del__(self):
        if self.filename:
            self.save()

    def add_account(self, key, access_token):
        self.accounts[key] = MendeleyAccount(access_token)

    def get_account(self, key):
        return self.accounts.get(key, None)

    def get_access_token(self, key):
        if not key in self.accounts:
            return None
        return self.accounts[key].access_token

    def remove_account(self, key):
        if not key in self.accounts:
            return
        del self.accounts[key]

    def save(self):
        if not self.filename:
            raise Exception("Need to specify a filename for this store")
        pickle.dump(self.accounts, open(self.filename, 'w'))

    def load(self):
        if not self.filename:
            raise Exception("Need to specify a filename for this store")
        try:
            self.accounts = pickle.load(open(self.filename, 'r'))
        except IOError:
            print "Can't load tokens from %s"%self.filename

class MendeleyClientConfig:

    def __init__(self, filename='config.json'):
        self.filename = filename
        self.load()

    def is_valid(self):
        if not hasattr(self,"client_id") or not hasattr(self, "client_secret"):
            return False

        if self.client_id == "<change me>" or self.client_secret == "<change me>":
            return False

        return True

    def load(self):
        loaded = json.loads(open(self.filename,'r').read())
        for key, value in loaded.items():
            setattr(self, key, value.encode("ascii"))

class MendeleyClient(object):

    def __init__(self, client_id, client_secret, options=None):
        self.oauth_client = OAuthClient(client_id, client_secret, options)

        # Create methods for all of the API calls
        for method, details in apidefinitions.methods.items():
            setattr(self, method, MendeleyRemoteMethod(details, self._api_request))

    # replace the upload_pdf with a more user friendly method
    def upload_pdf(self,document_id, filename):

        fp = open(filename, 'rb')
        data = fp.read()

        hasher = hashlib.sha1()
        hasher.update(data)
        sha1_hash = hasher.hexdigest()

        return self._upload_pdf(document_id,
                            file_name=os.path.basename(filename),
                            sha1_hash=sha1_hash,
                            data=data)

    def _api_request(self, url, access_token_required = False, method='get', params=None):
        if params == None:
            params = {}

        access_token = None
        if access_token_required:
            access_token = self.get_access_token()

        if method == 'get':
            if len(params) > 0:
                url += "?%s" % urllib.urlencode(params)
            response = self.oauth_client.get(url, access_token)
        elif method == 'delete':
            response = self.oauth_client.delete(url, access_token)
        elif method == 'put':
            [content_type, encoding] = mimetypes.guess_type(params.get('file_name'))
            headers = {'Content-disposition': 'attachment; filename="%s"' % params.get('file_name'), 'Content-Type': content_type}
            response = self.oauth_client.put(url, access_token, params.get('data'), headers)
        elif method == 'post':
            response = self.oauth_client.post(url, params, access_token)
        else:
            raise Exception("Unsupported method: %s"%method)
        return response

    def set_access_token(self, access_token):
        self.access_token = access_token

    def get_access_token(self):
        return self.access_token

    def get_auth_url(self,callback_url="http://localhost"):
        """Returns an auth url"""
        return self.oauth_client.get_authorize_url(callback_url)

    def exchange_access_token(self, code):
        """Generate an access_token from a request_token generated by
           get_auth_url and the verifier received from the server"""
        try :
            access_token = self.oauth_client.get_access_token(code, "http://localhost")
            print access_token
        except Exception as e:
            print "exchange_access_token"
            print e
        return access_token

    def interactive_auth(self):
        auth_url = self.get_auth_url()
        print 'Go to the following url to auth the token:\n%s' % (auth_url,)
        code = raw_input('Enter code: ')
        self.set_access_token(self.exchange_access_token(code))

def create_client(config_file="config.json", keys_file=None, account_name="test_account"):
    # Load the configuration file
    config = MendeleyClientConfig(config_file)
    if not config.is_valid():
        print "Please edit config.json before running this script"
        sys.exit(1)

    # create a client and load tokens from the pkl file
    host = "api-oauth2.mendeley.com"
    if hasattr(config, "host"):
        host = config.host

    if not keys_file:
        keys_file = "keys_%s.pkl"%host

    client = MendeleyClient(config.client_id, config.client_secret, {"host":host})
    tokens_store = MendeleyTokensStore(keys_file)

    # configure the client to use a specific token
    # if no tokens are available, prompt the user to authenticate
    access_token = tokens_store.get_access_token(account_name)
    if not access_token:
        try:
            client.interactive_auth()
            tokens_store.add_account(account_name,client.get_access_token())
        except Exception as e:
            print e
            sys.exit(1)
    else:
        client.set_access_token(access_token)
    return client

########NEW FILE########
__FILENAME__ = imap
"""
The MIT License

Copyright (c) 2007-2010 Leah Culver, Joe Stump, Mark Paschal, Vic Fryzel

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import oauth2
import imaplib


class IMAP4_SSL(imaplib.IMAP4_SSL):
    """IMAP wrapper for imaplib.IMAP4_SSL that implements XOAUTH."""

    def authenticate(self, url, consumer, token):
        if consumer is not None and not isinstance(consumer, oauth2.Consumer):
            raise ValueError("Invalid consumer.")

        if token is not None and not isinstance(token, oauth2.Token):
            raise ValueError("Invalid token.")

        imaplib.IMAP4_SSL.authenticate(self, 'XOAUTH',
            lambda x: oauth2.build_xoauth_string(url, consumer, token))

########NEW FILE########
__FILENAME__ = smtp
"""
The MIT License

Copyright (c) 2007-2010 Leah Culver, Joe Stump, Mark Paschal, Vic Fryzel

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import oauth2
import smtplib
import base64


class SMTP(smtplib.SMTP):
    """SMTP wrapper for smtplib.SMTP that implements XOAUTH."""

    def authenticate(self, url, consumer, token):
        if consumer is not None and not isinstance(consumer, oauth2.Consumer):
            raise ValueError("Invalid consumer.")

        if token is not None and not isinstance(token, oauth2.Token):
            raise ValueError("Invalid token.")

        self.docmd('AUTH', 'XOAUTH %s' % \
            base64.b64encode(oauth2.build_xoauth_string(url, consumer, token)))

########NEW FILE########
__FILENAME__ = synced_client
from mendeley_client import *

class SyncStatus:
    Deleted = 0
    Modified = 1
    New = 2
    Synced = 3   

    @staticmethod
    def to_str(status):
        return ["DEL","MOD","NEW","SYN"][status]

class Object:
    pass

class SyncedObject:

    def __init__(self, obj, status=SyncStatus.New):
        self.reset(obj, status)
        
    def reset(self, obj, status):
        self.changes = {}
        self.status = status

        if isinstance(obj, dict):
            self.object = Object()
            for key in obj.keys():
                setattr(self.object, key, obj[key])
        elif isinstance(obj, SyncedObject):
            self.object = obj.object
        else:
            assert False

    def version(self):
        if not hasattr(self.object, "version"):
            return None
        return self.object.version

    def id(self):
        if not hasattr(self.object, "id"):
            return None
        return self.object.id

    def update(self, change):
        if len(change.keys()) == 0:
            return
        # TODO add some checking of the keys etc
        for key, value in change.items():
            self.changes[key] = value
        
        self.status = SyncStatus.Modified

    def apply_changes(self):
        if len(self.changes) == 0:
            return

        for key, value in self.changes.items():
            setattr(self.object, key, value)

    def to_json(self):
        obj = {}
        for key in vars(self.object):
            obj[key] = getattr(self.object,key)
        return obj

    def is_deleted(self):
        return self.status == SyncStatus.Deleted

    def is_modified(self):
        return self.status == SyncStatus.Modified

    def is_new(self):
        return self.status == SyncStatus.New

    def is_synced(self):
        return self.status == SyncStatus.Synced

    def delete(self):
        self.status = SyncStatus.Deleted
        
class SyncedFolder(SyncedObject):
    pass

class SyncedDocument(SyncedObject):

    document_fields = [
        "abstract", "advisor", "applicationNumber", "articleColumn", "arxiv", 
        "authors", "cast", "chapter", "citation_key", "city", "code", "codeNumber", 
        "codeSection", "codeVolume", "committee", "counsel", "country", "date", 
        "dateAccessed", "day", "department", "doi", "edition", "editors", "genre", 
        "institution", "internationalAuthor", "internationalNumber", "internationalTitle", 
        "internationalUserType", "isbn", "issn", "issue", "isRead", "isStarred", "keywords", 
        "language", "lastUpdate", "legalStatus", "length", "medium", "month", "notes", 
        "original_publication", "owner", "pages", "pmid", "producers", "publicLawNumber", 
        "published_in", "publisher", "reprint_edition", "reviewedArticle", "revision", 
        "sections", "series", "seriesEditor", "seriesNumber", "session", "short_title", 
        "source_type", "tags", "time", "title", "translators", "type","userType", "volume", 
        "website", "year"
        ]

    def __str__(self):
        return self.object.id

    def to_json(self):
        obj = {}

        for key in vars(self.object):
            if key in SyncedDocument.document_fields:
                obj[key] = getattr(self.object,key)
        return obj

class ConflictResolver:

    def resolve_both_updated(self, local_document, remote_document):
        """Update local_document from remote_document as needed. 
           If the local_document status is modified after the resolution
           the changes will be applied to the remote_document in sync()

           no return value
           """
        raise Exception("Reimplement me")

    def resolve_local_delete_remote_update(self, local_document, remote_document):
        """Return a boolean to decide if the remote version should be kept"""
        raise Exception("Reimplement me")

    def resolve_local_update_remote_delete(self, local_document):
        """Return a boolean to decide if the local version should be recreated"""
        raise Exception("Reimplement me")

class SimpleConflictResolver(ConflictResolver):
    """Example implementation of ConflictResolver with conservative settings
       It keeps modified documents vs deleted ones and keeps remote data in case
       of both documents modifying the same field"""

    def resolve_local_delete_remote_update(self, local_document, remote_document):
        keep_remote_document = True
        return keep_remote_document

    def resolve_local_update_remote_delete(self, local_document):
        recreate_local_document = True
        return recreate_local_document

    def resolve_both_updated(self, local_document, remote_document):
        assert isinstance(remote_document, SyncedDocument)
        assert isinstance(local_document, SyncedDocument)

        local_changes = local_document.changes

        for key in vars(remote_document.object):
            remote_value = getattr(remote_document.object, key)
            if hasattr(local_document.object, key):
                local_value = getattr(local_document.object, key)
                if local_value == remote_value:
                    # nothing changed
                    continue

                # apply the remote change
                setattr(local_document.object, key, remote_value)

                if key not in local_changes:
                    # no conflict, no need to resolve anything
                    continue
                
                # the local and remote documents have modified the same field
                keep_remote_version = self.resolve_conflict(key, local_changes[key], remote_value)

                if keep_remote_version:
                    # get rid of the local changes
                    del local_changes[key]
                else:
                    # the document status will stay modified and will send its
                    # change to the remote in sync_documents
                    pass

        # the local_document data now is in sync with the remote_document
        assert local_document.version() == remote_document.version()

        # if no local changes are left, the document isn't modified anymore
        if len(local_changes) == 0:
            local_document.status = SyncStatus.Synced
        else:
            # local changes will be applied in sync_documents
            pass

    def resolve_conflict(self, key, local_version, remote_version):
        # dumb "resolution", 
        return False

class DummySyncedClient:

    def __init__(self, config_file="config.json", conflict_resolver=SimpleConflictResolver()):
        self.client = create_client(config_file)
        self.folders = {}
        self.documents = {}
        self.new_documents = []
        assert isinstance(conflict_resolver, ConflictResolver)
        self.conflict_resolver = conflict_resolver

    def sync(self):
        success = False
        
        while True:
            # if not self.sync_folders():
            #     continue
            if not self.sync_documents():
                continue
            break

    def fetch_document(self, remote_id):
        details = self.client.document_details(remote_id)
        assert "error" not in details
        assert details["id"] == remote_id  
        return SyncedDocument(details, SyncStatus.Synced)

    def push_new_local_document(self, local_document):
        # create the local document on the remote
        existing_id = local_document.id()

        # it's a new document, or the conflict resolver decided 
        # to keep the local version so needs to be reset
        response = self.client.create_document(document=local_document.to_json())
        assert "error" not in response

        local_document.object.version = response["version"]
        local_document.object.id = response["document_id"]
        local_document.status = SyncStatus.Synced

        if existing_id is not None:
            del self.documents[existing_id]
        self.documents[local_document.id()] = local_document
        return local_document.id()

    def add_new_local_document(self, document_details):
        document = SyncedDocument(document_details)
        self.new_documents.append(document)
        return document

    def sync_documents(self):
        # TODO fetch the whole library with paging
        # validate folders before storing, restart sync if unknown folder

        remote_documents = self.client.library()
        assert "error" not in remote_documents
        remote_ids = []

        def sync_remote_changes():

            for remote_document_dict in remote_documents["documents"]:
                remote_id = remote_document_dict["id"]
                remote_document = SyncedDocument(remote_document_dict, SyncStatus.Synced)
                remote_ids.append(remote_id)
                if remote_id not in self.documents:
                    # new document
                    self.documents[remote_id] = self.fetch_document(remote_id)
                    assert self.documents[remote_id].object.id == remote_id
                    continue

                local_document = self.documents[remote_id]

                # server can't know about new documents
                assert not local_document.is_new()

                # if remote version is more recent
                if local_document.version() != remote_document.version():
                    remote_document = self.fetch_document(remote_id)
                    if local_document.is_deleted():
                        keep_remote = self.conflict_resolver.resolve_local_delete_remote_update(local_document, remote_document)
                        if keep_remote:
                            self.documents[remote_id].reset(remote_document, SyncStatus.Synced)
                        else:
                            # will be deleted later
                            pass
                        continue

                    if local_document.is_synced():
                        # update from remote
                        local_document.reset(remote_document, SyncStatus.Synced)
                        continue

                    if local_document.is_modified():
                        # both documents are modified, resolve the conflict
                        # by handling the remote changes required and leave the local 
                        # changes to be synced later
                        self.conflict_resolver.resolve_both_updated(local_document, remote_document)
                        assert isinstance(local_document, SyncedDocument)
                        assert isinstance(remote_document, SyncedDocument)
                        assert local_document.version() == remote_document.version()
                        continue

                    # all cases should have been handled
                    assert False

                # both have the same version, so only local changes possible
                else:
                    if local_document.is_synced():
                        # nothing to do
                        # assert remote_document == local_document
                        continue

                    if local_document.is_deleted():
                        # nothing to do, will be deleted
                        continue

                    if local_document.is_modified():
                        # nothing to do, changes will be sent in the update loop
                        continue

                    # all cases should have been handled
                    assert False
    
        def sync_local_changes():
            # deal with local changes or remote deletion
            for doc_id in self.documents.keys():
                local_document = self.documents[doc_id]
                assert local_document.id() == doc_id

                # new documents are handled later
                assert not local_document.is_new()

                if doc_id not in remote_ids:
                    # was deleted on the server         
                    if local_document.is_modified():
                        recreate_local = self.conflict_resolver.resolve_local_update_remote_delete(local_document)
                        if recreate_local:
                            remote_ids.append(self.push_new_local_document(local_document))
                            continue
                    del self.documents[doc_id]
                    continue   

                if local_document.is_synced():
                    continue                 

                if local_document.is_deleted():
                    assert self.client.delete_library_document(doc_id)
                    del self.documents[doc_id]
                    continue

                if local_document.is_modified():
                    response = self.client.update_document(doc_id, document=local_document.changes)
                    assert "error" not in response
                    local_document.status = SyncStatus.Synced
                    local_document.object.version = response["version"]
                    local_document.apply_changes()
                    continue

                assert False

        def send_new_documents():
            # create new local documents on the server
            for new_document in self.new_documents:
                assert new_document.is_new()
                doc_id = self.push_new_local_document(new_document)
                assert doc_id > 0
            self.new_documents = []

            
        sync_remote_changes()
        sync_local_changes()
        send_new_documents()

        return True

    def reset(self):
        self.documents = {}
        self.folders = {}

    def dump_status(self,outf):
        outf.write( "\n")
        outf.write( "#Documents (%d)\n"%len(self.documents))
        outf.write( "@sort 0,-2\n")
        outf.write( "@group 0\n")
        outf.write( "--\n")
        outf.write( "status, id, version, title\n")
        if len(self.documents)+len(self.new_documents):

            for doc_id, document in self.documents.items():
                if document.is_modified():
                    outf.write("# changes: %s\n"%document.changes)
                outf.write( "%s,  %s ,  %s , %s\n"%(SyncStatus.to_str(document.status), document.id(), document.version(), document.object.title))
            for document in self.new_documents:
                outf.write( "%s,  %s ,  %s , %s\n"%(SyncStatus.to_str(document.status), document.id(), document.version(), document.object.title))

########NEW FILE########
__FILENAME__ = test-basics
import sys
import unittest
import os

parent_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")
os.sys.path.insert(0, parent_dir) 

from mendeley_client import *
from utils import test_prompt

class TestMendeleyClient(unittest.TestCase):

    client = create_client("../config.json")

    def clear_groups(self):
        for group in self.client.groups():
            self.client.delete_group(group["id"])
    
    def clear_folders(self):
        folders = self.client.folders()
        self.assertTrue("error" not in folders)
        for folder in self.client.folders():
            self.client.delete_folder(folder["id"])

    def clear_library(self):
        for doc in self.client.library()["document_ids"]:
            self.client.delete_library_document(doc)

    def is_folder(self, folder_id):
        ret = [f for f in self.client.folders() if f["id"] == folder_id]
        return len(ret) == 1

    @classmethod
    def setUpClass(self):
        self.client = create_client("../config.json")

    def tearDown(self):
        self.clear_folders()
        self.clear_groups()
        self.clear_library()
        
    ## Test Groups ##

    def test_create_open_groups(self):
        # Check that the user can create more than 2 open groups
        for i in range(5):
            self.assertTrue("error" not in self.client.create_group(group={"name":"test_open_group_%d"%i, "type":"open"}))

    def test_create_restricted_groups(self):

        # check that the user can't create more than 2 restricted groups
        types = ["private", "invite"]

        for group_type1 in types:
            first_group = self.client.create_group(group={"name":"test", "type":group_type1})
            self.assertTrue("group_id" in first_group)

            for group_type2 in types:
                response = self.client.create_group(group={"name":"test", "type":group_type2})
                self.assertEquals(response.status_code, 403)
            self.client.delete_group(first_group["group_id"])

    def test_create_group(self):
        # check that the user can create several open groups and one restricted group
        types = ["private", "invite"]
        for i in range(3):
            self.client.create_group(group={"name":"public_group_%d"%i, "type":"open"})
        for group_type in types:
            response = self.client.create_group(group={"name":"test_%s"%group_type, "type":group_type})
            self.assertTrue("error" not in response)
            self.client.delete_group(response["group_id"])


    ## Test Folder ##

    def test_create_folder_name_already_used(self):
        # check that the user can create two folders with the same name
        self.clear_folders()
        self.client.create_folder(folder={"name": "test"})
        rep = self.client.create_folder(folder={"name": "test"})
        self.assertFalse("error" in rep)

    def test_create_folder_valid(self):
        # check that the user can create folder
        folder_name = "test"
        rep = self.client.create_folder(folder={"name": folder_name})
        folder_id = rep["folder_id"]
        folder_ = [folder for folder in self.client.folders() if folder["id"] == folder_id]
        self.assertEquals(folder_name, folder_[0]["name"])

    def test_delete_folder_valid(self):
        # check that the user can delete folder
        folder_name = "test"
        rep = self.client.create_folder(folder={"name": folder_name})
        folder_id = rep["folder_id"]
        resp = self.client.delete_folder(folder_id)
        self.assertTrue("error" not in rep)

    def test_delete_folder_invalid(self):
        # check that the user can't delete a folder owned by an other user (or non-existent)
        invalid_ids = ["1234567890123", "-1234567890123", "-1", "","some string"]
        for invalid_id in invalid_ids:
            self.assertFalse(self.client.delete_folder(invalid_id))

    def test_parent_folder(self):
        parent_id = None
        folder_ids = []

        # create top level folder and 3 children
        for i in range(4):
            data={"name": "folder_%d"%i}
            if parent_id:
                data["parent"] = parent_id
            folder = self.client.create_folder(folder=data)
            self.assertTrue("folder_id" in folder)
            if parent_id:
                self.assertTrue("parent" in folder and str(folder["parent"]) == parent_id)

            # update the list of folder_ids
            folder_ids.append(folder["folder_id"])
            parent_id = folder_ids[-1]

        # delete last folder and check it"s gone and that its parent still exists
        response = self.client.delete_folder(folder_ids[-1])
        self.is_folder(folder_ids[-1])
        del folder_ids[-1]
        self.assertTrue(response)

        # add another folder on the bottom and delete its parent
        # check both are deleted and grandparent still ok
        parent_id = folder_ids[-1]
        grandparent_id = folder_ids[-2]

        #  Create the new folder
        folder = self.client.create_folder(folder={"name":"folder_4", "parent":parent_id})
        new_folder_id = folder["folder_id"]
        folder_ids.append(new_folder_id)
        self.assertTrue("parent" in folder and str(folder["parent"]) == parent_id)

        #  Delete the parent and check the parent and new folder are deleted
        deleted = self.client.delete_folder(parent_id)
        self.assertTrue(deleted)
        self.assertFalse(self.is_folder(new_folder_id))
        del folder_ids[-1] # new_folder_id
        self.assertFalse(self.is_folder(parent_id))
        del folder_ids[-1] # parent_id
        self.assertTrue(self.is_folder(grandparent_id))

        # delete top level folder and check all children are deleted
        top_folder = self.client.delete_folder(folder_ids[0])
        for folder_id in folder_ids:
            self.assertFalse(self.is_folder(folder_id))

        self.assertEqual(len(self.client.folders()), 0)

    ## Test Other ##

    def test_get_starred_documents(self):
        document = self.client.create_document(document={"type" : "Book","title": "starred_doc_test", "year": 2025, "isStarred": 1})
        self.assertTrue("document_id" in document)
        self.assertTrue("version" in document)

        response = self.client.documents_starred()
        self.assertEquals(response["documents"][0]["id"], document["document_id"])
        self.assertEquals(response["documents"][0]["version"], document["version"])

    def test_create_doc_from_canonical(self):
        canonical_id = "eaede082-7d8b-3f0c-be3a-fb7be685fbe6"
        document = self.client.create_document_from_canonical(canonical_id=canonical_id)
        self.assertTrue("document_id" in document)
        self.assertTrue("version" in document)

        canonical_metadata = self.client.details(canonical_id)
        library_metadata = self.client.document_details(document["document_id"])

        self.assertEquals(canonical_metadata["title"], library_metadata["title"])

    def test_add_doc_to_folder_valid(self):
        document = self.client.create_document(document={"type" : "Book","title": "doc_test", "year": 2025})
        doc_id = document["document_id"]
        folder = self.client.create_folder(folder={"name": "Test"})
        folder_id = folder["folder_id"]
        response = self.client.add_document_to_folder(folder_id, doc_id)
        self.assertTrue("error" not in response )

    def test_add_doc_to_folder_invalid(self):
        document = self.client.create_document(document={"type" : "Book","title": "doc_test", "year": 2025})
        document_id = document["document_id"]
        invalid_folder_ids = ["some string", "-1", "156484", "", "-2165465465"]
        for invalid_folder_id in invalid_folder_ids:
            response = self.client.add_document_to_folder(invalid_folder_id, document_id)
            self.assertTrue(response.status_code == 404 or response.status_code == 400)

        folder = self.client.create_folder(folder={"name": "Test"})
        self.assertTrue("error" not in folder)

        invalid_document_ids = ["some string", "-1", "156484", "", "-2165465465"]

        folder_id = folder["folder_id"]

        for invalid_document_id in invalid_document_ids:
            response = self.client.add_document_to_folder(folder_id, invalid_document_id)
            self.assertTrue(response.status_code == 404 or response.status_code == 400)

    def test_download_invalid(self):
        self.assertEquals(self.client.download_file("invalid", "invalid").status_code, 400)

    def test_upload_pdf(self):
        file_to_upload = "../example.pdf"

        hasher = hashlib.sha1()
        hasher.update(open(file_to_upload, "rb").read())
        expected_file_hash = hasher.hexdigest()
        expected_file_size = str(os.path.getsize(file_to_upload))

        response = self.client.create_document(document={"type":"Book", "title":"Ninja gonna be flyin"})
        self.assertTrue("error" not in response)
        document_id = response["document_id"]

        # upload the pdf
        upload_result = self.client.upload_pdf(document_id, file_to_upload)

        # get the details and check the document now has files
        details = self.client.document_details(document_id)
        self.assertEquals(len(details["files"]), 1)

        document_file = details["files"][0]
        self.assertEquals(document_file["file_extension"], "pdf")
        self.assertEquals(document_file["file_hash"], expected_file_hash)
        self.assertEquals(document_file["file_size"], expected_file_size)

        # delete the document
        self.assertTrue(self.client.delete_library_document(document_id))

    def test_download_pdf(self):
        file_to_upload = "../example.pdf"

        hasher = hashlib.sha1(open(file_to_upload, "rb").read())
        expected_file_hash = hasher.hexdigest()
        expected_file_size = os.path.getsize(file_to_upload)

        response = self.client.create_document(document={"type":"Book", "title":"Ninja gonna be flyin"})
        self.assertTrue("error" not in response)
        document_id = response["document_id"]

        # upload the pdf
        upload_result = self.client.upload_pdf(document_id, file_to_upload)
        
        def download_and_check(with_redirect):
            # download the file back
            response = self.client.download_file(document_id, expected_file_hash, with_redirect=with_redirect)
            self.assertTrue("data" in response and "filename" in response)

            # check that the downloaded file is the same as the uploaded one
            data = response['data']
            size = len(data)
            actual_file_hash = hashlib.sha1(data).hexdigest()
            self.assertEquals(size, expected_file_size)
            self.assertEquals(actual_file_hash, expected_file_hash)

        download_and_check(with_redirect="true")
        download_and_check(with_redirect="false")


if __name__ == "__main__":
    if not test_prompt():
        print "Aborting"
        sys.exit(1)
    print ""
    unittest.main()

########NEW FILE########
__FILENAME__ = test-sync
from multiprocessing import Pool
import os
import sys
import unittest

from utils import *
parent_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")
os.sys.path.insert(0, parent_dir) 
from synced_client import *

class TestEnv:
    sclient = None
    debug = True 
    # introduce a 1sec sleep when updating a document just after it has been created to
    # avoid version conflicts due to timestamp precision while WWW-8681 is fixed
    sleep_time = 1
    log_file = open("test-sync.log","w")

    @staticmethod
    def clear_library():
        p = Pool()
        p.map(remove_document, TestEnv.sclient.client.library()["document_ids"])

    @staticmethod
    def seed_library(count):
        p = Pool()
        ids = p.map(create_test_doc, range(count))
        assert len(ids) == count
        return ids

def create_test_doc(index):
    response = TestEnv.sclient.client.create_document(document={"type":"Book", "title":"Title %d"%index})
    return response["document_id"]

def remove_document(document_id):
    assert TestEnv.sclient.client.delete_library_document(document_id)

class TestDocumentsSyncing(unittest.TestCase):

    def log_status(self, message):
        if TestEnv.debug:
            TestEnv.log_file.write("\n#%s\n"%message)
            TestEnv.log_file.write("#"+"-"*len(message)+"\n\n")
            TestEnv.sclient.dump_status(TestEnv.log_file)

    def sync(self):
        self.log_status("Before sync")
        TestEnv.sclient.sync()
        self.log_status("After sync")        

    def document_exists(self, document_id):
        details = TestEnv.sclient.client.document_details(document_id)
        return isinstance(details, dict) and "error" not in details 
      
    def setUp(self):
        TestEnv.clear_library()
    
    def test_fetch(self):
        count = 5
        ids = TestEnv.seed_library(count)
        
        # sync, should have count documents with matching ids
        TestEnv.sclient.sync()
        self.assertEqual(len(TestEnv.sclient.documents), count)
        self.assertEqual(sorted(ids), sorted(TestEnv.sclient.documents.keys()))

        # the status of all documents should be synced
        for document in TestEnv.sclient.documents.values():
            self.assertTrue(document.is_synced())

    def test_new_local(self):
        count = 5
        ids = TestEnv.seed_library(count)
        TestEnv.sclient.sync()

        # add a new local document
        document = TestEnv.sclient.add_new_local_document({"type":"Book", "title":"new local document"})
        self.assertTrue(document.is_new())
        self.assertEqual(len(TestEnv.sclient.new_documents), 1)
        self.assertEqual(len(TestEnv.sclient.documents), count)

        self.sync()

        self.assertTrue(document.is_synced())
        self.assertEqual(len(TestEnv.sclient.new_documents), 0)
        self.assertEqual(len(TestEnv.sclient.documents), count+1)
        
    def test_local_delete(self):
        count = 5
        ids = TestEnv.seed_library(count)
        TestEnv.sclient.sync()

        # locally delete 1 document
        deletion_id = ids[count/2]
        local_document = TestEnv.sclient.documents[deletion_id]
        local_document.delete()
        # the status of the document should be deleted, the count
        # should stay the same until synced
        self.assertTrue(local_document.is_deleted())
        self.assertEqual(len(TestEnv.sclient.documents), count)
        
        # check that the status of the documents are correct
        for docid, document in TestEnv.sclient.documents.items():
            if docid == deletion_id:
                self.assertTrue(document.is_deleted())
            else:
                self.assertTrue(document.is_synced())

        # sync the deletion
        self.sync()
        
        # make sure the document doesn't exist anymore 
        self.assertEqual(len(TestEnv.sclient.documents), count-1)
        self.assertTrue(deletion_id not in TestEnv.sclient.documents.keys())

        # make sure the other documents are unaffected
        for document in TestEnv.sclient.documents.values():
            self.assertTrue(document.is_synced())
            self.assertTrue(document.id() in ids)
            self.assertTrue(document.id() != deletion_id)
        
        # check on the server that the deletion was done
        for doc_id in ids:
            if doc_id == deletion_id:
                self.assertFalse(self.document_exists(doc_id))
            else:
                self.assertTrue(self.document_exists(doc_id))
                
    def test_server_delete(self):
        count = 5 
        ids = TestEnv.seed_library(count)
        TestEnv.sclient.sync()

        # delete one doc on the server
        TestEnv.sclient.client.delete_library_document(ids[0])
        self.assertFalse(self.document_exists(ids[0]))

        self.sync()

        self.assertEqual(len(TestEnv.sclient.documents), count-1)
        self.assertTrue(ids[0] not in TestEnv.sclient.documents.keys())

        for doc_id in ids[1:]:
            self.assertTrue(doc_id in TestEnv.sclient.documents.keys())
            self.assertTrue(TestEnv.sclient.documents[doc_id].is_synced())

    def test_local_update_remote_delete(self):
        new_local_title = "updated_local_title"
        count = 5 
        ids = TestEnv.seed_library(count)
        TestEnv.sclient.sync()  

        local_document = TestEnv.sclient.documents[ids[0]]
        original_version = local_document.version()

        # do a remote delete
        response = TestEnv.sclient.client.delete_library_document(ids[0])
        self.assertFalse(self.document_exists(ids[0]))
        self.assertTrue(local_document.is_synced())

        # do a local update
        local_document.update({"title":new_local_title})
        self.assertTrue(local_document.is_modified())

        self.sync()
        
        # the default conflict resolver should recreate the local version
        self.assertTrue(local_document.is_synced())
        
        # the "new" document should have a different id and version
        self.assertNotEqual(local_document.id(), ids[0])
        self.assertNotEqual(local_document.version(), original_version)    
        self.assertFalse(self.document_exists(ids[0]))  
        self.assertEqual(len(TestEnv.sclient.documents), count)

    def test_local_delete_remote_update(self):
        new_remote_title = "updated_remote_title"
        count = 5 
        ids = TestEnv.seed_library(count)
        TestEnv.sclient.sync()  

        local_document = TestEnv.sclient.documents[ids[0]]
        original_version = local_document.version()

        # do a remote update
        time.sleep(TestEnv.sleep_time)  # see comment in TestEnv
        response = TestEnv.sclient.client.update_document(ids[0], document={"title":new_remote_title})
        remote_version = response["version"]
        self.assertTrue("error" not in response)
        self.assertTrue(remote_version > original_version)
        self.assertTrue(local_document.is_synced())

        # delete the local document
        local_document.delete()
        self.assertTrue(local_document.is_deleted())

        self.sync()
        
        # the default conflict resolver should keep the server version if more recent
        self.assertTrue(local_document.is_synced())
        self.assertEqual(local_document.version(), remote_version)

        # check that the document is still on the server
        self.assertTrue(self.document_exists(ids[0]))
    
    def test_local_update_remote_update_no_conflict(self):
        # update different fields locally and remotely
        new_remote_title = "updated_remote_title"
        new_local_year = 1997

        count = 5 
        ids = TestEnv.seed_library(count)
        TestEnv.sclient.sync()  

        local_document = TestEnv.sclient.documents[ids[0]]
        original_version = local_document.version()
        
        # do a remote update
        time.sleep(TestEnv.sleep_time) # see comment in TestEnv
        response = TestEnv.sclient.client.update_document(ids[0], document={"title":new_remote_title})
        self.assertTrue("error" not in response)
        self.assertTrue(response["version"] > original_version)
        self.assertTrue(local_document.is_synced())

        # do a local update
        local_document.update({"year":new_local_year})
        self.assertTrue(local_document.is_modified())  

        self.sync()

        # no conflict so both fields should be updated
        self.assertTrue(local_document.is_synced())
        self.assertEqual(local_document.object.title, new_remote_title)
        self.assertEqual(local_document.object.year, new_local_year)

    def test_local_update_remote_update_conflict(self):
        # update the same field locally and remotely to force a conflict
        new_remote_title = "updated_remote_title"
        new_local_title = "updated_local_title"

        count = 5 
        ids = TestEnv.seed_library(count)
        TestEnv.sclient.sync()  

        local_document = TestEnv.sclient.documents[ids[0]]
        original_version = local_document.version()
        
        # do a remote update
        time.sleep(TestEnv.sleep_time)
        response = TestEnv.sclient.client.update_document(ids[0], document={"title":new_remote_title})
        self.assertTrue("error" not in response)
        self.assertTrue(response["version"] > original_version)
        self.assertTrue(local_document.is_synced())

        # do a local update
        local_document.update({"title":new_local_title})
        self.assertTrue(local_document.is_modified())  

        self.sync()

        # default conflict resolver will choose the local version
        # TODO test different strategies
        self.assertTrue(local_document.is_synced())
        self.assertEqual(local_document.object.title, new_local_title)

    def test_local_update(self):
        new_title = "updated_title"

        count = 5 
        ids = TestEnv.seed_library(count)
        TestEnv.sclient.sync()     

        # change the title of one document
        local_document = TestEnv.sclient.documents[ids[0]]
        local_document.update({"title":new_title})

        original_version = local_document.version()
        
        # the document should be marked as modified
        self.assertTrue(local_document.is_modified())
        self.assertEqual(local_document.version(), original_version)
        for doc_id in ids[1:]:
            self.assertTrue(TestEnv.sclient.documents[doc_id].is_synced())
        
        self.sync()

        # all documents should be synced now
        for doc_id in ids:
            self.assertTrue(TestEnv.sclient.documents[doc_id].is_synced())
            self.assertTrue(self.document_exists(doc_id))

        self.assertEqual(local_document.object.title, new_title)
        self.assertTrue(local_document.version() > original_version)
        
        details = TestEnv.sclient.client.document_details(ids[0])
        self.assertEqual(details["title"], new_title)
        self.assertEqual(details["version"], local_document.version())
        
    def test_remote_update(self):
        new_title = "updated_title"

        count = 5 
        ids = TestEnv.seed_library(count)
        TestEnv.sclient.sync()        
        
        local_document = TestEnv.sclient.documents[ids[0]]
        original_version = TestEnv.sclient.documents[ids[0]].version()

        # update the title of a document on the server
        response = TestEnv.sclient.client.update_document(ids[0], document={"title":new_title})
        self.assertTrue("error" not in response)

        # make sure the title was updated on the server
        details = TestEnv.sclient.client.document_details(ids[0])
        self.assertEqual(details["title"], new_title)  
      
        self.sync()

        # all documents should be synced
        for doc_id in ids:
            self.assertTrue(TestEnv.sclient.documents[doc_id].is_synced())
            self.assertTrue(self.document_exists(doc_id))       

        self.assertEqual(local_document.object.title, new_title)
        self.assertTrue(local_document.version() > original_version)            

def main(config_file):
    sclient = DummySyncedClient(config_file)

    # verify that the version number is available on this server before running all the tests
    document = TemporaryDocument(sclient.client).document()
    if not "version" in document:
        print "The server doesn't support functionalities required by this test yet"
        sys.exit(1)

    TestEnv.sclient = sclient
    unittest.main()    

if __name__ == "__main__":
    main(get_config_file())

########NEW FILE########
__FILENAME__ = test-update-version
import os
import sys
import time
import unittest

from utils import *
parent_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")
os.sys.path.insert(0, parent_dir) 
from mendeley_client import *

class TestEnv:
    client = None
    sleep_time = 1 

class TestDocumentUpdate(unittest.TestCase):

    # Tests
    def setUp(self):
        self.test_document = TestEnv.client.create_document(document={'type' : 'Book',
                                                                      'title': 'Document creation test', 
                                                                      'year': 2008})
    def tearDown(self):
        TestEnv.client.delete_library_document(self.test_document["document_id"])  

    def update_doc(self, obj):
        document_id = self.test_document["document_id"]
        response = TestEnv.client.update_document(document_id, document=obj)
        if isinstance(response, requests.Response) and "error" in response.content:
            return False, response.content
        updated_details = TestEnv.client.document_details(document_id)
        return self.compare_documents(updated_details, obj), response

    def update_and_check(self, obj, expected_match):
        match, response = self.update_doc(obj)
        self.assertEqual("error" in response, not expected_match)
        self.assertEqual(match, expected_match)        
    
    def compare_documents(self, docA, docB):
        """Return True if docA[key] == docB[key] for keys in docB
        if docA has extra keys, they are ignored"""

        for key in docB.keys():
            if not key in docA or docA[key] != docB[key]:
                return False
        return True
    
    @timed
    @delay(TestEnv.sleep_time)
    def test_valid_update(self):
        info = {"type":"Book Section",
                "title":"How to kick asses when out of bubble gum",
                "authors":[ {"forename":"Steven", "surname":"Seagal"},
                            {"forename":"Dolph","surname":"Lundgren"}],
                "year":"1998"
                }
        self.update_and_check(info, True)

    @timed
    @delay(TestEnv.sleep_time)
    def test_valid_update_no_delay(self):
        info = {"type":"Book Section"}
        self.update_and_check(info, True)
        #Do a request without delay - the request should fail if done in less than a second from the previous create/update due to the rate limiting (one update per second per document)
        #Please note this test might fail if the previous update_and_check takes longer than a second to run.
        info = {"year":"1998"}
        self.update_and_check(info, False)
        #Sleeping again and doing the update should work then
        time.sleep(1)
        self.update_and_check(info, True)


    @timed
    @delay(TestEnv.sleep_time)
    @skip('skipping until format is fixed.')
    def test_authors_format(self):
        self.update_and_check({"authors":[ ["Steven", "Seagal"], ["Dolph","Lundgren"]]}, False)
        self.update_and_check({"authors":[ ["Steven Seagal"], ["Dolph Lundgren"]]}, False)
        self.update_and_check({"authors":"bleh"}, False)
        self.update_and_check({"authors":-1}, False)
        self.update_and_check({"authors":[ {"forename":"Steven", "surname":"Seagal"},
                                           {"forename":"Dolph","surname":"Lundgren"}]}, True)

    @timed
    @delay(TestEnv.sleep_time)
    @skip('skipping until value type is fixed.')
    def test_invalid_field_type(self):
        # year is a string not a number
        self.update_and_check({"year":1998}, False)

    @timed
    @delay(TestEnv.sleep_time)
    def test_invalid_document_type(self):
        self.update_and_check({"type":"Cat Portrait"}, False)

    @timed
    @delay(TestEnv.sleep_time)
    def test_invalid_field(self):
        self.update_and_check({"shoesize":1}, False)

    @timed
    @delay(TestEnv.sleep_time)
    def test_readonly_field(self):
        self.update_and_check({"uuid": "0xdeadbeef"}, False)

class TestDocumentVersion(unittest.TestCase):

    # Utils
    def verify_version(self, obj, expected):
        delta = abs(obj["version"]-expected)
        self.assertTrue(delta < 300)

    # Tests
    def setUp(self):
        self.test_document = TestEnv.client.create_document(document={'type' : 'Book',
                                                                        'title': 'Document creation test',
                                                                        'year': 2008})
    def tearDown(self):
        TestEnv.client.delete_library_document(self.test_document["document_id"])

    @timed
    def test_version_returned(self):
        """Verify that the version is returned on creation, details and listing"""
        now = timestamp()

        # verify that we get a version number when creating a document
        # at the moment it is the timestamp of creation, so check that it's around
        # the current UTC timestamp (see verify_version)
        created_version = self.test_document["version"]
        self.verify_version(self.test_document, now)

        # verify that the list of documents returns a version and that
        # it matches the version returned earlier
        document_id = self.test_document['document_id']
        documents = TestEnv.client.library()
        self.assertTrue(document_id in documents['document_ids'])

        found_document = None
        for document in documents['documents']:
            if document["id"] == document_id:
                found_document = document
                break
        self.assertTrue(found_document)
        self.assertEqual(found_document["version"], created_version)

        # verify that the document details have the same version
        details = TestEnv.client.document_details(document_id)
        self.assertEqual(details["version"], created_version)

    @timed
    @delay(TestEnv.sleep_time)
    def test_version_on_document_update(self):
        """Verify that an update increases the version number"""
        # sleep a bit to avoid receiving the same timestamp between create and update
        current_version = self.test_document["version"]
        response = TestEnv.client.update_document(self.test_document["document_id"], document={"title":"updated title"})
        self.assertTrue("version" in response)
        self.assertTrue(response["version"] > current_version)

    @timed
    @delay(TestEnv.sleep_time)
    def test_version_on_document_folder_update(self):
        # sleep a bit to avoid receiving the same timestamp between create and update

        folder = TestEnv.client.create_folder(folder={"name":"test"})
        self.assertTrue("version" in folder)
        current_version = self.test_document["version"]
        response = TestEnv.client.add_document_to_folder(folder["folder_id"], self.test_document["document_id"])

        # verify that the document version changed
        created_version = self.test_document["version"]
        details = TestEnv.client.document_details(self.test_document["document_id"])
        self.assertTrue(details["version"] > created_version)

        TestEnv.client.delete_folder(folder["folder_id"])

def main(config_file):
    client = create_client(config_file)

    # verify that the version number is available on this server before running all the tests
    document = TemporaryDocument(client).document()
    if not "version" in document:
        print "The server doesn't support functionalities required by this test yet"
        sys.exit(1)

    TestEnv.client = client
    unittest.main()

if __name__ == '__main__':
    main(get_config_file())


########NEW FILE########
__FILENAME__ = utils
import calendar
import os
import sys
import time

def timed(fn):
    def wrapped(*args, **kwargs):
        now = time.time()
        res = fn(*args, **kwargs)
        delta = time.time()-now
        print "\n%s took\t%5.3fs"%(fn.__name__,delta)
        return res
    return wrapped

def skip(reason):
    def wrappedskip(fn):
        def wrapped(*args, **kwargs):
            print "Skipping %(function)s:  %(reason)s" % {"function" : fn.__name__, "reason": reason}
            return
        wrapped.__name__=fn.__name__
        return wrapped
    return wrappedskip

def timestamp():
    n = time.gmtime()
    return calendar.timegm(n)

def delay(period):
    def wrappedperiod(fn):
        def wrapped(*args, **kwargs):
            time.sleep(period)
            res = fn(*args, **kwargs)
            return res
        wrapped.__name__=fn.__name__
        return wrapped
    return wrappedperiod

def get_config_file():
    config_file = "../config.json"
    if len(sys.argv) > 1:
        _, file_ext = os.path.splitext(sys.argv[1])
        if file_ext == ".json":
            config_file = sys.argv[1]
            del sys.argv[1]    
    return config_file

class TemporaryDocument:

    def __init__(self, client):
        self.__client = client
        self.__document = client.create_document(document={'type' : 'Book', 
                                                           'title': 'Document creation test'})
        assert "document_id" in self.__document

    def document(self):
        return self.__document

    def __del__(self):
        assert self.__client.delete_library_document(self.__document["document_id"])
        
def test_prompt():
    print "\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    print "!! This test will reset the library of the account used for testing !!"
    print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
    inp = raw_input("If you are okay with this, please type 'yes' to continue: ")
    return inp == "yes"

########NEW FILE########
