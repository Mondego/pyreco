__FILENAME__ = db_fields
from django.db.models.fields.related import ForeignKey

try:
    from south.modelsinspector import add_introspection_rules
    has_south = True
except ImportError:
    has_south = False


from smart_selects import form_fields


class ChainedForeignKey(ForeignKey):
    """
    chains the choices of a previous combo box with this one
    """
    def __init__(self, to, chained_field=None, chained_model_field=None,
                 show_all=False, auto_choose=False, view_name=None, **kwargs):
        if isinstance(to, basestring):
            self.app_name, self.model_name = to.split('.')
        else:
            self.app_name = to._meta.app_label
            self.model_name = to._meta.object_name
        self.chain_field = chained_field
        self.model_field = chained_model_field
        self.show_all = show_all
        self.auto_choose = auto_choose
        self.view_name = view_name
        ForeignKey.__init__(self, to, **kwargs)

    def formfield(self, **kwargs):
        defaults = {
            'form_class': form_fields.ChainedModelChoiceField,
            'queryset': self.rel.to._default_manager.complex_filter(self.rel.limit_choices_to),
            'to_field_name': self.rel.field_name,
            'app_name': self.app_name,
            'model_name': self.model_name,
            'chain_field': self.chain_field,
            'model_field': self.model_field,
            'show_all': self.show_all,
            'auto_choose': self.auto_choose,
            'view_name': self.view_name,
        }
        defaults.update(kwargs)
        return super(ChainedForeignKey, self).formfield(**defaults)


class GroupedForeignKey(ForeignKey):
    """
    Opt Grouped Field
    """
    def __init__(self, to, group_field, **kwargs):
        self.group_field = group_field
        self._choices = True
        ForeignKey.__init__(self, to, **kwargs)

    def formfield(self, **kwargs):
        defaults = {
            'form_class': form_fields.GroupedModelSelect,
            'queryset': self.rel.to._default_manager.complex_filter(
                                                    self.rel.limit_choices_to),
            'to_field_name': self.rel.field_name,
            'order_field': self.group_field,
        }
        defaults.update(kwargs)
        return super(ForeignKey, self).formfield(**defaults)

if has_south:
    rules_grouped = [(
        (GroupedForeignKey,),
        [],
        {
            'to': ['rel.to', {}],
            'group_field': ['group_field', {}],
        },
    )]

    add_introspection_rules([], ["^smart_selects\.db_fields\.ChainedForeignKey"])
    add_introspection_rules(rules_grouped, ["^smart_selects\.db_fields\.GroupedForeignKey"])

########NEW FILE########
__FILENAME__ = form_fields
from django.db.models import get_model
from django.forms.models import ModelChoiceField
from django.forms import ChoiceField

from smart_selects.widgets import ChainedSelect


class ChainedModelChoiceField(ModelChoiceField):

    def __init__(self, app_name, model_name,
                 chain_field, model_field, show_all,
                 auto_choose, manager=None,
                 initial=None, view_name=None, *args, **kwargs):
        defaults = {
            'widget': ChainedSelect(app_name, model_name, chain_field,
                                    model_field, show_all, auto_choose,
                                    manager, view_name),
        }
        defaults.update(kwargs)
        if not 'queryset' in kwargs:
            queryset = get_model(app_name, model_name).objects.all()
            super(ChainedModelChoiceField, self).__init__(queryset=queryset, initial=initial, *args, **defaults)
        else:
            super(ChainedModelChoiceField, self).__init__(initial=initial, *args, **defaults)

    def _get_choices(self):
        self.widget.queryset = self.queryset
        choices = super(ChainedModelChoiceField, self)._get_choices()
        return choices
    choices = property(_get_choices, ChoiceField._set_choices)


