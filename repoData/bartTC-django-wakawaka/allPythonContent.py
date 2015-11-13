__FILENAME__ = admin
from django.contrib import admin
from wakawaka.models import WikiPage, Revision

class RevisionInlines(admin.TabularInline):
    model = Revision
    extra = 1

class WikiPageAdmin(admin.ModelAdmin):
    inlines = [RevisionInlines]

class RevisionAdmin(admin.ModelAdmin):
    pass

admin.site.register(WikiPage, WikiPageAdmin)
admin.site.register(Revision, RevisionAdmin)
########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _, ugettext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from wakawaka.models import Revision, WikiPage

class WikiPageForm(forms.Form):
    content = forms.CharField(label=_('Content'), widget=forms.Textarea(attrs={'rows': 30}))
    message = forms.CharField(label=_('Change message (optional)'), widget=forms.TextInput, required=False)

    def save(self, request, page, *args, **kwargs):
        Revision.objects.create(
            page=page,
            creator=request.user,
            creator_ip=request.META['REMOTE_ADDR'],
            content = self.cleaned_data['content'],
            message = self.cleaned_data['message']
        )

DELETE_CHOICES = (

)

class DeleteWikiPageForm(forms.Form):
    delete = forms.ChoiceField(label=_('Delete'), choices=())

    def __init__(self, request, *args, **kwargs):
        '''
        Override the __init__ to display only delete choices the user has
        permission for.
        '''
        self.base_fields['delete'].choices = []
        if request.user.has_perm('wakawaka.delete_revision'):
            self.base_fields['delete'].choices.append(('rev', _('Delete this revision')),)

        if request.user.has_perm('wakawaka.delete_revision') and \
           request.user.has_perm('wakawaka.delete_wikipage'):
            self.base_fields['delete'].choices.append(('page', _('Delete the page with all revisions')),)

        super(DeleteWikiPageForm, self).__init__(*args, **kwargs)

    def _delete_page(self, page):
        page.delete()

    def _delete_revision(self, rev):
        rev.delete()

    def delete_wiki(self, request, page, rev):
        """
        Deletes the page with all revisions or the revision, based on the
        users choice.

        Returns a HttpResponseRedirect.
        """

        # Delete the page
        if self.cleaned_data.get('delete') == 'page' and \
           request.user.has_perm('wakawaka.delete_revision') and \
           request.user.has_perm('wakawaka.delete_wikipage'):
            self._delete_page(page)
            messages.success(request, ugettext('The page %s was deleted' % page.slug))
            return HttpResponseRedirect(reverse('wakawaka_index'))

        # Revision handling
        if self.cleaned_data.get('delete') == 'rev':

            revision_length = len(page.revisions.all())

            # Delete the revision if there are more than 1 and the user has permission
            if revision_length > 1 and request.user.has_perm('wakawaka.delete_revision'):
                self._delete_revision(rev)
                messages.success(request, ugettext('The revision for %s was deleted' % page.slug))
                return HttpResponseRedirect(reverse('wakawaka_page', kwargs={'slug': page.slug}))

            # Do not allow deleting the revision, if it's the only one and the user
            # has no permisson to delete the page.
            if revision_length <= 1 and \
               not request.user.has_perm('wakawaka.delete_wikipage'):
               messages.error(request, ugettext('You can not delete this revison for %s because it\'s the only one and you have no permission to delete the whole page.' % page.slug))
               return HttpResponseRedirect(reverse('wakawaka_page', kwargs={'slug': page.slug}))

            # Delete the page and the revision if the user has both permissions
            if revision_length <= 1 and \
               request.user.has_perm('wakawaka.delete_revision') and \
               request.user.has_perm('wakawaka.delete_wikipage'):
                self._delete_page(page)
                messages.success(request, ugettext('The page for %s was deleted because you deleted the only revision' % page.slug))
                return HttpResponseRedirect(reverse('wakawaka_index'))

        return None



