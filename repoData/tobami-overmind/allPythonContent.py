__FILENAME__ = models
#The api app needs an empty models.py so that it gets registered for unit test detection

########NEW FILE########
__FILENAME__ = provisioning
from piston.handler import BaseHandler
from piston.utils import rc
from libcloud.common.types import InvalidCredsException

from overmind.provisioning.provider_meta import PROVIDERS
from overmind.provisioning.models import Provider, Image, Location, Size, Node
from overmind.provisioning.models import get_state
from overmind.provisioning.views import save_new_node, save_new_provider, update_provider
import copy, logging

# Unit tests are not working for HttpBasicAuthentication
# This is a hack until authentication is reimplemented as OAuth
# (waiting for a new piston version)
_TESTING = False

class ProviderHandler(BaseHandler):
    fields = ('id', 'name', 'provider_type', 'access_key')
    model = Provider
    
    def create(self, request):
        if not _TESTING and not request.user.has_perm('provisioning.add_provider'):
            return rc.FORBIDDEN
        
        if not hasattr(request, "data"):
            request.data = request.POST
        attrs = self.flatten_dict(request.data)
        
        # Pass data to form Validation
        error, form, provider = save_new_provider(attrs)
        if error is None:
            return provider
        else:
            resp = rc.BAD_REQUEST
            if error == 'form':
                for k, v in form.errors.items():
                    formerror = v[0]
                    if type(formerror) != unicode:
                        formerror = formerror.__unicode__()
                    resp.write("\n" + k + ": " + formerror)
            else:
                resp.write("\n" + error)
            return resp
    
    def read(self, request, *args, **kwargs):
        id = kwargs.get('id')
        
        if id is None:
            provider_type = request.GET.get('provider_type')
            name = request.GET.get('name')
            if provider_type is not None:
                return self.model.objects.filter(
                    provider_type=provider_type,
                )
            elif name is not None:
                try:
                    return self.model.objects.get(name=name)
                except self.model.DoesNotExist:
                    return rc.NOT_FOUND
            else:
                return self.model.objects.all()
        else:
            try:
                return self.model.objects.get(id=id)
            except self.model.DoesNotExist:
                return rc.NOT_FOUND
    
    def update(self, request, *args, **kwargs):
        if not _TESTING and not request.user.has_perm('provisioning.change_provider'):
            return rc.FORBIDDEN
        if not hasattr(request, "data"):
            request.data = request.POST
        attrs = self.flatten_dict(request.data)
        
        # Check that it is a valid provider
        id = kwargs.get('id')
        if id is None:
            return rc.BAD_REQUEST
        
        try:
            provider = self.model.objects.get(id=id)
        except self.model.DoesNotExist:
            return rc.NOT_FOUND
        
        # Pass data to form Validation
        error, form, provider = update_provider(attrs, provider)
        if error is None:
            return provider
        else:
            resp = rc.BAD_REQUEST
            if error == 'form':
                for k, v in form.errors.items():
                    formerror = v[0]
                    if type(formerror) != unicode:
                        formerror = formerror.__unicode__()
                    resp.write("\n" + k + ": " + formerror)
            else:
                resp.write("\n" + error)
            return resp
    
    def delete(self, request, *args, **kwargs):
        if not _TESTING and not request.user.has_perm('provisioning.delete_provider'):
            return rc.FORBIDDEN
        id = kwargs.get('id')
        if id is None:
            return rc.BAD_REQUEST
        try:
            prov = self.model.objects.get(id=id)
            prov.delete()
            return rc.DELETED
        except self.model.DoesNotExist:
            return rc.NOT_FOUND


class ImageHandler(BaseHandler):
    fields = ('id', 'image_id', 'name', 'favorite')
    model = Image
    allowed_methods = ('GET',)
    
    def read(self, request, *args, **kwargs):
        id = kwargs.get('id')
        provider = Provider.objects.get(id=kwargs.get('provider_id'))
        if id is None:
            image_id = request.GET.get('image_id')
            name = request.GET.get('name')
            if image_id is not None:
                try:
                    return self.model.objects.get(
                        provider=provider,
                        image_id=image_id
                    )
                except self.model.DoesNotExist:
                    return rc.NOT_FOUND
            elif name is not None:
                try:
                    return self.model.objects.get(
                        provider=provider,
                        name=name
                    )
                except self.model.DoesNotExist:
                    return rc.NOT_FOUND
            else:
                return self.model.objects.filter(provider=provider)
        else:
            try:
                return self.model.objects.get(id=id)
            except self.model.DoesNotExist:
                return rc.NOT_FOUND


class LocationHandler(BaseHandler):
    fields = ('id', 'location_id', 'name')
    model = Location
    allowed_methods = ('GET',)


class SizeHandler(BaseHandler):
    fields = ('id', 'size_id', 'name')
    model = Size
    allowed_methods = ('GET',)


class NodeHandler(BaseHandler):
    fields = ('id', 'name', 'node_id', 'provider', 'image', 'location', 'size', 
        'public_ips', 'private_ips', 'created_by', 'state', 'environment',
        'destroyed_by', 'created_at', 'destroyed_at')
    model = Node
    
    def create(self, request):
        if not _TESTING and not request.user.has_perm('provisioning.add_node'):
            return rc.FORBIDDEN
        if not hasattr(request, "data"):
            request.data = request.POST
        attrs = self.flatten_dict(request.data)
        
        # Modify REST's "provider_id" to "provider" (expected form field)
        data = copy.deepcopy(attrs)
        data['provider'] = data.get('provider_id','')
        if 'provider_id' in data: del data['provider_id']
        
        # Validate data and save new node
        error, form, node = save_new_node(data, request.user)
        if error is None:
            return node
        else:
            resp = rc.BAD_REQUEST
            if error == 'form':
                for k, v in form.errors.items():
                    formerror = v[0]
                    if type(formerror) != unicode:
                        formerror = formerror.__unicode__()
                    resp.write("\n" + k + ": " + formerror)
            else:
                resp.write("\n" + error)
            return resp
    
    def read(self, request, *args, **kwargs):
        id = kwargs.get('id')
        
        if id is None:
            # If name specified, return node
            name = request.GET.get('name')
            if name is not None:
                try:
                    return self.model.objects.get(name=name)
                except self.model.DoesNotExist:
                    return rc.NOT_FOUND
            # Else return a subset of nodes
            query = self.model.objects.all()
            provider_id = request.GET.get('provider_id')
            if provider_id is not None:
                query = query.filter(provider=provider_id)
            if request.GET.get('show_decommissioned') != 'true':
                query = query.exclude(environment='Decommissioned')
            return query
        else:
            # Return the selected node
            try:
                return self.model.objects.get(id=id)
            except self.model.DoesNotExist:
                return rc.NOT_FOUND
    
    def update(self, request, *args, **kwargs):
        if not _TESTING and not request.user.has_perm('provisioning.change_node'):
            return rc.FORBIDDEN
        if not hasattr(request, "data"):
            request.data = request.POST
        attrs = self.flatten_dict(request.data)
        id = kwargs.get('id')
        if id is None:
            return rc.BAD_REQUEST
        
        try:
            node = self.model.objects.get(id=id)
        except self.model.DoesNotExist:
            return rc.NOT_FOUND
        
        # Update name if present
        name = attrs.get('name')
        if name is not None and name != node.name:
            try:
                self.model.objects.get(name=name)
                return rc.DUPLICATE_ENTRY
            except self.model.DoesNotExist:
                node.name = name
        node.save()
        return node
    
    def delete(self, request, *args, **kwargs):
        if not _TESTING and not request.user.has_perm('provisioning.delete_node'):
            return rc.FORBIDDEN
        id = kwargs.get('id')
        if id is None:
            return rc.BAD_REQUEST
        try:
            node = self.model.objects.get(id=id)
            if node.environment == 'Decommissioned':
                return rc.NOT_HERE
            if node.provider.supports('destroy'):
                node.destroy(request.user.username)
            else:
                node.decommission()
            return rc.DELETED
        except self.model.DoesNotExist:
            return rc.NOT_FOUND

########NEW FILE########
__FILENAME__ = tests
import unittest
import test_provisioning


def suite():
    provisioning = test_provisioning.suite()
    return unittest.TestSuite([provisioning])

########NEW FILE########
__FILENAME__ = test_provisioning
import copy
import unittest
import json

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User, Group
from overmind.provisioning.models import Provider, Node


class BaseProviderTestCase(TestCase):
    urls = 'overmind.test_urls'

    def setUp(self):
        self.path = "/api/providers/"

        op = Group.objects.get(name='Operator')
        self.user = User.objects.create_user(
            username='testuser', email='t@t.com', password='test1')
        self.user.groups.add(op)
        self.user.save()

        self.client = Client()
        #login = self.client.login(
            #username=self.user.username, password=self.user.password)
        #self.assertTrue(login)

    def create_provider(self):
        '''Utility function to create providers using the api'''
        data = {
            'name': 'A provider to be updated',
            'provider_type': 'DUMMY',
            'access_key': 'somekey',
        }
        resp_new = self.client.post(
            self.path, json.dumps(data), content_type='application/json')
        self.assertEquals(resp_new.status_code, 200)
        return json.loads(resp_new.content)


