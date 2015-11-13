__FILENAME__ = admin
# -*- coding: UTF-8 -*-
from django.contrib import admin
from models import *

class geoAdmin(admin.ModelAdmin):
    """ Django admin class for geo microformat """
    list_filter = ('latitude', 'longitude')
    save_on_top = True

class hCardAdmin(admin.ModelAdmin):
    """ Django admin class for flat hCard microformat """
    list_display = ('given_name', 'family_name', 'org', 'url')
    list_display_links = ('given_name', 'org')
    list_filter = ('family_name', 'org')
    save_on_top = True
    search_fields = ('given_name', 'family_name', 'org')

class hCalendarAdmin(admin.ModelAdmin):
    """ Django admin class for flat hCalendar microformat """
    list_display = ('dtstart', 'dtend', 'summary', 'location')
    list_display_links = ('dtstart', 'summary')
    list_filter = ('dtstart', 'dtend')
    save_on_top = True
    search_fields = ('summary', 'description', 'location')

class hListingAdmin(admin.ModelAdmin):
    """ Django admin class for hListing microformat """
    list_display = (
            'listing_action', 
            'description', 
            'lister_fn', 
            'item_fn',
            'price',
            )
    list_display_links = ('listing_action', 'description')
    list_filter = ('listing_action',)
    save_on_top = True
    search_fields = ('description', 'lister_fn', 'item_fn')

class hReviewAdmin(admin.ModelAdmin):
    """ Django admin class for hReview microformat """
    list_display = ('fn', 'reviewer', 'rating', 'summary')
    list_display_links = ('fn', 'rating', 'summary')
    list_filter = ('fn', 'rating')
    save_on_top = True
    search_fields = ('fn', 'reviewer', 'description', 'summary')

class hEntryAdmin(admin.ModelAdmin):
    """ Django admin class for hEntry microformat """
    list_display = ('entry_title', 'author', 'updated', 'entry_summary')
    list_display_links = ('entry_title',)
    list_filter = ('author', 'updated')
    save_on_top = True
    search_fields = ('entry_title', 'entry_content', 'entry_summary', 'author')

class hNewsAdmin(admin.ModelAdmin):
    """ Django admin class for hEntry microformat """
    list_display = ('entry_title', 'source_org', 'updated', 'dateline', 'entry_summary')
    list_display_links = ('entry_title',)
    list_filter = ('source_org', 'updated')
    save_on_top = True
    search_fields = ('entry_title', 'entry_content', 'entry_summary', 'author', 'source_org')

admin.site.register(geo, geoAdmin)
admin.site.register(hCard, hCardAdmin)
admin.site.register(hCalendar, hCalendarAdmin)
admin.site.register(hListing, hListingAdmin)
admin.site.register(hReview, hReviewAdmin)
admin.site.register(hEntry, hEntryAdmin)
admin.site.register(hNews, hNewsAdmin)
admin.site.register(adr_type)
admin.site.register(adr)
admin.site.register(tel_type)
admin.site.register(tel)
admin.site.register(email_type)
admin.site.register(email)
admin.site.register(photo)
admin.site.register(logo)
admin.site.register(sound)
admin.site.register(title)
admin.site.register(role)
admin.site.register(org)
admin.site.register(note)
admin.site.register(key)
admin.site.register(mailer)
admin.site.register(xfn_values)
admin.site.register(xfn)
admin.site.register(hFeed)

########NEW FILE########
__FILENAME__ = forms
# -*- coding: UTF-8 -*-
"""
Example Forms for Microformats. 

Copyright (c) 2009 Nicholas H.Tollervey (http://ntoll.org/contact)

All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in
the documentation and/or other materials provided with the
distribution.
* Neither the name of ntoll.org nor the names of its
contributors may be used to endorse or promote products
derived from this software without specific prior written
permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
# Django
from django import forms
from django.forms.util import ErrorList
from django.utils.translation import ugettext as _

# Microformats
from microformats.models import geo, hCard, adr, adr_type, org, email,\
        email_type, tel, tel_type, hCalendar, hReview, hListing, hFeed,\
        hEntry, hNews

class GeoForm(forms.ModelForm):
    """
    A ModelForm for the geo microformat that makes sure the degrees decimal
    fields are within the valid ranges:

    Latitude: ±90°
    Longitude: ±180°
    """
    def clean_latitude(self):
        """
        ±90
        """
        value = self.cleaned_data['latitude']
        if value < -90.0 or value > 90.0:
            raise forms.ValidationError(_(u'Latitude is not within the valid'
                u' range (±90)'))
        return value

    def clean_longitude(self):
        """
        ±180
        """
        value = self.cleaned_data['longitude']
        if value < -180.0 or value > 180.0:
            raise forms.ValidationError(_(u'Longitude is not within the valid'
                u' range (±180)'))
        return value

    class Meta:
        model = geo

class LocationAwareForm(forms.ModelForm):
    """
    Used in concert with models derived from the LocationAwareMicroformat model.
    This form makes sure that the geo information is valid.
    """
    def clean(self):
        """
        Checks if you have one of Long or Lat you must have the other
        """
        super(LocationAwareForm, self).clean()
        cleaned_data = self.cleaned_data
        # Make sure we have a longitude and latitude
        lat = cleaned_data.get("latitude", False)
        long = cleaned_data.get("longitude", False)
        if long and not lat:
            self._errors['longitude'] = ErrorList([_("You must supply both a"\
                    " longitude and latitude")])
            del cleaned_data['longitude']
        if lat and not long: 
            self._errors['latitude'] = ErrorList([_("You must supply both a"\
                    " longitude and latitude")])
            del cleaned_data['latitude']
        return cleaned_data

    def clean_latitude(self):
        """
        ±90
        """
        value = self.cleaned_data.get('latitude', False)
        if value:
            if value < -90.0 or value > 90.0:
                raise forms.ValidationError(_(u'Latitude is not within the valid'
                    u' range (±90)'))
        return value

    def clean_longitude(self):
        """
        ±180
        """
        value = self.cleaned_data.get('longitude', False)
        if value:
            if value < -180.0 or value > 180.0:
                raise forms.ValidationError(_(u'Longitude is not within the valid'
                    u' range (±180)'))
        return value

class hCardForm(LocationAwareForm):
    """
    A simple form to use for gathering basic information for an hCard. Use in
    conjunction with the AdrForm, OrgForm, EmailForm and TelForm to build
    something more complex. 

    This form assumes the hCard will be for a person (rather than an
    organisation) - so the constructor sets the given_name as a required field
    so we always get a valid fn.

    Don't use this form for hCards relating to organisations only (that don't
    require personal name details like this form does).
    
    Inspired by:

    http://microformats.org/code/hcard/creator
    """
    def clean(self):
        """
        Checks you have something useful to use as fn
        """
        super(hCardForm, self).clean()
        cleaned_data = self.cleaned_data

        # Some minimum fields needed to create a fn
        org = cleaned_data.get('org', False)
        given_name = cleaned_data.get('given_name', False)
        family_name = cleaned_data.get('family_name', False)
        nickname = cleaned_data.get('nickname', False)

        # What the following if statement means:
        # if the user hasn't supplied either and organization name or provided
        # at least a nickname or a given name then raise an error
        if not (org or nickname or given_name):
            raise forms.ValidationError("You must supply some sort of namimg"\
                    " information (given name or nickname"\
                    " or an organization name)")
        return cleaned_data
    
    class Meta:
        model = hCard

class hCalForm(LocationAwareForm):
    """
    A simple form for gathering information for an hCalendar event. Inspired by
    the form found here:

    http://microformats.org/code/hcalendar/creator
    """
    class Meta:
        model = hCalendar
        exclude = [
                'attendees',
                'contacts',
                'organizers',
                ]

class hReviewForm(LocationAwareForm):
    """
    A simple form for gathering information for an hReview microformat. Inspired
    by the form found here:

    http://microformats.org/code/hreview/creator
    """
    class Meta:
        model = hReview

class hListingForm(LocationAwareForm):
    """
    A simple form for gathering information for an hListing microforat.
    """
    class Meta:
        model = hListing

class hFeedForm(forms.ModelForm):
    """
    A simple form for gathering information for the hFeed part of the hAtom
    microformat.
    """
    class Meta:
        model = hFeed

class hEntryForm(forms.ModelForm):
    """
    A simple form for gathering information for the hEntry part of the hAtom
    microformat.
    """
    class Meta:
        model = hEntry

class hNewsForm(LocationAwareForm):
    """
    A simple form for gathering information for the hNews part of the hEntry
    microformat.
    """
    class Meta:
        model = hNews

class AdrForm(forms.ModelForm):
    """
    A simple form to use for gathering basic information for an adr microformat. 
    Use in conjunction with the hCardForm, OrgForm, EmailForm and TelForm to 
    build something more complex. 

    Inspired by:

    http://microformats.org/code/hcard/creator
    """
    def __init__(self, *args, **kwargs): 
        super(AdrForm, self).__init__(*args, **kwargs) 
        self.fields['types'].widget = forms.CheckboxSelectMultiple()
        self.fields['types'].label = _('Address Type')
        self.fields['types'].help_text = _('Please select as many that apply')
        self.fields['types'].queryset = adr_type.objects.all()

    class Meta:
        model = adr
        exclude = ['hcard', 'post_office_box']

class OrgForm(forms.ModelForm):
    """
    A simple form to use for gathering basic information for an organisation
    associated with an hCard.  Use in conjunction with the AdrForm, EmailForm 
    and TelForm to build something more complex. 

    Inspired by:

    http://microformats.org/code/hcard/creator
    """
    class Meta:
        model = org
        exclude = ['hcard']

class EmailForm(forms.ModelForm):
    """
    A simple form to use for gathering basic email information for an hCard. 
    Use in conjunction with the hCardForm, AdrForm, OrgForm and TelForm to 
    build something more complex. 

    Inspired by:

    http://microformats.org/code/hcard/creator
    """
    def __init__(self, *args, **kwargs): 
        super(EmailForm, self).__init__(*args, **kwargs) 
        self.fields['types'].widget = forms.CheckboxSelectMultiple()
        self.fields['types'].label = _('Email Type')
        self.fields['types'].help_text = _('Please select as many that apply')
        self.fields['types'].queryset = email_type.objects.all()

    class Meta:
        model = email 
        exclude = ['hcard']

class TelForm(forms.ModelForm):
    """
    A simple form to use for gathering basic telephone information for an hCard. 
    Use in conjunction with the hCardForm, AdrForm, OrgForm and EmailForm to 
    build something more complex. 

    Inspired by:

    http://microformats.org/code/hcard/creator
    """
    def __init__(self, *args, **kwargs): 
        super(TelForm, self).__init__(*args, **kwargs) 
        self.fields['types'].widget = forms.CheckboxSelectMultiple()
        self.fields['types'].label = _('Telephone Type')
        self.fields['types'].help_text = _('Please select as many that apply')
        self.fields['types'].queryset = tel_type.objects.all()

    class Meta:
        model = tel 
        exclude = ['hcard']

########NEW FILE########
__FILENAME__ = models
# -*- coding: UTF-8 -*-
"""
Models for Microformats. 

