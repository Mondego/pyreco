__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = jquery_validation
import os

from django import template

import ajax_validation

register = template.Library()

VALIDATION_SCRIPT = None

def include_validation():
    global VALIDATION_SCRIPT
    if VALIDATION_SCRIPT is None:
        VALIDATION_SCRIPT = open(os.path.join(os.path.dirname(ajax_validation.__file__), 'media', 'ajax_validation', 'js', 'jquery-ajax-validation.js')).read()
    return '''<script type="text/javascript">%s</script>''' % VALIDATION_SCRIPT
register.simple_tag(include_validation)

########NEW FILE########
__FILENAME__ = urls

########NEW FILE########
__FILENAME__ = utils
from django.utils.functional import Promise
from django.utils.encoding import force_unicode
try:
    from simplejson import JSONEncoder
except ImportError:
    try:
        from json import JSONEncoder
    except ImportError:
        from django.utils.simplejson import JSONEncoder

class LazyEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            return force_unicode(obj)
        return obj

########NEW FILE########
__FILENAME__ = views
from django import forms
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.forms.formsets import BaseFormSet

from ajax_validation.utils import LazyEncoder

def validate(request, *args, **kwargs):
    form_class = kwargs.pop('form_class')
    defaults = {
        'data': request.POST
    }
    extra_args_func = kwargs.pop('callback', lambda request, *args, **kwargs: {})
    kwargs = extra_args_func(request, *args, **kwargs)
    defaults.update(kwargs)
    form = form_class(**defaults)
    if form.is_valid():
        data = {
            'valid': True,
        }
    else:
        # if we're dealing with a FormSet then walk over .forms to populate errors and formfields
        if isinstance(form, BaseFormSet):
            errors = {}
            formfields = {}
            for f in form.forms:
                for field in f.fields.keys():
                    formfields[f.add_prefix(field)] = f[field]
                for field, error in f.errors.iteritems():
                    errors[f.add_prefix(field)] = error
            if form.non_form_errors():
                errors['__all__'] = form.non_form_errors()
        else:
            errors = form.errors
            formfields = dict([(fieldname, form[fieldname]) for fieldname in form.fields.keys()])

        # if fields have been specified then restrict the error list
        if request.POST.getlist('fields'):
            fields = request.POST.getlist('fields') + ['__all__']
            errors = dict([(key, val) for key, val in errors.iteritems() if key in fields])

        final_errors = {}
        for key, val in errors.iteritems():
            if '__all__' in key:
                final_errors[key] = val
            elif not isinstance(formfields[key].field, forms.FileField):
                html_id = formfields[key].field.widget.attrs.get('id') or formfields[key].auto_id
                html_id = formfields[key].field.widget.id_for_label(html_id)
                final_errors[html_id] = val
        data = {
            'valid': False or not final_errors,
            'errors': final_errors,
        }
    json_serializer = LazyEncoder()
    return HttpResponse(json_serializer.encode(data), mimetype='application/json')
validate = require_POST(validate)

########NEW FILE########
