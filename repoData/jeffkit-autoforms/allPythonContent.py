__FILENAME__ = admin
#encoding=utf-8

from django.conf.urls.defaults import *
from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import render_to_response,get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.template import loader, Context
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site

from autoforms import models
from autoforms import forms


class FieldInline(admin.TabularInline):
    model = models.Field
    form = forms.FieldForm

class FormAdmin(admin.ModelAdmin):
    list_display = ['name','slug','short_desc']
    search_fields = ['name','description']
    inlines = [FieldInline]
    fieldsets = (
        ('',{
            'fields':('name','base','slug','description','enable')
        }),
    )

    def preview(self,request,id):
        form = models.Form.objects.get(pk=id)
        return render_to_response('autoforms/admin/form_preview.html',{'form':form,'dform':form.as_form(),'title':_('Preview form : %(form_name)s')%{'form_name':form.name}},context_instance = RequestContext(request))

    def data(self,request,id):
        form = models.Form.objects.get(pk=id)
        return render_to_response('autoforms/admin/form_data.html',{'form':form,'title':_('Data of form : %(form_name)s')%{'form_name':form.name}},context_instance = RequestContext(request))

    def embed(self,request,id):
        form = models.Form.objects.get(pk=id)
        url = reverse("form-fill",args=[form.user.username,form.slug])
        site = Site.objects.get_current()
        url = site.domain + url
        if not url.startswith('http://'):
            url = 'http://' + url
        code = '<iframe id="id_%s" name="form_%s" width="100%%" height="500"  frameborder="0" marginheight="0" marginwidth="0" src="%s"></iframe>'%(form.slug,form.slug,url)
        return render_to_response('autoforms/admin/form_embed.html',{'code':code,'form':form,'is_popup':True,'title':_('Embed code')},
                context_instance = RequestContext(request))

    def export(self,request,id,format='csv'):
        form = models.Form.objects.get(pk=id)
        if format == 'csv':
            response = HttpResponse(mimetype='text/csv')
            response['Content-Disposition'] = 'attachment; filename=%s.csv'%id
            template = loader.get_template('autoforms/admin/form_export.csv')
            context = Context({'datalist':form.search(),'fields':form.sorted_fields()})
            response.write(template.render(context))
            return response
        else:
            return HttpResponse('format not support yet')

    def get_urls(self):
        urls = super(FormAdmin,self).get_urls()
        form_urls = patterns('',
            (r'^(?P<id>\d+)/preview/$',self.admin_site.admin_view(self.preview)),
            (r'^(?P<id>\d+)/data/$',self.admin_site.admin_view(self.data)),
            (r'^(?P<id>\d+)/embed/$',self.admin_site.admin_view(self.embed)),
            (r'^(?P<id>\d+)/data/export/(?P<format>\w+)/$',self.admin_site.admin_view(self.export)),
        )
        return form_urls + urls

    def queryset(self,request):
        qs = super(FormAdmin,self).queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    def save_model(self,request,obj,form,change):
        if getattr(obj,'user',None) is None:
            obj.user = request.user
        obj.save()

    def formfield_for_foreignkey(self,db_field,request,**kwargs):
        if not request.user.is_superuser:
            if db_field.name == 'base':
                kwargs['queryset'] = models.Form.objects.filter(user=request.user)
        return super(FormAdmin,self).formfield_for_foreignkey(db_field,request,**kwargs)

admin.site.register(models.Form,FormAdmin)

class ErrorMessageInline(admin.TabularInline):
    model = models.ErrorMessage
    template = 'autoforms/field_tabular.html'

class OptionInline(admin.TabularInline):
    model = models.Option
    template = 'autoforms/field_tabular.html'

class FieldAdmin(admin.ModelAdmin):
    list_display = ['label','form','name','type','required','order',]
    search_fields = ['form__name','name','label','description','help_text']
    inlines = [OptionInline,ErrorMessageInline]

    fieldsets = (
        (_('basic info'),{
            'fields':('form','type','widget','required','order','name','label','initial','help_text')
        }),
        (_('advantage settings'),{
            'classes': ('collapse',),
            'fields':('localize','extends','description')
        })
        )

    def formfield_for_foreignkey(self,db_field,request,**kwargs):
        if not request.user.is_superuser:
            if db_field.name == 'form':
                kwargs['queryset'] = models.Form.objects.filter(user=request.user)
        return super(FieldAdmin,self).formfield_for_foreignkey(db_field,request,**kwargs)

    def queryset(self,request):
        qs = super(FieldAdmin,self).queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(form__in = request.user.form_set.all())