class ReadProviderTest(BaseProviderTestCase):
    def setUp(self):
        super(ReadProviderTest, self).setUp()

        self.p1 = Provider(name="prov1", provider_type="DUMMY", access_key="keyzz")
        self.p1.save()
        self.p2 = Provider(name="prov2", provider_type="DUMMY", access_key="keyzz2")
        self.p2.save()
        self.p3 = Provider(name="prov3", provider_type="dedicated")
        self.p3.save()

    def test_not_authenticated(self):
        """Should get a 401 when the user is not authenticated"""
        # NOTE: Use non-authenticated client
        response = self.client.get(self.path)
        self.assertEquals(response.status_code, 401)

    def test_get_all_providers(self):
        '''Should show all existing providers'''
        response = self.client.get(self.path)
        self.assertEquals(response.status_code, 200)
        expected = [
            {'id': self.p1.id, 'access_key': self.p1.access_key,
            'provider_type': self.p1.provider_type, 'name': self.p1.name},
            {'id': self.p2.id, 'access_key': self.p2.access_key,
            'provider_type': self.p2.provider_type, 'name': self.p2.name},
            {'id': self.p3.id, 'access_key': self.p3.access_key,
            'provider_type': self.p3.provider_type, 'name': self.p3.name},
        ]
        self.assertEquals(json.loads(response.content), expected)

    def test_get_providers_by_type_dummy(self):
        '''Should show all providers of type DUMMY'''
        response = self.client.get(self.path + "?provider_type=DUMMY")
        self.assertEquals(response.status_code, 200)
        expected = [
            {'id': self.p1.id, 'access_key': self.p1.access_key,
            'provider_type': self.p1.provider_type, 'name': self.p1.name},
            {'id': self.p2.id, 'access_key': self.p2.access_key,
            'provider_type': self.p2.provider_type, 'name': self.p2.name},
        ]
        self.assertEquals(json.loads(response.content), expected)

    def test_get_providers_by_type_dedicated(self):
        '''Should show all providers of type dedicated'''
        response = self.client.get(self.path + "?provider_type=dedicated")
        self.assertEquals(response.status_code, 200)
        expected = [
            {'id': self.p3.id, 'access_key': self.p3.access_key,
            'provider_type': self.p3.provider_type, 'name': self.p3.name},
        ]
        self.assertEquals(json.loads(response.content), expected)

    def test_get_providers_by_type_not_found(self):
        '''Should show providers for non-existent type'''
        response = self.client.get(self.path + "?provider_type=DUMMIEST")
        self.assertEquals(response.status_code, 200)
        expected = []
        self.assertEquals(json.loads(response.content), expected)

    def test_get_provider_by_id(self):
        '''Should show provider with id=2'''
        response = self.client.get(self.path + "2")
        self.assertEquals(response.status_code, 200)
        expected = {
            'id': self.p2.id, 'access_key': self.p2.access_key,
            'provider_type': self.p2.provider_type, 'name': self.p2.name,
        }
        self.assertEquals(json.loads(response.content), expected)

    def test_get_provider_by_id_not_found(self):
        '''Should return NOT_FOUND when requesting a provider with non existing id'''
        response = self.client.get(self.path + '99999')
        self.assertEquals(response.status_code, 404)

    def test_get_provider_by_name(self):
        '''Should show provider with name "prov1"'''
        response = self.client.get(self.path + "?name=prov1")
        self.assertEquals(response.status_code, 200)
        expected = {
            'id': self.p1.id, 'access_key': self.p1.access_key,
            'provider_type': self.p1.provider_type, 'name': self.p1.name
        }
        self.assertEquals(json.loads(response.content), expected)

    def test_get_provider_by_name_not_found(self):
        '''Should return NOT_FOUND when requesting a provider with a non existing name'''
        response = self.client.get(self.path + "?name=prov1nothere")
        self.assertEquals(response.status_code, 404)


class CreateProviderTest(BaseProviderTestCase):
    def test_create_provider(self):
        '''Should create a new provider when request is valid'''
        data = {
            'name': 'A new provider',
            'provider_type': 'DUMMY',
            'access_key': 'kiuuuuuu',
        }
        resp = self.client.post(
            self.path, json.dumps(data), content_type='application/json')
        self.assertEquals(resp.status_code, 200)

        expected = data
        expected["id"] = 1
        self.assertEquals(json.loads(resp.content), expected)

        #Check that it really is in the DB
        p = Provider.objects.get(id=1)
        self.assertEquals(p.name, 'A new provider')
        self.assertEquals(p.provider_type, 'DUMMY')

    def test_create_provider_should_import_nodes(self):
        '''Should import nodes when a new provider is created'''
        # There shouldn't be any nodes in the DB
        self.assertEquals(len(Node.objects.all()), 0)
        data = {
            'name': 'A new provider',
            'provider_type': 'DUMMY',
            'access_key': 'kiuuuuuu',
        }
        resp = self.client.post(
            self.path, json.dumps(data), content_type='application/json')

        # There should be exactly 2 nodes in the DB now
        self.assertEquals(len(Node.objects.all()), 2)

    def test_create_provider_missing_access_key(self):
        """Should not create a new provider when access_key is missing"""
        data = {'name': 'A new provider', 'provider_type': 'DUMMY'}
        expected = "Bad Request\naccess_key: This field is required."
        resp = self.client.post(
            self.path, json.dumps(data), content_type='application/json')
        self.assertEquals(resp.status_code, 400)
        self.assertEquals(resp.content, expected)

        # Make sure it wasn't saved in the DB
        self.assertEquals(len(Provider.objects.all()), 0)

    def test_create_provider_empty_access_key(self):
        '''Should not create a new provider when access_key is empty'''
        data = {'name': 'A new provider',
                'provider_type': 'DUMMY',
                'access_key': '',
        }
        expected = "Bad Request\naccess_key: This field is required."
        resp = self.client.post(
            self.path, json.dumps(data), content_type='application/json')
        self.assertEquals(resp.status_code, 400)
        self.assertEquals(resp.content, expected)

        # Make sure it wasn't saved in the DB
        self.assertEquals(len(Provider.objects.all()), 0)


class UpdateProviderTest(BaseProviderTestCase):
    def test_update_provider_name(self):
        '''Should update the provider name when request is valid'''
        # First create a provider
        new_data = self.create_provider()

        # Now update the newly added provider
        new_data['name'] = "ThisNameIsMuchBetter"
        resp = self.client.put(
            self.path + str(new_data["id"]), json.dumps(new_data), content_type='application/json')
        self.assertEquals(resp.status_code, 200)

        expected = new_data
        self.assertEquals(json.loads(resp.content), expected)

        #Check that it was also updated in the DB
        p = Provider.objects.get(id=new_data['id'])
        self.assertEquals(p.name, new_data['name'])

    def test_update_provider_missing_field(self):
        '''Should not update a provider when a field is missing'''
        # First create a provider
        new_data = self.create_provider()

        # Now try to update the provider while leaving out each field in turn
        for field in new_data:
            if field == "id": continue#field "id" is not required
            modified_data = copy.deepcopy(new_data)#Don't alter original data
            del modified_data[field]#remove a required field
            resp = self.client.put(
                self.path + str(new_data['id']),
                json.dumps(modified_data),
                content_type='application/json')
            expected = "Bad Request\n%s: This field is required." % field
            self.assertEquals(resp.status_code, 400)
            self.assertEquals(resp.content, expected)

    def test_update_provider_empty_field(self):
        """Should not update a provider when a field is empty"""
        # First create a provider
        new_data = self.create_provider()

        # Now try to update the provider while leaving out each field empty
        for field in new_data:
            if field == "id": continue#field "id" is not required
            modified_data = copy.deepcopy(new_data)#Don't alter original data
            modified_data[field] = ""#Make a field empty
            resp = self.client.put(
                self.path + str(new_data['id']),
                json.dumps(modified_data),
                content_type='application/json')
            expected = "Bad Request\n%s: This field is required." % field
            self.assertEquals(resp.status_code, 400)
            self.assertEquals(resp.content, expected)


class DeleteProviderTest(BaseProviderTestCase):
    def test_delete_provider(self):
        '''Should delete a provider'''
        # First create a provider
        new_data = self.create_provider()

        # Now delete the newly added provider
        resp = self.client.delete(self.path + str(new_data['id']))
        self.assertEquals(resp.status_code, 204)

        # Check that the api returns not found
        resp = self.client.get(self.path + str(new_data['id']))
        self.assertEquals(resp.status_code, 404, 'The API should return NOT_FOUND')

        # Check that it was also deleted from the DB
        try:
            Provider.objects.get(id=new_data['id'])
            self.fail('The provider was not deleted from the DB')
        except Provider.DoesNotExist:
            pass


class CreateImageTest(BaseProviderTestCase):
    def setUp(self):
        super(ReadImageTest, self).setUp()

        self.p1 = Provider(name="prov1", provider_type="DUMMY", access_key="keyzz")
        self.p1.save()
        self.p1.import_images()
        self.p2 = Provider(name="prov2", provider_type="DUMMY", access_key="keyzz2")
        self.p2.save()
        self.p2.import_images()

    def test_create_image_should_fail(self):
        '''Should return not allowed when trying to POST'''
        data = {"image_id": "10", "name": "myimage", "favorite": False,
            "provider_id": "1"}
        resp = self.client.post(
            self.path, json.dumps(data), content_type='application/json')
        self.assertEquals(response.status_code, 405)