########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic


class WikiPage(models.Model):
    slug = models.CharField(_('slug'), max_length=255)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    modified = models.DateTimeField(_('modified'), auto_now=True)

    content_type = models.ForeignKey(ContentType, null=True)
    object_id = models.PositiveIntegerField(null=True)
    group = generic.GenericForeignKey("content_type", "object_id")

    class Meta:
        verbose_name = _("Wiki page")
        verbose_name_plural = _("Wiki pages")
        ordering = ['slug']

    def __unicode__(self):
        return self.slug

    @property
    def current(self):
        return self.revisions.latest()

    @property
    def rev(self, rev_id):
        return self.revisions.get(pk=rev_id)

class Revision(models.Model):
    page = models.ForeignKey(WikiPage, related_name='revisions')
    content = models.TextField(_('content'))
    message = models.TextField(_('change message'), blank=True)
    creator = models.ForeignKey(User, blank=True, null=True, related_name='wakawaka_revisions')
    creator_ip = models.IPAddressField(_('creator ip'))
    created = models.DateTimeField(_('created'), auto_now_add=True)
    modified = models.DateTimeField(_('modified'), auto_now=True)

    class Meta:
        verbose_name = _("Revision")
        verbose_name_plural = _("Revisions")
        ordering = ['-modified']
        get_latest_by = 'modified'

    def __unicode__(self):
        return ugettext('Revision %(created)s for %(page_slug)s') % {
            'created': self.created.strftime('%Y%m%d-%H%M'),
            'page_slug': self.page.slug,
        }


########NEW FILE########
__FILENAME__ = wakawaka_tags
# from http://open.e-scribe.com/browser/python/django/apps/protowiki/templatetags/wikitags.py
# copyright Paul Bissex, MIT license
import re
from django.core.exceptions import ObjectDoesNotExist
from django.template import Library, Node, Variable
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from wakawaka.models import WikiPage
from wakawaka.urls import WIKI_SLUG

register = Library()

WIKI_WORDS_REGEX = re.compile(r'\b%s\b' % WIKI_SLUG, re.UNICODE)


def replace_wikiwords(value, group=None):
    def replace_wikiword(m):
        slug = m.group(1)
        try:
            page = WikiPage.objects.get(slug=slug)
            kwargs = {
                'slug': slug,
            }
            if group:
                url = group.content_bridge.reverse('wakawaka_page', group, kwargs=kwargs)
            else:
                url = reverse('wakawaka_page', kwargs=kwargs)
            return r'<a href="%s">%s</a>' % (url, slug)
        except ObjectDoesNotExist:
            kwargs = {
                'slug': slug,
            }
            if group:
                url = group.content_bridge.reverse('wakawaka_edit', group, kwargs=kwargs)
            else:
                url = reverse('wakawaka_edit', kwargs=kwargs)
            return r'<a class="doesnotexist" href="%s">%s</a>' % (url, slug)
    return mark_safe(WIKI_WORDS_REGEX.sub(replace_wikiword, value))


@register.filter
def wikify(value):
    """Makes WikiWords"""
    return replace_wikiwords(value)


class WikifyContentNode(Node):
    def __init__(self, content_expr, group_var):
        self.content_expr = content_expr
        self.group_var = Variable(group_var)
    
    def render(self, context):
        content = self.content_expr.resolve(context)
        group = self.group_var.resolve(context)
        return replace_wikiwords(content, group)

@register.tag
def wikify_content(parser, token):
    bits = token.split_contents()
    try:
        group_var = bits[2]
    except IndexError:
        group_var = None
    return WikifyContentNode(parser.compile_filter(bits[1]), group_var)

########NEW FILE########
__FILENAME__ = authenticated
from django.contrib.auth.decorators import login_required
from wakawaka.urls import urlpatterns

for waka_url in urlpatterns:
    callback = waka_url.callback
    waka_url._callback = login_required(callback)