admin.site.register(models.Field,FieldAdmin)

########NEW FILE########
__FILENAME__ = forms
#encoding=utf-8
from django.contrib.admin import widgets
from django import forms
try:
    import simplejson
except:
    from django.utils import simplejson
from models import Field

field_types = {
    'boolean':forms.BooleanField,
    'char':forms.CharField,
    'choice':forms.ChoiceField,
    'date':forms.DateField,
    'datetime':forms.DateTimeField,
    'decimal':forms.DecimalField,
    'email':forms.EmailField,
    'file':forms.FileField,
    'float':forms.FloatField,
    'filepath':forms.FilePathField,
    'image':forms.ImageField,
    'integer':forms.IntegerField,
    'ipadress':forms.IPAddressField,
    'multipleChoice':forms.MultipleChoiceField,
    'nullBoolean':forms.NullBooleanField,
    'regex':forms.RegexField,
    'slug':forms.SlugField,
    'time':forms.TimeField,
    'url':forms.URLField,
    'modelChoice':forms.ModelChoiceField,
    'modelMultipleChoice':forms.ModelMultipleChoiceField,
}

widget_types = {
    'text':forms.TextInput,
    'password':forms.PasswordInput,
    'hidden':forms.HiddenInput,
    'multipleHidden':forms.MultipleHiddenInput,
    'file':forms.FileInput,
    'date':widgets.AdminDateWidget,
    'datetime':widgets.AdminSplitDateTime,
    'time':widgets.AdminTimeWidget,
    'textarea':forms.Textarea,
    'checkbox':forms.CheckboxInput,
    'select':forms.Select,
    'nullBoolean':forms.NullBooleanSelect,
    'selectMultiple':forms.SelectMultiple,
    'radio':forms.RadioSelect,
    'checkboxMultiple':forms.CheckboxSelectMultiple,
}

field_required_arguments = {
    'choice':'choices',
    'multipleChoice':'choices',
    'regex':'regex',
    'combo':'fields',
    'multiValue':'fields',
    'modelChoice':'queryset',
    'modelMultipleChoice':'queryset',
}

class AutoForm(forms.Form):
    """
    usage：
    1. create an empty AutoForm:
    form = AutoForm(fields=form.sorted_fields()))
    2. create an AutoForm with datas:
    form = AutoForm(fields=form.sorted_fields()),data=datas)
    """
    def __init__(self,fields,data=None,*args,**kwargs1):
        super(AutoForm,self).__init__(data,*args,**kwargs1)
        # fields is a set of sorted fields
        for field in fields:
            field_type = field_types[field.type]
            kwargs = {'required':field.required,'label':field.label,'help_text':field.help_text,'localize':field.localize}
            if field.widget:
                kwargs['widget'] = widget_types[field.widget]()
            if field.initial:
                kwargs['initial'] = field.initial

            # turn extends from json to dict
            if field.extends:
                other_args = simplejson.loads(field.extends)
                for item in other_args.items():
                    kwargs[str(item[0])] = item[1]

            # ModelChioce field，need a queryset parameter.
            if field.type in ['modelChoice','modelMultipleChoice']:
                if field.datasource:
                    kwargs['queryset'] = field.datasource.model_class().objects.all()
                else:
                    raise ValueError,u'%s need a datasource!'%field.name

            if field.type in ['choice','multipleChoice']:
                choices = []
                if kwargs.get('choices',None):
                    choices += kwargs['choices']
                for option in field.option_set.all():
                    choices.append((option.value,option.label))

                kwargs['choices'] = choices

            else:
                required_arguments = field_required_arguments.get(field.type,None)
                if required_arguments:
                    required_arguments = required_arguments.split(',')
                    for arg in required_arguments:
                        if arg not in kwargs:
                            raise ValueError,u'argument "%s" for %s is required'%(arg,field.name)

                if field.widget in ['select','selectMultiple','radio','checkboxMultiple']:
                    if 'choices' not in kwargs:
                        raise ValueError,'widget select,radio,checkbox need a choices parameters'

            # custome error message
            error_messages = {}
            for error_msg in field.errormessage_set.all():
                error_messages[error_msg.type] =  error_msg.message

            if error_messages:
                kwargs['error_messages'] = error_messages

            self.fields[field.name] = field_type(**kwargs)


