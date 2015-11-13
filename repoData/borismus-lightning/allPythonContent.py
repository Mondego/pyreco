__FILENAME__ = AppDelegate
#-*- coding: utf-8 -*-
#
#  LightningAppDelegate.py
#  Lightning
#
#  Created by Boris Smus on 7/12/13.
#  Copyright Boris Smus 2013. All rights reserved.
#

#from Foundation import *
from Foundation import NSObject, NSLog
from Cocoa import NSWindowController


class AppDelegate(NSObject):

    def applicationWillTerminate_(self,sender):
        NSLog("Application will terminate.")

    def applicationShouldTerminateAfterLastWindowClosed_(self, sender):
        return False
    
    def applicationDidFinishLaunching_(self, sender):
        NSLog("Application did finish launching.")
########NEW FILE########
__FILENAME__ = LinkTextProcessor
#-*- coding: utf-8 -*-
#
#  LinkTextProcessor.py
#  Lightning
#
#  Created by Boris Smus on 7/13/13.
#  Copyright (c) 2013 Boris Smus. All rights reserved.
#

from __future__ import print_function
from Syndicator import *

import re
import os
import datetime
import codecs
import subprocess
import threading

import unidecode

from Foundation import NSLog, NSBundle

class LinkTextProcessor:
    """
    Given the text of a link entry, does the following:

    Previewing:
    - Extracts URL from the text.
    - Creates a link entry in the lightning directory structure.
    - Previews how this looks locally.

    Publishing:
    - Publishes the lightning blog to S3.
    - Gets the published URL.
    - For each sharing service, decides what to share.

    Cleaning up:
    - Removes the newly added link.

    Naming:
    - Generates a unique slug for the link.
    - Based on that slug, gets the URL to the content.
    - If the slug changes, renames directory.
    """

    PREVIEW_URL = 'http://localhost/'
    BLOG_URL = 'http://smus.com/'
    BLOG_ROOT = '/Users/smus/Projects/smus.com/'
    LINK_ROOT = os.path.join(BLOG_ROOT, 'content/links')
    PYTHON = '/usr/bin/python'
    LIGHTNING = './lightning/lightning'
    LOG_PATH = 'lightning-gui.log'

    def __init__(self, syndicators=[]):
        self.is_first_run = True
        # The syndication services which to publish to.
        self.syndicators = syndicators


    def set_content(self, url, title, body):
        """
        Called when the preview changes.
        """
        # First clean any existing links.
        if self.is_first_run:
            self.is_first_run = False
        else:
            self.clean()

        self.url = url
        self.title = title
        self.body = body
        # Get a simple slug out of the title.
        self.slug = self.generate_slug(self.title)
        # Create a link file.
        return self.create_link_file(self.slug, self.url, self.title, self.body)


    def preview(self, url=PREVIEW_URL):
        """
        Preview the link to see how it would look locally.
        """
        NSLog("Starting a preview.")
        # Rebuild the blog locally.
        self.build_blog()
        # Open a browser to see the local preview.
        bundle = NSBundle.mainBundle()
        script_path = bundle.pathForResource_ofType_('open-chrome-tab', 'scpt')
        self.run_command_async('osascript', script_path, url)
    
    def preview_content(self):
        self.preview(self.get_preview_url())

    def publish(self):
        # Rebuild the blog locally.
        self.build_blog()
        # Publish the blog to S3.
        self.publish_blog()

    def publish_syndicate(self):
        """
        Called when the publish button is clicked.
        """
        # Rebuild the blog locally.
        self.build_blog()
        # Get the URL of the published link.
        blog_url = self.get_published_url()
        # Publish the blog to S3 (but just the permalink and archives).
        self.publish_permalink(self.get_relative_permalink())
        print('Published new link to: ' + blog_url)
        for syn in self.syndicators:
            try:
                syn.set_info(self.url, blog_url, self.title, self.body)
                syn.publish()
            except Exception as e:
                NSLog("Exception: %s" % str(e))


    def clean(self):
        """
        Called to clean up the link entry.
        """
        if not hasattr(self, 'slug'):
            return
        # Remove the link directory and rebuild the blog.
        link_path = self.get_link_path(self.slug)
        if os.path.exists(link_path):
            os.remove(link_path)
            self.build_blog()

    #####
    ##### Private methods
    #####

    def generate_slug(self, title):
        """
        Called to generate a short unique slug from the link text.
        """
        slug = unidecode.unidecode(title).lower()
        return re.sub(r'\W+','-', slug)


    def get_link_path(self, slug):
        return os.path.join(self.LINK_ROOT, slug + '.txt')


    def create_link_file(self, slug, url, title, body):
        """
        Creates a link index file in the link directory. Format:

        Title of Link
        =============
        posted: 2013-07-14

        Body of link goes here (markdown).
        """
        path = self.get_link_path(slug)
        print('Got link path: ' + path)
        # Ensure that the path is unique.
        if os.path.exists(path):
            raise Exception('Link already exists at specified path: %s.' % path)
            return False

        # Create a file and start writing things to it.
        #f = open(path, 'w')
        f = codecs.open(path, 'w', encoding='utf-8')
        # First write the title.
        print(title, file=f)
        # Next a separator.
        print('=' * len(title), file=f)
        # Post the date in YAML.
        now = datetime.datetime.now()
        print('posted: %s' % now.strftime('%Y-%m-%d'), file=f)
        # Add a link.
        print('link: %s' % url, file=f)
        # Lastly, write the body of the link.
        print('\n' + body, file=f)
        print('Printed to file')
        f.close()
        return True


    def build_blog(self):
        self.run_command_async(self.PYTHON, self.LIGHTNING, 'build')


    def publish_blog(self):
        self.run_command_async(self.PYTHON, self.LIGHTNING, 'deploy')
    
    def publish_permalink(self, path):
        self.run_command_async(self.PYTHON, self.LIGHTNING, 'deploy_permalink', path)

    def get_published_url(self):
        return os.path.join(self.BLOG_URL, self.get_relative_permalink())
    
    def get_preview_url(self):
        return os.path.join(self.PREVIEW_URL, self.get_relative_permalink())
    
    def get_relative_permalink(self):
        # TODO(smus): Make this actually respect the blog configuration.
        return 'link/%s/' % os.path.join(str(datetime.datetime.now().year), self.slug)

    def run_command_async(self, *args):
        task = CommandLineTask(args)
        task.set_cwd(self.BLOG_ROOT)
        task.start()
        while task.isAlive():
            pass
        # Periodically poll the task thread to see if it's done.
        # While polling, continuously call the callback with stdout.