########NEW FILE########
__FILENAME__ = views
import difflib
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.http import Http404, HttpResponseRedirect, HttpResponseBadRequest,\
    HttpResponseNotFound, HttpResponseForbidden
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext, ugettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist
from wakawaka.forms import WikiPageForm, DeleteWikiPageForm
from wakawaka.models import WikiPage, Revision

__all__ = ['index', 'page', 'edit', 'revisions', 'changes', 'revision_list', 'page_list']

def index(request, template_name='wakawaka/page.html'):
    '''
    Redirects to the default wiki index name.
    '''
    kwargs = {
        'slug': getattr(settings, 'WAKAWAKA_DEFAULT_INDEX', 'WikiIndex'),
    }
    # be group aware
    group = getattr(request, "group", None)
    if group:
        redirect_to = request.bridge.reverse('wakawaka_page', group, kwargs=kwargs)
    else:
        redirect_to = reverse('wakawaka_page', kwargs=kwargs)
    return HttpResponseRedirect(redirect_to)

def page(request, slug, rev_id=None, template_name='wakawaka/page.html', extra_context=None):
    '''
    Displays a wiki page. Redirects to the edit view if the page doesn't exist.
    '''
    if extra_context is None:
        extra_context = {}

    # be group aware
    group = getattr(request, "group", None)
    if group:
        bridge = request.bridge
        group_base = bridge.group_base_template()
    else:
        bridge = None
        group_base = None

    try:
        if group:
            queryset = group.content_objects(WikiPage)
        else:
            queryset = WikiPage.objects.all()
        page = queryset.get(slug=slug)
        rev = page.current

        # Display an older revision if rev_id is given
        if rev_id:
            if group:
                revision_queryset = group.content_objects(Revision, join="page")
            else:
                revision_queryset = Revision.objects.all()
            rev_specific = revision_queryset.get(pk=rev_id)
            if rev.pk != rev_specific.pk:
                rev_specific.is_not_current = True
            rev = rev_specific

    # The Page does not exist, redirect to the edit form or
    # deny, if the user has no permission to add pages
    except WikiPage.DoesNotExist:
        if request.user.is_authenticated():
            kwargs = {
                'slug': slug,
            }
            if group:
                redirect_to = bridge.reverse('wakawaka_edit', group, kwargs=kwargs)
            else:
                redirect_to = reverse('wakawaka_edit', kwargs=kwargs)
            return HttpResponseRedirect(redirect_to)
        raise Http404
    template_context = {
        'page': page,
        'rev': rev,
        'group': group,
        'group_base': group_base,
    }
    template_context.update(extra_context)
    return render_to_response(template_name, template_context,
                              RequestContext(request))