class FieldForm(forms.ModelForm):
    class Meta:
        model = Field
        fields = ('type','required','name','label','help_text','order','widget')


########NEW FILE########
__FILENAME__ = models
#encoding=utf-8
from django.db import models
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.db.models.query import QuerySet
from django.utils import simplejson
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.conf import settings
from django.core.mail import send_mail
from signal import form_filled

field_types = (
    ('char',_('char')),
    ('boolean',_('boolean')),
    ('choice',_('choice')),
    ('multipleChoice',_('mulitpleChoice')),
    ('date',_('date')),
    ('datetime',_('datetime')),
    ('decimal',_('decimal')),
    ('email',_('email')),
    #('file',_('file')),
    ('float',_('float')),
    #('filepath',_('filepath')),
    #('image',_('image')),
    ('integer',_('integer')),
    ('ipadress',_('ipaddress')),
    #('nullBoolean',_('nullBoolean')),
    #('regex',_('regex')),
    ('slug',_('slug')),
    ('time',_('time')),
    ('url',_('url')),
    #('modelChoice',_('modelChoice')),
    #('modelMultipleChoice',_('modelMultipleChoice')),
)

widget_types = (
    ('text',_('text')),
    ('textarea',_('textarea')),
    ('password',_('password')),
    ('hidden',_('hidden')),
    ('multipleHidden',_('multipleHidden')),
    #('file',_('file')),
    ('date',_('date')),
    ('datetime',_('datetime')),
    ('time',_('time')),
    ('radio',_('radio')),
    ('select',_('select')),
    #('nullBoolean',_('nullBoolean')),
    ('selectMultiple',_('selectMultiple')),
    ('checkbox',_('checkbox')),
    ('checkboxMultiple',_('checkboxMultiple')),
)

# Form Definition

class Form(models.Model):
    """
    Present a Django Form subClass
    """
    name = models.CharField(_('Form.name'),max_length=50)
    slug = models.SlugField(_('Form.slug'),unique=True,help_text=_('a easy to remember slug,letters,digits,underlines are allowed.'))
    base = models.ForeignKey('self',verbose_name=_('Form.base'),blank=True,null=True)
    fields = models.TextField(_('Form.fields'),help_text=_('set the display fields,separate with comma'),blank=True,null=True)
    description = models.TextField(_('Form.description'))
    enable = models.BooleanField(_('Form.enable'),default=True)
    user = models.ForeignKey(User,verbose_name=_('user'),blank=True,null=True)

    def short_desc(self):
        if self.description and len(self.description) > 70:
            return self.description[:70] + '...'
        return self.description

    short_desc.short_description = _('description')

    @models.permalink
    def get_absolute_url(self):
        return ('autoforms.views.fill_with_slug',[self.user.username,self.slug])

    def persist(self,data):
        """
        usage:
        data = request.POST
        form.persist(data)
        """
        form = self.as_form(data)
        if form.is_valid():
            fi = FormInstance(_form=self,_name=self.name)
            fi.save(form.cleaned_data)
            return fi
        else:
            return None

    def sorted_fields(self,fields=None):
        """
        return sorted fields
        """
        real_fields = []
        field_dict = {}
        if self.base: # add parent's field first
            field_set_base = self.base.sorted_fields()
            real_fields += field_set_base
            for field in field_set_base:
                field_dict[field.name] = field

        field_set = self.field_set.filter(enable=True).order_by('order')
        for field in field_set:
            if field_dict.has_key(field.name):
                index = real_fields.index(field_dict[field.name])
                real_fields.remove(field_dict[field.name])
                real_fields.insert(index,field)
            else:
                real_fields.append(field)
            field_dict[field.name] = field # local field will override the parent's same field

        if self.fields or fields:
            real_fields = []
            order_field = self.fields.split(',')
            for f in order_field:
                real_fields.append(field_dict[f])
        return real_fields

    def as_form(self,data=None):
        """
        usage:
        form = Form.objects.get(pk=1)
        fobj = form.as_form() # fobj is a Django Form obj
        """
        from autoforms.forms import AutoForm
        return AutoForm(fields=self.sorted_fields(),data=data)

    def search(self,page=1,pagesize=0,*args,**kwargs):
        """
        search form instance data
        """
        if pagesize:
            start = (page - 1) * pagesize
            fis = FormInstance.objects.filter(_form=self)[start:start + pagesize]
        else:
            fis = FormInstance.objects.filter(_form=self)


        fvs = FieldValue.objects.filter(form__in=fis).order_by('form')

        datas = []
        current_instance = None
        current_data = {}

        def find_instance(id):
            for fi in fis:
                if fi.pk == id:return fi

        def update_current():
            current_instance.apply_form_data(self.as_form(current_data))
            datas.append(current_instance)

        for item in fvs:
            if current_instance:
                # same as last row
                if item.form.pk != current_instance.pk:
                    update_current()
                    # setup new instace for current
                    current_instance = find_instance(item.form.pk)
                    current_data = {}
            else:
                # the first row
                current_instance = find_instance(item.form.pk)
            current_data[item.name] = item.value
            setattr(current_instance,item.name,item.value)
        if current_instance:
            update_current()
        return datas


    class Meta:
        verbose_name = _('form')
        verbose_name_plural = _('forms')

    def __unicode__(self):
        return self.name

