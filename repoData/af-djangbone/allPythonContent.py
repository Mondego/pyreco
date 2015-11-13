__FILENAME__ = models
# Empty models.py, which helps django recognize this as an app.

########NEW FILE########
__FILENAME__ = tests
import json
from django import forms
from django.contrib.auth.models import User
from django.http import Http404
from django.test.client import RequestFactory
from django.utils import unittest

from djangbone.views import BackboneAPIView


class AddUserForm(forms.ModelForm):
    """
    Simple ModelForm for testing POST requests.
    """
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name')

    def set_request(self, request):
        """
        add_form_class and edit_form_class classes can optionally provide this
        method in order to get access to the request object.
        """
        self.request = request

class EditUserForm(forms.ModelForm):
    """
    Simple ModelForm for testing PUT requests.
    """
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name')

    def set_request(self, request):
        """
        add_form_class and edit_form_class classes can optionally provide this
        method in order to get access to the request object.
        """
        self.request = request


class ReadOnlyView(BackboneAPIView):
    """
    BackboneAPIView subclass for testing read-only functionality.
    """
    base_queryset = User.objects.all()
    serialize_fields = ('id', 'username', 'first_name', 'last_name')

class FullView(BackboneAPIView):
    """
    The subclass used to test BackboneAPIView's PUT/POST requests.
    """
    base_queryset = User.objects.all()
    add_form_class = AddUserForm
    edit_form_class = EditUserForm
    serialize_fields = ('id', 'username', 'first_name', 'last_name')
    page_size = 2


