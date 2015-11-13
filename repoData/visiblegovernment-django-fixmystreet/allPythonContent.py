__FILENAME__ = admin
from fixmystreet.mainapp.models import UserProfile,EmailRule,Ward,ReportCategory,City, ReportCategoryClass, FaqEntry, Councillor,ReportCategorySet
from django.contrib import admin
from transmeta import canonical_fieldname
from django import forms

admin.site.register(City)
admin.site.register(UserProfile)

class ReportCategoryClassAdmin(admin.ModelAdmin):
    list_display = ('name',)
    
admin.site.register(ReportCategoryClass,ReportCategoryClassAdmin)

class ReportCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'hint')

admin.site.register(ReportCategory, ReportCategoryAdmin)

class ReportCategorySetAdmin(admin.ModelAdmin):
    list_display = ('name',)

admin.site.register(ReportCategorySet, ReportCategorySetAdmin)

class FaqEntryAdmin(admin.ModelAdmin):
    list_display = ('q', 'order')

admin.site.register(FaqEntry, FaqEntryAdmin)
    
class CouncillorAdmin(admin.ModelAdmin):
    ''' only show councillors from cities this user has access to '''
    list_display = ('last_name', 'first_name', 'email')
    
    def queryset(self,request):
        if request.user.is_superuser:
            return( super(CouncillorAdmin,self).queryset(request) )
        profile = request.user.get_profile()        
        qs = self.model._default_manager.filter(city__in=profile.cities.all())
        return(qs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "city":
                profile = request.user.get_profile()
                kwargs["queryset"] = profile.cities.all()
        return super(CouncillorAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)
    
            
admin.site.register(Councillor,CouncillorAdmin)


class WardAdmin(admin.ModelAdmin):
    ''' only show wards from cities this user has access to '''

    list_display = ('city','number','name',)
    list_display_links = ('name',)
    ordering       = ['city', 'number']
    exclude = ['geom']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            profile = request.user.get_profile()
            if db_field.name == "councillor":
                kwargs["queryset"] = Councillor.objects.filter(city__in=profile.cities.all())
            if db_field.name == "city":
                kwargs["queryset"] = profile.cities.all()
        return super(WardAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)
        
    def queryset(self,request):
        if request.user.is_superuser:
            return( super(WardAdmin,self).queryset(request) )
        profile = request.user.get_profile()
        qs = self.model._default_manager.filter(city__in=profile.cities.all())
        return(qs)
    
admin.site.register(Ward,WardAdmin)

class EmailRuleAdmin(admin.ModelAdmin):
    ''' only show email rules from cities this user has access to '''

    change_list_template = 'admin/mainapp/emailrules/change_list.html'

    def queryset(self,request):
        if request.user.is_superuser:
            return( super(EmailRuleAdmin,self).queryset(request) )
        profile = request.user.get_profile()
        qs = self.model._default_manager.filter(city__in=profile.cities.all())
        return(qs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "city":
                profile = request.user.get_profile()
                kwargs["queryset"] = profile.cities.all()
        return super(EmailRuleAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)
    

admin.site.register(EmailRule,EmailRuleAdmin)

########NEW FILE########
__FILENAME__ = emailrules
from django.utils.translation import ugettext as _

class EmailRuleBehaviour(object):
    def get_email(self,report,email_rule):
        return(None)
    
    def describe(self, email_rule):
        return("")
            
class ToCouncillor(EmailRuleBehaviour):
    def get_email(self, report, email_rule):
        return( report.ward.councillor.email )

    def describe(self, email_rule ):
        return("Send Reports to Councillor's Email Address")

    def report_group(self, email_rule):
        return(_("All reports"))
    
    def value_for_ward(self, email_rule, ward):
        return( ward.councillor.email )

    def value_for_city(self,email_rule):
        return(_("the councillor's email address"))
    
class ToWard(EmailRuleBehaviour):

    def get_email(self, report, email_rule):
        return( report.ward.email )

    def describe(self, email_rule ):
        return("Send Reports to Email Address for Ward")

    def report_group(self, email_rule):
        return(_("All reports"))
    
    def value_for_ward(self, email_rule, ward):
        return( ward.email )

    def value_for_city(self,email_rule):
        return(_("the 311 email address for that neighborhood"))
    
class MatchingCategoryClass(EmailRuleBehaviour):
    def get_email(self,report, email_rule):
        if report.category.category_class == email_rule.category_class:
            return( email_rule.email )
        else:
            return( None )

    def describe(self,email_rule):
        return('Send All Reports Matching Category Type %s To %s' % (email_rule.category_class.name_en, email_rule.email))
    
    def report_group(self, email_rule ):
        return(_("'%s' reports") % ( email_rule.category_class.name ) )
    
    def value_for_ward(self, email_rule, ward):
        return( email_rule.email )
    
    def value_for_city(self,email_rule):
        return(email_rule.email)
    
class NotMatchingCategoryClass(EmailRuleBehaviour):
    def get_email(self,report, email_rule):
        if report.category.category_class != email_rule.category_class:
            return( email_rule.email )
        else:
            return( None )

    def describe(self,email_rule):
        return('Send All Reports Not Matching Category Type %s To %s' % (email_rule.category_class.name_en, email_rule.email))

    def report_group(self, email_rule):
        return(_("non-'%s' reports") % ( email_rule.category_class.name ) )
    
    def value_for_ward(self, email_rule, ward):
        return( email_rule.email )

    def value_for_city(self,email_rule):
        return(email_rule.email)
    
# Creates a human-readable description of a single email rule 
# in the context of a particular ward or city.

class EmailRuleDescriber:

    def __init__(self, desc):
        self.cc = []
        self.to = []            
        self.desc = desc
        
    def __unicode__(self):
        s = _("%s will be ") % (self.desc)
        if len(self.to) != 0:
            s += _("sent to:")
            s += ",".join(self.to)
        
        if len(self.to) != 0 and len(self.cc) != 0:
            s += _(" and ")
            
        if len(self.cc) != 0:
            s += _("cc'd to:")
            s += ",".join(self.cc)
        return( s )

    def add_rule(self, rule, ward ):
        value = rule.value(ward)
        if rule.is_cc:
            self.cc.append(value)
        else:
            self.to.append(value)


# Creates a human-readable description of an email rule set
# for a particular ward or city.

class EmailRulesDesciber:
    
    def __init__(self, rules, city, ward = None):
        self.rule_set = {}
        if city.email:
            city_email = EmailRuleDescriber( _('All reports') )
            city_email.to.append(city.email)
            self.rule_set[city_email.desc] = city_email
            
        for rule in rules:
            label = rule.label()
            if not self.rule_set.has_key( label ):
                self.rule_set[ label ] = EmailRuleDescriber( label )
        
            describer = self.rule_set[ label ]
            describer.add_rule( rule, ward )
            
    def values(self):
        ret = self.rule_set.values()
        ret.reverse()
        return( ret )

        
########NEW FILE########
__FILENAME__ = feeds
from django.contrib.syndication.views import Feed
from django.contrib.syndication.feeds import FeedDoesNotExist
from mainapp.models import Report, ReportUpdate, City, Ward
from django.shortcuts import get_object_or_404

class ReportFeedBase(Feed):
    description_template = 'feeds/reports_description.html'

    def item_title(self, item):
        return item.title

    def item_pubdate(self, item):
        return item.created_at
    
    def item_link(self,item):
        return item.get_absolute_url()

    
class LatestReports(ReportFeedBase):
    title = "All FixMyStreet Reports"
    link = "/reports/"
    description = "All FixMyStreet.ca Reports"

    def items(self):
        return Report.objects.filter(is_confirmed=True).order_by('-created_at')[:30]

class CityFeedBase(ReportFeedBase):
    
    def title(self, obj):
        return "FixMyStreet.ca: Reports for %s" % obj.name

    def link(self, obj):
        if not obj:
            raise FeedDoesNotExist
        return obj.get_absolute_url()

    def description(self, obj):
        return "Problems recently reported in the city of %s" % obj.name

    def items(self, obj):
       return Report.objects.filter(is_confirmed=True,ward__city=obj.id).order_by('-created_at')[:30]


class CityIdFeed(CityFeedBase):
    ''' retrieve city by id '''
    def get_object(self, request, id ):
       return get_object_or_404(City, pk=id)

class CitySlugFeed(CityFeedBase):
    ''' retrieve city by slug '''
    def get_object(self, request, slug ):
       return get_object_or_404(City, slug=slug)
    
class WardFeedBase(ReportFeedBase):
    
    def title(self, obj):
        return "FixMyStreet.ca: Reports for %s, %s" % (obj.name, obj.city.name)

    def link(self, obj):
        if not obj:
            raise FeedDoesNotExist
        return obj.get_absolute_url()

    def description(self, obj):
        return "Problems recently reported in %s, %s" % ( obj.name, obj.city.name)

    def items(self, obj):
       return Report.objects.filter(is_confirmed=True,ward=obj.id).order_by('-created_at')[:30]


class WardIdFeed(WardFeedBase):
    ''' retrieve city by id '''
    def get_object(self, request, id ):
       return get_object_or_404(Ward, pk=id)

class WardSlugFeed(WardFeedBase):
    ''' retrieve city by slug '''
    def get_object(self, request, city_slug, ward_slug ):
       return get_object_or_404(Ward, slug=ward_slug,city__slug=city_slug)
    

# Allow subsciption to a particular report.

class LatestUpdatesByReport(Feed):
    
    def get_object(self, bits):
        # In case of "/rss/beats/0613/foo/bar/baz/", or other such clutter,
        # check that bits has only one member.
        if len(bits) != 1:
            raise ObjectDoesNotExist        
        return Report.objects.get(id=bits[0])

    def title(self, obj):
        return "FixMyStreet.ca: Updates for Report %s" % obj.title

    def link(self, obj):
        if not obj:
            raise FeedDoesNotExist
        return obj.get_absolute_url()
    
    def item_link(self,obj):
        return( obj.report.get_absolute_url())

    def description(self, obj):
        return "Updates for FixMySteet.ca Problem Report %s" % obj.title

    def items(self, obj):
       return obj.reportupdate_set.order_by('created_at')[:30]

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from mainapp.models import Ward, Report, ReportUpdate, ReportCategoryClass,ReportCategory,ReportSubscriber,DictToPoint,UserProfile
from django.utils.translation import ugettext_lazy as _
from django.contrib.gis.geos import fromstr
from django.forms.util import ErrorDict
from registration.forms import RegistrationForm
from registration.models import RegistrationProfile
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.sites.models import Site
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100,
                           widget=forms.TextInput(attrs={ 'class': 'required' }),
                           label=_('Name'))
    email = forms.EmailField(widget=forms.TextInput(attrs=dict({ 'class': 'required' },
                                                               maxlength=200)),
                             label=_('Email'))
    body = forms.CharField(widget=forms.Textarea(attrs={ 'class': 'required' }),
                              label=_('Message'))
    
    def save(self, fail_silently=False):
        message = render_to_string("emails/contact/message.txt", self.cleaned_data )
        send_mail('FixMyStreet.ca User Message from %s' % self.cleaned_data['email'], message, 
                   settings.EMAIL_FROM_USER,[settings.ADMIN_EMAIL], fail_silently=False)


class ReportUpdateForm(forms.ModelForm):
    class Meta:
        model = ReportUpdate
        fields = ( 'desc','author','email','phone')

class ReportSubscriberForm(forms.ModelForm):
    class Meta:
        model = ReportSubscriber
        fields = ( 'email', )

    def __init__(self,data=None,files=None,initial=None, freeze_email=False):
        super(ReportSubscriberForm,self).__init__(data,files=files, initial=initial)
        if freeze_email:
            self.fields['email'].widget.attrs['readonly'] = 'readonly'
        
"""
    Do some pre-processing to
    render opt-groups (silently supported, but undocumented
    http://code.djangoproject.com/ticket/4412 )
"""
    
class CategoryChoiceField(forms.fields.ChoiceField):
    
    def __init__(self, ward=None,required=True, widget=None, label=None,
                 initial=None, help_text=None, *args, **kwargs):
        # assemble the opt groups.
        choices = []
        self.ward = ward
        choices.append( ('', _("Select a Category")) )
        if ward:
            categories = ward.city.get_categories()
        else:
            categories = []
            
        groups = {}
        for category in categories:
            catclass = str(category.category_class)
            if not groups.has_key(catclass):
                groups[catclass] = []
            groups[catclass].append((category.pk, category.name ))
        for catclass, values in groups.items():
            choices.append((catclass,values))

        super(CategoryChoiceField,self).__init__(choices=choices,required=required,widget=widget,label=label,initial=initial,help_text=help_text,*args,**kwargs)

    def clean(self, value):
        if not self.ward:
            # don't bother validating if we couldn't resolve
            # the ward... this will be picked up in another error
            return None
        
        super(CategoryChoiceField,self).clean(value)
        try:
            model = ReportCategory.objects.get(pk=value)
        except ReportCategory.DoesNotExist:
            raise ValidationError(self.error_messages['invalid_choice'])
        return model


class EditProfileForm(forms.ModelForm):

    first_name = forms.CharField()
    last_name = forms.CharField()

    class Meta:
        model = UserProfile
        fields = ( 'first_name','last_name','phone',)
        
    # from example here:
    # http://yuji.wordpress.com/2010/02/16/django-extension-of-modeladmin-admin-views-arbitrary-form-validation-with-adminform/ 

    RELATED_FIELD_MAP = {
            'first_name': 'first_name',
            'last_name': 'last_name',
    }
        
    def __init__(self, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        if self.instance.id:
            for field, target_field in self.RELATED_FIELD_MAP.iteritems():
                self.initial[ field ] = getattr(self.instance.user, target_field )
     
    def save(self, *args, **kwargs):
          for field, target_field in self.RELATED_FIELD_MAP.iteritems():
              setattr(self.instance.user,target_field, self.cleaned_data.get(field))
          self.instance.user.save()
          super(EditProfileForm, self).save(*args, **kwargs)
     
class ReportUpdateForm(forms.ModelForm):
        
    class Meta:
        model = ReportUpdate
        fields = ('desc','author','email','phone','is_fixed')


    def __init__(self,data=None,files=None,initial={},first_update=False,user = None, report=None):
       self.user = None
       self.report = report
       self.first_update= first_update
       if user and user.is_authenticated() and UserProfile.objects.filter(user=user).exists():
           self.user = user

       if self.user:
           if not data:
               initial[ 'author' ] = user.first_name + " " + user.last_name
               initial[ 'phone' ] = user.get_profile().phone
               initial[ 'email' ] = user.email
           else:
               # this can't be overridden.

               data = data.copy()
               data['email'] = user.email
               
       super(ReportUpdateForm,self).__init__(data,files=files, initial=initial)
       
       if self.user and not data:
            self.fields['email'].widget.attrs['readonly'] = 'readonly'
    
       if first_update:
           del(self.fields['is_fixed'])
       else:
            self.fields['is_fixed'] = forms.fields.BooleanField(required=False,
                                         help_text=_('This problem has been fixed.'),
                                         label='')
              
    def save(self,commit=True):
       update = super(ReportUpdateForm,self).save( commit = False )
       if self.report:
           update.report = self.report
           
       update.first_update = self.first_update
       if self.user:
           #update.user = self.user
           update.is_confirmed = True
       if commit:
           update.save()
           if update.is_confirmed:
               update.notify()
       return( update )
           
    def as_table(self):
        "over-ridden to get rid of <br/> in help_text_html. "
        return self._html_output(
            normal_row = u'<tr%(html_class_attr)s><th>%(label)s</th><td>%(errors)s%(field)s%(help_text)s</td></tr>',
            error_row = u'<tr><td colspan="2">%s</td></tr>',
            row_ender = u'</td></tr>',
            help_text_html = u'<span class="helptext">%s</span>',
            errors_on_separate_row = False)
    
 
            
class ReportForm(forms.ModelForm):
    """
    ReportForm --
    combines is_valid(), clean(), and save()
    etc. for both an update form and a report form

    (information for both models is submitted at
    the same time when a report is initially created)
    """

    class Meta:
        model = Report
        fields = ('lat','lon','title', 'address', 'category','photo')

    lat = forms.fields.CharField(widget=forms.widgets.HiddenInput)
    lon = forms.fields.CharField(widget=forms.widgets.HiddenInput)

    def __init__(self,data=None,files=None,initial=None,user=None):
        if data:
            d2p = DictToPoint(data,exceptclass=None)
        else:
            d2p = DictToPoint(initial,exceptclass=None)
        
        self.pnt = d2p.pnt()
        self.ward = d2p.ward()
        self.update_form = ReportUpdateForm(data=data,initial=initial,user=user,first_update = True)
        super(ReportForm,self).__init__(data,files, initial=initial)
        self.fields['category'] = CategoryChoiceField(self.ward)
    
    def clean(self):
        if self.pnt and not self.ward:
            raise forms.ValidationError("lat/lon not supported")

        # Always return the full collection of cleaned data.
        return self.cleaned_data

    def is_valid(self):
        report_valid = super(ReportForm,self).is_valid()
        update_valid = self.update_form.is_valid()
        return( update_valid and report_valid )
    
    def save(self):
        
        report = super(ReportForm,self).save( commit = False )
        update = self.update_form.save(commit=False)
        
        #these are in the form for 'update'
        report.desc = update.desc
        report.author = update.author
        
        #this info is custom
        report.point = self.pnt
        report.ward = self.ward
        #report.user = update.user            

        report.save()
        update.report = report
        update.save()
        
        if update.is_confirmed:
            update.notify()
        
        return( report )
    
    def all_errors(self):
        "returns errors for both report and update forms"
        errors = {}
        for key,value in self.errors.items():
            errors[key] = value.as_text()[2:] 

        # add errors from the update form to the end.
        for key,value in self.update_form.errors.items():
            errors[key] = value.as_text()[2:] 
            
        return( errors )
    
from social_auth.backends import get_backend


class FMSNewRegistrationForm(RegistrationForm):

    username = forms.CharField(widget=forms.widgets.HiddenInput,required=False)
    phone = forms.CharField(max_length=100,
                           widget=forms.TextInput(attrs={ 'class': 'required' }),
                           label=_('Phone'))
    first_name = forms.CharField(max_length=100,
                           widget=forms.TextInput(attrs={ 'class': 'required' }),
                           label=_('First Name'))
    last_name = forms.CharField(max_length=100,
                           widget=forms.TextInput(attrs={ 'class': 'required' }),
                           label=_('Last Name'))

    def __init__(self, *args, **kw):
        super(FMSNewRegistrationForm, self).__init__(*args, **kw)
        self.fields.keyOrder = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'password1',
            'password2',
            'username' ]

    
    def save(self, profile_callback=None):
        username = self.cleaned_data.get('username',None)
        
        if username:
            # flag that there's an existing user created by 
            # social_auth.
            new_user = User.objects.get(username=username)
        else:
            # otherwise, normal registration.
            # look for a user with the same email.
            if User.objects.filter(email=self.cleaned_data.get('email')):
                new_user = User.objects.get(email=self.cleaned_data.get('email'))
            else:
                new_user = RegistrationProfile.objects.create_inactive_user(username=self.cleaned_data['email'],
                                                                    password=self.cleaned_data['password1'],
                                                                    email=self.cleaned_data['email'],
                                                                    send_email=False )        
        new_user.first_name = self.cleaned_data.get('first_name','')
        new_user.last_name = self.cleaned_data.get('last_name','')
        new_user.email = self.cleaned_data.get('email')
        new_user.set_password(self.cleaned_data.get('password1'))
        new_user.username = self.cleaned_data.get('email')
                    
        new_user.save()

        user_profile, g_or_c = UserProfile.objects.get_or_create(user=new_user)
        user_profile.phone = self.cleaned_data.get('phone','')
        user_profile.save()

        if not new_user.is_active:
            self.send_email(new_user)
            
        return( new_user )
    
    def clean_username(self):
        return self.cleaned_data['username']
    
    def clean_email(self):
        if User.objects.filter(email=self.cleaned_data['email'],is_active=True).count() != 0:
            raise forms.ValidationError(_(u'That email is already in use.'))    
        return self.cleaned_data['email']
    
    def send_email(self,new_user):
        registration_profile = RegistrationProfile.objects.get(user=new_user)
            
        subject = render_to_string('registration/activation_email_subject.txt',
                                   )
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
            
        message = render_to_string('registration/activation_email.txt',
                                       { 'user': new_user,
                                         'activation_link': "%s/accounts/activate/%s/" %(settings.SITE_URL,registration_profile.activation_key),
                                         'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS })
            
        new_user.email_user(subject, message, settings.EMAIL_FROM_USER)


# just override the AuthenticationForm username so that it's label
# says 'email'

class FMSAuthenticationForm(AuthenticationForm):
    """
    Base class for authenticating users. Extend this to get a form that accepts
    username/password logins.
    """
    username = forms.CharField(label=_("Email"), max_length=30)


  
########NEW FILE########
__FILENAME__ = create_cityadmin
from mainapp.models import CityAdmin, City
from optparse import make_option
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand,CommandError

class Command(BaseCommand):
    help = 'Create a city administrator user'
    option_list = BaseCommand.option_list + (
        make_option('--city', '-c', dest='city',help='city'),
        make_option('--userid', '-u', dest='userid',help='userid'),
        make_option('--pwd', '-p', dest='password',help='password'),
        make_option('--email', '-e', dest='email',help='email'),
    )

    def handle(self, *args, **options):
        for option in self.option_list:
            if not options.has_key(option.dest):
                raise CommandError("%s must be specified" % (option.dest))
        city = City.objects.get(name=options['city'])
        user = CityAdmin.objects.create_user(options['userid'], options['email'], city, options['password'] )
        if not user:
            print "error creating user"
########NEW FILE########
__FILENAME__ = export_email_rules
from mainapp.models import City,EmailRule
from optparse import make_option
import csv
from django.core.management.base import BaseCommand,CommandError

class Command(BaseCommand):
    help = 'Export email rules for particular city/cities'
    option_list = BaseCommand.option_list + (
        make_option('--city', '-c', dest='city',help='cityname[,cityname]'),
        make_option('--file', '-f', dest='file',help='name of output file'),

    )

    def handle(self, *args, **options):
        if not options.has_key('file'):
            raise CommandError("An output filename must be specified with -f=")
        if not options.has_key('city'):
            raise CommandError("At least one city must be specified with -c=")
        
        file = open(options['file'],'w')
        
        for city_name in options['city'].split(','):
            try:
                city = City.objects.get(name=city_name)
            except:
                raise CommandError("city %s not found in database."% city_name)
            
            rules = EmailRule.objects.filter(city=city)
            for rule in rules:
                file.write(str(rule) + "\n")
        
        file.close()
########NEW FILE########
__FILENAME__ = export_ward_info
from mainapp.models import Ward,City,Councillor
from optparse import make_option
from django.core.management.base import BaseCommand,CommandError
from unicodewriter import UnicodeWriter


class Command(BaseCommand):
    help = 'Export ward names and councillors in a CVS format for a given city'
    option_list = BaseCommand.option_list + (
        make_option('--city', '-c', dest='city',help='cityname[,cityname]'),
        make_option('--file', '-f', dest='file',help='name of output file'),

    )

    def handle(self, *args, **options):
        if not options.has_key('file'):
            raise CommandError("An output filename must be specified with -f=")
        if not options.has_key('city'):
            raise CommandError("At least one city must be specified with -c=")

        file = open(options['file'],'w')
        csv = UnicodeWriter(file)
        
        for city_name in options['city'].split(','):
            print city_name
            city = City.objects.get(name=city_name)
            wards = Ward.objects.filter(city=city)
            for ward in wards:
                row = [ city.name, ward.name, ward.councillor.first_name, ward.councillor.last_name, ward.councillor.email]
                csv.writerow(row)


########NEW FILE########
__FILENAME__ = resend_report
from mainapp.models import Report,ReportUpdate
from optparse import make_option
import csv
from django.core.management.base import BaseCommand,CommandError

class Command(BaseCommand):
    help = 'Resend original notification email for a particular report'
    args = 'report_id'

    def handle(self, *args, **options):
        if len(args) == 0:
            raise CommandError("a report ID must be supplied")
        report_id = args[0]
        try:
            report = Report.objects.get(id=report_id)
        except Exception,e:
            raise CommandError("there is no report with id %s in the database." % report_id )
        report.first_update().notify_on_new()
        
########NEW FILE########
__FILENAME__ = stats
import datetime
from mainapp.models import Report,ReportUpdate
from django.core.management.base import NoArgsCommand,CommandError

class StatBase(object):
    
    def results(self):
        pass
    
    def add_report(self,report):
        pass
    
class Stat(StatBase):
    """ Base class for discrete statistics """
    
    # a commonly used constant.
    MAX_NUM_DAYS = 9999
    

    def __init__(self,name):
        self.name = name
        self.count = 0
        
    def get_fix_time(self,report):
        """ a commonly used computation """
        if (not report.is_fixed) or (report.fixed_at == None):
            raise Exception("report is not fixed")
        return( report.fixed_at - report.created_at )
    
    def get_open_time(self,report):
        if report.is_fixed:
            return( self.get_fix_time(report))
        else:
            return( self.get_report_age(report))
                    
    def get_report_age(self, report):
        now = datetime.datetime.now()
        return( now - report.created_at )
    
    def labels(self):
        return( [ self.name ])
    
class StatColGroup(StatBase):
    def __init__(self, stats = []):
        self.stats = stats
        
    def labels(self):
        labels = []
        for stat in self.stats:
            for label in stat.labels():
                labels.append( label )
        return( labels )
    
    def result(self):
        row = []
        for stat in self.stats:
            row.append( stat.result() )
        return( [ row ] )
        
    def add_report(self,report):
        for stat in self.stats:
            stat.add_report(report)
        
    
class StatRowGroup(StatBase):
    def __init__(self,name,newstat_fcn):
        self.name = name
        self.newstat_fcn = newstat_fcn
        self.stat_group = {}
        self.stat_group['All'] = newstat_fcn()

    def labels(self):
        labels = self.stat_group['All'].labels()
        labels.insert(0,self.name)
        return( labels )
    
    def get_group_key(self, report):
        return( None )
 
    def add_report(self,report):
        key = self.get_group_key( report )
        if not self.stat_group.has_key(key):
            self.stat_group[key] = self.newstat_fcn()
        stat = self.stat_group[key]
        stat.add_report(report)
        self.stat_group['All'].add_report(report)
        
    def result(self):
        rows = []
        for key in self.stat_group.keys():
            key_rows = self.stat_group[key].result()
            for row in key_rows:
                row.insert(0,key)
                rows.append(row)

        return( rows )

    
class CityStatRows(StatRowGroup):
    def __init__(self,newstat_fcn):
        super(CityStatRows,self).__init__('City',newstat_fcn)
    
    def get_group_key(self,report):
        return( report.ward.city.name )

class CategoryGroupStatRows(StatRowGroup):
    def __init__(self,newstat_fcn):
        super(CategoryGroupStatRows,self).__init__('Category Group',newstat_fcn)
    
    def get_group_key(self,report):
        return( report.category.category_class.name_en )
            
class CategoryStatRows(StatRowGroup):
    def __init__(self,newstat_fcn):
        super(CategoryStatRows,self).__init__('Category',newstat_fcn)
    
    def get_group_key(self,report):
        return( report.category.name_en )
    
class AvgTimeToFix(Stat):  
    def __init__(self):
        super(AvgTimeToFix,self).__init__("Time To Fix")
        self.total = 0
        
    def add_report(self,report):
        if not report.is_fixed:
            return
        fix_time = self.get_fix_time(report)
        self.total += fix_time.days
        self.count += 1

    def result(self):
        if self.count == 0:
            return 0
        return( self.total / self.count )

class CountReportsWithStatusOnDay(Stat):
    
    OPEN = True
    FIXED = False
    
    def __init__(self, day = 0,status = OPEN ):
        
        if status == CountReportsWithStatusOnDay.OPEN:
            desc = "Open"
        else:
            desc = "Fixed"
        
        name = "Total %s On Day %d" % (desc, day )
            
        super(CountReportsWithStatusOnDay,self).__init__(name)
        self.status = status
        self.day = day
        
    def add_report(self,report):
 
        # is this report too young to be counted in this time span?
        if self.get_report_age(report).days < self.day:
            return

        # how long was this report open for?
        open_time = self.get_open_time(report).days

        if self.status == CountReportsWithStatusOnDay.OPEN:
            # was this report open on the given day?
            if open_time >= self.day:
                self.count +=1
        else:
            # looking to count fixed reports only
            if report.is_fixed:
                # was this report fixed by the given day?
                if open_time < self.day:
                    self.count +=1    

    def result(self):
        return( self.count )
    
    
class PercentFixedInDays(Stat):
        
    def __init__(self,min_num_days = 0,max_num_days = Stat.MAX_NUM_DAYS):
        if max_num_days == Stat.MAX_NUM_DAYS:
            name = "Fixed After %d Days" % ( min_num_days )
        else:
            name = "Fixed in %d-%d Days" % (min_num_days, max_num_days)
            
        super(PercentFixedInDays,self).__init__(name)
        self.total_fixed_in_period = 0
        self.min_num_days = min_num_days
        self.max_num_days = max_num_days
        
    def add_report(self,report):
        self.count += 1

        if not report.is_fixed:
            return
        fix_days = self.get_fix_time(report).days
        if fix_days < self.min_num_days:
            return
        if fix_days >= self.max_num_days:
            return
        
        self.total_fixed_in_period += 1    

    def result(self):
        if self.count == 0:
            return 0
        return( float(self.total_fixed_in_period) / self.count )
    

class PercentFixed(Stat):
    def __init__(self, name = "Percent Fixed", fixed_value = True):
        super(PercentFixed,self).__init__(name)
        self.total = 0
        self.fixed_value = fixed_value

    def add_report(self,report):
        self.count += 1
        if  report.is_fixed != self.fixed_value:
            return
        self.total += 1

    def result(self):
        if self.count == 0:
            return 0
        return( float(self.total) / self.count )

class PercentUnfixed(PercentFixed):
    
    def __init__(self):
        super(PercentUnfixed,self).__init__("Percent Unfixed",False)


class NumReports(Stat):

    def __init__(self):
        super(NumReports,self).__init__("Total Reports")

    def add_report(self,report):
        self.count += 1

    def result(self):
        return( self.count )
    
    
"""
    Define a series of statistics for a report.
"""
    
class ReportStatCols(StatColGroup):
    
    def __init__(self):
        stats = []
        stats.append(NumReports())
        stats.append(AvgTimeToFix())
        stats.append(PercentFixed())
        stats.append(PercentUnfixed())
        stats.append(PercentFixedInDays(0,7))
        stats.append(PercentFixedInDays(7,30))
        stats.append(PercentFixedInDays(30,60))
        stats.append(PercentFixedInDays(60,180))
        stats.append(PercentFixedInDays(180,PercentFixedInDays.MAX_NUM_DAYS))
        stats.append(CountReportsWithStatusOnDay(7, CountReportsWithStatusOnDay.OPEN))
        stats.append(CountReportsWithStatusOnDay(30, CountReportsWithStatusOnDay.OPEN))
        stats.append(CountReportsWithStatusOnDay(60, CountReportsWithStatusOnDay.OPEN))
        stats.append(CountReportsWithStatusOnDay(180, CountReportsWithStatusOnDay.OPEN))
        stats.append(CountReportsWithStatusOnDay(7, CountReportsWithStatusOnDay.FIXED))
        stats.append(CountReportsWithStatusOnDay(30, CountReportsWithStatusOnDay.FIXED))
        stats.append(CountReportsWithStatusOnDay(60, CountReportsWithStatusOnDay.FIXED))
        stats.append(CountReportsWithStatusOnDay(180, CountReportsWithStatusOnDay.FIXED))
        super(ReportStatCols,self).__init__(stats=stats)

"""
    Define a series of ways of breaking down the report statistics --
    eg. by city, by category group, by category
"""
class ReportRowGroup1(CategoryStatRows):
    def __init__(self):
        super(ReportRowGroup1,self).__init__(ReportStatCols)

class ReportRowGroup2(CategoryGroupStatRows):
    def __init__(self):
        super(ReportRowGroup2,self).__init__(ReportRowGroup1)
        
class ReportRowGroup3(CityStatRows):
    def __init__(self):
        super(ReportRowGroup3,self).__init__(ReportRowGroup2)
        
class Command(NoArgsCommand):
    help = 'Get Time To Fix Statistics'

    def handle_noargs(self, **options):
        stat_group = ReportRowGroup3()
        reports = Report.objects.filter(is_confirmed=True)
        for report in reports:
            stat_group.add_report(report)
        
        results = stat_group.result()
        print ",".join(stat_group.labels())
        for result_row in results:
            str_row = []
            for result in result_row:
                str_row.append(str(result))
            print ",".join(str_row)

########NEW FILE########
__FILENAME__ = sync_councillors
from mainapp.models import City,Ward,Councillor
from django.core.management.base import BaseCommand,CommandError

class Command(BaseCommand):
    help = 'Add \'city\' link to councillors in database, get rid of unlinked councillors'

    def handle(self, *args, **options):
        for councillor in Councillor.objects.all():
            # do we have a ward for this councillor?
            try:
                ward = Ward.objects.get(councillor=councillor)
                councillor.city = ward.city
                councillor.save()
                print "saving councillor %s %s (%s)" % (councillor.first_name,councillor.last_name,ward.city)
            except:
                print "deleting councillor %s %s" % (councillor.first_name,councillor.last_name)
                councillor.delete()
########NEW FILE########
__FILENAME__ = unicodewriter
import csv


class UnicodeWriter:
    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        self.writer = csv.writer(f, dialect=dialect, **kwds)
        self.encoding = encoding

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

########NEW FILE########
__FILENAME__ = post_syncdb


########NEW FILE########
__FILENAME__ = SSLMiddleware
"""
SSL Middleware
Stephen Zabel

This middleware answers the problem of redirecting to (and from) a SSL secured path
by stating what paths should be secured in urls.py file. To secure a path, add the
additional view_kwarg 'SSL':True to the view_kwargs.

For example

urlpatterns = patterns('some_site.some_app.views',
    (r'^test/secure/$','test_secure',{'SSL':True}),
     )

All paths where 'SSL':False or where the kwarg of 'SSL' is not specified are routed
to an unsecure path.

For example

urlpatterns = patterns('some_site.some_app.views',
    (r'^test/unsecure1/$','test_unsecure',{'SSL':False}),
    (r'^test/unsecure2/$','test_unsecure'),
     )

Gotcha's : Redirects should only occur during GETs; this is due to the fact that
POST data will get lost in the redirect.

A major benefit of this approach is that it allows you to secure django.contrib views
and generic views without having to modify the base code or wrapping the view.

This method is also better than the two alternative approaches of adding to the
settings file or using a decorator.

It is better than the tactic of creating a list of paths to secure in the settings
file, because you DRY. You are also not forced to consider all paths in a single
location. Instead you can address the security of a path in the urls file that it
is resolved in.

It is better than the tactic of using a @secure or @unsecure decorator, because
it prevents decorator build up on your view methods. Having a bunch of decorators
makes views cumbersome to read and looks pretty redundant. Also because the all
views pass through the middleware you can specify the only secure paths and the
remaining paths can be assumed to be unsecure and handled by the middleware.

This package is inspired by Antonio Cavedoni's SSL Middleware
"""

__license__ = "Python"
__copyright__ = "Copyright (C) 2007, Stephen Zabel"
__author__ = "Stephen Zabel"


from django.conf import settings
from django.http import HttpResponseRedirect, get_host

SSL = 'SSL'

class SSLRedirect:
    def process_view(self, request, view_func, view_args, view_kwargs):
        if SSL in view_kwargs:
            # FMS modification: open311 requires SSL only on 
            # post for 'requests' url.  
            # In that case, SSL is set as ['POST'],
            # instead of True/False
            if getattr(view_kwargs[SSL],'__iter__',False):
                secure = request.method in view_kwargs[SSL]
            else:
                secure = view_kwargs[SSL]

            del view_kwargs[SSL]
        else:
            secure = False

        if not settings.DEBUG and secure and not request.is_secure():
            return self._redirect(request, secure)

    def _redirect(self, request, secure):
        protocol = secure and "https" or "http"
        newurl = "%s://%s%s" % (protocol,
										  get_host(request),
										  request.get_full_path())

        if settings.DEBUG and request.method == 'POST':
            raise RuntimeError, \
"""Django can't perform a SSL redirect while maintaining POST data.
Please structure your views so that redirects only occur during GETs."""
        
        return HttpResponseRedirect(newurl)

########NEW FILE########
__FILENAME__ = subdomains
"""
    Subdomain middleware from here:
    http://thingsilearned.com/2009/01/05/using-subdomains-in-django/
    
    NOTE: there may be login issues across sub-domains when user
    logins are supported
"""

class SubdomainMiddleware:
        def process_request(self, request):
            """Parse out the subdomain from the request"""
            request.subdomain = None
            host = request.META.get('HTTP_HOST', '')
            host_s = host.replace('www.', '').split('.')
            if len(host_s) > 2:
                request.subdomain = ''.join(host_s[:-2])
########NEW FILE########
__FILENAME__ = models

from django.db import models, connection
from django.contrib.gis.db import models
from django.contrib.gis.maps.google import GoogleMap, GMarker, GEvent, GPolygon, GIcon
from django.template.loader import render_to_string
from fixmystreet import settings
from django import forms
from django.core.mail import send_mail, EmailMessage
import md5
import urllib
import time
import datetime
from mainapp import emailrules
from datetime import datetime as dt
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy, ugettext as _
from transmeta import TransMeta
from stdimage import StdImageField
from django.utils.encoding import iri_to_uri
from django.template.defaultfilters import slugify
from django.contrib.gis.geos import fromstr
from django.http import Http404
from django.contrib.auth.models import User,Group,Permission
from registration.models import RegistrationProfile 
      
# from here: http://www.djangosnippets.org/snippets/630/        
class CCEmailMessage(EmailMessage):
    def __init__(self, subject='', body='', from_email=None, to=None, cc=None,
                 bcc=None, connection=None, attachments=None, headers=None):
        super(CCEmailMessage, self).__init__(subject, body, from_email, to,
                                           bcc, connection, attachments, headers)
        if cc:
            self.cc = list(cc)
        else:
            self.cc = []

    def recipients(self):
        """
        Returns a list of all recipients of the email
        """
        return super(CCEmailMessage, self).recipients() + self.cc 

    def message(self):
        msg = super(CCEmailMessage, self).message()
        if self.cc:
            msg['Cc'] = ', '.join(self.cc)
        return msg

class ReportCategoryClass(models.Model):
    __metaclass__ = TransMeta

    name = models.CharField(max_length=100)

    def __unicode__(self):      
        return self.name

    class Meta:
        db_table = u'report_category_classes'
        translate = ('name', )
    
class ReportCategory(models.Model):
    __metaclass__ = TransMeta

    name = models.CharField(max_length=100)
    hint = models.TextField(blank=True, null=True)
    category_class = models.ForeignKey(ReportCategoryClass)
  
    def __unicode__(self):      
        return self.category_class.name + ":" + self.name
 
    class Meta:
        db_table = u'report_categories'
        translate = ('name', 'hint', )

class ReportCategorySet(models.Model):
    ''' A category group for a particular city '''
    name = models.CharField(max_length=100)
    categories = models.ManyToManyField(ReportCategory)

    def __unicode__(self):      
        return self.name
                 
class Province(models.Model):
    name = models.CharField(max_length=100)
    abbrev = models.CharField(max_length=3)

    class Meta:
        db_table = u'province'
    
class City(models.Model):
    province = models.ForeignKey(Province)
    name = models.CharField(max_length=100)
    # the city's 311 email, if it has one.
    email = models.EmailField(blank=True, null=True)    
    category_set = models.ForeignKey(ReportCategorySet, null=True, blank=True)
    objects = models.GeoManager()

    slug = models.CharField(max_length=100, unique=True, blank=True)

    def __unicode__(self):      
        return self.name
    
    def get_categories(self):
        if self.category_set:
            categories = self.category_set.categories
        else:
            # the 'Default' group is defined in fixtures/initial_data
            default = ReportCategorySet.objects.get(name='Default')
            categories = default.categories
        categories = categories.order_by('category_class')
        return( categories )
    
    def get_absolute_url(self):
        return "/cities/%s/" % (self.slug )
    
    def feed_url(self):
        return ('/feeds/cities/%s.rss' % ( self.slug) )


    def get_rule_descriptions(self):
        rules = EmailRule.objects.filter(city=self)
        describer = emailrules.EmailRulesDesciber(rules,self)
        return( describer.values() )

    def save(self):
        if not self.slug:
            self.slug = slugify(self.name + '-' + self.province.abbrev.lower() )
        super(City,self).save()
        
    class Meta:
        db_table = u'cities'

class Councillor(models.Model):

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    
    # this email addr. is the destination for reports
    # if the 'Councillor' email rule is enabled
    email = models.EmailField(blank=True, null=True)
    city = models.ForeignKey(City,null=True)

    def __unicode__(self):      
        return self.first_name + " " + self.last_name

    class Meta:
        db_table = u'councillors'


        
class Ward(models.Model):
    
    name = models.CharField(max_length=100)
    number = models.IntegerField()
    councillor = models.ForeignKey(Councillor,null=True,blank=True)
    city = models.ForeignKey(City)
    geom = models.MultiPolygonField( null=True)
    objects = models.GeoManager()
    
    # this email addr. is the destination for reports
    # if the 'Ward' email rule is enabled
    email = models.EmailField(blank=True, null=True)

    # lookup used in URL
    slug = models.CharField(max_length=100, blank=True)

    def get_absolute_url(self):
        return( "/cities/%s/wards/%s/" %( self.city.slug, self.slug ))
        
    def feed_url(self):
        return ('/feeds/cities/%s/wards/%s.rss' % ( self.city.slug, self.slug ))

    def save(self):
        if not self.slug:
            self.slug = slugify( self.name )
        super(Ward,self).save()

    def __unicode__(self):      
        return self.name + ", " + self.city.name  

    # return a list of email addresses to send new problems in this ward to.
    def get_emails(self,report):
        to_emails = []
        cc_emails = []
        if self.city.email:
            to_emails.append(self.city.email)
            
        # check for rules for this city.
        rules = EmailRule.objects.filter(city=self.city)
        for rule in rules:
            rule_email = rule.get_email(report)
            if rule_email:
               if not rule.is_cc: 
                   to_emails.append(rule_email)
               else:
                   cc_emails.append(rule_email)
        return( to_emails,cc_emails )

    
    def get_rule_descriptions(self):
        rules = EmailRule.objects.filter(city=self.city)
        describer = emailrules.EmailRulesDesciber(rules,self.city, self)
        return( describer.values() )
            

    class Meta:
        db_table = u'wards'

    
            
# Override where to send a report for a given city.        
#
# If no rule exists, the email destination is the 311 email address 
# for that city.
#
# Cities can have more than one rule.  If a given report matches more than
# one rule, more than one email is sent.  (Desired behaviour for cities that 
# want councillors CC'd)

class EmailRule(models.Model):
    
    TO_COUNCILLOR = 0
    MATCHING_CATEGORY_CLASS = 1
    NOT_MATCHING_CATEGORY_CLASS = 2
    TO_WARD = 3
    
    RuleChoices = [   
    (TO_COUNCILLOR, 'Send Reports to Councillor Email Address'),
    (MATCHING_CATEGORY_CLASS, 'Send Reports Matching Category Group (eg. Parks) To This Email'),
    (NOT_MATCHING_CATEGORY_CLASS, 'Send Reports Not Matching Category Group To This Email'), 
    (TO_WARD, 'Send Reports to Ward Email Address'),]
    
    RuleBehavior = { TO_COUNCILLOR: emailrules.ToCouncillor,
                     MATCHING_CATEGORY_CLASS: emailrules.MatchingCategoryClass,
                     NOT_MATCHING_CATEGORY_CLASS: emailrules.NotMatchingCategoryClass,
                     TO_WARD: emailrules.ToWard }
    
    rule = models.IntegerField(choices=RuleChoices)
    
    # is this a 'to' email or a 'cc' email
    is_cc = models.BooleanField(default=False,
            help_text="Set to true to include address in 'cc' list"

            )

    # the city this rule applies to 
    city = models.ForeignKey(City)    
    
    # filled in if this is a category class rule
    category_class = models.ForeignKey(ReportCategoryClass,null=True, blank=True,
                          verbose_name = 'Category Group',
                          help_text="Only set for 'Category Group' rule types."
                          )
    
    # filled in if this is a category rule
    #category = models.ForeignKey(ReportCategory,null=True, blank=True,
    #                    help_text="Set to send all "
    #                     )
    
    # filled in if an additional email address is required for the rule type
    email = models.EmailField(blank=True, null=True,
                        help_text="Only set for 'Category Group' rule types."
                        )
    
    def label(self):
        rule_behavior = EmailRule.RuleBehavior[ self.rule ]()
        return( rule_behavior.report_group(self) )
    
    def value(self, ward = None):
        rule_behavior = EmailRule.RuleBehavior[ self.rule ]()
        if ward:
            return( rule_behavior.value_for_ward(self,ward) )
        else:
            return( rule_behavior.value_for_city(self))
        
    def get_email(self,report):
        rule_behavior = EmailRule.RuleBehavior[ self.rule ]()
        return( rule_behavior.get_email(report,self))
    
    def __str__(self):
        rule_behavior = EmailRule.RuleBehavior[ self.rule ]()
        if self.is_cc:
            prefix = "CC:"
        else:
            prefix = "TO:"
        return( "%s - %s (%s)" % (self.city.name,rule_behavior.describe(self),prefix) )
        
class ApiKey(models.Model):
    
    WIDGET = 0
    MOBILE = 1
    
    TypeChoices = [
    (WIDGET, 'Embedded Widget'),
    (MOBILE, 'Mobile'), ]
    
    organization = models.CharField(max_length=255)
    key = models.CharField(max_length=100)
    type = models.IntegerField(choices=TypeChoices)
    contact_email = models.EmailField()
    approved = models.BooleanField(default=False)
    
    def save(self):
        if not self.key or self.key == "":
            m = md5.new()
            m.update(self.contact_email)
            m.update(str(time.time()))
            self.confirm_token = m.hexdigest()
        super(ApiKey,self).save()
        
    def __unicode__(self):
        return( str(self.organization) )

class Report(models.Model):
    title = models.CharField(max_length=100, verbose_name = ugettext_lazy("Subject"))
    category = models.ForeignKey(ReportCategory,null=True)
    ward = models.ForeignKey(Ward,null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # last time report was updated
    updated_at = models.DateTimeField(auto_now_add=True)
    
    # time report was marked as 'fixed'
    fixed_at = models.DateTimeField(null=True)
    is_fixed = models.BooleanField(default=False)
    is_hate = models.BooleanField(default=False)
    
    # last time report was sent to city
    sent_at = models.DateTimeField(null=True)
    
    # email where the report was sent
    email_sent_to = models.EmailField(null=True)
    
    # last time a reminder was sent to the person that filed the report.
    reminded_at = models.DateTimeField(auto_now_add=True)
    
    point = models.PointField(null=True)
    photo = StdImageField(upload_to="photos", blank=True, verbose_name =  ugettext_lazy("* Photo"), size=(400, 400), thumbnail_size=(133,100))
    desc = models.TextField(blank=True, null=True, verbose_name = ugettext_lazy("Details"))
    author = models.CharField(max_length=255,verbose_name = ugettext_lazy("Name"))
    address = models.CharField(max_length=255,verbose_name = ugettext_lazy("Location"))

    # true if first update has been confirmed - redundant with
    # one in ReportUpdate, but makes aggregate SQL queries easier.
    
    is_confirmed = models.BooleanField(default=False)

    # what API did the report come in on?
    api_key = models.ForeignKey(ApiKey,null=True,blank=True)
    
    # this this report come in from a particular mobile app?
    device_id = models.CharField(max_length=100,null=True,blank=True)
    
    # who filed this report?
    objects = models.GeoManager()
    
    def is_subscribed(self, email):
        if len( self.reportsubscriber_set.filter(email=email)) != 0:
            return( True )
        return( self.first_update().email == email )
    
    def sent_at_diff(self):
        if not self.sent_at:
            return( None )
        else:
            return(  self.sent_at - self.created_at )

    def first_update(self):
        return( ReportUpdate.objects.get(report=self,first_update=True))

    def get_absolute_url(self):
        return  "/reports/" + str(self.id)
            
    class Meta:
        db_table = u'reports'
        

class ReportUpdate(models.Model):   
    report = models.ForeignKey(Report)
    desc = models.TextField(blank=True, null=True, verbose_name = ugettext_lazy("Details"))
    created_at = models.DateTimeField(auto_now_add=True)
    is_confirmed = models.BooleanField(default=False)
    is_fixed = models.BooleanField(default=False)
    confirm_token = models.CharField(max_length=255, null=True)
    email = models.EmailField(max_length=255, verbose_name = ugettext_lazy("Email"))
    author = models.CharField(max_length=255,verbose_name = ugettext_lazy("Name"))
    phone = models.CharField(max_length=255, verbose_name = ugettext_lazy("Phone"), blank=True,null=True )
    first_update = models.BooleanField(default=False)
    
    def notify(self):
        """
        Tell whoever cares that there's been an update to this report.
         -  If it's the first update, tell city officials
         -  Anything after that, tell subscribers
        """
        if self.first_update:
            self.notify_on_new()
        else:
            self.notify_on_update()
            
    def notify_on_new(self):
        # send to the city immediately.           
        subject = render_to_string("emails/send_report_to_city/subject.txt", {'update': self })
        message = render_to_string("emails/send_report_to_city/message.txt", { 'update': self, 'SITE_URL':settings.SITE_URL })
        
        to_email_addrs,cc_email_addrs = self.report.ward.get_emails(self.report)
        email_msg = CCEmailMessage(subject,message,settings.EMAIL_FROM_USER, 
                        to_email_addrs, cc_email_addrs,headers = {'Reply-To': self.email })
        if self.report.photo:
            email_msg.attach_file( self.report.photo.file.name )
        
        email_msg.send()

        # update report to show time sent to city.
        self.report.sent_at=dt.now()
        email_addr_str = ""
        for email in to_email_addrs:
            if email_addr_str != "":
                email_addr_str += ", "
            email_addr_str += email
            
        self.report.email_sent_to = email_addr_str
        self.report.save()
        
    
    def notify_on_update(self):
        subject = render_to_string("emails/report_update/subject.txt", 
                    { 'update': self })
        
        # tell our subscribers there was an update.
        for subscriber in self.report.reportsubscriber_set.all():
            unsubscribe_url = settings.SITE_URL + "/reports/subscribers/unsubscribe/" + subscriber.confirm_token
            message = render_to_string("emails/report_update/message.txt", 
               { 'update': self, 'unsubscribe_url': unsubscribe_url })
            send_mail(subject, message, 
               settings.EMAIL_FROM_USER,[subscriber.email], fail_silently=False)

        # tell the original problem reporter there was an update
        message = render_to_string("emails/report_update/message.txt", 
                    { 'update': self })
        send_mail(subject, message, 
              settings.EMAIL_FROM_USER,
              [self.report.first_update().email],  fail_silently=False)

            
    def save(self):
        # does this update require confirmation?
        if not self.is_confirmed:
            self.get_confirmation()
            super(ReportUpdate,self).save()
        else:
            # update parent report
            if not self.created_at: 
                self.created_at = datetime.datetime.now()
            if self.is_fixed:
                self.report.is_fixed = True
                self.report.fixed_at = self.created_at   
            # we track a last updated time in the report to make statistics 
            # (such as on the front page) easier.  
            if not self.first_update:
                self.report.updated_at = self.created_at
            else:
                self.report.updated_at = self.report.created_at
                self.report.is_confirmed = True
            super(ReportUpdate,self).save()
            self.report.save()

    def confirm(self):    
        self.is_confirmed = True
        self.save()
        self.notify()

            
    def get_confirmation(self):
        """ Send a confirmation email to the user. """        
        if not self.confirm_token or self.confirm_token == "":
            m = md5.new()
            m.update(self.email)
            m.update(str(time.time()))
            self.confirm_token = m.hexdigest()
            confirm_url = settings.SITE_URL + "/reports/updates/confirm/" + self.confirm_token
            message = render_to_string("emails/confirm/message.txt", 
                    { 'confirm_url': confirm_url, 'update': self })
            subject = render_to_string("emails/confirm/subject.txt", 
                    {  'update': self })
            send_mail(subject, message, 
                   settings.EMAIL_FROM_USER,[self.email], fail_silently=False)
            
        super(ReportUpdate, self).save()
    
    def title(self):
        if self.first_update :
            return self.report.title
        if self.is_fixed:
            return "Reported Fixed"
        return("Update")
        
    class Meta:
        db_table = u'report_updates'

class ReportSubscriber(models.Model):
    """ 
        Report Subscribers are notified when there's an update to an existing report.
    """
    
    report = models.ForeignKey(Report)    
    confirm_token = models.CharField(max_length=255, null=True)
    is_confirmed = models.BooleanField(default=False)    
    email = models.EmailField()
    
    class Meta:
        db_table = u'report_subscribers'

    
    def save(self):
        if not self.confirm_token or self.confirm_token == "":
            m = md5.new()
            m.update(self.email)
            m.update(str(time.time()))
            self.confirm_token = m.hexdigest()
        if not self.is_confirmed:
            confirm_url = settings.SITE_URL + "/reports/subscribers/confirm/" + self.confirm_token
            message = render_to_string("emails/subscribe/message.txt", 
                    { 'confirm_url': confirm_url, 'subscriber': self })
            send_mail('Subscribe to FixMyStreet.ca Report Updates', message, 
                   settings.EMAIL_FROM_USER,[self.email], fail_silently=False)
        super(ReportSubscriber, self).save()

 
class ReportMarker(GMarker):
    """
        A marker for an existing report.  Override the GMarker class to 
        add a numbered, coloured marker.
        
        If the report is fixed, show a green marker, otherwise red.
    """
    def __init__(self, report, icon_number ):
        if report.is_fixed:
            color = 'green'
        else:
            color = 'red'
        icon_number = icon_number
        img = "/media/images/marker/%s/marker%s.png" %( color, icon_number )
        name = 'letteredIcon%s' %( icon_number )      
        icon = GIcon(name,image=img,iconsize=(20,34))
        GMarker.__init__(self,geom=(report.point.x,report.point.y), title=report.title.replace('"',"'"), icon=icon)

    def __unicode__(self):
        "The string representation is the JavaScript API call."
        return mark_safe('GMarker(%s)' % ( self.js_params))

    
class FixMyStreetMap(GoogleMap):  
    """
        Overrides the GoogleMap class that comes with GeoDjango.  Optionally,
        show nearby reports.
    """
    def __init__(self,pnt,draggable=False,nearby_reports = [] ):  
#        self.icons = []
        markers = []
        marker = GMarker(geom=(pnt.x,pnt.y), draggable=draggable)
        if draggable:
            event = GEvent('dragend',
                           'function() { reverse_geocode (geodjango.map_canvas_marker1.getPoint()); }')        
            marker.add_event(event)
        markers.append(marker)
        
        for i in range( len( nearby_reports ) ):
            nearby_marker = ReportMarker(nearby_reports[i], str(i+1) )
            markers.append(nearby_marker)

        GoogleMap.__init__(self,center=(pnt.x,pnt.y),zoom=17,key=settings.GMAP_KEY, markers=markers, dom_id='map_canvas')

class WardMap(GoogleMap):
    """ 
        Show a single ward as a gmap overlay.  Optionally, show reports in the
        ward.
    """
    def __init__(self,ward, reports = []):
        polygons = []
        for poly in ward.geom:
                polygons.append( GPolygon( poly ) )
        markers = []
        for i in range( len( reports ) ):
            marker = ReportMarker(reports[i], str(i+1) )
            markers.append(marker)

        GoogleMap.__init__(self,zoom=13,markers=markers,key=settings.GMAP_KEY, polygons=polygons, dom_id='map_canvas')

           

class CityMap(GoogleMap):
    """
        Show all wards in a city as overlays.  Used when debugging maps for new cities.
    """
    
    def __init__(self,city):
        polygons = []
        ward = Ward.objects.filter(city=city)[:1][0]
        for ward in Ward.objects.filter(city=city):
            for poly in ward.geom:
                polygons.append( GPolygon( poly ) )
        GoogleMap.__init__(self,center=ward.geom.centroid,zoom=13,key=settings.GMAP_KEY, polygons=polygons,dom_id='map_canvas')
    

    
class CountIf(models.sql.aggregates.Aggregate):
    # take advantage of django 1.3 aggregate functionality
    # from discussion here: http://groups.google.com/group/django-users/browse_thread/thread/bd5a6b329b009cfa
    sql_function = 'COUNT'
    sql_template= '%(function)s(CASE %(condition)s WHEN true THEN 1 ELSE NULL END)'
    
    def __init__(self, lookup, **extra):
        self.lookup = lookup
        self.extra = extra

    def _default_alias(self):
        return '%s__%s' % (self.lookup, self.__class__.__name__.lower())
    default_alias = property(_default_alias)

    def add_to_query(self, query, alias, col, source, is_summary):
        super(CountIf, self).__init__(col, source, is_summary, **self.extra)
        query.aggregate_select[alias] = self
            
        
class ReportCounter(CountIf):
    """ initialize an aggregate with one of 5 typical report queries """

    CONDITIONS = {
        'recent_new' : "age(clock_timestamp(), reports.created_at) < interval '%s' and reports.is_confirmed = True",
        'recent_fixed' : "age(clock_timestamp(), reports.fixed_at) < interval '%s' AND reports.is_fixed = True",
        'recent_updated': "age(clock_timestamp(), reports.updated_at) < interval '%s' AND reports.is_fixed = False and reports.updated_at != reports.created_at",
        'old_fixed' : "age(clock_timestamp(), reports.fixed_at) > interval '%s' AND reports.is_fixed = True",
        'old_unfixed' : "age(clock_timestamp(), reports.created_at) > interval '%s' AND reports.is_confirmed = True AND reports.is_fixed = False"  
                }
    
    def __init__(self, col, key, interval ):
        super(ReportCounter,self).__init__( col, condition=self.CONDITIONS[ key ] % ( interval ) )
         
        
class ReportCounters(dict):
    """ create a dict of typical report count aggregators. """    
    def __init__(self,report_col, interval = '1 Month'):
        super(ReportCounters,self).__init__()
        for key in ReportCounter.CONDITIONS.keys():
            self[key] = ReportCounter(report_col,key,interval)
    
class OverallReportCount(dict):
    """ this query needs some intervention """
    def __init__(self, interval ):
        super(OverallReportCount,self).__init__()
        q = Report.objects.annotate(**ReportCounters('id', interval ) ).values('recent_new','recent_fixed','recent_updated')
        q.query.group_by = []
        self.update( q[0] )

class FaqEntry(models.Model):
    __metaclass__ = TransMeta

    q = models.CharField(max_length=100)
    a = models.TextField(blank=True, null=True)
    slug = models.SlugField(null=True, blank=True)
    order = models.IntegerField(null=True, blank=True)
    
    def save(self):
        super(FaqEntry, self).save()
        if self.order == None: 
            self.order = self.id + 1
            super(FaqEntry, self).save()
    
    class Meta:
        db_table = u'faq_entries'
        translate = ('q', 'a', )
       

class FaqMgr(object):
        
    def incr_order(self, faq_entry ):
        if faq_entry.order == 1:
            return
        other = FaqEntry.objects.get(order=faq_entry.order-1)
        swap_order(other[0],faq_entry)
    
    def decr_order(self, faq_entry): 
        other = FaqEntry.objects.filter(order=faq_entry.order+1)
        if len(other) == 0:
            return
        swap_order(other[0],faq_entry)
        
    def swap_order(self, entry1, entry2 ):
        entry1.order = entry2.order
        entry2.order = entry1.order
        entry1.save()
        entry2.save()
 

class PollingStation(models.Model):
    """
    This is a temporary object.  Sometimes, we get maps in the form of
    polling stations, which have to be combined into wards.
    """
    number = models.IntegerField()
    station_name = models.CharField(max_length=100, null=True)
    ward_number = models.IntegerField()
    city = models.ForeignKey(City)
    geom = models.MultiPolygonField( null=True)
    objects = models.GeoManager()

    class Meta:
        db_table = u'polling_stations'
 
 
class UserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)
    
    # if user is a 'city admin' (is_staff=True),
    # this field lists all cities the user 
    # can edit through the admin 
    # panel.  
    
    cities = models.ManyToManyField(City, null=True,blank=True)
    
    # fields for 'non-admin' users:
    phone = models.CharField(max_length=255, verbose_name = ugettext_lazy("Phone"), null=True, blank=True )
    
    
    def __unicode__(self):
        return self.user.username

    
class FMSUserManager(models.Manager):   
    '''
    FMSUser and FMSUserManager integrate
    with django-social-auth and django-registration
    '''     
    def create_user(self, username, email, password=None):
        user = RegistrationProfile.objects.create_inactive_user(username,password,email,send_email=False)

        if user:
            UserProfile.objects.get_or_create(user=user)
            return FMSUser.objects.get(username=user.username)
        else:
             return( None )
     
class FMSUser(User):
    '''
    FMSUser and FMSUserManager integrate
    with django-social-auth and django-registration
    '''     
    class Meta:
        proxy = True

    objects = FMSUserManager()
    

class CityAdminManager(models.Manager):    
    PERMISSION_NAMES = [ 'Can change ward', 
                     'Can add email rule',
                     'Can change email rule',
                     'Can delete email rule',
                     'Can add councillor',
                     'Can change councillor',
                     'Can delete councillor' ]

    GROUP_NAME = 'CityAdmins'
    
    def get_group(self):
        if Group.objects.filter(name=self.GROUP_NAME).exists():
            return Group.objects.get(name=self.GROUP_NAME)
        else:
            group = Group.objects.create(name=self.GROUP_NAME)        
            for name in self.PERMISSION_NAMES:
                permission = Permission.objects.get(name=name)
                group.permissions.add(permission)
            group.save()
            return group
    
    
    def create_user(self, username, email, city, password=None):
        group = self.get_group()
        user = User.objects.create_user(username, email, password )
        user.is_staff = True
        user.groups.add(group)
        user.save()
        profile = UserProfile(user=user)
        profile.save()
        profile.cities.add(city)
        profile.save()
        return user
        
class CityAdmin(User):
    '''
        An admin user who can edit ward data for a city.
    '''     
    class Meta:
        proxy = True

    objects = CityAdminManager()
    
    

    
        
class DictToPoint():
    ''' Helper class '''
    def __init__(self, dict, exceptclass = Http404 ):
        if exceptclass and not dict.has_key('lat') or not dict.has_key('lon'):
            raise exceptclass
        
        self.lat = dict.get('lat',None)
        self.lon = dict.get('lon',None)
        self._pnt = None
        
    def __unicode__(self):
        return ("POINT(" + self.lon + " " + self.lat + ")" )
    
    def pnt(self, srid = None ):
        if self._pnt:
            return self._pnt
        if not self.lat or not self.lon:
            return None
        pntstr = self.__unicode__()
        self._pnt = fromstr( pntstr, srid=4326) 
        return self._pnt
    
    def ward(self):
        pnt = self.pnt()
        if not pnt:
            return None
        wards = Ward.objects.filter(geom__contains=pnt)[:1]
        if wards:
            return(wards[0])
        else:
            return(None)

    
    

########NEW FILE########
__FILENAME__ = search

########NEW FILE########
__FILENAME__ = tags
from django import template
register = template.Library()

MENU_DEFS = { 'submit' : { 'exact': [ '/','/reports/new', '/search' ], 
                           'startswith':[],  
                           'exclude' : []
                         },
              'view' : { 'exact': [],
                         'startswith' : [ '/cities','/wards', '/reports' ],
                         'exclude':[ '/reports/new' ] 
                         },
               'myreports' : {  'exact' :  [],
                              'startswith' : [ '/accounts' ],
                              'exclude' : []  },
                    
              
            }

def is_match( path, pattern ):
    if MENU_DEFS.has_key(pattern):
        menudef = MENU_DEFS[pattern]
        if path in menudef[ 'exact' ]:
            return True
        for match in menudef['startswith']:
            if path.startswith(match) and not path in menudef['exclude']:
                   return True
        return False 
    if path.startswith(pattern):
        return True
    return False
    
@register.simple_tag
def fmsmenu_active(request, pattern ):
    if is_match(request.path, pattern ):
        return 'active'
    return ''



########NEW FILE########
__FILENAME__ = account
from django.test import TestCase
from django.test.client import Client
from django.core import mail
from mainapp.models import UserProfile,Report,ReportUpdate,ReportSubscriber
from django.db import connection
from django.contrib.auth.models import User
from django.core import mail
from django.conf import settings


class TestAccountHome(TestCase):
    fixtures = ['test_accounts.json']

    def test_user1(self):
        """ 
            user 1 has:
            -- created reports 1 and 2
            -- updated reports 2 and 3
            -- subscribed to report 4
        """
         
        c = Client()
        r = c.login(username='user1',password='user1')
        self.assertEqual(r,True)
        r = c.get('/accounts/home/',follow=True)
        self.assertEqual(r.status_code,200)
        self.assertEqual(len(r.context['reports']),4)
        # check report 4
        self.assertEqual(r.context['reports'][0].id,4)
        self.assertEqual(r.context['reports'][0].is_reporter,False)
        self.assertEqual(r.context['reports'][0].is_updater,False)
        # check report 3
        self.assertEqual(r.context['reports'][1].id,3)
        self.assertEqual(r.context['reports'][1].is_reporter,False)
        self.assertEqual(r.context['reports'][1].is_updater,True)

        # check report 2
        self.assertEqual(r.context['reports'][2].id,2)
        self.assertEqual(r.context['reports'][2].is_reporter,True)
        self.assertEqual(r.context['reports'][2].is_updater,True)
        # check report 1
        self.assertEqual(r.context['reports'][3].id,1)
        self.assertEqual(r.context['reports'][3].is_reporter,True)
        self.assertEqual(r.context['reports'][3].is_updater,False)
        
        
                         

    def test_user2(self):
        """ 
            user 2 has:
            -- created report 3
            -- updated report 1
            -- not subscribed to any report
        """
         
        c = Client()
        r = c.login(username='user2',password='user2')
        self.assertEqual(r,True)
        r = c.get('/accounts/home/',follow=True)
        self.assertEqual(r.status_code,200)

        self.assertEqual(len(r.context['reports']),2)

        # check report 3
        self.assertEqual(r.context['reports'][0].id,3)
        self.assertEqual(r.context['reports'][0].is_reporter,True)
        self.assertEqual(r.context['reports'][0].is_updater,False)

        # check report 1
        self.assertEqual(r.context['reports'][1].id,1)
        self.assertEqual(r.context['reports'][1].is_reporter,False)
        self.assertEqual(r.context['reports'][1].is_updater,True)


CREATE_PARAMS =  { 'title': 'A report created when logged in', 
                     'lat': '45.4043333270000034',
                     'lon': '-75.6870889663999975',
                     'category': 5,
                     'desc': 'The description',
                     'address': 'Some street',
                } 


UPDATE_PARAMS = { 'author': 'Clark Kent',
                  'email': 'user1@test.com',
                  'desc': 'Report 4 has been fixed',
                  'phone': '555-111-1111',
                  'is_fixed': True }

class TestLoggedInUser(TestCase):
    fixtures = ['test_accounts.json']
        
    def test_report_form(self):
        # check that default values are already filled in.
        c = Client()
        r = c.login(username='user1',password='user1')
        self.assertEquals(r, True)
        url = '/reports/?lat=%s;lon=%s' % (CREATE_PARAMS['lat'],CREATE_PARAMS['lon'] )
        r = c.get( url )
        self.assertEquals( r.status_code, 200 )
        self.assertContains(r,"Clark Kent")
        self.assertContains(r,"user1@test.com")
        self.assertContains(r,"555-111-1111")
        # check that default values are not filled in
        # for a second, anonymous user (problem in the field)
        c2 = Client()
        r = c2.get( url )
        self.assertEquals( r.status_code, 200 )
        self.assertNotContains(r,"Clark Kent")
        self.assertNotContains(r,"user1@test.com")
        self.assertNotContains(r,"555-111-1111")
        
    def test_report_submit(self):
        params = CREATE_PARAMS.copy()
        params['author' ] = "Clark Kent"
        params['email'] = 'user1@test.com'
        params['phone'] = '555-111-1111'

        c = Client()
        r = c.login(username='user1',password='user1')
        
        # starting conditions
        self.assertEqual(Report.objects.filter(title=CREATE_PARAMS['title']).count(), 0 )
        self.assertEquals(len(mail.outbox), 0)
        self.assertEqual(ReportUpdate.objects.filter(author="Clark Kent",email='user1@test.com',desc=params['desc']).count(),0)

        # file the report
        response = c.post('/reports/', params, follow=True )
        self.assertEquals( response.status_code, 200 )
        self.assertEquals(response.template[0].name, 'reports/show.html')
        
        # there's a new report
        self.assertEqual(Report.objects.filter(title=CREATE_PARAMS['title'],is_confirmed=True,is_fixed=False).count(), 1 )
        self.assertEqual(ReportUpdate.objects.filter(author="Clark Kent",email='user1@test.com',desc=params['desc'],is_confirmed=True).count(),1)
                         
        # email should be sent directly to the city
        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].to, [u'example_city_email@yahoo.ca'])

        
    def test_update_form(self):
        # check that default values are already filled in.
        c = Client()
        r = c.login(username='user1',password='user1')
        url = '/reports/4' 
        r = c.get( url )
        self.assertEquals( r.status_code, 200 )
        self.assertContains(r,"Clark Kent")
        self.assertContains(r,"user1@test.com")
        self.assertContains(r,"555-111-1111")

        # check that default values are NOT already filled in.
        # for a second client (problem in the field)
        c2 = Client()
        r = c2.get( url )
        self.assertEquals( r.status_code, 200 )
        self.assertNotContains(r,"Clark Kent")
        self.assertNotContains(r,"user1@test.com")
        self.assertNotContains(r,"555-111-1111")

        
    def test_update_submit(self):
        c = Client()
        r = c.login(username='user1',password='user1')
        
        # starting conditions
        self.assertEquals(len(mail.outbox), 0)
        self.assertEqual(ReportUpdate.objects.filter(author="Clark Kent",email='user1@test.com',desc=UPDATE_PARAMS['desc']).count(),0)

        # file the report
        response = c.post('/reports/4/updates/', UPDATE_PARAMS, follow=True )
        self.assertEquals( response.status_code, 200 )
        
        # there's a new update
        self.assertEqual(ReportUpdate.objects.filter(report__id=4,author="Clark Kent",email='user1@test.com',desc=UPDATE_PARAMS['desc'],is_fixed=True,is_confirmed=True).count(),1)
        self.assertEqual(Report.objects.filter(id=4,is_fixed=True).count(),1)
        
        # we're redirected to the report page
        self.assertEquals(response.template[0].name, 'reports/show.html')
        # and it has our update on it.
        self.assertContains(response,UPDATE_PARAMS['desc'])
        
        # update emails go out to reporter and everyone who has subscribed.
        # in this case, 'nooneimportant@test.com', and ourselves.
        
        self.assertEquals(len(mail.outbox), 2)
        self.assertEquals(mail.outbox[0].to,[u'user1@test.com'])
        self.assertEquals(mail.outbox[1].to,[u"noone_important@test.com"])
        
    def test_subscribe_form(self):
        # check that default values are already filled in.
        c = Client()
        r = c.login(username='user2',password='user2')
        r = c.get( '/reports/4/subscribers' )
        self.assertEquals( r.status_code, 200 )
        self.assertContains(r,"user2@test.com")
        c2 = Client()
        r = c2.get( '/reports/4/subscribers' )
        self.assertEquals( r.status_code, 200 )
        self.assertNotContains(r,"user2@test.com")

        
    def test_subscribe_submit(self):
        c = Client()
        r = c.login(username='user2',password='user2')
        
        # test starting conditions.
        self.assertEquals( ReportSubscriber.objects.filter(email='user2@test.com',report=4).count(),0)
        
        response = c.post('/reports/4/subscribers/', 
                               { 'email': 'user2@test.com'} , follow=True )
        
        self.assertEquals( response.status_code, 200 )
        self.assertEquals(response.template[0].name, 'reports/subscribers/create.html')
        
        # a confirmed subscriber should be created
        # no confirmation email should be sent
        self.assertEquals( ReportSubscriber.objects.filter(email='user2@test.com',report=4, is_confirmed=True).count(),1)
        self.assertEquals(len(mail.outbox), 0)
        
from registration.models import RegistrationProfile
from social_auth.models import UserSocialAuth

EMAIL='lala@test.com'
FNAME = 'fname'
LNAME = 'lname'
UID = '12345'
PHONE = '858-555-1212'
UPDATE_PHONE = '999-777-5555'
PASSWORD = 'pwd1'
SOCIAL_COMPLETE_URL_W_EMAIL ='/accounts/complete/dummy/?email=%s&first_name=%s&last_name=%s&uid=%s' % (  EMAIL, FNAME, LNAME, UID )
SOCIAL_COMPLETE_URL_NO_EMAIL ='/accounts/complete/dummy/?first_name=%s&last_name=%s&uid=%s' % (  FNAME, LNAME, UID )

# does not contain a UID.
SOCIAL_COMPLETE_URL_W_ERROR ='/accounts/complete/dummy/?first_name=%s&last_name=%s' % ( FNAME, LNAME )
        

REGISTER_POST = { 
                  'email': EMAIL,
                  'first_name':FNAME,
                  'last_name':LNAME,
                  'phone': PHONE,
                  'password1': 'pwd1',
                  'password2': 'pwd1'
                  }


class TestRegistration(TestCase):
    fixtures = []

    def setUp(self):
        self.curr_auth = settings.AUTHENTICATION_BACKENDS
        settings.AUTHENTICATION_BACKENDS += ('mainapp.tests.testsocial_auth.dummy_socialauth.DummyBackend',)

    def tearDown(self):
        """Restores settings to avoid breaking other tests."""
        settings.AUTHENTICATION_BACKENDS = self.curr_auth

    def test_socialuth_registration_w_noemail(self):
        # starting conditions        
        self.assertEquals(User.objects.filter(first_name=FNAME).count(),0)

        c = Client()
        response = self._do_social_auth(c,SOCIAL_COMPLETE_URL_NO_EMAIL)

        # calling the same URL twice doesn't make two sets.
        self._do_social_auth(c, SOCIAL_COMPLETE_URL_NO_EMAIL)
        
        # complete the registration.
        self._register(c)
        self._activate()
        self._login(c)
    
    def test_socialuth_registration_w_email(self):
        ''' As above, but user has email field set --
            should show up user model, and registraton form.
        '''
        # starting conditions
        self.assertEquals(User.objects.filter(email=EMAIL).count(),0)

        c = Client()
        response = self._do_social_auth(c, SOCIAL_COMPLETE_URL_W_EMAIL)

        # check that our user model has the email.
        self.assertEquals(User.objects.filter(email=EMAIL,first_name=FNAME,last_name=LNAME,is_active=False).count(),1)
        
        # check that email is in the form
        self.assertContains( response, EMAIL )

        # check that calling the same URL twice doesn't make 
        # two profiles.        

        self._do_social_auth(c, SOCIAL_COMPLETE_URL_W_EMAIL)

        # complete registration and get going.
        
        self._register(c)
        self._activate()
        self._login(c)

        
    def test_social_auth_login(self):
        c = Client()
        
        self._do_social_auth(c,SOCIAL_COMPLETE_URL_W_EMAIL)
        self._register(c)

        # activate the user.
        self._activate()
        
        # now, do social auth completion again.  are we logged in?        
        response = c.get(SOCIAL_COMPLETE_URL_W_EMAIL,follow=True)  
        self.assertEquals(response.status_code, 200 )
        self.assertEquals(response.templates[0].name, 'account/home.html')

    
    def test_normal_register(self):        
        # starting conditions
        self.assertEquals(User.objects.filter(first_name=FNAME).count(),0)

        c = Client()
        self._register(c,social_auth=False)
        self._activate()
        self._login(c)
        
    def test_edit(self):
        c = Client()
        self._register(c,social_auth=False)
        self._activate()
        self._login(c)

        # test we get the edit form
        response = c.get('/accounts/edit/',follow=True)        
        self.assertEquals(response.status_code, 200 )
        self.assertEquals(response.templates[0].name, 'account/edit.html')
        self.assertContains(response,'Editing User Profile For %s %s' % ( FNAME, LNAME ))
        self.assertContains(response,PHONE)
        
        # test submitting an updated phone #
        response = c.post( '/accounts/edit/', data={ 'phone': UPDATE_PHONE, 'first_name':FNAME, 'last_name':LNAME }, follow=True, **{ "wsgi.url_scheme" : "https" })
        self.assertEquals(response.status_code, 200 )
        self.assertEquals(response.templates[0].name, 'account/home.html')
        self.assertEquals(UserProfile.objects.filter(user__first_name=FNAME,phone=UPDATE_PHONE).count(),1)
        self.assertEquals(UserProfile.objects.filter(user__first_name=FNAME,phone=PHONE).count(),0)
        
    def test_social_auth_error(self):
        c = Client()
        response = c.get(SOCIAL_COMPLETE_URL_W_ERROR,follow=True)
        self.assertEquals(response.templates[0].name, 'registration/error.html')
        self.assertContains(response,'Missing user id')
        
    def test_normal_register_after_social_auth(self):
        c = Client()
        self._do_social_auth(c,SOCIAL_COMPLETE_URL_W_EMAIL)
        self._register(c)

        # activate the user.
        self._activate()
        
        # Empty the test outbox
        mail.outbox = []
        
        post_data = REGISTER_POST.copy()       
        response = c.post( '/accounts/register/', data=post_data, follow=True)

        #we should end up with an error
        self.assertEquals(response.status_code, 200 )
        self.assertEquals(response.templates[0].name, 'registration/registration_form.html')

    
    def _do_social_auth(self,c,url):
        response = c.get(url,follow=True)
        # we should be redirected to the registration form
        self.assertEquals( response.status_code, 200 )
        self.assertEquals(response.templates[0].name, 'registration/registration_form.html')

        # check that we've made the right models
        self.assertEquals(User.objects.filter(first_name=FNAME,last_name=LNAME,is_active=False).count(),1)
        self.assertEquals(RegistrationProfile.objects.filter(user__first_name=FNAME).count(),1)
        self.assertEquals(UserSocialAuth.objects.filter(user__first_name=FNAME,provider='dummy',uid=UID).count(),1)
        self.assertEquals(UserProfile.objects.filter(user__first_name=FNAME).count(),1)

        user = User.objects.get(first_name=FNAME)

        # make sure the form contains our defaults.
        self.assertContains( response, FNAME )
        self.assertContains( response, LNAME )
        self.assertContains( response, user.username )

        return response
    
    def _register(self, c, social_auth = True, dest= 'registration/registration_complete.html', active=False,email_expected = True):
        self.assertEquals(len(mail.outbox), 0)
        post_data = REGISTER_POST.copy()
        
        if social_auth:
            user = User.objects.get(first_name=FNAME)        
            post_data[ 'username' ] = user.username
        
        response = c.post( '/accounts/register/', data=post_data, follow=True, **{ "wsgi.url_scheme" : "https" })
        self.assertEquals(response.status_code, 200 )
        self.assertEquals(response.templates[0].name, dest)

        # check that the right models are updated
        self.assertEquals(User.objects.filter(first_name=FNAME,last_name=LNAME,email=EMAIL,username=EMAIL,is_active=active).count(),1)
        self.assertEquals(RegistrationProfile.objects.filter(user__first_name=FNAME).count(),1)
        self.assertEquals(UserProfile.objects.filter(user__first_name=FNAME,phone=PHONE).count(),1)
           
        if email_expected:
            # check that we've sent out an email
            self.assertEquals(len(mail.outbox), 1)
            self.assertEquals(mail.outbox[0].to,[EMAIL])
        else:
            self.assertEquals(len(mail.outbox), 0)
            
        return response
    
    def _activate(self):
        user = User.objects.get(first_name = FNAME)
        user.is_active = True
        user.save()
        
    def _login(self,c):
        rc = c.login(username=EMAIL,password=PASSWORD)
        self.assertEquals(rc, True)


########NEW FILE########
__FILENAME__ = base_cases
from django.test import TestCase
from django.test.client import Client
from django.core import mail
from mainapp.models import Report,ReportUpdate,ReportSubscriber,City, \
    ReportCategory, ReportCategorySet, ReportCategoryClass
import settings
import re


CREATE_PARAMS =  { 'title': 'A report from our API', 
                     'lat': '45.4043333270000034',
                     'lon': '-75.6870889663999975',
                     'address': 'Some Street',
                     'category': 5,
                     'desc': 'The description',
                     'author': 'John Farmer',
                     'email': 'testcreator@hotmail.com',
                     'phone': '514-513-0475' } 

UPDATE_PARAMS = { 'author': 'John Farmer',
                      'email': 'testupdater@hotmail.com',
                      'desc': 'This problem has been fixed',
                      'phone': '514-513-0475',
                      'is_fixed': True }

class BaseCase(TestCase):
    """
        Some helper functions for our test base cases.
    """
    c = Client()

    
    def _get_confirm_url(self, email ):
        m = re.search( 'http://localhost:\d+(\S+)', email.body )
        self.assertNotEquals(m,None)
        self.assertEquals(len(m.groups()),1)
        return( str(m.group(1)))

    
class CreateReport(BaseCase):
    """
        Run through our regular report/submit/confirm/update-is-fixed/confirm
        lifecycle to make sure there's no issues, and the right
        emails are being sent.
    """

    def test(self):
        response = self.c.post('/reports/', CREATE_PARAMS, follow=True )
        self.assertEquals( response.status_code, 200 )
        self.assertEquals(response.template[0].name, 'reports/show.html')
        self.assertEqual(Report.objects.filter(title=CREATE_PARAMS['title'],is_confirmed=False).count(), 1,"There's a new unconfirmed report." )
        self.assertEqual(ReportUpdate.objects.filter(report__title=CREATE_PARAMS['title'],is_confirmed=False,first_update=True).count(), 1,"There's an unconfirmed report update." )
        
        # a confirmation email should be sent to the user
        self.assertEquals(len(mail.outbox), 1, "a confirmation email was sent.")
        self.assertEquals(mail.outbox[0].to, [u'testcreator@hotmail.com'])
        
        #test confirmation link
        confirm_url = self._get_confirm_url(mail.outbox[0])
        response = self.c.get(confirm_url, follow=True)
        self.assertEquals( response.status_code, 200 )
        self.assertEqual(Report.objects.filter(title=CREATE_PARAMS['title'],is_confirmed=True).count(), 1,"The report is confirmed." )


        #now there should be two emails in our outbox
        self.assertEquals(len(mail.outbox), 2)
        self.assertEquals(mail.outbox[1].to, [u'example_city_email@yahoo.ca'])

        #now submit a 'fixed' update.
        report = Report.objects.get(title=CREATE_PARAMS['title'])
        self.assertEquals( ReportUpdate.objects.filter(report=report).count(),1)
        update_url = report.get_absolute_url() + "/updates/"
        response = self.c.post(update_url,UPDATE_PARAMS, follow=True)
        self.assertEquals( response.status_code, 200 )
        self.assertEquals( ReportUpdate.objects.filter(report=report).count(),2)
        self.assertEquals( ReportUpdate.objects.filter( report=report, is_confirmed=True).count(),1)
        # we should have sent another confirmation link
        self.assertEquals(len(mail.outbox), 3)
        self.assertEquals(mail.outbox[2].to, [u'testupdater@hotmail.com'])

        #confirm the update
        confirm_url = self._get_confirm_url(mail.outbox[2])
        response = self.c.get(confirm_url, follow=True)
        self.assertEquals( response.status_code, 200 )
        self.assertEquals( ReportUpdate.objects.filter( report=report, is_confirmed=True).count(),2)
        self.assertContains(response, UPDATE_PARAMS['desc'])
        #make sure the creator of the report gets an update.
        self.assertEquals(len(mail.outbox), 4)
        self.assertEquals(mail.outbox[3].to, [u'testcreator@hotmail.com'])


class Subscribe(BaseCase):
    """
       Test subscribing and unsubscribing from a report     
    """

    #    this fixture has one fixed report (id=1), and one unfixed (id=2).
    fixtures = ['test_report_basecases.json']

    def test(self):
        response = self.c.post('/reports/2/subscribers/', 
                               { 'email': 'subscriber@test.com'} , follow=True )
        self.assertEquals( response.status_code, 200 )
        self.assertEquals(response.template[0].name, 'reports/subscribers/create.html')
        
        # an unconfirmed subscriber should be created, and an email sent.
        self.assertEquals( ReportSubscriber.objects.count(),1)
        self.assertEquals( ReportSubscriber.objects.get(email='subscriber@test.com').is_confirmed,False )
        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].to, [u'subscriber@test.com'])
        
        #confirm the subscriber
        confirm_url = self._get_confirm_url(mail.outbox[0])
        response = self.c.get(confirm_url, follow=True)
        self.assertEquals( response.status_code, 200 )

        #subscriber should now be confirmed
        self.assertEquals( ReportSubscriber.objects.get(email='subscriber@test.com').is_confirmed,True )

        # updating the report should send emails to report author, 
        # as well as all subscribers. 

        # -- send the update
        response = self.c.post('/reports/2/updates/',UPDATE_PARAMS, follow=True)
        self.assertEquals( response.status_code, 200 )
        self.assertEquals(len(mail.outbox), 2)

        # -- confirm the update
        confirm_url = self._get_confirm_url(mail.outbox[1])
        response = self.c.get(confirm_url, follow=True)
        self.assertEquals( response.status_code, 200 )

        # check that the right ppl got emails
        self.assertEquals(len(mail.outbox), 4)
        self.assertEquals(mail.outbox[2].to, [u'subscriber@test.com'])
        self.assertEquals(mail.outbox[3].to, [u'reportcreator@test.com'])
        
        # test that the subscribed user can unsubscribe with the link provided.
        unsubscribe_url = self._get_unsubscribe_url(mail.outbox[2])
        response = self.c.get(unsubscribe_url, follow=True)
        self.assertEquals( response.status_code, 200 )
        self.assertEquals( ReportSubscriber.objects.count(),0)
        
    def _get_unsubscribe_url(self,email):
        m = re.search( 'http://localhost:\d+(/reports/subscribers\S+)', email.body )
        self.assertNotEquals(m,None)
        self.assertEquals(len(m.groups()),1)
        return( str(m.group(1)))
    

