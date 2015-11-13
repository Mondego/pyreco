__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

$Id$
"""

import os, shutil, sys, tempfile, urllib2
from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')

# parsing arguments
parser = OptionParser(
    'This is a custom version of the zc.buildout %prog script.  It is '
    'intended to meet a temporary need if you encounter problems with '
    'the zc.buildout 1.5 release.')
parser.add_option("-v", "--version", dest="version", default='1.4.4',
                          help='Use a specific zc.buildout version.  *This '
                          'bootstrap script defaults to '
                          '1.4.4, unlike usual buildpout bootstrap scripts.*')
parser.add_option("-d", "--distribute",
                   action="store_true", dest="distribute", default=False,
                   help="Use Disribute rather than Setuptools.")

parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

# if -c was provided, we push it back into args for buildout' main function
if options.config_file is not None:
    args += ['-c', options.config_file]

if options.version is not None:
    VERSION = '==%s' % options.version
else:
    VERSION = ''

USE_DISTRIBUTE = options.distribute
args = args + ['bootstrap']

to_reload = False
try:
    import pkg_resources
    if not hasattr(pkg_resources, '_distribute'):
        to_reload = True
        raise ImportError
except ImportError:
    ez = {}
    if USE_DISTRIBUTE:
        exec urllib2.urlopen('http://python-distribute.org/distribute_setup.py'
                         ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0, no_fake=True)
    else:
        exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                             ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    if to_reload:
        reload(pkg_resources)
    else:
        import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

ws  = pkg_resources.working_set

if USE_DISTRIBUTE:
    requirement = 'distribute'
else:
    requirement = 'setuptools'

env = dict(os.environ,
           PYTHONPATH=
           ws.find(pkg_resources.Requirement.parse(requirement)).location
           )

cmd = [quote(sys.executable),
       '-c',
       quote('from setuptools.command.easy_install import main; main()'),
       '-mqNxd',
       quote(tmpeggs)]

if 'bootstrap-testing-find-links' in os.environ:
    cmd.extend(['-f', os.environ['bootstrap-testing-find-links']])

cmd.append('zc.buildout' + VERSION)

if is_jython:
    import subprocess
    exitcode = subprocess.Popen(cmd, env=env).wait()
else: # Windows prefers this, apparently; otherwise we would prefer subprocess
    exitcode = os.spawnle(*([os.P_WAIT, sys.executable] + cmd + [env]))
assert exitcode == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout' + VERSION)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = addmenu
from Products.CMFCore.utils import getToolByName
from plone.app.z3cform.layout import wrap_form
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.namedfile.field import NamedFile
from plone.z3cform.interfaces import IWrappedForm
from z3c.form import button, form, field
from z3c.form.interfaces import HIDDEN_MODE
from zope import interface, schema
from zope.app.publisher.interfaces.browser import IBrowserMenu
from zope.component import getUtility, queryUtility, getMultiAdapter
from zope.container.interfaces import INameChooser
from zope.interface import implements
from zope.publisher.browser import BrowserView
from plone.app.cmsui.interfaces import _


class IAddNewContent(interface.Interface):

    title = schema.TextLine(title=_(u"Title"))
    type_name = schema.TextLine(title=_(u"Type"))


class AddNewContentForm(form.Form):
    
    fields = field.Fields(IAddNewContent)
    ignoreContext = True # don't use context to get widget data
    label = _(u"Add content")
    css_class = 'overlayForm'
    
    def update(self):
        tn = self.fields['type_name']
        tn.mode = HIDDEN_MODE
        tn.field.default = unicode(getattr(self.request, 'type_name', ''))
        super(AddNewContentForm, self).update()

    @button.buttonAndHandler(_(u'Add content'))
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            return
        
        title = data['title']
        
        # Generate a name based on the title..
        util = queryUtility(IIDNormalizer)
        id = util.normalize(title)
        
        # Context may not be a container, get one.
        context_state = getMultiAdapter((self.context, self.request), name="plone_context_state")
        container = context_state.folder()
        
        # Make sure our chosen id is unique, iterate until we get one that is.
        chooser = INameChooser(container)
        id = chooser._findUniqueName(id, None)

        # create the object
        type_name = data['type_name']
        container.invokeFactory(type_name, id=id, title=title)
        if type_name in [u'Folder']:
            self.request.response.redirect("%s/@@cmsui-structure" % container[id].absolute_url())
        else:
            self.request.response.redirect("%s/edit" % container[id].absolute_url())

AddNewContentView = wrap_form(AddNewContentForm)


class IFileUploadForm(interface.Interface):
    file = NamedFile(title=u"File")

class FileUploadForm(form.Form):
    implements(IWrappedForm)
    
    fields = field.Fields(IFileUploadForm)
    ignoreContext = True # don't use context to get widget data
    label = _(u"Add content")
    
    @button.buttonAndHandler(_(u'Upload content'))
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            return
            
        # Context may not be a container, get one.
        context_state = getMultiAdapter((self.context, self.request), name="plone_context_state")
        container = context_state.folder()

        title = data['file'].filename
        # Generate a name based on the title..
        util = queryUtility(IIDNormalizer)
        id = util.normalize(title)
        
        # Make sure our chosen id is unique, iterate until we get one that is.
        chooser = INameChooser(container)
        id = chooser._findUniqueName(id, None)

        # Determine the Content Type
        ct_reg = getToolByName(self.context, 'content_type_registry')
        typeName = ct_reg.findTypeName(data['file'].filename, 
                                       data['file'].contentType,
                                       data['file'].data)

        # Really, we want Image if it's an image, and File for everything else...
        typeName = 'Image' if typeName == 'Image' else 'File'

        # create the object
        container.invokeFactory(typeName, 
                                id=id,
                                title=title,
                                file=data['file'].data)

        # Redirect to the view page.
        self.request.response.redirect("%s/view" % container[id].absolute_url())


class AddMenu(BrowserView):
    """Add menu overlay
    """
    quickUploadTypes = ["File", "Image"]
    typeOrder = ["Document","Folder","Topic","News Item","Event"]
    
    
    def __call__(self):
        # Disable theming
        self.request.response.setHeader('X-Theme-Disabled', 'True')
        
        # Get this of types addable here, by this user.
        factoriesMenu = getUtility(IBrowserMenu, name='plone_contentmenu_factory', context=self.context)
        self.addable_types = factoriesMenu.getMenuItems(self.context, self.request)

        breadcrumbs_view = getMultiAdapter((self.context, self.request),
                                           name='breadcrumbs_view')
        self.breadcrumbs = breadcrumbs_view.breadcrumbs()
                
        self.uploadForm = FileUploadForm(self.context, self.request)
        self.uploadForm.update()
        
        
        return self.index()

    def allowedTypes(self,order=True):
        factories_view = getMultiAdapter((self.context, self.request), name='folder_factories')
        if not order:
            return factories_view.addable_types()
        allowedTypes = {}
        for t in factories_view.addable_types():
            allowedTypes[t['id']]=t
        allowedTypesKeys = allowedTypes.keys()
        allowedTypesResult = []
        for key in self.typeOrder:
            if key in allowedTypesKeys:
                allowedTypesResult.append(allowedTypes[key])
        for key in allowedTypesKeys:
            if key not in self.typeOrder:
                allowedTypesResult.append(allowedTypes[key])
        return allowedTypesResult
            
        
    def showUploadForm(self):
        """We can't show the upload form if uploadable types can't be created here.
        """
        # TODO How are we sure which types are uploadable?
        # For now, just check on File/Image.

        for a in self.allowedTypes(order=False):
            if a['id'] in self.quickUploadTypes:
                return True
        return False

    def getUploadUrl(self):
        """
        return upload url in current folder
        """
        ploneview = getMultiAdapter((self.context, self.request), name="plone")

        folder_url = ploneview.getCurrentFolderUrl()                      
        return '%s/@@quick_upload' %folder_url

    def getDataForUploadUrl(self):
        return 'data_url'

########NEW FILE########
__FILENAME__ = cmsuipersonalbarviewlet
from plone.app.layout.viewlets.common import PersonalBarViewlet
from AccessControl import getSecurityManager


class CMSUIPersonalBarViewlet(PersonalBarViewlet):
    
    def render(self):
        """
        If this user has permission to see the CMSUI viewlet, display that. 
        Otherwise, degrade to old school log in and log out
        """
        if getSecurityManager().checkPermission("plone.ViewCMSUI", self.context):
            return u""
        return PersonalBarViewlet.render(self)
########NEW FILE########
__FILENAME__ = menulink
from zope.viewlet.viewlet import ViewletBase

class MenuLinkViewlet(ViewletBase):
    
    def getLink(self):
        return self.context.absolute_url()+"/@@cmsui-menu"

########NEW FILE########
__FILENAME__ = nullviewlet
from zope.viewlet.viewlet import ViewletBase

class NullViewlet(ViewletBase):
    """Simply view that renders an empty string.
    
    For BBB purposes, to disable certain viewlets, we register an override
    for the same name and context, specific to the ICMSUILayer layer, using
    this class to render nothing.
    """
    
    def render(self):
        return u""

########NEW FILE########
__FILENAME__ = displayoptions
from zope.publisher.browser import BrowserView

class DisplayOptions(BrowserView):
    """Display options overlay
    """
    
    def __call__(self):
        # Disable theming
        self.request.response.setHeader('X-Theme-Disabled', 'True')
        return self.index()

########NEW FILE########
__FILENAME__ = fileupload
import mimetypes
import random
import urllib
from Acquisition import aq_inner
from ZPublisher.HTTPRequest import HTTPRequest

from interfaces import IQuickUploadFileFactory
from zope.component import getUtility

from Products.CMFCore.utils import getToolByName
from zope.publisher.browser import BrowserView
from zope.app.container.interfaces import INameChooser
from plone.i18n.normalizer.interfaces import IIDNormalizer

# from collective.quickupload import siteMessageFactory as _
# from collective.quickupload import logger

import json

def decodeQueryString(QueryString):
  """decode *QueryString* into a dictionary, as ZPublisher would do"""
  r= HTTPRequest(None,
         {'QUERY_STRING' : QueryString,
          'SERVER_URL' : '',
          },
         None,1)
  r.processInputs()
  return r.form

def getDataFromAllRequests(request, dataitem) :
    """
    Sometimes data is send using POST METHOD and QUERYSTRING
    """
    data = request.form.get(dataitem, None)
    if data is None:
        # try to get data from QueryString
        data = decodeQueryString(request.get('QUERY_STRING','')).get(dataitem)
    return data


class QuickUploadView(BrowserView):
    """ The Quick Upload View
    """
    
    def __init__(self, context, request):
        super(QuickUploadView, self).__init__(context, request)
        self.uploader_id = self._uploader_id()
    
    def _uploader_id(self) :
        return 'uploader%s' %str(random.random()).replace('.','')
    
    def _utranslate(self, msg):
        # XXX fixme : the _ (SiteMessageFactory) doesn't work
        context = aq_inner(self.context)
        return context.translate(msg, domain="collective.quickupload")
    
    def upload_settings(self):
        context = aq_inner(self.context)
        portal_url = getToolByName(context, 'portal_url')()
        
        settings = dict(
            portal_url             = portal_url,
            typeupload             = '',
            context_url            = context.absolute_url(),
            physical_path          = "/".join(context.getPhysicalPath()),
            ul_id                  = self.uploader_id,
            ul_fill_titles         = 'true',
            ul_fill_descriptions   = 'false',
            ul_auto_upload         = 'false',
            ul_size_limit          = '1',
            ul_xhr_size_limit      = '0',
            ul_sim_upload_limit    = '1',
            ul_file_extensions     = '*.*',
            ul_file_extensions_list = '[]',
            ul_file_description    = self._utranslate(u'Choose files to upload'),
            ul_button_text         = self._utranslate(u'Choose one or more files to upload:'),
            ul_draganddrop_text    = self._utranslate(u'Drag and drop files to upload'),
            ul_msg_all_sucess      = self._utranslate(u'All files uploaded with success.'),
            ul_msg_some_sucess     = self._utranslate(u' files uploaded with success, '),
            ul_msg_some_errors     = self._utranslate(u" uploads return an error."),
            ul_msg_failed          = self._utranslate(u"Failed"),
            ul_error_try_again_wo  = self._utranslate(u"please select files again without it."),
            ul_error_try_again     = self._utranslate(u"please try again."),
            ul_error_empty_file    = self._utranslate(u"This file is empty :"),
            ul_error_file_large    = self._utranslate(u"This file is too large :"),
            ul_error_maxsize_is    = self._utranslate(u"maximum file size is :"),
            ul_error_bad_ext       = self._utranslate(u"This file has invalid extension :"),
            ul_error_onlyallowed   = self._utranslate(u"Only allowed :"),
            ul_error_no_permission = self._utranslate(u"You don't have permission to add this content in this place."),
            ul_error_always_exists = self._utranslate(u"This file already exists with the same name on server :"),
            ul_error_zodb_conflict = self._utranslate(u"A data base conflict error happened when uploading this file :"),
            ul_error_server        = self._utranslate(u"Server error, please contact support and/or try again."),
        )
        
        return settings
    
    def script_content(self) :
        return """
    var fillTitles = %(ul_fill_titles)s;
    var fillDescriptions = %(ul_fill_descriptions)s;
    var auto = %(ul_auto_upload)s;
    createUploader_%(ul_id)s= function(){
        var uploader;
        uploader = new qq.FileUploader({
            element: jQuery('#%(ul_id)s')[0],
            action: '%(context_url)s/@@quick_upload_file',
            container_url: '%(context_url)s/@@cmsui-structure',
            autoUpload: auto,
            onAfterSelect: function(file, id) { PloneQuickUpload.addUploadFields(uploader, uploader._element, file, id, fillTitles, fillDescriptions) },
            onComplete: function(id, fileName, responseJSON) { PloneQuickUpload.onUploadComplete(uploader, uploader._element, id, fileName, responseJSON) },
            allowedExtensions: %(ul_file_extensions_list)s,
            sizeLimit: %(ul_xhr_size_limit)s,
            simUploadLimit: %(ul_sim_upload_limit)s,
            template: '<div class="qq-uploader">' +
                      '<div class="qq-upload-drop-area"><span>%(ul_draganddrop_text)s</span></div>' +
                      '<div class="qq-upload-button"><label for="file-upload">%(ul_button_text)s</label></div>' +
                      '<ul class="qq-upload-list"></ul>' +
                      '</div>',
            fileTemplate: '<li>' +
                    '<a class="qq-upload-cancel" href="#">&nbsp;</a>' +
                    '<div class="qq-upload-infos"><span class="qq-upload-file"></span>' +
                    '<span class="qq-upload-spinner"></span>' +
                    '<span class="qq-upload-failed-text">%(ul_msg_failed)s</span></div>' +
                    '<div class="qq-upload-size"></div>' +
                '</li>',
            messages: {
                serverError: "%(ul_error_server)s",
                serverErrorAlwaysExist: "%(ul_error_always_exists)s {file}",
                serverErrorZODBConflict: "%(ul_error_zodb_conflict)s {file}, %(ul_error_try_again)s",
                serverErrorNoPermission: "%(ul_error_no_permission)s",
                typeError: "%(ul_error_bad_ext)s {file}. %(ul_error_onlyallowed)s {extensions}.",
                sizeError: "%(ul_error_file_large)s {file}, %(ul_error_maxsize_is)s {sizeLimit}.",
                emptyError: "%(ul_error_empty_file)s {file}, %(ul_error_try_again_wo)s"
            }
        });
        jQuery('#uploadify-upload').click(function(e) {
            PloneQuickUpload.sendDataAndUpload(uploader, uploader._element, '%(typeupload)s');
        });
        jQuery('#uploadify-clear-queue').click(function(e) {
            PloneQuickUpload.clearQueue(uploader, uploader._element);
        });
    }
    jQuery(document).ready(createUploader_%(ul_id)s);
        """ % self.upload_settings()

class QuickUploadFile(BrowserView):
    """ Upload a file
    """
    
    def __call__(self):
        """
        """
        context = aq_inner(self.context)
        request = self.request
        response = request.RESPONSE
        
        # Disable theming on this response, otherwise Diazo completely mucks
        # things up.
        response.setHeader('X-Theme-Disabled', 'True')
        
        response.setHeader('Expires', 'Sat, 1 Jan 2000 00:00:00 GMT')
        response.setHeader('Cache-control', 'no-cache')
        response.setHeader('Content-Type', 'application/json')
        
        if request.HTTP_X_REQUESTED_WITH:
            # using ajax upload
            file_name = urllib.unquote(request.HTTP_X_FILE_NAME)
            # upload_with = "XHR"
            try :
                file = request.BODYFILE
                file_data = file.read()
                file.seek(0)
            except AttributeError :
                # in case of cancel during xhr upload
                # logger.info("Upload of %s has been aborted" %file_name)
                # not really useful here since the upload block
                # is removed by "cancel" action, but
                # could be useful if someone change the js behavior
                return  json.dumps({u'error': u'emptyError'})
            except :
                # logger.info("Error when trying to read the file %s in request"  %file_name)
                return json.dumps({u'error': u'serverError'})
        else :
            # using classic form post method (MSIE<=8)
            file_data = request.get("qqfile", None)
            filename = getattr(file_data,'filename', '')
            file_name = filename.split("\\")[-1]
            # upload_with = "CLASSIC FORM POST"
            # we must test the file size in this case (no client test)
        
        file_id = self._get_file_id(file_name)
        
        content_type = mimetypes.guess_type(file_name)[0]
        # sometimes plone mimetypes registry could be more powerful
        if not content_type :
            mtr = getToolByName(context, 'mimetypes_registry')
            oct = mtr.globFilename(file_name)
            if oct is not None :
                content_type = str(oct)
        
        portal_type = getDataFromAllRequests(request, 'typeupload') or ''
        title =  getDataFromAllRequests(request, 'title') or ''
        description =  getDataFromAllRequests(request, 'description') or ''
        
        if not portal_type :
            ctr = getToolByName(context, 'content_type_registry')
            portal_type = ctr.findTypeName(file_name.lower(), content_type, '') or 'File'
        
        if file_data:
            factory = IQuickUploadFileFactory(context)
            # logger.info("uploading file with %s : filename=%s, title=%s, description=%s, content_type=%s, portal_type=%s" % \
            # (upload_with, file_name, title, description, content_type, portal_type))
            
            try :
                f = factory(file_id, title, description, content_type, file_data, portal_type)
            except :
                return json.dumps({u'error': u'serverError'})
            
            if f['success'] is not None :
                # o = f['success']
                # logger.info("file url: %s" % o.absolute_url())
                msg = {u'success': True}
            else :
                msg = {u'error': f['error']}
        else :
            msg = {u'error': u'emptyError'}
        return json.dumps(msg)
    
    def _get_file_id(self, id):
        context = aq_inner(self.context)
        charset = context.getCharset()
        id = id.decode(charset)
        normalizer = getUtility(IIDNormalizer)
        chooser = INameChooser(context)
        newid = chooser.chooseName(normalizer.normalize(id), context)
        # Make sure our chosen id is unique, iterate until we get one that is.
        chooser = INameChooser(context)
        newid = chooser._findUniqueName(id, None)
        # consolidation because it's different upon Plone versions
        newid = newid.replace('_','-').replace(' ','-').lower()

        return newid


########NEW FILE########
__FILENAME__ = historypanel
from Acquisition import aq_inner

from datetime import datetime
from dateutil.relativedelta import relativedelta

from plone.app.cmsui.interfaces import _

from Products.CMFCore.utils import _checkPermission
from Products.CMFCore.utils import getToolByName
from Products.CMFEditions.Permissions import AccessPreviousVersions
from zope.publisher.browser import BrowserView

from zope.i18n import translate

from zExceptions import Unauthorized

class HistoryPanel(BrowserView):
    def __init__(self, context, request):
        super(HistoryPanel, self).__init__(context, request)
        
        sel_from = request.form.get('sel_from',None)
        sel_to = request.form.get('sel_to',None)
        if sel_from and sel_to:
            self.sel_from = int(sel_from)
            self.sel_to = int(sel_to)
        elif sel_to:
            self.sel_from = 'previous'
            self.sel_to = int(sel_to)
        else:
            self.sel_from = 'previous'
            self.sel_to   = 'latest'
    
    def __call__(self):
        context = self.context
        #TODO: Is this how to do it?
        if not(_checkPermission(AccessPreviousVersions, self.context)):
            raise Unauthorized
        
        # Get editing history
        self.repo_tool=getToolByName(self.context, "portal_repository")
        if self.repo_tool is None or not self.repo_tool.isVersionable(context):
            # Item isn't versionable
            self.sel_to = self.sel_from = 0
            return super(HistoryPanel, self).__call__()
        edit_history=self.repo_tool.getHistoryMetadata(context);
        if not(hasattr(edit_history,'getLength')):
            # No history metadata
            self.sel_to = self.sel_from = 0
            return super(HistoryPanel, self).__call__()
        
        # Go through revision history backwards
        history_list = []
        for i in xrange(edit_history.getLength(countPurged=False)-1, -1, -1):
            data = edit_history.retrieve(i, countPurged=False)
            meta = data["metadata"]["sys_metadata"]
            
            # Get next version, updating which is latest and previous if need be
            version_id = edit_history.getVersionId(i, countPurged=False)
            if self.sel_to == 'latest':
                self.sel_to = version_id
            elif self.sel_from == 'previous' and version_id < self.sel_to:
                self.sel_from = version_id
            
            # Add block describing this revision
            h = dict(entry_type='edit',
                version_id=version_id,
                principal=meta['principal'],
                timestamp=datetime.fromtimestamp(meta['timestamp']),
                comment=meta['comment'] or _("Edit"),
                klass='',
            )
            if self.sel_from == h['version_id']:
              h['klass'] = 'sel_from'
              self.sel_from_version = h
            if self.sel_to == h['version_id']:
              h['klass'] = 'sel_to'
              self.sel_to_version = h
            history_list.append(h)
        
        # Add workflow history to version history
        workflow = getToolByName(self.context, 'portal_workflow')
        for r in workflow.getInfoFor(self.context, 'review_history'):
            title = workflow.getTitleForTransitionOnType(r['action'], self.context.portal_type)
            if title is None: continue # No title means 'Create', and there'll be a edit_history entry for this.
            history_list.append(dict(entry_type='workflow',
                transition=title,
                principal=r.get('actor', _(u'label_anonymous_user', default=u'Anonymous User')),
                timestamp=datetime.fromtimestamp(float(r['time'])),
                comment=r['comments'] or _("Transition"),
                klass='',
            ))
        
        # Insert a date marker for every unique month
        date_markers = dict()
        for e in history_list:
            date_string = e['timestamp'].strftime('%B %Y')
            if date_markers.has_key(date_string): continue
            date_markers[date_string] = dict(
                entry_type='date-marker',
                # Timestamp one month ahead so it's on top of all the entries it refers to
                timestamp=datetime(e['timestamp'].year,e['timestamp'].month,1)+relativedelta(months=+1),
                date=e['timestamp'].strftime('%B %Y'),
            )
        history_list += date_markers.values()
        
        # Sort list into reverse order
        self.history_list = history_list = sorted(history_list, key=lambda k: datetime.now() - k['timestamp'])
        
        return super(HistoryPanel, self).__call__()
    
    def history_changes(self):
        if not(isinstance(self.sel_from,int) and isinstance(self.sel_to,int)):
            return []
        dt=getToolByName(self.context, "portal_diff")
        changeset=dt.createChangeSet(
                self._getVersion(self.sel_from),
                self._getVersion(self.sel_to),
                id1=self._versionTitle(self.sel_to), #TODO
                id2=self._versionTitle(getattr(self,'sel_from',None))
        )
        return [change for change in changeset.getDiffs()
                      if not change.same]
    
    def _versionTitle(self, version):
        return translate(
            _(u"version ${version}",
              mapping=dict(version=version)),
            context=self.request
        )
    
    def _getVersion(self, version):
        context=aq_inner(self.context)
        if version >= 0:
            return self.repo_tool.retrieve(context, int(version)).object
        else:
            return context

########NEW FILE########
__FILENAME__ = interfaces
from zope.interface import Interface
from zope import schema
from zope.i18nmessageid import MessageFactory
from zope.filerepresentation.interfaces import IFileFactory

_ = MessageFactory(u"plone")

class ICMSUISettings(Interface):
    """CMS UI settings stored in the registry
    """
    
    skinName = schema.ASCIILine(
            title=_(u"CMS UI theme name"),
            default='cmsui',
        )
    
    folderContentsBatchSize = schema.Int(
            title=_(u"Folder Contents Batch Size"),
            default=30,
        )
    
    editActionId = schema.ASCIILine(
            title=_(u"Edit action id"),
            default='edit',
        )
    
    excludedActionIds = schema.Tuple(
            title=_(u"Actions not shown in the more menu"),
            default=('view', 'edit'),
        )
    
    defaultActionIcon = schema.ASCIILine(
            title=_(u"Default action icon path"),
            default='/++resource++plone.app.cmsui/icons/List.png',
        )

class ICMSUILayer(Interface):
    """Browser layer used to indicate that plone.app.cmsui is installed
    """

class IQuickUploadCapable(Interface):
    """Any container/object which supports quick uploading
    """

class IQuickUploadFileFactory(IFileFactory):
    """used for QuickUploadFileFactory
    """


########NEW FILE########
__FILENAME__ = lockinfo
from zope.component import getMultiAdapter
from zope.publisher.browser import BrowserView
from plone.memoize.instance import memoize

class LockInfo(BrowserView):
    """Manage locks
    """
    
    def __call__(self):
        # Disable theming
        self.request.response.setHeader('X-Theme-Disabled', 'True')
        return self.index()
    
    @memoize
    def lock_info(self):
        return getMultiAdapter((self.context, self.request), name="plone_lock_info")

########NEW FILE########
__FILENAME__ = menu
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.publisher.browser import BrowserView
from plone.registry.interfaces import IRegistry
from plone.memoize.instance import memoize
from plone.app.cmsui.interfaces import ICMSUISettings

from Acquisition import aq_base
from AccessControl import getSecurityManager
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces import IPloneSiteRoot


class Menu(BrowserView):
    """The view containing the overlay menu
    """

    def __call__(self):
        # Disable theming
        self.request.response.setHeader('X-Theme-Disabled', 'True')

        # Set the CMSUI skin so that we get the correct resources
        self.context.changeSkin(self.settings.skinName, self.request)

        # Commonly useful variables
        self.securityManager = getSecurityManager()
        self.anonymous = self.portalState.anonymous()
        self.tools = getMultiAdapter((self.context, self.request), name=u'plone_tools')

        # Render the template
        return self.index()

    # Personal actions

    @property
    @memoize
    def contextState(self):
        return getMultiAdapter((self.context, self.request), name=u'plone_context_state')

    @property
    @memoize
    def portalState(self):
        return getMultiAdapter((self.context, self.request), name=u'plone_portal_state')

    @property
    @memoize
    def settings(self):
        return getUtility(IRegistry).forInterface(ICMSUISettings, False)

    @memoize
    def personalActions(self):
        """Get the personal actions
        """
        actions = []
        for action in self.contextState.actions('user'):
            actions.append({
                'id': action['id'],
                'url': action['url'],
                'title': action['title'],
                'description': action['description'],
            })

        return actions

    @memoize
    def userName(self):
        """Get the username of the currently logged in user
        """
        if self.anonymous:
            return None

        member = self.portalState.member()
        userid = member.getId()

        membership = self.tools.membership()
        memberInfo = membership.getMemberInfo(userid)

        fullname = userid

        # Member info is None if there's no Plone user object, as when using OpenID.
        if memberInfo is not None:
            fullname = memberInfo.get('fullname', '') or fullname

        return fullname

    @memoize
    def userHomeLinkURL(self):
        """Get the URL of the user's home page (profile age)
        """
        member = self.portalState.member()
        userid = member.getId()
        return "%s/author/%s" % (self.portalState.navigation_root_url(), userid)

    @memoize
    def breadcrumbs(self):
        """Get the breadcrumbs data structure
        """
        breadcrumbsView = getMultiAdapter((self.context, self.request), name='breadcrumbs_view')
        return breadcrumbsView.breadcrumbs()

    @memoize
    def modificationDate(self):
        """Get the modification date for display purposes
        """
        if hasattr(aq_base(self.context), 'modified'):
            modifiedDate = self.context.modified()

            translationService = getToolByName(self.context, 'translation_service')
            return translationService.ulocalized_time(modifiedDate,
                    context=self.context,
                    domain='plonelocales'
                )
        return None

    @memoize
    def authorName(self):
        """Get the full name of the author
        """
        owner = None
        if hasattr(aq_base(self.context), 'Creator'):
            owner = self.context.Creator()
        if owner is None:
            acl_users, owner = self.context.getOwnerTuple()
        membership = self.tools.membership()
        memberInfo = membership.getMemberInfo(owner)
        return memberInfo.get('fullname', '') or owner

    @memoize
    def workflowState(self):
        """Get the name of the workflow state
        """
        state = self.contextState.workflow_state()
        if state is None:
            return None
        workflows = self.tools.workflow().getWorkflowsFor(self.context)
        if workflows:
            for w in workflows:
                if state in w.states:
                    return w.states[state].title or state
        return state

    @memoize
    def itemsInFolder(self):
        """Count the items in the screen
        """
        folder = self.contextState.folder()
        if IPloneSiteRoot.providedBy(folder):
            return len(folder.contentIds())
        # XXX: Assumes other folders behave well and only contain content
        return len(folder)

    @memoize
    def editLink(self):
        """Get the URL of the edit action - taking locking into account
        """
        if not self.securityManager.checkPermission('Modify portal content', self.context):
            return None
        if self.contextState.is_locked():
            return self.context.absolute_url() + "/@@cmsui-lock-info"
        objectActions = self.contextState.actions('object')
        for action in objectActions:
            if action['id'] == self.settings.editActionId:
                return "%s?last_referer=%s" % (action['url'], self.context.absolute_url())
        return None

    @memoize
    def deleteLink(self):
        """Get the URL of the delete action - also looks at locking
        """

        if not self.securityManager.checkPermission('Delete objects', self.context):
            return None

        if self.contextState.is_locked():
            return self.context.absolute_url() + "/@@cmsui-lock-info"

        objectButtons = self.contextState.actions('object_buttons')
        for action in objectButtons:
            if action['id'] == 'delete':
                return "%s" % (action['url'])

        return None

    @memoize
    def settingsActions(self):
        """Render every action other than the excluded ones (edit, view).
        Use the action icon if applicable, but fall back on the default icon.
        """

        actions = []
        objectActions = self.contextState.actions('object')

        defaultIcon = self.portalState.navigation_root_url() + self.settings.defaultActionIcon

        for action in objectActions:
            if action['id'] in self.settings.excludedActionIds:
                continue

            icon = action['icon']
            if not icon:
                icon = defaultIcon

            actions.append({
                'id': action['id'],
                'url': action['url'],
                'title': action['title'],
                'description': action['description'],
                'icon': icon,
            })

        return actions

    @memoize
    def baseURL(self):
        return self.context.absolute_url()

    def canAdd(self):
        pm = getToolByName(self.context, 'portal_membership')
        return pm.checkPermission('Add portal content', self.context)

    def canListFolderContents(self):
        pm = getToolByName(self.context, 'portal_membership')
        return pm.checkPermission('List folder contents', self.context)

    def canChangeState(self):
        wft = getToolByName(self.context, 'portal_workflow')
        return len(wft.getTransitionsFor(self.context)) > 0

    def canAccessHistory(self):
        pm = getToolByName(self.context, 'portal_membership')
        return pm.checkPermission('CMFEditions: Access previous versions', self.context)

    def canChangeSharing(self):
        pm = getToolByName(self.context, 'portal_membership')
        return pm.checkPermission('Sharing page: Delegate roles', self.context)

    def canManageSite(self):
        pm = getToolByName(self.context, 'portal_membership')
        return pm.checkPermission('Plone Site Setup', self.context)

########NEW FILE########
__FILENAME__ = overlaycontainer
from zope.component import getUtility
from zope.publisher.browser import BrowserView
from plone.memoize.instance import memoize
from plone.registry.interfaces import IRegistry
from plone.app.cmsui.interfaces import ICMSUISettings

class OverlayContainer(BrowserView):
    """View that provides a main_template replacement for overlays.
    
    Use metal:use-macro="context/@@cmsui-overlay-container/macros/master"
    and then fill the main macro.
    """
    
    def __call__(self):
        # Disable theming
        self.request.response.setHeader('X-Theme-Disabled', 'True')
        
        # Set CMSUI theme
        self.context.changeSkin(self.settings.skinName, self.request)
        
        return self.index()

    @property
    def macros(self):
        return self.index.macros
    
    @property
    @memoize
    def settings(self):
        return getUtility(IRegistry).forInterface(ICMSUISettings, False)

########NEW FILE########
__FILENAME__ = sharing
from itertools import chain

from plone.memoize.instance import memoize, clearafter
from zope.component import getUtilitiesFor, getMultiAdapter
from zope.i18n import translate

from Acquisition import aq_parent, aq_base
from AccessControl import Unauthorized
from zExceptions import Forbidden

from Products.CMFCore.utils import getToolByName
from Products.CMFCore import permissions
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser import BrowserView
from Products.statusmessages.interfaces import IStatusMessage

from plone.app.workflow import PloneMessageFactory as _
from plone.app.workflow.interfaces import ISharingPageRole

AUTH_GROUP = 'AuthenticatedUsers'
STICKY = set([AUTH_GROUP])

def merge_search_results(results, key):
    """Merge member search results.

    Based on PlonePAS.browser.search.PASSearchView.merge.
    """
    output={}
    for entry in results:
        id=entry[key]
        if id not in output:
            output[id]=entry.copy()
        else:
            buf=entry.copy()
            buf.update(output[id])
            output[id]=buf

    return output.values()

class SharingView(BrowserView):
    
    # Actions
    
    STICKY = STICKY
    
    def __call__(self):
        """Perform the update and redirect if necessary, or render the page
        """
        
        postback = True
        
        form = self.request.form
        submitted = form.get('form.submitted', False)
    
        cancel_button = form.get('form.button.Cancel', None) is not None
    
        if submitted and not cancel_button:

            if not self.request.get('REQUEST_METHOD','GET') == 'POST':
                raise Forbidden

            authenticator = self.context.restrictedTraverse('@@authenticator', None) 
            if not authenticator.verify(): 
                raise Forbidden

            # Update the acquire-roles setting
            inherit = bool(form.get('inherit', False))
            reindex = self.update_inherit(inherit, reindex=False)

            # Update settings for users and groups
            entries = form.get('entries', [])
            roles = [r['id'] for r in self.roles()]
            settings = []
            for entry in entries:
                settings.append(
                    dict(id = entry['id'],
                         type = entry['type'],
                         roles = [r for r in roles if entry.get('role_%s' % r, False)]))
            if settings:
                reindex = self.update_role_settings(settings, reindex=False) or reindex

            if reindex:
                self.context.reindexObjectSecurity()
            IStatusMessage(self.request).addStatusMessage(_(u"Changes saved."), type='info')

        # Other buttons return to the sharing page
        if cancel_button:
            postback = False

        if postback:
            return self.index()
        else:
            context_state = self.context.restrictedTraverse("@@plone_context_state")
            url = context_state.view_url()
            self.request.response.redirect(url)
            
    # View
    
    @memoize
    def roles(self):
        """Get a list of roles that can be managed.
        
        Returns a list of dicts with keys:
        
            - id
            - title
        """
        context = self.context
        portal_membership = getToolByName(context, 'portal_membership')
        
        pairs = []
        
        for name, utility in getUtilitiesFor(ISharingPageRole):
            permission = utility.required_permission
            if permission is None or portal_membership.checkPermission(permission, context):
                pairs.append(dict(id = name, title = utility.title))
                
        pairs.sort(key=lambda x: translate(x["title"], context=self.request))
        return pairs
        
    @memoize
    def role_settings(self):
        """Get current settings for users and groups for which settings have been made.
        
        Returns a list of dicts with keys:
        
         - id
         - title
         - type (one of 'group' or 'user')
         - roles
         
        'roles' is a dict of settings, with keys of role ids as returned by 
        roles(), and values True if the role is explicitly set, False
        if the role is explicitly disabled and None if the role is inherited.
        """
        
        existing_settings = self.existing_role_settings()
        user_results = self.user_search_results()
        group_results = self.group_search_results()

        current_settings = existing_settings + user_results + group_results

        # We may be called when the user does a search instead of an update.
        # In that case we must not loose the changes the user made and
        # merge those into the role settings.
        requested = self.request.form.get('entries', None)
        if requested is not None:
            knownroles = [r['id'] for r in self.roles()]
            settings = {}
            for entry in requested:
                roles = [r for r in knownroles
                                if entry.get('role_%s' % r, False)]
                settings[(entry['id'], entry['type'])] = roles

            for entry in current_settings:
                desired_roles = settings.get((entry['id'], entry['type']), None)

                if desired_roles is None:
                    continue
                for role in entry["roles"]:
                    if entry["roles"][role] in [True, False]:
                        entry["roles"][role] = role in desired_roles

        current_settings.sort(key=lambda x: safe_unicode(x["type"])+safe_unicode(x["title"]))

        return current_settings

    def inherited(self, context=None):
        """Return True if local roles are inherited here.
        """
        if context is None:
            context = self.context
        if getattr(aq_base(context), '__ac_local_roles_block__', None):
            return False
        return True
        
    # helper functions
    
    @memoize
    def existing_role_settings(self):
        """Get current settings for users and groups that have already got
        at least one of the managed local roles.

        Returns a list of dicts as per role_settings()
        """
        context = self.context
        
        portal_membership = getToolByName(context, 'portal_membership')
        portal_groups = getToolByName(context, 'portal_groups')
        acl_users = getToolByName(context, 'acl_users')
        
        info = []
        
        # This logic is adapted from computeRoleMap.py
        
        local_roles = acl_users._getLocalRolesForDisplay(context)
        acquired_roles = self._inherited_roles()
        available_roles = [r['id'] for r in self.roles()]

        # first process acquired roles
        items = {}
        for name, roles, rtype, rid in acquired_roles:
            items[rid] = dict(id       = rid,
                              name     = name,
                              type     = rtype,
                              sitewide = [],
                              acquired = roles,
                              local    = [],)
                                
        # second process local roles
        for name, roles, rtype, rid in local_roles:
            if items.has_key(rid):
                items[rid]['local'] = roles
            else:
                items[rid] = dict(id       = rid,
                                  name     = name,
                                  type     = rtype,
                                  sitewide = [],
                                  acquired = [],
                                  local    = roles,)

        # Make sure we always get the authenticated users virtual group
        if AUTH_GROUP not in items:
            items[AUTH_GROUP] = dict(id = AUTH_GROUP,
                                     name = _(u'Logged-in users'),
                                     type  = 'group',
                                     sitewide = [],
                                     acquired = [],
                                     local = [],)
        
        # If the current user has been given roles, remove them so that he
        # doesn't accidentally lock himself out.
        
        member = portal_membership.getAuthenticatedMember()
        if member.getId() in items:
            items[member.getId()]['disabled'] = True

        # Make sure we include the current user's groups
        groups = [portal_groups.getGroupById(m) for m in portal_groups.getGroupsForPrincipal(member)]
        current_groups = set([])
        for g in groups:
            group_id = g.getId()
            current_groups.add(group_id)
            if group_id not in items:
                items[group_id] = dict(id = group_id,
                                        name = g.getGroupTitleOrName(),
                                        type = 'group',
                                        sitewide = [],
                                        acquired = [],
                                        local = [],
                                        )

        # Sort the list: first the authenticated users virtual group, then 
        # all other groups and then all users, alphabetically

        sticky = STICKY | current_groups
        dec_users = [( a['id'] not in sticky,
                       a['type'], 
                       a['name'],
                       a) for a in items.values()]
        dec_users.sort()
        
        # Add the items to the info dict, assigning full name if possible.
        # Also, recut roles in the format specified in the docstring
        
        for d in dec_users:
            item = d[-1]
            name = item['name']
            rid = item['id']
            global_roles = set()
            
            if item['type'] == 'user':
                member = acl_users.getUserById(rid)
                if member is not None:
                    name = member.getProperty('fullname') or member.getId() or name
                    global_roles = set(member.getRoles())
            elif item['type'] == 'group':
                g = portal_groups.getGroupById(rid)
                name = g.getGroupTitleOrName()
                global_roles = set(g.getRoles())
                
                # This isn't a proper group, so it needs special treatment :(
                if rid == AUTH_GROUP:
                    name = _(u'Logged-in users')
            
            info_item = dict(id    = item['id'],
                             type  = item['type'],
                             title = name,
                             disabled = item.get('disabled', False),
                             roles = {})
                             
            # Record role settings
            have_roles = False
            for r in available_roles:
                if r in global_roles:
                    info_item['roles'][r] = 'global'
                elif r in item['acquired']:
                    info_item['roles'][r] = 'acquired'
                    have_roles = True # we want to show acquired roles
                elif r in item['local']:
                    info_item['roles'][r] = True
                    have_roles = True # at least one role is set
                else:
                    info_item['roles'][r] = False
            
            if have_roles or rid in sticky:
                info.append(info_item)
        
        return info
    
    def _principal_search_results(self,
                                  search_for_principal,
                                  get_principal_by_id,
                                  get_principal_title,
                                  principal_type,
                                  id_key):
        """Return search results for a query to add new users or groups.
        
        Returns a list of dicts, as per role_settings().
        
        Arguments:
            search_for_principal -- a function that takes an IPASSearchView and
                a search string. Uses the former to search for the latter and
                returns the results.
            get_principal_by_id -- a function that takes a user id and returns
                the user of that id
            get_principal_title -- a function that takes a user and a default
                title and returns a human-readable title for the user. If it
                can't think of anything good, returns the default title.
            principal_type -- either 'user' or 'group', depending on what kind
                of principals you want
            id_key -- the key under which the principal id is stored in the
                dicts returned from search_for_principal
        """
        context = self.context
        
        search_term = self.request.form.get('search_term', None)
        if not search_term:
            return []
        
        existing_principals = set([p['id'] for p in self.existing_role_settings() 
                                if p['type'] == principal_type])
        empty_roles = dict([(r['id'], False) for r in self.roles()])
        info = []
        
        hunter = getMultiAdapter((context, self.request), name='pas_search')
        for principal_info in search_for_principal(hunter, search_term):
            principal_id = principal_info[id_key]
            if principal_id not in existing_principals:
                principal = get_principal_by_id(principal_id)
                roles = empty_roles.copy()
                if principal is None:
                    continue

                for r in principal.getRoles():
                    if r in roles:
                        roles[r] = 'global'
                info.append(dict(id    = principal_id,
                                 title = get_principal_title(principal,
                                                             principal_id),
                                 type  = principal_type,
                                 roles = roles))
        return info
        
    def user_search_results(self):
        """Return search results for a query to add new users.
        
        Returns a list of dicts, as per role_settings().
        """
        def search_for_principal(hunter, search_term):
            return merge_search_results(chain(*[hunter.searchUsers(**{field: search_term})
                                 for field in ['login', 'fullname']]
                              ), 'userid')
        
        def get_principal_by_id(user_id):
            acl_users = getToolByName(self.context, 'acl_users')
            return acl_users.getUserById(user_id)
        
        def get_principal_title(user, default_title):
            return user.getProperty('fullname') or user.getId() or default_title
            
        return self._principal_search_results(search_for_principal,
            get_principal_by_id, get_principal_title, 'user', 'userid')
        
    def group_search_results(self):
        """Return search results for a query to add new groups.
        
        Returns a list of dicts, as per role_settings().
        """
        def search_for_principal(hunter, search_term):
            return merge_search_results(chain(*[hunter.searchGroups(**{field:search_term}) for field in ['id', 'title']]), 'groupid')
        
        def get_principal_by_id(group_id):
            portal_groups = getToolByName(self.context, 'portal_groups')
            return portal_groups.getGroupById(group_id)
        
        def get_principal_title(group, _):
            return group.getGroupTitleOrName()
        
        return self._principal_search_results(search_for_principal,
            get_principal_by_id, get_principal_title, 'group', 'groupid')
        
    def _inherited_roles(self):
        """Returns a tuple with the acquired local roles."""
        context = self.context
        
        if not self.inherited(context):
            return []
        
        portal = getToolByName(context, 'portal_url').getPortalObject()
        result = []
        cont = True
        if portal != context:
            parent = aq_parent(context)
            while cont:
                if not getattr(parent, 'acl_users', False):
                    break
                userroles = parent.acl_users._getLocalRolesForDisplay(parent)
                for user, roles, role_type, name in userroles:
                    # Find user in result
                    found = 0
                    for user2, roles2, type2, name2 in result:
                        if user2 == user:
                            # Check which roles must be added to roles2
                            for role in roles:
                                if not role in roles2:
                                    roles2.append(role)
                            found = 1
                            break
                    if found == 0:
                        # Add it to result and make sure roles is a list so
                        # we may append and not overwrite the loop variable
                        result.append([user, list(roles), role_type, name])
                if parent == portal:
                    cont = False
                elif not self.inherited(parent):
                    # Role acquired check here
                    cont = False
                else:
                    parent = aq_parent(parent)

        # Tuplize all inner roles
        for pos in range(len(result)-1,-1,-1):
            result[pos][1] = tuple(result[pos][1])
            result[pos] = tuple(result[pos])

        return tuple(result)
        
    def update_inherit(self, status=True, reindex=True):
        """Enable or disable local role acquisition on the context.

        Returns True if changes were made, or False if the new settings
        are the same as the existing settings.
        """
        context = self.context
        portal_membership = getToolByName(context, 'portal_membership')
        
        if not portal_membership.checkPermission(permissions.ModifyPortalContent, context):
            raise Unauthorized

        block = not status 
        oldblock = bool(getattr(aq_base(context), '__ac_local_roles_block__', False))

        if block == oldblock:
            return False

        context.__ac_local_roles_block__ = block and True or None
        if reindex:
            context.reindexObjectSecurity()
        return True
        
    @clearafter
    def update_role_settings(self, new_settings, reindex=True):
        """Update local role settings and reindex object security if necessary.
        
        new_settings is a list of dicts with keys id, for the user/group id;
        type, being either 'user' or 'group'; and roles, containing the list
        of role ids that are set.

        Returns True if changes were made, or False if the new settings
        are the same as the existing settings.
        """

        changed = False
        context = self.context
            
        managed_roles = frozenset([r['id'] for r in self.roles()])
        member_ids_to_clear = []
            
        for s in new_settings:
            user_id = s['id']
            
            existing_roles = frozenset(context.get_local_roles_for_userid(userid=user_id))
            selected_roles = frozenset(s['roles'])

            relevant_existing_roles = managed_roles & existing_roles

            # If, for the managed roles, the new set is the same as the
            # current set we do not need to do anything.
            if relevant_existing_roles == selected_roles:
                continue
            
            # We will remove those roles that we are managing and which set
            # on the context, but which were not selected
            to_remove = relevant_existing_roles - selected_roles

            # Leaving us with the selected roles, less any roles that we
            # want to remove
            wanted_roles = (selected_roles | existing_roles) - to_remove
            
            # take away roles that we are managing, that were not selected 
            # and which were part of the existing roles
            
            if wanted_roles:
                context.manage_setLocalRoles(user_id, list(wanted_roles))
                changed = True
            elif existing_roles:
                member_ids_to_clear.append(user_id)
                
        if member_ids_to_clear:
            context.manage_delLocalRoles(userids=member_ids_to_clear)
            changed = True
        
        if changed and reindex:
            self.context.reindexObjectSecurity()

        return changed

########NEW FILE########
__FILENAME__ = structure
from Acquisition import aq_inner, aq_parent
from Products.CMFPlone.utils import pretty_title_or_id, isExpired, base_hasattr, \
    safe_unicode
from Products.CMFCore.utils import getToolByName
from Products.ATContentTypes.interface import IATTopic

from plone.memoize import instance
from plone.app.content.batching import Batch
from plone.registry.interfaces import IRegistry
from plone.folder.interfaces import IOrderableFolder, IExplicitOrdering
from plone.app.cmsui.interfaces import ICMSUISettings

from zope.component import getMultiAdapter, getUtility
from zope.i18n import translate
from zope.i18nmessageid import MessageFactory
from zope.cachedescriptors.property import Lazy as lazy_property
from zope.publisher.browser import BrowserView

import urllib

_ = MessageFactory('plone')


class StructureView(BrowserView):
    """Folder contents overlay
    """

    def __call__(self, contentFilter={}):
        # Disable theming
        self.contentFilter = contentFilter
        self.request.response.setHeader('X-Theme-Disabled', 'True')

        registry = getUtility(IRegistry)
        settings = registry.forInterface(ICMSUISettings, False)
        
        self.pagesize = settings.folderContentsBatchSize
        self.showAll = self.request.get('show_all', '').lower() == 'true'
        self.selectAll = self.request.get('select', '').lower() == 'all'
        
        return self.index()


    @lazy_property
    def contextState(self):
        return getMultiAdapter((self.context, self.request), 
            name=u'plone_context_state')


    def breadcrumbs(self):
        breadcrumbsView = getMultiAdapter((self.context, self.request), 
            name='breadcrumbs_view')
        breadcrumbs = list(breadcrumbsView.breadcrumbs())
        if self.contextState.is_default_page():
            # then we need to mess with the breadcrumbs a bit.
            parent = aq_parent(aq_inner(self.context))
            if breadcrumbs:
                breadcrumbs[-1] = {
                    'absolute_url' : parent.absolute_url(), 
                    'Title': parent.Title()
                    }
            breadcrumbs.append({
                'absolute_url' : self.context.absolute_url(),
                'Title': self.context.Title()}
                )
        return breadcrumbs


    def contentsMethod(self):
        context = aq_inner(self.context)
        if IATTopic.providedBy(context):
            contentsMethod = context.queryCatalog
        else:
            contentsMethod = context.getFolderContents
        return contentsMethod


    @lazy_property
    def folderItems(self):
        """
        """
        context = aq_inner(self.context)
        ploneUtils = getToolByName(context, 'plone_utils')
        ploneView = getMultiAdapter((context, self.request), name=u'plone')
        ploneLayout = getMultiAdapter((context, self.request), name=u'plone_layout')
        portalWorkflow = getToolByName(context, 'portal_workflow')
        portalTypes = getToolByName(context, 'portal_types')
        portalMembership = getToolByName(context, 'portal_membership')

        browser_default = ploneUtils.browserDefault(context)

        contentsMethod = self.contentsMethod()

        start = 0
        end = start + self.pagesize

        results = []
        for i, obj in enumerate(contentsMethod(self.contentFilter)):
            path = obj.getPath() or "/".join(obj.getPhysicalPath())

            # avoid creating unnecessary info for items outside the current
            # batch;  only the path is needed for the "select all" case...
            if not self.selectAll and not self.showAll and not start <= i < end:
                results.append(dict(path = path))
                continue

            url = obj.getURL()
            viewUrl = url + "/cmsui-structure"
            
            fti = portalTypes.get(obj.portal_type)
            if fti is not None:
                typeTitleMsgid = fti.Title()
            else:
                typeTitleMsgid = obj.portal_type
            urlHrefTitle = u'%s: %s' % (translate(typeTitleMsgid,
                                            context=self.request),
                                            safe_unicode(obj.Description))
            creator = obj.Creator
            memberInfo = portalMembership.getMemberInfo(creator)
            creator = memberInfo.get('fullname', '') or creator

            modified = ploneView.toLocalizedTime(
                obj.ModificationDate, long_format=1)
            
            isBrowserDefault = len(browser_default[1]) == 1 and (
                obj.id == browser_default[1][0])

            results.append(dict(
                url = url,
                urlHrefTitle = urlHrefTitle,
                id = obj.getId,
                quotedId = urllib.quote_plus(obj.getId),
                path = path,
                titleOrId = safe_unicode(pretty_title_or_id(ploneUtils, obj)),
                creator = creator,
                modified = modified,
                icon = ploneLayout.getIcon(obj).html_tag(),
                typeClass = 'contenttype-' + ploneUtils.normalizeString(obj.portal_type),
                wf_state =  obj.review_state,
                stateTitle = portalWorkflow.getTitleForStateOnType(obj.review_state,
                                                           obj.Type),
                stateClass = 'state-' + ploneUtils.normalizeString(obj.review_state),
                isBrowserDefault = isBrowserDefault,
                folderish = obj.is_folderish,
                viewUrl = viewUrl,
                isExpired = isExpired(obj),
            ))
        return results


    @property
    @instance.memoize
    def orderable(self):
        """
        """
        context = aq_inner(self.context)
        if not IOrderableFolder.providedBy(context):
            if hasattr(context, 'moveObjectsByDelta'):
                # for instance, plone site root does not use plone.folder
                return True
            else:
                return False
        ordering = context.getOrdering()
        return IExplicitOrdering.providedBy(ordering)


    @property
    def showSortColumn(self):
        return self.orderable and self.editable


    @property
    def editable(self):
        """
        """
        return self.contextState.is_editable()


    @property
    def buttons(self):
        buttons = []
        context = aq_inner(self.context)
        portalActions = getToolByName(context, 'portal_actions')
        buttonActions = portalActions.listActionInfos(
            object=aq_inner(self.context), categories=('folder_buttons',))

        # Do not show buttons if there is no data, unless there is data to be
        # pasted
        if not len(self.folderItems):
            if self.context.cb_dataValid():
                for button in buttonActions:
                    if button['id'] == 'paste':
                        return [self.setButtonClass(button)]
            else:
                return []

        for button in buttonActions:
            # Make proper classes for our buttons
            if button['id'] != 'paste' or context.cb_dataValid():
                buttons.append(self.setButtonClass(button))
        return buttons


    def setButtonClass(self, button):
        if button['id'] == 'paste':
            button['cssclass'] = 'standalone'
        else:
            button['cssclass'] = 'context'
        return button


    def msgSelectItem(self, item):
        titleOrId = (item.get('titleOrId') or item.get('title') or
                       item.get('Title') or item.get('id') or item['getId'])
        return _(u'checkbox_select_item',
                 default=u"Select ${title}",
                 mapping={'title': safe_unicode(titleOrId)})


    def setChecked(self, item):
        item['checked'] = self.selectAll and 'checked' or None


    @lazy_property
    def batch(self):
        pagesize = self.pagesize
        if self.showAll:
            pagesize = len(self.folderItems)
        b = Batch(self.folderItems,
                  pagesize=pagesize,
                  pagenumber=1)
        map(self.setChecked, b)
        return b


    # options
    _select_all = False
    def _getSelectAll(self):
        return self._select_all

    def _setSelectAll(self, value):
        self._select_all = bool(value)
    selectAll = property(_getSelectAll, _setSelectAll)


    @lazy_property
    def viewUrl(self):
        return self.context.absolute_url() + '/cmsui-structure'


    @property
    def selectallUrl(self):
        if '?' in self.selectnoneUrl:
            return self.selectnoneUrl+'&select=all'
        else:
            return self.selectnoneUrl+'?select=all'


    @property
    def selectnoneUrl(self):
        base = self.viewUrl
        if self.showAll:
            if '?' in base:
                base += '&show_all=true'
            else:
                base += '?show_all=true'
        return base


    @property
    def showAllUrl(self):
        base = self.viewUrl + '?show_all=true'
        if self.selectAll:
            base += '&select=all'
        return base


    def quotePlus(self, string):
        return urllib.quote_plus(string)


class MoveItem(BrowserView):
    """
    Pretty much straight copy of the folder_moveitem.py script
    so we can eventually remove the bloody thing.
    """
    def __call__(self, item_id, delta, subset_ids=None):
        context = aq_inner(self.context)
        try:
            if not IOrderableFolder.providedBy(context):
                if not base_hasattr(context, 'moveObjectsByDelta'):
                    # for instance, plone site root does not use plone.folder
                    raise ValueError("Not an ordered folder.")
            else:
                ordering = context.getOrdering()
                if not IExplicitOrdering.providedBy(ordering):
                    raise ValueError("Ordering disable on folder.")

            delta = int(delta)
            if subset_ids is not None:
                objectPos = self.context.getObjectPosition
                position_id = [(objectPos(id), id) for id in subset_ids]
                position_id.sort()
                if subset_ids != [id for position, id in position_id]:
                    raise ValueError("Client/server ordering mismatch.")
                self.context.moveObjectsByDelta(item_id, delta, subset_ids)
        except ValueError as e:
            self.context.REQUEST.response.setStatus('BadRequest')
            return str(e)

        ploneUtils = getToolByName(self.context, 'plone_utils')
        ploneUtils.reindexOnReorder(self.context)
        return "<done />"

########NEW FILE########
__FILENAME__ = testing
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_PASSWORD
from plone.app.testing import applyProfile
from plone.app.testing.layers import FunctionalTesting
from plone.app.testing.layers import IntegrationTesting
from Products.CMFCore.utils import getToolByName
from zope.configuration import xmlconfig

class CMSUI(PloneSandboxLayer):
    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # load ZCML
        import plone.app.cmsui
        xmlconfig.file('configure.zcml', plone.app.cmsui, context=configurationContext)

    def setUpPloneSite(self, portal):
        # install into the Plone site
        applyProfile(portal, 'plone.app.cmsui:default')
        workflowTool = getToolByName(portal, 'portal_workflow')
        workflowTool.setDefaultChain('plone_workflow')


CMSUI_FIXTURE = CMSUI()
CMSUI_INTEGRATION_TESTING = IntegrationTesting(bases=(CMSUI_FIXTURE,), name="CMSUI:Integration")
CMSUI_FUNCTIONAL_TESTING = FunctionalTesting(bases=(CMSUI_FIXTURE,), name="CMSUI:Functional")

def browser_login(portal, browser, username=None, password=None):
    handleErrors = browser.handleErrors
    try:
        browser.handleErrors = False
        browser.open(portal.absolute_url() + '/login_form')
        if username is None:
            username = TEST_USER_NAME
        if password is None:
            password = TEST_USER_PASSWORD
        browser.getControl(name='__ac_name').value = username
        browser.getControl(name='__ac_password').value = password
        browser.getControl(name='submit').click()
    finally:
        browser.handleErrors = handleErrors

########NEW FILE########
__FILENAME__ = test_menu_link
import unittest2 as unittest

from plone.app.cmsui.testing import CMSUI_FUNCTIONAL_TESTING
from plone.app.cmsui.testing import browser_login
from plone.app.testing import TEST_USER_ID
from plone.app.testing import setRoles
from plone.testing.z2 import Browser
import transaction

class TestMenuLink(unittest.TestCase):

    layer = CMSUI_FUNCTIONAL_TESTING

    def test_menu_sublinks_rendered_in_correct_context(self):
        """
        The menu link was rendered as a relative link, which means it generally
        wasn't on the correct context.  e.g. /news/@@cmsui-menu is the folder,
        not the default view.
        """

        browser = Browser(self.layer['app'])
        portal = self.layer['portal']
        setRoles(portal, TEST_USER_ID, ('Member', 'Manager'))
        document_id = portal.invokeFactory("Document", "menu_test_context", title="Context test")
        document = portal[document_id]
        # Commit so the change in roles is visible to the browser
        transaction.commit()
        
        browser_login(portal, browser)
        browser.open(document.absolute_url())
        browser.getLink("Manage page").click()
        self.assertIn("menu_test_context", browser.url)
    

########NEW FILE########
__FILENAME__ = test_permissions
import unittest2 as unittest

import transaction
from plone.testing.z2 import Browser
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.cmsui.testing import CMSUI_FUNCTIONAL_TESTING
from plone.app.cmsui.testing import browser_login
from plone.app.cmsui.tests import createObject


class TestPermissions(unittest.TestCase):

    layer = CMSUI_FUNCTIONAL_TESTING

    def setUp(self):
        portal = self.layer['portal']
        acl_users = portal.acl_users
        acl_users.userFolderAddUser('other_user', 'secret', ['Manager'], [])
        login(portal, 'other_user')
        createObject(portal, 'Folder', 'empty-folder', delete_first=True, title=u"Folder 1")
        transaction.commit()
        self.portal = portal

    def test_not_visible_to_anon(self):
        browser = Browser(self.layer['app'])
        browser.open('http://nohost/plone/cmsui-structure')
        self.assertTrue('Log in' in browser.contents)

    def test_visible_to_members(self):
        browser = Browser(self.layer['app'])
        browser_login(self.portal, browser)
        browser.open('http://nohost/plone/cmsui-menu')
        self.assertTrue('Logged in as test_user_1_')

    def test_add_button_permission(self):
        browser = Browser(self.layer['app'])
        browser_login(self.portal, browser)
        browser.open('http://nohost/plone/empty-folder/cmsui-menu')
        self.assertTrue('folder-add_content' not in browser.contents)
        setRoles(self.portal, TEST_USER_ID, ['Member', 'Contributor'])
        transaction.commit()
        browser.open('http://nohost/plone/empty-folder/cmsui-menu')
        self.assertTrue('folder-add_content' in browser.contents)

    def test_structure_button_permission(self):
        browser = Browser(self.layer['app'])
        browser_login(self.portal, browser)
        browser.open('http://nohost/plone/empty-folder/cmsui-menu')
        self.assertTrue('structure' not in browser.contents)
        setRoles(self.portal, TEST_USER_ID, ['Member', 'Contributor'])
        transaction.commit()
        browser.open('http://nohost/plone/empty-folder/cmsui-menu')
        self.assertTrue('structure' in browser.contents)

    def test_edit_button_permission(self):
        browser = Browser(self.layer['app'])
        browser_login(self.portal, browser)
        browser.open('http://nohost/plone/empty-folder/cmsui-menu')
        self.assertTrue('document-edit' not in browser.contents)
        setRoles(self.portal, TEST_USER_ID, ['Member', 'Editor'])
        transaction.commit()
        browser.open('http://nohost/plone/empty-folder/cmsui-menu')
        self.assertTrue('document-edit' in browser.contents)

    def test_delete_button_permission(self):
        browser = Browser(self.layer['app'])
        browser_login(self.portal, browser)
        browser.open('http://nohost/plone/empty-folder/cmsui-menu')
        self.assertTrue('document-delete' not in browser.contents)
        setRoles(self.portal, TEST_USER_ID, ['Member', 'Editor'])
        transaction.commit()
        browser.open('http://nohost/plone/empty-folder/cmsui-menu')
        self.assertTrue('document-delete' in browser.contents)

    def test_workflow_button_permission(self):
        browser = Browser(self.layer['app'])
        browser_login(self.portal, browser)
        browser.open('http://nohost/plone/empty-folder/cmsui-menu')
        self.assertTrue('plone-contentmenu-workflow' not in browser.contents)
        self.assertTrue('Status:' in browser.contents)
        self.assertTrue('Public draft' in browser.contents)
        setRoles(self.portal, TEST_USER_ID, ['Member', 'Reviewer'])
        transaction.commit()
        browser.open('http://nohost/plone/empty-folder/cmsui-menu')
        self.assertTrue('plone-contentmenu-workflow' in browser.contents)

    def test_history_button_permission(self):
        browser = Browser(self.layer['app'])
        browser_login(self.portal, browser)
        browser.open('http://nohost/plone/empty-folder/cmsui-menu')
        self.assertTrue('document-history' not in browser.contents)
        setRoles(self.portal, TEST_USER_ID, ['Member', 'Editor'])
        transaction.commit()
        browser.open('http://nohost/plone/empty-folder/cmsui-menu')
        self.assertTrue('document-history' in browser.contents)

    def test_sharing_button_permission(self):
        browser = Browser(self.layer['app'])
        browser_login(self.portal, browser)
        browser.open('http://nohost/plone/empty-folder/cmsui-menu')
        self.assertTrue('document-author' not in browser.contents)
        setRoles(self.portal, TEST_USER_ID, ['Member', 'Editor'])
        transaction.commit()
        browser.open('http://nohost/plone/empty-folder/cmsui-menu')
        self.assertTrue('document-author' in browser.contents)

    def test_site_setup_button_permission(self):
        browser = Browser(self.layer['app'])
        browser_login(self.portal, browser)
        browser.open('http://nohost/plone/empty-folder/cmsui-menu')
        self.assertTrue('site-setup' not in browser.contents)
        setRoles(self.portal, TEST_USER_ID, ['Member', 'Manager'])
        transaction.commit()
        browser.open('http://nohost/plone/empty-folder/cmsui-menu')
        self.assertTrue('site-setup' in browser.contents)

########NEW FILE########
__FILENAME__ = test_structure
import unittest2 as unittest

import transaction
from plone.testing.z2 import Browser
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.cmsui.testing import CMSUI_FUNCTIONAL_TESTING
from plone.app.cmsui.testing import browser_login
from plone.app.cmsui.structure import MoveItem
from plone.app.cmsui.tests import createObject

class TestFolderContents(unittest.TestCase):

    layer = CMSUI_FUNCTIONAL_TESTING

    def setUp(self):
        portal = self.layer['portal']
        setRoles(portal, TEST_USER_ID, ['Manager'])
        createObject(portal, 'Folder', 'empty-folder', delete_first=True, title=u"Folder 1")
        transaction.commit()
        
        self.portal = portal
        self.browser = Browser(self.layer['app'])
        

    def test_not_visible_to_anon(self):
        browser = Browser(self.layer['app'])
        browser.open('http://nohost/plone/cmsui-structure')
        self.assertTrue('Log in' in browser.contents)

    def test_bbb_view(self):
        browser_login(self.portal, self.browser)
        self.browser.open('http://nohost/plone/@@folder_contents')
        self.assertTrue('cmsui-structure' in self.browser.contents)

    def test_table_headers_hidden_on_empty_folder(self):
        browser_login(self.portal, self.browser)
        
        # empty folder
        self.browser.open('http://nohost/plone/empty-folder/cmsui-structure')
        self.assertFalse('foldercontents-title-column' in self.browser.contents)

        # non-empty folder
        self.browser.open('http://nohost/plone/cmsui-structure')
        self.assertTrue('foldercontents-title-column' in self.browser.contents)
        

class TestDeleteItem(unittest.TestCase):
    layer = CMSUI_FUNCTIONAL_TESTING
    
    def setUp(self):
        portal = self.layer['portal']
        setRoles(portal, TEST_USER_ID, ['Manager'])
        createObject(portal, 'Folder', 'key-party', delete_first=True, title=u"Folder 1")
        party = portal.get('key-party')
        createObject(party, 'Document', 'he', delete_first=True, title=u"John Key")
        createObject(party, 'Document', 'she', delete_first=True, title=u"Joan Key")
        transaction.commit()
        self.portal = portal
        
    def test_delete_existence(self): 
        setRoles(self.layer['portal'], TEST_USER_ID, ['Owner'])
        browser = Browser(self.layer['app'])
        browser_login(self.portal, browser)
        browser.open('http://nohost/plone/key-party/he/@@cmsui-menu')
        self.assertTrue(browser.getLink('Delete').url.endswith('he/delete_confirmation'))

    # TODO: test locking - I think this is broken for edit as well
    
class TestMoveItem(unittest.TestCase):
    layer = CMSUI_FUNCTIONAL_TESTING
    
    def setUp(self):
        portal = self.layer['portal']
        setRoles(portal, TEST_USER_ID, ['Manager'])
        testfolder = createObject(portal, 'Folder', 'test-folder', check_for_first=True, title='Test Folder')
        createObject(portal, 'Folder', 'test-folder-2', check_for_first=True, title='Test Folder 2')
        createObject(testfolder, 'Document', 'test1', check_for_first=True)
        createObject(testfolder, 'Document', 'test2', check_for_first=True)
        createObject(testfolder, 'Document', 'test3', check_for_first=True)
        createObject(testfolder, 'Document', 'test4', check_for_first=True)
        createObject(testfolder, 'Document', 'test5', check_for_first=True)
        createObject(testfolder, 'Document', 'test6', check_for_first=True)
        createObject(testfolder, 'Document', 'test7', check_for_first=True)
        createObject(testfolder, 'Document', 'test8', check_for_first=True)
        createObject(testfolder, 'Document', 'test9', check_for_first=True)
        
        self.portal = portal
        self.testfolder = testfolder
        self.moveitem = MoveItem(testfolder, self.layer['request'])

    def test_move_item_up(self):
        self.moveitem('test1', 3, subset_ids=['test1', 'test2', 'test3', 'test4', 'test5'])
        self.assertTrue(self.testfolder.getObjectPosition('test1') == 3)
        
    def test_move_item_down(self):
        self.moveitem('test5', -3, subset_ids=['test1', 'test2', 'test3', 'test4', 'test5'])
        self.assertTrue(self.testfolder.getObjectPosition('test5') == 1)
        
    def test_throws_error_on_inconsistent_structure(self):
        res = self.moveitem('test5', 3, subset_ids=['test3', 'test2', 'test1', 'test4', 'test5'])
        self.assertTrue('Client/server ordering mismatch.' in res)
        
    def test_can_reorder_portal_site_root(self):
        moveitem = MoveItem(self.portal, self.layer['request'])
        orig_order = self.portal.getObjectPosition('test-folder')
        moveitem('test-folder', 1, subset_ids=['test-folder', 'test-folder-2'])
        self.assertTrue(self.portal.getObjectPosition('test-folder') == (orig_order+1))
        
    def test_can_not_reorder_if_ordering_is_disabled(self):
        folder = createObject(self.portal, 'Folder', 'test-folder-3')
        folder.setOrdering('unordered')
        
        createObject(folder, 'Document', 'test-1')
        createObject(folder, 'Document', 'test-2')
        
        moveitem = MoveItem(folder, self.layer['request'])
        res = moveitem('test-1', 1, subset_ids=['test-1', 'test-2'])
        self.assertTrue('Ordering disable on folder.' in res)
        
    def test_can_not_reorder_on_item_that_is_not_a_folder(self):
        test = createObject(self.portal, 'Document', 'test-1')
        moveitem = MoveItem(test, self.layer['request'])
        res = moveitem('something', 1)
        self.assertTrue("Not an ordered folder." in res)
        
        
"""
    Buttons
    -------

    With the folder contents view it is possible to copy, paste etc. a lot
    of content objects at once.

    An empty folder should only contain the paste button.

      >>> self.createFolder('empty-folder')
      >>> browser.open('http://nohost/plone/empty-folder/@@folder_contents')

      >>> browser.getControl('Copy')
      Traceback (most recent call last):
      ...
      LookupError: label 'Copy'

      >>> browser.getControl('Cut')
      Traceback (most recent call last):
      ...
      LookupError: label 'Cut'

      >>> browser.getControl('Rename')
      Traceback (most recent call last):
      ...
      LookupError: label 'Rename'

      >>> browser.getControl('Delete')
      Traceback (most recent call last):
      ...
      LookupError: label 'Delete'

      >>> browser.getControl('Change State')
      Traceback (most recent call last):
      ...
      LookupError: label 'Change State'

    The paste button should not be there yet either. We only want to see
    that when we have something copied.

      >>> browser.getControl('Paste')
      Traceback (most recent call last):
      ...
      LookupError: label 'Paste'

    When we look at a folder with content in it we should see more
    options.

      >>> browser.open('http://nohost/plone/@@folder_contents')

      >>> button = browser.getControl('Copy')
      >>> button = browser.getControl('Cut')
      >>> button = browser.getControl('Rename')
      >>> button = browser.getControl('Delete')
      >>> button = browser.getControl('Change State')

    Still the paste button should not be available.

      >>> browser.getControl('Paste')
      Traceback (most recent call last):
      ...
      LookupError: label 'Paste'

    Now we shall copy something so we can paste it.

      >>> objects = browser.getControl(name='paths:list')
      >>> objects.value = objects.options[0:1]
      >>> browser.getControl('Copy').click()

    Because we have copied something the paste button should show up.

      >>> button = browser.getControl('Paste')

    It should also show up in our empty folder.

      >>> browser.open('http://nohost/plone/empty-folder/@@folder_contents')
      >>> button = browser.getControl('Paste')


    Batching
    --------

    Because we have no content there should not be any batching.

      >>> browser.open('http://nohost/plone/@@folder_contents')
      >>> browser.getLink('Next 20 items')
      Traceback (most recent call last):
      ...
      LinkNotFoundError

    Create a few pages so that we have some content to play with.

      >>> self.createDocuments(65)

      >>> browser.open('http://nohost/plone/@@folder_contents')
      >>> 'Testing' in browser.contents
      True

    Now that we have a lot of pages we should also have some batching.

      >>> browser.getLink('Next 20 items')
      <Link ...>

    One of the later pages should not be in our current screen.

      >>> 'Testing \xc3\xa4 20' in browser.contents
      False

    Now when we go to the second screen it should show up.

      >>> browser.getLink('2').click()
      >>> 'Testing \xc3\xa4 20' in browser.contents
      True

    We should also have at most four pages of batched items. So at page four there
    should be no way to go further.

      >>> browser.getLink('4').click()
      >>> browser.getLink('Next 20 items')
      Traceback (most recent call last):
      ...
      LinkNotFoundError

    The batching navigation also should allow us to go back to previous pages.

      >>> browser.getLink('Previous 20 items')
      <Link ...>

    When we are at the first page this link should not be shown.

      >>> browser.open('http://nohost/plone/@@folder_contents')
      >>> browser.getLink('Previous 20 items')
      Traceback (most recent call last):
      ...
      LinkNotFoundError

    Selection
    ---------

    The folder contents view supports quite elaborate selection techniques. You can
    select items individually or group wise. We will now demonstrate how the group
    wise selection works.

      >>> browser.open('http://nohost/plone/@@folder_contents')

    First we can select all items on screen.

      >>> browser.getLink(id='foldercontents-selectall').click()

    This will show a message that only the items on the screen are selected.

      >>> print browser.contents
      <BLANKLINE>
      ... All 20 items on this page are selected...

    We now have a way to select all items in the batch.

      >>> browser.getLink(id='foldercontents-selectall-completebatch').click()

    This should have selected everything.

      >>> print browser.contents
      <BLANKLINE>
      ... All ... items in this folder are selected. ...

    We can also clear the selection, this will deselect everything.

      >>> browser.getLink(id='foldercontents-clearselection').click()

    Now we are back to square one and we can select all items on the screen again.

      >>> browser.getLink(id='foldercontents-selectall')
      <Link ...>

    The steps described are bit different for when we only have a few items. First
    we clean up all items by removing everything.

      >>> browser.getLink(id='foldercontents-selectall').click()
      >>> browser.getLink(id='foldercontents-selectall-completebatch').click()
      >>> browser.getControl(name='folder_delete:method').click()

    Notice that is no way to select any items now. This is because there
    is nothing to select.

      >>> browser.getLink(id='foldercontents-selectall')
      Traceback (most recent call last):
      ...
      LinkNotFoundError

    Now we will add some documents again.

      >>> self.createDocuments(3)

    When we press the select all button it should no longer offer us to select the
    whole batch because we are showing everything already.

      >>> browser.open('http://nohost/plone/@@folder_contents')
      >>> browser.getLink(id='foldercontents-selectall').click()
      >>> print browser.contents
      <BLANKLINE>
      ... All ... items in this folder are selected...

      >>> browser.getLink(id='foldercontents-selectall-completebatch')
      Traceback (most recent call last):
      ...
      LinkNotFoundError

    Instead we should now be able to clear the selection.

      >>> browser.getLink(id='foldercontents-clearselection')
      <Link ...>


    Going up
    --------

    When you are looking at the contents of a folder you might want to
    navigate to a different folder. This can be done by going to the
    parent folder.

    To show this we will need to create a folder first.

      >>> self.createFolder()

    Now we can go to this folder.

      >>> browser.open('http://nohost/plone/new-folder/@@folder_contents')

    In this folder contents view we should have link to go to the site root.

      >>> browser.getLink('Up one level')
      <Link ...>

    Now lets click it.

      >>> browser.getLink('Up one level').click()
      >>> browser.url
      'http://nohost/plone/folder_contents'

    In the site root we should not be able to go up any further.

      >>> browser.getLink('Up one level')
      Traceback (most recent call last):
      ...
      LinkNotFoundError


    Expanding the batch
    -------------------

    Sometimes you might want to see all the items in the folder. To make
    this possible you can ask the folder contents to show everything
    without enabling batching.

    Before we demonstrate we need to clear out the existing contents and
    create some new content.

      >>> browser.getLink(id='foldercontents-selectall').click()
      >>> browser.getControl(name='folder_delete:method').click()

    Putting only one page into the folder will not show the option to
    disable batching since there is no batching.

      >>> self.createDocuments(1)
      >>> browser.open('http://nohost/plone/@@folder_contents')
      >>> browser.getLink('Show all items')
      Traceback (most recent call last):
      ...
      LinkNotFoundError

    Create some more pages to show the batch disabling feature.

      >>> browser.open('http://nohost/plone/@@folder_contents')
      >>> browser.getLink(id='foldercontents-selectall').click()
      >>> browser.getControl(name='folder_delete:method').click()
      >>> self.createDocuments(60)

    Now we can show all the items in the folder if we want to.

      >>> browser.open('http://nohost/plone/@@folder_contents')
      >>> browser.getLink('Show all items').click()

    You can see all the items are now on the page.

      >>> browser.contents
      '...Testing \xc3\xa4 1...Testing \xc3\xa4 11...Testing \xc3\xa4 60...'

    Selecting the current page should make the entire folder selected
    (since we see everything).

      >>> browser.getLink(id='foldercontents-selectall').click()
      >>> print browser.contents
      <BLANKLINE>
      ... All ... items in this folder are selected. ...

