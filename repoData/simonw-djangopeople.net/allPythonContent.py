__FILENAME__ = admin
from django.contrib import admin
from djangopeople.models import Country, CountrySite, Region, DjangoPerson, PortfolioSite

class CountryAdmin(admin.ModelAdmin):
    list_display = ('name',)

class CountrySiteAdmin(admin.ModelAdmin):
    pass

class RegionAdmin(admin.ModelAdmin):
    list_display = ('name',)

class DjangoPersonAdmin(admin.ModelAdmin):
    list_display = ('user', 'profile_views')
    raw_id_fields = ('user',)

class PortfolioSiteAdmin(admin.ModelAdmin):
    pass

admin.site.register(Country, CountryAdmin)
admin.site.register(CountrySite, CountrySiteAdmin)
admin.site.register(Region, RegionAdmin)
admin.site.register(DjangoPerson, DjangoPersonAdmin)
admin.site.register(PortfolioSite, PortfolioSiteAdmin)

########NEW FILE########
__FILENAME__ = api
from django.http import HttpResponse, HttpResponseRedirect
import datetime
from machinetags.models import MachineTaggedItem
from django.conf import settings

def irc_lookup(request, irc_nick):
    try:
        person = MachineTaggedItem.objects.get(
            namespace = 'im', predicate = 'django', value = irc_nick
        ).content_object
    except MachineTaggedItem.DoesNotExist:
        return HttpResponse('no match', mimetype = 'text/plain')
    return HttpResponse(
        u'%s, %s, %s, http://djangopeople.net/%s/' % (person, person.location_description, person.country, person.user.username), mimetype = 'text/plain'
    )

def irc_redirect(request, irc_nick):
    try:
        person = MachineTaggedItem.objects.get(
            namespace = 'im', predicate = 'django', value = irc_nick
        ).content_object
    except MachineTaggedItem.DoesNotExist:
        return HttpResponse('no match', mimetype = 'text/plain')
    return HttpResponseRedirect(
        'http://djangopeople.net/%s/' % person.user.username
    )

def irc_spotted(request, irc_nick):
    if request.POST.get('sekrit', '') != settings.API_PASSWORD:
        return api_response('BAD_SEKRIT')
    
    try:
        person = MachineTaggedItem.objects.get(
            namespace = 'im', predicate = 'django', value = irc_nick
        ).content_object
    except MachineTaggedItem.DoesNotExist:
        return api_response('NO_MATCH')
    
    if not person.irc_tracking_allowed():
        return api_response('TRACKING_FORBIDDEN')
    
    first_time_seen = not person.last_active_on_irc
    
    person.last_active_on_irc = datetime.datetime.now()
    person.save()
    
    if first_time_seen:
        return api_response('FIRST_TIME_SEEN')
    else:
        return api_response('TRACKED')

def api_response(code):
    return HttpResponse(code, mimetype='text/plain')


########NEW FILE########
__FILENAME__ = clustering

from clusterlizard.clusterer import Clusterer

from django.http import HttpResponse
from djangopeople.models import *
from django.db.models import Q

import simplejson
import math


def latlong_to_mercator(lat, long):
    x = long * 20037508.34 / 180
    y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180)
    y = y * 20037508.34 / 180;
    return x, y


def mercator_to_latlong(x, y):
    long = (x / 20037508.34) * 180
    lat = (y / 20037508.34) * 180
    lat = 180/math.pi * (2 * math.atan(math.exp(lat * math.pi / 180)) - math.pi / 2)
    return lat, long


def input_generator():
    """
    The input to ClusterLizard should be a generator that yields (mx,my,id) tuples.
    This function reads them from the DjangoPeople models.
    """
    for person in DjangoPerson.objects.all():
        mx, my = latlong_to_mercator(person.latitude, person.longitude)
        yield (mx, my, person.id)
    
    
def save_clusters(clusters, zoom):
    """
    The output function provided to ClusterLizard should be a
    function that takes 'clusters', a set of clusters, and 'zoom',
    the integer Google zoom level.
    """
    for cluster in clusters:
        lat, long = mercator_to_latlong(*cluster.mean)
        ClusteredPoint.objects.create(
            latitude = lat,
            longitude = long,
            number = len(cluster),
            zoom = zoom,
            djangoperson_id = len(cluster) == 1 and list(cluster.points)[0][2] or None,
        )


def progress(done, left, took, zoom, eta):
    """
    You can also pass in an optional progress callback.
    """
    print "Iter %s (%s clusters) [%.3f secs] [zoom: %s] [ETA %s]" % (done, left, took, zoom, eta)
    

def as_json(request, x2, y1, x1, y2, z):
    """
    View that returns clusters for the given zoom level as JSON.
    """
    x1, y1, x2, y2 = map(float, (x1, y1, x2, y2))
    if y1 > y2:
        y1, y2 = y2, y1
    
    if x1 < x2: # View not crossing the date line
        query = ClusteredPoint.objects.filter(latitude__gt=y1, latitude__lt=y2, longitude__gt=x1, longitude__lt=x2, zoom=z)
    else: # View crossing the date line
        query = ClusteredPoint.objects.filter(Q(longitude__lt=x1) | Q(longitude__gt=x2, latitude__gt=y1, latitude__lt=y2), zoom=z)
    
    points = []
    for cluster in query:
        if cluster.djangoperson:
            points.append((cluster.longitude, cluster.latitude, cluster.number, cluster.djangoperson.get_absolute_url()))
        else:
            points.append((cluster.longitude, cluster.latitude, cluster.number, None))
    return HttpResponse(simplejson.dumps(points))
    


def run():
    """
    Runs the clustering, clearing the DB first.
    """
    ClusteredPoint.objects.all().delete()
    clusterer = Clusterer(
        input_generator(),
        save_clusters,
        progress,
    )
    clusterer.run()
########NEW FILE########
__FILENAME__ = constants
SERVICES = (
    # shortname, name, icon
    ('flickr', 'Flickr', '/static/img/services/flickr.png'),
    ('delicious', 'del.icio.us', '/static/img/services/delicious.png'),
    ('magnolia', 'Ma.gnolia.com', '/static/img/services/magnolia.png'),
    ('twitter', 'Twitter', '/static/img/services/twitter.png'),
    ('facebook', 'Facebook', '/static/img/services/facebook.png'),
    ('linkedin', 'LinkedIn', '/static/img/services/linkedin.png'),
    ('pownce', 'Pownce', '/static/img/services/pownce.png'),
    ('djangosnippets', 'djangosnippets.org', '/static/img/services/django.png'),
    ('djangosites', 'DjangoSites.org', '/static/img/services/django.png'),
)
SERVICES_DICT = dict([(r[0], r) for r in SERVICES])

IMPROVIDERS = (
    # shortname, name, icon
    ('aim', 'AIM', '/static/img/improviders/aim.png'),
    ('yim', 'Y!IM', '/static/img/improviders/yim.png'),
    ('gtalk', 'GTalk', '/static/img/improviders/gtalk.png'),
    ('msn', 'MSN', '/static/img/improviders/msn.png'),
    ('jabber', 'Jabber', '/static/img/improviders/jabber.png'),
    ('django', '#django IRC', '/static/img/services/django.png'),
)
IMPROVIDERS_DICT = dict([(r[0], r) for r in IMPROVIDERS])

# Convenience mapping from fields to machinetag (namespace, predicate)
MACHINETAGS_FROM_FIELDS = dict(
    [('service_%s' % shortname, ('services', shortname))
     for shortname, name, icon in SERVICES] + 
    [('im_%s' % shortname, ('im', shortname))
     for shortname, name, icon in IMPROVIDERS] + [
        ('privacy_search', ('privacy', 'search')),
        ('privacy_email', ('privacy', 'email')),
        ('privacy_im', ('privacy', 'im')),
        ('privacy_irctrack', ('privacy', 'irctrack')),
    ]
)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.forms.forms import BoundField
from django.db.models import ObjectDoesNotExist
from djangopeople.models import DjangoPerson, Country, Region, User, RESERVED_USERNAMES
from djangopeople.groupedselect import GroupedChoiceField
from djangopeople.constants import SERVICES, IMPROVIDERS
from tagging.forms import TagField

def region_choices():
    # For use with GroupedChoiceField
    regions = list(Region.objects.select_related().order_by('country', 'name'))
    groups = [(False, (('', '---'),))]
    current_country = False
    current_group = []
    
    for region in regions:
        if region.country.name != current_country:
            if current_group:
                groups.append((current_country, current_group))
                current_group = []
            current_country = region.country.name
        current_group.append((region.code, region.name))
    if current_group:
        groups.append((current_country, current_group))
        current_group = []
    
    return groups

def not_in_the_atlantic(self):
    if self.cleaned_data.get('latitude', '') and self.cleaned_data.get('longitude', ''):
        lat = self.cleaned_data['latitude']
        lon = self.cleaned_data['longitude']
        if 43 < lat < 45 and -39 < lon < -33:
            raise forms.ValidationError("Drag and zoom the map until the crosshair matches your location")
    return self.cleaned_data['location_description']

class SignupForm(forms.Form):
    def __init__(self, *args, **kwargs):
        # Dynamically add the fields for IM providers / external services
        if 'openid' in kwargs:
            self.openid = True
            kwargs.pop('openid')
        else:
            self.openid = False
        
        super(SignupForm, self).__init__(*args, **kwargs)
        self.service_fields = []
        for shortname, name, icon in SERVICES:
            field = forms.URLField(
                max_length=255, required=False, label=name
            )
            self.fields['service_' + shortname] = field
            self.service_fields.append({
                'label': name,
                'shortname': shortname,
                'id': 'service_' + shortname,
                'icon': icon,
                'field': BoundField(self, field, 'service_' + shortname),
            })
        
        self.improvider_fields = []
        for shortname, name, icon in IMPROVIDERS:
            field = forms.CharField(
                max_length=50, required=False, label=name
            )
            self.fields['im_' + shortname] = field
            self.improvider_fields.append({
                'label': name,
                'shortname': shortname,
                'id': 'im_' + shortname,
                'icon': icon,
                'field': BoundField(self, field, 'im_' + shortname),
            })
    
    # Fields for creating a User object
    username = forms.RegexField('^[a-zA-Z0-9]+$', min_length=3, max_length=30)
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()
    password1 = forms.CharField(widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(widget=forms.PasswordInput, required=False)
    
    # Fields for creating a DjangoPerson profile
    bio = forms.CharField(widget=forms.Textarea, required=False)
    blog = forms.URLField(required=False)
    
    country = forms.ChoiceField(choices = [('', '')] + [
        (c.iso_code, c.name) for c in Country.objects.all()
    ])
    latitude = forms.FloatField(min_value=-90, max_value=90)
    longitude = forms.FloatField(min_value=-180, max_value=180)
    location_description = forms.CharField(max_length=50)
    
    region = GroupedChoiceField(required=False, choices=region_choices())
    
    privacy_search = forms.ChoiceField(
        choices = (
            ('public', 
             'Allow search engines to index my profile page (recommended)'),
            ('private', "Don't allow search engines to index my profile page"),
        ), widget = forms.RadioSelect, initial='public'
    )
    privacy_email = forms.ChoiceField(
        choices = (
            ('public', 'Anyone can see my e-mail address'),
            ('private', 'Only logged-in users can see my e-mail address'),
            ('never', 'No one can ever see my e-mail address'),
        ), widget = forms.RadioSelect, initial='private'
    )
    privacy_im = forms.ChoiceField(
        choices = (
            ('public', 'Anyone can see my IM details'),
            ('private', 'Only logged-in users can see my IM details'),
        ), widget = forms.RadioSelect, initial='private'
    )
    privacy_irctrack = forms.ChoiceField(
        choices = (
            ('public', 'Keep track of the last time I was seen on IRC (requires your IRC nick)'),
            ('private', "Don't record the last time I was seen on IRC"),
        ), widget = forms.RadioSelect, initial='public'
    )
    looking_for_work = forms.ChoiceField(
        choices = (
            ('', 'Not looking for work at the moment'),
            ('freelance', 'Looking for freelance work'),
            ('full-time', 'Looking for full-time work'),
        ), required=False #, widget = forms.RadioSelect, initial=''
    )
    
    #skilltags = TagField(required=False)
    
    # Upload a photo is a separate page, because if validation fails we 
    # don't want to tell them to upload it all over again
    #   photo = forms.ImageField(required=False)
    
    # Fields used to create machinetags
    
    # Validation
    def clean_password1(self):
        "Only required if NO openid set for this form"
        if not self.openid and not self.cleaned_data.get('password1', ''):
            raise forms.ValidationError('Password is required')
        return self.cleaned_data['password1']
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1', '')
        password2 = self.cleaned_data.get('password2', '')
        if password1.strip() and password1 != password2:
            raise forms.ValidationError('Passwords must match')
        return self.cleaned_data['password2']
    
    def clean_username(self):
        already_taken = 'That username is unavailable'
        username = self.cleaned_data['username'].lower()
        
        # No reserved usernames, or anything that looks like a 4 digit year 
        if username in RESERVED_USERNAMES or (len(username) == 4 and username.isdigit()):
            raise forms.ValidationError(already_taken)
        
        try:
            user = User.objects.get(username = username)
        except User.DoesNotExist:
            pass
        else:
            raise forms.ValidationError(already_taken)
        
        return username
    
    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            user = User.objects.get(email = email)
        except User.DoesNotExist:
            pass
        else:
            raise forms.ValidationError('That e-mail is already in use')
        return email
    
    def clean_region(self):
        # If a region is selected, ensure it matches the selected country
        if self.cleaned_data['region']:
            try:
                region = Region.objects.get(
                    code = self.cleaned_data['region'],
                    country__iso_code = self.cleaned_data['country']
                )
            except ObjectDoesNotExist:
                raise forms.ValidationError(
                    'The region you selected does not match the country'
                )
        return self.cleaned_data['region']

    clean_location_description = not_in_the_atlantic

class PhotoUploadForm(forms.Form):
    photo = forms.ImageField()

class SkillsForm(forms.Form):
    skills = TagField(label='Change skills')

class BioForm(forms.Form):
    bio = forms.CharField(widget=forms.Textarea, required=False)

class AccountForm(forms.Form):
    openid_server = forms.URLField(required=False)
    openid_delegate = forms.URLField(required=False)

class LocationForm(forms.Form):
    country = forms.ChoiceField(choices = [('', '')] + [
        (c.iso_code, c.name) for c in Country.objects.all()
    ])
    latitude = forms.FloatField(min_value=-90, max_value=90)
    longitude = forms.FloatField(min_value=-180, max_value=180)
    location_description = forms.CharField(max_length=50)
    
    region = GroupedChoiceField(required=False, choices=region_choices())
    
    def clean_region(self):
        # If a region is selected, ensure it matches the selected country
        if self.cleaned_data['region']:
            try:
                region = Region.objects.get(
                    code = self.cleaned_data['region'],
                    country__iso_code = self.cleaned_data['country']
                )
            except ObjectDoesNotExist:
                raise forms.ValidationError(
                    'The region you selected does not match the country'
                )
        return self.cleaned_data['region']
    
    clean_location_description = not_in_the_atlantic

class FindingForm(forms.Form):
    def __init__(self, *args, **kwargs):
        # Dynamically add the fields for IM providers / external services
        self.person = kwargs.pop('person') # So we can validate e-mail later
        super(FindingForm, self).__init__(*args, **kwargs)
        self.service_fields = []
        for shortname, name, icon in SERVICES:
            field = forms.URLField(
                max_length=255, required=False, label=name
            )
            self.fields['service_' + shortname] = field
            self.service_fields.append({
                'label': name,
                'shortname': shortname,
                'id': 'service_' + shortname,
                'icon': icon,
                'field': BoundField(self, field, 'service_' + shortname),
            })
        
        self.improvider_fields = []
        for shortname, name, icon in IMPROVIDERS:
            field = forms.CharField(
                max_length=50, required=False, label=name
            )
            self.fields['im_' + shortname] = field
            self.improvider_fields.append({
                'label': name,
                'shortname': shortname,
                'id': 'im_' + shortname,
                'icon': icon,
                'field': BoundField(self, field, 'im_' + shortname),
            })
    
    email = forms.EmailField()
    blog = forms.URLField(required=False)
    privacy_search = forms.ChoiceField(
        choices = (
            ('public', 
             'Allow search engines to index my profile page (recommended)'),
            ('private', "Don't allow search engines to index my profile page"),
        ), widget = forms.RadioSelect, initial='public'
    )
    privacy_email = forms.ChoiceField(
        choices = (
            ('public', 'Anyone can see my e-mail address'),
            ('private', 'Only logged-in users can see my e-mail address'),
            ('never', 'No one can ever see my e-mail address'),
        ), widget = forms.RadioSelect, initial='private'
    )
    privacy_im = forms.ChoiceField(
        choices = (
            ('public', 'Anyone can see my IM details'),
            ('private', 'Only logged-in users can see my IM details'),
        ), widget = forms.RadioSelect, initial='private'
    )
    privacy_irctrack = forms.ChoiceField(
        choices = (
            ('public', 'Keep track of the last time I was seen on IRC (requires your IRC nick)'),
            ('private', "Don't record the last time I was seen on IRC"),
        ), widget = forms.RadioSelect, initial='public'
    )
    looking_for_work = forms.ChoiceField(
        choices = (
            ('', 'Not looking for work at the moment'),
            ('freelance', 'Looking for freelance work'),
            ('full-time', 'Looking for full-time work'),
        ), required=False #, widget = forms.RadioSelect, initial=''
    )
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(
            email = email
        ).exclude(djangoperson = self.person).count() > 0:
            raise forms.ValidationError('That e-mail is already in use')
        return email

class PortfolioForm(forms.Form):
    def __init__(self, *args, **kwargs):
        # Dynamically add the fields for IM providers / external services
        assert 'person' in kwargs, 'person is a required keyword argument'
        person = kwargs.pop('person')
        super(PortfolioForm, self).__init__(*args, **kwargs)
        self.portfolio_fields = []
        initial_data = {}
        num = 1
        for site in person.portfoliosite_set.all():
            url_field = forms.URLField(
                max_length=255, required=False, label='URL %d' % num
            )
            title_field = forms.CharField(
                max_length=100, required=False, label='Title %d' % num
            )
            self.fields['title_%d' % num] = title_field
            self.fields['url_%d' % num] = url_field
            self.portfolio_fields.append({
                'title_field': BoundField(self, title_field, 'title_%d' % num),
                'url_field': BoundField(self, url_field, 'url_%d' % num),
                'title_id': 'id_title_%d' % num,
                'url_id': 'id_url_%d' % num,
            })
            initial_data['title_%d' % num] = site.title
            initial_data['url_%d' % num] = site.url
            num += 1
        
        # Add some more empty ones
        for i in range(num, num + 3):
            url_field = forms.URLField(
                max_length=255, required=False, label='URL %d' % i
            )
            title_field = forms.CharField(
                max_length=100, required=False, label='Title %d' % i
            )
            self.fields['title_%d' % i] = title_field
            self.fields['url_%d' % i] = url_field
            self.portfolio_fields.append({
                'title_field': BoundField(self, title_field, 'title_%d' % i),
                'url_field': BoundField(self, url_field, 'url_%d' % i),
                'title_id': 'id_title_%d' % i,
                'url_id': 'id_url_%d' % i,
            })
        
        self.initial = initial_data
        
        # Add custom validator for each url field
        for key in [k for k in self.fields if k.startswith('url_')]:
            setattr(self, 'clean_%s' % key, make_validator(key, self))

def make_validator(key, form):
    def check():
        if form.cleaned_data.get(key.replace('url_', 'title_')) and \
            not form.cleaned_data.get(key):
            raise forms.ValidationError, 'You need to provide a URL'
        return form.cleaned_data.get(key)
    return check

########NEW FILE########
__FILENAME__ = groupedselect
from django import forms
from django.utils.safestring import mark_safe
# From http://www.djangosnippets.org/snippets/200/

# widget for select with optional opt groups
# modified from ticket 3442
# not sure if it's better but it doesn't force all options to be grouped

# Example:
# groceries = ((False, (('milk','milk'), (-1,'eggs'))), ('fruit', ((0,'apple'), (1,'orange'))), ('', (('yum','beer'), )),) 
# grocery_list = GroupedChoiceField(choices=groceries)

# Renders:
# <select name="grocery_list" id="id_grocery_list">
#   <option value="milk">milk</option>
#   <option value="-1">eggs</option>
#   <optgroup label="fruit">
#     <option value="0">apple</option>
#     <option value="1">orange</option>
#   </optgroup>
#   <option value="yum">beer</option>
# </select>

class GroupedSelect(forms.Select): 
    def render(self, name, value, attrs=None, choices=()):
        from django.utils.html import escape
        from django.forms.util import flatatt, smart_unicode
        if value is None: value = '' 
        final_attrs = self.build_attrs(attrs, name=name) 
        output = [u'<select%s>' % flatatt(final_attrs)] 
        str_value = smart_unicode(value)
        for group_label, group in self.choices: 
            if group_label: # should belong to an optgroup
                group_label = smart_unicode(group_label) 
                output.append(u'<optgroup label="%s">' % escape(group_label)) 
            for k, v in group:
                option_value = smart_unicode(k)
                option_label = smart_unicode(v) 
                selected_html = (option_value == str_value) and u' selected="selected"' or ''
                output.append(u'<option value="%s"%s>%s</option>' % (escape(option_value), selected_html, escape(option_label))) 
            if group_label:
                output.append(u'</optgroup>') 
        output.append(u'</select>') 
        return mark_safe(u'\n'.join(output))

# field for grouped choices, handles cleaning of funky choice tuple
class GroupedChoiceField(forms.ChoiceField):
    def __init__(self, choices=(), required=True, widget=GroupedSelect, label=None, initial=None, help_text=None):
        super(forms.ChoiceField, self).__init__(required, widget, label, initial, help_text)
        self.choices = choices
        
    def clean(self, value):
        """
        Validates that the input is in self.choices.
        """
        value = super(forms.ChoiceField, self).clean(value)
        if value in (None, ''):
            value = u''
        value = forms.util.smart_unicode(value)
        if value == u'':
            return value
        valid_values = []
        for group_label, group in self.choices:
            valid_values += [str(k) for k, v in group]
        if value not in valid_values:
            raise ValidationError(gettext(u'Select a valid choice. That choice is not one of the available choices.'))
        return value

########NEW FILE########
__FILENAME__ = importers
try:
    from xml.etree import cElementTree as ET
except ImportError:
    from elementtree import ElementTree as ET

from djangopeople.models import Country, Region

def import_countries(fp):
    et = ET.parse(fp)
    
    mapping = (
        # XML name, model field name, optional type conversion function
        ('countryName', 'name'),
        ('countryCode', 'iso_code'),
        ('isoNumeric', 'iso_numeric'),
        ('isoAlpha3', 'iso_alpha3'),
        ('fipsCode', 'fips_code'),
        ('continent', 'continent'),
        ('capital', 'capital'),
        ('areaInSqKm', 'area_in_sq_km', float),
        ('population', 'population', int),
        ('currencyCode', 'currency_code'),
        ('languages', 'languages'),
        ('geonameId', 'geoname_id', int),
        ('bBoxWest', 'bbox_west', float),
        ('bBoxNorth', 'bbox_north', float),
        ('bBoxEast', 'bbox_east', float),
        ('bBoxSouth', 'bbox_south', float),
    )
    mapping = [(tup + (unicode,))[:3] for tup in mapping]
    
    for country in et.findall('country'):
        creation_args = {}
        for xml, db_field, conv in mapping:
            if country.find(xml) is None or country.find(xml).text is None:
                continue
            creation_args[db_field] = conv(country.find(xml).text)
        
        Country.objects.get_or_create(iso_code = creation_args['iso_code'], 
            defaults = creation_args)

def import_us_states():
    """
    This file:
    http://www.census.gov/geo/cob/bdy/st/st00ascii/st99_d00_ascii.zip
    From here: http://www.census.gov/geo/www/cob/ascii_info.html
    
    Contains two files with shapes of the states in easy parse format - just 
    need to parse and find max and min lat and lon to get bounding boxes.
    """
    import os
    from django.contrib.localflavor.us.us_states import STATE_CHOICES
    REVERSE_STATE_CHOICES = dict([(p[1], p[0]) for p in STATE_CHOICES])
    
    # First collect all the segments
    s = open('djangopeople/data/st99_d00.dat').read()
    segments = [seg.strip() for seg in s.split('END') if seg.strip()]
    segment_lookup = {}
    for segment in segments:
        points = segment.split()
        id = points.pop(0)
        points = map(float, points)
        lats = points[::2] # Odd numbered indices
        lons = points[1::2] # Even numbered indices
        segment_lookup[id] = (lats, lons)
    
    # Now find out which segments belong to which US State
    s = open('djangopeople/data/st99_d00a.dat').read()
    chunks = [chunk.strip() for chunk in s.split('\n \n') if chunk.strip()]
    # Each chunk descripbes the corresponding segment
    assert len(chunks) == len(segments)
    
    # We're only going to add states which occur in both STATE_CHOICES and the
    # chunk/segment data
    
    statename_chunks = {}
    for chunk in chunks:
        bits = chunk.split('\n')
        chunk_id = bits[0]
        statename = bits[2].replace('"', '').strip()
        if not statename:
            continue # There's a blank one in there for some reason
        statename_chunks.setdefault(statename, []).append(chunk_id)
    
    usa = Country.objects.get(iso_code = 'US')
    
    for statename in statename_chunks.keys():
        if statename not in REVERSE_STATE_CHOICES:
            continue
        
        statecode = REVERSE_STATE_CHOICES[statename]
        if Region.objects.filter(
            country__iso_code = 'US', code = statecode
        ).count() > 0:
            continue # This state already exists
        
        # Find all the latitude / longitude values for the state
        segment_ids = statename_chunks[statename]
        lats = []
        lons = []
        for segment_id in segment_ids:
            lats.extend(segment_lookup[segment_id][0])
            lons.extend(segment_lookup[segment_id][1])
        
        bbox_south = min(lons)
        bbox_north = max(lons)
        bbox_west = min(lats)
        bbox_east = max(lats)
        
        flag = ''
        if os.path.exists(os.path.join(
            settings.OUR_ROOT, 'static/img/flags/us-states',
            '%s.png' % statecode.lower()
        )):
            flag = 'img/flags/us-states/%s.png' % statecode.lower()
        
        # And save the state
        Region.objects.create(
            country = usa,
            code = statecode,
            name = statename,
            bbox_south = bbox_south,
            bbox_north = bbox_north,
            bbox_west = bbox_west,
            bbox_east = bbox_east,
            flag = flag
        )
########NEW FILE########
__FILENAME__ = recluster

from django.core.management.base import NoArgsCommand
from djangopeople import clustering

class Command(NoArgsCommand):
    
    help = "Re-runs the server-side clustering"

    def handle_noargs(self, **options):
        clustering.run()
########NEW FILE########
__FILENAME__ = middleware
from django.http import HttpResponseRedirect, get_host, HttpResponsePermanentRedirect
import re

multislash_re = re.compile('/{2,}')

class NoDoubleSlashes:
    """
    123-reg redirects djangopeople.com/blah to djangopeople.net//blah - this
    middleware eliminates multiple slashes from incoming requests.
    """
    def process_request(self, request):
        if '//' in request.path:
            new_path = multislash_re.sub('/', request.path)
            return HttpResponseRedirect(new_path)
        else:
            return None

class RemoveWWW(object):
    def process_request(self, request):
        host = get_host(request)
        if host and host.startswith('www.'):
            newurl = "%s://%s%s" % (request.is_secure() and 'https' or 'http', host[len('www.'):], request.path)
            if request.GET:
                newurl += '?' + request.GET.urlencode()
            return HttpResponsePermanentRedirect(newurl)
        else:
            return None


########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from machinetags.models import MachineTaggedItem, add_machinetag
from django.contrib.contenttypes import generic
from geopy import distance
from django.utils.safestring import mark_safe
from django.utils.html import escape
import tagging

RESERVED_USERNAMES = set((
    # Trailing spaces are essential in these strings, or split() will be buggy
    'feed www help security porn manage smtp fuck pop manager api owner shit '
    'secure ftp discussion blog features test mail email administrator '
    'xmlrpc web xxx pop3 abuse atom complaints news information imap cunt rss '
    'info pr0n about forum admin weblog team feeds root about info news blog '
    'forum features discussion email abuse complaints map skills tags ajax '
    'comet poll polling thereyet filter search zoom machinetags search django '
    'people profiles profile person navigate nav browse manage static css img '
    'javascript js code flags flag country countries region place places '
    'photos owner maps upload geocode geocoding login logout openid openids '
    'recover lost signup reports report flickr upcoming mashups recent irc '
    'group groups bulletin bulletins messages message newsfeed events company '
    'companies active'
).split())

class CountryManager(models.Manager):
    def top_countries(self):
        return self.get_query_set().order_by('-num_people')

class Country(models.Model):
    # Longest len('South Georgia and the South Sandwich Islands') = 44
    name = models.CharField(max_length=50)
    iso_code = models.CharField(max_length=2, unique=True)
    iso_numeric = models.CharField(max_length=3, unique=True)
    iso_alpha3 = models.CharField(max_length=3, unique=True)
    fips_code = models.CharField(max_length=2, unique=True)
    continent = models.CharField(max_length=2)
    # Longest len('Grand Turk (Cockburn Town)') = 26
    capital = models.CharField(max_length=30, blank=True)
    area_in_sq_km = models.FloatField()
    population = models.IntegerField()
    currency_code = models.CharField(max_length=3)
    # len('en-IN,hi,bn,te,mr,ta,ur,gu,ml,kn,or,pa,as,ks,sd,sa,ur-IN') = 56
    languages = models.CharField(max_length=60)
    geoname_id = models.IntegerField()

    # Bounding boxes
    bbox_west = models.FloatField()
    bbox_north = models.FloatField()
    bbox_east = models.FloatField()
    bbox_south = models.FloatField()
    
    # De-normalised
    num_people = models.IntegerField(default=0)
    
    objects = CountryManager()
    
    def top_regions(self):
        # Returns populated regions in order of population
        return self.region_set.order_by('-num_people')
    
    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'Countries'
    
    def __unicode__(self):
        return self.name
    
class Region(models.Model):
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=50)
    country = models.ForeignKey(Country)
    flag = models.CharField(max_length=100, blank=True)
    bbox_west = models.FloatField()
    bbox_north = models.FloatField()
    bbox_east = models.FloatField()
    bbox_south = models.FloatField()
    
    # De-normalised
    num_people = models.IntegerField(default=0)
    
    def get_absolute_url(self):
        return '/%s/%s/' % (self.country.iso_code.lower(), self.code.lower())
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        ordering = ('name',)
    
class DjangoPerson(models.Model):
    user = models.ForeignKey(User, unique=True)
    bio = models.TextField(blank=True)
    
    # Location stuff - all location fields are required
    country = models.ForeignKey(Country)
    region = models.ForeignKey(Region, blank=True, null=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    location_description = models.CharField(max_length=50)
    
    # Profile photo
    photo = models.ImageField(blank=True, upload_to='profiles')
    
    # Stats
    profile_views = models.IntegerField(default=0)
    
    # Machine tags
    machinetags = generic.GenericRelation(MachineTaggedItem)
    add_machinetag = add_machinetag
    
    # OpenID delegation
    openid_server = models.URLField(max_length=255, blank=True)
    openid_delegate = models.URLField(max_length=255, blank=True)

    # Last active on IRC
    last_active_on_irc = models.DateTimeField(blank=True, null=True)

    def irc_nick(self):
        try:
            return self.machinetags.filter(namespace = 'im', predicate='django')[0].value
        except IndexError:
            return '<none>'
     
    def get_nearest(self, num=5):
        "Returns the nearest X people, but only within the same continent"
        # TODO: Add caching
        
        people = list(self.country.djangoperson_set.select_related().exclude(pk=self.id))
        if len(people) <= num:
            # Not enough in country; use people from the same continent instead
            people = list(DjangoPerson.objects.filter(
                country__continent = self.country.continent,
            ).exclude(pk=self.id).select_related())

        # Sort and annotate people by distance
        for person in people:
            person.distance_in_miles = distance.VincentyDistance(
                (self.latitude, self.longitude),
                (person.latitude, person.longitude)
            ).miles
        
        # Return the nearest X
        people.sort(key=lambda x: x.distance_in_miles)
        return people[:num]
    
    def location_description_html(self):
        region = ''
        if self.region:
            region = '<a href="%s">%s</a>' % (
                self.region.get_absolute_url(), self.region.name
            )
            bits = self.location_description.split(', ')        
            if len(bits) > 1 and bits[-1] == self.region.name:
                bits[-1] = region
            else:
                bits.append(region)
                bits[:-1] = map(escape, bits[:-1])
            return mark_safe(', '.join(bits))
        else:
            return self.location_description
    
    def __unicode__(self):
        return unicode(self.user.get_full_name())
    
    def get_absolute_url(self):
        return '/%s/' % self.user.username
    
    def save(self, force_insert=False, force_update=False): # TODO: Put in transaction
        # Update country and region counters
        super(DjangoPerson, self).save(force_insert=False, force_update=False)
        self.country.num_people = self.country.djangoperson_set.count()
        self.country.save()
        if self.region:
            self.region.num_people = self.region.djangoperson_set.count()
            self.region.save()
    
    class Meta:
        verbose_name_plural = 'Django people'

    def irc_tracking_allowed(self):
        return not self.machinetags.filter(
            namespace = 'privacy', predicate='irctrack', value='private'
        ).count()

tagging.register(DjangoPerson,
    tag_descriptor_attr = 'skilltags',
    tagged_item_manager_attr = 'skilltagged'
)

class PortfolioSite(models.Model):
    title = models.CharField(max_length=100)
    url = models.URLField(max_length=255)
    contributor = models.ForeignKey(DjangoPerson)
    
    def __unicode__(self):
        return '%s <%s>' % (self.title, self.url)
    
class CountrySite(models.Model):
    "Community sites for various countries"
    title = models.CharField(max_length = 100)
    url = models.URLField(max_length = 255)
    country = models.ForeignKey(Country)
    
    def __unicode__(self):
        return '%s <%s>' % (self.title, self.url)
   
#class ClusteredPoint(models.Model):
#    
#    """
#    Represents a clustered point on the map. Each cluster is at a lat/long,
#    is only for one zoom level, and has a number of people.
#    If it is only one person, it is also associated with a DjangoPerson ID.
#    """
#    
#    latitude = models.FloatField()
#    longitude = models.FloatField()
#    zoom = models.IntegerField()
#    number = models.IntegerField()
#    djangoperson = models.ForeignKey(DjangoPerson, blank=True, null=True)
#    
#    def __unicode__(self):
#        return "%s people at (%s,%s,z%s)" % (self.number, self.longitude, self.latitude, self.zoom)
#    
#    class Admin:
#        list_display = ("zoom", "latitude", "longitude", "number")
#        ordering = ("zoom",)

########NEW FILE########
__FILENAME__ = person_list_items
from django import template

register = template.Library()

@register.inclusion_tag('_person_list_items.html')
def person_list_items(people):
    return {'people': people}

########NEW FILE########
__FILENAME__ = utils
import md5, datetime
from django.conf import settings

ORIGIN_DATE = datetime.date(2000, 1, 1)

hex_to_int = lambda s: int(s, 16)
int_to_hex = lambda i: hex(i).replace('0x', '')

def lost_url_for_user(username):
    days = int_to_hex((datetime.date.today() - ORIGIN_DATE).days)
    hash = md5.new(settings.SECRET_KEY + days + username).hexdigest()
    return '/recover/%s/%s/%s/' % (
        username, days, hash
    )

def hash_is_valid(username, days, hash):
    if md5.new(settings.SECRET_KEY + days + username).hexdigest() != hash:
        return False # Hash failed
    # Ensure days is within a week of today
    days_now = (datetime.date.today() - ORIGIN_DATE).days
    days_old = days_now - hex_to_int(days)
    if days_old < 7:
        return True
    else:
        return False

def simple_decorator(decorator):
    """This decorator can be used to turn simple functions
    into well-behaved decorators, so long as the decorators
    are fairly simple. If a decorator expects a function and
    returns a function (no descriptors), and if it doesn't
    modify function attributes or docstring, then it is
    eligible to use this. Simply apply @simple_decorator to
    your decorator and it will automatically preserve the
    docstring and function attributes of functions to which
    it is applied."""
    # From http://wiki.python.org/moin/PythonDecoratorLibrary
    def new_decorator(f):
        g = decorator(f)
        g.__name__ = f.__name__
        g.__doc__ = f.__doc__
        g.__dict__.update(f.__dict__)
        return g
    # Now a few lines needed to make simple_decorator itself
    # be a well-behaved decorator.
    new_decorator.__name__ = decorator.__name__
    new_decorator.__doc__ = decorator.__doc__
    new_decorator.__dict__.update(decorator.__dict__)
    return new_decorator
########NEW FILE########
__FILENAME__ = views
from django.http import Http404, HttpResponse, HttpResponseRedirect, \
    HttpResponseForbidden
from django.contrib import auth
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string
from djangopeople.models import DjangoPerson, Country, User, Region, PortfolioSite
from djangopeople import utils
from django_openidauth.models import associate_openid, UserOpenID
from tagging.models import Tag
#from tagging.views import tagged_object_list
from tagging.utils import calculate_cloud, edit_string_for_tags
from machinetags.utils import tagdict
from machinetags.models import MachineTaggedItem
from djangopeople.forms import SkillsForm
from djangopeople.forms import SignupForm, PhotoUploadForm, PortfolioForm, \
    BioForm, LocationForm, FindingForm, AccountForm
from djangopeople.constants import MACHINETAGS_FROM_FIELDS, IMPROVIDERS_DICT, SERVICES_DICT
from django.conf import settings
import os, md5, datetime
from PIL import Image
from cStringIO import StringIO

def render(request, template, context_dict=None):
    return render_to_response(
        template, context_dict or {}, context_instance=RequestContext(request)
    )

@utils.simple_decorator
def must_be_owner(view):
    def inner(request, *args, **kwargs):
        if not request.user or request.user.is_anonymous() \
            or request.user.username != args[0]:
            return HttpResponseForbidden('Not allowed')
        return view(request, *args, **kwargs)
    return inner

def index(request):
    recent_people_limited = DjangoPerson.objects.all().select_related().order_by('-id')[:4]
    return render(request, 'index.html', {
        'recent_people_limited': recent_people_limited,
        'total_people': DjangoPerson.objects.count(),
        'api_key': settings.GOOGLE_MAPS_API_KEY,
        'countries': Country.objects.top_countries(),
    })

def about(request):
    return render(request, 'about.html', {
        'total_people': DjangoPerson.objects.count(),
        'openid_users': User.objects.filter(useropenid__openid__startswith = 'http').distinct().count(),
        'countries': Country.objects.top_countries(),
    })

def recent(request):
    return render(request, 'recent.html', {
        'people': DjangoPerson.objects.all().select_related().order_by('-auth_user.date_joined')[:50],
        'api_key': settings.GOOGLE_MAPS_API_KEY,
    })

def login(request):
    if request.method != 'POST':
        return render(request, 'login.html', {
            'next': request.REQUEST.get('next', ''),
        })
    username = request.POST.get('username')
    password = request.POST.get('password')
    user = auth.authenticate(username=username, password=password)
    if user is not None and user.is_active:
        auth.login(request, user)
        return HttpResponseRedirect(
            request.POST.get('next', '/%s/' % user.username)
        )
    else:
        return render(request, 'login.html', {
            'is_invalid': True,
            'username': username, # Populate form
            'next': request.REQUEST.get('next', ''),
        })

def logout(request):
    auth.logout(request)
    request.session['openids'] = []
    return HttpResponseRedirect('/')

def lost_password(request):
    username = request.POST.get('username', '')
    if username:
        try:
            person = DjangoPerson.objects.get(user__username = username)
        except DjangoPerson.DoesNotExist:
            return render(request, 'lost_password.html', {
                'message': 'That was not a valid username.'
            })
        path = utils.lost_url_for_user(username)
        from django.core.mail import send_mail
        import smtplib
        body = render_to_string('recovery_email.txt', {
            'path': path,
            'person': person,
        })
        try:
            send_mail(
                'Django People account recovery', body,
                settings.RECOVERY_EMAIL_FROM, [person.user.email],
                fail_silently=False
            )
        except smtplib.SMTPException:
            return render(request, 'lost_password.html', {
                'message': 'Could not e-mail you a recovery link.',
            })
        return render(request, 'lost_password.html', {
            'message': ('An e-mail has been sent with instructions for '
                "recovering your account. Don't forget to check your spam "
                'folder!')
        })
    return render(request, 'lost_password.html')

def lost_password_recover(request, username, days, hash):
    user = get_object_or_404(User, username=username)
    if utils.hash_is_valid(username, days, hash):
        user.backend='django.contrib.auth.backends.ModelBackend' 
        auth.login(request, user)
        return HttpResponseRedirect('/%s/password/' % username)
    else:
        return render(request, 'lost_password.html', {
            'message': 'That was not a valid account recovery link'
        })

def openid_whatnext(request):
    """
    If user is already logged in, send them to /openid/associations/
    Otherwise, send them to the signup page
    """
    if not request.openid:
        return HttpResponseRedirect('/')
    if request.user.is_anonymous():
        # Have they logged in with an OpenID that matches an account?
        try:
            user_openid = UserOpenID.objects.get(openid = str(request.openid))
        except UserOpenID.DoesNotExist:
            return HttpResponseRedirect('/signup/')
        # Log the user in
        user = user_openid.user
        user.backend='django.contrib.auth.backends.ModelBackend' 
        auth.login(request, user)
        return HttpResponseRedirect('/%s/' % user.username)
    
    else:
        return HttpResponseRedirect('/openid/associations/')

def signup(request):
    if not request.user.is_anonymous():
        return HttpResponseRedirect('/')
    if request.method == 'POST':
        if request.openid:
            form = SignupForm(
                request.POST, request.FILES, openid=request.openid
            )
        else:
            form = SignupForm(request.POST, request.FILES)
        if form.is_valid():
            # First create the user
            creation_args = {
                'username': form.cleaned_data['username'],
                'email': form.cleaned_data['email'],
            }
            if form.cleaned_data.get('password1'):
                creation_args['password'] = form.cleaned_data['password1']
                
            user = User.objects.create_user(**creation_args)
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()
            
            if request.openid:
                associate_openid(user, str(request.openid))
            
            region = None
            if form.cleaned_data['region']:
                region = Region.objects.get(
                    country__iso_code = form.cleaned_data['country'],
                    code = form.cleaned_data['region']
                )
            
            # Now create the DjangoPerson
            person = DjangoPerson.objects.create(
                user = user,
                bio = form.cleaned_data['bio'],
                country = Country.objects.get(
                    iso_code = form.cleaned_data['country']
                ),
                region = region,
                latitude = form.cleaned_data['latitude'],
                longitude = form.cleaned_data['longitude'],
                location_description = form.cleaned_data['location_description']
            )
            
            # Set up the various machine tags
            for fieldname, (namespace, predicate) in \
                    MACHINETAGS_FROM_FIELDS.items():
                if form.cleaned_data.has_key(fieldname) and \
                    form.cleaned_data[fieldname].strip():
                    value = form.cleaned_data[fieldname].strip()
                    person.add_machinetag(namespace, predicate, value)
            
            # Stash their blog and looking_for_work
            if form.cleaned_data['blog']:
                person.add_machinetag(
                    'profile', 'blog', form.cleaned_data['blog']
                )
            if form.cleaned_data['looking_for_work']:
                person.add_machinetag(
                    'profile', 'looking_for_work',
                    form.cleaned_data['looking_for_work']
                )
            
            # Finally, set their skill tags
            person.skilltags = form.cleaned_data['skilltags']
            
            # Log them in and redirect to their profile page
            # HACK! http://groups.google.com/group/django-users/
            #    browse_thread/thread/39488db1864c595f
            user.backend='django.contrib.auth.backends.ModelBackend' 
            auth.login(request, user)
            return HttpResponseRedirect(person.get_absolute_url())
    else:
        if request.openid and request.openid.sreg:
            sreg = request.openid.sreg
            first_name = ''
            last_name = ''
            username = ''
            if sreg.get('fullname'):
                bits = sreg['fullname'].split()
                first_name = bits[0]
                if len(bits) > 1:
                    last_name = ' '.join(bits[1:])
            # Find a not-taken username
            if sreg.get('nickname'):
                username = derive_username(sreg['nickname'])
            form = SignupForm(initial = {
                'first_name': first_name,
                'last_name': last_name,
                'email': sreg.get('email', ''),
                'username': username,
            }, openid = request.openid)
        elif request.openid:
            form = SignupForm(openid = request.openid)
        else:
            form = SignupForm()
    
    return render(request, 'signup.html', {
        'form': form,
        'api_key': settings.GOOGLE_MAPS_API_KEY,
        'openid': request.openid,
    })

import re
notalpha_re = re.compile('[^a-zA-Z0-9]')
def derive_username(nickname):
    nickname = notalpha_re.sub('', nickname)
    if not nickname:
        return ''
    base_nickname = nickname
    to_add = 1
    while True:
        try:
            DjangoPerson.objects.get(user__username = nickname)
        except DjangoPerson.DoesNotExist:
            break
        nickname = base_nickname + str(to_add)
        to_add += 1
    return nickname

@must_be_owner
def upload_profile_photo(request, username):
    person = get_object_or_404(DjangoPerson, user__username = username)
    if request.method == 'POST':
        form = PhotoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Figure out what type of image it is
            image_content = request.FILES['photo'].read()
            format = Image.open(StringIO(image_content)).format
            format = format.lower().replace('jpeg', 'jpg')
            filename = md5.new(image_content).hexdigest() + '.' + format
            # Save the image
            path = os.path.join(settings.MEDIA_ROOT, 'profiles', filename)
            open(path, 'w').write(image_content)
            person.photo = 'profiles/%s' % filename
            person.save()
            return HttpResponseRedirect('/%s/upload/done/' % username)
    else:
        form = PhotoUploadForm()
    return render(request, 'upload_profile_photo.html', {
        'form': form,
        'person': person,
    })

@must_be_owner
def upload_done(request, username):
    "Using a double redirect to try and stop back button from re-uploading"
    return HttpResponseRedirect('/%s/' % username)

def country(request, country_code):
    country = get_object_or_404(Country, iso_code = country_code.upper())
    return render(request, 'country.html', {
        'country': country,
        'api_key': settings.GOOGLE_MAPS_API_KEY,
        'regions': country.top_regions(),
    })

def country_sites(request, country_code):
    country = get_object_or_404(Country, iso_code = country_code.upper())
    sites = PortfolioSite.objects.select_related().filter(
        contributor__country = country
    ).order_by('contributor')
    return render(request, 'country_sites.html', {
        'country': country,
        'sites': sites,
    })

def region(request, country_code, region_code):
    region = get_object_or_404(Region, 
        country__iso_code = country_code.upper(),
        code = region_code.upper()
    )
    return render(request, 'country.html', {
        'country': region,
        'api_key': settings.GOOGLE_MAPS_API_KEY,
    })

def profile(request, username):
    person = get_object_or_404(DjangoPerson, user__username = username)
    person.profile_views += 1 # Not bothering with transactions; only a stat
    person.save()
    mtags = tagdict(person.machinetags.all())
    
    # Set up convenient iterables for IM and services
    ims = []
    for key, value in mtags.get('im', {}).items():
        shortname, name, icon = IMPROVIDERS_DICT.get(key, ('', '', ''))
        if not shortname:
            continue # Bad machinetag
        ims.append({
            'shortname': shortname,
            'name': name,
            'value': value,
        })
    ims.sort(lambda x, y: cmp(x['shortname'], y['shortname']))
    
    services = []
    for key, value in mtags.get('services', {}).items():
        shortname, name, icon = SERVICES_DICT.get(key, ('', '', ''))
        if not shortname:
            continue # Bad machinetag
        services.append({
            'shortname': shortname,
            'name': name,
            'value': value,
        })
    services.sort(lambda x, y: cmp(x['shortname'], y['shortname']))
    
    # Set up vars that control privacy stuff
    privacy = {
        'show_im': (
            mtags['privacy']['im'] == 'public' or 
            not request.user.is_anonymous()
        ),
        'show_email': (
            mtags['privacy']['email'] == 'public' or 
            (not request.user.is_anonymous() and mtags['privacy']['email'] == 'private')
        ),
        'hide_from_search': mtags['privacy']['search'] != 'public',
        'show_last_irc_activity': bool(person.last_active_on_irc and person.irc_tracking_allowed()),
    }
    
    # Should we show the 'Finding X' section at all?
    show_finding = services or privacy['show_email'] or \
        (privacy['show_im'] and ims)
    
    return render(request, 'profile.html', {
        'person': person,
        'api_key': settings.GOOGLE_MAPS_API_KEY,
        'is_owner': request.user.username == username,
        'skills_form': SkillsForm(initial={
            'skills': edit_string_for_tags(person.skilltags)
        }),
        'mtags': mtags,
        'ims': ims,
        'services': services,
        'privacy': privacy,
        'show_finding': show_finding,
    })

@must_be_owner
def edit_finding(request, username):
    person = get_object_or_404(DjangoPerson, user__username = username)
    if request.method == 'POST':
        form = FindingForm(request.POST, person=person)
        if form.is_valid():
            user = person.user
            user.email = form.cleaned_data['email']
            user.save()
            
            person.machinetags.filter(namespace = 'profile').delete()
            if form.cleaned_data['blog']:
                person.add_machinetag(
                    'profile', 'blog', form.cleaned_data['blog']
                )
            if form.cleaned_data['looking_for_work']:
                person.add_machinetag(
                    'profile', 'looking_for_work',
                    form.cleaned_data['looking_for_work']
                )
            
            for fieldname, (namespace, predicate) in \
                MACHINETAGS_FROM_FIELDS.items():
                person.machinetags.filter(
                    namespace = namespace, predicate = predicate
                ).delete()
                if form.cleaned_data.has_key(fieldname) and \
                    form.cleaned_data[fieldname].strip():
                    value = form.cleaned_data[fieldname].strip()
                    person.add_machinetag(namespace, predicate, value)
            
            return HttpResponseRedirect('/%s/' % username)
    else:
        mtags = tagdict(person.machinetags.all())
        initial = {
            'email': person.user.email,
            'blog': mtags['profile']['blog'],
            'looking_for_work': mtags['profile']['looking_for_work'],
        }
        
        # Fill in other initial fields from machinetags
        for fieldname, (namespace, predicate) in \
                MACHINETAGS_FROM_FIELDS.items():
            initial[fieldname] = mtags[namespace][predicate]
        
        form = FindingForm(initial=initial, person=person)
    return render(request, 'edit_finding.html', {
        'form': form,
        'person': person,
    })

@must_be_owner
def edit_portfolio(request, username):
    person = get_object_or_404(DjangoPerson, user__username = username)
    if request.method == 'POST':
        form = PortfolioForm(request.POST, person = person)
        if form.is_valid():
            person.portfoliosite_set.all().delete()
            for key in [k for k in request.POST if k.startswith('title_')]:
                title = request.POST[key]
                url = request.POST[key.replace('title_', 'url_')]
                if title.strip() and url.strip():
                    person.portfoliosite_set.create(title = title, url = url)
            return HttpResponseRedirect('/%s/' % username)
    else:
        form = PortfolioForm(person = person)
    return render(request, 'edit_portfolio.html', {
        'form': form,
    })

@must_be_owner
def edit_account(request, username):
    person = get_object_or_404(DjangoPerson, user__username = username)
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            person.openid_server = form.cleaned_data['openid_server']
            person.openid_delegate = form.cleaned_data['openid_delegate']
            person.save()
            return HttpResponseRedirect('/%s/' % username)
    else:
        form = AccountForm(initial = {
            'openid_server': person.openid_server,
            'openid_delegate': person.openid_delegate,
        })
    return render(request, 'edit_account.html', {
        'form': form,
        'person': person,
        'user': person.user,
    })

@must_be_owner
def edit_skills(request, username):
    person = get_object_or_404(DjangoPerson, user__username = username)
    if not request.POST.get('skills'):
        return render(request, 'edit_skills.html', {
            'form': SkillsForm(initial={
                'skills': edit_string_for_tags(person.skilltags)
            }),
        })
    person.skilltags = request.POST.get('skills', '')
    return HttpResponseRedirect('/%s/' % username)

@must_be_owner
def edit_password(request, username):
    user = get_object_or_404(User, username = username)
    p1 = request.POST.get('password1', '')
    p2 = request.POST.get('password2', '')
    if p1 and p2 and p1 == p2:
        user.set_password(p1)
        user.save()
        return HttpResponseRedirect('/%s/' % username)
    else:
        return render(request, 'edit_password.html')

@must_be_owner
def edit_bio(request, username):
    person = get_object_or_404(DjangoPerson, user__username = username)
    if request.method == 'POST':
        form = BioForm(request.POST)
        if form.is_valid():
            person.bio = form.cleaned_data['bio']
            person.save()
            return HttpResponseRedirect('/%s/' % username)
    else:
        form = BioForm(initial = {'bio': person.bio})
    return render(request, 'edit_bio.html', {
        'form': form,
    })

@must_be_owner
def edit_location(request, username):
    person = get_object_or_404(DjangoPerson, user__username = username)
    if request.method == 'POST':
        form = LocationForm(request.POST)
        if form.is_valid():
            region = None
            if form.cleaned_data['region']:
                region = Region.objects.get(
                    country__iso_code = form.cleaned_data['country'],
                    code = form.cleaned_data['region']
                )
            person.country = Country.objects.get(
                iso_code = form.cleaned_data['country']
            )
            person.region = region
            person.latitude = form.cleaned_data['latitude']
            person.longitude = form.cleaned_data['longitude']
            person.location_description = \
                form.cleaned_data['location_description']
            person.save()
            return HttpResponseRedirect('/%s/' % username)
    else:
        form = LocationForm()
    return render(request, 'edit_location.html', {
        'form': form,
        'api_key': settings.GOOGLE_MAPS_API_KEY,
    })

def skill_cloud(request):
    tags = DjangoPerson.skilltags.cloud(steps=5)
    calculate_cloud(tags, 5)
    return render(request, 'skills.html', {
        'tags': tags
    })

def country_skill_cloud(request, country_code):
    country = get_object_or_404(Country, iso_code = country_code.upper())
    tags = Tag.objects.cloud_for_model(DjangoPerson, steps=5, filters={
        'country': country
    })
    calculate_cloud(tags, 5)
    return render(request, 'skills.html', {
        'tags': tags,
        'country': country
    })

def skill(request, tag):
    return tagged_object_list(request,
        model = DjangoPerson,
        tag = tag,
        related_tags = True,
        related_tag_counts = True,
        template_name = 'skill.html',
        extra_context = {
            'api_key': settings.GOOGLE_MAPS_API_KEY,
        },
    )

def country_skill(request, country_code, tag):
    return tagged_object_list(request,
        model = DjangoPerson,
        tag = tag,
        related_tags = True,
        related_tag_counts = True,
        extra_filter_args = {'country__iso_code': country_code.upper()},
        template_name = 'skill.html',
        extra_context = {
            'api_key': settings.GOOGLE_MAPS_API_KEY,
            'country': Country.objects.get(iso_code = country_code.upper()),
        },
    )

def country_looking_for(request, country_code, looking_for):
    country = get_object_or_404(Country, iso_code = country_code.upper())
    ids = [
        o['object_id'] for o in MachineTaggedItem.objects.filter(
        namespace='profile', predicate='looking_for_work', value=looking_for).values('object_id')
    ]
    people = DjangoPerson.objects.filter(country = country, id__in = ids)
    return render(request, 'country_looking_for.html', {
        'people': people,
        'country': country,
        'looking_for': looking_for,
    })

from django.db.models import Q
import operator

def search_people(q):
    words = [w.strip() for w in q.split() if len(w.strip()) > 2]
    if not words:
        return []
    
    terms = []
    for word in words:
        terms.append(Q(
            user__username__icontains = word) | 
            Q(user__first_name__icontains = word) | 
            Q(user__last_name__icontains = word)
        )
    
    combined = reduce(operator.and_, terms)
    return DjangoPerson.objects.filter(combined).select_related().distinct()
    
def search(request):
    q = request.GET.get('q', '')
    has_badwords = [
        w.strip() for w in q.split() if len(w.strip()) in (1, 2)
    ]
    if q:
        people = search_people(q)
        return render(request, 'search.html', {
            'q': q,
            'results': people,
            'api_key': settings.GOOGLE_MAPS_API_KEY,
            'has_badwords': has_badwords,
        })
    else:
        return render(request, 'search.html')

def irc_active(request):
    "People active on IRC in the last hour"
    results = DjangoPerson.objects.filter(
        last_active_on_irc__gt = 
            datetime.datetime.now() - datetime.timedelta(hours=1)
    ).order_by('-last_active_on_irc')
    # Filter out the people who don't want to be tracked (inefficient)
    results = [r for r in results if r.irc_tracking_allowed()]
    return render(request, 'irc_active.html', {
        'results': results,
        'api_key': settings.GOOGLE_MAPS_API_KEY,
    })

# Custom variant of the generic view from django-tagging
from django.http import Http404
from django.utils.translation import ugettext as _
from django.views.generic.list_detail import object_list
from tagging.models import Tag, TaggedItem
from tagging.utils import get_tag
def tagged_object_list(request, model=None, tag=None, related_tags=False,
        related_tag_counts=True, extra_filter_args=None, **kwargs):
    """
    A thin wrapper around
    ``django.views.generic.list_detail.object_list`` which creates a
    ``QuerySet`` containing instances of the given model tagged with
    the given tag.

    In addition to the context variables set up by ``object_list``, a
    ``tag`` context variable will contain the ``Tag`` instance for the
    tag.

    If ``related_tags`` is ``True``, a ``related_tags`` context variable
    will contain tags related to the given tag for the given model.
    Additionally, if ``related_tag_counts`` is ``True``, each related
    tag will have a ``count`` attribute indicating the number of items
    which have it in addition to the given tag.
    """
    if model is None:
        try:
            model = kwargs['model']
        except KeyError:
            raise AttributeError(_('tagged_object_list must be called with a model.'))

    if tag is None:
        try:
            tag = kwargs['tag']
        except KeyError:
            raise AttributeError(_('tagged_object_list must be called with a tag.'))

    tag_instance = get_tag(tag)
    if tag_instance is None:
        raise Http404(_('No Tag found matching "%s".') % tag)
    queryset = TaggedItem.objects.get_by_model(model, tag_instance)
    if extra_filter_args:
        queryset = queryset.filter(**extra_filter_args)
    if not kwargs.has_key('extra_context'):
        kwargs['extra_context'] = {}
    kwargs['extra_context']['tag'] = tag_instance
    if related_tags:
        kwargs['extra_context']['related_tags'] = \
            Tag.objects.related_for_model(tag_instance, model,
                                          counts=related_tag_counts)
    return object_list(request, queryset, **kwargs)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

import sys, os
root = os.path.dirname(__file__)
paths = (
    os.path.join(root, '../lib'),
    os.path.join(root, '..'),
)
for path in paths:
    if not path in sys.path:
        sys.path.insert(0, path)

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
__FILENAME__ = settings
# Django settings for djangopeoplenet project.
import os
OUR_ROOT = os.path.realpath(os.path.dirname(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# Thumbnail settings
THUMBNAIL_DEBUG = True
THUMBNAIL_SUBDIR = '_thumbs'

# OpenID settings
OPENID_REDIRECT_NEXT = '/openid/whatnext/'
LOGIN_URL = '/login/'

# Tagging settings
FORCE_LOWERCASE_TAGS = True

AUTH_PROFILE_MODULE = 'djangopeople.DjangoPerson'
RECOVERY_EMAIL_FROM = 'simon@simonwillison.net'

ADMINS = (
    ('Simon Willison', 'simon@simonwillison.net'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'people.db'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

GOOGLE_MAPS_API_KEY = 'GOOGLE-MAPS-API-KEY-GOES-HERE'

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be avilable on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(OUR_ROOT, 'static')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'SECRET-KEY-GOES-HERE'

# Password used by the IRC bot for the API
API_PASSWORD = 'API-PASSWORD-GOES-HERE'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'djangopeople.middleware.RemoveWWW',
    'django.contrib.csrf.middleware.CsrfMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_openidconsumer.middleware.OpenIDMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'djangopeople.middleware.NoDoubleSlashes',
)

ROOT_URLCONF = 'djangopeoplenet.urls'

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
    'django.contrib.admin',
    'django.contrib.humanize',
    'django_openidconsumer',
    'django_openidauth',
    'djangopeople',
    'machinetags',
    'sorl.thumbnail',
)

try:
    from djangopeople_local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings
from django.http import HttpResponseRedirect
from djangopeople import views, api #, clustering
from djangopeople.models import DjangoPerson
from tagging.views import tagged_object_list
import os

def redirect(url):
    return lambda res: HttpResponseRedirect(url)

admin.autodiscover()

urlpatterns = patterns('',
    (r'^$', views.index),
    (r'^login/$', views.login),
    (r'^logout/$', views.logout),
    (r'^about/$', views.about),
    (r'^recent/$', views.recent),
    (r'^recover/$', views.lost_password),
    (r'^recover/([a-z0-9]{3,})/([a-f0-9]+)/([a-f0-9]{32})/$',
        views.lost_password_recover),
    (r'^signup/$', views.signup),

    (r'^openid/$', 'django_openidconsumer.views.begin', {
        'sreg': 'email,nickname,fullname',
        'redirect_to': '/openid/complete/',    
    }),
    (r'^openid/complete/$', 'django_openidconsumer.views.complete'),
    (r'^openid/whatnext/$', views.openid_whatnext),
    (r'^openid/signout/$', 'django_openidconsumer.views.signout'),
    (r'^openid/associations/$', 'django_openidauth.views.associations'),

    (r'^search/$', views.search),
#    (r'^openid/$', views.openid),
    
    (r'^skills/(?P<tag>.*)/$', views.skill),
    (r'^skills/$', views.skill_cloud),
    
    (r'^static/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': os.path.join(settings.OUR_ROOT, 'static')
    }),
    (r'^admin/(.*)', admin.site.root),
    (r'^api/irc_lookup/(.*?)/$', api.irc_lookup),
    (r'^api/irc_spotted/(.*?)/$', api.irc_spotted),
    (r'^irc/active/$', views.irc_active),
    (r'^irc/(.*?)/$', api.irc_redirect),
    
    (r'^uk/$', redirect('/gb/')),
    (r'^([a-z]{2})/$', views.country),
    (r'^([a-z]{2})/sites/$', views.country_sites),
    (r'^([a-z]{2})/skills/$', views.country_skill_cloud),
    (r'^([a-z]{2})/skills/(.*)/$', views.country_skill),
    (r'^([a-z]{2})/looking-for/(freelance|full-time)/$', views.country_looking_for),
    (r'^([a-z]{2})/(\w+)/$', views.region),
    
    (r'^([a-z0-9]{3,})/$', views.profile),
    (r'^([a-z0-9]{3,})/bio/$', views.edit_bio),
    (r'^([a-z0-9]{3,})/skills/$', views.edit_skills),
    (r'^([a-z0-9]{3,})/password/$', views.edit_password),
    (r'^([a-z0-9]{3,})/account/$', views.edit_account),
    (r'^([a-z0-9]{3,})/portfolio/$', views.edit_portfolio),
    (r'^([a-z0-9]{3,})/location/$', views.edit_location),
    (r'^([a-z0-9]{3,})/finding/$', views.edit_finding),
    (r'^([a-z0-9]{3,})/upload/$', views.upload_profile_photo),
    (r'^([a-z0-9]{3,})/upload/done/$', views.upload_done),
    
#    (r'^clusters/(\-?\d+\.?\d*)/(\-?\d+\.?\d*)/(\-?\d+\.?\d*)/(\-?\d+\.?\d*)/(\d+)/$', clustering.as_json),
)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django_openidauth.models import UserOpenID


class UserOpenIDAdmin(admin.ModelAdmin):
    pass
    
admin.site.register(UserOpenID, UserOpenIDAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User

import datetime

class UserOpenID(models.Model):
    user = models.ForeignKey(User)
    openid = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField()
    def __unicode__(self):
        return "<User %s has OpenID %s>" % (self.user, self.openid)
    class Meta:
        ordering = ('-created_at',)

def associate_openid(user, openid):
    "Associate an OpenID with a user account"
    # Remove any matching records first, just in case some slipped through
    unassociate_openid(user, openid)
    
    # check that openid isn't already associated with another user
    if UserOpenID.objects.filter(openid = openid).count():
        return False
    
    # Now create the new record
    new = UserOpenID(
        user = user,
        openid = openid,
        created_at = datetime.datetime.now()
    )
    new.save()
    
    return True
    
def unassociate_openid(user, openid):
    "Remove an association between an OpenID and a user account"
    matches = UserOpenID.objects.filter(
        user__id = user.id,
        openid = openid
    )
    [m.delete() for m in matches]

########NEW FILE########
__FILENAME__ = regviews
from django import forms
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.template import RequestContext

try:
    # dependency: http://code.google.com/p/django-registration
    from registration.forms import RegistrationForm
    from registration.models import RegistrationProfile
except ImportError, e:
    raise ImportError, (
        "Could not import a required dependency: please ensure that " +
        "django-registration is installed and available on the Python Path " +
        "as 'registration'. Try 'import registration' at a Python prompt to " +
        "confirm installation. django-registration is available from " +
        "http://code.google.com/p/django-registration\n\n%s" % str(e)
    )

class RegistrationFormOpenID(RegistrationForm):
    """
    This form requires access to the Django request object in order to properly
    validate itself, as the password field is only required if an OpenID is not
    currently available as part of the request. The request object can be 
    passed to the constructor as a named keyword argument called 'request'
    """
    def __init__(self, *args, **kwargs):
        self.request = kwargs.get('request', None)
        if 'request' in kwargs:
            del kwargs['request']
        super(RegistrationFormOpenID, self).__init__(*args, **kwargs)
        self.base_fields['password1'].required = False
        self.base_fields['password2'].required = False
    
    def clean_password1(self):
        "Password is only required if user is not registering with an OpenID"
        if not self.request or not getattr(self.request, 'openids', []):
            # No OpenID, so password field is required
            if 'password1' not in self.cleaned_data \
                or not self.cleaned_data.get('password1', '').strip():
                raise forms.ValidationError(u'You must provide a password')
        return self.cleaned_data.get('password1', '')

def register(request, success_url='/accounts/register/complete/', 
        template_name='registration_form.html'):
    """
    Allows a new user to register an account. A customised variation of the 
    view of the same name from django-registration.

    Context::
        form
            The registration form
    
    Template::
        registration/registration_form.html (or template_name argument)
    
    """
    if request.method == 'POST':
        form = RegistrationFormOpenID(request.POST, request=request)
        if form.is_valid():
            new_user = RegistrationProfile.objects.create_inactive_user(username=form.cleaned_data['username'],
                                                                        password=form.cleaned_data['password1'],
                                                                        email=form.cleaned_data['email'])
            return HttpResponseRedirect(success_url)
    else:
        form = RegistrationForm()
    return render_to_response(template_name, { 'form': form },
                              context_instance=RequestContext(request))

def demo_delete_me_asap(request):
    import django.forms
    
    class UserProfileForm(forms.Form):
        name = forms.CharField(max_length=100)
        email = forms.EmailField()
        bio = forms.CharField(widget=forms.Textarea)
        dob = forms.DateField(required=False)
        receive_newsletter = forms.BooleanField(required=False)
        def clean_email(self):
            from django.forms.util import ValidationError
            if self.cleaned_data['email'].split('@')[1] == 'hotmail.com':
                raise ValidationError, "No hotmail.com emails, please."

    if request.method == 'POST':
        form = UserProfileForm(request.POST)
        if form.is_valid():
            # ... save the user's profile
            return HttpResponseRedirect('/profile/saved/')
    else:
        form = UserProfileForm()
    return render_to_response('profile.html', {'form': form})

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response as render
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as log_user_in, load_backend
from django.utils.html import escape
from django.conf import settings

from models import UserOpenID, associate_openid, unassociate_openid
from django_openidconsumer import views as consumer_views

import time, md5, datetime

def _make_hash(hash_type, user, openid):
    return md5.new('%s:%d:%s:%s' % (
        hash_type, user.id, str(openid), settings.SECRET_KEY
    )).hexdigest()

@login_required
def associations(request, template_name='openid_associations.html'):
    """
    A view for managing the OpenIDs associated with a user account.
    """
    if 'openid_url' in request.POST:
        # They entered a new OpenID and need to authenticate it - kick off the
        # process and make sure they are redirected back here afterwards
        return consumer_views.begin(request, redirect_to='/openid/complete/')
    
    messages = []
    associated_openids = [
        rec.openid
        for rec in UserOpenID.objects.filter(user__id = request.user.id)
    ]
    
    # OpenIDs are associated and de-associated based on their key - which is a
    # hash of the OpenID, user ID and SECRET_KEY - this gives us a nice key for
    # submit button names or checkbox values and provides CSRF protection at 
    # the same time. We need to pre-calculate the hashes for the user's OpenIDs
    # in advance.
    add_hashes = dict([
        (_make_hash('add', request.user, openid), str(openid))
        for openid in request.openids
        if str(openid) not in associated_openids
    ])
    del_hashes = dict([
        (_make_hash('del', request.user, openid), openid)
        for openid in associated_openids
    ])
    
    # We can now cycle through the keys in POST, looking for stuff to add or 
    # delete. First though we check for the ?direct=1 argument and directly add
    # any OpenIDs that were authenticated in the last 5 seconds - this supports
    # the case where a user has entered an OpenID in the form on this page, 
    # authenticated it and been directed straight back here.
    # TODO: Reconsider this technique now that it's easier to create custom 
    #       behaviour when an OpenID authentication is successful.
    if request.GET.get('direct') and request.openids and \
            request.openids[-1].issued > int(time.time()) - 5 and \
            str(request.openids[-1]) not in associated_openids:
        new_openid = str(request.openids[-1])
        if associate_openid(request.user, new_openid):
            associated_openids.append(new_openid)
            messages.append('%s has been associated with your account' % escape(
                new_openid
            ))
        else:
            messages.append(('%s could not be associated with your account, ' + 
                'as it is already associated with a different account') % \
                escape(new_openid)
            )
    
    # Now cycle through POST.keys() looking for OpenIDs to add or remove
    for key in request.POST.keys():
        if key in add_hashes:
            openid = add_hashes[key]
            if openid not in associated_openids:
                if associate_openid(request.user, openid):
                    associated_openids.append(openid)
                    messages.append('%s has been associated with your account' % 
                        escape(openid)
                    )
                else:
                    messages.append(('%s could not be associated with your ' +
                        'account, as it is already associated with a ' + 
                        'different account') % escape(openid)
                    )

        if key in del_hashes:
            openid = del_hashes[key]
            if openid in associated_openids:
                # if user has no password and this is last one, don't allow
                if (not request.user.has_usable_password()) \
                    and len(associated_openids) < 2:
                    messages.append(
                        'You need to set a password if you want to remove all' + 
                        ' of your OpenIDs'
                    )
                else:
                    unassociate_openid(request.user, openid)
                    associated_openids.remove(openid)
                    messages.append('%s has been removed from your account' % \
                        escape(openid)
                    )
    
    # At this point associated_openids represents the current set of associated
    # OpenIDs, and messages contains any messages that should be displayed. The
    # final step is to work out which OpenIDs they have that are currently 
    # logged in BUT are not associated - these are the ones that should be 
    # displayed with an "associate this?" buttons.
    potential_openids = [
        str(openid) for openid in request.openids
        if str(openid) not in associated_openids
    ]
    
    # Finally, calculate the button hashes we are going to need for the form.
    add_buttons = [
        {'openid': openid, 'hash': _make_hash('add', request.user, openid)}
        for openid in potential_openids
    ]
    del_buttons = [
        {'openid': openid, 'hash': _make_hash('del', request.user, openid)}
        for openid in associated_openids
    ]
    
    return render(template_name, {
        'user': request.user,
        'messages': messages,
        'action': request.path,
        'add_buttons': add_buttons,
        'del_buttons': del_buttons, # This is also used to generate the list of 
                                    # of associated OpenIDs
    })

def complete(request, on_login_ok=None, on_login_failed=None, 
        on_login_ok_url=None, on_login_failed_url=None,
    ):
    """
    This view function takes optional arguments to configure how a successful
    or unsuccessful login will be dealt with. Default behaviour is to redirect
    to the homepage, appending a query string of loggedin=True or loggedin=False
    
    You can use the on_login_ok_url and on_login_failed_url arguments to 
    indicate different URLs for redirection after an OK or failed login attempt.
    
    Alternatively, you can provide your own view functions for these cases. For 
    example:
    
    def my_login_ok(request, identity_url):
        return HttpResponse(
            "Congratulations, you signed in as %s using OpenID %s" % (
                escape(request.user), escape(identity_url)
            ))
    
    def my_login_failed(request, identity_url):
        return HttpResponse(
            "Login failed; %s is not associated with an account" % (
                escape(identity_url)
            ))
    
    And in the URL configuration:
    
        (r'^openid/complete/$', 'django_openidauth.views.complete', {
            'on_login_ok': my_login_ok,
            'on_login_failed': my_login_failed,
        }),
    
    """
    if not on_login_ok:
        on_login_ok = lambda request, identity_url: HttpResponseRedirect(
            on_login_ok_url or '/?loggedin=True'
        )
    if not on_login_failed:
        on_login_failed = lambda request, identity_url: HttpResponseRedirect(
            on_login_failed_url or '/?loggedin=False'
        )
    
    def custom_on_success(request, identity_url, openid_response):
        # Reuse django_openidconsumer.views.default_on_success to set the 
        # relevant session variables:
        consumer_views.default_on_success(request, identity_url, openid_response)
        
        # Now look up the user's identity_url to see if they exist in the system
        try:
            user_openid = UserOpenID.objects.get(openid=identity_url)
        except UserOpenID.DoesNotExist:
            user_openid = None
        
        if user_openid:
            user = user_openid.user
            # Unfortunately we have to annotate the user with the 
            # 'django.contrib.auth.backends.ModelBackend' backend, or stuff breaks
            backend = load_backend('django.contrib.auth.backends.ModelBackend')
            user.backend = '%s.%s' % (
                backend.__module__, backend.__class__.__name__
            )
            log_user_in(request, user)
            
            return on_login_ok(request, identity_url)
        else:
            return on_login_failed(request, identity_url)
    
    # Re-use django_openidconsumer.views.complete, passing in a custom 
    # on_success function that checks to see if their OpenID is associated with 
    # a user in the system
    return consumer_views.complete(request, on_success=custom_on_success)

########NEW FILE########
__FILENAME__ = middleware
class OpenIDMiddleware(object):
    """
    Populate request.openid and request.openids with their openid. This comes 
    eithen from their cookie or from their session, depending on the presence 
    of OPENID_USE_SESSIONS.
    """
    def process_request(self, request):
        request.openids = request.session.get('openids', [])
        if request.openids:
            request.openid = request.openids[-1] # Last authenticated OpenID
        else:
            request.openid = None

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Nonce(models.Model):
    nonce = models.CharField(max_length=8)
    expires = models.IntegerField()
    def __unicode__(self):
        return "Nonce: %s" % self.nonce

class Association(models.Model):
    server_url = models.TextField(max_length=2047)
    handle = models.CharField(max_length=255)
    secret = models.TextField(max_length=255) # Stored base64 encoded
    issued = models.IntegerField()
    lifetime = models.IntegerField()
    assoc_type = models.TextField(max_length=64)
    def __unicode__(self):
        return "Association: %s, %s" % (self.server_url, self.handle)

########NEW FILE########
__FILENAME__ = util
from openid.store.interface import OpenIDStore
from openid.association import Association as OIDAssociation
from yadis import xri

import time, base64, md5

from django.conf import settings
from models import Association, Nonce

class OpenID:
    def __init__(self, openid, issued, attrs=None, sreg=None):
        self.openid = openid
        self.issued = issued
        self.attrs = attrs or {}
        self.sreg = sreg or {}
        self.is_iname = (xri.identifierScheme(openid) == 'XRI')
    
    def __repr__(self):
        return '<OpenID: %s>' % self.openid
    
    def __str__(self):
        return self.openid

class DjangoOpenIDStore(OpenIDStore):
    def __init__(self):
        self.max_nonce_age = 6 * 60 * 60 # Six hours
    
    def storeAssociation(self, server_url, association):
        assoc = Association(
            server_url = server_url,
            handle = association.handle,
            secret = base64.encodestring(association.secret),
            issued = association.issued,
            lifetime = association.issued,
            assoc_type = association.assoc_type
        )
        assoc.save()
    
    def getAssociation(self, server_url, handle=None):
        assocs = []
        if handle is not None:
            assocs = Association.objects.filter(
                server_url = server_url, handle = handle
            )
        else:
            assocs = Association.objects.filter(
                server_url = server_url
            )
        if not assocs:
            return None
        associations = []
        for assoc in assocs:
            association = OIDAssociation(
                assoc.handle, base64.decodestring(assoc.secret), assoc.issued,
                assoc.lifetime, assoc.assoc_type
            )
            if association.getExpiresIn() == 0:
                self.removeAssociation(server_url, assoc.handle)
            else:
                associations.append((association.issued, association))
        if not associations:
            return None
        return associations[-1][1]
    
    def removeAssociation(self, server_url, handle):
        assocs = list(Association.objects.filter(
            server_url = server_url, handle = handle
        ))
        assocs_exist = len(assocs) > 0
        for assoc in assocs:
            assoc.delete()
        return assocs_exist
    
    def storeNonce(self, nonce):
        nonce, created = Nonce.objects.get_or_create(
            nonce = nonce, defaults={'expires': int(time.time())}
        )
    
    def useNonce(self, nonce):
        try:
            nonce = Nonce.objects.get(nonce = nonce)
        except Nonce.DoesNotExist:
            return 0
        
        # Now check nonce has not expired
        nonce_age = int(time.time()) - nonce.expires
        if nonce_age > self.max_nonce_age:
            present = 0
        else:
            present = 1
        nonce.delete()
        return present
    
    def getAuthKey(self):
        # Use first AUTH_KEY_LEN characters of md5 hash of SECRET_KEY
        return md5.new(settings.SECRET_KEY).hexdigest()[:self.AUTH_KEY_LEN]
    
    def isDumb(self):
        return False

def from_openid_response(openid_response):
    issued = int(time.time())
    return OpenID(
        openid_response.identity_url, issued, openid_response.signed_args, 
        openid_response.extensionResponse('sreg')
    )

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse, HttpResponseRedirect, get_host
from django.shortcuts import render_to_response as render
from django.template import RequestContext
from django.conf import settings

import md5, re, time, urllib
from openid.consumer.consumer import Consumer, \
    SUCCESS, CANCEL, FAILURE, SETUP_NEEDED
from openid.consumer.discover import DiscoveryFailure
from yadis import xri

from util import OpenID, DjangoOpenIDStore, from_openid_response
from middleware import OpenIDMiddleware

from django.utils.html import escape

def get_url_host(request):
    if request.is_secure():
        protocol = 'https'
    else:
        protocol = 'http'
    host = escape(get_host(request))
    return '%s://%s' % (protocol, host)

def get_full_url(request):
    if request.is_secure():
        protocol = 'https'
    else:
        protocol = 'http'
    host = escape(request.META['HTTP_HOST'])
    return get_url_host(request) + request.get_full_path()

next_url_re = re.compile('^/[-\w/]+$')

def is_valid_next_url(next):
    # When we allow this:
    #   /openid/?next=/welcome/
    # For security reasons we want to restrict the next= bit to being a local 
    # path, not a complete URL.
    return bool(next_url_re.match(next))

def begin(request, sreg=None, extension_args=None, redirect_to=None, 
        on_failure=None):
    
    on_failure = on_failure or default_on_failure
    
    if request.GET.get('logo'):
        # Makes for a better demo
        return logo(request)
    
    extension_args = extension_args or {}
    if sreg:
        extension_args['sreg.optional'] = sreg
    trust_root = getattr(
        settings, 'OPENID_TRUST_ROOT', get_url_host(request) + '/'
    )
    redirect_to = redirect_to or getattr(
        settings, 'OPENID_REDIRECT_TO',
        # If not explicitly set, assume current URL with complete/ appended
        get_full_url(request).split('?')[0] + 'complete/'
    )
    # In case they were lazy...
    if not redirect_to.startswith('http://'):
        redirect_to =  get_url_host(request) + redirect_to
    
    if request.GET.get('next') and is_valid_next_url(request.GET['next']):
        if '?' in redirect_to:
            join = '&'
        else:
            join = '?'
        redirect_to += join + urllib.urlencode({
            'next': request.GET['next']
        })
    
    user_url = request.POST.get('openid_url', None)
    if not user_url:
        request_path = request.path
        if request.GET.get('next'):
            request_path += '?' + urllib.urlencode({
                'next': request.GET['next']
            })
        
        return render('openid_signin.html', {
            'action': request_path,
            'logo': request.path + '?logo=1',
        })
    
    if xri.identifierScheme(user_url) == 'XRI' and getattr(
        settings, 'OPENID_DISALLOW_INAMES', False
        ):
        return on_failure(request, 'i-names are not supported')
    
    consumer = Consumer(request.session, DjangoOpenIDStore())
    try:
        auth_request = consumer.begin(user_url)
    except DiscoveryFailure:
        return on_failure(request, "The OpenID was invalid")
    
    # Add extension args (for things like simple registration)
    for name, value in extension_args.items():
        namespace, key = name.split('.', 1)
        auth_request.addExtensionArg(namespace, key, value)
    
    redirect_url = auth_request.redirectURL(trust_root, redirect_to)
    return HttpResponseRedirect(redirect_url)

def complete(request, on_success=None, on_failure=None):
    on_success = on_success or default_on_success
    on_failure = on_failure or default_on_failure
    
    consumer = Consumer(request.session, DjangoOpenIDStore())
    # JanRain library raises a warning if passed unicode objects as the keys, 
    # so we convert to bytestrings before passing to the library
    query_dict = dict([
        (k.encode('utf8'), v.encode('utf8')) for k, v in request.GET.items()
    ])
    openid_response = consumer.complete(query_dict)
    
    if openid_response.status == SUCCESS:
        return on_success(request, openid_response.identity_url, openid_response)
    elif openid_response.status == CANCEL:
        return on_failure(request, 'The request was cancelled')
    elif openid_response.status == FAILURE:
        return on_failure(request, openid_response.message)
    elif openid_response.status == SETUP_NEEDED:
        return on_failure(request, 'Setup needed')
    else:
        assert False, "Bad openid status: %s" % openid_response.status

def default_on_success(request, identity_url, openid_response):
    if 'openids' not in request.session.keys():
        request.session['openids'] = []
    
    # Eliminate any duplicates
    request.session['openids'] = [
        o for o in request.session['openids'] if o.openid != identity_url
    ]
    request.session['openids'].append(from_openid_response(openid_response))
    
    # Set up request.openids and request.openid, reusing middleware logic
    OpenIDMiddleware().process_request(request)
    
    next = request.GET.get('next', '').strip()
    if not next or not is_valid_next_url(next):
        next = getattr(settings, 'OPENID_REDIRECT_NEXT', '/')
    
    return HttpResponseRedirect(next)

def default_on_failure(request, message):
    return render('openid_failure.html', {
        'message': message
    })

def signout(request):
    request.session['openids'] = []
    next = request.GET.get('next', '/')
    if not is_valid_next_url(next):
        next = '/'
    return HttpResponseRedirect(next)

def logo(request):
    return HttpResponse(
        OPENID_LOGO_BASE_64.decode('base64'), mimetype='image/gif'
    )

# Logo from http://openid.net/login-bg.gif
# Embedded here for convenience; you should serve this as a static file
OPENID_LOGO_BASE_64 = """
R0lGODlhEAAQAMQAAO3t7eHh4srKyvz8/P5pDP9rENLS0v/28P/17tXV1dHEvPDw8M3Nzfn5+d3d
3f5jA97Syvnv6MfLzcfHx/1mCPx4Kc/S1Pf189C+tP+xgv/k1N3OxfHy9NLV1/39/f///yH5BAAA
AAAALAAAAAAQABAAAAVq4CeOZGme6KhlSDoexdO6H0IUR+otwUYRkMDCUwIYJhLFTyGZJACAwQcg
EAQ4kVuEE2AIGAOPQQAQwXCfS8KQGAwMjIYIUSi03B7iJ+AcnmclHg4TAh0QDzIpCw4WGBUZeikD
Fzk0lpcjIQA7
"""

########NEW FILE########
__FILENAME__ = clusterer

import sys
import time
from clusterlizard.closestpair import closest_pair

# Some simple functions

def mean(l):
    return sum(l)/float(len(l))

# Cluster class

class Cluster(object):
    
    def __init__(self, iterable):
        self.points = set(iterable)
        self.mean = self._mean()
    
    def _mean(self):
        xs, ys = [], []
        for x, y, d in self.points:
            xs.append(x)
            ys.append(y)
        return mean(xs), mean(ys)
    
    def merge(self, other):
        return Cluster(self.points.union(other.points))
    
    def distance(self, other):
        return distance(self.mean, other.mean)
    
    def __len__(self):
        return len(self.points)


class Clusterer(object):
    
    def __init__(self, input, output, progress=None, separation=75):
        self.input = input
        self.output = output
        self.progress = progress
        self.separation = separation
    
    def run(self):
        "Runs the cluster analysis."
        
        clusters = set(Cluster([(x, y, d)]) for x, y, d in self.input)
        
        d = 0
        i = 0
        zoom = 17
        tooks = []
        
        while zoom >= 0:
            # Work out what separation is at this zoom
            m_per_pixel = (40075016.68 / 2**zoom) / 256
            max_sep = m_per_pixel * self.separation
            # Keep going until clusters are far apart or not very numerous.
            
            while d < max_sep and len(clusters) > 1:
                s = time.time()
                # Use closest-pair to find the closest two clusters
                d, (x1, y1, c1), (x2, y2, c2) = closest_pair([(c.mean[0], c.mean[1], c) for c in clusters])
                if d >= max_sep:
                    break
                # Merge them in the set
                cn = c1.merge(c2)
                clusters.discard(c1)
                clusters.discard(c2)
                clusters.add(cn)
                # Calculate stats
                i += 1
                tooks = [time.time() - s] + tooks[:2]
                took = mean(tooks)
                eta = took * (len(clusters) - 10) * 0.7
                eta = "%i:%i" % (eta/60, eta%60)
                if self.progress:
                    self.progress(i, len(clusters)-1, took, zoom, eta)
            self.output(clusters, zoom)
            zoom -= 1

########NEW FILE########
__FILENAME__ = generate

import random
import math


def latlong_to_mercator(lat, long):
    x = long * 20037508.34 / 180
    y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180)
    y = y * 20037508.34 / 180;
    return x, y


def mercator_to_latlong(x, y):
    long = (x / 20037508.34) * 180
    lat = (y / 20037508.34) * 180
    lat = 180/math.pi * (2 * math.atan(math.exp(lat * math.pi / 180)) - math.pi / 2)
    return lat, long



def random():
    f = open("points.csv", "w")
    
    for i in range(500):
        x = random.uniform(-20037508.34, 20037508.34)
        y = random.uniform(-15037508.34, 15037508.34)
        f.write('%s,%s,"Point %i"\n' % (x, y, i))
    
    f.close()

    
def geonames(file):
    f = open("cities.csv", "w")
    
    for row in file:
        items = row.split("\t")
        lat = float(items[4])
        long = float(items[5])
        name = items[1]
        x, y = latlong_to_mercator(lat, long)
        f.write('%s,%s,"%s"\n' % (x, y, name))
    
    f.close()

geonames(open("cities15000.txt"))
    
    
########NEW FILE########
__FILENAME__ = render

import cairo
import sys
import os
import math

width, height = 600.0, 600.0
mx1, my1, mx2, my2 = [-20037508.34, 20037508.34, 20037508.34, -20037508.34]
mxr = mx2 - mx1
myr = my2 - my1

surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
context = cairo.Context(surface)

def m_to_px(x, y):
    return ((x-mx1)/mxr)*width, ((y-my1)/myr)*height

context.set_source_rgba(1,1,1,1)
context.paint()
    
for row in open(sys.argv[1]):
    x, y, label = row.split(",")
    px, py = m_to_px(float(x), float(y))
    try:
        r = int(label)/100 + 1
    except ValueError:
        r = 2
    context.arc(px, py, r, 0, math.pi*2)
    context.set_source_rgba(0,0.2,0.6,0.8)
    context.fill()

surface.write_to_png("output.png")
surface.finish()

os.system("display output.png")
########NEW FILE########
__FILENAME__ = distance
from math import *
import util

# Average great-circle radius in kilometers, from Wikipedia.
# Using a sphere with this radius results in an error of up to about 0.5%.
EARTH_RADIUS = 6372.795

# From http://www.movable-type.co.uk/scripts/LatLongVincenty.html:
#   The most accurate and widely used globally-applicable model for the earth
#   ellipsoid is WGS-84, used in this script. Other ellipsoids offering a
#   better fit to the local geoid include Airy (1830) in the UK, International
#   1924 in much of Europe, Clarke (1880) in Africa, and GRS-67 in South
#   America. America (NAD83) and Australia (GDA) use GRS-80, functionally
#   equivalent to the WGS-84 ellipsoid.
#
#             model             major (km)   minor (km)     flattening
ELLIPSOIDS = {'WGS-84':        (6378.137,    6356.7523142,  1 / 298.257223563),
              'GRS-80':        (6378.137,    6356.7523141,  1 / 298.257222101),
              'Airy (1830)':   (6377.563396, 6356.256909,   1 / 299.3249646),
              'Intl 1924':     (6378.388,    6356.911946,   1 / 297.0),
              'Clarke (1880)': (6378.249145, 6356.51486955, 1 / 293.465),
              'GRS-67':        (6378.1600,   6356.774719,   1 / 298.25),
              }

def arc_degrees(arcminutes=0, arcseconds=0):
    """Calculate the decimal equivalent of the sum of ``arcminutes`` and
    ``arcseconds`` in degrees."""
    if arcminutes is None:
        arcminutes = 0
    if arcseconds is None:
        arcseconds = 0
    arcmin = float(arcminutes)
    arcsec = float(arcseconds)
    return arcmin * 1 / 60. + arcsec * 1 / 3600.

def kilometers(miles=0, feet=0, nautical=0):
    d = 0
    if feet:
        miles += feet / ft(1.0)
    if nautical:
        d += nautical / nm(1.0)
    d += miles * 1.609344
    return d

def miles(kilometers=0, feet=0, nautical=0):
    d = 0
    if nautical:
        kilometers += nautical / nm(1.0)
    if feet:
        d += feet / ft(1.0)
    d += kilometers * 0.621371192
    return d

def feet(miles=0, kilometers=0, nautical=0):
    d = 0
    if nautical:
        kilometers += nautical / nm(1.0)
    if kilometers:
        miles += mi(kilometers)
    d += miles * 5280
    return d

def nautical(kilometers=0, miles=0, feet=0):
    d = 0
    if feet:
        miles += feet / ft(1.0)
    if miles:
        kilometers += km(miles)
    d += kilometers / 1.852
    return d

km = kilometers
mi = miles
ft = feet
nm = nautical


class Distance(object):
    def __init__(self, kilometers=0, miles=0, feet=0, nautical=0):
        """Initialize a Distance whose length is the sum of all the units
        measured in the constructor (kilometers, miles, feet, nautical miles).
        """
        kilometers += km(miles=miles, feet=feet, nautical=nautical)
        self._kilometers = kilometers

    @property
    def kilometers(self):
        return self._kilometers
    
    @property
    def miles(self):
        return miles(self.kilometers)

    @property
    def feet(self):
        return feet(self.miles)

    @property
    def nautical(self):
        return nautical(self.kilometers)

    # Sadly, just aliasing the above properties with their abbreviations does
    # not work when they are subclassed. The easiest way I could find to
    # make this work without using a metaclass was to write more full-fledged
    # definitions...

    @property
    def mi(self):
        return self.miles
    
    @property
    def km(self):
        return self.kilometers
    
    @property
    def ft(self):
        return self.feet

    @property
    def nm(self):
        return self.nautical

    def __add__(self, other):
        """Return a new Distance of length ``self`` + ``other``."""
        if isinstance(other, Distance):
            return Distance(self.kilometers + other.kilometers)
        else:
            raise TypeError("Distance must be added with Distance.")

    def __sub__(self, other):
        """Return a new Distance of length ``self`` - ``other``."""
        if isinstance(other, Distance):
            return Distance(self.kilometers - other.kilometers)
        else:
            raise TypeError("Distance must be subtracted from Distance.")
        
    def __mul__(self, other):
        """Return a new Distance ``other`` times the length of ``self``,
        ``other`` is a number (int, float, long, or Decimal).
        """
        if isinstance(other, (int, float, long, Decimal)):
            other = float(other)
            return Distance(self.kilometers * other)
        else:
            raise TypeError("Distance must be multiplied by number.")

    def __div__(self, other):
        """If ``other`` is a number (int, float, long, or Decimal), return
        a new Distance of length ``self`` / ``other``.
        
        If ``other`` is a Distance, return the fraction given by
        ``self`` / ``other``.
        """
        if isinstance(other, Distance):
            return float(self.kilometers) / other.kilometers
        elif isinstance(other, (int, float, long, Decimal)):
            other = float(other)
            return Distance(self.kilometers / other)
        else:
            raise TypeError("Distance must be divided by Distance or number.")

    def __nonzero__(self):
        """Return whether or not this Distance is 0 units in length."""
        return bool(self.kilometers)


class GeodesicDistance(Distance):
    def __init__(self, a, b):
        """Initialize a Distance whose length is the distance between the two
        geodesic points ``a`` and ``b``, using the ``calculate`` method to
        determine this distance.
        """
        if isinstance(a, basestring):
            a = util.parse_geo(a)
        if isinstance(b, basestring):
            b = util.parse_geo(b)
        
        self.a = a
        self.b = b
        
        if a and b:
            self.calculate()

    def calculate(self):
        """Calculate and set the distance between ``self.a`` and ``self.b``,
        which should be two geodesic points. Since there are multiple formulas
        to calculate this, implementation is left up to the subclass.
        """
        raise NotImplementedError

    @property
    def kilometers(self):
        raise NotImplementedError

class GreatCircleDistance(GeodesicDistance):
    """Use spherical geometry to calculate the surface distance between two
    geodesic points. This formula can be written many different ways, including
    just the use of the spherical law of cosines or the haversine formula.
    
    The class member ``RADIUS`` indicates which radius of the earth to use,
    in kilometers. The default is to use the module constant ``EARTH_RADIUS``,
    which uses the average great-circle radius.
    """
    
    RADIUS = EARTH_RADIUS
    
    def calculate(self):
        lat1, lng1 = map(radians, self.a)
        lat2, lng2 = map(radians, self.b)
        
        sin_lat1, cos_lat1 = sin(lat1), cos(lat1)
        sin_lat2, cos_lat2 = sin(lat2), cos(lat2)
        
        delta_lng = lng2 - lng1
        cos_delta_lng, sin_delta_lng = cos(delta_lng), sin(delta_lng)
        
        central_angle = acos(sin_lat1 * sin_lat2 +
                             cos_lat1 * cos_lat2 * cos_delta_lng)
        
        # From http://en.wikipedia.org/wiki/Great_circle_distance:
        #   Historically, the use of this formula was simplified by the
        #   availability of tables for the haversine function. Although this
        #   formula is accurate for most distances, it too suffers from
        #   rounding errors for the special (and somewhat unusual) case of
        #   antipodal points (on opposite ends of the sphere). A more
        #   complicated formula that is accurate for all distances is: (below)
        
        d = atan2(sqrt((cos_lat2 * sin_delta_lng) ** 2 +
                       (cos_lat1 * sin_lat2 -
                        sin_lat1 * cos_lat2 * cos_delta_lng) ** 2),
                  sin_lat1 * sin_lat2 + cos_lat1 * cos_lat2 * cos_delta_lng)
        
        self.radians = d
    
    @property
    def kilometers(self):
        return self.RADIUS * self.radians
    

class VincentyDistance(GeodesicDistance):
    """Calculate the geodesic distance between two points using the formula
    devised by Thaddeus Vincenty, with an accurate ellipsoidal model of the
    earth.
    
    The class attribute ``ELLIPSOID`` indicates which ellipsoidal model of the
    earth to use. If it is a string, it is looked up in the ELLIPSOIDS
    dictionary to obtain the major and minor semiaxes and the flattening.
    Otherwise, it should be a tuple with those values. The most globally
    accurate model is WGS-84. See the comments above the ELLIPSOIDS dictionary
    for more information.
    """

    ELLIPSOID = ELLIPSOIDS['WGS-84']
    
    def calculate(self):
        lat1, lng1 = map(radians, self.a)
        lat2, lng2 = map(radians, self.b)
        
        if isinstance(self.ELLIPSOID, basestring):
            major, minor, f = ELLIPSOIDS[self.ELLIPSOID]
        else:
            major, minor, f = self.ELLIPSOID
        
        delta_lng = lng2 - lng1
        
        reduced_lat1 = atan((1 - f) * tan(lat1))
        reduced_lat2 = atan((1 - f) * tan(lat2))
        
        sin_reduced1, cos_reduced1 = sin(reduced_lat1), cos(reduced_lat1)
        sin_reduced2, cos_reduced2 = sin(reduced_lat2), cos(reduced_lat2)
        
        lambda_lng = delta_lng
        lambda_prime = 2 * pi
        
        iter_limit = 20
        
        while abs(lambda_lng - lambda_prime) > 10e-12 and iter_limit > 0:
            sin_lambda_lng, cos_lambda_lng = sin(lambda_lng), cos(lambda_lng)
            
            sin_sigma = sqrt((cos_reduced2 * sin_lambda_lng) ** 2 +
                             (cos_reduced1 * sin_reduced2 - sin_reduced1 *
                              cos_reduced2 * cos_lambda_lng) ** 2)
            
            if sin_sigma == 0:
                # Coincident points
                self._kilometers = self.initial_bearing = self.final_bearing = 0
                return
            
            cos_sigma = (sin_reduced1 * sin_reduced2 +
                         cos_reduced1 * cos_reduced2 * cos_lambda_lng)
            
            sigma = atan2(sin_sigma, cos_sigma)
            
            sin_alpha = cos_reduced1 * cos_reduced2 * sin_lambda_lng / sin_sigma
            cos_sq_alpha = 1 - sin_alpha ** 2
            
            if cos_sq_alpha != 0:
                cos2_sigma_m = cos_sigma - 2 * (sin_reduced1 * sin_reduced2 /
                                                cos_sq_alpha)
            else:
                cos2_sigma_m = 0.0 # Equatorial line
            
            C = f / 16. * cos_sq_alpha * (4 + f * (4 - 3 * cos_sq_alpha))
            
            lambda_prime = lambda_lng
            lambda_lng = (delta_lng + (1 - C) * f * sin_alpha *
                          (sigma + C * sin_sigma *
                           (cos2_sigma_m + C * cos_sigma * 
                            (-1 + 2 * cos2_sigma_m ** 2))))
            iter_limit -= 1
            
        if iter_limit == 0:
            raise ValueError("Vincenty formula failed to converge!")
        
        u_sq = cos_sq_alpha * (major ** 2 - minor ** 2) / minor ** 2
        
        A = 1 + u_sq / 16384. * (4096 + u_sq * (-768 + u_sq *
                                                (320 - 175 * u_sq)))
        
        B = u_sq / 1024. * (256 + u_sq * (-128 + u_sq * (74 - 47 * u_sq)))
        
        delta_sigma = (B * sin_sigma *
                       (cos2_sigma_m + B / 4. *
                        (cos_sigma * (-1 + 2 * cos2_sigma_m ** 2) -
                         B / 6. * cos2_sigma_m * (-3 + 4 * sin_sigma ** 2) *
                         (-3 + 4 * cos2_sigma_m ** 2))))
        
        s = minor * A * (sigma - delta_sigma)
        
        sin_lambda, cos_lambda = sin(lambda_lng), cos(lambda_lng)
        
        alpha_1 = atan2(cos_reduced2 * sin_lambda,
                        cos_reduced1 * sin_reduced2 -
                        sin_reduced1 * cos_reduced2 * cos_lambda)
        
        alpha_2 = atan2(cos_reduced1 * sin_lambda,
                        cos_reduced1 * sin_reduced2 * cos_lambda -
                        sin_reduced1 * cos_reduced2)
        
        self._kilometers = s
        self.initial_bearing = (360 + degrees(alpha_1)) % 360
        self.final_bearing = (360 + degrees(alpha_2)) % 360

    @property
    def kilometers(self):
        return self._kilometers

    @property
    def forward_azimuth(self):
        return self.initial_bearing


# Set the default distance formula to the most generally accurate.
distance = VincentyDistance


def destination(start, bearing, distance, radius=EARTH_RADIUS):
    lat1, lng1 = map(radians, start)
    bearing = radians(bearing)
    
    if isinstance(distance, Distance):
        distance = distance.kilometers
        
    d_div_r = float(distance) / radius
    
    lat2 = asin(sin(lat1) * cos(d_div_r) +
                cos(lat1) * sin(d_div_r) * cos(bearing))
    
    lng2 = lng1 + atan2(sin(bearing) * sin(d_div_r) * cos(lat1),
                        cos(d_div_r) - sin(lat1) * sin(lat2))
    
    return (degrees(lat2), degrees(lng2))


def vincenty_destination(start, bearing, distance,
                         ellipsoid=ELLIPSOIDS['WGS-84']):
    lat1, lng1 = map(radians, start)
    bearing = radians(bearing)
    
    if isinstance(distance, Distance):
        distance = distance.kilometers
    
    if isinstance(ellipsoid, basestring):
        ellipsoid = ELLIPSOIDS[ellipsoid]
    
    major, minor, f = ellipsoid
    
    tan_reduced1 = (1 - f) * tan(lat1)
    cos_reduced1 = 1 / sqrt(1 + tan_reduced1 ** 2)
    sin_reduced1 = tan_reduced1 * cos_reduced1
    sin_bearing, cos_bearing = sin(bearing), cos(bearing)
    sigma1 = atan2(tan_reduced1, cos_bearing)
    sin_alpha = cos_reduced1 * sin_bearing
    cos_sq_alpha = 1 - sin_alpha ** 2
    u_sq = cos_sq_alpha * (major ** 2 - minor ** 2) / minor ** 2
    
    A = 1 + u_sq / 16384. * (4096 + u_sq * (-768 + u_sq * (320 - 175 * u_sq)))
    B = u_sq / 1024. * (256 + u_sq * (-128 + u_sq * (74 - 47 * u_sq)))

    sigma = distance / (minor * A)
    sigma_prime = 2 * pi
    
    while abs(sigma - sigma_prime) > 10e-12:
        cos2_sigma_m = cos(2 * sigma1 + sigma)
        sin_sigma, cos_sigma = sin(sigma), cos(sigma)
        delta_sigma = B * sin_sigma * (cos2_sigma_m + B / 4. *
                                       (cos_sigma * (-1 + 2 * cos2_sigma_m) -
                                        B / 6. * cos2_sigma_m *
                                        (-3 + 4 * sin_sigma ** 2) *
                                        (-3 + 4 * cos2_sigma_m ** 2)))
        sigma_prime = sigma
        sigma = distance / (minor * A) + delta_sigma
    
    sin_sigma, cos_sigma = sin(sigma), cos(sigma)
    
    lat2 = atan2(sin_reduced1 * cos_sigma +
                 cos_reduced1 * sin_sigma * cos_bearing,
                 (1 - f) * sqrt(sin_alpha ** 2 +
                                (sin_reduced1 * sin_sigma -
                                 cos_reduced1 * cos_sigma * cos_bearing) ** 2))
    
    lambda_lng = atan2(sin_sigma * sin_bearing,
                       cos_reduced1 * cos_sigma -
                       sin_reduced1 * sin_sigma * cos_bearing)
    
    C = f / 16. * cos_sq_alpha * (4 + f * (4 - 3 * cos_sq_alpha))
    
    delta_lng = (lambda_lng - (1 - C) * f * sin_alpha *
                 (sigma + C * sin_sigma *
                  (cos2_sigma_m + C * cos_sigma *
                   (-1 + 2 * cos2_sigma_m ** 2))))
    
    final_bearing = atan2(sin_alpha,
                          cos_reduced1 * cos_sigma * cos_bearing -
                          sin_reduced1 * sin_sigma)
    
    lng2 = lng1 + delta_lng
    
    return (degrees(lat2), degrees(lng2))

########NEW FILE########
__FILENAME__ = geocoders
import re
import csv
import sys
import getpass
import xmlrpclib
import htmlentitydefs
import xml.dom.minidom
from itertools import groupby
from urllib import quote_plus, urlencode
from urllib2 import urlopen, HTTPError
from xml.parsers.expat import ExpatError

try:
    set
except NameError:
    import sets.Set as set

# Other submodules from geopy:

import util

# Now try some more exotic modules...

try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    print "BeautifulSoup was not found. " \
          "Geocoders assuming malformed markup will not work."

try:
    import simplejson
except ImportError:
    try:
        from django.utils import simplejson
    except ImportError:
        print "simplejson was not found. " \
              "Geocoders relying on JSON parsing will not work."


class Geocoder(object):
    """Base class for all geocoders."""

    def geocode(self, string):
        raise NotImplementedError


class WebGeocoder(Geocoder):
    """A Geocoder subclass with utility methods helpful for handling results
    given by web-based geocoders."""
    
    @classmethod
    def _get_encoding(cls, page, contents=None):
        """Get the last encoding (charset) listed in the header of ``page``."""
        plist = page.headers.getplist()
        if plist:
            key, value = plist[-1].split('=')
            if key.lower() == 'charset':
                return value
        if contents:
            try:
                return xml.dom.minidom.parseString(contents).encoding
            except ExpatError:
                pass

    @classmethod
    def _decode_page(cls, page):
        """Read the encoding (charset) of ``page`` and try to encode it using
        UTF-8."""
        contents = page.read()
        encoding = cls._get_encoding(page, contents) or sys.getdefaultencoding()
        return unicode(contents, encoding=encoding).encode('utf-8')

    @classmethod
    def _get_first_text(cls, node, tag_names, strip=None):
        """Get the text value of the first child of ``node`` with tag
        ``tag_name``. The text is stripped using the value of ``strip``."""
        if isinstance(tag_names, basestring):
            tag_names = [tag_names]
        if node:
            while tag_names:
                nodes = node.getElementsByTagName(tag_names.pop(0))
                if nodes:
                    child = nodes[0].firstChild
                    return child and child.nodeValue.strip(strip)

    @classmethod
    def _join_filter(cls, sep, seq, pred=bool):
        """Join items in ``seq`` with string ``sep`` if pred(item) is True.
        Sequence items are passed to unicode() before joining."""
        return sep.join([unicode(i) for i in seq if pred(i)])


class MediaWiki(WebGeocoder):
    def __init__(self, format_url, transform_string=None):
        """Initialize a geocoder that can parse MediaWiki pages with the GIS
        extension enabled.

        ``format_url`` is a URL string containing '%s' where the page name to
        request will be interpolated. For example: 'http://www.wiki.com/wiki/%s'

        ``transform_string`` is a callable that will make appropriate
        replacements to the input string before requesting the page. If None is
        given, the default transform_string which replaces ' ' with '_' will be
        used. It is recommended that you consider this argument keyword-only,
        since subclasses will likely place it last.
        """
        self.format_url = format_url

        if callable(transform_string):
            self.transform_string = transform_string

    @classmethod
    def transform_string(cls, string):
        """Do the WikiMedia dance: replace spaces with underscores."""
        return string.replace(' ', '_')

    def geocode(self, string):
        wiki_string = self.transform_string(string)
        url = self.format_url % wiki_string
        return self.geocode_url(url)

    def geocode_url(self, url):
        print "Fetching %s..." % url
        page = urlopen(url)
        name, (latitude, longitude) = self.parse_xhtml(page)
        return (name, (latitude, longitude))        

    def parse_xhtml(self, page):
        soup = isinstance(page, BeautifulSoup) and page or BeautifulSoup(page)

        meta = soup.head.find('meta', {'name': 'geo.placename'})
        name = meta and meta['content'] or None

        meta = soup.head.find('meta', {'name': 'geo.position'})
        if meta:
            position = meta['content']
            latitude, longitude = util.parse_geo(position)
            if latitude == 0 or longitude == 0:
                latitude = longitude = None
        else:
            latitude = longitude = None

        return (name, (latitude, longitude))


class SemanticMediaWiki(MediaWiki):
    def __init__(self, format_url, attributes=None, relations=None,
                 prefer_semantic=False, transform_string=None):
        """Initialize a geocoder that can parse MediaWiki pages with the GIS
        extension enabled, and can follow Semantic MediaWiki relations until
        a geocoded page is found.

        ``attributes`` is a sequence of semantic attribute names that can
        contain geographical coordinates. They will be tried, in order,
        if the page is not geocoded with the GIS extension. A single attribute
        may be passed as a string.
        For example: attributes=['geographical coordinate']
                 or: attributes='geographical coordinate'
        
        ``relations`` is a sequence of semantic relation names that will be
        followed, depth-first in order, until a geocoded page is found. A
        single relation name may be passed as a string.
        For example: relations=['Located in']
                 or: relations='Located in'
        
        ``prefer_semantic`` indicates whether or not the contents of the
        semantic attributes (given by ``attributes``) should be preferred
        over the GIS extension's coordinates if both exist. This defaults to
        False, since making it True will cause every page's RDF to be
        requested when it often won't be necessary.
        """
        base = super(SemanticMediaWiki, self)
        base.__init__(format_url, transform_string)

        if attributes is None:
            self.attributes = []
        elif isinstance(attributes, basestring):
            self.attributes = [attributes]
        else:
            self.attributes = attributes

        if relations is None:
            self.relations = []
        elif isinstance(relations, basestring):
            self.relations = [relations]
        else:
            self.relations = relations
        
        self.prefer_semantic = prefer_semantic

    def transform_semantic(self, string):
        """Normalize semantic attribute and relation names by replacing spaces
        with underscores and capitalizing the result."""
        return string.replace(' ', '_').capitalize()

    def geocode_url(self, url, tried=None):
        if tried is None:
            tried = set()

        print "Fetching %s..." % url
        page = urlopen(url)
        soup = BeautifulSoup(page)
        name, (latitude, longitude) = self.parse_xhtml(soup)
        if None in (name, latitude, longitude) or self.prefer_semantic:
            rdf_url = self.parse_rdf_link(soup)
            print "Fetching %s..." % rdf_url
            page = urlopen(rdf_url)
            
            things, thing = self.parse_rdf(page)
            name = self.get_label(thing)
            
            attributes = self.get_attributes(thing)
            for attribute, value in attributes:
                latitude, longitude = util.parse_geo(value)
                if None not in (latitude, longitude):
                    break
            
            if None in (latitude, longitude):
                relations = self.get_relations(thing)
                for relation, resource in relations:
                    url = things.get(resource, resource)
                    if url in tried: # Avoid cyclic relationships.
                        continue
                    tried.add(url)
                    name, (latitude, longitude) = self.geocode_url(url, tried)
                    if None not in (name, latitude, longitude):
                        break

        return (name, (latitude, longitude))

    def parse_rdf_link(self, page, mime_type='application/rdf+xml'):
        """Parse the URL of the RDF link from the <head> of ``page``."""
        soup = isinstance(page, BeautifulSoup) and page or BeautifulSoup(page)
        link = soup.head.find('link', rel='alternate', type=mime_type)
        return link and link['href'] or None

    def parse_rdf(self, page):
        if not isinstance(page, basestring):
            page = self._decode_page(page)
        doc = xml.dom.minidom.parseString(page)

        things = {}
        for thing in reversed(doc.getElementsByTagName('smw:Thing')):
            name = thing.attributes['rdf:about'].value
            articles = thing.getElementsByTagName('smw:hasArticle')
            things[name] = articles[0].attributes['rdf:resource'].value

        # ``thing`` should now be the semantic data for the exported page.

        return (things, thing)

    def get_label(self, thing):
        return self._get_first_text(thing, 'rdfs:label')

    def get_attributes(self, thing, attributes=None):
        if attributes is None:
            attributes = self.attributes
        
        for attribute in attributes:
            attribute = self.transform_semantic(attribute)
            for node in thing.getElementsByTagName('attribute:' + attribute):
                value = node.firstChild.nodeValue.strip()
                yield (attribute, value)

    def get_relations(self, thing, relations=None):
        if relations is None:
            relations = self.relations

        for relation in relations:
            relation = self.transform_semantic(relation)
            for node in thing.getElementsByTagName('relation:' + relation):
                resource = node.attributes['rdf:resource'].value
                yield (relation, resource)


class Google(WebGeocoder):
    """Geocoder using the Google Maps API."""
    
    def __init__(self, api_key=None, domain='maps.google.com',
                 resource='maps/geo', format_string='%s', output_format='kml'):
        """Initialize a customized Google geocoder with location-specific
        address information and your Google Maps API key.

        ``api_key`` should be a valid Google Maps API key. It is required for
        the 'maps/geo' resource to work.

        ``domain`` should be a the Google Maps domain to connect to. The default
        is 'maps.google.com', but if you're geocoding address in the UK (for
        example), you may want to set it to 'maps.google.co.uk'.

        ``resource`` is the HTTP resource to give the query parameter.
        'maps/geo' is the HTTP geocoder and is a documented API resource.
        'maps' is the actual Google Maps interface and its use for just
        geocoding is undocumented. Anything else probably won't work.

        ``format_string`` is a string containing '%s' where the string to
        geocode should be interpolated before querying the geocoder.
        For example: '%s, Mountain View, CA'. The default is just '%s'.
        
        ``output_format`` can be 'json', 'xml', 'kml', 'csv', or 'js' and will
        control the output format of Google's response. The default is 'kml'
        since it is supported by both the 'maps' and 'maps/geo' resources. The
        'js' format is the most likely to break since it parses Google's
        JavaScript, which could change. However, it currently returns the best
        results for restricted geocoder areas such as the UK.
        """
        self.api_key = api_key
        self.domain = domain
        self.resource = resource
        self.format_string = format_string
        self.output_format = output_format

    @property
    def url(self):
        domain = self.domain.strip('/')
        resource = self.resource.strip('/')
        return "http://%(domain)s/%(resource)s?%%s" % locals()

    def geocode(self, string, exactly_one=True):
        params = {'q': self.format_string % string,
                  'output': self.output_format.lower(),
                  }
        if self.resource.rstrip('/').endswith('geo'):
            # An API key is only required for the HTTP geocoder.
            params['key'] = self.api_key

        url = self.url % urlencode(params)
        return self.geocode_url(url, exactly_one)

    def geocode_url(self, url, exactly_one=True):
        print "Fetching %s..." % url
        page = urlopen(url)
        
        dispatch = getattr(self, 'parse_' + self.output_format)
        return dispatch(page, exactly_one)

    def parse_xml(self, page, exactly_one=True):
        """Parse a location name, latitude, and longitude from an XML response.
        """
        if not isinstance(page, basestring):
            page = self._decode_page(page)
        try:
            doc = xml.dom.minidom.parseString(page)
        except ExpatError:
            places = []
        else:
            places = doc.getElementsByTagName('Placemark')

        if exactly_one and len(places) != 1:
            raise ValueError("Didn't find exactly one placemark! " \
                             "(Found %d.)" % len(places))
        
        def parse_place(place):
            location = self._get_first_text(place, ['address', 'name']) or None
            points = place.getElementsByTagName('Point')
            point = points and points[0] or None
            coords = self._get_first_text(point, 'coordinates') or None
            if coords:
                longitude, latitude = [float(f) for f in coords.split(',')[:2]]
            else:
                latitude = longitude = None
                _, (latitude, longitude) = self.geocode(location)
            return (location, (latitude, longitude))
        
        if exactly_one:
            return parse_place(places[0])
        else:
            return (parse_place(place) for place in places)

    def parse_csv(self, page, exactly_one=True):
        raise NotImplementedError

    def parse_kml(self, page, exactly_one=True):
        return self.parse_xml(page, exactly_one)

    def parse_json(self, page, exactly_one=True):
        if not isinstance(page, basestring):
            page = self._decode_page(page)
        json = simplejson.loads(page)
        places = json.get('Placemark', [])

        if exactly_one and len(places) != 1:
            raise ValueError("Didn't find exactly one placemark! " \
                             "(Found %d.)" % len(places))

        def parse_place(place):
            location = place.get('address')
            longitude, latitude = place['Point']['coordinates'][:2]
            return (location, (latitude, longitude))
        
        if exactly_one:
            return parse_place(places[0])
        else:
            return (parse_place(place) for place in places)

    def parse_js(self, page, exactly_one=True):
        """This parses JavaScript returned by queries the actual Google Maps
        interface and could thus break easily. However, this is desirable if
        the HTTP geocoder doesn't work for addresses in your country (the
        UK, for example).
        """
        if not isinstance(page, basestring):
            page = self._decode_page(page)

        LATITUDE = r"[\s,]lat:\s*(?P<latitude>-?\d+\.\d+)"
        LONGITUDE = r"[\s,]lng:\s*(?P<longitude>-?\d+\.\d+)"
        LOCATION = r"[\s,]laddr:\s*'(?P<location>.*?)(?<!\\)',"
        ADDRESS = r"(?P<address>.*?)(?:(?: \(.*?@)|$)"
        MARKER = '.*?'.join([LATITUDE, LONGITUDE, LOCATION])
        MARKERS = r"{markers: (?P<markers>\[.*?\]),\s*polylines:"            

        def parse_marker(marker):
            latitude, longitude, location = marker
            location = re.match(ADDRESS, location).group('address')
            latitude, longitude = float(latitude), float(longitude)
            return (location, (latitude, longitude))

        match = re.search(MARKERS, page)
        markers = match and match.group('markers') or ''
        markers = re.findall(MARKER, markers)
       
        if exactly_one:
            if len(markers) != 1:
                raise ValueError("Didn't find exactly one marker! " \
                                 "(Found %d.)" % len(markers))
            
            marker = markers[0]
            return parse_marker(marker)
        else:
            return (parse_marker(marker) for marker in markers)


class Yahoo(WebGeocoder):
    """Geocoder using the Yahoo! Maps API.
    
    Note: The Terms of Use dictate that the stand-alone geocoder may only be
    used for displaying Yahoo! Maps or points on Yahoo! Maps. Lame.

    See the Yahoo! Maps API Terms of Use for more information:
    http://developer.yahoo.com/maps/mapsTerms.html
    """

    def __init__(self, app_id, format_string='%s', output_format='xml'):
        """Initialize a customized Yahoo! geocoder with location-specific
        address information and your Yahoo! Maps Application ID.

        ``app_id`` should be a valid Yahoo! Maps Application ID.

        ``format_string`` is a string containing '%s' where the string to
        geocode should be interpolated before querying the geocoder.
        For example: '%s, Mountain View, CA'. The default is just '%s'.

        ``output_format`` can currently only be 'xml'.
        """
        self.app_id = app_id
        self.format_string = format_string
        self.output_format = output_format.lower()
        self.url = "http://api.local.yahoo.com/MapsService/V1/geocode?%s"

    def geocode(self, string, exactly_one=True):
        params = {'location': self.format_string % string,
                  'output': self.output_format,
                  'appid': self.app_id
                  }
        url = self.url % urlencode(params)
        return self.geocode_url(url, exactly_one)
    
    def geocode_url(self, url, exactly_one=True):
        print "Fetching %s..." % url
        page = urlopen(url)
        
        parse = getattr(self, 'parse_' + self.output_format)
        return parse(page, exactly_one)

    def parse_xml(self, page, exactly_one=True):
        """Parse a location name, latitude, and longitude from an XML response.
        """
        if not isinstance(page, basestring):
            page = self._decode_page(page)
        doc = xml.dom.minidom.parseString(page)
        results = doc.getElementsByTagName('Result')
        
        if exactly_one and len(results) != 1:
            raise ValueError("Didn't find exactly one result! " \
                             "(Found %d.)" % len(results))

        def parse_result(result):
            strip = ", \n"
            address = self._get_first_text(result, 'Address', strip)
            city = self._get_first_text(result, 'City', strip)
            state = self._get_first_text(result, 'State', strip)
            zip = self._get_first_text(result, 'Zip', strip)
            country = self._get_first_text(result, 'Country', strip)
            city_state = self._join_filter(", ", [city, state])
            place = self._join_filter(" ", [city_state, zip])
            location = self._join_filter(", ", [address, place, country])
            latitude = self._get_first_text(result, 'Latitude') or None
            latitude = latitude and float(latitude)
            longitude = self._get_first_text(result, 'Longitude') or None
            longitude = longitude and float(longitude)
            return (location, (latitude, longitude))
    
        if exactly_one:
            return parse_result(results[0])
        else:
            return (parse_result(result) for result in results)


class GeocoderDotUS(WebGeocoder):
    """Geocoder using the United States-only geocoder.us API at
    http://geocoder.us. This geocoder is free for non-commercial purposes,
    otherwise you must register and pay per call. This class supports both free
    and commercial API usage.
    """
    
    def __init__(self, username=None, password=None, format_string='%s',
                 protocol='xmlrpc'):
        """Initialize a customized geocoder.us geocoder with location-specific
        address information and login information (for commercial usage).
        
        if ``username`` and ``password`` are given, they will be used to send
        account information to the geocoder.us API. If ``username`` is given
        and ``password`` is none, the ``getpass` module will be used to
        prompt for the password.
        
        ``format_string`` is a string containing '%s' where the string to
        geocode should be interpolated before querying the geocoder.
        For example: '%s, Mountain View, CA'. The default is just '%s'.
        
        ``protocol`` currently supports values of 'xmlrpc' and 'rest'.
        """
        if username and password is None:
            prompt = "geocoder.us password for %r: " % username
            password = getpass.getpass(prompt)

        self.format_string = format_string
        self.protocol = protocol
        self.username = username
        self.__password = password

    @property
    def url(self):
        domain = "geocoder.us"
        username = self.username
        password = self.__password
        protocol = self.protocol.lower()
        
        if username and password:
            auth = "%s:%s@" % (username, password)
            resource = "member/service/%s/" % protocol
        else:
            auth = ""
            resource = "service/%s/" % protocol

        if protocol not in ['xmlrpc', 'soap']:
            resource += "geocode?%s"

        return "http://%(auth)s%(domain)s/%(resource)s" % locals()

    def geocode(self, string, exactly_one=True):
        dispatch = getattr(self, 'geocode_' + self.protocol)
        return dispatch(string, exactly_one)

    def geocode_xmlrpc(self, string, exactly_one=True):
        proxy = xmlrpclib.ServerProxy(self.url)
        results = proxy.geocode(self.format_string % string)
        
        if exactly_one and len(results) != 1:
            raise ValueError("Didn't find exactly one result! " \
                             "(Found %d.)" % len(results))

        def parse_result(result):
            address = self._join_filter(" ", [result.get('number'),
                                              result.get('prefix'),
                                              result.get('street'),
                                              result.get('type'),
                                              result.get('suffix')])
            city_state = self._join_filter(", ", [result.get('city'),
                                                  result.get('state')])
            place = self._join_filter(" ", [city_state, result.get('zip')])
            location = self._join_filter(", ", [address, place]) or None
            latitude = result.get('lat')
            longitude = result.get('long')
            return (location, (latitude, longitude))
        
        if exactly_one:
            return parse_result(results[0])
        else:
            return (parse_result(result) for result in results)

    def geocode_rest(self, string, exactly_one=True):
        params = {'address': self.format_string % string}
        url = self.url % urlencode(params)
        page = urlopen(url)
        return self.parse_rdf(page, exactly_one)

    def parse_rdf(self, page, exactly_one=True):
        """Parse a location name, latitude, and longitude from an RDF response.
        """
        if not isinstance(page, basestring):
            page = self._decode_page(page)
        doc = xml.dom.minidom.parseString(page)
        points = doc.getElementsByTagName('geo:Point')
        
        if exactly_one and len(points) != 1:
            raise ValueError("Didn't find exactly one point! " \
                             "(Found %d.)" % len(points))
        
        def parse_point(point):
            strip = ", \n"
            location = self._get_first_text(point, 'dc:description', strip)
            location = location or None
            latitude = self._get_first_text(point, 'geo:lat') or None
            latitude = latitude and float(latitude)
            longitude = self._get_first_text(point, 'geo:long') or None
            longitude = longitude and float(longitude)
            return (location, (latitude, longitude))
            
        if exactly_one:
            return parse_point(points[0])
        else:
            return (parse_point(point) for point in points)


class VirtualEarth(WebGeocoder):
    """Geocoder using Microsoft's Windows Live Local web service, powered by
    Virtual Earth.
    
    WARNING: This does not use a published API and can easily break if
    Microsoft changes their JavaScript.
    """
    SINGLE_LOCATION = re.compile(r"AddLocation\((.*?')\)")
    AMBIGUOUS_LOCATION = re.compile(r"UpdateAmbiguousList\(\[(.*?)\]\)")
    AMBIGUOUS_SPLIT = re.compile(r"\s*,?\s*new Array\(")
    STRING_QUOTE = re.compile(r"(?<!\\)'")

    def __init__(self, domain='local.live.com', format_string='%s'):
        self.domain = domain
        self.format_string = format_string

    @property
    def url(self):
        domain = self.domain
        resource = "search.ashx"
        return "http://%(domain)s/%(resource)s?%%s" % locals()

    def geocode(self, string, exactly_one=True):
        params = {'b': self.format_string % string}
        url = self.url % urlencode(params)
        return self.geocode_url(url, exactly_one)

    def geocode_url(self, url, exactly_one=True):
        print "Fetching %s..." % url
        page = urlopen(url)
        return self.parse_javascript(page, exactly_one)

    def parse_javascript(self, page, exactly_one=True):
        if not isinstance(page, basestring):
            page = self._decode_page(page)

        matches = self.SINGLE_LOCATION.findall(page)
        if not matches:
            for match in self.AMBIGUOUS_LOCATION.findall(page):
                places = self.AMBIGUOUS_SPLIT.split(match)
                matches.extend([place for place in places if place])

        if exactly_one and len(matches) != 1:
            raise ValueError("Didn't find exactly one location! " \
                             "(Found %d.)" % len(matches))

        def parse_match(match):
            json = "[%s]" % self.STRING_QUOTE.sub('"', match.strip('()'))
            array = simplejson.loads(json)
            if len(array) == 8:
                location, (latitude, longitude) = array[0], array[5:7]
            else:
                location, latitude, longitude = array[:3]
                
            return (location, (latitude, longitude))

        if exactly_one:
            return parse_match(matches[0])
        else:
            return (parse_match(match) for match in matches)


class GeoNames(WebGeocoder):
    def __init__(self, format_string='%s', output_format='xml'):
        self.format_string = format_string
        self.output_format = output_format

    @property
    def url(self):
        domain = "ws.geonames.org"
        output_format = self.output_format.lower()
        append_formats = {'json': 'JSON'}
        resource = "postalCodeSearch" + append_formats.get(output_format, '')
        return "http://%(domain)s/%(resource)s?%%s" % locals()

    def geocode(self, string, exactly_one=True):
        params = {'placename': string}
        url = self.url % urlencode(params)
        return self.geocode_url(url, exactly_one)

    def geocode_url(self, url, exactly_one=True):
        page = urlopen(url)
        dispatch = getattr(self, 'parse_' + self.output_format)
        return dispatch(page, exactly_one)

    def parse_json(self, page, exactly_one):
        if not isinstance(page, basestring):
            page = self._decode_page(page)
        json = simplejson.loads(page)
        codes = json.get('postalCodes', [])
        
        if exactly_one and len(codes) != 1:
            raise ValueError("Didn't find exactly one code! " \
                             "(Found %d.)" % len(codes))
        
        def parse_code(code):
            place = self._join_filter(", ", [code.get('placeName'),
                                             code.get('countryCode')])
            location = self._join_filter(" ", [place,
                                               code.get('postalCode')]) or None
            latitude = code.get('lat')
            longitude = code.get('lng')
            latitude = latitude and float(latitude)
            longitude = longitude and float(longitude)
            return (location, (latitude, longitude))

        if exactly_one:
            return parse_code(codes[0])
        else:
            return (parse_code(code) for code in codes)

    def parse_xml(self, page, exactly_one):
        if not isinstance(page, basestring):
            page = self._decode_page(page)
        doc = xml.dom.minidom.parseString(page)
        codes = doc.getElementsByTagName('code')
        
        if exactly_one and len(codes) != 1:
            raise ValueError("Didn't find exactly one code! " \
                             "(Found %d.)" % len(codes))

        def parse_code(code):
            place_name = self._get_first_text(code, 'name')
            country_code = self._get_first_text(code, 'countryCode')
            postal_code = self._get_first_text(code, 'postalcode')
            place = self._join_filter(", ", [place_name, country_code])
            location = self._join_filter(" ", [place, postal_code]) or None
            latitude = self._get_first_text(code, 'lat') or None
            longitude = self._get_first_text(code, 'lng') or None
            latitude = latitude and float(latitude)
            longitude = longitude and float(longitude)
            return (location, (latitude, longitude))
        
        if exactly_one:
            return parse_code(codes[0])
        else:
            return (parse_code(code) for code in codes)


__all__ = ['Geocoder', 'MediaWiki', 'SemanticMediaWiki', 'Google', 'Yahoo',
           'GeocoderDotUS', 'VirtualEarth', 'GeoNames']
########NEW FILE########
__FILENAME__ = util
import re
import htmlentitydefs
from distance import arc_degrees

# Unicode characters for symbols that appear in coordinate strings:
DEGREE = unichr(htmlentitydefs.name2codepoint['deg'])
ARCMIN = unichr(htmlentitydefs.name2codepoint['prime'])
ARCSEC = unichr(htmlentitydefs.name2codepoint['Prime'])

def parse_geo(string, regex=None):
    """Return a 2-tuple of Decimals parsed from ``string``. The default
    regular expression can parse most common coordinate formats,
    including:
        41.5;-81.0
        41.5,-81.0
        41.5 -81.0
        41.5 N -81.0 W
        -41.5 S;81.0 E
        23 26m 22s N 23 27m 30s E
        23 26' 22" N 23 27' 30" E
    ...and more whitespace and separator variations. UTF-8 characters such
    as the degree symbol, prime (arcminutes), and double prime (arcseconds)
    are also supported. Coordinates given from South and West will be
    converted appropriately (by switching their signs).
    
    A custom expression can be given using the ``regex`` argument. It can
    be a string or compiled regular expression, and must contain groups
    named 'latitude_degrees' and 'longitude_degrees'. It can optionally
    contain groups named 'latitude_minutes', 'latitude_seconds',
    'longitude_minutes', 'longitude_seconds' for increased precision.
    Optional single-character groups named 'north_south' and 'east_west' may
    be included to indicate direction, it is assumed that the coordinates
    reference North and East otherwise.
    """
    string = string.strip()
    if regex is None:
        sep = r"(\s*[;,\s]\s*)"
        try:
            lat, _, lng = re.split(sep, string)
            return (float(lat), float(lng))
        except ValueError:
            coord = r"(?P<%%s_degrees>-?\d+\.?\d*)%s?" % DEGREE
            arcmin = r"((?P<%%s_minutes>\d+\.?\d*)[m'%s])?" % ARCMIN
            arcsec = r'((?P<%%s_seconds>\d+\.?\d*)[s"%s])?' % ARCSEC
            coord_lat = r"\s*".join([coord % 'latitude',
                                     arcmin % 'latitude',
                                     arcsec % 'latitude'])
            coord_lng = r"\s*".join([coord % 'longitude',
                                     arcmin % 'longitude',
                                     arcsec % 'longitude'])
            direction_lat = r"(?P<north_south>[NS])?"
            direction_lng = r"(?P<east_west>[EW])?"
            lat = r"\s*".join([coord_lat, direction_lat])
            lng = r"\s*".join([coord_lng, direction_lng])
            regex = sep.join([lat, lng])

    match = re.match(regex, string)
    if match:
        d = match.groupdict()
        lat = d.get('latitude_degrees')
        lng = d.get('longitude_degrees')
        if lat:
            lat = float(lat)
            lat += arc_degrees(d.get('latitude_minutes', 0),
                               d.get('latitude_seconds', 0))
            n_s = d.get('north_south', 'N').upper()
            if n_s == 'S':
                lat *= -1 
        if lng:
            lng = float(lng)
            lng += arc_degrees(d.get('longitude_minutes', 0),
                               d.get('longitude_seconds', 0))
            e_w = d.get('east_west', 'E').upper()
            if e_w == 'W':
                lng *= -1
        return (lat, lng)
    else:
        return (None, None)


########NEW FILE########
__FILENAME__ = association
"""
This module contains code for dealing with associations between
consumers and servers.
"""

import time

from openid import cryptutil
from openid import kvform
from openid import oidutil

class Association(object):
    """
    This class represents an association between a server and a
    consumer.  In general, users of this library will never see
    instances of this object.  The only exception is if you implement
    a custom C{L{OpenIDStore<openid.store.interface.OpenIDStore>}}.

    If you do implement such a store, it will need to store the values
    of the C{L{handle}}, C{L{secret}}, C{L{issued}}, C{L{lifetime}}, and
    C{L{assoc_type}} instance variables.

    @ivar handle: This is the handle the server gave this association.

    @type handle: C{str}


    @ivar secret: This is the shared secret the server generated for
        this association.

    @type secret: C{str}


    @ivar issued: This is the time this association was issued, in
        seconds since 00:00 GMT, January 1, 1970.  (ie, a unix
        timestamp)

    @type issued: C{int}


    @ivar lifetime: This is the amount of time this association is
        good for, measured in seconds since the association was
        issued.

    @type lifetime: C{int}


    @ivar assoc_type: This is the type of association this instance
        represents.  The only valid value of this field at this time
        is C{'HMAC-SHA1'}, but new types may be defined in the future.

    @type assoc_type: C{str}


    @sort: __init__, fromExpiresIn, getExpiresIn, __eq__, __ne__,
        handle, secret, issued, lifetime, assoc_type
    """

    # This is a HMAC-SHA1 specific value.
    SIG_LENGTH = 20

    # The ordering and name of keys as stored by serialize
    assoc_keys = [
        'version',
        'handle',
        'secret',
        'issued',
        'lifetime',
        'assoc_type',
        ]

    def fromExpiresIn(cls, expires_in, handle, secret, assoc_type):
        """
        This is an alternate constructor used by the OpenID consumer
        library to create associations.  C{L{OpenIDStore
        <openid.store.interface.OpenIDStore>}} implementations
        shouldn't use this constructor.


        @param expires_in: This is the amount of time this association
            is good for, measured in seconds since the association was
            issued.

        @type expires_in: C{int}


        @param handle: This is the handle the server gave this
            association.

        @type handle: C{str}


        @param secret: This is the shared secret the server generated
            for this association.

        @type secret: C{str}


        @param assoc_type: This is the type of association this
            instance represents.  The only valid value of this field
            at this time is C{'HMAC-SHA1'}, but new types may be
            defined in the future.

        @type assoc_type: C{str}
        """
        issued = int(time.time())
        lifetime = expires_in
        return cls(handle, secret, issued, lifetime, assoc_type)

    fromExpiresIn = classmethod(fromExpiresIn)

    def __init__(self, handle, secret, issued, lifetime, assoc_type):
        """
        This is the standard constructor for creating an association.


        @param handle: This is the handle the server gave this
            association.

        @type handle: C{str}


        @param secret: This is the shared secret the server generated
            for this association.

        @type secret: C{str}


        @param issued: This is the time this association was issued,
            in seconds since 00:00 GMT, January 1, 1970.  (ie, a unix
            timestamp)

        @type issued: C{int}


        @param lifetime: This is the amount of time this association
            is good for, measured in seconds since the association was
            issued.

        @type lifetime: C{int}


        @param assoc_type: This is the type of association this
            instance represents.  The only valid value of this field
            at this time is C{'HMAC-SHA1'}, but new types may be
            defined in the future.

        @type assoc_type: C{str}
        """
        if assoc_type != 'HMAC-SHA1':
            fmt = 'HMAC-SHA1 is the only supported association type (got %r)'
            raise ValueError(fmt % (assoc_type,))

        self.handle = handle
        self.secret = secret
        self.issued = issued
        self.lifetime = lifetime
        self.assoc_type = assoc_type

    def getExpiresIn(self, now=None):
        """
        This returns the number of seconds this association is still
        valid for, or C{0} if the association is no longer valid.


        @return: The number of seconds this association is still valid
            for, or C{0} if the association is no longer valid.

        @rtype: C{int}
        """
        if now is None:
            now = int(time.time())

        return max(0, self.issued + self.lifetime - now)

    expiresIn = property(getExpiresIn)

    def __eq__(self, other):
        """
        This checks to see if two C{L{Association}} instances
        represent the same association.


        @return: C{True} if the two instances represent the same
            association, C{False} otherwise.

        @rtype: C{bool}
        """
        return type(self) is type(other) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        """
        This checks to see if two C{L{Association}} instances
        represent different associations.


        @return: C{True} if the two instances represent different
            associations, C{False} otherwise.

        @rtype: C{bool}
        """
        return not (self == other)

    def serialize(self):
        """
        Convert an association to KV form.

        @return: String in KV form suitable for deserialization by
            deserialize.

        @rtype: str
        """
        data = {
            'version':'2',
            'handle':self.handle,
            'secret':oidutil.toBase64(self.secret),
            'issued':str(int(self.issued)),
            'lifetime':str(int(self.lifetime)),
            'assoc_type':self.assoc_type
            }

        assert len(data) == len(self.assoc_keys)
        pairs = []
        for field_name in self.assoc_keys:
            pairs.append((field_name, data[field_name]))

        return kvform.seqToKV(pairs, strict=True)

    def deserialize(cls, assoc_s):
        """
        Parse an association as stored by serialize().

        inverse of serialize


        @param assoc_s: Association as serialized by serialize()

        @type assoc_s: str


        @return: instance of this class
        """
        pairs = kvform.kvToSeq(assoc_s, strict=True)
        keys = []
        values = []
        for k, v in pairs:
            keys.append(k)
            values.append(v)

        if keys != cls.assoc_keys:
            raise ValueError('Unexpected key values: %r', keys)

        version, handle, secret, issued, lifetime, assoc_type = values
        if version != '2':
            raise ValueError('Unknown version: %r' % version)
        issued = int(issued)
        lifetime = int(lifetime)
        secret = oidutil.fromBase64(secret)
        return cls(handle, secret, issued, lifetime, assoc_type)

    deserialize = classmethod(deserialize)

    def sign(self, pairs):
        """
        Generate a signature for a sequence of (key, value) pairs


        @param pairs: The pairs to sign, in order

        @type pairs: sequence of (str, str)


        @return: The binary signature of this sequence of pairs

        @rtype: str
        """
        assert self.assoc_type == 'HMAC-SHA1'
        kv = kvform.seqToKV(pairs)
        return cryptutil.hmacSha1(self.secret, kv)

    def signDict(self, fields, data, prefix='openid.'):
        """
        Generate a signature for some fields in a dictionary


        @param fields: The fields to sign, in order

        @type fields: sequence of str


        @param data: Dictionary of values to sign

        @type data: {str:str}


        @return: the signature, base64 encoded

        @rtype: str
        """
        pairs = []
        for field in fields:
            pairs.append((field, data.get(prefix + field, '')))

        return oidutil.toBase64(self.sign(pairs))

    def addSignature(self, fields, data, prefix='openid.'):
        sig = self.signDict(fields, data, prefix)
        signed = ','.join(fields)
        data[prefix + 'sig'] = sig
        data[prefix + 'signed'] = signed

    def checkSignature(self, data, prefix='openid.'):
        try:
            signed = data[prefix + 'signed']
            fields = signed.split(',')
            expected_sig = self.signDict(fields, data, prefix)
            request_sig = data[prefix + 'sig']
        except KeyError:
            return False

        return request_sig == expected_sig

########NEW FILE########
__FILENAME__ = consumer
# -*- test-case-name: openid.test.consumer -*-
"""
This module documents the main interface with the OpenID consumer
library.  The only part of the library which has to be used and isn't
documented in full here is the store required to create an
C{L{Consumer}} instance.  More on the abstract store type and
concrete implementations of it that are provided in the documentation
for the C{L{__init__<Consumer.__init__>}} method of the
C{L{Consumer}} class.


OVERVIEW
========

    The OpenID identity verification process most commonly uses the
    following steps, as visible to the user of this library:

        1. The user enters their OpenID into a field on the consumer's
           site, and hits a login button.

        2. The consumer site discovers the user's OpenID server using
           the YADIS protocol.

        3. The consumer site sends the browser a redirect to the
           identity server.  This is the authentication request as
           described in the OpenID specification.

        4. The identity server's site sends the browser a redirect
           back to the consumer site.  This redirect contains the
           server's response to the authentication request.

    The most important part of the flow to note is the consumer's site
    must handle two separate HTTP requests in order to perform the
    full identity check.


LIBRARY DESIGN
==============

    This consumer library is designed with that flow in mind.  The
    goal is to make it as easy as possible to perform the above steps
    securely.

    At a high level, there are two important parts in the consumer
    library.  The first important part is this module, which contains
    the interface to actually use this library.  The second is the
    C{L{openid.store.interface}} module, which describes the
    interface to use if you need to create a custom method for storing
    the state this library needs to maintain between requests.

    In general, the second part is less important for users of the
    library to know about, as several implementations are provided
    which cover a wide variety of situations in which consumers may
    use the library.

    This module contains a class, C{L{Consumer}}, with methods
    corresponding to the actions necessary in each of steps 2, 3, and
    4 described in the overview.  Use of this library should be as easy
    as creating an C{L{Consumer}} instance and calling the methods
    appropriate for the action the site wants to take.


STORES AND DUMB MODE
====================

    OpenID is a protocol that works best when the consumer site is
    able to store some state.  This is the normal mode of operation
    for the protocol, and is sometimes referred to as smart mode.
    There is also a fallback mode, known as dumb mode, which is
    available when the consumer site is not able to store state.  This
    mode should be avoided when possible, as it leaves the
    implementation more vulnerable to replay attacks.

    The mode the library works in for normal operation is determined
    by the store that it is given.  The store is an abstraction that
    handles the data that the consumer needs to manage between http
    requests in order to operate efficiently and securely.

    Several store implementation are provided, and the interface is
    fully documented so that custom stores can be used as well.  See
    the documentation for the C{L{Consumer}} class for more
    information on the interface for stores.  The implementations that
    are provided allow the consumer site to store the necessary data
    in several different ways, including several SQL databases and
    normal files on disk.

    There is an additional concrete store provided that puts the
    system in dumb mode.  This is not recommended, as it removes the
    library's ability to stop replay attacks reliably.  It still uses
    time-based checking to make replay attacks only possible within a
    small window, but they remain possible within that window.  This
    store should only be used if the consumer site has no way to
    retain data between requests at all.


IMMEDIATE MODE
==============

    In the flow described above, the user may need to confirm to the
    identity server that it's ok to authorize his or her identity.
    The server may draw pages asking for information from the user
    before it redirects the browser back to the consumer's site.  This
    is generally transparent to the consumer site, so it is typically
    ignored as an implementation detail.

    There can be times, however, where the consumer site wants to get
    a response immediately.  When this is the case, the consumer can
    put the library in immediate mode.  In immediate mode, there is an
    extra response possible from the server, which is essentially the
    server reporting that it doesn't have enough information to answer
    the question yet.  In addition to saying that, the identity server
    provides a URL to which the user can be sent to provide the needed
    information and let the server finish handling the original
    request.


USING THIS LIBRARY
==================

    Integrating this library into an application is usually a
    relatively straightforward process.  The process should basically
    follow this plan:

    Add an OpenID login field somewhere on your site.  When an OpenID
    is entered in that field and the form is submitted, it should make
    a request to the your site which includes that OpenID URL.

    First, the application should instantiate the C{L{Consumer}} class
    using the store of choice.  If the application has any sort of
    session framework that provides per-client state management, a
    dict-like object to access the session should be passed as the
    optional second parameter.  The library just expects the session
    object to support a C{dict}-like interface, if it is provided.

    Next, the application should call the 'begin' method on the
    C{L{Consumer}} instance.  This method takes the OpenID URL.  The
    C{L{begin<Consumer.begin>}} method returns an C{L{AuthRequest}}
    object.

    Next, the application should call the
    C{L{redirectURL<AuthRequest.redirectURL>}} method on the
    C{L{AuthRequest}} object.  The parameter C{return_to} is the URL
    that the OpenID server will send the user back to after attempting
    to verify his or her identity.  The C{trust_root} parameter is the
    URL (or URL pattern) that identifies your web site to the user
    when he or she is authorizing it.  Send a redirect to the
    resulting URL to the user's browser.

    That's the first half of the authentication process.  The second
    half of the process is done after the user's ID server sends the
    user's browser a redirect back to your site to complete their
    login.

    When that happens, the user will contact your site at the URL
    given as the C{return_to} URL to the
    C{L{redirectURL<AuthRequest.redirectURL>}} call made
    above.  The request will have several query parameters added to
    the URL by the identity server as the information necessary to
    finish the request.

    Get an C{L{Consumer}} instance, and call its
    C{L{complete<Consumer.complete>}} method, passing in all the
    received query arguments.

    There are multiple possible return types possible from that
    method. These indicate the whether or not the login was
    successful, and include any additional information appropriate for
    their type.

@var SUCCESS: constant used as the status for
    L{SuccessResponse<openid.consumer.consumer.SuccessResponse>} objects.

@var FAILURE: constant used as the status for
    L{FailureResponse<openid.consumer.consumer.FailureResponse>} objects.

@var CANCEL: constant used as the status for
    L{CancelResponse<openid.consumer.consumer.CancelResponse>} objects.

@var SETUP_NEEDED: constant used as the status for
    L{SetupNeededResponse<openid.consumer.consumer.SetupNeededResponse>}
    objects.
"""

import string
import time
import urllib
import cgi
from urlparse import urlparse

from urljr import fetchers

from openid.consumer.discover import discover as openIDDiscover
from openid.consumer.discover import discoverXRI
from openid.consumer.discover import yadis_available, DiscoveryFailure
from openid import cryptutil
from openid import kvform
from openid import oidutil
from openid.association import Association
from openid.dh import DiffieHellman

__all__ = ['AuthRequest', 'Consumer', 'SuccessResponse',
           'SetupNeededResponse', 'CancelResponse', 'FailureResponse',
           'SUCCESS', 'FAILURE', 'CANCEL', 'SETUP_NEEDED',
           ]

if yadis_available:
    from yadis.manager import Discovery
    from yadis import xri

class Consumer(object):
    """An OpenID consumer implementation that performs discovery and
    does session management.

    @ivar consumer: an instance of an object implementing the OpenID
        protocol, but doing no discovery or session management.

    @type consumer: GenericConsumer

    @ivar session: A dictionary-like object representing the user's
        session data.  This is used for keeping state of the OpenID
        transaction when the user is redirected to the server.

    @cvar session_key_prefix: A string that is prepended to session
        keys to ensure that they are unique. This variable may be
        changed to suit your application.
    """
    session_key_prefix = "_openid_consumer_"

    _token = 'last_token'

    def __init__(self, session, store):
        """Initialize a Consumer instance.

        You should create a new instance of the Consumer object with
        every HTTP request that handles OpenID transactions.

        @param session: See L{the session instance variable<openid.consumer.consumer.Consumer.session>}

        @param store: an object that implements the interface in
            C{L{openid.store.interface.OpenIDStore}}.  Several
            implementations are provided, to cover common database
            environments.

        @type store: C{L{openid.store.interface.OpenIDStore}}

        @see: L{openid.store.interface}
        @see: L{openid.store}
        """
        self.session = session
        self.consumer = GenericConsumer(store)
        self._token_key = self.session_key_prefix + self._token

    def begin(self, user_url):
        """Start the OpenID authentication process. See steps 1-2 in
        the overview at the top of this file.

        @param user_url: Identity URL given by the user. This method
            performs a textual transformation of the URL to try and
            make sure it is normalized. For example, a user_url of
            example.com will be normalized to http://example.com/
            normalizing and resolving any redirects the server might
            issue.

        @type user_url: str

        @returns: An object containing the discovered information will
            be returned, with a method for building a redirect URL to
            the server, as described in step 3 of the overview. This
            object may also be used to add extension arguments to the
            request, using its
            L{addExtensionArg<openid.consumer.consumer.AuthRequest.addExtensionArg>}
            method.

        @returntype: L{AuthRequest<openid.consumer.consumer.AuthRequest>}

        @raises openid.consumer.discover.DiscoveryFailure: when I fail to
            find an OpenID server for this URL.  If the C{yadis} package
            is available, L{openid.consumer.discover.DiscoveryFailure} is
            an alias for C{yadis.discover.DiscoveryFailure}.
        """
        if yadis_available and xri.identifierScheme(user_url) == "XRI":
            discoverMethod = discoverXRI
            openid_url = user_url
        else:
            discoverMethod = openIDDiscover
            openid_url = oidutil.normalizeUrl(user_url)

        if yadis_available:
            try:
                disco = Discovery(self.session,
                                  openid_url,
                                  self.session_key_prefix)
                service = disco.getNextService(discoverMethod)
            except fetchers.HTTPFetchingError, e:
                raise DiscoveryFailure('Error fetching XRDS document', e)
        else:
            # XXX - Untested branch!
            _, services = openIDDiscover(user_url)
            if not services:
                service = None
            else:
                service = services[0]

        if service is None:
            raise DiscoveryFailure(
                'No usable OpenID services found for %s' % (openid_url,), None)
        else:
            return self.beginWithoutDiscovery(service)

    def beginWithoutDiscovery(self, service):
        """Start OpenID verification without doing OpenID server
        discovery. This method is used internally by Consumer.begin
        after discovery is performed, and exists to provide an
        interface for library users needing to perform their own
        discovery.

        @param service: an OpenID service endpoint descriptor.  This
            object and factories for it are found in the
            L{openid.consumer.discover} module.

        @type service:
            L{OpenIDServiceEndpoint<openid.consumer.discover.OpenIDServiceEndpoint>}

        @returns: an OpenID authentication request object.

        @rtype: L{AuthRequest<openid.consumer.consumer.AuthRequest>}

        @See: Openid.consumer.consumer.Consumer.begin
        @see: openid.consumer.discover
        """
        auth_req = self.consumer.begin(service)
        self.session[self._token_key] = auth_req.endpoint
        return auth_req

    def complete(self, query):
        """Called to interpret the server's response to an OpenID
        request. It is called in step 4 of the flow described in the
        consumer overview.

        @param query: A dictionary of the query parameters for this
            HTTP request.

        @returns: a subclass of Response. The type of response is
            indicated by the status attribute, which will be one of
            SUCCESS, CANCEL, FAILURE, or SETUP_NEEDED.

        @see: L{SuccessResponse<openid.consumer.consumer.SuccessResponse>}
        @see: L{CancelResponse<openid.consumer.consumer.CancelResponse>}
        @see: L{SetupNeededResponse<openid.consumer.consumer.SetupNeededResponse>}
        @see: L{FailureResponse<openid.consumer.consumer.FailureResponse>}
        """

        endpoint = self.session.get(self._token_key)
        if endpoint is None:
            response = FailureResponse(None, 'No session state found')
        else:
            response = self.consumer.complete(query, endpoint)
            del self.session[self._token_key]

        if (response.status in ['success', 'cancel'] and
            yadis_available and
            response.identity_url is not None):

            disco = Discovery(self.session,
                              response.identity_url,
                              self.session_key_prefix)
            # This is OK to do even if we did not do discovery in
            # the first place.
            disco.cleanup()

        return response

class DiffieHellmanConsumerSession(object):
    session_type = 'DH-SHA1'

    def __init__(self, dh=None):
        if dh is None:
            dh = DiffieHellman.fromDefaults()

        self.dh = dh

    def getRequest(self):
        cpub = cryptutil.longToBase64(self.dh.public)

        args = {'openid.dh_consumer_public': cpub}

        if not self.dh.usingDefaultValues():
            args.update({
                'openid.dh_modulus': cryptutil.longToBase64(self.dh.modulus),
                'openid.dh_gen': cryptutil.longToBase64(self.dh.generator),
                })

        return args

    def extractSecret(self, response):
        spub = cryptutil.base64ToLong(response['dh_server_public'])
        enc_mac_key = oidutil.fromBase64(response['enc_mac_key'])
        return self.dh.xorSecret(spub, enc_mac_key)

class PlainTextConsumerSession(object):
    session_type = None

    def getRequest(self):
        return {}

    def extractSecret(self, response):
        return oidutil.fromBase64(response['mac_key'])

class GenericConsumer(object):
    """This is the implementation of the common logic for OpenID
    consumers. It is unaware of the application in which it is
    running.
    """

    NONCE_LEN = 8
    NONCE_CHRS = string.ascii_letters + string.digits

    def __init__(self, store):
        self.store = store

    def begin(self, service_endpoint):
        nonce = self._createNonce()
        assoc = self._getAssociation(service_endpoint.server_url)
        request = AuthRequest(service_endpoint, assoc)
        request.return_to_args['nonce'] = nonce
        return request

    def complete(self, query, endpoint):
        mode = query.get('openid.mode', '<no mode specified>')

        if isinstance(mode, list):
            raise TypeError("query dict must have one value for each key, "
                            "not lists of values.  Query is %r" % (query,))

        if mode == 'cancel':
            return CancelResponse(endpoint)
        elif mode == 'error':
            error = query.get('openid.error')
            return FailureResponse(endpoint, error)
        elif mode == 'id_res':
            if endpoint.identity_url is None:
                return FailureResponse(endpoint, 'No session state found')
            try:
                response = self._doIdRes(query, endpoint)
            except fetchers.HTTPFetchingError, why:
                message = 'HTTP request failed: %s' % (str(why),)
                return FailureResponse(endpoint, message)
            else:
                if response.status == 'success':
                    return self._checkNonce(response, query.get('nonce'))
                else:
                    return response
        else:
            return FailureResponse(endpoint,
                                   'Invalid openid.mode: %r' % (mode,))

    def _checkNonce(self, response, nonce):
        parsed_url = urlparse(response.getReturnTo())
        query = parsed_url[4]
        for k, v in cgi.parse_qsl(query):
            if k == 'nonce':
                if v != nonce:
                    return FailureResponse(response, 'Nonce mismatch')
                else:
                    break
        else:
            return FailureResponse(response, 'Nonce missing from return_to: %r'
                                   % (response.getReturnTo()))

        # The nonce matches the signed nonce in the openid.return_to
        # response parameter
        if not self.store.useNonce(nonce):
            return FailureResponse(response,
                                   'Nonce missing from store')

        # If the nonce check succeeded, return the original success
        # response
        return response

    def _createNonce(self):
        nonce = cryptutil.randomString(self.NONCE_LEN, self.NONCE_CHRS)
        self.store.storeNonce(nonce)
        return nonce

    def _makeKVPost(self, args, server_url):
        mode = args['openid.mode']
        body = urllib.urlencode(args)

        resp = fetchers.fetch(server_url, body=body)
        if resp is None:
            fmt = 'openid.mode=%s: failed to fetch URL: %s'
            oidutil.log(fmt % (mode, server_url))
            return None

        response = kvform.kvToDict(resp.body)
        if resp.status == 400:
            server_error = response.get('error', '<no message from server>')
            fmt = 'openid.mode=%s: error returned from server %s: %s'
            oidutil.log(fmt % (mode, server_url, server_error))
            return None
        elif resp.status != 200:
            fmt = 'openid.mode=%s: bad status code from server %s: %s'
            oidutil.log(fmt % (mode, server_url, resp.status))
            return None

        return response

    def _doIdRes(self, query, endpoint):
        """Handle id_res responses.

        @param query: the response paramaters.
        @param consumer_id: The normalized Claimed Identifier.
        @param server_id: The Delegate Identifier.
        @param server_url: OpenID server endpoint URL.

        @returntype: L{Response}
        """
        user_setup_url = query.get('openid.user_setup_url')
        if user_setup_url is not None:
            return SetupNeededResponse(endpoint, user_setup_url)

        return_to = query.get('openid.return_to')
        server_id2 = query.get('openid.identity')
        assoc_handle = query.get('openid.assoc_handle')

        if return_to is None or server_id2 is None or assoc_handle is None:
            return FailureResponse(endpoint, 'Missing required field')

        if endpoint.getServerID() != server_id2:
            return FailureResponse(endpoint, 'Server ID (delegate) mismatch')

        signed = query.get('openid.signed')

        assoc = self.store.getAssociation(endpoint.server_url, assoc_handle)

        if assoc is None:
            # It's not an association we know about.  Dumb mode is our
            # only possible path for recovery.
            if self._checkAuth(query, endpoint.server_url):
                return SuccessResponse.fromQuery(endpoint, query, signed)
            else:
                return FailureResponse(endpoint,
                                       'Server denied check_authentication')

        if assoc.expiresIn <= 0:
            # XXX: It might be a good idea sometimes to re-start the
            # authentication with a new association. Doing it
            # automatically opens the possibility for
            # denial-of-service by a server that just returns expired
            # associations (or really short-lived associations)
            msg = 'Association with %s expired' % (endpoint.server_url,)
            return FailureResponse(endpoint, msg)

        # Check the signature
        sig = query.get('openid.sig')
        if sig is None or signed is None:
            return FailureResponse(endpoint, 'Missing argument signature')

        signed_list = signed.split(',')

        # Fail if the identity field is present but not signed
        if endpoint.identity_url is not None and 'identity' not in signed_list:
            msg = '"openid.identity" not signed'
            return FailureResponse(endpoint, msg)

        v_sig = assoc.signDict(signed_list, query)

        if v_sig != sig:
            return FailureResponse(endpoint, 'Bad signature')

        return SuccessResponse.fromQuery(endpoint, query, signed)

    def _checkAuth(self, query, server_url):
        request = self._createCheckAuthRequest(query)
        if request is None:
            return False
        response = self._makeKVPost(request, server_url)
        if response is None:
            return False
        return self._processCheckAuthResponse(response, server_url)

    def _createCheckAuthRequest(self, query):
        signed = query.get('openid.signed')
        if signed is None:
            oidutil.log('No signature present; checkAuth aborted')
            return None

        # Arguments that are always passed to the server and not
        # included in the signature.
        whitelist = ['assoc_handle', 'sig', 'signed', 'invalidate_handle']
        signed = signed.split(',') + whitelist

        check_args = dict([(k, v) for k, v in query.iteritems()
                           if k.startswith('openid.') and k[7:] in signed])

        check_args['openid.mode'] = 'check_authentication'
        return check_args

    def _processCheckAuthResponse(self, response, server_url):
        is_valid = response.get('is_valid', 'false')

        invalidate_handle = response.get('invalidate_handle')
        if invalidate_handle is not None:
            self.store.removeAssociation(server_url, invalidate_handle)

        if is_valid == 'true':
            return True
        else:
            oidutil.log('Server responds that checkAuth call is not valid')
            return False

    def _getAssociation(self, server_url):
        if self.store.isDumb():
            return None

        assoc = self.store.getAssociation(server_url)

        if assoc is None or assoc.expiresIn <= 0:
            assoc_session, args = self._createAssociateRequest(server_url)
            try:
                response = self._makeKVPost(args, server_url)
            except fetchers.HTTPFetchingError, why:
                oidutil.log('openid.associate request failed: %s' %
                            (str(why),))
                assoc = None
            else:
                assoc = self._parseAssociation(
                    response, assoc_session, server_url)

        return assoc

    def _createAssociateRequest(self, server_url):
        proto = urlparse(server_url)[0]
        if proto == 'https':
            session_type = PlainTextConsumerSession
        else:
            session_type = DiffieHellmanConsumerSession

        assoc_session = session_type()

        args = {
            'openid.mode': 'associate',
            'openid.assoc_type':'HMAC-SHA1',
            }

        if assoc_session.session_type is not None:
            args['openid.session_type'] = assoc_session.session_type

        args.update(assoc_session.getRequest())
        return assoc_session, args

    def _parseAssociation(self, results, assoc_session, server_url):
        try:
            assoc_type = results['assoc_type']
            assoc_handle = results['assoc_handle']
            expires_in_str = results['expires_in']
        except KeyError, e:
            fmt = 'Getting association: missing key in response from %s: %s'
            oidutil.log(fmt % (server_url, e[0]))
            return None

        if assoc_type != 'HMAC-SHA1':
            fmt = 'Unsupported assoc_type returned from server %s: %s'
            oidutil.log(fmt % (server_url, assoc_type))
            return None

        try:
            expires_in = int(expires_in_str)
        except ValueError, e:
            fmt = 'Getting Association: invalid expires_in field: %s'
            oidutil.log(fmt % (e[0],))
            return None

        session_type = results.get('session_type')
        if session_type != assoc_session.session_type:
            if session_type is None:
                oidutil.log('Falling back to plain text association '
                            'session from %s' % assoc_session.session_type)
                assoc_session = PlainTextConsumerSession()
            else:
                oidutil.log('Session type mismatch. Expected %r, got %r' %
                            (assoc_session.session_type, session_type))
                return None

        try:
            secret = assoc_session.extractSecret(results)
        except ValueError, why:
            oidutil.log('Malformed response for %s session: %s' % (
                assoc_session.session_type, why[0]))
            return None
        except KeyError, why:
            fmt = 'Getting association: missing key in response from %s: %s'
            oidutil.log(fmt % (server_url, why[0]))
            return None

        assoc = Association.fromExpiresIn(
            expires_in, assoc_handle, secret, assoc_type)
        self.store.storeAssociation(server_url, assoc)

        return assoc

class AuthRequest(object):
    def __init__(self, endpoint, assoc):
        """
        Creates a new AuthRequest object.  This just stores each
        argument in an appropriately named field.

        Users of this library should not create instances of this
        class.  Instances of this class are created by the library
        when needed.
        """
        self.assoc = assoc
        self.endpoint = endpoint
        self.extra_args = {}
        self.return_to_args = {}

    def addExtensionArg(self, namespace, key, value):
        """Add an extension argument to this OpenID authentication
        request.

        Use caution when adding arguments, because they will be
        URL-escaped and appended to the redirect URL, which can easily
        get quite long.

        @param namespace: The namespace for the extension. For
            example, the simple registration extension uses the
            namespace C{sreg}.

        @type namespace: str

        @param key: The key within the extension namespace. For
            example, the nickname field in the simple registration
            extension's key is C{nickname}.

        @type key: str

        @param value: The value to provide to the server for this
            argument.

        @type value: str
        """
        arg_name = '.'.join(['openid', namespace, key])
        self.extra_args[arg_name] = value

    def redirectURL(self, trust_root, return_to, immediate=False):
        if immediate:
            mode = 'checkid_immediate'
        else:
            mode = 'checkid_setup'

        return_to = oidutil.appendArgs(return_to, self.return_to_args)

        redir_args = {
            'openid.mode': mode,
            'openid.identity': self.endpoint.getServerID(),
            'openid.return_to': return_to,
            'openid.trust_root': trust_root,
            }

        if self.assoc:
            redir_args['openid.assoc_handle'] = self.assoc.handle

        redir_args.update(self.extra_args)
        return oidutil.appendArgs(self.endpoint.server_url, redir_args)

FAILURE = 'failure'
SUCCESS = 'success'
CANCEL = 'cancel'
SETUP_NEEDED = 'setup_needed'

class Response(object):
    status = None

class SuccessResponse(Response):
    """A response with a status of SUCCESS. Indicates that this request is a
    successful acknowledgement from the OpenID server that the
    supplied URL is, indeed controlled by the requesting agent.

    @ivar identity_url: The identity URL that has been authenticated

    @ivar endpoint: The endpoint that authenticated the identifier.  You
        may access other discovered information related to this endpoint,
        such as the CanonicalID of an XRI, through this object.
    @type endpoint: L{OpenIDServiceEndpoint<openid.consumer.discover.OpenIDServiceEndpoint>}

    @ivar signed_args: The arguments in the server's response that
        were signed and verified.

    @cvar status: SUCCESS
    """

    status = SUCCESS

    def __init__(self, endpoint, signed_args):
        self.endpoint = endpoint
        self.identity_url = endpoint.identity_url
        self.signed_args = signed_args

    def fromQuery(cls, endpoint, query, signed):
        signed_args = {}
        for field_name in signed.split(','):
            field_name = 'openid.' + field_name
            signed_args[field_name] = query.get(field_name, '')
        return cls(endpoint, signed_args)

    fromQuery = classmethod(fromQuery)

    def extensionResponse(self, prefix):
        """extract signed extension data from the server's response.

        @param prefix: The extension namespace from which to extract
            the extension data.
        """
        response = {}
        prefix = 'openid.%s.' % (prefix,)
        prefix_len = len(prefix)
        for k, v in self.signed_args.iteritems():
            if k.startswith(prefix):
                response_key = k[prefix_len:]
                response[response_key] = v

        return response

    def getReturnTo(self):
        """Get the openid.return_to argument from this response.

        This is useful for verifying that this request was initiated
        by this consumer.

        @returns: The return_to URL supplied to the server on the
            initial request, or C{None} if the response did not contain
            an C{openid.return_to} argument.

        @returntype: str
        """
        return self.signed_args.get('openid.return_to', None)



class FailureResponse(Response):
    """A response with a status of FAILURE. Indicates that the OpenID
    protocol has failed. This could be locally or remotely triggered.

    @ivar identity_url:  The identity URL for which authenitcation was
        attempted, if it can be determined. Otherwise, None.

    @ivar message: A message indicating why the request failed, if one
        is supplied. otherwise, None.

    @cvar status: FAILURE
    """

    status = FAILURE

    def __init__(self, endpoint, message=None):
        self.endpoint = endpoint
        if endpoint is not None:
            self.identity_url = endpoint.identity_url
        else:
            self.identity_url = None
        self.message = message


    def __repr__(self):
        return "<%s.%s id=%r message=%r>" % (
            self.__class__.__module__, self.__class__.__name__,
            self.identity_url, self.message)


class CancelResponse(Response):
    """A response with a status of CANCEL. Indicates that the user
    cancelled the OpenID authentication request.

    @ivar identity_url: The identity URL for which authenitcation was
        attempted, if it can be determined. Otherwise, None.

    @cvar status: CANCEL
    """

    status = CANCEL

    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.identity_url = endpoint.identity_url

class SetupNeededResponse(Response):
    """A response with a status of SETUP_NEEDED. Indicates that the
    request was in immediate mode, and the server is unable to
    authenticate the user without further interaction.

    @ivar identity_url:  The identity URL for which authenitcation was
        attempted.

    @ivar setup_url: A URL that can be used to send the user to the
        server to set up for authentication. The user should be
        redirected in to the setup_url, either in the current window
        or in a new browser window.

    @cvar status: SETUP_NEEDED
    """

    status = SETUP_NEEDED

    def __init__(self, endpoint, setup_url=None):
        self.endpoint = endpoint
        self.identity_url = endpoint.identity_url
        self.setup_url = setup_url

########NEW FILE########
__FILENAME__ = discover
# -*- test-case-name: openid.test.test_discover -*-

from urljr import fetchers

from openid import oidutil

# If the Yadis library is available, use it. Otherwise, only use
# old-style discovery.
try:
    import yadis
except ImportError:
    yadis_available = False

    oidutil.log('Consumer operating without Yadis support '
                '(failed to import Yadis library)')

    class DiscoveryFailure(RuntimeError):
        """A failure to discover an OpenID server.

        When the C{yadis} package is available, this is
        C{yadis.discover.DiscoveryFailure}."""
else:
    yadis_available = True
    from yadis.etxrd import nsTag, XRDSError
    from yadis.services import applyFilter as extractServices
    from yadis.discover import discover as yadisDiscover
    from yadis.discover import DiscoveryFailure
    from yadis import xrires, filters

from openid.consumer.parse import openIDDiscover as parseOpenIDLinkRel
from openid.consumer.parse import ParseError

OPENID_1_0_NS = 'http://openid.net/xmlns/1.0'
OPENID_1_2_TYPE = 'http://openid.net/signon/1.2'
OPENID_1_1_TYPE = 'http://openid.net/signon/1.1'
OPENID_1_0_TYPE = 'http://openid.net/signon/1.0'

class OpenIDServiceEndpoint(object):
    """Object representing an OpenID service endpoint.

    @ivar identity_url: the verified identifier.
    @ivar canonicalID: For XRI, the persistent identifier.
    """
    openid_type_uris = [
        OPENID_1_2_TYPE,
        OPENID_1_1_TYPE,
        OPENID_1_0_TYPE,
        ]

    def __init__(self):
        self.identity_url = None
        self.server_url = None
        self.type_uris = []
        self.delegate = None
        self.canonicalID = None
        self.used_yadis = False # whether this came from an XRDS

    def usesExtension(self, extension_uri):
        return extension_uri in self.type_uris

    def parseService(self, yadis_url, uri, type_uris, service_element):
        """Set the state of this object based on the contents of the
        service element."""
        self.type_uris = type_uris
        self.identity_url = yadis_url
        self.server_url = uri
        self.delegate = findDelegate(service_element)
        self.used_yadis = True

    def getServerID(self):
        """Return the identifier that should be sent as the
        openid.identity_url parameter to the server."""
        if self.delegate is None:
            return self.canonicalID or self.identity_url
        else:
            return self.delegate

    def fromBasicServiceEndpoint(cls, endpoint):
        """Create a new instance of this class from the endpoint
        object passed in.

        @return: None or OpenIDServiceEndpoint for this endpoint object"""
        type_uris = endpoint.matchTypes(cls.openid_type_uris)

        # If any Type URIs match and there is an endpoint URI
        # specified, then this is an OpenID endpoint
        if type_uris and endpoint.uri is not None:
            openid_endpoint = cls()
            openid_endpoint.parseService(
                endpoint.yadis_url,
                endpoint.uri,
                endpoint.type_uris,
                endpoint.service_element)
        else:
            openid_endpoint = None

        return openid_endpoint

    fromBasicServiceEndpoint = classmethod(fromBasicServiceEndpoint)

    def fromHTML(cls, uri, html):
        """Parse the given document as HTML looking for an OpenID <link
        rel=...>

        @raises: openid.consumer.parse.ParseError
        """
        delegate_url, server_url = parseOpenIDLinkRel(html)
        service = cls()
        service.identity_url = uri
        service.delegate = delegate_url
        service.server_url = server_url
        service.type_uris = [OPENID_1_0_TYPE]
        return service

    fromHTML = classmethod(fromHTML)

def findDelegate(service_element):
    """Extract a openid:Delegate value from a Yadis Service element
    represented as an ElementTree Element object. If no delegate is
    found, returns None."""
    # XXX: should this die if there is more than one delegate element?
    delegate_tag = nsTag(OPENID_1_0_NS, 'Delegate')

    delegates = service_element.findall(delegate_tag)
    for delegate_element in delegates:
        delegate = delegate_element.text
        break
    else:
        delegate = None

    return delegate

def discoverYadis(uri):
    """Discover OpenID services for a URI. Tries Yadis and falls back
    on old-style <link rel='...'> discovery if Yadis fails.

    @param uri: normalized identity URL
    @type uri: str

    @return: (identity_url, services)
    @rtype: (str, list(OpenIDServiceEndpoint))

    @raises: DiscoveryFailure
    """
    # Might raise a yadis.discover.DiscoveryFailure if no document
    # came back for that URI at all.  I don't think falling back
    # to OpenID 1.0 discovery on the same URL will help, so don't
    # bother to catch it.
    response = yadisDiscover(uri)

    identity_url = response.normalized_uri
    try:
        openid_services = extractServices(
            response.normalized_uri, response.response_text,
            OpenIDServiceEndpoint)
    except XRDSError:
        # Does not parse as a Yadis XRDS file
        openid_services = []

    if not openid_services:
        # Either not an XRDS or there are no OpenID services.

        if response.isXRDS():
            # if we got the Yadis content-type or followed the Yadis
            # header, re-fetch the document without following the Yadis
            # header, with no Accept header.
            return discoverNoYadis(uri)
        else:
            body = response.response_text

        # Try to parse the response as HTML to get OpenID 1.0/1.1
        # <link rel="...">
        try:
            service = OpenIDServiceEndpoint.fromHTML(identity_url, body)
        except ParseError:
            pass # Parsing failed, so return an empty list
        else:
            openid_services = [service]

    return (identity_url, openid_services)


def discoverXRI(iname):
    endpoints = []
    try:
        canonicalID, services = xrires.ProxyResolver().query(
            iname, OpenIDServiceEndpoint.openid_type_uris)
        flt = filters.mkFilter(OpenIDServiceEndpoint)
        for service_element in services:
            endpoints.extend(flt.getServiceEndpoints(iname, service_element))
    except XRDSError:
        oidutil.log('xrds error on ' + iname)

    for endpoint in endpoints:
        # Is there a way to pass this through the filter to the endpoint
        # constructor instead of tacking it on after?
        endpoint.canonicalID = canonicalID

    # FIXME: returned xri should probably be in some normal form
    return iname, endpoints


def discoverNoYadis(uri):
    http_resp = fetchers.fetch(uri)
    if http_resp.status != 200:
        raise DiscoveryFailure(
            'HTTP Response status from identity URL host is not 200. '
            'Got status %r' % (http_resp.status,), http_resp)
    identity_url = http_resp.final_url

    # Try to parse the response as HTML to get OpenID 1.0/1.1
    # <link rel="...">
    try:
        service = OpenIDServiceEndpoint.fromHTML(identity_url, http_resp.body)
    except ParseError:
        openid_services = []
    else:
        openid_services = [service]

    return identity_url, openid_services

if yadis_available:
    discover = discoverYadis
else:
    discover = discoverNoYadis

########NEW FILE########
__FILENAME__ = parse
"""
This module implements a VERY limited parser that finds <link> tags in
the head of HTML or XHTML documents and parses out their attributes
according to the OpenID spec. It is a liberal parser, but it requires
these things from the data in order to work:

 * There must be an open <html> tag

 * There must be an open <head> tag inside of the <html> tag

 * Only <link>s that are found inside of the <head> tag are parsed
   (this is by design)

 * The parser follows the OpenID specification in resolving the
   attributes of the link tags. This means that the attributes DO NOT
   get resolved as they would by an XML or HTML parser. In particular,
   only certain entities get replaced, and href attributes do not get
   resolved relative to a base URL.

From http://openid.net/specs.bml#linkrel:

 * The openid.server URL MUST be an absolute URL. OpenID consumers
   MUST NOT attempt to resolve relative URLs.

 * The openid.server URL MUST NOT include entities other than &amp;,
   &lt;, &gt;, and &quot;.

The parser ignores SGML comments and <![CDATA[blocks]]>. Both kinds of
quoting are allowed for attributes.

The parser deals with invalid markup in these ways:

 * Tag names are not case-sensitive

 * The <html> tag is accepted even when it is not at the top level

 * The <head> tag is accepted even when it is not a direct child of
   the <html> tag, but a <html> tag must be an ancestor of the <head>
   tag

 * <link> tags are accepted even when they are not direct children of
   the <head> tag, but a <head> tag must be an ancestor of the <link>
   tag

 * If there is no closing tag for an open <html> or <head> tag, the
   remainder of the document is viewed as being inside of the tag. If
   there is no closing tag for a <link> tag, the link tag is treated
   as a short tag. Exceptions to this rule are that <html> closes
   <html> and <body> or <head> closes <head>

 * Attributes of the <link> tag are not required to be quoted.

 * In the case of duplicated attribute names, the attribute coming
   last in the tag will be the value returned.

 * Any text that does not parse as an attribute within a link tag will
   be ignored. (e.g. <link pumpkin rel='openid.server' /> will ignore
   pumpkin)

 * If there are more than one <html> or <head> tag, the parser only
   looks inside of the first one.

 * The contents of <script> tags are ignored entirely, except unclosed
   <script> tags. Unclosed <script> tags are ignored.

 * Any other invalid markup is ignored, including unclosed SGML
   comments and unclosed <![CDATA[blocks.
"""

__all__ = ['parseLinkAttrs']

import re

flags = ( re.DOTALL # Match newlines with '.'
        | re.IGNORECASE
        | re.VERBOSE # Allow comments and whitespace in patterns
        | re.UNICODE # Make \b respect Unicode word boundaries
        )

# Stuff to remove before we start looking for tags
removed_re = re.compile(r'''
  # Comments
  <!--.*?-->

  # CDATA blocks
| <!\[CDATA\[.*?\]\]>

  # script blocks
| <script\b

  # make sure script is not an XML namespace
  (?!:)

  [^>]*>.*?</script>

''', flags)

tag_expr = r'''
# Starts with the tag name at a word boundary, where the tag name is
# not a namespace
<%(tag_name)s\b(?!:)

# All of the stuff up to a ">", hopefully attributes.
(?P<attrs>[^>]*?)

(?: # Match a short tag
    />

|   # Match a full tag
    >

    (?P<contents>.*?)

    # Closed by
    (?: # One of the specified close tags
        </?%(closers)s\s*>

        # End of the string
    |   \Z

    )

)
'''

def tagMatcher(tag_name, *close_tags):
    if close_tags:
        options = '|'.join((tag_name,) + close_tags)
        closers = '(?:%s)' % (options,)
    else:
        closers = tag_name

    expr = tag_expr % locals()
    return re.compile(expr, flags)

# Must contain at least an open html and an open head tag
html_find = tagMatcher('html')
head_find = tagMatcher('head', 'body')
link_find = re.compile(r'<link\b(?!:)', flags)

attr_find = re.compile(r'''
# Must start with a sequence of word-characters, followed by an equals sign
(?P<attr_name>\w+)=

# Then either a quoted or unquoted attribute
(?:

 # Match everything that\'s between matching quote marks
 (?P<qopen>["\'])(?P<q_val>.*?)(?P=qopen)
|

 # If the value is not quoted, match up to whitespace
 (?P<unq_val>(?:[^\s<>/]|/(?!>))+)
)

|

(?P<end_link>[<>])
''', flags)

# Entity replacement:
replacements = {
    'amp':'&',
    'lt':'<',
    'gt':'>',
    'quot':'"',
    }

ent_replace = re.compile(r'&(%s);' % '|'.join(replacements.keys()))
def replaceEnt(mo):
    "Replace the entities that are specified by OpenID"
    return replacements.get(mo.group(1), mo.group())

def parseLinkAttrs(html):
    """Find all link tags in a string representing a HTML document and
    return a list of their attributes.

    @param html: the text to parse
    @type html: str or unicode

    @return: A list of dictionaries of attributes, one for each link tag
    @rtype: [[(type(html), type(html))]]
    """
    stripped = removed_re.sub('', html)
    html_mo = html_find.search(stripped)
    if html_mo is None or html_mo.start('contents') == -1:
        return []

    start, end = html_mo.span('contents')
    head_mo = head_find.search(stripped, start, end)
    if head_mo is None or head_mo.start('contents') == -1:
        return []

    start, end = head_mo.span('contents')
    link_mos = link_find.finditer(stripped, head_mo.start(), head_mo.end())

    matches = []
    for link_mo in link_mos:
        start = link_mo.start() + 5
        link_attrs = {}
        for attr_mo in attr_find.finditer(stripped, start):
            if attr_mo.lastgroup == 'end_link':
                break

            # Either q_val or unq_val must be present, but not both
            # unq_val is a True (non-empty) value if it is present
            attr_name, q_val, unq_val = attr_mo.group(
                'attr_name', 'q_val', 'unq_val')
            attr_val = ent_replace.sub(replaceEnt, unq_val or q_val)

            link_attrs[attr_name] = attr_val

        matches.append(link_attrs)

    return matches

def relMatches(rel_attr, target_rel):
    """Does this target_rel appear in the rel_str?"""
    # XXX: TESTME
    rels = rel_attr.strip().split()
    for rel in rels:
        rel = rel.lower()
        if rel == target_rel:
            return 1

    return 0

def linkHasRel(link_attrs, target_rel):
    """Does this link have target_rel as a relationship?"""
    # XXX: TESTME
    rel_attr = link_attrs.get('rel')
    return rel_attr and relMatches(rel_attr, target_rel)

def findLinksRel(link_attrs_list, target_rel):
    """Filter the list of link attributes on whether it has target_rel
    as a relationship."""
    # XXX: TESTME
    matchesTarget = lambda attrs: linkHasRel(attrs, target_rel)
    return filter(matchesTarget, link_attrs_list)

def findFirstHref(link_attrs_list, target_rel):
    """Return the value of the href attribute for the first link tag
    in the list that has target_rel as a relationship."""
    # XXX: TESTME
    matches = findLinksRel(link_attrs_list, target_rel)
    if not matches:
        return None
    first = matches[0]
    return first.get('href')

class ParseError(ValueError):
    """Exception for errors in parsing the HTML text for OpenID
    settings"""

def openIDDiscover(html_text):
    """Parse OpenID settings out of the gived HTML text

    @raises: ParseError
    # XXX: document interface
    # XXX: TESTME
    """
    link_attrs = parseLinkAttrs(html_text)

    server_url = findFirstHref(link_attrs, 'openid.server')
    if server_url is None:
        raise ParseError('No openid.server found')

    delegate_url = findFirstHref(link_attrs, 'openid.delegate')
    return delegate_url, server_url

########NEW FILE########
__FILENAME__ = cryptutil
"""Module containing a cryptographic-quality source of randomness and
other cryptographically useful functionality

Python 2.4 needs no external support for this module, nor does Python
2.3 on a system with /dev/urandom.

Other configurations will need a quality source of random bytes and
access to a function that will convert binary strings to long
integers. This module will work with the Python Cryptography Toolkit
(pycrypto) if it is present. pycrypto can be found with a search
engine, but is currently found at:

http://www.amk.ca/python/code/crypto
"""

__all__ = ['randrange', 'hmacSha1', 'sha1', 'randomString',
           'binaryToLong', 'longToBinary', 'longToBase64', 'base64ToLong']

import hmac
import os
import random
import sha

from openid.oidutil import toBase64, fromBase64

try:
    from Crypto.Util.number import long_to_bytes, bytes_to_long
except ImportError:
    import pickle
    try:
        # Check Python compatiblity by raising an exception on import
        # if the needed functionality is not present. Present in
        # Python >= 2.3
        pickle.encode_long
        pickle.decode_long
    except AttributeError:
        raise ImportError(
            'No functionality for serializing long integers found')

    # Present in Python >= 2.4
    try:
        reversed
    except NameError:
        def reversed(seq):
            return map(seq.__getitem__, xrange(len(seq) - 1, -1, -1))

    def longToBinary(l):
        if l == 0:
            return '\x00'

        return ''.join(reversed(pickle.encode_long(l)))

    def binaryToLong(s):
        return pickle.decode_long(''.join(reversed(s)))
else:
    # We have pycrypto

    def longToBinary(l):
        if l < 0:
            raise ValueError('This function only supports positive integers')

        bytes = long_to_bytes(l)
        if ord(bytes[0]) > 127:
            return '\x00' + bytes
        else:
            return bytes

    def binaryToLong(bytes):
        if not bytes:
            raise ValueError('Empty string passed to strToLong')

        if ord(bytes[0]) > 127:
            raise ValueError('This function only supports positive integers')

        return bytes_to_long(bytes)

# A cryptographically safe source of random bytes
try:
    getBytes = os.urandom
except AttributeError:
    try:
        from Crypto.Util.randpool import RandomPool
    except ImportError:
        # Fall back on /dev/urandom, if present. It would be nice to
        # have Windows equivalent here, but for now, require pycrypto
        # on Windows.
        try:
            _urandom = file('/dev/urandom', 'rb')
        except OSError:
            raise ImportError('No adequate source of randomness found!')
        else:
            def getBytes(n):
                bytes = []
                while n:
                    chunk = _urandom.read(n)
                    n -= len(chunk)
                    bytes.append(chunk)
                    assert n >= 0
                return ''.join(bytes)
    else:
        _pool = RandomPool()
        def getBytes(n, pool=_pool):
            if pool.entropy < n:
                pool.randomize()
            return pool.get_bytes(n)

# A randrange function that works for longs
try:
    randrange = random.SystemRandom().randrange
except AttributeError:
    # In Python 2.2's random.Random, randrange does not support
    # numbers larger than sys.maxint for randrange. For simplicity,
    # use this implementation for any Python that does not have
    # random.SystemRandom
    from math import log, ceil

    _duplicate_cache = {}
    def randrange(start, stop=None, step=1):
        if stop is None:
            stop = start
            start = 0

        r = (stop - start) // step
        try:
            (duplicate, nbytes) = _duplicate_cache[r]
        except KeyError:
            rbytes = longToBinary(r)
            if rbytes[0] == '\x00':
                nbytes = len(rbytes) - 1
            else:
                nbytes = len(rbytes)

            mxrand = (256 ** nbytes)

            # If we get a number less than this, then it is in the
            # duplicated range.
            duplicate = mxrand % r

            if len(_duplicate_cache) > 10:
                _duplicate_cache.clear()

            _duplicate_cache[r] = (duplicate, nbytes)

        while 1:
            bytes = '\x00' + getBytes(nbytes)
            n = binaryToLong(bytes)
            # Keep looping if this value is in the low duplicated range
            if n >= duplicate:
                break

        return start + (n % r) * step

def hmacSha1(key, text):
    return hmac.new(key, text, sha).digest()

def sha1(s):
    return sha.new(s).digest()

def longToBase64(l):
    return toBase64(longToBinary(l))

def base64ToLong(s):
    return binaryToLong(fromBase64(s))

def randomString(length, chrs=None):
    """Produce a string of length random bytes, chosen from chrs."""
    if chrs is None:
        return getBytes(length)
    else:
        n = len(chrs)
        return ''.join([chrs[randrange(n)] for _ in xrange(length)])

########NEW FILE########
__FILENAME__ = dh
from openid import cryptutil
from openid import oidutil

def strxor(x, y):
    if len(x) != len(y):
        raise ValueError('Inputs to strxor must have the same length')

    xor = lambda (a, b): chr(ord(a) ^ ord(b))
    return "".join(map(xor, zip(x, y)))

class DiffieHellman(object):
    DEFAULT_MOD = 155172898181473697471232257763715539915724801966915404479707795314057629378541917580651227423698188993727816152646631438561595825688188889951272158842675419950341258706556549803580104870537681476726513255747040765857479291291572334510643245094715007229621094194349783925984760375594985848253359305585439638443L

    DEFAULT_GEN = 2

    def fromDefaults(cls):
        return cls(cls.DEFAULT_MOD, cls.DEFAULT_GEN)

    fromDefaults = classmethod(fromDefaults)

    def __init__(self, modulus, generator):
        self.modulus = long(modulus)
        self.generator = long(generator)

        self._setPrivate(cryptutil.randrange(1, modulus - 1))

    def _setPrivate(self, private):
        """This is here to make testing easier"""
        self.private = private
        self.public = pow(self.generator, self.private, self.modulus)

    def usingDefaultValues(self):
        return (self.modulus == self.DEFAULT_MOD and
                self.generator == self.DEFAULT_GEN)

    def getSharedSecret(self, composite):
        return pow(composite, self.private, self.modulus)

    def xorSecret(self, composite, secret):
        dh_shared = self.getSharedSecret(composite)
        sha1_dh_shared = cryptutil.sha1(cryptutil.longToBinary(dh_shared))
        return strxor(secret, sha1_dh_shared)

########NEW FILE########
__FILENAME__ = kvform
__all__ = ['seqToKV', 'kvToSeq', 'dictToKV', 'kvToDict']

from openid import oidutil

import types

def seqToKV(seq, strict=False):
    """Represent a sequence of pairs of strings as newline-terminated
    key:value pairs. The pairs are generated in the order given.

    @param seq: The pairs
    @type seq: [(str, (unicode|str))]

    @return: A string representation of the sequence
    @rtype: str
    """
    def err(msg):
        formatted = 'seqToKV warning: %s: %r' % (msg, seq)
        if strict:
            raise ValueError(formatted)
        else:
            oidutil.log(formatted)

    lines = []
    for k, v in seq:
        if not isinstance(k, types.StringType):
            err('Converting key to string: %r' % k)
            k = str(k)

        if '\n' in k:
            raise ValueError(
                'Invalid input for seqToKV: key contains newline: %r' % (k,))

        if ':' in k:
            raise ValueError(
                'Invalid input for seqToKV: key contains colon: %r' % (k,))

        if k.strip() != k:
            err('Key has whitespace at beginning or end: %r' % k)

        if isinstance(v, types.UnicodeType):
            v = v.encode('UTF8')
        if not isinstance(v, types.StringType):
            err('Converting value to string: %r' % v)
            v = str(v)

        if '\n' in v:
            raise ValueError(
                'Invalid input for seqToKV: value contains newline: %r' % (v,))

        if v.strip() != v:
            err('Value has whitespace at beginning or end: %r' % v)

        lines.append(k + ':' + v + '\n')

    return ''.join(lines)

def kvToSeq(data, strict=False):
    """

    After one parse, seqToKV and kvToSeq are inverses, with no warnings:
        seq = kvToSeq(s)

        seqToKV(kvToSeq(seq)) == seq
    """
    def err(msg):
        formatted = 'kvToSeq warning: %s: %r' % (msg, data)
        if strict:
            raise ValueError(formatted)
        else:
            oidutil.log(formatted)

    lines = data.split('\n')
    if lines[-1]:
        err('Does not end in a newline')
    else:
        del lines[-1]

    pairs = []
    line_num = 0
    for line in lines:
        line_num += 1

        # Ignore blank lines
        if not line.strip():
            continue

        pair = line.split(':', 1)
        if len(pair) == 2:
            k, v = pair
            k_s = k.strip()
            if k_s != k:
                fmt = ('In line %d, ignoring leading or trailing '
                       'whitespace in key %r')
                err(fmt % (line_num, k))

            if not k_s:
                err('In line %d, got empty key' % (line_num,))

            v_s = v.strip()
            if v_s != v:
                fmt = ('In line %d, ignoring leading or trailing '
                       'whitespace in value %r')
                err(fmt % (line_num, v))

            pairs.append((k_s, v_s))
        else:
            err('Line %d does not contain a colon' % line_num)

    return pairs

def dictToKV(d):
    seq = d.items()
    seq.sort()
    return seqToKV(seq)

def kvToDict(s):
    return dict(kvToSeq(s))

########NEW FILE########
__FILENAME__ = oidutil
__all__ = ['log', 'appendArgs', 'toBase64', 'fromBase64', 'normalizeUrl']

import binascii
import sys
import urlparse

from urllib import urlencode

def log(message, unused_level=0):
    sys.stderr.write(message)
    sys.stderr.write('\n')

def appendArgs(url, args):
    if hasattr(args, 'items'):
        args = args.items()
        args.sort()
    else:
        args = list(args)

    if len(args) == 0:
        return url

    if '?' in url:
        sep = '&'
    else:
        sep = '?'

    # Map unicode to UTF-8 if present. Do not make any assumptions
    # about the encodings of plain bytes (str).
    i = 0
    for k, v in args:
        if type(k) is not str:
            k = k.encode('UTF-8')

        if type(v) is not str:
            v = v.encode('UTF-8')

        args[i] = (k, v)
        i += 1

    return '%s%s%s' % (url, sep, urlencode(args))

def toBase64(s):
    """Represent string s as base64, omitting newlines"""
    return binascii.b2a_base64(s)[:-1]

def fromBase64(s):
    try:
        return binascii.a2b_base64(s)
    except binascii.Error, why:
        # Convert to a common exception type
        raise ValueError(why[0])

def quoteMinimal(s):
    """Turn a str or unicode object into an ASCII string

    Replace non-ascii characters with a %-encoded, UTF-8
    encoding. This function will fail if the input is a str and there
    are non-7-bit-safe characters. It is assumed that the caller will
    have already translated the input into a Unicode character
    sequence, according to the encoding of the HTTP POST or GET.

    Do not escape anything that is already 7-bit safe, so we do the
    minimal transform on the input
    """
    res = []
    for c in s:
        if c >= u'\x80':
            for b in c.encode('utf8'):
                res.append('%%%02X' % ord(b))
        else:
            res.append(c)
    return str(''.join(res))

def normalizeUrl(url):
    if not isinstance(url, (str, unicode)):
        return None

    url = url.strip()
    parsed = urlparse.urlparse(url)

    if parsed[0] == '' or parsed[1] == '':
        if parsed[2:] == ('', '', '', ''):
            return None

        url = 'http://' + url
        parsed = urlparse.urlparse(url)

    if isinstance(url, unicode):
        try:
            authority = parsed[1].encode('idna')
        except LookupError:
            authority = parsed[1].encode('us-ascii')
    else:
        authority = str(parsed[1])

    tail = map(quoteMinimal, parsed[2:])
    if tail[0] == '':
        tail[0] = '/'
    encoded = (str(parsed[0]), authority) + tuple(tail)
    url = urlparse.urlunparse(encoded)
    assert type(url) is str

    return url

def isAbsoluteHTTPURL(url):
    """Does this URL look like a http or https URL that has a host?

    @param url: The url to check
    @type url: str

    @return: Whether the URL looks OK
    @rtype: bool
    """
    parts = urlparse.urlparse(url)
    return parts[0] in ['http', 'https'] and parts[1]

########NEW FILE########
__FILENAME__ = server
# -*- test-case-name: openid.test.server -*-
"""OpenID server protocol and logic.

Overview
========

    An OpenID server must perform three tasks:

        1. Examine the incoming request to determine its nature and validity.

        2. Make a decision about how to respond to this request.

        3. Format the response according to the protocol.

    The first and last of these tasks may performed by
    the L{decodeRequest<Server.decodeRequest>} and
    L{encodeResponse<Server.encodeResponse>} methods of the
    L{Server} object.  Who gets to do the intermediate task -- deciding
    how to respond to the request -- will depend on what type of request it
    is.

    If it's a request to authenticate a user (a X{C{checkid_setup}} or
    X{C{checkid_immediate}} request), you need to decide if you will assert
    that this user may claim the identity in question.  Exactly how you do
    that is a matter of application policy, but it generally involves making
    sure the user has an account with your system and is logged in, checking
    to see if that identity is hers to claim, and verifying with the user that
    she does consent to releasing that information to the party making the
    request.

    Examine the properties of the L{CheckIDRequest} object, and if
    and when you've come to a decision, form a response by calling
    L{CheckIDRequest.answer}.

    Other types of requests relate to establishing associations between client
    and server and verifying the authenticity of previous communications.
    L{Server} contains all the logic and data necessary to respond to
    such requests; just pass it to L{Server.handleRequest}.


OpenID Extensions
=================

    Do you want to provide other information for your users
    in addition to authentication?  Version 1.2 of the OpenID
    protocol allows consumers to add extensions to their requests.
    For example, with sites using the U{Simple Registration
    Extension<http://www.openidenabled.com/openid/simple-registration-extension/>},
    a user can agree to have their nickname and e-mail address sent to a
    site when they sign up.

    Since extensions do not change the way OpenID authentication works,
    code to handle extension requests may be completely separate from the
    L{OpenIDRequest} class here.  But you'll likely want data sent back by
    your extension to be signed.  L{OpenIDResponse} provides methods with
    which you can add data to it which can be signed with the other data in
    the OpenID signature.

    For example::

        # when request is a checkid_* request
        response = request.answer(True)
        # this will a signed 'openid.sreg.timezone' parameter to the response
        response.addField('sreg', 'timezone', 'America/Los_Angeles')


Stores
======

    The OpenID server needs to maintain state between requests in order
    to function.  Its mechanism for doing this is called a store.  The
    store interface is defined in C{L{openid.store.interface.OpenIDStore}}.
    Additionally, several concrete store implementations are provided, so that
    most sites won't need to implement a custom store.  For a store backed
    by flat files on disk, see C{L{openid.store.filestore.FileOpenIDStore}}.
    For stores based on MySQL or SQLite, see the C{L{openid.store.sqlstore}}
    module.


Upgrading
=========

    The keys by which a server looks up associations in its store have changed
    in version 1.2 of this library.  If your store has entries created from
    version 1.0 code, you should empty it.


@group Requests: OpenIDRequest, AssociateRequest, CheckIDRequest,
    CheckAuthRequest

@group Responses: OpenIDResponse

@group HTTP Codes: HTTP_OK, HTTP_REDIRECT, HTTP_ERROR

@group Response Encodings: ENCODE_KVFORM, ENCODE_URL
"""

import time
from copy import deepcopy

from openid import cryptutil
from openid import kvform
from openid import oidutil
from openid.dh import DiffieHellman
from openid.server.trustroot import TrustRoot
from openid.association import Association

HTTP_OK = 200
HTTP_REDIRECT = 302
HTTP_ERROR = 400

BROWSER_REQUEST_MODES = ['checkid_setup', 'checkid_immediate']
OPENID_PREFIX = 'openid.'

ENCODE_KVFORM = ('kvform',)
ENCODE_URL = ('URL/redirect',)

class OpenIDRequest(object):
    """I represent an incoming OpenID request.

    @cvar mode: the C{X{openid.mode}} of this request.
    @type mode: str
    """
    mode = None


class CheckAuthRequest(OpenIDRequest):
    """A request to verify the validity of a previous response.

    @cvar mode: "X{C{check_authentication}}"
    @type mode: str

    @ivar assoc_handle: The X{association handle} the response was signed with.
    @type assoc_handle: str
    @ivar sig: The signature to check.
    @type sig: str
    @ivar signed: The ordered list of signed items you want to check.
    @type signed: list of pairs

    @ivar invalidate_handle: An X{association handle} the client is asking
        about the validity of.  Optional, may be C{None}.
    @type invalidate_handle: str

    @see: U{OpenID Specs, Mode: check_authentication
        <http://openid.net/specs.bml#mode-check_authentication>}
    """
    mode = "check_authentication"


    def __init__(self, assoc_handle, sig, signed, invalidate_handle=None):
        """Construct me.

        These parameters are assigned directly as class attributes, see
        my L{class documentation<CheckAuthRequest>} for their descriptions.

        @type assoc_handle: str
        @type sig: str
        @type signed: list of pairs
        @type invalidate_handle: str
        """
        self.assoc_handle = assoc_handle
        self.sig = sig
        self.signed = signed
        self.invalidate_handle = invalidate_handle


    def fromQuery(klass, query):
        """Construct me from a web query.

        @param query: The query parameters as a dictionary with each
            key mapping to one value.
        @type query: dict

        @returntype: L{CheckAuthRequest}
        """
        self = klass.__new__(klass)
        try:
            self.assoc_handle = query[OPENID_PREFIX + 'assoc_handle']
            self.sig = query[OPENID_PREFIX + 'sig']
            signed_list = query[OPENID_PREFIX + 'signed']
        except KeyError, e:
            raise ProtocolError(query,
                                text="%s request missing required parameter %s"
                                " from query %s" %
                                (self.mode, e.args[0], query))

        self.invalidate_handle = query.get(OPENID_PREFIX + 'invalidate_handle')

        signed_list = signed_list.split(',')
        signed_pairs = []
        for field in signed_list:
            try:
                if field == 'mode':
                    # XXX KLUDGE HAX WEB PROTOCoL BR0KENNN
                    # openid.mode is currently check_authentication because
                    # that's the mode of this request.  But the signature
                    # was made on something with a different openid.mode.
                    # http://article.gmane.org/gmane.comp.web.openid.general/537
                    value = "id_res"
                else:
                    value = query[OPENID_PREFIX + field]
            except KeyError, e:
                raise ProtocolError(
                    query,
                    text="Couldn't find signed field %r in query %s"
                    % (field, query))
            else:
                signed_pairs.append((field, value))

        self.signed = signed_pairs
        return self

    fromQuery = classmethod(fromQuery)


    def answer(self, signatory):
        """Respond to this request.

        Given a L{Signatory}, I can check the validity of the signature and
        the X{C{invalidate_handle}}.

        @param signatory: The L{Signatory} to use to check the signature.
        @type signatory: L{Signatory}

        @returns: A response with an X{C{is_valid}} (and, if
           appropriate X{C{invalidate_handle}}) field.
        @returntype: L{OpenIDResponse}
        """
        is_valid = signatory.verify(self.assoc_handle, self.sig, self.signed)
        # Now invalidate that assoc_handle so it this checkAuth message cannot
        # be replayed.
        signatory.invalidate(self.assoc_handle, dumb=True)
        response = OpenIDResponse(self)
        response.fields['is_valid'] = (is_valid and "true") or "false"

        if self.invalidate_handle:
            assoc = signatory.getAssociation(self.invalidate_handle, dumb=False)
            if not assoc:
                response.fields['invalidate_handle'] = self.invalidate_handle
        return response


    def __str__(self):
        if self.invalidate_handle:
            ih = " invalidate? %r" % (self.invalidate_handle,)
        else:
            ih = ""
        s = "<%s handle: %r sig: %r: signed: %r%s>" % (
            self.__class__.__name__, self.assoc_handle,
            self.sig, self.signed, ih)
        return s


class PlainTextServerSession(object):
    """An object that knows how to handle association requests with no
    session type.

    @cvar session_type: The session_type for this association
        session. There is no type defined for plain-text in the OpenID
        specification, so we use 'plaintext'.
    @type session_type: str

    @see: U{OpenID Specs, Mode: associate
        <http://openid.net/specs.bml#mode-associate>}
    @see: AssociateRequest
    """
    session_type = 'plaintext'

    def fromQuery(cls, unused_request):
        return cls()

    fromQuery = classmethod(fromQuery)

    def answer(self, secret):
        return {'mac_key': oidutil.toBase64(secret)}


class DiffieHellmanServerSession(object):
    """An object that knows how to handle association requests with the
    Diffie-Hellman session type.

    @cvar session_type: The session_type for this association
        session.
    @type session_type: str

    @ivar dh: The Diffie-Hellman algorithm values for this request
    @type dh: DiffieHellman

    @ivar consumer_pubkey: The public key sent by the consumer in the
        associate request
    @type consumer_pubkey: long

    @see: U{OpenID Specs, Mode: associate
        <http://openid.net/specs.bml#mode-associate>}
    @see: AssociateRequest
    """
    session_type = 'DH-SHA1'

    def __init__(self, dh, consumer_pubkey):
        self.dh = dh
        self.consumer_pubkey = consumer_pubkey

    def fromQuery(cls, query):
        """
        @param query: The associate request's query parameters
        @type query: {str:str}

        @returntype: L{DiffieHellmanServerSession}

        @raises ProtocolError: When parameters required to establish the
            session are missing.
        """
        dh_modulus = query.get('openid.dh_modulus')
        dh_gen = query.get('openid.dh_gen')
        if (dh_modulus is None and dh_gen is not None or
            dh_gen is None and dh_modulus is not None):

            if dh_modulus is None:
                missing = 'modulus'
            else:
                missing = 'generator'

            raise ProtocolError('If non-default modulus or generator is '
                                'supplied, both must be supplied. Missing %s'
                                % (missing,))

        if dh_modulus or dh_gen:
            dh_modulus = cryptutil.base64ToLong(dh_modulus)
            dh_gen = cryptutil.base64ToLong(dh_gen)
            dh = DiffieHellman(dh_modulus, dh_gen)
        else:
            dh = DiffieHellman.fromDefaults()

        consumer_pubkey = query.get('openid.dh_consumer_public')
        if consumer_pubkey is None:
            raise ProtocolError("Public key for DH-SHA1 session "
                                "not found in query %s" % (query,))

        consumer_pubkey = cryptutil.base64ToLong(consumer_pubkey)

        return cls(dh, consumer_pubkey)

    fromQuery = classmethod(fromQuery)

    def answer(self, secret):
        mac_key = self.dh.xorSecret(self.consumer_pubkey, secret)
        return {
            'dh_server_public': cryptutil.longToBase64(self.dh.public),
            'enc_mac_key': oidutil.toBase64(mac_key),
            }


class AssociateRequest(OpenIDRequest):
    """A request to establish an X{association}.

    @cvar mode: "X{C{check_authentication}}"
    @type mode: str

    @ivar assoc_type: The type of association.  The protocol currently only
        defines one value for this, "X{C{HMAC-SHA1}}".
    @type assoc_type: str

    @ivar session: An object that knows how to handle association
        requests of a certain type.

    @see: U{OpenID Specs, Mode: associate
        <http://openid.net/specs.bml#mode-associate>}
    """

    mode = "associate"
    assoc_type = 'HMAC-SHA1'

    session_classes = {
        None: PlainTextServerSession,
        'DH-SHA1': DiffieHellmanServerSession,
        }

    def __init__(self, session):
        """Construct me.

        The session is assigned directly as a class attribute. See my
        L{class documentation<AssociateRequest>} for its description.
        """
        super(AssociateRequest, self).__init__()
        self.session = session


    def fromQuery(klass, query):
        """Construct me from a web query.

        @param query: The query parameters as a dictionary with each
            key mapping to one value.
        @type query: dict

        @returntype: L{AssociateRequest}
        """
        session_type = query.get(OPENID_PREFIX + 'session_type')
        try:
            session_class = klass.session_classes[session_type]
        except KeyError:
            raise ProtocolError(query,
                                "Unknown session type %r" % (session_type,))

        try:
            session = session_class.fromQuery(query)
        except ValueError, why:
            raise ProtocolError(query, 'Error parsing %s session: %s' %
                                (session_class.session_type, why[0]))

        return klass(session)

    fromQuery = classmethod(fromQuery)

    def answer(self, assoc):
        """Respond to this request with an X{association}.

        @param assoc: The association to send back.
        @type assoc: L{openid.association.Association}

        @returns: A response with the association information, encrypted
            to the consumer's X{public key} if appropriate.
        @returntype: L{OpenIDResponse}
        """
        response = OpenIDResponse(self)
        response.fields.update({
            'expires_in': '%d' % (assoc.getExpiresIn(),),
            'assoc_type': 'HMAC-SHA1',
            'assoc_handle': assoc.handle,
            })
        response.fields.update(self.session.answer(assoc.secret))
        if self.session.session_type != 'plaintext':
            response.fields['session_type'] = self.session.session_type

        return response


class CheckIDRequest(OpenIDRequest):
    """A request to confirm the identity of a user.

    This class handles requests for openid modes X{C{checkid_immediate}}
    and X{C{checkid_setup}}.

    @cvar mode: "X{C{checkid_immediate}}" or "X{C{checkid_setup}}"
    @type mode: str

    @ivar immediate: Is this an immediate-mode request?
    @type immediate: bool

    @ivar identity: The identity URL being checked.
    @type identity: str

    @ivar trust_root: "Are you Frank?" asks the checkid request.  "Who wants
        to know?"  C{trust_root}, that's who.  This URL identifies the party
        making the request, and the user will use that to make her decision
        about what answer she trusts them to have.
    @type trust_root: str

    @ivar return_to: The URL to send the user agent back to to reply to this
        request.
    @type return_to: str

    @ivar assoc_handle: Provided in smart mode requests, a handle for a
        previously established association.  C{None} for dumb mode requests.
    @type assoc_handle: str
    """

    def __init__(self, identity, return_to, trust_root=None, immediate=False,
                 assoc_handle=None):
        """Construct me.

        These parameters are assigned directly as class attributes, see
        my L{class documentation<CheckIDRequest>} for their descriptions.

        @raises MalformedReturnURL: When the C{return_to} URL is not a URL.
        """
        self.assoc_handle = assoc_handle
        self.identity = identity
        self.return_to = return_to
        self.trust_root = trust_root or return_to
        if immediate:
            self.immediate = True
            self.mode = "checkid_immediate"
        else:
            self.immediate = False
            self.mode = "checkid_setup"

        if not TrustRoot.parse(self.return_to):
            raise MalformedReturnURL(None, self.return_to)
        if not self.trustRootValid():
            raise UntrustedReturnURL(None, self.return_to, self.trust_root)


    def fromQuery(klass, query):
        """Construct me from a web query.

        @raises ProtocolError: When not all required parameters are present
            in the query.

        @raises MalformedReturnURL: When the C{return_to} URL is not a URL.

        @raises UntrustedReturnURL: When the C{return_to} URL is outside
            the C{trust_root}.

        @param query: The query parameters as a dictionary with each
            key mapping to one value.
        @type query: dict

        @returntype: L{CheckIDRequest}
        """
        self = klass.__new__(klass)
        mode = query[OPENID_PREFIX + 'mode']
        if mode == "checkid_immediate":
            self.immediate = True
            self.mode = "checkid_immediate"
        else:
            self.immediate = False
            self.mode = "checkid_setup"

        required = [
            'identity',
            'return_to',
            ]

        for field in required:
            value = query.get(OPENID_PREFIX + field)
            if not value:
                raise ProtocolError(
                    query,
                    text="Missing required field %s from %r"
                    % (field, query))
            setattr(self, field, value)

        # There's a case for making self.trust_root be a TrustRoot
        # here.  But if TrustRoot isn't currently part of the "public" API,
        # I'm not sure it's worth doing.
        self.trust_root = query.get(OPENID_PREFIX + 'trust_root', self.return_to)
        self.assoc_handle = query.get(OPENID_PREFIX + 'assoc_handle')

        # Using TrustRoot.parse here is a bit misleading, as we're not
        # parsing return_to as a trust root at all.  However, valid URLs
        # are valid trust roots, so we can use this to get an idea if it
        # is a valid URL.  Not all trust roots are valid return_to URLs,
        # however (particularly ones with wildcards), so this is still a
        # little sketchy.
        if not TrustRoot.parse(self.return_to):
            raise MalformedReturnURL(query, self.return_to)

        # I first thought that checking to see if the return_to is within
        # the trust_root is premature here, a logic-not-decoding thing.  But
        # it was argued that this is really part of data validation.  A
        # request with an invalid trust_root/return_to is broken regardless of
        # application, right?
        if not self.trustRootValid():
            raise UntrustedReturnURL(query, self.return_to, self.trust_root)

        return self

    fromQuery = classmethod(fromQuery)


    def trustRootValid(self):
        """Is my return_to under my trust_root?

        @returntype: bool
        """
        if not self.trust_root:
            return True
        tr = TrustRoot.parse(self.trust_root)
        if tr is None:
            raise MalformedTrustRoot(None, self.trust_root)
        return tr.validateURL(self.return_to)


    def answer(self, allow, server_url=None):
        """Respond to this request.

        @param allow: Allow this user to claim this identity, and allow the
            consumer to have this information?
        @type allow: bool

        @param server_url: When an immediate mode request does not
            succeed, it gets back a URL where the request may be
            carried out in a not-so-immediate fashion.  Pass my URL
            in here (the fully qualified address of this server's
            endpoint, i.e.  C{http://example.com/server}), and I
            will use it as a base for the URL for a new request.

            Optional for requests where C{CheckIDRequest.immediate} is C{False}
            or C{allow} is C{True}.

        @type server_url: str

        @returntype: L{OpenIDResponse}
        """
        if allow or self.immediate:
            mode = 'id_res'
        else:
            mode = 'cancel'

        response = OpenIDResponse(self)

        if allow:
            response.addFields(None, {
                'mode': mode,
                'identity': self.identity,
                'return_to': self.return_to,
                })
        else:
            response.addField(None, 'mode', mode, False)
            if self.immediate:
                if not server_url:
                    raise ValueError("setup_url is required for allow=False "
                                     "in immediate mode.")
                # Make a new request just like me, but with immediate=False.
                setup_request = self.__class__(
                    self.identity, self.return_to, self.trust_root,
                    immediate=False, assoc_handle=self.assoc_handle)
                setup_url = setup_request.encodeToURL(server_url)
                response.addField(None, 'user_setup_url', setup_url, False)

        return response


    def encodeToURL(self, server_url):
        """Encode this request as a URL to GET.

        @param server_url: The URL of the OpenID server to make this request of.
        @type server_url: str

        @returntype: str
        """
        # Imported from the alternate reality where these classes are used
        # in both the client and server code, so Requests are Encodable too.
        # That's right, code imported from alternate realities all for the
        # love of you, id_res/user_setup_url.
        q = {'mode': self.mode,
             'identity': self.identity,
             'return_to': self.return_to}
        if self.trust_root:
            q['trust_root'] = self.trust_root
        if self.assoc_handle:
            q['assoc_handle'] = self.assoc_handle

        q = dict([(OPENID_PREFIX + k, v) for k, v in q.iteritems()])

        return oidutil.appendArgs(server_url, q)


    def getCancelURL(self):
        """Get the URL to cancel this request.

        Useful for creating a "Cancel" button on a web form so that operation
        can be carried out directly without another trip through the server.

        (Except you probably want to make another trip through the server so
        that it knows that the user did make a decision.  Or you could simulate
        this method by doing C{.answer(False).encodeToURL()})

        @returntype: str
        @returns: The return_to URL with openid.mode = cancel.
        """
        if self.immediate:
            raise ValueError("Cancel is not an appropriate response to "
                             "immediate mode requests.")
        return oidutil.appendArgs(self.return_to, {OPENID_PREFIX + 'mode':
                                                   'cancel'})


    def __str__(self):
        return '<%s id:%r im:%s tr:%r ah:%r>' % (self.__class__.__name__,
                                                 self.identity,
                                                 self.immediate,
                                                 self.trust_root,
                                                 self.assoc_handle)



class OpenIDResponse(object):
    """I am a response to an OpenID request.

    @ivar request: The request I respond to.
    @type request: L{OpenIDRequest}

    @ivar fields: My parameters as a dictionary with each key mapping to
        one value.  Keys are parameter names with no leading "C{openid.}".
        e.g.  "C{identity}" and "C{mac_key}", never "C{openid.identity}".
    @type fields: dict

    @ivar signed: The names of the fields which should be signed.
    @type signed: list of str
    """

    # Implementer's note: In a more symmetric client/server
    # implementation, there would be more types of OpenIDResponse
    # object and they would have validated attributes according to the
    # type of response.  But as it is, Response objects in a server are
    # basically write-only, their only job is to go out over the wire,
    # so this is just a loose wrapper around OpenIDResponse.fields.

    def __init__(self, request):
        """Make a response to an L{OpenIDRequest}.

        @type request: L{OpenIDRequest}
        """
        self.request = request
        self.fields = {}
        self.signed = []

    def __str__(self):
        return "%s for %s: %s" % (
            self.__class__.__name__,
            self.request.__class__.__name__,
            self.fields)


    def addField(self, namespace, key, value, signed=True):
        """Add a field to this response.

        @param namespace: The extension namespace the field is in, with no
            leading "C{openid.}" e.g. "C{sreg}".
        @type namespace: str

        @param key: The field's name, e.g. "C{fullname}".
        @type key: str

        @param value: The field's value.
        @type value: str

        @param signed: Whether this field should be signed.
        @type signed: bool
        """
        if namespace:
            key = '%s.%s' % (namespace, key)
        self.fields[key] = value
        if signed and key not in self.signed:
            self.signed.append(key)


    def addFields(self, namespace, fields, signed=True):
        """Add a number of fields to this response.

        @param namespace: The extension namespace the field is in, with no
            leading "C{openid.}" e.g. "C{sreg}".
        @type namespace: str

        @param fields: A dictionary with the fields to add.
            e.g. C{{"fullname": "Frank the Goat"}}

        @param signed: Whether these fields should be signed.
        @type signed: bool
        """
        for key, value in fields.iteritems():
            self.addField(namespace, key, value, signed)


    def update(self, namespace, other):
        """Update my fields with those from another L{OpenIDResponse}.

        The idea here is that if you write an OpenID extension, it
        could produce a Response object with C{fields} and C{signed}
        attributes, and you could merge it with me using this method
        before I am signed and sent.

        All entries in C{other.fields} will have their keys prefixed
        with C{namespace} and added to my fields.  All elements of
        C{other.signed} will be prefixed with C{namespace} and added
        to my C{signed} list.

        @param namespace: The extension namespace the field is in, with no
            leading "C{openid.}" e.g. "C{sreg}".
        @type namespace: str

        @param other: A response object to update from.
        @type other: L{OpenIDResponse}
        """
        if namespace:
            namespaced_fields = dict([('%s.%s' % (namespace, k), v) for k, v
                                      in other.fields.iteritems()])
            namespaced_signed = ['%s.%s' % (namespace, k) for k
                                 in other.signed]
        else:
            namespaced_fields = other.fields
            namespaced_signed = other.signed
        self.fields.update(namespaced_fields)
        self.signed.extend(namespaced_signed)


    def needsSigning(self):
        """Does this response require signing?

        @returntype: bool
        """
        return (
            (self.request.mode in ['checkid_setup', 'checkid_immediate'])
            and self.signed
            )


    # implements IEncodable

    def whichEncoding(self):
        """How should I be encoded?

        @returns: one of ENCODE_URL or ENCODE_KVFORM.
        """
        if self.request.mode in BROWSER_REQUEST_MODES:
            return ENCODE_URL
        else:
            return ENCODE_KVFORM


    def encodeToURL(self):
        """Encode a response as a URL for the user agent to GET.

        You will generally use this URL with a HTTP redirect.

        @returns: A URL to direct the user agent back to.
        @returntype: str
        """
        fields = dict(
            [(OPENID_PREFIX + k, v.encode('UTF8')) for k, v in self.fields.iteritems()])
        return oidutil.appendArgs(self.request.return_to, fields)


    def encodeToKVForm(self):
        """Encode a response in key-value colon/newline format.

        This is a machine-readable format used to respond to messages which
        came directly from the consumer and not through the user agent.

        @see: OpenID Specs,
           U{Key-Value Colon/Newline format<http://openid.net/specs.bml#keyvalue>}

        @returntype: str
        """
        return kvform.dictToKV(self.fields)


    def __str__(self):
        return "%s for %s: signed%s %s" % (
            self.__class__.__name__,
            self.request.__class__.__name__,
            self.signed, self.fields)



class WebResponse(object):
    """I am a response to an OpenID request in terms a web server understands.

    I generally come from an L{Encoder}, either directly or from
    L{Server.encodeResponse}.

    @ivar code: The HTTP code of this response.
    @type code: int

    @ivar headers: Headers to include in this response.
    @type headers: dict

    @ivar body: The body of this response.
    @type body: str
    """

    def __init__(self, code=HTTP_OK, headers=None, body=""):
        """Construct me.

        These parameters are assigned directly as class attributes, see
        my L{class documentation<WebResponse>} for their descriptions.
        """
        self.code = code
        if headers is not None:
            self.headers = headers
        else:
            self.headers = {}
        self.body = body



class Signatory(object):
    """I sign things.

    I also check signatures.

    All my state is encapsulated in an
    L{OpenIDStore<openid.store.interface.OpenIDStore>}, which means
    I'm not generally pickleable but I am easy to reconstruct.

    @cvar SECRET_LIFETIME: The number of seconds a secret remains valid.
    @type SECRET_LIFETIME: int
    """

    SECRET_LIFETIME = 14 * 24 * 60 * 60 # 14 days, in seconds

    # keys have a bogus server URL in them because the filestore
    # really does expect that key to be a URL.  This seems a little
    # silly for the server store, since I expect there to be only one
    # server URL.
    _normal_key = 'http://localhost/|normal'
    _dumb_key = 'http://localhost/|dumb'


    def __init__(self, store):
        """Create a new Signatory.

        @param store: The back-end where my associations are stored.
        @type store: L{openid.store.interface.OpenIDStore}
        """
        assert store is not None
        self.store = store


    def verify(self, assoc_handle, sig, signed_pairs):
        """Verify that the signature for some data is valid.

        @param assoc_handle: The handle of the association used to sign the
            data.
        @type assoc_handle: str

        @param sig: The base-64 encoded signature to check.
        @type sig: str

        @param signed_pairs: The data to check, an ordered list of key-value
            pairs.  The keys should be as they are in the request's C{signed}
            list, without any C{"openid."} prefix.
        @type signed_pairs: list of pairs

        @returns: C{True} if the signature is valid, C{False} if not.
        @returntype: bool
        """
        assoc = self.getAssociation(assoc_handle, dumb=True)
        if not assoc:
            oidutil.log("failed to get assoc with handle %r to verify sig %r"
                        % (assoc_handle, sig))
            return False

        # Not using Association.checkSignature here is intentional;
        # Association should not know things like "the list of signed pairs is
        # in the request's 'signed' parameter and it is comma-separated."
        expected_sig = oidutil.toBase64(assoc.sign(signed_pairs))

        return sig == expected_sig


    def sign(self, response):
        """Sign a response.

        I take a L{OpenIDResponse}, create a signature for everything
        in its L{signed<OpenIDResponse.signed>} list, and return a new
        copy of the response object with that signature included.

        @param response: A response to sign.
        @type response: L{OpenIDResponse}

        @returns: A signed copy of the response.
        @returntype: L{OpenIDResponse}
        """
        signed_response = deepcopy(response)
        assoc_handle = response.request.assoc_handle
        if assoc_handle:
            # normal mode
            assoc = self.getAssociation(assoc_handle, dumb=False)
            if not assoc:
                # fall back to dumb mode
                signed_response.fields['invalidate_handle'] = assoc_handle
                assoc = self.createAssociation(dumb=True)
        else:
            # dumb mode.
            assoc = self.createAssociation(dumb=True)

        signed_response.fields['assoc_handle'] = assoc.handle
        assoc.addSignature(signed_response.signed, signed_response.fields,
                           prefix='')
        return signed_response


    def createAssociation(self, dumb=True, assoc_type='HMAC-SHA1'):
        """Make a new association.

        @param dumb: Is this association for a dumb-mode transaction?
        @type dumb: bool

        @param assoc_type: The type of association to create.  Currently
            there is only one type defined, C{HMAC-SHA1}.
        @type assoc_type: str

        @returns: the new association.
        @returntype: L{openid.association.Association}
        """
        secret = cryptutil.getBytes(20)
        uniq = oidutil.toBase64(cryptutil.getBytes(4))
        handle = '{%s}{%x}{%s}' % (assoc_type, int(time.time()), uniq)

        assoc = Association.fromExpiresIn(
            self.SECRET_LIFETIME, handle, secret, assoc_type)

        if dumb:
            key = self._dumb_key
        else:
            key = self._normal_key
        self.store.storeAssociation(key, assoc)
        return assoc


    def getAssociation(self, assoc_handle, dumb):
        """Get the association with the specified handle.

        @type assoc_handle: str

        @param dumb: Is this association used with dumb mode?
        @type dumb: bool

        @returns: the association, or None if no valid association with that
            handle was found.
        @returntype: L{openid.association.Association}
        """
        # Hmm.  We've created an interface that deals almost entirely with
        # assoc_handles.  The only place outside the Signatory that uses this
        # (and thus the only place that ever sees Association objects) is
        # when creating a response to an association request, as it must have
        # the association's secret.

        if assoc_handle is None:
            raise ValueError("assoc_handle must not be None")

        if dumb:
            key = self._dumb_key
        else:
            key = self._normal_key
        assoc = self.store.getAssociation(key, assoc_handle)
        if assoc is not None and assoc.expiresIn <= 0:
            oidutil.log("requested %sdumb key %r is expired (by %s seconds)" %
                        ((not dumb) and 'not-' or '',
                         assoc_handle, assoc.expiresIn))
            self.store.removeAssociation(key, assoc_handle)
            assoc = None
        return assoc


    def invalidate(self, assoc_handle, dumb):
        """Invalidates the association with the given handle.

        @type assoc_handle: str

        @param dumb: Is this association used with dumb mode?
        @type dumb: bool
        """
        if dumb:
            key = self._dumb_key
        else:
            key = self._normal_key
        self.store.removeAssociation(key, assoc_handle)



class Encoder(object):
    """I encode responses in to L{WebResponses<WebResponse>}.

    If you don't like L{WebResponses<WebResponse>}, you can do
    your own handling of L{OpenIDResponses<OpenIDResponse>} with
    L{OpenIDResponse.whichEncoding}, L{OpenIDResponse.encodeToURL}, and
    L{OpenIDResponse.encodeToKVForm}.
    """

    responseFactory = WebResponse


    def encode(self, response):
        """Encode a response to a L{WebResponse}.

        @raises EncodingError: When I can't figure out how to encode this
            message.
        """
        encode_as = response.whichEncoding()
        if encode_as == ENCODE_KVFORM:
            wr = self.responseFactory(body=response.encodeToKVForm())
            if isinstance(response, Exception):
                wr.code = HTTP_ERROR
        elif encode_as == ENCODE_URL:
            location = response.encodeToURL()
            wr = self.responseFactory(code=HTTP_REDIRECT,
                                      headers={'location': location})
        else:
            # Can't encode this to a protocol message.  You should probably
            # render it to HTML and show it to the user.
            raise EncodingError(response)
        return wr



class SigningEncoder(Encoder):
    """I encode responses in to L{WebResponses<WebResponse>}, signing them when required.
    """

    def __init__(self, signatory):
        """Create a L{SigningEncoder}.

        @param signatory: The L{Signatory} I will make signatures with.
        @type signatory: L{Signatory}
        """
        self.signatory = signatory


    def encode(self, response):
        """Encode a response to a L{WebResponse}, signing it first if appropriate.

        @raises EncodingError: When I can't figure out how to encode this
            message.

        @raises AlreadySigned: When this response is already signed.

        @returntype: L{WebResponse}
        """
        # the isinstance is a bit of a kludge... it means there isn't really
        # an adapter to make the interfaces quite match.
        if (not isinstance(response, Exception)) and response.needsSigning():
            if not self.signatory:
                raise ValueError(
                    "Must have a store to sign this request: %s" %
                    (response,), response)
            if 'sig' in response.fields:
                raise AlreadySigned(response)
            response = self.signatory.sign(response)
        return super(SigningEncoder, self).encode(response)



class Decoder(object):
    """I decode an incoming web request in to a L{OpenIDRequest}.
    """

    _handlers = {
        'checkid_setup': CheckIDRequest.fromQuery,
        'checkid_immediate': CheckIDRequest.fromQuery,
        'check_authentication': CheckAuthRequest.fromQuery,
        'associate': AssociateRequest.fromQuery,
        }


    def decode(self, query):
        """I transform query parameters into an L{OpenIDRequest}.

        If the query does not seem to be an OpenID request at all, I return
        C{None}.

        @param query: The query parameters as a dictionary with each
            key mapping to one value.
        @type query: dict

        @raises ProtocolError: When the query does not seem to be a valid
            OpenID request.

        @returntype: L{OpenIDRequest}
        """
        if not query:
            return None
        myquery = dict(filter(lambda (k, v): k.startswith(OPENID_PREFIX),
                              query.iteritems()))
        if not myquery:
            return None

        mode = myquery.get(OPENID_PREFIX + 'mode')
        if isinstance(mode, list):
            raise TypeError("query dict must have one value for each key, "
                            "not lists of values.  Query is %r" % (query,))

        if not mode:
            raise ProtocolError(
                query,
                text="No %smode value in query %r" % (
                OPENID_PREFIX, query))
        handler = self._handlers.get(mode, self.defaultDecoder)
        return handler(query)


    def defaultDecoder(self, query):
        """Called to decode queries when no handler for that mode is found.

        @raises ProtocolError: This implementation always raises
            L{ProtocolError}.
        """
        mode = query[OPENID_PREFIX + 'mode']
        raise ProtocolError(
            query,
            text="No decoder for mode %r" % (mode,))



class Server(object):
    """I handle requests for an OpenID server.

    Some types of requests (those which are not C{checkid} requests) may be
    handed to my L{handleRequest} method, and I will take care of it and
    return a response.

    For your convenience, I also provide an interface to L{Decoder.decode}
    and L{SigningEncoder.encode} through my methods L{decodeRequest} and
    L{encodeResponse}.

    All my state is encapsulated in an
    L{OpenIDStore<openid.store.interface.OpenIDStore>}, which means
    I'm not generally pickleable but I am easy to reconstruct.

    Example::

        oserver = Server(FileOpenIDStore(data_path))
        request = oserver.decodeRequest(query)
        if request.mode in ["checkid_immediate", "checkid_setup"]:
            if self.isAuthorized(request.identity, request.trust_root):
                response = request.answer(True)
            elif request.immediate:
                response = request.answer(False, self.base_url)
            else:
                self.showDecidePage(request)
                return
        else:
            response = oserver.handleRequest(request)

        webresponse = oserver.encode(response)

    @ivar signatory: I'm using this for associate requests and to sign things.
    @type signatory: L{Signatory}

    @ivar decoder: I'm using this to decode things.
    @type decoder: L{Decoder}

    @ivar encoder: I'm using this to encode things.
    @type encoder: L{Encoder}
    """

    signatoryClass = Signatory
    encoderClass = SigningEncoder
    decoderClass = Decoder

    def __init__(self, store):
        """A new L{Server}.

        @param store: The back-end where my associations are stored.
        @type store: L{openid.store.interface.OpenIDStore}
        """
        self.store = store
        self.signatory = self.signatoryClass(self.store)
        self.encoder = self.encoderClass(self.signatory)
        self.decoder = self.decoderClass()


    def handleRequest(self, request):
        """Handle a request.

        Give me a request, I will give you a response.  Unless it's a type
        of request I cannot handle myself, in which case I will raise
        C{NotImplementedError}.  In that case, you can handle it yourself,
        or add a method to me for handling that request type.

        @raises NotImplementedError: When I do not have a handler defined
            for that type of request.
        """
        handler = getattr(self, 'openid_' + request.mode, None)
        if handler is not None:
            return handler(request)
        else:
            raise NotImplementedError(
                "%s has no handler for a request of mode %r." %
                (self, request.mode))


    def openid_check_authentication(self, request):
        """Handle and respond to {check_authentication} requests.

        @returntype: L{OpenIDResponse}
        """
        return request.answer(self.signatory)


    def openid_associate(self, request):
        """Handle and respond to {associate} requests.

        @returntype: L{OpenIDResponse}
        """
        assoc = self.signatory.createAssociation(dumb=False)
        return request.answer(assoc)


    def decodeRequest(self, query):
        """Transform query parameters into an L{OpenIDRequest}.

        If the query does not seem to be an OpenID request at all, I return
        C{None}.

        @param query: The query parameters as a dictionary with each
            key mapping to one value.
        @type query: dict

        @raises ProtocolError: When the query does not seem to be a valid
            OpenID request.

        @returntype: L{OpenIDRequest}

        @see: L{Decoder.decode}
        """
        return self.decoder.decode(query)


    def encodeResponse(self, response):
        """Encode a response to a L{WebResponse}, signing it first if appropriate.

        @raises EncodingError: When I can't figure out how to encode this
            message.

        @raises AlreadySigned: When this response is already signed.

        @returntype: L{WebResponse}

        @see: L{Encoder.encode}
        """
        return self.encoder.encode(response)



class ProtocolError(Exception):
    """A message did not conform to the OpenID protocol.

    @ivar query: The query that is failing to be a valid OpenID request.
    @type query: dict
    """

    def __init__(self, query, text=None):
        """When an error occurs.

        @param query: The query that is failing to be a valid OpenID request.
        @type query: dict

        @param text: A message about the encountered error.  Set as C{args[0]}.
        @type text: str
        """
        self.query = query
        Exception.__init__(self, text)


    def hasReturnTo(self):
        """Did this request have a return_to parameter?

        @returntype: bool
        """
        if self.query is None:
            return False
        else:
            return (OPENID_PREFIX + 'return_to') in self.query


    # implements IEncodable

    def encodeToURL(self):
        """Encode a response as a URL for the user agent to GET.

        You will generally use this URL with a HTTP redirect.

        @returns: A URL to direct the user agent back to.
        @returntype: str
        """
        return_to = self.query.get(OPENID_PREFIX + 'return_to')
        if not return_to:
            raise ValueError("I have no return_to URL.")
        return oidutil.appendArgs(return_to, {
            'openid.mode': 'error',
            'openid.error': str(self),
            })


    def encodeToKVForm(self):
        """Encode a response in key-value colon/newline format.

        This is a machine-readable format used to respond to messages which
        came directly from the consumer and not through the user agent.

        @see: OpenID Specs,
           U{Key-Value Colon/Newline format<http://openid.net/specs.bml#keyvalue>}

        @returntype: str
        """
        return kvform.dictToKV({
            'mode': 'error',
            'error': str(self),
            })


    def whichEncoding(self):
        """How should I be encoded?

        @returns: one of ENCODE_URL, ENCODE_KVFORM, or None.  If None,
            I cannot be encoded as a protocol message and should be
            displayed to the user.
        """
        if self.hasReturnTo():
            return ENCODE_URL

        if self.query is None:
            return None

        mode = self.query.get('openid.mode')
        if mode:
            if mode not in BROWSER_REQUEST_MODES:
                return ENCODE_KVFORM

        # According to the OpenID spec as of this writing, we are probably
        # supposed to switch on request type here (GET versus POST) to figure
        # out if we're supposed to print machine-readable or human-readable
        # content at this point.  GET/POST seems like a pretty lousy way of
        # making the distinction though, as it's just as possible that the
        # user agent could have mistakenly been directed to post to the
        # server URL.

        # Basically, if your request was so broken that you didn't manage to
        # include an openid.mode, I'm not going to worry too much about
        # returning you something you can't parse.
        return None



class EncodingError(Exception):
    """Could not encode this as a protocol message.

    You should probably render it and show it to the user.

    @ivar response: The response that failed to encode.
    @type response: L{OpenIDResponse}
    """

    def __init__(self, response):
        Exception.__init__(self, response)
        self.response = response



class AlreadySigned(EncodingError):
    """This response is already signed."""



class UntrustedReturnURL(ProtocolError):
    """A return_to is outside the trust_root."""

    def __init__(self, query, return_to, trust_root):
        ProtocolError.__init__(self, query)
        self.return_to = return_to
        self.trust_root = trust_root

    def __str__(self):
        return "return_to %r not under trust_root %r" % (self.return_to,
                                                         self.trust_root)


class MalformedReturnURL(ProtocolError):
    """The return_to URL doesn't look like a valid URL."""
    def __init__(self, query, return_to):
        self.return_to = return_to
        ProtocolError.__init__(self, query)



class MalformedTrustRoot(ProtocolError):
    """The trust root is not well-formed.

    @see: OpenID Specs, U{openid.trust_root<http://openid.net/specs.bml#mode-checkid_immediate>}
    """
    pass


#class IEncodable: # Interface
#     def encodeToURL(return_to):
#         """Encode a response as a URL for redirection.
#
#         @returns: A URL to direct the user agent back to.
#         @returntype: str
#         """
#         pass
#
#     def encodeToKvform():
#         """Encode a response in key-value colon/newline format.
#
#         This is a machine-readable format used to respond to messages which
#         came directly from the consumer and not through the user agent.
#
#         @see: OpenID Specs,
#            U{Key-Value Colon/Newline format<http://openid.net/specs.bml#keyvalue>}
#
#         @returntype: str
#         """
#         pass
#
#     def whichEncoding():
#         """How should I be encoded?
#
#         @returns: one of ENCODE_URL, ENCODE_KVFORM, or None.  If None,
#             I cannot be encoded as a protocol message and should be
#             displayed to the user.
#         """
#         pass

########NEW FILE########
__FILENAME__ = trustroot
"""
This module contains the C{L{TrustRoot}} class, which helps handle
trust root checking.  This module is used by the
C{L{openid.server.server}} module, but it is also available to server
implementers who wish to use it for additional trust root checking.
"""

from urlparse import urlparse, urlunparse

############################################
_protocols = ['http', 'https']
_top_level_domains = (
    'com|edu|gov|int|mil|net|org|biz|info|name|museum|coop|aero|ac|ad|ae|'
    'af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|az|ba|bb|bd|be|bf|bg|bh|bi|bj|'
    'bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|'
    'cu|cv|cx|cy|cz|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|fi|fj|fk|fm|fo|'
    'fr|ga|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|'
    'ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|'
    'kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|mg|mh|mk|ml|mm|'
    'mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|'
    'nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|ru|rw|sa|'
    'sb|sc|sd|se|sg|sh|si|sj|sk|sl|sm|sn|so|sr|st|sv|sy|sz|tc|td|tf|tg|th|'
    'tj|tk|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|um|us|uy|uz|va|vc|ve|vg|vi|'
    'vn|vu|wf|ws|ye|yt|yu|za|zm|zw'
    ).split('|')


def _parseURL(url):
    proto, netloc, path, params, query, frag = urlparse(url)
    path = urlunparse(('', '', path, params, query, frag))

    if ':' in netloc:
        try:
            host, port = netloc.split(':')
        except ValueError:
            return None
    else:
        host = netloc
        port = ''

    host = host.lower()
    if not path:
        path = '/'

    return proto, host, port, path

class TrustRoot(object):
    """
    This class represents an OpenID trust root.  The C{L{parse}}
    classmethod accepts a trust root string, producing a
    C{L{TrustRoot}} object.  The method OpenID server implementers
    would be most likely to use is the C{L{isSane}} method, which
    checks the trust root for given patterns that indicate that the
    trust root is too broad or points to a local network resource.

    @sort: parse, isSane
    """

    def __init__(self, unparsed, proto, wildcard, host, port, path):
        self.unparsed = unparsed
        self.proto = proto
        self.wildcard = wildcard
        self.host = host
        self.port = port
        self.path = path

    def isSane(self):
        """
        This method checks the to see if a trust root represents a
        reasonable (sane) set of URLs.  'http://*.com/', for example
        is not a reasonable pattern, as it cannot meaningfully specify
        the site claiming it.  This function attempts to find many
        related examples, but it can only work via heuristics.
        Negative responses from this method should be treated as
        advisory, used only to alert the user to examine the trust
        root carefully.


        @return: Whether the trust root is sane

        @rtype: C{bool}
        """

        if self.host == 'localhost':
            return True

        host_parts = self.host.split('.')
        if self.wildcard:
            assert host_parts[0] == '', host_parts
            del host_parts[0]

        # If it's an absolute domain name, remove the empty string
        # from the end.
        if host_parts and not host_parts[-1]:
            del host_parts[-1]

        if not host_parts:
            return False

        # Do not allow adjacent dots
        if '' in host_parts:
            return False

        tld = host_parts[-1]
        if tld not in _top_level_domains:
            return False

        if len(tld) == 2:
            if len(host_parts) == 1:
                # entire host part is 2-letter tld
                return False

            if len(host_parts[-2]) <= 3:
                # It's a 2-letter tld with a short second to last segment
                # so there needs to be more than two segments specified 
                # (e.g. *.co.uk is insane)
                return len(host_parts) > 2
            else:
                # A long second to last segment is specified.
                return len(host_parts) > 1
        else:
            # It's a regular tld, so it needs at least one more segment
            return len(host_parts) > 1

        # Fell through, so not sane
        return False

    def validateURL(self, url):
        """
        Validates a URL against this trust root.


        @param url: The URL to check

        @type url: C{str}


        @return: Whether the given URL is within this trust root.

        @rtype: C{bool}
        """

        url_parts = _parseURL(url)
        if url_parts is None:
            return False

        proto, host, port, path = url_parts

        if proto != self.proto:
            return False

        if port != self.port:
            return False

        if '*' in host:
            return False

        if not self.wildcard:
            if host != self.host:
                return False
        elif ((not host.endswith(self.host)) and
              ('.' + host) != self.host):
            return False

        if path != self.path:
            path_len = len(self.path)
            trust_prefix = self.path[:path_len]
            url_prefix = path[:path_len]

            # must be equal up to the length of the path, at least
            if trust_prefix != url_prefix:
                return False

            # These characters must be on the boundary between the end
            # of the trust root's path and the start of the URL's
            # path.
            if '?' in self.path:
                allowed = '&'
            else:
                allowed = '?/'

            return (self.path[-1] in allowed or
                path[path_len] in allowed)

        return True

    def parse(cls, trust_root):
        """
        This method creates a C{L{TrustRoot}} instance from the given
        input, if possible.


        @param trust_root: This is the trust root to parse into a
        C{L{TrustRoot}} object.

        @type trust_root: C{str}


        @return: A C{L{TrustRoot}} instance if trust_root parses as a
        trust root, C{None} otherwise.

        @rtype: C{NoneType} or C{L{TrustRoot}}
        """
        if not isinstance(trust_root, (str, unicode)):
            return None

        url_parts = _parseURL(trust_root)
        if url_parts is None:
            return None

        proto, host, port, path = url_parts

        # check for valid prototype
        if proto not in _protocols:
            return None

        # extract wildcard if it is there
        if host.find('*', 1) != -1:
            # wildcard must be at start of domain:  *.foo.com, not foo.*.com
            return None

        if host.startswith('*'):
            # Starts with star, so must have a dot after it (if a
            # domain is specified)
            if len(host) > 1 and host[1] != '.':
                return None

            host = host[1:]
            wilcard = True
        else:
            wilcard = False

        # we have a valid trust root
        tr = cls(trust_root, proto, wilcard, host, port, path)

        return tr

    parse = classmethod(parse)

    def checkSanity(cls, trust_root_string):
        """str -> bool

        is this a sane trust root?
        """
        return cls.parse(trust_root_string).isSane()

    checkSanity = classmethod(checkSanity)

    def checkURL(cls, trust_root, url):
        """quick func for validating a url against a trust root.  See the
        TrustRoot class if you need more control."""
        tr = cls.parse(trust_root)
        return tr is not None and tr.validateURL(url)

    checkURL = classmethod(checkURL)

    def __repr__(self):
        return "TrustRoot('%s', '%s', '%s', '%s', '%s', '%s')" % (
            self.unparsed, self.proto, self.wildcard, self.host, self.port,
            self.path)

    def __str__(self):
        return repr(self)

########NEW FILE########
__FILENAME__ = dumbstore
"""
This module contains an C{L{OpenIDStore}} implementation with no
persistent backing, for use only by limited consumers.
"""

from openid import cryptutil
from openid.store.interface import OpenIDStore

class DumbStore(OpenIDStore):
    """
    This is a store for use in the worst case, when you have no way of
    saving state on the consumer site.  Using this store makes the
    consumer vulnerable to replay attacks (though only within the
    lifespan of the tokens), as it's unable to use nonces.  Avoid
    using this store if it is at all possible.

    Most of the methods of this class are implementation details.
    Users of this class need to worry only about the C{L{__init__}}
    method.

    @sort: __init__
    """
    def __init__(self, secret_phrase):
        """
        Creates a new DumbStore instance.  For the security of the
        tokens generated by the library, this class attempts to at
        least have a secure implementation of C{L{getAuthKey}}.

        When you create an instance of this class, pass in a secret
        phrase.  The phrase is hashed with sha1 to make it the correct
        length and form for an auth key.  That allows you to use a
        long string as the secret phrase, which means you can make it
        very difficult to guess.

        Each C{L{DumbStore}} instance that is created for use by your
        consumer site needs to use the same C{secret_phrase}.

        @param secret_phrase: The phrase used to create the auth key
            returned by C{L{getAuthKey}}

        @type secret_phrase: C{str}
        """
        self.auth_key = cryptutil.sha1(secret_phrase)

    def storeAssociation(self, server_url, association):
        """
        This implementation does nothing.
        """
        pass

    def getAssociation(self, server_url, handle=None):
        """
        This implementation always returns C{None}.


        @return: C{None}

        @rtype: C{None}
        """
        return None

    def removeAssociation(self, server_url, handle):
        """
        This implementation always returns C{False}.


        @return: C{False}

        @rtype: C{bool}
        """
        return False

    def storeNonce(self, nonce):
        """
        This implementation does nothing.
        """
        pass

    def useNonce(self, nonce):
        """
        In a system truly limited to dumb mode, nonces must all be
        accepted.  This therefore always returns C{True}, which makes
        replay attacks feasible during the lifespan of the token.


        @return: C{True}

        @rtype: C{bool}
        """
        return True

    def getAuthKey(self):
        """
        This method returns the auth key generated by the constructor.


        @return: The auth key generated by the constructor.

        @rtype: C{str}
        """
        return self.auth_key

    def isDumb(self):
        """
        This store is a dumb mode store, so this method is overridden
        to return C{True}.


        @return: C{True}

        @rtype: C{bool}
        """
        return True

########NEW FILE########
__FILENAME__ = filestore
"""
This module contains an C{L{OpenIDStore}} implementation backed by
flat files.
"""

import string
import os
import os.path
import sys
import time

from errno import EEXIST, ENOENT

try:
    from tempfile import mkstemp
except ImportError:
    # Python < 2.3
    import tempfile
    import warnings
    warnings.filterwarnings("ignore",
                            "tempnam is a potential security risk",
                            RuntimeWarning,
                            "openid.store.filestore")

    def mkstemp(dir):
        for _ in range(5):
            name = os.tempnam(dir)
            try:
                fd = os.open(name, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0600)
            except OSError, why:
                if why[0] != EEXIST:
                    raise
            else:
                return fd, name

        raise RuntimeError('Failed to get temp file after 5 attempts')

from openid.association import Association
from openid.store.interface import OpenIDStore
from openid import cryptutil, oidutil

_filename_allowed = string.ascii_letters + string.digits + '.'
try:
    # 2.4
    set
except NameError:
    try:
        # 2.3
        import sets
    except ImportError:
        # Python < 2.2
        d = {}
        for c in _filename_allowed:
            d[c] = None
        _isFilenameSafe = d.has_key
        del d
    else:
        _isFilenameSafe = sets.Set(_filename_allowed).__contains__
else:
    _isFilenameSafe = set(_filename_allowed).__contains__

def _safe64(s):
    h64 = oidutil.toBase64(cryptutil.sha1(s))
    h64 = h64.replace('+', '_')
    h64 = h64.replace('/', '.')
    h64 = h64.replace('=', '')
    return h64

def _filenameEscape(s):
    filename_chunks = []
    for c in s:
        if _isFilenameSafe(c):
            filename_chunks.append(c)
        else:
            filename_chunks.append('_%02X' % ord(c))
    return ''.join(filename_chunks)

def _removeIfPresent(filename):
    """Attempt to remove a file, returning whether the file existed at
    the time of the call.

    str -> bool
    """
    try:
        os.unlink(filename)
    except OSError, why:
        if why[0] == ENOENT:
            # Someone beat us to it, but it's gone, so that's OK
            return 0
        else:
            raise
    else:
        # File was present
        return 1

def _ensureDir(dir_name):
    """Create dir_name as a directory if it does not exist. If it
    exists, make sure that it is, in fact, a directory.

    Can raise OSError

    str -> NoneType
    """
    try:
        os.makedirs(dir_name)
    except OSError, why:
        if why[0] != EEXIST or not os.path.isdir(dir_name):
            raise

class FileOpenIDStore(OpenIDStore):
    """
    This is a filesystem-based store for OpenID associations and
    nonces.  This store should be safe for use in concurrent systems
    on both windows and unix (excluding NFS filesystems).  There are a
    couple race conditions in the system, but those failure cases have
    been set up in such a way that the worst-case behavior is someone
    having to try to log in a second time.

    Most of the methods of this class are implementation details.
    People wishing to just use this store need only pay attention to
    the C{L{__init__}} method.

    Methods of this object can raise OSError if unexpected filesystem
    conditions, such as bad permissions or missing directories, occur.
    """

    def __init__(self, directory):
        """
        Initializes a new FileOpenIDStore.  This initializes the
        nonce and association directories, which are subdirectories of
        the directory passed in.

        @param directory: This is the directory to put the store
            directories in.

        @type directory: C{str}
        """
        # Make absolute
        directory = os.path.normpath(os.path.abspath(directory))

        self.nonce_dir = os.path.join(directory, 'nonces')

        self.association_dir = os.path.join(directory, 'associations')

        # Temp dir must be on the same filesystem as the assciations
        # directory and the directory containing the auth key file.
        self.temp_dir = os.path.join(directory, 'temp')

        self.auth_key_name = os.path.join(directory, 'auth_key')

        self.max_nonce_age = 6 * 60 * 60 # Six hours, in seconds

        self._setup()

    def _setup(self):
        """Make sure that the directories in which we store our data
        exist.

        () -> NoneType
        """
        _ensureDir(os.path.dirname(self.auth_key_name))
        _ensureDir(self.nonce_dir)
        _ensureDir(self.association_dir)
        _ensureDir(self.temp_dir)

    def _mktemp(self):
        """Create a temporary file on the same filesystem as
        self.auth_key_name and self.association_dir.

        The temporary directory should not be cleaned if there are any
        processes using the store. If there is no active process using
        the store, it is safe to remove all of the files in the
        temporary directory.

        () -> (file, str)
        """
        fd, name = mkstemp(dir=self.temp_dir)
        try:
            file_obj = os.fdopen(fd, 'wb')
            return file_obj, name
        except:
            _removeIfPresent(name)
            raise

    def readAuthKey(self):
        """Read the auth key from the auth key file. Will return None
        if there is currently no key.

        () -> str or NoneType
        """
        try:
            auth_key_file = file(self.auth_key_name, 'rb')
        except IOError, why:
            if why[0] == ENOENT:
                return None
            else:
                raise

        try:
            return auth_key_file.read()
        finally:
            auth_key_file.close()

    def createAuthKey(self):
        """Generate a new random auth key and safely store it in the
        location specified by self.auth_key_name.

        () -> str"""

        # Do the import here because this should only get called at
        # most once from each process. Once the auth key file is
        # created, this should not get called at all.
        auth_key = cryptutil.randomString(self.AUTH_KEY_LEN)

        file_obj, tmp = self._mktemp()
        try:
            file_obj.write(auth_key)
            # Must close the file before linking or renaming it on win32.
            file_obj.close()

            try:
                if hasattr(os, 'link') and sys.platform != 'cygwin':
                    # because os.link works in some cygwin environments,
                    # but returns errno 17 on others.  Haven't figured out
                    # how to predict when it will do that yet.
                    os.link(tmp, self.auth_key_name)
                else:
                    os.rename(tmp, self.auth_key_name)
            except OSError, why:
                if why[0] == EEXIST:
                    auth_key = self.readAuthKey()
                    if auth_key is None:
                        # This should only happen if someone deletes
                        # the auth key file out from under us.
                        raise
                else:
                    raise
        finally:
            file_obj.close()
            _removeIfPresent(tmp)

        return auth_key

    def getAuthKey(self):
        """Retrieve the auth key from the file specified by
        self.auth_key_name, creating it if it does not exist.

        () -> str
        """
        auth_key = self.readAuthKey()
        if auth_key is None:
            auth_key = self.createAuthKey()

        if len(auth_key) != self.AUTH_KEY_LEN:
            fmt = ('Got an invalid auth key from %s. Expected %d byte '
                   'string. Got: %r')
            msg = fmt % (self.auth_key_name, self.AUTH_KEY_LEN, auth_key)
            raise ValueError(msg)

        return auth_key

    def getAssociationFilename(self, server_url, handle):
        """Create a unique filename for a given server url and
        handle. This implementation does not assume anything about the
        format of the handle. The filename that is returned will
        contain the domain name from the server URL for ease of human
        inspection of the data directory.

        (str, str) -> str
        """
        if server_url.find('://') == -1:
            raise ValueError('Bad server URL: %r' % server_url)

        proto, rest = server_url.split('://', 1)
        domain = _filenameEscape(rest.split('/', 1)[0])
        url_hash = _safe64(server_url)
        if handle:
            handle_hash = _safe64(handle)
        else:
            handle_hash = ''

        filename = '%s-%s-%s-%s' % (proto, domain, url_hash, handle_hash)

        return os.path.join(self.association_dir, filename)

    def storeAssociation(self, server_url, association):
        """Store an association in the association directory.

        (str, Association) -> NoneType
        """
        association_s = association.serialize()
        filename = self.getAssociationFilename(server_url, association.handle)
        tmp_file, tmp = self._mktemp()

        try:
            try:
                tmp_file.write(association_s)
                os.fsync(tmp_file.fileno())
            finally:
                tmp_file.close()

            try:
                os.rename(tmp, filename)
            except OSError, why:
                if why[0] != EEXIST:
                    raise

                # We only expect EEXIST to happen only on Windows. It's
                # possible that we will succeed in unlinking the existing
                # file, but not in putting the temporary file in place.
                try:
                    os.unlink(filename)
                except OSError, why:
                    if why[0] == ENOENT:
                        pass
                    else:
                        raise

                # Now the target should not exist. Try renaming again,
                # giving up if it fails.
                os.rename(tmp, filename)
        except:
            # If there was an error, don't leave the temporary file
            # around.
            _removeIfPresent(tmp)
            raise

    def getAssociation(self, server_url, handle=None):
        """Retrieve an association. If no handle is specified, return
        the association with the latest expiration.

        (str, str or NoneType) -> Association or NoneType
        """
        if handle is None:
            handle = ''

        # The filename with the empty handle is a prefix of all other
        # associations for the given server URL.
        filename = self.getAssociationFilename(server_url, handle)

        if handle:
            return self._getAssociation(filename)
        else:
            association_files = os.listdir(self.association_dir)
            matching_files = []
            # strip off the path to do the comparison
            name = os.path.basename(filename)
            for association_file in association_files:
                if association_file.startswith(name):
                    matching_files.append(association_file)

            matching_associations = []
            # read the matching files and sort by time issued
            for name in matching_files:
                full_name = os.path.join(self.association_dir, name)
                association = self._getAssociation(full_name)
                if association is not None:
                    matching_associations.append(
                        (association.issued, association))

            matching_associations.sort()

            # return the most recently issued one.
            if matching_associations:
                (_, assoc) = matching_associations[-1]
                return assoc
            else:
                return None

    def _getAssociation(self, filename):
        try:
            assoc_file = file(filename, 'rb')
        except IOError, why:
            if why[0] == ENOENT:
                # No association exists for that URL and handle
                return None
            else:
                raise
        else:
            try:
                assoc_s = assoc_file.read()
            finally:
                assoc_file.close()

            try:
                association = Association.deserialize(assoc_s)
            except ValueError:
                _removeIfPresent(filename)
                return None

        # Clean up expired associations
        if association.getExpiresIn() == 0:
            _removeIfPresent(filename)
            return None
        else:
            return association

    def removeAssociation(self, server_url, handle):
        """Remove an association if it exists. Do nothing if it does not.

        (str, str) -> bool
        """
        assoc = self.getAssociation(server_url, handle)
        if assoc is None:
            return 0
        else:
            filename = self.getAssociationFilename(server_url, handle)
            return _removeIfPresent(filename)

    def storeNonce(self, nonce):
        """Mark this nonce as present.

        str -> NoneType
        """
        filename = os.path.join(self.nonce_dir, nonce)
        nonce_file = file(filename, 'w')
        nonce_file.close()

    def useNonce(self, nonce):
        """Return whether this nonce is present. As a side effect,
        mark it as no longer present.

        str -> bool
        """
        filename = os.path.join(self.nonce_dir, nonce)
        try:
            st = os.stat(filename)
        except OSError, why:
            if why[0] == ENOENT:
                # File was not present, so nonce is no good
                return 0
            else:
                raise
        else:
            # Either it is too old or we are using it. Either way, we
            # must remove the file.
            try:
                os.unlink(filename)
            except OSError, why:
                if why[0] == ENOENT:
                    # someone beat us to it, so we cannot use this
                    # nonce anymore.
                    return 0
                else:
                    raise

            now = time.time()
            nonce_age = now - st.st_mtime

            # We can us it if the age of the file is less than the
            # expiration time.
            return nonce_age <= self.max_nonce_age

    def clean(self):
        """Remove expired entries from the database. This is
        potentially expensive, so only run when it is acceptable to
        take time.

        () -> NoneType
        """
        nonces = os.listdir(self.nonce_dir)
        now = time.time()

        # Check all nonces for expiry
        for nonce in nonces:
            filename = os.path.join(self.nonce_dir, nonce)
            try:
                st = os.stat(filename)
            except OSError, why:
                if why[0] == ENOENT:
                    # The file did not exist by the time we tried to
                    # stat it.
                    pass
                else:
                    raise
            else:
                # Remove the nonce if it has expired
                nonce_age = now - st.st_mtime
                if nonce_age > self.max_nonce_age:
                    _removeIfPresent(filename)

        association_filenames = os.listdir(self.association_dir)
        for association_filename in association_filenames:
            try:
                association_file = file(association_filename, 'rb')
            except IOError, why:
                if why[0] == ENOENT:
                    pass
                else:
                    raise
            else:
                try:
                    assoc_s = association_file.read()
                finally:
                    association_file.close()

                # Remove expired or corrupted associations
                try:
                    association = Association.deserialize(assoc_s)
                except ValueError:
                    _removeIfPresent(association_filename)
                else:
                    if association.getExpiresIn() == 0:
                        _removeIfPresent(association_filename)

########NEW FILE########
__FILENAME__ = interface
"""
This module contains the definition of the C{L{OpenIDStore}}
interface.
"""

class OpenIDStore(object):
    """
    This is the interface for the store objects the OpenID library
    uses.  It is a single class that provides all of the persistence
    mechanisms that the OpenID library needs, for both servers and
    consumers.


    @cvar AUTH_KEY_LEN: The length of the auth key that should be
        returned by the C{L{getAuthKey}} method.

    @sort: storeAssociation, getAssociation, removeAssociation,
        storeNonce, useNonce, getAuthKey, isDumb
    """

    AUTH_KEY_LEN = 20

    def storeAssociation(self, server_url, association):
        """
        This method puts a C{L{Association
        <openid.association.Association>}} object into storage,
        retrievable by server URL and handle.


        @param server_url: The URL of the identity server that this
            association is with.  Because of the way the server
            portion of the library uses this interface, don't assume
            there are any limitations on the character set of the
            input string.  In particular, expect to see unescaped
            non-url-safe characters in the server_url field.

        @type server_url: C{str}


        @param association: The C{L{Association
            <openid.association.Association>}} to store.

        @type association: C{L{Association
            <openid.association.Association>}}


        @return: C{None}

        @rtype: C{NoneType}
        """
        raise NotImplementedError

    def getAssociation(self, server_url, handle=None):
        """
        This method returns an C{L{Association
        <openid.association.Association>}} object from storage that
        matches the server URL and, if specified, handle. It returns
        C{None} if no such association is found or if the matching
        association is expired.

        If no handle is specified, the store may return any
        association which matches the server URL.  If multiple
        associations are valid, the recommended return value for this
        method is the one that will remain valid for the longest
        duration.

        This method is allowed (and encouraged) to garbage collect
        expired associations when found. This method must not return
        expired associations.


        @param server_url: The URL of the identity server to get the
            association for.  Because of the way the server portion of
            the library uses this interface, don't assume there are
            any limitations on the character set of the input string.
            In particular, expect to see unescaped non-url-safe
            characters in the server_url field.

        @type server_url: C{str}


        @param handle: This optional parameter is the handle of the
            specific association to get.  If no specific handle is
            provided, any valid association matching the server URL is
            returned.

        @type handle: C{str} or C{NoneType}


        @return: The C{L{Association
            <openid.association.Association>}} for the given identity
            server.

        @rtype: C{L{Association <openid.association.Association>}} or
            C{NoneType}
        """
        raise NotImplementedError

    def removeAssociation(self, server_url, handle):
        """
        This method removes the matching association if it's found,
        and returns whether the association was removed or not.


        @param server_url: The URL of the identity server the
            association to remove belongs to.  Because of the way the
            server portion of the library uses this interface, don't
            assume there are any limitations on the character set of
            the input string.  In particular, expect to see unescaped
            non-url-safe characters in the server_url field.

        @type server_url: C{str}


        @param handle: This is the handle of the association to
            remove.  If there isn't an association found that matches
            both the given URL and handle, then there was no matching
            handle found.

        @type handle: C{str}


        @return: Returns whether or not the given association existed.

        @rtype: C{bool} or C{int}
        """
        raise NotImplementedError


    def storeNonce(self, nonce):
        """
        Stores a nonce.  This is used by the consumer to prevent
        replay attacks.


        @param nonce: The nonce to store.

        @type nonce: C{str}


        @return: C{None}

        @rtype: C{NoneType}
        """
        raise NotImplementedError

    def useNonce(self, nonce):
        """
        This method is called when the library is attempting to use a
        nonce.  If the nonce is in the store, this method removes it
        and returns a value which evaluates as true.  Otherwise it
        returns a value which evaluates as false.

        This method is allowed and encouraged to treat nonces older
        than some period (a very conservative window would be 6 hours,
        for example) as no longer existing, and return False and
        remove them.


        @param nonce: The nonce to use.

        @type nonce: C{str}


        @return: Whether or not the nonce was valid.

        @rtype: C{bool} or C{int}
        """
        raise NotImplementedError

    def getAuthKey(self):
        """
        This method returns a key used to sign the tokens, to
        ensure that they haven't been tampered with in transit.  It
        should return the same key every time it is called.  The key
        returned should be C{L{AUTH_KEY_LEN}} bytes long.

        @return: The key.  It should be C{L{AUTH_KEY_LEN}} bytes in
            length, and use the full range of byte values.  That is,
            it should be treated as a lump of binary data stored in a
            C{str} instance.

        @rtype: C{str}
        """
        raise NotImplementedError

    def isDumb(self):
        """
        This method must return C{True} if the store is a
        dumb-mode-style store.  Unlike all other methods in this
        class, this one provides a default implementation, which
        returns C{False}.

        In general, any custom subclass of C{L{OpenIDStore}} won't
        override this method, as custom subclasses are only likely to
        be created when the store is fully functional.

        @return: C{True} if the store works fully, C{False} if the
           consumer will have to use dumb mode to use this store.

        @rtype: C{bool}
        """
        return False

########NEW FILE########
__FILENAME__ = sqlstore
"""
This module contains C{L{OpenIDStore}} implementations that use
various SQL databases to back them.
"""
import time

from openid import cryptutil
from openid.association import Association
from openid.store.interface import OpenIDStore

def _inTxn(func):
    def wrapped(self, *args, **kwargs):
        return self._callInTransaction(func, self, *args, **kwargs)

    if hasattr(func, '__name__'):
        try:
            wrapped.__name__ = func.__name__[4:]
        except TypeError:
            pass

    if hasattr(func, '__doc__'):
        wrapped.__doc__ = func.__doc__

    return wrapped

class SQLStore(OpenIDStore):
    """
    This is the parent class for the SQL stores, which contains the
    logic common to all of the SQL stores.

    The table names used are determined by the class variables
    C{L{settings_table}}, C{L{associations_table}}, and
    C{L{nonces_table}}.  To change the name of the tables used, pass
    new table names into the constructor.

    To create the tables with the proper schema, see the
    C{L{createTables}} method.

    This class shouldn't be used directly.  Use one of its subclasses
    instead, as those contain the code necessary to use a specific
    database.

    All methods other than C{L{__init__}} and C{L{createTables}}
    should be considered implementation details.


    @cvar settings_table: This is the default name of the table to
        keep this store's settings in.
    
    @cvar associations_table: This is the default name of the table to
        keep associations in
    
    @cvar nonces_table: This is the default name of the table to keep
        nonces in.


    @sort: __init__, createTables
    """

    settings_table = 'oid_settings'
    associations_table = 'oid_associations'
    nonces_table = 'oid_nonces'

    def __init__(self, conn, settings_table=None, associations_table=None,
                 nonces_table=None):
        """
        This creates a new SQLStore instance.  It requires an
        established database connection be given to it, and it allows
        overriding the default table names.


        @param conn: This must be an established connection to a
            database of the correct type for the SQLStore subclass
            you're using.

        @type conn: A python database API compatible connection
            object.


        @param settings_table: This is an optional parameter to
            specify the name of the table used for this store's
            settings.  The default value is specified in
            C{L{SQLStore.settings_table}}.

        @type settings_table: C{str}


        @param associations_table: This is an optional parameter to
            specify the name of the table used for storing
            associations.  The default value is specified in
            C{L{SQLStore.associations_table}}.

        @type associations_table: C{str}


        @param nonces_table: This is an optional parameter to specify
            the name of the table used for storing nonces.  The
            default value is specified in C{L{SQLStore.nonces_table}}.

        @type nonces_table: C{str}
        """
        self.conn = conn
        self.cur = None
        self._statement_cache = {}
        self._table_names = {
            'settings': settings_table or self.settings_table,
            'associations': associations_table or self.associations_table,
            'nonces': nonces_table or self.nonces_table,
            }
        self.max_nonce_age = 6 * 60 * 60 # Six hours, in seconds

    def blobDecode(self, blob):
        """Convert a blob as returned by the SQL engine into a str object.

        str -> str"""
        return blob

    def blobEncode(self, s):
        """Convert a str object into the necessary object for storing
        in the database as a blob."""
        return s

    def _getSQL(self, sql_name):
        try:
            return self._statement_cache[sql_name]
        except KeyError:
            sql = getattr(self, sql_name)
            sql %= self._table_names
            self._statement_cache[sql_name] = sql
            return sql

    def _execSQL(self, sql_name, *args):
        sql = self._getSQL(sql_name)
        self.cur.execute(sql, args)

    def __getattr__(self, attr):
        # if the attribute starts with db_, use a default
        # implementation that looks up the appropriate SQL statement
        # as an attribute of this object and executes it.
        if attr[:3] == 'db_':
            sql_name = attr[3:] + '_sql'
            def func(*args):
                return self._execSQL(sql_name, *args)
            setattr(self, attr, func)
            return func
        else:
            raise AttributeError('Attribute %r not found' % (attr,))

    def _callInTransaction(self, func, *args, **kwargs):
        """Execute the given function inside of a transaction, with an
        open cursor. If no exception is raised, the transaction is
        comitted, otherwise it is rolled back."""
        # No nesting of transactions
        self.conn.rollback()

        try:
            self.cur = self.conn.cursor()
            try:
                ret = func(*args, **kwargs)
            finally:
                self.cur.close()
                self.cur = None
        except:
            self.conn.rollback()
            raise
        else:
            self.conn.commit()

        return ret

    def txn_createTables(self):
        """
        This method creates the database tables necessary for this
        store to work.  It should not be called if the tables already
        exist.
        """
        self.db_create_nonce()
        self.db_create_assoc()
        self.db_create_settings()

    createTables = _inTxn(txn_createTables)

    def txn_getAuthKey(self):
        """Get the key for this consumer to use to sign its own
        communications. This function will create a new key if one
        does not yet exist.

        () -> str
        """
        self.db_get_auth()
        val = self.cur.fetchone()
        if val is None:
            auth_key = cryptutil.randomString(self.AUTH_KEY_LEN)
            auth_key_s = self.blobEncode(auth_key)
            self.db_create_auth(auth_key_s)
        else:
            (auth_key_s,) = val
            auth_key = self.blobDecode(auth_key_s)

        if len(auth_key) != self.AUTH_KEY_LEN:
            fmt = 'Expected %d-byte string for auth key. Got %r'
            raise ValueError(fmt % (self.AUTH_KEY_LEN, auth_key))

        return auth_key

    getAuthKey = _inTxn(txn_getAuthKey)

    def txn_storeAssociation(self, server_url, association):
        """Set the association for the server URL.

        Association -> NoneType
        """
        a = association
        self.db_set_assoc(
            server_url,
            a.handle,
            self.blobEncode(a.secret),
            a.issued,
            a.lifetime,
            a.assoc_type)

    storeAssociation = _inTxn(txn_storeAssociation)

    def txn_getAssociation(self, server_url, handle=None):
        """Get the most recent association that has been set for this
        server URL and handle.

        str -> NoneType or Association
        """
        if handle is not None:
            self.db_get_assoc(server_url, handle)
        else:
            self.db_get_assocs(server_url)

        rows = self.cur.fetchall()
        if len(rows) == 0:
            return None
        else:
            associations = []
            for values in rows:
                assoc = Association(*values)
                assoc.secret = self.blobDecode(assoc.secret)
                if assoc.getExpiresIn() == 0:
                    self.txn_removeAssociation(server_url, assoc.handle)
                else:
                    associations.append((assoc.issued, assoc))

            if associations:
                associations.sort()
                return associations[-1][1]
            else:
                return None

    getAssociation = _inTxn(txn_getAssociation)

    def txn_removeAssociation(self, server_url, handle):
        """Remove the association for the given server URL and handle,
        returning whether the association existed at all.

        (str, str) -> bool
        """
        self.db_remove_assoc(server_url, handle)
        return self.cur.rowcount > 0 # -1 is undefined

    removeAssociation = _inTxn(txn_removeAssociation)

    def txn_storeNonce(self, nonce):
        """Add this nonce to the set of extant nonces, ignoring if it
        is already present.

        str -> NoneType
        """
        now = int(time.time())
        self.db_add_nonce(nonce, now)

    storeNonce = _inTxn(txn_storeNonce)

    def txn_useNonce(self, nonce):
        """Return whether this nonce is present, and if it is, then
        remove it from the set.

        str -> bool"""
        self.db_get_nonce(nonce)
        row = self.cur.fetchone()
        if row is not None:
            (nonce, timestamp) = row
            nonce_age = int(time.time()) - timestamp
            if nonce_age > self.max_nonce_age:
                present = 0
            else:
                present = 1

            self.db_remove_nonce(nonce)
        else:
            present = 0

        return present

    useNonce = _inTxn(txn_useNonce)

class SQLiteStore(SQLStore):
    """
    This is an SQLite-based specialization of C{L{SQLStore}}.

    To create an instance, see C{L{SQLStore.__init__}}.  To create the
    tables it will use, see C{L{SQLStore.createTables}}.

    All other methods are implementation details.
    """
    
    create_nonce_sql = """
    CREATE TABLE %(nonces)s
    (
        nonce CHAR(8) UNIQUE PRIMARY KEY,
        expires INTEGER
    );
    """

    create_assoc_sql = """
    CREATE TABLE %(associations)s
    (
        server_url VARCHAR(2047),
        handle VARCHAR(255),
        secret BLOB(128),
        issued INTEGER,
        lifetime INTEGER,
        assoc_type VARCHAR(64),
        PRIMARY KEY (server_url, handle)
    );
    """

    create_settings_sql = """
    CREATE TABLE %(settings)s
    (
        setting VARCHAR(128) UNIQUE PRIMARY KEY,
        value BLOB(20)
    );
    """

    create_auth_sql = 'INSERT INTO %(settings)s VALUES ("auth_key", ?);'
    get_auth_sql = 'SELECT value FROM %(settings)s WHERE setting = "auth_key";'

    set_assoc_sql = ('INSERT OR REPLACE INTO %(associations)s '
                     'VALUES (?, ?, ?, ?, ?, ?);')
    get_assocs_sql = ('SELECT handle, secret, issued, lifetime, assoc_type '
                      'FROM %(associations)s WHERE server_url = ?;')
    get_assoc_sql = (
        'SELECT handle, secret, issued, lifetime, assoc_type '
        'FROM %(associations)s WHERE server_url = ? AND handle = ?;')

    remove_assoc_sql = ('DELETE FROM %(associations)s '
                        'WHERE server_url = ? AND handle = ?;')

    add_nonce_sql = 'INSERT OR REPLACE INTO %(nonces)s VALUES (?, ?);'
    get_nonce_sql = 'SELECT * FROM %(nonces)s WHERE nonce = ?;'
    remove_nonce_sql = 'DELETE FROM %(nonces)s WHERE nonce = ?;'

    def blobDecode(self, buf):
        return str(buf)

    def blobEncode(self, s):
        return buffer(s)

class MySQLStore(SQLStore):
    """
    This is a MySQL-based specialization of C{L{SQLStore}}.

    Uses InnoDB tables for transaction support.

    To create an instance, see C{L{SQLStore.__init__}}.  To create the
    tables it will use, see C{L{SQLStore.createTables}}.

    All other methods are implementation details.
    """

    create_nonce_sql = """
    CREATE TABLE %(nonces)s
    (
        nonce CHAR(8) UNIQUE PRIMARY KEY,
        expires INTEGER
    )
    TYPE=InnoDB;
    """

    create_assoc_sql = """
    CREATE TABLE %(associations)s
    (
        server_url BLOB,
        handle VARCHAR(255),
        secret BLOB,
        issued INTEGER,
        lifetime INTEGER,
        assoc_type VARCHAR(64),
        PRIMARY KEY (server_url(255), handle)
    )
    TYPE=InnoDB;
    """

    create_settings_sql = """
    CREATE TABLE %(settings)s
    (
        setting VARCHAR(128) UNIQUE PRIMARY KEY,
        value BLOB
    )
    TYPE=InnoDB;
    """

    create_auth_sql = 'INSERT INTO %(settings)s VALUES ("auth_key", %%s);'
    get_auth_sql = 'SELECT value FROM %(settings)s WHERE setting = "auth_key";'

    set_assoc_sql = ('REPLACE INTO %(associations)s '
                     'VALUES (%%s, %%s, %%s, %%s, %%s, %%s);')
    get_assocs_sql = ('SELECT handle, secret, issued, lifetime, assoc_type'
                      ' FROM %(associations)s WHERE server_url = %%s;')
    get_assoc_sql = (
        'SELECT handle, secret, issued, lifetime, assoc_type'
        ' FROM %(associations)s WHERE server_url = %%s AND handle = %%s;')
    remove_assoc_sql = ('DELETE FROM %(associations)s '
                        'WHERE server_url = %%s AND handle = %%s;')

    add_nonce_sql = 'REPLACE INTO %(nonces)s VALUES (%%s, %%s);'
    get_nonce_sql = 'SELECT * FROM %(nonces)s WHERE nonce = %%s;'
    remove_nonce_sql = 'DELETE FROM %(nonces)s WHERE nonce = %%s;'

    def blobDecode(self, blob):
        return blob.tostring()

class PostgreSQLStore(SQLStore):
    """
    This is a PostgreSQL-based specialization of C{L{SQLStore}}.

    To create an instance, see C{L{SQLStore.__init__}}.  To create the
    tables it will use, see C{L{SQLStore.createTables}}.

    All other methods are implementation details.
    """

    create_nonce_sql = """
    CREATE TABLE %(nonces)s
    (
        nonce CHAR(8) UNIQUE PRIMARY KEY,
        expires INTEGER
    );
    """

    create_assoc_sql = """
    CREATE TABLE %(associations)s
    (
        server_url VARCHAR(2047),
        handle VARCHAR(255),
        secret BYTEA,
        issued INTEGER,
        lifetime INTEGER,
        assoc_type VARCHAR(64),
        PRIMARY KEY (server_url, handle),
        CONSTRAINT secret_length_constraint CHECK (LENGTH(secret) <= 128)
    );
    """

    create_settings_sql = """
    CREATE TABLE %(settings)s
    (
        setting VARCHAR(128) UNIQUE PRIMARY KEY,
        value BYTEA,
        CONSTRAINT value_length_constraint CHECK (LENGTH(value) <= 20)
    );
    """

    create_auth_sql = "INSERT INTO %(settings)s VALUES ('auth_key', %%s);"
    get_auth_sql = "SELECT value FROM %(settings)s WHERE setting = 'auth_key';"

    def db_set_assoc(self, server_url, handle, secret, issued, lifetime, assoc_type):
        """
        Set an association.  This is implemented as a method because
        REPLACE INTO is not supported by PostgreSQL (and is not
        standard SQL).
        """
        result = self.db_get_assoc(server_url, handle)
        rows = self.cur.fetchall()
        if len(rows):
            # Update the table since this associations already exists.
            return self.db_update_assoc(secret, issued, lifetime, assoc_type,
                                        server_url, handle)
        else:
            # Insert a new record because this association wasn't
            # found.
            return self.db_new_assoc(server_url, handle, secret, issued,
                                     lifetime, assoc_type)

    new_assoc_sql = ('INSERT INTO %(associations)s '
                     'VALUES (%%s, %%s, %%s, %%s, %%s, %%s);')
    update_assoc_sql = ('UPDATE %(associations)s SET '
                        'secret = %%s, issued = %%s, '
                        'lifetime = %%s, assoc_type = %%s '
                        'WHERE server_url = %%s AND handle = %%s;')
    get_assocs_sql = ('SELECT handle, secret, issued, lifetime, assoc_type'
                      ' FROM %(associations)s WHERE server_url = %%s;')
    get_assoc_sql = (
        'SELECT handle, secret, issued, lifetime, assoc_type'
        ' FROM %(associations)s WHERE server_url = %%s AND handle = %%s;')
    remove_assoc_sql = ('DELETE FROM %(associations)s '
                        'WHERE server_url = %%s AND handle = %%s;')

    def db_add_nonce(self, nonce, expires):
        """
        Set a nonce.  This is implemented as a method because REPLACE
        INTO is not supported by PostgreSQL (and is not standard SQL).
        """
        self.db_get_nonce(nonce)
        rows = self.cur.fetchall()
        if len(rows):
            # Update the table since this nonce already exists.
            return self.db_update_nonce(expires, nonce)
        else:
            # Insert a new record because this nonce wasn't found.
            return self.db_new_nonce(nonce, expires)

    update_nonce_sql = 'UPDATE %(nonces)s SET expires = %%s WHERE nonce = %%s;'
    new_nonce_sql = 'INSERT INTO %(nonces)s VALUES (%%s, %%s);'
    get_nonce_sql = 'SELECT * FROM %(nonces)s WHERE nonce = %%s;'
    remove_nonce_sql = 'DELETE FROM %(nonces)s WHERE nonce = %%s;'

    def blobEncode(self, blob):
        import psycopg
        return psycopg.Binary(blob)

########NEW FILE########
__FILENAME__ = base
import os
from os.path import isfile, isdir, getmtime, dirname, splitext, getsize
from tempfile import mkstemp
from shutil import copyfile
from subprocess import Popen, PIPE

from PIL import Image, ImageFilter

from sorl.thumbnail import defaults
from sorl.thumbnail.processors import get_valid_options, dynamic_import


class ThumbnailException(Exception):
    # Stop Django templates from choking if something goes wrong.
    silent_variable_failure = True


class Thumbnail(object):
    def __init__(self, source, requested_size, opts=None, quality=85,
                 dest=None, convert_path=defaults.CONVERT,
                 wvps_path=defaults.WVPS, processors=None):
        # Paths to external commands
        self.convert_path = convert_path
        self.wvps_path = wvps_path
        # Absolute paths to files
        self.source = source
        self.dest = dest

        # Thumbnail settings
        try:
            x, y = [int(v) for v in requested_size]
        except (TypeError, ValueError):
            raise TypeError('Thumbnail received invalid value for size '
                            'argument: %s' % repr(requested_size))
        else:
            self.requested_size = (x, y)
        try:
            self.quality = int(quality) 
            if not 0 < quality <= 100:
                raise ValueError
        except (TypeError, ValueError):
            raise TypeError('Thumbnail received invalid value for quality '
                            'argument: %r' % quality)

        # Processors
        if processors is None:
            processors = dynamic_import(defaults.PROCESSORS)
        self.processors = processors

        # Handle old list format for opts.
        opts = opts or {}
        if isinstance(opts, (list, tuple)):
            opts = dict([(opt, None) for opt in opts])

        # Set Thumbnail opt(ion)s
        VALID_OPTIONS = get_valid_options(processors)
        for opt in opts:
            if not opt in VALID_OPTIONS:
                raise TypeError('Thumbnail received an invalid option: %s'
                                % opt)
        self.opts = opts

        if self.dest is not None:
            self.generate()

    def generate(self):
        """
        Generates the thumbnail if it doesn't exist or if the file date of the
        source file is newer than that of the thumbnail.
        """
        # Ensure dest(ination) attribute is set
        if not self.dest:
            raise ThumbnailException("No destination filename set.")

        if not isinstance(self.dest, basestring):
            # We'll assume dest is a file-like instance if it exists but isn't
            # a string.
            self._do_generate()
        elif not isfile(self.dest) or (self.source_exists and
            getmtime(self.source) > getmtime(self.dest)):

            # Ensure the directory exists
            directory = dirname(self.dest)
            if directory and not isdir(directory):
                os.makedirs(directory)

            self._do_generate()

    def _check_source_exists(self):
        """
        Ensure the source file exists. If source is not a string then it is
        assumed to be a file-like instance which "exists".
        """
        if not hasattr(self, '_source_exists'):
            self._source_exists = (self.source and
                                   (not isinstance(self.source, basestring) or
                                    isfile(self.source)))
        return self._source_exists
    source_exists = property(_check_source_exists)

    def _get_source_filetype(self):
        """
        Set the source filetype. First it tries to use magic and
        if import error it will just use the extension
        """
        if not hasattr(self, '_source_filetype'):
            if not isinstance(self.source, basestring):
                # Assuming a file-like object - we won't know it's type.
                return None
            try:
                import magic
            except ImportError:
                self._source_filetype = splitext(self.source)[1].lower().\
                   replace('.', '').replace('jpeg', 'jpg')
            else:
                m = magic.open(magic.MAGIC_NONE)
                m.load()
                ftype = m.file(self.source)
                if ftype.find('Microsoft Office Document') != -1:
                    self._source_filetype = 'doc'
                elif ftype.find('PDF document') != -1:
                    self._source_filetype = 'pdf'
                elif ftype.find('JPEG') != -1:
                    self._source_filetype = 'jpg'
                else:
                    self._source_filetype = ftype
        return self._source_filetype
    source_filetype = property(_get_source_filetype)

    # data property is the image data of the (generated) thumbnail
    def _get_data(self):
        if not hasattr(self, '_data'):
            try:
                self._data = Image.open(self.dest)
            except IOError, detail:
                raise ThumbnailException(detail)
        return self._data
    def _set_data(self, im):
        self._data = im
    data = property(_get_data, _set_data)

    # source_data property is the image data from the source file
    def _get_source_data(self):
        if not hasattr(self, '_source_data'):
            if not self.source_exists:
                raise ThumbnailException("Source file: '%s' does not exist." %
                                         self.source)
            if self.source_filetype == 'doc':
                self._convert_wvps(self.source)
            elif self.source_filetype == 'pdf':
                self._convert_imagemagick(self.source)
            else:
                self.source_data = self.source
        return self._source_data

    def _set_source_data(self, image):
        if isinstance(image, Image.Image):
            self._source_data = image
        else:
            try:
                self._source_data = Image.open(image)
            except IOError, detail:
                raise ThumbnailException("%s: %s" % (detail, image))
            except MemoryError:
                raise ThumbnailException("Memory Error: %s" % image)
    source_data = property(_get_source_data, _set_source_data)

    def _convert_wvps(self, filename):
        tmp = mkstemp('.ps')[1]
        try:
            p = Popen((self.wvps_path, filename, tmp), stdout=PIPE)
            p.wait()
        except OSError, detail:
            os.remove(tmp)
            raise ThumbnailException('wvPS error: %s' % detail)
        self._convert_imagemagick(tmp)
        os.remove(tmp)

    def _convert_imagemagick(self, filename):
        tmp = mkstemp('.png')[1]
        if 'crop' in self.opts or 'autocrop' in self.opts:
            x, y = [d * 3 for d in self.requested_size]
        else:
            x, y = self.requested_size
        try:
            p = Popen((self.convert_path, '-size', '%sx%s' % (x, y),
                '-antialias', '-colorspace', 'rgb', '-format', 'PNG24',
                '%s[0]' % filename, tmp), stdout=PIPE)
            p.wait()
        except OSError, detail:
            os.remove(tmp)
            raise ThumbnailException('ImageMagick error: %s' % detail)
        self.source_data = tmp
        os.remove(tmp)

    def _do_generate(self):
        """
        Generates the thumbnail image.

        This a semi-private method so it isn't directly available to template
        authors if this object is passed to the template context.
        """
        im = self.source_data

        for processor in self.processors:
            im = processor(im, self.requested_size, self.opts)

        self.data = im

        filelike = not isinstance(self.dest, basestring)
        if not filelike:
            dest_extension = os.path.splitext(self.dest)[1][1:]
            format = None
        else:
            dest_extension = None
            format = 'JPEG'
        if (self.source_filetype and self.source_filetype == dest_extension and
                self.source_data == self.data):
            copyfile(self.source, self.dest)
        else:
            try:
                im.save(self.dest, format=format, quality=self.quality,
                        optimize=1)
            except IOError:
                # Try again, without optimization (PIL can't optimize an image
                # larger than ImageFile.MAXBLOCK, which is 64k by default)
                try:
                    im.save(self.dest, format=format, quality=self.quality)
                except IOError, detail:
                    raise ThumbnailException(detail)

        if filelike:
            self.dest.seek(0)

    # Some helpful methods

    def _dimension(self, axis):
        if self.dest is None:
            return None
        return self.data.size[axis]

    def width(self):
        return self._dimension(0)

    def height(self):
        return self._dimension(1)

    def _get_filesize(self):
        if self.dest is None:
            return None
        if not hasattr(self, '_filesize'):
            self._filesize = getsize(self.dest)
        return self._filesize
    filesize = property(_get_filesize)

    def _source_dimension(self, axis):
        if self.source_filetype in ['pdf', 'doc']:
            return None
        else:
            return self.source_data.size[axis]

    def source_width(self):
        return self._source_dimension(0)

    def source_height(self):
        return self._source_dimension(1)

    def _get_source_filesize(self):
        if not hasattr(self, '_source_filesize'):
            self._source_filesize = getsize(self.source)
        return self._source_filesize
    source_filesize = property(_get_source_filesize)

########NEW FILE########
__FILENAME__ = defaults
DEBUG = False
BASEDIR = ''
SUBDIR = ''
PREFIX = ''
QUALITY = 85
CONVERT = '/usr/bin/convert'
WVPS = '/usr/bin/wvPS'
EXTENSION = 'jpg'
PROCESSORS = (
    'sorl.thumbnail.processors.colorspace',
    'sorl.thumbnail.processors.autocrop',
    'sorl.thumbnail.processors.scale_and_crop',
    'sorl.thumbnail.processors.filters',
)

########NEW FILE########
__FILENAME__ = fields
import os.path
from UserDict import DictMixin
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.db.models.fields.files import ImageField, ImageFieldFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.safestring import mark_safe
from django.utils.functional import curry
from django.utils.html import escape
from django.conf import settings

from sorl.thumbnail.base import Thumbnail
from sorl.thumbnail.main import DjangoThumbnail, build_thumbnail_name
from sorl.thumbnail.utils import delete_thumbnails


REQUIRED_ARGS = ('size',)
ALL_ARGS = {
    'size': 'requested_size',
    'options': 'opts',
    'quality': 'quality',
    'basedir': 'basedir',
    'subdir': 'subdir',
    'prefix': 'prefix',
    'extension': 'extension',
}
BASE_ARGS = {
    'size': 'requested_size',
    'options': 'opts',
    'quality': 'quality',
}
TAG_HTML = '<img src="%(src)s" width="%(width)s" height="%(height)s" alt="" />'


class ThumbsDict(object, DictMixin):
    def __init__(self, descriptor):
        super(ThumbsDict, self).__init__()
        self.descriptor = descriptor

    def keys(self):
        return self.descriptor.field.extra_thumbnails.keys()


class LazyThumbs(ThumbsDict):
    def __init__(self, *args, **kwargs):
        super(LazyThumbs, self).__init__(*args, **kwargs)
        self.cached = {}

    def __getitem__(self, key):
        thumb = self.cached.get(key)
        if not thumb:
            args = self.descriptor.field.extra_thumbnails[key]
            thumb = self.descriptor._build_thumbnail(args)
            self.cached[key] = thumb
        return thumb

    def keys(self):
        return self.descriptor.field.extra_thumbnails.keys()


class ThumbTags(ThumbsDict):
    def __getitem__(self, key):
        thumb = self.descriptor.extra_thumbnails[key]
        return self.descriptor._build_thumbnail_tag(thumb)


class BaseThumbnailFieldFile(ImageFieldFile):
    def _build_thumbnail(self, args):
        # Build the DjangoThumbnail kwargs.
        kwargs = {}
        for k, v in args.items():
            kwargs[ALL_ARGS[k]] = v
        # Build the destination filename and return the thumbnail.
        name_kwargs = {}
        for key in ['size', 'options', 'quality', 'basedir', 'subdir',
                    'prefix', 'extension']:
            name_kwargs[key] = args.get(key)
        source = getattr(self.instance, self.field.name)
        dest = build_thumbnail_name(source.name, **name_kwargs)
        return DjangoThumbnail(source, relative_dest=dest, **kwargs)

    def _build_thumbnail_tag(self, thumb):
        opts = dict(src=escape(thumb), width=thumb.width(),
                    height=thumb.height())
        return mark_safe(self.field.thumbnail_tag % opts)

    def _get_extra_thumbnails(self):
        if self.field.extra_thumbnails is None:
            return None
        if not hasattr(self, '_extra_thumbnails'):
            self._extra_thumbnails = LazyThumbs(self)
        return self._extra_thumbnails
    extra_thumbnails = property(_get_extra_thumbnails)

    def _get_extra_thumbnails_tag(self):
        if self.field.extra_thumbnails is None:
            return None
        return ThumbTags(self)
    extra_thumbnails_tag = property(_get_extra_thumbnails_tag)

    def save(self, *args, **kwargs):
        # Optionally generate the thumbnails after the image is saved.
        super(BaseThumbnailFieldFile, self).save(*args, **kwargs)
        if self.field.generate_on_save:
            self.generate_thumbnails()

    def delete(self, *args, **kwargs):
        # Delete any thumbnails too (and not just ones defined here in case
        # the {% thumbnail %} tag was used or the thumbnail sizes changed).
        relative_source_path = getattr(self.instance, self.field.name).name
        delete_thumbnails(relative_source_path)
        super(BaseThumbnailFieldFile, self).delete(*args, **kwargs)

    def generate_thumbnails(self):
        # Getting the thumbs generates them.
        if self.extra_thumbnails:
            self.extra_thumbnails.values()


class ImageWithThumbnailsFieldFile(BaseThumbnailFieldFile):
    def _get_thumbnail(self):
        return self._build_thumbnail(self.field.thumbnail)
    thumbnail = property(_get_thumbnail)

    def _get_thumbnail_tag(self):
        return self._build_thumbnail_tag(self.thumbnail)
    thumbnail_tag = property(_get_thumbnail_tag)

    def generate_thumbnails(self, *args, **kwargs):
        self.thumbnail.generate()
        Super = super(ImageWithThumbnailsFieldFile, self)
        return Super.generate_thumbnails(*args, **kwargs)


class ThumbnailFieldFile(BaseThumbnailFieldFile):
    def save(self, name, content, *args, **kwargs):
        new_content = StringIO()
        # Build the Thumbnail kwargs.
        thumbnail_kwargs = {}
        for k, argk in BASE_ARGS.items():
            if not k in self.field.thumbnail:
                continue
            thumbnail_kwargs[argk] = self.field.thumbnail[k]
        Thumbnail(source=content, dest=new_content, **thumbnail_kwargs)
        new_content = SimpleUploadedFile(name, new_content.read(),
                                         content.content_type)
        super(ThumbnailFieldFile, self).save(name, new_content, *args,
                                             **kwargs)

    def _get_thumbnail_tag(self):
        opts = dict(src=escape(self.url), width=self.width,
                    height=self.height)
        return mark_safe(self.field.thumbnail_tag % opts)
    thumbnail_tag = property(_get_thumbnail_tag)


class BaseThumbnailField(ImageField):
    def __init__(self, *args, **kwargs):
        # The new arguments for this field aren't explicitly defined so that
        # users can still use normal ImageField positional arguments.
        self.extra_thumbnails = kwargs.pop('extra_thumbnails', None)
        self.thumbnail_tag = kwargs.pop('thumbnail_tag', TAG_HTML)
        self.generate_on_save = kwargs.pop('generate_on_save', False)

        super(BaseThumbnailField, self).__init__(*args, **kwargs)
        _verify_thumbnail_attrs(self.thumbnail)
        if self.extra_thumbnails:
            for extra, attrs in self.extra_thumbnails.items():
                name = "%r of 'extra_thumbnails'"
                _verify_thumbnail_attrs(attrs, name)


class ImageWithThumbnailsField(BaseThumbnailField):
    """
    photo = ImageWithThumbnailsField(
        upload_to='uploads',
        thumbnail={'size': (80, 80), 'options': ('crop', 'upscale'),
                   'extension': 'png'},
        extra_thumbnails={
            'admin': {'size': (70, 50), 'options': ('sharpen',)},
        }
    )
    """
    attr_class = ImageWithThumbnailsFieldFile

    def __init__(self, *args, **kwargs):
        self.thumbnail = kwargs.pop('thumbnail', None)
        super(ImageWithThumbnailsField, self).__init__(*args, **kwargs)


class ThumbnailField(BaseThumbnailField):
    """
    avatar = ThumbnailField(
        upload_to='uploads',
        size=(200, 200),
        options=('crop',),
        extra_thumbnails={
            'admin': {'size': (70, 50), 'options': (crop, 'sharpen')},
        }
    )
    """
    attr_class = ThumbnailFieldFile

    def __init__(self, *args, **kwargs):
        self.thumbnail = {}
        for attr in ALL_ARGS:
            if attr in kwargs:
                self.thumbnail[attr] = kwargs.pop(attr)
        super(ThumbnailField, self).__init__(*args, **kwargs)


def _verify_thumbnail_attrs(attrs, name="'thumbnail'"):
    for arg in REQUIRED_ARGS:
        if arg not in attrs:
            raise TypeError('Required attr %r missing in %s arg' % (arg, name))
    for attr in attrs:
        if attr not in ALL_ARGS:
            raise TypeError('Invalid attr %r found in %s arg' % (arg, name))

########NEW FILE########
__FILENAME__ = main
import os

from django.conf import settings
from django.utils.encoding import iri_to_uri, force_unicode

from sorl.thumbnail.base import Thumbnail
from sorl.thumbnail.processors import dynamic_import
from sorl.thumbnail import defaults


def get_thumbnail_setting(setting, override=None):
    """
    Get a thumbnail setting from Django settings module, falling back to the
    default.

    If override is not None, it will be used instead of the setting.
    """
    if override is not None:
        return override
    if hasattr(settings, 'THUMBNAIL_%s' % setting):
        return getattr(settings, 'THUMBNAIL_%s' % setting)
    else:
        return getattr(defaults, setting)


def build_thumbnail_name(source_name, size, options=None,
                         quality=None, basedir=None, subdir=None, prefix=None,
                         extension=None):
    quality = get_thumbnail_setting('QUALITY', quality)
    basedir = get_thumbnail_setting('BASEDIR', basedir)
    subdir = get_thumbnail_setting('SUBDIR', subdir)
    prefix = get_thumbnail_setting('PREFIX', prefix)
    extension = get_thumbnail_setting('EXTENSION', extension)
    path, filename = os.path.split(source_name)
    basename, ext = os.path.splitext(filename)
    name = '%s%s' % (basename, ext.replace(os.extsep, '_'))
    size = '%sx%s' % tuple(size)

    # Handle old list format for opts.
    options = options or {}
    if isinstance(options, (list, tuple)):
        options = dict([(opt, None) for opt in options])

    opts = options.items()
    opts.sort()   # options are sorted so the filename is consistent
    opts = ['%s_' % (v is not None and '%s-%s' % (k, v) or k)
            for k, v in opts]
    opts = ''.join(opts)
    extension = extension and '.%s' % extension
    thumbnail_filename = '%s%s_%s_%sq%s%s' % (prefix, name, size, opts,
                                              quality, extension)
    return os.path.join(basedir, path, subdir, thumbnail_filename)


class DjangoThumbnail(Thumbnail):
    def __init__(self, relative_source, requested_size, opts=None,
                 quality=None, basedir=None, subdir=None, prefix=None,
                 relative_dest=None, processors=None, extension=None):
        relative_source = force_unicode(relative_source)
        # Set the absolute filename for the source file
        source = self._absolute_path(relative_source)

        quality = get_thumbnail_setting('QUALITY', quality)
        convert_path = get_thumbnail_setting('CONVERT')
        wvps_path = get_thumbnail_setting('WVPS')
        if processors is None:
            processors = dynamic_import(get_thumbnail_setting('PROCESSORS'))

        # Call super().__init__ now to set the opts attribute. generate() won't
        # get called because we are not setting the dest attribute yet.
        super(DjangoThumbnail, self).__init__(source, requested_size,
            opts=opts, quality=quality, convert_path=convert_path,
            wvps_path=wvps_path, processors=processors)

        # Get the relative filename for the thumbnail image, then set the
        # destination filename
        if relative_dest is None:
            relative_dest = \
               self._get_relative_thumbnail(relative_source, basedir=basedir,
                                            subdir=subdir, prefix=prefix,
                                            extension=extension)
        filelike = not isinstance(relative_dest, basestring)
        if filelike:
            self.dest = relative_dest
        else: 
            self.dest = self._absolute_path(relative_dest)

        # Call generate now that the dest attribute has been set
        self.generate()

        # Set the relative & absolute url to the thumbnail
        if not filelike:
            self.relative_url = \
                iri_to_uri('/'.join(relative_dest.split(os.sep)))
            self.absolute_url = '%s%s' % (settings.MEDIA_URL,
                                          self.relative_url)

    def _get_relative_thumbnail(self, relative_source,
                                basedir=None, subdir=None, prefix=None,
                                extension=None):
        """
        Returns the thumbnail filename including relative path.
        """
        return build_thumbnail_name(relative_source, self.requested_size,
                                    self.opts, self.quality, basedir, subdir,
                                    prefix, extension)

    def _absolute_path(self, filename):
        absolute_filename = os.path.join(settings.MEDIA_ROOT, filename)
        return absolute_filename.encode(settings.FILE_CHARSET)

    def __unicode__(self):
        return self.absolute_url

########NEW FILE########
__FILENAME__ = thumbnail_cleanup
import os
import re
from django.db import models
from django.conf import settings
from django.core.management.base import NoArgsCommand
from sorl.thumbnail.main import get_thumbnail_setting


try:
    set
except NameError:
    from sets import Set as set     # For Python 2.3

thumb_re = re.compile(r'^%s(.*)_\d{1,}x\d{1,}_[-\w]*q([1-9]\d?|100)\.jpg' %
                      get_thumbnail_setting('PREFIX'))


def get_thumbnail_path(path):
    basedir = get_thumbnail_setting('BASEDIR')
    subdir = get_thumbnail_setting('SUBDIR')
    return os.path.join(basedir, path, subdir)


def clean_up():
    paths = set()
    for app in models.get_apps():
        app_name = app.__name__.split('.')[-2]
        model_list = models.get_models(app)
        for model in model_list:
            for field in model._meta.fields:
                if isinstance(field, models.ImageField):
                    #TODO: take care of date formatted and callable upload_to.
                    if (not callable(field.upload_to) and
                            field.upload_to.find("%") == -1):
                        paths = paths.union((field.upload_to,))
    paths = list(paths)
    for path in paths:
        thumbnail_path = get_thumbnail_path(path)
        try:
            file_list = os.listdir(os.path.join(settings.MEDIA_ROOT,
                                                thumbnail_path))
        except OSError:
            continue # Dir doesn't exists, no thumbnails here.
        for fn in file_list:
            m = thumb_re.match(fn)
            if m:
                # Due to that the naming of thumbnails replaces the dot before
                # extension with an underscore we have 2 possibilities for the
                # original filename. If either present we do not delete
                # suspected thumbnail.
                # org_fn is the expected original filename w/o extension
                # org_fn_alt is the expected original filename with extension
                org_fn = m.group(1)
                org_fn_exists = os.path.isfile(
                            os.path.join(settings.MEDIA_ROOT, path, org_fn))

                usc_pos = org_fn.rfind("_")
                if usc_pos != -1:
                    org_fn_alt = "%s.%s" % (org_fn[0:usc_pos],
                                            org_fn[usc_pos+1:])
                    org_fn_alt_exists = os.path.isfile(
                        os.path.join(settings.MEDIA_ROOT, path, org_fn_alt))
                else:
                    org_fn_alt_exists = False
                if not org_fn_exists and not org_fn_alt_exists:
                    del_me = os.path.join(settings.MEDIA_ROOT,
                                          thumbnail_path, fn)
                    os.remove(del_me)


class Command(NoArgsCommand):
    help = "Deletes thumbnails that no longer have an original file."
    requires_model_validation = False

    def handle_noargs(self, **options):
        clean_up()

########NEW FILE########
__FILENAME__ = models
# Needs a models.py file so that tests are picked up.
########NEW FILE########
__FILENAME__ = processors
from PIL import Image, ImageFilter, ImageChops


def dynamic_import(names):
    imported = []
    for name in names:
        modname, attrname = name.rsplit('.', 1)
        mod = __import__(modname, {}, {}, [''])
        imported.append(getattr(mod, attrname))
    return imported


def get_valid_options(processors):
    """
    Returns a list containing unique valid options from a list of processors
    in correct order.
    """
    valid_options = []
    for processor in processors:
        if hasattr(processor, 'valid_options'):
            valid_options.extend([opt for opt in processor.valid_options
                                  if opt not in valid_options])
    return valid_options


def colorspace(im, requested_size, opts):
    if 'bw' in opts and im.mode != "L":
        im = im.convert("L")
    elif im.mode not in ("L", "RGB", "RGBA"):
        im = im.convert("RGB")
    return im
colorspace.valid_options = ('bw',)


def autocrop(im, requested_size, opts):
    if 'autocrop' in opts:
        bw = im.convert("1")
        bw = bw.filter(ImageFilter.MedianFilter)
        # white bg
        bg = Image.new("1", im.size, 255)
        diff = ImageChops.difference(bw, bg)
        bbox = diff.getbbox()
        if bbox:
            im = im.crop(bbox)
    return im
autocrop.valid_options = ('autocrop',)


def scale_and_crop(im, requested_size, opts):
    x, y   = [float(v) for v in im.size]
    xr, yr = [float(v) for v in requested_size]

    if 'crop' in opts or 'max' in opts:
        r = max(xr/x, yr/y)
    else:
        r = min(xr/x, yr/y)

    if r < 1.0 or (r > 1.0 and 'upscale' in opts):
        im = im.resize((int(x*r), int(y*r)), resample=Image.ANTIALIAS)

    if 'crop' in opts:
        x, y   = [float(v) for v in im.size]
        ex, ey = (x-min(x, xr))/2, (y-min(y, yr))/2
        if ex or ey:
            im = im.crop((int(ex), int(ey), int(x-ex), int(y-ey)))
    return im
scale_and_crop.valid_options = ('crop', 'upscale', 'max')


def filters(im, requested_size, opts):
    if 'detail' in opts:
        im = im.filter(ImageFilter.DETAIL)
    if 'sharpen' in opts:
        im = im.filter(ImageFilter.SHARPEN)
    return im
filters.valid_options = ('detail', 'sharpen')

########NEW FILE########
__FILENAME__ = thumbnail
import re
import math
from django.template import Library, Node, Variable, VariableDoesNotExist, TemplateSyntaxError
from django.conf import settings
from django.utils.encoding import force_unicode
from sorl.thumbnail.main import DjangoThumbnail, get_thumbnail_setting
from sorl.thumbnail.processors import dynamic_import, get_valid_options
from sorl.thumbnail.utils import split_args

register = Library()

size_pat = re.compile(r'(\d+)x(\d+)$')

filesize_formats = ['k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
filesize_long_formats = {
    'k': 'kilo', 'M': 'mega', 'G': 'giga', 'T': 'tera', 'P': 'peta',
    'E': 'exa', 'Z': 'zetta', 'Y': 'yotta'
}

try:
    PROCESSORS = dynamic_import(get_thumbnail_setting('PROCESSORS'))
    VALID_OPTIONS = get_valid_options(PROCESSORS)
except:
    if get_thumbnail_setting('DEBUG'):
        raise
    else:
        PROCESSORS = []
        VALID_OPTIONS = []
TAG_SETTINGS = ['quality'] 

class ThumbnailNode(Node):
    def __init__(self, source_var, size_var, opts=None,
                 context_name=None, **kwargs):
        self.source_var = source_var
        self.size_var = size_var
        self.opts = opts
        self.context_name = context_name
        self.kwargs = kwargs

    def render(self, context):
        # Note that this isn't a global constant because we need to change the
        # value for tests.
        DEBUG = get_thumbnail_setting('DEBUG')
        try:
            # A file object will be allowed in DjangoThumbnail class
            relative_source = self.source_var.resolve(context)
        except VariableDoesNotExist:
            if DEBUG:
                raise VariableDoesNotExist("Variable '%s' does not exist." %
                        self.source_var)
            else:
                relative_source = None
        try:
            requested_size = self.size_var.resolve(context)
        except VariableDoesNotExist:
            if DEBUG:
                raise TemplateSyntaxError("Size argument '%s' is not a"
                        " valid size nor a valid variable." % self.size_var)
            else:
                requested_size = None
        # Size variable can be either a tuple/list of two integers or a valid
        # string, only the string is checked.
        else:
            if isinstance(requested_size, basestring):
                m = size_pat.match(requested_size)
                if m:
                    requested_size = (int(m.group(1)), int(m.group(2)))
                elif DEBUG:
                    raise TemplateSyntaxError("Variable '%s' was resolved but "
                            "'%s' is not a valid size." %
                            (self.size_var, requested_size))
                else:
                    requested_size = None
        if relative_source is None or requested_size is None:
            thumbnail = ''
        else:
            try:
                kwargs = {}
                for key, value in self.kwargs.items():
                    kwargs[key] = value.resolve(context)
                opts = dict([(k, v and v.resolve(context))
                             for k, v in self.opts.items()])
                thumbnail = DjangoThumbnail(relative_source, requested_size,
                                opts=opts, processors=PROCESSORS, **kwargs)
            except:
                if DEBUG:
                    raise
                else:
                    thumbnail = ''
        # Return the thumbnail class, or put it on the context
        if self.context_name is None:
            return thumbnail
        # We need to get here so we don't have old values in the context
        # variable.
        context[self.context_name] = thumbnail
        return ''


def thumbnail(parser, token):
    """
    Creates a thumbnail of for an ImageField.

    To just output the absolute url to the thumbnail::

        {% thumbnail image 80x80 %}

    After the image path and dimensions, you can put any options::

        {% thumbnail image 80x80 quality=95 crop %}

    To put the DjangoThumbnail class on the context instead of just rendering
    the absolute url, finish the tag with ``as [context_var_name]``::

        {% thumbnail image 80x80 as thumb %}
        {{ thumb.width }} x {{ thumb.height }}
    """
    args = token.split_contents()
    tag = args[0]
    # Check to see if we're setting to a context variable.
    if len(args) > 4 and args[-2] == 'as':
        context_name = args[-1]
        args = args[:-2]
    else:
        context_name = None

    if len(args) < 3:
        raise TemplateSyntaxError("Invalid syntax. Expected "
            "'{%% %s source size [option1 option2 ...] %%}' or "
            "'{%% %s source size [option1 option2 ...] as variable %%}'" %
            (tag, tag))

    # Get the source image path and requested size.
    source_var = parser.compile_filter(args[1])
    # Since we changed to allow filters we have to make an exception for our syntax
    m = size_pat.match(args[2])
    if m:
        args[2] = '"%s"' % args[2]
    size_var = parser.compile_filter(args[2])

    # Get the options.
    args_list = split_args(args[3:]).items()

    # Check the options.
    opts = {}
    kwargs = {} # key,values here override settings and defaults

    for arg, value in args_list:
        value = value and parser.compile_filter(value)
        if arg in TAG_SETTINGS and value is not None:
            kwargs[str(arg)] = value
            continue
        if arg in VALID_OPTIONS:
            opts[arg] = value
        else:
            raise TemplateSyntaxError("'%s' tag received a bad argument: "
                                      "'%s'" % (tag, arg))
    return ThumbnailNode(source_var, size_var, opts=opts,
            context_name=context_name, **kwargs)


def filesize(bytes, format='auto1024'):
    """
    Returns the number of bytes in either the nearest unit or a specific unit
    (depending on the chosen format method).

    Acceptable formats are:

    auto1024, auto1000
      convert to the nearest unit, appending the abbreviated unit name to the
      string (e.g. '2 KiB' or '2 kB').
      auto1024 is the default format.
    auto1024long, auto1000long
      convert to the nearest multiple of 1024 or 1000, appending the correctly
      pluralized unit name to the string (e.g. '2 kibibytes' or '2 kilobytes').
    kB, MB, GB, TB, PB, EB, ZB or YB
      convert to the exact unit (using multiples of 1000).
    KiB, MiB, GiB, TiB, PiB, EiB, ZiB or YiB
      convert to the exact unit (using multiples of 1024).

    The auto1024 and auto1000 formats return a string, appending the correct
    unit to the value. All other formats return the floating point value.

    If an invalid format is specified, the bytes are returned unchanged.
    """
    format_len = len(format)
    # Check for valid format
    if format_len in (2, 3):
        if format_len == 3 and format[0] == 'K':
            format = 'k%s' % format[1:]
        if not format[-1] == 'B' or format[0] not in filesize_formats:
            return bytes
        if format_len == 3 and format[1] != 'i':
            return bytes
    elif format not in ('auto1024', 'auto1000',
                        'auto1024long', 'auto1000long'):
        return bytes
    # Check for valid bytes
    try:
        bytes = long(bytes)
    except (ValueError, TypeError):
        return bytes

    # Auto multiple of 1000 or 1024
    if format.startswith('auto'):
        if format[4:8] == '1000':
            base = 1000
        else:
            base = 1024
        logarithm = bytes and math.log(bytes, base) or 0
        index = min(int(logarithm)-1, len(filesize_formats)-1)
        if index >= 0:
            if base == 1000:
                bytes = bytes and bytes / math.pow(1000, index+1)
            else:
                bytes = bytes >> (10*(index))
                bytes = bytes and bytes / 1024.0
            unit = filesize_formats[index]
        else:
            # Change the base to 1000 so the unit will just output 'B' not 'iB'
            base = 1000
            unit = ''
        if bytes >= 10 or ('%.1f' % bytes).endswith('.0'):
            bytes = '%.0f' % bytes
        else:
            bytes = '%.1f' % bytes
        if format.endswith('long'):
            unit = filesize_long_formats.get(unit, '')
            if base == 1024 and unit:
                unit = '%sbi' % unit[:2]
            unit = '%sbyte%s' % (unit, bytes!='1' and 's' or '')
        else:
            unit = '%s%s' % (base == 1024 and unit.upper() or unit,
                             base == 1024 and 'iB' or 'B')

        return '%s %s' % (bytes, unit)

    if bytes == 0:
        return bytes
    base = filesize_formats.index(format[0]) + 1
    # Exact multiple of 1000
    if format_len == 2:
        return bytes / (1000.0**base)
    # Exact multiple of 1024
    elif format_len == 3:
        bytes = bytes >> (10*(base-1))
        return bytes / 1024.0


register.tag(thumbnail)
register.filter(filesize)

########NEW FILE########
__FILENAME__ = base
import unittest
import os
from PIL import Image
from django.conf import settings
from sorl.thumbnail.base import Thumbnail

try:
    set
except NameError:
    from sets import Set as set     # For Python 2.3

def get_default_settings():
    from sorl.thumbnail import defaults
    def_settings = {}
    for key in dir(defaults):
        if key == key.upper() and key not in ['WVPS', 'CONVERT']:
            def_settings[key] = getattr(defaults, key)
    return def_settings


DEFAULT_THUMBNAIL_SETTINGS = get_default_settings()
RELATIVE_PIC_NAME = "sorl-thumbnail-test_source.jpg"
PIC_NAME = os.path.join(settings.MEDIA_ROOT, RELATIVE_PIC_NAME)
THUMB_NAME = os.path.join(settings.MEDIA_ROOT, "sorl-thumbnail-test_%02d.jpg")
PIC_SIZE = (800, 600)



class ChangeSettings:
    def __init__(self):
        self.default_settings = DEFAULT_THUMBNAIL_SETTINGS.copy()

    def change(self, override=None):
        if override is not None:
            self.default_settings.update(override)
        for setting, default in self.default_settings.items():
            settings_s = 'THUMBNAIL_%s' % setting
            self_s = 'original_%s' % setting
            if hasattr(settings, settings_s) and not hasattr(self, self_s):
                setattr(self, self_s, getattr(settings, settings_s))
            if hasattr(settings, settings_s) or \
               default != DEFAULT_THUMBNAIL_SETTINGS[setting]:
                setattr(settings, settings_s, default)

    def revert(self):
        for setting in self.default_settings:
            settings_s = 'THUMBNAIL_%s' % setting
            self_s = 'original_%s' % setting
            if hasattr(self, self_s):
                setattr(settings, settings_s, getattr(self, self_s))
                delattr(self, self_s)


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.images_to_delete = set()
        # Create the test image
        Image.new('RGB', PIC_SIZE).save(PIC_NAME, 'JPEG')
        self.images_to_delete.add(PIC_NAME)
        # Change settings so we know they will be constant
        self.change_settings = ChangeSettings()
        self.change_settings.change()

    def verify_thumbnail(self, expected_size, thumbnail=None,
                         expected_filename=None, expected_mode=None):
        assert thumbnail is not None or expected_filename is not None, \
            'verify_thumbnail should be passed at least a thumbnail or an' \
            'expected filename.'

        if thumbnail is not None:
            # Verify that the templatetag method returned a Thumbnail instance
            self.assertTrue(isinstance(thumbnail, Thumbnail))
            thumb_name = thumbnail.dest
        else:
            thumb_name = expected_filename

        if isinstance(thumb_name, basestring):
            # Verify that the thumbnail file exists
            self.assert_(os.path.isfile(thumb_name),
                         'Thumbnail file not found')

            # Remember to delete the file
            self.images_to_delete.add(thumb_name)

            # If we got an expected_filename, check that it is right
            if expected_filename is not None and thumbnail is not None:
                self.assertEqual(thumbnail.dest, expected_filename)

        image = Image.open(thumb_name)

        # Verify the thumbnail has the expected dimensions
        self.assertEqual(image.size, expected_size)

        if expected_mode is not None:
            self.assertEqual(image.mode, expected_mode)

    def tearDown(self):
        # Remove all the files that have been created
        for image in self.images_to_delete:
            try:
                os.remove(image)
            except:
                pass
        # Change settings back to original
        self.change_settings.revert()


########NEW FILE########
__FILENAME__ = classes
#! -*- coding: utf-8 -*-
import unittest
import os
import time
from StringIO import StringIO

from PIL import Image
from django.conf import settings

from sorl.thumbnail.base import Thumbnail
from sorl.thumbnail.main import DjangoThumbnail, get_thumbnail_setting
from sorl.thumbnail.processors import dynamic_import, get_valid_options
from sorl.thumbnail.tests.base import BaseTest, RELATIVE_PIC_NAME, PIC_NAME, THUMB_NAME, PIC_SIZE


class ThumbnailTest(BaseTest):
    def testThumbnails(self):
        # Thumbnail
        thumb = Thumbnail(source=PIC_NAME, dest=THUMB_NAME % 1,
                          requested_size=(240, 240))
        self.verify_thumbnail((240, 180), thumb)

        # Cropped thumbnail
        thumb = Thumbnail(source=PIC_NAME, dest=THUMB_NAME % 2,
                          requested_size=(240, 240), opts=['crop'])
        self.verify_thumbnail((240, 240), thumb)

        # Thumbnail with altered JPEG quality
        thumb = Thumbnail(source=PIC_NAME, dest=THUMB_NAME % 3,
                          requested_size=(240, 240), quality=95)
        self.verify_thumbnail((240, 180), thumb)

    def testRegeneration(self):
        # Create thumbnail
        thumb_name = THUMB_NAME % 4
        thumb_size = (240, 240)
        thumb = Thumbnail(source=PIC_NAME, dest=thumb_name,
                          requested_size=thumb_size)
        self.images_to_delete.add(thumb_name)
        thumb_mtime = os.path.getmtime(thumb_name)
        time.sleep(1)

        # Create another instance, shouldn't generate a new thumb
        thumb = Thumbnail(source=PIC_NAME, dest=thumb_name,
                          requested_size=thumb_size)
        self.assertEqual(os.path.getmtime(thumb_name), thumb_mtime)

        # Recreate the source image, then see if a new thumb is generated
        Image.new('RGB', PIC_SIZE).save(PIC_NAME, 'JPEG')
        thumb = Thumbnail(source=PIC_NAME, dest=thumb_name,
                          requested_size=thumb_size)
        self.assertNotEqual(os.path.getmtime(thumb_name), thumb_mtime)

    def testFilelikeDest(self):
        # Thumbnail
        filelike_dest = StringIO()
        thumb = Thumbnail(source=PIC_NAME, dest=filelike_dest,
                          requested_size=(240, 240))
        self.verify_thumbnail((240, 180), thumb)

    def testRGBA(self):
        # RGBA image
        rgba_pic_name = os.path.join(settings.MEDIA_ROOT,
                                     'sorl-thumbnail-test_rgba_source.png')
        Image.new('RGBA', PIC_SIZE).save(rgba_pic_name)
        self.images_to_delete.add(rgba_pic_name)
        # Create thumb and verify it's still RGBA
        rgba_thumb_name = os.path.join(settings.MEDIA_ROOT,
                                       'sorl-thumbnail-test_rgba_dest.png')
        thumb = Thumbnail(source=rgba_pic_name, dest=rgba_thumb_name,
                          requested_size=(240, 240))
        self.verify_thumbnail((240, 180), thumb, expected_mode='RGBA')


class DjangoThumbnailTest(BaseTest):
    def setUp(self):
        super(DjangoThumbnailTest, self).setUp()
        # Add another source image in a sub-directory for testing subdir and
        # basedir.
        self.sub_dir = os.path.join(settings.MEDIA_ROOT, 'test_thumbnail')
        try:
            os.mkdir(self.sub_dir)
        except OSError:
            pass
        self.pic_subdir = os.path.join(self.sub_dir, RELATIVE_PIC_NAME)
        Image.new('RGB', PIC_SIZE).save(self.pic_subdir, 'JPEG')
        self.images_to_delete.add(self.pic_subdir)

    def testFilenameGeneration(self):
        basename = RELATIVE_PIC_NAME.replace('.', '_')
        # Basic filename
        thumb = DjangoThumbnail(relative_source=RELATIVE_PIC_NAME,
                                requested_size=(240, 120))
        expected = os.path.join(settings.MEDIA_ROOT, basename)
        expected += '_240x120_q85.jpg'
        self.verify_thumbnail((160, 120), thumb, expected_filename=expected)

        # Changed quality and cropped
        thumb = DjangoThumbnail(relative_source=RELATIVE_PIC_NAME,
                                requested_size=(240, 120), opts=['crop'],
                                quality=95)
        expected = os.path.join(settings.MEDIA_ROOT, basename)
        expected += '_240x120_crop_q95.jpg'
        self.verify_thumbnail((240, 120), thumb, expected_filename=expected)

        # All options on
        processors = dynamic_import(get_thumbnail_setting('PROCESSORS'))
        valid_options = get_valid_options(processors)

        thumb = DjangoThumbnail(relative_source=RELATIVE_PIC_NAME,
                                requested_size=(240, 120), opts=valid_options)
        expected = (os.path.join(settings.MEDIA_ROOT, basename) + '_240x120_'
                    'autocrop_bw_crop_detail_max_sharpen_upscale_q85.jpg')
        self.verify_thumbnail((240, 120), thumb, expected_filename=expected)

        # Different basedir
        basedir = 'sorl-thumbnail-test-basedir'
        self.change_settings.change({'BASEDIR': basedir})
        thumb = DjangoThumbnail(relative_source=self.pic_subdir,
                                requested_size=(240, 120))
        expected = os.path.join(basedir, self.sub_dir, basename)
        expected += '_240x120_q85.jpg'
        self.verify_thumbnail((160, 120), thumb, expected_filename=expected)
        # Different subdir
        self.change_settings.change({'BASEDIR': '', 'SUBDIR': 'subdir'})
        thumb = DjangoThumbnail(relative_source=self.pic_subdir,
                                requested_size=(240, 120))
        expected = os.path.join(settings.MEDIA_ROOT,
                                os.path.basename(self.sub_dir), 'subdir',
                                basename)
        expected += '_240x120_q85.jpg'
        self.verify_thumbnail((160, 120), thumb, expected_filename=expected)
        # Different prefix
        self.change_settings.change({'SUBDIR': '', 'PREFIX': 'prefix-'})
        thumb = DjangoThumbnail(relative_source=self.pic_subdir,
                                requested_size=(240, 120))
        expected = os.path.join(self.sub_dir, 'prefix-' + basename)
        expected += '_240x120_q85.jpg'
        self.verify_thumbnail((160, 120), thumb, expected_filename=expected)

    def testAlternateExtension(self):
        basename = RELATIVE_PIC_NAME.replace('.', '_')
        # Control JPG
        thumb = DjangoThumbnail(relative_source=RELATIVE_PIC_NAME,
                                requested_size=(240, 120))
        expected = os.path.join(settings.MEDIA_ROOT, basename)
        expected += '_240x120_q85.jpg'
        expected_jpg = expected
        self.verify_thumbnail((160, 120), thumb, expected_filename=expected)
        # Test PNG
        thumb = DjangoThumbnail(relative_source=RELATIVE_PIC_NAME,
                                requested_size=(240, 120), extension='png')
        expected = os.path.join(settings.MEDIA_ROOT, basename)
        expected += '_240x120_q85.png'
        self.verify_thumbnail((160, 120), thumb, expected_filename=expected)
        # Compare the file size to make sure it's not just saving as a JPG with
        # a different extension.
        self.assertNotEqual(os.path.getsize(expected_jpg),
                            os.path.getsize(expected))

    def testUnicodeName(self):
        unicode_name = 'sorl-thumbnail-ążśź_source.jpg'
        unicode_path = os.path.join(settings.MEDIA_ROOT, unicode_name)
        Image.new('RGB', PIC_SIZE).save(unicode_path)
        self.images_to_delete.add(unicode_path)
        thumb = DjangoThumbnail(relative_source=unicode_name,
                                requested_size=(240, 120))
        base_name = unicode_name.replace('.', '_')
        expected = os.path.join(settings.MEDIA_ROOT,
                                base_name + '_240x120_q85.jpg')
        self.verify_thumbnail((160, 120), thumb, expected_filename=expected)

    def tearDown(self):
        super(DjangoThumbnailTest, self).tearDown()
        subdir = os.path.join(self.sub_dir, 'subdir')
        if os.path.exists(subdir):
            os.rmdir(subdir)
        os.rmdir(self.sub_dir)

########NEW FILE########
__FILENAME__ = fields
import os.path

from django.db import models
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from sorl.thumbnail.fields import ImageWithThumbnailsField, ThumbnailField
from sorl.thumbnail.tests.base import BaseTest, RELATIVE_PIC_NAME, PIC_NAME

thumbnail = {
    'size': (50, 50)
}
extra_thumbnails = {
    'admin': {
        'size': (30, 30),
        'options': ('crop',),
    }
}
extension_thumbnail = thumbnail.copy()
extension_thumbnail['extension'] = 'png'

# Temporary models for field_tests
class TestThumbnailFieldModel(models.Model):
    avatar = ThumbnailField(upload_to='test', size=(300, 300))
    photo = ImageWithThumbnailsField(upload_to='test', thumbnail=thumbnail,
                                     extra_thumbnails=extra_thumbnails)


class TestThumbnailFieldExtensionModel(models.Model):
    photo = ImageWithThumbnailsField(upload_to='test',
                                     thumbnail=extension_thumbnail,
                                     extra_thumbnails=extra_thumbnails)


class TestThumbnailFieldGenerateModel(models.Model):
    photo = ImageWithThumbnailsField(upload_to='test', thumbnail=thumbnail,
                                     extra_thumbnails=extra_thumbnails,
                                     generate_on_save=True)


class FieldTest(BaseTest):
    """
    Test the base field functionality. These use an ImageWithThumbnailsField
    but all the functionality tested is from BaseThumbnailField.
    """
    def test_extra_thumbnails(self):
        model = TestThumbnailFieldModel(photo=RELATIVE_PIC_NAME)
        self.assertTrue('admin' in model.photo.extra_thumbnails)
        thumb = model.photo.extra_thumbnails['admin']
        tag = model.photo.extra_thumbnails_tag['admin']
        expected_filename = os.path.join(settings.MEDIA_ROOT,
            'sorl-thumbnail-test_source_jpg_30x30_crop_q85.jpg')
        self.verify_thumbnail((30, 30), thumb, expected_filename)
        expected_tag = '<img src="%s" width="30" height="30" alt="" />' % \
            '/'.join((settings.MEDIA_URL.rstrip('/'),
                      'sorl-thumbnail-test_source_jpg_30x30_crop_q85.jpg'))
        self.assertEqual(tag, expected_tag)

    def test_extension(self):
        model = TestThumbnailFieldExtensionModel(photo=RELATIVE_PIC_NAME)
        thumb = model.photo.thumbnail
        tag = model.photo.thumbnail_tag
        expected_filename = os.path.join(settings.MEDIA_ROOT,
            'sorl-thumbnail-test_source_jpg_50x50_q85.png')
        self.verify_thumbnail((50, 37), thumb, expected_filename)
        expected_tag = '<img src="%s" width="50" height="37" alt="" />' % \
            '/'.join((settings.MEDIA_URL.rstrip('/'),
                      'sorl-thumbnail-test_source_jpg_50x50_q85.png'))
        self.assertEqual(tag, expected_tag)

    def test_delete_thumbnails(self):
        model = TestThumbnailFieldModel(photo=RELATIVE_PIC_NAME)
        thumb_file = model.photo.thumbnail.dest
        open(thumb_file, 'wb').close()
        self.assert_(os.path.exists(thumb_file))
        model.photo.delete(save=False)
        self.assertFalse(os.path.exists(thumb_file))

    def test_generate_on_save(self):
        main_thumb = os.path.join(settings.MEDIA_ROOT, 'test',
                        'sorl-thumbnail-test_source_jpg_50x50_q85.jpg')
        admin_thumb = os.path.join(settings.MEDIA_ROOT, 'test',
                        'sorl-thumbnail-test_source_jpg_30x30_crop_q85.jpg')
        self.images_to_delete.add(main_thumb)
        self.images_to_delete.add(admin_thumb)
        # Default setting is to only generate when the thumbnail is used.
        model = TestThumbnailFieldModel()
        source = SimpleUploadedFile('_', open(PIC_NAME).read())
        model.photo.save(RELATIVE_PIC_NAME, source, save=False)
        self.images_to_delete.add(model.photo.path)
        self.assertFalse(os.path.exists(main_thumb))
        self.assertFalse(os.path.exists(admin_thumb))
        os.remove(model.photo.path)
        # But it's easy to set it up the other way...
        model = TestThumbnailFieldGenerateModel()
        source = SimpleUploadedFile('_', open(PIC_NAME).read())
        model.photo.save(RELATIVE_PIC_NAME, source, save=False)
        self.assert_(os.path.exists(main_thumb))
        self.assert_(os.path.exists(admin_thumb))


class ImageWithThumbnailsFieldTest(BaseTest):
    def test_thumbnail(self):
        model = TestThumbnailFieldModel(photo=RELATIVE_PIC_NAME)
        thumb = model.photo.thumbnail
        tag = model.photo.thumbnail_tag
        base_name = RELATIVE_PIC_NAME.replace('.', '_')
        expected_filename = os.path.join(settings.MEDIA_ROOT,
                                         '%s_50x50_q85.jpg' % base_name)
        self.verify_thumbnail((50, 37), thumb, expected_filename)
        expected_tag = ('<img src="%s" width="50" height="37" alt="" />' %
                        '/'.join([settings.MEDIA_URL.rstrip('/'),
                                  '%s_50x50_q85.jpg' % base_name]))
        self.assertEqual(tag, expected_tag)


class ThumbnailFieldTest(BaseTest):
    def test_thumbnail(self):
        model = TestThumbnailFieldModel()
        source = SimpleUploadedFile('_', open(PIC_NAME).read())
        dest_name = 'sorl-thumbnail-test_dest.jpg'
        model.avatar.save(dest_name, source, save=False)
        expected_filename = os.path.join(model.avatar.path)
        self.verify_thumbnail((300, 225), expected_filename=expected_filename)

        tag = model.avatar.thumbnail_tag
        base_name = RELATIVE_PIC_NAME.replace('.', '_')
        expected_tag = ('<img src="%s" width="300" height="225" alt="" />' %
                        '/'.join([settings.MEDIA_URL.rstrip('/'), 'test',
                                  dest_name]))
        self.assertEqual(tag, expected_tag)

########NEW FILE########
__FILENAME__ = templatetags
import unittest
import os
import time
from PIL import Image
from django.conf import settings
from django.template import Template, Context, TemplateSyntaxError
from sorl.thumbnail.base import ThumbnailException
from sorl.thumbnail.tests.classes import BaseTest, RELATIVE_PIC_NAME


class ThumbnailTagTest(BaseTest):
    def render_template(self, source):
        context = Context({
            'source': RELATIVE_PIC_NAME,
            'invalid_source': 'not%s' % RELATIVE_PIC_NAME,
            'size': (90, 100),
            'invalid_size': (90, 'fish'),
            'strsize': '80x90',
            'invalid_strsize': ('1notasize2'),
            'invalid_q': 'notanumber'})
        source = '{% load thumbnail %}' + source
        return Template(source).render(context)

    def testTagInvalid(self):
        basename = RELATIVE_PIC_NAME.replace('.', '_')

        # No args, or wrong number of args
        src = '{% thumbnail %}'
        self.assertRaises(TemplateSyntaxError, self.render_template, src)
        src = '{% thumbnail source %}'
        self.assertRaises(TemplateSyntaxError, self.render_template, src)
        src = '{% thumbnail source 80x80 as variable crop %}'
        self.assertRaises(TemplateSyntaxError, self.render_template, src)

        # Invalid option
        src = '{% thumbnail source 240x200 invalid %}'
        self.assertRaises(TemplateSyntaxError, self.render_template, src)

        # Old comma separated options format can only have an = for quality
        src = '{% thumbnail source 80x80 crop=1,quality=1 %}'
        self.assertRaises(TemplateSyntaxError, self.render_template, src)

        # Invalid quality
        src_invalid = '{% thumbnail source 240x200 quality=invalid_q %}'
        src_missing = '{% thumbnail source 240x200 quality=missing_q %}'
        # ...with THUMBNAIL_DEBUG = False
        self.assertEqual(self.render_template(src_invalid), '')
        self.assertEqual(self.render_template(src_missing), '')
        # ...and with THUMBNAIL_DEBUG = True
        self.change_settings.change({'DEBUG': True})
        self.assertRaises(TypeError, self.render_template, src_invalid)
        self.assertRaises(TypeError, self.render_template, src_missing)

        # Invalid source
        src = '{% thumbnail invalid_source 80x80 %}'
        src_on_context = '{% thumbnail invalid_source 80x80 as thumb %}'
        # ...with THUMBNAIL_DEBUG = False
        self.change_settings.change({'DEBUG': False})
        self.assertEqual(self.render_template(src), '')
        # ...and with THUMBNAIL_DEBUG = True
        self.change_settings.change({'DEBUG': True})
        self.assertRaises(ThumbnailException, self.render_template, src)
        self.assertRaises(ThumbnailException, self.render_template,
                          src_on_context)

        # Non-existant source
        src = '{% thumbnail non_existant_source 80x80 %}'
        src_on_context = '{% thumbnail non_existant_source 80x80 as thumb %}'
        # ...with THUMBNAIL_DEBUG = False
        self.change_settings.change({'DEBUG': False})
        self.assertEqual(self.render_template(src), '')
        # ...and with THUMBNAIL_DEBUG = True
        self.change_settings.change({'DEBUG': True})
        self.assertRaises(ThumbnailException, self.render_template, src)

        # Invalid size as a tuple:
        src = '{% thumbnail source invalid_size %}'
        # ...with THUMBNAIL_DEBUG = False
        self.change_settings.change({'DEBUG': False})
        self.assertEqual(self.render_template(src), '')
        # ...and THUMBNAIL_DEBUG = True
        self.change_settings.change({'DEBUG': True})
        self.assertRaises(TypeError, self.render_template, src)
        # Invalid size as a string:
        src = '{% thumbnail source invalid_strsize %}'
        # ...with THUMBNAIL_DEBUG = False
        self.change_settings.change({'DEBUG': False})
        self.assertEqual(self.render_template(src), '')
        # ...and THUMBNAIL_DEBUG = True
        self.change_settings.change({'DEBUG': True})
        self.assertRaises(TemplateSyntaxError, self.render_template, src)

        # Non-existant size
        src = '{% thumbnail source non_existant_size %}'
        # ...with THUMBNAIL_DEBUG = False
        self.change_settings.change({'DEBUG': False})
        self.assertEqual(self.render_template(src), '')
        # ...and THUMBNAIL_DEBUG = True
        self.change_settings.change({'DEBUG': True})
        self.assertRaises(TemplateSyntaxError, self.render_template, src)

    def testTag(self):
        expected_base = RELATIVE_PIC_NAME.replace('.', '_')
        # Set DEBUG = True to make it easier to trace any failures
        self.change_settings.change({'DEBUG': True})

        # Basic
        output = self.render_template('src="'
            '{% thumbnail source 240x240 %}"')
        expected = '%s_240x240_q85.jpg' % expected_base
        expected_fn = os.path.join(settings.MEDIA_ROOT, expected)
        self.verify_thumbnail((240, 180), expected_filename=expected_fn)
        expected_url = ''.join((settings.MEDIA_URL, expected))
        self.assertEqual(output, 'src="%s"' % expected_url)

        # Size from context variable
        # as a tuple:
        output = self.render_template('src="'
            '{% thumbnail source size %}"')
        expected = '%s_90x100_q85.jpg' % expected_base
        expected_fn = os.path.join(settings.MEDIA_ROOT, expected)
        self.verify_thumbnail((90, 67), expected_filename=expected_fn)
        expected_url = ''.join((settings.MEDIA_URL, expected))
        self.assertEqual(output, 'src="%s"' % expected_url)
        # as a string:
        output = self.render_template('src="'
            '{% thumbnail source strsize %}"')
        expected = '%s_80x90_q85.jpg' % expected_base
        expected_fn = os.path.join(settings.MEDIA_ROOT, expected)
        self.verify_thumbnail((80, 60), expected_filename=expected_fn)
        expected_url = ''.join((settings.MEDIA_URL, expected))
        self.assertEqual(output, 'src="%s"' % expected_url)

        # On context
        output = self.render_template('height:'
            '{% thumbnail source 240x240 as thumb %}{{ thumb.height }}')
        self.assertEqual(output, 'height:180')

        # With options and quality
        output = self.render_template('src="'
            '{% thumbnail source 240x240 sharpen crop quality=95 %}"')
        # Note that the opts are sorted to ensure a consistent filename.
        expected = '%s_240x240_crop_sharpen_q95.jpg' % expected_base
        expected_fn = os.path.join(settings.MEDIA_ROOT, expected)
        self.verify_thumbnail((240, 240), expected_filename=expected_fn)
        expected_url = ''.join((settings.MEDIA_URL, expected))
        self.assertEqual(output, 'src="%s"' % expected_url)

        # With option and quality on context (also using its unicode method to
        # display the url)
        output = self.render_template(
            '{% thumbnail source 240x240 sharpen crop quality=95 as thumb %}'
            'width:{{ thumb.width }}, url:{{ thumb }}')
        self.assertEqual(output, 'width:240, url:%s' % expected_url)

        # Old comma separated format for options is still supported.
        output = self.render_template(
            '{% thumbnail source 240x240 sharpen,crop,quality=95 as thumb %}'
            'width:{{ thumb.width }}, url:{{ thumb }}')
        self.assertEqual(output, 'width:240, url:%s' % expected_url)

filesize_tests = """
>>> from sorl.thumbnail.templatetags.thumbnail import filesize

>>> filesize('abc')
'abc'
>>> filesize(100, 'invalid')
100

>>> bytes = 20
>>> filesize(bytes)
'20 B'
>>> filesize(bytes, 'auto1000')
'20 B'

>>> bytes = 1001
>>> filesize(bytes)
'1001 B'
>>> filesize(bytes, 'auto1000')
'1 kB'

>>> bytes = 10100
>>> filesize(bytes)
'9.9 KiB'

# Note that the decimal place is only used if < 10
>>> filesize(bytes, 'auto1000')
'10 kB'

>>> bytes = 190000000
>>> filesize(bytes)
'181 MiB'
>>> filesize(bytes, 'auto1000')
'190 MB'

# 'auto*long' methods use pluralisation:
>>> filesize(1, 'auto1024long')
'1 byte'
>>> filesize(1, 'auto1000long')
'1 byte'
>>> filesize(2, 'auto1024long')
'2 bytes'
>>> filesize(0, 'auto1000long')
'0 bytes'

# Test all 'auto*long' output:
>>> for i in range(1,10):
...     print '%s, %s' % (filesize(1024**i, 'auto1024long'),
...                       filesize(1000**i, 'auto1000long'))
1 kibibyte, 1 kilobyte
1 mebibyte, 1 megabyte
1 gibibyte, 1 gigabyte
1 tebibyte, 1 terabyte
1 pebibyte, 1 petabyte
1 exbibyte, 1 exabyte
1 zebibyte, 1 zettabyte
1 yobibyte, 1 yottabyte
1024 yobibytes, 1000 yottabytes

# Test all fixed outputs (eg 'kB' or 'MiB')
>>> from sorl.thumbnail.templatetags.thumbnail import filesize_formats, filesize_long_formats
>>> for f in filesize_formats:
...     print '%s (%siB, %sB):' % (filesize_long_formats[f], f.upper(), f)
...     for i in range(0, 10):
...         print ' %s, %s' % (filesize(1024**i, '%siB' % f.upper()),
...                            filesize(1000**i, '%sB' % f))
kilo (KiB, kB):
 0.0009765625, 0.001
 1.0, 1.0
 1024.0, 1000.0
 1048576.0, 1000000.0
 1073741824.0, 1000000000.0
 1.09951162778e+12, 1e+12
 1.12589990684e+15, 1e+15
 1.15292150461e+18, 1e+18
 1.18059162072e+21, 1e+21
 1.20892581961e+24, 1e+24
mega (MiB, MB):
 0.0, 1e-06
 0.0009765625, 0.001
 1.0, 1.0
 1024.0, 1000.0
 1048576.0, 1000000.0
 1073741824.0, 1000000000.0
 1.09951162778e+12, 1e+12
 1.12589990684e+15, 1e+15
 1.15292150461e+18, 1e+18
 1.18059162072e+21, 1e+21
giga (GiB, GB):
 0.0, 1e-09
 0.0, 1e-06
 0.0009765625, 0.001
 1.0, 1.0
 1024.0, 1000.0
 1048576.0, 1000000.0
 1073741824.0, 1000000000.0
 1.09951162778e+12, 1e+12
 1.12589990684e+15, 1e+15
 1.15292150461e+18, 1e+18
tera (TiB, TB):
 0.0, 1e-12
 0.0, 1e-09
 0.0, 1e-06
 0.0009765625, 0.001
 1.0, 1.0
 1024.0, 1000.0
 1048576.0, 1000000.0
 1073741824.0, 1000000000.0
 1.09951162778e+12, 1e+12
 1.12589990684e+15, 1e+15
peta (PiB, PB):
 0.0, 1e-15
 0.0, 1e-12
 0.0, 1e-09
 0.0, 1e-06
 0.0009765625, 0.001
 1.0, 1.0
 1024.0, 1000.0
 1048576.0, 1000000.0
 1073741824.0, 1000000000.0
 1.09951162778e+12, 1e+12
exa (EiB, EB):
 0.0, 1e-18
 0.0, 1e-15
 0.0, 1e-12
 0.0, 1e-09
 0.0, 1e-06
 0.0009765625, 0.001
 1.0, 1.0
 1024.0, 1000.0
 1048576.0, 1000000.0
 1073741824.0, 1000000000.0
zetta (ZiB, ZB):
 0.0, 1e-21
 0.0, 1e-18
 0.0, 1e-15
 0.0, 1e-12
 0.0, 1e-09
 0.0, 1e-06
 0.0009765625, 0.001
 1.0, 1.0
 1024.0, 1000.0
 1048576.0, 1000000.0
yotta (YiB, YB):
 0.0, 1e-24
 0.0, 1e-21
 0.0, 1e-18
 0.0, 1e-15
 0.0, 1e-12
 0.0, 1e-09
 0.0, 1e-06
 0.0009765625, 0.001
 1.0, 1.0
 1024.0, 1000.0
"""

########NEW FILE########
__FILENAME__ = utils
import os
from django.conf import settings
from sorl.thumbnail.utils import *

try:
    set
except NameError:
    from sets import Set as set     # For Python 2.3

utils_tests = """
>>> from sorl.thumbnail.tests.utils import *
>>> from sorl.thumbnail.tests.base import ChangeSettings
>>> from django.conf import settings

>>> change_settings = ChangeSettings()
>>> change_settings.change()

>>> media_root = settings.MEDIA_ROOT.rstrip('/')

#===============================================================================
# Set up test images
#===============================================================================

>>> make_image('test-thumbnail-utils/subdir/test_jpg_110x110_q85.jpg')
>>> make_image('test-thumbnail-utils/test_jpg_80x80_q85.jpg')
>>> make_image('test-thumbnail-utils/test_jpg_80x80_q95.jpg')
>>> make_image('test-thumbnail-utils/another_test_jpg_80x80_q85.jpg')
>>> make_image('test-thumbnail-utils/test_with_opts_jpg_80x80_crop_bw_q85.jpg')
>>> make_image('test-thumbnail-basedir/test-thumbnail-utils/test_jpg_100x100_q85.jpg')
>>> make_image('test-thumbnail-utils/prefix-test_jpg_120x120_q85.jpg')

#===============================================================================
# all_thumbnails()
#===============================================================================

# Find all thumbs
>>> thumb_dir = os.path.join(settings.MEDIA_ROOT, 'test-thumbnail-utils')
>>> thumbs = all_thumbnails(thumb_dir)
>>> k = thumbs.keys()
>>> k.sort()
>>> [consistent_slash(path) for path in k]
['another_test.jpg', 'prefix-test.jpg', 'subdir/test.jpg', 'test.jpg', 'test_with_opts.jpg']

# Find all thumbs, no recurse
>>> thumbs = all_thumbnails(thumb_dir, recursive=False)
>>> k = thumbs.keys()
>>> k.sort()
>>> k
['another_test.jpg', 'prefix-test.jpg', 'test.jpg', 'test_with_opts.jpg']

#===============================================================================
# thumbnails_for_file()
#===============================================================================

>>> output = []
>>> for thumb in thumbs['test.jpg']:
...     thumb['rel_fn'] = strip_media_root(thumb['filename'])
...     output.append('%(x)sx%(y)s %(quality)s %(rel_fn)s' % thumb)
>>> output.sort()
>>> output
['80x80 85 test-thumbnail-utils/test_jpg_80x80_q85.jpg', '80x80 95 test-thumbnail-utils/test_jpg_80x80_q95.jpg']

# Thumbnails for file
>>> output = []
>>> for thumb in thumbnails_for_file('test-thumbnail-utils/test.jpg'):
...    output.append(strip_media_root(thumb['filename']))
>>> output.sort()
>>> output
['test-thumbnail-utils/test_jpg_80x80_q85.jpg', 'test-thumbnail-utils/test_jpg_80x80_q95.jpg']

# Thumbnails for file - shouldn't choke on non-existant file
>>> thumbnails_for_file('test-thumbnail-utils/non-existant.jpg')
[]

# Thumbnails for file, with basedir setting
>>> change_settings.change({'BASEDIR': 'test-thumbnail-basedir'})
>>> for thumb in thumbnails_for_file('test-thumbnail-utils/test.jpg'):
...    print strip_media_root(thumb['filename'])
test-thumbnail-basedir/test-thumbnail-utils/test_jpg_100x100_q85.jpg

# Thumbnails for file, with subdir setting
>>> change_settings.change({'SUBDIR': 'subdir', 'BASEDIR': ''})
>>> for thumb in thumbnails_for_file('test-thumbnail-utils/test.jpg'):
...    print strip_media_root(thumb['filename'])
test-thumbnail-utils/subdir/test_jpg_110x110_q85.jpg

# Thumbnails for file, with prefix setting
>>> change_settings.change({'PREFIX': 'prefix-', 'SUBDIR': ''})
>>> for thumb in thumbnails_for_file('test-thumbnail-utils/test.jpg'):
...    print strip_media_root(thumb['filename'])
test-thumbnail-utils/prefix-test_jpg_120x120_q85.jpg

#===============================================================================
# Clean up images / directories
#===============================================================================

>>> clean_up()
"""

images_to_delete = set()
dirs_to_delete = []

def make_image(relative_image):
    absolute_image = os.path.join(settings.MEDIA_ROOT, relative_image)
    make_dirs(os.path.dirname(relative_image))
    open(absolute_image, 'w').close()
    images_to_delete.add(absolute_image)

def make_dirs(relative_path):
    if not relative_path:
        return
    absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    if os.path.isdir(absolute_path):
        return
    if absolute_path not in dirs_to_delete:
        dirs_to_delete.append(absolute_path)
    make_dirs(os.path.dirname(relative_path))
    os.mkdir(absolute_path)

def clean_up():
    for image in images_to_delete:
        os.remove(image)
    for path in dirs_to_delete:
        os.rmdir(path)

MEDIA_ROOT_LENGTH = len(os.path.normpath(settings.MEDIA_ROOT))
def strip_media_root(path):
    path = os.path.normpath(path)
    # chop off the MEDIA_ROOT and strip any leading os.sep
    path = path[MEDIA_ROOT_LENGTH:].lstrip(os.sep)
    return consistent_slash(path)

def consistent_slash(path):
    """
    Ensure we're always testing against the '/' os separator (otherwise tests
    fail against Windows).
    """
    if os.sep != '/':
        path = path.replace(os.sep, '/')
    return path

########NEW FILE########
__FILENAME__ = utils
import re
import os


re_thumbnail_file = re.compile(r'(?P<source_filename>.+)_(?P<x>\d+)x(?P<y>\d+)(?:_(?P<options>\w+))?_q(?P<quality>\d+)(?:.[^.]+)?$')
re_new_args = re.compile('(?<!quality)=')


def all_thumbnails(path, recursive=True, prefix=None, subdir=None):
    """
    Return a dictionary referencing all files which match the thumbnail format.

    Each key is a source image filename, relative to path.
    Each value is a list of dictionaries as explained in `thumbnails_for_file`.
    """
    # Fall back to using thumbnail settings. These are local imports so that
    # there is no requirement of Django to use the utils module.
    if prefix is None:
        from sorl.thumbnail.main import get_thumbnail_setting
        prefix = get_thumbnail_setting('PREFIX')
    if subdir is None:
        from sorl.thumbnail.main import get_thumbnail_setting
        subdir = get_thumbnail_setting('SUBDIR')
    thumbnail_files = {}
    if not path.endswith('/'):
        path = '%s/' % path
    len_path = len(path)
    if recursive:
        all = os.walk(path)
    else:
        files = []
        for file in os.listdir(path):
            if os.path.isfile(os.path.join(path, file)):
                files.append(file)
        all = [(path, [], files)]
    for dir_, subdirs, files in all:
        rel_dir = dir_[len_path:]
        for file in files:
            thumb = re_thumbnail_file.match(file)
            if not thumb:
                continue
            d = thumb.groupdict()
            source_filename = d.pop('source_filename')
            if prefix:
                source_path, source_filename = os.path.split(source_filename)
                if not source_filename.startswith(prefix):
                    continue
                source_filename = os.path.join(source_path,
                    source_filename[len(prefix):])
            d['options'] = d['options'] and d['options'].split('_') or []
            if subdir and rel_dir.endswith(subdir):
                rel_dir = rel_dir[:-len(subdir)]
            # Corner-case bug: if the filename didn't have an extension but did
            # have an underscore, the last underscore will get converted to a
            # '.'.
            m = re.match(r'(.*)_(.*)', source_filename)
            if m:
                 source_filename = '%s.%s' % m.groups()
            filename = os.path.join(rel_dir, source_filename)
            thumbnail_file = thumbnail_files.setdefault(filename, [])
            d['filename'] = os.path.join(dir_, file)
            thumbnail_file.append(d)
    return thumbnail_files


def thumbnails_for_file(relative_source_path, root=None, basedir=None,
                        subdir=None, prefix=None):
    """
    Return a list of dictionaries, one for each thumbnail belonging to the
    source image.

    The following list explains each key of the dictionary:

      `filename`  -- absolute thumbnail path
      `x` and `y` -- the size of the thumbnail
      `options`   -- list of options for this thumbnail
      `quality`   -- quality setting for this thumbnail
    """
    # Fall back to using thumbnail settings. These are local imports so that
    # there is no requirement of Django to use the utils module.
    if root is None:
        from django.conf import settings
        root = settings.MEDIA_ROOT
    if prefix is None:
        from sorl.thumbnail.main import get_thumbnail_setting
        prefix = get_thumbnail_setting('PREFIX')
    if subdir is None:
        from sorl.thumbnail.main import get_thumbnail_setting
        subdir = get_thumbnail_setting('SUBDIR')
    if basedir is None:
        from sorl.thumbnail.main import get_thumbnail_setting
        basedir = get_thumbnail_setting('BASEDIR')
    source_dir, filename = os.path.split(relative_source_path)
    thumbs_path = os.path.join(root, basedir, source_dir, subdir)
    if not os.path.isdir(thumbs_path):
        return []
    files = all_thumbnails(thumbs_path, recursive=False, prefix=prefix,
                           subdir='')
    return files.get(filename, [])


def delete_thumbnails(relative_source_path, root=None, basedir=None,
                      subdir=None, prefix=None):
    """
    Delete all thumbnails for a source image.
    """
    thumbs = thumbnails_for_file(relative_source_path, root, basedir, subdir,
                                 prefix)
    return _delete_using_thumbs_list(thumbs)


def _delete_using_thumbs_list(thumbs):
    deleted = 0
    for thumb_dict in thumbs:
        filename = thumb_dict['filename']
        try:
            os.remove(filename)
        except:
            pass
        else:
            deleted += 1
    return deleted


def delete_all_thumbnails(path, recursive=True):
    """
    Delete all files within a path which match the thumbnails pattern.

    By default, matching files from all sub-directories are also removed. To
    only remove from the path directory, set recursive=False.
    """
    total = 0
    for thumbs in all_thumbnails(path, recursive=recursive).values():
        total += _delete_using_thumbs_list(thumbs)
    return total


def split_args(args):
    """
    Split a list of argument strings into a dictionary where each key is an
    argument name.
    
    An argument looks like ``crop``, ``crop="some option"`` or ``crop=my_var``.
    Arguments which provide no value get a value of ``None``.
    """
    if not args:
        return {}
    # Handle the old comma separated argument format.
    if len(args) == 1 and not re_new_args.search(args[0]):
        args = args[0].split(',')
    # Separate out the key and value for each argument.
    args_dict = {}
    for arg in args:
        split_arg = arg.split('=', 1)
        value = len(split_arg) > 1 and split_arg[1] or None
        args_dict[split_arg[0]] = value
    return args_dict

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from tagging.models import Tag, TaggedItem
from tagging.forms import TagAdminForm

class TagAdmin(admin.ModelAdmin):
    form = TagAdminForm

admin.site.register(TaggedItem)
admin.site.register(Tag, TagAdmin)





########NEW FILE########
__FILENAME__ = fields
"""
A custom Model Field for tagging.
"""
from django.db.models import signals
from django.db.models.fields import CharField
from django.utils.translation import ugettext_lazy as _

from tagging import settings
from tagging.models import Tag
from tagging.utils import edit_string_for_tags

class TagField(CharField):
    """
    A "special" character field that actually works as a relationship to tags
    "under the hood". This exposes a space-separated string of tags, but does
    the splitting/reordering/etc. under the hood.
    """
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 255)
        kwargs['blank'] = kwargs.get('blank', True)
        super(TagField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        super(TagField, self).contribute_to_class(cls, name)

        # Make this object the descriptor for field access.
        setattr(cls, self.name, self)

        # Save tags back to the database post-save
        signals.post_save.connect(self._save, cls, True)

    def __get__(self, instance, owner=None):
        """
        Tag getter. Returns an instance's tags if accessed on an instance, and
        all of a model's tags if called on a class. That is, this model::

           class Link(models.Model):
               ...
               tags = TagField()

        Lets you do both of these::

           >>> l = Link.objects.get(...)
           >>> l.tags
           'tag1 tag2 tag3'

           >>> Link.tags
           'tag1 tag2 tag3 tag4'

        """
        # Handle access on the model (i.e. Link.tags)
        if instance is None:
            return edit_string_for_tags(Tag.objects.usage_for_model(owner))

        tags = self._get_instance_tag_cache(instance)
        if tags is None:
            if instance.pk is None:
                self._set_instance_tag_cache(instance, '')
            else:
                self._set_instance_tag_cache(
                    instance, edit_string_for_tags(Tag.objects.get_for_object(instance)))
        return self._get_instance_tag_cache(instance)

    def __set__(self, instance, value):
        """
        Set an object's tags.
        """
        if instance is None:
            raise AttributeError(_('%s can only be set on instances.') % self.name)
        if settings.FORCE_LOWERCASE_TAGS and value is not None:
            value = value.lower()
        self._set_instance_tag_cache(instance, value)

    def _save(self, **kwargs): #signal, sender, instance):
        """
        Save tags back to the database
        """
        tags = self._get_instance_tag_cache(kwargs['instance'])
        if tags is not None:
            Tag.objects.update_tags(kwargs['instance'], tags)

    def __delete__(self, instance):
        """
        Clear all of an object's tags.
        """
        self._set_instance_tag_cache(instance, '')

    def _get_instance_tag_cache(self, instance):
        """
        Helper: get an instance's tag cache.
        """
        return getattr(instance, '_%s_cache' % self.attname, None)

    def _set_instance_tag_cache(self, instance, tags):
        """
        Helper: set an instance's tag cache.
        """
        setattr(instance, '_%s_cache' % self.attname, tags)

    def get_internal_type(self):
        return 'CharField'

    def formfield(self, **kwargs):
        from tagging import forms
        defaults = {'form_class': forms.TagField}
        defaults.update(kwargs)
        return super(TagField, self).formfield(**defaults)

########NEW FILE########
__FILENAME__ = forms
"""
Tagging components for Django's ``newforms`` form library.
"""
from django import forms
from django.utils.translation import ugettext as _

from tagging import settings
from tagging.utils import parse_tag_input

class TagField(forms.CharField):
    """
    A ``CharField`` which validates that its input is a valid list of
    tag names.
    """
    def clean(self, value):
        value = super(TagField, self).clean(value)
        if value == u'':
            return value
        for tag_name in parse_tag_input(value):
            if len(tag_name) > settings.MAX_TAG_LENGTH:
                raise forms.ValidationError(
                    _('Each tag may be no more than %s characters long.') % settings.MAX_TAG_LENGTH)
        return value

########NEW FILE########
__FILENAME__ = generic
from django.contrib.contenttypes.models import ContentType

def fetch_content_objects(tagged_items, select_related_for=None):
    """
    Retrieves ``ContentType`` and content objects for the given list of
    ``TaggedItems``, grouping the retrieval of content objects by model
    type to reduce the number of queries executed.

    This results in ``number_of_content_types + 1`` queries rather than
    the ``number_of_tagged_items * 2`` queries you'd get by iterating
    over the list and accessing each item's ``object`` attribute.

    A ``select_related_for`` argument can be used to specify a list of
    of model names (corresponding to the ``model`` field of a
    ``ContentType``) for which ``select_related`` should be used when
    retrieving model instances.
    """
    if select_related_for is None: select_related_for = []

    # Group content object pks by their content type pks
    objects = {}
    for item in tagged_items:
        objects.setdefault(item.content_type_id, []).append(item.object_id)

    # Retrieve content types and content objects in bulk
    content_types = ContentType._default_manager.in_bulk(objects.keys())
    for content_type_pk, object_pks in objects.iteritems():
        model = content_types[content_type_pk].model_class()
        if content_types[content_type_pk].model in select_related_for:
            objects[content_type_pk] = model._default_manager.select_related().in_bulk(object_pks)
        else:
            objects[content_type_pk] = model._default_manager.in_bulk(object_pks)

    # Set content types and content objects in the appropriate cache
    # attributes, so accessing the 'content_type' and 'object'
    # attributes on each tagged item won't result in further database
    # hits.
    for item in tagged_items:
        item._object_cache = objects[item.content_type_id][item.object_id]
        item._content_type_cache = content_types[item.content_type_id]

########NEW FILE########
__FILENAME__ = managers
"""
Custom managers for Django models registered with the tagging
application.
"""
from django.contrib.contenttypes.models import ContentType
from django.db import models

from tagging.models import Tag, TaggedItem

class ModelTagManager(models.Manager):
    """
    A manager for retrieving tags for a particular model.
    """
    def get_query_set(self):
        ctype = ContentType.objects.get_for_model(self.model)
        return Tag.objects.filter(
            items__content_type__pk=ctype.pk).distinct()

    def cloud(self, *args, **kwargs):
        return Tag.objects.cloud_for_model(self.model, *args, **kwargs)

    def related(self, tags, *args, **kwargs):
        return Tag.objects.related_for_model(tags, self.model, *args, **kwargs)

    def usage(self, *args, **kwargs):
        return Tag.objects.usage_for_model(self.model, *args, **kwargs)

class ModelTaggedItemManager(models.Manager):
    """
    A manager for retrieving model instances based on their tags.
    """
    def related_to(self, obj, queryset=None, num=None):
        if queryset is None:
            return TaggedItem.objects.get_related(obj, self.model, num=num)
        else:
            return TaggedItem.objects.get_related(obj, queryset, num=num)

    def with_all(self, tags, queryset=None):
        if queryset is None:
            return TaggedItem.objects.get_by_model(self.model, tags)
        else:
            return TaggedItem.objects.get_by_model(queryset, tags)

    def with_any(self, tags, queryset=None):
        if queryset is None:
            return TaggedItem.objects.get_union_by_model(self.model, tags)
        else:
            return TaggedItem.objects.get_union_by_model(queryset, tags)

class TagDescriptor(object):
    """
    A descriptor which provides access to a ``ModelTagManager`` for
    model classes and simple retrieval, updating and deletion of tags
    for model instances.
    """
    def __get__(self, instance, owner):
        if not instance:
            tag_manager = ModelTagManager()
            tag_manager.model = owner
            return tag_manager
        else:
            return Tag.objects.get_for_object(instance)

    def __set__(self, instance, value):
        Tag.objects.update_tags(instance, value)

    def __delete__(self, instance):
        Tag.objects.update_tags(instance, None)

########NEW FILE########
__FILENAME__ = models
"""
Models and managers for generic tagging.
"""
# Python 2.3 compatibility
try:
    set
except NameError:
    from sets import Set as set

from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models
from django.db.models.query import QuerySet
from django.utils.translation import ugettext_lazy as _

from tagging import settings
from tagging.utils import calculate_cloud, get_tag_list, get_queryset_and_model, parse_tag_input
from tagging.utils import LOGARITHMIC

qn = connection.ops.quote_name

############
# Managers #
############

class TagManager(models.Manager):
    def update_tags(self, obj, tag_names):
        """
        Update tags associated with an object.
        """
        ctype = ContentType.objects.get_for_model(obj)
        current_tags = list(self.filter(items__content_type__pk=ctype.pk,
                                        items__object_id=obj.pk))
        updated_tag_names = parse_tag_input(tag_names)
        if settings.FORCE_LOWERCASE_TAGS:
            updated_tag_names = [t.lower() for t in updated_tag_names]

        # Remove tags which no longer apply
        tags_for_removal = [tag for tag in current_tags \
                            if tag.name not in updated_tag_names]
        if len(tags_for_removal):
            TaggedItem._default_manager.filter(content_type__pk=ctype.pk,
                                               object_id=obj.pk,
                                               tag__in=tags_for_removal).delete()
        # Add new tags
        current_tag_names = [tag.name for tag in current_tags]
        for tag_name in updated_tag_names:
            if tag_name not in current_tag_names:
                tag, created = self.get_or_create(name=tag_name)
                TaggedItem._default_manager.create(tag=tag, object=obj)

    def add_tag(self, obj, tag_name):
        """
        Associates the given object with a tag.
        """
        tag_names = parse_tag_input(tag_name)
        if not len(tag_names):
            raise AttributeError(_('No tags were given: "%s".') % tag_name)
        if len(tag_names) > 1:
            raise AttributeError(_('Multiple tags were given: "%s".') % tag_name)
        tag_name = tag_names[0]
        if settings.FORCE_LOWERCASE_TAGS:
            tag_name = tag_name.lower()
        tag, created = self.get_or_create(name=tag_name)
        ctype = ContentType.objects.get_for_model(obj)
        TaggedItem._default_manager.get_or_create(
            tag=tag, content_type=ctype, object_id=obj.pk)

    def get_for_object(self, obj):
        """
        Create a queryset matching all tags associated with the given
        object.
        """
        ctype = ContentType.objects.get_for_model(obj)
        return self.filter(items__content_type__pk=ctype.pk,
                           items__object_id=obj.pk)

    def _get_usage(self, model, counts=False, min_count=None, extra_joins=None, extra_criteria=None, params=None):
        """
        Perform the custom SQL query for ``usage_for_model`` and
        ``usage_for_queryset``.
        """
        if min_count is not None: counts = True

        model_table = qn(model._meta.db_table)
        model_pk = '%s.%s' % (model_table, qn(model._meta.pk.column))
        query = """
        SELECT DISTINCT %(tag)s.id, %(tag)s.name%(count_sql)s
        FROM
            %(tag)s
            INNER JOIN %(tagged_item)s
                ON %(tag)s.id = %(tagged_item)s.tag_id
            INNER JOIN %(model)s
                ON %(tagged_item)s.object_id = %(model_pk)s
            %%s
        WHERE %(tagged_item)s.content_type_id = %(content_type_id)s
            %%s
        GROUP BY %(tag)s.id, %(tag)s.name
        %%s
        ORDER BY %(tag)s.name ASC""" % {
            'tag': qn(self.model._meta.db_table),
            'count_sql': counts and (', COUNT(%s)' % model_pk) or '',
            'tagged_item': qn(TaggedItem._meta.db_table),
            'model': model_table,
            'model_pk': model_pk,
            'content_type_id': ContentType.objects.get_for_model(model).pk,
        }

        min_count_sql = ''
        if min_count is not None:
            min_count_sql = 'HAVING COUNT(%s) >= %%s' % model_pk
            params.append(min_count)

        cursor = connection.cursor()
        cursor.execute(query % (extra_joins, extra_criteria, min_count_sql), params)
        tags = []
        for row in cursor.fetchall():
            t = self.model(*row[:2])
            if counts:
                t.count = row[2]
            tags.append(t)
        return tags

    def usage_for_model(self, model, counts=False, min_count=None, filters=None):
        """
        Obtain a list of tags associated with instances of the given
        Model class.

        If ``counts`` is True, a ``count`` attribute will be added to
        each tag, indicating how many times it has been used against
        the Model class in question.

        If ``min_count`` is given, only tags which have a ``count``
        greater than or equal to ``min_count`` will be returned.
        Passing a value for ``min_count`` implies ``counts=True``.

        To limit the tags (and counts, if specified) returned to those
        used by a subset of the Model's instances, pass a dictionary
        of field lookups to be applied to the given Model as the
        ``filters`` argument.
        """
        if filters is None: filters = {}

        queryset = model._default_manager.filter()
        for f in filters.items():
            queryset.query.add_filter(f)
        usage = self.usage_for_queryset(queryset, counts, min_count)

        return usage

    def usage_for_queryset(self, queryset, counts=False, min_count=None):
        """
        Obtain a list of tags associated with instances of a model
        contained in the given queryset.

        If ``counts`` is True, a ``count`` attribute will be added to
        each tag, indicating how many times it has been used against
        the Model class in question.

        If ``min_count`` is given, only tags which have a ``count``
        greater than or equal to ``min_count`` will be returned.
        Passing a value for ``min_count`` implies ``counts=True``.
        """

        extra_joins = ' '.join(queryset.query.get_from_clause()[0][1:])
        where, params = queryset.query.where.as_sql()
        if where:
            extra_criteria = 'AND %s' % where
        else:
            extra_criteria = ''
        return self._get_usage(queryset.model, counts, min_count, extra_joins, extra_criteria, params)

    def related_for_model(self, tags, model, counts=False, min_count=None):
        """
        Obtain a list of tags related to a given list of tags - that
        is, other tags used by items which have all the given tags.

        If ``counts`` is True, a ``count`` attribute will be added to
        each tag, indicating the number of items which have it in
        addition to the given list of tags.

        If ``min_count`` is given, only tags which have a ``count``
        greater than or equal to ``min_count`` will be returned.
        Passing a value for ``min_count`` implies ``counts=True``.
        """
        if min_count is not None: counts = True
        tags = get_tag_list(tags)
        tag_count = len(tags)
        tagged_item_table = qn(TaggedItem._meta.db_table)
        query = """
        SELECT %(tag)s.id, %(tag)s.name%(count_sql)s
        FROM %(tagged_item)s INNER JOIN %(tag)s ON %(tagged_item)s.tag_id = %(tag)s.id
        WHERE %(tagged_item)s.content_type_id = %(content_type_id)s
          AND %(tagged_item)s.object_id IN
          (
              SELECT %(tagged_item)s.object_id
              FROM %(tagged_item)s, %(tag)s
              WHERE %(tagged_item)s.content_type_id = %(content_type_id)s
                AND %(tag)s.id = %(tagged_item)s.tag_id
                AND %(tag)s.id IN (%(tag_id_placeholders)s)
              GROUP BY %(tagged_item)s.object_id
              HAVING COUNT(%(tagged_item)s.object_id) = %(tag_count)s
          )
          AND %(tag)s.id NOT IN (%(tag_id_placeholders)s)
        GROUP BY %(tag)s.id, %(tag)s.name
        %(min_count_sql)s
        ORDER BY %(tag)s.name ASC""" % {
            'tag': qn(self.model._meta.db_table),
            'count_sql': counts and ', COUNT(%s.object_id)' % tagged_item_table or '',
            'tagged_item': tagged_item_table,
            'content_type_id': ContentType.objects.get_for_model(model).pk,
            'tag_id_placeholders': ','.join(['%s'] * tag_count),
            'tag_count': tag_count,
            'min_count_sql': min_count is not None and ('HAVING COUNT(%s.object_id) >= %%s' % tagged_item_table) or '',
        }

        params = [tag.pk for tag in tags] * 2
        if min_count is not None:
            params.append(min_count)

        cursor = connection.cursor()
        cursor.execute(query, params)
        related = []
        for row in cursor.fetchall():
            tag = self.model(*row[:2])
            if counts is True:
                tag.count = row[2]
            related.append(tag)
        return related

    def cloud_for_model(self, model, steps=4, distribution=LOGARITHMIC,
                        filters=None, min_count=None):
        """
        Obtain a list of tags associated with instances of the given
        Model, giving each tag a ``count`` attribute indicating how
        many times it has been used and a ``font_size`` attribute for
        use in displaying a tag cloud.

        ``steps`` defines the range of font sizes - ``font_size`` will
        be an integer between 1 and ``steps`` (inclusive).

        ``distribution`` defines the type of font size distribution
        algorithm which will be used - logarithmic or linear. It must
        be either ``tagging.utils.LOGARITHMIC`` or
        ``tagging.utils.LINEAR``.

        To limit the tags displayed in the cloud to those associated
        with a subset of the Model's instances, pass a dictionary of
        field lookups to be applied to the given Model as the
        ``filters`` argument.

        To limit the tags displayed in the cloud to those with a
        ``count`` greater than or equal to ``min_count``, pass a value
        for the ``min_count`` argument.
        """
        tags = list(self.usage_for_model(model, counts=True, filters=filters,
                                         min_count=min_count))
        return calculate_cloud(tags, steps, distribution)

class TaggedItemManager(models.Manager):
    """
    FIXME There's currently no way to get the ``GROUP BY`` and ``HAVING``
          SQL clauses required by many of this manager's methods into
          Django's ORM.

          For now, we manually execute a query to retrieve the PKs of
          objects we're interested in, then use the ORM's ``__in``
          lookup to return a ``QuerySet``.

          Now that the queryset-refactor branch is in the trunk, this can be
          tidied up significantly.
    """
    def get_by_model(self, queryset_or_model, tags):
        """
        Create a ``QuerySet`` containing instances of the specified
        model associated with a given tag or list of tags.
        """
        tags = get_tag_list(tags)
        tag_count = len(tags)
        if tag_count == 0:
            # No existing tags were given
            queryset, model = get_queryset_and_model(queryset_or_model)
            return model._default_manager.none()
        elif tag_count == 1:
            # Optimisation for single tag - fall through to the simpler
            # query below.
            tag = tags[0]
        else:
            return self.get_intersection_by_model(queryset_or_model, tags)

        queryset, model = get_queryset_and_model(queryset_or_model)
        content_type = ContentType.objects.get_for_model(model)
        opts = self.model._meta
        tagged_item_table = qn(opts.db_table)
        return queryset.extra(
            tables=[opts.db_table],
            where=[
                '%s.content_type_id = %%s' % tagged_item_table,
                '%s.tag_id = %%s' % tagged_item_table,
                '%s.%s = %s.object_id' % (qn(model._meta.db_table),
                                          qn(model._meta.pk.column),
                                          tagged_item_table)
            ],
            params=[content_type.pk, tag.pk],
        )

    def get_intersection_by_model(self, queryset_or_model, tags):
        """
        Create a ``QuerySet`` containing instances of the specified
        model associated with *all* of the given list of tags.
        """
        tags = get_tag_list(tags)
        tag_count = len(tags)
        queryset, model = get_queryset_and_model(queryset_or_model)

        if not tag_count:
            return model._default_manager.none()

        model_table = qn(model._meta.db_table)
        # This query selects the ids of all objects which have all the
        # given tags.
        query = """
        SELECT %(model_pk)s
        FROM %(model)s, %(tagged_item)s
        WHERE %(tagged_item)s.content_type_id = %(content_type_id)s
          AND %(tagged_item)s.tag_id IN (%(tag_id_placeholders)s)
          AND %(model_pk)s = %(tagged_item)s.object_id
        GROUP BY %(model_pk)s
        HAVING COUNT(%(model_pk)s) = %(tag_count)s""" % {
            'model_pk': '%s.%s' % (model_table, qn(model._meta.pk.column)),
            'model': model_table,
            'tagged_item': qn(self.model._meta.db_table),
            'content_type_id': ContentType.objects.get_for_model(model).pk,
            'tag_id_placeholders': ','.join(['%s'] * tag_count),
            'tag_count': tag_count,
        }

        cursor = connection.cursor()
        cursor.execute(query, [tag.pk for tag in tags])
        object_ids = [row[0] for row in cursor.fetchall()]
        if len(object_ids) > 0:
            return queryset.filter(pk__in=object_ids)
        else:
            return model._default_manager.none()

    def get_union_by_model(self, queryset_or_model, tags):
        """
        Create a ``QuerySet`` containing instances of the specified
        model associated with *any* of the given list of tags.
        """
        tags = get_tag_list(tags)
        tag_count = len(tags)
        queryset, model = get_queryset_and_model(queryset_or_model)

        if not tag_count:
            return model._default_manager.none()

        model_table = qn(model._meta.db_table)
        # This query selects the ids of all objects which have any of
        # the given tags.
        query = """
        SELECT %(model_pk)s
        FROM %(model)s, %(tagged_item)s
        WHERE %(tagged_item)s.content_type_id = %(content_type_id)s
          AND %(tagged_item)s.tag_id IN (%(tag_id_placeholders)s)
          AND %(model_pk)s = %(tagged_item)s.object_id
        GROUP BY %(model_pk)s""" % {
            'model_pk': '%s.%s' % (model_table, qn(model._meta.pk.column)),
            'model': model_table,
            'tagged_item': qn(self.model._meta.db_table),
            'content_type_id': ContentType.objects.get_for_model(model).pk,
            'tag_id_placeholders': ','.join(['%s'] * tag_count),
        }

        cursor = connection.cursor()
        cursor.execute(query, [tag.pk for tag in tags])
        object_ids = [row[0] for row in cursor.fetchall()]
        if len(object_ids) > 0:
            return queryset.filter(pk__in=object_ids)
        else:
            return model._default_manager.none()

    def get_related(self, obj, queryset_or_model, num=None):
        """
        Retrieve a list of instances of the specified model which share
        tags with the model instance ``obj``, ordered by the number of
        shared tags in descending order.

        If ``num`` is given, a maximum of ``num`` instances will be
        returned.
        """
        queryset, model = get_queryset_and_model(queryset_or_model)
        model_table = qn(model._meta.db_table)
        content_type = ContentType.objects.get_for_model(obj)
        related_content_type = ContentType.objects.get_for_model(model)
        query = """
        SELECT %(model_pk)s, COUNT(related_tagged_item.object_id) AS %(count)s
        FROM %(model)s, %(tagged_item)s, %(tag)s, %(tagged_item)s related_tagged_item
        WHERE %(tagged_item)s.object_id = %%s
          AND %(tagged_item)s.content_type_id = %(content_type_id)s
          AND %(tag)s.id = %(tagged_item)s.tag_id
          AND related_tagged_item.content_type_id = %(related_content_type_id)s
          AND related_tagged_item.tag_id = %(tagged_item)s.tag_id
          AND %(model_pk)s = related_tagged_item.object_id"""
        if content_type.pk == related_content_type.pk:
            # Exclude the given instance itself if determining related
            # instances for the same model.
            query += """
          AND related_tagged_item.object_id != %(tagged_item)s.object_id"""
        query += """
        GROUP BY %(model_pk)s
        ORDER BY %(count)s DESC
        %(limit_offset)s"""
        query = query % {
            'model_pk': '%s.%s' % (model_table, qn(model._meta.pk.column)),
            'count': qn('count'),
            'model': model_table,
            'tagged_item': qn(self.model._meta.db_table),
            'tag': qn(self.model._meta.get_field('tag').rel.to._meta.db_table),
            'content_type_id': content_type.pk,
            'related_content_type_id': related_content_type.pk,
            # Hardcoding this for now just to get tests working again - this
            # should now be handled by the query object.
            'limit_offset': num is not None and 'LIMIT %s' or '',
        }

        cursor = connection.cursor()
        params = [obj.pk]
        if num is not None:
            params.append(num)
        cursor.execute(query, params)
        object_ids = [row[0] for row in cursor.fetchall()]
        if len(object_ids) > 0:
            # Use in_bulk here instead of an id__in lookup, because id__in would
            # clobber the ordering.
            object_dict = queryset.in_bulk(object_ids)
            return [object_dict[object_id] for object_id in object_ids \
                    if object_id in object_dict]
        else:
            return []

##########
# Models #
##########

class Tag(models.Model):
    """
    A tag.
    """
    name = models.CharField(_('name'), max_length=50, unique=True, db_index=True)

    objects = TagManager()

    class Meta:
        ordering = ('name',)
        verbose_name = _('tag')
        verbose_name_plural = _('tags')

    def __unicode__(self):
        return self.name

class TaggedItem(models.Model):
    """
    Holds the relationship between a tag and the item being tagged.
    """
    tag          = models.ForeignKey(Tag, verbose_name=_('tag'), related_name='items')
    content_type = models.ForeignKey(ContentType, verbose_name=_('content type'))
    object_id    = models.PositiveIntegerField(_('object id'), db_index=True)
    object       = generic.GenericForeignKey('content_type', 'object_id')

    objects = TaggedItemManager()

    class Meta:
        # Enforce unique tag association per object
        unique_together = (('tag', 'content_type', 'object_id'),)
        verbose_name = _('tagged item')
        verbose_name_plural = _('tagged items')

    def __unicode__(self):
        return u'%s [%s]' % (self.object, self.tag)

########NEW FILE########
__FILENAME__ = settings
"""
Convenience module for access of custom tagging application settings,
which enforces default settings when the main settings module does not
contain the appropriate settings.
"""
from django.conf import settings

# The maximum length of a tag's name.
MAX_TAG_LENGTH = getattr(settings, 'MAX_TAG_LENGTH', 50)

# Whether to force all tags to lowercase before they are saved to the
# database.
FORCE_LOWERCASE_TAGS = getattr(settings, 'FORCE_LOWERCASE_TAGS', False)

########NEW FILE########
__FILENAME__ = tagging_tags
from django.db.models import get_model
from django.template import Library, Node, TemplateSyntaxError, Variable, resolve_variable
from django.utils.translation import ugettext as _

from tagging.models import Tag, TaggedItem
from tagging.utils import LINEAR, LOGARITHMIC

register = Library()

class TagsForModelNode(Node):
    def __init__(self, model, context_var, counts):
        self.model = model
        self.context_var = context_var
        self.counts = counts

    def render(self, context):
        model = get_model(*self.model.split('.'))
        if model is None:
            raise TemplateSyntaxError(_('tags_for_model tag was given an invalid model: %s') % self.model)
        context[self.context_var] = Tag.objects.usage_for_model(model, counts=self.counts)
        return ''

class TagCloudForModelNode(Node):
    def __init__(self, model, context_var, **kwargs):
        self.model = model
        self.context_var = context_var
        self.kwargs = kwargs

    def render(self, context):
        model = get_model(*self.model.split('.'))
        if model is None:
            raise TemplateSyntaxError(_('tag_cloud_for_model tag was given an invalid model: %s') % self.model)
        context[self.context_var] = \
            Tag.objects.cloud_for_model(model, **self.kwargs)
        return ''

class TagsForObjectNode(Node):
    def __init__(self, obj, context_var):
        self.obj = Variable(obj)
        self.context_var = context_var

    def render(self, context):
        context[self.context_var] = \
            Tag.objects.get_for_object(self.obj.resolve(context))
        return ''

class TaggedObjectsNode(Node):
    def __init__(self, tag, model, context_var):
        self.tag = Variable(tag)
        self.context_var = context_var
        self.model = model

    def render(self, context):
        model = get_model(*self.model.split('.'))
        if model is None:
            raise TemplateSyntaxError(_('tagged_objects tag was given an invalid model: %s') % self.model)
        context[self.context_var] = \
            TaggedItem.objects.get_by_model(model, self.tag.resolve(context))
        return ''

def do_tags_for_model(parser, token):
    """
    Retrieves a list of ``Tag`` objects associated with a given model
    and stores them in a context variable.

    Usage::

       {% tags_for_model [model] as [varname] %}

    The model is specified in ``[appname].[modelname]`` format.

    Extended usage::

       {% tags_for_model [model] as [varname] with counts %}

    If specified - by providing extra ``with counts`` arguments - adds
    a ``count`` attribute to each tag containing the number of
    instances of the given model which have been tagged with it.

    Examples::

       {% tags_for_model products.Widget as widget_tags %}
       {% tags_for_model products.Widget as widget_tags with counts %}

    """
    bits = token.contents.split()
    len_bits = len(bits)
    if len_bits not in (4, 6):
        raise TemplateSyntaxError(_('%s tag requires either three or five arguments') % bits[0])
    if bits[2] != 'as':
        raise TemplateSyntaxError(_("second argument to %s tag must be 'as'") % bits[0])
    if len_bits == 6:
        if bits[4] != 'with':
            raise TemplateSyntaxError(_("if given, fourth argument to %s tag must be 'with'") % bits[0])
        if bits[5] != 'counts':
            raise TemplateSyntaxError(_("if given, fifth argument to %s tag must be 'counts'") % bits[0])
    if len_bits == 4:
        return TagsForModelNode(bits[1], bits[3], counts=False)
    else:
        return TagsForModelNode(bits[1], bits[3], counts=True)

def do_tag_cloud_for_model(parser, token):
    """
    Retrieves a list of ``Tag`` objects for a given model, with tag
    cloud attributes set, and stores them in a context variable.

    Usage::

       {% tag_cloud_for_model [model] as [varname] %}

    The model is specified in ``[appname].[modelname]`` format.

    Extended usage::

       {% tag_cloud_for_model [model] as [varname] with [options] %}

    Extra options can be provided after an optional ``with`` argument,
    with each option being specified in ``[name]=[value]`` format. Valid
    extra options are:

       ``steps``
          Integer. Defines the range of font sizes.

       ``min_count``
          Integer. Defines the minimum number of times a tag must have
          been used to appear in the cloud.

       ``distribution``
          One of ``linear`` or ``log``. Defines the font-size
          distribution algorithm to use when generating the tag cloud.

    Examples::

       {% tag_cloud_for_model products.Widget as widget_tags %}
       {% tag_cloud_for_model products.Widget as widget_tags with steps=9 min_count=3 distribution=log %}

    """
    bits = token.contents.split()
    len_bits = len(bits)
    if len_bits != 4 and len_bits not in range(6, 9):
        raise TemplateSyntaxError(_('%s tag requires either three or between five and seven arguments') % bits[0])
    if bits[2] != 'as':
        raise TemplateSyntaxError(_("second argument to %s tag must be 'as'") % bits[0])
    kwargs = {}
    if len_bits > 5:
        if bits[4] != 'with':
            raise TemplateSyntaxError(_("if given, fourth argument to %s tag must be 'with'") % bits[0])
        for i in range(5, len_bits):
            try:
                name, value = bits[i].split('=')
                if name == 'steps' or name == 'min_count':
                    try:
                        kwargs[str(name)] = int(value)
                    except ValueError:
                        raise TemplateSyntaxError(_("%(tag)s tag's '%(option)s' option was not a valid integer: '%(value)s'") % {
                            'tag': bits[0],
                            'option': name,
                            'value': value,
                        })
                elif name == 'distribution':
                    if value in ['linear', 'log']:
                        kwargs[str(name)] = {'linear': LINEAR, 'log': LOGARITHMIC}[value]
                    else:
                        raise TemplateSyntaxError(_("%(tag)s tag's '%(option)s' option was not a valid choice: '%(value)s'") % {
                            'tag': bits[0],
                            'option': name,
                            'value': value,
                        })
                else:
                    raise TemplateSyntaxError(_("%(tag)s tag was given an invalid option: '%(option)s'") % {
                        'tag': bits[0],
                        'option': name,
                    })
            except ValueError:
                raise TemplateSyntaxError(_("%(tag)s tag was given a badly formatted option: '%(option)s'") % {
                    'tag': bits[0],
                    'option': bits[i],
                })
    return TagCloudForModelNode(bits[1], bits[3], **kwargs)

def do_tags_for_object(parser, token):
    """
    Retrieves a list of ``Tag`` objects associated with an object and
    stores them in a context variable.

    Usage::

       {% tags_for_object [object] as [varname] %}

    Example::

        {% tags_for_object foo_object as tag_list %}
    """
    bits = token.contents.split()
    if len(bits) != 4:
        raise TemplateSyntaxError(_('%s tag requires exactly three arguments') % bits[0])
    if bits[2] != 'as':
        raise TemplateSyntaxError(_("second argument to %s tag must be 'as'") % bits[0])
    return TagsForObjectNode(bits[1], bits[3])

def do_tagged_objects(parser, token):
    """
    Retrieves a list of instances of a given model which are tagged with
    a given ``Tag`` and stores them in a context variable.

    Usage::

       {% tagged_objects [tag] in [model] as [varname] %}

    The model is specified in ``[appname].[modelname]`` format.

    The tag must be an instance of a ``Tag``, not the name of a tag.

    Example::

        {% tagged_objects comedy_tag in tv.Show as comedies %}

    """
    bits = token.contents.split()
    if len(bits) != 6:
        raise TemplateSyntaxError(_('%s tag requires exactly five arguments') % bits[0])
    if bits[2] != 'in':
        raise TemplateSyntaxError(_("second argument to %s tag must be 'in'") % bits[0])
    if bits[4] != 'as':
        raise TemplateSyntaxError(_("fourth argument to %s tag must be 'as'") % bits[0])
    return TaggedObjectsNode(bits[1], bits[3], bits[5])

register.tag('tags_for_model', do_tags_for_model)
register.tag('tag_cloud_for_model', do_tag_cloud_for_model)
register.tag('tags_for_object', do_tags_for_object)
register.tag('tagged_objects', do_tagged_objects)

########NEW FILE########
__FILENAME__ = models
from django.db import models

from tagging.fields import TagField

class Perch(models.Model):
    size = models.IntegerField()
    smelly = models.BooleanField(default=True)

class Parrot(models.Model):
    state = models.CharField(max_length=50)
    perch = models.ForeignKey(Perch, null=True)

    def __unicode__(self):
        return self.state

    class Meta:
        ordering = ['state']

class Link(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Article(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']

class FormTest(models.Model):
    tags = TagField('Test', help_text='Test')

########NEW FILE########
__FILENAME__ = settings
import os
DIRNAME = os.path.dirname(__file__)

DEFAULT_CHARSET = 'utf-8'

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = os.path.join(DIRNAME, 'tagging_test.db')

#DATABASE_ENGINE = 'mysql'
#DATABASE_NAME = 'tagging_test'
#DATABASE_USER = 'root'
#DATABASE_PASSWORD = ''
#DATABASE_HOST = 'localhost'
#DATABASE_PORT = '3306'

#DATABASE_ENGINE = 'postgresql_psycopg2'
#DATABASE_NAME = 'tagging_test'
#DATABASE_USER = 'postgres'
#DATABASE_PASSWORD = ''
#DATABASE_HOST = 'localhost'
#DATABASE_PORT = '5432'

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'tagging',
    'tagging.tests',
)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
r"""
>>> import os
>>> from django import forms
>>> from tagging.forms import TagField
>>> from tagging import settings
>>> from tagging.models import Tag, TaggedItem
>>> from tagging.tests.models import Article, Link, Perch, Parrot, FormTest
>>> from tagging.utils import calculate_cloud, get_tag_list, get_tag, parse_tag_input
>>> from tagging.utils import LINEAR
>>> from tagging.validators import isTagList, isTag

#############
# Utilities #
#############

# Tag input ###################################################################

# Simple space-delimited tags
>>> parse_tag_input('one')
[u'one']
>>> parse_tag_input('one two')
[u'one', u'two']
>>> parse_tag_input('one two three')
[u'one', u'three', u'two']
>>> parse_tag_input('one one two two')
[u'one', u'two']

# Comma-delimited multiple words - an unquoted comma in the input will trigger
# this.
>>> parse_tag_input(',one')
[u'one']
>>> parse_tag_input(',one two')
[u'one two']
>>> parse_tag_input(',one two three')
[u'one two three']
>>> parse_tag_input('a-one, a-two and a-three')
[u'a-one', u'a-two and a-three']

# Double-quoted multiple words - a completed quote will trigger this.
# Unclosed quotes are ignored.
>>> parse_tag_input('"one')
[u'one']
>>> parse_tag_input('"one two')
[u'one', u'two']
>>> parse_tag_input('"one two three')
[u'one', u'three', u'two']
>>> parse_tag_input('"one two"')
[u'one two']
>>> parse_tag_input('a-one "a-two and a-three"')
[u'a-one', u'a-two and a-three']

# No loose commas - split on spaces
>>> parse_tag_input('one two "thr,ee"')
[u'one', u'thr,ee', u'two']

# Loose commas - split on commas
>>> parse_tag_input('"one", two three')
[u'one', u'two three']

# Double quotes can contain commas
>>> parse_tag_input('a-one "a-two, and a-three"')
[u'a-one', u'a-two, and a-three']
>>> parse_tag_input('"two", one, one, two, "one"')
[u'one', u'two']

# Bad users! Naughty users!
>>> parse_tag_input(None)
[]
>>> parse_tag_input('')
[]
>>> parse_tag_input('"')
[]
>>> parse_tag_input('""')
[]
>>> parse_tag_input('"' * 7)
[]
>>> parse_tag_input(',,,,,,')
[]
>>> parse_tag_input('",",",",",",","')
[u',']
>>> parse_tag_input('a-one "a-two" and "a-three')
[u'a-one', u'a-three', u'a-two', u'and']

# Normalised Tag list input ###################################################
>>> cheese = Tag.objects.create(name='cheese')
>>> toast = Tag.objects.create(name='toast')
>>> get_tag_list(cheese)
[<Tag: cheese>]
>>> get_tag_list('cheese toast')
[<Tag: cheese>, <Tag: toast>]
>>> get_tag_list('cheese,toast')
[<Tag: cheese>, <Tag: toast>]
>>> get_tag_list([])
[]
>>> get_tag_list(['cheese', 'toast'])
[<Tag: cheese>, <Tag: toast>]
>>> get_tag_list([cheese.id, toast.id])
[<Tag: cheese>, <Tag: toast>]
>>> get_tag_list(['cheese', 'toast', 'ŠĐĆŽćžšđ'])
[<Tag: cheese>, <Tag: toast>]
>>> get_tag_list([cheese, toast])
[<Tag: cheese>, <Tag: toast>]
>>> get_tag_list((cheese, toast))
(<Tag: cheese>, <Tag: toast>)
>>> get_tag_list(Tag.objects.filter(name__in=['cheese', 'toast']))
[<Tag: cheese>, <Tag: toast>]
>>> get_tag_list(['cheese', toast])
Traceback (most recent call last):
    ...
ValueError: If a list or tuple of tags is provided, they must all be tag names, Tag objects or Tag ids.
>>> get_tag_list(29)
Traceback (most recent call last):
    ...
ValueError: The tag input given was invalid.

# Normalised Tag input
>>> get_tag(cheese)
<Tag: cheese>
>>> get_tag('cheese')
<Tag: cheese>
>>> get_tag(cheese.id)
<Tag: cheese>
>>> get_tag('mouse')

# Tag clouds ##################################################################
>>> tags = []
>>> for line in open(os.path.join(os.path.dirname(__file__), 'tags.txt')).readlines():
...     name, count = line.rstrip().split()
...     tag = Tag(name=name)
...     tag.count = int(count)
...     tags.append(tag)

>>> sizes = {}
>>> for tag in calculate_cloud(tags, steps=5):
...     sizes[tag.font_size] = sizes.get(tag.font_size, 0) + 1

# This isn't a pre-calculated test, just making sure it's consistent
>>> sizes
{1: 48, 2: 30, 3: 19, 4: 15, 5: 10}

>>> sizes = {}
>>> for tag in calculate_cloud(tags, steps=5, distribution=LINEAR):
...     sizes[tag.font_size] = sizes.get(tag.font_size, 0) + 1

# This isn't a pre-calculated test, just making sure it's consistent
>>> sizes
{1: 97, 2: 12, 3: 7, 4: 2, 5: 4}

>>> calculate_cloud(tags, steps=5, distribution='cheese')
Traceback (most recent call last):
    ...
ValueError: Invalid distribution algorithm specified: cheese.

# Validators ##################################################################

>>> isTagList('foo qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvbn bar', {})
Traceback (most recent call last):
    ...
ValidationError: [u'Each tag may be no more than 50 characters long.']

>>> isTag('"test"', {})
>>> isTag(',test', {})
>>> isTag('f o o', {})
Traceback (most recent call last):
    ...
ValidationError: [u'Multiple tags were given.']
>>> isTagList('foo qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvbn bar', {})
Traceback (most recent call last):
    ...
ValidationError: [u'Each tag may be no more than 50 characters long.']

###########
# Tagging #
###########

# Basic tagging ###############################################################

>>> dead = Parrot.objects.create(state='dead')
>>> Tag.objects.update_tags(dead, 'foo,bar,"ter"')
>>> Tag.objects.get_for_object(dead)
[<Tag: bar>, <Tag: foo>, <Tag: ter>]
>>> Tag.objects.update_tags(dead, '"foo" bar "baz"')
>>> Tag.objects.get_for_object(dead)
[<Tag: bar>, <Tag: baz>, <Tag: foo>]
>>> Tag.objects.add_tag(dead, 'foo')
>>> Tag.objects.get_for_object(dead)
[<Tag: bar>, <Tag: baz>, <Tag: foo>]
>>> Tag.objects.add_tag(dead, 'zip')
>>> Tag.objects.get_for_object(dead)
[<Tag: bar>, <Tag: baz>, <Tag: foo>, <Tag: zip>]
>>> Tag.objects.add_tag(dead, '    ')
Traceback (most recent call last):
    ...
AttributeError: No tags were given: "    ".
>>> Tag.objects.add_tag(dead, 'one two')
Traceback (most recent call last):
    ...
AttributeError: Multiple tags were given: "one two".

# Note that doctest in Python 2.4 (and maybe 2.5?) doesn't support non-ascii
# characters in output, so we're displaying the repr() here.
>>> Tag.objects.update_tags(dead, 'ŠĐĆŽćžšđ')
>>> repr(Tag.objects.get_for_object(dead))
'[<Tag: \xc5\xa0\xc4\x90\xc4\x86\xc5\xbd\xc4\x87\xc5\xbe\xc5\xa1\xc4\x91>]'

>>> Tag.objects.update_tags(dead, None)
>>> Tag.objects.get_for_object(dead)
[]

# Using a model's TagField
>>> f1 = FormTest.objects.create(tags=u'test3 test2 test1')
>>> Tag.objects.get_for_object(f1)
[<Tag: test1>, <Tag: test2>, <Tag: test3>]
>>> f1.tags = u'test4'
>>> f1.save()
>>> Tag.objects.get_for_object(f1)
[<Tag: test4>]
>>> f1.tags = ''
>>> f1.save()
>>> Tag.objects.get_for_object(f1)
[]

# Forcing tags to lowercase
>>> settings.FORCE_LOWERCASE_TAGS = True
>>> Tag.objects.update_tags(dead, 'foO bAr Ter')
>>> Tag.objects.get_for_object(dead)
[<Tag: bar>, <Tag: foo>, <Tag: ter>]
>>> Tag.objects.update_tags(dead, 'foO bAr baZ')
>>> Tag.objects.get_for_object(dead)
[<Tag: bar>, <Tag: baz>, <Tag: foo>]
>>> Tag.objects.add_tag(dead, 'FOO')
>>> Tag.objects.get_for_object(dead)
[<Tag: bar>, <Tag: baz>, <Tag: foo>]
>>> Tag.objects.add_tag(dead, 'Zip')
>>> Tag.objects.get_for_object(dead)
[<Tag: bar>, <Tag: baz>, <Tag: foo>, <Tag: zip>]
>>> Tag.objects.update_tags(dead, None)
>>> f1.tags = u'TEST5'
>>> f1.save()
>>> Tag.objects.get_for_object(f1)
[<Tag: test5>]
>>> f1.tags
u'test5'

# Retrieving tags by Model ####################################################

>>> Tag.objects.usage_for_model(Parrot)
[]
>>> parrot_details = (
...     ('pining for the fjords', 9, True,  'foo bar'),
...     ('passed on',             6, False, 'bar baz ter'),
...     ('no more',               4, True,  'foo ter'),
...     ('late',                  2, False, 'bar ter'),
... )

>>> for state, perch_size, perch_smelly, tags in parrot_details:
...     perch = Perch.objects.create(size=perch_size, smelly=perch_smelly)
...     parrot = Parrot.objects.create(state=state, perch=perch)
...     Tag.objects.update_tags(parrot, tags)

>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_model(Parrot, counts=True)]
[(u'bar', 3), (u'baz', 1), (u'foo', 2), (u'ter', 3)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_model(Parrot, min_count=2)]
[(u'bar', 3), (u'foo', 2), (u'ter', 3)]

# Limiting results to a subset of the model
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(state='no more'))]
[(u'foo', 1), (u'ter', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(state__startswith='p'))]
[(u'bar', 2), (u'baz', 1), (u'foo', 1), (u'ter', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(perch__size__gt=4))]
[(u'bar', 2), (u'baz', 1), (u'foo', 1), (u'ter', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(perch__smelly=True))]
[(u'bar', 1), (u'foo', 2), (u'ter', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.usage_for_model(Parrot, min_count=2, filters=dict(perch__smelly=True))]
[(u'foo', 2)]
>>> [(tag.name, hasattr(tag, 'counts')) for tag in Tag.objects.usage_for_model(Parrot, filters=dict(perch__size__gt=4))]
[(u'bar', False), (u'baz', False), (u'foo', False), (u'ter', False)]
>>> [(tag.name, hasattr(tag, 'counts')) for tag in Tag.objects.usage_for_model(Parrot, filters=dict(perch__size__gt=99))]
[]

# Related tags
>>> [(tag.name, tag.count) for tag in Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar']), Parrot, counts=True)]
[(u'baz', 1), (u'foo', 1), (u'ter', 2)]
>>> [(tag.name, tag.count) for tag in Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar']), Parrot, min_count=2)]
[(u'ter', 2)]
>>> [tag.name for tag in Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar']), Parrot, counts=False)]
[u'baz', u'foo', u'ter']
>>> [(tag.name, tag.count) for tag in Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar', 'ter']), Parrot, counts=True)]
[(u'baz', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar', 'ter', 'baz']), Parrot, counts=True)]
[]

# Once again, with feeling (strings)
>>> [(tag.name, tag.count) for tag in Tag.objects.related_for_model('bar', Parrot, counts=True)]
[(u'baz', 1), (u'foo', 1), (u'ter', 2)]
>>> [(tag.name, tag.count) for tag in Tag.objects.related_for_model('bar', Parrot, min_count=2)]
[(u'ter', 2)]
>>> [tag.name for tag in Tag.objects.related_for_model('bar', Parrot, counts=False)]
[u'baz', u'foo', u'ter']
>>> [(tag.name, tag.count) for tag in Tag.objects.related_for_model(['bar', 'ter'], Parrot, counts=True)]
[(u'baz', 1)]
>>> [(tag.name, tag.count) for tag in Tag.objects.related_for_model(['bar', 'ter', 'baz'], Parrot, counts=True)]
[]

# Retrieving tagged objects by Model ##########################################

>>> foo = Tag.objects.get(name='foo')
>>> bar = Tag.objects.get(name='bar')
>>> baz = Tag.objects.get(name='baz')
>>> ter = Tag.objects.get(name='ter')
>>> TaggedItem.objects.get_by_model(Parrot, foo)
[<Parrot: no more>, <Parrot: pining for the fjords>]
>>> TaggedItem.objects.get_by_model(Parrot, bar)
[<Parrot: late>, <Parrot: passed on>, <Parrot: pining for the fjords>]

# Intersections are supported
>>> TaggedItem.objects.get_by_model(Parrot, [foo, baz])
[]
>>> TaggedItem.objects.get_by_model(Parrot, [foo, bar])
[<Parrot: pining for the fjords>]
>>> TaggedItem.objects.get_by_model(Parrot, [bar, ter])
[<Parrot: late>, <Parrot: passed on>]

# You can also pass Tag QuerySets
>>> TaggedItem.objects.get_by_model(Parrot, Tag.objects.filter(name__in=['foo', 'baz']))
[]
>>> TaggedItem.objects.get_by_model(Parrot, Tag.objects.filter(name__in=['foo', 'bar']))
[<Parrot: pining for the fjords>]
>>> TaggedItem.objects.get_by_model(Parrot, Tag.objects.filter(name__in=['bar', 'ter']))
[<Parrot: late>, <Parrot: passed on>]

# You can also pass strings and lists of strings
>>> TaggedItem.objects.get_by_model(Parrot, 'foo baz')
[]
>>> TaggedItem.objects.get_by_model(Parrot, 'foo bar')
[<Parrot: pining for the fjords>]
>>> TaggedItem.objects.get_by_model(Parrot, 'bar ter')
[<Parrot: late>, <Parrot: passed on>]
>>> TaggedItem.objects.get_by_model(Parrot, ['foo', 'baz'])
[]
>>> TaggedItem.objects.get_by_model(Parrot, ['foo', 'bar'])
[<Parrot: pining for the fjords>]
>>> TaggedItem.objects.get_by_model(Parrot, ['bar', 'ter'])
[<Parrot: late>, <Parrot: passed on>]

# Issue 50 - Get by non-existent tag
>>> TaggedItem.objects.get_by_model(Parrot, 'argatrons')
[]

# Unions
>>> TaggedItem.objects.get_union_by_model(Parrot, ['foo', 'ter'])
[<Parrot: late>, <Parrot: no more>, <Parrot: passed on>, <Parrot: pining for the fjords>]
>>> TaggedItem.objects.get_union_by_model(Parrot, ['bar', 'baz'])
[<Parrot: late>, <Parrot: passed on>, <Parrot: pining for the fjords>]

# Retrieving related objects by Model #########################################

# Related instances of the same Model
>>> l1 = Link.objects.create(name='link 1')
>>> Tag.objects.update_tags(l1, 'tag1 tag2 tag3 tag4 tag5')
>>> l2 = Link.objects.create(name='link 2')
>>> Tag.objects.update_tags(l2, 'tag1 tag2 tag3')
>>> l3 = Link.objects.create(name='link 3')
>>> Tag.objects.update_tags(l3, 'tag1')
>>> l4 = Link.objects.create(name='link 4')
>>> TaggedItem.objects.get_related(l1, Link)
[<Link: link 2>, <Link: link 3>]
>>> TaggedItem.objects.get_related(l1, Link, num=1)
[<Link: link 2>]
>>> TaggedItem.objects.get_related(l4, Link)
[]

# Related instance of a different Model
>>> a1 = Article.objects.create(name='article 1')
>>> Tag.objects.update_tags(a1, 'tag1 tag2 tag3 tag4')
>>> TaggedItem.objects.get_related(a1, Link)
[<Link: link 1>, <Link: link 2>, <Link: link 3>]
>>> Tag.objects.update_tags(a1, 'tag6')
>>> TaggedItem.objects.get_related(a1, Link)
[]

################
# Model Fields #
################

# TagField ####################################################################

# Ensure that automatically created forms use TagField
>>> class TestForm(forms.ModelForm):
...     class Meta:
...         model = FormTest
>>> form = TestForm()
>>> form.fields['tags'].__class__.__name__
'TagField'

# Recreating string representaions of tag lists ###############################
>>> plain = Tag.objects.create(name='plain')
>>> spaces = Tag.objects.create(name='spa ces')
>>> comma = Tag.objects.create(name='com,ma')

>>> from tagging.utils import edit_string_for_tags
>>> edit_string_for_tags([plain])
u'plain'
>>> edit_string_for_tags([plain, spaces])
u'plain, spa ces'
>>> edit_string_for_tags([plain, spaces, comma])
u'plain, spa ces, "com,ma"'
>>> edit_string_for_tags([plain, comma])
u'plain "com,ma"'
>>> edit_string_for_tags([comma, spaces])
u'"com,ma", spa ces'

###############
# Form Fields #
###############

>>> t = TagField()
>>> t.clean('foo')
u'foo'
>>> t.clean('foo bar baz')
u'foo bar baz'
>>> t.clean('foo,bar,baz')
u'foo,bar,baz'
>>> t.clean('foo, bar, baz')
u'foo, bar, baz'
>>> t.clean('foo qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvb bar')
u'foo qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvb bar'
>>> t.clean('foo qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvbn bar')
Traceback (most recent call last):
    ...
ValidationError: [u'Each tag may be no more than 50 characters long.']
"""

########NEW FILE########
__FILENAME__ = utils
"""
Tagging utilities - from user tag input parsing to tag cloud
calculation.
"""
import math
import types

from django.db.models.query import QuerySet
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext as _

# Python 2.3 compatibility
try:
    set
except NameError:
    from sets import Set as set

def parse_tag_input(input):
    """
    Parses tag input, with multiple word input being activated and
    delineated by commas and double quotes. Quotes take precedence, so
    they may contain commas.

    Returns a sorted list of unique tag names.
    """
    if not input:
        return []

    input = force_unicode(input)

    # Special case - if there are no commas or double quotes in the
    # input, we don't *do* a recall... I mean, we know we only need to
    # split on spaces.
    if u',' not in input and u'"' not in input:
        words = list(set(split_strip(input, u' ')))
        words.sort()
        return words

    words = []
    buffer = []
    # Defer splitting of non-quoted sections until we know if there are
    # any unquoted commas.
    to_be_split = []
    saw_loose_comma = False
    open_quote = False
    i = iter(input)
    try:
        while 1:
            c = i.next()
            if c == u'"':
                if buffer:
                    to_be_split.append(u''.join(buffer))
                    buffer = []
                # Find the matching quote
                open_quote = True
                c = i.next()
                while c != u'"':
                    buffer.append(c)
                    c = i.next()
                if buffer:
                    word = u''.join(buffer).strip()
                    if word:
                        words.append(word)
                    buffer = []
                open_quote = False
            else:
                if not saw_loose_comma and c == u',':
                    saw_loose_comma = True
                buffer.append(c)
    except StopIteration:
        # If we were parsing an open quote which was never closed treat
        # the buffer as unquoted.
        if buffer:
            if open_quote and u',' in buffer:
                saw_loose_comma = True
            to_be_split.append(u''.join(buffer))
    if to_be_split:
        if saw_loose_comma:
            delimiter = u','
        else:
            delimiter = u' '
        for chunk in to_be_split:
            words.extend(split_strip(chunk, delimiter))
    words = list(set(words))
    words.sort()
    return words

def split_strip(input, delimiter=u','):
    """
    Splits ``input`` on ``delimiter``, stripping each resulting string
    and returning a list of non-empty strings.
    """
    if not input:
        return []

    words = [w.strip() for w in input.split(delimiter)]
    return [w for w in words if w]

def edit_string_for_tags(tags):
    """
    Given list of ``Tag`` instances, creates a string representation of
    the list suitable for editing by the user, such that submitting the
    given string representation back without changing it will give the
    same list of tags.

    Tag names which contain commas will be double quoted.

    If any tag name which isn't being quoted contains whitespace, the
    resulting string of tag names will be comma-delimited, otherwise
    it will be space-delimited.
    """
    names = []
    use_commas = False
    for tag in tags:
        name = tag.name
        if u',' in name:
            names.append('"%s"' % name)
            continue
        elif u' ' in name:
            if not use_commas:
                use_commas = True
        names.append(name)
    if use_commas:
        glue = u', '
    else:
        glue = u' '
    return glue.join(names)

def get_queryset_and_model(queryset_or_model):
    """
    Given a ``QuerySet`` or a ``Model``, returns a two-tuple of
    (queryset, model).

    If a ``Model`` is given, the ``QuerySet`` returned will be created
    using its default manager.
    """
    try:
        return queryset_or_model, queryset_or_model.model
    except AttributeError:
        return queryset_or_model._default_manager.all(), queryset_or_model

def get_tag_list(tags):
    """
    Utility function for accepting tag input in a flexible manner.

    If a ``Tag`` object is given, it will be returned in a list as
    its single occupant.

    If given, the tag names in the following will be used to create a
    ``Tag`` ``QuerySet``:

       * A string, which may contain multiple tag names.
       * A list or tuple of strings corresponding to tag names.
       * A list or tuple of integers corresponding to tag ids.

    If given, the following will be returned as-is:

       * A list or tuple of ``Tag`` objects.
       * A ``Tag`` ``QuerySet``.

    """
    from tagging.models import Tag
    if isinstance(tags, Tag):
        return [tags]
    elif isinstance(tags, QuerySet) and tags.model is Tag:
        return tags
    elif isinstance(tags, types.StringTypes):
        return Tag.objects.filter(name__in=parse_tag_input(tags))
    elif isinstance(tags, (types.ListType, types.TupleType)):
        if len(tags) == 0:
            return tags
        contents = set()
        for item in tags:
            if isinstance(item, types.StringTypes):
                contents.add('string')
            elif isinstance(item, Tag):
                contents.add('tag')
            elif isinstance(item, (types.IntType, types.LongType)):
                contents.add('int')
        if len(contents) == 1:
            if 'string' in contents:
                return Tag.objects.filter(name__in=[force_unicode(tag) \
                                                    for tag in tags])
            elif 'tag' in contents:
                return tags
            elif 'int' in contents:
                return Tag.objects.filter(id__in=tags)
        else:
            raise ValueError(_('If a list or tuple of tags is provided, they must all be tag names, Tag objects or Tag ids.'))
    else:
        raise ValueError(_('The tag input given was invalid.'))

def get_tag(tag):
    """
    Utility function for accepting single tag input in a flexible
    manner.

    If a ``Tag`` object is given it will be returned as-is; if a
    string or integer are given, they will be used to lookup the
    appropriate ``Tag``.

    If no matching tag can be found, ``None`` will be returned.
    """
    from tagging.models import Tag
    if isinstance(tag, Tag):
        return tag

    try:
        if isinstance(tag, types.StringTypes):
            return Tag.objects.get(name=tag)
        elif isinstance(tag, (types.IntType, types.LongType)):
            return Tag.objects.get(id=tag)
    except Tag.DoesNotExist:
        pass

    return None

# Font size distribution algorithms
LOGARITHMIC, LINEAR = 1, 2

def _calculate_thresholds(min_weight, max_weight, steps):
    delta = (max_weight - min_weight) / float(steps)
    return [min_weight + i * delta for i in range(1, steps + 1)]

def _calculate_tag_weight(weight, max_weight, distribution):
    """
    Logarithmic tag weight calculation is based on code from the
    `Tag Cloud`_ plugin for Mephisto, by Sven Fuchs.

    .. _`Tag Cloud`: http://www.artweb-design.de/projects/mephisto-plugin-tag-cloud
    """
    if distribution == LINEAR or max_weight == 1:
        return weight
    elif distribution == LOGARITHMIC:
        return math.log(weight) * max_weight / math.log(max_weight)
    raise ValueError(_('Invalid distribution algorithm specified: %s.') % distribution)

def calculate_cloud(tags, steps=4, distribution=LOGARITHMIC):
    """
    Add a ``font_size`` attribute to each tag according to the
    frequency of its use, as indicated by its ``count``
    attribute.

    ``steps`` defines the range of font sizes - ``font_size`` will
    be an integer between 1 and ``steps`` (inclusive).

    ``distribution`` defines the type of font size distribution
    algorithm which will be used - logarithmic or linear. It must be
    one of ``tagging.utils.LOGARITHMIC`` or ``tagging.utils.LINEAR``.
    """
    if len(tags) > 0:
        counts = [tag.count for tag in tags]
        min_weight = float(min(counts))
        max_weight = float(max(counts))
        thresholds = _calculate_thresholds(min_weight, max_weight, steps)
        for tag in tags:
            font_set = False
            tag_weight = _calculate_tag_weight(tag.count, max_weight, distribution)
            for i in range(steps):
                if not font_set and tag_weight <= thresholds[i]:
                    tag.font_size = i + 1
                    font_set = True
    return tags

########NEW FILE########
__FILENAME__ = views
"""
Tagging related views.
"""
from django.http import Http404
from django.utils.translation import ugettext as _
from django.views.generic.list_detail import object_list

from tagging.models import Tag, TaggedItem
from tagging.utils import get_tag, get_queryset_and_model

def tagged_object_list(request, queryset_or_model=None, tag=None,
        related_tags=False, related_tag_counts=True, **kwargs):
    """
    A thin wrapper around
    ``django.views.generic.list_detail.object_list`` which creates a
    ``QuerySet`` containing instances of the given queryset or model
    tagged with the given tag.

    In addition to the context variables set up by ``object_list``, a
    ``tag`` context variable will contain the ``Tag`` instance for the
    tag.

    If ``related_tags`` is ``True``, a ``related_tags`` context variable
    will contain tags related to the given tag for the given model.
    Additionally, if ``related_tag_counts`` is ``True``, each related
    tag will have a ``count`` attribute indicating the number of items
    which have it in addition to the given tag.
    """
    if queryset_or_model is None:
        try:
            queryset_or_model = kwargs.pop('queryset_or_model')
        except KeyError:
            raise AttributeError(_('tagged_object_list must be called with a queryset or a model.'))

    if tag is None:
        try:
            tag = kwargs.pop('tag')
        except KeyError:
            raise AttributeError(_('tagged_object_list must be called with a tag.'))

    tag_instance = get_tag(tag)
    if tag_instance is None:
        raise Http404(_('No Tag found matching "%s".') % tag)
    queryset = TaggedItem.objects.get_by_model(queryset_or_model, tag_instance)
    if not kwargs.has_key('extra_context'):
        kwargs['extra_context'] = {}
    kwargs['extra_context']['tag'] = tag_instance
    if related_tags:
        kwargs['extra_context']['related_tags'] = \
            Tag.objects.related_for_model(tag_instance, queryset_or_model,
                                          counts=related_tag_counts)
    return object_list(request, queryset, **kwargs)

########NEW FILE########
__FILENAME__ = fetchers
# -*- test-case-name: urljr.test.test_fetchers -*-
"""
This module contains the HTTP fetcher interface and several implementations.
"""

__all__ = ['fetch', 'getDefaultFetcher', 'setDefaultFetcher', 'HTTPResponse',
           'HTTPFetcher', 'createHTTPFetcher', 'HTTPFetchingError', 'HTTPError']

import urllib2
import time
import cStringIO
import sys

import urljr.urinorm

# try to import pycurl, which will let us use CurlHTTPFetcher
try:
    import pycurl
except ImportError:
    pycurl = None

def fetch(url, body=None, headers=None):
    """Invoke the fetch method on the default fetcher. Most users
    should need only this method.

    @raises: any exceptions that may be raised by the default fetcher
    """
    fetcher = getDefaultFetcher()
    return fetcher.fetch(url, body, headers)

def createHTTPFetcher():
    """Create a default HTTP fetcher instance

    prefers Curl to urllib2."""
    if pycurl is None:
        fetcher = Urllib2Fetcher()
    else:
        fetcher = CurlHTTPFetcher()

    return fetcher

# Contains the currently set HTTP fetcher. If it is set to None, the
# library will call createHTTPFetcher() to set it. Do not access this
# variable outside of this module.
_default_fetcher = None

def getDefaultFetcher():
    """Return the default fetcher instance
    if no fetcher has been set, it will create a default fetcher.

    @return: the default fetcher
    @rtype: HTTPFetcher
    """
    global _default_fetcher

    if _default_fetcher is None:
        setDefaultFetcher(createHTTPFetcher())

    return _default_fetcher

def setDefaultFetcher(fetcher, wrap_exceptions=True):
    """Set the default fetcher

    @param fetcher: The fetcher to use as the default HTTP fetcher
    @type fetcher: HTTPFetcher

    @param wrap_exceptions: Whether to wrap exceptions thrown by the
        fetcher wil HTTPFetchingError so that they may be caught
        easier. By default, exceptions will be wrapped. In general,
        unwrapped fetchers are useful for debugging of fetching errors
        or if your fetcher raises well-known exceptions that you would
        like to catch.
    @type wrap_exceptions: bool
    """
    global _default_fetcher
    if fetcher is None or not wrap_exceptions:
        _default_fetcher = fetcher
    else:
        _default_fetcher = ExceptionWrappingFetcher(fetcher)

def usingCurl():
    """Whether the currently set HTTP fetcher is a Curl HTTP fetcher."""
    return isinstance(getDefaultFetcher(), CurlHTTPFetcher)

class HTTPResponse(object):
    """XXX document attributes"""
    headers = None
    status = None
    body = None
    final_url = None

    def __init__(self, final_url=None, status=None, headers=None, body=None):
        self.final_url = final_url
        self.status = status
        self.headers = headers
        self.body = body

    def __repr__(self):
        return "<%s status %s for %s>" % (self.__class__.__name__,
                                          self.status,
                                          self.final_url)

class HTTPFetcher(object):
    """
    This class is the interface for urljr HTTP fetchers.  This
    interface is only important if you need to write a new fetcher for
    some reason.
    """

    def fetch(self, url, body=None, headers=None):
        """
        This performs an HTTP POST or GET, following redirects along
        the way. If a body is specified, then the request will be a
        POST. Otherwise, it will be a GET.


        @param headers: HTTP headers to include with the request
        @type headers: {str:str}

        @return: An object representing the server's HTTP response. If
            there are network or protocol errors, an exception will be
            raised. HTTP error responses, like 404 or 500, do not
            cause exceptions.

        @rtype: L{HTTPResponse}

        @raise Exception: Different implementations will raise
            different errors based on the underlying HTTP library.
        """
        raise NotImplementedError

def _allowedURL(url):
    return url.startswith('http://') or url.startswith('https://')

class HTTPFetchingError(Exception):
    """Exception that is wrapped around all exceptions that are raised
    by the underlying fetcher when using the ExceptionWrappingFetcher

    @var why: The exception that caused this exception
    """
    def __init__(self, why=None):
        Exception.__init__(self, why)
        self.why = why

class ExceptionWrappingFetcher(HTTPFetcher):
    """Fetcher that wraps another fetcher, causing all exceptions

    @var uncaught_exceptions: Exceptions that should be exposed to the
        user if they are raised by the fetch call
    """

    uncaught_exceptions = (SystemExit, KeyboardInterrupt, MemoryError)

    def __init__(self, fetcher):
        self.fetcher = fetcher

    def fetch(self, *args, **kwargs):
        try:
            return self.fetcher.fetch(*args, **kwargs)
        except self.uncaught_exceptions:
            raise
        except:
            exc_cls, exc_inst = sys.exc_info()[:2]
            if exc_inst is None:
                # string exceptions
                exc_inst = exc_cls

            raise HTTPFetchingError(why=exc_inst)

class Urllib2Fetcher(HTTPFetcher):
    """An C{L{HTTPFetcher}} that uses urllib2.
    """
    def fetch(self, url, body=None, headers=None):
        if not _allowedURL(url):
            raise ValueError('Bad URL scheme: %r' % (url,))

        if headers is None:
            headers = {}

        req = urllib2.Request(url, data=body, headers=headers)
        try:
            f = urllib2.urlopen(req)
            try:
                return self._makeResponse(f)
            finally:
                f.close()
        except urllib2.HTTPError, why:
            try:
                return self._makeResponse(why)
            finally:
                why.close()

    def _makeResponse(self, urllib2_response):
        resp = HTTPResponse()
        resp.body = urllib2_response.read()
        resp.final_url = urllib2_response.geturl()
        resp.headers = dict(urllib2_response.info().items())

        if hasattr(urllib2_response, 'code'):
            resp.status = urllib2_response.code
        else:
            resp.status = 200

        return resp

class HTTPError(HTTPFetchingError):
    """
    This exception is raised by the C{L{CurlHTTPFetcher}} when it
    encounters an exceptional situation fetching a URL.
    """
    pass

# XXX: define what we mean by paranoid, and make sure it is.
class CurlHTTPFetcher(HTTPFetcher):
    """
    An C{L{HTTPFetcher}} that uses pycurl for fetching.
    See U{http://pycurl.sourceforge.net/}.
    """
    ALLOWED_TIME = 20 # seconds

    def __init__(self):
        HTTPFetcher.__init__(self)
        if pycurl is None:
            raise RuntimeError('Cannot find pycurl library')

    def _parseHeaders(self, header_file):
        header_file.seek(0)

        # Remove the status line from the beginning of the input
        unused_http_status_line = header_file.readline()
        lines = [line.strip() for line in header_file]

        # and the blank line from the end
        empty_line = lines.pop()
        if empty_line:
            raise HTTPError("No blank line at end of headers: %r" % (line,))

        headers = {}
        for line in lines:
            try:
                name, value = line.split(':', 1)
            except ValueError:
                raise HTTPError(
                    "Malformed HTTP header line in response: %r" % (line,))

            value = value.strip()

            # HTTP headers are case-insensitive
            name = name.lower()
            headers[name] = value

        return headers

    def _checkURL(self, url):
        # XXX: document that this can be overridden to match desired policy
        # XXX: make sure url is well-formed and routeable
        return _allowedURL(url)

    def fetch(self, url, body=None, headers=None):
        stop = int(time.time()) + self.ALLOWED_TIME
        off = self.ALLOWED_TIME

        header_list = []
        if headers is not None:
            for header_name, header_value in headers.iteritems():
                header_list.append('%s: %s' % (header_name, header_value))

        c = pycurl.Curl()
        try:
            c.setopt(pycurl.NOSIGNAL, 1)

            if header_list:
                c.setopt(pycurl.HTTPHEADER, header_list)

            # Presence of a body indicates that we should do a POST
            if body is not None:
                c.setopt(pycurl.POST, 1)
                c.setopt(pycurl.POSTFIELDS, body)

            while off > 0:
                if not self._checkURL(url):
                    raise HTTPError("Fetching URL not allowed: %r" % (url,))

                data = cStringIO.StringIO()
                response_header_data = cStringIO.StringIO()
                c.setopt(pycurl.WRITEFUNCTION, data.write)
                c.setopt(pycurl.HEADERFUNCTION, response_header_data.write)
                c.setopt(pycurl.TIMEOUT, off)
                c.setopt(pycurl.URL, urljr.urinorm.urinorm(url))

                c.perform()

                response_headers = self._parseHeaders(response_header_data)
                code = c.getinfo(pycurl.RESPONSE_CODE)
                if code in [301, 302, 303, 307]:
                    url = response_headers.get('location')
                    if url is None:
                        raise HTTPError(
                            'Redirect (%s) returned without a location' % code)

                    # Redirects are always GETs
                    c.setopt(pycurl.POST, 0)

                    # There is no way to reset POSTFIELDS to empty and
                    # reuse the connection, but we only use it once.
                else:
                    resp = HTTPResponse()
                    resp.headers = response_headers
                    resp.status = code
                    resp.final_url = url
                    resp.body = data.getvalue()
                    return resp

                off = stop - int(time.time())

            raise HTTPError("Timed out fetching: %r" % (url,))
        finally:
            c.close()

########NEW FILE########
__FILENAME__ = urinorm
import re

# from appendix B of rfc 3986 (http://www.ietf.org/rfc/rfc3986.txt)
uri_pattern = r'^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?'
uri_re = re.compile(uri_pattern)


authority_pattern = r'^([^@]*@)?([^:]*)(:.*)?'
authority_re = re.compile(authority_pattern)


pct_encoded_pattern = r'%([0-9A-Fa-f]{2})'
pct_encoded_re = re.compile(pct_encoded_pattern)

try:
    unichr(0x10000)
except ValueError:
    # narrow python build
    UCSCHAR = [
        (0xA0, 0xD7FF),
        (0xF900, 0xFDCF),
        (0xFDF0, 0xFFEF),
        ]

    IPRIVATE = [
        (0xE000, 0xF8FF),
        ]
else:
    UCSCHAR = [
        (0xA0, 0xD7FF),
        (0xF900, 0xFDCF),
        (0xFDF0, 0xFFEF),
        (0x10000, 0x1FFFD),
        (0x20000, 0x2FFFD),
        (0x30000, 0x3FFFD),
        (0x40000, 0x4FFFD),
        (0x50000, 0x5FFFD),
        (0x60000, 0x6FFFD),
        (0x70000, 0x7FFFD),
        (0x80000, 0x8FFFD),
        (0x90000, 0x9FFFD),
        (0xA0000, 0xAFFFD),
        (0xB0000, 0xBFFFD),
        (0xC0000, 0xCFFFD),
        (0xD0000, 0xDFFFD),
        (0xE1000, 0xEFFFD),
        ]

    IPRIVATE = [
        (0xE000, 0xF8FF),
        (0xF0000, 0xFFFFD),
        (0x100000, 0x10FFFD),
        ]


_unreserved = [False] * 256
for _ in range(ord('A'), ord('Z') + 1): _unreserved[_] = True
for _ in range(ord('0'), ord('9') + 1): _unreserved[_] = True
for _ in range(ord('a'), ord('z') + 1): _unreserved[_] = True
_unreserved[ord('-')] = True
_unreserved[ord('.')] = True
_unreserved[ord('_')] = True
_unreserved[ord('~')] = True


_escapeme_re = re.compile('[%s]' % (''.join(
    map(lambda (m, n): u'%s-%s' % (unichr(m), unichr(n)),
        UCSCHAR + IPRIVATE)),))


def _pct_escape_unicode(char_match):
    c = char_match.group()
    return ''.join(['%%%X' % (ord(octet),) for octet in c.encode('utf-8')])


def _pct_encoded_replace_unreserved(mo):
    try:
        i = int(mo.group(1), 16)
        if _unreserved[i]:
            return chr(i)
        else:
            return mo.group().upper()

    except ValueError:
        return mo.group()


def _pct_encoded_replace(mo):
    try:
        return chr(int(mo.group(1), 16))
    except ValueError:
        return mo.group()


def remove_dot_segments(path):
    result_segments = []
    
    while path:
        if path.startswith('../'):
            path = path[3:]
        elif path.startswith('./'):
            path = path[2:]
        elif path.startswith('/./'):
            path = path[2:]
        elif path == '/.':
            path = '/'
        elif path.startswith('/../'):
            path = path[3:]
            if result_segments:
                result_segments.pop()
        elif path == '/..':
            path = '/'
            if result_segments:
                result_segments.pop()
        elif path == '..' or path == '.':
            path = ''
        else:
            i = 0
            if path[0] == '/':
                i = 1
            i = path.find('/', i)
            if i == -1:
                i = len(path)
            result_segments.append(path[:i])
            path = path[i:]
            
    return ''.join(result_segments)


def urinorm(uri):
    if isinstance(uri, unicode):
        uri = _escapeme_re.sub(_pct_escape_unicode, uri).encode('ascii')

    uri_mo = uri_re.match(uri)

    scheme = uri_mo.group(2)
    if scheme is None:
        raise ValueError('No scheme specified')

    scheme = scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError('Not an absolute HTTP or HTTPS URI: %r' % (uri,))

    authority = uri_mo.group(4)
    if authority is None:
        raise ValueError('Not an absolute URI: %r' % (uri,))

    authority_mo = authority_re.match(authority)
    if authority_mo is None:
        raise ValueError('URI does not have a valid authority: %r' % (uri,))

    userinfo, host, port = authority_mo.groups()

    if userinfo is None:
        userinfo = ''

    if '%' in host:
        host = host.lower()
        host = pct_encoded_re.sub(_pct_encoded_replace, host)
        host = unicode(host, 'utf-8').encode('idna')
    else:
        host = host.lower()

    if port:
        if (port == ':' or
            (scheme == 'http' and port == ':80') or
            (scheme == 'https' and port == ':443')):
            port = ''
    else:
        port = ''

    authority = userinfo + host + port

    path = uri_mo.group(5)
    path = pct_encoded_re.sub(_pct_encoded_replace_unreserved, path)
    path = remove_dot_segments(path)
    if not path:
        path = '/'

    query = uri_mo.group(6)
    if query is None:
        query = ''

    fragment = uri_mo.group(8)
    if fragment is None:
        fragment = ''

    return scheme + '://' + authority + path + query + fragment

########NEW FILE########
__FILENAME__ = accept
"""Functions for generating and parsing HTTP Accept: headers for
supporting server-directed content negotiation.
"""

def generateAcceptHeader(*elements):
    """Generate an accept header value

    [str or (str, float)] -> str
    """
    parts = []
    for element in elements:
        if type(element) is str:
            qs = "1.0"
            mtype = element
        else:
            mtype, q = element
            q = float(q)
            if q > 1 or q <= 0:
                raise ValueError('Invalid preference factor: %r' % q)

            qs = '%0.1f' % (q,)

        parts.append((qs, mtype))

    parts.sort()
    chunks = []
    for q, mtype in parts:
        if q == '1.0':
            chunks.append(mtype)
        else:
            chunks.append('%s; q=%s' % (mtype, q))

    return ', '.join(chunks)

def parseAcceptHeader(value):
    """Parse an accept header, ignoring any accept-extensions

    returns a list of tuples containing main MIME type, MIME subtype,
    and quality markdown.

    str -> [(str, str, float)]
    """
    chunks = [chunk.strip() for chunk in value.split(',')]
    accept = []
    for chunk in chunks:
        parts = [s.strip() for s in chunk.split(';')]

        mtype = parts.pop(0)
        if '/' not in mtype:
            # This is not a MIME type, so ignore the bad data
            continue

        main, sub = mtype.split('/', 1)

        for ext in parts:
            if '=' in ext:
                k, v = ext.split('=', 1)
                if k == 'q':
                    try:
                        q = float(v)
                        break
                    except ValueError:
                        # Ignore poorly formed q-values
                        pass
        else:
            q = 1.0

        accept.append((q, main, sub))

    accept.sort()
    accept.reverse()
    return [(main, sub, q) for (q, main, sub) in accept]

def matchTypes(accept_types, have_types):
    """Given the result of parsing an Accept: header, and the
    available MIME types, return the acceptable types with their
    quality markdowns.

    For example:

    >>> acceptable = parseAcceptHeader('text/html, text/plain; q=0.5')
    >>> matchTypes(acceptable, ['text/plain', 'text/html', 'image/jpeg'])
    [('text/html', 1.0), ('text/plain', 0.5)]


    Type signature: ([(str, str, float)], [str]) -> [(str, float)]
    """
    if not accept_types:
        # Accept all of them
        default = 1
    else:
        default = 0

    match_main = {}
    match_sub = {}
    for (main, sub, q) in accept_types:
        if main == '*':
            default = max(default, q)
            continue
        elif sub == '*':
            match_main[main] = max(match_main.get(main, 0), q)
        else:
            match_sub[(main, sub)] = max(match_sub.get((main, sub), 0), q)

    accepted_list = []
    order_maintainer = 0
    for mtype in have_types:
        main, sub = mtype.split('/')
        if (main, sub) in match_sub:
            q = match_sub[(main, sub)]
        else:
            q = match_main.get(main, default)

        if q:
            accepted_list.append((1 - q, order_maintainer, q, mtype))
            order_maintainer += 1

    accepted_list.sort()
    return [(mtype, q) for (_, _, q, mtype) in accepted_list]

def getAcceptable(accept_header, have_types):
    """Parse the accept header and return a list of available types in
    preferred order. If a type is unacceptable, it will not be in the
    resulting list.

    This is a convenience wrapper around matchTypes and
    parseAcceptHeader.

    (str, [str]) -> [str]
    """
    accepted = parseAcceptHeader(accept_header)
    preferred = matchTypes(accepted, have_types)
    return [mtype for (mtype, _) in preferred]

########NEW FILE########
__FILENAME__ = constants
__all__ = ['YADIS_HEADER_NAME', 'YADIS_CONTENT_TYPE', 'YADIS_ACCEPT_HEADER']
from yadis.accept import generateAcceptHeader

YADIS_HEADER_NAME = 'X-XRDS-Location'
YADIS_CONTENT_TYPE = 'application/xrds+xml'

# A value suitable for using as an accept header when performing YADIS
# discovery, unless the application has special requirements
YADIS_ACCEPT_HEADER = generateAcceptHeader(
    ('text/html', 0.3),
    ('application/xhtml+xml', 0.5),
    (YADIS_CONTENT_TYPE, 1.0),
    )

########NEW FILE########
__FILENAME__ = discover
# -*- test-case-name: yadis.test.test_discover -*-
__all__ = ['discover', 'DiscoveryResult', 'DiscoveryFailure']

from cStringIO import StringIO

from urljr import fetchers

from yadis.constants import \
     YADIS_HEADER_NAME, YADIS_CONTENT_TYPE, YADIS_ACCEPT_HEADER
from yadis.parsehtml import MetaNotFound, findHTMLMeta

class DiscoveryFailure(Exception):
    """Raised when a YADIS protocol error occurs in the discovery process"""
    identity_url = None

    def __init__(self, message, http_response):
        Exception.__init__(self, message)
        self.http_response = http_response

class DiscoveryResult(object):
    """Contains the result of performing Yadis discovery on a URI"""

    # The URI that was passed to the fetcher
    request_uri = None

    # The result of following redirects from the request_uri
    normalized_uri = None

    # The URI from which the response text was returned (set to
    # None if there was no XRDS document found)
    xrds_uri = None

    # The content-type returned with the response_text
    content_type = None

    # The document returned from the xrds_uri
    response_text = None

    def __init__(self, request_uri):
        """Initialize the state of the object

        sets all attributes to None except the request_uri
        """
        self.request_uri = request_uri

    def usedYadisLocation(self):
        """Was the Yadis protocol's indirection used?"""
        return self.normalized_uri == self.xrds_uri

    def isXRDS(self):
        """Is the response text supposed to be an XRDS document?"""
        return (self.usedYadisLocation() or
                self.content_type == YADIS_CONTENT_TYPE)

def discover(uri):
    """Discover services for a given URI.

    @param uri: The identity URI as a well-formed http or https
        URI. The well-formedness and the protocol are not checked, but
        the results of this function are undefined if those properties
        do not hold.

    @return: DiscoveryResult object

    @raises Exception: Any exception that can be raised by fetching a URL with
        the given fetcher.
    """
    result = DiscoveryResult(uri)
    resp = fetchers.fetch(uri, headers={'Accept': YADIS_ACCEPT_HEADER})
    if resp.status != 200:
        raise DiscoveryFailure(
            'HTTP Response status from identity URL host is not 200. '
            'Got status %r' % (resp.status,), resp)

    # Note the URL after following redirects
    result.normalized_uri = resp.final_url

    # Attempt to find out where to go to discover the document
    # or if we already have it
    result.content_type = resp.headers.get('content-type')

    # According to the spec, the content-type header must be an exact
    # match, or else we have to look for an indirection.
    if (result.content_type and
        result.content_type.split(';', 1)[0].lower() == YADIS_CONTENT_TYPE):
        result.xrds_uri = result.normalized_uri
    else:
        # Try the header
        yadis_loc = resp.headers.get(YADIS_HEADER_NAME.lower())

        if not yadis_loc:
            # Parse as HTML if the header is missing.
            #
            # XXX: do we want to do something with content-type, like
            # have a whitelist or a blacklist (for detecting that it's
            # HTML)?
            try:
                yadis_loc = findHTMLMeta(StringIO(resp.body))
            except MetaNotFound:
                pass

        # At this point, we have not found a YADIS Location URL. We
        # will return the content that we scanned so that the caller
        # can try to treat it as an XRDS if it wishes.
        if yadis_loc:
            result.xrds_uri = yadis_loc
            resp = fetchers.fetch(yadis_loc)
            if resp.status != 200:
                exc = DiscoveryFailure(
                    'HTTP Response status from Yadis host is not 200. '
                    'Got status %r' % (resp.status,), resp)
                exc.identity_url = result.normalized_uri
                raise exc
            result.content_type = resp.headers.get('content-type')

    result.response_text = resp.body
    return result

########NEW FILE########
__FILENAME__ = etxrd
# -*- test-case-name: yadis.test.test_etxrd -*-
"""
ElementTree interface to an XRD document.
"""

__all__ = [
    'nsTag',
    'mkXRDTag',
    'isXRDS',
    'parseXRDS',
    'getCanonicalID',
    'getYadisXRD',
    'getPriorityStrict',
    'getPriority',
    'prioSort',
    'iterServices',
    'expandService',
    'expandServices',
    ]

import random

from xml.etree.ElementTree import ElementTree
from xml.parsers.expat import ExpatError as XMLError
from xml.etree.ElementTree import XMLTreeBuilder

from yadis import xri

class XRDSError(Exception):
    """An error with the XRDS document."""

    # The exception that triggered this exception
    reason = None



class XRDSFraud(XRDSError):
    """Raised when there's an assertion in the XRDS that it does not have
    the authority to make.
    """



def parseXRDS(text):
    """Parse the given text as an XRDS document.

    @return: ElementTree containing an XRDS document

    @raises XRDSError: When there is a parse error or the document does
        not contain an XRDS.
    """
    try:
        parser = XMLTreeBuilder()
        parser.feed(text)
        element = parser.close()
    except XMLError, why:
        exc = XRDSError('Error parsing document as XML')
        exc.reason = why
        raise exc
    else:
        tree = ElementTree(element)
        if not isXRDS(tree):
            raise XRDSError('Not an XRDS document')

        return tree

XRD_NS_2_0 = 'xri://$xrd*($v*2.0)'
XRDS_NS = 'xri://$xrds'

def nsTag(ns, t):
    return '{%s}%s' % (ns, t)

def mkXRDTag(t):
    """basestring -> basestring

    Create a tag name in the XRD 2.0 XML namespace suitable for using
    with ElementTree
    """
    return nsTag(XRD_NS_2_0, t)

def mkXRDSTag(t):
    """basestring -> basestring

    Create a tag name in the XRDS XML namespace suitable for using
    with ElementTree
    """
    return nsTag(XRDS_NS, t)

# Tags that are used in Yadis documents
root_tag = mkXRDSTag('XRDS')
service_tag = mkXRDTag('Service')
xrd_tag = mkXRDTag('XRD')
type_tag = mkXRDTag('Type')
uri_tag = mkXRDTag('URI')

# Other XRD tags
canonicalID_tag = mkXRDTag('CanonicalID')

def isXRDS(xrd_tree):
    """Is this document an XRDS document?"""
    root = xrd_tree.getroot()
    return root.tag == root_tag

def getYadisXRD(xrd_tree):
    """Return the XRD element that should contain the Yadis services"""
    xrd = None

    # for the side-effect of assigning the last one in the list to the
    # xrd variable
    for xrd in xrd_tree.findall(xrd_tag):
        pass

    # There were no elements found, or else xrd would be set to the
    # last one
    if xrd is None:
        raise XRDSError('No XRD present in tree')

    return xrd


def getCanonicalID(iname, xrd_tree):
    """Return the CanonicalID from this XRDS document.

    @param iname: the XRI being resolved.
    @type iname: unicode

    @param xrd_tree: The XRDS output from the resolver.
    @type xrd_tree: ElementTree

    @returns: The XRI CanonicalID or None.
    @returntype: unicode or None
    """
    xrd_list = xrd_tree.findall(xrd_tag)
    xrd_list.reverse()

    try:
        canonicalID = xri.XRI(xrd_list[0].findall(canonicalID_tag)[-1].text)
    except IndexError:
        return None

    childID = canonicalID

    for xrd in xrd_list[1:]:
        # XXX: can't use rsplit until we require python >= 2.4.
        parent_sought = childID[:childID.rindex('!')]
        parent_list = [xri.XRI(c.text) for c in xrd.findall(canonicalID_tag)]
        if parent_sought not in parent_list:
            raise XRDSFraud("%r can not come from any of %s" % (parent_sought,
                                                                parent_list))

        childID = parent_sought

    root = xri.rootAuthority(iname)
    if not xri.providerIsAuthoritative(root, childID):
        raise XRDSFraud("%r can not come from root %r" % (childID, root))

    return canonicalID



class _Max(object):
    """Value that compares greater than any other value.

    Should only be used as a singleton. Implemented for use as a
    priority value for when a priority is not specified."""
    def __cmp__(self, other):
        if other is self:
            return 0

        return 1

Max = _Max()

def getPriorityStrict(element):
    """Get the priority of this element.

    Raises ValueError if the value of the priority is invalid. If no
    priority is specified, it returns a value that compares greater
    than any other value.
    """
    prio_str = element.get('priority')
    if prio_str is not None:
        prio_val = int(prio_str)
        if prio_val >= 0:
            return prio_val
        else:
            raise ValueError('Priority values must be non-negative integers')

    # Any errors in parsing the priority fall through to here
    return Max

def getPriority(element):
    """Get the priority of this element

    Returns Max if no priority is specified or the priority value is invalid.
    """
    try:
        return getPriorityStrict(element)
    except ValueError:
        return Max

def prioSort(elements):
    """Sort a list of elements that have priority attributes"""
    # Randomize the services before sorting so that equal priority
    # elements are load-balanced.
    random.shuffle(elements)

    prio_elems = [(getPriority(e), e) for e in elements]
    prio_elems.sort()
    sorted_elems = [s for (_, s) in prio_elems]
    return sorted_elems

def iterServices(xrd_tree):
    """Return an iterable over the Service elements in the Yadis XRD

    sorted by priority"""
    xrd = getYadisXRD(xrd_tree)
    return prioSort(xrd.findall(service_tag))

def sortedURIs(service_element):
    """Given a Service element, return a list of the contents of all
    URI tags in priority order."""
    return [uri_element.text for uri_element
            in prioSort(service_element.findall(uri_tag))]

def getTypeURIs(service_element):
    """Given a Service element, return a list of the contents of all
    Type tags"""
    return [type_element.text for type_element
            in service_element.findall(type_tag)]

def expandService(service_element):
    """Take a service element and expand it into an iterator of:
    ([type_uri], uri, service_element)
    """
    uris = sortedURIs(service_element)
    if not uris:
        uris = [None]

    expanded = []
    for uri in uris:
        type_uris = getTypeURIs(service_element)
        expanded.append((type_uris, uri, service_element))

    return expanded

def expandServices(service_elements):
    """Take a sorted iterator of service elements and expand it into a
    sorted iterator of:
    ([type_uri], uri, service_element)

    There may be more than one item in the resulting list for each
    service element if there is more than one URI or type for a
    service, but each triple will be unique.

    If there is no URI or Type for a Service element, it will not
    appear in the result.
    """
    expanded = []
    for service_element in service_elements:
        expanded.extend(expandService(service_element))

    return expanded

########NEW FILE########
__FILENAME__ = filters
"""This module contains functions and classes used for extracting
endpoint information out of a Yadis XRD file using the ElementTree XML
parser.
"""

__all__ = [
    'BasicServiceEndpoint',
    'mkFilter',
    'IFilter',
    'TransformFilterMaker',
    'CompoundFilter',
    ]

from yadis.etxrd import expandService

class BasicServiceEndpoint(object):
    """Generic endpoint object that contains parsed service
    information, as well as a reference to the service element from
    which it was generated. If there is more than one xrd:Type or
    xrd:URI in the xrd:Service, this object represents just one of
    those pairs.

    This object can be used as a filter, because it implements
    fromBasicServiceEndpoint.

    The simplest kind of filter you can write implements
    fromBasicServiceEndpoint, which takes one of these objects.
    """
    def __init__(self, yadis_url, type_uris, uri, service_element):
        self.type_uris = type_uris
        self.yadis_url = yadis_url
        self.uri = uri
        self.service_element = service_element

    def matchTypes(self, type_uris):
        """Query this endpoint to see if it has any of the given type
        URIs. This is useful for implementing other endpoint classes
        that e.g. need to check for the presence of multiple versions
        of a single protocol.

        @param type_uris: The URIs that you wish to check
        @type type_uris: iterable of str

        @return: all types that are in both in type_uris and
            self.type_uris
        """
        return [uri for uri in type_uris if uri in self.type_uris]

    def fromBasicServiceEndpoint(endpoint):
        """Trivial transform from a basic endpoint to itself. This
        method exists to allow BasicServiceEndpoint to be used as a
        filter.

        If you are subclassing this object, re-implement this function.

        @param endpoint: An instance of BasicServiceEndpoint
        @return: The object that was passed in, with no processing.
        """
        return endpoint

    fromBasicServiceEndpoint = staticmethod(fromBasicServiceEndpoint)

class IFilter(object):
    """Interface for Yadis filter objects. Other filter-like things
    are convertable to this class."""

    def getServiceEndpoints(self, yadis_url, service_element):
        """Returns an iterator of endpoint objects"""
        raise NotImplementedError

class TransformFilterMaker(object):
    """Take a list of basic filters and makes a filter that transforms
    the basic filter into a top-level filter. This is mostly useful
    for the implementation of mkFilter, which should only be needed
    for special cases or internal use by this library.

    This object is useful for creating simple filters for services
    that use one URI and are specified by one Type (we expect most
    Types will fit this paradigm).

    Creates a BasicServiceEndpoint object and apply the filter
    functions to it until one of them returns a value.
    """

    def __init__(self, filter_functions):
        """Initialize the filter maker's state

        @param filter_functions: The endpoint transformer functions to
            apply to the basic endpoint. These are called in turn
            until one of them does not return None, and the result of
            that transformer is returned.
        """
        self.filter_functions = filter_functions

    def getServiceEndpoints(self, yadis_url, service_element):
        """Returns an iterator of endpoint objects produced by the
        filter functions."""
        endpoints = []

        # Do an expansion of the service element by xrd:Type and xrd:URI
        for type_uris, uri, _ in expandService(service_element):

            # Create a basic endpoint object to represent this
            # yadis_url, Service, Type, URI combination
            endpoint = BasicServiceEndpoint(
                yadis_url, type_uris, uri, service_element)

            e = self.applyFilters(endpoint)
            if e is not None:
                endpoints.append(e)

        return endpoints

    def applyFilters(self, endpoint):
        """Apply filter functions to an endpoint until one of them
        returns non-None."""
        for filter_function in self.filter_functions:
            e = filter_function(endpoint)
            if e is not None:
                # Once one of the filters has returned an
                # endpoint, do not apply any more.
                return e

        return None

class CompoundFilter(object):
    """Create a new filter that applies a set of filters to an endpoint
    and collects their results.
    """
    def __init__(self, subfilters):
        self.subfilters = subfilters

    def getServiceEndpoints(self, yadis_url, service_element):
        """Generate all endpoint objects for all of the subfilters of
        this filter and return their concatenation."""
        endpoints = []
        for subfilter in self.subfilters:
            endpoints.extend(
                subfilter.getServiceEndpoints(yadis_url, service_element))
        return endpoints

# Exception raised when something is not able to be turned into a filter
filter_type_error = TypeError(
    'Expected a filter, an endpoint, a callable or a list of any of these.')

def mkFilter(parts):
    """Convert a filter-convertable thing into a filter

    @param parts: a filter, an endpoint, a callable, or a list of any of these.
    """
    # Convert the parts into a list, and pass to mkCompoundFilter
    if parts is None:
        parts = [BasicServiceEndpoint]

    try:
        parts = list(parts)
    except TypeError:
        return mkCompoundFilter([parts])
    else:
        return mkCompoundFilter(parts)

def mkCompoundFilter(parts):
    """Create a filter out of a list of filter-like things

    Used by mkFilter

    @param parts: list of filter, endpoint, callable or list of any of these
    """
    # Separate into a list of callables and a list of filter objects
    transformers = []
    filters = []
    for subfilter in parts:
        try:
            subfilter = list(subfilter)
        except TypeError:
            # If it's not an iterable
            if hasattr(subfilter, 'getServiceEndpoints'):
                # It's a full filter
                filters.append(subfilter)
            elif hasattr(subfilter, 'fromBasicServiceEndpoint'):
                # It's an endpoint object, so put its endpoint
                # conversion attribute into the list of endpoint
                # transformers
                transformers.append(subfilter.fromBasicServiceEndpoint)
            elif callable(subfilter):
                # It's a simple callable, so add it to the list of
                # endpoint transformers
                transformers.append(subfilter)
            else:
                raise filter_type_error
        else:
            filters.append(mkCompoundFilter(subfilter))

    if transformers:
        filters.append(TransformFilterMaker(transformers))

    if len(filters) == 1:
        return filters[0]
    else:
        return CompoundFilter(filters)

########NEW FILE########
__FILENAME__ = manager
class YadisServiceManager(object):
    """Holds the state of a list of selected Yadis services, managing
    storing it in a session and iterating over the services in order."""

    def __init__(self, starting_url, yadis_url, services, session_key):
        # The URL that was used to initiate the Yadis protocol
        self.starting_url = starting_url

        # The URL after following redirects (the identifier)
        self.yadis_url = yadis_url

        # List of service elements
        self.services = list(services)

        self.session_key = session_key

        # Reference to the current service object
        self._current = None

    def __len__(self):
        """How many untried services remain?"""
        return len(self.services)

    def __iter__(self):
        return self

    def next(self):
        """Return the next service

        self.current() will continue to return that service until the
        next call to this method."""
        try:
            self._current = self.services.pop(0)
        except IndexError:
            raise StopIteration
        else:
            return self._current

    def current(self):
        """Return the current service.

        Returns None if there are no services left.
        """
        return self._current

    def forURL(self, url):
        return url in [self.starting_url, self.yadis_url]

    def started(self):
        """Has the first service been returned?"""
        return self._current is not None

    def store(self, session):
        """Store this object in the session, by its session key."""
        session[self.session_key] = self

class Discovery(object):
    """State management for discovery.

    High-level usage pattern is to call .getNextService(discover) in
    order to find the next available service for this user for this
    session. Once a request completes, call .finish() to clean up the
    session state.

    @ivar session: a dict-like object that stores state unique to the
        requesting user-agent. This object must be able to store
        serializable objects.

    @ivar url: the URL that is used to make the discovery request

    @ivar session_key_suffix: The suffix that will be used to identify
        this object in the session object.
    """

    DEFAULT_SUFFIX = 'auth'
    PREFIX = '_yadis_services_'

    def __init__(self, session, url, session_key_suffix=None):
        """Initialize a discovery object"""
        self.session = session
        self.url = url
        if session_key_suffix is None:
            session_key_suffix = self.DEFAULT_SUFFIX

        self.session_key_suffix = session_key_suffix

    def getNextService(self, discover):
        """Return the next authentication service for the pair of
        user_input and session.  This function handles fallback.


        @param discover: a callable that takes a URL and returns a
            list of services

        @type discover: str -> [service]


        @return: the next available service
        """
        manager = self.getManager()
        if manager is not None and not manager:
            self.destroyManager()

        if not manager:
            yadis_url, services = discover(self.url)
            manager = self.createManager(services, yadis_url)

        if manager:
            service = manager.next()
            manager.store(self.session)
        else:
            service = None

        return service

    def cleanup(self):
        """Clean up Yadis-related services in the session and return
        the most-recently-attempted service from the manager, if one
        exists.

        @return: current service endpoint object or None if there is
            no current service
        """
        manager = self.getManager()
        if manager is not None:
            service = manager.current()
            self.destroyManager()
        else:
            service = None

        return service

    ### Lower-level methods

    def getSessionKey(self):
        """Get the session key for this starting URL and suffix

        @return: The session key
        @rtype: str
        """
        return self.PREFIX + self.session_key_suffix

    def getManager(self):
        """Extract the YadisServiceManager for this object's URL and
        suffix from the session.

        @return: The current YadisServiceManager, if it's for this
            URL, or else None
        """
        manager = self.session.get(self.getSessionKey())
        if (manager is not None and manager.forURL(self.url)):
            return manager
        else:
            return None

    def createManager(self, services, yadis_url=None):
        """Create a new YadisService Manager for this starting URL and
        suffix, and store it in the session.

        @raises KeyError: When I already have a manager.

        @return: A new YadisServiceManager or None
        """
        key = self.getSessionKey()
        if self.getManager():
            raise KeyError('There is already a %r manager for %r' %
                           (key, self.url))

        if not services:
            return None

        manager = YadisServiceManager(self.url, yadis_url, services, key)
        manager.store(self.session)
        return manager

    def destroyManager(self):
        """Delete any YadisServiceManager with this starting URL and
        suffix from the session.

        If there is no service manager or the service manager is for a
        different URL, it silently does nothing.
        """
        if self.getManager() is not None:
            key = self.getSessionKey()
            del self.session[key]

########NEW FILE########
__FILENAME__ = parsehtml
__all__ = ['findHTMLMeta', 'MetaNotFound']

from HTMLParser import HTMLParser, HTMLParseError
import htmlentitydefs
import re

from yadis.constants import YADIS_HEADER_NAME

# Size of the chunks to search at a time (also the amount that gets
# read at a time)
CHUNK_SIZE = 1024 * 16 # 16 KB

class ParseDone(Exception):
    """Exception to hold the URI that was located when the parse is
    finished. If the parse finishes without finding the URI, set it to
    None."""

class MetaNotFound(Exception):
    """Exception to hold the content of the page if we did not find
    the appropriate <meta> tag"""

re_flags = re.IGNORECASE | re.UNICODE | re.VERBOSE
ent_pat = r'''
&

(?: \#x (?P<hex> [a-f0-9]+ )
|   \# (?P<dec> \d+ )
|   (?P<word> \w+ )
)

;'''

ent_re = re.compile(ent_pat, re_flags)

def substituteMO(mo):
    if mo.lastgroup == 'hex':
        codepoint = int(mo.group('hex'), 16)
    elif mo.lastgroup == 'dec':
        codepoint = int(mo.group('dec'))
    else:
        assert mo.lastgroup == 'word'
        codepoint = htmlentitydefs.name2codepoint.get(mo.group('word'))

    if codepoint is None:
        return mo.group()
    else:
        return unichr(codepoint)

def substituteEntities(s):
    return ent_re.sub(substituteMO, s)

class YadisHTMLParser(HTMLParser):
    """Parser that finds a meta http-equiv tag in the head of a html
    document.

    When feeding in data, if the tag is matched or it will never be
    found, the parser will raise ParseDone with the uri as the first
    attribute.

    Parsing state diagram
    =====================

    Any unlisted input does not affect the state::

                1, 2, 5                       8
               +--------------------------+  +-+
               |                          |  | |
            4  |    3       1, 2, 5, 7    v  | v
        TOP -> HTML -> HEAD ----------> TERMINATED
        | |            ^  |               ^  ^
        | | 3          |  |               |  |
        | +------------+  +-> FOUND ------+  |
        |                  6         8       |
        | 1, 2                               |
        +------------------------------------+

      1. any of </body>, </html>, </head> -> TERMINATE
      2. <body> -> TERMINATE
      3. <head> -> HEAD
      4. <html> -> HTML
      5. <html> -> TERMINATE
      6. <meta http-equiv='X-XRDS-Location'> -> FOUND
      7. <head> -> TERMINATE
      8. Any input -> TERMINATE
    """
    TOP = 0
    HTML = 1
    HEAD = 2
    FOUND = 3
    TERMINATED = 4

    def __init__(self):
        HTMLParser.__init__(self)
        self.phase = self.TOP

    def _terminate(self):
        self.phase = self.TERMINATED
        raise ParseDone(None)

    def handle_endtag(self, tag):
        # If we ever see an end of head, body, or html, bail out right away.
        # [1]
        if tag in ['head', 'body', 'html']:
            self._terminate()

    def handle_starttag(self, tag, attrs):
        # if we ever see a start body tag, bail out right away, since
        # we want to prevent the meta tag from appearing in the body
        # [2]
        if tag=='body':
            self._terminate()

        if self.phase == self.TOP:
            # At the top level, allow a html tag or a head tag to move
            # to the head or html phase
            if tag == 'head':
                # [3]
                self.phase = self.HEAD
            elif tag == 'html':
                # [4]
                self.phase = self.HTML

        elif self.phase == self.HTML:
            # if we are in the html tag, allow a head tag to move to
            # the HEAD phase. If we get another html tag, then bail
            # out
            if tag == 'head':
                # [3]
                self.phase = self.HEAD
            elif tag == 'html':
                # [5]
                self._terminate()

        elif self.phase == self.HEAD:
            # If we are in the head phase, look for the appropriate
            # meta tag. If we get a head or body tag, bail out.
            if tag == 'meta':
                attrs_d = dict(attrs)
                http_equiv = attrs_d.get('http-equiv', '').lower()
                if http_equiv == YADIS_HEADER_NAME.lower():
                    raw_attr = attrs_d.get('content')
                    yadis_loc = substituteEntities(raw_attr)
                    # [6]
                    self.phase = self.FOUND
                    raise ParseDone(yadis_loc)

            elif tag in ['head', 'html']:
                # [5], [7]
                self._terminate()

    def feed(self, chars):
        # [8]
        if self.phase in [self.TERMINATED, self.FOUND]:
            self._terminate()

        return HTMLParser.feed(self, chars)

def findHTMLMeta(stream):
    """Look for a meta http-equiv tag with the YADIS header name.

    @param stream: Source of the html text
    @type stream: Object that implements a read() method that works
        like file.read

    @return: The URI from which to fetch the XRDS document
    @rtype: str

    @raises MetaNotFound: raised with the content that was
        searched as the first parameter.
    """
    parser = YadisHTMLParser()
    chunks = []

    while 1:
        chunk = stream.read(CHUNK_SIZE)
        if not chunk:
            # End of file
            break

        chunks.append(chunk)
        try:
            parser.feed(chunk)
        except HTMLParseError, why:
            # HTML parse error, so bail
            chunks.append(stream.read())
            break
        except ParseDone, why:
            uri = why[0]
            if uri is None:
                # Parse finished, but we may need the rest of the file
                chunks.append(stream.read())
                break
            else:
                return uri

    content = ''.join(chunks)
    raise MetaNotFound(content)

########NEW FILE########
__FILENAME__ = services
from yadis.filters import mkFilter
from yadis.discover import discover
from yadis.etxrd import parseXRDS, iterServices

def getServiceEndpoints(input_url, flt=None):
    """Perform the Yadis protocol on the input URL and return an
    iterable of resulting endpoint objects.

    @param flt: A filter object or something that is convertable to
        a filter object (using mkFilter) that will be used to generate
        endpoint objects. This defaults to generating BasicEndpoint
        objects.

    @param input_url: The URL on which to perform the Yadis protocol

    @return: The normalized identity URL and an iterable of endpoint
        objects generated by the filter function.

    @rtype: (str, [endpoint])
    """
    result = discover(input_url)
    endpoints = applyFilter(result.normalized_uri, result.response_text, flt)
    return (result.normalized_uri, endpoints)

def applyFilter(normalized_uri, xrd_data, flt=None):
    """Generate an iterable of endpoint objects given this input data,
    presumably from the result of performing the Yadis protocol.

    @param normalized_uri: The input URL, after following redirects,
        as in the Yadis protocol.


    @param xrd_data: The XML text the XRDS file fetched from the
        normalized URI.
    @type xrd_data: str

    """
    flt = mkFilter(flt)
    et = parseXRDS(xrd_data)

    endpoints = []
    for service_element in iterServices(et):
        endpoints.extend(
            flt.getServiceEndpoints(normalized_uri, service_element))

    return endpoints

########NEW FILE########
__FILENAME__ = xri
# -*- test-case-name: yadis.test.test_xri -*-
"""Utility functions for handling XRIs.

@see: XRI Syntax v2.0 at the U{OASIS XRI Technical Committee<http://www.oasis-open.org/committees/tc_home.php?wg_abbrev=xri>}
"""

import re

XRI_AUTHORITIES = ['!', '=', '@', '+', '$', '(']

try:
    unichr(0x10000)
except ValueError:
    # narrow python build
    UCSCHAR = [
        (0xA0, 0xD7FF),
        (0xF900, 0xFDCF),
        (0xFDF0, 0xFFEF),
        ]

    IPRIVATE = [
        (0xE000, 0xF8FF),
        ]
else:
    UCSCHAR = [
        (0xA0, 0xD7FF),
        (0xF900, 0xFDCF),
        (0xFDF0, 0xFFEF),
        (0x10000, 0x1FFFD),
        (0x20000, 0x2FFFD),
        (0x30000, 0x3FFFD),
        (0x40000, 0x4FFFD),
        (0x50000, 0x5FFFD),
        (0x60000, 0x6FFFD),
        (0x70000, 0x7FFFD),
        (0x80000, 0x8FFFD),
        (0x90000, 0x9FFFD),
        (0xA0000, 0xAFFFD),
        (0xB0000, 0xBFFFD),
        (0xC0000, 0xCFFFD),
        (0xD0000, 0xDFFFD),
        (0xE1000, 0xEFFFD),
        ]

    IPRIVATE = [
        (0xE000, 0xF8FF),
        (0xF0000, 0xFFFFD),
        (0x100000, 0x10FFFD),
        ]


_escapeme_re = re.compile('[%s]' % (''.join(
    map(lambda (m, n): u'%s-%s' % (unichr(m), unichr(n)),
        UCSCHAR + IPRIVATE)),))


def identifierScheme(identifier):
    """Determine if this identifier is an XRI or URI.

    @returns: C{"XRI"} or C{"URI"}
    """
    if identifier.startswith('xri://') or identifier[0] in XRI_AUTHORITIES:
        return "XRI"
    else:
        return "URI"


def toIRINormal(xri):
    """Transform an XRI to IRI-normal form."""
    if not xri.startswith('xri://'):
        xri = 'xri://' + xri
    return escapeForIRI(xri)


_xref_re = re.compile('\((.*?)\)')


def _escape_xref(xref_match):
    """Escape things that need to be escaped if they're in a cross-reference.
    """
    xref = xref_match.group()
    xref = xref.replace('/', '%2F')
    xref = xref.replace('?', '%3F')
    xref = xref.replace('#', '%23')
    return xref


def escapeForIRI(xri):
    """Escape things that need to be escaped when transforming to an IRI."""
    xri = xri.replace('%', '%25')
    xri = _xref_re.sub(_escape_xref, xri)
    return xri


def toURINormal(xri):
    """Transform an XRI to URI normal form."""
    return iriToURI(toIRINormal(xri))


def _percentEscapeUnicode(char_match):
    c = char_match.group()
    return ''.join(['%%%X' % (ord(octet),) for octet in c.encode('utf-8')])


def iriToURI(iri):
    """Transform an IRI to a URI by escaping unicode."""
    # According to RFC 3987, section 3.1, "Mapping of IRIs to URIs"
    return _escapeme_re.sub(_percentEscapeUnicode, iri)


def providerIsAuthoritative(providerID, canonicalID):
    """Is this provider ID authoritative for this XRI?

    @returntype: bool
    """
    # XXX: can't use rsplit until we require python >= 2.4.
    lastbang = canonicalID.rindex('!')
    parent = canonicalID[:lastbang]
    return parent == providerID


def rootAuthority(xri):
    """Return the root authority for an XRI.

    Example::

        rootAuthority("xri://@example") == "xri://@"

    @type xri: unicode
    @returntype: unicode
    """
    if xri.startswith('xri://'):
        xri = xri[6:]
    authority = xri.split('/', 1)[0]
    if authority[0] == '(':
        # Cross-reference.
        # XXX: This is incorrect if someone nests cross-references so there
        #   is another close-paren in there.  Hopefully nobody does that
        #   before we have a real xriparse function.  Hopefully nobody does
        #   that *ever*.
        root = authority[:authority.index(')') + 1]
    elif authority[0] in XRI_AUTHORITIES:
        # Other XRI reference.
        root = authority[0]
    else:
        # IRI reference.  XXX: Can IRI authorities have segments?
        segments = authority.split('!')
        segments = reduce(list.__add__,
            map(lambda s: s.split('*'), segments))
        root = segments[0]

    return XRI(root)


def XRI(xri):
    """An XRI object allowing comparison of XRI.

    Ideally, this would do full normalization and provide comparsion
    operators as per XRI Syntax.  Right now, it just does a bit of
    canonicalization by ensuring the xri scheme is present.

    @param xri: an xri string
    @type xri: unicode
    """
    if not xri.startswith('xri://'):
        xri = 'xri://' + xri
    return xri

########NEW FILE########
__FILENAME__ = xrires
# -*- test-case-name: yadis.test.test_xrires -*-
"""XRI resolution.
"""

from urllib import urlencode
from urljr import fetchers
from yadis import etxrd
from yadis.xri import toURINormal
from yadis.services import iterServices

DEFAULT_PROXY = 'http://proxy.xri.net/'

class ProxyResolver(object):
    """Python interface to a remote XRI proxy resolver.
    """
    def __init__(self, proxy_url=DEFAULT_PROXY):
        self.proxy_url = proxy_url


    def queryURL(self, xri, service_type=None):
        """Build a URL to query the proxy resolver.

        @param xri: An XRI to resolve.
        @type xri: unicode

        @param service_type: The service type to resolve, if you desire
            service endpoint selection.  A service type is a URI.
        @type service_type: str

        @returns: a URL
        @returntype: str
        """
        # Trim off the xri:// prefix.  The proxy resolver didn't accept it
        # when this code was written, but that may (or may not) change for
        # XRI Resolution 2.0 Working Draft 11.
        qxri = toURINormal(xri)[6:]
        hxri = self.proxy_url + qxri
        args = {
            # XXX: If the proxy resolver will ensure that it doesn't return
            # bogus CanonicalIDs (as per Steve's message of 15 Aug 2006
            # 11:13:42), then we could ask for application/xrd+xml instead,
            # which would give us a bit less to process.
            '_xrd_r': 'application/xrds+xml',
            }
        if service_type:
            args['_xrd_t'] = service_type
        else:
            # Don't perform service endpoint selection.
            args['_xrd_r'] += ';sep=false'
        query = _appendArgs(hxri, args)
        return query


    def query(self, xri, service_types):
        """Resolve some services for an XRI.

        Note: I don't implement any service endpoint selection beyond what
        the resolver I'm querying does, so the Services I return may well
        include Services that were not of the types you asked for.

        May raise fetchers.HTTPFetchingError or L{etxrd.XRDError} if
        the fetching or parsing don't go so well.

        @param xri: An XRI to resolve.
        @type xri: unicode

        @param service_types: A list of services types to query for.  Service
            types are URIs.
        @type service_types: list of str

        @returns: tuple of (CanonicalID, Service elements)
        @returntype: (unicode, list of C{ElementTree.Element}s)
        """
        # FIXME: No test coverage!
        services = []
        # Make a seperate request to the proxy resolver for each service
        # type, as, if it is following Refs, it could return a different
        # XRDS for each.
        for service_type in service_types:
            url = self.queryURL(xri, service_type)
            response = fetchers.fetch(url)
            if response.status != 200:
                # XXX: sucks to fail silently.
                # print "response not OK:", response
                continue
            et = etxrd.parseXRDS(response.body)
            canonicalID = etxrd.getCanonicalID(xri, et)
            some_services = list(iterServices(et))
            services.extend(some_services)
        # TODO:
        #  * If we do get hits for multiple service_types, we're almost
        #    certainly going to have duplicated service entries and
        #    broken priority ordering.
        return canonicalID, services


def _appendArgs(url, args):
    """Append some arguments to an HTTP query.
    """
    # to be merged with oidutil.appendArgs when we combine the projects.
    if hasattr(args, 'items'):
        args = args.items()
        args.sort()

    if len(args) == 0:
        return url

    # According to XRI Resolution section "QXRI query parameters":
    #
    # """If the original QXRI had a null query component (only a leading
    #    question mark), or a query component consisting of only question
    #    marks, one additional leading question mark MUST be added when
    #    adding any XRI resolution parameters."""

    if '?' in url.rstrip('?'):
        sep = '&'
    else:
        sep = '?'

    return '%s%s%s' % (url, sep, urlencode(args))

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

class MachineTaggedItem(models.Model):
    "A machine tag on an item."
    namespace = models.CharField(max_length=50, db_index=True)
    predicate = models.CharField(max_length=50, db_index=True)
    value = models.CharField(max_length=255, db_index=True)
    
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()

    content_object = generic.GenericForeignKey()

    class Meta:
        ordering = ('namespace', 'predicate', 'value')

    def __unicode__(self):
        value = self.value
        if ' ' in value or '"' in value:
            value = '"%s"' % value.replace('"', r'\"')
        return '%s:%s=%s' % (self.namespace, self.predicate, value)

import re
_part_re = re.compile('^[a-z][a-z0-9_]*$')
_machinetag_re = re.compile('^([a-z][a-z0-9_]*):([a-z][a-z0-9_]*)=(.*)$')

def is_valid_part(part):
    "Checks string is a valid namespace or predicate"
    return bool(_part_re.match(part))

def parse_machinetag(namespace_or_fulltag, predicate=None, value=None):
    if predicate:
        assert value, 'If you provide a predicate you must also provide a value'
        assert is_valid_part(namespace_or_fulltag), 'namespace must be valid'
        assert is_valid_part(predicate), 'predicate must be valid'
        namespace = namespace_or_fulltag
    else:
        match = _machinetag_re.match(machinetag)
        assert match, 'machinetag must be of format namespace:predicate=value'
        namespace, predicate, value = match.groups()
        if value[0] == '"' or value[-1] == '"':
            assert value[0] == '"' and value[-1] == '"', \
                'If value is quoted, double quotes must occur at start AND end'
            value = value[1:-1]
            value = value.replace(r'\"', '"')
    return namespace, predicate, value

def tag_exists(*args):
    namespace, predicate, value = parse_machinetag(*args)
    return MachineTaggedItem.objects.filter(
        namespace = namespace,
        predicate = predicate,
        value = value
    ).count() > 0

def obj_for_tag(*args):
    namespace, predicate, value = parse_machinetag(*args)
    found = list(MachineTaggedItem.objects.filter(
        namespace = namespace,
        predicate = predicate,
        value = value
    ))
    if len(found) > 0:
        return found[0].content_object
    else:
        return False

def add_machinetag(obj, namespace_or_fulltag, predicate=None, value=None):
    if predicate:
        assert value, 'If you provide a predicate you must also provide a value'
        assert is_valid_part(namespace_or_fulltag), 'namespace must be valid'
        assert is_valid_part(predicate), 'predicate must be valid'
        namespace = namespace_or_fulltag
    else:
        namespace, predicate, value = parse_machinetag(namespace_or_fulltag)
    obj.machinetags.create(
        namespace = namespace,
        predicate = predicate,
        value = value
    )

########NEW FILE########
__FILENAME__ = utils
try:
    from collections import defaultdict
except:
    class defaultdict(dict):
        def __init__(self, default_factory=None, *a, **kw):
            if (default_factory is not None and
                not hasattr(default_factory, '__call__')):
                raise TypeError('first argument must be callable')
            dict.__init__(self, *a, **kw)
            self.default_factory = default_factory
        def __getitem__(self, key):
            try:
                return dict.__getitem__(self, key)
            except KeyError:
                return self.__missing__(key)
        def __missing__(self, key):
            if self.default_factory is None:
                raise KeyError(key)
            self[key] = value = self.default_factory()
            return value
        def __reduce__(self):
            if self.default_factory is None:
                args = tuple()
            else:
                args = self.default_factory,
            return type(self), args, None, None, self.items()
        def copy(self):
            return self.__copy__()
        def __copy__(self):
            return type(self)(self.default_factory, self)
        def __deepcopy__(self, memo):
            import copy
            return type(self)(self.default_factory,
                              copy.deepcopy(self.items()))
        def __repr__(self):
            return 'defaultdict(%s, %s)' % (self.default_factory,
                                            dict.__repr__(self))

def tagdict(queryset):
    "Returns a nested dictionary of machine tags, suitable for template languge"
    d = defaultdict(lambda: defaultdict(lambda: ''))
    for mtag in queryset:
        d[mtag.namespace][mtag.predicate] = mtag.value
    return d

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