"""
   Test that flagging a report sends the admin an email     
"""
class FlagReport(BaseCase):

    """ 
        this fixture has one fixed report (id=1), and one unfixed (id=2).
    """
    fixtures = ['test_report_basecases.json']
    
    def test(self):
        report = Report.objects.get(pk=2)
        flag_url = report.get_absolute_url() + "/flags/"
        response = self.c.post(flag_url,{}, follow=True)
        self.assertEquals( response.status_code, 200 )
        self.assertEquals( response.template[0].name, 'reports/flags/thanks.html')

        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].to, [settings.ADMIN_EMAIL])
 
    def _get_error_response(self,query):
        " check we always end up on the home page "
        response = self.c.get(self._url(query), follow=True)
        self.assertEquals( response.status_code, 200 )
        self.assertEquals( response.template[0].name, 'home.html')
        return response
    
    def _url(self,query_str):
        return( self.base_url + "?q=" + query_str )
    


class ChangeCategorySet(BaseCase):  
    
    def test(self):
        city = City.objects.get(name='Oglo')
        category_title = 'A brand new category'
        category_class = ReportCategoryClass.objects.get(name_en='Parks')
        newcategory = ReportCategory.objects.create(name_en=category_title,category_class=category_class)
        newset = ReportCategorySet.objects.create(name='newset')
        newset.categories.add(newcategory)
        newset.save()
        city.category_set = newset
        city.save()
        
        response = self.c.get('/reports/new?&lat=45.4169416715279&lon=-75.70075750350952')
        self.assertContains(response,category_title)      
    

