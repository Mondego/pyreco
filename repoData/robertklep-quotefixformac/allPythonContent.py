__FILENAME__ = app
from    AppKit                  import NSUserDefaults, NSBundle, NSApplication, NSRunAlertPanel
from    Foundation              import NSLog
from    quotefix.messagetypes   import *
from    quotefix.menu           import Menu
from    objc                    import Category, lookUpClass
from    logger                  import logger
import  os, re

class App(object):

    def __init__(self, version, updater):
        # set version
        self.version = version

        # set updater
        self.updater = updater

        # keep state of 'toggle key'
        self.toggle_key_active = False

        # read user defaults (preferences)
        self.prefs = NSUserDefaults.standardUserDefaults()

        # register some default values
        self.prefs.registerDefaults_(dict(
            QuoteFixFixReply        = True,
            QuoteFixFixReplyAll     = True,
            QuoteFixFixForward      = True,
            QuoteFixFixDraft        = False,
            QuoteFixFixNewMessage   = False,
        ))

        # set log level
        logger.setLevel(self.is_debugging and logger.DEBUG or logger.WARNING)
        logger.debug('debug logging active')

        # add menu item for quick enable/disable
        Menu.alloc().initWithApp_(self).inject()

        # check update interval
        self.check_update_interval = self.prefs.int["QuoteFixCheckUpdateInterval"] or 0

        # check if we're running in a different Mail version as before
        self.check_version()

    def check_version(self):
        infodict    = NSBundle.mainBundle().infoDictionary()
        mailversion = infodict['CFBundleVersion']
        lastknown   = self.prefs.string["QuoteFixLastKnownBundleVersion"]
        if lastknown and lastknown != mailversion:
            NSRunAlertPanel(
                'QuoteFix plug-in',
                '''
The QuoteFix plug-in detected a different Mail.app version (perhaps you updated?).

If you run into any problems with regards to replying or forwarding mail, consider removing this plug-in (from ~/Library/Mail/Bundles/).

(This alert is only displayed once for each new version of Mail.app)''',
                    None,
                    None,
                    None
            )
            self.prefs.string["QuoteFixLastKnownBundleVersion"] = mailversion

    # used for debugging
    @property
    def html(self):
        return self._html

    @html.setter
    def html(self, html):
        self._html = html

    # return reference to main window
    def window(self):
        return NSApplication.sharedApplication().mainWindow()

    # 'is plugin active?'
    @property
    def is_active(self):
        return not self.prefs.bool["QuoteFixDisabled"]

    @is_active.setter
    def is_active(self, value):
        self.prefs.bool["QuoteFixDisabled"] = value

    # debugging
    @property
    def is_debugging(self):
        return self.prefs.bool['QuoteFixEnableDebugging']

    # 'is quotefixing enabled?'
    @property
    def is_quotefixing(self):
        return not self.prefs.bool["QuoteFixQuoteFixingDisabled"]

    # 'keep whitespace after attribution'
    @property
    def keep_attribution_whitespace(self):
        return self.prefs.bool["QuoteFixKeepAttributionWhitespace"]

    # 'remove from last occurrance of possible signature match'
    @property
    def remove_from_last_signature_match(self):
        return self.prefs.bool["QuoteFixRemoveSignatureFromLastMatch"]

    # 'remove trailing whitespace'
    @property
    def remove_trailing_whitespace(self):
        return self.prefs.bool["QuoteFixRemoveTrailingWhitespace"]

    # 'keep leading whitespace'
    @property
    def keep_leading_whitespace(self):
        return self.prefs.bool['QuoteFixKeepLeadingWhitespace']

    # 'make selectable quotes'
    @property
    def selectable_quotes(self):
        return self.prefs.bool['QuoteFixMakeSelectableQuotes']

    # 'remove attachment placeholders'
    @property
    def remove_attachment_placeholders(self):
        return self.prefs.bool["QuoteFixRemoveAttachmentPlaceholders"]

    # 'remove quotes from level'
    @property
    def remove_quotes(self):
        return self.prefs.bool["QuoteFixRemoveQuotes"]

    # 'remove quotes from level'
    @property
    def remove_quotes_level(self):
        return self.prefs.int["QuoteFixRemoveQuotesLevel"] or 5

    # message types to perform quotefixing on
    @property
    def message_types_to_quotefix(self):
        types = []
        if self.prefs.bool["QuoteFixFixReply"]:
            types.append(REPLY)
            types.append(REPLY_AS)
        if self.prefs.bool["QuoteFixFixReplyAll"]:
            types.append(REPLY_ALL)
        if self.prefs.bool["QuoteFixFixForward"]:
            types.append(FORWARD)
        if self.prefs.bool["QuoteFixFixDraft"]:
            types.append(DRAFT)
        if self.prefs.bool["QuoteFixFixNewMessage"]:
            types.append(NEW)
        if self.prefs.bool["QuoteFixFixSendAgain"]:
            types.append(SENDAGAIN)
        return types

    # 'don't add extra line of whitespace below first-level quote'
    @property
    def no_whitespace_below_quote(self):
        return self.prefs.bool["QuoteFixNoWhitespaceBelowQuote"]

    # 'move cursor to top of document after quotefixing'
    @property
    def move_cursor_to_top(self):
        return self.prefs.bool["QuoteFixMoveCursorToTop"]

    # 'use custom reply attribution'
    @property
    def use_custom_reply_attribution(self):
        return self.is_active and self.prefs.bool["QuoteFixUseCustomReplyAttribution"] or False

    # 'custom reply attribution'
    @property
    def custom_reply_attribution(self):
        return self.prefs.string["QuoteFixCustomReplyAttribution"] or ""

    # 'increase quotelevel with custom reply'
    @property
    def custom_reply_increase_quotelevel(self):
        return self.prefs.bool["QuoteFixCustomReplyIncreaseQuoteLevel"] or False

    # 'custom reply is HTML code'
    @property
    def custom_reply_is_html(self):
        return self.prefs.bool["QuoteFixCustomReplyIsHTML"] or False

    # 'convert reply to rich text when needed?'
    @property
    def custom_reply_convert_to_rich(self):
        return self.prefs.bool['QuoteFixCustomReplyConvertToRichText'] or False

    # 'use custom send-again attribution'
    @property
    def use_custom_sendagain_attribution(self):
        return self.is_active and self.prefs.bool["QuoteFixUseCustomSendAgainAttribution"] or False

    # 'custom send-again attribution'
    @property
    def custom_sendagain_attribution(self):
        return self.prefs.string["QuoteFixCustomSendAgainAttribution"] or ""

    # 'custom send-again is HTML code'
    @property
    def custom_sendagain_is_html(self):
        return self.prefs.bool["QuoteFixCustomSendAgainIsHTML"] or False

    # 'convert send-again to rich text when needed?'
    @property
    def custom_sendagain_convert_to_rich(self):
        return self.prefs.bool['QuoteFixCustomSendAgainConvertToRichText'] or False

    # 'use custom forwarding attribution'
    @property
    def use_custom_forwarding_attribution(self):
        return self.is_active and self.prefs.bool["QuoteFixUseCustomForwardingAttribution"] or False

    # 'custom forwarding attribution'
    @property
    def custom_forwarding_attribution(self):
        return self.prefs.string["QuoteFixCustomForwardingAttribution"] or ""

    # 'increase quotelevel with custom forwarding'
    @property
    def custom_forwarding_increase_quotelevel(self):
        return self.prefs.bool["QuoteFixCustomForwardingIncreaseQuoteLevel"] or False

    # 'remove Apple Mail forward attribution'
    @property
    def remove_apple_mail_forward_attribution(self):
        return self.prefs.bool["QuoteFixRemoveAppleMailForwardAttribution"] or False

    # 'custom forwarding is HTML code'
    @property
    def custom_forwarding_is_html(self):
        return self.prefs.bool["QuoteFixCustomForwardingIsHTML"] or False

    # 'convert forwarded message to rich text when needed?'
    @property
    def custom_forwarding_convert_to_rich(self):
        return self.prefs.bool['QuoteFixCustomForwardingConvertToRichText'] or False

    # 'enable templating in customized attributions'
    @property
    def custom_attribution_allow_templating(self):
        return self.prefs.bool["QuoteFixCustomAttributionAllowTemplating"] or False

    # 'keep senders signature'
    @property
    def keep_sender_signature(self):
        return self.prefs.bool["QuoteFixKeepSenderSignature"] or False

    # signature matcher
    @property
    def signature_matcher(self):
        matcher = None
        # use custom matcher?
        if self.prefs.bool["QuoteFixUseCustomSignatureMatcher"]:
            matcher = self.prefs.string["QuoteFixCustomSignatureMatcher"]
        if not matcher:
            matcher = self.default_signature_matcher

        # try to compile regular expression to catch errors early
        try:
            re.compile(matcher)
        except re.error, e:
            matcher = self.default_signature_matcher
            NSRunAlertPanel(
                'QuoteFix plug-in',
                'The supplied custom signature matcher contains an invalid regular expression (error: "%s").\n\nI will revert back to the default matcher until the problem is fixed in the preferences.' % str(e),
                None, None, None)

        # return compiled regex
        return re.compile(matcher)

    @property
    def default_signature_matcher(self):
        return r'(?i)--(?:&nbsp;|\s+|\xa0)?$'

    # handle warning message generated with customized attributions
    @property
    def dont_show_html_attribution_warning(self):
        return self.prefs.string["QuoteFixDontShowHTMLAttributionWarning"]

    @dont_show_html_attribution_warning.setter
    def dont_show_html_attribution_warning(self, value):
        self.prefs.string["QuoteFixDontShowHTMLAttributionWarning"] = value

    # update-related properties
    @property
    def check_update_interval(self):
        return self._check_update_interval

    @check_update_interval.setter
    def check_update_interval(self, value):
        # store in preferences
        self.prefs.string["QuoteFixCheckUpdateInterval"] = value
        self._check_update_interval = value

        # convert to interval and pass to updater
        if   value == 0: interval = 0 # never
        elif value == 1: interval = 7 * 24 * 60 * 60 # weekly
        elif value == 2: interval = int(4.35 * 7 * 24 * 60 * 60) # monthly
        else           : return
        self.updater.set_update_interval(interval)

    @property
    def last_update_check(self):
        return self.updater.last_update_check

    # check for updates
    def check_for_updates(self):
        self.updater.check_for_updates()

# make NSUserDefaults a bit more Pythonic
class NSUserDefaults(Category(lookUpClass('NSUserDefaults'))):

    @property
    def bool(self):     return DictProxy(self, 'bool')

    @property
    def string(self):   return DictProxy(self, 'string')

    @property
    def object(self):   return DictProxy(self, 'object')

    @property
    def int(self):      return DictProxy(self, 'int')

class DictProxy:

    def __init__(self, delegate, type):
        self.delegate   = delegate
        self.type       = type

    def __getitem__(self, item):
        return {
            'string'    : self.delegate.stringForKey_,
            'bool'      : self.delegate.boolForKey_,
            'object'    : self.delegate.objectForKey_,
            'int'       : self.delegate.integerForKey_,
        }[self.type](item)

    def __setitem__(self, item, value):
        {
            'string'    : self.delegate.setObject_forKey_, # no setString_forKey_
            'bool'      : self.delegate.setBool_forKey_,
            'object'    : self.delegate.setObject_forKey_,
            'int'       : self.delegate.setInteger_forKey_,
        }[self.type](value, item)

########NEW FILE########
__FILENAME__ = attribution
from    AppKit                      import NSRunAlertPanel
from    objc                        import Category, lookUpClass
from    datetime                    import datetime
from    quotefix.utils              import swizzle, SimpleTemplate
from    quotefix.pyratemp           import Template
from    quotefix.messagetypes       import *
from    quotefix.attributionclasses import *
import  re

# Mavericks
try:
    from AppKit import MCMessage as Message
except:
    from AppKit import Message

