__FILENAME__ = settings
import os
from django.conf import settings

# PLEASE: Don't change anything here, use your site settings.py

MEDIA_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'media')
MEDIA_PREFIX = getattr(settings, 'MOBILEADMIN_MEDIA_PREFIX', '/mobileadmin_media/')
MEDIA_REGEX = r'^%s(?P<path>.*)$' % MEDIA_PREFIX.lstrip('/')

USER_AGENTS = {
    'mobile_safari': r'AppleWebKit/.*Mobile/',
    'blackberry': r'^BlackBerry',
    'opera_mini': r'[Oo]pera [Mm]ini',
}
USER_AGENTS.update(getattr(settings, 'MOBILEADMIN_USER_AGENTS', {}))

TEMPLATE_MAPPING = {
    'index': ('index_template', 'index.html'),
    'display_login_form': ('login_template', 'login.html'),
    'app_index': ('app_index_template', 'app_index.html'),
    'render_change_form': ('change_form_template', 'change_form.html'),
    'changelist_view': ('change_list_template', 'change_list.html'),
    'delete_view': ('delete_confirmation_template', 'delete_confirmation.html'),
    'history_view': ('object_history_template', 'object_history.html'),
    'logout': ('logout_template', 'registration/logged_out.html'),
    'password_change': ('password_change_template', 'registration/password_change_form.html'),
    'password_change_done': ('password_change_done_template', 'registration/password_change_done.html'),
}
TEMPLATE_MAPPING.update(getattr(settings, 'MOBILEADMIN_TEMPLATE_MAPPING', {}))

########NEW FILE########
__FILENAME__ = context_processors
from mobileadmin.utils import get_user_agent

def user_agent(request):
    return {'user_agent': get_user_agent(request)}

########NEW FILE########
__FILENAME__ = decorators
from mobileadmin.conf import settings
from mobileadmin.utils import get_user_agent

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.

def mobile_templates(function):
    """
    Decorator to be used on ``AdminSite`` or ``ModelAdmin`` methods that
    changes the template of that method according to the current user agent
    by using a template mapping.
    """
    func_name = function.__name__

    def _change_templates(self, request, *args, **kwargs):
        if func_name in settings.TEMPLATE_MAPPING:
            path_list = []
            attr_name, template_name = settings.TEMPLATE_MAPPING[func_name]
            user_agent = get_user_agent(request)
            params = dict(template_name=template_name)
            if user_agent:
                params.update(user_agent=user_agent)
                path_list += [
                    'mobileadmin/%(user_agent)s/%(template_name)s',
                    'mobileadmin/%(template_name)s',
                ]
                # if self is a ModelAdmin instance add more of the default
                # templates as fallback
                if getattr(self, 'model', False):
                    opts = self.model._meta
                    params.update(dict(app_label=opts.app_label,
                        object_name=opts.object_name.lower()))
                    path_list = [
                        'mobileadmin/%(user_agent)s/%(app_label)s/%(object_name)s/%(template_name)s',
                        'mobileadmin/%(user_agent)s/%(app_label)s/%(template_name)s',
                    ] + path_list + [
                        'admin/%(app_label)s/%(object_name)s/%(template_name)s',
                        'admin/%(app_label)s/%(template_name)s',
                    ]
                path_list += [
                    'admin/%(template_name)s',
                    '%(template_name)s',
                ]
            else:
                path_list += [
                    'admin/%(template_name)s',
                    '%(template_name)s',
                ]
            setattr(self, attr_name, [path % params for path in path_list])
        return function(self, request, *args, **kwargs)
    return wraps(function)(_change_templates)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = options
from django.contrib.admin import options
from mobileadmin import decorators

