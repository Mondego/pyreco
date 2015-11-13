__FILENAME__ = account
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import mailbox
import logging
import os
import glob

from alot.helper import call_cmd_async
from alot.helper import split_commandstring


class SendingMailFailed(RuntimeError):
    pass


class StoreMailError(Exception):
    pass


class Account(object):
    """
    Datastructure that represents an email account. It manages this account's
    settings, can send and store mails to maildirs (drafts/send).

    .. note::
        This is an abstract class that leaves :meth:`send_mail` unspecified.
        See :class:`SendmailAccount` for a subclass that uses a sendmail
        command to send out mails.
    """

    address = None
    """this accounts main email address"""
    aliases = []
    """list of alternative addresses"""
    realname = None
    """real name used to format from-headers"""
    gpg_key = None
    """gpg fingerprint for this account's private key"""
    signature = None
    """signature to append to outgoing mails"""
    signature_filename = None
    """filename of signature file in attachment"""
    signature_as_attachment = None
    """attach signature file instead of appending its content to body text"""
    abook = None
    """addressbook (:class:`addressbooks.AddressBook`)
       managing this accounts contacts"""

    def __init__(self, address=None, aliases=None, realname=None,
                 gpg_key=None, signature=None, signature_filename=None,
                 signature_as_attachment=False, sent_box=None,
                 sent_tags=['sent'], draft_box=None, draft_tags=['draft'],
                 abook=None, sign_by_default=False, **rest):
        self.address = address
        self.aliases = aliases
        self.realname = realname
        self.gpg_key = gpg_key
        self.signature = signature
        self.signature_filename = signature_filename
        self.signature_as_attachment = signature_as_attachment
        self.sign_by_default = sign_by_default
        self.sent_box = sent_box
        self.sent_tags = sent_tags
        self.draft_box = draft_box
        self.draft_tags = draft_tags
        self.abook = abook

    def get_addresses(self):
        """return all email addresses connected to this account, in order of
        their importance"""
        return [self.address] + self.aliases

    def store_mail(self, mbx, mail):
        """
        stores given mail in mailbox. If mailbox is maildir, set the S-flag and
        return path to newly added mail. Oherwise this will return `None`.

        :param mbx: mailbox to use
        :type mbx: :class:`mailbox.Mailbox`
        :param mail: the mail to store
        :type mail: :class:`email.message.Message` or str
        :returns: absolute path of mail-file for Maildir or None if mail was
                  successfully stored
        :rtype: str or None
        :raises: StoreMailError
        """
        if not isinstance(mbx, mailbox.Mailbox):
            logging.debug('Not a mailbox')
            return False

        mbx.lock()
        if isinstance(mbx, mailbox.Maildir):
            logging.debug('Maildir')
            msg = mailbox.MaildirMessage(mail)
            msg.set_flags('S')
        else:
            logging.debug('no Maildir')
            msg = mailbox.Message(mail)

        try:
            message_id = mbx.add(msg)
            mbx.flush()
            mbx.unlock()
            logging.debug('got mailbox msg id : %s' % message_id)
        except Exception as e:
            raise StoreMailError(e)

        path = None
        # add new Maildir message to index and add tags
        if isinstance(mbx, mailbox.Maildir):
            # this is a dirty hack to get the path to the newly added file
            # I wish the mailbox module were more helpful...
            plist = glob.glob1(os.path.join(mbx._path, 'new'),
                               message_id + '*')
            if plist:
                path = os.path.join(mbx._path, 'new', plist[0])
                logging.debug('path of saved msg: %s' % path)
        return path

    def store_sent_mail(self, mail):
        """
        stores mail (:class:`email.message.Message` or str) in send-store if
        :attr:`sent_box` is set.
        """
        if self.sent_box is not None:
            return self.store_mail(self.sent_box, mail)

    def store_draft_mail(self, mail):
        """
        stores mail (:class:`email.message.Message` or str) as draft if
        :attr:`draft_box` is set.
        """
        if self.draft_box is not None:
            return self.store_mail(self.draft_box, mail)

    def send_mail(self, mail):
        """
        sends given mail

        :param mail: the mail to send
        :type mail: :class:`email.message.Message` or string
        :returns: a `Deferred` that errs back with a class:`SendingMailFailed`,
                  containing a reason string if an error occured.
        """
        raise NotImplementedError


class SendmailAccount(Account):
    """:class:`Account` that pipes a message to a `sendmail` shell command for
    sending"""
    def __init__(self, cmd, **kwargs):
        """
        :param cmd: sendmail command to use for this account
        :type cmd: str
        """
        super(SendmailAccount, self).__init__(**kwargs)
        self.cmd = cmd

    def send_mail(self, mail):
        cmdlist = split_commandstring(self.cmd)

        def cb(out):
            logging.info('sent mail successfully')
            logging.info(out)

        def errb(failure):
            termobj = failure.value
            errmsg = '%s failed with code %s:\n%s' % \
                (self.cmd, termobj.exitCode, str(failure.value))
            logging.error(errmsg)
            logging.error(failure.getTraceback())
            logging.error(failure.value.stderr)
            raise SendingMailFailed(errmsg)

        d = call_cmd_async(cmdlist, stdin=mail)
        d.addCallback(cb)
        d.addErrback(errb)
        return d

########NEW FILE########
__FILENAME__ = addressbooks
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import re
import os

from alot.settings.utils import read_config
from helper import call_cmd
from alot.helper import split_commandstring


class AddressbookError(Exception):
    pass


class AddressBook(object):
    """can look up email addresses and realnames for contacts.

    .. note::

        This is an abstract class that leaves :meth:`get_contacts`
        unspecified. See :class:`AbookAddressBook` and
        :class:`MatchSdtoutAddressbook` for implementations.
    """
    def __init__(self, ignorecase=True):
        self.reflags = re.IGNORECASE if ignorecase else 0

    def get_contacts(self):
        """list all contacts tuples in this abook as (name, email) tuples"""
        return []

    def lookup(self, query=''):
        """looks up all contacts where name or address match query"""
        res = []
        query = '.*%s.*' % query
        for name, email in self.get_contacts():
            try:
                if re.match(query, name, self.reflags) or \
                        re.match(query, email, self.reflags):
                    res.append((name, email))
            except:
                pass
        return res


class AbookAddressBook(AddressBook):
    """:class:`AddressBook` that parses abook's config/database files"""
    def __init__(self, path='~/.abook/addressbook', **kwargs):
        """
        :param path: path to theme file
        :type path: str
        """
        AddressBook.__init__(self, **kwargs)
        DEFAULTSPATH = os.path.join(os.path.dirname(__file__), 'defaults')
        self._spec = os.path.join(DEFAULTSPATH, 'abook_contacts.spec')
        path = os.path.expanduser(path)
        self._config = read_config(path, self._spec)
        del(self._config['format'])

    def get_contacts(self):
        c = self._config
        res = []
        for id in c.sections:
            for email in c[id]['email']:
                if email:
                    res.append((c[id]['name'], email))
        return res


class MatchSdtoutAddressbook(AddressBook):
    """:class:`AddressBook` that parses a shell command's output for lookups"""

    def __init__(self, command, match=None, **kwargs):
        """
        :param command: lookup command
        :type command: str
        :param match: regular expression used to match contacts in `commands`
                      output to stdout. Must define subparts named "email" and
                      "name".  Defaults to
                      :regexp:`^(?P<email>[^@]+@[^\t]+)\t+(?P<name>[^\t]+)`.
        :type match: str
        """
        AddressBook.__init__(self, **kwargs)
        self.command = command
        if not match:
            self.match = '^(?P<email>[^@]+@[^\t]+)\t+(?P<name>[^\t]+)'
        else:
            self.match = match

    def get_contacts(self):
        return self.lookup('\'\'')

    def lookup(self, prefix):
        cmdlist = split_commandstring(self.command)
        resultstring, errmsg, retval = call_cmd(cmdlist + [prefix])
        if retval != 0:
            msg = 'abook command "%s" returned with ' % self.command
            msg += 'return code %d' % retval
            if errmsg:
                msg += ':\n%s' % errmsg
            raise AddressbookError(msg)

        if not resultstring:
            return []
        lines = resultstring.splitlines()
        res = []
        for l in lines:
            m = re.match(self.match, l, self.reflags)
            if m:
                info = m.groupdict()
                if 'email' and 'name' in info:
                    email = info['email'].strip()
                    name = info['name']
                    res.append((name, email))
        return res

########NEW FILE########
__FILENAME__ = buffers
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import urwid
import os
from notmuch import NotmuchError
import logging

from settings import settings
import commands
from walker import PipeWalker
from helper import shorten_author_string
from db.errors import NonexistantObjectError

from alot.widgets.globals import TagWidget
from alot.widgets.globals import HeadersList
from alot.widgets.globals import AttachmentWidget
from alot.widgets.bufferlist import BufferlineWidget
from alot.widgets.search import ThreadlineWidget
from alot.widgets.thread import ThreadTree
from alot.foreign.urwidtrees import ArrowTree, TreeBox, NestedTree


class Buffer(object):
    """Abstract base class for buffers."""

    modename = None  # mode identifier for subclasses

    def __init__(self, ui, widget):
        self.ui = ui
        self.body = widget

    def __str__(self):
        return '[%s]' % self.modename

    def render(self, size, focus=False):
        return self.body.render(size, focus)

    def selectable(self):
        return self.body.selectable()

    def rebuild(self):
        """tells the buffer to (re)construct its visible content."""
        pass

    def keypress(self, size, key):
        return self.body.keypress(size, key)

    def cleanup(self):
        """called before buffer is closed"""
        pass

    def get_info(self):
        """
        return dict of meta infos about this buffer.
        This can be requested to be displayed in the statusbar.
        """
        return {}


class BufferlistBuffer(Buffer):
    """lists all active buffers"""

    modename = 'bufferlist'

    def __init__(self, ui, filtfun=None):
        self.filtfun = filtfun
        self.ui = ui
        self.isinitialized = False
        self.rebuild()
        Buffer.__init__(self, ui, self.body)

    def index_of(self, b):
        """
        returns the index of :class:`Buffer` `b` in the global list of active
        buffers.
        """
        return self.ui.buffers.index(b)

    def rebuild(self):
        if self.isinitialized:
            focusposition = self.bufferlist.get_focus()[1]
        else:
            focusposition = 0
            self.isinitialized = True

        lines = list()
        displayedbuffers = filter(self.filtfun, self.ui.buffers)
        for (num, b) in enumerate(displayedbuffers):
            line = BufferlineWidget(b)
            if (num % 2) == 0:
                attr = settings.get_theming_attribute('bufferlist',
                                                      'line_even')
            else:
                attr = settings.get_theming_attribute('bufferlist', 'line_odd')
            focus_att = settings.get_theming_attribute('bufferlist',
                                                       'line_focus')
            buf = urwid.AttrMap(line, attr, focus_att)
            num = urwid.Text('%3d:' % self.index_of(b))
            lines.append(urwid.Columns([('fixed', 4, num), buf]))
        self.bufferlist = urwid.ListBox(urwid.SimpleListWalker(lines))
        num_buffers = len(displayedbuffers)
        if focusposition is not None and num_buffers > 0:
            self.bufferlist.set_focus(focusposition % num_buffers)
        self.body = self.bufferlist

    def get_selected_buffer(self):
        """returns currently selected :class:`Buffer` element from list"""
        (linewidget, pos) = self.bufferlist.get_focus()
        bufferlinewidget = linewidget.get_focus().original_widget
        return bufferlinewidget.get_buffer()

    def focus_first(self):
        self.body.set_focus(0)


class EnvelopeBuffer(Buffer):
    """message composition mode"""

    modename = 'envelope'

    def __init__(self, ui, envelope):
        self.ui = ui
        self.envelope = envelope
        self.all_headers = False
        self.rebuild()
        Buffer.__init__(self, ui, self.body)

    def __str__(self):
        to = self.envelope.get('To', fallback='unset')
        return '[envelope] to: %s' % (shorten_author_string(to, 400))

    def get_info(self):
        info = {}
        info['to'] = self.envelope.get('To', fallback='unset')
        return info

    def cleanup(self):
        if self.envelope.tmpfile:
            os.unlink(self.envelope.tmpfile.name)

    def rebuild(self):
        displayed_widgets = []
        hidden = settings.get('envelope_headers_blacklist')
        # build lines
        lines = []
        for (k, vlist) in self.envelope.headers.items():
            if (k not in hidden) or self.all_headers:
                for value in vlist:
                    lines.append((k, value))

        # sign/encrypt lines
        if self.envelope.sign:
            description = 'Yes'
            sign_key = self.envelope.sign_key
            if sign_key is not None and len(sign_key.subkeys) > 0:
                description += ', with key ' + sign_key.uids[0].uid
            lines.append(('GPG sign', description))

        if self.envelope.encrypt:
            description = 'Yes'
            encrypt_keys = self.envelope.encrypt_keys.values()
            if len(encrypt_keys) == 1:
                description += ', with key '
            elif len(encrypt_keys) > 1:
                description += ', with keys '
            first_key = True
            for key in encrypt_keys:
                if key is not None:
                    if first_key:
                        first_key = False
                    else:
                        description += ', '
                    if len(key.subkeys) > 0:
                        description += key.uids[0].uid
            lines.append(('GPG encrypt', description))

        # add header list widget iff header values exists
        if lines:
            key_att = settings.get_theming_attribute('envelope', 'header_key')
            value_att = settings.get_theming_attribute('envelope',
                                                       'header_value')
            gaps_att = settings.get_theming_attribute('envelope', 'header')
            self.header_wgt = HeadersList(lines, key_att, value_att, gaps_att)
            displayed_widgets.append(self.header_wgt)

        # display attachments
        lines = []
        for a in self.envelope.attachments:
            lines.append(AttachmentWidget(a, selectable=False))
        if lines:
            self.attachment_wgt = urwid.Pile(lines)
            displayed_widgets.append(self.attachment_wgt)

        self.body_wgt = urwid.Text(self.envelope.body)
        displayed_widgets.append(self.body_wgt)
        self.body = urwid.ListBox(displayed_widgets)

    def toggle_all_headers(self):
        """toggles visibility of all envelope headers"""
        self.all_headers = not self.all_headers
        self.rebuild()


class SearchBuffer(Buffer):
    """shows a result list of threads for a query"""

    modename = 'search'
    threads = []
    _REVERSE = {'oldest_first': 'newest_first',
                'newest_first': 'oldest_first'}

    def __init__(self, ui, initialquery='', sort_order=None):
        self.dbman = ui.dbman
        self.ui = ui
        self.querystring = initialquery
        default_order = settings.get('search_threads_sort_order')
        self.sort_order = sort_order or default_order
        self.result_count = 0
        self.isinitialized = False
        self.proc = None  # process that fills our pipe
        self.rebuild()
        Buffer.__init__(self, ui, self.body)

    def __str__(self):
        formatstring = '[search] for "%s" (%d message%s)'
        return formatstring % (self.querystring, self.result_count,
                               's' * (not (self.result_count == 1)))

    def get_info(self):
        info = {}
        info['querystring'] = self.querystring
        info['result_count'] = self.result_count
        info['result_count_positive'] = 's' * (not (self.result_count == 1))
        return info

    def cleanup(self):
        self.kill_filler_process()

    def kill_filler_process(self):
        """
        terminates the process that fills this buffers
        :class:`~alot.walker.PipeWalker`.
        """
        if self.proc:
            if self.proc.is_alive():
                self.proc.terminate()

    def rebuild(self, reverse=False):
        self.isinitialized = True
        self.reversed = reverse
        self.kill_filler_process()

        self.result_count = self.dbman.count_messages(self.querystring)
        if reverse:
            order = self._REVERSE[self.sort_order]
        else:
            order = self.sort_order

        try:
            self.pipe, self.proc = self.dbman.get_threads(self.querystring,
                                                          order)
        except NotmuchError:
            self.ui.notify('malformed query string: %s' % self.querystring,
                           'error')
            self.listbox = urwid.ListBox([])
            self.body = self.listbox
            return

        self.threadlist = PipeWalker(self.pipe, ThreadlineWidget,
                                     dbman=self.dbman,
                                     reverse=reverse)

        self.listbox = urwid.ListBox(self.threadlist)
        self.body = self.listbox

    def get_selected_threadline(self):
        """
        returns curently focussed :class:`alot.widgets.ThreadlineWidget`
        from the result list.
        """
        (threadlinewidget, size) = self.threadlist.get_focus()
        return threadlinewidget

    def get_selected_thread(self):
        """returns currently selected :class:`~alot.db.Thread`"""
        threadlinewidget = self.get_selected_threadline()
        thread = None
        if threadlinewidget:
            thread = threadlinewidget.get_thread()
        return thread

    def consume_pipe(self):
        while not self.threadlist.empty:
            self.threadlist._get_next_item()

    def focus_first(self):
        if not self.reversed:
            self.body.set_focus(0)
        else:
            self.rebuild(reverse=False)

    def focus_last(self):
        if self.reversed:
            self.body.set_focus(0)
        elif (self.result_count < 200) or \
                (self.sort_order not in self._REVERSE.keys()):
            self.consume_pipe()
            num_lines = len(self.threadlist.get_lines())
            self.body.set_focus(num_lines - 1)
        else:
            self.rebuild(reverse=True)



class ThreadBuffer(Buffer):
    """displays a thread as a tree of messages"""

    modename = 'thread'

    def __init__(self, ui, thread):
        """
        :param ui: main UI
        :type ui: :class:`~alot.ui.UI`
        :param thread: thread to display
        :type thread: :class:`~alot.db.Thread`
        """
        self.thread = thread
        self.message_count = thread.get_total_messages()

        # two semaphores for auto-removal of unread tag
        self._auto_unread_dont_touch_mids = set([])
        self._auto_unread_writing = False

        self.rebuild()
        Buffer.__init__(self, ui, self.body)

    def __str__(self):
        return '[thread] %s (%d message%s)' % (self.thread.get_subject(),
                                               self.message_count,
                                               's' * (self.message_count > 1))

    def get_info(self):
        info = {}
        info['subject'] = self.thread.get_subject()
        info['authors'] = self.thread.get_authors_string()
        info['tid'] = self.thread.get_thread_id()
        info['message_count'] = self.message_count
        return info

    def get_selected_thread(self):
        """returns the displayed :class:`~alot.db.Thread`"""
        return self.thread

    def rebuild(self):
        try:
            self.thread.refresh()
        except NonexistantObjectError:
            self.body = urwid.SolidFill()
            self.message_count = 0
            return

        self._tree = ThreadTree(self.thread)

        bars_att = settings.get_theming_attribute('thread', 'arrow_bars')
        heads_att = settings.get_theming_attribute('thread', 'arrow_heads')
        A = ArrowTree(self._tree,
                      indent=2,
                      childbar_offset=0,
                      arrow_tip_att=heads_att,
                      arrow_att=bars_att,
                      )
        self._nested_tree = NestedTree(A, interpret_covered=True)
        self.body = TreeBox(self._nested_tree)
        self.message_count = self.thread.get_total_messages()

    def render(self, size, focus=False):
        if settings.get('auto_remove_unread'):
            logging.debug('Tbuffer: auto remove unread tag from msg?')
            msg = self.get_selected_message()
            mid = msg.get_message_id()
            focus_pos = self.body.get_focus()[1]
            summary_pos = (self.body.get_focus()[1][0], (0,))
            cursor_on_non_summary = (focus_pos != summary_pos)
            if cursor_on_non_summary:
                if not mid in self._auto_unread_dont_touch_mids:
                    if 'unread' in msg.get_tags():
                        logging.debug('Tbuffer: removing unread')

                        def clear():
                            self._auto_unread_writing = False

                        self._auto_unread_dont_touch_mids.add(mid)
                        self._auto_unread_writing = True
                        msg.remove_tags(['unread'], afterwards=clear)
                        fcmd = commands.globals.FlushCommand(silent=True)
                        self.ui.apply_command(fcmd)
                    else:
                        logging.debug('Tbuffer: No, msg not unread')
                else:
                    logging.debug('Tbuffer: No, mid locked for autorm-unread')
            else:
                if not self._auto_unread_writing and \
                   mid in self._auto_unread_dont_touch_mids:
                    self._auto_unread_dont_touch_mids.remove(mid)
                logging.debug('Tbuffer: No, cursor on summary')
        return self.body.render(size, focus)

    def get_selected_mid(self):
        """returns Message ID of focussed message"""
        return self.body.get_focus()[1][0]

    def get_selected_message_position(self):
        """returns position of focussed message in the thread tree"""
        return self._sanitize_position((self.get_selected_mid(),))

    def get_selected_messagetree(self):
        """returns currently focussed :class:`MessageTree`"""
        return self._nested_tree[self.body.get_focus()[1][:1]]

    def get_selected_message(self):
        """returns focussed :class:`~alot.db.message.Message`"""
        return self.get_selected_messagetree()._message

    def get_messagetree_positions(self):
        """
        returns a Generator to walk through all positions of
        :class:`MessageTree` in the :class:`ThreadTree` of this buffer.
        """
        return [(pos,) for pos in self._tree.positions()]

    def messagetrees(self):
        """
        returns a Generator of all :class:`MessageTree` in the
        :class:`ThreadTree` of this buffer.
        """
        for pos in self._tree.positions():
            yield self._tree[pos]

    def refresh(self):
        """refresh and flushe caches of Thread tree"""
        self.body.refresh()

    # needed for ui.get_deep_focus..
    def get_focus(self):
        return self.body.get_focus()

    def set_focus(self, pos):
        logging.debug('setting focus to %s ' % str(pos))
        self.body.set_focus(pos)

    def focus_first(self):
        """set focus to first message of thread"""
        self.body.set_focus(self._nested_tree.root)

    def focus_last(self):
        self.body.set_focus(next(self._nested_tree.positions(reverse=True)))

    def _sanitize_position(self, pos):
        return self._nested_tree._sanitize_position(pos,
                                                    self._nested_tree._tree)

    def focus_selected_message(self):
        """focus the summary line of currently focussed message"""
        # move focus to summary (root of current MessageTree)
        self.set_focus(self.get_selected_message_position())

    def focus_parent(self):
        """move focus to parent of currently focussed message"""
        mid = self.get_selected_mid()
        newpos = self._tree.parent_position(mid)
        if newpos is not None:
            newpos = self._sanitize_position((newpos,))
            self.body.set_focus(newpos)

    def focus_first_reply(self):
        """move focus to first reply to currently focussed message"""
        mid = self.get_selected_mid()
        newpos = self._tree.first_child_position(mid)
        if newpos is not None:
            newpos = self._sanitize_position((newpos,))
            self.body.set_focus(newpos)

    def focus_last_reply(self):
        """move focus to last reply to currently focussed message"""
        mid = self.get_selected_mid()
        newpos = self._tree.last_child_position(mid)
        if newpos is not None:
            newpos = self._sanitize_position((newpos,))
            self.body.set_focus(newpos)

    def focus_next_sibling(self):
        """focus next sibling of currently focussed message in thread tree"""
        mid = self.get_selected_mid()
        newpos = self._tree.next_sibling_position(mid)
        if newpos is not None:
            newpos = self._sanitize_position((newpos,))
            self.body.set_focus(newpos)

    def focus_prev_sibling(self):
        """
        focus previous sibling of currently focussed message in thread tree
        """
        mid = self.get_selected_mid()
        localroot = self._sanitize_position((mid,))
        if localroot == self.get_focus()[1]:
            newpos = self._tree.prev_sibling_position(mid)
            if newpos is not None:
                newpos = self._sanitize_position((newpos,))
        else:
            newpos = localroot
        if newpos is not None:
            self.body.set_focus(newpos)

    def focus_next(self):
        """focus next message in depth first order"""
        mid = self.get_selected_mid()
        newpos = self._tree.next_position(mid)
        if newpos is not None:
            newpos = self._sanitize_position((newpos,))
            self.body.set_focus(newpos)

    def focus_prev(self):
        """focus previous message in depth first order"""
        mid = self.get_selected_mid()
        localroot = self._sanitize_position((mid,))
        if localroot == self.get_focus()[1]:
            newpos = self._tree.prev_position(mid)
            if newpos is not None:
                newpos = self._sanitize_position((newpos,))
        else:
            newpos = localroot
        if newpos is not None:
            self.body.set_focus(newpos)

    def focus_property(self, prop, direction):
        """does a walk in the given direction and focuses the
        first message tree that matches the given property"""
        newpos = self.get_selected_mid()
        newpos = direction(newpos)
        while newpos is not None:
            MT = self._tree[newpos]
            if prop(MT):
                newpos = self._sanitize_position((newpos,))
                self.body.set_focus(newpos)
                break
            newpos = direction(newpos)

    def focus_next_matching(self, querystring):
        """focus next matching message in depth first order"""
        self.focus_property(lambda x: x._message.matches(querystring),
                            self._tree.next_position)

    def focus_prev_matching(self, querystring):
        """focus previous matching message in depth first order"""
        self.focus_property(lambda x: x._message.matches(querystring),
                            self._tree.prev_position)

    def focus_next_unfolded(self):
        """focus next unfolded message in depth first order"""
        self.focus_property(lambda x: not x.is_collapsed(x.root),
                            self._tree.next_position)

    def focus_prev_unfolded(self):
        """focus previous unfolded message in depth first order"""
        self.focus_property(lambda x: not x.is_collapsed(x.root),
                            self._tree.prev_position)

    def expand(self, msgpos):
        """expand message at given position"""
        MT = self._tree[msgpos]
        MT.expand(MT.root)

    def messagetree_at_position(self, pos):
        """get :class:`MessageTree` for given position"""
        return self._tree[pos[0]]

    def expand_all(self):
        """expand all messages in thread"""
        for MT in self.messagetrees():
            MT.expand(MT.root)

    def collapse(self, msgpos):
        """collapse message at given position"""
        MT = self._tree[msgpos]
        MT.collapse(MT.root)
        self.focus_selected_message()

    def collapse_all(self):
        """collapse all messages in thread"""
        for MT in self.messagetrees():
            MT.collapse(MT.root)
        self.focus_selected_message()

    def unfold_matching(self, querystring, focus_first=True):
        """
        expand all messages that match a given querystring.

        :param querystring: query to match
        :type querystring: str
        :param focus_first: set the focus to the first matching message
        :type focus_first: bool
        """
        first = None
        for MT in self.messagetrees():
            msg = MT._message
            if msg.matches(querystring):
                MT.expand(MT.root)
                if first is None:
                    first = (self._tree.position_of_messagetree(MT), MT.root)
                    self.body.set_focus(first)
            else:
                MT.collapse(MT.root)
        self.body.refresh()


class TagListBuffer(Buffer):
    """lists all tagstrings present in the notmuch database"""

    modename = 'taglist'

    def __init__(self, ui, alltags=[], filtfun=None):
        self.filtfun = filtfun
        self.ui = ui
        self.tags = alltags
        self.isinitialized = False
        self.rebuild()
        Buffer.__init__(self, ui, self.body)

    def rebuild(self):
        if self.isinitialized:
            focusposition = self.taglist.get_focus()[1]
        else:
            focusposition = 0
            self.isinitialized = True

        lines = list()
        displayedtags = sorted(filter(self.filtfun, self.tags),
                               key=unicode.lower)
        for (num, b) in enumerate(displayedtags):
            if (num % 2) == 0:
                attr = settings.get_theming_attribute('taglist', 'line_even')
            else:
                attr = settings.get_theming_attribute('taglist', 'line_odd')
            focus_att = settings.get_theming_attribute('taglist', 'line_focus')

            tw = TagWidget(b, attr, focus_att)
            rows = [('fixed', tw.width(), tw)]
            if tw.hidden:
                rows.append(urwid.Text(b + ' [hidden]'))
            elif tw.translated is not b:
                rows.append(urwid.Text('(%s)' % b))
            line = urwid.Columns(rows, dividechars=1)
            line = urwid.AttrMap(line, attr, focus_att)
            lines.append(line)

        self.taglist = urwid.ListBox(urwid.SimpleListWalker(lines))
        self.body = self.taglist

        self.taglist.set_focus(focusposition % len(displayedtags))

    def focus_first(self):
        self.body.set_focus(0)

    def focus_last(self):
        allpos = self.taglist.body.positions(reverse=True)
        if allpos:
            lastpos = allpos[0]
            self.body.set_focus(lastpos)

    def get_selected_tag(self):
        """returns selected tagstring"""
        (cols, pos) = self.taglist.get_focus()
        tagwidget = cols.original_widget.get_focus()
        return tagwidget.get_tag()

########NEW FILE########
__FILENAME__ = bufferlist
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
from alot.commands import Command, registerCommand
from . import globals

MODE = 'bufferlist'


@registerCommand(MODE, 'open')
class BufferFocusCommand(Command):
    """focus selected buffer"""
    def apply(self, ui):
        selected = ui.current_buffer.get_selected_buffer()
        ui.buffer_focus(selected)


@registerCommand(MODE, 'close')
class BufferCloseCommand(Command):
    """close focussed buffer"""
    def apply(self, ui):
        bufferlist = ui.current_buffer
        selected = bufferlist.get_selected_buffer()
        d = ui.apply_command(globals.BufferCloseCommand(buffer=selected))

        def cb(ignoreme):
            if bufferlist is not selected:
                bufferlist.rebuild()
            ui.update()
        d.addCallback(cb)
        return d

########NEW FILE########
__FILENAME__ = envelope
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import argparse
import os
import re
import glob
import logging
import email
import tempfile
from twisted.internet.defer import inlineCallbacks
import datetime

from alot.account import SendingMailFailed, StoreMailError
from alot.errors import GPGProblem, GPGCode
from alot import buffers
from alot import commands
from alot import crypto
from alot.commands import Command, registerCommand
from alot.commands import globals
from alot.helper import string_decode
from alot.settings import settings
from alot.utils.booleanaction import BooleanAction
from alot.db.errors import DatabaseError


MODE = 'envelope'


@registerCommand(MODE, 'attach', arguments=[
    (['path'], {'help': 'file(s) to attach (accepts wildcads)'})])
class AttachCommand(Command):
    """attach files to the mail"""
    repeatable = True

    def __init__(self, path=None, **kwargs):
        """
        :param path: files to attach (globable string)
        :type path: str
        """
        Command.__init__(self, **kwargs)
        self.path = path

    def apply(self, ui):
        envelope = ui.current_buffer.envelope

        if self.path:  # TODO: not possible, otherwise argparse error before
            files = filter(os.path.isfile,
                           glob.glob(os.path.expanduser(self.path)))
            if not files:
                ui.notify('no matches, abort')
                return
        else:
            ui.notify('no files specified, abort')
            return

        logging.info("attaching: %s" % files)
        for path in files:
            envelope.attach(path)
        ui.current_buffer.rebuild()


@registerCommand(MODE, 'unattach', arguments=[
    (['hint'], {'nargs': '?', 'help': 'which attached file to remove'}),
])
class UnattachCommand(Command):
    """remove attachments from current envelope"""
    repeatable = True

    def __init__(self, hint=None, **kwargs):
        """
        :param hint: which attached file to remove
        :type hint: str
        """
        Command.__init__(self, **kwargs)
        self.hint = hint

    def apply(self, ui):
        envelope = ui.current_buffer.envelope

        if self.hint is not None:
            for a in envelope.attachments:
                if self.hint in a.get_filename():
                    envelope.attachments.remove(a)
        else:
            envelope.attachments = []
        ui.current_buffer.rebuild()


@registerCommand(MODE, 'refine', arguments=[
    (['key'], {'help': 'header to refine'})])
class RefineCommand(Command):
    """prompt to change the value of a header"""
    def __init__(self, key='', **kwargs):
        """
        :param key: key of the header to change
        :type key: str
        """
        Command.__init__(self, **kwargs)
        self.key = key

    def apply(self, ui):
        value = ui.current_buffer.envelope.get(self.key, '')
        cmdstring = 'set %s %s' % (self.key, value)
        ui.apply_command(globals.PromptCommand(cmdstring))


@registerCommand(MODE, 'save')
class SaveCommand(Command):
    """save draft"""
    def apply(self, ui):
        envelope = ui.current_buffer.envelope

        # determine account to use
        sname, saddr = email.Utils.parseaddr(envelope.get('From'))
        account = settings.get_account_by_address(saddr)
        if account is None:
            if not settings.get_accounts():
                ui.notify('no accounts set.', priority='error')
                return
            else:
                account = settings.get_accounts()[0]

        if account.draft_box is None:
            ui.notify('abort: account <%s> has no draft_box set.' % saddr,
                      priority='error')
            return

        mail = envelope.construct_mail()
        # store mail locally
        # add Date header
        mail['Date'] = email.Utils.formatdate(localtime=True)
        path = account.store_draft_mail(crypto.email_as_string(mail))

        msg = 'draft saved successfully'

        # add mail to index if maildir path available
        if path is not None:
            ui.notify(msg + ' to %s' % path)
            logging.debug('adding new mail to index')
            try:
                ui.dbman.add_message(path, account.draft_tags)
                ui.apply_command(globals.FlushCommand())
                ui.apply_command(commands.globals.BufferCloseCommand())
            except DatabaseError as e:
                logging.error(e.message)
                ui.notify('could not index message:\n%s' % e.message,
                          priority='error',
                          block=True)
        else:
            ui.apply_command(commands.globals.BufferCloseCommand())


@registerCommand(MODE, 'send')
class SendCommand(Command):
    """send mail"""
    def __init__(self, mail=None, envelope=None, **kwargs):
        """
        :param mail: email to send
        :type email: email.message.Message
        :param envelope: envelope to use to construct the outgoing mail. This
                         will be ignored in case the mail parameter is set.
        :type envelope: alot.db.envelope.envelope
        """
        Command.__init__(self, **kwargs)
        self.mail = mail
        self.envelope = envelope
        self.envelope_buffer = None

    @inlineCallbacks
    def apply(self, ui):
        if self.mail is None:
            if self.envelope is None:
                # needed to close later
                self.envelope_buffer = ui.current_buffer
                self.envelope = self.envelope_buffer.envelope

            # This is to warn the user before re-sending
            # an already sent message in case the envelope buffer
            # was not closed because it was the last remaining buffer.
            if self.envelope.sent_time:
                mod = self.envelope.modified_since_sent
                when = self.envelope.sent_time
                warning = 'A modified version of ' * mod
                warning += 'this message has been sent at %s.' % when
                warning += ' Do you want to resend?'
                if (yield ui.choice(warning, cancel='no',
                                    msg_position='left')) == 'no':
                    return

            # don't do anything if another SendCommand is in the middle of
            # sending the message and we were triggered accidentally
            if self.envelope.sending:
                msg = 'sending this message already!'
                logging.debug(msg)
                return

            clearme = ui.notify(u'constructing mail (GPG, attachments)\u2026',
                                timeout=-1)

            try:
                self.mail = self.envelope.construct_mail()
                self.mail['Date'] = email.Utils.formatdate(localtime=True)
                self.mail = crypto.email_as_string(self.mail)
            except GPGProblem, e:
                ui.clear_notify([clearme])
                ui.notify(e.message, priority='error')
                return

            ui.clear_notify([clearme])

        # determine account to use for sending
        msg = self.mail
        if not isinstance(msg, email.message.Message):
            msg = email.message_from_string(self.mail)
        sname, saddr = email.Utils.parseaddr(msg.get('From', ''))
        account = settings.get_account_by_address(saddr)
        if account is None:
            if not settings.get_accounts():
                ui.notify('no accounts set', priority='error')
                return
            else:
                account = settings.get_accounts()[0]

        # make sure self.mail is a string
        logging.debug(self.mail.__class__)
        if isinstance(self.mail, email.message.Message):
            self.mail = str(self.mail)

        # define callback
        def afterwards(returnvalue):
            initial_tags = []
            if self.envelope is not None:
                self.envelope.sending = False
                self.envelope.sent_time = datetime.datetime.now()
                initial_tags = self.envelope.tags
            logging.debug('mail sent successfully')
            ui.clear_notify([clearme])
            if self.envelope_buffer is not None:
                cmd = commands.globals.BufferCloseCommand(self.envelope_buffer)
                ui.apply_command(cmd)
            ui.notify('mail sent successfully')

            # store mail locally
            # This can raise StoreMailError
            path = account.store_sent_mail(self.mail)

            # add mail to index if maildir path available
            if path is not None:
                logging.debug('adding new mail to index')
                ui.dbman.add_message(path, account.sent_tags + initial_tags)
                ui.apply_command(globals.FlushCommand())

        # define errback
        def send_errb(failure):
            if self.envelope is not None:
                self.envelope.sending = False
            ui.clear_notify([clearme])
            failure.trap(SendingMailFailed)
            logging.error(failure.getTraceback())
            errmsg = 'failed to send: %s' % failure.value
            ui.notify(errmsg, priority='error', block=True)

        def store_errb(failure):
            failure.trap(StoreMailError)
            logging.error(failure.getTraceback())
            errmsg = 'could not store mail: %s' % failure.value
            ui.notify(errmsg, priority='error', block=True)

        # send out
        clearme = ui.notify('sending..', timeout=-1)
        if self.envelope is not None:
            self.envelope.sending = True
        d = account.send_mail(self.mail)
        d.addCallback(afterwards)
        d.addErrback(send_errb)
        d.addErrback(store_errb)


@registerCommand(MODE, 'edit', arguments=[
    (['--spawn'], {'action': BooleanAction, 'default': None,
                   'help': 'spawn editor in new terminal'}),
    (['--refocus'], {'action': BooleanAction, 'default': True,
                     'help': 'refocus envelope after editing'})])
class EditCommand(Command):
    """edit mail"""
    def __init__(self, envelope=None, spawn=None, refocus=True, **kwargs):
        """
        :param envelope: email to edit
        :type envelope: :class:`~alot.db.envelope.Envelope`
        :param spawn: force spawning of editor in a new terminal
        :type spawn: bool
        :param refocus: m
        """
        self.envelope = envelope
        self.openNew = (envelope is not None)
        self.force_spawn = spawn
        self.refocus = refocus
        self.edit_only_body = False
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        ebuffer = ui.current_buffer
        if not self.envelope:
            self.envelope = ui.current_buffer.envelope

        # determine editable headers
        edit_headers = set(settings.get('edit_headers_whitelist'))
        if '*' in edit_headers:
            edit_headers = set(self.envelope.headers.keys())
        blacklist = set(settings.get('edit_headers_blacklist'))
        if '*' in blacklist:
            blacklist = set(self.envelope.headers.keys())
        edit_headers = edit_headers - blacklist
        logging.info('editable headers: %s' % edit_headers)

        def openEnvelopeFromTmpfile():
            # This parses the input from the tempfile.
            # we do this ourselves here because we want to be able to
            # just type utf-8 encoded stuff into the tempfile and let alot
            # worry about encodings.

            # get input
            # tempfile will be removed on buffer cleanup
            f = open(self.envelope.tmpfile.name)
            enc = settings.get('editor_writes_encoding')
            template = string_decode(f.read(), enc)
            f.close()

            # call post-edit translate hook
            translate = settings.get_hook('post_edit_translate')
            if translate:
                template = translate(template, ui=ui, dbm=ui.dbman)
            self.envelope.parse_template(template,
                                         only_body=self.edit_only_body)
            if self.openNew:
                ui.buffer_open(buffers.EnvelopeBuffer(ui, self.envelope))
            else:
                ebuffer.envelope = self.envelope
                ebuffer.rebuild()

        # decode header
        headertext = u''
        for key in edit_headers:
            vlist = self.envelope.get_all(key)
            if not vlist:
                # ensure editable headers are present in template
                vlist = ['']
            else:
                # remove to be edited lines from envelope
                del self.envelope[key]

            for value in vlist:
                # newlines (with surrounding spaces) by spaces in values
                value = value.strip()
                value = re.sub('[ \t\r\f\v]*\n[ \t\r\f\v]*', ' ', value)
                headertext += '%s: %s\n' % (key, value)

        # determine editable content
        bodytext = self.envelope.body
        if headertext:
            content = '%s\n%s' % (headertext, bodytext)
            self.edit_only_body = False
        else:
            content = bodytext
            self.edit_only_body = True

        # call pre-edit translate hook
        translate = settings.get_hook('pre_edit_translate')
        if translate:
            content = translate(content, ui=ui, dbm=ui.dbman)

        # write stuff to tempfile
        old_tmpfile = None
        if self.envelope.tmpfile:
            old_tmpfile = self.envelope.tmpfile
        self.envelope.tmpfile = tempfile.NamedTemporaryFile(delete=False,
                                                            prefix='alot.',
                                                            suffix='.eml')
        self.envelope.tmpfile.write(content.encode('utf-8'))
        self.envelope.tmpfile.flush()
        self.envelope.tmpfile.close()
        if old_tmpfile:
            os.unlink(old_tmpfile.name)
        cmd = globals.EditCommand(self.envelope.tmpfile.name,
                                  on_success=openEnvelopeFromTmpfile,
                                  spawn=self.force_spawn,
                                  thread=self.force_spawn,
                                  refocus=self.refocus)
        ui.apply_command(cmd)


@registerCommand(MODE, 'set', arguments=[
    (['--append'], {'action': 'store_true', 'help': 'keep previous values'}),
    (['key'], {'help': 'header to refine'}),
    (['value'], {'nargs': '+', 'help': 'value'})])
class SetCommand(Command):
    """set header value"""
    def __init__(self, key, value, append=False, **kwargs):
        """
        :param key: key of the header to change
        :type key: str
        :param value: new value
        :type value: str
        """
        self.key = key
        self.value = ' '.join(value)
        self.reset = not append
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        envelope = ui.current_buffer.envelope
        if self.reset:
            if self.key in envelope:
                del(envelope[self.key])
        envelope.add(self.key, self.value)
        ui.current_buffer.rebuild()


@registerCommand(MODE, 'unset', arguments=[
    (['key'], {'help': 'header to refine'})])
class UnsetCommand(Command):
    """remove header field"""
    def __init__(self, key, **kwargs):
        """
        :param key: key of the header to remove
        :type key: str
        """
        self.key = key
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        del(ui.current_buffer.envelope[self.key])
        ui.current_buffer.rebuild()


@registerCommand(MODE, 'toggleheaders')
class ToggleHeaderCommand(Command):
    """toggle display of all headers"""
    repeatable = True

    def apply(self, ui):
        ui.current_buffer.toggle_all_headers()


@registerCommand(MODE, 'sign', forced={'action': 'sign'}, arguments=[
    (['keyid'], {'nargs': argparse.REMAINDER, 'help': 'which key id to use'})],
    help='mark mail to be signed before sending')
@registerCommand(MODE, 'unsign', forced={'action': 'unsign'},
                 help='mark mail not to be signed before sending')
@registerCommand(MODE, 'togglesign', forced={'action': 'toggle'}, arguments=[
    (['keyid'], {'nargs': argparse.REMAINDER, 'help': 'which key id to use'})],
    help='toggle sign status')
class SignCommand(Command):
    """toggle signing this email"""
    repeatable = True

    def __init__(self, action=None, keyid=None, **kwargs):
        """
        :param action: whether to sign/unsign/toggle
        :type action: str
        :param keyid: which key id to use
        :type keyid: str
        """
        self.action = action
        self.keyid = keyid
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        sign = None
        key = None
        envelope = ui.current_buffer.envelope
        # sign status
        if self.action == 'sign':
            sign = True
        elif self.action == 'unsign':
            sign = False
        elif self.action == 'toggle':
            sign = not envelope.sign
        envelope.sign = sign

        # try to find key if hint given as parameter
        if sign:
            if len(self.keyid) > 0:
                keyid = str(' '.join(self.keyid))
                try:
                    key = crypto.get_key(keyid, validate=True, sign=True)
                except GPGProblem, e:
                    envelope.sign = False
                    ui.notify(e.message, priority='error')
                    return
                envelope.sign_key = key

        # reload buffer
        ui.current_buffer.rebuild()


@registerCommand(MODE, 'encrypt', forced={'action': 'encrypt'}, arguments=[
    (['keyids'], {'nargs': argparse.REMAINDER,
                  'help': 'keyid of the key to encrypt with'})],
    help='request encryption of message before sendout')
@registerCommand(MODE, 'unencrypt', forced={'action': 'unencrypt'},
                 help='remove request to encrypt message before sending')
@registerCommand(MODE, 'toggleencrypt', forced={'action': 'toggleencrypt'},
                 arguments=[
                     (['keyids'], {'nargs': argparse.REMAINDER,
                      'help': 'keyid of the key to encrypt with'})],
                 help='toggle if message should be encrypted before sendout')
@registerCommand(MODE, 'rmencrypt', forced={'action': 'rmencrypt'},
                 arguments=[
                     (['keyids'], {'nargs': argparse.REMAINDER,
                      'help': 'keyid of the key to encrypt with'})],
                 help='do not encrypt to given recipient key')
class EncryptCommand(Command):
    def __init__(self, action=None, keyids=None, **kwargs):
        """
        :param action: wether to encrypt/unencrypt/toggleencrypt
        :type action: str
        :param keyid: the id of the key to encrypt
        :type keyid: str
        """

        self.encrypt_keys = keyids
        self.action = action
        Command.__init__(self, **kwargs)

    @inlineCallbacks
    def apply(self, ui):
        envelope = ui.current_buffer.envelope
        if self.action == 'rmencrypt':
            try:
                for keyid in self.encrypt_keys:
                    tmp_key = crypto.get_key(keyid)
                    del envelope.encrypt_keys[crypto.hash_key(tmp_key)]
            except GPGProblem as e:
                ui.notify(e.message, priority='error')
            if not envelope.encrypt_keys:
                envelope.encrypt = False
            ui.current_buffer.rebuild()
            return
        elif self.action == 'encrypt':
            encrypt = True
        elif self.action == 'unencrypt':
            encrypt = False
        elif self.action == 'toggleencrypt':
            encrypt = not envelope.encrypt
        envelope.encrypt = encrypt
        if encrypt:
            if not self.encrypt_keys:
                for recipient in envelope.headers['To'][0].split(','):
                    if not recipient:
                        continue
                    match = re.search("<(.*@.*)>", recipient)
                    if match:
                        recipient = match.group(0)
                    self.encrypt_keys.append(recipient)

            logging.debug("encryption keys: " + str(self.encrypt_keys))
            for keyid in self.encrypt_keys:
                try:
                    key = crypto.get_key(keyid, validate=True, encrypt=True)
                except GPGProblem as e:
                    if e.code == GPGCode.AMBIGUOUS_NAME:
                        possible_keys = crypto.list_keys(hint=keyid)
                        tmp_choices = [k.uids[0].uid for k in possible_keys]
                        choices = {str(len(tmp_choices) - x): tmp_choices[x]
                                   for x in range(0, len(tmp_choices))}
                        keyid = yield ui.choice("ambiguous keyid! Which " +
                                                "key do you want to use?",
                                                choices, cancel=None)
                        if keyid:
                            self.encrypt_keys.append(keyid)
                        continue
                    else:
                        ui.notify(e.message, priority='error')
                        continue
                envelope.encrypt_keys[crypto.hash_key(key)] = key
            if not envelope.encrypt_keys:
                envelope.encrypt = False
        # reload buffer
        ui.current_buffer.rebuild()

########NEW FILE########
__FILENAME__ = globals
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import os
import code
from twisted.internet import threads
from twisted.internet import defer
import subprocess
import email
import urwid
from twisted.internet.defer import inlineCallbacks
import logging
import argparse
import glob
from StringIO import StringIO

from alot.commands import Command, registerCommand
from alot.completion import CommandLineCompleter
from alot.commands import CommandParseError
from alot.commands import commandfactory
from alot.commands import CommandCanceled
from alot import buffers
from alot.widgets.utils import DialogBox
from alot import helper
from alot.db.errors import DatabaseLockedError
from alot.completion import ContactsCompleter
from alot.completion import AccountCompleter
from alot.completion import TagsCompleter
from alot.db.envelope import Envelope
from alot import commands
from alot.settings import settings
from alot.helper import split_commandstring, split_commandline
from alot.helper import mailto_to_envelope
from alot.utils.booleanaction import BooleanAction

MODE = 'global'


@registerCommand(MODE, 'exit')
class ExitCommand(Command):

    """shut down cleanly"""
    @inlineCallbacks
    def apply(self, ui):
        msg = 'index not fully synced. ' if ui.db_was_locked else ''
        if settings.get('bug_on_exit') or ui.db_was_locked:
            msg += 'really quit?'
            if (yield ui.choice(msg, select='yes', cancel='no',
                                msg_position='left')) == 'no':
                return
        for b in ui.buffers:
            b.cleanup()
        ui.exit()


@registerCommand(MODE, 'search', usage='search query', arguments=[
    (['--sort'], {'help': 'sort order', 'choices': [
                  'oldest_first', 'newest_first', 'message_id', 'unsorted']}),
    (['query'], {'nargs': argparse.REMAINDER, 'help': 'search string'})])
class SearchCommand(Command):

    """open a new search buffer"""
    repeatable = True

    def __init__(self, query, sort=None, **kwargs):
        """
        :param query: notmuch querystring
        :type query: str
        :param sort: how to order results. Must be one of
                     'oldest_first', 'newest_first', 'message_id' or
                     'unsorted'.
        :type sort: str
        """
        self.query = ' '.join(query)
        self.order = sort
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        if self.query:
            open_searches = ui.get_buffers_of_type(buffers.SearchBuffer)
            to_be_focused = None
            for sb in open_searches:
                if sb.querystring == self.query:
                    to_be_focused = sb
            if to_be_focused:
                if ui.current_buffer != to_be_focused:
                    ui.buffer_focus(to_be_focused)
                else:
                    # refresh an already displayed search
                    ui.current_buffer.rebuild()
                    ui.update()
            else:
                ui.buffer_open(buffers.SearchBuffer(ui, self.query,
                                                    sort_order=self.order))
        else:
            ui.notify('empty query string')


@registerCommand(MODE, 'prompt', arguments=[
    (['startwith'], {'nargs': '?', 'default': '', 'help': 'initial content'})])
class PromptCommand(Command):

    """prompts for commandline and interprets it upon select"""
    def __init__(self, startwith='', **kwargs):
        """
        :param startwith: initial content of the prompt widget
        :type startwith: str
        """
        self.startwith = startwith
        Command.__init__(self, **kwargs)

    @inlineCallbacks
    def apply(self, ui):
        logging.info('open command shell')
        mode = ui.mode or 'global'
        cmpl = CommandLineCompleter(ui.dbman, mode, ui.current_buffer)
        cmdline = yield ui.prompt('',
                                  text=self.startwith,
                                  completer=cmpl,
                                  history=ui.commandprompthistory,
                                  )
        logging.debug('CMDLINE: %s' % cmdline)

        # interpret and apply commandline
        if cmdline:
            # save into prompt history
            ui.commandprompthistory.append(cmdline)
            ui.apply_commandline(cmdline)
        else:
            raise CommandCanceled()


@registerCommand(MODE, 'refresh')
class RefreshCommand(Command):

    """refresh the current buffer"""
    repeatable = True

    def apply(self, ui):
        ui.current_buffer.rebuild()
        ui.update()


@registerCommand(MODE, 'shellescape', arguments=[
    (['--spawn'], {'action': BooleanAction, 'default': None,
                   'help': 'run in terminal window'}),
    (['--thread'], {'action': BooleanAction, 'default': None,
                    'help': 'run in separate thread'}),
    (['--refocus'], {'action': BooleanAction, 'help': 'refocus current buffer \
                     after command has finished'}),
    (['cmd'], {'help': 'command line to execute'})],
    forced={'shell': True},
)
class ExternalCommand(Command):

    """run external command"""
    repeatable = True

    def __init__(self, cmd, stdin=None, shell=False, spawn=False,
                 refocus=True, thread=False, on_success=None, **kwargs):
        """
        :param cmd: the command to call
        :type cmd: list or str
        :param stdin: input to pipe to the process
        :type stdin: file or str
        :param spawn: run command in a new terminal
        :type spawn: bool
        :param shell: let shell interpret command string
        :type shell: bool
        :param thread: run asynchronously, don't block alot
        :type thread: bool
        :param refocus: refocus calling buffer after cmd termination
        :type refocus: bool
        :param on_success: code to execute after command successfully exited
        :type on_success: callable
        """
        logging.debug({'spawn': spawn})
        # make sure cmd is a list of str
        if isinstance(cmd, unicode):
            # convert cmdstring to list: in case shell==True,
            # Popen passes only the first item in the list to $SHELL
            cmd = [cmd] if shell else split_commandstring(cmd)

        # determine complete command list to pass
        touchhook = settings.get_hook('touch_external_cmdlist')
        # filter cmd, shell and thread through hook if defined
        if touchhook is not None:
            logging.debug('calling hook: touch_external_cmdlist')
            res = touchhook(cmd, shell=shell, spawn=spawn, thread=thread)
            logging.debug('got: %s' % res)
            cmd, shell, self.in_thread = res
        # otherwise if spawn requested and X11 is running
        elif spawn:
            if 'DISPLAY' in os.environ:
                term_cmd = settings.get('terminal_cmd', '')
                logging.info('spawn in terminal: %s' % term_cmd)
                termcmdlist = split_commandstring(term_cmd)
                cmd = termcmdlist + cmd
            else:
                thread = False

        self.cmdlist = cmd
        self.stdin = stdin
        self.shell = shell
        self.refocus = refocus
        self.in_thread = thread
        self.on_success = on_success
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        logging.debug('cmdlist: %s' % self.cmdlist)
        callerbuffer = ui.current_buffer

        # set standard input for subcommand
        stdin = None
        if self.stdin is not None:
            # wrap strings in StrinIO so that they behaves like a file
            if isinstance(self.stdin, unicode):
                stdin = StringIO(self.stdin)
            else:
                stdin = self.stdin

        def afterwards(data):
            if data == 'success':
                if callable(self.on_success):
                    self.on_success()
            else:
                ui.notify(data, priority='error')
            if self.refocus and callerbuffer in ui.buffers:
                logging.info('refocussing')
                ui.buffer_focus(callerbuffer)

        logging.info('calling external command: %s' % self.cmdlist)

        def thread_code(*args):
            try:
                if stdin is None:
                    proc = subprocess.Popen(self.cmdlist, shell=self.shell,
                                            stderr=subprocess.PIPE)
                    ret = proc.wait()
                    err = proc.stderr.read()
                else:
                    proc = subprocess.Popen(self.cmdlist, shell=self.shell,
                                            stdin=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
                    out, err = proc.communicate(stdin.read())
                    ret = proc.wait()
                if ret == 0:
                    return 'success'
                else:
                    return err.strip()
            except OSError as e:
                return str(e)

        if self.in_thread:
            d = threads.deferToThread(thread_code)
            d.addCallback(afterwards)
        else:
            ui.mainloop.screen.stop()
            ret = thread_code()
            ui.mainloop.screen.start()

            # make sure urwid renders its canvas at the correct size
            ui.mainloop.screen_size = None
            ui.mainloop.draw_screen()

            afterwards(ret)


#@registerCommand(MODE, 'edit', arguments=[
# (['--nospawn'], {'action': 'store_true', 'help':'spawn '}), #todo
#    (['path'], {'help':'file to edit'})]
#]
#)
class EditCommand(ExternalCommand):

    """edit a file"""
    def __init__(self, path, spawn=None, thread=None, **kwargs):
        """
        :param path: path to the file to be edited
        :type path: str
        :param spawn: force running edtor in a new terminal
        :type spawn: bool
        :param thread: run asynchronously, don't block alot
        :type thread: bool
        """
        self.spawn = spawn
        if spawn is None:
            self.spawn = settings.get('editor_spawn')
        self.thread = thread
        if thread is None:
            self.thread = settings.get('editor_in_thread')

        editor_cmdstring = None
        if os.path.isfile('/usr/bin/editor'):
            editor_cmdstring = '/usr/bin/editor'
        editor_cmdstring = os.environ.get('EDITOR', editor_cmdstring)
        editor_cmdstring = settings.get('editor_cmd') or editor_cmdstring
        logging.debug('using editor_cmd: %s' % editor_cmdstring)

        self.cmdlist = None
        if '%s' in editor_cmdstring:
            cmdstring = editor_cmdstring.replace('%s',
                                                 helper.shell_quote(path))
            self.cmdlist = split_commandstring(cmdstring)
        else:
            self.cmdlist = split_commandstring(editor_cmdstring) + [path]

        logging.debug({'spawn: ': self.spawn, 'in_thread': self.thread})
        ExternalCommand.__init__(self, self.cmdlist,
                                 spawn=self.spawn, thread=self.thread,
                                 **kwargs)

    def apply(self, ui):
        if self.cmdlist is None:
            ui.notify('no editor set', priority='error')
        else:
            return ExternalCommand.apply(self, ui)


@registerCommand(MODE, 'pyshell')
class PythonShellCommand(Command):

    """open an interactive python shell for introspection"""
    repeatable = True

    def apply(self, ui):
        ui.mainloop.screen.stop()
        code.interact(local=locals())
        ui.mainloop.screen.start()


@registerCommand(MODE, 'repeat')
class RepeatCommand(Command):

    """Repeats the command executed last time"""
    def __init__(self, **kwargs):
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        if ui.last_commandline is not None:
            ui.apply_commandline(ui.last_commandline)
        else:
            ui.notify('no last command')


@registerCommand(MODE, 'call', arguments=[
    (['command'], {'help': 'python command string to call'})])
class CallCommand(Command):

    """ Executes python code """
    repeatable = True

    def __init__(self, command, **kwargs):
        """
        :param command: python command string to call
        :type command: str
        """
        Command.__init__(self, **kwargs)
        self.command = command

    def apply(self, ui):
        try:
            hooks = settings.hooks
            env = {'ui': ui, 'settings': settings}
            for k, v in env.items():
                if k not in hooks.__dict__:
                    hooks.__dict__[k] = v

            exec(self.command)
        except Exception as e:
            logging.exception(e)
            msg = 'an error occurred during execution of "%s":\n%s'
            ui.notify(msg % (self.command, e), priority='error')


@registerCommand(MODE, 'bclose', arguments=[
    (['--redraw'], {'action': BooleanAction, 'help': 'redraw current buffer \
                     after command has finished'}),
    (['--force'], {'action': 'store_true',
                   'help': 'never ask for confirmation'})])
class BufferCloseCommand(Command):

    """close a buffer"""
    repeatable = True

    def __init__(self, buffer=None, force=False, redraw=True, **kwargs):
        """
        :param buffer: the buffer to close or None for current
        :type buffer: `alot.buffers.Buffer`
        :param force: force buffer close
        :type force: bool
        """
        self.buffer = buffer
        self.force = force
        self.redraw = redraw
        Command.__init__(self, **kwargs)

    @inlineCallbacks
    def apply(self, ui):
        if self.buffer is None:
            self.buffer = ui.current_buffer

        if (isinstance(self.buffer, buffers.EnvelopeBuffer) and
                not self.buffer.envelope.sent_time):
            if (not self.force and (yield ui.choice('close without sending?',
                                                    select='yes', cancel='no',
                                                    msg_position='left')) ==
                    'no'):
                raise CommandCanceled()

        if len(ui.buffers) == 1:
            if settings.get('quit_on_last_bclose'):
                logging.info('closing the last buffer, exiting')
                ui.apply_command(ExitCommand())
            else:
                logging.info('not closing last remaining buffer as '
                             'global.quit_on_last_bclose is set to False')
        else:
            ui.buffer_close(self.buffer, self.redraw)


@registerCommand(MODE, 'bprevious', forced={'offset': -1},
                 help='focus previous buffer')
@registerCommand(MODE, 'bnext', forced={'offset': +1},
                 help='focus next buffer')
@registerCommand(MODE, 'buffer', arguments=[
    (['index'], {'type': int, 'help': 'buffer index to focus'}), ],
    help='focus buffer with given index')
class BufferFocusCommand(Command):

    """focus a :class:`~alot.buffers.Buffer`"""
    repeatable = True

    def __init__(self, buffer=None, index=None, offset=0, **kwargs):
        """
        :param buffer: the buffer to focus or None
        :type buffer: `alot.buffers.Buffer`
        :param index: index (in bufferlist) of the buffer to focus.
        :type index: int
        :param offset: position of the buffer to focus relative to the
                       currently focussed one. This is used only if `buffer`
                       is set to `None`
        :type offset: int
        """
        self.buffer = buffer
        self.index = index
        self.offset = offset
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        if self.buffer is None:
            if self.index is not None:
                try:
                    self.buffer = ui.buffers[self.index]
                except IndexError:
                    ui.notify('no buffer exists at index %d' % self.index)
                    return
            else:
                self.index = ui.buffers.index(ui.current_buffer)
            num = len(ui.buffers)
            self.buffer = ui.buffers[(self.index + self.offset) % num]
        ui.buffer_focus(self.buffer)


@registerCommand(MODE, 'bufferlist')
class OpenBufferlistCommand(Command):

    """open a list of active buffers"""
    def __init__(self, filtfun=None, **kwargs):
        """
        :param filtfun: filter to apply to displayed list
        :type filtfun: callable (str->bool)
        """
        self.filtfun = filtfun
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        blists = ui.get_buffers_of_type(buffers.BufferlistBuffer)
        if blists:
            ui.buffer_focus(blists[0])
        else:
            bl = buffers.BufferlistBuffer(ui, self.filtfun)
            ui.buffer_open(bl)


@registerCommand(MODE, 'taglist', arguments=[
    (['--tags'], {'nargs': '+', 'help': 'tags to display'}),
])
class TagListCommand(Command):

    """opens taglist buffer"""
    def __init__(self, filtfun=None, tags=None, **kwargs):
        """
        :param filtfun: filter to apply to displayed list
        :type filtfun: callable (str->bool)
        """
        self.filtfun = filtfun
        self.tags = tags
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        tags = self.tags or ui.dbman.get_all_tags()
        blists = ui.get_buffers_of_type(buffers.TagListBuffer)
        if blists:
            buf = blists[0]
            buf.tags = tags
            buf.rebuild()
            ui.buffer_focus(buf)
        else:
            ui.buffer_open(buffers.TagListBuffer(ui, tags, self.filtfun))


@registerCommand(MODE, 'flush')
class FlushCommand(Command):

    """flush write operations or retry until committed"""
    repeatable = True

    def __init__(self, callback=None, silent=False, **kwargs):
        """
        :param callback: function to call after successful writeout
        :type callback: callable
        """
        Command.__init__(self, **kwargs)
        self.callback = callback
        self.silent = silent

    def apply(self, ui):
        try:
            ui.dbman.flush()
            if callable(self.callback):
                self.callback()
            logging.debug('flush complete')
            if ui.db_was_locked:
                if not self.silent:
                    ui.notify('changes flushed')
                ui.db_was_locked = False
            ui.update()

        except DatabaseLockedError:
            timeout = settings.get('flush_retry_timeout')

            def f(*args):
                self.apply(ui)
            ui.mainloop.set_alarm_in(timeout, f)
            if not ui.db_was_locked:
                if not self.silent:
                    ui.notify(
                        'index locked, will try again in %d secs' % timeout)
                ui.db_was_locked = True
            ui.update()
            return


# TODO: choices
@registerCommand(MODE, 'help', arguments=[
    (['commandname'], {'help': 'command or \'bindings\''})])
class HelpCommand(Command):

    """
    display help for a command. Use \'bindings\' to
    display all keybings interpreted in current mode.'
    """
    def __init__(self, commandname='', **kwargs):
        """
        :param commandname: command to document
        :type commandname: str
        """
        Command.__init__(self, **kwargs)
        self.commandname = commandname

    def apply(self, ui):
        logging.debug('HELP')
        if self.commandname == 'bindings':
            text_att = settings.get_theming_attribute('help', 'text')
            title_att = settings.get_theming_attribute('help', 'title')
            section_att = settings.get_theming_attribute('help', 'section')
            # get mappings
            if ui.mode in settings._bindings:
                modemaps = dict(settings._bindings[ui.mode].items())
            else:
                modemaps = {}
            is_scalar = lambda k_v: k_v[0] in settings._bindings.scalars
            globalmaps = dict(filter(is_scalar, settings._bindings.items()))

            # build table
            maxkeylength = len(max((modemaps).keys() + globalmaps.keys(),
                                   key=len))
            keycolumnwidth = maxkeylength + 2

            linewidgets = []
            # mode specific maps
            if modemaps:
                txt = (section_att, '\n%s-mode specific maps' % ui.mode)
                linewidgets.append(urwid.Text(txt))
                for (k, v) in modemaps.items():
                    line = urwid.Columns([('fixed', keycolumnwidth,
                                           urwid.Text((text_att, k))),
                                          urwid.Text((text_att, v))])
                    linewidgets.append(line)

            # global maps
            linewidgets.append(urwid.Text((section_att, '\nglobal maps')))
            for (k, v) in globalmaps.items():
                if k not in modemaps:
                    line = urwid.Columns(
                        [('fixed', keycolumnwidth, urwid.Text((text_att, k))),
                         urwid.Text((text_att, v))])
                    linewidgets.append(line)

            body = urwid.ListBox(linewidgets)
            titletext = 'Bindings Help (escape cancels)'

            box = DialogBox(body, titletext,
                            bodyattr=text_att,
                            titleattr=title_att)

            # put promptwidget as overlay on main widget
            overlay = urwid.Overlay(box, ui.root_widget, 'center',
                                    ('relative', 70), 'middle',
                                    ('relative', 70))
            ui.show_as_root_until_keypress(overlay, 'esc')
        else:
            logging.debug('HELP %s' % self.commandname)
            parser = commands.lookup_parser(self.commandname, ui.mode)
            if parser:
                ui.notify(parser.format_help(), block=True)
            else:
                ui.notify('command not known: %s' % self.commandname,
                          priority='error')


@registerCommand(MODE, 'compose', arguments=[
    (['--sender'], {'nargs': '?', 'help': 'sender'}),
    (['--template'], {'nargs': '?',
                      'help': 'path to a template message file'}),
    (['--subject'], {'nargs': '?', 'help': 'subject line'}),
    (['--to'], {'nargs': '+', 'help': 'recipients'}),
    (['--cc'], {'nargs': '+', 'help': 'copy to'}),
    (['--bcc'], {'nargs': '+', 'help': 'blind copy to'}),
    (['--attach'], {'nargs': '+', 'help': 'attach files'}),
    (['--omit_signature'], {'action': 'store_true',
                            'help': 'do not add signature'}),
    (['--spawn'], {'action': BooleanAction, 'default': None,
                   'help': 'spawn editor in new terminal'}),
    (['rest'], {'nargs': '*'}),
])
class ComposeCommand(Command):

    """compose a new email"""
    def __init__(self, envelope=None, headers={}, template=None,
                 sender=u'', subject=u'', to=[], cc=[], bcc=[], attach=None,
                 omit_signature=False, spawn=None, rest=[], **kwargs):
        """
        :param envelope: use existing envelope
        :type envelope: :class:`~alot.db.envelope.Envelope`
        :param headers: forced header values
        :type headers: dict (str->str)
        :param template: name of template to parse into the envelope after
                         creation. This should be the name of a file in your
                         template_dir
        :type template: str
        :param sender: From-header value
        :type sender: str
        :param subject: Subject-header value
        :type subject: str
        :param to: To-header value
        :type to: str
        :param cc: Cc-header value
        :type cc: str
        :param bcc: Bcc-header value
        :type bcc: str
        :param attach: Path to files to be attached (globable)
        :type attach: str
        :param omit_signature: do not attach/append signature
        :type omit_signature: bool
        :param spawn: force spawning of editor in a new terminal
        :type spawn: bool
        :param rest: remaining parameters. These can start with
                     'mailto' in which case it is interpreted sa mailto string.
                     Otherwise it will be interpreted as recipients (to) header
        :type rest: list(str)
        """

        Command.__init__(self, **kwargs)

        self.envelope = envelope
        self.template = template
        self.headers = headers
        self.sender = sender
        self.subject = subject
        self.to = to
        self.cc = cc
        self.bcc = bcc
        self.attach = attach
        self.omit_signature = omit_signature
        self.force_spawn = spawn
        self.rest = ' '.join(rest)

    @inlineCallbacks
    def apply(self, ui):
        if self.envelope is None:
            if self.rest:
                if self.rest.startswith('mailto'):
                    self.envelope = mailto_to_envelope(self.rest)
                else:
                    self.envelope = Envelope()
                    self.envelope.add('To', self.rest)
            else:
                self.envelope = Envelope()
        if self.template is not None:
            # get location of tempsdir, containing msg templates
            tempdir = settings.get('template_dir')
            tempdir = os.path.expanduser(tempdir)
            if not tempdir:
                xdgdir = os.environ.get('XDG_CONFIG_HOME',
                                        os.path.expanduser('~/.config'))
                tempdir = os.path.join(xdgdir, 'alot', 'templates')

            path = os.path.expanduser(self.template)
            if not os.path.dirname(path):  # use tempsdir
                if not os.path.isdir(tempdir):
                    ui.notify('no templates directory: %s' % tempdir,
                              priority='error')
                    return
                path = os.path.join(tempdir, path)

            if not os.path.isfile(path):
                ui.notify('could not find template: %s' % path,
                          priority='error')
                return
            try:
                self.envelope.parse_template(open(path).read())
            except Exception as e:
                ui.notify(str(e), priority='error')
                return

        # set forced headers
        for key, value in self.headers.items():
            self.envelope.add(key, value)

        # set forced headers for separate parameters
        if self.sender:
            self.envelope.add('From', self.sender)
        if self.subject:
            self.envelope.add('Subject', self.subject)
        if self.to:
            self.envelope.add('To', ','.join(self.to))
        if self.cc:
            self.envelope.add('Cc', ','.join(self.cc))
        if self.bcc:
            self.envelope.add('Bcc', ','.join(self.bcc))

        # get missing From header
        if not 'From' in self.envelope.headers:
            accounts = settings.get_accounts()
            if len(accounts) == 1:
                a = accounts[0]
                fromstring = "%s <%s>" % (a.realname, a.address)
                self.envelope.add('From', fromstring)
            else:
                cmpl = AccountCompleter()
                fromaddress = yield ui.prompt('From', completer=cmpl,
                                              tab=1)
                if fromaddress is None:
                    raise CommandCanceled()

                self.envelope.add('From', fromaddress)

        # add signature
        if not self.omit_signature:
            name, addr = email.Utils.parseaddr(self.envelope['From'])
            account = settings.get_account_by_address(addr)
            if account is not None:
                if account.signature:
                    logging.debug('has signature')
                    sig = os.path.expanduser(account.signature)
                    if os.path.isfile(sig):
                        logging.debug('is file')
                        if account.signature_as_attachment:
                            name = account.signature_filename or None
                            self.envelope.attach(sig, filename=name)
                            logging.debug('attached')
                        else:
                            sigcontent = open(sig).read()
                            enc = helper.guess_encoding(sigcontent)
                            mimetype = helper.guess_mimetype(sigcontent)
                            if mimetype.startswith('text'):
                                sigcontent = helper.string_decode(sigcontent,
                                                                  enc)
                                self.envelope.body += '\n' + sigcontent
                    else:
                        ui.notify('could not locate signature: %s' % sig,
                                  priority='error')
                        if (yield ui.choice('send without signature?', 'yes',
                                            'no')) == 'no':
                            return

        # Figure out whether we should GPG sign messages by default
        # and look up key if so
        sender = self.envelope.get('From')
        name, addr = email.Utils.parseaddr(sender)
        account = settings.get_account_by_address(addr)
        if account:
            self.envelope.sign = account.sign_by_default
            self.envelope.sign_key = account.gpg_key

        # get missing To header
        if 'To' not in self.envelope.headers:
            allbooks = not settings.get('complete_matching_abook_only')
            logging.debug(allbooks)
            if account is not None:
                abooks = settings.get_addressbooks(order=[account],
                                                   append_remaining=allbooks)
                logging.debug(abooks)
                completer = ContactsCompleter(abooks)
            else:
                completer = None
            to = yield ui.prompt('To',
                                 completer=completer)
            if to is None:
                raise CommandCanceled()

            self.envelope.add('To', to.strip(' \t\n,'))

        if settings.get('ask_subject') and \
                not 'Subject' in self.envelope.headers:
            subject = yield ui.prompt('Subject')
            logging.debug('SUBJECT: "%s"' % subject)
            if subject is None:
                raise CommandCanceled()

            self.envelope.add('Subject', subject)

        if settings.get('compose_ask_tags'):
            comp = TagsCompleter(ui.dbman)
            tagsstring = yield ui.prompt('Tags', completer=comp)
            tags = filter(lambda x: x, tagsstring.split(','))
            if tags is None:
                raise CommandCanceled()

            self.envelope.tags = tags

        if self.attach:
            for gpath in self.attach:
                for a in glob.glob(gpath):
                    self.envelope.attach(a)
                    logging.debug('attaching: ' + a)

        cmd = commands.envelope.EditCommand(envelope=self.envelope,
                                            spawn=self.force_spawn,
                                            refocus=False)
        ui.apply_command(cmd)


@registerCommand(MODE, 'move', help='move focus in current buffer',
                 arguments=[(['movement'], {
                             'nargs': argparse.REMAINDER,
                             'help': 'up, down, [half]page up, '
                                     '[half]page down, first'})])
class MoveCommand(Command):

    """move in widget"""
    def __init__(self, movement=None, **kwargs):
        if movement is None:
            self.movement = ''
        else:
            self.movement = ' '.join(movement)
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        if self.movement in ['up', 'down', 'page up', 'page down']:
            ui.mainloop.process_input([self.movement])
        elif self.movement in ['halfpage down', 'halfpage up']:
            ui.mainloop.process_input(
                ui.mainloop.screen_size[1] / 2 * [self.movement.split()[-1]])
        elif self.movement == 'first':
            if hasattr(ui.current_buffer, "focus_first"):
                ui.current_buffer.focus_first()
                ui.update()
        elif self.movement == 'last':
            if hasattr(ui.current_buffer, "focus_last"):
                ui.current_buffer.focus_last()
                ui.update()
        else:
            ui.notify('unknown movement: ' + self.movement,
                      priority='error')

########NEW FILE########
__FILENAME__ = search
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import argparse
import logging

from alot.commands import Command, registerCommand
from alot.commands.globals import PromptCommand
from alot.commands.globals import MoveCommand

from alot.db.errors import DatabaseROError
from alot import commands
from alot import buffers


MODE = 'search'


@registerCommand(MODE, 'select')
class OpenThreadCommand(Command):

    """open thread in a new buffer"""
    def __init__(self, thread=None, **kwargs):
        """
        :param thread: thread to open (Uses focussed thread if unset)
        :type thread: :class:`~alot.db.Thread`
        """
        self.thread = thread
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        if not self.thread:
            self.thread = ui.current_buffer.get_selected_thread()
        if self.thread:
            query = ui.current_buffer.querystring
            logging.info('open thread view for %s' % self.thread)

            sb = buffers.ThreadBuffer(ui, self.thread)
            ui.buffer_open(sb)
            sb.unfold_matching(query)


@registerCommand(MODE, 'refine', help='refine query', arguments=[
    (['--sort'], {'help': 'sort order', 'choices': [
                  'oldest_first', 'newest_first', 'message_id', 'unsorted']}),
    (['query'], {'nargs': argparse.REMAINDER, 'help': 'search string'})])
@registerCommand(MODE, 'sort', help='set sort order', arguments=[
    (['sort'], {'help': 'sort order', 'choices': [
                'oldest_first', 'newest_first', 'message_id', 'unsorted']}),
])
class RefineCommand(Command):

    """refine the querystring of this buffer"""
    def __init__(self, query=None, sort=None, **kwargs):
        """
        :param query: new querystring given as list of strings as returned by
                      argparse
        :type query: list of str
        """
        if query is None:
            self.querystring = None
        else:
            self.querystring = ' '.join(query)
        self.sort_order = sort
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        if self.querystring or self.sort_order:
            sbuffer = ui.current_buffer
            oldquery = sbuffer.querystring
            if self.querystring not in [None, oldquery]:
                sbuffer.querystring = self.querystring
                sbuffer = ui.current_buffer
            if self.sort_order:
                sbuffer.sort_order = self.sort_order
            sbuffer.rebuild()
            ui.update()
        else:
            ui.notify('empty query string')


@registerCommand(MODE, 'refineprompt')
class RefinePromptCommand(Command):

    """prompt to change this buffers querystring"""
    repeatable = True

    def apply(self, ui):
        sbuffer = ui.current_buffer
        oldquery = sbuffer.querystring
        return ui.apply_command(PromptCommand('refine ' + oldquery))


@registerCommand(MODE, 'retagprompt')
class RetagPromptCommand(Command):

    """prompt to retag selected threads\' tags"""
    def apply(self, ui):
        thread = ui.current_buffer.get_selected_thread()
        if not thread:
            return
        tags = []
        for tag in thread.get_tags():
            if ' ' in tag:
                tags.append('"%s"' % tag)
            # skip empty tags
            elif tag:
                tags.append(tag)
        initial_tagstring = ','.join(sorted(tags)) + ','
        return ui.apply_command(PromptCommand('retag ' + initial_tagstring))


@registerCommand(MODE, 'tag', forced={'action': 'add'}, arguments=[
    (['--no-flush'], {'action': 'store_false', 'dest': 'flush',
                      'default': 'True',
                      'help': 'postpone a writeout to the index'}),
    (['--all'], {'action': 'store_true', 'dest': 'allmessages', 'default':
                 False, 'help': 'retag all messages in search result'}),
    (['tags'], {'help': 'comma separated list of tags'})],
    help='add tags to all messages in the thread that match the current query',
)
@registerCommand(MODE, 'retag', forced={'action': 'set'}, arguments=[
    (['--no-flush'], {'action': 'store_false', 'dest': 'flush',
                      'default': 'True',
                      'help': 'postpone a writeout to the index'}),
    (['--all'], {'action': 'store_true', 'dest': 'allmessages', 'default':
                 False, 'help': 'retag all messages in search result'}),
    (['tags'], {'help': 'comma separated list of tags'})],
    help='set tags of all messages in the thread that match the current query',
)
@registerCommand(MODE, 'untag', forced={'action': 'remove'}, arguments=[
    (['--no-flush'], {'action': 'store_false', 'dest': 'flush',
                      'default': 'True',
                      'help': 'postpone a writeout to the index'}),
    (['--all'], {'action': 'store_true', 'dest': 'allmessages', 'default':
                 False, 'help': 'retag all messages in search result'}),
    (['tags'], {'help': 'comma separated list of tags'})],
    help='remove tags from all messages in the thread that match the current query',
)
@registerCommand(MODE, 'toggletags', forced={'action': 'toggle'}, arguments=[
    (['--no-flush'], {'action': 'store_false', 'dest': 'flush',
                      'default': 'True',
                      'help': 'postpone a writeout to the index'}),
    (['tags'], {'help': 'comma separated list of tags'})],
    help="""flip presence of tags on this thread.
    A tag is considered present if at least one message contained in this
    thread is tagged with it. In that case this command will remove the tag
    from every message in the thread.
    """)
class TagCommand(Command):

    """manipulate message tags"""
    repeatable = True

    def __init__(self, tags=u'', action='add', allmessages=False, flush=True,
                 **kwargs):
        """
        :param tags: comma separated list of tagstrings to set
        :type tags: str
        :param action: adds tags if 'add', removes them if 'remove', adds tags
                       and removes all other if 'set' or toggle individually if
                       'toggle'
        :type action: str
        :param all: tag all messages in search result
        :type all: bool
        :param flush: imediately write out to the index
        :type flush: bool
        """
        self.tagsstring = tags
        self.action = action
        self.allm = allmessages
        self.flush = flush
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        searchbuffer = ui.current_buffer
        threadline_widget = searchbuffer.get_selected_threadline()
        # pass if the current buffer has no selected threadline
        # (displays an empty search result)
        if threadline_widget is None:
            return

        testquery = searchbuffer.querystring
        thread = threadline_widget.get_thread()
        if not self.allm:
            testquery = "(%s) AND thread:%s" % (testquery,
                                                thread.get_thread_id())
        logging.debug('all? %s' % self.allm)
        logging.debug('q: %s' % testquery)

        hitcount_before = ui.dbman.count_messages(testquery)

        def remove_thread():
            logging.debug('remove thread from result list: %s' % thread)
            if threadline_widget in searchbuffer.threadlist:
                # remove this thread from result list
                searchbuffer.threadlist.remove(threadline_widget)

        def refresh():
            # remove thread from resultset if it doesn't match the search query
            # any more and refresh selected threadline otherwise
            hitcount_after = ui.dbman.count_messages(testquery)
            # update total result count
            if not self.allm:
                if hitcount_after == 0:
                    remove_thread()
                else:
                    threadline_widget.rebuild()
            else:
                searchbuffer.rebuild()

            searchbuffer.result_count += (hitcount_after - hitcount_before)
            ui.update()

        tags = filter(lambda x: x, self.tagsstring.split(','))

        try:
            if self.action == 'add':
                ui.dbman.tag(testquery, tags, remove_rest=False)
            if self.action == 'set':
                ui.dbman.tag(testquery, tags, remove_rest=True)
            elif self.action == 'remove':
                ui.dbman.untag(testquery, tags)
            elif self.action == 'toggle':
                if not self.allm:
                    to_remove = []
                    to_add = []
                    for t in tags:
                        if t in thread.get_tags():
                            to_remove.append(t)
                        else:
                            to_add.append(t)
                    thread.remove_tags(to_remove)
                    thread.add_tags(to_add, afterwards=refresh)
        except DatabaseROError:
            ui.notify('index in read-only mode', priority='error')
            return

        # flush index
        if self.flush:
            ui.apply_command(commands.globals.FlushCommand(callback=refresh))


@registerCommand(MODE, 'move', help='move focus in search buffer',
                 arguments=[(['movement'], {
                             'nargs': argparse.REMAINDER,
                             'help': 'last'})])
class MoveFocusCommand(MoveCommand):

    def apply(self, ui):
        logging.debug(self.movement)
        if self.movement == 'last':
            ui.current_buffer.focus_last()
            ui.update()
        else:
            MoveCommand.apply(self, ui)

########NEW FILE########
__FILENAME__ = taglist
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
from alot.commands import Command, registerCommand
from alot.commands.globals import SearchCommand

MODE = 'taglist'


@registerCommand(MODE, 'select')
class TaglistSelectCommand(Command):

    """search for messages with selected tag"""
    def apply(self, ui):
        tagstring = ui.current_buffer.get_selected_tag()
        cmd = SearchCommand(query=['tag:"%s"' % tagstring])
        ui.apply_command(cmd)

########NEW FILE########
__FILENAME__ = thread
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import os
import re
import logging
import tempfile
import argparse
from twisted.internet.defer import inlineCallbacks
import subprocess
from email.Utils import getaddresses, parseaddr
import mailcap
from cStringIO import StringIO

from alot.commands import Command, registerCommand
from alot.commands.globals import ExternalCommand
from alot.commands.globals import FlushCommand
from alot.commands.globals import ComposeCommand
from alot.commands.globals import MoveCommand
from alot.commands.globals import CommandCanceled
from alot.commands.envelope import SendCommand
from alot import completion
from alot.db.utils import decode_header
from alot.db.utils import encode_header
from alot.db.utils import extract_headers
from alot.db.utils import extract_body
from alot.db.envelope import Envelope
from alot.db.attachment import Attachment
from alot.db.errors import DatabaseROError
from alot.settings import settings
from alot.helper import parse_mailcap_nametemplate
from alot.helper import split_commandstring
from alot.utils.booleanaction import BooleanAction
from alot.completion import ContactsCompleter

from alot.widgets.globals import AttachmentWidget

MODE = 'thread'


def determine_sender(mail, action='reply'):
    """
    Inspect a given mail to reply/forward/bounce and find the most appropriate
    account to act from and construct a suitable From-Header to use.

    :param mail: the email to inspect
    :type mail: `email.message.Message`
    :param action: intended use case: one of "reply", "forward" or "bounce"
    :type action: str
    """
    assert action in ['reply', 'forward', 'bounce']
    realname = None
    address = None

    # get accounts
    my_accounts = settings.get_accounts()
    assert my_accounts, 'no accounts set!'

    # extract list of addresses to check for my address
    # X-Envelope-To and Envelope-To are used to store the recipient address
    # if not included in other fields
    candidate_addresses = getaddresses(mail.get_all('To', []) +
                                       mail.get_all('Cc', []) +
                                       mail.get_all('Delivered-To', []) +
                                       mail.get_all('X-Envelope-To', []) +
                                       mail.get_all('Envelope-To', []) +
                                       mail.get_all('From', []))

    logging.debug('candidate addresses: %s' % candidate_addresses)
    # pick the most important account that has an address in candidates
    # and use that accounts realname and the address found here
    for account in my_accounts:
        acc_addresses = account.get_addresses()
        for alias in acc_addresses:
            if realname is not None:
                break
            regex = re.compile(re.escape(alias), flags=re.IGNORECASE)
            for seen_name, seen_address in candidate_addresses:
                if regex.match(seen_address):
                    logging.debug("match!: '%s' '%s'" % (seen_address, alias))
                    if settings.get(action + '_force_realname'):
                        realname = account.realname
                    else:
                        realname = seen_name
                    if settings.get(action + '_force_address'):
                        address = account.address
                    else:
                        address = seen_address

    # revert to default account if nothing found
    if realname is None:
        account = my_accounts[0]
        realname = account.realname
        address = account.address
    logging.debug('using realname: "%s"' % realname)
    logging.debug('using address: %s' % address)

    from_value = address if realname == '' else '%s <%s>' % (realname, address)
    return from_value, account


@registerCommand(MODE, 'reply', arguments=[
    (['--all'], {'action': 'store_true', 'help': 'reply to all'}),
    (['--spawn'], {'action': BooleanAction, 'default': None,
                   'help': 'open editor in new window'})])
class ReplyCommand(Command):

    """reply to message"""
    repeatable = True

    def __init__(self, message=None, all=False, spawn=None, **kwargs):
        """
        :param message: message to reply to (defaults to selected message)
        :type message: `alot.db.message.Message`
        :param all: group reply; copies recipients from Bcc/Cc/To to the reply
        :type all: bool
        :param spawn: force spawning of editor in a new terminal
        :type spawn: bool
        """
        self.message = message
        self.groupreply = all
        self.force_spawn = spawn
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        # get message to forward if not given in constructor
        if not self.message:
            self.message = ui.current_buffer.get_selected_message()
        mail = self.message.get_email()

        # set body text
        name, address = self.message.get_author()
        timestamp = self.message.get_date()
        qf = settings.get_hook('reply_prefix')
        if qf:
            quotestring = qf(name, address, timestamp, ui=ui, dbm=ui.dbman)
        else:
            quotestring = 'Quoting %s (%s)\n' % (name or address, timestamp)
        mailcontent = quotestring
        quotehook = settings.get_hook('text_quote')
        if quotehook:
            mailcontent += quotehook(self.message.accumulate_body())
        else:
            quote_prefix = settings.get('quote_prefix')
            for line in self.message.accumulate_body().splitlines():
                mailcontent += quote_prefix + line + '\n'

        envelope = Envelope(bodytext=mailcontent)

        # copy subject
        subject = decode_header(mail.get('Subject', ''))
        reply_subject_hook = settings.get_hook('reply_subject')
        if reply_subject_hook:
            subject = reply_subject_hook(subject)
        else:
            rsp = settings.get('reply_subject_prefix')
            if not subject.lower().startswith(('re:', rsp.lower())):
                subject = rsp + subject
        envelope.add('Subject', subject)

        # set From-header and sending account
        try:
            from_header, account = determine_sender(mail, 'reply')
        except AssertionError as e:
            ui.notify(e.message, priority='error')
            return
        envelope.add('From', from_header)

        # set To
        sender = mail['Reply-To'] or mail['From']
        my_addresses = settings.get_addresses()
        sender_address = parseaddr(sender)[1]
        cc = ''

        # check if reply is to self sent message
        if sender_address in my_addresses:
            recipients = [mail['To']]
            emsg = 'Replying to own message, set recipients to: %s' \
                % recipients
            logging.debug(emsg)
        else:
            recipients = [sender]

        if self.groupreply:
            # make sure that our own address is not included
            # if the message was self-sent, then our address is not included
            MFT = mail.get_all('Mail-Followup-To', [])
            followupto = self.clear_my_address(my_addresses, MFT)
            if followupto and settings.get('honor_followup_to'):
                logging.debug('honor followup to: %s', followupto)
                recipients = [followupto]
                # since Mail-Followup-To was set, ignore the Cc header
            else:
                if sender != mail['From']:
                    recipients.append(mail['From'])

                # append To addresses if not replying to self sent message
                if sender_address not in my_addresses:
                    cleared = self.clear_my_address(
                        my_addresses, mail.get_all('To', []))
                    recipients.append(cleared)

                # copy cc for group-replies
                if 'Cc' in mail:
                    cc = self.clear_my_address(
                        my_addresses, mail.get_all('Cc', []))
                    envelope.add('Cc', decode_header(cc))

        to = ', '.join(recipients)
        logging.debug('reply to: %s' % to)
        envelope.add('To', decode_header(to))

        # if any of the recipients is a mailinglist that we are subscribed to,
        # set Mail-Followup-To header so that duplicates are avoided
        if settings.get('followup_to'):
            # to and cc are already cleared of our own address
            allrecipients = [to] + [cc]
            lists = settings.get('mailinglists')
            # check if any recipient address matches a known mailing list
            if any([addr in lists for n, addr in getaddresses(allrecipients)]):
                followupto = ', '.join(allrecipients)
                logging.debug('mail followup to: %s' % followupto)
                envelope.add('Mail-Followup-To', decode_header(followupto))

        # set In-Reply-To header
        envelope.add('In-Reply-To', '<%s>' % self.message.get_message_id())

        # set References header
        old_references = mail.get('References', '')
        if old_references:
            old_references = old_references.split()
            references = old_references[-8:]
            if len(old_references) > 8:
                references = old_references[:1] + references
            references.append('<%s>' % self.message.get_message_id())
            envelope.add('References', ' '.join(references))
        else:
            envelope.add('References', '<%s>' % self.message.get_message_id())

        # continue to compose
        ui.apply_command(ComposeCommand(envelope=envelope,
                                        spawn=self.force_spawn))

    def clear_my_address(self, my_addresses, value):
        """return recipient header without the addresses in my_addresses"""
        new_value = []
        for name, address in getaddresses(value):
            if address not in my_addresses:
                if name != '':
                    new_value.append('"%s" <%s>' % (name, address))
                else:
                    new_value.append(address)
        return ', '.join(new_value)


@registerCommand(MODE, 'forward', arguments=[
    (['--attach'], {'action': 'store_true', 'help': 'attach original mail'}),
    (['--spawn'], {'action': BooleanAction, 'default': None,
                   'help': 'open editor in new window'})])
class ForwardCommand(Command):

    """forward message"""
    repeatable = True

    def __init__(self, message=None, attach=True, spawn=None, **kwargs):
        """
        :param message: message to forward (defaults to selected message)
        :type message: `alot.db.message.Message`
        :param attach: attach original mail instead of inline quoting its body
        :type attach: bool
        :param spawn: force spawning of editor in a new terminal
        :type spawn: bool
        """
        self.message = message
        self.inline = not attach
        self.force_spawn = spawn
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        # get message to forward if not given in constructor
        if not self.message:
            self.message = ui.current_buffer.get_selected_message()
        mail = self.message.get_email()

        envelope = Envelope()

        if self.inline:  # inline mode
            # set body text
            name, address = self.message.get_author()
            timestamp = self.message.get_date()
            qf = settings.get_hook('forward_prefix')
            if qf:
                quote = qf(name, address, timestamp, ui=ui, dbm=ui.dbman)
            else:
                quote = 'Forwarded message from %s (%s):\n' % (
                    name or address, timestamp)
            mailcontent = quote
            quotehook = settings.get_hook('text_quote')
            if quotehook:
                mailcontent += quotehook(self.message.accumulate_body())
            else:
                quote_prefix = settings.get('quote_prefix')
                for line in self.message.accumulate_body().splitlines():
                    mailcontent += quote_prefix + line + '\n'

            envelope.body = mailcontent

        else:  # attach original mode
            # attach original msg
            mail.set_type('message/rfc822')
            mail['Content-Disposition'] = 'attachment'
            envelope.attach(Attachment(mail))

        # copy subject
        subject = decode_header(mail.get('Subject', ''))
        subject = 'Fwd: ' + subject
        forward_subject_hook = settings.get_hook('forward_subject')
        if forward_subject_hook:
            subject = forward_subject_hook(subject)
        else:
            fsp = settings.get('forward_subject_prefix')
            if not subject.startswith(('Fwd:', fsp)):
                subject = fsp + subject
        envelope.add('Subject', subject)

        # set From-header and sending account
        try:
            from_header, account = determine_sender(mail, 'reply')
        except AssertionError as e:
            ui.notify(e.message, priority='error')
            return
        envelope.add('From', from_header)

        # continue to compose
        ui.apply_command(ComposeCommand(envelope=envelope,
                                        spawn=self.force_spawn))


@registerCommand(MODE, 'bounce')
class BounceMailCommand(Command):

    """directly re-send selected message"""
    repeatable = True

    def __init__(self, message=None, **kwargs):
        """
        :param message: message to bounce (defaults to selected message)
        :type message: `alot.db.message.Message`
        """
        self.message = message
        Command.__init__(self, **kwargs)

    @inlineCallbacks
    def apply(self, ui):
        # get mail to bounce
        if not self.message:
            self.message = ui.current_buffer.get_selected_message()
        mail = self.message.get_email()

        # look if this makes sense: do we have any accounts set up?
        my_accounts = settings.get_accounts()
        if not my_accounts:
            ui.notify('no accounts set', priority='error')
            return

        # remove "Resent-*" headers if already present
        del mail['Resent-From']
        del mail['Resent-To']
        del mail['Resent-Cc']
        del mail['Resent-Date']
        del mail['Resent-Message-ID']

        # set Resent-From-header and sending account
        try:
            resent_from_header, account = determine_sender(mail, 'bounce')
        except AssertionError as e:
            ui.notify(e.message, priority='error')
            return
        mail['Resent-From'] = resent_from_header

        # set Reset-To
        allbooks = not settings.get('complete_matching_abook_only')
        logging.debug('allbooks: %s', allbooks)
        if account is not None:
            abooks = settings.get_addressbooks(order=[account],
                                               append_remaining=allbooks)
            logging.debug(abooks)
            completer = ContactsCompleter(abooks)
        else:
            completer = None
        to = yield ui.prompt('To', completer=completer)
        if to is None:
            raise CommandCanceled()

        mail['Resent-To'] = to.strip(' \t\n,')

        logging.debug("bouncing mail")
        logging.debug(mail.__class__)

        ui.apply_command(SendCommand(mail=mail))


@registerCommand(MODE, 'editnew', arguments=[
    (['--spawn'], {'action': BooleanAction, 'default': None,
                   'help': 'open editor in new window'})])
class EditNewCommand(Command):

    """edit message in as new"""
    def __init__(self, message=None, spawn=None, **kwargs):
        """
        :param message: message to reply to (defaults to selected message)
        :type message: `alot.db.message.Message`
        :param spawn: force spawning of editor in a new terminal
        :type spawn: bool
        """
        self.message = message
        self.force_spawn = spawn
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        if not self.message:
            self.message = ui.current_buffer.get_selected_message()
        mail = self.message.get_email()
        # set body text
        name, address = self.message.get_author()
        mailcontent = self.message.accumulate_body()
        envelope = Envelope(bodytext=mailcontent)

        # copy selected headers
        to_copy = ['Subject', 'From', 'To', 'Cc', 'Bcc', 'In-Reply-To',
                   'References']
        for key in to_copy:
            value = decode_header(mail.get(key, ''))
            if value:
                envelope.add(key, value)

        # copy attachments
        for b in self.message.get_attachments():
            envelope.attach(b)

        ui.apply_command(ComposeCommand(envelope=envelope,
                                        spawn=self.force_spawn,
                                        omit_signature=True))


@registerCommand(MODE, 'fold', forced={'visible': False}, arguments=[
    (
        ['query'], {'help': 'query used to filter messages to affect',
                    'nargs': '*'}),
],
    help='fold message(s)')
@registerCommand(MODE, 'unfold', forced={'visible': True}, arguments=[
    (['query'], {'help': 'query used to filter messages to affect',
                 'nargs': '*'}),
], help='unfold message(s)')
@registerCommand(MODE, 'togglesource', forced={'raw': 'toggle'}, arguments=[
    (['query'], {'help': 'query used to filter messages to affect',
                 'nargs': '*'}),
], help='display message source')
@registerCommand(MODE, 'toggleheaders', forced={'all_headers': 'toggle'},
                 arguments=[
                     (['query'], {
                         'help': 'query used to filter messages to affect',
                         'nargs': '*'}),
                 ],
                 help='display all headers')
class ChangeDisplaymodeCommand(Command):

    """fold or unfold messages"""
    repeatable = True

    def __init__(self, query=None, visible=None, raw=None, all_headers=None,
                 **kwargs):
        """
        :param query: notmuch query string used to filter messages to affect
        :type query: str
        :param visible: unfold if `True`, fold if `False`, ignore if `None`
        :type visible: True, False, 'toggle' or None
        :param raw: display raw message text.
        :type raw: True, False, 'toggle' or None
        :param all_headers: show all headers (only visible if not in raw mode)
        :type all_headers: True, False, 'toggle' or None
        """
        self.query = None
        if query:
            self.query = ' '.join(query)
        self.visible = visible
        self.raw = raw
        self.all_headers = all_headers
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        tbuffer = ui.current_buffer
        logging.debug('matching lines %s...' % (self.query))
        if self.query is None:
            messagetrees = [tbuffer.get_selected_messagetree()]
        else:
            messagetrees = tbuffer.messagetrees()
            if self.query != '*':

                def matches(msgt):
                    msg = msgt.get_message()
                    return msg.matches(self.query)

                messagetrees = filter(matches, messagetrees)

        for mt in messagetrees:
            # determine new display values for this message
            if self.visible == 'toggle':
                visible = mt.is_collapsed(mt.root)
            else:
                visible = self.visible
            if self.raw == 'toggle':
                tbuffer.focus_selected_message()
            raw = not mt.display_source if self.raw == 'toggle' else self.raw
            all_headers = not mt.display_all_headers \
                if self.all_headers == 'toggle' else self.all_headers

            # collapse/expand depending on new 'visible' value
            if visible is False:
                mt.collapse(mt.root)
            elif visible is True:  # could be None
                mt.expand(mt.root)
            tbuffer.focus_selected_message()
            # set new values in messagetree obj
            if raw is not None:
                mt.display_source = raw
            if all_headers is not None:
                mt.display_all_headers = all_headers
            mt.debug()
            # let the messagetree reassemble itself
            mt.reassemble()
        # refresh the buffer (clears Tree caches etc)
        tbuffer.refresh()


@registerCommand(MODE, 'pipeto', arguments=[
    (['cmd'], {'help': 'shellcommand to pipe to', 'nargs': '+'}),
    (['--all'], {'action': 'store_true', 'help': 'pass all messages'}),
    (['--format'], {'help': 'output format', 'default': 'raw',
                    'choices': ['raw', 'decoded', 'id', 'filepath']}),
    (['--separately'], {'action': 'store_true',
                        'help': 'call command once for each message'}),
    (['--background'], {'action': 'store_true',
                        'help': 'don\'t stop the interface'}),
    (['--add_tags'], {'action': 'store_true',
                      'help': 'add \'Tags\' header to the message'}),
    (['--shell'], {'action': 'store_true',
                   'help': 'let the shell interpret the command'}),
    (['--notify_stdout'], {'action': 'store_true',
                           'help': 'display cmd\'s stdout as notification'}),
],
)
class PipeCommand(Command):

    """pipe message(s) to stdin of a shellcommand"""
    repeatable = True

    def __init__(self, cmd, all=False, separately=False, background=False,
                 shell=False, notify_stdout=False, format='raw',
                 add_tags=False, noop_msg='no command specified',
                 confirm_msg='', done_msg=None, **kwargs):
        """
        :param cmd: shellcommand to open
        :type cmd: str or list of str
        :param all: pipe all, not only selected message
        :type all: bool
        :param separately: call command once per message
        :type separately: bool
        :param background: do not suspend the interface
        :type background: bool
        :param notify_stdout: display command\'s stdout as notification message
        :type notify_stdout: bool
        :param shell: let the shell interpret the command
        :type shell: bool

                       'raw': message content as is,
                       'decoded': message content, decoded quoted printable,
                       'id': message ids, separated by newlines,
                       'filepath': paths to message files on disk
        :type format: str
        :param add_tags: add 'Tags' header to the message
        :type add_tags: bool
        :param noop_msg: error notification to show if `cmd` is empty
        :type noop_msg: str
        :param confirm_msg: confirmation question to ask (continues directly if
                            unset)
        :type confirm_msg: str
        :param done_msg: notification message to show upon success
        :type done_msg: str
        """
        Command.__init__(self, **kwargs)
        if isinstance(cmd, unicode):
            cmd = split_commandstring(cmd)
        self.cmd = cmd
        self.whole_thread = all
        self.separately = separately
        self.background = background
        self.shell = shell
        self.notify_stdout = notify_stdout
        self.output_format = format
        self.add_tags = add_tags
        self.noop_msg = noop_msg
        self.confirm_msg = confirm_msg
        self.done_msg = done_msg

    @inlineCallbacks
    def apply(self, ui):
        # abort if command unset
        if not self.cmd:
            ui.notify(self.noop_msg, priority='error')
            return

        # get messages to pipe
        if self.whole_thread:
            thread = ui.current_buffer.get_selected_thread()
            if not thread:
                return
            to_print = thread.get_messages().keys()
        else:
            to_print = [ui.current_buffer.get_selected_message()]

        # ask for confirmation if needed
        if self.confirm_msg:
            if (yield ui.choice(self.confirm_msg, select='yes',
                                cancel='no')) == 'no':
                return

        # prepare message sources
        pipestrings = []
        separator = '\n\n'
        logging.debug('PIPETO format')
        logging.debug(self.output_format)

        if self.output_format == 'id':
            pipestrings = [e.get_message_id() for e in to_print]
            separator = '\n'
        elif self.output_format == 'filepath':
            pipestrings = [e.get_filename() for e in to_print]
            separator = '\n'
        else:
            for msg in to_print:
                mail = msg.get_email()
                if self.add_tags:
                    mail['Tags'] = encode_header('Tags',
                                                 ', '.join(msg.get_tags()))
                if self.output_format == 'raw':
                    pipestrings.append(mail.as_string())
                elif self.output_format == 'decoded':
                    headertext = extract_headers(mail)
                    bodytext = extract_body(mail)
                    msgtext = '%s\n\n%s' % (headertext, bodytext)
                    pipestrings.append(msgtext.encode('utf-8'))

        if not self.separately:
            pipestrings = [separator.join(pipestrings)]
        if self.shell:
            self.cmd = [' '.join(self.cmd)]

        # do teh monkey
        for mail in pipestrings:
            if self.background:
                logging.debug('call in background: %s' % str(self.cmd))
                proc = subprocess.Popen(self.cmd,
                                        shell=True, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                out, err = proc.communicate(mail)
                if self.notify_stdout:
                    ui.notify(out)
            else:
                logging.debug('stop urwid screen')
                ui.mainloop.screen.stop()
                logging.debug('call: %s' % str(self.cmd))
                # if proc.stdout is defined later calls to communicate
                # seem to be non-blocking!
                proc = subprocess.Popen(self.cmd, shell=True,
                                        stdin=subprocess.PIPE,
                                        # stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                out, err = proc.communicate(mail)
                logging.debug('start urwid screen')
                ui.mainloop.screen.start()
            if err:
                ui.notify(err, priority='error')
                return

        # display 'done' message
        if self.done_msg:
            ui.notify(self.done_msg)


@registerCommand(MODE, 'remove', arguments=[
    (['--all'], {'action': 'store_true', 'help': 'remove whole thread'})])
class RemoveCommand(Command):

    """remove message(s) from the index"""
    repeatable = True

    def __init__(self, all=False, **kwargs):
        """
        :param all: remove all messages from thread, not just selected one
        :type all: bool
        """
        Command.__init__(self, **kwargs)
        self.all = all

    @inlineCallbacks
    def apply(self, ui):
        threadbuffer = ui.current_buffer
        # get messages and notification strings
        if self.all:
            thread = threadbuffer.get_selected_thread()
            tid = thread.get_thread_id()
            messages = thread.get_messages().keys()
            confirm_msg = 'remove all messages in thread?'
            ok_msg = 'removed all messages in thread: %s' % tid
        else:
            msg = threadbuffer.get_selected_message()
            messages = [msg]
            confirm_msg = 'remove selected message?'
            ok_msg = 'removed message: %s' % msg.get_message_id()

        # ask for confirmation
        if (yield ui.choice(confirm_msg, select='yes', cancel='no')) == 'no':
            return

        # notify callback
        def callback():
            threadbuffer.rebuild()
            ui.notify(ok_msg)

        # remove messages
        for m in messages:
            ui.dbman.remove_message(m, afterwards=callback)

        ui.apply_command(FlushCommand())


@registerCommand(MODE, 'print', arguments=[
    (['--all'], {'action': 'store_true', 'help': 'print all messages'}),
    (['--raw'], {'action': 'store_true', 'help': 'pass raw mail string'}),
    (['--separately'], {'action': 'store_true',
                        'help': 'call print command once for each message'}),
    (['--add_tags'], {'action': 'store_true',
                      'help': 'add \'Tags\' header to the message'}),
],
)
class PrintCommand(PipeCommand):

    """print message(s)"""
    repeatable = True

    def __init__(self, all=False, separately=False, raw=False, add_tags=False,
                 **kwargs):
        """
        :param all: print all, not only selected messages
        :type all: bool
        :param separately: call print command once per message
        :type separately: bool
        :param raw: pipe raw message string to print command
        :type raw: bool
        :param add_tags: add 'Tags' header to the message
        :type add_tags: bool
        """
        # get print command
        cmd = settings.get('print_cmd') or ''

        # set up notification strings
        if all:
            confirm_msg = 'print all messages in thread?'
            ok_msg = 'printed thread using %s' % cmd
        else:
            confirm_msg = 'print selected message?'
            ok_msg = 'printed message using %s' % cmd

        # no print cmd set
        noop_msg = 'no print command specified. Set "print_cmd" in the '\
            'global section.'

        PipeCommand.__init__(self, [cmd], all=all, separately=separately,
                             background=True,
                             shell=False,
                             format='raw' if raw else 'decoded',
                             add_tags=add_tags,
                             noop_msg=noop_msg, confirm_msg=confirm_msg,
                             done_msg=ok_msg, **kwargs)


@registerCommand(MODE, 'save', arguments=[
    (['--all'], {'action': 'store_true', 'help': 'save all attachments'}),
    (['path'], {'nargs': '?', 'help': 'path to save to'})])
class SaveAttachmentCommand(Command):

    """save attachment(s)"""
    def __init__(self, all=False, path=None, **kwargs):
        """
        :param all: save all, not only selected attachment
        :type all: bool
        :param path: path to write to. if `all` is set, this must be a
                     directory.
        :type path: str
        """
        Command.__init__(self, **kwargs)
        self.all = all
        self.path = path

    @inlineCallbacks
    def apply(self, ui):
        pcomplete = completion.PathCompleter()
        savedir = settings.get('attachment_prefix', '~')
        if self.all:
            msg = ui.current_buffer.get_selected_message()
            if not self.path:
                self.path = yield ui.prompt('save attachments to',
                                            text=os.path.join(savedir, ''),
                                            completer=pcomplete)
            if self.path:
                if os.path.isdir(os.path.expanduser(self.path)):
                    for a in msg.get_attachments():
                        dest = a.save(self.path)
                        name = a.get_filename()
                        if name:
                            ui.notify('saved %s as: %s' % (name, dest))
                        else:
                            ui.notify('saved attachment as: %s' % dest)
                else:
                    ui.notify('not a directory: %s' % self.path,
                              priority='error')
            else:
                raise CommandCanceled()
        else:  # save focussed attachment
            focus = ui.get_deep_focus()
            if isinstance(focus, AttachmentWidget):
                attachment = focus.get_attachment()
                filename = attachment.get_filename()
                if not self.path:
                    msg = 'save attachment (%s) to ' % filename
                    initialtext = os.path.join(savedir, filename)
                    self.path = yield ui.prompt(msg,
                                                completer=pcomplete,
                                                text=initialtext)
                if self.path:
                    try:
                        dest = attachment.save(self.path)
                        ui.notify('saved attachment as: %s' % dest)
                    except (IOError, OSError) as e:
                        ui.notify(str(e), priority='error')
                else:
                    raise CommandCanceled()


class OpenAttachmentCommand(Command):

    """displays an attachment according to mailcap"""
    def __init__(self, attachment, **kwargs):
        """
        :param attachment: attachment to open
        :type attachment: :class:`~alot.db.attachment.Attachment`
        """
        Command.__init__(self, **kwargs)
        self.attachment = attachment

    def apply(self, ui):
        logging.info('open attachment')
        mimetype = self.attachment.get_content_type()

        # returns pair of preliminary command string and entry dict containing
        # more info. We only use the dict and construct the command ourselves
        _, entry = settings.mailcap_find_match(mimetype)
        if entry:
            afterwards = None  # callback, will rm tempfile if used
            handler_stdin = None
            tempfile_name = None
            handler_raw_commandstring = entry['view']
            # read parameter
            part = self.attachment.get_mime_representation()
            parms = tuple(map('='.join, part.get_params()))

            # in case the mailcap defined command contains no '%s',
            # we pipe the files content to the handling command via stdin
            if '%s' in handler_raw_commandstring:
                nametemplate = entry.get('nametemplate', '%s')
                prefix, suffix = parse_mailcap_nametemplate(nametemplate)
                tmpfile = tempfile.NamedTemporaryFile(delete=False,
                                                      prefix=prefix,
                                                      suffix=suffix)

                tempfile_name = tmpfile.name
                self.attachment.write(tmpfile)
                tmpfile.close()

                def afterwards():
                    os.unlink(tempfile_name)
            else:
                handler_stdin = StringIO()
                self.attachment.write(handler_stdin)

            # create handler command list
            handler_cmd = mailcap.subst(handler_raw_commandstring, mimetype,
                                        filename=tempfile_name, plist=parms)

            handler_cmdlist = split_commandstring(handler_cmd)

            # 'needsterminal' makes handler overtake the terminal
            nt = entry.get('needsterminal', None)
            overtakes = (nt is None)

            ui.apply_command(ExternalCommand(handler_cmdlist,
                                             stdin=handler_stdin,
                                             on_success=afterwards,
                                             thread=overtakes))
        else:
            ui.notify('unknown mime type')


@registerCommand(MODE, 'move', help='move focus in current buffer',
                 arguments=[(['movement'], {
                             'nargs': argparse.REMAINDER,
                             'help': 'up, down, page up, '
                                     'page down, first, last'})])
class MoveFocusCommand(MoveCommand):

    def apply(self, ui):
        logging.debug(self.movement)
        tbuffer = ui.current_buffer
        if self.movement == 'parent':
            tbuffer.focus_parent()
        elif self.movement == 'first reply':
            tbuffer.focus_first_reply()
        elif self.movement == 'last reply':
            tbuffer.focus_last_reply()
        elif self.movement == 'next sibling':
            tbuffer.focus_next_sibling()
        elif self.movement == 'previous sibling':
            tbuffer.focus_prev_sibling()
        elif self.movement == 'next':
            tbuffer.focus_next()
        elif self.movement == 'previous':
            tbuffer.focus_prev()
        elif self.movement == 'next unfolded':
            tbuffer.focus_next_unfolded()
        elif self.movement == 'previous unfolded':
            tbuffer.focus_prev_unfolded()
        else:
            MoveCommand.apply(self, ui)
        # TODO add 'next matching' if threadbuffer stores the original query
        # TODO: add next by date..
        tbuffer.body.refresh()


@registerCommand(MODE, 'select')
class ThreadSelectCommand(Command):

    """select focussed element. The fired action depends on the focus:
        - if message summary, this toggles visibility of the message,
        - if attachment line, this opens the attachment"""
    def apply(self, ui):
        focus = ui.get_deep_focus()
        if isinstance(focus, AttachmentWidget):
            logging.info('open attachment')
            ui.apply_command(OpenAttachmentCommand(focus.get_attachment()))
        else:
            ui.apply_command(ChangeDisplaymodeCommand(visible='toggle'))


@registerCommand(MODE, 'tag', forced={'action': 'add'}, arguments=[
    (['--all'], {'action': 'store_true',
     'help': 'tag all messages in thread'}),
    (['--no-flush'], {'action': 'store_false', 'dest': 'flush',
                      'help': 'postpone a writeout to the index'}),
    (['tags'], {'help': 'comma separated list of tags'})],
    help='add tags to message(s)',
)
@registerCommand(MODE, 'retag', forced={'action': 'set'}, arguments=[
    (['--all'], {'action': 'store_true',
     'help': 'tag all messages in thread'}),
    (['--no-flush'], {'action': 'store_false', 'dest': 'flush',
                      'help': 'postpone a writeout to the index'}),
    (['tags'], {'help': 'comma separated list of tags'})],
    help='set message(s) tags.',
)
@registerCommand(MODE, 'untag', forced={'action': 'remove'}, arguments=[
    (['--all'], {'action': 'store_true',
     'help': 'tag all messages in thread'}),
    (['--no-flush'], {'action': 'store_false', 'dest': 'flush',
                      'help': 'postpone a writeout to the index'}),
    (['tags'], {'help': 'comma separated list of tags'})],
    help='remove tags from message(s)',
)
@registerCommand(MODE, 'toggletags', forced={'action': 'toggle'}, arguments=[
    (['--all'], {'action': 'store_true',
     'help': 'tag all messages in thread'}),
    (['--no-flush'], {'action': 'store_false', 'dest': 'flush',
                      'help': 'postpone a writeout to the index'}),
    (['tags'], {'help': 'comma separated list of tags'})],
    help='flip presence of tags on message(s)',
)
class TagCommand(Command):

    """manipulate message tags"""
    repeatable = True

    def __init__(self, tags=u'', action='add', all=False, flush=True,
                 **kwargs):
        """
        :param tags: comma separated list of tagstrings to set
        :type tags: str
        :param action: adds tags if 'add', removes them if 'remove', adds tags
                       and removes all other if 'set' or toggle individually if
                       'toggle'
        :type action: str
        :param all: tag all messages in thread
        :type all: bool
        :param flush: imediately write out to the index
        :type flush: bool
        """
        self.tagsstring = tags
        self.all = all
        self.action = action
        self.flush = flush
        Command.__init__(self, **kwargs)

    def apply(self, ui):
        tbuffer = ui.current_buffer
        if self.all:
            messagetrees = tbuffer.messagetrees()
        else:
            messagetrees = [tbuffer.get_selected_messagetree()]

        def refresh_widgets():
            for mt in messagetrees:
                mt.refresh()

            # put currently selected message id on a block list for the
            # auto-remove-unread feature. This makes sure that explicit
            # tag-unread commands for the current message are not undone on the
            # next keypress (triggering the autorm again)...
            mid = tbuffer.get_selected_mid()
            tbuffer._auto_unread_dont_touch_mids.add(mid)

            tbuffer.refresh()

        tags = filter(lambda x: x, self.tagsstring.split(','))
        try:
            for mt in messagetrees:
                m = mt.get_message()
                if self.action == 'add':
                    m.add_tags(tags, afterwards=refresh_widgets)
                if self.action == 'set':
                    m.add_tags(tags, afterwards=refresh_widgets,
                               remove_rest=True)
                elif self.action == 'remove':
                    m.remove_tags(tags, afterwards=refresh_widgets)
                elif self.action == 'toggle':
                    to_remove = []
                    to_add = []
                    for t in tags:
                        if t in m.get_tags():
                            to_remove.append(t)
                        else:
                            to_add.append(t)
                    m.remove_tags(to_remove)
                    m.add_tags(to_add, afterwards=refresh_widgets)

        except DatabaseROError:
            ui.notify('index in read-only mode', priority='error')
            return

        # flush index
        if self.flush:
            ui.apply_command(FlushCommand())

########NEW FILE########
__FILENAME__ = completion
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import re
import os
import glob
import logging
import argparse

import alot.crypto as crypto
import alot.commands as commands
from alot.buffers import EnvelopeBuffer
from alot.settings import settings
from alot.utils.booleanaction import BooleanAction
from alot.helper import split_commandline
from alot.addressbooks import AddressbookError
from errors import CompletionError

class Completer(object):
    """base class for completers"""
    def complete(self, original, pos):
        """returns a list of completions and cursor positions for the
        string original from position pos on.

        :param original: the string to complete
        :type original: str
        :param pos: starting position to complete from
        :type pos: int
        :returns: pairs of completed string and cursor position in the
                  new string
        :rtype: list of (str, int)
        :raises: :exc:`CompletionError`
        """
        return list()

    def relevant_part(self, original, pos, sep=' '):
        """
        calculates the subword in a `sep`-splitted list of substrings of
        `original` that `pos` is ia.n
        """
        start = original.rfind(sep, 0, pos) + 1
        end = original.find(sep, pos - 1)
        if end == -1:
            end = len(original)
        return original[start:end], start, end, pos - start


class StringlistCompleter(Completer):
    """completer for a fixed list of strings"""

    def __init__(self, resultlist, ignorecase=True, match_anywhere=False):
        """
        :param resultlist: strings used for completion
        :type resultlist: list of str
        :param liberal: match case insensitive and not prefix-only
        :type liberal: bool
        """
        self.resultlist = resultlist
        self.flags = re.IGNORECASE if ignorecase else 0
        self.match_anywhere = match_anywhere

    def complete(self, original, pos):
        pref = original[:pos]

        re_prefix = '.*' if self.match_anywhere else ''

        def match(s, m):
            r = re_prefix + m + '.*'
            return re.match(r, s, flags=self.flags) is not None

        return [(a, len(a)) for a in self.resultlist if match(a, pref)]


class MultipleSelectionCompleter(Completer):
    """
    Meta-Completer that turns any Completer into one that deals with a list of
    completion strings using the wrapped Completer.
    This allows for example to easily construct a completer for comma separated
    recipient-lists using a :class:`ContactsCompleter`.
    """

    def __init__(self, completer, separator=', '):
        """
        :param completer: completer to use for individual substrings
        :type completer: Completer
        :param separator: separator used to split the completion string into
                          substrings to be fed to `completer`.
        :type separator: str
        """
        self._completer = completer
        self._separator = separator

    def relevant_part(self, original, pos):
        """
        calculates the subword of `original` that `pos` is in
        """
        start = original.rfind(self._separator, 0, pos)
        if start == -1:
            start = 0
        else:
            start = start + len(self._separator)
        end = original.find(self._separator, pos - 1)
        if end == -1:
            end = len(original)
        return original[start:end], start, end, pos - start

    def complete(self, original, pos):
        mypart, start, end, mypos = self.relevant_part(original, pos)
        res = []
        for c, p in self._completer.complete(mypart, mypos):
            newprefix = original[:start] + c
            if not original[end:].startswith(self._separator):
                newprefix += self._separator
            res.append((newprefix + original[end:], len(newprefix)))
        return res


class QueryCompleter(Completer):
    """completion for a notmuch query string"""
    def __init__(self, dbman):
        """
        :param dbman: used to look up avaliable tagstrings
        :type dbman: :class:`~alot.db.DBManager`
        """
        self.dbman = dbman
        abooks = settings.get_addressbooks()
        self._abookscompleter = AbooksCompleter(abooks, addressesonly=True)
        self._tagcompleter = TagCompleter(dbman)
        self.keywords = ['tag', 'from', 'to', 'subject', 'attachment',
                         'is', 'id', 'thread', 'folder']

    def complete(self, original, pos):
        mypart, start, end, mypos = self.relevant_part(original, pos)
        myprefix = mypart[:mypos]
        m = re.search('(tag|is|to|from):(\w*)', myprefix)
        if m:
            cmd, params = m.groups()
            cmdlen = len(cmd) + 1  # length of the keyword part incld colon
            if cmd in ['to', 'from']:
                localres = self._abookscompleter.complete(mypart[cmdlen:],
                                                          mypos - cmdlen)
            else:
                localres = self._tagcompleter.complete(mypart[cmdlen:],
                                                       mypos - cmdlen)
            resultlist = []
            for ltxt, lpos in localres:
                newtext = original[:start] + cmd + ':' + ltxt + original[end:]
                newpos = start + len(cmd) + 1 + lpos
                resultlist.append((newtext, newpos))
            return resultlist
        else:
            matched = filter(lambda t: t.startswith(myprefix), self.keywords)
            resultlist = []
            for keyword in matched:
                newprefix = original[:start] + keyword + ':'
                resultlist.append((newprefix + original[end:], len(newprefix)))
            return resultlist


class TagCompleter(StringlistCompleter):
    """complete a tagstring"""

    def __init__(self, dbman):
        """
        :param dbman: used to look up avaliable tagstrings
        :type dbman: :class:`~alot.db.DBManager`
        """
        resultlist = dbman.get_all_tags()
        StringlistCompleter.__init__(self, resultlist)


class TagsCompleter(MultipleSelectionCompleter):
    """completion for a comma separated list of tagstrings"""

    def __init__(self, dbman):
        """
        :param dbman: used to look up avaliable tagstrings
        :type dbman: :class:`~alot.db.DBManager`
        """
        self._completer = TagCompleter(dbman)
        self._separator = ','


class ContactsCompleter(MultipleSelectionCompleter):
    """completes contacts from given address books"""
    def __init__(self, abooks, addressesonly=False):
        """
        :param abooks: used to look up email addresses
        :type abooks: list of :class:`~alot.account.AddresBook`
        :param addressesonly: only insert address, not the realname of the
                              contact
        :type addressesonly: bool
        """
        self._completer = AbooksCompleter(abooks, addressesonly=addressesonly)
        self._separator = ', '


class AbooksCompleter(Completer):
    """completes a contact from given address books"""
    def __init__(self, abooks, addressesonly=False):
        """
        :param abooks: used to look up email addresses
        :type abooks: list of :class:`~alot.account.AddresBook`
        :param addressesonly: only insert address, not the realname of the
                              contact
        :type addressesonly: bool
        """
        self.abooks = abooks
        self.addressesonly = addressesonly

    def complete(self, original, pos):
        if not self.abooks:
            return []
        prefix = original[:pos]
        res = []
        for abook in self.abooks:
            try:
                res = res + abook.lookup(prefix)
            except AddressbookError as e:
                raise CompletionError(e)
        if self.addressesonly:
            returnlist = [(email, len(email)) for (name, email) in res]
        else:
            returnlist = []
            for name, email in res:
                if name:
                    newtext = "%s <%s>" % (name, email)
                else:
                    newtext = email
                returnlist.append((newtext, len(newtext)))
        return returnlist


class ArgparseOptionCompleter(Completer):
    """completes option parameters for a given argparse.Parser"""
    def __init__(self, parser):
        """
        :param parser: the option parser we look up parameter and  choices from
        :type parser: `argparse.ArgumentParser`
        """
        self.parser = parser
        self.actions = parser._optionals._actions

    def complete(self, original, pos):
        pref = original[:pos]

        res = []
        for act in self.actions:
            if '=' in pref:
                optionstring = pref[:pref.rfind('=') + 1]
                # get choices
                if 'choices' in act.__dict__:
                    # TODO: respect prefix
                    choices = act.choices or []
                    res = res + [optionstring + a for a in choices]
            else:
                for optionstring in act.option_strings:
                    if optionstring.startswith(pref):
                        # append '=' for options that await a string value
                        if isinstance(act, argparse._StoreAction) or\
                                isinstance(act, BooleanAction):
                            optionstring += '='
                        res.append(optionstring)

        return [(a, len(a)) for a in res]


class AccountCompleter(StringlistCompleter):
    """completes users' own mailaddresses"""

    def __init__(self, **kwargs):
        accounts = settings.get_accounts()
        resultlist = ["%s <%s>" % (a.realname, a.address) for a in accounts]
        StringlistCompleter.__init__(self, resultlist, match_anywhere=True,
                                     **kwargs)


class CommandNameCompleter(Completer):
    """completes command names"""

    def __init__(self, mode):
        """
        :param mode: mode identifier
        :type mode: str
        """
        self.mode = mode

    def complete(self, original, pos):
        # TODO refine <tab> should get current querystring
        commandprefix = original[:pos]
        logging.debug('original="%s" prefix="%s"' % (original, commandprefix))
        cmdlist = commands.COMMANDS['global'].copy()
        cmdlist.update(commands.COMMANDS[self.mode])
        matching = [t for t in cmdlist if t.startswith(commandprefix)]
        return [(t, len(t)) for t in matching]


class CommandCompleter(Completer):
    """completes one command consisting of command name and parameters"""

    def __init__(self, dbman, mode, currentbuffer=None):
        """
        :param dbman: used to look up avaliable tagstrings
        :type dbman: :class:`~alot.db.DBManager`
        :param mode: mode identifier
        :type mode: str
        :param currentbuffer: currently active buffer. If defined, this will be
                              used to dynamically extract possible completion
                              strings
        :type currentbuffer: :class:`~alot.buffers.Buffer`
        """
        self.dbman = dbman
        self.mode = mode
        self.currentbuffer = currentbuffer
        self._commandnamecompleter = CommandNameCompleter(mode)
        self._querycompleter = QueryCompleter(dbman)
        self._tagcompleter = TagCompleter(dbman)
        abooks = settings.get_addressbooks()
        self._contactscompleter = ContactsCompleter(abooks)
        self._pathcompleter = PathCompleter()
        self._accountscompleter = AccountCompleter()
        self._secretkeyscompleter = CryptoKeyCompleter(private=True)
        self._publickeyscompleter = CryptoKeyCompleter(private=False)

    def complete(self, line, pos):
        # remember how many preceding space characters we see until the command
        # string starts. We'll continue to complete from there on and will add
        # these whitespaces again at the very end
        whitespaceoffset = len(line) - len(line.lstrip())
        line = line[whitespaceoffset:]
        pos = pos - whitespaceoffset

        words = line.split(' ', 1)

        res = []
        if pos <= len(words[0]):  # we complete commands
            for cmd, cpos in self._commandnamecompleter.complete(line, pos):
                newtext = ('%s %s' % (cmd, ' '.join(words[1:])))
                res.append((newtext, cpos + 1))
        else:
            cmd, params = words
            localpos = pos - (len(cmd) + 1)
            parser = commands.lookup_parser(cmd, self.mode)
            if parser is not None:
                # set 'res' - the result set of matching completionstrings
                # depending on the current mode and command

                # detect if we are completing optional parameter
                arguments_until_now = params[:localpos].split(' ')
                all_optionals = True
                logging.debug(str(arguments_until_now))
                for a in arguments_until_now:
                    logging.debug(a)
                    if a and not a.startswith('-'):
                        all_optionals = False
                # complete optional parameter if
                # 1. all arguments prior to current position are optional
                # 2. the parameter starts with '-' or we are at its beginning
                if all_optionals:
                    myarg = arguments_until_now[-1]
                    start_myarg = params.rindex(myarg)
                    beforeme = params[:start_myarg]
                    # set up local stringlist completer
                    # and let it complete for given list of options
                    localcompleter = ArgparseOptionCompleter(parser)
                    localres = localcompleter.complete(myarg, len(myarg))
                    res = [(
                        beforeme + c, p + start_myarg) for (c, p) in localres]

                # global
                elif cmd == 'search':
                    res = self._querycompleter.complete(params, localpos)
                elif cmd == 'help':
                    res = self._commandnamecompleter.complete(params, localpos)
                elif cmd in ['compose']:
                    res = self._contactscompleter.complete(params, localpos)
                # search
                elif self.mode == 'search' and cmd == 'refine':
                    res = self._querycompleter.complete(params, localpos)
                elif self.mode == 'search' and cmd in ['tag', 'retag', 'untag',
                                                       'toggletags']:
                    localcomp = MultipleSelectionCompleter(self._tagcompleter,
                                                           separator=',')
                    res = localcomp.complete(params, localpos)
                elif self.mode == 'search' and cmd == 'toggletag':
                    localcomp = MultipleSelectionCompleter(self._tagcompleter,
                                                           separator=' ')
                    res = localcomp.complete(params, localpos)
                # envelope
                elif self.mode == 'envelope' and cmd == 'set':
                    plist = params.split(' ', 1)
                    if len(plist) == 1:  # complete from header keys
                        localprefix = params
                        headers = ['Subject', 'To', 'Cc', 'Bcc', 'In-Reply-To',
                                   'From']
                        localcompleter = StringlistCompleter(headers)
                        localres = localcompleter.complete(
                            localprefix, localpos)
                        res = [(c, p + 6) for (c, p) in localres]
                    else:  # must have 2 elements
                        header, params = plist
                        localpos = localpos - (len(header) + 1)
                        if header.lower() in ['to', 'cc', 'bcc']:
                            res = self._contactscompleter.complete(params,
                                                                   localpos)
                        elif header.lower() == 'from':
                            res = self._accountscompleter.complete(params,
                                                                   localpos)

                        # prepend 'set ' + header and correct position
                        def f((completed, pos)):
                            return ('%s %s' % (header, completed),
                                    pos + len(header) + 1)
                        res = map(f, res)
                        logging.debug(res)

                elif self.mode == 'envelope' and cmd == 'unset':
                    plist = params.split(' ', 1)
                    if len(plist) == 1:  # complete from header keys
                        localprefix = params
                        buf = self.currentbuffer
                        if buf:
                            if isinstance(buf, EnvelopeBuffer):
                                available = buf.envelope.headers.keys()
                                localcompleter = StringlistCompleter(available)
                                localres = localcompleter.complete(localprefix,
                                                                   localpos)
                                res = [(c, p + 6) for (c, p) in localres]

                elif self.mode == 'envelope' and cmd == 'attach':
                    res = self._pathcompleter.complete(params, localpos)
                elif self.mode == 'envelope' and cmd in ['sign', 'togglesign']:
                    res = self._secretkeyscompleter.complete(params, localpos)
                elif self.mode == 'envelope' and cmd in ['encrypt',
                                                         'rmencrypt',
                                                         'toggleencrypt']:
                    res = self._publickeyscompleter.complete(params, localpos)
                # thread
                elif self.mode == 'thread' and cmd == 'save':
                    res = self._pathcompleter.complete(params, localpos)
                elif self.mode == 'thread' and cmd in ['fold', 'unfold',
                                                       'togglesource',
                                                       'toggleheaders']:
                    res = self._querycompleter.complete(params, localpos)
                elif self.mode == 'thread' and cmd in ['tag', 'retag', 'untag',
                                                       'toggletags']:
                    localcomp = MultipleSelectionCompleter(self._tagcompleter,
                                                           separator=',')
                    res = localcomp.complete(params, localpos)
                elif cmd == 'move':
                    directions = ['up', 'down', 'page up', 'page down']
                    if self.mode == 'thread':
                        directions += ['first', 'last', 'next', 'previous',
                                       'last reply', 'first reply', 'parent',
                                       'next unfolded', 'previous unfolded',
                                       'next sibling', 'previous sibling']
                    localcompleter = StringlistCompleter(directions)
                    res = localcompleter.complete(params, localpos)

                # prepend cmd and correct position
                res = [('%s %s' % (cmd, t), p + len(cmd) +
                        1) for (t, p) in res]

        # re-insert whitespaces and correct position
        wso = whitespaceoffset
        res = [(' ' * wso + cmdstr, p + wso) for cmdstr, p in res]
        return res


class CommandLineCompleter(Completer):
    """completes command lines: semicolon separated command strings"""

    def __init__(self, dbman, mode, currentbuffer=None):
        """
        :param dbman: used to look up avaliable tagstrings
        :type dbman: :class:`~alot.db.DBManager`
        :param mode: mode identifier
        :type mode: str
        :param currentbuffer: currently active buffer. If defined, this will be
                              used to dynamically extract possible completion
                              strings
        :type currentbuffer: :class:`~alot.buffers.Buffer`
        """
        self._commandcompleter = CommandCompleter(dbman, mode, currentbuffer)

    def get_context(self, line, pos):
        """
        computes start and end position of substring of line that is the
        command string under given position
        """
        commands = split_commandline(line) + ['']
        i = 0
        start = 0
        end = len(commands[i])
        while pos > end:
            i += 1
            start = end + 1
            end += 1 + len(commands[i])
        return start, end

    def complete(self, line, pos):
        cstart, cend = self.get_context(line, pos)
        before = line[:cstart]
        after = line[cend:]
        cmdstring = line[cstart:cend]
        cpos = pos - cstart

        res = []
        for ccmd, ccpos in self._commandcompleter.complete(cmdstring, cpos):
            newtext = before + ccmd + after
            newpos = pos + (ccpos - cpos)
            res.append((newtext, newpos))
        return res


class PathCompleter(Completer):
    """completion for paths"""
    def complete(self, original, pos):
        if not original:
            return [('~/', 2)]
        prefix = os.path.expanduser(original[:pos])

        def escape(path):
            return path.replace('\\', '\\\\').replace(' ', '\ ')

        def deescape(escaped_path):
            return escaped_path.replace('\\ ', ' ').replace('\\\\', '\\')

        def prep(path):
            escaped_path = escape(path)
            return escaped_path, len(escaped_path)

        return map(prep, glob.glob(deescape(prefix) + '*'))


class CryptoKeyCompleter(StringlistCompleter):
    """completion for gpg keys"""

    def __init__(self, private=False):
        """
        :param private: return private keys
        :type private: bool
        """
        keys = crypto.list_keys(private=private)
        resultlist = []
        for k in keys:
            for s in k.subkeys:
                resultlist.append(s.keyid)
            for u in k.uids:
                resultlist.append(u.email)
        StringlistCompleter.__init__(self, resultlist, match_anywhere=True)

########NEW FILE########
__FILENAME__ = crypto
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import re
import os

from email.generator import Generator
from cStringIO import StringIO
from alot.errors import GPGProblem, GPGCode
from email.mime.multipart import MIMEMultipart
import gpgme


def email_as_string(mail):
    """
    Converts the given message to a string, without mangling "From" lines
    (like as_string() does).

    :param mail: email to convert to string
    :rtype: str
    """
    fp = StringIO()
    g = Generator(fp, mangle_from_=False, maxheaderlen=78)
    g.flatten(mail)
    as_string = RFC3156_canonicalize(fp.getvalue())

    if isinstance(mail, MIMEMultipart):
        # Get the boundary for later
        boundary = mail.get_boundary()

        # Workaround for http://bugs.python.org/issue14983:
        # Insert a newline before the outer mail boundary so that other mail
        # clients can verify the signature when sending an email which contains
        # attachments.
        as_string = re.sub(r'--(\r\n)--' + boundary,
                           '--\g<1>\g<1>--' + boundary,
                           as_string, flags=re.MULTILINE)

    return as_string


def _hash_algo_name(hash_algo):
    """
    Re-implements GPGME's hash_algo_name as long as pygpgme doesn't wrap that
    function.

    :param hash_algo: GPGME hash_algo
    :rtype: str
    """
    mapping = {
        gpgme.MD_MD5: "MD5",
        gpgme.MD_SHA1: "SHA1",
        gpgme.MD_RMD160: "RIPEMD160",
        gpgme.MD_MD2: "MD2",
        gpgme.MD_TIGER: "TIGER192",
        gpgme.MD_HAVAL: "HAVAL",
        gpgme.MD_SHA256: "SHA256",
        gpgme.MD_SHA384: "SHA384",
        gpgme.MD_SHA512: "SHA512",
        gpgme.MD_MD4: "MD4",
        gpgme.MD_CRC32: "CRC32",
        gpgme.MD_CRC32_RFC1510: "CRC32RFC1510",
        gpgme.MD_CRC24_RFC2440: "CRC24RFC2440",
    }
    if hash_algo in mapping:
        return mapping[hash_algo]
    else:
        raise GPGProblem(("Invalid hash_algo passed to hash_algo_name."
                          " Please report this as a bug in alot."),
                         code=GPGCode.INVALID_HASH)


def RFC3156_micalg_from_algo(hash_algo):
    """
    Converts a GPGME hash algorithm name to one conforming to RFC3156.

    GPGME returns hash algorithm names such as "SHA256", but RFC3156 says that
    programs need to use names such as "pgp-sha256" instead.

    :param hash_algo: GPGME hash_algo
    :rtype: str
    """
    # hash_algo will be something like SHA256, but we need pgp-sha256.
    hash_algo = _hash_algo_name(hash_algo)
    return 'pgp-' + hash_algo.lower()


def RFC3156_canonicalize(text):
    """
    Canonicalizes plain text (MIME-encoded usually) according to RFC3156.

    This function works as follows (in that order):

    1. Convert all line endings to \\\\r\\\\n (DOS line endings).
    2. Ensure the text ends with a newline (\\\\r\\\\n).
    3. Encode all occurences of "From " at the beginning of a line
       to "From=20" in order to prevent other mail programs to replace
       this with "> From" (to avoid MBox conflicts) and thus invalidate
       the signature.

    :param text: text to canonicalize (already encoded as quoted-printable)
    :rtype: str
    """
    text = re.sub("\r?\n", "\r\n", text)
    if not text.endswith("\r\n"):
        text += "\r\n"
    text = re.sub("^From ", "From=20", text, flags=re.MULTILINE)
    return text


def get_key(keyid, validate=False, encrypt=False, sign=False):
    """
    Gets a key from the keyring by filtering for the specified keyid, but
    only if the given keyid is specific enough (if it matches multiple
    keys, an exception will be thrown).

    If validate is True also make sure that returned key is not invalid, revoked
    or expired. In addition if encrypt or sign is True also validate that key is
    valid for that action. For example only keys with private key can sign.

    :param keyid: filter term for the keyring (usually a key ID)
    :param validate: validate that returned keyid is valid
    :param encrypt: when validating confirm that returned key can encrypt
    :param sign: when validating confirm that returned key can sign
    :rtype: gpgme.Key
    """
    ctx = gpgme.Context()
    try:
        key = ctx.get_key(keyid)
        if validate:
            validate_key(key, encrypt=encrypt, sign=sign)
    except gpgme.GpgmeError as e:
        if e.code == gpgme.ERR_AMBIGUOUS_NAME:
            # When we get here it means there were multiple keys returned by gpg
            # for given keyid. Unfortunately gpgme returns invalid and expired
            # keys together with valid keys. If only one key is valid for given
            # operation maybe we can still return it instead of raising
            # exception
            keys = list_keys(hint=keyid)
            valid_key = None
            for k in keys:
                try:
                    validate_key(k, encrypt=encrypt, sign=sign)
                except GPGProblem:
                    # if the key is invalid for given action skip it
                    continue

                if valid_key:
                    # we have already found one valid key and now we find
                    # another? We really received an ambiguous keyid
                    raise GPGProblem(("More than one key found matching " +
                                      "this filter. Please be more " +
                                      "specific (use a key ID like " +
                                      "4AC8EE1D)."),
                                     code=GPGCode.AMBIGUOUS_NAME)
                valid_key = k

            if not valid_key:
                # there were multiple keys found but none of them are valid for
                # given action (we don't have private key, they are expired etc)
                raise GPGProblem("Can not find usable key for \'" + keyid + "\'.",
                                 code=GPGCode.NOT_FOUND)
            return valid_key
        elif e.code == gpgme.ERR_INV_VALUE or e.code == gpgme.ERR_EOF:
            raise GPGProblem("Can not find key for \'" + keyid + "\'.",
                             code=GPGCode.NOT_FOUND)
        else:
            raise e
    return key


def list_keys(hint=None, private=False):
    """
    Returns a list of all keys containing keyid.

    :param keyid: The part we search for
    :param private: Whether secret keys are listed
    :rtype: list
    """
    ctx = gpgme.Context()
    return ctx.keylist(hint, private)


def detached_signature_for(plaintext_str, key=None):
    """
    Signs the given plaintext string and returns the detached signature.

    A detached signature in GPG speak is a separate blob of data containing
    a signature for the specified plaintext.

    :param plaintext_str: text to sign
    :param key: gpgme_key_t object representing the key to use
    :rtype: tuple of gpgme.NewSignature array and str
    """
    ctx = gpgme.Context()
    ctx.armor = True
    if key is not None:
        ctx.signers = [key]
    plaintext_data = StringIO(plaintext_str)
    signature_data = StringIO()
    sigs = ctx.sign(plaintext_data, signature_data, gpgme.SIG_MODE_DETACH)
    signature_data.seek(0, os.SEEK_SET)
    signature = signature_data.read()
    return sigs, signature


def encrypt(plaintext_str, keys=None):
    """
    Encrypts the given plaintext string and returns a PGP/MIME compatible
    string

    :param plaintext_str: the mail to encrypt
    :param key: gpgme_key_t object representing the key to use
    :rtype: a string holding the encrypted mail
    """
    plaintext_data = StringIO(plaintext_str)
    encrypted_data = StringIO()
    ctx = gpgme.Context()
    ctx.armor = True
    ctx.encrypt(keys, gpgme.ENCRYPT_ALWAYS_TRUST, plaintext_data,
                encrypted_data)
    encrypted_data.seek(0, os.SEEK_SET)
    encrypted = encrypted_data.read()
    return encrypted


def verify_detached(message, signature):
    '''Verifies whether the message is authentic by checking the
    signature.

    :param message: the message as `str`
    :param signature: a `str` containing an OpenPGP signature
    :returns: a list of :class:`gpgme.Signature`
    :raises: :class:`~alot.errors.GPGProblem` if the verification fails
    '''
    message_data = StringIO(message)
    signature_data = StringIO(signature)
    ctx = gpgme.Context()
    try:
        return ctx.verify(signature_data, message_data, None)
    except gpgme.GpgmeError as e:
        raise GPGProblem(e.message, code=e.code)


def decrypt_verify(encrypted):
    '''Decrypts the given ciphertext string and returns both the
    signatures (if any) and the plaintext.

    :param encrypted: the mail to decrypt
    :returns: a tuple (sigs, plaintext) with sigs being a list of a
              :class:`gpgme.Signature` and plaintext is a `str` holding
              the decrypted mail
    :raises: :class:`~alot.errors.GPGProblem` if the decryption fails
    '''
    encrypted_data = StringIO(encrypted)
    plaintext_data = StringIO()
    ctx = gpgme.Context()
    try:
        sigs = ctx.decrypt_verify(encrypted_data, plaintext_data)
    except gpgme.GpgmeError as e:
        raise GPGProblem(e.message, code=e.code)

    plaintext_data.seek(0, os.SEEK_SET)
    return sigs, plaintext_data.read()


def hash_key(key):
    """
    Returns a hash of the given key. This is a workaround for
    https://bugs.launchpad.net/pygpgme/+bug/1089865
    and can be removed if the missing feature is added to pygpgme

    :param key: the key we want a hash of
    :rtype: a has of the key as string
    """
    hash_str = ""
    for tmp_key in key.subkeys:
        hash_str += tmp_key.keyid
    return hash_str


def validate_key(key, sign=False, encrypt=False):
    if key.revoked:
        raise GPGProblem("The key \"" + key.uids[0].uid + "\" is revoked.",
                         code=GPGCode.KEY_REVOKED)
    elif key.expired:
        raise GPGProblem("The key \"" + key.uids[0].uid + "\" is expired.",
                         code=GPGCode.KEY_EXPIRED)
    elif key.invalid:
        raise GPGProblem("The key \"" + key.uids[0].uid + "\" is invalid.",
                         code=GPGCode.KEY_INVALID)
    if encrypt and not key.can_encrypt:
        raise GPGProblem("The key \"" + key.uids[0].uid + "\" can not " +
                         "encrypt.", code=GPGCode.KEY_CANNOT_ENCRYPT)
    if sign and not key.can_sign:
        raise GPGProblem("The key \"" + key.uids[0].uid + "\" can not sign.",
                         code=GPGCode.KEY_CANNOT_SIGN)

########NEW FILE########
__FILENAME__ = attachment
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import os
import tempfile
import email.charset as charset
from email.header import Header
from copy import deepcopy
charset.add_charset('utf-8', charset.QP, charset.QP, 'utf-8')
import alot.helper as helper
from alot.helper import string_decode

from alot.db.utils import decode_header


class Attachment(object):

    """represents a mail attachment"""

    def __init__(self, emailpart):
        """
        :param emailpart: a non-multipart email that is the attachment
        :type emailpart: :class:`email.message.Message`
        """
        self.part = emailpart

    def __str__(self):
        desc = '%s:%s (%s)' % (self.get_content_type(),
                               self.get_filename(),
                               helper.humanize_size(self.get_size()))
        return string_decode(desc)

    def get_filename(self):
        """
        return name of attached file.
        If the content-disposition header contains no file name,
        this returns `None`
        """
        fname = self.part.get_filename()
        if fname:
            extracted_name = decode_header(fname)
            if extracted_name:
                return os.path.basename(extracted_name)
        return None

    def get_content_type(self):
        """mime type of the attachment part"""
        ctype = self.part.get_content_type()
        # replace underspecified mime description by a better guess
        if ctype in ['octet/stream', 'application/octet-stream']:
            ctype = helper.guess_mimetype(self.get_data())
        return ctype

    def get_size(self):
        """returns attachments size in bytes"""
        return len(self.part.get_payload())

    def save(self, path):
        """
        save the attachment to disk. Uses :meth:`~get_filename` in case path
        is a directory
        """
        filename = self.get_filename()
        path = os.path.expanduser(path)
        if os.path.isdir(path):
            if filename:
                basename = os.path.basename(filename)
                FILE = open(os.path.join(path, basename), "w")
            else:
                FILE = tempfile.NamedTemporaryFile(delete=False, dir=path)
        else:
            FILE = open(path, "w")  # this throws IOErrors for invalid path
        self.write(FILE)
        FILE.close()
        return FILE.name

    def write(self, fhandle):
        """writes content to a given filehandle"""
        fhandle.write(self.get_data())

    def get_data(self):
        """return data blob from wrapped file"""
        return self.part.get_payload(decode=True)

    def get_mime_representation(self):
        """returns mime part that constitutes this attachment"""
        part = deepcopy(self.part)
        cd = self.part['Content-Disposition']
        del part['Content-Disposition']
        part['Content-Disposition'] = Header(cd, maxlinelen=78,
                                             header_name='Content-Disposition')
        return part

########NEW FILE########
__FILENAME__ = envelope
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import os
import email
import re
import glob
import email.charset as charset
charset.add_charset('utf-8', charset.QP, charset.QP, 'utf-8')
from email.encoders import encode_7or8bit
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from alot import __version__
import logging
import alot.helper as helper
import alot.crypto as crypto
import gpgme
from alot.settings import settings
from alot.errors import GPGProblem, GPGCode

from .attachment import Attachment
from .utils import encode_header


class Envelope(object):

    """a message that is not yet sent and still editable.
    It holds references to unencoded! body text and mail headers among other
    things.  Envelope implements the python container API for easy access of
    header values.  So `e['To']`, `e['To'] = 'foo@bar.baz'` and
    'e.get_all('To')' would work for an envelope `e`..
    """

    headers = None
    """
    dict containing the mail headers (a list of strings for each header key)
    """
    body = None
    """mail body as unicode string"""
    tmpfile = None
    """template text for initial content"""
    attachments = None
    """list of :class:`Attachments <alot.db.attachment.Attachment>`"""
    tags = []
    """tags to add after successful sendout"""

    def __init__(
        self, template=None, bodytext=None, headers=None, attachments=[],
            sign=False, sign_key=None, encrypt=False, tags=[]):
        """
        :param template: if not None, the envelope will be initialised by
                         :meth:`parsing <parse_template>` this string before
                         setting any other values given to this constructor.
        :type template: str
        :param bodytext: text used as body part
        :type bodytext: str
        :param headers: unencoded header values
        :type headers: dict (str -> [unicode])
        :param attachments: file attachments to include
        :type attachments: list of :class:`~alot.db.attachment.Attachment`
        :param tags: tags to add after successful sendout and saving this msg
        :type tags: list of str
        """
        logging.debug('TEMPLATE: %s' % template)
        if template:
            self.parse_template(template)
            logging.debug('PARSED TEMPLATE: %s' % template)
            logging.debug('BODY: %s' % self.body)
        self.body = bodytext or u''
        self.headers = headers or {}
        self.attachments = list(attachments)
        self.sign = sign
        self.sign_key = sign_key
        self.encrypt = encrypt
        self.encrypt_keys = {}
        self.tags = tags  # tags to add after successful sendout
        self.sent_time = None
        self.modified_since_sent = False
        self.sending = False  # semaphore to avoid accidental double sendout

    def __str__(self):
        return "Envelope (%s)\n%s" % (self.headers, self.body)

    def __setitem__(self, name, val):
        """setter for header values. this allows adding header like so:

        >>> envelope['Subject'] = u'sm\xf8rebr\xf8d'
        """
        if name not in self.headers:
            self.headers[name] = []
        self.headers[name].append(val)

        if self.sent_time:
            self.modified_since_sent = True

    def __getitem__(self, name):
        """getter for header values.
        :raises: KeyError if undefined
        """
        return self.headers[name][0]

    def __delitem__(self, name):
        del(self.headers[name])

        if self.sent_time:
            self.modified_since_sent = True

    def __contains__(self, name):
        return self.headers.__contains__(name)

    def get(self, key, fallback=None):
        """secure getter for header values that allows specifying a `fallback`
        return string (defaults to None). This returns the first matching value
        and doesn't raise KeyErrors"""
        if key in self.headers:
            value = self.headers[key][0]
        else:
            value = fallback
        return value

    def get_all(self, key, fallback=[]):
        """returns all header values for given key"""
        if key in self.headers:
            value = self.headers[key]
        else:
            value = fallback
        return value

    def add(self, key, value):
        """add header value"""
        if key not in self.headers:
            self.headers[key] = []
        self.headers[key].append(value)

        if self.sent_time:
            self.modified_since_sent = True

    def attach(self, attachment, filename=None, ctype=None):
        """
        attach a file

        :param attachment: File to attach, given as
            :class:`~alot.db.attachment.Attachment` object or path to a file.
        :type attachment: :class:`~alot.db.attachment.Attachment` or str
        :param filename: filename to use in content-disposition.
            Will be ignored if `path` matches multiple files
        :param ctype: force content-type to be used for this attachment
        :type ctype: str
        """

        if isinstance(attachment, Attachment):
            self.attachments.append(attachment)
        elif isinstance(attachment, basestring):
            path = os.path.expanduser(attachment)
            part = helper.mimewrap(path, filename, ctype)
            self.attachments.append(Attachment(part))
        else:
            raise TypeError('attach accepts an Attachment or str')

        if self.sent_time:
            self.modified_since_sent = True

    def construct_mail(self):
        """
        compiles the information contained in this envelope into a
        :class:`email.Message`.
        """
        # Build body text part. To properly sign/encrypt messages later on, we
        # convert the text to its canonical format (as per RFC 2015).
        canonical_format = self.body.encode('utf-8')
        canonical_format = canonical_format.replace('\\t', ' ' * 4)
        textpart = MIMEText(canonical_format, 'plain', 'utf-8')

        # wrap it in a multipart container if necessary
        if self.attachments:
            inner_msg = MIMEMultipart()
            inner_msg.attach(textpart)
            # add attachments
            for a in self.attachments:
                inner_msg.attach(a.get_mime_representation())
        else:
            inner_msg = textpart

        if self.sign:
            plaintext = crypto.email_as_string(inner_msg)
            logging.debug('signing plaintext: ' + plaintext)

            try:
                signatures, signature_str = crypto.detached_signature_for(
                    plaintext, self.sign_key)
                if len(signatures) != 1:
                    raise GPGProblem("Could not sign message (GPGME "
                                     "did not return a signature)",
                                     code=GPGCode.KEY_CANNOT_SIGN)
            except gpgme.GpgmeError as e:
                if e.code == gpgme.ERR_BAD_PASSPHRASE:
                    # If GPG_AGENT_INFO is unset or empty, the user just does
                    # not have gpg-agent running (properly).
                    if os.environ.get('GPG_AGENT_INFO', '').strip() == '':
                        msg = "Got invalid passphrase and GPG_AGENT_INFO\
                                not set. Please set up gpg-agent."
                        raise GPGProblem(msg, code=GPGCode.BAD_PASSPHRASE)
                    else:
                        raise GPGProblem("Bad passphrase. Is gpg-agent "
                                         "running?",
                                         code=GPGCode.BAD_PASSPHRASE)
                raise GPGProblem(str(e), code=GPGCode.KEY_CANNOT_SIGN)

            micalg = crypto.RFC3156_micalg_from_algo(signatures[0].hash_algo)
            unencrypted_msg = MIMEMultipart('signed', micalg=micalg,
                                            protocol=
                                            'application/pgp-signature')

            # wrap signature in MIMEcontainter
            stype = 'pgp-signature; name="signature.asc"'
            signature_mime = MIMEApplication(_data=signature_str,
                                             _subtype=stype,
                                             _encoder=encode_7or8bit)
            signature_mime['Content-Description'] = 'signature'
            signature_mime.set_charset('us-ascii')

            # add signed message and signature to outer message
            unencrypted_msg.attach(inner_msg)
            unencrypted_msg.attach(signature_mime)
            unencrypted_msg['Content-Disposition'] = 'inline'
        else:
            unencrypted_msg = inner_msg

        if self.encrypt:
            plaintext = crypto.email_as_string(unencrypted_msg)
            logging.debug('encrypting plaintext: ' + plaintext)

            try:
                encrypted_str = crypto.encrypt(plaintext,
                                               self.encrypt_keys.values())
            except gpgme.GpgmeError as e:
                raise GPGProblem(str(e), code=GPGCode.KEY_CANNOT_ENCRYPT)

            outer_msg = MIMEMultipart('encrypted',
                                      protocol='application/pgp-encrypted')

            version_str = 'Version: 1'
            encryption_mime = MIMEApplication(_data=version_str,
                                              _subtype='pgp-encrypted',
                                              _encoder=encode_7or8bit)
            encryption_mime.set_charset('us-ascii')

            encrypted_mime = MIMEApplication(_data=encrypted_str,
                                             _subtype='octet-stream',
                                             _encoder=encode_7or8bit)
            encrypted_mime.set_charset('us-ascii')
            outer_msg.attach(encryption_mime)
            outer_msg.attach(encrypted_mime)

        else:
            outer_msg = unencrypted_msg

        headers = self.headers.copy()
        # add Message-ID
        if 'Message-ID' not in headers:
            headers['Message-ID'] = [email.Utils.make_msgid()]

        if 'User-Agent' in headers:
            uastring_format = headers['User-Agent'][0]
        else:
            uastring_format = settings.get('user_agent').strip()
        uastring = uastring_format.format(version=__version__)
        if uastring:
            headers['User-Agent'] = [uastring]

        # copy headers from envelope to mail
        for k, vlist in headers.items():
            for v in vlist:
                outer_msg[k] = encode_header(k, v)

        return outer_msg

    def parse_template(self, tmp, reset=False, only_body=False):
        """parses a template or user edited string to fills this envelope.

        :param tmp: the string to parse.
        :type tmp: str
        :param reset: remove previous envelope content
        :type reset: bool
        """
        logging.debug('GoT: """\n%s\n"""' % tmp)

        if self.sent_time:
            self.modified_since_sent = True

        if only_body:
            self.body = tmp
        else:
            m = re.match('(?P<h>([a-zA-Z0-9_-]+:.+\n)*)\n?(?P<b>(\s*.*)*)',
                         tmp)
            assert m

            d = m.groupdict()
            headertext = d['h']
            self.body = d['b']

            # remove existing content
            if reset:
                self.headers = {}

            # go through multiline, utf-8 encoded headers
            # we decode the edited text ourselves here as
            # email.message_from_file can't deal with raw utf8 header values
            key = value = None
            for line in headertext.splitlines():
                if re.match('[a-zA-Z0-9_-]+:', line):  # new k/v pair
                    if key and value:  # save old one from stack
                        self.add(key, value)  # save
                    key, value = line.strip().split(':', 1)  # parse new pair
                    # strip spaces, otherwise we end up having " foo" as value
                    # of "Subject: foo"
                    value = value.strip()
                elif key and value:  # append new line without key prefix
                    value += line
            if key and value:  # save last one if present
                self.add(key, value)

            # interpret 'Attach' pseudo header
            if 'Attach' in self:
                to_attach = []
                for line in self.get_all('Attach'):
                    gpath = os.path.expanduser(line.strip())
                    to_attach += filter(os.path.isfile, glob.glob(gpath))
                logging.debug('Attaching: %s' % to_attach)
                for path in to_attach:
                    self.attach(path)
                del(self['Attach'])

########NEW FILE########
__FILENAME__ = errors
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file


class DatabaseError(Exception):
    pass


class DatabaseROError(DatabaseError):

    """cannot write to read-only database"""
    pass


class DatabaseLockedError(DatabaseError):

    """cannot write to locked index"""
    pass


class NonexistantObjectError(DatabaseError):

    """requested thread or message does not exist in the index"""
    pass

########NEW FILE########
__FILENAME__ = manager
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
from notmuch import Database, NotmuchError, XapianError
import notmuch
import multiprocessing
import logging
import sys
import os
import errno
import signal
from twisted.internet import reactor

from collections import deque

from message import Message
from alot.settings import settings
from thread import Thread
from errors import DatabaseError
from errors import DatabaseLockedError
from errors import DatabaseROError
from errors import NonexistantObjectError
from alot.db import DB_ENC
from alot.db.utils import is_subdir_of



class FillPipeProcess(multiprocessing.Process):
    def __init__(self, it, stdout, stderr, pipe, fun=(lambda x: x)):
        multiprocessing.Process.__init__(self)
        self.it = it
        self.pipe = pipe[1]
        self.fun = fun
        self.keep_going = True
        self.stdout = stdout
        self.stderr = stderr

    def handle_sigterm(self, signo, frame):
        # this is used to suppress any EINTR errors at interpreter
        # shutdown
        self.keep_going = False

        # raises SystemExit to shut down the interpreter from the
        # signal handler
        sys.exit()

    def run(self):
        # replace filedescriptors 1 and 2 (stdout and stderr) with
        # pipes to the parent process
        os.dup2(self.stdout, 1)
        os.dup2(self.stderr, 2)

        # register a signal handler for SIGTERM
        signal.signal(signal.SIGTERM, self.handle_sigterm)

        for a in self.it:
            try:
                self.pipe.send(self.fun(a))
            except IOError as e:
                # suppress spurious EINTR errors at interpreter
                # shutdown
                if e.errno != errno.EINTR or self.keep_going:
                    raise

        self.pipe.close()


class DBManager(object):
    """
    Keeps track of your index parameters, maintains a write-queue and
    lets you look up threads and messages directly to the persistent wrapper
    classes.
    """
    _sort_orders = {
        'oldest_first': notmuch.database.Query.SORT.OLDEST_FIRST,
        'newest_first': notmuch.database.Query.SORT.NEWEST_FIRST,
        'unsorted': notmuch.database.Query.SORT.UNSORTED,
        'message_id': notmuch.database.Query.SORT.MESSAGE_ID,
    }
    """constants representing sort orders"""

    def __init__(self, path=None, ro=False):
        """
        :param path: absolute path to the notmuch index
        :type path: str
        :param ro: open the index in read-only mode
        :type ro: bool
        """
        self.ro = ro
        self.path = path
        self.writequeue = deque([])
        self.processes = []

    def flush(self):
        """
        write out all queued write-commands in order, each one in a separate
        :meth:`atomic <notmuch.Database.begin_atomic>` transaction.

        If this fails the current action is rolled back, stays in the write
        queue and an exception is raised.
        You are responsible to retry flushing at a later time if you want to
        ensure that the cached changes are applied to the database.

        :exception: :exc:`~errors.DatabaseROError` if db is opened read-only
        :exception: :exc:`~errors.DatabaseLockedError` if db is locked
        """
        if self.ro:
            raise DatabaseROError()
        if self.writequeue:
            # read notmuch's config regarding imap flag synchronization
            sync = settings.get_notmuch_setting('maildir', 'synchronize_flags')

            # go through writequeue entries
            while self.writequeue:
                current_item = self.writequeue.popleft()
                logging.debug('write-out item: %s' % str(current_item))

                # watch out for notmuch errors to re-insert current_item
                # to the queue on errors
                try:
                    # the first two coordinants are cnmdname and post-callback
                    cmd, afterwards = current_item[:2]
                    logging.debug('cmd created')

                    # aquire a writeable db handler
                    try:
                        mode = Database.MODE.READ_WRITE
                        db = Database(path=self.path, mode=mode)
                    except NotmuchError:
                        raise DatabaseLockedError()
                    logging.debug('got write lock')

                    # make this a transaction
                    db.begin_atomic()
                    logging.debug('got atomic')

                    if cmd == 'add':
                        logging.debug('add')
                        path, tags = current_item[2:]
                        msg, status = db.add_message(path,
                                                     sync_maildir_flags=sync)
                        logging.debug('added msg')
                        msg.freeze()
                        logging.debug('freeze')
                        for tag in tags:
                            msg.add_tag(tag.encode(DB_ENC),
                                        sync_maildir_flags=sync)
                        logging.debug('added tags ')
                        msg.thaw()
                        logging.debug('thaw')

                    elif cmd == 'remove':
                        path = current_item[2]
                        db.remove_message(path)

                    else:  # tag/set/untag
                        querystring, tags = current_item[2:]
                        query = db.create_query(querystring)
                        for msg in query.search_messages():
                            msg.freeze()
                            if cmd == 'tag':
                                for tag in tags:
                                    msg.add_tag(tag.encode(DB_ENC),
                                                sync_maildir_flags=sync)
                            if cmd == 'set':
                                msg.remove_all_tags()
                                for tag in tags:
                                    msg.add_tag(tag.encode(DB_ENC),
                                                sync_maildir_flags=sync)
                            elif cmd == 'untag':
                                for tag in tags:
                                    msg.remove_tag(tag.encode(DB_ENC),
                                                   sync_maildir_flags=sync)
                            msg.thaw()

                    logging.debug('ended atomic')
                    # end transaction and reinsert queue item on error
                    if db.end_atomic() != notmuch.STATUS.SUCCESS:
                        raise DatabaseError('end_atomic failed')
                    logging.debug('ended atomic')

                    # close db
                    db.close()
                    logging.debug('closed db')

                    # call post-callback
                    if callable(afterwards):
                        logging.debug(str(afterwards))
                        afterwards()
                        logging.debug('called callback')

                # re-insert item to the queue upon Xapian/NotmuchErrors
                except (XapianError, NotmuchError) as e:
                    logging.exception(e)
                    self.writequeue.appendleft(current_item)
                    raise DatabaseError(unicode(e))
                except DatabaseLockedError as e:
                    logging.debug('index temporarily locked')
                    self.writequeue.appendleft(current_item)
                    raise e
                logging.debug('flush finished')

    def kill_search_processes(self):
        """
        terminate all search processes that originate from
        this managers :meth:`get_threads`.
        """
        for p in self.processes:
            p.terminate()
        self.processes = []

    def tag(self, querystring, tags, afterwards=None, remove_rest=False):
        """
        add tags to messages matching `querystring`.
        This appends a tag operation to the write queue and raises
        :exc:`~errors.DatabaseROError` if in read only mode.

        :param querystring: notmuch search string
        :type querystring: str
        :param tags: a list of tags to be added
        :type tags: list of str
        :param afterwards: callback that gets called after successful
                           application of this tagging operation
        :type afterwards: callable
        :param remove_rest: remove tags from matching messages before tagging
        :type remove_rest: bool
        :exception: :exc:`~errors.DatabaseROError`

        .. note::
            This only adds the requested operation to the write queue.
            You need to call :meth:`DBManager.flush` to actually write out.
        """
        if self.ro:
            raise DatabaseROError()
        if remove_rest:
            self.writequeue.append(('set', afterwards, querystring, tags))
        else:
            self.writequeue.append(('tag', afterwards, querystring, tags))

    def untag(self, querystring, tags, afterwards=None):
        """
        removes tags from messages that match `querystring`.
        This appends an untag operation to the write queue and raises
        :exc:`~errors.DatabaseROError` if in read only mode.

        :param querystring: notmuch search string
        :type querystring: str
        :param tags: a list of tags to be added
        :type tags: list of str
        :param afterwards: callback that gets called after successful
                           application of this tagging operation
        :type afterwards: callable
        :exception: :exc:`~errors.DatabaseROError`

        .. note::
            This only adds the requested operation to the write queue.
            You need to call :meth:`DBManager.flush` to actually write out.
        """
        if self.ro:
            raise DatabaseROError()
        self.writequeue.append(('untag', afterwards, querystring, tags))

    def count_messages(self, querystring):
        """returns number of messages that match `querystring`"""
        return self.query(querystring).count_messages()

    def count_threads(self, querystring):
        """returns number of threads that match `querystring`"""
        return self.query(querystring).count_threads()

    def search_thread_ids(self, querystring):
        """
        returns the ids of all threads that match the `querystring`
        This copies! all integer thread ids into an new list.

        :returns: list of str
        """

        return self.query_threaded(querystring)

    def _get_notmuch_thread(self, tid):
        """returns :class:`notmuch.database.Thread` with given id"""
        query = self.query('thread:' + tid)
        try:
            return query.search_threads().next()
        except StopIteration:
            errmsg = 'no thread with id %s exists!' % tid
            raise NonexistantObjectError(errmsg)

    def get_thread(self, tid):
        """returns :class:`Thread` with given thread id (str)"""
        return Thread(self, self._get_notmuch_thread(tid))

    def _get_notmuch_message(self, mid):
        """returns :class:`notmuch.database.Message` with given id"""
        mode = Database.MODE.READ_ONLY
        db = Database(path=self.path, mode=mode)
        try:
            return db.find_message(mid)
        except:
            errmsg = 'no message with id %s exists!' % mid
            raise NonexistantObjectError(errmsg)

    def get_message(self, mid):
        """returns :class:`Message` with given message id (str)"""
        return Message(self, self._get_notmuch_message(mid))

    def get_all_tags(self):
        """
        returns all tagsstrings used in the database
        :rtype: list of str
        """
        db = Database(path=self.path)
        return [t for t in db.get_all_tags()]

    def async(self, cbl, fun):
        """
        return a pair (pipe, process) so that the process writes
        `fun(a)` to the pipe for each element `a` in the iterable returned
        by the callable `cbl`.

        :param cbl: a function returning something iterable
        :type cbl: callable
        :param fun: an unary translation function
        :type fun: callable
        :rtype: (:class:`multiprocessing.Pipe`,
                :class:`multiprocessing.Process`)
        """
        # create two unix pipes to redirect the workers stdout and
        # stderr
        stdout = os.pipe()
        stderr = os.pipe()

        # create a multiprocessing pipe for the results
        pipe = multiprocessing.Pipe(False)
        receiver, sender = pipe

        process = FillPipeProcess(cbl(), stdout[1], stderr[1], pipe, fun)
        process.start()
        self.processes.append(process)
        logging.debug('Worker process {0} spawned'.format(process.pid))

        def threaded_wait():
            # wait(2) for the process to die
            process.join()

            if process.exitcode < 0:
                msg = 'received signal {0}'.format(-process.exitcode)
            elif process.exitcode > 0:
                msg = 'returned error code {0}'.format(process.exitcode)
            else:
                msg = 'exited successfully'

            logging.debug('Worker process {0} {1}'.format(process.pid, msg))
            self.processes.remove(process)

        # spawn a thread to collect the worker process once it dies
        # preventing it from hanging around as zombie
        reactor.callInThread(threaded_wait)

        def threaded_reader(prefix, fd):
            with os.fdopen(fd) as handle:
                for line in handle:
                    logging.debug('Worker process {0} said on {1}: {2}'.format(
                            process.pid, prefix, line.rstrip()))

        # spawn two threads that read from the stdout and stderr pipes
        # and write anything that appears there to the log
        reactor.callInThread(threaded_reader, 'stdout', stdout[0])
        os.close(stdout[1])
        reactor.callInThread(threaded_reader, 'stderr', stderr[0])
        os.close(stderr[1])

        # closing the sending end in this (receiving) process guarantees
        # that here the apropriate EOFError is raised upon .recv in the walker
        sender.close()
        return receiver, process

    def get_threads(self, querystring, sort='newest_first'):
        """
        asynchronously look up thread ids matching `querystring`.

        :param querystring: The query string to use for the lookup
        :type querystring: str.
        :param sort: Sort order. one of ['oldest_first', 'newest_first',
                     'message_id', 'unsorted']
        :type query: str
        :returns: a pipe together with the process that asynchronously
                  writes to it.
        :rtype: (:class:`multiprocessing.Pipe`,
                :class:`multiprocessing.Process`)
        """
        assert sort in self._sort_orders.keys()
        q = self.query(querystring)
        q.set_sort(self._sort_orders[sort])
        return self.async(q.search_threads, (lambda a: a.get_thread_id()))

    def query(self, querystring):
        """
        creates :class:`notmuch.Query` objects on demand

        :param querystring: The query string to use for the lookup
        :type query: str.
        :returns: :class:`notmuch.Query` -- the query object.
        """
        mode = Database.MODE.READ_ONLY
        db = Database(path=self.path, mode=mode)
        return db.create_query(querystring)

    def add_message(self, path, tags=[], afterwards=None):
        """
        Adds a file to the notmuch index.

        :param path: path to the file
        :type path: str
        :param tags: tagstrings to add
        :type tags: list of str
        :param afterwards: callback to trigger after adding
        :type afterwards: callable or None
        """
        if self.ro:
            raise DatabaseROError()
        if not is_subdir_of(path,self.path):
            msg = 'message path %s ' % path
            msg += ' is not below notmuchs '
            msg += 'root path (%s)' % self.path
            raise DatabaseError(msg)
        else:
            self.writequeue.append(('add', afterwards, path, tags))

    def remove_message(self, message, afterwards=None):
        """
        Remove a message from the notmuch index

        :param message: message to remove
        :type message: :class:`Message`
        :param afterwards: callback to trigger after removing
        :type afterwards: callable or None
        """
        if self.ro:
            raise DatabaseROError()
        path = message.get_filename()
        self.writequeue.append(('remove', afterwards, path))

########NEW FILE########
__FILENAME__ = message
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import email
from datetime import datetime
import email.charset as charset
charset.add_charset('utf-8', charset.QP, charset.QP, 'utf-8')
from notmuch import NullPointerError

import alot.helper as helper
from alot.settings import settings

from .utils import extract_headers, extract_body, message_from_file
from alot.db.utils import decode_header
from .attachment import Attachment


class Message(object):

    """
    a persistent notmuch message object.
    It it uses a :class:`~alot.db.DBManager` for cached manipulation
    and lazy lookups.
    """
    def __init__(self, dbman, msg, thread=None):
        """
        :param dbman: db manager that is used for further lookups
        :type dbman: alot.db.DBManager
        :param msg: the wrapped message
        :type msg: notmuch.database.Message
        :param thread: this messages thread (will be looked up later if `None`)
        :type thread: :class:`~alot.db.Thread` or `None`
        """
        self._dbman = dbman
        self._id = msg.get_message_id()
        self._thread_id = msg.get_thread_id()
        self._thread = thread
        casts_date = lambda: datetime.fromtimestamp(msg.get_date())
        self._datetime = helper.safely_get(casts_date,
                                           ValueError, None)
        self._filename = msg.get_filename()
        author = helper.safely_get(lambda: msg.get_header('From'),
                                   NullPointerError)
        self._from = decode_header(author)
        self._email = None  # will be read upon first use
        self._attachments = None  # will be read upon first use
        self._tags = set(msg.get_tags())

    def __str__(self):
        """prettyprint the message"""
        aname, aaddress = self.get_author()
        if not aname:
            aname = aaddress
        return "%s (%s)" % (aname, self.get_datestring())

    def __hash__(self):
        """needed for sets of Messages"""
        return hash(self._id)

    def __cmp__(self, other):
        """needed for Message comparison"""
        res = cmp(self.get_message_id(), other.get_message_id())
        return res

    def get_email(self):
        """returns :class:`email.Message` for this message"""
        path = self.get_filename()
        warning = "Subject: Caution!\n"\
                  "Message file is no longer accessible:\n%s" % path
        if not self._email:
            try:
                f_mail = open(path)
                self._email = message_from_file(f_mail)
                f_mail.close()
            except IOError:
                self._email = email.message_from_string(warning)
        return self._email

    def get_date(self):
        """returns Date header value as :class:`~datetime.datetime`"""
        return self._datetime

    def get_filename(self):
        """returns absolute path of message files location"""
        return self._filename

    def get_message_id(self):
        """returns messages id (str)"""
        return self._id

    def get_thread_id(self):
        """returns id (str) of the thread this message belongs to"""
        return self._thread_id

    def get_message_parts(self):
        """returns a list of all body parts of this message"""
        # TODO really needed? email  iterators can do this
        out = []
        for msg in self.get_email().walk():
            if not msg.is_multipart():
                out.append(msg)
        return out

    def get_tags(self):
        """returns tags attached to this message as list of strings"""
        l = sorted(self._tags)
        return l

    def get_thread(self):
        """returns the :class:`~alot.db.Thread` this msg belongs to"""
        if not self._thread:
            self._thread = self._dbman.get_thread(self._thread_id)
        return self._thread

    def has_replies(self):
        """returns true if this message has at least one reply"""
        return (len(self.get_replies()) > 0)

    def get_replies(self):
        """returns replies to this message as list of :class:`Message`"""
        t = self.get_thread()
        return t.get_replies_to(self)

    def get_datestring(self):
        """
        returns reformated datestring for this message.

        It uses :meth:`SettingsManager.represent_datetime` to represent
        this messages `Date` header

        :rtype: str
        """
        if self._datetime is None:
            res = None
        else:
            res = settings.represent_datetime(self._datetime)
        return res

    def get_author(self):
        """
        returns realname and address of this messages author

        :rtype: (str,str)
        """
        return email.Utils.parseaddr(self._from)

    def get_headers_string(self, headers):
        """
        returns subset of this messages headers as human-readable format:
        all header values are decoded, the resulting string has
        one line "KEY: VALUE" for each requested header present in the mail.

        :param headers: headers to extract
        :type headers: list of str
        """
        return extract_headers(self.get_email(), headers)

    def add_tags(self, tags, afterwards=None, remove_rest=False):
        """
        adds tags to message

        .. note::

            This only adds the requested operation to this objects
            :class:`DBManager's <alot.db.DBManager>` write queue.
            You need to call :meth:`~alot.db.DBManager.flush` to write out.

        :param tags: a list of tags to be added
        :type tags: list of str
        :param afterwards: callback that gets called after successful
                           application of this tagging operation
        :type afterwards: callable
        :param remove_rest: remove all other tags
        :type remove_rest: bool
        """
        def myafterwards():
            if remove_rest:
                self._tags = set(tags)
            else:
                self._tags = self._tags.union(tags)
            if callable(afterwards):
                afterwards()

        self._dbman.tag('id:' + self._id, tags, afterwards=myafterwards,
                        remove_rest=remove_rest)
        self._tags = self._tags.union(tags)

    def remove_tags(self, tags, afterwards=None):
        """remove tags from message

        .. note::

            This only adds the requested operation to this objects
            :class:`DBManager's <alot.db.DBManager>` write queue.
            You need to call :meth:`~alot.db.DBManager.flush` to actually out.

        :param tags: a list of tags to be added
        :type tags: list of str
        :param afterwards: callback that gets called after successful
                           application of this tagging operation
        :type afterwards: callable
        """
        def myafterwards():
            self._tags = self._tags.difference(tags)
            if callable(afterwards):
                afterwards()

        self._dbman.untag('id:' + self._id, tags, myafterwards)

    def get_attachments(self):
        """
        returns messages attachments

        Derived from the leaves of the email mime tree
        that and are not part of :rfc:`2015` syntax for encrypted/signed mails
        and either have :mailheader:`Content-Disposition` `attachment`
        or have :mailheader:`Content-Disposition` `inline` but specify
        a filename (as parameter to `Content-Disposition`).

        :rtype: list of :class:`Attachment`
        """
        if not self._attachments:
            self._attachments = []
            for part in self.get_message_parts():
                cd = part.get('Content-Disposition', '')
                filename = part.get_filename()
                ct = part.get_content_type()
                # replace underspecified mime description by a better guess
                if ct in ['octet/stream', 'application/octet-stream']:
                    content = part.get_payload(decode=True)
                    ct = helper.guess_mimetype(content)

                if cd.startswith('attachment'):
                    if ct not in ['application/pgp-encrypted',
                                  'application/pgp-signature']:
                        self._attachments.append(Attachment(part))
                elif cd.startswith('inline'):
                    if filename is not None and ct != 'application/pgp':
                        self._attachments.append(Attachment(part))
        return self._attachments

    def accumulate_body(self):
        """
        returns bodystring extracted from this mail
        """
        # TODO: allow toggle commands to decide which part is considered body
        return extract_body(self.get_email())

    def get_text_content(self):
        return extract_body(self.get_email(), types=['text/plain'])

    def matches(self, querystring):
        """tests if this messages is in the resultset for `querystring`"""
        searchfor = querystring + ' AND id:' + self._id
        return self._dbman.count_messages(searchfor) > 0

########NEW FILE########
__FILENAME__ = thread
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
from datetime import datetime

from message import Message
from alot.settings import settings


class Thread(object):
    """
    A wrapper around a notmuch mailthread (:class:`notmuch.database.Thread`)
    that ensures persistence of the thread: It can be safely read multiple
    times, its manipulation is done via a :class:`alot.db.DBManager` and it can
    directly provide contained messages as :class:`~alot.db.message.Message`.
    """

    def __init__(self, dbman, thread):
        """
        :param dbman: db manager that is used for further lookups
        :type dbman: :class:`~alot.db.DBManager`
        :param thread: the wrapped thread
        :type thread: :class:`notmuch.database.Thread`
        """
        self._dbman = dbman
        self._id = thread.get_thread_id()
        self.refresh(thread)

    def refresh(self, thread=None):
        """refresh thread metadata from the index"""
        if not thread:
            thread = self._dbman._get_notmuch_thread(self._id)

        self._total_messages = thread.get_total_messages()
        self._notmuch_authors_string = thread.get_authors()
        self._subject = thread.get_subject()
        self._authors = None
        ts = thread.get_oldest_date()

        try:
            self._oldest_date = datetime.fromtimestamp(ts)
        except ValueError:  # year is out of range
            self._oldest_date = None
        try:
            timestamp = thread.get_newest_date()
            self._newest_date = datetime.fromtimestamp(timestamp)
        except ValueError:  # year is out of range
            self._newest_date = None

        self._tags = set([t for t in thread.get_tags()])
        self._messages = {}  # this maps messages to its children
        self._toplevel_messages = []

    def __str__(self):
        return "thread:%s: %s" % (self._id, self.get_subject())

    def get_thread_id(self):
        """returns id of this thread"""
        return self._id

    def get_tags(self, intersection=False):
        """
        returns tagsstrings attached to this thread

        :param intersection: return tags present in all contained messages
                             instead of in at least one (union)
        :type intersection: bool
        :rtype: set of str
        """
        tags = set(list(self._tags))
        if intersection:
            for m in self.get_messages().keys():
                tags = tags.intersection(set(m.get_tags()))
        return tags

    def add_tags(self, tags, afterwards=None, remove_rest=False):
        """
        add `tags` to all messages in this thread

        .. note::

            This only adds the requested operation to this objects
            :class:`DBManager's <alot.db.DBManager>` write queue.
            You need to call :meth:`DBManager.flush <alot.db.DBManager.flush>`
            to actually write out.

        :param tags: a list of tags to be added
        :type tags: list of str
        :param afterwards: callback that gets called after successful
                           application of this tagging operation
        :type afterwards: callable
        :param remove_rest: remove all other tags
        :type remove_rest: bool
        """
        def myafterwards():
            if remove_rest:
                self._tags = set(tags)
            else:
                self._tags = self._tags.union(tags)
            if callable(afterwards):
                afterwards()

        self._dbman.tag('thread:' + self._id, tags, afterwards=myafterwards,
                        remove_rest=remove_rest)

    def remove_tags(self, tags, afterwards=None):
        """
        remove `tags` (list of str) from all messages in this thread

        .. note::

            This only adds the requested operation to this objects
            :class:`DBManager's <alot.db.DBManager>` write queue.
            You need to call :meth:`DBManager.flush <alot.db.DBManager.flush>`
            to actually write out.

        :param tags: a list of tags to be added
        :type tags: list of str
        :param afterwards: callback that gets called after successful
                           application of this tagging operation
        :type afterwards: callable
        """
        rmtags = set(tags).intersection(self._tags)
        if rmtags:

            def myafterwards():
                self._tags = self._tags.difference(tags)
                if callable(afterwards):
                    afterwards()
            self._dbman.untag('thread:' + self._id, tags, myafterwards)
            self._tags = self._tags.difference(rmtags)

    def get_authors(self):
        """
        returns a list of authors (name, addr) of the messages.
        The authors are ordered by msg date and unique (by addr).

        :rtype: list of (str, str)
        """
        if self._authors is None:
            self._authors = []
            seen = {}
            msgs = self.get_messages().keys()
            msgs_with_date = filter(lambda m: m.get_date() is not None, msgs)
            msgs_without_date = filter(lambda m: m.get_date() is None, msgs)
            # sort messages with date and append the others
            msgs_with_date.sort(None, lambda m: m.get_date())
            msgs = msgs_with_date + msgs_without_date
            for m in msgs:
                pair = m.get_author()
                if not pair[1] in seen:
                    seen[pair[1]] = True
                    self._authors.append(pair)
        return self._authors

    def get_authors_string(self, own_addrs=None, replace_own=None):
        """
        returns a string of comma-separated authors
        Depending on settings, it will substitute "me" for author name if
        address is user's own.

        :param own_addrs: list of own email addresses to replace
        :type own_addrs: list of str
        :param replace_own: whether or not to actually do replacement
        :type replace_own: bool
        :rtype: str
        """
        if replace_own is None:
            replace_own = settings.get('thread_authors_replace_me')
        if replace_own:
            if own_addrs is None:
                own_addrs = settings.get_addresses()
            authorslist = []
            for aname, aaddress in self.get_authors():
                if aaddress in own_addrs:
                    aname = settings.get('thread_authors_me')
                if not aname:
                    aname = aaddress
                if not aname in authorslist:
                    authorslist.append(aname)
            return ', '.join(authorslist)
        else:
            return self._notmuch_authors_string

    def get_subject(self):
        """returns subject string"""
        return self._subject

    def get_toplevel_messages(self):
        """
        returns all toplevel messages contained in this thread.
        This are all the messages without a parent message
        (identified by 'in-reply-to' or 'references' header.

        :rtype: list of :class:`~alot.db.message.Message`
        """
        if not self._messages:
            self.get_messages()
        return self._toplevel_messages

    def get_messages(self):
        """
        returns all messages in this thread as dict mapping all contained
        messages to their direct responses.

        :rtype: dict mapping :class:`~alot.db.message.Message` to a list of
                :class:`~alot.db.message.Message`.
        """
        if not self._messages:  # if not already cached
            query = self._dbman.query('thread:' + self._id)
            thread = query.search_threads().next()

            def accumulate(acc, msg):
                M = Message(self._dbman, msg, thread=self)
                acc[M] = []
                r = msg.get_replies()
                if r is not None:
                    for m in r:
                        acc[M].append(accumulate(acc, m))
                return M

            self._messages = {}
            for m in thread.get_toplevel_messages():
                self._toplevel_messages.append(accumulate(self._messages, m))
        return self._messages

    def get_replies_to(self, msg):
        """
        returns all replies to the given message contained in this thread.

        :param msg: parent message to look up
        :type msg: :class:`~alot.db.message.Message`
        :returns: list of :class:`~alot.db.message.Message` or `None`
        """
        mid = msg.get_message_id()
        msg_hash = self.get_messages()
        for m in msg_hash.keys():
            if m.get_message_id() == mid:
                return msg_hash[m]
        return None

    def get_newest_date(self):
        """
        returns date header of newest message in this thread as
        :class:`~datetime.datetime`
        """
        return self._newest_date

    def get_oldest_date(self):
        """
        returns date header of oldest message in this thread as
        :class:`~datetime.datetime`
        """
        return self._oldest_date

    def get_total_messages(self):
        """returns number of contained messages"""
        return self._total_messages

    def matches(self, query):
        """
        Check if this thread matches the given notmuch query.

        :param query: The query to check against
        :type query: string
        :returns: True if this thread matches the given query, False otherwise
        :rtype: bool
        """
        thread_query = 'thread:{tid} AND {subquery}'.format(tid=self._id,
                                                            subquery=query)
        num_matches = self._dbman.count_messages(thread_query)
        return num_matches > 0

########NEW FILE########
__FILENAME__ = utils
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import os
import email
import tempfile
import re
from email.header import Header
import email.charset as charset
charset.add_charset('utf-8', charset.QP, charset.QP, 'utf-8')
from email.iterators import typed_subpart_iterator
import logging
import mailcap
from cStringIO import StringIO

import alot.crypto as crypto
import alot.helper as helper
from alot.errors import GPGProblem
from alot.settings import settings
from alot.helper import string_sanitize
from alot.helper import string_decode
from alot.helper import parse_mailcap_nametemplate
from alot.helper import split_commandstring

X_SIGNATURE_VALID_HEADER = 'X-Alot-OpenPGP-Signature-Valid'
X_SIGNATURE_MESSAGE_HEADER = 'X-Alot-OpenPGP-Signature-Message'


def add_signature_headers(mail, sigs, error_msg):
    '''Add pseudo headers to the mail indicating whether the signature
    verification was successful.

    :param mail: :class:`email.message.Message` the message to entitle
    :param sigs: list of :class:`gpgme.Signature`
    :param error_msg: `str` containing an error message, the empty
                      string indicating no error
    '''
    sig_from = ''

    if len(sigs) == 0:
        error_msg = error_msg or 'no signature found'
    else:
        try:
            sig_from = crypto.get_key(sigs[0].fpr).uids[0].uid
        except:
            sig_from = sigs[0].fpr

    mail.add_header(
        X_SIGNATURE_VALID_HEADER,
        'False' if error_msg else 'True',
    )
    mail.add_header(
        X_SIGNATURE_MESSAGE_HEADER,
        u'Invalid: {0}'.format(error_msg)
        if error_msg else
        u'Valid: {0}'.format(sig_from),
    )


def get_params(mail, failobj=list(), header='content-type', unquote=True):
    '''Get Content-Type parameters as dict.

    RFC 2045 specifies that parameter names are case-insensitive, so
    we normalize them here.

    :param mail: :class:`email.message.Message`
    :param failobj: object to return if no such header is found
    :param header: the header to search for parameters, default
    :param unquote: unquote the values
    :returns: a `dict` containing the parameters
    '''
    return {k.lower(): v for k, v in mail.get_params(failobj, header, unquote)}


def message_from_file(handle):
    '''Reads a mail from the given file-like object and returns an email
    object, very much like email.message_from_file. In addition to
    that OpenPGP encrypted data is detected and decrypted. If this
    succeeds, any mime messages found in the recovered plaintext
    message are added to the returned message object.

    :param handle: a file-like object
    :returns: :class:`email.message.Message` possibly augmented with
              decrypted data
    '''
    m = email.message_from_file(handle)

    # make sure noone smuggles a token in (data from m is untrusted)
    del m[X_SIGNATURE_VALID_HEADER]
    del m[X_SIGNATURE_MESSAGE_HEADER]

    p = get_params(m)
    app_pgp_sig = 'application/pgp-signature'
    app_pgp_enc = 'application/pgp-encrypted'

    # handle OpenPGP signed data
    if (m.is_multipart() and
        m.get_content_subtype() == 'signed' and
            p.get('protocol', None) == app_pgp_sig):
        # RFC 3156 is quite strict:
        # * exactly two messages
        # * the second is of type 'application/pgp-signature'
        # * the second contains the detached signature

        malformed = False
        if len(m.get_payload()) != 2:
            malformed = u'expected exactly two messages, got {0}'.format(
                len(m.get_payload()))

        ct = m.get_payload(1).get_content_type()
        if ct != app_pgp_sig:
            malformed = u'expected Content-Type: {0}, got: {1}'.format(
                app_pgp_sig, ct)

        # TODO: RFC 3156 says the alg has to be lower case, but I've
        # seen a message with 'PGP-'. maybe we should be more
        # permissive here, or maybe not, this is crypto stuff...
        if not p.get('micalg', 'nothing').startswith('pgp-'):
            malformed = u'expected micalg=pgp-..., got: {0}'.format(
                p.get('micalg', 'nothing'))

        sigs = []
        if not malformed:
            try:
                sigs = crypto.verify_detached(m.get_payload(0).as_string(),
                                              m.get_payload(1).get_payload())
            except GPGProblem as e:
                malformed = unicode(e)

        add_signature_headers(m, sigs, malformed)

    # handle OpenPGP encrypted data
    elif (m.is_multipart() and
          m.get_content_subtype() == 'encrypted' and
          p.get('protocol', None) == app_pgp_enc and
          'Version: 1' in m.get_payload(0).get_payload()):
        # RFC 3156 is quite strict:
        # * exactly two messages
        # * the first is of type 'application/pgp-encrypted'
        # * the first contains 'Version: 1'
        # * the second is of type 'application/octet-stream'
        # * the second contains the encrypted and possibly signed data
        malformed = False

        ct = m.get_payload(0).get_content_type()
        if ct != app_pgp_enc:
            malformed = u'expected Content-Type: {0}, got: {1}'.format(
                app_pgp_enc, ct)

        want = 'application/octet-stream'
        ct = m.get_payload(1).get_content_type()
        if ct != want:
            malformed = u'expected Content-Type: {0}, got: {1}'.format(want, ct)

        if not malformed:
            try:
                sigs, d = crypto.decrypt_verify(m.get_payload(1).get_payload())
            except GPGProblem as e:
                # signature verification failures end up here too if
                # the combined method is used, currently this prevents
                # the interpretation of the recovered plain text
                # mail. maybe that's a feature.
                malformed = unicode(e)
            else:
                # parse decrypted message
                n = message_from_string(d)

                # add the decrypted message to m. note that n contains
                # all the attachments, no need to walk over n here.
                m.attach(n)

                # add any defects found
                m.defects.extend(n.defects)

                # there are two methods for both signed and encrypted
                # data, one is called 'RFC 1847 Encapsulation' by
                # RFC 3156, and one is the 'Combined method'.
                if len(sigs) == 0:
                    # 'RFC 1847 Encapsulation', the signature is a
                    # detached signature found in the recovered mime
                    # message of type multipart/signed.
                    if X_SIGNATURE_VALID_HEADER in n:
                        for k in (X_SIGNATURE_VALID_HEADER,
                                  X_SIGNATURE_MESSAGE_HEADER):
                            m[k] = n[k]
                    else:
                        # an encrypted message without signatures
                        # should arouse some suspicion, better warn
                        # the user
                        add_signature_headers(m, [], 'no signature found')
                else:
                    # 'Combined method', the signatures are returned
                    # by the decrypt_verify function.

                    # note that if we reached this point, we know the
                    # signatures are valid. if they were not valid,
                    # the else block of the current try would not have
                    # been executed
                    add_signature_headers(m, sigs, '')

        if malformed:
            msg = u'Malformed OpenPGP message: {0}'.format(malformed)
            content = email.message_from_string(msg.encode('utf-8'))
            content.set_charset('utf-8')
            m.attach(content)

    return m


def message_from_string(s):
    '''Reads a mail from the given string. This is the equivalent of
    :func:`email.message_from_string` which does nothing but to wrap
    the given string in a StringIO object and to call
    :func:`email.message_from_file`.

    Please refer to the documentation of :func:`message_from_file` for
    details.

    '''
    return message_from_file(StringIO(s))


def extract_headers(mail, headers=None):
    """
    returns subset of this messages headers as human-readable format:
    all header values are decoded, the resulting string has
    one line "KEY: VALUE" for each requested header present in the mail.

    :param mail: the mail to use
    :type mail: :class:`email.Message`
    :param headers: headers to extract
    :type headers: list of str
    """
    headertext = u''
    if headers is None:
        headers = mail.keys()
    for key in headers:
        value = u''
        if key in mail:
            value = decode_header(mail.get(key, ''))
        headertext += '%s: %s\n' % (key, value)
    return headertext


def extract_body(mail, types=None):
    """
    returns a body text string for given mail.
    If types is `None`, `text/*` is used:
    The exact preferred type is specified by the prefer_plaintext config option
    which defaults to text/html.

    :param mail: the mail to use
    :type mail: :class:`email.Message`
    :param types: mime content types to use for body string
    :type types: list of str
    """

    preferred = 'text/plain' if settings.get(
        'prefer_plaintext') else 'text/html'
    has_preferred = False

    # see if the mail has our preferred type
    if types is None:
        has_preferred = list(typed_subpart_iterator(
            mail, *preferred.split('/')))

    body_parts = []
    for part in mail.walk():
        ctype = part.get_content_type()

        if types is not None:
            if ctype not in types:
                continue
        cd = part.get('Content-Disposition', '')
        if cd.startswith('attachment'):
            continue
        # if the mail has our preferred type, we only keep this type
        # note that if types != None, has_preferred always stays False
        if has_preferred and ctype != preferred:
            continue

        enc = part.get_content_charset() or 'ascii'
        raw_payload = part.get_payload(decode=True)
        if ctype == 'text/plain':
            raw_payload = string_decode(raw_payload, enc)
            body_parts.append(string_sanitize(raw_payload))
        else:
            # get mime handler
            key = 'copiousoutput'
            handler, entry = settings.mailcap_find_match(ctype, key=key)
            tempfile_name = None
            stdin = None

            if entry:
                handler_raw_commandstring = entry['view']
                # in case the mailcap defined command contains no '%s',
                # we pipe the files content to the handling command via stdin
                if '%s' in handler_raw_commandstring:
                    # open tempfile, respect mailcaps nametemplate
                    nametemplate = entry.get('nametemplate', '%s')
                    prefix, suffix = parse_mailcap_nametemplate(nametemplate)
                    tmpfile = tempfile.NamedTemporaryFile(delete=False,
                                                          prefix=prefix,
                                                          suffix=suffix)
                    # write payload to tmpfile
                    tmpfile.write(raw_payload)
                    tmpfile.close()
                    tempfile_name = tmpfile.name
                else:
                    stdin = raw_payload

                # read parameter, create handler command
                parms = tuple(map('='.join, part.get_params()))

                # create and call external command
                cmd = mailcap.subst(entry['view'], ctype,
                                    filename=tempfile_name, plist=parms)
                logging.debug('command: %s' % cmd)
                logging.debug('parms: %s' % str(parms))
                cmdlist = split_commandstring(cmd)
                # call handler
                rendered_payload, errmsg, retval = helper.call_cmd(
                    cmdlist, stdin=stdin)

                # remove tempfile
                if tempfile_name:
                    os.unlink(tempfile_name)

                if rendered_payload:  # handler had output
                    body_parts.append(string_sanitize(rendered_payload))
    return u'\n\n'.join(body_parts)


def decode_header(header, normalize=False):
    """
    decode a header value to a unicode string

    values are usually a mixture of different substrings
    encoded in quoted printable using different encodings.
    This turns it into a single unicode string

    :param header: the header value
    :type header: str
    :param normalize: replace trailing spaces after newlines
    :type normalize: bool
    :rtype: unicode
    """

    # If the value isn't ascii as RFC2822 prescribes,
    # we just return the unicode bytestring as is
    value = string_decode(header)  # convert to unicode
    try:
        value = value.encode('ascii')
    except UnicodeEncodeError:
        return value

    # some mailers send out incorrectly escaped headers
    # and double quote the escaped realname part again. remove those
    value = re.sub(r'\"(.*?=\?.*?.*?)\"', r'\1', value)

    # otherwise we interpret RFC2822 encoding escape sequences
    valuelist = email.header.decode_header(value)
    decoded_list = []
    for v, enc in valuelist:
        v = string_decode(v, enc)
        decoded_list.append(string_sanitize(v))
    value = u' '.join(decoded_list)
    if normalize:
        value = re.sub(r'\n\s+', r' ', value)
    return value


def encode_header(key, value):
    """
    encodes a unicode string as a valid header value

    :param key: the header field this value will be stored in
    :type key: str
    :param value: the value to be encoded
    :type value: unicode
    """
    # handle list of "realname <email>" entries separately
    if key.lower() in ['from', 'to', 'cc', 'bcc']:
        rawentries = value.split(',')
        encodedentries = []
        for entry in rawentries:
            m = re.search('\s*(.*)\s+<(.*\@.*\.\w*)>\s*$', entry)
            if m:  # If a realname part is contained
                name, address = m.groups()
                # try to encode as ascii, if that fails, revert to utf-8
                # name must be a unicode string here
                namepart = Header(name)
                # append address part encoded as ascii
                entry = '%s <%s>' % (namepart.encode(), address)
            encodedentries.append(entry)
        value = Header(', '.join(encodedentries))
    else:
        value = Header(value)
    return value

def is_subdir_of(subpath, superpath):
    #make both absolute    
    superpath = os.path.realpath(superpath)
    subpath = os.path.realpath(subpath)

    #return true, if the common prefix of both is equal to directory
    #e.g. /a/b/c/d.rst and directory is /a/b, the common prefix is /a/b
    return os.path.commonprefix([subpath, superpath]) == superpath

########NEW FILE########
__FILENAME__ = errors
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file


class GPGCode:
    AMBIGUOUS_NAME = 1
    NOT_FOUND = 2
    BAD_PASSPHRASE = 3
    KEY_REVOKED = 4
    KEY_EXPIRED = 5
    KEY_INVALID = 6
    KEY_CANNOT_ENCRYPT = 7
    KEY_CANNOT_SIGN = 8
    INVALID_HASH = 9


class GPGProblem(Exception):
    """GPG Error"""
    def __init__(self, message, code):
        self.code = code
        super(GPGProblem, self).__init__(message)


class CompletionError(Exception):
    pass

########NEW FILE########
__FILENAME__ = lru_cache
# This is a backport of functools.lru_cache, which is part of the stdlib =>v3.3.
# http://code.activestate.com/recipes/578078-py26-and-py30-backport-of-python-33s-lru-cache/

from collections import namedtuple
from functools import update_wrapper
from threading import Lock

_CacheInfo = namedtuple("CacheInfo", ["hits", "misses", "maxsize", "currsize"])

def lru_cache(maxsize=100, typed=False):
    """Least-recently-used cache decorator.

    If *maxsize* is set to None, the LRU features are disabled and the cache
    can grow without bound.

    If *typed* is True, arguments of different types will be cached separately.
    For example, f(3.0) and f(3) will be treated as distinct calls with
    distinct results.

    Arguments to the cached function must be hashable.

    View the cache statistics named tuple (hits, misses, maxsize, currsize) with
    f.cache_info().  Clear the cache and statistics with f.cache_clear().
    Access the underlying function with f.__wrapped__.

    See:  http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    """

    # Users should only access the lru_cache through its public API:
    #       cache_info, cache_clear, and f.__wrapped__
    # The internals of the lru_cache are encapsulated for thread safety and
    # to allow the implementation to change (including a possible C version).

    def decorating_function(user_function):

        cache = dict()
        stats = [0, 0]                  # make statistics updateable non-locally
        HITS, MISSES = 0, 1             # names for the stats fields
        kwd_mark = (object(),)          # separate positional and keyword args
        cache_get = cache.get           # bound method to lookup key or return None
        _len = len                      # localize the global len() function
        lock = Lock()                   # because linkedlist updates aren't threadsafe
        root = []                       # root of the circular doubly linked list
        nonlocal_root = [root]                  # make updateable non-locally
        root[:] = [root, root, None, None]      # initialize by pointing to self
        PREV, NEXT, KEY, RESULT = 0, 1, 2, 3    # names for the link fields

        def make_key(args, kwds, typed, tuple=tuple, sorted=sorted, type=type):
            # helper function to build a cache key from positional and keyword args
            key = args
            if kwds:
                sorted_items = tuple(sorted(kwds.items()))
                key += kwd_mark + sorted_items
            if typed:
                key += tuple(type(v) for v in args)
                if kwds:
                    key += tuple(type(v) for k, v in sorted_items)
            return key

        if maxsize == 0:

            def wrapper(*args, **kwds):
                # no caching, just do a statistics update after a successful call
                result = user_function(*args, **kwds)
                stats[MISSES] += 1
                return result

        elif maxsize is None:

            def wrapper(*args, **kwds):
                # simple caching without ordering or size limit
                key = make_key(args, kwds, typed) if kwds or typed else args
                result = cache_get(key, root)   # root used here as a unique not-found sentinel
                if result is not root:
                    stats[HITS] += 1
                    return result
                result = user_function(*args, **kwds)
                cache[key] = result
                stats[MISSES] += 1
                return result

        else:

            def wrapper(*args, **kwds):
                # size limited caching that tracks accesses by recency
                key = make_key(args, kwds, typed) if kwds or typed else args
                with lock:
                    link = cache_get(key)
                    if link is not None:
                        # record recent use of the key by moving it to the front of the list
                        root, = nonlocal_root
                        link_prev, link_next, key, result = link
                        link_prev[NEXT] = link_next
                        link_next[PREV] = link_prev
                        last = root[PREV]
                        last[NEXT] = root[PREV] = link
                        link[PREV] = last
                        link[NEXT] = root
                        stats[HITS] += 1
                        return result
                result = user_function(*args, **kwds)
                with lock:
                    root = nonlocal_root[0]
                    if _len(cache) < maxsize:
                        # put result in a new link at the front of the list
                        last = root[PREV]
                        link = [last, root, key, result]
                        cache[key] = last[NEXT] = root[PREV] = link
                    else:
                        # use root to store the new key and result
                        root[KEY] = key
                        root[RESULT] = result
                        cache[key] = root
                        # empty the oldest link and make it the new root
                        root = nonlocal_root[0] = root[NEXT]
                        del cache[root[KEY]]
                        root[KEY] = None
                        root[RESULT] = None
                    stats[MISSES] += 1
                return result

        def cache_info():
            """Report cache statistics"""
            with lock:
                return _CacheInfo(stats[HITS], stats[MISSES], maxsize, len(cache))

        def cache_clear():
            """Clear the cache and cache statistics"""
            with lock:
                cache.clear()
                root = nonlocal_root[0]
                root[:] = [root, root, None, None]
                stats[:] = [0, 0]

        wrapper.__wrapped__ = user_function
        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return update_wrapper(wrapper, user_function)

    return decorating_function

########NEW FILE########
__FILENAME__ = decoration
# Copyright (C) 2013  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
from tree import Tree, SimpleTree
import urwid
import logging

NO_SPACE_MSG = 'too little space for requested decoration'


class TreeDecorationError(Exception):
    pass


class DecoratedTree(Tree):
    """
    :class:`Tree` that wraps around another :class:`Tree` and allows to read
    original content as well as decorated versions thereof.
    """
    def __init__(self, content):
        if not isinstance(content, Tree):
            # do we need this?
            content = SimpleTree(content)
        self._tree = content
        self.root = self._tree.root

    def get_decorated(self, pos):
        """
        return widget that consists of the content of original tree at given
        position plus its decoration.
        """
        return self.decorate(pos, self[pos])

    def decorate(self, pos, widget, is_first=True):
        """
        decorate `widget` according to a position `pos` in the original tree.
        setting `is_first` to False indicates that we are decorating a line
        that is *part* of the (multi-line) content at this position, but not
        the first part. This allows to omit incoming arrow heads for example.
        """
        return widget

    # pass on everything else to the original tree.

    def parent_position(self, pos):
        return self._tree.parent_position(pos)

    def first_child_position(self, pos):
        return self._tree.first_child_position(pos)

    def last_child_position(self, pos):
        return self._tree.last_child_position(pos)

    def next_sibling_position(self, pos):
        return self._tree.next_sibling_position(pos)

    def prev_sibling_position(self, pos):
        return self._tree.prev_sibling_position(pos)

    def __getitem__(self, pos):
        return self._tree[pos]


class CollapseMixin(object):
    """
    Mixin for :class:`Tree` that allows to collapse subtrees.

    This works by overwriting
    :meth:`[first|last]_child_position <first_child_position>`, forcing them to
    return `None` if the given position is considered collapsed. We use a
    (given) callable `is_collapsed` that accepts positions and returns a
    boolean to determine which node is considered collapsed.
    """
    def __init__(self, is_collapsed=lambda pos: False,
                 **kwargs):
        self._initially_collapsed = is_collapsed
        self._divergent_positions = []

    def is_collapsed(self, pos):
        """checks if given position is currently collapsed"""
        collapsed = self._initially_collapsed(pos)
        if pos in self._divergent_positions:
            collapsed = not collapsed
        return collapsed

    # implement functionality by overwriting local position transformations

    # TODO: ATM this assumes we are in a wrapper: it uses self._tree.
    # This is not necessarily true, for example for subclasses of SimpleTree!
    # maybe define this whole class as a wrapper?

    def last_child_position(self, pos):
        if self.is_collapsed(pos):
            return None
        return self._tree.last_child_position(pos)

    def first_child_position(self, pos):
        if self.is_collapsed(pos):
            return None
        return self._tree.first_child_position(pos)

    def collapsible(self, pos):
        return not self._tree.is_leaf(pos)

    def set_position_collapsed(self, pos, is_collapsed):
        if self.collapsible(pos):
            if self._initially_collapsed(pos) == is_collapsed:
                if pos in self._divergent_positions:
                    self._divergent_positions.remove(pos)
            else:
                if pos not in self._divergent_positions:
                    self._divergent_positions.append(pos)

    def toggle_collapsed(self, pos):
        self.set_position_collapsed(pos, not self.is_collapsed(pos))

    def collapse(self, pos):
        self.set_position_collapsed(pos, True)

    def collapse_all(self):
        self.set_collapsed_all(True)

    def expand_all(self):
        self.set_collapsed_all(False)

    def set_collapsed_all(self, is_collapsed):
        self._initially_collapsed = lambda x: is_collapsed
        self._divergent_positions = []

    def expand(self, pos):
        self.set_position_collapsed(pos, False)


class CollapseIconMixin(CollapseMixin):
    """
    Mixin for :classs:`Tree` that allows to allows to collapse subtrees
    and use an indicator icon in line decorations.
    This Mixin adds the ability to construct collapse-icon for a
    position, indicating its collapse status to :class:`CollapseMixin`.
    """
    def __init__(self,
                 is_collapsed=lambda pos: False,
                 icon_collapsed_char='+',
                 icon_expanded_char='-',
                 icon_collapsed_att=None,
                 icon_expanded_att=None,
                 icon_frame_left_char='[',
                 icon_frame_right_char=']',
                 icon_frame_att=None,
                 icon_focussed_att=None,
                 **kwargs):
        """TODO: docstrings"""
        CollapseMixin.__init__(self, is_collapsed, **kwargs)
        self._icon_collapsed_char = icon_collapsed_char
        self._icon_expanded_char = icon_expanded_char
        self._icon_collapsed_att = icon_collapsed_att
        self._icon_expanded_att = icon_expanded_att
        self._icon_frame_left_char = icon_frame_left_char
        self._icon_frame_right_char = icon_frame_right_char
        self._icon_frame_att = icon_frame_att
        self._icon_focussed_att = icon_focussed_att

    def _construct_collapse_icon(self, pos):
        width = 0
        widget = None
        char = self._icon_expanded_char
        charatt = self._icon_expanded_att
        if self.is_collapsed(pos):
            char = self._icon_collapsed_char
            charatt = self._icon_collapsed_att
        if char is not None:

            columns = []
            if self._icon_frame_left_char is not None:
                lchar = self._icon_frame_left_char
                charlen = len(lchar)
                leftframe = urwid.Text((self._icon_frame_att, lchar))
                columns.append((charlen, leftframe))
                width += charlen

            # next we build out icon widget: we feed all markups to a Text,
            # make it selectable (to toggle collapse) if requested
            markup = (charatt, char)
            widget = urwid.Text(markup)
            charlen = len(char)
            columns.append((charlen, widget))
            width += charlen

            if self._icon_frame_right_char is not None:
                rchar = self._icon_frame_right_char
                charlen = len(rchar)
                rightframe = urwid.Text((self._icon_frame_att, rchar))
                columns.append((charlen, rightframe))
                width += charlen

            widget = urwid.Columns(columns)
        return width, widget


class CollapsibleTree(CollapseMixin, DecoratedTree):
    """Undecorated Tree that allows to collapse subtrees"""
    def __init__(self, tree, **kwargs):
        DecoratedTree.__init__(self, tree)
        CollapseMixin.__init__(self, **kwargs)


class IndentedTree(DecoratedTree):
    """Indent tree nodes according to their depth in the tree"""
    def __init__(self, tree, indent=2):
        """
        :param tree: tree of widgets to be displayed
        :type tree: Tree
        :param indent: indentation width
        :type indent: int
        """
        self._indent = indent
        DecoratedTree.__init__(self, tree)

    def decorate(self, pos, widget, is_first=True):
        line = None
        indent = self._tree.depth(pos) * self._indent
        cols = [(indent, urwid.SolidFill(' ')), widget]
        # construct a Columns, defining all spacer as Box widgets
        line = urwid.Columns(cols, box_columns=range(len(cols))[:-1])
        return line


class CollapsibleIndentedTree(CollapseIconMixin, IndentedTree):
    """
    Indent collapsible tree nodes according to their depth in the tree and
    display icons indicating collapse-status in the gaps.
    """
    def __init__(self, walker, icon_offset=1, indent=4, **kwargs):
        """
        :param walker: tree of widgets to be displayed
        :type walker: Tree
        :param indent: indentation width
        :type indent: int
        :param icon_offset: distance from icon to the eginning of the tree
                            node.
        :type icon_offset: int
        """
        self._icon_offset = icon_offset
        IndentedTree.__init__(self, walker, indent=indent)
        CollapseIconMixin.__init__(self, **kwargs)

    def decorate(self, pos, widget, is_first=True):
        """
        builds a list element for given position in the tree.
        It consists of the original widget taken from the Tree and some
        decoration columns depending on the existence of parent and sibling
        positions. The result is a urwid.Culumns widget.
        """
        void = urwid.SolidFill(' ')
        line = None
        cols = []
        depth = self._tree.depth(pos)

        # add spacer filling all but the last indent
        if depth > 0:
            cols.append((depth * self._indent, void)),  # spacer

        # construct last indent
        # TODO
        iwidth, icon = self._construct_collapse_icon(pos)
        available_space = self._indent
        firstindent_width = self._icon_offset + iwidth

        # stop if indent is too small for this decoration
        if firstindent_width > available_space:
            raise TreeDecorationError(NO_SPACE_MSG)

        # add icon only for non-leafs
        is_leaf = self._tree.is_leaf(pos)
        if not is_leaf:
            if icon is not None:
                # space to the left
                cols.append((available_space - firstindent_width,
                             urwid.SolidFill(' ')))
                # icon
                icon_pile = urwid.Pile([('pack', icon), void])
                cols.append((iwidth, icon_pile))
                # spacer until original widget
                available_space = self._icon_offset
            cols.append((available_space, urwid.SolidFill(' ')))
        else:  # otherwise just add another spacer
            cols.append((self._indent, urwid.SolidFill(' ')))

        cols.append(widget)  # original widget ]
        # construct a Columns, defining all spacer as Box widgets
        line = urwid.Columns(cols, box_columns=range(len(cols))[:-1])

        return line


class ArrowTree(IndentedTree):
    """
    Decorates the tree by indenting nodes according to their depth and using
    the gaps to draw arrows indicate the tree structure.
    """
    def __init__(self, walker,
                 indent=3,
                 childbar_offset=0,
                 arrow_hbar_char=u'\u2500',
                 arrow_hbar_att=None,
                 arrow_vbar_char=u'\u2502',
                 arrow_vbar_att=None,
                 arrow_tip_char=u'\u27a4',
                 arrow_tip_att=None,
                 arrow_att=None,
                 arrow_connector_tchar=u'\u251c',
                 arrow_connector_lchar=u'\u2514',
                 arrow_connector_att=None, **kwargs):
        """
        :param walker: tree of widgets to be displayed
        :type walker: Tree
        :param indent: indentation width
        :type indent: int
        """
        IndentedTree.__init__(self, walker, indent)
        self._childbar_offset = childbar_offset
        self._arrow_hbar_char = arrow_hbar_char
        self._arrow_hbar_att = arrow_hbar_att
        self._arrow_vbar_char = arrow_vbar_char
        self._arrow_vbar_att = arrow_vbar_att
        self._arrow_connector_lchar = arrow_connector_lchar
        self._arrow_connector_tchar = arrow_connector_tchar
        self._arrow_connector_att = arrow_connector_att
        self._arrow_tip_char = arrow_tip_char
        self._arrow_tip_att = arrow_tip_att
        self._arrow_att = arrow_att

    def _construct_spacer(self, pos, acc):
        """
        build a spacer that occupies the horizontally indented space between
        pos's parent and the root node. It will return a list of tuples to be
        fed into a Columns widget.
        """
        parent = self._tree.parent_position(pos)
        if parent is not None:
            grandparent = self._tree.parent_position(parent)
            if self._indent > 0 and grandparent is not None:
                parent_sib = self._tree.next_sibling_position(parent)
                draw_vbar = parent_sib is not None and \
                    self._arrow_vbar_char is not None
                space_width = self._indent - 1 * (draw_vbar) - self._childbar_offset
                if space_width > 0:
                    void = urwid.AttrMap(urwid.SolidFill(' '), self._arrow_att)
                    acc.insert(0, ((space_width, void)))
                if draw_vbar:
                    barw = urwid.SolidFill(self._arrow_vbar_char)
                    bar = urwid.AttrMap(barw, self._arrow_vbar_att or
                                        self._arrow_att)
                    acc.insert(0, ((1, bar)))
            return self._construct_spacer(parent, acc)
        else:
            return acc

    def _construct_connector(self, pos):
        """
        build widget to be used as "connector" bit between the vertical bar
        between siblings and their respective horizontab bars leading to the
        arrow tip
        """
        # connector symbol, either L or |- shaped.
        connectorw = None
        connector = None
        if self._tree.next_sibling_position(pos) is not None:  # |- shaped
            if self._arrow_connector_tchar is not None:
                connectorw = urwid.Text(self._arrow_connector_tchar)
        else:  # L shaped
            if self._arrow_connector_lchar is not None:
                connectorw = urwid.Text(self._arrow_connector_lchar)
        if connectorw is not None:
            att = self._arrow_connector_att or self._arrow_att
            connector = urwid.AttrMap(connectorw, att)
        return connector

    def _construct_arrow_tip(self, pos):
        """returns arrow tip as (width, widget)"""
        arrow_tip = None
        width = 0
        if self._arrow_tip_char:
            txt = urwid.Text(self._arrow_tip_char)
            arrow_tip = urwid.AttrMap(
                txt, self._arrow_tip_att or self._arrow_att)
            width = len(self._arrow_tip_char)
        return width, arrow_tip

    def _construct_first_indent(self, pos):
        """
        build spacer to occupy the first indentation level from pos to the
        left. This is separate as it adds arrowtip and sibling connector.
        """
        cols = []
        void = urwid.AttrMap(urwid.SolidFill(' '), self._arrow_att)
        available_width = self._indent

        if self._tree.depth(pos) > 0:
            connector = self._construct_connector(pos)
            if connector is not None:
                width = connector.pack()[0]
                if width > available_width:
                    raise TreeDecorationError(NO_SPACE_MSG)
                available_width -= width
                if self._tree.next_sibling_position(pos) is not None:
                    barw = urwid.SolidFill(self._arrow_vbar_char)
                    below = urwid.AttrMap(barw, self._arrow_vbar_att or
                                          self._arrow_att)
                else:
                    below = void
                # pile up connector and bar
                spacer = urwid.Pile([('pack', connector), below])
                cols.append((width, spacer))

            #arrow tip
            awidth, at = self._construct_arrow_tip(pos)
            if at is not None:
                if awidth > available_width:
                    raise TreeDecorationError(NO_SPACE_MSG)
                available_width -= awidth
                at_spacer = urwid.Pile([('pack', at), void])
                cols.append((awidth, at_spacer))

            # bar between connector and arrow tip
            if available_width > 0:
                barw = urwid.SolidFill(self._arrow_hbar_char)
                bar = urwid.AttrMap(
                    barw, self._arrow_hbar_att or self._arrow_att)
                hb_spacer = urwid.Pile([(1, bar), void])
                cols.insert(1, (available_width, hb_spacer))
        return cols

    def decorate(self, pos, widget, is_first=True):
        """
        builds a list element for given position in the tree.
        It consists of the original widget taken from the Tree and some
        decoration columns depending on the existence of parent and sibling
        positions. The result is a urwid.Culumns widget.
        """
        line = None
        if pos is not None:
            original_widget = widget
            cols = self._construct_spacer(pos, [])

            # Construct arrow leading from parent here,
            # if we have a parent and indentation is turned on
            if self._indent > 0:
                if is_first:
                    indent = self._construct_first_indent(pos)
                    if indent is not None:
                        cols = cols + indent
                else:
                    parent = self._tree.parent_position(pos)
                    if self._indent > 0 and parent is not None:
                        parent_sib = self._tree.next_sibling_position(pos)
                        draw_vbar = parent_sib is not None
                        void = urwid.AttrMap(urwid.SolidFill(' '),
                                             self._arrow_att)
                        if self._childbar_offset > 0:
                            cols.append((self._childbar_offset, void))
                        if draw_vbar:
                            barw = urwid.SolidFill(self._arrow_vbar_char)
                            bar = urwid.AttrMap(
                                barw, self._arrow_vbar_att or self._arrow_att)
                            rspace_width = self._indent - \
                                1 - self._childbar_offset
                            cols.append((1, bar))
                            cols.append((rspace_width, void))
                        else:
                            cols.append((self._indent, void))

            # add the original widget for this line
            cols.append(original_widget)
            # construct a Columns, defining all spacer as Box widgets
            line = urwid.Columns(cols, box_columns=range(len(cols))[:-1])
        return line


class CollapsibleArrowTree(CollapseIconMixin, ArrowTree):
    """Arrow-decoration that allows collapsing subtrees"""
    def __init__(self, treelistwalker, icon_offset=0, indent=5, **kwargs):
        self._icon_offset = icon_offset
        ArrowTree.__init__(self, treelistwalker, indent, **kwargs)
        CollapseIconMixin.__init__(self, **kwargs)

    def _construct_arrow_tip(self, pos):

        cols = []
        overall_width = self._icon_offset

        if self._icon_offset > 0:
            # how often we repeat the hbar_char until width icon_offset is
            # reached
            hbar_char_count = len(self._arrow_hbar_char) / self._icon_offset
            barw = urwid.Text(self._arrow_hbar_char * hbar_char_count)
            bar = urwid.AttrMap(barw, self._arrow_hbar_att or self._arrow_att)
            cols.insert(1, (self._icon_offset, bar))

        # add icon only for non-leafs
        if self.collapsible(pos):
            iwidth, icon = self._construct_collapse_icon(pos)
            if icon is not None:
                cols.insert(0, (iwidth, icon))
                overall_width += iwidth

        # get arrow tip
        awidth, tip = ArrowTree._construct_arrow_tip(self, pos)
        if tip is not None:
            cols.append((awidth, tip))
            overall_width += awidth

        return overall_width, urwid.Columns(cols)

########NEW FILE########
__FILENAME__ = example1
#!/usr/bin/python
# Copyright (C) 2013  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.

import urwid
from tree import SimpleTree
from widgets import TreeBox


# define some colours
palette = [
    ('body', 'black', 'light gray'),
    ('focus', 'light gray', 'dark blue', 'standout'),
    ('bars', 'dark blue', 'light gray', ''),
    ('arrowtip', 'light blue', 'light gray', ''),
    ('connectors', 'light red', 'light gray', ''),
]

# We use selectable Text widgets for our example..


class FocusableText(urwid.WidgetWrap):
    """Selectable Text used for nodes in our example"""
    def __init__(self, txt):
        t = urwid.Text(txt)
        w = urwid.AttrMap(t, 'body', 'focus')
        urwid.WidgetWrap.__init__(self, w)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key

# define a test tree in the format accepted by SimpleTree. Essentially, a
# tree is given as (nodewidget, [list, of, subtrees]). SimpleTree accepts
# lists of such trees.


def construct_example_simpletree_structure(selectable_nodes=True, children=3):

    Text = FocusableText if selectable_nodes else urwid.Text

    # define root node
    tree = (Text('ROOT'), [])

    # define some children
    c = g = gg = 0  # counter
    for i in range(children):
        subtree = (Text('Child %d' % c), [])
        # and grandchildren..
        for j in range(children):
            subsubtree = (Text('Grandchild %d' % g), [])
            for k in range(children):
                leaf = (Text('Grand Grandchild %d' % gg), None)
                subsubtree[1].append(leaf)
                gg += 1  # inc grand-grandchild counter
            subtree[1].append(subsubtree)
            g += 1  # inc grandchild counter
        tree[1].append(subtree)
        c += 1
    return tree


def construct_example_tree(selectable_nodes=True, children=2):
    # define a list of tree structures to be passed on to SimpleTree
    forrest = [construct_example_simpletree_structure(selectable_nodes,
                                                      children)]

    # stick out test tree into a SimpleTree and return
    return SimpleTree(forrest)

if __name__ == "__main__":
    # get example tree
    stree = construct_example_tree()

    # put the tree into a treebox
    treebox = TreeBox(stree)

    # add some decoration
    rootwidget = urwid.AttrMap(treebox, 'body')
    urwid.MainLoop(rootwidget, palette).run()  # go

########NEW FILE########
__FILENAME__ = example2.arrows
#!/usr/bin/python
# Copyright (C) 2013  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.

from example1 import construct_example_tree, palette  # example data
from decoration import ArrowTree  # for Decoration
from widgets import TreeBox
import urwid

if __name__ == "__main__":
    # get example tree
    stree = construct_example_tree()
    # Here, we add some decoration by wrapping the tree using ArrowTree.
    atree = ArrowTree(stree,
                      # customize at will..
                      # arrow_hbar_char=u'\u2550',
                      # arrow_vbar_char=u'\u2551',
                      # arrow_tip_char=u'\u25B7',
                      # arrow_connector_tchar=u'\u2560',
                      # arrow_connector_lchar=u'\u255A',
                      )

    # put the into a treebox
    treebox = TreeBox(atree)

    rootwidget = urwid.AttrMap(treebox, 'body')
    urwid.MainLoop(rootwidget, palette).run()  # go

########NEW FILE########
__FILENAME__ = example3.collapse
#!/usr/bin/python
# Copyright (C) 2013  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.

from example1 import construct_example_tree, palette  # example data
from decoration import CollapsibleIndentedTree  # for Decoration
from widgets import TreeBox
import urwid

if __name__ == "__main__":
    # get some SimpleTree
    stree = construct_example_tree()

    # Use (subclasses of) the wrapper decoration.CollapsibleTree to construct a
    # tree where collapsible subtrees. Apart from the original tree, these take
    # a callable `is_collapsed` that defines initial collapsed-status if a
    # given position.

    # We want all grandchildren collapsed initially
    if_grandchild = lambda pos: stree.depth(pos) > 1

    # We use CollapsibleIndentedTree around the original example tree.
    # This uses Indentation to indicate the tree structure and squeezes in
    # text-icons to indicate the collapsed status.
    # Also try CollapsibleTree or CollapsibleArrowTree..
    tree = CollapsibleIndentedTree(stree,
                                   is_collapsed=if_grandchild,
                                   icon_focussed_att='focus',
                                   # indent=6,
                                   # childbar_offset=1,
                                   # icon_frame_left_char=None,
                                   # icon_frame_right_char=None,
                                   # icon_expanded_char='-',
                                   # icon_collapsed_char='+',
                                   )

    # put the tree into a treebox
    treebox = TreeBox(tree)

    rootwidget = urwid.AttrMap(treebox, 'body')
    urwid.MainLoop(rootwidget, palette).run()  # go

########NEW FILE########
__FILENAME__ = example4.filesystem
#!/usr/bin/python
# Copyright (C) 2013  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.

import urwid
import os
from example1 import palette  # example data
from widgets import TreeBox
from tree import Tree
from decoration import CollapsibleArrowTree


# define selectable urwid.Text widgets to display paths
class FocusableText(urwid.WidgetWrap):
    """Widget to display paths lines"""
    def __init__(self, txt):
        t = urwid.Text(txt)
        w = urwid.AttrMap(t, 'body', 'focus')
        urwid.WidgetWrap.__init__(self, w)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key

# define Tree that can walk your filesystem


class DirectoryTree(Tree):
    """
    A custom Tree representing our filesystem structure.
    This implementation is rather inefficient: basically every position-lookup
    will call `os.listdir`.. This makes navigation in the tree quite slow.
    In real life you'd want to do some caching.

    As positions we use absolute path strings.
    """
    # determine dir separator and form of root node
    pathsep = os.path.sep
    drive, _ = os.path.splitdrive(pathsep)

    # define root node This is part of the Tree API!
    root = drive + pathsep

    def __getitem__(self, pos):
        return FocusableText(pos)

    # generic helper
    def _list_dir(self, path):
        """returns absolute paths for all entries in a directory"""
        try:
            elements = [os.path.join(
                path, x) for x in os.listdir(path) if os.path.isdir(path)]
            elements.sort()
        except OSError:
            elements = None
        return elements

    def _get_siblings(self, pos):
        """lists the parent directory of pos """
        parent = self.parent_position(pos)
        siblings = [pos]
        if parent is not None:
            siblings = self._list_dir(parent)
        return siblings

    # Tree API
    def parent_position(self, pos):
        parent = None
        if pos != '/':
            parent = os.path.split(pos)[0]
        return parent

    def first_child_position(self, pos):
        candidate = None
        if os.path.isdir(pos):
            children = self._list_dir(pos)
            if children:
                candidate = children[0]
        return candidate

    def last_child_position(self, pos):
        candidate = None
        if os.path.isdir(pos):
            children = self._list_dir(pos)
            if children:
                candidate = children[-1]
        return candidate

    def next_sibling_position(self, pos):
        candidate = None
        siblings = self._get_siblings(pos)
        myindex = siblings.index(pos)
        if myindex + 1 < len(siblings):  # pos is not the last entry
            candidate = siblings[myindex + 1]
        return candidate

    def prev_sibling_position(self, pos):
        candidate = None
        siblings = self._get_siblings(pos)
        myindex = siblings.index(pos)
        if myindex > 0:  # pos is not the first entry
            candidate = siblings[myindex - 1]
        return candidate

if __name__ == "__main__":
    cwd = os.getcwd()  # get current working directory
    dtree = DirectoryTree()  # get a directory walker

    # Use CollapsibleArrowTree for decoration.
    # define initial collapse:
    as_deep_as_cwd = lambda pos: dtree.depth(pos) >= dtree.depth(cwd)

    # We hide the usual arrow tip and use a customized collapse-icon.
    decorated_tree = CollapsibleArrowTree(dtree,
                                          is_collapsed=as_deep_as_cwd,
                                          arrow_tip_char=None,
                                          icon_frame_left_char=None,
                                          icon_frame_right_char=None,
                                          icon_collapsed_char=u'\u25B6',
                                          icon_expanded_char=u'\u25B7',)

    # stick it into a TreeBox and use 'body' color attribute for gaps
    tb = TreeBox(decorated_tree, focus=cwd)
    root_widget = urwid.AttrMap(tb, 'body')
    urwid.MainLoop(root_widget, palette).run()  # go

########NEW FILE########
__FILENAME__ = example5.nested
#!/usr/bin/python
# Copyright (C) 2013  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.

from example1 import palette, construct_example_tree  # example data
from example1 import FocusableText  # Selectable Text used for nodes
from widgets import TreeBox
from tree import SimpleTree
from nested import NestedTree
from decoration import ArrowTree, CollapsibleArrowTree  # decoration
import urwid
import logging


if __name__ == "__main__":
    #logging.basicConfig(filename='example.log',level=logging.DEBUG)
    # Take some Arrow decorated Tree that we later stick inside another tree.
    innertree = ArrowTree(construct_example_tree())
    # Some collapsible, arrow decorated tree with extra indent
    anotherinnertree = CollapsibleArrowTree(construct_example_tree(),
                                            indent=10)

    # A SimpleTree, that contains the two above
    middletree = SimpleTree(
        [
            (FocusableText('Middle ROOT'),
             [
                 (FocusableText('Mid Child One'), None),
                 (FocusableText('Mid Child Two'), None),
                 (innertree, None),
                 (FocusableText('Mid Child Three'),
                  [
                      (FocusableText('Mid Grandchild One'), None),
                      (FocusableText('Mid Grandchild Two'), None),
                  ]
                  ),
                 (anotherinnertree,
                  # middletree defines a childnode here. This is usually
                  # covered by the tree 'anotherinnertree', unless the
                  # interepreting NestedTree's constructor gets parameter
                  # interpret_covered=True..
                  [
                      (FocusableText('XXX I\'m invisible!'), None),

                  ]),
             ]
             )
        ]
    )  # end SimpleTree constructor for middletree
    # use customized arrow decoration for middle tree
    middletree = ArrowTree(middletree,
                           arrow_hbar_char=u'\u2550',
                           arrow_vbar_char=u'\u2551',
                           arrow_tip_char=u'\u25B7',
                           arrow_connector_tchar=u'\u2560',
                           arrow_connector_lchar=u'\u255A')

    # define outmost tree
    outertree = SimpleTree(
        [
            (FocusableText('Outer ROOT'),
             [
                 (FocusableText('Child One'), None),
                 (middletree, None),
                 (FocusableText('last outer child'), None),
             ]
             )
        ]
    )  # end SimpleTree constructor

    # add some Arrow decoration
    outertree = ArrowTree(outertree)
    # wrap the whole thing into a Nested Tree
    outertree = NestedTree(outertree,
                           # show covered nodes like  XXX
                           interpret_covered=False
                           )

    # put it into a treebox and run
    treebox = TreeBox(outertree)
    rootwidget = urwid.AttrMap(treebox, 'body')
    urwid.MainLoop(rootwidget, palette).run()  # go

########NEW FILE########
__FILENAME__ = lru_cache
# This is a backport of functools.lru_cache, which is part of the stdlib =>v3.3.
# http://code.activestate.com/recipes/578078-py26-and-py30-backport-of-python-33s-lru-cache/

from collections import namedtuple
from functools import update_wrapper
from threading import Lock

_CacheInfo = namedtuple("CacheInfo", ["hits", "misses", "maxsize", "currsize"])

def lru_cache(maxsize=100, typed=False):
    """Least-recently-used cache decorator.

    If *maxsize* is set to None, the LRU features are disabled and the cache
    can grow without bound.

    If *typed* is True, arguments of different types will be cached separately.
    For example, f(3.0) and f(3) will be treated as distinct calls with
    distinct results.

    Arguments to the cached function must be hashable.

    View the cache statistics named tuple (hits, misses, maxsize, currsize) with
    f.cache_info().  Clear the cache and statistics with f.cache_clear().
    Access the underlying function with f.__wrapped__.

    See:  http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    """

    # Users should only access the lru_cache through its public API:
    #       cache_info, cache_clear, and f.__wrapped__
    # The internals of the lru_cache are encapsulated for thread safety and
    # to allow the implementation to change (including a possible C version).

    def decorating_function(user_function):

        cache = dict()
        stats = [0, 0]                  # make statistics updateable non-locally
        HITS, MISSES = 0, 1             # names for the stats fields
        kwd_mark = (object(),)          # separate positional and keyword args
        cache_get = cache.get           # bound method to lookup key or return None
        _len = len                      # localize the global len() function
        lock = Lock()                   # because linkedlist updates aren't threadsafe
        root = []                       # root of the circular doubly linked list
        nonlocal_root = [root]                  # make updateable non-locally
        root[:] = [root, root, None, None]      # initialize by pointing to self
        PREV, NEXT, KEY, RESULT = 0, 1, 2, 3    # names for the link fields

        def make_key(args, kwds, typed, tuple=tuple, sorted=sorted, type=type):
            # helper function to build a cache key from positional and keyword args
            key = args
            if kwds:
                sorted_items = tuple(sorted(kwds.items()))
                key += kwd_mark + sorted_items
            if typed:
                key += tuple(type(v) for v in args)
                if kwds:
                    key += tuple(type(v) for k, v in sorted_items)
            return key

        if maxsize == 0:

            def wrapper(*args, **kwds):
                # no caching, just do a statistics update after a successful call
                result = user_function(*args, **kwds)
                stats[MISSES] += 1
                return result

        elif maxsize is None:

            def wrapper(*args, **kwds):
                # simple caching without ordering or size limit
                key = make_key(args, kwds, typed) if kwds or typed else args
                result = cache_get(key, root)   # root used here as a unique not-found sentinel
                if result is not root:
                    stats[HITS] += 1
                    return result
                result = user_function(*args, **kwds)
                cache[key] = result
                stats[MISSES] += 1
                return result

        else:

            def wrapper(*args, **kwds):
                # size limited caching that tracks accesses by recency
                key = make_key(args, kwds, typed) if kwds or typed else args
                with lock:
                    link = cache_get(key)
                    if link is not None:
                        # record recent use of the key by moving it to the front of the list
                        root, = nonlocal_root
                        link_prev, link_next, key, result = link
                        link_prev[NEXT] = link_next
                        link_next[PREV] = link_prev
                        last = root[PREV]
                        last[NEXT] = root[PREV] = link
                        link[PREV] = last
                        link[NEXT] = root
                        stats[HITS] += 1
                        return result
                result = user_function(*args, **kwds)
                with lock:
                    root = nonlocal_root[0]
                    if _len(cache) < maxsize:
                        # put result in a new link at the front of the list
                        last = root[PREV]
                        link = [last, root, key, result]
                        cache[key] = last[NEXT] = root[PREV] = link
                    else:
                        # use root to store the new key and result
                        root[KEY] = key
                        root[RESULT] = result
                        cache[key] = root
                        # empty the oldest link and make it the new root
                        root = nonlocal_root[0] = root[NEXT]
                        del cache[root[KEY]]
                        root[KEY] = None
                        root[RESULT] = None
                    stats[MISSES] += 1
                return result

        def cache_info():
            """Report cache statistics"""
            with lock:
                return _CacheInfo(stats[HITS], stats[MISSES], maxsize, len(cache))

        def cache_clear():
            """Clear the cache and cache statistics"""
            with lock:
                cache.clear()
                root = nonlocal_root[0]
                root[:] = [root, root, None, None]
                stats[:] = [0, 0]

        wrapper.__wrapped__ = user_function
        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return update_wrapper(wrapper, user_function)

    return decorating_function

########NEW FILE########
__FILENAME__ = nested
# Copyright (C) 2013  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
from tree import Tree
from decoration import DecoratedTree, CollapseMixin


class NestedTree(Tree):
    """
    A Tree that wraps around Trees that may contain list walkers or other
    trees.  The wrapped tree may contain normal widgets as well. List walkers
    and subtree contents will be expanded into the tree presented by this
    wrapper.

    This wrapper's positions are tuples of positions of the original and
    subtrees: For example, `(X,Y,Z)` points at position Z in tree/list at
    position Y in tree/list at position X in the original tree.

    NestedTree transparently behaves like a collapsible DecoratedTree.
    """
    @property
    def root(self):
        root = (self._tree.root,)
        rcontent = self._tree[self._tree.root]
        if isinstance(rcontent, Tree):
            root = root + (rcontent.root,)
        return root

    def _sanitize_position(self, pos, tree=None):
        """
        Ensure a position tuple until the result does not
        point to a :class:`Tree` any more.
        """
        if pos is not None:
            tree = tree or self._tree
            entry = self._lookup_entry(tree, pos)
            if isinstance(entry, Tree):
                pos = pos + self._sanitize_position((entry.root,), tree=entry)
        return pos

    def __init__(self, tree, interpret_covered=False):
        self._tree = tree
        self._interpret_covered = interpret_covered

    def _lookup_entry(self, tree, pos):
        if len(pos) == 0:
            entry = tree[tree.root]
        else:
            entry = tree[pos[0]]
            if len(pos) > 1 and isinstance(entry, Tree):
                subtree = entry
                entry = self._lookup_entry(subtree, pos[1:])
        return entry

    def _depth(self, tree, pos, outmost_only=True):
        depth = self._tree.depth(pos[1:])
        if not outmost_only:
            entry = self._tree[pos[0]]
            if isinstance(entry, Tree) and len(pos) > 1:
                depth += self._depth(entry, pos[1:], outmost_only=False)
        return depth

    def depth(self, pos, outmost=True):
        return self._depth(self._tree, pos)

    def __getitem__(self, pos):
        return self._lookup_entry(self._tree, pos)

    # DecoratedTree API
    def _get_decorated_entry(self, tree, pos, widget=None, is_first=True):
        entry = tree[pos[0]]
        if len(pos) > 1 and isinstance(entry, Tree):
            subtree = entry
            entry = self._get_decorated_entry(
                subtree, pos[1:], widget, is_first)
        else:
            entry = widget or entry
        if isinstance(tree, (DecoratedTree, NestedTree)):  # has decorate-API
            isf = len(pos) < 2
            if not isf and isinstance(tree[pos[0]], Tree):
                isf = (tree[pos[0]].parent_position(pos[1])
                       is None) or not is_first
            entry = tree.decorate(pos[0], entry, is_first=isf)
        return entry

    def get_decorated(self, pos):
        return self._get_decorated_entry(self._tree, pos)

    def decorate(self, pos, widget, is_first=True):
        return self._get_decorated_entry(self._tree, pos, widget, is_first)

    # Collapse API
    def _get_subtree_for(self, pos):
        """returns Tree that manages pos[-1]"""
        res = self._tree
        candidate = self._lookup_entry(self._tree, pos[:-1])
        if isinstance(candidate, Tree):
            res = candidate
        return res

    def collapsible(self, pos):
        res = False
        subtree = self._get_subtree_for(pos)
        if isinstance(subtree, (CollapseMixin, NestedTree)):
            res = subtree.collapsible(pos[-1])
        return res

    def is_collapsed(self, pos):
        res = False
        subtree = self._get_subtree_for(pos)
        if isinstance(subtree, (CollapseMixin, NestedTree)):
            res = subtree.is_collapsed(pos[-1])
        return res

    def toggle_collapsed(self, pos):
        subtree = self._get_subtree_for(pos)
        if isinstance(subtree, (CollapseMixin, NestedTree)):
            subtree.toggle_collapsed(pos)

    def collapse(self, pos):
        subtree = self._get_subtree_for(pos)
        if isinstance(subtree, (CollapseMixin, NestedTree)):
            subtree.collapse(pos[-1])

    def collapse_all(self):
        self._collapse_all(self._tree, self.root)

    def _collapse_all(self, tree, pos=None):
        if pos is not None:
            if isinstance(tree, (CollapseMixin, NestedTree)):
                tree.expand_all()

            if len(pos) > 1:
                self._collapse_all(tree[pos[0]], pos[1:])
            nextpos = tree.next_position(pos[0])
            if nextpos is not None:
                nentry = tree[nextpos]
                if isinstance(nentry, Tree):
                    self._collapse_all(nentry, (nentry.root,))
                self._collapse_all(tree, (nextpos,))
            if isinstance(tree, (CollapseMixin, NestedTree)):
                tree.collapse_all()

    def expand(self, pos):
        subtree = self._get_subtree_for(pos)
        if isinstance(subtree, (CollapseMixin, NestedTree)):
            subtree.expand(pos[-1])

    def expand_all(self):
        self._expand_all(self._tree, self.root)

    def _expand_all(self, tree, pos=None):
        if pos is not None:
            if isinstance(tree, (CollapseMixin, NestedTree)):
                tree.expand_all()
            if len(pos) > 1:
                self._expand_all(tree[pos[0]], pos[1:])
            nextpos = tree.next_position(pos[0])
            if nextpos is not None:
                nentry = tree[nextpos]
                if isinstance(nentry, Tree):
                    self._expand_all(nentry, (nentry.root,))
                self._expand_all(tree, (nextpos,))
            if isinstance(tree, (CollapseMixin, NestedTree)):
                tree.expand_all()

    def is_leaf(self, pos, outmost_only=False):
        return self.first_child_position(pos, outmost_only) is None

    ################################################
    # Tree API
    ################################################
    def parent_position(self, pos):
        candidate_pos = self._parent_position(self._tree, pos)
        # return sanitized path (ensure it points to content, not a subtree)
        return self._sanitize_position(candidate_pos)

    def _parent_position(self, tree, pos):
        candidate_pos = None
        if len(pos) > 1:
            # get the deepest subtree
            subtree_pos = pos[:-1]
            subtree = self._lookup_entry(tree, subtree_pos)
            # get parent for our position in this subtree
            least_pos = pos[-1]
            subparent_pos = subtree.parent_position(least_pos)
            if subparent_pos is not None:
                # in case there is one, we are done, the position we look for
                # is the path up to the subtree plus the local parent position.
                candidate_pos = subtree_pos + (subparent_pos,)
            else:
                # otherwise we recur and look for subtree's parent in the next
                # outer tree
                candidate_pos = self._parent_position(self._tree, subtree_pos)
        else:
            # there is only one position in the path, we return its parent in
            # the outmost tree
            outer_parent = self._tree.parent_position(pos[0])
            if outer_parent is not None:
                # result needs to be valid position (tuple of local positions)
                candidate_pos = outer_parent,
        return candidate_pos

    def first_child_position(self, pos, outmost_only=False):
        childpos = self._first_child_position(self._tree, pos, outmost_only)
        return self._sanitize_position(childpos, self._tree)

    def _first_child_position(self, tree, pos, outmost_only=False):
        childpos = None
        # get content at first path element in outmost tree
        entry = tree[pos[0]]
        if isinstance(entry, Tree) and not outmost_only and len(pos) > 1:
            # this points to a tree and we don't check the outmost tree only
            # recur: get first child in the subtree for remaining path
            subchild = self._first_child_position(entry, pos[1:])
            if subchild is not None:
                # found a childposition, re-append the path up to this subtree
                childpos = (pos[0],) + subchild
                return childpos
            else:
                # continue in the next outer tree only if we do not drop
                # "covered" parts and the position path points to a parent-less
                # position in the subtree.
                if (entry.parent_position(pos[1]) is not None or not
                        self._interpret_covered):
                    return None

        # return the first child of the outmost tree
        outerchild = tree.first_child_position(pos[0])
        if outerchild is not None:
            childpos = outerchild,
        return childpos

    def last_child_position(self, pos, outmost_only=False):
        childpos = self._last_child_position(self._tree, pos, outmost_only)
        return self._sanitize_position(childpos, self._tree)

    def _last_child_position(self, tree, pos, outmost_only=False):
        childpos = None
        # get content at first path element in outmost tree
        entry = tree[pos[0]]
        if isinstance(entry, Tree) and not outmost_only and len(pos) > 1:
            # this points to a tree and we don't check the outmost tree only

            # get last child in the outmost tree if we do not drop "covered"
            # parts and the position path points to a root of the subtree.
            if self._interpret_covered:
                if entry.parent_position(pos[1]) is None:
                    # return the last child of the outmost tree
                    outerchild = tree.last_child_position(pos[0])
                    if outerchild is not None:
                        childpos = outerchild,

            # continue as if we have not found anything yet
            if childpos is None:
                # recur: get last child in the subtree for remaining path
                subchild = self._last_child_position(entry, pos[1:])
                if subchild is not None:
                    # found a childposition, re-prepend path up to this subtree
                    childpos = (pos[0],) + subchild
        else:
            # outmost position element does not point to a tree:
            # return the last child of the outmost tree
            outerchild = tree.last_child_position(pos[0])
            if outerchild is not None:
                childpos = outerchild,
        return childpos

    def _next_sibling_position(self, tree, pos):
        candidate = None
        if len(pos) > 1:
            # if position path does not point to position in outmost tree,
            # first get the subtree as pointed out by first dimension, recur
            # and check if some inner tree already returns a sibling
            subtree = tree[pos[0]]
            subsibling_pos = self._next_sibling_position(subtree, pos[1:])
            if subsibling_pos is not None:
                # we found our sibling, prepend the path up to the subtree
                candidate = pos[:1] + subsibling_pos
            else:
                # no deeper tree has sibling. If inner position is root node
                # the sibling in the outer tree is a valid candidate
                subparent = subtree.parent_position(pos[1])
                if subparent is None:
                    # check if outer tree defines sibling
                    next_sib = tree.next_sibling_position(pos[0])
                    if next_sib is not None:
                        # it has, we found our candidate
                        candidate = next_sib,
                # if the inner position has depth 1, then the first child
                # of its parent in the outer tree can be seen as candidate for
                # this position next sibling. Those live in the shadow of the
                # inner tree and are hidden unless requested otherwise
                elif subtree.parent_position(subparent) is None and \
                        self._interpret_covered:
                    # we respect "covered" stuff and inner position has depth 1
                    # get (possibly nested) first child in outer tree
                    candidate = self._first_child_position(tree, pos[:1])

        else:
            # the position path points to the outmost tree
            # just return its next sibling in the outmost tree
            next_sib = tree.next_sibling_position(pos[0])
            if next_sib is not None:
                candidate = next_sib,
        return candidate

    def next_sibling_position(self, pos):
        candidate = self._next_sibling_position(self._tree, pos)
        return self._sanitize_position(candidate, self._tree)

    def _prev_sibling_position(self, tree, pos):
        candidate = None
        if len(pos) > 1:
            # if position path does not point to position in outmost tree,
            # first get the subtree as pointed out by first dimension, recur
            # and check if some inner tree already returns a sibling
            subtree = tree[pos[0]]
            subsibling_pos = self._prev_sibling_position(subtree, pos[1:])
            if subsibling_pos is not None:
                # we found our sibling, prepend the path up to the subtree
                candidate = pos[:1] + subsibling_pos
            else:
                # no deeper tree has sibling. If inner position is root node
                # the sibling in the outer tree is a valid candidate
                subparent = subtree.parent_position(pos[1])
                if subparent is None:
                    prev_sib = tree.prev_sibling_position(pos[0])
                    if prev_sib is not None:
                        candidate = prev_sib,
                        return candidate
            # my position could be "hidden" by being child of a
            # position pointing to a Tree object (which is then unfolded).
            if self._interpret_covered:
                # we respect "covered" stuff:
                # if parent is Tree, return last child of its (last) root
                parent_pos = self._parent_position(tree, pos)
                if parent_pos is not None:
                    parent = self._lookup_entry(self._tree, parent_pos)
                    if isinstance(parent, Tree):
                        sib = parent.last_sibling_position(parent.root)
                        candidate = parent.last_child_position(sib)
                        if candidate is not None:
                            candidate = parent_pos + (candidate,)
        else:
            # pos points to position in outmost tree
            prev_sib = tree.prev_sibling_position(pos[0])
            if prev_sib is not None:
                candidate = prev_sib,
        # In case our new candidate points to a Tree, pick its last root node
        if candidate is not None:
            entry = self._lookup_entry(tree, candidate)
            if isinstance(entry, Tree):
                candidate = (candidate) + (entry.last_sibling_position(entry.root),)
        return candidate

    def prev_sibling_position(self, pos):
        candidate = self._prev_sibling_position(self._tree, pos)
        return self._sanitize_position(candidate, self._tree)

    def last_decendant(self, pos):
        def lastd(pos):
            c = self.last_child_position(pos)
            if c is not None:
                c = self.last_sibling_position(c)
            return c
        return self._last_in_direction(pos, lastd)

########NEW FILE########
__FILENAME__ = tree
# Copyright (C) 2013  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.

import logging


class Tree(object):
    """
    Base class for a tree strucures that can be displayed by :class:`TreeBox`
    widgets. An instance defines a structure by defining local transformations
    on positions. That is, by overwriting

     * `next_sibling_position`
     * `prev_sibling_position`
     * `parent_position`
     * `first_child_position`
     * `last_child_position`

    that compute the next position in the respective direction. Also, they need
    to implement method `__getitem__` that returns a :class:`Widget` for a
    given position.

    The type of objects used as positions may vary in subclasses and is
    deliberately unspecified for the base class.

    This base class already implements methods based on the local
    transformations above. These include :meth:`depth`, :meth:`last_decendant`
    and :meth:`[next|prev]_position <next_position>` that computes
    next/previous positions in depth-first order.
    """
    root = None

    # local helper
    def _get(self, pos):
        """loads widget at given position; handling invalid arguments"""
        res = None, None
        if pos is not None:
            try:
                res = self[pos], pos
            except (IndexError, KeyError):
                pass
        return res

    def _next_of_kin(self, pos):
        """
        looks up the next sibling of the closest ancestor with not-None next
        siblings.
        """
        candidate = None
        parent = self.parent_position(pos)
        if parent is not None:
            candidate = self.next_sibling_position(parent)
            if candidate is None:
                candidate = self._next_of_kin(parent)
        return candidate

    def _last_in_direction(self, starting_pos, direction):
        """
        recursively move in the tree in given direction
        and return the last position.

        :param starting_pos: position to start at
        :param direction: callable that transforms a position into a position.
        """
        next_pos = direction(starting_pos)
        if next_pos is None:
            return starting_pos
        else:
            return self._last_in_direction(next_pos, direction)

    def depth(self, pos):
        """determine depth of node at pos"""
        parent = self.parent_position(pos)
        if parent is None:
            return 0
        else:
            return self.depth(parent) + 1

    def is_leaf(self, pos):
        """checks if given position has no children"""
        return self.first_child_position(pos) is None

    def first_ancestor(self, pos):
        """
        position of pos's ancestor with depth 0. Usually, this should return
        the root node, but a :class:`Tree` might represent a forrest - have
        multiple nodes without parent.
        """
        return self._last_in_direction(pos, self.parent_position)

    def last_decendant(self, pos):
        """position of last (in DFO) decendant of pos"""
        return self._last_in_direction(pos, self.last_child_position)

    def last_sibling_position(self, pos):
        """position of last sibling of pos"""
        return self._last_in_direction(pos, self.next_sibling_position)

    def first_sibling_position(self, pos):
        """position of first sibling of pos"""
        return self._last_in_direction(pos, self.prev_sibling_position)

    def next_position(self, pos):
        """returns the next position in depth-first order"""
        candidate = None
        if pos is not None:
            candidate = self.first_child_position(pos)
            if candidate is None:
                candidate = self.next_sibling_position(pos)
                if candidate is None:
                    candidate = self._next_of_kin(pos)
        return candidate

    def prev_position(self, pos):
        """returns the previous position in depth-first order"""
        candidate = None
        if pos is not None:
            prevsib = self.prev_sibling_position(pos)  # is None if first
            if prevsib is not None:
                candidate = self.last_decendant(prevsib)
            else:
                parent = self.parent_position(pos)
                if parent is not None:
                    candidate = parent
        return candidate

    def positions(self, reverse=False):
        """returns a generator that walks the positions of this tree in DFO"""
        def Posgen(reverse):
            if reverse:
                lastrootsib = self.last_sibling_position(self.root)
                current = self.last_decendant(lastrootsib)
                while current is not None:
                    yield current
                    current = self.prev_position(current)
            else:
                current = self.root
                while current is not None:
                    yield current
                    current = self.next_position(current)
        return Posgen(reverse)

    ####################################################################
    # End of high-level helper implementation. The following need to be
    # overwritten by subclasses
    ####################################################################
    def parent_position(self, pos):
        """returns the position of the parent node of the node at `pos`
        or `None` if none exists."""
        return None

    def first_child_position(self, pos):
        """returns the position of the first child of the node at `pos`,
        or `None` if none exists."""
        return None

    def last_child_position(self, pos):
        """returns the position of the last child of the node at `pos`,
        or `None` if none exists."""
        return None

    def next_sibling_position(self, pos):
        """returns the position of the next sibling of the node at `pos`,
        or `None` if none exists."""
        return None

    def prev_sibling_position(self, pos):
        """returns the position of the previous sibling of the node at `pos`,
        or `None` if none exists."""
        return None


class SimpleTree(Tree):
    """
    Walks on a given fixed acyclic structure given as a list of nodes; every
    node is a tuple `(content, children)`, where `content` is a `urwid.Widget`
    to be displayed at that position and `children` is either `None` or a list
    of nodes.

    Positions are lists of integers determining a path from the root node with
    position `(0,)`.
    """
    def __init__(self, treelist):
        self._treelist = treelist
        self.root = (0,) if treelist else None
        Tree.__init__(self)

    # a few local helper methods
    def _get_substructure(self, treelist, pos):
        """recursive helper to look up node-tuple for `pos` in `treelist`"""
        subtree = None
        if len(pos) > 1:
            subtree = self._get_substructure(treelist[pos[0]][1], pos[1:])
        else:
            try:
                subtree = treelist[pos[0]]
            except (IndexError, TypeError):
                pass
        return subtree

    def _get_node(self, treelist, pos):
        """
        look up widget at `pos` of `treelist`; default to None if
        nonexistent.
        """
        node = None
        if pos is not None:
            subtree = self._get_substructure(treelist, pos)
            if subtree is not None:
                node = subtree[0]
        return node

    def _confirm_pos(self, pos):
        """look up widget for pos and default to None"""
        candidate = None
        if self._get_node(self._treelist, pos) is not None:
            candidate = pos
        return candidate

    # Tree API
    def __getitem__(self, pos):
        return self._get_node(self._treelist, pos)

    def parent_position(self, pos):
        parent = None
        if pos is not None:
            if len(pos) > 1:
                parent = pos[:-1]
        return parent

    def first_child_position(self, pos):
        return self._confirm_pos(pos + (0,))

    def last_child_position(self, pos):
        candidate = None
        subtree = self._get_substructure(self._treelist, pos)
        if subtree is not None:
            children = subtree[1]
            if children is not None:
                candidate = pos + (len(children) - 1,)
        return candidate

    def next_sibling_position(self, pos):
        return self._confirm_pos(pos[:-1] + (pos[-1] + 1,))

    def prev_sibling_position(self, pos):
        return pos[:-1] + (pos[-1] - 1,) if (pos[-1] > 0) else None

    # optimizations
    def depth(self, pos):
        """more performant implementation due to specific structure of pos"""
        return len(pos) - 1

########NEW FILE########
__FILENAME__ = widgets
# Copyright (C) 2013  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.

import urwid
import logging
from urwid import WidgetWrap, ListBox
from urwid import signals
from decoration import DecoratedTree, CollapseMixin
from nested import NestedTree
from lru_cache import lru_cache

# The following are used to check dynamically if a tree offers sub-APIs


def implementsDecorateAPI(tree):
    """determines if given tree offers line decoration"""
    return isinstance(tree, (DecoratedTree, NestedTree))


def implementsCollapseAPI(tree):
    """determines if given tree can collapse positions"""
    res = False
    if isinstance(tree, (CollapseMixin, NestedTree)):
        res = True
    return res


class TreeListWalker(urwid.ListWalker):
    """
    ListWalker to walk through a class:`Tree`.

    This translates a :class:`Tree` into a :class:`urwid.ListWalker` that is
    digestible by :class:`urwid.ListBox`.
    It uses :meth:`Tree.[next|prev]_position <Tree.next_position>` to determine
    the next/previous position in depth first order.
    """
    def __init__(self, tree, focus=None):
        """
        :param tree: the tree to be displayed
        :type tree: Tree
        :param focus: position of node to be focussed initially.
            This has to be a valid position in the Tree.
            It defaults to the value of `Tree.root`.
        """
        self._tree = tree
        self._focus = focus or tree.root
        self.root = tree.root

    @lru_cache()
    def __getitem__(self, pos):
        """gets (possibly decorated) line widget at given position"""
        if implementsDecorateAPI(self._tree):
            entry = self._tree.get_decorated(pos)
        else:
            entry = self._tree[pos]
        return entry

    def clear_cache(self):
        """removes all cached lines"""
        self.__getitem__.cache_clear()

    def _get(self, pos):
        """looks up widget for given position; handling invalid arguments"""
        res = None, None
        if pos is not None:
            try:
                res = self[pos], pos
            except (IndexError, KeyError):
                pass
        return res

    # List Walker API.
    def get_focus(self):
        return self._get(self._focus)

    def set_focus(self, pos):
        self._focus = pos

    def get_next(self, pos):
        return self._get(self._tree.next_position(pos))

    def get_prev(self, pos):
        return self._get(self._tree.prev_position(pos))

    def positions(self, reverse=False):
        """returns a generator that walks the tree's positions"""
        return self._tree.positions(reverse)
    # end of List Walker API


class TreeBox(WidgetWrap):
    """
    A widget that displays a given :class:`Tree`.
    This is essentially a :class:`ListBox` with the ability to move the focus
    based on directions in the Tree and to collapse/expand subtrees if
    possible.

    TreeBox interprets `left/right` as well as `page up/`page down` to move the
    focus to parent/first child and next/previous sibling respectively. All
    other keys are passed to the underlying ListBox.
    """

    def __init__(self, tree, focus=None):
        """
        :param tree: tree of widgets to be displayed.
        :type tree: Tree
        :param focus: initially focussed position
        """
        self._tree = tree
        self._walker = TreeListWalker(tree)
        self._outer_list = ListBox(self._walker)
        if focus is not None:
            self._outer_list.set_focus(focus)
        self.__super.__init__(self._outer_list)

    # Widget API
    def get_focus(self):
        return self._outer_list.get_focus()

    def set_focus(self, pos):
        return self._outer_list.set_focus(pos)

    def refresh(self):
        self._walker.clear_cache()
        signals.emit_signal(self._walker, "modified")

    def keypress(self, size, key):
        key = self._outer_list.keypress(size, key)
        if key in ['left', 'right', '[', ']', '-', '+', 'C', 'E', ]:
            if key == 'left':
                self.focus_parent()
            elif key == 'right':
                self.focus_first_child()
            elif key == '[':
                self.focus_prev_sibling()
            elif key == ']':
                self.focus_next_sibling()
            elif key == '-':
                self.collapse_focussed()
            elif key == '+':
                self.expand_focussed()
            elif key == 'C':
                self.collapse_all()
            elif key == 'E':
                self.expand_all()
            # This is a hack around ListBox misbehaving:
            # it seems impossible to set the focus without calling keypress as
            # otherwise the change becomes visible only after the next render()
            return self._outer_list.keypress(size, None)
        else:
            return self._outer_list.keypress(size, key)

    # Collapse operations
    def collapse_focussed(self):
        """
        Collapse currently focussed position; works only if the underlying
        tree allows it.
        """
        if implementsCollapseAPI(self._tree):
            w, focuspos = self.get_focus()
            self._tree.collapse(focuspos)
            self._walker.clear_cache()
            self.refresh()

    def expand_focussed(self):
        """
        Expand currently focussed position; works only if the underlying
        tree allows it.
        """
        if implementsCollapseAPI(self._tree):
            w, focuspos = self.get_focus()
            self._tree.expand(focuspos)
            self._walker.clear_cache()
            self.refresh()

    def collapse_all(self):
        """
        Collapse all positions; works only if the underlying tree allows it.
        """
        if implementsCollapseAPI(self._tree):
            self._tree.collapse_all()
            self.set_focus(self._tree.root)
            self._walker.clear_cache()
            self.refresh()

    def expand_all(self):
        """
        Expand all positions; works only if the underlying tree allows it.
        """
        if implementsCollapseAPI(self._tree):
            self._tree.expand_all()
            self._walker.clear_cache()
            self.refresh()

    # Tree based focus movement
    def focus_parent(self):
        """move focus to parent node of currently focussed one"""
        w, focuspos = self.get_focus()
        parent = self._tree.parent_position(focuspos)
        if parent is not None:
            self.set_focus(parent)

    def focus_first_child(self):
        """move focus to first child of currently focussed one"""
        w, focuspos = self.get_focus()
        child = self._tree.first_child_position(focuspos)
        if child is not None:
            self.set_focus(child)

    def focus_last_child(self):
        """move focus to last child of currently focussed one"""
        w, focuspos = self.get_focus()
        child = self._tree.last_child_position(focuspos)
        if child is not None:
            self.set_focus(child)

    def focus_next_sibling(self):
        """move focus to next sibling of currently focussed one"""
        w, focuspos = self.get_focus()
        sib = self._tree.next_sibling_position(focuspos)
        if sib is not None:
            self.set_focus(sib)

    def focus_prev_sibling(self):
        """move focus to previous sibling of currently focussed one"""
        w, focuspos = self.get_focus()
        sib = self._tree.prev_sibling_position(focuspos)
        if sib is not None:
            self.set_focus(sib)

    def focus_next(self):
        """move focus to next position (DFO)"""
        w, focuspos = self.get_focus()
        next = self._tree.next_position(focuspos)
        if next is not None:
            self.set_focus(next)

    def focus_prev(self):
        """move focus to previous position (DFO)"""
        w, focuspos = self.get_focus()
        prev = self._tree.prev_position(focuspos)
        if prev is not None:
            self.set_focus(prev)

########NEW FILE########
__FILENAME__ = helper
# -*- coding: utf-8 -*-
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
from datetime import timedelta
from datetime import datetime
from collections import deque
import subprocess
import shlex
import email
import mimetypes
import os
import re
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
import urwid
import magic
from twisted.internet import reactor
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.defer import Deferred
import StringIO
import logging


def split_commandline(s, comments=False, posix=True):
    """
    splits semi-colon separated commandlines
    """
    # shlex seems to remove unescaped quotes and backslashes
    s = s.replace('\\', '\\\\')
    s = s.replace('\'', '\\\'')
    s = s.replace('\"', '\\\"')
    # encode s to utf-8 for shlex
    if isinstance(s, unicode):
        s = s.encode('utf-8')
    lex = shlex.shlex(s, posix=posix)
    lex.whitespace_split = True
    lex.whitespace = ';'
    if not comments:
        lex.commenters = ''
    return list(lex)


def split_commandstring(cmdstring):
    """
    split command string into a list of strings to pass on to subprocess.Popen
    and the like. This simply calls shlex.split but works also with unicode
    bytestrings.
    """
    if isinstance(cmdstring, unicode):
        cmdstring = cmdstring.encode('utf-8', errors='ignore')
    return shlex.split(cmdstring)


def safely_get(clb, E, on_error=''):
    """
    returns result of :func:`clb` and falls back to `on_error`
    in case exception `E` is raised.

    :param clb: function to evaluate
    :type clb: callable
    :param E: exception to catch
    :type E: Exception
    :param on_error: default string returned when exception is caught
    :type on_error: str
    """
    try:
        return clb()
    except E:
        return on_error


def string_sanitize(string, tab_width=8):
    r"""
    strips, and replaces non-printable characters

    :param tab_width: number of spaces to replace tabs with. Read from
                      `globals.tabwidth` setting if `None`
    :type tab_width: int or `None`

    >>> string_sanitize(' foo\rbar ', 8)
    ' foobar '
    >>> string_sanitize('foo\tbar', 8)
    'foo     bar'
    >>> string_sanitize('foo\t\tbar', 8)
    'foo             bar'
    """

    string = string.replace('\r', '')

    lines = list()
    for line in string.split('\n'):
        tab_count = line.count('\t')

        if tab_count > 0:
            line_length = 0
            new_line = list()
            for i, chunk in enumerate(line.split('\t')):
                line_length += len(chunk)
                new_line.append(chunk)

                if i < tab_count:
                    next_tab_stop_in = tab_width - (line_length % tab_width)
                    new_line.append(' ' * next_tab_stop_in)
                    line_length += next_tab_stop_in
            lines.append(''.join(new_line))
        else:
            lines.append(line)

    return '\n'.join(lines)


def string_decode(string, enc='ascii'):
    """
    safely decodes string to unicode bytestring, respecting `enc` as a hint.
    """

    if enc is None:
        enc = 'ascii'
    try:
        string = unicode(string, enc, errors='replace')
    except LookupError:  # malformed enc string
        string = string.decode('ascii', errors='replace')
    except TypeError:  # already unicode
        pass
    return string


def shorten(string, maxlen):
    """shortens string if longer than maxlen, appending ellipsis"""
    if maxlen > 1 and len(string) > maxlen:
        string = string[:maxlen - 1] + u'\u2026'
    return string[:maxlen]


def shorten_author_string(authors_string, maxlength):
    """
    Parse a list of authors concatenated as a text string (comma
    separated) and smartly adjust them to maxlength.

    1) If the complete list of sender names does not fit in maxlength, it
    tries to shorten names by using only the first part of each.

    2) If the list is still too long, hide authors according to the
    following priority:

      - First author is always shown (if too long is shorten with ellipsis)

      - If possible, last author is also shown (if too long, uses ellipsis)

      - If there are more than 2 authors in the thread, show the
        maximum of them. More recent senders have higher priority.

      - If it is finally necessary to hide any author, an ellipsis
        between first and next authors is added.

    >>> authors = u'King Kong, Mucho Muchacho, Jaime Huerta, Flash Gordon'
    >>> print shorten_author_string(authors, 60)
    King Kong, Mucho Muchacho, Jaime Huerta, Flash Gordon
    >>> print shorten_author_string(authors, 40)
    King, Mucho, Jaime, Flash
    >>> print shorten_author_string(authors, 20)
    King, …, Jai…, Flash
    >>> print shorten_author_string(authors, 10)
    King, …
    >>> print shorten_author_string(authors, 2)
    K…
    >>> print shorten_author_string(authors, 1)
    K
    """

    # I will create a list of authors by parsing author_string. I use
    # deque to do popleft without performance penalties
    authors = deque()

    # If author list is too long, it uses only the first part of each
    # name (gmail style)
    short_names = len(authors_string) > maxlength
    for au in authors_string.split(", "):
        if short_names:
            author_as_list = au.split()
            if len(author_as_list) > 0:
                authors.append(author_as_list[0])
        else:
            authors.append(au)

    # Author chain will contain the list of author strings to be
    # concatenated using commas for the final formatted author_string.
    authors_chain = deque()

    if len(authors) == 0:
        return u''

    # reserve space for first author
    first_au = shorten(authors.popleft(), maxlength)
    remaining_length = maxlength - len(first_au)

    # Tries to add an ellipsis if no space to show more than 1 author
    if authors and maxlength > 3 and remaining_length < 3:
        first_au = shorten(first_au, maxlength - 3)
        remaining_length += 3

    # Tries to add as more authors as possible. It takes into account
    # that if any author will be hidden, and ellipsis should be added
    while authors and remaining_length >= 3:
        au = authors.pop()
        if len(au) > 1 and (remaining_length == 3 or (authors and
                                                      remaining_length < 7)):
            authors_chain.appendleft(u'\u2026')
            break
        else:
            if authors:
                # 5= ellipsis + 2 x comma and space used as separators
                au_string = shorten(au, remaining_length - 5)
            else:
                # 2 = comma and space used as separator
                au_string = shorten(au, remaining_length - 2)
            remaining_length -= len(au_string) + 2
            authors_chain.appendleft(au_string)

    # Add the first author to the list and concatenate list
    authors_chain.appendleft(first_au)
    authorsstring = ', '.join(authors_chain)
    return authorsstring


def pretty_datetime(d):
    """
    translates :class:`datetime` `d` to a "sup-style" human readable string.

    >>> now = datetime.now()
    >>> now.strftime('%c')
    'Sat 31 Mar 2012 14:47:26 '
    >>> pretty_datetime(now)
    u'just now'
    >>> pretty_datetime(now - timedelta(minutes=1))
    u'1min ago'
    >>> pretty_datetime(now - timedelta(hours=5))
    u'5h ago'
    >>> pretty_datetime(now - timedelta(hours=12))
    u'02:54am'
    >>> pretty_datetime(now - timedelta(days=1))
    u'yest 02pm'
    >>> pretty_datetime(now - timedelta(days=2))
    u'Thu 02pm'
    >>> pretty_datetime(now - timedelta(days=7))
    u'Mar 24'
    >>> pretty_datetime(now - timedelta(days=356))
    u'Apr 2011'
    """
    ampm = d.strftime('%P')
    if len(ampm):
        hourfmt = '%I' + ampm
        hourminfmt = '%I:%M' + ampm
    else:
        hourfmt = '%Hh'
        hourminfmt = '%H:%M'

    now = datetime.now()
    today = now.date()
    if d.date() == today or d > now - timedelta(hours=6):
        delta = datetime.now() - d
        if delta.seconds < 60:
            string = 'just now'
        elif delta.seconds < 3600:
            string = '%dmin ago' % (delta.seconds / 60)
        elif delta.seconds < 6 * 3600:
            string = '%dh ago' % (delta.seconds / 3600)
        else:
            string = d.strftime(hourminfmt)
    elif d.date() == today - timedelta(1):
        string = d.strftime('yest ' + hourfmt)
    elif d.date() > today - timedelta(7):
        string = d.strftime('%a ' + hourfmt)
    elif d.year != today.year:
        string = d.strftime('%b %Y')
    else:
        string = d.strftime('%b %d')
    return string_decode(string, 'UTF-8')


def call_cmd(cmdlist, stdin=None):
    """
    get a shell commands output, error message and return value and immediately
    return.

    .. warning::

        This returns with the first screen content for interactive commands.

    :param cmdlist: shellcommand to call, already splitted into a list accepted
                    by :meth:`subprocess.Popen`
    :type cmdlist: list of str
    :param stdin: string to pipe to the process
    :type stdin: str
    :return: triple of stdout, stderr, return value of the shell command
    :rtype: str, str, int
    """

    out, err, ret = '', '', 0
    try:
        if stdin:
            proc = subprocess.Popen(cmdlist, stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            out, err = proc.communicate(stdin)
            ret = proc.poll()
        else:
            try:
                out = subprocess.check_output(cmdlist)
            except subprocess.CalledProcessError as e:
                err = e.output
                ret = e.returncode
    except OSError as e:
        err = e.strerror
        ret = e.errno

    out = string_decode(out, urwid.util.detected_encoding)
    err = string_decode(err, urwid.util.detected_encoding)
    return out, err, ret


def call_cmd_async(cmdlist, stdin=None, env=None):
    """
    get a shell commands output, error message and return value as a deferred.

    :type cmdlist: list of str
    :param stdin: string to pipe to the process
    :type stdin: str
    :return: deferred that calls back with triple of stdout, stderr and
             return value of the shell command
    :rtype: `twisted.internet.defer.Deferred`
    """

    class _EverythingGetter(ProcessProtocol):
        def __init__(self, deferred):
            self.deferred = deferred
            self.outBuf = StringIO.StringIO()
            self.errBuf = StringIO.StringIO()
            self.outReceived = self.outBuf.write
            self.errReceived = self.errBuf.write

        def processEnded(self, status):
            termenc = urwid.util.detected_encoding
            out = string_decode(self.outBuf.getvalue(), termenc)
            err = string_decode(self.errBuf.getvalue(), termenc)
            if status.value.exitCode == 0:
                self.deferred.callback(out)
            else:
                terminated_obj = status.value
                terminated_obj.stderr = err
                self.deferred.errback(terminated_obj)

    d = Deferred()
    environment = os.environ
    if env is not None:
        environment.update(env)
    logging.debug('ENV = %s' % environment)
    logging.debug('CMD = %s' % cmdlist)
    proc = reactor.spawnProcess(_EverythingGetter(d), executable=cmdlist[0],
                                env=environment,
                                args=cmdlist)
    if stdin:
        logging.debug('writing to stdin')
        proc.write(stdin)
        proc.closeStdin()
    return d


def guess_mimetype(blob):
    """
    uses file magic to determine the mime-type of the given data blob.

    :param blob: file content as read by file.read()
    :type blob: data
    :returns: mime-type, falls back to 'application/octet-stream'
    :rtype: str
    """
    mimetype = 'application/octet-stream'
    # this is a bit of a hack to support different versions of python magic.
    # Hopefully at some point this will no longer be necessary
    #
    # the version with open() is the bindings shipped with the file source from
    # http://darwinsys.com/file/ - this is what is used by the python-magic
    # package on Debian/Ubuntu. However, it is not available on pypi/via pip.
    #
    # the version with from_buffer() is available at
    # https://github.com/ahupp/python-magic and directly installable via pip.
    #
    # for more detail see https://github.com/pazz/alot/pull/588
    if hasattr(magic, 'open'):
        m = magic.open(magic.MAGIC_MIME_TYPE)
        m.load()
        magictype = m.buffer(blob)
    elif hasattr(magic, 'from_buffer'):
        magictype = magic.from_buffer(blob, mime=True)
    else:
        raise Exception('Unknown magic API')

    # libmagic does not always return proper mimetype strings, cf. issue #459
    if re.match(r'\w+\/\w+', magictype):
        mimetype = magictype
    return mimetype


def guess_encoding(blob):
    """
    uses file magic to determine the encoding of the given data blob.

    :param blob: file content as read by file.read()
    :type blob: data
    :returns: encoding
    :rtype: str
    """
    # this is a bit of a hack to support different versions of python magic.
    # Hopefully at some point this will no longer be necessary
    #
    # the version with open() is the bindings shipped with the file source from
    # http://darwinsys.com/file/ - this is what is used by the python-magic
    # package on Debian/Ubuntu.  However it is not available on pypi/via pip.
    #
    # the version with from_buffer() is available at
    # https://github.com/ahupp/python-magic and directly installable via pip.
    #
    # for more detail see https://github.com/pazz/alot/pull/588
    if hasattr(magic, 'open'):
        m = magic.open(magic.MAGIC_MIME_ENCODING)
        m.load()
        return m.buffer(blob)
    elif hasattr(magic, 'from_buffer'):
        m = magic.Magic(mime_encoding=True)
        return m.from_buffer(blob)
    else:
        raise Exception('Unknown magic API')


def libmagic_version_at_least(version):
    """
    checks if the libmagic library installed is more recent than a given
    version.

    :param version: minimum version expected in the form XYY (i.e. 5.14 -> 514)
                    with XYY >= 513
    """
    if hasattr(magic, 'open'):
        magic_wrapper = magic._libraries['magic']
    elif hasattr(magic, 'from_buffer'):
        magic_wrapper = magic.libmagic
    else:
        raise Exception('Unknown magic API')

    if not hasattr(magic_wrapper, 'magic_version'):
        # The magic_version function has been introduced in libmagic 5.13,
        # if it's not present, we can't guess right, so let's assume False
        return False

    return (magic_wrapper.magic_version >= version)


# TODO: make this work on blobs, not paths
def mimewrap(path, filename=None, ctype=None):
    content = open(path, 'rb').read()
    if not ctype:
        ctype = guess_mimetype(content)
        # libmagic < 5.12 incorrectly detects excel/powerpoint files as
        # 'application/msword' (see #179 and #186 in libmagic bugtracker)
        # This is a workaround, based on file extension, useful as long
        # as distributions still ship libmagic 5.11.
        if (ctype == 'application/msword' and
                not libmagic_version_at_least(513)):
            mimetype, encoding = mimetypes.guess_type(path)
            if mimetype:
                ctype = mimetype

    maintype, subtype = ctype.split('/', 1)
    if maintype == 'text':
        part = MIMEText(content.decode(guess_encoding(content), 'replace'),
                        _subtype=subtype,
                        _charset='utf-8')
    elif maintype == 'image':
        part = MIMEImage(content, _subtype=subtype)
    elif maintype == 'audio':
        part = MIMEAudio(content, _subtype=subtype)
    else:
        part = MIMEBase(maintype, subtype)
        part.set_payload(content)
        # Encode the payload using Base64
        email.encoders.encode_base64(part)
    # Set the filename parameter
    if not filename:
        filename = os.path.basename(path)
    part.add_header('Content-Disposition', 'attachment',
                    filename=filename)
    return part


def shell_quote(text):
    r'''
    >>> print(shell_quote("hello"))
    'hello'
    >>> print(shell_quote("hello'there"))
    'hello'"'"'there'
    '''
    return "'%s'" % text.replace("'", """'"'"'""")


def tag_cmp(a, b):
    r'''
    Sorting tags using this function puts all tags of length 1 at the
    beginning. This groups all tags mapped to unicode characters.
    '''
    if min(len(a), len(b)) == 1 and max(len(a), len(b)) > 1:
        return cmp(len(a), len(b))
    else:
        return cmp(a.lower(), b.lower())


def humanize_size(size):
    r'''
    >>> humanize_size(1)
    '1'
    >>> humanize_size(123)
    '123'
    >>> humanize_size(1234)
    '1K'
    >>> humanize_size(1234 * 1024)
    '1.2M'
    >>> humanize_size(1234 * 1024 * 1024)
    '1234.0M'
    '''
    for factor, format_string in ((1, '%i'),
                                  (1024, '%iK'),
                                  (1024 * 1024, '%.1fM')):
        if size / factor < 1024:
            return format_string % (float(size) / factor)
    return format_string % (size / factor)


def parse_mailcap_nametemplate(tmplate='%s'):
    """this returns a prefix and suffix to be used
    in the tempfile module for a given mailcap nametemplate string"""
    nt_list = tmplate.split('%s')
    template_prefix = ''
    template_suffix = ''
    if len(nt_list) == 2:
        template_suffix = nt_list[1]
        template_prefix = nt_list[0]
    else:
        template_suffix = tmplate
    return (template_prefix, template_suffix)


def parse_mailto(mailto_str):
    """
    Interpret mailto-string
    :param mailto_str: the string to interpret. Must conform to :rfc:2368.
    :return: pair headers,body. headers is a dict mapping str to lists of str,
             body is a str.
    :rtype: (dict(str-->[str,..], str)
    """
    if mailto_str.startswith('mailto:'):
        import urllib
        to_str, parms_str = mailto_str[7:].partition('?')[::2]
        headers = {}
        body = u''

        to = urllib.unquote(to_str)
        if to:
            headers['To'] = [to]

        for s in parms_str.split('&'):
            key, value = s.partition('=')[::2]
            key = key.capitalize()
            if key is 'body':
                body = urllib.unquote(value)
            elif value:
                headers[key] = [urllib.unquote(value)]
        return (headers, body)
    else:
        return (None, None)


def mailto_to_envelope(mailto_str):
    """
    Interpret mailto-string into a :class:`alot.db.envelope.Envelope`
    """
    from alot.db.envelope import Envelope
    headers, body = parse_mailto(mailto_str)
    return Envelope(bodytext=body, headers=headers)

########NEW FILE########
__FILENAME__ = init
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import sys
import logging
import os

import alot
from alot.settings import settings
from alot.settings.errors import ConfigError
from alot.db.manager import DBManager
from alot.ui import UI
from alot.commands import *
from alot.commands import CommandParseError

from twisted.python import usage


class SubcommandOptions(usage.Options):
    optFlags = []

    def parseArgs(self, *args):
        self.args = args

    def as_argparse_opts(self):
        optstr = ''
        for k, v in self.items():
            # flags translate int value 0 or 1..
            if k in [a[0] for a in self.optFlags]:  # if flag
                optstr += ('--%s ' % k) * v
            else:
                if v is not None:
                    optstr += '--%s \'%s\' ' % (k, v)
        return optstr

    def opt_version(self):
        print alot.__version__
        sys.exit(0)


class ComposeOptions(SubcommandOptions):
    optParameters = [
        ['sender', '', None, 'From line'],
        ['subject', '', None, 'subject line'],
        ['to', [], None, 'recipients'],
        ['cc', '', None, 'copy to'],
        ['bcc', '', None, 'blind copy to'],
        ['template', '', None, 'path to template file'],
        ['attach', '', None, 'files to attach'],
    ]
    optFlags = [
        ['omit_signature', '', 'do not add signature'],
    ]

    def parseArgs(self, *args):
        SubcommandOptions.parseArgs(self, *args)
        self.rest = ' '.join(args) or None


class SearchOptions(SubcommandOptions):
    accepted = ['oldest_first', 'newest_first', 'message_id', 'unsorted']

    def colourint(val):
        if val not in accepted:
            raise ValueError("Unknown sort order")
        return val
    colourint.coerceDoc = "Must be one of " + str(accepted)
    optParameters = [
        ['sort', 'newest_first', None, 'Sort order'],
    ]


class Options(usage.Options):
    optFlags = [["read-only", "r", 'open db in read only mode'], ]

    def colourint(val):
        val = int(val)
        if val not in [1, 16, 256]:
            raise ValueError("Not in range")
        return val
    colourint.coerceDoc = "Must be 1, 16 or 256"

    def debuglogstring(val):
        if val not in ['error', 'debug', 'info', 'warning']:
            raise ValueError("Not in range")
        return val
    debuglogstring.coerceDoc = "Must be one of debug,info,warning or error"

    optParameters = [
        ['config', 'c', None, 'config file'],
        ['notmuch-config', 'n', None, 'notmuch config'],
        ['colour-mode', 'C', None, 'terminal colour mode', colourint],
        ['mailindex-path', 'p', None, 'path to notmuch index'],
        ['debug-level', 'd', 'info', 'debug log', debuglogstring],
        ['logfile', 'l', '/dev/null', 'logfile'],
    ]
    search_help = "start in a search buffer using the querystring provided "\
                  "as parameter. See the SEARCH SYNTAX section of notmuch(1)."

    subCommands = [['search', None, SearchOptions, search_help],
                   ['compose', None, ComposeOptions, "compose a new message"]]

    def opt_version(self):
        print alot.__version__
        sys.exit(0)


def main():
    # interpret cml arguments
    args = Options()
    try:
        args.parseOptions()  # When given no argument, parses sys.argv[1:]
    except usage.UsageError, errortext:
        print '%s' % errortext
        print 'Try --help for usage details.'
        sys.exit(1)

    # logging
    root_logger = logging.getLogger()
    for log_handler in root_logger.handlers:
        root_logger.removeHandler(log_handler)
    root_logger = None
    numeric_loglevel = getattr(logging, args['debug-level'].upper(), None)
    logfilename = os.path.expanduser(args['logfile'])
    logformat = '%(levelname)s:%(module)s:%(message)s'
    logging.basicConfig(level=numeric_loglevel, filename=logfilename,
                        filemode='w', format=logformat)

    # locate alot config files
    configfiles = [
        os.path.join(os.environ.get('XDG_CONFIG_HOME',
                                    os.path.expanduser('~/.config')),
                     'alot', 'config'),
    ]
    if args['config']:
        expanded_path = os.path.expanduser(args['config'])
        if not os.path.exists(expanded_path):
            msg = 'Config file "%s" does not exist. Goodbye for now.'
            sys.exit(msg % expanded_path)
        configfiles.insert(0, expanded_path)

    # locate notmuch config
    notmuchpath = os.environ.get('NOTMUCH_CONFIG', '~/.notmuch-config')
    if args['notmuch-config']:
        notmuchpath = args['notmuch-config']
    notmuchconfig = os.path.expanduser(notmuchpath)

    alotconfig = None
    # read the first alot config file we find
    for configfilename in configfiles:
        if os.path.exists(configfilename):
            alotconfig = configfilename
            break  # use only the first

    try:
        settings.read_config(alotconfig)
        settings.read_notmuch_config(notmuchconfig)
    except (ConfigError, OSError, IOError), e:
        sys.exit(e)

    # store options given by config swiches to the settingsManager:
    if args['colour-mode']:
        settings.set('colourmode', args['colour-mode'])

    # get ourselves a database manager
    indexpath = settings.get_notmuch_setting('database', 'path')
    indexpath = args['mailindex-path'] or indexpath
    dbman = DBManager(path=indexpath, ro=args['read-only'])

    # determine what to do
    try:
        if args.subCommand == 'search':
            query = ' '.join(args.subOptions.args)
            cmdstring = 'search %s %s' % (args.subOptions.as_argparse_opts(),
                                          query)
        elif args.subCommand == 'compose':
            cmdstring = 'compose %s' % args.subOptions.as_argparse_opts()
            if args.subOptions.rest is not None:
                cmdstring += ' ' + args.subOptions.rest
        else:
            cmdstring = settings.get('initial_command')
    except CommandParseError, e:
        sys.exit(e)

    # set up and start interface
    UI(dbman, cmdstring)

########NEW FILE########
__FILENAME__ = checks
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import mailbox
import re
from urwid import AttrSpec, AttrSpecError
from urlparse import urlparse
from validate import VdtTypeError
from validate import is_list
from validate import ValidateError, VdtValueTooLongError, VdtValueError

from alot import crypto
from alot.errors import GPGProblem


def attr_triple(value):
    """
    Check that interprets the value as `urwid.AttrSpec` triple for the colour
    modes 1,16 and 256.  It assumes a <6 tuple of attribute strings for
    mono foreground, mono background, 16c fg, 16c bg, 256 fg and 256 bg
    respectively. If any of these are missing, we downgrade to the next
    lower available pair, defaulting to 'default'.

    :raises: VdtValueTooLongError, VdtTypeError
    :rtype: triple of `urwid.AttrSpec`
    """
    keys = ['dfg', 'dbg', '1fg', '1bg', '16fg', '16bg', '256fg', '256bg']
    acc = {}
    if not isinstance(value, (list, tuple)):
        value = value,
    if len(value) > 6:
        raise VdtValueTooLongError(value)
    # ensure we have exactly 6 attribute strings
    attrstrings = (value + (6 - len(value)) * [None])[:6]
    # add fallbacks for the empty list
    attrstrings = (2 * ['default']) + attrstrings
    for i, value in enumerate(attrstrings):
        if value:
            acc[keys[i]] = value
        else:
            acc[keys[i]] = acc[keys[i - 2]]
    try:
        mono = AttrSpec(acc['1fg'], acc['1bg'], 1)
        normal = AttrSpec(acc['16fg'], acc['16bg'], 16)
        high = AttrSpec(acc['256fg'], acc['256bg'], 256)
    except AttrSpecError, e:
        raise ValidateError(e.message)
    return mono, normal, high


def align_mode(value):
    """
    test if value is one of 'left', 'right' or 'center'
    """
    if value not in ['left', 'right', 'center']:
        raise VdtValueError
    return value


def width_tuple(value):
    """
    test if value is a valid width indicator (for a sub-widget in a column).
    This can either be
    ('fit', min, max): use the length actually needed for the content, padded
                       to use at least width min, and cut of at width max.
                       Here, min and max are positive integers or 0 to disable
                       the boundary.
    ('weight',n): have it relative weight of n compared to other columns.
                  Here, n is an int.
    """
    if value is None:
        res = 'fit', 0, 0
    elif not isinstance(value, (list, tuple)):
        raise VdtTypeError(value)
    elif value[0] not in ['fit', 'weight']:
        raise VdtTypeError(value)
    if value[0] == 'fit':
        if not isinstance(value[1], int) or not isinstance(value[2], int):
            VdtTypeError(value)
        res = 'fit', int(value[1]), int(value[2])
    else:
        if not isinstance(value[1], int):
            VdtTypeError(value)
        res = 'weight', int(value[1])
    return res


def mail_container(value):
    """
    Check that the value points to a valid mail container,
    in URI-style, e.g.: `mbox:///home/username/mail/mail.box`.
    The value is cast to a :class:`mailbox.Mailbox` object.
    """
    if not re.match(r'.*://.*', value):
        raise VdtTypeError(value)
    mburl = urlparse(value)
    if mburl.scheme == 'mbox':
        box = mailbox.mbox(mburl.path)
    elif mburl.scheme == 'maildir':
        box = mailbox.Maildir(mburl.path)
    elif mburl.scheme == 'mh':
        box = mailbox.MH(mburl.path)
    elif mburl.scheme == 'babyl':
        box = mailbox.Babyl(mburl.path)
    elif mburl.scheme == 'mmdf':
        box = mailbox.MMDF(mburl.path)
    else:
        raise VdtTypeError(value)
    return box


def force_list(value, min=None, max=None):
    """
    Check that a value is a list, coercing strings into
    a list with one member.

    You can optionally specify the minimum and maximum number of members.
    A minumum of greater than one will fail if the user only supplies a
    string.

    The difference to :func:`validate.force_list` is that this test
    will return an empty list instead of `['']` if the config value
    matches `r'\s*,?\s*'`.

    >>> vtor.check('force_list', 'hello')
    ['hello']
    >>> vtor.check('force_list', '')
    []
    """
    if not isinstance(value, (list, tuple)):
        value = [value]
    rlist = is_list(value, min, max)
    if rlist == ['']:
        rlist = []
    return rlist


def gpg_key(value):
    """
    test if value points to a known gpg key
    and return that key as :class:`pyme.pygpgme._gpgme_key`.
    """
    try:
        return crypto.get_key(value)
    except GPGProblem, e:
        raise ValidateError(e.message)

########NEW FILE########
__FILENAME__ = errors
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file


class ConfigError(Exception):
    """could not parse user config"""
    pass

########NEW FILE########
__FILENAME__ = manager
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import imp
import os
import re
import mailcap
import logging
from configobj import ConfigObj, Section

from alot.account import SendmailAccount
from alot.addressbooks import MatchSdtoutAddressbook, AbookAddressBook
from alot.helper import pretty_datetime, string_decode

from errors import ConfigError
from utils import read_config
from utils import resolve_att
from checks import force_list
from checks import mail_container
from checks import gpg_key
from checks import attr_triple
from checks import align_mode
from theme import Theme


DEFAULTSPATH = os.path.join(os.path.dirname(__file__), '..', 'defaults')


class SettingsManager(object):
    """Organizes user settings"""
    def __init__(self, alot_rc=None, notmuch_rc=None):
        """
        :param alot_rc: path to alot's config file
        :type alot_rc: str
        :param notmuch_rc: path to notmuch's config file
        :type notmuch_rc: str
        """
        self.hooks = None
        self._mailcaps = mailcap.getcaps()
        self._config = ConfigObj()
        self._notmuchconfig = None
        self._theme = None
        self._accounts = None
        self._accountmap = None
        bindings_path = os.path.join(DEFAULTSPATH, 'default.bindings')
        self._bindings = ConfigObj(bindings_path)
        if alot_rc is not None:
            self.read_config(alot_rc)
        if notmuch_rc is not None:
            self.read_notmuch_config(notmuch_rc)

    def read_notmuch_config(self, path):
        """parse notmuch's config file from path"""
        spec = os.path.join(DEFAULTSPATH, 'notmuch.rc.spec')
        self._notmuchconfig = read_config(path, spec)

    def read_config(self, path):
        """parse alot's config file from path"""
        spec = os.path.join(DEFAULTSPATH, 'alot.rc.spec')
        newconfig = read_config(path, spec,
                                checks={'mail_container': mail_container,
                                        'force_list': force_list,
                                        'align': align_mode,
                                        'attrtriple': attr_triple,
                                        'gpg_key_hint': gpg_key})
        self._config.merge(newconfig)

        hooks_path = os.path.expanduser(self._config.get('hooksfile'))
        try:
            self.hooks = imp.load_source('hooks', hooks_path)
        except:
            logging.debug('unable to load hooks file:%s' % hooks_path)
        if 'bindings' in newconfig:
            newbindings = newconfig['bindings']
            if isinstance(newbindings, Section):
                self._bindings.merge(newbindings)
        # themes
        themestring = newconfig['theme']
        themes_dir = self._config.get('themes_dir')
        if themes_dir:
            themes_dir = os.path.expanduser(themes_dir)
        else:
            configdir = os.environ.get('XDG_CONFIG_HOME',
                                       os.path.expanduser('~/.config'))
            themes_dir = os.path.join(configdir, 'alot', 'themes')
        logging.debug(themes_dir)

        # if config contains theme string use that
        if themestring:
            if not os.path.isdir(themes_dir):
                err_msg = 'cannot find theme %s: themes_dir %s is missing'
                raise ConfigError(err_msg % (themestring, themes_dir))
            else:
                theme_path = os.path.join(themes_dir, themestring)
                try:
                    self._theme = Theme(theme_path)
                except ConfigError as e:
                    err_msg = 'Theme file %s failed validation:\n'
                    raise ConfigError((err_msg % themestring) + str(e.message))

        # if still no theme is set, resort to default
        if self._theme is None:
            theme_path = os.path.join(DEFAULTSPATH, 'default.theme')
            self._theme = Theme(theme_path)

        self._accounts = self._parse_accounts(self._config)
        self._accountmap = self._account_table(self._accounts)

    def _parse_accounts(self, config):
        """
        read accounts information from config

        :param config: valit alot config
        :type config: `configobj.ConfigObj`
        :returns: list of accounts
        """
        accounts = []
        if 'accounts' in config:
            for acc in config['accounts'].sections:
                accsec = config['accounts'][acc]
                args = dict(config['accounts'][acc])

                # create abook for this account
                abook = accsec['abook']
                logging.debug('abook defined: %s' % abook)
                if abook['type'] == 'shellcommand':
                    cmd = abook['command']
                    regexp = abook['regexp']
                    if cmd is not None and regexp is not None:
                        args['abook'] = MatchSdtoutAddressbook(cmd,
                                                               match=regexp)
                    else:
                        msg = 'underspecified abook of type \'shellcommand\':'
                        msg += '\ncommand: %s\nregexp:%s' % (cmd, regexp)
                        raise ConfigError(msg)
                elif abook['type'] == 'abook':
                    contacts_path = abook['abook_contacts_file']
                    args['abook'] = AbookAddressBook(
                        contacts_path, ignorecase=abook['ignorecase'])
                else:
                    del(args['abook'])

                cmd = args['sendmail_command']
                del(args['sendmail_command'])
                newacc = SendmailAccount(cmd, **args)
                accounts.append(newacc)
        return accounts

    def _account_table(self, accounts):
        """
        creates a lookup table (emailaddress -> account) for a given list of
        accounts

        :param accounts: list of accounts
        :type accounts: list of `alot.account.Account`
        :returns: hashtable
        :rvalue: dict (str -> `alot.account.Account`)
        """
        accountmap = {}
        for acc in accounts:
            accountmap[acc.address] = acc
            for alias in acc.aliases:
                accountmap[alias] = acc
        return accountmap

    def get(self, key, fallback=None):
        """
        look up global config values from alot's config

        :param key: key to look up
        :type key: str
        :param fallback: fallback returned if key is not present
        :type fallback: str
        :returns: config value with type as specified in the spec-file
        """
        value = None
        if key in self._config:
            value = self._config[key]
            if isinstance(value, Section):
                value = None
        if value is None:
            value = fallback
        return value

    def set(self, key, value):
        """
        setter for global config values

        :param key: config option identifise
        :type key: str
        :param value: option to set
        :type value: depends on the specfile :file:`alot.rc.spec`
        """
        self._config[key] = value

    def get_notmuch_setting(self, section, key, fallback=None):
        """
        look up config values from notmuch's config

        :param section: key is in
        :type section: str
        :param key: key to look up
        :type key: str
        :param fallback: fallback returned if key is not present
        :type fallback: str
        :returns: config value with type as specified in the spec-file
        """
        value = None
        if section in self._notmuchconfig:
            if key in self._notmuchconfig[section]:
                value = self._notmuchconfig[section][key]
        if value is None:
            value = fallback
        return value

    def get_theming_attribute(self, mode, name, part=None):
        """
        looks up theming attribute

        :param mode: ui-mode (e.g. `search`,`thread`...)
        :type mode: str
        :param name: identifier of the atttribute
        :type name: str
        :rtype: urwid.AttrSpec
        """
        colours = int(self._config.get('colourmode'))
        return self._theme.get_attribute(colours, mode, name, part)

    def get_threadline_theming(self, thread):
        """
        looks up theming info a threadline displaying a given thread. This
        wraps around :meth:`~alot.settings.theme.Theme.get_threadline_theming`,
        filling in the current colour mode.

        :param thread: thread to theme
        :type thread: alot.db.thread.Thread
        """
        colours = int(self._config.get('colourmode'))
        return self._theme.get_threadline_theming(thread, colours)

    def get_tagstring_representation(self, tag, onebelow_normal=None,
                                     onebelow_focus=None):
        """
        looks up user's preferred way to represent a given tagstring.

        :param tag: tagstring
        :type tag: str
        :param onebelow_normal: attribute that shines through if unfocussed
        :type onebelow_normal: urwid.AttrSpec
        :param onebelow_focus: attribute that shines through if focussed
        :type onebelow_focus: urwid.AttrSpec

        If `onebelow_normal` or `onebelow_focus` is given these attributes will
        be used as fallbacks for fg/bg values '' and 'default'.

        This returns a dictionary mapping
            :normal: to :class:`urwid.AttrSpec` used if unfocussed
            :focussed: to :class:`urwid.AttrSpec` used if focussed
            :translated: to an alternative string representation
        """
        colourmode = int(self._config.get('colourmode'))
        theme = self._theme
        cfg = self._config
        colours = [1, 16, 256]

        def colourpick(triple):
            """ pick attribute from triple (mono,16c,256c) according to current
            colourmode"""
            if triple is None:
                return None
            return triple[colours.index(colourmode)]

        # global default attributes for tagstrings.
        # These could contain values '' and 'default' which we interpret as
        # "use the values from the widget below"
        default_normal = theme.get_attribute(colourmode, 'global', 'tag')
        default_focus = theme.get_attribute(colourmode, 'global', 'tag_focus')

        # local defaults for tagstring attributes. depend on next lower widget
        fallback_normal = resolve_att(onebelow_normal, default_normal)
        fallback_focus = resolve_att(onebelow_focus, default_focus)

        for sec in cfg['tags'].sections:
            if re.match('^' + sec + '$', tag):
                normal = resolve_att(colourpick(cfg['tags'][sec]['normal']),
                                     fallback_normal)
                focus = resolve_att(colourpick(cfg['tags'][sec]['focus']),
                                    fallback_focus)

                translated = cfg['tags'][sec]['translated']
                if translated is None:
                    translated = tag
                translation = cfg['tags'][sec]['translation']
                if translation:
                    translated = re.sub(translation[0], translation[1], tag)
                break
        else:
            normal = fallback_normal
            focus = fallback_focus
            translated = tag

        return {'normal': normal, 'focussed': focus, 'translated': translated}

    def get_hook(self, key):
        """return hook (`callable`) identified by `key`"""
        if self.hooks:
            if key in self.hooks.__dict__:
                return self.hooks.__dict__[key]
        return None

    def get_mapped_input_keysequences(self, mode='global', prefix=u''):
        candidates = self._bindings.scalars
        if mode != 'global':
            candidates = candidates + self._bindings[mode].scalars
        if prefix is not None:
            prefixs = prefix + ' '
            cand = filter(lambda x: x.startswith(prefixs), candidates)
            if prefix in candidates:
                candidates = cand + [prefix]
            else:
                candidates = cand
        return candidates

    def get_keybinding(self, mode, key):
        """look up keybinding from `MODE-maps` sections

        :param mode: mode identifier
        :type mode: str
        :param key: urwid-style key identifier
        :type key: str
        :returns: a command line to be applied upon keypress
        :rtype: str
        """
        cmdline = None
        bindings = self._bindings
        if key in bindings.scalars:
            cmdline = bindings[key]
        if mode in bindings.sections:
            if key in bindings[mode].scalars:
                value = bindings[mode][key]
                if value:
                    cmdline = value
        # Workaround for ConfigObj misbehaviour. cf issue #500
        # this ensures that we get at least strings only as commandlines
        if isinstance(cmdline, list):
            cmdline = ','.join(cmdline)
        return cmdline

    def get_accounts(self):
        """
        returns known accounts

        :rtype: list of :class:`Account`
        """
        return self._accounts

    def get_account_by_address(self, address):
        """
        returns :class:`Account` for a given email address (str)

        :param address: address to look up
        :type address: string
        :rtype:  :class:`Account` or None
        """

        for myad in self.get_addresses():
            if myad in address:
                return self._accountmap[myad]
        return None

    def get_main_addresses(self):
        """returns addresses of known accounts without its aliases"""
        return [a.address for a in self._accounts]

    def get_addresses(self):
        """returns addresses of known accounts including all their aliases"""
        return self._accountmap.keys()

    def get_addressbooks(self, order=[], append_remaining=True):
        """returns list of all defined :class:`AddressBook` objects"""
        abooks = []
        for a in order:
            if a:
                if a.abook:
                    abooks.append(a.abook)
        if append_remaining:
            for a in self._accounts:
                if a.abook and a.abook not in abooks:
                    abooks.append(a.abook)
        return abooks

    def mailcap_find_match(self, *args, **kwargs):
        """
        Propagates :func:`mailcap.find_match` but caches the mailcap (first
        argument)
        """
        return mailcap.findmatch(self._mailcaps, *args, **kwargs)

    def represent_datetime(self, d):
        """
        turns a given datetime obj into a unicode string representation.
        This will:

        1) look if a fixed 'timestamp_format' is given in the config
        2) check if a 'timestamp_format' hook is defined
        3) use :func:`~alot.helper.pretty_datetime` as fallback
        """

        fixed_format = self.get('timestamp_format')
        if fixed_format:
            rep = string_decode(d.strftime(fixed_format), 'UTF-8')
        else:
            format_hook = self.get_hook('timestamp_format')
            if format_hook:
                rep = string_decode(format_hook(d), 'UTF-8')
            else:
                rep = pretty_datetime(d)
        return rep

########NEW FILE########
__FILENAME__ = theme
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import os

from utils import read_config
from checks import align_mode
from checks import attr_triple
from checks import width_tuple
from checks import force_list
from errors import ConfigError

DEFAULTSPATH = os.path.join(os.path.dirname(__file__), '..', 'defaults')
DUMMYDEFAULT = ('default',) * 6


class Theme(object):
    """Colour theme"""
    def __init__(self, path):
        """
        :param path: path to theme file
        :type path: str
        :raises: :class:`~alot.settings.errors.ConfigError`
        """
        self._spec = os.path.join(DEFAULTSPATH, 'theme.spec')
        self._config = read_config(path, self._spec,
                                   checks={'align': align_mode,
                                           'widthtuple': width_tuple,
                                           'force_list': force_list,
                                           'attrtriple': attr_triple})
        self._colours = [1, 16, 256]
        # make sure every entry in 'order' lists have their own subsections
        threadline = self._config['search']['threadline']
        for sec in self._config['search']:
            if sec.startswith('threadline'):
                tline = self._config['search'][sec]
                if tline['parts'] is not None:
                    listed = set(tline['parts'])
                    here = set(tline.sections)
                    indefault = set(threadline.sections)
                    diff = listed.difference(here.union(indefault))
                    if diff:
                        msg = 'missing threadline parts: %s' % ', '.join(diff)
                        raise ConfigError(msg)

    def get_attribute(self, colourmode, mode, name, part=None):
        """
        returns requested attribute

        :param mode: ui-mode (e.g. `search`,`thread`...)
        :type mode: str
        :param name: of the atttribute
        :type name: str
        :param colourmode: colour mode; in [1, 16, 256]
        :type colourmode: int
        :rtype: urwid.AttrSpec
        """
        thmble = self._config[mode][name]
        if part is not None:
            thmble = thmble[part]
        thmble = thmble or DUMMYDEFAULT
        return thmble[self._colours.index(colourmode)]

    def get_threadline_theming(self, thread, colourmode):
        """
        look up how to display a Threadline wiidget in search mode
        for a given thread.

        :param thread: Thread to theme Threadline for
        :type thread: alot.db.thread.Thread
        :param colourmode: colourmode to use, one of 1,16,256.
        :type colourmode: int

        This will return a dict mapping
            :normal: to `urwid.AttrSpec`,
            :focus: to `urwid.AttrSpec`,
            :parts: to a list of strings indentifying subwidgets
                    to be displayed in this order.

        Moreover, for every part listed this will map 'part' to a dict mapping
            :normal: to `urwid.AttrSpec`,
            :focus: to `urwid.AttrSpec`,
            :width: to a tuple indicating the width of the subpart.
                    This is either `('fit', min, max)` to force the widget
                    to be at least `min` and at most `max` characters wide,
                    or `('weight', n)` which makes it share remaining space
                    with other 'weight' parts.
            :alignment: where to place the content if shorter than the widget.
                        This is either 'right', 'left' or 'center'.
        """
        def pickcolour(triple):
            return triple[self._colours.index(colourmode)]

        def matches(sec, thread):
            if sec.get('tagged_with') is not None:
                if not set(sec['tagged_with']).issubset(thread.get_tags()):
                    return False
            if sec.get('query') is not None:
                if not thread.matches(sec['query']):
                    return False
            return True

        default = self._config['search']['threadline']
        match = default

        candidates = self._config['search'].sections
        for candidatename in candidates:
            candidate = self._config['search'][candidatename]
            if candidatename.startswith('threadline') and\
               (not candidatename == 'threadline') and\
               matches(candidate, thread):
                    match = candidate
                    break

        # fill in values
        res = {}
        res['normal'] = pickcolour(match.get('normal') or default['normal'])
        res['focus'] = pickcolour(match.get('focus') or default['focus'])
        res['parts'] = match.get('parts') or default['parts']
        for part in res['parts']:
            defaultsec = default.get(part)
            partsec = match.get(part) or {}

            def fill(key, fallback=None):
                pvalue = partsec.get(key) or defaultsec.get(key)
                return pvalue or fallback

            res[part] = {}
            res[part]['width'] = fill('width', ('fit', 0, 0))
            res[part]['alignment'] = fill('alignment', 'right')
            res[part]['normal'] = pickcolour(fill('normal'))
            res[part]['focus'] = pickcolour(fill('focus'))
        return res

########NEW FILE########
__FILENAME__ = utils
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
from configobj import ConfigObj, ConfigObjError, flatten_errors
from validate import Validator
from errors import ConfigError
from urwid import AttrSpec


def read_config(configpath=None, specpath=None, checks={}):
    """
    get a (validated) config object for given config file path.

    :param configpath: path to config-file
    :type configpath: str
    :param specpath: path to spec-file
    :type specpath: str
    :param checks: custom checks to use for validator.
        see `validate docs <http://www.voidspace.org.uk/python/validate.html>`_
    :type checks: dict str->callable,
    :raises: :class:`~alot.settings.errors.ConfigError`
    :rtype: `configobj.ConfigObj`
    """
    try:
        config = ConfigObj(infile=configpath, configspec=specpath,
                           file_error=True, encoding='UTF8')
    except ConfigObjError as e:
        raise ConfigError(e)
    except IOError:
        raise ConfigError('Could not read %s' % configpath)
    except UnboundLocalError:
        # this works around a bug in configobj
        msg = '%s is malformed. Check for sections without parents..'
        raise ConfigError(msg % configpath)

    if specpath:
        validator = Validator()
        validator.functions.update(checks)
        try:
            results = config.validate(validator, preserve_errors=True)
        except ConfigObjError as e:
            raise ConfigError(e.message)

        if results is not True:
            error_msg = ''
            for (section_list, key, res) in flatten_errors(config, results):
                if key is not None:
                    if res is False:
                        msg = 'key "%s" in section "%s" is missing.'
                        msg = msg % (key, ', '.join(section_list))
                    else:
                        msg = 'key "%s" in section "%s" failed validation: %s'
                        msg = msg % (key, ', '.join(section_list), res)
                else:
                    msg = 'section "%s" is missing' % '.'.join(section_list)
                error_msg += msg + '\n'
            raise ConfigError(error_msg)
    return config


def resolve_att(a, fallback):
    """ replace '' and 'default' by fallback values """
    if a is None:
        return fallback
    if a.background in ['default', '']:
        bg = fallback.background
    else:
        bg = a.background
    if a.foreground in ['default', '']:
        fg = fallback.foreground
    else:
        fg = a.foreground
    return AttrSpec(fg, bg)

########NEW FILE########
__FILENAME__ = ui
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import urwid
import logging
from twisted.internet import reactor, defer

from settings import settings
from buffers import BufferlistBuffer
from commands import commandfactory
from commands import CommandCanceled
from alot.commands import CommandParseError
from alot.helper import split_commandline
from alot.helper import string_decode
from alot.widgets.globals import CompleteEdit
from alot.widgets.globals import ChoiceWidget


class UI(object):
    """
    This class integrates all components of alot and offers
    methods for user interaction like :meth:`prompt`, :meth:`notify` etc.
    It handles the urwid widget tree and mainloop (we use twisted) and is
    responsible for opening, closing and focussing buffers.
    """

    def __init__(self, dbman, initialcmdline):
        """
        :param dbman: :class:`~alot.db.DBManager`
        :param initialcmdline: commandline applied after setting up interface
        :type initialcmdline: str
        :param colourmode: determines which theme to chose
        :type colourmode: int in [1,16,256]
        """
        self.dbman = dbman
        """Database Manager (:class:`~alot.db.manager.DBManager`)"""
        self.buffers = []
        """list of active buffers"""
        self.current_buffer = None
        """points to currently active :class:`~alot.buffers.Buffer`"""
        self.db_was_locked = False
        """flag used to prevent multiple 'index locked' notifications"""
        self.mode = 'global'
        """interface mode identifier - type of current buffer"""
        self.commandprompthistory = []
        """history of the command line prompt"""
        self.input_queue = []
        """stores partial keyboard input"""
        self.last_commandline = None
        """saves the last executed commandline"""

        # define empty notification pile
        self._notificationbar = None
        # should we show a status bar?
        self._show_statusbar = settings.get('show_statusbar')
        # pass keypresses to the root widget and never interpret bindings
        self._passall = False
        # indicates "input lock": only focus move commands are interpreted
        self._locked = False
        self._unlock_callback = None  # will be called after input lock ended
        self._unlock_key = None  # key that ends input lock

        # alarm handle for callback that clears input queue (to cancel alarm)
        self._alarm = None

        # create root widget
        global_att = settings.get_theming_attribute('global', 'body')
        mainframe = urwid.Frame(urwid.SolidFill())
        self.root_widget = urwid.AttrMap(mainframe, global_att)

        # set up main loop
        self.mainloop = urwid.MainLoop(self.root_widget,
                                       handle_mouse=False,
                                       event_loop=urwid.TwistedEventLoop(),
                                       unhandled_input=self._unhandeled_input,
                                       input_filter=self._input_filter)

        # set up colours
        colourmode = int(settings.get('colourmode'))
        logging.info('setup gui in %d colours' % colourmode)
        self.mainloop.screen.set_terminal_properties(colors=colourmode)

        logging.debug('fire first command')
        self.apply_commandline(initialcmdline)

        # start urwids mainloop
        self.mainloop.run()

    def _input_filter(self, keys, raw):
        """
        handles keypresses.
        This function gets triggered directly by class:`urwid.MainLoop`
        upon user input and is supposed to pass on its `keys` parameter
        to let the root widget handle keys. We intercept the input here
        to trigger custom commands as defined in our keybindings.
        """
        logging.debug("Got key (%s, %s)" % (keys, raw))
        # work around: escape triggers this twice, with keys = raw = []
        # the first time..
        if not keys:
            return
        # let widgets handle input if key is virtual window resize keypress
        # or we are in "passall" mode
        elif 'window resize' in keys or self._passall:
            return keys
        # end "lockdown" mode if the right key was pressed
        elif self._locked and keys[0] == self._unlock_key:
            self._locked = False
            self.mainloop.widget = self.root_widget
            if callable(self._unlock_callback):
                self._unlock_callback()
        # otherwise interpret keybinding
        else:
            # define callback that resets input queue
            def clear(*args):
                if self._alarm is not None:
                    self.mainloop.remove_alarm(self._alarm)
                self.input_queue = []

            def fire(ignored, cmdline):
                clear()
                logging.debug("cmdline: '%s'" % cmdline)
                if not self._locked:
                    try:
                        self.apply_commandline(cmdline)
                    except CommandParseError, e:
                        self.notify(e.message, priority='error')
                # move keys are always passed
                elif cmdline in ['move up', 'move down', 'move page up',
                                 'move page down']:
                    return [cmdline[5:]]

            key = keys[0]
            self.input_queue.append(key)
            keyseq = ' '.join(self.input_queue)
            candidates = settings.get_mapped_input_keysequences(self.mode,
                                                                prefix=keyseq)
            if keyseq in candidates:
                # case: current input queue is a mapped keysequence
                # get binding and interpret it if non-null
                cmdline = settings.get_keybinding(self.mode, keyseq)
                if cmdline:
                    if len(candidates) > 1:
                        timeout = float(settings.get('input_timeout'))
                        if self._alarm is not None:
                            self.mainloop.remove_alarm(self._alarm)
                        self._alarm = self.mainloop.set_alarm_in(
                            timeout, fire, cmdline)
                    else:
                        return fire(self.mainloop, cmdline)

            elif not candidates:
                # case: no sequence with prefix keyseq is mapped
                # just clear the input queue
                clear()
            else:
                # case: some sequences with proper prefix keyseq is mapped
                timeout = float(settings.get('input_timeout'))
                if self._alarm is not None:
                    self.mainloop.remove_alarm(self._alarm)
                self._alarm = self.mainloop.set_alarm_in(timeout, clear)
            # update statusbar
            self.update()

    def apply_commandline(self, cmdline):
        """
        interprets a command line string

        i.e., splits it into separate command strings,
        instanciates :class:`Commands <alot.commands.Command>`
        accordingly and applies then in sequence.

        :param cmdline: command line to interpret
        :type cmdline: str
        """
        # remove initial spaces
        cmdline = cmdline.lstrip()

        # we pass Commands one by one to `self.apply_command`.
        # To properly call them in sequence, even if they trigger asyncronous
        # code (return Deferreds), these applications happen in individual
        # callback functions which are then used as callback chain to some
        # trivial Deferred that immediately calls its first callback. This way,
        # one callback may return a Deferred and thus postpone the application
        # of the next callback (and thus Command-application)

        def apply_this_command(ignored, cmdstring):
            logging.debug('%s command string: "%s"' % (self.mode,
                                                       str(cmdstring)))
            #logging.debug('CMDSEQ: apply %s' % str(cmdstring))
            # translate cmdstring into :class:`Command`
            #try:
            cmd = commandfactory(cmdstring, self.mode)
            #except CommandParseError, e:
             #   self.notify(e.message, priority='error')
              #  return
            # store cmdline for use with 'repeat' command
            if cmd.repeatable:
                self.last_commandline = cmdline
            return self.apply_command(cmd)

        # we initialize a deferred which is already triggered
        # so that the first callbacks will be called immediately
        d = defer.succeed(None)

        # split commandline if necessary
        for cmdstring in split_commandline(cmdline):
            d.addCallback(apply_this_command, cmdstring)

        # add sequence-wide error handler
        def errorHandler(failure):
            if failure.check(CommandParseError):
                self.notify(failure.getErrorMessage(), priority='error')
            elif failure.check(CommandCanceled):
                self.notify("operation cancelled", priority='error')
            else:
                logging.error(failure.getTraceback())
                errmsg = failure.getErrorMessage()
                if errmsg:
                    msg = "%s\n(check the log for details)"
                    self.notify(msg % errmsg, priority='error')
        d.addErrback(errorHandler)
        return d

    def _unhandeled_input(self, key):
        """
        Called by :class:`urwid.MainLoop` if a keypress was passed to the root
        widget by `self._input_filter` but is not handled in any widget. We
        keep it for debuging purposes.
        """
        logging.debug('unhandled input: %s' % key)

    def show_as_root_until_keypress(self, w, key, afterwards=None):
        """
        Replaces root widget by given :class:`urwid.Widget` and makes the UI
        ignore all further commands apart from cursor movement.
        If later on `key` is pressed, the old root widget is reset, callable
        `afterwards` is called and normal behaviour is resumed.
        """
        self.mainloop.widget = w
        self._unlock_key = key
        self._unlock_callback = afterwards
        self._locked = True

    def prompt(self, prefix, text=u'', completer=None, tab=0, history=[]):
        """
        prompt for text input.
        This returns a :class:`~twisted.defer.Deferred` that calls back with
        the input string.

        :param prefix: text to print before the input field
        :type prefix: str
        :param text: initial content of the input field
        :type text: str
        :param completer: completion object to use
        :type completer: :meth:`alot.completion.Completer`
        :param tab: number of tabs to press initially
                    (to select completion results)
        :type tab: int
        :param history: history to be used for up/down keys
        :type history: list of str
        :rtype: :class:`twisted.defer.Deferred`
        """
        d = defer.Deferred()  # create return deferred
        oldroot = self.mainloop.widget

        def select_or_cancel(text):
            # restore main screen and invoke callback
            # (delayed return) with given text
            self.mainloop.widget = oldroot
            self._passall = False
            d.callback(text)

        def cerror(e):
            logging.error(e)
            self.notify('completion error: %s' % e.message,
                        priority='error')
            self.update()

        prefix = prefix + settings.get('prompt_suffix')

        # set up widgets
        leftpart = urwid.Text(prefix, align='left')
        editpart = CompleteEdit(completer, on_exit=select_or_cancel,
                                edit_text=text, history=history,
                                on_error=cerror)

        for i in range(tab):  # hit some tabs
            editpart.keypress((0,), 'tab')

        # build promptwidget
        both = urwid.Columns(
            [
                ('fixed', len(prefix), leftpart),
                ('weight', 1, editpart),
            ])
        att = settings.get_theming_attribute('global', 'prompt')
        both = urwid.AttrMap(both, att)

        # put promptwidget as overlay on main widget
        overlay = urwid.Overlay(both, oldroot,
                                ('fixed left', 0),
                                ('fixed right', 0),
                                ('fixed bottom', 1),
                                None)
        self.mainloop.widget = overlay
        self._passall = True
        return d  # return deferred

    def exit(self):
        """
        shuts down user interface without cleaning up.
        Use a :class:`alot.commands.globals.ExitCommand` for a clean shutdown.
        """
        exit_msg = None
        try:
            reactor.stop()
        except Exception as e:
            exit_msg = 'Could not stop reactor: {}.'.format(e)
            logging.error(exit_msg + '\nShutting down anyway..')

    def buffer_open(self, buf):
        """register and focus new :class:`~alot.buffers.Buffer`."""

        # call pre_buffer_open hook
        prehook = settings.get_hook('pre_buffer_open')
        if prehook is not None:
            prehook(ui=self, dbm=self.dbman, buf=buf)

        if self.current_buffer is not None:
            offset = settings.get('bufferclose_focus_offset') * -1
            currentindex = self.buffers.index(self.current_buffer)
            self.buffers.insert(currentindex + offset, buf)
        else:
            self.buffers.append(buf)
        self.buffer_focus(buf)

        # call post_buffer_open hook
        posthook = settings.get_hook('post_buffer_open')
        if posthook is not None:
            posthook(ui=self, dbm=self.dbman, buf=buf)

    def buffer_close(self, buf, redraw=True):
        """
        closes given :class:`~alot.buffers.Buffer`.

        This it removes it from the bufferlist and calls its cleanup() method.
        """

        # call pre_buffer_close hook
        prehook = settings.get_hook('pre_buffer_close')
        if prehook is not None:
            prehook(ui=self, dbm=self.dbman, buf=buf)

        buffers = self.buffers
        success = False
        if buf not in buffers:
            string = 'tried to close unknown buffer: %s. \n\ni have:%s'
            logging.error(string % (buf, self.buffers))
        elif self.current_buffer == buf:
            logging.info('closing current buffer %s' % buf)
            index = buffers.index(buf)
            buffers.remove(buf)
            offset = settings.get('bufferclose_focus_offset')
            nextbuffer = buffers[(index + offset) % len(buffers)]
            self.buffer_focus(nextbuffer, redraw)
            buf.cleanup()
            success = True
        else:
            string = 'closing buffer %d:%s'
            buffers.remove(buf)
            buf.cleanup()
            success = True

        # call post_buffer_closed hook
        posthook = settings.get_hook('post_buffer_closed')
        if posthook is not None:
            posthook(ui=self, dbm=self.dbman, buf=buf, success=success)

    def buffer_focus(self, buf, redraw=True):
        """focus given :class:`~alot.buffers.Buffer`."""

        # call pre_buffer_focus hook
        prehook = settings.get_hook('pre_buffer_focus')
        if prehook is not None:
            prehook(ui=self, dbm=self.dbman, buf=buf)

        success = False
        if buf not in self.buffers:
            logging.error('tried to focus unknown buffer')
        else:
            if self.current_buffer != buf:
                self.current_buffer = buf
            self.mode = buf.modename
            if isinstance(self.current_buffer, BufferlistBuffer):
                self.current_buffer.rebuild()
            self.update()
            success = True

        # call post_buffer_focus hook
        posthook = settings.get_hook('post_buffer_focus')
        if posthook is not None:
            posthook(ui=self, dbm=self.dbman, buf=buf, success=success)

    def get_deep_focus(self, startfrom=None):
        """return the bottom most focussed widget of the widget tree"""
        if not startfrom:
            startfrom = self.current_buffer
        if 'get_focus' in dir(startfrom):
            focus = startfrom.get_focus()
            if isinstance(focus, tuple):
                focus = focus[0]
            if isinstance(focus, urwid.Widget):
                return self.get_deep_focus(startfrom=focus)
        return startfrom

    def get_buffers_of_type(self, t):
        """
        returns currently open buffers for a given subclass of
        :class:`~alot.buffers.Buffer`.

        :param t: Buffer class
        :type t: alot.buffers.Buffer
        :rtype: list
        """
        return filter(lambda x: isinstance(x, t), self.buffers)

    def clear_notify(self, messages):
        """
        Clears notification popups. Call this to ged rid of messages that don't
        time out.

        :param messages: The popups to remove. This should be exactly
                         what :meth:`notify` returned when creating the popup
        """
        newpile = self._notificationbar.widget_list
        for l in messages:
            if l in newpile:
                newpile.remove(l)
        if newpile:
            self._notificationbar = urwid.Pile(newpile)
        else:
            self._notificationbar = None
        self.update()

    def choice(self, message, choices={'y': 'yes', 'n': 'no'},
               select=None, cancel=None, msg_position='above'):
        """
        prompt user to make a choice.

        :param message: string to display before list of choices
        :type message: unicode
        :param choices: dict of possible choices
        :type choices: dict: keymap->choice (both str)
        :param select: choice to return if enter/return is hit. Ignored if set
                       to `None`.
        :type select: str
        :param cancel: choice to return if escape is hit. Ignored if set to
                       `None`.
        :type cancel: str
        :param msg_position: determines if `message` is above or left of the
                             prompt. Must be `above` or `left`.
        :type msg_position: str
        :rtype:  :class:`twisted.defer.Deferred`
        """
        assert select in choices.values() + [None]
        assert cancel in choices.values() + [None]
        assert msg_position in ['left', 'above']

        d = defer.Deferred()  # create return deferred
        oldroot = self.mainloop.widget

        def select_or_cancel(text):
            self.mainloop.widget = oldroot
            self._passall = False
            d.callback(text)

        # set up widgets
        msgpart = urwid.Text(message)
        choicespart = ChoiceWidget(choices, callback=select_or_cancel,
                                   select=select, cancel=cancel)

        # build widget
        if msg_position == 'left':
            both = urwid.Columns(
                [
                    ('fixed', len(message), msgpart),
                    ('weight', 1, choicespart),
                ], dividechars=1)
        else:  # above
            both = urwid.Pile([msgpart, choicespart])
        att = settings.get_theming_attribute('global', 'prompt')
        both = urwid.AttrMap(both, att, att)

        # put promptwidget as overlay on main widget
        overlay = urwid.Overlay(both, oldroot,
                                ('fixed left', 0),
                                ('fixed right', 0),
                                ('fixed bottom', 1),
                                None)
        self.mainloop.widget = overlay
        self._passall = True
        return d  # return deferred

    def notify(self, message, priority='normal', timeout=0, block=False):
        """
        opens notification popup.

        :param message: message to print
        :type message: str
        :param priority: priority string, used to format the popup: currently,
                         'normal' and 'error' are defined. If you use 'X' here,
                         the attribute 'global_notify_X' is used to format the
                         popup.
        :type priority: str
        :param timeout: seconds until message disappears. Defaults to the value
                        of 'notify_timeout' in the general config section.
                        A negative value means never time out.
        :type timeout: int
        :param block: this notification blocks until a keypress is made
        :type block: bool
        :returns: an urwid widget (this notification) that can be handed to
                  :meth:`clear_notify` for removal
        """
        def build_line(msg, prio):
            cols = urwid.Columns([urwid.Text(msg)])
            att = settings.get_theming_attribute('global', 'notify_' + prio)
            return urwid.AttrMap(cols, att)
        msgs = [build_line(message, priority)]

        if not self._notificationbar:
            self._notificationbar = urwid.Pile(msgs)
        else:
            newpile = self._notificationbar.widget_list + msgs
            self._notificationbar = urwid.Pile(newpile)
        self.update()

        def clear(*args):
            self.clear_notify(msgs)

        if block:
            # put "cancel to continue" widget as overlay on main widget
            txt = build_line('(escape continues)', priority)
            overlay = urwid.Overlay(txt, self.root_widget,
                                    ('fixed left', 0),
                                    ('fixed right', 0),
                                    ('fixed bottom', 0),
                                    None)
            self.show_as_root_until_keypress(overlay, 'esc',
                                             afterwards=clear)
        else:
            if timeout >= 0:
                if timeout == 0:
                    timeout = settings.get('notify_timeout')
                self.mainloop.set_alarm_in(timeout, clear)
        return msgs[0]

    def update(self, redraw=True):
        """redraw interface"""
        # get the main urwid.Frame widget
        mainframe = self.root_widget.original_widget

        # body
        if self.current_buffer:
            mainframe.set_body(self.current_buffer)

        # footer
        lines = []
        if self._notificationbar:  # .get_text()[0] != ' ':
            lines.append(self._notificationbar)
        if self._show_statusbar:
            lines.append(self.build_statusbar())

        if lines:
            mainframe.set_footer(urwid.Pile(lines))
        else:
            mainframe.set_footer(None)
        # force a screen redraw
        if self.mainloop.screen.started and redraw:
            self.mainloop.draw_screen()

    def build_statusbar(self):
        """construct and return statusbar widget"""
        info = {}
        cb = self.current_buffer
        btype = None

        if cb is not None:
            info = cb.get_info()
            btype = cb.modename
            info['buffer_no'] = self.buffers.index(cb)
            info['buffer_type'] = btype
        info['total_messages'] = self.dbman.count_messages('*')
        info['pending_writes'] = len(self.dbman.writequeue)
        info['input_queue'] = ' '.join(self.input_queue)

        lefttxt = righttxt = u''
        if cb is not None:
            lefttxt, righttxt = settings.get(btype + '_statusbar', (u'', u''))
            lefttxt = string_decode(lefttxt, 'UTF-8')
            lefttxt = lefttxt.format(**info)
            righttxt = string_decode(righttxt, 'UTF-8')
            righttxt = righttxt.format(**info)

        footerleft = urwid.Text(lefttxt, align='left')
        pending_writes = len(self.dbman.writequeue)
        if pending_writes > 0:
            righttxt = ('|' * pending_writes) + ' ' + righttxt
        footerright = urwid.Text(righttxt, align='right')
        columns = urwid.Columns([
            footerleft,
            ('fixed', len(righttxt), footerright)])
        footer_att = settings.get_theming_attribute('global', 'footer')
        return urwid.AttrMap(columns, footer_att)

    def apply_command(self, cmd):
        """
        applies a command

        This calls the pre and post hooks attached to the command,
        as well as :meth:`cmd.apply`.

        :param cmd: an applicable command
        :type cmd: :class:`~alot.commands.Command`
        """
        if cmd:
            # define (callback) function that invokes post-hook
            def call_posthook(retval_from_apply):
                if cmd.posthook:
                    logging.info('calling post-hook')
                    return defer.maybeDeferred(cmd.posthook,
                                               ui=self,
                                               dbm=self.dbman,
                                               cmd=cmd)

            # call cmd.apply
            def call_apply(ignored):
                return defer.maybeDeferred(cmd.apply, self)

            prehook = cmd.prehook or (lambda **kwargs: None)
            d = defer.maybeDeferred(prehook, ui=self, dbm=self.dbman, cmd=cmd)
            d.addCallback(call_apply)
            d.addCallback(call_posthook)
            return d

########NEW FILE########
__FILENAME__ = booleanaction
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import argparse


TRUEISH = ['true', 'yes', 'on', '1', 't', 'y']
FALSISH = ['false', 'no', 'off', '0', 'f', 'n']


def boolean(string):
    string = string.lower()
    if string in FALSISH:
        return False
    elif string in TRUEISH:
        return True
    else:
        raise ValueError()


class BooleanAction(argparse.Action):
    """
    argparse action that can be used to store boolean values
    """
    def __init__(self, *args, **kwargs):
        kwargs['type'] = boolean
        kwargs['metavar'] = 'BOOL'
        argparse.Action.__init__(self, *args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)

########NEW FILE########
__FILENAME__ = walker
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import urwid
import logging


class PipeWalker(urwid.ListWalker):
    """urwid.ListWalker that reads next items from a pipe and
    wraps them in `containerclass` widgets for displaying
    """
    def __init__(self, pipe, containerclass, reverse=False, **kwargs):
        self.pipe = pipe
        self.kwargs = kwargs
        self.containerclass = containerclass
        self.lines = []
        self.focus = 0
        self.empty = False
        self.direction = -1 if reverse else 1

    def __contains__(self, name):
        return self.lines.__contains__(name)

    def get_focus(self):
        return self._get_at_pos(self.focus)

    def set_focus(self, focus):
        self.focus = focus
        self._modified()

    def get_next(self, start_from):
        return self._get_at_pos(start_from + self.direction)

    def get_prev(self, start_from):
        return self._get_at_pos(start_from - self.direction)

    def remove(self, obj):
        next_focus = self.focus % len(self.lines)
        if self.focus == len(self.lines) - 1 and self.empty:
            next_focus = self.focus - 1

        self.lines.remove(obj)
        if self.lines:
            self.set_focus(next_focus)
        self._modified()

    def _get_at_pos(self, pos):
        if pos < 0:  # pos too low
            return (None, None)
        elif pos > len(self.lines):  # pos too high
            return (None, None)
        elif len(self.lines) > pos:  # pos already cached
            return (self.lines[pos], pos)
        else:  # pos not cached yet, look at next item from iterator
            if self.empty:  # iterator is empty
                return (None, None)
            else:
                widget = self._get_next_item()
                if widget:
                    return (widget, pos)
                else:
                    return (None, None)

    def _get_next_item(self):
        if self.empty:
            return None
        try:
            # the next line blocks until it can read from the pipe or
            # EOFError is raised. No races here.
            next_obj = self.pipe.recv()
            next_widget = self.containerclass(next_obj, **self.kwargs)
            self.lines.append(next_widget)
        except EOFError:
            logging.debug('EMPTY PIPE')
            next_widget = None
            self.empty = True
        return next_widget

    def get_lines(self):
        return self.lines

########NEW FILE########
__FILENAME__ = bufferlist
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file

"""
Widgets specific to Bufferlist mode
"""
import urwid


class BufferlineWidget(urwid.Text):
    """
    selectable text widget that represents a :class:`~alot.buffers.Buffer`
    in the :class:`~alot.buffers.BufferlistBuffer`.
    """

    def __init__(self, buffer):
        self.buffer = buffer
        line = buffer.__str__()
        urwid.Text.__init__(self, line, wrap='clip')

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key

    def get_buffer(self):
        return self.buffer

########NEW FILE########
__FILENAME__ = globals
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file

"""
This contains alot-specific :class:`urwid.Widget` used in more than one mode.
"""
import urwid

from alot.helper import string_decode
from alot.settings import settings
from alot.db.attachment import Attachment
from alot.errors import CompletionError


class AttachmentWidget(urwid.WidgetWrap):
    """
    one-line summary of an :class:`~alot.db.attachment.Attachment`.
    """
    def __init__(self, attachment, selectable=True):
        self._selectable = selectable
        self.attachment = attachment
        if not isinstance(attachment, Attachment):
            self.attachment = Attachment(self.attachment)
        att = settings.get_theming_attribute('thread', 'attachment')
        focus_att = settings.get_theming_attribute('thread',
                                                   'attachment_focus')
        widget = urwid.AttrMap(urwid.Text(self.attachment.__str__()),
                               att, focus_att)
        urwid.WidgetWrap.__init__(self, widget)

    def get_attachment(self):
        return self.attachment

    def selectable(self):
        return self._selectable

    def keypress(self, size, key):
        return key


class ChoiceWidget(urwid.Text):
    def __init__(self, choices, callback, cancel=None, select=None,
                 separator=' '):
        self.choices = choices
        self.callback = callback
        self.cancel = cancel
        self.select = select
        self.separator = separator

        items = []
        for k, v in choices.items():
            if v == select and select is not None:
                items += ['[', k, ']:', v]
            else:
                items += ['(', k, '):', v]
            items += [self.separator]
        urwid.Text.__init__(self, items)

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key == 'enter' and self.select is not None:
            self.callback(self.select)
        elif key == 'esc' and self.cancel is not None:
            self.callback(self.cancel)
        elif key in self.choices:
            self.callback(self.choices[key])
        else:
            return key


class CompleteEdit(urwid.Edit):
    """
    This is a vamped-up :class:`urwid.Edit` widget that allows for
    tab-completion using :class:`~alot.completion.Completer` objects

    These widgets are meant to be used as user input prompts and hence
    react to 'return' key presses by calling a 'on_exit' callback
    that processes the current text value.

    The interpretation of some keypresses is hard-wired:
        :enter: calls 'on_exit' callback with current value
        :esc: calls 'on_exit' with value `None`, which can be interpreted
              as cancelation
        :tab: calls the completer and tabs forward in the result list
        :shift tab: tabs backward in the result list
        :up/down: move in the local input history
        :ctrl a/e: moves curser to the beginning/end of the input
    """
    def __init__(self, completer, on_exit,
                 on_error=None,
                 edit_text=u'',
                 history=None,
                 **kwargs):
        """
        :param completer: completer to use
        :type completer: alot.completion.Completer
        :param on_exit: "enter"-callback that interprets the input (str)
        :type on_exit: callable
        :param on_error: callback that handles :class:`completion errors <alot.errors.CompletionErrors>`
        :type on_error: callback
        :param edit_text: initial text
        :type edit_text: str
        :param history: initial command history
        :type history: list or str
        """
        self.completer = completer
        self.on_exit = on_exit
        self.on_error = on_error
        self.history = list(history)  # we temporarily add stuff here
        self.historypos = None

        if not isinstance(edit_text, unicode):
            edit_text = string_decode(edit_text)
        self.start_completion_pos = len(edit_text)
        self.completions = None
        urwid.Edit.__init__(self, edit_text=edit_text, **kwargs)

    def keypress(self, size, key):
        # if we tabcomplete
        if key in ['tab', 'shift tab'] and self.completer:
            # if not already in completion mode
            if self.completions is None:
                self.completions = [(self.edit_text, self.edit_pos)]
                try:
                    self.completions += self.completer.complete(self.edit_text,
                                                                self.edit_pos)
                    self.focus_in_clist = 1
                except CompletionError, e:
                    if self.on_error is not None:
                        self.on_error(e)

            else:  # otherwise tab through results
                if key == 'tab':
                    self.focus_in_clist += 1
                else:
                    self.focus_in_clist -= 1
            if len(self.completions) > 1:
                ctext, cpos = self.completions[self.focus_in_clist %
                                               len(self.completions)]
                self.set_edit_text(ctext)
                self.set_edit_pos(cpos)
            else:
                self.completions = None
        elif key in ['up', 'down']:
            if self.history:
                if self.historypos is None:
                    self.history.append(self.edit_text)
                    self.historypos = len(self.history) - 1
                if key == 'cursor up':
                    self.historypos = (self.historypos + 1) % len(self.history)
                else:
                    self.historypos = (self.historypos - 1) % len(self.history)
                self.set_edit_text(self.history[self.historypos])
        elif key == 'enter':
            self.on_exit(self.edit_text)
        elif key == 'esc':
            self.on_exit(None)
        elif key == 'ctrl a':
            self.set_edit_pos(0)
        elif key == 'ctrl e':
            self.set_edit_pos(len(self.edit_text))
        else:
            result = urwid.Edit.keypress(self, size, key)
            self.completions = None
            return result


class HeadersList(urwid.WidgetWrap):
    """ renders a pile of header values as key/value list """
    def __init__(self, headerslist, key_attr, value_attr, gaps_attr=None):
        """
        :param headerslist: list of key/value pairs to display
        :type headerslist: list of (str, str)
        :param key_attr: theming attribute to use for keys
        :type key_attr: urwid.AttrSpec
        :param value_attr: theming attribute to use for values
        :type value_attr: urwid.AttrSpec
        :param gaps_attr: theming attribute to wrap lines in
        :type gaps_attr: urwid.AttrSpec
        """
        self.headers = headerslist
        self.key_attr = key_attr
        self.value_attr = value_attr
        pile = urwid.Pile(self._build_lines(headerslist))
        if gaps_attr is None:
            gaps_attr = key_attr
        pile = urwid.AttrMap(pile, gaps_attr)
        urwid.WidgetWrap.__init__(self, pile)

    def __str__(self):
        return str(self.headers)

    def _build_lines(self, lines):
        max_key_len = 1
        headerlines = []
        #calc max length of key-string
        for key, value in lines:
            if len(key) > max_key_len:
                max_key_len = len(key)
        for key, value in lines:
            ##todo : even/odd
            keyw = ('fixed', max_key_len + 1,
                    urwid.Text((self.key_attr, key)))
            valuew = urwid.Text((self.value_attr, value))
            line = urwid.Columns([keyw, valuew])
            headerlines.append(line)
        return headerlines


class TagWidget(urwid.AttrMap):
    """
    text widget that renders a tagstring.

    It looks up the string it displays in the `tags` section
    of the config as well as custom theme settings for its tag.
    """
    def __init__(self, tag, fallback_normal=None, fallback_focus=None):
        self.tag = tag
        representation = settings.get_tagstring_representation(tag,
                                                               fallback_normal,
                                                               fallback_focus)
        self.translated = representation['translated']
        self.hidden = self.translated == ''
        self.txt = urwid.Text(self.translated, wrap='clip')
        normal_att = representation['normal']
        focus_att = representation['focussed']
        self.attmaps = {'normal': normal_att, 'focus': focus_att}
        urwid.AttrMap.__init__(self, self.txt, normal_att, focus_att)

    def set_map(self, attrstring):
        self.set_attr_map({None: self.attmaps[attrstring]})

    def width(self):
        # evil voodoo hotfix for double width chars that may
        # lead e.g. to strings with length 1 that need width 2
        return self.txt.pack()[0]

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key

    def get_tag(self):
        return self.tag

    def set_focussed(self):
        self.set_attr_map(self.attmap['focus'])

    def set_unfocussed(self):
        self.set_attr_map(self.attmap['normal'])

########NEW FILE########
__FILENAME__ = search
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
"""
Widgets specific to search mode
"""
import urwid

from alot.settings import settings
from alot.helper import shorten_author_string
from alot.helper import tag_cmp
from alot.widgets.utils import AttrFlipWidget
from alot.widgets.globals import TagWidget


class ThreadlineWidget(urwid.AttrMap):
    """
    selectable line widget that represents a :class:`~alot.db.Thread`
    in the :class:`~alot.buffers.SearchBuffer`.
    """
    def __init__(self, tid, dbman):
        self.dbman = dbman
        self.tid = tid
        self.thread = None  # will be set by refresh()
        self.tag_widgets = []
        self.structure = None
        self.rebuild()
        normal = self.structure['normal']
        focussed = self.structure['focus']
        urwid.AttrMap.__init__(self, self.columns, normal, focussed)

    def _build_part(self, name, struct, minw, maxw, align):
        def pad(string, shorten=None):
            if maxw:
                if len(string) > maxw:
                    if shorten:
                        string = shorten(string, maxw)
                    else:
                        string = string[:maxw]
            if minw:
                if len(string) < minw:
                    if align == 'left':
                        string = string.ljust(minw)
                    elif align == 'center':
                        string = string.center(minw)
                    else:
                        string = string.rjust(minw)
            return string

        part = None
        width = None
        if name == 'date':
            newest = None
            datestring = ''
            if self.thread:
                newest = self.thread.get_newest_date()
                datestring = settings.represent_datetime(newest)
            datestring = pad(datestring)
            width = len(datestring)
            part = AttrFlipWidget(urwid.Text(datestring), struct['date'])

        elif name == 'mailcount':
            if self.thread:
                mailcountstring = "(%d)" % self.thread.get_total_messages()
            else:
                mailcountstring = "(?)"
            mailcountstring = pad(mailcountstring)
            width = len(mailcountstring)
            mailcount_w = AttrFlipWidget(urwid.Text(mailcountstring),
                                         struct['mailcount'])
            part = mailcount_w
        elif name == 'authors':
            if self.thread:
                authors = self.thread.get_authors_string() or '(None)'
            else:
                authors = '(None)'
            authorsstring = pad(authors, shorten_author_string)
            authors_w = AttrFlipWidget(urwid.Text(authorsstring),
                                       struct['authors'])
            width = len(authorsstring)
            part = authors_w

        elif name == 'subject':
            if self.thread:
                subjectstring = self.thread.get_subject() or ' '
            else:
                subjectstring = ' '
            # sanitize subject string:
            subjectstring = subjectstring.replace('\n', ' ')
            subjectstring = subjectstring.replace('\r', '')
            subjectstring = pad(subjectstring)

            subject_w = AttrFlipWidget(urwid.Text(subjectstring, wrap='clip'),
                                       struct['subject'])
            if subjectstring:
                width = len(subjectstring)
                part = subject_w

        elif name == 'content':
            if self.thread:
                msgs = self.thread.get_messages().keys()
            else:
                msgs = []
            # sort the most recent messages first
            msgs.sort(key=lambda msg: msg.get_date(), reverse=True)
            lastcontent = ' '.join([m.get_text_content() for m in msgs])
            contentstring = pad(lastcontent.replace('\n', ' ').strip())
            content_w = AttrFlipWidget(urwid.Text(contentstring, wrap='clip'),
                                       struct['content'])
            width = len(contentstring)
            part = content_w
        elif name == 'tags':
            if self.thread:
                fallback_normal = struct[name]['normal']
                fallback_focus = struct[name]['focus']
                tag_widgets = [TagWidget(t, fallback_normal, fallback_focus)
                               for t in self.thread.get_tags()]
                tag_widgets.sort(tag_cmp,
                                 lambda tag_widget: tag_widget.translated)
            else:
                tag_widgets = []
            cols = []
            length = -1
            for tag_widget in tag_widgets:
                if not tag_widget.hidden:
                    wrapped_tagwidget = tag_widget
                    tag_width = tag_widget.width()
                    cols.append(('fixed', tag_width, wrapped_tagwidget))
                    length += tag_width + 1
            if cols:
                part = urwid.Columns(cols, dividechars=1)
                width = length
        return width, part

    def rebuild(self):
        self.thread = self.dbman.get_thread(self.tid)
        self.widgets = []
        columns = []
        self.structure = settings.get_threadline_theming(self.thread)
        for partname in self.structure['parts']:
            minw = maxw = None
            width_tuple = self.structure[partname]['width']
            if width_tuple is not None:
                if width_tuple[0] == 'fit':
                    minw, maxw = width_tuple[1:]
            align_mode = self.structure[partname]['alignment']
            width, part = self._build_part(partname, self.structure,
                                           minw, maxw, align_mode)
            if part is not None:
                if isinstance(part, urwid.Columns):
                    for w in part.widget_list:
                        self.widgets.append(w)
                else:
                    self.widgets.append(part)

                # compute width and align
                if width_tuple[0] == 'weight':
                    columnentry = width_tuple + (part,)
                else:
                    columnentry = ('fixed', width, part)
                columns.append(columnentry)
        self.columns = urwid.Columns(columns, dividechars=1)
        self.original_widget = self.columns

    def render(self, size, focus=False):
        for w in self.widgets:
            w.set_map('focus' if focus else 'normal')
        return urwid.AttrMap.render(self, size, focus)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key

    def get_thread(self):
        return self.thread

    def _get_theme(self, component, focus=False):
        path = ['search', 'threadline', component]
        if focus:
            path.append('focus')
        else:
            path.append('normal')
        return settings.get_theming_attribute(path)

########NEW FILE########
__FILENAME__ = thread
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
"""
Widgets specific to thread mode
"""
import urwid
import logging

from alot.settings import settings
from alot.db.utils import decode_header, X_SIGNATURE_MESSAGE_HEADER
from alot.helper import tag_cmp
from alot.widgets.globals import TagWidget
from alot.widgets.globals import AttachmentWidget
from alot.foreign.urwidtrees import Tree, SimpleTree, CollapsibleTree
from alot.db.utils import extract_body


class MessageSummaryWidget(urwid.WidgetWrap):
    """
    one line summary of a :class:`~alot.db.message.Message`.
    """

    def __init__(self, message, even=True):
        """
        :param message: a message
        :type message: alot.db.Message
        :param even: even entry in a pile of messages? Used for theming.
        :type even: bool
        """
        self.message = message
        self.even = even
        if even:
            attr = settings.get_theming_attribute('thread', 'summary', 'even')
        else:
            attr = settings.get_theming_attribute('thread', 'summary', 'odd')
        focus_att = settings.get_theming_attribute('thread', 'summary',
                                                   'focus')
        cols = []

        sumstr = self.__str__()
        txt = urwid.Text(sumstr)
        cols.append(txt)

        thread_tags = message.get_thread().get_tags(intersection=True)
        outstanding_tags = set(message.get_tags()).difference(thread_tags)
        tag_widgets = [TagWidget(t, attr, focus_att) for t in outstanding_tags]
        tag_widgets.sort(tag_cmp, lambda tag_widget: tag_widget.translated)
        for tag_widget in tag_widgets:
            if not tag_widget.hidden:
                cols.append(('fixed', tag_widget.width(), tag_widget))
        line = urwid.AttrMap(urwid.Columns(cols, dividechars=1), attr,
                             focus_att)
        urwid.WidgetWrap.__init__(self, line)

    def __str__(self):
        author, address = self.message.get_author()
        date = self.message.get_datestring()
        rep = author if author != '' else address
        if date is not None:
            rep += " (%s)" % date
        return rep

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class FocusableText(urwid.WidgetWrap):
    """Selectable Text used for nodes in our example"""
    def __init__(self, txt, att, att_focus):
        t = urwid.Text(txt)
        w = urwid.AttrMap(t, att, att_focus)
        urwid.WidgetWrap.__init__(self, w)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class TextlinesList(SimpleTree):
    def __init__(self, content, attr=None, attr_focus=None):
        """
        :class:`SimpleTree` that contains a list of all-level-0 Text widgets
        for each line in content.
        """
        structure = []
        for line in content.splitlines():
            structure.append((FocusableText(line, attr, attr_focus), None))
        SimpleTree.__init__(self, structure)


class DictList(SimpleTree):
    """
    :class:`SimpleTree` that displays key-value pairs.

    The structure will obey the Tree API but will not actually be a tree
    but a flat list: It contains one top-level node (displaying the k/v pair in
    Columns) per pair. That is, the root will be the first pair,
    its sibblings will be the other pairs and first|last_child will always
    be None.
    """
    def __init__(self, content, key_attr, value_attr, gaps_attr=None):
        """
        :param headerslist: list of key/value pairs to display
        :type headerslist: list of (str, str)
        :param key_attr: theming attribute to use for keys
        :type key_attr: urwid.AttrSpec
        :param value_attr: theming attribute to use for values
        :type value_attr: urwid.AttrSpec
        :param gaps_attr: theming attribute to wrap lines in
        :type gaps_attr: urwid.AttrSpec
        """
        max_key_len = 1
        structure = []
        # calc max length of key-string
        for key, value in content:
            if len(key) > max_key_len:
                max_key_len = len(key)
        for key, value in content:
            # todo : even/odd
            keyw = ('fixed', max_key_len + 1,
                    urwid.Text((key_attr, key)))
            valuew = urwid.Text((value_attr, value))
            line = urwid.Columns([keyw, valuew])
            if gaps_attr is not None:
                line = urwid.AttrMap(line, gaps_attr)
            structure.append((line, None))
        SimpleTree.__init__(self, structure)


class MessageTree(CollapsibleTree):
    """
    :class:`Tree` that displays contents of a single :class:`alot.db.Message`.

    Its root node is a :class:`MessageSummaryWidget`, and its child nodes
    reflect the messages content (parts for headers/attachments etc).

    Collapsing this message corresponds to showing the summary only.
    """
    def __init__(self, message, odd=True):
        """
        :param message: Messag to display
        :type message: alot.db.Message
        :param odd: theme summary widget as if this is an odd line
                    (in the message-pile)
        :type odd: bool
        """
        self._message = message
        self._odd = odd
        self.display_source = False
        self._summaryw = None
        self._bodytree = None
        self._sourcetree = None
        self.display_all_headers = False
        self._all_headers_tree = None
        self._default_headers_tree = None
        self.display_attachments = True
        self._attachments = None
        self._maintree = SimpleTree(self._assemble_structure())
        CollapsibleTree.__init__(self, self._maintree)

    def get_message(self):
        return self._message

    def reassemble(self):
        self._maintree._treelist = self._assemble_structure()

    def refresh(self):
        self._summaryw = None
        self.reassemble()

    def debug(self):
        logging.debug('collapsed %s' % self.is_collapsed(self.root))
        logging.debug('display_source %s' % self.display_source)
        logging.debug('display_all_headers %s' % self.display_all_headers)
        logging.debug('display_attachements %s' % self.display_attachments)
        logging.debug('AHT %s' % str(self._all_headers_tree))
        logging.debug('DHT %s' % str(self._default_headers_tree))
        logging.debug('MAINTREE %s' % str(self._maintree._treelist))

    def _assemble_structure(self):
        mainstruct = []
        if self.display_source:
            mainstruct.append((self._get_source(), None))
        else:
            mainstruct.append((self._get_headers(), None))

            attachmenttree = self._get_attachments()
            if attachmenttree is not None:
                mainstruct.append((attachmenttree, None))

            bodytree = self._get_body()
            if bodytree is not None:
                mainstruct.append((self._get_body(), None))

        structure = [
            (self._get_summary(), mainstruct)
        ]
        return structure

    def collapse_if_matches(self, querystring):
        """
        collapse (and show summary only) if the :class:`alot.db.Message`
        matches given `querystring`
        """
        self.set_position_collapsed(
            self.root, self._message.matches(querystring))

    def _get_summary(self):
        if self._summaryw is None:
            self._summaryw = MessageSummaryWidget(
                self._message, even=(not self._odd))
        return self._summaryw

    def _get_source(self):
        if self._sourcetree is None:
            sourcetxt = self._message.get_email().as_string()
            att = settings.get_theming_attribute('thread', 'body')
            att_focus = settings.get_theming_attribute('thread', 'body_focus')
            self._sourcetree = TextlinesList(sourcetxt, att, att_focus)
        return self._sourcetree

    def _get_body(self):
        if self._bodytree is None:
            bodytxt = extract_body(self._message.get_email())
            if bodytxt:
                att = settings.get_theming_attribute('thread', 'body')
                att_focus = settings.get_theming_attribute(
                    'thread', 'body_focus')
                self._bodytree = TextlinesList(bodytxt, att, att_focus)
        return self._bodytree

    def replace_bodytext(self, txt):
        """display txt instead of current msg 'body'"""
        if txt:
            att = settings.get_theming_attribute('thread', 'body')
            att_focus = settings.get_theming_attribute('thread', 'body_focus')
            self._bodytree = TextlinesList(txt, att, att_focus)

    def _get_headers(self):
        if self.display_all_headers is True:
            if self._all_headers_tree is None:
                self._all_headers_tree = self.construct_header_pile()
            ret = self._all_headers_tree
        else:
            if self._default_headers_tree is None:
                headers = settings.get('displayed_headers')
                self._default_headers_tree = self.construct_header_pile(
                    headers)
            ret = self._default_headers_tree
        return ret

    def _get_attachments(self):
        if self._attachments is None:
            alist = []
            for a in self._message.get_attachments():
                alist.append((AttachmentWidget(a), None))
            if alist:
                self._attachments = SimpleTree(alist)
        return self._attachments

    def construct_header_pile(self, headers=None, normalize=True):
        mail = self._message.get_email()
        lines = []

        if headers is None:
            # collect all header/value pairs in the order they appear
            headers = mail.keys()
            for key, value in mail.items():
                dvalue = decode_header(value, normalize=normalize)
                lines.append((key, dvalue))
        else:
            # only a selection of headers should be displayed.
            # use order of the `headers` parameter
            for key in headers:
                if key in mail:
                    if key.lower() in ['cc', 'bcc', 'to']:
                        values = mail.get_all(key)
                        values = [decode_header(
                            v, normalize=normalize) for v in values]
                        lines.append((key, ', '.join(values)))
                    else:
                        for value in mail.get_all(key):
                            dvalue = decode_header(value, normalize=normalize)
                            lines.append((key, dvalue))
                elif key.lower() == 'tags':
                    logging.debug('want tags header')
                    values = []
                    for t in self._message.get_tags():
                        tagrep = settings.get_tagstring_representation(t)
                        if t is not tagrep['translated']:
                            t = '%s (%s)' % (tagrep['translated'], t)
                        values.append(t)
                    lines.append((key, ', '.join(values)))

        # OpenPGP pseudo headers
        if mail[X_SIGNATURE_MESSAGE_HEADER]:
            lines.append(('PGP-Signature', mail[X_SIGNATURE_MESSAGE_HEADER]))

        key_att = settings.get_theming_attribute('thread', 'header_key')
        value_att = settings.get_theming_attribute('thread', 'header_value')
        gaps_att = settings.get_theming_attribute('thread', 'header')
        return DictList(lines, key_att, value_att, gaps_att)


class ThreadTree(Tree):
    """
    :class:`Tree` that parses a given :class:`alot.db.Thread` into a tree of
    :class:`MessageTrees <MessageTree>` that display this threads individual
    messages. As MessageTreess are *not* urwid widgets themself this is to be
    used in combination with :class:`NestedTree` only.
    """
    def __init__(self, thread):
        self._thread = thread
        self.root = thread.get_toplevel_messages()[0].get_message_id()
        self._parent_of = {}
        self._first_child_of = {}
        self._last_child_of = {}
        self._next_sibling_of = {}
        self._prev_sibling_of = {}
        self._message = {}

        def accumulate(msg, odd=True):
            """recursively read msg and its replies"""
            mid = msg.get_message_id()
            self._message[mid] = MessageTree(msg, odd)
            odd = not odd
            last = None
            self._first_child_of[mid] = None
            for reply in thread.get_replies_to(msg):
                rid = reply.get_message_id()
                if self._first_child_of[mid] is None:
                    self._first_child_of[mid] = rid
                self._parent_of[rid] = mid
                self._prev_sibling_of[rid] = last
                self._next_sibling_of[last] = rid
                last = rid
                odd = accumulate(reply, odd)
            self._last_child_of[mid] = last
            return odd

        last = None
        for msg in thread.get_toplevel_messages():
            mid = msg.get_message_id()
            self._prev_sibling_of[mid] = last
            self._next_sibling_of[last] = mid
            accumulate(msg)
            last = mid
        self._next_sibling_of[last] = None

    # Tree API
    def __getitem__(self, pos):
        return self._message.get(pos, None)

    def parent_position(self, pos):
        return self._parent_of.get(pos, None)

    def first_child_position(self, pos):
        return self._first_child_of.get(pos, None)

    def last_child_position(self, pos):
        return self._last_child_of.get(pos, None)

    def next_sibling_position(self, pos):
        return self._next_sibling_of.get(pos, None)

    def prev_sibling_position(self, pos):
        return self._prev_sibling_of.get(pos, None)

    def position_of_messagetree(self, mt):
        return mt._message.get_message_id()

########NEW FILE########
__FILENAME__ = utils
# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file

"""
Utility Widgets not specific to alot
"""
import urwid


class AttrFlipWidget(urwid.AttrMap):
    """
    An AttrMap that can remember attributes to set
    """
    def __init__(self, w, maps, init_map='normal'):
        self.maps = maps
        urwid.AttrMap.__init__(self, w, maps[init_map])

    def set_map(self, attrstring):
        self.set_attr_map({None: self.maps[attrstring]})


class DialogBox(urwid.WidgetWrap):
    def __init__(self, body, title, bodyattr=None, titleattr=None):
        self.body = urwid.LineBox(body)
        self.title = urwid.Text(title)
        if titleattr is not None:
            self.title = urwid.AttrMap(self.title, titleattr)
        if bodyattr is not None:
            self.body = urwid.AttrMap(self.body, bodyattr)

        box = urwid.Overlay(self.title, self.body,
                            align='center',
                            valign='top',
                            width=len(title),
                            height=None,
                            )
        urwid.WidgetWrap.__init__(self, box)

    def selectable(self):
        return self.body.selectable()

    def keypress(self, size, key):
        return self.body.keypress(size, key)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# alot documentation build configuration file, created by
# sphinx-quickstart on Tue Aug  9 15:00:51 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

###############################
# readthedocs.org hack,
# needed to use autodocs on their build-servers:
# http://readthedocs.org/docs/read-the-docs/en/latest/faq.html?highlight=autodocs#where-do-i-need-to-put-my-docs-for-rtd-to-find-it

class Mock(object):
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return Mock()

    @classmethod
    def __getattr__(self, name):
        return Mock() if name not in ('__file__', '__path__') else '/dev/null'

MOCK_MODULES = ['notmuch', 'notmuch.globals',
                'twisted', 'twisted.internet',
                'twisted.internet.defer',
                'twisted.python',
                'twisted.python.failure',
                'urwid',
                'magic',
                'argparse']
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = Mock()

# end of readthedocs.org hack
##############################

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))
from alot import __version__,__author__

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'alot'
copyright = u'2011 ' + __author__

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = __version__
# The full version, including alpha/beta/rc tags.
release = __version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'alotdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'alot.tex', u'alot Documentation',
   u'Patrick Totzke', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'alot', u'alot Documentation',
     [u'Patrick Totzke'], 1)
]

autodoc_member_order = 'bysource'
autoclass_content = 'both'
intersphinx_mapping = {
        'python': ('http://docs.python.org/3.2', None),
        'notmuch': ('http://packages.python.org/notmuch', None),
        'urwid': ('http://urwid.readthedocs.org/en/latest', None),
        }

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
# alot documentation build configuration file

import sys, os

###############################
# readthedocs.org hack,
# needed to use autodocs on their build-servers:
# http://readthedocs.org/docs/read-the-docs/en/latest/faq.html?highlight=autodocs#where-do-i-need-to-put-my-docs-for-rtd-to-find-it

class Mock(object):
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return Mock()

    @classmethod
    def __getattr__(self, name):
        return Mock() if name not in ('__file__', '__path__') else '/dev/null'

class MockModule(object):
    @classmethod
    def __getattr__(self, name):
        return Mock if name not in ('__file__', '__path__') else '/dev/null'

MOCK_MODULES = ['twisted', 'twisted.internet',
                'twisted.internet.defer',
                'twisted.python',
                'twisted.python.failure',
                'twisted.internet.protocol',
                'urwid',
                'magic',
                'gpgme',
                'configobj',
                'validate',
                'argparse']
MOCK_DIRTY = ['notmuch']
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = MockModule()
for mod_name in MOCK_DIRTY:
    sys.modules[mod_name] = Mock()

# end of readthedocs.org hack
##############################

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath(os.path.join('..','..')))
from alot import __version__,__author__

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']

# autodoc tweaks

# show classes' docstrings _and_ constructors docstrings/parameters
autoclass_content = 'both'


# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'alot'
copyright = u'2012, Patrick Totzke'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = __version__
# The full version, including alpha/beta/rc tags.
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = [
]

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = 'Alot User Manual'

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'alotdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'alot.tex', u'alot Documentation',
   u'Patrick Totzke', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True

autodoc_member_order = 'groupwise'

# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('manpage', 'alot', u'mail user agent for the notmuch mail system',
     [u'Patrick Totzke'], 1),
]


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'http://docs.python.org/': None,
    'http://notmuch.readthedocs.org/en/latest/': None,
    'http://urwid.readthedocs.org/en/latest/': None
}

########NEW FILE########
__FILENAME__ = generate_commands
import sys
import os
HERE = os.path.dirname(__file__)
sys.path.append(os.path.join(HERE, '..', '..', '..'))
from alot.commands import *
from alot.commands import COMMANDS
import alot.buffers
from argparse import HelpFormatter, SUPPRESS, OPTIONAL, ZERO_OR_MORE, ONE_OR_MORE, PARSER, REMAINDER
from alot.utils.booleanaction import BooleanAction
from gettext import gettext as _
import collections as _collections
import copy as _copy
import os as _os
import re as _re
import sys as _sys
import textwrap as _textwrap

NOTE = ".. CAUTION: THIS FILE IS AUTO-GENERATED!\n\n\n"

class HF(HelpFormatter):
    def _metavar_formatter(self, action, default_metavar):
        if action.metavar is not None:
            result = action.metavar
        else:
            result = default_metavar

        def format(tuple_size):
            if isinstance(result, tuple):
                return result
            else:
                return (result, ) * tuple_size
        return format


def rstify_parser(parser):
        #header = parser.format_usage().strip()
        #print '\n\n%s\n' % header + '_' * len(header)
        parser.formatter_class = HF
        #parser.print_help()
        #continue

        formatter = parser._get_formatter()
        out = ""

        # usage
        usage = formatter._format_usage(None, parser._actions,
                                         parser._mutually_exclusive_groups,
                                        '').strip()
        usage = usage.replace('--','---')

        # section header
        out += '.. describe:: %s\n\n' % parser.prog

        # description
        out += ' '*4 + parser.description
        out += '\n\n'

        if len(parser._positionals._group_actions) == 1:
            out += "    argument\n"
            a = parser._positionals._group_actions[0]
            out += ' '*8 + parser._positionals._group_actions[0].help
            if a.choices:
                out += ". valid choices are: %s." % ','.join(['\`%s\`' % s for s
                                                              in a.choices])
            if a.default:
                out += ". defaults to: '%s'." % a.default
            out += '\n\n'
        elif len(parser._positionals._group_actions) > 1:
            out += "    positional arguments\n"
            for index, a in enumerate(parser._positionals._group_actions):
                out += "        %s: %s" % (index, a.help)
                if a.choices:
                    out += ". valid choices are: %s." % ','.join(['\`%s\`' % s for s
                                                                  in a.choices])
                if a.default:
                    out += ". defaults to: '%s'." % a.default
                out += '\n'
            out += '\n\n'

        if parser._optionals._group_actions:
            out += "    optional arguments\n"
        for a in parser._optionals._group_actions:
            switches = [s.replace('--','---') for s in a.option_strings]
            out += "        :%s: %s" % (', '.join(switches), a.help)
            if a.choices and not isinstance(a, BooleanAction):
                out += ". Valid choices are: %s" % ','.join(['\`%s\`' % s for s
                                                              in a.choices])
            if a.default:
                out += " (Defaults to: '%s')" % a.default
            out += '.\n'
        out += '\n'

        # epilog
        #out += formatter.add_text(parser.epilog)

        return out

def get_mode_docs():
    docs = {}
    b = alot.buffers.Buffer
    for entry in alot.buffers.__dict__.values():
        if isinstance(entry, type):
            if issubclass(entry, b) and not entry == b:
                docs[entry.modename] = entry.__doc__.strip()
    return docs


if __name__ == "__main__":

    modes = []
    for mode, modecommands in COMMANDS.items():
        modefilename = mode+'.rst'
        modefile = open(os.path.join(HERE, 'usage', 'modes', modefilename), 'w')
        modefile.write(NOTE)
        if mode != 'global':
            modes.append(mode)
            header = 'Commands in `%s` mode' % mode
            modefile.write('%s\n%s\n' % (header, '-' * len(header)))
            modefile.write('The following commands are available in %s mode\n\n' % mode)
        else:
            header = 'Global Commands'
            modefile.write('%s\n%s\n' % (header, '-' * len(header)))
            modefile.write('The following commands are available globally\n\n')
        for cmdstring,struct in modecommands.items():
            cls, parser, forced_args = struct
            labelline = '.. _cmd.%s.%s:\n\n' % (mode, cmdstring.replace('_',
                                                                        '-'))
            modefile.write(labelline)
            modefile.write(rstify_parser(parser))
        modefile.close()

########NEW FILE########
__FILENAME__ = generate_configs
import sys
import os
HERE = os.path.dirname(__file__)
sys.path.append(os.path.join(HERE, '..', '..', '..'))
from alot.commands import COMMANDS
from configobj import ConfigObj
from validate import Validator
import re
NOTE = """
.. CAUTION: THIS FILE IS AUTO-GENERATED
    from the inline comments of specfile %s.

    If you want to change its content make your changes
    to that spec to ensure they woun't be overwritten later.
"""
def rewrite_entries(config, path, specpath, sec=None, sort=False):
    file = open(path, 'w')
    file.write(NOTE % specpath)

    if sec == None:
        sec = config
    if sort:
        sec.scalars.sort()
    for entry in sec.scalars:
        v = Validator()
        #config.validate(v)
        #print config[entry]
        #etype = re.sub('\(.*\)','', config[entry])
        ##if etype == 'option':
        etype, eargs, ekwargs, default = v._parse_check(sec[entry])
        if default is not None:
            default = config._quote(default)

        if etype == 'gpg_key_hint':
            etype = 'string'
        description = '\n.. _%s:\n' % entry.replace('_', '-')
        description += '\n.. describe:: %s\n\n' % entry
        comments = [sec.inline_comments[entry]] + sec.comments[entry]
        for c in comments:
            if c:
                description += ' '*4 + re.sub('^\s*#', '', c) + '\n'
        if etype == 'option':
            description += '\n    :type: option, one of %s\n' % eargs
        else:
            if etype == 'force_list':
                etype = 'string list'
            description += '\n    :type: %s\n' % etype

        if default != None:
            default = default.replace('*','\\*')
            if etype in ['string', 'string_list', 'gpg_key_hint'] and default != 'None':
                description += '    :default: "%s"\n\n' % (default)
            else:
                description += '    :default: %s\n\n' % (default)
        file.write(description)
    file.close()

if __name__ == "__main__":
    specpath = os.path.join(HERE, '..','..', 'alot', 'defaults', 'alot.rc.spec')
    config = ConfigObj(None, configspec=specpath, stringify=False, list_values=False)
    config.validate(Validator())

    alotrc_table_file = os.path.join(HERE, 'configuration', 'alotrc_table')
    rewrite_entries(config.configspec, alotrc_table_file, 'defaults/alot.rc.spec', sort=True)

    rewrite_entries(config, os.path.join(HERE, 'configuration', 'accounts_table'),
                    'defaults/alot.rc.spec',
                    sec=config.configspec['accounts']['__many__'])

########NEW FILE########
__FILENAME__ = colour_picker
#!/usr/bin/python
#
# COLOUR PICKER.
# This is a lightly modified version of urwids palette_test.py example script as
# found at https://raw.github.com/wardi/urwid/master/examples/palette_test.py
#
# This version simply omits resetting the screens default colour palette,
# and therefore displays the colour attributes as alot would render them in
# your terminal.
#
# Urwid Palette Test.  Showing off highcolor support
#    Copyright (C) 2004-2009  Ian Ward
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Urwid web site: http://excess.org/urwid/

"""
Palette test.  Shows the available foreground and background settings
in monochrome, 16 color, 88 color and 256 color modes.
"""

import re
import sys

import urwid
import urwid.raw_display

CHART_256 = """
brown__   dark_red_   dark_magenta_   dark_blue_   dark_cyan_   dark_green_
yellow_   light_red   light_magenta   light_blue   light_cyan   light_green

              #00f#06f#08f#0af#0df#0ff        black_______    dark_gray___   
            #60f#00d#06d#08d#0ad#0dd#0fd        light_gray__    white_______
          #80f#60d#00a#06a#08a#0aa#0da#0fa        
        #a0f#80d#60a#008#068#088#0a8#0d8#0f8        
      #d0f#a0d#80d#608#006#066#086#0a6#0d6#0f6
    #f0f#d0d#a0a#808#606#000#060#080#0a0#0d0#0f0#0f6#0f8#0fa#0fd#0ff
      #f0d#d0a#a08#806#600#660#680#6a0#6d0#6f0#6f6#6f8#6fa#6fd#6ff#0df
        #f0a#d08#a06#800#860#880#8a0#8d0#8f0#8f6#8f8#8fa#8fd#8ff#6df#0af
          #f08#d06#a00#a60#a80#aa0#ad0#af0#af6#af8#afa#afd#aff#8df#6af#08f
            #f06#d00#d60#d80#da0#dd0#df0#df6#df8#dfa#dfd#dff#adf#8af#68f#06f
              #f00#f60#f80#fa0#fd0#ff0#ff6#ff8#ffa#ffd#fff#ddf#aaf#88f#66f#00f
                                    #fd0#fd6#fd8#fda#fdd#fdf#daf#a8f#86f#60f
      #66d#68d#6ad#6dd                #fa0#fa6#fa8#faa#fad#faf#d8f#a6f#80f
    #86d#66a#68a#6aa#6da                #f80#f86#f88#f8a#f8d#f8f#d6f#a0f
  #a6d#86a#668#688#6a8#6d8                #f60#f66#f68#f6a#f6d#f6f#d0f
#d6d#a6a#868#666#686#6a6#6d6#6d8#6da#6dd    #f00#f06#f08#f0a#f0d#f0f
  #d6a#a68#866#886#8a6#8d6#8d8#8da#8dd#6ad       
    #d68#a66#a86#aa6#ad6#ad8#ada#add#8ad#68d   
      #d66#d86#da6#dd6#dd8#dda#ddd#aad#88d#66d        g78_g82_g85_g89_g93_g100  
                    #da6#da8#daa#dad#a8d#86d        g52_g58_g62_g66_g70_g74_
      #88a#8aa        #d86#d88#d8a#d8d#a6d        g27_g31_g35_g38_g42_g46_g50_
    #a8a#888#8a8#8aa    #d66#d68#d6a#d6d        g0__g3__g7__g11_g15_g19_g23_
      #a88#aa8#aaa#88a                        
            #a88#a8a
"""                    

CHART_88 = """
brown__   dark_red_   dark_magenta_   dark_blue_   dark_cyan_   dark_green_
yellow_   light_red   light_magenta   light_blue   light_cyan   light_green

      #00f#08f#0cf#0ff            black_______    dark_gray___             
    #80f#00c#08c#0cc#0fc            light_gray__    white_______           
  #c0f#80c#008#088#0c8#0f8
#f0f#c0c#808#000#080#0c0#0f0#0f8#0fc#0ff            #88c#8cc        
  #f0c#c08#800#880#8c0#8f0#8f8#8fc#8ff#0cf        #c8c#888#8c8#8cc   
    #f08#c00#c80#cc0#cf0#cf8#cfc#cff#8cf#08f        #c88#cc8#ccc#88c
      #f00#f80#fc0#ff0#ff8#ffc#fff#ccf#88f#00f            #c88#c8c        
                    #fc0#fc8#fcc#fcf#c8f#80f    
                      #f80#f88#f8c#f8f#c0f        g62_g74_g82_g89_g100  
                        #f00#f08#f0c#f0f        g0__g19_g35_g46_g52
"""

CHART_16 = """
brown__   dark_red_   dark_magenta_   dark_blue_   dark_cyan_   dark_green_
yellow_   light_red   light_magenta   light_blue   light_cyan   light_green

black_______    dark_gray___    light_gray__    white_______           
"""

ATTR_RE = re.compile("(?P<whitespace>[ \n]*)(?P<entry>[^ \n]+)")
SHORT_ATTR = 4 # length of short high-colour descriptions which may
# be packed one after the next

def parse_chart(chart, convert):
    """
    Convert string chart into text markup with the correct attributes.

    chart -- palette chart as a string
    convert -- function that converts a single palette entry to an
        (attr, text) tuple, or None if no match is found
    """
    out = []
    for match in re.finditer(ATTR_RE, chart):
        if match.group('whitespace'):
            out.append(match.group('whitespace'))
        entry = match.group('entry')
        entry = entry.replace("_", " ")
        while entry:
            # try the first four characters
            attrtext = convert(entry[:SHORT_ATTR])
            if attrtext:
                elen = SHORT_ATTR
                entry = entry[SHORT_ATTR:].strip()
            else: # try the whole thing
                attrtext = convert(entry.strip())
                assert attrtext, "Invalid palette entry: %r" % entry
                elen = len(entry)
                entry = ""
            attr, text = attrtext
            out.append((attr, text.ljust(elen)))
    return out
            
def foreground_chart(chart, background, colors):
    """
    Create text markup for a foreground colour chart

    chart -- palette chart as string
    background -- colour to use for background of chart
    colors -- number of colors (88 or 256)
    """
    def convert_foreground(entry):
        try:
            attr = urwid.AttrSpec(entry, background, colors)
        except urwid.AttrSpecError:
            return None
        return attr, entry
    return parse_chart(chart, convert_foreground)

def background_chart(chart, foreground, colors):
    """
    Create text markup for a background colour chart

    chart -- palette chart as string
    foreground -- colour to use for foreground of chart
    colors -- number of colors (88 or 256)

    This will remap 8 <= colour < 16 to high-colour versions
    in the hopes of greater compatibility
    """
    def convert_background(entry):
        try:
            attr = urwid.AttrSpec(foreground, entry, colors)
        except urwid.AttrSpecError:
            return None
        # fix 8 <= colour < 16
        if colors > 16 and attr.background_basic and \
            attr.background_number >= 8:
            # use high-colour with same number
            entry = 'h%d'%attr.background_number
            attr = urwid.AttrSpec(foreground, entry, colors)
        return attr, entry
    return parse_chart(chart, convert_background)


def main():
    palette = [
        ('header', 'black,underline', 'light gray', 'standout,underline',
            'black,underline', '#88a'),
        ('panel', 'light gray', 'dark blue', '',
            '#ffd', '#00a'),
        ('focus', 'light gray', 'dark cyan', 'standout',
            '#ff8', '#806'),
        ]

    screen = urwid.raw_display.Screen()
    screen.register_palette(palette)

    lb = urwid.SimpleListWalker([])
    chart_offset = None  # offset of chart in lb list

    mode_radio_buttons = []
    chart_radio_buttons = []

    def fcs(widget):
        # wrap widgets that can take focus
        return urwid.AttrMap(widget, None, 'focus')

    def set_mode(colors, is_foreground_chart):
        # set terminal mode and redraw chart
        screen.set_terminal_properties(colors)

        chart_fn = (background_chart, foreground_chart)[is_foreground_chart]
        if colors == 1:
            lb[chart_offset] = urwid.Divider()
        else:
            chart = {16: CHART_16, 88: CHART_88, 256: CHART_256}[colors]
            txt = chart_fn(chart, 'default', colors)
            lb[chart_offset] = urwid.Text(txt, wrap='clip')

    def on_mode_change(rb, state, colors):
        # if this radio button is checked
        if state:
            is_foreground_chart = chart_radio_buttons[0].state
            set_mode(colors, is_foreground_chart)
            
    def mode_rb(text, colors, state=False):
        # mode radio buttons
        rb = urwid.RadioButton(mode_radio_buttons, text, state)
        urwid.connect_signal(rb, 'change', on_mode_change, colors)
        return fcs(rb)

    def on_chart_change(rb, state):
        # handle foreground check box state change
        set_mode(screen.colors, state)
        
    def click_exit(button):
        raise urwid.ExitMainLoop()
    
    lb.extend([
        urwid.AttrMap(urwid.Text("Urwid Palette Test"), 'header'),
        urwid.AttrMap(urwid.Columns([
            urwid.Pile([
                mode_rb("Monochrome", 1),
                mode_rb("16-Color", 16, True),
                mode_rb("88-Color", 88),
                mode_rb("256-Color", 256),]),
            urwid.Pile([
                fcs(urwid.RadioButton(chart_radio_buttons,
                    "Foreground Colors", True, on_chart_change)),
                fcs(urwid.RadioButton(chart_radio_buttons,
                    "Background Colors")),
                urwid.Divider(),
                fcs(urwid.Button("Exit", click_exit)),
                ]),
            ]),'panel')
        ])

    chart_offset = len(lb)
    lb.extend([
        urwid.Divider() # placeholder for the chart
        ])

    set_mode(16, True) # displays the chart
    
    def unhandled_input(key):
        if key in ('Q','q','esc'):
            raise urwid.ExitMainLoop()

    urwid.MainLoop(urwid.ListBox(lb), screen=screen,
        unhandled_input=unhandled_input).run()

if __name__ == "__main__":
    main()



########NEW FILE########
__FILENAME__ = tagsections_convert
#!/usr/bin/python
"""
 CONFIG CONVERTER
 this script converts your custom tag string section from the v.3.1 syntax
 to the current format.

     >>> tagsections_convert.py -o config.new config.old

 will convert your whole alot config safely to the new format.
"""

from configobj import ConfigObj
import argparse
import sys
import re


def get_leaf_value(cfg, path, fallback=''):
    if len(path) == 1:
        if isinstance(cfg, ConfigObj):
            if path[0] not in cfg.scalars:
                return fallback
            else:
                return cfg[path[0]]
        else:
            if path[0] not in cfg:
                return fallback
            else:
                return cfg[path[0]]
    else:
        if path[0] in cfg:
            scfg = cfg[path[0]]
            sp = path[1:]
            return get_leaf_value(scfg, sp, fallback)
        else:
            return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='update alot theme files')
    parser.add_argument('configfile', type=argparse.FileType('r'),
                        help='theme file to convert')
    parser.add_argument('-o', type=argparse.FileType('w'), dest='out',
                        help='destination', default=sys.stdout)
    args = parser.parse_args()

    cfg = ConfigObj(args.configfile)
    out = args.out
    print args

    def is_256(att):
        r = r'(g\d{1,3}(?!\d))|(#[0-9A-Fa-f]{3}(?![0-9A-Fa-f]))'
        return re.search(r, att)

    if 'tags' in cfg:
        for tag in cfg['tags'].sections:
            sec = cfg['tags'][tag]
            att = [''] * 6

            if 'fg' in sec:
                fg = sec['fg']
                if not is_256(fg):
                    att[2] = fg
                att[4] = fg
                del(sec['fg'])

            if 'bg' in sec:
                bg = sec['bg']
                if not is_256(bg):
                    att[3] = bg
                att[5] = bg
                del(sec['bg'])
            sec['normal'] = att

            if sec.get('hidden'):
                sec['translated'] = ''
    cfg.write(out)

########NEW FILE########
__FILENAME__ = theme_convert
#!/usr/bin/python
"""
 THEME CONVERTER
 this script converts your custom alot theme files from the v.3.1 syntax
 to the current format.

     >>> theme_convert.py -o themefile.new themefile.old
"""

from configobj import ConfigObj
import argparse
import sys


def get_leaf_value(cfg, path, fallback=''):
    if len(path) == 1:
        if isinstance(cfg, ConfigObj):
            if path[0] not in cfg.scalars:
                return fallback
            else:
                return cfg[path[0]]
        else:
            if path[0] not in cfg:
                return fallback
            else:
                return cfg[path[0]]
    else:
        if path[0] in cfg:
            scfg = cfg[path[0]]
            sp = path[1:]
            return get_leaf_value(scfg, sp, fallback)
        else:
            return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='update alot theme files')
    parser.add_argument('themefile', type=argparse.FileType('r'),
                        help='theme file to convert')
    parser.add_argument('-o', type=argparse.FileType('w'), dest='out',
                        help='destination', default=sys.stdout)
    args = parser.parse_args()

    old = ConfigObj(args.themefile)
    new = ConfigObj()
    out = args.out

    def lookup(path):
        values = []
        for c in ['1', '16', '256']:
            values.append(get_leaf_value(old, [c] + path + ['fg']) or 'default')
            values.append(get_leaf_value(old, [c] + path + ['bg']) or 'default')
        return values
        values = map(lambda s: '\'' + s + '\'', values)
        return ','.join(values)

    for bmode in ['global', 'help', 'envelope']:
        new[bmode] = {}
        #out.write('[%s]\n' % bmode)
        for themable in old['16'][bmode].sections:
            new[bmode][themable] = lookup([bmode, themable])
            #out.write('    %s = %s\n' % (themable, lookup([bmode, themable])))

    # BUFFERLIST
    new['bufferlist'] = {}
    new['bufferlist']['line_even'] = lookup(['bufferlist','results_even'])
    new['bufferlist']['line_odd'] = lookup(['bufferlist','results_odd'])
    new['bufferlist']['line_focus'] = lookup(['bufferlist','focus'])

    # TAGLIST
    new['taglist'] = {}
    new['taglist']['line_even'] = lookup(['bufferlist','results_even'])
    new['taglist']['line_odd'] = lookup(['bufferlist','results_odd'])
    new['taglist']['line_focus'] = lookup(['bufferlist','focus'])

    # SEARCH
    new['search'] = {}

    new['search']['threadline'] = {}
    new['search']['threadline']['normal'] = lookup(['search', 'thread'])
    new['search']['threadline']['focus'] = lookup(['search', 'thread_focus'])
    new['search']['threadline']['parts'] = ['date','mailcount','tags','authors','subject']

    new['search']['threadline']['date'] = {}
    new['search']['threadline']['date']['normal'] = lookup(['search', 'thread_date'])
    new['search']['threadline']['date']['focus'] = lookup(['search', 'thread_date_focus'])

    new['search']['threadline']['mailcount'] = {}
    new['search']['threadline']['mailcount']['normal'] = lookup(['search', 'thread_mailcount'])
    new['search']['threadline']['mailcount']['focus'] = lookup(['search', 'thread_mailcount_focus'])

    new['search']['threadline']['tags'] = {}
    new['search']['threadline']['tags']['normal'] = lookup(['search', 'thread_tags'])
    new['search']['threadline']['tags']['focus'] = lookup(['search', 'thread_tags_focus'])

    new['search']['threadline']['authors'] = {}
    new['search']['threadline']['authors']['normal'] = lookup(['search', 'thread_authors'])
    new['search']['threadline']['authors']['focus'] = lookup(['search', 'thread_authors_focus'])

    new['search']['threadline']['subject'] = {}
    new['search']['threadline']['subject']['normal'] = lookup(['search', 'thread_subject'])
    new['search']['threadline']['subject']['focus'] = lookup(['search', 'thread_subject_focus'])

    new['search']['threadline']['content'] = {}
    new['search']['threadline']['content']['normal'] = lookup(['search', 'thread_content'])
    new['search']['threadline']['content']['focus'] = lookup(['search', 'thread_content_focus'])

    # THREAD
    new['thread'] = {}
    new['thread']['attachment'] = lookup(['thread','attachment'])
    new['thread']['attachment_focus'] = lookup(['thread','attachment_focus'])
    new['thread']['body'] = lookup(['thread','body'])
    new['thread']['arrow_heads'] = lookup(['thread','body'])
    new['thread']['arrow_bars'] = lookup(['thread','body'])
    new['thread']['header'] = lookup(['thread','header'])
    new['thread']['header_key'] = lookup(['thread','header_key'])
    new['thread']['header_value'] = lookup(['thread','header_value'])
    new['thread']['summary'] = {}
    new['thread']['summary']['even'] = lookup(['thread','summary_even'])
    new['thread']['summary']['odd'] = lookup(['thread','summary_odd'])
    new['thread']['summary']['focus'] = lookup(['thread','summary_focus'])

    # write out
    new.write(out)

########NEW FILE########