# patch MessageHeaders class to return empty attributions with forwards
try:
    from AppKit import MCMessageHeaders
    class MCMessageHeaders(Category(MCMessageHeaders)):

        @classmethod
        def registerQuoteFixApplication(cls, app):
            cls.app = app

        @swizzle(MCMessageHeaders, 'htmlStringShowingHeaderDetailLevel:useBold:useGray:')
        def htmlStringShowingHeaderDetailLevel_useBold_useGray_(self, original, level, bold, gray):
            if self.app.use_custom_forwarding_attribution and self.app.remove_apple_mail_forward_attribution:
                return ''
            return original(self, level, bold, gray)
    MessageHeaders = MCMessageHeaders
except:
    from AppKit import MessageHeaders
    class MessageHeaders(Category(MessageHeaders)):

        @classmethod
        def registerQuoteFixApplication(cls, app):
            cls.app = app

        @swizzle(MessageHeaders, 'htmlStringShowingHeaderDetailLevel:useBold:useGray:')
        def htmlStringShowingHeaderDetailLevel_useBold_useGray_(self, original, level, bold, gray):
            if self.app.use_custom_forwarding_attribution and self.app.remove_apple_mail_forward_attribution:
                return ''
            return original(self, level, bold, gray)

class CustomizedAttribution:
    """ Provide customized reply/sendagain/forward attributions """

    @classmethod
    def registerQuoteFixApplication(cls, app):
        cls.app = app

    @classmethod
    def customize_reply(cls, app, editor, dom, reply, inreplyto):
        return cls.customize_attribution(
            # grab the original attribution string from the
            # Message class, so we can replace it with a
            # customized version of it.
            original    = Message.replyPrefixWithSpacer_(False),
            editor      = editor,
            dom         = dom,
            reply       = reply,
            inreplyto   = inreplyto,
            template    = app.custom_reply_attribution,
            messagetype = REPLY
        )

    @classmethod
    def customize_sendagain(cls, app, editor, dom, reply, inreplyto):
        return cls.customize_attribution(
            original    = None,
            editor      = editor,
            dom         = dom,
            reply       = reply,
            inreplyto   = inreplyto,
            template    = app.custom_sendagain_attribution,
            messagetype = SENDAGAIN
        )

    @classmethod
    def customize_forward(cls, app, editor, dom, reply, inreplyto):
        return cls.customize_attribution(
            original    = Message.forwardedMessagePrefixWithSpacer_(False),
            editor      = editor,
            dom         = dom,
            reply       = reply,
            inreplyto   = inreplyto,
            template    = app.custom_forwarding_attribution,
            messagetype = FORWARD
        )

    @classmethod
    def customize_attribution(cls, original, editor, dom, reply, inreplyto, template, messagetype):
        is_forward      = messagetype == FORWARD
        is_reply        = messagetype == REPLY
        is_sendagain    = messagetype == SENDAGAIN

        # create matcher for matching original attribution (and replace
        # nsbp's with normal spaces)
        if original:
            original    = original.replace(u'\xa0', ' ').strip()
            original    = original.replace('(', r'\(').replace(')', r'\)')
            original    = re.sub(r'%\d+\$\@', '.*?', original)
            matcher     = re.compile(original)
        else:
            matcher     = None

        # find possible nodes which can contain attribution
        root = dom.documentElement()
        if is_sendagain:
            # Special case: Mail doesn't include an attribution for Send Again messages,
            # so we'll just use the root element
            node        = root
            children    = node.getElementsByTagName_('body')
        else:
            nodes = root.getElementsByClassName_('AppleOriginalContents')
            if not nodes.length():
                nodes = root.getElementsByClassName_('ApplePlainTextBody')
                if not nodes.length():
                    return False
            node        = nodes.item_(0)
            children    = node.childNodes()

        # check children for attribution node
        is_rich = editor.backEnd().containsRichText()
        for i in range(children.length()):
            child = children.item_(i)
            if not is_sendagain:
                if child.nodeType() == 1:
                    html = child.innerHTML()
                    if matcher and not matcher.match(html):
                        continue
                elif child.nodeType() == 3:
                    text = child.data()
                    if matcher and not matcher.match(text):
                        continue

            # should attribution be treated as HTML?
            is_html =   (is_forward     and cls.app.custom_forwarding_is_html) or \
                        (is_sendagain   and cls.app.custom_sendagain_is_html) or \
                        (is_reply       and cls.app.custom_reply_is_html)

            # check if message is rich text with HTML-attribution
            if is_html and not is_rich:
                if  (is_forward     and cls.app.custom_forwarding_convert_to_rich) or \
                    (is_sendagain   and cls.app.custom_sendagain_convert_to_rich) or \
                    (is_reply       and cls.app.custom_reply_convert_to_rich):
                    editor.makeRichText_(editor)
                elif not cls.app.dont_show_html_attribution_warning:
                    idx = NSRunAlertPanel(
                        "QuoteFix warning",
                        "You are using an HTML-attribution, but the current message format is plain text.\n\n" +
                        "Unless you convert to rich text, the HTML-formatting will be lost when sending the message.",
                        "OK",
                        "Don't show this warning again",
                        None
                    )
                    if idx == 0:
                        cls.app.dont_show_html_attribution_warning = True

            # render attribution
            attribution = cls.render_attribution(
                reply       = reply,
                inreplyto   = inreplyto,
                template    = template,
                is_html     = is_html,
            )

            # replace leading whitespace with non-breaking spaces
            attribution = re.sub(r'(?m)^( +)' , lambda m: u'\u00a0' * len(m.group(1)), attribution)
            attribution = re.sub(r'(?m)^(\t+)', lambda m: u'\u00a0\u00a0' * len(m.group(1)), attribution)

            # replace newlines with hard linebreaks
            attribution = attribution.replace('\n', '<br/>')

            # replace old attribution with new, depending on node type
            if is_sendagain:
                newnode = dom.createElement_("span")
                newnode.setInnerHTML_(attribution)
                child.insertBefore_refChild_(newnode, child.firstChild())
                copynode = newnode
            elif child.nodeType() == 1:
                child.setInnerHTML_(attribution)
                copynode = child
            else:
                newnode = dom.createElement_("span")
                newnode.setInnerHTML_(attribution)
                node.replaceChild_oldChild_(newnode, child)
                copynode = newnode

            # increase quote level of attribution?
            if  (is_forward     and cls.app.custom_forwarding_increase_quotelevel) or \
                (is_reply       and cls.app.custom_reply_increase_quotelevel):
                copy = copynode.cloneNode_(True)
                copynode.parentNode().removeChild_(copynode)
                blockquote = root.firstDescendantBlockQuote()
                blockquote.insertBefore_refChild_(copy, blockquote.childNodes().item_(0))

            # done
            return True

        # done nothing
        return False

    @classmethod
    def render_attribution(cls, reply, inreplyto, template, is_html):
        # expand template and return it
        return cls.render_with_params(
            template,
            cls.setup_params(reply, inreplyto),
            is_html
        )

    @classmethod
    def render_with_params(cls, template, params, is_html):
        # hmm...
        template = template.replace('message.from',     'message.From')
        template = template.replace('response.from',    'response.From')
        template = template.replace('recipients.all',   'recipients.All')

        # escape some characters when not using HTML-mode
        if not is_html:
            template = template.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # templating enabled?
        if cls.app.custom_attribution_allow_templating:
            # try to expand a complex template first
            try:
                return Template(string = template, data = params)()
            except Exception:
                return "<i>&lt;A templating error occured, please check your template for errors&gt;</i>"

        # simple template
        return SimpleTemplate(template).substitute(params)

    @classmethod
    def setup_params(cls, reply, inreplyto):
        return {
            'message'   : QFMessage(inreplyto),
            'response'  : QFMessage(reply),
            # 'now'?
        }

########NEW FILE########
__FILENAME__ = attributionclasses
from    AppKit      import NSDate, NSLocale, NSDateFormatter
from    Foundation  import NSLog
from    datetime    import datetime
import  email.utils, re

class QFMessage:
    """ wraps a message """

    def __init__(self, message):
        self.From           = QFAddressee(message.sender())
        self.sender         = message.sender()
        self.to             = QFAddresseeList( message.to() )
        self.recipients     = QFRecipients(
            All     = message.recipients(),
            to      = message.toRecipients(),
            cc      = message.ccRecipients(),
            bcc     = message.bccRecipients(),
        )
        self.subject        = message.subject()
        self.sent           = QFDateTime(message.dateSent())
        self.received       = QFDateTime(message.dateReceived())

class QFRecipients:

    def __init__(self, All, to, cc, bcc):
        self.All    = QFAddresseeList(All)
        self.to     = QFAddresseeList(to)
        self.cc     = QFAddresseeList(cc)
        self.bcc    = QFAddresseeList(bcc)

    def __len__(self):
        return len(self.All)

    def __unicode__(self):
        return unicode(self.All)

    def __repr__(self):
        return self.__unicode__()

class QFAddresseeList:

    def __init__(self, addresseelist):
        # convert to list if passed parameter is a string
        if isinstance(addresseelist, basestring):
            addresseelist = [ addresseelist ]

        # make a list of QFAddressee's
        self.addressees = []
        for addressee in list(addresseelist):
            # expand MessageAddressee instances
            if addressee.__class__.__name__ in [ 'MFMessageAddressee', 'MessageAddressee' ]:
                addressee = addressee.formattedAddress()
            self.addressees.append( QFAddressee(addressee) )

    def __len__(self):
        return len(self.addressees)

    def join(self, separator = ", ", field = 'address'):
        if field not in [ 'address', 'name', 'email' ]:
            field = 'address'
        return separator.join([ unicode(getattr(a, field)) for a in self.addressees ])

    def __unicode__(self):
        return self.join(", ")

    def __repr__(self):
        return self.__unicode__()

class QFAddressee:
    """ wrap a message addressee """

    def __init__(self, address):
        self.address        = address
        name, emailaddr     = email.utils.parseaddr(address)
        self.email          = emailaddr
        self.name           = name or emailaddr

    def __unicode__(self):
        return self.address

    def __repr__(self):
        return self.__unicode__()

class QFDateTime(str):
    """ wraps a datetime object """
    formatter           = NSDateFormatter.alloc().init()
    default_format      = "EEE MMM dd yyyy HH:mm:ss"
    STRFTIME_TO_UNICODE = {
        '%Y'    : 'yyyy',
        '%m'    : 'MM',
        '%d'    : 'dd',
        '%H'    : 'HH',
        '%I'    : 'hh',
        '%p'    : 'a',
        '%M'    : 'mm',
        '%S'    : 'ss',
        '%U'    : 'w',
        '%b'    : 'MMM',
        '%B'    : 'MMMM',
        '%a'    : 'E',
        '%A'    : 'EEEE',
        '%x'    : 'EEE MMM dd yyyy',
        '%X'    : 'HH:mm:ss',
        '%z'    : 'Z',
    }

    def __new__(cls, nsdate):
        cls.formatter.setDateFormat_(cls.default_format)
        self            = super(QFDateTime, cls).__new__(
            cls,
            cls.formatter.stringFromDate_(nsdate).encode('utf-8')
        )
        self.nsdate     = nsdate

        # set date/time attributes
        attributes      = dict(
            year        = "yyyy",
            month       = "MM",
            day         = "dd",
            hour        = "HH",
            hour12      = "hh",
            ampm        = "a",
            minute      = "mm",
            second      = "ss",
            weeknumber  = "w",
            monthshort  = "MMM",
            monthlong   = "MMMM",
            dayshort    = "E",
            daylong     = "EEEE",
            date        = "EEE MMM dd yyyy",
            time        = "HH:mm:ss",
            timezone    = "Z",
        )

        for attribute, format in attributes.items():
            self.formatter.setDateFormat_(format)
            setattr(self, attribute, self.formatter.stringFromDate_(nsdate).encode('utf-8'))

        return self

    def strftime_to_unicode(self, fmt):
        """ convert strftime formatting character to Unicode formatting string """
        return re.sub(
            r'(%[a-zA-Z])',
            lambda m: self.STRFTIME_TO_UNICODE.get(m.group(1), m.group(1)),
            fmt
        )

    def strftime(self, fmt, locale = None, timezone = None):
        return self.format(self.strftime_to_unicode(fmt), locale, timezone = None)

    def format(self, fmt, locale = None, timezone = None):
        self.formatter.setDateFormat_(fmt)
        if locale:
            self.formatter.setLocale_(NSLocale.alloc().initWithLocaleIdentifier_(locale))
        return self.formatter.stringFromDate_(self.nsdate).encode('utf-8')

    def locale(self, locale):
        return self.format(self.default_format, locale)

    @classmethod
    def nsdate_to_datetime(cls, nsdate):
        # convert NSDate to datetime (XXX: always converts to local timezone)
        description = nsdate.descriptionWithCalendarFormat_timeZone_locale_("%Y-%m-%d %H:%M:%S", None, None)
        return datetime.strptime(description, "%Y-%m-%d %H:%M:%S")