class Field(models.Model):
    """
    Present a Form Field Class
    """
    form = models.ForeignKey(Form,verbose_name=_('Field.form'))
    name = models.SlugField(_('Field.name'),help_text=_('leters,digits,underline are allowed.'))
    label = models.CharField(_('Field.label'),max_length=50,blank=True,null=True,help_text=_('a friendly field label'))
    required = models.BooleanField(_('Field.required'),help_text=_('is it required?'))
    type = models.CharField(_('Field.type'),max_length=50,choices=field_types)
    help_text = models.CharField(_('Field.help_text'),max_length=200,blank=True,null=True)
    widget = models.CharField(_('Field.widget'),max_length=50,blank=True,null=True,choices=widget_types)
    initial = models.CharField(_('Field.initial'),max_length=200,blank=True,null=True)
    validators = models.CharField(_('Field.validators'),max_length=200,help_text=_('validator names,separate with space'),blank=True,null=True)
    localize = models.BooleanField(_('Field.localize'),default=False)
    order = models.IntegerField(_('Field.order'),default=0)
    description = models.TextField(_('Field.description'),blank=True,null=True)
    datasource = models.ForeignKey(ContentType,verbose_name=_('Field.datasource'),help_text=_('select a datasource for the choice field'),null=True,blank=True)
    extends = models.TextField(_('Field.extends'),help_text=_('other parameters,such as widget parameters,use a json dictionary'),blank=True,null=True)
    enable = models.BooleanField(_('Field.enable'),default=True)

    class Meta:
        verbose_name = _('Field')
        verbose_name_plural = _('Fields')

    def __unicode__(self):
        return self.name

class Option(models.Model):
    """
    Options for Choice.
    """
    field = models.ForeignKey(Field,verbose_name=_('Option.field'))
    value = models.CharField(_('Option.value'),max_length=100)
    label = models.CharField(_('Option.label'),max_length=100)

    def __unicode__(self):
        return self.label

    class Meta:
        verbose_name = _('Option')
        verbose_name_plural = _('Options')


class ErrorMessage(models.Model):
    """
    Custom Error Messages
    """
    field = models.ForeignKey(Field,verbose_name=_('ErrorMessage.field'))
    type = models.CharField(_('ErrorMessage.type'),max_length=20)
    message = models.CharField(_('ErrorMessage.message'),max_length=100)

    class Meta:
        verbose_name = _('ErrorMessage')
        verbose_name_plural = _('ErrorMessages')

    def __unicode__(self):
        return self.type