class CommandLineTask(threading.Thread):
    def __init__(self, args):
        self.args = args
        self.out = None
        self.err = None
        threading.Thread.__init__(self)
    
    def set_cwd(self, cwd):
        self.cwd = cwd

    def run(self):
        NSLog("Running command: %s" % ' '.join(self.args))
        logfile = open(LinkTextProcessor.LOG_PATH, 'w')
        process = subprocess.Popen(self.args, shell=False, cwd=self.cwd, env={},
                                   stdout=logfile,
                                   stderr=subprocess.PIPE)
        # Wait for the process to terminate.
        self.out, self.err = process.communicate()
        returncode = process.returncode
        # Debug only: output results of the command.
        if returncode == 0:
            NSLog("Ran command: %s. Output: %s." % (' '.join(self.args), self.out))
        else:
            NSLog("Failed command: %s. Error: %s." % (' '.join(self.args), self.err))


if __name__ == '__main__':
    test_url = 'http://procrastineering.blogspot.com/2012/04/projects-at-google-x.html'
    test_title = 'Projects at Google X'
    test_title2 = 'Cool Projects at X'
    test_body = '''> These past couple weeks, there have been a few videos released from
> the group I work in at Google. Congratulations to the many people in X
> who's hard work has gone into each of these.

Google X released a few concept videos of projects in their pipeline.
Very exciting stuff to see this great work slowly trickle out to the
public.'''
    # Run some tests.
    ltp = LinkTextProcessor()
    ltp.set_content(test_url, test_title, test_body)
    ltp.preview()
    ltp.set_content(test_url, test_title2, test_body)
    ltp.preview()
    ltp.clean()