class MobileModelAdmin(options.ModelAdmin):
    """
    A custom model admin class to override the used templates depending on the
    user agent of the request.
    
    Please use it in case you want to create you own mobileadmin.
    """
    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        return super(MobileModelAdmin, self).render_change_form(request, context, add, change, form_url, obj)
    render_change_form = decorators.mobile_templates(render_change_form)

    def changelist_view(self, request, extra_context=None):
        return super(MobileModelAdmin, self).changelist_view(request, extra_context)
    changelist_view = decorators.mobile_templates(changelist_view)

    def delete_view(self, request, object_id, extra_context=None):
        return super(MobileModelAdmin, self).delete_view(request, object_id, extra_context)
    delete_view = decorators.mobile_templates(delete_view)

    def history_view(self, request, object_id, extra_context=None):
        return super(MobileModelAdmin, self).history_view(request, object_id, extra_context)
    history_view = decorators.mobile_templates(history_view)

class MobileStackedInline(options.StackedInline):
    template = 'edit_inline/stacked.html'

class MobileTabularInline(options.InlineModelAdmin):
    template = 'edit_inline/tabular.html'

########NEW FILE########
__FILENAME__ = sites
from django.contrib.admin import sites
from django.views.decorators.cache import never_cache
from django.contrib.auth.views import password_change, password_change_done, logout

from mobileadmin.decorators import mobile_templates

class MobileAdminSite(sites.AdminSite):
    """
    A custom admin site to override the used templates.
    Add that to your urls.py:
    
    import mobileadmin
    urlpatterns += patterns('',
        (r'^m/(.*)', mobileadmin.site.root),
    )
    """
    logout_template = None
    password_change_template = None
    password_change_done_template = None

    def index(self, request, extra_context=None):
        return super(MobileAdminSite, self).index(request, extra_context)
    index = mobile_templates(index)
    
    def display_login_form(self, request, error_message='', extra_context=None):
        return super(MobileAdminSite, self).display_login_form(request, error_message, extra_context)
    display_login_form = mobile_templates(display_login_form)

    def app_index(self, request, app_label, extra_context=None):
        return super(MobileAdminSite, self).app_index(request, app_label, extra_context)
    app_index = mobile_templates(app_index)

    def logout(self, request):
        return logout(request, template_name=self.logout_template or 'registration/logged_out.html')
    logout = never_cache(mobile_templates(logout))

    def password_change(self, request):
        return password_change(request,
            template_name=self.password_change_template or 'registration/password_change_form.html',
            post_change_redirect='%spassword_change/done/' % self.root_path)
    password_change = mobile_templates(password_change)

    def password_change_done(self, request):
        return password_change_done(request,
            template_name=self.password_change_done_template or 'registration/password_change_done.html')
    password_change_done = mobile_templates(password_change_done)

site = MobileAdminSite()

########NEW FILE########
__FILENAME__ = mobile_admin_list
from django import template
from django.template.loader import render_to_string
from django.contrib.admin.views.main import ALL_VAR, PAGE_VAR, SEARCH_VAR

register = template.Library()

def paginator_number(cl, i):
    if i == cl.page_num:
        classname = "active"
    else:
        classname = "inactive"
    return u'<a href="%s" class="%s float-left">%d</a> ' % (cl.get_query_string({PAGE_VAR: i}), classname, i+1)
paginator_number = register.simple_tag(paginator_number)

