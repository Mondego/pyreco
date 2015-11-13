__FILENAME__ = forms
from django import forms
from .models import Person
from companies.models import Company
from projects.models import Project


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = (
            'first_name', 'last_name', 'email', 'title'
        )
        widgets = {
            'title': forms.TextInput(attrs={'class': 'span3'})
        }

    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'span3'}))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'span3'}))
    email = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'span3'}))

    new_password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'span3'}))
    confirm = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'span3'}))

    def clean_confirm(self):
        password = self.cleaned_data['new_password']
        confirm = self.cleaned_data['confirm']
        if confirm != password:
            raise forms.ValidationError("The two passwords do not match.")
        if confirm != '':
            self.confirm = confirm
        return confirm

    def save(self, commit=True, *args, **kwargs):
        if hasattr(self, 'confirm'):
            self.instance.set_password(self.confirm)
        return super(PersonForm, self).save(commit, *args, **kwargs)


class CreatePersonForm(PersonForm):
    def __init__(self, *args, **kwargs):
        super(CreatePersonForm, self).__init__(*args, **kwargs)
        del self.fields['new_password']
        del self.fields['confirm']

    company = forms.ModelChoiceField(queryset=Company.objects.active(), widget=forms.Select(attrs={'class': 'span3'}))

    class Meta:
        model = Person
        fields = (
            'email', 'first_name', 'last_name', 'company'
        )

    def clean_email(self):
        try:
            Person.objects.get(username=self.cleaned_data['email'])
            raise forms.ValidationError("This email is already in use.")
        except Person.DoesNotExist:
            return self.cleaned_data['email']

    def save(self, *args, **kwargs):
        self.instance.username = self.cleaned_data['email']
        self.instance.set_unusable_password()
        self.instance.is_active = True
        self.instance.company = self.cleaned_data['company']
        return super(CreatePersonForm, self).save(*args, **kwargs)


class DeletedCompanyForm(forms.Form):
    company = forms.ModelChoiceField(queryset=Company.objects.deleted(),
                                     widget=forms.Select(attrs={'class': 'span3'}))

    def save(self):
        company = self.cleaned_data['company']
        company.set_active(True)
        return company


def permission_forms(request, person):
    return [PermissionsForm(request.POST or None, person=person, company=company) for company in
            Company.objects.active().filter(pk__in=Project.objects.active().values('company__pk'))]


class PermissionsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.person = kwargs.pop('person')
        self.company = kwargs.pop('company')
        self.projects = Project.objects.active().filter(company=self.company)
        super(PermissionsForm, self).__init__(*args, **kwargs)
        self.fields[self.company] = forms.BooleanField(required=False, label='Select/Unselect All',
                                                       widget=forms.CheckboxInput(
                                                           attrs={'class': 'company_checkbox',
                                                                  'pk_id': self.company.pk,
                                                           }))
        for project in self.projects:
            self.fields['%i' % project.pk] = forms.BooleanField(required=False, label=project,
                                                                initial=True if project.clients.filter(
                                                                    pk=self.person.pk).exists() else False,
                                                                widget=forms.CheckboxInput(
                                                                    attrs={'pk': self.company.pk}))

    def save(self):
        for project in self.projects:
            is_selected = self.cleaned_data['%i' % project.pk]
            if is_selected:
                if not project.clients.filter(pk=self.person.pk).exists():
                    project.clients.add(self.person)
            else:
                if project.clients.filter(pk=self.person.pk).exists():
                    project.clients.remove(self.person)

########NEW FILE########
__FILENAME__ = mixins
from django.contrib.auth import get_user
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls):
        return login_required(super(LoginRequiredMixin, cls).as_view())


class AdminRequiredMixin(object):
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        user = get_user(request)
        if not user.is_admin:
            raise PermissionDenied()
        return super(AdminRequiredMixin, self).dispatch(request, *args, **kwargs)

########NEW FILE########
__FILENAME__ = models
from django.conf import settings
from django.contrib.auth.models import UserManager, AbstractUser
from django.db import models
from django_localflavor_us.models import PhoneNumberField
from timezone_field import TimeZoneField
import companies
import projects
import datetime


class Person(AbstractUser):
    title = models.CharField(max_length=255, null=True, blank=True)
    company = models.ForeignKey('companies.Company')
    timezone = TimeZoneField(default=settings.TIME_ZONE, blank=True)
    access_new_projects = models.BooleanField(default=False)

    is_admin = models.BooleanField(default=False)

    # Phone numbers
    fax = PhoneNumberField(null=True, blank=True)
    home = PhoneNumberField(null=True, blank=True)
    mobile = PhoneNumberField(null=True, blank=True)
    office = PhoneNumberField(null=True, blank=True)
    ext = models.CharField(max_length=10, null=True, blank=True)

    last_updated = models.DateTimeField(auto_now=True, auto_now_add=True)
    removed = models.DateField(null=True)

    objects = UserManager()

    class Meta:
        ordering = ['first_name', 'last_name']
        db_table = 'kala_person'

    def set_active(self, active):
        self.is_active = active
        if not self.is_active:
            self.removed = datetime.date.today()
        self.save()

    def get_companies(self):
        if self.is_admin:
            _companies = companies.models.Company.objects.active()
        else:
            _companies = companies.models.Company.objects.active().filter(
                pk__in=projects.models.Project.clients.through.objects.filter(person__pk=self.pk).values(
                    'project__company__pk'))
        has_projects = companies.models.Company.objects.active().filter(
            pk__in=projects.models.Project.objects.active().values('company__pk'))
        return _companies & has_projects

    def __str__(self):  # pragma: no cover
        return "{0} {1}".format(self.first_name, self.last_name)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from django.contrib.auth.views import login, logout_then_login
from .views import EditProfile, PeopleView


urlpatterns = patterns('',
   url(regex=r'^$',
       view=PeopleView.as_view(),
       name='accounts',
   ),

   url(
       regex=r'^login$',
       view=login,
       kwargs={'template_name': 'login.html'},
       name='login'
   ),
   url(
       regex=r'^logout$',
       view=logout_then_login,
       kwargs={'login_url': '/login'},
       name='logout'
   ),
   #    url(r'^create_account$', CreateAccount.as_view(), name='create_account'),
   url(
       regex=r'^edit_profile/(?P<pk>\d+)$',
       view=EditProfile.as_view(),
       name='edit_profile'
   ),
)

########NEW FILE########
__FILENAME__ = views
from django.contrib import messages
from django.contrib.auth import get_user
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from .forms import PersonForm, CreatePersonForm, permission_forms, DeletedCompanyForm
from .mixins import LoginRequiredMixin
from .models import Person
from companies.forms import CreateCompanyForm
from companies.models import Company
from projects.models import Project