########NEW FILE########
__FILENAME__ = fixer
from    AppKit                  import NSRunAlertPanel, NSAlternateKeyMask, NSEvent, NSKeyDown, NSControlKeyMask, MessageViewer
from    Foundation              import NSLog
from    quotefix.utils          import swizzle
from    quotefix.attribution    import CustomizedAttribution
from    quotefix.messagetypes   import *
from    objc                    import Category, lookUpClass
from    logger                  import logger
import  re, traceback, objc

DOMText = lookUpClass('DOMText')

MailApp = lookUpClass('MailApp')
class MailApp(Category(MailApp)):

    @classmethod
    def registerQuoteFixApplication(cls, app):
        cls.app = app

    @swizzle(MailApp, 'sendEvent:')
    def sendEvent(self, original, event):
        if not hasattr(self, 'app'):
            original(self, event)
            return
        self.app.toggle_key_active = False
        # keep track of an active option key
        flags = event.modifierFlags()
        if (flags & NSAlternateKeyMask) and not (flags & NSControlKeyMask):
            self.app.toggle_key_active = True
            # handle reply/reply-all (XXX: won't work if you have assigned
            # a different shortcut key to these actions!)
            if event.type() == NSKeyDown and event.charactersIgnoringModifiers().lower() == 'r':
                # strip the Option-key from the event
                event = NSEvent.keyEventWithType_location_modifierFlags_timestamp_windowNumber_context_characters_charactersIgnoringModifiers_isARepeat_keyCode_(
                    event.type(),
                    event.locationInWindow(),
                    event.modifierFlags() & ~NSAlternateKeyMask,
                    event.timestamp(),
                    event.windowNumber(),
                    event.context(),
                    event.characters(),
                    event.charactersIgnoringModifiers(),
                    event.isARepeat(),
                    event.keyCode()
                )
        original(self, event)

# our own DocumentEditor implementation
DocumentEditor = lookUpClass('DocumentEditor')
class DocumentEditor(Category(DocumentEditor)):

    @classmethod
    def registerQuoteFixApplication(cls, app):
        cls.app = app

    @swizzle(DocumentEditor, 'finishLoadingEditor')
    def finishLoadingEditor(self, original):
        logger.debug('DocumentEditor finishLoadingEditor')

        # execute original finishLoadingEditor()
        original(self)

        try:
            # if toggle key is active, temporarily switch the active state
            is_active = self.app.toggle_key_active ^ self.app.is_active

            # check if we can proceed
            if not is_active:
                logger.debug("QuoteFix is not active, so no QuoteFixing for you!")
                return

            # grab composeView instance (this is the WebView which contains the
            # message editor) and check for the right conditions
            try:
                view = objc.getInstanceVariable(self, 'composeWebView')
            except:
                # was renamed in Lion
                view = objc.getInstanceVariable(self, '_composeWebView')

            # grab some other variables we need to perform our business
            backend     = self.backEnd()
            htmldom     = view.mainFrame().DOMDocument()
            htmlroot    = htmldom.documentElement()
            messageType = self.messageType()

            # XXX: hack alert! if message type is DRAFT, but we can determine this
            # is actually a Send Again action, adjust the message type.
            origmsg = backend.originalMessage()
            if origmsg and messageType == DRAFT:
                # get the message viewer for this message
                viewer = MessageViewer.existingViewerShowingMessage_(origmsg)
                if viewer:
                    # get the mailbox for the viewer
                    mailboxes = viewer.selectedMailboxes()
                    # get the Drafts mailbox
                    draftmailbox = viewer.draftsMailbox()
                    # check if they're the same; if not, it's a Send-Again
                    if draftmailbox not in mailboxes:
                        messageType = SENDAGAIN

            # send original HTML to menu for debugging
            self.app.html = htmlroot.innerHTML()

            # should we be quotefixing?
            if not self.app.is_quotefixing:
                logger.debug('quotefixing turned off in preferences, skipping that part')
            elif messageType not in self.app.message_types_to_quotefix:
                logger.debug('message type "%s" not in %s, not quotefixing' % (
                    messageType,
                    self.app.message_types_to_quotefix
                ))
            else:
                # remove attachment placeholders?
                if self.app.remove_attachment_placeholders:
                    self.remove_attachment_placeholders(backend, htmlroot)
                    backend.setHasChanges_(False)

                # move cursor to end of document
                view.moveToEndOfDocument_(self)

                # remove quotes?
                if self.app.remove_quotes:
                    logger.debug('calling remove_quotes()')
                    self.remove_quotes(htmldom, self.app.remove_quotes_level)
                    backend.setHasChanges_(False)

                # make quotes selectable?
                if self.app.selectable_quotes:
                    logger.debug('calling make_selectable_quotes()')
                    self.make_selectable_quotes(view, htmldom)
                    backend.setHasChanges_(False)

                # remove signature from sender
                if not self.app.keep_sender_signature:
                    logger.debug('calling remove_old_signature()')
                    if self.remove_old_signature(htmldom, view):
                        backend.setHasChanges_(False)

                # place cursor above own signature (if any)
                logger.debug('calling move_above_new_signature()')
                if self.move_above_new_signature(htmldom, view):
                    backend.setHasChanges_(False)
                else:
                    view.insertNewline_(self)

                # perform some general cleanups
                logger.debug('calling cleanup_layout()')
                if self.cleanup_layout(htmlroot, backend):
                    backend.setHasChanges_(False)

                # move cursor to end of document
                if self.app.move_cursor_to_top:
                    view.moveToBeginningOfDocument_(self)

            # provide custom attribution?
            attributor = None
            if self.app.use_custom_reply_attribution and messageType in [ REPLY, REPLY_ALL, REPLY_AS ]:
                logger.debug("calling customize_attribution() for reply{-all,-as}")
                attributor = CustomizedAttribution.customize_reply
            elif self.app.use_custom_sendagain_attribution and messageType in [ SENDAGAIN ]:
                logger.debug("calling customize_attribution() for Send Again")
                attributor = CustomizedAttribution.customize_sendagain
            elif self.app.use_custom_forwarding_attribution and messageType == FORWARD:
                logger.debug("calling customize_attribution() for forwarding")
                attributor = CustomizedAttribution.customize_forward

            if attributor:
                # play nice with Attachment Tamer
                try:
                    message = backend.draftMessage()
                except:
                    message = backend._makeMessageWithContents_isDraft_shouldSign_shouldEncrypt_shouldSkipSignature_shouldBePlainText_(
                        backend.copyOfContentsForDraft_shouldBePlainText_isOkayToForceRichText_(True, False, True),
                        True,
                        False,
                        False,
                        False,
                        False
                    )
                try:
                    attributor(
                        app         = self.app,
                        editor      = self,
                        dom         = htmldom,
                        reply       = message,
                        inreplyto   = backend.originalMessage()
                    )
                    backend.setHasChanges_(False)
                except:
                    # ignore when not debugging
                    if self.app.is_debugging:
                        raise

            # move to beginning of line
            logger.debug('calling view.moveToBeginningOfLine()')
            view.moveToBeginningOfLine_(self)

            # done
            logger.debug('QuoteFixing done')
        except Exception:
            logger.critical(traceback.format_exc())
            if self.app.is_debugging:
                NSRunAlertPanel(
                    'QuoteFix caught an exception',
                    'The QuoteFix plug-in caught an exception:\n\n' +
                    traceback.format_exc() +
                    '\nPlease contact the developer quoting the contents of this alert.',
                    None, None, None
                )

    def remove_attachment_placeholders(self, backend, htmlroot):
        messagebody = backend.originalMessage().messageBody()
        if not messagebody:
            return
        attachments = messagebody.attachmentFilenames()
        if not attachments:
            return
        html        = htmlroot.innerHTML()
        matchnames  = []
        for attachment in attachments:
            attachment  = attachment.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            escaped     = re.escape('&lt;%s&gt;' % attachment)
            escaped     = escaped.replace(r'\ ', r'(?: |\&nbsp;)')
            escaped     = escaped.replace(r'\:', '[:_]')
            matchnames.append(escaped)
        matches = "|".join(matchnames)
        html    = re.sub(matches, '', html)
        htmlroot.setInnerHTML_(html)

    def remove_quotes(self, dom, level):
        # find all blockquotes
        blockquotes = dom.querySelectorAll_("blockquote")
        for i in range(blockquotes.length()):
            blockquote = blockquotes.item_(i)
            # check quotelevel against maximum allowed level
            if blockquote.quoteLevel() >= level:
                blockquote.parentNode().removeChild_(blockquote)

    def make_selectable_quotes(self, view, dom):
        return

        # find all blockquotes
        blockquotes = dom.querySelectorAll_("blockquote")
        for i in range(blockquotes.length()):
            blockquote = blockquotes.item_(i)
            # don't fix top-level blockquote
            if blockquote.quoteLevel() > 1:
                # get current computed style
                style = dom.getComputedStyle_pseudoElement_(blockquote, None).cssText()

                # remove text-color-related stuff (so it will be inherited)
                style = re.sub(r'\scolor.*?:.*?;', '', style)
                style = re.sub(r'\soutline-color.*?:.*?;', '', style)
                style = re.sub(r'\s-webkit-text-emphasis-color.*?:.*?;', '', style)
                style = re.sub(r'\s-webkit-text-fill-color.*?:.*?;', '', style)
                style = re.sub(r'\s-webkit-text-stroke-color.*?:.*?;', '', style)
                style = re.sub(r'\sflood-color.*?:.*?;', '', style)
                style = re.sub(r'\slighting-color.*?:.*?;', '', style)

                # remove 'type' attribute
                blockquote.removeAttribute_("type")

                # and set style attribute to match original style
                blockquote.setAttribute_value_("style", style)

    # try to find, and remove, signature of sender
    def remove_old_signature(self, dom, view):
        signature   = None
        root        = dom.documentElement()

        # grab first blockquote (if any)
        blockquote = root.firstDescendantBlockQuote()
        if not blockquote:
            return False

        # get matcher
        matcher = self.app.signature_matcher

        # find nodes which might contain senders signature
        nodes   = []
        matches = dom.querySelectorAll_("div, br, span")
        nodes   += [ matches.item_(i) for i in range(matches.length()) ]

        # try to find a signature
        matches = []
        for node in nodes:
            # skip nodes which aren't at quotelevel 1
            if node.quoteLevel() != 1:
                continue

            # BR's are empty, so treat them differently
            if node.nodeName().lower() == 'br':
                nextnode = node.nextSibling()
                if isinstance(nextnode, DOMText) and matcher.search(nextnode.data()):
                    matches.append(node)
            elif node.nodeName().lower() in [ 'div', 'span' ] and matcher.search(node.innerHTML()):
                matches.append(node)

        # if we found a signature, remove it
        if len(matches):
            signature = matches[self.app.remove_from_last_signature_match and -1 or 0]

            # remove all siblings following signature, except for attachments
            node    = signature
            parent  = signature.parentNode()
            while node:
                if node.nodeName().lower() == 'object':
                    node = node.nextSibling()
                else:
                    nextnode = node.nextSibling()
                    parent.removeChild_(node)
                    node = nextnode
                while not node and parent != blockquote:
                    node    = parent.nextSibling()
                    parent  = parent.parentNode()

            # move down a line
            view.moveDown_(self)

            # and insert a paragraph break
            view.insertParagraphSeparator_(self)

            # remove empty lines
            blockquote.removeStrayLinefeeds()

            # signal that we removed an old signature
            return True

        # found nothing?
        return False

    def move_above_new_signature(self, dom, view):
        # find new signature by ID
        div = dom.getElementById_("AppleMailSignature")
        if not div:
            return False

        # set selection range
        domrange = dom.createRange()
        domrange.selectNode_(div)

        # create selection
        view.setSelectedDOMRange_affinity_(domrange, 0)

        # move up (positions cursor above signature)
        view.moveUp_(self)

        # insert a paragraph break?
        if not self.app.no_whitespace_below_quote:
            view.insertParagraphSeparator_(self)

        # signal that we moved
        return True

    def cleanup_layout(self, root, backend):
        # clean up stray linefeeds
        if not self.app.keep_leading_whitespace:
            root.getElementsByTagName_("body").item_(0)._removeStrayLinefeedsAtBeginning()

        # remove trailing whitespace on first blockquote?
        if self.app.remove_trailing_whitespace:
            blockquote = root.firstDescendantBlockQuote()
            if blockquote:
                blockquote._removeStrayLinefeedsAtEnd()

        # done?
        if self.app.keep_attribution_whitespace:
            return True

        # clean up linebreaks before first blockquote
        blockquote = root.firstDescendantBlockQuote()
        if blockquote:
            parent  = blockquote.parentNode()
            node    = blockquote.previousSibling()
            while node and node.nodeName().lower() == 'br':
                parent.removeChild_(node)
                node = blockquote.previousSibling()

        return True