class ViewTest(unittest.TestCase):
    """
    Tests for BackboneAPIView.

    Note that django.contrib.auth must be in INSTALLED_APPS for these to work.
    """
    def setUp(self):
        self.factory = RequestFactory()
        self.view = ReadOnlyView.as_view()
        self.writable_view = FullView.as_view()
        self.user1 = User.objects.create(username='test1', first_name='Test', last_name='One')

    def tearDown(self):
        User.objects.all().delete()

    def add_two_more_users(self):
        self.user2 = User.objects.create(username='test2', first_name='Test', last_name='Two')
        self.user3 = User.objects.create(username='test3', first_name='Test', last_name='Three')

    def test_collection_get(self):
        request = self.factory.get('/users/')
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)

        # Ensure response json deserializes to a 1-item list:
        self.assert_(isinstance(response_data, list))
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]['username'], self.user1.username)

        # Try again with a few more users in the database:
        self.add_two_more_users()
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assert_(isinstance(response_data, list))
        self.assertEqual(len(response_data), 3)
        # With User model's default ordering (by id), user3 should be last:
        self.assertEqual(response_data[2]['username'], self.user3.username)

        # Test pagination:
        response = self.writable_view(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assert_(isinstance(response_data, list))
        self.assertEqual(len(response_data), 2)

        # Page 2 should only have one item:
        request = self.factory.get('/users/?p=2')
        response = self.writable_view(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assert_(isinstance(response_data, list))
        self.assertEqual(len(response_data), 1)

    def test_single_item_get(self):
        request = self.factory.get('/users/1')
        response = self.view(request, id='1')   # Simulate a urlconf passing in the 'id' kwarg
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assert_(isinstance(response_data, dict))
        self.assertEqual(response_data['username'], self.user1.username)

        # Ensure 404s are raised for non-existent items:
        request = self.factory.get('/users/7')
        self.assertRaises(Http404, lambda: self.view(request, id='7'))

    def test_post(self):
        request = self.factory.post('/users')
        response = self.view(request)
        self.assertEqual(response.status_code, 405)     # "Method not supported" if no add_form_class specified

        # Testing BackboneAPIView subclasses that support POST via add_form_class:

        # If no JSON provided in POST body, return HTTP 400:
        response = self.writable_view(request)
        self.assertEqual(response.status_code, 400)

        # Test the case where invalid input is given (leading to form errors):
        request = self.factory.post('/users', '{"wrong_field": "xyz"}', content_type='application/json')
        response = self.writable_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'ERROR: validation failed')

        # If valid JSON was provided, a new instance should be created:
        request = self.factory.post('/users', '{"username": "post_test"}', content_type='application/json')
        response = self.writable_view(request)
        self.assertEqual(response.status_code, 200)
        self.assert_(User.objects.get(username='post_test'))
        response_json = json.loads(response.content)
        self.assertEqual(response_json['username'], 'post_test')

    def test_put(self):
        request = self.factory.put('/users/1')
        response = self.view(request, id='1')
        self.assertEqual(response.status_code, 405)     # "Method not supported" if no edit_form_class specified

        # PUT is also not supported for collections (when no id is provided):
        request = self.factory.put('/users')
        response = self.writable_view(request)
        self.assertEqual(response.status_code, 405)

        # If no JSON in PUT body, return HTTP 400:
        response = self.writable_view(request, id='1')
        self.assertEqual(response.status_code, 400)

        # Raise 404 if an object with the given id doesn't exist:
        request = self.factory.put('/users/27', '{"username": "put_test"}', content_type='application/json')
        self.assertRaises(Http404, lambda: self.writable_view(request, id='27'))

        # If the object exists and an edit_form_class is supplied, it actually does something:
        request = self.factory.put('/users/1', '{"username": "put_test"}', content_type='application/json')
        response = self.writable_view(request, id='1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.get(id=1).username, 'put_test')
        response_json = json.loads(response.content)
        self.assertEqual(response_json['username'], 'put_test')

        # Test the case where invalid input is given (leading to form errors):
        request = self.factory.put('/users/1', '{"wrong_field": "xyz"}', content_type='application/json')
        response = self.writable_view(request, id='1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'ERROR: validation failed')

    def test_delete(self):
        # Delete is not supported for collections:
        request = self.factory.delete('/users')
        response = self.view(request)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(User.objects.filter(id=1).count(), 1)

        # But it is supported for single items (specified by id):
        request = self.factory.delete('/users/1')
        response = self.view(request, id='1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(id=1).count(), 0)

        # Should raise 404 if we try to access a deleted resource again:
        request = self.factory.delete('/users/1')
        self.assertRaises(Http404, lambda: self.view(request, id='1'))

########NEW FILE########
__FILENAME__ = views
import datetime
import decimal
import json

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, Http404
from django.views.generic import View


class DjangboneJSONEncoder(json.JSONEncoder):
    """
    JSON encoder that converts additional Python types to JSON.
    """
    def default(self, obj):
        """
        Converts datetime objects to ISO-compatible strings during json serialization.
        Converts Decimal objects to floats during json serialization.
        """
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        else:
            return None



class BackboneAPIView(View):
    """
    Abstract class view, which makes it easy for subclasses to talk to backbone.js.

    Supported operations (copied from backbone.js docs):
        create -> POST   /collection
        read ->   GET    /collection[/id]
        update -> PUT    /collection/id
        delete -> DELETE /collection/id
    """
    base_queryset = None        # Queryset to use for all data accesses, eg. User.objects.all()
    serialize_fields = tuple()  # Tuple of field names that should appear in json output

    # Optional pagination settings:
    page_size = None            # Set to an integer to enable GET pagination (at the specified page size)
    page_param_name = 'p'       # HTTP GET parameter to use for accessing pages (eg. /widgets?p=2)

    # Override these attributes with ModelForm instances to support PUT and POST requests:
    add_form_class = None       # Form class to be used for POST requests
    edit_form_class = None      # Form class to be used for PUT requests

    # Override these if you have custom JSON encoding/decoding needs:
    json_encoder = DjangboneJSONEncoder()
    json_decoder = json.JSONDecoder()

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests, either for a single resource or a collection.
        """
        if kwargs.get('id'):
            return self.get_single_item(request, *args, **kwargs)
        else:
            return self.get_collection(request, *args, **kwargs)

    def get_single_item(self, request, *args, **kwargs):
        """
        Handle a GET request for a single model instance.
        """
        try:
            qs = self.base_queryset.filter(id=kwargs['id'])
            assert len(qs) == 1
        except AssertionError:
            raise Http404
        output = self.serialize_qs(qs)
        return self.success_response(output)

    def get_collection(self, request, *args, **kwargs):
        """
        Handle a GET request for a full collection (when no id was provided).
        """
        qs = self.base_queryset
        output = self.serialize_qs(qs)
        return self.success_response(output)

    def post(self, request, *args, **kwargs):
        """
        Handle a POST request by adding a new model instance.

        This view will only do something if BackboneAPIView.add_form_class is specified
        by the subclass. This should be a ModelForm corresponding to the model used by
        base_queryset.

        Backbone.js will send the new object's attributes as json in the request body,
        so use our json decoder on it, rather than looking at request.POST.
        """
        if self.add_form_class == None:
            return HttpResponse('POST not supported', status=405)
        try:
            request_dict = self.json_decoder.decode(request.raw_post_data)
        except ValueError:
            return HttpResponse('Invalid POST JSON', status=400)
        form = self.add_form_class(request_dict)
        if hasattr(form, 'set_request'):
            form.set_request(request)
        if form.is_valid():
            new_object = form.save()
            # Serialize the new object to json using our built-in methods.
            # The extra DB read here is not ideal, but it keeps the code DRY:
            wrapper_qs = self.base_queryset.filter(id=new_object.id)
            return self.success_response(self.serialize_qs(wrapper_qs, single_object=True))
        else:
            return self.validation_error_response(form.errors)

    def put(self, request, *args, **kwargs):
        """
        Handle a PUT request by editing an existing model.

        This view will only do something if BackboneAPIView.edit_form_class is specified
        by the subclass. This should be a ModelForm corresponding to the model used by
        base_queryset.
        """
        if self.edit_form_class == None or not kwargs.has_key('id'):
            return HttpResponse('PUT not supported', status=405)
        try:
            # Just like with POST requests, Backbone will send the object's data as json:
            request_dict = self.json_decoder.decode(request.raw_post_data)
            instance = self.base_queryset.get(id=kwargs['id'])
        except ValueError:
            return HttpResponse('Invalid PUT JSON', status=400)
        except ObjectDoesNotExist:
            raise Http404
        form = self.edit_form_class(request_dict, instance=instance)
        if hasattr(form, 'set_request'):
            form.set_request(request)
        if form.is_valid():
            item = form.save()
            wrapper_qs = self.base_queryset.filter(id=item.id)
            return self.success_response(self.serialize_qs(wrapper_qs, single_object=True))
        else:
            return self.validation_error_response(form.errors)

    def delete(self, request, *args, **kwargs):
        """
        Respond to DELETE requests by deleting the model and returning its JSON representation.
        """
        if not kwargs.has_key('id'):
            return HttpResponse('DELETE is not supported for collections', status=405)
        qs = self.base_queryset.filter(id=kwargs['id'])
        if qs:
            output = self.serialize_qs(qs)
            qs.delete()
            return self.success_response(output)
        else:
            raise Http404

    def serialize_qs(self, queryset, single_object=False):
        """
        Serialize a queryset into a JSON object that can be consumed by backbone.js.

        If the single_object argument is True, or the url specified an id, return a
        single JSON object, otherwise return a JSON array of objects.
        """
        values = queryset.values(*self.serialize_fields)
        if single_object or self.kwargs.get('id'):
            # For single-item requests, convert ValuesQueryset to a dict simply
            # by slicing the first item:
            json_output = self.json_encoder.encode(values[0])
        else:
            # Process pagination options if they are enabled:
            if isinstance(self.page_size, int):
                try:
                    page_number = int(self.request.GET.get(self.page_param_name, 1))
                    offset = (page_number - 1) * self.page_size
                except ValueError:
                    offset = 0
                values = values[offset:offset+self.page_size]
            json_output = self.json_encoder.encode(list(values))
        return json_output

    def success_response(self, output):
        """
        Convert json output to an HttpResponse object, with the correct mimetype.
        """
        return HttpResponse(output, mimetype='application/json')

    def validation_error_response(self, form_errors):
        """
        Return an HttpResponse indicating that input validation failed.

        The form_errors argument contains the contents of form.errors, and you
        can override this method is you want to use a specific error response format.
        By default, the output is a simple text response.
        """
        return HttpResponse('<p>ERROR: validation failed</p>' + str(form_errors), status=400)

########NEW FILE########
