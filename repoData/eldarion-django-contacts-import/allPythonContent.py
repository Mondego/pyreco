__FILENAME__ = base
from contacts_import.conf import settings


class Importer(object):
    
    form_class = None
    
    def get_authentication_url(self):
        raise NotImplementedError()
    
    def run(self, *args, **kwargs):
        """
        Called when we are ready to do the import of contacts. This method
        will call process which calls the importer's handle to generate
        contacts from the given arguments.
        """
        # @@@ async? (consider how args and kwargs should be serialized;
        # that may change things quite a bit)
        self.process((args, kwargs))
    
    def process(self, args):
        """
        Handles the processing of contacts import and passes data to the
        callback for site specific processing. This method may not run in the
        same process that handled the web request.
        """
        contacts = self.handle(*args[0], **args[1])
        settings.CONTACTS_IMPORT_CALLBACK(contacts)
    
    def handle(self, *args, **kwargs):
        """
        This method should be overridden by our children to do what is best
        for them.
        """
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = csv
from __future__ import absolute_import

import csv

from django import forms

from contacts_import.backends.importers.base import Importer


def guess_email(entry):
    if "E-mail Address" in entry: # outlook
        return entry["E-mail Address"]
    if "E-mail 1 - Value" in entry: # gmail
        return entry["E-mail 1 - Value"]
    return None


def guess_name(entry):
    if "Name" in entry: # gmail
        return entry["Name"]
    if "First Name" in entry and "Last Name" in entry: # outlook
        return entry["First Name"] + " " + entry["Last Name"]
    if "Given Name" in entry and "Family Name" in entry: # gmail alt
        return entry["Given Name"] + " " + entry["Family Name"]
    return None


class CSVImportForm(forms.Form):
    
    file = forms.FileField()


class CSVImporter(Importer):
    
    name = "CSV"
    form_class = CSVImportForm
    
    def handle(self, form):
        for entry in csv.DictReader(form.cleaned_data["file"]):
            email = guess_email(entry)
            name = guess_name(entry)
            if email and name:
                yield {"email": email, "name": name}

########NEW FILE########
__FILENAME__ = google
from django.core.urlresolvers import reverse

from contacts_import.backends.importers.base import Importer


class GoogleImporter(Importer):
    
    name = "Gmail"
    oauth_service = "google"
    
    def get_authentication_url(self):
        return reverse("oauth_access_login", kwargs=dict(service=self.oauth_service))

########NEW FILE########
__FILENAME__ = vcard
from __future__ import absolute_import

from django import forms

import vobject

from contacts_import.backends.importers.base import Importer


class vCardImportForm(forms.Form):
    
    file = forms.FileField()


class vCardImporter(Importer):
    
    name = "vCard"
    form_class = vCardImportForm
    
    def handle(self, form):
        for entry in vobject.readComponents(form.cleaned_data["file"]):
            yield {
                "email": entry.email.value,
                "name": entry.fn.value
            }

########NEW FILE########
__FILENAME__ = yahoo
from django.core.urlresolvers import reverse

from contacts_import.backends.importers.base import Importer


class YahooImporter(Importer):
    
    name = "Yahoo! Mail"
    oauth_service = "yahoo"
    
    def get_authentication_url(self):
        return reverse("oauth_access_login", kwargs=dict(service=self.oauth_service))

########NEW FILE########
__FILENAME__ = callbacks
from django.core.exceptions import ImproperlyConfigured


def dummy(contacts):
    raise ImproperlyConfigured("CONTACTS_IMPORT_CALLBACK is set to a dummy "
        "callback. You should define your own.")


def debug(contacts):
    print "imported:"
    for contact in contacts:
        print repr(contact)
    print "done"

########NEW FILE########
__FILENAME__ = conf
import functools

from django.conf import settings

from appconf import AppConf

from contacts_import.utils import load_path_attr


class ContactsImportAppConf(AppConf):
    
    IMPORTERS = {
        "gmail": "contacts_import.backends.importers.google.GoogleImporter",
        "yahoo": "contacts_import.backends.importers.yahoo.YahooImporter",
        "vcard": "contacts_import.backends.importers.vcard.vCardImporter",
        "csv": "contacts_import.backends.importers.csv.CSVImporter",
    }
    CALLBACK = "contacts_import.callbacks.dummy"
    
    class Meta:
        prefix = "contacts_import"
    
    def configure_importers(self, value):
        return {k: functools.partial(load_path_attr, v) for k, v in value.iteritems()}
    
    def configure_callback(self, value):
        return load_path_attr(value)

########NEW FILE########
__FILENAME__ = models
# empty
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

from contacts_import.views import (
    ImportBeginView, ImportServiceView
)


urlpatterns = patterns("",
    url(r"^$", ImportBeginView.as_view(), name="contacts_import"),
    url(r"^(?P<service>\w+)/$", ImportServiceView.as_view(), name="contacts_import_service"),
)
########NEW FILE########
__FILENAME__ = utils
import importlib

from django.core.exceptions import ImproperlyConfigured


def load_path_attr(path):
    i = path.rfind(".")
    module, attr = path[:i], path[i+1:]
    try:
        mod = importlib.import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured("Error importing %s: '%s'" % (module, e))
    try:
        attr = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured("Module '%s' does not define a '%s'" % (module, attr))
    return attr

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from contacts_import.conf import settings


class ImportBeginView(TemplateView):
    
    template_name = "contacts_import/import_begin.html"


class ImportServiceView(FormView):
    
    template_name = "contacts_import/import_service.html"
    
    def dispatch(self, request, *args, **kwargs):
        try:
            Importer = settings.CONTACTS_IMPORT_IMPORTERS[kwargs["service"]]()
        except KeyError:
            raise Http404()
        self.importer = Importer()
        return super(ImportServiceView, self).dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        ctx = kwargs
        ctx["importer"] = self.importer
        return ctx
    
    def get_form_class(self):
        return self.importer.form_class
    
    def get_form(self, form_class):
        if form_class:
            return super(ImportServiceView, self).get_form(form_class)
    
    def form_valid(self, form):
        self.importer.run(form=form)
        return HttpResponse("done")

########NEW FILE########