# Form Runtime

class FormInstance(models.Model):
    """
    A Form Instance
    """
    _id = models.AutoField(primary_key=True)
    _form = models.ForeignKey(Form,verbose_name=_('FormInstance.form'))
    _name = models.CharField(_('FormInstance.name'),max_length=100)
    _create_at = models.DateTimeField(_('FormInstance.create_at'),auto_now_add=True)

    def apply_form_data(self,form):
        self.formobj = form
        if form.is_valid():
            self.cleaned_data = form.cleaned_data

    def save(self,*args,**kwargs):
        data = None
        if kwargs.get('data',None):
           data = kwargs['data']
           del kwargs['data']
        super(FormInstance,self).save(*args,**kwargs)
        if data:
            for key in data.keys():
                if data[key] is not None:
                    if type(data[key]) in(list,QuerySet,tuple):
                        value = [unicode(item) for item in data[key]]
                        value = simplejson.dumps(value)
                    else:
                        value = unicode(data[key])
                    field_value = FieldValue(form=self,name=key,value=value)
                    field_value.save()
        form_filled.send(sender=self.__class__,form=self._form,instance=self)


    class Meta:
        verbose_name = _('FormInstance')
        verbose_name_plural = _('FormInstances')

    def __unicode__(self):
        return self._name

    def summary(self):
        result = ''
        for value in self.fieldvalue_set.all():
            result = result + '%s : %s \n'%(value.name,value.value)
        return result


class FieldValue(models.Model):
    form = models.ForeignKey(FormInstance,verbose_name=_('FieldValue.form'))
    name = models.CharField(_('FieldValue.name'),max_length=100)
    value = models.TextField(_('FieldValue.value'))

    class Meta:
        verbose_name = _('FieldValue')
        verbose_name_plural = _('FieldValues')

    def __unicode__(self):
        return "%s: %s" % (self.name, self.value)

############ signals ############

def form_fill_notify(sender,form,instance,**kwargs):
    if getattr(settings,'NOTIFY_FORM_CHANGE',False):
        msg = 'New commit for form "%s":\n%s' %(form.name,instance.summary())
        send_mail('New commit for form %s'%form.name,msg,
                'notfiy@jeffkit.info',[form.user.email],fail_silently=True)


form_filled.connect(form_fill_notify,sender=FormInstance,dispatch_uid='form_fill_notify')



########NEW FILE########
__FILENAME__ = signal
#encoding=utf-8

from django.dispatch import Signal

form_filled = Signal(providing_args=['form','instance'])

########NEW FILE########
__FILENAME__ = autoforms
#encoding=utf-8
from django import template
from django.template import resolve_variable,TemplateSyntaxError,loader
import re

register = template.Library()
kwarg_re = re.compile(r"(?:(\w+)=)?(.+)")

def form_value(value):
  if not value:
	return ''
  if type(value) == list:
	return ','.join(value)
  return value

register.filter('formvalue',form_value)

def attr(value,attr):
    if value is not None:
        return getattr(value,attr,None)

register.filter('attr',attr)


class DataListNode(template.Node):
    def __init__(self,form,args,kwargs):
        self.form = form
        self.args = args
        self.kwargs = kwargs
        self.fields = None
        self.template = 'autoforms/datalist.html'
        if self.args:
            if len(args) >= 3:
                self.fields = args[2]
            if len(args) >=4:
                self.template = args[3]
        elif self.kwargs:
            self.fields = self.kwargs.get('fields',None)
            self.template = self.kwargs.get('template',None)
        if self.fields:
            self.fields = self.fields.split(',')

    def render(self,context):
        self.form = resolve_variable(self.form,context)
        formlist = self.form.search(*self.args,**self.kwargs)
        self.fields = self.form.sorted_fields(self.fields)
        context = {'form':self.form,'datalist':formlist,'fields':self.fields}
        result = loader.render_to_string(self.template,context)
        return result



