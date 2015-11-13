__FILENAME__ = djpjax
import functools

from django.views.generic.base import TemplateResponseMixin

def pjax(pjax_template=None):
    def pjax_decorator(view):
        @functools.wraps(view)
        def _view(request, *args, **kwargs):
            resp = view(request, *args, **kwargs)
            # this is lame. what else though?
            # if not hasattr(resp, "is_rendered"):
            #     warnings.warn("@pjax used with non-template-response view")
            #     return resp
            if request.META.get('HTTP_X_PJAX', False):
                if pjax_template:
                    resp.template_name = pjax_template
                else:
                    resp.template_name = _pjaxify_template_var(resp.template_name)
            return resp
        return _view
    return pjax_decorator

def pjaxtend(parent='base.html', pjax_parent='pjax.html', context_var='parent'):
    def pjaxtend_decorator(view):
        @functools.wraps(view)
        def _view(request, *args, **kwargs):
            resp = view(request, *args, **kwargs)
            # this is lame. what else though?
            # if not hasattr(resp, "is_rendered"):
            #     warnings.warn("@pjax used with non-template-response view")
            #     return resp
            if request.META.get('HTTP_X_PJAX', False):
                resp.context_data[context_var] = pjax_parent
            elif parent:
                resp.context_data[context_var] = parent
            return resp
        return _view
    return pjaxtend_decorator

class PJAXResponseMixin(TemplateResponseMixin):

    pjax_template_name = None

    def get_template_names(self):
        names = super(PJAXResponseMixin, self).get_template_names()
        if self.request.META.get('HTTP_X_PJAX', False):
            if self.pjax_template_name:
                names = [self.pjax_template_name]
            else:
                names = _pjaxify_template_var(names)
        return names


def _pjaxify_template_var(template_var):
    if isinstance(template_var, (list, tuple)):
        template_var = type(template_var)(_pjaxify_template_name(name) for name in template_var)
    elif isinstance(template_var, basestring):
        template_var = _pjaxify_template_name(template_var)
    return template_var


def _pjaxify_template_name(name):
    if "." in name:
        name = "%s-pjax.%s" % tuple(name.rsplit('.', 1))
    else:
        name += "-pjax"
    return name

########NEW FILE########
__FILENAME__ = tests
# Django bootstrap, sigh.
from django.conf import settings; settings.configure()

import djpjax
from django.template.response import TemplateResponse
from django.test.client import RequestFactory
from django.views.generic import View

# A couple of request objects - one PJAX, one not.
rf = RequestFactory()
regular_request = rf.get('/')
pjax_request = rf.get('/', HTTP_X_PJAX=True)

# Tests.

def test_pjax_sans_template():
    resp = view_sans_pjax_template(regular_request)
    assert resp.template_name == "template.html"
    resp = view_sans_pjax_template(pjax_request)
    assert resp.template_name == "template-pjax.html"

def test_view_with_silly_template():
    resp = view_with_silly_template(regular_request)
    assert resp.template_name == "silly"
    resp = view_with_silly_template(pjax_request)
    assert resp.template_name == "silly-pjax"

def test_view_with_pjax_template():
    resp = view_with_pjax_template(regular_request)
    assert resp.template_name == "template.html"
    resp = view_with_pjax_template(pjax_request)
    assert resp.template_name == "pjax.html"

def test_view_with_template_tuple():
    resp = view_with_template_tuple(regular_request)
    assert resp.template_name == ("template.html", "other_template.html")
    resp = view_with_template_tuple(pjax_request)
    assert resp.template_name == ("template-pjax.html", "other_template-pjax.html")

def test_class_pjax_sans_template():
    view = NoPJAXTemplateVew.as_view()
    resp = view(regular_request)
    assert resp.template_name[0] == "template.html"
    resp = view(pjax_request)
    assert resp.template_name[0] == "template-pjax.html"

def test_class_with_silly_template():
    view = SillyTemplateNameView.as_view()
    resp = view(regular_request)
    assert resp.template_name[0] == "silly"
    resp = view(pjax_request)
    assert resp.template_name[0] == "silly-pjax"

def test_class_with_pjax_template():
    view = PJAXTemplateView.as_view()
    resp = view(regular_request)
    assert resp.template_name[0] == "template.html"
    resp = view(pjax_request)
    assert resp.template_name[0] == "pjax.html"

def test_pjaxtend_default():
    resp = view_default_pjaxtend(regular_request)
    assert resp.template_name == "template.html"
    assert resp.context_data['parent'] == "base.html"
    resp = view_default_pjaxtend(pjax_request)
    assert resp.template_name == "template.html"
    assert resp.context_data['parent'] == "pjax.html"

def test_pjaxtend_default_parent():
    resp = view_default_parent_pjaxtend(regular_request)
    assert resp.template_name == "template.html"
    assert resp.context_data['parent'] == "parent.html"
    resp = view_default_parent_pjaxtend(pjax_request)
    assert resp.template_name == "template.html"
    assert resp.context_data['parent'] == "pjax.html"

def test_pjaxtend_custom_parent():
    resp = view_custom_parent_pjaxtend(regular_request)
    assert resp.template_name == "template.html"
    assert resp.context_data['parent'] == "parent.html"
    resp = view_custom_parent_pjaxtend(pjax_request)
    assert resp.template_name == "template.html"
    assert resp.context_data['parent'] == "parent-pjax.html"

def test_pjaxtend_custom_context():
    resp = view_custom_context_pjaxtend(regular_request)
    assert resp.template_name == "template.html"
    assert resp.context_data['my_parent'] == "parent.html"
    resp = view_custom_context_pjaxtend(pjax_request)
    assert resp.template_name == "template.html"
    assert resp.context_data['my_parent'] == "parent-pjax.html"

# The test "views" themselves.

@djpjax.pjax()
def view_sans_pjax_template(request):
    return TemplateResponse(request, "template.html", {})
    
@djpjax.pjax()
def view_with_silly_template(request):
    return TemplateResponse(request, "silly", {})
    
@djpjax.pjax("pjax.html")
def view_with_pjax_template(request):
    return TemplateResponse(request, "template.html", {})

@djpjax.pjax()
def view_with_template_tuple(request):
    return TemplateResponse(request, ("template.html", "other_template.html"), {})

@djpjax.pjaxtend()
def view_default_pjaxtend(request):
    return TemplateResponse(request, "template.html", {})

@djpjax.pjaxtend('parent.html')
def view_default_parent_pjaxtend(request):
    return TemplateResponse(request, "template.html", {})

@djpjax.pjaxtend('parent.html', 'parent-pjax.html')
def view_custom_parent_pjaxtend(request):
    return TemplateResponse(request, "template.html", {})

@djpjax.pjaxtend('parent.html', 'parent-pjax.html', 'my_parent')
def view_custom_context_pjaxtend(request):
    return TemplateResponse(request, "template.html", {})

class NoPJAXTemplateVew(djpjax.PJAXResponseMixin, View):
    template_name = 'template.html'

    def get(self, request):
        return self.render_to_response({})

class SillyTemplateNameView(djpjax.PJAXResponseMixin, View):
    template_name = 'silly'

    def get(self, request):
        return self.render_to_response({})

class PJAXTemplateView(djpjax.PJAXResponseMixin, View):
    template_name = 'template.html'
    pjax_template_name = 'pjax.html'
    
    def get(self, request):
        return self.render_to_response({})

########NEW FILE########
