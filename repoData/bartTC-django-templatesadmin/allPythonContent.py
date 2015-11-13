__FILENAME__ = dotbackupfiles
from shutil import copy

from django import forms
from django.utils.translation import ugettext_lazy as _

from templatesadmin.edithooks import TemplatesAdminHook
from templatesadmin import TemplatesAdminException

class DotBackupFilesHook(TemplatesAdminHook):
    '''
    Backup File before saving
    '''

    @classmethod
    def pre_save(cls, request, form, template_path):
        backup = form.cleaned_data['backup']

        if not backup:
            return None

        try:
            copy(template_path, '%s.backup' % template_path)
        except IOError, e:
            raise TemplatesAdminException(
                _(u'Backup Template "%(path)s" has not been saved! Reason: %(errormsg)s' % {
                    'path': template_path,
                    'errormsg': e
                })
            )

        return "Backup \'%s.backup\' has been saved." % template_path

    @classmethod
    def contribute_to_form(cls, template_path):
        return dict(backup=forms.BooleanField(
            label = _('Backup file before saving?'),
            required = False,
        ))

########NEW FILE########
__FILENAME__ = gitcommit
from django import forms
from django.utils.translation import ugettext_lazy as _
from templatesadmin import TemplatesAdminException
from templatesadmin.edithooks import TemplatesAdminHook

import subprocess
import os

class GitCommitHook(TemplatesAdminHook):
    '''
    Commit to git after saving
    '''

    @classmethod
    def post_save(cls, request, form, template_path):
        dir, file = os.path.dirname(template_path) + "/", os.path.basename(template_path)

        if request.user.first_name and request.user.last_name:
            author = "%s %s" % (request.user.first_name, request.user.last_name)
        else:
            author = request.user.username

        message = form.cleaned_data['commitmessage'] or '--'

        command = (
            'GIT_COMMITTER_NAME="%(author)s" GIT_COMMITER_EMAIL="%(email)s" '
            'GIT_AUTHOR_NAME="%(author)s" GIT_AUTHOR_EMAIL="%(email)s" '
            'git commit -F - -- %(file)s'
        ) % {
          'file': template_path,
          'author': author,
          'email': request.user.email,
        }

        # Stolen from gitpython's git/cmd.py
        proc = subprocess.Popen(
            args=command,
            shell=True,
            cwd=dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            proc.stdin.write(message.encode('utf-8'))
            proc.stdin.close()
            stderr_value = proc.stderr.read()
            stdout_value = proc.stdout.read()
            status = proc.wait()
        finally:
            proc.stderr.close()

        if status != 0:
            raise TemplatesAdminException("Error while executing %s: %s" % (command, stderr_value.rstrip(), ))

        return stdout_value.rstrip()

    @classmethod
    def contribute_to_form(cls, template_path):
        return dict(commitmessage=forms.CharField(
            widget=forms.TextInput(attrs={'size':'100'}),
            label = _('Change message'),
            required = False,
        ))

########NEW FILE########
__FILENAME__ = hgcommit
from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from templatesadmin import TemplatesAdminException
from templatesadmin.edithooks import TemplatesAdminHook

from mercurial import hg, ui, match
import os


TEMPLATESADMIN_HG_ROOT = getattr(
    settings,
    'TEMPLATESADMIN_HG_ROOT',
    None
)


class HgCommitHook(TemplatesAdminHook):
    '''
    Commit to git after saving
    '''

    @classmethod
    def post_save(cls, request, form, template_path):
        dir = os.path.dirname(template_path) + os.sep
        file = os.path.basename(template_path)

        if request.user.first_name and request.user.last_name:
            author = "%s %s" % (request.user.first_name, request.user.last_name)
        else:
            author = request.user.username

        message = form.cleaned_data['commitmessage'] or '--'

        path = TEMPLATESADMIN_HG_ROOT
        if path is None:
            for template_dir in settings.TEMPLATE_DIRS:
                if dir.startswith(template_dir):
                    if path is None or len(templare_dir)>len(path):
                        path = template_dir
        if path is None:
            raise TemplatesAdminException("Could not find template base directory")
        uio = ui.ui()
        uio.setconfig('ui', 'interactive', False)
        uio.setconfig('ui', 'report_untrusted', False)
        uio.setconfig('ui', 'quiet', True)
        repo = hg.repository(uio, path=path)
        filter = match.match(repo.root, dir, [file])
        repo.commit(match=filter, text=message, user="%s <%s>" % (author, request.user.email))

        return "Template '%s' was committed succesfully into mercurial repository." % file

    @classmethod
    def contribute_to_form(cls, template_path):
        return dict(commitmessage=forms.CharField(
            widget=forms.TextInput(attrs={'size':'100'}),
            label = _('Change message'),
            required = False,
        ))

########NEW FILE########
__FILENAME__ = forms
from django import forms

class TemplateForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea()
    )