def edit(request, slug, rev_id=None, template_name='wakawaka/edit.html',
         extra_context=None, wiki_page_form=WikiPageForm,
         wiki_delete_form=DeleteWikiPageForm):
    '''
    Displays the form for editing and deleting a page.
    '''
    if extra_context is None:
        extra_context = {}

    # be group aware
    group = getattr(request, "group", None)
    if group:
        bridge = request.bridge
        group_base = bridge.group_base_template()
    else:
        bridge = None
        group_base = None
    # Get the page for slug and get a specific revision, if given
    try:
        if group:
            queryset = group.content_objects(WikiPage)
        else:
            queryset = WikiPage.objects.all()
        page = queryset.get(slug=slug)
        rev = page.current
        initial = {'content': page.current.content}

        # Do not allow editing wiki pages if the user has no permission
        if not request.user.has_perms(('wakawaka.change_wikipage', 'wakawaka.change_revision' )):
            return HttpResponseForbidden(ugettext('You don\'t have permission to edit pages.'))

        if rev_id:
            # There is a specific revision, fetch this
            rev_specific = Revision.objects.get(pk=rev_id)
            if rev.pk != rev_specific.pk:
                rev = rev_specific
                rev.is_not_current = True
                initial = {'content': rev.content, 'message': _('Reverted to "%s"' % rev.message)}


    # This page does not exist, create a dummy page
    # Note that it's not saved here
    except WikiPage.DoesNotExist:
        
        # Do not allow adding wiki pages if the user has no permission
        if not request.user.has_perms(('wakawaka.add_wikipage', 'wakawaka.add_revision',)):
            return HttpResponseForbidden(ugettext('You don\'t have permission to add wiki pages.'))

        page = WikiPage(slug=slug)
        page.is_initial = True
        rev = None
        initial = {'content': _('Describe your new page %s here...' % slug),
                   'message': _('Initial revision')}

    # Don't display the delete form if the user has nor permission
    delete_form = None
    # The user has permission, then do
    if request.user.has_perm('wakawaka.delete_wikipage') or \
       request.user.has_perm('wakawaka.delete_revision'):
        delete_form = wiki_delete_form(request)
        if request.method == 'POST' and request.POST.get('delete'):
            delete_form = wiki_delete_form(request, request.POST)
            if delete_form.is_valid():
                return delete_form.delete_wiki(request, page, rev)

    # Page add/edit form
    form = wiki_page_form(initial=initial)
    if request.method == 'POST':
        form = wiki_page_form(data=request.POST)
        if form.is_valid():
            # Check if the content is changed, except there is a rev_id and the
            # user possibly only reverted the HEAD to it
            if not rev_id and initial['content'] == form.cleaned_data['content']:
                form.errors['content'] = (_('You have made no changes!'),)

            # Save the form and redirect to the page view
            else:
                try:
                    # Check that the page already exist
                    if group:
                        queryset = group.content_objects(WikiPage)
                    else:
                        queryset = WikiPage.objects.all()
                    page = queryset.get(slug=slug)
                except WikiPage.DoesNotExist:
                    # Must be a new one, create that page
                    page = WikiPage(slug=slug)
                    if group:
                        page = group.associate(page, commit=False)
                    page.save()

                form.save(request, page)
                
                kwargs = {
                    'slug': page.slug,
                }
                
                if group:
                    redirect_to = bridge.reverse('wakawaka_page', group, kwargs=kwargs)
                else:
                    redirect_to = reverse('wakawaka_page', kwargs=kwargs)
                messages.success(request, ugettext('Your changes to %s were saved' % page.slug))
                return HttpResponseRedirect(redirect_to)

    template_context = {
        'form': form,
        'delete_form': delete_form,
        'page': page,
        'rev': rev,
        'group': group,
        'group_base': group_base,
    }
    template_context.update(extra_context)
    return render_to_response(template_name, template_context,
                              RequestContext(request))

def revisions(request, slug, template_name='wakawaka/revisions.html', extra_context=None):
    '''
    Displays the list of all revisions for a specific WikiPage
    '''
    if extra_context is None:
        extra_context = {}

    # be group aware
    group = getattr(request, "group", None)
    if group:
        bridge = request.bridge
        group_base = bridge.group_base_template()
    else:
        bridge = None
        group_base = None

    if group:
        queryset = group.content_objects(WikiPage)
    else:
        queryset = WikiPage.objects.all()
    page = get_object_or_404(queryset, slug=slug)

    template_context = {
        'page': page,
        'group': group,
        'group_base': group_base,
    }
    template_context.update(extra_context)
    return render_to_response(template_name, template_context,
                              RequestContext(request))

