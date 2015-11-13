__FILENAME__ = managers
from django.contrib.admin.widgets import AdminTextInputWidget
from django.utils.translation import ugettext_lazy as _

from taggit.forms import TagField
from taggit.managers import TaggableManager as BaseTaggableManager

from widgets import TagAutocomplete


class TaggableManager(BaseTaggableManager):
    def formfield(self, form_class=TagField, **kwargs):
        defaults = {
            "label": _("Tags"),
            "help_text": _("A comma-separated list of tags."),
        }
        defaults.update(kwargs)
        
        kwargs['widget'] = TagAutocomplete
        
        return form_class(**kwargs)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('taggit_autocomplete.views',
    url(r'^list$', 'list_tags', name='taggit_autocomplete-list'),
)

########NEW FILE########
__FILENAME__ = utils
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

    Ported from Jonathan Buchanan's `django-tagging
    <http://django-tagging.googlecode.com/>`_
    """
    names = []
    for tag in tags:
        name = tag.name
        if u',' in name:
            names.append('"%s"' % name)
        else:
            names.append(name)
    glue = u', '
    return glue.join(sorted(names))

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from django.core import serializers
from taggit.models import Tag

def list_tags(request):
	try:
		tags = Tag.objects.filter(name__istartswith=request.GET['q']).values_list('name', flat=True)
	except MultiValueDictKeyError:
		pass
	
	return HttpResponse('\n'.join(tags), mimetype='text/plain')

########NEW FILE########
__FILENAME__ = widgets
from django import forms
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils.safestring import mark_safe

from utils import edit_string_for_tags


class TagAutocomplete(forms.TextInput):
	input_type = 'text'
	
	def render(self, name, value, attrs=None):
		list_view = reverse('taggit_autocomplete-list')
		if value is not None and not isinstance(value, basestring):
			value = edit_string_for_tags([o.tag for o in value.select_related("tag")])
		html = super(TagAutocomplete, self).render(name, value, attrs)
		js = u'<script type="text/javascript">jQuery().ready(function() { jQuery("#%s").autocomplete("%s", { multiple: true }); });</script>' % (attrs['id'], list_view)
		return mark_safe("\n".join([html, js]))
	
	class Media:
		js_base_url = getattr(settings, 'TAGGIT_AUTOCOMPLETE_JS_BASE_URL','%s/jquery-autocomplete' % settings.MEDIA_URL)
		css = {
		    'all': ('%s/jquery.autocomplete.css' % js_base_url,)
		}
		js = (
			'%s/jquery.autocomplete.js' % js_base_url,
			)
########NEW FILE########