########NEW FILE########
__FILENAME__ = emailrules
"""
"""

from django.test import TestCase
from mainapp.models import Report,ReportUpdate,EmailRule, City, Ward,ReportCategory,ReportCategoryClass
from mainapp.emailrules import EmailRuleDescriber



class EmailRuleTestBase(TestCase):
    fixtures = ['test_email_rules.json']
    
    def setUp(self):
        # these are from the fixtures file.
        self.test_categoryclass = ReportCategoryClass.objects.get(name_en='Parks')
        self.test_category = ReportCategory.objects.get(name_en='Broken or Damaged Equipment/Play Structures')
        self.not_test_category = ReportCategory.objects.get(name_en='Damaged Curb')

        self.test_city = City.objects.get(name='TestCityWithoutEmail')
        self.test_ward = Ward.objects.get(name = 'WardInCityWithNo311Email')
        self.test_report = Report(ward=self.test_ward,category=self.test_category)
    
class TestNoRules(EmailRuleTestBase):
        
    def test(self):
        self.failUnlessEqual( self.test_ward.get_emails(self.test_report), ([],[]) )


class TestNoRulesWCityEmail(EmailRuleTestBase):

    def test(self):
        ward_w_email = Ward.objects.get(name='WardInCityWith311Email')
        self.failUnlessEqual( ward_w_email.get_emails(self.test_report),([ ward_w_email.city.email ],[]) )