########NEW FILE########
__FILENAME__ = main
#-*- coding: utf-8 -*-
#
#  main.py
#  Lightning
#
#  Created by Boris Smus on 7/12/13.
#  Copyright Boris Smus 2013. All rights reserved.
#

#import modules required by application
import objc
import Foundation
import AppKit

from PyObjCTools import AppHelper

# import modules containing classes required to start application and load MainMenu.nib
import AppDelegate
import PMController

if __name__ == "__main__":
    # pass control to AppKit
    AppHelper.runEventLoop()

########NEW FILE########
__FILENAME__ = PMController
#-*- coding: utf-8 -*-
#
#  MyWindowController.py
#  Lightning
#
#  Created by Boris Smus on 7/12/13.
#  Copyright (c) 2013 Boris Smus. All rights reserved.
#

from objc import YES, NO, IBAction, IBOutlet
#from Foundation import *
from Foundation import NSLog
#from AppKit import *
from AppKit import NSWindowController, NSFont, NSOnState, NSApp, NSNotificationCenter, NSApplicationWillTerminateNotification

# Required for status bar stuff.
from AppKit import NSStatusBar, NSSquareStatusItemLength, NSVariableStatusItemLength, NSImage, NSMenu, NSMenuItem, NSShiftKeyMask, NSCommandKeyMask, NSStatusWindowLevel


from LinkTextProcessor import *
from Syndicator import *