########NEW FILE########
__FILENAME__ = templatesadmin_tags
from os import path
from django.template import Library

register = Library()

@register.filter
def shortenfilepath(path, num_dirs=2, pathsep='/'):
    splitted = path.split(path)[1]
    return pathsep.join(path.split(pathsep)[-num_dirs:])

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'templatesadmin.views.listing', name='templatesadmin-overview'),
    url(r'^edit(?P<path>.*)/$', 'templatesadmin.views.modify', name='templatesadmin-edit'),
)

########NEW FILE########
__FILENAME__ = views
import os
import codecs
from datetime import datetime
from stat import ST_MTIME, ST_CTIME
from re import search

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.loaders.app_directories import app_template_dirs
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache

from templatesadmin.forms import TemplateForm
from templatesadmin import TemplatesAdminException

# Default settings that may be overriden by global settings (settings.py)
TEMPLATESADMIN_VALID_FILE_EXTENSIONS = getattr(
    settings,
    'TEMPLATESADMIN_VALID_FILE_EXTENSIONS',
    ('html', 'htm', 'txt', 'css', 'backup',)
)

TEMPLATESADMIN_GROUP = getattr(
    settings,
    'TEMPLATESADMIN_GROUP',
    'TemplateAdmins'
)

TEMPLATESADMIN_EDITHOOKS = getattr(
    settings,
    'TEMPLATESADMIN_EDITHOOKS',
    ('templatesadmin.edithooks.dotbackupfiles.DotBackupFilesHook', )
)

TEMPLATESADMIN_HIDE_READONLY = getattr(
    settings,
    'TEMPLATESADMIN_HIDE_READONLY',
    False
)

if str == type(TEMPLATESADMIN_EDITHOOKS):
    TEMPLATESADMIN_EDITHOOKS = (TEMPLATESADMIN_EDITHOOKS,)

_hooks = []

for path in TEMPLATESADMIN_EDITHOOKS:
    # inspired by django.template.context.get_standard_processors
    i = path.rfind('.')
    module, attr = path[:i], path[i+1:]
    try:
        mod = __import__(module, {}, {}, [attr])
    except ImportError, e:
        raise ImproperlyConfigured('Error importing edithook module %s: "%s"' % (module, e))
    try:
        func = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define a "%s" callable request processor' % (module, attr))

    _hooks.append(func)

TEMPLATESADMIN_EDITHOOKS = tuple(_hooks)

_fixpath = lambda path: os.path.abspath(os.path.normpath(path))

TEMPLATESADMIN_TEMPLATE_DIRS = getattr(
    settings,
    'TEMPLATESADMIN_TEMPLATE_DIRS', [
        d for d in list(settings.TEMPLATE_DIRS) + \
        list(app_template_dirs) if os.path.isdir(d)
    ]
)

TEMPLATESADMIN_TEMPLATE_DIRS = [_fixpath(dir) for dir in TEMPLATESADMIN_TEMPLATE_DIRS]

def user_in_templatesadmin_group(user):
    try:
        user.groups.get(name=TEMPLATESADMIN_GROUP)
        return True
    except ObjectDoesNotExist:
        return False

@never_cache
@user_passes_test(lambda u: user_in_templatesadmin_group(u))
@login_required
def listing(request,
             template_name='templatesadmin/overview.html',
             available_template_dirs=TEMPLATESADMIN_TEMPLATE_DIRS):

    template_dict = []
    for templatedir in available_template_dirs:
        for root, dirs, files in os.walk(templatedir):
            for f in sorted([f for f in files if f.rsplit('.')[-1] \
                      in TEMPLATESADMIN_VALID_FILE_EXTENSIONS]):
                full_path = os.path.join(root, f)
                l = {
                     'templatedir': templatedir,
                     'rootpath': root,
                     'abspath': full_path,
                     'modified': datetime.fromtimestamp(os.stat(full_path)[ST_MTIME]),
                     'created': datetime.fromtimestamp(os.stat(full_path)[ST_CTIME]),
                     'writeable': os.access(full_path, os.W_OK)
                }

                # Do not fetch non-writeable templates if settings set.
                if (TEMPLATESADMIN_HIDE_READONLY == True and \
                    l['writeable'] == True) or \
                   TEMPLATESADMIN_HIDE_READONLY == False:
                    try:
                        template_dict += (l,)
                    except KeyError:
                        template_dict = (l,)

    template_context = {
        'messages': request.user.get_and_delete_messages(),
        'template_dict': template_dict,
        'ADMIN_MEDIA_PREFIX': settings.ADMIN_MEDIA_PREFIX,
    }

    return render_to_response(template_name, template_context,
                              RequestContext(request))