"""
########NEW FILE########
__FILENAME__ = test_workflow_panel
import unittest2 as unittest

from datetime import datetime, timedelta
from DateTime import DateTime

from plone.app.cmsui.testing import CMSUI_FUNCTIONAL_TESTING
from plone.app.cmsui.testing import browser_login
from plone.app.testing import TEST_USER_ID
from plone.app.testing import setRoles
from plone.testing.z2 import Browser
import transaction

from plone.app.cmsui.tests import createObject

class TestWorkflowPanel(unittest.TestCase):

    layer = CMSUI_FUNCTIONAL_TESTING

    def test_panel_linked_to_in_menu(self):
        browser = Browser(self.layer['app'])
        portal = self.layer['portal']
        setRoles(portal, TEST_USER_ID, ('Member', 'Manager'))
        document = createObject(portal, "Document", "panel_linked_to_in_menu_doc", delete_first=True, title="Workflow transitions")
        # Commit so the change in roles is visible to the browser
        transaction.commit()
        
        browser_login(portal, browser)
        browser.open(document.absolute_url())
        browser.getLink("Manage page").click()
        
        # raises exception if not present
        browser.getLink("Public draft").click()
        self.assertIn("form.widgets.workflow_action", browser.contents)

    def test_available_workflow_transition_shown_in_workflow_panel(self):
        browser = Browser(self.layer['app'])
        portal = self.layer['portal']
        setRoles(portal, TEST_USER_ID, ('Member', 'Manager'))
        document = createObject(portal, "Document", "transition_shown_in_workflow_panel_doc", delete_first=True, title="Workflow transitions")
        # Commit so the change in roles is visible to the browser
        transaction.commit()
        
        browser_login(portal, browser)
        browser.open(document.absolute_url())
        browser.getLink("Manage page").click()
        browser.getLink("Public draft").click()
        
        # The submit button should be available
        transitions = portal.portal_workflow.getTransitionsFor(document)
        transition_ids = [transition['id'] for transition in transitions]
        # Ensure the workflow transition we are going to look for in the
        # workflow panel is actually available to save debugging headaches
        # later
        self.assertEqual(sorted(['submit', 'hide', 'publish']), sorted(transition_ids))
        
        # Make sure we have both labels and values for all possible workflow actions
        workflow_actions = browser.getControl(name="form.widgets.workflow_action:list")
        self.assertEqual(len(workflow_actions.mech_control.items),3)
        self.assertEqual(workflow_actions.getControl(label='Submit for publication').optionValue, 'submit')
        self.assertEqual(workflow_actions.getControl(label='Make private').optionValue, 'hide')
        self.assertEqual(workflow_actions.getControl(label='Publish').optionValue, 'publish')
    
    def test_choosing_transition_transitions_content(self):
        browser = Browser(self.layer['app'])
        portal = self.layer['portal']
        setRoles(portal, TEST_USER_ID, ('Member', 'Manager'))
        document = createObject(portal, "Document", "do_workflow_transition_doc", delete_first=True, title="Workflow transitioning")
        transaction.commit()
        
        browser_login(portal, browser)
        browser.open(document.absolute_url())
        browser.getLink("Manage page").click()
        browser.getLink("Public draft").click()
        workflow_actions = browser.getControl(name="form.widgets.workflow_action:list")
        workflow_actions.getControl(value="publish").click()
        browser.getControl("Save").click()
        
        self.assertEqual("published", portal.portal_workflow.getInfoFor(document, "review_state"))
    
    def test_can_enter_changenote(self):
        browser = Browser(self.layer['app'])
        portal = self.layer['portal']
        setRoles(portal, TEST_USER_ID, ('Member', 'Manager'))
        document = createObject(portal, "Document", "changenote_transition_doc", delete_first=True, title="Workflow note")
        transaction.commit()
        
        browser_login(portal, browser)
        browser.open(document.absolute_url())
        browser.getLink("Manage page").click()
        browser.getLink("Public draft").click()
        workflow_actions = browser.getControl(name="form.widgets.workflow_action:list")
        workflow_actions.getControl(value="publish").click()
        # We set up a comment this time
        browser.getControl(name="form.widgets.comment").value = "wibble fkjwel"
        browser.getControl("Save").click()
        
        # and it shows up in the workflow history
        self.assertEqual("publish", document.workflow_history['plone_workflow'][-1]['action'])
        self.assertEqual("wibble fkjwel", document.workflow_history['plone_workflow'][-1]['comments'])
    
    def test_can_enter_effective_date(self):
        browser = Browser(self.layer['app'])
        portal = self.layer['portal']
        setRoles(portal, TEST_USER_ID, ('Member', 'Manager'))
        document = createObject(portal, "Document", "effective_date_transition_doc", delete_first=True, title="Workflow note")
        transaction.commit()
        
        browser_login(portal, browser)
        browser.open(document.absolute_url())
        browser.getLink("Manage page").click()
        browser.getLink("Public draft").click()
        workflow_actions = browser.getControl(name="form.widgets.workflow_action:list")
        workflow_actions.getControl(value="publish").click()
        # We set up a comment this time
        
        tommorow = datetime.now() + timedelta(1)
        tommorow = tommorow - timedelta(seconds=tommorow.second,
                                        microseconds=tommorow.microsecond)
        browser.getControl(name="form.widgets.effective_date-day").value = str(tommorow.day)
        browser.getControl(name="form.widgets.effective_date-month").value = [str(tommorow.month)]
        browser.getControl(name="form.widgets.effective_date-year").value = str(tommorow.year)
        browser.getControl(name="form.widgets.effective_date-hour").value = str(tommorow.hour)
        browser.getControl(name="form.widgets.effective_date-min").value = str(tommorow.minute)
        browser.getControl("Save").click()
        
        # and it shows up in the workflow history
        self.assertEqual("publish", document.workflow_history['plone_workflow'][-1]['action'])
        self.assertEqual("published", portal.portal_workflow.getInfoFor(document, "review_state"))
        self.assertEqual(DateTime(tommorow), document.getRawEffectiveDate())
        
        # cleanup
        portal.manage_delObjects(['effective_date_transition_doc'])

    def test_can_enter_expiry_date(self):
        browser = Browser(self.layer['app'])
        portal = self.layer['portal']
        setRoles(portal, TEST_USER_ID, ('Member', 'Manager'))
        document = createObject(portal, "Document", "effective_date_transition_doc", delete_first=True, title="Workflow note")
        transaction.commit()
        
        browser_login(portal, browser)
        browser.open(document.absolute_url())
        browser.getLink("Manage page").click()
        browser.getLink("Public draft").click()
        workflow_actions = browser.getControl(name="form.widgets.workflow_action:list")
        workflow_actions.getControl(value="publish").click()
        # We set up a comment this time
        
        next_year = datetime.now() + timedelta(365)
        next_year = next_year - timedelta(seconds=next_year.second,
                                        microseconds=next_year.microsecond)
        browser.getControl(name="form.widgets.expiration_date-day").value = str(next_year.day)
        browser.getControl(name="form.widgets.expiration_date-month").value = [str(next_year.month)]
        browser.getControl(name="form.widgets.expiration_date-year").value = str(next_year.year)
        browser.getControl(name="form.widgets.expiration_date-hour").value = str(next_year.hour)
        browser.getControl(name="form.widgets.expiration_date-min").value = str(next_year.minute)
        browser.getControl("Save").click()
        
        # and it shows up in the workflow history
        self.assertEqual("publish", document.workflow_history['plone_workflow'][-1]['action'])
        self.assertEqual("published", portal.portal_workflow.getInfoFor(document, "review_state"))
        self.assertEqual(DateTime(next_year), document.getRawExpirationDate())
        
        portal.manage_delObjects(['effective_date_transition_doc'])

    def test_can_enter_expiration_date_without_transaction(self):
        browser = Browser(self.layer['app'])
        portal = self.layer['portal']
        setRoles(portal, TEST_USER_ID, ('Member', 'Manager'))
        document = createObject(portal, "Document", "expiration_date_without_transition_doc", delete_first=True, title="Workflow note")
        transaction.commit()
        
        browser_login(portal, browser)
        browser.open(document.absolute_url())
        browser.getLink("Manage page").click()
        browser.getLink("Public draft").click()
        
        # Don't select any workflow action, but set date
        next_year = datetime.now() + timedelta(365)
        next_year = next_year - timedelta(seconds=next_year.second,
                                        microseconds=next_year.microsecond)
        browser.getControl(name="form.widgets.expiration_date-day").value = str(next_year.day)
        browser.getControl(name="form.widgets.expiration_date-month").value = [str(next_year.month)]
        browser.getControl(name="form.widgets.expiration_date-year").value = str(next_year.year)
        browser.getControl(name="form.widgets.expiration_date-hour").value = str(next_year.hour)
        browser.getControl(name="form.widgets.expiration_date-min").value = str(next_year.minute)
        browser.getControl("Save").click()
        
        # Still draft, but expiration date set
        self.assertEqual("visible", portal.portal_workflow.getInfoFor(document, "review_state"))
        self.assertEqual(DateTime(next_year), document.getRawExpirationDate())

########NEW FILE########
__FILENAME__ = uploadcapable
# -*- coding: utf-8 -*-
#
#
# Copyright (c) InQuant GmbH
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from thread import allocate_lock

import transaction
from AccessControl import Unauthorized
from ZODB.POSException import ConflictError
from Acquisition import aq_inner
from zope import interface
from zope import component
from zope.event import notify
from zope.app.container.interfaces import INameChooser

from plone.i18n.normalizer.interfaces import IIDNormalizer
from Products.Archetypes.event import ObjectInitializedEvent

# from collective.quickupload import logger
from plone.app.cmsui.interfaces import (
    IQuickUploadCapable, IQuickUploadFileFactory)


upload_lock = allocate_lock()

class QuickUploadCapableFileFactory(object):
    interface.implements(IQuickUploadFileFactory)
    component.adapts(IQuickUploadCapable)

    def __init__(self, context):
        self.context = aq_inner(context)

    def __call__(self, name, title, description, content_type, data, portal_type):

        context = aq_inner(self.context)
        charset = context.getCharset()
        filename = name
        name = name.decode(charset)
        error = ''
        result = {}
        result['success'] = None
        normalizer = component.getUtility(IIDNormalizer)
        chooser = INameChooser(self.context)

        # normalize all filename but dots
        normalized = ".".join([normalizer.normalize(n) for n in name.split('.')])
        newid = chooser.chooseName(normalized, context)

        # consolidation because it's different upon Plone versions
        newid = newid.replace('_','-').replace(' ','-').lower()
        if not title :
            # try to split filenames because we don't want
            # big titles without spaces
            title = name.split('.')[0].replace('_',' ').replace('-',' ')
        if newid in context.objectIds() :
            # only here for flashupload method since a check_id is done
            # in standard uploader - see also XXX in quick_upload.py
            raise NameError, 'Object id %s already exists' %newid
        else :
            upload_lock.acquire()
            transaction.begin()
            try:
                context.invokeFactory(type_name=portal_type, id=newid, title=title, description=description)
            except Unauthorized :
                error = u'serverErrorNoPermission'
            except ConflictError :
                # rare with xhr upload / happens sometimes with flashupload
                error = u'serverErrorZODBConflict'
            except Exception, e:
                error = u'serverError'
                # logger.exception(e)

            if not error :
                obj = getattr(context, newid)
                if obj :
                    primaryField = obj.getPrimaryField()
                    if primaryField is not None:
                        mutator = primaryField.getMutator(obj)
                        # mimetype arg works with blob files
                        mutator(data, content_type=content_type, mimetype=content_type)
                        # XXX when getting file through request.BODYFILE (XHR direct upload)
                        # the filename is not inside the file
                        # and the filename must be a string, not unicode
                        # otherwise Archetypes raise an error (so we use filename and not name)
                        if not obj.getFilename() :
                            if isinstance(filename, unicode):
                                filename = filename.encode(charset)
                            obj.setFilename(filename)
                        obj.reindexObject()
                        notify(ObjectInitializedEvent(obj))
                    else :
                        # some products remove the 'primary' attribute on ATFile or ATImage (which is very bad)
                        error = u'serverError'
                        # logger.info("An error happens : impossible to get the primary field for file %s, rawdata can't be created" %obj.absolute_url())
                else:
                    error = u'serverError'
                    # logger.info("An error happens with setId from filename, the file has been created with a bad id, can't find %s" %newid)
            transaction.commit()
            upload_lock.release()

        result['error'] = error
        if not error :
            result['success'] = obj
        return result

########NEW FILE########
__FILENAME__ = workflowpanel
from datetime import datetime
from DateTime import DateTime

from zExceptions import Unauthorized
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from plone.app.cmsui.interfaces import _

from zope.interface import Interface, implements
from zope import schema
from z3c.form import form, field, button
from zope.schema import vocabulary, interfaces
from z3c.form.browser.radio import RadioFieldWidget


class WorkflowActionsSourceBinder(object):
    implements(interfaces.IContextSourceBinder)
    """Generates vocabulary for all allowed workflow transitions"""

    def getTransitions(self):
        wft = getToolByName(self.context, 'portal_workflow')
        return wft.getTransitionsFor(self.context)

    def __call__(self, context):
        wft = getToolByName(context, 'portal_workflow')
        return vocabulary.SimpleVocabulary([
            vocabulary.SimpleVocabulary.createTerm(t['id'], t['id'], _(t['name']))
            for t in wft.getTransitionsFor(context)
        ])


class IWorkflowPanel(Interface):
    """Form for workflow panel"""
    workflow_action = schema.Choice(
        title=_(u'label_change_status', u"Change State"),
        description=_(u'help_change_status_action',
                          default=u"Select the transition to be used for modifying the items state."),
        source=WorkflowActionsSourceBinder(),
        required=False,
        )
    comment = schema.Text(
        title=_(u"label_comments", u"Comments"),
        description=_(u'help_publishing_comments',
                          default=u"Will be added to the publishing history. If multiple "
                                   "items are selected, this comment will be attached to all of them."),
        required=False,
        )
    effective_date = schema.Datetime(
        title=_(u'label_effective_date', u'Publishing Date'),
        description=_(u'help_effective_date',
                          default=u"If this date is in the future, the content will "
                                   "not show up in listings and searches until this date."),
        required=False
        )
    expiration_date = schema.Datetime(
        title=_(u'label_expiration_date', u'Expiration Date'),
        description=_(u'help_expiration_date',
                              default=u"When this date is reached, the content will no"
                                       "longer be visible in listings and searches."),
        required=False
        )


class WorkflowPanel(form.Form):
    """Shows a panel with the advanced workflow options
    """

    @property
    def label(self):
        return _(u'Workflow for ${name}', mapping={'name': safe_unicode(self.context.Title())})

    def render(self):
        return self.index()

    css_class = 'overlayForm'

    fields = field.Fields(IWorkflowPanel)
    fields['workflow_action'].widgetFactory = RadioFieldWidget
    ignoreContext = True

    def updateActions(self):
        super(WorkflowPanel, self).updateActions()
        self.actions["cancel"].addClass("overlayCloseAction")

    @button.buttonAndHandler(_(u'Save'))
    def handleSave(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        # Context might be temporary
        real_context = self.context.portal_factory.doCreate(self.context)

        # Read form
        workflow_action = data.get('workflow_action', '')
        effective_date = data.get('effective_date', None)
        if workflow_action and not effective_date and real_context.EffectiveDate() == 'None':
            effective_date = DateTime()
        expiration_date = data.get('expiration_date', None)

        # Try editing content, might not be able to yet
        retryContentEdit = False
        try:
            self._editContent(real_context, effective_date, expiration_date)
        except Unauthorized:
            retryContentEdit = True

        postwf_context = None
        if workflow_action is not None:
            postwf_context = real_context.portal_workflow.doActionFor(self.context,
                             workflow_action, comment=data.get('comment', ''))
        if postwf_context is None:
            postwf_context = real_context

        # Retry if need be
        if retryContentEdit:
            self._editContent(postwf_context, effective_date, expiration_date)

        self.request.response.redirect(postwf_context.absolute_url())

    @button.buttonAndHandler(_(u'Cancel'))
    def cancel(self, action):
        self.request.response.redirect(self.context.absolute_url())

    def _editContent(self, context, effective, expiry):
        kwargs = {}
        if isinstance(effective, datetime):
            kwargs['effective_date'] = DateTime(effective)
        # may contain the year
        elif effective and (isinstance(effective, DateTime) or len(effective) > 5):
            kwargs['effective_date'] = effective
        if isinstance(expiry, datetime):
            kwargs['expiration_date'] = DateTime(expiry)
        # may contain the year
        elif expiry and (isinstance(expiry, DateTime) or len(expiry) > 5):
            kwargs['expiration_date'] = expiry
        context.plone_utils.contentEdit(context, **kwargs)

########NEW FILE########