class PMController(NSWindowController):

    titleField = IBOutlet()
    urlField = IBOutlet()
    bodyField = IBOutlet()
    charCountLabel = IBOutlet()
    actionButton = IBOutlet()
    twitterCheckbox = IBOutlet()
    gplusCheckbox = IBOutlet()
    
    # Confirm token sheet.
    confirmTokenSheet = IBOutlet()
    confirmTokenField = IBOutlet()
    
    # Publish log sheet.
    publishLogWindow = IBOutlet()
    publishLogField = IBOutlet()
    publishCancelButton = IBOutlet()

    twitter = TwitterSyndicator()
    gplus = GPlusSyndicator()
    ltp = LinkTextProcessor()
    

    def awakeFromNib(self):
        NSLog("Awake from nib.")
        self.setPreviewMode(True)
        self.bodyField.setDelegate_(self)
        self.urlField.setDelegate_(self)
        self.titleField.setDelegate_(self)

        # Style the bodyField.
        self.bodyField.setFont_(NSFont.fontWithName_size_("Monaco", 13))
        self.bodyField.setRichText_(NO)
        self.bodyField.setUsesFontPanel_(NO)
    
        # Authenticate to twitter if we can.
        if self.twitter.is_authenticated():
            self.twitter.login()
            self.twitterCheckbox.setState_(NSOnState)
            self.ltp.syndicators.append(self.twitter)
        
        # Authenticate to G+ if we can.
        if self.gplus.is_authenticated():
            self.gplus.login()
            self.gplusCheckbox.setState_(NSOnState)
            self.ltp.syndicators.append(self.gplus)

        # Listen to the NSApplicationWillTerminateNotification.
        center = NSNotificationCenter.defaultCenter()
        center.addObserver_selector_name_object_(self, "applicationWillTerminateNotification:", NSApplicationWillTerminateNotification, None)
                
        self.setupStatusBar()

        self.didPublish = False
        self.didPreview = False


    def applicationWillTerminateNotification_(self, notification):
        NSLog("applicationWillTerminateNotification_")


    @IBAction
    def post_(self, sender):
        url = self.urlField.stringValue()
        title = self.titleField.stringValue()
        body = self.bodyField.string()
        # TODO(smus): Validate all fields.

        if self.isPreview:
            # Relinquish control to the link text processor for a preview.
            self.ltp.set_content(url, title, body)
            # Show the preview in a browser window.
            self.ltp.preview_content()
            # Go into publish mode.
            self.setPreviewMode(False)
            self.didPreview = True
        else:
            # If in publish mode, push to S3, publish to twitter & G+.
            print 'Syndicators: ' + str(self.ltp.syndicators)
            self.ltp.publish_syndicate()
            self.didPublish = True
            self.hideWindow()

    @IBAction
    def cancel_(self, sender):
        NSLog(u"Cancel")
        # Remove the link if one was created.
        self.ltp.clean()
        # Exit the application.
        self.hideWindow()
    
    @IBAction
    def twitterChecked_(self, sender):
        if self.twitterCheckbox.state() == NSOnState:
            self.twitter.login()
            if not self.twitter.is_authenticated():
                self.currentService = self.twitter
                self.showTheSheet_(sender)

        isTwitterEnabled = bool(self.twitterCheckbox.state() == NSOnState)
        if isTwitterEnabled:
            self.ltp.syndicators.append(self.twitter)
        else:
            self.ltp.syndicators.remove(self.twitter)

    @IBAction
    def gplusChecked_(self, sender):
        if self.gplusCheckbox.state() == NSOnState:
            self.gplus.login()
            print self.gplus.is_authenticated()
            if not self.gplus.is_authenticated():
                self.currentService = self.gplus
                self.showTheSheet_(sender)
        
        isGPlusEnabled = bool(self.gplusCheckbox.state() == NSOnState)
        if isGPlusEnabled:
            self.ltp.syndicators.append(self.gplus)
        else:
            self.ltp.syndicators.remove(self.gplus)

    @IBAction
    def confirmToken_(self, sender):
        NSLog("Confirmed token")
        verifier = self.confirmTokenField.stringValue()

        if self.currentService == self.twitter:
            self.twitter.confirm_verifier(verifier)
        elif self.currentService == self.gplus:
            self.gplus.confirm_verifier(verifier)
                
        self.endTheSheet_(sender)

    @IBAction
    def cancelToken_(self, sender):
        self.endTheSheet_(sender)

    def doPreview_(self, sender):
        NSLog("Doing a preview.")
        self.ltp.preview()

    def doPublish_(self, sender):
        NSLog("Doing a publish.")
        self.ltp.publish()
    
    def doLink_(self, sender):
        NSLog("Doing a link.")
        self.showWindow()


    def showTheSheet_(self, sender):
        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
                self.confirmTokenSheet, NSApp.mainWindow(), self, None, None)

    def endTheSheet_(self, sender):
        NSApp.endSheet_(self.confirmTokenSheet)
        self.confirmTokenSheet.orderOut_(sender)
    
    def hideWindow(self):
        # Hide the window.
        self.window().orderOut_(self)
        
        # Cleanup if the app did not publish (to keep state consistent).
        if not self.didPublish:
            self.ltp.clean()

        # Reset the internal state.
        self.didPreview = False
        self.didPublish = False
        
        # Clear all of the UI elements.
        self.titleField.setStringValue_('')
        self.urlField.setStringValue_('')
        self.bodyField.setString_('')
    
    def showWindow(self):
        self.window().makeKeyAndOrderFront_(self)
        self.window().setLevel_(NSStatusWindowLevel)
        # Give the window focus.
        NSApp.activateIgnoringOtherApps_(YES)

    def setPreviewMode(self, isPreview):
        self.isPreview = isPreview
        # Update the UI.
        self.actionButton.setTitle_(isPreview and "Preview" or "Publish")

    def controlTextDidChange_(self, notification):
        # If any of the text changes, go into preview mode.
        self.setPreviewMode(True)
        self.enableButtonIfValid()

        changedField = notification.object()
        if changedField == self.urlField:
            # If the URL field, try to infer the title.
            url = self.urlField.stringValue()
            title = self.inferTitleFromURL(url)
            if title:
                NSLog("Setting title to be: " + title)
                self.titleField.setStringValue_(title)

    def textDidChange_(self, notification):
        # Go back to preview mode.
        self.setPreviewMode(True)
        self.enableButtonIfValid()
        # If the body text changes, update the count.
        text = self.bodyField.string()
        self.charCountLabel.setStringValue_(len(text))
        NSLog(u"Length: %d" % len(text))


    def inferTitleFromURL(self, url):
        from mechanize import Browser
        from urlparse import urlparse
        try:
            result = urlparse(url)
            if result.scheme not in ['http', 'https']:
                return None
            browser = Browser()
            browser.open(url)
            return unicode(browser.title(), 'utf8')
        except Exception as e:
            NSLog("Exception: " + str(e))
            return None

    def quit(self):
        NSApp.performSelector_withObject_afterDelay_("terminate:", None, 0);

    def enableButtonIfValid(self):
        # If all of the text fields have content in them, enable the button.
        # Otherwise, disable it.
        url = unicode(self.urlField.stringValue())
        title = unicode(self.titleField.stringValue())
        body = unicode(self.bodyField.string())
        isEnabled = url and title and body

        self.actionButton.setEnabled_(isEnabled and YES or NO)

    def setupStatusBar(self):
        statusbar = NSStatusBar.systemStatusBar()
        statusitem = statusbar.statusItemWithLength_(20).retain()
        
        icon = NSImage.imageNamed_('status')
        icon.setSize_((20, 20))
        statusitem.setImage_(icon)
        
        iconHighlight = NSImage.imageNamed_('status-hi')
        iconHighlight.setSize_((20, 20))
        statusitem.setAlternateImage_(iconHighlight)
        
        statusitem.setHighlightMode_(1)
        
        # TODO: Put this whole menu creation stuff into interface builder!
        menu = NSMenu.alloc().init()
        
        linkMenu = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Post a Link', 'doLink:', '')
        linkMenu.setTarget_(self);
        # Make it possible to invoke the link menu via a keyboard shortcut.
        linkMenu.setKeyEquivalentModifierMask_(NSShiftKeyMask | NSCommandKeyMask)
        linkMenu.setKeyEquivalent_('l')
        menu.addItem_(linkMenu)
        
        
        menu.addItem_(NSMenuItem.separatorItem())
        
        previewMenu = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Update Preview', 'doPreview:', '')
        previewMenu.setTarget_(self);
        menu.addItem_(previewMenu)
        
        publishMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Publish', None, '')
        publishMenu = NSMenu.alloc().init();
        s3MenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('S3', 'doPublish:', '')
        s3MenuItem.setTarget_(self);
        publishMenu.addItem_(s3MenuItem)
        publishMenuItem.setSubmenu_(publishMenu)
        menu.addItem_(publishMenuItem)
        
        menu.addItem_(NSMenuItem.separatorItem())

        quitMenu = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Quit', 'terminate:', '')
        menu.addItem_(quitMenu)
        
        statusitem.setMenu_(menu)
        menu.release();
    
    @IBAction
    def hidePublishLog_(self, sender):
        self.publishLogWindow.orderOut_(self);

    def showPublishLog(self):
        self.publishLogWindow.makeKeyAndOrderFront_(self);