def formdata(parser,token):
    bits = token.split_contents()
    if len(bits) < 2:
        raise TemplateSyntaxError("'%s' takes at least one argument (form to a view)" % bits[0])
    form = bits[1]
    args = []
    kwargs = {}
    bits = bits[2:]

    if len(bits):
        for bit in bits:
            match = kwarg_re.match(bit)
            if not match:
                raise TemplateSyntaxError("Malformed arguments to url tag")
            name,value = match.groups()
            if name:
                kwarg[name] = parser.compile_filter(value)
            else:
                args.append(parser.compile_filter(value))
    return DataListNode(form,args,kwargs)

register.tag(formdata)

########NEW FILE########
__FILENAME__ = tests
#encoding=utf-8

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)


__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
#encoding=utf-8
from django.conf.urls.defaults import *
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),

    (r'^$','autoforms.views.index'),
    (r'^jsi18n/$','autoforms.views.jsi18n'),
	(r'^preview/$','autoforms.views.preview'),
	(r'^preview/(?P<id>\d+)/$','autoforms.views.preview'),
	url(r'^fill/(?P<id>\d+)/$','autoforms.views.fill_with_id',name="form-fill-old"),
	url(r'^(?P<user>[\w-]+)/(?P<slug>[\w-]+)/$','autoforms.views.fill_with_slug',name="form-fill"),
)

########NEW FILE########
__FILENAME__ = views
# Create your views here.
from models import Form,FormInstance
from autoforms.forms import AutoForm
from django.shortcuts import render_to_response,get_object_or_404
from django.contrib import admin
from django.template import RequestContext

def jsi18n(request):
    return admin.site.i18n_javascript(request)

def index(request):
    return render_to_response('autoforms/index.html',context_instance=RequestContext(request))

def preview(request,id=None,template='autoforms/preview.html'):
    if request.method == 'GET':
        pk = id or request.GET.get('id',None)
        if not pk:
            forms = Form.objects.all()
            return render_to_response(template,{'forms':forms},context_instance=RequestContext(request))
        else:
            dform = get_object_or_404(Form,pk=pk)
            form = dform.as_form()
            return render_to_response(template,{'form':form,'dform':dform,'edit':True,'id':pk},context_instance=RequestContext(request))
    else:
        dform = get_object_or_404(Form,pk=id)
        form = AutoForm(fields=dform.field_set.all().order_by('order'),data=request.POST)
        if form.is_valid():
            return render_to_response(template,{'form':form,'dform':dform},context_instance=RequestContext(request))
        else:
            return render_to_response(template,{'form':form,'dform':dform,'edit':True},context_instance=RequestContext(request))

def fill_with_id(request,id,template='autoforms/fill.html',success_template='autoforms/fill_done.html'):
    form = get_object_or_404(Form,pk=id)
    return fill(request,form,template,success_template)

def fill_with_slug(request,user,slug,template='autoforms/fill.html',success_template='autoforms/fill_done.html'):
    form = get_object_or_404(Form,user__username=user,slug=slug)
    return fill(request,form,template,success_template)

def fill(request,form,template='autoforms/fill.html',success_template='autoforms/fill_done.html'):
    data = request.GET or request.POST
    #is_popup = data.get('is_popup',None)
    is_popup = True
    if request.method == 'GET':
        dform = form.as_form()
        return render_to_response(template,{'title':form.name,'is_popup':is_popup,'form':form,'dform':dform},context_instance=RequestContext(request))
    else:
        dform = AutoForm(fields=form.sorted_fields(),data=request.POST)
        if dform.is_valid():
            if form.enable:
                # save the data only form is enable
                fi = FormInstance(_form=form,_name=form.name)
                fi.save(data=dform.cleaned_data)
            return render_to_response(success_template,{'title':form.name,'is_popup':is_popup,'form':form,'dform':dform},context_instance=RequestContext(request))
        else:
            return render_to_response(template,{'title':form.name,'is_popup':is_popup,'form':form,'dform':dform},context_instance=RequestContext(request))




########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for sample project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'autoforms.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
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

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'e4ncgz$#*thuu%=s%=s4%bylps=f+a2e81(h#@yi+0!uye71f%'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'sample.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'autoforms',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'sample.views.home', name='home'),
    # url(r'^sample/', include('sample.foo.urls')),

    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