class TestToCouncillor(EmailRuleTestBase):

    def test(self):
        rule = EmailRule( rule=EmailRule.TO_COUNCILLOR, city = self.test_city )
        rule.save()
        self.failUnlessEqual( self.test_ward.get_emails(self.test_report), ([self.test_report.ward.councillor.email],[]) )
        

class TestToWardAddress(EmailRuleTestBase):

    def test(self):
        email = 'ward_email@yahoo.ca'
        rule = EmailRule( rule=EmailRule.TO_WARD, city = self.test_city )
        rule.save()
        self.test_ward.councillor = None
        self.test_ward.email = email
        self.test_ward.save()
        self.failUnlessEqual( self.test_ward.get_emails(self.test_report), ([email],[]) )


class TestMatchingCategoryClass(EmailRuleTestBase):

    def test(self):
        email = 'parks@city.ca'
        rule = EmailRule( rule=EmailRule.MATCHING_CATEGORY_CLASS, city = self.test_city, category_class = self.test_categoryclass, email=email )
        rule.save()
        self.failUnlessEqual( self.test_ward.get_emails(self.test_report), ([email],[]) )
        report2 = Report(ward=self.test_ward,category=self.not_test_category)
        self.failUnlessEqual( self.test_ward.get_emails(report2), ([],[]) )
        