########NEW FILE########
__FILENAME__ = logger
from Foundation import NSLog

class Logger:
    DEBUG       = 1
    INFO        = 2
    WARNING     = 3
    ERROR       = 4
    CRITICAL    = 5

    def __init__(self, level = INFO):
        self.setLevel(level)

    def setLevel(self, level):
        self.level = level

    def debug(self, fmt, **args):
        self.log(self.DEBUG, fmt, **args)

    def info(self, fmt, **args):
        self.log(self.INFO, fmt, **args)

    def warning(self, fmt, **args):
        self.log(self.WARNING, fmt, **args)

    def error(self, fmt, **args):
        self.log(self.ERROR, fmt, **args)

    def critical(self, fmt, **args):
        self.log(self.CRITICAL, fmt, **args)

    def log(self, minlevel, fmt, **args):
        if minlevel >= self.level:
            NSLog(fmt, **args)

logger = Logger()

if __name__ == '__main__':
    logger.debug('this is a debug message');
    logger.info('this is a info message');
    logger.warning('this is a warning message');
    logger.error('this is a error message');
    logger.critical('this is a critical message');

########NEW FILE########
__FILENAME__ = menu
from    AppKit          import NSKeyValueObservingOptionNew, NSUserDefaultsController, NSMenuItem, NSApplication, NSBundle, NSObject
from    Foundation      import NSLog
import  objc

class Menu(NSObject):

    def initWithApp_(self, app):
        self = super(Menu, self).init()
        if self is None:
            return None
        self.app        = app
        self.mainwindow = NSApplication.sharedApplication().mainWindow()
        self.bundle     = NSBundle.bundleWithIdentifier_('name.klep.mail.QuoteFix')
        return self

    def inject(self):
        try:
            # necessary because of the menu callbacks
            self.retain()

            # get application menu instance
            appmenu = NSApplication.sharedApplication().mainMenu().itemAtIndex_(0).submenu()

            # make a new menu item
            self.item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "QuoteFix",
                "toggleState:",
                "")
            self.item.setToolTip_(self.get_string("QUOTEFIX_TOOLTIP", ""))
            self.set_state_and_title(self.item)
            self.item.setTarget_(self)

            # add separator and new item
            appmenu.insertItem_atIndex_(NSMenuItem.separatorItem(), 1)
            appmenu.insertItem_atIndex_(self.item, 2)

            # observe changes for active state
            NSUserDefaultsController.sharedUserDefaultsController().addObserver_forKeyPath_options_context_(
                self,
                "values.QuoteFixDisabled",
                NSKeyValueObservingOptionNew,
                None
            )

        except Exception, e:
            raise e
        return self

    def set_state_and_title(self, item):
        item.setState_(self.app.is_active)
        item.setTitle_(self.get_string(
            self.app.is_active and "QuoteFix is enabled" or "QuoteFix is disabled"
        ))
        item.setState_(self.app.is_active)

    def get_string(self, key, fallback = None):
        if fallback is None:
            fallback = key
        return self.bundle.localizedStringForKey_value_table_(key, fallback, None)

    def toggleState_(self, sender):
        self.app.is_active = sender.state()
        self.set_state_and_title(sender)

    def window(self):
        return self.mainwindow

    # update menu item when active state of plug-in changes
    def observeValueForKeyPath_ofObject_change_context_(self, keyPath, obj, change, context):
        self.set_state_and_title(self.item)

########NEW FILE########
__FILENAME__ = messagetypes
# message types
REPLY       = 1
REPLY_ALL   = 2
FORWARD     = 3
DRAFT       = 4
NEW         = 5
REPLY_AS    = 8  # reply triggered by AppleScript
SENDAGAIN   = 90 # not official

########NEW FILE########
__FILENAME__ = preferences
# -*- coding:utf-8 -*-
from    AppKit                  import NSPreferencesModule, NSNib, NSBox, NSNibTopLevelObjects, NSObject, NSPreferences, NSWorkspace, NSURL, NSBundle, NSImage, NSDateFormatter, NSLocale, NSDateFormatterMediumStyle, NSColor, MessageViewer
from    Foundation              import NSLog
from    quotefix.utils          import swizzle, htmlunescape
from    quotefix.attribution    import CustomizedAttribution
from    quotefix.preview        import preview_message
from    datetime                import datetime, timedelta
from    logger                  import logger
import  objc, random, re

class QuoteFixPreferencesModule(NSPreferencesModule):

    def init(self):
        context     = { NSNibTopLevelObjects : [] }
        nib         = NSNib.alloc().initWithNibNamed_bundle_("QuoteFixPreferencesModule.nib", NSBundle.bundleWithIdentifier_('name.klep.mail.QuoteFix'))
        inited      = nib.instantiateNibWithExternalNameTable_(context)
        self.view   = filter(lambda _: isinstance(_, NSBox), context[NSNibTopLevelObjects])[0]
        self.setMinSize_(self.view.boundsSize())
        self.setPreferencesView_(self.view)
        return self

    def minSize(self):
        return self.view.boundsSize()

    def isResizable(self):
        return False

class QuoteFixPreferences(NSPreferences):

    @classmethod
    def injectPreferencesModule(cls, prefs):
        titles = objc.getInstanceVariable(prefs, '_preferenceTitles')
        if 'QuoteFix' not in titles:
            prefs.addPreferenceNamed_owner_("QuoteFix", QuoteFixPreferencesModule.sharedInstance())
            toolbar     = objc.getInstanceVariable(prefs, '_preferencesPanel').toolbar()
            numitems    = len( toolbar.items() )
            toolbar.insertItemWithItemIdentifier_atIndex_("QuoteFix", numitems)

    @swizzle(NSPreferences, 'showPreferencesPanel')
    def showPreferencesPanel(self, original):
        QuoteFixPreferences.injectPreferencesModule(self)
        original(self)

# controller for NIB controls
class QuoteFixPreferencesController(NSObject):
    updateInterval                      = objc.IBOutlet()
    lastUpdateCheck                     = objc.IBOutlet()
    currentVersionUpdater               = objc.IBOutlet()
    checkUpdateButton                   = objc.IBOutlet()
    customReplyAttribution              = objc.IBOutlet()
    customForwardingAttribution         = objc.IBOutlet()
    customSendAgainAttribution          = objc.IBOutlet()
    customSignatureMatcher              = objc.IBOutlet()
    customSignatureMatcherFeedback      = objc.IBOutlet()
    customSignatureMatcherDefault       = objc.IBOutlet()
    helpButton                          = objc.IBOutlet()
    donateButton                        = objc.IBOutlet()

    @classmethod
    def registerQuoteFixApplication(cls, app):
        cls.app = app
        # inject preferences module
        prefs = NSPreferences.sharedPreferences()
        if prefs:
            QuoteFixPreferences.injectPreferencesModule(prefs)

    @objc.IBAction
    def changeDebugging_(self, sender):
        is_debugging = sender.state()
        logger.setLevel(is_debugging and logger.DEBUG or logger.WARNING)
        logger.debug('debug logging active')

    @objc.IBAction
    def changeUpdateInterval_(self, sender):
        self.app.check_update_interval = sender.selectedSegment()

    @objc.IBAction
    def performUpdateCheckNow_(self, sender):
        self.app.check_for_updates()
        self.setLastUpdateCheck()

    @objc.IBAction
    def donateButtonPressed_(self, sender):
        NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_("https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=4UF2KB2BTW6AC"))

    @objc.IBAction
    def helpButtonPressed_(self, sender):
        # open help url
        NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_("http://code.google.com/p/quotefixformac/wiki/CustomAttribution"))

    def awakeFromNib(self):
        self.currentVersionUpdater.setStringValue_(self.app.version)
        self.updateInterval.setSelectedSegment_(self.app.check_update_interval)
        self.setLastUpdateCheck()

        # set donate image
        bundle  = NSBundle.bundleWithIdentifier_('name.klep.mail.QuoteFix')
        path    = bundle.pathForResource_ofType_("donate", "gif")
        image   = NSImage.alloc().initByReferencingFile_(path)
        self.donateButton.setImage_(image)

        # check custom signature matcher
        self.check_signature_matcher(self.customSignatureMatcher)
        self.customSignatureMatcherDefault.setStringValue_(self.app.default_signature_matcher)

        # set attribution previews
        self.set_preview(self.customReplyAttribution)
        self.set_preview(self.customForwardingAttribution)
        self.set_preview(self.customSendAgainAttribution)

    def setLastUpdateCheck(self):
        date = self.app.last_update_check
        if date:
            formatter = NSDateFormatter.alloc().init()
            # use current user locale for 'last update' timestamp
            formatter.setLocale_(NSLocale.currentLocale())
            # use user-definable 'medium style' formats
            formatter.setTimeStyle_(NSDateFormatterMediumStyle)
            formatter.setDateStyle_(NSDateFormatterMediumStyle)
            date = formatter.stringFromDate_(date)
        self.lastUpdateCheck.setStringValue_(date)

    # act as a delegate for text fields
    def controlTextDidChange_(self, notification):
        obj = notification.object()
        tag = obj.tag()
        # update previews when customized attribution fields change
        if tag in [ 31, 32, 33 ]:
            self.set_preview(obj)
        # check custom signature matcher and provide feedback
        elif tag in [ 50 ]:
            self.check_signature_matcher(obj)

    def control_textView_doCommandBySelector_(self, control, textview, selector):
        if str(selector) == 'insertNewline:':
            textview.insertNewlineIgnoringFieldEditor_(self)
            return True
        return False

    # check custom signature for a valid regular expression
    def check_signature_matcher(self, obj):
        regex       = obj.stringValue()
        feedback    = self.customSignatureMatcherFeedback
        try:
            re.compile(regex)
            feedback.setColor_(NSColor.greenColor())
            feedback.setToolTip_("")
        except re.error, e:
            feedback.setColor_(NSColor.redColor())
            feedback.setToolTip_(str(e))

    # render a preview message for customized attributions
    def set_preview(self, sender):
        if not sender:
            return
        viewers = MessageViewer.allMessageViewers()
        if not viewers:
            return
        messages = viewers[0].selectedMessages()
        if not messages:
            return

        preview = CustomizedAttribution.render_attribution(
            messages[0],
            messages[0],
            sender.stringValue(),
            False
        )

        # make newlines visible
        preview = preview.replace('\n', u'⤦\n')
        sender.setToolTip_(htmlunescape(preview))