def pagination(cl, user_agent):
    paginator, page_num = cl.paginator, cl.page_num

    pagination_required = (not cl.show_all or not cl.can_show_all) and cl.multi_page
    if not pagination_required:
        page_range = []
    else:
        ON_EACH_SIDE = 1

        # If there are 4 or fewer pages, display links to every page.
        # Otherwise, do some fancy
        if paginator.num_pages <= 3:
            page_range = range(paginator.num_pages)
        else:
            # Insert "smart" pagination links, so that there are always ON_ENDS
            # links at either end of the list of pages, and there are always
            # ON_EACH_SIDE links at either end of the "current page" link.
            page_range = []
            if page_num > ON_EACH_SIDE:
                page_range.extend(range(0, ON_EACH_SIDE - 1))
                page_range.extend(range(page_num - ON_EACH_SIDE, page_num + 1))
            else:
                page_range.extend(range(0, page_num + 1))
            if page_num < (paginator.num_pages - ON_EACH_SIDE - 1):
                page_range.extend(range(page_num + 1, page_num + ON_EACH_SIDE + 1))
                page_range.extend(range(paginator.num_pages, paginator.num_pages))
            else:
                page_range.extend(range(page_num + 1, paginator.num_pages))

    need_show_all_link = cl.can_show_all and not cl.show_all and cl.multi_page
    return render_to_string((
        'mobileadmin/%s/pagination.html' % user_agent,
        'mobileadmin/pagination.html',
        'admin/pagination.html'
    ), {
        'cl': cl,
        'pagination_required': pagination_required,
        'show_all_url': need_show_all_link and cl.get_query_string({ALL_VAR: ''}),
        'page_range': page_range,
        'ALL_VAR': ALL_VAR,
        '1': 1,
    })
register.simple_tag(pagination)

def search_form(cl, user_agent):
    return render_to_string((
        'mobileadmin/%s/search_form.html' % user_agent,
        'mobileadmin/search_form.html',
        'admin/search_form.html'
    ), {
        'cl': cl,
        'show_result_count': cl.result_count != cl.full_result_count and not cl.opts.one_to_one_field,
        'search_var': SEARCH_VAR
    })
register.simple_tag(search_form)

def admin_list_filter(cl, spec, user_agent):
    return render_to_string((
        'mobileadmin/%s/filter.html' % user_agent,
        'mobileadmin/filter.html',
        'admin/filter.html'
    ), {
        'title': spec.title(),
        'choices': list(spec.choices(cl)),
    })
register.simple_tag(admin_list_filter)

########NEW FILE########
__FILENAME__ = mobile_admin_media
from django.template import Library

register = Library()

def mobileadmin_media_prefix():
    """
    Returns the string contained in the setting MOBILEADMIN_MEDIA_PREFIX.
    """
    try:
        from mobileadmin.conf import settings
    except ImportError:
        return ''
    return settings.MEDIA_PREFIX
mobileadmin_media_prefix = register.simple_tag(mobileadmin_media_prefix)

########NEW FILE########
__FILENAME__ = mobile_admin_modify
import re
from django import template
from django.template.loader import render_to_string
register = template.Library()

admin_re = re.compile(r'^admin\/')

def prepopulated_fields_js(context):
    """
    Creates a list of prepopulated_fields that should render Javascript for
    the prepopulated fields for both the admin form and inlines.
    """
    prepopulated_fields = []
    if context['add'] and 'adminform' in context:
        prepopulated_fields.extend(context['adminform'].prepopulated_fields)
    if 'inline_admin_formsets' in context:
        for inline_admin_formset in context['inline_admin_formsets']:
            for inline_admin_form in inline_admin_formset:
                if inline_admin_form.original is None:
                    prepopulated_fields.extend(inline_admin_form.prepopulated_fields)
    context.update({'prepopulated_fields': prepopulated_fields})
    return context
prepopulated_fields_js = register.inclusion_tag('admin/prepopulated_fields_js.html', takes_context=True)(prepopulated_fields_js)

def mobile_inline_admin_formset(inline_admin_formset, user_agent):
    template_name = inline_admin_formset.opts.template
    if admin_re.match(template_name):
        # remove admin/ prefix to have a clean template name
        template_name = admin_re.sub('', template_name)
    return render_to_string((
        'mobileadmin/%s/%s' % (user_agent, template_name),
        'mobileadmin/%s' % template_name,
        'admin/%s' % template_name,
    ), {
        'inline_admin_formset': inline_admin_formset,
        'user_agent': user_agent,
    })
register.simple_tag(mobile_inline_admin_formset)