class TestNotMatchingCategoryClass(EmailRuleTestBase):

    def test(self):
        email = 'parks@city.ca'
        rule = EmailRule( rule=EmailRule.NOT_MATCHING_CATEGORY_CLASS, city = self.test_city, category_class = self.test_categoryclass, email=email )
        rule.save()
        self.failUnlessEqual( self.test_ward.get_emails(self.test_report), ([],[]) )
        report2 = Report(ward=self.test_ward,category=self.not_test_category)
        self.failUnlessEqual( self.test_ward.get_emails(report2), ([email],[]) )
        
        
class TestCharlottetownRules(EmailRuleTestBase):

    def test(self):

        # simulate Charlottetown's somewhat complicated cases:
        # 
        # For all categories except Parks, send email to  not_parks1@city.com  and  not_parks2@city.com
        # with a Cc: to not_parks_cc@city.com  and  the ward councillor.
        #
        # For the category of Parks, send email to:  parks@city.com
        # with a Cc: to  parks_cc@city.com  and  the ward councillor   
        #
        parks_category = ReportCategory.objects.get(name_en='Lights Malfunctioning in Park')
        not_parks_category = ReportCategory.objects.get(name_en='Damaged Curb')
        parks_category_class = ReportCategoryClass.objects.get(name_en='Parks')
        
        # always CC the councillor
        EmailRule( is_cc=True, rule=EmailRule.TO_COUNCILLOR, city = self.test_city ).save()
        
        # parks rules
        EmailRule(rule=EmailRule.MATCHING_CATEGORY_CLASS, city =self.test_city, category_class = parks_category_class, email='parks@city.com' ).save()
        EmailRule(rule=EmailRule.MATCHING_CATEGORY_CLASS, city =self.test_city, category_class = parks_category_class, email='parks_cc@city.com', is_cc=True ).save()

        # not parks rules
        EmailRule( rule=EmailRule.NOT_MATCHING_CATEGORY_CLASS, city = self.test_city, category_class = parks_category_class, email='not_parks1@city.com' ).save()
        EmailRule( rule=EmailRule.NOT_MATCHING_CATEGORY_CLASS, city = self.test_city, category_class = parks_category_class, email='not_parks2@city.com' ).save()
        EmailRule( rule=EmailRule.NOT_MATCHING_CATEGORY_CLASS, city = self.test_city, category_class = parks_category_class, email='not_parks_cc@city.com', is_cc=True ).save()
        
        parks_report = Report(ward=self.test_ward,category = parks_category )
        self.failUnlessEqual( self.test_ward.get_emails(parks_report), ([ u'parks@city.com' ],[u"councillor_email@testward1.com", u'parks_cc@city.com'] ))
        
        not_parks_report = Report(ward=self.test_ward,category = not_parks_category )
        self.failUnlessEqual( self.test_ward.get_emails(not_parks_report), ([ u'not_parks1@city.com',u'not_parks2@city.com' ], [u"councillor_email@testward1.com",u'not_parks_cc@city.com'] ))


class TestDescriber(EmailRuleTestBase):
    
    
    def test_to_councillor(self):
        rule = EmailRule( is_cc=False, rule=EmailRule.TO_COUNCILLOR, city = self.test_city )
        self.assertEqual("All reports", rule.label())
        self.assertEqual(self.test_ward.councillor.email,rule.value(self.test_ward))
        self.assertEqual("the councillor's email address",rule.value())
         
        describer = EmailRuleDescriber("All reports")
        describer.add_rule(rule,self.test_ward)
        expect = "All reports will be sent to:%s"%(self.test_ward.councillor.email)
        self.assertEqual( expect , unicode(describer))

    def test_category_match(self):
        parks_category = ReportCategory.objects.get(name_en='Lights Malfunctioning in Park')
        parks_category_class = ReportCategoryClass.objects.get(name_en='Parks')
        rule = EmailRule(rule=EmailRule.MATCHING_CATEGORY_CLASS, city =self.test_city, category_class = parks_category_class, email='parks@city.com'  )
        self.assertEqual("'Parks' reports", rule.label())
        self.assertEqual('parks@city.com',rule.value(self.test_ward))
        self.assertEqual('parks@city.com',rule.value())
         
        describer = EmailRuleDescriber("'Parks' reports")
        describer.add_rule(rule,self.test_ward)
        expect = "'Parks' reports will be sent to:parks@city.com"
        self.assertEqual( expect , unicode(describer))

    def test_not_category_match(self):
        parks_category = ReportCategory.objects.get(name_en='Lights Malfunctioning in Park')
        parks_category_class = ReportCategoryClass.objects.get(name_en='Parks')
        rule = EmailRule(rule=EmailRule.NOT_MATCHING_CATEGORY_CLASS, city =self.test_city, category_class = parks_category_class, email='notparks@city.com'  )
        self.assertEqual("non-'Parks' reports", rule.label())
        self.assertEqual('notparks@city.com',rule.value(self.test_ward))
        self.assertEqual('notparks@city.com',rule.value(None))
         
        describer = EmailRuleDescriber("non-'Parks' reports")
        describer.add_rule(rule,self.test_ward)
        expect = "non-'Parks' reports will be sent to:notparks@city.com"
        self.assertEqual( expect , unicode(describer))

    def test_pei(self):
                # simulate Charlottetown's somewhat complicated cases:
        # 
        # For all categories except Parks, send email to  not_parks1@city.com  and  not_parks2@city.com
        # with a Cc: to not_parks_cc@city.com  and  the ward councillor.
        #
        # For the category of Parks, send email to:  parks@city.com
        # with a Cc: to  parks_cc@city.com  and  the ward councillor   
        #
        parks_category = ReportCategory.objects.get(name_en='Lights Malfunctioning in Park')
        not_parks_category = ReportCategory.objects.get(name_en='Damaged Curb')
        parks_category_class = ReportCategoryClass.objects.get(name_en='Parks')
        
        # always CC the councillor
        EmailRule( is_cc=True, rule=EmailRule.TO_COUNCILLOR, city = self.test_city ).save()
        
        # parks rules
        EmailRule(rule=EmailRule.MATCHING_CATEGORY_CLASS, city =self.test_city, category_class = parks_category_class, email='parks@city.com' ).save()
        EmailRule(rule=EmailRule.MATCHING_CATEGORY_CLASS, city =self.test_city, category_class = parks_category_class, email='parks_cc@city.com', is_cc=True ).save()

        # not parks rules
        EmailRule( rule=EmailRule.NOT_MATCHING_CATEGORY_CLASS, city = self.test_city, category_class = parks_category_class, email='not_parks1@city.com' ).save()
        EmailRule( rule=EmailRule.NOT_MATCHING_CATEGORY_CLASS, city = self.test_city, category_class = parks_category_class, email='not_parks2@city.com' ).save()
        EmailRule( rule=EmailRule.NOT_MATCHING_CATEGORY_CLASS, city = self.test_city, category_class = parks_category_class, email='not_parks_cc@city.com', is_cc=True ).save()
        
        descs = self.test_ward.get_rule_descriptions()
        self.assertEquals(3,len(descs))
        self.assertEquals("All reports will be cc'd to:councillor_email@testward1.com",unicode(descs[0]))
        self.assertEquals("'Parks' reports will be sent to:parks@city.com and cc'd to:parks_cc@city.com",unicode(descs[1]))
        self.assertEquals("non-'Parks' reports will be sent to:not_parks1@city.com,not_parks2@city.com and cc'd to:not_parks_cc@city.com",unicode(descs[2]))
        
        city_descs = self.test_city.get_rule_descriptions()
        self.assertEquals(3,len(city_descs))
        self.assertEquals("All reports will be cc'd to:the councillor's email address",unicode(city_descs[0]))
        self.assertEquals("'Parks' reports will be sent to:parks@city.com and cc'd to:parks_cc@city.com",unicode(city_descs[1]))
        self.assertEquals("non-'Parks' reports will be sent to:not_parks1@city.com,not_parks2@city.com and cc'd to:not_parks_cc@city.com",unicode(city_descs[2]))


    def test_city_default(self):
        ward_w_email = Ward.objects.get(name='WardInCityWith311Email')
        descs = ward_w_email.get_rule_descriptions()
        self.assertEquals(1,len(descs))
        self.assertEquals('All reports will be sent to:%s' % ( ward_w_email.city.email ), unicode(descs[0]))

########NEW FILE########
__FILENAME__ = mobile
from django.test import TestCase
from django.test.client import Client
from mainapp.models import Report,ReportUpdate
from mainapp.views.rest import MobileReportAPI
import simplejson
import md5
import settings
import binascii
import re
from django.core import mail
           
LOCAL_PARAMS =  { 'title': 'A report from our API', 
                     'lat': '45.4301269580000024',
                     'lon': '-75.6824648380000014',
                     'category_id': 5,
                     'desc': 'The description',
                     'author': 'John Farmer',
                     'email': 'testuser@hotmail.com',
                     'phone': '514-513-0475' } 

MOBILE_PARAMS =  { 'title': 'A report from our API', 
                      'lat': '45.4301269580000024',
                      'lon': '-75.6824648380000014',
                      'category': 5,
                      'first_name': 'John',
                      'last_name':'Farmer',
                      'description': 'The description',
                      'customer_email': 'testuser@hotmail.com',
                      'customer_phone': '514-513-0475' } 
    
UPDATE_PARAMS = { 'author': 'John Farmer',
                      'email': 'testuser@hotmail.com',
                      'desc': 'This problem has been fixed',
                      'phone': '514-513-0475',
                      'is_fixed': True }


class MobileTestCases(TestCase):
    """ 
        our fixture has 4 confirmed reports and one unconfirmed.
        two of the confirmed reports share the same latitude and longitude.
    """
    fixtures = ['test_rest.json']
    c = Client()
    
    def get_json(self, query):
        response = self.c.get(query)
        self.assertEquals(response.status_code,200)
        return( simplejson.loads(response.content) )
        
    def test_get_by_query(self):
        result = self.get_json('/mobile/reports.json?q=K2P1N8')
        self.assertEquals( len(result), 4 )
        
    def test_get_bad_format(self):
        response = self.c.get('/mobile/reports.unknown?q=K2P1N8')
        self.assertEquals(response.status_code,415)

    def test_get_by_lat_lon(self):
        lon = '-75.6824648380000014'
        lat = '45.4301269580000024'
        result = self.get_json('/mobile/reports.json?lat=%s;lon=%s' % (lat,lon))
        self.assertEquals( len(result), 4 )

    def test_get_by_lat_lon_with_r(self):
        lon = '-75.6824648380000014'
        lat = '45.4301269580000024'
        result = self.get_json('/mobile/reports.json?lat=%s;lon=%s;r=.002' % (lat,lon))
        self.assertEquals( len(result), 2 )

    def test_create_param_tranform(self):  
       output = MobileReportAPI._transform_params( MOBILE_PARAMS.copy() )
       self.assertEquals(output, LOCAL_PARAMS ) 

    def test_create(self):
        params = MOBILE_PARAMS.copy()
        params['device_id'] = 'iphone'
        params['timestamp'] = 'asdfasdf'
        seed = '%s:%s:%s' % ( params['customer_email'],params['timestamp'],settings.MOBILE_SECURE_KEY )
        m = md5.new( seed )
        params['api_key'] = binascii.b2a_base64(m.digest())

        response = self.c.post('/mobile/reports.json', params )
        self.assertEquals( response.status_code, 200 )
        self.assertEqual(Report.objects.filter(title=params['title']).count(), 1 )
        # mail should go directly to the city.
        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].to, [u'example_city_email@yahoo.ca'])
        
    def test_create_no_nonce(self):
        params = MOBILE_PARAMS.copy()
        response = self.c.post('/mobile/reports.json', params )
        self.assertEquals( response.status_code, 412 )
    
    def test_create_basecase(self):
        """
            Run through our regular report/submit/confirm/update-is-fixed/confirm
            lifecycle to make sure there's no issues, and the right
            emails are being sent.
        """
        response = self.c.post('/reports/', LOCAL_PARAMS, follow=True )
        self.assertEquals( response.status_code, 200 )
        self.assertEquals(response.template[0].name, 'reports/show.html')
        self.assertEqual(Report.objects.filter(title=LOCAL_PARAMS['title']).count(), 1 )

        # a confirmation email should be sent to the user
        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].to, [u'testuser@hotmail.com'])

        #test confirmation link
        confirm_url = self._get_confirm_url(mail.outbox[0])
        response = self.c.get(confirm_url, follow=True)
        self.assertEquals( response.status_code, 200 )

        #now there should be two emails in our outbox
        self.assertEquals(len(mail.outbox), 2)
        self.assertEquals(mail.outbox[1].to, [u'example_city_email@yahoo.ca'])

        #now submit a 'fixed' update.
        report = Report.objects.get(title=LOCAL_PARAMS['title'])
        self.assertEquals( ReportUpdate.objects.filter(report=report).count(),1)
        update_url = report.get_absolute_url() + "/updates/"
        response = self.c.post(update_url,UPDATE_PARAMS, follow=True)
        self.assertEquals( response.status_code, 200 )
        self.assertEquals( ReportUpdate.objects.filter(report=report).count(),2)
  
        # we should have sent another confirmation link
        self.assertEquals(len(mail.outbox), 3)
        self.assertEquals(mail.outbox[2].to, [u'testuser@hotmail.com'])

        #confirm the update
        confirm_url = self._get_confirm_url(mail.outbox[2])
        response = self.c.get(confirm_url, follow=True)
        self.assertEquals( response.status_code, 200 )
        
        #I guess we send an email to the user to let them know they've confirmed.
        #seems redundant.
        
        self.assertEquals(len(mail.outbox), 4)
        self.assertEquals(mail.outbox[3].to, [u'testuser@hotmail.com'])
        
    def _get_confirm_url(self, email ):
        m = re.search( 'http://localhost:\d+(\S+)', email.body )
        self.assertNotEquals(m,None)
        self.assertEquals(len(m.groups()),1)
        return( str(m.group(1)))