class ReadImageTest(BaseProviderTestCase):
    def setUp(self):
        super(ReadImageTest, self).setUp()

        self.p1 = Provider(name="prov1", provider_type="DUMMY", access_key="keyzz")
        self.p1.save()
        self.p1.import_images()
        self.p2 = Provider(name="prov2", provider_type="DUMMY", access_key="keyzz2")
        self.p2.save()
        self.p2.import_images()

    def test_get_all_images(self):
        '''Should return all images for a given provider'''
        response = self.client.get(self.path + str(self.p1.id) + "/images/")
        self.assertEquals(response.status_code, 200)
        expected = [
            {"id": 1, "image_id": "1", "name": "Ubuntu 9.10", "favorite": False},
            {"id": 2,"image_id": "2","name": "Ubuntu 9.04", "favorite": False},
            {"id": 3, "image_id": "3", "name": "Slackware 4", "favorite": False},
        ]
        self.assertEquals(json.loads(response.content), expected)

    def test_get_image_by_id(self):
        '''Should show image with id=2'''
        response = self.client.get(self.path + str(self.p1.id) + "/images/2")
        self.assertEquals(response.status_code, 200)
        expected = {
            "id": 2,"image_id": "2","name": "Ubuntu 9.04", "favorite": False}
        self.assertEquals(json.loads(response.content), expected)

    def test_get_image_by_image_id(self):
        '''Should show image with image_id=2'''
        path = self.path + str(self.p1.id) + "/images/" + "?image_id=2"
        response = self.client.get(path)
        self.assertEquals(response.status_code, 200)
        expected = {
            "id": 2,"image_id": "2","name": "Ubuntu 9.04", "favorite": False}
        self.assertEquals(json.loads(response.content), expected)

    def test_get_image_by_name(self):
        '''Should show image with name=Ubuntu 9.04'''
        path = self.path + str(self.p1.id) + "/images/" + "?name=Ubuntu 9.04"
        response = self.client.get(path)
        self.assertEquals(response.status_code, 200)
        expected = {
            "id": 2,"image_id": "2","name": "Ubuntu 9.04", "favorite": False}
        self.assertEquals(json.loads(response.content), expected)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(CreateProviderTest))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(ReadProviderTest))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(UpdateProviderTest))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(DeleteProviderTest))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(ReadImageTest))
    return suite

########NEW FILE########
__FILENAME__ = test_urls
from django.conf.urls.defaults import *
from api.provisioning import ProviderHandler, NodeHandler, ImageHandler
import api
from urls import CsrfExemptResource


# The test url creates resources that do not require authentication
api.provisioning._TESTING = True

provider_resource = CsrfExemptResource(ProviderHandler)
image_resource = CsrfExemptResource(ImageHandler)
node_resource = CsrfExemptResource(NodeHandler)