def mobile_inline_admin_fieldset(fieldset, user_agent):
    return render_to_string((
        'mobileadmin/%s/includes/fieldset.html' % user_agent,
        'mobileadmin/includes/fieldset.html',
        'admin/includes/fieldset.html',
    ), {
        'fieldset': fieldset,
    })
register.simple_tag(mobile_inline_admin_fieldset)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
import mobileadmin

urlpatterns = patterns('',
    (r'^(.*)', mobileadmin.site.root),
)

########NEW FILE########
__FILENAME__ = utils
import re
from mobileadmin.conf import settings

def get_user_agent(request):
    """
    Checks if the given user agent string matches one of the valid user
    agents.
    """
    name = request.META.get('HTTP_USER_AGENT', None)
    if not name:
        return False
    for platform, regex in settings.USER_AGENTS.iteritems():
        if re.compile(regex).search(name) is not None:
            return platform.lower()
    return False

########NEW FILE########
__FILENAME__ = views
from django import template
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponseServerError
from django.views import defaults
from django.shortcuts import render_to_response
from django.core.exceptions import PermissionDenied
from django.template import Context, RequestContext, loader
from django.utils.translation import ugettext, ugettext_lazy as _

from mobileadmin import utils

def auth_add_view(self, request):
    if not self.has_change_permission(request):
        raise PermissionDenied
    template_list = ['admin/auth/user/add_form.html']
    user_agent = utils.get_user_agent(request)
    if user_agent:
        template_list = [
            'mobileadmin/%s/auth/user/add_form.html' % user_agent,
        ] + template_list
    if request.method == 'POST':
        form = self.add_form(request.POST)
        if form.is_valid():
            new_user = form.save()
            msg = _('The %(name)s "%(obj)s" was added successfully.') % {'name': 'user', 'obj': new_user}
            self.log_addition(request, new_user)
            if "_addanother" in request.POST:
                request.user.message_set.create(message=msg)
                return HttpResponseRedirect(request.path)
            elif '_popup' in request.REQUEST:
                return self.response_add(request, new_user)
            else:
                request.user.message_set.create(message=msg + ' ' + ugettext("You may edit it again below."))
                return HttpResponseRedirect('../%s/' % new_user.id)
    else:
        form = self.add_form()
    return render_to_response(template_list, {
        'title': _('Add user'),
        'form': form,
        'is_popup': '_popup' in request.REQUEST,
        'add': True,
        'change': False,
        'has_add_permission': True,
        'has_delete_permission': False,
        'has_change_permission': True,
        'has_file_field': False,
        'has_absolute_url': False,
        'auto_populated_fields': (),
        'opts': self.model._meta,
        'save_as': False,
        'username_help_text': self.model._meta.get_field('username').help_text,
        'root_path': self.admin_site.root_path,
        'app_label': self.model._meta.app_label,
    }, context_instance=template.RequestContext(request))

def page_not_found(request, template_name='404.html'):
    """
    Mobile 404 handler.

    Templates: `404.html`
    Context:
        request_path
            The path of the requested URL (e.g., '/app/pages/bad_page/')
    """
    user_agent = utils.get_user_agent(request)
    if user_agent:
        template_list = (
            'mobileadmin/%s/404.html' % user_agent,
            template_name,
        )
        return HttpResponseNotFound(loader.render_to_string(template_list, {
            'request_path': request.path,
        }, context_instance=RequestContext(request)))
    return defaults.page_not_found(request, template_name)

def server_error(request, template_name='500.html'):
    """
    Mobile 500 error handler.

    Templates: `500.html`
    Context: None
    """
    user_agent = utils.get_user_agent(request)
    if user_agent:
        template_list = (
            'mobileadmin/%s/500.html' % user_agent,
            template_name,
        )
        return HttpResponseServerError(loader.render_to_string(template_list))
    return defaults.server_error(request, template_name)

########NEW FILE########