Copyright (c) 2009 Nicholas H.Tollervey (http://ntoll.org/contact)

All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in
the documentation and/or other materials provided with the
distribution.
* Neither the name of ntoll.org nor the names of its
contributors may be used to endorse or promote products
derived from this software without specific prior written
permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
from django.db import models
from django.utils.translation import ugettext_lazy as _, ugettext as __
from django.contrib.auth.models import User
from datetime import date

########################################
# Constant tuples used in several models
########################################

# Timezone representation taken from the hCalendar creator:
# http://microformats.org/code/hcalendar/creator
TIMEZONE = (
        ('-12:00', _('-12 (IDLW)')),
        ('-11:00', _('-11 (NT)')),
        ('-10:00', _('-10 (HST)')),
        ('-09:00', _('-9 (AKST)')),
        ('-08:00', _('-8 (PST/AKDT)')),
        ('-07:00', _('-7 (MST/PDT)')),
        ('-06:00', _('-6 (CST/MDT)')),
        ('-05:00', _('-5 (EST/CDT)')),
        ('-04:00', _('-4 (AST/EDT)')),
        ('-03:45', _('-3:45')),
        ('-03:30', _('-3:30')),
        ('-03:00', _('-3 (ADT)')),
        ('-02:00', _('-2 (AT)')),
        ('-01:00', _('-1 (WAT)')),
        ('Z', _('+0 (GMT/UTC)')),
        ('+01:00', _('+1 (CET/BST/IST/WEST)')),
        ('+02:00', _('+2 (EET/CEST)')),
        ('+03:00', _('+3 (MSK/EEST)')),
        ('+03:30', _('+3:30 (Iran)')),
        ('+04:00', _('+4 (ZP4/MSD)')),
        ('+04:30', _('+4:30 (Afghanistan)')),
        ('+05:00', _('+5 (ZP5)')),
        ('+05:30', _('+5:30 (India)')),
        ('+06:00', _('+6 (ZP6)')),
        ('+06:30', _('+6:30 (Burma)')),
        ('+07:00', _('+7 (WAST)')),
        ('+08:00', _('+8 (WST)')),
        ('+09:00', _('+9 (JST)')),
        ('+09:30', _('+9:30 (Central Australia)')),
        ('+10:00', _('+10 (AEST)')),
        ('+11:00', _('+11 (AEST(summer))')),
        ('+12:00', _('+12 (NZST/IDLE)')),
        )

# A list of all countries stored as (('ISO 3166'), ('Name')) 
COUNTRY_LIST = (
        ('',_('--- Please Select ---')),
        ('GB', _('United Kingdom')),
        ('US', _('United States')),
        ('CA', _('Canada')),
        ('AU', _('Australia')),
        ('NZ', _('New Zealand')),
        ('IE', _('Ireland')),
        ('FR', _('France')),
        ('DE', _('Germany')),
        ('IT', _('Italy')),
        ('ES', _('Spain')),
        ('AF', _('Afghanistan')),
        ('AL', _('Albania')),
        ('DZ', _('Algeria')),
        ('AS', _('American Samoa')),
        ('AD', _('Andorra')),
        ('AO', _('Angola')),
        ('AI', _('Anguilla')),
        ('AQ', _('Antarctica')),
        ('AG', _('Antigua and Barbuda')),
        ('AR', _('Argentina')),
        ('AM', _('Armenia')),
        ('AW', _('Aruba')),
        ('AT', _('Austria')),
        ('AZ', _('Azerbaidjan')),
        ('BS', _('Bahamas')),
        ('BH', _('Bahrain')),
        ('BD', _('Bangladesh')),
        ('BB', _('Barbados')),
        ('BY', _('Belarus')),
        ('BE', _('Belgium')),
        ('BZ', _('Belize')),
        ('BJ', _('Benin')),
        ('BM', _('Bermuda')),
        ('BT', _('Bhutan')),
        ('BO', _('Bolivia')),
        ('BA', _('Bosnia-Herzegovina')),
        ('BW', _('Botswana')),
        ('BV', _('Bouvet Island')),
        ('BR', _('Brazil')),
        ('IO', _('British Indian Ocean Territory')),
        ('BN', _('Brunei Darussalam')),
        ('BG', _('Bulgaria')),
        ('BF', _('Burkina Faso')),
        ('BI', _('Burundi')),
        ('KH', _('Cambodia')),
        ('CM', _('Cameroon')),
        ('CV', _('Cape Verde')),
        ('KY', _('Cayman Islands')),
        ('CF', _('Central African Republic')),
        ('TD', _('Chad')),
        ('CL', _('Chile')),
        ('CN', _('China')),
        ('CX', _('Christmas Island')),
        ('CC', _('Cocos (Keeling) Islands')),
        ('CO', _('Colombia')),
        ('KM', _('Comoros')),
        ('CG', _('Congo')),
        ('CK', _('Cook Islands')),
        ('CR', _('Costa Rica')),
        ('HR', _('Croatia')),
        ('CU', _('Cuba')),
        ('CY', _('Cyprus')),
        ('CZ', _('Czech Republic')),
        ('DK', _('Denmark')),
        ('DJ', _('Djibouti')),
        ('DM', _('Dominica')),
        ('DO', _('Dominican Republic')),
        ('TP', _('East Timor')),
        ('EC', _('Ecuador')),
        ('EG', _('Egypt')),
        ('SV', _('El Salvador')),
        ('GQ', _('Equatorial Guinea')),
        ('ER', _('Eritrea')),
        ('EE', _('Estonia')),
        ('ET', _('Ethiopia')),
        ('FK', _('Falkland Islands')),
        ('FO', _('Faroe Islands')),
        ('FJ', _('Fiji')),
        ('FI', _('Finland')),
        ('CS', _('Former Czechoslovakia')),
        ('SU', _('Former USSR')),
        ('FX', _('France (European Territory)')),
        ('GF', _('French Guyana')),
        ('TF', _('French Southern Territories')),
        ('GA', _('Gabon')),
        ('GM', _('Gambia')),
        ('GE', _('Georgia')),
        ('GH', _('Ghana')),
        ('GI', _('Gibraltar')),
        ('GR', _('Greece')),
        ('GL', _('Greenland')),
        ('GD', _('Grenada')),
        ('GP', _('Guadeloupe (French)')),
        ('GU', _('Guam (USA)')),
        ('GT', _('Guatemala')),
        ('GN', _('Guinea')),
        ('GW', _('Guinea Bissau')),
        ('GY', _('Guyana')),
        ('HT', _('Haiti')),
        ('HM', _('Heard and McDonald Islands')),
        ('HN', _('Honduras')),
        ('HK', _('Hong Kong')),
        ('HU', _('Hungary')),
        ('IS', _('Iceland')),
        ('IN', _('India')),
        ('ID', _('Indonesia')),
        ('IR', _('Iran')),
        ('IQ', _('Iraq')),
        ('IL', _('Israel')),
        ('CI', _('Ivory Coast (Cote D&#39;Ivoire)')),
        ('JM', _('Jamaica')),
        ('JP', _('Japan')),
        ('JO', _('Jordan')),
        ('KZ', _('Kazakhstan')),
        ('KE', _('Kenya')),
        ('KI', _('Kiribati')),
        ('KW', _('Kuwait')),
        ('KG', _('Kyrgyzstan')),
        ('LA', _('Laos')),
        ('LV', _('Latvia')),
        ('LB', _('Lebanon')),
        ('LS', _('Lesotho')),
        ('LR', _('Liberia')),
        ('LY', _('Libya')),
        ('LI', _('Liechtenstein')),
        ('LT', _('Lithuania')),
        ('LU', _('Luxembourg')),
        ('MO', _('Macau')),
        ('MK', _('Macedonia')),
        ('MG', _('Madagascar')),
        ('MW', _('Malawi')),
        ('MY', _('Malaysia')),
        ('MV', _('Maldives')),
        ('ML', _('Mali')),
        ('MT', _('Malta')),
        ('MH', _('Marshall Islands')),
        ('MQ', _('Martinique (French)')),
        ('MR', _('Mauritania')),
        ('MU', _('Mauritius')),
        ('YT', _('Mayotte')),
        ('MX', _('Mexico')),
        ('FM', _('Micronesia')),
        ('MD', _('Moldavia')),
        ('MC', _('Monaco')),
        ('MN', _('Mongolia')),
        ('MS', _('Montserrat')),
        ('MA', _('Morocco')),
        ('MZ', _('Mozambique')),
        ('MM', _('Myanmar')),
        ('NA', _('Namibia')),
        ('NR', _('Nauru')),
        ('NP', _('Nepal')),
        ('NL', _('Netherlands')),
        ('AN', _('Netherlands Antilles')),
        ('NT', _('Neutral Zone')),
        ('NC', _('New Caledonia (French)')),
        ('NI', _('Nicaragua')),
        ('NE', _('Niger')),
        ('NG', _('Nigeria')),
        ('NU', _('Niue')),
        ('NF', _('Norfolk Island')),
        ('KP', _('North Korea')),
        ('MP', _('Northern Mariana Islands')),
        ('NO', _('Norway')),
        ('OM', _('Oman')),
        ('PK', _('Pakistan')),
        ('PW', _('Palau')),
        ('PA', _('Panama')),
        ('PG', _('Papua New Guinea')),
        ('PY', _('Paraguay')),
        ('PE', _('Peru')),
        ('PH', _('Philippines')),
        ('PN', _('Pitcairn Island')),
        ('PL', _('Poland')),
        ('PF', _('Polynesia (French)')),
        ('PT', _('Portugal')),
        ('PR', _('Puerto Rico')),
        ('QA', _('Qatar')),
        ('RE', _('Reunion (French)')),
        ('RO', _('Romania')),
        ('RU', _('Russian Federation')),
        ('RW', _('Rwanda')),
        ('GS', _('S. Georgia &amp; S. Sandwich Isls.')),
        ('SH', _('Saint Helena')),
        ('KN', _('Saint Kitts &amp; Nevis Anguilla')),
        ('LC', _('Saint Lucia')),
        ('PM', _('Saint Pierre and Miquelon')),
        ('ST', _('Saint Tome (Sao Tome) and Principe')),
        ('VC', _('Saint Vincent &amp; Grenadines')),
        ('WS', _('Samoa')),
        ('SM', _('San Marino')),
        ('SA', _('Saudi Arabia')),
        ('SN', _('Senegal')),
        ('SC', _('Seychelles')),
        ('SL', _('Sierra Leone')),
        ('SG', _('Singapore')),
        ('SK', _('Slovak Republic')),
        ('SI', _('Slovenia')),
        ('SB', _('Solomon Islands')),
        ('SO', _('Somalia')),
        ('ZA', _('South Africa')),
        ('KR', _('South Korea')),
        ('LK', _('Sri Lanka')),
        ('SD', _('Sudan')),
        ('SR', _('Suriname')),
        ('SJ', _('Svalbard and Jan Mayen Islands')),
        ('SZ', _('Swaziland')),
        ('SE', _('Sweden')),
        ('CH', _('Switzerland')),
        ('SY', _('Syria')),
        ('TJ', _('Tadjikistan')),
        ('TW', _('Taiwan')),
        ('TZ', _('Tanzania')),
        ('TH', _('Thailand')),
        ('TG', _('Togo')),
        ('TK', _('Tokelau')),
        ('TO', _('Tonga')),
        ('TT', _('Trinidad and Tobago')),
        ('TN', _('Tunisia')),
        ('TR', _('Turkey')),
        ('TM', _('Turkmenistan')),
        ('TC', _('Turks and Caicos Islands')),
        ('TV', _('Tuvalu')),
        ('UG', _('Uganda')),
        ('UA', _('Ukraine')),
        ('AE', _('United Arab Emirates')),
        ('UY', _('Uruguay')),
        ('MIL', _('USA Military')),
        ('UM', _('USA Minor Outlying Islands')),
        ('UZ', _('Uzbekistan')),
        ('VU', _('Vanuatu')),
        ('VA', _('Vatican City State')),
        ('VE', _('Venezuela')),
        ('VN', _('Vietnam')),
        ('VG', _('Virgin Islands (British)')),
        ('VI', _('Virgin Islands (USA)')),
        ('WF', _('Wallis and Futuna Islands')),
        ('EH', _('Western Sahara')),
        ('YE', _('Yemen')),
        ('YU', _('Yugoslavia')),
        ('ZR', _('Zaire')),
        ('ZM', _('Zambia')),
        ('ZW', _('Zimbabwe')),
    )

########
# Models
########

class LocationAwareMicroformat(models.Model):
    """
    An abstract database model that provides "de-normalized" fields to represent
    the adr and geo microformats.

    This class also provides two functions: adr and geo to return UTF
    representations of the appropriate microformats.
    """
    # This first part represents an adr Microformat.
    # 
    # See:
    #
    # http://microformats.org/wiki/adr
    #
    # adr (pronounced "adder"; FAQ: "why 'adr'?") is a simple format for marking
    # up address information, suitable for embedding in HTML, XHTML, Atom, RSS,
    # and arbitrary XML. adr is a 1:1 representation of the adr property in the
    # vCard standard (RFC2426) in HTML, one of several open microformat standards.
    # It is also a property of hCard. 
    street_address = models.CharField(
            _('Street Address'), 
            max_length=128, 
            blank=True
            ) 
    extended_address = models.CharField(
            _('Extended Address'), 
            max_length=128, 
            blank=True
            )
    locality = models.CharField(
            _('Town / City'), 
            max_length=128, 
            blank=True
            )
    region = models.CharField(
            _('County / State'), 
            max_length=128, 
            blank=True
            )
    country_name = models.CharField(
            _('Country'), 
            max_length=3, 
            choices = COUNTRY_LIST, 
            blank=True,
            null=True
            )
    postal_code = models.CharField(
            _('Post Code'), 
            max_length=32, 
            blank=True
            )
    post_office_box = models.CharField(
            _('Post Office Box'),
            max_length=32,
            blank=True
            )
    # Represents a geo microformat.
    #
    # See:
    #
    # http://microformats.org/wiki/geo
    #
    # For more information
    latitude = models.FloatField(
            _('Latitude'),
            null=True,
            blank=True,
            help_text=_(u'degrees decimal, e.g. 37.408183 (±90)')
            )
    longitude = models.FloatField(
            _('Longitude'),
            null=True,
            blank=True,
            help_text=_(u'degrees decimal, e.g. -122.13855 (±180)')
            )
    
    def adr(self):
        """
        Returns a Unicode string representation of the adr microformat
        associated with this instance.
        """
        result = u', '.join((x for x in (
            self.street_address, 
            self.extended_address,
            self.locality, 
            self.region, 
            self.country_name and self.get_country_name_display() or self.country_name, 
            self.postal_code,
            self.post_office_box,
            ) if x and x.strip()))
        if result:
            return result
        else:
            return None

    def geo(self):
        """
        Returns a Unicode string representation of the geo microformat
        associated with this instance.
        """
        if self.latitude and self.longitude:
            return u' '.join((
                _('lat'), 
                str(self.latitude), 
                _('long'), 
                str(self.longitude)
                ))
        else:
            return None

    class Meta:
        abstract = True


class hCard(LocationAwareMicroformat):
    """
    A lightweight representation of the hCard microformat with no Foreign Key
    dependancies.

    For a complete and compliant representation use the hCardComplete model

    For more information about this microformat see:

    http://microformats.org/wiki/hcard

    hCard is a simple, open, distributed format for representing people,
    companies, organizations, and places, using a 1:1 representation of vCard
    (RFC2426) properties and values in semantic HTML or XHTML. hCard is one of
    several open microformat standards suitable for embedding in HTML, XHTML,
    Atom, RSS, and arbitrary XML. 
    
    Field help text is derived from Microformats site. See:

    http://microformats.org/wiki/hcard-singular-properties
    """
    family_name = models.CharField(
            _('Family Name'),
            max_length=64,
            blank=True,
            help_text=_('Surname')
            )
    given_name = models.CharField(
            _('Given Name'),
            max_length=64,
            blank=True,
            help_text=_('Forename')
            )
    additional_name = models.CharField(
            _('Additional Name(s)'),
            max_length=128,
            blank=True,
            help_text=_('e.g. middle names')
            )
    honorific_prefix = models.CharField(
            _('Honorific Prefix'),
            max_length=32,
            blank=True,
            help_text=_('e.g. Dr, Professor etc')
            )
    honorific_suffix = models.CharField(
            _('Honorific Suffix'),
            max_length=32,
            blank=True,
            help_text=_('e.g. BA, MSc etc')
            )
    nickname = models.CharField(
            _('Nickname'),
            max_length=64,
            blank=True,
            help_text=_('For recording nickname, handle, username etc...')
            )
    # A person only has a single physical birthday (reincarnation cannot be 
    # scientifically substantiated and thus constitues the creation of a new 
    # directory object rather than the re-birth of an existing object, and 
    # being 'born again' is not the physical event that 'bday' represents). 
    # Thus 'bday' is singular.
    bday = models.DateField(
            _('Date of Birth'),
            null=True,
            blank=True
            )
    # A URL for the person or organization represented by this hCard
    url = models.URLField(
            _('URL'),
            verify_exists=False,
            blank=True,
            help_text=_("e.g. http://www.company.com/")
            )
    # The tz property represents the contact's current timezone.
    tz = models.CharField(
            _('Timezone'),
            max_length=8,
            blank=True,
            choices=TIMEZONE,
            help_text=_("Hour(s) from GMT")
            )
    # Represents a photo/image/logo associated with an instance
    image = models.ImageField(
            upload_to='hcardphoto',
            null=True,
            blank=True
            )
    # The 'rev' property represents the datetime of the last revision 
    rev = models.DateTimeField(
            _('Revision'),
            auto_now=True,
            help_text=_("Last revised on")
            )
    # Telephone numbers
    tel_work = models.CharField(
            _('Telephone (work)'),
            max_length=64,
            blank=True
            )
    tel_home = models.CharField(
            _('Telephone (home)'),
            max_length=64,
            blank=True
            )
    tel_fax = models.CharField(
            _('Fax'),
            max_length=64,
            blank=True
            )
    # Email
    email_work = models.EmailField(
            _('Email (work)'),
            blank=True
            )
    email_home = models.EmailField(
            _('Email (home)'),
            blank = True
            )
    # Org related
    org = models.CharField(
            _('Organization'),
            max_length=128,
            blank=True
            )
    title = models.CharField(
            _('Title'),
            max_length=128,
            blank=True,
            help_text=_('The job title a person has within the specified'
                ' organization e.g. CEO, Vice President, Software Engineer')
            )
    role = models.CharField(
            _('Role'),
            max_length=256,
            blank=True,
            help_text=_("The role a person plays within the specified"\
                    " organization")
            )

    def n(self):
        """
        Uses the values in honorific-prefix, given-name, additional-name,
        family-name and honorific-suffix to build a name "n".

        Ensures that *at least* given-name, additional-name and family-name
        produce something useful.

        Legal precedents afford a person a single given-name (with multiple
        additional-name(s)) and single family-name, thus, only a single "n"
        property is permitted.
        """
        name = ' '.join((i for i in (
            self.given_name,
            self.additional_name,
            self.family_name) if i.strip()))
        if name:
            return ' '.join((i for i in(
                self.honorific_prefix,
                name,
                self.honorific_suffix) if i.strip()))
        else:
            return '' 

    def fn(self, is_org=False):
        """
        Formatted Name

        An entity has only one "best" / most preferred way of formatting their
        name, and legally organizations have only a single name, thus "fn" is
        singular. 
        """
        name = self.n()
        if not name:
            if org:
                return org
            else:
                return _('None')
        else:
            return name

    class Meta:
        verbose_name = _('hCard')
        verbose_name_plural = _('hCards')

    def __unicode__(self):
        return self.fn()

class hCalendar(LocationAwareMicroformat):
    """
    Represents an hCalendar Microformat. 

    See:

    http://microformats.org/wiki/hcalendar

    hCalendar is a simple, open, distributed calendaring and events format,
    based on the iCalendar standard (RFC2445), suitable for embedding in HTML or
    XHTML, Atom, RSS, and arbitrary XML. hCalendar is one of several open
    microformat standards. 
    """
    summary = models.CharField(
            _('Summary'),
            max_length=256
            )
    location = models.CharField(
            _('Location'),
            max_length=256,
            blank=True
            )
    url = models.URLField(
            _('URL'),
            verify_exists=False,
            blank=True
            )
    dtstart = models.DateTimeField(_('Start'))
    dtend = models.DateTimeField(
            _('End'),
            null=True,
            blank=True
            )
    all_day_event = models.BooleanField(
            _('All day event'),
            default=False
            )
    tz = models.CharField(
            _('Timezone'),
            max_length=8,
            blank=True,
            choices=TIMEZONE,
            help_text=_("Hour(s) from GMT")
            )
    description = models.TextField(
            _('Description'),
            blank=True
            )
    attendees = models.ManyToManyField(
            hCard,
            related_name='attendees',
            null=True,
            blank=True
            )
    contacts = models.ManyToManyField(
            hCard,
            related_name='contacts',
            null=True,
            blank=True
            )
    organizers = models.ManyToManyField(
            hCard,
            related_name='organizers',
            null=True,
            blank=True
            )

    class Meta:
        verbose_name = _('Event')
        verbose_name_plural = _('Events')

    def __unicode__(self):
        return u"%s - %s"%(self.dtstart.strftime('%a %b %d %Y, %I:%M%p'),
                self.summary)

class hListing(LocationAwareMicroformat):
    """
    hListing is a proposal for an open, distributed listings (UK English:
    small-ads; classifieds) format suitable for embedding in (X)HTML, Atom, RSS,
    and arbitrary XML. hListing would be one of several microformats open
    standards. 

    If hReview is about an item and what you think of it, hListing is about an
    item and what you want to do with it. 

    For more information see:

    http://microformats.org/wiki/hlisting-proposal
    """
    LISTING_TYPE = (
            ('sell', _('To sell')),
            ('rent', _('For rent')),
            ('trade', _('To trade')),
            ('meet', _('Meetup')),
            ('announce', _('Announcement')),
            ('offer', _('On offer')),
            ('wanted', _('Is wanted')),
            ('event', _('Event')),
            ('service', _('Service')),
            )

    listing_action = models.CharField(
            _('Listing Action'),
            max_length=8,
            choices=LISTING_TYPE,
            help_text=_('The type of listing this is')
            )
    summary = models.TextField(
            _("Summary"),
            blank=True
            )
    description = models.TextField(
            _("Description")
            )
    lister_fn = models.CharField(
            _('Lister Name'),
            max_length=128,
            help_text=_('Name of the person / organization making the listing')
            )
    lister_email = models.EmailField(
            _("Lister's Email"),
            blank=True
            )
    lister_url = models.URLField(
            _("Lister's URL"),
            blank=True,
            verify_exists=False
            )
    lister_tel = models.CharField(
            _("Lister's Telephone Number"),
            max_length=64,
            blank=True
            )
    dtlisted = models.DateTimeField(
            _("Listing starts on"),
            null=True,
            blank=True
            )
    dtexprired = models.DateTimeField(
            _("Listing expires after"),
            null=True,
            blank=True
            )
    price = models.CharField(
            _("Price"),
            max_length=128,
            blank=True
            )
    item_fn = models.CharField(
            _('Item Name'),
            max_length=128,
            help_text=_('Name of the item / person / organization being listed')
            )
    item_url = models.URLField(
            _("Item's URL"),
            blank=True,
            verify_exists=False
            )
    item_photo = models.ImageField(
            _("A photo of the item"),
            upload_to='hlistingphoto',
            null=True,
            blank=True
            )

    class Meta:
        verbose_name = _('hListing')
        verbose_name_plural = _('hListings')

    def __unicode__(self):
        return u"%s (%s: %s) - %s"%(self.item_fn,
                self.get_listing_action_display(),
                self.lister_fn,
                self.description)

class hReview(LocationAwareMicroformat):
    """
    hReview is a simple, open, distributed format, suitable for embedding
    reviews (of products, services, businesses, events, etc.) in HTML, XHTML,
    Atom, RSS, and arbitrary XML. hReview is one of several microformats open
    standards.

    For more information see:

    http://microformats.org/wiki/hreview

    (I've omitted the "version" field as I'm assuming version 0.2 of the hReview
    microformat specification [or later]. See the URL referenced above for more
    information.)
    """
    ITEM_TYPE = (
            ('product', _('Product')),
            ('business', _('Business')),
            ('event', _('Event')),
            ('person', _('Person')),
            ('place', _('Place')),
            ('website', _('Website')),
            ('url', _('URL')),
            ('book', _('Book')),
            ('film', _('Film')),
            ('music', _('Music')),
            ('software', _('Software')),
            )

    RATINGS = (
            (1, _('1')),
            (2, _('2')),
            (3, _('3')),
            (4, _('4')),
            (5, _('5')),
            )

    # This optional field serves as a title for the review itself.
    summary = models.TextField(
            _("Summary"),
            blank=True,
            help_text=_('To serve as a title for the review.')
            )
    # This optional field contains the full text representing the 
    # written opinion of the reviewer. The field may include valid HTML markup 
    # (e.g. paragraphs). User agents should preserve any markup. Multiple 
    # descriptions or section descriptions (e.g. pros and cons, plusses and 
    # minusses) should be included in the description field.
    description = models.TextField(
            _('Description'),
            blank=True
            )
    # The rating is a fixed point integer (one decimal point of precision) 
    # from 1 to 5 inclusive indicating a rating for the item, higher
    # indicating a better rating by default. 
    rating = models.IntegerField(
            _('Rating'),
            choices=RATINGS,
            help_text=_('1 = worst, 5 = best')
            )
    # This optional field when present must provide an ISO8601 
    # absolute date time of when the review was written or otherwise authored. 
    dtreviewed = models.DateTimeField(
            _('Date of Review'),
            null=True,
            blank=True
            )
    # The optional field specifies the person who authored the review. 
    # If the reviewer is specified, an hCard representing the reviewer must be 
    # provided. For anonymous reviews, use "anonymous" (without quotes) for the 
    # full name of the reviewer.
    reviewer = models.CharField(
            _('Reviewer Name'),
            max_length=256,
            default=_('Anonymous'),
            help_text=_('Defaults to "Anonymous" if not supplied')
            )
    # This optional field "type" provides the type of the item being 
    # reviewed, one of the following: product, business, event, person, place, 
    # website, url.
    # Nota Bene: I (ntoll) have added the following types to the choices list:
    # book, film, music, software.
    type = models.CharField(
            _("Item Type"),
            max_length=8,
            choices=ITEM_TYPE,
            help_text=_('The kind of thing this review is for')
            )
    # The rest of these fields allow the item being reviewed to be identified
    # with hCard or hCalendar microformats.
    # As this is also a location aware microformat you'll also be able to store
    # the address or geo information of the thing being reviewed.
    fn = models.CharField(
            _('Item Name'),
            max_length=256
            )
    url = models.URLField(
            _('Item URL'),
            blank=True,
            verify_exists=True
            )
    tel = models.CharField(
            _('Telephone'),
            max_length=64,
            blank=True
            )
    photo = models.ImageField(
            upload_to='hreviewphoto',
            null=True,
            blank=True
            )
    dtstart = models.DateTimeField(
            _('Start'),
            null=True,
            blank=True
            )
    dtend = models.DateTimeField(
            _('End'),
            null=True,
            blank=True
            )
    all_day_event = models.BooleanField(
            _('All day event'),
            default=False
            )
    tz = models.CharField(
            _('Timezone'),
            max_length=8,
            blank=True,
            choices=TIMEZONE,
            help_text=_("Hour(s) from GMT")
            )
    
    class Meta:
        verbose_name = _('hReview')
        verbose_name_plural = _('hReviews')

    def __unicode__(self):
        return u"%s: %s/5"%(self.fn, self.get_rating_display())

class geo(models.Model):
    """
    Represents the geo microformat.

    See:

    http://microformats.org/wiki/geo

    geo (pronounced "gee-oh") is a simple format for marking up WGS84 geographic
    coordinates (latitude; longitude), suitable for embedding in HTML or XHTML,
    Atom, RSS, and arbitrary XML. geo is a 1:1 representation of the "geo"
    property in the vCard standard (RFC2426) in HTML, one of several open
    microformat standards. 
    """

    latitude = models.FloatField(
            _('Latitude'),
            help_text=_(u'degrees decimal, e.g. 37.408183 (±90)')
            )
    latitude_description = models.CharField(
            _('Latitude description'),
            max_length=32,
            help_text=_(u'e.g. N 37° 24.491'),
            blank=True
            )
    longitude = models.FloatField(
            _('Longitude'),
            help_text=_(u'degrees decimal, e.g. -122.13855 (±180)')
            )
    longitude_description = models.CharField(
            _('Longitude description'),
            max_length=32,
            help_text=_(u'e.g. W 122° 08.313'),
            blank=True
            )

    class Meta:
        verbose_name = _('Geolocation')
        verbose_name_plural = _('Geolocations')

    def __unicode__(self):
        return ' '.join((
            'lat', 
            str(self.latitude), 
            'long', 
            str(self.longitude)
            ))

class xfn_values(models.Model):
    """
    Potential values to be used in the rel attribute of the XFM "microformat"

    See:

    http://www.gmpg.org/xfn/1

    Summary of values (loaded in the fixtures)

    relationship category         |  XFN values
    ------------------------------+--------------------------------
    friendship (at most one):     |  friend acquaintance contact
    physical:                     |  met
    professional:                 |  co-worker colleague
    geographical (at most one):   |  co-resident neighbor
    family (at most one):         |  child parent sibling spouse kin
    romantic:                     |  muse crush date sweetheart
    identity:                     |  me
    """

    VALUE_LIST = (
            ('friend', _('Friend')),
            ('acquaintance', _('Acquaintance')),
            ('contact', _('Contact')),
            ('met', _('Met')),
            ('co-worker', _('Co-worker')),
            ('colleague', _('Colleague')),
            ('co-resident', _('Co-resident')),
            ('neighbor', _('Neighbour')),
            ('child', _('Child')),
            ('parent', _('Parent')),
            ('sibling', _('Sibling')),
            ('spouse', _('Spouse')),
            ('kin', _('Kin')),
            ('muse', _('Muse')),
            ('crush', _('Crush')),
            ('date', _('Date')),
            ('sweetheart', _('Sweetheart')),
            ('me', _('Me'))
        )
    value = models.CharField(
            _('Relationship'),
            max_length=16,
            choices=VALUE_LIST
            )

    class Meta:
        verbose_name = _('XFN Relationship')
        verbose_name_plural = _('XFN Relationships')
        ordering = ['value']

    def __unicode__(self):
        return self.get_value_display()

class xfn(models.Model):
    """
    XFN™ (XHTML Friends Network) is a simple way to represent human
    relationships using hyperlinks. In recent years, blogs and blogrolls have
    become the fastest growing area of the Web. XFN enables web authors to
    indicate their relationship(s) to the people in their blogrolls simply by
    adding a 'rel' attribute to their <a href> tags, e.g.:

    <a href="http://jeff.example.org" rel="friend met">... 
    """
    # The person who is indicating the relationship - must be a user of the
    # application
    source = models.ForeignKey(
            User,
            related_name='source'
            )
    # The person who is the "friend"
    target = models.CharField(
            max_length=255
            )
    # A URL indicating who is the "friend" (if not a user in the system)
    url = models.URLField(
            _('URL'),
            verify_exists=False,
            )
    # The type of relationship
    relationships = models.ManyToManyField(xfn_values)
    
    class Meta:
        verbose_name = _('XFN')
        verbose_name_plural = _('XFN definitions')

    def __unicode__(self):
        vals = u', '.join(x.__unicode__() for x in self.relationships.all())
        if vals:
            return self.target+u' ('+vals+u')'
        else:
            return self.target 

class hFeed(models.Model):
    """
    The hFeed model is used for representing feeds in the hAtom microformat.

    hAtom is a microformat for content that can be syndicated, primarily but not
    exclusively weblog postings. hAtom is based on a subset of the Atom
    syndication format. hAtom will be one of several microformats open
    standards.

    For more information see:

    http://microformats.org/wiki/hatom

    """
    category = models.TextField(
            _('Category(ies)'),
            blank=True,
            help_text=_('A comma-separated list of keywords or phrases')
            )

    class Meta:
        verbose_name = _('hFeed');
        verbose_name_plural = _('hFeeds')

    def __unicode__(self):
        if self.category:
            return self.category
        else:
            return _('Uncategorized feed')

class hEntry(models.Model):
    """
    The hEntry model is used for representing entries in the hAtom microformat.

    hAtom is a microformat for content that can be syndicated, primarily but not
    exclusively weblog postings. hAtom is based on a subset of the Atom
    syndication format. hAtom will be one of several microformats open
    standards.

    For more information see:

    http://microformats.org/wiki/hatom
    """

    # An Entry Title element represents the concept of an Atom entry title
    # The "atom:title" element is a Text construct that conveys a human-readable
    # title for an entry or feed. 
    entry_title = models.TextField(
            _("Entry Title"),
            help_text=_('Title for the entry.')
            )
    # An Entry Content element represents the concept of an Atom content
    # The "atom:content" element either contains or links to the content of the
    # entry. The content of atom:content is Language-Sensitive. 
    entry_content = models.TextField(
            _('Content'),
            blank=True
            )
    # An Entry Summary element represents the concept of an Atom summary
    # The "atom:summary" element is a Text construct that conveys a short
    # summary, abstract, or excerpt of an entry. 
    entry_summary = models.TextField(
            _('Summary'),
            blank=True
            )
    # An Entry Updated element represents the concept of Atom updated
    # The "atom:updated" element is a Date construct indicating the most recent
    # instant in time when an entry or feed was modified in a way the publisher
    # considers significant. Therefore, not all modifications necessarily result
    # in a changed atom:updated value.
    updated = models.DateTimeField(
            _('Updated on'),
            )
    # An Entry Published element represents the concept of Atom published
    # The "atom:published" element is a Date construct indicating an instant in
    # time associated with an event early in the life cycle of the entry. 
    published = models.DateTimeField(
            _('Published on'),
            null=True,
            blank=True
            )
    # An Entry Author element represents the concept of an Atom author
    # An Entry Author element MUST be encoded in an hCard
    # The "atom:author" element is a Person construct that indicates the author
    # of the entry or feed.
    author = models.CharField(
            _('Author'),
            max_length=256,
            default=_('Anonymous'),
            help_text=_('Defaults to "Anonymous" if not supplied')
            )
    # A permalink to the referenced entry
    bookmark = models.URLField(
            _('Bookmark (permalink)'),
            verify_exists=False,
            blank=True
            )
    # The feed this entry is associated with
    hfeed = models.ForeignKey(
            hFeed,
            null=True,
            related_name='entries'
            )

    class Meta:
        verbose_name = _('hEntry')
        verbose_name_plural = _('hEntries')

    def __unicode__(self):
        return u"%s: %s (%s)"%(
                self.entry_title, 
                self.author,
                self.updated.strftime('%c')
                )

class hNews(hEntry, LocationAwareMicroformat):
    """
    The hNews model is used for representing online news content.

    hNews is a microformat that expands the hAtom standard represented by
    the hEntry mondel so it is better suited for journalistic content.

    It was originated by The Associated Press and Media Standards Trust 
    and first published as a draft in Fall 2009.

    For more information see:

    http://microformats.org/wiki/hnews
    """
    # Source Organization represents the originating organization for the news story. 
    source_org = models.TextField(
            _('Source organization')
            )
    source_url = models.URLField(
            _('Link to the source organization'),
            verify_exists=False,
            blank=True
            )
    # principles represents the statement of principles and ethics used by the news 
    # organization that produced the news story.
    principles_url = models.URLField(
            _('Link to statement of principles'),
            verify_exists=False,
            blank=True
            )
    # A link to an image that will tease the statement of principles
    # by default it's set to one provided by the hNews creators
    principles_img = models.URLField(
            _('Link to image representing principles link'),
            verify_exists=False,
            blank=True,
            default='http://labs.ap.org/principles-button-blue.png'
            )
    # The licensing and attribution requirements for republication
    license_url = models.URLField(
            _('Link to license'),
            verify_exists=False,
            blank=True
            )
    license_description = models.TextField(
            _('Description of license'),
            blank=True
            )

    class Meta:
        verbose_name = _('hNews')
        verbose_name_plural = _('hNews')

    def __unicode__(self):
        return u"%s: %s (%s)"%(
                self.entry_title, 
                self.source_org,
                self.updated.strftime('%c')
                )

    def dateline(self):
        """
        Returns a Unicode string representation of the dateline where
        the story originated
        """
        result = u', '.join((x for x in (
            self.locality, 
            self.country_name and self.get_country_name_display() or self.country_name, 
            ) if x and x.strip()))
        if result:
            return result
        else:
            return None


class hCardComplete(models.Model):
    """ 
    A full (correct) representation an hCard microformat.

    See:

    http://microformats.org/wiki/hcard

    For a more simple and "flatter" representation of hCard use the hCard class
    defined above.

    hCard is a simple, open, distributed format for representing people,
    companies, organizations, and places, using a 1:1 representation of vCard
    (RFC2426) properties and values in semantic HTML or XHTML. hCard is one of
    several open microformat standards suitable for embedding in HTML, XHTML,
    Atom, RSS, and arbitrary XML. 
    
    Field help text is derived from Microformats site. See:

    http://microformats.org/wiki/hcard-singular-properties
    """
    family_name = models.CharField(
            _('Family Name'),
            max_length=64,
            blank=True,
            help_text=_('Surname')
            )
    given_name = models.CharField(
            _('Given Name'),
            max_length=64,
            blank=True,
            help_text=_('Forename')
            )
    additional_name = models.CharField(
            _('Additional Name(s)'),
            max_length=128,
            blank=True,
            help_text=_('e.g. middle names')
            )
    honorific_prefix = models.CharField(
            _('Honorific Prefix'),
            max_length=32,
            blank=True,
            help_text=_('e.g. Dr, Professor etc')
            )
    honorific_suffix = models.CharField(
            _('Honorific Suffix'),
            max_length=32,
            blank=True,
            help_text=_('e.g. BA, MSc etc')
            )
    nickname = models.CharField(
            _('Nickname'),
            max_length=64,
            blank=True,
            help_text=_('For recording nicknames, handles, usernames etc...')
            )
    # A person only has a single physical birthday (reincarnation cannot be 
    # scientifically substantiated and thus constitues the creation of a new 
    # directory object rather than the re-birth of an existing object, and 
    # being 'born again' is not the physical event that 'bday' represents). 
    # Thus 'bday' is singular.
    bday = models.DateField(
            _('Date of Birth'),
            null=True,
            blank=True
            )
    geo = models.ForeignKey(
            geo, 
            null=True,
            help_text=_("The 'geo' property represents the contact's actual"\
                " location, not a coordinate approximation of an 'adr'.")
            )
    # A URL for the person or organization represented by this hCard
    url = models.URLField(
            _('URL'),
            verify_exists=False,
            blank=True,
            help_text=_("e.g. http://www.company.com/")
            )
    # The tz property represents the contact's current timezone.
    tz = models.CharField(
            _('Timezone'),
            max_length=8,
            blank=True,
            choices=TIMEZONE,
            help_text=_("Hour(s) from GMT")
            )
    # When sorting a name, it doesn't make sense for it to have more than one
    # way of sorting it, thus "sort-string" must be singular.
    sort_string = models.CharField(
            _('Sort String'),
            max_length=32,
            blank=True,
            help_text=_("The sort string used when sorting this contact.")
            )
    # The "uid" property is a globally unique identifier corresponding to the
    # individual or resource associated with the hCard. It doesn't make sense
    # for an hCard to have more than one "uid". 
    uid = models.CharField(
            _('UID'),
            max_length=128,
            blank=True,
            help_text=_('Globally Unique ID')
            )
    # The "class" property indicates the confidentiality/access classification
    # of the hCard as a whole, and thus it only makes sense for there to be one
    # (or rather, makes no sense for there to be more than one).
    klass = models.CharField(
            _('Class'),
            max_length=128,
            blank=True,
            help_text=_("The 'class' property indicates the"\
                " confidentiality / access classification of the contact.")
            )
    # The 'rev' property represents the datetime of the revision of the hCard as
    # a whole.
    # Why not use auto_now = True..? Well, this is the (optional) timestamp for
    # the hCard *as a whole* so revisions to data not stored in this table
    # should also cause the 'rev' to be updated. As a result, it is left to the
    # application to control this behaviour.
    rev = models.DateTimeField(
            _('Revision'),
            null=True,
            blank=True,
            help_text=_("Last revised on")
            )
    # Specifies information about other contact(s) acting on behalf of the
    # entity represented by the hCard 
    agents = models.ManyToManyField(
            "self", 
            symmetrical=False
            )

    def n(self):
        """
        Uses the values in honorific-prefix, given-name, additional-name,
        family-name and honorific-suffix to build a name "n".

        Ensures that *at least* given-name, additional-name and family-name
        produce something useful.

        Legal precedents afford a person a single given-name (with multiple
        additional-name(s)) and single family-name, thus, only a single "n"
        property is permitted.
        """
        name = u' '.join((i for i in (
            self.given_name,
            self.additional_name,
            self.family_name) if i.strip()))
        if name:
            return u' '.join((i for i in(
                self.honorific_prefix,
                name,
                self.honorific_suffix) if i.strip()))
        else:
            return '' 

    def fn(self, is_org=False):
        """
        Formatted Name

        Use is_org=True to use organization name if this hCard represents an
        organization. Otherwise this method returns self.n(). If self.n()
        returns nothing then an attempt is made to return an org. If all else
        fails returns 'None'

        A person has only one "best" / most preferred way of formatting their
        name, and legally organizations have only a single name, thus "fn" is
        singular. 
        """
        result = ''
        if is_org:
            o = self.org_set.filter(primary=True).order_by('id')
            if o:
                result = o[0].__unicode__()
            else:
                result = self.n()
        else:
            result = self.n()
            if not result:
                # check we have an organization we should use instead
                o = self.org_set.filter(primary=True).order_by('id')
                if o:
                    result = o[0].__unicode__()

        if result:
            return result
        else:
            return _('None')

    class Meta:
        verbose_name = _('hCard')
        verbose_name_plural = _('hCards')

    def __unicode__(self):
        return self.fn()

class adr_type(models.Model):
    """
    Represents a type of adr Microformat

    See:
    
    http://microformats.org/wiki/hcard#adr_tel_email_types

    Also see: http://www.ietf.org/rfc/rfc2426.txt (quoted below)

    The type parameter values can include:

    "dom" to indicate a domestic delivery address; "intl" to indicate an
    international delivery address; "postal" to indicate a postal
    delivery address; "parcel" to indicate a parcel delivery address;
    "home" to indicate a delivery address for a residence; "work" to
    indicate delivery address for a place of work; and "pref" to indicate
    the preferred delivery address when more than one address is specified.

    """

    TYPE_LIST = (
            ('dom', _('Domestic')),
            ('intl', _('International')),
            ('postal', _('Postal')),
            ('parcel', _('Parcel')),
            ('home', _('Home')),
            ('work', _('Work')),
            ('pref', _('Preferred')),
            )

    name = models.CharField(
            _('Address Type'),
            max_length=8,
            choices=TYPE_LIST,
            default='intl'
            )

    class Meta:
        verbose_name = _('Address Type')
        verbose_name_plural = _('Address Types')

    def __unicode__(self):
        return self.get_name_display()

class adr(models.Model):
    """ 
    Represents an adr Microformat.
    
    See:

    http://microformats.org/wiki/adr

    adr (pronounced "adder"; FAQ: "why 'adr'?") is a simple format for marking
    up address information, suitable for embedding in HTML, XHTML, Atom, RSS,
    and arbitrary XML. adr is a 1:1 representation of the adr property in the
    vCard standard (RFC2426) in HTML, one of several open microformat standards.
    It is also a property of hCard. 
    """
    street_address = models.CharField(
            _('Street Address'), 
            max_length=128, 
            blank=True
            ) 
    extended_address = models.CharField(
            _('Extended Address'), 
            max_length=128, 
            blank=True
            )
    locality = models.CharField(
            _('Town / City'), 
            max_length=128, 
            blank=True
            )
    region = models.CharField(
            _('County / State'), 
            max_length=128, 
            blank=True
            )
    country_name = models.CharField(
            _('Country'), 
            max_length=3, 
            choices = COUNTRY_LIST, 
            blank=True
            )
    postal_code = models.CharField(
            _('Post Code'), 
            max_length=32, 
            blank=True
            )
    post_office_box = models.CharField(
            _('Post Office Box'),
            max_length=32,
            blank=True
            )
    types = models.ManyToManyField(adr_type)
    hcard = models.ForeignKey(hCardComplete, null=True)

    class Meta:
        verbose_name = _('Address')
        verbose_name_plural = _('Addresses')
    
    def __unicode__(self):
         result = u', '.join((x for x in (
            self.street_address, 
            self.extended_address,
            self.locality, 
            self.region, 
            self.get_country_name_display(), 
            self.postal_code,
            self.post_office_box) if x.strip()))
         if result:
             return result
         else:
             return _('None')

class tel_type(models.Model):
    """ 
    Represents a type of telephone number in the hCard microformat.

    See:

    http://microformats.org/wiki/hcard#adr_tel_email_types

    Also see: http://www.ietf.org/rfc/rfc2426.txt (quoted below)

    The type parameter values can include:
    
    "home" to indicate a telephone number associated with a residence,
    "msg" to indicate the telephone number has voice messaging support,
    "work" to indicate a telephone number associated with a place of
    work, "pref" to indicate a preferred-use telephone number, "voice" to
    indicate a voice telephone number, "fax" to indicate a facsimile
    telephone number, "cell" to indicate a cellular telephone number,
    "video" to indicate a video conferencing telephone number, "pager" to
    indicate a paging device telephone number, "bbs" to indicate a
    bulletin board system telephone number, "modem" to indicate a
    MODEM connected telephone number, "car" to indicate a car-phone telephone
    number, "isdn" to indicate an ISDN service telephone number, "pcs" to 
    indicate a personal communication services telephone number. The
    default type is "voice". These type parameter values can be specified
    as a parameter list (i.e., "TYPE=work;TYPE=voice") or as a value list
    (i.e., "TYPE=work,voice").  The default can be overridden to another
    set of values by specifying one or more alternate values. For example, the
    default TYPE of "voice" can be reset to a WORK and HOME, VOICE and FAX
    telephone number by the value list "TYPE=work,home,voice,fax".

    """

    TYPE_LIST = (
            ('voice', _('Voice')),
            ('home', _('Home')),
            ('msg', _('Message Service')),
            ('work', _('Work')),
            ('pref', _('Preferred')),
            ('fax', _('Fax')),
            ('cell', _('Cell/Mobile')),
            ('video', _('Videoconference')),
            ('pager', _('Pager')),
            ('bbs', _('Bulletin Board Service')),
            ('modem', _('Modem')),
            ('car', _('Carphone (fixed)')),
            ('isdn', _('ISDN')),
            ('pcs', _('Personal Communication Service')),
            )

    name = models.CharField(
            _('Telephone Number Type'),
            max_length=5,
            choices=TYPE_LIST,
            default='voice'
            )

    class Meta:
        verbose_name = _('Telephone Type')
        verbose_name_plural = _('Telephone Types')
    
    def __unicode__(self):
        return self.get_name_display()

class tel(models.Model):
    """
    Represents a telephone number in the hCard microformat.

    See:

    http://microformats.org/wiki/hcard
    
    """
    hcard = models.ForeignKey(hCardComplete)
    # A telephone number can have more than one type. e.g. pref, home, voice
    types = models.ManyToManyField(tel_type)
    value = models.CharField(
            _('Value'),
            max_length=64,
            help_text=_('(e.g. +44(0)1234 567876)')
            )

    class Meta:
        verbose_name = _('Telephone Number')
        verbose_name_plural = _('Telephone Numbers')
    
    def __unicode__(self):
        return self.value
    
class email_type(models.Model):
    """
    Represents a type of email in the hCard microformat.

    See:

    http://microformats.org/wiki/hcard#adr_tel_email_types

    Also see: http://www.ietf.org/rfc/rfc2426.txt (quoted below)

    Used to specify the format or preference of the electronic mail address. 
    The TYPE parameter values can include: "internet" to indicate an Internet
    addressing type, "x400" to indicate a X.400 addressing type or "pref"
    to indicate a preferred-use email address when more than one is
    specified. Another IANA registered address type can also be
    specified. The default email type is "internet". A non-standard value 
    can also be specified.

    """

    TYPE_LIST = (
            ('internet', _('Internet')),
            ('x400', _('x400')),
            ('pref', _('Preferred')),
            ('other', _('Other IANA address type')),
            )

    name = models.CharField(
            _('Email type'),
            max_length=8,
            choices=TYPE_LIST,
            default='internet'
            )

    class Meta:
        verbose_name = _('Email Type')
        verbose_name_plural = _('Email Types')

    def __unicode__(self):
        return self.get_name_display()

class email(models.Model):
    """
    Represents an email address in the hCard microformat.

    See:

    http://microformats.org/wiki/hcard
    
    """
    hcard = models.ForeignKey(hCardComplete)
    # An email address can have more than one type (but won't usually)
    types = models.ManyToManyField(email_type)
    value = models.CharField(
            _('Value'),
            max_length=64,
            help_text=_('(e.g. john.smith@company.com)')
            )
    
    class Meta:
        verbose_name = _('Email Address')
        verbose_name_plural = _('Email Addresses')
    
    def __unicode__(self):
        return self.value

class photo(models.Model):
    """
    Represents a photo associated with an hCard microformat instance

    See:

    http://microformats.org/wiki/hcard
    
    """
    hcard = models.ForeignKey(hCardComplete)
    image = models.ImageField(upload_to='hcardphoto')

    class  Meta:
        verbose_name = _('Photo')
        verbose_name_plural = _('Photos')

    def __unicode__(self):
        return _('Photo for hCard')

class logo(models.Model):
    """
    Represents a logo associated with an hCard microformat instance

    See:

    http://microformats.org/wiki/hcard
    
    """
    hcard = models.ForeignKey(hCardComplete)
    image = models.ImageField(upload_to='hcardlogo')

    class  Meta:
        verbose_name = _('Logo')
        verbose_name_plural = _('Logos')

    def __unicode__(self):
        return _('Logo for hCard')

class sound(models.Model):
    """
    Represents a sound associated with an hCard microformat instance

    See:

    http://microformats.org/wiki/hcard
    
    """
    hcard = models.ForeignKey(hCardComplete)
    recording = models.FileField(upload_to='hcardsounds')

    class  Meta:
        verbose_name = _('Sound')
        verbose_name_plural = _('Sounds')

    def __unicode__(self):
        return _('Sound for hCard')

class title(models.Model):
    """
    Represents a title a person has at the referenced organization associated 
    with an hCard microformat instance

    See:

    http://microformats.org/wiki/hcard
    
    """
    hcard = models.ForeignKey(hCardComplete)
    name = models.CharField(
            _('Title name'),
            max_length=128,
            help_text=_('e.g. CEO, Consultant, Principal')
            )

    class  Meta:
        verbose_name = _('Title')
        verbose_name_plural = _('Title')

    def __unicode__(self):
        return self.name 

class role(models.Model):
    """
    Represents the role a person plays within the organization associated with 
    an hCard microformat instance

    See:

    http://microformats.org/wiki/hcard
    
    """
    hcard = models.ForeignKey(hCardComplete)
    description = models.CharField(
            _('Role name'),
            max_length=256,
            help_text=_('The role played within the organization')
            )

    class  Meta:
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')

    def __unicode__(self):
        return self.description

class org(models.Model):
    """
    Represents an organisation associated with an hCard microformat instance

    See:

    http://microformats.org/wiki/hcard
    
    """
    hcard = models.ForeignKey(hCardComplete)
    name = models.CharField(
            _('Organization Name'),
            max_length=256
            )
    unit = models.CharField(
            _('Organizational Unit'),
            max_length=256,
            blank=True
            )
    primary = models.BooleanField(
            _('Primary organization'),
            default=True,
            help_text=_('This is the primary organization'\
                    ' associated with this contact')
            )
    title = models.ForeignKey(title, null=True)
    role = models.ForeignKey(role, null=True)

    class Meta:
        verbose_name = _('Organization')
        verbose_name_plural = _('Organizations')

    def __unicode__(self):
        if self.unit:
            return self.unit+', '+self.name
        else:
            return self.name


class note(models.Model):
    """
    Represents supplemental information or a comment associated with an hCard 
    microformat instance

    See:

    http://microformats.org/wiki/hcard
    
    """
    hcard = models.ForeignKey(hCardComplete)
    content = models.TextField(_('Note'))

    class Meta:
        verbose_name = _('Note')
        verbose_name_plural = _('Notes')

    def __unicode__(self):
        return self.content
    
class key(models.Model):
    """
    Represents a public key or authentication certificate associated with an 
    hCard microformat instance

    See:

    http://microformats.org/wiki/hcard
    
    """
    hcard = models.ForeignKey(hCardComplete)
    name = models.TextField(
            _('Key Details'),
            help_text = _('Details of a public key or authentication'\
                    ' certificate associated with this contact')
            )

    class Meta:
        verbose_name = _('Key')
        verbose_name_plural = _('Keys')

    def __unicode__(self):
        return self.name

class mailer(models.Model):
    """
    Represents the type of electronic mail software that is used by the entity 
    associated with an hCard microformat instance

    See:

    http://microformats.org/wiki/hcard
    
    """
    hcard = models.ForeignKey(hCardComplete)
    name = models.CharField(
            _('Mailer'),
            max_length=128,
            help_text = _('The type of email software used by the contact')
            )

    class Meta:
        verbose_name = _('Mailer')
        verbose_name_plural = _('Mailers')

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = microformat_extras
# -*- coding: UTF-8 -*-
"""
Custom Django template filters and template tags for Microformats. 

Copyright (c) 2009 Nicholas H.Tollervey (http://ntoll.org/contact)

All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in
the documentation and/or other materials provided with the
distribution.
* Neither the name of ntoll.org nor the names of its
contributors may be used to endorse or promote products
derived from this software without specific prior written
permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
from django.template import Template, Context
from django import template
from django.template.loader import select_template
from django.conf import settings
from django.utils.translation import ugettext as _
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.forms.fields import email_re, url_re
# We'll be using all the models at some point or other
import microformats.models
import datetime

################################################
# Default templates (over-ridden in settings.py)
################################################
GEO_MICROFORMAT_TEMPLATE = 'geo.html'
HCARD_MICROFORMAT_TEMPLATE = 'hcard.html'
HCAL_MICROFORMAT_TEMPLATE = 'hcal.html'
HLISTING_MICROFORMAT_TEMPLATE = 'hlisting.html'
HREVIEW_MICROFORMAT_TEMPLATE = 'hreview.html'
ADR_MICROFORMAT_TEMPLATE = 'adr.html'
HFEED_MICROFORMAT_TEMPLATE = 'hfeed.html'
HENTRY_MICROFORMAT_TEMPLATE = 'hentry.html'
HNEWS_MICROFORMAT_TEMPLATE = 'hnews.html'

# For registering the templates
register = template.Library()

########################
# Some utility functions
########################

def is_valid_email(email):
    """ 
    Is the string a valid email? 
    
    (We use the regex Django uses to define an email address)
    """
    return True if email_re.match(email) else False

def is_valid_url(url):
    """ 
    Is the string a valid url? 
    
    (We use the regex Django uses to define a URL)
    """
    return True if url_re.match(url) else False

def fragment(value, arg, autoescape=None):
    """
    A generic utility function that takes the value and arg and returns a
    <span> enclosed version.

    The arg should contain the contents of what is to be the class attribute of
    the <span> element.

    For example, where value = "Microsoft" and arg = "org fn" then the result
    will be:

    <span class="org fn">Microsoft</span>

    The function does inspect the value type and attempts to select the most
    appropriate element for display (99.9% of the time this will be a <span>
    element, but for the case of datetime values <abbr> is more appropriate). It
    also checks if the arg is either longitude or latitude and uses the more
    appropriate <abbr> element.

    In the case of a datetime value only the first arg will be used for the
    class, anything else will be assumed to be arguments for strftime. e.g. an
    arg containing "dtstart %a %d %b %y" will result in "dtstart" as the <attr>
    class and the rest as arguments for date/time formatting:

    <abbr class="dtstart" title="2009-05-03">Sun 3 May 2009</abbr>

    Verging of the redundant, this function *does* save typing, incorporates
    some useful heuristics and abstracts the output of individual field values 
    in a neat way.
    """
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    # Make sure we have an arg
    if arg:
        if isinstance(value, datetime.datetime):
            # check we have a datetime field that might need
            # formatting
            args = arg.split()
            klass = args[0]
            if len(args)>1:
                # We're assuming these are strftime formatting instructions
                format = str(' '.join(args[1:]).strip())
            else:
                # Safe default
                format = '%c'
            result = u'<abbr class="%s" title="%s">%s</abbr>' % (
                            esc(klass),
                            esc(value.isoformat()),
                            esc(value.strftime(format))
                        )
        elif arg == 'longitude' or arg == 'latitude' or arg == 'long' or arg == 'lat':
            # Check for geo related fields so we can use the abbr pattern
            if arg == 'latitude' or arg == 'lat':
                klass = u'latitude'
            else:
                klass = u'longitude'
            result = u'<abbr class="%s" title="%s">%s</abbr>' % (
                            esc(klass),
                            esc(value),
                            esc(value)
                        )
        elif is_valid_email(esc(value)):
            # If the field is an email address we need to wrap it in an anchor
            # element
            result = u'<a class="%s" href="mailto:%s">%s</a>'%(
                            esc(arg),
                            esc(value), 
                            esc(value)
                        )
        elif is_valid_url(esc(value)):
            # If the field is a URL we need to wrap it in an anchor element
            result = u'<a class="%s" href="%s">%s</a>'%(
                            esc(arg),
                            esc(value), 
                            esc(value)
                        )
        else:
            # if not just return the raw value in a span with arg as the class
            result = u'<span class="%s">%s</span>' % (esc(arg), esc(value))
    else:
        # We don't have an arg
        result = esc(value)
    return mark_safe(result)

def render_microformat(instance, template_name):
    """
    A generic function that simply takes an instance of a microformat and a
    template name, creates an appropriate context object and returns the rendered
    result.
    """
    template = select_template([template_name,])
    adr_template = getattr(settings, 'ADR_MICROFORMAT_TEMPLATE', False) and settings.ADR_MICROFORMAT_TEMPLATE or ADR_MICROFORMAT_TEMPLATE
    context = Context({
        'instance': instance,
        'adr_microformat_template': adr_template,
        })
    return template.render(context)

@register.filter
def geo(value, arg=None, autoescape=None):
    """
    Formats a value to conform with the geo microformat.

    {{value|geo:"longitude"}}

    or

    {{geo_instance|geo}}

    If rendering a fragment arg to be one of:
    
    ['long', 'lat', 'longitude', 'latitude'] 

    See:

    http://microformats.org/wiki/geo

    geo (pronounced "gee-oh") is a simple format for marking up WGS84 geographic
    coordinates (latitude; longitude), suitable for embedding in HTML or XHTML,
    Atom, RSS, and arbitrary XML. geo is a 1:1 representation of the "geo"
    property in the vCard standard (RFC2426) in HTML, one of several open
    microformat standards. 
    """
    if isinstance(value, datetime.datetime) or isinstance(value, str) or isinstance(value, unicode) or isinstance(value, float) or isinstance(value, int) or isinstance(value, long) or isinstance(value, complex):
        return fragment(value, arg, autoescape)
    else:
        # lets try rendering something with the correct attributes for this
        # microformat
        template_name = getattr(settings, 'GEO_MICROFORMAT_TEMPLATE', False) and settings.GEO_MICROFORMAT_TEMPLATE or GEO_MICROFORMAT_TEMPLATE
        return mark_safe(render_microformat(value, template_name))
geo.needs_autoescape = True

@register.filter
def hcard(value, arg=None, autoescape=None):
    """ 
    Formats a value to conform with the hCard microformat.

    arg to be one of the field names referenced here:

    http://microformats.org/wiki/hcard-cheatsheet

    If an instance of the hCard model is passed as a value then the arg is not
    required and the microformat will be rendered using the hcard template
    specified in settings.HCARD_MICROFORMAT_TEMPLATE (attempts to default to 
    the one found in the templates directory of this application).

    See:

    http://microformats.org/wiki/hcard

    hCard is a simple, open, distributed format for representing people,
    companies, organizations, and places, using a 1:1 representation of vCard
    (RFC2426) properties and values in semantic HTML or XHTML. hCard is one of
    several open microformat standards suitable for embedding in HTML, XHTML,
    Atom, RSS, and arbitrary XML. 
    """
    if isinstance(value, datetime.datetime) or isinstance(value, str) or isinstance(value, unicode) or isinstance(value, float) or isinstance(value, int) or isinstance(value, long) or isinstance(value, complex):
        return fragment(value, arg, autoescape)
    else:
        # lets try rendering something with the correct attributes for this
        # microformat
        template_name = getattr(settings, 'HCARD_MICROFORMAT_TEMPLATE', False) and settings.HCARD_MICROFORMAT_TEMPLATE or HCARD_MICROFORMAT_TEMPLATE
        return mark_safe(render_microformat(value, template_name))
hcard.needs_autoescape = True

@register.filter
def adr(value, arg=None, autoescape=None):
    """ 
    Formats a value to conform with the adr Microformat.

    args to be one of the field names referenced here:

    http://microformats.org/wiki/adr-cheatsheet

    If an instance of the adr model is passed as a value then the arg is not
    required.
    
    See:

    http://microformats.org/wiki/adr

    adr (pronounced "adder"; FAQ: "why 'adr'?") is a simple format for marking
    up address information, suitable for embedding in HTML, XHTML, Atom, RSS,
    and arbitrary XML. adr is a 1:1 representation of the adr property in the
    vCard standard (RFC2426) in HTML, one of several open microformat standards.
    It is also a property of hCard. 
    """
    if isinstance(value, datetime.datetime) or isinstance(value, str) or isinstance(value, unicode) or isinstance(value, float) or isinstance(value, int) or isinstance(value, long) or isinstance(value, complex):
        return fragment(value, arg, autoescape)
    else:
        # lets try rendering something with the correct attributes for this
        # microformat
        template_name = getattr(settings, 'ADR_MICROFORMAT_TEMPLATE', False) and settings.ADR_MICROFORMAT_TEMPLATE or ADR_MICROFORMAT_TEMPLATE
        return mark_safe(render_microformat(value, template_name))
adr.needs_autoescape = True

@register.filter
def hcal(value, arg=None, autoescape=None):
    """
    Formats a value to conform with the hCalendar Microformat. 

    args to be one of the field names referenced here:

    http://microformats.org/wiki/hcalendar-cheatsheet

    If an instance of the hCalendar model is passed as a value then the arg is
    not required.

    Inspired by the markup found here:

    http://microformats.org/code/hcalendar/creator

    For more information see:

    http://microformats.org/wiki/hcalendar

    hCalendar is a simple, open, distributed calendaring and events format,
    based on the iCalendar standard (RFC2445), suitable for embedding in HTML or
    XHTML, Atom, RSS, and arbitrary XML. hCalendar is one of several open
    microformat standards. 
    """
    if isinstance(value, datetime.datetime) or isinstance(value, str) or isinstance(value, unicode) or isinstance(value, float) or isinstance(value, int) or isinstance(value, long) or isinstance(value, complex):
        return fragment(value, arg, autoescape)
    else:
        # lets try rendering something with the correct attributes for this
        # microformat
        template_name = getattr(settings, 'HCAL_MICROFORMAT_TEMPLATE', False) and settings.HCAL_MICROFORMAT_TEMPLATE or HCAL_MICROFORMAT_TEMPLATE
        return mark_safe(render_microformat(value, template_name))
hcal.needs_autoescape = True

@register.filter
def hlisting(value, arg=None, autoescape=None):
    """
    Formats a value to conform with the hListing Microformat
    """
    if isinstance(value, datetime.datetime) or isinstance(value, str) or isinstance(value, unicode) or isinstance(value, float) or isinstance(value, int) or isinstance(value, long) or isinstance(value, complex):
        return fragment(value, arg, autoescape)
    else:
        # lets try rendering something with the correct attributes for this
        # microformat
        template_name = getattr(settings, 'HLISTING_MICROFORMAT_TEMPLATE', False) and settings.HLISTING_MICROFORMAT_TEMPLATE or HLISTING_MICROFORMAT_TEMPLATE
        return mark_safe(render_microformat(value, template_name))
hlisting.needs_autoescape = True

@register.filter
def hreview(value, arg=None, autoescape=None):
    """
    Formats a value to conform with the hReview Microformat
    
    Inspired by the markup found here:

    http://microformats.org/code/hreview/creator
    """
    if isinstance(value, datetime.datetime) or isinstance(value, str) or isinstance(value, unicode) or isinstance(value, float) or isinstance(value, int) or isinstance(value, long) or isinstance(value, complex):
        return fragment(value, arg, autoescape)
    else:
        # lets try rendering something with the correct attributes for this
        # microformat
        template_name = getattr(settings, 'HREVIEW_MICROFORMAT_TEMPLATE', False) and settings.HREVIEW_MICROFORMAT_TEMPLATE or HREVIEW_MICROFORMAT_TEMPLATE
        return mark_safe(render_microformat(value, template_name))
hreview.needs_autoescape = True

@register.filter
def xfn(value, arg=None, autoescape=None):
    """
    Formats an instance of the xfn model to conform with the XFN microformat.

    XFN™ (XHTML Friends Network) is a simple way to represent human
    relationships using hyperlinks. In recent years, blogs and blogrolls have
    become the fastest growing area of the Web. XFN enables web authors to
    indicate their relationship(s) to the people in their blogrolls simply by
    adding a 'rel' attribute to their <a href> tags, e.g.:

    <a href="http://jeff.example.org" rel="friend met">... 
    """
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    if isinstance(value, datetime.datetime) or isinstance(value, str) or isinstance(value, unicode) or isinstance(value, float) or isinstance(value, int) or isinstance(value, long) or isinstance(value, complex):
        return mark_safe(esc(value))
    else:
        # lets try rendering something with the correct attributes for this
        # microformat
        vals = ' '.join(esc(x.value) for x in value.relationships.all())
        result = u'<a href="%s" rel="%s">%s</a>' % (
                            esc(value.url),
                            vals,
                            esc(value.target)
                            )
        return mark_safe(result)
xfn.needs_autoescape = True

@register.filter
def hfeed(value, arg=None, autoescape=None):
    """
    Formats a value to conform with the hFeed Microformat fragment
    
    Inspired by the markup found here:

    http://microformats.org/wiki/hatom-examples
    """
    if isinstance(value, datetime.datetime) or isinstance(value, str) or isinstance(value, unicode) or isinstance(value, float) or isinstance(value, int) or isinstance(value, long) or isinstance(value, complex):
        return fragment(value, arg, autoescape)
    else:
        # lets try rendering something with the correct attributes for this
        # microformat
        template_name = getattr(settings, 'HFEED_MICROFORMAT_TEMPLATE', False) and settings.HFEED_MICROFORMAT_TEMPLATE or HFEED_MICROFORMAT_TEMPLATE
        return mark_safe(render_microformat(value, template_name))
hfeed.needs_autoescape = True

@register.filter
def hentry(value, arg=None, autoescape=None):
    """
    Formats a value to conform with the hEntry Microformat fragment
    
    Inspired by the markup found here:

    http://microformats.org/wiki/hatom-examples
    """
    if isinstance(value, datetime.datetime) or isinstance(value, str) or isinstance(value, unicode) or isinstance(value, float) or isinstance(value, int) or isinstance(value, long) or isinstance(value, complex):
        return fragment(value, arg, autoescape)
    else:
        # lets try rendering something with the correct attributes for this
        # microformat
        template_name = getattr(settings, 'HENTRY_MICROFORMAT_TEMPLATE', False) and settings.HENTRY_MICROFORMAT_TEMPLATE or HENTRY_MICROFORMAT_TEMPLATE
        return mark_safe(render_microformat(value, template_name))
hentry.needs_autoescape = True

@register.filter
def hnews(value, arg=None, autoescape=None):
    """
    Formats a value to conform with the hNews Microformat fragment
    
    Inspired by the markup found here:

    http://microformats.org/wiki/hnews-examples
    """
    if isinstance(value, datetime.datetime) or isinstance(value, str) or isinstance(value, unicode) or isinstance(value, float) or isinstance(value, int) or isinstance(value, long) or isinstance(value, complex):
        return fragment(value, arg, autoescape)
    else:
        # lets try rendering something with the correct attributes for this
        # microformat
        template_name = getattr(settings, 'HNEWS_MICROFORMAT_TEMPLATE', False) and settings.HNEWS_MICROFORMAT_TEMPLATE or HNEWS_MICROFORMAT_TEMPLATE
        return mark_safe(render_microformat(value, template_name))
hentry.needs_autoescape = True
########NEW FILE########
__FILENAME__ = tests
# -*- coding: UTF-8 -*-
"""
Unit tests are found in the unit_tests module. This file is simply to hook into
the Django test framework. 

Author: Nicholas H.Tollervey

"""
from unit_tests.test_views import *
from unit_tests.test_models import *
from unit_tests.test_forms import *
from unit_tests.test_templatetags import *

########NEW FILE########
__FILENAME__ = test_forms
# -*- coding: UTF-8 -*-
"""
Forms tests for microformats 

Author: Nicholas H.Tollervey

"""
# python
import datetime

# django
from django.test.client import Client
from django.test import TestCase

# project
from microformats.forms import GeoForm, hCardForm, AdrForm, EmailForm, TelForm

class FormTestCase(TestCase):
        """
        Testing Forms 
        """
        # Reference fixtures here
        fixtures = []

        def test_geo(self):
            """
            Makes sure the validation for longitude and latitude works correctly
            """
            # Safe case
            data = {
                    'latitude': '37.408183',
                    'latitude_description': u'N 37° 24.491',
                    'longitude': '-122.13855',
                    'longitude_description': u'W 122° 08.313'
                    }
            f = GeoForm(data)
            self.assertEquals(True, f.is_valid())
            # Remove the non required fields
            data['latitude_description'] = ''
            data['longitude_description'] = ''
            f = GeoForm(data)
            self.assertEquals(True, f.is_valid())
            # Boundry check latitude
            # Upper
            data['latitude'] = '90'
            f = GeoForm(data)
            self.assertEquals(True, f.is_valid())
            data['latitude'] = '90.000001'
            f = GeoForm(data)
            self.assertEquals(False, f.is_valid())
            # Lower
            data['latitude'] = '-90'
            f = GeoForm(data)
            self.assertEquals(True, f.is_valid())
            data['latitude'] = '-90.000001'
            f = GeoForm(data)
            self.assertEquals(False, f.is_valid())
            data['latitude'] = '37.408183'
            # Boundry check for longitude
            # Upper
            data['longitude'] = '180'
            f = GeoForm(data)
            self.assertEquals(True, f.is_valid())
            data['longitude'] = '180.000001'
            f = GeoForm(data)
            self.assertEquals(False, f.is_valid())
            # Lower
            data['longitude'] = '-180'
            f = GeoForm(data)
            self.assertEquals(True, f.is_valid())
            data['longitude'] = '-180.000001'
            f = GeoForm(data)
            self.assertEquals(False, f.is_valid())
            data['longitude'] = '-122.13855'
            # Make sure required fields are correct
            data['latitude'] = ''
            f = GeoForm(data)
            self.assertEquals(False, f.is_valid())
            data['latitude'] = '37.408183'
            data['longitude'] = ''
            f = GeoForm(data)
            self.assertEquals(False, f.is_valid())

        def test_hcard(self):
            """
            Makes sure if long or lat are supplied then so should the other, and
            that it validates something useful for the fn
            """
            # Long and lat
            data = {
                    'given_name': 'John',
                    'longitude': '-122.13855'
                    }
            f = hCardForm(data)
            # No latitude
            self.assertEquals(False, f.is_valid())
            self.assertEquals(1, len(f.errors['longitude']))
            data['longitude'] = ''
            data['latitude'] = '37.408183'
            f = hCardForm(data)
            # No longitude
            self.assertEquals(False, f.is_valid())
            self.assertEquals(1, len(f.errors['latitude']))
            data['longitude'] = '-122.13855'
            # No fn related data
            data['given_name'] = ''
            f = hCardForm(data)
            self.assertEquals(False, f.is_valid())
            self.assertEquals(1, len(f.errors['__all__']))
            # given name is valid
            data['given_name'] = 'John'
            f = hCardForm(data)
            self.assertEquals(True, f.is_valid())
            # nickname is valid
            data['given_name'] = ''
            data['nickname'] = 'John'
            f = hCardForm(data)
            self.assertEquals(True, f.is_valid())
            # as is org
            data['nickname'] = ''
            data['org'] = 'Acme Corp.'
            f = hCardForm(data)
            self.assertEquals(True, f.is_valid())

        def test_adr(self):
            """
            Makes sure the types are rendered as an unordered list of checkboxes
            """
            f = AdrForm()
            p = f.as_p()
            self.assertEquals(True, p.find('type="checkbox" name="types"')>-1)

        def test_email(self):
            """
            Makes sure the types are rendered as an unordered list of checkboxes
            """
            f = EmailForm()
            p = f.as_p()
            self.assertEquals(True, p.find('type="checkbox" name="types"')>-1)

        def test_tel(self):
            """
            Makes sure the types are rendered as an unordered list of checkboxes
            """
            f = TelForm()
            p = f.as_p()
            self.assertEquals(True, p.find('type="checkbox" name="types"')>-1)


########NEW FILE########
__FILENAME__ = test_models
# -*- coding: UTF-8 -*-
"""
Model tests for Microformats 

Author: Nicholas H.Tollervey

"""
# python
import datetime

# django
from django.test.client import Client
from django.test import TestCase
from django.contrib.auth.models import User

# project
from microformats.models import *

class ModelTestCase(TestCase):
        """
        Testing Models 
        """
        # Reference fixtures here
        fixtures = []

        def test_geo(self):
            """
            Make sure the string representation of the geolocation looks correct
            """
            g = geo()
            g.latitude = 37.408183
            g.longitude = -122.13855
            g.latitude_description = 'N 37 24.491'
            g.longitude_description = 'W 122 08.313'
            g.save()
            self.assertEquals('lat 37.408183 long -122.13855', g.__unicode__())

        def test_hCardComplete(self):
            """
            Check that the n() and fn() methods return the correct values
            """
            hc = hCardComplete()
            hc.honorific_prefix = 'Mr'
            hc.given_name = 'Joe'
            hc.additional_name = 'Arthur'
            hc.family_name = 'Blogs'
            hc.honorific_suffix = 'PhD'
            hc.save()
            self.assertEquals('Mr Joe Arthur Blogs PhD', hc.n())
            # Make sure we get a useful name back *NOT* "Mr PhD"
            hc.given_name = ''
            hc.additional_name = ''
            hc.family_name = ''
            hc.save()
            self.assertEquals('', hc.n())
            # Make sure fn() returns the same as n() if is_org isn't passed
            hc.given_name = 'Joe'
            hc.additional_name = 'Arthur'
            hc.family_name = 'Blogs'
            self.assertEquals('Mr Joe Arthur Blogs PhD', hc.fn())
            # Make sure we don't let whitespace or empty into the result of n()
            hc.honorific_prefix = """       
            """ # some spaces, tabs and a newline
            hc.honorific_suffix = '' # empty
            hc.save()
            self.assertEquals('Joe Arthur Blogs', hc.n())
            # Lets add an organization to the hCard
            o = org()
            o.hcard = hc
            o.name = 'Acme Corp.'
            o.unit = 'Widget Development'
            o.primary = True
            o.save()
            self.assertEquals('Widget Development, Acme Corp.',
                    hc.fn(is_org=True))
            o.unit = ''
            o.save()
            self.assertEquals('Acme Corp.', hc.fn(is_org=True))
            o.primary = False
            o.save()
            # If we don't have an organization by do have some name information
            # then fall back on that
            self.assertEquals('Joe Arthur Blogs', hc.fn(is_org=True))
            o2 = org()
            o2.hcard = hc
            o2.name = 'Mega Corp.'
            o2.unit = 'Sales'
            o2.primary = True
            o2.save()
            o.primary = True
            o.save()
            # check that two organizations marked as primary doesn't result in
            # an error
            self.assertEquals('Acme Corp.', hc.fn(is_org=True))
            # Check that despite being associated with an organization fn()
            # doesn't return it if is_org isn't passed
            self.assertEquals('Joe Arthur Blogs', hc.fn())
            # Finally, make sure we get something sensible if nothing else is
            # available for fn() to create something
            # No name information so fall back on organization
            hc.given_name = ''
            hc.additional_name = ''
            hc.family_name = ''
            self.assertEquals('Acme Corp.', hc.fn())
            o.delete()
            o2.delete()
            self.assertEquals('None', hc.fn())

        def test_adr(self):
            """ 
            Make sure the string representation of the address looks correct
            """
            a = adr()
            a.street_address = 'Flat 29a'
            a.extended_address = '123 Somewhere Street'
            a.locality = 'Townsville'
            a.region = 'Countyshire'
            a.country_name = 'GB'
            a.postal_code = 'CS23 6YT'
            a.post_office_box = 'PO Box 6754'
            expected = 'Flat 29a, 123 Somewhere Street, Townsville,'\
                    ' Countyshire, United Kingdom, CS23 6YT,'\
                    ' PO Box 6754'
            self.assertEquals(expected, a.__unicode__())
            # Lets check we ignore whitespace and empty fields
            a.post_office_box = """    
                """ # whitespace of various sorts
            a.extended_address = '' # empty
            expected = 'Flat 29a, Townsville, Countyshire, United Kingdom,'\
                    ' CS23 6YT'
            self.assertEquals(expected, a.__unicode__())

        def test_org(self):
            """ 
            Make sure the string representation of the organization looks correct
            """
            hc = hCardComplete()
            hc.given_name = 'test'
            hc.save()
            o = org()
            o.hcard = hc
            o.name = 'Acme Corp.'
            o.unit = 'Widget Development'
            o.primary = True
            o.save()
            self.assertEquals('Widget Development, Acme Corp.', o.__unicode__())
            o.unit = ''
            o.save()
            self.assertEquals('Acme Corp.', o.__unicode__())

        def test_hCalendar(self):
            """
            Make sure the string representation of the hCalendar looks correct
            """
            hc = hCalendar()
            hc.summary = 'This is a summary'
            hc.dtstart = datetime.datetime(2009, 4, 11, 13, 30)
            hc.save()
            expected = hc.dtstart.strftime('%a %b %d %Y, %I:%M%p')+' - This is'\
                    ' a summary'
            self.assertEquals(expected, hc.__unicode__())

        def test_xfn(self):
            """
            Make sure the string representation of the XFN looks correct
            """
            # Set things up
            u = User.objects.create_user('john', 'john@smith.com', 'password')
            URL = 'http://twitter.com/ntoll'
            tgt = 'Nicholas Tollervey'
            x = xfn()
            x.source = u
            x.target = tgt 
            x.save()
            xfnv1 = xfn_values.objects.get(value='friend')
            xfnv2 = xfn_values.objects.get(value='met')
            xfnv3 = xfn_values.objects.get(value='colleague')
            x.relationships.add(xfnv1)
            x.relationships.add(xfnv2)
            x.relationships.add(xfnv3)
            x.save()
            # default case
            expected = 'Nicholas Tollervey (Colleague, Friend, Met)'
            self.assertEquals(expected, x.__unicode__())
            # with valid target but no relationships
            x.relationships.clear()
            x.save()
            expected = 'Nicholas Tollervey'
            self.assertEquals(expected, x.__unicode__())

        def test_hfeed(self):
            """
            Make sure the string representation of teh hFeed looks correct
            """
            # Set things up
            f = hFeed()
            f.save()
            self.assertEqual(u'Uncategorized feed', f.__unicode__())
            f.category = u'Some, tags'
            f.save()
            self.assertEqual(u'Some, tags', f.__unicode__())


########NEW FILE########
__FILENAME__ = test_templatetags
# -*- coding: UTF-8 -*-
"""
Custom templatetags tests for microformats 

Author: Nicholas H.Tollervey

"""
# python
import datetime
import codecs
import os

# django
from django.test.client import Client
from django.test import TestCase
from django.template import Context, Template
from django.template.loader import get_template
from django.contrib.auth.models import User

# project
import microformats.models 
from microformats.templatetags.microformat_extras import *

class TemplateTagsTestCase(TestCase):
        """
        Testing custom templatetags 
        """
        # Reference fixtures here
        fixtures = []

        def test_geo(self):
            """
            Make sure we can render the geo microformat correctly 
            """
            # Safe case with an instance
            g = microformats.models.geo()
            g.latitude = 37.408183
            g.latitude_description = 'N 37° 24.491'
            g.longitude = -122.13855
            g.longitude_description = 'W 122° 08.313'
            g.save()
            # With no arg
            result = geo(g, autoescape=True)
            expected = u'''\n<div class="geo">\n    <abbr class="latitude" title="37.408183">\n    N 37\xb0 24.491\n    </abbr>&nbsp;\n    <abbr class="longitude" title="-122.13855">\n    W 122\xb0 08.313\n    </abbr>\n</div>\n'''
            self.assertEquals(expected, result) 
            # With an arg
            result = geo(g, arg="Geo", autoescape=True)
            expected = u'\n<div class="geo">\n    <abbr class="latitude" title="37.408183">\n    N 37\xb0 24.491\n    </abbr>&nbsp;\n    <abbr class="longitude" title="-122.13855">\n    W 122\xb0 08.313\n    </abbr>\n</div>\n'
            self.assertEquals(expected, result) 
            # An instance without any description fields
            g.latitude_description = ''
            g.longitude_description = ''
            g.save()
            result = geo(g, autoescape=True)
            expected = u'\n<div class="geo">\n    <abbr class="latitude" title="37.408183">\n    37.408183\n    </abbr>&nbsp;\n    <abbr class="longitude" title="-122.13855">\n    -122.13855\n    </abbr>\n</div>\n'
            self.assertEquals(expected, result) 
            # Test Geocode fragments
            result = geo(g.latitude, arg="latitude", autoescape=True)
            expected = u'<abbr class="latitude" title="37.408183">37.408183</abbr>'
            self.assertEquals(expected, result) 
            result = geo(g.longitude, arg="longitude", autoescape=True)
            expected = u'<abbr class="longitude" title="-122.13855">-122.13855</abbr>'
            self.assertEquals(expected, result) 

        def test_fragment(self):
            """
            The fragment function being exercised
            """
            # Test that an unknown arg results in the return of the raw value in
            # an appropriatly formatted span

            # Generic call results in the span
            result = fragment("foo", arg="bar", autoescape=True)
            expected = u'<span class="bar">foo</span>'
            self.assertEquals(expected, result) 

            # multiple classes in the arg result in the correct class
            result = fragment("foo", arg="bar baz", autoescape=True)
            expected = u'<span class="bar baz">foo</span>'
            self.assertEquals(expected, result) 

            # override the formatting of date-time data
            dt = datetime.datetime.today()
            result = fragment(dt, arg="dtstart %a %b %d %Y", autoescape=True)
            expected = u'<abbr class="dtstart" title="%s">%s</abbr>' % (
                            dt.isoformat(),
                            dt.strftime('%a %b %d %Y')
                            )
            self.assertEquals(expected, result)
            result = fragment(dt, arg="dtstart right now", autoescape=True)
            expected = u'<abbr class="dtstart" title="%s">right now</abbr>' % (
                            dt.isoformat(),
                            )
            self.assertEquals(expected, result)
            result = fragment(dt, arg="dtstart", autoescape=True)
            expected = u'<abbr class="dtstart" title="%s">%s</abbr>' % (
                            dt.isoformat(),
                            dt.strftime('%c')
                            )
            self.assertEquals(expected, result)

            # Check for geo related abbr pattern
            result = fragment(37.408183, arg="latitude", autoescape=True)
            expected = u'<abbr class="latitude" title="37.408183">37.408183</abbr>'
            self.assertEquals(expected, result)

            result = fragment(37.408183, arg="lat", autoescape=True)
            self.assertEquals(expected, result)

            result = fragment(-122.13855, arg="longitude", autoescape=True)
            expected = u'<abbr class="longitude" title="-122.13855">-122.13855</abbr>'
            self.assertEquals(expected, result)

            result = fragment(-122.13855, arg="long", autoescape=True)
            self.assertEquals(expected, result)

            # Check for email address anchor element (this depends on the value
            # of the field *NOT* the name of the class passed as an arg)
            result = fragment('joe@blogs.com', arg='foo', autoescape=True)
            expected = u'<a class="foo" href="mailto:joe@blogs.com">joe@blogs.com</a>'
            self.assertEquals(expected, result)

            # Check for URL anchor element (works in the same way as email but
            # with a different regex)
            result = fragment('http://foo.com', arg='bar', autoescape=True)
            expected = u'<a class="bar" href="http://foo.com">http://foo.com</a>'
            self.assertEquals(expected, result)

            # Lets make sure we can handle ints and floats
            result = fragment(1.234, arg='foo', autoescape=True)
            expected = u'<span class="foo">1.234</span>'
            self.assertEquals(expected, result)

            result = fragment(1234, arg='foo', autoescape=True)
            expected = u'<span class="foo">1234</span>'
            self.assertEquals(expected, result)

        def test_non_microformat_model_rendering(self):
            """
            Make sure we can render objects that are not microformat models from
            this application but that have attributes that conform to the
            microformat naming conventions.
            """
            # Lets just test this with a dict 
            hc = dict()
            hc['honorific_prefix'] = 'Mr'
            hc['given_name'] = 'Joe'
            hc['additional_name'] = 'Arthur'
            hc['family_name'] = 'Blogs'
            hc['honorific_suffix'] = 'PhD'
            hc['url'] = 'http://acme.com/'
            hc['email_work'] = 'joe.blogs@acme.com'
            hc['email_home'] = 'joe.blogs@home-isp.com'
            hc['tel_work'] = '+44(0)1234 567876'
            hc['tel_home'] = '+44(0)1543 234345'
            hc['street_address'] = '5445 N. 27th Street'
            hc['extended_address'] = ''
            hc['locality'] = 'Milwaukee'
            hc['region'] = 'WI'
            hc['country_name'] = 'US'
            hc['postal_code'] = '53209'
            hc['title'] = 'Vice President'
            hc['org'] = 'Acme Corp.'
            result = hcard(hc, autoescape=True)
            expected = u'\n<div id="hcard_" class="vcard">\n    <div class="fn n">\n        <a href="http://acme.com/" class="url">\n        \n            <span class="honorific-prefix">Mr</span>\n            <span class="given-name">Joe</span>\n            <span class="additional-name">Arthur</span>\n            <span class="family-name">Blogs</span>\n            <span class="honorific-suffix">PhD</span>\n        \n        </a>\n    </div>\n    \n    <span class="title">Vice President</span>\n    \n    <div class="org">Acme Corp.</div>\n    \n    \n    <a class="email" href="mailto:joe.blogs@acme.com">joe.blogs@acme.com</a> [work]<br/> \n    <a class="email" href="mailto:joe.blogs@home-isp.com">joe.blogs@home-isp.com</a> [home]<br/> \n    \n<div class="adr">\n    <div class="street-address">5445 N. 27th Street</div>\n    \n    <span class="locality">Milwaukee</span>&nbsp;\n    <span class="region">WI</span>&nbsp;\n    <span class="postal-code">53209</span>&nbsp;\n    <span class="country-name">US</span>\n</div>\n\n    <div class="tel"><span class="value">+44(0)1234 567876</span> [<abbr class="type" title="work">work</abbr>]</div>\n    <div class="tel"><span class="value">+44(0)1543 234345</span> [<abbr class="type" title="home">home</abbr>]</div>\n    \n</div>\n'
            self.assertEquals(expected, result)

        def test_hcard(self):
            """
            Make sure we have a pass-able means of rendering an hCard
            """
            # Start with a happy case
            hc = microformats.models.hCard()
            hc.honorific_prefix = 'Mr'
            hc.given_name = 'Joe'
            hc.additional_name = 'Arthur'
            hc.family_name = 'Blogs'
            hc.honorific_suffix = 'PhD'
            hc.url = 'http://acme.com/'
            hc.email_work = 'joe.blogs@acme.com'
            hc.email_home = 'joe.blogs@home-isp.com'
            hc.tel_work = '+44(0)1234 567876'
            hc.tel_home = '+44(0)1543 234345'
            hc.street_address = '5445 N. 27th Street'
            hc.extended_address = ''
            hc.locality = 'Milwaukee'
            hc.region = 'WI'
            hc.country_name = 'US'
            hc.postal_code = '53209'
            hc.title = 'Vice President'
            hc.org = 'Acme Corp.'
            hc.save()
            result = hcard(hc, autoescape=True)
            expected = u'\n<div id="hcard_1" class="vcard">\n    <div class="fn n">\n        <a href="http://acme.com/" class="url">\n        \n            <span class="honorific-prefix">Mr</span>\n            <span class="given-name">Joe</span>\n            <span class="additional-name">Arthur</span>\n            <span class="family-name">Blogs</span>\n            <span class="honorific-suffix">PhD</span>\n        \n        </a>\n    </div>\n    \n    <span class="title">Vice President</span>\n    \n    <div class="org">Acme Corp.</div>\n    \n    \n    <a class="email" href="mailto:joe.blogs@acme.com">joe.blogs@acme.com</a> [work]<br/> \n    <a class="email" href="mailto:joe.blogs@home-isp.com">joe.blogs@home-isp.com</a> [home]<br/> \n    \n<div class="adr">\n    <div class="street-address">5445 N. 27th Street</div>\n    \n    <span class="locality">Milwaukee</span>&nbsp;\n    <span class="region">WI</span>&nbsp;\n    <span class="postal-code">53209</span>&nbsp;\n    <span class="country-name">United States</span>\n</div>\n\n    <div class="tel"><span class="value">+44(0)1234 567876</span> [<abbr class="type" title="work">work</abbr>]</div>\n    <div class="tel"><span class="value">+44(0)1543 234345</span> [<abbr class="type" title="home">home</abbr>]</div>\n    \n</div>\n'
            self.assertEquals(expected, result)
            # Lets make sure we can get a valid hCard when it is for an
            # organisation
            hc.honorific_prefix = ''
            hc.given_name = ''
            hc.additional_name = ''
            hc.family_name = ''
            hc.honorific_suffix = ''
            hc.save()
            result = hcard(hc, autoescape=True)
            expected = u'\n<div id="hcard_1" class="vcard">\n    <div class="fn n">\n        <a href="http://acme.com/" class="url">\n        \n        <span class="org">Acme Corp.</span>\n        \n        </a>\n    </div>\n    \n    <a class="email" href="mailto:joe.blogs@acme.com">joe.blogs@acme.com</a> [work]<br/> \n    <a class="email" href="mailto:joe.blogs@home-isp.com">joe.blogs@home-isp.com</a> [home]<br/> \n    \n<div class="adr">\n    <div class="street-address">5445 N. 27th Street</div>\n    \n    <span class="locality">Milwaukee</span>&nbsp;\n    <span class="region">WI</span>&nbsp;\n    <span class="postal-code">53209</span>&nbsp;\n    <span class="country-name">United States</span>\n</div>\n\n    <div class="tel"><span class="value">+44(0)1234 567876</span> [<abbr class="type" title="work">work</abbr>]</div>\n    <div class="tel"><span class="value">+44(0)1543 234345</span> [<abbr class="type" title="home">home</abbr>]</div>\n    \n</div>\n'
            self.assertEquals(expected, result)
            # No address, org, url and email and minimum telephone information
            hc.url = ''
            hc.email_work = ''
            hc.email_home = ''
            hc.street_address = ''
            hc.extended_address = ''
            hc.locality = ''
            hc.region = ''
            hc.country_name = ''
            hc.postal_code = ''
            hc.title = ''
            hc.org = ''
            hc.url = ''
            hc.honorific_prefix = 'Mr'
            hc.given_name = 'Joe'
            hc.additional_name = 'Arthur'
            hc.family_name = 'Blogs'
            hc.honorific_suffix = 'PhD'
            hc.save()
            result = hcard(hc, autoescape=True)
            expected = u'\n<div id="hcard_1" class="vcard">\n    <div class="fn n">\n        \n        \n            <span class="honorific-prefix">Mr</span>\n            <span class="given-name">Joe</span>\n            <span class="additional-name">Arthur</span>\n            <span class="family-name">Blogs</span>\n            <span class="honorific-suffix">PhD</span>\n        \n        \n    </div>\n    \n    \n    \n    \n     \n     \n    \n<div class="adr">\n    \n    \n    \n    \n    \n    \n</div>\n\n    <div class="tel"><span class="value">+44(0)1234 567876</span> [<abbr class="type" title="work">work</abbr>]</div>\n    <div class="tel"><span class="value">+44(0)1543 234345</span> [<abbr class="type" title="home">home</abbr>]</div>\n    \n</div>\n'
            self.assertEquals(expected, result)
            # Absolute minimum
            hc.honorific_prefix = ''
            hc.additional_name = ''
            hc.honorific_suffix = ''
	    hc.tel_work = ''
	    hc.tel_home = ''
	    hc.save()
            result = hcard(hc, autoescape=True)
            expected = u'\n<div id="hcard_1" class="vcard">\n    <div class="fn n">\n        \n        \n            \n            <span class="given-name">Joe</span>\n            \n            <span class="family-name">Blogs</span>\n            \n        \n        \n    </div>\n    \n    \n    \n    \n     \n     \n    \n<div class="adr">\n    \n    \n    \n    \n    \n    \n</div>\n\n    \n    \n    \n</div>\n'
            self.assertEquals(expected, result)

        def test_adr(self):
            """
            Lets make sure we get a good address with or without types
            """
            # With type
            at = microformats.models.adr_type.objects.get(id=5)
            a = microformats.models.adr()
            a.street_address = 'Flat 29a'
            a.extended_address = '123 Somewhere Street'
            a.locality = 'Townsville'
            a.region = 'Countyshire'
            a.country_name = 'GB'
            a.postal_code = 'CS23 6YT'
            a.save()
            a.types.add(at)
            a.save()
            result = adr(a, autoescape=True)
            expected = u'\n<div class="adr">\n    <div class="street-address">Flat 29a</div>\n    <div class="extended-address">123 Somewhere Street</div>\n    <span class="locality">Townsville</span>&nbsp;\n    <span class="region">Countyshire</span>&nbsp;\n    <span class="postal-code">CS23 6YT</span>&nbsp;\n    <span class="country-name">United Kingdom</span>\n</div>\n'
            self.assertEquals(expected, result)
            # Without type
            a.types.clear()
            a.save()
            result = adr(a, autoescape=True)
            expected = u'\n<div class="adr">\n    <div class="street-address">Flat 29a</div>\n    <div class="extended-address">123 Somewhere Street</div>\n    <span class="locality">Townsville</span>&nbsp;\n    <span class="region">Countyshire</span>&nbsp;\n    <span class="postal-code">CS23 6YT</span>&nbsp;\n    <span class="country-name">United Kingdom</span>\n</div>\n'
            self.assertEquals(expected, result)

        def test_hcal(self):
            """
            Check we get the expected results for an hCalendar
            """
            hc = microformats.models.hCalendar()
            hc.summary = 'Important Meeting'
            hc.location = 'BBC in London'
            hc.url = 'http://www.bbc.co.uk/'
            hc.dtstart = datetime.datetime(2009, 4, 11, 13, 30)
            hc.dtend = datetime.datetime(2009, 4, 11, 15, 30)
            hc.description = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.'
            hc.street_address = 'Broadcasting House'
            hc.extended_address = 'Portland Place'
            hc.locality = 'London'
            hc.region = ''
            hc.country_name = 'GB'
            hc.postal_code = 'W1A 1AA'
            hc.save()
            hc.save()
            result = hcal(hc, autoescape=True)
            expected = u'\n<div id="hcalendar_1" class="vevent">\n    <a href="http://www.bbc.co.uk/" class="url">\n        \n        <abbr title="2009-04-11T13:30:00" class="dtstart">Sat 11 Apr 2009 1:30 p.m.</abbr>\n        \n        \n            &nbsp;-&nbsp;\n            \n            <abbr title="2009-04-11T15:30:00" class="dtend">All day event</abbr>\n            \n        \n        :&nbsp;\n        <span class="summary">Important Meeting</span>\n         at <span class="location">BBC in London</span>\n    </a>\n    \n<div class="adr">\n    <div class="street-address">Broadcasting House</div>\n    <div class="extended-address">Portland Place</div>\n    <span class="locality">London</span>&nbsp;\n    \n    <span class="postal-code">W1A 1AA</span>&nbsp;\n    <span class="country-name">United Kingdom</span>\n</div>\n\n    <p class="description">Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.</p>    \n</div>\n'
            self.assertEquals(expected, result)
            # Make sure things render correctly *if* all_day_event = True
            hc.all_day_event = True
            hc.save()
            result = hcal(hc, autoescape=True)
            expected = u'\n<div id="hcalendar_1" class="vevent">\n    <a href="http://www.bbc.co.uk/" class="url">\n        \n        <abbr title="2009-04-11T13:30:00" class="dtstart">Sat 11 Apr 2009</abbr>\n        \n        \n            &nbsp;-&nbsp;\n            \n            <abbr title="2009-04-11T15:30:00" class="dtend">All day event</abbr>\n            \n        \n        :&nbsp;\n        <span class="summary">Important Meeting</span>\n         at <span class="location">BBC in London</span>\n    </a>\n    \n<div class="adr">\n    <div class="street-address">Broadcasting House</div>\n    <div class="extended-address">Portland Place</div>\n    <span class="locality">London</span>&nbsp;\n    \n    <span class="postal-code">W1A 1AA</span>&nbsp;\n    <span class="country-name">United Kingdom</span>\n</div>\n\n    <p class="description">Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.</p>    \n</div>\n'
            self.assertEquals(expected, result)
            hc.all_day_event = False
            hc.save()
            # Lets cut things down to the essentials with a different end date
            hc.url = ''
            hc.location = ''
            hc.description = ''
            hc.street_address = ''
            hc.extended_address = ''
            hc.locality = ''
            hc.region = ''
            hc.country_name = ''
            hc.postal_code = ''
            hc.dtend = datetime.datetime(2009, 4, 15, 15, 30)
            hc.save()
            result = hcal(hc, autoescape=True)
            expected = u'\n<div id="hcalendar_1" class="vevent">\n    \n        \n        <abbr title="2009-04-11T13:30:00" class="dtstart">Sat 11 Apr 2009 1:30 p.m.</abbr>\n        \n        \n            &nbsp;-&nbsp;\n            \n            <abbr title="2009-04-15T15:30:00" class="dtend">3:30 p.m.</abbr>\n            \n        \n        :&nbsp;\n        <span class="summary">Important Meeting</span>\n        \n    \n    \n<div class="adr">\n    \n    \n    \n    \n    \n    \n</div>\n\n        \n</div>\n'
            self.assertEquals(expected, result)
            # Absolute minimum
            hc.dtend = None
            hc.dtstart = datetime.datetime(2009, 4, 15)
            result = hcal(hc, autoescape=True)
            # We probably want to separate the date and time of dtstart and
            # dtend so we don't default to midnight... ToDo: Fix date/time
            expected = u'\n<div id="hcalendar_1" class="vevent">\n    \n        \n        <abbr title="2009-04-15T00:00:00" class="dtstart">Wed 15 Apr 2009 midnight</abbr>\n        \n        \n        :&nbsp;\n        <span class="summary">Important Meeting</span>\n        \n    \n    \n<div class="adr">\n    \n    \n    \n    \n    \n    \n</div>\n\n        \n</div>\n'
            self.assertEquals(expected, result)

        def test_hlisting(self):
            """
            Check we get the expected results for an hListing
            """
            listing = microformats.models.hListing()
            listing.listing_action = "sell"
            listing.summary = "Pony requires a good home"
            listing.description = "A young pony who answers to the name Django"\
                " requires a new home having outgrown his current host. Easy"\
                " going and fun to play with Django also provides rainbow"\
                " manure that is sure to help the garden grow."
            listing.lister_fn = "John Doe"
            listing.lister_email = "john.doe@isp.net"
            listing.lister_url = "http://isp.com/django_the_pony"
            listing.lister_tel = "+44(0) 1234 567456"
            listing.dtlisted = datetime.datetime(2009, 5, 6)
            listing.dtexpired = datetime.datetime(2009, 8, 19)
            listing.price = "£2500 ono"
            listing.item_fn = "Django the Pony"
            listing.item_url = "http://djangoproject.com/"
            listing.locality = "Brighton"
            listing.country_name = "GB"
            listing.save()
            result = hlisting(listing, autoescape=True)
            expected = u'\n<div class="hlisting">\n    <p>\n        <span class="item vcard">\n        <a href="http://djangoproject.com/" class="url">\n            <span class="fn">Django the Pony</span>\n        </a>\n        \n        <span class="location">\n        \n<div class="adr">\n    \n    \n    <span class="locality">Brighton</span>&nbsp;\n    \n    \n    <span class="country-name">United Kingdom</span>\n</div>\n\n        </span>\n        \n        </span>\n        <span class="sell">To sell</span>\n        (<abbr class="dtlisted" title="2009-05-06T00:00:00">Wed 06 May 2009</abbr>)\n        <p class="summary">Pony requires a good home</p>\n        <p class="description">A young pony who answers to the name Django requires a new home having outgrown his current host. Easy going and fun to play with Django also provides rainbow manure that is sure to help the garden grow.</p>\n        \n        <p>Available from: <abbr class="dtexpired" title="2009-08-19T00:00:00">Wed 19 Aug 2009</abbr></p>\n        \n        \n        <p>Price: <span class="price">\xa32500 ono</span></p>\n        \n        <div class="lister vcard">\n            <p>For more information, please contact\n            <a href="http://isp.com/django_the_pony" class="url">\n                <span class="fn">John Doe</span>\n            </a>\n            <a href="mailto:john.doe@isp.net" class="email">john.doe@isp.net</a>\n            <span class="tel"><span class="value">+44(0) 1234 567456</span></span>\n            </p>\n        </div>\n    </p>\n</div>\n'
            self.assertEquals(expected, result)
            # Lets cut things down to the minimum
            listing.summary = ""
            listing.description = "A young pony who answers to the name Django"\
                " requires a new home having outgrown his current host. Easy"\
                " going and fun to play with Django also provides rainbow"\
                " manure that is sure to help the garden grow."
            listing.lister_fn = "John Doe"
            listing.lister_email = ""
            listing.lister_url = ""
            listing.lister_tel = ""
            listing.dtlisted = None 
            listing.dtexpired = None
            listing.price = ""
            listing.item_fn = "Django the Pony"
            listing.item_url = ""
            listing.locality = ""
            listing.country_name = ""
            listing.save()
            result = hlisting(listing, autoescape=True)
            expected=u'\n<div class="hlisting">\n    <p>\n        <span class="item vcard">\n        \n            <span class="fn">Django the Pony</span>\n        \n        \n        </span>\n        <span class="sell">To sell</span>\n        \n        \n        <p class="description">A young pony who answers to the name Django requires a new home having outgrown his current host. Easy going and fun to play with Django also provides rainbow manure that is sure to help the garden grow.</p>\n        \n        \n        <div class="lister vcard">\n            <p>For more information, please contact\n            \n                <span class="fn">John Doe</span>\n            \n            \n            \n            </p>\n        </div>\n    </p>\n</div>\n'
            self.assertEquals(expected, result)

        def test_hreview(self):
            """
            Check we get the expected results for an hReview
            """
            rev1 = microformats.models.hReview()
            rev1.summary="Acme's new services rock!"
            rev1.type='business'
            rev1.description='Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat.'
            rev1.rating=4
            rev1.dtreviewed=datetime.datetime(2009,4,10)
            rev1.reviewer='John Smith'
            rev1.fn='Acme Corp'
            rev1.url='http://acme.com'
            rev1.tel='+44(0)1234 567456'
            rev1.street_address = '5445 N. 27th Street'
            rev1.extended_address = ''
            rev1.locality = 'Milwaukee'
            rev1.region = 'WI'
            rev1.country_name = 'US'
            rev1.postal_code = '53209'
            rev1.save()
            rev2 = microformats.models.hReview()
            rev2.summary = 'A phenomenal tuba recital'
            rev2.description = 'Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat.'
            rev2.rating=5
            rev2.type='event'
            rev2.reviewer='John Doe'
            rev2.fn='John Fletcher - One man and his Tuba'
            rev2.url='http://www.johnfletcher-tuba.co.uk/'
            rev2.dtstart = datetime.datetime(1987, 10, 3, 19, 30)
            rev2.street_address = 'The Pro Arte Theatre'
            rev2.locality = 'London'
            rev2.save()
            rev3 = microformats.models.hReview()
            rev3.summary = 'Latest Star-Wars is Sucko-Barfo'
            rev3.description = 'Claritas est etiam processus dynamicus, qui sequitur mutationem consuetudium lectorum. Mirum est notare quam littera gothica, quam nunc putamus parum claram, anteposuerit litterarum formas humanitatis per seacula quarta decima et quinta decima. Eodem modo typi, qui nunc nobis videntur parum clari, fiant sollemnes in futurum.'
            rev3.rating=1
            rev3.type='film'
            rev3.reviewer='Barry Norman'
            rev3.fn='Star Wars - Revenge of the Sith'
            rev3.url='http://www.starwars.com/movies/episode-iii/'
            rev3.save()
            # Test for a review concerning something represented by an hCard
            result = hreview(rev1, autoescape=True) 
            expected = u'\n<div class="hreview">\n    <strong class="summary">Acme&#39;s new services rock!</strong>\n    <abbr class="type" title="business"> Business</abbr> Review\n    <br/>\n    \n    <abbr title="" class="dtreviewed">Fri 10 Apr 2009</abbr>\n    \n    by\n    <span class="reviewer vcard"><span class="fn">John Smith</span></span>\n    \n        \n    <div class="item vcard">\n        \n        <a class="url fn org" href="http://acme.com">\n        \n        Acme Corp\n        \n        </a>\n        \n        <div class="tel">+44(0)1234 567456</div>\n        \n        \n<div class="adr">\n    <div class="street-address">5445 N. 27th Street</div>\n    \n    <span class="locality">Milwaukee</span>&nbsp;\n    <span class="region">WI</span>&nbsp;\n    <span class="postal-code">53209</span>&nbsp;\n    <span class="country-name">United States</span>\n</div>\n\n        \n    </div>\n        \n    \n    \n    \n    \n    \n    <abbr class="rating" title="4">\u2605\u2605\u2605\u2605\u2606</abbr>\n    \n    \n    \n    <blockquote class="description">\n        Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat.\n    </blockquote>\n    \n</div>\n'
            self.assertEquals(expected, result)
            # Test for a review concerning something represented by an hCalendar
            result = hreview(rev2, autoescape=True) 
            expected = u'\n<div class="hreview">\n    <strong class="summary">A phenomenal tuba recital</strong>\n    <abbr class="type" title="event"> Event</abbr> Review\n    <br/>\n    \n    by\n    <span class="reviewer vcard"><span class="fn">John Doe</span></span>\n    \n    <div class ="item vevent">\n        <a href="http://www.johnfletcher-tuba.co.uk/" class="url">\n        \n        <abbr title="1987-10-03T19:30:00" class="dtstart">Sat 03 Oct 1987 7:30 p.m.</abbr>\n        \n        \n        </a> -\n        <span class="summary">John Fletcher - One man and his Tuba</span>\n        \n        \n<div class="adr">\n    <div class="street-address">The Pro Arte Theatre</div>\n    \n    <span class="locality">London</span>&nbsp;\n    \n    \n    \n</div>\n\n        \n    </div>\n    \n    \n    \n    \n    \n    \n    <abbr class="rating" title="5">\u2605\u2605\u2605\u2605\u2605</abbr>\n    \n    \n    <blockquote class="description">\n        Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat.\n    </blockquote>\n    \n</div>\n'
            self.assertEquals(expected, result)
            # Test for a review about anything else
            result = hreview(rev3, autoescape=True) 
            expected = u'\n<div class="hreview">\n    <strong class="summary">Latest Star-Wars is Sucko-Barfo</strong>\n    <abbr class="type" title="film"> Film</abbr> Review\n    <br/>\n    \n    by\n    <span class="reviewer vcard"><span class="fn">Barry Norman</span></span>\n    \n        \n            \n    <div class="item">\n        \n        <a class="url fn" href="http://www.starwars.com/movies/episode-iii/">\n        \n        Star Wars - Revenge of the Sith\n        \n        </a>\n        \n    </div>\n            \n        \n    \n    \n    <abbr class="rating" title="1">\u2605\u2606\u2606\u2606\u2606</abbr>\n    \n    \n    \n    \n    \n    \n    <blockquote class="description">\n        Claritas est etiam processus dynamicus, qui sequitur mutationem consuetudium lectorum. Mirum est notare quam littera gothica, quam nunc putamus parum claram, anteposuerit litterarum formas humanitatis per seacula quarta decima et quinta decima. Eodem modo typi, qui nunc nobis videntur parum clari, fiant sollemnes in futurum.\n    </blockquote>\n    \n</div>\n'
            self.assertEquals(expected, result)
            # Test for minimal review
            rev3.summary = ''
            rev3.description = ''
            rev3.rating = 1
            rev3.type = 'film'
            rev3.reviewer = 'Barry Norman'
            rev3.fn = 'Star Wars - Revenge of the Sith'
            rev3.url = ''
            result = hreview(rev3, autoescape=True) 
            expected = u'\n<div class="hreview">\n    \n    <abbr class="type" title="film"> Film</abbr> Review\n    <br/>\n    \n    by\n    <span class="reviewer vcard"><span class="fn">Barry Norman</span></span>\n    \n        \n            \n    <div class="item">\n        \n        <span class="fn">\n        \n        Star Wars - Revenge of the Sith\n        \n        </span>\n        \n    </div>\n            \n        \n    \n    \n    <abbr class="rating" title="1">\u2605\u2606\u2606\u2606\u2606</abbr>\n    \n    \n    \n    \n    \n    \n</div>\n'
            self.assertEquals(expected, result)

        def test_xfn(self):
            """
            Make sure XFN links render correctly
            """
            # Set things up
            u = User.objects.create_user('john', 'john@smith.com', 'password')
            URL = 'http://twitter.com/ntoll'
            tgt = 'Nicholas Tollervey'
            x = microformats.models.xfn()
            x.source = u
            x.target = tgt 
            x.url = URL
            x.save()
            xfnv1 = microformats.models.xfn_values.objects.get(value='friend')
            xfnv2 = microformats.models.xfn_values.objects.get(value='met')
            xfnv3 = microformats.models.xfn_values.objects.get(value='colleague')
            x.relationships.add(xfnv1)
            x.relationships.add(xfnv2)
            x.relationships.add(xfnv3)
            x.save()
            result = xfn(x, autoescape=True)
            expected = u'<a href="http://twitter.com/ntoll" rel="colleague friend met">Nicholas Tollervey</a>'
            self.assertEquals(expected, result)

        def test_template_output(self):
            """ 
            Generates an html file containing various examples of the tags in
            use for testing with screen-scrapers and browser plugins.
            """
            g = microformats.models.geo()
            g.latitude = 37.408183
            g.latitude_description = 'N 37° 24.491'
            g.longitude = -122.13855
            g.longitude_description = 'W 122° 08.313'
            g.save()
            hc = microformats.models.hCard()
            hc.honorific_prefix = 'Mr'
            hc.given_name = 'Joe'
            hc.additional_name = 'Arthur'
            hc.family_name = 'Blogs'
            hc.honorific_suffix = 'PhD'
            hc.url = 'http://acme.com/'
            hc.email_work = 'joe.blogs@acme.com'
            hc.email_home = 'joeblogs2000@home-isp.com'
            hc.tel_work = '+44(0)1234 567890'
            hc.tel_home = '+44(0)1324 234123'
            hc.street_address = '5445 N. 27th Street'
            hc.extended_address = ''
            hc.locality = 'Milwaukee'
            hc.region = 'WI'
            hc.country_name = 'US'
            hc.postal_code = '53209'
            hc.org = "Acme Corp."
            hc.title = 'Vice President'
            hc.save()
            hcl = microformats.models.hCalendar()
            hcl.summary = 'Important Meeting'
            hcl.location = 'BBC in London'
            hcl.url = 'http://www.bbc.co.uk/'
            hcl.dtstart = datetime.datetime(2009, 4, 11, 13, 30)
            hcl.dtend = datetime.datetime(2009, 4, 11, 15, 30)
            hcl.description = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.'
            hcl.street_address = 'Broadcasting House'
            hcl.extended_address = 'Portland Place'
            hcl.locality = 'London'
            hcl.region = ''
            hcl.country_name = 'GB'
            hcl.postal_code = 'W1A 1AA'
            hcl.save()
            u = User.objects.create_user('john', 'john@smith.com', 'password')
            URL = 'http://twitter.com/ntoll'
            tgt = 'Nicholas Tollervey'
            x = microformats.models.xfn()
            x.source = u
            x.target = tgt 
            x.url = URL
            x.save()
            xfnv1 = microformats.models.xfn_values.objects.get(value='friend')
            xfnv2 = microformats.models.xfn_values.objects.get(value='met')
            xfnv3 = microformats.models.xfn_values.objects.get(value='colleague')
            x.relationships.add(xfnv1)
            x.relationships.add(xfnv2)
            x.relationships.add(xfnv3)
            x.save()
            g2 = microformats.models.geo()
            g2.latitude = 45.498677
            g2.latitude_description = "45°34' 13"" N"
            g2.longitude = -73.570260 
            g2.longitude_description = "73°29' 55"" W" 
            g2.save()
            hc2 = microformats.models.hCard()
            hc2.honorific_prefix = 'Mr'
            hc2.given_name = 'John'
            hc2.additional_name = ''
            hc2.family_name = 'Fletcher'
            hc2.honorific_suffix = 'MA(cantab)'
            hc2.url = 'http://lso.co.uk/'
            hc2.tel_work = '+44(0)1234 567456'
            hc2.street_address = 'The Barbican Centre'
            hc2.extended_address = 'Silk Street'
            hc2.locality = 'London'
            hc2.country_name = 'GB'
            hc2.postal_code = 'EC2Y 8DS'
            hc2.org = 'London Symphony Orchestra'
            hc2.title = 'Principal Tuba Player'
            hc2.save()
            hcl2 = microformats.models.hCalendar()
            hcl2.summary = 'Operation Overlord'
            hcl2.location = 'Normandy, France'
            hcl2.url = 'http://en.wikipedia.org/wiki/Operation_Overlord'
            hcl2.dtstart = datetime.datetime(1944, 6, 6)
            hcl2.dtend = datetime.datetime(1944, 8, 30)
            hcl2.description = 'You are about to embark upon the Great Crusade, toward which we have striven these many months. The eyes of the world are upon you. The hopes and prayers of liberty-loving people everywhere march with you. In company with our brave Allies and brothers-in-arms on other Fronts, you will bring about the destruction of the German war machine, the elimination of Nazi tyranny over the oppressed peoples of Europe, and security for ourselves in a free world.'
            hcl2.save()
            listing = microformats.models.hListing()
            listing.listing_action = "sell"
            listing.summary = "Pony requires a good home"
            listing.description = "A young pony who answers to the name Django"\
                " requires a new home having outgrown his current host. Easy"\
                " going and fun to play with Django also provides rainbow"\
                " manure that is sure to help the garden grow."
            listing.lister_fn = "John Doe"
            listing.lister_email = "john.doe@isp.net"
            listing.lister_url = "http://isp.com/django_the_pony"
            listing.lister_tel = "+44(0) 1234 567456"
            listing.dtlisted = datetime.datetime(2009, 5, 6)
            listing.dtexpired = datetime.datetime(2009, 8, 19)
            listing.price = "£2500 ono"
            listing.item_fn = "Django the Pony"
            listing.item_url = "http://djangoproject.com/"
            listing.locality = "Brighton"
            listing.country_name = "GB"
            listing.save()
            rev1 = microformats.models.hReview()
            rev1.summary="Acme's new services rock!"
            rev1.type='business'
            rev1.description='Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat.'
            rev1.rating=4
            rev1.dtreviewed=datetime.datetime(2009,4,10)
            rev1.reviewer='John Smith'
            rev1.fn='Acme Corp'
            rev1.url='http://acme.com'
            rev1.tel='+44(0)1234 567456'
            rev1.street_address = '5445 N. 27th Street'
            rev1.extended_address = ''
            rev1.locality = 'Milwaukee'
            rev1.region = 'WI'
            rev1.country_name = 'US'
            rev1.postal_code = '53209'
            rev1.save()
            rev2 = microformats.models.hReview()
            rev2.summary = 'A phenomenal tuba recital'
            rev2.description = 'Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat.'
            rev2.rating=5
            rev2.type='event'
            rev2.reviewer='John Doe'
            rev2.fn='John Fletcher - One man and his Tuba'
            rev2.url='http://www.johnfletcher-tuba.co.uk/'
            rev2.dtstart = datetime.datetime(1987, 10, 3, 19, 30)
            rev2.street_address = 'The Pro Arte Theatre'
            rev2.locality = 'London'
            rev2.save()
            rev3 = microformats.models.hReview()
            rev3.summary = "Mr Bloggs children's entertainer flops"
            rev3.description = 'Claritas est etiam processus dynamicus, qui sequitur mutationem consuetudium lectorum. Mirum est notare quam littera gothica, quam nunc putamus parum claram, anteposuerit litterarum formas humanitatis per seacula quarta decima et quinta decima. Eodem modo typi, qui nunc nobis videntur parum clari, fiant sollemnes in futurum.'
            rev3.rating=2
            rev3.type='person'
            rev3.reviewer='Melvyn Bragg'
            rev3.fn='Mr Bloggs'
            rev3.tel='01234 567456'
            rev3.save()
            rev4 = microformats.models.hReview()
            rev4.summary = 'Latest Star-Wars is Sucko-Barfo'
            rev4.description = 'Claritas est etiam processus dynamicus, qui sequitur mutationem consuetudium lectorum. Mirum est notare quam littera gothica, quam nunc putamus parum claram, anteposuerit litterarum formas humanitatis per seacula quarta decima et quinta decima. Eodem modo typi, qui nunc nobis videntur parum clari, fiant sollemnes in futurum.'
            rev4.rating=1
            rev4.type='film'
            rev4.reviewer='Barry Norman'
            rev4.fn='Star Wars - Revenge of the Sith'
            rev4.url='http://www.starwars.com/movies/episode-iii/'
            rev4.save()
            rev5 = microformats.models.hReview()
            rev5.rating=1
            rev5.type='film'
            rev5.fn='Star Wars - The Phantom Menace'
            rev5.save()
            feed = microformats.models.hFeed()
            feed.save()
            entry1 = microformats.models.hEntry()
            entry1.hfeed = feed
            entry1.entry_title = 'Entry 1 Title'
            entry1.entry_content = 'Claritas est etiam processus dynamicus, qui sequitur mutationem consuetudium lectorum. Mirum est notare quam littera gothica, quam nunc putamus parum claram, anteposuerit litterarum formas humanitatis per seacula quarta decima et quinta decima. Eodem modo typi, qui nunc nobis videntur parum clari, fiant sollemnes in futurum.'
            entry1.entry_summary = 'Lorem ipsum dolor sit amet doo-dah whatsit thingymajig'
            entry1.author = 'A.N.Other'
            entry1.bookmark = 'http://website.com/entry1'
            entry1.updated = datetime.datetime(2009, 6, 1)
            entry1.save()
            entry2 = microformats.models.hEntry()
            entry2.hfeed = feed
            entry2.entry_title = 'Entry 2 Title'
            entry2.entry_content = 'Claritas est etiam processus dynamicus, qui sequitur mutationem consuetudium lectorum. Mirum est notare quam littera gothica, quam nunc putamus parum claram, anteposuerit litterarum formas humanitatis per seacula quarta decima et quinta decima. Eodem modo typi, qui nunc nobis videntur parum clari, fiant sollemnes in futurum.'
            entry2.entry_summary = 'Lorem ipsum dolor sit amet doo-dah whatsit thingymajig'
            entry2.author = 'Sidney Humphries'
            entry2.bookmark = 'http://website.com/entry2'
            entry2.updated = datetime.datetime(2009, 3, 14)
            entry2.save()
            entry3 = microformats.models.hEntry()
            entry3.hfeed = feed
            entry3.entry_title = 'Entry 3 Title'
            entry3.entry_content = 'Claritas est etiam processus dynamicus, qui sequitur mutationem consuetudium lectorum. Mirum est notare quam littera gothica, quam nunc putamus parum claram, anteposuerit litterarum formas humanitatis per seacula quarta decima et quinta decima. Eodem modo typi, qui nunc nobis videntur parum clari, fiant sollemnes in futurum.'
            entry3.entry_summary = 'Lorem ipsum dolor sit amet doo-dah whatsit thingymajig'
            entry3.author = 'Nicholas Hawkesmoor'
            entry3.bookmark = 'http://website.com/entry3'
            entry3.updated = datetime.datetime(2008, 12, 28)
            entry3.save()
            entry4 = microformats.models.hEntry()
            entry4.entry_title = 'Entry 4 Title'
            entry4.entry_content = 'Claritas est etiam processus dynamicus, qui sequitur mutationem consuetudium lectorum. Mirum est notare quam littera gothica, quam nunc putamus parum claram, anteposuerit litterarum formas humanitatis per seacula quarta decima et quinta decima. Eodem modo typi, qui nunc nobis videntur parum clari, fiant sollemnes in futurum.'
            entry4.entry_summary = 'Lorem ipsum dolor sit amet doo-dah whatsit thingymajig'
            entry4.author = 'Fred Blogs'
            entry4.bookmark = 'http://website.com/entry4'
            entry4.updated = datetime.datetime(2008, 11, 15)
            entry4.save()
            item1 = microformats.models.hNews()
            item1.hfeed = feed
            item1.entry_title = 'L.A. Icon Otis Chandler Dies at 78'
            item1.entry_content = 'Otis Chandler, whose vision and determination as publisher of the Los Angeles Times from 1960 to 1980 catapulted the paper from mediocrity into the front ranks of American journalism, died today of a degenerative illness called Lewy body disease. He was 78.'
            item1.entry_summary = 'An obituary of Los Angeles Times Publisher Otis Chandler'
            item1.author = 'David Shaw and Mitchell Landsberg'
            item1.bookmark = 'http://www.latimes.com/news/local/la-me-chandler-obit,0,7195252.story'
            item1.updated = datetime.datetime(2006, 2, 27)
            item1.source_org = 'Los Angeles Times'
            item1.source_url = 'http://www.latimes.com'
            item1.principles_url = 'http://www.latimes.com/news/nationworld/nation/la-0705lat_ethics_code-pdf,0,7257671.acrobat'
            item1.license_url = 'http://www.latimes.com/services/site/lat-terms,0,6713384.htmlstory'
            item1.license_description = 'Terms of service'
            item1.locality = 'Los Angeles'
            item1.country_name = 'US'
            item1.longitude = -118.2666667
            item1.latitude = 34.0444444
            item1.save()

            # All the data is defined so lets render the test template...
            template = get_template('test.html')
            data = {
                    'contact': hc,
                    'loc': g,
                    'event': hcl, 
                    'listing': listing,
                    'review1': rev1,
                    'review2': rev2,
                    'review3': rev3,
                    'review4': rev4,
                    'review5': rev5,
                    'person': x,
                    'c2': hc2,
                    'loc2': g2,
                    'event2': hcl2,
                    'feed': feed,
                    'entry': entry4,
                    'item': item1,
                    }
            context = Context(data)
            import html_test
            path =  os.path.dirname(html_test.__file__)
            outfile = codecs.open(os.path.join(path, 'microformat_test.html'), 'w', 'utf-8')
            outfile.write(template.render(context))
            outfile.close()

########NEW FILE########
__FILENAME__ = test_views
# -*- coding: UTF-8 -*-
"""
View tests for Microformats 

Author: Nicholas H.Tollervey

"""
# python
import datetime

# django
from django.test.client import Client
from django.test import TestCase

# project

class ViewTestCase(TestCase):
        """
        Testing Views 
        """
        # Reference fixtures here
        fixtures = []

        def test_example(self):
            # Your test goes here
            pass

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