def changes(request, slug, template_name='wakawaka/changes.html', extra_context=None):
    '''
    Displays the changes between two revisions.
    '''
    
    if extra_context is None:
        extra_context = {}

    # be group aware
    group = getattr(request, "group", None)
    if group:
        bridge = request.bridge
        group_base = bridge.group_base_template()
    else:
        bridge = None
        group_base = None

    rev_a_id = request.GET.get('a', None)
    rev_b_id = request.GET.get('b', None)

    # Some stinky fingers manipulated the url
    if not rev_a_id or not rev_b_id:
        return HttpResponseBadRequest('Bad Request')

    try:
        if group:
            revision_queryset = group.content_objects(Revision, join="page")
            wikipage_queryset = group.content_objects(WikiPage)
        else:
            revision_queryset = Revision.objects.all()
            wikipage_queryset = WikiPage.objects.all()
        rev_a = revision_queryset.get(pk=rev_a_id)
        rev_b = revision_queryset.get(pk=rev_b_id)
        page = wikipage_queryset.get(slug=slug)
    except ObjectDoesNotExist:
        raise Http404

    if rev_a.content != rev_b.content:
        d = difflib.unified_diff(rev_b.content.splitlines(),
                                 rev_a.content.splitlines(),
                                 'Original', 'Current', lineterm='')
        difftext = '\n'.join(d)
    else:
        difftext = _(u'No changes were made between this two files.')

    template_context = {
        'page': page,
        'diff': difftext,
        'rev_a': rev_a,
        'rev_b': rev_b,
        'group': group,
        'group_base': group_base,
    }
    template_context.update(extra_context)
    return render_to_response(template_name, template_context,
                              RequestContext(request))

# Some useful views
def revision_list(request, template_name='wakawaka/revision_list.html', extra_context=None):
    '''
    Displays a list of all recent revisions.
    '''
    if extra_context is None:
        extra_context = {}

    # be group aware
    group = getattr(request, "group", None)
    if group:
        bridge = request.bridge
        group_base = bridge.group_base_template()
    else:
        bridge = None
        group_base = None

    if group:
        revision_list = group.content_objects(Revision, join="page")
    else:
        revision_list = Revision.objects.all()

    template_context = {
        'revision_list': revision_list,
        'group': group,
        'group_base': group_base,
    }
    template_context.update(extra_context)
    return render_to_response(template_name, template_context,
                              RequestContext(request))

def page_list(request, template_name='wakawaka/page_list.html', extra_context=None):
    '''
    Displays all Pages
    '''
    if extra_context is None:
        extra_context = {}

    # be group aware
    group = getattr(request, "group", None)
    if group:
        bridge = request.bridge
        group_base = bridge.group_base_template()
    else:
        bridge = None
        group_base = None

    if group:
        page_list = group.content_objects(WikiPage)
    else:
        page_list = WikiPage.objects.all()
    page_list = page_list.order_by('slug')

    template_context = {
        'page_list': page_list,
        'index_slug': getattr(settings, 'WAKAWAKA_DEFAULT_INDEX', 'WikiIndex'),
        'group': group,
        'group_base': group_base,
    }
    template_context.update(extra_context)
    return render_to_response(template_name, template_context,
                              RequestContext(request))
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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
# Django settings for wakawaka_project project.
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

APPEND_SLASH = False

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_ROOT, 'dev.db'),
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
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

STATIC_URL = '/static/'

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin_media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'oqyozs+&notx&0ik!-$p0u%b5rg7bwt594fdaatu^1ykop^fr0'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
	'django.template.loaders.filesystem.Loader',
	'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'wakawaka_project.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'wakawaka',
)

LOGIN_URL = '/accounts/login/'
LOGOUT_URL = '/accounts/logout/'
LOGIN_REDIRECT_URL = '/'

try:
    from settings_local import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib.auth.views import login, logout
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),

    url('^accounts/login/$', login, name='auth_login'),
    url('^accounts/logout/$', logout, name='auth_logout'),

    # Include the wacky wakawaka urls
    (r'^', include('wakawaka.urls')),

    # If all pages are only for authenticated users, import this urlconf instead
    #(r'^', include('wakawaka.urls.authenticated')),
)

urlpatterns += staticfiles_urlpatterns()
########NEW FILE########