########NEW FILE########
__FILENAME__ = v2
from django.test import TestCase
from django.test.client import Client
import os
from mainapp.models import Report,ApiKey,ReportCategorySet,ReportCategory,City
import xml.dom.minidom
from django.core import mail

PATH = os.path.dirname(__file__)         

ANON_CREATE_PARAMS =  { 'lat': '45.4198266',
                        'lon': '-75.6943189',
                        'api_key': 'test_mobile_api_key',
                        'device_id': '411',
                        'service_code': 5,
                        'location': 'Some Street',
                        'first_name': 'John',
                        'last_name':'Farmer',
                        'title': 'Submitted by our mobile app',
                        'description': 'The description of a mobile submitted report',
                        'email': 'testuser@hotmail.com',
                        'phone': '514-513-0475' 
                    } 

LOGGEDIN_CREATE_PARAMS =  { 'title': 'A report from our API from a logged in user', 
                            'api_key': 'test_mobile_api_key',
                            'device_id': '411',
                            'lat': '45.4301269580000024',
                            'lon': '-75.6824648380000014',
                            'location': 'Some Street',
                            'service_code': 5,
                            'description': 'The description' 
                        } 

EXPECTED_ERRORS = {
           'lat': ['lat:This field is required.'],
           'lon': ['lon:This field is required.'],
           'service_code': ['service_code:This field is required.'],
           'first_name':  None,
           'last_name': ['last_name:This field is required.'],
           'title': None,
           'description': ['description:This field is required.'],
           'email': ['email:This field is required.'],
           'phone': None,
           'api_key': [ 'description:This field is required.' ]  }

class Open311v2(TestCase):
    
    fixtures = ['test_mobile.json']
    c = Client()

    def test_get_report(self):
        url = self._url('requests/1.xml?jurisdiction_id=oglo_on.fixmystreet.ca')
        response = self.c.get(url)
        self._expectXML(response, 'get_report_1.xml' )
                
    def test_get_services_by_jurid(self):
        url = self._url('services.xml?jurisdiction_id=oglo_on.fixmystreet.ca')
        self._test_get_services(url)

    def test_get_services_by_latlon(self):
        url = self._url('services.xml?lat=45.4301269580000024;lon=-75.6824648380000014')
        self._test_get_services(url)    

    def test_get_services_by_unspecified(self):
        url = self._url('services.xml')
        response = self.c.get(url)
        self.assertEquals(response.status_code,400)

    def test_get_services_by_bad_jurid(self):
        url = self._url('services.xml?jurisdiction_id=doesnt_exist')
        response = self.c.get(url)
        self.assertEquals(response.status_code,404)

    def test_get_services_by_bad_latlon(self):
        url = self._url('services.xml?lat=-45.4301269580000024;lon=75.6824648380000014')
        response = self.c.get(url)
        self.assertEquals(response.status_code,404)
        
    def test_get_by_lat_lon(self):
        params = { 'lon': '-75.6824648380000014',
                   'lat': '45.4301269580000024' }
        url = self._reportsUrl(params)
        response = self.c.get(url)
        self._expectXML(response, 'get_reports.xml' )

    def test_get_by_date_range(self):
        params = { 'start_date' : '2009-02-02',
                   'end_date' : '2009-02-03' }
        url = self._reportsUrl(params)
        response = self.c.get(url)
        self._expectXML(response, 'get_report_2.xml' )

    def test_get_by_end_date(self):
        params =  { 'end_date': '2009-02-02' }
        url = self._reportsUrl(params)
        response = self.c.get(url)
        self._expectXML(response, 'get_report_1.xml' )

    def test_get_by_start_date(self):
        params =  { 'start_date': '2009-02-04' }
        url = self._reportsUrl(params)
        response = self.c.get(url)
        self._expectXML(response, 'get_report_4.xml' )
        
    def _create_request(self, params,expected_errors=None, anon=True, error_code=400):
        api_key = ApiKey.objects.get(key='test_mobile_api_key')
        response = self.c.post(self._reportsUrl(), params, **{ "wsgi.url_scheme" : "https" } )
        doc = xml.dom.minidom.parseString(response.content)            

        if not expected_errors:
            self.assertEquals( response.status_code, 200 )
            self.assertEqual(Report.objects.filter(api_key=api_key,device_id=ANON_CREATE_PARAMS['device_id'],desc=ANON_CREATE_PARAMS['description']).count(), 1 )
            self.assertEquals(len(mail.outbox), 1, 'an email was sent')
            if anon:
                self.assertEquals(mail.outbox[0].to, ['testuser@hotmail.com'])
            self.assertEqual(len(doc.getElementsByTagName('service_request_id')), 1, "there is a request id in the resposne")
            request_id = doc.getElementsByTagName('service_request_id')[0].childNodes[0].data
            self.assertEquals( request_id, '6', "we've created a new request" ) 
        else:
            self.assertEquals( response.status_code, error_code )
            errors = doc.getElementsByTagName('description')
            if len(errors) != len(expected_errors):
                for error in errors:
                    print error.childNodes[0].data
            self.assertEquals(len(errors),len(expected_errors))
            for error in errors:
                error_text = error.childNodes[0].data
                self.assertEquals(error_text in expected_errors,True)
                
    def test_anon_report_post(self):
        self._create_request(ANON_CREATE_PARAMS)
    
    def _test_post_missing(self, field, error_code=400 ):
        params = ANON_CREATE_PARAMS.copy()
        del( params[field])
        self._create_request(params,expected_errors=EXPECTED_ERRORS[field],error_code=error_code)

    def test_post_missing_title(self):
        self._test_post_missing('title')
        
    def test_post_missing_email(self):
        self._test_post_missing('email')

    def test_post_missing_phone(self):
        self._test_post_missing('phone')
    
    def test_post_missing_lname(self):    
        self._test_post_missing('last_name')

    def test_post_missing_fname(self):    
        self._test_post_missing('first_name')

    def test_post_missing_scode(self):    
        self._test_post_missing('service_code')

    def test_post_missing_desc(self):    
        self._test_post_missing('description')

    def test_post_missing_lat(self):    
        self._test_post_missing('lat')

    def test_post_multi_missing(self):    
        params = ANON_CREATE_PARAMS.copy()
        del( params['lat'])
        del( params['email'])
        errors = EXPECTED_ERRORS['lat']
        errors.extend(EXPECTED_ERRORS['email']) 
        self._create_request(params,errors)
        
    def test_bad_latlon(self):
        params = ANON_CREATE_PARAMS.copy()
        params['lat'] = '22.3232323'
        expect = ['__all__:lat/lon not supported']
        self._create_request(params,expected_errors=expect)
        
    def test_post_missing_api_key(self):
        params = ANON_CREATE_PARAMS.copy()
        del(params[ 'api_key' ])
        self._create_request(params,["403:Invalid api_key received -- can't proceed with create_request."],error_code=403)
        
    def test_bad_api_key(self):
        params = ANON_CREATE_PARAMS.copy()
        params[ 'api_key' ] = 'bad api key'
        self._create_request(params,["403:Invalid api_key received -- can't proceed with create_request."],error_code=403)

    def _test_get_services(self,url):
        response = self.c.get(url)
        # check that the default is as expected.
        self._expectXML(response, 'get_default_services.xml' )
        
        # now, change the services available in the city.
        new_categoryset = ReportCategorySet.objects.create(name='modified')
        for category in ReportCategory.objects.filter(category_class__name_en='Parks'):
            new_categoryset.categories.add(category)
        new_categoryset.save()
        city = City.objects.get(name='Oglo')
        city.category_set = new_categoryset
        city.save()

        response = self.c.get(url)
        # check that the default is as expected.
        self._expectXML(response, 'get_modified_services.xml' )
        

    def _url(self, url):
        return('/open311/v2/' + url )
    
    def _reportsUrl(self, params = None ):
        url = self._url('requests.xml')
        if params:
            url += '?'
            for key, value in params.items():
                url += key + "=" + value + ";"
        return url
    
    def _expectXML(self,response,filename):
        self.assertEquals(response.status_code,200)
        file = PATH + '/expected/' +filename
        expect_doc = xml.dom.minidom.parse(file)
        expect_s = expect_doc.toprettyxml()
        got_doc = xml.dom.minidom.parseString(response.content)
        got_s = got_doc.toprettyxml()
        self.maxDiff = None
        self.assertMultiLineEqual( got_s, expect_s )
        
         
ANON_UPDATE_PARAMS = { 'author': 'John Farmer',
                      'email': 'testuser@hotmail.com',
                      'desc': 'This problem has been fixed',
                      'phone': '514-513-0475',
                      'is_fixed': True }

LOGGEDIN_UPDATE_PARAMS = { 'desc': 'This problem has been fixed',
                           'is_fixed': True }


########NEW FILE########
__FILENAME__ = stats
from django.test import TestCase
from mainapp.models import Report,ReportUpdate,Ward,City
from mainapp.management.commands.stats import CountReportsWithStatusOnDay,NumReports,CityStatRows,CategoryGroupStatRows,CategoryStatRows,StatColGroup,AvgTimeToFix, PercentUnfixed, PercentFixedInDays

class StatTestCase(TestCase):
    """ 
        our fixture has:
            1 report fixed in 2 days
            1 report fixed in 16 days
            2 unfixed reports, which are the same age
    """
    fixtures = ['test_stats.json']
    
    def setUp(self):
        self.reports = Report.objects.filter(is_confirmed=True)
        
    def check_result(self,stat_instance,expected):
        for report in self.reports:
            stat_instance.add_report(report)
        self.assertEquals(stat_instance.result(), expected)
            

class NumReportsTestCase(StatTestCase):
    
    def test(self):
        self.check_result(NumReports(), 4)

class AvgFixTestCase(StatTestCase):
    
    def test(self):
        self.check_result(AvgTimeToFix(), 9)

class UnfixedTestCase(StatTestCase):
    
    def test(self):
        self.check_result(PercentUnfixed(), .5)

class FixedInDaysTestCase(StatTestCase):
    
    def test(self):
        self.check_result(PercentFixedInDays(0,3), .25)
        self.check_result(PercentFixedInDays(3,19), .25)
        self.check_result(PercentFixedInDays(0,19), .5)

class CountReportsWithStatusOnDayTestCase(StatTestCase):

    def test(self):
        self.check_result(CountReportsWithStatusOnDay(7,
                                                      CountReportsWithStatusOnDay.FIXED), 1)
        self.check_result(CountReportsWithStatusOnDay(7,
                                                      CountReportsWithStatusOnDay.OPEN), 3)
        self.check_result(CountReportsWithStatusOnDay(17,
                                                      CountReportsWithStatusOnDay.OPEN), 2)
        self.check_result(CountReportsWithStatusOnDay(17,
                                                      CountReportsWithStatusOnDay.FIXED), 2)
            
class ColGroupTestCase(StatTestCase):
    
    def test(self):
        group = StatColGroup( stats = [ PercentFixedInDays(0,3), PercentUnfixed() ] )
        self.check_result(group, [[ .25, .5 ]])
        self.assertEquals(group.labels(),  ['Fixed in 0-3 Days', 'Percent Unfixed'] )


class TestStatGroup1(StatColGroup):
    """
        A grouping of statistics columns to be used in testing
        different row groupings (city,category,category group).
    """
    def __init__(self):
        super(TestStatGroup1,self).__init__(stats = [ PercentFixedInDays(0,3),PercentFixedInDays(3,18), PercentUnfixed() ])
        

class CategoryTestCase(StatTestCase):
    
    def test(self):
        cat_group = CategoryStatRows(TestStatGroup1)
        self.assertEquals(cat_group.labels(),  ['Category','Fixed in 0-3 Days','Fixed in 3-18 Days', 'Percent Unfixed'] )
        self.check_result(cat_group, [[ 'All',.25, .25, .5 ], [u'Graffiti On City Property',0,.5,.5],[u'Broken or Damaged Equipment/Play Structures',.5, 0, .5]])

        
class CategoryGroupTestCase(StatTestCase):
    
    def test(self):
        cat_group = CategoryGroupStatRows(TestStatGroup1)
        self.assertEquals(cat_group.labels(),  ['Category Group','Fixed in 0-3 Days','Fixed in 3-18 Days', 'Percent Unfixed'] )
        self.check_result(cat_group, [[ 'All',.25, .25, .5 ], [u'Grafitti',0,.5,.5],[u'Parks',.5, 0, .5]])


class CityTestCase(StatTestCase):

    def test(self):
        cat_group = CityStatRows(TestStatGroup1)
        self.assertEquals(cat_group.labels(),  ['City','Fixed in 0-3 Days','Fixed in 3-18 Days', 'Percent Unfixed'] )
        self.check_result(cat_group, [[ 'All',.25, .25, .5 ], [u'Oglo',.25,.25,.5]])

########NEW FILE########
__FILENAME__ = dummy_socialauth
"""
Dummy Auth
"""

from social_auth.backends import SocialAuthBackend,BaseAuth
from django.contrib.auth import authenticate

class DummyBackend(SocialAuthBackend):
    name = 'dummy'

    def get_user_details(self, response):
        return {'username': response['username'],
                'email': response.get('email', ''),
                'fullname': response.get('first_name',"") + " " + response.get('last_name',''),
                'first_name': response.get('first_name', ''),
                'last_name': response.get('last_name', '')}


    def get_user_id(self, details, response):
        "OAuth providers return an unique user id in response"""
        if not response.get('id',None):
            raise ValueError('Missing user id')

        return response['id']


class DummyAuth(BaseAuth):
    AUTH_BACKEND = DummyBackend

        
    def auth_complete(self, *args, **kwargs):
        """Returns user, might be logged in"""
        response = { 'email': self.data.get('email',''),
                     'username': self.data.get('username',''),
                     'first_name': self.data.get('first_name',''),
                     'last_name': self.data.get('last_name','')
                    }
        
        if self.data.get('uid',None):
            response['id'] = self.data.get('uid')
            
        kwargs.update({'response': response, DummyBackend.name: True})
        return authenticate(*args, **kwargs)




# Backend definition
BACKENDS = {
    'dummy': DummyAuth,
}

########NEW FILE########
__FILENAME__ = testviewdefs
# urls used by testview app

TEST_URLS = [   
    ('/'         , 'home'), 
    ('/cities/'  , 'city list'),
    ('/cities/1' , 'ward list'),
    ('/wards/3'  , 'show ward'),
    ('/search?q=slater street', 'ambigous search'),
    ('/search?q=Moscow,Russia', 'failed search'),
    ('/search?q=somerset and empress,ottawa canada', 'search'),
    ('/reports/new?&lat=45.41958499972712&lon=-75.7028603553772','file new report'),
    ('/reports/114', 'unconfirmed report'),
    ('/reports/331', 'report with no updates'),
    ('/reports/491', 'updated report'),
    ('/reports/479', 'fixed report'),
    ('/reports/updates/create/', 'request to confirm update'),
    ('/reports/331/subscribers/', 'new subscriber'),
    ('/reports/subscribers/create/', 'request subscriber confirm'),
    ('/reports/subscribers/confirm/02a99e748e18bfec372d6f460b592d69','on subscriber confirm'),
    ('/reports/331/flags', 'flag report'),
    ('/reports/331/flags/thanks', 'after flagging a report'),
    ('/contact/', 'contact form'),
    ('/contact/thanks', 'after submitting contact form'),
    ('/about', 'about') 
    ]

FIXTURES = [] # [ 'testview_report_fixtures.json' ]
########NEW FILE########
__FILENAME__ = account
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from mainapp.models import UserProfile, Report, ReportSubscriber,ReportUpdate
from mainapp.forms import FMSNewRegistrationForm,FMSAuthenticationForm, EditProfileForm
from django.template import Context, RequestContext
from django.contrib.auth.decorators import login_required
from django.db import connection,transaction
from django.db.models import Q
from django.utils.datastructures import SortedDict
from social_auth.backends import get_backend
from social_auth.models import UserSocialAuth
from django.conf import settings
from django.contrib.auth import login, REDIRECT_FIELD_NAME
from django.core.paginator import Paginator, InvalidPage, EmptyPage

LOGO_OFFSETS = {    'facebook': 0,
                    'twitter': -128,
                    'google': -192,
                    'dummy':0  
                }    

class SocialProvider(object):
    def __init__(self, name):
        self.name=name
        self.key=name.lower()
        self.logo_offset=LOGO_OFFSETS[ self.key ]
    
    def url(self):
        return '/accounts/login/%s/' % [ self.key ]
    
SUPPORTED_SOCIAL_PROVIDERS = [ 
                SocialProvider('Facebook'),
                SocialProvider('Twitter') ]

DEFAULT_REDIRECT = getattr(settings, 'SOCIAL_AUTH_LOGIN_REDIRECT_URL', '') or \
                   getattr(settings, 'LOGIN_REDIRECT_URL', '')


@login_required
def home( request ):
    email = request.user.email
    subscriberQ = Q(reportsubscriber__email=email,reportsubscriber__is_confirmed=True)
    updaterQ = Q(reportupdate__email=email,reportupdate__is_confirmed=True)
    allreports = Report.objects.filter(subscriberQ | updaterQ).order_by('-created_at').extra(select=SortedDict([('is_reporter','select case when bool_or(report_updates.first_update) then true else false end from report_updates where report_updates.email=%s and report_updates.is_confirmed=true and report_updates.report_id=reports.id'), 
                                                                                        ('is_updater','select case when count(report_updates.id) > 0 then true else false end from report_updates where report_updates.report_id=reports.id and report_updates.first_update=false and report_updates.email=%s and report_updates.is_confirmed=true'),                                                                                        ('days_open','case when reports.is_fixed then date(reports.fixed_at) - date(reports.created_at) else CURRENT_DATE - date(reports.created_at) end')]), select_params=( email, email )).distinct()
    try:
        page_no = int(request.GET.get('page', '1'))
    except ValueError:
        page_no = 1

    paginator = Paginator(allreports, 100) 

    try:
        page = paginator.page(page_no)
    except (EmptyPage, InvalidPage):
        page = paginator.page(paginator.num_pages)
        
    return render_to_response("account/home.html",
                {'reports':page.object_list,
                 'page':page },
                context_instance=RequestContext(request))

@login_required
def edit( request ):
    if request.method == 'POST':
        form = EditProfileForm(request.POST, instance=request.user.get_profile())
        if form.is_valid():
            form.save()
            # redirect after save
            return HttpResponseRedirect( reverse('account_home'))
    else:
        form = EditProfileForm( instance=request.user.get_profile())

    return render_to_response("account/edit.html", { 'form': form },
                              context_instance=RequestContext(request))

    return render_to_response("account/edit.html")

@transaction.commit_on_success
def socialauth_complete( request, backend ):    
    """
       Authentication complete process -- override from the
       default in django-social-auth to:
        -- collect phone numbers on registration
        -- integrate with django-registration in order
           to confirm email for new users
    """
    backend = get_backend(backend, request, request.path)
    if not backend:
        return HttpResponseServerError('Incorrect authentication service')

    try:
        user = backend.auth_complete()
    except ValueError, e:  # some Authentication error ocurred
        user = None
        error_key = getattr(settings, 'SOCIAL_AUTH_ERROR_KEY', 'error_msg')
        if error_key:  # store error in session
            request.session[error_key] = str(e)

    if user:
        backend_name = backend.AUTH_BACKEND.name
        if getattr(user, 'is_active', True):
            # a returning active user
            login(request, user)
            if getattr(settings, 'SOCIAL_AUTH_SESSION_EXPIRATION', True):
                # Set session expiration date if present and not disabled by
                # setting
                social_user = user.social_auth.get(provider=backend_name)
                if social_user.expiration_delta():
                    request.session.set_expiry(social_user.expiration_delta())
            url = request.session.pop(REDIRECT_FIELD_NAME, '') or DEFAULT_REDIRECT
            return HttpResponseRedirect(url)
        else:
            # User created but not yet activated. 
            details = { 'username':user.username,
                        'first_name':user.first_name,
                        'last_name': user.last_name }

            if user.email and user.email != '':
                details[ 'email' ] = user.email
            social_user = UserSocialAuth.objects.get(user=user)        
            form = FMSNewRegistrationForm( initial=details )
            return render_to_response("registration/registration_form.html",
                                          {'form': form,
                                           'social_connect': SocialProvider(backend.AUTH_BACKEND.name.capitalize()) },
                                          context_instance=RequestContext(request))

    # some big error.
    url = getattr(settings, 'LOGIN_ERROR_URL', settings.LOGIN_URL)
    return HttpResponseRedirect(url)


def error(request):
    error_msg = request.session.pop(settings.SOCIAL_AUTH_ERROR_KEY, None)
    return render_to_response('registration/error.html', {'social_error': error_msg},
                              RequestContext(request))


   