urlpatterns = patterns('',
    url(r'^providers/(?P<provider_id>\d+)/images/$', image_resource),
    url(r'^providers/(?P<provider_id>\d+)/images/(?P<id>\d+)$', image_resource),
    url(r'^providers/$', provider_resource),
    url(r'^providers/(?P<id>\d+)$', provider_resource),
    url(r'^nodes/$', node_resource),
    url(r'^nodes/(?P<id>\d+)$', node_resource),
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from piston.resource import Resource
from piston.authentication import HttpBasicAuthentication

from api.provisioning import ProviderHandler, NodeHandler, ImageHandler


auth = HttpBasicAuthentication(realm="overmind")
ad = { 'authentication': auth }

class CsrfExemptResource(Resource):
    '''Django 1.2 CSRF protection can interfere'''
    def __init__(self, handler, authentication = None):
        super(CsrfExemptResource, self).__init__(handler, authentication)
        self.csrf_exempt = getattr(self.handler, 'csrf_exempt', True)

provider_resource = CsrfExemptResource(ProviderHandler, **ad)
image_resource = CsrfExemptResource(ImageHandler, **ad)
node_resource = CsrfExemptResource(NodeHandler, **ad)

urlpatterns = patterns('',
    url(r'^providers/(?P<provider_id>\d+)/images/$', image_resource),
    url(r'^providers/(?P<provider_id>\d+)/images/(?P<id>\d+)$', image_resource),
    url(r'^providers/$', provider_resource),
    url(r'^providers/(?P<id>\d+)$', provider_resource),
    url(r'^nodes/$', node_resource),
    url(r'^nodes/(?P<id>\d+)$', node_resource),
)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = controllers
from libcloud.compute import types
from libcloud.compute.base import NodeAuthPassword, NodeAuthSSHKey, Node
from libcloud.compute.base import NodeImage, NodeSize, NodeLocation
from libcloud.compute.providers import get_driver
from libcloud.compute.deployment import SSHKeyDeployment
from provisioning import plugins
from django.conf import settings
import copy, logging


class ProviderController():
    name = None
    extra_param_name = None
    extra_param_value = None
    
    def __init__(self, provider):
        self.extra_param_name  = provider.extra_param_name
        self.extra_param_value = provider.extra_param_value
        self.provider_type = provider.provider_type
        # Get libcloud provider type
        try:
            driver_type = types.Provider.__dict__[self.provider_type]
            # Get driver from libcloud
            Driver = get_driver(driver_type)
            logging.debug('selected "%s" libcloud driver' % self.provider_type)
        except KeyError:
            # Try to load provider from plugins
            Driver = plugins.get_driver(self.provider_type)
            logging.debug('selected "%s" plugin driver' % self.provider_type)
        except Exception, e:
            logging.critical(
                'ProviderController can\'t find a driver for %s' % self.provider_type)
            raise Exception, "Unknown provider %s" % self.provider_type
        
        # Providers with only one access key
        if provider.secret_key == "":
            self.conn = Driver(str(provider.access_key))
        # Providers with 2 keys
        else:
            self.conn = Driver(str(provider.access_key), str(provider.secret_key))
    
    def create_node(self, form):
        name   = form.cleaned_data['name']
        image = form.cleaned_data.get('image')
        if image:
            image  = NodeImage(image.image_id, '', self.conn)
        size = form.cleaned_data.get('size')
        if size:
            size = NodeSize(size.size_id, '', '', '', None, None, driver=self.conn)
        location = form.cleaned_data.get('location')
        if location:
            location  = NodeLocation(location.location_id, '', '', self.conn)
        
        # Choose node creation strategy
        features = self.conn.features.get('create_node', [])
        try:
            if "ssh_key" in features:
                # Pass on public key and we are done
                logging.debug("Provider feature: ssh_key. Pass on key")
                node = self.conn.create_node(
                    name=name, image=image, size=size, location=location,
                    auth=NodeAuthSSHKey(settings.PUBLIC_KEY)
                )
            elif 'generates_password' in features:
                # Use deploy_node to deploy public key
                logging.debug(
                    "Provider feature: generates_password. Use deploy_node")
                pubkey = SSHKeyDeployment(settings.PUBLIC_KEY) 
                node = self.conn.deploy_node(
                    name=name, image=image, size=size, location=location,
                    deploy=pubkey
                )
            elif 'password' in features:
                # Pass on password and use deploy_node to deploy public key
                pubkey = SSHKeyDeployment(settings.PUBLIC_KEY)
                rpassword = generate_random_password(15)
                logging.debug("Provider feature: password. Pass on password=%s to deploy_node" % rpassword)
                node = self.conn.deploy_node(
                    name=name, image=image, size=size, location=location,
                    auth=NodeAuthPassword(rpassword), deploy=pubkey
                )
            else:
                # Create node without any extra steps nor parameters
                logging.debug("Provider feature: none. Call create_node")
                # Include all plugin form fields in the argument dict
                args = copy.deepcopy(form.cleaned_data)
                # Remove unneeded fields
                for field in ['name', 'image', 'size', 'location', 'provider']:
                    if field in args:
                        del args[field]#Avoid colissions with default args
                args[str(self.extra_param_name)] = str(self.extra_param_value)
                node = self.conn.create_node(
                    name=name, image=image, size=size, location=location, **args
                )
        except Exception, e:
            logging.error('while creating node. %s: %s' % (type(e), e))
            return e, None
        
        return None, {
            'public_ips': node.public_ips,
            'node_id': node.id,
            'state': node.state,
            'extra': node.extra,
        }
    
    def reboot_node(self, node):
        '''Reboots a node using node.node_id and self.conn'''
        return self.conn.reboot_node(Node(node.node_id,'','','','',self.conn))
    
    def destroy_node(self, node):
        '''Destroys a node using node.node_id and self.conn'''
        return self.conn.destroy_node(Node(node.node_id,'','','','',self.conn))
    
    def get_nodes(self):
        return self.conn.list_nodes()
    
    def get_images(self):
        images = self.conn.list_images()
        # Hack for Amazon's EC2: only retrieve AMI images
        if self.provider_type.startswith("EC2"):
            images = [image for image in images if image.id.startswith('ami')]
        return images
    
    def get_sizes(self):
        return self.conn.list_sizes()
    
    def get_locations(self):
        return self.conn.list_locations()


def generate_random_password(length):
    import random, string
    chars = []
    chars.extend([i for i in string.ascii_letters])
    chars.extend([i for i in string.digits])
    chars.extend([i for i in '\'"!@#$%&*()-_=+[{}]~^,<.>;:/?'])

    return ''.join([random.choice(chars) for i in range(length)])

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode

from provisioning.models import Provider, Node, Image, Location, Size
from provisioning.provider_meta import PROVIDERS

class ProviderForm(forms.ModelForm):
    def __init__(self, provider_type, *args, **kwargs):
        super(ProviderForm, self).__init__(*args, **kwargs)
        self.fields['provider_type'].widget = forms.HiddenInput()
        self.fields['provider_type'].initial = provider_type
        provider_type_info = PROVIDERS.get(provider_type, {})
        
        for field in ['access_key', 'secret_key']:
            label = provider_type_info.get(field)
            if label is None:
                self.fields[field].widget = forms.HiddenInput()
            else:
                self.fields[field].required = True
                self.fields[field].label = label
                if field == 'secret_key':
                    self.fields['secret_key'].widget = forms.PasswordInput()
        
    class Meta:
        model = Provider
        fields = ('name', 'provider_type', 'access_key', 'secret_key')


class AddImageForm(forms.Form):
    provider = forms.ModelChoiceField(
        queryset = Provider.objects.all(),
        widget   = forms.HiddenInput,
    )
    image_id = forms.CharField(widget=forms.HiddenInput, required=False)
    favimage1 = forms.CharField(label="Type an image id", required=False)
    favimage2 = forms.ChoiceField(label="or select an image", choices=[])
    
    def __init__(self, provider_id, *args, **kwargs):
        super(AddImageForm, self).__init__(*args, **kwargs)
        prov = Provider.objects.get(id=provider_id)
        self.fields['provider'].initial = prov.id
        self.fields['favimage2'].choices = []
        for img in prov.get_images().order_by('name'):
            self.fields['favimage2'].choices += [(img.id, img)]
    
    def clean(self):
        cleaned_data = self.cleaned_data
        image = cleaned_data.get('favimage1')
        if image != "":
            try:
                cleaned_data['image'] = Image.objects.get(
                    provider=cleaned_data['provider'],
                    image_id=image
                )
            except Image.DoesNotExist:
                raise forms.ValidationError(u"Invalid image id")
        else:
            cleaned_data['image'] = Image.objects.get(
                    id=cleaned_data.get('favimage2'))
        if cleaned_data['image'].favorite:
            msg = u"This image is already marked as favorite"
            self._errors['favimage1'] = self.error_class([msg])
        return cleaned_data


class CustomRadioFieldRenderer(forms.widgets.RadioFieldRenderer):
    def __init__(self, *args, **kwargs):
        super(CustomRadioFieldRenderer, self).__init__(*args, **kwargs)
    
    def render(self):
        """Outputs a <ul> for this set of radio fields."""
        return mark_safe(u'<ul>\n%s\n</ul>' % u'\n'.join([u'<li class="clearfix">%s<a class="imgremove" href="javascript:removeImage(\'%s\');">x</a></li>'
            % (force_unicode(w), w.choice_value) for w in self]))


class SizeChoiceField(forms.ModelChoiceField):
    field_width = 10
    
    def __init__(self, width=None, *args, **kwargs):
        super(SizeChoiceField, self).__init__(*args, **kwargs)
        if width:
            self.field_width = width
    
    def label_from_instance(self, size):
        string = str(size)
        if size.price:
            blankspaces = self.field_width - len(str(size))- len(str(size.price))
            if blankspaces < 0:
                blankspaces = 0
            string += '&nbsp;'*blankspaces + size.price + ' $/hour'
        return mark_safe(string)


class NodeForm(forms.ModelForm):
    provider = forms.ModelChoiceField(
        queryset = Provider.objects.all(),
        widget   = forms.HiddenInput,
    )
    
    location = forms.ModelChoiceField(
        queryset=None,widget=forms.HiddenInput,required=False)
    size     = forms.ModelChoiceField(
        queryset=None,widget=forms.HiddenInput,required=False)
    image    = forms.ModelChoiceField(
        queryset=None,widget=forms.HiddenInput,required=False)
    
    def __init__(self, provider_id, *args, **kwargs):
        super(NodeForm, self).__init__(*args, **kwargs)
        prov = Provider.objects.get(id=provider_id)
        self.fields['provider'].initial = prov.id
        provider_info = PROVIDERS[prov.provider_type]
        # Add custom plugin fields
        for field in provider_info.get('form_fields', []):
            # These fields will be added later
            if field in ['location', 'size', 'image']:
                continue
            self.fields[field] = forms.CharField(max_length=30)
        
        # Add location field
        if 'location' in provider_info.get('form_fields', []):
            locs = prov.get_locations()
            self.fields['location'] = forms.ModelChoiceField(
                queryset=locs,
                widget=forms.RadioSelect(),
                empty_label=None,
            )
            if len(locs):
                self.fields['location'].initial = locs[0]
        
        # Add size field
        if 'size' in provider_info.get('form_fields', []):
            sizes = prov.get_sizes().order_by('price')
            width = None
            if len(sizes):
                width = max([len(str(s)) for s in sizes]) + 5
            
            self.fields['size'] = SizeChoiceField(
                queryset=sizes,
                width=width,
                empty_label=None,
            )
            if len(sizes):
                self.fields['size'].initial = sizes[0]
        
        # Add image field
        if 'image' in provider_info.get('form_fields', []):
            images = prov.get_fav_images()
            self.fields['image'] = forms.ModelChoiceField(
                queryset=images,
                widget=forms.RadioSelect(renderer=CustomRadioFieldRenderer),
                empty_label=None,
            )
            if len(images):
                self.fields['image'].initial = images[0]
    
    class Meta:
        model  = Node
        fields = ('provider', 'name', 'location', 'size', 'image')

class UserCreationFormExtended(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super(UserCreationFormExtended, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['username'].help_text = None
        self.fields['groups'] = forms.ModelChoiceField(
            queryset=Group.objects.all(),
            initial = 2,#id of group "Operator"
            help_text = None,
            required = True,
            label='Role',
        )
        self.fields['password2'].help_text = None
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'groups')
    
    def save(self, commit=True):
        user = super(UserCreationFormExtended, self).save(commit=False)
        if commit:
            user.save()
        user.groups.add(self.cleaned_data["groups"])
        user.save()
        return user

class BasicEditForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password", widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(
        label="Password confirmation", widget=forms.PasswordInput, required=False)
    
    def __init__(self, *args, **kwargs):
        super(BasicEditForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
    
    def clean_password2(self):
        password1 = self.cleaned_data["password1"]
        password2 = self.cleaned_data["password2"]
        if password1 != password2:
            raise forms.ValidationError("The two password fields didn't match.")
        return password2

    def save(self, commit=True):
        user = super(BasicEditForm, self).save(commit=False)
        if self.cleaned_data["password1"] != "":
            user.set_password(self.cleaned_data["password1"])
        
        if commit:
            user.save()
        
        return user

class UserEditForm(BasicEditForm):
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        help_text=None,
        required=True,
        initial=2,
        label='Role',
    )
    
    def __init__(self, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        initial_group = kwargs.get('instance').groups.all()
        if len(initial_group):
            self.fields['group'].initial = initial_group[0].id
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'group')
    
    def save(self, commit=True):
        user = super(UserEditForm, self).save(commit=False)
        user.groups.clear()
        user.groups.add(self.cleaned_data["group"])
        if commit:
            user.save()
        
        return user

class ProfileEditForm(BasicEditForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')

########NEW FILE########
__FILENAME__ = create_groups
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group, Permission

class Command(BaseCommand):
    help = 'Creates predefined user Roles'

    def handle(self, *args, **options):
        auth_perms = ['add_user', 'change_user', 'delete_user']
        provisioning_perms = [
            'add_provider', 'change_provider', 'delete_provider',
            'add_node', 'change_node', 'delete_node',
        ]
        
        try:
            admin = Group.objects.get(name='Admin')
        except Group.DoesNotExist:
            admin = Group(name='Admin')
            admin.save()
        try:
            op = Group.objects.get(name='Operator')
        except Group.DoesNotExist:
            op = Group(name='Operator')
            op.save()
        
        admin.permissions = [
            Permission.objects.get(codename=codename) for codename in auth_perms]
        
        for codename in provisioning_perms:
            admin.permissions.add(Permission.objects.get(codename=codename))
            op.permissions.add(Permission.objects.get(codename=codename))
        
        # Add an Observer role with no rights
        try:
            ob = Group.objects.get(name='Observer')
        except Group.DoesNotExist:
            ob = Group(name='Observer')
            ob.save()
        
        # Remove superuser status (if any exist) and add the user to the admin group
        superusers = User.objects.filter(is_superuser=True)
        for user in superusers:
            user.is_superuser = False
            user.save()
            user.groups = [admin]
        
        verbosity = int(options.get('verbosity', 1))
        if verbosity >= 1:
            print('Successfully loaded permission groups')


########NEW FILE########
__FILENAME__ = models
import json
import datetime
import logging

from IPy import IP
from django.db import models, transaction

from provisioning.controllers import ProviderController
from provisioning.provider_meta import PROVIDERS


provider_meta_keys = PROVIDERS.keys()
provider_meta_keys.sort()
PROVIDER_CHOICES = ([(key, key) for key in provider_meta_keys])

# libcloud states mapping
STATES = {
    0: 'Running',
    1: 'Rebooting',
    2: 'Terminated',
    3: 'Pending',
    4: 'Unknown',
}


def get_state(state):
    if state not in STATES:
        state = 4
    return STATES[state]


class Action(models.Model):
    name = models.CharField(unique=True, max_length=20)
    show = models.BooleanField()

    def __unicode__(self):
        return self.name


class Provider(models.Model):
    name              = models.CharField(unique=True, max_length=25)
    provider_type     = models.CharField(
        default='EC2_US_EAST', max_length=25, choices=PROVIDER_CHOICES)
    access_key        = models.CharField("Access Key", max_length=100, blank=True)
    secret_key        = models.CharField("Secret Key", max_length=100, blank=True)

    extra_param_name  = models.CharField(
        "Extra parameter name", max_length=30, blank=True)
    extra_param_value = models.CharField(
        "Extra parameter value", max_length=30, blank=True)

    actions = models.ManyToManyField(Action)
    ready   = models.BooleanField(default=False)
    conn    = None

    class Meta:
        unique_together = ('provider_type', 'access_key')

    def save(self, *args, **kwargs):
        # Define proper key field names
        if PROVIDERS[self.provider_type]['access_key'] is not None:
            self._meta.get_field('access_key').verbose_name = \
                PROVIDERS[self.provider_type]['access_key']
            self._meta.get_field('access_key').blank = False
        if PROVIDERS[self.provider_type]['secret_key'] is not None:
            self._meta.get_field('secret_key').verbose_name = \
                PROVIDERS[self.provider_type]['secret_key']
            self._meta.get_field('access_key').blank = False

        # Read optional extra_param
        if 'extra_param' in PROVIDERS[self.provider_type].keys():
            self.extra_param_name  = PROVIDERS[self.provider_type]['extra_param'][0]
            self.extra_param_value = PROVIDERS[self.provider_type]['extra_param'][1]

        # Check connection and save new provider
        self.create_connection()
        # If connection was succesful save provider
        super(Provider, self).save(*args, **kwargs)
        logging.debug('Provider "%s" saved' % self.name)

        # Add supported actions
        for action_name in PROVIDERS[self.provider_type]['supported_actions']:
            try:
                action = Action.objects.get(name=action_name)
            except Action.DoesNotExist:
                raise Exception, 'Unsupported action "%s" specified' % action_name
            self.actions.add(action)

    def supports(self, action):
        try:
            self.actions.get(name=action)
            return True
        except Action.DoesNotExist:
            return False

    def create_connection(self):
        if self.conn is None:
            self.conn = ProviderController(self)

    @transaction.commit_on_success()
    def import_nodes(self):
        '''Sync nodes present at a provider with Overmind's DB'''
        if not self.supports('list'): return
        self.create_connection()
        nodes = self.conn.get_nodes()
        # Import nodes not present in the DB
        for node in nodes:
            try:
                n = Node.objects.get(provider=self, node_id=str(node.id))
            except Node.DoesNotExist:
                # Create a new Node
                logging.info("import_nodes(): adding %s ..." % node)
                n = Node(
                    name       = node.name,
                    node_id    = str(node.id),
                    provider   = self,
                    created_by = 'imported by Overmind',
                )
                try:
                    n.image = Image.objects.get(
                        image_id=node.extra.get('imageId'), provider=self)
                except Image.DoesNotExist:
                    n.image = None
                locs = Location.objects.filter(provider=self)
                if len(locs) == 1:
                    n.location = locs[0]
                else:
                    n.location = None
                try:
                    size_id = node.extra.get('instancetype') or\
                        node.extra.get('flavorId')
                    n.size = Size.objects.get(size_id=size_id, provider=self)
                except Size.DoesNotExist:
                    n.size = None
                n.save()
            # Import/Update node info
            n.sync_ips(node.public_ips, public=True)
            n.sync_ips(node.private_ips, public=False)
            n.state = get_state(node.state)
            n.save_extra_data(node.extra)
            n.save()
            logging.debug("import_nodes(): succesfully saved %s" % node.name)

        # Delete nodes in the DB not listed by the provider
        for n in Node.objects.filter(provider=self
            ).exclude(environment='Decommissioned'):
            found = False
            for node in nodes:
                if n.node_id == str(node.id):
                    found = True
                    break
            # This node was probably removed from the provider by another tool
            # TODO: Needs user notification
            if not found:
                logging.info("import_nodes(): Delete node %s" % n)
                n.decommission()
        logging.debug("Finished synching nodes")

    @transaction.commit_on_success()
    def import_images(self):
        '''Get all images from this provider and store them in the DB
        The transaction.commit_on_success decorator is needed because
        some providers have thousands of images, which take a long time
        to save to the DB as separated transactions
        '''
        if not self.supports('images'): return
        self.create_connection()
        for image in self.conn.get_images():
            try:
                # Update image if it exists
                img = Image.objects.get(image_id=str(image.id), provider=self)
            except Image.DoesNotExist:
                # Create new image if it didn't exist
                img = Image(
                    image_id = str(image.id),
                    provider = self,
                )
            img.name = image.name
            img.save()
            logging.debug(
                "Added new image '%s' for provider %s" % (img.name, self))
        logging.info("Imported all images for provider %s" % self)

    @transaction.commit_on_success()
    def import_locations(self):
        '''Get all locations from this provider and store them in the DB'''
        if not self.supports('locations'): return
        self.create_connection()
        for location in self.conn.get_locations():
            try:
                # Update location if it exists
                loc = Location.objects.get(location_id=str(location.id), provider=self)
            except Location.DoesNotExist:
                # Create new location if it didn't exist
                loc = Location(
                    location_id = location.id,
                    provider = self,
                )
            loc.name    = location.name
            loc.country = location.country
            loc.save()
            logging.debug(
                "Added new location '%s' for provider %s" % (loc.name, self))
        logging.info("Imported all locations for provider %s" % self)

    @transaction.commit_on_success()
    def import_sizes(self):
        '''Get all sizes from this provider and store them in the DB'''
        if not self.supports('sizes'): return
        self.create_connection()
        sizes = self.conn.get_sizes()

        # Go through all sizes returned by the provider
        for size in sizes:
            try:
                # Read size
                s = Size.objects.get(size_id=str(size.id), provider=self)
            except Size.DoesNotExist:
                # Create new size if it didn't exist
                s = Size(
                    size_id = str(size.id),
                    provider = self,
                )
            # Save/update size info
            s.name      = size.name
            s.ram       = size.ram
            s.disk      = size.disk or ""
            s.bandwidth = size.bandwidth or ""
            s.price     = size.price or ""
            s.save()
            logging.debug("Saved size '%s' for provider %s" % (s.name, self))

        # Delete sizes in the DB not listed by the provider
        for s in self.get_sizes():
            found = False
            for size in sizes:
                if s.size_id == str(size.id):
                    found = True
                    break
            # This size is probably not longer offered by the provider
            if not found:
                logging.debug("Deleted size %s" % s)
                s.delete()
        logging.debug("Finished synching sizes")

    def update(self):
        logging.debug('Updating provider "%s"...' % self.name)
        self.save()
        self.import_nodes()

    def check_credentials(self):
        if not self.supports('list'): return
        self.create_connection()
        self.conn.get_nodes()
        return True

    def get_sizes(self):
        return self.size_set.all()

    def get_images(self):
        return self.image_set.all()

    def get_fav_images(self):
        return self.image_set.filter(favorite=True).order_by('-last_used')

    def get_locations(self):
        return self.location_set.all()

    def create_node(self, data):
        self.create_connection()
        return self.conn.create_node(data)

    def reboot_node(self, node):
        self.create_connection()
        return self.conn.reboot_node(node)

    def destroy_node(self, node):
        self.create_connection()
        return self.conn.destroy_node(node)

    def __unicode__(self):
        return self.name


class Image(models.Model):
    '''OS image model'''
    image_id  = models.CharField(max_length=20)
    name      = models.CharField(max_length=30)
    provider  = models.ForeignKey(Provider)
    favorite  = models.BooleanField(default=False)
    last_used = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together  = ('provider', 'image_id')


class Location(models.Model):
    '''Location model'''
    location_id = models.CharField(max_length=20)
    name        = models.CharField(max_length=20)
    country     = models.CharField(max_length=20)
    provider    = models.ForeignKey(Provider)

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together  = ('provider', 'location_id')


class Size(models.Model):
    '''Location model'''
    size_id   = models.CharField(max_length=20)
    name      = models.CharField(max_length=20)
    ram       = models.CharField(max_length=20)
    disk      = models.CharField(max_length=20)
    bandwidth = models.CharField(max_length=20, blank=True)
    price     = models.CharField(max_length=20, blank=True)
    provider  = models.ForeignKey(Provider)

    def __unicode__(self):
        return "%s (%sMB)" % (self.name, self.ram)

    class Meta:
        unique_together  = ('provider', 'size_id')


class NodeIP(models.Model):
    INET_FAMILIES = (
        ('inet4', 4),
        ('inet6', 6),
    )
    node = models.ForeignKey('Node', related_name='ips')
    address = models.IPAddressField()
    is_public = models.BooleanField(default=True)
    version = models.IntegerField(choices=INET_FAMILIES, default=4)
    position = models.IntegerField()
    interface_name = models.CharField(max_length=32, blank=True)

    def __unicode__(self):
        return "%s" % (self.address)

class Node(models.Model):
    STATE_CHOICES = (
        (u'Begin', u'Begin'),
        (u'Pending', u'Pending'),
        (u'Rebooting', u'Rebooting'),
        (u'Configuring', u'Configuring'),
        (u'Running', u'Running'),
        (u'Terminated', u'Terminated'),
        (u'Stopping', u'Stopping'),
        (u'Stopped', u'Stopped'),
        (u'Stranded', u'Stranded'),
        (u'Unknown', u'Unknown'),
    )
    ENVIRONMENT_CHOICES = (
        (u'Production', u'Production'),
        (u'Stage', u'Stage'),
        (u'Test', u'Test'),
        (u'Decommissioned', u'Decommissioned'),
    )
    # Standard node fields
    name        = models.CharField(max_length=25)
    node_id     = models.CharField(max_length=50)
    provider    = models.ForeignKey(Provider)
    image       = models.ForeignKey(Image, null=True, blank=True)
    location    = models.ForeignKey(Location, null=True, blank=True)
    size        = models.ForeignKey(Size, null=True, blank=True)

    state       = models.CharField(
        default='Begin', max_length=20, choices=STATE_CHOICES
    )
    hostname    = models.CharField(max_length=25, blank=True)
    _extra_data = models.TextField(blank=True)

    # Overmind related fields
    environment = models.CharField(
        default='Production', max_length=2, choices=ENVIRONMENT_CHOICES
    )
    created_by   = models.CharField(max_length=25)
    destroyed_by = models.CharField(max_length=25, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    destroyed_at = models.DateTimeField(null=True)

    @property
    def public_ips(self):
        return self.ips.filter(is_public=True)


    @property
    def private_ips(self):
        return self.ips.filter(is_public=False)

    # Backward compatibility properties
    @property
    def public_ip(self):
        public_ips = self.ips.filter(is_public=True).filter(version=4)
        if len(public_ips):
            return public_ips[0].address
        return ''

    @property
    def private_ip(self):
        private_ips = self.ips.filter(is_public=False)
        if len(private_ips):
            return private_ips[0].address
        return ''

    # helper for related ips creation
    def sync_ips(self, ips, public=True):
        """Sync IP for a node"""
        previous = self.ips.filter(is_public=public).order_by('position')
        addrs = []
        for i in ips:
            addr = IP(i)
            addrs.append(addr)
        new_ips = [x.strFullsize() for x in addrs]
        for p in previous:
            if p.address in new_ips:
                p.position = new_ips.index(p.address)
            else:
                p.delete()
        for a in addrs:
            if a.strFullsize() not in [x.address for x in previous]:
                # Create new nodeip object
                NodeIP.objects.create(
                    address=a.strFullsize(),
                    position=new_ips.index(a.strFullsize()),
                    version=a.version(), is_public=public, node=self
                )

    class Meta:
        unique_together  = (('provider', 'name'), ('provider', 'node_id'))

    def __unicode__(self):
        return "<" + str(self.provider) + ": " + self.name + " - " + self.public_ip + " - " + str(self.node_id) + ">"

    def save_extra_data(self, data):
        self._extra_data = json.dumps(data)

    def extra_data(self):
        if self._extra_data == '':
            return {}
        return json.loads(self._extra_data)

    def reboot(self):
        '''Returns True if the reboot was successful, otherwise False'''
        if not self.provider.supports('reboot'):
            return True

        ret = self.provider.reboot_node(self)
        if ret:
            logging.debug('Rebooted %s' % self)
        else:
            logging.warn('Could not reboot node %s' % self)
        return ret

    def destroy(self, username):
        '''Returns True if the destroy was successful, otherwise False'''
        if self.provider.supports('destroy'):
            ret = self.provider.destroy_node(self)
            if ret:
                logging.info('Destroyed %s' % self)
            else:
                logging.error("controler.destroy_node() did not return True: %s.\nnot calling Node.delete()" % ret)
                return False
        self.decommission()
        self.destroyed_by = username
        self.destroyed_at = datetime.datetime.now()
        self.save()
        return True

    def decommission(self):
        '''Rename node and set its environment to decomissioned'''
        self.state = 'Terminated'
        # Rename node to free the name for future use
        counter = 1
        newname = "DECOM" + str(counter) + "-" + self.name
        while(len(Node.objects.filter(
                provider=self.provider,name=newname
            ).exclude(
                id=self.id
            ))):
            counter += 1
            newname = "DECOM" + str(counter) + "-" + self.name
        self.name = newname

        # Mark as decommissioned and save
        self.environment  = 'Decommissioned'
        self.save()

########NEW FILE########
__FILENAME__ = dedicated
# Dedicated Hardware plugin
from libcloud.compute.base import ConnectionKey, NodeDriver, Node
from libcloud.compute.types import NodeState

display_name = "Dedicated Hardware"
access_key   = None
secret_key   = None
form_fields  = ['ip']
supported_actions = ['create']


class Connection(ConnectionKey):
    '''Dummy connection'''
    def connect(self, host=None, port=None):
        pass


class Driver(NodeDriver):
    name = display_name
    type = 0

    def __init__(self, creds):
        self.creds = creds
        self.connection = Connection(self.creds)
    
    def _validate_ip(self, ip):
        try:
            # Validate with IPy module
            from IPy import IP
            try:
                IP(ip)
            except ValueError:
                raise Exception, "Incorrect IP"
        except ImportError:
            # Validate with regex
            import re
            valid_ip_regex = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
            if re.match(valid_ip_regex, ip) is None:
                raise Exception, "Incorrect IP"
    
    def create_node(self, **kwargs):
        # Validate IP address
        ip = kwargs.get('ip', '')
        self._validate_ip(ip)
        
        # Return Node object (IP serves as id feed)
        n = Node(id=ip.replace(".",""),
                 name=kwargs.get('name'),
                 state=NodeState.RUNNING,
                 public_ip=[ip],
                 private_ip=[],
                 driver=self)
        return n

########NEW FILE########
__FILENAME__ = hetzner
# Hetzner plugin
import json
from urllib import urlencode

from libcloud.compute.base import NodeDriver, Node
from libcloud.compute.types import NodeState, InvalidCredsException
import httplib2

display_name = "Hetzner"
access_key   = 'User'
secret_key   = 'Password'
form_fields  = None
# It seems that reboot (reset in the Hetzner API) doesn't work, so don't add
supported_actions = ['list']


class Connection():
    host = "https://robot-ws.your-server.de/"

    def __init__(self, user, password):
        self.conn = httplib2.Http(".cache")
        self.conn.add_credentials(user, password)

    def _raise_error(self, response, content):
        if response.get('status') == '400':
            raise Exception, "Invalid parameters"
        elif response.get('status') == '401':
            raise InvalidCredsException
        elif response.get('status') == '404' and content == 'Server not found':
            raise Exception, "Server not found"
        elif response.get('status') == '404':
            raise Exception, "Reset not available"
        elif response.get('status') == '500' and content == 'Reset failed':
            raise Exception, "Reset failed"
        else:
            raise Exception, "Unknown error: " + response.get('status')

    def request(self, path, method='GET', params=None):
        if method != 'GET' and method != 'POST': return None
        data = None
        if params: data = urlencode(params)
        response, content = self.conn.request(
            self.host + path,
            method,
            data,
        )
        if response.get('status') == '200':
            return json.loads(content)
        else:
            self._raise_error(response, content)


class Driver(NodeDriver):
    name = display_name
    type = 0

    NODE_STATE_MAP = {
        'ready': NodeState.RUNNING,
        'process': NodeState.PENDING,
    }

    def __init__(self, user, password):
        self.connection = Connection(user, password)

    def _parse_nodes(self, data):
        nodes = []
        for n in data:
            nodedata = n['server']
            response = self.connection.request('server/%s' % nodedata['server_ip'])
            nodedata['extra_ips'] = ", ".join(response['server']['ip'])
            # dict.get() will return None even if we write get('subnet', [])
            subnets = response['server'].get('subnet') or []
            nodedata['subnet'] = ", ".join(s['ip'] for s in subnets)
            nodes.append(nodedata)
        return nodes

    def _to_node(self, el):
        public_ip = [el.get('server_ip')]
        n = Node(id=el.get('server_ip').replace(".",""),
                 name=el.get('server_ip'),
                 state=self.NODE_STATE_MAP.get(el.get('status'), NodeState.UNKNOWN),
                 public_ip=public_ip,
                 private_ip=[],
                 driver=self,
                 extra={
                    'location':   el.get('dc'),
                    'product':    el.get('product'),
                    'traffic':    el.get('traffic'),
                    'paid_until': el.get('paid_until'),
                    'extra_ips':  el.get('extra_ips'),
                    'subnet':     el.get('subnet'),
                 })
        return n

    def list_nodes(self):
        #TODO: 404 error "No server found" needs to be handled
        response = self.connection.request('server')
        nodes = []
        for node in self._parse_nodes(response):
            nodes.append(self._to_node(node))
        return nodes

    def reboot(self, node):
        params = { 'type': 'sw' }#Support hd reset?
        response = self.connection.request(
            'reset/' + node.public_ip[0] + "/", method='POST', params=params
        )

########NEW FILE########
__FILENAME__ = provider_meta
# List of supported providers and related info
from django.conf import settings
from provisioning import plugins

LIBCLOUD_PROVIDERS = {
    'DUMMY': {
        'display_name': 'Dummy Provider',
        'access_key': 'Dummy Access Key',
        'secret_key': None,
    },
    'EC2_US_WEST': {
        'display_name': 'EC2 US West',
        'access_key': 'AWS Access Key ID',
        'secret_key': 'AWS Secret Key',
        # ex_keyname is needed for EC2 to have our ssh key deployed to nodes
        'extra_param': ['ex_keyname', settings.PUBLIC_KEY_FILE.split(".")[0]],
    },
    'EC2_US_EAST': {
        'display_name': 'EC2 US East',
        'access_key': 'AWS Access Key ID',
        'secret_key': 'AWS Secret Key',
        'extra_param': ['ex_keyname', settings.PUBLIC_KEY_FILE.split(".")[0]],
    },
    'EC2_EU_WEST': {
        'display_name': 'EC2 EU West',
        'access_key': 'AWS Access Key ID',
        'secret_key': 'AWS Secret Key',
        'extra_param': ['ex_keyname', settings.PUBLIC_KEY_FILE.split(".")[0]],
    },
    'RACKSPACE': {
        'display_name': 'Rackspace',
        'access_key': 'Username',
        'secret_key': 'API Access Key',
    },
}

PROVIDERS = {}

def add_libcloud_providers():
    for provider in LIBCLOUD_PROVIDERS.keys():
        PROVIDERS[provider] = LIBCLOUD_PROVIDERS[provider]
        PROVIDERS[provider]['supported_actions'] = [
            'create', 'destroy', 'reboot',
            'list', 'images', 'sizes', 'locations',
        ]
        PROVIDERS[provider]['form_fields'] = ['image', 'size', 'location']

def add_plugins():
    plugin_dict = plugins.load_plugins()
    for provider in plugin_dict.keys():
        PROVIDERS[provider] = plugin_dict[provider]

add_libcloud_providers()
add_plugins()

########NEW FILE########
__FILENAME__ = tasks
from celery.task import task, periodic_task
from celery.task.sets import subtask
from libcloud.common.types import InvalidCredsException
from provisioning.models import Provider
from datetime import timedelta


@periodic_task(run_every=timedelta(seconds=30))
def update_providers(**kwargs):
    logger = update_providers.get_logger(**kwargs)
    logger.debug("Syncing providers...")
    for prov in Provider.objects.filter(ready=True):
        import_sizes.delay(prov.id)
        import_nodes.delay(prov.id)

@task()
def import_provider_info(provider_id, **kwargs):
    logger = import_provider_info.get_logger(**kwargs)
    prov = Provider.objects.get(id=provider_id)
    logger.debug('Importing info for provider %s...' % prov)
    import_images.delay(provider_id, callback=subtask(import_locations,
                                callback=subtask(import_sizes,
                                    callback=subtask(import_nodes))))

@task(ignore_result=True)
def import_images(provider_id, callback=None, **kwargs):
    logger = import_images.get_logger(**kwargs)
    prov = Provider.objects.get(id=provider_id)
    logger.debug('Importing images for provider %s...' % prov)
    prov.import_images()
    if callback:
        subtask(callback).delay(provider_id)

@task(ignore_result=True)
def import_locations(provider_id, callback=None, **kwargs):
    logger = import_locations.get_logger(**kwargs)
    prov = Provider.objects.get(id=provider_id)
    logger.debug('Importing locations for provider %s...' % prov)
    prov.import_locations()
    if callback:
        subtask(callback).delay(provider_id)

@task(ignore_result=True)
def import_sizes(provider_id, callback=None, **kwargs):
    logger = import_sizes.get_logger(**kwargs)
    prov = Provider.objects.get(id=provider_id)
    logger.debug('Importing sizes for provider %s...' % prov)
    prov.import_sizes()
    if callback:
        subtask(callback).delay(provider_id)


@task(ignore_result=True)
def import_nodes(provider_id, **kwargs):
    logger = import_nodes.get_logger(**kwargs)
    prov = Provider.objects.get(id=provider_id)
    logger.debug('Importing nodes for provider %s...' % prov)
    prov.import_nodes()
    if not prov.ready:
        prov.ready = True
        prov.save()

########NEW FILE########
__FILENAME__ = tests

########NEW FILE########
__FILENAME__ = views
import logging
import json

from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required, permission_required
from django.template import RequestContext
from libcloud.common.types import InvalidCredsException

from provisioning.models import Action, Provider, Node, get_state, Image
from provisioning import tasks
from provisioning.forms import ProviderForm, NodeForm, AddImageForm, ProfileEditForm
from provisioning.forms import UserCreationFormExtended, UserEditForm
from provisioning.provider_meta import PROVIDERS


@login_required
def overview(request):
    provider_list = Provider.objects.all()
    nodes = []
    #TODO: Optimize for hundreds of nodes
    for n in Node.objects.exclude(environment='Decommissioned'):
        datatable = "<table>"
        fields = [
            ['Created by', n.created_by],
            ['Created at', n.created_at.strftime('%Y-%m-%d %H:%M:%S')],
            ['Node ID', n.node_id],
            ['OS image', n.image or "-"],
            ['Location', n.location or "-"],
            ['Size', n.size or "-"],
        ]
        if n.size and n.size.price:
            fields.append(['Price', n.size.price + ' $/hour'])
        fields.append(['-----', '-----'])
        if n.destroyed_by:
            fields.append(['Destroyed by', n.destroyed_by])
            fields.append(['Destroyed at', n.destroyed_at])
        if n.private_ip:
            fields.append(['private_ip', n.private_ip])

        for key, val in n.extra_data().items():
            fields.append([key, val])

        for field in fields:
            datatable += "<tr><td>" + field[0] + ":</td><td>" + str(field[1])
            datatable += "</td></tr></td>"
        datatable += "</table>"

        actions_list = []
        if n.state != 'Terminated' and \
            request.user.has_perm('provisioning.change_node'):
            actions = n.provider.actions.filter(show=True)

            if actions.filter(name='reboot'):
                actions_list.append({
                    'action': 'reboot',
                    'label': 'reboot',
                    'confirmation': 'Are you sure you want to reboot the node "%s"'\
                    % n.name,
                })

            if actions.filter(name='destroy'):
                actions_list.append({
                    'action': 'destroy',
                    'label': 'destroy',
                    'confirmation': 'This action will completely destroy the node %s'\
                    % n.name,
                })
            else:
                actions_list.append({
                    'action': 'destroy',
                    'label': 'delete',
                    'confirmation': 'This action will remove the node %s with IP %s' % (n.name, n.public_ip),
                })

        nodes.append({ 'node': n, 'data': datatable, 'actions': actions_list })

    variables = RequestContext(request, {
        'nodes': nodes,
        'provider_list': provider_list,
    })
    return render_to_response('overview.html', variables)

@permission_required('provisioning.add_provider')
def provider(request):
    providers = []
    provider_types = PROVIDERS.keys()
    provider_types.sort()
    for p in provider_types:
        providers.append([p, PROVIDERS[p]['display_name']])

    variables = RequestContext(request, {
        'provider_types': providers, 'user': request.user,
    })
    return render_to_response('provider.html', variables)

@permission_required('provisioning.add_provider')
def newprovider(request):
    error = None
    if request.method == 'POST':
        error, form, prov = save_new_provider(request.POST)
        if error is None:
            return HttpResponse('<p>success</p>')
    else:
        form = ProviderForm(request.GET.get("provider_type"))
    if error == 'form':
        error = None
    return render_to_response('provider_form.html',
        { 'form': form, 'error': error })

def save_new_provider(data):
    form = ProviderForm(data.get('provider_type'), data)
    return save_provider(form)

def update_provider(data, provider):
    form = ProviderForm(data.get('provider_type'), data, instance=provider)
    return save_provider(form)

def save_provider(form):
    error = None
    if form.is_valid():
        provider = None
        try:
            provider = form.save()
            # Make sure the credentials are correct
            provider.check_credentials()

            logging.info('Provider saved %s' % provider.name)
            result = tasks.import_provider_info.delay(provider.id)
        except InvalidCredsException:
            # Delete provider if InvalidCreds is raised (by EC2)
            # after it has been saved
            if provider:
                provider.delete()
            # Return form with InvalidCreds error
            error = 'Invalid account credentials'
        else:
            return None, form, provider
    else:
        error = 'form'
    return error, form, None

@login_required
def updateproviders(request):
    providers = Provider.objects.all()
    for provider in providers:
        if provider.supports('list'):
            provider.update()
    return HttpResponseRedirect('/overview/')

@permission_required('provisioning.delete_provider')
def deleteprovider(request, provider_id):
    provider = Provider.objects.get(id=provider_id)
    provider.delete()
    return HttpResponseRedirect('/overview/')

@permission_required('provisioning.add_node')
def node(request):
    '''Displays a provider selection list to call the node creation form'''
    variables = RequestContext(request, {
        'provider_list': Action.objects.get(name='create').provider_set.all(),
    })
    return render_to_response('node.html', variables)

@permission_required('provisioning.add_node')
def addimage(request):
    error = None
    if request.method == 'POST':
        form = AddImageForm(request.POST.get("provider"), request.POST)
        if form.is_valid():
            img = form.cleaned_data['image']
            img.favorite = True
            img.save()
            favimage = {'name': img.name, 'image_id': img.image_id, 'id': img.id}
            return HttpResponse(json.dumps(favimage))
    else:
        form = AddImageForm(request.GET.get("provider"))
    return render_to_response('image_form.html', { 'form': form, 'error': error })

@permission_required('provisioning.add_node')
def removeimage(request, image_id):
    if request.method == 'POST':
        try:
            image = Image.objects.get(id=image_id)
            image.favorite = False
            image.save()
            return HttpResponse("<p>SUCCESS</p>" % image)
        except Image.DoesNotExist:
            error = "<p>Image id %s does not exist</p>" % image_id
    else:
        error = "<p>Only POST Allowed</p>"
    return HttpResponse(error)

@permission_required('provisioning.add_node')
def newnode(request):
    error = None
    favcount = 0
    if request.method == 'POST':
        error, form, node = save_new_node(request.POST, request.user)
        if error is None:
            return HttpResponse('<p>success</p>')
    else:
        form = NodeForm(request.GET.get("provider"))
        favcount = Image.objects.filter(
            provider=request.GET.get("provider"),
            favorite=True
        ).count()
    if error == 'form':
        error = None
    return render_to_response('node_form.html',
        { 'form': form, 'favcount': favcount, 'error': error })

def save_new_node(data, user):
    provider_id = data.get("provider")
    if not provider_id:
        return 'Incorrect provider id', None, None
    error = None
    form = None
    try:
        provider = Provider.objects.get(id=provider_id)
        form = NodeForm(provider_id, data)
    except Provider.DoesNotExist:
        error = 'Incorrect provider id'

    if form is not None:
        if form.is_valid():
            try:
                node = Node.objects.get(
                    provider=provider, name=form.cleaned_data['name']
                )
                error = 'A node with that name already exists'
            except Node.DoesNotExist:
                error, data_from_provider = provider.create_node(form)
                if error is None:
                    node = form.save(commit = False)
                    node.node_id    = str(data_from_provider['node_id'])
                    node.public_ip  = data_from_provider['public_ip']
                    node.private_ip = data_from_provider.get('private_ip', '')
                    node.state      = get_state(data_from_provider['state'])
                    node.created_by = user.username
                    node.save_extra_data(data_from_provider.get('extra', ''))
                    try:
                        node.save()
                        logging.info('New node created %s' % node)
                        # Mark image as recently used by saving it
                        if node.image is not None:
                            node.image.save()
                        return None, form, node
                    except Exception, e:
                        error = e
                        logging.error('Could not create node: %s' % e)
        else:
            error = 'form'
    return error, form, None

@permission_required('provisioning.change_node')
def rebootnode(request, node_id):
    node = Node.objects.get(id=node_id)
    result = node.reboot()
    return HttpResponseRedirect('/overview/')

@permission_required('provisioning.delete_node')
def destroynode(request, node_id):
    node = Node.objects.get(id=node_id)
    result = node.destroy(request.user.username)
    return HttpResponseRedirect('/overview/')

@login_required
def settings(request):
    variables = RequestContext(request, {
        'user_list': User.objects.all(),
    })
    return render_to_response('settings.html', variables)

def count_admin_users():
    '''Returns the number of users belonging to the Admin group
 or having superuser rights'''
    g = get_object_or_404(Group, name='Admin')
    admin_users_count = len(g.user_set.all())
    admin_users_count += len(User.objects.filter(is_superuser=True))
    return admin_users_count

@permission_required('auth.add_user')
def adduser(request):
    if request.method == 'POST':
        form = UserCreationFormExtended(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse('<p>success</p>')
    else:
        form = UserCreationFormExtended()

    return render_to_response("registration/register.html",
        {'form': form, 'editing': False}
    )

@login_required
def edituser(request, id):
    edit_user = get_object_or_404(User, id=id)
    if not request.user.has_perm('auth.change_user') and request.user.id != int(id):
        # If user doesn't have auth permissions and he/she is not editting
        # his/her own profile don't allow the operation
        return HttpResponse("<p>Your don't have permissions to edit users</p>")

    if request.method == 'POST':
        if request.user.has_perm('auth.change_user'):
            admin   = Group.objects.get(name='Admin')
            oldrole = admin if admin in edit_user.groups.all() else False
            newrole = Group.objects.get(id=request.POST.get('group'))
            if oldrole is admin and newrole != admin and count_admin_users() <= 1:
                errormsg = "<p>Not allowed: you cannot remove admin rights"
                errormsg += " from the only admin user</p>"
                return HttpResponse(errormsg)
            form = UserEditForm(request.POST, instance=edit_user)
        else:
            form = ProfileEditForm(request.POST, instance=edit_user)

        if form.is_valid():
            form.save()
            return HttpResponse('<p>success</p>')
    else:
        if request.user.has_perm('auth.change_user'):
            form = UserEditForm(instance=edit_user)
        else:
            form = ProfileEditForm(instance=edit_user)

    variables = RequestContext(request, {
        'form': form, 'editing': True, 'edit_user': edit_user
    })
    return render_to_response("registration/register.html", variables)

@permission_required('auth.delete_user')
def deleteuser(request, id):
    user = get_object_or_404(User, id=id)
    if user.has_perm('auth.add_user') and count_admin_users() <= 1:
        return HttpResponse(
            "<p>Not allowed: You cannot delete the only admin user</p>")
    user.delete()
    return HttpResponse('<p>success</p>')

########NEW FILE########
__FILENAME__ = settings
# Django settings for Overmind project.
import os, logging
import djcelery

djcelery.setup_loader()
BROKER_HOST = "localhost"
BROKER_PORT = 5672
BROKER_USER = "guest"
BROKER_PASSWORD = "guest"
BROKER_VHOST = "/"

DEBUG = True
TEMPLATE_DEBUG = DEBUG

BASEDIR = os.path.abspath( os.path.dirname(__file__).replace('\\','/') )

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'data.db'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = BASEDIR + '/media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin_media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'po7j6y(so=k75zpzu4^fpquj%&^s9j$ix9se9kth(9qi!0(z&s'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.csrf.CsrfResponseMiddleware',
)

ROOT_URLCONF = 'overmind.urls'

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), 'templates').replace('\\','/'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'djcelery',
    'django.contrib.sites',
    'provisioning',
    'api',
)

PUBLIC_KEY_FILE = "id_rsa.pub"
PUBLIC_KEY = open(os.path.expanduser("~/.ssh/%s" % PUBLIC_KEY_FILE)).read()

# Configure logging
if DEBUG:
    logging.basicConfig(
        level = logging.DEBUG,
        format = '%(asctime)s %(levelname)s: %(message)s',
    )
else:
    logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s %(levelname)s: %(message)s',
        filename = BASEDIR + '/log.log',
        filemode = 'w',
    )

########NEW FILE########
__FILENAME__ = test_urls
from django.conf.urls.defaults import patterns, include
from urls import urlpatterns as normal_urlpatterns

urlpatterns = patterns('',
    (r'^api/', include('overmind.api.test_urls'))
)

urlpatterns += normal_urlpatterns

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.views.generic.simple import redirect_to
from django.conf import settings


urlpatterns = []

if settings.DEBUG:
    urlpatterns = patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    )

urlpatterns += patterns('',
    (r'^api/', include('overmind.api.urls')),
)

# Provisioning
urlpatterns += patterns('',
    (r'^overview/$', 'provisioning.views.overview'),
    (r'^provider/$', 'provisioning.views.provider'),
    (r'^node/$', 'provisioning.views.node'),
    (r'^settings/$', 'provisioning.views.settings'),
    
    # Create
    (r'^provider/new/$', 'provisioning.views.newprovider'),
    (r'^node/new/$', 'provisioning.views.newnode'),
    (r'^node/image/add/$', 'provisioning.views.addimage'),
    (r'^node/image/(?P<image_id>\d+)/remove/$', 'provisioning.views.removeimage'),
    
    # Update
    (r'^provider/update/$', 'provisioning.views.updateproviders'),
    
    # Reboot
    (r'^node/(?P<node_id>\d+)/reboot/$', 'provisioning.views.rebootnode'),
    
    # Delete
    (r'^provider/(?P<provider_id>\d+)/delete/$',\
        'provisioning.views.deleteprovider'),
    (r'^node/(?P<node_id>\d+)/destroy/$', 'provisioning.views.destroynode'),

    (r'^$', redirect_to, {'url': '/overview/', 'permanent': False}),
)

# Users
urlpatterns += patterns('',
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout'),
    (r'^accounts/new/$', 'provisioning.views.adduser'),
    (r'^accounts/edit/(?P<id>\d+)/$', 'provisioning.views.edituser'),
    (r'^accounts/delete/(?P<id>\d+)/$', 'provisioning.views.deleteuser'),
)

########NEW FILE########