########NEW FILE########
__FILENAME__ = Syndicator
from os.path import expanduser
import os
import pickle
import webbrowser
import string

# TODO: Separate TwitterSyndicator and GPlusSyndicator into own files.
# For twitter
import tweepy

# For G+
from oauth2client.client import OAuth2WebServerFlow
from urllib import urlencode
import httplib2
import json
import logging
logging.basicConfig()

class Syndicator:
    """
    Publishes a link to a service (eg. Twitter, G+).
    """
    # TODO: Set the service name.
    service_name = None
    prefs_path = '~/.lightning'

    def __init__(self):
        self.load_prefs()

    def load_prefs(self):
        """
        Loads the access token from a preference file.
        """
        path = expanduser(self.prefs_path)
        if os.path.exists(path):
            prefs_file = open(path, 'r')
            self.prefs = pickle.load(prefs_file)
            if not self.service_name in self.prefs:
                self.prefs[self.service_name] = {}
        else:
            self.prefs = {}
            self.prefs[self.service_name] = {}

    def save_prefs(self):
        """
        Sets the access token and saves it to the pickle.
        """
        prefs_file = open(expanduser(self.prefs_path), 'w')
        pickle.dump(self.prefs, prefs_file)

    def get(self, key):
        service = self.prefs[self.service_name]
        if key in service:
            return service[key]
        return None

    def set(self, key, value):
        self.prefs[self.service_name][key] = value
        self.save_prefs()

    def clear_all(self):
        # Clears all stored prefs.
        self.prefs[self.service_name] = {}
        self.save_prefs()


    def set_info(self, link_url, blog_url, title, body):
        """
        Publishes the link to the service.
        """
        self.title = title
        self.body = body
        self.blog_url = blog_url
        self.link_url = link_url


    def is_authenticated(self):
        # TODO: Implementation-specific.
        return False

    def publish(self):
        # TODO: Provide implementations in each syndicator.
        pass

    def markdown_to_plaintext(self, markdown_string):
        """
        Utility function to convert markdown to plaintext.
        """
        from BeautifulSoup import BeautifulSoup
        from markdown import markdown

        html = markdown(markdown_string)
        return ''.join(BeautifulSoup(html).findAll(text=True))