########NEW FILE########
__FILENAME__ = ajax
from django.shortcuts import render_to_response, get_object_or_404
from django.template import Context, RequestContext
from mainapp.models import ReportCategory, ReportCategoryClass

def category_desc(request,id):    
   return render_to_response("ajax/category_description.html",
                {"category": ReportCategory.objects.get(id=id),
                  },
                context_instance=RequestContext(request))
########NEW FILE########
__FILENAME__ = cities
from django.shortcuts import render_to_response, get_object_or_404
from mainapp.models import City, Ward, Report, ReportCounters, CityMap
from django.template import Context, RequestContext
from django.db.models import  Count

def index(request):    
    return render_to_response("cities/index.html",
                {"report_counts": City.objects.annotate(**ReportCounters('ward__report')).order_by('province__abbrev') },
                context_instance=RequestContext(request))


def show( request, city ):    
    #top problems
    top_problems = Report.objects.filter(ward__city=city,is_fixed=False).annotate(subscriber_count=Count('reportsubscriber' ) ).filter(subscriber_count__gte=1).order_by('-subscriber_count')[:5]
    if request.GET.has_key('test'):
        google = CityMap(city)
    else:
        google = None
        
    
    return render_to_response("cities/show.html",
                {"city":city,
                 "google": google,
                 'top_problems': top_problems,
                 'city_totals' : City.objects.filter(id=city.id).annotate(**ReportCounters('ward__report','10 years'))[0],
                 "report_counts": Ward.objects.filter(city=city).order_by('number').annotate(**ReportCounters('report'))
                  },
                 context_instance=RequestContext(request))

def show_by_id(request, city_id ):
    city = get_object_or_404(City, id=city_id)
    return( show(request,city )) 

def show_by_slug(request, city_slug ):
    city = get_object_or_404(City, slug=city_slug)
    return( show(request,city )) 

def home( request, city, error_msg, disambiguate ):
    #top problems
    top_problems = Report.objects.filter(ward__city=city,is_fixed=False).annotate(subscriber_count=Count('reportsubscriber' ) ).filter(subscriber_count__gte=1).order_by('-subscriber_count')[:10]
    reports_with_photos = Report.objects.filter(is_confirmed=True, ward__city=city).exclude(photo='').order_by("-created_at")[:3]
    recent_reports = Report.objects.filter(is_confirmed=True, ward__city=city).order_by("-created_at")[:5]
        
    return render_to_response("cities/home.html",
                {"report_counts": City.objects.filter(id=city.id).annotate(ReportTotalCounters('ward__report','10 years'))[0],
                 "cities": City.objects.all(),
                 'city':city,
                 'top_problems': top_problems,
                 "reports_with_photos": reports_with_photos,
                 "recent_reports": recent_reports , 
                 'error_msg': error_msg,
                 'disambiguate':disambiguate },
                context_instance=RequestContext(request))    
    
########NEW FILE########
__FILENAME__ = contact
from django.shortcuts import render_to_response, get_object_or_404
from mainapp.models import Report
from mainapp.forms import ContactForm
from django.template import Context, RequestContext
from django.http import HttpResponseRedirect

import settings

def thanks(request): 
     return render_to_response("contact/thanks.html", {},
                context_instance=RequestContext(request))

def new(request):
    if request.method == 'POST':
        form = ContactForm(data=request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("/contact/thanks")
    else:
        form = ContactForm()

    return render_to_response("contact/new.html",
                              { 'contact_form': form },
                              context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = main
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, Http404
from mainapp.models import DictToPoint, Report, ReportUpdate, Ward, FixMyStreetMap, OverallReportCount, City, FaqEntry
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.template import Context, RequestContext
from django.contrib.gis.measure import D 
from django.contrib.gis.geos import *
import settings
import datetime
from django.utils.translation import ugettext as _
from django.utils.http import urlquote
from django.utils.encoding import iri_to_uri
from mainapp.views.cities import home as city_home
import logging
import os
import urllib


def home(request, location = None, error_msg =None): 

    if request.subdomain:
        matching_cities = City.objects.filter(name__iexact=request.subdomain)
        if matching_cities:
            return( city_home(request, matching_cities[0], error_msg, disambiguate ) )

    if request.GET.has_key('q'):
        location = request.GET["q"]
                    
    return render_to_response("home.html",
                {"report_counts": OverallReportCount('1 year'),
                 "cities": City.objects.all(),
                 'search_error': error_msg,
                 'location':location,
                 'GOOGLE_KEY': settings.GMAP_KEY },
                context_instance=RequestContext(request))    

def _search_url(request,years_ago):
    return('/search?lat=%s;lon=%s;years_ago=%s' % ( request.GET['lat'], request.GET['lon'], years_ago ))
           
def search_address(request):
    if request.method == 'POST':
        address = iri_to_uri(u'/search?q=%s' % request.POST["q"])
        return HttpResponseRedirect( address )

    if request.GET.has_key('q'):
        address = request.GET["q"]
        return home( request, address, None )

    # should have a lat and lon by this time.
    dict2pt = DictToPoint( request.GET )
    pnt = dict2pt.pnt()
    ward = dict2pt.ward()
    if not ward:
        return( home(request, None, _("Sorry, we don't yet have that area in our database. Please have your area councillor contact fixmystreet.ca.")))
    
    try:
        page_no = int(request.GET.get('page', '1'))
    except ValueError:
        page_no = 1

    reportQ = Report.objects.filter(is_confirmed = True,point__distance_lte=(pnt,D(km=2))).distance(pnt).order_by('-created_at')
    paginator = Paginator(reportQ, 100) 
    
    try:
        page = paginator.page(page_no)
    except (EmptyPage, InvalidPage):
        page = paginator.page(paginator.num_pages)

    
    reports = page.object_list
    gmap = FixMyStreetMap(pnt,True,reports)
        
    return render_to_response("search_result.html",
                {'google' : gmap,
                 'GOOGLE_KEY': settings.GMAP_KEY,
                 "pnt": pnt,
                 "enable_map": True,
                 "ward" : ward,
                 "reports" : reports,
                 "page":page,
                 "url_parms": "&lat=%s&lon=%s" %( request.GET['lat'], request.GET['lon'])
                  },
                 context_instance=RequestContext(request))


def about(request):
   return render_to_response("about.html",{'faq_entries' : FaqEntry.objects.all().order_by('order')},
                context_instance=RequestContext(request)) 


def show_faq( request, slug ):
    faq = get_object_or_404(FaqEntry, slug=slug)
    return render_to_response("faq/show.html",
                {"faq_entry":faq },
                 context_instance=RequestContext(request))
   
def posters(request): 
   return render_to_response("posters.html",
                {'languages': settings.LANGUAGES },
                 context_instance=RequestContext(request))
      
def privacy(request): 
   return render_to_response("privacy.html",
                { },
                 context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = mobile
from contrib.django_restapi.model_resource import Collection
from contrib.django_restapi.responder import JSONResponder, XMLResponder
from django.contrib.gis.geos import fromstr
from django.contrib.gis.measure import D
from django.forms.util import ErrorDict
from mainapp.models import Report,ReportCategory
from mainapp import search
from mainapp.views.reports.main import create_report
import md5
import binascii
import settings
from django.core import serializers
from django.http import HttpResponse, HttpResponseBadRequest
from django.db import models


class InputValidationException(Exception):
    pass

class InvalidAPIKey(Exception):
    pass

class MobileReportAPI(object):
    
    EXPOSE_FIELDS = ('id','point', 'title','desc','author','email_sent_to','created_at','is_fixed')

    FORIEGN_TO_LOCAL_KEYS = {    'customer_email':'email',
                                 'customer_phone':'phone',
                                 'description': 'desc',
                                 'category': 'category_id'
                            }
    
    def get(self,request):
        ids = request.GET.getlist("id")
        if ids:
            try:
                ids = [int(id) for id in ids]
            except (TypeError, ValueError), e:
                raise InputValidationException(str(e))
            reports = Report.objects.filter(id__in = ids)
            # process ids right now
        else:
            lon = request.GET.get("lon")
            lat = request.GET.get("lat")
            address = request.GET.get("q")
            if lat and lon:
                point_str = "POINT(%s %s)" %(lon, lat)
            elif address:
                addrs = []
                match_index = int(request.GET.get('index', -1))
                point_str = search.search_address(address, match_index, addrs)
            else:
                raise InputValidationException('Must supply either a `q`, `lat` `lon`, or a report `id`')

            radius = float(request.GET.get('r', 4))
            pnt = fromstr(point_str, srid=4326)
            reports = Report.objects.filter(is_confirmed = True,point__distance_lte=(pnt,D(km=radius))).distance(pnt).order_by('distance')[:100]
            return( reports ) 
        
    def post(self,request):
        request.POST = MobileReportAPI._transform_params(request.POST)

        if not request.POST.has_key('device_id'):
            raise InputValidationException('General Service Error: No device_id')

        if not MobileReportAPI._nonce_ok(request):
            raise InvalidAPIKey('Invalid API Key')
 
        # we're good.        
        report = create_report(request,True)
        if not report:
            # some issue with our form input.  Does this need to be more detailed?
            raise InputValidationException('General Service Error: bad input')
        return( Report.objects.filter(pk=report.id) )
    
    def make_response(self,format,models = [],fields= None,status=200):
        mimetype = 'application/%s'%format
        data = serializers.serialize(format, models, fields=fields)
        return HttpResponse(data,mimetype=mimetype,status=status)
    
    @staticmethod    
    def _nonce_ok(request):
        timestamp = request.POST.get('timestamp')
        email = request.POST.get('email')
        nonce = request.POST.get('api_key')
        seed = '%s:%s:%s' % ( email,timestamp,settings.MOBILE_SECURE_KEY )
        m = md5.new( seed )
        compare_nonce = binascii.b2a_base64(m.digest())
        return( compare_nonce == nonce)
    
    @staticmethod
    def _transform_params(params):
        for theirkey,ourkey in MobileReportAPI.FORIEGN_TO_LOCAL_KEYS.items():
            if params.has_key(theirkey):
                params[ ourkey ] = params[ theirkey ]
                del(params[theirkey])
        
        # combine first and last names.
        if params.has_key('first_name') or params.has_key('last_name'):
            if params.has_key('first_name') and params.has_key('last_name'):
                params['author'] = params.get('first_name') + " " + params.get('last_name')
            else:
                params['author'] = params.get('first_name',params.get('last_name'))
            del(params['first_name'])
            del(params['last_name'])
                
        return( params )


class RestCollection(Collection):
    ''' Subclasses Collection to provide multiple responders '''
    def __init__(self, queryset, responders=None, **kwargs):
        '''
        Replaces the responder in Collection.__init__ with responders, which
        maybe a list of responders or None. In the case of None, default
        responders are allocated to the colelction.

        See Collection.__init__ for more details
        '''
        if responders is None:
            responders = {
                'json'  : JSONResponder(),
                'xml'   :XMLResponder(),
            }
        self.responders = {}
        for k, r in responders.items():
            Collection.__init__(self, queryset, r, **kwargs)
            self.responders[k] = self.responder

    def __call__(self, request, format, *args, **kwargs):
        '''
        urls.py must contain .(?P<format>\w+) at the end of the url
        for rest resources, such that it would match one of the keys
        in self.responders
        '''
        error_code = 400
        errors = ErrorDict({'info': ["An error has occured"]})
        if format in self.responders:
            self.responder = self.responders[format]
            try:
                return Collection.__call__(self, request, *args, **kwargs)
            except search.SearchAddressDisambiguateError, e:
                return self.responder.error(request, 412, ErrorDict({
                    'info': [str(e)],
                    'possible_addresses': addrs }))

            except InputValidationException, e:
                errors = ErrorDict({'info': [str(e)]})
                error_code = 412
        else:
            error_code = 415
            errors = ErrorDict(
                {'info': ['Requested content type "%s" not available!' %format]})
        # Using the last used responder to return error
        return self.responder.error(request, error_code, errors)
    

class MobileReportRest(RestCollection):

    api = MobileReportAPI()
    
    def read(self, request):
        reports = self.api.get(request)
        return self.responder.list(request, reports)

    def create(self, request, *args, **kwargs):
        report = self.api.post(request)
        return self.responder.list(request, report )

            

# These use the django-rest-api library.
mobile_report_rest = MobileReportRest(
    queryset=Report.objects.all(),
    permitted_methods = ['GET', 'POST'],
    expose_fields = MobileReportAPI.EXPOSE_FIELDS
)

json_poll_resource = Collection(
    queryset = ReportCategory.objects.all(),
    expose_fields = ('id', 'name_en', 'name_fr'),
    #permitted_methods = ('GET'),
    responder = JSONResponder()
)

# These classes do not use the django-rest-api library

class MobileReportAPIError(models.Model):
    EXPOSE_FIELDS = ('error',)
    error = models.CharField(max_length=255)
    
def mobile_reports( request, format ):
    api = MobileReportAPI()
    supported_formats = [ 'xml','json' ]
    if not format in supported_formats:
        return( HttpResponse('Requested content type "%s" not available.'%format,status=415))         
    try:
        if request.method == "POST":
            to_serialize = api.post(request)
        else:
            to_serialize = api.get(request) 
        return( api.make_response(format,to_serialize,MobileReportAPIError.EXPOSE_FIELDS ) )
    except Exception, e:
        to_serialize = [ MobileReportAPIError(error=str(e)) ]
        return( api.make_response(format,to_serialize,MobileReportAPIError.EXPOSE_FIELDS, status=412 ) )
 

########NEW FILE########
__FILENAME__ = open311v2
from django.contrib.gis.geos import fromstr
from django.contrib.gis.measure import D
from django.shortcuts import render,render_to_response, get_object_or_404
from django.template import Context, RequestContext
from django.http import HttpResponse, HttpResponseBadRequest
from mainapp.models import ApiKey,Report,ReportCategory,DictToPoint,City
from django.conf.urls.defaults import patterns, url, include
from mainapp.forms import ReportForm
from django.conf import settings
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
import re

class InvalidAPIKey(Exception):

    def __init__(self):
        super(InvalidAPIKey,self).__init__("Invalid api_key received -- can't proceed with create_request.")
    
class ApiKeyField(forms.fields.CharField):
    
    def __init__(self,required=True, widget=None, label=None,
                 initial=None, help_text=None, *args, **kwargs):
        super(ApiKeyField,self).__init__(required=required,widget=widget,label=label,initial=initial,help_text=help_text,*args,**kwargs)

    def clean(self, value):
        try:
            api_key = ApiKey.objects.get(key=value)
        except ObjectDoesNotExist:
            raise InvalidAPIKey()
        return api_key


class Open311ReportForm(ReportForm):

    service_code = forms.fields.CharField()
    description = forms.fields.CharField()
    first_name = forms.fields.CharField(required=False)
    last_name = forms.fields.CharField()
    api_key = ApiKeyField()
    
    class Meta:
        model = Report
        fields = ('service_code','description','lat','lon','title', 'category', 'photo','device_id','api_key')

    def __init__(self,data=None,files=None,initial=None, user=None):
        
        if data:
            data = data.copy() # can't modify request.POST directly
            data['desc'] = data.get('description','')
            data['category'] = data.get('service_code','1')
            data['author'] = (data.get('first_name','') + " "  + data.get('last_name','')).strip()
        super(Open311ReportForm,self).__init__(data,files, initial=initial,user=user)
        self.fields['device_id'].required = True
        self.fields['category'].required = False
        self.fields['title'].required = False
        self.update_form.fields['author'].required = False
        
    def _get_category(self):
        service_code = self.cleaned_data.get('service_code',None)
        if not service_code:
            return ''
        categories = ReportCategory.objects.filter(id=service_code)
        if len(categories) == 0:
            return None
        return(categories[0])
    
        
    def clean_title(self):
        data = self.cleaned_data.get('title',None)
        if data:
            return data        
        category = self._get_category()
        if not category:
            return ''
        return ('%s: %s' % (category.category_class.name,category.name))

    
class Open311v2Api(object):
    
    def __init__(self, content_type ):
        self.content_type = content_type 
                
    def report(self,request, report_id ):
        report = get_object_or_404(Report, id=report_id)
        return self._render_reports( request, [ report ])

    def reports(self,request):
        if request.method != "POST":
            reports = Report.objects.filter(is_confirmed=True)
            if request.GET.has_key('lat') and request.GET.has_key('lon'):
                pnt = DictToPoint( request.GET ).pnt()
                d = request.GET.get('r','2')
                reports = reports.filter(point__distance_lte=(pnt,D(km=d)))     
            if request.GET.has_key('start_date'):
                reports = reports.filter(created_at__gte=request.GET['start_date'])
            if request.GET.has_key('end_date'):
                reports = reports.filter(created_at__lte=request.GET['end_date'])  
            reports = reports.order_by('-created_at')[:1000]
            return self._render_reports(request, reports)
        else:
            # creating a new report
            report_form = Open311ReportForm( request.POST, request.FILES,user=request.user )
            try:
                if report_form.is_valid():
                    report = report_form.save()
                    if report:
                        return( self._render_reports(request, [ report ] ) )
                return( self._render_errors(request, report_form.all_errors()))
            except InvalidAPIKey, e:
                return render( request,
                        'open311/v2/_errors.%s' % (self.content_type),
                        { 'errors' : {'403' : str(e) } },
                        content_type = 'text/%s' % ( self.content_type ),
                        context_instance=RequestContext(request),
                        status = 403 )

    def services(self,request):
        city = None
        if request.GET.has_key('lat') and request.GET.has_key('lon'):
            ward = DictToPoint( request.GET ).ward()
            if not ward:
                return HttpResponse('lat/lon not supported',status=404)
            city = ward.city
        if request.GET.has_key('jurisdiction_id'):
            # expect format <city>_<province-abbrev>.fixmystreet.ca
            city = self._parse_jurisdiction(request.GET['jurisdiction_id'])
            if not city:
                return HttpResponse('jurisdiction_id provided not found',status=404)
        if not city:
            return HttpResponse('jurisdiction_id was not provided',status=400)
        
        categories = city.get_categories()

        return render_to_response('open311/v2/_services.%s' % (self.content_type),
                          { 'services' : categories },
                          mimetype = 'text/%s' % ( self.content_type ),
                          context_instance=RequestContext(request))
    
    def _parse_jurisdiction(self,jurisdiction):
        # expect format <city>_<province-abbrev>.fixmystreet.ca
        match = re.match(r"(\w+)_(\w+)\.fixmystreet\.ca",jurisdiction)
        if not match:
            return None
        city = get_object_or_404(City,name__iexact=match.group(1),province__abbrev__iexact=match.group(2))
        return city
    
    def _render_reports(self, request, reports):
        return render_to_response('open311/v2/_reports.%s' % (self.content_type),
                          { 'reports' : reports },
                          mimetype = 'text/%s' % ( self.content_type ),
                          context_instance=RequestContext(request))

    def _render_errors(self,request,errors):
        return render( request,
                       'open311/v2/_errors.%s' % (self.content_type),
                        { 'errors' : errors },
                          content_type = 'text/%s' % ( self.content_type ),
                          context_instance=RequestContext(request),
                          status = 400 )

    
    def get_urls(self):
        urlpatterns = patterns('',
            url(r'^requests.%s$' % ( self.content_type ), self.reports,  {'SSL': ['POST']} ),
            url(r'^services.%s$' % ( self.content_type ), self.services ),
            url(r'^requests/(\d+).%s$' % ( self.content_type ),
                self.report),
            )
        return urlpatterns
    
    @property
    def urls(self):
        return self.get_urls(), 'open311v2', 'open311v2'
    
xml = Open311v2Api('xml')

########NEW FILE########
__FILENAME__ = promotion
from django.template import Context, RequestContext
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from mainapp.models import Report, ReportUpdate


def show(request, promo_code):
    matchstr = "author LIKE '%%" + promo_code + "%%'"
    reports = Report.objects.filter(is_confirmed=True).extra(select={'match': matchstr }).order_by('created_at')[0:100]
    count = Report.objects.filter(author__contains=promo_code).count()
    return render_to_response("promotions/show.html",
                {   "reports": reports,
                    "promo_code":promo_code,
                    "count": count },
                context_instance=RequestContext(request))


########NEW FILE########
__FILENAME__ = flags
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect
from mainapp.models import Report
from django.template import Context, RequestContext
from fixmystreet import settings
from django.template.loader import render_to_string
from django.core.mail import send_mail

def new( request, report_id ):
    report = get_object_or_404(Report, id=report_id)
    if request.method == 'GET':
        return render_to_response("reports/flags/new.html",
                { "report": report },
                context_instance=RequestContext(request))
    else:
        # send email flagging this report as being potentially offensive.
        message = render_to_string("emails/flag_report/message.txt", 
                    { 'report': report })
        send_mail('FixMyStreet.ca Report Flagged as Offensive', message, 
                   settings.EMAIL_FROM_USER,[settings.ADMIN_EMAIL], fail_silently=False)
        return HttpResponseRedirect(report.get_absolute_url() + '/flags/thanks')

def thanks( request, report_id ):
    return render_to_response("reports/flags/thanks.html", {},
                context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = main
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect,Http404
from mainapp.models import UserProfile,DictToPoint,Report, ReportUpdate, Ward, FixMyStreetMap, ReportCategory
from mainapp.forms import ReportForm,ReportUpdateForm
from django.template import Context, RequestContext
from django.contrib.gis.geos import *
from fixmystreet import settings
from django.utils.translation import ugettext as _

def new( request ):
    
    d2p = DictToPoint( request.REQUEST )
    pnt = d2p.pnt()
     
    if request.method == "POST":
        #an UpdateForm is bundled inside ReportForm
        report_form = ReportForm( request.POST, request.FILES, user=request.user )
        # this checks update is_valid too
        if report_form.is_valid():
            # this saves the update as part of the report.
            report = report_form.save()
            if report:
                return( HttpResponseRedirect( report.get_absolute_url() ))
    else:
        initial = {}
        initial['lat' ] =request.GET['lat']
        initial['lon'] = request.GET['lon']
        initial['address'] = request.GET.get('address',None) 
    
        report_form = ReportForm( initial=initial, user=request.user )

    return render_to_response("reports/new.html",
                { "google": FixMyStreetMap(pnt, True),
                  'GOOGLE_KEY': settings.GMAP_KEY,
                  "report_form": report_form,
                  "update_form": report_form.update_form,
                  'ward': report_form.ward },
                context_instance=RequestContext(request))
    
        
def show( request, report_id ):
    report = get_object_or_404(Report, id=report_id)
    subscribers = report.reportsubscriber_set.count() + 1
    return render_to_response("reports/show.html",
                { "report": report,
                  "subscribers": subscribers,
                  "ward":report.ward,
                  "updates": ReportUpdate.objects.filter(report=report, is_confirmed=True).order_by("created_at")[1:], 
                  "update_form": ReportUpdateForm(user=request.user,initial={}), 
                  "google":  FixMyStreetMap((report.point)) },
                context_instance=RequestContext(request))



########NEW FILE########
__FILENAME__ = subscribers
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect
from mainapp.models import Report, ReportSubscriber
from mainapp.forms import ReportSubscriberForm
from django.template import Context, RequestContext
from django.utils.translation import ugettext as _

def new( request, report_id ):
    report = get_object_or_404(Report, id=report_id)
    error_msg = None
    
    if request.method == 'POST':    
        form = ReportSubscriberForm( request.POST )
        if form.is_valid():
           subscriber = form.save( commit = False )
           subscriber.report = report
           subscriber.is_confirmed = request.user.is_authenticated()
           if report.is_subscribed(subscriber.email):
               error_msg = _("You are already subscribed to this report.")
           else:
               subscriber.save()
               return( HttpResponseRedirect( '/reports/subscribers/create/' ) ) 
    else:
        initial = {}
        if request.user.is_authenticated():
            initial['email'] = request.user.email
        form = ReportSubscriberForm(initial=initial,freeze_email=request.user.is_authenticated())
        
    return render_to_response("reports/subscribers/new.html",
                {   "subscriber_form": form,
                    "report":  report,
                    "error_msg": error_msg, },
                context_instance=RequestContext(request))

def create( request ):
    return render_to_response("reports/subscribers/create.html",
                { },
                context_instance=RequestContext(request))
            
def confirm( request, confirm_token ):
    subscriber = get_object_or_404(ReportSubscriber, confirm_token = confirm_token )
    subscriber.is_confirmed = True
    subscriber.save()
    
    return render_to_response("reports/subscribers/confirm.html",
                {   "subscriber": subscriber, },
                context_instance=RequestContext(request))
    
def unsubscribe(request, confirm_token ):
    subscriber = get_object_or_404(ReportSubscriber, confirm_token = confirm_token )
    report = subscriber.report
    subscriber.delete()
    return render_to_response("reports/subscribers/message.html",
                {   "message": _("You have unsubscribed from updates to:") +  report.title, },
                context_instance=RequestContext(request))
    
########NEW FILE########
__FILENAME__ = updates
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect
from mainapp.models import Report, ReportUpdate, Ward, FixMyStreetMap, ReportCategory
from mainapp.forms import ReportForm,ReportUpdateForm
from django.template import Context, RequestContext

def new( request, report_id ):
    report = get_object_or_404(Report, id=report_id)
    if request.method == 'POST':    
        update_form = ReportUpdateForm( request.POST, user=request.user, report=report )
        if update_form.is_valid():
            update = update_form.save()
            # redirect after a POST
            if update.is_confirmed:
                return( HttpResponseRedirect( report.get_absolute_url() ) )
            else:       
                return( HttpResponseRedirect( '/reports/updates/create/' ) )
                
    else:
        update_form = ReportUpdateForm(initial={},user=request.user)
        
    return render_to_response("reports/show.html",
                {   "report": report,
                    "google":  FixMyStreetMap(report.point),
                    "update_form": update_form,
                 },
                context_instance=RequestContext(request))    

def create( request ):
    return render_to_response("reports/updates/create.html",
                {  },
                context_instance=RequestContext(request))    

def confirm( request, confirm_token ):
    update = get_object_or_404(ReportUpdate, confirm_token = confirm_token )
    
    if update.is_confirmed:
        return( HttpResponseRedirect( update.report.get_absolute_url() ))
    
    update.confirm()
    
    # redirect to report    
    return( HttpResponseRedirect( update.report.get_absolute_url() ))

########NEW FILE########
__FILENAME__ = wards
from django.shortcuts import render_to_response, get_object_or_404
from mainapp.models import City, Ward, WardMap, Report
from django.template import Context, RequestContext
from django.db import connection
from django.utils.translation import ugettext_lazy, ugettext as _
from django.core.paginator import Paginator, InvalidPage, EmptyPage

import datetime
    
def show( request, ward ):
    
    try:
        page_no = int(request.GET.get('page', '1'))
    except ValueError:
        page_no = 1

    all_reports = Report.objects.filter( ward = ward, is_confirmed = True ).extra( select = { 'status' : """
        CASE 
        WHEN age( clock_timestamp(), created_at ) < interval '1 month' AND is_fixed = false THEN 'New Problems'
        WHEN age( clock_timestamp(), created_at ) > interval '1 month' AND is_fixed = false THEN 'Older Unresolved Problems'
        WHEN age( clock_timestamp(), fixed_at ) < interval '1 month' AND is_fixed = true THEN 'Recently Fixed'
        WHEN age( clock_timestamp(), fixed_at ) > interval '1 month' AND is_fixed = true THEN 'Old Fixed'
        ELSE 'Unknown Status'
        END """,
        'status_int' : """
        CASE 
        WHEN age( clock_timestamp(), created_at ) < interval '1 month' AND is_fixed = false THEN 0
        WHEN age( clock_timestamp(), created_at ) > interval '1 month' AND is_fixed = false THEN 1
        WHEN age( clock_timestamp(), fixed_at ) < interval '1 month' AND is_fixed = true THEN 2
        WHEN age( clock_timestamp(), fixed_at ) > interval '1 month' AND is_fixed = true THEN 3
        ELSE 4
        END """ } ).order_by('-created_at') 
        
    paginator = Paginator(all_reports, 100) 
    try:
        page = paginator.page(page_no)
    except (EmptyPage, InvalidPage):
        page = paginator.page(paginator.num_pages)
        
    reports = sorted(page.object_list,key=lambda o: o.status_int )
    google = WardMap(ward,reports)
    
    return render_to_response("wards/show.html",
                {"ward": ward,
                 "google": google,
                 "page":page,
                 "reports": reports                },
                context_instance=RequestContext(request))

def show_by_id(request,ward_id):
    ward = get_object_or_404(Ward, id=ward_id)
    return(show(request,ward))

def show_by_number( request, city_id, ward_no ):
    ward = get_object_or_404( Ward,city__id=city_id, number=ward_no)
    return(show(request,ward))

def show_by_slug( request, city_slug, ward_slug ):
    ward = get_object_or_404( Ward,city__slug=city_slug, slug=ward_slug)
    return(show(request,ward))

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
__FILENAME__ = batch_reports
#!/usr/bin/env python
# encoding: utf-8

import sys
import os

path = os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))))
sys.path.append(path)
os.environ['DJANGO_SETTINGS_MODULE'] = 'fixmystreet.settings'