class GroupedModelSelect(ModelChoiceField):
    def __init__(self, queryset, order_field, *args, **kwargs):
        self.order_field = order_field
        super(GroupedModelSelect, self).__init__(queryset, *args, **kwargs)

    def _get_choices(self):
        # If self._choices is set, then somebody must have manually set
        # the property self.choices. In this case, just return self._choices.
        if hasattr(self, '_choices'):
            return self._choices
        # Otherwise, execute the QuerySet in self.queryset to determine the
        # choices dynamically. Return a fresh QuerySetIterator that has not been
        # consumed. Note that we're instantiating a new QuerySetIterator *each*
        # time _get_choices() is called (and, thus, each time self.choices is
        # accessed) so that we can ensure the QuerySet has not been consumed. This
        # construct might look complicated but it allows for lazy evaluation of
        # the queryset.
        group_indexes = {}
        choices = [("", self.empty_label or "---------")]
        i = len(choices)
        for item in self.queryset:
            order_field = getattr(item, self.order_field)
            group_index = order_field.pk
            if not group_index in group_indexes:
                group_indexes[group_index] = i
                choices.append([unicode(order_field), []])
                i += 1
            choice_index = group_indexes[group_index]
            choices[choice_index][1].append(self.make_choice(item))
        return choices

    def make_choice(self, obj):
        return (obj.pk, "   " + self.label_from_instance(obj))

    choices = property(_get_choices, ChoiceField._set_choices)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls.defaults import *
except ImportError:
    from django.conf.urls import *

urlpatterns = patterns('smart_selects.views',
    url(r'^all/(?P<app>[\w\-]+)/(?P<model>[\w\-]+)/(?P<field>[\w\-]+)/(?P<value>[\w\-]+)/$', 'filterchain_all', name='chained_filter_all'),
    url(r'^filter/(?P<app>[\w\-]+)/(?P<model>[\w\-]+)/(?P<field>[\w\-]+)/(?P<value>[\w\-]+)/$', 'filterchain', name='chained_filter'),
    url(r'^filter/(?P<app>[\w\-]+)/(?P<model>[\w\-]+)/(?P<manager>[\w\-]+)/(?P<field>[\w\-]+)/(?P<value>[\w\-]+)/$', 'filterchain', name='chained_filter'),
)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

def unicode_sorter(input):
    """ This function implements sort keys for the german language according to 
    DIN 5007."""
    
    # key1: compare words lowercase and replace umlauts according to DIN 5007
    key1=input.lower()
    key1=key1.replace(u"ä", u"a")
    key1=key1.replace(u"ö", u"o")
    key1=key1.replace(u"ü", u"u")
    key1=key1.replace(u"ß", u"ss")
    
    # key2: sort the lowercase word before the uppercase word and sort
    # the word with umlaut after the word without umlaut
    #key2=input.swapcase()
    
    # in case two words are the same according to key1, sort the words
    # according to key2. 
    return key1

########NEW FILE########
__FILENAME__ = views
import locale

from django.db.models import get_model
from django.http import HttpResponse
from django.utils import simplejson

from smart_selects.utils import unicode_sorter


def filterchain(request, app, model, field, value, manager=None):
    model_class = get_model(app, model)
    if value == '0':
        keywords = {str("%s__isnull" % field): True}
    else:
        keywords = {str(field): str(value)}
    if manager is not None and hasattr(model_class, manager):
        queryset = getattr(model_class, manager)
    else:
        queryset = model_class._default_manager
    results = list(queryset.filter(**keywords))
    results.sort(cmp=locale.strcoll, key=lambda x: unicode_sorter(unicode(x)))
    result = []
    for item in results:
        result.append({'value': item.pk, 'display': unicode(item)})
    json = simplejson.dumps(result)
    return HttpResponse(json, mimetype='application/json')