class TwitterSyndicator(Syndicator):
    """
    Shortens the text and URL to fit within 140 characters and publishes to
    Twitter.
    """
    service_name = 'Twitter'
    consumer_token = 'VNypXiSafjLkvMgk7eXLGQ'
    consumer_secret = 'UruEouAfvaVwmlcW32bzJ4mcuqmgfW4N3Ze3daouCI'
    auth = tweepy.OAuthHandler(consumer_token, consumer_secret)

    def publish(self):
        # If the title is too long, truncate it, leaving room for a URL.
        status = self.truncate_words(self.title, 110) + ' ' + self.link_url

        api = tweepy.API(self.auth)
        api.update_status(status)
        print "Published to Twitter."

    def truncate_words(self, text, char_limit):
        words = text.split(' ')
        buf = ''
        count = 0
        for word in words:
            count += len(word) + 1
            if count > char_limit:
                return buf.strip(string.punctuation + ' ') + '...'
            buf += word + ' '
        return buf.strip()

    def is_authenticated(self):
        key = self.get('key')
        secret = self.get('secret')
        return bool(key and secret)

    def login(self):
        # First, try getting the access token.
        if not self.is_authenticated():
            # If there's no token, start verification.
            self.verify()
            # At this point, wait for a callback to confirm_verifier with the
            # verification code.
        self.finish_login()

    def finish_login(self):
        key = self.get('key')
        secret = self.get('secret')
        self.auth.set_access_token(key, secret)

    def verify(self):
        try:
            redirect_url = self.auth.get_authorization_url()
            webbrowser.open(redirect_url)
        except tweepy.TweepError:
            print 'Error! Failed to get request token.'

    def confirm_verifier(self, verifier):
        try:
            self.auth.get_access_token(verifier)
        except tweepy.TweepError:
            print 'Error! Failed to get access token.'

        self.set('key', self.auth.access_token.key)
        self.set('secret', self.auth.access_token.secret)
        self.finish_login()