class EditProfile(LoginRequiredMixin, TemplateView):
    template_name = 'profile.html'

    def get_context_data(self, **kwargs):
        context = {
            'form': self.form,
            'person': self.person,
        }
        if self.request.user.is_admin:
            context['permission_forms'] = self.permission_forms
        return context

    def dispatch(self, request, pk, *args, **kwargs):
        self.person = get_object_or_404(Person, pk=pk)
        if self.person != request.user and not request.user.is_admin:
            messages.error(request, 'You do not have permission to edit this persons account')
            return redirect(reverse('home'))
        self.form = PersonForm(request.POST or None, instance=self.person)
        if request.user.is_admin:
            self.permission_forms = permission_forms(request, self.person)
        return super(EditProfile, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if 'toggle-admin' in request.POST and request.user.is_admin:
            self.person.is_admin = not self.person.is_admin
            self.person.save()
            if self.person.is_admin:
                messages.success(request, 'This user has been granted administrator privileges')
            else:
                messages.success(request, 'This user has had it\'s administrator privileges revoked')
            return redirect(reverse('edit_profile', args=[self.person.pk]))

        if 'delete' in request.POST and request.user.is_admin:
            self.person.set_active(False)
            messages.success(request, 'The person has been removed')
            return redirect(reverse('accounts'))

        if 'save-permissions' in request.POST:
            for form in self.permission_forms:
                if form.is_valid():
                    form.save()
            messages.success(request, 'The permissions have been updated')
            return redirect(reverse('edit_profile', args=[self.person.pk]))

        if self.form.is_valid():
            self.form.save()
            messages.success(request, 'Profile data has been saved')
            return redirect(reverse('edit_profile', args=[self.person.pk]))
        return self.render_to_response(self.get_context_data())


class PeopleView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts.html'

    def get_context_data(self, **kwargs):
        if self.request.user.is_admin:
            return {
                'companies': self.companies,
                'company_form': self.company_form,
                'person_form': self.person_form,
                'undelete_form': self.undelete_form,
            }
        return {
            'companies': self.companies
        }

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = get_user(request)
        if self.user.is_admin:
            self.companies = Company.objects.active()
            self.company_form = CreateCompanyForm(request.POST if 'create_company' in request.POST else None)
            self.person_form = CreatePersonForm(request.POST if 'create_person' in request.POST else None)
            self.undelete_form = DeletedCompanyForm(request.POST if 'undelete' in request.POST else None)
        else:
            self.companies = Company.objects.active().filter(
                pk__in=Project.clients.through.objects.filter(person__pk=self.user.pk).values(
                    'project__company__pk'))
            self.companies = self.companies | Company.objects.active().filter(pk=self.user.company.pk)
        return super(PeopleView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not self.user.is_admin:
            messages.error(request, 'You do not have permission to create data')
            return redirect(reverse('accounts'))

        if 'create_company' in request.POST and self.company_form.is_valid():
            company = self.company_form.save()
            messages.success(request, 'The company has been created')
            return redirect(reverse('company', args=[company.pk]))

        if 'create_person' in request.POST and self.person_form.is_valid():
            self.person_form.save()
            messages.success(request, 'The person has been created')
            return redirect(reverse('accounts'))

        if 'undelete' in request.POST and self.undelete_form.is_valid():
            company = self.undelete_form.save()
            messages.success(request, 'The company %s has been un-deleted' % company.name)
            return redirect(reverse('accounts'))
        return self.render_to_response(self.get_context_data())

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.core.exceptions import ValidationError
import requests


class BasecampAuthorizationForm(forms.Form):
    name = forms.CharField(label="Basecamp Company Name", required=True)
    username = forms.CharField(required=True)
    password = forms.CharField(widget=forms.PasswordInput(), required=True)

    def clean(self):
        cleaned_data = super(BasecampAuthorizationForm, self).clean()
        url = 'https://%s.basecamphq.com' % cleaned_data['name']
        r = requests.get('%s/account.xml' % url, auth=(cleaned_data['username'], cleaned_data['password']))
        if r.status_code != 200:
            raise ValidationError("Basecamp failed to authorize your account information. Please check that the "
                                  "information you provided above is correct. The status code returned was %i"
                                  % r.status_code)
        return self.cleaned_data

########NEW FILE########
__FILENAME__ = models
from django.db import models
from accounts.models import Person
from companies.models import Company
from documents.models import DocumentVersion
from projects.models import Project


class BCCompany(Company):
    bc_id = models.IntegerField()


class BCDocumentVersion(DocumentVersion):
    def __init__(self, *args, **kwargs):
        super(BCDocumentVersion, self).__init__(*args, **kwargs)
        self.file.field.null = True
        for field in self._meta.local_fields:
            if field.name == 'created':
                field.auto_add_now = False
            elif field.name == 'changed':
                field.auto_now_add = False

    bc_latest = models.BooleanField()
    bc_size = models.IntegerField()
    bc_collection = models.IntegerField()
    bc_id = models.IntegerField()
    bc_category = models.IntegerField(null=True, blank=True)
    bc_url = models.URLField(max_length=400)
    bc_project = models.ForeignKey('BCProject')


class BCPerson(Person):
    bc_id = models.IntegerField(null=True, blank=True)


class BCProject(Project):
    bc_id = models.IntegerField()

########NEW FILE########
__FILENAME__ = serializers
from bc_import.models import BCCompany
from rest_framework import serializers


class BasecampCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = BCCompany

    def restore_object(self, attrs, instance=None):
        if instance:
            instance.bc_id = attrs.get('id', instance.bc_id)
            instance.name = attrs.get('name', instance.name)
            instance.address = attrs.get('address-one', instance.address)
            instance.address1 = attrs.get('address-two', instance.address1)
            instance.city = attrs.get('city', instance.city)
            instance.state = attrs.get('state', instance.state)
            instance.web = attrs.get('web-address', instance.web)
            instance.fax = attrs.get('phone-number-fax', instance.fax)
            instance.office = attrs.get('phone-number-office', instance.office)
            return instance

########NEW FILE########
__FILENAME__ = tasks
from datetime import datetime
from defusedxml import ElementTree
from django.conf import settings
from django.utils import timezone
from djcelery import celery
from .models import BCCompany, BCPerson, BCProject, BCDocumentVersion
from documents.models import Document
import requests
import urllib


BASE_URL = 'basecamphq.com'


@celery.task
def import_groups(service, username, password):
    r = requests.get('https://%s.%s/companies.xml' % (service, BASE_URL), auth=(username, password))
    if r.status_code != 200:
        return r.status_code
    xml = ElementTree.fromstring(r.text)
    count = 0; created = 0
    for company in xml.findall('company'):
        bc_id = company.find('id').text

        try:
            bc_company = BCCompany.objects.get(bc_id=bc_id)
        except BCCompany.DoesNotExist:
            bc_company = BCCompany(bc_id=bc_id)
            created += 1
        bc_company.name = company.find('name').text
        bc_company.address = company.find('address-one').text
        bc_company.address1 = company.find('address-two').text
        bc_company.country = 'US' # Not Correct
        bc_company.city = company.find('city').text
        bc_company.state = 'HI' # Not Correct #company.find('state').text
        bc_company.locale = company.find('locale').text
        bc_company.fax = company.find('phone-number-fax').text
        bc_company.phone = company.find('phone-number-office').text
        bc_company.web = company.find('web-address').text
        bc_company.timezone = settings.TIME_ZONE
        bc_company.save()
        count += 1
    import_users.delay(service, username, password)
    return count, created


@celery.task
def import_users(service, username, password):
    r = requests.get('https://%s.%s/people.xml' % (service, BASE_URL), auth=(username, password))
    if r.status_code != 200:
        return r.status_code
    xml = ElementTree.fromstring(r.text)
    count = 0; created = 0
    for person in xml.findall('person'):
        bc_id = person.find('id').text
        try:
            p = BCPerson.objects.get(bc_id=bc_id)
        except BCPerson.DoesNotExist:
            p = BCPerson(bc_id=bc_id)
            created += 1
        p.date_joined = datetime.strptime(person.find('created-at').text, '%Y-%m-%dT%H:%M:%SZ')
        p.is_active = person.find('deleted').text
        p.access_new_projects = True if person.find('has-access-to-new-projects').text == 'true' else False
        p.im_handle = person.find('im-handle').text
        p.im_service = person.find('im-service').text
        p.fax = person.find('phone-number-fax').text
        p.home = person.find('phone-number-home').text
        p.mobile = person.find('phone-number-mobile').text
        p.office = person.find('phone-number-office').text
        p.ext = person.find('phone-number-office-ext').text
        p.title = person.find('title').text
        p.last_updated = datetime.strptime(person.find('updated-at').text, '%Y-%m-%dT%H:%M:%SZ').replace(
            tzinfo=timezone.utc)
        p.first_name = person.find('first-name').text
        p.last_name = person.find('last-name').text
        p.company = BCCompany.objects.get(bc_id=person.find('company-id').text)
        p.timezone = person.find('time-zone-name').text
        p.username = person.find('user-name').text
        p.is_superuser = True if person.find('administrator').text == 'true' else False
        p.email = person.find('email-address').text
        p.avatar_url = person.find('avatar-url').text
        if p.username is None:
            p.username = p.email
            p.is_active = False
        p.save()
        count += 1
    import_projects.delay(service, username, password)
    return count, created


@celery.task
def import_projects(service, username, password):
    r = requests.get('https://%s.%s/projects.xml' % (service, BASE_URL), auth=(username, password))
    if r.status_code != 200:
        return r.status_code
    xml = ElementTree.fromstring(r.text)
    count = 0; created = 0
    for project in xml.findall('project'):
        bc_id = project.find('id').text
        try:
            p = BCProject.objects.get(bc_id=bc_id)
        except BCProject.DoesNotExist:
            p = BCProject(bc_id=bc_id)
            created += 1
        p.name = project.find('name').text
        if project.find('last-changed-on').text is not None:
            p.changed = datetime.strptime(project.find('last-changed-on').text, '%Y-%m-%dT%H:%M:%SZ')
        p.created = datetime.strptime(project.find('created-on').text, '%Y-%m-%d')
        p.is_active = project.find('status').text
        p.company = BCCompany.objects.get(bc_id=project.find('company').find('id').text)
        p.save()
        count += 1
    import_documents.delay(service, username, password)
    return count, created


@celery.task
def import_documents(service, username, password):
    count = 0; created = 0
    for project in BCProject.objects.all():
        n = 0
        while True:
            r = requests.get('https://%s.%s/projects/%s/attachments.xml?n=%i' % (service, BASE_URL, project.bc_id, n),
                             auth=(username, password))
            if r.status_code != 200:
                return str(r.status_code) + 'https://%s.%s/projects/%s/attachments.xml?n=%i' % (service, BASE_URL, project.bc_id, n)
            xml = ElementTree.fromstring(r.text)

            documents = xml.findall('attachment')
            for document in documents:
                bc_id = document.find('id').text
                try:
                    d = BCDocumentVersion.objects.get(bc_id=bc_id)
                except BCDocumentVersion.DoesNotExist:
                    d = BCDocumentVersion(bc_id=bc_id)
                    created += 1
                d.created = datetime.strptime(document.find('created-on').text, '%Y-%m-%dT%H:%M:%SZ')
                d.bc_size = document.find('byte-size').text
                d.bc_category = document.find('category-id').text
                d.bc_collection = document.find('collection').text
                d.bc_latest = True if document.find('current').text == 'true' else False
                d.description = document.find('description').text
                d.name = document.find('name').text
                try:
                    d.person = BCPerson.objects.get(bc_id=document.find('person-id').text)
                except BCPerson.DoesNotExist:
                    d.person = None
                d.bc_project = BCProject.objects.get(bc_id=document.find('project-id').text)
                d.bc_url = document.find('download-url').text
                d.save(save_document=False)
                count += 1
            if len(documents) >= 100:
                n += 100
            else:
                break
    create_document_from_document_versions.delay()
    return count, created


@celery.task
def create_document_from_document_versions():
    created = 0
    for collection in BCDocumentVersion.objects.all().order_by('bc_collection').distinct('bc_collection').values_list('bc_collection'):
        documents = BCDocumentVersion.objects.filter(bc_collection=collection).values_list('document')
        if documents.count() > 0:
            document = Document.objects.get(pk=documents[0])
            latest = document.get_latest()
        else:
            document = Document.objects.create(name=version.name, project=version.bc_project, date=version.created)
            created += 1
            latest = None

        for version in BCDocumentVersion.objects.filter(bc_collection=collection):
            if latest is None or latest.created < version.created:
                document.date = version.created
                document.mime = version.mime
                document.save()

            if version.document is None:
                version.document = document
                version.save()
    return created


@celery.task
def download_document(document, username, password):
    r = requests.get(document.bc_url, auth=(username, password))
    if r.status_code != 200:
        return r.status_code
    file_name = urllib.unquote(r.url.split('/')[-1:][0])
    file_path = settings.DOCUMENT_ROOT + str(document.uuid)
    f = open(file_path, 'w')
    f.write(r.content)
    f.close()
    document.file = file_path
    document.name = file_name
    document.mime = r.headers['content-type'].split(';')[0]
    document.save()
    return r.status_code

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from .views import BasecampAuthorize, BasecampImport, BasecampUnauthorize, BasecampDownloadDocument

urlpatterns = patterns('',
   url(
       regex=r'^authorize$',
       view=BasecampAuthorize.as_view(),
       name='basecamp_authorize'
   ),
   url(
       regex=r'^unauthorize$',
       view=BasecampUnauthorize.as_view(),
       name='basecamp_unauthorize'
   ),
   url(
       regex=r'^$',
       view=BasecampImport.as_view(),
       name='basecamp_import'
   ),
   url(
       regex=r'^(?P<pk>[a-fA-F0-9]{32})/download$',
       view=BasecampDownloadDocument.as_view(),
       name='basecamp_download_document'
   ),
)

########NEW FILE########
__FILENAME__ = views
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, HttpResponse, get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, View
from .models import BCDocumentVersion
from .tasks import import_groups, download_document
from .forms import BasecampAuthorizationForm
from accounts.mixins import LoginRequiredMixin


class BasecampAuthorize(LoginRequiredMixin, TemplateView):
    template_name = 'basecamp_authorization.html'

    def get_context_data(self, **kwargs):
        return {
            'form': self.form,
        }

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.form = BasecampAuthorizationForm(request.POST or None)
        return super(BasecampAuthorize, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if self.form.is_valid():
            bc_auth =  signing.dumps({
                'bc_name': self.form.cleaned_data['name'],
                'username': self.form.cleaned_data['username'],
                'password': self.form.cleaned_data['password'],
            })
            request.session['bc_auth'] = bc_auth
            messages.success(request, 'Your account has been authorized')
            return redirect(reverse('basecamp_import'))
        return self.render_to_response(self.get_context_data())


class BasecampUnauthorize(View):
    def get(self, request, *args, **kwargs):
        if 'bc_auth' in request.session:
            del request.session['bc_auth']
        messages.success(request, 'Your account has been unauthorized')
        return redirect(reverse('basecamp_authorize'))


class BasecampImport(TemplateView):
    template_name = 'basecamp_import.html'

    def get_context_data(self, **kwargs):
        return {
            'name': self.bc_auth['bc_name'],
        }

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if 'bc_auth' not in request.session:
            messages.error(request, 'You have not authorized any basecamp projects')
            return redirect(reverse('basecamp_authorize'))
        self.bc_auth = signing.loads(request.session.get('bc_auth'))
        return super(BasecampImport, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if 'update-information' in request.POST:
            import_groups.delay(self.bc_auth['bc_name'], self.bc_auth['username'], self.bc_auth['password'])

        if 'update-documents' in request.POST:
            documents = BCDocumentVersion.objects.filter(file='')
            for document in documents:
                download_document.delay(document, self.bc_auth['username'], self.bc_auth['password'])

        return self.render_to_response(self.get_context_data())


class BasecampDownloadDocument(View):
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if 'bc_auth' not in request.session:
            messages.error(request, 'You have not authorized any basecamp projects')
            return redirect(reverse('basecamp_authorize'))
        self.bc_auth = signing.loads(request.session.get('bc_auth'))
        return super(BasecampDownloadDocument, self).dispatch(request, *args, **kwargs)

    def get(self, request, pk, *args, **kwargs):
        document = get_object_or_404(BCDocumentVersion, pk=pk)
        task = download_document.delay(document, self.bc_auth['username'], self.bc_auth['password'])
        return HttpResponse("{'worked': 'true'}", content_type='application/json')

########NEW FILE########
__FILENAME__ = forms
from django import forms
from .models import Company
from accounts.models import Person


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        exclude = ('is_active', 'removed')


class CreateCompanyForm(CompanyForm):
    class Meta:
        model = Company
        fields = ('name',)
        widgets = {
            'name': forms.TextInput(attrs={'class': 'span3'})
        }


class DeletedPeopleForm(forms.Form):
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company')
        super(DeletedPeopleForm, self).__init__(*args, **kwargs)
        self.fields['person'] = forms.ModelChoiceField(queryset=Person.objects.filter(company=company, is_active=False),
                                                       widget=forms.Select(attrs={'class': 'span3'}))

    def save(self):
        person = self.cleaned_data['person']
        person.set_active(True)
        return person

########NEW FILE########
__FILENAME__ = models
import datetime
from django.conf import settings
from django_localflavor_us.models import PhoneNumberField
from django.db import models
from django_countries.fields import CountryField
from django_localflavor_us.models import USStateField
from timezone_field import TimeZoneField
from accounts.models import Person
from managers import ActiveManager
from projects.models import Project


class CompaniesWithProjectManager(models.Manager):
    def get_query_set(self):
        return super(CompaniesWithProjectManager, self).get_query_set().filter(is_active=True,
                                                                               pk__in=Project.objects.active().values(
                                                                                   'company__pk'))


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    address1 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    state = USStateField(null=True, blank=True)
    country = CountryField(default='US')
    fax = PhoneNumberField(null=True, blank=True)
    phone = PhoneNumberField(null=True, blank=True)
    locale = models.CharField(max_length=2, null=True, blank=True, default='en')
    removed = models.DateField(null=True)
    timezone = TimeZoneField(default=settings.TIME_ZONE)
    website = models.URLField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    objects = ActiveManager()
    with_projects = CompaniesWithProjectManager()

    class Meta:
        ordering = ['name']
        db_table = 'kala_companies'

    def set_active(self, active):
        self.is_active = active
        for person in Person.objects.filter(company=self):
            person.set_active(active)

        for project in Project.objects.filter(company=self):
            project.set_active(active)

        if not self.is_active:
            self.removed = datetime.date.today()
        self.save()

    def get_project_list(self, person=None):
    #        assert type(person) is People, 'The user parameter must be of type People'
        if not person or person.is_admin:
            return Project.objects.active().filter(company=self)
        else:
            return Project.objects.active().filter(company=self,
                                                   pk__in=Project.clients.through.objects.filter(person=person).values(
                                                       'project__pk'))

    def get_people_list(self):
        return Person.objects.filter(company=self)  # Todo: only show people that are active

    def add_person_to_projects(self, person):
        assert type(person) is Person, 'The person parameter must be of type People'
        for project in Project.active.filter(company=self):
            project.clients.add(person)

    def __str__(self):
        return self.name

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from .views import CompanyView

urlpatterns = patterns('',
                       url(
                           regex=r'^(?P<pk>\d+)$',
                           view=CompanyView.as_view(),
                           name='company',
                       ),
)

########NEW FILE########
__FILENAME__ = views
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView
from .forms import CompanyForm, DeletedPeopleForm
from .models import Company
from accounts.mixins import AdminRequiredMixin


class CompanyView(AdminRequiredMixin, TemplateView):
    template_name = 'company.html'

    def get_context_data(self, **kwargs):
        return {
            'company': self.company,
            'form': self.form,
            'undelete_form': self.undelete_form,
            }

    def dispatch(self, request, pk, *args, **kwargs):
        self.company = get_object_or_404(Company.objects.active(), pk=pk)
        self.form = CompanyForm(request.POST or None, instance=self.company)
        self.undelete_form = DeletedPeopleForm(request.POST or None, company=self.company)
        return super(CompanyView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if 'delete' in request.POST:
            self.company.set_active(False)
            messages.success(request, 'The company %s has been deleted' % self.company)
            return redirect(reverse('accounts'))

        if 'undelete' in request.POST and self.undelete_form.is_valid():
            person = self.undelete_form.save()
            messages.success(request, 'The person %s has been un-deleted' % person)
            return redirect(reverse('company', args=[self.company.pk]))

        if 'update' in request.POST and self.form.is_valid():
            self.form.save()
            messages.success(request, 'The company information has been updated')
            return redirect(reverse('company', args=[self.company.pk]))

        return self.render_to_response(self.get_context_data())

########NEW FILE########
__FILENAME__ = databases
from django.core.exceptions import ImproperlyConfigured
from kala.settings.functions import get_env_variable


DATABASE_USER = get_env_variable('KALA_DATABASE_USER')
DATABASE_PASSWORD = get_env_variable('KALA_DATABASE_PASSWORD')

try:
    DATABASE_ENGINE = get_env_variable('KALA_DATABASE_ENGINE')
except ImproperlyConfigured:
    DATABASE_ENGINE = 'django.db.backends.postgresql_psycopg2'

try:
    DATABASE_NAME = get_env_variable('KALA_DATABASE_NAME')
except ImproperlyConfigured:
    DATABASE_NAME = 'ndptc'

try:
    DATABASE_PORT = get_env_variable('KALA_DATABASE_PORT')
except ImproperlyConfigured:
    DATABASE_PORT = '5432'

try:
    DATABASE_HOST = get_env_variable('KALA_DATABASE_HOST')
except ImproperlyConfigured:
    DATABASE_HOST = 'localhost'


DATABASES = {
    'default': {
        'ENGINE': DATABASE_ENGINE,
        'NAME': DATABASE_NAME,
        'USER': DATABASE_USER,
        'PASSWORD': DATABASE_PASSWORD,
        'HOST': DATABASE_HOST,
        'PORT': DATABASE_PORT,
    }
}

########NEW FILE########
__FILENAME__ = functions
from django.core.exceptions import ImproperlyConfigured
import os


def get_env_variable(variable):
    try:
        return os.environ[variable]
    except KeyError:
        raise ImproperlyConfigured("The environment variable {0} is not set.".format(variable))


########NEW FILE########
__FILENAME__ = installed_apps
from kala.settings import get_env_variable


DEPLOYMENT_ENVIRONMENT = get_env_variable('KALA_DEPLOYMENT_ENVIRONMENT')

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',

    'accounts',
    'companies',
    'documents',
    'kala',
    'projects',
    'bc_import',
)


if DEPLOYMENT_ENVIRONMENT is 'development':
    INSTALLED_APPS += ('debug_toolbar',)

########NEW FILE########
__FILENAME__ = kala_tags
from django.utils.functional import SimpleLazyObject
from django.template import Library
from accounts.models import Person
from companies.models import Company

register = Library()


@register.filter
def pretty_user(user):
    if user is None:
        return 'Lost in translation'
    else:
        return '%s %s' % (user.first_name, user.last_name)


@register.filter
def users_projects(company, user):
    return company.get_project_list(user)


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from .views import Home, LicenseView, UserDocumentationView

urlpatterns = patterns('',
   url(
       regex=r'^$',
       view=Home.as_view(),
       name='home'
   ),

   url(
       r'^companies/',
       include('companies.urls'),
   ),

   url(
       r'^documents/',
       include('documents.urls'),
   ),

   url(
       r'^accounts/',
       include('accounts.urls'),
   ),

   url(
       r'^projects/',
       include('projects.urls'),
   ),

   url(
       r'^import/',
       include('bc_import.urls'),
   ),

    url(
        regex=r'^license$',
        view=LicenseView.as_view(),
        name='license',
    ),
    url(
        regex=r'^user_documentation$',
        view=UserDocumentationView.as_view(),
        name='user_documentation',
    ),
)

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth import get_user
from django.views.generic import TemplateView
from accounts.mixins import LoginRequiredMixin
from documents.models import Document, DocumentVersion


class Home(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        return {
            'companies': self.request.user.get_companies(),
            'documents': Document.objects.active().filter(
                pk__in=DocumentVersion.objects.filter(person=get_user(self.request)).values('document__pk'))[:10],
        }


class UserDocumentationView(LoginRequiredMixin, TemplateView):
    template_name = 'user_documentation.html'


class LicenseView(TemplateView, LoginRequiredMixin):
    template_name = 'license.html'

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for kala project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "kala.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kala.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kala.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = managers
from django.db import models
from django.db.models.query import QuerySet


class ActiveMixin(object):
    def active(self):
        return self.filter(is_active=True)

    def deleted(self):
        return self.filter(is_active=False)


class ActiveQuerySet(QuerySet, ActiveMixin):
    pass


class ActiveManager(models.Manager, ActiveMixin):
    def get_query_set(self):
        return ActiveQuerySet(self.model, using=self._db)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from .models import Project
from companies.models import Company
from documents.defs import get_categories_for_mimes
from documents.models import Document


class CategoryForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project')
        super(CategoryForm, self).__init__(*args, **kwargs)

        self.fields['category'] = forms.ChoiceField(choices=get_categories_for_mimes(
            Document.objects.active().filter(project=self.project).distinct('mime').order_by('mime').values_list(
                'mime')), widget=forms.Select(attrs={'class': 'span3'}))


class CompanyForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project')
        super(CompanyForm, self).__init__(*args, **kwargs)

        self.fields['company'] = forms.ModelChoiceField(queryset=Company.objects.active(),
                                                        initial=self.project.company,
                                                        widget=forms.Select(attrs={'class': 'span3'}))

    def save(self):
        self.project.company = self.cleaned_data['company']
        self.project.save()
        return self.project


class DeleteProjectsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(DeleteProjectsForm, self).__init__(*args, **kwargs)

        choices = []
        for company in Company.objects.active().filter(pk__in=Project.objects.deleted().values('company')):
            projects = [(project.pk, project.name) for project in Project.objects.deleted().filter(company=company)]
            choices.append((company.name, projects))

        self.fields['project'] = forms.ChoiceField(choices=choices, widget=forms.Select(attrs={'class': 'span3'}))

    def save(self):
        project = Project.objects.deleted().get(pk=self.cleaned_data['project'])
        project.set_active(True)
        return project


def permission_forms(request, project):
    forms = [PermissionsForm(request.POST or None, project=project, company=project.company)]
    for company in Company.objects.active().exclude(pk=project.company.pk):
        forms.append(PermissionsForm(request.POST or None, project=project, company=company))
    return forms


class PermissionsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project')
        self.company = kwargs.pop('company')
        self.people = self.company.get_people_list()
        super(PermissionsForm, self).__init__(*args, **kwargs)
        self.fields[self.company] = forms.BooleanField(required=False, label='Select/Unselect All',
                                                       widget=forms.CheckboxInput(
                                                           attrs={'class': 'company_checkbox',
                                                                  'pk_id': self.company.pk,
                                                           }))

        for person in self.people:
            self.fields['%i' % person.pk] = forms.BooleanField(required=False, label=str(person),
                                                               initial=True if self.project.clients.filter(
                                                                   pk=person.pk).exists() else False,
                                                               widget=forms.CheckboxInput(
                                                                   attrs={'pk': self.company.pk}))

    def save(self):
        for person in self.people:
            is_selected = self.cleaned_data['%i' % person.pk]
            if is_selected:
                if not self.project.clients.filter(pk=person.pk).exists():
                    self.project.clients.add(person)
            else:
                if self.project.clients.filter(pk=person.pk).exists():
                    self.project.clients.remove(person)


class ProjectForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company')
        self.is_admin = kwargs.pop('is_admin')
        super(ProjectForm, self).__init__(*args, **kwargs)
        if self.is_admin:
            self.fields['company'] = forms.ModelChoiceField(queryset=Company.objects.active(), initial=self.company,
                                                            widget=forms.Select(attrs={'class': 'span3'}))

    class Meta:
        model = Project
        fields = ('name', 'company')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'span3'})
        }

    def save(self, commit=True):
        if self.is_admin:
            self.instance.owner = self.cleaned_data['company']
        else:
            self.instance.owner = self.company
        project = super(ProjectForm, self).save(commit)
        # Add all of the companies accounts to the project.
        #[self.instance.clients.add(person) for person in Person.active.filter(company=self.company)]
        return project


class SortForm(forms.Form):
    search = forms.ChoiceField(choices=(('DATE', 'Sort by Date'), ('AZ', 'Sort Alphabetically')),
                               widget=forms.RadioSelect,
                               initial='DATE')




########NEW FILE########
__FILENAME__ = models
import datetime
from django.conf import settings
from django.db import models
from accounts.models import Person
from documents.models import Document
from managers import ActiveManager


class Project(models.Model):
    name = models.CharField(max_length=255)
    company = models.ForeignKey('companies.Company')
    clients = models.ManyToManyField(settings.AUTH_USER_MODEL, null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    removed = models.DateField(null=True)
    changed = models.DateTimeField(auto_now=True, auto_now_add=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    objects = ActiveManager()

    class Meta:
        ordering = ('name',)
        db_table = 'kala_projects'

    def set_active(self, active):
        assert type(active) is bool, 'The active parameter must be of type bool.'
        self.is_active = active
        for document in Document.objects.filter(project=self):
            document.set_active(active)
        if not self.is_active:
            self.removed = datetime.date.today()
        self.save()

    def add_client(self, client):
        assert type(client) is Person, 'The client parameter must be of type People.' # Solient Green

        # Check if the client is in the clients list, add if not.
        try:
            self.clients.get(client)
        except Person.DoesNotExist:
            self.clients.add(client)

    def remove_client(self, client):
        assert type(client) is Person, 'The client parameter must be of type People.'
        self.clients.remove(client)

    def __str__(self):
        return self.name

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from .views import ProjectsView, ProjectView, ProjectPermissions

urlpatterns = patterns('',
                       url(
                           regex=r'^$',
                           view=ProjectsView.as_view(),
                           name='projects'
                       ),
                       url(
                           regex=r'^(?P<pk>\d+)$',
                           view=ProjectView.as_view(),
                           name='project'
                       ),
                       url(
                           regex=r'^(?P<pk>\d+)/permissions$',
                           view=ProjectPermissions.as_view(),
                           name='permissions'),
)

########NEW FILE########
__FILENAME__ = views
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import TemplateView
from .models import Project
from .forms import CategoryForm, ProjectForm, SortForm, permission_forms, CompanyForm, DeleteProjectsForm
from accounts.mixins import LoginRequiredMixin, AdminRequiredMixin
from accounts.models import Person
from documents.defs import get_mimes_for_category
from documents.forms import DocumentForm
from documents.models import Document


class ProjectsView(LoginRequiredMixin, TemplateView):
    template_name = 'projects.html'

    def get_context_data(self, **kwargs):
        context = {
            'companies': self.request.user.get_companies(),
            'form': self.form,
            }
        if self.request.user.is_admin:
            context['deleted_form'] = self.deleted_form

        return context

    def dispatch(self, request, *args, **kwargs):
        self.form = ProjectForm(request.POST or None, company=request.user.company,
                                is_admin=self.request.user.is_admin)
        if request.user.is_admin:
            self.deleted_form = DeleteProjectsForm(request.POST or None)

        return super(ProjectsView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not request.user.is_admin:
            messages.error(request, 'You do not have permission to create a new project')
            return redirect(reverse('projects'))

        if 'create' in request.POST and self.form.is_valid():
            project = self.form.save()
            # Add everyone in the organization to the project.
            #[project.clients.add(person) for person in project.company.get_people_list()]
            messages.success(request, 'The project has been created')
            return redirect(reverse('project', args=[project.pk]))

        if 'undelete' in request.POST and self.deleted_form.is_valid():
            project = self.deleted_form.save()
            messages.success(request, 'The project %s has been un-deleted' % project.name)
            return redirect(reverse('projects'))

        return self.render_to_response(self.get_context_data())


class ProjectView(LoginRequiredMixin, TemplateView):
    template_name = 'project.html'

    def get_context_data(self, **kwargs):
        documents = Document.objects.active().filter(project=self.project)
        if hasattr(self, 'sort_order'):
            if self.sort_order == 'AZ':
                documents = documents.order_by('name')
        if hasattr(self, 'category'):
            mimes = get_mimes_for_category(self.category)
            documents = documents.filter(mime__in=mimes)
        return {
            'categories_form': self.categories_form,
            'company_form': self.company_form,
            'documents': documents,
            'form': self.form,
            'project': self.project,
            'sort_form': self.sort_form,
            }

    def dispatch(self, request, pk, *args, **kwargs):
        self.project = get_object_or_404(Project.objects.active(), pk=pk)
        person = Person.objects.get(pk=self.request.user.pk)
        self.form = DocumentForm(request.POST or None, request.FILES or None, person=person,
                                 project=self.project)
        self.categories_form = CategoryForm(request.GET or None, project=self.project)
        self.company_form = CompanyForm(request.POST or None, project=self.project)
        self.sort_form = SortForm(request.GET or None)
        if 'search' in request.GET:
            self.sort_order = request.GET.get('search')
        if 'category' in request.GET and request.GET.get('category'):
            self.category = request.GET.get('category')
        return super(ProjectView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if 'delete' in request.POST and request.user.is_admin:
            self.project.set_active(False)
            messages.success(request, 'The project has been deleted')
            return redirect(reverse('projects'))

        if 'move' in request.POST and request.user.is_admin and self.company_form.is_valid():
            self.company_form.save()
            return redirect(reverse('project', args=[self.project.pk]))

        if 'upload' in request.POST and self.form.is_valid():
            self.form.save()
            messages.success(request, 'The document has been created')
            return redirect(reverse('project', args=[self.project.pk]))
        return self.render_to_response(self.get_context_data())


class ProjectPermissions(AdminRequiredMixin, TemplateView):
    template_name = 'permissions.html'

    def get_context_data(self, **kwargs):
        return {
            'forms': self.forms,
            'project': self.project,
            }

    def dispatch(self, request, pk, *args, **kwargs):
        self.project = get_object_or_404(Project.objects.active(), pk=pk)
        self.forms = permission_forms(request, self.project)
        return super(ProjectPermissions, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        all_valid = True
        for form in self.forms:
            if form.is_valid():
                form.save()
            else:
                all_valid = False
        if all_valid:
            messages.success(request, 'The permissions have been updated.')
            return redirect(reverse('permissions', args=[self.project.pk]))
        return self.render_to_response(self.get_context_data())

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import django
import six
import kala
import tests
import sys

sys.path.insert(0, os.path.dirname(kala.__file__))
print(sys.path)
urlpatterns = []

TEMPLATE_DEBUG = True
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = tempfile.mkdtemp(prefix='django_')
DATA_ROOT = os.path.dirname(tests.__file__) + '/'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'test',
        'USER': 'test',
        'PASSWORD': 'test',
        'HOST': 'localhost'
    },
}


INSTALLED_APPS = [
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.humanize',
        'django.contrib.staticfiles',

        'kala.kala',
        'kala.accounts',
        'kala.bc_import',
        'kala.companies',
        'kala.documents',
        'kala.projects',

        'tests.accounts',
        'tests.bc_import',
        'tests.companies',
        'tests.documents',
        'tests.projects',

        'django_nose',
]


def runtests(verbosity, interactive, failfast, test_labels):
    from django.conf import settings
    settings.configure(
        INSTALLED_APPS=INSTALLED_APPS,
        DATABASES=DATABASES,
        AUTH_USER_MODEL='accounts.Person',
        USE_TZ=True,
        TEST_RUNNER='django_nose.NoseTestSuiteRunner',
        TEMPLATE_DEBUG=TEMPLATE_DEBUG,
        STATIC_ROOT=os.path.join(TEMP_DIR, 'static'),
        DOCUMENT_ROOT=os.path.join(TEMP_DIR, 'static'),
        PASSWORD_HASHERS=(
            'django.contrib.auth.hashers.MD5PasswordHasher',
        ),
        SECRET_KEY="kala_tests_secret_key",
        NOSE_ARGS=[
            '--with-coverage',
            '--cover-package=kala.kala,kala.accounts,kala.bc_import,kala.companies,kala.documents,kala.projects'
        ],
        ROOT_URLCONF='kala.kala.urls',
        LOGIN_REDIRECT_URL = '/',
    )

    # Run the test suite, including the extra validation tests.
    from django.test.utils import get_runner
    TestRunner = get_runner(settings)
    print("Testing against kala installed in '{0}' against django version {1}".format(os.path.dirname(kala.__file__),
                                                                                     django.VERSION))

    test_runner = TestRunner(verbosity=verbosity, interactive=interactive, failfast=failfast)
    failures = test_runner.run_tests(test_labels)
    return failures


def teardown():
    try:
        shutil.rmtree(six.text_type(TEMP_DIR))
    except OSError:
        print('Failed to remove temp directory: %s' % TEMP_DIR)


if __name__ == "__main__":
    from optparse import OptionParser
    usage = "%prog [options] [module module module ...]"
    parser = OptionParser(usage=usage)
    parser.add_option(
        '-v', '--verbosity', action='store', dest='verbosity', default='1',
        type='choice', choices=['0', '1', '2', '3'],
        help='Verbosity level; 0=minimal output, 1=normal output, 2=all '
             'output')
    parser.add_option(
        '--noinput', action='store_false', dest='interactive', default=True,
        help='Tells Django to NOT prompt the user for input of any kind.')
    parser.add_option(
        '--failfast', action='store_true', dest='failfast', default=False,
        help='Tells Django to stop running the test suite after first failed '
             'test.')
    options, args = parser.parse_args()

    os.environ['DJANGO_SETTINGS_MODULE'] = 'runtests'
    options.settings = os.environ['DJANGO_SETTINGS_MODULE']

    runtests(int(options.verbosity), options.interactive, options.failfast, args)

########NEW FILE########
__FILENAME__ = factories
from kala.accounts.models import Person
from ..companies.factories import CompanyFactory
import factory


class PersonFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = Person
    username = factory.Sequence(lambda n: 'user{0}'.format(n))
    company = factory.SubFactory(CompanyFactory)
    email = factory.LazyAttribute(lambda a: 'user.{0}@example.com'.format(a.username).lower())
    first_name = 'test'
    last_name = 'user'
    access_new_projects = True

########NEW FILE########
__FILENAME__ = unit_tests
from django_nose import FastFixtureTestCase
from .factories import PersonFactory
from ..projects.factories import ProjectFactory
import datetime


class PersonTests(FastFixtureTestCase):
    def setUp(self):
        self.person = PersonFactory(username='test_user')

    def full_name_test(self):
        self.assertEqual('test user', self.person.get_full_name())

    def short_name_test(self):
        self.assertEqual('test', self.person.get_short_name())

    def username_test(self):
        self.assertEqual('test_user', self.person.get_username())

    def set_active_test(self):
        self.person.set_active(False)
        self.assertFalse(self.person.is_active)
        self.assertEqual(datetime.date.today(), self.person.removed)
        self.person.set_active(True)
        self.assertTrue(self.person.is_active)

    def get_companies_test(self):
        # The company does not have any projects at the moment, so we do not show it.
        self.assertEqual(0, self.person.get_companies().count())

        # Add a project and make this person a client.
        project = ProjectFactory(company=self.person.company)
        project.clients.add(self.person)
        self.assertEqual(1, self.person.get_companies().count())

        # Add a project with no one in it. This will also create a new company
        ProjectFactory()
        self.assertEqual(1, self.person.get_companies().count())

        # Test that as an admin we get all the companies no matter what.
        self.person.is_admin = True
        self.person.save()
        self.assertEqual(2, self.person.get_companies().count())

########NEW FILE########
__FILENAME__ = view_tests
from django.test.client import Client
from django_nose import FastFixtureTestCase
from kala.accounts.views import *
from .factories import PersonFactory
from ..projects.factories import ProjectFactory


class NotLoggedInTests(FastFixtureTestCase):
    def setUp(self):
        self.client = Client()

    def edit_profile_not_logged_in_test(self):
        person = PersonFactory(is_active=True)
        response = self.client.get(reverse('edit_profile', args=[person.pk]))
        self.assertRedirects(response, reverse('login'), status_code=302, target_status_code=200)

        response = self.client.post(reverse('edit_profile', args=[person.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'), status_code=302, target_status_code=200)


class EditProfileViewTests(FastFixtureTestCase):
    def setUp(self):
        self.client = Client()
        self.person = PersonFactory(is_active=True)
        self.person.set_password('test')
        self.person.save()
        self.client = Client()
        self.client.login(username=self.person.username, password='test')

    def edit_profile_test(self):
        # Test editing a profile
        data = self.person.__dict__
        data['first_name'] = 'foo'
        response = self.client.post(reverse('edit_profile', args=[self.person.pk]), data=data)
        self.assertEqual(response.status_code, 302)
        person = Person.objects.get(pk=self.person.pk)
        self.assertEqual('foo', person.first_name)

    def get_test(self):
        # Test doing a get without and with admin rights.
        response = self.client.get(reverse('edit_profile', args=[self.person.pk]))
        self.assertEqual(response.status_code, 200)

        self.person.is_admin = True
        self.person.save()
        response = self.client.get(reverse('edit_profile', args=[self.person.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue('permission_forms' in response.context)

    def get_no_self_not_admin_test(self):
        # Expect to fail chaning someone else when we do not have admin rights.
        person = PersonFactory(is_active=True)
        response = self.client.get(reverse('edit_profile', args=[person.pk]))
        self.assertRedirects(response, reverse('home'), status_code=302, target_status_code=200)

    def toggle_admin_not_admin_test(self):
        person = PersonFactory(is_active=True)

        # This should fail because we do not have admin rights.
        response = self.client.post(reverse('edit_profile', args=[person.pk]), data={'toggle-admin': True})
        self.assertRedirects(response, reverse('home'), status_code=302, target_status_code=200)

        self.person.is_admin = True
        self.person.save()
        # Now that we are admin, toggle the user admin flag.
        response = self.client.post(reverse('edit_profile', args=[person.pk]), data={'toggle-admin': True})
        self.assertRedirects(response, reverse('edit_profile', args=[person.pk]), status_code=302,
                             target_status_code=200)
        person = Person.objects.get(pk=person.pk)
        self.assertTrue(person.is_admin)

        # Toggle back to not admin
        response = self.client.post(reverse('edit_profile', args=[person.pk]), data={'toggle-admin': True})
        self.assertRedirects(response, reverse('edit_profile', args=[person.pk]), status_code=302,
                             target_status_code=200)
        person = Person.objects.get(pk=person.pk)
        self.assertFalse(person.is_admin)

    def toggle_admin_test(self):
        person = PersonFactory(is_active=True)

        # This should fail because we do not have admin rights.
        response = self.client.post(reverse('edit_profile', args=[person.pk]), data={'toggle-admin': True})
        self.assertRedirects(response, reverse('home'), status_code=302, target_status_code=200)

        self.person.is_admin = True
        self.person.save()
        # Now that we are admin, delete the user.
        response = self.client.post(reverse('edit_profile', args=[person.pk]), data={'delete': True})
        self.assertRedirects(response, reverse('accounts'), status_code=302,
                             target_status_code=200)
        person = Person.objects.get(pk=person.pk)
        self.assertFalse(person.is_active)

    def toggle_permissions_test(self):
        # We need to be admin to change permissions
        self.person.is_admin = True
        self.person.save()
        project = ProjectFactory(company=self.person.company)

#        raise Exception(str(permission_forms[0]['{0}'.format(project.pk)]))
        self.person.is_admin = True
        self.person.save()
        # Now that we are admin, delete the user.
        response = self.client.post(reverse('edit_profile', args=[self.person.pk]), data={'{0}'.format(project.pk):
                                                                                         'checked',
                                                                                          'save-permissions': True})
        self.assertRedirects(response, reverse('edit_profile', args=[self.person.pk]), status_code=302,
                             target_status_code=200)
        client = project.clients.get(pk=self.person.pk)
        self.assertEqual(client, self.person)

        # Remove from project and make sure there is no one there.
        response = self.client.post(reverse('edit_profile', args=[self.person.pk]), data={'save-permissions': True})
        self.assertRedirects(response, reverse('edit_profile', args=[self.person.pk]), status_code=302,
                             target_status_code=200)
        self.assertFalse(project.clients.all().exists())


class PeopleViewTests(FastFixtureTestCase):
    def setUp(self):
        self.client = Client()
        self.person = PersonFactory(is_active=True)
        self.person.set_password('test')
        self.person.save()
        self.client = Client()
        self.client.login(username=self.person.username, password='test')

    def not_admin_test(self):
        response = self.client.get(reverse('accounts'))
        self.assertTrue('companies' in response.context)
        self.assertFalse('person_form' in response.context)
        response = self.client.post(reverse('accounts'))
        self.assertRedirects(response, reverse('accounts'), status_code=302, target_status_code=200)

    def is_admin_test(self):
        self.person.is_admin = True
        self.person.save()
        response = self.client.get(reverse('accounts'))
        self.assertTrue('companies' in response.context)
        self.assertTrue('person_form' in response.context)

    def create_company_test(self):
        self.person.is_admin = True
        self.person.save()
        response = self.client.post(reverse('accounts'), data={'create_company': True, 'name': 'foo-bar'})
        company = Company.objects.get(name='foo-bar')
        self.assertTrue(company)
        self.assertRedirects(response, reverse('company', args=[company.pk]), status_code=302, target_status_code=200)

    def create_person_test(self):
        self.person.is_admin = True
        self.person.save()
        response = self.client.post(reverse('accounts'), data={'create_person': True, 'first_name': 'foo',
                                                               'last_name': 'bar', 'username': 'foobar',
                                                               'email': 'foo@bar.com', 'access_new_projects': 'checked',
                                                               'company': self.person.company.pk})
        person = Person.objects.get(email='foo@bar.com')
        self.assertTrue(person)
        self.assertRedirects(response, reverse('accounts'), status_code=302, target_status_code=200)

    def undelete_company_test(self):
        self.person.is_admin = True
        self.person.save()
        self.person.company.set_active(False)
        response = self.client.post(reverse('accounts'), data={'undelete': True, 'company': self.person.company.pk})
        self.assertTrue(Company.objects.get(pk=self.person.company.pk).is_active)
        self.assertRedirects(response, reverse('accounts'), status_code=302, target_status_code=200)

    def post_render_test(self):
        self.person.is_admin = True
        self.person.save()
        response = self.client.post(reverse('accounts'))
        self.assertTrue(response.status_code, 200)

########NEW FILE########
__FILENAME__ = factories
__author__ = 'bryce'

########NEW FILE########
__FILENAME__ = mocks
__author__ = 'bryce'

########NEW FILE########
__FILENAME__ = tests
__author__ = 'bryce'

########NEW FILE########
__FILENAME__ = factories
from kala.companies.models import Company
import factory


class CompanyFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = Company
    name = factory.Sequence(lambda n: 'company-{0}'.format(n))

########NEW FILE########
__FILENAME__ = tests
__author__ = 'bryce'

########NEW FILE########
__FILENAME__ = factories
__author__ = 'bryce'

########NEW FILE########
__FILENAME__ = tests
__author__ = 'bryce'

########NEW FILE########
__FILENAME__ = factories
__author__ = 'bryce'

########NEW FILE########
__FILENAME__ = factories
from kala.projects.models import Project
from ..companies.factories import CompanyFactory
import factory


class ProjectFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = Project
    name = factory.Sequence(lambda n: 'project-{0}'.format(n))
    company = factory.SubFactory(CompanyFactory)

########NEW FILE########
__FILENAME__ = tests
__author__ = 'bryce'

########NEW FILE########