@never_cache
@user_passes_test(lambda u: user_in_templatesadmin_group(u))
@login_required
def modify(request,
           path,
           template_name='templatesadmin/edit.html',
           base_form=TemplateForm,
           available_template_dirs=TEMPLATESADMIN_TEMPLATE_DIRS):

    template_path = _fixpath(path)

    # Check if file is within template-dirs
    if not any([template_path.startswith(templatedir) for templatedir in available_template_dirs]):
        request.user.message_set.create(message=_('Sorry, that file is not available for editing.'))
        return HttpResponseRedirect(reverse('templatesadmin-overview'))

    if request.method == 'POST':
        formclass = base_form
        for hook in TEMPLATESADMIN_EDITHOOKS:
            formclass.base_fields.update(hook.contribute_to_form(template_path))

        form = formclass(request.POST)
        if form.is_valid():
            content = form.cleaned_data['content']

            try:
                for hook in TEMPLATESADMIN_EDITHOOKS:
                    pre_save_notice = hook.pre_save(request, form, template_path)
                    if pre_save_notice:
                        request.user.message_set.create(message=pre_save_notice)
            except TemplatesAdminException, e:
                request.user.message_set.create(message=e.message)
                return HttpResponseRedirect(request.build_absolute_uri())

            # Save the template
            try:
                f = open(template_path, 'r')
                file_content = f.read()
                f.close()

                # browser tend to strip newlines from <textarea/>s before
                # HTTP-POSTing: re-insert them if neccessary

                # content is in dos-style lineending, will be converted in next step
                if (file_content[-1] == '\n' or file_content[:-2] == '\r\n') \
                   and content[:-2] != '\r\n':
                    content = u"%s\r\n" % content

                # Template is saved in unix-style, save in unix style.
                if None == search("\r\n", file_content):
                    content = content.replace("\r\n", "\n")

                f = codecs.open(template_path, 'w', 'utf-8')
                f.write(content)
                f.close()
            except IOError, e:
                request.user.message_set.create(
                    message=_('Template "%(path)s" has not been saved! Reason: %(errormsg)s' % {
                        'path': path,
                        'errormsg': e
                    })
                )
                return HttpResponseRedirect(request.build_absolute_uri())

            try:
                for hook in TEMPLATESADMIN_EDITHOOKS:
                    post_save_notice = hook.post_save(request, form, template_path)
                    if post_save_notice:
                        request.user.message_set.create(message=post_save_notice)
            except TemplatesAdminException, e:
                request.user.message_set.create(message=e.message)
                return HttpResponseRedirect(request.build_absolute_uri())

            request.user.message_set.create(
                message=_('Template "%s" was saved successfully.' % path)
            )
            return HttpResponseRedirect(reverse('templatesadmin-overview'))
    else:
        template_file = codecs.open(template_path, 'r', 'utf-8').read()

        formclass = TemplateForm
        for hook in TEMPLATESADMIN_EDITHOOKS:
            formclass.base_fields.update(hook.contribute_to_form(template_path))

        form = formclass(
            initial={'content': template_file}
        )

    template_context = {
        'messages': request.user.get_and_delete_messages(),
        'form': form,
        'short_path': path,
        'template_path': path,
        'template_writeable': os.access(template_path, os.W_OK),
        'ADMIN_MEDIA_PREFIX': settings.ADMIN_MEDIA_PREFIX,
    }

    return render_to_response(template_name, template_context,
                              RequestContext(request))

# For backwards compatibility and secure out-of-the-box views
overview = user_passes_test(lambda u: user_in_templatesadmin_group(u))(login_required(listing))
edit = user_passes_test(lambda u: user_in_templatesadmin_group(u))(login_required(modify))

########NEW FILE########