class GPlusSyndicator(Syndicator):
    """
    Publishes to Google Plus.
    """
    service_name = 'G+'
    client_id = '930206334662.apps.googleusercontent.com'
    client_secret = 'r2aq6CJDRAA3Dd5ODlUwHibk'
    scope = 'https://www.googleapis.com/auth/plus.stream.write ' + \
            'https://www.googleapis.com/auth/plus.me'
    flow = OAuth2WebServerFlow(client_id=client_id,
                               client_secret=client_secret,
                               scope=scope,
                               redirect_uri='urn:ietf:wg:oauth:2.0:oob')
    post_url = 'https://www.googleapis.com/plus/v1whitelisted/people/me/activities'

    def publish(self):
        credentials = self.get('credentials')
        # Create a new authorized API client.
        http = httplib2.Http()
        http = credentials.authorize(http)

        headers = {'Content-Type': 'application/json'}

        # TODO(smus): Actually we want to format as much as possible. Perhaps a
        # custom Markdown to G+ formatter would fit the bill here.  For
        # example, converting quotes (> foo) to "foo", and more obvious
        # formatting.
        plainbody = self.markdown_to_plaintext(self.body)
        attachments = [dict(url=self.link_url)]
        object = dict(originalContent=plainbody, attachments=attachments)
        access = dict(items=[dict(type='public')])
        data = dict(object=object, access=access)
        body = json.dumps(data)

        resp, content = http.request(self.post_url,
                method='POST',
                headers=headers,
                body=body)

        print "Published to G+."

    def is_authenticated(self):
        credentials = self.get('credentials')
        return bool(credentials)

    def login(self):
        # First, try getting the access token.
        if not self.is_authenticated():
            # If there's no token, start verification.
            self.verify()
            # At this point, wait for a callback to confirm_verifier with the
            # verification code.
        self.finish_login()

    def finish_login(self):
        credentials = self.get('credentials')

    def verify(self):
        auth_uri = self.flow.step1_get_authorize_url()
        webbrowser.open(auth_uri)


    def confirm_verifier(self, verifier):
        credentials = self.flow.step2_exchange(verifier)
        self.set('credentials', credentials)
        self.finish_login()


if __name__ == '__main__':
    # Make a G+ syndicator.
    synd = GPlusSyndicator()
    synd.login()
    #code = raw_input("Code: ")
    #synd.confirm_verifier(code)
    print 'authenticated: ' + str(synd.is_authenticated())
    synd.set_info(
            link_url='http://pythonhosted.org/tweepy/html/auth_tutorial.html',
            blog_url='http://smus.com/link/foo',
            title='Authenticating',
            body='Testing 1.')
    synd.publish()
"""
    B = '''Read Scott Jenson's webapp UX paper. First part goes into a native app replacement, along the lines of [my previous blog post](http://smus.com/installable-webapps/). 

Next, a plea for an open web integrated wireless discovery service, ideally supporting multiple protocols including Bluetooth Low Energy. Fundamentally,

> This ability to 'summon' a web page without typing anything at all needs to be explored in future W3C standards and not be left solely to handset makers. 

Lastly, with some cross-device link in place, we can enter a world of multi-device interactions, which is, in my opinion, the key UX area to streamline in the near future.
'''

    synd = TwitterSyndicator()
    synd.login()
    synd.set_info(
            link_url='https://docs.google.com/document/d/1wcXubh-yUtViwtUG4o43v3jeO6P1T63EWTh4iw2iHy8/edit',
            blog_url='http://smus.com/link/2013/web-apps-position-paper/',
            title='Web Apps Position paper',
            body=B)

    synd.publish()
        """

########NEW FILE########
__FILENAME__ = test
from oauth2client.client import OAuth2WebServerFlow

from urllib import urlencode
import httplib2
import webbrowser
import json

import logging
logging.basicConfig()

client_id = '930206334662.apps.googleusercontent.com'
client_secret = 'r2aq6CJDRAA3Dd5ODlUwHibk'
scope = 'https://www.googleapis.com/auth/plus.stream.write ' + \
        'https://www.googleapis.com/auth/plus.me'
flow = OAuth2WebServerFlow(client_id=client_id,
                           client_secret=client_secret,
                           scope=scope,
                           redirect_uri='urn:ietf:wg:oauth:2.0:oob')

auth_uri = flow.step1_get_authorize_url()
webbrowser.open(auth_uri)

code = raw_input("Code: ")
credentials = flow.step2_exchange(code)

print 'Got credentials: ' + str(credentials.access_token)

# Create a new authorized API client.
http = httplib2.Http()
http = credentials.authorize(http)