def filterchain_all(request, app, model, field, value):
    model_class = get_model(app, model)
    if value == '0':
        keywords = {str("%s__isnull" % field): True}
    else:
        keywords = {str(field): str(value)}
    results = list(model_class._default_manager.filter(**keywords))
    results.sort(cmp=locale.strcoll, key=lambda x: unicode_sorter(unicode(x)))
    final = []
    for item in results:
        final.append({'value': item.pk, 'display': unicode(item)})
    results = list(model_class._default_manager.exclude(**keywords))
    results.sort(cmp=locale.strcoll, key=lambda x: unicode_sorter(unicode(x)))
    final.append({'value': "", 'display': "---------"})

    for item in results:
        final.append({'value': item.pk, 'display': unicode(item)})
    json = simplejson.dumps(final)
    return HttpResponse(json, mimetype='application/json')

########NEW FILE########
__FILENAME__ = widgets
import locale

import django

from django.conf import settings
from django.contrib.admin.templatetags.admin_static import static
from django.core.urlresolvers import reverse
from django.db.models import get_model
from django.forms.widgets import Select
from django.utils.safestring import mark_safe

from smart_selects.utils import unicode_sorter


if django.VERSION >= (1, 2, 0) and getattr(settings,
                                           'USE_DJANGO_JQUERY', True):
    USE_DJANGO_JQUERY = True
else:
    USE_DJANGO_JQUERY = False
    JQUERY_URL = getattr(settings, 'JQUERY_URL', 'http://ajax.googleapis.com/ajax/libs/jquery/1.3.2/jquery.min.js')

URL_PREFIX = getattr(settings, "SMART_SELECTS_URL_PREFIX", "")