import datetime
from datetime import datetime as dt
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from fixmystreet.mainapp.models import Ward,Report
from fixmystreet import settings


reminder_email_count = 0
councillor_email_count = 0
#
## send new reports to ward councillors                    
#for ward in Ward.objects.all():    
#    new_reports = ward.report_set.filter(ward=ward,is_confirmed=True,is_fixed=False,sent_at__isnull=True).order_by("-created_at")                        
#    if len(new_reports) > 0 :
#        subject = render_to_string("emails/batch_reports/new_reports/subject.txt", 
#                               {'ward': ward })
#        message = render_to_string("emails/batch_reports/new_reports/message.html", 
#                               {'new_reports': new_reports, 'ward': ward })
#        
#        msg = EmailMessage(subject, message,settings.EMAIL_FROM_USER,[ward.councillor.email, settings.ADMIN_EMAIL])
#        msg.content_subtype = "html"  # Main content is now text/html
#        msg.send()
#
#        print "sending report for ward " + ward.name
#        new_reports.update(sent_at=dt.now())
#        councillor_email_count += 1

# send old reports that have not been updated
one_month_ago = dt.today() - datetime.timedelta(days=31)
reminder_reports = Report.objects.filter(is_confirmed=True, is_fixed = False, reminded_at__lte=one_month_ago, updated_at__lte=one_month_ago ).order_by("ward","-created_at")  

for report in reminder_reports:
    subject = render_to_string("emails/batch_reports/reminders/subject.txt", 
                               {'report': report })
    message = render_to_string("emails/batch_reports/reminders/message.txt", 
                               {'report': report })

    send_mail(subject, message, settings.EMAIL_FROM_USER,[report.first_update().email], fail_silently=False)

    report.reminded_at = dt.now()
    report.save()
    reminder_email_count += 1

# notify admin reports were run
send_mail('Ward Summary Reports Run %s' % ( dt.now()  ), 
          '%d Report Summaries Sent to Councillors\n%d Reminders Sent' %( councillor_email_count, reminder_email_count ), 
              settings.EMAIL_FROM_USER,[settings.ADMIN_EMAIL], fail_silently=False)


########NEW FILE########
__FILENAME__ = settings
# Django settings for fixmystreet project.
import os
import logging

PROJECT_PATH = os.path.abspath(os.path.dirname(__file__))
POSTGIS_TEMPLATE = 'template_postgis'

logging.basicConfig(
    level = logging.DEBUG,
    format = '%(asctime)s %(levelname)s %(message)s',
    filename = '/tmp/fixmystreet.log',
    filemode = 'w'
)

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_PATH, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin_media/'

# ensure large uploaded files end up with correct permissions.  See
# http://docs.djangoproject.com/en/dev/ref/settings/#file-upload-permissions

FILE_UPLOAD_PERMISSIONS = 0644
DATE_FORMAT = "l, F jS, Y"

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.load_template_source',
)

# include request object in template to determine active page
TEMPLATE_CONTEXT_PROCESSORS = (
  'django.core.context_processors.request',
  'django.contrib.auth.context_processors.auth',
  'django.core.context_processors.csrf',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
#    'django.middleware.csrf.CsrfResponseMiddleware',
    'mainapp.middleware.subdomains.SubdomainMiddleware',
    'mainapp.middleware.SSLMiddleware.SSLRedirect',
)


LANGUAGES = (
  ('en','English'),
  ('fr', 'French'),
)


ROOT_URLCONF = 'fixmystreet.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_PATH, 'templates')
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.gis',
    'registration',
    'google_analytics',
    'transmeta',
    'social_auth',
    'mainapp',
)

AUTH_PROFILE_MODULE = 'mainapp.UserProfile'

AUTHENTICATION_BACKENDS = (
    'social_auth.backends.twitter.TwitterBackend',
    'social_auth.backends.facebook.FacebookBackend',
#    'social_auth.backends.google.GoogleOAuthBackend',
#    'social_auth.backends.google.GoogleOAuth2Backend',
#    'social_auth.backends.google.GoogleBackend',
#    'social_auth.backends.yahoo.YahooBackend',
#    'social_auth.backends.OpenIDBackend',
    'django.contrib.auth.backends.ModelBackend',
#    'mainapp.tests.testsocial_auth.dummy_socialauth.DummyBackend',
)

CACHE_MIDDLEWARE_ANONYMOUS_ONLY =True
SOCIAL_AUTH_USER_MODEL = 'mainapp.FMSUser'
SOCIAL_AUTH_ASSOCIATE_BY_MAIL = True
ACCOUNT_ACTIVATION_DAYS = 14
SOCIAL_AUTH_EXTRA_DATA = False
SOCIAL_AUTH_COMPLETE_URL_NAME = 'socialauth_complete'
LOGIN_ERROR_URL = '/accounts/login/error/'
SOCIAL_AUTH_ERROR_KEY = 'socialauth_error'
LOGIN_REDIRECT_URL = '/accounts/home/'
LOGIN_DISABLED = False

#################################################################################
# These variables Should be defined in the local settings file
#################################################################################
#
#DATABASES = {
#    'default': {
#        'ENGINE': 'django.contrib.gis.db.backends.postgis',
#        'NAME': '',
#        'USER': '',
#        'PASSWORD': ''
#    }
#}
#
#EMAIL_USE_TLS =
#EMAIL_HOST =
#EMAIL_HOST_USER =
#EMAIL_HOST_PASSWORD =
#EMAIL_PORT =
#EMAIL_FROM_USER =
#DEBUG =
#LOCAL_DEV =
#SITE_URL = http://localhost:8000
#SECRET_KEY=
#GMAP_KEY=
#
#ADMIN_EMAIL =
#ADMINS =
#
# ----- social_auth consumer id's ----- #
#TWITTER_CONSUMER_KEY         = ''
#TWITTER_CONSUMER_SECRET      = ''
#FACEBOOK_APP_ID              = ''
#FACEBOOK_API_SECRET          = ''
#####################################################################################

# import local settings overriding the defaults
# local_settings.py is machine independent and should not be checked in

try:
    from local_settings import *
except ImportError:
    try:
        from mod_python import apache
        apache.log_error( "local_settings.py not set; using default settings", apache.APLOG_NOTICE )
    except ImportError:
        import sys
        sys.stderr.write( "local_settings.py not set; using default settings\n" )


# Using django_testview from here (add 'TESTVIEW' to your local settings): 
# https://github.com/visiblegovernment/django_testview

if DEBUG and globals().has_key('TESTVIEW'):
    INSTALLED_APPS += ('django_testview',)


if DEBUG:
    SOCIAL_AUTH_IMPORT_BACKENDS = (
                                   'mainapp.tests.testsocial_auth',
                                   )

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings
from django.http import HttpResponseRedirect
from django.contrib import admin
from mainapp.feeds import LatestReports, CityIdFeed, CitySlugFeed, WardIdFeed, WardSlugFeed,LatestUpdatesByReport
from mainapp.models import City
from social_auth.views import auth as social_auth
from social_auth.views import disconnect as social_disconnect
from registration.views import register
from mainapp.forms import FMSNewRegistrationForm,FMSAuthenticationForm
from mainapp.views.account import SUPPORTED_SOCIAL_PROVIDERS
from django.contrib.auth import views as auth_views
from mainapp.views.mobile import open311v2 
import mainapp.views.cities as cities


SSL_ON = not settings.DEBUG
    
admin.autodiscover()
urlpatterns = patterns('',
    (r'^admin/password_reset/$', 'django.contrib.auth.views.password_reset',{'SSL':SSL_ON}),
    (r'^password_reset/done/$', 'django.contrib.auth.views.password_reset_done'),
    (r'^reset/(?P<uidb36>[-\w]+)/(?P<token>[-\w]+)/$', 'django.contrib.auth.views.password_reset_confirm'),
    (r'^reset/done/$', 'django.contrib.auth.views.password_reset_complete'),
)

if not settings.LOGIN_DISABLED:
    urlpatterns += patterns('',
        (r'^admin/', admin.site.urls,{'SSL':SSL_ON}),
        (r'^i18n/', include('django.conf.urls.i18n')),
        url(r'^login/(?P<backend>[^/]+)/$', social_auth, name='begin'),
        url(r'^disconnect/(?P<backend>[^/]+)/$', social_disconnect, name='socialdisconnect'),
    )

urlpatterns += patterns('',
    (r'^feeds/cities/(\d+)$', CityIdFeed()), # backwards compatibility
    (r'^feeds/wards/(\d+)$', WardIdFeed()), # backwards compatibility
    (r'^feeds/cities/([^/]+).rss', CitySlugFeed()),
    (r'^feeds/cities/([^/]+)/wards/(\S+).rss', WardSlugFeed()),
    (r'^feeds/reports/$', LatestReports()), # backwards compatibility
    (r'^feeds/reports.rss$', LatestReports()),
)

urlpatterns += patterns('mainapp.views.main',
    (r'^$', 'home', {}, 'home_url_name'),
    (r'^search', 'search_address'),
    (r'about/$', 'about',{}, 'about_url_name'),
    (r'^about/(\S+)$', 'show_faq'),
    (r'posters/$', 'posters',{}, 'posters'),
    (r'privacy/$', 'privacy',{}, 'privacy'),

)


urlpatterns += patterns('mainapp.views.promotion',
    (r'^promotions/(\w+)$', 'show'),
)

urlpatterns += patterns('mainapp.views.wards',
    (r'^wards/(\d+)', 'show_by_id'), # support old url format       
    (r'^cities/(\S+)/wards/(\S+)/', 'show_by_slug'),           
    (r'^cities/(\d+)/wards/(\d+)', 'show_by_number'),           
)

urlpatterns += patterns('',
    (r'^cities/(\d+)$', cities.show_by_id ), # support old url format   
    (r'^cities/(\S+)/$', cities.show_by_slug ),    
    (r'^cities/$', cities.index, {}, 'cities_url_name'),
)

urlpatterns += patterns( 'mainapp.views.reports.updates',
    (r'^reports/updates/confirm/(\S+)', 'confirm'), 
    (r'^reports/updates/create/', 'create'), 
    (r'^reports/(\d+)/updates/', 'new'),
)


urlpatterns += patterns( 'mainapp.views.reports.subscribers',
    (r'^reports/subscribers/confirm/(\S+)', 'confirm'), 
    (r'^reports/subscribers/unsubscribe/(\S+)', 'unsubscribe'),
    (r'^reports/subscribers/create/', 'create'),
    (r'^reports/(\d+)/subscribers', 'new'),
)

urlpatterns += patterns( 'mainapp.views.reports.flags',
    (r'^reports/(\d+)/flags/thanks', 'thanks'),
    (r'^reports/(\d+)/flags', 'new'),
)

urlpatterns += patterns('mainapp.views.reports.main',
    (r'^reports/(\d+)$', 'show'),       
    (r'^reports/', 'new'),
)

urlpatterns += patterns('mainapp.views.contact',
    (r'^contact/thanks', 'thanks'),
    (r'^contact', 'new', {}, 'contact_url_name'),
)

urlpatterns += patterns('mainapp.views.ajax',
    (r'^ajax/categories/(\d+)', 'category_desc'),
)


urlpatterns += patterns('',
 url('^accounts/register/$', register, {'SSL':SSL_ON , 
                                        'form_class': FMSNewRegistrationForm,
                                         'extra_context': 
                                    { 'providers': SUPPORTED_SOCIAL_PROVIDERS } },name='registration_register'),
 url('^accounts/login/$',  auth_views.login, {'SSL':SSL_ON, 
                                              'template_name':'registration/login.html',
                                              'authentication_form':FMSAuthenticationForm,
                                              'extra_context': 
                                              { 'providers': SUPPORTED_SOCIAL_PROVIDERS, 'login_disabled': settings.LOGIN_DISABLED }}, name='auth_login'), 
 url(r'^accounts/logout/$',  auth_views.logout,
                           {'SSL':SSL_ON,
                            'next_page': '/'}, name='auth_logout' ),
 (r'^accounts/', include('registration.urls') )
)
 
urlpatterns += patterns('mainapp.views.account',
    url(r'^accounts/home/', 'home',{ 'SSL':SSL_ON },  name='account_home'),
    url(r'^accounts/edit/', 'edit', {'SSL':SSL_ON }, name='account_edit'),
    (r'^accounts/login/error/$', 'error'),
    url(r'^accounts/complete/(?P<backend>[^/]+)/$', 'socialauth_complete', {'SSL':SSL_ON }, name='socialauth_complete'),
)

urlpatterns += patterns('',
    (r'^open311/v2/', open311v2.xml.urls ),
)

if settings.DEBUG and 'TESTVIEW' in settings.__members__:
    urlpatterns += patterns ('',
    (r'^testview',include('django_testview.urls')))


#The following is used to serve up local media files like images
if settings.LOCAL_DEV:
    baseurlregex = r'^media/(?P<path>.*)$'
    urlpatterns += patterns('',
        (baseurlregex, 'django.views.static.serve',
        {'document_root':  settings.MEDIA_ROOT}),
    )

########NEW FILE########