########NEW FILE########
__FILENAME__ = preview
from    quotefix.attributionclasses import QFMessage
from    datetime                    import datetime, timedelta

class PreviewMessage:

    sender                  = lambda s: "Original Sender <original@sender.domain>"
    senderAddressComment    = lambda s: "Original Sender"
    to                      = lambda s: "Original Receiver <original@sender.domain>"
    subject                 = lambda s: "This is the original subject"
    dateSent                = lambda s: datetime.now() - timedelta(seconds = 3600)
    dateReceived            = lambda s: datetime.now() - timedelta(seconds = 1800)
    toRecipients            = lambda s: [ "Original Receiver <original@sender.dom>" ]
    ccRecipients            = lambda s: [ "CC Recip 1 <cc1@test>", "CC Recip 2 <cc2@test>" ]
    recipients              = lambda s: s.toRecipients() + s.ccRecipients()
    bccRecipients           = lambda s: []

class PreviewResponse:

    sender                  = lambda s: "Your Name <you@some.domain>"
    senderAddressComment    = lambda s: "Your Name"
    to                      = lambda s: "New Receiver <new@receiver.domain>"
    subject                 = lambda s: "This is the *new* subject"
    dateSent                = lambda s: datetime.now()
    dateReceived            = lambda s: datetime.now()
    recipients              = lambda s: []
    toRecipients            = lambda s: []
    ccRecipients            = lambda s: []
    bccRecipients           = lambda s: []

# 'fake' message to preview custom reply/forward attribution
preview_message = {
    'message'   : QFMessage(PreviewMessage()),
    'response'  : QFMessage(PreviewResponse())
}

########NEW FILE########
__FILENAME__ = pyratemp
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Small, simple and powerful template-engine for python.

A template-engine for python, which is very simple, easy to use, small,
fast, powerful, modular, extensible, well documented and pythonic.

See documentation for a list of features, template-syntax etc.

:Version:   0.2.0

:Usage:
    see class ``Template`` and examples below.

:Example:

    quickstart::
        >>> t = Template("hello @!name!@")
        >>> print t(name="marvin")
        hello marvin

    generic usage::
        >>> t = Template("output is in Unicode äöü€")
        >>> t                                           #doctest: +ELLIPSIS
        <...Template instance at 0x...>
        >>> t()
        u'output is in Unicode \\xe4\\xf6\\xfc\\u20ac'
        >>> unicode(t)
        u'output is in Unicode \\xe4\\xf6\\xfc\\u20ac'

    with data::
        >>> t = Template("hello @!name!@", data={"name":"world"})
        >>> t()
        u'hello world'
        >>> t(name="worlds")
        u'hello worlds'

        # >>> t(note="data must be Unicode or ASCII", name=u"ä")
        # u'hello \\xe4'

    escaping::
        >>> t = Template("hello escaped: @!name!@, unescaped: $!name!$")
        >>> t(name='''<>&'"''')
        u'hello escaped: &lt;&gt;&amp;&#39;&quot;, unescaped: <>&\\'"'
    
    result-encoding::
        # encode the unicode-object to your encoding with encode()
        >>> t = Template("hello äöü€")
        >>> result = t()
        >>> result
        u'hello \\xe4\\xf6\\xfc\\u20ac'
        >>> result.encode("utf-8")
        'hello \\xc3\\xa4\\xc3\\xb6\\xc3\\xbc\\xe2\\x82\\xac'
        >>> result.encode("ascii")
        Traceback (most recent call last):
          ...
        UnicodeEncodeError: 'ascii' codec can't encode characters in position 6-9: ordinal not in range(128)
        >>> result.encode("ascii", 'xmlcharrefreplace')
        'hello &#228;&#246;&#252;&#8364;'

    python-expressions::
        >>> Template('formatted: @! "%8.5f" % value !@')(value=3.141592653)
        u'formatted:  3.14159'
        >>> Template("hello --@!name.upper().center(20)!@--")(name="world")
        u'hello --       WORLD        --'
        >>> Template("calculate @!var*5+7!@")(var=7)
        u'calculate 42'

    blocks (if/for/macros/...)::
        >>> t = Template("<!--(if foo == 1)-->bar<!--(elif foo == 2)-->baz<!--(else)-->unknown(@!foo!@)<!--(end)-->")
        >>> t(foo=2)
        u'baz'
        >>> t(foo=5)
        u'unknown(5)'

        >>> t = Template("<!--(for i in mylist)-->@!i!@ <!--(else)-->(empty)<!--(end)-->")
        >>> t(mylist=[])
        u'(empty)'
        >>> t(mylist=[1,2,3])
        u'1 2 3 '

        >>> t = Template("<!--(for i,elem in enumerate(mylist))--> - @!i!@: @!elem!@<!--(end)-->")
        >>> t(mylist=["a","b","c"])
        u' - 0: a - 1: b - 2: c'

        >>> t = Template('<!--(macro greetings)-->hello <strong>@!name!@</strong><!--(end)-->  @!greetings(name=user)!@')
        >>> t(user="monty")
        u'  hello <strong>monty</strong>'

    exists::
        >>> t = Template('<!--(if exists("foo"))-->YES<!--(else)-->NO<!--(end)-->')
        >>> t()
        u'NO'
        >>> t(foo=1)
        u'YES'
        >>> t(foo=None)       # note this difference to 'default()'
        u'YES'

    default-values::
        # non-existing variables raise an error
        >>> Template('hi @!optional!@')()
        Traceback (most recent call last):
          ...
        TemplateRenderError: Cannot eval expression 'optional'. (NameError: name 'optional' is not defined)

        >>> t = Template('hi @!default("optional","anyone")!@')
        >>> t()
        u'hi anyone'
        >>> t(optional=None)
        u'hi anyone'
        >>> t(optional="there")
        u'hi there'

        # the 1st parameter can be any eval-expression
        >>> t = Template('@!default("5*var1+var2","missing variable")!@')
        >>> t(var1=10)
        u'missing variable'
        >>> t(var1=10, var2=2)
        u'52'

        # also in blocks
        >>> t = Template('<!--(if default("opt1+opt2",0) > 0)-->yes<!--(else)-->no<!--(end)-->')
        >>> t()
        u'no'
        >>> t(opt1=23, opt2=42)
        u'yes'

        >>> t = Template('<!--(for i in default("optional_list",[]))-->@!i!@<!--(end)-->')
        >>> t()
        u''
        >>> t(optional_list=[1,2,3])
        u'123'

        
        # but make sure to put the expression in quotation marks, otherwise:
        >>> Template('@!default(optional,"fallback")!@')()
        Traceback (most recent call last):
          ...
        TemplateRenderError: Cannot eval expression 'default(optional,"fallback")'. (NameError: name 'optional' is not defined)

    setvar::
        >>> t = Template('$!setvar("i", "i+1")!$@!i!@')
        >>> t(i=6)
        u'7'
        
        >>> t = Template('''<!--(if isinstance(s, (list,tuple)))-->$!setvar("s", '"\\\\\\\\n".join(s)')!$<!--(end)-->@!s!@''')
        >>> t(isinstance=isinstance, s="123")
        u'123'
        >>> t(isinstance=isinstance, s=["123", "456"])
        u'123\\n456'