# POST https://www.googleapis.com/plus/v1whitelisted/people/{userId}/activities
headers = {'Content-Type': 'application/json'}
print 'Request headers: ' + str(headers)

content_text = 'hello world'
content_url = 'http://onstartups.com/tabid/3339/bid/33111/7-Reasons-Why-You-Need-To-Work-For-A-Big-Company.aspx'

url = 'https://www.googleapis.com/plus/v1whitelisted/people/me/activities'
attachments = [dict(url=content_url)]
object = dict(originalContent=content_text, attachments=attachments)
access = dict(items=dict(type='public'))
data = dict(object=object, access=access)
body = json.dumps(data)

print 'Created request body: ' + body
resp, content = http.request(url,
        method='POST',
        headers=headers,
        body=body)

print content

########NEW FILE########
__FILENAME__ = migrate
#!/usr/bin/env python
# Loop through all of the content, converting everything from the hyde format
# into the lightning format.

# source format: (path is year/<filename>.html)
#---------------
# {% hyde
# title: <title>
# created: <YYYY-MM-DD HH:MM:SS>
# <YAML>
# %}
#
# {% block article %}
# <Markdown>
# {% endblock %}

# destination format: (path is year/<filename>/index.txt)
#--------------------
# <title>
# =======
# posted: <YYYY-MM-DD>
# <YAML>
#
# <Markdown>

import sys
import os
import re
import yaml
import time
import datetime
from distutils import dir_util

OUT_ROOT = './output/'
# Get the root path of hyde content.
ROOT = sys.argv[1]

OUT_TMPL = """%(title)s
%(sep)s
%(yaml)s

%(markdown)s
"""

def main():
  # Get all of the blog posts in the hyde root.
  files = get_files()
  # Make the directory for the new content.
  out = dir_util.mkpath(OUT_ROOT)
  # Reformat each blog post.
  for path in files:
    converted = convert(path)
    index_root = OUT_ROOT + os.path.splitext(path)[0] + '/'
    # Write out the reformatted blog post into the directory.
    dir_util.mkpath(index_root)
    f = open(index_root + 'index.txt', 'w');
    f.write(converted)


def get_files():
  """Gets the list of all hyde blog posts in the given directory."""
  files = []
  for dirpath, dirnames, filenames in os.walk(ROOT):
    for fname in filenames:
      if fname.endswith(".html"):
        # Get the file's path and modified time
        path = os.path.join(dirpath, fname)
        files.append(path)

  return files

def convert(path):
  """Converts a file at the given path to the new format."""
  # Open the file.
  contents = open(path, 'r').read()
  # Parse out the hyde metadata.
  yaml_str = get_tag_attribute(contents, 'hyde')
  metadata = yaml.load(yaml_str)
  # Parse out the markdown.
  markdown = get_tag_content(contents, 'block')
  # Convert the date formats.
  created = metadata['created']
  metadata['posted'] = convert_date(created)
  del metadata['created']
  # Extract the title.
  title = metadata['title']
  del metadata['title']
  return OUT_TMPL % {
    'yaml': yaml.safe_dump(metadata),
    'title': title,
    'markdown': markdown,
    'sep': '=' * len(title)
  }

def get_tag_attribute(string, tag):
  """Gets the tag's inline value {% tag ...this... %}"""
  # Find the tag in the string.
  tag_start = '{%% *%s' % tag
  tag_end = ' *%}'
  return get_substr_between(string, tag_start, tag_end)

def get_tag_content(string, tag):
  """Gets the tag's content {% tag %}...this...{% endtag %}"""
  tag_start = '{%% *%s *\w*? *%%}' % tag
  tag_end = '{%% *end%s *%%}' % tag
  return get_substr_between(string, tag_start, tag_end)

def get_substr_between(string, start, end):
  start_index = re.search(start, string).start()
  after_string = string[start_index:]
  end_index = re.search(end, after_string).start() + start_index

  return string[start_index + len(start):end_index]

def convert_date(dt):
  return dt.date()

if __name__ == '__main__':
  main()

########NEW FILE########