class ChainedSelect(Select):
    def __init__(self, app_name, model_name, chain_field,
                 model_field, show_all, auto_choose,
                 manager=None, view_name=None, *args, **kwargs):
        self.app_name = app_name
        self.model_name = model_name
        self.chain_field = chain_field
        self.model_field = model_field
        self.show_all = show_all
        self.auto_choose = auto_choose
        self.manager = manager
        self.view_name = view_name
        super(Select, self).__init__(*args, **kwargs)

    class Media:
        extra = '' if settings.DEBUG else '.min'
        js = [
            'jquery%s.js' % extra,
            'jquery.init.js'
        ]
        if USE_DJANGO_JQUERY:
            js = [static('admin/js/%s' % url) for url in js]
        elif JQUERY_URL:
            js = [JQUERY_URL]

    def render(self, name, value, attrs=None, choices=()):
        if len(name.split('-')) > 1:  # formset
            chain_field = '-'.join(name.split('-')[:-1] + [self.chain_field])
        else:
            chain_field = self.chain_field
        if not self.view_name:
            if self.show_all:
                view_name = "chained_filter_all"
            else:
                view_name = "chained_filter"
        else:
            view_name = self.view_name
        kwargs = {'app': self.app_name, 'model': self.model_name,
                  'field': self.model_field, 'value': "1"}
        if self.manager is not None:
            kwargs.update({'manager': self.manager})
        url = URL_PREFIX + ("/".join(reverse(view_name, kwargs=kwargs).split("/")[:-2]))
        if self.auto_choose:
            auto_choose = 'true'
        else:
            auto_choose = 'false'
        empty_label = iter(self.choices).next()[1]  # Hacky way to getting the correct empty_label from the field instead of a hardcoded '--------'
        js = """
        <script type="text/javascript">
        //<![CDATA[
        (function($) {
            function fireEvent(element,event){
                if (document.createEventObject){
                // dispatch for IE
                var evt = document.createEventObject();
                return element.fireEvent('on'+event,evt)
                }
                else{
                // dispatch for firefox + others
                var evt = document.createEvent("HTMLEvents");
                evt.initEvent(event, true, true ); // event type,bubbling,cancelable
                return !element.dispatchEvent(evt);
                }
            }

            function dismissRelatedLookupPopup(win, chosenId) {
                var name = windowname_to_id(win.name);
                var elem = document.getElementById(name);
                if (elem.className.indexOf('vManyToManyRawIdAdminField') != -1 && elem.value) {
                    elem.value += ',' + chosenId;
                } else {
                    elem.value = chosenId;
                }
                fireEvent(elem, 'change');
                win.close();
            }

            $(document).ready(function(){
                function fill_field(val, init_value){
                    if (!val || val==''){
                        options = '<option value="">%(empty_label)s<'+'/option>';
                        $("#%(id)s").html(options);
                        $('#%(id)s option:first').attr('selected', 'selected');
                        $("#%(id)s").trigger('change');
                        return;
                    }
                    $.getJSON("%(url)s/"+val+"/", function(j){
                        var options = '<option value="">%(empty_label)s<'+'/option>';
                        for (var i = 0; i < j.length; i++) {
                            options += '<option value="' + j[i].value + '">' + j[i].display + '<'+'/option>';
                        }
                        var width = $("#%(id)s").outerWidth();
                        $("#%(id)s").html(options);
                        if (navigator.appVersion.indexOf("MSIE") != -1)
                            $("#%(id)s").width(width + 'px');
                        $('#%(id)s option:first').attr('selected', 'selected');
                        var auto_choose = %(auto_choose)s;
                        if(init_value){
                            $('#%(id)s option[value="'+ init_value +'"]').attr('selected', 'selected');
                        }
                        if(auto_choose && j.length == 1){
                            $('#%(id)s option[value="'+ j[0].value +'"]').attr('selected', 'selected');
                        }
                        $("#%(id)s").trigger('change');
                    })
                }

                if(!$("#id_%(chainfield)s").hasClass("chained")){
                    var val = $("#id_%(chainfield)s").val();
                    fill_field(val, "%(value)s");
                }

                $("#id_%(chainfield)s").change(function(){
                    var start_value = $("#%(id)s").val();
                    var val = $(this).val();
                    fill_field(val, start_value);
                })
            })
            if (typeof(dismissAddAnotherPopup) !== 'undefined') {
                var oldDismissAddAnotherPopup = dismissAddAnotherPopup;
                dismissAddAnotherPopup = function(win, newId, newRepr) {
                    oldDismissAddAnotherPopup(win, newId, newRepr);
                    if (windowname_to_id(win.name) == "id_%(chainfield)s") {
                        $("#id_%(chainfield)s").change();
                    }
                }
            }
        })(jQuery || django.jQuery);
        //]]>
        </script>

        """
        js = js % {"chainfield": chain_field,
                   "url": url,
                   "id": attrs['id'],
                   'value': value,
                   'auto_choose': auto_choose,
                   'empty_label': empty_label}
        final_choices = []

        if value:
            item = self.queryset.filter(pk=value)[0]
            try:
                pk = getattr(item, self.model_field + "_id")
                filter = {self.model_field: pk}
            except AttributeError:
                try:  # maybe m2m?
                    pks = getattr(item, self.model_field).all().values_list('pk', flat=True)
                    filter = {self.model_field + "__in": pks}
                except AttributeError:
                    try:  # maybe a set?
                        pks = getattr(item, self.model_field + "_set").all().values_list('pk', flat=True)
                        filter = {self.model_field + "__in": pks}
                    except:  # give up
                        filter = {}
            filtered = list(get_model(self.app_name, self.model_name).objects.filter(**filter).distinct())
            filtered.sort(cmp=locale.strcoll, key=lambda x: unicode_sorter(unicode(x)))
            for choice in filtered:
                final_choices.append((choice.pk, unicode(choice)))
        if len(final_choices) > 1:
            final_choices = [("", (empty_label))] + final_choices
        if self.show_all:
            final_choices.append(("", (empty_label)))
            self.choices = list(self.choices)
            self.choices.sort(cmp=locale.strcoll, key=lambda x: unicode_sorter(x[1]))
            for ch in self.choices:
                if not ch in final_choices:
                    final_choices.append(ch)
        self.choices = ()
        final_attrs = self.build_attrs(attrs, name=name)
        if 'class' in final_attrs:
            final_attrs['class'] += ' chained'
        else:
            final_attrs['class'] = 'chained'
        output = super(ChainedSelect, self).render(name, value, final_attrs, choices=final_choices)
        output += js
        return mark_safe(output)

########NEW FILE########