:Author:    Roland Koebler (rk at simple-is-better dot org)
:Copyright: Roland Koebler
:License:   MIT/X11-like, see __license__
"""

__version__ = "0.2.0"
__author__   = "Roland Koebler <rk at simple-is-better dot org>"
__license__  = """Copyright (c) Roland Koebler, 2007-2010

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
IN THE SOFTWARE."""

#=========================================

import __builtin__, os
import re

#=========================================
# some useful functions

#----------------------
# string-position: i <-> row,col

def srow(string, i):
    """Get line numer of ``string[i]`` in `string`.

    :Returns: row, starting at 1
    :Note:    This works for text-strings with ``\\n`` or ``\\r\\n``.
    """
    return string.count('\n', 0, max(0, i)) + 1

def scol(string, i):
    """Get column number of ``string[i]`` in `string`.

    :Returns: column, starting at 1 (but may be <1 if i<0)
    :Note:    This works for text-strings with ``\\n`` or ``\\r\\n``.
    """
    return i - string.rfind('\n', 0, max(0, i))

def sindex(string, row, col):
    """Get index of the character at `row`/`col` in `string`.
   
    :Parameters:
        - `row`: row number, starting at 1.
        - `col`: column number, starting at 1.
    :Returns:    ``i``, starting at 0 (but may be <1 if row/col<0)
    :Note:       This works for text-strings with '\\n' or '\\r\\n'.
    """
    n = 0
    for _ in range(row-1):
        n = string.find('\n', n) + 1
    return n+col-1

#----------------------

def dictkeyclean(d):
    """Convert all keys of the dict `d` to strings.
    """
    new_d = {}
    for k, v in d.iteritems():
        new_d[str(k)] = v
    return new_d

#----------------------

def dummy(*args, **kwargs):
    """Dummy function, doing nothing.
    """
    pass

def dummy_raise(exception, value):
    """Create an exception-raising dummy function.

    :Returns: dummy function, raising ``exception(value)``
    """
    def mydummy(*args, **kwargs):
        raise exception(value)
    return mydummy

#=========================================
# escaping

(NONE, HTML, LATEX) = range(0, 3)
ESCAPE_SUPPORTED = {"NONE":None, "HTML":HTML, "LATEX":LATEX} #for error-/parameter-checking

def escape(s, format=HTML):
    """Replace special characters by their escape sequence.

    :Parameters:
        - `s`:      string or unicode-string to escape
        - `format`:

          - `NONE`:  nothing is replaced
          - `HTML`:  replace &<>'" by &...;
          - `LATEX`: replace \#$%&_{} (TODO! - this is very incomplete!)
    :Returns:
        the escaped string in unicode
    :Exceptions:
        - `ValueError`: if `format` is invalid.

    :TODO:  complete LaTeX-escaping, optimize speed
    """
    #Note: If you have to make sure that every character gets replaced
    #      only once (and if you cannot achieve this with the following code),
    #      use something like u"".join([replacedict.get(c,c) for c in s])
    #      which is about 2-3 times slower (but maybe needs less memory).
    #Note: This is one of the most time-consuming parts of the template.
    #      So maybe speed this up.

    if format is None or format == NONE:
        pass
    elif format == HTML:
        s = s.replace(u"&", u"&amp;") # must be done first!
        s = s.replace(u"<", u"&lt;")
        s = s.replace(u">", u"&gt;")
        s = s.replace(u'"', u"&quot;")
        s = s.replace(u"'", u"&#39;")
    elif format == LATEX:
        #TODO: which are the "reserved" characters for LaTeX?
        #      are there more than these?
        s = s.replace("\\", u"\\backslash{}")   #must be done first!
        s = s.replace("#",  u"\\#")
        s = s.replace("$",  u"\\$")
        s = s.replace("%",  u"\\%")
        s = s.replace("&",  u"\\&")
        s = s.replace("_",  u"\\_")
        s = s.replace("{",  u"\\{")
        s = s.replace("}",  u"\\}")
    else:
        raise ValueError('Invalid format (only None, HTML and LATEX are supported).')
    return unicode(s)

#=========================================

#-----------------------------------------
# Exceptions

class TemplateException(Exception):
    """Base class for template-exceptions."""
    pass

class TemplateParseError(TemplateException):
    """Template parsing failed."""
    def __init__(self, err, errpos):
        """
        :Parameters:
            - `err`:    error-message or exception to wrap
            - `errpos`: ``(filename,row,col)`` where the error occured.
        """
        self.err = err
        self.filename, self.row, self.col = errpos
        TemplateException.__init__(self)
    def __str__(self):
        if not self.filename:
            return "line %d, col %d: %s" % (self.row, self.col, str(self.err))
        else:
            return "file %s, line %d, col %d: %s" % (self.filename, self.row, self.col, str(self.err))

class TemplateSyntaxError(TemplateParseError, SyntaxError):
    """Template syntax-error."""
    pass

class TemplateIncludeError(TemplateParseError):
    """Template 'include' failed."""
    pass

class TemplateRenderError(TemplateException):
    """Template rendering failed."""
    pass

#-----------------------------------------
# Loader

class LoaderString:
    """Load template from a string/unicode.

    Note that 'include' is not possible in such templates.
    """
    def __init__(self, encoding='utf-8'):
        self.encoding = encoding

    def load(self, string):
        """Return template-string as unicode.
        """
        if isinstance(string, unicode):
            u = string
        else:
            u = unicode(string, self.encoding)
        return u

class LoaderFile:
    """Load template from a file.
    
    When loading a template from a file, it's possible to including other
    templates (by using 'include' in the template). But for simplicity
    and security, all included templates have to be in the same directory!
    (see ``allowed_path``)
    """
    def __init__(self, allowed_path=None, encoding='utf-8'):
        """Init the loader.

        :Parameters:
            - `allowed_path`: path of the template-files
            - `encoding`: encoding of the template-files
        :Exceptions:
            - `ValueError`: if `allowed_path` is not a directory
        """
        if allowed_path and not os.path.isdir(allowed_path):
            raise ValueError("'allowed_path' has to be a directory.")
        self.path     = allowed_path
        self.encoding = encoding

    def load(self, filename):
        """Load a template from a file.

        Check if filename is allowed and return its contens in unicode.

        :Parameters:
            - `filename`: filename of the template without path
        :Returns:
            the contents of the template-file in unicode
        :Exceptions:
            - `ValueError`: if `filename` contains a path
        """
        if filename != os.path.basename(filename):
            raise ValueError("No path allowed in filename. (%s)" %(filename))
        filename = os.path.join(self.path, filename)

        f = open(filename, 'rb')
        string = f.read()
        f.close()

        u = unicode(string, self.encoding)

        return u

#-----------------------------------------
# Parser

class Parser(object):
    """Parse a template into a parse-tree.
    
    Includes a syntax-check, an optional expression-check and verbose
    error-messages.

    See documentation for a description of the parse-tree.
    """
    # template-syntax
    _comment_start = "{#"
    _comment_end   = "#}"
    _sub_start     = "{{"
    _sub_end       = "}}"
    _subesc_start  = "${"
    _subesc_end    = "}"
    _block_start   = "{%"
    _block_end     = "%}"

    # build regexps
    # comment
    #   single-line, until end-tag or end-of-line.
    _strComment = r"""%s(?P<content>.*?)(?P<end>%s|\n|$)""" \
                    % (re.escape(_comment_start), re.escape(_comment_end))
    _reComment = re.compile(_strComment, re.M)

    # escaped or unescaped substitution
    #   single-line ("|$" is needed to be able to generate good error-messges)
    _strSubstitution = r"""
                    (
                    %s\s*(?P<sub>.*?)\s*(?P<end>%s|$)       #substitution
                    |
                    %s\s*(?P<escsub>.*?)\s*(?P<escend>%s|$) #escaped substitution
                    )
                """ % (re.escape(_sub_start),    re.escape(_sub_end),
                       re.escape(_subesc_start), re.escape(_subesc_end))
    _reSubstitution = re.compile(_strSubstitution, re.X|re.M)

    # block
    #   - single-line, no nesting.
    #   or
    #   - multi-line, nested by whitespace indentation:
    #       * start- and end-tag of a block must have exactly the same indentation.
    #       * start- and end-tags of *nested* blocks should have a greater indentation.
    # NOTE: A single-line block must not start at beginning of the line with
    #       the same indentation as the enclosing multi-line blocks!
    #       Note that "       " and "\t" are different, although they may
    #       look the same in an editor!
    _s = re.escape(_block_start) + "\s*"
    _e = "\s*" + re.escape(_block_end)
    _strBlock = r"""
                    ^(?P<mEnd>[ \t]*)%send%s(?P<meIgnored>.*)\r?\n?   # multi-line end  (^   <!--(end)-->IGNORED_TEXT\n)
                    |
                    (?P<sEnd>)%send%s                               # single-line end (<!--(end)-->)
                    |
                    (?P<sSpace>[ \t]*)                              # single-line tag (no nesting)
                    %s(?P<sKeyw>\w+)[ \t]*(?P<sParam>.*?)%s
                    (?P<sContent>.*?)
                    (?=(?:%s.*?%s.*?)??%send%s)                     # (match until end or i.e. <!--(elif/else...)-->)
                    |
                                                                    # multi-line tag, nested by whitespace indentation
                    ^(?P<indent>[ \t]*)                             #   save indentation of start tag
                    %s(?P<mKeyw>\w+)\s*(?P<mParam>.*?)%s(?P<mIgnored>.*)\r?\n
                    (?P<mContent>(?:.*\n)*?)
                    (?=(?P=indent)%s(?:.|\s)*?%s)                   #   match indentation
                """ % (_s, _e,
                       _s, _e,
                       _s, _e, _s, _e, _s, _e,
                       _s, _e, _s, _e)
    _reBlock = re.compile(_strBlock, re.X|re.M)

    # "for"-block parameters: "var(,var)* in ..."
    _strForParam = r"""^(?P<names>\w+(?:\s*,\s*\w+)*)\s+in\s+(?P<iter>.+)$"""
    _reForParam  = re.compile(_strForParam)

    # allowed macro-names
    _reMacroParam = re.compile(r"""^\w+$""")


    def __init__(self, loadfunc=None, testexpr=None, escape=HTML):
        """Init the parser.

        :Parameters:
            - `loadfunc`: function to load included templates
              (i.e. ``LoaderFile(...).load``)
            - `testexpr`: function to test if a template-expressions is valid
              (i.e. ``EvalPseudoSandbox().compile``)
            - `escape`:   default-escaping (may be modified by the template)
        :Exceptions:
            - `ValueError`: if `testexpr` or `escape` is invalid.
        """
        if loadfunc is None:
            self._load = dummy_raise(NotImplementedError, "'include' not supported, since no 'loadfunc' was given.")
        else:
            self._load = loadfunc

        if testexpr is None:
            self._testexprfunc = dummy
        else:
            try:    # test if testexpr() works
                testexpr("i==1")
            except Exception,err:
                raise ValueError("Invalid 'testexpr' (%s)." %(err))
            self._testexprfunc = testexpr

        if escape not in ESCAPE_SUPPORTED.values():
            raise ValueError("Unsupported 'escape' (%s)." %(escape))
        self.escape = escape
        self._includestack = []

    def parse(self, template):
        """Parse a template.

        :Parameters:
            - `template`: template-unicode-string
        :Returns:         the resulting parse-tree
        :Exceptions:
            - `TemplateSyntaxError`: for template-syntax-errors
            - `TemplateIncludeError`: if template-inclusion failed
            - `TemplateException`
        """
        self._includestack = [(None, template)]   # for error-messages (_errpos)
        return self._parse(template)

    def _errpos(self, fpos):
        """Convert `fpos` to ``(filename,row,column)`` for error-messages."""
        filename, string = self._includestack[-1]
        return filename, srow(string, fpos), scol(string, fpos)

    def _testexpr(self, expr,  fpos=0):
        """Test a template-expression to detect errors."""
        try:
            self._testexprfunc(expr)
        except SyntaxError,err:
            raise TemplateSyntaxError(err, self._errpos(fpos))

    def _parse_sub(self, parsetree, text, fpos=0):
        """Parse substitutions, and append them to the parse-tree.
        
        Additionally, remove comments.
        """
        curr = 0
        for match in self._reSubstitution.finditer(text):
            start = match.start()
            if start > curr:
                parsetree.append(("str", self._reComment.sub('', text[curr:start])))

            if match.group("sub") is not None:
                if not match.group("end"):
                    raise TemplateSyntaxError("Missing closing tag '%s' for '%s'." 
                            % (self._sub_end, match.group()), self._errpos(fpos+start))
                if len(match.group("sub")) > 0:
                    self._testexpr(match.group("sub"), fpos+start)
                    parsetree.append(("sub", match.group("sub")))
            else:
                assert(match.group("escsub") is not None)
                if not match.group("escend"):
                    raise TemplateSyntaxError("Missing closing tag '%s' for '%s'."
                            % (self._subesc_end, match.group()), self._errpos(fpos+start))
                if len(match.group("escsub")) > 0:
                    self._testexpr(match.group("escsub"), fpos+start)
                    parsetree.append(("esc", self.escape, match.group("escsub")))

            curr = match.end()

        if len(text) > curr:
            parsetree.append(("str", self._reComment.sub('', text[curr:])))

    def _parse(self, template, fpos=0):
        """Recursive part of `parse()`.
        
        :Parameters:
            - template
            - fpos: position of ``template`` in the complete template (for error-messages)
        """
        # blank out comments
        # (So that its content does not collide with other syntax, and
        #  because removing them completely would falsify the character-
        #  position ("match.start()") of error-messages)
        template = self._reComment.sub(lambda match: self._comment_start+" "*len(match.group(1))+match.group(2), template)

        # init parser
        parsetree = []
        curr = 0            # current position (= end of previous block)
        block_type = None   # block type: if,for,macro,raw,...
        block_indent = None # None: single-line, >=0: multi-line

        # find blocks
        for match in self._reBlock.finditer(template):
            start = match.start()
            # process template-part before this block
            if start > curr:
                self._parse_sub(parsetree, template[curr:start], fpos)

            # analyze block syntax (incl. error-checking and -messages)
            keyword = None
            block = match.groupdict()
            pos__ = fpos + start                # shortcut
            if   block["sKeyw"] is not None:    # single-line block tag
                block_indent = None
                keyword = block["sKeyw"]
                param   = block["sParam"]
                content = block["sContent"]
                if block["sSpace"]:             # restore spaces before start-tag
                    if len(parsetree) > 0 and parsetree[-1][0] == "str":
                        parsetree[-1] = ("str", parsetree[-1][1] + block["sSpace"])
                    else:
                        parsetree.append(("str", block["sSpace"]))
                pos_p = fpos + match.start("sParam")    # shortcuts
                pos_c = fpos + match.start("sContent")
            elif block["mKeyw"] is not None:    # multi-line block tag
                block_indent = len(block["indent"])
                keyword = block["mKeyw"]
                param   = block["mParam"]
                content = block["mContent"]
                pos_p = fpos + match.start("mParam")
                pos_c = fpos + match.start("mContent")
                ignored = block["mIgnored"].strip()
                if ignored  and  ignored != self._comment_start:
                    raise TemplateSyntaxError("No code allowed after block-tag.", self._errpos(fpos+match.start("mIgnored")))
            elif block["mEnd"] is not None:     # multi-line block end
                if block_type is None:
                    raise TemplateSyntaxError("No block to end here/invalid indent.", self._errpos(pos__) )
                if block_indent != len(block["mEnd"]):
                    raise TemplateSyntaxError("Invalid indent for end-tag.", self._errpos(pos__) )
                ignored = block["meIgnored"].strip()
                if ignored  and  ignored != self._comment_start:
                    raise TemplateSyntaxError("No code allowed after end-tag.", self._errpos(fpos+match.start("meIgnored")))
                block_type = None
            elif block["sEnd"] is not None:     # single-line block end
                if block_type is None:
                    raise TemplateSyntaxError("No block to end here/invalid indent.", self._errpos(pos__))
                if block_indent is not None:
                    raise TemplateSyntaxError("Invalid indent for end-tag.", self._errpos(pos__))
                block_type = None
            else:
                raise TemplateException("FATAL: Block regexp error. Please contact the author. (%s)" % match.group())

            # analyze block content (mainly error-checking and -messages)
            if keyword:
                keyword = keyword.lower()
                if   'for'   == keyword:
                    if block_type is not None:
                        raise TemplateSyntaxError("Missing block-end-tag before new block at '%s'." %(match.group()), self._errpos(pos__))
                    block_type = 'for'
                    cond = self._reForParam.match(param)
                    if cond is None:
                        raise TemplateSyntaxError("Invalid 'for ...' at '%s'." %(param), self._errpos(pos_p))
                    names = tuple(n.strip()  for n in cond.group("names").split(","))
                    self._testexpr(cond.group("iter"), pos_p+cond.start("iter"))
                    parsetree.append(("for", names, cond.group("iter"), self._parse(content, pos_c)))
                elif 'if'    == keyword:
                    if block_type is not None:
                        raise TemplateSyntaxError("Missing block-end-tag before new block at '%s'." %(match.group()), self._errpos(pos__))
                    if not param:
                        raise TemplateSyntaxError("Missing condition for 'if' at '%s'." %(match.group()), self._errpos(pos__))
                    block_type = 'if'
                    self._testexpr(param, pos_p)
                    parsetree.append(("if", param, self._parse(content, pos_c)))
                elif 'elif'  == keyword:
                    if block_type != 'if':
                        raise TemplateSyntaxError("'elif' may only appear after 'if' at '%s'." %(match.group()), self._errpos(pos__))
                    if not param:
                        raise TemplateSyntaxError("Missing condition for 'elif' at '%s'." %(match.group()), self._errpos(pos__))
                    self._testexpr(param, pos_p)
                    parsetree.append(("elif", param, self._parse(content, pos_c)))
                elif 'else'  == keyword:
                    if block_type not in ('if', 'for'):
                        raise TemplateSyntaxError("'else' may only appear after 'if' of 'for' at '%s'." %(match.group()), self._errpos(pos__))
                    if param:
                        raise TemplateSyntaxError("'else' may not have parameters at '%s'." %(match.group()), self._errpos(pos__))
                    parsetree.append(("else", self._parse(content, pos_c)))
                elif 'macro' == keyword:
                    if block_type is not None:
                        raise TemplateSyntaxError("Missing block-end-tag before new block '%s'." %(match.group()), self._errpos(pos__))
                    block_type = 'macro'
                    # make sure param is "\w+" (instead of ".+")
                    if not param:
                        raise TemplateSyntaxError("Missing name for 'macro' at '%s'." %(match.group()), self._errpos(pos__))
                    if not self._reMacroParam.match(param):
                        raise TemplateSyntaxError("Invalid name for 'macro' at '%s'." %(match.group()), self._errpos(pos__))
                    #remove last newline
                    if len(content) > 0 and content[-1] == '\n':
                        content = content[:-1]
                    if len(content) > 0 and content[-1] == '\r':
                        content = content[:-1]
                    parsetree.append(("macro", param, self._parse(content, pos_c)))

                # parser-commands
                elif 'raw'   == keyword:
                    if block_type is not None:
                        raise TemplateSyntaxError("Missing block-end-tag before new block '%s'." %(match.group()), self._errpos(pos__))
                    if param:
                        raise TemplateSyntaxError("'raw' may not have parameters at '%s'." %(match.group()), self._errpos(pos__))
                    block_type = 'raw'
                    parsetree.append(("str", content))
                elif 'include' == keyword:
                    if block_type is not None:
                        raise TemplateSyntaxError("Missing block-end-tag before new block '%s'." %(match.group()), self._errpos(pos__))
                    if param:
                        raise TemplateSyntaxError("'include' may not have parameters at '%s'." %(match.group()), self._errpos(pos__))
                    block_type = 'include'
                    try:
                        u = self._load(content.strip())
                    except Exception,err:
                        raise TemplateIncludeError(err, self._errpos(pos__))
                    self._includestack.append((content.strip(), u))  # current filename/template for error-msg.
                    p = self._parse(u)
                    self._includestack.pop()
                    parsetree.extend(p)
                elif 'set_escape' == keyword:
                    if block_type is not None:
                        raise TemplateSyntaxError("Missing block-end-tag before new block '%s'." %(match.group()), self._errpos(pos__))
                    if param:
                        raise TemplateSyntaxError("'set_escape' may not have parameters at '%s'." %(match.group()), self._errpos(pos__))
                    block_type = 'set_escape'
                    esc = content.strip().upper()
                    if esc not in ESCAPE_SUPPORTED:
                        raise TemplateSyntaxError("Unsupported escape '%s'." %(esc), self._errpos(pos__))
                    self.escape = ESCAPE_SUPPORTED[esc]
                else:
                    raise TemplateSyntaxError("Invalid keyword '%s'." %(keyword), self._errpos(pos__))
            curr = match.end()

        if block_type is not None:
            raise TemplateSyntaxError("Missing end-tag.", self._errpos(pos__))

        if len(template) > curr:            # process template-part after last block
            self._parse_sub(parsetree, template[curr:], fpos)

        return parsetree

#-----------------------------------------
# Evaluation

# some checks
assert len(eval("dir()", {'__builtins__':{'dir':dir}})) == 1, \
    "FATAL: 'eval' does not work as expected (%s)."
assert compile("0 .__class__", "<string>", "eval").co_names == ('__class__',), \
    "FATAL: 'compile' does not work as expected."

class EvalPseudoSandbox:
    """An eval-pseudo-sandbox.

    The pseudo-sandbox restricts the available functions/objects, so the
    code can only access:

    - some of the builtin python-functions, which are considered "safe"
      (see safe_builtins)
    - some additional functions (exists(), default(), setvar())
    - the passed objects incl. their methods.

    Additionally, names beginning with "_" are forbidden.
    This is to prevent things like '0 .__class__', with which you could
    easily break out of a "sandbox".

    Be careful to only pass "safe" objects/functions to the template,
    because any unsafe function/method could break the sandbox!
    For maximum security, restrict the access to as few objects/functions
    as possible!

    :Warning:
        Note that this is no real sandbox! (And although I don't know any
        way to break out of the sandbox without passing-in an unsafe object,
        I cannot guarantee that there is no such way. So use with care.)

        Take care if you want to use it for untrusted code!!
    """

    safe_builtins = {
        "True"      : __builtin__.True,
        "False"     : __builtin__.False,
        "None"      : __builtin__.None,

        "abs"       : __builtin__.abs,
        "chr"       : __builtin__.chr,
        "cmp"       : __builtin__.cmp,
        "divmod"    : __builtin__.divmod,
        "hash"      : __builtin__.hash,
        "hex"       : __builtin__.hex,
        "len"       : __builtin__.len,
        "max"       : __builtin__.max,
        "min"       : __builtin__.min,
        "oct"       : __builtin__.oct,
        "ord"       : __builtin__.ord,
        "pow"       : __builtin__.pow,
        "range"     : __builtin__.range,
        "round"     : __builtin__.round,
        "sorted"    : __builtin__.sorted,
        "sum"       : __builtin__.sum,
        "unichr"    : __builtin__.unichr,
        "zip"       : __builtin__.zip,

        "bool"      : __builtin__.bool,
        "complex"   : __builtin__.complex,
        "dict"      : __builtin__.dict,
        "enumerate" : __builtin__.enumerate,
        "float"     : __builtin__.float,
        "int"       : __builtin__.int,
        "list"      : __builtin__.list,
        "long"      : __builtin__.long,
        "reversed"  : __builtin__.reversed,
        "str"       : __builtin__.str,
        "tuple"     : __builtin__.tuple,
        "unicode"   : __builtin__.unicode,
        "xrange"    : __builtin__.xrange,
    }

    def __init__(self):
        self._compile_cache = {}
        self.locals_ptr = None
        self.eval_allowed_globals = self.safe_builtins.copy()
        self.register("__import__", self.f_import)
        self.register("exists",  self.f_exists)
        self.register("default", self.f_default)
        self.register("setvar",  self.f_setvar)

    def register(self, name, obj):
        """Add an object to the "allowed eval-globals".

        Mainly useful to add user-defined functions to the pseudo-sandbox.
        """
        self.eval_allowed_globals[name] = obj

    def compile(self, expr):
        """Compile a python-eval-expression.

        - Use a compile-cache.
        - Raise a `NameError` if `expr` contains a name beginning with ``_``.
        
        :Returns: the compiled `expr`
        :Exceptions:
            - `SyntaxError`: for compile-errors
            - `NameError`: if expr contains a name beginning with ``_``
        """
        if expr not in self._compile_cache:
            c = compile(expr, "", "eval")
            for i in c.co_names:    #prevent breakout via new-style-classes
                if i[0] == '_':
                    raise NameError("Name '%s' is not allowed." %(i))
            self._compile_cache[expr] = c
        return self._compile_cache[expr]

    def eval(self, expr, locals):
        """Eval a python-eval-expression.
        
        Sets ``self.locals_ptr`` to ``locales`` and compiles the code
        before evaluating.
        """
        sav = self.locals_ptr
        self.locals_ptr = locals
        x = eval(self.compile(expr), {"__builtins__":self.eval_allowed_globals}, locals)
        self.locals_ptr = sav
        return x

    def f_import(self, name, *args, **kwargs):
        """``import``/``__import__()`` for the sandboxed code.

        Since "import" is insecure, the PseudoSandbox does not allow to
        import other modules. But since some functions need to import
        other modules (e.g. "datetime.datetime.strftime" imports "time"),
        this function replaces the builtin "import" and allows to use
        modules which are already accessible by the sandboxed code.

        :Note:
            - This probably only works for rather simple imports.
            - For security, it may be better to avoid such (complex) modules
              which import other modules. (e.g. use time.localtime and
              time.strftime instead of datetime.datetime.strftime)

        :Example:
            
            >>> from datetime import datetime
            >>> import pyratemp
            >>> t = pyratemp.Template('@!mytime.strftime("%H:%M:%S")!@')
            >>> print t(mytime=datetime.now())
            Traceback (most recent call last):
              ...
            ImportError: import not allowed in pseudo-sandbox; try to import 'time' yourself and pass it to the sandbox/template
            >>> import time
            >>> print t(mytime=datetime.strptime("13:40:54", "%H:%M:%S"), time=time)
            13:40:54

            # >>> print t(mytime=datetime.now(), time=time)
            # 13:40:54
        """
        import types
        if self.locals_ptr is not None  and  name in self.locals_ptr  and  isinstance(self.locals_ptr[name], types.ModuleType):
            return self.locals_ptr[name]
        else:
            raise ImportError("import not allowed in pseudo-sandbox; try to import '%s' yourself and pass it to the sandbox/template" % name)

    def f_exists(self, varname):
        """``exists()`` for the sandboxed code.
        
        Test if the variable `varname` exists in the current locals-namespace.

        This only works for single variable names. If you want to test
        complicated expressions, use i.e. `default`.
        (i.e. `default("expr",False)`)

        :Note:      the variable-name has to be quoted! (like in eval)
        :Example:   see module-docstring
        """
        return (varname in self.locals_ptr)

    def f_default(self, expr, default=None):
        """``default()`` for the sandboxed code.
        
        Try to evaluate an expression and return the result or a
        fallback-/default-value; the `default`-value is used
        if `expr` does not exist/is invalid/results in None.

        This is very useful for optional data.

        :Parameter:
            - expr: eval-expression
            - default: fallback-falue if eval(expr) fails or is None.
        :Returns:
            the eval-result or the "fallback"-value.

        :Note:      the eval-expression has to be quoted! (like in eval)
        :Example:   see module-docstring
        """
        try:
            r = self.eval(expr, self.locals_ptr)
            if r is None:
                return default
            return r
        #TODO: which exceptions should be catched here?
        except (NameError, IndexError, KeyError):
            return default

    def f_setvar(self, name, expr):
        """``setvar()`` for the sandboxed code.

        Set a variable.

        :Example:   see module-docstring
        """
        self.locals_ptr[name] = self.eval(expr, self.locals_ptr)
        return ""

#-----------------------------------------
# basic template / subtemplate

class TemplateBase:
    """Basic template-class.
    
    Used both for the template itself and for 'macro's ("subtemplates") in
    the template.
    """

    def __init__(self, parsetree, renderfunc, data=None):
        """Create the Template/Subtemplate/Macro.

        :Parameters:
            - `parsetree`: parse-tree of the template/subtemplate/macro
            - `renderfunc`: render-function
            - `data`: data to fill into the template by default (dictionary).
              This data may later be overridden when rendering the template.
        :Exceptions:
            - `TypeError`: if `data` is not a dictionary
        """
        #TODO: parameter-checking?
        self.parsetree = parsetree
        if isinstance(data, dict):
            self.data = data
        elif data is None:
            self.data = {}
        else:
            raise TypeError('"data" must be a dict (or None).')
        self.current_data = data
        self._render = renderfunc

    def __call__(self, **override):
        """Fill out/render the template.

        :Parameters: 
            - `override`: objects to add to the data-namespace, overriding
              the "default"-data.
        :Returns:    the filled template (in unicode)
        :Note:       This is also called when invoking macros
                     (i.e. ``$!mymacro()!$``).
        """
        self.current_data = self.data.copy()
        self.current_data.update(override)
        u = u"".join(self._render(self.parsetree, self.current_data))
        self.current_data = self.data       # restore current_data
        return _dontescape(u)               # (see class _dontescape)

    def __unicode__(self):
        """Alias for __call__()."""
        return self.__call__()
    def __str__(self):
        """Only here for completeness. Use __unicode__ instead!"""
        return self.__call__()

#-----------------------------------------
# Renderer

class _dontescape(unicode):
    """Unicode-string which should not be escaped.

    If ``isinstance(object,_dontescape)``, then don't escape the object in
    ``@!...!@``. It's useful for not double-escaping macros, and it's
    automatically used for macros/subtemplates.

    :Note: This only works if the object is used on its own in ``@!...!@``.
           It i.e. does not work in ``@!object*2!@`` or ``@!object + "hi"!@``.
    """
    __slots__ = []


class Renderer(object):
    """Render a template-parse-tree.
    
    :Uses: `TemplateBase` for macros
    """

    def __init__(self, evalfunc, escapefunc):
        """Init the renderer.

        :Parameters:
            - `evalfunc`: function for template-expression-evaluation
              (i.e. ``EvalPseudoSandbox().eval``)
            - `escapefunc`: function for escaping special characters
              (i.e. `escape`)
        """
        #TODO: test evalfunc
        self.evalfunc = evalfunc
        self.escapefunc = escapefunc

    def _eval(self, expr, data):
        """evalfunc with error-messages"""
        try:
            return self.evalfunc(expr, data)
        #TODO: any other errors to catch here?
        except (TypeError,NameError,IndexError,KeyError,AttributeError, SyntaxError), err:
            raise TemplateRenderError("Cannot eval expression '%s'. (%s: %s)" %(expr, err.__class__.__name__, err))

    def render(self, parsetree, data):
        """Render a parse-tree of a template.

        :Parameters:
            - `parsetree`: the parse-tree
            - `data`:      the data to fill into the template (dictionary)
        :Returns:   the rendered output-unicode-string
        :Exceptions:
            - `TemplateRenderError`
        """
        _eval = self._eval  # shortcut
        output = []
        do_else = False     # use else/elif-branch?

        if parsetree is None:
            return ""
        for elem in parsetree:
            if   "str"   == elem[0]:
                output.append(elem[1])
            elif "sub"   == elem[0]:
                output.append(unicode(_eval(elem[1], data)))
            elif "esc"   == elem[0]:
                obj = _eval(elem[2], data)
                #prevent double-escape
                if isinstance(obj, _dontescape) or isinstance(obj, TemplateBase):
                    output.append(unicode(obj))
                else:
                    output.append(self.escapefunc(unicode(obj), elem[1]))
            elif "for"   == elem[0]:
                do_else = True
                (names, iterable) = elem[1:3]
                try:
                    loop_iter = iter(_eval(iterable, data))
                except TypeError:
                    raise TemplateRenderError("Cannot loop over '%s'." % iterable)
                for i in loop_iter:
                    do_else = False
                    if len(names) == 1:
                        data[names[0]] = i
                    else:
                        data.update(zip(names, i))   #"for a,b,.. in list"
                    output.extend(self.render(elem[3], data))
            elif "if"    == elem[0]:
                do_else = True
                if _eval(elem[1], data):
                    do_else = False
                    output.extend(self.render(elem[2], data))
            elif "elif"  == elem[0]:
                if do_else and _eval(elem[1], data):
                    do_else = False
                    output.extend(self.render(elem[2], data))
            elif "else"  == elem[0]:
                if do_else:
                    do_else = False
                    output.extend(self.render(elem[1], data))
            elif "macro" == elem[0]:
                data[elem[1]] = TemplateBase(elem[2], self.render, data)
            else:
                raise TemplateRenderError("Invalid parse-tree (%s)." %(elem))

        return output

#-----------------------------------------
# template user-interface (putting all together)

class Template(TemplateBase):
    """Template-User-Interface.

    :Usage:
        ::
            t = Template(...)  (<- see __init__)
            output = t(...)    (<- see TemplateBase.__call__)

    :Example:
        see module-docstring
    """

    def __init__(self, string=None,filename=None,parsetree=None, encoding='utf-8', data=None, escape=HTML,
            loader_class=LoaderFile,
            parser_class=Parser,
            renderer_class=Renderer,
            eval_class=EvalPseudoSandbox,
            escape_func=escape):
        """Load (+parse) a template.

        :Parameters:
            - `string,filename,parsetree`: a template-string,
                                           filename of a template to load,
                                           or a template-parsetree.
                                           (only one of these 3 is allowed)
            - `encoding`: encoding of the template-files (only used for "filename")
            - `data`:     data to fill into the template by default (dictionary).
                          This data may later be overridden when rendering the template.
            - `escape`:   default-escaping for the template, may be overwritten by the template!
            - `loader_class`
            - `parser_class`
            - `renderer_class`
            - `eval_class`
            - `escapefunc`
        """
        if [string, filename, parsetree].count(None) != 2:
            raise ValueError('Exactly 1 of string,filename,parsetree is necessary.')
  
        tmpl = None
        # load template
        if filename is not None:
            incl_load = loader_class(os.path.dirname(filename), encoding).load
            tmpl = incl_load(os.path.basename(filename))
        if string is not None:
            incl_load = dummy_raise(NotImplementedError, "'include' not supported for template-strings.")
            tmpl = LoaderString(encoding).load(string)

        # eval (incl. compile-cache)
        templateeval = eval_class()

        # parse
        if tmpl is not None:
            p = parser_class(loadfunc=incl_load, testexpr=templateeval.compile, escape=escape)
            parsetree = p.parse(tmpl)
            del p

        # renderer
        renderfunc = renderer_class(templateeval.eval, escape_func).render

        #create template
        TemplateBase.__init__(self, parsetree, renderfunc, data)


#=========================================
#doctest

def _doctest():
    """doctest this module."""
    import doctest
    doctest.testmod()

#----------------------
if __name__ == '__main__':
    _doctest()

#=========================================


########NEW FILE########
__FILENAME__ = updater
from    AppKit          import NSBundle, NSObject
from    Foundation      import NSLog
from    datetime        import datetime
from    logger          import logger
import  objc, os, os.path

# load Sparkle framework
BUNDLE          = NSBundle.bundleWithIdentifier_('name.klep.mail.QuoteFix')
frameworkspath  = BUNDLE.privateFrameworksPath()
sparklepath     = os.path.join(frameworkspath, 'Sparkle.framework')
sparkle         = dict() # use 'private' storage to keep Sparkle classes in
objc.loadBundle('Sparkle', sparkle, bundle_path = sparklepath)

class Updater:

    def __init__(self):
        # instantiate Sparkle updater
        try:
            self.updater = sparkle['SUUpdater'].updaterForBundle_(BUNDLE)
        except:
            NSLog("QuoteFix: updater error - cannot initialize the updater for QuoteFix. This usually happens because of compatibility issues between Mail plugins. Updates are disabled, but QuoteFix should function normally.")
            self.enabled = False
            return

        # set delegate
        self.updater.setDelegate_(UpdaterDelegate.alloc().init().retain())

        # reset update cycle
        self.updater.resetUpdateCycle()

        # updates are enabled
        self.enabled = True

    # check for updates now
    def check_for_updates(self):
        if not self.enabled:
            return
        logger.debug("checking for updates (URL = %s)" % self.updater.feedURL())
        self.updater.checkForUpdatesInBackground()

    @property
    def last_update_check(self):
        if not self.enabled:
            return None
        return self.updater.lastUpdateCheckDate()

    def set_update_interval(self, interval):
        if not self.enabled:
            return

        # disable check if interval == 0
        if interval == 0:
            self.updater.setAutomaticallyChecksForUpdates_(False)
            return

        # only update when value changes (because changing it triggers
        # a reset of the update cycle)
        if self.updater.updateCheckInterval() == interval:
            return
        self.updater.setAutomaticallyChecksForUpdates_(True)
        self.updater.setUpdateCheckInterval_(interval);

class UpdaterDelegate(NSObject):

    # relaunch Mail instead of the plugin
    def pathToRelaunchForUpdater_(self, updater):
        return NSBundle.mainBundle().bundlePath()

    def updater_didFinishLoadingAppcast_(self, updater, appcast):
        logger.debug("Updater finished loading appcast.")

    def updaterDidNotFindUpdate_(self, updater):
        logger.debug("Updater did not find update.")

    def updater_didFindValidUpdate_(self, updater, update):
        logger.debug("Updater found valid update.")

########NEW FILE########
__FILENAME__ = utils
import  objc, re, htmlentitydefs

# Method Swizzler: exchange an existing Objective-C method with a new
# implementation (akin to monkeypatching)
def swizzle(cls, SEL):
    if isinstance(cls, basestring):
        cls = objc.lookUpClass(cls)
    def decorator(func):
        oldIMP = cls.instanceMethodForSelector_(SEL)
        if oldIMP.isClassMethod:
            oldIMP = cls.methodForSelector_(SEL)
        def wrapper(self, *args, **kwargs):
            return func(self, oldIMP, *args, **kwargs)
        newMethod = objc.selector(wrapper, selector = oldIMP.selector, signature = oldIMP.signature, isClassMethod = oldIMP.isClassMethod)
        objc.classAddMethod(cls, SEL, newMethod)
        return wrapper
    return decorator

# string.Template-like string interpolation
class SimpleTemplate:

    def __init__(self, template):
        self.template = template

    def _substitute_param(self, param, params):
        tokens  = param.split('.')
        node    = params.get(tokens.pop(0))
        while node and tokens:
            node = getattr(node, tokens.pop(0), None)
        if node == None:
            return '${%s}' % param
        return unicode(node)

    def _substitute(self, params):
        expanded = self.template
        expanded = re.sub(r'\$\{(.*?)\}',  lambda p: self._substitute_param(p.group(1), params), expanded)
        return expanded

    def substitute(self, params):
        return self._substitute(params)

# unescape HTML-escaped string
def htmlunescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)

########NEW FILE########
__FILENAME__ = QuoteFix
from    AppKit          import NSBundle
from    Foundation      import NSLog
from    quotefix        import *
import  objc

class QuoteFix(objc.runtime.MVMailBundle):

    @classmethod
    def initialize(cls):
        # instantiate updater
        updater = Updater()

        # register ourselves
        objc.runtime.MVMailBundle.registerBundle()

        # extract plugin version from Info.plist
        bundle  = NSBundle.bundleWithIdentifier_('name.klep.mail.QuoteFix')
        version = bundle.infoDictionary().get('CFBundleVersion', '??')

        # initialize app
        app = App(version, updater)

        # initialize our posing classes with app instance
        DocumentEditor.registerQuoteFixApplication(app)
        MessageHeaders.registerQuoteFixApplication(app)
        MailApp.registerQuoteFixApplication(app)
        QuoteFixPreferencesController.registerQuoteFixApplication(app)
        CustomizedAttribution.registerQuoteFixApplication(app)

        # announce that we have loaded
        NSLog("QuoteFix Plugin (version %s) registered with Mail.app" % version)

########NEW FILE########
